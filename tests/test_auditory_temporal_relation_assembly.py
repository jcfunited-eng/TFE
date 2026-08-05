from __future__ import annotations

import hashlib
import json
from dataclasses import replace
from fractions import Fraction

import pytest

from dsf_ai_service.glew_runtime.global_uf import DSF_FIELD_ORDER
from dsf_ai_service.substrate.auditory_full_field_occurrence_validation import (
    validate_auditory_full_field_occurrence,
)
from dsf_ai_service.substrate.auditory_live_motif import (
    AuditoryLiveMotifResult,
)
from dsf_ai_service.substrate.auditory_recurrent_motif import (
    AuditoryMotifActivation,
    AuditoryReceptorIdentity,
    AuditoryReceptorOccurrence,
)
from dsf_ai_service.substrate.auditory_temporal_relation_assembly import (
    AuditoryTemporalAssemblyProfile,
    AuditoryTemporalRelationAssemblyOwner,
    TemporalAssemblyFiringState,
    _digest,
)
from dsf_ai_service.substrate.senses.auditory_full_field_provider import (
    AUDITORY_CHANNELS,
)


KEY = b"auditory-temporal-relation-test-authority"


def _sha(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _profile(**changes) -> AuditoryTemporalAssemblyProfile:
    values = {
        "profile_id": "exact-presemantic-temporal-test",
        "max_exposures": 16,
        "max_events_per_exposure": 16,
        "max_assemblies": 4,
        "max_relations_per_assembly": 64,
        "max_state_bytes": 8 * 1024 * 1024,
    }
    values.update(changes)
    return AuditoryTemporalAssemblyProfile.create(**values)


def _occurrence(
    name: str,
    *,
    index: int,
    start: Fraction,
    end: Fraction,
) -> AuditoryReceptorOccurrence:
    receptor = AuditoryReceptorIdentity(
        cochlear_index=0,
        channel_id=AUDITORY_CHANNELS[0].name,
        winding_direction=1,
    )
    fields = tuple(
        (field, Fraction(index + offset + 1, 100))
        for offset, field in enumerate(DSF_FIELD_ORDER)
    )
    draft = AuditoryReceptorOccurrence(
        receptor=receptor,
        source_index=index,
        source_time=start,
        causal_interval_end=end,
        winding_delta=1,
        pressure_fields=fields,
        phase_fields=tuple(
            (field, value + 1) for field, value in fields
        ),
        pressure_field_receipt_sha256=_sha(f"{name}-pressure"),
        phase_field_receipt_sha256=_sha(f"{name}-phase"),
        authority_receipt_sha256="0" * 64,
    )
    result = replace(
        draft,
        authority_receipt_sha256=_digest(draft.payload()),
    )
    result.verify()
    return result


def _result(
    name: str,
    events: tuple[tuple[str, Fraction, Fraction], ...],
) -> AuditoryLiveMotifResult:
    activations = []
    for index, (identity, start, end) in enumerate(events):
        occurrence = _occurrence(
            f"{name}-{identity}-{index}",
            index=index,
            start=start,
            end=end,
        )
        activations.append(AuditoryMotifActivation(
            neuron_id=_sha(identity),
            segment_index=0,
            state_ordinal_start=index,
            state_ordinal_end=index + 1,
            source_index_start=index,
            source_index_end=index,
            source_time_start=start,
            source_time_end=end,
            full_field_occurrences=(occurrence,),
        ))
    draft = AuditoryLiveMotifResult(
        source_receptor_event_receipt_sha256=_sha(f"{name}-event"),
        source_experience_receipt_sha256=_sha(f"{name}-experience"),
        firing_state="observed",
        learning_state="observed",
        firing_motif_neuron_ids=tuple(sorted({
            value.neuron_id for value in activations
        })),
        learning_firing_motif_neuron_ids=tuple(sorted({
            value.neuron_id for value in activations
        })),
        newly_grown_motif_neuron_ids=(),
        reinforced_motif_neuron_ids=(),
        unresolved_source_indices=(),
        firing_work_cells=len(activations),
        learning_work_cells=len(activations),
        firing_reason="exact synthetic activation witness",
        learning_reason="exact synthetic activation witness",
        activation_spans=(),
        internal_activations=tuple(activations),
        authority_receipt_sha256="0" * 64,
    )
    from dsf_ai_service.substrate.auditory_live_motif import (
        _activation_payload,
    )
    draft = replace(
        draft,
        activation_spans=tuple(
            _activation_payload(value) for value in activations
        ),
    )
    result = replace(
        draft,
        authority_receipt_sha256=hashlib.sha256(
            json.dumps(
                draft.payload(),
                allow_nan=False,
                separators=(",", ":"),
                sort_keys=True,
            ).encode("utf-8")
        ).hexdigest(),
    )
    result.verify()
    return result


def _learned_owner():
    owner = AuditoryTemporalRelationAssemblyOwner(
        profile=_profile(),
        authority_key=KEY,
    )
    a1 = _result("a1", (
        ("x", Fraction(0), Fraction(1)),
        ("room-a", Fraction(1, 2), Fraction(3, 4)),
        ("y", Fraction(2), Fraction(3)),
    ))
    a2 = _result("a2", (
        ("x", Fraction(0), Fraction(1)),
        ("room-b", Fraction(5, 4), Fraction(3, 2)),
        ("y", Fraction(2), Fraction(3)),
    ))
    b1 = _result("b1", (
        ("p", Fraction(0), Fraction(1)),
        ("q", Fraction(2), Fraction(3)),
    ))
    b2 = _result("b2", (
        ("p", Fraction(0), Fraction(1)),
        ("q", Fraction(2), Fraction(3)),
    ))
    room = _result("room", (
        ("room-a", Fraction(0), Fraction(1)),
        ("room-b", Fraction(2), Fraction(3)),
    ))
    values = (a1, a2, b1, b2, room)
    for index, value in enumerate(values):
        owner.observe_typed(
            value,
            source_component_receipt_sha256s=(
                _sha(f"physical-source-{index}"),
            ),
        )
    assembly_a = owner.learn_acoustic_contrast(
        positive_exposure_receipt_sha256s=(
            a1.source_experience_receipt_sha256,
            a2.source_experience_receipt_sha256,
        ),
        contrast_exposure_receipt_sha256s=(
            b1.source_experience_receipt_sha256,
            b2.source_experience_receipt_sha256,
            room.source_experience_receipt_sha256,
        ),
    )
    assembly_b = owner.learn_acoustic_contrast(
        positive_exposure_receipt_sha256s=(
            b1.source_experience_receipt_sha256,
            b2.source_experience_receipt_sha256,
        ),
        contrast_exposure_receipt_sha256s=(
            a1.source_experience_receipt_sha256,
            a2.source_experience_receipt_sha256,
            room.source_experience_receipt_sha256,
        ),
    )
    assert assembly_a is not None and assembly_b is not None
    return owner, assembly_a, assembly_b


def test_complete_relations_survive_interleaving_and_competing_are_ambiguous():
    owner, assembly_a, assembly_b = _learned_owner()
    mixed = _result("mixed", (
        ("x", Fraction(0), Fraction(1)),
        ("p", Fraction(1, 4), Fraction(5, 4)),
        ("unrelated", Fraction(3, 2), Fraction(7, 4)),
        ("y", Fraction(2), Fraction(3)),
        ("q", Fraction(9, 4), Fraction(13, 4)),
    ))

    firing = owner.fire(mixed.as_record())

    assert firing.state is TemporalAssemblyFiringState.AMBIGUOUS
    assert firing.complete_assembly_ids == tuple(sorted((
        assembly_a.assembly_id,
        assembly_b.assembly_id,
    )))


def test_partial_and_unrelated_relations_remain_unknown():
    owner, _assembly_a, _assembly_b = _learned_owner()
    partial = _result("partial", (
        ("x", Fraction(0), Fraction(1)),
    ))
    unrelated = _result("unrelated", (
        ("u", Fraction(0), Fraction(1)),
        ("v", Fraction(2), Fraction(3)),
    ))

    assert owner.fire(partial.as_record()).state is (
        TemporalAssemblyFiringState.UNKNOWN
    )
    assert owner.fire(unrelated.as_record()).state is (
        TemporalAssemblyFiringState.UNKNOWN
    )


def test_cold_restore_keeps_resolvable_full_fields_and_rejects_tamper():
    owner, assembly_a, assembly_b = _learned_owner()
    encoded = owner.snapshot_encoded()
    restored = AuditoryTemporalRelationAssemblyOwner.restore_encoded(
        encoded,
        authority_key=KEY,
    )
    assert restored.snapshot_encoded() == encoded
    assert restored.status() == owner.status()
    assert restored.status()["assembly_count"] == 2
    assert {
        assembly_a.assembly_id,
        assembly_b.assembly_id,
    }
    mixed = _result("restored-mixed", (
        ("x", Fraction(0), Fraction(1)),
        ("p", Fraction(1, 4), Fraction(5, 4)),
        ("room-after-restore", Fraction(3, 2), Fraction(7, 4)),
        ("y", Fraction(2), Fraction(3)),
        ("q", Fraction(9, 4), Fraction(13, 4)),
    ))
    assert restored.fire(mixed.as_record()) == owner.fire(
        mixed.as_record()
    )
    changed = bytearray(encoded)
    changed[-10] ^= 1
    with pytest.raises(ValueError):
        AuditoryTemporalRelationAssemblyOwner.restore_encoded(
            bytes(changed),
            authority_key=KEY,
        )


def test_full_pressure_phase_fields_and_receipts_refuse_tamper():
    occurrence = _occurrence(
        "tamper",
        index=7,
        start=Fraction(1),
        end=Fraction(2),
    )
    record = occurrence.payload() | {
        "authority_receipt_sha256": occurrence.authority_receipt_sha256,
    }
    validate_auditory_full_field_occurrence(record)

    for field in ("pressure_fields", "phase_fields"):
        changed = json.loads(json.dumps(record))
        changed[field][0][1] = "999"
        with pytest.raises(ValueError):
            validate_auditory_full_field_occurrence(changed)

    for field in (
        "pressure_field_receipt_sha256",
        "phase_field_receipt_sha256",
    ):
        changed = json.loads(json.dumps(record))
        changed[field] = "0" * 64
        with pytest.raises(ValueError):
            validate_auditory_full_field_occurrence(changed)


def test_canonical_l6_selects_recurrent_cells_and_locks_without_tuning():
    owner = AuditoryTemporalRelationAssemblyOwner(
        profile=_profile(max_exposures=8),
        authority_key=KEY,
    )
    positives = tuple(
        _result(f"l6-positive-{index}", tuple(
            (identity, Fraction(ordinal * 2), Fraction(ordinal * 2 + 1))
            for ordinal, identity in enumerate(
                (
                    "stable-a",
                    "stable-b",
                    "stable-c",
                    "stable-d",
                    *((f"incidental-{index}",) if index == 4 else ()),
                )
            )
            if not (identity == "stable-d" and index == 4)
        ))
        for index in range(5)
    )
    contrasts = (
        _result("l6-contrast-1", (
            ("contrast-only", Fraction(0), Fraction(1)),
        )),
        _result("l6-contrast-2", (
            ("contrast-only", Fraction(0), Fraction(1)),
        )),
    )
    for index, value in enumerate(positives + contrasts):
        owner.observe_typed(
            value,
            source_component_receipt_sha256s=(
                _sha(f"l6-source-{index}"),
            ),
        )
    assembly = owner.learn_acoustic_contrast(
        positive_exposure_receipt_sha256s=tuple(
            value.source_experience_receipt_sha256
            for value in positives
        ),
        contrast_exposure_receipt_sha256s=tuple(
            value.source_experience_receipt_sha256
            for value in contrasts
        ),
    )
    assert assembly is not None
    assert tuple(
        value.neuron_id for value in assembly.required_event_identities
    ) == tuple(sorted((
        _sha("stable-a"),
        _sha("stable-b"),
        _sha("stable-c"),
        _sha("stable-d"),
    )))

    locked = _result("l6-locked-challenge", (
        ("stable-a", Fraction(0), Fraction(1)),
        ("stable-b", Fraction(2), Fraction(3)),
        ("stable-c", Fraction(4), Fraction(5)),
    ))
    unresolved = _result("l6-unresolved-challenge", (
        ("stable-a", Fraction(0), Fraction(1)),
        ("stable-b", Fraction(2), Fraction(3)),
    ))
    locked_firing = owner.fire(locked.as_record())
    unresolved_firing = owner.fire(unresolved.as_record())
    assert locked_firing.state is TemporalAssemblyFiringState.OBSERVED
    assert locked_firing.l6_directions[0] == {
        "assembly_id": assembly.assembly_id,
        "dimensions": 4,
        "effective_dimensions": 1,
        "knee": 2,
        "locked": True,
        "matching_non_null": 3,
        "matching_quiescent": 0,
    }
    assert unresolved_firing.state is TemporalAssemblyFiringState.UNKNOWN


def test_source_reuse_and_capacity_fail_closed():
    owner = AuditoryTemporalRelationAssemblyOwner(
        profile=_profile(max_exposures=3),
        authority_key=KEY,
    )
    one = _result("one", (
        ("x", Fraction(0), Fraction(1)),
        ("y", Fraction(2), Fraction(3)),
    ))
    two = _result("two", (
        ("x", Fraction(0), Fraction(1)),
        ("y", Fraction(2), Fraction(3)),
    ))
    contrast = _result("source-reuse-contrast", (
        ("u", Fraction(0), Fraction(1)),
    ))
    shared = (_sha("same-physical-source"),)
    owner.observe_typed(
        one,
        source_component_receipt_sha256s=shared,
    )
    owner.observe_typed(
        two,
        source_component_receipt_sha256s=shared,
    )
    owner.observe_typed(
        contrast,
        source_component_receipt_sha256s=(
            _sha("contrast-physical-source"),
        ),
    )
    with pytest.raises(ValueError, match="not source-disjoint"):
        owner.learn_acoustic_contrast(
            positive_exposure_receipt_sha256s=(
                one.source_experience_receipt_sha256,
                two.source_experience_receipt_sha256,
                ),
                contrast_exposure_receipt_sha256s=(
                    contrast.source_experience_receipt_sha256,
                ),
        )
    third = _result("third", (
        ("u", Fraction(0), Fraction(1)),
    ))
    with pytest.raises(RuntimeError, match="capacity exhausted"):
        owner.observe_typed(
            third,
            source_component_receipt_sha256s=(_sha("third-source"),),
        )
