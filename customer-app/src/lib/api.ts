import { useCallback } from "react";

const BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

export function useApi() {
  const fetchClient = useCallback(
    async (endpoint: string, options: RequestInit = {}) => {
      const headers = new Headers(options.headers);
      headers.set("Content-Type", "application/json");

      // We don't append a Bearer token.
      // Customer sessions use HttpOnly cookies that the browser attaches automatically.
      const res = await fetch(`${BASE_URL}${endpoint}`, {
        ...options,
        headers,
        credentials: "include", // VERY IMPORTANT for customer sessions
      });

      if (res.status === 401 || res.status === 403) {
        // Session dead, but let individual components handle redirect, 
        // as some endpoints might be semi-public (like viewing menu without session)
        console.warn("Session may be invalid");
      }

      return res;
    },
    []
  );

  return { fetchClient };
}
