import json
from concurrent.futures import ThreadPoolExecutor

import pytest

from dsf_ai_service.gualaloom_engine import P3I, TRITS, encode
from dsf_ai_service.substrate.language_fact_strand import (
    DSF_FIELD_NAMES,
    BindingWindowCitation,
    FactProvenance,
    LanguageFactMemory,
    RecallReason,
    RecallStatus,
    canonical_l6_direction,
    compare_reciprocally,
    construct_language_fact_strand,
)
from dsf_ai_service.v4.gualaloom_v4_krimelack_dna import LanguageKrimelack
from dsf_ai_service.v4.gualaloom_v4_uf_kernel import compute_dsf


def _grounded_provenance(origin="emulated"):
    return FactProvenance(
        source_tag="story_emulator" if origin == "emulated" else "embodied_sensor",
        trace_id="trace-17",
        windows=(
            BindingWindowCitation(
                window_id="win-17",
                experience_origin=origin,
                modalities=("word", "sight", "sound"),
            ),
        ),
    )


def test_balanced_ternary_preserves_3_to_i_identity_and_unknown_mask():
    fact = construct_language_fact_strand("listen")

    for char_index, char in enumerate(fact.language_form):
        start = char_index * TRITS
        strand = fact.trits[start:start + TRITS]
        assert strand == encode(char)
        assert sum(trit * P3I[position] for position, trit in enumerate(strand)) == ord(char) - 96

    # "i" is balanced ternary (0, 0, +1): its low zeros are valid
    # quiescence; unused high places are unknown/invalid, not another zero.
    i_start = fact.language_form.index("i") * TRITS
    assert fact.trits[i_start:i_start + 3] == (0, 0, 1)
    assert fact.validity_mask[i_start:i_start + 3] == (True, True, True)
    assert fact.trits[i_start + 3] == 0
    assert fact.validity_mask[i_start + 3] is False


def test_constructor_uses_real_language_krimelack_events_and_full_dsf():
    fact = construct_language_fact_strand("memory")
    krimelack = LanguageKrimelack()
    krimelack.transduce("memory")
    expected_events = tuple(
        (float(event["t"]), int(event["dw"]), float(event["s"]))
        for event in krimelack.events
    )
    assert tuple((event.t, event.dw, event.s) for event in fact.events) == expected_events

    expected_dsf = compute_dsf(list(krimelack.events))
    assert tuple(fact.dsf.to_dict()) == DSF_FIELD_NAMES
    for field_name in DSF_FIELD_NAMES:
        assert getattr(fact.dsf, field_name) == getattr(expected_dsf, field_name)

    assert fact.topology.chi == fact.topology.vertices - fact.topology.edges


def test_fact_and_memory_json_round_trip_without_field_loss():
    fact = construct_language_fact_strand(
        "experience",
        provenance=_grounded_provenance("emulated"),
    )
    restored_fact = type(fact).from_json(fact.to_json())
    assert restored_fact == fact
    assert set(json.loads(fact.to_json())["dsf"]) == set(DSF_FIELD_NAMES)

    memory = LanguageFactMemory((fact,))
    restored_memory = LanguageFactMemory.from_json(memory.to_json())
    assert len(restored_memory) == 1
    result = restored_memory.recall(construct_language_fact_strand("experience"))
    assert result.status is RecallStatus.MATCH
    assert result.matched_strands == (fact,)


def test_unique_bidirectional_l6_class_recognizes_without_label_index():
    remembered = construct_language_fact_strand(
        "reciprocity",
        provenance=_grounded_provenance("observed"),
    )
    query = construct_language_fact_strand("reciprocity")
    memory = LanguageFactMemory((remembered,))

    result = memory.recall(query)
    comparison = compare_reciprocally(query, remembered)

    assert result.status is RecallStatus.MATCH
    assert result.reason is RecallReason.UNIQUE_RECIPROCAL_CLASS
    assert comparison.prerequisite_fields_equal is True
    assert comparison.forward.locked is True
    assert comparison.reverse.locked is True
    assert result.matched_strands[0].language_form == "reciprocity"


def test_canonical_l6_uses_ceil_boundary_not_legacy_rounding():
    # n_eff=1 and ceil(4/e)=2, therefore the canonical law locks.  The
    # legacy round(4/e)=1 implementation would incorrectly reject it.
    direction = canonical_l6_direction(
        dimensions=4,
        matching_non_null=3,
        matching_quiescent=0,
    )

    assert direction.dimensions == 4
    assert direction.matching_non_null == 3
    assert direction.effective_dimensions == 1
    assert direction.knee == 2
    assert direction.locked is True


def test_valid_quiescent_zero_constrains_reciprocity_instead_of_becoming_unknown():
    query = construct_language_fact_strand("i")
    remembered = construct_language_fact_strand(
        "i", provenance=FactProvenance(source_tag="quiescent-proof")
    )

    comparison = compare_reciprocally(query, remembered)
    result = LanguageFactMemory((remembered,)).recall(query)

    assert comparison.forward.matching_non_null == 1
    assert comparison.forward.matching_quiescent == 2
    assert comparison.forward.effective_dimensions == 0
    assert comparison.forward.locked is True
    assert comparison.reverse.locked is True
    assert result.recognized is True


def test_zero_evidence_and_absent_structure_are_honest_unknowns():
    memory = LanguageFactMemory(
        (construct_language_fact_strand("reciprocity", provenance=_grounded_provenance()),)
    )

    zero = memory.recall(construct_language_fact_strand(""))
    absent = memory.recall(construct_language_fact_strand("unremembered"))

    assert zero.status is RecallStatus.UNKNOWN
    assert zero.reason is RecallReason.ZERO_EVIDENCE
    assert absent.status is RecallStatus.UNKNOWN
    assert absent.reason is RecallReason.NO_STRUCTURAL_CANDIDATE
    with pytest.raises(ValueError, match="zero-evidence"):
        memory.remember(construct_language_fact_strand(""))


def test_repeated_episodes_form_one_structural_class_not_false_ambiguity():
    emulated = construct_language_fact_strand(
        "reciprocity",
        provenance=_grounded_provenance("emulated"),
    )
    observed = construct_language_fact_strand(
        "reciprocity",
        provenance=_grounded_provenance("observed"),
    )
    memory = LanguageFactMemory((emulated, observed))

    result = memory.recall(construct_language_fact_strand("reciprocity"))

    assert result.status is RecallStatus.MATCH
    assert len(result.matched_strands) == 2
    assert {window.experience_origin for window in result.meaning_windows} == {
        "emulated",
        "observed",
    }


def test_multiple_distinct_bidirectional_locks_are_unknown_not_first_match():
    # These two real LanguageKrimelack constructions share the same event,
    # chi, and full-DSF prerequisites and each L6-locks reciprocally with the
    # query, while their balanced-ternary structures remain distinct.
    query = construct_language_fact_strand("aeu")
    same_class = construct_language_fact_strand(
        "aeu", provenance=FactProvenance(source_tag="episode-one")
    )
    other_class = construct_language_fact_strand(
        "aeo", provenance=FactProvenance(source_tag="episode-two")
    )
    assert same_class.reciprocity_fingerprint == other_class.reciprocity_fingerprint
    assert same_class.structural_fingerprint != other_class.structural_fingerprint
    assert compare_reciprocally(query, same_class).bidirectionally_locked is True
    assert compare_reciprocally(query, other_class).bidirectionally_locked is True

    result = LanguageFactMemory((same_class, other_class)).recall(query)

    assert result.status is RecallStatus.UNKNOWN
    assert result.reason is RecallReason.AMBIGUOUS_RECIPROCAL_CLASSES
    assert result.matched_strands == ()


def test_recognition_does_not_claim_meaning_without_multimodal_window():
    no_window = construct_language_fact_strand(
        "reciprocity",
        provenance=FactProvenance(source_tag="typed_text"),
    )
    word_only = construct_language_fact_strand(
        "reciprocity",
        provenance=FactProvenance(
            source_tag="story_emulator",
            windows=(
                BindingWindowCitation(
                    window_id="win-word-only",
                    experience_origin="emulated",
                    modalities=("word",),
                ),
            ),
        ),
    )

    no_window_result = LanguageFactMemory((no_window,)).recall(
        construct_language_fact_strand("reciprocity")
    )
    word_only_result = LanguageFactMemory((word_only,)).recall(
        construct_language_fact_strand("reciprocity")
    )

    assert no_window_result.recognized is True
    assert no_window_result.meaning_grounded is False
    assert word_only_result.recognized is True
    assert word_only_result.meaning_grounded is False


@pytest.mark.parametrize("origin", ["emulated", "observed"])
def test_multimodal_window_citation_is_explicit_meaning_evidence(origin):
    fact = construct_language_fact_strand(
        "reciprocity",
        provenance=_grounded_provenance(origin),
    )
    result = LanguageFactMemory((fact,)).recall(
        construct_language_fact_strand("reciprocity")
    )

    assert result.recognized is True
    assert result.meaning_grounded is True
    assert result.meaning_windows[0].experience_origin == origin


def test_invalid_experience_origin_fails_loudly():
    with pytest.raises(ValueError, match="emulated.*observed"):
        BindingWindowCitation(
            window_id="win-hidden",
            experience_origin="synthetic-but-unlabeled",
            modalities=("word", "sight"),
        )


def test_json_tampering_cannot_turn_hash_or_label_into_match_authority():
    fact = construct_language_fact_strand("reciprocity")
    payload = json.loads(fact.to_json())
    payload["language_form"] = "recognition"

    with pytest.raises(ValueError, match="language_form and balanced-ternary"):
        type(fact).from_json(json.dumps(payload))


def test_json_validity_mask_rejects_non_boolean_values():
    fact = construct_language_fact_strand("reciprocity")
    payload = json.loads(fact.to_json())
    payload["validity_mask"][0] = 0

    with pytest.raises(ValueError, match="validity_mask entries.*booleans"):
        type(fact).from_json(json.dumps(payload))


def test_unsupported_unicode_cannot_silently_truncate_3_to_i_structure():
    with pytest.raises(ValueError, match="exceeds the canonical"):
        construct_language_fact_strand("🧠")


def test_memory_remember_recall_and_serialization_are_thread_safe():
    facts = tuple(
        construct_language_fact_strand(
            "reciprocity", provenance=FactProvenance(source_tag=f"episode-{index}")
        )
        for index in range(33)
    )
    query = construct_language_fact_strand("reciprocity")
    memory = LanguageFactMemory((facts[0],))

    def remember(fact):
        return memory.remember(fact)

    def recall(_index):
        return memory.recall(query).status

    with ThreadPoolExecutor(max_workers=12) as executor:
        remember_results = tuple(executor.map(remember, facts))
        recall_results = tuple(executor.map(recall, range(64)))
        serialized = tuple(executor.map(lambda _index: memory.to_json(), range(8)))

    assert remember_results[0] is False
    assert all(remember_results[1:])
    assert all(status is RecallStatus.MATCH for status in recall_results)
    assert len(memory) == len(facts)
    assert all(len(LanguageFactMemory.from_json(value)) == len(facts) for value in serialized)
