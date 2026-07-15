import { Suspense } from "react";

import { LineageExplorer } from "./LineageExplorer";

export default function LineagePage() {
  return (
    <div className="pageShell narrowPage">
      <header className="workspaceHeader">
        <div>
          <p className="eyebrow">Shared evidence route</p>
          <h1>Lineage</h1>
        </div>
        <p>
          Follow immutable identifiers from the source claim through the last real persisted
          artifact. Missing later evidence remains a fail-closed terminal state.
        </p>
      </header>
      <Suspense
        fallback={
          <p className="statePanel" role="status" aria-live="polite">
            Loading lineage selection...
          </p>
        }
      >
        <LineageExplorer />
      </Suspense>
    </div>
  );
}
