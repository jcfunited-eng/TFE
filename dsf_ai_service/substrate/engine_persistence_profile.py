"""Exact finite storage profile owned by the Guala engine.

These are declared production resource boundaries.  They are not estimates
of typical behavior and they do not authorize deletion of learned state.
The compact diary is observational telemetry.  Legacy crash-replay files are
read-only in sealed production; the canonical cold generation is the sole
learned-state authority.
"""

from __future__ import annotations

import json
from dataclasses import dataclass


# Legacy whole-state snapshots are not a production storage owner.  Sealed
# production refuses their creation and restore because the authenticated
# immutable cold-generation store is the sole learned-state recovery
# authority.  The number remains only so unsealed migration tooling can list
# and preserve the historical files without silently deleting them.
LEGACY_ENGINE_SNAPSHOT_RETAINED = 20

# These constants describe the read-only legacy crash-replay format.  They are
# deliberately excluded from the sealed production profile.
LEGACY_ENGINE_EVENT_FILE_BYTES = 10 * 1024 * 1024
LEGACY_ENGINE_EVENT_ROTATED_FILES = 9
LEGACY_ENGINE_EVENT_LIVE_FILES = LEGACY_ENGINE_EVENT_ROTATED_FILES + 1
LEGACY_ENGINE_EVENT_RECORD_BYTES = 64 * 1024

ENGINE_DIARY_RETAINED_DAYS = 7
ENGINE_DIARY_TRANSIENT_DAY_SLOTS = 1
ENGINE_DIARY_MATERIALIZATIONS = (
    ENGINE_DIARY_RETAINED_DAYS + ENGINE_DIARY_TRANSIENT_DAY_SLOTS
)
ENGINE_DIARY_RECORDS_PER_DAY = 4_000
UINT64_MAX = (1 << 64) - 1
OBSERVATIONAL_EVENT_KIND_MAX_BYTES = 128
OBSERVATIONAL_FAILURE_KIND_MAX_BYTES = 64
OBSERVATIONAL_ERROR_TYPE_MAX_BYTES = 128


def _canonical_line(value: dict) -> bytes:
    return (
        json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        )
        + "\n"
    ).encode("ascii")


def _maximum_observational_receipt() -> dict:
    return {
        "schema": "guala.observational_event_receipt.v1",
        "event_kind": "e" * OBSERVATIONAL_EVENT_KIND_MAX_BYTES,
        "tick": UINT64_MAX,
        "timestamp": "9999-12-31T23:59:59Z",
        "detail_sha256": "f" * 64,
        "detail_bytes": UINT64_MAX,
        "authority_receipt_sha256": "f" * 64,
        "failure": {
            "failure_kind": (
                "f" * OBSERVATIONAL_FAILURE_KIND_MAX_BYTES
            ),
            "error_type": "E" * OBSERVATIONAL_ERROR_TYPE_MAX_BYTES,
            "error_message_sha256": "f" * 64,
            "physical_byte_receipt_sha256": "f" * 64,
        },
        "authority_hmac_sha256": "f" * 64,
    }


# Exact canonical encoded maximum of the fixed receipt schema above.  Runtime
# construction rejects fields outside these character/uint64 contracts and
# asserts every encoded line against this derived value.
ENGINE_DIARY_EVENT_BYTES = len(
    _canonical_line(_maximum_observational_receipt())
)
ENGINE_DIARY_DAY_BYTES = (
    ENGINE_DIARY_RECORDS_PER_DAY * ENGINE_DIARY_EVENT_BYTES
)


class EnginePersistenceProfileError(ValueError):
    """The cold-state bound cannot produce a valid engine storage profile."""


def derived_engine_persistence_profile_bytes(
        max_cold_generation_bytes: int) -> int:
    """Return the exact nonduplicated engine-owned persistence peak.

    ``max_cold_generation_bytes`` is validated only as the caller's canonical
    generation contract.  It is intentionally absent from the sum: learned
    state and its transactional materializations are already owned by the
    immutable-generation profile and must never be counted again here.
    """
    if (
        isinstance(max_cold_generation_bytes, bool)
        or not isinstance(max_cold_generation_bytes, int)
        or max_cold_generation_bytes <= 0
    ):
        raise EnginePersistenceProfileError(
            "max cold generation bytes must be a positive integer"
        )
    diary_peak = (
        ENGINE_DIARY_MATERIALIZATIONS * ENGINE_DIARY_DAY_BYTES
    )
    return diary_peak


@dataclass(frozen=True)
class EnginePersistenceProfile:
    max_cold_generation_bytes: int

    @property
    def snapshot_peak_bytes(self) -> int:
        return 0

    @property
    def event_peak_bytes(self) -> int:
        return 0

    @property
    def diary_peak_bytes(self) -> int:
        return ENGINE_DIARY_MATERIALIZATIONS * ENGINE_DIARY_DAY_BYTES

    @property
    def peak_bytes(self) -> int:
        return derived_engine_persistence_profile_bytes(
            self.max_cold_generation_bytes
        )

    def receipt(self) -> dict:
        return {
            "schema": "guala.engine_persistence_profile.v1",
            "accounting": "peak_logical_bytes_by_engine_resource_boundary",
            "max_cold_generation_bytes": self.max_cold_generation_bytes,
            "components": {
                "authenticated_observational_diary_peak_bytes": (
                    self.diary_peak_bytes
                ),
            },
            "peak_bytes": self.peak_bytes,
            "learned_state_authority": "canonical_cold_generation",
            "canonical_learned_state_bytes_counted": 0,
            "legacy_whole_state_snapshots": {
                "production_creation": "refused",
                "production_restore": "refused",
                "existing_files": "read_only_pending_authenticated_migration",
            },
            "legacy_crash_replay_events": {
                "production_writes": "refused",
                "production_replay": "refused",
                "existing_files": "read_only_pending_authenticated_migration",
            },
            "telemetry_retention": {
                "crash_replay_event_files_written": 0,
                "diary_utc_days": ENGINE_DIARY_RETAINED_DAYS,
                "diary_is_learned_state": False,
            },
        }


__all__ = [
    "ENGINE_DIARY_DAY_BYTES",
    "ENGINE_DIARY_EVENT_BYTES",
    "ENGINE_DIARY_MATERIALIZATIONS",
    "ENGINE_DIARY_RECORDS_PER_DAY",
    "ENGINE_DIARY_RETAINED_DAYS",
    "LEGACY_ENGINE_EVENT_FILE_BYTES",
    "LEGACY_ENGINE_EVENT_LIVE_FILES",
    "LEGACY_ENGINE_EVENT_RECORD_BYTES",
    "LEGACY_ENGINE_SNAPSHOT_RETAINED",
    "OBSERVATIONAL_ERROR_TYPE_MAX_BYTES",
    "OBSERVATIONAL_EVENT_KIND_MAX_BYTES",
    "OBSERVATIONAL_FAILURE_KIND_MAX_BYTES",
    "UINT64_MAX",
    "EnginePersistenceProfile",
    "EnginePersistenceProfileError",
    "derived_engine_persistence_profile_bytes",
]
