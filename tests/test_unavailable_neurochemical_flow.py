"""Truth contracts for the typed unavailable-chemistry owner."""

from __future__ import annotations

import hashlib
import json
from fractions import Fraction

import pytest

from dsf_ai_service.substrate.physical_internal_body_state import (
    create_embodiment_proprioceptive_internal_body_authority,
)
from dsf_ai_service.substrate.unavailable_neurochemical_flow import (
    UNAVAILABLE_REASON,
    UnavailableNeurochemicalFlowOwner,
)
from tests.test_whole_organism_recovery_state import (
    BODY_KEY,
    _body_owner,
)


KEY = b"unavailable-neurochemical-flow-test-key"


def test_unavailable_is_not_quiescent_or_fabricated_chemistry() -> None:
    owner = UnavailableNeurochemicalFlowOwner(
        authority_key=KEY,
        internal_body_owner=_body_owner(),
    )
    status = owner.status()
    assert status["available"] is False
    assert status["mechanism_state"] == "unavailable"
    assert status["quiescent_claim"] is False
    assert status["chemistry_authority"] is False
    assert status["reason"] == UNAVAILABLE_REASON

    body = json.loads(owner.snapshot_encoded())["body"]
    assert body["chemical_state"] == {
        "available": False,
        "mechanism_state": "unavailable",
        "quiescent_claim": False,
        "reason": UNAVAILABLE_REASON,
    }
    encoded_chemical = json.dumps(
        body["chemical_state"],
        sort_keys=True,
    )
    for invented in (
        "species:",
        "concentration",
        "mass",
        "volume",
        "velocity",
        "reaction_rate",
        "reward",
        "mood",
        "salience",
    ):
        assert invented not in encoded_chemical
    assert "internal_body_snapshot_hex" not in body
    assert body["internal_body_snapshot_bytes"] > 0


def test_cold_restore_is_exact_and_body_bound() -> None:
    body = _body_owner()
    owner = UnavailableNeurochemicalFlowOwner(
        authority_key=KEY,
        internal_body_owner=body,
    )
    encoded = owner.snapshot_encoded()
    restored = UnavailableNeurochemicalFlowOwner.restore_encoded(
        authority_key=KEY,
        internal_body_owner=body,
        encoded=encoded,
    )
    assert restored.snapshot_encoded() == encoded
    assert restored.status() == owner.status()

    tampered = bytearray(encoded)
    tampered[-2] = (
        ord("0") if tampered[-2] != ord("0") else ord("1")
    )
    with pytest.raises(ValueError):
        UnavailableNeurochemicalFlowOwner.restore_encoded(
            authority_key=KEY,
            internal_body_owner=body,
            encoded=bytes(tampered),
        )

    changed_body = (
        create_embodiment_proprioceptive_internal_body_authority(
            authority_key=BODY_KEY,
            world_observation_receipt_sha256=hashlib.sha256(
                b"whole-organism-recovery-world-observation"
            ).hexdigest(),
            position_x_mm=Fraction(1),
            position_y_mm=Fraction(0),
            position_z_mm=Fraction(0),
            supported_load_grams=Fraction(0),
        )
    )
    with pytest.raises(
        ValueError,
        match="restored internal body changed",
    ):
        UnavailableNeurochemicalFlowOwner.restore_encoded(
            authority_key=KEY,
            internal_body_owner=changed_body,
            encoded=encoded,
        )
