"""
DSF-AI Service — FastAPI Application
=====================================
Three endpoints:
  POST /api/v1/analyze        — CSV upload → kernel → JSON report + LLM narrative
  POST /api/v1/cluster        — element + N → screener → properties JSON
  POST /api/v1/cluster/screen — batch screening with constraints

TRADE SECRET — kernel internals never leave the server.
"""

import os
import sys
import io
import csv
import time
import math
import heapq
import logging
import statistics
import hashlib as _hashlib
import traceback


def deterministic_motif_id(name):
    """1.5: Deterministic motif ID — replaces hash()%1000."""
    return int(_hashlib.md5(name.encode()).hexdigest()[:8], 16) % 10000


def decode_image_bytes(img_bytes):
    """H5a: Shared HEIC-capable image decode for every image route.
    Returns (full_image, gray_grid_64x64, orig_w, orig_h) or raises."""
    try:
        import pillow_heif
        pillow_heif.register_heif_opener()
    except ImportError:
        pass
    from PIL import Image
    import io as _io
    img_full = Image.open(_io.BytesIO(img_bytes))
    if img_full.mode not in ('RGB', 'L'):
        img_full = img_full.convert('RGB')
    orig_w, orig_h = img_full.size
    img_gray = img_full.convert('L').resize((64, 64))
    grid = np.array(img_gray, dtype=np.float64) / 255.0
    return img_full, grid, orig_w, orig_h
from typing import Optional, List, Dict, Literal

from fastapi import FastAPI, File, UploadFile, HTTPException, Form, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse, Response
from pydantic import BaseModel

# Add project root to path so we can import uf_core and tools
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from dsf_ai_service.kernel_runner import run_analysis
from dsf_ai_service.integrity import initialize_integrity, get_integrity_status
from dsf_ai_service.cluster_screener import (
    predict_cluster,
    screen_clusters,
    find_thermocouple_pairs,
)
from dsf_ai_service.narrator import narrate_results
from dsf_ai_service.cff_discovery import run_discovery, verify_candidate

# ═══════════════════════════════════════════════════════════════
# GL-ARCH-FRONTEND-SPLIT: substrate mode
# ═══════════════════════════════════════════════════════════════
SUBSTRATE_MODE = os.environ.get("SUBSTRATE_MODE", "embedded")  # "embedded" or "remote"
_substrate_client = None
_converse_client = None  # kept for API compat; no longer used for SSE

# ── GL-CMD-CONVERSE-TASK-PATTERN-62: 202 + poll task registry ─────────────────
from typing import Dict, Any
from uuid import uuid4
_converse_tasks: Dict[str, Dict[str, Any]] = {}
_TASK_TTL_SECONDS = 300  # 5 min after complete before GC

# ── GL-CMD-LOCK-CONTENTION-FIX-182 L3: frame backpressure ──────────────────
# /sight_frame and /sound_frame used to queue unboundedly in the default
# executor whenever frames arrived faster than they could be processed
# (measured live: individual calls holding self.lock for up to ~93s while
# camera+mic streamed continuously), which could starve converse() no
# matter how bounded any single call's own work is. Cap concurrent
# in-flight frame jobs per kind; anything over the cap is dropped
# immediately (never queued) with an honest response and a counter,
# rather than piling up silently.
import threading
_frame_inflight_lock = threading.Lock()
_FRAME_INFLIGHT_MAX = 1
_frame_inflight = {"sight": 0, "sound": 0}
_frame_dropped = {"sight": 0, "sound": 0}

from dsf_ai_service.substrate.auditory_pcm_stream import (
    AuditoryPCMStreamRegistry,
    PCM_SAMPLE_RATE_HZ as _PCM_STREAM_SAMPLE_RATE_HZ,
    pcm_s16le_wav as _pcm_s16le_wav,
)
from dsf_ai_service.substrate.auditory_incremental_terminal import (
    AuditoryIncrementalTerminalEvent,
)

_auditory_pcm_streams = AuditoryPCMStreamRegistry()
_auditory_pcm_epoch_lock = threading.RLock()

# ── STT boundary transducer (port of stranded a8277fa onto the live
# lineage) ──────────────────────────────────────────────────────────────────
# One CTranslate2 whisper model is one physical recognition resource: a
# dedicated single-worker executor owns the call side, serializing
# inference.  Spec v3 STT staging: inference itself runs in the
# out-of-process worker by DEFAULT (VOICE_WHISPER_WORKER, default 1) so it
# never competes for this process's GIL or RAM; VOICE_WHISPER_WORKER=0 is
# the explicit embedded escape hatch.  Whisper is a SENSE TRANSDUCER at the
# boundary, like the ffmpeg WebM->WAV decode: never part of cognition.
# See dsf_ai_service/speech_transducer.py.
import concurrent.futures as _concurrent_futures
_speech_recognition_executor = _concurrent_futures.ThreadPoolExecutor(
    max_workers=1,
    thread_name_prefix="speech-recognition",
)


def _speech_transduction_enabled():
    """Live read (never cached) so config honesty survives env changes."""
    return os.environ.get("VOICE_WHISPER", "0") == "1"


# GL-FIX-VOICE-REPLY-DOOR-20260720: recognized speech used to enter ONLY
# through read_sentence() -- the same door as passive corpus reading. That
# door updates memory/presence but has no step that ever composes a reply;
# converse() (the door typed chat uses) is the one real mechanism that both
# processes input AND generates a turn. A full minute of continuously
# recognized speech (confirmed live: 7 consecutive real transcriptions)
# produced zero replies because nothing on the voice path had ever called
# converse() -- not a threshold to tune, a missing call.
#
# converse() is genuinely slow (measured history: 49-94s for a full
# six-section compose, and a past incident where holding self.lock for that
# long starved the container health check and got the task killed).
# CONVERSE_PHASED=1 (confirmed set on the live task) already splits
# self.lock from self._emission_lock for exactly this reason -- calling
# converse() off the request thread, in a dedicated single-worker executor
# (so a still-composing reply is never joined by a second overlapping one),
# is safe under that split; it would not have been safe under the
# unphased path.  A single worker means back-to-back recognized utterances
# naturally serialize instead of racing. One additional terminal may wait
# behind the active turn; a third is rejected explicitly. This single-slot
# admission preserves a contiguous exchange without permitting a backlog.
_voice_reply_executor = _concurrent_futures.ThreadPoolExecutor(
    max_workers=1,
    thread_name_prefix="voice-reply",
)
_voice_reply_busy = threading.Event()
_voice_reply_state_lock = threading.Lock()
_voice_reply_pending = None
_voice_reply_active_event_id = None
_voice_turn_results = {}
_VOICE_TURN_RESULT_CAPACITY = 8


def _run_voice_reply(terminal_event, tick_hint):
    """Runs on the single voice-reply worker thread, never the request
    thread. Mirrors substrate_runner's autonomous-emission loop's own
    result contract (_last_autonomous_thought) so the existing /thought
    poll surfaces a voice-triggered reply with zero new frontend work --
    and self-hears on a real release, same as every other release
    authority (one mouth, GL Change 4)."""
    import dsf_ai_service.substrate_runner as _sr
    t0 = time.time()
    terminal_event.verify()
    terminal_event_id = terminal_event.event_id
    terminal_receipt = terminal_event.authority_receipt_sha256
    spoken_text = terminal_event.tutor_label
    delivery = {
        "status": "completed_without_speech",
        "terminal_event_id": terminal_event_id,
        "causal_experience_id": terminal_event_id,
        "causal_intake_receipt_sha256": terminal_receipt,
    }
    try:
        if _guala is None:
            return
        # Auditory form recognition does not prove who produced the sound.
        # Keep the heard turn available to conversation without fabricating
        # Joe's pair-bond identity from a mono waveform.
        turn_result = _guala.converse(
            spoken_text,
            source="auditory:unresolved_source",
            causal_intake=terminal_event,
        )
        if (
            turn_result.causal_experience_id != terminal_event_id
            or turn_result.causal_intake_receipt_sha256 != terminal_receipt
        ):
            raise RuntimeError(
                "voice reply lost its auditory causal experience"
            )
        content = (turn_result.response or "").strip()
        response_source = turn_result.response_source
        delivery.update({
            "response_source": response_source,
            "emission_id": turn_result.emission_id,
            "committed_sections": list(turn_result.committed_sections),
        })
        print(f"[voice-reply] {time.time()-t0:.3f}s "
              f"response_source={response_source} "
              f"committed={bool(content)}")
        if not content:
            return
        speech_audio = None
        speech_output_status = "browser_noncausal"
        if response_source == "causal_action_cycle_commit":
            speech_audio = _sr._synthesize_released_voice(
                content, response_source
            )
            speech_output_status = (
                "delivered"
                if speech_audio is not None
                else "actuator_unavailable"
            )
        with _sr._autonomous_thought_lock:
            _sr._last_autonomous_thought = {
                "speech": content,
                "tick": _guala.tick,
                "ts": time.time(),
                "category": "voice_reply",
                "source": "guala",
                "response_source": response_source,
                "emission_id": turn_result.emission_id,
                "terminal_event_id": terminal_event_id,
                "causal_experience_id": terminal_event_id,
                "causal_intake_receipt_sha256": terminal_receipt,
                "committed_sections": list(turn_result.committed_sections),
                "commit_provenance": [
                    p.as_record() if hasattr(p, "as_record") else p
                    for p in turn_result.commit_provenance],
                "speech_audio": speech_audio,
                "speech_output_status": speech_output_status,
            }
        delivery = {
            "status": (
                "completed_without_speech"
                if speech_output_status == "actuator_unavailable"
                else "completed"
            ),
            "terminal_event_id": terminal_event_id,
            "causal_experience_id": terminal_event_id,
            "causal_intake_receipt_sha256": terminal_receipt,
            (
                "intended_speech"
                if speech_output_status == "actuator_unavailable"
                else "speech"
            ): content,
            "speech_audio": speech_audio,
            "speech_output_status": speech_output_status,
            "tick": _guala.tick,
            "response_source": response_source,
            "emission_id": turn_result.emission_id,
            "committed_sections": list(turn_result.committed_sections),
        }
    except Exception as error:
        delivery = {
            "status": "error",
            "terminal_event_id": terminal_event_id,
            "causal_experience_id": terminal_event_id,
            "causal_intake_receipt_sha256": terminal_receipt,
            "error": f"{type(error).__name__}: {error}",
        }
        print(f"[voice-reply] error after {time.time()-t0:.3f}s: "
              f"{type(error).__name__}: {error}")
        try:
            if _guala is not None:
                _guala._log_substrate_event(
                    "voice_reply_error", tick_hint=tick_hint,
                    error=str(error))
        except Exception:
            pass
    finally:
        global _voice_reply_pending, _voice_reply_active_event_id
        with _voice_reply_state_lock:
            _voice_turn_results[terminal_event_id] = delivery
            while len(_voice_turn_results) > _VOICE_TURN_RESULT_CAPACITY:
                del _voice_turn_results[next(iter(_voice_turn_results))]
            pending = _voice_reply_pending
            _voice_reply_pending = None
            if pending is None:
                _voice_reply_active_event_id = None
                _voice_reply_busy.clear()
            else:
                _voice_reply_active_event_id = pending[0].event_id
                try:
                    _voice_reply_executor.submit(_run_voice_reply, *pending)
                except Exception as submit_error:
                    pending_event = pending[0]
                    if _guala is not None:
                        _guala.discard_unadmitted_auditory_terminal(
                            pending_event
                        )
                    _voice_turn_results[pending_event.event_id] = {
                        "status": "error",
                        "terminal_event_id": pending_event.event_id,
                        "causal_experience_id": pending_event.event_id,
                        "causal_intake_receipt_sha256": (
                            pending_event.authority_receipt_sha256
                        ),
                        "error": (
                            f"{type(submit_error).__name__}: "
                            f"{submit_error}"
                        ),
                    }
                    while (
                        len(_voice_turn_results)
                        > _VOICE_TURN_RESULT_CAPACITY
                    ):
                        del _voice_turn_results[
                            next(iter(_voice_turn_results))
                        ]
                    _voice_reply_active_event_id = None
                    _voice_reply_busy.clear()


def _maybe_trigger_voice_reply(terminal_event, tick_hint):
    """Non-blocking: submits at most one converse() call at a time to the
    dedicated voice-reply worker. Called right after a real transcript is
    recognized; never called from read_sentence's own path (that would
    double-process the same words -- converse() already reads its input
    into the substrate as part of composing a reply)."""
    if not isinstance(terminal_event, AuditoryIncrementalTerminalEvent):
        raise TypeError(
            "voice reply admission requires an auditory terminal event"
        )
    terminal_event.verify()
    global _voice_reply_pending, _voice_reply_active_event_id
    with _voice_reply_state_lock:
        terminal_event_id = terminal_event.event_id
        if (
            terminal_event_id == _voice_reply_active_event_id
            or (
                _voice_reply_pending is not None
                and _voice_reply_pending[0].event_id == terminal_event_id
            )
        ):
            if _guala is not None:
                _guala._log_substrate_event(
                    "auditory_reply_duplicate_ignored",
                    terminal_event_id=terminal_event_id,
                )
            return False
        if terminal_event_id in _voice_turn_results:
            if _guala is not None:
                _guala.discard_unadmitted_auditory_terminal(terminal_event)
                _guala._log_substrate_event(
                    "auditory_reply_replay_rejected",
                    terminal_event_id=terminal_event_id,
                )
            return False
        if _voice_reply_busy.is_set():
            if _voice_reply_pending is not None:
                if _guala is not None:
                    _guala.discard_unadmitted_auditory_terminal(
                        terminal_event
                    )
                    _guala._log_substrate_event(
                        "auditory_reply_admission_full",
                        terminal_event_id=terminal_event_id,
                    )
                return False
            _voice_reply_pending = (terminal_event, tick_hint)
            return True
        _voice_reply_busy.set()
        _voice_reply_active_event_id = terminal_event_id
        try:
            _voice_reply_executor.submit(
                _run_voice_reply,
                terminal_event,
                tick_hint,
            )
            return True
        except Exception:
            _voice_reply_active_event_id = None
            _voice_reply_busy.clear()
            if _guala is not None:
                _guala.discard_unadmitted_auditory_terminal(terminal_event)
                _guala._log_substrate_event(
                    "voice_reply_submit_error",
                    terminal_event_id=terminal_event_id,
                )
            return False


def _speech_result_wall_timeout():
    """Belt-and-braces wall for awaiting the STT future (3x the worker's own
    per-request timeout).  Adversarial-review hardening: if the worker/queue
    machinery ever wedges past its internal deadlines, the frame degrades to
    the typed unavailable error instead of pinning the executor thread (and
    its deployment-lifecycle mutation admit) forever.  Crash-safe parse:
    garbage falls back to the default."""
    try:
        per_request = float(
            os.environ.get("SPEECH_WORKER_REQUEST_TIMEOUT_S", "30"))
    except (TypeError, ValueError):
        per_request = 30.0
    if not (per_request > 0) or per_request != per_request \
            or per_request == float("inf"):
        per_request = 30.0
    return 3.0 * min(max(per_request, 0.1), 3600.0)


def _prewarm_speech_transducer():
    """Steady-state STT pre-warm; runs on the owned speech executor thread.

    Spec v3 STT staging / acceptance criterion 7: the worker (or, under the
    VOICE_WHISPER_WORKER=0 escape hatch, the in-process model) spawns at
    steady state only — never during boot (the 2026-07-16 boot OOM is why).
    Failure is loud but contained: every subsequent frame reports the same
    failure visibly (status="error"), and the UI's honest banner path
    ("spoken-word recognition unavailable") keeps working.
    """
    try:
        from dsf_ai_service.speech_transducer import require_speech_recognizer
        require_speech_recognizer()
        print("[voice-whisper] recognizer ready (steady-state pre-warm)")
    except Exception as recognition_error:
        print("[voice-whisper] steady-state pre-warm error="
              f"{type(recognition_error).__name__}: {recognition_error}")


def _kick_speech_prewarm_after_ready():
    """Kick the STT pre-warm strictly AFTER readiness; first use also warms.

    Called only once _init_complete is True.  Returns the executor future
    (tests observe it), or None when STT is off — in which case nothing is
    ever constructed and the honest-unavailable report stands.
    """
    if not _speech_transduction_enabled():
        return None
    return _speech_recognition_executor.submit(_prewarm_speech_transducer)


def _speech_status_snapshot():
    """Telemetry for /health: never constructs a recognizer or a worker."""
    try:
        from dsf_ai_service.speech_transducer import speech_transducer_status
        return {"enabled": _speech_transduction_enabled(),
                **speech_transducer_status()}
    except Exception as error:  # health must always answer
        return {"enabled": _speech_transduction_enabled(),
                "error": f"{type(error).__name__}: {error}"}


def _spoken_word_recognition_report(source):
    """Report that deterministic auditory L5 did not receive this request."""
    if _guala is None and not _is_remote():
        return {
            "capability": "spoken_word_recognition",
            "available": False,
            "status": "unavailable",
            "reason": "auditory L5 is not ready",
            "mechanism": "directed_joint_causal_path_complex",
            "raw_sensing": {"available": False,
                            "mechanism": "causal_gammatone_erb_v1"},
        }
    return {
        "capability": "spoken_word_recognition",
        "available": True,
        "status": "not_attempted",
        "mechanism": "directed_joint_causal_path_complex",
        "raw_sensing": {"available": True, "mechanism": "causal_gammatone_erb_v1"},
    }


def _auditory_l5_spoken_report(auditory_status):
    recognition = next(
        (
            value for value in auditory_status.get("recognitions", [])
            if value.get("kind") == "spoken_form"
        ),
        None,
    )
    state = recognition.get("state") if recognition else "unknown"
    label = recognition.get("tutor_label") if recognition else None
    return {
        "capability": "spoken_word_recognition",
        "available": True,
        "status": state,
        "recognized_form": label,
        "candidate_labels": (
            recognition.get("candidate_labels", []) if recognition else []
        ),
        "experience_id": auditory_status.get("latest_experience_id"),
        "mechanism": "directed_joint_causal_path_complex",
        "raw_sensing": {"available": True, "mechanism": "causal_gammatone_erb_v1"},
    }


def _frame_backpressure_acquire(kind):
    """True if this frame may proceed; False if it was dropped (over capacity)."""
    with _frame_inflight_lock:
        if _frame_inflight[kind] >= _FRAME_INFLIGHT_MAX:
            _frame_dropped[kind] += 1
            return False
        _frame_inflight[kind] += 1
        return True


def _frame_backpressure_release(kind):
    with _frame_inflight_lock:
        _frame_inflight[kind] = max(0, _frame_inflight[kind] - 1)


# ── GL-CMD-CONVERSE-FRAME-PRIORITY: talking has priority over raw frames ─────
# Root cause, measured live (mic+camera streaming): the conversational turn
# (legacy converse() OR the GLEW MultiScalarTurnScheduler) runs in the SAME
# single uvicorn process as continuous /sound_frame (~0.2-0.35s CPU each) and
# /sight_frame processing. One core + the GIL means those always-runnable frame
# jobs starve the turn's pure-Python/flint compute: a local harness reproduced
# the exact mechanism -- the same real 5-scalar turn stretched x1.9 under 1
# competing CPU thread, x5.9 under 2, x12.9 under 4 (super-linear, because the
# flint turn keeps releasing/re-acquiring the GIL against greedy competitors).
# The legacy engine suffered identically under the same load in production
# (a 'hello' took 111s), confirming this is process-level contention, not
# GLEW-specific compute.
#
# Fix (Joe's standing ruling, "let talking be its own thing"): while a real
# conversational turn is settling, shed incoming sensory frames using the SAME
# honest backpressure path these endpoints already have (the UI already renders
# it gracefully), so the turn gets the core. This is a pure capacity/priority
# yield -- never gated on frame CONTENT, and only in embedded (in-process) mode
# where the contention exists (remote mode ring-writes frames to another
# process). A plain GIL-atomic counter (mirrors _frame_inflight) with a
# balanced begin/finally in _run_converse guarantees it can never stick "on".
#
# TIME-BOXED (amendment after the first live deploy): unconditional whole-turn
# shedding had two verified defects (full code-trace, 2026-07-15): (1) a SLOW
# turn blacked out all sensory intake for its entire duration AND silenced both
# background tick sources (frame ingestion is itself an incidental tick source
# via Section.receive, and autonomy is paused during converse), making the
# substrate look frozen; (2) a turn whose executor call never returns would
# shed frames until process restart (the finally can't run if the await never
# completes). The trace also proved the priority window that actually matters
# is the first few seconds -- the real quiet-turn compute is ~1.7-2.7s -- so
# shedding is now bounded: frames are shed only within the first
# _CONVERSE_PRIORITY_WINDOW_S of the OLDEST in-flight turn, then flow again
# even while it is still settling. This is a distinct frame-admission window,
# not the causal scheduling owner used by sensory settlement. The deadline
# doubles as the stuck-counter watchdog: a hung turn's window simply
# expires, so a never-returning await can no longer blind the process.
_converse_inflight_lock = threading.Lock()
_converse_inflight = 0
_converse_window_started_at = 0.0
_CONVERSE_PRIORITY_WINDOW_S = 2.5


def _converse_turn_begin():
    """Mark that a real conversational turn is settling in this process."""
    global _converse_inflight, _converse_window_started_at
    with _converse_inflight_lock:
        _converse_inflight += 1
        if _converse_inflight == 1:
            # Window opens with the FIRST concurrent turn only; queued turns
            # serialize on the engine lock anyway, and re-arming per turn
            # would let a steady stream of turns black out senses forever.
            _converse_window_started_at = time.time()


def _converse_turn_end():
    """Clear one settling-turn mark (always called from a finally)."""
    global _converse_inflight
    with _converse_inflight_lock:
        _converse_inflight = max(0, _converse_inflight - 1)


def _converse_turn_in_flight():
    """True only while a settling turn is inside its bounded priority window.

    A turn that outlives _CONVERSE_PRIORITY_WINDOW_S keeps settling but loses
    frame priority: senses resume, background ticking resumes, and a hung turn
    can never blind the process until restart.
    """
    if _converse_inflight <= 0:
        return False
    return (time.time() - _converse_window_started_at) < _CONVERSE_PRIORITY_WINDOW_S


def _converse_admission_busy():
    """True while a text-driven conversational turn already occupies the
    engine lock (GL-FIX-CONVERSE-ADMIT-GUARD-20260720).

    Typed converse had no admission guard, unlike voice's own
    _voice_reply_busy: every /listen or plain-text request immediately
    created a new task and scheduled it, no matter how many turns were
    already queued on the engine lock. Each turn is measured at 49-94s
    (see _run_converse's own comments); a handful of prompts arriving
    close together stacked additively and produced live-observed waits up
    to ~1000s for the last one in line. Reuses _converse_inflight (already
    incremented/decremented around the full body of _run_converse, always
    cleared in a finally) rather than adding parallel bookkeeping.

    Does NOT (yet) coordinate with voice's separate _voice_reply_busy flag
    -- _run_voice_reply calls converse() directly, without going through
    _run_converse, so a voice reply in flight does not set
    _converse_inflight and is not caught by this check. A text prompt can
    still be admitted while a voice reply is composing. That cross-path
    case is a known gap, not addressed here.
    """
    return _converse_inflight > 0


def _converse_admission_rejected_response():
    """Honest, typed 409 instead of accepting a task that would just queue.
    Existing frontend handling already renders `response` as a system
    message for any non-202/500/503 status -- no frontend change needed."""
    return JSONResponse(status_code=409, content={
        "ok": False,
        "busy": True,
        "response": "still composing the last reply — try again in a moment",
        "reason": "a conversational turn is already in progress",
    })


def _prune_stale_tasks():
    """Remove completed tasks older than TTL. Called opportunistically."""
    now = time.time()
    to_delete = [
        tid for tid, task in _converse_tasks.items()
        if task["status"] in ("complete", "error")
        and (now - task.get("completed_at", now)) > _TASK_TTL_SECONDS
    ]
    for tid in to_delete:
        del _converse_tasks[tid]


def _fail_inflight_converse_tasks(reason):
    """GL-CMD-LOCK-CONTENTION-FIX-182 L2: mark every not-yet-terminal
    conversation task as a loud, explicit error instead of letting it
    vanish silently. _converse_tasks is in-memory only (line 75) -- it
    does not survive a process restart, so a deploy landing mid-turn used
    to orphan it: the UI stayed on "(settling...)" forever with nothing
    ever telling it the turn was lost. Called right before the deploy's
    pause (so a client still polling THIS process gets the honest error)
    and from the SIGTERM handler (defense in depth if the pause step is
    ever skipped or the container is killed directly)."""
    now = time.time()
    n_failed = 0
    for task in _converse_tasks.values():
        if task["status"] not in ("complete", "error"):
            task["status"] = "error"
            task["error"] = reason
            task["completed_at"] = now
            n_failed += 1
    # GL-RPT-RAM-FIXES-DEPLOYED-AND-SEAL-DEFECTS defect 3 (2026-07-15):
    # marking the registry alone released NOTHING — the asyncio coroutines
    # kept running and kept their _schedule_mutating_background slots, so a
    # seal drain that relied on this helper could never converge.  Cancel the
    # owning tasks too: cancellation still waits out any in-flight executor
    # thread (_run_lifecycle_executor shields it), and the coroutine's finally
    # releases the mutation slot.  A cancelled turn is exactly as lost as it
    # was a moment later when the deploy retired the process.
    n_cancelled = 0
    for background_task in tuple(_mutating_background_tasks):
        if (background_task.get_name().startswith("converse-")
                and not background_task.done()):
            background_task.cancel()
            n_cancelled += 1
    if n_failed or n_cancelled:
        print(f"[converse-tasks] {n_failed} in-flight task(s) marked error, "
              f"{n_cancelled} cancelled: {reason}")
    return n_failed


class _live_interaction_scope:
    """GL-CMD-CAMERA-TURN-LATENCY priority gate (caller side). Context manager
    that marks a live human interaction (a converse turn, or a real sight/
    sound frame) as pending, so the in-process background lock-hogs (the
    autonomous emission loop, the 5Hz autonomy tick) defer their self.lock
    acquisition and let the live work win the lock first.

    No-op in remote mode or before the substrate is ready (no in-process
    _guala). __exit__ ALWAYS releases the mark -- including on exception -- so
    a turn that raises can never leave her background cognition permanently
    deferred (the try/finally correctness the mandate requires)."""
    __slots__ = ("_guala_ref", "_entered")

    def __enter__(self):
        guala = _guala  # snapshot: release on the same instance we entered
        self._guala_ref = guala
        self._entered = False
        if guala is not None and hasattr(guala, "_enter_live_interaction"):
            try:
                guala._enter_live_interaction()
                self._entered = True
            except Exception:
                self._entered = False
        return self

    def __exit__(self, *exc):
        if self._entered and self._guala_ref is not None:
            try:
                self._guala_ref._exit_live_interaction()
            except Exception:
                pass
        return False


# ═══════════════════════════════════════════════════════════════════════════
# GLEW clean-conversation-engine cutover (feature-flagged, embedded mode only)
# ═══════════════════════════════════════════════════════════════════════════
# When GLEW_CONVERSATION_ENGINE_ENABLED is truthy, the single embedded converse
# path (_run_converse) drives the new ProductionCleanConversationEngine (via
# MultiScalarTurnScheduler) INSTEAD OF the legacy _guala.converse(). This is a
# true cutover of the one existing mouth, never a second parallel path:
#   - flag OFF (default/unset): behaviour is 100% identical to today; the new
#     engine is never constructed and never called.
#   - flag ON: the legacy converse()/sleep-gate/event-log path is not run for
#     that turn -- one mouth, never both. NO SHADOW MODE.
# The engine + scheduler + one mounted story-chemistry runtime are constructed
# exactly once at app startup (fail-closed: a construction failure fails startup
# loudly rather than silently degrading).
_GLEW_ENGINE_ENABLED = os.environ.get(
    "GLEW_CONVERSATION_ENGINE_ENABLED", "0").strip().lower() in (
        "1", "true", "yes", "on")
# Named env vars for the two runtime HMAC secrets. Populated from AWS Secrets
# Manager at deploy time (see report). NEVER hardcode a fallback: a checkpoint
# signed with a boot-random key could never verify after a restart, and a
# hardcoded key is a security hole.
GLEW_CHEMISTRY_HMAC_KEY_ENV = "GLEW_CHEMISTRY_HMAC_KEY"
GLEW_CHECKPOINT_HMAC_KEY_ENV = "GLEW_CHECKPOINT_HMAC_KEY"
_glew_engine = None
_glew_scheduler = None
_glew_story_chemistry = None


def _boot_glew_conversation_engine():
    """Construct the single, long-lived ProductionCleanConversationEngine plus
    its MultiScalarTurnScheduler and one mounted story-chemistry runtime, once,
    at app startup. Fail-closed and loud: any failure raises (failing startup)
    rather than silently degrading. Only invoked when _GLEW_ENGINE_ENABLED is
    true and SUBSTRATE_MODE is embedded (the actually-live production mode)."""
    global _glew_engine, _glew_scheduler, _glew_story_chemistry

    from dsf_ai_service.glew_runtime import (
        PRODUCTION_SENSOR_CALIBRATION_UNRATIFIED_v1 as _glew_cal,
    )
    from dsf_ai_service.glew_runtime.production_runtime_bootstrap import (
        bootstrap_production_clean_conversation_engine,
        resolve_default_generation_store_root,
    )
    from dsf_ai_service.glew_runtime.clean_conversation_engine import (
        GenerationIdentityParameters,
    )
    from dsf_ai_service.glew_runtime.multi_scalar_turn_scheduler import (
        MultiScalarTurnScheduler,
    )
    from dsf_ai_service.glew_runtime.story_chemistry import (
        StoryChemistryStatus, mount_packaged_production_story_chemistry,
    )

    # Fail-closed secret loading. The env vars are populated from AWS Secrets
    # Manager at deploy time; if either is absent, refuse to run rather than
    # invent a key.
    chem_secret = os.environ.get(GLEW_CHEMISTRY_HMAC_KEY_ENV, "")
    ckpt_secret = os.environ.get(GLEW_CHECKPOINT_HMAC_KEY_ENV, "")
    if not chem_secret:
        raise RuntimeError(
            f"GLEW_CONVERSATION_ENGINE_ENABLED is on but "
            f"{GLEW_CHEMISTRY_HMAC_KEY_ENV} is unset -- create the AWS Secrets "
            "Manager secret gualaloom/glew-chemistry-hmac/prod and wire it into "
            "the task definition before enabling the engine")
    if not ckpt_secret:
        raise RuntimeError(
            f"GLEW_CONVERSATION_ENGINE_ENABLED is on but "
            f"{GLEW_CHECKPOINT_HMAC_KEY_ENV} is unset -- create the AWS Secrets "
            "Manager secret gualaloom/glew-checkpoint-hmac/prod and wire it into "
            "the task definition before enabling the engine")
    chem_key = chem_secret.encode("utf-8")
    ckpt_key = ckpt_secret.encode("utf-8")

    if getattr(_glew_cal, "STATUS", None) != "unratified_placeholder":
        raise RuntimeError(
            "GLEW sensor calibration module lost its unratified_placeholder marker")

    # Real, discoverable persistent-storage root on the container's EFS volume.
    # Default derivation: sibling of STATE_DIR named STATE_DIR + basename +
    # "-glew-conversation-engine" (distinct from the legacy "-sealed" store and
    # from GLEW_GENESIS_ROOT). In production STATE_DIR=/app/guala/active, so this
    # resolves to /app/guala/active-glew-conversation-engine on the EFS mount.
    store_root = resolve_default_generation_store_root()
    store_root.mkdir(parents=True, exist_ok=True)

    params = _glew_cal.production_six_lane_runtime_parameters(
        engine_id=_glew_cal.ENGINE_ID,
        chemistry_authentication_key=chem_key,
        chemistry_key_id=_glew_cal.CHEMISTRY_HMAC_KEY_ID,
    )
    identity = GenerationIdentityParameters(
        genesis_identity=_glew_cal.GENESIS_IDENTITY_UUID,
        genesis_generation_uuid=_glew_cal.GENESIS_GENERATION_UUID,
        genesis_tick=0,
    )
    engine = bootstrap_production_clean_conversation_engine(
        generation_store_root=store_root,
        story_chemistry_authentication_key=chem_key,
        story_chemistry_key_id=_glew_cal.CHEMISTRY_HMAC_KEY_ID,
        six_lane_runtime_parameters=params,
        checkpoint_authentication_key=ckpt_key,
        checkpoint_key_id=_glew_cal.CHECKPOINT_HMAC_KEY_ID,
        generation_identity=identity,
        engine_id=_glew_cal.ENGINE_ID,
    )
    mounted = mount_packaged_production_story_chemistry(
        runtime_authentication_key=chem_key,
        runtime_key_id=_glew_cal.CHEMISTRY_HMAC_KEY_ID,
    )
    if mounted.status is not StoryChemistryStatus.MOUNTED or mounted.runtime is None:
        raise RuntimeError(f"GLEW story chemistry mount failed: {mounted.reason}")

    _glew_engine = engine
    _glew_story_chemistry = mounted.runtime
    _glew_scheduler = MultiScalarTurnScheduler(engine=engine)
    fresh = engine._learned_state.initial_event is None
    print(
        f"[glew] ProductionCleanConversationEngine constructed; "
        f"store_root={store_root} mode_bank_rank={engine._mode_bank.rank} "
        + ("state=fresh_genesis(honest-silence-until-a-first-successor-is-"
           "learned+persisted)" if fresh else "state=restored(can-commit-and-"
           "learn-on-live-turns)"))


async def _run_glew_converse_turn(task, task_id, text, source):
    """Drive one real conversational turn through the new engine instead of
    _guala.converse(). Fully replaces the legacy path for this turn (never
    both). Translates the real MultiScalarTurnResult into the existing task
    poll contract, using only real data from the result -- honest empty output
    when the engine is genuinely silent, never a fabricated reply."""
    if _glew_scheduler is None or _glew_story_chemistry is None:
        # Flag on but engine missing -> honest error, never a silent fall-back
        # to the legacy path (startup already fails loudly if construction
        # failed, so this is defense-in-depth).
        raise RuntimeError("glew_engine_enabled_but_not_constructed")

    text = text or ""
    if not text.strip():
        response = ""
        response_source = "glew_typed_silence"
    else:
        turn_result = await _run_lifecycle_executor(
            lambda: _glew_scheduler.run_turn(
                task_id=task_id, text=text,
                story_chemistry=_glew_story_chemistry, source=source))
        if turn_result.all_silent:
            # Genuinely nothing to release -- honest silence, no placeholder.
            response = ""
            response_source = "glew_typed_silence"
        else:
            # Every scalar that actually released visible text, in real causal
            # order. Concatenated for the single-string response contract; never
            # a fabricated single sentence.
            response = "".join(turn_result.visible_scalar_texts)
            response_source = "glew_expression_released"

    # mode_bank rank is the honest new-engine analogue of the legacy vocab count
    # (how many distinct expression modes have been grown), a real int.
    try:
        motifs = _glew_engine._mode_bank.rank if _glew_engine is not None else 0
    except Exception:
        motifs = 0

    task["status"] = "complete"
    task["response"] = response
    task["response_source"] = response_source
    task["motifs"] = motifs
    task["emission_id"] = None          # new engine has no emission_id concept
    task["committed_sections"] = []     # new engine has no legacy "sections"
    task["pictures"] = []               # picture recall not wired on this path
    task["source_turn_index"] = None
    task["completed_tick"] = _guala.tick if _guala else 0
    task["completed_at"] = time.time()


async def _run_converse(
        task_id: str, text: str, source: str, emission_mode=None):
    """Run substrate converse in executor, write result to task registry."""
    task = _converse_tasks.get(task_id)
    if task is None:
        return
    task["status"] = "settling"
    task["phase"] = "processing"
    speech_audio = None
    # GL-BUG-CURRICULUM-LOCK-PRIORITY (Joe, 2026-07-06): "let talking be its
    # own thing" -- live conversation and her own autonomous background
    # reading (curriculum/worldfeed/lookup) both serialize through the same
    # self.lock via read_sentence(), with no priority between them. A
    # previous session (Eve, 2026-06-30, see substrate_runner.py's
    # _curriculum_feed_chunk) already found curriculum thrashing on this
    # lock could make /converse time out at 5s+, and partially mitigated it
    # by pausing OTHER autonomy during a feed -- but never gave live
    # conversation actual priority over an in-progress feed. A plain
    # attribute set/read (no lock needed, GIL-atomic) lets the curriculum
    # loop check "is someone waiting to talk to her right now" between
    # sentences and yield early -- reusing the SAME graceful partial-chunk
    # pattern that function already uses for its own rate-cap gate, so an
    # interrupted chunk just resumes next cycle, nothing is lost.
    #
    # GL-CMD-CONVERSE-FRAME-PRIORITY: mark a real conversational turn in flight
    # for its whole duration (legacy OR GLEW path -- both go through here) so the
    # in-process /sound_frame and /sight_frame handlers shed frames and stop
    # starving this turn's core. Balanced by the finally below: it can never
    # stick "on", even if the turn raises.
    _converse_turn_begin()
    try:
        # GLEW cutover: when the new conversation engine is enabled, IT is the
        # single embedded mouth for this turn. Drive it and return -- the legacy
        # sleep-gate / remote-vs-embedded / _guala.converse() / event-log path
        # below is not run at all for this turn (one mouth, never both -- no
        # shadow mode). Any error here falls to the outer except and is recorded
        # as an honest task error, never silently swallowed or routed to legacy.
        if _GLEW_ENGINE_ENABLED:
            await _run_glew_converse_turn(task, task_id, text, source)
            return
        # Conversations should auto-wake her -- talking to her should wake her.
        # substrate_runner.py's handle_gualaloom_post() already does this
        # (coordinator.wake() alone only sets presence, it does NOT end a
        # SLEEPING/DREAMING activity), but that check was never carried over
        # to this, the actually-live embedded-mode path -- so a real turn
        # arriving during an autonomous sleep cycle ran with no wake at all,
        # at whatever crawling tick rate she rests at, instead of being woken
        # first like every other entry point already does.
        if _guala is not None and _guala.is_asleep and text.strip():
            try:
                _guala.wake_from_sleep(state_dir=STATE_DIR)
                _guala.coordinator.wake(source or "joe", _guala, _guala.needs, _guala.atlas)
            except Exception:
                pass
            if _guala.is_asleep:
                ca = getattr(_guala, "_current_activity", None)
                quiet_kind = getattr(ca, "kind", "sleeping").lower() if ca else "sleeping"
                task["status"] = "complete"
                task["response"] = f"she is {quiet_kind}..."
                task["response_source"] = "sleep_quiet"
                task["motifs"] = len(_guala.vocab) if _guala else 0
                task["emission_id"] = None
                task["completed_tick"] = _guala.tick if _guala else 0
                task["completed_at"] = time.time()
                return
        if _is_remote():
            client = _get_substrate_client()
            result = await client.call(
                "gualaloom_post",
                command="",
                text=text,
                source=source,
                emission_mode=emission_mode,
                timeout=300.0,
            )
            if not isinstance(result, dict):
                raise TypeError("remote converse returned a non-object result")
            response = result["response"]
            response_source = result["response_source"]
            motifs = result.get("motifs", 0)
            emission_id = result.get("emission_id")
            committed_sections = result.get("committed_sections", [])
            picture_refs = result.get("pictures", [])
            source_turn_index = result.get("source_turn_index")
            if response_source == "causal_action_cycle_commit":
                speech_audio = result.get("speech")
        else:
            if _guala is None:
                raise RuntimeError("guala_not_ready")
            # GL-CMD-CAMERA-TURN-LATENCY: mark this live turn pending for its
            # whole duration so the autonomous emission loop / autonomy tick
            # defer self.lock to it. Scope brackets the await: entered before
            # the executor thread runs converse (which takes self.lock),
            # released after it completes OR raises (see _live_interaction_scope).
            with _live_interaction_scope():
                turn_result = await _run_lifecycle_executor(
                    lambda: _guala.converse(text, source=source))
            response = turn_result.response
            response_source = turn_result.response_source
            # All-at-once doctrine (Joe 2026-07-16, "gibberish if that is
            # what it only knows"): a HUMAN turn ending in silence attempts
            # an honest organism babble before answering with nothing.
            # Seeds = the turn's own just-lived words; recall runs
            # LOCK-FREE (two-phase precompute); the in-lock half is
            # assembly-only; conversational=True because this IS the
            # pending turn. Label stays organism_attempt end-to-end.
            if (not response and response_source == "silence_no_commit"
                    and os.environ.get(
                        "CONVERSE_BABBLE_FALLTHROUGH", "1") != "0"):
                try:
                    _released = await _run_lifecycle_executor(
                        lambda: _compose_conversational_organism_fallthrough(
                            text))
                    if _released is not None:
                        response = _released["content"]
                        response_source = _released["response_source"]
                except Exception as _bab_e:
                    print(f"[converse-babble] fall-through failed (honest "
                          f"silence kept): {_bab_e}", flush=True)
            motifs = len(_guala.vocab)
            emission_id = turn_result.emission_id
            committed_sections = list(turn_result.committed_sections)
            source_turn_index = turn_result.source_turn_index
            picture_refs = []
            seen_picture_ids = set()
            for _motif, item_id in turn_result.recalled_pictures:
                if item_id in seen_picture_ids:
                    continue
                picture = _guala._pictures.get(item_id)
                if picture is None:
                    continue
                seen_picture_ids.add(item_id)
                picture_refs.append({"item_id": item_id,
                                     "title": picture.title})
                if len(picture_refs) >= 4:
                    break
            if response and response_source == "causal_action_cycle_commit":
                import dsf_ai_service.substrate_runner as _sr
                speech_audio = await _run_lifecycle_executor(
                    lambda: _sr._synthesize_released_voice(
                        response, response_source
                    )
                )

        # This write is part of the accepted turn.  Await it so deployment
        # quiescence cannot certify the turn complete while its event writer
        # is still mutating EFS in an unowned thread.
        event_guala = _guala
        if event_guala is not None:
            await _run_lifecycle_executor(
                lambda: event_guala.log_event(
                    STATE_DIR, "source_interaction",
                    source=source, words_in=len(text.split()),
                    source_count=source_turn_index),
            )

        task["status"] = "complete"
        task["response"] = response
        task["response_source"] = response_source
        task["motifs"] = motifs
        task["emission_id"] = emission_id
        task["committed_sections"] = committed_sections
        task["pictures"] = picture_refs
        task["source_turn_index"] = source_turn_index
        task["speech_audio"] = speech_audio
        task["speech_output_status"] = (
            "delivered"
            if response_source == "causal_action_cycle_commit"
            and speech_audio is not None
            else "actuator_unavailable"
            if response_source == "causal_action_cycle_commit"
            else "browser_noncausal"
        )
        task["completed_tick"] = _guala.tick if _guala else 0
        task["completed_at"] = time.time()
    except Exception as _e:
        task["status"] = "error"
        task["error"] = str(_e)[:500]
        task["completed_at"] = time.time()
    finally:
        # GL-CMD-CONVERSE-FRAME-PRIORITY: always clear the in-flight mark, on
        # normal completion, early return, or error -- frames must resume the
        # instant the turn settles.
        _converse_turn_end()


_mutating_background_tasks = set()


def _unfinished_mutating_task_names():
    """Names of background mutation owners that have not finished.

    The lifecycle counter is anonymous; when a seal drain times out this is
    the only surface that can say WHICH owner is stuck (defect 2 of
    GL-RPT-RAM-FIXES-DEPLOYED-AND-SEAL-DEFECTS: three deploys failed on an
    unidentifiable holder).
    """
    return sorted(
        task.get_name() for task in _mutating_background_tasks
        if not task.done())


def _schedule_mutating_background(coroutine_factory, *, name):
    """Atomically own a background mutation until its coroutine finishes.

    HTTP middleware owns only the request lifetime.  Endpoints returning 202
    must acquire this second lifecycle count *before* returning, otherwise a
    deploy can close admission between response creation and task startup.
    """
    if not _deployment_lifecycle.admit_mutation():
        raise HTTPException(
            status_code=503,
            detail="deployment quiescence is active",
            headers={"Retry-After": "30"},
        )

    async def _owned():
        try:
            return await coroutine_factory()
        finally:
            _deployment_lifecycle.finish_mutation()

    import asyncio as _aio
    try:
        task = _aio.create_task(_owned(), name=name)
    except BaseException:
        _deployment_lifecycle.finish_mutation()
        raise
    _mutating_background_tasks.add(task)
    task.add_done_callback(_mutating_background_tasks.discard)
    return task

def _get_substrate_client():
    """Lazy-init the substrate client for remote mode."""
    global _substrate_client
    if _substrate_client is None:
        from dsf_ai_service.substrate_client import SubstrateClient
        _substrate_client = SubstrateClient()
    return _substrate_client

def _get_converse_client():
    """Dedicated client for converse SSE path — separate connection avoids lock contention."""
    global _converse_client
    if _converse_client is None:
        from dsf_ai_service.substrate_client import SubstrateClient
        _converse_client = SubstrateClient()
    return _converse_client

def _is_remote():
    return SUBSTRATE_MODE == "remote"

app = FastAPI(
    title="DSF-AI Structural Analysis Service",
    version="1.0.0",
    description="Universal structural analysis for any measurement-vs-stimulus data.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class _DeploymentLifecycle:
    """Single process admission and sealed-owner state machine."""

    STATES = ("RUNNING", "QUIESCING", "SEALED", "RETIRED")

    def __init__(self):
        import threading
        self._condition = threading.Condition()
        self._state = "RUNNING"
        self._nonce = None
        self._active_mutations = 0
        self._certificate = None
        self._failure = None

    def snapshot(self):
        with self._condition:
            return {
                "state": self._state,
                "nonce": self._nonce,
                "active_mutations": self._active_mutations,
                "certificate": self._certificate,
                "failure": self._failure,
            }

    def admit_mutation(self):
        with self._condition:
            if self._state != "RUNNING":
                return False
            self._active_mutations += 1
            return True

    def finish_mutation(self):
        with self._condition:
            if self._active_mutations <= 0:
                raise RuntimeError("deployment mutation counter underflow")
            self._active_mutations -= 1
            self._condition.notify_all()

    def begin_quiescence(self, nonce):
        with self._condition:
            if self._state == "RUNNING":
                self._state = "QUIESCING"
                self._nonce = nonce
                self._failure = None
                return
            if self._state in {"QUIESCING", "SEALED"} and self._nonce == nonce:
                return
            raise RuntimeError(
                f"lifecycle is {self._state} for a different deployment")

    def wait_for_mutations(self, timeout):
        import time
        deadline = time.monotonic() + float(timeout)
        with self._condition:
            while self._active_mutations:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise RuntimeError(
                        f"{self._active_mutations} mutating request(s) did not finish")
                self._condition.wait(timeout=remaining)

    def seal(self, certificate):
        with self._condition:
            if self._state != "QUIESCING":
                raise RuntimeError("only a quiescing owner can seal")
            self._certificate = certificate
            self._state = "SEALED"
            self._condition.notify_all()

    def fail_quiescence(self, error, *, resumed):
        with self._condition:
            self._failure = str(error)
            if resumed:
                self._state = "RUNNING"
                self._nonce = None
            self._condition.notify_all()

    def retire(self):
        with self._condition:
            if self._state != "SEALED":
                raise RuntimeError("only a sealed owner can retire")
            self._state = "RETIRED"
            self._condition.notify_all()


_deployment_lifecycle = _DeploymentLifecycle()
import contextvars as _contextvars
_lifecycle_mutation_depth = _contextvars.ContextVar(
    "guala_lifecycle_mutation_depth", default=0)
_app_lifecycle_tasks = set()


def _start_app_lifecycle_task(coroutine, *, name):
    """Retain a process-owned asyncio loop so quiescence can stop it."""
    import asyncio
    task = asyncio.create_task(coroutine, name=name)
    _app_lifecycle_tasks.add(task)
    task.add_done_callback(_app_lifecycle_tasks.discard)
    return task


async def _run_lifecycle_executor(function, *args):
    """Run one writer in the executor while retaining lifecycle ownership.

    Cancellation waits for the underlying thread to finish; asyncio cannot
    otherwise stop a running executor function, and releasing the mutation
    count early would create a false seal.
    """
    inherited = _lifecycle_mutation_depth.get() > 0
    if not inherited and not _deployment_lifecycle.admit_mutation():
        raise RuntimeError("deployment quiescence is active")
    import asyncio
    loop = asyncio.get_running_loop()
    # Executor workers are reused.  Running directly on the worker lets a
    # ContextVar written by one mutation (notably WindowManager's bound
    # BindingWindow) survive into a later, unrelated mutation on that thread.
    # Enter one caller-derived context per job so caller-local authority is
    # preserved while prior worker state can never become the next caller's.
    caller_context = _contextvars.copy_context()
    future = loop.run_in_executor(
        None, caller_context.run, function, *args)
    try:
        try:
            return await asyncio.shield(future)
        except asyncio.CancelledError:
            await asyncio.shield(future)
            raise
    finally:
        if not inherited:
            _deployment_lifecycle.finish_mutation()


async def _stop_app_lifecycle_tasks(timeout):
    """Cancel and join every retained app-owned background coroutine."""
    import asyncio
    current = asyncio.current_task()
    tasks = [task for task in tuple(_app_lifecycle_tasks)
             if task is not current and not task.done()]
    for task in tasks:
        task.cancel()
    if tasks:
        done, pending = await asyncio.wait(tasks, timeout=float(timeout))
        if pending:
            raise RuntimeError(
                "app background tasks did not stop: "
                + ", ".join(sorted(task.get_name() for task in pending)))
        for task in done:
            if task.cancelled():
                continue
            error = task.exception()
            if error is not None:
                raise RuntimeError(
                    f"app background task {task.get_name()} failed: {error}")
    return {"app_tasks_stopped": len(tasks)}


_CONTROL_PATHS = frozenset({
    "/internal/deployment/quiesce",
    "/internal/deployment/readiness",
    "/ready",
    "/ready/guala",
    # GL-RPT-RAM-FIXES-DEPLOYED-AND-SEAL-DEFECTS defect 1 (2026-07-15): this
    # alias serves the SAME quiesce handler.  Counting it as a mutation made
    # the seal wait on a counter that included the seal request itself, so a
    # scripted seal could never drain below 1 — every deploy 503'd at 120 s.
    # A control request is not a data mutation on either route.
    "/sleep_for_deploy",
})
@app.middleware("http")
async def deployment_mutation_admission(request, call_next):
    mutating = request.method.upper() not in {"GET", "HEAD", "OPTIONS"}
    if not mutating or request.url.path in _CONTROL_PATHS:
        return await call_next(request)
    if not _deployment_lifecycle.admit_mutation():
        return JSONResponse(
            status_code=503,
            content={
                "ok": False,
                "error": "deployment_quiescence",
                "lifecycle": _deployment_lifecycle.snapshot(),
            },
            headers={"Retry-After": "30"},
        )
    depth_token = _lifecycle_mutation_depth.set(
        _lifecycle_mutation_depth.get() + 1)
    try:
        return await call_next(request)
    finally:
        _lifecycle_mutation_depth.reset(depth_token)
        _deployment_lifecycle.finish_mutation()

STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static')

# GL-BRIEF-REMOVE-30S-CAP: API key enforcement for bridge auth.
# When GUALALOOM_API_KEY is set, admin and converse endpoints require
# X-API-Key header. If not set, all endpoints remain open (dev mode).
_GUALALOOM_API_KEY = os.environ.get("GUALALOOM_API_KEY", "")


def _require_api_key(request: Request):
    """Check X-API-Key header against env-var secret. No-op if key not configured."""
    xff = request.headers.get("x-forwarded-for", request.client.host if request.client else "-")
    print(f"[admin-access] path={request.url.path} xff={xff}")
    if not _GUALALOOM_API_KEY:
        return  # no key configured, skip auth
    provided = request.headers.get("X-API-Key", "")
    if provided != _GUALALOOM_API_KEY:
        raise HTTPException(status_code=401, detail="unauthorized")


from fastapi import Depends

def _api_key_dep(request: Request):
    """FastAPI dependency for API key enforcement."""
    _require_api_key(request)


@app.get("/")
async def index():
    return FileResponse(os.path.join(STATIC_DIR, 'index.html'))


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


# ════════════════════════════════════════════════════════════════
# Endpoint 1: CSV structural analysis
# ════════════════════════════════════════════════════════════════

@app.post("/api/v1/analyze")
async def analyze_csv(
    file: UploadFile = File(...),
    context: Optional[str] = Form(None),
):
    """
    Upload a two-column CSV (stimulus, measurement).
    Returns structural analysis with transitions, precursors,
    regime map, and LLM narrative.
    """
    if not file.filename.endswith('.csv'):
        raise HTTPException(400, "File must be a .csv")

    content = await file.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(400, "File too large (max 10 MB)")

    try:
        text = content.decode('utf-8')
    except UnicodeDecodeError:
        raise HTTPException(400, "File must be UTF-8 encoded")

    # Parse CSV
    reader = csv.reader(io.StringIO(text))
    pairs = []
    for row in reader:
        if not row or len(row) < 2:
            continue
        try:
            stimulus = float(row[0].strip())
            measurement = float(row[1].strip())
            pairs.append((stimulus, measurement))
        except ValueError:
            continue  # skip header or non-numeric rows

    if len(pairs) < 5:
        raise HTTPException(400, "Need at least 5 data points")
    if len(pairs) > 500000:
        raise HTTPException(400, "Too many data points (max 500,000)")

    t0 = time.time()

    # Run kernel (TRADE SECRET — internals stay here)
    try:
        report = run_analysis(pairs)
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(500, f"Kernel error: {str(e)}")

    # Generate LLM narrative
    try:
        narrative = narrate_results(report, context=context)
        report['narrative'] = narrative
    except Exception:
        report['narrative'] = None  # LLM failure is non-fatal

    report['compute_time_s'] = round(time.time() - t0, 3)

    return report


# ════════════════════════════════════════════════════════════════
# Endpoint 2: Single cluster prediction
# ════════════════════════════════════════════════════════════════

class ClusterRequest(BaseModel):
    element: str
    N_atoms: int = 13
    temperature_K: float = 300
    lattice: str = "cubic"


@app.post("/api/v1/cluster")
async def cluster_predict(req: ClusterRequest):
    """Predict properties for a single nanoparticle cluster."""
    try:
        result = predict_cluster(
            req.element, req.N_atoms, req.temperature_K, req.lattice
        )
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(500, str(e))
    return result


# ════════════════════════════════════════════════════════════════
# Endpoint 3: Batch screening with constraints
# ════════════════════════════════════════════════════════════════

class ScreenConstraints(BaseModel):
    moment_min_uB: Optional[float] = None
    seebeck_min_uV_K: Optional[float] = None
    EA_min_eV: Optional[float] = None
    gap_min_eV: Optional[float] = None


class ScreenRequest(BaseModel):
    elements: Optional[List[str]] = None
    N_atoms: Optional[List[int]] = None
    constraints: Optional[ScreenConstraints] = None


@app.post("/api/v1/cluster/screen")
async def cluster_screen(req: ScreenRequest):
    """Batch screen clusters against property constraints."""
    t0 = time.time()
    try:
        result = screen_clusters(
            elements=req.elements,
            n_atoms_list=req.N_atoms,
            constraints=req.constraints.model_dump() if req.constraints else None,
        )
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(500, str(e))
    result['compute_time_ms'] = round((time.time() - t0) * 1000, 1)
    return result


# ════════════════════════════════════════════════════════════════
# Endpoint 4: Thermocouple pair finder
# ════════════════════════════════════════════════════════════════

class ThermocoupleRequest(BaseModel):
    N_atoms: int = 13
    min_delta_S: float = 50


@app.post("/api/v1/cluster/thermocouple")
async def thermocouple(req: ThermocoupleRequest):
    """Find optimal thermocouple pairs from cluster Seebeck predictions."""
    try:
        result = find_thermocouple_pairs(req.N_atoms, req.min_delta_S)
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(500, str(e))
    return result


# ════════════════════════════════════════════════════════════════
# Endpoint 5: Hardware weight derivation (hidden, auth required)
# ════════════════════════════════════════════════════════════════

class HWDeriveRequest(BaseModel):
    calibration_table: Dict
    sensor_names: List[str]
    sensor_roles: Dict[str, str]
    sensor_label: str = "unknown sensor"
    camera_mode: bool = False
    background: Optional[Dict] = None


@app.post("/api/v1/hw/derive")
async def hw_derive(req: HWDeriveRequest):
    """
    Derive coupling weights + BSIL thresholds from sensor calibration data.
    Hidden endpoint — not linked from any public page.
    Supports IR distance sensors (axial/lateral roles) and
    camera vision features (structural role).
    """
    t0 = time.time()
    try:
        from tools.derive_sppu_weights import (
            derive_weights, format_verilog, format_json,
            format_bsil_thresholds, build_field_series, run_kernel,
            dsf_to_coupling_profile, derive_bsil_thresholds,
        )
        import numpy as np

        # Convert string keys back to proper types
        cal_table = {}
        for k, v in req.calibration_table.items():
            if k == 'inf' or k == 'Inf':
                cal_table['inf'] = tuple(
                    None if x is None else float(x) for x in v
                )
            else:
                cal_table[float(k)] = tuple(
                    None if x is None else float(x) for x in v
                )

        # Check if any role is "structural" (camera mode)
        has_structural = any(r == 'structural' for r in req.sensor_roles.values())

        if not has_structural:
            # Standard IR mode — use existing derive_weights
            weights, bsil_thresholds, metadata = derive_weights(
                calibration_table=cal_table,
                sensor_names=req.sensor_names,
                sensor_roles=req.sensor_roles,
                sensor_label=req.sensor_label,
            )
            verilog = format_verilog(weights, metadata)
            verilog += "\n\n" + format_bsil_thresholds(bsil_thresholds)
            json_str = format_json(weights, metadata)
        else:
            # Camera / structural mode
            # Run each feature through the kernel independently
            from tools.derive_sppu_weights import ingest_calibration_table

            sensor_data = ingest_calibration_table(cal_table)
            background = getattr(req, 'background', None)
            if hasattr(req, '__dict__'):
                background = req.__dict__.get('background', None)

            profiles = {}
            all_boundaries = {}
            bsil_thresholds = {}
            baselines = {}

            for i, name in enumerate(req.sensor_names):
                key = f'sensor_{i}'
                if key not in sensor_data or not sensor_data[key]:
                    continue

                # Get baseline from 'inf' entry or background
                for stim, readings in cal_table.items():
                    if stim == 'inf':
                        if readings[i] is not None:
                            baselines[name] = float(readings[i])
                        break

                series = build_field_series(sensor_data[key], name)
                kernel_out = run_kernel(series)
                profile = dsf_to_coupling_profile(kernel_out['dsf'])
                profiles[name] = profile
                all_boundaries[name] = kernel_out['boundaries']

                baseline = baselines.get(name, 0)
                thresholds = derive_bsil_thresholds(
                    kernel_out['boundaries'], baseline
                )
                bsil_thresholds[name] = thresholds

            # Build camera-specific Verilog output
            verilog_lines = []
            verilog_lines.append("// ---- Camera Vision Coupling Weights ----")
            verilog_lines.append(f"// Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}")
            verilog_lines.append(f"// Sensor: {req.sensor_label}")
            verilog_lines.append(f"// Features: {', '.join(req.sensor_names)}")
            verilog_lines.append(f"// Role: structural (vision)")
            verilog_lines.append("")

            for name, profile in profiles.items():
                cs = profile['coupling_strength']
                mw = profile['momentum_weight']
                unc = profile['uncertainty']
                bm = profile['breathing_magnitude']
                rr = profile['reversal_rate']

                # Base weight from DSF profile
                raw = cs * (1.0 + bm) * (1.0 - unc * 0.5) * (1.0 - rr * 0.3)
                base_w = int(np.clip(raw * 40, 5, 40))

                # Confidence coupling (primary for structural features)
                conf = 1.0 - unc
                stability = 1.0 - min(bm, 1.0) * 0.5
                conf_w = int(np.clip(conf * stability * 25, 5, 30))

                # Steer coupling (derived — may be zero if symmetric)
                # Use D_k std as proxy for directional asymmetry
                steer_w = int(np.clip(cs * 10, 0, 15))

                # Speed coupling (approach when recognized)
                speed_w = int(np.clip(cs * mw * 20, 0, 20))

                baseline = baselines.get(name, 0)
                # Dead zone: uncertainty * range
                dz = int(np.clip(unc * 50, 5, 100))

                verilog_lines.append(f"// {name}:")
                verilog_lines.append(f"//   coupling_strength = {cs:.4f}")
                verilog_lines.append(f"//   momentum_weight   = {mw:.4f}")
                verilog_lines.append(f"//   uncertainty        = {unc:.4f}")
                verilog_lines.append(f"//   breathing          = {bm:.4f}")
                verilog_lines.append(f"//   reversal_rate      = {rr:.4f}")
                verilog_lines.append(f"parameter [7:0] BASELINE_{name.upper()} = 8'd{int(baseline)};")
                verilog_lines.append(f"parameter [7:0] DEADZONE_{name.upper()} = 8'd{dz};")
                verilog_lines.append(f"parameter [7:0] W_CONFIDENCE_{name.upper()} = 8'd{conf_w};")
                verilog_lines.append(f"parameter signed [7:0] W_STEER_{name.upper()} = 8'sd{steer_w};")
                verilog_lines.append(f"parameter [7:0] W_SPEED_{name.upper()} = 8'd{speed_w};")
                verilog_lines.append("")

            verilog = "\n".join(verilog_lines)
            verilog += "\n\n" + format_bsil_thresholds(bsil_thresholds)

            # JSON output
            import json as json_mod
            json_out = {
                'sensor_label': req.sensor_label,
                'mode': 'camera_structural',
                'features': req.sensor_names,
                'baselines': baselines,
                'profiles': profiles,
                'bsil_thresholds': bsil_thresholds,
            }
            json_str = json_mod.dumps(json_out, indent=2, default=str)

        # Build profiles summary
        profiles_lines = []
        dsf_profiles = profiles if has_structural else metadata.get('dsf_profiles', {})
        for name, profile in dsf_profiles.items():
            profiles_lines.append(f"--- {name} ---")
            for k, v in profile.items():
                if isinstance(v, float):
                    profiles_lines.append(f"  {k}: {v:.4f}")
                else:
                    profiles_lines.append(f"  {k}: {v}")
            profiles_lines.append("")
        profiles_str = "\n".join(profiles_lines)

        return {
            'status': 'ok',
            'verilog': verilog,
            'json': json_str,
            'profiles': profiles_str,
            'compute_time_s': round(time.time() - t0, 3),
        }
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(500, str(e))


# ════════════════════════════════════════════════════════════════
# Endpoint 6: CFF Discovery Algorithm
# ════════════════════════════════════════════════════════════════

class DiscoveryRequest(BaseModel):
    target_property: str = "RTSC"
    max_pressure_GPa: float = 0
    must_be_2D: bool = False
    must_be_gateable: bool = False
    exclude_families: Optional[List[str]] = None


@app.post("/api/v1/discover")
async def discover(req: DiscoveryRequest):
    """
    CFF Discovery Algorithm: given a target property,
    output the forced architectural class and ranked candidates.
    """
    t0 = time.time()
    try:
        result = run_discovery(
            target_property=req.target_property,
            max_pressure_GPa=req.max_pressure_GPa,
            must_be_2D=req.must_be_2D,
            must_be_gateable=req.must_be_gateable,
            exclude_families=req.exclude_families,
        )
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(500, str(e))
    result['compute_time_ms'] = round((time.time() - t0) * 1000, 1)
    return result


class VerifyRequest(BaseModel):
    composition: str
    substrate: str
    target_property: str = "RTSC"


@app.post("/api/v1/discover/verify")
async def discover_verify(req: VerifyRequest):
    """
    Verify mode: check which CFF filters a specific
    candidate passes or fails.
    """
    try:
        result = verify_candidate(
            composition=req.composition,
            substrate=req.substrate,
            target_property=req.target_property,
        )
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(500, str(e))
    return result


# ════════════════════════════════════════════════════════════════
# GualaLoom — substrate below, dialog above
# GUALALOOM-INTEGRATE-WC-2026-06-05
# ════════════════════════════════════════════════════════════════

import numpy as np
import json

# ════════════════════════════════════════════════════════════════
# GualaLoom v5 — Recall + Question Bucket + Honest Fallback
# GUALALOOM-V5-WC-2026-06-05
# ════════════════════════════════════════════════════════════════

from dsf_ai_service.v4.gualaloom_v5_engine import (
    Guala, CORPUS, SensoryItem, PictureItem, VideoItem,
)
from fastapi.responses import StreamingResponse

_guala = None
_persist_every = 50   # save every N exchanges
_exchange_count = 0
STATE_DIR = os.environ.get("STATE_DIR", "state")
GENERATION_STORE_ROOT = os.environ.get(
    "GUALA_GENERATION_STORE_ROOT",
    os.path.join(
        os.path.dirname(os.path.abspath(STATE_DIR)),
        os.path.basename(os.path.abspath(STATE_DIR)) + "-sealed",
    ),
)
LIVE_RECOVERY_STORE_ROOT = os.environ.get(
    "GUALA_LIVE_RECOVERY_STORE_ROOT",
    os.path.join(
        os.path.dirname(GENERATION_STORE_ROOT),
        os.path.basename(GENERATION_STORE_ROOT) + "-live-recovery",
    ),
)
def _safe_ledger_status(module_name):
    """Best-effort status from a schooling ledger; never raises into /status."""
    try:
        import importlib
        mod = importlib.import_module(
            f"dsf_ai_service.substrate.{module_name}")
        return mod.get_ledger(STATE_DIR).status()
    except Exception:
        return {}


OWNER_LOCK_PATH = os.environ.get(
    "GUALA_OWNER_LOCK_PATH",
    os.path.join(os.path.dirname(GENERATION_STORE_ROOT), ".guala-owner.lock"),
)
_REQUIRE_SEALED_STATE = os.environ.get(
    "GUALA_REQUIRE_SEALED_STATE", "0").strip() == "1"
_generation_owner_lock = None
_loaded_generation = None
_deployment_baseline_generation = None
_live_recovery_store = None
# GL-CMD-LANGUAGE-SEED-PHASE2-GENERATOR-EVE-20260707-v1: rich/programmatic
# seed load progress, polled by /health. None until a seed load is attempted.
_seed_load_progress = None

# v7: Seed corpora — lines for autonomous reading
SEED_CORPORA = {
    "see_spot_run": {
        "title": "See Spot Run",
        "lines": [
            "see spot", "see spot run", "run spot run",
            "see jane", "see jane run", "run jane run",
            "see spot and jane", "spot and jane run",
            "see the dog run", "the dog is spot",
            "spot is a good dog", "jane has a dog",
            "spot can run fast", "run run run",
        ],
    },
    "goodnight_moon": {
        "title": "Goodnight Moon",
        "lines": [
            "in the great green room", "there was a telephone",
            "and a red balloon", "and a picture of the cow jumping over the moon",
            "goodnight room", "goodnight moon", "goodnight cow jumping over the moon",
            "goodnight light", "goodnight red balloon",
            "goodnight stars", "goodnight air", "goodnight noises everywhere",
        ],
    },
    "green_eggs": {
        "title": "Green Eggs and Ham",
        "lines": [
            "i am sam", "sam i am", "do you like green eggs and ham",
            "i do not like them sam i am", "i do not like green eggs and ham",
            "would you like them here or there",
            "i would not like them here or there",
            "i would not like them anywhere",
            "not in a house", "not with a mouse",
            "not in a box", "not with a fox",
            "i do not like green eggs and ham", "i do not like them sam i am",
            "you do not like them so you say", "try them and you may",
            "i like green eggs and ham", "i do i like them sam i am",
        ],
    },
    "mother_goose": {
        "title": "Mother Goose Rhymes",
        "lines": [
            "twinkle twinkle little star", "how i wonder what you are",
            "up above the world so high", "like a diamond in the sky",
            "mary had a little lamb", "its fleece was white as snow",
            "and everywhere that mary went", "the lamb was sure to go",
            "humpty dumpty sat on a wall", "humpty dumpty had a great fall",
            "jack and jill went up the hill", "to fetch a pail of water",
            "baa baa black sheep", "have you any wool",
            "yes sir yes sir", "three bags full",
            "one two three four five", "once i caught a fish alive",
            "six seven eight nine ten", "then i let it go again",
            "hey diddle diddle", "the cat and the fiddle",
            "the cow jumped over the moon",
            "the little dog laughed to see such sport",
            "and the dish ran away with the spoon",
        ],
    },
}

# v7 corpora expansion — GUALALOOM-V7-CORPORA-EXPANSION-WC-2026-06-07
# Original sentences capturing vocabulary and structure patterns
# from age-appropriate reading material.

SEED_CORPORA["hungry_caterpillar"] = {
    "title": "The Hungry Caterpillar",
    "lines": [
        "on monday the caterpillar ate one apple",
        "on tuesday the caterpillar ate two pears",
        "on wednesday the caterpillar ate three plums",
        "on thursday the caterpillar ate four strawberries",
        "on friday the caterpillar ate five oranges",
        "the caterpillar was very hungry",
        "the caterpillar ate and ate and ate",
        "one piece of cake", "one ice cream cone",
        "one pickle", "one slice of cheese",
        "one slice of salami", "one lollipop",
        "one piece of pie", "one sausage",
        "one cupcake", "one slice of watermelon",
        "the caterpillar had a stomachache",
        "the caterpillar ate one nice green leaf",
        "the caterpillar felt much better",
        "the caterpillar was not hungry anymore",
        "the caterpillar was a big fat caterpillar",
        "the caterpillar built a small house around himself",
        "the caterpillar stayed inside for more than two weeks",
        "the caterpillar pushed his way out",
        "the caterpillar was a beautiful butterfly",
    ],
}

SEED_CORPORA["brown_bear"] = {
    "title": "Brown Bear",
    "lines": [
        "brown bear brown bear what do you see",
        "i see a red bird looking at me",
        "red bird red bird what do you see",
        "i see a yellow duck looking at me",
        "yellow duck yellow duck what do you see",
        "i see a blue horse looking at me",
        "blue horse blue horse what do you see",
        "i see a green frog looking at me",
        "green frog green frog what do you see",
        "i see a purple cat looking at me",
        "purple cat purple cat what do you see",
        "i see a white dog looking at me",
        "white dog white dog what do you see",
        "i see a black sheep looking at me",
        "black sheep black sheep what do you see",
        "i see a goldfish looking at me",
        "goldfish goldfish what do you see",
        "i see children looking at me",
        "children children what do you see",
        "we see a brown bear and a red bird",
        "we see a yellow duck and a blue horse",
        "we see a green frog and a purple cat",
        "we see a white dog and a black sheep",
        "we see a goldfish and children",
        "that is what we see",
    ],
}

SEED_CORPORA["chicka_boom"] = {
    "title": "Letter Tree",
    "lines": [
        "a told b and b told c",
        "i will meet you at the top of the tree",
        "d e f g h i j k",
        "l m n o p q r s t",
        "u v w x y and z",
        "the whole alphabet up the tree",
        "but the tree could not hold them all",
        "and they all came tumbling down",
        "a skinned knee", "b a stubbed toe",
        "c said ouch", "d said oh no",
        "the sun came up and so did they",
        "back up the tree to play all day",
        "a b c d e f g",
        "h i j k l m n o p",
        "q r s t u v w",
        "x y z the tree is free",
    ],
}

SEED_CORPORA["wild_things"] = {
    "title": "Wild Things",
    "lines": [
        "the night max wore his wolf suit",
        "and made mischief of one kind and another",
        "his mother called him wild thing",
        "max said i will eat you up",
        "so he was sent to bed without eating anything",
        "that very night in his room a forest grew",
        "and grew and grew until the ceiling hung with vines",
        "and the walls became the world all around",
        "and an ocean tumbled by with a private boat for max",
        "and he sailed off through night and day",
        "and in and out of weeks",
        "and almost over a year",
        "to where the wild things are",
        "and when he came to the place where the wild things are",
        "they roared their terrible roars",
        "and gnashed their terrible teeth",
        "and rolled their terrible eyes",
        "and showed their terrible claws",
        "max said be still",
        "and tamed them with the magic trick",
        "of staring into their yellow eyes without blinking",
        "and they were frightened and called him the most wild thing of all",
        "and made him king of all wild things",
        "let the wild rumpus start",
        "now stop max said",
        "max the king of all wild things was lonely",
        "and wanted to be where someone loved him best of all",
        "max sailed back over a year",
        "and in and out of weeks and through a day",
        "and into the night of his very own room",
        "where he found his supper waiting for him",
        "and it was still hot",
    ],
}

SEED_CORPORA["corduroy"] = {
    "title": "Corduroy",
    "lines": [
        "corduroy is a bear who lives in a big store",
        "he sits on a shelf with many other animals",
        "a girl named lisa sees corduroy",
        "she says look there is the bear i always wanted",
        "her mother says not today dear",
        "he does not look new",
        "he has lost a button",
        "that night corduroy climbs down from the shelf",
        "i think i lost a button he says",
        "he searches the store all night",
        "he looks on the furniture",
        "he looks on the escalator",
        "he pulls a button on a mattress",
        "the mattress wobbles and corduroy falls",
        "a guard finds him and puts him back on the shelf",
        "the next morning lisa comes back",
        "she has saved her money",
        "she buys corduroy and takes him home",
        "she sews a button on his overalls",
        "i like you the way you are says lisa",
        "but you will be more comfortable with your button",
        "you must be a friend says corduroy",
        "i have always wanted a friend",
        "me too says lisa and she gives him a big hug",
    ],
}

SEED_CORPORA["frog_and_toad"] = {
    "title": "Frog and Toad",
    "lines": [
        "frog ran up the path to toads house",
        "he knocked on the front door",
        "toad toad said frog wake up it is spring",
        "i am not here said toad",
        "but toad said frog the sun is shining",
        "the snow is melting",
        "toad said go away i am not here",
        "frog walked into the house",
        "it was dark and all the shutters were closed",
        "toad where are you said frog",
        "toad was in bed with the blanket over his head",
        "toad i have a story to tell you said frog",
        "tell it tomorrow said toad",
        "frog sat close to toad",
        "i am glad you woke up said frog",
        "me too said toad",
        "shall we go for a walk asked frog",
        "yes let us go for a walk said toad",
        "they walked along the river together",
        "they found a fine place and sat down",
        "this is a good day said toad",
        "yes said frog it is the best day",
        "frog and toad were happy",
        "they sat there feeling the warm sun",
    ],
}

SEED_CORPORA["amelia_bedelia"] = {
    "title": "Amelia Bedelia",
    "lines": [
        "amelia bedelia went to work for the first time",
        "she found a list of things to do",
        "the list said change the towels",
        "amelia bedelia got scissors and cut the towels",
        "now they are changed she said",
        "the list said dust the furniture",
        "she put dusting powder on every piece",
        "the list said draw the drapes",
        "amelia bedelia sat down and drew a picture of the drapes",
        "the list said put the lights out",
        "she took every light outside and put them on the clothesline",
        "the list said dress the chicken",
        "amelia bedelia found some cloth and dressed the chicken in it",
        "the list said measure two cups of rice",
        "she took a ruler and measured each cup",
        "amelia bedelia said i do exactly what they tell me to do",
        "she tried very hard to do everything right",
        "she made a beautiful pie",
        "everyone loved the pie so much",
        "they forgave all the mix ups",
        "you are the best pie maker in the world they said",
        "amelia bedelia smiled",
    ],
}

SEED_CORPORA["counting_book"] = {
    "title": "Counting Book",
    "lines": [
        "one sun in the sky",
        "two eyes on my face",
        "three kittens playing",
        "four wheels on a car",
        "five fingers on a hand",
        "six legs on a bug and two more on another bug",
        "seven days in a week",
        "eight arms on an octopus",
        "nine birds sitting on a fence",
        "ten toes on my feet",
        "one two three four five",
        "six seven eight nine ten",
        "i can count to ten",
        "ten nine eight seven six",
        "five four three two one",
        "i can count back down",
        "one is the loneliest number",
        "two is company",
        "three is a crowd",
        "four is enough for a game",
        "five makes a team",
    ],
}

SEED_CORPORA["colors_book"] = {
    "title": "Colors Book",
    "lines": [
        "red is the color of an apple",
        "red is the color of a fire truck",
        "orange is the color of an orange",
        "orange is the color of a sunset",
        "yellow is the color of the sun",
        "yellow is the color of a banana",
        "green is the color of the grass",
        "green is the color of the leaves",
        "blue is the color of the sky",
        "blue is the color of the ocean",
        "purple is the color of grapes",
        "purple is the color of a plum",
        "pink is the color of a flower",
        "brown is the color of the earth",
        "black is the color of the night",
        "white is the color of the snow",
        "the rainbow has many colors",
        "red orange yellow green blue purple",
        "i see colors everywhere",
        "the world is full of colors",
    ],
}

SEED_CORPORA["feelings_book"] = {
    "title": "Feelings Book",
    "lines": [
        "sometimes i feel happy",
        "when i feel happy i smile and laugh",
        "sometimes i feel sad",
        "when i feel sad i want to be held",
        "sometimes i feel angry",
        "when i feel angry my face gets hot",
        "sometimes i feel scared",
        "when i feel scared i want to hide",
        "sometimes i feel brave",
        "when i feel brave i try new things",
        "sometimes i feel tired",
        "when i feel tired i close my eyes",
        "sometimes i feel excited",
        "when i feel excited i jump up and down",
        "sometimes i feel lonely",
        "when i feel lonely i look for a friend",
        "sometimes i feel proud",
        "when i feel proud my heart feels big",
        "sometimes i feel curious",
        "when i feel curious i ask questions",
        "sometimes i feel calm",
        "when i feel calm i breathe slowly",
        "all of my feelings are okay",
        "feelings come and feelings go",
        "i am still me no matter how i feel",
    ],
}

# v7: Legacy corpus as fallback reading material
SEED_CORPORA["grammar_basics"] = {
    "title": "Grammar Basics",
    "lines": [
        "a sentence has a subject and a verb",
        "the subject tells who or what",
        "the verb tells what happens",
        "the cat sits is a sentence",
        "cat is the subject", "sits is the verb",
        "some sentences have an object",
        "the dog chases the ball",
        "dog is the subject", "chases is the verb", "ball is the object",
        "a noun is a person place or thing",
        "a verb is an action or a state",
        "an adjective describes a noun",
        "the big red ball", "big and red are adjectives",
        "an adverb describes a verb",
        "the cat runs quickly", "quickly is an adverb",
        "a pronoun takes the place of a noun",
        "he she it they we you i",
        "he runs", "she sings", "they play", "we learn",
        "a preposition shows position or direction",
        "on the table", "under the bed", "in the box",
        "beside the tree", "between the houses",
        "a conjunction joins words or sentences",
        "and but or so because",
        "the cat and the dog", "big but gentle",
        "i run or i walk", "i eat because i am hungry",
        "an article comes before a noun",
        "a an the", "a cat", "an apple", "the sun",
        "the plural of cat is cats",
        "the plural of box is boxes",
        "the plural of baby is babies",
        "the plural of child is children",
        "the plural of mouse is mice",
        "the past tense of run is ran",
        "the past tense of eat is ate",
        "the past tense of go is went",
        "the past tense of see is saw",
        "the past tense of give is gave",
        "a question ends with a question mark",
        "who what where when why how",
        "who is there", "what is that", "where is the cat",
        "when is dinner", "why is the sky blue", "how does it work",
    ],
}

SEED_CORPORA["simple_dictionary"] = {
    "title": "Simple Dictionary",
    "lines": [
        "apple is a fruit that is red or green",
        "ball is a round thing you throw or catch",
        "cat is a small animal with fur and whiskers",
        "dog is an animal that barks and wags its tail",
        "egg is something a bird lays",
        "fish is an animal that lives in water and has fins",
        "grass is the green plant that covers the ground",
        "house is a building where people live",
        "ice is frozen water", "juice is a drink made from fruit",
        "key is a small metal thing that opens a lock",
        "leaf is the flat green part of a plant",
        "moon is the round bright thing in the night sky",
        "nose is the part of your face you smell with",
        "ocean is a very large body of salt water",
        "pencil is a tool you write with",
        "queen is a woman who rules a country",
        "rain is water that falls from clouds",
        "sun is the star that gives us light and warmth",
        "tree is a tall plant with a trunk and branches",
        "umbrella keeps you dry in the rain",
        "voice is the sound you make when you speak",
        "water is a clear liquid you drink",
        "yard is the ground around a house",
        "zero is the number that means nothing",
        "friend is someone you like and who likes you",
        "family is the people who love you and live with you",
        "morning is the beginning of the day",
        "night is when the sky is dark and you sleep",
        "happy means feeling good inside",
        "sad means feeling like you want to cry",
        "kind means being nice and helpful to others",
        "brave means doing something even when you are scared",
        "gentle means being soft and careful",
        "strong means having power to lift or push",
    ],
}

SEED_CORPORA["opposites"] = {
    "title": "Opposites",
    "lines": [
        "big is the opposite of small",
        "hot is the opposite of cold",
        "fast is the opposite of slow",
        "up is the opposite of down",
        "in is the opposite of out",
        "open is the opposite of closed",
        "light is the opposite of dark",
        "hard is the opposite of soft",
        "wet is the opposite of dry",
        "happy is the opposite of sad",
        "loud is the opposite of quiet",
        "full is the opposite of empty",
        "new is the opposite of old",
        "near is the opposite of far",
        "long is the opposite of short",
        "thick is the opposite of thin",
        "heavy is the opposite of light",
        "clean is the opposite of dirty",
        "smooth is the opposite of rough",
        "sweet is the opposite of bitter",
        "the big dog and the small cat",
        "the hot sun and the cold snow",
        "the fast rabbit and the slow turtle",
    ],
}

SEED_CORPORA["simple_sentences"] = {
    "title": "Simple Sentences",
    "lines": [
        "the cat sat on the mat",
        "the dog ran in the yard",
        "the bird flew over the tree",
        "the fish swam in the pond",
        "the boy kicked the ball",
        "the girl drew a picture",
        "the baby laughed and clapped",
        "the man walked to the store",
        "the woman read a book",
        "the children played in the park",
        "the sun set behind the mountains",
        "the rain fell on the roof",
        "the wind blew through the trees",
        "the snow covered the ground",
        "the flowers grew in the garden",
        "the frog jumped into the water",
        "the bear slept in the cave",
        "the owl hooted in the night",
        "the spider spun a web",
        "the butterfly landed on a flower",
        "i ate breakfast this morning",
        "she went to school today",
        "he played with his friends",
        "they sang a song together",
        "we built a house with blocks",
    ],
}

# v7: Legacy corpus as fallback reading material
SEED_CORPORA["legacy_seed"] = {"title": "Seed Corpus", "lines": CORPUS}


def _prepare_generation_boot():
    """Acquire the sole EFS owner and activate fully verified CURRENT state."""
    global _generation_owner_lock, _loaded_generation
    global _deployment_baseline_generation, _live_recovery_store
    if not _REQUIRE_SEALED_STATE:
        return None
    if _generation_owner_lock is not None:
        return _loaded_generation
    from dsf_ai_service.substrate.deployment_generation import (
        ProcessLifetimeEFSOwnerLock,
        materialize_current,
    )
    from dsf_ai_service.substrate.live_recovery_generation import (
        LiveRecoveryGenerationStore,
    )
    owner = ProcessLifetimeEFSOwnerLock(OWNER_LOCK_PATH).acquire()
    try:
        baseline = materialize_current(
            store_root=GENERATION_STORE_ROOT,
            active_directory=STATE_DIR,
            retained_generations=3,
        )
        live_store = LiveRecoveryGenerationStore(
            LIVE_RECOVERY_STORE_ROOT,
            baseline=baseline,
            hot_files=Guala.HOT_SAVE_MANIFEST_FILES,
            hmac_key=_deploy_hmac_key(),
        )
        live = live_store.apply_current(STATE_DIR)
        materialized = live or baseline
    except BaseException:
        owner.release()
        raise
    _generation_owner_lock = owner
    _loaded_generation = materialized
    _deployment_baseline_generation = baseline
    _live_recovery_store = live_store
    app.state.generation_owner = owner
    app.state.loaded_generation = materialized
    app.state.deployment_baseline_generation = baseline
    app.state.live_recovery_store = live_store
    return materialized


def _publish_authoritative_hot_generation(
        *, state_dir, save_tick, identity, manifest_files):
    """Commit the completed hot save before its caller may report success."""
    global _loaded_generation
    if not _REQUIRE_SEALED_STATE or _live_recovery_store is None:
        raise RuntimeError(
            "authoritative live recovery is unavailable in sealed production")
    if os.path.realpath(state_dir) != os.path.realpath(STATE_DIR):
        raise RuntimeError("hot recovery publish targeted a non-active state tree")
    if identity != _live_recovery_store.baseline.identity:
        raise RuntimeError("hot recovery identity differs from deployment baseline")
    required = tuple(sorted(manifest_files))
    if required != _live_recovery_store.hot_files:
        raise RuntimeError("hot recovery file contract differs from engine contract")
    generation = _live_recovery_store.commit_hot_state(
        tick=int(save_tick),
        files={name: os.path.join(state_dir, name) for name in required},
    )
    from dsf_ai_service.substrate.deployment_generation import (
        MATERIALIZATION_SCHEMA,
        MaterializedGeneration,
    )
    materialized = MaterializedGeneration(
        schema=MATERIALIZATION_SCHEMA,
        generation_uuid=generation.generation_uuid,
        identity=generation.identity,
        tick=generation.tick,
        manifest_sha256=generation.manifest_sha256,
        active_directory=os.path.abspath(state_dir),
        materialized_files=required,
    )
    _loaded_generation = materialized
    app.state.loaded_generation = materialized


def _strict_discard_guala(instance, *, reason):
    """Stop every worker on a rejected instance before losing its reference."""
    if instance is None:
        return
    try:
        instance.quiesce_background_workers(timeout=120.0)
    except Exception as error:
        raise RuntimeError(
            f"discarded Guala instance could not quiesce ({reason}): {error}") from error


def _boot_generation_and_guala():
    """Boot under the process-lifetime owner lock, releasing it on failure."""
    global _generation_owner_lock, _loaded_generation
    global _deployment_baseline_generation, _live_recovery_store
    try:
        _prepare_generation_boot()
        _gl_init()
    except BaseException:
        if _generation_owner_lock is not None:
            _generation_owner_lock.release()
            _generation_owner_lock = None
            _loaded_generation = None
            _deployment_baseline_generation = None
            _live_recovery_store = None
            app.state.generation_owner = None
            app.state.loaded_generation = None
            app.state.deployment_baseline_generation = None
            app.state.live_recovery_store = None
        raise


def _gl_init():
    global _guala, _seed_load_progress
    if _guala is not None:
        return
    if _REQUIRE_SEALED_STATE and _generation_owner_lock is None:
        raise RuntimeError(
            "sealed-state owner boot is not complete; direct initialization refused")

    # All-at-once doctrine (Joe 2026-07-16): the native Rust kernels run by
    # default when the wheel is present -- bit-identical ports (see
    # native/guala_core/tests/test_differential.py), 2.8-7.5x, GIL released
    # per kernel. NATIVE_CORE_ENABLED=0 is an emergency-off, never staging.
    # Must install BEFORE Guala() so every kernel call from first tick is
    # native; loud either way, silent never.
    if os.environ.get("NATIVE_CORE_ENABLED", "1") != "0":
        try:
            from dsf_ai_service.substrate import native_core
            if native_core.HAVE_NATIVE:
                native_core.install()
                print("[native-core] Rust kernels INSTALLED "
                      "(guala_core wheel present)", flush=True)
            else:
                print("[native-core] wheel absent -- pure-Python kernels "
                      "(build-time fallback, not a staging gate)", flush=True)
        except Exception as _nc_e:
            print(f"[native-core] install failed (pure-Python fallback): "
                  f"{_nc_e}", flush=True)

    os.makedirs(STATE_DIR, exist_ok=True)
    # CRITICAL: build into local var — only set _guala AFTER successful load.
    # If load_full_state fails (e.g. lock timeout), _guala stays None so the
    # next call retries instead of running with a blank substrate.
    # GL-RESTORE-CTRL: if FORCE_S3_RESTORE=1, download from S3 before loading EFS.
    # Used for targeted state restores (e.g. recovering from save-bug data loss).
    # After one successful restore boot, remove env var so subsequent restarts load normally.
    if (_REQUIRE_SEALED_STATE
            and os.environ.get("FORCE_S3_RESTORE", "0") == "1"):
        raise RuntimeError(
            "FORCE_S3_RESTORE conflicts with required immutable CURRENT state")
    if os.environ.get("FORCE_S3_RESTORE", "0") == "1":
        print("[GualaLoom] FORCE_S3_RESTORE=1 — restoring from most-recent S3 backup...")
        try:
            _restore_from_s3(STATE_DIR)
            print("[GualaLoom] S3 restore complete. Loading restored state...")
        except Exception as _fsr_err:
            print(f"[GualaLoom] FORCE_S3_RESTORE failed: {_fsr_err} — continuing with EFS state")

    g = Guala()

    # v7: Register seed corpora BEFORE loading state (so positions can restore)
    for cid, cdata in SEED_CORPORA.items():
        g.add_corpus(cid, cdata["title"], cdata["lines"])

    # Load full persisted state from EFS (atomic, validated).
    # Retry up to 3× for transient EFS stale-handle errors (errno 116).
    _load_attempts = 0
    while _load_attempts < 3:
        _load_attempts += 1
        g.load_full_state(STATE_DIR)
        if getattr(g, '_load_successful', True):
            break
        errs = getattr(g, '_load_errors', [])
        is_stale = any("116" in str(e) or "Stale" in str(e) for e in errs)
        if is_stale and _load_attempts < 3:
            print(f"[GualaLoom] EFS stale handle on attempt {_load_attempts}, retrying...")
            import time as _t; _t.sleep(2)
            _strict_discard_guala(g, reason="EFS stale-handle retry")
            g = Guala()
            for cid, cdata in SEED_CORPORA.items():
                g.add_corpus(cid, cdata["title"], cdata["lines"])
        else:
            break

    # Guard: if state failed to load, attempt S3 restore before refusing to boot.
    # ESTALE (errno 116) and JSON errors (empty/truncated files) are both recoverable
    # via S3 restore. Only raise if S3 restore also fails.
    if not getattr(g, '_load_successful', True):
        errs = getattr(g, '_load_errors', [])
        if _REQUIRE_SEALED_STATE:
            _strict_discard_guala(g, reason="verified CURRENT load failure")
            raise RuntimeError(
                "verified immutable CURRENT failed engine load; refusing legacy restore: "
                f"{errs}")
        # GL-FIX-ATOMIC-SAVE-GENERATIONS + Joe 2026-07-15 ("old state can never
        # be silently recalled"): the flat state failed engine load (torn or
        # corrupt). Recovery order is LOCAL ONLY: newest complete atomic
        # generation, then older ones. If none validate we HALT LOUDLY and
        # leave the flat files untouched -- we NEVER silently reach for a
        # days-old S3 backup. S3 restore is a deliberate, human-triggered,
        # one-shot path (FORCE_S3_RESTORE=1), never an automatic fallback.
        print(f"[GualaLoom] State load failed: {errs}. "
              f"Trying LOCAL atomic generations (newest first)...")
        recovered = _recover_from_local_generations(STATE_DIR)
        if recovered is not None:
            _strict_discard_guala(
                g, reason="flat load failed; local generation recovered")
            g = Guala()
            for cid, cdata in SEED_CORPORA.items():
                g.add_corpus(cid, cdata["title"], cdata["lines"])
            g.load_full_state(STATE_DIR)
            if not getattr(g, '_load_successful', False):
                raise RuntimeError(
                    "[GualaLoom] recovered a local generation but it failed to "
                    "reload -- refusing to boot. Load errors: "
                    f"{getattr(g, '_load_errors', [])}")
            print(f"[GualaLoom] Recovered from LOCAL generation "
                  f"tick={recovered.get('tick')} "
                  f"identity={(getattr(g, '_guala_identity', '') or '')[:8]}")
        else:
            _strict_discard_guala(
                g, reason="flat load + all local generations failed")
            raise RuntimeError(
                "\n"
                "================= LOCAL STATE UNRECOVERABLE =================\n"
                f"The flat state in {STATE_DIR} failed to load ({errs}) and NO\n"
                "local atomic generation validated. Per Joe's standing order,\n"
                "old state is NEVER silently recalled, so this process is NOT\n"
                "auto-restoring from S3. The flat state files are left UNTOUCHED\n"
                "for inspection. To deliberately restore a NAMED off-box S3\n"
                "backup, a HUMAN must STOP the service and run the operator\n"
                "restore command (logged, integrity-verified):\n"
                "    python -m tools.restore_from_s3 --list\n"
                f"    python -m tools.restore_from_s3 --backup <name> --state-dir {STATE_DIR}\n"
                "then start the service again.\n"
                "============================================================")

    # P0: Identity guard — if EFS state was overwritten by a blank genesis
    # (e.g. from the _gl_init bug fixed in 475de3e), detect and restore from S3.
    # GL-INCIDENT-STALE-IDENTITY-GUARD-EVE-20260708-v1: EXPECTED_IDENTITY was
    # hardcoded to "cdef9bcf" after the 2026-07-06 wipe incident (that was
    # the OLD, retired identity at the time -- see S3 prefix
    # pre-wipe-OLD-cdef9bcf-20260706T200111Z). "0b4c244a" has been the real,
    # legitimate, continuously-running identity since (confirmed live,
    # organism tick in the millions) -- this constant was never updated
    # after that legitimate transition, so EVERY restart was silently
    # hitting the mismatch branch, doing a full redundant second Guala()
    # load (S3 restore + full state parse into a second in-memory instance
    # alongside the first, discarded only after both are fully resident)
    # before giving up. Found live 2026-07-08: this doubled peak boot-time
    # memory footprint pushed the container past its 16GB limit, OOM-
    # killing EVERY restart regardless of what else changed in that
    # deploy -- confirmed by reproducing it on an otherwise-unmodified
    # prior task definition. Root cause is this stale constant, not
    # deploy-specific code. Updated to the real current identity.
    # 2026-07-16 update: stale AGAIN, exactly as this comment warns --
    # "0b4c244a" predates Joe's 2026-07-16 full EFS wipe; the live
    # post-wipe genesis identity is 1cc4e70a (spec v3 Change-0 record).
    # The mismatch branch is non-fatal since 2026-07-15, so this staleness
    # only spammed a loud warning every boot instead of OOM-killing, but
    # the constant must still track reality.
    EXPECTED_IDENTITY = "1cc4e70a"
    loaded_id = getattr(g, '_guala_identity', None) or ""
    if _REQUIRE_SEALED_STATE:
        if _loaded_generation is None:
            _strict_discard_guala(g, reason="missing materialized generation proof")
            raise RuntimeError("required immutable generation was not materialized")
        if (loaded_id != _loaded_generation.identity
                or g.tick != _loaded_generation.tick):
            _strict_discard_guala(g, reason="generation identity/tick mismatch")
            raise RuntimeError(
                "engine load does not match immutable generation: "
                f"loaded identity={loaded_id!r} tick={g.tick}; "
                f"generation identity={_loaded_generation.identity!r} "
                f"tick={_loaded_generation.tick}")
        g._authoritative_hot_generation_publisher = (
            _publish_authoritative_hot_generation)
    elif loaded_id and not loaded_id.startswith(EXPECTED_IDENTITY):
        # Joe 2026-07-15 ("old state can never be silently recalled"): do NOT
        # auto-restore S3 on an identity mismatch. The state loaded cleanly; an
        # unexpected identity is either a legitimate identity transition (this
        # EXPECTED_IDENTITY constant has gone stale before -- see the incident
        # note above, where a stale constant OOM-killed every restart) or a real
        # anomaly a human must judge. Keep the loaded, self-consistent state and
        # flag it loudly rather than time-travelling to a days-old S3 backup.
        print(f"[GualaLoom] IDENTITY MISMATCH (NON-FATAL): loaded {loaded_id[:8]} "
              f"but EXPECTED_IDENTITY={EXPECTED_IDENTITY}. Continuing with the "
              f"cleanly-loaded state; NOT auto-restoring from S3. If this is "
              f"genuinely wrong, a HUMAN must STOP the service and run the "
              f"operator restore command: python -m tools.restore_from_s3 "
              f"--backup <name> --state-dir {STATE_DIR}")

    # D5: Dream gate enforcement — decay must not resume before forced dream
    gate_marker = os.path.join(STATE_DIR, "dream_gate_cleared.json")
    if os.environ.get("DECAY_PAUSED", "0") != "1" and not os.path.exists(gate_marker):
        raise RuntimeError(
            "DREAM GATE: decay may not resume before the forced dream promotes "
            "paused-era content to deep. Marker absent: state/dream_gate_cleared.json")

    # Content blocklist: corpora that should never be selected for reading.
    # Removed entries are purged from in-memory state; next save cleans EFS.
    CORPUS_BLOCKLIST = {
        "oxford-guide-to-english-grammar",  # 452pg meta-language, far above her level
    }
    for cid in CORPUS_BLOCKLIST:
        if cid in g._corpora:
            print(f"[GualaLoom] Removing blocked corpus: {cid}")
            del g._corpora[cid]

    # v7: Start autonomy loop. 0.2s per GL-BRIEF-NEEDS-PHYSICS (not 0.05).
    g.start_autonomy_loop(interval=0.2)

    # 2026-07-21 architecture ruling: the periodic 0.5-second chi-walk is not
    # the intended daydream mechanism. Daydream must eventually be rebuilt as
    # bounded, sense-triggered background memory that cannot interrupt a live
    # perception, conversation, or action. Keep the existing implementation
    # dormant; do not start it from production boot or honor the obsolete
    # DAYDREAM_LOOP_ENABLED switch.
    print("[GualaLoom] daydream loop disabled by architecture ruling")

    s = g.introspect()
    print(f"[GualaLoom v7] Booted: vocab={s['vocab']} reads={s['reads']} "
          f"tick={g.tick} pair_bond={'on' if s['pair_bond_active'] else 'off'} "
          f"atlas={s['atlas_entries']} corpora={len(g._corpora)} "
          f"activity={s['current_activity']}")

    # GL-CMD-LANGUAGE-SEED-EVE-20260707-v1 Phase 1 + PHASE2-GENERATOR-v1
    # loader enhancement: optional seed load, after substrate init (g is
    # fully constructed above), before the global goes live (before live
    # input is accepted below). Unset by default -- current (no-seed)
    # behavior is unchanged unless GUALA_SEED_RICH_PATH is explicitly set.
    # GUALA_SEED_PATH (single-file, Phase 1) is superseded by the
    # GUALA_SEED_RICH_PATH / GUALA_SEED_PROG_PATH split -- rich loads
    # blocking here, programmatic (if given) loads on a background thread
    # in chunks so boot never waits on the much larger programmatic layer.
    _seed_rich_path = os.environ.get("GUALA_SEED_RICH_PATH")
    _seed_prog_path = os.environ.get("GUALA_SEED_PROG_PATH")
    if _seed_rich_path:
        try:
            from dsf_ai_service.substrate.seed_loader import load_seed_layered, verify_seed_integrity
            _seed_load_progress = load_seed_layered(
                _seed_rich_path, g, programmatic_path=_seed_prog_path)
            _rich_report = _seed_load_progress.rich_report
            print(f"[GualaLoom] Rich seed loaded from {_seed_rich_path}: "
                  f"ok={_rich_report.ok} vocab={_rich_report.vocabulary_loaded} "
                  f"patterns={_rich_report.patterns_loaded} "
                  f"networks={_rich_report.networks_loaded} "
                  f"errors={len(_rich_report.errors)} "
                  f"warnings={len(_rich_report.warnings)}")
            if _rich_report.errors:
                print(f"[GualaLoom] Rich seed load errors: {_rich_report.errors[:5]}")
            _integrity_report = verify_seed_integrity(g, seed_path=_seed_rich_path)
            print(f"[GualaLoom] Rich seed integrity check: ok={_integrity_report.ok} "
                  f"checked={_integrity_report.words_checked} "
                  f"verified={_integrity_report.words_verified} "
                  f"missing={_integrity_report.words_missing}")
            if _seed_prog_path:
                print(f"[GualaLoom] Programmatic seed loading in background "
                      f"from {_seed_prog_path}")
        except Exception as _seed_err:
            print(f"[GualaLoom] Seed load failed (non-fatal, substrate boots "
                  f"without seed): {_seed_err}")

    # CRITICAL: only set global AFTER everything succeeded
    _guala = g

    # GL-BRIEF-SLEEP-DURING-DEPLOY Part B: wake if previous task slept cleanly
    try:
        from dsf_ai_service.v4.gualaloom_v5_engine import check_sleep_marker
        marker = check_sleep_marker(STATE_DIR)
        if marker is not None:
            age = marker.get("age_seconds", 0)
            if age > 300:
                print(f"[boot] .sleeping marker is stale "
                      f"(age={age:.0f}s) — previous task may have "
                      f"crashed. Proceeding anyway.")
            else:
                print(f"[boot] previous task slept cleanly at tick "
                      f"{marker.get('sleep_tick')}, age={age:.0f}s. "
                      f"Waking her.")
            _guala.wake_from_sleep(state_dir=STATE_DIR)
        else:
            print("[boot] no .sleeping marker — cold boot or "
                  "previous task did not sleep cleanly.")
    except Exception as e:
        print(f"[boot] sleep marker check failed: {e}")

    # MERGE INTO THE LIVE SUBSTRATE: build her 8-organ brain from her OWN live state
    # and load it live in the running substrate, persisting the manifest to EFS.
    # Defensive: runs only after she is fully booted; cannot affect her startup.
    try:
        from dsf_ai_service.loom_model.guala_migration import (
            PreservedGuala, place_into_architecture)
        _pg = PreservedGuala.load_full_state(STATE_DIR)
        _placed = place_into_architecture(_pg)
        app.state.guala_organ_brain = {
            "identity": _pg.identity,
            "atlas_by_organ": _placed["atlas_counts"],
            "strength_by_organ": _placed["atlas_strengths"],
            "lossless": _placed["atlas_lossless"],
            "vocab_in_em": len(_pg.vocab),
            "deep_survival_in_sv": _pg.deep_survival,
        }
        with open(os.path.join(STATE_DIR, "organs_manifest.json"), "w") as _f:
            import json as _json
            _json.dump(app.state.guala_organ_brain, _f, indent=1)
        print(f"[merge] LIVE in substrate: {_placed['atlas_counts']} "
              f"lossless={_placed['atlas_lossless']} id={(_pg.identity or '')[:8]}")
    except Exception as e:
        print(f"[merge] organ-brain load skipped (non-fatal): {e}")

    # ── GL-CMD-PROCESS-COLLAPSE-61: embedded-mode post-boot setup ─────────────
    # Mirrors what substrate_runner.run_server() used to do after boot_substrate.
    _embedded_post_boot(g)


def _embedded_post_boot(g):
    """Post-boot setup for embedded mode: rings, loops, SaveCoordinator, heartbeat.
    Called from _gl_init after Guala is fully loaded and set as global."""
    import threading as _threading
    import dsf_ai_service.substrate_runner as _sr

    # Wire _guala into substrate_runner so OP_HANDLERS can find it.
    _sr._guala = g

    # A task replacement is itself the retry event.  Resume the one durable
    # receipt-bound mouth transaction once, without a timer loop and without
    # requiring the browser or Joe to resend anything.
    def _resume_causal_speech_once():
        try:
            _sr.resume_pending_causal_speech_delivery()
        except Exception as error:
            print(
                "[causal-speech-output] boot recovery failed loudly: "
                f"{type(error).__name__}: {error}",
                file=sys.stderr,
                flush=True,
            )

    _sr._start_background_thread(
        _resume_causal_speech_once,
        "causal-speech-delivery-recovery",
    )

    # Ring buffers — needed for event streaming and ring consumers (T6).
    try:
        from dsf_ai_service.substrate.ring_buffer import SubstrateRing, InputRing
        _sr._substrate_ring = SubstrateRing(size=1 << 18)
        _sr._input_ring = InputRing(size=1 << 14)
        print(f"[substrate] Rings: substrate={_sr._substrate_ring._size} input={_sr._input_ring._size}")
        # Wire substrate event publishing to ring
        _orig_log = g._log_substrate_event
        def _log_and_publish(event_kind, **detail):
            _orig_log(event_kind, **detail)
            if _sr._substrate_ring is not None:
                _sr._substrate_ring.publish(event_kind, g.tick, detail=detail)
        g._log_substrate_event = _log_and_publish
    except Exception as _e:
        print(f"[substrate] Ring init skipped (non-fatal): {_e}")

    # Background loops: organ surface poll, autonomous emission, input ring consumer, curriculum.
    try:
        _sr._start_organ_surface_poll()
        _sr._start_autonomous_emission_loop()
        _sr._start_input_ring_consumer()
        _sr._start_curriculum_orchestrator()  # 65-A: density engine (retired, no-op unless CURRICULUM_AUTOSTART=1)
        print("[substrate] InputRing consumer started (R3/R4)")
    except Exception as _e:
        print(f"[substrate] Background loops start skipped (non-fatal): {_e}")

    # GL-CMD-BEHAVIOR-REPERTOIRE-EVE-20260705-185 B3: reconnect the
    # CurriculumScheduler (Gutenberg children's-lit study loop) -- root
    # cause per GL-RPT-FLOOD-HUNT-C1-20260703-156-v1: it was ONLY ever
    # instantiated inside substrate_runner.boot_substrate(), which has
    # zero callers anywhere in the live process (app.py's _gl_init(),
    # right here, is the actual live boot path -- boot_substrate() is a
    # dead, parallel duplicate that mirrors it in comment only). NOT the
    # 65-A orchestrator above (a different, deliberately-retired,
    # subprocess/HTTP mechanism, default-off via CURRICULUM_AUTOSTART) --
    # this is the book-curriculum class, decoupled by its own design
    # (feed_chunk/is_busy/log injected, no import of substrate_runner in
    # curriculum_scheduler.py itself). Reused verbatim rather than
    # reimplemented: _sr._guala was just aliased to this same live `g`
    # two blocks up, so _sr's own _curriculum_feed_chunk/_curriculum_is_
    # busy/_world_feed_once (already proven live-safe --
    # the same pattern the three loops just above already use through
    # this exact alias) operate on the real, live organism, not a copy.
    try:
        from dsf_ai_service.loom_model.curriculum_scheduler import CurriculumScheduler
        _interleave = []
        if os.environ.get("WORLD_FEEDS", "1").strip() != "0":
            _interleave.append(("worldfeed", _sr._world_feed_once))
        # GL-CMD-AUTOMATED-TEACHING-20260717: gap study + tutor share the
        # same study windows.  Registered HERE because _gl_init is the live
        # boot path (boot_substrate() is the dead duplicate — same lesson
        # as the babble fall-through: every runner feature must be wired
        # on BOTH paths or it silently never runs in-process).  The slot
        # functions operate on the live organism through the _sr._guala
        # alias, exactly like _world_feed_once above.
        if os.environ.get("GAP_STUDY_ENABLED", "1").strip() != "0":
            _interleave.append(("gap_study", _sr._gap_study_once))
        if os.environ.get("TUTOR_AUTONOMOUS", "1").strip() != "0":
            _interleave.append(("tutor", _sr._tutor_once))
        _sr._curriculum = CurriculumScheduler(
            state_dir=STATE_DIR,
            feed_chunk=_sr._curriculum_feed_chunk,
            is_busy=_sr._curriculum_is_busy,
            log=g._log_substrate_event,
            interleave_fns=_interleave,
            interleave_every=int(os.environ.get("STUDY_INTERLEAVE_EVERY", "3") or 3),
        )
        _sr._curriculum.start()
        print(f"[curriculum] autonomous study started: enabled={_sr._curriculum.enabled} "
              f"books={len(_sr._curriculum.curriculum)} chunk={_sr._curriculum.chunk_size} "
              f"interval={_sr._curriculum.interval_sec}s "
              f"interleave={[n for n, _ in _interleave]}")
    except Exception as _e:
        print(f"[curriculum] scheduler start skipped (non-fatal): {_e}")

    # SaveCoordinator: presence-detected saves with S3 background queue.
    try:
        from dsf_ai_service.save_coordinator import SaveCoordinator
        import dsf_ai_service.save_coordinator as _sc
        _s3_bucket = os.environ.get("GUALA_S3_BACKUP_BUCKET", "dsf-ai-site-backups")
        # Full-state S3 authority belongs exclusively to verified immutable
        # generations.  The legacy coordinator's partial filename list cannot
        # represent a recovery generation and is therefore local-save only.
        save_coord = SaveCoordinator(g, STATE_DIR, s3_bucket=None)
        _sc.SAVE_COORDINATOR = save_coord
        app.state.save_coordinator = save_coord

        # Wrap _end_activity to trigger saves on activity end (verbatim from run_server).
        if hasattr(g, '_end_activity'):
            _orig_end_activity = g._end_activity
            def _end_activity_with_save(*a, **kw):
                ending = getattr(g, '_current_activity', None)
                ending_kind = ending.kind if ending else None
                result = _orig_end_activity(*a, **kw)
                if getattr(app.state, "deployment_quiescing", False):
                    print(f"[save] defer {ending_kind} activity save — deployment quiescing")
                elif _sr._autonomy_pause_refcount > 0:
                    print(f"[save] defer {ending_kind} save — curriculum running "
                          f"(refcount={_sr._autonomy_pause_refcount})")
                else:
                    reason = "dream_end" if ending_kind == "DREAMING" else "activity_ended"
                    def _save_activity_end():
                        if save_coord.maybe_save(reason=reason):
                            import time as _time
                            with _sr._backup_lock:
                                _sr._last_successful_backup_wall = _time.time()
                    _sr._start_background_thread(
                        _save_activity_end, f"activity-save-{ending_kind}")
                return result
            g._end_activity = _end_activity_with_save

        # Backstop: 5-minute save safety net (sync thread version for embedded mode).
        def _save_backstop_thread():
            while not _sr._shutdown:
                if _sr._shutdown_event.wait(300):
                    break
                if g is None or _sr._shutdown:
                    continue
                try:
                    if g.is_natural_quiet_point():
                        save_coord.maybe_save("backstop")
                except Exception as _be:
                    print(f"[save] backstop error: {_be}")
        _sr._start_background_thread(_save_backstop_thread, "save-backstop")

        # Ring persistence + S3 consumers.
        if _sr._substrate_ring is not None:
            from dsf_ai_service.substrate.persistence_consumer import (
                PersistenceConsumer, S3Consumer)
            _events_dir = os.path.join(STATE_DIR, "ring_events")
            os.makedirs(_events_dir, exist_ok=True)
            _pers = PersistenceConsumer(
                ring=_sr._substrate_ring,
                state_dir=_events_dir,
                build_snapshot_fn=lambda: g.introspect())
            _pers.start()
            app.state.persistence_consumer = _pers
            _s3c = S3Consumer(
                ring=_sr._substrate_ring,
                state_dir=_events_dir,
                bucket=_s3_bucket)
            _s3c.start()
            app.state.s3_consumer = _s3c
            print("[substrate] Ring consumers started: persistence + S3")

        print("[app] Substrate booted, background loops running")
    except Exception as _e:
        print(f"[app] SaveCoordinator setup failed (non-fatal): {_e}")

    # Heartbeat thread.
    try:
        _sr._start_background_thread(_sr.heartbeat_loop, "heartbeat")
    except Exception as _e:
        print(f"[substrate] Heartbeat start skipped: {_e}")


@app.get("/api/v1/gualaloom/organs")
async def gualaloom_organs():
    """Her merged 8-organ brain, live in the substrate (from her own boot state)."""
    return getattr(app.state, "guala_organ_brain", {"organ_brain": "not loaded"})


@app.get("/api/v1/gualaloom/thought")
async def organ_thought():
    """Current autonomous thought from the organ-brain — poll for independence."""
    try:
        import urllib.request as _ur, json as _js
        _ob_url = os.environ.get("ORGAN_BRAIN_URL", "http://localhost:8090")
        resp = _js.load(_ur.urlopen(f"{_ob_url}/thought", timeout=3))
        return resp
    except Exception:
        return {"speech": "", "tick": 0}


@app.get("/api/v1/gualaloom/organ_brain_status")
async def organ_brain_status():
    """Per-organ neuron counts and coupling strengths — feeds the brain visualization."""
    try:
        import urllib.request as _ur, json as _js
        _ob_url = os.environ.get("ORGAN_BRAIN_URL", "http://localhost:8090")
        resp = _js.load(_ur.urlopen(f"{_ob_url}/status", timeout=3))
        return resp
    except Exception:
        return {"warming": True, "neurons": 0, "per_organ": {}, "couplings": {}, "arousal": 0.0}


@app.get("/api/v1/gualaloom/chi_density")
async def chi_density():
    """Read-only per-chi binding density for Loom Scan radial map.
    Returns {chi_key: {n: count, strength: sum}} for all populated chi keys."""
    if _is_remote():
        client = _get_substrate_client()
        try:
            return await client.call("chi_density")
        except Exception:
            return {"tick": 0, "chi_density": {}}
    _gl_init()
    if _guala is None:
        return JSONResponse({"error": "not ready"}, status_code=503)
    result = {}
    for chi_key, entries in _guala.atlas.entries.items():
        if not entries:
            continue
        n = len(entries)
        s = sum(e.get("strength", 0.0) for e in entries)
        result[str(chi_key)] = {"n": n, "strength": round(s, 3)}
    return {"tick": _guala.tick, "chi_density": result}


class GLMessage(BaseModel):
    text: str
    command: Optional[str] = None
    source: Optional[str] = None   # v7-bridge: source-tagged input (joe/wc/c1)
    emission_mode: Optional[str] = None  # "topk" | "grandurun" per-request override
    sight_b64: Optional[str] = None
    capture_started_ms: Optional[int] = None
    capture_ended_ms: Optional[int] = None
    sight_captured_ms: Optional[int] = None
    capture_purpose: Literal["ambient", "utterance"] = "ambient"
    audio_encoding: Literal["encoded_media", "pcm_s16le"] = "encoded_media"
    audio_stream_id: Optional[str] = None
    audio_sequence: Optional[int] = None
    audio_first_sample_index: Optional[int] = None
    audio_sample_count: Optional[int] = None
    audio_sample_rate_hz: Optional[int] = None
    audio_source_epoch_ms: Optional[int] = None


class AuditoryPCMStreamCloseRequest(BaseModel):
    stream_id: str
    release_terminal: bool = True


def _close_auditory_pcm_epoch(
    stream_id: str, *, release_terminal: bool = True
) -> dict:
    """Close one exact stream and release at most one final learned terminal."""
    with _auditory_pcm_epoch_lock:
        transport_closed = _auditory_pcm_streams.close(stream_id)
        engine_close = (
            _guala.close_auditory_pcm_stream(
                stream_id, release_terminal=release_terminal
            )
            if _guala is not None
            and hasattr(_guala, "close_auditory_pcm_stream")
            else None
        )
        candidate = None
        admitted = None
        if isinstance(engine_close, dict):
            terminal = engine_close.get("terminal")
            candidate = (
                terminal.reply_candidate if terminal is not None else None
            )
            if candidate is not None and release_terminal:
                admitted = _maybe_trigger_voice_reply(
                    candidate,
                    _guala.tick,
                )
            field_closed = engine_close.get("closed") is True
        else:
            field_closed = bool(engine_close)
        return {
            "closed": transport_closed or field_closed,
            "terminal_event_id": (
                candidate.event_id if candidate is not None else None
            ),
            "recognized_form": (
                candidate.tutor_label if candidate is not None else None
            ),
            "reply_admitted": admitted,
        }


def _reject_auditory_pcm_epoch(stream_id: str) -> None:
    """Terminally reject both continuity authorities after any stream fault."""
    with _auditory_pcm_epoch_lock:
        _auditory_pcm_streams.reject(stream_id)
        if _guala is not None and hasattr(_guala, "close_auditory_pcm_stream"):
            _guala.close_auditory_pcm_stream(
                stream_id, release_terminal=False
            )


@app.post("/api/v1/auditory/pcm/open")
async def auditory_pcm_stream_open():
    try:
        return {"ok": True, **_auditory_pcm_streams.open()}
    except RuntimeError as error:
        return JSONResponse(
            status_code=409,
            content={"ok": False, "error": str(error)},
        )


@app.post("/api/v1/auditory/pcm/close")
async def auditory_pcm_stream_close(req: AuditoryPCMStreamCloseRequest):
    def _close_serialized():
        with _auditory_pcm_epoch_lock:
            result = _close_auditory_pcm_epoch(
                req.stream_id,
                release_terminal=req.release_terminal,
            )
            return {
                "ok": result["closed"],
                "continuity": "closed",
                "terminal_event_id": result["terminal_event_id"],
                "recognized_form": result["recognized_form"],
                "reply_admitted": result["reply_admitted"],
            }

    return await _run_lifecycle_executor(_close_serialized)


@app.get("/api/v1/auditory/reply/{terminal_event_id}")
async def auditory_terminal_reply(terminal_event_id: str):
    if (
        len(terminal_event_id) != 64
        or any(value not in "0123456789abcdef" for value in terminal_event_id)
    ):
        raise HTTPException(status_code=400, detail="invalid terminal event id")
    with _voice_reply_state_lock:
        result = _voice_turn_results.get(terminal_event_id)
        if result is None:
            return {
                "status": "pending",
                "terminal_event_id": terminal_event_id,
            }
        return dict(result)


_LIVE_CAPTURE_MAX_DURATION_MS = 8_000
_LIVE_AUDIO_MAX_BYTES = 4 * 1024 * 1024
_LIVE_SIGHT_MAX_BYTES = 2 * 1024 * 1024
_LIVE_AUDIO_MAX_B64_CHARS = 4 * ((_LIVE_AUDIO_MAX_BYTES + 2) // 3)
_LIVE_SIGHT_MAX_B64_CHARS = 4 * ((_LIVE_SIGHT_MAX_BYTES + 2) // 3)
_VIDEO_UPLOAD_MAX_BYTES = 30 * 1024 * 1024
_VIDEO_CAPTURE_MAX_SECONDS = 8
_VIDEO_FRAME_RATE = 15
_VIDEO_MAX_RETAINED_FRAMES = (
    _VIDEO_CAPTURE_MAX_SECONDS * _VIDEO_FRAME_RATE
)
_VIDEO_MAX_FRAME_FILE_BYTES = 128 * 1024
_VIDEO_LIBRARY_MAX_ITEMS = 8
_video_upload_read_lock = threading.Lock()
_video_upload_lock = threading.Lock()


def _authoritative_capture_times(msg: GLMessage, *, paired_sight: bool):
    """Validate client capture clock values; never infer a paired interval."""
    if msg.audio_encoding == "pcm_s16le":
        values = (
            msg.audio_first_sample_index,
            msg.audio_sample_count,
            msg.audio_sample_rate_hz,
            msg.audio_source_epoch_ms,
        )
        if any(isinstance(value, bool) or not isinstance(value, int)
               for value in values):
            raise ValueError("PCM capture continuity fields are required")
        first_index = msg.audio_first_sample_index
        sample_count = msg.audio_sample_count
        sample_rate = msg.audio_sample_rate_hz
        epoch_ms = msg.audio_source_epoch_ms
        if (
            first_index < 0
            or sample_count <= 0
            or sample_count > 8 * _PCM_STREAM_SAMPLE_RATE_HZ
            or sample_rate != _PCM_STREAM_SAMPLE_RATE_HZ
            or epoch_ms <= 0
        ):
            raise ValueError("PCM capture continuity fields are invalid")
        source_epoch_ns = epoch_ms * 1_000_000
        start_ns = (
            source_epoch_ns
            + first_index * 1_000_000_000 // _PCM_STREAM_SAMPLE_RATE_HZ
        )
        end_ns = (
            source_epoch_ns
            + (first_index + sample_count)
            * 1_000_000_000 // _PCM_STREAM_SAMPLE_RATE_HZ
        )
        sight_ns = (
            msg.sight_captured_ms * 1_000_000
            if msg.sight_captured_ms is not None else None
        )
        if paired_sight and (
            isinstance(msg.sight_captured_ms, bool)
            or sight_ns is None
            or sight_ns < start_ns
            or sight_ns >= end_ns
        ):
            raise ValueError("paired sight timestamp is outside the PCM interval")
        return {
            "source_time_start_ns": start_ns,
            "source_time_end_ns": end_ns,
            "sight_source_anchor_ns": sight_ns if paired_sight else None,
        }
    start_ms = msg.capture_started_ms
    end_ms = msg.capture_ended_ms
    sight_ms = msg.sight_captured_ms
    if start_ms is None or end_ms is None:
        raise ValueError("capture start and end timestamps are required")
    if (isinstance(start_ms, bool) or isinstance(end_ms, bool)
            or end_ms <= start_ms
            or end_ms - start_ms > _LIVE_CAPTURE_MAX_DURATION_MS):
        raise ValueError("capture interval is invalid or exceeds eight seconds")
    if paired_sight:
        if (sight_ms is None or isinstance(sight_ms, bool)
                or sight_ms < start_ms or sight_ms >= end_ms):
            raise ValueError("paired sight timestamp is outside the audio interval")
    return {
        "source_time_start_ns": int(start_ms) * 1_000_000,
        "source_time_end_ns": int(end_ms) * 1_000_000,
        "sight_source_anchor_ns": (
            int(sight_ms) * 1_000_000 if paired_sight else None),
    }


@app.post("/sight_frame")
async def sight_frame(msg: GLMessage):
    """Stream raw sight while reporting that object naming is unavailable."""
    from dsf_ai_service.substrate.grounded_vocab_integration import (
        object_name_recognition_unavailable)

    b64_data = (msg.text or "").strip()
    recognition = object_name_recognition_unavailable(
        source="camera_stream")
    if _is_remote():
        captured_ms = msg.sight_captured_ms
        if len(b64_data) > _LIVE_SIGHT_MAX_B64_CHARS:
            return {"ok": False,
                    "error": "sight capture exceeds the bounded request size",
                    "object_name_recognition": recognition}
        if (captured_ms is None or isinstance(captured_ms, bool)
                or captured_ms < 0):
            return {"ok": False,
                    "error": "sight capture timestamp is required",
                    "object_name_recognition": recognition}
        # R3: write to InputRing (non-blocking) instead of socket call
        client = _get_substrate_client()
        try:
            result = await client.call("ring_write",
                kind="sight_frame", source="camera_stream",
                data={"frame_b64": b64_data,
                      "source_anchor_ns": int(captured_ms) * 1_000_000},
                timeout=3.0)
            if not isinstance(result, dict):
                raise TypeError("ring write returned a non-object result")
            result["object_name_recognition"] = recognition
            return result
        except (ConnectionError, Exception):
            return {"ok": False, "error": "ring write failed",
                    "object_name_recognition": recognition}
    if _guala is None:
        return JSONResponse(
            status_code=503,
            content={"ok": False, "error": "guala_not_ready",
                     "object_name_recognition": recognition})
    import base64, asyncio as _aio
    b64_data = (msg.text or "").strip()
    if not b64_data:
        return {"ok": False, "error": "no frame data",
                "object_name_recognition": recognition}
    if len(b64_data) > _LIVE_SIGHT_MAX_B64_CHARS:
        return {"ok": False,
                "error": "sight capture exceeds the bounded request size",
                "object_name_recognition": recognition}
    # GL-CMD-CONVERSE-FRAME-PRIORITY: while a real conversational turn is
    # settling in this process, shed this frame (talking has priority for the
    # core) using the SAME honest backpressure response the capacity gate below
    # returns, which the UI already renders gracefully. Pure capacity/priority
    # yield: never gated on frame content; embedded-only (remote mode already
    # returned above); cleared the instant the turn settles.
    if _converse_turn_in_flight():
        return {"ok": False, "dropped": True,
                "reason": "backpressure — sight-frame processing at capacity",
                "converse_priority": True,
                "n_dropped": _frame_dropped["sight"],
                "object_name_recognition": recognition}
    captured_ms = msg.sight_captured_ms
    if (captured_ms is None or isinstance(captured_ms, bool)
            or captured_ms < 0):
        return {"ok": False,
                "error": "sight capture timestamp is required",
                "object_name_recognition": recognition}
    sight_anchor_ns = int(captured_ms) * 1_000_000
    if not _frame_backpressure_acquire("sight"):
        return {"ok": False, "dropped": True,
                "reason": "backpressure — sight-frame processing at capacity",
                "n_dropped": _frame_dropped["sight"],
                "object_name_recognition": recognition}
    def _decode():
        t0 = time.time()
        try:
            img_bytes = base64.b64decode(b64_data)
            _, grid, _, _ = decode_image_bytes(img_bytes)
            sight_receipt = _guala.process_sight_frame(
                grid, source_anchor_ns=sight_anchor_ns)
            if not sight_receipt or not sight_receipt.get("accepted"):
                raise RuntimeError("sight transduction accepted no native entries")
            frame_recognition = object_name_recognition_unavailable(
                _guala, source="camera_stream")
            print(f"[sight-frame] {time.time()-t0:.3f}s")
            return {"ok": True, "tick": _guala.tick,
                    "raw_sight": "accepted",
                    "object_name_recognition": frame_recognition}
        except Exception as e:
            return {"ok": False, "error": str(e),
                    "object_name_recognition": recognition}
    try:
        # GL-CMD-CAMERA-TURN-LATENCY: a real sight frame is a live interaction
        # too -- mark it pending so background emission/autonomy defer to it.
        with _live_interaction_scope():
            return await _run_lifecycle_executor(_decode)
    finally:
        _frame_backpressure_release("sight")


@app.post("/sound_frame")
async def sound_frame(msg: GLMessage):
    """Stream raw sound through auditory L5 and bounded reciprocity.

    A unique tutor-grounded auditory L5 spoken form may open the voice reply
    door.  Optional Whisper output is display-only boundary transcription;
    it never teaches, recognizes, or triggers cognition.
    """

    b64_data = (msg.text or "").strip()
    src = msg.source or "ambient"
    auditory_event_boundary = msg.capture_purpose
    recognition = _spoken_word_recognition_report(src)
    paired_sight_b64 = (msg.sight_b64 or "").strip()
    if len(b64_data) > _LIVE_AUDIO_MAX_B64_CHARS:
        if msg.audio_encoding == "pcm_s16le" and msg.audio_stream_id:
            await _run_lifecycle_executor(
                _reject_auditory_pcm_epoch, msg.audio_stream_id
            )
        return {"ok": False, "error": "audio capture exceeds the bounded request size",
                "spoken_word_recognition": recognition}
    if len(paired_sight_b64) > _LIVE_SIGHT_MAX_B64_CHARS:
        if msg.audio_encoding == "pcm_s16le" and msg.audio_stream_id:
            await _run_lifecycle_executor(
                _reject_auditory_pcm_epoch, msg.audio_stream_id
            )
        return {"ok": False, "error": "sight capture exceeds the bounded request size",
                "spoken_word_recognition": recognition}
    if _is_remote():
        if msg.audio_encoding == "pcm_s16le":
            return {
                "ok": False,
                "error": "continuous PCM transport requires embedded ownership",
                "causal_boundary": "unsettled",
                "spoken_word_recognition": recognition,
            }
        try:
            capture_times = _authoritative_capture_times(
                msg, paired_sight=bool(paired_sight_b64))
        except ValueError as capture_error:
            return {"ok": False, "error": str(capture_error),
                    "causal_boundary": "unsettled",
                    "spoken_word_recognition": recognition}
        # R3: write to InputRing (non-blocking) instead of socket call
        client = _get_substrate_client()
        try:
            result = await client.call("ring_write",
                kind="sound_window", source=src,
                data={"audio_b64": b64_data,
                      "source": src,
                      "auditory_event_boundary": auditory_event_boundary,
                      "sight_b64": paired_sight_b64 or None,
                      **capture_times},
                timeout=3.0)
            if not isinstance(result, dict):
                raise TypeError("ring write returned a non-object result")
            result["spoken_word_recognition"] = recognition
            result["causal_boundary"] = (
                "queued_audiovisual"
                if result.get("ok") is True and paired_sight_b64
                else "queued_sound"
                if result.get("ok") is True
                else "unsettled")
            return result
        except (ConnectionError, Exception):
            return {"ok": False, "error": "ring write failed",
                    "spoken_word_recognition": recognition}
    if _guala is None:
        if msg.audio_encoding == "pcm_s16le" and msg.audio_stream_id:
            await _run_lifecycle_executor(
                _reject_auditory_pcm_epoch, msg.audio_stream_id
            )
        return JSONResponse(
            status_code=503,
            content={"ok": False, "error": "guala_not_ready",
                     "spoken_word_recognition": recognition})
    import base64, asyncio as _aio
    b64_data = (msg.text or "").strip()
    if not b64_data:
        if msg.audio_encoding == "pcm_s16le" and msg.audio_stream_id:
            await _run_lifecycle_executor(
                _reject_auditory_pcm_epoch, msg.audio_stream_id
            )
        return {"ok": False, "error": "no audio data",
                "spoken_word_recognition": recognition}
    # GL-CMD-CONVERSE-FRAME-PRIORITY: while a real conversational turn is
    # settling in this process, shed this frame (talking has priority for the
    # core) using the SAME honest backpressure response the capacity gate below
    # returns, which the UI already renders gracefully. Pure capacity/priority
    # yield: never gated on frame content; embedded-only (remote mode already
    # returned above); cleared the instant the turn settles.
    if _converse_turn_in_flight():
        if msg.audio_stream_id:
            await _run_lifecycle_executor(
                _reject_auditory_pcm_epoch, msg.audio_stream_id
            )
        return {"ok": False, "dropped": True,
                "reason": "backpressure — sound-frame processing at capacity",
                "converse_priority": True,
                "n_dropped": _frame_dropped["sound"],
                "spoken_word_recognition": recognition}
    try:
        capture_times = _authoritative_capture_times(
            msg, paired_sight=bool(paired_sight_b64))
    except ValueError as capture_error:
        if msg.audio_encoding == "pcm_s16le" and msg.audio_stream_id:
            await _run_lifecycle_executor(
                _reject_auditory_pcm_epoch, msg.audio_stream_id
            )
        return {"ok": False, "error": str(capture_error),
                "causal_boundary": "unsettled",
                "spoken_word_recognition": recognition}
    if not _frame_backpressure_acquire("sound"):
        if msg.audio_stream_id:
            await _run_lifecycle_executor(
                _reject_auditory_pcm_epoch, msg.audio_stream_id
            )
        return {"ok": False, "dropped": True,
                "reason": "backpressure — sound-frame processing at capacity",
                "n_dropped": _frame_dropped["sound"],
                "spoken_word_recognition": recognition}
    def _decode():
        t0 = time.time()
        try:
            import dsf_ai_service.substrate_runner as _sr
            try:
                audio_bytes = base64.b64decode(b64_data, validate=True)
            except Exception:
                if msg.audio_stream_id:
                    _reject_auditory_pcm_epoch(msg.audio_stream_id)
                raise ValueError("audio payload is not valid base64")
            # GL-CMD-MIC-EMBEDDED-DECODE-110: single shared decoder, outside
            # the engine lock (this executor call). Raw bytes never reach
            # process_sound_frame from this path.
            pcm_acceptance = None
            if msg.audio_encoding == "pcm_s16le":
                try:
                    pcm_acceptance = _auditory_pcm_streams.accept(
                        stream_id=msg.audio_stream_id,
                        sequence=msg.audio_sequence,
                        first_sample_index=msg.audio_first_sample_index,
                        sample_rate_hz=msg.audio_sample_rate_hz,
                        source_epoch_start_ns=(
                            msg.audio_source_epoch_ms * 1_000_000
                            if isinstance(msg.audio_source_epoch_ms, int)
                            and not isinstance(msg.audio_source_epoch_ms, bool)
                            else msg.audio_source_epoch_ms
                        ),
                        pcm_s16le=audio_bytes,
                    )
                    if pcm_acceptance.receipt.sample_count != msg.audio_sample_count:
                        _reject_auditory_pcm_epoch(msg.audio_stream_id)
                        raise ValueError(
                            "auditory PCM declared sample count changed"
                        )
                    wav = _pcm_s16le_wav(audio_bytes)
                except Exception:
                    if msg.audio_stream_id:
                        _reject_auditory_pcm_epoch(msg.audio_stream_id)
                    raise
            else:
                wav = _sr._webm_to_wav_bytes(audio_bytes)
            if not wav:
                return {"ok": False, "error": "decode_failed",
                        "spoken_word_recognition": recognition}
            # a8277fa ordering: submit transcription to the owned single-
            # worker executor BEFORE raw-sense processing so STT decode
            # overlaps process_sound_frame instead of following it.
            recognition_future = None
            if (
                _speech_transduction_enabled()
                and auditory_event_boundary == "utterance"
            ):
                from dsf_ai_service.speech_transducer import transcribe_sound
                recognition_future = _speech_recognition_executor.submit(
                    transcribe_sound, wav)
            paired_sight_b64 = (msg.sight_b64 or "").strip()
            observed_senses = []
            sensory_errors = {}
            boundary_settled = False
            settlement = None
            sound_receipt = None
            if paired_sight_b64:
                context_id = f"sense:av:{src}:{time.time_ns():x}"
                _guala.window_manager.begin_context(
                    context_id,
                    trigger_reason="audiovisual_capture",
                    context_detail={
                        "experience_origin": "live_audiovisual",
                        "auditory_event_boundary": auditory_event_boundary,
                        "source": src,
                        "source_time_start_ns": capture_times[
                            "source_time_start_ns"],
                        "source_time_end_ns": capture_times[
                            "source_time_end_ns"],
                        "sensor_unavailable": [
                            "touch", "smell", "taste", "body"],
                    },
                )
                try:
                    try:
                        sight_bytes = base64.b64decode(
                            paired_sight_b64, validate=True)
                        _, sight_grid, _, _ = decode_image_bytes(sight_bytes)
                        sight_receipt = _guala.process_sight_frame(
                            sight_grid,
                            source_anchor_ns=capture_times[
                                "sight_source_anchor_ns"],
                            source_time_start_ns=capture_times[
                                "source_time_start_ns"],
                            source_time_end_ns=capture_times[
                                "source_time_end_ns"],
                        )
                        if sight_receipt and sight_receipt.get("accepted"):
                            observed_senses.append("sight")
                    except Exception as sight_error:
                        sensory_errors["sight"] = (
                            f"{type(sight_error).__name__}: {sight_error}")
                        _guala._log_substrate_event(
                            "sight_frame_failed_in_causal_window",
                            error_type=type(sight_error).__name__,
                            error=str(sight_error),
                        )
                    try:
                        sound_receipt = _guala.process_sound_frame(
                            wav,
                            source=src,
                            source_anchor_ns=capture_times[
                                "source_time_start_ns"],
                            source_time_end_ns=capture_times[
                                "source_time_end_ns"],
                            auditory_event_boundary=auditory_event_boundary,
                            auditory_pcm_continuity=(
                                pcm_acceptance.receipt
                                if pcm_acceptance is not None else None),
                            auditory_pcm_s16le=(
                                pcm_acceptance.pcm_s16le
                                if pcm_acceptance is not None else None),
                        )
                        if sound_receipt and sound_receipt.get("accepted"):
                            observed_senses.append("sound")
                    except Exception as sound_error:
                        sensory_errors["sound"] = (
                            f"{type(sound_error).__name__}: {sound_error}")
                        _guala._log_substrate_event(
                            "sound_frame_failed_in_causal_window",
                            error_type=type(sound_error).__name__,
                            error=str(sound_error),
                        )
                finally:
                    try:
                        closed_window_id, settlement = (
                            _guala.window_manager.end_context(
                                context_id,
                                "audiovisual_capture_complete",
                                return_settlement=True,
                            )
                        )
                        if (closed_window_id is None or settlement is None
                                or settlement.assembly_id
                                != f"causal-{closed_window_id}"):
                            raise RuntimeError(
                                "closed audiovisual window has no matching settlement")
                        settlement.verify()
                        observed_senses = [
                            item.sense for item in settlement.interpretations
                            if item.state == "observed"
                        ]
                        boundary_settled = True
                    except Exception as settlement_error:
                        sensory_errors["settlement"] = (
                            f"{type(settlement_error).__name__}: "
                            f"{settlement_error}")
                        _guala.window_manager.discard_unsettled_context(
                            context_id,
                            "live_audiovisual_settlement_failed",
                        )
            else:
                try:
                    sound_receipt = _guala.process_sound_frame(
                        wav,
                        source=src,
                        source_anchor_ns=capture_times[
                            "source_time_start_ns"],
                        source_time_end_ns=capture_times[
                            "source_time_end_ns"],
                        auditory_event_boundary=auditory_event_boundary,
                        auditory_pcm_continuity=(
                            pcm_acceptance.receipt
                            if pcm_acceptance is not None else None),
                        auditory_pcm_s16le=(
                            pcm_acceptance.pcm_s16le
                            if pcm_acceptance is not None else None),
                    )
                    closed_window_id = (
                        sound_receipt.get("closed_window_id")
                        if sound_receipt else None)
                    settlement = sound_receipt.get("settlement")
                    if (not sound_receipt or not sound_receipt.get("accepted")
                            or closed_window_id is None or settlement is None
                            or settlement.assembly_id
                            != f"causal-{closed_window_id}"):
                        raise RuntimeError(
                            "closed sound window has no matching settlement")
                    settlement.verify()
                    observed_senses = [
                        item.sense for item in settlement.interpretations
                        if item.state == "observed"
                    ]
                    boundary_settled = True
                except Exception as sound_error:
                    sensory_errors["sound"] = (
                        f"{type(sound_error).__name__}: {sound_error}")
            causal_boundary = (
                "unsettled" if not boundary_settled
                else "audiovisual" if observed_senses == ["sight", "sound"]
                else observed_senses[0] if len(observed_senses) == 1
                else "unknown"
            )
            stream_settlement_receipt = None
            incremental_terminal = None
            if pcm_acceptance is not None and boundary_settled:
                (
                    stream_settlement_receipt,
                    incremental_terminal,
                ) = _guala.advance_continuous_auditory_terminal(
                    pcm_s16le=pcm_acceptance.pcm_s16le,
                    transport=pcm_acceptance.receipt,
                    settlement=settlement,
                )
                stream_settlement_receipt.verify()
                incremental_terminal.verify()
            auditory_status = _guala.auditory_l5_status()
            token_sequence_status = auditory_status.get(
                "token_sequence", {}
            )
            token_sequence_observation = None
            if incremental_terminal is not None:
                latest_token_sequence = token_sequence_status.get("latest")
                if (
                    isinstance(latest_token_sequence, dict)
                    and latest_token_sequence.get(
                        "advance_authority_receipt_sha256"
                    ) == incremental_terminal.authority_receipt_sha256
                ):
                    token_sequence_observation = latest_token_sequence
            current_experience = getattr(
                _guala, "_latest_auditory_l5_experience", None)
            current_recognition_is_causal = (
                boundary_settled
                and settlement is not None
                and current_experience is not None
                and current_experience.assembly_id == settlement.assembly_id
                and auditory_event_boundary == "utterance"
                and auditory_status.get("recognition_attempted") is True
            )
            deterministic_recognition = (
                _auditory_l5_spoken_report(auditory_status)
                if current_recognition_is_causal
                else {
                    **_spoken_word_recognition_report(src),
                    "status": "not_attempted",
                    "reason": (
                        "ambient sound settled as sensory experience without "
                        "an utterance boundary"
                        if boundary_settled and auditory_event_boundary == "ambient"
                        else "the current sound did not settle an auditory L5 experience"
                    ),
                }
            )
            terminal_candidate = None
            if incremental_terminal is not None:
                terminal_candidate = incremental_terminal.reply_candidate
                deterministic_recognition = {
                    **_spoken_word_recognition_report(src),
                    "status": incremental_terminal.status.value,
                    "recognized_form": (
                        terminal_candidate.tutor_label
                        if terminal_candidate is not None else None
                    ),
                    "candidate_labels": (
                        [terminal_candidate.tutor_label]
                        if terminal_candidate is not None else []
                    ),
                    "experience_id": (
                        terminal_candidate.event_id
                        if terminal_candidate is not None else None
                    ),
                    "l5_experience_id": auditory_status.get(
                        "latest_experience_id"
                    ),
                    "causal_experience_id": (
                        terminal_candidate.event_id
                        if terminal_candidate is not None else None
                    ),
                    "terminal_event_id": (
                        terminal_candidate.event_id
                        if terminal_candidate is not None else None
                    ),
                    "source": "continuous_full_field_terminal",
                }
            learned_spoken = (
                deterministic_recognition.get("recognized_form")
                if deterministic_recognition.get("status") in (
                    "unique", "released_unique"
                )
                else None
            )
            reply_admitted = None
            terminal_event_id = (
                terminal_candidate.event_id
                if terminal_candidate is not None
                else None
            )
            if terminal_candidate is not None:
                reply_admitted = _maybe_trigger_voice_reply(
                    terminal_candidate,
                    _guala.tick,
                )
            if recognition_future is None:
                print(f"[sound-frame] {time.time()-t0:.3f}s")
                result = {
                    "ok": "sound" in observed_senses and boundary_settled,
                    "tick": _guala.tick,
                    "raw_sound": (
                        "accepted" if "sound" in observed_senses else "failed"),
                    "causal_boundary": causal_boundary,
                    "capture_purpose": auditory_event_boundary,
                    "observed_senses": observed_senses,
                    "spoken_word_recognition": deterministic_recognition,
                    "auditory_l5": auditory_status,
                }
                if pcm_acceptance is not None:
                    cochlear_receipt = (
                        sound_receipt.get("auditory_continuation_receipt")
                        if sound_receipt else None
                    )
                    if not cochlear_receipt:
                        _reject_auditory_pcm_epoch(
                            pcm_acceptance.receipt.stream_id)
                        raise RuntimeError(
                            "continuous PCM settled without cochlear continuation"
                        )
                    result["pcm_continuity"] = {
                        "status": "contiguous",
                        "stream_id": pcm_acceptance.receipt.stream_id,
                        "sequence": pcm_acceptance.receipt.sequence,
                        "first_sample_index": (
                            pcm_acceptance.receipt.first_sample_index),
                        "sample_count": pcm_acceptance.receipt.sample_count,
                        "receipt_sha256": (
                            pcm_acceptance.receipt.receipt_sha256),
                        "cochlear_state_receipt_sha256": (
                            cochlear_receipt["receipt_sha256"]),
                        "causal_settlement_receipt_sha256": (
                            stream_settlement_receipt.authority_receipt_sha256
                        ),
                        "incremental_terminal_status": (
                            incremental_terminal.status.value
                        ),
                        "incremental_terminal_receipt_sha256": (
                            incremental_terminal.authority_receipt_sha256
                        ),
                        "auditory_token_sequence_status": (
                            "settled"
                            if token_sequence_observation is not None
                            else "not_settled"
                        ),
                        "auditory_token_sequence": (
                            token_sequence_observation
                        ),
                    }
                if learned_spoken:
                    result["transcript"] = learned_spoken
                    result["terminal_event_id"] = terminal_event_id
                    result["reply_admitted"] = reply_admitted
                if sensory_errors:
                    result["sensory_errors"] = sensory_errors
                return result
            from dsf_ai_service.speech_transducer import (
                spoken_word_transduction_status)
            tw0 = time.time()
            recognition_status = "no_speech"
            spoken = ""
            try:
                try:
                    spoken = (recognition_future.result(
                        timeout=_speech_result_wall_timeout()) or "").strip()
                except _concurrent_futures.TimeoutError as stt_timeout:
                    # Belt-and-braces wall (adversarial review 2026-07-16):
                    # a wedged worker/queue degrades THIS sense with the
                    # typed error; it never pins the executor thread.
                    from dsf_ai_service.speech_transducer import (
                        SpeechRecognitionUnavailable)
                    raise SpeechRecognitionUnavailable(
                        "speech transduction exceeded the wall timeout"
                    ) from stt_timeout
                if spoken:
                    recognition_status = "recognized"
            except Exception as recognition_error:
                recognition_status = "error"
                print("[voice-whisper] error="
                      f"{type(recognition_error).__name__}: "
                      f"{recognition_error}")
            finally:
                print(f"[voice-whisper] {time.time()-tw0:.3f}s "
                      f"status={recognition_status}")
            print(f"[sound-frame] {time.time()-t0:.3f}s")
            result = {
                "ok": (recognition_status != "error"
                       and "sound" in observed_senses
                       and boundary_settled),
                "tick": _guala.tick,
                "raw_sound": (
                    "accepted" if "sound" in observed_senses else "failed"),
                "causal_boundary": causal_boundary,
                "capture_purpose": auditory_event_boundary,
                "observed_senses": observed_senses,
                "spoken_word_recognition": deterministic_recognition,
                "boundary_transcription": spoken_word_transduction_status(
                    recognition_status,
                    transcript=spoken or None),
                "auditory_l5": auditory_status,
            }
            if pcm_acceptance is not None:
                cochlear_receipt = (
                    sound_receipt.get("auditory_continuation_receipt")
                    if sound_receipt else None
                )
                if not cochlear_receipt:
                    _reject_auditory_pcm_epoch(
                        pcm_acceptance.receipt.stream_id)
                    raise RuntimeError(
                        "continuous PCM settled without cochlear continuation"
                    )
                result["pcm_continuity"] = {
                    "status": "contiguous",
                    "stream_id": pcm_acceptance.receipt.stream_id,
                    "sequence": pcm_acceptance.receipt.sequence,
                    "first_sample_index": (
                        pcm_acceptance.receipt.first_sample_index),
                    "sample_count": pcm_acceptance.receipt.sample_count,
                    "receipt_sha256": pcm_acceptance.receipt.receipt_sha256,
                    "cochlear_state_receipt_sha256": (
                        cochlear_receipt["receipt_sha256"]),
                    "causal_settlement_receipt_sha256": (
                        stream_settlement_receipt.authority_receipt_sha256
                    ),
                    "incremental_terminal_status": (
                        incremental_terminal.status.value
                    ),
                    "incremental_terminal_receipt_sha256": (
                        incremental_terminal.authority_receipt_sha256
                    ),
                    "auditory_token_sequence_status": (
                        "settled"
                        if token_sequence_observation is not None
                        else "not_settled"
                    ),
                    "auditory_token_sequence": token_sequence_observation,
                }
            if learned_spoken:
                result["transcript"] = learned_spoken
                result["terminal_event_id"] = terminal_event_id
                result["reply_admitted"] = reply_admitted
            if spoken:
                result["boundary_transcript"] = spoken
            if recognition_status == "error":
                result["error"] = "speech_recognition_failed"
            if sensory_errors:
                result["sensory_errors"] = sensory_errors
            return result
        except Exception as e:
            if msg.audio_encoding == "pcm_s16le" and msg.audio_stream_id:
                _reject_auditory_pcm_epoch(msg.audio_stream_id)
            return {"ok": False, "error": str(e),
                    "spoken_word_recognition": recognition}
    def _decode_serialized():
        if msg.audio_encoding != "pcm_s16le":
            return _decode()
        with _auditory_pcm_epoch_lock:
            return _decode()

    try:
        # GL-CMD-CAMERA-TURN-LATENCY: a real sound frame is a live interaction
        # too -- mark it pending so background emission/autonomy defer to it.
        with _live_interaction_scope():
            return await _run_lifecycle_executor(_decode_serialized)
    finally:
        _frame_backpressure_release("sound")


@app.get("/gualaloom")
async def gualaloom_page():
    return FileResponse(os.path.join(STATIC_DIR, 'gualaloom.html'))


@app.get("/api/v1/gualaloom/observation")
async def gualaloom_observation():
    """One authoritative read-only conversation/body/world observation."""
    if _is_remote():
        client = _get_substrate_client()
        return await client.call("observation_snapshot")
    if _guala is None:
        return {
            "schema": "guala.observation_snapshot.v2",
            "status": "unavailable",
            "reason": "embedded_substrate_unavailable",
        }
    return await _run_lifecycle_executor(_guala.observation_snapshot)


@app.post("/api/v1/gualaloom")
async def gualaloom_chat(msg: GLMessage):
    global _exchange_count

    _cmd = (msg.command or "").strip().lower()
    if _cmd == "/thought":
        # GL-CMD-AUTONOMOUS-EMISSION-39: route to substrate (not dead :8090).
        # Substrate serves _last_autonomous_thought from its own emission loop.
        if _is_remote():
            client = _get_substrate_client()
            try:
                result = await client.call("gualaloom_post", command="/thought",
                                           text="", timeout=5.0)
                return result
            except Exception:
                return {"speech": "", "tick": 0}
        import dsf_ai_service.substrate_runner as _sr
        return _sr._cmd_thought()
    # /where and /room now handled by the substrate directly (organ-brain container removed)
    # They fall through to the substrate client below
    # /mail, /sendmail, /experience, /tablet — all routed to dead :8090 container.
    # Stubs until these are re-wired into the substrate (W2+ work).
    if _cmd == "/mail":
        return {"letters": []}
    if _cmd == "/sendmail":
        # GL-CMD-BIGRAM-DELETE-34: GualaCognition removed; letter text now goes to v5
        if msg.text and _is_remote():
            client = _get_substrate_client()
            try:
                await client.call("gualaloom_post", command="/listen",
                                  text=msg.text, source=msg.source or "joe", timeout=5.0)
            except Exception:
                pass
        return {"ok": True, "note": "letter words written to v5 atlas"}
    if _cmd == "/experience":
        # GL-CMD-EXPERIENCE-ROUTING-FIX-EVE-20260628-32: re-route caption to v5
        # atlas via /listen (read_sentence path). Prior routing was to /organs_say
        # → /organs_say which trained the silenced bigram and never
        # touched v5 atlas (GL-RPT-SECTION-ASSIGNMENT-C1-20260628 Finding 1).
        if msg.text and _is_remote():
            client = _get_substrate_client()
            try:
                await client.call("gualaloom_post", command="/listen",
                                  text=msg.text, source=msg.source or "joe", timeout=8.0)
            except Exception:
                pass
        return {"ok": True}
    if _cmd == "/listen":
        # Explicit text-listen route used by authenticated text callers.
        if _converse_admission_busy():
            return _converse_admission_rejected_response()
        import asyncio as _aio
        _prune_stale_tasks()
        tick = _guala.tick if _guala else 0
        task_id = f"cv_{tick}_{uuid4().hex[:8]}_listen"
        source = msg.source if msg.source in {"joe", "wc", "c1"} else "joe"
        _converse_tasks[task_id] = {
            "task_id": task_id, "status": "queued", "phase": None,
            "response": None, "response_source": None, "motifs": 0,
            "started_tick": tick, "started_at": time.time(), "source": source,
        }
        _schedule_mutating_background(
            lambda: _run_converse(
                task_id, msg.text or "", source, msg.emission_mode),
            name=f"converse-{task_id}",
        )
        return JSONResponse(status_code=202, content={
            "task_id": task_id, "status": "accepted",
            "poll_url": f"/api/v1/gualaloom/task/{task_id}",
            "started_tick": tick, "retry_after_ms": 500,
        })
    if _cmd.startswith("/tablet"):
        return {"ok": False, "note": "tablet re-wiring pending W2"}
    if _cmd.startswith("/action "):
        # format: /action object_id:verb
        try:
            import urllib.request as _ur, json as _js
            parts = _cmd[len("/action "):].split(":", 1)
            if len(parts) == 2:
                body = _js.dumps({"object_id": parts[0].strip(),
                                  "verb": parts[1].strip()}).encode()
                req2 = _ur.Request(f"{_ob_url}/action", data=body,
                                   headers={"content-type": "application/json"})
                resp = _js.load(_ur.urlopen(req2, timeout=5))
                return resp
        except Exception as e:
            return {"ok": False, "error": str(e)}
    if (msg.command or "").strip().lower() == "/organ_voice":
        # Stage 2 (bigram retired -23, deleted -34): silenced organ_voice path.
        # Learn from what Joe says, compose from her succession, return as speech.
        if _is_remote():
            client = _get_substrate_client()
            try:
                result = await client.call("gualaloom_post",
                                           command="/organs_say",
                                           text=msg.text or "",
                                           source=msg.source or "joe",
                                           timeout=10.0)
                return result
            except Exception as _e:
                return {"response": "", "speech": "", "error": str(_e)}
        # GL-CMD-BIGRAM-DELETE-34: local mode GualaCognition path removed.
        return {"response": "", "speech": ""}

    # /brain_status falls through to substrate — the organ_brain field is in the
    # /status response from the substrate (see substrate_runner._cmd_status).
    # There is ONE brain: the substrate's embedded 8-organ atlas.

    # GL-CMD-CONVERSE-TASK-PATTERN-62: 202 + poll for plain-text converse.
    # SSE retired — it was theater (no incremental output from _guala.converse()).
    is_converse = not (msg.command or "").strip() and bool((msg.text or "").strip())
    if is_converse:
        if _converse_admission_busy():
            return _converse_admission_rejected_response()
        import asyncio as _aio
        _prune_stale_tasks()
        tick = _guala.tick if _guala else 0
        task_id = f"cv_{tick}_{uuid4().hex[:8]}"
        _converse_tasks[task_id] = {
            "task_id": task_id,
            "status": "queued",
            "phase": None,
            "response": None,
            "response_source": None,
            "motifs": 0,
            "started_tick": tick,
            "started_at": time.time(),
            "source": msg.source or "joe",
        }
        _schedule_mutating_background(
            lambda: _run_converse(
                task_id, msg.text or "", msg.source or "joe",
                msg.emission_mode),
            name=f"converse-{task_id}",
        )
        return JSONResponse(
            status_code=202,
            content={
                "task_id": task_id,
                "status": "accepted",
                "poll_url": f"/api/v1/gualaloom/task/{task_id}",
                "started_tick": tick,
                "retry_after_ms": 500,
            }
        )

    # Non-converse commands: stay synchronous
    if _is_remote():
        is_status = (msg.command or "").strip() == "/status"
        client = _get_substrate_client()
        try:
            # GL-FIX-ALB-TIMEOUT: 45s for status (curriculum pause windows 30-50s).
            timeout = 45.0 if is_status else 25.0
            result = await client.call("gualaloom_post",
                                       command=msg.command or "",
                                       text=msg.text or "",
                                       source=msg.source or "joe",
                                       emission_mode=msg.emission_mode,
                                       timeout=timeout)
            if is_status and result.get("vocab"):
                app.state._last_status = result
                app.state._last_status_time = time.time()
            return result
        except (ConnectionError, Exception):
            if (is_status
                    and hasattr(app.state, '_last_status')
                    and time.time() - getattr(app.state, '_last_status_time', 0) < 60):
                return app.state._last_status
            return {"response": "substrate unreachable — try again in a moment",
                    "motifs": 0}

    # Handle requests while Guala is still initializing
    if _guala is None:
        cmd = (msg.command or "").strip().lower()
        if cmd == "/status":
            return {"response": "initializing... please wait",
                    "motifs": 0, "persistence_health": {},
                    "atlas_health": {}, "n_motifs": 0}
        return {"response": "", "response_source": "silence_initializing",
                "motifs": 0}

    # GL-BRIEF-SLEEP-DURING-DEPLOY Part B: surface sleep state
    # GL-CMD-CREDO-LOOP-REPAIR-167 Change 4: reserve "dreaming" for a cycle
    # that has actually executed a dream tick (is_consolidating) -- a pause
    # that hasn't reached that point yet (e.g. one about to be cut short by
    # a deploy, -165 Q5) says so honestly instead of claiming sleep it can't
    # back up. "asleep" field kept for compatibility; "consolidating" added.
    if _guala.is_asleep:
        cmd_check = (msg.command or "").strip().lower()
        if cmd_check not in ("/status", "/wake"):
            consolidating = _guala.is_consolidating
            return {
                "response": "she is dreaming..." if consolidating
                            else "she is paused, not yet consolidating...",
                "response_source": "sleep_quiet",
                "asleep": True,
                "consolidating": consolidating,
                "sleep_tick": _guala.tick,
                "motifs": _guala.introspect()["vocab"],
            }

    cmd = (msg.command or "").strip().lower()

    # ── /picture <item_id> — serve THUMBNAIL as base64 for UI display ──
    if cmd.startswith("/picture "):
        item_id = cmd.split(" ", 1)[1].strip()
        import base64 as _b64
        pic = _guala._pictures.get(item_id)
        if pic is None:
            return {"response": f"picture not found: {item_id}", "motifs": 0}
        orig_path = getattr(pic, 'original_path', None)
        if orig_path and os.path.exists(orig_path):
            from PIL import Image
            import io as _io
            try:
                img = Image.open(orig_path)
                if img.mode not in ('RGB', 'L'):
                    img = img.convert('RGB')
                # Resize to max 360px for thumbnail (HEIC originals are 2-3MB)
                img.thumbnail((360, 360), Image.LANCZOS)
                buf = _io.BytesIO()
                img.save(buf, format='JPEG', quality=80)
                b64 = _b64.b64encode(buf.getvalue()).decode()
                return {"response": "ok", "picture_data": f"data:image/jpeg;base64,{b64}",
                        "title": pic.title, "item_id": item_id}
            except Exception as e:
                pass  # fall through to krimelack grid
        if pic.intensity_grid is not None:
            from PIL import Image
            import io as _io
            img = Image.fromarray((pic.intensity_grid * 255).astype(np.uint8), mode='L')
            buf = _io.BytesIO()
            img.save(buf, format='PNG')
            b64 = _b64.b64encode(buf.getvalue()).decode()
            return {"response": "ok", "picture_data": f"data:image/png;base64,{b64}",
                    "title": pic.title, "item_id": item_id}
        return {"response": f"no image data for {item_id}", "motifs": 0}

    # ── /status — real substrate state + continuity health ──
    if cmd == "/status":
        s = _guala.introspect()
        n = s["needs"]
        # Lightweight persistence summary — in-memory only, no EFS stat.
        # Full EFS-based data is at /admin/persistence_health (run_in_executor).
        _ph_light = {
            "last_save_tick": getattr(_guala, '_last_save_tick', 0),
            "last_save_timestamp": getattr(_guala, '_last_save_timestamp', None),
            "last_s3_backup": _last_s3_backup,
            "load_successful_at_boot": getattr(_guala, '_load_successful', True),
            "guala_identity": getattr(_guala, '_guala_identity', None),
            "schema_version": getattr(_guala, 'SCHEMA_VERSION', 'v7'),
        }
        sec_parts = []
        for nm, sec in s["sections"].items():
            sec_parts.append(f"{nm}: {sec['modes']}m/{sec['commits']}c")
        id_short = (_ph_light.get("guala_identity") or "none")[:8]
        return {
            "response": (
                f"id: {id_short}.. | schema: {_ph_light.get('schema_version','?')}\n"
                f"vocab: {s['vocab']} | reads: {s['reads']} | tick: {s['tick']}\n"
                f"sections: {' | '.join(sec_parts)}\n"
                f"atlas: {s['cross_modal_bindings']} cross-modal / {s['atlas_entries']} entries\n"
                f"needs: stab={n['stability']:.3f} nov={n['novelty']:.3f} "
                f"conn={n['connection']:.3f} v={n['valence']:+.3f} a={n['arousal']:.3f}\n"
                f"pair-bond: {'on' if s['pair_bond_active'] else 'off'} | "
                f"recoveries(lifetime): {s['suffering_events']} | "
                f"coord: att={s['coordinator_attentions']} act={s['coordinator_actions']}\n"
                f"persistence: save@tick={_ph_light['last_save_tick']} "
                f"boot={'ok' if _ph_light['load_successful_at_boot'] else 'FAILED'}\n"
                f"deep: {s.get('deep_atlas', {}).get('n_entries', 0)} entries "
                f"str={s.get('deep_atlas', {}).get('total_strength', 0)} "
                f"surv={s.get('deep_atlas', {}).get('promotions_survival', 0)} "
                f"ep={s.get('deep_atlas', {}).get('promotions_episodic', 0)} "
                f"reinst={s.get('deep_atlas', {}).get('reinstatements_since_boot', 0)}"
            ),
            "motifs": s["vocab"],
            "vocab": s["vocab"],
            "asleep": _guala.is_asleep,
            "consolidating": _guala.is_consolidating,  # GL-CMD-167 Change 4
            # GL-CMD-GROWTH-LIVE-EVE-20260705-202 G1: the git SHA actually
            # baked into THIS running image (Dockerfile ENV GIT_SHA, from
            # the build-arg the deploy script already passes) -- ends
            # "what's actually deployed" disputes; every window report
            # quotes this field, not a task-def number or a claim.
            "running_sha": os.environ.get("GIT_SHA", "unknown"),
            # GL-CMD-COGNITION-AT-SPEED-EVE-20260705-205 C5: measured
            # rolling tick rate, next to running_sha per the dispatch --
            # her status now answers both "what code" and "how fast."
            "tick_rate": s.get("tick_rate", 0.0),
            "tick_rate_had_pending_work": s.get("tick_rate_had_pending_work", False),
            "persistence_health": _ph_light,
            # GL-CMD-LOCK-CONTENTION-FIX-182 L3: frame backpressure visibility
            "frame_backpressure": {
                "inflight": dict(_frame_inflight),
                "dropped": dict(_frame_dropped),
                "max_inflight": _FRAME_INFLIGHT_MAX,
            },
            # GL-RPT-WINDOW6-DEPLOY-C1B-20260705-v1 item 3 / GL-CMD-FIRE-
            # WINDOW8-EVE-20260705-189: both already computed by
            # introspect() (-179's organism_worker, -185's
            # organism_population) but never forwarded into this
            # curated response dict -- forwarded here, no other change.
            "organism_population": s.get("organism_population", 0),
            "organism_worker": s.get("organism_worker", {}),
            # GL-CMD-GROWTH-LIVE-EVE-20260705-202 G3a: organism_growth
            # (embryo.growth_snapshot(), -198 P3a) was computed in
            # introspect() (gualaloom_v5_engine.py) but never forwarded
            # into THIS curated dict -- the same forgot-to-forward mistake
            # already hit organism_worker/organism_population/curriculum_status/
            # scene_lanes tonight. Fixed here, live-confirmed missing via
            # the new running_sha field proving the correct commit was
            # already running with this gap still present.
            "organism_growth": s.get("organism_growth", {}),
            "atlas_health": s.get("atlas_health", {}),
            "presence": s.get("presence", {}),
            "pair_bond": s.get("pair_bond", {}),
            # GL-CMD-SYNTAX-ARC-20260718: the daily prediction curve and
            # schooling ledgers, surfaced on the LIVE status handler (the
            # runner's /curriculum dispatcher is dead in embedded mode —
            # the same forgot-the-live-path mistake as organism_growth
            # above, caught same-day this time).
            "reading_predictions": _safe_ledger_status(
                "reading_prediction_ledger"),
            "knowledge_gaps": _safe_ledger_status("knowledge_gap_ledger"),
            # GL-CMD-SCENE-LANES-B1-188 V5: THIS is the live /status handler
            # in embedded mode (SUBSTRATE_MODE=embedded, the production
            # config) -- substrate_runner.py's _cmd_status() is a dead,
            # remote-mode-only twin (per GL-HANDOFF-C1B-20260705-v1's
            # lesson: organism_worker/organism_population/curriculum_status
            # all hit this exact mistake tonight). Forwarded HERE, not just
            # in substrate_runner.py, so loomscan's place/ambient panels
            # actually receive real data live.
            "scene_lanes": s.get("scene_lanes", {"place": [], "ambient": []}),
            # v8: deep atlas (GL-BRIEF-032)
            "deep_atlas": s.get("deep_atlas", {}),
            # 042: audio
            # 1.9: ladder metrics
            "ladder": s.get("ladder", {}),
            "n_sounds": s.get("n_sounds", 0),
            "sounds": [{"item_id": snd["item_id"], "title": snd["title"],
                        "times_attended": snd.get("times_attended", 0)}
                       for snd in s.get("sounds", [])[-10:]],
            # v7: autonomy fields
            "current_activity": s.get("current_activity"),
            "activity_history_summary": s.get("activity_history_summary", {}),
            "n_motifs": s.get("n_motifs", 0),
            "n_corpora": len(s.get("corpora", [])),
            "corpora": [{"corpus_id": c["corpus_id"], "title": c["title"]}
                        for c in s.get("corpora", [])[-10:]],
            "sensory_items": len(s.get("sensory_items", [])),
            # Phase 2: visual
            "n_visual_fragments": s.get("n_visual_fragments", 0),
            "n_visual_motifs": s.get("n_visual_motifs", 0),
            # 1.8: refs not dumps — counts + last 10 only (was full motif list)
            "sight_section": {"n_motifs": s.get("n_visual_motifs", 0)},
            "n_pictures": len(s.get("pictures", [])),
            "pictures": [{"item_id": p["item_id"], "title": p["title"],
                          "times_attended": p["times_attended"]}
                         for p in s.get("pictures", [])[-10:]],
            "n_videos": len(s.get("videos", [])),
            # GL-CMD-EPISODIC-MEMORY: computed in introspect() but this
            # handler is a curated forward-list, not a passthrough -- same
            # forgot-to-forward mistake this file's own comments already
            # flag as having hit organism_worker/organism_population/
            # scene_lanes/organism_growth earlier tonight. Forwarded here
            # so it doesn't silently repeat a fourth time.
            "episodic_memory": s.get("episodic_memory", {}),
            "reflections": s.get("reflections", {}),
        }

    # ── /wake — substrate-physical wake event ──
    if cmd == "/wake":
        # Source from text field (e.g. "joe")
        wake_source = msg.text.strip().lower() if msg.text else "joe"
        if wake_source not in {"joe", "wc", "c1"}:
            return {"response": f"wake: unknown source '{wake_source}'", "motifs": 0}
        result = _guala.coordinator.wake(wake_source, _guala, _guala.needs, _guala.atlas)
        # GL-CMD-73: log_event does EFS write blocking async loop 5-31s under load.
        # Coordinator.wake() has already flipped presence; log is diagnostic bookkeeping.
        await _run_lifecycle_executor(
            lambda: _guala.log_event(
                STATE_DIR, "wake", source=wake_source))
        return {"response": json.dumps(result), "motifs": _guala.introspect()["vocab"]}

    # ── /rest — substrate-physical rest event ──
    if cmd == "/rest":
        rest_source = msg.text.strip().lower() if msg.text else "joe"
        result = _guala.coordinator.rest(rest_source, _guala, reason="voluntary")
        # GL-CMD-73: same executor-wrap as /wake
        await _run_lifecycle_executor(
            lambda: _guala.log_event(
                STATE_DIR, "rest", source=rest_source))
        return {"response": json.dumps(result), "motifs": _guala.introspect()["vocab"]}

    # ── /diag — reach distribution + strength histogram for wC ──
    if cmd == "/diag":
        from collections import Counter, defaultdict
        atlas = _guala.atlas
        FTHRESH = 0.02
        # Reach distribution: for each (section, motif), how many chi values does it appear in (alive)?
        motif_reach = Counter()
        for chi_k, entries in atlas.entries.items():
            seen = set()
            for e in entries:
                if e["strength"] >= FTHRESH:
                    key = (e["section"], e["motif"])
                    if key not in seen:
                        motif_reach[key] += 1
                        seen.add(key)
        # Histogram of reach counts
        reach_hist = Counter()
        for key, reach in motif_reach.items():
            reach_hist[reach] += 1
        max_reach_key = motif_reach.most_common(1)[0] if motif_reach else (("?", 0), 0)
        # Look up what word the max-reach mode is
        max_word = "?"
        if motif_reach:
            mk = max_reach_key[0]
            sec = _guala.sections.get(mk[0])
            if sec and mk[1] < len(sec.modes):
                _, _, max_word = sec.modes[mk[1]]
        # Strength histogram (finer buckets: 0.0-0.1, 0.1-0.2, ..., 0.9-1.0)
        strength_hist = {}
        for i in range(10):
            lo = i * 0.1
            hi = (i + 1) * 0.1
            strength_hist[f"{lo:.1f}-{hi:.1f}"] = 0
        for entries in atlas.entries.values():
            for e in entries:
                bucket = min(9, int(e["strength"] * 10))
                lo = bucket * 0.1
                hi = (bucket + 1) * 0.1
                strength_hist[f"{lo:.1f}-{hi:.1f}"] += 1
        return {
            "response": "diagnostic data attached",
            "reach_distribution": dict(sorted(reach_hist.items())),
            "max_reach_mode": {
                "section": max_reach_key[0][0] if motif_reach else "?",
                "motif_id": max_reach_key[0][1] if motif_reach else 0,
                "word": max_word,
                "reach": max_reach_key[1] if motif_reach else 0,
            },
            "strength_histogram_fine": strength_hist,
            "n_live_bindings": atlas.n_live_bindings(),
            "total_strength": round(atlas.total_strength(), 2),
            "n_modes_with_reach": len(motif_reach),
        }

    # ── /sleep — manual sleep trigger from UI ──
    if cmd == "/sleep":
        result = _guala.manual_sleep()
        return {"response": json.dumps(result), "motifs": _guala.introspect()["vocab"]}

    # ── /presence — passive presence heartbeat from UI ──
    if cmd == "/presence":
        source = msg.text.strip().lower() if msg.text.strip() else "joe"
        if source in {"joe", "wc", "c1"}:
            if not _guala.coordinator._presence.get(source, False):
                # First presence → wake
                _guala.coordinator.wake(source, _guala, _guala.needs, _guala.atlas)
                _guala._log_substrate_event("presence_heartbeat",
                                           source=source, action="wake")
            else:
                # Extend timeout by updating last_input_tick
                _guala.coordinator.update_last_input(source, _guala.tick)
        return {"response": "ok", "motifs": _guala.introspect()["vocab"]}

    # ── /events — substrate event stream for UI polling ──
    if cmd == "/events":
        since_tick = 0
        try:
            since_tick = int(msg.text.strip()) if msg.text.strip() else 0
        except ValueError:
            pass
        events = _guala.get_recent_events(since_tick=since_tick, limit=50)
        return {"response": f"{len(events)} events", "motifs": _guala.introspect()["vocab"],
                "events": events}

    # ── /addbook:<filename> — add text as new corpus ──
    if cmd.startswith("/addbook:"):
        filename = cmd[len("/addbook:"):]
        title = filename.replace('.txt', '').replace('_', ' ')
        corpus_id = filename.replace('.txt', '').replace(' ', '_').lower()
        lines = [l.strip() for l in msg.text.splitlines() if l.strip()]
        if not lines:
            return {"response": "empty book", "motifs": _guala.introspect()["vocab"]}
        _guala.add_corpus(corpus_id, title, lines)
        _guala._log_substrate_event("corpus_added",
                                    corpus_id=corpus_id, title=title,
                                    n_lines=len(lines))
        return {"response": f"added \"{title}\" ({len(lines)} lines) to her library",
                "motifs": _guala.introspect()["vocab"]}

    # ── /removebook:<corpus_id> — remove corpus from library ──
    if cmd.startswith("/removebook:"):
        corpus_id = cmd[len("/removebook:"):].strip()
        if corpus_id in _guala._corpora:
            c = _guala._corpora[corpus_id]
            n_lines = len(c.lines)
            del _guala._corpora[corpus_id]
            _guala._log_substrate_event("corpus_removed",
                                        corpus_id=corpus_id, title=c.title,
                                        n_lines=n_lines)
            return {"response": f"removed \"{c.title}\" ({n_lines} lines) from her library",
                    "motifs": _guala.introspect()["vocab"]}
        else:
            available = [c.corpus_id for c in _guala._corpora.values()]
            return {"response": f"corpus '{corpus_id}' not found. available: {available}",
                    "motifs": _guala.introspect()["vocab"]}

    # ── /addpdf:<filename> — extract text from PDF, register as corpus ──
    # C8: entire decode runs in executor (never blocks health checks)
    if cmd.startswith("/addpdf:"):
        import base64
        filename = cmd[len("/addpdf:"):]
        title = filename.replace('.pdf', '').replace('_', ' ')
        corpus_id = filename.replace('.pdf', '').replace(' ', '_').lower()
        b64_data = msg.text.strip()
        if not b64_data:
            return {"response": "no PDF data", "motifs": _guala.introspect()["vocab"]}
        def _decode_pdf():
            t0 = time.time()
            try:
                pdf_bytes = base64.b64decode(b64_data)
                import fitz
                doc = fitz.open(stream=pdf_bytes, filetype="pdf")
                n_pages = len(doc)
                all_text = []
                for page in doc:
                    text = page.get_text()
                    if text.strip():
                        all_text.append(text.strip())
                pdf_dir = os.path.join(STATE_DIR, "books")
                os.makedirs(pdf_dir, exist_ok=True)
                with open(os.path.join(pdf_dir, f"{corpus_id}.pdf"), 'wb') as f:
                    f.write(pdf_bytes)
                feedback = []
                if all_text:
                    full_text = "\n".join(all_text)
                    lines = [l.strip() for l in full_text.split('\n') if l.strip()]
                    split_lines = []
                    for line in lines:
                        if len(line) > 200:
                            for sent in line.replace('. ', '.\n').split('\n'):
                                if sent.strip():
                                    split_lines.append(sent.strip())
                        else:
                            split_lines.append(line)
                    lines = split_lines
                    _guala.add_corpus(corpus_id, title, lines)
                    _guala._log_substrate_event("corpus_added",
                                                corpus_id=corpus_id, title=title,
                                                n_lines=len(lines), source="pdf",
                                                n_pages=n_pages)
                    feedback.append(f"text: {n_pages} pages, {len(lines)} lines → "
                                    f"added to her library")
                n_rasterized = 0
                if not all_text:
                    import hashlib
                    pic_dir = os.path.join(STATE_DIR, "pictures")
                    os.makedirs(pic_dir, exist_ok=True)
                    for i, page in enumerate(doc):
                        pix = page.get_pixmap(dpi=150)
                        img_bytes = pix.tobytes("jpeg")
                        page_id = hashlib.md5(img_bytes).hexdigest()[:12]
                        orig_path = os.path.join(pic_dir, f"{page_id}_original.jpg")
                        with open(orig_path, 'wb') as f:
                            f.write(img_bytes)
                        from PIL import Image
                        import io as _io
                        img = Image.open(_io.BytesIO(img_bytes)).convert('L').resize((64, 64))
                        grid = np.array(img, dtype=np.float32) / 255.0
                        pic = PictureItem(item_id=page_id, title=f"{title}_p{i+1}",
                                          intensity_grid=grid, source="pdf",
                                          shown_at_tick=_guala.tick)
                        pic.original_path = orig_path
                        _guala._pictures[page_id] = pic
                        n_rasterized += 1
                    feedback.append(f"images: {n_rasterized} pages registered as pictures — "
                                    f"no text layer; she'll see them, not read them")
                doc.close()
                if not feedback:
                    feedback.append("empty PDF — nothing to process")
                result = {"response": f"\"{title}\" ({n_pages} pages): " + "; ".join(feedback),
                          "motifs": _guala.introspect()["vocab"]}
            except Exception as e:
                result = {"response": f"PDF decode error: {e}",
                          "motifs": _guala.introspect()["vocab"]}
            print(f"[decode-pdf] {time.time()-t0:.2f}s")
            return result
        return await _run_lifecycle_executor(_decode_pdf)

    # ── /addpicture:<filename> — preserve original, derive krimelack grid ──
    # C8: decode in executor
    if cmd.startswith("/addpicture:"):
        import base64, hashlib
        filename = cmd[len("/addpicture:"):]
        title = filename.rsplit('.', 1)[0] if '.' in filename else filename
        b64_data = msg.text.strip()
        if not b64_data:
            return {"response": "no image data", "motifs": _guala.introspect()["vocab"]}
        def _decode_picture():
            t0 = time.time()
            try:
                img_bytes = base64.b64decode(b64_data)
                img_full, grid, orig_w, orig_h = decode_image_bytes(img_bytes)
                item_id = hashlib.md5(img_bytes).hexdigest()[:12]
                pic_dir = os.path.join(STATE_DIR, "pictures")
                os.makedirs(pic_dir, exist_ok=True)
                ext = filename.rsplit('.', 1)[1] if '.' in filename else 'jpg'
                orig_path = os.path.join(pic_dir, f"{item_id}_original.{ext}")
                with open(orig_path, 'wb') as f:
                    f.write(img_bytes)
                pic = PictureItem(item_id=item_id, title=title,
                                  intensity_grid=grid, source="upload",
                                  shown_at_tick=_guala.tick)
                pic.original_path = orig_path
                pic.original_width = orig_w
                pic.original_height = orig_h
                _guala._pictures[item_id] = pic
                _guala._log_substrate_event("picture_uploaded",
                                            item_id=item_id, title=title,
                                            original_size=f"{orig_w}x{orig_h}")
                result = {"response": f"showed her \"{title}\" ({orig_w}x{orig_h} color, "
                                      f"krimelack 64x64 grayscale). she'll look at it when curiosity drives her.",
                          "motifs": _guala.introspect()["vocab"]}
            except Exception as e:
                result = {"response": f"image decode error: {e}",
                          "motifs": _guala.introspect()["vocab"]}
            print(f"[decode-picture] {time.time()-t0:.2f}s")
            return result
        return await _run_lifecycle_executor(_decode_picture)

    # ── /bundle:<name> — experience bundle: all senses in one window (A4) ──
    # H5b: entire handler wrapped — always returns structured JSON
    # C8: entire bundle decode runs in executor
    if cmd.startswith("/bundle:"):
        import base64
        bundle_name = cmd[len("/bundle:"):]
        try:
            bundle_data = json.loads(msg.text) if msg.text else {}
        except json.JSONDecodeError:
            bundle_data = {"caption": msg.text}
        # GL-CMD-DENSITY-RETIRE-109 F2: bundle attribution truth. Default to
        # "curriculum" — never "joe" — unless the request genuinely names him.
        bundle_source = bundle_data.get("source") or "curriculum"

        def _decode_bundle():
            t0 = time.time()
            results = []
            bundle_chis = []
            # GL-CMD-BINDING-WINDOWS-BUILD-EVE-20260706-v1: give_experience's
            # own explicit open/add_entry-per-lane/close, per design. Opened
            # here (not left to the first lane's implicit auto-open) so an
            # empty-caption bundle (sight/sound/touch only) still gets one
            # shared window across every lane below.
            _bundle_uses_emulator = any(
                bool(bundle_data.get(sense_name))
                for sense_name in ("touch", "smell", "taste"))
            _bundle_has_observed_lane = bool(
                bundle_data.get("image_b64")
                or bundle_data.get("picture_id")
                or bundle_data.get("sound_b64")
                or bundle_data.get("sound_id"))
            _bundle_origin = (
                "observed"
                if _bundle_has_observed_lane and not _bundle_uses_emulator
                else "emulated")
            # GL-RPT-WAL-BLOAT F2 (2026-07-15): the pair below opens AND
            # closes with an EXPLICIT context id, so the close can never
            # silently no-op on contextvar resolution (the failure mode
            # that left contexts open forever, re-embedded into every ~60s
            # save manifest).  Unique per request: a leaked context from a
            # failed bundle can never absorb a later bundle's lanes.
            _bundle_context_id = f"give_experience:{time.time_ns():x}"
            _guala.window_manager.open(
                "give_experience",
                context_id=_bundle_context_id,
                experience_origin=_bundle_origin,
                source=bundle_source,
                bundle_name=bundle_name,
            )
            caption = bundle_data.get("caption", "")
            caption_bound = False
            # ── SIGHT lane (H1: process_viewing, H5a: shared decode) ──
            # Support both base64 upload and reference to existing picture (3.12)
            img_b64 = bundle_data.get("image_b64")
            picture_ref = bundle_data.get("picture_id")
            if not img_b64 and picture_ref and picture_ref in _guala._pictures:
                # 3.12: reference existing picture — re-view it in this window
                pic = _guala._pictures[picture_ref]
                if pic.intensity_grid is not None:
                    try:
                        from dsf_ai_service.visual_krimelack import view_picture as vp
                        frags = vp(pic.intensity_grid, source_id=picture_ref,
                                   born_tick=_guala.tick, seed=_guala.tick % 10000,
                                   n_fixations=6, ticks_per_fixation=100)
                        _guala._visual_fragments_count += len(frags)
                        motif, is_new, overlap = _guala.sight.process_viewing(
                            frags, picture_ref, _guala.tick)
                        if motif:
                            chi = motif.motif_id % 100
                            _guala.window_manager.add_entry(
                                modality="sight", section="sight",
                                motif_id=motif.motif_id, chi=chi,
                                tick=_guala.tick, source_tag=bundle_source,
                                trigger_reason="give_experience",
                                salience=1.5, dwell_ticks=8)
                            bundle_chis.append(chi)
                        results.append(f"showed her \"{pic.title}\" (ref, {len(frags)} fragments)")
                    except Exception as e:
                        results.append(f"image ref ERROR: {e}")
                img_b64 = None  # don't process again below
            if img_b64:
                try:
                    img_bytes = base64.b64decode(img_b64)
                    _, grid, orig_w, orig_h = decode_image_bytes(img_bytes)
                    img_id = _hashlib.md5(img_bytes).hexdigest()[:12]
                    pic = PictureItem(item_id=img_id, title=bundle_name,
                                      intensity_grid=grid, source="bundle",
                                      shown_at_tick=_guala.tick)
                    pic_dir = os.path.join(STATE_DIR, "pictures")
                    os.makedirs(pic_dir, exist_ok=True)
                    orig_path = os.path.join(pic_dir, f"{img_id}_original.jpg")
                    with open(orig_path, 'wb') as f:
                        f.write(img_bytes)
                    pic.original_path = orig_path
                    pic.original_width = orig_w
                    pic.original_height = orig_h
                    _guala._pictures[img_id] = pic
                    # H1: real visual path via process_viewing (not process_fragment)
                    from dsf_ai_service.visual_krimelack import view_picture as vp
                    frags = vp(grid, source_id=img_id,
                               born_tick=_guala.tick, seed=_guala.tick % 10000,
                               n_fixations=6, ticks_per_fixation=100)
                    _guala._visual_fragments_count += len(frags)
                    motif, is_new, overlap = _guala.sight.process_viewing(
                        frags, img_id, _guala.tick)
                    if motif:
                        chi = motif.motif_id % 100
                        _guala.window_manager.add_entry(
                            modality="sight", section="sight",
                            motif_id=motif.motif_id, chi=chi,
                            tick=_guala.tick, source_tag=bundle_source,
                            trigger_reason="give_experience",
                            salience=1.5, dwell_ticks=8)
                        bundle_chis.append(chi)
                    results.append(f"showed her \"{bundle_name}\" "
                                   f"({len(frags)} fragments, {orig_w}x{orig_h})")
                except Exception as e:
                    results.append(f"image ERROR: {e}")

            # ── SOUND lane (H2: size guard on server side) ──
            # Support reference to existing sound (3.12)
            sound_ref = bundle_data.get("sound_id")
            if sound_ref and sound_ref in _guala._sounds and not bundle_data.get("sound_b64"):
                snd = _guala._sounds[sound_ref]
                try:
                    replay = _guala.replay_sound_asset(
                        sound_ref,
                        source=f"give_experience:{bundle_name}:sound_ref")
                    if replay.get("accepted"):
                        results.append(
                            f"played her \"{snd.get('title', sound_ref)}\" "
                            "through auditory L5 (ref)")
                    else:
                        results.append(
                            f"sound ref UNAVAILABLE: {replay.get('reason')}")
                except Exception as error:
                    results.append(f"sound ref ERROR: {error}")

            snd_b64 = bundle_data.get("sound_b64")
            if snd_b64:
                try:
                    import binascii
                    if len(snd_b64) > _LIVE_AUDIO_MAX_B64_CHARS:
                        raise ValueError(
                            "encoded sound exceeds the 4 MiB request boundary")
                    snd_bytes = base64.b64decode(snd_b64, validate=True)
                    if len(snd_bytes) > _LIVE_AUDIO_MAX_BYTES:
                        raise ValueError(
                            "encoded sound exceeds the 4 MiB request boundary")
                    from dsf_ai_service.substrate_runner import _webm_to_wav_bytes
                    wav_bytes = _webm_to_wav_bytes(snd_bytes)
                    if wav_bytes is None:
                        raise ValueError(
                            "sound could not be decoded inside the auditory boundary")
                    snd_id = _hashlib.sha256(snd_bytes).hexdigest()[:16]
                    receipt = _guala.register_replayable_sound(
                        snd_id, bundle_name, wav_bytes,
                        source=f"give_experience:{bundle_name}:sound_upload")
                    results.append(
                        f"played her \"{bundle_name}\" through auditory L5 "
                        f"({receipt['duration_s']:.1f}s)")
                except binascii.Error:
                    results.append("sound ERROR: invalid base64 audio")
                except Exception as e:
                    results.append(f"sound ERROR: {e}")

            # ── TOUCH/SMELL/TASTE lanes (gated: bundle + dream only) ──
            from dsf_ai_service.substrate.sensory_generators import (
                generate_sensory_signals, transduce_sensory_signals)
            for sense_name in ("touch", "smell", "taste"):
                selections = bundle_data.get(sense_name, [])
                if selections:
                    try:
                        signals = generate_sensory_signals(sense_name, selections)
                        channel_results = transduce_sensory_signals(signals)
                        for ch_name, ch_data in channel_results.items():
                            chi = ch_data["chi"]
                            motif = deterministic_motif_id(
                                f"{bundle_name}_{sense_name}_{ch_name}")
                            _guala.window_manager.add_entry(
                                modality=sense_name,
                                section=f"{sense_name}_{ch_name}",
                                motif_id=motif, chi=chi, tick=_guala.tick,
                                source_tag=bundle_source,
                                trigger_reason="give_experience",
                                salience=1.5, dwell_ticks=8)
                            bundle_chis.append(chi)
                        label = {"touch": "feels", "smell": "smells",
                                 "taste": "tastes"}[sense_name]
                        results.append(f"{label} {', '.join(selections)} "
                                       f"({len(channel_results)} channels)")
                    except Exception as e:
                        results.append(f"{sense_name} ERROR: {e}")

            # ── WORD lane ──
            # 2026-07-09 credo fix: moved to AFTER the sight/sound/touch/
            # smell/taste lanes (was first) so that when this caption's
            # word commits (Section.receive -> window_manager.add_entry),
            # _current_window_has_real_grounding() sees whatever real
            # sensory entries this same bundle call already added to the
            # still-open window -- same window, same tick range, same
            # results either way, just reordered so the word actually
            # gets to know what else was really part of this experience.
            if caption:
                try:
                    _guala.read_sentence(caption, source="joe")
                    caption_bound = True
                    from dsf_ai_service.v4.gualaloom_v5_engine import _normalize_text
                    for w in _normalize_text(caption):
                        from dsf_ai_service.v4.gualaloom_v4_krimelack_dna import LanguageKrimelack
                        tk = LanguageKrimelack()
                        tk.transduce(w)
                        bundle_chis.append(tk.winding % 100)
                    results.append(f"told her \"{caption}\"")
                except Exception as e:
                    results.append(f"word ERROR: {e}")

            # ── Bind all lanes in one window ──
            # _open_response_window (below) is the PRE-EXISTING, unrelated
            # response-triggering mechanism (context anchors for emission,
            # see Guala._open_response_window) -- not the binding window
            # this dispatch builds. Left untouched, still fires as before.
            if bundle_chis:
                _guala._open_response_window(bundle_source, bundle_chis,
                                              source_context={"bundle": bundle_name})
            _guala._log_substrate_event("experience_bundle",
                                        name=bundle_name, lanes=results,
                                        n_chis=len(bundle_chis), source=bundle_source)

            # GL-CMD-EPISODIC-MEMORY: bind this real, curated experience to
            # its situation -- when, where, who was present, how she felt,
            # what else was active -- so it becomes a specific remembered
            # moment, not a flat word. Only fires when there's a real
            # concept (caption) to bind to; a bare sensory lane with no
            # word has nothing to remember-as. Deliberately kept separate
            # from the conversational emission/composition path (see this
            # function's own note above on the standing "one mind, one
            # mouth" ruling) -- this records real memory; whether/how it
            # feeds what she says is a separate decision, not made here.
            if caption:
                _guala._record_episodic_experience(caption, source=bundle_source)

            # GL-CMD-BINDING-WINDOWS-BUILD-EVE-20260706-v1: close the
            # binding window opened at the top of this function -- give_
            # experience's explicit open/add_entry-per-lane/close, complete.
            _closed_bundle_window = _guala.window_manager.close(
                "give_experience_complete", context_id=_bundle_context_id)
            if caption_bound:
                if _closed_bundle_window is None:
                    raise RuntimeError(
                        "give_experience BindingWindow did not close")

            # H5b: always structured JSON, never raw 500
            print(f"[decode-bundle] {time.time()-t0:.2f}s")
            response_payload = {
                "response": f"experience \"{bundle_name}\": {'; '.join(results)}. "
                            f"{len(bundle_chis)} cross-modal bindings.",
                "motifs": _guala.introspect()["vocab"],
                "bundle": {"name": bundle_name, "lanes": results,
                           "n_chis": len(bundle_chis)},
            }
            return response_payload
        return await _run_lifecycle_executor(_decode_bundle)

    # ── /addsound:<filename> — one bounded full-field auditory capture ──
    # C8: entire decode in executor
    if cmd.startswith("/addsound:"):
        import base64
        import binascii
        import hashlib

        filename = cmd[len("/addsound:"):]
        title = filename.rsplit('.', 1)[0] if '.' in filename else filename
        b64_data = msg.text.strip()
        if not b64_data:
            return {"response": "no audio data", "motifs": _guala.introspect()["vocab"]}
        def _decode_sound():
            t0 = time.time()
            try:
                if len(b64_data) > _LIVE_AUDIO_MAX_B64_CHARS:
                    raise ValueError("encoded sound exceeds the 4 MiB request boundary")
                audio_bytes = base64.b64decode(b64_data, validate=True)
                if len(audio_bytes) > _LIVE_AUDIO_MAX_BYTES:
                    raise ValueError("encoded sound exceeds the 4 MiB request boundary")
                from dsf_ai_service.substrate_runner import _webm_to_wav_bytes
                wav_bytes = _webm_to_wav_bytes(audio_bytes)
                if wav_bytes is None:
                    raise ValueError(
                        "sound could not be decoded inside the auditory boundary")
                item_id = hashlib.sha256(audio_bytes).hexdigest()[:16]
                receipt = _guala.register_replayable_sound(
                    item_id, title, wav_bytes,
                    source=f"sound_upload:{item_id}")
                result = {
                    "response": (
                        f"heard \"{title}\" through the full auditory field "
                        f"({receipt['duration_s']:.1f}s)"),
                    "motifs": _guala.introspect()["vocab"],
                    "sound_info": {
                        "item_id": item_id, "title": title,
                        "duration_s": round(receipt["duration_s"], 2),
                        "causal_entries": receipt["causal_receipt"].get(
                            "entries_bound", 0),
                        "replay_pcm_bytes": receipt["replay_pcm_bytes"],
                        "auditory_boundary": "full_field_l5",
                    },
                }
            except (ValueError, TypeError, binascii.Error) as e:
                result = {"response": f"sound decode error: {e}",
                          "motifs": _guala.introspect()["vocab"]}
            except Exception as e:
                result = {"response": f"sound processing error: {e}",
                          "motifs": _guala.introspect()["vocab"]}
            print(f"[decode-sound] {time.time()-t0:.2f}s")
            return result
        return await _run_lifecycle_executor(_decode_sound)

    # The retired organism query accepted a flattened 200 Hz waveform.  The
    # full auditory field cannot enter that interface without destroying its
    # channel topology, phase, and causal timing, so report the missing direct
    # mechanism instead of presenting the old reduction as auditory recall.
    if cmd.startswith("/organism_recall_auditory:"):
        sound_item_id = cmd[len("/organism_recall_auditory:"):]
        snd = _guala._sounds.get(sound_item_id)
        if snd is None:
            return {"response": f"no such sound item: {sound_item_id}",
                    "organism_recall_auditory": None}
        return {
            "response": (
                "auditory recall through the flattened organism signal is retired; "
                "a full-field auditory recall mechanism is not yet present"),
            "organism_recall_auditory": None,
            "reason": "full_field_auditory_recall_mechanism_missing",
        }

    # ── Normal conversation — now handled by 202 + task poll path above ──
    # This branch is only reached for text messages if _is_converse was False
    # (for example, empty text with no command). Empty input is neutral silence.
    if not (msg.text or "").strip():
        return {"response": "", "response_source": "silence_empty_input",
                "motifs": _guala.introspect()["vocab"] if _guala else 0}

    # Fallback for any command not explicitly handled above, with non-empty
    # text. GL-CMD-VOICE-TO-WORDS-153 Part C: /listen no longer relies on
    # this — it has its own intentional route above. This remains the
    # genuine catch-all for unrecognized commands.
    import asyncio as _aio
    _prune_stale_tasks()
    tick = _guala.tick if _guala else 0
    task_id = f"cv_{tick}_{uuid4().hex[:8]}_fb"
    source = msg.source if msg.source in {"joe", "wc", "c1"} else "joe"
    _converse_tasks[task_id] = {
        "task_id": task_id, "status": "queued", "phase": None,
        "response": None, "response_source": None, "motifs": 0,
        "started_tick": tick, "started_at": time.time(), "source": source,
    }
    _schedule_mutating_background(
        lambda: _run_converse(
            task_id, msg.text or "", source, msg.emission_mode),
        name=f"converse-{task_id}",
    )
    return JSONResponse(status_code=202, content={
        "task_id": task_id, "status": "accepted",
        "poll_url": f"/api/v1/gualaloom/task/{task_id}",
        "started_tick": tick, "retry_after_ms": 500,
    })


# GL-CMD-CONVERSE-TASK-PATTERN-62: poll endpoint for converse tasks
@app.get("/api/v1/gualaloom/task/{task_id}")
async def get_converse_task(task_id: str):
    """Poll for converse task result. Returns progress (200) or complete (200) or not_found (404)."""
    task = _converse_tasks.get(task_id)
    if task is None:
        # GL-CMD-LOCK-CONTENTION-FIX-182 L2: _converse_tasks is in-memory
        # only, so a task id from before a deploy's process restart looks
        # identical to one that just aged out past the TTL -- we can't
        # tell them apart without persistence, so say so honestly instead
        # of implying it definitely expired normally.
        return JSONResponse(status_code=404, content={
            "task_id": task_id,
            "status": "not_found",
            "error": ("task not found on this server instance — either it "
                      "expired (TTL: 5 min after completion) or it was in "
                      "flight during a deploy and was lost in the restart. "
                      "Please resend your message."),
        })
    if task["status"] == "complete":
        return JSONResponse(status_code=200, content={
            "task_id": task_id,
            "status": "complete",
            "response": task["response"],
            "response_source": task["response_source"],
            "motifs": task.get("motifs", 0),
            # GL-CMD-ENABLE-COGNITION-EVE-20260705-211 / Joe 2026-07-06: was
            # missing entirely, so no polled reply ever carried a real
            # emission_id to the frontend -- see _run_converse's own note.
            "emission_id": task.get("emission_id"),
            "committed_sections": task.get("committed_sections", []),
            "pictures": task.get("pictures", []),
            "source_turn_index": task.get("source_turn_index"),
            "speech_audio": task.get("speech_audio"),
            "speech_output_status": task.get("speech_output_status"),
            "started_tick": task["started_tick"],
            "completed_tick": task.get("completed_tick"),
            "elapsed_ms": int((task.get("completed_at", time.time()) - task["started_at"]) * 1000),
        })
    if task["status"] == "error":
        return JSONResponse(status_code=200, content={
            "task_id": task_id,
            "status": "error",
            "error": task.get("error", "unknown error"),
        })
    return JSONResponse(status_code=200, content={
        "task_id": task_id,
        "status": task["status"],
        "phase": task.get("phase"),
        "started_tick": task["started_tick"],
        "current_tick": _guala.tick if _guala else 0,
        "elapsed_ms": int((time.time() - task["started_at"]) * 1000),
        "retry_after_ms": 500,
    })


# C2: serve individual pictures by ID (refs-not-base64)
@app.get("/api/v1/gualaloom/picture/{item_id}")
async def gualaloom_picture(item_id: str):
    """Return a single picture as binary image response."""
    _gl_init()
    if _guala is None:
        return JSONResponse({"error": "not ready"}, status_code=503)
    pic = _guala._pictures.get(item_id)
    if pic is None:
        return JSONResponse({"error": "not found"}, status_code=404)
    orig_path = getattr(pic, 'original_path', None)
    if orig_path and os.path.exists(orig_path):
        ext = orig_path.rsplit('.', 1)[1].lower() if '.' in orig_path else 'png'
        mime = {'jpg': 'image/jpeg', 'jpeg': 'image/jpeg', 'png': 'image/png',
                'gif': 'image/gif', 'webp': 'image/webp', 'heic': 'image/heic'}.get(ext, 'image/png')
        with open(orig_path, 'rb') as f:
            data = f.read()
        return Response(content=data, media_type=mime)
    elif pic.intensity_grid is not None:
        from PIL import Image
        import io as _io
        img = Image.fromarray((pic.intensity_grid * 255).astype(np.uint8), mode='L')
        buf = _io.BytesIO()
        img.save(buf, format='PNG')
        return Response(content=buf.getvalue(), media_type="image/png")
    return JSONResponse({"error": "no image data"}, status_code=404)


# ════════════════════════════════════════════════════════════════
# UNPAUSE admin endpoints (GL-BRIEF-UNPAUSE-WC-20260613-01)
# ════════════════════════════════════════════════════════════════

# Runtime repause flag (survives within the process; env var alone isn't enough)
_runtime_decay_paused = None  # None = defer to env var

@app.post("/api/v1/gualaloom/admin/amnesty", dependencies=[Depends(_api_key_dep)])
async def admin_amnesty():
    """Step 1: Reset last_tick on all atlas entries to current tick. Zero strength changes."""
    if _is_remote():
        client = _get_substrate_client()
        return await client.call("amnesty")
    _gl_init()
    if _guala is None:
        return JSONResponse({"error": "not ready"}, status_code=503)
    tick = _guala.tick
    total_strength_before = round(_guala.atlas.total_strength(), 4)
    count = _guala.atlas.amnesty(tick)
    total_strength_after = round(_guala.atlas.total_strength(), 4)
    _guala._log_substrate_event("amnesty_complete", entries_restamped=count,
                                 tick=tick, strength_before=total_strength_before,
                                 strength_after=total_strength_after)
    print(f"[UNPAUSE] Amnesty: {count} entries re-stamped to tick {tick}, "
          f"strength {total_strength_before} → {total_strength_after}")
    return {"amnesty": "complete", "entries_restamped": count, "tick": tick,
            "total_strength_before": total_strength_before,
            "total_strength_after": total_strength_after}


@app.post("/api/v1/gualaloom/admin/force_dream", dependencies=[Depends(_api_key_dep)])
async def admin_force_dream():
    """Step 2: Force a sleep→dream cycle. Returns dream artifact."""
    if _is_remote():
        client = _get_substrate_client()
        return await client.call("force_dream", timeout=90.0)
    _gl_init()
    if _guala is None:
        return JSONResponse({"error": "not ready"}, status_code=503)
    # Fix B: dream cycle takes 60-120s; API GW has 30s timeout.
    # Return 202 immediately, run dream in background. Poll /status for activity change.
    import asyncio as _aio
    start_tick = _guala.tick
    _guala._force_next_activity = ("SLEEPING", None)
    if _guala._current_activity:
        _guala._end_activity()
    _guala._log_substrate_event("force_dream_initiated", tick=start_tick)
    print(f"[UNPAUSE] Force dream initiated at tick {start_tick}")

    async def _bg_dream():
        for _ in range(240):  # 240 × 0.5s = 120s
            await _aio.sleep(0.5)
            activity = _guala._current_activity
            if activity and activity.kind == "DREAMING":
                continue
            if activity is None or (activity.kind not in ("SLEEPING", "DREAMING")):
                print(f"[UNPAUSE] Dream cycle complete at tick {_guala.tick}")
                return
        print(f"[UNPAUSE] Dream cycle timeout at tick {_guala.tick}")
    _schedule_mutating_background(
        lambda: _bg_dream(), name="admin-force-dream")
    return JSONResponse(
        status_code=202,
        content={"force_dream": "accepted", "start_tick": start_tick,
                 "message": "Dream cycle initiated. Poll /status current_activity for completion."},
    )


@app.post("/api/v1/gualaloom/admin/force_reading", dependencies=[Depends(_api_key_dep)])
async def admin_force_reading(request: Request):
    """GL-CMD-SCENE-LANES-B1-188 follow-up: force a specific corpus into
    READING right now instead of waiting on natural rotation (c1b's
    handoff -- Secret Garden was uploaded but has never actually been
    read). Mirrors admin_force_dream's _force_next_activity pre-emption
    exactly -- same existing override, no new mechanism. Body:
    {"corpus_id": "..."} (exact) or {"title_contains": "secret garden"}
    (substring, case-insensitive); corpus_id wins if both given."""
    try:
        body = await request.json()
    except Exception:
        body = {}
    corpus_id = (body.get("corpus_id") or "").strip()
    title_contains = (body.get("title_contains") or "").strip()
    if _is_remote():
        client = _get_substrate_client()
        return await client.call("force_reading", corpus_id=corpus_id,
                                 title_contains=title_contains, timeout=15.0)
    _gl_init()
    if _guala is None:
        return JSONResponse({"error": "not ready"}, status_code=503)
    target = None
    if corpus_id and corpus_id in _guala._corpora:
        target = corpus_id
    elif title_contains:
        tl = title_contains.lower()
        for cid, c in _guala._corpora.items():
            if tl in c.title.lower():
                target = cid
                break
    if target is None:
        return JSONResponse(
            {"error": "no matching corpus", "corpus_id": corpus_id,
             "title_contains": title_contains,
             "available": [{"corpus_id": cid, "title": c.title}
                          for cid, c in _guala._corpora.items()]},
            status_code=404)
    start_tick = _guala.tick
    _guala._force_next_activity = ("READING", target)
    if _guala._current_activity:
        _guala._end_activity()
    _guala._log_substrate_event("force_reading_initiated", tick=start_tick,
                                corpus_id=target)
    print(f"[UNPAUSE] Force reading initiated: corpus_id={target} at tick {start_tick}")
    return {"force_reading": "accepted", "corpus_id": target,
            "title": _guala._corpora[target].title, "start_tick": start_tick,
            "message": "Reading initiated. Poll /status current_activity for progress."}


@app.post("/api/v1/gualaloom/admin/repause", dependencies=[Depends(_api_key_dep)])
async def admin_repause():
    """Kill switch: re-pause decay immediately."""
    if _is_remote():
        client = _get_substrate_client()
        return await client.call("repause")
    global _runtime_decay_paused
    os.environ["DECAY_PAUSED"] = "1"
    _runtime_decay_paused = True
    if _guala:
        _guala._log_substrate_event("decay_repaused", tick=_guala.tick,
                                     reason="manual_kill_switch")
    print(f"[UNPAUSE] KILL SWITCH: decay re-paused")
    return {"repause": "active", "DECAY_PAUSED": "1"}


@app.post("/api/v1/gualaloom/admin/unpause", dependencies=[Depends(_api_key_dep)])
async def admin_unpause():
    """Unpause decay — durable transaction via substrate config file."""
    if _is_remote():
        client = _get_substrate_client()
        return await client.call("unpause")
    # Embedded mode fallback
    global _runtime_decay_paused
    os.environ["DECAY_PAUSED"] = "0"
    _runtime_decay_paused = False
    if _guala:
        _guala._log_substrate_event("decay_unpaused", tick=_guala.tick,
                                     reason="admin_unpause")
    print(f"[UNPAUSE] Decay unpaused")
    return {"unpaused": True, "tick": _guala.tick if _guala else 0}


@app.get("/api/v1/gualaloom/admin/atlas_snapshot", dependencies=[Depends(_api_key_dep)])
async def admin_atlas_snapshot():
    """Monitor: live atlas stats for unpause monitoring."""
    if _is_remote():
        client = _get_substrate_client()
        return await client.call("atlas_snapshot")
    _gl_init()
    if _guala is None:
        return JSONResponse({"error": "not ready"}, status_code=503)
    dist = _guala.atlas.strength_distribution()
    return {
        "tick": _guala.tick,
        "total_strength": round(_guala.atlas.total_strength(), 2),
        "n_live_bindings": _guala.atlas.n_live_bindings(),
        "n_total_entries": sum(len(v) for v in _guala.atlas.entries.values()),
        "strength_distribution": dist,
        "decay_paused": os.environ.get("DECAY_PAUSED", "0"),
        "decay_lambda_override": os.environ.get("DECAY_LAMBDA_OVERRIDE", ""),
        "slow_div_override": os.environ.get("SLOW_DIV_OVERRIDE", ""),
    }


@app.get("/api/v1/gualaloom/admin/familiarity_debug", dependencies=[Depends(_api_key_dep)])
async def admin_familiarity_debug():
    """GL-CMD-FLOOD-HUNT-156: owed diagnostic from -107's unresolved
    target_familiarity persistence gap. Dumps self.target_familiarity
    directly, no serialization round-trip, plus its object id() — so two
    calls across a save boundary can show whether the dict is ever a
    different object (silent rebind) vs. the same object losing entries."""
    if _is_remote():
        client = _get_substrate_client()
        return await client.call("familiarity_debug")
    _gl_init()
    if _guala is None:
        return JSONResponse({"error": "not ready"}, status_code=503)
    return {
        "tick": _guala.tick,
        "target_familiarity": dict(_guala.target_familiarity),
        "n_keys": len(_guala.target_familiarity),
        "dict_id": id(_guala.target_familiarity),
        "last_save_tick": getattr(_guala, "_last_save_tick", None),
        "last_save_timestamp": getattr(_guala, "_last_save_timestamp", None),
    }


# (A) Step-0 atlas backup with verification
@app.post("/api/v1/gualaloom/admin/backup", dependencies=[Depends(_api_key_dep)])
async def admin_backup():
    """Step 0: Full state backup to dedicated UNPAUSE-PRE S3 prefix. Verified."""
    if _REQUIRE_SEALED_STATE:
        raise HTTPException(
            status_code=409,
            detail=("partial legacy backup is disabled; use the authenticated "
                    "immutable generation seal"),
        )
    if _is_remote():
        # GL-CMD-104: API Gateway has 30s timeout. force_save takes 10-25s.
        # Fire-and-forget: kick off backup in background, return 202 immediately.
        # Caller polls /status for last_s3_backup to confirm completion.
        import asyncio as _aio
        async def _do_remote_backup():
            try:
                client = _get_substrate_client()
                await client.call("backup", timeout=55.0)
            except Exception as e:
                print(f"[backup] remote backup error: {e}")
        _schedule_mutating_background(
            lambda: _do_remote_backup(), name="admin-remote-backup")
        return JSONResponse(
            status_code=202,
            content={"backup": "accepted", "message": "EFS+S3 backup started. Poll /status for last_s3_backup."},
        )
    _gl_init()
    if _guala is None:
        return JSONResponse({"error": "not ready"}, status_code=503)
    # Fix B: embedded mode uses same 202+background pattern as remote mode.
    # save_full_state + S3 upload takes 30-120s; API GW has 30s timeout.
    # Fire-and-forget: return 202 immediately, backup runs in background thread.
    import boto3 as _boto3
    def _do_backup():
        t0 = time.time()
        s3 = _boto3.client("s3", region_name="us-east-1")
        bucket = "dsf-ai-site-backups"
        ts = time.strftime("%Y%m%d-%H%M%S", time.gmtime())
        prefix = f"guala/UNPAUSE-PRE-{ts}/"
        # Save state to EFS first (fresh)
        _guala.save_full_state(STATE_DIR)
        # Upload all 11 state files
        state_files = ["guala_core.json", "guala_needs.json", "guala_coordinator.json",
                       "guala_atlas.json", "guala_sections.json", "guala_bucket.json",
                       "guala_deep_atlas.json", "guala_visual.json", "guala_identity.json",
                       "guala_sounds.json", "guala_videos.json"]
        uploaded = 0
        for f in state_files:
            path = os.path.join(STATE_DIR, f)
            if os.path.exists(path):
                s3.upload_file(path, bucket, prefix + f)
                uploaded += 1
        # Also backup pictures
        pic_dir = os.path.join(STATE_DIR, "pictures")
        if os.path.isdir(pic_dir):
            for pf in os.listdir(pic_dir):
                s3.upload_file(os.path.join(pic_dir, pf), bucket, prefix + "pictures/" + pf)
        # VERIFY: re-fetch atlas and check entry count
        import tempfile
        verify_path = tempfile.mktemp(suffix=".json")
        try:
            s3.download_file(bucket, prefix + "guala_atlas.json", verify_path)
            import json as _json
            with open(verify_path) as fh:
                atlas_data = _json.load(fh)
            inner = atlas_data.get("data", atlas_data)
            entries_dict = inner.get("entries", inner)
            backup_entries = sum(len(v) for v in entries_dict.values()
                                if isinstance(v, list))
            live_entries = sum(len(v) for v in _guala.atlas.entries.values())
            os.unlink(verify_path)
            if backup_entries != live_entries:
                return {"error": f"verification failed: backup has {backup_entries} entries, "
                                 f"live has {live_entries}", "s3_prefix": prefix}
        except Exception as e:
            return {"error": f"verification failed: {e}", "s3_prefix": prefix}
        dt = time.time() - t0
        print(f"[UNPAUSE] Backup verified: {uploaded} files to {prefix} in {dt:.1f}s, "
              f"{live_entries} entries confirmed")
        return {"backup": "verified", "s3_prefix": prefix, "files_uploaded": uploaded,
                "n_entries_verified": live_entries, "duration_s": round(dt, 1)}
    # Launch backup in background thread, return 202 immediately.
    # Caller polls /status for last_s3_backup to confirm completion.
    async def _bg_backup():
        try:
            await _run_lifecycle_executor(_do_backup)
        except Exception as e:
            print(f"[backup] embedded backup error: {e}")
    _schedule_mutating_background(
        lambda: _bg_backup(), name="admin-embedded-backup")
    return JSONResponse(
        status_code=202,
        content={"backup": "accepted", "message": "EFS+S3 backup started. Poll /status for last_s3_backup."},
    )


@app.post("/api/v1/gualaloom/admin/backfill_picture_titles", dependencies=[Depends(_api_key_dep)])
async def admin_backfill_picture_titles():
    """GL-CMD-PICTURE-TITLE-BIND Part 2: one-shot backfill of all existing picture
    titles into language substrate, bundled to item:pic:<id>. Idempotent."""
    if _is_remote():
        client = _get_substrate_client()
        return await client.call("backfill_picture_titles", timeout=60.0)
    _gl_init()
    if _guala is None:
        return JSONResponse({"error": "not ready"}, status_code=503)
    fed, skipped = 0, 0
    max_strength_seen = 0.0
    for pic_id, pic in list(_guala._pictures.items()):
        title = (getattr(pic, "title", None) or "").strip()
        if not title:
            skipped += 1
            continue
        _guala.read_sentence(title, source="addpicture_backfill",
                             bundle_id=f"item:pic:{pic_id}", salience=1.5)
        fed += 1
    return {"fed": fed, "skipped": skipped, "total_pictures": len(_guala._pictures)}


@app.post("/api/v1/gualaloom/admin/backfill_sound_captions", dependencies=[Depends(_api_key_dep)])
async def admin_backfill_sound_captions():
    """GL-CMD-PICTURE-TITLE-BIND Part 3: one-shot backfill of all existing sound
    titles into language substrate, bundled to item:snd:<id>. Idempotent."""
    if _is_remote():
        client = _get_substrate_client()
        return await client.call("backfill_sound_captions", timeout=60.0)
    _gl_init()
    if _guala is None:
        return JSONResponse({"error": "not ready"}, status_code=503)
    fed, skipped = 0, 0
    for snd_id, snd in list(_guala._sounds.items()):
        caption = (snd.get("title") or "").strip()
        if not caption:
            skipped += 1
            continue
        _guala.read_sentence(caption, source="addsound_backfill",
                             bundle_id=f"item:snd:{snd_id}", salience=1.5)
        fed += 1
    return {"fed": fed, "skipped": skipped, "total_sounds": len(_guala._sounds)}


# (B.1) Atlas surgery — GL-CMD-ATLAS-SURGERY-EVE-20260627-18
class AtlasSurgeryRequest(BaseModel):
    operation_id: str
    dry_run: bool = False
    allow_overwrite: bool = False
    high_strength_acknowledged: bool = False
    bindings: list = []

@app.post("/api/v1/gualaloom/admin/atlas_surgery", dependencies=[Depends(_api_key_dep)])
async def admin_atlas_surgery(req: AtlasSurgeryRequest):
    """B.1: Validated direct-write surface for atlas seeding (Phase G/I seeds use this)."""
    if _is_remote():
        client = _get_substrate_client()
        try:
            return await client.call("atlas_surgery", timeout=300.0,  # Path 3 sync backup ~170s
                                     operation_id=req.operation_id,
                                     dry_run=req.dry_run,
                                     allow_overwrite=req.allow_overwrite,
                                     high_strength_acknowledged=req.high_strength_acknowledged,
                                     bindings=req.bindings)
        except Exception as e:
            return JSONResponse({"error": str(e), "writes": {"n_written": 0}}, status_code=503)
    return JSONResponse({"error": "not in remote mode"}, status_code=503)


# (B.2) Backup orchestrator — GL-CMD-BACKUP-ORCHESTRATOR-EVE-20260627-19
@app.post("/api/v1/gualaloom/admin/backup_orchestrator/configure",
          dependencies=[Depends(_api_key_dep)])
async def admin_backup_orchestrator_configure(body: dict = None):
    """B.2: Configure orchestrator trigger enables/disables."""
    if _is_remote():
        client = _get_substrate_client()
        try:
            return await client.call("backup_orchestrator_configure",
                                     timeout=10.0, **(body or {}))
        except Exception as e:
            return JSONResponse({"error": str(e)}, status_code=503)
    return JSONResponse({"error": "not in remote mode"}, status_code=503)

@app.get("/api/v1/gualaloom/admin/backup_orchestrator/status",
         dependencies=[Depends(_api_key_dep)])
async def admin_backup_orchestrator_status():
    """B.2: Recent backup history and current config."""
    if _is_remote():
        client = _get_substrate_client()
        try:
            return await client.call("backup_orchestrator_status", timeout=10.0)
        except Exception as e:
            return JSONResponse({"error": str(e)}, status_code=503)
    return JSONResponse({"error": "not in remote mode"}, status_code=503)


# (B) Cascade auto-trigger monitor
class CascadeMonitorRequest(BaseModel):
    baseline_n_bindings: int
    baseline_strength: float
    baseline_saturated: int = 0
    interval_s: int = 10

@app.post("/api/v1/gualaloom/admin/start_cascade_monitor", dependencies=[Depends(_api_key_dep)])
async def admin_start_cascade_monitor(req: CascadeMonitorRequest):
    """Start cascade detection — forwarded to substrate process."""
    if _is_remote():
        client = _get_substrate_client()
        return await client.call("start_cascade_monitor",
            baseline_n_bindings=req.baseline_n_bindings,
            baseline_strength=req.baseline_strength,
            baseline_saturated=req.baseline_saturated,
            interval_s=req.interval_s,
        )
    return JSONResponse({"error": "cascade monitor requires remote substrate mode"},
                        status_code=501)


@app.post("/api/v1/gualaloom/admin/stop_cascade_monitor", dependencies=[Depends(_api_key_dep)])
async def admin_stop_cascade_monitor():
    """Stop cascade monitor — forwarded to substrate process."""
    if _is_remote():
        client = _get_substrate_client()
        return await client.call("stop_cascade_monitor")
    return JSONResponse({"error": "cascade monitor requires remote substrate mode"},
                        status_code=501)


@app.post("/api/v1/gualaloom/admin/restore_from_s3_prefix", dependencies=[Depends(_api_key_dep)])
async def admin_restore_from_s3_prefix(request: Request):
    """Restore state files from a specific S3 backup prefix.
    Body: {"prefix": "auto/2026-06-29_23-58-17_activity_ended/"}
    Downloads all files (including pictures/) to STATE_DIR.
    Requires substrate restart to load restored state.
    """
    if _REQUIRE_SEALED_STATE:
        raise HTTPException(
            status_code=409,
            detail=("legacy mutable-root restore is disabled; restore a fully "
                    "verified immutable generation while no owner is running"),
        )
    body = await request.json()
    prefix = body.get("prefix", "").strip("/") + "/"
    if not prefix or prefix == "/":
        raise HTTPException(400, "prefix required")
    import boto3
    def _do_restore():
        s3 = boto3.client("s3", region_name="us-east-1")
        bucket = "dsf-ai-site-backups"
        full_prefix = f"guala/{prefix}"
        paginator = s3.get_paginator("list_objects_v2")
        pages = paginator.paginate(Bucket=bucket, Prefix=full_prefix)
        files_restored = []
        for page in pages:
            for obj in page.get("Contents", []):
                key = obj["Key"]
                rel = key[len(full_prefix):]
                if not rel:
                    continue
                local_path = os.path.join(STATE_DIR, rel)
                os.makedirs(os.path.dirname(local_path), exist_ok=True)
                s3.download_file(bucket, key, local_path)
                files_restored.append(rel)
        return files_restored
    restored = await _run_lifecycle_executor(_do_restore)
    return {"restored": len(restored), "files": restored,
            "note": "restart substrate to load restored state"}


@app.post("/api/v1/gualaloom/admin/compact_wave_atlas", dependencies=[Depends(_api_key_dep)])
async def admin_compact_wave_atlas():
    """GL-CMD-WAVE-DIET-82: one-time WaveAtlas compaction.

    Drops every WaveAtlas binding with no live LivingAtlas counterpart.
    Join key: (section, motif, chi_original). Cell phase_vecs preserved for
    cells retaining >=1 live binding. No restart needed — runs in-place.
    """
    if _guala is None or _guala.wave_atlas is None:
        raise HTTPException(503, "substrate not ready")
    def _do_compact():
        wa = _guala.wave_atlas
        atlas = _guala.atlas
        # Build live key set from LivingAtlas
        live_keys = set()
        for chi_k, entries in atlas.entries.items():
            for e in entries:
                live_keys.add((e["section"], e["motif"], e.get("chi", chi_k)))
        before = sum(len(c.bindings) for c in wa.cells.values())
        before_cells = len(wa.cells)
        for cell in wa.cells.values():
            orig = len(cell.bindings)
            cell.bindings = [
                b for b in cell.bindings
                if (b.get("section"), b.get("motif"), b.get("chi")) in live_keys
            ]
            if len(cell.bindings) != orig:
                cell.aggregate_strength = sum(
                    float(b.get("strength", 0.05)) for b in cell.bindings)
            cell.saturated = cell.aggregate_strength > 5.0
        # Remove empty cells
        empty = [k for k, c in wa.cells.items() if not c.bindings]
        for k in empty:
            del wa.cells[k]
        after = sum(len(c.bindings) for c in wa.cells.values())
        after_cells = len(wa.cells)
        print(f"[GualaLoom] WaveAtlas compacted: {before}→{after} bindings, "
              f"{before_cells}→{after_cells} cells")
        return {"before_bindings": before, "after_bindings": after,
                "removed": before - after,
                "before_cells": before_cells, "after_cells": after_cells,
                "live_keys_in_atlas": len(live_keys)}
    result = await _run_lifecycle_executor(_do_compact)
    return result


@app.post("/api/v1/gualaloom/admin/migrate_wave_atlas", dependencies=[Depends(_api_key_dep)])
async def admin_migrate_wave_atlas():
    """GL-CMD-WAVE-SEMANTICS-85 Part B.3: one-time WaveAtlas migration.

    1. Snapshot raw state to S3 (compressed, pre-migration backup).
    2. Collapse by (chi, section, motif) in-memory — sums duplicate strengths.
    3. Save collapsed atlas to wave_atlas.npz on EFS.
    Returns binding counts before/after and S3 snapshot key.
    """
    if _guala is None or _guala.wave_atlas is None:
        raise HTTPException(503, "substrate not ready")
    import boto3 as _boto3, gzip as _gzip, json as _json, io as _io

    def _do_migrate():
        wa = _guala.wave_atlas
        before_b = wa.binding_count()
        before_c = wa.cell_count()

        # Step 1: S3 raw snapshot (pre-migration)
        try:
            s3 = _boto3.client("s3", region_name="us-east-1")
            raw = _json.dumps(wa.to_dict()).encode("utf-8")
            compressed = _gzip.compress(raw, compresslevel=6)
            ts = time.strftime("%Y-%m-%d_%H-%M-%S", time.gmtime())
            snap_key = f"guala/wave_migrate_pre/{ts}_wave_atlas_raw.json.gz"
            s3.put_object(
                Bucket="dsf-ai-site-backups",
                Key=snap_key,
                Body=compressed,
                ContentType="application/gzip",
            )
            snap_uri = f"s3://dsf-ai-site-backups/{snap_key}"
            print(f"[85-B3] Pre-migration snapshot: {snap_uri} ({len(compressed)/1e6:.1f}MB)")
        except Exception as _se:
            raise RuntimeError(
                f"WaveAtlas migration refused because its pre-state snapshot failed: {_se}"
            ) from _se

        # Step 2: collapse by (chi, section, motif)
        collapse_result = wa.collapse_by_key()
        after_b = collapse_result["after"]
        after_c = collapse_result["cells"]
        print(f"[85-B3] Collapse: {before_b}→{after_b} bindings, {before_c}→{after_c} cells")

        # Step 3: save collapsed atlas to npz
        _guala._save_wave_atlas(STATE_DIR)

        return {
            "before_bindings": before_b,
            "after_bindings": after_b,
            "removed": before_b - after_b,
            "before_cells": before_c,
            "after_cells": after_c,
            "s3_snapshot": snap_uri,
        }

    result = await _run_lifecycle_executor(_do_migrate)
    return result


@app.get("/api/v1/gualaloom/admin/persistence_health", dependencies=[Depends(_api_key_dep)])
async def admin_persistence_health():
    """Full EFS-based persistence health. Uses executor so EFS stat() doesn't block
    the event loop. May take 5-30s under NFS latency — poll infrequently.
    For lightweight save-tick summary, read persistence_health from /status instead."""
    if _guala is None:
        raise HTTPException(status_code=503, detail="substrate loading")
    import asyncio as _aio
    loop = _aio.get_event_loop()
    result = await loop.run_in_executor(
        None, lambda: _guala.persistence_health(STATE_DIR))
    result["last_s3_backup"] = _last_s3_backup
    return result


# GL-BRIEF-CHITRACE: read-only chi-geometry readout
class ChiTraceRequest(BaseModel):
    picture_ids: list = []
    sound_ids: list = []
    input_text: str = ""

@app.post("/api/v1/gualaloom/chi_trace")
async def chi_trace(req: ChiTraceRequest):
    """Read-only chi-geometry readout. No state mutation."""
    _gl_init()
    if _guala is None:
        return JSONResponse({"error": "initializing"}, status_code=503)
    if not req.picture_ids and not req.sound_ids and not req.input_text:
        return JSONResponse({"error": "at least one of picture_ids, sound_ids, or input_text required"}, status_code=400)

    result = {"tick": _guala.tick}

    # Input chis
    if req.input_text:
        result["input_chis"] = _guala._chis_for_text(req.input_text)
    else:
        result["input_chis"] = []

    # Refs
    refs = {}
    all_ids = [(pid, "picture") for pid in (req.picture_ids or [])] + \
              [(sid, "sound") for sid in (req.sound_ids or [])]
    for item_id, kind in all_ids:
        ref = {"kind": kind, "title": None, "n_chis": 0, "chis": [], "_note": None}

        if kind == "picture":
            pic = _guala._pictures.get(item_id)
            if pic is None:
                ref["_note"] = "item not found"
                refs[item_id] = ref
                continue
            ref["title"] = pic.title

            # Reverse map: find sight motifs whose source_history contains this item_id
            item_chis = []
            for sm in _guala.sight.motifs:
                if item_id in sm.source_history:
                    # Find atlas entries for this motif in the sight section
                    for chi_key, entries in _guala.atlas.entries.items():
                        for e in entries:
                            if e.get("section") == "sight" and e.get("motif") == sm.motif_id:
                                deep_prior = _guala.deep_atlas.get_prior(chi_key, "sight", sm.motif_id)
                                # Cross-modal neighbors
                                assoc = _guala.atlas.query_associations("sight", chi_key)
                                neighbors = {}
                                for sec_name, motif_list in assoc.items():
                                    top5 = sorted(motif_list, key=lambda x: x[1], reverse=True)[:5]
                                    neighbors[sec_name] = [{"motif": m, "strength": round(s, 3)} for m, s in top5]
                                item_chis.append({
                                    "chi": chi_key,
                                    "binding_strength": round(e["strength"], 3),
                                    "encoded_strength": round(e.get("encoded_strength", 0), 3),
                                    "dwell_ticks": e.get("dwell_ticks", 0),
                                    "reinforcement_count": e.get("reinforcement_count", 0),
                                    "deep_prior": round(deep_prior, 3),
                                    "in_deep": deep_prior > 0,
                                    "cross_modal_neighbors": neighbors,
                                })
            # Sort by strength, cap at 16
            item_chis.sort(key=lambda x: x["binding_strength"], reverse=True)
            ref["chis"] = item_chis[:16]
            ref["n_chis"] = len(item_chis)

        elif kind == "sound":
            snd = _guala._sounds.get(item_id)
            if snd is None:
                ref["_note"] = "item not found"
                refs[item_id] = ref
                continue
            ref["title"] = snd.get("title", item_id)
            # Sound→chi: audio_* sections in atlas keyed by deterministic_motif_id(item_id)
            target_motif = deterministic_motif_id(item_id)
            item_chis = []
            for chi_key, entries in _guala.atlas.entries.items():
                for e in entries:
                    if e.get("section", "").startswith("audio_") and e.get("motif") == target_motif:
                        deep_prior = _guala.deep_atlas.get_prior(chi_key, e["section"], target_motif)
                        assoc = _guala.atlas.query_associations(e["section"], chi_key)
                        neighbors = {}
                        for sec_name, motif_list in assoc.items():
                            top5 = sorted(motif_list, key=lambda x: x[1], reverse=True)[:5]
                            neighbors[sec_name] = [{"motif": m, "strength": round(s, 3)} for m, s in top5]
                        item_chis.append({
                            "chi": chi_key,
                            "section": e["section"],
                            "binding_strength": round(e["strength"], 3),
                            "encoded_strength": round(e.get("encoded_strength", 0), 3),
                            "dwell_ticks": e.get("dwell_ticks", 0),
                            "reinforcement_count": e.get("reinforcement_count", 0),
                            "deep_prior": round(deep_prior, 3),
                            "in_deep": deep_prior > 0,
                            "cross_modal_neighbors": neighbors,
                        })
            item_chis.sort(key=lambda x: x["binding_strength"], reverse=True)
            ref["chis"] = item_chis[:16]
            ref["n_chis"] = len(item_chis)
            if not item_chis:
                ref["_note"] = "no audio-section bindings found for this sound"

        refs[item_id] = ref
    result["refs"] = refs

    # Input chi neighborhoods
    if result["input_chis"]:
        neighborhoods = {}
        for chi_val in set(result["input_chis"]):
            by_section = {}
            for d in range(-_guala.atlas.band, _guala.atlas.band + 1):
                for e in _guala.atlas.entries.get(chi_val + d, []):
                    if e["strength"] < 0.01:
                        continue
                    sec = e["section"]
                    if sec not in by_section:
                        by_section[sec] = []
                    deep_prior = _guala.deep_atlas.get_prior(chi_val + d, sec, e["motif"])
                    by_section[sec].append({
                        "motif_id": e["motif"],
                        "strength": round(e["strength"], 3),
                        "in_deep": deep_prior > 0,
                    })
            # Sort each section by strength, cap at 5
            for sec in by_section:
                by_section[sec] = sorted(by_section[sec], key=lambda x: x["strength"], reverse=True)[:5]
            if by_section:
                neighborhoods[str(chi_val)] = {"by_section": by_section}
        result["input_chi_neighborhoods"] = neighborhoods
    else:
        result["input_chi_neighborhoods"] = {}

    # Hard-cap response at 64KB
    resp_str = json.dumps(result)
    if len(resp_str) > 65536:
        # Truncate cross_modal_neighbors first
        for ref in result["refs"].values():
            for c in ref.get("chis", []):
                c["cross_modal_neighbors"] = {}
        result["_truncated"] = True

    return result


# ════════════════════════════════════════════════════════════════
# v7: Substrate event stream (SSE) + sleep endpoint
# GUALALOOM-V7-AUTONOMY-WC-2026-06-06
# ════════════════════════════════════════════════════════════════

@app.get("/api/v1/gualaloom/events")
async def gualaloom_events(since: int = 0, stream: bool = False, n: int = 50):
    """Substrate events. ?stream=true for SSE, default returns JSON array.

    GL-BUG-DUPLICATE-EVENTS-ROUTE (found during -196 live verification):
    this path had TWO @app.get definitions -- an earlier stub (always
    `return {"events": []}` in embedded mode, the production config)
    registered first, silently shadowing this real implementation for
    every request. Deleted; `n` (loomscan.html's limit param, previously
    silently ignored here) now actually controls `limit` below instead
    of a hardcoded 50 that only coincidentally matched loomscan's own
    default."""
    if _is_remote():
        # Remote mode: poll substrate via socket for events
        client = _get_substrate_client()
        if stream:
            import asyncio
            # SSE stream gets its own dedicated client to avoid blocking
            # the shared client with continuous /events polling
            from dsf_ai_service.substrate_client import SubstrateClient
            sse_client = SubstrateClient()
            async def event_generator():
                last_tick = since
                while True:
                    try:
                        result = await sse_client.call("gualaloom_post",
                                                       command="/events",
                                                       text=str(last_tick))
                        for ev in result.get("events", []):
                            if ev.get("tick", 0) > last_tick:
                                last_tick = ev["tick"]
                            yield f"data: {json.dumps(ev)}\n\n"
                    except Exception:
                        pass
                    await asyncio.sleep(1.5)
            return StreamingResponse(event_generator(), media_type="text/event-stream")
        else:
            try:
                result = await client.call("gualaloom_post",
                                           command="/events",
                                           text=str(since))
                return {"events": result.get("events", [])}
            except ConnectionError:
                return {"events": []}
    _gl_init()
    if stream:
        import asyncio

        async def event_generator():
            last_tick = since
            while True:
                events = _guala.get_recent_events(since_tick=last_tick, limit=n)
                for ev in events:
                    if ev["tick"] > last_tick:
                        last_tick = ev["tick"]
                    yield f"data: {json.dumps(ev)}\n\n"
                await asyncio.sleep(1.0)

        return StreamingResponse(event_generator(), media_type="text/event-stream")
    else:
        events = _guala.get_recent_events(since_tick=since, limit=n)
        return {"events": events}


@app.websocket("/events_stream")
async def events_stream_ws(websocket):
    """WebSocket: live event stream from substrate ring buffer.
    Companion HTML and bridge subscribe here for real-time events."""
    import asyncio
    await websocket.accept()
    try:
        if _is_remote():
            client = _get_substrate_client()
            last_tick = 0
            while True:
                try:
                    result = await client.call("gualaloom_post",
                                               command="/events",
                                               text=str(last_tick),
                                               timeout=5.0)
                    for ev in result.get("events", []):
                        if ev.get("tick", 0) > last_tick:
                            last_tick = ev["tick"]
                        await websocket.send_json(ev)
                except Exception:
                    pass
                await asyncio.sleep(0.5)
        else:
            ring = getattr(_guala, '_substrate_ring', None)
            if ring is None:
                await websocket.send_json({"error": "ring not initialized"})
                return
            cursor = ring.subscribe()
            while True:
                events = cursor.read_available()
                for ev in events:
                    await websocket.send_json(ev)
                if not events:
                    await asyncio.sleep(0.1)
    except Exception:
        pass


@app.get("/api/v1/gualaloom/ring/read")
async def ring_read(since_seq: int = 0, limit: int = 100):
    """REST ring read — returns events from sequence since_seq.
    Bridge and external consumers use this for stateless event polling."""
    if _is_remote():
        client = _get_substrate_client()
        try:
            return await client.call("ring_read",
                                      since_seq=since_seq, limit=limit)
        except ConnectionError:
            return {"events": [], "published_seq": 0}
    ring = getattr(_guala, '_substrate_ring', None)
    if ring is None:
        return {"events": [], "published_seq": 0}
    from dsf_ai_service.substrate.ring_buffer import Cursor
    cursor = Cursor(ring)
    cursor._read_seq = since_seq
    events = cursor.read_available()[:limit]
    return {"events": events, "published_seq": ring._published_seq}


@app.post("/api/v1/gualaloom/ring/write")
async def ring_write(request: Request):
    """REST ring write — publishes an input event to the InputRing.
    Bridge uses this for guaranteed-ack writes."""
    if _is_remote():
        client = _get_substrate_client()
        body = await request.json()
        try:
            return await client.call("ring_write", **body)
        except ConnectionError:
            return {"ok": False, "error": "substrate unreachable"}
    from dsf_ai_service.substrate_runner import _input_ring
    if _input_ring is None:
        return {"ok": False, "error": "ring not initialized"}
    body = await request.json()
    from dsf_ai_service.substrate.ring_buffer import InputRingCapacityError
    try:
        seq = _input_ring.publish(
            kind=body.get("kind", "text_input"),
            source=body.get("source", "bridge"),
            **body.get("data", {}))
    except InputRingCapacityError as error:
        return JSONResponse(
            status_code=429,
            content={
                "ok": False,
                "error": str(error),
                "input_pending": _input_ring.pending,
                "input_pending_transport_bytes": (
                    _input_ring.pending_transport_bytes),
                "input_max_pending_transport_bytes": (
                    _input_ring.max_pending_transport_bytes),
            },
        )
    return {"ok": True, "seq": seq}


@app.post("/api/v1/gualaloom/sleep")
async def gualaloom_sleep():
    """Manual sleep trigger."""
    _gl_init()
    result = _guala.manual_sleep()
    return result


# ════════════════════════════════════════════════════════════════
# v7 Phase 5: Upload endpoints
# GUALALOOM-V7-AUTONOMY-WC-2026-06-06
# ════════════════════════════════════════════════════════════════

@app.post("/api/v1/gualaloom/upload/book")
async def gualaloom_upload_book(file: UploadFile = File(...)):
    """Upload a text file as a new corpus for autonomous reading."""
    if _is_remote():
        content = await file.read()
        text = content.decode('utf-8')
        client = _get_substrate_client()
        return await client.call("gualaloom_post",
                                 command=f"/addbook:{file.filename}",
                                 text=text)
    _gl_init()
    if not file.filename.endswith('.txt'):
        raise HTTPException(400, "Book must be a .txt file")
    content = await file.read()
    if len(content) > 1024 * 1024:
        raise HTTPException(400, "File too large (max 1MB)")
    try:
        text = content.decode('utf-8')
    except UnicodeDecodeError:
        raise HTTPException(400, "File must be UTF-8")
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    if not lines:
        raise HTTPException(400, "File is empty")
    title = file.filename.replace('.txt', '').replace('_', ' ')
    corpus_id = file.filename.replace('.txt', '').replace(' ', '_').lower()
    _guala.add_corpus(corpus_id, title, lines)
    _guala._log_substrate_event("corpus_added",
                                corpus_id=corpus_id, title=title,
                                n_lines=len(lines))
    return {"message": f"added \"{title}\" ({len(lines)} lines) to her library",
            "corpus_id": corpus_id}


@app.post("/api/v1/gualaloom/upload/picture")
async def gualaloom_upload_picture(file: UploadFile = File(...)):
    """Upload a picture for visual perception. C8: decode in executor."""
    if _is_remote():
        import base64
        content = await file.read()
        b64 = base64.b64encode(content).decode()
        client = _get_substrate_client()
        return await client.call("gualaloom_post",
                                 command=f"/addpicture:{file.filename}",
                                 text=b64, timeout=30.0)
    _gl_init()
    import hashlib
    content = await file.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(400, "File too large (max 10MB)")
    _fname = file.filename
    def _decode():
        """Decode, persist the original atomically, then register the picture.

        Registration cannot point at an unfinished EFS write: deployment
        quiescence owns this entire worker through _run_lifecycle_executor.
        """
        t0 = time.time()
        try:
            try:
                import pillow_heif as _ph; _ph.register_heif_opener()
            except ImportError:
                pass
            from PIL import Image
            import io as _io
            img_full = Image.open(_io.BytesIO(content))
            if img_full.mode not in ('RGB', 'L'):
                img_full = img_full.convert('RGB')
            orig_w, orig_h = img_full.size
            grid = np.array(img_full.convert('L').resize((64, 64)), dtype=np.float64) / 255.0
        except Exception as e:
            print(f"[decode-upload-picture] {time.time()-t0:.2f}s ERROR")
            return {"error": f"Cannot decode image: {e}"}
        item_id = hashlib.md5(content).hexdigest()[:12]
        title = _fname or item_id
        pic_dir = os.path.join(STATE_DIR, "pictures")
        try:
            os.makedirs(pic_dir, exist_ok=True)
        except OSError as _me:
            print(f"[decode-upload-picture] pic_dir mkdir failed: {_me}")
        ext = (_fname or "img").rsplit('.', 1)[1] if '.' in (_fname or "") else 'jpg'
        orig_path = os.path.join(pic_dir, f"{item_id}_original.{ext}")

        pic = PictureItem(item_id=item_id, title=title,
                          intensity_grid=grid, source="upload",
                          shown_at_tick=_guala.tick)
        pic.original_path = orig_path
        pic.original_width = orig_w
        pic.original_height = orig_h
        import uuid as _picture_uuid
        tmp_path = f"{orig_path}.{_picture_uuid.uuid4().hex}.tmp"
        try:
            with open(tmp_path, 'wb') as original_file:
                original_file.write(content)
                original_file.flush()
                os.fsync(original_file.fileno())
            os.replace(tmp_path, orig_path)
            directory_fd = os.open(pic_dir, os.O_RDONLY)
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
        except BaseException:
            try:
                os.unlink(tmp_path)
            except FileNotFoundError:
                pass
            raise

        # Publish only after the exact original exists on EFS.
        _guala._pictures[item_id] = pic
        _guala._log_substrate_event("picture_uploaded",
                                    item_id=item_id, title=title)
        print(f"[decode-upload-picture] complete {time.time()-t0:.2f}s")

        return {"message": f"picture \"{title}\" uploaded ({grid.shape[0]}x{grid.shape[1]})",
                "item_id": item_id}
    result = await _run_lifecycle_executor(_decode)
    if "error" in result:
        raise HTTPException(400, result["error"])
    return result


@app.post("/api/v1/gualaloom/upload/sound")
async def gualaloom_upload_sound(file: UploadFile = File(...)):
    """Decode one bounded sound and retain only its canonical replay capture."""
    content = await file.read(_LIVE_AUDIO_MAX_BYTES + 1)
    if len(content) > _LIVE_AUDIO_MAX_BYTES:
        raise HTTPException(413, "Sound upload exceeds the 4 MiB request boundary")
    if _is_remote():
        import base64
        b64 = base64.b64encode(content).decode()
        client = _get_substrate_client()
        return await client.call("gualaloom_post",
                                 command=f"/addsound:{file.filename}",
                                 text=b64, timeout=30.0)
    _gl_init()
    if _guala is None:
        return {"message": "initializing..."}
    import base64
    b64 = base64.b64encode(content).decode()
    from pydantic import BaseModel
    class FakeMsg(BaseModel):
        text: str
        command: str = ""
        source: str = None
    fake = FakeMsg(
        text=b64,
        command=f"/addsound:{file.filename or 'uploaded-sound'}")
    result = await gualaloom_chat(fake)
    return result


@app.post("/api/v1/gualaloom/upload/video")
async def gualaloom_upload_video(file: UploadFile = File(...)):
    """Retain one bounded audiovisual capture for autonomous attention."""
    if not _video_upload_read_lock.acquire(blocking=False):
        raise HTTPException(429, "Another video upload is currently being read")
    try:
        content = await file.read(_VIDEO_UPLOAD_MAX_BYTES + 1)
    finally:
        _video_upload_read_lock.release()
    if len(content) > _VIDEO_UPLOAD_MAX_BYTES:
        raise HTTPException(413, "Video exceeds the 30 MiB request boundary")
    if _is_remote():
        # Remote video processing is not wired; retain a bounded handoff file
        # without claiming that a nonexistent consumer has queued it.
        vid_dir = os.path.join("state", "uploads")
        os.makedirs(vid_dir, exist_ok=True)
        import hashlib
        vid_id = hashlib.md5(content).hexdigest()[:12]
        vid_path = os.path.join(vid_dir, f"{vid_id}.video")
        retained = [
            name for name in os.listdir(vid_dir)
            if name.endswith(".video")
            and os.path.isfile(os.path.join(vid_dir, name))
        ]
        if (not os.path.exists(vid_path)
                and len(retained) >= _VIDEO_LIBRARY_MAX_ITEMS):
            raise HTTPException(409, "Remote video retention boundary reached")
        with open(vid_path, 'wb') as f:
            f.write(content)
        return {
            "message": (
                f"video saved ({len(content)//1024}KB); remote video processing "
                "is unavailable"),
            "item_id": vid_id,
            "processing": "unavailable_in_remote_mode",
        }
    _gl_init()
    if _guala is None:
        raise HTTPException(503, "Guala is still initializing")
    import hashlib, shutil, tempfile, subprocess
    _fname = file.filename
    item_id = hashlib.md5(content).hexdigest()[:12]
    with _guala.lock:
        if item_id in _guala._videos:
            return {"message": "video already retained", "item_id": item_id}
        if len(_guala._videos) >= _VIDEO_LIBRARY_MAX_ITEMS:
            raise HTTPException(409, "Video library boundary reached")
    if not _video_upload_lock.acquire(blocking=False):
        raise HTTPException(429, "Another video is currently being decoded")

    def _decode():
        t0 = time.time()
        title = _fname or item_id
        tmp_dir = tempfile.mkdtemp(prefix="guala_vid_")
        video_path = os.path.join(tmp_dir, "input.mp4")
        with open(video_path, "wb") as f:
            f.write(content)
        frame_dir = os.path.join(tmp_dir, "frames")
        os.makedirs(frame_dir, exist_ok=True)
        audio_path = os.path.join(tmp_dir, "audio.wav")
        try:
            subprocess.run([
                "ffmpeg", "-nostdin", "-hide_banner", "-i", video_path,
                "-t", str(_VIDEO_CAPTURE_MAX_SECONDS), "-vf",
                "scale=160:120,format=gray", "-r", str(_VIDEO_FRAME_RATE),
                "-frames:v", str(_VIDEO_MAX_RETAINED_FRAMES),
                os.path.join(frame_dir, "frame_%05d.png"),
                "-y", "-loglevel", "error"
            ], check=True, timeout=60)
            from dsf_ai_service.substrate_runner import _webm_to_wav_bytes
            wav_bytes = _webm_to_wav_bytes(
                content, encoded_max_bytes=_VIDEO_UPLOAD_MAX_BYTES)
            if wav_bytes is not None:
                with open(audio_path, "wb") as audio_file:
                    audio_file.write(wav_bytes)
                    audio_file.flush()
                    os.fsync(audio_file.fileno())
        except FileNotFoundError:
            shutil.rmtree(tmp_dir, ignore_errors=True)
            print(f"[decode-video] {time.time()-t0:.2f}s ERROR: no ffmpeg")
            return {"message": "ffmpeg not available"}
        except Exception as e:
            shutil.rmtree(tmp_dir, ignore_errors=True)
            print(f"[decode-video] {time.time()-t0:.2f}s ERROR")
            return {"message": f"video decode error: {e}"}
        frame_files = sorted(f for f in os.listdir(frame_dir) if f.endswith('.png'))
        if len(frame_files) > _VIDEO_MAX_RETAINED_FRAMES:
            shutil.rmtree(tmp_dir, ignore_errors=True)
            return {"message": "video decode exceeded the retained frame boundary"}
        for fname in frame_files:
            from PIL import Image
            fpath = os.path.join(frame_dir, fname)
            if os.path.getsize(fpath) > _VIDEO_MAX_FRAME_FILE_BYTES:
                shutil.rmtree(tmp_dir, ignore_errors=True)
                return {"message": "video frame exceeded its encoded byte boundary"}
            img = Image.open(fpath).convert('L')
            if img.size != (160, 120):
                shutil.rmtree(tmp_dir, ignore_errors=True)
                return {"message": "video frame changed the retained geometry"}
            arr = np.array(img, dtype=np.uint8)
            np.save(fpath.replace('.png', '.npy'), arr)
            os.unlink(fpath)
        n_frames = len(frame_files)
        duration_ms = int(n_frames / float(_VIDEO_FRAME_RATE) * 1000)
        try:
            os.unlink(video_path)
        except FileNotFoundError:
            pass
        vid = VideoItem(item_id=item_id, title=title,
                        frame_dir=frame_dir,
                        audio_path=audio_path if os.path.exists(audio_path) else "",
                        duration_ms=duration_ms, n_frames=n_frames,
                        source="upload", shown_at_tick=_guala.tick)
        with _guala.lock:
            _guala._videos[item_id] = vid
            _guala._log_substrate_event(
                "video_uploaded", item_id=item_id, title=title,
                n_frames=n_frames, duration_ms=duration_ms)
        print(f"[decode-video] {time.time()-t0:.2f}s")
        return {
            "message": (
                f"video \"{title}\" decoded ({n_frames} frames, "
                f"{duration_ms}ms; audio "
                f"{'retained' if vid.audio_path else 'unavailable'})"),
            "item_id": item_id,
        }
    try:
        return await _run_lifecycle_executor(_decode)
    finally:
        _video_upload_lock.release()


# ════════════════════════════════════════════════════════════════
# Deep multimodal substrate — parallel test endpoint
# GL-CMD-DEPLOY-DEEP-SUBSTRATE-WC-20260608-01
# ════════════════════════════════════════════════════════════════

_substrate = None

def _get_substrate():
    global _substrate
    if _substrate is None:
        _substrate = _init_substrate()
    return _substrate

def _init_substrate():
    from dsf_ai_service.substrate.GL_MDL_MULTIMODAL_DEEP_WC_20260608_03 import DeepMultiModalCognition
    cog = DeepMultiModalCognition()
    SENSORY_WORDS = ["moon", "cow", "bears", "stars", "kittens", "room"]
    OTHER_WORDS = ["the", "and", "a", "in", "was", "goodnight", "of",
                   "picture", "over", "there", "were", "three", "little", "sitting", "on",
                   "great", "green", "telephone", "red", "balloon",
                   "chairs", "jumping", "air", "noises", "everywhere"]
    for w in SENSORY_WORDS + OTHER_WORDS:
        cog.install_word(w)
    for _ in range(5):
        for w in SENSORY_WORDS:
            cog.hear_word_with_senses(w)
            cog.run(8)
    GOODNIGHT_MOON = """in the great green room there was a telephone and a red balloon.
and a picture of the cow jumping over the moon.
and there were three little bears sitting on chairs.
goodnight room. goodnight moon.
goodnight cow jumping over the moon.
goodnight light and the red balloon.
goodnight bears. goodnight chairs.
goodnight kittens. goodnight mittens.
goodnight stars. goodnight air. goodnight noises everywhere."""
    sentences = [s.strip() for s in GOODNIGHT_MOON.replace("\n", " ").split(".") if s.strip()]
    SENSORY_SET = set(SENSORY_WORDS)
    for _ in range(3):
        for sent in sentences:
            words = sent.lower().replace(",", "").split()
            for w in words:
                w_clean = "".join(c for c in w if c.isalnum())
                if w_clean in SENSORY_SET and w_clean in cog.sections["word"]:
                    cog.hear_word_with_senses(w_clean)
                elif w_clean in cog.sections["word"]:
                    cog.fire("word", w_clean)
                cog.run(3)
            cog.run(4)
    print(f"[Substrate] Initialized")
    return cog


class SubstrateHearRequest(BaseModel):
    word: str

class SubstrateFeedRequest(BaseModel):
    word: str
    modalities: List[str] = ["visual", "audio"]


@app.post("/substrate/hear_word")
async def substrate_hear_word(req: SubstrateHearRequest):
    cog = _get_substrate()
    word = req.word
    cog.emissions.clear()
    cog.run(15)
    cog.emissions.clear()
    cog.fire("word", word, salience=2.5)
    em = cog.run(25)
    first_per_section = {}
    strongest_per_section = {}
    for e in em:
        sec = e["section"]
        if sec not in first_per_section:
            first_per_section[sec] = e["label"]
        if sec not in strongest_per_section or e["activation"] > strongest_per_section[sec]["activation"]:
            strongest_per_section[sec] = {"label": e["label"], "activation": e["activation"]}
    # Bridge: relay multimodal winner to v7 default session (spec 4.2)
    result = {"first": first_per_section, "strongest": strongest_per_section}
    try:
        from dsf_ai_service.substrate.v7_engine import get_or_create_session
        v7_session = get_or_create_session("default", engine=_guala)
        bridge = _get_bridge(v7_session)
        # Use the heard word directly (attention_focus decays after 20 ticks)
        bridge_result = bridge.multimodal_winner_to_v7(word)
        if bridge_result:
            result["bridge_mm_to_v7"] = bridge_result
    except Exception:
        pass
    return result


@app.post("/substrate/feed_senses")
async def substrate_feed_senses(req: SubstrateFeedRequest):
    cog = _get_substrate()
    word = req.word
    modalities = req.modalities
    cog.emissions.clear()
    cog.run(15)
    cog.emissions.clear()
    for modality in modalities:
        modal_label = f"{word}__{modality}"
        if modal_label in cog.sections.get(modality, {}):
            cog.fire(modality, modal_label, salience=2.5, set_focus=False)
    em = cog.run(25)
    word_em = [e for e in em if e["section"] == "word"]
    if not word_em:
        return {"strongest_word": None, "top_words": []}
    strongest = max(word_em, key=lambda e: e["activation"])
    unique = []
    for e in word_em:
        if e["label"] not in unique:
            unique.append(e["label"])
    return {"strongest_word": strongest["label"], "activation": strongest["activation"],
            "top_words": unique[:5]}


# ════════════════════════════════════════════════════════════════
# v7 DNA Recipe Substrate
# GL-CMD-DEPLOY-DNA-RECIPE-WC-20260608-01
# ════════════════════════════════════════════════════════════════

import uuid as _uuid

class V7ConverseRequest(BaseModel):
    text: str
    session_id: Optional[str] = None
    emission_mode: Optional[str] = None  # "topk" | "grandurun"

class V7FeedbackRequest(BaseModel):
    session_id: str
    correct: bool
    expected_tokens: Optional[Dict] = None

def _get_bridge(session):
    """Get or create a bridge between a v7 session and the multimodal substrate."""
    from dsf_ai_service.substrate.gl_bridge import SubstrateBridge
    if not hasattr(session, '_bridge') or session._bridge is None:
        mm = _get_substrate()
        session._bridge = SubstrateBridge(session, mm)
    return session._bridge

@app.post("/v7/converse")
async def v7_converse(req: V7ConverseRequest):
    if _is_remote():
        client = _get_substrate_client()
        sid = req.session_id or str(_uuid.uuid4())[:8]
        result = await client.call("v7_converse",
                                   session_id=sid, text=req.text,
                                   emission_mode=req.emission_mode)
        result["session_id"] = sid
        return result
    if _guala is None:
        raise HTTPException(status_code=503, detail={
            "error": "guala_not_ready",
            "retry_after_seconds": 10,
            "message": "she is still loading — try again in a moment"
        })
    from dsf_ai_service.substrate.v7_engine import get_or_create_session, save_session
    sid = req.session_id or str(_uuid.uuid4())[:8]
    text = req.text
    def _do_converse():
        session = get_or_create_session(sid, engine=_guala)
        result = session.converse(text)
        # Bridge: relay v7 emissions to multimodal (spec 4.2)
        try:
            bridge = _get_bridge(session)
            tokens = [t.get("token", "") for t in result.get("response_tokens", [])]
            if tokens:
                bridge_result = bridge.v7_emission_to_multimodal(tokens)
                if bridge_result:
                    result["bridge_v7_to_mm"] = bridge_result
        except Exception:
            pass
        save_session(session)
        return session, result
    session, result = await _run_lifecycle_executor(_do_converse)
    result["session_id"] = sid
    return result

@app.post("/v7/feedback")
async def v7_feedback(req: V7FeedbackRequest):
    if _is_remote():
        client = _get_substrate_client()
        result = await client.call("v7_feedback",
                                   session_id=req.session_id,
                                   correct=req.correct,
                                   expected_tokens=req.expected_tokens)
        return result
    if _guala is None:
        raise HTTPException(status_code=503, detail={
            "error": "guala_not_ready",
            "retry_after_seconds": 10,
            "message": "she is still loading — try again in a moment"
        })
    from dsf_ai_service.substrate.v7_engine import get_or_create_session, save_session
    feedback_sid = req.session_id
    correct = req.correct
    expected_tokens = req.expected_tokens
    def _do_feedback():
        session = get_or_create_session(feedback_sid, engine=_guala)
        result = session.apply_feedback(correct, expected_tokens)
        save_session(session)
        return session, result
    session, result = await _run_lifecycle_executor(_do_feedback)
    result["session_id"] = feedback_sid
    return result

# ── GL-CMD-TEACHER-CORRECTION-UI: teacher endpoints ──────────

class TeacherFeedbackRequest(BaseModel):
    emission_id: Optional[str] = None
    source: Optional[str] = "joe"

class TeacherCorrectionRequest(BaseModel):
    emission_id: Optional[str] = None
    corrected_text: Optional[str] = None
    story: Optional[str] = None
    temporal: Optional[str] = None
    sensory_freetext: Optional[str] = None
    source: Optional[str] = "joe"
    # 2026-07-16 (Joe: "corrections should work always"): attempts carry no
    # certified emission record, so the page supplies the conversation pair
    # directly -- the question it answered and the attempt text itself.
    original_input: Optional[str] = None
    her_emission: Optional[str] = None


class AuditoryL5TeachRequest(BaseModel):
    experience_id: str
    kind: str
    tutor_label: str


class CausalActionTeachRequest(BaseModel):
    trigger_experience_id: str
    action_experience_id: str
    source: Optional[str] = "joe"


@app.get("/api/v1/auditory/status")
async def auditory_l5_status():
    if _is_remote():
        client = _get_substrate_client()
        return await client.call("auditory_l5_status")
    if _guala is None:
        raise HTTPException(status_code=503, detail="guala_not_ready")
    return _guala.auditory_l5_status()


@app.post(
    "/api/v1/auditory/teach",
    dependencies=[Depends(_api_key_dep)],
)
async def auditory_l5_teach(req: AuditoryL5TeachRequest):
    if req.kind not in ("spoken_form", "source_continuity"):
        raise HTTPException(status_code=400, detail="invalid auditory teaching kind")
    if not req.tutor_label.strip():
        raise HTTPException(status_code=400, detail="tutor_label required")
    authority_receipt = None
    if _GUALALOOM_API_KEY:
        from dsf_ai_service.substrate.auditory_tutor_authority import (
            AuditoryTutorAuthority,
        )
        try:
            authority_receipt = AuditoryTutorAuthority(
                api_key=_GUALALOOM_API_KEY,
                required=True,
            ).issue(
                experience_id=req.experience_id,
                kind=req.kind,
                tutor_label=req.tutor_label,
            ).as_dict()
        except ValueError as error:
            raise HTTPException(
                status_code=400, detail=str(error)
            ) from error
    if _is_remote():
        raise HTTPException(
            status_code=501,
            detail="remote auditory tutoring has no authoritative durability barrier",
        )
    if _guala is None:
        raise HTTPException(status_code=503, detail="guala_not_ready")
    def _teach_and_commit():
        return _guala.durably_teach_latest_auditory_experience(
            experience_id=req.experience_id,
            kind=req.kind,
            tutor_label=req.tutor_label,
            authority_receipt=authority_receipt,
            state_dir=STATE_DIR,
        )

    try:
        return await _run_lifecycle_executor(_teach_and_commit)
    except (RuntimeError, ValueError) as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


@app.post(
    "/api/v1/auditory/teach-asset",
    dependencies=[Depends(_api_key_dep)],
)
async def auditory_l5_teach_asset(
    file: UploadFile = File(...),
    tutor_label: str = Form(...),
):
    """Teach one authenticated isolated sound as a spoken-form witness."""
    if _is_remote():
        raise HTTPException(
            status_code=501,
            detail="auditory tutor asset requires embedded ownership",
        )
    if _guala is None:
        raise HTTPException(status_code=503, detail="guala_not_ready")
    encoded = await file.read(_LIVE_AUDIO_MAX_BYTES + 1)
    if not encoded:
        raise HTTPException(status_code=400, detail="auditory tutor asset is empty")
    if len(encoded) > _LIVE_AUDIO_MAX_BYTES:
        raise HTTPException(
            status_code=413,
            detail="auditory tutor asset exceeds the 4 MiB request boundary",
        )

    def _decode_and_teach():
        from dsf_ai_service.substrate_runner import _webm_to_wav_bytes

        wav_bytes = _webm_to_wav_bytes(encoded)
        if not wav_bytes:
            raise ValueError(
                "auditory tutor asset could not be decoded into canonical PCM"
            )
        return _guala.durably_teach_isolated_auditory_asset(
            wav_bytes,
            tutor_label,
            state_dir=STATE_DIR,
        )

    try:
        return await _run_lifecycle_executor(_decode_and_teach)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except RuntimeError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


@app.post(
    "/api/v1/causal-action/teach",
    dependencies=[Depends(_api_key_dep)],
)
async def causal_action_teach(req: CausalActionTeachRequest):
    if req.source not in ("joe", "wc"):
        raise HTTPException(status_code=403, detail="invalid source")
    if req.trigger_experience_id == req.action_experience_id:
        raise HTTPException(
            status_code=400,
            detail="trigger and action must be separate causal experiences",
        )
    for value in (
        req.trigger_experience_id,
        req.action_experience_id,
    ):
        if (
            not isinstance(value, str)
            or len(value) != 64
            or any(character not in "0123456789abcdef" for character in value)
        ):
            raise HTTPException(
                status_code=400,
                detail="causal experience id must be canonical SHA-256",
            )
    if _is_remote():
        raise HTTPException(
            status_code=501,
            detail="remote causal action teaching has no durability barrier",
        )
    if _guala is None:
        raise HTTPException(status_code=503, detail="guala_not_ready")

    def _teach_and_commit():
        return _guala.durably_teach_causal_action(
            trigger_experience_id=req.trigger_experience_id,
            action_experience_id=req.action_experience_id,
            source=req.source,
            state_dir=STATE_DIR,
        )

    try:
        return await _run_lifecycle_executor(_teach_and_commit)
    except (RuntimeError, ValueError) as error:
        raise HTTPException(status_code=409, detail=str(error)) from error

@app.post("/api/v1/teacher/feedback")
async def teacher_feedback(req: TeacherFeedbackRequest):
    if req.source not in ("joe", "wc"):
        raise HTTPException(status_code=403, detail="invalid source")
    if _is_remote():
        client = _get_substrate_client()
        return await client.call("teacher_feedback",
                                  emission_id=req.emission_id,
                                  source=req.source)
    if _guala is None:
        raise HTTPException(status_code=503, detail="guala_not_ready")
    return await _run_lifecycle_executor(
        lambda: handle_teacher_feedback_local(req)
    )


@app.post("/api/v1/teacher/correction")
async def teacher_correction(req: TeacherCorrectionRequest):
    if req.source not in ("joe", "wc"):
        raise HTTPException(status_code=403, detail="invalid source")
    if not req.corrected_text or not req.corrected_text.strip():
        raise HTTPException(status_code=400, detail="corrected_text required")
    if _is_remote():
        client = _get_substrate_client()
        return await client.call("teacher_correction",
                                  emission_id=req.emission_id,
                                  corrected_text=req.corrected_text,
                                  story=req.story,
                                  temporal=req.temporal,
                                  sensory_freetext=req.sensory_freetext,
                                  source=req.source)
    if _guala is None:
        raise HTTPException(status_code=503, detail="guala_not_ready")
    return await _run_lifecycle_executor(
        lambda: handle_teacher_correction_local(req)
    )


def handle_teacher_feedback_local(req):
    with _guala.lock:
        causal_record = _guala._emission_records.get(req.emission_id)
    if (
        isinstance(causal_record, dict)
        and causal_record.get("response_source")
        == "causal_action_cycle_commit"
    ):
        return _guala.durably_review_causal_action_emission(
            emission_id=req.emission_id,
            correct=True,
            source=req.source,
            state_dir=STATE_DIR,
        )
    rec = _guala._certified_emission_record(req.emission_id)
    if rec is None:
        raise HTTPException(status_code=400,
                            detail="emission is not source-certified")
    original_input = rec.get("input_text", "")
    her_emission = rec.get("text", "")
    if not original_input or not her_emission:
        raise HTTPException(status_code=400, detail="no conversation context")
    return _guala.apply_teacher_correction(
        original_input=original_input, her_emission=her_emission,
        correct=True, source=req.source, emission_id=req.emission_id)


def handle_teacher_correction_local(req):
    with _guala.lock:
        causal_record = _guala._emission_records.get(req.emission_id)
    if (
        isinstance(causal_record, dict)
        and causal_record.get("response_source")
        == "causal_action_cycle_commit"
    ):
        result = _guala.durably_review_causal_action_emission(
            emission_id=req.emission_id,
            correct=False,
            source=req.source,
            state_dir=STATE_DIR,
        )
        result["corrected_text_learned"] = False
        result["correction_note"] = (
            "action revoked; corrected text requires a separately "
            "experienced spoken action"
        )
        return result
    rec = _guala._certified_emission_record(req.emission_id)
    if rec is not None:
        original_input = rec.get("input_text", "")
        her_emission = rec.get("text", "")
    else:
        # Attempt-labeled replies (organism babble) have no certified
        # record; the page supplies the pair. Corrections must work for
        # EVERY reply kind -- teaching is the consequence loop.
        original_input = (req.original_input or "").strip()
        her_emission = (req.her_emission or "").strip()
    if not original_input or not her_emission:
        raise HTTPException(status_code=400, detail="no conversation context")
    return _guala.apply_teacher_correction(
        original_input=original_input, her_emission=her_emission,
        correct=False, corrected_text=req.corrected_text, source=req.source,
        emission_id=req.emission_id, story=req.story,
        temporal=req.temporal, sensory_freetext=req.sensory_freetext)


# ── GL-CMD-73: Curriculum endpoint ─────────────────────────────

class LoadCorpusRequest(BaseModel):
    corpus_id: str
    title: str
    url: Optional[str] = None      # fetch from URL if provided
    lines: Optional[list] = None   # pre-fetched lines (skip URL fetch)
    source: Optional[str] = None   # adapter name, e.g. "gutenberg"
    book_id: Optional[int] = None  # source-specific ID (gutenberg book ID)


async def _run_load_job(job_id: str, corpus_id: str, title: str, lines: list):
    """Asyncio background task (GL-CMD-74): delegates to substrate fire-and-forget,
    polls progress, updates web-container job registry to completion."""
    import asyncio as _aio
    from dsf_ai_service.curriculum import job_registry as _jr
    client = _get_substrate_client()

    # Tell substrate to start loading (returns immediately with "queued")
    try:
        substrate_resp = await client.call(
            "load_corpus",
            corpus_id=corpus_id,
            title=title,
            lines=lines,
            timeout=30.0,
        )
    except Exception as e:
        _jr.mark_failed(job_id, f"substrate call failed: {e}")
        return

    _jr.mark_running(job_id)

    # Poll substrate until complete or failed
    poll_interval = 5.0
    deadline = _aio.get_event_loop().time() + 600.0  # 10 min hard stop
    while _aio.get_event_loop().time() < deadline:
        await _aio.sleep(poll_interval)
        try:
            status = await client.call("corpus_status", corpus_id=corpus_id, timeout=10.0)
        except Exception as e:
            # Substrate unreachable — keep trying
            continue

        n_fed = status.get("n_fed", 0)
        _jr.update_progress(job_id, n_fed)

        if status.get("status") == "complete":
            _jr.mark_complete(job_id, result=status)
            return
        elif status.get("status") == "failed":
            _jr.mark_failed(job_id, error=status.get("error", "unknown"), partial_n_fed=n_fed)
            return
        # status == "running" or "queued" — keep polling

    # Timed out
    _jr.mark_failed(job_id, error="load job timed out after 600s")


@app.post("/api/v1/curriculum/load_corpus",
          dependencies=[Depends(_api_key_dep)],
          status_code=202)
async def load_corpus(req: LoadCorpusRequest):
    """GL-CMD-74: Async curriculum load — returns 202 immediately.
    Poll GET /api/v1/curriculum/load_corpus/job/{job_id} for progress."""
    import asyncio as _aio
    from dsf_ai_service.curriculum import job_registry as _jr

    # Conflict detection: single in-flight job per substrate
    active = _jr.get_active_job()
    if active:
        return JSONResponse(
            status_code=409,
            content={
                "error": "conflict",
                "message": "a corpus load job is already in flight",
                "existing_job_id": active["job_id"],
                "existing_corpus_id": active["corpus_id"],
                "state": active["state"],
            },
        )

    # Resolve lines (synchronously — fast path, 30s timeout)
    if req.lines:
        lines = [str(l) for l in req.lines if l]
    elif req.source == "gutenberg" and req.book_id is not None:
        from dsf_ai_service.curriculum.adapters.gutenberg import GutenbergAdapter
        from dsf_ai_service.curriculum.allowlist import CorpusSourceNotAllowed
        try:
            adapter = GutenbergAdapter(book_id=req.book_id)
            loop = _aio.get_event_loop()
            lines = await loop.run_in_executor(None, adapter.fetch_normalized)
        except CorpusSourceNotAllowed as e:
            raise HTTPException(status_code=403, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"fetch failed: {e}")
    elif req.url:
        from dsf_ai_service.curriculum.gutenberg_adapter import fetch_and_parse
        try:
            loop = _aio.get_event_loop()
            lines, _ = await loop.run_in_executor(None, fetch_and_parse, req.url)
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"fetch failed: {e}")
    else:
        raise HTTPException(status_code=400, detail="either url, lines, or source+book_id required")

    if not lines:
        raise HTTPException(status_code=400, detail="no sentences extracted")

    # Create job in registry
    job = _jr.create_job(corpus_id=req.corpus_id, n_sentences=len(lines))
    job_id = job["job_id"]

    # Kick off background asyncio task
    _schedule_mutating_background(
        lambda: _run_load_job(job_id, req.corpus_id, req.title, lines),
        name=f"corpus-load-{job_id}",
    )

    return {
        "job_id": job_id,
        "corpus_id": req.corpus_id,
        "n_sentences": len(lines),
        "state": "queued",
    }


@app.get("/api/v1/curriculum/load_corpus/job/{job_id}",
         dependencies=[Depends(_api_key_dep)])
async def get_load_corpus_job(job_id: str):
    """GL-CMD-74: Poll status of a corpus load job."""
    from dsf_ai_service.curriculum import job_registry as _jr
    job = _jr.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"job {job_id!r} not found")
    return {k: v for k, v in job.items() if not k.startswith("_")}


@app.get("/api/v1/curriculum/corpus_status/{corpus_id}", dependencies=[Depends(_api_key_dep)])
async def corpus_status(corpus_id: str):
    """Substrate-side corpus load status (GL-CMD-73 compatibility)."""
    if _is_remote():
        client = _get_substrate_client()
        return await client.call("corpus_status", corpus_id=corpus_id)
    raise HTTPException(status_code=501, detail="not implemented for local mode")


@app.get("/v7/state")
async def v7_state(session_id: str = "default"):
    if _is_remote():
        client = _get_substrate_client()
        return await client.call("v7_state", session_id=session_id)
    if _guala is None:
        raise HTTPException(status_code=503, detail={
            "error": "guala_not_ready",
            "retry_after_seconds": 10,
            "message": "she is still loading — try again in a moment"
        })
    import asyncio as _aio, time as _t7
    from dsf_ai_service.substrate.v7_engine import _sessions, _sessions_lock
    def _do_state():
        _t0 = _t7.time()
        with _sessions_lock:
            session = _sessions.get(session_id)
        if session is None:
            return None
        _t1 = _t7.time()
        result = session.get_state(engine=_guala)
        _t2 = _t7.time()
        print(f"[v7-state] sid={session_id} session={(_t1-_t0)*1000:.0f}ms "
              f"get_state={(_t2-_t1)*1000:.0f}ms total={(_t2-_t0)*1000:.0f}ms")
        return result
    result = await _aio.get_event_loop().run_in_executor(None, _do_state)
    if result is None:
        raise HTTPException(status_code=404, detail="v7 session not found")
    return result

@app.post("/v7/quiet")
async def v7_quiet(session_id: str = "default", n_ticks: int = 10):
    """Quiet ticks — substrate's Default Mode. Replay + consolidation."""
    if _is_remote():
        client = _get_substrate_client()
        return await client.call("v7_quiet",
                                 session_id=session_id, n_ticks=n_ticks)
    if _guala is None:
        raise HTTPException(status_code=503, detail={
            "error": "guala_not_ready",
            "retry_after_seconds": 10,
            "message": "she is still loading — try again in a moment"
        })
    from dsf_ai_service.substrate.v7_engine import get_or_create_session, save_session
    capped_ticks = min(n_ticks, 50)
    def _do_quiet():
        session = get_or_create_session(session_id, engine=_guala)
        results = session.quiet_tick(capped_ticks)
        total_replayed = sum(len(r["replayed"]) for r in results)
        total_commits = sum(len(r["commits"]) for r in results)
        save_session(session)
        return {"session_id": session_id, "ticks": len(results),
                "replayed": total_replayed, "commits": total_commits}
    result = await _run_lifecycle_executor(_do_quiet)
    return result


@app.post("/v7/save")
async def v7_save(session_id: str = "default"):
    """Manual save — Joe can hit this before risky operations."""
    if _is_remote():
        client = _get_substrate_client()
        return await client.call("v7_save", session_id=session_id)
    if _guala is None:
        raise HTTPException(status_code=503, detail={
            "error": "guala_not_ready",
            "retry_after_seconds": 10,
            "message": "she is still loading — try again in a moment"
        })
    from dsf_ai_service.substrate.v7_engine import get_or_create_session, save_session
    def _do_save():
        session = get_or_create_session(session_id, engine=_guala)
        save_session(session)
        data = session.to_json()
        return {"saved": True, "session_id": session_id,
                "schema_version": data.get("schema_version"),
                "tick": data.get("tick"),
                "n_sections": len(data.get("sections", {})),
                "vocab_size": sum(len(v) for v in session.vocab.values())}
    try:
        return await _run_lifecycle_executor(_do_save)
    except Exception as e:
        return {"saved": False, "error": str(e)}

@app.get("/v7/persistence")
async def v7_persistence(session_id: str = "default"):
    """Check persistence health — is session state on disk?"""
    import os, json as _json
    from dsf_ai_service.substrate.v7_engine import STATE_DIR
    path = os.path.join(STATE_DIR, f"{session_id}.json")
    if not os.path.exists(path):
        return {"on_disk": False, "session_id": session_id, "path": path}
    try:
        stat = os.stat(path)
        with open(path) as f:
            data = _json.load(f)
        return {
            "on_disk": True, "session_id": session_id,
            "file_size_bytes": stat.st_size,
            "last_modified": stat.st_mtime,
            "schema_version": data.get("schema_version"),
            "tick": data.get("tick"),
            "n_sections": len(data.get("sections", {})),
        }
    except Exception as e:
        return {"on_disk": True, "error": str(e)}

@app.get("/v6/events_histogram")
async def v6_events_histogram(source: str = "diary"):
    """Histogram of event types. GL-CMD-EVENT-RETENTION-FIX-172 R5:
    source='diary' (default) reads the durable, full-width, 7-day diary
    (dsf_ai_service/v4/gualaloom_v5_engine.py Guala.DIARY_DIR). source=
    'replay' (or 'events'/'events_log') reads the original narrow-
    whitelist crash-replay log (events.log) — byte-identical to this
    endpoint's pre-172 behavior, preserved for any caller that explicitly
    asks for it; no existing caller breaks since the response shape
    (total/histogram) is unchanged either way."""
    import os as _os
    from collections import Counter as _Counter

    def _histogram_from_lines(lines_iter):
        hist = _Counter()
        total = 0
        for line in lines_iter:
            line = line.strip()
            if not line:
                continue
            try:
                ev = json.loads(line)
                hist[ev.get("type", "unknown")] += 1
                total += 1
            except Exception:
                hist["parse_error"] += 1
        return total, hist

    if source in ("replay", "events", "events_log"):
        log_path = _os.path.join(STATE_DIR, "events.log")
        if not _os.path.exists(log_path):
            return {"error": "no events log", "source": "replay"}
        with open(log_path) as f:
            total, hist = _histogram_from_lines(f)
        return {"total": total, "histogram": dict(hist.most_common()), "source": "replay"}

    # default: diary (R5) — aggregate every retained daily file (<=7 days, R2)
    diary_dir = _os.path.join(STATE_DIR, "diary")
    if not _os.path.isdir(diary_dir):
        return {"error": "no diary", "source": "diary"}
    combined_hist = _Counter()
    combined_total = 0
    for fname in sorted(_os.listdir(diary_dir)):
        if not fname.endswith(".log"):
            continue
        with open(_os.path.join(diary_dir, fname)) as f:
            day_total, day_hist = _histogram_from_lines(f)
        combined_total += day_total
        combined_hist.update(day_hist)
    return {"total": combined_total, "histogram": dict(combined_hist.most_common()),
            "source": "diary"}


# ════════════════════════════════════════════════════════════════
# Health check
# ════════════════════════════════════════════════════════════════

_init_complete = False  # V2: health gate
_init_error = None
# GL-SPC-SUBSTRATE-TRUE Change 1 review (2026-07-16): a NAMED boot halt
# (integrity failure, P4) must be externally visible — before this, the halt
# was caught by _eager_init and /ready kept answering 200, leaving a
# healthy-looking zombie serving no substrate.  When set, /ready and
# /ready/guala answer 503 with the halt reason.
_boot_halted = None


def _classify_boot_halt(error):
    """Return the named-halt label for a P4 boot-halt exception, else None."""
    try:
        from dsf_ai_service.substrate.window_manager import (
            WindowStoreIntegrityHalt,
        )
        from dsf_ai_service.v4.gualaloom_v5_engine import (
            GualaBootIdentityUnreadableHalt,
            GualaBootStateIntegrityHalt,
        )
    except ImportError:
        return None
    named = (WindowStoreIntegrityHalt, GualaBootIdentityUnreadableHalt,
             GualaBootStateIntegrityHalt)
    if isinstance(error, named):
        return f"{type(error).__name__}: {error}"
    return None
_BOOT_START = time.time()   # module load time — for elapsed_ms in readiness responses
_LIFESPAN_STARTED = False   # set True as soon as startup event fires

@app.on_event("startup")
async def startup():
    global _init_complete, _init_error, _LIFESPAN_STARTED
    _LIFESPAN_STARTED = True   # shallow-ready gate: uvicorn is up
    # GL-CMD-HOTFIX-BUNDLE-95 item 4: build identity in the boot banner —
    # the running code must name its own commit.
    try:
        with open("/BUILD_INFO") as _bf:
            print(f"[build] {' '.join(_bf.read().split())}")
    except OSError:
        print("[build] BUILD_INFO absent (image predates -95 build stamp)")
    result = initialize_integrity()
    print(f"[DSF-AI] Integrity initialized: {result['files_present']}/{result['files_checked']} files hashed")

    # GL-ARCH-FRONTEND-SPLIT: in remote mode, skip in-process substrate boot
    if _is_remote():
        _init_complete = True
        print(f"[DSF-AI] SUBSTRATE_MODE=remote — substrate runs in separate process")
        return

    # Embedded mode: print the T1 boot banner before _gl_init fires
    print("[app] Booting substrate in-process...")

    # Uvicorn owns SIGTERM/SIGINT and runs the async lifespan shutdown below.
    # A synchronous signal handler cannot drain asyncio-owned mutations and
    # previously performed a second, unsealed root save after deploy sealing.

    # V2 EAGER INIT: initialize in background so health check passes immediately
    import asyncio
    async def _eager_init():
        global _init_complete, _init_error, _boot_halted
        t0 = time.time()
        try:
            await _run_lifecycle_executor(_boot_generation_and_guala)
            # The a8277fa boot pre-warm used to live HERE.  Removed per spec
            # v3 STT staging (acceptance criterion 7): the whisper worker/
            # model must spawn at steady state only, after readiness, never
            # during boot — see _kick_speech_prewarm_after_ready below,
            # called strictly after _init_complete flips.
            # GLEW cutover: construct the new conversation engine once, here,
            # only when explicitly enabled. Fail-closed: a construction failure
            # propagates and fails startup loudly rather than leaving the app
            # serving with the flag on but no engine (which _run_glew_converse_turn
            # would then reject per-turn anyway).
            if _GLEW_ENGINE_ENABLED:
                print("[glew] GLEW_CONVERSATION_ENGINE_ENABLED=on -- constructing "
                      "new ProductionCleanConversationEngine")
                await _run_lifecycle_executor(_boot_glew_conversation_engine)
        except Exception as error:
            _init_error = str(error)
            halt = _classify_boot_halt(error)
            if halt is not None:
                # NAMED P4 boot halt: flip the readiness surface so the
                # halt is externally visible (503, never a healthy zombie).
                _boot_halted = halt
                print(f"[DSF-AI] BOOT HALTED (named, readiness now 503): {halt}")
            print(f"[DSF-AI] Guala initialization FAILED: {error}")
            raise
        else:
            dt = time.time() - t0
            print(f"[DSF-AI] Guala initialized in {dt:.1f}s")
            _init_complete = True
            # STT staging (spec v3, acceptance criterion 7): pre-warm the
            # transducer only NOW — boot is over, readiness is flipped, and
            # the kick runs on the speech executor, so the worker spawn can
            # never compete with boot for memory again (2026-07-16 OOM).
            _kick_speech_prewarm_after_ready()
    _start_app_lifecycle_task(_eager_init(), name="guala-eager-init")

    # Server-side background replay for v7 sessions
    # GL-BUG-V7-SESSION-LEAK (Joe, 2026-07-06): _sessions never evicted
    # anything -- every page load/reload creates a new session_id, and this
    # loop kept quiet_tick+save-ing every one of them, forever, every 15s,
    # for the life of the container. Confirmed live: 128 accumulated
    # session files going back to 2026-06-08, 1.4GB total, with tonight's
    # active sessions alone ~20MB EACH -- re-serialized to disk every 15s
    # regardless of whether anyone was still using them. That's real CPU
    # (serializing tens of MB isn't free) and real EFS write bandwidth,
    # competing with the same narrow storage throughput her actual memory
    # saves already contend for (see the hot-save latency investigation
    # earlier tonight). EVICT_AFTER_SECONDS stops the recurring per-15s tax
    # for genuinely abandoned sessions (one final save, then drop from
    # memory -- reloads from disk fine if that session_id ever reconnects).
    # RETENTION_DAYS bounds the disk itself, same policy this file already
    # uses for the diary (DIARY_RETENTION_DAYS=7) -- old test/dev session
    # files here go back a MONTH with nothing removing them ever.
    import asyncio
    V7_SESSION_EVICT_AFTER_SECONDS = 3600  # 1 hour idle -> stop background-ticking it
    # GL-BUG-V7-SESSION-LEAK follow-up (Joe, 2026-07-06): 7 days (matching
    # DIARY_RETENTION_DAYS) was still too generous given each session file
    # runs ~20MB even after the atlas-cap fix above -- confirmed live, 71
    # files/1.2GB survived a 7-day cutoff. Cut hard per Joe's explicit
    # "much more aggressively" call: 1 day is enough to resume a same-day
    # browser tab, not enough to let a month of abandoned tabs pile up
    # gigabytes again.
    V7_SESSION_RETENTION_DAYS = 1
    _v7_last_prune_day = [None]

    def _prune_old_v7_session_files():
        from dsf_ai_service.substrate.v7_engine import STATE_DIR as V7_STATE_DIR
        cutoff = time.time() - V7_SESSION_RETENTION_DAYS * 86400
        removed, freed_bytes = 0, 0
        try:
            for fname in os.listdir(V7_STATE_DIR):
                if not (fname.endswith(".json") or fname.endswith(".json.tmp")
                        or fname.endswith(".events.jsonl")):
                    continue
                fpath = os.path.join(V7_STATE_DIR, fname)
                try:
                    st = os.stat(fpath)
                    if st.st_mtime < cutoff:
                        freed_bytes += st.st_size
                        os.remove(fpath)
                        removed += 1
                except OSError:
                    pass
        except OSError as e:
            print(f"[v7-prune] scan failed: {e}")
            return
        if removed:
            print(f"[v7-prune] removed {removed} session files older than "
                  f"{V7_SESSION_RETENTION_DAYS}d, freed {freed_bytes/1e6:.1f}MB")

    async def _background_replay():
        """Run quiet_tick on idle sessions every 15s; evict long-abandoned
        sessions from memory; prune disk files past retention once/day."""
        from dsf_ai_service.substrate.v7_engine import (
            _sessions, _sessions_lock, save_session,
        )
        while True:
            await asyncio.sleep(15)
            try:
                today = time.strftime("%Y-%m-%d", time.gmtime())
                if _v7_last_prune_day[0] != today:
                    _v7_last_prune_day[0] = today
                    await _run_lifecycle_executor(
                        _prune_old_v7_session_files)
                with _sessions_lock:
                    session_ids = list(_sessions.keys())
                for sid in session_ids:
                    with _sessions_lock:
                        session = _sessions.get(sid)
                    if session is None:
                        continue
                    idle = time.time() - getattr(session, '_last_converse_time', 0)
                    if idle > V7_SESSION_EVICT_AFTER_SECONDS:
                        try:
                            await _run_lifecycle_executor(save_session, session)
                            with _sessions_lock:
                                _sessions.pop(sid, None)
                            print(f"[v7-evict] session={sid} idle={idle:.0f}s "
                                  f"-- final save, dropped from memory")
                        except Exception:
                            pass
                        continue
                    if idle > 30:
                        try:
                            results = session.quiet_tick(3)
                            total_c = sum(len(r.get("commits", [])) for r in results)
                            if total_c > 0:
                                print(f"[v7-replay] session={sid}: {total_c} commits from replay")
                            await _run_lifecycle_executor(save_session, session)
                        except Exception:
                            pass
            except Exception:
                pass
    _start_app_lifecycle_task(_background_replay(), name="v7-background-replay")

    # N2: Periodic save + backup in executor (never blocks event loop)
    # GL-CMD-DEEP-STORE-PHYSICS-86 P2: hot/cold split.
    # Hot: small stores every 60s (target <5s). Cold: full state every 30 min.
    def _do_hot_save_and_compact():
        """Hot-lane: small stores only + event compact. Target <5s."""
        with _guala.persistence_transaction():
            t0 = time.time()
            pre_size = _guala.events_log_size(STATE_DIR)
            _guala.save_hot_state(STATE_DIR)
            t1 = time.time()
            _guala.compact_events(STATE_DIR, keep_after_offset=pre_size)
            t2 = time.time()
        total_dt = t2 - t0
        print(f"[save-hot] {total_dt:.2f}s core={t1-t0:.2f}s compact={t2-t1:.2f}s")
        return total_dt

    def _do_save_and_compact(write_wave: bool = False):
        """Cold lane: one full+compact+optional snapshot transaction."""
        with _guala.persistence_transaction():
            t0 = time.time()
            pre_size = _guala.events_log_size(STATE_DIR)
            results = _guala.save_full_state(STATE_DIR)
            t1 = time.time()
            _guala.compact_events(STATE_DIR, keep_after_offset=pre_size)
            t2 = time.time()
            snapshot_dir = None
            snapshot_dt = 0.0
            if write_wave:
                t3 = time.time()
                # snapshot_state performs the one required WaveAtlas write;
                # keeping it inside this outer transaction prevents another
                # save generation from entering between save and snapshot.
                snapshot_dir = _guala.snapshot_state(
                    STATE_DIR, reason="periodic")
                snapshot_dt = time.time() - t3
        core_dt = t1 - t0
        compact_dt = t2 - t1
        grids_dt = results.get("_grids_dt", 0.0) if isinstance(results, dict) else 0.0
        if write_wave:
            total_dt = t2 - t0 + snapshot_dt
            print(f"[save] {total_dt:.2f}s core={core_dt:.2f}s grids={grids_dt:.2f}s "
                  f"snapshot={snapshot_dt:.2f}s compact={compact_dt:.2f}s")
            print(f"[v6] Snapshot: {snapshot_dir}")
        else:
            total_dt = t2 - t0
            print(f"[save] {total_dt:.2f}s core={core_dt:.2f}s grids={grids_dt:.2f}s "
                  f"wave=skip compact={compact_dt:.2f}s")
        return total_dt

    async def _periodic_v6_save():
        save_count = 0
        _last_cold_wall = 0.0   # wall-clock of last cold save
        loop = asyncio.get_event_loop()
        while True:
            await asyncio.sleep(60)
            if _guala is None:
                continue
            now = loop.time()
            do_cold = (now - _last_cold_wall) >= 1800  # 30-min staleness bound
            do_wave = save_count > 0 and save_count % 10 == 0
            try:
                if do_cold:
                    await _run_lifecycle_executor(
                        _do_save_and_compact, do_wave)
                    _last_cold_wall = loop.time()
                else:
                    await _run_lifecycle_executor(_do_hot_save_and_compact)
            except Exception as e:
                print(f"[save] error: {e}")
            finally:
                # GL-CMD-SAVE-CONTAINMENT-91: save_count in finally — wave/snapshot
                # exceptions can never jam the counter at #10.
                save_count += 1
    _start_app_lifecycle_task(_periodic_v6_save(), name="periodic-v6-save")

    # GL-CMD-SAVE-TRUTH-84 (retired 2026-07-09): this ran _backup_to_s3 --
    # the SAME upload as _daily_s3_backup just above -- every hour,
    # unconditionally, uncompressed. Real, live contributor to the S3
    # bloat found and cleaned up tonight (~95 near-duplicate guala/
    # <timestamp>/ snapshot folders, ~5.6 GiB, matching roughly 4 days x
    # 24/day). Joe's explicit call tonight: one backup a day, not one an
    # hour "complementing" a daily one that already covers the same
    # state. _daily_s3_backup (above) plus the boot-time backup in
    # _eager_init already give a real daily cadence without this.

    # GL-CMD-74: Job registry GC — expire old jobs every 60 seconds
    async def _job_registry_gc():
        from dsf_ai_service.curriculum import job_registry as _jr
        while True:
            await asyncio.sleep(60)
            try:
                n = _jr.gc_expired()
                if n > 0:
                    print(f"[job-gc] Evicted {n} expired job(s)")
            except Exception:
                pass
    _start_app_lifecycle_task(_job_registry_gc(), name="job-registry-gc")

    # GL-CMD-WAVE-SEMANTICS-85 Part D.2: S3 lifecycle policy at startup
    # hourly backups expire 7d, auto/ dailies expire 60d, named restores permanent
    #
    # 2026-07-10: this function runs on EVERY boot and OVERWRITES the
    # bucket's entire lifecycle config -- confirmed root cause of a
    # storage config fix silently disappearing twice tonight after
    # routine deploys. The bucket has versioning Enabled; the original
    # 3 rules here only ever set Expiration (which just adds a delete
    # marker on a versioned bucket, never reclaiming bytes), with no
    # NoncurrentVersionExpiration anywhere -- root cause of a real,
    # already-once-manually-purged 0.3GB->11.7TB runaway (2026-06-26 to
    # 2026-07-09). Extended to match the corrected policy applied
    # directly tonight: NoncurrentVersionExpiration on every rule, plus
    # coverage for 3 previously-uncovered prefixes found actually
    # growing (guala/events/, guala/checkpoints/, guala/UNPAUSE-PRE-,
    # alb-access-logs/), plus a bucket-wide noncurrent/delete-marker
    # catch-all for anything not explicitly listed. This is now the
    # single source of truth for this bucket's lifecycle -- any future
    # AWS-console/CLI-only change here will be silently reverted on the
    # next deploy, same as tonight, unless it's also made here.
    def _apply_s3_lifecycle():
        try:
            import boto3 as _b3
            _s3 = _b3.client("s3", region_name="us-east-1")
            _s3.put_bucket_lifecycle_configuration(
                Bucket="dsf-ai-site-backups",
                LifecycleConfiguration={
                    "Rules": [
                        {
                            "ID": "guala-hourly-expire-7d",
                            "Status": "Enabled",
                            "Filter": {"Prefix": "guala/2"},  # date-stamped hourly: guala/2026-...
                            "Expiration": {"Days": 7},
                            "NoncurrentVersionExpiration": {"NoncurrentDays": 7},
                        },
                        {
                            "ID": "guala-auto-expire-60d",
                            "Status": "Enabled",
                            "Filter": {"Prefix": "guala/auto/"},
                            "Expiration": {"Days": 60},
                            "NoncurrentVersionExpiration": {"NoncurrentDays": 60},
                        },
                        {
                            "ID": "guala-wave-migrate-expire-90d",
                            "Status": "Enabled",
                            "Filter": {"Prefix": "guala/wave_migrate_pre/"},
                            "Expiration": {"Days": 90},
                            "NoncurrentVersionExpiration": {"NoncurrentDays": 90},
                        },
                        {
                            "ID": "guala-events-expire-7d",
                            "Status": "Enabled",
                            "Filter": {"Prefix": "guala/events/"},
                            "Expiration": {"Days": 7},
                            "NoncurrentVersionExpiration": {"NoncurrentDays": 7},
                        },
                        {
                            "ID": "guala-checkpoints-expire-7d",
                            "Status": "Enabled",
                            "Filter": {"Prefix": "guala/checkpoints/"},
                            "Expiration": {"Days": 7},
                            "NoncurrentVersionExpiration": {"NoncurrentDays": 7},
                        },
                        {
                            "ID": "guala-unpause-pre-expire-30d",
                            "Status": "Enabled",
                            "Filter": {"Prefix": "guala/UNPAUSE-PRE-"},
                            "Expiration": {"Days": 30},
                            "NoncurrentVersionExpiration": {"NoncurrentDays": 30},
                        },
                        {
                            "ID": "guala-alb-access-logs-expire-90d",
                            "Status": "Enabled",
                            "Filter": {"Prefix": "alb-access-logs/"},
                            "Expiration": {"Days": 90},
                            "NoncurrentVersionExpiration": {"NoncurrentDays": 90},
                        },
                        {
                            "ID": "guala-bucketwide-noncurrent-catchall-30d",
                            "Status": "Enabled",
                            "Filter": {},
                            "NoncurrentVersionExpiration": {"NoncurrentDays": 30},
                            "Expiration": {"ExpiredObjectDeleteMarker": True},
                        },
                    ]
                },
            )
            print("[85-D2] S3 lifecycle policy applied: 8 rules (7d/60d/90d expirations "
                  "+ noncurrent-version reclaim on all, bucket-wide catch-all)")
        except Exception as _le:
            print(f"[85-D2] S3 lifecycle policy failed (non-fatal): {_le}")
    # Bucket lifecycle is infrastructure state.  Application boot must never
    # mutate it asynchronously or overwrite an operator-reviewed policy.


_last_s3_backup = None  # D3: tracked for persistence_health

def _recover_from_local_generations(state_dir):
    """GL-FIX-ATOMIC-SAVE-GENERATIONS: try to recover from the newest complete
    LOCAL atomic generation, then older ones. Returns the recovered manifest
    dict (and materializes it into ``state_dir``) or None if no local
    generation validates. NEVER touches S3 -- Joe's standing order is that old
    state can never be silently recalled; S3 is a human-only, explicit path."""
    try:
        from dsf_ai_service.substrate import atomic_state_generation as _asg
    except Exception as _imp_err:
        print(f"[GualaLoom] generation recovery unavailable: {_imp_err}")
        return None

    def _load_test(gen_dir):
        probe = Guala()
        for cid, cdata in SEED_CORPORA.items():
            probe.add_corpus(cid, cdata["title"], cdata["lines"])
        probe.load_full_state(gen_dir)
        ok = bool(getattr(probe, "_load_successful", False))
        _strict_discard_guala(probe, reason="generation load-test probe")
        return ok

    return _asg.recover_from_generations(state_dir, _load_test, log=print)


def _restore_from_s3(state_dir):
    """P0: Restore state files from most recent S3 backup.

    HUMAN-ONLY PATH. Reachable only via the explicit FORCE_S3_RESTORE=1 env
    flag (set by a human on the task definition, one-shot). No automatic boot
    path may call this: Joe's standing order (2026-07-15) is that old state can
    never be silently recalled. See the guard test
    test_no_silent_s3_restore.py, which fails the build if any automatic caller
    is reintroduced."""
    import boto3
    s3 = boto3.client("s3", region_name="us-east-1")
    bucket = "dsf-ai-site-backups"
    # Find most recent backup prefix — date-stamped folders only (exclude auto/, events/, etc.)
    resp = s3.list_objects_v2(Bucket=bucket, Prefix="guala/", Delimiter="/")
    import re as _re
    _date_pat = _re.compile(r"guala/\d{4}-\d{2}-\d{2}_")
    prefixes = sorted(
        [p["Prefix"] for p in resp.get("CommonPrefixes", [])
         if _date_pat.match(p["Prefix"])],
        reverse=True)
    if not prefixes:
        raise RuntimeError("No S3 backups found")
    latest = prefixes[0]
    print(f"[GualaLoom] Restoring from {latest}")
    # Download all files
    objs = s3.list_objects_v2(Bucket=bucket, Prefix=latest)
    for obj in objs.get("Contents", []):
        key = obj["Key"]
        filename = key[len(latest):]
        if "/" in filename:
            # pictures/xxx.npy → state/pictures/xxx.npy
            subdir = os.path.join(state_dir, os.path.dirname(filename))
            os.makedirs(subdir, exist_ok=True)
        # 2026-07-09: _backup_to_s3 now gzips the plain .json files before
        # upload (guala_core.json -> guala_core.json.gz on S3) -- undo
        # that here so load_full_state finds the plain filenames it
        # expects locally, same fix as substrate_runner.py's equivalent
        # restore path for the guala/auto/ backups. Older backups
        # written before this change are still plain and fall through
        # to the else branch unchanged.
        if filename.endswith(".json.gz"):
            real_filename = filename[:-3]
            local_path = os.path.join(state_dir, real_filename)
            import gzip as _gzip
            obj_body = s3.get_object(Bucket=bucket, Key=key)["Body"].read()
            with open(local_path, "wb") as f:
                f.write(_gzip.decompress(obj_body))
        else:
            local_path = os.path.join(state_dir, filename)
            s3.download_file(bucket, key, local_path)
    print(f"[GualaLoom] Restored {len(objs.get('Contents', []))} files from S3")


def _backup_to_s3(state_dir):
    """V4/D3: Copy state files to S3 via boto3 (no aws CLI in container)."""
    global _last_s3_backup
    import boto3
    s3 = boto3.client("s3", region_name="us-east-1")
    bucket = "dsf-ai-site-backups"
    date_str = time.strftime("%Y-%m-%d_%H-%M-%S", time.gmtime())
    prefix = f"guala/{date_str}/"
    files = ["guala_core.json", "guala_needs.json", "guala_coordinator.json",
             "guala_atlas.json", "guala_sections.json", "guala_bucket.json",
             "guala_deep_atlas.json", "guala_visual.json", "guala_identity.json",
             "guala_sounds.json", "guala_videos.json",
             "guala_organism.pkl.gz", "guala_tapestry.pkl.gz"]  # GL-CMD-175 P1
    backed = 0
    for f in files:
        path = os.path.join(state_dir, f)
        if os.path.exists(path):
            try:
                if f.endswith(".json"):
                    # 2026-07-09: same fix as save_coordinator.py's S3
                    # mirror -- these plain JSON files (several MB each)
                    # were uploaded byte-for-byte; the .pkl.gz files
                    # below were already compressed. Compress in memory
                    # for the S3 copy only; the local EFS file this
                    # reads from stays plain, untouched.
                    import gzip as _gzip
                    import io as _io
                    with open(path, "rb") as _fh:
                        _raw = _fh.read()
                    _buf = _io.BytesIO(_gzip.compress(_raw))
                    s3.upload_fileobj(_buf, bucket, prefix + f + ".gz")
                else:
                    s3.upload_file(path, bucket, prefix + f)
                backed += 1
            except Exception as e:
                print(f"[DSF-AI] S3 backup {f} failed: {e}")
    # Also backup picture originals
    pic_dir = os.path.join(state_dir, "pictures")
    if os.path.isdir(pic_dir):
        for pf in os.listdir(pic_dir):
            try:
                s3.upload_file(os.path.join(pic_dir, pf), bucket, prefix + "pictures/" + pf)
            except Exception:
                pass
    _last_s3_backup = {
        "timestamp": date_str,
        "prefix": f"s3://{bucket}/{prefix}",
        "file_count": backed,
    }
    print(f"[DSF-AI] S3 backup: {backed} files to s3://{bucket}/{prefix}")
    return f"s3://{bucket}/{prefix}"


@app.on_event("shutdown")
async def shutdown():
    """Retire a sealed owner without ever writing a second generation."""
    global _generation_owner_lock
    import asyncio
    _fail_inflight_converse_tasks(
        "turn lost — server shut down mid-conversation, please resend")
    snapshot = _deployment_lifecycle.snapshot()
    if (snapshot["state"] == "RUNNING" and _guala is not None
            and _REQUIRE_SEALED_STATE):
        # Defense for an external stop that did not use the deploy route.  If
        # this cannot finish inside the platform stop allowance, the prior
        # immutable CURRENT remains authoritative; no torn pointer is exposed.
        import secrets
        try:
            await _quiesce_and_seal(secrets.token_hex(32))
            snapshot = _deployment_lifecycle.snapshot()
        except Exception as error:
            print(f"[shutdown] emergency generation seal failed: {error}")
            snapshot = _deployment_lifecycle.snapshot()
    elif snapshot["state"] == "RUNNING" and _guala is not None:
        # Local/non-production mode has no immutable recovery contract, but
        # still must prove its threads have stopped before interpreter exit.
        try:
            await _stop_app_lifecycle_tasks(timeout=120.0)
            import dsf_ai_service.substrate_runner as _sr
            await asyncio.to_thread(_sr.quiesce_background_loops, 120.0)
            from dsf_ai_service.speech_transducer import shutdown_speech_worker
            await asyncio.to_thread(shutdown_speech_worker, 30.0)
            await asyncio.to_thread(_guala.strict_shutdown, 120.0)
        except Exception as error:
            print(f"[shutdown] strict local quiescence failed: {error}")

    if snapshot["state"] == "SEALED":
        _deployment_lifecycle.retire()
    if _generation_owner_lock is not None:
        _generation_owner_lock.release()
        _generation_owner_lock = None


# ── GL-CMD-STDP-INTROSPECTION-EVE-20260707-v1: read-only STDP state ──
# Prerequisite for interpreting Phase 1 v2's parallel STDP/spike/membrane
# mechanism (GL-RPT-BLUEPRINT-PHASE-1-MERGED-C1-20260707-v2) before the
# shadow-mode test -- there is currently no way to see whether that
# mechanism is accumulating usable memory, since RECALL_BACKEND stays
# "legacy" throughout Phase 1 and nothing reads the new state yet.
# Never mutates substrate state. Auth reuses the existing _api_key_dep
# (GUALALOOM_API_KEY) admin gate rather than inventing a new
# DEBUG_ENDPOINTS_ENABLED flag -- functionally identical existing
# introspection endpoints (familiarity_debug, persistence_health,
# atlas_snapshot) already sit behind exactly this gate, so this joins
# that same protected surface instead of adding a second mechanism.

_STDP_EMISSION_THRESHOLD = 0.5  # per dispatch spec; distinct from brain.py's RECALL_ACTIVATION_THRESHOLD=0.3


def _stdp_snapshot_neuron(neuron, now_s: float) -> dict:
    """Briefly holds neuron._neuron_lock to copy out primitive state + a
    shallow dict copy of _incoming_synapse_weights -- released
    immediately after, never held across other neurons or any aggregate
    computation (dispatch requirement: brief per-neuron lock
    acquisition, not held across full iteration)."""
    with neuron._neuron_lock:
        weights = dict(neuron._incoming_synapse_weights)
        last_fire = neuron._last_fire_time_s
        membrane_potential = neuron.membrane_potential
        last_update = neuron.last_update_time_s
        refractory_until = neuron.refractory_until_s
        membrane_rest = neuron.membrane_rest
        tau_m_ms = neuron.tau_m_ms
        fire_count = neuron.chi_atlas.tick  # one record() call per fire -- see neuron.py _on_fire_bookkeeping
        # Phase 1 delivery plan Step 2: copy out the bounded recent-fire-
        # timestamp deque (list() of a deque under the lock is a cheap,
        # correct atomic-enough snapshot -- same convention as the dict()
        # copies above) and the breaker trip counter, for the real
        # windowed fire-rate metric (_fire_rate_window_metrics below).
        recent_fire_timestamps = list(neuron._recent_fire_timestamps)
        fire_breaker_trip_count = neuron._fire_breaker_trip_count
    dt_ms = (now_s - last_update) * 1000.0
    if dt_ms > 0 and tau_m_ms > 0:
        decay = math.exp(-dt_ms / tau_m_ms)
        decayed_potential = membrane_rest + (membrane_potential - membrane_rest) * decay
    else:
        decayed_potential = membrane_potential
    return {
        "neuron_id": neuron.neuron_id,
        "weights": weights,
        "last_fire_time_s": last_fire,
        "decayed_potential": decayed_potential,
        "refractory_until_s": refractory_until,
        "fire_count": fire_count,
        "recent_fire_timestamps": recent_fire_timestamps,
        "fire_breaker_trip_count": fire_breaker_trip_count,
    }


def _word_neuron_map_metrics(guala) -> dict:
    # dict(...) on a live dict is a single atomic C call (PyDict_Copy) --
    # safe against the spike-bus delivery thread's concurrent
    # _on_word_firing writes without needing a dedicated lock.
    word_map = dict(guala._word_neuron_map)
    neuron_map = dict(guala._neuron_word_map)
    sizes = [len(s) for s in word_map.values()]
    top_words = sorted(
        ((w, len(s)) for w, s in word_map.items()), key=lambda t: -t[1]
    )[:20]
    return {
        "word_neuron_map_size": len(word_map),
        "neuron_word_map_size": len(neuron_map),
        "avg_neurons_per_word": (sum(sizes) / len(sizes)) if sizes else 0.0,
        "median_neurons_per_word": statistics.median(sizes) if sizes else 0.0,
        "top_words_by_neuron_count": [
            {"word": w, "neuron_count": c} for w, c in top_words
        ],
        "words_with_only_one_neuron": sum(1 for s in sizes if s == 1),
    }


def _synapse_distribution_metrics(neuron_snapshots: list, default_weight: float) -> dict:
    all_entries = [
        (source_id, snap["neuron_id"], w)
        for snap in neuron_snapshots
        for source_id, w in snap["weights"].items()
    ]
    total = len(all_entries)
    sample = all_entries
    sampled = False
    if total > 100_000:
        import random
        sample = random.sample(all_entries, total // 10)
        sampled = True

    edges = [0.0, 0.05, 0.1, 0.25, 0.5, 1.0, 2.0, 5.0]
    hist = {f"[{edges[i]},{edges[i + 1]})": 0 for i in range(len(edges) - 1)}
    hist[f">={edges[-1]}"] = 0
    for _, _, w in sample:
        for i in range(len(edges) - 1):
            if edges[i] <= w < edges[i + 1]:
                hist[f"[{edges[i]},{edges[i + 1]})"] += 1
                break
        else:
            hist[f">={edges[-1]}"] += 1

    eps = 1e-9
    top10 = heapq.nlargest(10, all_entries, key=lambda t: t[2])
    return {
        "total_synapses_updated": total,
        "synapses_at_default_weight": sum(1 for _, _, w in all_entries if abs(w - default_weight) < eps),
        "synapses_strengthened": sum(1 for _, _, w in all_entries if w > default_weight + eps),
        "synapses_depressed": sum(1 for _, _, w in all_entries if w < default_weight - eps),
        "weight_histogram": hist,
        "weight_histogram_sampled_10pct": sampled,
        "top_10_strongest_synapses": [
            {"source_id": s, "target_id": t, "weight": w} for s, t, w in top10
        ],
    }


def _fire_event_metrics(neuron_snapshots: list, now_s: float, uptime_s: float) -> dict:
    total_fires = sum(s["fire_count"] for s in neuron_snapshots)
    ever_fired = sum(1 for s in neuron_snapshots if s["last_fire_time_s"] > 0)
    fired_last_minute = sum(
        1 for s in neuron_snapshots
        if s["last_fire_time_s"] > 0 and (now_s - s["last_fire_time_s"]) <= 60.0
    )
    return {
        "total_fire_events_since_boot": total_fires,
        "fires_per_second_since_boot": (total_fires / uptime_s) if uptime_s > 0 else 0.0,
        "fires_per_second_last_minute": fired_last_minute / 60.0,
        "neurons_that_have_ever_fired": ever_fired,
        "neurons_never_fired": len(neuron_snapshots) - ever_fired,
        "notes": [
            "fires_per_second_last_minute is an approximation: distinct "
            "neurons that fired at least once in the last 60s, divided by "
            "60 -- not a true event-rate (a neuron firing multiple times "
            "in the window is only counted once). No time-series counter "
            "exists, per this dispatch's own 'no historical time-series "
            "storage' constraint -- this is the best reading available "
            "from existing per-neuron state alone. IMPORTANT: this metric "
            "CANNOT detect a single neuron firing continuously (it "
            "saturates at 1/60 per neuron no matter how many times that "
            "neuron actually fired) -- this is exactly how the real "
            "2026-07-08/09 runaway-neuron incident (~3800 fires/sec, "
            "caught by chance) went unseen. See "
            "fire_rate_window_metrics below for a metric that can "
            "actually detect that failure class.",
        ],
    }


def _fire_rate_window_metrics(neuron_snapshots: list, neuron_word_map: dict) -> dict:
    """Phase 1 delivery plan Step 2: a REAL windowed fire-rate metric,
    designed specifically to detect the class of incident
    fires_per_second_last_minute above cannot see: a single neuron firing
    continuously at a high rate.

    Reads each neuron's own bounded recent-fire-timestamp deque
    (LoomNeuron._recent_fire_timestamps, maxlen=FIRE_BREAKER_WINDOW_N --
    see neuron.py) and computes the actual fire rate spanning that
    neuron's own last N fires, wherever/whenever they happened -- this is
    a true per-neuron event-rate over a real recent window, not an
    approximation. A neuron is flagged in runaway_neurons if that rate
    exceeds FIRE_BREAKER_CEILING_HZ -- the SAME threshold the live
    circuit breaker in neuron.py's _fire() uses to trip (see that file's
    reasoning comment) -- so this metric is a direct read of the
    breaker's own trip condition, not a separately-invented display
    threshold.

    Verification that this would have caught the real 2026-07-08/09
    incident: test_debug_stdp_state.py's
    test_fire_rate_window_metrics_flags_incident_reproduction builds a
    neuron snapshot with FIRE_BREAKER_WINDOW_N timestamps spaced at the
    incident's observed ~3800/sec and asserts this function flags it
    (while a neuron firing at a realistic STDP-driven rate is not
    flagged) -- run and passing locally (see test run output in the
    accompanying report)."""
    from dsf_ai_service.loom_model.neuron import (
        FIRE_BREAKER_CEILING_HZ, FIRE_BREAKER_WINDOW_N,
    )

    per_neuron = []
    for snap in neuron_snapshots:
        timestamps = snap.get("recent_fire_timestamps") or []
        rate_hz = None
        window_span_s = None
        if len(timestamps) >= 2:
            window_span_s = timestamps[-1] - timestamps[0]
            rate_hz = (
                (len(timestamps) - 1) / window_span_s
                if window_span_s > 0 else float("inf")
            )
        per_neuron.append({
            "neuron_id": snap["neuron_id"],
            "recent_fire_count_in_window": len(timestamps),
            "recent_window_span_s": window_span_s,
            "recent_fire_rate_hz": rate_hz,
            "fire_breaker_trip_count": snap.get("fire_breaker_trip_count", 0),
        })

    # "Saturated within a short window" (task's own phrasing) is exactly
    # rate_hz > ceiling restated in time terms: the window (of
    # FIRE_BREAKER_WINDOW_N fires) filled in less time than the ceiling
    # would allow. Only neurons whose deque is fully saturated (a full
    # window's worth of real history to judge, matching the breaker's
    # own "not enough history yet" guard) are eligible to be flagged.
    runaway = [
        p for p in per_neuron
        if p["recent_fire_count_in_window"] == FIRE_BREAKER_WINDOW_N
        and p["recent_fire_rate_hz"] is not None
        and p["recent_fire_rate_hz"] > FIRE_BREAKER_CEILING_HZ
    ]
    runaway_sorted = sorted(
        runaway,
        key=lambda p: (p["recent_fire_rate_hz"] if p["recent_fire_rate_hz"] != float("inf")
                       else float("inf")),
        reverse=True,
    )
    total_trips = sum(p["fire_breaker_trip_count"] for p in per_neuron)

    return {
        "window_n": FIRE_BREAKER_WINDOW_N,
        "ceiling_hz": FIRE_BREAKER_CEILING_HZ,
        "neurons_with_runaway_fire_pattern": len(runaway_sorted),
        "runaway_neurons": [
            {
                "neuron_id": p["neuron_id"],
                "recent_fire_rate_hz": p["recent_fire_rate_hz"],
                "recent_window_span_s": p["recent_window_span_s"],
                "word": neuron_word_map.get(p["neuron_id"]),
            }
            for p in runaway_sorted[:20]
        ],
        "total_fire_breaker_trips_since_boot_or_restore": total_trips,
        "notes": [
            "recent_fire_rate_hz is computed per-neuron from its own "
            f"bounded recent-fire-timestamp deque (last {FIRE_BREAKER_WINDOW_N} "
            "fires, wherever/whenever they happened) -- unlike "
            "fire_event_metrics.fires_per_second_last_minute (distinct "
            "neurons firing at least once per 60s), this detects a SINGLE "
            "neuron firing continuously at high rate -- the exact failure "
            "class of the 2026-07-08/09 incident. A neuron only appears "
            "in runaway_neurons once its window has fully saturated "
            f"({FIRE_BREAKER_WINDOW_N} real fires recorded) AND that "
            f"window's rate exceeds {FIRE_BREAKER_CEILING_HZ} Hz -- the "
            "same ceiling the live circuit breaker in neuron.py uses to "
            "skip outgoing propagation, so this list and the breaker's "
            "own trips agree by construction.",
        ],
    }


def _spike_bus_metrics(guala, now_s: float) -> dict:
    bus = guala._spike_bus
    if bus is None:
        return {
            "enabled": False,
            "notes": ["EVENT_DRIVEN_SUBSTRATE=0 -- no spike bus constructed."],
        }
    with bus._queue.mutex:
        pending = list(bus._queue.queue)
    return {
        "enabled": True,
        "spike_queue_depth": len(pending),
        "spikes_in_flight_delayed": sum(1 for p in pending if p.arrival_time > now_s),
        "total_spikes_injected_since_boot": bus.injected_count,
        "total_spikes_delivered_since_boot": bus.delivered_count,
        "spikes_dropped": bus.dropped_count,
    }


def _membrane_state_metrics(neuron_snapshots: list, neuron_word_map: dict, now_s: float) -> dict:
    potentials = [s["decayed_potential"] for s in neuron_snapshots]
    top20 = heapq.nlargest(20, neuron_snapshots, key=lambda s: s["decayed_potential"])
    return {
        "neurons_currently_above_emission_threshold": sum(1 for p in potentials if p > _STDP_EMISSION_THRESHOLD),
        "neurons_currently_in_refractory": sum(1 for s in neuron_snapshots if s["refractory_until_s"] > now_s),
        "mean_membrane_potential": (sum(potentials) / len(potentials)) if potentials else 0.0,
        "top_20_active_neurons": [
            {
                "neuron_id": s["neuron_id"],
                "potential": s["decayed_potential"],
                "word": neuron_word_map.get(s["neuron_id"]),
            }
            for s in top20
        ],
    }


def _ecs_task_def_best_effort() -> str:
    """Reads the ECS Fargate task metadata v4 endpoint (always present in
    a real deployed task, absent locally) instead of a deploy-script-
    injected env var -- avoids the chicken-and-egg problem of the task
    definition revision not being known until AFTER register-task-
    definition returns, and avoids adding another hardcoded value that
    can silently go stale (see GL-RPT-BLUEPRINT-PHASE-1-MERGED-C1-
    20260707-v2 finding 5 -- EXPECTED_IDENTITY already burned us on
    exactly this pattern once)."""
    uri = os.environ.get("ECS_CONTAINER_METADATA_URI_V4")
    if not uri:
        return "unknown (not running under ECS Fargate)"
    try:
        import urllib.request
        with urllib.request.urlopen(f"{uri}/task", timeout=0.3) as resp:
            data = json.loads(resp.read())
        return f"{data.get('Family', 'unknown')}:{data.get('Revision', 'unknown')}"
    except Exception:
        return "unknown (metadata fetch failed)"


def _build_stdp_snapshot(guala) -> dict:
    """All synchronous work for /debug/stdp_state, run off the event
    loop via run_in_executor (matches the shutdown() precedent above) so
    a slow query never blocks other requests being served concurrently
    -- the actual halt condition this dispatch calls out ('endpoint lock
    acquisition measurably slows substrate'). The only I/O in here is
    the ECS metadata call, bounded to a 0.3s socket timeout; everything
    else is in-memory and, at current substrate scale (dozens of
    neurons), sub-millisecond."""
    now_s = time.monotonic()
    uptime_s = time.time() - _BOOT_START
    result = {}
    log = logging.getLogger("guala.debug_endpoints")

    try:
        result["word_neuron_map"] = _word_neuron_map_metrics(guala)
    except Exception:
        log.exception("stdp_state: word_neuron_map metrics failed")
        result["word_neuron_map"] = {"error": "unavailable"}

    # Per-neuron isolation (not one try/except around the whole loop): a
    # neuron missing a field the loop expects -- e.g. an organism
    # restored from a guala_organism.pkl.gz saved before this field
    # existed, since pickle.load() reconstructs __dict__ directly and
    # never re-runs LoomNeuron.__init__() -- must not hide every OTHER
    # neuron's real data. First production run of this endpoint found
    # exactly this: see GL-RPT-STDP-INTROSPECTION-C1-20260707-v1 finding 1.
    neuron_snapshots = []
    neuron_snapshot_failures = 0
    neuron_snapshot_sample_error = None
    all_neurons = []
    try:
        all_neurons = guala._all_neurons()
    except Exception:
        log.exception("stdp_state: _all_neurons() failed")
    for n in all_neurons:
        try:
            neuron_snapshots.append(_stdp_snapshot_neuron(n, now_s))
        except Exception as e:
            neuron_snapshot_failures += 1
            if neuron_snapshot_sample_error is None:
                neuron_snapshot_sample_error = f"{type(e).__name__}: {e}"
            log.exception("stdp_state: snapshot failed for neuron %s",
                          getattr(n, "neuron_id", "?"))
    result["diagnostics"] = {
        "neurons_total": len(all_neurons),
        "neurons_snapshot_ok": len(neuron_snapshots),
        "neurons_snapshot_failed": neuron_snapshot_failures,
        "neuron_snapshot_sample_error": neuron_snapshot_sample_error,
    }

    from dsf_ai_service.loom_model.neuron import STDP_DEFAULT_SYNAPSE_WEIGHT
    try:
        result["synapse_weight_distribution"] = _synapse_distribution_metrics(
            neuron_snapshots, STDP_DEFAULT_SYNAPSE_WEIGHT)
    except Exception:
        log.exception("stdp_state: synapse distribution metrics failed")
        result["synapse_weight_distribution"] = {"error": "unavailable"}

    try:
        result["fire_event_metrics"] = _fire_event_metrics(neuron_snapshots, now_s, uptime_s)
    except Exception:
        log.exception("stdp_state: fire event metrics failed")
        result["fire_event_metrics"] = {"error": "unavailable"}

    try:
        fire_rate_neuron_word_map = dict(guala._neuron_word_map)
        result["fire_rate_window_metrics"] = _fire_rate_window_metrics(
            neuron_snapshots, fire_rate_neuron_word_map)
    except Exception:
        log.exception("stdp_state: fire rate window metrics failed")
        result["fire_rate_window_metrics"] = {"error": "unavailable"}

    try:
        result["spike_bus_metrics"] = _spike_bus_metrics(guala, now_s)
    except Exception:
        log.exception("stdp_state: spike bus metrics failed")
        result["spike_bus_metrics"] = {"error": "unavailable"}

    try:
        neuron_word_map_snapshot = dict(guala._neuron_word_map)
        result["membrane_state"] = _membrane_state_metrics(neuron_snapshots, neuron_word_map_snapshot, now_s)
    except Exception:
        log.exception("stdp_state: membrane state metrics failed")
        result["membrane_state"] = {"error": "unavailable"}

    try:
        result["substrate_identity"] = {
            "running_sha": os.environ.get("GIT_SHA", "unknown"),
            "task_def": _ecs_task_def_best_effort(),
            "identity_id": getattr(guala, "_guala_identity", None),
            "uptime_seconds": uptime_s,
            "EVENT_DRIVEN_SUBSTRATE": os.environ.get("EVENT_DRIVEN_SUBSTRATE", "1"),
            "RECALL_BACKEND": os.environ.get("RECALL_BACKEND", "legacy"),
        }
    except Exception:
        log.exception("stdp_state: substrate identity metrics failed")
        result["substrate_identity"] = {"error": "unavailable"}

    return result


@app.get("/debug/stdp_state", dependencies=[Depends(_api_key_dep)])
async def debug_stdp_state():
    """Read-only snapshot of Phase 1 v2's parallel STDP/spike/membrane
    state. See GL-CMD-STDP-INTROSPECTION-EVE-20260707-v1."""
    import asyncio

    if _guala is None:
        return JSONResponse(status_code=503, content={"error": "guala not loaded"})

    loop = asyncio.get_event_loop()
    snapshot = await loop.run_in_executor(None, _build_stdp_snapshot, _guala)
    return snapshot


@app.get("/debug/thread_dump", dependencies=[Depends(_api_key_dep)])
async def debug_thread_dump():
    """2026-07-09: real-time Python-level stack trace for every live
    thread, using only sys._current_frames() + traceback (stdlib, no
    profiler dependency, no container rebuild risk). Built to answer a
    real, live incident: CloudWatch + a direct ECS Exec /proc sample
    both confirmed ~1 full CPU core continuously busy in 1-2 specific OS
    threads inside this process, but py-spy isn't installed in the
    container and Python doesn't rename OS threads, so neither CloudWatch
    nor /proc could say WHICH function is actually running. This can.
    Read-only: sys._current_frames() only inspects existing frame
    objects, does not pause/signal/modify any thread."""
    import sys
    import threading
    import traceback

    id_to_name = {t.ident: t.name for t in threading.enumerate()}
    frames = sys._current_frames()
    out = {}
    for thread_id, frame in frames.items():
        out[str(thread_id)] = {
            "name": id_to_name.get(thread_id, "unknown"),
            "stack": traceback.format_stack(frame),
        }
    return out


@app.post("/debug/wal_compact", dependencies=[Depends(_api_key_dep)])
async def debug_wal_compact():
    """The verbatim lifetime-window store is retired from live cognition."""
    return JSONResponse(
        status_code=410,
        content={
            "error": "verbatim lifetime-window storage is retired",
            "memory_authority": "atlas_chi_krimelack_sections_organism",
        },
    )


@app.get("/health")
async def health():
    # Always return 200 for ALB liveness checks.
    result = {
        "status": "ok" if _init_complete else "initializing",
        "service": "dsf-ai",
        "version": "1.0.0",
        "ready": _init_complete,
    }
    # GL-CMD-LANGUAGE-SEED-PHASE2-GENERATOR-EVE-20260707-v1: report seed
    # load progress when a seed load was attempted (None otherwise --
    # matches current no-seed production behavior exactly).
    if _seed_load_progress is not None:
        result["seed_load"] = _seed_load_progress.as_dict()
    # STT staging telemetry (spec v3, acceptance criterion 7): worker state
    # and RSS-watchdog breach count.  Read-only snapshot — can never spawn
    # a worker or load a model from this path.
    result["speech"] = _speech_status_snapshot()
    result["auditory_pcm_transport"] = _auditory_pcm_streams.status()
    return result

@app.get("/ready")
async def ready():
    """Container readiness; sealed production never reports shallow success."""
    elapsed_ms = int((time.time() - _BOOT_START) * 1000)
    if _boot_halted is not None:
        # A NAMED P4 boot halt is never a healthy container.  503 makes the
        # orchestrator recycle/hold the task — the crash-loop IS the signal.
        return JSONResponse(
            status_code=503,
            content={
                "ready": False,
                "boot_halted": _boot_halted,
                "elapsed_ms": elapsed_ms,
            },
            headers={"Retry-After": "30"},
        )
    if _REQUIRE_SEALED_STATE:
        lifecycle_state = _deployment_lifecycle.snapshot()["state"]
        if lifecycle_state in {"QUIESCING", "SEALED"}:
            # The ALB uses this route as its target-health probe.  A
            # controlled deployment drain must remain process-alive long
            # enough to finish already-admitted neuron work and return its
            # signed seal, while ordinary mutation admission is already
            # closed by the lifecycle owner.  Returning HTTP 200 here keeps
            # ECS from killing that sole state owner mid-seal; ready=False
            # remains explicit, and deep readiness still fails because it
            # requires RUNNING.
            return {
                "ready": False,
                "draining": True,
                "lifecycle": lifecycle_state,
                "elapsed_ms": elapsed_ms,
            }
        try:
            proof = _production_runtime_proof()
        except Exception as error:
            return JSONResponse(
                status_code=503,
                content={
                    "ready": False,
                    "error": str(error),
                    "initialization_error": _init_error,
                    "elapsed_ms": elapsed_ms,
                },
                headers={"Retry-After": "10"},
            )
        return {"ready": True, **proof, "elapsed_ms": elapsed_ms}
    guala_ready = _guala is not None
    return {
        "ready": True,           # always 200 after lifespan starts
        "guala_ready": guala_ready,
        "state": "ready" if guala_ready else "warming",
        "elapsed_ms": elapsed_ms,
    }


def _read_build_git_sha():
    with open("/BUILD_INFO", encoding="utf-8") as handle:
        fields = dict(
            item.split("=", 1)
            for item in handle.read().split()
            if "=" in item)
    git_sha = fields.get("git_sha")
    if not isinstance(git_sha, str) or len(git_sha) != 40:
        raise RuntimeError("BUILD_INFO has no exact git SHA")
    return git_sha


def _ecs_task_runtime_identity():
    import json
    import urllib.request
    uri = os.environ.get("ECS_CONTAINER_METADATA_URI_V4", "")
    if not uri:
        raise RuntimeError("ECS task metadata URI is absent")
    with urllib.request.urlopen(uri.rstrip("/") + "/task", timeout=3.0) as response:
        metadata = json.load(response)
    family = metadata.get("Family")
    revision = metadata.get("Revision")
    containers = [
        item for item in metadata.get("Containers", [])
        if item.get("Name") == "dsf-ai"]
    if not family or revision is None or len(containers) != 1:
        raise RuntimeError("ECS task metadata identity is incomplete")
    image_digest = containers[0].get("ImageID")
    if (not isinstance(image_digest, str)
            or not image_digest.startswith("sha256:")):
        raise RuntimeError("ECS task metadata image digest is absent")
    return {
        "task_definition": f"{family}:{revision}",
        "image_digest": image_digest,
    }


def _production_runtime_proof(nonce=None):
    """Prove code, task, image, owner, CURRENT, seal, and live identity."""
    if not _init_complete or _init_error is not None or _guala is None:
        raise RuntimeError(_init_error or "Guala initialization is incomplete")
    if _deployment_lifecycle.snapshot()["state"] != "RUNNING":
        raise RuntimeError("deployment lifecycle is not RUNNING")
    if (_generation_owner_lock is None
            or not _generation_owner_lock.acquired):
        raise RuntimeError("process does not hold the EFS owner lease")
    if (_loaded_generation is None
            or _deployment_baseline_generation is None
            or _live_recovery_store is None):
        raise RuntimeError("no immutable generation was materialized")

    from dsf_ai_service.substrate.deployment_generation import (
        load_and_verify_deployment_seal,
    )
    certificate = load_and_verify_deployment_seal(
        GENERATION_STORE_ROOT,
        hmac_key=_deploy_hmac_key(),
        expected_nonce=nonce,
    )
    expected = {
        "generation_uuid": _deployment_baseline_generation.generation_uuid,
        "identity": _deployment_baseline_generation.identity,
        "manifest_sha256": _deployment_baseline_generation.manifest_sha256,
        "tick": _deployment_baseline_generation.tick,
    }
    for field, value in expected.items():
        if certificate.get(field) != value:
            raise RuntimeError(f"deployment seal {field} mismatch")
    if getattr(_guala, "_guala_identity", None) != expected["identity"]:
        raise RuntimeError("live Guala identity differs from immutable generation")
    live_current = _live_recovery_store.load_current()
    active = live_current or _deployment_baseline_generation
    for field in ("generation_uuid", "identity", "manifest_sha256", "tick"):
        if getattr(_loaded_generation, field) != getattr(active, field):
            raise RuntimeError(
                f"loaded live recovery {field} differs from authoritative CURRENT")
    if int(_guala.tick) < int(_loaded_generation.tick):
        raise RuntimeError("live Guala tick precedes authoritative recovery state")

    git_sha = _read_build_git_sha()
    task = _ecs_task_runtime_identity()
    expected_git = os.environ.get("DEPLOY_EXPECTED_GIT_SHA")
    expected_image = os.environ.get("DEPLOY_EXPECTED_IMAGE_DIGEST")
    expected_task_definition = os.environ.get(
        "DEPLOY_EXPECTED_TASK_DEFINITION")
    if expected_git != git_sha:
        raise RuntimeError("running git SHA differs from task expectation")
    if expected_image != task["image_digest"]:
        raise RuntimeError("running image digest differs from task expectation")
    if (expected_task_definition is not None
            and expected_task_definition != task["task_definition"]):
        raise RuntimeError(
            "running task definition differs from task expectation")
    return {
        "owner": True,
        "git_sha": git_sha,
        # These three fields are the immutable deployment identity consumed by
        # the sealed single-owner handoff controller.  A newer, verified hot
        # recovery overlay is allowed to be active without changing which
        # complete generation the deployment seal authenticated.
        "generation": expected["generation_uuid"],
        "identity": expected["identity"],
        "manifest_sha256": expected["manifest_sha256"],
        "generation_tick": expected["tick"],
        "active_recovery_generation": _loaded_generation.generation_uuid,
        "active_recovery_manifest_sha256": _loaded_generation.manifest_sha256,
        "active_recovery_tick": _loaded_generation.tick,
        "active_recovery_is_overlay": live_current is not None,
        "deployment_baseline_generation": expected["generation_uuid"],
        "deployment_baseline_manifest_sha256": expected["manifest_sha256"],
        "deployment_baseline_tick": expected["tick"],
        **task,
    }


def _require_readiness_control(request):
    import hmac
    if not _GUALALOOM_API_KEY:
        raise HTTPException(
            status_code=503, detail="deployment control is not configured")
    supplied_key = request.headers.get("X-API-Key", "")
    if not supplied_key or not hmac.compare_digest(
            supplied_key, _GUALALOOM_API_KEY):
        raise HTTPException(status_code=401, detail="invalid deployment credential")
    nonce = request.headers.get("X-Deploy-Nonce", "")
    if not nonce:
        raise HTTPException(status_code=400, detail="deployment nonce is required")
    return nonce


@app.get("/internal/deployment/readiness")
@app.get("/ready/guala")
async def ready_guala(request: Request):
    """Deep readiness — 200 only when Guala is fully loaded.
    Non-critical consumers (bridge, UI) can poll this to know when to expect responses.
    Returns 503 with Retry-After during boot.
    """
    elapsed_ms = int((time.time() - _BOOT_START) * 1000)
    if _boot_halted is not None:
        return JSONResponse(
            status_code=503,
            content={
                "ready": False,
                "boot_halted": _boot_halted,
                "elapsed_ms": elapsed_ms,
            },
            headers={"Retry-After": "30"},
        )
    if _REQUIRE_SEALED_STATE:
        nonce = _require_readiness_control(request)
        try:
            proof = _production_runtime_proof(nonce=nonce)
        except Exception as error:
            return JSONResponse(
                status_code=503,
                content={
                    "ready": False,
                    "error": str(error),
                    "initialization_error": _init_error,
                    "elapsed_ms": elapsed_ms,
                },
                headers={"Retry-After": "10"},
            )
        return {"ready": True, **proof, "elapsed_ms": elapsed_ms}
    if _guala is None:
        return JSONResponse(
            status_code=503,
            content={"ready": False, "error": "guala loading", "elapsed_ms": elapsed_ms},
            headers={"Retry-After": "10"},
        )
    return {
        "ready": True,
        "guala_id": (getattr(_guala, '_guala_identity', None) or "")[:8],
        "vocab": len(_guala.vocab),
        "tick": _guala.tick,
    }

def _deploy_hmac_key():
    """Derive a fixed-width seal key from the authenticated control secret."""
    if not _GUALALOOM_API_KEY:
        raise RuntimeError("deployment control credential is not configured")
    return _hashlib.sha256(
        ("guala-deployment-seal-v1\0" + _GUALALOOM_API_KEY).encode("utf-8")
    ).digest()


async def _require_deploy_control(request: Request):
    """Authenticate one nonce-bound deployment request before any mutation."""
    import hmac
    if not _GUALALOOM_API_KEY:
        raise HTTPException(
            status_code=503, detail="deployment control is not configured")
    supplied_key = request.headers.get("X-API-Key", "")
    if not supplied_key or not hmac.compare_digest(
            supplied_key, _GUALALOOM_API_KEY):
        raise HTTPException(status_code=401, detail="invalid deployment credential")
    header_nonce = request.headers.get("X-Deploy-Nonce", "")
    try:
        body = await request.json()
    except Exception:
        body = {}
    body_nonce = body.get("deploy_nonce") if isinstance(body, dict) else None
    if (not isinstance(header_nonce, str) or not header_nonce
            or not isinstance(body_nonce, str) or not body_nonce
            or not hmac.compare_digest(header_nonce, body_nonce)):
        raise HTTPException(
            status_code=400, detail="matching deployment nonce is required")
    return header_nonce


def _stop_embedded_persistence_components(timeout):
    """Stop retained non-engine persistence writers, propagating every failure."""
    stopped = []
    for attribute in ("s3_consumer", "persistence_consumer", "save_coordinator"):
        component = getattr(app.state, attribute, None)
        if component is None:
            continue
        component.stop(timeout=float(timeout))
        stopped.append(attribute)
    return {"persistence_components_stopped": stopped}


def _flush_v7_sessions_for_seal():
    """Persist every admitted v7 session after HTTP admission is drained."""
    from dsf_ai_service.substrate.v7_engine import (
        _sessions,
        _sessions_lock,
        save_session,
    )
    with _sessions_lock:
        sessions = tuple(_sessions.values())
    for session in sessions:
        save_session(session)
    return {"v7_sessions_flushed": len(sessions)}


def _copy_generation_auxiliary_tree(source, destination, *, suffixes):
    """Copy a finite, validated auxiliary tree without following links."""
    import shutil
    import stat
    if not os.path.exists(source):
        return 0
    if os.path.islink(source) or not os.path.isdir(source):
        raise RuntimeError(f"auxiliary state is not a real directory: {source}")
    copied = 0
    for current_root, directory_names, file_names in os.walk(
            source, topdown=True, followlinks=False):
        current = os.path.abspath(current_root)
        relative_root = os.path.relpath(current, source)
        target_root = (
            destination if relative_root == "."
            else os.path.join(destination, relative_root))
        os.makedirs(target_root, exist_ok=True)
        for name in directory_names:
            path = os.path.join(current, name)
            if os.path.islink(path) or not stat.S_ISDIR(os.lstat(path).st_mode):
                raise RuntimeError(f"unsafe auxiliary directory: {path}")
        for name in file_names:
            path = os.path.join(current, name)
            info = os.lstat(path)
            if (os.path.islink(path) or not stat.S_ISREG(info.st_mode)
                    ):
                # (st_nlink deliberately unchecked -- see
                # _copy_generation_file: hardlinked atomic-generation
                # sources are legitimate; the copy is the sealed artifact.)
                raise RuntimeError(f"unsafe auxiliary file: {path}")
            if not name.endswith(tuple(suffixes)):
                raise RuntimeError(f"unexpected auxiliary file: {path}")
            shutil.copy2(path, os.path.join(target_root, name))
            copied += 1
    return copied


def _copy_generation_file(source, destination, *, required=False):
    import shutil
    import stat
    try:
        info = os.lstat(source)
    except FileNotFoundError:
        if required:
            raise RuntimeError(f"required generation file is absent: {source}")
        return False
    # 2026-07-16: the atomic per-save generation store HARDLINKS state
    # files, so a legitimate source often has st_nlink > 1. The sealed
    # property lives in the fresh COPY below (nlink=1 by construction,
    # hashed after copy) and quiescence guarantees no writers -- extra
    # source links are harmless. Symlinks and non-regular files stay
    # rejected.
    if os.path.islink(source) or not stat.S_ISREG(info.st_mode):
        raise RuntimeError(f"generation source is not a regular file: {source}")
    shutil.copy2(source, destination)
    return True


def _write_runtime_generation_stage(stage):
    """Write the complete runtime recovery contract into one private stage."""
    _guala.save_full_state(str(stage), publish_generation=False)
    _guala._save_wave_atlas(str(stage))
    if (os.environ.get("WAVE_ATLAS_ENABLED", "0") == "1"
            and (getattr(_guala, "wave_atlas", None) is None
                 or not os.path.isfile(stage / "wave_atlas.npz"))):
        raise RuntimeError(
            "configured WaveAtlas is absent from the generation stage")
    identity_source = os.path.join(STATE_DIR, _guala.IDENTITY_FILE)
    _copy_generation_file(
        identity_source, stage / _guala.IDENTITY_FILE, required=True)
    for relative_path in (
            "dream_gate_cleared.json",
            "guala_runtime_config.json",
            "curriculum_progress.json",
            "curriculum.json",
            "world_state.json"):
        source = os.path.join(STATE_DIR, relative_path)
        _copy_generation_file(source, stage / relative_path)
    _copy_generation_auxiliary_tree(
        os.path.join(STATE_DIR, "v7_sessions"),
        os.path.join(stage, "v7_sessions"),
        suffixes=(".json", ".events.jsonl"),
    )
    _copy_generation_auxiliary_tree(
        os.path.join(STATE_DIR, "sounds"),
        os.path.join(stage, "sounds"),
        suffixes=(".audio",),
    )


def _seal_runtime_generation(nonce, *, pre_publish_validator=None):
    """Create, upload, read back, and publish one exact stopped generation."""
    global _deployment_baseline_generation, _loaded_generation
    import boto3
    from dsf_ai_service.substrate.deployment_generation import (
        persist_deployment_seal,
        stage_commit_upload,
        verify_deployment_seal,
    )

    identity = getattr(_guala, "_guala_identity", None)
    if not isinstance(identity, str) or not identity:
        raise RuntimeError("Guala identity is absent; generation cannot be sealed")
    tick = int(_guala.tick)

    bucket = os.environ.get(
        "GUALA_S3_BACKUP_BUCKET", "dsf-ai-site-backups")
    prefix = os.environ.get(
        "GUALA_GENERATION_S3_PREFIX", "guala/generations")
    key = _deploy_hmac_key()
    result = stage_commit_upload(
        store_root=GENERATION_STORE_ROOT,
        identity=identity,
        tick=tick,
        save_callback=_write_runtime_generation_stage,
        s3_client=boto3.client("s3", region_name="us-east-1"),
        bucket=bucket,
        prefix=prefix,
        hmac_key=key,
        nonce=nonce,
        pre_publish_validator=pre_publish_validator,
    )
    certificate_bytes = result.seal_certificate_bytes()
    certificate = verify_deployment_seal(
        certificate_bytes, hmac_key=key, expected_nonce=nonce)
    persist_deployment_seal(
        GENERATION_STORE_ROOT,
        certificate_bytes,
        hmac_key=key,
        expected_nonce=nonce,
    )
    if _live_recovery_store is not None:
        hot_payloads = {
            name: (json.dumps(
                result.generation.payload(name),
                allow_nan=False,
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            ) + "\n").encode("utf-8")
            for name in Guala.HOT_SAVE_MANIFEST_FILES
        }
        rebased = _live_recovery_store.rebase_after_deployment_seal(
            baseline=result.generation,
            tick=result.generation.tick,
            files=hot_payloads,
        )
        from dsf_ai_service.substrate.deployment_generation import (
            MATERIALIZATION_SCHEMA,
            MaterializedGeneration,
        )
        _deployment_baseline_generation = result.generation
        _loaded_generation = MaterializedGeneration(
            schema=MATERIALIZATION_SCHEMA,
            generation_uuid=rebased.generation_uuid,
            identity=rebased.identity,
            tick=rebased.tick,
            manifest_sha256=rebased.manifest_sha256,
            active_directory=os.path.abspath(STATE_DIR),
            materialized_files=tuple(sorted(Guala.HOT_SAVE_MANIFEST_FILES)),
        )
        app.state.deployment_baseline_generation = result.generation
        app.state.loaded_generation = _loaded_generation
    from dsf_ai_service.substrate.immutable_generation_store import (
        ImmutableGenerationStore,
    )
    generation_store = ImmutableGenerationStore(
        GENERATION_STORE_ROOT,
        identity=result.generation.identity,
        required_files=result.generation.required_files,
    )
    generation_store.prune_generations(
        retain=3,
        verified_current=result.generation,
    )
    return certificate


async def _quiesce_and_seal(nonce):
    """Execute RUNNING -> QUIESCING -> SEALED without a partial resume."""
    import asyncio
    lifecycle = _deployment_lifecycle
    lifecycle.begin_quiescence(nonce)
    destructive_started = False
    try:
        # At this first boundary no component has been stopped.  A drain
        # failure can safely reopen admission because process state is intact.
        # In-flight conversational turns are failed FIRST (the shutdown
        # handler's long-standing order): they hold background mutation slots
        # for their full settle time and may await engine progress that
        # quiescence pauses, so waiting on them deadlocked the drain (defect 2
        # of GL-RPT-RAM-FIXES-DEPLOYED-AND-SEAL-DEFECTS).  A turn failed here
        # is exactly as lost as it would be seconds later at owner turnover,
        # and its client gets the honest error either way.
        _fail_inflight_converse_tasks(
            "turn lost — deployment quiescence began before completion")
        try:
            await asyncio.to_thread(lifecycle.wait_for_mutations, 120.0)
        except RuntimeError as drain_error:
            stuck = _unfinished_mutating_task_names()
            raise RuntimeError(
                f"{drain_error}; unfinished background owners: "
                f"{stuck if stuck else 'none — holder is an HTTP request or executor job'}"
            ) from drain_error

        destructive_started = True
        await _stop_app_lifecycle_tasks(timeout=120.0)
        await asyncio.to_thread(lifecycle.wait_for_mutations, 120.0)
        _fail_inflight_converse_tasks(
            "turn lost — deployment quiescence began before completion")

        if _guala is None:
            raise RuntimeError("Guala is not loaded")
        app.state.deployment_quiescing = True
        v7_proof = await asyncio.to_thread(_flush_v7_sessions_for_seal)
        await asyncio.to_thread(
            _stop_embedded_persistence_components, 120.0)
        import dsf_ai_service.substrate_runner as _sr
        runner_proof = await asyncio.to_thread(
            _sr.quiesce_background_loops, 120.0)
        # Boundary STT worker is its own OS process (like the curriculum
        # subprocess quiesce_background_loops stops just above); terminate and
        # join it here on seal.  A no-op when the worker was never spawned.
        from dsf_ai_service.speech_transducer import shutdown_speech_worker
        speech_proof = await asyncio.to_thread(shutdown_speech_worker, 30.0)

        # This is the final admitted engine mutation.  It records sleep only
        # after every external producer has stopped, and before the engine
        # closes its own mutation admission below.
        await asyncio.to_thread(_guala.manual_sleep, STATE_DIR)

        # A sealed boundary cannot retain a threshold backlog.  The former
        # settle_queues(threshold=8) phase ran while autonomy and daydream
        # could still refill organism and tapestry queues.  The strict engine
        # boundary owns the correct order: stop producers, close admission,
        # join accepted mutations, drain all queues to zero, then stop every
        # worker.  Give that one proof the former settle allowance plus the
        # existing strict-stop allowance.
        import math
        raw_settle_budget = os.environ.get("SEAL_SETTLE_BUDGET_S", "420")
        try:
            settle_budget = float(raw_settle_budget or 420)
        except (TypeError, ValueError) as error:
            raise RuntimeError(
                "SEAL_SETTLE_BUDGET_S must be a finite non-negative number"
            ) from error
        if not math.isfinite(settle_budget) or settle_budget < 0.0:
            raise RuntimeError(
                "SEAL_SETTLE_BUDGET_S must be a finite non-negative number")
        engine_proof = await asyncio.to_thread(
            _guala.quiesce_background_workers, settle_budget + 120.0)
        certificate = await asyncio.to_thread(_seal_runtime_generation, nonce)
        proof = {
            **certificate,
            "runner": runner_proof,
            "speech_worker": speech_proof,
            "engine": engine_proof,
            "v7": v7_proof,
        }
        lifecycle.seal(proof)
        return proof
    except Exception as error:
        lifecycle.fail_quiescence(
            error,
            resumed=not destructive_started,
        )
        raise


@app.post("/internal/deployment/quiesce")
@app.post("/sleep_for_deploy")
async def sleep_for_deploy(request: Request):
    """Authenticated compatibility route for the canonical sealed handoff."""
    nonce = await _require_deploy_control(request)
    try:
        proof = await _quiesce_and_seal(nonce)
    except Exception as error:
        return JSONResponse(
            status_code=503,
            content={
                "ok": False,
                "error": str(error),
                "lifecycle": _deployment_lifecycle.snapshot(),
            },
        )
    return {
        "ok": True,
        "state": "SEALED",
        "deploy_nonce": nonce,
        "generation": proof["generation_uuid"],
        "identity": proof["identity"],
        "tick": proof["tick"],
        "manifest_sha256": proof["manifest_sha256"],
        "seal_hmac_sha256": proof["seal_hmac_sha256"],
    }
