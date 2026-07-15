import Link from "next/link";

import { ApiStatus } from "../components/ApiStatus";
import { navigationItems } from "../lib/navigation";

const modes = [
  {
    kicker: "Preserve the claim",
    description:
      "Capture exact source text, ambiguity, extraction state, and the normalized card without turning prose into advice.",
  },
  {
    kicker: "Let blockers lead",
    description:
      "Inspect trials, leakage, selection diagnostics, costs, and lineage. A failed gate outranks every positive metric.",
  },
  {
    kicker: "Historical status only",
    description:
      "Review immutable synthetic approval evidence and revocations. Nothing on this surface can create executable intent.",
  },
  {
    kicker: "Reconstruct the decision",
    description:
      "Read all ordered checks, currentness evidence, reason codes, and append-only governance artifacts.",
  },
] as const;

export default function HomePage() {
  return (
    <div className="pageShell phase8Home">
      <section className="phase8Hero" aria-labelledby="home-title">
        <div className="phase8HeroCopy">
          <p className="eyebrow">Evidence before simulation</p>
          <h1 id="home-title">
            Make the <em>no</em> visible.
          </h1>
          <p>
            Fable5 turns a source claim into an inspectable chain of synthetic evidence. It keeps
            missing data, fragile costs, overfitting, and governance failures in the foreground.
          </p>
          <div className="heroActions">
            <Link className="primaryAction" href="/ideas">
              Start with a source <span aria-hidden="true">→</span>
            </Link>
            <Link className="textAction" href="/research">
              Review research evidence
            </Link>
          </div>
        </div>

        <aside className="heroLedger" aria-label="Platform evidence posture">
          <div className="ledgerHeader">
            <span>System posture</span>
            <ApiStatus />
          </div>
          <dl>
            <div>
              <dt>Data</dt>
              <dd>Synthetic, point-in-time QA</dd>
            </div>
            <div>
              <dt>Research</dt>
              <dd>Gate-first and selection-aware</dd>
            </div>
            <div>
              <dt>Paper status</dt>
              <dd>Historical, simulated, non-executable</dd>
            </div>
            <div>
              <dt>Live path</dt>
              <dd>Absent by design</dd>
            </div>
          </dl>
        </aside>
      </section>

      <section className="workflowIntro" aria-labelledby="workflow-title">
        <div>
          <p className="eyebrow">Four linked workspaces</p>
          <h2 id="workflow-title">One chain of evidence.</h2>
        </div>
        <p>
          Every visible result links to its complete source-to-governance lineage. Server artifacts
          own the facts; this interface only makes them legible.
        </p>
      </section>

      <section className="phase8ModeGrid" aria-label="Platform modes">
        {navigationItems.map((item, index) => (
          <article className="phase8ModeCard" key={item.href}>
            <span className="modeIndex">0{index + 1}</span>
            <p className="modeKicker">{modes[index].kicker}</p>
            <h2>{item.label}</h2>
            <p>{modes[index].description}</p>
            <Link href={item.href}>
              Open workspace <span aria-hidden="true">↗</span>
            </Link>
          </article>
        ))}
      </section>

      <section className="blockerManifesto" aria-labelledby="blocker-title">
        <span className="blockerMark" aria-hidden="true">
          !
        </span>
        <div>
          <p className="eyebrow">Presentation rule 01</p>
          <h2 id="blocker-title">A blocker is the headline.</h2>
        </div>
        <p>
          Leakage, failed cost stress, high PBO, stale evidence, revocation, or an uncomputable
          check remains visually dominant. Positive statistics never soften an ineligible state.
        </p>
      </section>
    </div>
  );
}
