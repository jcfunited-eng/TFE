"""STT staging proofs (spec v3, acceptance criterion 7): never during boot.

The 2026-07-16 boot OOM happened because the _eager_init pre-warm loaded
whisper DURING boot, in the shared process, while the substrate was already
paying its own boot memory peak.  Staged truth now:

  - the boot path never constructs the model or spawns the worker — the
    pre-warm is a post-ready kick that runs strictly AFTER _init_complete
    flips (first use would also warm it);
  - the out-of-process worker is the default lane (VOICE_WHISPER_WORKER
    defaults 1; 0 is the explicit embedded escape hatch);
  - the Dockerfile records the staged truth (VOICE_WHISPER=1 stays the image
    default per the existing honest-boundary test; VOICE_WHISPER_WORKER=1 is
    now baked beside it);
  - when STT is off, nothing is ever constructed and the honest
    "spoken-word recognition unavailable" banner path stands untouched.

Structural source-order asserts follow the existing convention
(test_stt_boundary_transducer.test_live_sound_route_owns_one_recognizer...).
"""

import inspect
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import dsf_ai_service.app as appmod  # noqa: E402
import dsf_ai_service.speech_transducer as transducer  # noqa: E402


# ── boot path never constructs the model ─────────────────────────────────────

def test_boot_path_never_constructs_the_recognizer_or_worker():
    """The whole startup coroutine (which contains _eager_init) must not
    reach model/worker construction; the only STT mention allowed is the
    post-ready kick."""
    startup_source = inspect.getsource(appmod.startup)
    assert "require_speech_recognizer" not in startup_source, (
        "boot pre-warm reintroduced — the model must never load during boot")
    assert "get_speech_recognizer" not in startup_source
    assert "transcribe_sound" not in startup_source
    assert "_kick_speech_prewarm_after_ready" in startup_source


def test_prewarm_kick_fires_strictly_after_readiness_flips():
    startup_source = inspect.getsource(appmod.startup)
    ready_flip = startup_source.index("_init_complete = True",
                                      startup_source.index("def _eager_init"))
    kick = startup_source.index("_kick_speech_prewarm_after_ready()")
    assert kick > ready_flip, (
        "the pre-warm kick must come AFTER _init_complete = True")
    # And the failure branch (_init_error path) must NOT kick a pre-warm.
    error_branch = startup_source.index("_init_error = str(error)")
    assert not (error_branch < kick < startup_source.index(
        "else:", error_branch)), "no pre-warm on a failed boot"


def test_importing_the_app_constructs_nothing():
    """Module import (part of every boot) must leave both lanes lazy.
    Other tests may have populated the singletons in this pytest process,
    so this asserts the mechanism: the singletons start as None in a fresh
    interpreter (module defaults), and the status reader never constructs."""
    source = Path(inspect.getsourcefile(transducer)).read_text()
    assert "_speech_recognizer = None" in source
    assert "_speech_worker = None" in source


# ── the post-ready kick itself ───────────────────────────────────────────────

def test_kick_is_a_noop_when_stt_is_off(monkeypatch):
    monkeypatch.delenv("VOICE_WHISPER", raising=False)
    called = []
    monkeypatch.setattr(
        transducer, "require_speech_recognizer",
        lambda: called.append(True))
    assert appmod._kick_speech_prewarm_after_ready() is None
    assert called == [], "STT off: nothing may ever be constructed"


def test_kick_prewarms_on_the_owned_executor_when_stt_is_on(monkeypatch):
    monkeypatch.setenv("VOICE_WHISPER", "1")
    called = []
    monkeypatch.setattr(
        transducer, "require_speech_recognizer",
        lambda: called.append(True) or object())
    future = appmod._kick_speech_prewarm_after_ready()
    assert future is not None
    assert future.result(timeout=10) is None, "kick returns nothing"
    assert called == [True], "exactly one steady-state pre-warm"


def test_prewarm_failure_is_loud_but_contained(monkeypatch, capsys):
    monkeypatch.setenv("VOICE_WHISPER", "1")

    def _explode():
        raise transducer.SpeechRecognitionUnavailable("model missing")

    monkeypatch.setattr(transducer, "require_speech_recognizer", _explode)
    future = appmod._kick_speech_prewarm_after_ready()
    assert future.result(timeout=10) is None, (
        "a pre-warm failure must never propagate into the app lifecycle")
    out = capsys.readouterr().out
    assert "steady-state pre-warm error=SpeechRecognitionUnavailable" in out


# ── staged truth in the image + honest banner path intact ────────────────────

def test_dockerfile_records_the_staged_truth():
    dockerfile = (ROOT / "dsf_ai_service" / "Dockerfile").read_text()
    assert "ENV VOICE_WHISPER=1" in dockerfile
    assert "ENV VOICE_WHISPER_WORKER=1" in dockerfile, (
        "worker lane is the image default (spec v3 acceptance criterion 7)")


def test_health_exposes_speech_telemetry_without_constructing(monkeypatch):
    monkeypatch.setattr(transducer, "_speech_worker", None)
    monkeypatch.setattr(transducer, "_speech_recognizer", None)
    snapshot = appmod._speech_status_snapshot()
    assert snapshot["worker"]["rss_breaches"] == 0
    assert snapshot["worker"]["state"] == "never_started"
    assert transducer._speech_worker is None
    assert transducer._speech_recognizer is None


def test_honest_unavailable_report_survives_the_staging(monkeypatch):
    """STT off or worker down: the UI banner path keeps working — the report
    for a non-configured capability is exactly the Fact-Strand-era one."""
    monkeypatch.delenv("VOICE_WHISPER", raising=False)
    report = appmod._spoken_word_recognition_report("joe_voice")
    assert report["status"] == "unavailable"
    assert report["available"] is False
    assert report["raw_sensing"]["available"] is True
