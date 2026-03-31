"use client";

import { useState } from "react";
import { useAuth } from "@/components/AuthProvider";
import { BASE_URL } from "@/lib/api";

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const { setAuth } = useAuth();

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError("");

    try {
      const res = await fetch(`${BASE_URL}/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ admin_id: email, password }),
      });

      const data = await res.json();
      if (res.ok && data.data?.access_token) {
        // Also need the restaurant_id to hook up WebSockets!
        const meRes = await fetch(`${BASE_URL}/auth/me`, {
          headers: { Authorization: `Bearer ${data.data.access_token}` }
        });
        const meData = await meRes.json();
        
        if (meRes.ok && meData.data) {
          setAuth(data.data.access_token, meData.data.restaurant_id);
          // Redirect handled by AuthProvider (or router push) automatically
          window.location.href = "/"; 
        } else {
          setError("Failed to verify staff permissions.");
        }
      } else {
        setError(data.error?.message || "Invalid credential.");
      }
    } catch (err) {
      console.error(err);
      setError("Kitchen uplink offline.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-background flex flex-col items-center justify-center p-6 relative">
      <div className="w-full max-w-sm glass-card p-10 relative z-10">
        <div className="mb-10 text-center">
          <h1 className="font-display italic text-3xl text-primary font-bold">Kitchen Sys.</h1>
          <p className="font-mono text-xs uppercase tracking-[0.2em] text-on-surface-variant mt-2">
            Authorized Personnel Only
          </p>
        </div>

        <form onSubmit={handleLogin} className="space-y-6">
          <div className="space-y-1">
            <input
              type="text"
              placeholder="System ID"
              className="w-full bg-surface-lowest text-on-background border border-outline focus:border-primary focus:ring-1 focus:ring-primary rounded-xl px-4 py-3 font-mono text-sm outline-none transition-colors"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
          </div>
          <div className="space-y-1">
            <input
              type="password"
              placeholder="Passcode"
              className="w-full bg-surface-lowest text-on-background border border-outline focus:border-primary focus:ring-1 focus:ring-primary rounded-xl px-4 py-3 font-mono text-sm outline-none transition-colors"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </div>

          {error && (
            <div className="text-status-pending text-xs py-2 px-3 bg-status-pending/10 rounded-lg">
              ERR: {error}
            </div>
          )}

          <button
            type="submit"
            disabled={loading}
            className="w-full bg-primary text-on-primary font-mono text-sm uppercase tracking-widest py-3 rounded-xl hover:bg-primary-container transition-colors disabled:opacity-50"
          >
            {loading ? "Authenticating..." : "Establish Uplink"}
          </button>
        </form>
      </div>
    </div>
  );
}
