from __future__ import annotations

import hashlib
import inspect
import json
import math
import struct
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from fractions import Fraction

import pytest

import dsf_ai_service.substrate.articulatory_consequence_closure as closure_module
from dsf_ai_service.substrate.articulatory_consequence_closure import (
    ArticulatoryConsequenceClosureOwner,
    ArticulatoryConsequenceClosureProfile,
)
from dsf_ai_service.substrate.articulatory_self_vocal_motor import (
    ArticulatoryMotorResourceProfile,
    ArticulatorySelfVocalMotorOwner,
)
from dsf_ai_service.substrate.auditory_recurrent_motif import (
    AuditoryMotifResourceProfile,
    AuditoryRecurrentMotifOwner,
)
from dsf_ai_service.substrate.causal_thing_mosaic import (
    CausalThingMosaicOwner,
    CausalThingMosaicProfile,
)
from dsf_ai_service.substrate.custodied_thing_encounter import (
    THING_MOSAIC_CONSUMER_ID,
    CustodiedW1ContactThingEncounterAuthority,
)
from dsf_ai_service.substrate.embodiment_world import (
    MAX_VOCAL_SAMPLE_COUNT,
    PORT_ID,
    SECOND_BODY_PORT_ID,
    VOCAL_SAMPLE_RATE_HZ,
    EmbodimentWorldAuthority,
    MoveCommand,
    PickCommand,
    PlaceCommand,
    PoseMM,
    PositionMM,
    encode_command,
)
from dsf_ai_service.substrate.exact_causal_experience import (
    ExactCausalExperienceOwner,
)
from dsf_ai_service.substrate.fresh_articulatory_self_acoustic_custody import (
    FRESH_ARTICULATORY_SELF_ACOUSTIC_CONSUMER_ID,
    FreshArticulatorySelfAcousticCustodyAuthority,
    FreshArticulatorySelfAcousticCustodyProfile,
)
from dsf_ai_service.substrate.settled_experience_custody import (
    SettledExperienceCustodyAuthority,
    SettledExperienceCustodyProfile,
)
from dsf_ai_service.substrate.w1_binaural_auditory_l5 import (
    W1BinauralAuditoryL5Owner,
)
from dsf_ai_service.substrate.w1_companion_vocal_experience import (
    W1CompanionVocalExperienceAuthority,
)
from dsf_ai_service.substrate.w1_physical_receptors import (
    EmbodimentSensoryOutcomeAuthority,
)
from dsf_ai_service.substrate.w1_self_acoustic_propagation import (
    W1SelfAcousticPropagationAuthority,
)
from tests.test_articulatory_self_vocal_motor import _program
from tests.test_w1_audiovisual_physical_evidence import (
    EVIDENCE_KEY,
    _authority as _physical_authority,
)


ARTICULATORY_KEY = b"consequence-direct-articulatory-authority-key"
ACOUSTIC_KEY = b"consequence-direct-self-acoustic-authority-key"
THING_KEY = b"consequence-direct-causal-thing-authority-key"
FRESH_KEY = b"consequence-direct-fresh-custody-authority-key"
CLOSURE_KEY = b"consequence-direct-closure-authority-key"
COMPANION_KEY = b"consequence-direct-companion-vocal-authority-key"


def _intent(name: str) -> str:
    return hashlib.sha256(name.encode("utf-8")).hexdigest()


def _vocal_pcm() -> bytes:
    return b"".join(
        struct.pack(
            "<h",
            int(8_000 * math.sin(2 * math.pi * 220 * index / 16_000)),
        )
        for index in range(960)
    )


def _assert_no_persistence_failure(capfd) -> None:
    captured = capfd.readouterr()
    combined = f"{captured.out}\n{captured.err}".lower()
    assert "persistence failed" not in combined
    assert "diary utc-day capacity is full" not in combined


class _Harness:
    """One isolated physical world with no engine or diary persistence."""

    def __init__(
        self,
        *,
        world_key: bytes,
        max_bindings: int = 8,
        max_closure_state_bytes: int = 8 * 1024 * 1024,
    ) -> None:
        self.world_key = world_key
        self.world = EmbodimentWorldAuthority(
            authority_key=world_key
        )
        self.sensory = EmbodimentSensoryOutcomeAuthority(
            authority_key=world_key
        )
        self.partitions = CustodiedW1ContactThingEncounterAuthority(
            authority_key=THING_KEY,
            world_authority=self.world,
            sensory_authority=self.sensory,
            max_roots_per_partition=512,
        )
        self.things = CausalThingMosaicOwner(
            authority_key=THING_KEY,
            profile=CausalThingMosaicProfile.create(
                profile_id="consequence-direct-thing-mosaics",
                max_mosaics=4,
                max_partitions_per_mosaic=32,
                max_roots_per_partition=512,
                max_routes=16_384,
                max_state_bytes=128 * 1024 * 1024,
            ),
            partition_authority=self.partitions,
        )
        self.physical = _physical_authority(self.world)
        self.companion_vocal = W1CompanionVocalExperienceAuthority(
            authority_key=COMPANION_KEY,
            world_authority=self.world,
            physical_authority=self.physical,
        )
        self.articulatory = ArticulatorySelfVocalMotorOwner(
            authority_key=ARTICULATORY_KEY,
            resource_profile=ArticulatoryMotorResourceProfile.create(
                profile_id="consequence-direct-programs",
                max_programs=4,
                max_state_bytes=256 * 1024,
            ),
        )
        self.programs = (
            self.articulatory.admit_program(_program(14_000)),
            self.articulatory.admit_program(_program(16_000)),
        )

        self.acoustic = W1SelfAcousticPropagationAuthority(
            authority_key=ACOUSTIC_KEY,
            world_authority=self.world,
            causal_owner=ExactCausalExperienceOwner(
                on_settlement=lambda _settlement: None,
                log_event=lambda *_args, **_kwargs: None,
            ),
            binaural_l5_owner=W1BinauralAuditoryL5Owner(),
            binaural_motif_owner=AuditoryRecurrentMotifOwner(
                AuditoryMotifResourceProfile.create(
                    profile_id="consequence-direct-binaural-q",
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
        self.fresh_profile = (
            FreshArticulatorySelfAcousticCustodyProfile.create(
                profile_id="consequence-direct-fresh-attempt",
                max_full_field_tuples=4_000_000,
                max_receipt_bytes=64 * 1024,
            )
        )
        self.fresh = FreshArticulatorySelfAcousticCustodyAuthority(
            authority_key=FRESH_KEY,
            profile=self.fresh_profile,
            articulatory_owner=self.articulatory,
            world_authority=self.world,
            acoustic_authority=self.acoustic,
        )
        self.closure_profile = (
            ArticulatoryConsequenceClosureProfile.create(
                profile_id="consequence-direct-bindings",
                max_bindings=max_bindings,
                max_state_bytes=max_closure_state_bytes,
            )
        )
        self.closure = ArticulatoryConsequenceClosureOwner(
            authority_key=CLOSURE_KEY,
            profile=self.closure_profile,
            fresh_custody_authority=self.fresh,
            thing_owner=self.things,
            articulatory_owner=self.articulatory,
            world_authority=self.world,
            companion_vocal_authority=self.companion_vocal,
        )
        self._custody_ordinal = 0

    def _next_custody_key(self) -> bytes:
        self._custody_ordinal += 1
        return hashlib.sha256(
            (
                f"consequence-direct-custody-"
                f"{self._custody_ordinal}"
            ).encode("utf-8")
        ).digest()

    def _execute(self, *, port_id: str, command, intent: str):
        before = self.world.observation_snapshot()
        result = self.world.execute_port_command(
            port_id=port_id,
            command_payload=encode_command(command),
            causal_intent_receipt_sha256=intent,
            expected_revision=before.revision,
        )
        assert result.disposition == "applied", result.reason
        return result

    def self_action(self, command, name: str):
        return self._execute(
            port_id=PORT_ID,
            command=command,
            intent=_intent(name),
        )

    def companion_action(
        self,
        *,
        causal_intent_receipt_sha256: str,
    ):
        before = self.world.observation_snapshot()
        companion = next(
            body
            for body in before.bodies
            if body.body_id != before.self_body_id
        )
        midpoint_x = (
            before.room_bounds.minimum.x
            + before.room_bounds.maximum.x
        ) // 2
        displacement = (
            -25
            if companion.pose.position.x > midpoint_x
            else 25
        )
        return self._execute(
            port_id=SECOND_BODY_PORT_ID,
            command=MoveCommand(
                target_pose=PoseMM(
                    PositionMM(
                        companion.pose.position.x + displacement,
                        companion.pose.position.y,
                        companion.pose.position.z,
                    ),
                    companion.pose.heading_millidegrees,
                ),
                duration_microseconds=100_000,
            ),
            intent=causal_intent_receipt_sha256,
        )

    def _settled(self, mount, execution, *, self_acoustic: bool):
        authority = SettledExperienceCustodyAuthority(
            authority_key=self._next_custody_key(),
            w1_physical_authority_key=EVIDENCE_KEY,
            world_authority_key=self.world_key,
            w1_self_acoustic_authority_key=(
                ACOUSTIC_KEY if self_acoustic else None
            ),
            profile=SettledExperienceCustodyProfile.create(
                profile_id=(
                    f"consequence-direct-occurrence-"
                    f"{self._custody_ordinal}"
                ),
                max_children=4,
                max_snapshot_bytes=128 * 1024 * 1024,
            ),
        )
        authority.admit(mount, execution)
        return authority

    def _physical_partition(
        self,
        execution,
        *,
        prior=None,
    ):
        mount = self.physical.mount_action_outcome(execution)
        custody = self._settled(
            mount,
            execution,
            self_acoustic=False,
        )
        capability = custody.issue_child(THING_MOSAIC_CONSUMER_ID)
        return self.partitions.partition_from_custody(
            custody_authority=custody,
            capability=capability,
            prior=prior,
        )

    def start_first_thing(self):
        picked = self.self_action(
            PickCommand(
                object_id="W1-object-1",
                duration_microseconds=100_000,
            ),
            "pick-first-thing",
        )
        return self.things.admit(self._physical_partition(picked))

    def start_second_thing(self):
        self.self_action(
            PlaceCommand(
                object_id="W1-object-1",
                target_position=PositionMM(1_000, 1_700, 0),
                duration_microseconds=100_000,
            ),
            "place-first-thing",
        )
        self.self_action(
            MoveCommand(
                target_pose=PoseMM(
                    PositionMM(2_000, 1_000, 0),
                    0,
                ),
                duration_microseconds=100_000,
            ),
            "move-to-second-thing",
        )
        picked = self.self_action(
            PickCommand(
                object_id="W1-object-2",
                duration_microseconds=100_000,
            ),
            "pick-second-thing",
        )
        return self.things.admit(self._physical_partition(picked))

    def attempt(
        self,
        mosaic,
        *,
        program_id: str,
        name: str,
    ):
        before = self.world.observation_snapshot()
        synthesis = self.articulatory.synthesize(
            program_id=program_id,
            source_time_start=Fraction(
                before.revision * MAX_VOCAL_SAMPLE_COUNT,
                VOCAL_SAMPLE_RATE_HZ,
            ),
        )
        prepared_emission = (
            self.articulatory.prepare_generated_emission(
                synthesis=synthesis,
                world_authority=self.world,
                causal_intent_receipt_sha256=_intent(name),
            )
        )
        prepared_mount = self.acoustic.prepare_articulatory(
            prepared_emission,
            articulatory_owner=self.articulatory,
        )
        (
            emission,
            mount,
            _acoustic_undo,
        ) = self.acoustic.commit_prepared_articulatory(prepared_mount)
        custody = self._settled(
            mount,
            emission.execution_receipt,
            self_acoustic=True,
        )
        thing_capability = custody.issue_child(
            THING_MOSAIC_CONSUMER_ID
        )
        partition = self.partitions.partition_from_custody(
            custody_authority=custody,
            capability=thing_capability,
            prior=mosaic.partitions[-1],
        )
        mosaic = self.things.admit(partition)
        fresh_capability = custody.issue_child(
            FRESH_ARTICULATORY_SELF_ACOUSTIC_CONSUMER_ID
        )
        receipt = self.fresh.seal(
            synthesis=synthesis,
            emission=emission,
            acoustic_mount=mount,
            settled_custody_authority=custody,
            settled_custody_capability=fresh_capability,
        )
        return mosaic, receipt, synthesis

    def admit_consequence(self, mosaic, consequence):
        partition = self._physical_partition(
            consequence,
            prior=mosaic.partitions[-1],
        )
        return self.things.admit(partition)


def test_accepted_lineage_is_transactional_concurrent_cold_and_media_free(
    capfd,
) -> None:
    harness = _Harness(
        world_key=b"consequence-accepted-direct-world-key"
    )
    mosaic = harness.start_first_thing()
    mosaic, attempt, _synthesis = harness.attempt(
        mosaic,
        program_id=harness.programs[0].program_id,
        name="accepted-attempt",
    )
    consequence = harness.companion_action(
        causal_intent_receipt_sha256=(
            attempt.authority_receipt_sha256
        )
    )

    empty = harness.closure.snapshot_encoded()
    prepared = harness.closure.prepare(attempt, consequence)
    assert harness.closure.snapshot_encoded() == empty
    assert harness.closure.bindings == ()
    assert not hasattr(prepared, "binding")
    assert mosaic.thing_id not in repr(prepared)
    assert harness.programs[0].program_id not in repr(prepared)
    with pytest.raises(ValueError, match="not retained"):
        harness.closure.verify_binding(prepared._candidate_binding)
    harness.closure.discard_prepared(prepared)
    assert harness.closure.snapshot_encoded() == empty

    candidates = tuple(
        harness.closure.prepare(attempt, consequence)
        for _index in range(8)
    )
    with ThreadPoolExecutor(max_workers=8) as executor:
        committed = tuple(executor.map(
            harness.closure.commit_prepared,
            candidates,
        ))
    assert len(harness.closure.bindings) == 1
    assert sum(value.undo.changed for value in committed) == 1
    binding = harness.closure.bindings[0]
    assert binding.thing_id == mosaic.thing_id
    assert binding.program_id == harness.programs[0].program_id
    assert binding.attempt_custody == attempt
    assert binding.consequence_execution == consequence
    assert (
        harness.world.execution_receipt_from_record(
            binding.consequence_execution.as_record()
        )
        == consequence
    )
    harness.closure.verify_binding(binding)
    assert harness.closure.status()["retained_pcm_bytes"] == 0
    encoded = harness.closure.snapshot_encoded()
    assert b"pcm" not in encoded.lower()
    assert b"exemplar" not in encoded.lower()
    assert b"transcript" not in encoded.lower()

    changed = next(
        value for value in committed if value.undo.changed
    )
    harness.closure.rollback_committed(changed.undo)
    assert harness.closure.snapshot_encoded() == empty
    harness.closure.commit_prepared(
        harness.closure.prepare(attempt, consequence)
    )
    encoded = harness.closure.snapshot_encoded()
    mosaic = harness.admit_consequence(mosaic, consequence)

    cold = ArticulatoryConsequenceClosureOwner.restore_encoded(
        authority_key=CLOSURE_KEY,
        profile=harness.closure_profile,
        encoded=encoded,
        fresh_custody_authority=harness.fresh,
        thing_owner=harness.things,
        articulatory_owner=harness.articulatory,
        world_authority=harness.world,
        companion_vocal_authority=harness.companion_vocal,
    )
    assert cold.snapshot_encoded() == encoded
    assert cold.bindings == harness.closure.bindings

    foreign = _Harness(
        world_key=b"consequence-cold-cross-world-key"
    )
    with pytest.raises(ValueError):
        ArticulatoryConsequenceClosureOwner.restore_encoded(
            authority_key=CLOSURE_KEY,
            profile=harness.closure_profile,
            encoded=encoded,
            fresh_custody_authority=foreign.fresh,
            thing_owner=harness.things,
            articulatory_owner=foreign.articulatory,
            world_authority=foreign.world,
            companion_vocal_authority=foreign.companion_vocal,
        )
    with pytest.raises(
        ValueError,
        match="dependencies changed owners",
    ):
        ArticulatoryConsequenceClosureOwner(
            authority_key=CLOSURE_KEY,
            profile=harness.closure_profile,
            fresh_custody_authority=harness.fresh,
            thing_owner=harness.things,
            articulatory_owner=foreign.articulatory,
            world_authority=harness.world,
            companion_vocal_authority=harness.companion_vocal,
        )

    mosaic, conflicting_attempt, _synthesis = harness.attempt(
        mosaic,
        program_id=harness.programs[1].program_id,
        name="conflicting-attempt",
    )
    conflicting_consequence = harness.companion_action(
        causal_intent_receipt_sha256=(
            conflicting_attempt.authority_receipt_sha256
        )
    )
    retained = harness.closure.snapshot_encoded()
    with pytest.raises(
        ValueError,
        match="conflicting articulatory programs",
    ):
        harness.closure.prepare(
            conflicting_attempt,
            conflicting_consequence,
        )
    assert harness.closure.snapshot_encoded() == retained
    _assert_no_persistence_failure(capfd)


def test_injected_install_failure_restores_exact_bytes(
    monkeypatch,
    capfd,
) -> None:
    harness = _Harness(
        world_key=b"consequence-install-failure-direct-world-key"
    )
    mosaic = harness.start_first_thing()
    mosaic, attempt, _synthesis = harness.attempt(
        mosaic,
        program_id=harness.programs[0].program_id,
        name="install-failure-attempt",
    )
    consequence = harness.companion_action(
        causal_intent_receipt_sha256=(
            attempt.authority_receipt_sha256
        )
    )
    prepared = harness.closure.prepare(attempt, consequence)
    before = harness.closure.snapshot_encoded()
    original = harness.closure._install_prepared

    def fail_after_install(candidate):
        original(candidate)
        raise RuntimeError("injected closure install failure")

    monkeypatch.setattr(
        harness.closure,
        "_install_prepared",
        fail_after_install,
    )
    with pytest.raises(
        RuntimeError,
        match="injected closure install failure",
    ):
        harness.closure.commit_prepared(prepared)
    assert harness.closure.snapshot_encoded() == before
    assert harness.closure.bindings == ()
    _assert_no_persistence_failure(capfd)


def test_unrelated_valid_consequence_rejects_without_mutation(
    capfd,
) -> None:
    harness = _Harness(
        world_key=b"consequence-unrelated-direct-world-key"
    )
    mosaic = harness.start_first_thing()
    _mosaic, attempt, _synthesis = harness.attempt(
        mosaic,
        program_id=harness.programs[0].program_id,
        name="unrelated-attempt",
    )
    unrelated = harness.companion_action(
        causal_intent_receipt_sha256=(
            _intent("unrelated-valid-physical-intent")
        )
    )
    before = harness.closure.snapshot_encoded()
    with pytest.raises(
        ValueError,
        match="not the immediate physical result",
    ):
        harness.closure.prepare(attempt, unrelated)
    assert harness.closure.snapshot_encoded() == before
    assert harness.closure.bindings == ()
    _assert_no_persistence_failure(capfd)


def test_adjacency_cross_world_and_tamper_reject(capfd) -> None:
    first = _Harness(
        world_key=b"consequence-adjacency-direct-world-key"
    )
    mosaic = first.start_first_thing()
    _mosaic, attempt, _synthesis = first.attempt(
        mosaic,
        program_id=first.programs[0].program_id,
        name="adjacency-attempt",
    )
    valid = first.companion_action(
        causal_intent_receipt_sha256=(
            attempt.authority_receipt_sha256
        )
    )
    with pytest.raises(ValueError):
        first.closure.prepare(
            attempt,
            replace(valid, port_id=PORT_ID),
        )
    first.companion_action(
        causal_intent_receipt_sha256=_intent("later-world-edge")
    )
    with pytest.raises(
        ValueError,
        match="no longer the immediate world edge",
    ):
        first.closure.prepare(attempt, valid)
    assert first.closure.bindings == ()

    foreign = _Harness(
        world_key=b"consequence-foreign-direct-world-key"
    )
    foreign_mosaic = foreign.start_first_thing()
    _foreign_mosaic, _foreign_attempt, _synthesis = foreign.attempt(
        foreign_mosaic,
        program_id=foreign.programs[0].program_id,
        name="foreign-attempt",
    )
    foreign_consequence = foreign.companion_action(
        causal_intent_receipt_sha256=(
            attempt.authority_receipt_sha256
        )
    )
    with pytest.raises(ValueError):
        first.closure.prepare(attempt, foreign_consequence)
    assert first.closure.bindings == ()
    _assert_no_persistence_failure(capfd)


def test_capacity_rejects_second_thing_without_mutation(
    capfd,
) -> None:
    harness = _Harness(
        world_key=b"consequence-capacity-direct-world-key",
        max_bindings=1,
    )
    first = harness.start_first_thing()
    first, first_attempt, _synthesis = harness.attempt(
        first,
        program_id=harness.programs[0].program_id,
        name="capacity-first-attempt",
    )
    first_consequence = harness.companion_action(
        causal_intent_receipt_sha256=(
            first_attempt.authority_receipt_sha256
        )
    )
    capacity_profile = ArticulatoryConsequenceClosureProfile.create(
        profile_id="consequence-full-receipt-capacity",
        max_bindings=1,
        max_state_bytes=4 * 1024,
    )
    capacity_owner = ArticulatoryConsequenceClosureOwner(
        authority_key=CLOSURE_KEY,
        profile=capacity_profile,
        fresh_custody_authority=harness.fresh,
        thing_owner=harness.things,
        articulatory_owner=harness.articulatory,
        world_authority=harness.world,
        companion_vocal_authority=harness.companion_vocal,
    )
    capacity_empty = capacity_owner.snapshot_encoded()
    with pytest.raises(
        RuntimeError,
        match="state capacity exhausted",
    ):
        capacity_owner.prepare(first_attempt, first_consequence)
    assert capacity_owner.snapshot_encoded() == capacity_empty
    harness.closure.commit_prepared(
        harness.closure.prepare(first_attempt, first_consequence)
    )
    harness.admit_consequence(first, first_consequence)

    second = harness.start_second_thing()
    _second, second_attempt, _synthesis = harness.attempt(
        second,
        program_id=harness.programs[1].program_id,
        name="capacity-second-attempt",
    )
    second_consequence = harness.companion_action(
        causal_intent_receipt_sha256=(
            second_attempt.authority_receipt_sha256
        )
    )
    retained = harness.closure.snapshot_encoded()
    with pytest.raises(
        RuntimeError,
        match="binding capacity exhausted",
    ):
        harness.closure.prepare(
            second_attempt,
            second_consequence,
        )
    assert harness.closure.snapshot_encoded() == retained
    assert len(harness.closure.bindings) == 1
    _assert_no_persistence_failure(capfd)


def _run_two_thing_world(
    *,
    selected_by_slot: dict[str, int],
):
    harness = _Harness(
        world_key=b"consequence-swap-identical-direct-world-key"
    )
    trace = []
    thing_ids = {}
    mosaic = harness.start_first_thing()
    for slot in ("A", "B"):
        if slot == "B":
            mosaic = harness.start_second_thing()
        thing_ids[slot] = mosaic.thing_id
        for program_index, program in enumerate(harness.programs):
            mosaic, attempt, synthesis = harness.attempt(
                mosaic,
                program_id=program.program_id,
                name=f"identical-{slot}-{program_index}-attempt",
            )
            selected = selected_by_slot[slot] == program_index
            consequence = harness.companion_action(
                causal_intent_receipt_sha256=(
                    attempt.authority_receipt_sha256
                    if selected
                    else _intent(
                        f"identical-{slot}-{program_index}-unlinked"
                    )
                )
            )
            trace.append((
                slot,
                program_index,
                program.program_id,
                str(synthesis.receipt.source_time_start),
                str(synthesis.receipt.source_time_end),
                consequence.command_sha256,
                consequence.before.state_sha256,
                consequence.after.state_sha256,
            ))
            if selected:
                harness.closure.commit_prepared(
                    harness.closure.prepare(attempt, consequence)
                )
            mosaic = harness.admit_consequence(
                mosaic,
                consequence,
            )
    mapped = {
        slot: next(
            binding.program_id
            for binding in harness.closure.bindings
            if binding.thing_id == thing_ids[slot]
        )
        for slot in ("A", "B")
    }
    return harness, tuple(
        program.program_id for program in harness.programs
    ), trace, mapped


def test_two_world_consequence_swap_swaps_authoritative_mappings(
    capfd,
) -> None:
    _first, programs, first_trace, first_mapping = (
        _run_two_thing_world(
            selected_by_slot={"A": 0, "B": 1},
        )
    )
    _second, second_programs, second_trace, second_mapping = (
        _run_two_thing_world(
            selected_by_slot={"A": 1, "B": 0},
        )
    )
    assert second_programs == programs
    assert second_trace == first_trace
    assert first_mapping == {
        "A": programs[0],
        "B": programs[1],
    }
    assert second_mapping == {
        "A": programs[1],
        "B": programs[0],
    }
    _assert_no_persistence_failure(capfd)


def test_companion_vocal_episode_closes_cold_and_rejects_false_lineage(
    capfd,
) -> None:
    harness = _Harness(
        world_key=b"consequence-vocal-episode-world-key"
    )
    mosaic = harness.start_first_thing()
    _mosaic, attempt, _synthesis = harness.attempt(
        mosaic,
        program_id=harness.programs[0].program_id,
        name="vocal-episode-attempt",
    )
    pcm = _vocal_pcm()
    episode_prepared = harness.companion_vocal.prepare_episode(
        pcm_s16le=pcm,
        causal_parent_receipt_sha256=(
            attempt.authority_receipt_sha256
        ),
    )
    intent = episode_prepared.intent_receipt
    consequence = (
        episode_prepared.prediction_blocks[0].execution_receipt
    )
    harness.companion_vocal.commit_episode(episode_prepared)

    for changed_intent in (
        replace(
            intent,
            causal_parent_receipt_sha256=_intent("wrong-parent"),
        ),
        replace(intent, block_count=2),
    ):
        with pytest.raises(ValueError):
            harness.closure.prepare(
                attempt,
                consequence,
                companion_episode_intent=changed_intent,
            )
    assert harness.closure.bindings == ()

    foreign_companion = W1CompanionVocalExperienceAuthority(
        authority_key=b"foreign-companion-vocal-authority-key",
        world_authority=harness.world,
        physical_authority=harness.physical,
    )
    foreign_closure = ArticulatoryConsequenceClosureOwner(
        authority_key=CLOSURE_KEY,
        profile=harness.closure_profile,
        fresh_custody_authority=harness.fresh,
        thing_owner=harness.things,
        articulatory_owner=harness.articulatory,
        world_authority=harness.world,
        companion_vocal_authority=foreign_companion,
    )
    with pytest.raises(ValueError, match="intent authority changed"):
        foreign_closure.prepare(
            attempt,
            consequence,
            companion_episode_intent=intent,
        )

    committed = harness.closure.commit_prepared(
        harness.closure.prepare(
            attempt,
            consequence,
            companion_episode_intent=intent,
        )
    )
    binding = committed.binding
    assert binding.causal_linkage == "companion_episode_intent"
    assert binding.companion_episode_intent == intent
    assert (
        binding.consequence_execution.causal_intent_receipt_sha256
        == intent.authority_receipt_sha256
    )
    harness.closure.verify_binding(binding)
    encoded = harness.closure.snapshot_encoded()
    assert pcm not in encoded
    assert harness.closure.status()["retained_pcm_bytes"] == 0

    cold = ArticulatoryConsequenceClosureOwner.restore_encoded(
        authority_key=CLOSURE_KEY,
        profile=harness.closure_profile,
        encoded=encoded,
        fresh_custody_authority=harness.fresh,
        thing_owner=harness.things,
        articulatory_owner=harness.articulatory,
        world_authority=harness.world,
        companion_vocal_authority=harness.companion_vocal,
    )
    assert cold.snapshot_encoded() == encoded
    assert cold.bindings == harness.closure.bindings
    with pytest.raises(ValueError, match="intent authority changed"):
        ArticulatoryConsequenceClosureOwner.restore_encoded(
            authority_key=CLOSURE_KEY,
            profile=harness.closure_profile,
            encoded=encoded,
            fresh_custody_authority=harness.fresh,
            thing_owner=harness.things,
            articulatory_owner=harness.articulatory,
            world_authority=harness.world,
            companion_vocal_authority=foreign_companion,
        )

    harness.companion_action(
        causal_intent_receipt_sha256=_intent("after-vocal-edge")
    )
    with pytest.raises(
        ValueError,
        match="no longer the immediate world edge",
    ):
        harness.closure.prepare(
            attempt,
            consequence,
            companion_episode_intent=intent,
        )
    _assert_no_persistence_failure(capfd)


def test_authenticated_v1_direct_state_migrates_without_invented_binding(
    capfd,
) -> None:
    harness = _Harness(
        world_key=b"consequence-v1-migration-world-key"
    )
    mosaic = harness.start_first_thing()
    mosaic, attempt, _synthesis = harness.attempt(
        mosaic,
        program_id=harness.programs[0].program_id,
        name="legacy-direct-attempt",
    )
    consequence = harness.companion_action(
        causal_intent_receipt_sha256=(
            attempt.authority_receipt_sha256
        )
    )
    binding = harness.closure.commit_prepared(
        harness.closure.prepare(attempt, consequence)
    ).binding
    legacy_payload = binding.payload()
    legacy_payload.pop("causal_linkage")
    legacy_payload.pop("companion_episode_intent")
    legacy_payload["schema"] = (
        closure_module._LEGACY_BINDING_SCHEMA
    )
    legacy_binding_hmac = closure_module._sign(
        harness.closure._legacy_binding_key,
        closure_module._LEGACY_BINDING_DOMAIN,
        legacy_payload,
    )
    legacy_binding = {
        **legacy_payload,
        "authority_hmac_sha256": legacy_binding_hmac,
        "authority_receipt_sha256": closure_module._digest({
            "authority_hmac_sha256": legacy_binding_hmac,
            "payload": legacy_payload,
        }),
    }
    legacy_body = {
        "bindings": [legacy_binding],
        "profile": harness.closure_profile.record(),
        "schema": closure_module._LEGACY_STATE_SCHEMA,
    }
    legacy_envelope = {
        "body": legacy_body,
        "schema": closure_module._LEGACY_ENVELOPE_SCHEMA,
        "state_hmac_sha256": closure_module._sign(
            harness.closure._legacy_state_key,
            closure_module._LEGACY_STATE_DOMAIN,
            legacy_body,
        ),
    }
    legacy_encoded = closure_module._canonical(legacy_envelope)
    harness.admit_consequence(mosaic, consequence)
    migrated = ArticulatoryConsequenceClosureOwner.restore_encoded(
        authority_key=CLOSURE_KEY,
        profile=harness.closure_profile,
        encoded=legacy_encoded,
        fresh_custody_authority=harness.fresh,
        thing_owner=harness.things,
        articulatory_owner=harness.articulatory,
        world_authority=harness.world,
        companion_vocal_authority=harness.companion_vocal,
    )
    assert len(migrated.bindings) == 1
    assert migrated.bindings[0].companion_episode_intent is None
    assert migrated.bindings[0].causal_linkage == "direct_attempt"
    assert migrated.snapshot_encoded() != legacy_encoded
    assert (
        json.loads(migrated.snapshot_encoded())["schema"]
        == closure_module.ENVELOPE_SCHEMA
    )

    tampered = json.loads(legacy_encoded)
    tampered["body"]["bindings"][0]["program_id"] = "tampered"
    tampered_encoded = closure_module._canonical(tampered)
    with pytest.raises(ValueError, match="snapshot HMAC changed"):
        ArticulatoryConsequenceClosureOwner.restore_encoded(
            authority_key=CLOSURE_KEY,
            profile=harness.closure_profile,
            encoded=tampered_encoded,
            fresh_custody_authority=harness.fresh,
            thing_owner=harness.things,
            articulatory_owner=harness.articulatory,
            world_authority=harness.world,
            companion_vocal_authority=harness.companion_vocal,
        )
    _assert_no_persistence_failure(capfd)


def test_public_prepare_accepts_only_attempt_and_consequence() -> None:
    parameters = tuple(
        inspect.signature(
            ArticulatoryConsequenceClosureOwner.prepare
        ).parameters
    )
    assert parameters == (
        "self",
        "attempt_custody",
        "consequence",
        "companion_episode_intent",
    )
