from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from uuid import UUID

import pytest
from fable5_paper.phase12.adapters import (
    DeterministicMockPaperBrokerAdapter,
    MockReadinessScenario,
    PaperBrokerAdapter,
    PaperBrokerInspection,
)
from fable5_paper.phase12.canonical import PHASE12_ARTIFACT_HASH_DOMAIN, domain_sha256
from fable5_paper.phase12.contracts import (
    PaperShadowReadinessArtifact,
    PaperShadowReadinessCreateRequest,
    ReadinessOutcome,
)
from fable5_paper.phase12.workflow import (
    PaperShadowReadinessCreation,
    PaperShadowReadinessWorkflow,
    PaperShadowReadinessWorkflowConflict,
)

CODE_SHA = "b8657abe34d3290a42cb92cb1ad751d0d9d73ad5"
KEY = "phase12-workflow-proof"


class InMemoryReadinessStore:
    def __init__(self) -> None:
        self.by_key: dict[str, PaperShadowReadinessArtifact] = {}
        self.by_id: dict[UUID, PaperShadowReadinessArtifact] = {}
        self.create_calls = 0

    @contextmanager
    def serialized_creation(self, key: str) -> Iterator[PaperShadowReadinessCreation]:
        del key
        yield self

    def find_by_idempotency_key(self, key: str) -> PaperShadowReadinessArtifact | None:
        return self.by_key.get(key)

    def create_readiness(
        self, artifact: PaperShadowReadinessArtifact
    ) -> PaperShadowReadinessArtifact:
        self.create_calls += 1
        self.by_key[artifact.readiness_idempotency_key] = artifact
        self.by_id[artifact.readiness_assessment_id] = artifact
        return artifact

    def get_readiness(self, readiness_assessment_id: UUID) -> PaperShadowReadinessArtifact:
        return self.by_id[readiness_assessment_id]


def build_mock_artifact(
    scenario: MockReadinessScenario = MockReadinessScenario.READY,
    *,
    key: str = KEY,
) -> PaperShadowReadinessArtifact:
    return PaperShadowReadinessWorkflow(
        adapter=DeterministicMockPaperBrokerAdapter(scenario),
        store=InMemoryReadinessStore(),
        phase12_code_version_git_sha=CODE_SHA,
    ).create_readiness(PaperShadowReadinessCreateRequest(readiness_idempotency_key=key))


def test_mock_artifact_is_deterministic_complete_and_never_external_authority() -> None:
    first = build_mock_artifact()
    second = build_mock_artifact()

    assert first == second
    assert first.model_dump_json() == second.model_dump_json()
    assert first.outcome is ReadinessOutcome.MOCK_PROOF_COMPLETE
    assert first.reason_codes == ("all_mock_readiness_checks_passed",)
    assert len(first.inspections) == 6
    assert len(first.checks) == 8
    assert all(item.status == "PASS" for item in first.checks)
    assert first.order_submission_authorized is False
    assert first.strategy_execution_eligible is False
    assert first.live_path_absent is True
    assert first.no_personalized_investment_advice is True
    assert first.no_real_performance_claimed is True
    assert (first.expires_at_utc - first.assessment_completed_at_utc).total_seconds() == 60


@pytest.mark.parametrize(
    ("scenario", "reason"),
    (
        (MockReadinessScenario.ACCOUNT_BLOCKED, "account_not_ready"),
        (MockReadinessScenario.CLOCK_CLOSED, "market_clock_closed"),
        (MockReadinessScenario.INSTRUMENT_INACTIVE, "instrument_not_active_tradable"),
        (MockReadinessScenario.POSITIONS_NONEMPTY, "positions_not_empty"),
        (MockReadinessScenario.OPEN_ORDERS_NONEMPTY, "open_orders_not_empty"),
        (MockReadinessScenario.QUOTE_STALE, "iex_quote_stale_or_invalid"),
    ),
)
def test_each_mock_defect_produces_one_deterministic_blocked_artifact(
    scenario: MockReadinessScenario,
    reason: str,
) -> None:
    artifact = build_mock_artifact(scenario, key=f"phase12-{scenario.value.lower()}")

    assert artifact.outcome is ReadinessOutcome.BLOCKED
    assert artifact.reason_codes == (reason,)
    assert (
        artifact.model_dump_json()
        == build_mock_artifact(scenario, key=f"phase12-{scenario.value.lower()}").model_dump_json()
    )


class CountingAdapter:
    def __init__(self) -> None:
        self.delegate = DeterministicMockPaperBrokerAdapter()
        self.calls: list[str] = []

    @property
    def source_kind(self):  # type: ignore[no-untyped-def]
        return self.delegate.source_kind

    @property
    def transport_profile_sha256(self) -> str:
        return self.delegate.transport_profile_sha256

    def _call(self, name: str) -> PaperBrokerInspection:
        self.calls.append(name)
        return getattr(self.delegate, name)()  # type: ignore[no-any-return]

    def inspect_account(self) -> PaperBrokerInspection:
        return self._call("inspect_account")

    def inspect_clock(self) -> PaperBrokerInspection:
        return self._call("inspect_clock")

    def inspect_instrument(self) -> PaperBrokerInspection:
        return self._call("inspect_instrument")

    def inspect_positions(self) -> PaperBrokerInspection:
        return self._call("inspect_positions")

    def inspect_open_orders(self) -> PaperBrokerInspection:
        return self._call("inspect_open_orders")

    def inspect_latest_quote(self) -> PaperBrokerInspection:
        return self._call("inspect_latest_quote")


def test_same_key_is_single_flight_and_conflicting_fingerprint_fails_before_adapter() -> None:
    store = InMemoryReadinessStore()
    adapter = CountingAdapter()
    request = PaperShadowReadinessCreateRequest(readiness_idempotency_key=KEY)
    workflow = PaperShadowReadinessWorkflow(
        adapter=adapter,
        store=store,
        phase12_code_version_git_sha=CODE_SHA,
    )

    first = workflow.create_readiness(request)
    second = workflow.create_readiness(request)

    assert second is first
    assert store.create_calls == 1
    assert adapter.calls == [
        "inspect_account",
        "inspect_clock",
        "inspect_instrument",
        "inspect_positions",
        "inspect_open_orders",
        "inspect_latest_quote",
    ]

    conflicting_adapter = CountingAdapter()
    conflicting = PaperShadowReadinessWorkflow(
        adapter=conflicting_adapter,
        store=store,
        phase12_code_version_git_sha="1" * 40,
    )
    with pytest.raises(PaperShadowReadinessWorkflowConflict, match="different fingerprint"):
        conflicting.create_readiness(request)
    assert conflicting_adapter.calls == []


def test_mock_cannot_be_reclassified_as_shadow_ready_even_with_rehashed_payload() -> None:
    artifact = build_mock_artifact()
    tampered = artifact.model_dump(mode="python")
    tampered["outcome"] = "SHADOW_READY"
    tampered["reason_codes"] = ("all_external_shadow_readiness_checks_passed",)
    payload = {
        key: value
        for key, value in tampered.items()
        if key not in {"readiness_assessment_id", "artifact_sha256"}
    }
    tampered["artifact_sha256"] = domain_sha256(PHASE12_ARTIFACT_HASH_DOMAIN, payload)

    with pytest.raises(ValueError, match="outcome and reasons"):
        PaperShadowReadinessArtifact.model_validate(tampered)


def test_invalid_code_sha_and_transport_profile_fail_before_any_inspection() -> None:
    store = InMemoryReadinessStore()
    adapter = CountingAdapter()
    request = PaperShadowReadinessCreateRequest(readiness_idempotency_key=KEY)

    with pytest.raises(PaperShadowReadinessWorkflowConflict, match="code identity"):
        PaperShadowReadinessWorkflow(
            adapter=adapter,
            store=store,
            phase12_code_version_git_sha=None,
        ).create_readiness(request)
    assert adapter.calls == []

    class WrongProfile(CountingAdapter):
        @property
        def transport_profile_sha256(self) -> str:
            return "0" * 64

    wrong = WrongProfile()
    with pytest.raises(PaperShadowReadinessWorkflowConflict, match="transport profile"):
        PaperShadowReadinessWorkflow(
            adapter=wrong,
            store=store,
            phase12_code_version_git_sha=CODE_SHA,
        ).create_readiness(request)
    assert wrong.calls == []


def test_adapter_protocol_exposes_only_read_inspections() -> None:
    adapter = DeterministicMockPaperBrokerAdapter()
    assert isinstance(adapter, PaperBrokerAdapter)
    for forbidden in ("submit_order", "replace_order", "cancel_order", "close_position"):
        assert not hasattr(adapter, forbidden)
