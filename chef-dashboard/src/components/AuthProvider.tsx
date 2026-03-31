"use client";

import { createContext, useContext, useEffect, useState } from "react";
import { useRouter, usePathname } from "next/navigation";

interface AuthContextType {
  token: string | null;
  restaurantId: string | null;
  setAuth: (token: string, restaurantId: string) => void;
  logout: () => void;
  isAuthenticated: boolean;
  isLoading: boolean;
}

const AuthContext = createContext<AuthContextType>({
  token: null,
  restaurantId: null,
  setAuth: () => {},
  logout: () => {},
  isAuthenticated: false,
  isLoading: true,
});

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [token, setToken] = useState<string | null>(null);
  const [restaurantId, setRestaurantId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    // Basic in-memory hydration fallback (though JWT is stored in httpOnly cookies,
    // the chef dashboard needs the token specifically to send in the initial WS payload).
    // In a production app, the WS endpoint would read the HttpOnly cookie itself.
    // For this prototype/demo based on the backend ws_manager code, the WS expects
    // the literal JWT token string in {"type": "auth", "token": "jwt"}. 
    const storedToken = localStorage.getItem("chef_tablz_token");
    const storedRestId = localStorage.getItem("chef_tablz_rest_id");

    if (storedToken && storedRestId) {
      setToken(storedToken);
      setRestaurantId(storedRestId);
    } else if (pathname !== "/login") {
      router.push("/login");
    }
    setIsLoading(false);
  }, [pathname, router]);

  const setAuth = (newToken: string, newRestId: string) => {
    setToken(newToken);
    setRestaurantId(newRestId);
    localStorage.setItem("chef_tablz_token", newToken);
    localStorage.setItem("chef_tablz_rest_id", newRestId);
  };

  const logout = () => {
    setToken(null);
    setRestaurantId(null);
    localStorage.removeItem("chef_tablz_token");
    localStorage.removeItem("chef_tablz_rest_id");
    router.push("/login");
  };

  return (
    <AuthContext.Provider value={{ token, restaurantId, setAuth, logout, isAuthenticated: !!token, isLoading }}>
      {isLoading ? (
        <div className="min-h-screen flex items-center justify-center bg-background">
          <div className="w-8 h-8 border-2 border-primary border-t-transparent rounded-full animate-spin" />
        </div>
      ) : (
        children
      )}
    </AuthContext.Provider>
  );
}

export const useAuth = () => useContext(AuthContext);
