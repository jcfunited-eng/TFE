from __future__ import annotations

import base64
import copy
import hashlib
import json
import math
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from fractions import Fraction

import pytest

import dsf_ai_service.substrate.auditory_batch_causal_intake as intake_module
import dsf_ai_service.substrate.auditory_token_sequence as token_module
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
from dsf_ai_service.substrate.auditory_batch_causal_intake import (
    AuditoryBatchCausalEntryLink,
    AuditoryBatchCausalIntakeAuthority,
    AuditoryBatchCausalIntakeReceipt,
)
from dsf_ai_service.substrate.auditory_token_sequence import (
    AuditoryTokenSequenceAuthority,
    AuditoryTokenSequenceReceipt,
    OrderedAuditoryTokenOccurrence,
    TokenClassIdentity,
    TokenClassificationState,
)
from dsf_ai_service.substrate.causal_action_cycle import (
    ActionCommand,
    CausalActionCycle,
)
from dsf_ai_service.substrate.causal_language_construction import (
    CausalLanguageConstructionAuthority,
)
from dsf_ai_service.substrate.embodiment_sensory_outcome import (
    EmbodimentSensoryOutcomeAuthority,
)
from dsf_ai_service.substrate.embodiment_world import EmbodimentWorldAuthority
from dsf_ai_service.substrate.exact_causal_experience import (
    ExactCausalExperienceOwner,
)
from dsf_ai_service.substrate.full_field_prediction import (
    FullFieldPredictionAuthority,
    _compare_structures,
    _overall,
)


KEY = b"full-field-prediction-test-key-" * 2
TOKEN_KEY = b"full-field-token-test-key-" * 2
INTAKE_KEY = b"full-field-intake-test-key-" * 2


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


def _token_sequence(
    authority: AuditoryTokenSequenceAuthority,
    forms: tuple[str, ...],
    *,
    label: str,
    states: tuple[TokenClassificationState, ...] | None = None,
) -> AuditoryTokenSequenceReceipt:
    occurrences = []
    for ordinal, form in enumerate(forms):
        state = (
            states[ordinal] if states is not None
            else TokenClassificationState.UNIQUE
        )
        candidates = (
            ()
            if state is TokenClassificationState.UNKNOWN
            else (
                TokenClassIdentity(_sha(f"{form}-a"), form),
                TokenClassIdentity(_sha(f"{form}-b"), f"{form}-other"),
            )
            if state is TokenClassificationState.AMBIGUOUS
            else (TokenClassIdentity(_sha(form), form),)
        )
        sub_event_id = _sha(f"{label}-event-{ordinal}")
        classification_payload = {
            "candidates": [value.as_record() for value in candidates],
            "schema": token_module.TOKEN_CLASSIFICATION_SCHEMA,
            "state": state.value,
            "sub_event_id": sub_event_id,
        }
        start = ordinal * 20
        occurrences.append(OrderedAuditoryTokenOccurrence(
            ordinal=ordinal,
            sub_event_id=sub_event_id,
            source_sample_start=start,
            source_sample_end=start + 10,
            source_time_start=Fraction(start, 16_000),
            source_time_end=Fraction(start + 10, 16_000),
            structural_fingerprint=_sha(f"{label}-structure-{ordinal}"),
            l5_authority_receipt_sha256=_sha(f"{label}-l5-{ordinal}"),
            terminal_authority_receipt_sha256=_sha(
                f"{label}-terminal-{ordinal}"
            ),
            sub_event_admission_hmac_sha256=_sha(
                f"{label}-admission-{ordinal}"
            ),
            classification_state=state,
            token_candidates=candidates,
            classification_authority_hmac_sha256=token_module._hmac(
                authority._classification_key, classification_payload
            ),
        ))
    binding = _sha("binding")
    base = {
        "binding_state_sha256": binding,
        "occurrences": [value.as_record() for value in occurrences],
        "schema": token_module.TOKEN_SEQUENCE_SCHEMA,
        "stream_id": f"stream-{label}",
    }
    sequence_id = token_module._digest(base)
    provisional = AuditoryTokenSequenceReceipt(
        sequence_id=sequence_id,
        stream_id=f"stream-{label}",
        binding_state_sha256=binding,
        occurrences=tuple(occurrences),
        authority_hmac_sha256="",
    )
    result = replace(
        provisional,
        authority_hmac_sha256=token_module._hmac(
            authority._sequence_key, provisional.payload()
        ),
    )
    authority.verify_sequence(result)
    return result


def _intake(sequence: AuditoryTokenSequenceReceipt, settlement):
    authority = AuditoryBatchCausalIntakeAuthority(authority_key=INTAKE_KEY)
    entries = tuple(
        AuditoryBatchCausalEntryLink(
            ordinal=item.ordinal,
            sub_event_id=item.sub_event_id,
            source_sample_start=item.source_sample_start,
            source_sample_end=item.source_sample_end,
            source_time_start=item.source_time_start,
            source_time_end=item.source_time_end,
            structural_fingerprint=item.structural_fingerprint,
            terminal_authority_receipt_sha256=(
                item.terminal_authority_receipt_sha256
            ),
            l5_authority_receipt_sha256=item.l5_authority_receipt_sha256,
        )
        for item in sequence.occurrences
    )
    values = {
        "advance_authority_receipt_sha256": _sha("advance"),
        "batch_authority_receipt_sha256": _sha("batch"),
        "token_sequence_id": sequence.sequence_id,
        "token_sequence_authority_hmac_sha256": (
            sequence.authority_hmac_sha256
        ),
        "joint_settlement_authority_receipt_sha256": _sha("joint"),
        "causal_settlement_authority_receipt_sha256": (
            settlement.authority_receipt_sha256
        ),
        "assembly_id": settlement.assembly_id,
        "stream_id": sequence.stream_id,
        "source_time_start": settlement.source_time_start,
        "source_time_end": settlement.source_time_end,
        "entries": entries,
    }
    payload = intake_module._intake_payload(**values)
    receipt = AuditoryBatchCausalIntakeReceipt(
        intake_id=intake_module._digest(payload),
        **values,
        authority_hmac_sha256=intake_module._sign(
            authority._intake_key, payload
        ),
    )
    authority.verify_for_episode(
        intake=receipt, sequence=sequence, settlement=settlement
    )
    return authority, receipt


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


def test_auditory_sequence_order_classification_and_intake_are_authoritative() -> None:
    token_authority = AuditoryTokenSequenceAuthority(
        authority_secret=TOKEN_KEY
    )
    authority = FullFieldPredictionAuthority(authority_key=KEY)
    settlement = _settlement("auditory", sound_frequency=10)
    sequence = _token_sequence(
        token_authority, ("hello", "guala"), label="auditory"
    )
    intake_authority, intake = _intake(sequence, settlement)
    episode = authority.admit_episode(
        settlement,
        intake_authority=intake_authority,
        intake=intake,
        token_authority=token_authority,
        token_sequence=sequence,
    )
    auditory = episode.auditory_attachment
    assert [
        item["token_candidates"][0]["token_form"]
        for item in auditory["sequence"]["occurrences"]
    ] == ["hello", "guala"]
    tampered = replace(sequence, stream_id="wrong-stream")
    with pytest.raises(ValueError):
        authority.admit_episode(
            settlement,
            intake_authority=intake_authority,
            intake=intake,
            token_authority=token_authority,
            token_sequence=tampered,
        )

    unique = {
        "full_field": {"interpretations": [
            {"sense": sense.value, "state": "sensor_unavailable", "substreams": []}
            for sense in SENSE_ORDER
        ]},
        "auditory": {
            "occurrences": [
                {
                    "classification_state": "unique",
                    "ordinal": 0,
                    "structural_fingerprint": _sha("one"),
                    "token_candidates": [{"token_class_id": _sha("hello"), "token_form": "hello"}],
                }
            ]
        },
        "w1_geometry": None,
    }
    unknown = copy.deepcopy(unique)
    unknown["auditory"]["occurrences"][0]["classification_state"] = "unknown"
    unknown["auditory"]["occurrences"][0]["token_candidates"] = []
    outcomes = _compare_structures(unique, unknown)
    assert _overall(outcomes) == "unknown"
    assert any("/auditory/" in item.path for item in outcomes)
    ambiguous = copy.deepcopy(unique)
    ambiguous["auditory"]["occurrences"][0]["classification_state"] = "ambiguous"
    ambiguous["auditory"]["occurrences"][0]["token_candidates"].append({
        "token_class_id": _sha("other"),
        "token_form": "other",
    })
    assert _overall(_compare_structures(unique, ambiguous)) == "ambiguous"


def test_w1_attachment_retains_exact_bodies_objects_and_topology() -> None:
    world = EmbodimentWorldAuthority(authority_key=KEY)
    sensory = EmbodimentSensoryOutcomeAuthority(authority_key=KEY)
    observation = world.observation_snapshot()
    outcome = sensory.transduce(
        observation,
        causal_owner=ExactCausalExperienceOwner(
            on_settlement=lambda _value: None,
            log_event=lambda *_args, **_kwargs: None,
        ),
        commit=False,
    )
    authority = FullFieldPredictionAuthority(authority_key=KEY)
    episode = authority.admit_episode(
        outcome.causal_settlement,
        world_authority=world,
        sensory_authority=sensory,
        observation=observation,
        outcome_receipt=outcome.observation_receipt,
    )
    record = episode.w1_attachment["observation"]
    assert record["bodies"] and record["objects"]
    assert record["room_bounds"] and record["regions"] and record["portals"]
    changed = replace(observation, revision=observation.revision + 1)
    with pytest.raises(ValueError):
        authority.admit_episode(
            outcome.causal_settlement,
            world_authority=world,
            sensory_authority=sensory,
            observation=changed,
            outcome_receipt=outcome.observation_receipt,
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
    cycle_state = json.loads(
        base64.b64decode(cycle.encoded_snapshot()["payload_base64"])
    )
    closure_record = cycle_state["bindings"][0]["latest_closure"]
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


def test_public_language_episode_verifier_is_read_only_and_exact() -> None:
    token_authority = AuditoryTokenSequenceAuthority(
        authority_secret=TOKEN_KEY
    )
    language = CausalLanguageConstructionAuthority(authority_key=KEY)
    settlement = _settlement("language", sound_frequency=12)
    sequence = _token_sequence(token_authority, ("hello",), label="language")
    intake_authority, intake = _intake(sequence, settlement)
    admission = language.admit_episode(
        intake_authority=intake_authority,
        intake=intake,
        token_authority=token_authority,
        sequence=sequence,
        settlement=settlement,
    )
    before = language.working_count
    verified = language.verify_episode_record(admission.episode.as_record())
    assert verified == admission.episode
    assert language.working_count == before
    changed = copy.deepcopy(admission.episode.as_record())
    changed["tokens"][0]["token_form"] = "wrong"
    with pytest.raises(ValueError):
        language.verify_episode_record(changed)


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
    ):
        assert forbidden not in source
