"""Focused conformance tests for exact remembered-expression output."""

from __future__ import annotations

import json
from dataclasses import replace
from fractions import Fraction

import pytest

from dsf_ai_service.glew_runtime.commit import (
    closed_experience_seal_receipt_payload,
)
from dsf_ai_service.glew_runtime.language import encode_balanced_ternary_scalar
from dsf_ai_service.glew_runtime.model import (
    ReceiptError,
    ReceiptRegistry,
    receipt_sha256,
)
from dsf_ai_service.glew_runtime.output import (
    CommittedMotifEvent,
    MotifBindingBank,
    MotifEventKind,
    MotifOutputBinding,
    OutputBindingKind,
    OutputReason,
    OutputStatus,
    RememberedExpressionActuator,
    StageDisposition,
    committed_motif_event_receipt_payload,
    decode_balanced_ternary_scalar,
    expression_close_authority_receipt_payload,
    motif_binding_bank_receipt_payload,
    motif_output_binding_receipt_payload,
)


class _ReceiptWorld:
    def __init__(self, name: str) -> None:
        self.profile_payload = f"profile:{name}".encode()
        self.profile_sha256 = receipt_sha256(self.profile_payload)
        self._payloads: dict[str, bytes] = {
            self.profile_sha256: self.profile_payload
        }

    def fact(self, name: str) -> str:
        return self.mount(f"fact:{name}".encode())

    def mount(self, payload: bytes) -> str:
        digest = receipt_sha256(payload)
        self._payloads[digest] = payload
        return digest

    def _transport_evidence(self, name: str, lane_id: str) -> str:
        payload = json.dumps(
            {
                "lane_id": lane_id,
                "schema": "glew.field.transport_evidence.v1",
            },
            allow_nan=False,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
        return self.mount(payload)

    def sensory(self, name: str) -> tuple[str, ...]:
        return tuple(
            sorted(
                self._transport_evidence(
                    f"{name}:sense:{index}",
                    f"sense-{index}",
                )
                for index in range(3)
            )
        )

    def closed_experience(
        self,
        name: str,
        sensory: tuple[str, ...],
    ) -> str:
        language = self._transport_evidence(f"{name}:language", "language")
        payload = closed_experience_seal_receipt_payload(
            experience_id=f"{name}:closed-experience",
            topology_authority_receipt_sha256=self.fact(f"{name}:topology"),
            input_expression_receipt_sha256=self.fact(f"{name}:expression"),
            recognition_receipt_sha256=self.fact(f"{name}:recognition"),
            ordered_evidence_receipt_sha256s=(language, *sensory),
            source_time_start=Fraction(0),
            source_time_end=Fraction(1),
            structural_time_unit="structural_second",
        )
        return self.mount(payload)

    def registry(self) -> ReceiptRegistry:
        return ReceiptRegistry.from_payloads(
            profile_payload=self.profile_payload,
            receipt_payloads=tuple(
                payload
                for digest, payload in self._payloads.items()
                if digest != self.profile_sha256
            ),
        )


def _binding(
    world: _ReceiptWorld,
    *,
    binding_id: str,
    motif_receipt_sha256: str,
    scalar: str | None,
) -> MotifOutputBinding:
    sensory = world.sensory(binding_id)
    closed = world.closed_experience(binding_id, sensory)
    strand = world.fact(f"{binding_id}:strand")
    output = world.fact(f"{binding_id}:output")
    if scalar is None:
        kind = OutputBindingKind.NO_OUTPUT
        trits = ()
        language_count = 0
        no_output_count = 1
    else:
        assert len(scalar) == 1
        kind = OutputBindingKind.LANGUAGE_SCALAR
        trits = encode_balanced_ternary_scalar(ord(scalar))
        language_count = 1
        no_output_count = 0
    payload = motif_output_binding_receipt_payload(
        binding_id=binding_id,
        profile_binding_sha256=world.profile_sha256,
        motif_receipt_sha256=motif_receipt_sha256,
        closed_experience_receipt_sha256=closed,
        fact_strand_receipt_sha256=strand,
        sensory_evidence_receipt_sha256s=sensory,
        coexperienced_output_receipt_sha256=output,
        kind=kind,
        trits=trits,
        language_scalar_cardinality=language_count,
        no_output_cardinality=no_output_count,
    )
    return MotifOutputBinding(
        binding_id=binding_id,
        profile_binding_sha256=world.profile_sha256,
        motif_receipt_sha256=motif_receipt_sha256,
        closed_experience_receipt_sha256=closed,
        fact_strand_receipt_sha256=strand,
        sensory_evidence_receipt_sha256s=sensory,
        coexperienced_output_receipt_sha256=output,
        kind=kind,
        trits=trits,
        language_scalar_cardinality=language_count,
        no_output_cardinality=no_output_count,
        binding_receipt_sha256=world.mount(payload),
    )


def _bank(
    world: _ReceiptWorld,
    bindings: tuple[MotifOutputBinding, ...],
    bank_id: str = "complete-bank",
) -> MotifBindingBank:
    ordered = tuple(
        sorted(
            bindings,
            key=lambda item: (
                item.motif_receipt_sha256,
                item.binding_id,
                item.binding_receipt_sha256,
            ),
        )
    )
    payload = motif_binding_bank_receipt_payload(
        bank_id=bank_id,
        profile_binding_sha256=world.profile_sha256,
        bindings=ordered,
    )
    return MotifBindingBank(
        bank_id=bank_id,
        profile_binding_sha256=world.profile_sha256,
        bindings=ordered,
        bank_receipt_sha256=world.mount(payload),
        bank_receipt_payload=payload,
    )


def _event(
    world: _ReceiptWorld,
    *,
    expression_id: str,
    event_id: str,
    motif_receipt_sha256: str,
    source_state_receipt_sha256: str,
    transition_edge_receipt_sha256: str,
    result_state_receipt_sha256: str,
    binding_bank: MotifBindingBank,
    kind: MotifEventKind = MotifEventKind.CONTENT,
) -> CommittedMotifEvent:
    close_authority: str | None = None
    if kind is MotifEventKind.EXPRESSION_CLOSE:
        close_authority = world.mount(
            expression_close_authority_receipt_payload(
                expression_id=expression_id,
                close_motif_receipt_sha256=motif_receipt_sha256,
            )
        )
    sensory = world.sensory(event_id)
    closed = world.closed_experience(event_id, sensory)
    strand = world.fact(f"{event_id}:strand")
    full_field = world.fact(f"{event_id}:full-field")
    field_commit = world.fact(f"{event_id}:field-commit")
    motif_commit = world.fact(f"{event_id}:motif-commit")
    l6_lock = world.fact(f"{event_id}:l6-lock")
    payload = committed_motif_event_receipt_payload(
        expression_id=expression_id,
        event_id=event_id,
        event_kind=kind,
        profile_binding_sha256=world.profile_sha256,
        motif_receipt_sha256=motif_receipt_sha256,
        closed_experience_receipt_sha256=closed,
        fact_strand_receipt_sha256=strand,
        sensory_evidence_receipt_sha256s=sensory,
        full_field_state_receipt_sha256=full_field,
        field_commit_receipt_sha256=field_commit,
        dominant_motif_commit_receipt_sha256=motif_commit,
        corrected_l6_lock_receipt_sha256=l6_lock,
        output_binding_bank_receipt_sha256=binding_bank.bank_receipt_sha256,
        source_state_receipt_sha256=source_state_receipt_sha256,
        transition_edge_receipt_sha256=transition_edge_receipt_sha256,
        result_state_receipt_sha256=result_state_receipt_sha256,
        expression_close_authority_receipt_sha256=close_authority,
    )
    return CommittedMotifEvent(
        expression_id=expression_id,
        event_id=event_id,
        event_kind=kind,
        profile_binding_sha256=world.profile_sha256,
        motif_receipt_sha256=motif_receipt_sha256,
        closed_experience_receipt_sha256=closed,
        fact_strand_receipt_sha256=strand,
        sensory_evidence_receipt_sha256s=sensory,
        full_field_state_receipt_sha256=full_field,
        field_commit_receipt_sha256=field_commit,
        dominant_motif_commit_receipt_sha256=motif_commit,
        corrected_l6_lock_receipt_sha256=l6_lock,
        output_binding_bank_receipt_sha256=binding_bank.bank_receipt_sha256,
        source_state_receipt_sha256=source_state_receipt_sha256,
        transition_edge_receipt_sha256=transition_edge_receipt_sha256,
        result_state_receipt_sha256=result_state_receipt_sha256,
        expression_close_authority_receipt_sha256=close_authority,
        event_receipt_sha256=world.mount(payload),
    )


def _states(world: _ReceiptWorld, name: str, count: int) -> tuple[str, ...]:
    return tuple(world.fact(f"{name}:state:{index}") for index in range(count))


def test_multiword_memory_is_released_only_after_exact_close() -> None:
    world = _ReceiptWorld("multiword")
    expression_id = "remembered-expression"
    remembered = "we remember 🌿"
    motifs = tuple(world.fact(f"motif:{index}") for index in range(len(remembered)))
    bindings = tuple(
        _binding(
            world,
            binding_id=f"binding:{index}",
            motif_receipt_sha256=motif,
            scalar=scalar,
        )
        for index, (motif, scalar) in enumerate(zip(motifs, remembered, strict=True))
    )
    bank = _bank(world, bindings)
    states = _states(world, "multiword", len(remembered) + 2)
    events = tuple(
        _event(
            world,
            expression_id=expression_id,
            event_id=f"content:{index}",
            motif_receipt_sha256=motif,
            source_state_receipt_sha256=states[index],
            transition_edge_receipt_sha256=world.fact(f"edge:{index}"),
            result_state_receipt_sha256=states[index + 1],
            binding_bank=bank,
        )
        for index, motif in enumerate(motifs)
    )
    close_motif = world.fact("motif:exact-close")
    close = _event(
        world,
        expression_id=expression_id,
        event_id="close",
        motif_receipt_sha256=close_motif,
        source_state_receipt_sha256=states[-2],
        transition_edge_receipt_sha256=world.fact("edge:close"),
        result_state_receipt_sha256=states[-1],
        binding_bank=bank,
        kind=MotifEventKind.EXPRESSION_CLOSE,
    )
    registry = world.registry()
    actuator = RememberedExpressionActuator(
        expression_id=expression_id,
        profile_binding_sha256=world.profile_sha256,
        initial_state_receipt_sha256=states[0],
    )

    for event in events:
        result = actuator.process(
            event=event,
            binding_bank=bank,
            receipt_registry=registry,
        )
        assert result.text == ""
        assert result.receipt.status is OutputStatus.STAGED_PRIVATE
        assert result.receipt.emitted_scalar_codepoints == ()
        assert result.receipt.contributing_event_receipt_sha256s == ()
        assert result.receipt.binding_receipt_sha256s == ()

    released = actuator.process(
        event=close,
        binding_bank=bank,
        receipt_registry=registry,
    )
    assert released.text == remembered
    assert released.receipt.status is OutputStatus.EXPRESSION_RELEASED
    assert released.receipt.reason is OutputReason.EXACT_EXPRESSION_CLOSE_COMMITTED
    assert released.receipt.stage_disposition is StageDisposition.RELEASED_AND_CLEARED
    assert released.receipt.emitted_scalar_codepoints == tuple(map(ord, remembered))
    assert len(released.receipt.binding_receipt_sha256s) == len(remembered)


def test_one_word_fragment_never_crosses_the_actuation_boundary() -> None:
    world = _ReceiptWorld("fragment")
    expression_id = "unclosed-word"
    fragment = "hello"
    motifs = tuple(world.fact(f"fragment-motif:{index}") for index in range(len(fragment)))
    bank = _bank(
        world,
        tuple(
            _binding(
                world,
                binding_id=f"fragment-binding:{index}",
                motif_receipt_sha256=motif,
                scalar=scalar,
            )
            for index, (motif, scalar) in enumerate(zip(motifs, fragment, strict=True))
        ),
    )
    states = _states(world, "fragment", len(fragment) + 1)
    events = tuple(
        _event(
            world,
            expression_id=expression_id,
            event_id=f"fragment-event:{index}",
            motif_receipt_sha256=motif,
            source_state_receipt_sha256=states[index],
            transition_edge_receipt_sha256=world.fact(f"fragment-edge:{index}"),
            result_state_receipt_sha256=states[index + 1],
            binding_bank=bank,
        )
        for index, motif in enumerate(motifs)
    )
    registry = world.registry()
    actuator = RememberedExpressionActuator(
        expression_id=expression_id,
        profile_binding_sha256=world.profile_sha256,
        initial_state_receipt_sha256=states[0],
    )

    results = tuple(
        actuator.process(event=event, binding_bank=bank, receipt_registry=registry)
        for event in events
    )

    assert all(result.text == "" for result in results)
    assert all(result.receipt.silent for result in results)
    assert all(
        result.receipt.stage_disposition is StageDisposition.RETAINED_PRIVATE
        for result in results
    )


def test_conflict_and_language_no_output_mix_are_unknown_silence() -> None:
    world = _ReceiptWorld("ambiguity")
    conflict_motif = world.fact("motif:conflict")
    mixed_motif = world.fact("motif:mixed")
    bank = _bank(
        world,
        (
            _binding(
                world,
                binding_id="conflict:x",
                motif_receipt_sha256=conflict_motif,
                scalar="x",
            ),
            _binding(
                world,
                binding_id="conflict:y",
                motif_receipt_sha256=conflict_motif,
                scalar="y",
            ),
            _binding(
                world,
                binding_id="mixed:language",
                motif_receipt_sha256=mixed_motif,
                scalar="m",
            ),
            _binding(
                world,
                binding_id="mixed:no-output",
                motif_receipt_sha256=mixed_motif,
                scalar=None,
            ),
        ),
    )
    conflict_states = _states(world, "conflict", 2)
    conflict_event = _event(
        world,
        expression_id="conflict-expression",
        event_id="conflict-event",
        motif_receipt_sha256=conflict_motif,
        source_state_receipt_sha256=conflict_states[0],
        transition_edge_receipt_sha256=world.fact("conflict-edge"),
        result_state_receipt_sha256=conflict_states[1],
        binding_bank=bank,
    )
    mixed_states = _states(world, "mixed", 2)
    mixed_event = _event(
        world,
        expression_id="mixed-expression",
        event_id="mixed-event",
        motif_receipt_sha256=mixed_motif,
        source_state_receipt_sha256=mixed_states[0],
        transition_edge_receipt_sha256=world.fact("mixed-edge"),
        result_state_receipt_sha256=mixed_states[1],
        binding_bank=bank,
    )
    registry = world.registry()

    conflict = RememberedExpressionActuator(
        expression_id="conflict-expression",
        profile_binding_sha256=world.profile_sha256,
        initial_state_receipt_sha256=conflict_states[0],
    ).process(event=conflict_event, binding_bank=bank, receipt_registry=registry)
    mixed = RememberedExpressionActuator(
        expression_id="mixed-expression",
        profile_binding_sha256=world.profile_sha256,
        initial_state_receipt_sha256=mixed_states[0],
    ).process(event=mixed_event, binding_bank=bank, receipt_registry=registry)

    assert conflict.text == mixed.text == ""
    assert conflict.receipt.status is mixed.receipt.status is OutputStatus.UNKNOWN_SILENCE
    assert conflict.receipt.reason is OutputReason.CONFLICTING_LANGUAGE_BINDINGS
    assert mixed.receipt.reason is OutputReason.MIXED_LANGUAGE_AND_NO_OUTPUT


def test_exact_repeated_state_and_edge_proves_cycle_and_discards_stage() -> None:
    world = _ReceiptWorld("cycle")
    motif = world.fact("motif:cycle-content")
    bank = _bank(
        world,
        (
            _binding(
                world,
                binding_id="cycle-binding",
                motif_receipt_sha256=motif,
                scalar="c",
            ),
        ),
    )
    state_a, state_b = _states(world, "cycle", 2)
    edge_forward = world.fact("cycle-edge:forward")
    edge_return = world.fact("cycle-edge:return")
    events = (
        _event(
            world,
            expression_id="cycle-expression",
            event_id="cycle:one",
            motif_receipt_sha256=motif,
            source_state_receipt_sha256=state_a,
            transition_edge_receipt_sha256=edge_forward,
            result_state_receipt_sha256=state_b,
            binding_bank=bank,
        ),
        _event(
            world,
            expression_id="cycle-expression",
            event_id="cycle:two",
            motif_receipt_sha256=motif,
            source_state_receipt_sha256=state_b,
            transition_edge_receipt_sha256=edge_return,
            result_state_receipt_sha256=state_a,
            binding_bank=bank,
        ),
        _event(
            world,
            expression_id="cycle-expression",
            event_id="cycle:three",
            motif_receipt_sha256=motif,
            source_state_receipt_sha256=state_a,
            transition_edge_receipt_sha256=edge_forward,
            result_state_receipt_sha256=state_b,
            binding_bank=bank,
        ),
    )
    registry = world.registry()
    actuator = RememberedExpressionActuator(
        expression_id="cycle-expression",
        profile_binding_sha256=world.profile_sha256,
        initial_state_receipt_sha256=state_a,
    )

    first = actuator.process(event=events[0], binding_bank=bank, receipt_registry=registry)
    second = actuator.process(event=events[1], binding_bank=bank, receipt_registry=registry)
    cycle = actuator.process(event=events[2], binding_bank=bank, receipt_registry=registry)

    assert first.text == second.text == cycle.text == ""
    assert first.receipt.status is second.receipt.status is OutputStatus.STAGED_PRIVATE
    assert cycle.receipt.status is OutputStatus.UNKNOWN_SILENCE
    assert cycle.receipt.reason is OutputReason.EXACT_STATE_EDGE_CYCLE
    assert cycle.receipt.stage_disposition is StageDisposition.DISCARDED


def test_unicode_arithmetic_and_tamper_failure_are_exact_and_silent() -> None:
    assert decode_balanced_ternary_scalar(
        encode_balanced_ternary_scalar(ord("🌌"), scalar_index=9)
    ) == "🌌"
    assert decode_balanced_ternary_scalar(
        encode_balanced_ternary_scalar(0x10FFFF)
    ) == chr(0x10FFFF)
    with pytest.raises(ReceiptError, match="exactly 14"):
        decode_balanced_ternary_scalar(encode_balanced_ternary_scalar(ord("a"))[:-1])

    world = _ReceiptWorld("tamper")
    motif = world.fact("motif:tamper")
    original = _binding(
        world,
        binding_id="tamper-binding",
        motif_receipt_sha256=motif,
        scalar="🌌",
    )
    valid_bank = _bank(world, (original,))
    tampered_binding = replace(
        original,
        trits=encode_balanced_ternary_scalar(ord("?")),
    )
    tampered_bank = MotifBindingBank(
        bank_id=valid_bank.bank_id,
        profile_binding_sha256=valid_bank.profile_binding_sha256,
        bindings=(tampered_binding,),
        bank_receipt_sha256=valid_bank.bank_receipt_sha256,
        bank_receipt_payload=valid_bank.bank_receipt_payload,
    )
    states = _states(world, "tamper", 2)
    event = _event(
        world,
        expression_id="tamper-expression",
        event_id="tamper-event",
        motif_receipt_sha256=motif,
        source_state_receipt_sha256=states[0],
        transition_edge_receipt_sha256=world.fact("tamper-edge"),
        result_state_receipt_sha256=states[1],
        binding_bank=valid_bank,
    )
    result = RememberedExpressionActuator(
        expression_id="tamper-expression",
        profile_binding_sha256=world.profile_sha256,
        initial_state_receipt_sha256=states[0],
    ).process(
        event=event,
        binding_bank=tampered_bank,
        receipt_registry=world.registry(),
    )

    assert result.text == ""
    assert result.receipt.status is OutputStatus.UNKNOWN_SILENCE
    assert result.receipt.reason is OutputReason.RECEIPT_FAILURE
    assert result.receipt.stage_disposition is StageDisposition.EMPTY
    assert "mounted exact bytes" in result.receipt.failure_detail
