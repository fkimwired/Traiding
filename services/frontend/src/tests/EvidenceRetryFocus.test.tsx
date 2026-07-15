import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useCallback, useState } from "react";
import { describe, expect, it } from "vitest";

import { useEvidenceRetryFocus } from "../lib/use-evidence-retry-focus";

type TerminalStatus = "error" | "success";

function deferred() {
  let resolve = () => {};
  const promise = new Promise<void>((complete) => {
    resolve = complete;
  });
  return { promise, resolve };
}

function RetryHarness({
  completion,
  terminalStatus,
}: Readonly<{ completion: Promise<void>; terminalStatus: TerminalStatus }>) {
  const [status, setStatus] = useState<"error" | "loading" | "success">("error");
  const reload = useCallback(() => {
    setStatus("loading");
    void completion.then(() => setStatus(terminalStatus));
  }, [completion, terminalStatus]);
  const { retry, setRetryButton } = useEvidenceRetryFocus(status, reload);

  return (
    <main id="main-content" tabIndex={-1}>
      {status === "loading" ? <p role="status">Loading immutable evidence...</p> : null}
      {status === "error" ? (
        <div role="alert">
          <button onClick={retry} ref={setRetryButton} type="button">
            Retry evidence load
          </button>
        </div>
      ) : null}
      {status === "success" ? <p>Evidence loaded.</p> : null}
    </main>
  );
}

describe("useEvidenceRetryFocus", () => {
  it("restores focus to a re-rendered retry control after another retry-safe failure", async () => {
    const request = deferred();
    const user = userEvent.setup();
    render(<RetryHarness completion={request.promise} terminalStatus="error" />);

    const retry = screen.getByRole("button", { name: "Retry evidence load" });
    retry.focus();
    await user.keyboard("{Enter}");
    expect(screen.getByRole("status")).toHaveTextContent("Loading immutable evidence");

    request.resolve();
    const restoredRetry = await screen.findByRole("button", { name: "Retry evidence load" });
    await waitFor(() => expect(restoredRetry).toHaveFocus());
  });

  it("moves focus to the main landmark when a successful retry removes the control", async () => {
    const request = deferred();
    const user = userEvent.setup();
    render(<RetryHarness completion={request.promise} terminalStatus="success" />);

    const retry = screen.getByRole("button", { name: "Retry evidence load" });
    retry.focus();
    await user.keyboard("{Enter}");
    request.resolve();

    await screen.findByText("Evidence loaded.");
    await waitFor(() => expect(screen.getByRole("main")).toHaveFocus());
  });
});
