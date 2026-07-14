from __future__ import annotations

import ast
import hashlib
from pathlib import Path
from uuid import UUID

import pytest
from fable5_backtester.contracts import GateCode, LeakageCode
from fable5_research.contracts import (
    ResearchAttemptStatus,
    ResearchConfigurationId,
    ResearchPipelineSpecification,
    ResearchRunCreateRequest,
    ResearchRunSummary,
    StructuredTextFeatures,
    TextFeatureExtraction,
)
from pydantic import ValidationError

ROOT = Path(__file__).resolve().parents[1]

PRIOR_MIGRATION_SHA256 = {
    "0001_phase1_audit_spine.py": (
        "5cd27e1bde6b03720f54fe5e1260cf5f9085e16a4eebed957aeeba1a3a7d17f8"
    ),
    "0002_phase2_source_extraction.py": (
        "d45c1cb0ade079cfba7492c75c1aff13fc714aaae0a81637f21942c175c4e5c8"
    ),
    "0003_phase3_canon_mapping.py": (
        "6859c63723dc31d6ede4cdd5528a42640f16e3c6103567b5d900a46741edf07d"
    ),
    "0004_phase4_point_in_time_data.py": (
        "78c52c613358708940d88cbd47069bdde9bc857046bf646d7461bd13b57b3008"
    ),
    "0005_phase5_evaluation.py": (
        "b368edf97c35c5b7d7ac651073a02c204816b638855d3bcae4d7cabf265a1404"
    ),
}

PHASE5_GATE_IMPLEMENTATION_SHA256 = {
    "canonical.py": "095c174b94778d22feef4a0444279f0fea63d1d6b53b678aac571221faf4a4c0",
    "chronology.py": "dd6418352b96089306ecfc8a026d1be4c217ef220fe818a05c92dc5aa813fa76",
    "costs.py": "7b5a31c165756f99ca33ed72585aa5631d26588f48fb811f5e483dfc7f92273f",
    "engine.py": "eaf99d7295a51b9f49019105fbc9c7272a911fd8cfeaffce8f5d4a7608d0cdc3",
    "evaluation_geometry.py": ("8d66b3e4e31a1e45a13d0c3e57c5e8162a4487cd283fbef2b3a1404c3bdf03ce"),
    "leakage.py": "a7e31285ddf9f376c402fe2dd4651442f513a4ed290f5267e06a17d918efebf1",
    "metrics.py": "b8d21981b98c02f68be6b9393dd486d667882c0415e207d22f8449fac450f2aa",
    "outcomes.py": "28d45549873ca6f805a20c1989e2985b91649ff332a638a11e54fe14d28a2f86",
    "preprocessing.py": ("f8eadbd610aec003ea6700c2141656a34491d1b0e03992274ec8f1dd389d5c34"),
    "statistics.py": "1afa8c4f5e6a3b3e1ba85b525d50b34b86eb3feb1178329bec2d069aedd30907",
}

PHASE4_BASE_FUNCTION_PROSRC_SHA256 = {
    "940e8e9b175cad7e0cc986b97cde39e1ef115022983114bcf73cff9918da4a27",
    "bf41f4906b94991731d80fbf1756dbad087081d552acc6d328e6b4eff6cca4af",
}


def normalized(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig").replace("\r\n", "\n").replace("\r", "\n")


def declared_names(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return {
        node.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))
    }


def test_phase6_preserves_every_prior_migration_and_phase5_gate_implementation_byte_exactly() -> (
    None
):
    migration_root = ROOT / "services/api/migrations/versions"
    for filename, expected in PRIOR_MIGRATION_SHA256.items():
        assert hashlib.sha256((migration_root / filename).read_bytes()).hexdigest() == expected

    gate_root = ROOT / "services/backtester/src/fable5_backtester"
    for filename, expected in PHASE5_GATE_IMPLEMENTATION_SHA256.items():
        assert hashlib.sha256((gate_root / filename).read_bytes()).hexdigest() == expected

    verifier = normalized(ROOT / "scripts/verify_phase1.py")
    for expected in PHASE4_BASE_FUNCTION_PROSRC_SHA256:
        assert expected in verifier


def test_phase6_keeps_the_exact_twelve_gates_and_six_leakage_blockers() -> None:
    assert tuple(code.value for code in GateCode) == (
        "DATA_PIT",
        "CV_CHRONOLOGY",
        "PREPROCESSING",
        "TRIAL_REGISTRY",
        "DSR",
        "PBO",
        "COST_STRESS",
        "LEAKAGE",
        "SAMPLE_ADEQUACY",
        "REGIME",
        "RISK_LIMITS",
        "REPRODUCIBILITY",
    )
    assert tuple(code.value for code in LeakageCode) == (
        "L01",
        "L02",
        "L03",
        "L04",
        "L05",
        "L06",
    )
    contracts = normalized(ROOT / "services/backtester/src/fable5_backtester/contracts.py")
    leakage = normalized(ROOT / "services/backtester/src/fable5_backtester/leakage.py")
    for evidence in (
        "L01PriceBasisEvidence",
        "L02FundamentalRevisionEvidence",
        "L03FeatureAvailabilityEvidence",
        "L04DependencyScanEvidence",
        "L05MembershipReconstructionEvidence",
        "L06TrainOnlyFitEvidence",
    ):
        assert evidence in contracts
        assert evidence in leakage


def test_phase6_verifier_uses_full_pit_capabilities_and_standard_leakage_evidence() -> None:
    verifier = normalized(ROOT / "scripts/verify_phase1.py")
    phase6_api = verifier.split("def verify_phase6_api", 1)[1].split("def compose_exec", 1)[0]

    for required_evidence in (
        '"security_master": 11',
        '"universe_membership": 5',
        '"ohlcv": 852',
        '"trading_calendar": 305',
        "sum(one_source_constituent_counts.values()) != 1195",
        '"phase5-leakage-l01-evidence-v1"',
        '"phase5-leakage-l05-evidence-v1"',
        'social_reference.get("record_type") != "social_attention"',
        'official_reference.get("record_type") != "official_document_content"',
        'item.get("extractor_kind") != "deterministic_mock"',
    ):
        assert required_evidence in phase6_api
    assert "not-applicable-evidence" not in phase6_api

    decisions = normalized(ROOT / "docs/PHASE_06_RESEARCH_DECISIONS.md")
    assert "1,195 deterministic records" in decisions
    assert "305 calendar sessions" in decisions


def test_phase6_has_only_the_six_frozen_server_owned_fixture_ids() -> None:
    assert {item.value for item in ResearchConfigurationId} == {
        "phase6-a-pass-v1",
        "phase6-a-fail-cost-v1",
        "phase6-b-pass-v1",
        "phase6-b-fail-crash-v1",
        "phase6-c-pass-v1",
        "phase6-c-fail-corroboration-v1",
    }
    assert {item.value for item in ResearchAttemptStatus} == {
        "completed",
        "failed",
        "abandoned",
        "no_return",
        "blocked",
    }

    request = ResearchRunCreateRequest(
        mapping_id=UUID("aaaaaaaa-aaaa-5aaa-8aaa-aaaaaaaaaaaa"),
        snapshot_ids=(UUID("bbbbbbbb-bbbb-5bbb-8bbb-bbbbbbbbbbbb"),),
        research_configuration_id=ResearchConfigurationId.A_PASS,
    )
    assert set(request.model_dump()) == {
        "mapping_id",
        "snapshot_ids",
        "research_configuration_id",
    }
    with pytest.raises(ValidationError, match="Extra inputs"):
        ResearchRunCreateRequest.model_validate(
            {
                **request.model_dump(),
                "metrics": {},
                "thresholds": {},
                "artifact_sha256": "0" * 64,
                "promotion_state": "PASS_RESEARCH",
            }
        )


def test_phase6_specification_cannot_run_without_every_policy_declaration() -> None:
    schema = ResearchPipelineSpecification.model_json_schema()
    required = set(schema["required"])
    assert {
        "specification_id",
        "specification_version",
        "specification_sha256",
        "family",
        "signal_definition",
        "target_forecast_horizon",
        "required_capabilities",
        "feature_names",
        "label_interval_rule",
        "transaction_cost_model_id",
        "slippage_model_id",
        "walk_forward",
        "risk_limits",
        "required_audit_fields",
        "llm_role",
    } <= required
    assert schema["properties"]["no_image_or_chart_pattern_classifier"]["const"] is True


def test_phase6_text_contract_is_extraction_only_and_never_a_decision_surface() -> None:
    assert set(StructuredTextFeatures.model_fields) == {
        "novelty",
        "direction",
        "uncertainty",
        "risk_change",
        "event_tags",
    }
    prohibited = {
        "label",
        "signal",
        "model_decision",
        "buy_sell_call",
        "allocation",
        "position_size",
        "promotion_outcome",
        "execution_instruction",
    }
    assert not prohibited.intersection(TextFeatureExtraction.model_fields)


def test_phase6_summary_carries_non_negotiable_research_only_flags() -> None:
    schema = ResearchRunSummary.model_json_schema()
    properties = schema["properties"]
    assert properties["synthetic"]["const"] is True
    assert properties["no_real_performance_claimed"]["const"] is True
    assert properties["pass_research_is_not_paper_approval"]["const"] is True


def test_phase6_has_no_phase7_execution_or_approval_module() -> None:
    research_root = ROOT / "services/research/src/fable5_research"
    forbidden_module_tokens = {
        "approval",
        "broker",
        "execution",
        "live",
        "order",
        "paper",
        "position",
        "pre_order",
    }
    for path in research_root.glob("*.py"):
        assert path.stem.casefold() not in forbidden_module_tokens
        names = {name.casefold() for name in declared_names(path)}
        assert not names.intersection(
            {
                "approvedpaper",
                "broker",
                "liveexecution",
                "order",
                "paperexecution",
                "position",
                "preorderrisk",
            }
        )
    combined = "\n".join(path.read_text(encoding="utf-8") for path in research_root.glob("*.py"))
    for prohibited_state in ("APPROVED_PAPER", "PAPER_APPROVED", "LIVE_TRADING"):
        assert prohibited_state not in combined


def test_phase6_verifier_has_static_full_and_preserving_hooks() -> None:
    verifier = normalized(ROOT / "scripts/verify_phase1.py")
    for static_evidence in (
        "PHASE_6_REQUIRED_PATHS",
        "PHASE_6_TABLES",
        "PHASE_6_APPEND_ONLY_ERROR",
        "PHASE_1_5_MIGRATION_SHA256",
        "PHASE_5_GATE_IMPLEMENTATION_SHA256",
        "ResearchRunCreateRequest accepts client-authoritative results or metadata",
        "LLM text output exceeds the structured-feature boundary",
        "Phase 7 or execution capability leaked into Phase 6",
    ):
        assert static_evidence in verifier
    for hook in (
        "def verify_phase6_api",
        "def verify_phase6_postgres_acceptance",
        "def verify_phase6_append_only",
        "def verify_phase6_migration_cycle",
        "verify_phase6_api(api_url)",
        "verify_phase6_postgres_acceptance(environment)",
        "verify_phase6_append_only(project, environment)",
        "verify_phase6_migration_cycle(project, environment)",
    ):
        assert hook in verifier

    cycle = verifier.split("def verify_phase6_migration_cycle", 1)[1].split(
        "def wait_for_frontend", 1
    )[0]
    for evidence in (
        "*PHASE_5_TABLES",
        "len(before) != 31",
        '"downgrade",\n            "0005_phase5"',
        '"upgrade",\n            "0006_phase6"',
        "assert_snapshots_equal(before, after_downgrade",
        "assert_snapshots_equal(before, after_reupgrade",
        "preserved all 31 Phase 1-5 tables",
    ):
        assert evidence in cycle
