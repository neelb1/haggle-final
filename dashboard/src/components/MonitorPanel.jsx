import { useState, useEffect } from "react";
import { api } from "../api";

const SOURCE_BADGES = {
  airbyte_stripe: { color: "bg-accent-purple/20 text-accent-purple", label: "Stripe" },
  overshoot_vision: { color: "bg-accent-blue/20 text-accent-blue", label: "Overshoot" },
  tavily_search: { color: "bg-accent-amber/20 text-accent-amber", label: "Tavily" },
  demo: { color: "bg-gray-600/40 text-gray-300", label: "Monitor" },
};

export default function MonitorPanel() {
  const [detections, setDetections] = useState([]);
  const [status, setStatus] = useState(null);
  const [scanning, setScanning] = useState(false);
  const [calling, setCalling] = useState(false);

  useEffect(() => {
    api.getMonitorStatus().then(setStatus).catch(() => {});
    api.getDemoDetections().then((d) => setDetections(d.detections || [])).catch(() => {});
  }, []);

  const handleScan = async () => {
    setScanning(true);
    try {
      const result = await api.runScan();
      if (result.detections?.length) {
        setDetections((prev) => [...result.detections, ...prev]);
      }
    } catch (e) {
      console.error("Scan failed:", e);
    } finally {
      setScanning(false);
    }
  };

  const handleCallMe = async () => {
    setCalling(true);
    try {
      await api.runUserConsult();
    } catch (e) {
      console.error("User consult failed:", e);
    } finally {
      setTimeout(() => setCalling(false), 3000);
    }
  };

  return (
    <div className="card flex flex-col h-full">
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wider">
          Threat Monitor
        </h2>
        <div className="flex items-center gap-2">
          {status && (
            <div className="flex items-center gap-1 mr-2">
              {Object.entries(status).map(([key, val]) => (
                <span
                  key={key}
                  title={`${key}: ${val ? "active" : "inactive"}`}
                  className={`w-1.5 h-1.5 rounded-full ${
                    val ? "bg-accent-green" : "bg-gray-600"
                  }`}
                />
              ))}
            </div>
          )}
          <button
            onClick={handleCallMe}
            disabled={calling}
            className="text-xs px-3 py-1 rounded-lg border border-dark-600 hover:border-accent-green/50 text-gray-400 hover:text-accent-green transition-colors disabled:opacity-40 flex items-center gap-1.5"
          >
            <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M3 5a2 2 0 012-2h3.28a1 1 0 01.948.684l1.498 4.493a1 1 0 01-.502 1.21l-2.257 1.13a11.042 11.042 0 005.516 5.516l1.13-2.257a1 1 0 011.21-.502l4.493 1.498a1 1 0 01.684.949V19a2 2 0 01-2 2h-1C9.716 21 3 14.284 3 6V5z" />
            </svg>
            {calling ? "Calling..." : "Call Me"}
          </button>
          <button
            onClick={handleScan}
            disabled={scanning}
            className="text-xs px-3 py-1 rounded-lg border border-dark-600 hover:border-accent-red/50 text-gray-400 hover:text-accent-red transition-colors disabled:opacity-40"
          >
            {scanning ? "Scanning..." : "Scan"}
          </button>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto space-y-2 pr-1">
        {detections.map((d, i) => {
          const badge = SOURCE_BADGES[d.source] || SOURCE_BADGES.demo;
          const isIncrease = d.type === "BILLING_INCREASE" || d.type === "RATE_INCREASE";
          return (
            <div
              key={i}
              className={`bg-dark-700 rounded-lg p-3 border transition-colors animate-slide-up ${
                isIncrease
                  ? "border-accent-red/20 hover:border-accent-red/40"
                  : "border-dark-600 hover:border-dark-500"
              }`}
            >
              <div className="flex items-center gap-2 mb-1.5">
                <span className={`badge ${badge.color}`}>{badge.label}</span>
                <span className="text-[10px] text-gray-500 uppercase">{d.type?.replace(/_/g, " ")}</span>
              </div>

              {(d.company || d.merchant) && (
                <p className="text-sm font-medium">
                  {d.company || d.merchant}
                  {d.old_amount != null && d.new_amount != null && (
                    <span className="text-accent-red ml-2 text-xs">
                      ${d.old_amount} &rarr; ${d.new_amount}
                      {d.increase_pct && (
                        <span className="text-accent-red/60 ml-1">
                          (+{d.increase_pct}%)
                        </span>
                      )}
                    </span>
                  )}
                </p>
              )}

              {d.summary && (
                <p className="text-xs text-gray-400 mt-1 leading-relaxed line-clamp-2">
                  {d.summary}
                </p>
              )}

              {d.relevance && (
                <p className="text-[10px] text-accent-amber/80 mt-1">
                  {d.relevance}
                </p>
              )}
            </div>
          );
        })}

        {detections.length === 0 && (
          <div className="text-center text-gray-600 py-6 text-sm">
            No threats detected
          </div>
        )}
      </div>
    </div>
  );
}
