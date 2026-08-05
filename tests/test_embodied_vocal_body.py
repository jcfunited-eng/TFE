from __future__ import annotations

import base64
import hashlib
import inspect
import io
import json
import struct
import wave
from dataclasses import replace
from fractions import Fraction
from pathlib import Path

import pytest

from dsf_ai_service.substrate.articulatory_self_vocal_motor import (
    ArticulatoryBodyTrajectoryInterval,
    ArticulatoryProgram,
    LaryngealExcitationConfiguration,
    VocalTractConfiguration,
)
from dsf_ai_service.substrate.embodied_vocal_body import (
    EmbodiedVocalBodyAuthority,
)
from dsf_ai_service.substrate.embodiment_world import (
    MAX_VOCAL_SAMPLE_COUNT,
    EmbodimentWorldAuthority,
    MoveCommand,
    PickCommand,
    PoseMM,
    PositionMM,
    encode_command,
)
from dsf_ai_service.glew_runtime.global_uf import DSF_FIELD_ORDER
from dsf_ai_service.glew_runtime.native_sensory_full_field import (
    MAX_NATIVE_SAMPLES_PER_SUBSTREAM,
)
from dsf_ai_service.glew_runtime.sensory_full_field_boundary import (
    PhysicalSense,
)
from dsf_ai_service.v4.guala_physical_runtime import Guala
from tests.physical_inquiry_test_support import (
    RUNTIME_KEY,
    _seed_held_thing_and_inquiry,
)
from tests.test_live_multisensory_inquiry_custody import (
    _physical_frames,
)
from dsf_ai_service.substrate.w1_recorded_vocal_provenance import (
    _decode_pcm,
)
from tests.test_articulatory_consequence_closure import _vocal_pcm


KEY = b"body-owned-inquiry-efferent-production-key"
WORLD_KEY = b"body-owned-inquiry-efferent-world-key"
DADDY = Path(
    "/tmp/guala-production-capture-profile-20260725/"
    "docs/Daddy says Hello.mp3"
)


def _runtime(monkeypatch) -> Guala:
    monkeypatch.setenv("EVENT_DRIVEN_SUBSTRATE", "0")
    monkeypatch.setenv("GUALA_CAUSAL_ACTION_KEY", RUNTIME_KEY)
    return Guala()


def _wav(pcm_s16le: bytes) -> bytes:
    payload = io.BytesIO()
    with wave.open(payload, "wb") as stream:
        stream.setnchannels(1)
        stream.setsampwidth(2)
        stream.setframerate(16_000)
        stream.writeframes(pcm_s16le)
    return payload.getvalue()


def test_fresh_body_is_exactly_neutral_and_has_no_seeded_program(
    monkeypatch,
) -> None:
    guala = _runtime(monkeypatch)
    try:
        anatomy = guala._embodied_vocal_body.anatomy

        assert len(anatomy.actuators) == 9
        assert anatomy.phonatory_exhalation_samples == 16_000
        assert anatomy.laryngeal_cycle_samples == 160
        assert (
            anatomy.phonatory_exhalation_samples
            // anatomy.laryngeal_cycle_samples
            == 100
        )
        assert all(
            actuator.current_coordinate
            == actuator.neutral_coordinate
            and actuator.negative.tension_quanta == 0
            and actuator.positive.tension_quanta == 0
            for actuator in anatomy.actuators
        )
        assert guala._articulatory_self_vocal_owner.programs == ()
        assert guala._embodied_vocal_body.acquired_program_count == 0
        assert (
            guala._embodied_vocal_body.status()["retained_pcm_bytes"]
            == 0
        )
        assert "pcm" not in inspect.signature(
            guala._embodied_vocal_body.capture_inquiry_efferent
        ).parameters
    finally:
        guala.shutdown()


def test_authenticated_drive_is_deterministic_and_returns_pcm_once(
    monkeypatch,
) -> None:
    first = _runtime(monkeypatch)
    second = _runtime(monkeypatch)
    try:
        deliveries = []
        candidates = []
        for guala in (first, second):
            _seed_held_thing_and_inquiry(guala)
            need = guala._causal_inquiry_owner.active_need
            assert need is not None
            witness = next(
                value
                for value in guala._causal_inquiry_owner.witnesses
                if value.authority_receipt_sha256
                == need.witness_receipt_sha256
            )
            pre_candidate_retained = (
                guala._embodied_vocal_body.snapshot_encoded()
                + guala._articulatory_self_vocal_owner.snapshot_encoded()
                + guala._causal_inquiry_owner.snapshot_encoded()
            )
            custody = (
                guala._embodied_vocal_body.capture_inquiry_efferent(
                    need=need,
                    witness=witness,
                )
            )
            candidate, pcm = (
                guala._embodied_vocal_body
                .attempt_with_transient_delivery(
                    custody,
                    w1_authority=(
                        guala._body_owned_w1_self_acoustic
                    ),
                )
            )
            candidates.append(candidate)
            deliveries.append(pcm)
            assert len(pcm) == 2 * candidate.sample_count
            assert hashlib.sha256(pcm).hexdigest() == (
                candidate.pressure_sha256
            )
            candidate_payload = str(candidate.payload()).lower().encode()
            delivery_base64 = base64.b64encode(pcm)
            for retained in (
                candidate_payload,
                pre_candidate_retained,
            ):
                assert pcm not in retained
                assert delivery_base64 not in retained
                assert b"pcm_s16le" not in retained
            with pytest.raises(
                RuntimeError,
                match="cannot enter persistence",
            ):
                guala._embodied_vocal_body.snapshot_encoded()
            assert all(
                actuator.current_coordinate
                == actuator.neutral_coordinate
                and actuator.negative.tension_quanta == 0
                and actuator.positive.tension_quanta == 0
                for actuator in guala._embodied_vocal_body.anatomy.actuators
            )

        assert deliveries[0] == deliveries[1]
        assert candidates[0].pressure_sha256 == (
            candidates[1].pressure_sha256
        )
        assert candidates[0].program_sample_count == (
            candidates[1].program_sample_count
        )
    finally:
        for guala, candidate in zip(
            (first, second),
            candidates,
            strict=False,
        ):
            guala._embodied_vocal_body.rollback_candidate(
                candidate,
                w1_authority=guala._body_owned_w1_self_acoustic,
            )
        second.shutdown()
        first.shutdown()


def test_tampered_efferent_custody_fails_and_original_is_discardable(
    monkeypatch,
) -> None:
    guala = _runtime(monkeypatch)
    try:
        _seed_held_thing_and_inquiry(guala)
        need = guala._causal_inquiry_owner.active_need
        assert need is not None
        witness = next(
            value
            for value in guala._causal_inquiry_owner.witnesses
            if value.authority_receipt_sha256
            == need.witness_receipt_sha256
        )
        custody = (
            guala._embodied_vocal_body.capture_inquiry_efferent(
                need=need,
                witness=witness,
            )
        )
        with pytest.raises(ValueError, match="changed"):
            guala._embodied_vocal_body.verify_custody(replace(
                custody,
                sound_fields=custody.sound_fields[:-1],
            ))

        prepared = guala._embodied_vocal_body.prepare_transient(
            custody
        )
        guala._embodied_vocal_body.discard_prepared_transient(
            prepared
        )
        assert guala._embodied_vocal_body.status()["live_custody"] == 0
        assert (
            guala._embodied_vocal_body.status()["prepared_transient"]
            == 0
        )
    finally:
        guala.shutdown()


def test_program_pressure_and_complete_world_bound_are_exact() -> None:
    world = EmbodimentWorldAuthority(authority_key=WORLD_KEY)
    vocal = EmbodiedVocalBodyAuthority(
        authority_key=KEY,
        world_authority=world,
    )
    neutral = vocal.anatomy
    moved = replace(
        neutral.actuators[1],
        current_coordinate=(
            neutral.actuators[1].current_coordinate
            + neutral.actuators[1].native_resolution
        ),
    )
    moved_areas = (
        moved.current_coordinate,
        *(value.current_coordinate for value in neutral.actuators[2:]),
    )
    neutral_areas = tuple(
        value.neutral_coordinate for value in neutral.actuators[1:]
    )

    def body_program(sample_count: int) -> ArticulatoryProgram:
        return ArticulatoryProgram.create(
            sample_count=sample_count,
            larynx=LaryngealExcitationConfiguration(
                cycle_samples=neutral.laryngeal_cycle_samples,
                open_samples=neutral.actuators[0].neutral_coordinate,
                peak_volume_velocity_pcm=(
                    neutral.respiratory_peak_volume_velocity_pcm
                ),
            ),
            tract=VocalTractConfiguration(
                initial_section_area_mm2=neutral_areas,
                apex_section_area_mm2=neutral_areas,
                final_section_area_mm2=neutral_areas,
                radiation_load_area_mm2=(
                    neutral.radiation_load_area_mm2
                ),
                wall_retention_ppm=neutral.wall_retention_ppm,
            ),
            body_trajectory=(
                ArticulatoryBodyTrajectoryInterval(
                    sample_start=0,
                    sample_end=sample_count,
                    glottal_open_samples=(
                        neutral.actuators[0].neutral_coordinate
                    ),
                    section_area_mm2=moved_areas,
                ),
            ),
        )

    pcm, quiescent, program_count = vocal._physical_pressure(
        program=body_program(24_800),
    )

    assert program_count == 24_800
    assert quiescent
    assert 24_800 <= len(pcm) // 2 <= MAX_VOCAL_SAMPLE_COUNT
    assert vocal.anatomy == neutral
    assert vocal.status()["retained_pcm_bytes"] == 0
    upper_pcm, upper_quiescent, upper_program_count = (
        vocal._physical_pressure(
            program=body_program(MAX_VOCAL_SAMPLE_COUNT),
        )
    )
    assert upper_program_count == MAX_VOCAL_SAMPLE_COUNT
    assert len(upper_pcm) // 2 == MAX_VOCAL_SAMPLE_COUNT
    assert upper_quiescent
    with pytest.raises(ValueError, match="sample count"):
        body_program(MAX_VOCAL_SAMPLE_COUNT + 1)


def test_real_external_interval_is_retained_but_anatomy_owns_one_second_act(
    monkeypatch,
) -> None:
    monkeypatch.setenv("EVENT_DRIVEN_SUBSTRATE", "0")
    monkeypatch.setenv("WAVE_ATLAS_ENABLED", "0")
    monkeypatch.setenv("WAVE_SUMMARY_ENQUEUE_ENABLED", "0")
    monkeypatch.setenv("SELF_HEARING_ENABLED", "0")
    monkeypatch.setenv("GUALA_CAUSAL_ACTION_KEY", RUNTIME_KEY)
    pcm = _decode_pcm(DADDY)
    assert len(pcm) == 49_320
    assert len(pcm) // 2 == 24_660
    duration_ns = len(pcm) * 1_000_000_000 // (2 * 16_000)
    assert duration_ns == 1_541_250_000
    source_start_ns = 4_000_000_000_000
    source_end_ns = source_start_ns + duration_ns
    engine = Guala()
    candidate = None
    admission_undo = None
    replay_undo = None
    try:
        engine.window_manager.begin_context(
            "test:real-daddy-inquiry-efferent",
            "audiovisual_capture",
            context_detail={
                "source_time_start_ns": source_start_ns,
                "source_time_end_ns": source_end_ns,
                "sensor_unavailable": [
                    "touch",
                    "smell",
                    "taste",
                    "body",
                ],
            },
        )
        engine.process_live_visual_region_sequence(
            _physical_frames(source_start_ns),
            source_time_start_ns=source_start_ns,
            source_time_end_ns=source_end_ns,
        )
        engine.process_sound_frame(
            _wav(pcm),
            source="browser_microphone",
            source_anchor_ns=source_start_ns,
            source_time_end_ns=source_end_ns,
            auditory_event_boundary="ambient",
        )
        _window_id, settlement = engine.window_manager.end_context(
            "test:real-daddy-inquiry-efferent",
            "audiovisual_capture_complete",
            return_settlement=True,
        )
        witness = engine._causal_inquiry_owner.witnesses[0]
        need = engine._causal_inquiry_owner.active_need
        assert need is not None
        assert witness.source_time_start == (
            settlement.source_time_start
        )
        assert witness.source_time_end == settlement.source_time_end
        exact_extent = (
            witness.source_time_end - witness.source_time_start
        ) * 16_000
        assert exact_extent == 24_660
        sound_roots = tuple(
            root for root in witness.full_field_roots
            if root.sense == "sound"
        )
        assert len(sound_roots) == 32

        pre_candidate_retained = (
            engine._embodied_vocal_body.snapshot_encoded()
            + engine._articulatory_self_vocal_owner.snapshot_encoded()
            + engine._causal_inquiry_owner.snapshot_encoded()
        )
        custody = (
            engine._embodied_vocal_body.capture_inquiry_efferent(
                need=need,
                witness=witness,
            )
        )
        with pytest.raises(ValueError, match="changed"):
            engine._embodied_vocal_body.verify_custody(replace(
                custody,
                source_time_end=custody.source_time_end + 1,
            ))
        with pytest.raises(
            ValueError,
            match="exact bounded 16 kHz sample extent",
        ):
            (
                engine._embodied_vocal_body
                ._witness_source_sample_count(replace(
                    witness,
                    source_time_end=(
                        witness.source_time_end
                        + Fraction(1, 32_000)
                    ),
                ))
            )
        assert custody.source_sample_count == 24_660
        assert len(custody.sound_fields) == 32
        roots_by_topology = {
            root.topology_index: json.loads(root.full_evidence_json)
            for root in sound_roots
        }
        assert all(
            trajectory.source_intervals
            == tuple(
                (
                    item["source_index_start"],
                    item["source_index_end"],
                )
                for item in roots_by_topology[
                    trajectory.topology_index
                ]["field_tuples"]
            )
            for trajectory in custody.sound_fields
        )
        candidate, delivery = (
            engine._embodied_vocal_body
            .attempt_with_transient_delivery(
                custody,
                w1_authority=engine._body_owned_w1_self_acoustic,
            )
        )
        assert candidate.source_sample_count == 16_000
        assert candidate.program_sample_count == 16_000
        assert candidate.sample_count == 16_000
        assert hashlib.sha256(delivery).hexdigest() == (
            candidate.pressure_sha256
        )
        assert any(delivery)
        assert len({
            candidate.w1_mount_receipt_sha256,
            candidate.causal_settlement_receipt_sha256,
            candidate.binaural_l5_receipt_sha256,
            candidate.receptor_settlement_receipt_sha256,
            candidate.recurrent_q_receipt_sha256,
        }) == 5
        retained = (
            str(candidate.payload()).lower().encode()
            + pre_candidate_retained.lower()
        )
        assert delivery not in retained
        assert base64.b64encode(delivery) not in retained
        assert b"pcm_s16le" not in retained
        with pytest.raises(
            RuntimeError,
            match="cannot enter persistence",
        ):
            engine._embodied_vocal_body.snapshot_encoded()
        assert engine._embodied_vocal_body.status()[
            "retained_pcm_bytes"
        ] == 0

        motor_custody = (
            engine._embodied_vocal_body.open_motor_fragment_custody(
                candidate
            )
        )
        body_trajectory = motor_custody.program.body_trajectory
        assert len(body_trajectory) == 1
        assert body_trajectory[0].sample_start == 0
        assert body_trajectory[0].sample_end == 16_000
        assert body_trajectory[0].glottal_open_samples == (
            engine._embodied_vocal_body.anatomy
            .actuators[0].neutral_coordinate
        )
        assert body_trajectory[0].section_area_mm2 == tuple(
            actuator.neutral_coordinate
            for actuator
            in engine._embodied_vocal_body.anatomy.actuators[1:]
        )
        program_record = json.dumps(
            motor_custody.program.as_record(),
            sort_keys=True,
        )
        assert all(
            trajectory.sound_root_sha256 not in program_record
            for trajectory in custody.sound_fields
        )
        assert base64.b64encode(delivery).decode("ascii") not in (
            program_record
        )
        motor_before = (
            engine._articulatory_self_vocal_owner.snapshot_encoded()
        )
        prepared_admission = (
            engine._articulatory_self_vocal_owner
            .prepare_program_admission(motor_custody.program)
        )
        admission_undo = (
            engine._articulatory_self_vocal_owner
            .commit_prepared_program_admission(prepared_admission)
        )
        replay_world_before = (
            engine._embodiment_world.encoded_snapshot()
        )
        synthesis = (
            engine._articulatory_self_vocal_owner.synthesize(
                program_id=motor_custody.program.program_id,
                source_time_start=Fraction(
                    engine._embodiment_world
                    .observation_snapshot().revision,
                    1,
                ),
            )
        )
        assert synthesis.program.sample_count == 16_000
        assert hashlib.sha256(
            synthesis.radiated_pcm_s16le
        ).hexdigest() == candidate.pressure_sha256

        assembly = synthesis.actuator_full_field_assembly
        assembly.verify()
        expected_extents = tuple(
            (
                sample_start,
                min(
                    sample_start
                    + MAX_NATIVE_SAMPLES_PER_SUBSTREAM,
                    16_000,
                ),
            )
            for sample_start in range(
                0,
                16_000,
                MAX_NATIVE_SAMPLES_PER_SUBSTREAM,
            )
        )
        assert len(assembly.partitions) == 8
        assert tuple(
            (partition.sample_start, partition.sample_end)
            for partition in assembly.partitions
        ) == expected_extents
        assert expected_extents[-1] == (14_336, 16_000)

        substream_times: dict[str, list[Fraction]] = {}
        laryngeal_samples: list[int] = []
        for partition in assembly.partitions:
            span = partition.sample_end - partition.sample_start
            assert span <= MAX_NATIVE_SAMPLES_PER_SUBSTREAM
            body = next(
                boundary
                for boundary
                in partition.full_field.boundary.boundaries
                if boundary.sense is PhysicalSense.BODY
            )
            assert len(body.substreams) == 9
            assert all(
                all(
                    isinstance(
                        getattr(field_tuple, field_name),
                        Fraction,
                    )
                    for field_name in DSF_FIELD_ORDER
                )
                for substream in body.substreams
                for field_tuple
                in substream.kernel_basin.exact_dsf_field_tuples
            )
            for (
                stream_receipt,
                sample_count,
                _commitment,
            ) in partition.full_field.source_sample_commitments:
                assert sample_count == span
                native = partition.full_field.source_native_input(
                    stream_receipt
                )
                assert native.source_times == tuple(
                    assembly.source_time_start
                    + Fraction(index, 16_000)
                    for index in range(
                        partition.sample_start,
                        partition.sample_end,
                    )
                )
                substream_times.setdefault(
                    native.substream_id,
                    [],
                ).extend(native.source_times)
                if (
                    native.substream_id
                    == "glottal-volume-acceleration"
                ):
                    laryngeal_samples.extend(
                        round(value * 32_768)
                        for value in native.normalized_signal
                    )
        assert set(substream_times) == {
            "glottal-volume-acceleration",
            *{
                f"vocal-tract-section-{index:02d}-area"
                for index in range(8)
            },
        }
        expected_times = [
            assembly.source_time_start + Fraction(index, 16_000)
            for index in range(16_000)
        ]
        assert all(
            values == expected_times
            for values in substream_times.values()
        )
        assert laryngeal_samples == [
            sample[0]
            for sample in struct.iter_unpack(
                "<h",
                synthesis.excitation_pcm_s16le,
            )
        ]

        prepared_emission = (
            engine._articulatory_self_vocal_owner
            .prepare_generated_emission(
                synthesis=synthesis,
                world_authority=engine._embodiment_world,
                causal_intent_receipt_sha256=(
                    motor_custody.authority_receipt_sha256
                ),
            )
        )
        prepared_replay = (
            engine._w1_self_acoustic_propagation
            .prepare_articulatory(
                prepared_emission,
                articulatory_owner=(
                    engine._articulatory_self_vocal_owner
                ),
            )
        )
        emission, replay_mount, replay_undo = (
            engine._w1_self_acoustic_propagation
            .commit_prepared_articulatory(prepared_replay)
        )
        assert emission.pcm_s16le == synthesis.radiated_pcm_s16le
        assert replay_mount.receipt.motor_id == synthesis.program.program_id
        assert (
            replay_mount.receipt.source_time_end
            - replay_mount.receipt.source_time_start
        ) * 16_000 == 16_000
        engine._w1_self_acoustic_propagation \
            .rollback_committed_articulatory(replay_undo)
        replay_undo = None
        assert (
            engine._embodiment_world.encoded_snapshot()
            == replay_world_before
        )
        engine._articulatory_self_vocal_owner \
            .rollback_program_admission(admission_undo)
        admission_undo = None
        assert (
            engine._articulatory_self_vocal_owner.snapshot_encoded()
            == motor_before
        )
        assert (
            engine._articulatory_self_vocal_owner.status()[
                "retained_pcm_bytes"
            ]
            == 0
        )
    finally:
        if replay_undo is not None:
            engine._w1_self_acoustic_propagation \
                .rollback_committed_articulatory(replay_undo)
        if admission_undo is not None:
            engine._articulatory_self_vocal_owner \
                .rollback_program_admission(admission_undo)
        if candidate is not None:
            engine._embodied_vocal_body.rollback_candidate(
                candidate,
                w1_authority=engine._body_owned_w1_self_acoustic,
            )
        engine.shutdown()


def test_real_external_witness_learns_and_reuses_causal_self_act(
    monkeypatch,
    tmp_path,
) -> None:
    monkeypatch.setenv("EVENT_DRIVEN_SUBSTRATE", "0")
    monkeypatch.setenv("WAVE_ATLAS_ENABLED", "0")
    monkeypatch.setenv("WAVE_SUMMARY_ENQUEUE_ENABLED", "0")
    monkeypatch.setenv("SELF_HEARING_ENABLED", "0")
    monkeypatch.setenv("GUALA_CAUSAL_ACTION_KEY", RUNTIME_KEY)
    pcm = _decode_pcm(DADDY)
    source_start_ns = 5_000_000_000_000
    source_end_ns = source_start_ns + (
        len(pcm) * 1_000_000_000 // (2 * 16_000)
    )
    engine = Guala()
    cold = None
    admission_undo = None
    replay_undo = None
    try:
        engine._authoritative_hot_generation_publisher = (
            lambda **_values: None
        )
        world_before_pick = (
            engine._embodiment_world.observation_snapshot()
        )
        picked = engine._embodiment_world.execute_port_command(
            port_id=engine._embodiment_world.port_id,
            command_payload=encode_command(PickCommand(
                object_id="W1-object-1",
                duration_microseconds=100_000,
            )),
            causal_intent_receipt_sha256=hashlib.sha256(
                b"real-daddy-held-thing"
            ).hexdigest(),
            expected_revision=world_before_pick.revision,
        )
        assert picked.disposition == "applied"
        pick_mount = engine._w1_physical_evidence.mount_action_outcome(
            picked,
            commit=True,
        )
        pick_custody = engine._settled_prediction_custody(
            pick_mount,
            world_execution=picked,
        )
        engine._admit_settled_embodiment_thing(
            pick_custody,
            picked,
        )

        engine.window_manager.begin_context(
            "test:real-daddy-held-thing-e2e",
            "audiovisual_capture",
            context_detail={
                "source_time_start_ns": source_start_ns,
                "source_time_end_ns": source_end_ns,
                "sensor_unavailable": [
                    "touch",
                    "smell",
                    "taste",
                    "body",
                ],
            },
        )
        engine.process_live_visual_region_sequence(
            _physical_frames(source_start_ns),
            source_time_start_ns=source_start_ns,
            source_time_end_ns=source_end_ns,
        )
        engine.process_sound_frame(
            _wav(pcm),
            source="browser_microphone",
            source_anchor_ns=source_start_ns,
            source_time_end_ns=source_end_ns,
            auditory_event_boundary="ambient",
        )
        engine.window_manager.end_context(
            "test:real-daddy-held-thing-e2e",
            "audiovisual_capture_complete",
            return_settlement=True,
        )
        assert engine._causal_inquiry_owner.active_need is not None
        observation = engine._embodiment_world.observation_snapshot()
        assert next(
            body
            for body in observation.bodies
            if body.body_id == observation.self_body_id
        ).held_object_id == "W1-object-1"
        engine.save_full_state(
            tmp_path,
            publish_generation=False,
        )

        request_one = engine.create_body_owned_vocal_request_one(
            state_dir=tmp_path,
        )
        assert request_one.sample_count == 16_000
        assert hashlib.sha256(
            request_one.pcm_s16le
        ).hexdigest() == request_one.pressure_sha256

        pending_custody = (
            engine._pending_body_owned_vocal_consequence
            .open_pending_custody(request_one.client_capability)
        )
        assert pending_custody.program.body_trajectory
        assert pending_custody.program.body_trajectory[0].sample_start == 0
        assert (
            pending_custody.program.body_trajectory[-1].sample_end
            == 16_000
        )
        assert len({
            (
                interval.glottal_open_samples,
                interval.section_area_mm2,
            )
            for interval
            in pending_custody.program.body_trajectory
        }) == 1
        motor_before = (
            engine._articulatory_self_vocal_owner.snapshot_encoded()
        )
        prepared_admission = (
            engine._articulatory_self_vocal_owner
            .prepare_program_admission(pending_custody.program)
        )
        admission_undo = (
            engine._articulatory_self_vocal_owner
            .commit_prepared_program_admission(prepared_admission)
        )
        replay_world_before = (
            engine._embodiment_world.encoded_snapshot()
        )
        synthesis = (
            engine._articulatory_self_vocal_owner.synthesize(
                program_id=pending_custody.program.program_id,
                source_time_start=Fraction(
                    engine._embodiment_world
                    .observation_snapshot().revision,
                    1,
                ),
            )
        )
        assert len(
            synthesis.actuator_full_field_assembly.partitions
        ) == 8
        assert hashlib.sha256(
            synthesis.radiated_pcm_s16le
        ).hexdigest() == request_one.pressure_sha256
        prepared_emission = (
            engine._articulatory_self_vocal_owner
            .prepare_generated_emission(
                synthesis=synthesis,
                world_authority=engine._embodiment_world,
                causal_intent_receipt_sha256=(
                    pending_custody
                    .pending_authority_receipt_sha256
                ),
            )
        )
        prepared_replay = (
            engine._w1_self_acoustic_propagation
            .prepare_articulatory(
                prepared_emission,
                articulatory_owner=(
                    engine._articulatory_self_vocal_owner
                ),
            )
        )
        replay_emission, _replay_mount, replay_undo = (
            engine._w1_self_acoustic_propagation
            .commit_prepared_articulatory(prepared_replay)
        )
        assert replay_emission.pcm_s16le == request_one.pcm_s16le
        engine._w1_self_acoustic_propagation \
            .rollback_committed_articulatory(replay_undo)
        replay_undo = None
        assert (
            engine._embodiment_world.encoded_snapshot()
            == replay_world_before
        )
        engine._articulatory_self_vocal_owner \
            .rollback_program_admission(admission_undo)
        admission_undo = None
        assert (
            engine._articulatory_self_vocal_owner.snapshot_encoded()
            == motor_before
        )

        request_two = engine.create_body_owned_vocal_request_two(
            client_capability=request_one.client_capability,
            nonce=b"\x91" * 32,
            companion_pcm_s16le=_vocal_pcm(),
            state_dir=tmp_path,
        )
        assert request_two.inquiry_resolved is True
        assert request_two.autonomous_reuse_available is True
        engine.save_full_state(
            tmp_path,
            publish_generation=False,
        )
        cold = Guala()
        cold.load_full_state(tmp_path)
        cold_programs = (
            cold._articulatory_self_vocal_owner.programs
        )
        assert cold_programs == (pending_custody.program,)
        cold_synthesis = (
            cold._articulatory_self_vocal_owner.synthesize(
                program_id=cold_programs[0].program_id,
                source_time_start=Fraction(0),
            )
        )
        assert cold_synthesis.program.body_trajectory == (
            pending_custody.program.body_trajectory
        )
        assert hashlib.sha256(
            cold_synthesis.radiated_pcm_s16le
        ).hexdigest() == request_one.pressure_sha256
        cold.shutdown()
        cold = None
        before_move = engine._embodiment_world.observation_snapshot()
        learned = engine.durably_experience_embodied_action(
            tutor_id="joe",
            nonce="external-witness-causal-self-act-0001",
            port_id=engine._embodiment_world.port_id,
            command_payload=encode_command(MoveCommand(
                target_pose=PoseMM(
                    PositionMM(1_200, 1_400, 0),
                    0,
                ),
                duration_microseconds=100_000,
            )),
            state_dir=tmp_path,
        )
        vocal = learned["vocal_causal_act"]
        assert learned["world_revision_before"] == before_move.revision
        assert learned["world_revision_after"] == before_move.revision + 1
        assert (
            engine._embodiment_world.observation_snapshot().revision
            == before_move.revision + 2
        )
        assert vocal["state"] == "emitted"
        assert vocal["sample_count"] == 16_000
        assert vocal["pcm_sha256"] == request_one.pressure_sha256
        assert hashlib.sha256(
            vocal["pcm_s16le"]
        ).hexdigest() == request_one.pressure_sha256
        assert (
            engine._articulatory_self_vocal_owner.status()[
                "retained_pcm_bytes"
            ]
            == 0
        )
        assert (
            engine._experience_grown_vocal_causal_act.status()[
                "retained_pcm_bytes"
            ]
            == 0
        )
        for path in tmp_path.rglob("*"):
            if path.is_file():
                retained = path.read_bytes()
                assert request_one.pcm_s16le not in retained
                assert base64.b64encode(
                    request_one.pcm_s16le
                ) not in retained
    finally:
        if cold is not None:
            cold.shutdown()
        if replay_undo is not None:
            engine._w1_self_acoustic_propagation \
                .rollback_committed_articulatory(replay_undo)
        if admission_undo is not None:
            engine._articulatory_self_vocal_owner \
                .rollback_program_admission(admission_undo)
        engine.shutdown()
