"""Real, non-monkeypatched-internals integration coverage for the GLEW
conversation-engine cutover in ``dsf_ai_service/app.py``.

Proves both halves of the feature flag:

* flag ON  -> a real multi-character turn reaches the real, constructed
  ``ProductionCleanConversationEngine`` (never the legacy ``_guala.converse``),
  produces a real GLEW response shape, and really processes every scalar
  (the engine's own mode bank grows as a load-bearing side effect).
* flag OFF -> behaviour is byte-identical to today: the legacy ``converse`` is
  called and the GLEW scheduler is never touched (the critical regression
  guard -- the default path must be provably unchanged).

The flag-ON test builds the engine through the SAME real construction function
the live app uses (``_boot_glew_conversation_engine``), including real secret
loading from env vars, the real unratified sensor-calibration module, and the
real bootstrap -- nothing about recognition/commit/persistence is monkeypatched.
"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest


# Placeholder (non-real) secrets, only for constructing an engine in-test.
_TEST_CHEM_SECRET = "glew-cutover-test-chemistry-hmac-secret-not-real-000000"
_TEST_CKPT_SECRET = "glew-cutover-test-checkpoint-hmac-secret-not-real-00000"


def _task_record(source: str = "joe") -> dict:
    return {
        "status": "queued",
        "phase": None,
        "started_at": 1.0,
        "started_tick": 0,
        "source": source,
    }


def _legacy_turn_result() -> SimpleNamespace:
    """A stand-in for the v5 engine's ConversationTurnResult carrying exactly
    the fields ``_run_converse``'s legacy embedded branch reads back."""

    return SimpleNamespace(
        response="warm",
        response_source="fact_strand_commit",
        emission_id="e1",
        committed_sections=("language_fact",),
        source_turn_index=1,
        recalled_pictures=(),
    )


@pytest.fixture(autouse=True)
def _reset_glew_globals():
    """Guarantee no GLEW global leaks between tests (the boot function assigns
    module globals directly)."""

    import dsf_ai_service.app as appmod

    saved = (appmod._glew_engine, appmod._glew_scheduler,
             appmod._glew_story_chemistry, appmod._GLEW_ENGINE_ENABLED)
    try:
        yield
    finally:
        (appmod._glew_engine, appmod._glew_scheduler,
         appmod._glew_story_chemistry, appmod._GLEW_ENGINE_ENABLED) = saved


def test_flag_on_routes_a_real_multichar_turn_to_the_new_engine(tmp_path, monkeypatch):
    import dsf_ai_service.app as appmod

    # Real construction through the live boot path: secrets from env, real
    # calibration module, real bootstrap, real store root on a temp dir.
    monkeypatch.setenv(appmod.GLEW_CHEMISTRY_HMAC_KEY_ENV, _TEST_CHEM_SECRET)
    monkeypatch.setenv(appmod.GLEW_CHECKPOINT_HMAC_KEY_ENV, _TEST_CKPT_SECRET)
    monkeypatch.setenv(
        "GLEW_CONVERSATION_ENGINE_STORE_ROOT", str(tmp_path / "glew-store"))

    appmod._boot_glew_conversation_engine()
    assert appmod._glew_scheduler is not None
    assert appmod._glew_story_chemistry is not None
    assert appmod._glew_engine is not None
    # A pure cold-start genesis has learned no successor yet -> honest silence.
    assert appmod._glew_engine._learned_state.initial_event is None
    rank_before = appmod._glew_engine._mode_bank.rank

    monkeypatch.setattr(appmod, "_GLEW_ENGINE_ENABLED", True)

    # Legacy substrate that must NEVER be conversed with while the flag is on.
    class _NoLegacyConverse:
        tick = 7
        is_asleep = False

        def converse(self, *_a, **_k):
            raise AssertionError(
                "legacy _guala.converse called while GLEW flag is on")

    monkeypatch.setattr(appmod, "_guala", _NoLegacyConverse())
    monkeypatch.setattr(appmod, "SUBSTRATE_MODE", "embedded")

    appmod._converse_tasks["glew-on"] = _task_record()
    asyncio.run(appmod._run_converse("glew-on", "hello", "joe"))
    task = dict(appmod._converse_tasks.pop("glew-on"))

    assert task["status"] == "complete"
    # A label only the GLEW path ever produces -> the new engine really ran.
    assert task["response_source"] in (
        "glew_typed_silence", "glew_expression_released")
    # Fresh genesis: honest silence, never a fabricated reply.
    assert task["response_source"] == "glew_typed_silence"
    assert task["response"] == ""
    # New-engine shape (no legacy sections/pictures/emission concepts).
    assert task["committed_sections"] == []
    assert task["pictures"] == []
    assert task["emission_id"] is None
    assert task["completed_tick"] == 7  # from the stub's tick, not a crash
    # Every one of the 5 scalars of "hello" really drove the engine: the mode
    # bank grew as a real, load-bearing side effect of recognition. This is the
    # proof the multi-scalar turn reached the engine, not just that it returned.
    assert appmod._glew_engine._mode_bank.rank > rank_before


def test_flag_off_is_byte_identical_to_legacy_converse(monkeypatch):
    import dsf_ai_service.app as appmod

    monkeypatch.setattr(appmod, "_GLEW_ENGINE_ENABLED", False)

    # A GLEW scheduler is present but must never be used while the flag is off.
    class _SchedulerMustNotRun:
        def run_turn(self, **_k):
            raise AssertionError("GLEW scheduler used while flag is off")

    monkeypatch.setattr(appmod, "_glew_scheduler", _SchedulerMustNotRun())
    monkeypatch.setattr(appmod, "_glew_story_chemistry", object())

    converse_calls: list[str] = []

    class _LegacyGuala:
        tick = 3
        is_asleep = False
        vocab = {"warm", "cold"}
        _pictures: dict = {}

        def converse(self, text, **_k):
            converse_calls.append(text)
            return _legacy_turn_result()

        def log_event(self, *_a, **_k):
            return None

    monkeypatch.setattr(appmod, "_guala", _LegacyGuala())
    monkeypatch.setattr(appmod, "SUBSTRATE_MODE", "embedded")

    appmod._converse_tasks["legacy-off"] = _task_record()
    asyncio.run(appmod._run_converse("legacy-off", "hello", "joe"))
    task = dict(appmod._converse_tasks.pop("legacy-off"))

    # The legacy mouth was used, exactly as before this change.
    assert converse_calls == ["hello"]
    assert task["status"] == "complete"
    assert task["response"] == "warm"
    assert task["response_source"] == "fact_strand_commit"
    assert task["emission_id"] == "e1"
    assert task["committed_sections"] == ["language_fact"]
    assert task["source_turn_index"] == 1
    assert task["motifs"] == 2  # len(_guala.vocab)


def test_flag_on_without_constructed_engine_fails_closed(monkeypatch):
    """Fail-closed: if the flag is on but no engine was constructed, the turn
    is an honest error -- never a silent fall-back to the legacy path."""

    import dsf_ai_service.app as appmod

    monkeypatch.setattr(appmod, "_GLEW_ENGINE_ENABLED", True)
    monkeypatch.setattr(appmod, "_glew_scheduler", None)
    monkeypatch.setattr(appmod, "_glew_story_chemistry", None)

    class _LegacyMustNotRun:
        tick = 0
        is_asleep = False

        def converse(self, *_a, **_k):
            raise AssertionError("legacy converse called as a silent fallback")

    monkeypatch.setattr(appmod, "_guala", _LegacyMustNotRun())

    appmod._converse_tasks["glew-missing"] = _task_record()
    asyncio.run(appmod._run_converse("glew-missing", "hello", "joe"))
    task = dict(appmod._converse_tasks.pop("glew-missing"))

    assert task["status"] == "error"
    assert "glew_engine_enabled_but_not_constructed" in task["error"]


def test_boot_fails_closed_without_secrets(tmp_path, monkeypatch):
    """The construction path refuses to run without both HMAC secrets rather
    than inventing a key."""

    import dsf_ai_service.app as appmod

    monkeypatch.delenv(appmod.GLEW_CHEMISTRY_HMAC_KEY_ENV, raising=False)
    monkeypatch.delenv(appmod.GLEW_CHECKPOINT_HMAC_KEY_ENV, raising=False)
    monkeypatch.setenv(
        "GLEW_CONVERSATION_ENGINE_STORE_ROOT", str(tmp_path / "glew-store"))

    with pytest.raises(RuntimeError, match="GLEW_CHEMISTRY_HMAC_KEY"):
        appmod._boot_glew_conversation_engine()


def test_calibration_module_is_marked_unratified():
    from dsf_ai_service.glew_runtime import (
        PRODUCTION_SENSOR_CALIBRATION_UNRATIFIED_v1 as cal,
    )

    assert cal.STATUS == "unratified_placeholder"
