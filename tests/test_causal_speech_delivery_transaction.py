"""Production speech may only use learned bounded PCM self-vocal output."""

from __future__ import annotations

import asyncio
import inspect
import json
from pathlib import Path

import dsf_ai_service.app as app_module
from dsf_ai_service import substrate_runner


def test_transcript_reply_worker_and_registry_are_deleted():
    source = inspect.getsource(app_module)

    assert "def _run_voice_reply(" not in source
    assert "def _maybe_trigger_voice_reply(" not in source
    assert "_voice_turn_results" not in source


def test_historical_terminal_reply_poll_route_is_retired():
    response = asyncio.run(
        app_module.auditory_terminal_reply("a" * 64)
    )

    assert response.status_code == 410
    assert json.loads(response.body) == (
        app_module._RETIRED_SCRIPTED_COGNITION
    )


def test_boot_cannot_resume_historical_unicode_speech():
    app_source = Path(app_module.__file__).read_text(encoding="utf-8")
    runner_source = Path(substrate_runner.__file__).read_text(
        encoding="utf-8"
    )

    assert "resume_pending_causal_speech_delivery()" not in app_source
    assert "def resume_pending_causal_speech_delivery(" not in runner_source
    assert "def _synthesize_released_voice(" not in runner_source


def test_browser_has_no_text_synthesizer_and_keeps_exact_pcm_player():
    page = (
        Path(app_module.__file__).parent / "static" / "gualaloom.html"
    ).read_text(encoding="utf-8")

    assert "speechSynthesis" not in page
    assert "SpeechSynthesisUtterance" not in page
    assert "function gualaPlayExactWav" in page
    assert "data:audio/wav;base64," in page
