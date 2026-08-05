from __future__ import annotations

from dataclasses import replace

import pytest

from dsf_ai_service.glew_runtime.global_uf import DSF_FIELD_ORDER
from dsf_ai_service.glew_runtime.sensory_full_field_boundary import (
    SenseBoundaryState,
)
from dsf_ai_service.substrate.articulatory_consequence_closure import (
    ArticulatoryConsequenceClosureOwner,
)
from dsf_ai_service.substrate.articulatory_self_vocal_motor import (
    ArticulatorySelfVocalMotorOwner,
)
from dsf_ai_service.substrate.causal_thing_mosaic_persistence import (
    restore_causal_thing_mosaic_owner,
)
from dsf_ai_service.substrate.causal_thing_reciprocal_mosaic import (
    CausalThingReciprocalMosaicOwner,
)
from dsf_ai_service.substrate.consequence_evoked_articulatory_response import (
    CONSEQUENCE_EVOKED_RESPONSE_CONSUMER_ID,
    CommittedConsequenceEvokedArticulatoryAct,
    ConsequenceEvokedArticulatoryResponseAuthority,
)
from dsf_ai_service.substrate.custodied_thing_encounter import (
    THING_MOSAIC_CONSUMER_ID,
)
from dsf_ai_service.substrate.embodiment_world import (
    MoveCommand,
    PickCommand,
    PlaceCommand,
    PoseMM,
    PositionMM,
)
from dsf_ai_service.substrate.fresh_articulatory_self_acoustic_custody import (
    FreshArticulatorySelfAcousticCustodyAuthority,
)
from dsf_ai_service.substrate.settled_experience_custody import (
    SettledExperienceCustodyAuthority,
    SettledExperienceCustodyProfile,
)
from dsf_ai_service.substrate.w1_self_acoustic_propagation import (
    W1ArticulatorySelfAcousticCommitUndo,
)
from tests.test_articulatory_consequence_closure import (
    ACOUSTIC_KEY,
    ARTICULATORY_KEY,
    CLOSURE_KEY,
    EVIDENCE_KEY,
    FRESH_KEY,
    THING_KEY,
    _Harness,
    _intent,
)


RESPONSE_KEY = b"consequence-evoked-response-authority-key"
WORLD_KEY = b"consequence-evoked-identical-world-authority-key"


@pytest.fixture(autouse=True)
def _isolated_state_dir(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("STATE_DIR", str(tmp_path / "isolated-state"))


def _start_thing(harness: _Harness, *, slot: str):
    if slot == "A":
        picked = harness.self_action(
            PickCommand(
                "W1-object-1",
                duration_microseconds=100_000,
            ),
            "response-pick-first-thing",
        )
    else:
        harness.self_action(
            PlaceCommand(
                "W1-object-1",
                PositionMM(1_000, 1_700, 0),
                duration_microseconds=100_000,
            ),
            "response-place-first-thing",
        )
        harness.self_action(
            MoveCommand(
                PoseMM(PositionMM(2_000, 1_000, 0), 0),
                duration_microseconds=100_000,
            ),
            "response-move-to-second-thing",
        )
        picked = harness.self_action(
            PickCommand(
                "W1-object-2",
                duration_microseconds=100_000,
            ),
            "response-pick-second-thing",
        )
    mount = harness.physical.mount_action_outcome(picked)
    custody = harness._settled(
        mount,
        picked,
        self_acoustic=False,
    )
    capability = custody.issue_child(THING_MOSAIC_CONSUMER_ID)
    partition = harness.partitions.partition_from_custody(
        custody_authority=custody,
        capability=capability,
        prior=None,
    )
    return harness.things.admit(partition), mount.causal_settlement


def _trained_world(
    *,
    selected_by_slot: dict[str, int],
    closed_slots: frozenset[str] = frozenset({"A", "B"}),
):
    harness = _Harness(world_key=WORLD_KEY)
    cues = {}
    thing_ids = {}
    for slot in ("A", "B"):
        mosaic, cue = _start_thing(harness, slot=slot)
        cues[slot] = cue
        thing_ids[slot] = mosaic.thing_id
        for program_index, program in enumerate(harness.programs):
            mosaic, attempt, _synthesis = harness.attempt(
                mosaic,
                program_id=program.program_id,
                name=f"response-{slot}-{program_index}-attempt",
            )
            selected = selected_by_slot[slot] == program_index
            consequence = harness.companion_action(
                causal_intent_receipt_sha256=(
                    attempt.authority_receipt_sha256
                    if selected and slot in closed_slots
                    else _intent(
                        f"response-{slot}-{program_index}-unclosed"
                    )
                )
            )
            if selected and slot in closed_slots:
                harness.closure.commit_prepared(
                    harness.closure.prepare(attempt, consequence)
                )
            mosaic = harness.admit_consequence(
                mosaic,
                consequence,
            )
    return harness, cues, thing_ids


def _cold_restore(
    source: _Harness,
):
    cold = _Harness(world_key=source.world_key)
    cold.world.restore_encoded(source.world.encoded_snapshot())
    cold.articulatory = ArticulatorySelfVocalMotorOwner.restore_encoded(
        authority_key=ARTICULATORY_KEY,
        encoded=source.articulatory.snapshot_encoded(),
    )
    cold.things = restore_causal_thing_mosaic_owner(
        authority_key=THING_KEY,
        encoded=source.things.snapshot_encoded(),
        partition_authority=cold.partitions,
    )
    cold.fresh = FreshArticulatorySelfAcousticCustodyAuthority(
        authority_key=FRESH_KEY,
        profile=cold.fresh_profile,
        articulatory_owner=cold.articulatory,
        world_authority=cold.world,
        acoustic_authority=cold.acoustic,
    )
    cold.closure = ArticulatoryConsequenceClosureOwner.restore_encoded(
        authority_key=CLOSURE_KEY,
        profile=cold.closure_profile,
        encoded=source.closure.snapshot_encoded(),
        fresh_custody_authority=cold.fresh,
        thing_owner=cold.things,
        articulatory_owner=cold.articulatory,
        world_authority=cold.world,
        companion_vocal_authority=cold.companion_vocal,
    )
    cold.reciprocal = CausalThingReciprocalMosaicOwner(
        authority_key=THING_KEY,
        thing_owner=cold.things,
        max_classes=4,
        max_roots_per_class=4_096,
        max_cue_roots=1_024,
    )
    cold.response = ConsequenceEvokedArticulatoryResponseAuthority(
        authority_key=RESPONSE_KEY,
        reciprocal_owner=cold.reciprocal,
        consequence_owner=cold.closure,
        articulatory_owner=cold.articulatory,
        acoustic_authority=cold.acoustic,
        world_authority=cold.world,
    )
    return cold


def _cue_custody(system, *, execution=None):
    observation = system.world.observation_snapshot()
    mount = (
        system.physical.mount_authenticated_observation(
            observation,
            commit=True,
        )
        if execution is None
        else system.physical.mount_action_outcome(execution)
    )
    authority = SettledExperienceCustodyAuthority(
        authority_key=system._next_custody_key(),
        w1_physical_authority_key=EVIDENCE_KEY,
        world_authority_key=system.world_key,
        profile=SettledExperienceCustodyProfile.create(
            profile_id=(
                "consequence-response-cue-"
                f"{observation.revision}-"
                f"{system._custody_ordinal}"
            ),
            max_children=2,
            max_snapshot_bytes=128 * 1024 * 1024,
        ),
    )
    authority.admit(
        mount,
        execution,
        world_observation=(
            observation if execution is None else None
        ),
    )
    capability = authority.issue_child(
        CONSEQUENCE_EVOKED_RESPONSE_CONSUMER_ID
    )
    return authority, capability, mount.causal_settlement


def _respond(system, cue):
    authority, capability, _settlement = cue
    return system.response.respond(
        custody_authority=authority,
        custody_capability=capability,
    )


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


def _published_state(system) -> dict[str, object]:
    return {
        "articulatory": system.articulatory.snapshot_encoded(),
        "causal": system.acoustic._causal.status(),
        "closure": system.closure.snapshot_encoded(),
        "l5": system.acoustic._l5.status(),
        "motif": system.acoustic._motif.snapshot_encoded(),
        "world": system.world.encoded_snapshot(),
        "world_receipts": system.world.recent_applied_receipts(),
    }


def _prepared_state(system) -> dict[str, int]:
    return {
        "causal_atomic": (
            system.acoustic._causal.status()["atomic_sequence"]
        ),
        "l5_atomic": system.acoustic._l5.status()["atomic_sequence"],
        "motif": system.acoustic._motif.status()[
            "prepared_binaural_observation_count"
        ],
        "world": system.world.status()["prepared_action_execution"],
    }


def _forbid_legacy_paths(monkeypatch, system) -> None:
    assert not hasattr(system.acoustic, "_motor")
    assert not hasattr(system.acoustic, "propagate")
    assert not hasattr(system.acoustic, "propagate_articulatory")
    assert not hasattr(system.articulatory, "bind_thing_program")
    assert not hasattr(
        system.articulatory,
        "verify_thing_program_binding",
    )


def _capture_commits(monkeypatch, system):
    captured = []
    commitments = []
    original_commit = system.acoustic.commit_prepared_articulatory
    original_view = system.acoustic.prepared_articulatory_commitment

    def view(prepared):
        result = original_view(prepared)
        assert not hasattr(result, "pcm_s16le")
        assert not hasattr(result, "mount")
        assert not hasattr(result, "receipt")
        result.verify(ACOUSTIC_KEY)
        commitments.append(result)
        return result

    def commit(prepared):
        result = original_commit(prepared)
        captured.append(result)
        return result

    monkeypatch.setattr(
        system.acoustic,
        "prepared_articulatory_commitment",
        view,
    )
    monkeypatch.setattr(
        system.acoustic,
        "commit_prepared_articulatory",
        commit,
    )
    return captured, commitments


def test_cold_restored_swapped_consequences_swap_fresh_program_and_pcm(
    monkeypatch,
) -> None:
    first_source, _first_cues, first_things = _trained_world(
        selected_by_slot={"A": 0, "B": 1}
    )
    second_source, _second_cues, second_things = _trained_world(
        selected_by_slot={"A": 1, "B": 0}
    )
    assert first_things == second_things

    first = _cold_restore(first_source)
    second = _cold_restore(second_source)
    assert (
        first.closure.snapshot_encoded()
        == first_source.closure.snapshot_encoded()
    )
    assert (
        second.closure.snapshot_encoded()
        == second_source.closure.snapshot_encoded()
    )
    _forbid_legacy_paths(monkeypatch, first)
    _forbid_legacy_paths(monkeypatch, second)
    first_captured, first_commitments = _capture_commits(
        monkeypatch,
        first,
    )
    second_captured, second_commitments = _capture_commits(
        monkeypatch,
        second,
    )

    first_act = _respond(first, _cue_custody(first))
    second_act = _respond(second, _cue_custody(second))
    assert all(
        isinstance(
            act,
            CommittedConsequenceEvokedArticulatoryAct,
        )
        for act in (first_act, second_act)
    )

    first_selected = next(
        binding.program_id
        for binding in first_source.closure.bindings
        if binding.thing_id == first_things["B"]
    )
    second_selected = next(
        binding.program_id
        for binding in second_source.closure.bindings
        if binding.thing_id == second_things["B"]
    )
    assert first_act.response.program_id == first_selected
    assert second_act.response.program_id == second_selected
    assert first_act.pcm_s16le != second_act.pcm_s16le

    for system, act, captures, commitments in (
        (first, first_act, first_captured, first_commitments),
        (second, second_act, second_captured, second_commitments),
    ):
        assert len(captures) == 1
        assert len(commitments) == 2
        assert commitments[0] == commitments[1]
        emission, mount, undo = captures[0]
        assert isinstance(
            undo,
            W1ArticulatorySelfAcousticCommitUndo,
        )
        commitment = commitments[0]
        response = act.response
        system.response.verify_response(response)
        system.response.verify_committed_act(act)
        assert act.pcm_s16le == emission.pcm_s16le
        assert response.state == "executed"
        assert response.synthesis_pcm_sha256 == (
            emission.emission_receipt.pcm_sha256
        )
        assert response.emission_receipt_sha256 == (
            emission.emission_receipt.authority_receipt_sha256
        )
        assert response.self_acoustic_receipt_sha256 == (
            mount.receipt.authority_receipt_sha256
        )
        assert (
            response.prepared_self_acoustic_commitment_receipt_sha256
            == commitment.authority_receipt_sha256
        )
        mount.verify(ACOUSTIC_KEY)
        assert all(
            tuple(name for name, _value in field_tuple.fields)
            == DSF_FIELD_ORDER
            for field_tuple in _all_field_tuples(mount)
        )
        assert not hasattr(response, "synthesis")
        assert not hasattr(response, "self_acoustic_mount")
        assert not hasattr(response, "pcm_s16le")
        assert not hasattr(response, "label")
        assert not hasattr(response, "transcript")
        assert not hasattr(response, "score")
        assert not hasattr(act, "snapshot_encoded")
        assert not hasattr(act, "record")
        assert system.response.status()["retained_pcm_bytes"] == 0
        assert system.response.status()["retained_replay_receipts"] == 0


def test_unknown_unclosed_and_ambiguous_sight_are_exactly_silent(
    monkeypatch,
) -> None:
    source, historical_cues, thing_ids = _trained_world(
        selected_by_slot={"A": 0, "B": 1},
        closed_slots=frozenset({"A"}),
    )
    system = _cold_restore(source)
    _forbid_legacy_paths(monkeypatch, system)

    unbound_cue = _cue_custody(system)
    before_unbound = _published_state(system)
    unbound = _respond(system, unbound_cue)
    assert unbound.state == "unbound"
    assert unbound.thing_ids == (thing_ids["B"],)
    assert unbound.synthesis_pcm_sha256 is None
    assert unbound.self_acoustic_receipt_sha256 is None
    assert _published_state(system) == before_unbound
    retry = _respond(system, unbound_cue)
    assert retry.authority_receipt_sha256 == unbound.authority_receipt_sha256

    moved = system.self_action(
        MoveCommand(
            PoseMM(PositionMM(1_850, 1_250, 0), 45_000),
            duration_microseconds=100_000,
        ),
        "response-unknown-sight-cue",
    )
    unknown_cue = _cue_custody(system, execution=moved)
    before_unknown = _published_state(system)
    unknown = _respond(system, unknown_cue)
    assert unknown.state == "unresolved"
    assert unknown.thing_ids == ()
    assert unknown.synthesis_pcm_sha256 is None
    assert unknown.self_acoustic_receipt_sha256 is None
    assert _published_state(system) == before_unknown

    unique = system.reciprocal.evoke(
        historical_cues["A"],
        cue_senses=("sight",),
    )
    injected_ambiguous = replace(
        unique,
        state="ambiguous",
        thing_ids=tuple(sorted(thing_ids.values())),
        candidate=None,
        evoked_full_field_roots=(),
    )
    with monkeypatch.context() as patch:
        patch.setattr(
            system.reciprocal,
            "evoke",
            lambda *_args, **_kwargs: injected_ambiguous,
        )
        patch.setattr(
            system.reciprocal,
            "verify_evocation",
            lambda _value: None,
        )
        before_ambiguous = _published_state(system)
        ambiguous = _respond(system, unknown_cue)
    assert ambiguous.state == "ambiguous"
    assert ambiguous.synthesis_pcm_sha256 is None
    assert ambiguous.self_acoustic_receipt_sha256 is None
    assert _published_state(system) == before_ambiguous


@pytest.mark.parametrize(
    "boundary",
    ("response", "w1", "world"),
)
def test_response_w1_and_world_failures_restore_exact_state(
    monkeypatch,
    boundary,
) -> None:
    source, _cues, _thing_ids = _trained_world(
        selected_by_slot={"A": 0, "B": 1}
    )
    system = _cold_restore(source)
    cue = _cue_custody(system)
    before = _published_state(system)

    def fail(*_args, **_kwargs):
        raise RuntimeError(f"injected {boundary} failure")

    with monkeypatch.context() as patch:
        if boundary == "response":
            patch.setattr(system.response, "_seal", fail)
        elif boundary == "w1":
            patch.setattr(system.acoustic, "_finish_mount", fail)
        else:
            patch.setattr(
                system.world,
                "commit_prepared_action",
                fail,
            )
        with pytest.raises(
            RuntimeError,
            match=f"injected {boundary} failure",
        ):
            _respond(system, cue)

    assert _published_state(system) == before
    assert all(value == 0 for value in _prepared_state(system).values())
    retry = _respond(system, cue)
    assert isinstance(retry, CommittedConsequenceEvokedArticulatoryAct)


def test_constructor_rejects_crossed_exact_owners() -> None:
    source, _cues, _thing_ids = _trained_world(
        selected_by_slot={"A": 0, "B": 1}
    )
    first = _cold_restore(source)
    second = _cold_restore(source)
    exact = {
        "authority_key": RESPONSE_KEY,
        "reciprocal_owner": first.reciprocal,
        "consequence_owner": first.closure,
        "articulatory_owner": first.articulatory,
        "acoustic_authority": first.acoustic,
        "world_authority": first.world,
    }
    for replacement in (
        {"reciprocal_owner": second.reciprocal},
        {"consequence_owner": second.closure},
        {"articulatory_owner": second.articulatory},
        {"world_authority": second.world},
        {"acoustic_authority": second.acoustic},
    ):
        with pytest.raises(ValueError, match="crossed"):
            ConsequenceEvokedArticulatoryResponseAuthority(
                **(exact | replacement)
            )


def test_success_makes_exact_cue_occurrence_stale() -> None:
    source, _cues, _thing_ids = _trained_world(
        selected_by_slot={"A": 0, "B": 1}
    )
    system = _cold_restore(source)
    cue = _cue_custody(system)

    first = _respond(system, cue)
    assert isinstance(first, CommittedConsequenceEvokedArticulatoryAct)
    after_first_world = _published_state(system)

    with pytest.raises(ValueError, match="not current"):
        _respond(system, cue)

    assert _published_state(system) == after_first_world
    assert system.response.status()["retained_replay_receipts"] == 0
    assert all(value == 0 for value in _prepared_state(system).values())


def test_unrelated_world_change_makes_cue_stale_without_response() -> None:
    source, _cues, _thing_ids = _trained_world(
        selected_by_slot={"A": 0, "B": 1}
    )
    system = _cold_restore(source)
    cue = _cue_custody(system)
    system.companion_action(
        causal_intent_receipt_sha256=_intent(
            "response-unrelated-world-change"
        )
    )
    changed = _published_state(system)

    with pytest.raises(ValueError, match="not current"):
        _respond(system, cue)

    assert _published_state(system) == changed
    assert system.response.status()["retained_replay_receipts"] == 0


def test_cold_authority_accepts_new_current_cue_without_replay_state() -> None:
    source, _cues, _thing_ids = _trained_world(
        selected_by_slot={"A": 0, "B": 1}
    )
    live = _cold_restore(source)
    old_cue = _cue_custody(live)
    _respond(live, old_cue)

    cold = _cold_restore(live)
    assert cold.response.status()["stateful"] is False
    assert cold.response.status()["retained_replay_receipts"] == 0
    with pytest.raises(ValueError, match="not current"):
        _respond(cold, old_cue)

    fresh = _respond(cold, _cue_custody(cold))
    assert isinstance(fresh, CommittedConsequenceEvokedArticulatoryAct)


def test_crossed_custody_authority_and_capability_are_rejected() -> None:
    source, _cues, _thing_ids = _trained_world(
        selected_by_slot={"A": 0, "B": 1}
    )
    system = _cold_restore(source)
    first_authority, _first_capability, _ = _cue_custody(system)
    _second_authority, second_capability, _ = _cue_custody(system)
    wrong_consumer = first_authority.issue_child(
        "not-consequence-response"
    )
    before = _published_state(system)

    with pytest.raises(ValueError, match="dedicated capability"):
        system.response.respond(
            custody_authority=first_authority,
            custody_capability=wrong_consumer,
        )
    with pytest.raises(ValueError):
        system.response.respond(
            custody_authority=first_authority,
            custody_capability=second_capability,
        )

    assert _published_state(system) == before


def test_forged_prepared_mount_commitment_is_rejected_before_commit(
    monkeypatch,
) -> None:
    source, _cues, _thing_ids = _trained_world(
        selected_by_slot={"A": 0, "B": 1}
    )
    system = _cold_restore(source)
    cue = _cue_custody(system)
    before = _published_state(system)
    original = system.acoustic.prepared_articulatory_commitment

    def forged(prepared):
        return replace(
            original(prepared),
            prospective_mount_receipt_sha256="f" * 64,
        )

    monkeypatch.setattr(
        system.acoustic,
        "prepared_articulatory_commitment",
        forged,
    )
    with pytest.raises(ValueError):
        _respond(system, cue)

    assert _published_state(system) == before
    assert all(value == 0 for value in _prepared_state(system).values())
