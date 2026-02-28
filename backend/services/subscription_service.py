"""
Subscription Context Service
Builds the billing analysis object injected into the Vapi user-consult prompt
and returned by the get_subscription_analysis tool.

Primary source: Neo4j knowledge graph (live rates, updated after each negotiation).
Fallback: hardcoded demo data when Neo4j is not configured.

Neo4j provides:  service name, service type, current rate, previous rate
Metadata catalog provides: phone number, anomaly description, competitor rates,
                            day-pass cost, recommended action, potential savings
"""

from services.neo4j_service import neo4j_service

# ── Supplemental metadata not stored in Neo4j ────────────────
# Keyed by lowercase service name for fuzzy matching.
_SERVICE_METADATA: dict[str, dict] = {
    "comcast": {
        "phone_number": "+18005551234",
        "anomaly": "54% billing increase detected — promotional rate expired",
        "competitor_note": "T-Mobile 5G Home at $50/mo, AT&T Fiber at $55/mo",
        "recommended_action": "negotiate_rate",
        "target_savings_pct": 0.24,   # aim to save ~24% off current rate
    },
    "planet fitness": {
        "phone_number": "+18005555678",
        "anomaly": "Rate jumped from $10 to $25/mo (Black Card upgrade)",
        "day_pass_cost": 10.0,
        "usage_note": "No check-ins detected in last 3 months",
        "recommended_action": "cancel_service",
        "target_savings_pct": 1.0,    # full cancellation
    },
}

# Hardcoded fallback used only when Neo4j is unavailable
_FALLBACK_SUBSCRIPTIONS: list[dict] = [
    {
        "service": "Comcast",
        "service_type": "internet",
        "monthly_cost": 85.0,
        "previous_cost": 55.0,
    },
    {
        "service": "Planet Fitness",
        "service_type": "gym",
        "monthly_cost": 25.0,
        "previous_cost": 10.0,
    },
]


def build_subscription_context(user_name: str = "Neel") -> dict:
    """
    Returns the full billing context used in two places:
      1. Injected into the Vapi user-consult system prompt at call creation.
      2. Returned by the get_subscription_analysis tool during the call.

    Reads live rates from Neo4j. Falls back to hardcoded data if unavailable.
    """
    raw = neo4j_service.get_subscription_profile(user_name)
    source = "neo4j" if raw else "fallback"
    if not raw:
        raw = _FALLBACK_SUBSCRIPTIONS

    subscriptions = [_enrich(s) for s in raw]

    total_monthly = sum(s["monthly_cost"] for s in subscriptions)
    total_savings = sum(s["potential_savings"] for s in subscriptions)

    return {
        "user_name": user_name,
        "subscriptions": subscriptions,
        "total_monthly": total_monthly,
        "total_potential_savings": total_savings,
        "source": source,
        "summary_text": _build_summary_text(user_name, total_monthly, total_savings, subscriptions),
    }


def _enrich(raw: dict) -> dict:
    """Merge a Neo4j subscription record with its supplemental metadata."""
    key = raw["service"].lower()
    meta = _SERVICE_METADATA.get(key, {})

    monthly_cost = raw["monthly_cost"]
    previous_cost = raw.get("previous_cost")

    # Compute potential savings
    savings_pct = meta.get("target_savings_pct", 0.20)
    potential_savings = round(monthly_cost * savings_pct, 2)

    # Anomaly: use metadata if present, otherwise infer from rate change
    anomaly = meta.get("anomaly", "")
    if not anomaly and previous_cost and previous_cost < monthly_cost:
        pct = round((monthly_cost - previous_cost) / previous_cost * 100, 1)
        anomaly = f"{pct}% rate increase detected (${previous_cost:.0f} → ${monthly_cost:.0f})"

    return {
        "service": raw["service"],
        "service_type": raw.get("service_type", "subscription"),
        "monthly_cost": monthly_cost,
        "previous_cost": previous_cost,
        "anomaly": anomaly,
        "recommended_action": meta.get("recommended_action", "negotiate_rate"),
        "phone_number": meta.get("phone_number", "+18005551234"),
        "potential_savings": potential_savings,
        "day_pass_cost": meta.get("day_pass_cost"),
        "competitor_note": meta.get("competitor_note", ""),
        "usage_note": meta.get("usage_note", ""),
    }


def _build_summary_text(
    user_name: str,
    total_monthly: float,
    total_savings: float,
    subscriptions: list[dict],
) -> str:
    lines = [
        f"SUBSCRIPTION ANALYSIS FOR {user_name.upper()} (live from knowledge graph)",
        f"Total monthly spend: ${total_monthly:.0f}/mo",
        f"Identified potential savings: ${total_savings:.0f}/mo (${total_savings * 12:.0f}/yr)",
        "",
        "ISSUES FOUND:",
    ]
    for s in subscriptions:
        line = f"• {s['service']} — ${s['monthly_cost']:.0f}/mo"
        if s.get("anomaly"):
            line += f" | {s['anomaly']}"
        if s.get("usage_note"):
            line += f" | {s['usage_note']}"
        if s.get("competitor_note"):
            line += f" | Competitors: {s['competitor_note']}"
        if s.get("day_pass_cost"):
            line += f" | Day pass: ${s['day_pass_cost']:.0f}"
        lines.append(line)
    return "\n".join(lines)


def get_subscription_by_service(service_name: str) -> dict | None:
    """Look up enriched subscription metadata by (case-insensitive) service name."""
    ctx = build_subscription_context()
    name_lower = service_name.lower()
    for s in ctx["subscriptions"]:
        if s["service"].lower() in name_lower or name_lower in s["service"].lower():
            return s
    return None
