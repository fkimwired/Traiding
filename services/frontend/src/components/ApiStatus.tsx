"use client";

import type { components } from "@fable5/contracts";
import { useEffect, useState } from "react";

type HealthResponse = components["schemas"]["HealthResponse"];
type ConnectionState = "checking" | "online" | "offline";

const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export function ApiStatus() {
  const [connectionState, setConnectionState] = useState<ConnectionState>("checking");

  useEffect(() => {
    const controller = new AbortController();

    async function checkHealth() {
      try {
        const response = await fetch(`${apiUrl}/health`, { signal: controller.signal });
        if (!response.ok) {
          throw new Error("Health endpoint returned a non-success status.");
        }
        const body = (await response.json()) as HealthResponse;
        setConnectionState(body.status === "ok" ? "online" : "offline");
      } catch (error) {
        if ((error as Error).name !== "AbortError") {
          setConnectionState("offline");
        }
      }
    }

    void checkHealth();
    return () => controller.abort();
  }, []);

  return (
    <span className={`apiStatus apiStatus-${connectionState}`} aria-live="polite">
      API {connectionState}
    </span>
  );
}

