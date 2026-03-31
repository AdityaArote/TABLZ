"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import { useAuth } from "@/components/AuthProvider";
import { useWebSocket } from "@/hooks/useWebSocket";
import { BASE_URL } from "@/lib/api";
import type { Order, MenuItem } from "../types/shared";
import { ChefHat, CheckSquare, ArrowRight } from "lucide-react";

export default function ChefDashboard() {
  const { token, restaurantId, logout } = useAuth();
  const { status, messages, clearMessages } = useWebSocket(restaurantId, token);
  const [orders, setOrders] = useState<Order[]>([]);
  const [menuItems, setMenuItems] = useState<Record<string, MenuItem>>({});
  const containerRef = useRef<HTMLDivElement>(null);

  // Fetch initial state queue natively across REST before WS handles diffs
  const fetchQueue = useCallback(async () => {
    if (!token) return;
    try {
      // 1. Fetch menu dict to resolve ID names
      const menuRes = await fetch(`${BASE_URL}/menu`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      const menuData = await menuRes.json();
      const menuMap: Record<string, MenuItem> = {};
      (menuData.data || []).forEach((m: MenuItem) => {
        menuMap[m.id] = m;
      });
      setMenuItems(menuMap);

      // 2. Fetch active orders
      const orderRes = await fetch(`${BASE_URL}/orders`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      const orderData = await orderRes.json();

      // Filter out received/cancelled from main view
      const active = (orderData.data || []).filter((o: Order) =>
        ["pending", "preparing", "ready"].includes(o.status),
      );
      setOrders(active);
    } catch (e) {
      console.error(e);
    }
  }, [token]);

  useEffect(() => {
    fetchQueue();
  }, [fetchQueue]);

  // Handle incoming WS events
  useEffect(() => {
    if (messages.length > 0) {
      const newOrders = [...orders];
      let didModify = false;

      messages.forEach((msg) => {
        if (
          msg.event === "order.created" ||
          msg.event === "order.status_changed"
        ) {
          const typedMsg = msg as { data?: { order?: Order } };
          const incomingOrder = typedMsg.data?.order;
          if (!incomingOrder) return;

          if (["received", "cancelled"].includes(incomingOrder.status)) {
            // Remove from view
            const index = newOrders.findIndex((o) => o.id === incomingOrder.id);
            if (index > -1) {
              newOrders.splice(index, 1);
              didModify = true;
            }
          } else {
            const index = newOrders.findIndex((o) => o.id === incomingOrder.id);
            if (index > -1) {
              newOrders[index] = incomingOrder;
            } else {
              newOrders.push(incomingOrder);
            }
            didModify = true;
          }
        }
      });

      if (didModify) {
        // Sort oldest first
        newOrders.sort(
          (a, b) =>
            new Date(a.placed_at).getTime() - new Date(b.placed_at).getTime(),
        );
        setOrders(newOrders);
        clearMessages();
      }
    }
  }, [messages, orders, clearMessages]);

  const updateStatus = async (orderId: string, newStatus: string) => {
    if (!token) return;
    try {
      await fetch(`${BASE_URL}/orders/${orderId}/status`, {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ status: newStatus }),
      });
      // Don't modify UI immediately; let WS event bounce back for ultimate truth sync
    } catch (e) {
      console.error("Status update error", e);
    }
  };

  return (
    <div className="min-h-screen bg-background text-on-background flex flex-col font-sans h-screen overflow-hidden">
      {/* Header */}
      <header className="flex-none bg-surface/80 backdrop-blur-md border-b border-outline-variant px-6 py-4 flex items-center justify-between z-10">
        <div className="flex items-center space-x-4">
          <ChefHat className="text-primary" size={28} />
          <div>
            <h1 className="font-display italic text-xl font-bold leading-none">
              Line Command
            </h1>
            <p className="font-mono text-[10px] text-on-surface-variant uppercase tracking-widest mt-1">
              Live Ticket Stream
            </p>
          </div>
        </div>

        <div className="flex items-center space-x-6">
          <div className="flex items-center space-x-2">
            <div
              className={`w-3 h-3 rounded-full ${status === "connected" ? "bg-status-ready animate-pulse-slow shadow-[0_0_10px_#34D399]" : "bg-status-pending"}`}
            />
            <span className="font-mono text-xs uppercase tracking-wider text-on-surface-variant">
              Uplink {status}
            </span>
          </div>
          <button
            onClick={logout}
            className="text-on-surface-variant hover:text-primary transition-colors"
          >
            <span className="font-mono text-xs uppercase cursor-pointer">
              Log Out
            </span>
          </button>
        </div>
      </header>

      {/* Kanban Grid */}
      <main
        className="flex-1 overflow-x-auto overflow-y-hidden p-6 gap-6 relative"
        ref={containerRef}
      >
        <div className="flex h-full gap-6 w-max">
          {/* Column: Pending */}
          <div className="flex flex-col w-96 h-full bg-surface-lowest/50 rounded-2xl border border-outline-variant p-4">
            <h2 className="font-sans text-status-pending text-sm font-semibold tracking-widest uppercase mb-4 flex items-center">
              <span className="w-2 h-2 rounded-full bg-status-pending mr-2" />{" "}
              Incoming
            </h2>
            <div className="flex-1 overflow-y-auto no-scrollbar space-y-4">
              {orders
                .filter((o) => o.status === "pending")
                .map((o) => (
                  <div
                    key={o.id}
                    className="glass-card p-4 border-l-4 border-status-pending"
                  >
                    <div className="flex justify-between items-start mb-3">
                      <span className="font-mono text-sm text-on-surface-variant">
                        TBL: {o.table_id.slice(-4).toUpperCase()}
                      </span>
                      <span className="font-mono text-xs text-on-surface-variant">
                        {((new Date().getTime() -
                          new Date(o.placed_at).getTime()) /
                          60000) |
                          0}
                        m ago
                      </span>
                    </div>
                    <ul className="space-y-2 mb-4">
                      {o.items.map((i) => (
                        <li key={i.id} className="flex justify-between text-sm">
                          <span>
                            <span className="font-mono text-primary mr-2">
                              {i.quantity}x
                            </span>{" "}
                            {menuItems[i.menu_item_id]?.name || "Item"}
                          </span>
                        </li>
                      ))}
                    </ul>
                    <button
                      onClick={() => updateStatus(o.id, "preparing")}
                      className="w-full py-2 flex items-center justify-center space-x-2 bg-status-pending/10 hover:bg-status-pending/20 text-status-pending rounded-lg transition-colors font-mono text-xs uppercase"
                    >
                      <span>Start Fire</span> <ArrowRight size={14} />
                    </button>
                  </div>
                ))}
            </div>
          </div>

          {/* Column: Preparing */}
          <div className="flex flex-col w-96 h-full bg-surface-lowest/50 rounded-2xl border border-outline-variant p-4">
            <h2 className="font-sans text-status-preparing text-sm font-semibold tracking-widest uppercase mb-4 flex items-center">
              <span className="w-2 h-2 rounded-full bg-status-preparing mr-2" />{" "}
              Firing
            </h2>
            <div className="flex-1 overflow-y-auto no-scrollbar space-y-4">
              {orders
                .filter((o) => o.status === "preparing")
                .map((o) => (
                  <div
                    key={o.id}
                    className="glass-card p-4 border-l-4 border-status-preparing"
                  >
                    <div className="flex justify-between items-start mb-3">
                      <span className="font-mono text-sm text-on-surface-variant">
                        TBL: {o.table_id.slice(-4).toUpperCase()}
                      </span>
                      <span className="font-mono text-xs text-on-surface-variant">
                        {((new Date().getTime() -
                          new Date(o.placed_at).getTime()) /
                          60000) |
                          0}
                        m ago
                      </span>
                    </div>
                    <ul className="space-y-2 mb-4">
                      {o.items.map((i) => (
                        <li key={i.id} className="flex justify-between text-sm">
                          <span>
                            <span className="font-mono text-status-preparing mr-2">
                              {i.quantity}x
                            </span>{" "}
                            {menuItems[i.menu_item_id]?.name || "Item"}
                          </span>
                        </li>
                      ))}
                    </ul>
                    <button
                      onClick={() => updateStatus(o.id, "ready")}
                      className="w-full py-2 flex items-center justify-center space-x-2 bg-status-preparing/10 hover:bg-status-preparing/20 text-status-preparing rounded-lg transition-colors font-mono text-xs uppercase"
                    >
                      <CheckSquare size={14} /> <span>Mark Ready</span>
                    </button>
                  </div>
                ))}
            </div>
          </div>

          {/* Column: Ready */}
          <div className="flex flex-col w-96 h-full bg-surface-lowest/50 rounded-2xl border border-outline-variant p-4">
            <h2 className="font-sans text-status-ready text-sm font-semibold tracking-widest uppercase mb-4 flex items-center">
              <span className="w-2 h-2 rounded-full bg-status-ready mr-2" />{" "}
              Awaiting Runner
            </h2>
            <div className="flex-1 overflow-y-auto no-scrollbar space-y-4">
              {orders
                .filter((o) => o.status === "ready")
                .map((o) => (
                  <div
                    key={o.id}
                    className="glass-card p-4 border-l-4 border-status-ready opacity-50 hover:opacity-100 transition-opacity"
                  >
                    <div className="flex justify-between items-start mb-3">
                      <span className="font-mono text-sm text-on-surface-variant">
                        TBL: {o.table_id.slice(-4).toUpperCase()}
                      </span>
                    </div>
                    <div className="font-mono text-xs text-status-ready text-center py-2 bg-status-ready/10 rounded-lg">
                      Ready for Floor
                    </div>
                  </div>
                ))}
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
