import { ResearchWorkspace } from "./ResearchWorkspace";

export default function ResearchLabPage() {
  return (
    <div className="pageShell narrowPage">
      <header className="workspaceHeader">
        <div>
          <p className="eyebrow">Mode 02</p>
          <h1>Research Lab</h1>
        </div>
        <p>
          Run only the persisted deterministic mock workflow. Leakage, selection diagnostics,
          cost stress, and missing evidence remain authoritative blockers.
        </p>
      </header>
      <ResearchWorkspace />
    </div>
  );
}
