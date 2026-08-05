"""Clean genesis for the ratified executable GLEW operator bundle.

The field operator is executable, but clean genesis mounts no port topology.
Its direct-sum field dimension is therefore exactly zero and it contains no
field state or evolution event.  No fixed 24/144 dimensional surface, hash-QR
projection, fixed integration schedule, entropy, mode, commit, or output
authority is implied by this checkpoint.
"""

from __future__ import annotations

import hashlib
import json
import os
import stat
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from dsf_ai_service.substrate.immutable_generation_store import (
    CURRENT_NAME,
    CurrentPointerError,
    GenerationStoreError,
    ImmutableGenerationStore,
    LoadedGeneration,
)


PROFILE_SCHEMA = "glew.upstream.executable_profile.v1"
PROFILE_ID = "guala.glew.upstream.executable.v1"
CHECKPOINT_SCHEMA = "glew.upstream.genesis.v1"
GENESIS_KIND = "clean_generation_genesis"
IDENTITY_SCHEMA = "guala.glew.identity_provenance.v1"
RECEIPT_REGISTRY_SCHEMA = "glew.receipt_registry_binding.v1"
L6_GENESIS_SCHEMA = "guala.glew.fixed42_genesis.v1"
FIELD_TOPOLOGY_SCHEMA = "glew.field.genesis_topology.v1"
FIELD_OPERATOR_STATUS = "operator_conformant_no_live_mounted_topology"
PROFILE_FILE = "profile/exact_profile.bin"
EMPTY_TOPOLOGY_RECEIPT_FILE = "field/empty_topology_receipt.bin"
STATE_FILE = "state.json"
REQUIRED_FILES = (EMPTY_TOPOLOGY_RECEIPT_FILE, PROFILE_FILE, STATE_FILE)

_EXPECTED_LANES = (
    "language",
    "sight",
    "sound",
    "touch",
    "smell",
    "taste",
)
_EXPECTED_FIELDS = (
    "D_k",
    "M_k",
    "R_rev_k",
    "U_star_k",
    "C_k",
    "P_k",
    "B_k",
)
_EXPECTED_TRANSPORT_COORDINATES = (
    "TVR_T",
    "TVR_V",
    "TVR_R",
    "w_k",
    "CV_T",
    "CV_V",
    "CV_R",
    "S_k",
    "U_k",
    "IAS_k",
    "URF_k",
    "D_k",
    "M_k",
    "R_rev_k",
    "U_star_k",
    "C_k",
    "P_k",
    "B_k",
    "N_gate",
)
_REQUIRED_PROHIBITIONS = frozenset(
    {
        "legacy_state_import",
        "compatibility_loader",
        "machine_learning",
        "probabilistic_or_heuristic_substitution",
        "native_port_averaging_selection_or_scalar_flattening",
        "DSF_field_weighted_sum_or_score_authority",
        "lookup_language_or_vocabulary_authority",
        "unratified_24_node_or_144_dimension_runtime_authority",
        "hash_derived_projection_or_QR",
        "fixed_step_or_per_gate_integration_count",
        "dimension_from_lane_count_without_mounted_ports",
        "zero_constraint_rows",
    }
)


class GenesisError(RuntimeError):
    """Base error for clean genesis construction or cold restoration."""


class GenesisAuthorityError(GenesisError):
    """A required executable authority is absent or inconsistent."""


class GenesisStateError(GenesisError):
    """The genesis root or immutable checkpoint violates the clean contract."""


@dataclass(frozen=True)
class GenesisReceipt:
    """Externally retainable identity and immutable recovery evidence."""

    identity: str
    generation_uuid: str
    profile_sha256: str
    manifest_sha256: str
    recovery_certificate_sha256: str


@dataclass(frozen=True)
class RestoredGenesis:
    """A verified cold-restored clean genesis and its receipt."""

    generation: LoadedGeneration
    receipt: GenesisReceipt


def _reject_constant(value: str) -> None:
    raise ValueError(f"non-finite JSON constant {value!r} is forbidden")


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key {key!r} is forbidden")
        result[key] = value
    return result


def _canonical_json(value: Any) -> bytes:
    try:
        return (
            json.dumps(
                value,
                allow_nan=False,
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
            + "\n"
        ).encode("utf-8")
    except (TypeError, ValueError) as error:
        raise GenesisStateError(
            f"genesis value is not canonical JSON: {error}"
        ) from error


def _operator_canonical_bytes(value: Any) -> bytes:
    try:
        return json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
    except (TypeError, ValueError) as error:
        raise GenesisAuthorityError(
            f"operator receipt is not canonical JSON: {error}"
        ) from error


def _mapping_at(value: Any, path: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise GenesisAuthorityError(f"profile {path} must be an object")
    return value


def _load_profile(profile_path: str | os.PathLike[str]) -> tuple[bytes, dict]:
    path = Path(profile_path)
    try:
        info = path.stat()
        profile_bytes = path.read_bytes()
    except OSError as error:
        raise GenesisAuthorityError(
            f"exact executable profile cannot be read: {error}"
        ) from error
    if not stat.S_ISREG(info.st_mode):
        raise GenesisAuthorityError("exact executable profile is not a regular file")
    try:
        profile = json.loads(
            profile_bytes.decode("utf-8"),
            parse_constant=_reject_constant,
            object_pairs_hook=_reject_duplicate_keys,
        )
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as error:
        raise GenesisAuthorityError(
            f"exact executable profile is not strict UTF-8 JSON: {error}"
        ) from error
    if not isinstance(profile, dict):
        raise GenesisAuthorityError("exact executable profile root must be an object")
    if _canonical_json(profile) != profile_bytes:
        raise GenesisAuthorityError(
            "exact executable profile bytes are not recursively sorted, two-space "
            "indented canonical JSON with one trailing LF"
        )
    _validate_profile_contract(profile)
    return profile_bytes, profile


def _validate_profile_contract(profile: Mapping[str, Any]) -> None:
    if profile.get("schema") != PROFILE_SCHEMA:
        raise GenesisAuthorityError("profile is not the executable upstream schema")
    if profile.get("profile_id") != PROFILE_ID:
        raise GenesisAuthorityError("profile identity is not the executable bundle")
    if not isinstance(profile.get("version"), str) or not profile["version"]:
        raise GenesisAuthorityError("executable profile version is missing")

    authority = _mapping_at(profile.get("authority"), "authority")
    if authority.get("architecture_status") != "ratified_executable":
        raise GenesisAuthorityError("profile architecture is not ratified executable")
    if (
        authority.get("implementation_authority")
        != "upstream_and_field_operator_bundle_only"
    ):
        raise GenesisAuthorityError("profile implementation scope is not exact")
    if authority.get("full_glew_language_commit_authority") is not False:
        raise GenesisAuthorityError(
            "executable profile must deny full language-commit authority"
        )
    ratification = _mapping_at(profile.get("ratification"), "ratification")
    if ratification.get("status") != "ratified_executable_bundle":
        raise GenesisAuthorityError("profile bundle is not ratified executable")

    downstream = _mapping_at(profile.get("downstream"), "downstream")
    if downstream.get("field_evolution") != FIELD_OPERATOR_STATUS:
        raise GenesisAuthorityError("profile field operator status is not executable")
    if downstream.get("full_GLEW_commit") != "forbidden":
        raise GenesisAuthorityError("profile does not forbid full GLEW commits")

    field_operator = _mapping_at(profile.get("field_operator"), "field_operator")
    if field_operator.get("fiber_dimension") != 19:
        raise GenesisAuthorityError("profile port-fiber dimension is not exact 19")
    if tuple(field_operator.get("coordinate_order_per_port", ())) != (
        _EXPECTED_TRANSPORT_COORDINATES
    ):
        raise GenesisAuthorityError("profile transport coordinate order is not exact")
    conformance = _mapping_at(
        field_operator.get("conformance"), "field_operator.conformance"
    )
    if (
        conformance.get("schema") != "glew.field.operator_conformance.v1"
        or conformance.get("status") != FIELD_OPERATOR_STATUS
    ):
        raise GenesisAuthorityError("profile field conformance contract is incomplete")
    if "exact_direct_identity_inclusion" not in str(
        field_operator.get("map_inject", "")
    ):
        raise GenesisAuthorityError("profile MapInject is not direct identity inclusion")
    evolution = _mapping_at(
        field_operator.get("evolution"), "field_operator.evolution"
    )
    if evolution.get("equation") != (
        "dpsi_dt=(diag(growth-decay)-i*H/hbar)*psi+J"
    ):
        raise GenesisAuthorityError("profile field equation is not exact")
    if "external_derivation_or_measurement_provenance" not in str(
        evolution.get("physical_profile_authority", "")
    ):
        raise GenesisAuthorityError(
            "profile field physics lacks external derivation authority"
        )

    fixed42 = _mapping_at(profile.get("fixed42"), "fixed42")
    if fixed42.get("ambient_columns") != 42:
        raise GenesisAuthorityError("profile fixed-42 ambient dimension is invalid")
    if tuple(fixed42.get("lane_order", ())) != _EXPECTED_LANES:
        raise GenesisAuthorityError("profile fixed-42 lane order is not canonical")
    if tuple(fixed42.get("field_order", ())) != _EXPECTED_FIELDS:
        raise GenesisAuthorityError("profile fixed-42 field order is not canonical")

    structural_facts = _mapping_at(
        profile.get("structural_facts"), "structural_facts"
    )
    if not isinstance(structural_facts.get("S_UF"), Mapping):
        raise GenesisAuthorityError("profile S_UF operator is missing")
    if not isinstance(structural_facts.get("R_UF"), Mapping):
        raise GenesisAuthorityError("profile R_UF operator is missing")
    native = _mapping_at(profile.get("native_evidence"), "native_evidence")
    if "no_averaging_selection_or_scalar_flattening" not in str(
        native.get("multi_port_rule", "")
    ):
        raise GenesisAuthorityError("profile does not preserve native multi-port evidence")
    typed = _mapping_at(profile.get("typed_language"), "typed_language")
    if "exact_unit_event_relevance_one" not in str(typed.get("relevance", "")):
        raise GenesisAuthorityError("typed-language relevance authority is missing")
    forbidden = profile.get("forbidden")
    if not isinstance(forbidden, list) or not _REQUIRED_PROHIBITIONS.issubset(forbidden):
        raise GenesisAuthorityError("executable profile prohibitions are incomplete")


def _enum_value(value: Any, description: str) -> str:
    result = getattr(value, "value", None)
    if not isinstance(result, str) or not result:
        raise GenesisAuthorityError(f"fixed-42 provider {description} is invalid")
    return result


def _fixed42_genesis(fixed42_provider: object | None) -> dict[str, Any]:
    if fixed42_provider is None:
        raise GenesisAuthorityError("canonical fixed-42 provider is required")
    required = (
        "LANE_ORDER",
        "FIELD_ORDER",
        "N_START",
        "Fixed42ConstraintStack",
        "fixed42_column",
        "exact_rank_receipt",
        "evaluate_l6",
    )
    missing = tuple(name for name in required if not hasattr(fixed42_provider, name))
    if missing:
        raise GenesisAuthorityError(
            f"fixed-42 provider is missing required authority: {missing}"
        )
    lanes = tuple(
        _enum_value(value, "lane") for value in fixed42_provider.LANE_ORDER
    )
    fields = tuple(
        _enum_value(value, "field") for value in fixed42_provider.FIELD_ORDER
    )
    if lanes != _EXPECTED_LANES or fields != _EXPECTED_FIELDS:
        raise GenesisAuthorityError("fixed-42 provider basis order is not canonical")
    if fixed42_provider.N_START != 42:
        raise GenesisAuthorityError("fixed-42 provider ambient dimension is not 42")
    for expected_column, (lane, field) in enumerate(
        (lane, field)
        for lane in fixed42_provider.LANE_ORDER
        for field in fixed42_provider.FIELD_ORDER
    ):
        try:
            actual_column = fixed42_provider.fixed42_column(lane, field)
        except Exception as error:
            raise GenesisAuthorityError(
                f"fixed-42 provider rejected canonical column: {error}"
            ) from error
        if actual_column != expected_column:
            raise GenesisAuthorityError("fixed-42 column mapping is not canonical")
    try:
        stack = fixed42_provider.Fixed42ConstraintStack(())
        rank = fixed42_provider.exact_rank_receipt(stack)
        evaluation = fixed42_provider.evaluate_l6(stack)
    except Exception as error:
        raise GenesisAuthorityError(
            f"fixed-42 provider rejected empty genesis: {error}"
        ) from error
    expected_rank = {
        "n_start": 42,
        "row_count": 0,
        "rank": 0,
        "n_effective": 42,
        "pivot_columns": (),
    }
    if {key: getattr(rank, key, None) for key in expected_rank} != expected_rank:
        raise GenesisAuthorityError("fixed-42 empty rank receipt is invalid")
    status = _enum_value(getattr(evaluation, "status", None), "status")
    if status != "unknown_no_lock" or evaluation.structural_lock is not None:
        raise GenesisAuthorityError("empty fixed-42 stack did not fail closed")
    if getattr(evaluation, "rank_receipt", None) != rank:
        raise GenesisAuthorityError("fixed-42 rank receipts disagree")
    reason = getattr(evaluation, "reason", None)
    if not isinstance(reason, str) or not reason:
        raise GenesisAuthorityError("fixed-42 unknown result has no reason")
    columns = [
        {"field": field, "index": index, "lane": lane}
        for index, (lane, field) in enumerate(
            (lane, field) for lane in lanes for field in fields
        )
    ]
    return {
        "schema": L6_GENESIS_SCHEMA,
        "column_basis": columns,
        "evaluation": {
            "reason": reason,
            "status": status,
            "structural_lock": None,
        },
        "matrix_shape": [0, 42],
        "rank_receipt": {
            "n_effective": rank.n_effective,
            "n_start": rank.n_start,
            "pivot_columns": list(rank.pivot_columns),
            "rank": rank.rank,
            "row_count": rank.row_count,
        },
        "rows": [],
    }


def _field_genesis(
    field_provider: object | None,
) -> tuple[dict[str, Any], dict[str, Any], bytes]:
    if field_provider is None:
        raise GenesisAuthorityError("canonical field provider is required")
    required = (
        "FIBER_DIMENSION",
        "TRANSPORT_COORDINATE_ORDER",
        "field_conformance",
        "field_topology_receipt_payload",
    )
    missing = tuple(name for name in required if not hasattr(field_provider, name))
    if missing:
        raise GenesisAuthorityError(
            f"field provider is missing required authority: {missing}"
        )
    if field_provider.FIBER_DIMENSION != 19:
        raise GenesisAuthorityError("field provider fiber dimension is not exact 19")
    if tuple(field_provider.TRANSPORT_COORDINATE_ORDER) != (
        _EXPECTED_TRANSPORT_COORDINATES
    ):
        raise GenesisAuthorityError("field provider coordinate order is not exact")
    try:
        report = field_provider.field_conformance()
        topology_payload = field_provider.field_topology_receipt_payload(
            "empty-genesis", ()
        )
    except Exception as error:
        raise GenesisAuthorityError(
            f"field operator conformance failed: {error}"
        ) from error
    if not isinstance(report, dict):
        raise GenesisAuthorityError("field conformance report is not an object")
    report_sha256 = report.get("report_sha256")
    body = {key: value for key, value in report.items() if key != "report_sha256"}
    if report_sha256 != hashlib.sha256(_operator_canonical_bytes(body)).hexdigest():
        raise GenesisAuthorityError("field conformance report digest is invalid")
    if (
        report.get("schema") != "glew.field.operator_conformance.v1"
        or report.get("status") != FIELD_OPERATOR_STATUS
        or report.get("live_mounted_topology") is not False
    ):
        raise GenesisAuthorityError("field conformance disposition is invalid")
    if tuple(report.get("coordinate_order", ())) != _EXPECTED_TRANSPORT_COORDINATES:
        raise GenesisAuthorityError("field conformance coordinate order differs")
    empty = report.get("empty_genesis")
    if not isinstance(empty, dict):
        raise GenesisAuthorityError("field conformance has no empty genesis receipt")
    topology_digest = hashlib.sha256(topology_payload).hexdigest()
    if empty != {
        "available": False,
        "dimension": 0,
        "topology_receipt_sha256": topology_digest,
    }:
        raise GenesisAuthorityError("field conformance empty topology is invalid")
    one_port = report.get("one_port_vector")
    if (
        not isinstance(one_port, dict)
        or one_port.get("dimension") != 19
        or one_port.get("expected_integrated_charge") != "3/2"
    ):
        raise GenesisAuthorityError("field conformance did not prove one 19-fiber")
    backend = report.get("backend")
    if not isinstance(backend, dict) or backend != {
        "flint": "3.6.0",
        "precision_bits": 256,
        "python_flint": "0.9.0",
        "threads": 1,
        "wheel_sha256": (
            "376b88cacd30612479e839ffdba887599d3f9c8c0e214852bf80bb2b194e4d76"
        ),
    }:
        raise GenesisAuthorityError("field conformance backend is invalid")
    topology_state = {
        "schema": FIELD_TOPOLOGY_SCHEMA,
        "authority_receipt_sha256": topology_digest,
        "available": False,
        "dimension": 0,
        "exact_receipt_path": EMPTY_TOPOLOGY_RECEIPT_FILE,
        "fiber_dimension": 19,
        "ordered_port_fibers": [],
        "topology_id": "empty-genesis",
    }
    conformance_state = {
        "schema": report["schema"],
        "report_sha256": report_sha256,
        "status": report["status"],
    }
    return topology_state, conformance_state, topology_payload


def _new_identity() -> str:
    identity = uuid.uuid4()
    if identity.version != 4 or identity.variant != uuid.RFC_4122:
        raise GenesisStateError("identity source did not produce an RFC UUIDv4")
    return str(identity)


def _deterministic_generation_uuid(identity: str, profile_sha256: str) -> str:
    framed = (
        b"GLEW-EXECUTABLE-CLEAN-GENESIS\x00"
        + identity.encode("ascii")
        + b"\x00"
        + profile_sha256.encode("ascii")
    )
    raw = bytearray(hashlib.sha256(framed).digest()[:16])
    raw[6] = (raw[6] & 0x0F) | 0x80
    raw[8] = (raw[8] & 0x3F) | 0x80
    return str(uuid.UUID(bytes=bytes(raw)))


def _receipt_registry_binding(
    profile_sha256: str, topology_sha256: str
) -> dict[str, Any]:
    manifest = {
        "profile_binding_sha256": profile_sha256,
        "record_digests": [profile_sha256, topology_sha256],
        "schema": RECEIPT_REGISTRY_SCHEMA,
    }
    return {
        **manifest,
        "manifest_sha256": hashlib.sha256(_canonical_json(manifest)).hexdigest(),
    }


def _unknown_fact(reason: str) -> dict[str, Any]:
    return {"reason": reason, "status": "unknown", "value": None}


def _build_state(
    *,
    identity: str,
    profile: Mapping[str, Any],
    profile_sha256: str,
    profile_size: int,
    l6_state: Mapping[str, Any],
    topology_state: Mapping[str, Any],
    field_conformance_state: Mapping[str, Any],
) -> dict[str, Any]:
    topology_sha256 = topology_state["authority_receipt_sha256"]
    return {
        "schema": CHECKPOINT_SCHEMA,
        "checkpoint_kind": GENESIS_KIND,
        "disruption_recovery": {
            "baseline_established": False,
            "disruption_latched": False,
            "recovery_pending": False,
        },
        "downstream_field_evolution": FIELD_OPERATOR_STATUS,
        "faults": [],
        "field_operator_conformance": dict(field_conformance_state),
        "fixed42": dict(l6_state),
        "identity": {
            "schema": IDENTITY_SCHEMA,
            "entropy_provenance": {
                "algorithm": "RFC_4122_UUIDv4",
                "scope": "identity_only",
                "source": "operating_system_csprng",
            },
            "identity": identity,
            "lineage": [],
            "parent_identity": None,
        },
        "immutable_facts": [],
        "memory": [],
        "mounted_field_topology": dict(topology_state),
        "open_windows": [],
        "output": [],
        "per_port_phase_state": {},
        "profile_binding": {
            "exact_bytes_path": PROFILE_FILE,
            "profile_id": profile["profile_id"],
            "sha256": profile_sha256,
            "size_bytes": profile_size,
            "version": profile["version"],
        },
        "receipt_registry_binding": _receipt_registry_binding(
            profile_sha256, topology_sha256
        ),
        "source_time": {"ports": {}},
        "structural_facts": {
            "R_UF": _unknown_fact(
                "no_closed_receipted_grid_or_mounted_required_edge_graph"
            ),
            "S_UF": _unknown_fact(
                "no_closed_receipted_grid_or_mounted_required_port_domain"
            ),
        },
        "structural_time": {"exact_rational": "0/1", "gate_count": 0},
    }


def _require_unused_root(root: Path) -> None:
    if not root.exists():
        return
    try:
        info = root.lstat()
        entries = tuple(root.iterdir())
    except OSError as error:
        raise GenesisStateError(f"genesis root cannot be inspected: {error}") from error
    if not stat.S_ISDIR(info.st_mode) or root.is_symlink():
        raise GenesisStateError("genesis root must be a real directory")
    if entries:
        raise GenesisStateError(
            "clean genesis requires an unused root; existing state is never imported"
        )


def _require_existing_store_root(root: Path) -> None:
    try:
        info = root.lstat()
    except FileNotFoundError as error:
        raise GenesisStateError("cold genesis root is missing") from error
    except OSError as error:
        raise GenesisStateError(f"cold genesis root cannot be inspected: {error}") from error
    if not stat.S_ISDIR(info.st_mode) or root.is_symlink():
        raise GenesisStateError("cold genesis root must be a real directory")
    if not (root / CURRENT_NAME).exists() or not (root / "generations").is_dir():
        raise GenesisStateError("cold genesis root is not a published immutable store")


def _receipt(loaded: LoadedGeneration, profile_sha256: str) -> GenesisReceipt:
    return GenesisReceipt(
        identity=loaded.identity,
        generation_uuid=loaded.generation_uuid,
        profile_sha256=profile_sha256,
        manifest_sha256=loaded.manifest_sha256,
        recovery_certificate_sha256=hashlib.sha256(
            loaded.recovery_certificate_bytes()
        ).hexdigest(),
    )


def create_clean_genesis(
    root: str | os.PathLike[str],
    *,
    profile_path: str | os.PathLike[str],
    fixed42_provider: object | None,
    field_provider: object | None,
) -> GenesisReceipt:
    """Create, publish, and cold-verify one clean executable genesis."""

    profile_bytes, profile = _load_profile(profile_path)
    l6_state = _fixed42_genesis(fixed42_provider)
    topology_state, conformance_state, topology_payload = _field_genesis(
        field_provider
    )
    root_path = Path(root)
    _require_unused_root(root_path)
    identity = _new_identity()
    profile_sha256 = hashlib.sha256(profile_bytes).hexdigest()
    state_bytes = _canonical_json(
        _build_state(
            identity=identity,
            profile=profile,
            profile_sha256=profile_sha256,
            profile_size=len(profile_bytes),
            l6_state=l6_state,
            topology_state=topology_state,
            field_conformance_state=conformance_state,
        )
    )
    generation_uuid = _deterministic_generation_uuid(identity, profile_sha256)
    store = ImmutableGenerationStore(
        root_path,
        identity=identity,
        required_files=REQUIRED_FILES,
    )
    try:
        committed = store.commit(
            tick=0,
            generation_uuid=generation_uuid,
            files={
                EMPTY_TOPOLOGY_RECEIPT_FILE: topology_payload,
                PROFILE_FILE: profile_bytes,
                STATE_FILE: state_bytes,
            },
        )
    except (GenerationStoreError, OSError) as error:
        raise GenesisStateError(f"immutable genesis creation failed: {error}") from error
    restored = restore_clean_genesis(
        root_path,
        expected_identity=identity,
        profile_path=profile_path,
        fixed42_provider=fixed42_provider,
        field_provider=field_provider,
    )
    if committed.recovery_certificate_bytes() != (
        restored.generation.recovery_certificate_bytes()
    ):
        raise GenesisStateError("cold restore certificate differs from publication")
    return restored.receipt


def restore_clean_genesis(
    root: str | os.PathLike[str],
    *,
    expected_identity: str,
    profile_path: str | os.PathLike[str],
    fixed42_provider: object | None,
    field_provider: object | None,
) -> RestoredGenesis:
    """Cold-load CURRENT and verify every genesis byte against its authorities."""

    try:
        parsed_identity = uuid.UUID(expected_identity)
    except (ValueError, AttributeError) as error:
        raise GenesisStateError("expected identity is not a canonical UUID") from error
    if str(parsed_identity) != expected_identity or parsed_identity.version != 4:
        raise GenesisStateError("expected identity is not a canonical UUIDv4")
    profile_bytes, profile = _load_profile(profile_path)
    l6_state = _fixed42_genesis(fixed42_provider)
    topology_state, conformance_state, topology_payload = _field_genesis(
        field_provider
    )
    profile_sha256 = hashlib.sha256(profile_bytes).hexdigest()
    expected_state = _build_state(
        identity=expected_identity,
        profile=profile,
        profile_sha256=profile_sha256,
        profile_size=len(profile_bytes),
        l6_state=l6_state,
        topology_state=topology_state,
        field_conformance_state=conformance_state,
    )
    expected_generation_uuid = _deterministic_generation_uuid(
        expected_identity, profile_sha256
    )
    _require_existing_store_root(Path(root))
    store = ImmutableGenerationStore(
        root,
        identity=expected_identity,
        required_files=REQUIRED_FILES,
    )
    try:
        loaded = store.load_current()
    except (CurrentPointerError, GenerationStoreError, OSError) as error:
        raise GenesisStateError(f"cold genesis restore failed: {error}") from error
    if loaded.generation_uuid != expected_generation_uuid:
        raise GenesisStateError("genesis generation UUID is not identity-derived")
    if loaded.tick != 0:
        raise GenesisStateError("clean genesis tick is not zero")
    if loaded.stored_bytes(PROFILE_FILE) != profile_bytes:
        raise GenesisStateError("cold genesis exact profile bytes differ")
    if loaded.stored_bytes(EMPTY_TOPOLOGY_RECEIPT_FILE) != topology_payload:
        raise GenesisStateError("cold genesis empty topology receipt differs")
    if loaded.payload(STATE_FILE) != expected_state:
        raise GenesisStateError("cold genesis state differs from canonical emptiness")
    independently_verified = store.verify_generation(loaded.generation_uuid)
    if independently_verified.recovery_certificate_bytes() != (
        loaded.recovery_certificate_bytes()
    ):
        raise GenesisStateError("repeat verification certificate is not bit exact")
    return RestoredGenesis(
        generation=loaded,
        receipt=_receipt(loaded, profile_sha256),
    )


def discover_and_restore_clean_genesis(
    root: str | os.PathLike[str],
    *,
    profile_path: str | os.PathLike[str],
    fixed42_provider: object | None,
    field_provider: object | None,
) -> RestoredGenesis:
    """Discover a candidate identity, then perform complete cold verification."""

    root_path = Path(root)
    _require_existing_store_root(root_path)
    current_path = root_path / CURRENT_NAME
    try:
        info = current_path.lstat()
        current_bytes = current_path.read_bytes()
    except OSError as error:
        raise GenesisStateError(
            f"cold genesis CURRENT cannot be read: {error}"
        ) from error
    if (
        not stat.S_ISREG(info.st_mode)
        or stat.S_IMODE(info.st_mode) != 0o444
        or info.st_nlink != 1
    ):
        raise GenesisStateError(
            "cold genesis CURRENT is not an immutable regular file"
        )
    try:
        pointer = json.loads(
            current_bytes.decode("utf-8"),
            parse_constant=_reject_constant,
            object_pairs_hook=_reject_duplicate_keys,
        )
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as error:
        raise GenesisStateError(
            f"cold genesis CURRENT is not strict UTF-8 JSON: {error}"
        ) from error
    required_keys = {
        "schema",
        "generation_uuid",
        "identity",
        "tick",
        "generation_path",
        "manifest_sha256",
    }
    if not isinstance(pointer, dict) or set(pointer) != required_keys:
        raise GenesisStateError("cold genesis CURRENT has an invalid field set")
    if pointer.get("schema") != "immutable_generation_current_v1":
        raise GenesisStateError("cold genesis CURRENT schema is unsupported")
    if current_bytes != _canonical_json(pointer):
        raise GenesisStateError("cold genesis CURRENT is not canonical JSON")
    candidate_identity = pointer.get("identity")
    try:
        parsed_identity = uuid.UUID(candidate_identity)
    except (ValueError, AttributeError) as error:
        raise GenesisStateError(
            "cold genesis CURRENT identity is not a canonical UUID"
        ) from error
    if str(parsed_identity) != candidate_identity or parsed_identity.version != 4:
        raise GenesisStateError(
            "cold genesis CURRENT identity is not a canonical UUIDv4"
        )
    return restore_clean_genesis(
        root_path,
        expected_identity=candidate_identity,
        profile_path=profile_path,
        fixed42_provider=fixed42_provider,
        field_provider=field_provider,
    )


__all__ = [
    "CHECKPOINT_SCHEMA",
    "EMPTY_TOPOLOGY_RECEIPT_FILE",
    "FIELD_OPERATOR_STATUS",
    "FIELD_TOPOLOGY_SCHEMA",
    "GENESIS_KIND",
    "GenesisAuthorityError",
    "GenesisError",
    "GenesisReceipt",
    "GenesisStateError",
    "IDENTITY_SCHEMA",
    "L6_GENESIS_SCHEMA",
    "PROFILE_FILE",
    "PROFILE_ID",
    "PROFILE_SCHEMA",
    "RECEIPT_REGISTRY_SCHEMA",
    "REQUIRED_FILES",
    "RestoredGenesis",
    "STATE_FILE",
    "create_clean_genesis",
    "discover_and_restore_clean_genesis",
    "restore_clean_genesis",
]
