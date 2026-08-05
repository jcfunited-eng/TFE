"""Adversarial contracts for migration-only legacy custody inspection."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json

import pytest

import dsf_ai_service.substrate.legacy_learned_state_gate as gate_module
from dsf_ai_service.substrate.causal_action_cycle import (
    CausalActionCycle,
)
from dsf_ai_service.substrate.causal_deliberation import (
    CausalDeliberation,
)
from dsf_ai_service.substrate.legacy_learned_state_gate import (
    LegacyLearnedStateGateError,
    _inspect_retired_causal_deliberation,
    _inspect_retired_embodied_action_teaching,
)
from dsf_ai_service.v4.guala_physical_runtime import Guala
from tests.test_causal_deliberation import (
    _action,
    _learn_transition,
    _settlement,
)


AUTHORITY_KEY = "legacy-inspector-focused-authority-key-000000000000"


def _canonical(value: object) -> bytes:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


@pytest.fixture
def runtime(monkeypatch):
    monkeypatch.setenv("EVENT_DRIVEN_SUBSTRATE", "0")
    monkeypatch.setenv("GUALA_CAUSAL_ACTION_KEY", AUTHORITY_KEY)
    value = Guala()
    try:
        yield value
    finally:
        value.strict_shutdown(timeout=30.0)


def _witnesses(payload: dict[str, object]) -> list[dict[str, object]]:
    result: list[dict[str, object]] = []
    for relation in payload["relations"]:
        result.append(relation["trigger"])
        result.extend(relation["outcomes"])
    episode = payload["episode"]
    if episode is not None:
        for name in ("current", "expected_outcome"):
            witness = episode[name]
            if witness is not None:
                result.append(witness)
    return result


def _first_field_tuple(
    witness: dict[str, object],
) -> dict[str, object]:
    settlement = json.loads(
        base64.b64decode(
            witness["settlement_payload_base64"],
            validate=True,
        )
    )
    field_tuple = settlement["interpretations"][0]["substreams"][0][
        "field_tuples"
    ][0]
    witness["_decoded_settlement_for_test"] = settlement
    return field_tuple


def _publish_witness_mutation(witness: dict[str, object]) -> None:
    settlement = witness.pop("_decoded_settlement_for_test")
    encoded = _canonical(settlement)
    witness["settlement_payload_base64"] = base64.b64encode(
        encoded
    ).decode("ascii")
    witness["settlement_receipt_sha256"] = hashlib.sha256(
        encoded
    ).hexdigest()


def _legacy_deliberation_envelope(runtime: Guala) -> dict[str, object]:
    trigger = _settlement("legacy-inspector-trigger", frequency=8)
    outcome = _settlement("legacy-inspector-outcome", frequency=9)
    cycle = CausalActionCycle(
        authority_key="legacy-inspector-cycle"
    )
    _learn_transition(
        cycle,
        trigger,
        _action("legacy-inspector-action"),
        outcome,
        "legacy-inspector-teacher-nonce-0001",
    )
    deliberation = CausalDeliberation(
        authority_key="legacy-inspector-deliberation"
    )
    assert deliberation.start(
        trigger,
        action_cycle=cycle,
    ).status == "action"
    current = deliberation.encoded_snapshot()
    payload = json.loads(
        base64.b64decode(
            current["payload_base64"],
            validate=True,
        )
    )
    for witness in _witnesses(payload):
        settlement = json.loads(
            base64.b64decode(
                witness["settlement_payload_base64"],
                validate=True,
            )
        )
        for sense in settlement["interpretations"]:
            for substream in sense["substreams"]:
                for field_tuple in substream["field_tuples"]:
                    field_tuple.pop("source_index_end")
                    field_tuple.pop("source_index_start")
                    field_tuple.pop(
                        "source_l0_l4_trace_receipt_sha256"
                    )
        encoded = _canonical(settlement)
        witness["settlement_payload_base64"] = base64.b64encode(
            encoded
        ).decode("ascii")
        witness["settlement_receipt_sha256"] = hashlib.sha256(
            encoded
        ).hexdigest()
    return _signed_deliberation_envelope(runtime, payload)


def _signed_deliberation_envelope(
    runtime: Guala,
    payload: dict[str, object],
) -> dict[str, object]:
    encoded = _canonical(payload)
    return {
        "payload_base64": base64.b64encode(encoded).decode("ascii"),
        "schema": "guala.causal_deliberation.hmac.v2",
        "state_hmac_sha256": hmac.new(
            runtime._causal_deliberation._key,
            b"guala-causal-deliberation-state-v1\0" + encoded,
            hashlib.sha256,
        ).hexdigest(),
    }


def _mutate_malformed(field_tuple: dict[str, object]) -> None:
    field_tuple["fields"] = [["D_k"]]


def _mutate_flattened(field_tuple: dict[str, object]) -> None:
    field_tuple["fields"] = [["support_minus_drag", "1/1"]]


def _mutate_noncanonical(field_tuple: dict[str, object]) -> None:
    field_tuple["fields"][0][1] = "2/2"


@pytest.mark.parametrize(
    "mutation",
    (
        pytest.param(_mutate_malformed, id="malformed"),
        pytest.param(_mutate_flattened, id="flattened"),
        pytest.param(_mutate_noncanonical, id="noncanonical"),
    ),
)
def test_retired_deliberation_rejects_non_full_exact_dsf_tuples(
    runtime,
    mutation,
) -> None:
    envelope = _legacy_deliberation_envelope(runtime)
    payload = json.loads(
        base64.b64decode(
            envelope["payload_base64"],
            validate=True,
        )
    )
    witness = _witnesses(payload)[0]
    mutation(_first_field_tuple(witness))
    _publish_witness_mutation(witness)
    forged = _signed_deliberation_envelope(runtime, payload)

    with pytest.raises(
        LegacyLearnedStateGateError,
        match="DSF|field|fingerprint|settlement",
    ):
        _inspect_retired_causal_deliberation(
            forged,
            runtime=runtime,
        )


def test_retired_deliberation_rejects_mismatched_structural_fingerprint(
    runtime,
) -> None:
    envelope = _legacy_deliberation_envelope(runtime)
    payload = json.loads(
        base64.b64decode(
            envelope["payload_base64"],
            validate=True,
        )
    )
    _witnesses(payload)[0]["structural_fingerprint"] = "f" * 64
    forged = _signed_deliberation_envelope(runtime, payload)

    with pytest.raises(
        LegacyLearnedStateGateError,
        match="fingerprint|identity|settlement",
    ):
        _inspect_retired_causal_deliberation(
            forged,
            runtime=runtime,
        )


def test_embodied_teaching_acceptance_does_not_repeat_a_tautology(
    runtime,
    monkeypatch,
) -> None:
    envelope = json.loads(
        runtime._embodied_action_teaching
        .encoded_snapshot()
        .decode("utf-8")
    )
    original = gate_module._canonical
    envelope_calls = 0

    def reject_repeated_same_object(value: object) -> bytes:
        nonlocal envelope_calls
        if value is envelope:
            envelope_calls += 1
            if envelope_calls > 1:
                raise AssertionError(
                    "embodied teaching acceptance repeated the same "
                    "canonicalization as a tautological check"
                )
        return original(value)

    monkeypatch.setattr(
        gate_module,
        "_canonical",
        reject_repeated_same_object,
    )
    assert _inspect_retired_embodied_action_teaching(
        envelope,
        runtime=runtime,
    ) is None
    assert envelope_calls <= 1
