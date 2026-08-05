from __future__ import annotations

import math
import json

import numpy as np
import pytest

from dsf_ai_service.substrate.auditory_recurrent_motif import (
    AuditoryMotifResourceProfile,
    AuditoryRecurrentMotifOwner,
)
from dsf_ai_service.substrate.embodiment_world import (
    PORT_ID,
    MoveCommand,
    PickCommand,
    PoseMM,
    PositionMM,
    encode_command,
)
from dsf_ai_service.substrate.exact_causal_experience import (
    ExactCausalExperienceOwner,
)
from dsf_ai_service.substrate.self_vocal_pcm_motor import (
    SelfVocalMotorResourceProfile,
    SelfVocalPCMMotorOwner,
)
from dsf_ai_service.substrate.settled_experience_custody import (
    SettledExperienceCustodyAuthority,
    SettledExperienceCustodyProfile,
)
from dsf_ai_service.substrate.senses.auditory_full_field_provider import (
    REQUIRED_SAMPLE_RATE_HZ,
)
from dsf_ai_service.substrate.w1_action_vocal_lesson import (
    W1ActionVocalLessonAuthority,
    W1ActionVocalLessonResourceProfile,
)
from dsf_ai_service.substrate.w1_action_vocal_demonstration import (
    W1_ACTION_VOCAL_DEMONSTRATION_ACTION_CONSUMER_ID,
    W1_ACTION_VOCAL_DEMONSTRATION_SELF_CONSUMER_ID,
    W1ActionVocalDemonstrationOwner,
    W1ActionVocalDemonstrationResourceProfile,
)
from dsf_ai_service.substrate.w1_binaural_auditory_l5 import (
    W1BinauralAuditoryL5Owner,
)
from dsf_ai_service.substrate.w1_binaural_grounding_evidence import (
    W1BinauralGroundingEvidenceAuthority,
    W1BinauralGroundingResourceProfile,
)
from dsf_ai_service.substrate.w1_cross_regime_vocal_calibration import (
    W1CrossRegimeCalibrationResourceProfile,
    W1CrossRegimeVocalCalibrationOwner,
)
from dsf_ai_service.substrate.w1_external_self_imitation import (
    W1_IMITATION_EXTERNAL_CONSUMER_ID,
    W1_IMITATION_SELF_CONSUMER_ID,
    W1ExternalSelfImitationAuthority,
    W1ImitationResourceProfile,
)
from dsf_ai_service.substrate.w1_experience_curriculum import (
    W1ExperienceCurriculumOwner,
    W1ExperienceCurriculumResourceProfile,
)
from dsf_ai_service.substrate.w1_self_acoustic_propagation import (
    W1SelfAcousticPropagationAuthority,
)
from tests.test_w1_audiovisual_physical_evidence import (
    EVIDENCE_KEY,
    WORLD_KEY,
    _authority,
    _emission,
    _vocal_execution,
    _world,
)
from tests.test_w1_self_acoustic_propagation import _mono_experience


KEY = b"W1-cross-regime-calibration-test-key"
CUSTODY_KEY = b"W1-cross-regime-custody-authority-key"


def _custody(source_mount, execution, consumer_id):
    authority = SettledExperienceCustodyAuthority(
        authority_key=CUSTODY_KEY,
        w1_physical_authority_key=EVIDENCE_KEY,
        world_authority_key=WORLD_KEY,
        w1_self_acoustic_authority_key=KEY,
        profile=SettledExperienceCustodyProfile.create(
            profile_id=(
                "W1-cross-regime-"
                + execution.authority_receipt_sha256[:16]
            ),
            max_children=2,
            max_snapshot_bytes=64 * 1024 * 1024,
        ),
    )
    authority.admit(source_mount, execution)
    return authority, authority.issue_child(consumer_id)


def _tone(frequency_hz: int, amplitude: int) -> bytes:
    sample_count = 3_200
    source_times = np.arange(sample_count) / REQUIRED_SAMPLE_RATE_HZ
    values = np.rint(
        amplitude
        * (0.55 + 0.4 * np.sin(2 * math.pi * 5 * source_times))
        * np.sin(2 * math.pi * frequency_hz * source_times)
    ).astype("<i2")
    return values.tobytes()


def _motor_owner():
    mono_q = AuditoryRecurrentMotifOwner(
        AuditoryMotifResourceProfile.create(
            profile_id="W1-cross-regime-mono-q",
            ear_count=1,
            max_motif_neurons=12_096,
            max_pending_experiences=8,
            max_work_cells_per_observation=4_000_000,
            max_exact_fraction_text_bytes=4_096,
            encoded_state_allocation_bytes=64 * 1024 * 1024,
        )
    )
    owner = SelfVocalPCMMotorOwner(
        authority_key=KEY,
        resource_profile=SelfVocalMotorResourceProfile.create(
            profile_id="W1-cross-regime-motors",
            max_exemplars=2,
            max_total_pcm_bytes=32 * 1024,
            max_state_bytes=128 * 1024,
        ),
    )
    exemplars = {}
    occurrence = 1
    for frequency in (440, 660):
        first_event, first = _mono_experience(
            _tone(frequency, 10_000), occurrence
        )
        occurrence += 1
        motor_event, motor_experience = _mono_experience(
            _tone(frequency, 11_000), occurrence
        )
        occurrence += 1
        mono_q.observe(first)
        assert mono_q.observe(
            motor_experience
        ).newly_grown_motif_neuron_ids
        exemplars[frequency] = owner.admit_exemplar(
            pcm_s16le=_tone(frequency, 11_000),
            receptor_event=motor_event,
            receptor_experience=motor_experience,
            motif_owner=mono_q,
        )
    return owner, exemplars


def _binaural_q():
    return AuditoryRecurrentMotifOwner(
        AuditoryMotifResourceProfile.create(
            profile_id="W1-cross-regime-binaural-q",
            ear_count=2,
            max_motif_neurons=24_192,
            max_pending_experiences=8,
            max_work_cells_per_observation=8_000_000,
            max_exact_fraction_text_bytes=4_096,
            encoded_state_allocation_bytes=128 * 1024 * 1024,
        ),
        ear_ids=("left", "right"),
    )


def _external_observation(q_owner, frequency: int, amplitude: int):
    world = _world()
    physical = _authority(world)
    epoch = physical.open_epoch()
    pcm = _tone(frequency, amplitude)
    execution = _vocal_execution(
        world,
        epoch,
        sequence=0,
        source_sample_start=0,
        pcm=pcm,
    )
    mount = physical.mount(
        epoch_token=epoch,
        sequence=0,
        execution_receipt=execution,
        acoustic_emission=_emission(
            physical,
            epoch,
            execution,
            sequence=0,
            source_sample_start=0,
            pcm=pcm,
        ),
    )
    return q_owner.observe_binaural(
        mount.binaural_receptor_settlement
    )


def _action(world, kind: str, intent_digit: str):
    before = world.observation_snapshot()
    command = (
        PickCommand("teaching-object")
        if kind == "pick"
        else MoveCommand(PoseMM(PositionMM(1_000, 800, 0), 0))
    )
    execution = world.execute_port_command(
        port_id=PORT_ID,
        command_payload=encode_command(command),
        causal_intent_receipt_sha256=intent_digit * 64,
        expected_revision=before.revision,
    )
    assert execution.disposition == "applied"
    return execution


def _imitation_episode(
    *,
    q_owner,
    motor_owner,
    exemplar,
    kind: str,
    frequency: int,
    amplitude: int,
    intent_digit: str,
):
    grounding = W1BinauralGroundingEvidenceAuthority(
        authority_key=KEY,
        resource_profile=W1BinauralGroundingResourceProfile.create(
            profile_id="W1-cross-regime-grounding",
            max_activations=4_096,
            max_roots=256,
            max_evidence_bytes=32 * 1024 * 1024,
        ),
    )
    world = _world()
    physical = _authority(world)
    action_execution = _action(world, kind, intent_digit)
    action_mount = physical.mount_action_outcome(action_execution)
    epoch = physical.open_epoch()
    pcm = _tone(frequency, amplitude)
    external_execution = _vocal_execution(
        world,
        epoch,
        sequence=0,
        source_sample_start=0,
        pcm=pcm,
    )
    external_mount = physical.mount(
        epoch_token=epoch,
        sequence=0,
        execution_receipt=external_execution,
        acoustic_emission=_emission(
            physical,
            epoch,
            external_execution,
            sequence=0,
            source_sample_start=0,
            pcm=pcm,
        ),
    )
    external_firing = q_owner.fire_binaural(
        external_mount.binaural_receptor_settlement
    )
    assert external_firing.activations
    external_grounding = grounding.admit(
        settlement=external_mount.causal_settlement,
        receptor_settlement=(
            external_mount.binaural_receptor_settlement
        ),
        firing=external_firing,
        motif_owner=q_owner,
    )
    lesson_owner = W1ActionVocalLessonAuthority(
        authority_key=KEY,
        resource_profile=W1ActionVocalLessonResourceProfile.create(
            profile_id="W1-cross-regime-lessons",
            max_lessons=8,
            max_action_roots_per_lesson=256,
            max_vocal_activations_per_lesson=4_096,
            max_lesson_bytes=32 * 1024 * 1024,
        ),
        world_authority=world,
        physical_authority=physical,
        grounding_authority=grounding,
    )
    lesson = lesson_owner.compose(
        action_execution=action_execution,
        action_mount=action_mount,
        vocal_execution=external_execution,
        vocal_mount=external_mount,
        vocal_grounding=external_grounding,
    )
    self_acoustic = W1SelfAcousticPropagationAuthority(
        authority_key=KEY,
        world_authority=world,
        motor_owner=motor_owner,
        causal_owner=ExactCausalExperienceOwner(
            on_settlement=lambda _settlement: None,
            log_event=lambda *_args, **_kwargs: None,
        ),
        binaural_l5_owner=W1BinauralAuditoryL5Owner(),
        binaural_motif_owner=q_owner,
    )
    self_emission = motor_owner.execute(
        motor_id=exemplar.motor_id,
        world_authority=world,
        causal_intent_receipt_sha256=intent_digit * 64,
    )
    self_mount = self_acoustic.propagate(self_emission)
    imitation = W1ExternalSelfImitationAuthority(
        authority_key=KEY,
        resource_profile=W1ImitationResourceProfile.create(
            profile_id="W1-cross-regime-imitations",
            max_imitation_episodes=8,
            max_activations_per_regime=4_096,
            max_episode_bytes=32 * 1024 * 1024,
        ),
        world_authority=world,
        lesson_authority=lesson_owner,
        motor_owner=motor_owner,
    )
    external_custody, external_capability = _custody(
        external_mount,
        external_execution,
        W1_IMITATION_EXTERNAL_CONSUMER_ID,
    )
    self_custody, self_capability = _custody(
        self_mount,
        self_emission.execution_receipt,
        W1_IMITATION_SELF_CONSUMER_ID,
    )
    return imitation.admit(
        lesson=lesson,
        external_custody_authority=external_custody,
        external_custody_capability=external_capability,
        self_custody_authority=self_custody,
        self_custody_capability=self_capability,
    ), imitation


def _calibrated_system():
    motor_owner, exemplars = _motor_owner()
    q_owner = _binaural_q()
    for frequency in (440, 660):
        _external_observation(q_owner, frequency, 10_000)
        observed = _external_observation(q_owner, frequency, 11_000)
        assert observed.observation.newly_grown_motif_neuron_ids
    episodes = []
    verifier = None
    for kind, frequency, digits in (
        ("pick", 440, ("1", "2")),
        ("move", 660, ("3", "4")),
    ):
        for amplitude, digit in zip((10_000, 11_000), digits):
            episode, verifier = _imitation_episode(
                q_owner=q_owner,
                motor_owner=motor_owner,
                exemplar=exemplars[frequency],
                kind=kind,
                frequency=frequency,
                amplitude=amplitude,
                intent_digit=digit,
            )
            episodes.append(episode)
    assert verifier is not None
    owner = W1CrossRegimeVocalCalibrationOwner(
        authority_key=KEY,
        resource_profile=(
            W1CrossRegimeCalibrationResourceProfile.create(
                profile_id="W1-cross-regime-calibration",
                max_calibrations=4,
                max_imitation_episodes_per_calibration=8,
                max_forms_per_calibration=4,
                max_roots_per_form=256,
                max_diagnostic_cells_per_form=24_192,
                max_calibration_bytes=32 * 1024 * 1024,
            )
        ),
        imitation_authority=verifier,
        motor_owner=motor_owner,
    )

    calibration = owner.calibrate(tuple(episodes))
    return (
        motor_owner,
        exemplars,
        q_owner,
        episodes,
        owner,
        calibration,
    )


def test_calibration_requires_two_cross_regime_hearings_per_form():
    (
        _motor_owner_value,
        _exemplars,
        _q_owner_value,
        episodes,
        owner,
        calibration,
    ) = _calibrated_system()

    owner.verify(calibration)
    assert len(calibration.forms) == 2
    assert all(
        len(value.positive_imitation_receipt_sha256s) == 2
        for value in calibration.forms
    )
    assert len({
        value.motor_id for value in calibration.forms
    }) == 2
    assert {
        cell.ear_id
        for form in calibration.forms
        for cell in form.diagnostic_cells
    } == {"left", "right"}
    for form in calibration.forms:
        matching_episode = next(
            episode for episode in episodes
            if episode.motor_id == form.motor_id
        )
        assert owner.resolve_self_cells(
            calibration=calibration,
            active_cells=frozenset(
                matching_episode.cross_regime_cells
            ),
        ) == form
    with pytest.raises(
        ValueError,
        match="two external and two self hearings per form",
    ):
        owner.calibrate(tuple(episodes[:3]))


def _challenge(
    *,
    calibration_owner,
    calibration,
    q_owner,
    motor_owner,
    exemplar,
    kind: str,
    intent_digit: str,
):
    world = _world()
    physical = _authority(world)
    action_execution = _action(world, kind, intent_digit)
    action_mount = physical.mount_action_outcome(action_execution)
    self_acoustic = W1SelfAcousticPropagationAuthority(
        authority_key=KEY,
        world_authority=world,
        motor_owner=motor_owner,
        causal_owner=ExactCausalExperienceOwner(
            on_settlement=lambda _settlement: None,
            log_event=lambda *_args, **_kwargs: None,
        ),
        binaural_l5_owner=W1BinauralAuditoryL5Owner(),
        binaural_motif_owner=q_owner,
    )
    emission = motor_owner.execute(
        motor_id=exemplar.motor_id,
        world_authority=world,
        causal_intent_receipt_sha256=intent_digit * 64,
    )
    self_mount = self_acoustic.propagate(emission)
    owner = W1ActionVocalDemonstrationOwner(
        authority_key=KEY,
        resource_profile=(
            W1ActionVocalDemonstrationResourceProfile.create(
                profile_id="W1-action-vocal-demonstration",
                max_demonstrations=8,
                max_action_roots=256,
                max_self_activations=4_096,
                max_demonstration_bytes=32 * 1024 * 1024,
            )
        ),
        world_authority=world,
        motor_owner=motor_owner,
        calibration_owner=calibration_owner,
    )
    action_custody, action_capability = _custody(
        action_mount,
        action_execution,
        W1_ACTION_VOCAL_DEMONSTRATION_ACTION_CONSUMER_ID,
    )
    self_custody, self_capability = _custody(
        self_mount,
        emission.execution_receipt,
        W1_ACTION_VOCAL_DEMONSTRATION_SELF_CONSUMER_ID,
    )
    return owner, owner.admit(
        calibration=calibration,
        action_custody_authority=action_custody,
        action_custody_capability=action_capability,
        self_custody_authority=self_custody,
        self_custody_capability=self_capability,
    )


def test_fresh_action_challenge_requires_exact_calibrated_self_response():
    (
        motor_owner,
        exemplars,
        q_owner,
        _episodes,
        calibration_owner,
        calibration,
    ) = _calibrated_system()

    owner, demonstration = _challenge(
        calibration_owner=calibration_owner,
        calibration=calibration,
        q_owner=q_owner,
        motor_owner=motor_owner,
        exemplar=exemplars[440],
        kind="pick",
        intent_digit="5",
    )

    owner.verify(demonstration)
    matching_form = next(
        form for form in calibration.forms
        if form.motor_id == exemplars[440].motor_id
    )
    assert (
        demonstration.calibrated_action_field_identity
        == matching_form.action_field_identity
    )
    assert demonstration.motor_id == exemplars[440].motor_id
    assert {
        value.ear_id for value in demonstration.self_activations
    } == {"left", "right"}
    assert not hasattr(demonstration, "label")
    assert not hasattr(demonstration, "text")

    with pytest.raises(
        ValueError,
        match="wrong calibrated response",
    ):
        _challenge(
            calibration_owner=calibration_owner,
            calibration=calibration,
            q_owner=q_owner,
            motor_owner=motor_owner,
            exemplar=exemplars[660],
            kind="pick",
            intent_digit="6",
        )


def test_curriculum_persists_only_lived_action_vocal_plumbing():
    (
        motor_owner,
        exemplars,
        q_owner,
        _episodes,
        calibration_owner,
        calibration,
    ) = _calibrated_system()
    first_owner, first = _challenge(
        calibration_owner=calibration_owner,
        calibration=calibration,
        q_owner=q_owner,
        motor_owner=motor_owner,
        exemplar=exemplars[440],
        kind="pick",
        intent_digit="7",
    )
    _second_owner, second = _challenge(
        calibration_owner=calibration_owner,
        calibration=calibration,
        q_owner=q_owner,
        motor_owner=motor_owner,
        exemplar=exemplars[660],
        kind="move",
        intent_digit="8",
    )
    profile = W1ExperienceCurriculumResourceProfile.create(
        profile_id="W1-production-experience-curriculum",
        max_calibrations=4,
        max_demonstrations=16,
        max_state_bytes=64 * 1024 * 1024,
    )
    empty = W1ExperienceCurriculumOwner(
        authority_key=KEY,
        resource_profile=profile,
        calibration_owner=calibration_owner,
        demonstration_owner=first_owner,
    )
    assert empty.acceptance().state == "not_ready"
    assert empty.acceptance().developmental_equivalence == (
        "not_claimed_no_validated_human_age_mapping"
    )

    empty.admit_calibration(calibration)
    assert empty.acceptance().state == "not_ready"
    empty.admit_demonstration(first)
    assert empty.acceptance().state == "not_ready"
    empty.admit_demonstration(second)
    accepted = empty.acceptance()
    empty.verify_acceptance(accepted)
    assert accepted.state == (
        "authenticated_w1_action_vocal_plumbing_ready"
    )
    assert accepted.calibrated_form_count == 2
    assert accepted.external_hearing_count == 4
    assert accepted.self_hearing_count == 4
    assert accepted.demonstrated_form_count == 2
    encoded = empty.snapshot_encoded()

    cold = W1ExperienceCurriculumOwner.restore_encoded(
        authority_key=KEY,
        encoded=encoded,
        calibration_owner=calibration_owner,
        demonstration_owner=first_owner,
    )

    assert cold.snapshot_encoded() == encoded
    assert cold.acceptance() == accepted
    assert len(cold.calibrations) == 1
    assert len(cold.demonstrations) == 2
    corrupted = bytearray(encoded)
    corrupted[-2] = (
        ord("0") if corrupted[-2] != ord("0") else ord("1")
    )
    with pytest.raises(ValueError):
        W1ExperienceCurriculumOwner.restore_encoded(
            authority_key=KEY,
            encoded=bytes(corrupted),
            calibration_owner=calibration_owner,
            demonstration_owner=first_owner,
        )
    with pytest.raises(ValueError, match="state HMAC changed"):
        W1ExperienceCurriculumOwner.restore_encoded(
            authority_key=(
                b"W1-wrong-curriculum-restore-key-material"
            ),
            encoded=encoded,
            calibration_owner=calibration_owner,
            demonstration_owner=first_owner,
        )
    reordered = json.loads(encoded)
    reordered["body"]["demonstrations"].reverse()
    reordered_encoded = json.dumps(
        reordered,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    with pytest.raises(ValueError, match="state HMAC changed"):
        W1ExperienceCurriculumOwner.restore_encoded(
            authority_key=KEY,
            encoded=reordered_encoded,
            calibration_owner=calibration_owner,
            demonstration_owner=first_owner,
        )

    one_demonstration = W1ExperienceCurriculumOwner(
        authority_key=KEY,
        resource_profile=(
            W1ExperienceCurriculumResourceProfile.create(
                profile_id="W1-one-demonstration-capacity",
                max_calibrations=1,
                max_demonstrations=1,
                max_state_bytes=64 * 1024 * 1024,
            )
        ),
        calibration_owner=calibration_owner,
        demonstration_owner=first_owner,
    )
    one_demonstration.admit_calibration(calibration)
    one_demonstration.admit_demonstration(first)
    with pytest.raises(
        RuntimeError,
        match="demonstration capacity exhausted",
    ):
        one_demonstration.admit_demonstration(second)

    bounded = W1ExperienceCurriculumOwner(
        authority_key=KEY,
        resource_profile=(
            W1ExperienceCurriculumResourceProfile.create(
                profile_id="W1-exact-state-byte-capacity",
                max_calibrations=1,
                max_demonstrations=1,
                max_state_bytes=1_024,
            )
        ),
        calibration_owner=calibration_owner,
        demonstration_owner=first_owner,
    )
    with pytest.raises(
        RuntimeError,
        match="state capacity exhausted",
    ):
        bounded.admit_calibration(calibration)
