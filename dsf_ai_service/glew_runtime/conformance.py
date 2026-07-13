"""Deterministic startup and read-only conformance for the GLEW runtime."""

from __future__ import annotations

import argparse
import contextlib
import fcntl
import hashlib
import importlib
import json
import os
import re
import stat
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator, Mapping

from . import field, l6
from .genesis import (
    FIELD_OPERATOR_STATUS,
    PROFILE_FILE,
    STATE_FILE,
    GenesisError,
    create_clean_genesis,
    discover_and_restore_clean_genesis,
    restore_clean_genesis,
)


SCHEMA = "glew.runtime_conformance.v1"
DEFAULT_PROFILE_PATH = Path(__file__).with_name("GLEW_UPSTREAM_PROFILE_v1.json")
ROOT_ENVIRONMENT_VARIABLE = "GLEW_GENESIS_ROOT"
IDENTITY_ENVIRONMENT_VARIABLE = "GLEW_EXPECTED_IDENTITY"
PROFILE_ENVIRONMENT_VARIABLE = "GLEW_PROFILE_PATH"
CREATE_ENVIRONMENT_VARIABLE = "GLEW_CREATE_CLEAN_GENESIS"
CREATED_ACTION = "created_clean_genesis"
RESTORED_ACTION = "cold_restored_existing"
_IMPLEMENTATION_AUTHORITY = "upstream_and_field_operator_bundle_only"
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")


class RuntimeConformanceError(RuntimeError):
    """A required runtime fact is absent, inconsistent, or uncertified."""


@dataclass(frozen=True, slots=True)
class RuntimeConfiguration:
    """Locations and explicit first-boot authority for one clean generation."""

    genesis_root: Path
    expected_identity: str | None = None
    profile_path: Path = DEFAULT_PROFILE_PATH
    create_clean_genesis: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.genesis_root, Path):
            raise TypeError("genesis_root must be pathlib.Path")
        if not isinstance(self.profile_path, Path):
            raise TypeError("profile_path must be pathlib.Path")
        if not isinstance(self.create_clean_genesis, bool):
            raise TypeError("create_clean_genesis must be bool")
        if self.expected_identity is not None and (
            not isinstance(self.expected_identity, str)
            or not self.expected_identity
            or self.expected_identity != self.expected_identity.strip()
        ):
            raise RuntimeConformanceError(
                "expected clean-generation identity is noncanonical"
            )

    @classmethod
    def from_environment(
        cls, environment: Mapping[str, str] | None = None
    ) -> "RuntimeConfiguration":
        source = os.environ if environment is None else environment
        root = source.get(ROOT_ENVIRONMENT_VARIABLE)
        if not root:
            raise RuntimeConformanceError(
                f"{ROOT_ENVIRONMENT_VARIABLE} is required; legacy discovery and "
                "migration are forbidden"
            )
        creation = source.get(CREATE_ENVIRONMENT_VARIABLE, "0")
        if creation not in ("0", "1"):
            raise RuntimeConformanceError(
                f"{CREATE_ENVIRONMENT_VARIABLE} must be exactly 0 or 1"
            )
        profile = source.get(PROFILE_ENVIRONMENT_VARIABLE)
        identity = source.get(IDENTITY_ENVIRONMENT_VARIABLE)
        return cls(
            genesis_root=Path(root),
            expected_identity=identity or None,
            profile_path=Path(profile) if profile else DEFAULT_PROFILE_PATH,
            create_clean_genesis=creation == "1",
        )


def _strict_json(data: bytes, description: str) -> dict[str, Any]:
    def reject_constant(value: str) -> None:
        raise ValueError(f"non-finite JSON constant {value!r}")

    def reject_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"duplicate JSON key {key!r}")
            result[key] = value
        return result

    try:
        value = json.loads(
            data.decode("utf-8"),
            parse_constant=reject_constant,
            object_pairs_hook=reject_duplicates,
        )
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as error:
        raise RuntimeConformanceError(
            f"{description} is not strict UTF-8 JSON: {error}"
        ) from error
    if not isinstance(value, dict):
        raise RuntimeConformanceError(f"{description} root is not an object")
    return value


def _mapping(value: Any, description: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise RuntimeConformanceError(f"{description} is not an object")
    return value


def _digest(value: Any, description: str) -> str:
    if not isinstance(value, str) or _SHA256.fullmatch(value) is None:
        raise RuntimeConformanceError(f"{description} is not a SHA-256 digest")
    return value


def _report_hash(report: Mapping[str, Any]) -> str:
    encoded = (
        json.dumps(
            report,
            allow_nan=False,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )
        + "\n"
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def bind_startup_action(
    report: Mapping[str, Any], action: str
) -> dict[str, Any]:
    """Bind a startup receipt to a conformance report and re-hash it."""

    if action not in (CREATED_ACTION, RESTORED_ACTION):
        raise RuntimeConformanceError("startup action is not canonical")
    bound = dict(report)
    bound.pop("conformance_report_sha256", None)
    bound["startup_action"] = action
    bound["conformance_report_sha256"] = _report_hash(bound)
    return bound


def _backend_conformance(profile: Mapping[str, Any]) -> dict[str, Any]:
    facts = _mapping(profile.get("structural_facts"), "profile structural_facts")
    resonance = _mapping(facts.get("R_UF"), "profile R_UF")
    declared = _mapping(resonance.get("backend"), "profile R_UF backend")
    wheel_hash = _digest(
        declared.get("python_flint_wheel_sha256"),
        "profile python-flint wheel hash",
    )
    expected = (
        l6.PINNED_PYTHON_FLINT_VERSION,
        l6.PINNED_FLINT_VERSION,
        1,
    )
    if (
        declared.get("python_flint"),
        declared.get("flint"),
        declared.get("threads"),
    ) != expected:
        raise RuntimeConformanceError(
            "profile and fixed-42 provider disagree on the Arb runtime"
        )
    try:
        flint = importlib.import_module("flint")
    except ModuleNotFoundError as error:
        if error.name != "flint":
            raise
        raise RuntimeConformanceError("pinned python-flint is unavailable") from error
    observed = (
        getattr(flint, "__version__", None),
        getattr(flint, "__FLINT_VERSION__", None),
        getattr(getattr(flint, "ctx", None), "threads", None),
    )
    if observed != expected:
        raise RuntimeConformanceError(
            f"observed Arb runtime {observed!r} differs from {expected!r}"
        )
    with flint.ctx.workprec(l6.ARB_PRECISION_BITS):
        threshold = flint.arb(l6.N_START) / flint.arb(1).exp()
        if not (flint.arb(15) < threshold and threshold < flint.arb(16)):
            raise RuntimeConformanceError(
                "Arb did not uniquely certify 15 < 42/exp(1) < 16"
            )
        threshold_ball = threshold.str(40)
    adapter_bytes = Path(l6.__file__).read_bytes()
    return {
        "adapter_sha256": hashlib.sha256(adapter_bytes).hexdigest(),
        "arb_capture_certificate": {
            "expression": "15 < 42/exp(1) < 16",
            "precision_bits": l6.ARB_PRECISION_BITS,
            "threshold_ball": threshold_ball,
            "uniquely_certified": True,
        },
        "flint_version": observed[1],
        "python_flint_version": observed[0],
        "python_flint_wheel_sha256": wheel_hash,
        "threads": observed[2],
    }


def _fixed42_conformance(state: Mapping[str, Any]) -> dict[str, Any]:
    fixed42 = _mapping(state.get("fixed42"), "genesis fixed42")
    rank = _mapping(fixed42.get("rank_receipt"), "genesis rank receipt")
    evaluation = _mapping(fixed42.get("evaluation"), "genesis L6 evaluation")
    expected_rank = {
        "n_start": 42,
        "row_count": 0,
        "rank": 0,
        "n_effective": 42,
        "pivot_columns": [],
    }
    if (
        fixed42.get("rows") != []
        or fixed42.get("matrix_shape") != [0, 42]
        or dict(rank) != expected_rank
    ):
        raise RuntimeConformanceError("fixed-42 genesis is not exact quiescence")
    if (
        evaluation.get("status") != "unknown_no_lock"
        or evaluation.get("structural_lock") is not None
    ):
        raise RuntimeConformanceError("empty fixed-42 state did not fail closed")
    return {
        "ambient_columns": 42,
        "current_evaluation": {
            "status": "unknown_no_lock",
            "structural_lock": None,
        },
        "current_matrix_shape": [0, 42],
        "current_row_count": 0,
        "current_state": "empty_quiescent_no_constraint_rows",
        "rank_receipt": expected_rank,
        "zero_rows_fabricated": False,
    }


def _field_facts(state: Mapping[str, Any]) -> dict[str, Any]:
    current = _mapping(state.get("structural_facts"), "genesis structural_facts")
    result: dict[str, Any] = {}
    for name in ("S_UF", "R_UF"):
        fact = _mapping(current.get(name), f"genesis {name}")
        if (
            fact.get("status") != "unknown"
            or fact.get("value") is not None
            or not isinstance(fact.get("reason"), str)
            or not fact.get("reason")
        ):
            raise RuntimeConformanceError(
                f"clean genesis {name} is not explicit unknown"
            )
        result[name] = dict(fact)
    return {
        "current_evaluation": "quiescent_no_admitted_evidence",
        "current_facts": result,
        "dsf_field_reduced": False,
        "full_field_preserved": True,
    }


def _field_operator_marker(state: Mapping[str, Any]) -> dict[str, Any]:
    marker = _mapping(
        state.get("field_operator_conformance"),
        "genesis field_operator_conformance",
    )
    topology = _mapping(
        state.get("mounted_field_topology"), "genesis mounted_field_topology"
    )
    report_sha256 = _digest(
        marker.get("report_sha256"), "genesis field conformance report"
    )
    topology_sha256 = _digest(
        topology.get("authority_receipt_sha256"),
        "genesis empty topology receipt",
    )
    if (
        marker.get("schema") != "glew.field.operator_conformance.v1"
        or marker.get("status") != FIELD_OPERATOR_STATUS
        or topology.get("available") is not False
        or topology.get("dimension") != 0
        or topology.get("ordered_port_fibers") != []
        or topology.get("fiber_dimension") != field.FIBER_DIMENSION
    ):
        raise RuntimeConformanceError(
            "genesis field operator or empty topology marker is invalid"
        )
    return {
        "empty_genesis": {
            "available": False,
            "dimension": 0,
            "topology_receipt_sha256": topology_sha256,
        },
        "live_mounted_topology": False,
        "report_sha256": report_sha256,
        "schema": marker["schema"],
        "status": FIELD_OPERATOR_STATUS,
    }


def _cold_restore(configuration: RuntimeConfiguration):
    arguments = {
        "profile_path": configuration.profile_path,
        "fixed42_provider": l6,
        "field_provider": field,
    }
    if configuration.expected_identity is None:
        return discover_and_restore_clean_genesis(
            configuration.genesis_root,
            **arguments,
        )
    return restore_clean_genesis(
        configuration.genesis_root,
        expected_identity=configuration.expected_identity,
        **arguments,
    )


def run_conformance(configuration: RuntimeConfiguration) -> dict[str, Any]:
    """Cold-restore and return one deterministic, truthful runtime report."""

    if not isinstance(configuration, RuntimeConfiguration):
        raise TypeError("configuration must be RuntimeConfiguration")
    try:
        restored = _cold_restore(configuration)
    except GenesisError as error:
        raise RuntimeConformanceError(
            f"clean genesis cold restore failed: {error}"
        ) from error
    profile = _strict_json(
        restored.generation.stored_bytes(PROFILE_FILE), "restored exact profile"
    )
    authority = _mapping(profile.get("authority"), "profile authority")
    if (
        authority.get("full_glew_language_commit_authority") is not False
        or authority.get("implementation_authority") != _IMPLEMENTATION_AUTHORITY
    ):
        raise RuntimeConformanceError(
            "profile exceeds or differs from ratified operator authority"
        )
    state = restored.generation.payload(STATE_FILE)
    if not isinstance(state, Mapping):
        raise RuntimeConformanceError("restored state is not an object")
    if state.get("downstream_field_evolution") != FIELD_OPERATOR_STATUS:
        raise RuntimeConformanceError("genesis field operator marker is absent")
    receipt = restored.receipt
    report: dict[str, Any] = {
        "backend": _backend_conformance(profile),
        "conformant": True,
        "field_authority": _field_facts(state),
        "field_evolution": _field_operator_marker(state),
        "fixed42": _fixed42_conformance(state),
        "full_glew_language_commit_authority": False,
        "genesis": {
            "generation_uuid": receipt.generation_uuid,
            "identity": receipt.identity,
            "manifest_sha256": receipt.manifest_sha256,
            "recovery_certificate_sha256": receipt.recovery_certificate_sha256,
            "tick": restored.generation.tick,
        },
        "legacy_conversation_routed_through_glew": False,
        "profile": {
            "profile_id": profile.get("profile_id"),
            "sha256": receipt.profile_sha256,
            "version": profile.get("version"),
        },
        "schema": SCHEMA,
        "scope": "clean_genesis_and_ratified_GLEW_operator_runtime_only",
    }
    report["conformance_report_sha256"] = _report_hash(report)
    return report


def _root_is_empty_or_absent(root: Path) -> bool:
    try:
        info = root.lstat()
    except FileNotFoundError:
        return True
    except OSError as error:
        raise RuntimeConformanceError(
            f"clean genesis root cannot be inspected: {error}"
        ) from error
    if not stat.S_ISDIR(info.st_mode) or root.is_symlink():
        raise RuntimeConformanceError(
            "clean genesis root must be an absent path or a real directory"
        )
    try:
        return not any(root.iterdir())
    except OSError as error:
        raise RuntimeConformanceError(
            f"clean genesis root contents cannot be inspected: {error}"
        ) from error


@contextlib.contextmanager
def _bootstrap_lock(root: Path) -> Iterator[None]:
    parent = root.parent
    if parent == root or not root.name:
        raise RuntimeConformanceError("filesystem root cannot be a genesis root")
    try:
        parent_info = parent.lstat()
    except OSError as error:
        raise RuntimeConformanceError(
            f"clean genesis parent cannot be inspected: {error}"
        ) from error
    if not stat.S_ISDIR(parent_info.st_mode) or parent.is_symlink():
        raise RuntimeConformanceError(
            "clean genesis parent must be an existing real directory"
        )
    lock_path = parent / f".{root.name}.clean-genesis-bootstrap.lock"
    flags = os.O_RDWR | os.O_CREAT
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(lock_path, flags, 0o600)
    except OSError as error:
        raise RuntimeConformanceError(
            f"clean genesis bootstrap lock cannot be opened: {error}"
        ) from error
    try:
        lock_info = os.fstat(descriptor)
        if not stat.S_ISREG(lock_info.st_mode) or lock_info.st_nlink != 1:
            raise RuntimeConformanceError(
                "clean genesis bootstrap lock is not a private regular file"
            )
        os.fchmod(descriptor, 0o600)
        fcntl.flock(descriptor, fcntl.LOCK_EX)
        yield
    finally:
        with contextlib.suppress(OSError):
            fcntl.flock(descriptor, fcntl.LOCK_UN)
        os.close(descriptor)


def run_startup_conformance(
    configuration: RuntimeConfiguration,
) -> dict[str, Any]:
    """Optionally create exactly one clean genesis, then cold-conform it."""

    if not isinstance(configuration, RuntimeConfiguration):
        raise TypeError("configuration must be RuntimeConfiguration")
    action = RESTORED_ACTION
    if configuration.create_clean_genesis:
        with _bootstrap_lock(configuration.genesis_root):
            if _root_is_empty_or_absent(configuration.genesis_root):
                if configuration.expected_identity is not None:
                    raise RuntimeConformanceError(
                        "clean creation cannot promise a pre-existing identity"
                    )
                try:
                    create_clean_genesis(
                        configuration.genesis_root,
                        profile_path=configuration.profile_path,
                        fixed42_provider=l6,
                        field_provider=field,
                    )
                except GenesisError as error:
                    raise RuntimeConformanceError(
                        f"clean genesis creation failed: {error}"
                    ) from error
                action = CREATED_ACTION
            report = run_conformance(configuration)
    else:
        report = run_conformance(configuration)
    return bind_startup_action(report, action)


def _failed_report(error: Exception) -> dict[str, Any]:
    report: dict[str, Any] = {
        "conformant": False,
        "error": {"kind": type(error).__name__, "reason": str(error)},
        "full_glew_language_commit_authority": False,
        "legacy_conversation_routed_through_glew": False,
        "schema": SCHEMA,
        "scope": "clean_genesis_and_ratified_GLEW_operator_runtime_only",
    }
    report["conformance_report_sha256"] = _report_hash(report)
    return report


def main(arguments: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Cold-restore and verify one clean GLEW generation."
    )
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--identity")
    parser.add_argument("--profile", type=Path, default=DEFAULT_PROFILE_PATH)
    parsed = parser.parse_args(arguments)
    try:
        report = run_conformance(
            RuntimeConfiguration(
                genesis_root=parsed.root,
                expected_identity=parsed.identity,
                profile_path=parsed.profile,
            )
        )
        status = 0
    except (RuntimeConformanceError, OSError, ValueError, TypeError) as error:
        report = _failed_report(error)
        status = 1
    sys.stdout.write(
        json.dumps(report, allow_nan=False, ensure_ascii=False, indent=2, sort_keys=True)
        + "\n"
    )
    return status


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "CREATE_ENVIRONMENT_VARIABLE",
    "CREATED_ACTION",
    "DEFAULT_PROFILE_PATH",
    "IDENTITY_ENVIRONMENT_VARIABLE",
    "PROFILE_ENVIRONMENT_VARIABLE",
    "RESTORED_ACTION",
    "ROOT_ENVIRONMENT_VARIABLE",
    "RuntimeConfiguration",
    "RuntimeConformanceError",
    "bind_startup_action",
    "main",
    "run_conformance",
    "run_startup_conformance",
]
