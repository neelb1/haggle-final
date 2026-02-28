import { useState, useEffect } from "react";

export default function Header({ connected }) {
  const [time, setTime] = useState(new Date());

  useEffect(() => {
    const interval = setInterval(() => setTime(new Date()), 1000);
    return () => clearInterval(interval);
  }, []);

  return (
    <header className="flex items-center justify-between px-5 py-2.5 border-b border-dark-600/50 bg-dark-800/60 backdrop-blur-md">
      <div className="flex items-center gap-2.5">
        <img src="/logo.png" alt="Haggle" className="w-8 h-8 rounded-lg object-cover" />
        <span className="text-sm font-semibold tracking-tight">Haggle</span>
        <span className="text-[10px] text-gray-600 font-medium">AUTONOMOUS FINANCIAL AGENT</span>
      </div>

      <div className="flex items-center gap-4 text-[11px]">
        <div className="flex items-center gap-1.5">
          {connected ? (
            <>
              <span className="pulse-dot" />
              <span className="text-accent-green font-medium">Live</span>
            </>
          ) : (
            <>
              <span className="w-2 h-2 rounded-full bg-gray-600" />
              <span className="text-gray-500">Connecting...</span>
            </>
          )}
        </div>
        <span className="text-gray-600 tabular-nums font-mono text-[10px]">
          {time.toLocaleTimeString()}
        </span>
      </div>
    </header>
  );
}
