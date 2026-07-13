import { IdeaMappings } from "./IdeaMappings";

export default function IdeaIntakePage() {
  return (
    <div className="pageShell narrowPage">
      <p className="eyebrow">Mode 01</p>
      <h1>Idea Intake</h1>
      <div className="phasePlaceholder">
        <span>Phase 2 evidence boundary</span>
        <h2>Source first. Interpretation second.</h2>
        <p>
          The source API preserves exact text, ambiguity, versions, and provenance before producing
          an extraction-only research card. An interactive intake workflow remains a later UI task;
          this surface provides no strategy, recommendation, or order control.
        </p>
      </div>
      <IdeaMappings />
    </div>
  );
}
