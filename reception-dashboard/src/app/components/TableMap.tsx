"use client";

import { useEffect, useState, useRef, useCallback } from "react";
import { useApi } from "@/lib/api";
import type { Table } from "../../../types/shared";
import gsap from "gsap";
import { Users, RefreshCw, CheckCircle2 } from "lucide-react";

export default function TableMap() {
  const { fetchWithAuth } = useApi();
  const [tables, setTables] = useState<Table[]>([]);
  const [loading, setLoading] = useState(true);
  const gridRef = useRef<HTMLDivElement>(null);

  const fetchTables = useCallback(async () => {
    try {
      const res = await fetchWithAuth("/tables");
      const data = await res.json();
      setTables(data.data || []);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  }, [fetchWithAuth]);

  useEffect(() => {
    fetchTables();
    // Poll every 10s for updates
    const interval = setInterval(fetchTables, 10000);
    return () => clearInterval(interval);
  }, [fetchTables]);

  useEffect(() => {
    if (!loading && gridRef.current && tables.length > 0) {
      gsap.fromTo(
        gridRef.current.children,
        { scale: 0.9, opacity: 0 },
        {
          scale: 1,
          opacity: 1,
          duration: 0.5,
          stagger: 0.05,
          ease: "back.out(1.7)",
        },
      );
    }
  }, [loading, tables.length]);

  const updateTableStatus = async (
    tableId: string,
    status: "available" | "occupied" | "cleaning",
  ) => {
    try {
      await fetchWithAuth(`/tables/${tableId}`, {
        method: "PUT",
        body: JSON.stringify({ status }),
      });
      // Optimistic UI update
      setTables((prev) =>
        prev.map((t) => (t.id === tableId ? { ...t, status } : t)),
      );
    } catch (e) {
      console.error("Failed to update status", e);
    }
  };

  if (loading) {
    return (
      <div className="absolute inset-0 flex items-center justify-center">
        <div className="w-6 h-6 border-2 border-primary border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case "occupied":
        return "bg-status-occupied shadow-[0_0_12px_rgba(201,168,76,0.5)]";
      case "cleaning":
        return "bg-status-cleaning shadow-[0_0_12px_rgba(123,97,255,0.5)]";
      case "available":
        return "bg-on-surface-variant/20";
      default:
        return "bg-on-surface-variant/20";
    }
  };

  return (
    <div
      ref={gridRef}
      className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-6 p-2"
    >
      {tables.map((table) => (
        <div
          key={table.id}
          className="group relative h-40 rounded-2xl bg-surface p-5 border border-outline-variant flex flex-col justify-between hover:bg-surface-highest hover:border-primary/30 transition-all duration-300"
        >
          {/* Status Orb + Menu logic */}
          <div className="flex justify-between items-start">
            <div className="flex items-center space-x-3">
              <div
                className={`w-3 h-3 rounded-full ${getStatusColor(table.status)}`}
              />
              <span className="font-mono text-sm text-on-surface-variant capitalize">
                {table.status}
              </span>
            </div>

            {/* Hover Actions */}
            <div className="opacity-0 group-hover:opacity-100 transition-opacity flex space-x-1">
              {table.status !== "available" && (
                <button
                  onClick={() => updateTableStatus(table.id, "available")}
                  title="Make Available"
                  className="p-1.5 rounded-lg bg-surface-lowest text-on-surface-variant hover:text-status-occupied transition-colors"
                >
                  <CheckCircle2 size={16} />
                </button>
              )}
              {table.status === "occupied" && (
                <button
                  onClick={() => updateTableStatus(table.id, "cleaning")}
                  title="Mark Cleaning"
                  className="p-1.5 rounded-lg bg-surface-lowest text-on-surface-variant hover:text-status-cleaning transition-colors"
                >
                  <RefreshCw size={16} />
                </button>
              )}
            </div>
          </div>

          <div>
            <div className="text-4xl font-display font-bold text-on-background mb-1">
              {table.table_number.toString().padStart(2, "0")}
            </div>
            <div className="flex items-center space-x-1.5 text-on-surface-variant text-sm">
              <Users size={14} />
              <span>{table.max_capacity} Seats</span>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}
