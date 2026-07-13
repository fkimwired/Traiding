"use client";

import type { components } from "@fable5/contracts";
import { useEffect, useState } from "react";

type MappingWithRationale = components["schemas"]["MappingWithRationale"];

type MappingState =
  | { status: "loading" }
  | { status: "loaded"; mappings: MappingWithRationale[] }
  | { status: "error" };

const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export function IdeaMappings() {
  const [state, setState] = useState<MappingState>({ status: "loading" });

  useEffect(() => {
    const controller = new AbortController();

    async function loadMappings() {
      try {
        const response = await fetch(`${apiUrl}/v1/mappings`, { signal: controller.signal });
        if (!response.ok) {
          throw new Error("Mapping endpoint returned a non-success status.");
        }

        const mappings = (await response.json()) as MappingWithRationale[];
        setState({ status: "loaded", mappings });
      } catch (error) {
        if ((error as Error).name !== "AbortError") {
          setState({ status: "error" });
        }
      }
    }

    void loadMappings();
    return () => controller.abort();
  }, []);

  return (
    <section className="mappingSection" aria-labelledby="mapping-heading">
      <div className="mappingBoundary">
        <p className="eyebrow">Phase 3 research boundary</p>
        <h2 id="mapping-heading">Deterministic canon mappings</h2>
        <p>
          <strong>BUILD_RESEARCH</strong> authorizes only a later research specification. It does not
          indicate profitability, approval, advice, a signal, a recommendation, position sizing, or
          paper-trading eligibility.
        </p>
      </div>

      {state.status === "loading" ? (
        <p className="mappingState" role="status">
          Loading deterministic mappings…
        </p>
      ) : null}

      {state.status === "error" ? (
        <p className="mappingState mappingStateError" role="alert">
          Deterministic mappings could not be loaded. No research state was changed.
        </p>
      ) : null}

      {state.status === "loaded" && state.mappings.length === 0 ? (
        <p className="mappingState">No deterministic mappings are available yet.</p>
      ) : null}

      {state.status === "loaded" && state.mappings.length > 0 ? (
        <div className="mappingList">
          {state.mappings.map(({ mapping, rationale }) => (
            <article className="mappingCard" key={mapping.mapping_id}>
              <header className="mappingHeader">
                <div>
                  <span>Canonical family</span>
                  <h3>{mapping.canonical_family ?? "UNRESOLVED"}</h3>
                </div>
                <code className="mappingVerdict">{mapping.verdict}</code>
              </header>

              <div className="mappingEvidence">
                <div>
                  <h4>Ordered reason codes</h4>
                  <ol aria-label="Ordered reason codes">
                    {mapping.reason_codes.length > 0 ? (
                      mapping.reason_codes.map((reason) => <li key={reason}>{reason}</li>)
                    ) : (
                      <li>None recorded</li>
                    )}
                  </ol>
                </div>
                <div>
                  <h4>Matched rule IDs</h4>
                  <ul aria-label="Matched rule IDs">
                    {mapping.matched_rule_ids.map((ruleId) => (
                      <li key={ruleId}>{ruleId}</li>
                    ))}
                  </ul>
                </div>
              </div>

              <div className="mappingRationale">
                <h4>Deterministic rationale</h4>
                <pre>{rationale.markdown}</pre>
              </div>

              <nav className="mappingLineage" aria-label={`Lineage for ${mapping.mapping_id}`}>
                <span>API lineage</span>
                <a href={`${apiUrl}/v1/sources/${mapping.source_id}`}>Source</a>
                <a href={`${apiUrl}/v1/source-versions/${mapping.source_version_id}`}>
                  Source version
                </a>
                <a href={`${apiUrl}/v1/cards/${mapping.card_id}`}>Card</a>
                <a href={`${apiUrl}/v1/extractions/${mapping.extraction_request_id}`}>
                  Extraction
                </a>
              </nav>
            </article>
          ))}
        </div>
      ) : null}
    </section>
  );
}
