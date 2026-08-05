from __future__ import annotations

import ast
import hashlib
import inspect
import json
import struct
from dataclasses import replace
from fractions import Fraction

import pytest

import dsf_ai_service.substrate.settled_experience_custody as custody_module
from dsf_ai_service.glew_runtime.global_uf import DSF_FIELD_ORDER
from dsf_ai_service.substrate.articulatory_self_vocal_motor import (
    ArticulatoryMotorResourceProfile,
    ArticulatorySelfVocalMotorOwner,
)
from dsf_ai_service.substrate.embodiment_world import (
    MAX_VOCAL_SAMPLE_COUNT,
    PORT_ID,
    VOCAL_SAMPLE_RATE_HZ,
    ActionExecutionReceipt,
    EmbodiedBody,
    EmbodiedObject,
    EmbodimentPort,
    EmbodimentWorldAuthority,
    ObservationSnapshot,
    PickCommand,
    PoseMM,
    PositionMM,
    VocalizeCommand,
    encode_command,
)
from dsf_ai_service.substrate.exact_causal_experience import (
    ExactCausalExperienceOwner,
)
from dsf_ai_service.substrate.settled_experience_custody import (
    SettledExperienceConsumerView,
    SettledExperienceCustodyAuthority,
    SettledExperienceCustodyProfile,
)
from dsf_ai_service.substrate.w1_acoustic_emitter import (
    W1AcousticEmitterAuthority,
)
from dsf_ai_service.substrate.w1_anonymous_audiovisual_continuity import (
    W1AnonymousAudiovisualContinuityOwner,
)
from dsf_ai_service.substrate.w1_audiovisual_physical_evidence import (
    W1AudiovisualPhysicalEvidenceAuthority,
    W1PhysicalEvidenceMount,
)
from dsf_ai_service.substrate.w1_binaural_auditory_l5 import (
    W1BinauralAuditoryL5Owner,
)
from dsf_ai_service.substrate.auditory_recurrent_motif import (
    AuditoryMotifResourceProfile,
    AuditoryRecurrentMotifOwner,
)
from dsf_ai_service.substrate.w1_self_acoustic_propagation import (
    W1SelfAcousticPropagationAuthority,
)
from tests.test_articulatory_self_vocal_motor import _program


WORLD_KEY = b"world-authority-key-for-custody-tests"
PHYSICAL_KEY = b"physical-authority-key-for-custody-tests"
EMISSION_KEY = b"emission-authority-key-for-custody-tests"
CONTINUITY_KEY = b"continuity-authority-key-for-custody-tests"
CUSTODY_KEY = b"settled-custody-authority-key-for-tests"
SELF_ACOUSTIC_KEY = b"settled-custody-self-acoustic-authority-key"
ARTICULATORY_KEY = b"settled-custody-articulatory-authority-key"
INTENT_RECEIPT = "1" * 64
EMITTER_PORT = "w1.external-emitter"


def _pcm(sample_count: int = 960) -> bytes:
    samples = tuple(
        12_000 if index % 16 < 8 else -12_000
        for index in range(sample_count)
    )
    return struct.pack(f"<{sample_count}h", *samples)


def _settled_w1_occurrence(
) -> tuple[
    W1PhysicalEvidenceMount,
    ActionExecutionReceipt,
]:
    world = EmbodimentWorldAuthority(
        authority_key=WORLD_KEY,
        bodies=(
            EmbodiedBody(
                "external-body",
                PoseMM(PositionMM(3_500, 2_500, 0), 180_000),
                radius_mm=200,
                reach_mm=600,
            ),
            EmbodiedBody(
                "guala-body-1",
                PoseMM(PositionMM(1_000, 1_000, 0), 0),
                radius_mm=250,
                reach_mm=800,
            ),
        ),
        actor_ports=(
            EmbodimentPort(PORT_ID, "guala-body-1"),
            EmbodimentPort(EMITTER_PORT, "external-body"),
        ),
        initial_objects=(
            EmbodiedObject(
                "teaching-object",
                radius_mm=100,
                mass_grams=500,
                position=PositionMM(1_500, 1_000, 0),
            ),
        ),
    )
    causal_owner = ExactCausalExperienceOwner(
        on_settlement=lambda _settlement: None,
        log_event=lambda *_args, **_kwargs: None,
    )
    physical = W1AudiovisualPhysicalEvidenceAuthority(
        authority_key=PHYSICAL_KEY,
        world_authority=world,
        causal_owner=causal_owner,
        acoustic_emitter=W1AcousticEmitterAuthority(
            authority_key=EMISSION_KEY,
            world_authority=world,
        ),
        binaural_auditory_l5_owner=W1BinauralAuditoryL5Owner(),
        anonymous_av_continuity_owner=(
            W1AnonymousAudiovisualContinuityOwner(
                authority_key=CONTINUITY_KEY,
                physical_authority_key=PHYSICAL_KEY,
            )
        ),
    )
    epoch = physical.open_epoch()
    pcm = _pcm()
    command = VocalizeCommand(
        epoch_commitment_sha256=hashlib.sha256(
            epoch.encode("utf-8")
        ).hexdigest(),
        sequence=0,
        source_sample_start=0,
        pcm_sha256=hashlib.sha256(pcm).hexdigest(),
        sample_count=len(pcm) // 2,
    )
    command_payload = encode_command(command)
    before = world.observation_snapshot()
    execution = world.execute_port_command(
        port_id=EMITTER_PORT,
        command_payload=command_payload,
        causal_intent_receipt_sha256=INTENT_RECEIPT,
        expected_revision=before.revision,
    )
    emission = physical.emit_acoustic_pressure(
        epoch_token=epoch,
        sequence=0,
        source_sample_start=0,
        observation_snapshot=execution.after,
        execution_receipt=execution,
        command_payload=command_payload,
        emitter_port_id=EMITTER_PORT,
        pcm_s16le=pcm,
    )
    mount = physical.mount(
        epoch_token=epoch,
        sequence=0,
        execution_receipt=execution,
        acoustic_emission=emission,
        commit=True,
    )
    physical.verify_mount(mount)
    return mount, execution


def _settled_non_acoustic_w1_occurrence(
) -> tuple[
    W1PhysicalEvidenceMount,
    ActionExecutionReceipt,
]:
    world = EmbodimentWorldAuthority(
        authority_key=WORLD_KEY,
        bodies=(
            EmbodiedBody(
                "external-body",
                PoseMM(PositionMM(3_500, 2_500, 0), 180_000),
                radius_mm=200,
                reach_mm=600,
            ),
            EmbodiedBody(
                "guala-body-1",
                PoseMM(PositionMM(1_000, 1_000, 0), 0),
                radius_mm=250,
                reach_mm=800,
            ),
        ),
        actor_ports=(
            EmbodimentPort(PORT_ID, "guala-body-1"),
            EmbodimentPort(EMITTER_PORT, "external-body"),
        ),
        initial_objects=(
            EmbodiedObject(
                "teaching-object",
                radius_mm=100,
                mass_grams=500,
                position=PositionMM(1_500, 1_000, 0),
            ),
        ),
    )
    physical = W1AudiovisualPhysicalEvidenceAuthority(
        authority_key=PHYSICAL_KEY,
        world_authority=world,
        causal_owner=ExactCausalExperienceOwner(
            on_settlement=lambda _settlement: None,
            log_event=lambda *_args, **_kwargs: None,
        ),
        acoustic_emitter=W1AcousticEmitterAuthority(
            authority_key=EMISSION_KEY,
            world_authority=world,
        ),
        binaural_auditory_l5_owner=W1BinauralAuditoryL5Owner(),
        anonymous_av_continuity_owner=(
            W1AnonymousAudiovisualContinuityOwner(
                authority_key=CONTINUITY_KEY,
                physical_authority_key=PHYSICAL_KEY,
            )
        ),
    )
    before = world.observation_snapshot()
    execution = world.execute_port_command(
        port_id=PORT_ID,
        command_payload=encode_command(
            PickCommand("teaching-object", 200_000)
        ),
        causal_intent_receipt_sha256=INTENT_RECEIPT,
        expected_revision=before.revision,
    )
    mount = physical.mount_action_outcome(execution)
    physical.verify_mount(mount)
    return mount, execution


def _settled_passive_w1_occurrence(
) -> tuple[
    W1PhysicalEvidenceMount,
    ObservationSnapshot,
]:
    world = EmbodimentWorldAuthority(
        authority_key=WORLD_KEY,
        bodies=(
            EmbodiedBody(
                "external-body",
                PoseMM(PositionMM(3_500, 2_500, 0), 180_000),
                radius_mm=200,
                reach_mm=600,
            ),
            EmbodiedBody(
                "guala-body-1",
                PoseMM(PositionMM(1_000, 1_000, 0), 0),
                radius_mm=250,
                reach_mm=800,
            ),
        ),
        actor_ports=(
            EmbodimentPort(PORT_ID, "guala-body-1"),
            EmbodimentPort(EMITTER_PORT, "external-body"),
        ),
        initial_objects=(
            EmbodiedObject(
                "teaching-object",
                radius_mm=100,
                mass_grams=500,
                position=PositionMM(1_500, 1_000, 0),
            ),
        ),
    )
    physical = W1AudiovisualPhysicalEvidenceAuthority(
        authority_key=PHYSICAL_KEY,
        world_authority=world,
        causal_owner=ExactCausalExperienceOwner(
            on_settlement=lambda _settlement: None,
            log_event=lambda *_args, **_kwargs: None,
        ),
        acoustic_emitter=W1AcousticEmitterAuthority(
            authority_key=EMISSION_KEY,
            world_authority=world,
        ),
        binaural_auditory_l5_owner=W1BinauralAuditoryL5Owner(),
        anonymous_av_continuity_owner=(
            W1AnonymousAudiovisualContinuityOwner(
                authority_key=CONTINUITY_KEY,
                physical_authority_key=PHYSICAL_KEY,
            )
        ),
    )
    observation = world.observation_snapshot()
    mount = physical.mount_current_observation(commit=True)
    physical.verify_mount(mount)
    return mount, observation


def _authority(
    *,
    max_children: int = 4,
    max_snapshot_bytes: int = 64 * 1024 * 1024,
) -> SettledExperienceCustodyAuthority:
    return SettledExperienceCustodyAuthority(
        authority_key=CUSTODY_KEY,
        w1_physical_authority_key=PHYSICAL_KEY,
        world_authority_key=WORLD_KEY,
        w1_self_acoustic_authority_key=SELF_ACOUSTIC_KEY,
        profile=SettledExperienceCustodyProfile.create(
            profile_id="test-settled-w1-custody",
            max_children=max_children,
            max_snapshot_bytes=max_snapshot_bytes,
        ),
    )


def _settled_self_acoustic_occurrence():
    world = EmbodimentWorldAuthority(authority_key=WORLD_KEY)
    motor = ArticulatorySelfVocalMotorOwner(
        authority_key=ARTICULATORY_KEY,
        resource_profile=ArticulatoryMotorResourceProfile.create(
            profile_id="settled-custody-articulatory-programs",
            max_programs=2,
            max_state_bytes=256 * 1024,
        ),
    )
    program = motor.admit_program(_program(16_000))
    owner = W1SelfAcousticPropagationAuthority(
        authority_key=SELF_ACOUSTIC_KEY,
        world_authority=world,
        causal_owner=ExactCausalExperienceOwner(
            on_settlement=lambda _settlement: None,
            log_event=lambda *_args, **_kwargs: None,
        ),
        binaural_l5_owner=W1BinauralAuditoryL5Owner(),
        binaural_motif_owner=AuditoryRecurrentMotifOwner(
            AuditoryMotifResourceProfile.create(
                profile_id="settled-custody-self-acoustic-q",
                ear_count=2,
                max_motif_neurons=24_192,
                max_pending_experiences=8,
                max_work_cells_per_observation=8_000_000,
                max_exact_fraction_text_bytes=4_096,
                encoded_state_allocation_bytes=128 * 1024 * 1024,
            ),
            ear_ids=("left", "right"),
        ),
    )
    before = world.observation_snapshot()
    synthesis = motor.synthesize(
        program_id=program.program_id,
        source_time_start=Fraction(
            before.revision * MAX_VOCAL_SAMPLE_COUNT,
            VOCAL_SAMPLE_RATE_HZ,
        ),
    )
    prepared_emission = motor.prepare_generated_emission(
        synthesis=synthesis,
        world_authority=world,
        causal_intent_receipt_sha256="9" * 64,
    )
    prepared_mount = owner.prepare_articulatory(
        prepared_emission,
        articulatory_owner=motor,
    )
    emission, mount, _undo = owner.commit_prepared_articulatory(
        prepared_mount
    )
    return mount, emission.execution_receipt


def test_one_w1_occurrence_has_one_full_field_custody_lineage():
    mount, execution = _settled_w1_occurrence()
    authority = _authority()

    custody = authority.admit(mount, execution)
    repeated = authority.admit(mount, execution)

    assert repeated is custody
    assert custody.world_execution is execution
    assert custody.physical_evidence_receipt is mount.evidence_receipt
    assert custody.causal_settlement is mount.causal_settlement
    assert custody.binaural_auditory_l5 is mount.binaural_auditory_l5
    assert (
        custody.binaural_receptor_settlement
        is mount.binaural_receptor_settlement
    )
    assert custody.occurrence_counter.source_transduction_lineage_count == 1
    assert custody.occurrence_counter.full_field_build_lineage_count == 1
    assert custody.occurrence_counter.causal_settlement_lineage_count == 1
    assert custody.occurrence_counter.custody_count == 1

    field_tuple_count = 0
    for sense in custody.causal_settlement.interpretations:
        for substream in sense.substreams:
            assert substream.coordinates
            for field_tuple in substream.field_tuples:
                field_tuple_count += 1
                assert tuple(
                    name for name, _value in field_tuple.fields
                ) == DSF_FIELD_ORDER
    assert field_tuple_count > 0


def test_self_acoustic_source_is_one_typed_complete_custody():
    mount, execution = _settled_self_acoustic_occurrence()
    authority = _authority()

    custody = authority.admit(mount, execution)
    child = authority.issue_child("self-acoustic-continuation")
    view = authority.open_child(child)

    assert custody.source_kind.value == "w1_self_acoustic"
    assert custody.physical_evidence_receipt is None
    assert custody.self_acoustic_receipt is mount.receipt
    assert (
        custody.self_acoustic_prelearning_firing
        is mount.prelearning_firing
    )
    assert custody.self_acoustic_observation is mount.observation
    assert custody.causal_settlement is mount.causal_settlement
    assert custody.binaural_auditory_l5 is mount.binaural_l5
    assert custody.binaural_receptor_settlement is mount.receptor_settlement
    assert view.source_kind is custody.source_kind
    assert view.self_acoustic_receipt is mount.receipt
    assert (
        view.self_acoustic_prelearning_firing
        is mount.prelearning_firing
    )
    assert view.self_acoustic_observation is mount.observation
    assert view.world_execution is execution
    assert view.occurrence_counter.source_transduction_lineage_count == 1
    observed = {
        interpretation.sense
        for interpretation in custody.causal_settlement.interpretations
        if interpretation.state == "observed"
    }
    assert observed == {"body", "sight", "sound", "touch"}
    assert all(
        tuple(name for name, _value in field_tuple.fields)
        == DSF_FIELD_ORDER
        for interpretation in custody.causal_settlement.interpretations
        for substream in interpretation.substreams
        for field_tuple in substream.field_tuples
    )

    encoded = authority.snapshot_encoded()
    restored = SettledExperienceCustodyAuthority.restore_encoded(
        encoded,
        authority_key=CUSTODY_KEY,
        w1_physical_authority_key=PHYSICAL_KEY,
        world_authority_key=WORLD_KEY,
        source_mount=mount,
        w1_self_acoustic_authority_key=SELF_ACOUSTIC_KEY,
        world_execution=execution,
    )
    assert restored.snapshot_encoded() == encoded


def test_every_child_capability_names_the_same_parent_and_exact_objects(
    monkeypatch,
):
    mount, execution = _settled_w1_occurrence()
    authority = _authority()
    custody = authority.admit(mount, execution)
    settlement_type = type(custody.causal_settlement)
    original_verify = settlement_type.verify
    verify_calls = 0

    def counted_verify(value):
        nonlocal verify_calls
        verify_calls += 1
        return original_verify(value)

    monkeypatch.setattr(settlement_type, "verify", counted_verify)

    prediction = authority.issue_child("full-field-prediction")
    teaching = authority.issue_child("lived-vocal-teaching")
    assert authority.issue_child("full-field-prediction") is prediction

    for capability in (prediction, teaching):
        assert (
            capability.parent_custody_receipt_sha256
            == custody.authority_receipt_sha256
        )
        assert capability.source_occurrence_id == custody.source_occurrence_id
        view = authority.open_child(capability)
        assert isinstance(view, SettledExperienceConsumerView)
        assert view.causal_settlement is custody.causal_settlement
        assert view.binaural_auditory_l5 is custody.binaural_auditory_l5
        assert (
            view.binaural_receptor_settlement
            is custody.binaural_receptor_settlement
        )

    alien = replace(
        prediction,
        parent_custody_receipt_sha256="f" * 64,
    )
    with pytest.raises(
            ValueError,
            match="another parent",
        ):
        authority.open_child(alien)
    assert verify_calls == 0


def test_non_acoustic_action_outcome_has_common_full_field_custody():
    mount, execution = _settled_non_acoustic_w1_occurrence()
    authority = _authority()

    custody = authority.admit(mount, execution)
    child = authority.issue_child("physical-action-learning")
    view = authority.open_child(child)

    assert custody.world_execution is execution
    assert custody.physical_evidence_receipt is mount.evidence_receipt
    assert custody.causal_settlement is mount.causal_settlement
    assert custody.physical_evidence_receipt.acoustic_emission_receipt_sha256s == ()
    assert custody.binaural_auditory_l5 is None
    assert custody.binaural_receptor_settlement is None
    assert custody.occurrence_counter.binaural_l5_receipt_sha256 is None
    assert custody.occurrence_counter.binaural_receptor_receipt_sha256 is None
    assert view.causal_settlement is custody.causal_settlement
    assert view.binaural_auditory_l5 is None
    assert view.binaural_receptor_settlement is None

    observed = {
        interpretation.sense
        for interpretation in custody.causal_settlement.interpretations
        if interpretation.state == "observed"
    }
    assert observed == {"sight", "body"}
    for interpretation in custody.causal_settlement.interpretations:
        for substream in interpretation.substreams:
            for field_tuple in substream.field_tuples:
                assert tuple(
                    name for name, _value in field_tuple.fields
                ) == DSF_FIELD_ORDER

    encoded = authority.snapshot_encoded()
    restored = SettledExperienceCustodyAuthority.restore_encoded(
        encoded,
        authority_key=CUSTODY_KEY,
        w1_physical_authority_key=PHYSICAL_KEY,
        world_authority_key=WORLD_KEY,
        source_mount=mount,
        world_execution=execution,
    )
    assert restored.snapshot_encoded() == encoded
    assert restored.custody is not None
    assert restored.custody.binaural_auditory_l5 is None
    assert restored.custody.binaural_receptor_settlement is None


def test_passive_current_observation_has_no_fabricated_execution():
    mount, observation = _settled_passive_w1_occurrence()
    authority = _authority()

    custody = authority.admit(
        mount,
        world_observation=observation,
    )
    child = authority.issue_child("passive-play-trigger")
    view = authority.open_child(child)

    assert custody.world_execution is None
    assert custody.world_observation is observation
    assert custody.occurrence_counter.world_execution_receipt_sha256 is None
    assert (
        custody.occurrence_counter.world_observation_receipt_sha256
        == observation.authority_receipt_sha256
    )
    assert custody.physical_evidence_receipt.world_execution_receipt_sha256 is None
    assert custody.physical_evidence_receipt.world_observation_before_receipt_sha256 == (
        observation.authority_receipt_sha256
    )
    assert custody.physical_evidence_receipt.world_observation_after_receipt_sha256 == (
        observation.authority_receipt_sha256
    )
    assert view.world_execution is None
    assert view.world_observation is observation

    encoded = authority.snapshot_encoded()
    restored = SettledExperienceCustodyAuthority.restore_encoded(
        encoded,
        authority_key=CUSTODY_KEY,
        w1_physical_authority_key=PHYSICAL_KEY,
        world_authority_key=WORLD_KEY,
        source_mount=mount,
        world_observation=observation,
    )
    assert restored.snapshot_encoded() == encoded
    assert restored.custody is not None
    assert restored.custody.world_execution is None
    assert restored.custody.world_observation is observation

    with pytest.raises(
        ValueError,
        match="exactly one world occurrence variant",
    ):
        _authority().admit(
            mount,
            world_observation=observation,
            world_execution=object(),
        )


def test_snapshot_restore_is_byte_identical_and_requires_live_typed_custody():
    mount, execution = _settled_w1_occurrence()
    authority = _authority()
    authority.admit(mount, execution)
    authority.issue_child("full-field-prediction")
    authority.issue_child("causal-deliberation")
    encoded = authority.snapshot_encoded()

    restored = SettledExperienceCustodyAuthority.restore_encoded(
        encoded,
        authority_key=CUSTODY_KEY,
        w1_physical_authority_key=PHYSICAL_KEY,
        world_authority_key=WORLD_KEY,
        source_mount=mount,
        world_execution=execution,
    )

    assert restored.snapshot_encoded() == encoded
    assert restored.custody is not None
    assert (
        restored.custody.source_occurrence_id
        == authority.custody.source_occurrence_id
    )
    assert tuple(
        value.consumer_id for value in restored.children
    ) == (
        "full-field-prediction",
        "causal-deliberation",
    )

    decoded = json.loads(encoded)
    decoded["authority_hmac_sha256"] = "0" * 64
    tampered = json.dumps(
        decoded,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    with pytest.raises(
        ValueError,
        match="snapshot authority changed",
    ):
        SettledExperienceCustodyAuthority.restore_encoded(
            tampered,
            authority_key=CUSTODY_KEY,
            w1_physical_authority_key=PHYSICAL_KEY,
            world_authority_key=WORLD_KEY,
            source_mount=mount,
            world_execution=execution,
        )


def test_child_and_snapshot_capacities_fail_closed():
    mount, execution = _settled_w1_occurrence()
    authority = _authority(max_children=1)
    authority.admit(mount, execution)
    authority.issue_child("first")
    with pytest.raises(RuntimeError, match="child capacity is full"):
        authority.issue_child("second")

    too_small = _authority(max_snapshot_bytes=4_096)
    with pytest.raises(
        RuntimeError,
        match="snapshot byte capacity is full",
    ):
        too_small.admit(mount, execution)
    assert too_small.custody is None


def test_custody_rejects_raw_pcm_bare_world_and_incomplete_mounts():
    mount, execution = _settled_w1_occurrence()
    authority = _authority()

    with pytest.raises(TypeError, match="typed W1 source variant"):
        authority.admit(b"\x00\x00", execution)
    with pytest.raises(TypeError, match="world execution is not typed"):
        authority.admit(mount, execution.after)
    incomplete = replace(
        mount,
        binaural_receptor_settlement=None,
    )
    with pytest.raises(
        ValueError,
        match="acoustic receptor evidence is incomplete",
    ):
        authority.admit(incomplete, execution)


def test_downstream_contract_has_no_remount_or_resettlement_surface(
    monkeypatch,
):
    mount, execution = _settled_w1_occurrence()

    tree = ast.parse(inspect.getsource(custody_module))
    forbidden_calls = {
        "mount",
        "mount_action_outcome",
        "mount_authenticated_action_outcome",
        "mount_current_observation",
        "settle",
        "transduce",
        "transduce_auditory_full_field",
    }
    observed_calls = {
        node.func.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
    }
    assert observed_calls.isdisjoint(forbidden_calls)
    assert set(SettledExperienceConsumerView.__dataclass_fields__) == {
        "source_occurrence_id",
        "parent_custody_receipt_sha256",
        "source_kind",
        "world_execution",
        "world_observation",
            "physical_evidence_receipt",
            "anonymous_passive_window_receipt",
        "self_acoustic_receipt",
        "self_acoustic_prelearning_firing",
        "self_acoustic_observation",
        "causal_settlement",
        "binaural_auditory_l5",
        "binaural_receptor_settlement",
        "occurrence_counter",
    }
    assert "physical_mount" not in SettledExperienceConsumerView.__slots__
    assert "binaural_pcm" not in SettledExperienceConsumerView.__slots__
    assert "causal_owner" not in SettledExperienceConsumerView.__slots__
    assert "world_authority" not in SettledExperienceConsumerView.__slots__

    def forbidden(*_args, **_kwargs):
        raise AssertionError(
            "custody invoked a forbidden producer"
        )

    monkeypatch.setattr(
        W1AudiovisualPhysicalEvidenceAuthority,
        "mount",
        forbidden,
    )
    monkeypatch.setattr(
        W1AudiovisualPhysicalEvidenceAuthority,
        "mount_current_observation",
        forbidden,
    )
    monkeypatch.setattr(
        W1AudiovisualPhysicalEvidenceAuthority,
        "mount_action_outcome",
        forbidden,
    )
    monkeypatch.setattr(
        ExactCausalExperienceOwner,
        "settle",
        forbidden,
    )

    authority = _authority()
    authority.admit(mount, execution)
    child = authority.issue_child("negative-contract-consumer")
    view = authority.open_child(child)
    encoded = authority.snapshot_encoded()
    restored = SettledExperienceCustodyAuthority.restore_encoded(
        encoded,
        authority_key=CUSTODY_KEY,
        w1_physical_authority_key=PHYSICAL_KEY,
        world_authority_key=WORLD_KEY,
        source_mount=mount,
        world_execution=execution,
    )
    assert view.causal_settlement is mount.causal_settlement
    assert restored.snapshot_encoded() == encoded
