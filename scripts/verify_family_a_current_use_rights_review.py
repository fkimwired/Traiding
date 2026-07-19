"""Verify one canonical Phase 18 current-use rights review completely offline."""

from __future__ import annotations

import argparse
import hmac
import json
import os
import stat
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any, NoReturn

MAX_REVIEW_BYTES = 512 * 1024
FAILURE_MESSAGE = "Family A current-use rights review verification failed.\n"
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


class _InvalidReview(Exception):
    pass


class _OfflineBoundaryViolation(Exception):
    pass


class _SanitizedArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        del message
        raise _InvalidReview


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
            raise _InvalidReview
        setattr(namespace, self.dest, values)


def _offline_audit_hook(event: str, args: tuple[object, ...]) -> None:
    del args
    if event.startswith("socket.") or event in _DENIED_AUDIT_EVENTS:
        raise _OfflineBoundaryViolation


def _install_offline_boundary() -> None:
    sys.addaudithook(_offline_audit_hook)


def _prove_socket_construction_is_denied() -> None:
    import socket

    candidate: socket.socket | None = None
    try:
        candidate = socket.socket()
    except _OfflineBoundaryViolation:
        return
    finally:
        if candidate is not None:
            candidate.close()
    raise _InvalidReview


def _parser() -> argparse.ArgumentParser:
    parser = _SanitizedArgumentParser(
        description="Verify one deterministic Phase 18 Family A current-use rights review.",
        allow_abbrev=False,
    )
    parser.add_argument("--review", action=_SingleValueAction, required=True, metavar="PATH")
    return parser


def _reject_duplicate_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise _InvalidReview
        result[key] = value
    return result


def _reject_float(value: str) -> NoReturn:
    del value
    raise _InvalidReview


def _identity_fingerprint(metadata: os.stat_result) -> tuple[int, int, int, int, int]:
    return (
        metadata.st_dev,
        metadata.st_ino,
        metadata.st_mode,
        metadata.st_size,
        metadata.st_mtime_ns,
    )


def _stability_fingerprint(metadata: os.stat_result) -> tuple[int, int, int, int, int, int]:
    return (*_identity_fingerprint(metadata), metadata.st_ctime_ns)


def _read_review(path_text: str) -> bytes:
    path = Path(path_text)
    descriptor: int | None = None
    try:
        metadata = path.lstat()
        if (
            not stat.S_ISREG(metadata.st_mode)
            or metadata.st_size <= 0
            or metadata.st_size > MAX_REVIEW_BYTES
        ):
            raise _InvalidReview
        flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
        descriptor = os.open(path, flags)
        opened = os.fstat(descriptor)
        if not stat.S_ISREG(opened.st_mode) or _identity_fingerprint(
            opened
        ) != _identity_fingerprint(metadata):
            raise _InvalidReview
        with os.fdopen(descriptor, "rb", closefd=False) as handle:
            raw = handle.read(MAX_REVIEW_BYTES + 1)
        after = os.fstat(descriptor)
    except _InvalidReview:
        raise
    except (OSError, OverflowError, ValueError):
        raise _InvalidReview from None
    finally:
        if descriptor is not None:
            try:
                os.close(descriptor)
            except OSError:
                pass
    if (
        _stability_fingerprint(after) != _stability_fingerprint(opened)
        or len(raw) != opened.st_size
        or len(raw) > MAX_REVIEW_BYTES
        or raw.startswith(b"\xef\xbb\xbf")
    ):
        raise _InvalidReview
    try:
        decoded = json.loads(
            raw.decode("utf-8", errors="strict"),
            object_pairs_hook=_reject_duplicate_keys,
            parse_float=_reject_float,
            parse_constant=_reject_float,
        )
    except _InvalidReview:
        raise
    except (UnicodeDecodeError, json.JSONDecodeError, RecursionError, ValueError):
        raise _InvalidReview from None
    if not isinstance(decoded, dict):
        raise _InvalidReview
    return raw


def _matches_prefix(module_name: str, prefix: str) -> bool:
    return module_name == prefix or module_name.startswith(f"{prefix}.")


def _load_contract() -> tuple[Any, Any]:
    before = frozenset(sys.modules)
    contracts = __import__(
        "fable5_data.phase18.contracts",
        fromlist=["FamilyACurrentUseRightsReview"],
    )
    review = __import__(
        "fable5_data.phase18.rights_review",
        fromlist=["canonical_current_use_rights_review_bytes"],
    )
    newly_imported = frozenset(sys.modules).difference(before)
    if any(
        _matches_prefix(module_name, prefix)
        for module_name in newly_imported
        for prefix in _FORBIDDEN_IMPORT_PREFIXES
    ):
        raise _InvalidReview
    model = getattr(contracts, "FamilyACurrentUseRightsReview", None)
    canonical_bytes = getattr(review, "canonical_current_use_rights_review_bytes", None)
    if model is None or canonical_bytes is None:
        raise _InvalidReview
    return model, canonical_bytes


def _verify(path_text: str) -> dict[str, str]:
    raw = _read_review(path_text)
    model, canonical_bytes = _load_contract()
    try:
        validated = model.model_validate_json(raw, strict=True)
    except Exception:
        raise _InvalidReview from None
    if not hmac.compare_digest(raw, canonical_bytes()):
        raise _InvalidReview
    return {
        "aggregate_conclusion": validated.aggregate_conclusion.value,
        "artifact_id": str(validated.artifact_id),
        "artifact_sha256": validated.artifact_sha256,
        "currentness": "review-snapshot-only",
        "independent_rights_review_sha256": validated.independent_rights_review_sha256,
        "network": "disabled",
        "outcome": validated.outcome.value,
        "rights_currentness_sha256": validated.rights_currentness_sha256,
        "schema_version": validated.schema_version,
        "status": "valid",
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
        _install_offline_boundary()
        _prove_socket_construction_is_denied()
        arguments = _parser().parse_args(argv)
        result = _verify(arguments.review)
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
