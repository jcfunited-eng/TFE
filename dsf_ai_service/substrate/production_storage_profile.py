"""Deterministic storage refusal bounds and reachable-content accounting.

Production readiness is not a multiplication of a configured protocol limit.
It is established from verified reachable unique content plus exact manifest
and receipt deltas.  The larger namespace calculation in this module is only
an emergency infrastructure refusal envelope used to prevent an unsafe write;
it is not a storage target, forecast, or steady-state design.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any, Mapping

from dsf_ai_service.substrate.engine_persistence_profile import (
    ENGINE_DIARY_DAY_BYTES,
    ENGINE_DIARY_RETAINED_DAYS,
    derived_engine_persistence_profile_bytes,
)
from dsf_ai_service.substrate.immutable_generation_store import (
    CONTENT_CHUNK_MIN_BYTES,
)
from dsf_ai_service.substrate.persistence_consumer import (
    RING_RECEIPT_SEGMENT_MAX_BYTES,
    ring_checkpoint_max_bytes,
    ring_observation_receipt_max_bytes,
)


class ProductionStorageProfileError(RuntimeError):
    """A required finite persistence refusal boundary is invalid."""


MAX_COLD_GENERATION_BYTES_ENV = "GUALA_MAX_COLD_GENERATION_BYTES"

COLD_RETAINED_GENERATIONS = 2
COLD_TRANSACTION_GENERATIONS = 3
ACTIVE_MATERIALIZATION_RETAINED_TREES = 0
ACTIVE_MATERIALIZATION_TRANSIENT_TREES = 1
LIVE_RECOVERY_RETAINED_GENERATIONS = 3
LIVE_RECOVERY_TRANSACTION_GENERATIONS = 4
RING_TRANSIENT_CHECKPOINTS = 3
LEDGER_TRANSIENT_COPIES = 2
PICTURE_INGRESS_MAX_FILE_BYTES = 10 * 1024 * 1024

MAX_COLD_REQUIRED_FILES = 16_384
MAX_COLD_REQUIRED_PATH_BYTES = 2 * 1024 * 1024
MAX_GAP_WORD_UTF8_BYTES = 512 * 4
KNOWLEDGE_GAP_ENTRY_CAP = 400
KNOWLEDGE_GAP_TUTOR_DAY_CAP = 14
READING_PREDICTION_DAY_CAP = 60
UINT64_MAX = (1 << 64) - 1

S3_MAX_BUCKET_BYTES = 63
S3_MAX_OBJECT_KEY_UTF8_BYTES = 1_024
DEPLOYMENT_SEAL_RETAINED_COPIES = 3
DEPLOYMENT_SEAL_TRANSIENT_COPIES = 5

LINUX_MAX_PID = 1 << 22
POSIX_HOST_NAME_MAX_BYTES = 64
LINUX_PATH_MAX_BYTES = 4_096
NAMESPACE_CEILING_MAX = UINT64_MAX


def _canonical_compact(value: Any) -> bytes:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _canonical_indented(value: Any) -> bytes:
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


def _positive_environment(
    environment: Mapping[str, str],
    name: str,
) -> int:
    raw = environment.get(name)
    try:
        value = int(raw)
    except (TypeError, ValueError) as error:
        raise ProductionStorageProfileError(
            f"{name} must be configured as a positive integer") from error
    if value <= 0:
        raise ProductionStorageProfileError(
            f"{name} must be configured as a positive integer")
    if value > UINT64_MAX:
        raise ProductionStorageProfileError(
            f"{name} exceeds the uint64 production storage protocol")
    return value


def _knowledge_gap_ledger_bytes() -> int:
    entries = {}
    for index in range(KNOWLEDGE_GAP_ENTRY_CAP):
        suffix = f"{index:04x}"
        word = "w" * (MAX_GAP_WORD_UTF8_BYTES - len(suffix)) + suffix
        entries[word] = {
            "addressed_ts": UINT64_MAX,
            "count": UINT64_MAX,
            "first_ts": UINT64_MAX,
            "kind": "recognition_miss",
            "last_ts": UINT64_MAX,
        }
    tutor_days = {
        f"9999-12-{day:02d}": UINT64_MAX
        for day in range(1, KNOWLEDGE_GAP_TUTOR_DAY_CAP + 1)
    }
    return len(_canonical_compact({
        "entries": entries,
        "tutor_days": tutor_days,
    }))


def _reading_prediction_ledger_bytes() -> int:
    days = {
        f"9999-{month:02d}-{day:02d}": {
            "attempts": UINT64_MAX,
            "covered": UINT64_MAX,
            "hits": UINT64_MAX,
        }
        for month in range(1, 13)
        for day in range(1, 6)
    }
    if len(days) != READING_PREDICTION_DAY_CAP:
        raise AssertionError("reading-prediction profile lost its day bound")
    return len(_canonical_compact({"days": days}))


def _maximum_content_object_count(
    max_cold_generation_bytes: int,
) -> int:
    chunk_count = (
        max_cold_generation_bytes
        + MAX_COLD_REQUIRED_FILES * (CONTENT_CHUNK_MIN_BYTES - 1)
    ) // CONTENT_CHUNK_MIN_BYTES
    return chunk_count + 1


def _deployment_certificate_bytes(
    max_cold_generation_bytes: int,
) -> int:
    object_count = _maximum_content_object_count(
        max_cold_generation_bytes)
    worst_key = "\x01" * S3_MAX_OBJECT_KEY_UTF8_BYTES
    object_record_bytes = len(_canonical_compact({
        "key": worst_key,
        "sha256": "f" * 64,
        "size_bytes": max_cold_generation_bytes,
    }))
    object_list_bytes = (
        2
        + object_count * object_record_bytes
        + max(0, object_count - 1)
    )
    fixed_envelope = {
        "algorithm": "HMAC-SHA256",
        "attempt_operational_metadata_sha256": "f" * 64,
        "bucket": "b" * S3_MAX_BUCKET_BYTES,
        "causal_state_sha256": "f" * 64,
        "generation_uuid": "f" * 36,
        "identity": "",
        "manifest_sha256": "f" * 64,
        "nonce_base64": "f" * 88,
        "objects": [],
        "operational_metadata_sha256": "f" * 64,
        "recovery_certificate_sha256": "f" * 64,
        "schema": "deployment_generation_seal_v3",
        "seal_hmac_sha256": "f" * 64,
        "state_revision": UINT64_MAX,
        "tick": UINT64_MAX,
        "versioned_prefix": "\x01" * S3_MAX_OBJECT_KEY_UTF8_BYTES,
    }
    return (
        len(_canonical_compact(fixed_envelope))
        - len(_canonical_compact([]))
        + object_list_bytes
    )


def _owner_record_bytes() -> int:
    return len(_canonical_compact({
        "hostname": "h" * POSIX_HOST_NAME_MAX_BYTES,
        "pid": LINUX_MAX_PID,
        "schema": "deployment_generation_efs_owner_v1",
    })) + 1


def _authority_metadata_bytes() -> int:
    worst_scope = "/" + "\x01" * (LINUX_PATH_MAX_BYTES - 1)
    return len(_canonical_indented({
        "accounting": "unique_regular_file_logical_bytes",
        "ceiling_bytes": NAMESPACE_CEILING_MAX,
        "schema": "physical_byte_ceiling_v1",
        "scope_root": worst_scope,
    }))


@dataclass(frozen=True)
class ProductionStorageProfile:
    """Writer bounds plus a separately labelled infrastructure refusal."""

    max_cold_generation_bytes: int
    max_live_recovery_generation_bytes: int
    ring_event_record_bytes: int
    ring_event_segment_bytes: int
    ring_checkpoint_bytes: int
    knowledge_gap_ledger_bytes: int
    reading_prediction_ledger_bytes: int
    deployment_certificate_bytes: int
    owner_record_bytes: int
    authority_metadata_bytes: int
    engine_persistence_profile_bytes: int

    @classmethod
    def from_environment(
        cls,
        environment: Mapping[str, str] | None = None,
    ) -> "ProductionStorageProfile":
        source = os.environ if environment is None else environment
        cold = _positive_environment(source, MAX_COLD_GENERATION_BYTES_ENV)
        profile = cls(
            max_cold_generation_bytes=cold,
            max_live_recovery_generation_bytes=cold,
            ring_event_record_bytes=ring_observation_receipt_max_bytes(),
            ring_event_segment_bytes=RING_RECEIPT_SEGMENT_MAX_BYTES,
            ring_checkpoint_bytes=ring_checkpoint_max_bytes(),
            knowledge_gap_ledger_bytes=_knowledge_gap_ledger_bytes(),
            reading_prediction_ledger_bytes=(
                _reading_prediction_ledger_bytes()),
            deployment_certificate_bytes=(
                _deployment_certificate_bytes(cold)),
            owner_record_bytes=_owner_record_bytes(),
            authority_metadata_bytes=_authority_metadata_bytes(),
            engine_persistence_profile_bytes=(
                derived_engine_persistence_profile_bytes(cold)),
        )
        if (
            profile.emergency_namespace_refusal_bytes
            > NAMESPACE_CEILING_MAX
        ):
            raise ProductionStorageProfileError(
                "derived emergency namespace refusal exceeds the uint64 "
                "production storage protocol")
        return profile

    @property
    def deployment_metadata_peak_bytes(self) -> int:
        return (
            DEPLOYMENT_SEAL_TRANSIENT_COPIES
            * self.deployment_certificate_bytes
        )

    def emergency_refusal_components(self) -> dict[str, int]:
        """Worst-case refusal envelope, never a readiness or sizing claim."""
        return {
            "cold_generation_store_peak": (
                COLD_TRANSACTION_GENERATIONS
                * self.max_cold_generation_bytes
            ),
            "active_materialization_peak": (
                ACTIVE_MATERIALIZATION_TRANSIENT_TREES
                * self.max_cold_generation_bytes
            ),
            "live_recovery_store_peak": (
                LIVE_RECOVERY_TRANSACTION_GENERATIONS
                * self.max_live_recovery_generation_bytes
            ),
            "ring_persistence_peak": (
                self.ring_event_segment_bytes
                + RING_TRANSIENT_CHECKPOINTS * self.ring_checkpoint_bytes
            ),
            "knowledge_gap_ledger_peak": (
                LEDGER_TRANSIENT_COPIES
                * self.knowledge_gap_ledger_bytes
            ),
            "reading_prediction_ledger_peak": (
                LEDGER_TRANSIENT_COPIES
                * self.reading_prediction_ledger_bytes
            ),
            "picture_ingress_peak": (
                self.max_cold_generation_bytes
                + PICTURE_INGRESS_MAX_FILE_BYTES
            ),
            "deployment_metadata_peak": self.deployment_metadata_peak_bytes,
            "owner_record_peak": self.owner_record_bytes,
            "authority_metadata_peak": self.authority_metadata_bytes,
            "engine_persistence_peak": self.engine_persistence_profile_bytes,
        }

    def emergency_retained_refusal_components(self) -> dict[str, int]:
        """Refusal-only retained envelope after transaction cleanup."""
        return {
            "cold_generation_store_retained": (
                COLD_RETAINED_GENERATIONS
                * self.max_cold_generation_bytes
            ),
            "active_materialization_retained": 0,
            "live_recovery_store_retained": (
                LIVE_RECOVERY_RETAINED_GENERATIONS
                * self.max_live_recovery_generation_bytes
            ),
            "ring_persistence_retained": (
                self.ring_event_segment_bytes + self.ring_checkpoint_bytes
            ),
            "knowledge_gap_ledger_retained": (
                self.knowledge_gap_ledger_bytes),
            "reading_prediction_ledger_retained": (
                self.reading_prediction_ledger_bytes),
            "picture_library_retained": self.max_cold_generation_bytes,
            "deployment_metadata_retained": (
                DEPLOYMENT_SEAL_RETAINED_COPIES
                * self.deployment_certificate_bytes
            ),
            "owner_record_retained": self.owner_record_bytes,
            "authority_metadata_retained": self.authority_metadata_bytes,
            "engine_diary_retained": (
                ENGINE_DIARY_RETAINED_DAYS * ENGINE_DIARY_DAY_BYTES
            ),
        }

    @property
    def emergency_nonengine_refusal_components(self) -> dict[str, int]:
        return {
            name: value
            for name, value in self.emergency_refusal_components().items()
            if name != "engine_persistence_peak"
        }

    @property
    def emergency_nonengine_refusal_bytes(self) -> int:
        return sum(self.emergency_nonengine_refusal_components.values())

    @property
    def emergency_namespace_refusal_bytes(self) -> int:
        return sum(self.emergency_refusal_components().values())

    @property
    def emergency_retained_refusal_bytes(self) -> int:
        return sum(self.emergency_retained_refusal_components().values())

    # Compatibility names used by the physical writer.  They intentionally
    # preserve refusal behavior while keeping readiness accounting separate.
    def components(self) -> dict[str, int]:
        return self.emergency_refusal_components()

    def retained_components(self) -> dict[str, int]:
        return self.emergency_retained_refusal_components()

    @property
    def nonengine_components(self) -> dict[str, int]:
        return self.emergency_nonengine_refusal_components

    @property
    def nonengine_ceiling_bytes(self) -> int:
        return self.emergency_nonengine_refusal_bytes

    @property
    def namespace_ceiling_bytes(self) -> int:
        return self.emergency_namespace_refusal_bytes

    @property
    def retained_ceiling_bytes(self) -> int:
        return self.emergency_retained_refusal_bytes

    def receipt(self) -> dict[str, Any]:
        return {
            "schema": "guala.production_storage_profile.v4",
            "production_readiness_accounting": {
                "authority": (
                    "verified_reachable_unique_content_plus_manifest_and_"
                    "authenticated_receipt_deltas"
                ),
                "zero_learning_rule": (
                    "zero changed learned files and zero new learned-content "
                    "chunk bytes"
                ),
                "causal_mutation_rule": (
                    "every changed learned file and newly retained learned "
                    "chunk is covered by an authenticated causal mutation "
                    "receipt"
                ),
                "static_readiness_total_bytes": None,
            },
            "emergency_infrastructure_refusal_envelope": {
                "classification": (
                    "write_refusal_only_not_storage_target_or_steady_state"
                ),
                "peak_components": self.emergency_refusal_components(),
                "peak_bytes": self.emergency_namespace_refusal_bytes,
                "retained_components": (
                    self.emergency_retained_refusal_components()),
                "retained_bytes": self.emergency_retained_refusal_bytes,
            },
            "unresolved_external_capacity": None,
        }


__all__ = [
    "MAX_COLD_GENERATION_BYTES_ENV",
    "ProductionStorageProfile",
    "ProductionStorageProfileError",
]
