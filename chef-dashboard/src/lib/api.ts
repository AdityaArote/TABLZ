export const BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

export function getWsUrl(restaurantId: string, token: string) {
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  // We expect BASE_URL to end in /api/v1 (e.g. localhost:8000/api/v1)
  const host = BASE_URL.replace(/^https?:\/\//, ""); // localhost:8000/api/v1
  return `${protocol}//${host}/ws/${restaurantId}?token=${token}`;
}
