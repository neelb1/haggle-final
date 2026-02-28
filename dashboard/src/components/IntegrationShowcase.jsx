import { useState, useEffect } from "react";
import { api } from "../api";

const INTEGRATIONS = [
  {
    key: "vapi",
    name: "Vapi",
    desc: "Voice AI Agent Platform",
    detail: "Powers autonomous phone calls with real-time transcription and tool execution",
    color: "from-blue-500 to-cyan-500",
    textColor: "text-blue-400",
    category: "Voice",
  },
  {
    key: "modulate",
    name: "Modulate",
    desc: "Voice Intelligence (Velma 2)",
    detail: "Real-time emotion detection, stress analysis, behavioral signals, and safety monitoring",
    color: "from-violet-500 to-purple-500",
    textColor: "text-violet-400",
    category: "Analysis",
  },
  {
    key: "neo4j",
    name: "Neo4j",
    desc: "Knowledge Graph",
    detail: "Stores subscription relationships, negotiation history, and user context",
    color: "from-emerald-500 to-green-500",
    textColor: "text-emerald-400",
    category: "Data",
  },
  {
    key: "tavily",
    name: "Tavily",
    desc: "Web Intelligence Search",
    detail: "Searches competitor rates, retention offers, and market data in real-time",
    color: "from-amber-500 to-orange-500",
    textColor: "text-amber-400",
    category: "Research",
  },
  {
    key: "reka",
    name: "Reka",
    desc: "Vision / Bill Analysis",
    detail: "Scans bills using multimodal vision to detect hidden fees and price changes",
    color: "from-cyan-500 to-teal-500",
    textColor: "text-cyan-400",
    category: "Analysis",
  },
  {
    key: "stripe",
    name: "Stripe (Airbyte)",
    desc: "Payment Anomaly Detection",
    detail: "Monitors recurring charges via Airbyte sync, detects billing anomalies",
    color: "from-purple-500 to-pink-500",
    textColor: "text-purple-400",
    category: "Monitor",
  },
  {
    key: "overshoot",
    name: "Overshoot",
    desc: "Broadcast Financial Alerts",
    detail: "Monitors financial news and broadcasts for rate increase announcements",
    color: "from-red-500 to-orange-500",
    textColor: "text-red-400",
    category: "Monitor",
  },
  {
    key: "yutori",
    name: "Yutori",
    desc: "Web Scout Monitoring",
    detail: "Deploys scouts to monitor provider websites for price changes and promotions",
    color: "from-teal-500 to-emerald-500",
    textColor: "text-teal-400",
    category: "Monitor",
  },
  {
    key: "senso",
    name: "Senso",
    desc: "Context OS / Compliance",
    detail: "Provides regulatory context and compliance documentation for negotiations",
    color: "from-blue-400 to-indigo-500",
    textColor: "text-blue-400",
    category: "Research",
  },
  {
    key: "slack",
    name: "Slack",
    desc: "Alert Notifications",
    detail: "Sends real-time alerts for detected threats and completed negotiations",
    color: "from-fuchsia-500 to-purple-600",
    textColor: "text-fuchsia-400",
    category: "Notify",
  },
];

const CATEGORY_COLORS = {
  Voice: "bg-blue-500/15 text-blue-400 border-blue-500/30",
  Analysis: "bg-violet-500/15 text-violet-400 border-violet-500/30",
  Data: "bg-emerald-500/15 text-emerald-400 border-emerald-500/30",
  Research: "bg-amber-500/15 text-amber-400 border-amber-500/30",
  Monitor: "bg-red-500/15 text-red-400 border-red-500/30",
  Notify: "bg-fuchsia-500/15 text-fuchsia-400 border-fuchsia-500/30",
};

export default function IntegrationShowcase() {
  const [status, setStatus] = useState(null);

  useEffect(() => {
    api.getMonitorStatus().then(setStatus).catch(() => {});
    const interval = setInterval(() => {
      api.getMonitorStatus().then(setStatus).catch(() => {});
    }, 10000);
    return () => clearInterval(interval);
  }, []);

  const activeCount = status ? Object.values(status).filter(Boolean).length : 0;

  return (
    <div className="card h-full flex flex-col overflow-hidden">
      <div className="flex items-center gap-2 mb-3">
        <div className="w-6 h-6 rounded-lg bg-gradient-to-br from-blue-500/20 to-purple-500/20 border border-blue-500/30 flex items-center justify-center">
          <svg className="w-3.5 h-3.5 text-blue-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M13 10V3L4 14h7v7l9-11h-7z" />
          </svg>
        </div>
        <h2 className="text-xs font-semibold text-gray-400 uppercase tracking-widest">
          Integrations
        </h2>
        <div className="ml-auto flex items-center gap-1.5">
          <span className="text-[10px] text-gray-500 tabular-nums">
            {status ? `${activeCount}/${INTEGRATIONS.length}` : "..."} active
          </span>
          {activeCount > 0 && <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />}
        </div>
      </div>

      <div className="flex-1 overflow-y-auto space-y-1.5 pr-1 min-h-0">
        {INTEGRATIONS.map((integ) => {
          const isActive = status ? status[integ.key] : null;
          return (
            <div
              key={integ.key}
              className="group flex items-start gap-3 px-3 py-2.5 rounded-xl bg-dark-700/30 border border-dark-600/40 hover:border-dark-500/60 transition-all"
            >
              {/* Status indicator */}
              <div className="mt-1 shrink-0">
                {isActive === true ? (
                  <span className="flex h-2.5 w-2.5">
                    <span className="absolute inline-flex h-2.5 w-2.5 rounded-full bg-emerald-400 opacity-50 animate-ping" />
                    <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-emerald-400" />
                  </span>
                ) : isActive === false ? (
                  <span className="inline-flex h-2.5 w-2.5 rounded-full bg-gray-600" />
                ) : (
                  <span className="inline-flex h-2.5 w-2.5 rounded-full bg-gray-700 animate-pulse" />
                )}
              </div>

              {/* Info */}
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-semibold text-gray-200">{integ.name}</span>
                  <span className={`text-[8px] font-bold px-1.5 py-0.5 rounded-full border uppercase tracking-wider ${CATEGORY_COLORS[integ.category]}`}>
                    {integ.category}
                  </span>
                </div>
                <p className="text-[11px] text-gray-400 mt-0.5">{integ.desc}</p>
                <p className="text-[10px] text-gray-600 mt-0.5 leading-relaxed group-hover:text-gray-500 transition-colors">
                  {integ.detail}
                </p>
              </div>
            </div>
          );
        })}
      </div>

      {/* Data flow summary */}
      <div className="mt-3 pt-3 border-t border-dark-600/50">
        <div className="flex items-center justify-between text-[10px] text-gray-600">
          <span>SSE real-time stream</span>
          <span>Postgres durable storage</span>
          <span>Neo4j graph memory</span>
        </div>
      </div>
    </div>
  );
}
