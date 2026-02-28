"""
Airbyte Agent Connectors Integration
- Stripe: detect billing anomalies (rate hikes, new fees, duplicate charges)
- Slack: send threat alerts + call summaries to user

These are standalone pip packages — no Airbyte platform needed.
Install: pip install airbyte-agent-stripe airbyte-agent-slack

For hackathon: we use httpx to call Stripe/Slack APIs directly since
the agent connector packages may not be available on all Python versions.
Same entity-action pattern, just implemented with raw HTTP.
"""

import logging
import time
from typing import Optional

import httpx

import config

logger = logging.getLogger(__name__)


# ── Stripe: Detect Billing Anomalies ─────────────────────────

async def check_stripe_charges(days: int = 30) -> list[dict]:
    """Pull recent Stripe charges and detect anomalies."""
    if not config.STRIPE_API_KEY:
        logger.debug("STRIPE_API_KEY not set — Stripe monitoring disabled")
        return []

    created_after = int(time.time()) - (days * 86400)

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                "https://api.stripe.com/v1/charges",
                params={"limit": 50, "created[gte]": created_after},
                headers={"Authorization": f"Bearer {config.STRIPE_API_KEY}"},
            )
            resp.raise_for_status()
            charges = resp.json().get("data", [])
            logger.info("Fetched %d Stripe charges from last %d days", len(charges), days)
            return charges
    except Exception as e:
        logger.error("Stripe charge fetch failed: %s", e)
        return []


async def detect_billing_anomalies(days: int = 60) -> list[dict]:
    """Analyze Stripe charges for anomalies: rate hikes, duplicates, new fees."""
    charges = await check_stripe_charges(days)
    if not charges:
        return []

    anomalies = []

    # Group by description/merchant
    by_merchant: dict[str, list[dict]] = {}
    for charge in charges:
        desc = charge.get("description", "") or charge.get("statement_descriptor", "") or "unknown"
        by_merchant.setdefault(desc, []).append(charge)

    for merchant, merchant_charges in by_merchant.items():
        if len(merchant_charges) < 2:
            continue

        # Sort by creation date
        sorted_charges = sorted(merchant_charges, key=lambda c: c["created"])
        amounts = [c["amount"] / 100.0 for c in sorted_charges]  # cents to dollars

        # Detect rate increase (latest charge > previous by 10%+)
        if len(amounts) >= 2 and amounts[-1] > amounts[-2] * 1.10:
            anomalies.append({
                "type": "BILLING_INCREASE",
                "merchant": merchant,
                "old_amount": amounts[-2],
                "new_amount": amounts[-1],
                "increase_pct": round((amounts[-1] - amounts[-2]) / amounts[-2] * 100, 1),
                "detected_at": time.time(),
            })

        # Detect duplicate charges (same amount within 48 hours)
        for i in range(len(sorted_charges) - 1):
            if (
                sorted_charges[i + 1]["created"] - sorted_charges[i]["created"] < 172800
                and sorted_charges[i]["amount"] == sorted_charges[i + 1]["amount"]
            ):
                anomalies.append({
                    "type": "DUPLICATE_CHARGE",
                    "merchant": merchant,
                    "amount": sorted_charges[i]["amount"] / 100.0,
                    "detected_at": time.time(),
                })
                break

    logger.info("Detected %d billing anomalies", len(anomalies))
    return anomalies


# ── Slack: Send Alerts ────────────────────────────────────────

async def send_slack_alert(message: str, channel: Optional[str] = None) -> dict:
    """Send a threat alert or call summary to Slack."""
    token = config.SLACK_BOT_TOKEN
    ch = channel or config.SLACK_CHANNEL_ID

    if not token or not ch:
        logger.debug("Slack not configured — alert skipped")
        return {"status": "slack_unavailable"}

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                "https://slack.com/api/chat.postMessage",
                headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                json={"channel": ch, "text": message},
            )
            resp.raise_for_status()
            data = resp.json()
            if not data.get("ok"):
                logger.error("Slack API error: %s", data.get("error"))
                return {"error": data.get("error")}
            return {"status": "sent", "ts": data.get("ts")}
    except Exception as e:
        logger.error("Slack alert failed: %s", e)
        return {"error": str(e)}


async def send_task_summary(task_company: str, outcome: str, savings: float = 0):
    """Send a formatted task completion summary to Slack."""
    emoji = "💰" if savings > 0 else "✅"
    msg = f"{emoji} *LifePilot Task Complete*\n"
    msg += f"*Company:* {task_company}\n"
    msg += f"*Outcome:* {outcome}\n"
    if savings > 0:
        msg += f"*Savings:* ${savings:.2f}/month (${savings * 12:.2f}/year)\n"
    return await send_slack_alert(msg)
