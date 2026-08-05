"""Engine cutover contract for embodied causal actions."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_engine_has_only_the_embodied_action_cycle_and_dispatcher() -> None:
    engine = (
        ROOT / "dsf_ai_service/v4/guala_physical_runtime_core.py"
    ).read_text()
    assert "_causal_action_cycle" in engine
    assert "_causal_action_dispatcher" in engine
    assert "_causal_action_owner" not in engine
    assert "teach_causal_action(" not in engine
    assert "_execute_causal_speech_request(" not in engine
    assert "causal_speech_output_status(" not in engine
