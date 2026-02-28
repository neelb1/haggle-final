const API_BASE = import.meta.env.VITE_API_URL || "";

async function request(path, options = {}) {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json();
}

export const api = {
  getTasks: () => request("/api/tasks"),
  triggerTask: (id) => request(`/api/tasks/${id}/trigger`, { method: "POST" }),
  getGraph: () => request("/api/graph"),
  getMonitorStatus: () => request("/api/monitor/status"),
  runScan: () => request("/api/monitor/scan", { method: "POST" }),
  getDemoDetections: () => request("/api/monitor/demo"),
  getStats: () => request("/api/demo/stats"),
  runDemo: () => request("/api/demo/run", { method: "POST" }),
  resetDemo: () => request("/api/demo/reset", { method: "POST" }),
  runUserConsult: () => request("/api/demo/user-consult", { method: "POST" }),
  callUser: () => request("/api/user/call", { method: "POST" }),
  // Call history (Postgres)
  getCallHistory: () => request("/api/calls/history"),
  // Reka Vision bill analysis
  analyzeBill: (imageUrl) => request("/api/bills/analyze", { method: "POST", body: JSON.stringify({ image_url: imageUrl }) }),
  compareBills: (oldUrl, newUrl) => request("/api/bills/compare", { method: "POST", body: JSON.stringify({ old_image_url: oldUrl, new_image_url: newUrl }) }),
  // Yutori Scouts
  createScout: (provider, url) => request("/api/monitor/scout", { method: "POST", body: JSON.stringify({ provider, url }) }),
};

export function createSSE() {
  const url = `${API_BASE}/api/events`;
  return new EventSource(url);
}
