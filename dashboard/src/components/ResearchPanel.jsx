import { useMemo } from "react";
import KnowledgeGraph from "./KnowledgeGraph";

const STEP_ICONS = {
  detection: (
    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
    </svg>
  ),
  research: (
    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
    </svg>
  ),
  tool: (
    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.066 2.573c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.573 1.066c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.066-2.573c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
      <path strokeLinecap="round" strokeLinejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
    </svg>
  ),
  call: (
    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M3 5a2 2 0 012-2h3.28a1 1 0 01.948.684l1.498 4.493a1 1 0 01-.502 1.21l-2.257 1.13a11.042 11.042 0 005.516 5.516l1.13-2.257a1 1 0 011.21-.502l4.493 1.498a1 1 0 01.684.949V19a2 2 0 01-2 2h-1C9.716 21 3 14.284 3 6V5z" />
    </svg>
  ),
  entity: (
    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A2 2 0 013 12V7a4 4 0 014-4z" />
    </svg>
  ),
  graph: (
    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
      <circle cx="6" cy="6" r="2" /><circle cx="18" cy="18" r="2" /><circle cx="18" cy="6" r="2" />
      <path d="M8 6h8M6 8v8l10 2" />
    </svg>
  ),
  voice: (
    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M9 19V6l12-3v13M9 19c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zm12-3c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zM9 10l12-3" />
    </svg>
  ),
  summary: (
    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
    </svg>
  ),
  strategy: (
    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
    </svg>
  ),
};

const STEP_COLORS = {
  detection: { bg: "bg-red-500/10", border: "border-red-500/30", text: "text-red-400", dot: "bg-red-400" },
  research: { bg: "bg-blue-500/10", border: "border-blue-500/30", text: "text-blue-400", dot: "bg-blue-400" },
  tool: { bg: "bg-amber-500/10", border: "border-amber-500/30", text: "text-amber-400", dot: "bg-amber-400" },
  call: { bg: "bg-green-500/10", border: "border-green-500/30", text: "text-green-400", dot: "bg-green-400" },
  entity: { bg: "bg-emerald-500/10", border: "border-emerald-500/30", text: "text-emerald-400", dot: "bg-emerald-400" },
  graph: { bg: "bg-purple-500/10", border: "border-purple-500/30", text: "text-purple-400", dot: "bg-purple-400" },
  voice: { bg: "bg-violet-500/10", border: "border-violet-500/30", text: "text-violet-400", dot: "bg-violet-400" },
  summary: { bg: "bg-green-500/10", border: "border-green-500/30", text: "text-green-400", dot: "bg-green-400" },
  strategy: { bg: "bg-cyan-500/10", border: "border-cyan-500/30", text: "text-cyan-400", dot: "bg-cyan-400" },
};

function buildReasoningChain(events) {
  const steps = [];

  for (const ev of events) {
    const d = ev.data || {};

    if (ev.type === "task_updated") {
      if (d.phase === "research") {
        steps.push({
          category: "research",
          label: "Research Phase",
          detail: d.message || "Gathering competitive intelligence and context...",
          source: "Tavily + Senso",
        });
      }
      if (d.phase === "research_complete") {
        steps.push({
          category: "strategy",
          label: "Strategy Formed",
          detail: "Analysis complete — negotiation approach determined",
          source: "Haggle Engine",
        });
      }
      if (d.confirmed_action) {
        steps.push({
          category: "summary",
          label: `User Confirmed: ${d.confirmed_action.action === "cancel_service" ? "Cancel" : "Negotiate"} ${d.confirmed_action.service}`,
          detail: d.confirmed_action.reason || `Target savings: $${d.confirmed_action.monthly_savings}/mo`,
          source: "User Decision",
          highlight: true,
        });
      }
      if (d.phase === "dispatch") {
        steps.push({
          category: "call",
          label: "Dispatching Service Calls",
          detail: d.message || "Initiating autonomous negotiation...",
          source: "Vapi",
        });
      }
    }

    if (ev.type === "tool_call") {
      const toolLabels = {
        tavily_search: { label: "Web Intelligence Search", detail: "Searching competitor rates, retention offers, and market data", source: "Tavily" },
        search_task_context: { label: "Loading Task Context", detail: "Retrieving subscription details and negotiation parameters", source: "Context Store" },
        extract_entities: { label: "Entity Extraction", detail: "Parsing call for confirmation numbers, prices, account details", source: "GLiNER2" },
        update_neo4j: { label: "Knowledge Graph Update", detail: "Persisting negotiation results and subscription changes", source: "Neo4j" },
        end_task: { label: "Task Completed", detail: "Marking task as resolved with final outcome", source: "Haggle Engine" },
        get_subscription_analysis: { label: "Subscription Analysis", detail: "Analyzing user's subscription portfolio for optimization", source: "Analytics" },
        confirm_action: { label: "Action Confirmed", detail: "Recording user's confirmed decision", source: "User Input" },
        calculate_cost_per_use: { label: "Cost-Per-Use Analysis", detail: "Calculating actual value vs. cost of subscription", source: "Analytics" },
      };
      const info = toolLabels[d.tool] || { label: d.tool, detail: "Processing...", source: "Agent" };
      steps.push({ category: "tool", ...info });
    }

    if (ev.type === "call_status") {
      if (d.status === "ringing") {
        steps.push({
          category: "call",
          label: `Calling ${d.company || "Provider"}`,
          detail: "Connecting to service provider...",
          source: "Vapi",
        });
      }
      if (d.status === "in_progress") {
        steps.push({
          category: "call",
          label: "Call Connected",
          detail: `Live negotiation in progress${d.company ? ` with ${d.company}` : ""}`,
          source: "Vapi",
        });
      }
      if (d.status === "ended") {
        steps.push({
          category: "summary",
          label: "Call Completed",
          detail: `Duration: ${d.duration_seconds || "?"}s${d.outcome ? ` — ${d.outcome}` : ""}`,
          source: "Vapi",
          highlight: d.outcome === "success",
        });
      }
    }

    if (ev.type === "voice_analysis") {
      const insights = d.key_insights || [];
      if (insights.length > 0) {
        steps.push({
          category: "voice",
          label: `Voice Intelligence: ${d.emotion || "Analysis"}`,
          detail: insights[0],
          extras: insights.slice(1, 3),
          source: "Modulate Velma 2",
        });
      }
    }

    if (ev.type === "entity_extracted") {
      steps.push({
        category: "entity",
        label: (d.entity_type || "entity").replace(/_/g, " "),
        detail: d.value,
        source: d.extraction_source || "GLiNER2",
        extras: d.gliner2_extras,
      });
    }

    if (ev.type === "graph_updated") {
      const savings = d.details?.monthly_savings;
      steps.push({
        category: "graph",
        label: `Knowledge Graph: ${d.service || "Updated"}`,
        detail: savings ? `Saved $${savings}/mo ($${d.details.annual_savings}/yr)` : "Graph nodes updated",
        source: "Neo4j",
        highlight: !!savings,
      });
    }

    if (ev.type === "bill_analyzed") {
      steps.push({
        category: "detection",
        label: `Bill Scanned: ${d.provider_name || "Provider"}`,
        detail: `Total: $${d.total_amount || "?"}${d.price_change ? ` — ${d.price_change}` : ""}`,
        source: "Reka Vision",
      });
    }

    if (ev.type === "call_summary") {
      steps.push({
        category: "summary",
        label: "Agent Summary",
        detail: d.narrative,
        extras: d.key_points,
        source: "Haggle Agent",
        highlight: true,
      });
    }

    if (ev.type === "modulate_analysis") {
      const perf = d.agent_performance || {};
      if (perf.professionalism) {
        steps.push({
          category: "voice",
          label: `Performance: ${perf.professionalism.grade} Professionalism, ${perf.privacy?.grade || "?"} Privacy`,
          detail: perf.summary_note || "Agent performance evaluated",
          source: "Modulate",
        });
      }
    }

    if (ev.type === "pii_detected") {
      steps.push({
        category: "detection",
        label: `PII Protected: ${d.count} item${d.count !== 1 ? "s" : ""} auto-redacted`,
        detail: "Sensitive data detected and removed from transcript",
        source: "Modulate Safety",
      });
    }
  }

  return steps;
}

function EntityCard({ entity }) {
  const icons = {
    confirmation_number: "# ",
    price: "$ ",
    dollar_amount: "$ ",
    account_number: "@ ",
    person_name: "   ",
    phone_number: "   ",
    company_name: "   ",
    contract_term: "   ",
    promotional_rate: "   ",
    penalty_fee: "   ",
    date: "   ",
  };
  const icon = icons[entity.label] || "   ";
  return (
    <div className="inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg bg-emerald-500/8 border border-emerald-500/20">
      <span className="text-sm">{icon}</span>
      <div>
        <div className="text-[9px] text-gray-500 uppercase tracking-wider">{entity.label}</div>
        <div className="text-xs font-semibold text-emerald-400">{entity.detail}</div>
      </div>
    </div>
  );
}

export default function ResearchPanel({ events }) {
  const chain = useMemo(() => buildReasoningChain(events), [events]);
  const entities = useMemo(
    () => chain.filter((s) => s.category === "entity"),
    [chain]
  );

  return (
    <div className="h-full flex flex-col gap-2.5">
      {/* Top: Reasoning Chain */}
      <div className="flex-[3] min-h-0 card flex flex-col">
        <div className="flex items-center gap-2 mb-3">
          <div className="w-6 h-6 rounded-lg bg-gradient-to-br from-cyan-500/20 to-blue-500/20 border border-cyan-500/30 flex items-center justify-center">
            <svg className="w-3.5 h-3.5 text-cyan-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
            </svg>
          </div>
          <h2 className="text-xs font-semibold text-gray-400 uppercase tracking-widest">
            AI Reasoning Chain
          </h2>
          {chain.length > 0 && (
            <span className="text-[10px] text-gray-600 ml-auto tabular-nums">{chain.length} steps</span>
          )}
        </div>

        <div className="flex-1 overflow-y-auto pr-1 min-h-0">
          {chain.length > 0 ? (
            <div className="relative pl-6">
              {/* Timeline line */}
              <div className="absolute left-[9px] top-2 bottom-2 w-px bg-gradient-to-b from-blue-500/40 via-purple-500/30 to-green-500/40" />

              <div className="space-y-2">
                {chain.map((step, i) => {
                  const color = STEP_COLORS[step.category] || STEP_COLORS.research;
                  const isLast = i === chain.length - 1;
                  return (
                    <div key={i} className={`relative ${isLast ? "animate-slide-up" : ""}`}>
                      {/* Timeline dot */}
                      <div className={`absolute -left-6 top-2.5 w-[18px] h-[18px] rounded-full ${color.bg} border ${color.border} flex items-center justify-center z-10`}>
                        <div className={`w-2 h-2 rounded-full ${color.dot} ${isLast ? "animate-pulse" : ""}`} />
                      </div>

                      <div className={`rounded-xl p-3 ${step.highlight ? `${color.bg} border ${color.border}` : "bg-dark-700/40 border border-dark-600/50 hover:border-dark-500/50"} transition-colors`}>
                        <div className="flex items-center gap-2 mb-1">
                          <span className={color.text}>{STEP_ICONS[step.category]}</span>
                          <span className={`text-xs font-semibold ${step.highlight ? color.text : "text-gray-200"}`}>
                            {step.label}
                          </span>
                          <span className="text-[9px] text-gray-600 ml-auto font-mono">{step.source}</span>
                        </div>
                        <p className="text-[11px] text-gray-400 leading-relaxed">{step.detail}</p>
                        {step.extras && step.extras.length > 0 && (
                          <ul className="mt-1.5 space-y-0.5">
                            {step.extras.map((ex, j) => (
                              <li key={j} className="flex items-start gap-1.5 text-[10px] text-gray-500">
                                <span className={`${color.text} mt-px shrink-0`}>+</span>
                                <span>{ex}</span>
                              </li>
                            ))}
                          </ul>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center h-full text-center py-8">
              <div className="w-12 h-12 rounded-2xl bg-dark-700 flex items-center justify-center mb-3">
                <svg className="w-6 h-6 text-gray-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                </svg>
              </div>
              <p className="text-sm text-gray-500 font-medium">No reasoning data yet</p>
              <p className="text-xs text-gray-600 mt-1">Run a demo to see the AI's decision-making process</p>
            </div>
          )}
        </div>
      </div>

      {/* Bottom: Extracted Entities + Knowledge Graph side by side */}
      <div className="flex-[2] min-h-0 flex gap-2.5">
        {/* Entities */}
        <div className="flex-1 min-h-0 card flex flex-col">
          <h3 className="text-[10px] font-semibold text-gray-500 uppercase tracking-widest mb-2">
            Extracted Entities
          </h3>
          <div className="flex-1 overflow-y-auto min-h-0">
            {entities.length > 0 ? (
              <div className="flex flex-wrap gap-1.5">
                {entities.map((e, i) => (
                  <EntityCard key={i} entity={e} />
                ))}
              </div>
            ) : (
              <div className="text-xs text-gray-600 text-center py-4">
                Entities appear as the agent extracts them from calls
              </div>
            )}
          </div>
        </div>

        {/* Knowledge Graph */}
        <div className="flex-1 min-h-0">
          <KnowledgeGraph />
        </div>
      </div>
    </div>
  );
}
