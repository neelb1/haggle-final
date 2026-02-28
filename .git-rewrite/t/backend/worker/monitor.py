"""
LifePilot Background Monitor
Runs as a Render Background Worker (no execution time limit).

Loop:
1. Check Airbyte Stripe connector for billing anomalies
2. Check Overshoot for financial broadcast alerts
3. Check Tavily for relevant web mentions
4. Create tasks for detected threats
5. Optionally send Slack alerts
6. Sleep and repeat

Usage: python -m worker.monitor
"""

import asyncio
import logging
import os
import sys
import time

# Add parent directory to path so imports work
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

import config
from services import airbyte_service, overshoot_service, senso_service, tavily_service

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("lifepilot.monitor")

# How often to run the monitoring loop (seconds)
SCAN_INTERVAL = int(os.getenv("SCAN_INTERVAL", "900"))  # Default: 15 minutes


async def run_scan() -> list[dict]:
    """Run a single monitoring scan across all sources."""
    detections = []
    scan_start = time.time()

    # 1. Stripe billing anomalies
    if config.STRIPE_API_KEY:
        logger.info("Checking Stripe for billing anomalies...")
        try:
            anomalies = await airbyte_service.detect_billing_anomalies(days=60)
            for a in anomalies:
                classification = await senso_service.classify_threat(
                    f"{a['merchant']} {a['type']}: ${a.get('old_amount', '?')} -> ${a.get('new_amount', '?')}"
                )
                a["classification"] = classification
                a["source"] = "airbyte_stripe"
                detections.append(a)
        except Exception as e:
            logger.error("Stripe scan failed: %s", e)

    # 2. Overshoot financial broadcast monitoring
    if config.OVERSHOOT_API_KEY:
        logger.info("Checking Overshoot for financial broadcast alerts...")
        try:
            events = await overshoot_service.monitor_broadcast("latest")
            detections.extend(events)
        except Exception as e:
            logger.error("Overshoot scan failed: %s", e)

    # 3. Tavily web search for financial threats
    if config.TAVILY_API_KEY:
        logger.info("Checking Tavily for financial news...")
        try:
            result = tavily_service.search(
                "subscription price increases rate hikes 2026",
                max_results=3,
            )
            if result and "unavailable" not in result.lower():
                detections.append({
                    "source": "tavily_search",
                    "type": "WEB_MENTION",
                    "summary": result[:500],
                })
        except Exception as e:
            logger.error("Tavily scan failed: %s", e)

    scan_duration = time.time() - scan_start
    logger.info(
        "Scan complete: %d detections in %.1fs",
        len(detections),
        scan_duration,
    )

    # Send Slack summary if we found anything
    if detections and config.SLACK_BOT_TOKEN:
        msg = f"LifePilot Monitor: {len(detections)} anomalies detected in latest scan"
        await airbyte_service.send_slack_alert(msg)

    return detections


async def main():
    """Main monitoring loop. Runs forever on Render Background Worker."""
    logger.info("LifePilot Monitor starting up")
    logger.info("Scan interval: %ds", SCAN_INTERVAL)
    logger.info("Stripe: %s", "configured" if config.STRIPE_API_KEY else "not configured")
    logger.info("Overshoot: %s", "configured" if config.OVERSHOOT_API_KEY else "not configured")
    logger.info("Tavily: %s", "configured" if config.TAVILY_API_KEY else "not configured")
    logger.info("Slack: %s", "configured" if config.SLACK_BOT_TOKEN else "not configured")
    logger.info("Senso: %s", "configured" if config.SENSO_API_KEY else "not configured")

    # Seed Senso on first run
    await senso_service.seed_compliance_docs()

    while True:
        try:
            detections = await run_scan()
            if detections:
                logger.info("Detections: %s", detections)
        except Exception as e:
            logger.error("Monitor loop error: %s", e)

        logger.info("Sleeping %ds until next scan...", SCAN_INTERVAL)
        await asyncio.sleep(SCAN_INTERVAL)


if __name__ == "__main__":
    asyncio.run(main())
