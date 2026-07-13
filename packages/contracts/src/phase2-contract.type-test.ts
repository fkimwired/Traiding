import type { components } from "./api.generated";

type SourceInput = components["schemas"]["SourceIntakeRequest"];

const textInput: SourceInput = {
  source_type: "manual_notes",
  source_authority: "unknown",
  raw_text: "Exact supplied text.",
};

const urlOnlyInput: SourceInput = {
  source_type: "url_provenance",
  source_authority: "unknown",
  source_url: "https://example.invalid/url-only",
};

const explicitNullText: SourceInput = {
  source_type: "url_provenance",
  source_authority: "unknown",
  source_url: "https://example.invalid/url-only",
  // @ts-expect-error URL-only input omits raw_text; explicit null is not accepted.
  raw_text: null,
};

const clientSuppliedTimestamp: SourceInput = {
  source_type: "manual_notes",
  source_authority: "unknown",
  raw_text: "Exact supplied text.",
  // @ts-expect-error supplied_at_utc is server-owned and output-only.
  supplied_at_utc: "2026-07-13T20:00:00Z",
};

const assetClass: components["schemas"]["AssetClassEvidence"] = {
  state: "source_supported",
  value: "equity",
  claim_ids: ["segment-001"],
};

const forecastHorizon: components["schemas"]["ForecastHorizonEvidence"] = {
  state: "source_supported",
  value: "next_day",
  claim_ids: ["segment-001"],
};

const signalFamily: components["schemas"]["SignalFamilyEvidence"] = {
  state: "source_supported",
  value: "trend_or_pattern_claim",
  claim_ids: ["segment-001"],
};

const executionStyle: components["schemas"]["ExecutionStyleEvidence"] = {
  state: "source_supported",
  value: "periodic_research_claim",
  claim_ids: ["segment-001"],
};

const requiredData: components["schemas"]["RequiredDataEvidence"] = {
  state: "source_supported",
  values: ["point_in_time_universe"],
  claim_ids: ["segment-001"],
};

const riskAssumptions: components["schemas"]["RiskAssumptionsEvidence"] = {
  state: "source_supported",
  values: ["liquidity"],
  claim_ids: ["segment-001"],
};

const wrongAssetClass: components["schemas"]["AssetClassEvidence"] = {
  state: "source_supported",
  // @ts-expect-error horizon labels cannot populate asset-class evidence.
  value: "next_day",
  claim_ids: ["segment-001"],
};

const wrongForecastHorizon: components["schemas"]["ForecastHorizonEvidence"] = {
  state: "source_supported",
  // @ts-expect-error asset-class labels cannot populate horizon evidence.
  value: "equity",
  claim_ids: ["segment-001"],
};

const wrongSignalFamily: components["schemas"]["SignalFamilyEvidence"] = {
  state: "source_supported",
  // @ts-expect-error execution-style labels cannot populate signal-family evidence.
  value: "high_frequency_claim",
  claim_ids: ["segment-001"],
};

const wrongExecutionStyle: components["schemas"]["ExecutionStyleEvidence"] = {
  state: "source_supported",
  // @ts-expect-error signal-family labels cannot populate execution-style evidence.
  value: "trend_or_pattern_claim",
  claim_ids: ["segment-001"],
};

const wrongRequiredData: components["schemas"]["RequiredDataEvidence"] = {
  state: "source_supported",
  // @ts-expect-error risk-assumption labels cannot populate required-data evidence.
  values: ["liquidity"],
  claim_ids: ["segment-001"],
};

const wrongRiskAssumptions: components["schemas"]["RiskAssumptionsEvidence"] = {
  state: "source_supported",
  // @ts-expect-error required-data labels cannot populate risk-assumption evidence.
  values: ["ohlcv"],
  claim_ids: ["segment-001"],
};

void [
  textInput,
  urlOnlyInput,
  explicitNullText,
  clientSuppliedTimestamp,
  assetClass,
  forecastHorizon,
  signalFamily,
  executionStyle,
  requiredData,
  riskAssumptions,
  wrongAssetClass,
  wrongForecastHorizon,
  wrongSignalFamily,
  wrongExecutionStyle,
  wrongRequiredData,
  wrongRiskAssumptions,
];
