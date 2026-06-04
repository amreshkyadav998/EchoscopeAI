"use client";

import { useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { useWebSocket } from "./useWebSocket";
import { useAuth } from "@/store/auth";

const WS_BASE = process.env.NEXT_PUBLIC_WS_BASE || "ws://localhost:8005";

/** Connects to /ws/dashboard and refetches analytics on metrics_update events. */
export function useDashboardSocket() {
  const token = useAuth((s) => s.accessToken) || "";
  const qc = useQueryClient();
  const [connected, setConnected] = useState(false);

  useWebSocket({
    url: `${WS_BASE}/ws/dashboard`,
    token,
    onStatusChange: (s) => setConnected(s === "open"),
    onMessage: (msg) => {
      if (msg.type === "metrics_update") {
        qc.invalidateQueries({ queryKey: ["overview"] });
        qc.invalidateQueries({ queryKey: ["sentiment"] });
      }
    },
  });

  return { connected };
}
