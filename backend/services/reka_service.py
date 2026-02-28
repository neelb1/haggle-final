"""
Reka Vision Integration
- Analyze bill images for hidden fees, rate increases, unexpected charges
- Compare bills month-over-month to detect changes
- Extract structured financial data from PDFs and screenshots
- Feed extracted data into Neo4j and auto-create negotiation tasks

Models: reka-flash-3 (fast, cheap) | reka-core (high quality)
Content types: image_url, video_url, audio_url, pdf_url
"""

import json
import logging
from typing import Optional

import config

logger = logging.getLogger(__name__)

_client = None


def get_client():
    """Lazy-init async Reka client."""
    global _client
    if _client is None and config.REKA_API_KEY:
        try:
            from reka.client import AsyncReka
            _client = AsyncReka(api_key=config.REKA_API_KEY)
            logger.info("Reka Vision async client initialized")
        except ImportError:
            logger.warning("reka-api package not installed — run: pip install reka-api")
        except Exception as e:
            logger.error("Reka client init failed: %s", e)
    return _client


def _parse_json_response(content: str) -> dict:
    """Try to parse JSON from Reka response, handling markdown code blocks."""
    text = content.strip()
    if text.startswith("```json"):
        text = text[7:]
    elif text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    text = text.strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {"raw_analysis": content}


async def analyze_bill_image(image_url: str) -> dict:
    """
    Analyze a bill/statement image and extract structured financial data.

    Returns:
        {
            "provider_name": "Comcast",
            "total_amount": "$127.43",
            "line_items": [{"description": "Internet", "amount": "$89.99"}, ...],
            "fees": [{"description": "Broadcast TV Fee", "amount": "$21.00"}, ...],
            "previous_amount": "$105.00",
            "price_change": "+$22.43",
            "promotional_expiry": "2025-03-01",
            "hidden_fees": ["Regional Sports Fee: $12.44 (new this month)"]
        }
    """
    client = get_client()
    if not client:
        return {"status": "reka_unavailable", "error": "Reka API key not configured or reka-api not installed"}

    try:
        response = await client.chat.create(
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "image_url", "image_url": image_url},
                        {
                            "type": "text",
                            "text": (
                                "Analyze this bill or statement image. Extract and return as JSON with these fields:\n"
                                '- "provider_name": string, the service provider\n'
                                '- "total_amount": string, total amount due with $ sign\n'
                                '- "line_items": array of {"description": string, "amount": string} for each charge\n'
                                '- "fees": array of {"description": string, "amount": string} for surcharges, regulatory fees, taxes\n'
                                '- "previous_amount": string or null, previous bill amount if visible\n'
                                '- "price_change": string or null, increase/decrease amount if detectable\n'
                                '- "promotional_expiry": string or null, any promo expiration dates\n'
                                '- "hidden_fees": array of strings, any fees that seem unusual or recently added\n'
                                "Return ONLY valid JSON, no markdown formatting."
                            ),
                        },
                    ],
                }
            ],
            model="reka-flash-3",
        )
        content = response.responses[0].message.content
        return _parse_json_response(content)
    except Exception as e:
        logger.error("Reka bill analysis failed: %s", e)
        return {"error": str(e)}


async def compare_bills(image_url_old: str, image_url_new: str) -> dict:
    """
    Compare two bill images to detect price changes, new fees, expired discounts.
    """
    client = get_client()
    if not client:
        return {"status": "reka_unavailable", "error": "Reka API key not configured or reka-api not installed"}

    try:
        response = await client.chat.create(
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "image_url", "image_url": image_url_old},
                        {"type": "image_url", "image_url": image_url_new},
                        {
                            "type": "text",
                            "text": (
                                "Compare these two bills from the same provider (first is older, second is newer). "
                                "Return as JSON:\n"
                                '- "provider_name": string\n'
                                '- "old_total": string with $\n'
                                '- "new_total": string with $\n'
                                '- "price_change": string with +/- and $\n'
                                '- "change_percentage": string with %\n'
                                '- "new_fees": array of strings for any new fees or charges added\n'
                                '- "removed_discounts": array of strings for any discounts that expired\n'
                                '- "action_recommended": string, what the consumer should do about changes\n'
                                "Return ONLY valid JSON."
                            ),
                        },
                    ],
                }
            ],
            model="reka-flash-3",
        )
        content = response.responses[0].message.content
        return _parse_json_response(content)
    except Exception as e:
        logger.error("Reka bill comparison failed: %s", e)
        return {"error": str(e)}


async def analyze_document(document_url: str, doc_type: str = "pdf") -> dict:
    """
    Analyze a financial document (PDF statement, contract, terms of service).
    """
    client = get_client()
    if not client:
        return {"status": "reka_unavailable", "error": "Reka API key not configured or reka-api not installed"}

    content_key = "pdf_url" if doc_type == "pdf" else "image_url"

    try:
        response = await client.chat.create(
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": content_key, content_key: document_url},
                        {
                            "type": "text",
                            "text": (
                                "Analyze this financial document thoroughly. Extract as JSON:\n"
                                '- "document_type": string (bill, contract, terms, statement)\n'
                                '- "provider_name": string\n'
                                '- "monthly_charges": array of {"item": string, "amount": string}\n'
                                '- "contract_term": string or null (e.g., "24 months")\n'
                                '- "contract_expiry": string or null\n'
                                '- "early_termination_fee": string or null\n'
                                '- "promotional_rates": array of {"rate": string, "expires": string}\n'
                                '- "consumer_leverage_points": array of strings (clauses that favor the consumer for negotiation)\n'
                                "Return ONLY valid JSON."
                            ),
                        },
                    ],
                }
            ],
            model="reka-flash-3",
        )
        content = response.responses[0].message.content
        return _parse_json_response(content)
    except Exception as e:
        logger.error("Reka document analysis failed: %s", e)
        return {"error": str(e)}
