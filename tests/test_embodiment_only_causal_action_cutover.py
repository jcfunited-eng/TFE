from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dsf_ai_service.substrate.causal_action_cycle import (
    INTENT_DOMAIN,
    LEGACY_STATE_DOMAIN,
    STATE_SCHEMA,
    TEACHER_DOMAIN,
    ActionCommand,
    CausalActionCycle,
)
from dsf_ai_service.substrate.causal_settlement_dispatcher import (
    CausalSettlementDispatcher,
    authenticate_executor_acknowledgement,
)
from dsf_ai_service.substrate.owner_scoped_persistence import (
    OWNER_STATE_GROUPS,
)
from test_causal_action_cycle import _settlement, _teach


ROOT = Path(__file__).resolve().parents[1]
CYCLE_KEY = b"embodiment-only-migration-cycle-key"


def _canonical(value: object) -> bytes:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _digest(value: object) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _signed_receipt(record: dict[str, object]) -> str:
    signature = record["authority_hmac_sha256"]
    payload = {
        field: value
        for field, value in record.items()
        if field != "authority_hmac_sha256"
    }
    return _digest({
        "authority_hmac_sha256": signature,
        "payload": payload,
    })


def _legacy_action(
    record: dict[str, object], *, speech: bool
) -> dict[str, object]:
    if speech:
        return {
            "command_payload_base64": "",
            "kind": "speech",
            "port_id": None,
            "schema": "guala.causal_action_cycle.action.v1",
            "unicode_scalars": [114, 101, 116, 105, 114, 101, 100],
        }
    return {
        **record,
        "schema": "guala.causal_action_cycle.action.v1",
        "unicode_scalars": [],
    }


def _legacy_mixed_snapshot(
    cycle: CausalActionCycle,
    *,
    max_witness_bytes: int,
) -> dict[str, object]:
    envelope = cycle.encoded_snapshot()
    state = json.loads(base64.b64decode(envelope["payload_base64"]))
    old_binding_ids: dict[str, str] = {}
    old_actions: dict[str, dict[str, object]] = {}
    for index, binding in enumerate(state["bindings"]):
        old_action = _legacy_action(
            binding["action"], speech=index == 1
        )
        old_action_receipt = _digest(old_action)
        old_binding_id = _digest({
            "action_receipt_sha256": old_action_receipt,
            "schema": "guala.causal_action_cycle.semantic_relation.v1",
            "trigger_structural_fingerprint": binding[
                "trigger_structural_fingerprint"
            ],
        })
        teacher = dict(binding["teacher_relation"])
        teacher["action_receipt_sha256"] = old_action_receipt
        teacher_payload = {
            field: value
            for field, value in teacher.items()
            if field != "authority_hmac_sha256"
        }
        teacher["authority_hmac_sha256"] = hmac.new(
            CYCLE_KEY,
            TEACHER_DOMAIN + _canonical(teacher_payload),
            hashlib.sha256,
        ).hexdigest()
        old_binding_ids[binding["binding_id"]] = old_binding_id
        old_actions[binding["binding_id"]] = old_action
        binding["action"] = old_action
        binding["binding_id"] = old_binding_id
        binding["teacher_relation"] = teacher

    for intent in state["intents"]:
        current_binding_id = intent["binding_id"]
        intent["binding_id"] = old_binding_ids[current_binding_id]
        intent["action"] = old_actions[current_binding_id]
        intent_payload = {
            field: value
            for field, value in intent.items()
            if field != "authority_hmac_sha256"
        }
        intent["authority_hmac_sha256"] = hmac.new(
            CYCLE_KEY,
            INTENT_DOMAIN + _canonical(intent_payload),
            hashlib.sha256,
        ).hexdigest()

    state["schema"] = "guala.causal_action_cycle.state.v2"
    state["capacities"]["max_speech_scalars"] = 512
    state["capacities"]["max_witness_bytes"] = max_witness_bytes
    payload = _canonical(state)
    return {
        "payload_base64": base64.b64encode(payload).decode("ascii"),
        "schema": "guala.causal_action_cycle.hmac.v2",
        "state_hmac_sha256": hmac.new(
            CYCLE_KEY,
            LEGACY_STATE_DOMAIN + payload,
            hashlib.sha256,
        ).hexdigest(),
    }


def test_active_action_schema_and_sources_have_no_unicode_speech_authority():
    action = ActionCommand.embodiment("body", b"move")
    assert action.as_record() == {
        "command_payload_base64": "bW92ZQ==",
        "kind": "embodiment_port",
        "port_id": "body",
        "schema": "guala.causal_action_cycle.action.v2",
    }
    assert not (
        ROOT / "dsf_ai_service/substrate/causal_action.py"
    ).exists()
    assert not (
        ROOT / "dsf_ai_service/substrate/causal_speech_delivery.py"
    ).exists()
    assert {
        group.owner_id for group in OWNER_STATE_GROUPS
    }.isdisjoint({"causal_action", "causal_speech_release"})
    engine_path = ROOT / "dsf_ai_service/v4/gualaloom_v5_engine.py"
    if engine_path.exists():
        engine = engine_path.read_text()
        assert "_execute_causal_speech_request" not in engine
        assert "causal_speech_output_status" not in engine
        assert "_causal_action_owner" not in engine


def test_retired_action_sidecars_are_absent_from_generation_manifests():
    retired = {
        "guala_causal_speech_delivery.json",
        "owner_state/causal_action.json",
        "owner_state/causal_speech_release.json",
    }
    try:
        from dsf_ai_service.v4.gualaloom_v5_engine import Guala
    except ModuleNotFoundError:
        # The legacy v5 engine is deleted entirely: guard the current
        # physical runtime manifests instead.
        from dsf_ai_service.v4.guala_physical_runtime import Guala
    assert retired.isdisjoint(Guala.FULL_SAVE_MANIFEST_FILES)
    assert retired.isdisjoint(Guala.HOT_SAVE_MANIFEST_FILES)


@pytest.mark.parametrize(
    "legacy_max_witness_bytes",
    (2 * 1024 * 1024, 25_165_056),
)
def test_authenticated_migration_drops_speech_and_reauthors_embodiment(
    legacy_max_witness_bytes,
):
    source = CausalActionCycle(authority_key=CYCLE_KEY)
    embodied = _settlement("cutover-retained", frequency=8)
    retired = _settlement("cutover-retired", frequency=9)
    _teach(
        source,
        embodied,
        ActionCommand.embodiment("body", b"move"),
        "cutover-retained-teacher-nonce",
    )
    _teach(
        source,
        retired,
        ActionCommand.embodiment("body", b"placeholder"),
        "cutover-retired-teacher-nonce",
    )
    assert source.select(
        _settlement("cutover-retained-live", frequency=8)
    ).status == "committed"
    assert source.select(
        _settlement("cutover-retired-live", frequency=9)
    ).status == "committed"

    restored = CausalActionCycle(authority_key=CYCLE_KEY)
    restored.restore_encoded(
        _legacy_mixed_snapshot(
            source,
            max_witness_bytes=legacy_max_witness_bytes,
        )
    )

    status = restored.status()
    assert status["bindings"] == 1
    assert status["intents"] == 1
    assert restored.last_restore_retired_speech_state
    evidence = restored.verified_relation_evidence()
    assert len(evidence) == 1
    assert evidence[0].action.command_payload == b"move"
    assert restored.select(
        _settlement("cutover-retained-after", frequency=8)
    ).status == "committed"
    assert restored.select(
        _settlement("cutover-retired-after", frequency=9)
    ).status == "unknown"
    sealed = base64.b64decode(
        restored.encoded_snapshot()["payload_base64"]
    )
    assert b"unicode_scalars" not in sealed
    assert json.loads(sealed)["schema"] == STATE_SCHEMA


def test_embodiment_dispatcher_active_transaction_survives_restart():
    trigger = _settlement("cutover-dispatch")
    cycle = CausalActionCycle(authority_key=b"dispatcher-cycle-key")
    _teach(
        cycle,
        trigger,
        ActionCommand.embodiment("body", b"move"),
        "cutover-dispatch-teacher-nonce",
    )
    dispatcher_key = b"dispatcher-key"
    executor_key = b"executor-key"

    def execute(request):
        return authenticate_executor_acknowledgement(
            request=request,
            executor_id="body-executor",
            authority_key=executor_key,
            executor_action_receipt_sha256=hashlib.sha256(
                b"physical-move"
            ).hexdigest(),
            disposition="executed",
        )

    dispatcher = CausalSettlementDispatcher(
        cycle=cycle,
        authority_key=dispatcher_key,
        embodiment_executor=execute,
        embodiment_executor_id="body-executor",
        embodiment_executor_authority_key=executor_key,
        outcome_observer_id="body-observer",
        outcome_observer_authority_key=b"observer-key",
    )
    assert dispatcher.dispatch(trigger).status == "pending"
    restored = CausalSettlementDispatcher(
        cycle=cycle,
        authority_key=dispatcher_key,
        embodiment_executor=execute,
        embodiment_executor_id="body-executor",
        embodiment_executor_authority_key=executor_key,
        outcome_observer_id="body-observer",
        outcome_observer_authority_key=b"observer-key",
    )
    restored.restore_encoded(dispatcher.encoded_snapshot())
    assert restored.status()["active"] is True
    assert b"unicode_scalars" not in base64.b64decode(
        restored.encoded_snapshot()["payload_base64"]
    )
