import { useAuth } from "@/components/AuthProvider";
import { useCallback } from "react";

const BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

export function useApi() {
  const { accessToken, logout } = useAuth();

  const fetchWithAuth = useCallback(
    async (endpoint: string, options: RequestInit = {}) => {
      const headers = new Headers(options.headers);
      headers.set("Content-Type", "application/json");

      if (accessToken) {
        headers.set("Authorization", `Bearer ${accessToken}`);
      }

      const res = await fetch(`${BASE_URL}${endpoint}`, {
        ...options,
        headers,
      });

      if (res.status === 401) {
        // Token expired and refresh failed bounds handled in AuthProvider,
        // but if an arbitrary request fails with 401, force logout.
        logout();
        throw new Error("Unauthorized");
      }

      return res;
    },
    [accessToken, logout]
  );

  return { fetchWithAuth };
}
