"use client";

import { useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useApi } from "@/lib/api";

export default function ScanPage() {
  const searchParams = useSearchParams();
  const tableNumber = searchParams.get("table_number");
  const router = useRouter();
  const { fetchClient } = useApi();
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const errorParam = searchParams.get("error");
    if (errorParam === "no-session") {
      setError("Please scan the QR code on your table to view the menu.");
      return;
    }

    if (!tableNumber) {
      setError("Invalid or missing Table ID in the QR code.");
      return;
    }

    const initSession = async () => {
      try {
        const res = await fetchClient("/sessions/create", {
          method: "POST",
          body: JSON.stringify({ table_number: parseInt(tableNumber) })
        });

        if (res.ok) {
          // The backend sets the HttpOnly cookie for the session!
          // Redirect to menu automatically
          setTimeout(() => router.push("/menu"), 1500);
        } else {
          const data = await res.json();
          setError(data.error?.message || "Failed to establish secure session to table.");
        }
      } catch (err) {
        console.error(err);
        setError("Network error establishing session.");
      }
    };

    initSession();
  }, [tableNumber, searchParams, fetchClient, router]);

  return (
    <div className="min-h-screen flex flex-col items-center justify-center bg-background p-6">
      <div className="glass-card p-10 max-w-sm w-full text-center space-y-6">
        <h1 className="font-display italic text-primary text-4xl">TABLZ.</h1>
        
        {error ? (
          <div className="text-status-cleaning text-sm p-4 bg-status-cleaning/10 rounded-xl">
            {error}
          </div>
        ) : (
          <div className="space-y-4">
            <div className="flex justify-center">
               <div className="w-8 h-8 border-2 border-primary border-t-transparent rounded-full animate-spin" />
            </div>
            <p className="font-sans text-on-surface-variant text-sm">
              Establishing secure connection to Table {tableNumber}...
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
