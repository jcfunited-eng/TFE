from __future__ import annotations

import json
import math
from dataclasses import replace
from fractions import Fraction

import pytest

from dsf_ai_service.glew_runtime.global_uf import DSF_FIELD_ORDER
from dsf_ai_service.glew_runtime.native_sensory_full_field import (
    NativeSensorySubstreamInput,
    build_six_sense_full_field,
)
from dsf_ai_service.glew_runtime.sensory_full_field_boundary import (
    NativeAxisCoordinate,
    PhysicalSense,
    SENSE_ORDER,
    SenseBoundaryState,
)
from dsf_ai_service.substrate.anonymous_passive_window import (
    AnonymousPassiveWindowAuthority,
    AnonymousPassiveWindowCapacityError,
    AnonymousPassiveWindowProfile,
    MAX_ANONYMOUS_PASSIVE_WINDOW_TRANSFER_BYTES,
)
from dsf_ai_service.substrate.embodiment_world import (
    EmbodimentWorldAuthority,
)
from dsf_ai_service.substrate.exact_causal_experience import (
    ExactCausalExperienceOwner,
)
from dsf_ai_service.substrate.settled_experience_custody import (
    SettledExperienceCustodyAuthority,
    SettledExperienceCustodyProfile,
    SettledExperienceSourceKind,
)
from tests.native_joint_occurrence_support import joint_occurrences_for


WINDOW_KEY = b"anonymous-passive-window-authority-key-v1"
WORLD_KEY = b"anonymous-passive-window-world-key-v1"
CUSTODY_KEY = b"anonymous-passive-window-custody-key-v1"
PHYSICAL_KEY = b"unused-w1-physical-authority-key-v1"


def _native(sense, sensor_id, substream_id, topology_index):
    count = 48
    return NativeSensorySubstreamInput(
        sense=sense,
        sensor_id=sensor_id,
        substream_id=substream_id,
        topology_index=topology_index,
        coordinates=(
            NativeAxisCoordinate("receptor", str(topology_index)),
        ),
        physical_quantity=(
            "sound-pressure"
            if sense is PhysicalSense.SOUND
            else "light-intensity"
        ),
        physical_unit="exact-normalized-physical-input",
        source_times=tuple(
            Fraction(index, 1_000) for index in range(count)
        ),
        normalized_signal=tuple(
            math.sin(
                2
                * math.pi
                * (topology_index + 2)
                * index
                / count
            )
            for index in range(count)
        ),
        phase_turns=tuple(
            Fraction(index // 8) for index in range(count)
        ),
    )


def _settlement(
    window_id,
    *,
    receptors,
    audiovisual,
    routing_chis=(),
    direct_assembly_identity=False,
):
    sound = tuple(
        _native(
            PhysicalSense.SOUND,
            receptor,
            f"{receptor}-pressure",
            index,
        )
        for index, receptor in enumerate(receptors)
    )
    observed = {PhysicalSense.SOUND: sound}
    if audiovisual:
        observed[PhysicalSense.SIGHT] = (
            _native(
                PhysicalSense.SIGHT,
                "retina",
                "retinal-region",
                0,
            ),
        )
    states = {
        sense: (
            SenseBoundaryState.OBSERVED
            if sense in observed
            else SenseBoundaryState.SENSOR_UNAVAILABLE
        )
        for sense in SENSE_ORDER
    }
    built = build_six_sense_full_field(
        assembly_id=(
            window_id
            if direct_assembly_identity
            else f"causal-{window_id}"
        ),
        source_time_start=Fraction(0),
        source_time_end=Fraction(48, 1_000),
        observed_substreams=observed, occurrences=joint_occurrences_for(observed),
        states=states,
    )
    return ExactCausalExperienceOwner(
        on_settlement=lambda _value: None,
        log_event=lambda *_args, **_kwargs: None,
    ).settle(
        built,
        routing_chis=routing_chis,
        source_tags=(),
    )


def _authority(
    world,
    *,
    max_state_bytes=32 * 1024 * 1024,
    max_transfer_bytes=None,
):
    return AnonymousPassiveWindowAuthority(
        authority_key=WINDOW_KEY,
        profile=AnonymousPassiveWindowProfile.create(
            profile_id="anonymous-passive-window-focused",
            max_mounts=1,
            max_state_bytes=max_state_bytes,
        ),
        world_authority=world,
        max_transfer_bytes=max_transfer_bytes,
    )


def test_direct_authenticated_assembly_identity_is_preserved():
    world = EmbodimentWorldAuthority(authority_key=WORLD_KEY)
    owner = _authority(world)
    assembly_id = "w1-physical-audiovisual-window"
    settlement = _settlement(
        assembly_id,
        receptors=("left-ear", "right-ear"),
        audiovisual=True,
        direct_assembly_identity=True,
    )
    prepared = owner.prepare(
        window_id=assembly_id,
        settlement=settlement,
        world_observation=world.observation_snapshot(),
    )

    assert prepared.mount.receipt.window_id == assembly_id
    assert prepared.mount.receipt.assembly_id == assembly_id
    prepared.mount.receipt.verify(WINDOW_KEY)

    with pytest.raises(
        ValueError,
        match="assembly identity changed",
    ):
        replace(
            prepared.mount.receipt,
            window_id="different-window",
        ).verify(WINDOW_KEY)


@pytest.mark.parametrize(
    ("receptors", "topology"),
    [
        (("microphone",), "mono"),
        (("left-ear", "right-ear"), "binaural"),
    ],
)
def test_exact_mono_and_binaural_passive_topology(
    receptors,
    topology,
):
    world = EmbodimentWorldAuthority(authority_key=WORLD_KEY)
    owner = _authority(world)
    settlement = _settlement(
        f"{topology}-window",
        receptors=receptors,
        audiovisual=False,
    )
    observation = world.observation_snapshot()
    prepared = owner.prepare(
        window_id=f"{topology}-window",
        settlement=settlement,
        world_observation=observation,
    )
    mount = prepared.mount

    assert mount.settlement is settlement
    assert mount.world_observation is observation
    assert mount.receipt.auditory_topology == topology
    assert (
        mount.receipt.settled_window_identity.window_id
        == f"{topology}-window"
    )
    assert (
        mount.receipt.settled_window_identity
        .settlement_receipt_sha256
        == settlement.authority_receipt_sha256
    )
    assert (
        mount.receipt.auditory_receptor_ids
        == tuple(sorted(receptors))
    )
    assert mount.receipt.audiovisual is False
    assert mount.receipt.full_field_tuple_count > 0
    assert json.loads(mount.receipt.topology_json)
    assert all(
        tuple(name for name, _value in field_tuple.fields)
        == DSF_FIELD_ORDER
        for sense in settlement.interpretations
        for substream in sense.substreams
        for field_tuple in substream.field_tuples
    )
    assert not hasattr(mount.receipt, "world_execution")
    assert not mount.receipt.meaning_authority
    assert not mount.receipt.word_authority
    assert not mount.receipt.label_authority
    assert not mount.receipt.recognition_authority


def test_audiovisual_transfer_enters_custody_and_lineage_cold_restores():
    world = EmbodimentWorldAuthority(authority_key=WORLD_KEY)
    owner = _authority(world)
    settlement = _settlement(
        "audiovisual-window",
        receptors=("left-ear", "right-ear"),
        audiovisual=True,
    )
    prepared = owner.prepare(
        window_id="audiovisual-window",
        settlement=settlement,
        world_observation=world.observation_snapshot(),
    )
    mount = prepared.mount
    assert mount.receipt.audiovisual is True

    custody = SettledExperienceCustodyAuthority(
        authority_key=CUSTODY_KEY,
        w1_physical_authority_key=PHYSICAL_KEY,
        world_authority_key=WORLD_KEY,
        anonymous_passive_window_authority_key=WINDOW_KEY,
        profile=SettledExperienceCustodyProfile.create(
            profile_id="anonymous-window-custody",
            max_children=2,
            max_snapshot_bytes=64 * 1024 * 1024,
        ),
    )
    admitted = custody.admit(mount)
    owner.commit_prepared(prepared)
    assert len(owner.receipt_lineage) == 1
    assert owner.receipt_lineage[0] is mount.receipt
    assert not hasattr(owner, "_mounts")

    encoded_owner = owner.snapshot_encoded()
    cold_owner = AnonymousPassiveWindowAuthority.restore_encoded(
        authority_key=WINDOW_KEY,
        profile=owner._profile,
        world_authority=world,
        encoded=encoded_owner,
    )
    assert cold_owner.snapshot_encoded() == encoded_owner
    assert cold_owner.receipt_lineage == (mount.receipt,)

    child = custody.issue_child("passive-window-test")
    view = custody.open_child(child)
    assert admitted.world_execution is None
    assert (
        view.source_kind
        is SettledExperienceSourceKind.ANONYMOUS_PASSIVE_WINDOW
    )
    assert view.world_execution is None
    assert view.causal_settlement is settlement
    assert view.world_observation is mount.world_observation
    assert view.anonymous_passive_window_receipt is mount.receipt
    encoded_custody = custody.snapshot_encoded()
    cold_custody = SettledExperienceCustodyAuthority.restore_encoded(
        encoded_custody,
        authority_key=CUSTODY_KEY,
        w1_physical_authority_key=PHYSICAL_KEY,
        world_authority_key=WORLD_KEY,
        anonymous_passive_window_authority_key=WINDOW_KEY,
        source_mount=mount,
    )
    assert cold_custody.snapshot_encoded() == encoded_custody

    forged = bytearray(encoded_owner)
    forged[-8] = ord("0") if forged[-8] != ord("0") else ord("1")
    with pytest.raises(ValueError):
        AnonymousPassiveWindowAuthority.restore_encoded(
            authority_key=WINDOW_KEY,
            profile=owner._profile,
            world_authority=world,
            encoded=bytes(forged),
        )


def test_forgery_symbolic_authority_and_transactions_fail_closed():
    world = EmbodimentWorldAuthority(authority_key=WORLD_KEY)
    owner = _authority(world)
    settlement = _settlement(
        "transaction-window",
        receptors=("microphone",),
        audiovisual=False,
    )
    before = owner.snapshot_encoded()
    prepared = owner.prepare(
        window_id="transaction-window",
        settlement=settlement,
        world_observation=world.observation_snapshot(),
    )
    with pytest.raises(ValueError, match="topology authority"):
        owner.verify_mount(
            replace(
                prepared.mount,
                receipt=replace(
                    prepared.mount.receipt,
                    topology_sha256="f" * 64,
                ),
            )
        )
    owner.discard_prepared(prepared)
    assert owner.snapshot_encoded() == before

    committed = owner.prepare(
        window_id="transaction-window",
        settlement=settlement,
        world_observation=world.observation_snapshot(),
    )
    undo = owner.commit_prepared(committed)
    admitted = owner.snapshot_encoded()
    replacement = owner.prepare(
        window_id="replacement-window",
        settlement=_settlement(
            "replacement-window",
            receptors=("microphone",),
            audiovisual=False,
        ),
        world_observation=world.observation_snapshot(),
    )
    owner.discard_prepared(replacement)
    owner.rollback_committed(undo)
    assert owner.snapshot_encoded() == before
    assert admitted != before

    symbolic = _settlement(
        "symbolic-window",
        receptors=("microphone",),
        audiovisual=False,
        routing_chis=(7,),
    )
    with pytest.raises(ValueError, match="symbolic or source"):
        owner.prepare(
            window_id="symbolic-window",
            settlement=symbolic,
            world_observation=world.observation_snapshot(),
        )


def test_transient_full_mount_extent_is_bounded():
    world = EmbodimentWorldAuthority(authority_key=WORLD_KEY)
    owner = _authority(world, max_state_bytes=4_096)
    settlement = _settlement(
        "capacity-window",
        receptors=("left-ear", "right-ear"),
        audiovisual=True,
    )
    with pytest.raises(
        AnonymousPassiveWindowCapacityError,
        match="transfer capacity",
    ) as captured:
        owner.prepare(
            window_id="capacity-window",
            settlement=settlement,
            world_observation=world.observation_snapshot(),
        )
    message = str(captured.value)
    assert "transfer_bytes=" in message
    assert "transfer_limit=" in message
    assert "retained_bytes=" in message
    assert "retained_limit=4096" in message
    assert owner.receipt_lineage == ()
    assert owner.snapshot_encoded()


def test_live_transfer_capacity_is_derived_and_separate_from_retained_state():
    world = EmbodimentWorldAuthority(authority_key=WORLD_KEY)
    owner = _authority(
        world,
        max_state_bytes=32 * 1024 * 1024,
        max_transfer_bytes=MAX_ANONYMOUS_PASSIVE_WINDOW_TRANSFER_BYTES,
    )
    assert (
        owner._max_transfer_bytes
        == MAX_ANONYMOUS_PASSIVE_WINDOW_TRANSFER_BYTES
    )
    assert owner._max_transfer_bytes > owner._profile.max_state_bytes

    encoded = owner.snapshot_encoded()
    restored = AnonymousPassiveWindowAuthority.restore_encoded(
        authority_key=WINDOW_KEY,
        profile=owner._profile,
        world_authority=world,
        encoded=encoded,
        max_transfer_bytes=MAX_ANONYMOUS_PASSIVE_WINDOW_TRANSFER_BYTES,
    )
    assert restored.snapshot_encoded() == encoded
    assert restored._max_transfer_bytes == owner._max_transfer_bytes
