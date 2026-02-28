"""
Vapi Tool Call Handler
POST /api/vapi/tool-call

Vapi sends tool-calls here when the voice agent invokes any of the 5 tools.
We route by function name, execute, and return results.

CRITICAL FORMAT (from Vapi docs):
- Request: message.toolCallList[].{id, name, arguments}
- Response: {"results": [{"name": "x", "toolCallId": "y", "result": "single-line string"}]}
- Always return HTTP 200
- result and error must be single-line strings
"""

import json
import logging

from fastapi import APIRouter, Request

from models.schemas import SSEEvent, SSEEventType, ConfirmedAction
from services.task_store import store
from services import tavily_service, senso_service, airbyte_service, subscription_service
from services.neo4j_service import neo4j_service

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/api/vapi/tool-call")
async def handle_tool_call(request: Request):
    body = await request.json()
    message = body.get("message", {})
    tool_call_list = message.get("toolCallList", [])
    call_obj = message.get("call", {})
    call_id = call_obj.get("id", "unknown")

    results = []

    for tool_call in tool_call_list:
        tc_id = tool_call.get("id", "")
        # Vapi nests name/arguments under "function" key
        func = tool_call.get("function", {})
        tc_name = func.get("name", "") or tool_call.get("name", "")
        args = func.get("arguments", {}) or tool_call.get("arguments", {})
        if isinstance(args, str):
            try:
                args = json.loads(args)
            except json.JSONDecodeError:
                args = {}

        logger.info("Tool call: %s (id=%s) args=%s", tc_name, tc_id, args)

        # Push tool call badge to dashboard live feed
        await store.push_event(SSEEvent(
            type=SSEEventType.TOOL_CALL,
            data={
                "call_id": call_id,
                "tool": tc_name,
                "arguments": {k: str(v)[:100] for k, v in args.items()},
            },
        ))

        try:
            result = await _dispatch_tool(tc_name, args, call_id)
        except Exception as e:
            logger.error("Tool %s failed: %s", tc_name, e)
            result = f"Error: {str(e)}"

        # Ensure single-line string
        result_str = str(result).replace("\n", " ").replace("\r", "")

        results.append({
            "name": tc_name,
            "toolCallId": tc_id,
            "result": result_str,
        })

    return {"results": results}


async def _dispatch_tool(name: str, args: dict, call_id: str) -> str:
    """Route tool call to the correct handler."""

    if name == "search_task_context":
        return await _handle_search_task_context(args, call_id)
    elif name == "tavily_search":
        return await _handle_tavily_search(args)
    elif name == "extract_entities":
        return await _handle_extract_entities(args, call_id)
    elif name == "update_neo4j":
        return await _handle_update_neo4j(args, call_id)
    elif name == "end_task":
        return await _handle_end_task(args, call_id)
    elif name == "get_subscription_analysis":
        return _handle_get_subscription_analysis()
    elif name == "confirm_action":
        return await _handle_confirm_action(args, call_id)
    elif name == "calculate_cost_per_use":
        return _handle_calculate_cost_per_use(args)
    else:
        return f"Unknown tool: {name}"


# ── Tool Handlers ────────────────────────────────────────────


async def _handle_search_task_context(args: dict, call_id: str) -> str:
    """Return task details so the agent knows what to do. Fast — no external API calls."""
    task_id = args.get("task_id", "")

    # Try to find by exact ID first
    task = store.get_task(task_id)

    # If not found, find the first task that's currently calling
    if not task:
        for t in store.list_tasks():
            if t.call_id == call_id or t.status == "calling":
                task = t
                break

    # Last resort: return first pending task
    if not task:
        tasks = store.list_tasks()
        task = tasks[0] if tasks else None

    if not task:
        return "No task found. Ask the customer how you can help them."

    # Link call to task
    store.update_task(task.id, call_id=call_id)

    context = (
        f"Task: {task.action.value} for {task.company}. "
        f"Client: {task.user_name}. "
    )
    if task.current_rate:
        context += f"Current rate: ${task.current_rate}/month. "
    if task.target_rate:
        context += f"Target rate: ${task.target_rate}/month. "
    if task.notes:
        context += f"Notes: {task.notes} "
    if task.research_context:
        context += f"Research: {task.research_context} "

    # NOTE: Senso search removed from hot path — was adding 2-10s latency per tool call.
    # Context is now pre-baked into the system prompt and task research_context field.

    return context


async def _handle_tavily_search(args: dict) -> str:
    """Web search via Tavily."""
    query = args.get("query", "")
    if not query:
        return "No search query provided."
    return tavily_service.search(query)


async def _handle_extract_entities(args: dict, call_id: str) -> str:
    """Extract and store entities from the call. Fast path — no external API calls."""
    entity_type = args.get("entity_type", "other")
    value = args.get("value", "")
    context = args.get("context", "")

    if not value:
        return "No value provided."

    # Store in Neo4j graph
    neo4j_service.add_entity(entity_type, value, context, call_id)

    # Update the linked task
    for task in store.list_tasks():
        if task.call_id == call_id:
            if entity_type == "confirmation_number":
                store.update_task(task.id, confirmation_number=value)
            elif entity_type == "price":
                store.update_task(task.id, outcome=f"New rate: {value}")
            break

    # Push to SSE for dashboard
    await store.push_event(SSEEvent(
        type=SSEEventType.ENTITY_EXTRACTED,
        data={
            "entity_type": entity_type,
            "value": value,
            "context": context,
            "call_id": call_id,
        },
    ))

    return f"Logged {entity_type}: {value}"


async def _handle_update_neo4j(args: dict, call_id: str) -> str:
    """Update the knowledge graph."""
    action = args.get("action", "")
    service_name = args.get("service_name", "")
    details_raw = args.get("details", "{}")

    try:
        details = json.loads(details_raw) if isinstance(details_raw, str) else details_raw
    except json.JSONDecodeError:
        details = {"raw": details_raw}

    if action == "cancel_service":
        result = neo4j_service.cancel_service(
            user_name="Neel",
            service_name=service_name,
            confirmation=details.get("confirmation", ""),
        )
    elif action == "negotiate_rate":
        result = neo4j_service.update_service_rate(
            service_name=service_name,
            old_rate=float(details.get("old_rate", 0)),
            new_rate=float(details.get("new_rate", 0)),
            confirmation=details.get("confirmation", ""),
        )
    elif action == "update_status":
        result = neo4j_service.update_status(service_name, str(details))
    else:
        result = neo4j_service.update_status(service_name, str(details))

    # Push graph update to SSE
    await store.push_event(SSEEvent(
        type=SSEEventType.GRAPH_UPDATED,
        data={"action": action, "service": service_name, "details": details},
    ))

    return f"Graph updated: {action} for {service_name}. {json.dumps(result)}"


async def _handle_end_task(args: dict, call_id: str) -> str:
    """Mark task complete, notify via Slack, prepare for call end."""
    status = args.get("status", "completed")
    summary = args.get("summary", "")

    # Find and update the task
    for task in store.list_tasks():
        if task.call_id == call_id:
            new_status = {
                "completed": "completed",
                "failed": "failed",
                "needs_followup": "needs_followup",
                "transferred": "needs_followup",
            }.get(status, "completed")

            store.update_task(task.id, status=new_status, outcome=summary)
            await store.push_task_update(task)

            # Send completion alert to Slack via Airbyte connector
            savings = task.savings or 0
            await airbyte_service.send_task_summary(task.company, summary, savings)
            break

    return f"Task marked as {status}. {summary}"


# ── User Consult Tool Handlers ───────────────────────────────

def _handle_get_subscription_analysis() -> str:
    """Return the full billing context so the agent can present findings to the user."""
    ctx = subscription_service.build_subscription_context()
    subs = ctx["subscriptions"]
    lines = [ctx["summary_text"], "", "DETAILS:"]
    for s in subs:
        line = f"{s['service']}: ${s['monthly_cost']:.0f}/mo"
        if s.get("previous_cost"):
            line += f" (was ${s['previous_cost']:.0f})"
        if s.get("anomaly"):
            line += f" — {s['anomaly']}"
        if s.get("competitor_note"):
            line += f" | Competitors: {s['competitor_note']}"
        if s.get("day_pass_cost"):
            line += f" | Day pass: ${s['day_pass_cost']:.0f}"
        lines.append(line)
    lines.append(f"Total potential savings: ${ctx['total_potential_savings']:.0f}/mo")
    return " | ".join(lines)


async def _handle_confirm_action(args: dict, call_id: str) -> str:
    """Record a user-confirmed action and push it to the dashboard via SSE."""
    service = args.get("service", "")
    action = args.get("action", "")
    reason = args.get("reason", "")
    monthly_savings = float(args.get("monthly_savings", 0))

    if not service or not action:
        return "Missing service or action — cannot confirm."

    # Look up phone number from subscription catalog
    sub = subscription_service.get_subscription_by_service(service)
    phone = sub["phone_number"] if sub else "+18005551234"

    confirmed = ConfirmedAction(
        service=service,
        action=action,
        reason=reason,
        monthly_savings=monthly_savings,
        phone_number=phone,
    )
    store.add_confirmed_action(confirmed)

    # Push SSE so dashboard shows confirmed action in real-time
    await store.push_event(SSEEvent(
        type=SSEEventType.TASK_UPDATED,
        data={
            "confirmed_action": {
                "service": service,
                "action": action,
                "reason": reason,
                "monthly_savings": monthly_savings,
            },
            "call_id": call_id,
            "message": f"User confirmed: {action.replace('_', ' ')} {service} — saves ${monthly_savings:.0f}/mo",
        },
    ))

    logger.info("Confirmed action stored: %s %s saves=$%.0f", action, service, monthly_savings)
    return f"Confirmed: will {action.replace('_', ' ')} {service}. Saves ${monthly_savings:.0f}/mo. I'll take care of this right after our call."


def _handle_calculate_cost_per_use(args: dict) -> str:
    """Calculate cost-per-visit and compare against alternatives."""
    service = args.get("service", "service")
    monthly_cost = float(args.get("monthly_cost", 0))
    visits = float(args.get("visits_per_month", 1))

    if visits <= 0:
        return f"{service}: With 0 visits, you're paying ${monthly_cost:.0f}/mo for nothing."

    cost_per_visit = monthly_cost / visits

    # Look up day-pass cost if known
    sub = subscription_service.get_subscription_by_service(service)
    day_pass = sub.get("day_pass_cost") if sub else None

    result = f"{service}: ${monthly_cost:.0f}/mo ÷ {visits:.0f} visits = ${cost_per_visit:.2f}/visit."
    if day_pass:
        if cost_per_visit > day_pass:
            result += f" Day pass is ${day_pass:.0f} — you're overpaying by ${cost_per_visit - day_pass:.2f}/visit. Not worth the subscription."
        else:
            result += f" Day pass is ${day_pass:.0f} — the subscription is actually saving you ${day_pass - cost_per_visit:.2f}/visit. Worth keeping."
    return result
