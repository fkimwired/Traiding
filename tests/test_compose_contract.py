from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def test_compose_declares_the_complete_phase1_stack() -> None:
    compose = yaml.safe_load((ROOT / "compose.yaml").read_text(encoding="utf-8"))
    services = compose["services"]

    assert set(services) == {"postgres", "redis", "migrate", "api", "worker", "frontend"}
    assert services["api"]["depends_on"]["migrate"]["condition"] == (
        "service_completed_successfully"
    )
    assert services["api"]["depends_on"]["postgres"]["condition"] == "service_healthy"
    assert services["api"]["depends_on"]["redis"]["condition"] == "service_healthy"
    assert services["frontend"]["depends_on"]["api"]["condition"] == "service_healthy"
    assert services["worker"]["depends_on"]["redis"]["condition"] == "service_healthy"

    for service_name in ("postgres", "redis", "api", "worker", "frontend"):
        assert "healthcheck" in services[service_name]


def test_compose_is_paper_only_and_locally_bound() -> None:
    compose = yaml.safe_load((ROOT / "compose.yaml").read_text(encoding="utf-8"))
    services = compose["services"]

    for service_name in ("migrate", "api", "worker"):
        assert services[service_name]["environment"]["FABLE5_EXECUTION_MODE"] == "paper"

    for service_name in ("postgres", "redis", "api", "frontend"):
        for port in services[service_name]["ports"]:
            assert port.startswith("127.0.0.1:")

    manifest = (ROOT / "compose.yaml").read_text(encoding="utf-8").lower()
    assert "api.alpaca.markets" not in manifest
    assert "/v2/orders" not in manifest


def test_database_identity_cannot_diverge_from_the_application_url() -> None:
    compose = yaml.safe_load((ROOT / "compose.yaml").read_text(encoding="utf-8"))
    services = compose["services"]
    expected_url = "postgresql+psycopg://fable5:fable5_dev_only@postgres:5432/fable5"

    assert services["postgres"]["environment"] == {
        "POSTGRES_DB": "fable5",
        "POSTGRES_USER": "fable5",
        "POSTGRES_PASSWORD": "fable5_dev_only",
    }
    for service_name in ("migrate", "api", "worker"):
        assert services[service_name]["environment"]["FABLE5_DATABASE_URL"] == expected_url

    example_environment = (ROOT / ".env.example").read_text(encoding="utf-8")
    assert "POSTGRES_DB=" not in example_environment
    assert "POSTGRES_USER=" not in example_environment
    assert "POSTGRES_PASSWORD=" not in example_environment
    assert "FABLE5_DATABASE_URL=" not in example_environment
