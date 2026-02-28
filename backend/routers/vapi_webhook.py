"""
Vapi Webhook Handler
POST /api/vapi/webhook

Receives ALL Vapi server messages:
- end-of-call-report: Full transcript + analysis after call ends
- status-update: Call state changes (ringing, in-progress, ended)
- transcript: Real-time partial transcripts
- conversation-update: Full conversation history
- speech-update: Speech activity events

From Vapi docs: Always return HTTP 200, even for errors.
"""

import asyncio
import logging

from fastapi import APIRouter, Request

from models.schemas import SSEEvent, SSEEventType, TaskCreate, TaskAction, TaskStatus
from services.task_store import store
from services import gmail_service, modulate_service, fastino_service, postgres_service
import config

logger = logging.getLogger(__name__)
router = APIRouter()



@router.post("/api/vapi/webhook")
async def vapi_webhook(request: Request):
    body = await request.json()
    message = body.get("message", {})
    msg_type = message.get("type", "")
    call_obj = message.get("call", {})
    call_id = call_obj.get("id", "unknown")

    logger.info("Webhook: type=%s call=%s", msg_type, call_id)

    if msg_type == "end-of-call-report":
        await _handle_end_of_call(message, call_id)

    elif msg_type == "status-update":
        await _handle_status_update(message, call_id)

    elif msg_type == "transcript":
        # Real-time transcript: push only "final" (sentence-complete) events
        await _handle_transcript(message, call_id)

    elif msg_type == "conversation-update":
        # Kept for internal tracking only — transcript display uses "transcript" events above
        pass

    # Always return 200
    return {"status": "ok"}


async def _handle_end_of_call(message: dict, call_id: str):
    """Process end-of-call report with full transcript and analysis."""
    transcript = message.get("transcript", "")
    summary = message.get("summary", "")
    ended_reason = message.get("endedReason", "")
    call_obj = message.get("call", {})
    analysis = message.get("analysis", {})
    structured_data = analysis.get("structuredData", {})
    duration = message.get("durationSeconds", 0)

    logger.info(
        "Call ended: reason=%s summary=%s",
        ended_reason,
        summary[:100] if summary else "none",
    )

    # ── Branch: user consult call ────────────────────────────
    # Detect by finding a consult_user task linked to this call_id
    consult_task = None
    for task in store.list_tasks():
        if task.call_id == call_id and task.action == TaskAction.CONSULT_USER:
            consult_task = task
            break

    if consult_task:
        # Run Modulate Velma 2 on the user consult call, then dispatch service tasks
        await _run_modulate_user_consult(call_id, message)
        await _handle_consult_end_of_call(consult_task, call_id)
        # Push SSE and return — skip service-provider logic below
        await store.push_event(SSEEvent(
            type=SSEEventType.CALL_STATUS,
            data={"call_id": call_id, "status": "ended", "ended_reason": ended_reason,
                  "call_type": "user_consult"},
        ))
        return

    # ── Branch: service provider call (existing logic) ───────
    for task in store.list_tasks():
        if task.call_id == call_id:
            task_completed = structured_data.get("task_completed", False)
            outcome = structured_data.get("outcome", summary or "Call ended")
            savings = structured_data.get("savings_amount", 0)
            conf = structured_data.get("confirmation_number", "")

            new_status = "completed" if task_completed else "needs_followup"

            store.update_task(
                task.id,
                status=new_status,
                outcome=outcome,
                savings=savings,
                confirmation_number=conf or task.confirmation_number,
            )
            await store.push_task_update(task)

            # Send call summary email with full transcript
            refreshed = store.get_task(task.id)
            await gmail_service.send_call_summary(
                task=refreshed,
                transcript_text=transcript,
            )
            break

    # ── Postgres: durable call log ──────────────────────────────
    try:
        task_for_log = None
        for t in store.list_tasks():
            if t.call_id == call_id:
                task_for_log = t
                break
        await postgres_service.insert_call_log(
            call_id=call_id,
            task_id=task_for_log.id if task_for_log else "",
            company=task_for_log.company if task_for_log else "",
            action=task_for_log.action.value if task_for_log else "",
            outcome=structured_data.get("outcome", summary or ""),
            savings=structured_data.get("savings_amount", 0),
            confirmation=structured_data.get("confirmation_number", ""),
            transcript=transcript[:5000],
            duration_seconds=duration,
        )
    except Exception as e:
        logger.error("Postgres call log failed: %s", e)

    # Push full report to SSE
    await store.push_event(SSEEvent(
        type=SSEEventType.CALL_STATUS,
        data={
            "call_id": call_id,
            "status": "ended",
            "ended_reason": ended_reason,
            "summary": summary,
            "structured_data": structured_data,
            "transcript": transcript[:2000],
            "duration_seconds": duration,
        },
    ))

    # ── Modulate Velma 2: Post-call emotion + PII + diarization ──
    recording_url = message.get("recordingUrl") or call_obj.get("recordingUrl")
    if recording_url and config.MODULATE_API_KEY:
        try:
            modulate_result = await modulate_service.analyze_call_from_url(recording_url)
            if "error" not in modulate_result and modulate_result.get("utterances"):
                emotion_timeline = modulate_service.extract_emotion_timeline(modulate_result)
                safety_report = modulate_service.generate_call_safety_report(modulate_result)

                # Build agent performance report from Modulate data
                perf = _build_agent_performance(safety_report, summary, duration)

                await store.push_event(SSEEvent(
                    type=SSEEventType.MODULATE_ANALYSIS,
                    data={
                        "call_id": call_id,
                        "source": "modulate_velma2",
                        "emotion_timeline": emotion_timeline[:50],
                        "safety_report": safety_report,
                        "agent_performance": perf,
                    },
                ))

                if safety_report.get("pii_detected", 0) > 0:
                    await store.push_event(SSEEvent(
                        type=SSEEventType.PII_DETECTED,
                        data={
                            "call_id": call_id,
                            "count": safety_report["pii_detected"],
                            "items": safety_report.get("pii_items", []),
                        },
                    ))

                logger.info(
                    "Modulate analysis complete: safety=%s, hostile=%d, pii=%d",
                    safety_report.get("safety_score"),
                    safety_report.get("rep_hostile_utterances", 0),
                    safety_report.get("pii_detected", 0),
                )
        except Exception as e:
            logger.error("Modulate post-call analysis failed: %s", e)

    # ── Fastino GLiNER2: Structured extraction on full transcript ──
    if transcript:
        try:
            negotiation = fastino_service.extract_negotiation_result(transcript)
            if negotiation and negotiation.get("outcome"):
                for t in store.list_tasks():
                    if t.call_id == call_id:
                        updates = {}
                        if negotiation.get("confirmation"):
                            updates["confirmation_number"] = negotiation["confirmation"]
                        if negotiation.get("outcome"):
                            updates["outcome"] = f"GLiNER2: {negotiation['outcome']}"
                        if negotiation.get("new_rate"):
                            updates["outcome"] = f"GLiNER2: {negotiation['outcome']} — new rate {negotiation['new_rate']}"
                        if updates:
                            store.update_task(t.id, **updates)
                        break
                logger.info("GLiNER2 post-call extraction: %s", negotiation)
        except Exception as e:
            logger.error("GLiNER2 post-call extraction failed: %s", e)


async def _run_modulate_user_consult(call_id: str, message: dict):
    """Run Modulate Velma 2 on the user consult call and push voice_analysis SSE."""
    conversation = message.get("conversation", [])
    transcript = [
        {"role": t.get("role"), "text": t.get("content", "")}
        for t in conversation
        if t.get("role") not in ("system", "tool") and t.get("content")
    ]

    recording_url = message.get("recordingUrl") or message.get("call", {}).get("recordingUrl")

    try:
        analysis = await modulate_service.analyze_call(
            transcript=transcript,
            call_type="user_consult",
            audio_url=recording_url,
        )
    except Exception as exc:
        logger.warning("Modulate user consult analysis failed, using demo fallback: %s", exc)
        analysis = modulate_service._analyze_user_consult_demo(transcript)

    await store.push_event(SSEEvent(
        type=SSEEventType.VOICE_ANALYSIS,
        data={**analysis, "call_id": call_id},
    ))
    logger.info("Velma 2 user consult analysis pushed: emotion=%s stress=%.2f certainty=%.2f",
                analysis.get("emotion"), analysis.get("stress_level", 0), analysis.get("certainty_score", 0))


async def _handle_consult_end_of_call(consult_task, call_id: str):
    """
    After the user consult call ends:
    1. Read confirmed_actions from the store
    2. Create a service-provider Task for each
    3. Auto-trigger the demo simulation for each task
    """
    confirmed = store.get_confirmed_actions()
    store.clear_confirmed_actions()

    # Mark the consult task complete
    store.update_task(consult_task.id, status=TaskStatus.COMPLETED,
                      outcome=f"User confirmed {len(confirmed)} action(s)")
    await store.push_task_update(store.get_task(consult_task.id))

    if not confirmed:
        logger.info("User consult ended with no confirmed actions.")
        await store.push_event(SSEEvent(
            type=SSEEventType.TASK_UPDATED,
            data={"message": "Consult complete — no actions confirmed by user.", "call_id": call_id},
        ))
        return

    logger.info("User consult confirmed %d action(s) — creating service tasks", len(confirmed))

    await store.push_event(SSEEvent(
        type=SSEEventType.TASK_UPDATED,
        data={
            "message": f"User confirmed {len(confirmed)} action(s). Dispatching service calls now...",
            "confirmed_count": len(confirmed),
            "call_id": call_id,
        },
    ))

    # Create and auto-run each service provider task
    for ca in confirmed:
        new_task = store.create_task(TaskCreate(
            company=ca.service,
            action=ca.action,
            phone_number=ca.phone_number,
            service_type="subscription",
            current_rate=ca.monthly_savings + (0 if ca.action == "cancel_service" else ca.monthly_savings),
            target_rate=0 if ca.action == "cancel_service" else None,
            user_name=consult_task.user_name,
            notes=ca.reason,
        ))
        await store.push_task_update(new_task)

        # Schedule the demo simulation for this task (non-blocking)
        asyncio.create_task(_auto_run_service_task(new_task.id))


async def _auto_run_service_task(task_id: str):
    """Run the full demo simulation for a service provider task created post-consult."""
    from routers.demo import (
        _phase_research, _phase_call, _phase_tool_calls,
        _phase_resolution, _phase_cancellation_resolution,
        _generate_call_id, _generate_confirmation,
        _build_comcast_negotiation_script, _build_cancellation_script,
    )
    import asyncio as _asyncio

    await _asyncio.sleep(1.5)  # brief pause so dashboard shows the task first

    task = store.get_task(task_id)
    if not task:
        return

    call_id = _generate_call_id()
    confirmation = _generate_confirmation()

    research = await _phase_research(task_id, task.company, task.action.value, task.service_type or "")

    if task.action.value == "cancel_service":
        script = _build_cancellation_script(task.user_name, task.company,
                                             task.service_type or "service", confirmation)
    else:
        ctx = research.get("context", "Competitors offer lower rates in this area.")
        script = _build_comcast_negotiation_script(
            task.user_name,
            task.current_rate or 85.0,
            task.target_rate or 65.0,
            ctx[:200],
            confirmation,
        )

    await _phase_call(task_id, call_id, script)
    await _phase_tool_calls(task_id, call_id, task.company,
                             research.get("context", ""), confirmation,
                             task.target_rate or 65.0)

    if task.action.value == "cancel_service":
        await _phase_cancellation_resolution(task_id, call_id, task.company,
                                              task.user_name, task.current_rate or 25.0, confirmation)
    else:
        await _phase_resolution(task_id, call_id, task.company,
                                 task.current_rate or 85.0, task.target_rate or 65.0, confirmation)

    # Send Gmail summary for this completed task
    completed = store.get_task(task_id)
    transcript_lines = [{"role": role, "text": text} for role, text, _ in script]
    await gmail_service.send_call_summary(task=completed, transcript=transcript_lines)


def _build_agent_performance(safety_report: dict, summary: str, duration: float) -> dict:
    """Build an intuitive agent performance report from Modulate data."""
    safety_score = safety_report.get("safety_score", 50)
    hostile = safety_report.get("rep_hostile_utterances", 0)
    pii = safety_report.get("pii_detected", 0)
    total = safety_report.get("total_utterances", 0)
    rep_emotions = safety_report.get("rep_emotion_summary", {})

    # Professionalism grade (A-F) based on safety + hostility
    prof_score = safety_score
    if hostile > 0:
        prof_score -= hostile * 15
    prof_score = max(0, min(100, prof_score))

    if prof_score >= 90:
        prof_grade = "A"
    elif prof_score >= 75:
        prof_grade = "B"
    elif prof_score >= 60:
        prof_grade = "C"
    elif prof_score >= 40:
        prof_grade = "D"
    else:
        prof_grade = "F"

    # Privacy grade based on PII exposure
    if pii == 0:
        privacy_grade = "A"
        privacy_note = "No sensitive data exposed"
    elif pii <= 2:
        privacy_grade = "B"
        privacy_note = f"{pii} item{'s' if pii > 1 else ''} detected, auto-redacted"
    elif pii <= 4:
        privacy_grade = "C"
        privacy_note = f"{pii} items flagged — review recommended"
    else:
        privacy_grade = "D"
        privacy_note = f"{pii} items exposed — needs attention"

    # Rep sentiment analysis
    positive_emotions = sum(rep_emotions.get(e, 0) for e in
        ["Happy", "Confident", "Interested", "Hopeful", "Relieved", "Amused"])
    negative_emotions = sum(rep_emotions.get(e, 0) for e in
        ["Frustrated", "Angry", "Contemptuous", "Stressed", "Anxious", "Disappointed"])
    neutral_emotions = sum(rep_emotions.get(e, 0) for e in
        ["Neutral", "Calm", "Bored", "Confused"])

    if positive_emotions > negative_emotions + neutral_emotions:
        rep_mood = "Cooperative"
        rep_icon = "positive"
    elif negative_emotions > positive_emotions:
        rep_mood = "Resistant"
        rep_icon = "negative"
    else:
        rep_mood = "Neutral"
        rep_icon = "neutral"

    # Efficiency based on call duration
    if duration and duration > 0:
        if duration < 120:
            efficiency = "Fast"
            efficiency_note = f"{int(duration)}s — quick resolution"
        elif duration < 300:
            efficiency = "Normal"
            efficiency_note = f"{int(duration // 60)}m {int(duration % 60)}s"
        else:
            efficiency = "Long"
            efficiency_note = f"{int(duration // 60)}m {int(duration % 60)}s — consider optimization"
    else:
        efficiency = "N/A"
        efficiency_note = ""

    return {
        "professionalism": {"grade": prof_grade, "score": prof_score},
        "privacy": {"grade": privacy_grade, "note": privacy_note, "pii_count": pii},
        "rep_sentiment": {"mood": rep_mood, "icon": rep_icon, "breakdown": rep_emotions},
        "efficiency": {"rating": efficiency, "note": efficiency_note, "duration": duration},
        "total_exchanges": total,
        "summary_note": safety_report.get("negotiation_dynamics", ""),
    }


async def _handle_status_update(message: dict, call_id: str):
    """Track call state: ringing, in-progress, ended."""
    status = message.get("status", "")

    logger.info("Call status: %s -> %s", call_id, status)

    # Update task status based on call state
    if status == "in-progress":
        for task in store.list_tasks():
            if task.call_id == call_id:
                store.update_task(task.id, status="calling")
                await store.push_task_update(task)
                break

    await store.push_event(SSEEvent(
        type=SSEEventType.CALL_STATUS,
        data={"call_id": call_id, "status": status},
    ))


async def _handle_transcript(message: dict, call_id: str):
    """Push real-time finalized transcript segments to SSE.

    Vapi sends transcript events with transcriptType "partial" or "final".
    We only push "final" to avoid flooding the dashboard with partial fragments.
    """
    transcript_type = message.get("transcriptType", "")
    transcript_text = message.get("transcript", "")
    role = message.get("role", "")

    # Only push finalized sentences — skip partials to avoid duplicates
    if transcript_type != "final" or not transcript_text:
        return

    # Normalize role for dashboard
    display_role = "agent" if role in ("assistant", "bot") else "rep"

    await store.push_event(SSEEvent(
        type=SSEEventType.TRANSCRIPT,
        data={
            "call_id": call_id,
            "role": display_role,
            "text": transcript_text,
        },
    ))
