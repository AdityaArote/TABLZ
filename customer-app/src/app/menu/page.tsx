"use client";

import { useEffect, useState } from "react";
import { useApi } from "@/lib/api";
import { useCartStore } from "@/store/cart";
import { MenuItem } from "../../types/shared";
import { MagneticButton } from "@/components/MagneticButton";
import { ShoppingBag, Plus } from "lucide-react";
import Link from "next/link";
import gsap from "gsap";

export default function MenuPage() {
  const { fetchClient } = useApi();
  const [items, setItems] = useState<MenuItem[]>([]);
  const [loading, setLoading] = useState(true);

  const cartItemCount = useCartStore((state) => state.getItemCount());
  const addToCart = useCartStore((state) => state.addItem);

  useEffect(() => {
    const loadMenu = async () => {
      try {
        const res = await fetchClient("/menu");
        const data = await res.json();
        setItems(data.data || []);
      } catch (error) {
        console.error("Failed to load menu", error);
      } finally {
        setLoading(false);
      }
    };
    loadMenu();
  }, [fetchClient]);

  // Group by category
  const grouped = items.reduce(
    (acc, current) => {
      const cat = current.category || "General";
      if (!acc[cat]) acc[cat] = [];
      acc[cat].push(current);
      return acc;
    },
    {} as Record<string, MenuItem[]>,
  );

  // Intro animation
  useEffect(() => {
    if (!loading) {
      gsap.fromTo(
        ".menu-item-row",
        { y: 20, opacity: 0 },
        { y: 0, opacity: 1, duration: 0.6, stagger: 0.05, ease: "power2.out" },
      );
    }
  }, [loading]);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <div className="w-8 h-8 border-2 border-primary border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background pb-32">
      {/* Mobile-First Floating Header */}
      <header className="sticky top-0 z-40 bg-background/80 backdrop-blur-xl border-b border-outline-variant px-6 py-6">
        <h1 className="font-display italic text-3xl font-bold text-on-background">
          Explore the Menu
        </h1>
        <p className="text-on-surface-variant text-sm mt-1">
          Tap an item to add to your curation.
        </p>
      </header>

      <div className="px-6 py-8 space-y-12">
        {Object.entries(grouped).map(([category, catItems]) => (
          <section key={category}>
            <h2 className="font-sans text-primary text-xs uppercase tracking-widest pl-2 mb-4 border-l-2 border-primary">
              {category}
            </h2>

            <div className="space-y-4">
              {catItems.map((item) => (
                <div
                  key={item.id}
                  className="menu-item-row glass-card p-4 flex justify-between items-center group cursor-pointer"
                  onClick={() => addToCart(item, 1)}
                >
                  <div className="flex-1 pr-4">
                    <h3 className="font-sans font-medium text-lg text-on-background leading-tight">
                      {item.name}
                    </h3>
                    {item.description && (
                      <p className="text-sm text-on-surface-variant mt-1 line-clamp-2">
                        {item.description}
                      </p>
                    )}
                    <div className="font-mono text-primary mt-2">
                      ${item.price.toFixed(2)}
                    </div>
                  </div>

                  <button className="w-10 h-10 rounded-full bg-surface-lowest border border-outline-variant flex items-center justify-center text-primary group-hover:bg-primary group-hover:text-on-primary transition-colors">
                    <Plus size={18} />
                  </button>
                </div>
              ))}
            </div>
          </section>
        ))}
      </div>

      {/* Floating Action Button for Cart */}
      {cartItemCount > 0 && (
        <div className="fixed bottom-8 left-1/2 -translate-x-1/2 z-50 animate-[fadeUp_0.5s_ease-out_forwards]">
          <Link href="/checkout">
            <MagneticButton
              variant="primary"
              className="px-8 py-4 flex items-center space-x-3 rounded-full shadow-[0_10px_40px_-10px_rgba(201,168,76,0.6)]"
            >
              <ShoppingBag size={20} />
              <span className="font-sans font-medium text-lg">
                View Curation ({cartItemCount})
              </span>
            </MagneticButton>
          </Link>
        </div>
      )}
    </div>
  );
}
