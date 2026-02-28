import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from services.neo4j_service import neo4j_service
from services import senso_service, postgres_service
from routers import vapi_tools, vapi_webhook, tasks, monitoring, demo, user_call
import config

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Haggle backend starting up")
    neo4j_service.connect()
    if neo4j_service.available:
        neo4j_service.seed_demo_data()
    # Seed Senso with compliance docs for grounded knowledge
    await senso_service.seed_compliance_docs()
    # Connect to Render Postgres for call logging
    await postgres_service.connect()
    # NOTE: GLiNER2 preload removed — 205M param model exceeds Render free tier 512MB limit
    # fastino_service will lazy-load on first use if memory allows
    yield
    # Shutdown
    await postgres_service.disconnect()
    neo4j_service.close()
    logger.info("Haggle backend shut down")


app = FastAPI(
    title="Haggle Backend",
    description="Backend for Haggle voice agent — handles Vapi webhooks, tool calls, task management, and SSE streaming.",
    version="1.0.0",
    lifespan=lifespan,
)

# ── Demo protection: block action endpoints unless secret header present ──
DEMO_SECRET = os.getenv("DEMO_SECRET", "")
# Endpoints that cost money / trigger calls — require X-Demo-Secret header
PROTECTED_PREFIXES = [
    "/api/demo/run", "/api/demo/reset", "/api/demo/user-consult",
    "/api/bills/analyze", "/api/bills/compare", "/api/bills/document",
    "/api/monitor/scan", "/api/monitor/scout",
    "/api/user/call",
]

class DemoGuardMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if DEMO_SECRET and request.method == "POST":
            path = request.url.path
            if any(path.startswith(p) for p in PROTECTED_PREFIXES):
                token = request.headers.get("x-demo-secret", "")
                if token != DEMO_SECRET:
                    return JSONResponse(
                        status_code=403,
                        content={"error": "Demo locked. Not authorized."},
                    )
        return await call_next(request)

app.add_middleware(DemoGuardMiddleware)

# CORS — allow dashboard frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)

# Routers
app.include_router(vapi_tools.router, tags=["Vapi Tools"])
app.include_router(vapi_webhook.router, tags=["Vapi Webhooks"])
app.include_router(tasks.router, tags=["Tasks"])
app.include_router(monitoring.router, tags=["Monitoring"])
app.include_router(demo.router, tags=["Demo"])
app.include_router(user_call.router, tags=["User Consult"])


@app.get("/api/status")
async def api_status():
    return {
        "service": "Haggle Backend",
        "status": "running",
        "neo4j": "connected" if neo4j_service.available else "not configured",
        "senso": "configured" if config.SENSO_API_KEY else "not configured",
        "stripe": "configured" if config.STRIPE_API_KEY else "not configured",
        "overshoot": "configured" if config.OVERSHOOT_API_KEY else "not configured",
        "tavily": "configured" if config.TAVILY_API_KEY else "not configured",
        "modulate": "configured" if config.MODULATE_API_KEY else "not configured",
        "reka": "configured" if config.REKA_API_KEY else "not configured",
        "postgres": "connected" if postgres_service.available() else "not configured",
        "fastino_gliner2": "disabled (memory limit)",
        "yutori": "configured" if config.YUTORI_API_KEY else "not configured",
    }


@app.get("/health")
async def health():
    return {"status": "ok"}


# ── Serve Dashboard ──────────────────────────────────────────
DASHBOARD_DIR = Path(__file__).parent / "static"

if DASHBOARD_DIR.exists() and (DASHBOARD_DIR / "index.html").exists():
    # Serve /assets/* statically (won't conflict with /api/*)
    if (DASHBOARD_DIR / "assets").exists():
        app.mount("/assets", StaticFiles(directory=DASHBOARD_DIR / "assets"), name="static-assets")

    # Serve static files in root (logo, demo-bill, etc.)
    @app.get("/logo.png")
    async def serve_logo():
        return FileResponse(DASHBOARD_DIR / "logo.png")

    @app.get("/demo-bill.png")
    async def serve_demo_bill():
        return FileResponse(DASHBOARD_DIR / "demo-bill.png")

    @app.get("/")
    async def serve_index():
        return FileResponse(DASHBOARD_DIR / "index.html")
