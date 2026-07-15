import { IdeaIntakeWorkspace } from "./IdeaIntakeWorkspace";

export default function IdeaIntakePage() {
  return (
    <div className="pageShell narrowPage">
      <p className="eyebrow">Mode 01</p>
      <h1>Idea Intake</h1>
      <div className="phasePlaceholder">
        <span>Source first - server authority preserved</span>
        <h2>Exact text in. Auditable evidence out.</h2>
        <p>
          Source provenance and ambiguity remain visible from intake through extraction, mapping,
          deterministic mock research, and simulated governance status. This workflow produces no
          recommendation, allocation, or executable instruction.
        </p>
      </div>
      <IdeaIntakeWorkspace />
    </div>
  );
}
