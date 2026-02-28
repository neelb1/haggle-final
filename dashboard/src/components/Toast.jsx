import { useEffect } from "react";

const TOAST_STYLES = {
  success: "border-accent-green/30 bg-accent-green/10",
  savings: "border-accent-green/30 bg-accent-green/10",
  error: "border-accent-red/30 bg-accent-red/10",
  info: "border-accent-blue/30 bg-accent-blue/10",
};

const TOAST_ICONS = {
  success: (
    <svg className="w-5 h-5 text-accent-green" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
    </svg>
  ),
  savings: (
    <svg className="w-5 h-5 text-accent-green" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
    </svg>
  ),
  error: (
    <svg className="w-5 h-5 text-accent-red" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
    </svg>
  ),
  info: (
    <svg className="w-5 h-5 text-accent-blue" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
    </svg>
  ),
};

export default function Toast({ type = "info", message, detail, onDismiss }) {
  useEffect(() => {
    const timer = setTimeout(onDismiss, 5000);
    return () => clearTimeout(timer);
  }, [onDismiss]);

  return (
    <div className="fixed bottom-6 right-6 z-50 animate-slide-up">
      <div
        className={`flex items-start gap-3 px-4 py-3 rounded-xl border backdrop-blur-md shadow-2xl max-w-sm ${
          TOAST_STYLES[type]
        }`}
      >
        <div className="flex-shrink-0 mt-0.5">{TOAST_ICONS[type]}</div>
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-gray-100">{message}</p>
          {detail && <p className="text-xs text-gray-400 mt-0.5">{detail}</p>}
        </div>
        <button
          onClick={onDismiss}
          className="text-gray-500 hover:text-gray-300 transition-colors flex-shrink-0"
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>
    </div>
  );
}
