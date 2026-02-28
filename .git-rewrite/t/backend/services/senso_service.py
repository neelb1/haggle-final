"""
Senso Context OS Integration
- Ingest compliance docs + resolution scripts
- Search verified knowledge before/during calls
- Generate grounded call scripts
- Classify threats via triggers
"""

import logging

import httpx

import config

logger = logging.getLogger(__name__)


def _headers() -> dict:
    return {
        "X-API-Key": config.SENSO_API_KEY,
        "Content-Type": "application/json",
    }


@property
def available() -> bool:
    return bool(config.SENSO_API_KEY)


async def ingest_content(title: str, text: str) -> dict:
    """Ingest compliance docs / resolution scripts into Senso."""
    if not config.SENSO_API_KEY:
        return {"status": "senso_unavailable"}
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                f"{config.SENSO_BASE_URL}/content/raw",
                headers=_headers(),
                json={"title": title, "summary": title, "text": text},
            )
            resp.raise_for_status()
            return resp.json()
    except Exception as e:
        logger.error("Senso ingest failed: %s", e)
        return {"error": str(e)}


async def search_knowledge(query: str, max_results: int = 3) -> str:
    """Query Senso for verified, grounded context. Returns single-line string for Vapi."""
    if not config.SENSO_API_KEY:
        return ""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                f"{config.SENSO_BASE_URL}/search",
                headers=_headers(),
                json={"query": query, "max_results": max_results},
            )
            resp.raise_for_status()
            data = resp.json()
            answer = data.get("answer", "")
            sources = data.get("results", [])
            if sources:
                citations = " | ".join(s.get("title", "") for s in sources[:2])
                answer = f"{answer} [Sources: {citations}]"
            return answer.replace("\n", " ").strip()
    except Exception as e:
        logger.error("Senso search failed: %s", e)
        return ""


async def generate_script(company: str, action: str, context: str = "") -> str:
    """Generate a call script grounded in ingested knowledge."""
    if not config.SENSO_API_KEY:
        return ""
    instructions = (
        f"Generate a professional phone call script for a representative calling "
        f"{company} to {action.replace('_', ' ')}. "
        f"The script should be concise, cite specific policies where available, "
        f"and include fallback strategies if the first approach is refused. "
        f"Additional context: {context}"
    )
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                f"{config.SENSO_BASE_URL}/generate",
                headers=_headers(),
                json={
                    "content_type": "call_script",
                    "instructions": instructions,
                    "max_results": 3,
                },
            )
            resp.raise_for_status()
            return resp.json().get("content", "")
    except Exception as e:
        logger.error("Senso generate failed: %s", e)
        return ""


async def classify_threat(text: str) -> str:
    """Use Senso triggers to classify threat type."""
    if not config.SENSO_API_KEY:
        return "unknown"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                f"{config.SENSO_BASE_URL}/triggers",
                headers=_headers(),
                json={"text": text},
            )
            resp.raise_for_status()
            return resp.json().get("classification", "unknown")
    except Exception as e:
        logger.error("Senso classify failed: %s", e)
        return "unknown"


async def seed_compliance_docs():
    """Ingest common compliance/negotiation docs on startup."""
    if not config.SENSO_API_KEY:
        logger.warning("SENSO_API_KEY not set — Context OS features disabled")
        return

    docs = [
        {
            "title": "Comcast Retention Playbook",
            "text": (
                "Comcast retention department has authority to offer: 1) Promotional rate "
                "matching for existing customers, typically $20-30/month discount for 12 months. "
                "2) Free speed upgrade to match competitor offerings. 3) Waived equipment fees "
                "for 6-12 months. Key leverage: mention T-Mobile 5G Home Internet at $50/month "
                "or AT&T Fiber promotional rates. If first rep refuses, ask to speak with "
                "retention specialist. Average call time: 15-25 minutes. Success rate for "
                "rate reduction: approximately 73% when competitor rates are cited."
            ),
        },
        {
            "title": "Planet Fitness Cancellation Policy",
            "text": (
                "Planet Fitness cancellation requires: 1) Written letter sent to home club via "
                "certified mail, OR 2) In-person visit to home club to fill out cancellation form. "
                "Phone cancellation is NOT officially supported but some clubs accept it when "
                "pressed. Annual fee ($49) is non-refundable if charged within 30 days. "
                "Monthly dues stop after next billing cycle. If calling: request manager, "
                "cite FTC guidelines on subscription cancellation, reference your state's "
                "consumer protection laws. Keep confirmation number and rep name."
            ),
        },
        {
            "title": "General Bill Negotiation Framework",
            "text": (
                "Step 1: State current rate and desired rate clearly. "
                "Step 2: Cite specific competitor offers with prices. "
                "Step 3: If refused, ask to speak with retention/loyalty department. "
                "Step 4: If still refused, state intent to cancel service. "
                "Step 5: Accept any counter-offer within 15% of target rate. "
                "Step 6: Always get confirmation number and effective date. "
                "Step 7: Verify changes will appear on next billing statement. "
                "Key phrases: 'I've been a loyal customer for X years', "
                "'I've found a better rate with [competitor]', "
                "'Can you match this offer or should I proceed with cancellation?'"
            ),
        },
    ]

    for doc in docs:
        result = await ingest_content(doc["title"], doc["text"])
        logger.info("Senso ingested '%s': %s", doc["title"], result.get("status", result))
