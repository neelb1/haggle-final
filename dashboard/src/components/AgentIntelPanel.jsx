import { useMemo } from "react";

const EMOTION_COLORS = {
  Happy: "bg-green-500/20 text-green-400",
  Confident: "bg-emerald-500/20 text-emerald-400",
  Excited: "bg-green-400/20 text-green-300",
  Interested: "bg-teal-500/20 text-teal-400",
  Hopeful: "bg-cyan-500/20 text-cyan-400",
  Relieved: "bg-green-600/20 text-green-400",
  Frustrated: "bg-red-500/20 text-red-400",
  Angry: "bg-red-600/20 text-red-500",
  Stressed: "bg-orange-500/20 text-orange-400",
  Anxious: "bg-amber-500/20 text-amber-400",
  Neutral: "bg-gray-500/20 text-gray-400",
  Calm: "bg-blue-500/20 text-blue-400",
  Confused: "bg-yellow-500/20 text-yellow-400",
  Surprised: "bg-purple-500/20 text-purple-400",
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
    <div className="flex flex-col items-center gap-1">
      <span className={`text-2xl font-black px-3 py-1 rounded-xl border ${colors[grade] || colors.C}`}>
        {grade}
      </span>
      <span className="text-[9px] text-gray-500 uppercase tracking-wider font-medium">{label}</span>
    </div>
  );
}

function MeterBar({ value, max = 1, label, color = "bg-accent-blue", showPct = true }) {
  const pct = Math.round((value / max) * 100);
  return (
    <div className="flex items-center gap-2">
      <span className="text-[10px] text-gray-500 w-16 text-right shrink-0">{label}</span>
      <div className="flex-1 h-2 rounded-full bg-dark-600 overflow-hidden">
        <div
          className={`h-full rounded-full ${color} transition-all duration-700`}
          style={{ width: `${pct}%` }}
        />
      </div>
      {showPct && <span className="text-[10px] text-gray-400 w-8 tabular-nums">{pct}%</span>}
    </div>
  );
}

export default function AgentIntelPanel({ events }) {
  // Get the latest voice analysis, modulate report, and PII alerts
  const { latestVoice, allVoice, latestModulate, piiCount, emotionTimeline } = useMemo(() => {
    let latestVoice = null;
    let latestModulate = null;
    let piiCount = 0;
    const allVoice = [];
    const emotionTimeline = [];

    for (const ev of events) {
      if (ev.type === "voice_analysis") {
        latestVoice = ev.data;
        allVoice.push(ev.data);
        if (ev.data?.emotion) {
          emotionTimeline.push(ev.data.emotion);
        }
      }
      if (ev.type === "modulate_analysis") {
        latestModulate = ev.data;
      }
      if (ev.type === "pii_detected") {
        piiCount += ev.data?.count || 0;
      }
      if (ev.type === "emotion" && ev.data?.emotion) {
        emotionTimeline.push(ev.data.emotion);
      }
    }

    return { latestVoice, allVoice, latestModulate, piiCount, emotionTimeline };
  }, [events]);

  const perf = latestModulate?.agent_performance || {};
  const hasPerf = !!perf.professionalism;
  const hasVoice = !!latestVoice;
  const hasData = hasVoice || hasPerf;

  return (
    <div className="card h-full flex flex-col overflow-hidden">
      <div className="flex items-center gap-2 mb-3">
        <div className="w-6 h-6 rounded-lg bg-gradient-to-br from-violet-500/20 to-purple-500/20 border border-violet-500/30 flex items-center justify-center">
          <svg className="w-3.5 h-3.5 text-violet-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M9 3v2m6-2v2M9 19v2m6-2v2M5 9H3m2 6H3m18-6h-2m2 6h-2M7 19h10a2 2 0 002-2V7a2 2 0 00-2-2H7a2 2 0 00-2 2v10a2 2 0 002 2zM9 9h6v6H9V9z" />
          </svg>
        </div>
        <h2 className="text-xs font-semibold text-gray-400 uppercase tracking-widest">
          Agent Intelligence
        </h2>
        {hasVoice && (
          <span className="ml-auto flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-violet-400 animate-pulse" />
            <span className="text-[10px] text-violet-400 font-semibold">Live</span>
          </span>
        )}
      </div>

      <div className="flex-1 overflow-y-auto space-y-3 pr-1 min-h-0">
        {hasData ? (
          <>
            {/* Voice Metrics */}
            {hasVoice && (
              <div className="rounded-xl p-3.5 bg-violet-500/5 border border-violet-500/20">
                <div className="flex items-center gap-1.5 mb-3">
                  <svg className="w-3.5 h-3.5 text-violet-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" />
                  </svg>
                  <span className="text-[10px] font-bold text-violet-400 uppercase tracking-wider">
                    Voice Analysis — Modulate Velma 2
                  </span>
                </div>

                {/* Current emotion */}
                <div className="flex items-center gap-3 mb-3">
                  <span className={`text-sm px-3 py-1 rounded-full font-semibold ${EMOTION_COLORS[latestVoice.emotion] || EMOTION_COLORS.Neutral}`}>
                    {latestVoice.emotion || "Neutral"}
                  </span>
                  <span className="text-[10px] text-gray-500">
                    {latestVoice.call_type === "user_consult" ? "User Consult" : latestVoice.company || "Provider Call"}
                  </span>
                </div>

                {/* Meters */}
                <div className="space-y-2">
                  <MeterBar
                    value={latestVoice.stress_level ?? 0}
                    label="Stress"
                    color="bg-gradient-to-r from-green-400 to-red-400"
                  />
                  <MeterBar
                    value={latestVoice.certainty_score ?? latestVoice.compliance_score ?? 0}
                    label={latestVoice.call_type === "user_consult" ? "Certainty" : "Compliance"}
                    color="bg-gradient-to-r from-blue-400 to-emerald-400"
                  />
                </div>

                {/* Emotion timeline */}
                {emotionTimeline.length > 1 && (
                  <div className="mt-3 pt-2 border-t border-violet-500/10">
                    <div className="text-[9px] text-gray-600 mb-1.5 uppercase tracking-wider">Emotion Flow</div>
                    <div className="flex flex-wrap gap-1">
                      {emotionTimeline.slice(-10).map((em, i) => (
                        <span key={i} className={`text-[9px] px-1.5 py-0.5 rounded-full ${EMOTION_COLORS[em] || EMOTION_COLORS.Neutral}`}>
                          {em}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Behavioral Signals */}
            {hasVoice && latestVoice.behavioral_signals?.length > 0 && (
              <div className="rounded-xl p-3.5 bg-dark-700/40 border border-dark-600/50">
                <div className="flex items-center gap-1.5 mb-2.5">
                  <svg className="w-3.5 h-3.5 text-cyan-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                  </svg>
                  <span className="text-[10px] font-bold text-cyan-400 uppercase tracking-wider">Behavioral Signals</span>
                </div>
                <div className="space-y-1.5">
                  {latestVoice.behavioral_signals.map((signal, i) => {
                    const [key, value] = signal.includes(":") ? signal.split(":").map((s) => s.trim()) : [signal, ""];
                    return (
                      <div key={i} className="flex items-center justify-between px-2 py-1.5 rounded-lg bg-dark-600/30">
                        <span className="text-[11px] text-gray-400">{key}</span>
                        {value && (
                          <span className={`text-[11px] font-semibold ${
                            value === "high" ? "text-red-400" :
                            value === "medium" ? "text-amber-400" :
                            value === "low" ? "text-green-400" :
                            value === "fast" ? "text-blue-400" :
                            "text-gray-300"
                          }`}>
                            {value}
                          </span>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            {/* Agent Coaching */}
            {hasVoice && (latestVoice.negotiation_recommendation || latestVoice.key_insights?.length > 0) && (
              <div className="rounded-xl p-3.5 bg-amber-500/5 border border-amber-500/20">
                <div className="flex items-center gap-1.5 mb-2.5">
                  <svg className="w-3.5 h-3.5 text-amber-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                  </svg>
                  <span className="text-[10px] font-bold text-amber-400 uppercase tracking-wider">Agent Coaching</span>
                </div>
                {latestVoice.key_insights?.map((insight, i) => (
                  <p key={i} className="text-[11px] text-gray-300 leading-relaxed mb-1 flex items-start gap-1.5">
                    <span className="text-amber-400 shrink-0 mt-0.5">&#9670;</span>
                    {insight}
                  </p>
                ))}
                {latestVoice.negotiation_recommendation && (
                  <p className="text-[11px] text-amber-300/80 italic mt-2 pt-2 border-t border-amber-500/10 leading-relaxed">
                    {latestVoice.negotiation_recommendation}
                  </p>
                )}
              </div>
            )}

            {/* Performance Report Card */}
            {hasPerf && (
              <div className="rounded-xl p-3.5 bg-purple-500/5 border border-purple-500/20">
                <div className="flex items-center gap-1.5 mb-3">
                  <svg className="w-3.5 h-3.5 text-purple-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                  </svg>
                  <span className="text-[10px] font-bold text-purple-400 uppercase tracking-wider">Performance Report Card</span>
                  <span className="text-[8px] text-gray-600 ml-auto">powered by Modulate</span>
                </div>

                {/* Grades */}
                <div className="flex items-center justify-around mb-3">
                  <GradeBadge grade={perf.professionalism?.grade || "?"} label="Professional" />
                  <GradeBadge grade={perf.privacy?.grade || "?"} label="Privacy" />
                  <div className="flex flex-col items-center gap-1">
                    <div className="flex items-center gap-2 px-3 py-1.5 rounded-xl border border-gray-700 bg-dark-800/50">
                      <span className={`w-2.5 h-2.5 rounded-full ${
                        perf.rep_sentiment?.mood === "Cooperative" ? "bg-green-400 animate-pulse" :
                        perf.rep_sentiment?.mood === "Resistant" ? "bg-red-400" : "bg-gray-400"
                      }`} />
                      <span className="text-sm font-bold text-gray-200">{perf.rep_sentiment?.mood || "N/A"}</span>
                    </div>
                    <span className="text-[9px] text-gray-500 uppercase tracking-wider font-medium">Rep Mood</span>
                  </div>
                </div>

                {/* Stats */}
                <div className="grid grid-cols-3 gap-2 mb-3">
                  <div className="text-center py-2 rounded-lg bg-dark-700/50">
                    <div className="text-lg font-bold text-gray-200 tabular-nums">{perf.total_exchanges || 0}</div>
                    <div className="text-[9px] text-gray-500">Exchanges</div>
                  </div>
                  <div className="text-center py-2 rounded-lg bg-dark-700/50">
                    <div className="text-lg font-bold text-emerald-400 tabular-nums">{piiCount}</div>
                    <div className="text-[9px] text-gray-500">PII Blocked</div>
                  </div>
                  <div className="text-center py-2 rounded-lg bg-dark-700/50">
                    <div className="text-lg font-bold text-gray-200">{perf.efficiency?.rating || "—"}</div>
                    <div className="text-[9px] text-gray-500">Efficiency</div>
                  </div>
                </div>

                {/* Emotion breakdown */}
                {perf.rep_sentiment?.breakdown && Object.keys(perf.rep_sentiment.breakdown).length > 0 && (
                  <div className="mb-2">
                    <div className="text-[9px] text-gray-600 mb-1.5 uppercase tracking-wider">Rep Emotion Breakdown</div>
                    <div className="flex flex-wrap gap-1">
                      {Object.entries(perf.rep_sentiment.breakdown).map(([emotion, count]) => (
                        <span key={emotion} className={`text-[10px] px-2 py-0.5 rounded-full ${EMOTION_COLORS[emotion] || "bg-gray-500/20 text-gray-400"}`}>
                          {emotion} x{count}
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                {/* Summary */}
                {perf.summary_note && (
                  <p className="text-[11px] text-gray-400 italic leading-relaxed border-t border-purple-500/10 pt-2">
                    {perf.summary_note}
                  </p>
                )}
              </div>
            )}
          </>
        ) : (
          <div className="flex flex-col items-center justify-center h-full text-center py-8">
            <div className="w-12 h-12 rounded-2xl bg-dark-700 flex items-center justify-center mb-3">
              <svg className="w-6 h-6 text-gray-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M9 3v2m6-2v2M9 19v2m6-2v2M5 9H3m2 6H3m18-6h-2m2 6h-2M7 19h10a2 2 0 002-2V7a2 2 0 00-2-2H7a2 2 0 00-2 2v10a2 2 0 002 2zM9 9h6v6H9V9z" />
              </svg>
            </div>
            <p className="text-sm text-gray-500 font-medium">No intelligence data yet</p>
            <p className="text-xs text-gray-600 mt-1">Voice analysis and agent metrics appear during active calls</p>
          </div>
        )}
      </div>
    </div>
  );
}
