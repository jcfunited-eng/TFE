"""Regression proof for exact causal, conserved organism growth.

The retired word/spectrum pool allowed method order to decide anatomy.  These
tests prove that words still reach the organism but cannot divide it, while a
typed causal claim contributes one exact energy unit shared simultaneously
across the mechanisms that physically participated.
"""

from __future__ import annotations

import hashlib
import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from dsf_ai_service.loom_model.embryo import Embryo
from dsf_ai_service.substrate.causal_organism_growth import (
    CausalOrganismGrowthClaim,
)


SEED_KW = {
    "brain_seed": 42,
    "observable": "event_count",
    "seed_size": 8,
}
ACTIVE = ("em", "pr", "ep", "sf")


def _digest(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def _claim(index: int) -> CausalOrganismGrowthClaim:
    return CausalOrganismGrowthClaim(
        claim_id=_digest(f"claim-{index}"),
        settlement_event_id=_digest(f"event-{index}"),
        settlement_structural_fingerprint=_digest(f"field-{index}"),
        settlement_authority_receipt_sha256=_digest(f"receipt-{index}"),
        engine_tick=index,
        active_organs=ACTIVE,
        sense_relations=(
            ("sight", "observed", "structural_change", _digest(f"s-{index}")),
            ("sound", "observed", "structural_change", _digest(f"a-{index}")),
            ("touch", "observed", "recurrence", _digest("touch")),
            ("smell", "sensor_unavailable", "not_observed", _digest("smell")),
            ("taste", "sensor_unavailable", "not_observed", _digest("taste")),
            ("body", "observed", "recurrence", _digest("body")),
        ),
        contributes_division_energy=True,
        authority_hmac_sha256=_digest(f"hmac-{index}"),
    )


def _prime_real_structural_state(embryo: Embryo) -> None:
    t = np.linspace(0.0, 2.0 * np.pi, 200)
    embryo.experience_word(
        "physical",
        {
            "auditory": np.sin(7.0 * t),
            "language": "physical",
            "visual": np.cos(5.0 * t),
        },
    )


def test_word_and_waveform_processing_cannot_divide() -> None:
    embryo = Embryo(**SEED_KW)
    for index in range(12):
        t = np.linspace(0.0, 2.0 * np.pi, 200)
        embryo.experience_word(
            f"word-{index}",
            {
                "auditory": np.sin((3 + index) * t),
                "language": f"word-{index}",
                "visual": np.cos((5 + index) * t),
            },
        )
    snapshot = embryo.growth_snapshot()
    assert snapshot["total_neurons"] == 64
    assert snapshot["total_divisions"] == 0
    assert snapshot["division_pool"] == 0.0


def test_legacy_charge_and_fold_is_closed() -> None:
    embryo = Embryo(**SEED_KW)
    with pytest.raises(RuntimeError, match="exact causal growth claim"):
        embryo._charge_and_fold(
            embryo.brain.hemispheres[0],
            coherent=True,
            quantum=1.0,
        )


def test_four_causal_experiences_divide_four_active_organs_together() -> None:
    embryo = Embryo(**SEED_KW)
    _prime_real_structural_state(embryo)

    for index in range(4):
        result = embryo.apply_causal_growth_claim(_claim(index))
        assert result["applied"] is True

    snapshot = embryo.growth_snapshot()
    assert snapshot["total_neurons"] == 68
    assert snapshot["total_divisions"] == 4
    assert snapshot["remaining_lifetime_divisions"] == 60
    assert snapshot["per_hemisphere"] == {
        "aff": 8,
        "em": 9,
        "ep": 9,
        "gp": 8,
        "pr": 9,
        "sc": 8,
        "sf": 9,
        "sv": 8,
    }
    assert set(snapshot["causal_growth_reservoirs"].values()) == {"0/1"}
    events = embryo.pop_fold_events()
    assert len(events) == 4
    assert {event["hemi"] for event in events} == set(ACTIVE)
    assert all(
        event["cause"] == "exact_causal_experience"
        and event["division_energy_at_fold"] == "1/1"
        for event in events
    )


def test_duplicate_claim_is_idempotent() -> None:
    embryo = Embryo(**SEED_KW)
    _prime_real_structural_state(embryo)
    claim = _claim(0)
    first = embryo.apply_causal_growth_claim(claim)
    before = embryo.growth_snapshot()
    second = embryo.apply_causal_growth_claim(claim)
    after = embryo.growth_snapshot()

    assert first["applied"] is True
    assert second == {
        "applied": False,
        "claim_id": claim.claim_id,
        "folds": (),
        "reason": "already_applied",
    }
    assert after == before


def test_remaining_energy_reaches_starved_organs_after_legacy_em_growth() -> None:
    embryo = Embryo(**SEED_KW)
    _prime_real_structural_state(embryo)
    for index in range(42):
        em_only = _claim(index)
        em_only = CausalOrganismGrowthClaim(
            claim_id=em_only.claim_id,
            settlement_event_id=em_only.settlement_event_id,
            settlement_structural_fingerprint=(
                em_only.settlement_structural_fingerprint
            ),
            settlement_authority_receipt_sha256=(
                em_only.settlement_authority_receipt_sha256
            ),
            engine_tick=em_only.engine_tick,
            active_organs=("em",),
            sense_relations=em_only.sense_relations,
            contributes_division_energy=True,
            authority_hmac_sha256=em_only.authority_hmac_sha256,
        )
        embryo.apply_causal_growth_claim(em_only)
    embryo.clear_causal_growth_checkpoint_claims(
        embryo.causal_growth_checkpoint_claim_ids()
    )
    assert embryo.growth_snapshot()["per_hemisphere"]["em"] == 50

    for index in range(42, 46):
        embryo.apply_causal_growth_claim(_claim(index))

    populations = embryo.growth_snapshot()["per_hemisphere"]
    assert populations["em"] == 51
    assert populations["pr"] == 9
    assert populations["ep"] == 9
    assert populations["sf"] == 9
    assert all(
        populations[tag] == 8
        for tag in ("sc", "gp", "sv", "aff")
    )


def test_lifetime_division_budget_is_hard_bounded() -> None:
    embryo = Embryo(**SEED_KW)
    _prime_real_structural_state(embryo)
    for index in range(64):
        embryo.apply_causal_growth_claim(_claim(index))
    snapshot = embryo.growth_snapshot()
    assert snapshot["total_neurons"] == 128
    assert snapshot["total_divisions"] == 64
    assert snapshot["remaining_lifetime_divisions"] == 0
    assert snapshot["division_pool"] == 0.0
    assert snapshot["max_total_neurons"] >= snapshot["total_neurons"]


def test_structural_graph_roundtrip_preserves_exact_reservoir_and_claims(
    tmp_path,
) -> None:
    embryo = Embryo(**SEED_KW)
    _prime_real_structural_state(embryo)
    for index in range(3):
        embryo.apply_causal_growth_claim(_claim(index))
    before = embryo.growth_snapshot()
    path = tmp_path / "organism.sgr"

    embryo.save_full_state(path)
    restored = Embryo.load_full_state(path)

    assert restored.growth_snapshot() == before
    assert restored.causal_growth_checkpoint_claim_ids() == tuple(
        _claim(index).claim_id for index in range(3)
    )
    restored.apply_causal_growth_claim(_claim(3))
    assert restored.growth_snapshot()["total_divisions"] == 4


def test_checkpoint_clear_removes_only_the_saved_prefix() -> None:
    embryo = Embryo(**SEED_KW)
    _prime_real_structural_state(embryo)
    embryo.apply_causal_growth_claim(_claim(0))
    saved_prefix = embryo.causal_growth_checkpoint_claim_ids()
    embryo.apply_causal_growth_claim(_claim(1))

    embryo.clear_causal_growth_checkpoint_claims(saved_prefix)

    assert embryo.causal_growth_checkpoint_claim_ids() == (
        _claim(1).claim_id,
    )
