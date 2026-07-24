from __future__ import annotations

import ast
import copy
import hashlib
import inspect
import itertools
import json
import math
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
    TokenClassificationState,
    TokenClassIdentity,
)
from dsf_ai_service.substrate.causal_language_construction import (
    CausalLanguageConstructionAuthority,
)
from dsf_ai_service.substrate.exact_causal_experience import (
    ExactCausalExperienceOwner,
)


TOKEN_SECRET = b"causal-language-token-test-secret" * 2
CONSTRUCTION_SECRET = b"causal-language-construction-test-secret" * 2
INTAKE_SECRET = b"causal-language-intake-test-secret" * 2


def _canonical(value: object) -> bytes:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _sha(value: object) -> str:
    if isinstance(value, str):
        value = value.encode("utf-8")
    return hashlib.sha256(value).hexdigest()


def _sequence(
    authority: AuditoryTokenSequenceAuthority,
    forms: tuple[str, ...],
    *,
    label: str,
    state_overrides: dict[int, TokenClassificationState] | None = None,
) -> AuditoryTokenSequenceReceipt:
    occurrences = []
    for ordinal, form in enumerate(forms):
        state = (state_overrides or {}).get(ordinal, TokenClassificationState.UNIQUE)
        candidates = (
            ()
            if state is TokenClassificationState.UNKNOWN
            else (
                TokenClassIdentity(_sha(f"class:{form}:a"), form),
                TokenClassIdentity(_sha(f"class:{form}:b"), form + "-other"),
            )
            if state is TokenClassificationState.AMBIGUOUS
            else (TokenClassIdentity(_sha(f"class:{form}:a"), form),)
        )
        sub_event_id = _sha(f"sub-event:{label}:{ordinal}")
        classification_payload = {
            "candidates": [value.as_record() for value in candidates],
            "schema": token_module.TOKEN_CLASSIFICATION_SCHEMA,
            "state": state.value,
            "sub_event_id": sub_event_id,
        }
        start = ordinal * 100
        occurrences.append(OrderedAuditoryTokenOccurrence(
            ordinal=ordinal,
            sub_event_id=sub_event_id,
            source_sample_start=start,
            source_sample_end=start + 40,
            source_time_start=Fraction(start, 16_000),
            source_time_end=Fraction(start + 40, 16_000),
            structural_fingerprint=_sha(f"structure:{label}:{ordinal}"),
            l5_authority_receipt_sha256=_sha(f"l5:{label}:{ordinal}"),
            terminal_authority_receipt_sha256=_sha(f"terminal:{label}:{ordinal}"),
            sub_event_admission_hmac_sha256=_sha(f"admission:{label}:{ordinal}"),
            classification_state=state,
            token_candidates=candidates,
            classification_authority_hmac_sha256=token_module._hmac(
                authority._classification_key, classification_payload
            ),
        ))
    binding_state = _sha("binding-state")
    base = {
        "binding_state_sha256": binding_state,
        "occurrences": [value.as_record() for value in occurrences],
        "schema": token_module.TOKEN_SEQUENCE_SCHEMA,
        "stream_id": f"stream-{label}",
    }
    sequence_id = token_module._digest(base)
    provisional = AuditoryTokenSequenceReceipt(
        sequence_id=sequence_id,
        stream_id=f"stream-{label}",
        binding_state_sha256=binding_state,
        occurrences=tuple(occurrences),
        authority_hmac_sha256="",
    )
    receipt = AuditoryTokenSequenceReceipt(
        sequence_id=sequence_id,
        stream_id=provisional.stream_id,
        binding_state_sha256=binding_state,
        occurrences=tuple(occurrences),
        authority_hmac_sha256=token_module._hmac(
            authority._sequence_key, provisional.payload()
        ),
    )
    authority.verify_sequence(receipt)
    return receipt


def _intake(
    sequence: AuditoryTokenSequenceReceipt,
    settlement,
) -> tuple[
    AuditoryBatchCausalIntakeAuthority,
    AuditoryBatchCausalIntakeReceipt,
]:
    authority = AuditoryBatchCausalIntakeAuthority(
        authority_key=INTAKE_SECRET
    )
    entries = tuple(
        AuditoryBatchCausalEntryLink(
            ordinal=value.ordinal,
            sub_event_id=value.sub_event_id,
            source_sample_start=value.source_sample_start,
            source_sample_end=value.source_sample_end,
            source_time_start=value.source_time_start,
            source_time_end=value.source_time_end,
            structural_fingerprint=value.structural_fingerprint,
            terminal_authority_receipt_sha256=(
                value.terminal_authority_receipt_sha256
            ),
            l5_authority_receipt_sha256=(
                value.l5_authority_receipt_sha256
            ),
        )
        for value in sequence.occurrences
    )
    payload = intake_module._intake_payload(
        advance_authority_receipt_sha256=_sha("advance"),
        batch_authority_receipt_sha256=_sha("batch"),
        token_sequence_id=sequence.sequence_id,
        token_sequence_authority_hmac_sha256=(
            sequence.authority_hmac_sha256
        ),
        joint_settlement_authority_receipt_sha256=_sha("joint"),
        causal_settlement_authority_receipt_sha256=(
            settlement.authority_receipt_sha256
        ),
        assembly_id=settlement.assembly_id,
        stream_id=sequence.stream_id,
        source_time_start=settlement.source_time_start,
        source_time_end=settlement.source_time_end,
        entries=entries,
    )
    receipt = AuditoryBatchCausalIntakeReceipt(
        intake_id=intake_module._digest(payload),
        advance_authority_receipt_sha256=_sha("advance"),
        batch_authority_receipt_sha256=_sha("batch"),
        token_sequence_id=sequence.sequence_id,
        token_sequence_authority_hmac_sha256=(
            sequence.authority_hmac_sha256
        ),
        joint_settlement_authority_receipt_sha256=_sha("joint"),
        causal_settlement_authority_receipt_sha256=(
            settlement.authority_receipt_sha256
        ),
        assembly_id=settlement.assembly_id,
        stream_id=sequence.stream_id,
        source_time_start=settlement.source_time_start,
        source_time_end=settlement.source_time_end,
        entries=entries,
        authority_hmac_sha256=intake_module._sign(
            authority._intake_key, payload
        ),
    )
    authority.verify_for_episode(
        intake=receipt,
        sequence=sequence,
        settlement=settlement,
    )
    return authority, receipt


def _episode_admission(
    authority,
    token_authority,
    sequence,
    settlement,
):
    intake_authority, intake = _intake(sequence, settlement)
    return authority.admit_episode(
        intake_authority=intake_authority,
        intake=intake,
        token_authority=token_authority,
        sequence=sequence,
        settlement=settlement,
    )


def _substream(
    sense: PhysicalSense,
    *,
    substream_id: str,
    axis_value: str,
) -> NativeSensorySubstreamInput:
    count = 96
    return NativeSensorySubstreamInput(
        sense=sense,
        sensor_id=f"sensor-{sense.value}",
        substream_id=substream_id,
        topology_index=0,
        coordinates=(NativeAxisCoordinate("referent", axis_value),),
        physical_quantity=f"{sense.value}-intensity",
        physical_unit="normalized-intensity",
        source_times=tuple(Fraction(index, 200) for index in range(count)),
        normalized_signal=tuple(
            math.sin(2 * math.pi * 8 * index / 200) for index in range(count)
        ),
        phase_turns=tuple(Fraction(index // 12) for index in range(count)),
    )


def _settlement(
    label: str,
    *,
    sight: str = "red",
    touch: str = "soft",
    sound: str | None = None,
    routing_chis: tuple[int, ...] = (),
):
    observed = {
        PhysicalSense.SIGHT: (_substream(
            PhysicalSense.SIGHT, substream_id="visual-referent", axis_value=sight
        ),),
        PhysicalSense.TOUCH: (_substream(
            PhysicalSense.TOUCH, substream_id="touch-referent", axis_value=touch
        ),),
    }
    if sound is not None:
        observed[PhysicalSense.SOUND] = (_substream(
            PhysicalSense.SOUND,
            substream_id="auditory-language-carrier",
            axis_value=sound,
        ),)
    built = build_six_sense_full_field(
        assembly_id=f"causal-language-{label}",
        source_time_start=Fraction(0),
        source_time_end=Fraction(96, 200),
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
        source_tags=(f"source:{label}",),
    )


def _admit(authority, token_authority, forms, settlement, label):
    result = _episode_admission(
        authority,
        token_authority,
        _sequence(token_authority, forms, label=label),
        settlement,
    )
    assert result.state == "unique"
    assert result.episode is not None
    return result


def test_learns_arbitrary_non_svo_order_without_grammatical_roles() -> None:
    tokens = AuditoryTokenSequenceAuthority(authority_secret=TOKEN_SECRET)
    authority = CausalLanguageConstructionAuthority(authority_key=CONSTRUCTION_SECRET)
    red = _admit(
        authority, tokens, ("ball", "moves", "guala"),
        _settlement("non-svo-red", sight="red"), "non-svo-red",
    )
    blue = _admit(
        authority, tokens, ("cube", "moves", "guala"),
        _settlement("non-svo-blue", sight="blue"), "non-svo-blue",
    )
    learned = authority.learn_construction((
        red.episode.structure_id, blue.episode.structure_id
    ))
    assert learned.state == "unique"
    assert learned.reason == "construction_learned"
    assert [value.kind for value in learned.construction.elements] == [
        "slot", "fixed", "fixed"
    ]
    assert authority.generate(_settlement("generate-red", sight="red")).tokens == (
        red.episode.tokens
    )
    assert all(
        forbidden not in _canonical(learned.construction.as_record()).decode("utf-8")
        for forbidden in ("subject", "verb", "object")
    )


def test_one_token_change_requires_exactly_one_causal_referent_change() -> None:
    tokens = AuditoryTokenSequenceAuthority(authority_secret=TOKEN_SECRET)
    authority = CausalLanguageConstructionAuthority(authority_key=CONSTRUCTION_SECRET)
    first = _admit(
        authority, tokens, ("red", "thing"),
        _settlement("one-change-a", sight="red", touch="soft"), "one-change-a",
    )
    second = _admit(
        authority, tokens, ("blue", "thing"),
        _settlement("one-change-b", sight="blue", touch="hard"), "one-change-b",
    )
    result = authority.learn_construction((
        first.episode.structure_id, second.episode.structure_id
    ))
    assert result.state == "unknown"
    assert result.reason == "causal_contrast_not_unique"
    assert authority.construction_count == 0


def test_multi_slot_requires_complete_independence_lattice() -> None:
    tokens = AuditoryTokenSequenceAuthority(authority_secret=TOKEN_SECRET)
    incomplete = CausalLanguageConstructionAuthority(authority_key=CONSTRUCTION_SECRET)
    partial = []
    for sight, touch in (("red", "soft"), ("blue", "soft"), ("red", "hard")):
        partial.append(_admit(
            incomplete,
            tokens,
            (sight, "is", touch),
            _settlement(f"partial-{sight}-{touch}", sight=sight, touch=touch),
            f"partial-{sight}-{touch}",
        ))
    refused = incomplete.learn_construction(tuple(
        value.episode.structure_id for value in partial
    ))
    assert refused.reason == "independence_lattice_incomplete"

    complete = CausalLanguageConstructionAuthority(authority_key=CONSTRUCTION_SECRET)
    lattice = []
    for sight, touch in itertools.product(("red", "blue"), ("soft", "hard")):
        lattice.append(_admit(
            complete,
            tokens,
            (sight, "is", touch),
            _settlement(f"full-{sight}-{touch}", sight=sight, touch=touch),
            f"full-{sight}-{touch}",
        ))
    learned = complete.learn_construction(tuple(
        value.episode.structure_id for value in lattice
    ))
    assert learned.state == "unique"
    assert [value.kind for value in learned.construction.elements] == [
        "slot", "fixed", "slot"
    ]
    generated = complete.generate(
        _settlement("full-generate", sight="blue", touch="hard")
    )
    assert generated.state == "unique"
    assert tuple(value.token_form for value in generated.tokens) == (
        "blue", "is", "hard"
    )


def test_comprehension_is_separate_and_requires_sequence_causal_agreement() -> None:
    tokens = AuditoryTokenSequenceAuthority(authority_secret=TOKEN_SECRET)
    authority = CausalLanguageConstructionAuthority(authority_key=CONSTRUCTION_SECRET)
    episodes = [
        _admit(
            authority, tokens, (color, "appears"),
            _settlement(f"comprehend-{color}", sight=color), f"comprehend-{color}",
        )
        for color in ("red", "blue")
    ]
    authority.learn_construction(tuple(value.episode.structure_id for value in episodes))
    field = _settlement("comprehend-current", sight="blue")
    assert authority.generate(field).state == "unique"
    correct = authority.comprehend(
        token_authority=tokens,
        sequence=_sequence(tokens, ("blue", "appears"), label="correct"),
        settlement=field,
    )
    wrong = authority.comprehend(
        token_authority=tokens,
        sequence=_sequence(tokens, ("red", "appears"), label="wrong"),
        settlement=field,
    )
    assert correct.reason == "construction_comprehended"
    assert wrong.reason == "sequence_causal_relation_disagrees"


@pytest.mark.parametrize(
    "state", [TokenClassificationState.UNKNOWN, TokenClassificationState.AMBIGUOUS]
)
def test_non_unique_token_classification_is_an_explicit_noop(state) -> None:
    tokens = AuditoryTokenSequenceAuthority(authority_secret=TOKEN_SECRET)
    authority = CausalLanguageConstructionAuthority(authority_key=CONSTRUCTION_SECRET)
    settlement = _settlement(f"classification-{state.value}")
    result = _episode_admission(
        authority,
        tokens,
        _sequence(
            tokens, ("unsettled",), label=state.value, state_overrides={0: state}
        ),
        settlement,
    )
    assert result.state == state.value
    assert not result.stored
    assert authority.working_count == 0


def test_routing_chi_is_irrelevant_but_full_field_change_is_authoritative() -> None:
    tokens = AuditoryTokenSequenceAuthority(authority_secret=TOKEN_SECRET)
    authority = CausalLanguageConstructionAuthority(authority_key=CONSTRUCTION_SECRET)
    first = _admit(
        authority, tokens, ("same",),
        _settlement("chi-a", sight="red", routing_chis=(3,)), "chi-a",
    )
    same_settlement = _settlement(
        "chi-b", sight="red", routing_chis=(91,)
    )
    same = _episode_admission(
        authority,
        tokens,
        _sequence(tokens, ("same",), label="chi-b"),
        same_settlement,
    )
    changed = _admit(
        authority, tokens, ("changed",),
        _settlement("chi-c", sight="blue", routing_chis=(3,)), "chi-c",
    )
    assert same.reason == "duplicate_structure"
    assert same.stored is False
    assert same.episode.structure_id == first.episode.structure_id
    assert same.episode.episode_id != first.episode.episode_id
    assert (
        same.episode.causal_intake_id
        != first.episode.causal_intake_id
    )
    assert changed.episode.structure_id != first.episode.structure_id
    assert all("chi" not in key for key, _value in first.episode.field_roots)


def test_conflict_is_permanently_ambiguous_and_never_voted() -> None:
    tokens = AuditoryTokenSequenceAuthority(authority_secret=TOKEN_SECRET)
    authority = CausalLanguageConstructionAuthority(authority_key=CONSTRUCTION_SECRET)
    first_pair = [
        _admit(
            authority, tokens, (color, "here"),
            _settlement(f"conflict-a-{color}", sight=color), f"conflict-a-{color}",
        )
        for color in ("red", "blue")
    ]
    first = authority.learn_construction(tuple(
        value.episode.structure_id for value in first_pair
    ))
    second_pair = [
        _admit(
            authority, tokens, ("here", color),
            _settlement(f"conflict-b-{color}", sight=color), f"conflict-b-{color}",
        )
        for color in ("red", "blue")
    ]
    second = authority.learn_construction(tuple(
        value.episode.structure_id for value in second_pair
    ))
    assert first.state == "unique"
    assert second.state == "ambiguous"
    assert second.reason == "construction_conflict"
    assert authority.generate(_settlement("conflict-current", sight="red")).state == "unknown"
    restored = CausalLanguageConstructionAuthority(authority_key=CONSTRUCTION_SECRET)
    restored.restore(authority.snapshot())
    assert restored.generate(_settlement("conflict-restored", sight="red")).state == "unknown"


def test_capacity_duplicate_idempotence_and_constant_state() -> None:
    tokens = AuditoryTokenSequenceAuthority(authority_secret=TOKEN_SECRET)
    authority = CausalLanguageConstructionAuthority(
        authority_key=CONSTRUCTION_SECRET, working_capacity=2
    )
    first = _admit(
        authority, tokens, ("one",), _settlement("capacity-one", sight="red"),
        "capacity-one",
    )
    before = _canonical(authority.snapshot())
    for index in range(25):
        duplicate_settlement = _settlement(
            f"duplicate-{index}", sight="red"
        )
        duplicate = _episode_admission(
            authority,
            tokens,
            _sequence(tokens, ("one",), label=f"duplicate-{index}"),
            duplicate_settlement,
        )
        assert duplicate.reason == "duplicate_structure"
    assert _canonical(authority.snapshot()) == before
    _admit(
        authority, tokens, ("two",), _settlement("capacity-two", sight="blue"),
        "capacity-two",
    )
    full_before = _canonical(authority.snapshot())
    refused_settlement = _settlement("capacity-three", sight="green")
    refused = _episode_admission(
        authority,
        tokens,
        _sequence(tokens, ("three",), label="capacity-three"),
        refused_settlement,
    )
    assert refused.reason == "working_capacity_full"
    assert _canonical(authority.snapshot()) == full_before
    assert first.episode is not None


def test_construction_capacity_and_redundant_proof_are_constant_state() -> None:
    tokens = AuditoryTokenSequenceAuthority(authority_secret=TOKEN_SECRET)
    authority = CausalLanguageConstructionAuthority(
        authority_key=CONSTRUCTION_SECRET, construction_capacity=1
    )
    first = [
        _admit(
            authority, tokens, (color, "seen"),
            _settlement(f"construction-cap-{color}", sight=color),
            f"construction-cap-{color}",
        )
        for color in ("red", "blue")
    ]
    learned = authority.learn_construction(tuple(
        value.episode.structure_id for value in first
    ))
    assert learned.state == "unique"
    assert authority.working_count == 0
    learned_state = _canonical(authority.snapshot())

    repeated = [
        _admit(
            authority, tokens, (color, "seen"),
            _settlement(f"construction-repeat-{color}", sight=color),
            f"construction-repeat-{color}",
        )
        for color in ("red", "blue")
    ]
    duplicate = authority.learn_construction(tuple(
        value.episode.structure_id for value in repeated
    ))
    assert duplicate.reason == "construction_duplicate"
    assert authority.working_count == 0
    assert _canonical(authority.snapshot()) == learned_state

    second = [
        _admit(
            authority, tokens, (touch, "felt"),
            _settlement(f"construction-full-{touch}", sight="red", touch=touch),
            f"construction-full-{touch}",
        )
        for touch in ("soft", "hard")
    ]
    before_refusal = _canonical(authority.snapshot())
    refused = authority.learn_construction(tuple(
        value.episode.structure_id for value in second
    ))
    assert refused.reason == "construction_capacity_full"
    assert authority.construction_count == 1
    assert _canonical(authority.snapshot()) == before_refusal


def test_snapshot_restore_is_atomic_and_tamper_evident() -> None:
    tokens = AuditoryTokenSequenceAuthority(authority_secret=TOKEN_SECRET)
    authority = CausalLanguageConstructionAuthority(authority_key=CONSTRUCTION_SECRET)
    episodes = [
        _admit(
            authority, tokens, (color, "visible"),
            _settlement(f"persist-{color}", sight=color), f"persist-{color}",
        )
        for color in ("red", "blue")
    ]
    authority.learn_construction(tuple(value.episode.structure_id for value in episodes))
    snapshot = authority.snapshot()
    restored = CausalLanguageConstructionAuthority(authority_key=CONSTRUCTION_SECRET)
    restored.restore(snapshot)
    assert restored.snapshot() == snapshot
    before = copy.deepcopy(restored.snapshot())
    changed = copy.deepcopy(snapshot)
    changed["payload"]["constructions"][0]["state"] = "ambiguous"
    with pytest.raises(ValueError, match="state authority changed"):
        restored.restore(changed)
    assert restored.snapshot() == before


def test_forbidden_legacy_dependencies_are_absent() -> None:
    import dsf_ai_service.substrate.causal_language_construction as module

    tree = ast.parse(inspect.getsource(module))
    imported = {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module is not None
    }
    assert not any(
        forbidden in module_name
        for module_name in imported
        for forbidden in (
            "assemblage", "language_fact", "atlas", "gualaloom_v5_engine"
        )
    )
    source = inspect.getsource(module)
    assert "routing_chis" not in inspect.getsource(
        CausalLanguageConstructionAuthority._learn_locked
    )
    assert all(term not in source for term in ("recall_fast(", "most_common(", "np."))

def test_intake_is_required_embedded_persistent_and_tamper_evident() -> None:
    tokens = AuditoryTokenSequenceAuthority(authority_secret=TOKEN_SECRET)
    authority = CausalLanguageConstructionAuthority(
        authority_key=CONSTRUCTION_SECRET
    )
    settlement = _settlement("intake-proof", sight="red")
    sequence = _sequence(tokens, ("red", "appears"), label="intake-proof")
    intake_authority, intake = _intake(sequence, settlement)
    admitted = authority.admit_episode(
        intake_authority=intake_authority,
        intake=intake,
        token_authority=tokens,
        sequence=sequence,
        settlement=settlement,
    )
    assert admitted.state == "unique"
    record = admitted.episode.as_record()
    assert record["causal_intake_id"] == intake.intake_id
    assert record["causal_intake_record"] == intake.as_record()
    snapshot = authority.snapshot()
    restored = CausalLanguageConstructionAuthority(
        authority_key=CONSTRUCTION_SECRET
    )
    restored.restore(snapshot)
    assert restored.snapshot() == snapshot

    tampered = copy.deepcopy(intake.as_record())
    tampered["entries"][0]["source_sample_end"] += 1
    changed = AuditoryBatchCausalIntakeReceipt.from_record(tampered)
    with pytest.raises(ValueError, match="clocks disagree|identity changed|authority changed"):
        authority.admit_episode(
            intake_authority=intake_authority,
            intake=changed,
            token_authority=tokens,
            sequence=sequence,
            settlement=settlement,
        )


def test_sound_carrier_and_boundary_relation_are_witnessed_not_referents() -> None:
    import dsf_ai_service.substrate.causal_language_construction as module

    tokens = AuditoryTokenSequenceAuthority(authority_secret=TOKEN_SECRET)
    authority = CausalLanguageConstructionAuthority(
        authority_key=CONSTRUCTION_SECRET
    )
    red = _admit(
        authority,
        tokens,
        ("red", "first"),
        _settlement("carrier-red", sight="red", sound="carrier-a"),
        "carrier-red",
    )
    blue = _admit(
        authority,
        tokens,
        ("blue", "first"),
        _settlement("carrier-blue", sight="blue", sound="carrier-b"),
        "carrier-blue",
    )
    assert red.episode.settlement_witness["interpretations"][1][
        "sense"
    ] == "sound"
    assert red.episode.settlement_witness != blue.episode.settlement_witness
    assert all(
        not key.startswith("sense:sound")
        for key, _value in red.episode.field_roots
    )
    learned = authority.learn_construction((
        red.episode.structure_id,
        blue.episode.structure_id,
    ))
    assert learned.state == "unique"
    assert learned.construction.elements[0].kind == "slot"

    witness = copy.deepcopy(red.episode.settlement_witness)
    roots_before = module._field_roots(witness)
    for sense in witness["interpretations"]:
        sense["relation"] = "structural_change"
    assert module._field_roots(witness) == roots_before


def test_settlement_learns_only_the_whole_complete_contrast_component() -> None:
    tokens = AuditoryTokenSequenceAuthority(authority_secret=TOKEN_SECRET)
    authority = CausalLanguageConstructionAuthority(
        authority_key=CONSTRUCTION_SECRET
    )
    episodes = []
    for sight, touch in (
        ("red", "soft"),
        ("blue", "soft"),
        ("red", "hard"),
        ("blue", "hard"),
        ("green", "soft"),
    ):
        episodes.append(_admit(
            authority,
            tokens,
            (sight, "is", touch),
            _settlement(
                f"whole-component-{sight}-{touch}",
                sight=sight,
                touch=touch,
            ),
            f"whole-component-{sight}-{touch}",
        ))

    before = authority.snapshot()
    results = authority.settle_complete_constructions()

    assert len(results) == 1
    assert results[0].state == "unknown"
    assert results[0].reason == "independence_lattice_incomplete"
    assert authority.snapshot() == before
    assert authority.construction_count == 0
    assert authority.working_count == 5


def test_settlement_expands_a_narrow_proof_without_overlap() -> None:
    tokens = AuditoryTokenSequenceAuthority(authority_secret=TOKEN_SECRET)
    authority = CausalLanguageConstructionAuthority(
        authority_key=CONSTRUCTION_SECRET
    )
    for sight in ("red", "blue"):
        _admit(
            authority,
            tokens,
            (sight, "is", "soft"),
            _settlement(
                f"narrow-{sight}", sight=sight, touch="soft"
            ),
            f"narrow-{sight}",
        )
    first = authority.settle_complete_constructions()
    assert len(first) == 1
    assert first[0].reason == "construction_learned"
    narrow_id = first[0].construction.construction_id
    assert authority.construction_count == 1

    for sight in ("red", "blue"):
        _admit(
            authority,
            tokens,
            (sight, "is", "hard"),
            _settlement(
                f"broad-{sight}", sight=sight, touch="hard"
            ),
            f"broad-{sight}",
        )
    expanded = authority.settle_complete_constructions()

    assert len(expanded) == 1
    assert expanded[0].state == "unique"
    assert expanded[0].reason == "construction_expanded"
    assert expanded[0].construction.construction_id != narrow_id
    assert [value.kind for value in expanded[0].construction.elements] == [
        "slot", "fixed", "slot"
    ]
    assert len(expanded[0].construction.proof_episodes) == 4
    assert authority.construction_count == 1
    assert authority.working_count == 0
    generated = authority.generate(
        _settlement("expanded-current", sight="blue", touch="hard")
    )
    assert generated.state == "unique"
    assert tuple(value.token_form for value in generated.tokens) == (
        "blue", "is", "hard"
    )

    snapshot = authority.snapshot()
    restored = CausalLanguageConstructionAuthority(
        authority_key=CONSTRUCTION_SECRET
    )
    restored.restore(snapshot)
    assert restored.snapshot() == snapshot
    assert restored.generate(
        _settlement("expanded-restored", sight="red", touch="soft")
    ).state == "unique"


def test_settlement_rejects_overlap_that_is_not_structural_subsumption() -> None:
    tokens = AuditoryTokenSequenceAuthority(authority_secret=TOKEN_SECRET)
    authority = CausalLanguageConstructionAuthority(
        authority_key=CONSTRUCTION_SECRET
    )
    for sight in ("red", "blue"):
        _admit(
            authority,
            tokens,
            (sight, "here"),
            _settlement(f"overlap-first-{sight}", sight=sight),
            f"overlap-first-{sight}",
        )
    learned = authority.settle_complete_constructions()
    assert learned[0].reason == "construction_learned"
    original = authority.snapshot()

    for sight in ("red", "blue"):
        _admit(
            authority,
            tokens,
            ("here", sight),
            _settlement(f"overlap-second-{sight}", sight=sight),
            f"overlap-second-{sight}",
        )
    before_refusal = authority.snapshot()
    refused = authority.settle_complete_constructions()

    assert len(refused) == 1
    assert refused[0].state == "ambiguous"
    assert refused[0].reason == "construction_overlap_not_subsumed"
    assert authority.snapshot() == before_refusal
    assert authority.construction_count == 1
    assert authority.working_count == 2
    assert original["payload"]["constructions"] == (
        authority.snapshot()["payload"]["constructions"]
    )


def test_settlement_result_and_expansion_proof_stay_inside_episode_boundary() -> None:
    tokens = AuditoryTokenSequenceAuthority(authority_secret=TOKEN_SECRET)
    authority = CausalLanguageConstructionAuthority(
        authority_key=CONSTRUCTION_SECRET
    )
    colors = tuple(f"color-{index}" for index in range(8))
    for color in colors:
        _admit(
            authority,
            tokens,
            (color, "seen"),
            _settlement(f"boundary-{color}", sight=color),
            f"boundary-{color}",
        )
    settled = authority.settle_complete_constructions()
    assert len(settled) == 1
    assert settled[0].reason == "construction_learned"
    assert len(settled[0].construction.proof_episodes) == 8

    _admit(
        authority,
        tokens,
        ("color-8", "seen"),
        _settlement("boundary-color-8", sight="color-8"),
        "boundary-color-8",
    )
    before = authority.snapshot()
    refused = authority.settle_complete_constructions()

    assert len(refused) == 1
    assert refused[0].reason == "contrast_lattice_exceeds_episode_boundary"
    assert authority.snapshot() == before
    assert authority.construction_count == 1
    assert authority.working_count == 1


def test_settlement_reverifies_retained_episode_hmac_before_consolidation() -> None:
    import dsf_ai_service.substrate.causal_language_construction as module

    tokens = AuditoryTokenSequenceAuthority(authority_secret=TOKEN_SECRET)
    authority = CausalLanguageConstructionAuthority(
        authority_key=CONSTRUCTION_SECRET
    )
    for sight in ("red", "blue"):
        _admit(
            authority,
            tokens,
            (sight, "appears"),
            _settlement(f"reverify-{sight}", sight=sight),
            f"reverify-{sight}",
        )
    authority.settle_complete_constructions()
    _admit(
        authority,
        tokens,
        ("green", "appears"),
        _settlement("reverify-green", sight="green"),
        "reverify-green",
    )

    construction = next(iter(authority._constructions.values()))
    damaged_proof = copy.deepcopy(construction.proof_episodes)
    damaged_proof[0]["tokens"][0]["token_form"] = "forged"
    payload = {
        **construction.payload(),
        "proof_episodes": damaged_proof,
    }
    damaged = module.LearnedConstruction(
        construction_id=construction.construction_id,
        family_id=construction.family_id,
        state=construction.state,
        elements=construction.elements,
        background_roots=construction.background_roots,
        proof_episodes=tuple(damaged_proof),
        authority_hmac_sha256=module._sign(
            authority._construction_key,
            module.CONSTRUCTION_DOMAIN,
            payload,
        ),
    )
    authority._constructions[construction.construction_id] = damaged
    before_working = tuple(authority._working)

    with pytest.raises(ValueError, match="episode authority changed"):
        authority.settle_complete_constructions()

    assert tuple(authority._working) == before_working
    assert authority.working_count == 1
