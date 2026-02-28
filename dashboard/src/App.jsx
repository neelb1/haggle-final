import { useState, useEffect, useCallback } from "react";
import Header from "./components/Header";
import StatsRibbon from "./components/StatsRibbon";
import TaskQueue from "./components/TaskQueue";
import LiveCall from "./components/LiveCall";
import KnowledgeGraph from "./components/KnowledgeGraph";
import MonitorPanel from "./components/MonitorPanel";
import ResearchPanel from "./components/ResearchPanel";
import AgentIntelPanel from "./components/AgentIntelPanel";
import CallTimeline from "./components/CallTimeline";
import IntegrationShowcase from "./components/IntegrationShowcase";
import Toast from "./components/Toast";
import { useSSE } from "./hooks/useSSE";
import { api, setDemoSecret, getDemoSecret } from "./api";

function TabBar({ tabs, active, onChange }) {
  return (
    <div className="flex items-center gap-0.5 mb-2 bg-dark-800/60 rounded-xl p-0.5 border border-dark-600/40">
      {tabs.map((tab, i) => (
        <button
          key={tab.key}
          onClick={() => onChange(i)}
          className={`flex-1 text-[10px] font-semibold px-2 py-1.5 rounded-lg uppercase tracking-wider transition-all ${
            active === i
              ? "bg-dark-600/80 text-gray-200 shadow-sm"
              : "text-gray-500 hover:text-gray-400 hover:bg-dark-700/30"
          }`}
        >
          <span className="flex items-center justify-center gap-1.5">
            {tab.label}
            {tab.badge && (
              <span className={`w-1.5 h-1.5 rounded-full ${tab.badge}`} />
            )}
          </span>
        </button>
      ))}
    </div>
  );
}

const CENTER_TABS = [
  { key: "live", label: "Live Feed", badge: null },
  { key: "reasoning", label: "AI Reasoning", badge: null },
  { key: "history", label: "History", badge: null },
];

const RIGHT_TABS = [
  { key: "monitor", label: "Monitor", badge: null },
  { key: "intel", label: "Agent Intel", badge: null },
  { key: "integrations", label: "Stack", badge: null },
];

export default function App() {
  const { events, connected } = useSSE();
  const [stats, setStats] = useState(null);
  const [demoRunning, setDemoRunning] = useState(false);
  const [toast, setToast] = useState(null);
  const [scanningBill, setScanningBill] = useState(false);
  const [centerTab, setCenterTab] = useState(0);
  const [rightTab, setRightTab] = useState(0);
  const [unlocked, setUnlocked] = useState(!!getDemoSecret());

  const handleUnlock = () => {
    const pin = prompt("Enter demo pin:");
    if (pin) {
      setDemoSecret(pin);
      setUnlocked(true);
      setToast({ type: "success", message: "Demo unlocked" });
    }
  };

  const refreshStats = useCallback(async () => {
    try {
      setStats(await api.getStats());
    } catch {}
  }, []);

  useEffect(() => {
    refreshStats();
    const interval = setInterval(refreshStats, 3000);
    return () => clearInterval(interval);
  }, [refreshStats]);

  // Auto-switch tabs on relevant events + show toasts
  useEffect(() => {
    if (events.length === 0) return;
    const latest = events[events.length - 1];

    // Auto-switch center to Live Feed on call events
    if (latest.type === "transcript" || (latest.type === "call_status" && latest.data?.status === "in_progress")) {
      setCenterTab(0);
    }

    // Auto-switch right to Agent Intel when voice analysis arrives
    if (latest.type === "voice_analysis" || latest.type === "modulate_analysis") {
      setRightTab(1);
    }

    // Phone number ready — show toast with number to call
    if (latest.type === "call_status" && latest.data?.status === "awaiting_call") {
      const phone = latest.data.agent_phone_display || "(208) 675-1229";
      const company = latest.data.company || "the company";
      setToast({
        type: "info",
        message: `Call ${phone} now!`,
        detail: `You play ${company} — the agent negotiates`,
      });
      setDemoRunning(false);
    }

    // Toast for completions
    if (latest.type === "call_status" && latest.data?.status === "ended" && latest.data?.outcome === "success") {
      setToast({ type: "success", message: `Call completed successfully` });
      setDemoRunning(false);
    }
    if (latest.type === "graph_updated" && latest.data?.details?.monthly_savings) {
      const s = latest.data.details;
      setToast({
        type: "savings",
        message: `Saved $${s.monthly_savings}/mo ($${s.annual_savings}/yr)`,
        detail: `${latest.data.service} — ${s.confirmation || "confirmed"}`,
      });
    }
  }, [events.length]);

  // Add live badges to tabs
  const centerTabsWithBadges = CENTER_TABS.map((tab) => {
    if (tab.key === "live" && events.some((e) => e.type === "transcript")) {
      return { ...tab, badge: "bg-accent-green animate-pulse" };
    }
    if (tab.key === "reasoning" && events.some((e) => e.type === "tool_call" || e.type === "entity_extracted")) {
      return { ...tab, badge: "bg-cyan-400" };
    }
    if (tab.key === "history" && events.some((e) => e.type === "call_status" && e.data?.status === "ended")) {
      return { ...tab, badge: "bg-emerald-400" };
    }
    return tab;
  });

  const rightTabsWithBadges = RIGHT_TABS.map((tab) => {
    if (tab.key === "intel" && events.some((e) => e.type === "voice_analysis")) {
      return { ...tab, badge: "bg-violet-400 animate-pulse" };
    }
    if (tab.key === "monitor" && events.some((e) => e.type === "detection")) {
      return { ...tab, badge: "bg-red-400" };
    }
    return tab;
  });

  const handleRunDemo = async () => {
    setDemoRunning(true);
    try {
      // Starts background: mock user consult → research → SSE pushes phone number
      await api.runDemo();
      setToast({
        type: "info",
        message: "Demo started — user consult playing...",
        detail: "Watch the live feed. Phone number appears after research.",
      });
    } catch (e) {
      console.error("Demo failed:", e);
      setToast({ type: "error", message: "Demo failed — " + (e.message || "try reset") });
      setDemoRunning(false);
    }
  };

  const handleScanBill = async () => {
    setScanningBill(true);
    try {
      const billUrl = (import.meta.env.VITE_API_URL || window.location.origin) + "/demo-bill.png";
      const result = await api.analyzeBill(billUrl);
      setToast({
        type: "success",
        message: `Bill scanned: ${result.provider_name || "Provider"} — $${result.total_amount || "?"}`,
        detail: result.price_change ? `Price change: ${result.price_change}` : "Analysis complete",
      });
      refreshStats();
    } catch (e) {
      console.error("Bill scan failed:", e);
      setToast({ type: "error", message: "Bill scan failed — " + (e.message || "check Reka API") });
    } finally {
      setScanningBill(false);
    }
  };

  const handleResetDemo = async () => {
    try {
      await api.resetDemo();
      await refreshStats();
      setToast({ type: "info", message: "Demo reset — tasks restored" });
    } catch (e) {
      console.error("Reset failed:", e);
    }
  };

  return (
    <div className="h-screen flex flex-col overflow-hidden bg-dark-900">
      <Header connected={connected} />
      <StatsRibbon
        stats={stats}
        onRunDemo={handleRunDemo}
        onResetDemo={handleResetDemo}
        onScanBill={handleScanBill}
        onUnlock={handleUnlock}
        demoRunning={demoRunning}
        scanningBill={scanningBill}
        unlocked={unlocked}
      />

      <main className="flex-1 grid grid-cols-12 gap-2.5 p-2.5 min-h-0">
        {/* Left: Task Queue */}
        <div className="col-span-3 min-h-0">
          <TaskQueue />
        </div>

        {/* Center: Tabbed — Live Feed / AI Reasoning / History */}
        <div className="col-span-5 flex flex-col min-h-0">
          <TabBar tabs={centerTabsWithBadges} active={centerTab} onChange={setCenterTab} />
          <div className="flex-1 min-h-0">
            {centerTab === 0 && (
              <div className="h-full flex flex-col gap-2.5">
                <div className="flex-[3] min-h-0">
                  <LiveCall events={events} />
                </div>
                <div className="flex-[2] min-h-0">
                  <KnowledgeGraph />
                </div>
              </div>
            )}
            {centerTab === 1 && <ResearchPanel events={events} />}
            {centerTab === 2 && <CallTimeline />}
          </div>
        </div>

        {/* Right: Tabbed — Monitor / Agent Intel / Integrations */}
        <div className="col-span-4 flex flex-col min-h-0">
          <TabBar tabs={rightTabsWithBadges} active={rightTab} onChange={setRightTab} />
          <div className="flex-1 min-h-0">
            {rightTab === 0 && <MonitorPanel />}
            {rightTab === 1 && <AgentIntelPanel events={events} />}
            {rightTab === 2 && <IntegrationShowcase />}
          </div>
        </div>
      </main>

      {/* Toast notifications */}
      {toast && <Toast {...toast} onDismiss={() => setToast(null)} />}
    </div>
  );
}
