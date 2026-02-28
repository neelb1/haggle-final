import { useEffect, useState } from "react";
import { api } from "../api";

const NODE_STYLES = {
  Person: { bg: "bg-blue-500/20", border: "border-blue-500/40", text: "text-blue-400", icon: "👤", glow: "shadow-blue-500/20" },
  Service: { bg: "bg-purple-500/20", border: "border-purple-500/40", text: "text-purple-400", icon: "⚙️", glow: "shadow-purple-500/20" },
  Negotiation: { bg: "bg-emerald-500/20", border: "border-emerald-500/40", text: "text-emerald-400", icon: "🤝", glow: "shadow-emerald-500/20" },
};

const EDGE_LABELS = {
  SUBSCRIBES_TO: "subscribes to",
  NEGOTIATED: "negotiated",
};

function NodeCard({ node, x, y, active }) {
  const style = NODE_STYLES[node.label] || NODE_STYLES.Service;
  const props = node.properties || {};
  const rate = props.monthlyRate;
  const prevRate = props.previousRate;
  const status = props.status;
  const savings = props.savings;

  return (
    <foreignObject x={x - 70} y={y - 38} width={140} height={76}>
      <div className={`
        h-full rounded-xl border ${style.border} ${style.bg}
        flex flex-col items-center justify-center gap-0.5 px-2
        transition-all duration-500
        ${active ? `shadow-lg ${style.glow}` : ""}
      `}>
        <span className="text-base">{style.icon}</span>
        <span className={`text-xs font-bold ${style.text} leading-tight`}>{node.name}</span>
        {rate && (
          <span className="text-[10px] text-gray-400 tabular-nums">
            {prevRate && prevRate !== rate ? (
              <>
                <span className="line-through text-gray-600">${prevRate}/mo</span>
                {" → "}
                <span className="text-emerald-400 font-semibold">${rate}/mo</span>
              </>
            ) : (
              `$${rate}/mo`
            )}
          </span>
        )}
        {savings && (
          <span className="text-[9px] text-emerald-400 font-semibold">
            Saved ${savings}/mo
          </span>
        )}
        {node.label === "Person" && (
          <span className="text-[9px] text-gray-500">Account holder</span>
        )}
      </div>
    </foreignObject>
  );
}

function EdgeLine({ x1, y1, x2, y2, label, status }) {
  const mx = (x1 + x2) / 2;
  const my = (y1 + y2) / 2;
  const isCancelled = status === "cancelled";
  const strokeColor = isCancelled ? "#ef4444" : "#6b7280";
  const dashArray = isCancelled ? "6 4" : "none";

  return (
    <g>
      <line
        x1={x1} y1={y1} x2={x2} y2={y2}
        stroke={strokeColor} strokeWidth={1.5}
        strokeDasharray={dashArray} opacity={0.4}
      />
      {label && (
        <>
          <rect
            x={mx - 40} y={my - 8} width={80} height={16} rx={8}
            fill="rgba(15,15,20,0.8)" stroke={strokeColor} strokeWidth={0.5} opacity={0.6}
          />
          <text x={mx} y={my + 3.5} textAnchor="middle" fill="#9ca3af" fontSize={9} fontWeight={500}>
            {isCancelled ? "cancelled" : label}
          </text>
        </>
      )}
      {status === "cancelled" && (
        <text x={mx} y={my + 16} textAnchor="middle" fill="#ef4444" fontSize={8} fontWeight={600}>
          ✕ Cancelled
        </text>
      )}
    </g>
  );
}

export default function KnowledgeGraph() {
  const [graphData, setGraphData] = useState({ nodes: [], links: [] });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.getGraph().then(setGraphData).catch(() => {}).finally(() => setLoading(false));
    const interval = setInterval(() => {
      api.getGraph().then(setGraphData).catch(() => {});
    }, 6000);
    return () => clearInterval(interval);
  }, []);

  // Layout: Person center, services to left/right, negotiations below services
  const layout = computeLayout(graphData);
  const nodeCount = graphData.nodes.length;

  return (
    <div className="card h-full flex flex-col">
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2.5">
          <h2 className="text-xs font-semibold text-gray-500 uppercase tracking-widest">
            Knowledge Graph
          </h2>
          {nodeCount > 0 && (
            <span className="text-[10px] text-gray-600 tabular-nums">
              {nodeCount} nodes &middot; {graphData.links.length} edges
            </span>
          )}
        </div>
        <div className="flex items-center gap-3 text-[10px] text-gray-600">
          {["Person", "Service", "Negotiation"].map((label) => (
            <span key={label} className="flex items-center gap-1">
              <span>{NODE_STYLES[label].icon}</span>
              {label}
            </span>
          ))}
        </div>
      </div>

      <div className="flex-1 rounded-xl overflow-hidden bg-dark-900/60 min-h-0 flex items-center justify-center">
        {nodeCount > 0 ? (
          <svg viewBox="0 0 500 280" className="w-full h-full max-h-[280px]" preserveAspectRatio="xMidYMid meet">
            {/* Edges first (behind nodes) */}
            {layout.edges.map((edge, i) => (
              <EdgeLine key={i} {...edge} />
            ))}
            {/* Nodes */}
            {layout.positioned.map((item) => (
              <NodeCard key={item.node.id} node={item.node} x={item.x} y={item.y} active={item.active} />
            ))}
          </svg>
        ) : (
          <div className="flex flex-col items-center gap-2 text-gray-600 text-xs py-8">
            {loading ? (
              <>
                <svg className="w-5 h-5 animate-spin text-gray-600" viewBox="0 0 24 24" fill="none">
                  <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" strokeDasharray="31.4" strokeDashoffset="10" />
                </svg>
                Loading graph...
              </>
            ) : (
              <>
                <svg className="w-8 h-8 text-gray-700" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1}>
                  <circle cx="6" cy="6" r="2.5" /><circle cx="18" cy="18" r="2.5" /><circle cx="18" cy="6" r="2.5" />
                  <path d="M8 7l8-1M7 8l9 8" strokeDasharray="3 2" />
                </svg>
                <span>Run the demo to populate the graph</span>
              </>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

function computeLayout(graphData) {
  const { nodes, links } = graphData;
  if (nodes.length === 0) return { positioned: [], edges: [] };

  // Find person node (center)
  const person = nodes.find((n) => n.label === "Person");
  const services = nodes.filter((n) => n.label === "Service");
  const negotiations = nodes.filter((n) => n.label === "Negotiation");

  const positions = {};
  const CX = 250, CY = 80;

  // Person at top center
  if (person) positions[person.id] = { x: CX, y: CY };

  // Services spread horizontally below person
  const serviceY = 180;
  const serviceSpacing = 180;
  const serviceStartX = CX - ((services.length - 1) * serviceSpacing) / 2;
  services.forEach((s, i) => {
    positions[s.id] = { x: serviceStartX + i * serviceSpacing, y: serviceY };
  });

  // Negotiations below their linked service
  negotiations.forEach((neg, i) => {
    // Find which service this negotiation is linked to
    const link = links.find(
      (l) => (sourceId(l) === neg.id || targetId(l) === neg.id) &&
             (services.some((s) => s.id === sourceId(l) || s.id === targetId(l)))
    );
    if (link) {
      const serviceId = sourceId(link) === neg.id ? targetId(link) : sourceId(link);
      const sp = positions[serviceId];
      if (sp) {
        positions[neg.id] = { x: sp.x + 20 * (i + 1), y: sp.y + 60 };
      }
    }
    if (!positions[neg.id]) {
      positions[neg.id] = { x: CX + 60 * i, y: 240 };
    }
  });

  // Build positioned array
  const positioned = nodes
    .filter((n) => positions[n.id])
    .map((n) => ({
      node: n,
      x: positions[n.id].x,
      y: positions[n.id].y,
      active: n.label === "Negotiation" || (n.properties?.previousRate && n.properties.previousRate !== n.properties.monthlyRate),
    }));

  // Build edges
  const edges = links
    .filter((l) => positions[sourceId(l)] && positions[targetId(l)])
    .map((l) => {
      const s = positions[sourceId(l)];
      const t = positions[targetId(l)];
      return {
        x1: s.x, y1: s.y,
        x2: t.x, y2: t.y,
        label: EDGE_LABELS[l.type] || l.type?.replace(/_/g, " "),
        status: l.properties?.status,
      };
    });

  return { positioned, edges };
}

// force-graph passes objects, API returns strings
function sourceId(link) {
  return typeof link.source === "object" ? link.source.id : link.source;
}
function targetId(link) {
  return typeof link.target === "object" ? link.target.id : link.target;
}
