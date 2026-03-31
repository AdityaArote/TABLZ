"use client";

import { useEffect, useState } from "react";
import { useAuth } from "@/components/AuthProvider";
import { useApi } from "@/lib/api";
import { LogOut } from "lucide-react";
import { MagneticButton } from "@/components/MagneticButton";

// Placeholder components that will be built next
import TableMap from "./components/TableMap";
import OrdersQueue from "./components/OrdersQueue";

export default function DashboardHome() {
  const { logout } = useAuth();
  const { fetchWithAuth } = useApi();
  const [stats, setStats] = useState({ revenue: 0, orders: 0, occupancy: 0 });

  useEffect(() => {
    // Fetch Quick Stats
    fetchWithAuth("/analytics/summary?period=daily")
      .then(res => res.json())
      .then(data => {
        if(data.data) {
          setStats({
            revenue: data.data.revenue || 0,
            orders: data.data.total_orders || 0,
            occupancy: data.data.occupancy_rate || 0,
          });
        }
      })
      .catch(err => console.error("Failed to load stats", err));
  }, [fetchWithAuth]);

  return (
    <div className="min-h-screen bg-background relative pt-24 pb-12 px-6 lg:px-12">
      {/* Floating Island Navbar */}
      <nav className="fixed top-6 left-1/2 -translate-x-1/2 w-[95%] max-w-7xl glass rounded-full px-6 py-4 flex items-center justify-between z-50">
        <div className="flex items-center space-x-8">
          <div className="font-display italic text-2xl text-primary font-bold">TABLZ.</div>
          <div className="hidden md:flex items-center space-x-6">
            <button className="text-on-surface-variant hover:text-primary transition-colors text-sm font-medium">Floor Plan</button>
            <button className="text-on-surface-variant hover:text-primary transition-colors text-sm font-medium">Active Orders</button>
            <button className="text-on-surface-variant hover:text-primary transition-colors text-sm font-medium">Menu Settings</button>
          </div>
        </div>

        <div className="flex items-center space-x-6">
          <div className="flex items-center space-x-2">
            <span className="relative flex h-3 w-3">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-3 w-3 bg-green-500"></span>
            </span>
            <span className="font-mono text-xs text-on-surface-variant hidden sm:inline-block">SYSTEM OPERATIONAL</span>
          </div>
          
          <button 
            onClick={() => logout()}
            className="text-on-surface-variant hover:text-primary transition-colors p-2"
          >
            <LogOut size={18} />
          </button>
        </div>
      </nav>

      <div className="max-w-7xl mx-auto space-y-12">
        {/* Quick Stats Bar */}
        <section className="grid grid-cols-1 md:grid-cols-3 gap-6 animate-[fadeUp_0.8s_ease-out_forwards]">
          <div className="glass-card p-6 flex flex-col justify-between h-32">
            <span className="text-sm font-sans text-on-surface-variant">Daily Revenue</span>
            <span className="font-mono text-3xl font-light text-on-background">${stats.revenue.toFixed(2)}</span>
          </div>
          <div className="glass-card p-6 flex flex-col justify-between h-32">
            <span className="text-sm font-sans text-on-surface-variant">Active Orders</span>
            <span className="font-mono text-3xl font-light text-on-background">{stats.orders}</span>
          </div>
          <div className="glass-card p-6 flex flex-col justify-between h-32">
            <span className="text-sm font-sans text-on-surface-variant">Table Occupancy</span>
            <span className="font-mono text-3xl font-light text-on-background">{stats.occupancy.toFixed(0)}%</span>
          </div>
        </section>

        {/* Main Content Areas */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          <section className="lg:col-span-2 space-y-6">
            <div className="flex justify-between items-end">
              <div>
                <h2 className="font-sans text-2xl font-semibold text-on-background">Floor Plan</h2>
                <p className="text-sm text-on-surface-variant mt-1">Live table status and capacity.</p>
              </div>
              <MagneticButton variant="secondary" className="scale-90 origin-bottom-right">
                Refresh Map
              </MagneticButton>
            </div>
            
            {/* TableMap component will go here */}
            <div className="glass-card min-h-[500px] p-6 !bg-surface-low relative">
               <TableMap />
            </div>
          </section>

          <section className="space-y-6">
             <div>
                <h2 className="font-sans text-2xl font-semibold text-on-background">Order Queue</h2>
                <p className="text-sm text-on-surface-variant mt-1">Pending action required.</p>
              </div>
            
            {/* OrdersQueue component will go here */}
            <div className="glass-card h-[500px] p-0 flex flex-col overflow-hidden">
               <OrdersQueue />
            </div>
          </section>
        </div>
      </div>
    </div>
  );
}
