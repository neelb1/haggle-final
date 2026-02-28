"""
Monitoring Endpoints
- GET  /api/monitor/status   — check all integration statuses
- POST /api/monitor/scan     — trigger a manual scan (Stripe + Overshoot + Tavily)
- POST /api/monitor/ingest   — ingest a document into Senso
- GET  /api/monitor/demo     — get pre-built demo detection for presentation
"""

import logging

from fastapi import APIRouter, Request

from models.schemas import TaskCreate, TaskAction, SSEEvent, SSEEventType
from services.task_store import store
from services import airbyte_service, overshoot_service, senso_service, tavily_service, gmail_service, reka_service, yutori_service, postgres_service
from services.neo4j_service import neo4j_service
import config

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/api/monitor/status")
async def integration_status():
    """Check which integrations are configured and available."""
    return {
        "vapi": bool(config.VAPI_API_KEY),
        "neo4j": bool(config.NEO4J_URI),
        "tavily": bool(config.TAVILY_API_KEY),
        "senso": bool(config.SENSO_API_KEY),
        "stripe": bool(config.STRIPE_API_KEY),
        "slack": bool(config.SLACK_BOT_TOKEN and config.SLACK_CHANNEL_ID),
        "overshoot": bool(config.OVERSHOOT_API_KEY),
        "modulate": bool(config.MODULATE_API_KEY),
        "reka": bool(config.REKA_API_KEY),
        "yutori": bool(config.YUTORI_API_KEY),
    }


@router.post("/api/monitor/scan")
async def trigger_scan():
    """
    Run a monitoring scan across all configured sources.
    Creates tasks for any detected anomalies.
    """
    detections = []

    # 1. Check Stripe for billing anomalies
    if config.STRIPE_API_KEY:
        anomalies = await airbyte_service.detect_billing_anomalies(days=60)
        for a in anomalies:
            # Classify via Senso
            classification = await senso_service.classify_threat(
                f"{a['merchant']} {a['type']} amount changed from ${a.get('old_amount', '?')} to ${a.get('new_amount', '?')}"
            )
            a["classification"] = classification
            detections.append(a)

            # Auto-create task for billing increases
            if a["type"] == "BILLING_INCREASE":
                task = store.create_task(TaskCreate(
                    company=a["merchant"],
                    action="negotiate_rate",
                    phone_number="+18005551234",  # Placeholder
                    service_type="subscription",
                    current_rate=a["new_amount"],
                    target_rate=a["old_amount"],
                    notes=f"Detected {a['increase_pct']}% rate increase via Stripe monitoring",
                ))
                await store.push_task_update(task)

    # 2. Check Overshoot for financial broadcast alerts
    if config.OVERSHOOT_API_KEY:
        # In production: pass a live video URL
        # For hackathon: use demo detection
        events = await overshoot_service.monitor_broadcast("demo")
        detections.extend(events)

    # 3. Notify via Slack + Gmail
    if detections:
        await airbyte_service.send_slack_alert(
            f"Haggle scan detected {len(detections)} anomalies"
        )
        await gmail_service.send_threat_alert(detections)

    # Push scan results to SSE
    await store.push_event(SSEEvent(
        type=SSEEventType.TASK_UPDATED,
        data={"scan_results": detections, "count": len(detections)},
    ))

    return {"detections": detections, "count": len(detections)}


@router.get("/api/monitor/demo")
async def demo_detection():
    """Return pre-built detections for reliable demo flow."""
    overshoot_detection = overshoot_service.get_demo_detection()

    return {
        "detections": [
            {
                "source": "airbyte_stripe",
                "type": "BILLING_INCREASE",
                "company": "Comcast",
                "old_amount": 55.0,
                "new_amount": 85.0,
                "increase_pct": 54.5,
                "classification": "BILLING_INCREASE",
            },
            overshoot_detection,
            {
                "source": "tavily_search",
                "type": "COMPETITOR_RATE",
                "company": "T-Mobile",
                "summary": "T-Mobile 5G Home Internet available at $50/month in your area",
                "relevance": "leverage for Comcast negotiation",
            },
        ],
    }


@router.post("/api/monitor/ingest")
async def ingest_document(request: Request):
    """Ingest a document into Senso Context OS."""
    body = await request.json()
    title = body.get("title", "")
    text = body.get("text", "")
    if not title or not text:
        return {"error": "title and text required"}
    result = await senso_service.ingest_content(title, text)
    return result


# ── Reka Vision: Bill Image Analysis ─────────────────────────


@router.post("/api/bills/analyze")
async def analyze_bill(request: Request):
    """
    Analyze a bill image with Reka Vision.
    Auto-creates a negotiation task if price increase detected.
    """
    body = await request.json()
    image_url = body.get("image_url", "")
    if not image_url:
        return {"error": "image_url required"}

    result = await reka_service.analyze_bill_image(image_url)

    # If price increase detected, auto-create a negotiation task
    price_change = result.get("price_change")
    if price_change:
        change_str = str(price_change).replace("$", "").replace("+", "").replace("-", "")
        try:
            change_val = float(change_str)
        except ValueError:
            change_val = 0
        if change_val > 0:
            total_str = str(result.get("total_amount", "0")).replace("$", "").replace(",", "")
            try:
                current_rate = float(total_str)
            except ValueError:
                current_rate = 0
            task = store.create_task(TaskCreate(
                company=result.get("provider_name", "Unknown Provider"),
                action=TaskAction.NEGOTIATE_RATE,
                phone_number="",
                current_rate=current_rate,
                notes=f"Reka Vision detected price increase: {price_change}. Hidden fees: {result.get('hidden_fees', [])}",
            ))
            result["auto_task_created"] = task.id
            await store.push_task_update(task)

    # Store analysis in Neo4j
    neo4j_service.add_entity(
        "bill_analysis",
        result.get("provider_name", "Unknown"),
        f"Reka Vision: total={result.get('total_amount')}, change={price_change}",
    )

    # Push to SSE
    await store.push_event(SSEEvent(
        type=SSEEventType.BILL_ANALYZED,
        data=result,
    ))

    # Store in Postgres
    await postgres_service.insert_bill_scan(result, task_id=result.get("auto_task_created", ""))

    return result


@router.get("/api/calls/history")
async def call_history():
    """Return recent call logs from Postgres."""
    rows = await postgres_service.get_call_history(limit=20)
    return {"calls": rows, "count": len(rows), "postgres": postgres_service.available()}


@router.post("/api/bills/compare")
async def compare_bills(request: Request):
    """Compare two bill images to detect changes (Reka Vision)."""
    body = await request.json()
    old_url = body.get("old_image_url", "")
    new_url = body.get("new_image_url", "")
    if not old_url or not new_url:
        return {"error": "old_image_url and new_image_url required"}
    return await reka_service.compare_bills(old_url, new_url)


@router.post("/api/bills/document")
async def analyze_document(request: Request):
    """Analyze a financial document — PDF or image (Reka Vision)."""
    body = await request.json()
    url = body.get("document_url", "")
    doc_type = body.get("type", "pdf")
    if not url:
        return {"error": "document_url required"}
    return await reka_service.analyze_document(url, doc_type)


# ── Yutori Scouts: Proactive Web Monitoring ──────────────────


@router.post("/api/monitor/scout")
async def create_scout(request: Request):
    """Create a Yutori Scout to monitor a provider's website."""
    body = await request.json()
    provider = body.get("provider", "")
    if not provider:
        return {"error": "provider required"}
    return await yutori_service.create_scout(
        provider=provider,
        provider_url=body.get("url", ""),
        monitor_type=body.get("monitor_type", "price_change"),
    )


@router.post("/api/monitor/yutori-webhook")
async def yutori_webhook(request: Request):
    """Receive webhook from a Yutori Scout detection."""
    body = await request.json()
    detection = await yutori_service.handle_scout_webhook(body)

    # Auto-create task for detected threats
    if detection.get("detection_type") == "price_change":
        details = detection.get("details", {})
        task = store.create_task(TaskCreate(
            company=detection.get("provider", "Unknown"),
            action=TaskAction.NEGOTIATE_RATE,
            phone_number="",
            notes=f"Yutori Scout detected: {details.get('old_price', '?')} -> {details.get('new_price', '?')}",
        ))
        await store.push_task_update(task)
        detection["auto_task_created"] = task.id

    return detection
