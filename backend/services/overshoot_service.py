"""
Overshoot Vision AI Integration
- Monitor financial news broadcasts (CNBC, Bloomberg) via video/screen capture
- Extract structured financial data at sub-200ms latency
- Detect rate changes, billing announcements before text-based feeds

Overshoot API: https://api.overshoot.ai
Docs: https://docs.overshoot.ai
SDK: TypeScript only — we use the REST API directly via httpx.
"""

import logging

import httpx

import config

logger = logging.getLogger(__name__)


async def analyze_frame(
    image_url: str,
    prompt: str = None,
    model: str = "qwen3-vl-30b",
) -> dict:
    """Analyze a single image/frame for financial data."""
    if not config.OVERSHOOT_API_KEY:
        return {"status": "overshoot_unavailable"}

    if prompt is None:
        prompt = (
            "Extract any financial announcements visible in this image: "
            "rate changes, price increases, billing updates, service announcements, "
            "stock movements, or economic data. Return structured JSON with fields: "
            "company, change_type (rate_increase/rate_decrease/new_fee/announcement), "
            "old_value, new_value, summary. If no financial data is visible, "
            "return {\"financial_data\": false}."
        )

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{config.OVERSHOOT_BASE_URL}/v1/analyze",
                headers={
                    "Authorization": f"Bearer {config.OVERSHOOT_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "image_url": image_url,
                    "prompt": prompt,
                    "model": model,
                },
            )
            resp.raise_for_status()
            return resp.json()
    except Exception as e:
        logger.error("Overshoot analyze failed: %s", e)
        return {"error": str(e)}


async def monitor_broadcast(video_source: str) -> list[dict]:
    """
    Monitor a video source for financial events.

    For hackathon demo: we pass a screenshot URL of a financial news broadcast
    rather than a live video stream (simpler, same visual effect on dashboard).
    """
    if not config.OVERSHOOT_API_KEY:
        logger.debug("OVERSHOOT_API_KEY not set — vision monitoring disabled")
        return []

    result = await analyze_frame(video_source)

    if "error" in result:
        return []

    # Parse the VLM response for financial events
    events = []
    data = result.get("result", result)

    # The VLM returns structured text — try to extract events
    if isinstance(data, dict) and data.get("financial_data") is not False:
        events.append({
            "source": "overshoot_vision",
            "raw": data,
            "video_source": video_source,
        })
    elif isinstance(data, str) and "financial_data" not in data.lower():
        events.append({
            "source": "overshoot_vision",
            "raw": data,
            "video_source": video_source,
        })

    return events


# ── Demo Helpers ──────────────────────────────────────────────

def get_demo_detection() -> dict:
    """
    Return a pre-built detection for the demo.
    Used when Overshoot API isn't configured or for reliable demo flow.
    """
    return {
        "source": "overshoot_vision",
        "type": "BILLING_INCREASE",
        "company": "Comcast",
        "summary": "Overshoot Vision AI detected Comcast rate increase announcement on financial broadcast",
        "details": {
            "change_type": "rate_increase",
            "old_value": "$55/month",
            "new_value": "$85/month",
            "confidence": 0.94,
        },
    }
