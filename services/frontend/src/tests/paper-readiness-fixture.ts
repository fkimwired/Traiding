import type { SuccessfulJsonResponseByOperation } from "@fable5/contracts";

export type PaperReadinessArtifact =
  SuccessfulJsonResponseByOperation[
    "GET /v1/paper-shadow-readiness/{readiness_assessment_id}"
  ];

export const PAPER_READINESS_ASSESSMENT_ID =
  "83c60e08-f3cc-5569-9410-20e88993056d";

export const PAPER_READINESS_CHECK_CODES = [
  "SOURCE_KIND_EXACT",
  "READ_ONLY_TRANSPORT_EXACT",
  "ACCOUNT_READY",
  "MARKET_CLOCK_OPEN",
  "INSTRUMENT_ACTIVE_TRADABLE",
  "POSITIONS_EMPTY",
  "OPEN_ORDERS_EMPTY",
  "IEX_QUOTE_FRESH_VALID",
] as const satisfies readonly PaperReadinessArtifact["checks"][number]["code"][];

/** Exact deterministic mock output from the accepted Phase 12 workflow contract. */
export const paperReadinessFixture = {
  account: {
    account_blocked: false,
    observation_sha256:
      "bbe2ac03f7a2fd2ae2e4255c2c1fde8f83dc37326d9daa711242fdc40753b1b8",
    schema_version: "phase12-paper-account-observation-v1",
    status: "ACTIVE",
    trade_suspended_by_user: false,
    trading_blocked: false,
  },
  artifact_schema_version: "phase12-paper-shadow-readiness-v1",
  artifact_sha256:
    "78dc6679bf3bdda4e473311dd4652341e36ee68db10143db04ec1592e036698e",
  assessment_completed_at_utc: "2024-01-02T15:00:00.061000Z",
  assessment_started_at_utc: "2024-01-02T15:00:00.010000Z",
  checks: [
    {
      check_sha256:
        "433c742863d3f7a60650a122bbe3da74546f5cabf3c372bbc814e057cafa3620",
      code: "SOURCE_KIND_EXACT",
      evidence_sha256s: [
        "52fb1df27cc0d43a0e725f37e80a3030bb18ad18fca8327cdb181131324ddd08",
      ],
      observed_value: "DETERMINISTIC_MOCK",
      ordinal: 1,
      reason_code: "source_kind_explicit",
      schema_version: "phase12-paper-shadow-readiness-check-v1",
      status: "PASS",
      threshold_value: "DETERMINISTIC_MOCK|ALPACA_PAPER_READ_ONLY",
    },
    {
      check_sha256:
        "df2c0466ce56445993cb8a13ec30b40587ba2cd5f49aac8b939ddc4f0506367e",
      code: "READ_ONLY_TRANSPORT_EXACT",
      evidence_sha256s: [
        "0abdef0f61353960485a354cb00bebd137e387e857202f020a2caec25cb5926c",
      ],
      observed_value:
        "0abdef0f61353960485a354cb00bebd137e387e857202f020a2caec25cb5926c",
      ordinal: 2,
      reason_code: "read_only_transport_exact",
      schema_version: "phase12-paper-shadow-readiness-check-v1",
      status: "PASS",
      threshold_value:
        "0abdef0f61353960485a354cb00bebd137e387e857202f020a2caec25cb5926c",
    },
    {
      check_sha256:
        "f74b7069c3f91a84edd2d3d4a804a1758c8dd22cd12f74be6b61ea6272b1792e",
      code: "ACCOUNT_READY",
      evidence_sha256s: [
        "6ae1550b9346af29c36009837613fa872a674d2e0b8b738e31548535c927e2b3",
        "bbe2ac03f7a2fd2ae2e4255c2c1fde8f83dc37326d9daa711242fdc40753b1b8",
      ],
      observed_value: "status=ACTIVE;blocked=False",
      ordinal: 3,
      reason_code: "account_ready",
      schema_version: "phase12-paper-shadow-readiness-check-v1",
      status: "PASS",
      threshold_value: "status=ACTIVE;blocked=false",
    },
    {
      check_sha256:
        "26b77c06336b215f882294a290dde287704803ca69cde6f1894249a1bc4f5cdb",
      code: "MARKET_CLOCK_OPEN",
      evidence_sha256s: [
        "54ac9ffe0625551bf35765c4a597835fb7686aa21a84d7fe2a33ff893e33014c",
        "b1c9fb4bbf493c616770bdc8fb951c8e8f99640719d433393c51cc0c691516f1",
      ],
      observed_value: "true",
      ordinal: 4,
      reason_code: "market_clock_open",
      schema_version: "phase12-paper-shadow-readiness-check-v1",
      status: "PASS",
      threshold_value: "true",
    },
    {
      check_sha256:
        "c20d6b1d229135ac76d250ca36d849d101d13925373cbdedd5a1649ddaa7dfa4",
      code: "INSTRUMENT_ACTIVE_TRADABLE",
      evidence_sha256s: [
        "8b7732dac32ab1abb568c5c45bc123f9a4b59ed909f4af4787c75f0ae21b6f0e",
        "b8ed2949481db9d13f671d9ac04f2088af048488a051715578588caa53907934",
      ],
      observed_value: "active=True;tradable=True",
      ordinal: 5,
      reason_code: "instrument_active_tradable",
      schema_version: "phase12-paper-shadow-readiness-check-v1",
      status: "PASS",
      threshold_value: "active=true;tradable=true",
    },
    {
      check_sha256:
        "1db9bb1873156f3baa1044987bfff8947f7ff017a0af88cc94a69dd825289cff",
      code: "POSITIONS_EMPTY",
      evidence_sha256s: [
        "0498b530825e002648a133a497d501e1f96599dca32425dc168a3e56f169e2f5",
        "592d132585bc69cc78f8a58cb9f48fbae49bfc336636706c7dad4ac9a03c87aa",
      ],
      observed_value: "0",
      ordinal: 6,
      reason_code: "positions_empty",
      schema_version: "phase12-paper-shadow-readiness-check-v1",
      status: "PASS",
      threshold_value: "0",
    },
    {
      check_sha256:
        "460e51a0282e5db2a7b225067035a620ced6e3d6c4446fbd78bdbcff5db08c3c",
      code: "OPEN_ORDERS_EMPTY",
      evidence_sha256s: [
        "0dcd6434d7af301af9c59775e43ddf31ff29c2872a3a05a45f686a581df1500d",
        "cd4249334080e6664c644012ae0f0271640fe3180639aea4ec372dd6130daa9b",
      ],
      observed_value: "0",
      ordinal: 7,
      reason_code: "open_orders_empty",
      schema_version: "phase12-paper-shadow-readiness-check-v1",
      status: "PASS",
      threshold_value: "0",
    },
    {
      check_sha256:
        "58d216aafc9360797e35c1cabb940a861a472321312ba139ab6186bc5734f00b",
      code: "IEX_QUOTE_FRESH_VALID",
      evidence_sha256s: [
        "bbfab3ac2c47e35b86f86a9751646b09fe5e0bf1de94feb29a8f341f3fddc080",
        "fb2c3f6a6b545efc9391eac0efd5ae4fbb42d2590f3582cc56b787f47bdcaa46",
      ],
      observed_value: "fresh=True;valid=True",
      ordinal: 8,
      reason_code: "iex_quote_fresh_valid",
      schema_version: "phase12-paper-shadow-readiness-check-v1",
      status: "PASS",
      threshold_value: "feed=iex;fresh=true;valid=true",
    },
  ],
  clock: {
    is_open: true,
    next_close_utc: "2024-01-02T21:00:00Z",
    next_open_utc: "2024-01-03T08:30:00Z",
    observation_sha256:
      "b1c9fb4bbf493c616770bdc8fb951c8e8f99640719d433393c51cc0c691516f1",
    provider_timestamp_utc: "2024-01-02T15:00:00Z",
    schema_version: "phase12-paper-clock-observation-v1",
  },
  disclaimer:
    "PAPER ONLY shadow-readiness evidence; no order submission, strategy execution, real performance claim, or personalized investment advice.",
  expires_at_utc: "2024-01-02T15:01:00.061000Z",
  inspections: [
    {
      code: "ACCOUNT",
      external_request_performed: false,
      failure_reason: null,
      http_status: null,
      inspection_sha256:
        "6ae1550b9346af29c36009837613fa872a674d2e0b8b738e31548535c927e2b3",
      method: "GET",
      observation_sha256:
        "bbe2ac03f7a2fd2ae2e4255c2c1fde8f83dc37326d9daa711242fdc40753b1b8",
      ordinal: 1,
      request_completed_at_utc: "2024-01-02T15:00:00.011000Z",
      request_id: null,
      request_started_at_utc: "2024-01-02T15:00:00.010000Z",
      response_sha256: null,
      schema_version: "phase12-paper-shadow-inspection-v1",
      status: "OBSERVED",
    },
    {
      code: "CLOCK",
      external_request_performed: false,
      failure_reason: null,
      http_status: null,
      inspection_sha256:
        "54ac9ffe0625551bf35765c4a597835fb7686aa21a84d7fe2a33ff893e33014c",
      method: "GET",
      observation_sha256:
        "b1c9fb4bbf493c616770bdc8fb951c8e8f99640719d433393c51cc0c691516f1",
      ordinal: 2,
      request_completed_at_utc: "2024-01-02T15:00:00.021000Z",
      request_id: null,
      request_started_at_utc: "2024-01-02T15:00:00.020000Z",
      response_sha256: null,
      schema_version: "phase12-paper-shadow-inspection-v1",
      status: "OBSERVED",
    },
    {
      code: "INSTRUMENT",
      external_request_performed: false,
      failure_reason: null,
      http_status: null,
      inspection_sha256:
        "8b7732dac32ab1abb568c5c45bc123f9a4b59ed909f4af4787c75f0ae21b6f0e",
      method: "GET",
      observation_sha256:
        "b8ed2949481db9d13f671d9ac04f2088af048488a051715578588caa53907934",
      ordinal: 3,
      request_completed_at_utc: "2024-01-02T15:00:00.031000Z",
      request_id: null,
      request_started_at_utc: "2024-01-02T15:00:00.030000Z",
      response_sha256: null,
      schema_version: "phase12-paper-shadow-inspection-v1",
      status: "OBSERVED",
    },
    {
      code: "POSITIONS",
      external_request_performed: false,
      failure_reason: null,
      http_status: null,
      inspection_sha256:
        "0498b530825e002648a133a497d501e1f96599dca32425dc168a3e56f169e2f5",
      method: "GET",
      observation_sha256:
        "592d132585bc69cc78f8a58cb9f48fbae49bfc336636706c7dad4ac9a03c87aa",
      ordinal: 4,
      request_completed_at_utc: "2024-01-02T15:00:00.041000Z",
      request_id: null,
      request_started_at_utc: "2024-01-02T15:00:00.040000Z",
      response_sha256: null,
      schema_version: "phase12-paper-shadow-inspection-v1",
      status: "OBSERVED",
    },
    {
      code: "OPEN_ORDERS",
      external_request_performed: false,
      failure_reason: null,
      http_status: null,
      inspection_sha256:
        "0dcd6434d7af301af9c59775e43ddf31ff29c2872a3a05a45f686a581df1500d",
      method: "GET",
      observation_sha256:
        "cd4249334080e6664c644012ae0f0271640fe3180639aea4ec372dd6130daa9b",
      ordinal: 5,
      request_completed_at_utc: "2024-01-02T15:00:00.051000Z",
      request_id: null,
      request_started_at_utc: "2024-01-02T15:00:00.050000Z",
      response_sha256: null,
      schema_version: "phase12-paper-shadow-inspection-v1",
      status: "OBSERVED",
    },
    {
      code: "LATEST_QUOTE",
      external_request_performed: false,
      failure_reason: null,
      http_status: null,
      inspection_sha256:
        "bbfab3ac2c47e35b86f86a9751646b09fe5e0bf1de94feb29a8f341f3fddc080",
      method: "GET",
      observation_sha256:
        "fb2c3f6a6b545efc9391eac0efd5ae4fbb42d2590f3582cc56b787f47bdcaa46",
      ordinal: 6,
      request_completed_at_utc: "2024-01-02T15:00:00.061000Z",
      request_id: null,
      request_started_at_utc: "2024-01-02T15:00:00.060000Z",
      response_sha256: null,
      schema_version: "phase12-paper-shadow-inspection-v1",
      status: "OBSERVED",
    },
  ],
  instrument: {
    active: true,
    asset_id: "b0b6dd9d-8b9b-52ba-a39b-36bd3d5b2024",
    exchange: "NASDAQ",
    observation_sha256:
      "b8ed2949481db9d13f671d9ac04f2088af048488a051715578588caa53907934",
    schema_version: "phase12-paper-instrument-observation-v1",
    status: "active",
    symbol: "AAPL",
    tradable: true,
  },
  latest_quote: {
    age_seconds: "1.0",
    ask_price_valid: true,
    bid_price_valid: true,
    event_time_utc: "2024-01-02T14:59:59Z",
    feed: "iex",
    fresh: true,
    freshness_ttl_seconds: 60,
    non_crossed: true,
    observation_sha256:
      "fb2c3f6a6b545efc9391eac0efd5ae4fbb42d2590f3582cc56b787f47bdcaa46",
    received_at_utc: "2024-01-02T15:00:00Z",
    schema_version: "phase12-paper-quote-observation-v1",
    symbol: "AAPL",
  },
  live_path_absent: true,
  no_personalized_investment_advice: true,
  no_real_performance_claimed: true,
  open_orders: {
    inventory_kind: "OPEN_ORDERS",
    inventory_sha256:
      "ed4dcaf2c4cf7388117c1c41f3b8f73e336de0adc574a36e73693bc96cf821bd",
    item_count: 0,
    observation_sha256:
      "cd4249334080e6664c644012ae0f0271640fe3180639aea4ec372dd6130daa9b",
    schema_version: "phase12-paper-inventory-observation-v1",
  },
  order_submission_authorized: false,
  outcome: "MOCK_PROOF_COMPLETE",
  phase12_code_version_git_sha: "4d70b823947fd61d0ea17df14c9f1ff9f93fd45b",
  positions: {
    inventory_kind: "POSITIONS",
    inventory_sha256:
      "4341111af2a8527bf3de910898fd7df327742ea6a124df80c26d6fcb48b22643",
    item_count: 0,
    observation_sha256:
      "592d132585bc69cc78f8a58cb9f48fbae49bfc336636706c7dad4ac9a03c87aa",
    schema_version: "phase12-paper-inventory-observation-v1",
  },
  readiness_assessment_id: PAPER_READINESS_ASSESSMENT_ID,
  readiness_idempotency_key: "phase12-t002-mock-evidence",
  reason_codes: ["all_mock_readiness_checks_passed"],
  request_fingerprint_sha256:
    "8d0bd374384c7603ac6308ad73051dd6fbae82f9126c93b3937c382ac88a4b9a",
  source_kind: "DETERMINISTIC_MOCK",
  strategy_execution_eligible: false,
  transport_profile_sha256:
    "0abdef0f61353960485a354cb00bebd137e387e857202f020a2caec25cb5926c",
} satisfies PaperReadinessArtifact;

export function paperReadinessArtifact(
  overrides: Partial<PaperReadinessArtifact> = {},
): PaperReadinessArtifact {
  return { ...paperReadinessFixture, ...overrides };
}

export const blockedPaperReadinessFixture: PaperReadinessArtifact = {
  ...paperReadinessFixture,
  artifact_sha256:
    "9999999999999999999999999999999999999999999999999999999999999999",
  checks: paperReadinessFixture.checks.map(
    (check): PaperReadinessArtifact["checks"][number] =>
      check.code === "MARKET_CLOCK_OPEN"
        ? {
            ...check,
            check_sha256:
              "8888888888888888888888888888888888888888888888888888888888888888",
            observed_value: "false",
            reason_code: "market_clock_closed_verbatim",
            status: "BLOCKED",
          }
        : check,
  ),
  outcome: "BLOCKED",
  reason_codes: ["market_clock_closed_verbatim", "quote_freshness_blocked_verbatim"],
};
