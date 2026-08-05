from __future__ import annotations

import base64
import copy
import hashlib
from fractions import Fraction
from pathlib import Path

import pytest

from dsf_ai_service.glew_runtime.closed_experience import (
    run_ratified_native_l0_l4_trace_typed,
)
from dsf_ai_service.glew_runtime.model import (
    ReceiptRegistry,
    receipt_sha256,
)
from dsf_ai_service.glew_runtime.native_sensory_full_field import (
    PROFILE_PAYLOAD,
    NativeSensorySubstreamInput,
    _prepare_port,
    build_transaction_owned_six_sense_full_field,
)
from dsf_ai_service.glew_runtime.sensory_full_field_boundary import (
    NativeAxisCoordinate,
    PhysicalSense,
    SENSE_ORDER,
    SenseBoundaryState,
)
from dsf_ai_service.v4.guala_physical_runtime import Guala
from dsf_ai_service.v4.guala_physical_runtime_core import (
    Guala as CoreGuala,
    NATIVE_MATERIALIZED_FABRIC_V4_MIGRATION,
)
from dsf_ai_service.substrate.owner_free_materialized_fabric_boundary import (
    PRIOR_MATERIALIZED_FABRIC_REFERENCE_SCHEMA,
)
from dsf_ai_service.substrate.owner_scoped_persistence import (
    LEGACY_MISSING_NATIVE_MATERIALIZED_FABRIC_PATH,
)
from dsf_ai_service.substrate.window_manager import physical_topology_fact
from tests.native_joint_occurrence_support import joint_occurrences_for


def _port(
    sense: PhysicalSense,
    *,
    sensor_id: str,
    substream_id: str,
) -> NativeSensorySubstreamInput:
    return NativeSensorySubstreamInput(
        sense=sense,
        sensor_id=sensor_id,
        substream_id=substream_id,
        topology_index=0,
        coordinates=(NativeAxisCoordinate("receptor", "0"),),
        physical_quantity="normalized_pressure"
        if sense is PhysicalSense.SOUND
        else "normalized_light",
        physical_unit="normalized_binary64",
        source_times=(
            Fraction(0),
            Fraction(1, 4),
            Fraction(1, 2),
            Fraction(3, 4),
        ),
        normalized_signal=(0.0, 0.5, -0.25, 0.125),
        phase_turns=(
            Fraction(0),
            Fraction(1, 8),
            Fraction(1, 4),
            Fraction(3, 8),
        ),
    )


def _trusted_trace_digest(
    native: NativeSensorySubstreamInput,
    *,
    assembly_id: str,
) -> str:
    prepared = _prepare_port(native, assembly_id=assembly_id)
    registry = ReceiptRegistry.from_payloads(
        profile_payload=PROFILE_PAYLOAD,
        receipt_payloads=tuple(
            payload
            for payload in prepared.input_payloads
            if payload != PROFILE_PAYLOAD
        ),
    )
    trace = run_ratified_native_l0_l4_trace_typed(
        stream=prepared.stream,
        adapter=prepared.adapter,
        receipt_registry=registry,
    )
    return receipt_sha256(trace.raw_payload)


def test_one_native_batch_preserves_current_organism_trace_identity(
    monkeypatch,
) -> None:
    import dsf_ai_service.glew_runtime.exact_field_executor as retired_executor

    def forbidden_worker_boundary():
        raise AssertionError("multiprocess field executor was called")

    monkeypatch.setattr(
        retired_executor,
        "exact_field_executor",
        forbidden_worker_boundary,
    )
    assembly_id = "native-current-organism-parity"
    sight = _port(
        PhysicalSense.SIGHT,
        sensor_id="retina",
        substream_id="retina-0",
    )
    sound = _port(
        PhysicalSense.SOUND,
        sensor_id="cochlea",
        substream_id="cochlea-0",
    )
    observed = {
        PhysicalSense.SIGHT: (sight,),
        PhysicalSense.SOUND: (sound,),
    }
    states = {
        sense: (
            SenseBoundaryState.OBSERVED
            if sense in observed
            else SenseBoundaryState.QUIESCENT
        )
        for sense in SENSE_ORDER
    }

    built = build_transaction_owned_six_sense_full_field(
        assembly_id=assembly_id,
        source_time_start=Fraction(0),
        source_time_end=Fraction(3, 4),
        observed_substreams=observed, occurrences=joint_occurrences_for(observed),
        states=states,
    )

    built.verify_construction(
        boundary=built.boundary,
        receipt_registry=built.receipt_registry,
    )
    bank = built.native_full_field_bank
    assert bank.python_callback_count == 0
    assert bank.port_count == 2
    assert bank.source_sample_count == 8
    mounted = {
        boundary.sense: tuple(
            substream.l0_l4_trace_receipt_sha256
            for substream in boundary.substreams
        )
        for boundary in built.boundary.boundaries
        if boundary.substreams
    }
    assert mounted == {
        PhysicalSense.SIGHT: (
            _trusted_trace_digest(sight, assembly_id=assembly_id),
        ),
        PhysicalSense.SOUND: (
            _trusted_trace_digest(sound, assembly_id=assembly_id),
        ),
    }


def test_current_organism_cold_restores_exact_native_fabric(
        monkeypatch,
        tmp_path,
) -> None:
    monkeypatch.setenv("EVENT_DRIVEN_SUBSTRATE", "0")
    monkeypatch.setenv(
        "GUALA_CAUSAL_ACTION_KEY",
        "native-fabric-cold-restore-key-123456789012345678901234",
    )
    monkeypatch.setattr(
        "dsf_ai_service.v4.guala_physical_runtime_core."
        "_native_transition_working_memory_bytes",
        lambda: 1024 * 1024 * 1024,
    )
    sight = _port(
        PhysicalSense.SIGHT,
        sensor_id="retina",
        substream_id="retina-0",
    )
    sound = _port(
        PhysicalSense.SOUND,
        sensor_id="cochlea",
        substream_id="cochlea-0",
    )
    observed = {
        PhysicalSense.SIGHT: (sight,),
        PhysicalSense.SOUND: (sound,),
    }
    states = {
        sense: (
            SenseBoundaryState.OBSERVED
            if sense in observed
            else SenseBoundaryState.QUIESCENT
        )
        for sense in SENSE_ORDER
    }
    built = build_transaction_owned_six_sense_full_field(
        assembly_id="native-current-organism-cold-restore",
        source_time_start=Fraction(0),
        source_time_end=Fraction(3, 4),
        observed_substreams=observed, occurrences=joint_occurrences_for(observed),
        states=states,
    )
    source = Guala()
    restored = Guala()
    try:
        source.load_full_state(str(tmp_path / "source"))
        restored.load_full_state(str(tmp_path / "restored"))
        source._advance_native_materialized_fabric(
            built.native_joint_source_episode
        )
        payload = source._teaching_persistence_payload()
        CoreGuala._restore_whole_organism_state(restored, payload)

        assert (
            restored._native_materialized_fabric_state
            == source._native_materialized_fabric_state
        )
        restored_reference = restored._native_materialized_fabric_reference
        source_reference = source._native_materialized_fabric_reference
        assert restored_reference.state_sha256 == source_reference.state_sha256
        assert restored_reference.joint_transition_sha256 == (
            source_reference.joint_transition_sha256
        )
        assert restored_reference.joint_field_count == (
            source_reference.joint_field_count
        )
        assert restored_reference.joint_neuron_count == (
            source_reference.joint_neuron_count
        )
        assert restored_reference.outcome == "joint_neuronal_state_restored"
        assert restored_reference.evidence_count == 0
        assert restored_reference.transitioned_fractal_count == 0
        assert restored._latest_native_materialized_fabric_transition[
            "transition"
        ] == "cold_restore_exact"
    finally:
        source.shutdown()
        restored.shutdown()


def test_prior_native_fabric_requires_and_records_exact_v4_migration(
    monkeypatch,
    tmp_path,
) -> None:
    monkeypatch.setenv("EVENT_DRIVEN_SUBSTRATE", "0")
    monkeypatch.setenv(
        "GUALA_CAUSAL_ACTION_KEY",
        "native-fabric-migration-marker-key-123456789012345678901",
    )
    monkeypatch.setattr(
        "dsf_ai_service.v4.guala_physical_runtime_core."
        "_native_transition_working_memory_bytes",
        lambda: 1024 * 1024 * 1024,
    )
    source = Guala()
    refuser = Guala()
    migrated = Guala()
    try:
        source.load_full_state(str(tmp_path / "source"))
        refuser.load_full_state(str(tmp_path / "refuser"))
        migrated.load_full_state(str(tmp_path / "migrated"))
        observed = {
            PhysicalSense.SIGHT: (_port(
                PhysicalSense.SIGHT,
                sensor_id="retina",
                substream_id="retina-0",
            ),),
        }
        source._advance_native_materialized_fabric(
            build_transaction_owned_six_sense_full_field(
                assembly_id="native-current-organism-v3-migration",
                source_time_start=Fraction(0),
                source_time_end=Fraction(3, 4),
                observed_substreams=observed,
                occurrences=joint_occurrences_for(observed),
                states={
                    sense: (
                        SenseBoundaryState.OBSERVED
                        if sense is PhysicalSense.SIGHT
                        else SenseBoundaryState.QUIESCENT
                    )
                    for sense in SENSE_ORDER
                },
            ).native_joint_source_episode
        )
        current = source._native_materialized_fabric_state
        joint_size = int.from_bytes(current[18:22], "little")
        joint = current[22:22 + joint_size]
        prior = b"".join((
            b"GLMFAB03",
            (3).to_bytes(2, "little"),
            current[10:18],
            (0).to_bytes(4, "little"),
            (0).to_bytes(4, "little"),
            len(joint).to_bytes(4, "little"),
            joint,
        ))
        payload = copy.deepcopy(source._teaching_persistence_payload())
        record = payload["native_materialized_fabric"]
        digest = hashlib.sha256(prior).hexdigest()
        record["state_base64"] = base64.b64encode(prior).decode("ascii")
        record["state_sha256"] = digest
        reference = record["reference"]
        reference["schema"] = PRIOR_MATERIALIZED_FABRIC_REFERENCE_SCHEMA
        reference["state_sha256"] = digest
        reference["byte_count"] = len(prior)
        reference.pop("episode_relation_candidate_sha256")

        with pytest.raises(
            ValueError,
            match="requires an authenticated v2/v3-to-v4 migration",
        ):
            CoreGuala._restore_whole_organism_state(refuser, payload)

        migrated._allow_authenticated_current_schema_migration = True
        CoreGuala._restore_whole_organism_state(migrated, payload)
        assert migrated._native_materialized_fabric_state.startswith(
            b"GLMFAB04"
        )
        assert migrated._authenticated_current_schema_migrations == (
            NATIVE_MATERIALIZED_FABRIC_V4_MIGRATION,
        )
        assert migrated._latest_native_materialized_fabric_transition[
            "transition"
        ] == "cold_restore_one_way_migration"
    finally:
        source.shutdown()
        refuser.shutdown()
        migrated.shutdown()


def test_current_runtime_rejects_owner_scoped_predecessor_without_native_fabric(
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("EVENT_DRIVEN_SUBSTRATE", "0")
    monkeypatch.setenv(
        "GUALA_CAUSAL_ACTION_KEY",
        "native-fabric-predecessor-key-123456789012345678901234",
    )
    organism = Guala()
    try:
        with pytest.raises(
            RuntimeError,
            match="legacy owner-scoped persistence is permanently retired",
        ):
            organism._bounded_owner_state_bodies()
    finally:
        organism.shutdown()


def test_failed_current_organism_settlement_restores_native_fabric_exactly(
        monkeypatch,
        tmp_path,
) -> None:
    monkeypatch.setenv("EVENT_DRIVEN_SUBSTRATE", "0")
    monkeypatch.setenv(
        "GUALA_CAUSAL_ACTION_KEY",
        "native-fabric-rollback-key-123456789012345678901234567",
    )
    monkeypatch.setattr(
        "dsf_ai_service.v4.guala_physical_runtime_core."
        "_native_transition_working_memory_bytes",
        lambda: 1024 * 1024 * 1024,
    )
    organism = Guala()
    organism.load_full_state(str(tmp_path))
    sight = _port(
        PhysicalSense.SIGHT,
        sensor_id="test-retina",
        substream_id="retina-0",
    )
    observed = {PhysicalSense.SIGHT: (sight,)}
    states = {
        sense: (
            SenseBoundaryState.OBSERVED
            if sense in observed
            else SenseBoundaryState.QUIESCENT
        )
        for sense in SENSE_ORDER
    }
    built = build_transaction_owned_six_sense_full_field(
        assembly_id="native-current-organism-rollback-prior",
        source_time_start=Fraction(0),
        source_time_end=Fraction(3, 4),
        observed_substreams=observed, occurrences=joint_occurrences_for(observed),
        states=states,
    )

    class FailingOwner:
        def settle(self, *_args, **_kwargs):
            raise RuntimeError("injected whole-organism settlement failure")

    public = {
        "schema": "guala.native_sensory_input.v2",
        "sense": "sight",
        "sensor_id": "test-retina",
        "substream_id": "retina-0",
        "topology_index": 0,
        "coordinates": [["receptor", "0"]],
        "physical_quantity": "normalized_light",
        "physical_unit": "normalized_binary64",
        "source_anchor_fraction": [0, 1],
        "causal_offsets_fraction": [[0, 1], [1, 4], [1, 2], [3, 4]],
        "normalized_signal": [0.0, 0.5, -0.25, 0.125],
        "phase_turns": [0.0, 0.125, 0.25, 0.375],
    }
    record = {
        "window_id": "native-current-organism-rollback",
        "context_id": "native-current-organism-rollback-context",
        "context_detail": {
            "source_time_start_fraction": [0, 1],
            "source_time_end_fraction": [3, 4],
            "sensor_quiescent": [
                sense.value
                for sense in SENSE_ORDER
                if sense is not PhysicalSense.SIGHT
            ],
        },
        "entries": [{
            "entry_index": 0,
            "modality": "sight",
            "topology": physical_topology_fact(public),
            "full_field": public,
            "detail": {},
        }],
    }
    try:
        organism._advance_native_materialized_fabric(
            built.native_joint_source_episode
        )
        prior_state = organism._native_materialized_fabric_state
        prior_reference = organism._native_materialized_fabric_reference
        prior_observation = dict(
            organism._latest_native_materialized_fabric_transition
        )
        prior_pending = organism._pending_native_materialized_fabric_transition
        organism._causal_experience_owner = FailingOwner()
        monkeypatch.setattr(
            organism.window_manager,
            "_settlement_custodies_for_record",
            lambda _record: (),
        )

        with pytest.raises(
            RuntimeError,
            match="injected whole-organism settlement failure",
        ):
            organism._build_causal_window_settlement(record)

        assert organism._native_materialized_fabric_state == prior_state
        assert organism._native_materialized_fabric_reference == prior_reference
        assert (
            organism._latest_native_materialized_fabric_transition
            == prior_observation
        )
        assert (
            organism._pending_native_materialized_fabric_transition
            is prior_pending
        )
    finally:
        organism.shutdown()


def test_native_fabric_refuses_growth_beyond_organism_storage_boundary(
    monkeypatch,
    tmp_path,
) -> None:
    monkeypatch.setenv("EVENT_DRIVEN_SUBSTRATE", "0")
    monkeypatch.setenv(
        "GUALA_CAUSAL_ACTION_KEY",
        "native-fabric-capacity-key-1234567890123456789012345678",
    )
    import dsf_ai_service.v4.guala_physical_runtime_core as core

    monkeypatch.setattr(
        core,
        "NATIVE_MATERIALIZED_FABRIC_STATE_MAX_BYTES",
        1,
    )
    monkeypatch.setattr(
        core,
        "_native_transition_working_memory_bytes",
        lambda: 1024 * 1024 * 1024,
    )
    sight = _port(
        PhysicalSense.SIGHT,
        sensor_id="test-retina",
        substream_id="retina-0",
    )
    observed = {PhysicalSense.SIGHT: (sight,)}
    states = {
        sense: (
            SenseBoundaryState.OBSERVED
            if sense in observed
            else SenseBoundaryState.QUIESCENT
        )
        for sense in SENSE_ORDER
    }
    built = build_transaction_owned_six_sense_full_field(
        assembly_id="native-current-organism-capacity",
        source_time_start=Fraction(0),
        source_time_end=Fraction(3, 4),
        observed_substreams=observed, occurrences=joint_occurrences_for(observed),
        states=states,
    )
    organism = Guala()
    try:
        organism.load_full_state(str(tmp_path))
        with pytest.raises(
            RuntimeError,
            match="exceeds its organism storage boundary",
        ):
            organism._advance_native_materialized_fabric(
                built.native_joint_source_episode
            )
        assert organism._native_materialized_fabric_state is None
        assert organism._native_materialized_fabric_reference is None
    finally:
        organism.shutdown()


def test_native_working_memory_is_derived_from_current_cgroup(
    monkeypatch,
    tmp_path,
) -> None:
    import dsf_ai_service.v4.guala_physical_runtime_core as core

    ceiling = tmp_path / "memory.max"
    current = tmp_path / "memory.current"
    ceiling.write_bytes(b"1000000\n")
    current.write_bytes(b"345678\n")
    monkeypatch.setattr(
        core,
        "_NATIVE_WORKING_MEMORY_CGROUP_FILES",
        ((str(ceiling), str(current)),),
    )

    assert core._native_transition_working_memory_bytes() == 654322
