"use client";

import { useState } from "react";
import { useCartStore } from "@/store/cart";
import { useApi } from "@/lib/api";
import { useRouter } from "next/navigation";
import { MagneticButton } from "@/components/MagneticButton";
import Link from "next/link";
import { ArrowLeft, Trash2, Minus, Plus } from "lucide-react";

export default function CheckoutPage() {
  const { items, updateQuantity, getTotal, clearCart } = useCartStore();
  const { fetchClient } = useApi();
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleCheckout = async () => {
    if (items.length === 0) return;
    setLoading(true);
    setError("");

    try {
      // Backend expects: { table_id: null, items: [{ menu_item_id, quantity, item_notes }] }
      // The session cookie determines the table automatically!
      const payload = {
        items: items.map(i => ({
          menu_item_id: i.menuItem.id,
          quantity: i.quantity,
          item_notes: i.itemNotes || ""
        }))
      };

      const res = await fetchClient("/orders", {
        method: "POST",
        body: JSON.stringify(payload)
      });
      const data = await res.json();

      if (res.ok) {
        clearCart();
        // Send user to receipt view
        router.push(`/receipt/${data.data.id}`);
      } else {
        setError(data.error?.message || "Failed to finalize your curation.");
      }
    } catch (e) {
      console.error(e);
      setError("Network error communicating with the kitchen.");
    } finally {
      setLoading(false);
    }
  };

  const total = getTotal();

  return (
    <div className="min-h-screen bg-background relative flex flex-col">
      <header className="sticky top-0 z-40 bg-background/80 backdrop-blur-xl border-b border-outline-variant px-6 py-6 flex items-center justify-between">
        <Link href="/menu" className="w-10 h-10 flex items-center justify-center rounded-full bg-surface hover:bg-surface-highest transition-colors">
          <ArrowLeft size={20} className="text-on-background" />
        </Link>
        <h1 className="font-display italic text-2xl font-bold text-on-background">Your Curation</h1>
        <div className="w-10"></div> {/* Spacer */}
      </header>

      <main className="flex-1 px-6 py-8 overflow-y-auto no-scrollbar">
        {items.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center text-center space-y-4">
            <p className="text-on-surface-variant font-sans">Your curation is currently empty.</p>
            <Link href="/menu">
              <MagneticButton variant="secondary">Return to Menu</MagneticButton>
            </Link>
          </div>
        ) : (
          <div className="space-y-6">
            {items.map((cartItem) => (
              <div key={cartItem.menuItem.id} className="glass-card p-4 flex justify-between items-start">
                <div className="flex-1 pr-4">
                  <h3 className="font-sans font-medium text-lg text-on-background">
                    {cartItem.menuItem.name}
                  </h3>
                  <div className="font-mono text-primary mt-1">
                    ${(cartItem.menuItem.price * cartItem.quantity).toFixed(2)}
                  </div>
                </div>

                <div className="flex items-center space-x-3 bg-surface-lowest px-2 py-1.5 rounded-xl border border-outline-variant">
                  <button 
                    onClick={() => updateQuantity(cartItem.menuItem.id, cartItem.quantity - 1)}
                    className="p-1 text-on-surface-variant hover:text-primary transition-colors"
                  >
                    {cartItem.quantity === 1 ? <Trash2 size={16} /> : <Minus size={16} />}
                  </button>
                  <span className="font-mono text-on-background w-4 text-center">{cartItem.quantity}</span>
                  <button 
                    onClick={() => updateQuantity(cartItem.menuItem.id, cartItem.quantity + 1)}
                    className="p-1 text-on-surface-variant hover:text-primary transition-colors"
                  >
                    <Plus size={16} />
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </main>

      {/* Checkout Footer block */}
      {items.length > 0 && (
        <footer className="bg-surface-lowest border-t border-outline-variant p-6 rounded-t-3xl">
          <div className="space-y-2 mb-6">
            <div className="flex justify-between text-on-surface-variant text-sm">
              <span>Subtotal</span>
              <span className="font-mono">${total.toFixed(2)}</span>
            </div>
            <div className="flex justify-between text-on-background font-medium text-lg pt-2 border-t border-outline-variant/30">
              <span>Total Curation</span>
              <span className="font-mono text-primary">${total.toFixed(2)}</span>
            </div>
            {error && (
              <p className="text-status-cleaning text-xs pt-2">Error: {error}</p>
            )}
          </div>
          
          <MagneticButton 
            variant="primary" 
            className="w-full py-4 text-lg"
            onClick={handleCheckout}
            disabled={loading}
          >
            {loading ? "Transmitting..." : "Send to Kitchen"}
          </MagneticButton>
        </footer>
      )}
    </div>
  );
}
