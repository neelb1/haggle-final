import { useEffect, useRef, useState } from "react";

function AnimatedNumber({ value, prefix = "", suffix = "", className = "" }) {
  const [display, setDisplay] = useState(0);
  const prev = useRef(0);

  useEffect(() => {
    const start = prev.current;
    const end = value;
    if (start === end) return;
    const duration = 600;
    const startTime = performance.now();

    function tick(now) {
      const elapsed = now - startTime;
      const progress = Math.min(elapsed / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3);
      setDisplay(Math.round(start + (end - start) * eased));
      if (progress < 1) requestAnimationFrame(tick);
      else prev.current = end;
    }
    requestAnimationFrame(tick);
  }, [value]);

  return (
    <span className={className}>
      {prefix}{display.toLocaleString()}{suffix}
    </span>
  );
}

export default function StatsRibbon({ stats, onRunDemo, onResetDemo, onScanBill, demoRunning, scanningBill }) {
  const s = stats || {};
  const hasSavings = (s.total_annual_savings || 0) > 0;

  return (
    <div className="px-4 py-3 bg-dark-800/40 border-b border-dark-600/30">
      <div className="flex items-center gap-6">
        {/* Big savings number */}
        <div className="flex items-baseline gap-1">
          <AnimatedNumber
            value={s.total_annual_savings || 0}
            prefix="$"
            suffix=""
            className={`text-3xl font-black tabular-nums tracking-tight ${
              hasSavings ? "text-accent-green" : "text-gray-600"
            }`}
          />
          <span className="text-xs text-gray-500 font-medium">/yr saved</span>
        </div>

        {/* Secondary stats */}
        <div className="flex items-center gap-4 text-xs border-l border-dark-600/50 pl-5">
          <MiniStat
            value={`$${s.total_monthly_savings || 0}`}
            label="monthly"
            active={hasSavings}
          />
          <MiniStat
            value={`${s.tasks_completed || 0}/${s.tasks_total || 0}`}
            label="tasks done"
            active={(s.tasks_completed || 0) > 0}
          />
          <MiniStat
            value={s.calls_made || 0}
            label="calls"
            active={(s.calls_made || 0) > 0}
          />
          <MiniStat
            value={s.graph_nodes || 0}
            label="nodes"
            active={(s.graph_nodes || 0) > 3}
          />
        </div>

        {/* Spacer */}
        <div className="flex-1" />

        {/* Demo controls */}
        <div className="flex items-center gap-2">
          <button
            onClick={onScanBill}
            disabled={scanningBill}
            className={`text-sm font-semibold px-4 py-2 rounded-xl transition-all ${
              scanningBill
                ? "bg-amber-500/20 text-amber-400 border border-amber-500/30"
                : "bg-gradient-to-r from-amber-500 to-orange-500 text-white hover:shadow-lg hover:shadow-amber-500/20 hover:-translate-y-0.5"
            } disabled:cursor-not-allowed`}
          >
            {scanningBill ? (
              <span className="flex items-center gap-1.5">
                <svg className="w-3.5 h-3.5 animate-spin" viewBox="0 0 24 24" fill="none">
                  <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" strokeDasharray="31.4" strokeDashoffset="10" />
                </svg>
                Scanning...
              </span>
            ) : (
              "Scan Bill"
            )}
          </button>
          <button
            onClick={onResetDemo}
            disabled={demoRunning}
            className="text-[11px] text-gray-500 hover:text-gray-300 px-3 py-1.5 rounded-lg hover:bg-dark-700 transition-all disabled:opacity-30"
          >
            Reset
          </button>
          <button
            onClick={onRunDemo}
            disabled={demoRunning}
            className={`relative text-sm font-semibold px-6 py-2 rounded-xl transition-all overflow-hidden ${
              demoRunning
                ? "bg-accent-purple/20 text-accent-purple border border-accent-purple/30"
                : "bg-gradient-to-r from-accent-blue to-accent-purple text-white hover:shadow-xl hover:shadow-accent-purple/30 hover:-translate-y-0.5"
            } disabled:cursor-not-allowed`}
          >
            {demoRunning && <span className="absolute inset-0 shimmer" />}
            <span className="relative">
              {demoRunning ? (
                <span className="flex items-center gap-2">
                  <svg className="w-4 h-4 animate-spin" viewBox="0 0 24 24" fill="none">
                    <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" strokeDasharray="31.4" strokeDashoffset="10" />
                  </svg>
                  Agent Working...
                </span>
              ) : (
                "Run Demo"
              )}
            </span>
          </button>
        </div>
      </div>
    </div>
  );
}

function MiniStat({ value, label, active }) {
  return (
    <div className="flex items-baseline gap-1">
      <span className={`font-bold tabular-nums ${active ? "text-gray-200" : "text-gray-600"}`}>
        {value}
      </span>
      <span className="text-gray-600">{label}</span>
    </div>
  );
}
