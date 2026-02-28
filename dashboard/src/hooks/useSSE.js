import { useEffect, useRef, useState } from "react";
import { createSSE } from "../api";

const EVENT_TYPES = [
  "task_updated",
  "call_started",
  "call_ended",
  "call_status",
  "call_summary",
  "transcript",
  "tool_call",
  "entity_extracted",
  "graph_updated",
  "emotion",
  "detection",
  "call_summary",
  "voice_analysis",
  "modulate_analysis",
  "pii_detected",
  "bill_analyzed",
];

export function useSSE() {
  const [events, setEvents] = useState([]);
  const [connected, setConnected] = useState(false);
  const [callStatus, setCallStatus] = useState(null);
  const esRef = useRef(null);

  useEffect(() => {
    const es = createSSE();
    esRef.current = es;

    es.onopen = () => setConnected(true);
    es.onerror = () => setConnected(false);

    const handler = (e) => {
      try {
        const data = JSON.parse(e.data);

        // On demo reset, wipe the feed so old runs don't repeat
        if (data.type === "task_updated" && data.data?.reset === true) {
          setEvents([]);
          return;
        }

        setEvents((prev) => [...prev, data].slice(-150));

        if (data.type === "call_status" || data.type === "transcript") {
          setCallStatus(data);
        }
      } catch {}
    };

    for (const type of EVENT_TYPES) {
      es.addEventListener(type, handler);
    }

    return () => {
      es.close();
      esRef.current = null;
    };
  }, []);

  return { events, connected, callStatus };
}
