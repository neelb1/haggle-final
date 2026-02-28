import { useEffect, useRef } from "react";

const EMOTION_COLORS = {
  // Positive
  Happy: "bg-green-500/20 text-green-400",
  Confident: "bg-emerald-500/20 text-emerald-400",
  Excited: "bg-green-400/20 text-green-300",
  Interested: "bg-teal-500/20 text-teal-400",
  Hopeful: "bg-cyan-500/20 text-cyan-400",
  Relieved: "bg-green-600/20 text-green-400",
  Amused: "bg-lime-500/20 text-lime-400",
  Proud: "bg-emerald-600/20 text-emerald-400",
  // Negative
  Frustrated: "bg-red-500/20 text-red-400",
  Angry: "bg-red-600/20 text-red-500",
  Contemptuous: "bg-red-700/20 text-red-500",
  Stressed: "bg-orange-500/20 text-orange-400",
  Anxious: "bg-amber-500/20 text-amber-400",
  Disappointed: "bg-orange-600/20 text-orange-400",
  Disgusted: "bg-red-400/20 text-red-300",
  // Neutral
  Neutral: "bg-gray-500/20 text-gray-400",
  Calm: "bg-blue-500/20 text-blue-400",
  Bored: "bg-gray-600/20 text-gray-500",
  Tired: "bg-gray-600/20 text-gray-500",
  Confused: "bg-yellow-500/20 text-yellow-400",
  Surprised: "bg-purple-500/20 text-purple-400",
};

function emotionColor(emotion) {
  return EMOTION_COLORS[emotion] || "bg-gray-500/20 text-gray-400";
}

function formatEvent(event) {
  const d = event.data || {};
  switch (event.type) {
    case "call_status":
      if (d.status === "awaiting_call")
        return {
          type: "call_prompt",
          phone: d.agent_phone_display || d.agent_phone,
          company: d.company,
          message: d.message,
        };
      if (d.status === "ringing")
        return { type: "status", icon: "phone", text: `Calling ${d.company || ""}...`, color: "text-accent-amber" };
      if (d.status === "in_progress")
        return { type: "status", icon: "connected", text: "Call connected", color: "text-accent-green" };
      if (d.status === "ended")
        return { type: "status", icon: "done", text: `Call completed  ${d.duration_seconds ? d.duration_seconds + "s" : ""}`, color: "text-accent-green" };
      return { type: "status", icon: "info", text: d.message || "Status update", color: "text-gray-400" };

    case "transcript":
      return { type: "chat", role: d.role, text: d.text || d.transcript || "" };

    case "entity_extracted":
      return {
        type: "extraction", icon: "extract",
        text: d.value, label: d.entity_type?.replace(/_/g, " "),
        extras: d.gliner2_extras,
        source: d.extraction_source,
        color: "text-accent-green",
      };

    case "graph_updated":
      return { type: "status", icon: "graph", text: `Knowledge graph updated`, color: "text-accent-purple" };

    case "call_summary":
      return { type: "summary", narrative: d.narrative, keyPoints: d.key_points };

    case "voice_analysis":
      return {
        type: "voice_analysis",
        callType: d.call_type,
        company: d.company || "",
        emotion: d.emotion || d.rep_emotion || "neutral",
        stress: d.stress_level ?? d.rep_stress_level ?? 0,
        score: d.certainty_score ?? d.compliance_score ?? 0,
        scoreLabel: d.call_type === "user_consult" ? "certainty" : "compliance",
        signals: d.behavioral_signals || [],
        insights: d.key_insights || [],
        recommendation: d.negotiation_recommendation || d.outcome_validation || "",
      };

    case "emotion":
      return { type: "emotion", emotion: d.emotion, text: d.context, confidence: d.confidence };

    case "modulate_analysis":
      return {
        type: "modulate",
        safetyReport: d.safety_report,
        timeline: d.emotion_timeline,
        agentPerf: d.agent_performance,
      };

    case "pii_detected":
      return {
        type: "pii_alert",
        count: d.count,
        items: d.items,
      };

    case "bill_analyzed":
      return {
        type: "bill",
        provider: d.provider_name,
        total: d.total_amount,
        change: d.price_change,
        taskCreated: d.auto_task_created,
      };

    case "tool_call": {
      const TOOL_LABELS = {
        search_task_context: "Retrieving task context",
        tavily_search: "Searching web (Tavily)",
        extract_entities: "Extracting entities",
        update_neo4j: "Updating knowledge graph",
        end_task: "Completing task",
      };
      return {
        type: "tool",
        tool: d.tool,
        text: TOOL_LABELS[d.tool] || d.tool,
      };
    }

    case "task_updated":
      if (d.confirmed_action)
        return { type: "confirmed", service: d.confirmed_action.service, action: d.confirmed_action.action, savings: d.confirmed_action.monthly_savings, reason: d.confirmed_action.reason };
      if (d.phase === "dispatch")
        return { type: "status", icon: "phone", text: d.message || "Dispatching service calls...", color: "text-accent-amber" };
      if (d.phase === "research")
        return { type: "status", icon: "search", text: d.message || "Researching...", color: "text-accent-blue" };
      if (d.phase === "research_complete")
        return { type: "status", icon: "check", text: "Research complete", color: "text-accent-green" };
      if (d.tool_call)
        return { type: "tool", text: d.message || d.tool_call, tool: d.tool_call };
      if (d.tasks)
        return null;
      if (d.status)
        return { type: "status", icon: "info", text: `Task ${d.status}`, color: "text-accent-blue" };
      return null;

    default:
      return null;
  }
}

const STATUS_ICONS = {
  phone: (
    <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M3 5a2 2 0 012-2h3.28a1 1 0 01.948.684l1.498 4.493a1 1 0 01-.502 1.21l-2.257 1.13a11.042 11.042 0 005.516 5.516l1.13-2.257a1 1 0 011.21-.502l4.493 1.498a1 1 0 01.684.949V19a2 2 0 01-2 2h-1C9.716 21 3 14.284 3 6V5z" />
    </svg>
  ),
  connected: (
    <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
    </svg>
  ),
  done: (
    <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
    </svg>
  ),
  search: (
    <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
    </svg>
  ),
  check: (
    <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
    </svg>
  ),
  graph: (
    <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
      <circle cx="6" cy="6" r="2" /><circle cx="18" cy="18" r="2" /><circle cx="18" cy="6" r="2" />
      <path d="M8 6h8M6 8v8l10 2" />
    </svg>
  ),
  extract: (
    <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A2 2 0 013 12V7a4 4 0 014-4z" />
    </svg>
  ),
  info: (
    <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
    </svg>
  ),
  shield: (
    <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
    </svg>
  ),
  lock: (
    <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
    </svg>
  ),
};

function GradeBadge({ grade, label }) {
  const colors = {
    A: "text-green-400 bg-green-500/15 border-green-500/30",
    B: "text-emerald-400 bg-emerald-500/15 border-emerald-500/30",
    C: "text-amber-400 bg-amber-500/15 border-amber-500/30",
    D: "text-orange-400 bg-orange-500/15 border-orange-500/30",
    F: "text-red-400 bg-red-500/15 border-red-500/30",
  };
  return (
    <div className="flex flex-col items-center gap-0.5">
      <span className={`text-[18px] font-black px-2.5 py-0.5 rounded-lg border ${colors[grade] || colors.C}`}>
        {grade}
      </span>
      <span className="text-[8px] text-gray-500 uppercase tracking-wider">{label}</span>
    </div>
  );
}

function SentimentDot({ mood }) {
  const config = {
    Cooperative: { color: "bg-green-400", pulse: true },
    Resistant: { color: "bg-red-400", pulse: false },
    Neutral: { color: "bg-gray-400", pulse: false },
  };
  const c = config[mood] || config.Neutral;
  return (
    <span className={`inline-block w-2 h-2 rounded-full ${c.color} ${c.pulse ? "animate-pulse" : ""}`} />
  );
}

export default function LiveCall({ events }) {
  const scrollRef = useRef(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [events.length]);

  const formatted = events.map(formatEvent).filter(Boolean);

  return (
    <div className="card h-full flex flex-col">
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-xs font-semibold text-gray-500 uppercase tracking-widest">
          Live Agent Feed
        </h2>
        {formatted.some(f => f.type === "chat") && (
          <div className="flex items-center gap-1.5">
            <span className="pulse-dot" />
            <span className="text-[10px] text-accent-green font-semibold uppercase tracking-wider">Active</span>
          </div>
        )}
      </div>

      <div ref={scrollRef} className="flex-1 overflow-y-auto space-y-2 pr-1 min-h-0">
        {formatted.map((item, i) => {
          if (!item) return null;
          const isNew = i === formatted.length - 1;

          if (item.type === "chat") {
            const isAgent = item.role === "agent";
            const isUser = item.role === "user"; // person being called in consult
            const label = isAgent ? "Haggle Agent" : isUser ? "You (User)" : "Customer Rep";
            return (
              <div
                key={i}
                className={`flex ${isAgent ? "justify-start" : "justify-end"} ${isNew ? "animate-slide-up" : ""}`}
              >
                <div className={`max-w-[85%] px-3.5 py-2.5 ${isAgent ? "bubble-agent" : "bubble-rep"}`}>
                  <div className={`text-[10px] font-semibold mb-1 ${isAgent ? "text-accent-blue/70" : isUser ? "text-accent-green/70" : "text-gray-500"}`}>
                    {label}
                  </div>
                  <p className="text-[13px] leading-relaxed text-gray-200">{item.text}</p>
                </div>
              </div>
            );
          }

          if (item.type === "confirmed") {
            const actionLabel = item.action === "cancel_service" ? "Cancel" : "Negotiate";
            return (
              <div key={i} className={`flex justify-center ${isNew ? "animate-count-up" : ""}`}>
                <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-accent-green/10 border border-accent-green/25">
                  <span className="text-accent-green text-xs font-bold">✓ Confirmed</span>
                  <span className="text-gray-400 text-[10px]">{actionLabel} {item.service}</span>
                  <span className="text-accent-green text-[10px] font-semibold">–${item.savings}/mo</span>
                </div>
              </div>
            );
          }

          if (item.type === "summary") {
            return (
              <div key={i} className={`${isNew ? "animate-fade-in" : ""} mb-1`}>
                <div className="p-3.5 rounded-xl bg-accent-blue/5 border border-accent-blue/15">
                  <div className="flex items-center gap-1.5 mb-2">
                    <svg className="w-3 h-3 text-accent-blue" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                    </svg>
                    <span className="text-[10px] font-semibold text-accent-blue uppercase tracking-wider">Agent Summary</span>
                  </div>
                  <p className="text-[12px] text-gray-300 leading-relaxed mb-2.5">{item.narrative}</p>
                  <ul className="space-y-1">
                    {item.keyPoints?.map((pt, idx) => (
                      <li key={idx} className="flex items-start gap-1.5 text-[11px] text-gray-400">
                        <span className="text-accent-green mt-px shrink-0">✓</span>
                        <span>{pt}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              </div>
            );
          }

          if (item.type === "extraction") {
            return (
              <div key={i} className={`flex flex-col items-center gap-1 ${isNew ? "animate-count-up" : ""}`}>
                <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-accent-green/10 border border-accent-green/20">
                  <span className="text-accent-green">{STATUS_ICONS.extract}</span>
                  <span className="text-[10px] text-gray-500 uppercase">{item.label}</span>
                  <span className="text-xs font-bold text-accent-green">{item.text}</span>
                  {item.source && (
                    <span className="text-[8px] text-gray-600 font-mono">{item.source}</span>
                  )}
                </div>
                {item.extras && item.extras.length > 0 && (
                  <div className="flex flex-wrap gap-1 justify-center">
                    {item.extras.map((e, j) => (
                      <span key={j} className="text-[9px] px-1.5 py-0.5 rounded-full bg-accent-blue/10 text-accent-blue border border-accent-blue/20">
                        GLiNER2: {e}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            );
          }

          if (item.type === "emotion") {
            return (
              <div key={i} className={`flex justify-center ${isNew ? "animate-fade-in" : ""}`}>
                <div className="text-[10px] text-gray-600 italic">
                  Sentiment: {item.emotion} ({(item.confidence * 100).toFixed(0)}%)
                </div>
              </div>
            );
          }

          if (item.type === "voice_analysis") {
            const isConsult = item.callType === "user_consult";
            const header = isConsult
              ? "Velma 2 — User Voice Analysis"
              : `Velma 2 — ${item.company || "Provider"} Call Analysis`;
            const stressPct = Math.round((item.stress || 0) * 100);
            const scorePct = Math.round((item.score || 0) * 100);
            return (
              <div key={i} className={`${isNew ? "animate-fade-in" : ""} mb-1`}>
                <div className="p-3 rounded-xl bg-accent-purple/8 border border-accent-purple/20">
                  <div className="flex items-center gap-1.5 mb-2.5">
                    <svg className="w-3 h-3 text-accent-purple shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M9 19V6l12-3v13M9 19c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zm12-3c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zM9 10l12-3" />
                    </svg>
                    <span className="text-[10px] font-bold text-accent-purple uppercase tracking-wider">{header}</span>
                  </div>
                  <div className="flex items-center gap-3 mb-2.5">
                    <span className="text-[10px] px-2 py-0.5 rounded-full bg-accent-purple/15 text-accent-purple font-medium capitalize">{item.emotion}</span>
                    <div className="flex items-center gap-1.5 text-[10px] text-gray-500">
                      <span>stress</span>
                      <div className="w-16 h-1.5 rounded-full bg-dark-600">
                        <div className="h-full rounded-full bg-accent-amber" style={{ width: `${stressPct}%` }} />
                      </div>
                      <span className="text-gray-400">{stressPct}%</span>
                    </div>
                    <div className="flex items-center gap-1.5 text-[10px] text-gray-500">
                      <span>{item.scoreLabel}</span>
                      <div className="w-16 h-1.5 rounded-full bg-dark-600">
                        <div className="h-full rounded-full bg-accent-green" style={{ width: `${scorePct}%` }} />
                      </div>
                      <span className="text-accent-green font-semibold">{scorePct}%</span>
                    </div>
                  </div>
                  {item.insights.length > 0 && (
                    <ul className="space-y-0.5 mb-2">
                      {item.insights.slice(0, 3).map((ins, idx) => (
                        <li key={idx} className="flex items-start gap-1.5 text-[11px] text-gray-400">
                          <span className="text-accent-purple mt-px shrink-0">◆</span>
                          <span>{ins}</span>
                        </li>
                      ))}
                    </ul>
                  )}
                  {item.recommendation && (
                    <p className="text-[10px] text-accent-purple/70 italic border-t border-accent-purple/10 pt-1.5 mt-1.5">
                      {item.recommendation.slice(0, 140)}{item.recommendation.length > 140 ? "…" : ""}
                    </p>
                  )}
                </div>
              </div>
            );
          }

          {/* Agent Performance Report (Modulate Voice Analysis) */}
          if (item.type === "modulate") {
            const perf = item.agentPerf || {};
            const r = item.safetyReport || {};
            const hasPerf = perf.professionalism;
            return (
              <div key={i} className={`flex justify-center ${isNew ? "animate-slide-up" : ""}`}>
                <div className="w-full max-w-md p-3 rounded-xl bg-dark-700/50 border border-purple-500/20 space-y-3">
                  {/* Header */}
                  <div className="flex items-center gap-1.5">
                    <span className="text-purple-400">{STATUS_ICONS.shield}</span>
                    <span className="text-[10px] font-semibold text-purple-400 uppercase tracking-wider">
                      Agent Performance Report
                    </span>
                    <span className="text-[8px] text-gray-600 ml-auto">powered by Modulate</span>
                  </div>

                  {hasPerf ? (
                    <>
                      {/* Grade Cards */}
                      <div className="grid grid-cols-3 gap-3">
                        <GradeBadge grade={perf.professionalism?.grade || "?"} label="Professionalism" />
                        <GradeBadge grade={perf.privacy?.grade || "?"} label="Privacy" />
                        <div className="flex flex-col items-center gap-0.5">
                          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg border border-gray-700 bg-dark-800/50">
                            <SentimentDot mood={perf.rep_sentiment?.mood} />
                            <span className="text-[13px] font-bold text-gray-200">{perf.rep_sentiment?.mood || "N/A"}</span>
                          </div>
                          <span className="text-[8px] text-gray-500 uppercase tracking-wider">Rep Mood</span>
                        </div>
                      </div>

                      {/* Stats Row */}
                      <div className="flex items-center justify-between text-[10px] text-gray-400 px-1">
                        <span>{perf.total_exchanges || 0} exchanges</span>
                        <span>{perf.efficiency?.note || ""}</span>
                        <span>{perf.privacy?.note || ""}</span>
                      </div>

                      {/* Rep emotions */}
                      {perf.rep_sentiment?.breakdown && Object.keys(perf.rep_sentiment.breakdown).length > 0 && (
                        <div className="flex flex-wrap gap-1">
                          {Object.entries(perf.rep_sentiment.breakdown).map(([emotion, count]) => (
                            <span key={emotion} className={`text-[9px] px-1.5 py-0.5 rounded-full ${emotionColor(emotion)}`}>
                              {emotion} x{count}
                            </span>
                          ))}
                        </div>
                      )}

                      {/* Summary note */}
                      {perf.summary_note && (
                        <p className="text-[10px] text-gray-400 italic leading-snug border-t border-gray-800 pt-2">
                          {perf.summary_note}
                        </p>
                      )}
                    </>
                  ) : (
                    /* Fallback: show raw safety data if no perf report */
                    <div className="grid grid-cols-3 gap-2 text-center">
                      <div>
                        <div className="text-[18px] font-bold text-gray-200">{r.total_utterances || 0}</div>
                        <div className="text-[9px] text-gray-500">Exchanges</div>
                      </div>
                      <div>
                        <div className="text-[18px] font-bold text-red-400">{r.rep_hostile_utterances || 0}</div>
                        <div className="text-[9px] text-gray-500">Hostile</div>
                      </div>
                      <div>
                        <div className="text-[18px] font-bold text-amber-400">{r.pii_detected || 0}</div>
                        <div className="text-[9px] text-gray-500">PII Found</div>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            );
          }

          if (item.type === "pii_alert") {
            return (
              <div key={i} className={`flex justify-center ${isNew ? "animate-slide-up" : ""}`}>
                <div className="inline-flex items-center gap-2 px-3 py-2 rounded-lg bg-red-500/10 border border-red-500/30">
                  <span className="text-red-400">{STATUS_ICONS.lock}</span>
                  <span className="text-[11px] font-semibold text-red-400">
                    {item.count} PII item{item.count !== 1 ? "s" : ""} detected — auto-redacted
                  </span>
                </div>
              </div>
            );
          }

          if (item.type === "bill") {
            return (
              <div key={i} className={`flex justify-center ${isNew ? "animate-slide-up" : ""}`}>
                <div className="inline-flex items-center gap-2 px-3 py-2 rounded-lg bg-cyan-500/10 border border-cyan-500/20">
                  <span className="text-[11px] text-cyan-400 font-semibold">
                    Reka Vision: {item.provider} bill {item.total}
                    {item.change && <span className="text-red-400 ml-1">({item.change})</span>}
                    {item.taskCreated && <span className="text-accent-green ml-1">Task created</span>}
                  </span>
                </div>
              </div>
            );
          }

          if (item.type === "call_prompt") {
            return (
              <div key={i} className={`flex justify-center ${isNew ? "animate-slide-up" : ""}`}>
                <div className="w-full max-w-sm p-4 rounded-xl bg-accent-blue/10 border border-accent-blue/30 text-center space-y-2">
                  <div className="flex items-center justify-center gap-2">
                    <span className="inline-block w-2.5 h-2.5 rounded-full bg-accent-green animate-pulse" />
                    <span className="text-xs font-semibold text-accent-green uppercase tracking-wider">Agent Ready</span>
                  </div>
                  <p className="text-sm text-gray-300">
                    Call your Haggle agent — you play <span className="text-white font-semibold">{item.company}</span>
                  </p>
                  <a
                    href={`tel:${item.phone}`}
                    className="inline-block text-2xl font-bold text-accent-blue tracking-wide hover:text-accent-blue/80 transition-colors"
                  >
                    {item.phone}
                  </a>
                  <p className="text-[10px] text-gray-500">
                    The agent will negotiate with you as if you're {item.company}'s rep
                  </p>
                </div>
              </div>
            );
          }

          if (item.type === "tool") {
            return (
              <div key={i} className={`flex justify-center ${isNew ? "animate-slide-up" : ""}`}>
                <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-accent-amber/10 border border-accent-amber/25">
                  <span className="inline-block w-1.5 h-1.5 rounded-full bg-accent-amber animate-pulse" />
                  <span className="text-[10px] text-accent-amber font-semibold uppercase tracking-wider">Tool Call</span>
                  <span className="text-[11px] text-gray-300 font-medium">{item.text}</span>
                </div>
              </div>
            );
          }

          // Status events
          return (
            <div key={i} className={`flex justify-center ${isNew ? "animate-fade-in" : ""}`}>
              <div className="inline-flex items-center gap-1.5 px-3 py-1.5 text-[11px]">
                <span className={item.color}>{STATUS_ICONS[item.icon] || STATUS_ICONS.info}</span>
                <span className={`${item.color} font-medium`}>{item.text}</span>
              </div>
            </div>
          );
        })}

        {formatted.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full text-center py-8">
            <div className="w-12 h-12 rounded-2xl bg-dark-700 flex items-center justify-center mb-3">
              <svg className="w-6 h-6 text-gray-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M3 5a2 2 0 012-2h3.28a1 1 0 01.948.684l1.498 4.493a1 1 0 01-.502 1.21l-2.257 1.13a11.042 11.042 0 005.516 5.516l1.13-2.257a1 1 0 011.21-.502l4.493 1.498a1 1 0 01.684.949V19a2 2 0 01-2 2h-1C9.716 21 3 14.284 3 6V5z" />
              </svg>
            </div>
            <p className="text-sm text-gray-500 font-medium">No active calls</p>
            <p className="text-xs text-gray-600 mt-1">Click "Call Me" to start the autonomous loop, or "Run Demo" to jump straight to negotiation</p>
          </div>
        )}
      </div>
    </div>
  );
}
