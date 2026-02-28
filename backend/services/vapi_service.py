import logging

import httpx

import config

logger = logging.getLogger(__name__)

VAPI_BASE = "https://api.vapi.ai"

# ── Inline tool schemas for the user-consult assistant ──────
_SUBSCRIPTION_ANALYSIS_TOOL = {
    "type": "function",
    "function": {
        "name": "get_subscription_analysis",
        "description": "Get the full billing context and subscription analysis for the user.",
        "parameters": {"type": "object", "properties": {}, "required": []},
        "server": {"url": f"{config.BACKEND_URL}/api/vapi/tool-call"},
    },
}

_CONFIRM_ACTION_TOOL = {
    "type": "function",
    "function": {
        "name": "confirm_action",
        "description": "Record a confirmed action for a subscription service after the user agrees.",
        "parameters": {
            "type": "object",
            "properties": {
                "service":         {"type": "string", "description": "Name of the service (e.g. Comcast)"},
                "action":          {"type": "string", "enum": ["cancel_service", "negotiate_rate"]},
                "reason":          {"type": "string", "description": "Why this action makes sense"},
                "monthly_savings": {"type": "number", "description": "Estimated monthly savings in dollars"},
            },
            "required": ["service", "action", "reason", "monthly_savings"],
        },
        "server": {"url": f"{config.BACKEND_URL}/api/vapi/tool-call"},
    },
}

_COST_PER_USE_TOOL = {
    "type": "function",
    "function": {
        "name": "calculate_cost_per_use",
        "description": "Calculate cost per visit given a monthly subscription cost and visit frequency.",
        "parameters": {
            "type": "object",
            "properties": {
                "service":          {"type": "string"},
                "monthly_cost":     {"type": "number"},
                "visits_per_month": {"type": "number"},
            },
            "required": ["service", "monthly_cost", "visits_per_month"],
        },
        "server": {"url": f"{config.BACKEND_URL}/api/vapi/tool-call"},
    },
}


def _build_user_consult_prompt(context: dict) -> str:
    """Build the system prompt injected into the user-consult Vapi assistant."""
    summary = context.get("summary_text", "")
    user_name = context.get("user_name", "there")
    total_savings = context.get("total_potential_savings", 0)
    return f"""You are Haggle, an autonomous financial advocate AI. You are calling {user_name} by phone.

{summary}

YOUR GOAL:
1. Greet {user_name} briefly and explain you're calling about their bills.
2. Walk through each issue with specific dollar numbers.
3. For gym/fitness subscriptions, ask how often they actually go. Use calculate_cost_per_use if they give a frequency.
4. For billing increases, mention competitors' rates as leverage.
5. For each service where {user_name} agrees to act: call confirm_action immediately.
6. After all confirmations, tell them you'll handle everything and they'll get an email summary.

RULES:
- Be concise and conversational — this is a real phone call, keep it under 3 minutes.
- Always confirm explicitly before calling confirm_action ("Should I go ahead and cancel it?" → user says yes → call tool).
- Do not make up numbers. Use only the data above.
- If {user_name} says no to an action, respect it and move on.
- Potential savings: ${total_savings:.0f}/month if all actions confirmed."""


async def trigger_user_consult_call(
    phone: str,
    task_id: str,
    context: dict,
) -> dict:
    """
    Trigger a Vapi outbound call TO THE USER for subscription consultation.
    Uses an inline (ephemeral) assistant so the system prompt is dynamically
    built with the full billing context — no pre-configured assistant needed.
    """
    if not config.VAPI_API_KEY:
        return {"error": "VAPI_API_KEY not set"}
    if not config.VAPI_PHONE_NUMBER_ID:
        return {"error": "VAPI_PHONE_NUMBER_ID not set"}
    if not phone:
        return {"error": "USER_PHONE_NUMBER not set — add it to env vars"}

    system_prompt = _build_user_consult_prompt(context)

    payload = {
        "phoneNumberId": config.VAPI_PHONE_NUMBER_ID,
        "customer": {"number": phone},
        "assistant": {
            "name": "Haggle User Consult",
            "model": {
                "provider": "groq",
                "model": "llama-3.3-70b-versatile",
                "messages": [{"role": "system", "content": system_prompt}],
                "tools": [
                    _SUBSCRIPTION_ANALYSIS_TOOL,
                    _CONFIRM_ACTION_TOOL,
                    _COST_PER_USE_TOOL,
                ],
            },
            "voice": {
                "provider": "11labs",
                "voiceId": "21m00Tcm4TlvDq8ikWAM",  # ElevenLabs Rachel — clear, professional
            },
            "serverUrl": f"{config.BACKEND_URL}/api/vapi/webhook",
            "serverMessages": ["end-of-call-report", "transcript", "status-update"],
            "metadata": {"task_id": task_id, "call_type": "user_consult"},
        },
    }

    async with httpx.AsyncClient() as client:
        try:
            resp = await client.post(
                f"{VAPI_BASE}/call",
                json=payload,
                headers={
                    "Authorization": f"Bearer {config.VAPI_API_KEY}",
                    "Content-Type": "application/json",
                },
                timeout=15.0,
            )
            resp.raise_for_status()
            data = resp.json()
            logger.info("User consult call triggered: %s → %s", task_id, data.get("id"))
            return data
        except httpx.HTTPStatusError as e:
            logger.error("Vapi user consult call failed: %s %s", e.response.status_code, e.response.text)
            return {"error": e.response.text}
        except Exception as e:
            logger.error("Vapi user consult call error: %s", e)
            return {"error": str(e)}


async def trigger_outbound_call(
    phone_number: str,
    task_id: str,
    user_name: str = "Neel",
    company: str = "",
    objective: str = "",
    current_rate: float = 0,
    target_rate: float = 0,
    research_context: str = "",
) -> dict:
    """Trigger a Vapi outbound call with task-specific overrides."""
    if not config.VAPI_API_KEY:
        return {"error": "VAPI_API_KEY not set"}
    if not config.VAPI_PHONE_NUMBER_ID:
        return {"error": "VAPI_PHONE_NUMBER_ID not set — buy a number in Vapi dashboard"}

    payload = {
        "phoneNumberId": config.VAPI_PHONE_NUMBER_ID,
        "assistantId": config.VAPI_ASSISTANT_ID,
        "customer": {
            "number": phone_number,
            "numberE164CheckEnabled": False,
        },
        "assistantOverrides": {
            "variableValues": {
                "taskId": task_id,
                "customerName": user_name,
                "targetCompany": company,
                "objective": objective,
                "currentRate": str(current_rate),
                "targetRate": str(target_rate),
                "researchContext": research_context[:500],
            }
        },
    }

    async with httpx.AsyncClient() as client:
        try:
            resp = await client.post(
                f"{VAPI_BASE}/call/phone",
                json=payload,
                headers={
                    "Authorization": f"Bearer {config.VAPI_API_KEY}",
                    "Content-Type": "application/json",
                },
                timeout=15.0,
            )
            resp.raise_for_status()
            data = resp.json()
            logger.info("Outbound call triggered: %s", data.get("id"))
            return data
        except httpx.HTTPStatusError as e:
            logger.error("Vapi call failed: %s %s", e.response.status_code, e.response.text)
            return {"error": e.response.text}
        except Exception as e:
            logger.error("Vapi call error: %s", e)
            return {"error": str(e)}


async def update_assistant_server_url(new_url: str) -> dict:
    """Update the assistant's server URL (used after Render deploy)."""
    if not config.VAPI_API_KEY:
        return {"error": "VAPI_API_KEY not set"}

    async with httpx.AsyncClient() as client:
        try:
            resp = await client.patch(
                f"{VAPI_BASE}/assistant/{config.VAPI_ASSISTANT_ID}",
                json={"serverUrl": f"{new_url}/api/vapi/webhook"},
                headers={
                    "Authorization": f"Bearer {config.VAPI_API_KEY}",
                    "Content-Type": "application/json",
                },
                timeout=10.0,
            )
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.error("Failed to update assistant URL: %s", e)
            return {"error": str(e)}


async def update_tool_server_urls(new_url: str) -> list[dict]:
    """Update all 5 tool server URLs to point to new backend."""
    tool_ids = config.VAPI_TOOL_IDS
    if not tool_ids:
        logger.warning("VAPI_TOOL_IDS not set — skipping tool URL updates")
        return []
    results = []
    async with httpx.AsyncClient() as client:
        for tool_id in tool_ids:
            try:
                resp = await client.patch(
                    f"{VAPI_BASE}/tool/{tool_id}",
                    json={"server": {"url": f"{new_url}/api/vapi/tool-call"}},
                    headers={
                        "Authorization": f"Bearer {config.VAPI_API_KEY}",
                        "Content-Type": "application/json",
                    },
                    timeout=10.0,
                )
                resp.raise_for_status()
                results.append({"tool_id": tool_id, "status": "updated"})
            except Exception as e:
                results.append({"tool_id": tool_id, "error": str(e)})
    return results
