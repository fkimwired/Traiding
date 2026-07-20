"""Verify one canonical Phase 20 input register completely offline."""

from __future__ import annotations

import argparse
import ctypes
import hmac
import json
import ntpath
import os
import stat
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any, NoReturn

MAX_REGISTER_BYTES = 512 * 1024
FAILURE_MESSAGE = "Family A evaluation/holdout input-register verification failed.\n"
_DENIED_AUDIT_EVENTS = frozenset({"os.system", "subprocess.Popen"})
_IS_WINDOWS = os.name == "nt"
_WINDOWS_FILE_READ_ATTRIBUTES = 0x00000080
_WINDOWS_GENERIC_READ = 0x80000000
_WINDOWS_FILE_SHARE_READ = 0x00000001
_WINDOWS_FILE_SHARE_WRITE = 0x00000002
_WINDOWS_OPEN_EXISTING = 3
_WINDOWS_FILE_ATTRIBUTE_DIRECTORY = 0x00000010
_WINDOWS_FILE_ATTRIBUTE_REPARSE_POINT = 0x00000400
_WINDOWS_FILE_FLAG_OPEN_REPARSE_POINT = 0x00200000
_WINDOWS_FILE_FLAG_BACKUP_SEMANTICS = 0x02000000
_WINDOWS_FILE_ATTRIBUTE_TAG_INFO_CLASS = 9
_WINDOWS_INVALID_HANDLE_VALUE = ctypes.c_void_p(-1).value
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


class _InvalidRegister(Exception):
    pass


class _OfflineBoundaryViolation(Exception):
    pass


class _WindowsFileAttributeTagInfo(ctypes.Structure):
    _fields_ = (("file_attributes", ctypes.c_uint32), ("reparse_tag", ctypes.c_uint32))


class _WindowsFileTime(ctypes.Structure):
    _fields_ = (("low", ctypes.c_uint32), ("high", ctypes.c_uint32))


class _WindowsByHandleFileInformation(ctypes.Structure):
    _fields_ = (
        ("file_attributes", ctypes.c_uint32),
        ("creation_time", _WindowsFileTime),
        ("last_access_time", _WindowsFileTime),
        ("last_write_time", _WindowsFileTime),
        ("volume_serial_number", ctypes.c_uint32),
        ("file_size_high", ctypes.c_uint32),
        ("file_size_low", ctypes.c_uint32),
        ("number_of_links", ctypes.c_uint32),
        ("file_index_high", ctypes.c_uint32),
        ("file_index_low", ctypes.c_uint32),
    )


class _SanitizedArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        del message
        raise _InvalidRegister


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
            raise _InvalidRegister
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
    raise _InvalidRegister


def _prove_subprocess_construction_is_denied() -> None:
    import subprocess

    candidate: subprocess.Popen[bytes] | None = None
    try:
        candidate = subprocess.Popen(
            [sys.executable, "-c", "pass"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except _OfflineBoundaryViolation:
        return
    finally:
        if candidate is not None:
            candidate.kill()
            candidate.wait()
    raise _InvalidRegister


def _parser() -> argparse.ArgumentParser:
    parser = _SanitizedArgumentParser(
        description="Verify one deterministic Phase 20 Family A evaluation/holdout input register.",
        allow_abbrev=False,
    )
    parser.add_argument("--register", action=_SingleValueAction, required=True, metavar="PATH")
    return parser


def _reject_duplicate_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise _InvalidRegister
        result[key] = value
    return result


def _reject_float(value: str) -> NoReturn:
    del value
    raise _InvalidRegister


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


def _entry_fingerprint(metadata: os.stat_result) -> tuple[int, int, int]:
    return (metadata.st_dev, metadata.st_ino, stat.S_IFMT(metadata.st_mode))


def _local_register_path(path_text: str) -> Path:
    # Reject network and Win32 device namespaces before any metadata lookup. Python's
    # socket audit events do not cover SMB I/O performed by the operating system.
    if not path_text or "\0" in path_text:
        raise _InvalidRegister
    if len(path_text) >= 2 and all(character in {"/", "\\"} for character in path_text[:2]):
        raise _InvalidRegister
    if _IS_WINDOWS:
        windows_text = path_text.replace("/", "\\")
        folded = windows_text.casefold()
        if windows_text.startswith("\\") or folded.startswith(
            ("\\??\\", "\\device\\", "\\globalroot\\")
        ):
            raise _InvalidRegister
        drive, tail = ntpath.splitdrive(windows_text)
        if drive and not ntpath.isabs(windows_text):
            raise _InvalidRegister
        if drive:
            current_drive, _current_tail = ntpath.splitdrive(os.getcwd())
            if not current_drive or drive.casefold() != current_drive.casefold():
                raise _InvalidRegister
        if ":" in tail:
            raise _InvalidRegister
        components = tuple(component for component in tail.split("\\") if component)
        if any(
            component in {".", ".."} or component.endswith((".", " ")) for component in components
        ):
            raise _InvalidRegister
    elif ".." in Path(path_text).parts:
        raise _InvalidRegister
    return Path(path_text)


def _lexical_register_location(path: Path) -> tuple[str, str, tuple[str, ...]]:
    root = os.getcwd()
    path_text = os.fspath(path)
    path_module = ntpath if _IS_WINDOWS else os.path
    candidate = path_module.normpath(
        path_text if path_module.isabs(path_text) else path_module.join(root, path_text)
    )
    try:
        common = path_module.commonpath((root, candidate))
        relative = path_module.relpath(candidate, root)
    except (OSError, ValueError):
        raise _InvalidRegister from None
    normalized_root = path_module.normpath(root)
    root_matches = (
        ntpath.normcase(common) == ntpath.normcase(normalized_root)
        if _IS_WINDOWS
        else common == normalized_root
    )
    if not root_matches:
        raise _InvalidRegister
    separator = "\\" if _IS_WINDOWS else os.sep
    components = tuple(component for component in relative.split(separator) if component)
    if not components or any(component in {".", ".."} for component in components):
        raise _InvalidRegister
    return normalized_root, candidate, components


def _read_descriptor(descriptor: int) -> tuple[bytes, os.stat_result, os.stat_result]:
    opened = os.fstat(descriptor)
    if (
        not stat.S_ISREG(opened.st_mode)
        or opened.st_size <= 0
        or opened.st_size > MAX_REGISTER_BYTES
    ):
        raise _InvalidRegister
    chunks: list[bytes] = []
    remaining = MAX_REGISTER_BYTES + 1
    while remaining > 0:
        chunk = os.read(descriptor, min(64 * 1024, remaining))
        if not chunk:
            break
        chunks.append(chunk)
        remaining -= len(chunk)
    raw = b"".join(chunks)
    after = os.fstat(descriptor)
    if (
        _stability_fingerprint(after) != _stability_fingerprint(opened)
        or len(raw) != opened.st_size
        or len(raw) > MAX_REGISTER_BYTES
    ):
        raise _InvalidRegister
    return raw, opened, after


def _read_posix_register(root: str, components: tuple[str, ...]) -> bytes:
    nofollow = getattr(os, "O_NOFOLLOW", 0)
    directory = getattr(os, "O_DIRECTORY", 0)
    if not nofollow or not directory:
        raise _InvalidRegister
    directory_flags = os.O_RDONLY | nofollow | directory | getattr(os, "O_CLOEXEC", 0)
    file_flags = os.O_RDONLY | nofollow | getattr(os, "O_CLOEXEC", 0)
    directory_descriptors: list[int] = []
    leaf_descriptor: int | None = None
    try:
        root_descriptor = os.open(root, directory_flags)
        directory_descriptors.append(root_descriptor)
        root_metadata = os.fstat(root_descriptor)
        if not stat.S_ISDIR(root_metadata.st_mode):
            raise _InvalidRegister
        root_device = root_metadata.st_dev

        for component in components[:-1]:
            parent_descriptor = directory_descriptors[-1]
            before = os.stat(component, dir_fd=parent_descriptor, follow_symlinks=False)
            if not stat.S_ISDIR(before.st_mode) or before.st_dev != root_device:
                raise _InvalidRegister
            opened_descriptor = os.open(component, directory_flags, dir_fd=parent_descriptor)
            opened = os.fstat(opened_descriptor)
            if (
                not stat.S_ISDIR(opened.st_mode)
                or opened.st_dev != root_device
                or _entry_fingerprint(opened) != _entry_fingerprint(before)
            ):
                os.close(opened_descriptor)
                raise _InvalidRegister
            directory_descriptors.append(opened_descriptor)

        leaf_name = components[-1]
        parent_descriptor = directory_descriptors[-1]
        before = os.stat(leaf_name, dir_fd=parent_descriptor, follow_symlinks=False)
        if (
            not stat.S_ISREG(before.st_mode)
            or before.st_dev != root_device
            or before.st_size <= 0
            or before.st_size > MAX_REGISTER_BYTES
        ):
            raise _InvalidRegister
        leaf_descriptor = os.open(leaf_name, file_flags, dir_fd=parent_descriptor)
        opened = os.fstat(leaf_descriptor)
        if opened.st_dev != root_device or _identity_fingerprint(opened) != _identity_fingerprint(
            before
        ):
            raise _InvalidRegister
        raw, _opened, _after = _read_descriptor(leaf_descriptor)
        current = os.stat(leaf_name, dir_fd=parent_descriptor, follow_symlinks=False)
        if _entry_fingerprint(current) != _entry_fingerprint(opened):
            raise _InvalidRegister
        return raw
    except _InvalidRegister:
        raise
    except (OSError, OverflowError, ValueError):
        raise _InvalidRegister from None
    finally:
        if leaf_descriptor is not None:
            try:
                os.close(leaf_descriptor)
            except OSError:
                pass
        for directory_descriptor in reversed(directory_descriptors):
            try:
                os.close(directory_descriptor)
            except OSError:
                pass


def _windows_kernel32() -> Any:
    loader = getattr(ctypes, "WinDLL", None)
    if loader is None:
        raise _InvalidRegister
    return loader("kernel32", use_last_error=True)


def _windows_extended_path(path_text: str) -> str:
    return "\\\\?\\" + ntpath.normpath(path_text)


def _windows_create_file(
    path_text: str,
    desired_access: int,
    share_mode: int,
    flags_and_attributes: int,
) -> int:
    kernel32 = _windows_kernel32()
    create_file = kernel32.CreateFileW
    create_file.argtypes = (
        ctypes.c_wchar_p,
        ctypes.c_uint32,
        ctypes.c_uint32,
        ctypes.c_void_p,
        ctypes.c_uint32,
        ctypes.c_uint32,
        ctypes.c_void_p,
    )
    create_file.restype = ctypes.c_void_p
    handle = create_file(
        _windows_extended_path(path_text),
        desired_access,
        share_mode,
        None,
        _WINDOWS_OPEN_EXISTING,
        flags_and_attributes,
        None,
    )
    handle_value = 0 if handle is None else int(handle)
    if handle_value in {0, _WINDOWS_INVALID_HANDLE_VALUE}:
        raise _InvalidRegister
    return handle_value


def _windows_close_handle(handle: int) -> None:
    kernel32 = _windows_kernel32()
    close_handle = kernel32.CloseHandle
    close_handle.argtypes = (ctypes.c_void_p,)
    close_handle.restype = ctypes.c_int
    if not close_handle(ctypes.c_void_p(handle)):
        raise OSError


def _windows_attribute_tag(handle: int) -> tuple[int, int]:
    kernel32 = _windows_kernel32()
    get_information = kernel32.GetFileInformationByHandleEx
    get_information.argtypes = (
        ctypes.c_void_p,
        ctypes.c_int,
        ctypes.c_void_p,
        ctypes.c_uint32,
    )
    get_information.restype = ctypes.c_int
    information = _WindowsFileAttributeTagInfo()
    if not get_information(
        ctypes.c_void_p(handle),
        _WINDOWS_FILE_ATTRIBUTE_TAG_INFO_CLASS,
        ctypes.byref(information),
        ctypes.sizeof(information),
    ):
        raise _InvalidRegister
    return information.file_attributes, information.reparse_tag


def _windows_handle_fingerprint(handle: int) -> tuple[int, ...]:
    kernel32 = _windows_kernel32()
    get_information = kernel32.GetFileInformationByHandle
    get_information.argtypes = (ctypes.c_void_p, ctypes.c_void_p)
    get_information.restype = ctypes.c_int
    information = _WindowsByHandleFileInformation()
    if not get_information(ctypes.c_void_p(handle), ctypes.byref(information)):
        raise _InvalidRegister
    return (
        information.volume_serial_number,
        information.file_index_high,
        information.file_index_low,
        information.file_attributes,
        information.file_size_high,
        information.file_size_low,
        information.last_write_time.high,
        information.last_write_time.low,
    )


def _windows_open_component(path_text: str, *, directory: bool) -> int:
    access = _WINDOWS_FILE_READ_ATTRIBUTES | (0 if directory else _WINDOWS_GENERIC_READ)
    flags = _WINDOWS_FILE_FLAG_OPEN_REPARSE_POINT | (
        _WINDOWS_FILE_FLAG_BACKUP_SEMANTICS if directory else 0
    )
    return _windows_create_file(
        path_text,
        access,
        _WINDOWS_FILE_SHARE_READ | _WINDOWS_FILE_SHARE_WRITE,
        flags,
    )


def _read_windows_register(root: str, components: tuple[str, ...]) -> bytes:
    directory_handles: list[int] = []
    leaf_handle: int | None = None
    descriptor: int | None = None
    try:
        root_handle = _windows_open_component(root, directory=True)
        directory_handles.append(root_handle)
        root_attributes, _root_tag = _windows_attribute_tag(root_handle)
        if not root_attributes & _WINDOWS_FILE_ATTRIBUTE_DIRECTORY:
            raise _InvalidRegister
        root_fingerprint = _windows_handle_fingerprint(root_handle)
        root_volume = root_fingerprint[0]

        current_path = root
        for component in components[:-1]:
            current_path = ntpath.join(current_path, component)
            handle = _windows_open_component(current_path, directory=True)
            directory_handles.append(handle)
            attributes, reparse_tag = _windows_attribute_tag(handle)
            fingerprint = _windows_handle_fingerprint(handle)
            if (
                not attributes & _WINDOWS_FILE_ATTRIBUTE_DIRECTORY
                or attributes & _WINDOWS_FILE_ATTRIBUTE_REPARSE_POINT
                or reparse_tag != 0
                or fingerprint[0] != root_volume
            ):
                raise _InvalidRegister

        leaf_path = ntpath.join(current_path, components[-1])
        leaf_handle = _windows_open_component(leaf_path, directory=False)
        attributes, reparse_tag = _windows_attribute_tag(leaf_handle)
        before = _windows_handle_fingerprint(leaf_handle)
        file_size = (before[4] << 32) | before[5]
        if (
            attributes & _WINDOWS_FILE_ATTRIBUTE_DIRECTORY
            or attributes & _WINDOWS_FILE_ATTRIBUTE_REPARSE_POINT
            or reparse_tag != 0
            or before[0] != root_volume
            or file_size <= 0
            or file_size > MAX_REGISTER_BYTES
        ):
            raise _InvalidRegister

        msvcrt = __import__("msvcrt")
        descriptor = int(
            msvcrt.open_osfhandle(
                leaf_handle,
                os.O_RDONLY | getattr(os, "O_BINARY", 0),
            )
        )
        if descriptor < 0:
            raise _InvalidRegister
        transferred_handle = leaf_handle
        leaf_handle = None
        raw, _opened, _after = _read_descriptor(descriptor)
        if _windows_handle_fingerprint(transferred_handle) != before:
            raise _InvalidRegister
        return raw
    except _InvalidRegister:
        raise
    except (OSError, OverflowError, ValueError):
        raise _InvalidRegister from None
    finally:
        if descriptor is not None:
            try:
                os.close(descriptor)
            except OSError:
                pass
        elif leaf_handle is not None:
            try:
                _windows_close_handle(leaf_handle)
            except OSError:
                pass
        for directory_handle in reversed(directory_handles):
            try:
                _windows_close_handle(directory_handle)
            except OSError:
                pass


def _read_register(path_text: str) -> bytes:
    path = _local_register_path(path_text)
    root, _candidate, components = _lexical_register_location(path)
    raw = (
        _read_windows_register(root, components)
        if _IS_WINDOWS
        else _read_posix_register(root, components)
    )
    if raw.startswith(b"\xef\xbb\xbf"):
        raise _InvalidRegister
    try:
        decoded = json.loads(
            raw.decode("utf-8", errors="strict"),
            object_pairs_hook=_reject_duplicate_keys,
            parse_float=_reject_float,
            parse_constant=_reject_float,
        )
    except _InvalidRegister:
        raise
    except (UnicodeDecodeError, json.JSONDecodeError, RecursionError, ValueError):
        raise _InvalidRegister from None
    if not isinstance(decoded, dict):
        raise _InvalidRegister
    return raw


def _matches_prefix(module_name: str, prefix: str) -> bool:
    return module_name == prefix or module_name.startswith(f"{prefix}.")


def _load_contract() -> tuple[Any, Any]:
    before = frozenset(sys.modules)
    contracts = __import__(
        "fable5_data.phase20.contracts",
        fromlist=["FamilyAEvaluationHoldoutInputRegister"],
    )
    input_register = __import__(
        "fable5_data.phase20.input_register",
        fromlist=["canonical_evaluation_holdout_input_register_bytes"],
    )
    newly_imported = frozenset(sys.modules).difference(before)
    if any(
        _matches_prefix(module_name, prefix)
        for module_name in newly_imported
        for prefix in _FORBIDDEN_IMPORT_PREFIXES
    ):
        raise _InvalidRegister
    model = getattr(contracts, "FamilyAEvaluationHoldoutInputRegister", None)
    canonical_bytes = getattr(
        input_register,
        "canonical_evaluation_holdout_input_register_bytes",
        None,
    )
    if model is None or canonical_bytes is None:
        raise _InvalidRegister
    return model, canonical_bytes


def _verify(path_text: str) -> dict[str, object]:
    raw = _read_register(path_text)
    model, canonical_bytes = _load_contract()
    try:
        validated = model.model_validate_json(raw, strict=True)
    except Exception:
        raise _InvalidRegister from None
    if not hmac.compare_digest(raw, canonical_bytes()):
        raise _InvalidRegister
    return {
        "aggregate_conclusion": validated.aggregate_conclusion.value,
        "artifact_id": str(validated.artifact_id),
        "artifact_sha256": validated.artifact_sha256,
        "input_requirement_count": len(validated.input_requirements),
        "network": "disabled",
        "outcome": validated.outcome.value,
        "register_state": validated.register_state.value,
        "required_prior_evidence": "missing",
        "schema_version": validated.schema_version,
        "status": "valid",
        "step3_eligible": validated.step3_eligible,
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
        _install_offline_boundary()
        _prove_socket_construction_is_denied()
        _prove_subprocess_construction_is_denied()
        arguments = _parser().parse_args(argv)
        result = _verify(arguments.register)
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
