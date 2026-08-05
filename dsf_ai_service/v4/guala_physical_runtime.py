"""Production transport shell around one native resident Guala organism.

The historical Python class temporarily supplies bounded sensor, body, HTTP,
and checkpoint adapters.  Cognitive state is exactly one resident native
``GLORUN01`` body.  Checkpoints carry that body as one raw binary file and a
small exact receipt in ``guala_core.json``; Python does not serialize a second
cognitive body, recall database, semantic owner, or successor authority.
"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
import stat

from dsf_ai_service.v4 import guala_physical_runtime_core as _core
from dsf_ai_service.v4.guala_physical_runtime_core import *


NATIVE_RESIDENT_ORGANISM_SCHEMA = "guala.native_resident_organism.v3"
NATIVE_RESIDENT_ORGANISM_FILE = "guala_organism.glorun"
NATIVE_RESIDENT_RAW_PERSISTENCE_CUTOVER = (
    "native_resident_base64_to_raw_glorun_v1"
)
TASK853_NATIVE_RESIDENT_CUTOVER = (
    "authenticated_task853_native_resident_cutover_v1"
)
_LEGACY_BASE64_RESIDENT_SCHEMA = "guala.native_resident_organism.v1"
_RESTORED_RAW_STATE_SCHEMA = "guala.restored_raw_resident_organism.v1"
_RAW_POINTER_KEYS = frozenset({
    "byte_count",
    "file",
    "state_sha256",
})


class Guala(_core.Guala):
    """One Python transport shell retaining exactly one native organism."""

    STATE_FILES = ["guala_core.json", NATIVE_RESIDENT_ORGANISM_FILE]
    FULL_SAVE_MANIFEST_FILES = (
        "guala_core.json",
        NATIVE_RESIDENT_ORGANISM_FILE,
    )
    HOT_SAVE_MANIFEST_FILES = FULL_SAVE_MANIFEST_FILES

    def __init__(self, **options):
        super().__init__(**options)
        self._native_resident_organism = None
        self._native_resident_prepare = None
        self._latest_native_resident_transition = None
        self._native_resident_restore_tick = None
        self._native_resident_resource = None
        self._native_resident_state_directory = None
        self._native_resident_persistence_snapshot = None

    def _native_resident_budgets(self):
        if self._native_resident_resource is None:
            from dsf_ai_service.substrate.native_resident_resource_admission import (
                derive_native_resident_resource_admission,
            )

            directory = self._native_resident_state_directory or "."
            self._native_resident_resource = (
                derive_native_resident_resource_admission(directory)
            )
        resource = self._native_resident_resource
        return (
            resource.max_envelope_bytes,
            resource.max_fabric_bytes,
            resource.max_logical_peak_bytes,
        )

    @staticmethod
    def _native_resident_observation_record(observation):
        return {
            "cognitive_formation_claimed": (
                observation.cognitive_formation_claimed
            ),
            "cognitive_mosaic_count": observation.cognitive_mosaic_count,
            "cognitive_ordinal": observation.cognitive_ordinal,
            "cognitive_trace_count": observation.cognitive_trace_count,
            "fabric_bytes": observation.fabric_bytes,
            "fabric_generation": observation.fabric_generation,
            "fabric_sha256": observation.fabric_sha256,
            "formation_activation_count": (
                observation.formation_activation_count
            ),
            "identity": observation.identity,
            "joint_field_count": observation.joint_field_count,
            "joint_neuron_count": observation.joint_neuron_count,
            "mounted_generation": observation.mounted_generation,
            "organism_tick": observation.organism_tick,
            "partial_cue_reassembly_count": (
                observation.partial_cue_reassembly_count
            ),
            "python_callback_count": observation.python_callback_count,
            "schema": observation.schema,
            "state_bytes": observation.state_bytes,
            "state_sha256": observation.state_sha256,
        }

    def native_resident_readiness(self):
        organism = self._native_resident_organism
        if organism is None:
            return {
                "available": False,
                "schema": "guala.native.resident_readiness.v2",
            }
        resource = self._native_resident_resource
        resource_record = (
            {
                "runtime_available_bytes_at_mount": (
                    resource.runtime_available_bytes
                ),
                "derivation": resource.derivation,
                "memory_boundary_source": resource.memory_boundary_source,
                "max_envelope_bytes": resource.max_envelope_bytes,
                "max_fabric_bytes": resource.max_fabric_bytes,
                "max_logical_peak_bytes": resource.max_logical_peak_bytes,
                "persistence_available_bytes_at_mount": (
                    resource.persistence_available_bytes
                ),
            }
            if resource is not None
            else None
        )
        return {
            "available": True,
            **self._native_resident_observation_record(organism.readiness()),
            "persistence": {
                "body_file": NATIVE_RESIDENT_ORGANISM_FILE,
                "encoding": "raw_glorun01",
                "schema": NATIVE_RESIDENT_ORGANISM_SCHEMA,
            },
            "resource_admission": resource_record,
        }

    def _capture_native_resident_persistence(self):
        organism = self._native_resident_organism
        if organism is None:
            raise RuntimeError("native resident organism is not mounted")
        envelope_limit, _fabric_limit, _logical_limit = (
            self._native_resident_budgets()
        )
        before = organism.readiness()
        state = organism.save()
        after = organism.readiness()
        if (
            before.state_bytes != after.state_bytes
            or before.state_sha256 != after.state_sha256
            or not isinstance(state, bytes)
            or not state.startswith(b"GLORUN01")
            or len(state) > envelope_limit
            or len(state) != before.state_bytes
            or hashlib.sha256(state).hexdigest() != before.state_sha256
        ):
            raise RuntimeError(
                "native resident state changed during raw checkpoint capture"
            )
        pointer = {
            "byte_count": len(state),
            "file": NATIVE_RESIDENT_ORGANISM_FILE,
            "state_sha256": before.state_sha256,
        }
        return state, {
            "native_resident_organism": pointer,
            "schema": NATIVE_RESIDENT_ORGANISM_SCHEMA,
        }

    def _teaching_persistence_payload(self):
        snapshot = self._native_resident_persistence_snapshot
        if snapshot is None:
            raise RuntimeError(
                "native resident persistence payload was requested outside "
                "one raw checkpoint capture"
            )
        return snapshot

    def _save_whole_organism_state(
        self,
        state_dir,
        *,
        include_organism,
        publish_generation,
    ):
        self._native_resident_state_directory = os.fspath(state_dir)
        with self.staged_persistence_flip():
            state, pointer = self._capture_native_resident_persistence()
            self._native_resident_persistence_snapshot = pointer
            try:
                self._write_canonical_binary_file(
                    os.path.join(state_dir, NATIVE_RESIDENT_ORGANISM_FILE),
                    state,
                )
                result = _core.Guala._save_whole_organism_state(
                    self,
                    state_dir,
                    include_organism=include_organism,
                    publish_generation=publish_generation,
                )
            finally:
                self._native_resident_persistence_snapshot = None
        return {
            **result,
            NATIVE_RESIDENT_ORGANISM_FILE: len(state),
        }

    @staticmethod
    def _read_exact_raw_resident(state_dir, pointer):
        if (
            not isinstance(pointer, dict)
            or set(pointer) != _RAW_POINTER_KEYS
            or pointer.get("file") != NATIVE_RESIDENT_ORGANISM_FILE
            or isinstance(pointer.get("byte_count"), bool)
            or not isinstance(pointer.get("byte_count"), int)
            or pointer["byte_count"] <= 0
            or not isinstance(pointer.get("state_sha256"), str)
            or len(pointer["state_sha256"]) != 64
            or any(
                character not in "0123456789abcdef"
                for character in pointer["state_sha256"]
            )
        ):
            raise ValueError("native resident raw pointer changed")
        path = Path(state_dir) / NATIVE_RESIDENT_ORGANISM_FILE
        information = path.lstat()
        if (
            path.is_symlink()
            or not stat.S_ISREG(information.st_mode)
            or information.st_size != pointer["byte_count"]
        ):
            raise ValueError("native resident raw body changed file identity")
        body = path.read_bytes()
        if (
            len(body) != pointer["byte_count"]
            or not body.startswith(b"GLORUN01")
            or hashlib.sha256(body).hexdigest()
            != pointer["state_sha256"]
        ):
            raise ValueError("native resident raw body or receipt changed")
        return body

    def _read_whole_organism_state(
        self,
        state_dir,
        core,
        *,
        allow_authenticated_legacy_import,
    ):
        self._native_resident_state_directory = os.fspath(state_dir)
        data = self._unwrap(core, "guala_core.json")
        organism_state = (
            data.get("organism_state") if isinstance(data, dict) else None
        )
        if (
            isinstance(organism_state, dict)
            and organism_state.get("schema")
            == NATIVE_RESIDENT_ORGANISM_SCHEMA
        ):
            if (
                set(data) != {
                    "continuity_contract",
                    "organism_state",
                    "organism_state_bytes",
                    "organism_state_sha256",
                    "state_file_ticks",
                    "tick",
                }
                or data.get("continuity_contract")
                != self.WHOLE_ORGANISM_STATE_CONTRACT
                or isinstance(data.get("tick"), bool)
                or not isinstance(data.get("tick"), int)
                or data["tick"] < 0
                or set(organism_state) != {
                    "native_resident_organism",
                    "schema",
                }
            ):
                raise ValueError(
                    "native resident whole-organism shape changed"
                )
            organism_bytes = self._canonical_persistence_bytes(
                organism_state
            )
            expected_ticks = {
                "guala_core.json": data["tick"],
                NATIVE_RESIDENT_ORGANISM_FILE: data["tick"],
            }
            if (
                data.get("organism_state_bytes") != len(organism_bytes)
                or data.get("organism_state_sha256")
                != hashlib.sha256(organism_bytes).hexdigest()
                or data.get("state_file_ticks") != expected_ticks
            ):
                raise ValueError(
                    "native resident whole-organism integrity changed"
                )
            body = self._read_exact_raw_resident(
                state_dir,
                organism_state["native_resident_organism"],
            )
            self._native_resident_restore_tick = data["tick"]
            return data["tick"], {
                "body": body,
                "schema": _RESTORED_RAW_STATE_SCHEMA,
            }
        if (
            isinstance(organism_state, dict)
            and organism_state.get("schema")
            == _LEGACY_BASE64_RESIDENT_SCHEMA
        ):
            if not allow_authenticated_legacy_import:
                raise ValueError(
                    "base64 resident persistence requires explicit one-way "
                    "raw persistence migration"
                )
            self._authenticated_current_schema_migrations = (
                *getattr(
                    self,
                    "_authenticated_current_schema_migrations",
                    (),
                ),
                NATIVE_RESIDENT_RAW_PERSISTENCE_CUTOVER,
            )
            self._native_resident_restore_tick = data.get("tick")
            return data["tick"], organism_state
        tick, state = super()._read_whole_organism_state(
            state_dir,
            core,
            allow_authenticated_legacy_import=(
                allow_authenticated_legacy_import
            ),
        )
        self._native_resident_restore_tick = tick
        return tick, state

    def _restore_whole_organism_state(self, state):
        envelope_limit, fabric_limit, logical_limit = (
            self._native_resident_budgets()
        )
        if (
            isinstance(state, dict)
            and set(state) == {"body", "schema"}
            and state.get("schema") == _RESTORED_RAW_STATE_SCHEMA
        ):
            from dsf_ai_service.glew_runtime.native_resident_organism import (
                restore_native_resident_organism,
            )

            organism = restore_native_resident_organism(
                current_envelope=state["body"],
                max_envelope_bytes=envelope_limit,
                max_fabric_bytes=fabric_limit,
                max_logical_peak_bytes=logical_limit,
            )
        elif (
            isinstance(state, dict)
            and set(state) == {"native_resident_organism", "schema"}
            and state.get("schema") == _LEGACY_BASE64_RESIDENT_SCHEMA
        ):
            from dsf_ai_service.substrate.native_resident_organism_persistence import (
                restore_native_resident_organism_record,
            )

            organism = restore_native_resident_organism_record(
                state["native_resident_organism"],
                max_envelope_bytes=envelope_limit,
                max_fabric_bytes=fabric_limit,
                max_logical_peak_bytes=logical_limit,
            )
        elif (
            isinstance(state, dict)
            and set(state) == {"native_materialized_fabric", "schema"}
            and state.get("schema") == self.NATIVE_EXACT_ORGANISM_SCHEMA
        ):
            if not getattr(
                self,
                "_allow_authenticated_current_schema_migration",
                False,
            ):
                raise ValueError(
                    "task-853 resident cutover requires explicit "
                    "authenticated migration"
                )
            predecessor_record = state["native_materialized_fabric"]
            if predecessor_record is None:
                from dsf_ai_service.glew_runtime.native_resident_organism import (
                    create_native_resident_organism,
                )

                organism = create_native_resident_organism(
                    organism_identity=self._guala_identity,
                    organism_tick=self._native_resident_restore_tick or 0,
                    max_envelope_bytes=envelope_limit,
                    max_fabric_bytes=fabric_limit,
                    max_logical_peak_bytes=logical_limit,
                )
            else:
                from dsf_ai_service.glew_runtime.authenticated_task853_organism_migration import (
                    migrate_authenticated_task853_predecessor,
                )
                from dsf_ai_service.glew_runtime.native_resident_organism import (
                    restore_native_resident_organism,
                )
                from dsf_ai_service.substrate.owner_free_materialized_fabric_boundary import (
                    extract_authenticated_predecessor_fabric_bytes,
                )

                predecessor = extract_authenticated_predecessor_fabric_bytes(
                    predecessor_record
                )
                migration = migrate_authenticated_task853_predecessor(
                    legacy_glmfab03=predecessor
                )
                organism = restore_native_resident_organism(
                    current_envelope=migration.envelope,
                    max_envelope_bytes=envelope_limit,
                    max_fabric_bytes=fabric_limit,
                    max_logical_peak_bytes=logical_limit,
                )
                self._authenticated_current_schema_migrations = (
                    *getattr(
                        self,
                        "_authenticated_current_schema_migrations",
                        (),
                    ),
                    TASK853_NATIVE_RESIDENT_CUTOVER,
                )
        else:
            raise ValueError("native resident organism state changed")
        observation = organism.readiness()
        if observation.identity != self._guala_identity:
            raise ValueError(
                "native resident identity differs from body identity"
            )
        self._native_resident_organism = organism
        self._native_resident_prepare = None
        self._latest_native_resident_transition = {
            **self._native_resident_observation_record(observation),
            "transition": "cold_restore",
        }
        self._native_materialized_fabric_state = None
        self._native_materialized_fabric_reference = None
        self._latest_native_materialized_fabric_transition = None
        self._pending_native_materialized_fabric_transition = None

    def load_full_state(self, *args, **kwargs):
        state_directory = (
            args[0]
            if args
            else kwargs.get("state_dir", "state")
        )
        self._native_resident_state_directory = os.fspath(state_directory)
        self._native_resident_budgets()
        result = super().load_full_state(*args, **kwargs)
        if self._load_successful and self._native_resident_organism is None:
            from dsf_ai_service.glew_runtime.native_resident_organism import (
                create_native_resident_organism,
            )

            envelope_limit, fabric_limit, logical_limit = (
                self._native_resident_budgets()
            )
            self._native_resident_organism = (
                create_native_resident_organism(
                    organism_identity=self._guala_identity,
                    organism_tick=self.tick,
                    max_envelope_bytes=envelope_limit,
                    max_fabric_bytes=fabric_limit,
                    max_logical_peak_bytes=logical_limit,
                )
            )
            self._latest_native_resident_transition = {
                **self._native_resident_observation_record(
                    self._native_resident_organism.readiness()
                ),
                "transition": "genesis",
            }
        return result

    def _advance_native_materialized_fabric(self, source):
        organism = self._native_resident_organism
        if organism is None:
            raise RuntimeError("native resident organism is not mounted")
        if self._native_resident_prepare is not None:
            raise RuntimeError(
                "native resident organism already has a pending step"
            )
        prepared = organism.prepare(source)
        self._native_resident_prepare = prepared
        return prepared

    def _commit_pending_native_organism_transition(self):
        prepared = self._native_resident_prepare
        if prepared is None:
            raise RuntimeError(
                "native resident organism has no prepared step"
            )
        observation = self._native_resident_organism.commit(prepared.token)
        if (
            observation.state_sha256 != prepared.prepared_state_sha256
            or observation.organism_tick != prepared.organism_tick
            or observation.fabric_generation != prepared.fabric_generation
            or observation.mounted_generation != prepared.mounted_generation
        ):
            raise RuntimeError(
                "native resident commit differs from preparation"
            )
        self._latest_native_resident_transition = {
            **self._native_resident_observation_record(observation),
            "current_cohort_evaluation_count": (
                prepared.current_cohort_evaluation_count
            ),
            "dsf_delivery_count": prepared.dsf_delivery_count,
            "complete_neuron_fractal_count": (
                prepared.complete_neuron_fractal_count
            ),
            "recurrent_complete_neuron_fractal_count": (
                prepared.recurrent_complete_neuron_fractal_count
            ),
            "transition": "joint_field_delivery_without_neuronal_cognition",
        }
        self._native_resident_prepare = None

    def _discard_pending_native_organism_transition(self):
        prepared = self._native_resident_prepare
        if prepared is None:
            return
        self._native_resident_organism.discard(prepared.token)
        self._native_resident_prepare = None


def __getattr__(name):
    return getattr(_core, name)


__all__ = tuple(
    name for name in dir(_core)
    if not name.startswith("_") and name != "Guala"
) + (
    "Guala",
    "NATIVE_RESIDENT_ORGANISM_FILE",
    "NATIVE_RESIDENT_ORGANISM_SCHEMA",
    "NATIVE_RESIDENT_RAW_PERSISTENCE_CUTOVER",
    "TASK853_NATIVE_RESIDENT_CUTOVER",
)
