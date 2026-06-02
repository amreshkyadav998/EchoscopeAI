/**
 * useWebSocket — resilient WebSocket hook (HLD §10, Phase 9).
 *
 * - JWT passed via the `token` query param (matches the notification-service handshake).
 * - Auto-reconnect with exponential backoff (1s→2s→4s→8s→…→30s max) plus ±20% jitter.
 * - Ping/pong keepalive every 30s.
 * - Calls `onMessage` with each parsed payload (e.g. dispatch into a Zustand store).
 *
 * The full frontend app is built in Phase 13; this hook is the Phase 9 deliverable.
 */
import { useEffect, useRef, useCallback } from "react";

export type WsMessage = { type: string; payload?: unknown };

interface Options {
  url: string; // e.g. ws://localhost:8005/ws/dashboard
  token: string;
  onMessage: (msg: WsMessage) => void;
  onStatusChange?: (status: "connecting" | "open" | "closed") => void;
  pingIntervalMs?: number;
  maxBackoffMs?: number;
}

export function useWebSocket({
  url,
  token,
  onMessage,
  onStatusChange,
  pingIntervalMs = 30_000,
  maxBackoffMs = 30_000,
}: Options) {
  const wsRef = useRef<WebSocket | null>(null);
  const attemptRef = useRef(0);
  const pingRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const reconnectRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const closedRef = useRef(false);

  const clearTimers = () => {
    if (pingRef.current) clearInterval(pingRef.current);
    if (reconnectRef.current) clearTimeout(reconnectRef.current);
    pingRef.current = null;
    reconnectRef.current = null;
  };

  const connect = useCallback(() => {
    onStatusChange?.("connecting");
    const sep = url.includes("?") ? "&" : "?";
    const ws = new WebSocket(`${url}${sep}token=${encodeURIComponent(token)}`);
    wsRef.current = ws;

    ws.onopen = () => {
      attemptRef.current = 0;
      onStatusChange?.("open");
      pingRef.current = setInterval(() => {
        if (ws.readyState === WebSocket.OPEN) ws.send(JSON.stringify({ type: "ping" }));
      }, pingIntervalMs);
    };

    ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data) as WsMessage;
        if (msg.type === "pong") return;
        onMessage(msg);
      } catch {
        /* ignore malformed frames */
      }
    };

    ws.onclose = () => {
      clearTimers();
      onStatusChange?.("closed");
      if (closedRef.current) return;
      // exponential backoff with ±20% jitter
      const base = Math.min(maxBackoffMs, 1000 * 2 ** attemptRef.current);
      const jitter = base * 0.2 * (Math.random() * 2 - 1);
      attemptRef.current += 1;
      reconnectRef.current = setTimeout(connect, Math.max(0, base + jitter));
    };

    ws.onerror = () => ws.close();
  }, [url, token, onMessage, onStatusChange, pingIntervalMs, maxBackoffMs]);

  useEffect(() => {
    closedRef.current = false;
    connect();
    return () => {
      closedRef.current = true;
      clearTimers();
      wsRef.current?.close();
    };
  }, [connect]);

  const send = useCallback((data: unknown) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(data));
    }
  }, []);

  return { send };
}
