"""The retired Unicode/TTS bridge cannot execute a mouth action."""

from __future__ import annotations

from pathlib import Path

from dsf_ai_service import substrate_runner


def test_runner_contains_no_espeak_speech_synthesizer():
    source = Path(substrate_runner.__file__).read_text(encoding="utf-8")

    assert "espeak-ng" not in source
    assert "def _synthesize_voice(" not in source
    assert "def _synthesize_released_voice(" not in source
    assert "def resume_pending_causal_speech_delivery(" not in source
    assert "SpeechSynthesisUtterance" not in source
