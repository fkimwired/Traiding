"use client";

import { useEffect, useState } from "react";

import { fable5Api } from "../lib/api";

type ConnectionState = "checking" | "online" | "offline";

export function ApiStatus() {
  const [connectionState, setConnectionState] = useState<ConnectionState>("checking");

  useEffect(() => {
    const controller = new AbortController();

    async function checkHealth() {
      const result = await fable5Api.getHealth(controller.signal);
      if (!result.ok) {
        if (result.error.kind !== "aborted") {
          setConnectionState("offline");
        }
        return;
      }

      setConnectionState(result.data.status === "ok" ? "online" : "offline");
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
