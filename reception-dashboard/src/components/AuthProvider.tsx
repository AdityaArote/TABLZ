"use client";

import { createContext, useContext, useEffect, useState } from "react";
import { useRouter, usePathname } from "next/navigation";

interface AuthContextType {
  accessToken: string | null;
  setAccessToken: (token: string | null) => void;
  isAuthenticated: boolean;
  isLoading: boolean;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType>({
  accessToken: null,
  setAccessToken: () => {},
  isAuthenticated: false,
  isLoading: true,
  logout: () => {},
});

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [accessToken, setAccessToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    // Check if we already have a session on load by attempting a refresh
    const initAuth = async () => {
      try {
        const res = await fetch("http://localhost:8000/api/v1/auth/refresh", {
          method: "POST",
          // Send HttpOnly cookies automatically
          credentials: "include", 
        });

        if (res.ok) {
          const data = await res.json();
          setAccessToken(data.data.access_token);
        } else {
          // Refresh failed (no session)
          if (pathname !== "/login") {
            router.push("/login");
          }
        }
      } catch (err) {
        console.error("Auth init failed", err);
      } finally {
        setIsLoading(false);
      }
    };

    initAuth();
  }, [pathname, router]);

  // Handle silent token refresh 2 minutes before expiry (expiry is 15min)
  useEffect(() => {
    if (!accessToken) return;

    const interval = setInterval(async () => {
      try {
        const res = await fetch("http://localhost:8000/api/v1/auth/refresh", {
          method: "POST",
          credentials: "include",
        });
        if (res.ok) {
          const data = await res.json();
          setAccessToken(data.data.access_token);
        } else {
          setAccessToken(null);
          router.push("/login");
        }
      } catch (error) {
        console.error("Token refresh failed", error);
      }
    }, 13 * 60 * 1000); // 13 minutes

    return () => clearInterval(interval);
  }, [accessToken, router]);

  const logout = async () => {
    try {
      await fetch("http://localhost:8000/api/v1/auth/logout", {
        method: "POST",
        credentials: "include",
        headers: {
          "Authorization": `Bearer ${accessToken}`
        }
      });
    } catch (e) {
      console.error(e);
    } finally {
      setAccessToken(null);
      router.push("/login");
    }
  };

  return (
    <AuthContext.Provider
      value={{
        accessToken,
        setAccessToken,
        isAuthenticated: !!accessToken,
        isLoading,
        logout,
      }}
    >
      {/* Do not render app content until auth state is known, except on login page */}
      {isLoading && pathname !== "/login" ? (
        <div className="min-h-screen flex items-center justify-center bg-background">
          <div className="w-6 h-6 border-2 border-primary border-t-transparent rounded-full animate-spin" />
        </div>
      ) : (
        children
      )}
    </AuthContext.Provider>
  );
}

export const useAuth = () => useContext(AuthContext);
