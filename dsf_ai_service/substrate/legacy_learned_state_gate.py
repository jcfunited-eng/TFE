"""Authenticated, byte-complete gate for pre-owner learned-state files.

The physical runtime cannot silently discard a path merely because the new
runtime no longer reads its legacy container.  This module classifies every
present pre-owner path that the persistence registry calls learned state.

Three dispositions exist:

``direct_owner_translation``
    The member is already an exact current owner-state field and every field
    in that owner group is present.  The gate emits the canonical target owner
    body and a trace from each source member to that body.

``sealed_nonactive_escrow``
    The source is a retired named-profile, scripted, Chi/Atlas, or raw-media
    authority.  Its bytes may remain only in the bounded sealed source
    generation; they cannot enter active cognition.

``unresolved_mixed_custody``
    The member may contain physical or learned evidence but has neither a
    lossless current-owner mapping nor an explicitly approved inactive archive
    disposition.  Any such member refuses migration.

The accounting is exact.  Every learned source file is measured once.  A
mixed teaching monolith is partitioned into canonical single-member records
plus its exact remaining container/framing bytes.  The category totals must
sum to the measured source bytes before a plan can be authenticated.
"""

from __future__ import annotations

import base64
import gzip
import hashlib
import hmac
import io
import json
import os
import stat
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path
from typing import Mapping

from dsf_ai_service.glew_runtime.global_uf import DSF_FIELD_ORDER
from dsf_ai_service.glew_runtime.sensory_full_field_boundary import (
    SENSE_ORDER,
)
from dsf_ai_service.substrate.auditory_reciprocity import (
    AUDITORY_RECIPROCITY_ENVELOPE_SCHEMA,
    AUDITORY_RECIPROCITY_SNAPSHOT_SCHEMA,
    MAX_DECODED_SNAPSHOT_BYTES,
    MAX_ENCODED_SNAPSHOT_BYTES,
    MAX_PATH_BRANCHES_PER_CLASS,
    MAX_RECIPROCAL_CLASSES_PER_KIND,
    inspect_legacy_v4_envelope,
)
from dsf_ai_service.substrate.owner_scoped_persistence import (
    ACTIVE_OWNER_STATE_KEYS,
    OWNER_STATE_BODY_SCHEMA,
    OWNER_STATE_GROUPS,
    PATH_OWNERSHIP_REGISTRY,
    ROLE_LEARNED,
    decode_owner_state_bodies,
    owner_state_body_mutation_root,
)
from dsf_ai_service.substrate.w1_anonymous_audiovisual_continuity import (
    W1AnonymousAudiovisualContinuityOwner,
)


GATE_SCHEMA = "guala.legacy_learned_state_gate.v1"
DIRECT = "direct_owner_translation"
ESCROW = "sealed_nonactive_escrow"
UNRESOLVED = "unresolved_mixed_custody"

_GATE_DOMAIN = b"guala-legacy-learned-state-gate-v1\0"
_HEX = frozenset("0123456789abcdef")
_LEGACY_ANONYMOUS_AV_SNAPSHOT_SCHEMA = (
    "guala.w1.anonymous_audiovisual_continuity.snapshot.v1"
)
_LEGACY_ANONYMOUS_AV_SNAPSHOT_DOMAIN = (
    b"guala.w1.anonymous_audiovisual_continuity.snapshot.v1\0"
)
_CURRENT_ANONYMOUS_AV_OWNER_ID = (
    "w1_anonymous_audiovisual_continuity"
)
_CURRENT_ANONYMOUS_AV_OWNER_PATH = (
    "owner_state/w1_companion_av_continuity.state"
)
_AUDITORY_V4_ARCHIVE_SCHEMA = (
    "guala.auditory.persistence_archive.v1"
)
_LEGACY_CAUSAL_ACTION_ENVELOPE_SCHEMA = (
    "guala.causal_action.hmac.v1"
)
_LEGACY_CAUSAL_ACTION_STATE_SCHEMA = (
    "guala.causal_action.state.v1"
)
_LEGACY_CAUSAL_ACTION_STATE_DOMAIN = (
    b"guala-causal-action-state-v1\0"
)
_LEGACY_CAUSAL_ACTION_TEACHER_RELATION_SCHEMA = (
    "guala.causal_action.teacher_relation.v1"
)
_LEGACY_CAUSAL_ACTION_TEACHER_DOMAIN = (
    b"guala-causal-action-teacher-v1\0"
)
_LEGACY_CAUSAL_ACTION_BINDING_SCHEMA = (
    "guala.causal_action.binding.v1"
)
_LEGACY_CAUSAL_ACTION_SEMANTIC_RELATION_SCHEMA = (
    "guala.causal_action.semantic_relation.v1"
)
_LEGACY_CAUSAL_ACTION_TRANSIENT_CAPACITY = 4
_LEGACY_CAUSAL_ACTION_ACTION_CAPACITY = 64
_LEGACY_CAUSAL_ACTION_WITNESS_CAPACITY = 128
_LEGACY_CAUSAL_ACTION_SCALAR_CAPACITY = 512
_LEGACY_CAUSAL_ACTION_ENCODED_BYTE_CAPACITY = 16 * 1024 * 1024
_LEGACY_EMBODIED_COMMAND_SCHEMA = "guala.embodiment.command.v1"
_EMBODIED_TEACHING_STATE_SCHEMA = (
    "guala.embodied_action_teaching.state.v1"
)
_EMBODIED_TEACHING_ENVELOPE_SCHEMA = (
    "guala.embodied_action_teaching.state.hmac.v1"
)
_EMBODIED_TEACHING_DEMONSTRATION_SCHEMA = (
    "guala.embodied_action_teaching.demonstration.v1"
)
_EMBODIED_TEACHING_STATE_DOMAIN = (
    b"guala-embodied-action-teaching-state-v1\0"
)
_EMBODIED_TEACHING_DEMONSTRATION_DOMAIN = (
    b"guala-embodied-action-demonstration-v1\0"
)
_CAUSAL_DELIBERATION_ENVELOPE_SCHEMA = (
    "guala.causal_deliberation.hmac.v2"
)
_CAUSAL_DELIBERATION_STATE_SCHEMA = (
    "guala.causal_deliberation.state.v2"
)
_CAUSAL_DELIBERATION_STATE_DOMAIN = (
    b"guala-causal-deliberation-state-v1\0"
)
_CAUSAL_DELIBERATION_WITNESS_SCHEMA = (
    "guala.causal_deliberation.witness.v1"
)
_LEGACY_CAUSAL_SETTLEMENT_SCHEMA = (
    "guala.exact_causal_experience.settlement.v4"
)
_LEGACY_CAUSAL_ACTION_CYCLE_ENVELOPE_SCHEMA = (
    "guala.causal_action_cycle.hmac.v2"
)
_LEGACY_CAUSAL_ACTION_CYCLE_STATE_SCHEMA = (
    "guala.causal_action_cycle.state.v2"
)
_LEGACY_CAUSAL_ACTION_CYCLE_STATE_DOMAIN = (
    b"guala-causal-action-cycle-state-v2\0"
)

_PRE_OWNER_LEARNED_SELECTORS = frozenset({
    "guala_visual.json",
    "guala_sight_motifs.json",
    "guala_sounds.json",
    "guala_videos.json",
    "guala_episodic.json",
    "guala_teaching.json",
})
_PRE_OWNER_LEARNED_PREFIXES = ("assets/", "sounds/")

# These mechanisms are forbidden as cognition but their exact source bytes
# remain migration evidence in the sealed, non-active source generation.
_RETIRED_TEACHING_MEMBERS = frozenset({
    "auditory_token_bindings",
    "causal_language",
    "causal_speech_release",
    "correction_log",
    "feedback_log",
    "latest_auditory_causal_language",
    "latest_auditory_token_sequence",
    "legacy_causal_prediction_disposition",
})

# These historical members may contain physical observations or learned
# receipts, but their old envelopes lack the custody needed by their current
# replacements.  Joseph explicitly requires their bytes to remain preserved
# while forbidding their legacy mechanisms from re-entering cognition.  They
# therefore enter the bounded authenticated non-active archive, not genesis
# translation and not deletion.
_INACTIVE_ARCHIVE_TEACHING_MEMBERS = frozenset({
    "anonymous_audiovisual_continuity",
    "causal_play_observation",
    "emission_records",
    "latest_auditory_causal_event",
    "live_anonymous_encounter_continuity",
})


class LegacyLearnedStateGateError(RuntimeError):
    """A learned source is malformed, unauthenticated, or unaccounted."""


class LegacyLearnedStateUnresolved(LegacyLearnedStateGateError):
    """The authenticated plan contains evidence with no lawful target."""

    def __init__(self, message: str, plan: "LegacyLearnedStatePlan"):
        super().__init__(message)
        self.plan = plan


def _canonical(value: object) -> bytes:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _legacy_canonical(value: object) -> bytes:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _sha(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _identity(value: object) -> str:
    if not isinstance(value, str) or not value:
        raise LegacyLearnedStateGateError(
            "learned-state source identity is absent"
        )
    return value


def _tick(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise LegacyLearnedStateGateError(
            "learned-state source tick is invalid"
        )
    return value


def _authority_key(value: bytes | bytearray | memoryview | str) -> bytes:
    raw = value.encode("utf-8") if isinstance(value, str) else bytes(value)
    if len(raw) < 16:
        raise LegacyLearnedStateGateError(
            "learned-state gate authority is too short"
        )
    return raw


def _regular_body(root: Path, relative_path: str) -> bytes:
    path = root / relative_path
    try:
        info = path.lstat()
    except FileNotFoundError as error:
        raise LegacyLearnedStateGateError(
            f"learned source disappeared: {relative_path}"
        ) from error
    if not stat.S_ISREG(info.st_mode) or path.is_symlink():
        raise LegacyLearnedStateGateError(
            f"learned source is not a regular file: {relative_path}"
        )
    body = path.read_bytes()
    if len(body) != info.st_size:
        raise LegacyLearnedStateGateError(
            f"learned source changed while read: {relative_path}"
        )
    return body


def _legacy_learned_paths(root: Path) -> tuple[str, ...]:
    registry = tuple(
        record
        for record in PATH_OWNERSHIP_REGISTRY
        if record.role == ROLE_LEARNED
        and (
            record.selector in _PRE_OWNER_LEARNED_SELECTORS
            or record.selector in _PRE_OWNER_LEARNED_PREFIXES
        )
    )
    paths: list[str] = []
    for directory, directory_names, file_names in os.walk(root):
        current = Path(directory)
        for name in directory_names:
            child = current / name
            if child.is_symlink():
                raise LegacyLearnedStateGateError(
                    "learned-state tree contains a directory symlink: "
                    + child.relative_to(root).as_posix()
                )
        for name in file_names:
            child = current / name
            relative = child.relative_to(root).as_posix()
            matches = [
                record for record in registry if record.matches(relative)
            ]
            if len(matches) == 1:
                paths.append(relative)
            elif len(matches) > 1:
                raise LegacyLearnedStateGateError(
                    f"learned source has overlapping owners: {relative}"
                )
    return tuple(sorted(paths))


def _decoded_legacy_envelope(
    body: bytes,
    *,
    relative_path: str,
    identity: str,
    tick: int,
) -> Mapping[str, object]:
    try:
        value = json.loads(body)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise LegacyLearnedStateGateError(
            f"learned JSON is unreadable: {relative_path}"
        ) from error
    expected = {
        "data",
        "guala_identity",
        "saved_at_tick",
        "saved_at_timestamp",
        "schema_version",
    }
    if not isinstance(value, dict) or set(value) != expected:
        raise LegacyLearnedStateGateError(
            f"learned JSON envelope changed: {relative_path}"
        )
    if (
        value["guala_identity"] != identity
        or value["saved_at_tick"] != tick
        or not isinstance(value["schema_version"], str)
        or not value["schema_version"]
        or not isinstance(value["saved_at_timestamp"], str)
        or not value["saved_at_timestamp"]
        or not isinstance(value["data"], dict)
    ):
        raise LegacyLearnedStateGateError(
            f"learned JSON authority differs: {relative_path}"
        )
    return value


def _member_record(
    *,
    source_path: str,
    member: str,
    value: object,
    category: str,
    reason: str,
    target_owner_id: str | None = None,
    target_path: str | None = None,
) -> dict[str, object]:
    encoded = _canonical({member: value})
    return {
        "accounted_bytes": len(encoded),
        "category": category,
        "member": member,
        "reason": reason,
        "source_member_sha256": _sha(encoded),
        "source_path": source_path,
        "target_owner_id": target_owner_id,
        "target_path": target_path,
    }


def _owner_groups_by_state_key() -> dict[str, object]:
    result = {}
    for group in OWNER_STATE_GROUPS:
        for key in group.state_keys:
            if key in result:
                raise LegacyLearnedStateGateError(
                    "current owner state key has overlapping owners"
                )
            result[key] = group
    if set(result) != set(ACTIVE_OWNER_STATE_KEYS):
        raise LegacyLearnedStateGateError(
            "current owner state-key registry changed"
        )
    return result


def _translate_legacy_anonymous_av_genesis(
    value: object,
    *,
    runtime,
) -> tuple[bytes | None, str]:
    """Authenticate v1 custody and translate only its exact empty genesis."""

    if runtime is None:
        raise LegacyLearnedStateGateError(
            "anonymous audiovisual continuity lacks runtime authority"
        )
    owner = getattr(
        runtime,
        "_w1_anonymous_av_continuity_owner",
        None,
    )
    physical_key = getattr(runtime, "_w1_physical_key", None)
    if (
        not isinstance(owner, W1AnonymousAudiovisualContinuityOwner)
        or not isinstance(getattr(owner, "_key", None), bytes)
        or not isinstance(physical_key, bytes)
    ):
        raise LegacyLearnedStateGateError(
            "anonymous audiovisual continuity runtime authority is absent"
        )
    if not isinstance(value, dict) or set(value) != {
        "authority_hmac_sha256",
        "authority_receipt_sha256",
        "payload",
    }:
        raise LegacyLearnedStateGateError(
            "anonymous audiovisual continuity v1 record changed"
        )
    payload = value.get("payload")
    if not isinstance(payload, dict) or set(payload) != {
        "generation",
        "latest",
        "schema",
        "settled",
        "transition_capacity",
        "transitions",
    }:
        raise LegacyLearnedStateGateError(
            "anonymous audiovisual continuity v1 payload changed"
        )
    supplied_hmac = value.get("authority_hmac_sha256")
    expected_hmac = hmac.new(
        owner._key,
        _LEGACY_ANONYMOUS_AV_SNAPSHOT_DOMAIN
        + _legacy_canonical(payload),
        hashlib.sha256,
    ).hexdigest()
    expected_receipt = _sha(_legacy_canonical({
        "authority_hmac_sha256": expected_hmac,
        "payload": payload,
    }))
    if (
        not isinstance(supplied_hmac, str)
        or not hmac.compare_digest(supplied_hmac, expected_hmac)
        or value.get("authority_receipt_sha256") != expected_receipt
        or payload.get("schema")
        != _LEGACY_ANONYMOUS_AV_SNAPSHOT_SCHEMA
    ):
        raise LegacyLearnedStateGateError(
            "anonymous audiovisual continuity v1 authentication failed"
        )
    exact_genesis = {
        "generation": 0,
        "latest": None,
        "schema": _LEGACY_ANONYMOUS_AV_SNAPSHOT_SCHEMA,
        "settled": 0,
        "transition_capacity": owner._max_transitions,
        "transitions": [],
    }
    if payload != exact_genesis:
        return None, (
            "authenticated v1 continuity contains learned lineage or "
            "transitions; v1 lacks the physical-custody fields required "
            "by the current v2 owner, so lossless promotion is unproved"
        )

    current = W1AnonymousAudiovisualContinuityOwner(
        authority_key=owner._key,
        physical_authority_key=physical_key,
        max_transitions=owner._max_transitions,
    )
    target = current.encoded_snapshot()
    current.restore_encoded(target)
    if current.encoded_snapshot() != target:
        raise LegacyLearnedStateGateError(
            "current anonymous audiovisual genesis did not restore exactly"
        )
    return target, (
        "authenticated v1 genesis contains zero learned observations; "
        "translated to byte-exact current v2 genesis"
    )


def _inspect_retired_auditory_reciprocity(
    value: object,
) -> dict[str, object]:
    """Prove bounded v5 integrity without granting cognition authority."""

    if not isinstance(value, dict) or set(value) != {
        "encoding",
        "payload",
        "payload_sha256",
        "schema",
    }:
        raise LegacyLearnedStateGateError(
            "retired auditory reciprocity envelope changed"
        )
    if (
        value.get("schema") != AUDITORY_RECIPROCITY_ENVELOPE_SCHEMA
        or value.get("encoding") != "gzip+base64"
    ):
        raise LegacyLearnedStateGateError(
            "retired auditory reciprocity schema changed"
        )
    encoded = value.get("payload")
    expected_sha = value.get("payload_sha256")
    if (
        not isinstance(encoded, str)
        or not encoded
        or len(encoded.encode("ascii", errors="ignore"))
        > MAX_ENCODED_SNAPSHOT_BYTES
        or not isinstance(expected_sha, str)
        or len(expected_sha) != 64
        or any(character not in _HEX for character in expected_sha)
    ):
        raise LegacyLearnedStateGateError(
            "retired auditory reciprocity boundary changed"
        )
    try:
        encoded_bytes = encoded.encode("ascii")
        compressed = base64.b64decode(encoded_bytes, validate=True)
        if base64.b64encode(compressed) != encoded_bytes:
            raise ValueError("noncanonical base64")
        with gzip.GzipFile(fileobj=io.BytesIO(compressed)) as stream:
            payload = stream.read(MAX_DECODED_SNAPSHOT_BYTES + 1)
    except Exception as error:
        raise LegacyLearnedStateGateError(
            "retired auditory reciprocity payload is unreadable"
        ) from error
    if (
        len(payload) > MAX_DECODED_SNAPSHOT_BYTES
        or _sha(payload) != expected_sha
    ):
        raise LegacyLearnedStateGateError(
            "retired auditory reciprocity integrity changed"
        )
    try:
        snapshot = json.loads(payload)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise LegacyLearnedStateGateError(
            "retired auditory reciprocity snapshot is unreadable"
        ) from error
    if _legacy_canonical(snapshot) != payload:
        raise LegacyLearnedStateGateError(
            "retired auditory reciprocity snapshot is not canonical"
        )
    if not isinstance(snapshot, dict) or set(snapshot) != {
        "branch_capacity_per_class",
        "class_capacity_per_kind",
        "classes",
        "schema",
        "source_continuity",
        "tutor_authority_required",
    }:
        raise LegacyLearnedStateGateError(
            "retired auditory reciprocity snapshot changed"
        )
    classes = snapshot.get("classes")
    if (
        snapshot.get("schema") != AUDITORY_RECIPROCITY_SNAPSHOT_SCHEMA
        or snapshot.get("branch_capacity_per_class")
        != MAX_PATH_BRANCHES_PER_CLASS
        or snapshot.get("class_capacity_per_kind")
        != MAX_RECIPROCAL_CLASSES_PER_KIND
        or snapshot.get("source_continuity")
        != "unavailable_without_receipted_stream_authority"
        or snapshot.get("tutor_authority_required") is not True
        or not isinstance(classes, list)
        or len(classes) > MAX_RECIPROCAL_CLASSES_PER_KIND
    ):
        raise LegacyLearnedStateGateError(
            "retired auditory reciprocity authority or capacity changed"
        )
    branch_count = 0
    receipt_count = 0
    labels: set[str] = set()
    class_fields = {
        "admission_evidence_sha256",
        "admission_receipts",
        "authority_receipts",
        "branches",
        "first_experience_id",
        "kind",
        "last_experience_id",
        "reinforcement_count",
        "tutor_label",
    }
    for item in classes:
        if not isinstance(item, dict) or set(item) != class_fields:
            raise LegacyLearnedStateGateError(
                "retired auditory reciprocity class changed"
            )
        branches = item.get("branches")
        authority_receipts = item.get("authority_receipts")
        admission_receipts = item.get("admission_receipts")
        admission_evidence = item.get("admission_evidence_sha256")
        reinforcement_count = item.get("reinforcement_count")
        label = item.get("tutor_label")
        if (
            item.get("kind") != "spoken_form"
            or not isinstance(label, str)
            or not label
            or label in labels
            or not isinstance(branches, list)
            or not 0 < len(branches) <= MAX_PATH_BRANCHES_PER_CLASS
            or not isinstance(authority_receipts, list)
            or not isinstance(admission_receipts, list)
            or not isinstance(admission_evidence, list)
            or isinstance(reinforcement_count, bool)
            or not isinstance(reinforcement_count, int)
            or reinforcement_count < len(branches)
            or len(authority_receipts) != reinforcement_count
            or len(admission_receipts) != reinforcement_count
            or len(admission_evidence) != reinforcement_count
        ):
            raise LegacyLearnedStateGateError(
                "retired auditory reciprocity class authority changed"
            )
        labels.add(label)
        branch_count += len(branches)
        receipt_count += reinforcement_count
    return {
        "branch_count": branch_count,
        "class_count": len(classes),
        "decoded_payload_bytes": len(payload),
        "encoded_payload_bytes": len(encoded_bytes),
        "label_keyed": True,
        "mechanism_active_in_current_runtime": False,
        "payload_sha256": expected_sha,
        "single_sense_authority": True,
        "tutor_authority_receipt_count": receipt_count,
    }


def _legacy_causal_action_digest(
    value: object,
    *,
    field: str,
) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in _HEX for character in value)
    ):
        raise LegacyLearnedStateGateError(
            f"retired causal action {field} is invalid"
        )
    return value


def _legacy_causal_action_scalars(
    value: object,
    *,
    field: str,
) -> tuple[int, ...]:
    if (
        not isinstance(value, list)
        or not value
        or any(
            isinstance(item, bool)
            or not isinstance(item, int)
            or item < 0
            or item > 0x10FFFF
            or 0xD800 <= item <= 0xDFFF
            for item in value
        )
    ):
        raise LegacyLearnedStateGateError(
            f"retired causal action {field} Unicode scalars changed"
        )
    return tuple(value)


def _inspect_retired_causal_action(
    value: object,
    *,
    authority_key: bytes,
) -> dict[str, object]:
    """Authenticate retired auditory-class/Unicode authority as inert bytes."""

    if not isinstance(value, dict) or set(value) != {
        "payload_base64",
        "schema",
        "state_hmac_sha256",
    }:
        raise LegacyLearnedStateGateError(
            "retired causal action envelope changed"
        )
    if value.get("schema") != _LEGACY_CAUSAL_ACTION_ENVELOPE_SCHEMA:
        raise LegacyLearnedStateGateError(
            "retired causal action envelope schema changed"
        )
    encoded = value.get("payload_base64")
    supplied_hmac = _legacy_causal_action_digest(
        value.get("state_hmac_sha256"),
        field="state HMAC",
    )
    if not isinstance(encoded, str) or not encoded:
        raise LegacyLearnedStateGateError(
            "retired causal action encoded payload changed"
        )
    try:
        encoded_bytes = encoded.encode("ascii")
    except UnicodeEncodeError as error:
        raise LegacyLearnedStateGateError(
            "retired causal action encoded payload changed"
        ) from error
    if len(encoded_bytes) > 4 * (
        (_LEGACY_CAUSAL_ACTION_ENCODED_BYTE_CAPACITY + 2) // 3
    ):
        raise LegacyLearnedStateGateError(
            "retired causal action encoded payload exceeds capacity"
        )
    try:
        payload = base64.b64decode(encoded_bytes, validate=True)
    except Exception as error:
        raise LegacyLearnedStateGateError(
            "retired causal action payload is not canonical base64"
        ) from error
    if (
        not payload
        or base64.b64encode(payload) != encoded_bytes
        or len(payload) > _LEGACY_CAUSAL_ACTION_ENCODED_BYTE_CAPACITY
    ):
        raise LegacyLearnedStateGateError(
            "retired causal action payload boundary changed"
        )
    expected_hmac = hmac.new(
        authority_key,
        _LEGACY_CAUSAL_ACTION_STATE_DOMAIN + payload,
        hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(supplied_hmac, expected_hmac):
        raise LegacyLearnedStateGateError(
            "retired causal action state HMAC changed"
        )
    try:
        decoded = json.loads(payload)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise LegacyLearnedStateGateError(
            "retired causal action payload is invalid"
        ) from error
    expected_state_fields = {
        "action_capacity",
        "bindings",
        "encoded_byte_capacity",
        "scalar_capacity",
        "schema",
        "transient_capacity",
        "witness_capacity",
        "witnesses",
    }
    if (
        not isinstance(decoded, dict)
        or set(decoded) != expected_state_fields
        or decoded.get("schema") != _LEGACY_CAUSAL_ACTION_STATE_SCHEMA
        or _legacy_canonical(decoded) != payload
    ):
        raise LegacyLearnedStateGateError(
            "retired causal action state schema changed"
        )
    witnesses = decoded.get("witnesses")
    bindings = decoded.get("bindings")
    if (
        decoded.get("transient_capacity")
        != _LEGACY_CAUSAL_ACTION_TRANSIENT_CAPACITY
        or decoded.get("action_capacity")
        != _LEGACY_CAUSAL_ACTION_ACTION_CAPACITY
        or decoded.get("witness_capacity")
        != _LEGACY_CAUSAL_ACTION_WITNESS_CAPACITY
        or decoded.get("scalar_capacity")
        != _LEGACY_CAUSAL_ACTION_SCALAR_CAPACITY
        or decoded.get("encoded_byte_capacity")
        != _LEGACY_CAUSAL_ACTION_ENCODED_BYTE_CAPACITY
        or not isinstance(witnesses, list)
        or len(witnesses) > _LEGACY_CAUSAL_ACTION_WITNESS_CAPACITY
        or not isinstance(bindings, list)
        or len(bindings) > _LEGACY_CAUSAL_ACTION_ACTION_CAPACITY
    ):
        raise LegacyLearnedStateGateError(
            "retired causal action state capacities changed"
        )

    witness_fields = {
        "event_id",
        "recognition_class_authority_receipt_sha256",
        "recognition_occurrence_authority_receipt_sha256",
        "settlement_payload_base64",
        "settlement_receipt_sha256",
        "structural_fingerprint",
        "unicode_scalars",
    }
    witness_by_receipt: dict[str, dict[str, object]] = {}
    for witness in witnesses:
        if not isinstance(witness, dict) or set(witness) != witness_fields:
            raise LegacyLearnedStateGateError(
                "retired causal action witness schema changed"
            )
        settlement_receipt = _legacy_causal_action_digest(
            witness.get("settlement_receipt_sha256"),
            field="witness settlement receipt",
        )
        for field in (
            "event_id",
            "recognition_class_authority_receipt_sha256",
            "recognition_occurrence_authority_receipt_sha256",
            "structural_fingerprint",
        ):
            _legacy_causal_action_digest(
                witness.get(field),
                field=f"witness {field}",
            )
        scalars = _legacy_causal_action_scalars(
            witness.get("unicode_scalars"),
            field="witness",
        )
        settlement_encoded = witness.get("settlement_payload_base64")
        if not isinstance(settlement_encoded, str):
            raise LegacyLearnedStateGateError(
                "retired causal action witness payload changed"
            )
        try:
            settlement_encoded_bytes = settlement_encoded.encode("ascii")
            settlement_payload = base64.b64decode(
                settlement_encoded_bytes,
                validate=True,
            )
        except Exception as error:
            raise LegacyLearnedStateGateError(
                "retired causal action witness payload changed"
            ) from error
        if (
            not settlement_payload
            or base64.b64encode(settlement_payload)
            != settlement_encoded_bytes
            or _sha(settlement_payload) != settlement_receipt
        ):
            raise LegacyLearnedStateGateError(
                "retired causal action witness payload receipt changed"
            )
        try:
            settlement = json.loads(settlement_payload)
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise LegacyLearnedStateGateError(
                "retired causal action witness settlement changed"
            ) from error
        interpretations = (
            settlement.get("interpretations")
            if isinstance(settlement, dict)
            else None
        )
        language_events = (
            settlement.get("language_events")
            if isinstance(settlement, dict)
            else None
        )
        if (
            not isinstance(settlement, dict)
            or _legacy_canonical(settlement) != settlement_payload
            or settlement.get("event_id") != witness.get("event_id")
            or settlement.get("structural_fingerprint")
            != witness.get("structural_fingerprint")
            or not isinstance(interpretations, list)
            or len(interpretations) != 6
            or not isinstance(language_events, list)
            or len(language_events) != 1
        ):
            raise LegacyLearnedStateGateError(
                "retired causal action witness settlement identity changed"
            )
        sense_states = {
            item.get("sense"): item.get("state")
            for item in interpretations
            if isinstance(item, dict)
        }
        if (
            set(sense_states)
            != {"sight", "sound", "touch", "smell", "taste", "body"}
            or sense_states["sound"] != "observed"
            or any(
                state not in {
                    "observed",
                    "sensor_unavailable",
                    "unknown",
                }
                for state in sense_states.values()
            )
        ):
            raise LegacyLearnedStateGateError(
                "retired causal action witness sense authority changed"
            )
        language = language_events[0]
        occurrence = (
            language.get("recognition_occurrence")
            if isinstance(language, dict)
            else None
        )
        if (
            not isinstance(language, dict)
            or not isinstance(occurrence, dict)
            or occurrence.get("state") != "unique"
            or occurrence.get("kind") != "spoken_form"
            or occurrence.get("authority_receipt_sha256")
            != witness.get(
                "recognition_occurrence_authority_receipt_sha256"
            )
            or occurrence.get(
                "selected_class_authority_receipt_sha256"
            )
            != witness.get(
                "recognition_class_authority_receipt_sha256"
            )
            or tuple(language.get("unicode_scalars") or ()) != scalars
            or language.get("form")
            != "".join(chr(scalar) for scalar in scalars)
        ):
            raise LegacyLearnedStateGateError(
                "retired causal action witness auditory authority changed"
            )
        if settlement_receipt in witness_by_receipt:
            raise LegacyLearnedStateGateError(
                "retired causal action state repeats a witness"
            )
        witness_by_receipt[settlement_receipt] = witness

    teacher_fields = {
        "action_class_authority_receipt_sha256",
        "action_settlement_receipt_sha256",
        "authority_hmac_sha256",
        "issued_at_unix_ns",
        "nonce",
        "schema",
        "source",
        "trigger_class_authority_receipt_sha256",
        "trigger_settlement_receipt_sha256",
    }
    binding_fields = {
        "action_class_authority_receipt_sha256",
        "action_witness_receipt_sha256",
        "binding_id",
        "binding_receipt_sha256",
        "schema",
        "teacher_relation",
        "trigger_class_authority_receipt_sha256",
        "trigger_witness_receipt_sha256",
        "unicode_scalars",
    }
    binding_ids: set[str] = set()
    teacher_nonces: set[str] = set()
    unicode_scalar_count = 0
    for binding in bindings:
        if (
            not isinstance(binding, dict)
            or set(binding) != binding_fields
            or binding.get("schema")
            != _LEGACY_CAUSAL_ACTION_BINDING_SCHEMA
        ):
            raise LegacyLearnedStateGateError(
                "retired causal action binding schema changed"
            )
        for field in (
            "action_class_authority_receipt_sha256",
            "action_witness_receipt_sha256",
            "binding_id",
            "binding_receipt_sha256",
            "trigger_class_authority_receipt_sha256",
            "trigger_witness_receipt_sha256",
        ):
            _legacy_causal_action_digest(
                binding.get(field),
                field=f"binding {field}",
            )
        scalars = _legacy_causal_action_scalars(
            binding.get("unicode_scalars"),
            field="binding",
        )
        if len(scalars) > _LEGACY_CAUSAL_ACTION_SCALAR_CAPACITY:
            raise LegacyLearnedStateGateError(
                "retired causal action binding scalar capacity changed"
            )
        teacher = binding.get("teacher_relation")
        if (
            not isinstance(teacher, dict)
            or set(teacher) != teacher_fields
            or teacher.get("schema")
            != _LEGACY_CAUSAL_ACTION_TEACHER_RELATION_SCHEMA
        ):
            raise LegacyLearnedStateGateError(
                "retired causal action teacher relation schema changed"
            )
        for field in (
            "action_class_authority_receipt_sha256",
            "action_settlement_receipt_sha256",
            "authority_hmac_sha256",
            "trigger_class_authority_receipt_sha256",
            "trigger_settlement_receipt_sha256",
        ):
            _legacy_causal_action_digest(
                teacher.get(field),
                field=f"teacher relation {field}",
            )
        nonce = teacher.get("nonce")
        issued_at = teacher.get("issued_at_unix_ns")
        if (
            teacher.get("source") not in {"joe", "wc"}
            or isinstance(issued_at, bool)
            or not isinstance(issued_at, int)
            or issued_at <= 0
            or not isinstance(nonce, str)
            or len(nonce) != 64
            or any(character not in _HEX for character in nonce)
        ):
            raise LegacyLearnedStateGateError(
                "retired causal action teacher relation changed"
            )
        unsigned_teacher = {
            field: teacher[field]
            for field in sorted(teacher)
            if field != "authority_hmac_sha256"
        }
        expected_teacher_hmac = hmac.new(
            authority_key,
            _LEGACY_CAUSAL_ACTION_TEACHER_DOMAIN
            + _legacy_canonical(unsigned_teacher),
            hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(
            teacher["authority_hmac_sha256"],
            expected_teacher_hmac,
        ):
            raise LegacyLearnedStateGateError(
                "retired causal action teacher relation HMAC changed"
            )
        semantic_id = _sha(_legacy_canonical({
            "action_class_authority_receipt_sha256": binding[
                "action_class_authority_receipt_sha256"
            ],
            "schema": _LEGACY_CAUSAL_ACTION_SEMANTIC_RELATION_SCHEMA,
            "trigger_class_authority_receipt_sha256": binding[
                "trigger_class_authority_receipt_sha256"
            ],
            "unicode_scalars": list(scalars),
        }))
        binding_payload = {
            field: binding[field]
            for field in sorted(binding)
            if field != "binding_receipt_sha256"
        }
        if (
            binding.get("binding_id") != semantic_id
            or binding.get("binding_receipt_sha256")
            != _sha(_legacy_canonical(binding_payload))
        ):
            raise LegacyLearnedStateGateError(
                "retired causal action binding identity changed"
            )
        trigger = witness_by_receipt.get(
            binding["trigger_witness_receipt_sha256"]
        )
        action = witness_by_receipt.get(
            binding["action_witness_receipt_sha256"]
        )
        if (
            trigger is None
            or action is None
            or binding["trigger_class_authority_receipt_sha256"]
            != trigger["recognition_class_authority_receipt_sha256"]
            or binding["action_class_authority_receipt_sha256"]
            != action["recognition_class_authority_receipt_sha256"]
            or list(scalars) != action["unicode_scalars"]
            or teacher["trigger_settlement_receipt_sha256"]
            != trigger["settlement_receipt_sha256"]
            or teacher["trigger_class_authority_receipt_sha256"]
            != trigger["recognition_class_authority_receipt_sha256"]
            or teacher["action_settlement_receipt_sha256"]
            != action["settlement_receipt_sha256"]
            or teacher["action_class_authority_receipt_sha256"]
            != action["recognition_class_authority_receipt_sha256"]
        ):
            raise LegacyLearnedStateGateError(
                "retired causal action binding evidence changed"
            )
        if binding["binding_id"] in binding_ids or nonce in teacher_nonces:
            raise LegacyLearnedStateGateError(
                "retired causal action state repeats binding authority"
            )
        binding_ids.add(binding["binding_id"])
        teacher_nonces.add(nonce)
        unicode_scalar_count += len(scalars)

    return {
        "action_capacity": _LEGACY_CAUSAL_ACTION_ACTION_CAPACITY,
        "auditory_class_authority": True,
        "binding_count": len(bindings),
        "decoded_payload_bytes": len(payload),
        "encoded_byte_capacity": (
            _LEGACY_CAUSAL_ACTION_ENCODED_BYTE_CAPACITY
        ),
        "encoded_payload_bytes": len(encoded_bytes),
        "mechanism_active_in_current_runtime": False,
        "payload_sha256": _sha(payload),
        "scalar_capacity_per_binding": (
            _LEGACY_CAUSAL_ACTION_SCALAR_CAPACITY
        ),
        "state_hmac_sha256": supplied_hmac,
        "transient_capacity": _LEGACY_CAUSAL_ACTION_TRANSIENT_CAPACITY,
        "unicode_action_authority": True,
        "unicode_scalar_count": unicode_scalar_count,
        "witness_capacity": _LEGACY_CAUSAL_ACTION_WITNESS_CAPACITY,
        "witness_count": len(witnesses),
    }


def _inspect_retired_auditory_v4_archive(
    value: object,
) -> dict[str, object]:
    """Verify the explicit v4 quarantine without detaching dependents."""

    expected_fields = {
        "auditory_reciprocity_v4",
        "auditory_reciprocity_v4_canonical_sha256",
        "quarantined_causal_action",
        "quarantined_causal_action_canonical_sha256",
        "quarantined_latest_auditory_causal_event",
        (
            "quarantined_latest_auditory_causal_event_"
            "canonical_sha256"
        ),
        "schema",
    }
    if not isinstance(value, dict) or set(value) != expected_fields:
        raise LegacyLearnedStateGateError(
            "retired auditory v4 archive changed"
        )
    if value.get("schema") != _AUDITORY_V4_ARCHIVE_SCHEMA:
        raise LegacyLearnedStateGateError(
            "retired auditory v4 archive schema changed"
        )
    try:
        reciprocity = inspect_legacy_v4_envelope(
            value["auditory_reciprocity_v4"]
        )
    except ValueError as error:
        raise LegacyLearnedStateGateError(
            "retired auditory v4 reciprocity integrity changed"
        ) from error
    if (
        value.get("auditory_reciprocity_v4_canonical_sha256")
        != reciprocity.envelope_canonical_sha256
    ):
        raise LegacyLearnedStateGateError(
            "retired auditory v4 reciprocity digest changed"
        )

    component_evidence: dict[str, dict[str, object]] = {}
    for field, digest_field in (
        (
            "quarantined_causal_action",
            "quarantined_causal_action_canonical_sha256",
        ),
        (
            "quarantined_latest_auditory_causal_event",
            (
                "quarantined_latest_auditory_causal_event_"
                "canonical_sha256"
            ),
        ),
    ):
        encoded = _legacy_canonical(value[field])
        expected = value.get(digest_field)
        if (
            len(encoded) > MAX_DECODED_SNAPSHOT_BYTES
            or not isinstance(expected, str)
            or len(expected) != 64
            or any(character not in _HEX for character in expected)
            or _sha(encoded) != expected
        ):
            raise LegacyLearnedStateGateError(
                f"retired auditory v4 archive {field} digest changed"
            )
        component_evidence[field] = {
            "bytes": len(encoded),
            "canonical_sha256": expected,
            "schema": (
                value[field].get("schema")
                if isinstance(value[field], dict)
                else None
            ),
        }
    archive = _legacy_canonical(value)
    if len(archive) > MAX_DECODED_SNAPSHOT_BYTES:
        raise LegacyLearnedStateGateError(
            "retired auditory v4 archive exceeds its boundary"
        )
    return {
        "archive_bytes": len(archive),
        "auditory_reciprocity_v4": {
            "decoded_payload_bytes": (
                reciprocity.decoded_payload_bytes
            ),
            "encoded_payload_bytes": (
                reciprocity.encoded_payload_bytes
            ),
            "envelope_canonical_sha256": (
                reciprocity.envelope_canonical_sha256
            ),
            "payload_sha256": reciprocity.payload_sha256,
        },
        "causal_dependents_detachable": False,
        "components": component_evidence,
        "mechanism_active_in_current_runtime": False,
        "migration_to_current_recurrent_motif": "unavailable",
        "single_sense_authority": True,
    }


def _inspect_retired_causal_organism_growth(
    value: object,
    *,
    authority_key: bytes,
) -> dict[str, object]:
    """Authenticate the retired empty Embryo growth journal as inert state."""

    from dsf_ai_service.substrate.causal_organism_growth import (
        CAUSAL_GROWTH_ORGAN_ORDER,
        CAUSAL_GROWTH_STATE_SCHEMA,
        MAX_PENDING_CAUSAL_GROWTH_CLAIMS,
    )

    if not isinstance(value, dict) or set(value) != {
        "payload",
        "state_hmac_sha256",
    }:
        raise LegacyLearnedStateGateError(
            "retired causal organism growth envelope changed"
        )
    payload = value.get("payload")
    if not isinstance(payload, dict) or set(payload) != {
        "allowed_organs",
        "max_pending",
        "pending",
        "schema",
    }:
        raise LegacyLearnedStateGateError(
            "retired causal organism growth payload changed"
        )
    if (
        payload.get("schema") != CAUSAL_GROWTH_STATE_SCHEMA
        or payload.get("allowed_organs")
        != list(CAUSAL_GROWTH_ORGAN_ORDER)
        or payload.get("max_pending")
        != MAX_PENDING_CAUSAL_GROWTH_CLAIMS
        or payload.get("pending") != []
    ):
        raise LegacyLearnedStateGateError(
            "retired causal organism growth is not exact empty custody"
        )
    journal_key = hmac.new(
        authority_key,
        b"guala-causal-organism-growth-authority-v1",
        hashlib.sha256,
    ).digest()
    expected = hmac.new(
        journal_key,
        _legacy_canonical(payload),
        hashlib.sha256,
    ).hexdigest()
    supplied = value.get("state_hmac_sha256")
    if (
        not isinstance(supplied, str)
        or not hmac.compare_digest(supplied, expected)
    ):
        raise LegacyLearnedStateGateError(
            "retired causal organism growth authentication failed"
        )
    return {
        "allowed_organs": list(CAUSAL_GROWTH_ORGAN_ORDER),
        "mechanism_active_in_current_runtime": False,
        "pending_count": 0,
        "state_hmac_sha256": supplied,
    }


def _inspect_retired_embodied_action_teaching(
    value: object,
    *,
    runtime,
) -> dict[str, object] | None:
    """Authenticate prior command-schema lessons without inventing duration."""

    owner = getattr(runtime, "_embodied_action_teaching", None)
    if owner is None:
        raise LegacyLearnedStateGateError(
            "embodied teaching archive lacks current authority custody"
        )
    if (
        not isinstance(value, dict)
        or set(value) != {
            "authority_hmac_sha256",
            "payload_base64",
            "schema",
        }
        or value.get("schema") != _EMBODIED_TEACHING_ENVELOPE_SCHEMA
    ):
        raise LegacyLearnedStateGateError(
            "embodied teaching archive envelope changed"
        )
    try:
        payload = base64.b64decode(
            value.get("payload_base64"),
            validate=True,
        )
    except Exception as error:
        raise LegacyLearnedStateGateError(
            "embodied teaching archive payload is not canonical base64"
        ) from error
    if (
        base64.b64encode(payload).decode("ascii")
        != value.get("payload_base64")
    ):
        raise LegacyLearnedStateGateError(
            "embodied teaching archive payload is not canonical base64"
        )
    expected_state_hmac = hmac.new(
        owner._key,
        _EMBODIED_TEACHING_STATE_DOMAIN + payload,
        hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(
        expected_state_hmac,
        value.get("authority_hmac_sha256", ""),
    ):
        raise LegacyLearnedStateGateError(
            "embodied teaching archive authentication failed"
        )
    try:
        decoded = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise LegacyLearnedStateGateError(
            "embodied teaching archive payload is invalid"
        ) from error
    expected_limits = {
        "demonstration_capacity": owner._capacity,
        "max_command_bytes": owner._max_command_bytes,
        "max_encoded_state_bytes": owner._max_encoded_state_bytes,
    }
    records = decoded.get("records") if isinstance(decoded, dict) else None
    if (
        not isinstance(decoded, dict)
        or _canonical(decoded) != payload
        or set(decoded) != {
            "authorized_tutors",
            "limits",
            "records",
            "schema",
        }
        or decoded.get("schema") != _EMBODIED_TEACHING_STATE_SCHEMA
        or decoded.get("authorized_tutors")
        != list(owner._authorized_tutors)
        or decoded.get("limits") != expected_limits
        or not isinstance(records, list)
        or len(records) > owner._capacity
    ):
        raise LegacyLearnedStateGateError(
            "embodied teaching archive state changed"
        )

    legacy_count = 0
    current_count = 0
    seen_nonces: set[str] = set()
    demonstration_keys = {
        "action_receipt_sha256",
        "authority_hmac_sha256",
        "authority_receipt_sha256",
        "command_payload_base64",
        "command_sha256",
        "execution_receipt_sha256",
        "nonce",
        "port_id",
        "post_observation_receipt_sha256",
        "post_settlement_receipt_sha256",
        "post_structural_fingerprint",
        "pre_observation_receipt_sha256",
        "pre_settlement_receipt_sha256",
        "pre_structural_fingerprint",
        "schema",
        "tutor_id",
    }
    for record in records:
        if (
            not isinstance(record, dict)
            or set(record) != {"binding_id", "demonstration"}
            or not isinstance(record.get("demonstration"), dict)
        ):
            raise LegacyLearnedStateGateError(
                "embodied teaching archive record changed"
            )
        demonstration = record["demonstration"]
        if (
            set(demonstration) != demonstration_keys
            or demonstration.get("schema")
            != _EMBODIED_TEACHING_DEMONSTRATION_SCHEMA
        ):
            raise LegacyLearnedStateGateError(
                "embodied teaching archive demonstration changed"
            )
        try:
            command_payload = base64.b64decode(
                demonstration.get("command_payload_base64"),
                validate=True,
            )
            command = json.loads(command_payload.decode("utf-8"))
        except Exception as error:
            raise LegacyLearnedStateGateError(
                "embodied teaching archive command is invalid"
            ) from error
        if (
            not command_payload
            or len(command_payload) > owner._max_command_bytes
            or base64.b64encode(command_payload).decode("ascii")
            != demonstration.get("command_payload_base64")
            or _legacy_canonical(command) != command_payload
            or not isinstance(command, dict)
            or not isinstance(command.get("schema"), str)
        ):
            raise LegacyLearnedStateGateError(
                "embodied teaching archive command changed"
            )
        if command["schema"] == _LEGACY_EMBODIED_COMMAND_SCHEMA:
            operation_fields = {
                "move": {"operation", "schema", "target_pose"},
                "pick": {"object_id", "operation", "schema"},
                "place": {
                    "object_id",
                    "operation",
                    "schema",
                    "target_position",
                },
            }
            if set(command) != operation_fields.get(
                command.get("operation"),
                set(),
            ):
                raise LegacyLearnedStateGateError(
                    "legacy embodied command fields changed"
                )
            legacy_count += 1
        else:
            current_count += 1
        unsigned = {
            key: demonstration[key]
            for key in demonstration_keys
            if key not in {
                "authority_hmac_sha256",
                "authority_receipt_sha256",
            }
        }
        expected_hmac = hmac.new(
            owner._key,
            _EMBODIED_TEACHING_DEMONSTRATION_DOMAIN
            + _canonical(unsigned),
            hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(
            expected_hmac,
            demonstration["authority_hmac_sha256"],
        ):
            raise LegacyLearnedStateGateError(
                "embodied teaching demonstration authentication failed"
            )
        expected_receipt = hashlib.sha256(_canonical({
            "authority_hmac_sha256": expected_hmac,
            "payload": unsigned,
        })).hexdigest()
        expected_binding = hashlib.sha256(_canonical({
            "action_receipt_sha256": demonstration[
                "action_receipt_sha256"
            ],
            "schema": (
                "guala.causal_action_cycle.semantic_relation.v1"
            ),
            "trigger_structural_fingerprint": demonstration[
                "pre_structural_fingerprint"
            ],
        })).hexdigest()
        nonce = demonstration.get("nonce")
        if (
            demonstration.get("authority_receipt_sha256")
            != expected_receipt
            or record.get("binding_id") != expected_binding
            or not isinstance(nonce, str)
            or nonce in seen_nonces
            or hashlib.sha256(command_payload).hexdigest()
            != demonstration.get("command_sha256")
        ):
            raise LegacyLearnedStateGateError(
                "embodied teaching archive causal identity changed"
            )
        seen_nonces.add(nonce)

    if legacy_count == 0:
        return None
    if current_count:
        raise LegacyLearnedStateGateError(
            "embodied teaching archive mixes command schema generations"
        )
    return {
        "legacy_command_count": legacy_count,
        "legacy_command_schema": _LEGACY_EMBODIED_COMMAND_SCHEMA,
        "mechanism_active_in_current_runtime": False,
        "state_hmac_sha256": expected_state_hmac,
    }


def _inspect_retired_causal_deliberation(
    value: object,
    *,
    runtime,
) -> dict[str, object] | None:
    """Authenticate deliberation whose old DSF tuples lack provenance."""

    owner = getattr(runtime, "_causal_deliberation", None)
    if owner is None:
        raise LegacyLearnedStateGateError(
            "causal deliberation archive lacks current authority custody"
        )
    if (
        not isinstance(value, dict)
        or set(value) != {
            "payload_base64",
            "schema",
            "state_hmac_sha256",
        }
        or value.get("schema") != _CAUSAL_DELIBERATION_ENVELOPE_SCHEMA
    ):
        raise LegacyLearnedStateGateError(
            "causal deliberation archive envelope changed"
        )
    try:
        payload = base64.b64decode(
            value.get("payload_base64"),
            validate=True,
        )
        decoded = json.loads(payload.decode("utf-8"))
    except Exception as error:
        raise LegacyLearnedStateGateError(
            "causal deliberation archive payload is invalid"
        ) from error
    expected_hmac = hmac.new(
        owner._key,
        _CAUSAL_DELIBERATION_STATE_DOMAIN + payload,
        hashlib.sha256,
    ).hexdigest()
    relations = decoded.get("relations") if isinstance(decoded, dict) else None
    if (
        not payload
        or len(payload) > owner._encoded_state_capacity
        or base64.b64encode(payload).decode("ascii")
        != value.get("payload_base64")
        or _legacy_canonical(decoded) != payload
        or not hmac.compare_digest(
            expected_hmac,
            value.get("state_hmac_sha256", ""),
        )
        or not isinstance(decoded, dict)
        or set(decoded) != {
            "capacities",
            "episode",
            "relations",
            "schema",
            "terminal",
        }
        or decoded.get("schema") != _CAUSAL_DELIBERATION_STATE_SCHEMA
        or decoded.get("capacities") != owner._capacities()
        or not isinstance(relations, list)
        or len(relations) > owner._relation_capacity
    ):
        raise LegacyLearnedStateGateError(
            "causal deliberation archive authentication changed"
        )

    witnesses: list[Mapping[str, object]] = []
    for relation in relations:
        if not isinstance(relation, Mapping):
            raise LegacyLearnedStateGateError(
                "causal deliberation archive relation changed"
            )
        trigger = relation.get("trigger")
        outcomes = relation.get("outcomes")
        if (
            not isinstance(trigger, Mapping)
            or not isinstance(outcomes, list)
            or any(not isinstance(item, Mapping) for item in outcomes)
        ):
            raise LegacyLearnedStateGateError(
                "causal deliberation archive witness custody changed"
            )
        witnesses.append(trigger)
        witnesses.extend(outcomes)
    episode = decoded.get("episode")
    if episode is not None:
        if not isinstance(episode, Mapping):
            raise LegacyLearnedStateGateError(
                "causal deliberation archive episode changed"
            )
        for name in ("current", "expected_outcome"):
            witness = episode.get(name)
            if witness is not None:
                if not isinstance(witness, Mapping):
                    raise LegacyLearnedStateGateError(
                        "causal deliberation episode witness changed"
                    )
                witnesses.append(witness)

    legacy_tuple_count = 0
    current_tuple_count = 0
    expected_senses = tuple(item.value for item in SENSE_ORDER)
    witness_fields = {
        "event_id",
        "schema",
        "settlement_payload_base64",
        "settlement_receipt_sha256",
        "structural_fingerprint",
    }
    legacy_tuple_fields = {
        "authority_receipt_sha256",
        "fields",
        "tuple_index",
    }
    current_tuple_fields = legacy_tuple_fields | {
        "source_index_end",
        "source_index_start",
        "source_l0_l4_trace_receipt_sha256",
    }
    for witness in witnesses:
        if (
            set(witness) != witness_fields
            or witness.get("schema")
            != _CAUSAL_DELIBERATION_WITNESS_SCHEMA
        ):
            raise LegacyLearnedStateGateError(
                "causal deliberation archive witness fields changed"
            )
        try:
            settlement_payload = base64.b64decode(
                witness.get("settlement_payload_base64"),
                validate=True,
            )
            settlement = json.loads(
                settlement_payload.decode("utf-8")
            )
        except Exception as error:
            raise LegacyLearnedStateGateError(
                "causal deliberation settlement archive is invalid"
            ) from error
        interpretations = (
            settlement.get("interpretations")
            if isinstance(settlement, dict)
            else None
        )
        if (
            not settlement_payload
            or len(settlement_payload) > owner._max_witness_bytes
            or base64.b64encode(settlement_payload).decode("ascii")
            != witness.get("settlement_payload_base64")
            or _legacy_canonical(settlement) != settlement_payload
            or hashlib.sha256(settlement_payload).hexdigest()
            != witness.get("settlement_receipt_sha256")
            or not isinstance(settlement, Mapping)
            or settlement.get("schema")
            != _LEGACY_CAUSAL_SETTLEMENT_SCHEMA
            or settlement.get("event_id") != witness.get("event_id")
            or settlement.get("structural_fingerprint")
            != witness.get("structural_fingerprint")
            or not isinstance(interpretations, list)
            or len(interpretations) != len(expected_senses)
            or any(
                not isinstance(sense, Mapping)
                or not isinstance(sense.get("substreams"), list)
                for sense in interpretations
            )
            or tuple(
                sense.get("sense")
                for sense in interpretations
            )
            != expected_senses
            or not isinstance(
                settlement.get("language_events"),
                list,
            )
        ):
            raise LegacyLearnedStateGateError(
                "causal deliberation settlement custody changed"
            )
        sense_identity: dict[str, dict[str, object]] = {}
        for sense in interpretations:
            if set(sense) != {
                "boundary_receipt_sha256",
                "relation",
                "sense",
                "state",
                "structural_fingerprint",
                "substreams",
                "topology_receipt_sha256",
            }:
                raise LegacyLearnedStateGateError(
                    "causal deliberation sense structure changed"
                )
            compact_substreams: list[dict[str, object]] = []
            for topology_index, substream in enumerate(
                sense["substreams"]
            ):
                if (
                    not isinstance(substream, Mapping)
                    or set(substream) != {
                        "coordinates",
                        "field_tuples",
                        "kernel_basin_receipt_sha256",
                        "physical_quantity",
                        "physical_unit",
                        "profile_receipt_sha256",
                        "sensor_id",
                        "source_evidence_stream_receipt_sha256",
                        "source_sample_commitment_sha256",
                        "source_sample_count",
                        "substream_id",
                        "topology_index",
                    }
                    or substream.get("topology_index")
                    != topology_index
                    or not isinstance(
                        substream.get("coordinates"),
                        list,
                    )
                    or not isinstance(
                        substream.get("field_tuples"),
                        list,
                    )
                ):
                    raise LegacyLearnedStateGateError(
                        "causal deliberation DSF substream changed"
                    )
                compact_tuples: list[dict[str, object]] = []
                for tuple_index, field_tuple in enumerate(
                    substream["field_tuples"]
                ):
                    if not isinstance(field_tuple, Mapping):
                        raise LegacyLearnedStateGateError(
                            "causal deliberation DSF tuple changed"
                        )
                    if set(field_tuple) == legacy_tuple_fields:
                        legacy_tuple_count += 1
                    elif set(field_tuple) == current_tuple_fields:
                        current_tuple_count += 1
                    else:
                        raise LegacyLearnedStateGateError(
                            "causal deliberation DSF tuple schema is unknown"
                        )
                    fields = field_tuple.get("fields")
                    if (
                        field_tuple.get("tuple_index") != tuple_index
                        or not isinstance(fields, list)
                        or len(fields) != len(DSF_FIELD_ORDER)
                        or tuple(
                            item[0]
                            for item in fields
                            if isinstance(item, list)
                            and len(item) == 2
                        )
                        != DSF_FIELD_ORDER
                    ):
                        raise LegacyLearnedStateGateError(
                            "causal deliberation DSF tuple changed"
                        )
                    compact_fields: list[list[str]] = []
                    for name, raw in fields:
                        if not isinstance(raw, str):
                            raise LegacyLearnedStateGateError(
                                "causal deliberation DSF field is not exact"
                            )
                        try:
                            exact = Fraction(raw)
                        except (
                            ValueError,
                            ZeroDivisionError,
                        ) as error:
                            raise LegacyLearnedStateGateError(
                                "causal deliberation DSF field is not exact"
                            ) from error
                        if (
                            f"{exact.numerator}/{exact.denominator}"
                            != raw
                        ):
                            raise LegacyLearnedStateGateError(
                                "causal deliberation DSF field is not canonical"
                            )
                        compact_fields.append([name, raw])
                    compact_tuple: dict[str, object] = {
                        "fields": compact_fields,
                        "tuple_index": tuple_index,
                    }
                    if set(field_tuple) == current_tuple_fields:
                        start = field_tuple.get("source_index_start")
                        end = field_tuple.get("source_index_end")
                        if (
                            isinstance(start, bool)
                            or not isinstance(start, int)
                            or isinstance(end, bool)
                            or not isinstance(end, int)
                            or not 0 <= start <= end
                        ):
                            raise LegacyLearnedStateGateError(
                                "causal deliberation DSF provenance changed"
                            )
                        compact_tuple.update({
                            "source_index_end": end,
                            "source_index_start": start,
                        })
                    compact_tuples.append(compact_tuple)
                compact_substreams.append({
                    "coordinates": substream["coordinates"],
                    "field_tuples": compact_tuples,
                    "physical_quantity": substream.get(
                        "physical_quantity"
                    ),
                    "physical_unit": substream.get("physical_unit"),
                    "substream_id": substream.get("substream_id"),
                    "topology_index": topology_index,
                })
            recomputed_sense = _sha(_legacy_canonical({
                "state": sense.get("state"),
                "substreams": compact_substreams,
            }))
            if recomputed_sense != sense.get(
                "structural_fingerprint"
            ):
                raise LegacyLearnedStateGateError(
                    "causal deliberation explicit DSF field changed"
                )
            sense_identity[sense["sense"]] = {
                "state": sense.get("state"),
                "structural_fingerprint": recomputed_sense,
            }
        language_identity: list[dict[str, object]] = []
        for item in settlement["language_events"]:
            if not isinstance(item, Mapping):
                raise LegacyLearnedStateGateError(
                    "causal deliberation language event changed"
                )
            occurrence = item.get("recognition_occurrence")
            selected = (
                occurrence.get(
                    "selected_class_authority_receipt_sha256"
                )
                if isinstance(occurrence, Mapping)
                else None
            )
            language_identity.append({
                "form": item.get("form"),
                "recognition_class_authority_receipt_sha256": (
                    selected
                ),
                "unicode_scalars": item.get("unicode_scalars"),
            })
        recomputed_settlement = _sha(_legacy_canonical({
            "interpretations": sense_identity,
            "language_events": language_identity,
        }))
        if recomputed_settlement != witness.get(
            "structural_fingerprint"
        ):
            raise LegacyLearnedStateGateError(
                "causal deliberation structural identity changed"
            )

    if legacy_tuple_count == 0:
        return None
    if current_tuple_count:
        raise LegacyLearnedStateGateError(
            "causal deliberation mixes DSF provenance generations"
        )
    return {
        "legacy_dsf_tuple_count": legacy_tuple_count,
        "missing_current_provenance_fields": [
            "source_index_end",
            "source_index_start",
            "source_l0_l4_trace_receipt_sha256",
        ],
        "mechanism_active_in_current_runtime": False,
        "state_hmac_sha256": expected_hmac,
        "witness_count": len(witnesses),
    }


def _inspect_retired_causal_action_cycle(
    value: object,
    *,
    runtime,
) -> dict[str, object] | None:
    """Authenticate v2 actions whose opaque commands have no duration."""

    if not isinstance(value, dict):
        raise LegacyLearnedStateGateError(
            "causal action cycle archive is not an envelope"
        )
    if value.get("schema") != _LEGACY_CAUSAL_ACTION_CYCLE_ENVELOPE_SCHEMA:
        return None
    owner = getattr(runtime, "_causal_action_cycle", None)
    if owner is None:
        raise LegacyLearnedStateGateError(
            "causal action cycle archive lacks current authority custody"
        )
    if set(value) != {
        "payload_base64",
        "schema",
        "state_hmac_sha256",
    }:
        raise LegacyLearnedStateGateError(
            "causal action cycle archive envelope changed"
        )
    try:
        payload = base64.b64decode(
            value.get("payload_base64"),
            validate=True,
        )
        decoded = json.loads(payload.decode("utf-8"))
    except Exception as error:
        raise LegacyLearnedStateGateError(
            "causal action cycle archive payload is invalid"
        ) from error
    expected_hmac = hmac.new(
        owner._key,
        _LEGACY_CAUSAL_ACTION_CYCLE_STATE_DOMAIN + payload,
        hashlib.sha256,
    ).hexdigest()
    if (
        not payload
        or len(payload) > owner._encoded_state_capacity
        or base64.b64encode(payload).decode("ascii")
        != value.get("payload_base64")
        or _legacy_canonical(decoded) != payload
        or not hmac.compare_digest(
            expected_hmac,
            value.get("state_hmac_sha256", ""),
        )
        or not isinstance(decoded, dict)
        or set(decoded) != {
            "bindings",
            "capacities",
            "evidence",
            "executions",
            "intents",
            "outcomes",
            "schema",
        }
        or decoded.get("schema")
        != _LEGACY_CAUSAL_ACTION_CYCLE_STATE_SCHEMA
        or any(
            not isinstance(decoded.get(name), list)
            for name in (
                "bindings",
                "evidence",
                "executions",
                "intents",
                "outcomes",
            )
        )
    ):
        raise LegacyLearnedStateGateError(
            "causal action cycle archive authentication changed"
        )
    legacy_commands = 0
    retired_speech = 0
    for binding in decoded["bindings"]:
        action = (
            binding.get("action")
            if isinstance(binding, Mapping)
            else None
        )
        if not isinstance(action, Mapping):
            raise LegacyLearnedStateGateError(
                "causal action cycle archive binding changed"
            )
        kind = action.get("kind")
        if kind == "speech":
            if (
                action.get("schema")
                != "guala.causal_action_cycle.action.v1"
                or action.get("command_payload_base64") != ""
                or action.get("port_id") is not None
                or not isinstance(action.get("unicode_scalars"), list)
                or not action["unicode_scalars"]
            ):
                raise LegacyLearnedStateGateError(
                    "retired speech action archive changed"
                )
            retired_speech += 1
            continue
        if kind != "embodiment_port":
            raise LegacyLearnedStateGateError(
                "causal action cycle archive action kind changed"
            )
        try:
            command_payload = base64.b64decode(
                action.get("command_payload_base64"),
                validate=True,
            )
            command = json.loads(command_payload.decode("utf-8"))
        except Exception as error:
            raise LegacyLearnedStateGateError(
                "causal action cycle archive command is invalid"
            ) from error
        operation_fields = {
            "move": {"operation", "schema", "target_pose"},
            "pick": {"object_id", "operation", "schema"},
            "place": {
                "object_id",
                "operation",
                "schema",
                "target_position",
            },
        }
        if (
            not isinstance(command, dict)
            or _legacy_canonical(command) != command_payload
            or command.get("schema") != _LEGACY_EMBODIED_COMMAND_SCHEMA
            or set(command) != operation_fields.get(
                command.get("operation"),
                set(),
            )
        ):
            raise LegacyLearnedStateGateError(
                "causal action cycle prior command schema changed"
            )
        legacy_commands += 1
    if legacy_commands == 0 and retired_speech == 0:
        return None
    return {
        "legacy_duration_free_command_count": legacy_commands,
        "legacy_command_schema": _LEGACY_EMBODIED_COMMAND_SCHEMA,
        "mechanism_active_in_current_runtime": False,
        "retired_scripted_speech_action_count": retired_speech,
        "state_hmac_sha256": expected_hmac,
    }


@dataclass(frozen=True, slots=True)
class LegacyLearnedStatePlan:
    body: dict[str, object]
    authority_hmac_sha256: str
    direct_owner_bodies: dict[str, bytes]

    @property
    def cutover_allowed(self) -> bool:
        return self.body["unresolved_member_count"] == 0

    def record(self) -> dict[str, object]:
        return {
            "authority_hmac_sha256": self.authority_hmac_sha256,
            "body": self.body,
            "schema": GATE_SCHEMA,
        }


def verify_legacy_learned_state_plan(
    record: Mapping[str, object],
    *,
    authority_key: bytes | bytearray | memoryview | str,
) -> dict[str, object]:
    if (
        not isinstance(record, Mapping)
        or set(record) != {"authority_hmac_sha256", "body", "schema"}
        or record.get("schema") != GATE_SCHEMA
        or not isinstance(record.get("body"), dict)
    ):
        raise LegacyLearnedStateGateError(
            "learned-state gate record changed"
        )
    supplied = record.get("authority_hmac_sha256")
    if (
        not isinstance(supplied, str)
        or len(supplied) != 64
        or any(character not in _HEX for character in supplied)
    ):
        raise LegacyLearnedStateGateError(
            "learned-state gate authentication is invalid"
        )
    expected = hmac.new(
        _authority_key(authority_key),
        _GATE_DOMAIN + _canonical(record["body"]),
        hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(supplied, expected):
        raise LegacyLearnedStateGateError(
            "learned-state gate authentication failed"
        )
    body = dict(record["body"])
    category_bytes = body.get("category_bytes")
    if (
        not isinstance(category_bytes, dict)
        or set(category_bytes) != {DIRECT, ESCROW, UNRESOLVED}
        or any(
            isinstance(value, bool)
            or not isinstance(value, int)
            or value < 0
            for value in category_bytes.values()
        )
        or sum(category_bytes.values())
        != body.get("learned_source_bytes")
    ):
        raise LegacyLearnedStateGateError(
            "learned-state byte accounting changed"
        )
    return body


def build_legacy_learned_state_plan(
    source: Path,
    *,
    identity: str,
    tick: int,
    authority_key: bytes | bytearray | memoryview | str,
    max_sealed_escrow_bytes: int,
    runtime=None,
) -> LegacyLearnedStatePlan:
    """Classify every pre-owner learned source and authenticate the plan."""

    root = Path(source)
    identity = _identity(identity)
    tick = _tick(tick)
    key = _authority_key(authority_key)
    if (
        isinstance(max_sealed_escrow_bytes, bool)
        or not isinstance(max_sealed_escrow_bytes, int)
        or max_sealed_escrow_bytes <= 0
    ):
        raise LegacyLearnedStateGateError(
            "sealed learned-state escrow ceiling is invalid"
        )

    paths = _legacy_learned_paths(root)
    files: list[dict[str, object]] = []
    members: list[dict[str, object]] = []
    category_bytes = {DIRECT: 0, ESCROW: 0, UNRESOLVED: 0}
    direct_values: dict[str, object] = {}
    direct_raw_bodies: dict[str, bytes] = {}
    member_reasons: dict[str, str] = {}
    member_evidence: dict[str, dict[str, object]] = {}
    source_bytes = 0

    groups_by_key = _owner_groups_by_state_key()
    teaching_values: Mapping[str, object] | None = None
    teaching_body: bytes | None = None
    for relative_path in paths:
        body = _regular_body(root, relative_path)
        source_bytes += len(body)
        file_record = {
            "bytes": len(body),
            "path": relative_path,
            "sha256": _sha(body),
        }
        files.append(file_record)

        if relative_path != "guala_teaching.json":
            if relative_path.endswith(".json"):
                envelope = _decoded_legacy_envelope(
                    body,
                    relative_path=relative_path,
                    identity=identity,
                    tick=tick,
                )
                for member, value in sorted(envelope["data"].items()):
                    members.append(_member_record(
                        source_path=relative_path,
                        member=member,
                        value=value,
                        category=ESCROW,
                        reason=(
                            "retired pre-owner sensory/profile authority; "
                            "sealed source bytes remain non-active"
                        ),
                    ))
            category_bytes[ESCROW] += len(body)
            continue

        envelope = _decoded_legacy_envelope(
            body,
            relative_path=relative_path,
            identity=identity,
            tick=tick,
        )
        teaching_values = envelope["data"]
        teaching_body = body

    if teaching_values is not None and teaching_body is not None:
        preliminary: dict[str, str] = {}
        retired_action_cycle = None
        if "causal_action_cycle" in teaching_values:
            retired_action_cycle = (
                _inspect_retired_causal_action_cycle(
                    teaching_values["causal_action_cycle"],
                    runtime=runtime,
                )
            )
        for member, value in teaching_values.items():
            if member == "anonymous_audiovisual_continuity":
                translated, reason = (
                    _translate_legacy_anonymous_av_genesis(
                        value,
                        runtime=runtime,
                    )
                )
                member_reasons[member] = reason
                if translated is None:
                    preliminary[member] = UNRESOLVED
                else:
                    preliminary[member] = DIRECT
                    direct_raw_bodies[
                        _CURRENT_ANONYMOUS_AV_OWNER_PATH
                    ] = translated
            elif member == "auditory_reciprocity":
                member_evidence[member] = (
                    _inspect_retired_auditory_reciprocity(value)
                )
                member_reasons[member] = (
                    "retired label-keyed auditory-only causal-path "
                    "classifier; exact bounded source bytes remain in "
                    "authenticated sealed non-active custody"
                )
                preliminary[member] = ESCROW
            elif member == "auditory_v4_archive":
                member_evidence[member] = (
                    _inspect_retired_auditory_v4_archive(value)
                )
                member_reasons[member] = (
                    "explicit quarantine of an incompatible v4 "
                    "auditory-only classifier and its causally dependent "
                    "action and terminal state; exact bounded source "
                    "bytes remain in authenticated sealed non-active "
                    "custody"
                )
                preliminary[member] = ESCROW
            elif member == "causal_action":
                member_evidence[member] = (
                    _inspect_retired_causal_action(
                        value,
                        authority_key=key,
                    )
                )
                member_reasons[member] = (
                    "retired auditory-class/Unicode action authority has "
                    "no faithful current owner mapping; authenticated "
                    "bounded source bytes remain in sealed non-active "
                    "custody"
                )
                preliminary[member] = ESCROW
            elif member == "causal_organism_growth":
                member_evidence[member] = (
                    _inspect_retired_causal_organism_growth(
                        value,
                        authority_key=key,
                    )
                )
                member_reasons[member] = (
                    "retired duplicate-Embryo growth journal is "
                    "authenticated empty state; its exact source bytes "
                    "remain in sealed non-active custody"
                )
                preliminary[member] = ESCROW
            elif member == "embodied_action_teaching":
                retired_teaching = (
                    _inspect_retired_embodied_action_teaching(
                        value,
                        runtime=runtime,
                    )
                )
                if retired_teaching is None:
                    preliminary[member] = DIRECT
                else:
                    member_evidence[member] = retired_teaching
                    member_reasons[member] = (
                        "authenticated demonstrations use the prior "
                        "duration-free physical command schema; inventing "
                        "action duration would alter learned experience, so "
                        "the exact bounded source remains in non-active "
                        "archive custody"
                    )
                    preliminary[member] = ESCROW
            elif member == "causal_deliberation":
                retired_deliberation = (
                    _inspect_retired_causal_deliberation(
                        value,
                        runtime=runtime,
                    )
                )
                if retired_deliberation is None:
                    preliminary[member] = DIRECT
                else:
                    member_evidence[member] = retired_deliberation
                    member_reasons[member] = (
                        "authenticated deliberation witnesses retain all "
                        "seven DSF fields but predate exact source-index and "
                        "L0-L4 trace provenance; fabricating that provenance "
                        "would be false, so the exact bounded source remains "
                        "in non-active archive custody"
                    )
                    preliminary[member] = ESCROW
            elif (
                member
                in {
                    "causal_action_cycle",
                    "causal_action_cycle_pending_review",
                }
                and retired_action_cycle is not None
            ):
                member_evidence[member] = retired_action_cycle
                member_reasons[member] = (
                    "authenticated action bindings contain prior "
                    "duration-free physical commands or retired scripted "
                    "speech; inventing duration or reactivating scripted "
                    "meaning would alter experience, so the complete owner "
                    "group remains in non-active archive custody"
                )
                preliminary[member] = ESCROW
            elif member in _INACTIVE_ARCHIVE_TEACHING_MEMBERS:
                member_reasons[member] = (
                    "historical learned/physical evidence lacks the "
                    "provenance required by its current owner; exact source "
                    "bytes remain bounded and authenticated in non-active "
                    "archive custody"
                )
                preliminary[member] = ESCROW
            elif member in ACTIVE_OWNER_STATE_KEYS:
                preliminary[member] = DIRECT
            elif member in _RETIRED_TEACHING_MEMBERS:
                if member in {"feedback_log", "correction_log"} and value:
                    preliminary[member] = UNRESOLVED
                elif member == "causal_speech_release" and value is not None:
                    preliminary[member] = UNRESOLVED
                else:
                    preliminary[member] = ESCROW
            else:
                preliminary[member] = UNRESOLVED

        # A current owner body is indivisible.  A partial group is unresolved;
        # a companion field cannot be promoted by borrowing genesis state.
        for group in OWNER_STATE_GROUPS:
            present = set(group.state_keys) & set(teaching_values)
            if present and present != set(group.state_keys):
                for member in present:
                    if preliminary[member] == DIRECT:
                        preliminary[member] = UNRESOLVED

        teaching_accounted = 0
        for member, value in sorted(teaching_values.items()):
            category = preliminary[member]
            group = groups_by_key.get(member)
            if (
                category == DIRECT
                and member == "anonymous_audiovisual_continuity"
            ):
                reason = member_reasons[member]
                target_owner_id = _CURRENT_ANONYMOUS_AV_OWNER_ID
                target_path = _CURRENT_ANONYMOUS_AV_OWNER_PATH
            elif category == DIRECT and group is not None:
                reason = (
                    "exact current owner field; complete owner group present"
                )
                target_owner_id = group.owner_id
                target_path = group.relative_path
                direct_values[member] = value
            elif category == ESCROW:
                reason = member_reasons.get(
                    member,
                    "retired scripted/label authority retained only in "
                    "sealed non-active source custody",
                )
                target_owner_id = None
                target_path = None
            else:
                reason = member_reasons.get(
                    member,
                    "learned or physical custody has no lossless direct "
                    "current-owner mapping",
                )
                target_owner_id = None
                target_path = None
            record = _member_record(
                source_path="guala_teaching.json",
                member=member,
                value=value,
                category=category,
                reason=reason,
                target_owner_id=target_owner_id,
                target_path=target_path,
            )
            if member in member_evidence:
                record["custody_evidence"] = member_evidence[member]
            members.append(record)
            accounted = int(record["accounted_bytes"])
            teaching_accounted += accounted
            category_bytes[category] += accounted
        framing_bytes = len(teaching_body) - teaching_accounted
        if framing_bytes < 0:
            raise LegacyLearnedStateGateError(
                "teaching member accounting exceeds source bytes"
            )
        category_bytes[ESCROW] += framing_bytes
        members.append({
            "accounted_bytes": framing_bytes,
            "category": ESCROW,
            "member": "$container_framing",
            "reason": (
                "legacy JSON envelope, member keys, whitespace, and framing"
            ),
            "source_member_sha256": _sha(teaching_body),
            "source_path": "guala_teaching.json",
            "target_owner_id": None,
            "target_path": None,
        })

    direct_owner_bodies: dict[str, bytes] = dict(direct_raw_bodies)
    for group in OWNER_STATE_GROUPS:
        if not set(group.state_keys).issubset(direct_values):
            continue
        body = _canonical({
            "owner_id": group.owner_id,
            "schema": OWNER_STATE_BODY_SCHEMA,
            "state": {
                member: direct_values[member]
                for member in group.state_keys
            },
        })
        mutation_root = owner_state_body_mutation_root(group, body)
        direct_owner_bodies[group.relative_path] = body
        for record in members:
            if record.get("target_path") == group.relative_path:
                record["target_body_bytes"] = len(body)
                record["target_body_sha256"] = _sha(body)
                record["target_mutation_root_sha256"] = mutation_root
    for record in members:
        path = record.get("target_path")
        if path not in direct_raw_bodies:
            continue
        body = direct_raw_bodies[path]
        record["target_body_bytes"] = len(body)
        record["target_body_sha256"] = _sha(body)
        record["target_mutation_root_sha256"] = _sha(
            b"guala-raw-current-owner-translation-v1\0" + body
        )

    direct_owner_authentication = "not_applicable"
    if direct_owner_bodies:
        if runtime is None:
            raise LegacyLearnedStateGateError(
                "direct learned-owner translation lacks a runtime "
                "authentication authority"
            )
        try:
            current_bodies = runtime._bounded_owner_state_bodies()
            merged = decode_owner_state_bodies(
                {
                    group.relative_path: current_bodies[
                        group.relative_path
                    ]
                    for group in OWNER_STATE_GROUPS
                }
            )
            for path, encoded in direct_owner_bodies.items():
                if path in direct_raw_bodies:
                    continue
                decoded = json.loads(encoded)
                for member, value in decoded["state"].items():
                    merged[member] = value
            from dsf_ai_service.v4.guala_physical_runtime_core import (
                Guala as PhysicalRuntimeCore,
            )
            PhysicalRuntimeCore._restore_whole_organism_state(
                runtime,
                merged,
            )
            restored = runtime._bounded_owner_state_bodies()
        except Exception as error:
            raise LegacyLearnedStateGateError(
                "direct learned-owner translation authentication failed: "
                + str(error)
            ) from error
        migrated_owner_paths: set[str] = set()
        for path, encoded in tuple(direct_owner_bodies.items()):
            if path in direct_raw_bodies:
                if (
                    runtime._w1_anonymous_av_continuity_owner
                    .encoded_snapshot()
                    != encoded
                ):
                    raise LegacyLearnedStateGateError(
                        "direct learned-owner translation changed after "
                        f"authenticated restore: {path}"
                    )
                continue
            restored_body = restored.get(path)
            if not isinstance(restored_body, bytes):
                raise LegacyLearnedStateGateError(
                    "direct learned-owner translation was not "
                    f"resnapshotted: {path}"
                )
            if restored_body != encoded:
                migrated_owner_paths.add(path)
                direct_owner_bodies[path] = restored_body
        group_by_path = {
            group.relative_path: group
            for group in OWNER_STATE_GROUPS
        }
        for record in members:
            path = record.get("target_path")
            if path not in direct_owner_bodies:
                continue
            target = direct_owner_bodies[path]
            record["target_body_bytes"] = len(target)
            record["target_body_sha256"] = _sha(target)
            if path in group_by_path:
                record["target_mutation_root_sha256"] = (
                    owner_state_body_mutation_root(
                        group_by_path[path],
                        target,
                    )
                )
            if path in migrated_owner_paths:
                record["reason"] = (
                    "authenticated source owner accepted by its explicit "
                    "current schema migration and canonically resnapshotted"
                )
        direct_owner_authentication = (
            "current_runtime_restore_and_canonical_target_resnapshot"
        )

    if sum(category_bytes.values()) != source_bytes:
        raise LegacyLearnedStateGateError(
            "learned source byte accounting is not complete"
        )
    escrow_bytes = category_bytes[ESCROW]
    if escrow_bytes > max_sealed_escrow_bytes:
        raise LegacyLearnedStateGateError(
            "sealed learned-state escrow exceeds its explicit ceiling"
        )

    unresolved_members = [
        f"{record['source_path']}:{record['member']}"
        for record in members
        if record["category"] == UNRESOLVED
    ]
    body = {
        "category_bytes": category_bytes,
        "direct_owner_bodies": [
            {
                "bytes": len(encoded),
                "path": path,
                "sha256": _sha(encoded),
            }
            for path, encoded in sorted(direct_owner_bodies.items())
        ],
        "direct_owner_authentication": direct_owner_authentication,
        "identity": identity,
        "learned_source_bytes": source_bytes,
        "learned_source_files": files,
        "max_sealed_escrow_bytes": max_sealed_escrow_bytes,
        "members": members,
        "schema": GATE_SCHEMA,
        "tick": tick,
        "unresolved_member_count": len(unresolved_members),
        "unresolved_members": unresolved_members,
    }
    signature = hmac.new(
        key,
        _GATE_DOMAIN + _canonical(body),
        hashlib.sha256,
    ).hexdigest()
    plan = LegacyLearnedStatePlan(
        body=body,
        authority_hmac_sha256=signature,
        direct_owner_bodies=direct_owner_bodies,
    )
    verify_legacy_learned_state_plan(
        plan.record(),
        authority_key=key,
    )
    if unresolved_members:
        raise LegacyLearnedStateUnresolved(
            "legacy learned-state migration is unresolved: "
            + ", ".join(unresolved_members),
            plan,
        )
    return plan


__all__ = [
    "DIRECT",
    "ESCROW",
    "GATE_SCHEMA",
    "LegacyLearnedStateGateError",
    "LegacyLearnedStatePlan",
    "LegacyLearnedStateUnresolved",
    "UNRESOLVED",
    "build_legacy_learned_state_plan",
    "verify_legacy_learned_state_plan",
]
