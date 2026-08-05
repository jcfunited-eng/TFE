from __future__ import annotations

import threading
from contextlib import contextmanager
from dataclasses import replace
from fractions import Fraction

import pytest

from dsf_ai_service.glew_runtime.global_uf import DSF_FIELD_ORDER
from dsf_ai_service.glew_runtime.sensory_full_field_boundary import (
    PhysicalSense,
    SenseBoundaryState,
)
from dsf_ai_service.substrate.articulatory_self_vocal_motor import (
    ArticulatoryMotorResourceProfile,
    ArticulatoryProgram,
    ArticulatorySelfVocalMotorOwner,
    LaryngealExcitationConfiguration,
    VocalTractConfiguration,
)
from dsf_ai_service.substrate.auditory_kernel_mount import (
    AUDITORY_KERNEL_COMPONENT_COUNT,
)
from dsf_ai_service.substrate.auditory_recurrent_motif import (
    AuditoryMotifResourceProfile,
    AuditoryRecurrentMotifOwner,
)
from dsf_ai_service.substrate.embodiment_world import (
    MAX_VOCAL_SAMPLE_COUNT,
    VOCAL_SAMPLE_RATE_HZ,
    EmbodimentWorldAuthority,
)
from dsf_ai_service.substrate.exact_causal_experience import (
    ExactCausalExperienceOwner,
)
from dsf_ai_service.substrate.w1_binaural_auditory_l5 import (
    W1BinauralAuditoryL5Owner,
)
from dsf_ai_service.substrate.w1_self_acoustic_propagation import (
    PreparedW1SelfAcousticMount,
    W1ArticulatorySelfAcousticCommitUndo,
    W1SelfAcousticPropagationAuthority,
)


KEY = b"W1-prepared-self-acoustic-transaction-key"
INTENT = "7" * 64


def _program() -> ArticulatoryProgram:
    return ArticulatoryProgram.create(
        sample_count=3_200,
        larynx=LaryngealExcitationConfiguration(
            cycle_samples=80,
            open_samples=48,
            peak_volume_velocity_pcm=14_000,
        ),
        tract=VocalTractConfiguration(
            initial_section_area_mm2=(
                90,
                110,
                150,
                210,
                280,
                360,
                470,
                620,
            ),
            apex_section_area_mm2=(
                420,
                90,
                520,
                120,
                680,
                160,
                760,
                240,
            ),
            final_section_area_mm2=(
                90,
                110,
                150,
                210,
                280,
                360,
                470,
                620,
            ),
            radiation_load_area_mm2=900,
            wall_retention_ppm=990_000,
        ),
    )


def _system():
    articulatory = ArticulatorySelfVocalMotorOwner(
        authority_key=KEY,
        resource_profile=ArticulatoryMotorResourceProfile.create(
            profile_id="W1-prepared-articulatory",
            max_programs=2,
            max_state_bytes=64 * 1024,
        ),
    )
    admitted = articulatory.admit_program(_program())
    synthesis = articulatory.synthesize(
        program_id=admitted.program_id,
        source_time_start=Fraction(0),
    )
    world = EmbodimentWorldAuthority(
        authority_key=b"W1-prepared-self-acoustic-world-key"
    )
    causal = ExactCausalExperienceOwner(
        on_settlement=lambda _settlement: None,
        log_event=lambda *_args, **_kwargs: None,
    )
    l5 = W1BinauralAuditoryL5Owner()
    motif = AuditoryRecurrentMotifOwner(
        AuditoryMotifResourceProfile.create(
            profile_id="W1-prepared-self-acoustic-binaural",
            ear_count=2,
            max_motif_neurons=24_192,
            max_pending_experiences=8,
            max_work_cells_per_observation=8_000_000,
            max_exact_fraction_text_bytes=4_096,
            encoded_state_allocation_bytes=128 * 1024 * 1024,
        ),
        ear_ids=("left", "right"),
    )
    authority = W1SelfAcousticPropagationAuthority(
        authority_key=KEY,
        world_authority=world,
        causal_owner=causal,
        binaural_l5_owner=l5,
        binaural_motif_owner=motif,
    )
    return authority, articulatory, synthesis, world, causal, l5, motif


def _published_state(world, causal, l5, motif):
    causal_status = causal.status()
    l5_status = l5.status()
    return {
        "world": world.encoded_snapshot(),
        "world_receipts": world.recent_applied_receipts(),
        "causal": (
            causal_status["settled"],
            tuple(causal_status["tracked_senses"]),
            causal_status["transition_relations"],
        ),
        "l5": (
            l5_status["has_latest"],
            l5_status["settled"],
            l5_status["transition_relations"],
        ),
        "motif": motif.snapshot_encoded(),
    }


def _control_state(world, causal, l5, motif):
    return {
        "world_prepared": world.status()["prepared_action_execution"],
        "causal_prepared": causal.status()["prepared_reservation"],
        "causal_atomic": causal.status()["atomic_sequence"],
        "l5_prepared": l5.status()["prepared"],
        "l5_atomic": l5.status()["atomic_sequence"],
        "motif_prepared": motif.status()[
            "prepared_binaural_observation_count"
        ],
    }


def _prepare_motor(articulatory, synthesis, world):
    return articulatory.prepare_generated_emission(
        synthesis=synthesis,
        world_authority=world,
        causal_intent_receipt_sha256=INTENT,
    )


def _prepare_current_motor(articulatory, program_id, world):
    before = world.observation_snapshot()
    synthesis = articulatory.synthesize(
        program_id=program_id,
        source_time_start=Fraction(
            before.revision * MAX_VOCAL_SAMPLE_COUNT,
            VOCAL_SAMPLE_RATE_HZ,
        ),
    )
    return _prepare_motor(articulatory, synthesis, world)


def _all_field_tuples(mount):
    for ear in mount.binaural_l5.ears:
        for channel in ear.channels:
            for component in (
                channel.pressure,
                channel.carrier_phase_advance,
            ):
                yield from component.field_tuples
    for sense in mount.causal_settlement.interpretations:
        if sense.state == SenseBoundaryState.OBSERVED.value:
            for substream in sense.substreams:
                yield from substream.field_tuples


def test_prepare_is_live_pure_full_field_and_discard_is_exact():
    authority, articulatory, synthesis, world, causal, l5, motif = _system()
    initial = _published_state(world, causal, l5, motif)
    prepared_emission = _prepare_motor(articulatory, synthesis, world)
    after_motor_prepare = _published_state(world, causal, l5, motif)

    prepared = authority.prepare_articulatory(
        prepared_emission,
        articulatory_owner=articulatory,
    )

    assert isinstance(prepared, PreparedW1SelfAcousticMount)
    assert not hasattr(prepared, "mount")
    assert not hasattr(prepared, "receipt")
    assert _published_state(world, causal, l5, motif) == after_motor_prepare
    assert _control_state(world, causal, l5, motif) == {
        "world_prepared": 1,
        "causal_prepared": 0,
        "causal_atomic": 1,
        "l5_prepared": 0,
        "l5_atomic": 1,
        "motif_prepared": 1,
    }

    authority.discard_prepared_articulatory(prepared)

    assert _published_state(world, causal, l5, motif) == initial
    assert all(
        value == 0
        for value in _control_state(
            world, causal, l5, motif
        ).values()
    )


def test_commit_hides_world_sensory_mismatch_from_every_observer(
    monkeypatch,
):
    authority, articulatory, synthesis, world, causal, l5, motif = _system()
    before = world.observation_snapshot()
    prepared_emission = _prepare_motor(articulatory, synthesis, world)
    prospective = prepared_emission.prospective_emission_receipt_sha256
    prepared = authority.prepare_articulatory(
        prepared_emission,
        articulatory_owner=articulatory,
    )
    original_world_commit = world.commit_prepared_action
    observer_started = threading.Event()
    observer_done = threading.Event()
    observed_states = []
    observer_threads = []

    def observe_during_commit():
        observer_started.set()
        observed_states.append(_published_state(world, causal, l5, motif))
        observer_done.set()

    def world_commit(value):
        receipt = original_world_commit(value)
        observer = threading.Thread(target=observe_during_commit)
        observer_threads.append(observer)
        observer.start()
        assert observer_started.wait(1)
        assert not observer_done.wait(0.05)
        with pytest.raises(RuntimeError, match="visibility transaction"):
            world.observation_snapshot()
        with pytest.raises(RuntimeError, match="visibility transaction"):
            causal.status()
        with pytest.raises(RuntimeError, match="visibility transaction"):
            l5.status()
        with pytest.raises(RuntimeError, match="visibility transaction"):
            motif.status()
        return receipt

    monkeypatch.setattr(world, "commit_prepared_action", world_commit)

    emission, mount, _undo = authority.commit_prepared_articulatory(
        prepared
    )

    assert len(observer_threads) == 1
    observer_threads[0].join(1)
    assert observer_done.is_set()
    assert emission.emission_receipt.authority_receipt_sha256 == prospective
    mount.verify(KEY)
    assert mount.receipt.self_vocal_emission_receipt_sha256 == prospective
    assert len(mount.binaural_l5.ears) == 2
    assert sum(
        2
        for ear in mount.binaural_l5.ears
        for _channel in ear.channels
    ) == 2 * AUDITORY_KERNEL_COMPONENT_COUNT
    assert all(
        tuple(name for name, _value in field_tuple.fields)
        == DSF_FIELD_ORDER
        for field_tuple in _all_field_tuples(mount)
    )
    observed = {
        sense.sense
        for sense in mount.causal_settlement.interpretations
        if sense.state == SenseBoundaryState.OBSERVED.value
    }
    assert observed == {
        PhysicalSense.BODY.value,
        PhysicalSense.SIGHT.value,
        PhysicalSense.SOUND.value,
        PhysicalSense.TOUCH.value,
    }
    assert world.observation_snapshot() == emission.execution_receipt.after
    assert world.observation_snapshot().revision == before.revision + 1
    assert causal.status()["settled"] == 1
    assert l5.status()["settled"] == 1
    assert motif.status()["fade_total_count"] == 1
    assert all(
        value == 0
        for value in _control_state(
            world, causal, l5, motif
        ).values()
    )
    final = _published_state(world, causal, l5, motif)
    assert observed_states == [final]
    with pytest.raises(ValueError, match="changed custody"):
        authority.commit_prepared_articulatory(prepared)
    assert _published_state(world, causal, l5, motif) == final


def test_commit_undo_restores_exact_current_world_and_sensory_tail():
    authority, articulatory, synthesis, world, causal, l5, motif = _system()
    before = _published_state(world, causal, l5, motif)
    causal_before = causal.status()
    l5_before = l5.encoded_snapshot()
    motif_status_before = motif.status()
    prepared = authority.prepare_articulatory(
        _prepare_motor(articulatory, synthesis, world),
        articulatory_owner=articulatory,
    )

    emission, mount, undo = authority.commit_prepared_articulatory(
        prepared
    )

    assert isinstance(undo, W1ArticulatorySelfAcousticCommitUndo)
    assert emission.execution_receipt.after.revision == 1
    mount.verify(KEY)
    authority.rollback_committed_articulatory(undo)
    assert _published_state(world, causal, l5, motif) == before
    assert causal.status() == causal_before
    assert l5.encoded_snapshot() == l5_before
    assert motif.status() == motif_status_before
    assert all(
        value == 0
        for value in _control_state(
            world, causal, l5, motif
        ).values()
    )
    with pytest.raises(ValueError, match="changed custody"):
        authority.rollback_committed_articulatory(undo)


def test_commit_undo_rejects_cross_owner_and_later_tail_without_consumption():
    authority, articulatory, synthesis, world, causal, l5, motif = _system()
    initial = _published_state(world, causal, l5, motif)
    first_prepared = authority.prepare_articulatory(
        _prepare_motor(articulatory, synthesis, world),
        articulatory_owner=articulatory,
    )
    _first_emission, _first_mount, first_undo = (
        authority.commit_prepared_articulatory(first_prepared)
    )
    after_first = _published_state(world, causal, l5, motif)
    crossed = W1SelfAcousticPropagationAuthority(
        authority_key=KEY,
        world_authority=world,
        causal_owner=causal,
        binaural_l5_owner=l5,
        binaural_motif_owner=motif,
    )
    with pytest.raises(ValueError, match="changed custody"):
        crossed.rollback_committed_articulatory(first_undo)

    second_prepared = authority.prepare_articulatory(
        _prepare_current_motor(
            articulatory,
            synthesis.receipt.program_id,
            world,
        ),
        articulatory_owner=articulatory,
    )
    _second_emission, _second_mount, second_undo = (
        authority.commit_prepared_articulatory(second_prepared)
    )
    after_second = _published_state(world, causal, l5, motif)

    with pytest.raises(
        ValueError,
        match="committed embodiment action tail changed",
    ):
        authority.rollback_committed_articulatory(first_undo)
    assert _published_state(world, causal, l5, motif) == after_second

    authority.rollback_committed_articulatory(second_undo)
    assert _published_state(world, causal, l5, motif) == after_first
    authority.rollback_committed_articulatory(first_undo)
    assert _published_state(world, causal, l5, motif) == initial


def test_commit_rollback_hides_partial_world_sensory_state_from_observer(
    monkeypatch,
):
    authority, articulatory, synthesis, world, causal, l5, motif = _system()
    before = _published_state(world, causal, l5, motif)
    prepared = authority.prepare_articulatory(
        _prepare_motor(articulatory, synthesis, world),
        articulatory_owner=articulatory,
    )
    _emission, _mount, undo = authority.commit_prepared_articulatory(
        prepared
    )
    original_transaction = (
        motif.committed_binaural_rollback_transaction
    )
    observer_started = threading.Event()
    observer_done = threading.Event()
    observed_states = []
    observer_threads = []

    def observe_during_rollback():
        observer_started.set()
        observed_states.append(_published_state(world, causal, l5, motif))
        observer_done.set()

    @contextmanager
    def expose_rollback_boundary(value):
        with original_transaction(value) as rollback_now:
            def rollback_and_observe():
                rollback_now()
                with pytest.raises(
                    RuntimeError,
                    match="visibility transaction",
                ):
                    world.observation_snapshot()
                with pytest.raises(
                    RuntimeError,
                    match="visibility transaction",
                ):
                    causal.status()
                with pytest.raises(
                    RuntimeError,
                    match="visibility transaction",
                ):
                    l5.status()
                with pytest.raises(
                    RuntimeError,
                    match="visibility transaction",
                ):
                    motif.status()
                observer = threading.Thread(
                    target=observe_during_rollback
                )
                observer_threads.append(observer)
                observer.start()
                assert observer_started.wait(1)
                assert not observer_done.wait(0.05)

            yield rollback_and_observe

    monkeypatch.setattr(
        motif,
        "committed_binaural_rollback_transaction",
        expose_rollback_boundary,
    )

    authority.rollback_committed_articulatory(undo)

    assert len(observer_threads) == 1
    observer_threads[0].join(1)
    assert observer_done.is_set()
    assert observed_states == [before]


@pytest.mark.parametrize(
    "boundary",
    (
        "causal_settle",
        "l5_prepare",
        "receptor_settlement",
        "causal_stage",
        "l5_stage",
        "motif_prepare",
        "mount_finish",
    ),
)
def test_prepare_boundary_failure_restores_every_authority(
    monkeypatch,
    boundary,
):
    authority, articulatory, synthesis, world, causal, l5, motif = _system()
    before = _published_state(world, causal, l5, motif)
    prepared_emission = _prepare_motor(articulatory, synthesis, world)

    def fail(*_args, **_kwargs):
        raise RuntimeError(f"injected {boundary}")

    if boundary == "causal_settle":
        monkeypatch.setattr(causal, "settle", fail)
    elif boundary == "l5_prepare":
        monkeypatch.setattr(l5, "prepare", fail)
    elif boundary == "receptor_settlement":
        monkeypatch.setattr(
            "dsf_ai_service.substrate.w1_self_acoustic_propagation."
            "settle_w1_binaural_receptors",
            fail,
        )
    elif boundary == "causal_stage":
        monkeypatch.setattr(causal, "commit_prepared", fail)
    elif boundary == "l5_stage":
        monkeypatch.setattr(l5, "commit_prepared", fail)
    elif boundary == "motif_prepare":
        monkeypatch.setattr(motif, "prepare_binaural", fail)
    else:
        monkeypatch.setattr(authority, "_finish_mount", fail)

    with pytest.raises(RuntimeError, match=f"injected {boundary}"):
        authority.prepare_articulatory(
            prepared_emission,
            articulatory_owner=articulatory,
        )

    assert _published_state(world, causal, l5, motif) == before
    assert all(
        value == 0
        for value in _control_state(
            world, causal, l5, motif
        ).values()
    )


@pytest.mark.parametrize(
    "boundary",
    (
        "causal_preverify",
        "l5_preverify",
        "motif_preverify",
        "motor_preverify",
        "world_publish",
    ),
)
def test_commit_boundary_failure_rolls_back_exactly(
    monkeypatch,
    boundary,
):
    authority, articulatory, synthesis, world, causal, l5, motif = _system()
    before = _published_state(world, causal, l5, motif)
    prepared_emission = _prepare_motor(articulatory, synthesis, world)
    prepared = authority.prepare_articulatory(
        prepared_emission,
        articulatory_owner=articulatory,
    )

    def fail(*_args, **_kwargs):
        raise RuntimeError(f"injected {boundary}")

    if boundary == "causal_preverify":
        monkeypatch.setattr(
            causal,
            "preverify_atomic_visibility_install",
            fail,
        )
    elif boundary == "l5_preverify":
        monkeypatch.setattr(
            l5,
            "preverify_atomic_visibility_install",
            fail,
        )
    elif boundary == "motif_preverify":
        monkeypatch.setattr(
            motif,
            "preverify_binaural_visibility_install",
            fail,
        )
    elif boundary == "motor_preverify":
        monkeypatch.setattr(
            articulatory,
            "preverify_generated_emission_commit",
            fail,
        )
    else:
        monkeypatch.setattr(world, "commit_prepared_action", fail)

    with pytest.raises(RuntimeError, match=f"injected {boundary}"):
        authority.commit_prepared_articulatory(prepared)

    assert _published_state(world, causal, l5, motif) == before
    assert all(
        value == 0
        for value in _control_state(
            world, causal, l5, motif
        ).values()
    )


def test_capacity_tamper_and_stale_capabilities_fail_closed():
    authority, articulatory, synthesis, world, causal, l5, motif = _system()
    before = _published_state(world, causal, l5, motif)
    prepared_emission = _prepare_motor(articulatory, synthesis, world)
    prepared = authority.prepare_articulatory(
        prepared_emission,
        articulatory_owner=articulatory,
    )

    with pytest.raises(RuntimeError, match="already prepared"):
        authority.prepare_articulatory(
            prepared_emission,
            articulatory_owner=articulatory,
        )
    copied = replace(prepared)
    with pytest.raises(ValueError, match="changed custody"):
        authority.commit_prepared_articulatory(copied)
    changed = replace(
        prepared,
        prepared_emission=replace(
            prepared.prepared_emission,
            prospective_emission_receipt_sha256="0" * 64,
        ),
    )
    with pytest.raises(ValueError, match="changed custody"):
        authority.commit_prepared_articulatory(changed)

    authority.discard_prepared_articulatory(prepared)
    assert _published_state(world, causal, l5, motif) == before
    with pytest.raises(ValueError, match="changed custody"):
        authority.discard_prepared_articulatory(prepared)


def test_public_commitment_is_live_owner_bound_and_tamper_evident():
    authority, articulatory, synthesis, world, causal, l5, motif = _system()
    other, *_unused = _system()
    prepared_emission = _prepare_motor(articulatory, synthesis, world)
    prepared = authority.prepare_articulatory(
        prepared_emission,
        articulatory_owner=articulatory,
    )
    commitment = authority.prepared_articulatory_commitment(prepared)

    authority.verify_prepared_articulatory_commitment(
        prepared,
        commitment,
    )
    with pytest.raises(ValueError, match="changed"):
        authority.verify_prepared_articulatory_commitment(
            prepared,
            replace(commitment, pcm_sha256="0" * 64),
        )
    with pytest.raises(ValueError, match="changed custody"):
        other.verify_prepared_articulatory_commitment(
            prepared,
            commitment,
        )

    authority.discard_prepared_articulatory(prepared)
    with pytest.raises(ValueError, match="changed custody"):
        authority.verify_prepared_articulatory_commitment(
            prepared,
            commitment,
        )


def test_preverified_capabilities_reject_cross_owner_and_cross_world():
    authority, articulatory, synthesis, world, causal, l5, motif = _system()
    (
        _other_authority,
        other_articulatory,
        _other_synthesis,
        other_world,
        other_causal,
        other_l5,
        other_motif,
    ) = _system()
    prepared_emission = _prepare_motor(articulatory, synthesis, world)
    prepared = authority.prepare_articulatory(
        prepared_emission,
        articulatory_owner=articulatory,
    )
    sensory = prepared._sensory
    causal_install = causal.preverify_atomic_visibility_install(
        sensory.causal_sequence_token
    )
    l5_install = l5.preverify_atomic_visibility_install(
        sensory.l5_sequence_token
    )
    motif_install = motif.preverify_binaural_visibility_install(
        sensory.motif_preparation
    )
    motor_commit = articulatory.preverify_generated_emission_commit(
        prepared_emission,
        world_authority=world,
    )

    with pytest.raises(ValueError, match="changed custody"):
        with other_causal.atomic_visibility_transaction(causal_install):
            pass
    with pytest.raises(ValueError, match="changed custody"):
        with other_l5.atomic_visibility_transaction(l5_install):
            pass
    with pytest.raises(ValueError, match="changed custody"):
        with other_motif.binaural_visibility_transaction(motif_install):
            pass
    with pytest.raises(ValueError, match="changed custody"):
        with other_articulatory.preverified_generated_emission_transaction(
            motor_commit,
            world_authority=world,
        ):
            pass
    with pytest.raises(ValueError, match="changed custody"):
        with articulatory.preverified_generated_emission_transaction(
            motor_commit,
            world_authority=other_world,
        ):
            pass

    authority.discard_prepared_articulatory(prepared)


def test_preverified_install_and_motor_commit_capabilities_are_one_use(
    monkeypatch,
):
    authority, articulatory, synthesis, world, causal, l5, motif = _system()
    prepared_emission = _prepare_motor(articulatory, synthesis, world)
    prepared = authority.prepare_articulatory(
        prepared_emission,
        articulatory_owner=articulatory,
    )
    captured = []
    original_causal = causal.atomic_visibility_transaction
    original_l5 = l5.atomic_visibility_transaction
    original_motif = motif.binaural_visibility_transaction
    original_motor = (
        articulatory.preverified_generated_emission_transaction
    )

    @contextmanager
    def capture_causal(install):
        with original_causal(install) as install_now:
            captured.append(install_now)
            yield install_now

    @contextmanager
    def capture_l5(install):
        with original_l5(install) as install_now:
            captured.append(install_now)
            yield install_now

    @contextmanager
    def capture_motif(install):
        with original_motif(install) as install_now:
            captured.append(install_now)
            yield install_now

    @contextmanager
    def capture_motor(preverified, *, world_authority):
        with original_motor(
            preverified,
            world_authority=world_authority,
        ) as commit_now:
            captured.append(commit_now)
            yield commit_now

    monkeypatch.setattr(
        causal,
        "atomic_visibility_transaction",
        capture_causal,
    )
    monkeypatch.setattr(
        l5,
        "atomic_visibility_transaction",
        capture_l5,
    )
    monkeypatch.setattr(
        motif,
        "binaural_visibility_transaction",
        capture_motif,
    )
    monkeypatch.setattr(
        articulatory,
        "preverified_generated_emission_transaction",
        capture_motor,
    )

    authority.commit_prepared_articulatory(prepared)

    assert len(captured) == 4
    for capability in captured:
        with pytest.raises(AssertionError):
            capability()
