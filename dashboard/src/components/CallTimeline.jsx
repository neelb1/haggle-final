import { useState, useEffect } from "react";
import { api } from "../api";

export default function CallTimeline() {
  const [calls, setCalls] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.getCallHistory()
      .then(setCalls)
      .catch(() => {})
      .finally(() => setLoading(false));
    const interval = setInterval(() => {
      api.getCallHistory().then(setCalls).catch(() => {});
    }, 5000);
    return () => clearInterval(interval);
  }, []);

  const totalSavings = calls.reduce((sum, c) => sum + (parseFloat(c.savings) || 0), 0);
  const successCount = calls.filter((c) => c.outcome === "success" || c.savings > 0).length;

  return (
    <div className="h-full flex flex-col gap-2.5">
      {/* Summary stats */}
      <div className="grid grid-cols-3 gap-2.5">
        <StatCard
          value={calls.length}
          label="Total Calls"
          color="text-blue-400"
          icon={
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M3 5a2 2 0 012-2h3.28a1 1 0 01.948.684l1.498 4.493a1 1 0 01-.502 1.21l-2.257 1.13a11.042 11.042 0 005.516 5.516l1.13-2.257a1 1 0 011.21-.502l4.493 1.498a1 1 0 01.684.949V19a2 2 0 01-2 2h-1C9.716 21 3 14.284 3 6V5z" />
            </svg>
          }
        />
        <StatCard
          value={successCount}
          label="Successful"
          color="text-emerald-400"
          icon={
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          }
        />
        <StatCard
          value={`$${totalSavings.toFixed(0)}`}
          label="Monthly Saved"
          color="text-green-400"
          icon={
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          }
        />
      </div>

      {/* Call list */}
      <div className="flex-1 min-h-0 card flex flex-col">
        <div className="flex items-center gap-2 mb-3">
          <h2 className="text-xs font-semibold text-gray-400 uppercase tracking-widest">
            Call History
          </h2>
          {calls.length > 0 && (
            <span className="text-[10px] text-gray-600 tabular-nums">{calls.length} calls</span>
          )}
        </div>

        <div className="flex-1 overflow-y-auto space-y-2 pr-1 min-h-0">
          {loading ? (
            <div className="space-y-2">
              {[1, 2, 3].map((i) => (
                <div key={i} className="h-20 bg-dark-700 rounded-xl animate-pulse" />
              ))}
            </div>
          ) : calls.length > 0 ? (
            calls.map((call, i) => <CallCard key={call.call_id || i} call={call} />)
          ) : (
            <div className="flex flex-col items-center justify-center h-full text-center py-8">
              <div className="w-12 h-12 rounded-2xl bg-dark-700 flex items-center justify-center mb-3">
                <svg className="w-6 h-6 text-gray-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>
              <p className="text-sm text-gray-500 font-medium">No call history yet</p>
              <p className="text-xs text-gray-600 mt-1">Completed calls appear here with outcomes and savings</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function StatCard({ value, label, color, icon }) {
  return (
    <div className="card flex items-center gap-3 py-3">
      <div className={`${color} opacity-60`}>{icon}</div>
      <div>
        <div className={`text-xl font-black tabular-nums ${color}`}>{value}</div>
        <div className="text-[9px] text-gray-500 uppercase tracking-wider">{label}</div>
      </div>
    </div>
  );
}

function CallCard({ call }) {
  const isSuccess = call.outcome === "success" || parseFloat(call.savings) > 0;
  const actionLabel = call.action === "cancel_service" ? "Cancel" : call.action === "negotiate_rate" ? "Negotiate" : call.action || "Call";
  const duration = call.duration_seconds ? `${call.duration_seconds}s` : "—";
  const savings = parseFloat(call.savings) || 0;
  const time = call.created_at ? new Date(call.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }) : "";

  return (
    <div className={`rounded-xl border p-3 transition-colors ${
      isSuccess
        ? "bg-emerald-500/5 border-emerald-500/20 hover:border-emerald-500/40"
        : "bg-dark-700/40 border-dark-600/50 hover:border-dark-500/50"
    }`}>
      <div className="flex items-start justify-between mb-1.5">
        <div className="flex items-center gap-2">
          <span className={`w-2 h-2 rounded-full ${isSuccess ? "bg-emerald-400" : "bg-gray-500"}`} />
          <span className="text-sm font-semibold text-gray-200">{call.company}</span>
          <span className={`text-[9px] font-semibold px-1.5 py-0.5 rounded-full uppercase tracking-wider ${
            call.action === "cancel_service"
              ? "bg-red-500/15 text-red-400"
              : "bg-blue-500/15 text-blue-400"
          }`}>
            {actionLabel}
          </span>
        </div>
        {savings > 0 && (
          <span className="text-emerald-400 text-sm font-bold">-${savings}/mo</span>
        )}
      </div>

      <div className="flex items-center gap-3 text-[10px] text-gray-500">
        {time && <span>{time}</span>}
        <span>Duration: {duration}</span>
        {call.outcome && (
          <span className={isSuccess ? "text-emerald-400 font-semibold" : "text-gray-400"}>
            {call.outcome}
          </span>
        )}
      </div>

      {call.confirmation_number && (
        <div className="mt-1.5 inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-emerald-500/10 text-emerald-400 text-[10px] font-mono font-semibold">
          #{call.confirmation_number}
        </div>
      )}
    </div>
  );
}
