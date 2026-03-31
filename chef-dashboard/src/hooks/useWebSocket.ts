"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import { getWsUrl } from "@/lib/api";

type ConnectionStatus = "connecting" | "connected" | "disconnected";

export function useWebSocket(restaurantId: string | null, token: string | null) {
  const [status, setStatus] = useState<ConnectionStatus>("disconnected");
  const [messages, setMessages] = useState<Record<string, unknown>[]>([]);
  const ws = useRef<WebSocket | null>(null);

  const connect = useCallback(() => {
    if (!restaurantId || !token) return;

    ws.current = new WebSocket(getWsUrl(restaurantId, token));
    setStatus("connecting");

    ws.current.onopen = () => {
      // Backend expects immediate auth message
      ws.current?.send(JSON.stringify({ type: "auth", token }));
    };

    ws.current.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === "auth_success") {
          setStatus("connected");
        } else if (data.type === "heartbeat") {
          ws.current?.send(JSON.stringify({ type: "pong" }));
        } else if (data.type === "auth_failed" || data.type === "auth_timeout") {
           setStatus("disconnected");
        } else {
          // Push meaningful broadcast events to the local message queue
          setMessages((prev) => [...prev, data]);
        }
      } catch (e) {
        console.error("WS Parse error", e);
      }
    };

    ws.current.onclose = () => {
      setStatus("disconnected");
      // Auto-reconnect after 3s
      setTimeout(connect, 3000);
    };

    ws.current.onerror = () => {
      setStatus("disconnected");
      ws.current?.close();
    };
  }, [restaurantId, token]);

  useEffect(() => {
    connect();
    return () => {
      if (ws.current) ws.current.close();
    };
  }, [connect]);

  // Method to manually clear processed messages if needed
  const clearMessages = useCallback(() => setMessages([]), []);

  return { status, messages, clearMessages };
}
