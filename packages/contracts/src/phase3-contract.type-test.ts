import type { components, paths } from "./api.generated";

type CanonicalFamily = components["schemas"]["CanonicalFamily"];
type ResearchVerdict = components["schemas"]["ResearchVerdict"];
type MappingReasonCode = components["schemas"]["MappingReasonCode"];
type MappingResponse = components["schemas"]["MappingWithRationale"];
type CreateMappingOperation = paths["/v1/cards/{card_id}/mappings"]["post"];

const family: CanonicalFamily = "A_CROSS_SECTIONAL_EQUITY_RANKING";
const verdict: ResearchVerdict = "BUILD_RESEARCH";
const reason: MappingReasonCode = "CANON_A_RULE_MATCHED";
const unresolvedFamily: CanonicalFamily | null = null;

// @ts-expect-error Phase 5 promotion states are not Phase 3 verdicts.
const laterPromotionState: ResearchVerdict = "PASS_RESEARCH";
// @ts-expect-error Priority prose is not a machine verdict.
const priorityProse: ResearchVerdict = "BUILD_FIRST";
// @ts-expect-error A fabricated family is outside the generated closed vocabulary.
const fabricatedFamily: CanonicalFamily = "SOCIAL_SENTIMENT_TRADING";
// @ts-expect-error Clients cannot invent a reason outside the generated vocabulary.
const fabricatedReason: MappingReasonCode = "LLM_RECOMMENDED";

type ExpectNever<Value extends never> = Value;
type CreateRequestPayload = Exclude<CreateMappingOperation["requestBody"], undefined>;
type CreateHasNoRequestPayload = ExpectNever<CreateRequestPayload>;

declare const response: MappingResponse;
const generatedVerdict: ResearchVerdict = response.mapping.verdict;
const generatedReasons: MappingReasonCode[] = response.mapping.reason_codes;

void [
  family,
  verdict,
  reason,
  unresolvedFamily,
  laterPromotionState,
  priorityProse,
  fabricatedFamily,
  fabricatedReason,
  generatedVerdict,
  generatedReasons,
];

export type { CreateHasNoRequestPayload };
