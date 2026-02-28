"""
Fastino GLiNER2 Integration
- Zero-shot entity extraction from call transcripts (205M params, CPU)
- Structured JSON extraction for negotiation results
- Replaces/augments LLM-based extract_entities with faster specialized model

Prize criteria: "Best and creative usage of Pioneer fine-tuning tool" + GLiNER F1 score
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Lazy-loaded model singleton
_extractor = None

# Financial entity schema with descriptions for higher accuracy
FINANCIAL_ENTITY_SCHEMA = {
    "confirmation_number": "Reference numbers, confirmation codes, ticket IDs, case numbers",
    "dollar_amount": "Monetary values: monthly rates, fees, charges, savings amounts with $ symbol",
    "date": "Dates: billing cycles, contract expiration, effective dates, months, years",
    "account_number": "Customer account numbers, member IDs, subscriber IDs",
    "company_name": "Service providers, ISPs, gyms, telecom companies mentioned",
    "phone_number": "Phone numbers for callbacks, transfers, specific departments",
    "contract_term": "Contract durations like '12 months', '2 year agreement', 'no contract'",
    "promotional_rate": "Special offers, promotional pricing, limited-time deals, intro rates",
    "penalty_fee": "Early termination fees, cancellation fees, late payment fees, annual fees",
    "person_name": "Names of customer service reps, managers, supervisors spoken to",
}

# Simpler schema for real-time mid-call extraction (fewer labels = faster)
REALTIME_ENTITY_SCHEMA = {
    "confirmation_number": "Reference numbers, confirmation codes, case numbers",
    "dollar_amount": "Monetary values with $ symbol",
    "account_number": "Customer account or member IDs",
    "person_name": "Names of reps or managers",
}


def get_extractor():
    """Lazy-load GLiNER2 model. Loads once (~2s on CPU), reuses across requests."""
    global _extractor
    if _extractor is None:
        try:
            from gliner2 import GLiNER2
            _extractor = GLiNER2.from_pretrained("fastino/gliner2-base-v1")
            logger.info("GLiNER2 model loaded successfully (205M params)")
        except ImportError:
            logger.warning("gliner2 package not installed — run: pip install gliner2")
            return None
        except Exception as e:
            logger.error("GLiNER2 model load failed: %s", e)
            return None
    return _extractor


def extract_financial_entities(text: str, realtime: bool = False) -> dict:
    """
    Extract financial entities from transcript text using GLiNER2.

    Args:
        text: Transcript text to extract from
        realtime: If True, use smaller schema for faster mid-call extraction

    Returns:
        {
            "entities": {
                "dollar_amount": [{"text": "$85", "confidence": 0.95, "start": 42, "end": 45}],
                "confirmation_number": [{"text": "XR-7742", "confidence": 0.92, ...}],
                ...
            },
            "source": "gliner2"
        }
    """
    extractor = get_extractor()
    if not extractor:
        return {"entities": {}, "source": "unavailable"}

    schema = REALTIME_ENTITY_SCHEMA if realtime else FINANCIAL_ENTITY_SCHEMA

    try:
        result = extractor.extract_entities(
            text,
            schema,
            include_confidence=True,
            include_spans=True,
        )
        return {**result, "source": "gliner2"}
    except Exception as e:
        logger.error("GLiNER2 extraction failed: %s", e)
        return {"entities": {}, "source": "error", "error": str(e)}


def extract_negotiation_result(transcript: str) -> dict:
    """
    Extract structured negotiation outcome from the full call transcript.
    Uses GLiNER2's JSON extraction mode for structured output.

    Returns:
        {
            "company": "Comcast",
            "original_rate": "$85",
            "new_rate": "$55",
            "confirmation": "XR-7742",
            "effective_date": "next billing cycle",
            "duration": "12 months",
            "outcome": "success"
        }
    """
    extractor = get_extractor()
    if not extractor:
        return {}

    try:
        result = extractor.extract_json(
            transcript,
            {
                "negotiation_result": [
                    "company::str::Service provider or company name",
                    "original_rate::str::Original monthly rate before negotiation",
                    "new_rate::str::New negotiated monthly rate",
                    "confirmation::str::Confirmation or reference number given by rep",
                    "effective_date::str::When the new rate takes effect",
                    "duration::str::How long the promotional rate lasts",
                    "outcome::[success|partial|failed]::str",
                ]
            },
        )
        results_list = result.get("negotiation_result", [])
        return results_list[0] if results_list else {}
    except Exception as e:
        logger.error("GLiNER2 JSON extraction failed: %s", e)
        return {}


def batch_extract_from_chunks(chunks: list[str]) -> list[dict]:
    """Batch entity extraction across multiple transcript chunks."""
    extractor = get_extractor()
    if not extractor or not chunks:
        return [{"entities": {}} for _ in chunks]

    try:
        return extractor.batch_extract_entities(
            chunks,
            FINANCIAL_ENTITY_SCHEMA,
            batch_size=8,
        )
    except Exception as e:
        logger.error("GLiNER2 batch extraction failed: %s", e)
        return [{"entities": {}} for _ in chunks]


def flatten_entities(result: dict) -> list[tuple[str, str, float]]:
    """
    Flatten GLiNER2 result into [(entity_type, value, confidence), ...] tuples.
    Useful for storing in Neo4j and pushing to SSE.
    """
    flat = []
    for entity_type, values in result.get("entities", {}).items():
        for v in values:
            if isinstance(v, dict):
                flat.append((entity_type, v.get("text", ""), v.get("confidence", 0.0)))
            else:
                flat.append((entity_type, str(v), 1.0))
    return flat
