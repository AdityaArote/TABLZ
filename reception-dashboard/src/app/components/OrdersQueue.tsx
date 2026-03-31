"use client";

import { useEffect, useState, useCallback } from "react";
import { useApi } from "@/lib/api";
import type { Order } from "../../../types/shared";
import { Clock } from "lucide-react";

export default function OrdersQueue() {
  const { fetchWithAuth } = useApi();
  const [orders, setOrders] = useState<Order[]>([]);

  const fetchOrders = useCallback(async () => {
    try {
      const res = await fetchWithAuth("/orders");
      const data = await res.json();
      // Filter for active orders (not received or cancelled)
      const active = (data.data || []).filter(
        (o: Order) => !["received", "cancelled"].includes(o.status),
      );
      setOrders(active);
    } catch (e) {
      console.error(e);
    }
  }, [fetchWithAuth]);

  useEffect(() => {
    fetchOrders();
    const interval = setInterval(fetchOrders, 10000);
    return () => clearInterval(interval);
  }, [fetchOrders]);

  const getTimeAgo = (dateStr: string) => {
    const min = Math.floor(
      (new Date().getTime() - new Date(dateStr).getTime()) / 60000,
    );
    if (min < 1) return "Just now";
    return `${min}m ago`;
  };

  // The "No-Line" Rule: We use alternating tonal shifts padding instead of bottom borders
  return (
    <div className="flex-1 overflow-y-auto no-scrollbar py-4 space-y-2">
      {orders.length === 0 ? (
        <div className="h-full flex flex-col items-center justify-center text-on-surface-variant">
          <Clock size={32} className="mb-4 opacity-50" />
          <p className="font-sans">No active orders</p>
        </div>
      ) : (
        orders.map((order, idx) => (
          <div
            key={order.id}
            className={`px-6 py-4 flex flex-col space-y-3 transition-colors hover:bg-surface-highest/50 ${
              idx % 2 === 0 ? "bg-surface-lowest/50" : "bg-transparent"
            }`}
          >
            <div className="flex justify-between items-center">
              <div className="flex items-center space-x-3">
                <span className="font-mono text-primary font-bold">
                  TBL-{order.table_id.substring(0, 4).toUpperCase()}
                </span>
                <span className="text-xs text-on-surface-variant flex items-center">
                  <Clock size={12} className="mr-1" />
                  {getTimeAgo(order.placed_at)}
                </span>
              </div>

              <div className="px-2 py-1 rounded bg-surface text-xs font-mono uppercase tracking-wider text-on-background border border-outline-variant">
                {order.status}
              </div>
            </div>

            <div className="flex justify-between items-end">
              <div className="text-sm text-on-surface-variant">
                {order.items.length} Items
              </div>
              <div className="font-mono text-lg text-primary">
                ${order.total_amount.toFixed(2)}
              </div>
            </div>
          </div>
        ))
      )}
    </div>
  );
}
