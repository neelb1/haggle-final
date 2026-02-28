"""
Monitoring Endpoints
- GET  /api/monitor/status   — check all integration statuses
- POST /api/monitor/scan     — trigger a manual scan (Stripe + Overshoot + Tavily)
- POST /api/monitor/ingest   — ingest a document into Senso
- GET  /api/monitor/demo     — get pre-built demo detection for presentation
"""

import logging

from fastapi import APIRouter, Request

from models.schemas import TaskCreate, SSEEvent, SSEEventType
from services.task_store import store
from services import airbyte_service, overshoot_service, senso_service, tavily_service
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

    # 3. Notify via Slack
    if detections:
        summary = f"LifePilot scan detected {len(detections)} anomalies"
        await airbyte_service.send_slack_alert(summary)

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
