"use client";

import { useCallback, useEffect, useRef } from "react";

import type { RemoteState } from "./api";

type EvidenceLoadStatus = RemoteState<unknown>["status"];

export function useEvidenceRetryFocus(status: EvidenceLoadStatus, reload: () => void) {
  const retryButtonRef = useRef<HTMLButtonElement>(null);
  const restoreFocusAfterRetry = useRef(false);

  const retry = useCallback(() => {
    restoreFocusAfterRetry.current = true;
    reload();
  }, [reload]);

  const setRetryButton = useCallback((button: HTMLButtonElement | null) => {
    retryButtonRef.current = button;
  }, []);

  useEffect(() => {
    if (!restoreFocusAfterRetry.current || status === "loading") return;

    restoreFocusAfterRetry.current = false;
    const target = retryButtonRef.current ?? document.getElementById("main-content");
    target?.focus({ preventScroll: true });
  }, [status]);

  return { retry, setRetryButton };
}
