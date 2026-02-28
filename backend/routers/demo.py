"""
Demo Simulation Endpoints
- POST /api/demo/run    -- Run a full simulated agent loop with realistic SSE events
- POST /api/demo/reset  -- Reset all tasks to pending and re-seed the Neo4j graph
- GET  /api/demo/stats  -- Return aggregate demo statistics
"""

import asyncio
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException

from models.schemas import (
    SSEEvent,
    SSEEventType,
    TaskStatus,
)
from services.task_store import store
from services.neo4j_service import neo4j_service
from services import tavily_service, gmail_service, senso_service

logger = logging.getLogger(__name__)
router = APIRouter()

# ── Simulated call ID generator ─────────────────────────────

def _generate_call_id() -> str:
    return f"call_{uuid.uuid4().hex[:12]}"


def _generate_confirmation() -> str:
    return f"CNF-2026-{uuid.uuid4().hex[:4].upper()}"


# ── Transcript Scripts ───────────────────────────────────────
# Each entry: (role, text, optional delay_before in seconds)

def _build_comcast_negotiation_script(
    user_name: str,
    current_rate: float,
    target_rate: float,
    competitor_intel: str,
    confirmation_number: str,
) -> list[tuple[str, str, float]]:
    """Build a realistic Comcast retention department transcript."""
    return [
        (
            "agent",
            f"Hi, this is Haggle calling on behalf of {user_name}. "
            f"I'm reaching out about account holder {user_name}'s internet service. "
            f"Could I speak with someone in your retention or loyalty department?",
            1.5,
        ),
        (
            "human",
            "Thank you for calling Comcast. This is Marcus in our customer loyalty department. "
            "I can see the account here. How can I help you today?",
            2.0,
        ),
        (
            "agent",
            f"Thanks Marcus. I'm calling because {user_name}'s monthly bill has increased "
            f"from $55 to ${current_rate:.0f} per month, which is a significant jump. "
            f"{user_name} has been a loyal Comcast customer and we'd like to discuss "
            f"getting the rate back to something more reasonable.",
            1.5,
        ),
        (
            "human",
            f"I understand the concern. Let me pull up the account details. "
            f"I can see the promotional rate expired last month, which is why the bill "
            f"went up to the standard rate of ${current_rate:.0f}. Unfortunately that is "
            f"our current pricing for that tier.",
            2.0,
        ),
        (
            "agent",
            f"I appreciate you explaining that, Marcus. However, I've done some research "
            f"on current market rates. {competitor_intel} "
            f"Given that {user_name} has been with Comcast for over two years, "
            f"we were hoping you could offer a retention rate closer to ${target_rate:.0f} per month.",
            1.8,
        ),
        (
            "human",
            "I understand, and we definitely value long-term customers. "
            "Let me see what I have available in our retention offers... "
            "I can offer a 12-month promotional rate. Give me just a moment.",
            2.5,
        ),
        (
            "agent",
            "Of course, take your time. We really want to keep this service "
            "and avoid having to switch providers.",
            1.0,
        ),
        (
            "human",
            f"Okay, I've got good news. I can apply our loyalty discount which brings the "
            f"monthly rate down to ${target_rate:.0f} per month for the next 12 months. "
            f"Same speed tier, same service. Would that work?",
            2.0,
        ),
        (
            "agent",
            f"${target_rate:.0f} per month for 12 months -- that works perfectly. "
            f"{user_name} will be happy with that. Could I get a confirmation number "
            f"for this rate change?",
            1.5,
        ),
        (
            "human",
            f"Absolutely. Your confirmation number is {confirmation_number}. "
            f"The new rate of ${target_rate:.0f} per month will take effect on your next "
            f"billing cycle. Is there anything else I can help with today?",
            1.8,
        ),
        (
            "agent",
            f"No, that's everything. Thank you for your help, Marcus. "
            f"Just to confirm -- confirmation number {confirmation_number}, "
            f"new rate ${target_rate:.0f} per month, effective next billing cycle. "
            f"Have a great day.",
            1.2,
        ),
        (
            "human",
            "You're welcome. Thank you for being a loyal Comcast customer. Goodbye!",
            1.0,
        ),
    ]


def _build_cancellation_script(
    user_name: str,
    company: str,
    service_type: str,
    confirmation_number: str,
) -> list[tuple[str, str, float]]:
    """Build a realistic service cancellation transcript."""
    return [
        (
            "agent",
            f"Hello, this is Haggle calling on behalf of {user_name}. "
            f"I need to process a cancellation for {user_name}'s {service_type} membership.",
            1.5,
        ),
        (
            "human",
            f"Hi, thanks for calling {company}. I can help you with that. "
            f"Can you confirm the account holder's name?",
            1.8,
        ),
        (
            "agent",
            f"Yes, the account holder is {user_name}.",
            1.0,
        ),
        (
            "human",
            f"Thank you. I see {user_name}'s account. I do need to let you know "
            f"there's a cancellation process. Is there anything we can do to keep "
            f"the membership active? We could offer a reduced rate.",
            2.0,
        ),
        (
            "agent",
            f"I appreciate the offer, but {user_name} has made the decision to cancel. "
            f"They haven't used the membership in several months.",
            1.5,
        ),
        (
            "human",
            f"I understand. Let me process that cancellation now. "
            f"The membership will end at the end of the current billing cycle. "
            f"Your confirmation number is {confirmation_number}.",
            2.2,
        ),
        (
            "agent",
            f"Thank you. Confirmation number {confirmation_number} -- got it. "
            f"And there will be no further charges after the current cycle?",
            1.2,
        ),
        (
            "human",
            "That's correct. No further charges. Is there anything else?",
            1.5,
        ),
        (
            "agent",
            "That's all. Thank you for your help.",
            0.8,
        ),
    ]


# ── Summary Generator ────────────────────────────────────────

def _generate_narrative_summary(
    action: str,
    company: str,
    user_name: str,
    old_rate: float,
    new_rate: float,
    savings: float,
    confirmation: str,
    research_context: str = "",
) -> dict:
    """Generate a first-person agent narrative summary of the completed call."""
    if action == "negotiate_rate":
        # Build competitor clause from research context
        competitors = []
        ctx = research_context.lower()
        if "t-mobile" in ctx:
            competitors.append("T-Mobile 5G Home Internet at $50/mo")
        if "at&t" in ctx:
            competitors.append("AT&T Fiber at $55/mo")
        if "verizon" in ctx:
            competitors.append("Verizon FiOS at $49.99/mo")

        competitor_clause = ""
        if competitors:
            competitor_clause = (
                f" I cited {', '.join(competitors)} as leverage to negotiate from a position of strength."
            )

        narrative = (
            f"I called {company} on behalf of {user_name} and reached the customer retention department. "
            f"The representative confirmed the rate increase was due to a promotional period expiration.{competitor_clause} "
            f"After negotiation, {company} applied a 12-month loyalty discount — reducing the monthly bill "
            f"from ${old_rate:.0f} to ${new_rate:.0f}, saving ${savings:.0f}/month (${savings * 12:.0f}/year). "
            f"Confirmation number {confirmation} was issued and the new rate takes effect next billing cycle."
        )
        key_points = [
            f"Connected with {company} retention department",
            f"Cited competitor pricing as negotiation leverage" if competitors else f"Presented rate reduction request",
            f"Secured ${savings:.0f}/month reduction — from ${old_rate:.0f} to ${new_rate:.0f}",
            f"12-month loyalty discount applied",
            f"Confirmation #{confirmation} issued",
        ]

    elif action == "cancel_service":
        narrative = (
            f"I called {company} on behalf of {user_name} to process a membership cancellation. "
            f"The representative offered a reduced rate to retain the account, but I confirmed the decision to cancel. "
            f"The membership will end at the close of the current billing cycle with no further charges, "
            f"saving ${savings:.0f}/month (${savings * 12:.0f}/year). "
            f"Confirmation number {confirmation} was issued."
        )
        key_points = [
            f"Called {company} and requested cancellation",
            f"Declined retention offer",
            f"Cancellation confirmed — ends current billing cycle",
            f"No further charges — saves ${savings:.0f}/month (${savings * 12:.0f}/year)",
            f"Confirmation #{confirmation} issued",
        ]

    else:
        narrative = (
            f"I completed the {action.replace('_', ' ')} task for {company} on behalf of {user_name}. "
            f"Confirmation: {confirmation}."
        )
        key_points = [f"Task completed for {company}", f"Confirmation #{confirmation}"]

    return {"narrative": narrative, "key_points": key_points}


# ── Phase Runners ────────────────────────────────────────────

async def _phase_research(task_id: str, company: str, action: str, service_type: str) -> dict:
    """Phase 1: Research via Tavily with SSE events."""
    task = store.get_task(task_id)

    # Update status to researching
    store.update_task(task_id, status=TaskStatus.RESEARCHING)
    task = store.get_task(task_id)
    await store.push_task_update(task)

    await store.push_event(SSEEvent(
        type=SSEEventType.TASK_UPDATED,
        data={
            "task_id": task_id,
            "phase": "research",
            "message": f"Researching {company} rates and competitor pricing...",
        },
    ))

    await asyncio.sleep(1.0)

    # Attempt real Tavily research
    research_data: dict = {"context": "", "sources": []}
    try:
        research_data = tavily_service.research_for_task(
            company=company,
            action=action,
            service_type=service_type,
        )
        logger.info("Tavily research returned: %s", research_data.get("context", "")[:120])
    except Exception as exc:
        logger.warning("Tavily research failed, using fallback: %s", exc)

    # Fallback context when Tavily is unavailable or returns nothing useful
    if not research_data.get("context") or "unavailable" in research_data["context"].lower():
        research_data = {
            "context": (
                f"T-Mobile 5G Home Internet is available in the area at $50/month. "
                f"AT&T Fiber offers plans starting at $55/month. "
                f"Verizon FiOS is advertising $49.99/month for new customers. "
                f"{company} retention department typically offers 20-30% discounts "
                f"to customers who mention competitor rates."
            ),
            "sources": [
                "https://www.t-mobile.com/home-internet",
                "https://www.att.com/internet/fiber/",
                "https://www.verizon.com/home/fios/",
            ],
        }

    # ── Senso compliance context ──────────────────────────────
    senso_context = ""
    try:
        senso_result = await senso_service.search_knowledge(
            f"{company} {action.replace('_', ' ')} consumer rights retention strategies"
        )
        if senso_result and "unavailable" not in senso_result.lower():
            senso_context = senso_result
            research_data["context"] += f" Compliance: {senso_context[:300]}"
            research_data.setdefault("sources", []).append("senso:compliance_db")
            logger.info("Senso compliance context: %s", senso_context[:120])
    except Exception as exc:
        logger.warning("Senso search failed (non-fatal): %s", exc)

    store.update_task(
        task_id,
        research_context=research_data["context"],
        research_sources=research_data.get("sources", []),
    )

    await store.push_event(SSEEvent(
        type=SSEEventType.TASK_UPDATED,
        data={
            "task_id": task_id,
            "phase": "research_complete",
            "research": research_data,
            "senso_context": senso_context[:200] if senso_context else None,
            "message": f"Research complete. Found competitor rates and retention strategies.",
        },
    ))

    await asyncio.sleep(0.8)
    return research_data


async def _phase_call(
    task_id: str,
    call_id: str,
    script: list[tuple[str, str, float]],
) -> None:
    """Phase 2: Simulate a phone call with transcript SSE events."""
    task = store.get_task(task_id)

    # Update task to calling
    store.update_task(task_id, status=TaskStatus.CALLING, call_id=call_id)
    task = store.get_task(task_id)
    await store.push_task_update(task)

    # Push call_started event
    await store.push_event(SSEEvent(
        type=SSEEventType.CALL_STATUS,
        data={
            "task_id": task_id,
            "call_id": call_id,
            "status": "ringing",
            "company": task.company,
            "phone_number": task.phone_number,
        },
    ))

    await asyncio.sleep(1.5)

    await store.push_event(SSEEvent(
        type=SSEEventType.CALL_STATUS,
        data={
            "task_id": task_id,
            "call_id": call_id,
            "status": "in_progress",
            "message": "Call connected",
        },
    ))

    await asyncio.sleep(0.8)

    # Stream transcript lines
    for role, text, delay in script:
        await asyncio.sleep(delay)

        await store.push_event(SSEEvent(
            type=SSEEventType.TRANSCRIPT,
            data={
                "task_id": task_id,
                "call_id": call_id,
                "role": role,
                "text": text,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        ))

        # Push emotion events at key moments for dashboard flair
        if role == "human" and "loyalty discount" in text.lower():
            await store.push_event(SSEEvent(
                type=SSEEventType.EMOTION,
                data={
                    "call_id": call_id,
                    "emotion": "positive",
                    "confidence": 0.92,
                    "context": "Representative offering retention deal",
                },
            ))
        elif role == "human" and "confirmation number" in text.lower():
            await store.push_event(SSEEvent(
                type=SSEEventType.EMOTION,
                data={
                    "call_id": call_id,
                    "emotion": "success",
                    "confidence": 0.97,
                    "context": "Confirmation number received",
                },
            ))
        elif role == "human" and "standard rate" in text.lower():
            await store.push_event(SSEEvent(
                type=SSEEventType.EMOTION,
                data={
                    "call_id": call_id,
                    "emotion": "neutral",
                    "confidence": 0.75,
                    "context": "Representative explaining rate increase",
                },
            ))


async def _phase_tool_calls(
    task_id: str,
    call_id: str,
    company: str,
    research_context: str,
    confirmation_number: str,
    new_rate: float,
) -> None:
    """Phase 3: Simulate the agent's internal tool calls with SSE events."""

    # Tool call 1: search_task_context
    await store.push_event(SSEEvent(
        type=SSEEventType.TASK_UPDATED,
        data={
            "task_id": task_id,
            "call_id": call_id,
            "tool_call": "search_task_context",
            "message": f"Agent retrieved task context and research for {company}",
            "arguments": {"task_id": task_id},
        },
    ))
    await asyncio.sleep(0.6)

    # Tool call 2: extract_entities -- price
    await store.push_event(SSEEvent(
        type=SSEEventType.ENTITY_EXTRACTED,
        data={
            "entity_type": "price",
            "value": f"${new_rate:.0f}/month",
            "context": f"New negotiated rate with {company}",
            "call_id": call_id,
        },
    ))
    await asyncio.sleep(0.5)

    # Tool call 3: extract_entities -- confirmation number
    await store.push_event(SSEEvent(
        type=SSEEventType.ENTITY_EXTRACTED,
        data={
            "entity_type": "confirmation_number",
            "value": confirmation_number,
            "context": f"Rate change confirmation from {company} retention department",
            "call_id": call_id,
        },
    ))

    # Update task with extracted data
    store.update_task(
        task_id,
        confirmation_number=confirmation_number,
        outcome=f"New rate: ${new_rate:.0f}/month",
    )
    await asyncio.sleep(0.5)

    # Tool call 4: update_neo4j
    await store.push_event(SSEEvent(
        type=SSEEventType.TASK_UPDATED,
        data={
            "task_id": task_id,
            "call_id": call_id,
            "tool_call": "update_neo4j",
            "message": f"Updating knowledge graph with negotiation result",
            "arguments": {
                "action": "negotiate_rate",
                "service_name": company,
                "details": {
                    "old_rate": 85,
                    "new_rate": new_rate,
                    "confirmation": confirmation_number,
                },
            },
        },
    ))
    await asyncio.sleep(0.4)


async def _phase_resolution(
    task_id: str,
    call_id: str,
    company: str,
    old_rate: float,
    new_rate: float,
    confirmation_number: str,
) -> dict:
    """Phase 4: Update Neo4j, mark task completed, push final events."""

    # Update the Neo4j knowledge graph
    graph_result = neo4j_service.update_service_rate(
        service_name=company,
        old_rate=old_rate,
        new_rate=new_rate,
        confirmation=confirmation_number,
    )
    logger.info("Neo4j update result: %s", graph_result)

    # Store price entity in Neo4j (confirmation numbers are ephemeral, skip them)
    neo4j_service.add_entity(
        entity_type="price",
        value=f"${new_rate:.0f}/month",
        context=f"New negotiated monthly rate for {company}",
        call_id=call_id,
    )

    # Push graph updated event
    graph_data = neo4j_service.get_graph_data()
    await store.push_event(SSEEvent(
        type=SSEEventType.GRAPH_UPDATED,
        data={
            "action": "negotiate_rate",
            "service": company,
            "details": {
                "old_rate": old_rate,
                "new_rate": new_rate,
                "confirmation": confirmation_number,
                "monthly_savings": old_rate - new_rate,
                "annual_savings": (old_rate - new_rate) * 12,
            },
            "graph": graph_data,
        },
    ))
    await asyncio.sleep(0.5)

    # Push call ended event
    await store.push_event(SSEEvent(
        type=SSEEventType.CALL_STATUS,
        data={
            "task_id": task_id,
            "call_id": call_id,
            "status": "ended",
            "duration_seconds": 47,
            "outcome": "success",
        },
    ))
    await asyncio.sleep(0.3)

    # Mark task completed
    savings = old_rate - new_rate
    store.update_task(
        task_id,
        status=TaskStatus.COMPLETED,
        savings=savings,
        outcome=(
            f"Successfully negotiated {company} rate from ${old_rate:.0f}/mo to "
            f"${new_rate:.0f}/mo. Saving ${savings:.0f}/mo (${savings * 12:.0f}/yr). "
            f"Confirmation: {confirmation_number}"
        ),
    )
    task = store.get_task(task_id)
    await store.push_task_update(task)

    # Push narrative summary for dashboard and email
    summary_data = _generate_narrative_summary(
        action="negotiate_rate",
        company=company,
        user_name=task.user_name,
        old_rate=old_rate,
        new_rate=new_rate,
        savings=savings,
        confirmation=confirmation_number,
        research_context=task.research_context or "",
    )
    await store.push_event(SSEEvent(
        type=SSEEventType.CALL_SUMMARY,
        data={"task_id": task_id, "call_id": call_id, **summary_data},
    ))

    return {
        "task_id": task_id,
        "company": company,
        "old_rate": old_rate,
        "new_rate": new_rate,
        "monthly_savings": savings,
        "annual_savings": savings * 12,
        "confirmation_number": confirmation_number,
    }


async def _phase_cancellation_resolution(
    task_id: str,
    call_id: str,
    company: str,
    user_name: str,
    monthly_rate: float,
    confirmation_number: str,
) -> dict:
    """Resolution phase for service cancellation tasks."""

    # Update Neo4j
    graph_result = neo4j_service.cancel_service(
        user_name=user_name,
        service_name=company,
        confirmation=confirmation_number,
    )
    logger.info("Neo4j cancellation result: %s", graph_result)

    graph_data = neo4j_service.get_graph_data()
    await store.push_event(SSEEvent(
        type=SSEEventType.GRAPH_UPDATED,
        data={
            "action": "cancel_service",
            "service": company,
            "details": {
                "status": "cancelled",
                "confirmation": confirmation_number,
                "monthly_savings": monthly_rate,
                "annual_savings": monthly_rate * 12,
            },
            "graph": graph_data,
        },
    ))
    await asyncio.sleep(0.5)

    await store.push_event(SSEEvent(
        type=SSEEventType.CALL_STATUS,
        data={
            "task_id": task_id,
            "call_id": call_id,
            "status": "ended",
            "duration_seconds": 32,
            "outcome": "success",
        },
    ))
    await asyncio.sleep(0.3)

    store.update_task(
        task_id,
        status=TaskStatus.COMPLETED,
        savings=monthly_rate,
        confirmation_number=confirmation_number,
        outcome=(
            f"Successfully cancelled {company} {monthly_rate:.0f}/mo membership. "
            f"Saving ${monthly_rate:.0f}/mo (${monthly_rate * 12:.0f}/yr). "
            f"Confirmation: {confirmation_number}"
        ),
    )
    task = store.get_task(task_id)
    await store.push_task_update(task)

    # Push narrative summary for dashboard and email
    summary_data = _generate_narrative_summary(
        action="cancel_service",
        company=company,
        user_name=user_name,
        old_rate=monthly_rate,
        new_rate=0,
        savings=monthly_rate,
        confirmation=confirmation_number,
        research_context=task.research_context or "",
    )
    await store.push_event(SSEEvent(
        type=SSEEventType.CALL_SUMMARY,
        data={"task_id": task_id, "call_id": call_id, **summary_data},
    ))

    return {
        "task_id": task_id,
        "company": company,
        "action": "cancel_service",
        "monthly_savings": monthly_rate,
        "annual_savings": monthly_rate * 12,
        "confirmation_number": confirmation_number,
    }


# ── Mock User Consult Script (trimmed for demo) ─────────────

_DEMO_CONSULT_SCRIPT: list[tuple[str, str, float]] = [
    ("agent",
     "Hi Neel, this is Haggle. I've finished scanning your accounts and found "
     "some savings opportunities — do you have a minute?",
     1.5),
    ("user",
     "Yeah, go ahead.",
     1.2),
    ("agent",
     "Your Comcast bill jumped from $55 to $85 last month — a 54% increase. "
     "The promotional rate expired. T-Mobile 5G Home Internet is $50 and "
     "AT&T Fiber is $55 in your area right now.",
     2.0),
    ("user",
     "Yeah I noticed that. That's annoying.",
     1.2),
    ("agent",
     "I can call their retention department and negotiate it down to around $65. "
     "Customers who mention competitor rates usually get a 12-month loyalty discount. "
     "Should I make the call?",
     1.8),
    ("user",
     "Yes, do it.",
     1.0),
    ("agent",
     "On it. I'll call Comcast retention now and get your rate back down. "
     "Stand by — I'll update you when it's done.",
     1.2),
]


# ── Full Demo Background Runner ─────────────────────────────

async def _run_full_demo(task_id: str):
    """
    Full demo flow:
      1. Mock user consult (simulated conversation)
      2. Research phase (Tavily + Senso)
      3. Show phone number for live Vapi call
    """
    task = store.get_task(task_id)
    consult_call_id = f"consult_{uuid.uuid4().hex[:10]}"

    # ── Phase 0: Mock user consult ────────────────────────────
    await store.push_event(SSEEvent(
        type=SSEEventType.CALL_STATUS,
        data={
            "task_id": task_id,
            "call_id": consult_call_id,
            "status": "ringing",
            "company": "Neel (User Consult)",
            "phone_number": "+15550000001",
            "call_type": "user_consult",
        },
    ))
    await asyncio.sleep(1.2)

    await store.push_event(SSEEvent(
        type=SSEEventType.CALL_STATUS,
        data={
            "task_id": task_id,
            "call_id": consult_call_id,
            "status": "in_progress",
            "call_type": "user_consult",
            "message": "User consult call connected",
        },
    ))
    await asyncio.sleep(0.6)

    # Stream the consult transcript
    for role, text, delay in _DEMO_CONSULT_SCRIPT:
        await asyncio.sleep(delay)
        await store.push_event(SSEEvent(
            type=SSEEventType.TRANSCRIPT,
            data={
                "task_id": task_id,
                "call_id": consult_call_id,
                "role": role,
                "text": text,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "call_type": "user_consult",
            },
        ))

    await asyncio.sleep(0.5)

    # Consult call ended
    await store.push_event(SSEEvent(
        type=SSEEventType.CALL_STATUS,
        data={
            "task_id": task_id,
            "call_id": consult_call_id,
            "status": "ended",
            "call_type": "user_consult",
            "duration_seconds": 28,
            "message": "User confirmed: negotiate Comcast rate",
        },
    ))

    await asyncio.sleep(1.0)

    # ── Phase 1: Research (Tavily + Senso) ────────────────────
    research_data = await _phase_research(
        task_id=task_id,
        company=task.company,
        action=task.action.value,
        service_type=task.service_type or "",
    )

    # ── Phase 2: Show phone number for live call ──────────────
    agent_phone = "+12086751229"
    agent_phone_display = "(208) 675-1229"

    call_id = _generate_call_id()
    store.update_task(task_id, status=TaskStatus.CALLING, call_id=call_id)
    refreshed = store.get_task(task_id)
    await store.push_task_update(refreshed)

    await store.push_event(SSEEvent(
        type=SSEEventType.CALL_STATUS,
        data={
            "task_id": task_id,
            "call_id": call_id,
            "status": "awaiting_call",
            "company": task.company,
            "agent_phone": agent_phone,
            "agent_phone_display": agent_phone_display,
            "message": f"Call {agent_phone_display} — you play {task.company}, the agent negotiates",
        },
    ))


# ── Endpoints ────────────────────────────────────────────────

@router.post("/api/demo/run")
async def demo_run():
    """
    Run the full demo: mock user consult → research → live Vapi call.
    Returns immediately; SSE events drive the dashboard in real-time.
    """
    # Find the first pending task
    pending_tasks = [t for t in store.list_tasks() if t.status == TaskStatus.PENDING]
    if not pending_tasks:
        raise HTTPException(
            status_code=404,
            detail="No pending tasks available. Use POST /api/demo/reset to restore demo tasks.",
        )

    task = pending_tasks[0]
    task_id = task.id

    logger.info(
        "Demo run started: task=%s company=%s action=%s",
        task_id, task.company, task.action.value,
    )

    # Kick off the full demo flow in the background
    asyncio.create_task(_run_full_demo(task_id))

    return {
        "status": "demo_started",
        "task_id": task_id,
        "message": "Demo started — watch the dashboard. User consult plays first, then call the agent.",
    }


@router.post("/api/demo/reset")
async def demo_reset():
    """
    Reset the demo environment to a clean starting state.

    - Clears all tasks and re-seeds the demo scenarios
    - Wipes the Neo4j graph and re-seeds demo nodes
    - Pushes a task_updated SSE event so the dashboard refreshes
    """
    # Clear and re-seed tasks
    store.tasks.clear()
    store._seed_demo_tasks()

    # Clear and re-seed Neo4j graph
    if neo4j_service.available:
        try:
            with neo4j_service.driver.session() as session:
                session.execute_write(lambda tx: tx.run("MATCH (n) DETACH DELETE n"))
            neo4j_service.seed_demo_data()
            logger.info("Neo4j graph cleared and re-seeded")
        except Exception as exc:
            logger.error("Neo4j reset failed: %s", exc)

    # Notify dashboard
    tasks = store.list_tasks()
    await store.push_event(SSEEvent(
        type=SSEEventType.TASK_UPDATED,
        data={"tasks": [t.model_dump() for t in tasks], "reset": True},
    ))

    return {
        "status": "reset_complete",
        "tasks": [t.model_dump() for t in tasks],
        "neo4j": "re-seeded" if neo4j_service.available else "not_configured",
    }


@router.get("/api/demo/stats")
async def demo_stats():
    """
    Return aggregate statistics for the demo dashboard.

    Provides total savings, completed task count, call count,
    and Neo4j graph node count for the stats ribbon.
    """
    tasks = store.list_tasks()

    completed = [t for t in tasks if t.status == TaskStatus.COMPLETED]
    total_monthly_savings = sum(t.savings or 0 for t in completed)
    total_annual_savings = total_monthly_savings * 12
    calls_made = sum(1 for t in tasks if t.call_id is not None)

    # Graph stats
    graph_nodes = 0
    graph_relationships = 0
    if neo4j_service.available:
        try:
            graph_data = neo4j_service.get_graph_data()
            graph_nodes = len(graph_data.get("nodes", []))
            graph_relationships = len(graph_data.get("links", []))
        except Exception as exc:
            logger.warning("Could not fetch graph stats: %s", exc)

    return {
        "total_monthly_savings": total_monthly_savings,
        "total_annual_savings": total_annual_savings,
        "tasks_total": len(tasks),
        "tasks_completed": len(completed),
        "tasks_pending": sum(1 for t in tasks if t.status == TaskStatus.PENDING),
        "tasks_in_progress": sum(
            1 for t in tasks if t.status in (TaskStatus.RESEARCHING, TaskStatus.CALLING)
        ),
        "calls_made": calls_made,
        "graph_nodes": graph_nodes,
        "graph_relationships": graph_relationships,
    }
