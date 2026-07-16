"""Focused production contracts for real-boundary BindingWindow closes.

GL-RPT-WAL-BLOAT-RAM-ROOT-CAUSE-C1-20260715 F2: ``close()`` resolved its
target through the CLOSING caller's bound contextvar, so a close issued from
a different thread -- or from a different copied ``contextvars.Context``
(app.py's ``_run_lifecycle_executor`` runs every executor job in a fresh
copy, discarded at job end) -- than the opener silently no-oped.  Live cost
when found: 170 never-closed contexts / 30,507 entries / 24.5MB re-embedded
into every ~60s save manifest.  These tests pin the fixed contracts:

  * a real boundary close by EXPLICIT context id succeeds from any thread;
  * an unbound ``close()`` is loud (``window_close_unbound`` event), never
    an invisible no-op;
  * an implicit context closes at its real structural boundary (the same
    caller's next entry that declares an episode/bundle);
  * leaked/orphaned contexts (opener context discarded -- exactly the
    executor-isolation shape) are enumerable via ``open_context_ids()`` and
    closable by explicit id: the engine's activity-end sweep contract;
  * closed windows stay write-once: a recurring context id starts a NEW
    window, never mutates the closed record.
"""

import contextvars
import copy
import sys
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dsf_ai_service.substrate.window_manager import WindowManager


def _manager(*, tick=None, mirror=None, events=None, atlas_calls=None):
    tick = tick if tick is not None else {"value": 0}
    mirror = mirror if mirror is not None else {}
    events = events if events is not None else []
    atlas_calls = atlas_calls if atlas_calls is not None else []

    def atlas_record(section, motif, chi, at_tick, **kwargs):
        atlas_calls.append((section, motif, chi, at_tick, kwargs))

    manager = WindowManager(
        atlas_record_fn=atlas_record,
        log_event_fn=lambda kind, **detail: events.append((kind, detail)),
        get_tick_fn=lambda: tick["value"],
        get_presence_fn=lambda: {"joe": True},
        get_affect_fn=lambda: {"arousal": 0.7, "valence": -0.2},
        get_needs_fn=lambda: {"stability": 0.6, "connection": 0.8},
        atlas_windows=mirror,
    )
    return manager, tick, mirror, events, atlas_calls


def test_cross_thread_boundary_close_succeeds_with_explicit_id():
    manager, _tick, _mirror, events, _calls = _manager()
    errors = []

    def opener():
        # The production shape: an attending-audio tick on the autonomy
        # thread declares its episode; the manager infers the context id
        # "episode:" + episode_ref and binds it to THIS thread only.
        try:
            manager.add_entry(
                modality="sound", section="audio_low", motif_id=7, chi=31,
                tick=1, source_tag="attending_audio", trigger_reason="sound",
                episode_ref="episode:attending_audio:100:snd1")
        except BaseException as error:  # surfaced below
            errors.append(error)

    thread = threading.Thread(target=opener)
    thread.start()
    thread.join(timeout=5)
    assert not errors
    context_id = "episode:episode:attending_audio:100:snd1"
    assert context_id in manager.snapshot()["open_contexts"]

    # The old defect, now loud: a contextvar-resolved close from a thread
    # that opened nothing cannot see the context -- and says so.
    assert manager.close("activity_ended") is None
    assert ("window_close_unbound",
            {"close_reason": "activity_ended"}) in events
    assert context_id in manager.snapshot()["open_contexts"]

    # The fix: the real boundary passes the explicit id; the closing
    # thread is irrelevant (this is the main thread, not the opener).
    window_id = manager.end_context(context_id, "activity_ended")
    assert window_id is not None
    record = manager.windows[window_id]
    assert record["close_reason"] == "activity_ended"
    assert record["context_id"] == context_id
    assert manager.snapshot()["open_contexts"] == {}
    # The closed window is durable, recallable memory.
    assert manager.lookup_chi(31)[0]["window_id"] == window_id


def test_implicit_context_closes_at_its_structural_boundary():
    manager, _tick, _mirror, _events, _calls = _manager()
    caller_context = contextvars.copy_context()

    # Bare sensory entry: no context_id, no episode/bundle -> the manager
    # mints an implicit container for it, bound to this caller's context.
    caller_context.run(lambda: manager.add_entry(
        modality="sound", section="audio_mid", motif_id=1, chi=41,
        tick=1, source_tag="mic:live", trigger_reason="sound"))
    implicit_ids = manager.open_context_ids("implicit:")
    assert len(implicit_ids) == 1
    open_record = manager.snapshot()["open_contexts"][implicit_ids[0]]
    assert open_record["context_origin"] == "implicit"

    # The SAME caller then declares real structure.  That is exactly the
    # implicit container's boundary: it closes; the episode context opens.
    # (Before the fix the implicit context had origin "legacy", which the
    # boundary check skipped -- it absorbed the episode entry and lived
    # forever.)
    caller_context.run(lambda: manager.add_entry(
        modality="sight", section="sight", motif_id=2, chi=42,
        tick=2, source_tag="attending_visual", trigger_reason="sight",
        episode_ref="episode:attending_visual:5:pic1"))

    assert manager.open_context_ids("implicit:") == ()
    assert manager.open_context_ids("episode:") == (
        "episode:episode:attending_visual:5:pic1",)
    closed_implicit = [record for record in manager.windows.values()
                       if record["context_id"].startswith("implicit:")]
    assert len(closed_implicit) == 1
    assert closed_implicit[0]["close_reason"] == "context_boundary"
    assert len(closed_implicit[0]["entries"]) == 1
    assert closed_implicit[0]["entries"][0]["chi"] == 41
    # The episode entry landed in the episode window, not the implicit one.
    episode_open = manager.snapshot()["open_contexts"][
        "episode:episode:attending_visual:5:pic1"]
    assert [entry["chi"] for entry in episode_open["entries"]] == [42]


def test_leaked_contexts_close_at_their_next_real_boundary_by_explicit_id():
    """The engine's _end_activity sweep contract (Guala._close_boundary_
    window_contexts): contexts opened inside a discarded contextvars
    Context -- app.py's per-executor-job isolation, the exact production
    leak shape -- are enumerable via open_context_ids() and closable by
    explicit id, including ones no live thread has ever bound."""
    manager, _tick, _mirror, _events, _calls = _manager()

    # Two mic-frame implicit contexts and one attending-audio episode, each
    # opened the way production leaked them: the opening Context is thrown
    # away, so no later caller can ever resolve them through a contextvar.
    for index in range(2):
        contextvars.copy_context().run(lambda index=index: manager.add_entry(
            modality="sound", section="audio_low", motif_id=index, chi=51,
            tick=index + 1, source_tag="mic:live", trigger_reason="sound"))
    contextvars.copy_context().run(lambda: manager.add_entry(
        modality="sound", section="audio_high", motif_id=9, chi=52,
        tick=3, source_tag="attending_audio", trigger_reason="sound",
        episode_ref="episode:attending_audio:200:snd9"))

    assert len(manager.open_context_ids("implicit:")) == 2
    assert manager.open_context_ids("episode:episode:attending_") == (
        "episode:episode:attending_audio:200:snd9",)
    # Nothing is bound anywhere: the contextvar close path can never reach
    # these (this was the live 170-context leak).
    assert manager.close("activity_boundary") is None

    # The sweep: enumerate + explicit-id close, exactly what the engine
    # does at every activity end.
    for prefix in ("episode:episode:attending_", "implicit:"):
        for context_id in manager.open_context_ids(prefix):
            assert manager.end_context(
                context_id, "activity_boundary") is not None

    assert manager.snapshot()["open_contexts"] == {}
    assert len(manager.windows) == 3
    # All three are durable closed windows, present in the chi index.
    assert len(manager.lookup_chi(51)) == 2
    assert len(manager.lookup_chi(52)) == 1
    # Double-close (two boundaries racing) is benign, never an error.
    assert manager.end_context(
        "episode:episode:attending_audio:200:snd9",
        "activity_boundary") is None


def test_closed_windows_stay_write_once_when_a_context_id_recurs():
    manager, _tick, _mirror, _events, _calls = _manager()
    context_id = "episode:episode:attending_audio:300:snd3"
    manager.add_entry(
        modality="sound", section="audio_low", motif_id=1, chi=61,
        tick=1, source_tag="attending_audio", trigger_reason="sound",
        context_id=context_id)
    first = manager.end_context(context_id, "activity_ended")
    assert first is not None
    frozen = copy.deepcopy(manager.windows[first])

    # A straggler entry with the same context id (an add racing the
    # boundary close) starts a NEW window; the closed record never mutates.
    manager.add_entry(
        modality="sound", section="audio_low", motif_id=2, chi=61,
        tick=2, source_tag="attending_audio", trigger_reason="sound",
        context_id=context_id)
    second = manager.end_context(context_id, "activity_boundary")
    assert second is not None and second != first
    assert manager.windows[first] == frozen
    assert len(manager.lookup_chi(61)) == 2
