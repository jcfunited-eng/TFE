"""Retirement contract for the text-derived causal action owner."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_text_derived_causal_action_owner_is_absent() -> None:
    assert not (
        ROOT / "dsf_ai_service/substrate/causal_action.py"
    ).exists()
    engine = (
        ROOT / "dsf_ai_service/v4/gualaloom_v5_engine.py"
    ).read_text()
    assert "CausalActionOwner" not in engine
    assert "_causal_action_owner" not in engine
