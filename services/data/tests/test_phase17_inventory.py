from __future__ import annotations

from fable5_data.phase16.plan import build_family_a_point_in_time_source_plan
from fable5_data.phase17.canonical import (
    PHASE17_ACCEPTED_PHASE16_COMMIT_SHA,
    PHASE17_ACCEPTED_PHASE16_TREE_SHA,
    PHASE17_BOUNDARY_VALUES,
    PHASE17_FROZEN_AT_UTC,
    PHASE17_PHASE16_ARTIFACT_SHA256,
    PHASE17_PHASE16_GAP_BINDINGS_MANIFEST_SHA256,
    PHASE17_PHASE16_STEP1_SHA256,
)
from fable5_data.phase17.inventory import (
    build_family_a_candidate_product_inventory,
    canonical_candidate_product_inventory_bytes,
)


def test_builder_is_byte_deterministic_and_ambient_free() -> None:
    first = build_family_a_candidate_product_inventory()
    second = build_family_a_candidate_product_inventory()

    assert first == second
    assert canonical_candidate_product_inventory_bytes() == (
        canonical_candidate_product_inventory_bytes()
    )
    assert canonical_candidate_product_inventory_bytes().endswith(b"\n")
    assert canonical_candidate_product_inventory_bytes().count(b"\n") == 1
    assert first.frozen_at_utc == PHASE17_FROZEN_AT_UTC


def test_inventory_binds_accepted_phase16_artifact_and_step1_exactly() -> None:
    phase16 = build_family_a_point_in_time_source_plan()
    inventory = build_family_a_candidate_product_inventory()

    assert inventory.accepted_phase16_commit_sha == PHASE17_ACCEPTED_PHASE16_COMMIT_SHA
    assert inventory.accepted_phase16_tree_sha == PHASE17_ACCEPTED_PHASE16_TREE_SHA
    assert inventory.phase16_artifact_sha256 == phase16.artifact_sha256
    assert inventory.phase16_artifact_sha256 == PHASE17_PHASE16_ARTIFACT_SHA256
    assert inventory.phase16_gap_bindings_manifest_sha256 == (phase16.gap_bindings_manifest_sha256)
    assert inventory.phase16_gap_bindings_manifest_sha256 == (
        PHASE17_PHASE16_GAP_BINDINGS_MANIFEST_SHA256
    )
    assert inventory.phase16_step1_sha256 == phase16.future_steps[0].step_sha256
    assert inventory.phase16_step1_sha256 == PHASE17_PHASE16_STEP1_SHA256


def test_exact_official_surfaces_and_candidate_group_mappings_are_frozen() -> None:
    inventory = build_family_a_candidate_product_inventory()
    urls = tuple(item.official_documentation_url for item in inventory.products)

    assert urls == (
        "https://www.tiingo.com/documentation/end-of-day",
        "https://www.tiingo.com/documentation/fundamentals",
        "https://www.tiingo.com/documentation/corporate-actions/dividends",
        "https://www.tiingo.com/documentation/corporate-actions/splits",
        "https://indexes.morningstar.com/research-data-products/crsp-us-stock-databases",
        "https://indexes.morningstar.com/research-data-products/crsp-compustat-merged-database",
        "https://www.sec.gov/search-filings/edgar-application-programming-interfaces",
        "https://fred.stlouisfed.org/docs/api/fred/overview.html",
        "https://www.lseg.com/en/data-analytics/market-data/data-feeds/tick-history",
    )
    assert tuple(len(group.product_codes) for group in inventory.candidate_groups) == (
        4,
        1,
        1,
        1,
        1,
        1,
    )
    assert inventory.candidate_groups[-1].product_codes[0].value == (
        "LSEG_TICK_HISTORY_INSTRUMENT_AND_VENUE_WEB_API"
    )
    crsp_roles = {item.value for item in inventory.products[4].capability_codes}
    assert "sector_classification_history" in crsp_roles
    assert inventory.products[-1].capability_codes[0].value == "historical_liquidity_depth"


def test_only_inventory_output_is_frozen_and_all_later_steps_are_unstarted() -> None:
    inventory = build_family_a_candidate_product_inventory()
    first, *later = inventory.source_plan_steps

    assert first.state.value == "OUTPUT_FROZEN"
    assert first.external_action_authorized is False
    assert len(first.produced_outputs) == 1
    assert first.produced_outputs[0].name == "candidate_product_inventory_sha256"
    assert first.produced_outputs[0].sha256 == inventory.candidate_product_inventory_sha256
    assert all(item.state.value == "NOT_STARTED" for item in later)
    assert all(not item.produced_outputs and not item.external_action_authorized for item in later)


def test_every_authority_and_action_boundary_remains_closed() -> None:
    rendered = build_family_a_candidate_product_inventory().model_dump(mode="python")
    for field, expected in PHASE17_BOUNDARY_VALUES.items():
        assert rendered[field] is expected
