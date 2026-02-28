import { useState, useEffect } from "react";
import { api } from "../api";

const PHASES = ["pending", "researching", "calling", "completed"];
const PHASE_LABELS = { pending: "Queued", researching: "Research", calling: "On Call", completed: "Done" };

const ACTION_CONFIG = {
  negotiate_rate: { label: "Negotiate", color: "accent-blue" },
  cancel_service: { label: "Cancel", color: "accent-red" },
  update_status: { label: "Update", color: "accent-amber" },
};

export default function TaskQueue() {
  const [tasks, setTasks] = useState([]);
  const [loading, setLoading] = useState(true);

  const fetchTasks = async () => {
    try {
      setTasks(await api.getTasks());
    } catch {}
    finally { setLoading(false); }
  };

  useEffect(() => {
    fetchTasks();
    const interval = setInterval(fetchTasks, 3000);
    return () => clearInterval(interval);
  }, []);

  if (loading) {
    return (
      <div className="card h-full">
        <div className="h-4 bg-dark-700 rounded w-16 mb-4" />
        <div className="space-y-3">
          {[1, 2].map(i => (
            <div key={i} className="h-28 bg-dark-700 rounded-xl animate-pulse" />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="card h-full flex flex-col">
      <h2 className="text-xs font-semibold text-gray-500 uppercase tracking-widest mb-3">
        Tasks
      </h2>

      <div className="flex-1 overflow-y-auto space-y-3 pr-1 min-h-0">
        {tasks.map((task) => (
          <TaskCard key={task.id} task={task} />
        ))}
        {tasks.length === 0 && (
          <div className="text-center text-gray-600 py-8 text-sm">
            No tasks queued
          </div>
        )}
      </div>
    </div>
  );
}

function TaskCard({ task }) {
  const config = ACTION_CONFIG[task.action] || ACTION_CONFIG.update_status;
  const phaseIndex = PHASES.indexOf(task.status);
  const isActive = task.status === "researching" || task.status === "calling";
  const isDone = task.status === "completed";
  const isFailed = task.status === "failed";

  return (
    <div className={`rounded-xl border transition-all ${
      isActive
        ? "bg-dark-700/80 border-accent-purple/30 shadow-lg shadow-accent-purple/5"
        : isDone
        ? "bg-dark-700/40 border-accent-green/20"
        : isFailed
        ? "bg-dark-700/40 border-accent-red/20"
        : "bg-dark-700/50 border-dark-600 hover:border-dark-500"
    }`}>
      <div className="px-3.5 pt-3 pb-2">
        <div className="flex items-start justify-between gap-2">
          <div>
            <div className="flex items-center gap-2">
              <span className="text-sm font-semibold">{task.company}</span>
              <span className={`badge bg-${config.color}/10 text-${config.color}`}>
                {config.label}
              </span>
            </div>
            <p className="text-[11px] text-gray-500 mt-0.5">
              {task.service_type || "service"}
              {task.current_rate ? (
                <span>
                  {" "}&middot; ${task.current_rate}
                  {task.target_rate ? ` \u2192 $${task.target_rate}` : ""}/mo
                </span>
              ) : ""}
            </p>
          </div>

          {isDone && task.savings && (
            <div className="text-right">
              <div className="text-accent-green text-sm font-bold">
                -${task.savings}/mo
              </div>
              <div className="text-[10px] text-accent-green/60">
                ${(task.savings * 12).toFixed(0)}/yr
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Progress bar */}
      <div className="px-3.5 pb-2">
        <div className="flex items-center gap-1">
          {PHASES.map((phase, i) => {
            const isPast = i < phaseIndex || isDone;
            const isCurrent = phase === task.status && isActive;
            return (
              <div key={phase} className="flex-1 flex flex-col items-center">
                <div className={`h-1 w-full rounded-full transition-all duration-500 ${
                  isPast ? "bg-accent-green" :
                  isCurrent ? "bg-accent-purple animate-pulse" :
                  "bg-dark-600"
                }`} />
                <span className={`text-[8px] mt-1 transition-colors ${
                  isPast ? "text-accent-green" :
                  isCurrent ? "text-accent-purple font-semibold" :
                  "text-gray-600"
                }`}>
                  {PHASE_LABELS[phase]}
                </span>
              </div>
            );
          })}
        </div>
      </div>

      {isDone && task.outcome && (
        <div className="px-3.5 pb-3 pt-1 border-t border-dark-600/30">
          <p className="text-[11px] text-gray-400 leading-relaxed line-clamp-2">{task.outcome}</p>
          {task.confirmation_number && (
            <div className="mt-1.5 inline-flex items-center gap-1.5 px-2 py-0.5 rounded-md bg-accent-green/10 text-accent-green text-[10px] font-mono font-semibold">
              {task.confirmation_number}
            </div>
          )}
        </div>
      )}

      {isActive && (
        <div className="px-3.5 pb-3">
          <div className="flex items-center gap-2 text-[11px] text-accent-purple">
            <svg className="w-3.5 h-3.5 animate-spin" viewBox="0 0 24 24" fill="none">
              <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" strokeDasharray="31.4" strokeDashoffset="10" />
            </svg>
            {task.status === "researching" ? "Researching..." : "Agent negotiating..."}
          </div>
        </div>
      )}
    </div>
  );
}
