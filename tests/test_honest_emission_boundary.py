"""Active production contract for the retired text-emission authority.

The former tests in this module certified a typed-text/chi composer and a
text-to-speech mouth.  Those mechanisms conflict with the physical hearing,
causal grounding, and learned PCM motor architecture.  Historical state may
remain readable, but none of it may regain live action authority.
"""

import inspect
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class _ExplosiveLegacyEngine:
    """Any access proves a retired route reached the legacy engine."""

    tick = 0

    def __getattr__(self, name):
        raise AssertionError(f"retired route accessed legacy engine: {name}")


def test_runner_has_no_typed_converse_operation(monkeypatch):
    import dsf_ai_service.substrate_runner as runner

    monkeypatch.setattr(runner, "_guala", _ExplosiveLegacyEngine())
    assert "gualaloom_post" not in runner.OP_HANDLERS
    assert not hasattr(runner, "handle_gualaloom_post")


def test_runner_has_no_text_to_pcm_synthesizer():
    import dsf_ai_service.substrate_runner as runner

    source = inspect.getsource(runner)
    assert "def _synthesize_voice" not in source
    assert "def _synthesize_released_voice" not in source
    assert "espeak-ng" not in source


def test_preserved_text_speech_receipts_remain_inert():
    import dsf_ai_service.substrate_runner as runner

    source = inspect.getsource(runner)
    assert "def resume_pending_causal_speech_delivery(" not in source


def test_app_has_no_retained_text_converse_worker_or_task_registry():
    import dsf_ai_service.app as appmod

    source = inspect.getsource(appmod)
    assert "def _run_converse(" not in source
    assert "_converse_tasks" not in source
    assert "_GLEW_ENGINE_ENABLED" not in source


def test_browser_observation_is_not_a_reply_or_a_mouth():
    page = (
        ROOT / "dsf_ai_service" / "static" / "gualaloom.html"
    ).read_text(encoding="utf-8")

    assert "/api/v1/auditory/observations" not in page
    assert "speechSynthesis" not in page
    assert "SpeechSynthesisUtterance" not in page
    assert '<input id="msg" type="text"' not in page
