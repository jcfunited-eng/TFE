"""Adversarial checkpoint proof for causal-action evidence continuity."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import sys
from fractions import Fraction

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from test_causal_action_engine_integration import _artifacts

from dsf_ai_service.substrate.auditory_reciprocity import (
    AuditoryReciprocityOwner,
)
from dsf_ai_service.substrate.auditory_tutor_authority import (
    AuditoryTutorAuthority,
)
from dsf_ai_service.substrate.causal_action import (
    CAUSAL_ACTION_HMAC_DOMAIN,
    CausalActionOwner,
)


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _digest(value: object) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def test_hmac_valid_checkpoint_cannot_cross_bind_its_witnesses() -> None:
    key = b"persistence-integrity-key"
    reciprocity = AuditoryReciprocityOwner(
        log_event=lambda *_args, **_kwargs: None,
        tutor_authority=AuditoryTutorAuthority.unrequired(),
    )
    _built, _auditory, _terminal, trigger = _artifacts(
        name="integrity-trigger",
        label="hello guala",
        values=(Fraction(1, 8), Fraction(1, 4), Fraction(3, 8)),
        reciprocity=reciprocity,
        teach=True,
    )
    _built, _auditory, _terminal, action = _artifacts(
        name="integrity-action",
        label="hello daddy",
        values=(Fraction(5, 8), Fraction(3, 4), Fraction(7, 8)),
        reciprocity=reciprocity,
        teach=True,
    )
    owner = CausalActionOwner(
        log_event=lambda *_args, **_kwargs: None,
        authority_key=key,
    )
    owner.offer_teaching_experience(trigger)
    owner.offer_teaching_experience(action)
    owner.teach(
        trigger_experience_id=trigger.event_id,
        action_experience_id=action.event_id,
        source="joe",
    )
    envelope = owner.encoded_snapshot()
    state = json.loads(base64.b64decode(envelope["payload_base64"]))
    binding = state["bindings"][0]
    binding["trigger_witness_receipt_sha256"] = (
        binding["action_witness_receipt_sha256"]
    )
    binding["binding_receipt_sha256"] = _digest({
        key_name: value
        for key_name, value in binding.items()
        if key_name != "binding_receipt_sha256"
    })
    payload = _canonical_bytes(state)
    crossed = {
        "payload_base64": base64.b64encode(payload).decode("ascii"),
        "schema": envelope["schema"],
        "state_hmac_sha256": hmac.new(
            key,
            CAUSAL_ACTION_HMAC_DOMAIN + payload,
            hashlib.sha256,
        ).hexdigest(),
    }
    restored = CausalActionOwner(
        log_event=lambda *_args, **_kwargs: None,
        authority_key=key,
    )

    with pytest.raises(ValueError, match="binding evidence"):
        restored.restore_encoded(crossed)
