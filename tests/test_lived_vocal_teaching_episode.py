from __future__ import annotations

import base64
import json
import math
from fractions import Fraction

import numpy as np
import pytest

from dsf_ai_service.glew_runtime.global_uf import DSF_FIELD_ORDER
from dsf_ai_service.substrate.articulatory_self_vocal_motor import (
    ArticulatoryMotorResourceProfile,
    ArticulatoryProgram,
    ArticulatorySelfVocalMotorOwner,
    LaryngealExcitationConfiguration,
    VocalTractConfiguration,
)
from dsf_ai_service.substrate.auditory_recurrent_motif import (
    AuditoryMotifResourceProfile,
    AuditoryRecurrentMotifOwner,
)
from dsf_ai_service.substrate.embodiment_world import (
    MAX_VOCAL_SAMPLE_COUNT,
    PORT_ID,
    VOCAL_SAMPLE_RATE_HZ,
    MoveCommand,
    PoseMM,
    PositionMM,
    encode_command,
)
from dsf_ai_service.substrate.exact_causal_experience import (
    ExactCausalExperienceOwner,
)
from dsf_ai_service.substrate.lived_vocal_teaching_episode import (
    LIVED_VOCAL_TEACHING_CONSUMER_ID,
    LivedVocalTeachingEpisodeAuthority,
    LivedVocalTeachingResourceProfile,
)
from dsf_ai_service.substrate.senses.auditory_full_field_provider import (
    REQUIRED_SAMPLE_RATE_HZ,
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
from dsf_ai_service.substrate.w1_self_acoustic_propagation import (
    W1PreparedArticulatoryCommitment,
    W1SelfAcousticPropagationAuthority,
    W1SelfAcousticState,
)
from tests.test_w1_audiovisual_physical_evidence import (
    EVIDENCE_KEY,
    WORLD_KEY,
    _authority,
    _emission,
    _vocal_execution,
    _world,
)


KEY = b"lived-vocal-teaching-episode-authority-key"


def _profile(*, max_episodes: int = 4):
    return LivedVocalTeachingResourceProfile.create(
        profile_id="lived-vocal-teaching-production-proof",
        max_episodes=max_episodes,
        max_external_settlement_bytes=32 * 1024 * 1024,
        max_self_settlement_bytes=32 * 1024 * 1024,
        max_motor_pcm_bytes=64 * 1024,
        max_auditory_activations=8_192,
        max_witness_bytes=128 * 1024 * 1024,
        max_state_bytes=256 * 1024 * 1024,
    )


def _binaural_q():
    return AuditoryRecurrentMotifOwner(
        AuditoryMotifResourceProfile.create(
            profile_id="lived-vocal-teaching-binaural-q",
            ear_count=2,
            max_motif_neurons=24_192,
            max_pending_experiences=8,
            max_work_cells_per_observation=8_000_000,
            max_exact_fraction_text_bytes=4_096,
            encoded_state_allocation_bytes=128 * 1024 * 1024,
        ),
        ear_ids=("left", "right"),
    )


def _modulated_tone_pcm(amplitude: int) -> bytes:
    sample_count = 3_200
    source_times = np.arange(sample_count) / REQUIRED_SAMPLE_RATE_HZ
    values = np.rint(
        amplitude
        * (0.55 + 0.4 * np.sin(2 * math.pi * 5 * source_times))
        * np.sin(2 * math.pi * 440 * source_times)
    ).astype("<i2")
    return values.tobytes()


def _articulatory_program() -> ArticulatoryProgram:
    return ArticulatoryProgram.create(
        sample_count=3_200,
        larynx=LaryngealExcitationConfiguration(
            cycle_samples=80,
            open_samples=48,
            peak_volume_velocity_pcm=16_000,
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


def _external_mount(world, physical, pressure):
    epoch = physical.open_epoch()
    execution = _vocal_execution(
        world,
        epoch,
        sequence=0,
        source_sample_start=0,
        pcm=pressure,
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
            pcm=pressure,
        ),
    )
    assert mount.causal_settlement is not None
    assert mount.binaural_receptor_settlement is not None
    assert physical.close_epoch(epoch) is True
    return execution, mount


def _commit_articulatory_self_hearing(
    *,
    articulatory,
    program,
    world,
    self_acoustic,
    causal_intent_receipt_sha256,
):
    before = world.observation_snapshot()
    synthesis = articulatory.synthesize(
        program_id=program.program_id,
        source_time_start=Fraction(
            before.revision * MAX_VOCAL_SAMPLE_COUNT,
            VOCAL_SAMPLE_RATE_HZ,
        ),
    )
    prepared_emission = articulatory.prepare_generated_emission(
        synthesis=synthesis,
        world_authority=world,
        causal_intent_receipt_sha256=(
            causal_intent_receipt_sha256
        ),
    )
    prepared_mount = self_acoustic.prepare_articulatory(
        prepared_emission,
        articulatory_owner=articulatory,
    )
    commitment = self_acoustic.prepared_articulatory_commitment(
        prepared_mount
    )
    assert isinstance(commitment, W1PreparedArticulatoryCommitment)
    self_acoustic.verify_prepared_articulatory_commitment(
        prepared_mount,
        commitment,
    )
    emission, outcome, _undo = (
        self_acoustic.commit_prepared_articulatory(prepared_mount)
    )
    articulatory.verify_generated_emission(
        emission,
        world_authority=world,
    )
    assert outcome.receipt.state is W1SelfAcousticState.OBSERVED
    assert emission.execution_receipt.before == before
    assert (
        outcome.receipt.self_vocal_emission_receipt_sha256
        == emission.emission_receipt.authority_receipt_sha256
    )
    return synthesis, emission, outcome, commitment


def _stack():
    pressure = _modulated_tone_pcm(11_000)
    world = _world()
    physical = _authority(world)
    q_owner = _binaural_q()
    for _index in range(2):
        _execution, training = _external_mount(
            world, physical, pressure
        )
        q_owner.observe_binaural(
            training.binaural_receptor_settlement
        )
    external_execution, external_mount = _external_mount(
        world, physical, pressure
    )
    custody_authority = SettledExperienceCustodyAuthority(
        authority_key=KEY,
        w1_physical_authority_key=EVIDENCE_KEY,
        world_authority_key=WORLD_KEY,
        profile=SettledExperienceCustodyProfile.create(
            profile_id="lived-vocal-teaching-custody",
            max_children=4,
            max_snapshot_bytes=128 * 1024 * 1024,
        ),
    )
    custody = custody_authority.admit(
        external_mount,
        external_execution,
    )
    custody_capability = custody_authority.issue_child(
        LIVED_VOCAL_TEACHING_CONSUMER_ID
    )
    firing = q_owner.fire_binaural(
        external_mount.binaural_receptor_settlement
    )
    assert firing.activations
    grounding = W1BinauralGroundingEvidenceAuthority(
        authority_key=KEY,
        resource_profile=W1BinauralGroundingResourceProfile.create(
            profile_id="lived-vocal-teaching-grounding",
            max_activations=8_192,
            max_roots=256,
            max_evidence_bytes=64 * 1024 * 1024,
        ),
    )
    auditory_form = grounding.admit(
        settlement=external_mount.causal_settlement,
        receptor_settlement=(
            external_mount.binaural_receptor_settlement
        ),
        firing=firing,
        motif_owner=q_owner,
    )
    articulatory = ArticulatorySelfVocalMotorOwner(
        authority_key=KEY,
        resource_profile=ArticulatoryMotorResourceProfile.create(
            profile_id="lived-vocal-teaching-articulatory",
            max_programs=2,
            max_state_bytes=64 * 1024,
        ),
    )
    program = articulatory.admit_program(_articulatory_program())
    self_acoustic = W1SelfAcousticPropagationAuthority(
        authority_key=KEY,
        world_authority=world,
        causal_owner=ExactCausalExperienceOwner(
            on_settlement=lambda _settlement: None,
            log_event=lambda *_args, **_kwargs: None,
        ),
        binaural_l5_owner=W1BinauralAuditoryL5Owner(),
        binaural_motif_owner=q_owner,
    )
    (
        self_synthesis,
        self_emission,
        self_outcome,
        self_commitment,
    ) = _commit_articulatory_self_hearing(
        articulatory=articulatory,
        program=program,
        world=world,
        self_acoustic=self_acoustic,
        causal_intent_receipt_sha256="8" * 64,
    )
    self_custody_authority = SettledExperienceCustodyAuthority(
        authority_key=KEY,
        w1_physical_authority_key=EVIDENCE_KEY,
        w1_self_acoustic_authority_key=KEY,
        world_authority_key=WORLD_KEY,
        profile=SettledExperienceCustodyProfile.create(
            profile_id="lived-vocal-teaching-self-custody",
            max_children=4,
            max_snapshot_bytes=128 * 1024 * 1024,
        ),
    )
    self_custody = self_custody_authority.admit(
        self_outcome,
        self_emission.execution_receipt,
    )
    self_custody_capability = (
        self_custody_authority.issue_child(
            LIVED_VOCAL_TEACHING_CONSUMER_ID
        )
    )
    return {
        "articulatory": articulatory,
        "auditory_form": auditory_form,
        "custody": custody,
        "custody_authority": custody_authority,
        "custody_capability": custody_capability,
        "external_execution": external_execution,
        "external_mount": external_mount,
        "grounding": grounding,
        "physical": physical,
        "program": program,
        "q_owner": q_owner,
        "self_acoustic": self_acoustic,
        "self_commitment": self_commitment,
        "self_custody": self_custody,
        "self_custody_authority": self_custody_authority,
        "self_custody_capability": self_custody_capability,
        "self_emission": self_emission,
        "self_outcome": self_outcome,
        "self_synthesis": self_synthesis,
        "world": world,
    }


def _owner(stack, *, profile=None):
    return LivedVocalTeachingEpisodeAuthority(
        authority_key=KEY,
        resource_profile=profile or _profile(),
        world_authority=stack["world"],
        grounding_authority=stack["grounding"],
    )


def _admit(owner, stack):
    return owner.admit(
        external_custody_authority=stack["custody_authority"],
        external_custody_capability=stack["custody_capability"],
        self_custody_authority=stack["self_custody_authority"],
        self_custody_capability=stack["self_custody_capability"],
        auditory_form_evidence=stack["auditory_form"],
    )


def _all_keys(value):
    if isinstance(value, dict):
        result = set(value)
        for nested in value.values():
            result.update(_all_keys(nested))
        return result
    if isinstance(value, list):
        result = set()
        for nested in value:
            result.update(_all_keys(nested))
        return result
    return set()


def _assert_full_field(settlement):
    assert all(
        tuple(name for name, _value in field_tuple.fields)
        == DSF_FIELD_ORDER
        for sense in settlement.interpretations
        for substream in sense.substreams
        for field_tuple in substream.field_tuples
    )


def test_one_receipt_retains_full_lived_field_form_and_self_outcome():
    stack = _stack()
    owner = _owner(stack)

    episode = _admit(owner, stack)

    owner.verify(episode)
    witness = owner.witness(episode)
    external_payload = base64.b64decode(
        witness["external_multisensory"][
            "settlement_payload_base64"
        ],
        validate=True,
    )
    exact_external = (
        stack["custody"].causal_settlement.receipt_registry.resolve(
            stack["custody"]
            .causal_settlement.authority_receipt_sha256,
            "test external settlement",
        )
    )
    assert external_payload == exact_external
    assert (
        witness["auditory_form_evidence"][
            "causal_settlement_receipt_sha256"
        ]
        == witness["external_multisensory"][
            "settlement_receipt_sha256"
        ]
    )
    assert witness["causal_junction"][
        "world_observation_receipt_sha256"
    ] == stack["self_emission"].execution_receipt.before \
        .authority_receipt_sha256
    assert (
        stack["self_emission"].emission_receipt.program_id
        == stack["program"].program_id
    )
    assert (
        stack["self_commitment"].prospective_emission_receipt_sha256
        == stack["self_emission"]
        .emission_receipt.authority_receipt_sha256
    )
    _assert_full_field(stack["custody"].causal_settlement)
    _assert_full_field(stack["self_custody"].causal_settlement)
    assert {
        activation.ear_id
        for activation in stack["auditory_form"].activations
    } == {"left", "right"}
    assert not {
        "chi",
        "decision_vector",
        "label",
        "legacy_binding",
        "score",
        "text",
        "transcript",
        "tts",
    }.intersection(_all_keys(witness))
    assert _admit(owner, stack) == episode


def test_intervening_world_action_cannot_be_joined_after_the_fact():
    stack = _stack()
    world = stack["world"]
    before = world.observation_snapshot()
    gap = world.execute_port_command(
        port_id=PORT_ID,
        command_payload=encode_command(MoveCommand(PoseMM(
            PositionMM(1_100, 1_000, 0),
            0,
        ), duration_microseconds=200_000)),
        causal_intent_receipt_sha256="9" * 64,
        expected_revision=before.revision,
    )
    assert gap.disposition == "applied"
    _synthesis, emission, outcome, _commitment = (
        _commit_articulatory_self_hearing(
            articulatory=stack["articulatory"],
            program=stack["program"],
            world=world,
            self_acoustic=stack["self_acoustic"],
            causal_intent_receipt_sha256="a" * 64,
        )
    )
    gap_custody = SettledExperienceCustodyAuthority(
        authority_key=KEY,
        w1_physical_authority_key=EVIDENCE_KEY,
        w1_self_acoustic_authority_key=KEY,
        world_authority_key=WORLD_KEY,
        profile=SettledExperienceCustodyProfile.create(
            profile_id="lived-vocal-gap-self-custody",
            max_children=2,
            max_snapshot_bytes=128 * 1024 * 1024,
        ),
    )
    gap_custody.admit(outcome, emission.execution_receipt)
    gap_child = gap_custody.issue_child(
        LIVED_VOCAL_TEACHING_CONSUMER_ID
    )
    owner = _owner(stack)

    with pytest.raises(
        ValueError,
        match="immediate physical outcome",
    ):
        owner.admit(
            external_custody_authority=stack["custody_authority"],
            external_custody_capability=stack["custody_capability"],
            self_custody_authority=gap_custody,
            self_custody_capability=gap_child,
            auditory_form_evidence=stack["auditory_form"],
        )


def test_auditory_form_from_another_settlement_is_rejected():
    stack = _stack()
    execution, mount = _external_mount(
        stack["world"],
        stack["physical"],
        _modulated_tone_pcm(11_000),
    )
    firing = stack["q_owner"].fire_binaural(
        mount.binaural_receptor_settlement
    )
    other_form = stack["grounding"].admit(
        settlement=mount.causal_settlement,
        receptor_settlement=mount.binaural_receptor_settlement,
        firing=firing,
        motif_owner=stack["q_owner"],
    )
    assert execution.authority_receipt_sha256 != (
        stack["external_execution"].authority_receipt_sha256
    )
    owner = _owner(stack)

    with pytest.raises(
        ValueError,
        match="not mounted in this experience",
    ):
        owner.admit(
            external_custody_authority=stack["custody_authority"],
            external_custody_capability=stack["custody_capability"],
            self_custody_authority=stack["self_custody_authority"],
            self_custody_capability=stack["self_custody_capability"],
            auditory_form_evidence=other_form,
        )


def test_authenticated_snapshot_round_trip_and_tamper_rejection():
    stack = _stack()
    owner = _owner(stack)
    episode = _admit(owner, stack)
    encoded = owner.encoded_snapshot()
    restored = _owner(stack)

    restored.restore_encoded(encoded)

    assert restored.episodes == (episode,)
    restored.verify(episode)
    envelope = json.loads(encoded)
    envelope["body"]["episodes"][0]["witness_json"] += " "
    tampered = json.dumps(
        envelope,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    with pytest.raises(ValueError, match="state authority changed"):
        restored.restore_encoded(tampered)
