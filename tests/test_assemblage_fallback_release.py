"""Retirement contract for the former assemblage fallback reply path."""

import inspect
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_no_legacy_text_release_bridge_exists():
    import dsf_ai_service.substrate_runner as runner

    source = inspect.getsource(runner)
    assert "def _synthesize_released_voice(" not in source
    assert "def resume_pending_causal_speech_delivery(" not in source


def test_live_command_dispatch_does_not_call_the_archived_converse_composer():
    import dsf_ai_service.substrate_runner as runner

    assert "gualaloom_post" not in runner.OP_HANDLERS
    assert not hasattr(runner, "handle_gualaloom_post")


def test_browser_contains_no_assemblage_tts_fallback():
    page = (
        ROOT / "dsf_ai_service" / "static" / "gualaloom.html"
    ).read_text(encoding="utf-8")

    assert "speechSynthesis" not in page
    assert "SpeechSynthesisUtterance" not in page
