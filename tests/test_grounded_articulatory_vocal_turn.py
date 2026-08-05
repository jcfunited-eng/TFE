from __future__ import annotations

from fractions import Fraction

import pytest

from dsf_ai_service.glew_runtime.global_uf import DSF_FIELD_ORDER
from dsf_ai_service.substrate.articulatory_self_vocal_motor import (
    ArticulatoryMotorResourceProfile,
    ArticulatorySelfVocalMotorOwner,
)
from dsf_ai_service.substrate.auditory_recurrent_motif import (
    AuditoryMotifResourceProfile,
    AuditoryRecurrentMotifOwner,
)
from dsf_ai_service.substrate.causal_thing_lived_context import (
    CausalThingLivedContextOwner,
    CausalThingLivedContextResourceProfile,
)
from dsf_ai_service.substrate.causal_thing_mosaic import (
    CausalThingMosaicOwner,
    CausalThingMosaicProfile,
)
from dsf_ai_service.substrate.causal_thing_sensory_expansion import (
    THING_SENSORY_EXPANSION_CONSUMER_ID,
    THING_SENSORY_GROUNDING_CONSUMER_ID,
    CausalThingSensoryExpansionOwner,
    RetainedAudiovisualCustodyAuthority,
)
from dsf_ai_service.substrate.custodied_thing_encounter import (
    THING_MOSAIC_CONSUMER_ID,
    CustodiedW1ContactThingEncounterAuthority,
)
from dsf_ai_service.substrate.embodiment_world import (
    MAX_VOCAL_SAMPLE_COUNT,
    PORT_ID,
    VOCAL_SAMPLE_RATE_HZ,
    PickCommand,
    encode_command,
)
from dsf_ai_service.substrate.exact_causal_experience import (
    ExactCausalExperienceOwner,
)
from dsf_ai_service.substrate.grounded_articulatory_vocal_turn import (
    GroundedArticulatoryResolutionState,
    GroundedArticulatoryTeachingOccurrence,
    GroundedArticulatoryVocalTurnOwner,
    GroundedArticulatoryVocalTurnProfile,
    PreparedGroundedArticulatoryVocalTurn,
)
from dsf_ai_service.substrate.lived_vocal_teaching_episode import (
    LIVED_VOCAL_TEACHING_CONSUMER_ID,
    LivedVocalTeachingEpisodeAuthority,
    LivedVocalTeachingResourceProfile,
)
from dsf_ai_service.substrate.settled_experience_custody import (
    SettledExperienceCustodyAuthority,
    SettledExperienceCustodyProfile,
)
from dsf_ai_service.substrate.w1_binaural_auditory_l5 import (
    W1BinauralAuditoryL5Owner,
)
from dsf_ai_service.substrate.w1_binaural_grounding_evidence import (
    W1BinauralGroundingEvidenceAuthority,
    W1BinauralGroundingResourceProfile,
)
from dsf_ai_service.substrate.w1_physical_receptors import (
    EmbodimentSensoryOutcomeAuthority,
)
from dsf_ai_service.substrate.w1_self_acoustic_propagation import (
    W1SelfAcousticPropagationAuthority,
)
from tests.test_articulatory_self_vocal_motor import _program
from tests.test_lived_vocal_teaching_episode import _external_mount
from tests.test_w1_audiovisual_physical_evidence import (
    EVIDENCE_KEY,
    INTENT_RECEIPT,
    WORLD_KEY,
    _authority,
    _world,
)
from tests.test_w1_self_acoustic_propagation import (
    _modulated_tone_pcm,
)


KEY = b"grounded-articulatory-vocal-turn-owner-key"
MOTOR_KEY = b"grounded-articulatory-current-motor-owner-key"
ACOUSTIC_KEY = b"grounded-articulatory-self-acoustic-key"
THING_KEY = b"grounded-articulatory-causal-thing-key"
CONTEXT_KEY = b"grounded-articulatory-lived-context-key"
MEDIA_KEY = b"grounded-articulatory-retained-media-key"
PHYSICAL_ACTION_DURATION_US = 200_000
HONEST_VARIATION_SAMPLE_INDEX = 1_600
HONEST_VARIATION_DELTA = 9


def _q_owner():
    return AuditoryRecurrentMotifOwner(
        AuditoryMotifResourceProfile.create(
            profile_id="grounded-articulatory-binaural-q",
            ear_count=2,
            max_motif_neurons=24_192,
            max_pending_experiences=8,
            max_work_cells_per_observation=8_000_000,
            max_exact_fraction_text_bytes=4_096,
            encoded_state_allocation_bytes=128 * 1024 * 1024,
        ),
        ear_ids=("left", "right"),
    )


def _contact_execution(world):
    before = world.observation_snapshot()
    receipt = world.execute_port_command(
        port_id=PORT_ID,
        command_payload=encode_command(
            PickCommand(
                "teaching-object",
                duration_microseconds=PHYSICAL_ACTION_DURATION_US,
            )
        ),
        causal_intent_receipt_sha256=INTENT_RECEIPT,
        expected_revision=before.revision,
    )
    assert receipt.disposition == "applied"
    return receipt


def _honest_in_window_variation(baseline: bytes) -> bytes:
    changed = bytearray(baseline)
    offset = HONEST_VARIATION_SAMPLE_INDEX * 2
    if offset + 2 > len(changed):
        raise ValueError("honest variation left the source observation")
    original = int.from_bytes(
        changed[offset:offset + 2],
        "little",
        signed=True,
    )
    replacement = original + HONEST_VARIATION_DELTA
    if not -32_768 <= replacement <= 32_767:
        raise ValueError("honest variation left signed PCM")
    changed[offset:offset + 2] = replacement.to_bytes(
        2,
        "little",
        signed=True,
    )
    result = bytes(changed)
    assert result != baseline
    return result


def _full_dsf_values(mount):
    return {
        (
            sense.sense,
            substream.substream_id,
            tuple_index,
            name,
        ): value
        for sense in mount.causal_settlement.interpretations
        for substream in sense.substreams
        for tuple_index, field_tuple in enumerate(
            substream.field_tuples
        )
        for name, value in field_tuple.fields
    }


def _assert_honest_heard_variation(baseline_mount, challenge_mount):
    baseline_binaural = baseline_mount.binaural_pcm
    challenge_binaural = challenge_mount.binaural_pcm
    assert baseline_binaural is not None
    assert challenge_binaural is not None
    assert (
        baseline_binaural.left_pcm_s16le
        != challenge_binaural.left_pcm_s16le
    )
    assert (
        baseline_binaural.right_pcm_s16le
        != challenge_binaural.right_pcm_s16le
    )
    baseline_fields = _full_dsf_values(baseline_mount)
    challenge_fields = _full_dsf_values(challenge_mount)
    assert baseline_fields.keys() == challenge_fields.keys()
    changed_fields = tuple(
        key
        for key in baseline_fields
        if baseline_fields[key] != challenge_fields[key]
    )
    assert changed_fields
    assert any(key[0] == "sound" for key in changed_fields)
    assert all(key[3] in DSF_FIELD_ORDER for key in changed_fields)


class _System:
    pass


def _system():
    values = _System()
    values.world = _world()
    values.physical = _authority(values.world)
    contact_execution = _contact_execution(values.world)
    contact_mount = values.physical.mount_action_outcome(
        contact_execution
    )
    values.contact_custody = SettledExperienceCustodyAuthority(
        authority_key=KEY,
        w1_physical_authority_key=EVIDENCE_KEY,
        world_authority_key=WORLD_KEY,
        profile=SettledExperienceCustodyProfile.create(
            profile_id="grounded-articulatory-contact",
            max_children=8,
            max_snapshot_bytes=128 * 1024 * 1024,
        ),
    )
    values.contact_custody.admit(
        contact_mount,
        contact_execution,
    )
    values.partitions = CustodiedW1ContactThingEncounterAuthority(
        authority_key=THING_KEY,
        world_authority=values.world,
        sensory_authority=EmbodimentSensoryOutcomeAuthority(
            authority_key=WORLD_KEY
        ),
        max_roots_per_partition=512,
    )
    contact_capability = values.contact_custody.issue_child(
        THING_MOSAIC_CONSUMER_ID
    )
    partition = values.partitions.partition_from_custody(
        custody_authority=values.contact_custody,
        capability=contact_capability,
    )
    values.things = CausalThingMosaicOwner(
        authority_key=THING_KEY,
        profile=CausalThingMosaicProfile.create(
            profile_id="grounded-articulatory-THING",
            max_mosaics=4,
            max_partitions_per_mosaic=16,
            max_roots_per_partition=512,
            max_routes=4_096,
            max_state_bytes=64 * 1024 * 1024,
        ),
        partition_authority=values.partitions,
    )
    mosaic = values.things.admit(partition)
    values.thing_id = mosaic.thing_id
    values.expansions = CausalThingSensoryExpansionOwner(
        authority_key=THING_KEY,
        thing_owner=values.things,
        max_expansions=16,
        max_roots_per_expansion=512,
        max_state_bytes=64 * 1024 * 1024,
    )
    values.context = CausalThingLivedContextOwner(
        authority_key=CONTEXT_KEY,
        custody_authority_key=KEY,
        w1_physical_authority_key=EVIDENCE_KEY,
        world_authority_key=WORLD_KEY,
        w1_self_acoustic_authority_key=ACOUSTIC_KEY,
        thing_owner=values.things,
        sensory_expansion_owner=values.expansions,
        resource_profile=CausalThingLivedContextResourceProfile.create(
            profile_id="grounded-articulatory-context",
            max_episodes=16,
            max_events_per_episode=16,
            max_total_events=64,
            max_full_field_roots_per_event=512,
            max_state_bytes=64 * 1024 * 1024,
        ),
    )
    values.q = _q_owner()
    baseline = _modulated_tone_pcm(11_000)
    for _index in range(2):
        _execution_receipt, training = _external_mount(
            values.world,
            values.physical,
            baseline,
        )
        values.q.observe_binaural(
            training.binaural_receptor_settlement
        )
    values.grounding = W1BinauralGroundingEvidenceAuthority(
        authority_key=KEY,
        resource_profile=W1BinauralGroundingResourceProfile.create(
            profile_id="grounded-articulatory-form",
            max_activations=8_192,
            max_roots=512,
            max_evidence_bytes=64 * 1024 * 1024,
        ),
    )
    values.motor = ArticulatorySelfVocalMotorOwner(
        authority_key=MOTOR_KEY,
        resource_profile=ArticulatoryMotorResourceProfile.create(
            profile_id="grounded-articulatory-current-programs",
            max_programs=4,
            max_state_bytes=256 * 1024,
        ),
    )
    values.program = values.motor.admit_program(_program(16_000))
    values.acoustic = W1SelfAcousticPropagationAuthority(
        authority_key=ACOUSTIC_KEY,
        world_authority=values.world,
        causal_owner=ExactCausalExperienceOwner(
            on_settlement=lambda _value: None,
            log_event=lambda *_args, **_kwargs: None,
        ),
        binaural_l5_owner=W1BinauralAuditoryL5Owner(),
        binaural_motif_owner=values.q,
    )
    values.teaching = LivedVocalTeachingEpisodeAuthority(
        authority_key=KEY,
        resource_profile=LivedVocalTeachingResourceProfile.create(
            profile_id="grounded-articulatory-teaching",
            max_episodes=8,
            max_external_settlement_bytes=32 * 1024 * 1024,
            max_self_settlement_bytes=32 * 1024 * 1024,
            max_motor_pcm_bytes=64 * 1024,
            max_auditory_activations=8_192,
            max_witness_bytes=128 * 1024 * 1024,
            max_state_bytes=512 * 1024 * 1024,
        ),
        world_authority=values.world,
        grounding_authority=values.grounding,
    )
    values.media = RetainedAudiovisualCustodyAuthority(
        authority_key=MEDIA_KEY,
        max_live_occurrences=16,
        max_frames_per_occurrence=4,
    )
    values.seeded = False
    values.teachings = []
    values.external_mounts = []
    return values


def _teaching_occurrence(values, pressure, *, program=None):
    selected_program = values.program if program is None else program
    external_execution, external_mount = _external_mount(
        values.world,
        values.physical,
        pressure,
    )
    external_custody = SettledExperienceCustodyAuthority(
        authority_key=KEY,
        w1_physical_authority_key=EVIDENCE_KEY,
        world_authority_key=WORLD_KEY,
        profile=SettledExperienceCustodyProfile.create(
            profile_id=(
                "grounded-external-"
                + external_mount.causal_settlement
                .authority_receipt_sha256[:12]
            ),
            max_children=8,
            max_snapshot_bytes=128 * 1024 * 1024,
        ),
    )
    external_value = external_custody.admit(
        external_mount,
        external_execution,
    )
    external_form = values.grounding.admit(
        settlement=external_mount.causal_settlement,
        receptor_settlement=(
            external_mount.binaural_receptor_settlement
        ),
        firing=values.q.fire_binaural(
            external_mount.binaural_receptor_settlement
        ),
        motif_owner=values.q,
    )

    before = values.world.observation_snapshot()
    synthesis = values.motor.synthesize(
        program_id=selected_program.program_id,
        source_time_start=Fraction(
            before.revision * MAX_VOCAL_SAMPLE_COUNT,
            VOCAL_SAMPLE_RATE_HZ,
        ),
    )
    prepared_emission = values.motor.prepare_generated_emission(
        synthesis=synthesis,
        world_authority=values.world,
        causal_intent_receipt_sha256="b" * 64,
    )
    prepared_self = values.acoustic.prepare_articulatory(
        prepared_emission,
        articulatory_owner=values.motor,
    )
    self_emission, self_mount, _undo = (
        values.acoustic.commit_prepared_articulatory(prepared_self)
    )
    self_custody = SettledExperienceCustodyAuthority(
        authority_key=KEY,
        w1_physical_authority_key=EVIDENCE_KEY,
        w1_self_acoustic_authority_key=ACOUSTIC_KEY,
        world_authority_key=WORLD_KEY,
        profile=SettledExperienceCustodyProfile.create(
            profile_id=(
                "grounded-self-"
                + self_mount.receipt.authority_receipt_sha256[:12]
            ),
            max_children=8,
            max_snapshot_bytes=128 * 1024 * 1024,
        ),
    )
    self_custody.admit(
        self_mount,
        self_emission.execution_receipt,
    )
    external_teaching_capability = external_custody.issue_child(
        LIVED_VOCAL_TEACHING_CONSUMER_ID
    )
    self_teaching_capability = self_custody.issue_child(
        LIVED_VOCAL_TEACHING_CONSUMER_ID
    )
    episode = values.teaching.admit(
        external_custody_authority=external_custody,
        external_custody_capability=(
            external_teaching_capability
        ),
        self_custody_authority=self_custody,
        self_custody_capability=self_teaching_capability,
        auditory_form_evidence=external_form,
    )

    if not values.seeded:
        media = values.media.admit(
            settlement=external_mount.causal_settlement,
            frame_sha256s=("c" * 64,),
            canonical_audio_sha256="d" * 64,
        )
        media_capability = values.media.issue_child(
            media,
            THING_SENSORY_EXPANSION_CONSUMER_ID,
        )
        contact_capability = values.contact_custody.issue_child(
            THING_SENSORY_GROUNDING_CONSUMER_ID
        )
        seeded = values.expansions.admit_lived_contact_tutor(
            custody_authority=values.media,
            custody_capability=media_capability,
            contact_custody_authority=values.contact_custody,
            contact_custody_capability=contact_capability,
        )
        assert seeded.thing_id == values.thing_id
        values.seeded = True
    expansion_capability = external_custody.issue_child(
        THING_SENSORY_EXPANSION_CONSUMER_ID
    )
    expansion_admission = (
        values.expansions.admit_settled_known_sight(
            custody_authority=external_custody,
            custody_capability=expansion_capability,
        )
    )
    assert expansion_admission.state == "unique"
    expansion = expansion_admission.expansion
    assert expansion is not None
    context_admission = values.context.admit_settled_expansion(
        expansion,
        custody_authority=external_custody,
        custody_capability=expansion_capability,
    )
    event = context_admission.event
    values.context.verify_owned_event(event)
    assert event.source_occurrence_id == (
        external_value.source_occurrence_id
    )
    assert event.settlement_receipt_sha256 == (
        external_mount.causal_settlement.authority_receipt_sha256
    )
    assert event.thing_ids == (values.thing_id,)
    result = GroundedArticulatoryTeachingOccurrence(
        teaching_episode=episode,
        external_form=external_form,
        lived_context_event=event,
        articulatory_program=selected_program,
    )
    values.teachings.append(result)
    values.external_mounts.append(external_mount)
    return result


def _owner(values, *, max_occurrences=8, max_state_bytes=4 << 20):
    return GroundedArticulatoryVocalTurnOwner(
        authority_key=KEY,
        profile=GroundedArticulatoryVocalTurnProfile.create(
            profile_id="grounded-articulatory-owner",
            max_occurrences=max_occurrences,
            max_occurrence_bytes=512 * 1024,
            max_state_bytes=max_state_bytes,
        ),
        teaching_authority=values.teaching,
        grounding_authority=values.grounding,
        lived_context_owner=values.context,
        articulatory_owner=values.motor,
        world_authority=values.world,
        self_acoustic_authority=values.acoustic,
    )


@pytest.fixture(scope="module")
def learned_system():
    values = _system()
    baseline = _modulated_tone_pcm(11_000)
    first = _teaching_occurrence(values, baseline)
    second = _teaching_occurrence(values, baseline)
    owner = _owner(values)
    learned = owner.learn((first, second))
    baseline_mount = values.external_mounts[0]
    return values, owner, learned, baseline, baseline_mount


def test_two_independent_lived_teachings_cold_restore_and_bounds(
    learned_system,
):
    values, owner, learned, _baseline, _baseline_mount = learned_system
    assert len(learned) == 2
    assert len({value.teaching_episode_id for value in learned}) == 2
    assert len({
        value.external_source_occurrence_id for value in learned
    }) == 2
    assert len({
        value.external_settlement_receipt_sha256 for value in learned
    }) == 2
    assert len({
        value.external_grounding_receipt_sha256 for value in learned
    }) == 2
    assert {value.thing_id for value in learned} == {
        values.thing_id
    }
    assert len({value.form_sha256 for value in learned}) == 1
    encoded = owner.snapshot_encoded()
    assert len(encoded) < 512 * 1024
    assert len(encoded) < len(learned[0].teaching_episode_id) + sum(
        len(value.teaching_episode.witness_json)
        for value in values.teachings[:2]
    )
    assert b"source_json" not in encoded
    lowered = encoded.lower()
    for forbidden in (
        b'"chi"',
        b'"label"',
        b'"meaning"',
        b'"score"',
        b'"similarity"',
        b'"text"',
        b'"threshold"',
        b'"transcript"',
        b'"tts"',
        b'"word"',
    ):
        assert forbidden not in lowered
    assert owner.status()["retained_pcm_bytes"] == 0
    cold = _owner(values)
    cold.restore_encoded(encoded)
    assert cold.snapshot_encoded() == encoded
    tampered = bytearray(encoded)
    tampered[-8] = ord("0") if tampered[-8] != ord("0") else ord("1")
    with pytest.raises(ValueError):
        _owner(values).restore_encoded(bytes(tampered))
    limited = _owner(values, max_occurrences=1)
    with pytest.raises(RuntimeError, match="capacity exhausted"):
        limited.learn(tuple(values.teachings[:2]))


def test_held_out_heard_field_variation_emits_and_rolls_back(
    learned_system,
):
    values, owner, learned, baseline, baseline_mount = learned_system
    changed = _honest_in_window_variation(baseline)
    held_out = _teaching_occurrence(values, changed)
    held_out_mount = values.external_mounts[-1]
    _assert_honest_heard_variation(
        baseline_mount,
        held_out_mount,
    )
    prepared = owner.prepare_turn(
        external_form=held_out.external_form,
        lived_context_event=held_out.lived_context_event,
    )
    assert isinstance(prepared, PreparedGroundedArticulatoryVocalTurn)
    assert prepared.decision.state is (
        GroundedArticulatoryResolutionState.PREPARED
    )
    assert prepared.decision.form_sha256 == learned[0].form_sha256
    assert prepared.decision.selected_program_id == (
        values.program.program_id
    )
    before = values.world.observation_snapshot()
    output, undo = owner.commit_prepared(prepared)
    assert output.emission.pcm_s16le == (
        output.emission.synthesis.radiated_pcm_s16le
    )
    assert output.emission.synthesis.program == values.program
    assert output.self_hearing.receipt.motor_id == (
        values.program.program_id
    )
    assert output.full_dsf_tuple_count > 0
    assert all(
        tuple(name for name, _value in field_tuple.fields)
        == DSF_FIELD_ORDER
        for sense in output.self_hearing
        .causal_settlement.interpretations
        for substream in sense.substreams
        for field_tuple in substream.field_tuples
    )
    assert values.world.observation_snapshot().revision == (
        before.revision + 1
    )
    owner.rollback_committed(undo)
    assert values.world.observation_snapshot() == before
    assert learned[0].form_sha256 == learned[1].form_sha256


def test_one_teaching_is_unresolved_and_program_ambiguity_is_silent(
    learned_system,
):
    values, one, _learned, baseline, _baseline_mount = learned_system
    second_program = values.motor.admit_program(_program(15_000))
    alternative = (
        _teaching_occurrence(
            values, baseline, program=second_program
        ),
        _teaching_occurrence(
            values, baseline, program=second_program
        ),
    )
    one.learn(alternative)
    challenge = _teaching_occurrence(values, baseline)
    before = values.world.observation_snapshot()
    decision = one.prepare_turn(
        external_form=challenge.external_form,
        lived_context_event=challenge.lived_context_event,
    )
    assert decision.state is GroundedArticulatoryResolutionState.AMBIGUOUS
    assert decision.selected_program_id is None
    assert set(decision.grounded_program_ids) == {
        values.program.program_id,
        second_program.program_id,
    }
    assert values.world.observation_snapshot() == before

    fresh = _system()
    first = _teaching_occurrence(
        fresh, _modulated_tone_pcm(11_000)
    )
    unresolved_owner = _owner(fresh)
    with pytest.raises(ValueError, match="requires two"):
        unresolved_owner.learn((first,))


def test_failure_after_physical_commit_rolls_back(monkeypatch):
    values = _system()
    baseline = _modulated_tone_pcm(11_000)
    first = _teaching_occurrence(values, baseline)
    second = _teaching_occurrence(values, baseline)
    baseline_mount = values.external_mounts[0]
    owner = _owner(values)
    learned = owner.learn((first, second))
    changed = _honest_in_window_variation(baseline)
    held_out = _teaching_occurrence(values, changed)
    held_out_mount = values.external_mounts[-1]
    _assert_honest_heard_variation(
        baseline_mount,
        held_out_mount,
    )
    prepared = owner.prepare_turn(
        external_form=held_out.external_form,
        lived_context_event=held_out.lived_context_event,
    )
    assert isinstance(prepared, PreparedGroundedArticulatoryVocalTurn)
    assert prepared.decision.form_sha256 == learned[0].form_sha256
    before = values.world.observation_snapshot()

    def fail_full_field(_mount):
        raise RuntimeError("injected output seal failure")

    monkeypatch.setattr(owner, "_full_field", fail_full_field)
    with pytest.raises(RuntimeError, match="injected"):
        owner.commit_prepared(prepared)
    assert values.world.observation_snapshot() == before
