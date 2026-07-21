"""Verify one canonical Phase 24 RTDSM rights-clarification requirements artifact offline."""

from __future__ import annotations

import argparse
import hmac
import json
import sys
from collections.abc import Sequence
from typing import Any, NoReturn

import verify_family_a_evaluation_holdout_input_register as hardened

FAILURE_MESSAGE = "Family A RTDSM rights-clarification requirements verification failed.\n"
_DENIED_AUDIT_EVENTS = frozenset({"os.system", "subprocess.Popen"})
_FORBIDDEN_IMPORT_PREFIXES = (
    "aiohttp",
    "fastapi",
    "fable5_api",
    "fable5_jobs",
    "fable5_paper",
    "fable5_research",
    "httpx",
    "psycopg",
    "redis",
    "requests",
    "rq",
    "sqlalchemy",
    "sqlite3",
    "urllib.request",
    "urllib3",
    "uvicorn",
)


class _InvalidArtifact(Exception):
    pass


class _OfflineBoundaryViolation(Exception):
    pass


class _SanitizedArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        del message
        raise _InvalidArtifact


class _SingleValueAction(argparse.Action):
    def __call__(
        self,
        parser: argparse.ArgumentParser,
        namespace: argparse.Namespace,
        values: object,
        option_string: str | None = None,
    ) -> None:
        del parser, option_string
        if not isinstance(values, str) or getattr(namespace, self.dest, None) is not None:
            raise _InvalidArtifact
        setattr(namespace, self.dest, values)


def _offline_audit_hook(event: str, args: tuple[object, ...]) -> None:
    del args
    if event.startswith("socket.") or event in _DENIED_AUDIT_EVENTS:
        raise _OfflineBoundaryViolation


def _prove_offline_boundary() -> None:
    import socket
    import subprocess

    candidate: socket.socket | None = None
    try:
        candidate = socket.socket()
    except _OfflineBoundaryViolation:
        pass
    else:
        candidate.close()
        raise _InvalidArtifact
    process: subprocess.Popen[bytes] | None = None
    try:
        process = subprocess.Popen(
            [sys.executable, "-c", "pass"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
    except _OfflineBoundaryViolation:
        return
    finally:
        if process is not None:
            process.kill()
            process.wait()
    raise _InvalidArtifact


def _parser() -> argparse.ArgumentParser:
    parser = _SanitizedArgumentParser(
        description="Verify deterministic Phase 24 RTDSM rights-clarification requirements.",
        allow_abbrev=False,
    )
    parser.add_argument("--requirements", action=_SingleValueAction, required=True, metavar="PATH")
    return parser


def _matches_prefix(module_name: str, prefix: str) -> bool:
    return module_name == prefix or module_name.startswith(f"{prefix}.")


def _load_contract() -> tuple[Any, Any]:
    before = frozenset(sys.modules)
    contracts = __import__(
        "fable5_data.phase24.contracts", fromlist=["FamilyARTDSMRightsClarificationRequirements"]
    )
    builder = __import__(
        "fable5_data.phase24.rights_clarification",
        fromlist=["canonical_rtdsm_rights_clarification_requirements_bytes"],
    )
    newly_imported = frozenset(sys.modules).difference(before)
    if any(
        _matches_prefix(module_name, prefix)
        for module_name in newly_imported
        for prefix in _FORBIDDEN_IMPORT_PREFIXES
    ):
        raise _InvalidArtifact
    model = getattr(contracts, "FamilyARTDSMRightsClarificationRequirements", None)
    canonical_bytes = getattr(
        builder, "canonical_rtdsm_rights_clarification_requirements_bytes", None
    )
    if model is None or canonical_bytes is None:
        raise _InvalidArtifact
    return model, canonical_bytes


def _verify(path_text: str) -> dict[str, object]:
    try:
        raw = hardened._read_register(path_text)
    except BaseException:
        raise _InvalidArtifact from None
    model, canonical_bytes = _load_contract()
    try:
        validated = model.model_validate_json(raw, strict=True)
    except Exception:
        raise _InvalidArtifact from None
    if not hmac.compare_digest(raw, canonical_bytes()):
        raise _InvalidArtifact
    return {
        "aggregate_conclusion": validated.aggregate_conclusion.value,
        "artifact_id": str(validated.artifact_id),
        "artifact_sha256": validated.artifact_sha256,
        "clarification_question_count": len(validated.clarification_questions),
        "evidence_requirement_count": len(validated.evidence_requirements),
        "network": "disabled",
        "outcome": validated.outcome.value,
        "proposed_use_disclosure_count": len(validated.proposed_use_disclosures),
        "requirements_state": validated.requirements_state.value,
        "schema_version": validated.schema_version,
        "status": "valid",
        "transition_rule_count": len(validated.transition_rules),
    }


def _failure_exit() -> int:
    try:
        sys.stderr.buffer.write(FAILURE_MESSAGE.encode("ascii"))
        sys.stderr.buffer.flush()
    except BaseException:
        pass
    return 2


def main(argv: Sequence[str] | None = None) -> int:
    try:
        sys.addaudithook(_offline_audit_hook)
        _prove_offline_boundary()
        arguments = _parser().parse_args(argv)
        result = _verify(arguments.requirements)
    except SystemExit as exc:
        if exc.code in (None, 0):
            raise
        return _failure_exit()
    except BaseException:
        return _failure_exit()
    try:
        sys.stdout.write(json.dumps(result, sort_keys=True, separators=(",", ":")) + "\n")
    except BaseException:
        return _failure_exit()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
