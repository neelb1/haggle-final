"""
User Consult Call Endpoints
- POST /api/user/call          -- Trigger a real Vapi outbound call to the user's phone
- POST /api/demo/user-consult  -- Simulate the full user consult → service provider loop
"""

import asyncio
import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException

from models.schemas import (
    SSEEvent,
    SSEEventType,
    TaskCreate,
    TaskAction,
    TaskStatus,
    ConfirmedAction,
)
from services.task_store import store
from services import vapi_service, subscription_service, modulate_service

logger = logging.getLogger(__name__)
router = APIRouter()


# ── Real Vapi Outbound Call ───────────────────────────────────

@router.post("/api/user/call")
async def call_user():
    """
    Trigger a real Vapi outbound call to the user's phone.
    The agent presents billing analysis, asks usage questions,
    and collects confirmed actions via the confirm_action tool.
    Falls back to simulation if USER_PHONE_NUMBER is not set.
    """
    import config
    if not config.USER_PHONE_NUMBER:
        raise HTTPException(
            status_code=400,
            detail="USER_PHONE_NUMBER not set. Use POST /api/demo/user-consult for a simulated demo.",
        )

    ctx = subscription_service.build_subscription_context()

    # Create a consult task so the webhook can identify this call later
    task = store.create_task(TaskCreate(
        company="Haggle Consult",
        action=TaskAction.CONSULT_USER,
        phone_number=config.USER_PHONE_NUMBER,
        service_type="consult",
        user_name=ctx["user_name"],
        notes=f"Outbound consult: ${ctx['total_potential_savings']:.0f}/mo potential savings",
    ))

    result = await vapi_service.trigger_user_consult_call(
        phone=config.USER_PHONE_NUMBER,
        task_id=task.id,
        context=ctx,
    )

    if "error" in result:
        store.update_task(task.id, status=TaskStatus.FAILED, outcome=result["error"])
        raise HTTPException(status_code=502, detail=result["error"])

    call_id = result.get("id", "")
    store.update_task(task.id, call_id=call_id, status=TaskStatus.CALLING)

    await store.push_event(SSEEvent(
        type=SSEEventType.CALL_STATUS,
        data={
            "task_id": task.id,
            "call_id": call_id,
            "status": "ringing",
            "company": "User Consult",
            "phone_number": config.USER_PHONE_NUMBER,
            "call_type": "user_consult",
            "message": f"Haggle is calling you to review ${ctx['total_potential_savings']:.0f}/mo in potential savings",
        },
    ))

    return {
        "status": "calling",
        "call_id": call_id,
        "task_id": task.id,
        "context": {
            "total_monthly": ctx["total_monthly"],
            "total_potential_savings": ctx["total_potential_savings"],
            "subscriptions": len(ctx["subscriptions"]),
        },
    }


# ── Demo Simulation ───────────────────────────────────────────

@router.post("/api/demo/user-consult")
async def demo_user_consult():
    """
    Simulate the full autonomous loop:
      1. Haggle calls the user (pre-scripted conversation)
      2. User confirms: cancel Planet Fitness + negotiate Comcast
      3. Service provider tasks are created automatically
      4. Both service provider calls run sequentially
    """
    # Clear any leftover state
    store.clear_confirmed_actions()

    ctx = subscription_service.build_subscription_context()
    call_id = f"consult_{uuid.uuid4().hex[:10]}"

    # Create the consult task
    task = store.create_task(TaskCreate(
        company="Haggle Consult",
        action=TaskAction.CONSULT_USER,
        phone_number="+15550000001",
        service_type="consult",
        user_name=ctx["user_name"],
        notes=f"Demo consult: ${ctx['total_potential_savings']:.0f}/mo potential savings",
    ))
    store.update_task(task.id, call_id=call_id, status=TaskStatus.CALLING)

    # Kick off simulation as a background task so this endpoint returns immediately
    asyncio.create_task(_run_consult_simulation(task.id, call_id, ctx))

    return {
        "status": "simulation_started",
        "task_id": task.id,
        "call_id": call_id,
        "message": "Watch the dashboard — Haggle is calling the user now.",
    }


# ── Simulation Script ─────────────────────────────────────────

_CONSULT_SCRIPT: list[tuple[str, str, float]] = [
    ("agent",
     "Hi Neel, this is Haggle. I've finished scanning your accounts and found "
     "a couple of things worth reviewing — do you have two minutes?",
     1.5),
    ("user",
     "Yeah, go ahead.",
     1.8),
    ("agent",
     "Great. So first: your Comcast bill jumped from $55 to $85 last month — "
     "that's a 54% increase. Their promotional rate expired. "
     "T-Mobile 5G Home is $50 and AT&T Fiber is $55 in your area right now.",
     2.2),
    ("user",
     "Yeah I noticed that. That's annoying.",
     1.5),
    ("agent",
     "I can call their retention department and negotiate it back down to around $65. "
     "Customers who mention competitor rates usually get a 12-month loyalty discount. "
     "Should I go ahead and do that?",
     2.0),
    ("user",
     "Yes, please do that.",
     1.2),
    ("agent",
     "Done — I'll handle Comcast. Second thing: you're paying $25 a month for Planet Fitness. "
     "How often are you actually going these days?",
     2.0),
    ("user",
     "Honestly, maybe twice a month.",
     1.5),
    ("agent",
     "So that works out to $12.50 per visit. A day pass at Planet Fitness is $10. "
     "You'd actually save $2.50 every visit just by walking in instead of having a membership. "
     "Want me to cancel it?",
     2.5),
    ("user",
     "Yeah, cancel it. I keep meaning to go more but it's not happening.",
     1.8),
    ("agent",
     "Understood. I'll cancel that too. So in total you're looking at saving $45 a month — "
     "$540 a year. I'll make both calls right now and send you an email when everything's done.",
     2.0),
    ("user",
     "That's great, thanks.",
     1.2),
    ("agent",
     "You're welcome. I'll take care of it. Talk soon.",
     1.0),
]


async def _run_consult_simulation(task_id: str, call_id: str, ctx: dict):
    """Stream the pre-scripted user consult conversation, then fire service provider calls."""

    # Signal: call ringing
    await store.push_event(SSEEvent(
        type=SSEEventType.CALL_STATUS,
        data={
            "task_id": task_id,
            "call_id": call_id,
            "status": "ringing",
            "company": "Neel (User Consult)",
            "phone_number": "+15550000001",
            "call_type": "user_consult",
        },
    ))
    await asyncio.sleep(1.2)

    await store.push_event(SSEEvent(
        type=SSEEventType.CALL_STATUS,
        data={"task_id": task_id, "call_id": call_id, "status": "in_progress",
              "call_type": "user_consult", "message": "User consult call connected"},
    ))
    await asyncio.sleep(0.6)

    # Stream transcript
    for role, text, delay in _CONSULT_SCRIPT:
        await asyncio.sleep(delay)
        await store.push_event(SSEEvent(
            type=SSEEventType.TRANSCRIPT,
            data={
                "task_id": task_id,
                "call_id": call_id,
                "role": role,
                "text": text,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "call_type": "user_consult",
            },
        ))

        # Simulate confirm_action tool firing after user says yes
        if "cancel it" in text.lower() and role == "user":
            await asyncio.sleep(0.4)
            _fire_confirmed_action(
                service="Planet Fitness",
                action="cancel_service",
                reason="User visits twice/month at $12.50/visit vs $10 day pass — not cost-effective",
                monthly_savings=25.0,
                phone_number="+18005555678",
                call_id=call_id,
            )

        elif "yes, please do that" in text.lower() and role == "user":
            await asyncio.sleep(0.4)
            _fire_confirmed_action(
                service="Comcast",
                action="negotiate_rate",
                reason="54% billing increase detected — competitor rates available as leverage",
                monthly_savings=20.0,
                phone_number="+18005551234",
                call_id=call_id,
            )

    await asyncio.sleep(0.5)

    # Call ended
    await store.push_event(SSEEvent(
        type=SSEEventType.CALL_STATUS,
        data={"task_id": task_id, "call_id": call_id, "status": "ended",
              "call_type": "user_consult", "duration_seconds": 52},
    ))

    # ── Modulate Velma 2: analyze user consult voice ──────────
    await store.push_event(SSEEvent(
        type=SSEEventType.TASK_UPDATED,
        data={
            "task_id": task_id,
            "call_id": call_id,
            "phase": "research",
            "message": "Modulate Velma 2 analyzing user consult voice...",
        },
    ))
    await asyncio.sleep(0.6)

    consult_analysis = await modulate_service.analyze_call(
        transcript=[{"role": r, "text": t} for r, t, _ in _CONSULT_SCRIPT],
        call_type="user_consult",
    )
    await store.push_event(SSEEvent(
        type=SSEEventType.VOICE_ANALYSIS,
        data={"task_id": task_id, "call_id": call_id, **consult_analysis},
    ))
    await asyncio.sleep(0.4)

    # Mark consult task complete
    confirmed = store.get_confirmed_actions()
    store.update_task(task_id, status=TaskStatus.COMPLETED,
                      outcome=f"User confirmed {len(confirmed)} action(s) — dispatching service calls")
    await store.push_task_update(store.get_task(task_id))

    await asyncio.sleep(0.8)

    # Announce service call dispatch — include Velma recommendation as context
    velma_rec = consult_analysis.get("negotiation_recommendation", "")
    await store.push_event(SSEEvent(
        type=SSEEventType.TASK_UPDATED,
        data={
            "message": (
                f"User confirmed {len(confirmed)} action(s). "
                "Velma context loaded. Dispatching service calls now..."
            ),
            "confirmed_count": len(confirmed),
            "call_id": call_id,
            "phase": "dispatch",
            "velma_context": velma_rec,
        },
    ))

    # Create service provider tasks and run them sequentially
    store.clear_confirmed_actions()
    for ca in confirmed:
        await _create_and_run_service_task(ca, ctx["user_name"], consult_analysis)
        await asyncio.sleep(1.0)  # brief gap between calls


def _fire_confirmed_action(
    service: str,
    action: str,
    reason: str,
    monthly_savings: float,
    phone_number: str,
    call_id: str,
):
    """Store a confirmed action and push its SSE event synchronously."""
    ca = ConfirmedAction(
        service=service,
        action=action,
        reason=reason,
        monthly_savings=monthly_savings,
        phone_number=phone_number,
    )
    store.add_confirmed_action(ca)
    # Push SSE from sync context via asyncio — this is called inside an async task
    asyncio.get_event_loop().call_soon(
        lambda: asyncio.ensure_future(store.push_event(SSEEvent(
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
        )))
    )


async def _create_and_run_service_task(
    ca: ConfirmedAction,
    user_name: str,
    consult_analysis: dict | None = None,
):
    """Create a service provider task from a confirmed action and run the demo simulation."""
    from routers.demo import (
        _phase_research,
        _phase_call,
        _phase_tool_calls,
        _phase_resolution,
        _phase_cancellation_resolution,
        _generate_call_id,
        _generate_confirmation,
        _build_comcast_negotiation_script,
        _build_cancellation_script,
    )
    from services import gmail_service

    # Look up rate info from subscription catalog
    sub = subscription_service.get_subscription_by_service(ca.service)
    current_rate = (sub["monthly_cost"] if sub else ca.monthly_savings)
    target_rate = current_rate - ca.monthly_savings if ca.action == "negotiate_rate" else 0.0

    task = store.create_task(TaskCreate(
        company=ca.service,
        action=ca.action,
        phone_number=ca.phone_number,
        service_type="subscription",
        current_rate=current_rate,
        target_rate=target_rate if ca.action == "negotiate_rate" else None,
        user_name=user_name,
        notes=ca.reason,
    ))
    await store.push_task_update(task)
    await asyncio.sleep(0.5)

    call_id = _generate_call_id()
    confirmation = _generate_confirmation()

    research = await _phase_research(task.id, ca.service, ca.action, "subscription")

    # Inject Velma user-consult insights into the competitor line so the agent
    # sounds informed by what it learned about the user's intent and urgency.
    velma_context_prefix = ""
    if consult_analysis:
        rec = consult_analysis.get("negotiation_recommendation", "")
        certainty = consult_analysis.get("certainty_score", 0)
        if rec:
            velma_context_prefix = (
                f"[Velma context: user certainty {certainty:.0%}, decisive — {rec[:120]}] "
            )

    if ca.action == "cancel_service":
        script = _build_cancellation_script(user_name, ca.service, "membership", confirmation)
    else:
        base_context = research.get("context", "Competitors offer lower rates in this area.")[:200]
        competitor_line = velma_context_prefix + base_context
        script = _build_comcast_negotiation_script(
            user_name, current_rate, target_rate, competitor_line, confirmation
        )

    await _phase_call(task.id, call_id, script)
    await _phase_tool_calls(task.id, call_id, ca.service,
                            research.get("context", ""), confirmation, target_rate)

    if ca.action == "cancel_service":
        await _phase_cancellation_resolution(task.id, call_id, ca.service,
                                              user_name, current_rate, confirmation)
    else:
        await _phase_resolution(task.id, call_id, ca.service,
                                 current_rate, target_rate, confirmation)

    # ── Modulate Velma 2: analyze service provider call ───────
    transcript_lines = [{"role": role, "text": text} for role, text, _ in script]
    service_analysis = await modulate_service.analyze_call(
        transcript=transcript_lines,
        call_type="service_provider",
        company=ca.service,
    )
    await store.push_event(SSEEvent(
        type=SSEEventType.VOICE_ANALYSIS,
        data={"task_id": task.id, "call_id": call_id, **service_analysis},
    ))

    completed = store.get_task(task.id)
    await gmail_service.send_call_summary(task=completed, transcript=transcript_lines)
