from __future__ import annotations

import base64
import ast
import copy
import hashlib
import hmac
import inspect
import json
import math
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from fractions import Fraction

import pytest

import dsf_ai_service.substrate.full_field_prediction as prediction_module
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
from dsf_ai_service.substrate.causal_action_cycle import (
    ActionCommand,
    CausalActionCycle,
)
from dsf_ai_service.substrate.embodiment_world import (
    PORT_ID,
    EmbodiedBody,
    EmbodiedObject,
    EmbodimentPort,
    EmbodimentWorldAuthority,
    PoseMM,
    PositionMM,
)
from dsf_ai_service.substrate.exact_causal_experience import (
    ExactCausalExperienceOwner,
)
from dsf_ai_service.substrate.full_field_prediction import (
    FullFieldPredictionAuthority,
)
from dsf_ai_service.substrate.settled_experience_custody import (
    SettledExperienceCustodyAuthority,
    SettledExperienceCustodyProfile,
)
from dsf_ai_service.substrate.w1_acoustic_emitter import (
    W1AcousticEmitterAuthority,
)
from dsf_ai_service.substrate.w1_anonymous_audiovisual_continuity import (
    W1AnonymousAudiovisualContinuityOwner,
)
from dsf_ai_service.substrate.w1_binaural_auditory_l5 import (
    W1BinauralAuditoryL5Owner,
)
from dsf_ai_service.substrate.w1_audiovisual_physical_evidence import (
    W1AudiovisualPhysicalEvidenceAuthority,
)


KEY = b"full-field-prediction-test-key-" * 2


def _sha(value: str | bytes) -> str:
    if isinstance(value, str):
        value = value.encode("utf-8")
    return hashlib.sha256(value).hexdigest()


def _substream(
    sense: PhysicalSense,
    *,
    frequency: int,
    substream_id: str = "field-0",
) -> NativeSensorySubstreamInput:
    count = 96
    return NativeSensorySubstreamInput(
        sense=sense,
        sensor_id=f"prediction-{sense.value}-sensor",
        substream_id=substream_id,
        topology_index=0,
        coordinates=(
            NativeAxisCoordinate("field-axis", f"{sense.value}-center"),
        ),
        physical_quantity=f"{sense.value}-intensity",
        physical_unit="normalized-intensity",
        source_times=tuple(Fraction(index, 512) for index in range(count)),
        normalized_signal=tuple(
            math.sin(2 * math.pi * frequency * index / 512)
            for index in range(count)
        ),
        phase_turns=tuple(Fraction(index // 12) for index in range(count)),
    )


def _settlement(
    label: str,
    *,
    sight_frequency: int = 8,
    sound_frequency: int | None = None,
    sight_observed: bool = True,
    routing_chis: tuple[int, ...] = (),
):
    observed = {}
    if sight_observed:
        observed[PhysicalSense.SIGHT] = (
            _substream(PhysicalSense.SIGHT, frequency=sight_frequency),
        )
    if sound_frequency is not None:
        observed[PhysicalSense.SOUND] = (
            _substream(PhysicalSense.SOUND, frequency=sound_frequency),
        )
    built = build_six_sense_full_field(
        assembly_id=f"prediction-{label}",
        source_time_start=Fraction(0),
        source_time_end=Fraction(96, 512),
        observed_substreams=observed,
        states={
            sense: (
                SenseBoundaryState.OBSERVED
                if sense in observed
                else SenseBoundaryState.SENSOR_UNAVAILABLE
            )
            for sense in SENSE_ORDER
        },
    )
    return ExactCausalExperienceOwner(
        on_settlement=lambda _value: None,
        log_event=lambda *_args, **_kwargs: None,
    ).settle(
        built,
        routing_chis=routing_chis,
        source_tags=(f"test-source:{label}",),
    )


def _settled_prediction_custody():
    world = EmbodimentWorldAuthority(
        authority_key=KEY,
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
            EmbodimentPort(
                "w1.external-emitter",
                "external-body",
            ),
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
        authority_key=KEY,
        world_authority=world,
        causal_owner=ExactCausalExperienceOwner(
            on_settlement=lambda _value: None,
            log_event=lambda *_args, **_kwargs: None,
        ),
        acoustic_emitter=W1AcousticEmitterAuthority(
            authority_key=KEY,
            world_authority=world,
        ),
        binaural_auditory_l5_owner=W1BinauralAuditoryL5Owner(),
        anonymous_av_continuity_owner=(
            W1AnonymousAudiovisualContinuityOwner(
                authority_key=KEY,
                physical_authority_key=KEY,
            )
        ),
    )
    observation = world.observation_snapshot()
    mount = physical.mount_current_observation(commit=True)
    physical.verify_mount(mount)
    custody = SettledExperienceCustodyAuthority(
        authority_key=KEY,
        w1_physical_authority_key=KEY,
        world_authority_key=KEY,
        profile=SettledExperienceCustodyProfile.create(
            profile_id="full-field-prediction-custody",
            max_children=2,
            max_snapshot_bytes=32 * 1024 * 1024,
        ),
    )
    admitted = custody.admit(
        mount,
        world_observation=observation,
    )
    capability = custody.issue_child("full-field-prediction")
    return (
        custody,
        capability,
        admitted,
        mount,
        observation,
        physical,
        world,
    )


def test_w1_acoustic_prediction_rejects_legacy_single_sound_stream() -> None:
    legacy = _settlement("legacy-acoustic", sound_frequency=12)

    with pytest.raises(ValueError, match="two complete cochleae"):
        FullFieldPredictionAuthority._verify_binaural_cochlear_topology(
            legacy
        )


def _teach_passive(
    authority: FullFieldPredictionAuthority,
    before,
    after,
):
    left = authority.admit_episode(before)
    right = authority.admit_episode(after)
    authority.open_context(left)
    step = authority.observe_next(right)
    authority.stop_context()
    return left, right, step


def test_retains_complete_six_sense_explicit_dsf_witness_and_ignores_routes() -> None:
    authority = FullFieldPredictionAuthority(authority_key=KEY)
    first = authority.admit_episode(
        _settlement("full-a", sound_frequency=13, routing_chis=(3,))
    )
    second = authority.admit_episode(
        _settlement("full-b", sound_frequency=13, routing_chis=(91,))
    )
    assert first.structure_id == second.structure_id
    interpretations = first.settlement_witness["interpretations"]
    assert tuple(item["sense"] for item in interpretations) == tuple(
        sense.value for sense in SENSE_ORDER
    )
    fields = interpretations[0]["substreams"][0]["field_tuples"][0]["fields"]
    assert {item[0] for item in fields} == {
        "D_k", "M_k", "R_rev_k", "U_star_k", "C_k", "P_k", "B_k"
    }
    assert first.settlement_witness["routing_chis"] == [3]


def test_prediction_contains_complete_target_and_exact_field_resolution() -> None:
    authority = FullFieldPredictionAuthority(authority_key=KEY)
    _teach_passive(
        authority,
        _settlement("learn-before", sight_frequency=8),
        _settlement("learn-after", sight_frequency=13),
    )
    context = authority.admit_episode(
        _settlement("live-before", sight_frequency=8)
    )
    attempt = authority.open_context(context)
    assert attempt.status == "predicted"
    candidate = attempt.candidates[0]
    assert len(candidate["settlement_witness"]["interpretations"]) == 6
    actual = authority.admit_episode(
        _settlement("live-after", sight_frequency=13)
    )
    step = authority.observe_next(actual)
    assert step.resolution.verification == "predicted_exact"
    assert step.resolution.matching_candidate_episode_ids
    outcomes = step.resolution.candidate_outcomes[0]["field_outcomes"]
    assert outcomes
    assert all(item["state"] == "exact" for item in outcomes)


def test_mismatch_and_missing_observation_are_distinct() -> None:
    authority = FullFieldPredictionAuthority(authority_key=KEY)
    _teach_passive(
        authority,
        _settlement("dist-before", sight_frequency=8),
        _settlement("dist-after", sight_frequency=13),
    )
    context = authority.admit_episode(_settlement("dist-live", sight_frequency=8))
    authority.open_context(context)
    changed = authority.admit_episode(
        _settlement("dist-changed", sight_frequency=21)
    )
    assert authority.observe_next(changed).resolution.verification == (
        "predicted_mismatch"
    )
    missing_authority = FullFieldPredictionAuthority(authority_key=KEY)
    _teach_passive(
        missing_authority,
        _settlement("missing-before", sight_frequency=8),
        _settlement("missing-after", sight_frequency=13),
    )
    missing_context = missing_authority.admit_episode(
        _settlement("missing-live", sight_frequency=8)
    )
    missing_authority.open_context(missing_context)
    unavailable = missing_authority.admit_episode(
        _settlement("dist-missing", sight_observed=False)
    )
    resolution = missing_authority.observe_next(unavailable).resolution
    assert resolution.verification == "predicted_unknown_unobserved"
    assert any(
        item["state"] == "unknown_unobserved"
        for item in resolution.candidate_outcomes[0]["field_outcomes"]
    )


def test_zero_one_many_cardinality_and_no_automatic_adjacency() -> None:
    authority = FullFieldPredictionAuthority(authority_key=KEY)
    context_a = authority.admit_episode(_settlement("card-a", sight_frequency=8))
    unused = authority.admit_episode(_settlement("card-unused", sight_frequency=9))
    assert authority.open_context(context_a).status == "unknown"
    authority.stop_context()
    assert authority.relation_records() == ()
    target_a = authority.admit_episode(_settlement("card-b", sight_frequency=11))
    authority.open_context(context_a)
    authority.observe_next(target_a)
    authority.stop_context()
    assert authority.open_context(context_a).status == "predicted"
    authority.stop_context()
    target_b = authority.admit_episode(_settlement("card-c", sight_frequency=17))
    authority.open_context(context_a)
    authority.observe_next(target_b)
    authority.stop_context()
    assert authority.open_context(context_a).status == "ambiguous"
    assert len(authority.current_attempt().candidates) == 2
    assert unused.episode_id != target_a.episode_id


def test_w1_attachment_retains_exact_parent_occurrence_and_full_field() -> None:
    custody, capability, admitted, mount, observation, physical, world = (
        _settled_prediction_custody()
    )
    authority = FullFieldPredictionAuthority(authority_key=KEY)
    custody_before = custody.snapshot_encoded()
    world_before = world.encoded_snapshot()
    producer_before = physical.status()
    episode = authority.admit_episode(
        admitted.causal_settlement,
        custody_authority=custody,
        custody_capability=capability,
    )
    assert custody.snapshot_encoded() == custody_before
    assert world.encoded_snapshot() == world_before
    assert physical.status() == producer_before
    attachment = episode.w1_attachment
    assert attachment["source_occurrence_id"] == admitted.source_occurrence_id
    assert attachment["parent_custody_receipt_sha256"] == (
        admitted.authority_receipt_sha256
    )
    assert attachment["world_execution"] is None
    assert attachment["observation"] == observation.as_record()
    assert attachment["physical_evidence"] == (
        mount.evidence_receipt.as_record()
    )
    assert attachment["occurrence_counter"] == (
        admitted.occurrence_counter.as_record()
    )
    assert attachment["observation"]["bodies"]
    assert attachment["observation"]["objects"]
    for interpretation in episode.settlement_witness["interpretations"]:
        for substream in interpretation["substreams"]:
            for field_tuple in substream["field_tuples"]:
                assert tuple(
                    name for name, _value in field_tuple["fields"]
                ) == (
                    "D_k",
                    "M_k",
                    "R_rev_k",
                    "U_star_k",
                    "C_k",
                    "P_k",
                    "B_k",
                )

    with pytest.raises(
        ValueError,
        match="not the parent occurrence",
    ):
        authority.admit_episode(
            _settlement("alien-w1", sight_frequency=19),
            custody_authority=custody,
            custody_capability=capability,
        )
    other_consumer = custody.issue_child("causal-deliberation")
    with pytest.raises(
        ValueError,
        match="belongs to another consumer",
    ):
        authority.admit_episode(
            admitted.causal_settlement,
            custody_authority=custody,
            custody_capability=other_consumer,
        )


def test_w1_prediction_cannot_invoke_producers_or_accept_raw_boundaries(
    monkeypatch,
) -> None:
    (
        custody,
        capability,
        admitted,
        _mount,
        observation,
        physical,
        world,
    ) = (
        _settled_prediction_custody()
    )

    tree = ast.parse(inspect.getsource(prediction_module))
    forbidden_calls = {
        "mount_current_observation",
        "mount_action_outcome",
        "mount_authenticated_action_outcome",
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

    def forbidden(*_args, **_kwargs):
        raise AssertionError("prediction invoked a W1 producer")

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

    authority = FullFieldPredictionAuthority(authority_key=KEY)
    custody_before = custody.snapshot_encoded()
    world_before = world.encoded_snapshot()
    producer_before = physical.status()
    episode = authority.admit_episode(
        admitted.causal_settlement,
        custody_authority=custody,
        custody_capability=capability,
    )
    assert custody.snapshot_encoded() == custody_before
    assert world.encoded_snapshot() == world_before
    assert physical.status() == producer_before
    attachment = episode.w1_attachment
    assert attachment["source_occurrence_id"] == capability.source_occurrence_id
    assert attachment["parent_custody_receipt_sha256"] == (
        capability.parent_custody_receipt_sha256
    )

    with pytest.raises(
        TypeError,
        match="settled custody authority",
    ):
        authority.admit_episode(
            admitted.causal_settlement,
            custody_authority=observation,
            custody_capability=capability,
        )
    with pytest.raises(
        TypeError,
        match="settled custody capability",
    ):
        authority.admit_episode(
            admitted.causal_settlement,
            custody_authority=custody,
            custody_capability=admitted.causal_settlement,
        )
    with pytest.raises(TypeError, match="unexpected keyword"):
        authority.admit_episode(
            admitted.causal_settlement,
            observation=observation,
        )


def _teach_action(cycle: CausalActionCycle, trigger, action: ActionCommand):
    cycle.accept(trigger)
    relation = cycle.issue_teacher_relation(
        trigger_reference=trigger.event_id,
        action=action,
        source="teacher",
        nonce="full-field-action-teacher-0001",
    )
    cycle.learn(
        trigger_reference=trigger.event_id,
        action=action,
        teacher_relation=relation,
    )


def test_action_conditioned_relation_requires_live_intent_and_closed_outcome() -> None:
    learned_trigger = _settlement("action-teach", sight_frequency=8)
    live_trigger = _settlement("action-live", sight_frequency=8)
    outcome = _settlement("action-outcome", sight_frequency=19)
    cycle = CausalActionCycle(authority_key=KEY)
    command = ActionCommand.embodiment("body.motion.primary", b"exact-move")
    _teach_action(cycle, learned_trigger, command)
    selection = cycle.select(live_trigger)
    assert selection.status == "committed"

    prediction = FullFieldPredictionAuthority(authority_key=KEY)
    context_episode = prediction.admit_episode(live_trigger)
    outcome_episode = prediction.admit_episode(outcome)
    prediction.open_context(context_episode)
    assert prediction.condition_on_action(
        intent=selection.intent, action_cycle=cycle
    ).status == "unknown"
    with pytest.raises(ValueError, match="action_outcome_unavailable"):
        prediction.observe_next(outcome_episode)

    execution = cycle.record_execution(
        intent_receipt_sha256=selection.intent.authority_receipt_sha256,
        executor_receipt_sha256=_sha("executor"),
        disposition="executed",
    )
    observed = cycle.observe_outcome(
        execution_receipt_sha256=execution.authority_receipt_sha256,
        settlement=outcome,
    )
    cycle.apply_feedback(
        outcome_receipt_sha256=observed.authority_receipt_sha256,
        decision="confirm",
        source="teacher",
        nonce="full-field-action-feedback-0001",
    )
    closure_record = cycle.latest_closure_record(
        selection.intent.binding_id
    )
    assert closure_record is not None
    step = prediction.observe_next(
        outcome_episode,
        action_cycle=cycle,
        closure_record=closure_record,
    )
    assert step.transition.mode == "action_conditioned"
    assert step.transition.closure_record["closure_receipt_sha256"]
    prediction.stop_context()

    repeated = _settlement("action-repeat", sight_frequency=8)
    passive_context = prediction.admit_episode(repeated)
    assert prediction.open_context(passive_context).status == "unknown"
    prediction.stop_context()
    next_selection = cycle.select(repeated)
    prediction.open_context(passive_context)
    attempt = prediction.condition_on_action(
        intent=next_selection.intent, action_cycle=cycle
    )
    assert attempt.status == "predicted"
    assert attempt.candidates[0]["structure_id"] == outcome_episode.structure_id
    restored = FullFieldPredictionAuthority(authority_key=KEY)
    restored.restore_encoded(prediction.encoded_snapshot())
    assert restored.current_attempt().mode == "passive"
    assert restored.current_attempt().status == "unknown"
    with pytest.raises(ValueError, match="passive prediction"):
        restored.observe_next(
            outcome_episode,
            action_cycle=cycle,
            closure_record=closure_record,
        )


def test_cancelled_action_returns_exact_context_to_passive_prediction() -> None:
    learned_trigger = _settlement("cancel-teach", sight_frequency=8)
    live_trigger = _settlement("cancel-live", sight_frequency=8)
    cycle = CausalActionCycle(authority_key=KEY)
    command = ActionCommand.embodiment("body.motion.primary", b"exact-stop")
    _teach_action(cycle, learned_trigger, command)
    selection = cycle.select(live_trigger)
    prediction = FullFieldPredictionAuthority(authority_key=KEY)
    context = prediction.admit_episode(live_trigger)
    prediction.open_context(context)
    prediction.condition_on_action(
        intent=selection.intent, action_cycle=cycle
    )

    assert prediction.current_episode() == context
    passive = prediction.cancel_conditioned_action(
        selection.intent.authority_receipt_sha256
    )
    assert passive.mode == "passive"
    assert prediction.current_episode() == context
    with pytest.raises(ValueError, match="no matching conditioned action"):
        prediction.cancel_conditioned_action(
            selection.intent.authority_receipt_sha256
        )


def test_unreferenced_experience_witnesses_are_not_a_lifetime_index() -> None:
    authority = FullFieldPredictionAuthority(authority_key=KEY)
    episodes = tuple(
        authority.admit_episode(
            _settlement(f"unreferenced-{index}", sight_frequency=8 + index)
        )
        for index in range(8)
    )
    authority.open_context(episodes[-1])
    removed = authority.compact_unreferenced_episodes()
    assert removed == 7
    assert authority.status()["episodes"] == 1
    assert authority.current_episode() == episodes[-1]


def test_duplicate_concurrent_advance_commits_once_and_duplicate_learning_is_constant() -> None:
    authority = FullFieldPredictionAuthority(authority_key=KEY)
    before = authority.admit_episode(_settlement("race-before", sight_frequency=8))
    after = authority.admit_episode(_settlement("race-after", sight_frequency=14))
    authority.open_context(before)
    with ThreadPoolExecutor(max_workers=8) as pool:
        steps = tuple(pool.map(lambda _index: authority.observe_next(after), range(8)))
    assert len({item.transition.transition_id for item in steps}) == 1
    assert len(authority.relation_records()) == 1
    assert authority.status()["episodes"] == 2
    authority.stop_context()
    authority.open_context(before)
    authority.observe_next(after)
    before_bytes = len(authority.encoded_snapshot())
    for _ in range(20):
        authority.stop_context()
        authority.open_context(before)
        authority.observe_next(after)
    assert len(authority.relation_records()) == 1
    assert len(authority.encoded_snapshot()) == before_bytes


def test_capacity_is_atomic_and_never_evicts() -> None:
    authority = FullFieldPredictionAuthority(
        authority_key=KEY,
        passive_relation_capacity=1,
    )
    before = authority.admit_episode(_settlement("cap-before", sight_frequency=8))
    one = authority.admit_episode(_settlement("cap-one", sight_frequency=9))
    two = authority.admit_episode(_settlement("cap-two", sight_frequency=31))
    assert one.structure_id != two.structure_id
    authority.open_context(before)
    authority.observe_next(one)
    authority.stop_context()
    prior = authority.encoded_snapshot()
    authority.open_context(before)
    with pytest.raises(RuntimeError, match="prediction_capacity_full"):
        authority.observe_next(two)
    authority.stop_context()
    assert authority.relation_records()[0]["target_structure_id"] == one.structure_id
    assert len(authority.relation_records()) == 1
    assert len(prior) <= 32 * 1024 * 1024


def test_unreferenced_episode_compaction_preserves_learned_evidence() -> None:
    authority = FullFieldPredictionAuthority(authority_key=KEY)
    before, after, _step = _teach_passive(
        authority,
        _settlement("gc-before", sight_frequency=8),
        _settlement("gc-after", sight_frequency=15),
    )
    authority.stop_context()
    for index in range(160):
        authority.admit_episode(
            _settlement(
                f"gc-transient-{index}",
                sight_frequency=20 + (index % 11),
            )
        )
    assert authority.status()["episodes"] <= 132
    assert len(authority.relation_records()) == 1
    authority.open_context(before)
    attempt = authority.current_attempt()
    assert attempt.status == "predicted"
    assert attempt.candidates[0]["structure_id"] == after.structure_id


def test_snapshot_restart_and_every_episode_tamper_fail_closed() -> None:
    authority = FullFieldPredictionAuthority(authority_key=KEY)
    before, after, _step = _teach_passive(
        authority,
        _settlement("restart-before", sight_frequency=8),
        _settlement("restart-after", sight_frequency=15),
    )
    authority.open_context(before)
    snapshot = authority.encoded_snapshot()
    restored = FullFieldPredictionAuthority(authority_key=KEY)
    restored.restore_encoded(snapshot)
    assert restored.encoded_snapshot() == snapshot
    assert restored.current_attempt().status == "predicted"

    envelope = json.loads(snapshot)
    payload = bytearray(base64.b64decode(envelope["payload_base64"]))
    payload[-2] ^= 1
    envelope["payload_base64"] = base64.b64encode(payload).decode("ascii")
    with pytest.raises(ValueError):
        restored.restore_encoded(
            json.dumps(envelope, separators=(",", ":"), sort_keys=True).encode()
        )

    witness = copy.deepcopy(after.settlement_witness)
    witness["interpretations"][0]["state"] = "sensor_unavailable"
    tampered = replace(after, settlement_witness=witness)
    restored.stop_context()
    with pytest.raises(ValueError):
        restored.open_context(tampered)


def test_authenticated_legacy_witness_boundaries_migrate_without_losing_learning() -> None:
    before_settlement = _settlement(
        "legacy-boundary-before",
        sight_frequency=8,
    )
    after_settlement = _settlement(
        "legacy-boundary-after",
        sight_frequency=15,
    )
    legacy_prediction = FullFieldPredictionAuthority(
        authority_key=KEY,
        max_witness_bytes=prediction_module.LEGACY_MAX_WITNESS_BYTES,
    )
    before, after, _step = _teach_passive(
        legacy_prediction,
        before_settlement,
        after_settlement,
    )
    legacy_prediction.open_context(before)
    legacy_prediction_snapshot = legacy_prediction.encoded_snapshot()

    migrated_prediction = FullFieldPredictionAuthority(authority_key=KEY)
    migrated_prediction.restore_encoded(legacy_prediction_snapshot)
    assert migrated_prediction.current_attempt().status == "predicted"
    assert (
        migrated_prediction.current_attempt().candidates[0]["structure_id"]
        == after.structure_id
    )
    current_prediction_snapshot = migrated_prediction.encoded_snapshot()
    assert current_prediction_snapshot != legacy_prediction_snapshot
    cold_prediction = FullFieldPredictionAuthority(authority_key=KEY)
    cold_prediction.restore_encoded(current_prediction_snapshot)
    assert cold_prediction.encoded_snapshot() == current_prediction_snapshot

    legacy_cycle = CausalActionCycle(
        authority_key=KEY,
        max_witness_bytes=prediction_module.LEGACY_MAX_WITNESS_BYTES,
    )
    witness = legacy_cycle.accept(before_settlement)
    binding = legacy_cycle.teach(
        trigger_reference=witness.event_id,
        action=ActionCommand.embodiment("test.body", b"heard"),
        source="authenticated-teacher",
        nonce="legacy-boundary-teaching-nonce",
    )
    legacy_cycle_snapshot = legacy_cycle.encoded_snapshot()

    migrated_cycle = CausalActionCycle(authority_key=KEY)
    migrated_cycle.restore_encoded(legacy_cycle_snapshot)
    relation = migrated_cycle.verified_relation_evidence()
    assert len(relation) == 1
    assert relation[0].binding_id == binding.binding_id
    current_cycle_snapshot = migrated_cycle.encoded_snapshot()
    assert current_cycle_snapshot != legacy_cycle_snapshot
    cold_cycle = CausalActionCycle(authority_key=KEY)
    cold_cycle.restore_encoded(current_cycle_snapshot)
    assert cold_cycle.encoded_snapshot() == current_cycle_snapshot


def test_hmac_valid_snapshot_cannot_cross_bind_relation_episodes() -> None:
    authority = FullFieldPredictionAuthority(authority_key=KEY)
    before, after, _step = _teach_passive(
        authority,
        _settlement("cross-bind-before", sight_frequency=8),
        _settlement("cross-bind-after", sight_frequency=15),
    )
    authority.stop_context()
    envelope = json.loads(authority.encoded_snapshot())
    state = json.loads(base64.b64decode(envelope["payload_base64"]))
    relation = state["relations"][0]
    evidence = relation["latest_evidence"]
    assert evidence["context_episode_id"] == before.episode_id
    evidence["context_episode_id"] = after.episode_id
    evidence_payload = {
        key: value for key, value in evidence.items()
        if key not in {"authority_hmac_sha256", "transition_id"}
    }
    evidence["transition_id"] = prediction_module._digest(
        evidence_payload
    )
    evidence["authority_hmac_sha256"] = prediction_module._sign(
        authority._key,
        prediction_module.TRANSITION_DOMAIN,
        evidence_payload,
    )
    relation_payload = {
        "action_receipt_sha256": relation["action_receipt_sha256"],
        "context_structure_id": relation["context_structure_id"],
        "latest_evidence": evidence,
        "mode": relation["mode"],
        "relation_id": relation["relation_id"],
        "schema": relation["schema"],
        "target_structure_id": relation["target_structure_id"],
    }
    relation["authority_hmac_sha256"] = prediction_module._sign(
        authority._key,
        prediction_module.RELATION_DOMAIN,
        relation_payload,
    )
    payload = prediction_module._canonical(state)
    changed = prediction_module._canonical({
        "authority_hmac_sha256": hmac.new(
            authority._key,
            prediction_module.STATE_DOMAIN + payload,
            hashlib.sha256,
        ).hexdigest(),
        "payload_base64": base64.b64encode(payload).decode("ascii"),
        "schema": prediction_module.ENVELOPE_SCHEMA,
    })
    restored = FullFieldPredictionAuthority(authority_key=KEY)
    with pytest.raises(ValueError, match="lost its retained episodes"):
        restored.restore_encoded(changed)


def test_source_contains_no_reduced_or_automatic_prediction_authority() -> None:
    source = (
        __import__(
            "dsf_ai_service.substrate.full_field_prediction",
            fromlist=["unused"],
        )
        .__loader__
        .get_source("dsf_ai_service.substrate.full_field_prediction")
    )
    for forbidden in (
        "reading_prediction_ledger",
        "sklearn",
        "torch",
        "tensorflow",
        "nearest_neighbor",
        "timing_speaker",
        "causal_language_construction",
        "auditory_token_sequence",
        "auditory_batch_causal_intake",
        "unicode_scalars",
    ):
        assert forbidden not in source
