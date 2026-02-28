"""
Yutori Scouts Integration
- Proactive web monitoring for price changes, policy updates, new fees
- Fires webhooks to task engine when threats detected
- Falls back to Tavily search when Yutori API not available

NOTE: Get API credentials from Dhruv Batra at hackathon.
Yutori is early stage — API details will be provided on-site.
"""

import logging
from typing import Optional

import config

logger = logging.getLogger(__name__)


async def create_scout(
    provider: str,
    provider_url: str = "",
    monitor_type: str = "price_change",
) -> dict:
    """
    Create a Yutori Scout to proactively monitor a provider's website.

    When Yutori API is available, this creates a persistent Scout that:
    - Periodically browses the provider's website
    - Detects price changes, policy updates, new fees
    - Fires webhooks back to our /api/monitor/yutori-webhook endpoint
    """
    if not config.YUTORI_API_KEY:
        logger.info("Yutori not configured — using Tavily fallback for %s", provider)
        return await _fallback_monitor(provider, monitor_type)

    # TODO: Wire to Yutori Scout API once credentials obtained at hackathon
    # Expected integration pattern:
    #
    # async with httpx.AsyncClient() as client:
    #     resp = await client.post(
    #         "https://api.yutori.ai/v1/scouts",
    #         headers={"Authorization": f"Bearer {config.YUTORI_API_KEY}"},
    #         json={
    #             "name": f"LifePilot-{provider}-monitor",
    #             "target_url": provider_url or f"https://www.{provider.lower().replace(' ', '')}.com",
    #             "schedule": "daily",
    #             "detect": ["price_changes", "policy_updates", "new_fees", "promotional_offers"],
    #             "webhook_url": f"{config.SERVER_URL}/api/monitor/yutori-webhook",
    #         },
    #     )
    #     return resp.json()

    return {"status": "yutori_pending", "message": "API integration ready — awaiting credentials"}


async def list_scouts() -> list[dict]:
    """List all active Yutori Scouts."""
    if not config.YUTORI_API_KEY:
        return []
    # TODO: GET /v1/scouts
    return []


async def handle_scout_webhook(payload: dict) -> dict:
    """
    Handle incoming webhook from a Yutori Scout detection.
    This gets called when a Scout finds a price change or policy update.

    Expected payload:
    {
        "scout_id": "...",
        "provider": "Comcast",
        "detection_type": "price_change",
        "details": {
            "old_price": "$55/mo",
            "new_price": "$85/mo",
            "effective_date": "2025-04-01",
            "source_url": "https://www.xfinity.com/pricing"
        },
        "confidence": 0.94,
        "screenshot_url": "https://..."
    }
    """
    return {
        "provider": payload.get("provider", "Unknown"),
        "detection_type": payload.get("detection_type", "unknown"),
        "details": payload.get("details", {}),
        "confidence": payload.get("confidence", 0.0),
        "screenshot_url": payload.get("screenshot_url"),
    }


async def _fallback_monitor(provider: str, monitor_type: str) -> dict:
    """
    Fallback: use Tavily search to simulate Scout behavior.
    Searches for recent news about provider price changes.
    """
    from services import tavily_service

    queries = {
        "price_change": f"{provider} price increase rate change 2025",
        "policy_update": f"{provider} policy change cancellation update 2025",
        "new_fees": f"{provider} new fees surcharges added 2025",
    }
    query = queries.get(monitor_type, f"{provider} {monitor_type} 2025")

    result = tavily_service.search(query)
    return {
        "source": "tavily_fallback",
        "provider": provider,
        "monitor_type": monitor_type,
        "result": result,
    }
