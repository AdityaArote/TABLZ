"use client";

import { useState, useRef, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/components/AuthProvider";
import { MagneticButton } from "@/components/MagneticButton";
import gsap from "gsap";

export default function LoginPage() {
  const [adminId, setAdminId] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  
  const { setAccessToken } = useAuth();
  const router = useRouter();
  const formRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (formRef.current) {
      gsap.fromTo(
        formRef.current.children,
        { y: 40, opacity: 0 },
        { y: 0, opacity: 1, duration: 0.8, stagger: 0.15, ease: "power3.out" }
      );
    }
  }, []);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      const res = await fetch("http://localhost:8000/api/v1/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ admin_id: adminId, password }),
        credentials: "include",
      });

      const data = await res.json();

      if (res.ok) {
        setAccessToken(data.data.access_token);
        router.push("/");
      } else {
        setError(data.error?.message || "Login failed");
      }
    } catch (err) {
      console.error(err);
      setError("Network error connecting to server.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="relative min-h-screen flex items-center bg-background overflow-hidden selection:bg-primary/30 selection:text-primary">
      {/* Background Graphic Element */}
      <div className="absolute inset-0 z-0">
        <div className="absolute top-[-20%] right-[-10%] w-[800px] h-[800px] bg-primary/10 rounded-full blur-[120px] mix-blend-screen" />
        <div className="absolute bottom-[-10%] left-[-20%] w-[600px] h-[600px] bg-primary-container/10 rounded-full blur-[100px] mix-blend-screen" />
      </div>

      <div className="container mx-auto px-6 relative z-10 flex flex-col lg:flex-row items-center justify-between">
        
        {/* Typographic Hero */}
        <div className="lg:w-1/2 mb-16 lg:mb-0">
          <div className="overflow-hidden">
            <h1 className="font-sans text-white text-5xl md:text-7xl font-bold tracking-tight mb-2 opacity-0 animate-[fadeUp_0.8s_ease-out_forwards]">
              Digital Maître D&apos;
            </h1>
          </div>
          <div className="overflow-hidden">
            <h2 className="font-display italic text-primary text-6xl md:text-8xl mt-[-10px] opacity-0 animate-[fadeUp_0.8s_ease-out_0.2s_forwards]">
              System.
            </h2>
          </div>
        </div>

        {/* Login Form Wrapper */}
        <div className="lg:w-1/3 w-full max-w-md">
          <div 
            ref={formRef}
            className="glass-card p-10 flex flex-col space-y-8"
          >
            <div>
              <h3 className="text-xl font-sans font-semibold text-on-background">Staff Terminal</h3>
              <p className="text-sm text-on-surface-variant mt-1">Authenticate to access operations.</p>
            </div>

            <form onSubmit={handleLogin} className="flex flex-col space-y-6">
              
              <div className="relative group">
                <input
                  type="text"
                  id="adminId"
                  value={adminId}
                  onChange={(e) => setAdminId(e.target.value.toUpperCase())}
                  className="w-full bg-surface-highest/50 border border-outline-variant rounded-xl px-4 py-4 text-on-background placeholder-transparent focus:outline-none focus:border-primary transition-colors focus:bg-surface-lowest peer"
                  placeholder="Admin ID"
                  required
                />
                <label 
                  htmlFor="adminId" 
                  className="absolute left-4 -top-2.5 bg-surface-lowest px-1 text-xs text-on-surface-variant transition-all peer-placeholder-shown:text-base peer-placeholder-shown:text-on-surface-variant peer-placeholder-shown:top-4 peer-focus:-top-2.5 peer-focus:text-xs peer-focus:text-primary"
                >
                  Admin ID (TBZ-...)
                </label>
              </div>

              <div className="relative group">
                <input
                  type="password"
                  id="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full bg-surface-highest/50 border border-outline-variant rounded-xl px-4 py-4 text-on-background placeholder-transparent focus:outline-none focus:border-primary transition-colors focus:bg-surface-lowest peer"
                  placeholder="Password"
                  required
                />
                <label 
                  htmlFor="password" 
                  className="absolute left-4 -top-2.5 bg-surface-lowest px-1 text-xs text-on-surface-variant transition-all peer-placeholder-shown:text-base peer-placeholder-shown:text-on-surface-variant peer-placeholder-shown:top-4 peer-focus:-top-2.5 peer-focus:text-xs peer-focus:text-primary"
                >
                  Password
                </label>
              </div>

              {error && (
                <div className="text-status-cleaning text-sm font-medium p-3 bg-status-cleaning/10 rounded-lg">
                  {error}
                </div>
              )}

              <MagneticButton 
                type="submit" 
                disabled={loading}
                className="w-full mt-4"
              >
                {loading ? "Authenticating..." : "Establish Secure Link"}
              </MagneticButton>
            </form>
          </div>
        </div>
      </div>
    </div>
  );
}
