"use client";

import { useEffect, useState } from "react";
import { useApi } from "@/lib/api";
import type { Order } from "../../../types/shared";
import { CheckCircle2, Ticket } from "lucide-react";
import gsap from "gsap";

export default function ReceiptPage({ params }: { params: { id: string } }) {
  const { fetchClient } = useApi();
  const [order, setOrder] = useState<Order | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Reveal animation
    gsap.fromTo(
      ".receipt-reveal",
      { y: 30, opacity: 0 },
      { y: 0, opacity: 1, duration: 0.8, stagger: 0.1, ease: "power3.out" },
    );
  }, []);

  useEffect(() => {
    const fetchOrder = async () => {
      try {
        const res = await fetchClient(`/orders/${params.id}`);
        const data = await res.json();
        setOrder(data.data);
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    };
    fetchOrder();
  }, [fetchClient, params.id]);

  if (loading || !order) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <div className="w-8 h-8 border-2 border-primary border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  // A stylized fake barcode generation based on order ID
  const generateBarcodeLines = () => {
    const lines = [];
    const seed = order.id
      .split("")
      .reduce((acc, char) => acc + char.charCodeAt(0), 0);
    for (let i = 0; i < 40; i++) {
      const width = ["w-1", "w-1.5", "w-2", "w-3"][
        Math.floor(((seed * i) % 73) % 4)
      ];
      lines.push(
        <div key={i} className={`h-16 bg-on-surface ${width} mx-[1px]`} />,
      );
    }
    return lines;
  };

  return (
    <div className="min-h-screen bg-background relative flex flex-col items-center justify-center py-12 px-6">
      <div className="receipt-reveal flex flex-col items-center mb-8 text-center space-y-3">
        <div className="w-16 h-16 rounded-full bg-surface-highest flex items-center justify-center text-primary mb-2 shadow-[0_0_20px_rgba(201,168,76,0.3)]">
          <CheckCircle2 size={32} />
        </div>
        <h1 className="font-display italic text-3xl font-bold text-primary">
          Transmission Complete
        </h1>
        <p className="font-sans text-on-surface-variant max-w-xs text-sm">
          Your curation has been received by the kitchen. Please present this
          credential at the maître d&apos; desk to finalize.
        </p>
      </div>

      <div className="receipt-reveal w-full max-w-sm glass-card bg-surface-lowest flex flex-col relative overflow-hidden">
        {/* Receipt Notch Top */}
        <div className="absolute top-0 left-0 w-full flex justify-between px-4 -mt-3">
          {[...Array(12)].map((_, i) => (
            <div key={i} className="w-4 h-4 rounded-full bg-background" />
          ))}
        </div>

        <div className="p-8 pt-12 text-center border-b border-outline-variant/30 custom-dashed-border">
          <span className="font-sans text-xs uppercase tracking-widest text-on-surface-variant block mb-2">
            Final Obligation
          </span>
          <span className="font-mono text-5xl font-light text-on-background">
            ${order.total_amount.toFixed(2)}
          </span>
        </div>

        <div className="p-8 bg-surface/50 border-b border-outline-variant/30 text-left space-y-3">
          <div className="flex justify-between text-sm">
            <span className="text-on-surface-variant">Transaction ID</span>
            <span className="font-mono text-on-background opacity-80 uppercase">
              {order.id.slice(0, 8)}
            </span>
          </div>
          <div className="flex justify-between text-sm">
            <span className="text-on-surface-variant">Table Designation</span>
            <span className="font-mono text-on-background">
              {order.table_id.slice(-4).toUpperCase()}
            </span>
          </div>
          <div className="flex justify-between text-sm">
            <span className="text-on-surface-variant">Time Indexed</span>
            <span className="font-mono text-on-background">
              {new Date(order.placed_at).toLocaleTimeString([], {
                hour: "2-digit",
                minute: "2-digit",
              })}
            </span>
          </div>
        </div>

        <div className="p-8 flex flex-col items-center justify-center bg-surface-highest">
          <div className="flex items-center justify-center w-full mb-2">
            {generateBarcodeLines()}
          </div>
          <span className="font-mono text-[10px] tracking-[0.2em] text-on-surface-variant mt-2">
            SCAN TO FINALIZE
          </span>
        </div>

        {/* Receipt Notch Bottom */}
        <div className="absolute bottom-0 left-0 w-full flex justify-between px-4 -mb-3">
          {[...Array(12)].map((_, i) => (
            <div key={i} className="w-4 h-4 rounded-full bg-background" />
          ))}
        </div>
      </div>

      <div className="receipt-reveal mt-8 cursor-pointer text-primary text-sm flex items-center space-x-2 hover:opacity-80 transition-opacity">
        <Ticket size={16} />
        <span className="font-medium underline decoration-primary/30 underline-offset-4">
          Return to Table Overview
        </span>
      </div>
    </div>
  );
}
