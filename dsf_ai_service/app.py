"""
DSF-AI Service — FastAPI Application
=====================================
Three endpoints:
  POST /api/v1/analyze        — CSV upload → kernel → deterministic JSON report
  POST /api/v1/cluster        — element + N → screener → properties JSON
  POST /api/v1/cluster/screen — batch screening with constraints

TRADE SECRET — kernel internals never leave the server.
"""

import os
import stat
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
import base64
import binascii
import asyncio
from dataclasses import asdict


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
from typing import Optional, List, Dict, Any, Literal

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
from dsf_ai_service.cff_discovery import run_discovery, verify_candidate
_EMBODIED_READING_ROUTE_PATH = "/api/v1/embodiment/reading-lesson"
_PHYSICAL_SURFACE_LESSON_ROUTE_PATH = (
    "/api/v1/embodiment/physical-surface-lesson"
)

# ═══════════════════════════════════════════════════════════════
# GL-ARCH-FRONTEND-SPLIT: substrate mode
# ═══════════════════════════════════════════════════════════════
SUBSTRATE_MODE = os.environ.get("SUBSTRATE_MODE", "embedded")  # "embedded" or "remote"
_substrate_client = None

# ── GL-CMD-LOCK-CONTENTION-FIX-182 L3: frame backpressure ──────────────────
# /sight_frame and /sound_frame used to queue unboundedly in the default
# executor whenever frames arrived faster than they could be processed
# (measured live: individual calls holding self.lock for up to ~93s while
# camera+mic streamed continuously). Cap concurrent
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
    PCM_RING_BYTES as _PCM_STREAM_RING_BYTES,
    PCM_SAMPLE_RATE_HZ as _PCM_STREAM_SAMPLE_RATE_HZ,
    PCM_TRANSPORT_UNITS as _PCM_STREAM_TRANSPORT_UNITS,
    pcm_s16le_wav as _pcm_s16le_wav,
)
from dsf_ai_service.substrate.browser_binaural_pcm_stream import (
    BINAURAL_CHANNEL_ORDER as _BINAURAL_CHANNEL_ORDER,
    BrowserBinauralLineageMode as _BrowserBinauralLineageMode,
    BrowserBinauralPCMStreamRegistry as _BrowserBinauralPCMStreamRegistry,
)
from dsf_ai_service.substrate.browser_discrete_channel_projection import (
    BrowserDiscreteChannelProjectionOwner as _BrowserDiscreteChannelProjectionOwner,
    BrowserDiscreteChannelProjectionReceipt as _BrowserDiscreteChannelProjectionReceipt,
)
from dsf_ai_service.substrate.live_hearing_authority_integration import (
    LiveHearingAuthorityIntegrator as _LiveHearingAuthorityIntegrator,
)

_auditory_pcm_streams = AuditoryPCMStreamRegistry()
_auditory_pcm_epoch_lock = threading.RLock()
_browser_binaural_pcm_streams = _BrowserBinauralPCMStreamRegistry()
_browser_binaural_epoch_lock = threading.RLock()
# These process-local keys receipt only the typed refusal boundary.  They do
# not prove physical microphones, speaker paths, separated sources, meaning,
# or cognition.
_live_hearing_browser_integrator = _LiveHearingAuthorityIntegrator(
    authority_key=os.urandom(32),
    room_authority_key=os.urandom(32),
    w1_capture_authority_key=os.urandom(32),
    loom_authority_key=os.urandom(32),
)
_browser_discrete_channel_projection_owner = (
    _BrowserDiscreteChannelProjectionOwner(os.urandom(32))
)

_SIGHT_ARTICULATORY_ACT_RESULT_KEY = "articulatory_act"
_SIGHT_ARTICULATORY_PLAYBACK_SCHEMA = (
    "guala.loom.same_request_sight_articulatory_playback.v1"
)


def _consume_same_request_sight_articulatory_playback(
    sight_receipt,
    *,
    response_authority,
):
    """Verify and consume only the transient act returned by this sight call.

    No observation, engine history, retained response, or replay surface is
    consulted.  Removing the act from the engine result leaves no server-side
    transport reference to its PCM after this request has been serialized.
    """

    if not isinstance(sight_receipt, dict):
        raise TypeError("live sight result must be a mutable receipt")
    occurrence = sight_receipt.pop(
        _SIGHT_ARTICULATORY_ACT_RESULT_KEY,
        None,
    )
    if occurrence is None:
        return None
    raise RuntimeError(
        "legacy Python sight-to-vocal cognition is permanently retired"
    )



def _spoken_word_recognition_report(source):
    """Report that deterministic auditory L5 did not receive this request."""
    if _guala is None and not _is_remote():
        return {
            "capability": "spoken_word_recognition",
            "available": False,
            "status": "unavailable",
            "reason": "auditory L5 is not ready",
            "mechanism": (
                "continuous_component_hierarchical_reciprocal_l6_v1"
            ),
            "raw_sensing": {"available": False,
                            "mechanism": "causal_gammatone_erb_v1"},
        }
    return {
        "capability": "spoken_word_recognition",
        "available": True,
        "status": "not_attempted",
        "mechanism": (
            "continuous_component_hierarchical_reciprocal_l6_v1"
        ),
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
            except Exception as rejection_error:
                print(
                    "[visual] rejection telemetry failed: "
                    f"{type(rejection_error).__name__}: {rejection_error}"
                )
        return False


_mutating_background_tasks = set()


class _AdministrativeCheckpointAdmission:
    """One exact owner for authenticated administrative checkpoints."""

    def __init__(self):
        self._lock = threading.Lock()
        self._active_token = None

    def admit(self):
        with self._lock:
            if self._active_token is not None:
                return None
            token = object()
            self._active_token = token
            return token

    def release(self, token):
        with self._lock:
            if token is not self._active_token:
                raise RuntimeError(
                    "administrative checkpoint admission token changed")
            self._active_token = None

    def snapshot(self):
        with self._lock:
            return {
                "active": self._active_token is not None,
                "active_count": (
                    1 if self._active_token is not None else 0),
            }


_administrative_checkpoint_admission = (
    _AdministrativeCheckpointAdmission()
)


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
_PERIODIC_COLD_CHECKPOINT_INTERVAL_SECONDS = 30 * 60
_periodic_cold_checkpoint_status = {
    "active": False,
    "last_attempt_at": None,
    "last_failure": None,
    "last_failure_at": None,
    "last_success_at": None,
    "last_unchanged_skip_at": None,
    "next_eligible_at": None,
}
_periodic_hot_checkpoint_status = {
    "active": False,
    "last_attempt_at": None,
    "last_failure": None,
    "last_failure_at": None,
    "last_success_at": None,
    "last_success_duration_seconds": None,
    "last_unchanged_skip_at": None,
}


class _PeriodicColdCheckpointCadence:
    """Admit at most one cold-checkpoint attempt per exact interval."""

    def __init__(self, *, monotonic_now, wall_now):
        self._next_monotonic = (
            float(monotonic_now)
            + _PERIODIC_COLD_CHECKPOINT_INTERVAL_SECONDS
        )
        self.next_wall = (
            float(wall_now)
            + _PERIODIC_COLD_CHECKPOINT_INTERVAL_SECONDS
        )

    def admit(self, *, monotonic_now, wall_now):
        monotonic_now = float(monotonic_now)
        wall_now = float(wall_now)
        if monotonic_now < self._next_monotonic:
            return False
        self._next_monotonic = (
            monotonic_now
            + _PERIODIC_COLD_CHECKPOINT_INTERVAL_SECONDS
        )
        self.next_wall = (
            wall_now
            + _PERIODIC_COLD_CHECKPOINT_INTERVAL_SECONDS
        )
        return True


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


def _guala_publication_file(filename):
    if filename not in {
        "guala-brain-foundation-v1.png",
        "gualaloom.html",
        "loomscan.html",
        "legal.html",
        "style.css",
    }:
        raise RuntimeError(
            "Guala publication requested an unsealed static asset"
        )
    return FileResponse(os.path.join(STATIC_DIR, filename))


@app.get("/")
@app.get("/gualaloom.html")
async def index():
    return _guala_publication_file("gualaloom.html")


@app.get("/loomscan.html")
async def loomscan_page():
    return _guala_publication_file("loomscan.html")


@app.get("/legal.html")
async def legal_page():
    return _guala_publication_file("legal.html")


@app.get("/style.css")
async def guala_style():
    return _guala_publication_file("style.css")


@app.get("/guala-brain-foundation-v1.png")
async def guala_brain_foundation():
    return _guala_publication_file("guala-brain-foundation-v1.png")


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
    regime map, and explicit structural fields.
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

from dsf_ai_service.v4.guala_physical_runtime import Guala
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
PERSISTENT_STORAGE_CEILING_ENV = (
    "GUALA_PERSISTENT_STORAGE_CEILING_BYTES")
APPROVED_PERSISTENT_STORAGE_CEILING_BYTES = 5 * 1024 * 1024 * 1024


class PersistentStorageReadinessHalt(RuntimeError):
    """Sealed persistence has no configured global physical-byte authority."""


def _knowledge_gap_status():
    """Best-effort status from the current tutoring gap owner."""
    try:
        from dsf_ai_service.substrate import knowledge_gap_ledger
        options = {}
        profile = globals().get("_production_storage_profile")
        authority = globals().get("_physical_byte_authority")
        if (
            globals().get("_REQUIRE_SEALED_STATE", False)
            and (profile is None or authority is None)
        ):
            return {
                "persistence_failure": (
                    "production storage authority is not configured"
                )
            }
        if profile is not None and authority is not None:
            options["physical_byte_authority"] = authority
            options["max_encoded_bytes"] = (
                profile.knowledge_gap_ledger_bytes
            )
        return knowledge_gap_ledger.get_ledger(
            STATE_DIR,
            **options,
        ).status()
    except Exception:
        return {}


_REQUIRE_SEALED_STATE = os.environ.get(
    "GUALA_REQUIRE_SEALED_STATE", "0").strip() == "1"
_loaded_generation = None
_deployment_baseline_generation = None
_live_recovery_store = None
_authoritative_cold_store = None
_physical_byte_authority = None
_production_storage_profile = None
_legacy_cold_retention_transition = None
_predecessor_live_recovery_retirement = None
_remote_generation_reconciliation = None
_persistence_authority_lock = threading.RLock()
_last_verified_runtime_readiness = None
_AUTHENTICATED_CURRENT_SCHEMA_EXTENSION_SCHEMA = (
    "guala.authenticated_current_schema_extension.readiness.v1"
)
_REVIEWED_CURRENT_SCHEMA_MIGRATIONS = (
    "authenticated_task853_native_resident_cutover_v1",
    "legacy_whole_organism_to_native_exact_v1",
    "native_materialized_fabric_v2_or_v3_to_v4",
    "native_resident_base64_to_raw_glorun_v1",
    "physical_surface_tutoring_conductor_genesis",
    "whole_organism_neuron_population_profile_v1_to_v2",
)
_authenticated_current_schema_extension_certificate = None

# Production boot creates no scripted corpus, vocabulary, or experience.
# Only an authenticated persisted generation may supply learned state.

def _prepare_generation_boot():
    """Activate one fully verified immutable CURRENT generation."""
    global _loaded_generation
    global _deployment_baseline_generation, _live_recovery_store
    global _authoritative_cold_store, _legacy_cold_retention_transition
    global _physical_byte_authority, _production_storage_profile
    global _remote_generation_reconciliation
    global _predecessor_live_recovery_retirement
    if (
        os.environ.get("ECS_CONTAINER_METADATA_URI_V4")
        and not _REQUIRE_SEALED_STATE
    ):
        raise PersistentStorageReadinessHalt(
            "ECS production cannot start the retired flat/full-copy "
            "persistence path; GUALA_REQUIRE_SEALED_STATE=1 is mandatory"
        )
    if not _REQUIRE_SEALED_STATE:
        return None
    if _loaded_generation is not None:
        return _loaded_generation
    from dsf_ai_service.substrate.deployment_generation import (
        DEPLOYMENT_SEAL_NAME,
        LEGACY_DEPLOYMENT_SEAL_SCHEMA,
        load_and_verify_deployment_seal,
        load_current_generation_deployment_seal,
        materialize_verified_generation,
        persist_generation_deployment_seal,
        reconcile_generation_deployment_seals,
        reconcile_remote_generation_prefixes,
        verified_causal_generation_receipt,
    )
    from dsf_ai_service.substrate.authoritative_cold_generation_store import (
        AuthoritativeColdGenerationError,
        AuthoritativeColdGenerationStore,
    )
    from dsf_ai_service.substrate.live_recovery_generation import (
        LiveRecoveryError,
        LiveRecoveryGenerationStore,
        retire_redundant_predecessor_current,
    )
    from dsf_ai_service.substrate.physical_byte_ceiling import (
        PhysicalByteCeilingAuthority,
    )
    (
        persistent_storage_ceiling,
        persistent_storage_scope,
        storage_profile,
    ) = _authoritative_physical_storage_config()
    physical_byte_authority = PhysicalByteCeilingAuthority(
        persistent_storage_scope,
        persistent_storage_ceiling,
    )
    remote_generation_reconciliation = None
    try:
        (
            max_generation_bytes,
            max_required_files,
            max_path_bytes,
        ) = _authoritative_cold_limits()
        _current_reference, deployment_seal = (
            load_current_generation_deployment_seal(
                GENERATION_STORE_ROOT,
                hmac_key=_deploy_hmac_key(),
            )
        )
        has_generation_bound_seal = deployment_seal is not None
        if deployment_seal is None:
            deployment_seal = load_and_verify_deployment_seal(
                GENERATION_STORE_ROOT,
                hmac_key=_deploy_hmac_key(),
            )

        cold_store = AuthoritativeColdGenerationStore(
            GENERATION_STORE_ROOT,
            identity=deployment_seal["identity"],
            required_files=None,
            max_encoded_generation_bytes=max_generation_bytes,
            max_dynamic_required_files=max_required_files,
            max_dynamic_path_bytes=max_path_bytes,
            pre_publish_validator=_validate_runtime_generation_cold_restore,
            physical_byte_ceiling=persistent_storage_ceiling,
            physical_byte_scope=persistent_storage_scope,
            generation_revision=verified_causal_generation_receipt,
        )
        _legacy_cold_retention_transition = None
        if has_generation_bound_seal:
            cold_state = cold_store.inspect_sealed_boot(
                require_predecessor=False
            )
            verified_receipt = cold_state.current_authority
            for field in (
                "generation_uuid",
                "identity",
                "tick",
                "manifest_sha256",
            ):
                if deployment_seal[field] != getattr(
                        cold_state.current, field):
                    raise RuntimeError(
                        f"signed deployment seal {field} differs from "
                        "verified CURRENT generation")
            if verified_receipt is None:
                if any(
                    field in deployment_seal
                    for field in (
                        "state_revision",
                        "causal_state_sha256",
                        "operational_metadata_sha256",
                        "attempt_operational_metadata_sha256",
                    )
                ):
                    raise RuntimeError(
                        "signed deployment seal declares causal authority "
                        "for a legacy CURRENT generation"
                    )
            else:
                receipt_authority = {
                    "state_revision": verified_receipt.state_revision,
                    "causal_state_sha256": (
                        verified_receipt.causal_state_sha256
                    ),
                    "operational_metadata_sha256": (
                        verified_receipt.operational_metadata_sha256
                    ),
                    "attempt_operational_metadata_sha256": (
                        verified_receipt.operational_metadata_sha256
                    ),
                }
                for field, value in receipt_authority.items():
                    if deployment_seal.get(field) != value:
                        raise RuntimeError(
                            f"signed deployment seal {field} differs from "
                            "verified CURRENT causal receipt"
                        )
        else:
            try:
                cold_state = cold_store.inspect_sealed_boot(
                    require_predecessor=False
                )
            except AuthoritativeColdGenerationError:
                cold_state = cold_store.inspect_legacy_retention_transition()
                _legacy_cold_retention_transition = cold_state.current
            if (
                deployment_seal["generation_uuid"]
                != cold_state.current.generation_uuid
            ):
                raise RuntimeError(
                    "CURRENT has no matching generation-bound deployment seal")
            if _legacy_cold_retention_transition is None:
                legacy_seal_path = os.path.join(
                    GENERATION_STORE_ROOT,
                    DEPLOYMENT_SEAL_NAME,
                )
                with open(legacy_seal_path, "rb") as handle:
                    legacy_seal_bytes = handle.read()
                import base64
                persist_generation_deployment_seal(
                    GENERATION_STORE_ROOT,
                    legacy_seal_bytes,
                    hmac_key=_deploy_hmac_key(),
                    expected_nonce=base64.b64decode(
                        deployment_seal["nonce_base64"],
                        validate=True,
                    ),
                    physical_byte_authority=physical_byte_authority,
                )
        if _legacy_cold_retention_transition is None:
            retained_generation_uuids = tuple(
                record.generation_uuid
                for record in cold_state.census
            )
            reconcile_generation_deployment_seals(
                GENERATION_STORE_ROOT,
                retained_generation_uuids=retained_generation_uuids,
                physical_byte_authority=physical_byte_authority,
            )
            import boto3
            removed_remote_generations = reconcile_remote_generation_prefixes(
                s3_client=boto3.client("s3", region_name="us-east-1"),
                bucket=os.environ.get(
                    "GUALA_S3_BACKUP_BUCKET",
                    "dsf-ai-site-backups",
                ),
                prefix=os.environ.get(
                    "GUALA_GENERATION_S3_PREFIX",
                    "guala/generations",
                ),
                retained_generation_uuids=retained_generation_uuids,
                maximum_objects_per_generation=max_required_files + 1,
            )
            remote_generation_reconciliation = {
                "executed": True,
                "retained_generation_uuids": (
                    retained_generation_uuids
                ),
                "retired_generation_uuids": (
                    removed_remote_generations
                ),
                "version_aware": True,
            }
        authoritative_baseline = cold_state.current
        # The bounded ring append body is operational transport, never learned
        # cognition authority. It may remain after any stopped sealed owner and
        # must not block exact replacement by the next sealed generation.
        # The retired-component purge proof likewise records removal of the
        # prohibited duplicate legacy brain; it is archival evidence, not an
        # active owner or learned state body.
        retirable_runtime_paths = (
            "legacy_cognition_archive/retired_component_purge_proof.json",
            "ring_events/events.log",
        )
        if deployment_seal["schema"] == LEGACY_DEPLOYMENT_SEAL_SCHEMA:
            # These predecessor-only files were never cognition authority.
            # organs_manifest.json was written by the retired 8-organ
            # compatibility merge. ring_events/events.log is an operational
            # append body governed by the separate checkpoint recovery
            # authority. Their exact names may cross only this authenticated
            # v2-to-v1 cutover boundary; arbitrary extras still halt boot.
            retirable_runtime_paths = (
                "organs_manifest.json",
                "ring_events/events.log",
            )
        materialized_baseline = materialize_verified_generation(
            generation=cold_state.current,
            active_directory=STATE_DIR,
            physical_byte_authority=physical_byte_authority,
            retirable_runtime_paths=retirable_runtime_paths,
        )
        live_store = LiveRecoveryGenerationStore(
            LIVE_RECOVERY_STORE_ROOT,
            baseline=authoritative_baseline,
            hot_files=Guala.HOT_SAVE_MANIFEST_FILES,
            hmac_key=_deploy_hmac_key(),
            state_file_tick_manifest="guala_core.json",
            max_encoded_generation_bytes=(
                storage_profile.max_live_recovery_generation_bytes
            ),
            physical_byte_ceiling=persistent_storage_ceiling,
            physical_byte_scope=persistent_storage_scope,
        )
        predecessor_live_recovery_retirement = ()
        try:
            live_store.load_current()
        except LiveRecoveryError:
            predecessor_live_recovery_retirement = (
                retire_redundant_predecessor_current(
                    LIVE_RECOVERY_STORE_ROOT,
                    baseline=authoritative_baseline,
                    hmac_key=_deploy_hmac_key(),
                    physical_byte_authority=physical_byte_authority,
                )
            )
        live = live_store.apply_current(
            STATE_DIR,
            physical_byte_authority=physical_byte_authority,
        )
        from dsf_ai_service.substrate import knowledge_gap_ledger
        knowledge_gap_ledger.get_ledger(
            STATE_DIR,
            physical_byte_authority=physical_byte_authority,
            max_encoded_bytes=storage_profile.knowledge_gap_ledger_bytes,
        )
        materialized = live or materialized_baseline
    except BaseException:
        _legacy_cold_retention_transition = None
        _predecessor_live_recovery_retirement = None
        raise
    _loaded_generation = materialized
    _deployment_baseline_generation = authoritative_baseline
    _live_recovery_store = live_store
    _authoritative_cold_store = cold_store
    _physical_byte_authority = physical_byte_authority
    _production_storage_profile = storage_profile
    _remote_generation_reconciliation = (
        remote_generation_reconciliation
    )
    _predecessor_live_recovery_retirement = (
        predecessor_live_recovery_retirement
    )
    app.state.loaded_generation = materialized
    app.state.deployment_baseline_generation = authoritative_baseline
    app.state.live_recovery_store = live_store
    app.state.authoritative_cold_store = cold_store
    return materialized


def _complete_legacy_cold_retention_transition(restored_guala):
    """Retire legacy retain-three state only after the real CURRENT restore."""
    global _legacy_cold_retention_transition
    global _deployment_baseline_generation
    global _remote_generation_reconciliation
    if _legacy_cold_retention_transition is None:
        return
    if _authoritative_cold_store is None:
        raise RuntimeError(
            "legacy retention transition has no cold-generation authority")
    from dsf_ai_service.substrate.deployment_generation import (
        DEPLOYMENT_SEAL_NAME,
        load_and_verify_deployment_seal,
        persist_generation_deployment_seal,
        reconcile_generation_deployment_seals,
        reconcile_remote_generation_prefixes,
    )
    audited_current = _legacy_cold_retention_transition
    transitioned = _authoritative_cold_store.complete_legacy_retention_transition(
        audited_current=audited_current,
        restored_identity=getattr(restored_guala, "_guala_identity", None),
        restored_tick=int(restored_guala.tick),
    )
    deployment_seal = load_and_verify_deployment_seal(
        GENERATION_STORE_ROOT,
        hmac_key=_deploy_hmac_key(),
    )
    if (
        deployment_seal["generation_uuid"]
        != transitioned.current.generation_uuid
    ):
        raise RuntimeError(
            "legacy retention transition changed sealed CURRENT")
    legacy_seal_path = os.path.join(
        GENERATION_STORE_ROOT,
        DEPLOYMENT_SEAL_NAME,
    )
    with open(legacy_seal_path, "rb") as handle:
        legacy_seal_bytes = handle.read()
    import base64
    persist_generation_deployment_seal(
        GENERATION_STORE_ROOT,
        legacy_seal_bytes,
        hmac_key=_deploy_hmac_key(),
        expected_nonce=base64.b64decode(
            deployment_seal["nonce_base64"],
            validate=True,
        ),
        physical_byte_authority=_physical_byte_authority,
    )
    retained_generation_uuids = tuple(
        record.generation_uuid
        for record in transitioned.census
    )
    reconcile_generation_deployment_seals(
        GENERATION_STORE_ROOT,
        retained_generation_uuids=retained_generation_uuids,
        physical_byte_authority=_physical_byte_authority,
    )
    import boto3
    _, max_required_files, _ = _authoritative_cold_limits()
    removed_remote_generations = reconcile_remote_generation_prefixes(
        s3_client=boto3.client("s3", region_name="us-east-1"),
        bucket=os.environ.get(
            "GUALA_S3_BACKUP_BUCKET",
            "dsf-ai-site-backups",
        ),
        prefix=os.environ.get(
            "GUALA_GENERATION_S3_PREFIX",
            "guala/generations",
        ),
        retained_generation_uuids=retained_generation_uuids,
        maximum_objects_per_generation=max_required_files + 1,
    )
    _remote_generation_reconciliation = {
        "executed": True,
        "retained_generation_uuids": retained_generation_uuids,
        "retired_generation_uuids": removed_remote_generations,
        "version_aware": True,
    }
    _deployment_baseline_generation = transitioned.current
    app.state.deployment_baseline_generation = transitioned.current
    _legacy_cold_retention_transition = None
    print(
        "[generation] legacy retain-three transition completed after exact "
        f"CURRENT restore; retained={retained_generation_uuids}",
        flush=True,
    )


def _publish_authoritative_hot_generation(
        *, save_tick, identity, manifest_files, files):
    """Commit staged hot bytes without creating a second flat state body."""
    global _loaded_generation
    with _persistence_authority_lock:
        if not _REQUIRE_SEALED_STATE or _live_recovery_store is None:
            raise RuntimeError(
                "authoritative live recovery is unavailable in sealed production")
        if identity != _live_recovery_store.baseline.identity:
            raise RuntimeError(
                "hot recovery identity differs from deployment baseline")
        required = tuple(sorted(manifest_files))
        if required != _live_recovery_store.hot_files:
            raise RuntimeError(
                "hot recovery file contract differs from engine contract")
        supplied = {
            str(relative): os.path.abspath(os.fspath(source))
            for relative, source in files.items()
        }
        if set(supplied) != set(required):
            raise RuntimeError(
                "hot recovery staged files differ from engine contract"
            )
        state_root = os.path.realpath(STATE_DIR)
        for relative, source in supplied.items():
            expected_source = os.path.join(
                state_root,
                *relative.split("/"),
            ) + ".tmp"
            try:
                source_info = os.stat(source, follow_symlinks=False)
            except (FileNotFoundError, NotADirectoryError, OSError):
                source_info = None
            if (
                source != expected_source
                or os.path.realpath(os.path.dirname(source))
                != os.path.dirname(expected_source)
                or source_info is None
                or not stat.S_ISREG(source_info.st_mode)
                or source_info.st_nlink != 1
            ):
                raise RuntimeError(
                    "hot recovery source is not an exact private engine "
                    f"stage: {relative}"
                )
        generation = _live_recovery_store.commit_hot_state(
            tick=int(save_tick),
            files=supplied,
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
            active_directory=str(generation.directory),
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
    """Boot one verified immutable generation and its live organism."""
    global _loaded_generation
    global _deployment_baseline_generation, _live_recovery_store
    global _authoritative_cold_store, _legacy_cold_retention_transition
    global _remote_generation_reconciliation
    global _authenticated_current_schema_extension_certificate
    try:
        _prepare_generation_boot()
        _gl_init()
    except BaseException:
        _loaded_generation = None
        _deployment_baseline_generation = None
        _live_recovery_store = None
        _authoritative_cold_store = None
        _legacy_cold_retention_transition = None
        _remote_generation_reconciliation = None
        _authenticated_current_schema_extension_certificate = None
        app.state.loaded_generation = None
        app.state.deployment_baseline_generation = None
        app.state.live_recovery_store = None
        app.state.authoritative_cold_store = None
        raise


def _gl_init():
    global _guala
    global _authenticated_current_schema_extension_certificate
    if _guala is not None:
        return
    if _REQUIRE_SEALED_STATE and _loaded_generation is None:
        raise RuntimeError(
            "sealed-state generation boot is not complete; direct "
            "initialization refused")

    os.makedirs(STATE_DIR, exist_ok=True)
    # CRITICAL: build into local var — only set _guala AFTER successful load.
    # If load_full_state fails (e.g. lock timeout), _guala stays None so the
    # next call retries instead of running with a blank substrate.
    # GL-RESTORE-CTRL: if FORCE_S3_RESTORE=1, download from S3 before loading EFS.
    # Used for targeted state restores (e.g. recovering from save-bug data loss).
    # After one successful restore boot, remove env var so subsequent restarts load normally.
    if os.environ.get("FORCE_S3_RESTORE", "0") == "1":
        raise RuntimeError(
            "FORCE_S3_RESTORE is retired; restore only an authenticated "
            "immutable generation while no owner is running"
        )

    def _runtime_guala():
        if _physical_byte_authority is None:
            return Guala()
        if _production_storage_profile is None:
            raise RuntimeError(
                "physical-byte authority has no production storage profile"
            )
        return Guala(
            physical_byte_authority=_physical_byte_authority,
            engine_persistence_profile_bytes=(
                _production_storage_profile
                .engine_persistence_profile_bytes
            ),
            observational_receipt_hmac_key=_deploy_hmac_key(),
        )

    g = _runtime_guala()

    # Load full persisted state from EFS (atomic, validated).
    # Retry up to 3× for transient EFS stale-handle errors (errno 116).
    _load_attempts = 0
    while _load_attempts < 3:
        _load_attempts += 1
        if _REQUIRE_SEALED_STATE and _loaded_generation is not None:
            g.load_full_state(
                STATE_DIR,
                allow_authenticated_current_schema_migration=True,
            )
        else:
            g.load_full_state(STATE_DIR)
        if getattr(g, '_load_successful', True):
            break
        errs = getattr(g, '_load_errors', [])
        is_stale = any("116" in str(e) or "Stale" in str(e) for e in errs)
        if is_stale and _load_attempts < 3:
            print(f"[GualaLoom] EFS stale handle on attempt {_load_attempts}, retrying...")
            import time as _t; _t.sleep(2)
            _strict_discard_guala(g, reason="EFS stale-handle retry")
            g = _runtime_guala()
        else:
            break

    # Any failed engine load halts. Recovery is an explicit authenticated
    # generation operation performed while no process owns the state.
    if not getattr(g, '_load_successful', True):
        errs = getattr(g, '_load_errors', [])
        _strict_discard_guala(g, reason="engine state load failure")
        raise RuntimeError(
            "engine state failed exact load; refusing every unauthenticated "
            f"or automatic fallback: {errs}"
        )

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
        try:
            _complete_legacy_cold_retention_transition(g)
        except Exception:
            _strict_discard_guala(
                g,
                reason="legacy cold-retention transition failure",
            )
            raise
        materialized_baseline = _deployment_baseline_generation
        materialized_live_overlay = (
            None
            if _live_recovery_store is None
            else _live_recovery_store.load_current()
        )
        if materialized_baseline is None:
            _strict_discard_guala(
                g,
                reason="missing verified cold baseline",
            )
            raise RuntimeError(
                "sealed-state boot has no verified cold baseline"
            )
        g.establish_loaded_cold_checkpoint(
            authoritative_tick=materialized_baseline.tick,
        )
        applied_schema_migrations = tuple(sorted(getattr(
            g,
            "_authenticated_current_schema_migrations",
            (),
        )))
        if applied_schema_migrations:
            expected_schema_migrations = set(
                _REVIEWED_CURRENT_SCHEMA_MIGRATIONS
            )
            if (
                len(applied_schema_migrations)
                != len(set(applied_schema_migrations))
                or not set(applied_schema_migrations).issubset(
                    expected_schema_migrations
                )
            ):
                _strict_discard_guala(
                    g,
                    reason="unreviewed current-schema migration set",
                )
                raise RuntimeError(
                    "authenticated current-schema migration set changed: "
                    + ", ".join(applied_schema_migrations)
                )
            import secrets
            extension_certificate = _seal_runtime_generation(
                secrets.token_hex(32),
                runtime=g,
                authenticated_current_schema_migrations=(
                    applied_schema_migrations
                ),
            )
            _authenticated_current_schema_extension_certificate = (
                _build_authenticated_current_schema_extension_certificate(
                    predecessor=materialized_baseline,
                    successor_certificate=extension_certificate,
                    migration_markers=applied_schema_migrations,
                )
            )
            print(
                "[generation] authenticated whole-organism current-schema "
                "extension sealed: "
                f"generation={extension_certificate['generation_uuid']} "
                f"tick={extension_certificate['tick']}",
                flush=True,
            )
        g._authoritative_hot_generation_publisher = (
            _publish_authoritative_hot_generation)
        g._authoritative_cold_generation_checkpoint = (
            _checkpoint_authoritative_runtime)
        from dsf_ai_service.substrate.deployment_generation import (
            retire_verified_materialization,
        )
        retire_verified_materialization(
            baseline=materialized_baseline,
            active_directory=STATE_DIR,
            overlays=(
                ()
                if materialized_live_overlay is None
                else (materialized_live_overlay,)
            ),
            physical_byte_authority=_physical_byte_authority,
        )
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

    if (
        not _REQUIRE_SEALED_STATE
        and getattr(g, "_last_save_timestamp", None) is not None
    ):
        g.establish_loaded_cold_checkpoint(
            authoritative_tick=g.tick,
        )

    autonomous_status = g.start_autonomous_experience_driver()
    print(
        "[GualaLoom] physical substrate booted: "
        f"tick={g.tick} autonomous_experience="
        f"{autonomous_status['lifecycle']}"
    )

    # ── GL-CMD-PROCESS-COLLAPSE-61: embedded-mode post-boot setup ─────────────
    # Mirrors what substrate_runner.run_server() used to do after boot_substrate.
    try:
        _embedded_post_boot(g)
    except BaseException as setup_error:
        import dsf_ai_service.substrate_runner as _sr
        try:
            _sr.quiesce_background_loops(timeout=120.0)
        except BaseException as quiesce_error:
            raise RuntimeError(
                "embedded substrate setup failed and its runner loops "
                f"could not quiesce: {quiesce_error}"
            ) from setup_error
        finally:
            _sr._guala = None
        _strict_discard_guala(
            g,
            reason="embedded substrate setup failure",
        )
        raise

    # CRITICAL: only expose the global after every required transport and
    # observation loop has started successfully.
    _guala = g


def _mount_embedded_rings(g, runner):
    """Mount the required bounded event and physical-input transports."""
    from dsf_ai_service.substrate.ring_buffer import SubstrateRing, InputRing

    runner._substrate_ring = SubstrateRing(
        size=1 << 18,
        max_event_record_bytes=g.OBSERVATIONAL_RECEIPT_MAX_BYTES,
    )
    runner._input_ring = InputRing(size=1 << 14)
    print(
        f"[substrate] Rings: substrate={runner._substrate_ring._size} "
        f"input={runner._input_ring._size}"
    )
    original_log = g._log_substrate_event

    def log_and_publish(event_kind, **detail):
        original_log(event_kind, **detail)
        runner._substrate_ring.publish(
            event_kind,
            g.tick,
            detail=detail,
        )

    g._log_substrate_event = log_and_publish


def _start_embedded_input_consumer(runner):
    """Start the required physical input-ring owner."""
    runner._start_input_ring_consumer()
    print("[substrate] InputRing consumer started (R3/R4)")


def _embedded_post_boot(g):
    """Post-boot setup for embedded mode: rings, loops, SaveCoordinator.
    Called from _gl_init after Guala is fully loaded and set as global."""
    import dsf_ai_service.substrate_runner as _sr

    # Wire _guala into substrate_runner so OP_HANDLERS can find it.
    _sr._guala = g

    _mount_embedded_rings(g, _sr)
    _start_embedded_input_consumer(_sr)

    print(
        "[curriculum] legacy custody-native tutoring retired; "
        "native tutoring unavailable",
        flush=True,
    )

    # SaveCoordinator: presence-detected saves with S3 background queue.
    try:
        from dsf_ai_service.save_coordinator import SaveCoordinator
        import dsf_ai_service.save_coordinator as _sc
        _s3_bucket = os.environ.get("GUALA_S3_BACKUP_BUCKET", "dsf-ai-site-backups")
        # Full-state S3 authority belongs exclusively to verified immutable
        # generations.  The legacy coordinator's partial filename list cannot
        # represent a recovery generation and is therefore local-save only.
        save_coord = (
            None
            if _REQUIRE_SEALED_STATE
            else SaveCoordinator(g, STATE_DIR, s3_bucket=None)
        )
        _sc.SAVE_COORDINATOR = save_coord
        app.state.save_coordinator = save_coord

        # Wrap _end_activity to trigger saves on activity end (verbatim from run_server).
        if save_coord is not None and hasattr(g, '_end_activity'):
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
        if save_coord is not None:
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
            _sr._start_background_thread(
                _save_backstop_thread,
                "save-backstop",
            )

        # Ring persistence + S3 consumers.
        if _sr._substrate_ring is not None:
            from dsf_ai_service.substrate.persistence_consumer import (
                PersistenceConsumer, S3Consumer, ring_checkpoint_state)
            _events_dir = os.path.join(STATE_DIR, "ring_events")
            os.makedirs(_events_dir, exist_ok=True)
            persistence_capacity = {}
            if (
                _physical_byte_authority is not None
                and _production_storage_profile is not None
            ):
                persistence_capacity = {
                    "physical_byte_authority": _physical_byte_authority,
                    "max_event_record_bytes": (
                        _production_storage_profile.ring_event_record_bytes
                    ),
                    "max_checkpoint_bytes": (
                        _production_storage_profile.ring_checkpoint_bytes
                    ),
                    "max_event_segment_bytes": (
                        _production_storage_profile.ring_event_segment_bytes
                    ),
                    "receipt_hmac_key": _deploy_hmac_key(),
                }
            _pers = PersistenceConsumer(
                ring=_sr._substrate_ring,
                state_dir=_events_dir,
                build_snapshot_fn=lambda: ring_checkpoint_state(g.tick),
                **persistence_capacity,
            )
            _pers.start()
            app.state.persistence_consumer = _pers
            _s3c = S3Consumer(
                ring=_sr._substrate_ring,
                state_dir=_events_dir,
                bucket=_s3_bucket,
                version_aware_retirement=_REQUIRE_SEALED_STATE,
            )
            _s3c.start()
            app.state.s3_consumer = _s3c
            print("[substrate] Ring consumers started: persistence + S3")

        print("[app] Substrate booted, background loops running")
    except Exception as _e:
        if _REQUIRE_SEALED_STATE:
            raise
        print(f"[app] SaveCoordinator setup failed (non-fatal): {_e}")









class GLVisualFrameClaim(BaseModel):
    captured_ms: int
    frame_b64: str


class GLMessage(BaseModel):
    text: str
    command: Optional[str] = None
    source: Optional[str] = None   # v7-bridge: source-tagged input (joe/wc/c1)
    emission_mode: Optional[str] = None  # "topk" | "grandurun" per-request override
    sight_b64: Optional[object] = None
    capture_started_ms: Optional[int] = None
    capture_ended_ms: Optional[int] = None
    sight_captured_ms: Optional[object] = None
    visual_source: Literal[
        "camera_stream",
        "simulated_material_display",
    ] = "camera_stream"
    # Camera claims are deliberately transport-opaque here.  A malformed
    # camera claim must reach the independent visual rejection boundary; it
    # must never make FastAPI reject an otherwise valid continuous PCM window.
    sight_frames: Optional[object] = None
    capture_purpose: Literal["ambient", "utterance"] = "ambient"
    audio_encoding: Literal["encoded_media", "pcm_s16le"] = "encoded_media"
    audio_stream_id: Optional[str] = None
    audio_sequence: Optional[int] = None
    audio_first_sample_index: Optional[int] = None
    audio_sample_count: Optional[int] = None
    audio_sample_rate_hz: Optional[int] = None
    audio_source_epoch_ms: Optional[int] = None
    audio_channel_mode: Literal[
        "legacy_unspecified",
        "single_runtime_channel",
        "discrete_left_projection",
    ] = "legacy_unspecified"
    audio_channel_projection: Optional[Dict[str, Any]] = None


class AuditoryPCMStreamCloseRequest(BaseModel):
    stream_id: str
    release_terminal: bool = True


class BrowserBinauralLineageRequest(BaseModel):
    stream_id: str
    capture_session_sha256: str
    worklet_source_sha256: str
    media_track_settings_sha256: str
    mode: Literal["discrete_source_channels"]
    media_track_channel_count: int
    worklet_input_channel_count: int
    channel_order: List[str]


class BrowserBinauralChunkRequest(BaseModel):
    stream_id: str
    target_mono_stream_id: str
    lineage_receipt_sha256: str
    sequence: int
    first_sample_index: int
    render_frame_start: int
    sample_rate_hz: int
    source_epoch_start_ns: int
    left_pcm_b64: str
    right_pcm_b64: str


class BrowserBinauralCloseRequest(BaseModel):
    stream_id: str


def _verify_browser_channel_projection(
    msg: GLMessage,
    pcm_s16le: bytes,
) -> _BrowserDiscreteChannelProjectionReceipt | None:
    """Verify one explicit runtime-channel lineage before mono hearing."""

    if msg.audio_channel_mode == "discrete_left_projection":
        if msg.audio_channel_projection is None:
            raise ValueError(
                "discrete left-channel provenance is absent"
            )
        receipt = _BrowserDiscreteChannelProjectionReceipt.from_record(
            msg.audio_channel_projection
        )
        _browser_discrete_channel_projection_owner.verify(
            receipt,
            pcm_s16le=pcm_s16le,
        )
        if (
            receipt.sequence != msg.audio_sequence
            or receipt.first_sample_index
            != msg.audio_first_sample_index
            or receipt.sample_count != msg.audio_sample_count
            or receipt.target_mono_stream_id
            != msg.audio_stream_id
        ):
            raise ValueError(
                "mono hearing left its parent channel interval"
            )
        return receipt
    if msg.audio_channel_mode == "single_runtime_channel":
        if msg.audio_channel_projection is not None:
            raise ValueError(
                "single runtime channel carried false binaural provenance"
            )
        return None
    if msg.audio_channel_projection is not None:
        raise ValueError(
            "legacy mono PCM cannot carry channel provenance"
        )
    return None


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
        if isinstance(engine_close, dict):
            field_closed = engine_close.get("closed") is True
            terminal = engine_close.get("terminal")
        else:
            field_closed = bool(engine_close)
            terminal = None
        return {
            "closed": transport_closed or field_closed,
            "terminal_event_id": (
                terminal.authority_receipt_sha256
                if terminal is not None else None
            ),
            "auditory_motif": (
                terminal.as_record() if terminal is not None else None
            ),
            "recognized_form": None,
            "reply_admitted": None,
        }


def _reject_auditory_pcm_epoch(stream_id: str) -> dict[str, object]:
    """Terminally reject both continuity authorities after any stream fault."""
    with _auditory_pcm_epoch_lock:
        _auditory_pcm_streams.reject(stream_id)
        if _guala is None:
            return {
                "closed": True,
                "schema": "guala.auditory.rejected_pcm_epoch.v1",
                "stream_id": stream_id,
                "substrate": "unavailable",
            }
        if hasattr(_guala, "reject_auditory_pcm_stream"):
            rejected = _guala.reject_auditory_pcm_stream(stream_id)
        else:
            rejected = _guala.close_auditory_pcm_stream(
                stream_id,
                release_terminal=False,
            )
        return {
            "closed": bool(rejected.get("closed")),
            "schema": "guala.auditory.rejected_pcm_epoch.v1",
            "stream_id": stream_id,
            "substrate": rejected,
        }


@app.post("/api/v1/auditory/pcm/open")
async def auditory_pcm_stream_open():
    try:
        return {
            "ok": True,
            **_auditory_pcm_streams.open(),
            "visual_capture": _visual_capture_contract(),
        }
    except RuntimeError as error:
        return JSONResponse(
            status_code=409,
            content={"ok": False, "error": str(error)},
        )


@app.get("/api/v1/visual/capture-contract")
async def visual_capture_contract():
    return {"ok": True, **_visual_capture_contract()}


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
                "auditory_motif": result["auditory_motif"],
                "recognized_form": result["recognized_form"],
                "reply_admitted": result["reply_admitted"],
            }

    return await _run_lifecycle_executor(_close_serialized)


@app.post("/api/v1/auditory/binaural-pcm/open")
async def browser_binaural_pcm_stream_open():
    """Open a bounded two-channel candidate epoch with no ear authority."""
    try:
        return {
            "ok": True,
            **_browser_binaural_pcm_streams.open(),
        }
    except RuntimeError as error:
        return JSONResponse(
            status_code=409,
            content={"ok": False, "error": str(error)},
        )


@app.post("/api/v1/auditory/binaural-pcm/lineage")
async def browser_binaural_pcm_stream_lineage(
    req: BrowserBinauralLineageRequest,
):
    """Receipt runtime channel lineage without asserting physical ears."""

    def _register():
        with _browser_binaural_epoch_lock:
            receipt = _browser_binaural_pcm_streams.register_lineage(
                stream_id=req.stream_id,
                capture_session_sha256=req.capture_session_sha256,
                worklet_source_sha256=req.worklet_source_sha256,
                media_track_settings_sha256=(
                    req.media_track_settings_sha256
                ),
                mode=_BrowserBinauralLineageMode(req.mode),
                media_track_channel_count=(
                    req.media_track_channel_count
                ),
                worklet_input_channel_count=(
                    req.worklet_input_channel_count
                ),
                channel_order=tuple(req.channel_order),
            )
            return {
                "ok": True,
                "lineage_receipt_sha256": receipt.receipt_sha256,
                "channel_order": list(receipt.channel_order),
                "binaural_hardware_authority_proven": False,
                "cognition_authority": False,
            }

    try:
        return await _run_lifecycle_executor(_register)
    except ValueError as error:
        _browser_binaural_pcm_streams.reject(req.stream_id)
        return JSONResponse(
            status_code=400,
            content={"ok": False, "error": str(error)},
        )


@app.post("/api/v1/auditory/binaural-pcm/chunk")
async def browser_binaural_pcm_stream_chunk(
    req: BrowserBinauralChunkRequest,
):
    """Admit discrete bytes, then enforce the unproven-hardware refusal."""

    def _accept():
        try:
            left = base64.b64decode(req.left_pcm_b64, validate=True)
            right = base64.b64decode(req.right_pcm_b64, validate=True)
        except Exception as error:
            raise ValueError(
                "browser binaural PCM payload is not valid base64"
            ) from error
        with _browser_binaural_epoch_lock:
            accepted = _browser_binaural_pcm_streams.accept(
                stream_id=req.stream_id,
                lineage_receipt_sha256=(
                    req.lineage_receipt_sha256
                ),
                sequence=req.sequence,
                first_sample_index=req.first_sample_index,
                render_frame_start=req.render_frame_start,
                sample_rate_hz=req.sample_rate_hz,
                source_epoch_start_ns=req.source_epoch_start_ns,
                left_pcm_s16le=left,
                right_pcm_s16le=right,
            )
            view = _live_hearing_browser_integrator.hear_browser_binaural(
                accepted
            )
            left_projection = (
                _browser_discrete_channel_projection_owner.issue(
                    accepted,
                    target_mono_stream_id=req.target_mono_stream_id,
                )
            )
            return {
                "ok": True,
                "continuity": {
                    "status": "contiguous",
                    "stream_id": accepted.receipt.stream_id,
                    "sequence": accepted.receipt.sequence,
                    "first_sample_index": (
                        accepted.receipt.first_sample_index
                    ),
                    "sample_count": accepted.receipt.sample_count,
                    "render_frame_start": (
                        accepted.receipt.render_frame_start
                    ),
                    "receipt_sha256": (
                        accepted.receipt.receipt_sha256
                    ),
                },
                "binaural_hardware_authority_proven": False,
                "room_hearing": {
                    "state": view.room_outcome.state.value,
                    "reason": view.room_outcome.reason,
                    "authority": view.room_hearing_authority,
                    "outcome_receipt_sha256": (
                        view.room_outcome.authority_receipt_sha256
                    ),
                    "full_field_occurrence_receipt_sha256s": list(
                        view.full_field_occurrence_receipt_sha256s
                    ),
                },
                "production_exact_room_hearing_wired": (
                    view.production_live_wired
                ),
                "cognition_authority": view.cognition_authority,
                "meaning_authority": view.meaning_authority,
                "integration_receipt_sha256": (
                    view.authority_receipt_sha256
                ),
                "left_channel_projection": (
                    left_projection.as_record()
                ),
            }

    try:
        return await _run_lifecycle_executor(_accept)
    except ValueError as error:
        _browser_binaural_pcm_streams.reject(req.stream_id)
        return JSONResponse(
            status_code=400,
            content={"ok": False, "error": str(error)},
        )


@app.post("/api/v1/auditory/binaural-pcm/close")
async def browser_binaural_pcm_stream_close(
    req: BrowserBinauralCloseRequest,
):
    with _browser_binaural_epoch_lock:
        closed = _browser_binaural_pcm_streams.close(req.stream_id)
    return {
        "ok": closed,
        "continuity": "closed",
        "binaural_hardware_authority_proven": False,
        "room_hearing_authority": False,
        "cognition_authority": False,
    }


_LIVE_CAPTURE_MAX_DURATION_MS = 8_000
_LIVE_AUDIO_MAX_BYTES = 4 * 1024 * 1024
_LIVE_AUDIO_MAX_B64_CHARS = 4 * ((_LIVE_AUDIO_MAX_BYTES + 2) // 3)
from dsf_ai_service.substrate.visual_region_continuity import (
    MAX_VISUAL_FRAMES as _LIVE_VISUAL_MAX_FRAMES,
    MAX_VISUAL_IMAGE_BYTES as _LIVE_VISUAL_MAX_FRAME_BYTES,
    MIN_VISUAL_FRAMES as _LIVE_VISUAL_MIN_FRAMES,
    RETINA_COLUMNS as _LIVE_VISUAL_RETINA_COLUMNS,
    RETINA_ROWS as _LIVE_VISUAL_RETINA_ROWS,
)
_LIVE_VISUAL_MAX_B64_CHARS = 4 * (
    (_LIVE_VISUAL_MAX_FRAME_BYTES + 2) // 3
)
_LIVE_SENSORY_ORDER = (
    "sight",
    "sound",
    "touch",
    "smell",
    "taste",
    "body",
)
_LIVE_SENSORY_STATES = frozenset(
    ("observed", "sensor_unavailable", "unknown")
)
# One hard ingress allocation boundary covers the physically admissible audio
# bytes, all physically admissible camera bytes, base64 expansion, and bounded
# JSON transport metadata.  It is enforced while streaming, before Pydantic or
# an image decoder can allocate the supplied payload.
_LIVE_CAPTURE_REQUEST_MAX_BYTES = (
    _LIVE_AUDIO_MAX_B64_CHARS
    + _LIVE_VISUAL_MAX_FRAMES * _LIVE_VISUAL_MAX_B64_CHARS
    + 64 * 1024
)
from dsf_ai_service.substrate.ring_buffer import (
    DEFAULT_INPUT_RING_MAX_PENDING_BYTES as _INPUT_RING_MAX_PENDING_BYTES,
)
_LIVE_RING_WRITE_REQUEST_MAX_BYTES = (
    _INPUT_RING_MAX_PENDING_BYTES + 64 * 1024
)
_VIDEO_UPLOAD_MAX_BYTES = 30 * 1024 * 1024
_PICTURE_UPLOAD_MAX_BYTES = 10 * 1024 * 1024
_VIDEO_CAPTURE_MAX_SECONDS = 8
_VIDEO_FRAME_RATE = 15
_VIDEO_MAX_RETAINED_FRAMES = (
    _VIDEO_CAPTURE_MAX_SECONDS * _VIDEO_FRAME_RATE
)
_VIDEO_MAX_FRAME_FILE_BYTES = 128 * 1024


def _persist_picture_original(path, content):
    """Publish one bounded picture under the shared persistent-byte authority."""
    if not isinstance(content, bytes):
        raise TypeError("picture original must be bytes")
    if len(content) > _PICTURE_UPLOAD_MAX_BYTES:
        raise ValueError("picture original exceeds the 10 MiB boundary")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if _physical_byte_authority is None:
        with open(path, "wb") as picture_file:
            picture_file.write(content)
            picture_file.flush()
            os.fsync(picture_file.fileno())
        return
    _physical_byte_authority.atomic_replace_bytes(
        path,
        content,
        operation="publish_picture_ingress_original",
    )
_video_upload_read_lock = threading.Lock()
_video_upload_lock = threading.Lock()


def _visual_capture_contract():
    return {
        "schema": "guala.visual_capture_contract.v1",
        "minimum_frames": _LIVE_VISUAL_MIN_FRAMES,
        "maximum_frames": _LIVE_VISUAL_MAX_FRAMES,
        "maximum_frame_bytes": _LIVE_VISUAL_MAX_FRAME_BYTES,
        "canonical_width": 64,
        "canonical_height": 64,
        "retina_rows": _LIVE_VISUAL_RETINA_ROWS,
        "retina_columns": _LIVE_VISUAL_RETINA_COLUMNS,
    }


def _live_sensory_boundary_projection(settlement):
    """Project every exact sense state without granting field authority."""
    interpretations = tuple(settlement.interpretations)
    if tuple(item.sense for item in interpretations) != _LIVE_SENSORY_ORDER:
        raise ValueError("live settlement changed six-sense order")
    states = tuple(item.state for item in interpretations)
    if any(state not in _LIVE_SENSORY_STATES for state in states):
        raise ValueError("live settlement changed a sense boundary state")
    return dict(zip(_LIVE_SENSORY_ORDER, states, strict=True))


def _decode_visual_sequence(
    claims,
    *,
    source_time_start_ns,
    source_time_end_ns,
):
    """Validate one all-or-nothing camera sequence independently of audio."""
    from dsf_ai_service.substrate.visual_region_continuity import (
        canonical_visual_frames_from_claims,
    )
    return canonical_visual_frames_from_claims(
        tuple(claims),
        source_time_start_ns=source_time_start_ns,
        source_time_end_ns=source_time_end_ns,
    )


def _visual_claim_transport(value):
    """Separate bounded visual transport shape from the audio model."""
    if value is None:
        return False, (), None
    if not isinstance(value, list):
        return True, (), "visual sequence transport must be a list"
    if not _LIVE_VISUAL_MIN_FRAMES <= len(value) <= _LIVE_VISUAL_MAX_FRAMES:
        return True, (), "visual sequence must contain four through eight frames"
    normalized = []
    for claim in value:
        if isinstance(claim, GLVisualFrameClaim):
            normalized.append(
                {
                    "captured_ms": claim.captured_ms,
                    "frame_b64": claim.frame_b64,
                }
            )
        elif isinstance(claim, dict):
            normalized.append(dict(claim))
        else:
            return True, (), "every visual frame claim must be an object"
    return True, tuple(normalized), None


@app.middleware("http")
async def bounded_live_sensory_ingress(request, call_next):
    """Bound live sensory request memory before JSON and image decoding."""
    request_limits = {
        "/sound_frame": _LIVE_CAPTURE_REQUEST_MAX_BYTES,
        "/sight_frame": _LIVE_CAPTURE_REQUEST_MAX_BYTES,
        "/api/v1/auditory/binaural-pcm/chunk": (
            2 * _LIVE_CAPTURE_REQUEST_MAX_BYTES
        ),
        "/api/v1/gualaloom/ring/write": _LIVE_RING_WRITE_REQUEST_MAX_BYTES,
    }
    request_limit = request_limits.get(request.url.path)
    if request_limit is None:
        return await call_next(request)
    content_length = request.headers.get("content-length")
    if content_length is not None:
        try:
            declared_length = int(content_length)
        except ValueError:
            return JSONResponse(
                status_code=400,
                content={"ok": False, "error": "invalid content length"},
            )
        if declared_length < 0 or declared_length > request_limit:
            return JSONResponse(
                status_code=413,
                content={"ok": False, "error": "live sensory request exceeds its memory boundary"},
            )
    body = bytearray()
    async for chunk in request.stream():
        if len(body) + len(chunk) > request_limit:
            return JSONResponse(
                status_code=413,
                content={"ok": False, "error": "live sensory request exceeds its memory boundary"},
            )
        body.extend(chunk)
    request._body = bytes(body)
    return await call_next(request)


def _authoritative_capture_times(msg: GLMessage):
    """Validate only the audio interval; visual claims are independent."""
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
        return {
            "source_time_start_ns": start_ns,
            "source_time_end_ns": end_ns,
        }
    start_ms = msg.capture_started_ms
    end_ms = msg.capture_ended_ms
    if start_ms is None or end_ms is None:
        raise ValueError("capture start and end timestamps are required")
    if (isinstance(start_ms, bool) or isinstance(end_ms, bool)
            or end_ms <= start_ms
            or end_ms - start_ms > _LIVE_CAPTURE_MAX_DURATION_MS):
        raise ValueError("capture interval is invalid or exceeds eight seconds")
    return {
        "source_time_start_ns": int(start_ms) * 1_000_000,
        "source_time_end_ns": int(end_ms) * 1_000_000,
    }


@app.post("/sight_frame")
async def sight_frame(msg: GLMessage):
    """Admit one complete temporal retina sequence; never a singleton frame."""
    remote = _is_remote()
    recognition = {
        "status": "unavailable",
        "reason": "no_experience_grown_visual_thing_relation",
        "source": "camera_stream",
    }
    if not remote and _guala is None:
        return JSONResponse(
            status_code=503,
            content={
                "ok": False,
                "error": "guala_not_ready",
                "object_name_recognition": recognition,
                "articulatory_playback": None,
            },
        )
    visual_claimed, claims, visual_transport_error = _visual_claim_transport(
        msg.sight_frames
    )
    if not visual_claimed:
        return {
            "ok": False,
            "error": "a bounded temporal visual sequence is required",
            "visual_region": {"status": "rejected", "reason": "missing_sequence"},
            "object_name_recognition": recognition,
            "articulatory_playback": None,
        }
    if visual_transport_error:
        return {
            "ok": False,
            "error": visual_transport_error,
            "visual_region": {
                "status": "rejected",
                "reason": visual_transport_error,
            },
            "object_name_recognition": recognition,
            "articulatory_playback": None,
        }
    start_ms = msg.capture_started_ms
    end_ms = msg.capture_ended_ms
    if (
        isinstance(start_ms, bool)
        or not isinstance(start_ms, int)
        or isinstance(end_ms, bool)
        or not isinstance(end_ms, int)
        or end_ms <= start_ms
        or end_ms - start_ms > _LIVE_CAPTURE_MAX_DURATION_MS
    ):
        return {
            "ok": False,
            "error": "visual capture interval is invalid",
            "object_name_recognition": recognition,
            "articulatory_playback": None,
        }
    source_start_ns = start_ms * 1_000_000
    source_end_ns = end_ms * 1_000_000
    if remote:
        client = _get_substrate_client()
        try:
            result = await client.call(
                "ring_write",
                kind="sight_sequence",
                source=msg.visual_source,
                data={
                    "frames": list(claims),
                    "visual_source": msg.visual_source,
                    "source_time_start_ns": source_start_ns,
                    "source_time_end_ns": source_end_ns,
                },
                timeout=3.0,
            )
            if not isinstance(result, dict):
                raise TypeError("ring write returned a non-object result")
            result["object_name_recognition"] = recognition
            result["articulatory_playback"] = None
            return result
        except Exception:
            return {
                "ok": False,
                "error": "ring write failed",
                "object_name_recognition": recognition,
                "articulatory_playback": None,
            }
    if not _frame_backpressure_acquire("sight"):
        return {"ok": False, "dropped": True,
                "reason": "backpressure — visual processing at capacity",
                "n_dropped": _frame_dropped["sight"],
                "object_name_recognition": recognition,
                "articulatory_playback": None}
    def _decode():
        t0 = time.time()
        try:
            frames = _decode_visual_sequence(
                claims,
                source_time_start_ns=source_start_ns,
                source_time_end_ns=source_end_ns,
            )
            sight_receipt = _guala.process_live_visual_region_sequence(
                frames,
                source_time_start_ns=source_start_ns,
                source_time_end_ns=source_end_ns,
            )
            if not sight_receipt or not sight_receipt.get("accepted"):
                raise RuntimeError("visual region authority accepted no field")
            articulatory_playback = (
                _consume_same_request_sight_articulatory_playback(
                    sight_receipt,
                    response_authority=(
                        _guala
                        ._consequence_evoked_articulatory_response
                    ),
                )
            )
            print(f"[sight-sequence] {time.time()-t0:.3f}s")
            return {"ok": True, "tick": _guala.tick,
                    "raw_sight": "accepted",
                    "visual_region": sight_receipt.get("visual_region"),
                    "object_name_recognition": recognition,
                    "articulatory_response": sight_receipt.get(
                        "articulatory_response"
                    ),
                    "articulatory_playback": articulatory_playback}
        except Exception as e:
            try:
                _guala.record_live_visual_rejection(
                    error_type=type(e).__name__, reason=str(e)
                )
            except Exception as rejection_error:
                _guala._log_substrate_event(
                    "visual_rejection_telemetry_failed",
                    error_type=type(rejection_error).__name__,
                    error=str(rejection_error),
                )
            return {"ok": False, "error": str(e),
                    "visual_region": {"status": "rejected", "reason": str(e)},
                    "object_name_recognition": recognition,
                    "articulatory_playback": None}
    try:
        with _live_interaction_scope():
            return await _run_lifecycle_executor(_decode)
    finally:
        _frame_backpressure_release("sight")


@app.post("/sound_frame")
async def sound_frame(msg: GLMessage):
    """Stream raw sound through continuous exact full-field hearing.

    Structural motif firing remains presemantic physical evidence.  It grants
    no word, transcript, meaning, reply, or action authority.
    """

    b64_data = (msg.text or "").strip()
    src = msg.source or "ambient"
    auditory_event_boundary = msg.capture_purpose
    recognition = _spoken_word_recognition_report(src)
    visual_claimed, visual_claims, visual_transport_error = (
        _visual_claim_transport(msg.sight_frames)
    )
    legacy_sight_claimed = msg.sight_b64 is not None
    visual_claimed = visual_claimed or legacy_sight_claimed
    if len(b64_data) > _LIVE_AUDIO_MAX_B64_CHARS:
        if msg.audio_encoding == "pcm_s16le" and msg.audio_stream_id:
            await _run_lifecycle_executor(
                _reject_auditory_pcm_epoch, msg.audio_stream_id
            )
        return {"ok": False, "error": "audio capture exceeds the bounded request size",
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
            capture_times = _authoritative_capture_times(msg)
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
                      "sight_frames": list(visual_claims),
                      "visual_claimed": visual_claimed,
                      "visual_source": msg.visual_source,
                      "visual_transport_error": visual_transport_error,
                      "legacy_sight_claimed": legacy_sight_claimed,
                      **capture_times},
                timeout=3.0)
            if not isinstance(result, dict):
                raise TypeError("ring write returned a non-object result")
            result["spoken_word_recognition"] = recognition
            if result.get("ok") is True and visual_claimed:
                if visual_transport_error or legacy_sight_claimed:
                    rejection = visual_transport_error or (
                        "legacy singleton sight cannot establish a temporal field"
                    )
                    result["causal_boundary"] = "queued_sound_visual_rejected"
                    result["visual_region"] = {
                        "status": "rejected",
                        "reason": rejection,
                    }
                else:
                    result["causal_boundary"] = "queued_audiovisual"
            elif result.get("ok") is True:
                result["causal_boundary"] = "queued_sound"
            else:
                result["causal_boundary"] = "unsettled"
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
    try:
        capture_times = _authoritative_capture_times(msg)
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
        profile_started = time.perf_counter()
        profile_durations = {}
        profile_emitted = False

        def _record_profile_stage(name, started):
            profile_durations[name] = (
                time.perf_counter() - started
            )

        def _emit_profile(outcome):
            nonlocal profile_emitted
            if profile_emitted:
                return
            profile_emitted = True
            profile_durations["total"] = (
                time.perf_counter() - profile_started
            )
            ordered = " ".join(
                f"{name}={profile_durations[name]:.6f}"
                for name in (
                    "transport",
                    "context_begin",
                    "visual",
                    "sound",
                    "settlement",
                    "terminal",
                    "status",
                    "reply",
                    "speech_boundary",
                    "total",
                )
                if name in profile_durations
            )
            print(
                "[sound-frame-stage] "
                f"outcome={outcome} "
                f"pcm={msg.audio_encoding == 'pcm_s16le'} "
                f"visual_claimed={visual_claimed} "
                f"capture_purpose={auditory_event_boundary} "
                f"{ordered}"
            )

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
            channel_projection = None
            if msg.audio_encoding == "pcm_s16le":
                try:
                    channel_projection = (
                        _verify_browser_channel_projection(
                            msg,
                            audio_bytes,
                        )
                    )
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
                _emit_profile("decode_failed")
                return {"ok": False, "error": "decode_failed",
                        "spoken_word_recognition": recognition}
            _record_profile_stage("transport", profile_started)
            recognition_future = None
            observed_senses = []
            sensory_errors = {}
            boundary_settled = False
            settlement = None
            sound_receipt = None
            visual_frames = ()
            retired_cognition = {
                "native_exact_field_preserved": True,
                "reason": "legacy_python_cognition_retired",
                "schema": "guala.retired_cognition.unavailable.v1",
                "status": "unavailable",
            }
            passive_thing_learning = dict(retired_cognition)
            sound_evoked_causal_thing = dict(retired_cognition)
            context_id = f"sense:av:{src}:{time.time_ns():x}"
            unavailable = ["touch", "smell", "taste", "body"]
            context_begin_started = time.perf_counter()
            _guala.window_manager.begin_context(
                context_id,
                trigger_reason="audiovisual_capture",
                context_detail={
                    "experience_origin": "live_audiovisual",
                    "auditory_event_boundary": auditory_event_boundary,
                    "source": src,
                    "visual_source": (
                        msg.visual_source if visual_claimed else None
                    ),
                    "source_time_start_ns": capture_times[
                        "source_time_start_ns"],
                    "source_time_end_ns": capture_times[
                        "source_time_end_ns"],
                    "sensor_unavailable": unavailable,
                },
            )
            _record_profile_stage(
                "context_begin",
                context_begin_started,
            )
            try:
                visual_started = time.perf_counter()
                if visual_claimed:
                    try:
                        if visual_transport_error:
                            raise ValueError(visual_transport_error)
                        if legacy_sight_claimed:
                            raise ValueError(
                                "legacy singleton sight cannot establish a temporal field"
                            )
                        visual_frames = _decode_visual_sequence(
                            visual_claims,
                            source_time_start_ns=capture_times[
                                "source_time_start_ns"],
                            source_time_end_ns=capture_times[
                                "source_time_end_ns"],
                        )
                        sight_receipt = (
                            _guala.process_live_visual_region_sequence(
                                visual_frames,
                                source_time_start_ns=capture_times[
                                    "source_time_start_ns"],
                                source_time_end_ns=capture_times[
                                    "source_time_end_ns"],
                                auditory_pcm_continuity=(
                                    pcm_acceptance.receipt
                                    if pcm_acceptance is not None
                                    else None
                                ),
                            )
                        )
                        if sight_receipt and sight_receipt.get("accepted"):
                            observed_senses.append("sight")
                    except Exception as sight_error:
                        try:
                            _guala.record_live_visual_rejection(
                                error_type=type(sight_error).__name__,
                                reason=str(sight_error),
                            )
                        except Exception as rejection_error:
                            _guala._log_substrate_event(
                                "visual_rejection_telemetry_failed",
                                error_type=type(rejection_error).__name__,
                                error=str(rejection_error),
                            )
                        sensory_errors["sight"] = (
                            f"{type(sight_error).__name__}: {sight_error}"
                        )
                        _guala._log_substrate_event(
                            "visual_sequence_rejected_in_causal_window",
                            error_type=type(sight_error).__name__,
                            error=str(sight_error),
                        )
                _record_profile_stage("visual", visual_started)
                sound_started = time.perf_counter()
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
                    _record_profile_stage("sound", sound_started)
            finally:
                settlement_started = time.perf_counter()
                try:
                    if pcm_acceptance is None:
                        closed_window_id, settlement = (
                            _guala.window_manager.end_context(
                                context_id,
                                "audiovisual_capture_complete",
                                return_settlement=True,
                            )
                        )
                    else:
                        closed_window_id, settlement = (
                            _guala.settle_live_audiovisual_context(
                                context_id,
                                "audiovisual_capture_complete",
                                auditory_transport=(
                                    pcm_acceptance.receipt
                                ),
                                auditory_pcm_s16le=(
                                    pcm_acceptance.pcm_s16le
                                ),
                            )
                        )
                    if (
                        closed_window_id is None
                        or settlement is None
                        or settlement.assembly_id != f"causal-{closed_window_id}"
                    ):
                        raise RuntimeError(
                            "closed sensory window has no matching settlement"
                        )
                    verified_causal_transaction = (
                        _guala._continuous_auditory_causal_transaction(
                            transport=(
                                pcm_acceptance.receipt
                                if pcm_acceptance is not None
                                else None
                            ),
                            settlement=settlement,
                        )
                    )
                    if verified_causal_transaction is None:
                        settlement.verify()
                    else:
                        verified_causal_transaction.verify_linkage(
                            settlement
                        )
                    observed_senses = [
                        item.sense
                        for item in settlement.interpretations
                        if item.state == "observed"
                    ]
                    boundary_settled = True
                except Exception as settlement_error:
                    sensory_errors["settlement"] = (
                        f"{type(settlement_error).__name__}: {settlement_error}"
                    )
                    _guala.window_manager.discard_unsettled_context(
                        context_id,
                        "live_audiovisual_settlement_failed",
                    )
                finally:
                    _record_profile_stage(
                        "settlement",
                        settlement_started,
                    )
            causal_boundary = (
                "unsettled" if not boundary_settled
                else "audiovisual" if observed_senses == ["sight", "sound"]
                else observed_senses[0] if len(observed_senses) == 1
                else "unknown"
            )
            stream_settlement_receipt = None
            auditory_motif_result = None
            terminal_started = time.perf_counter()
            if (
                pcm_acceptance is not None
                and boundary_settled
                and "sound" in observed_senses
            ):
                (
                    stream_settlement_receipt,
                    auditory_motif_result,
                ) = _guala.advance_continuous_auditory_terminal(
                    pcm_s16le=pcm_acceptance.pcm_s16le,
                    transport=pcm_acceptance.receipt,
                    settlement=settlement,
                )
                stream_settlement_receipt.verify()
                auditory_motif_result.verify()
            _record_profile_stage("terminal", terminal_started)
            status_started = time.perf_counter()
            auditory_status = _guala.auditory_l5_status()
            current_experience = getattr(
                _guala, "_latest_auditory_l5_experience", None)
            deterministic_recognition = {
                **_spoken_word_recognition_report(src),
                "status": "not_established_presemantic_motifs_only",
                "recognized_form": None,
                "candidate_labels": [],
                "meaning_authority": False,
                "transcript_authority": False,
                "reason": (
                    "exact auditory motif firing is presemantic and cannot "
                    "be reported as a word, kind, or meaning"
                ),
            }
            if auditory_motif_result is not None:
                deterministic_recognition = {
                    **_spoken_word_recognition_report(src),
                    "status": "not_established_presemantic_motifs_only",
                    "recognized_form": None,
                    "candidate_labels": [],
                    "experience_id": None,
                    "l5_experience_id": auditory_status.get(
                        "latest_experience_id"
                    ),
                    "kind_id": None,
                    "component_count": None,
                    "meaning_authority": False,
                    "transcript_authority": False,
                    "source": "exact_presemantic_recurrent_motif",
                    "reason": (
                        "motif neuron IDs and occurrence spans are not words "
                        "or semantic recognition"
                    ),
                }
            _record_profile_stage("status", status_started)
            reply_started = time.perf_counter()
            _record_profile_stage("reply", reply_started)
            if recognition_future is None:
                _emit_profile("settled")
                print(f"[sound-frame] {time.time()-t0:.3f}s")
                result = {
                    "ok": "sound" in observed_senses and boundary_settled,
                    "tick": _guala.tick,
                    "raw_sound": (
                        "accepted" if "sound" in observed_senses else "failed"),
                    "causal_boundary": causal_boundary,
                    "capture_purpose": auditory_event_boundary,
                    "visual_source": (
                        msg.visual_source if visual_claimed else None
                    ),
                    "observed_senses": observed_senses,
                    "sensory_boundary": (
                        _live_sensory_boundary_projection(settlement)
                    ),
                    "spoken_word_recognition": deterministic_recognition,
                    "auditory_motif": (
                        auditory_motif_result.as_record()
                        if auditory_motif_result is not None
                        else None
                    ),
                    "auditory_l5": auditory_status,
                    "passive_thing_learning": (
                        passive_thing_learning
                    ),
                    "sound_evoked_causal_thing": (
                        sound_evoked_causal_thing
                    ),
                    "visual_region": (
                        _guala._latest_visual_region_observation
                        if "sight" in observed_senses
                        else {
                            "status": "rejected",
                            "reason": sensory_errors.get("sight"),
                        }
                        if visual_claimed
                        else {"status": "sensor_unavailable"}
                    ),
                }
                if pcm_acceptance is not None:
                    if (
                        not boundary_settled
                        or stream_settlement_receipt is None
                        or auditory_motif_result is None
                    ):
                        root_errors = "; ".join(
                            f"{name}={reason}"
                            for name, reason in sorted(
                                sensory_errors.items()
                            )
                        ) or "auditory terminal authority was not produced"
                        raise RuntimeError(
                            "continuous PCM has no authenticated causal "
                            f"terminal: {root_errors}"
                        )
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
                        "auditory_motif_firing_state": (
                            auditory_motif_result.firing_state
                        ),
                        "auditory_motif_learning_state": (
                            auditory_motif_result.learning_state
                        ),
                        "auditory_motif_result_receipt_sha256": (
                            auditory_motif_result.authority_receipt_sha256
                        ),
                        "meaning_authority": False,
                        "transcript_authority": False,
                        "channel_mode": msg.audio_channel_mode,
                        "channel_projection_receipt_sha256": (
                            channel_projection.authority_receipt_sha256
                            if channel_projection is not None else None
                        ),
                        "binaural_hardware_authority_proven": False,
                        "room_hearing_authority": False,
                    }
                if sensory_errors:
                    result["sensory_errors"] = sensory_errors
                return result
        except Exception as e:
            _emit_profile(f"error:{type(e).__name__}")
            rejection_error = None
            if msg.audio_encoding == "pcm_s16le" and msg.audio_stream_id:
                try:
                    _reject_auditory_pcm_epoch(msg.audio_stream_id)
                except BaseException as cleanup_error:
                    rejection_error = {
                        "error": str(cleanup_error),
                        "error_type": type(cleanup_error).__name__,
                    }
            response = {
                "ok": False,
                "error": str(e),
                "error_type": type(e).__name__,
                "spoken_word_recognition": recognition,
            }
            if rejection_error is not None:
                response["auditory_rejection_cleanup_error"] = (
                    rejection_error
                )
            return response
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
    return _guala_publication_file("gualaloom.html")


@app.get("/api/v1/gualaloom/observation")
async def gualaloom_observation():
    """One authoritative read-only conversation/body/world observation."""
    if _is_remote():
        client = _get_substrate_client()
        return await client.call("observation_snapshot")
    if _guala is None:
        return {
            "schema": "guala.observation_snapshot.v5",
            "status": "unavailable",
            "reason": "embedded_substrate_unavailable",
        }
    return await _run_lifecycle_executor(_guala.observation_snapshot)






# C2: serve individual pictures by ID (refs-not-base64)


# ════════════════════════════════════════════════════════════════
# UNPAUSE admin endpoints (GL-BRIEF-UNPAUSE-WC-20260613-01)
# ════════════════════════════════════════════════════════════════

# Runtime repause flag (survives within the process; env var alone isn't enough)
_runtime_decay_paused = None  # None = defer to env var















@app.post("/api/v1/gualaloom/admin/backup", dependencies=[Depends(_api_key_dep)])
async def admin_backup():
    """Request one bounded authenticated immutable generation checkpoint."""
    if not _REQUIRE_SEALED_STATE:
        raise HTTPException(
            status_code=409,
            detail=(
                "legacy flat-file backup is retired; authenticated "
                "generation authority is required"
            ),
        )
    _gl_init()
    if _guala is None:
        return JSONResponse({"error": "not ready"}, status_code=503)
    admission_token = _administrative_checkpoint_admission.admit()
    if admission_token is None:
        raise HTTPException(
            status_code=409,
            detail=(
                "an authenticated administrative checkpoint is already "
                "in progress"
            ),
            headers={"Retry-After": "5"},
        )

    async def _authoritative_backup():
        try:
            try:
                await _run_lifecycle_executor(
                    _settled_authoritative_checkpoint,
                    "admin-backup",
                )
            except Exception as error:
                traceback.print_exc()
                print(
                    f"[backup] authoritative checkpoint failed: {error}",
                    flush=True,
                )
        finally:
            _administrative_checkpoint_admission.release(
                admission_token)

    try:
        _schedule_mutating_background(
            lambda: _authoritative_backup(),
            name="admin-authoritative-backup",
        )
    except BaseException:
        _administrative_checkpoint_admission.release(
            admission_token)
        raise
    return JSONResponse(
        status_code=202,
        content={
            "backup": "accepted",
            "message": "Bounded immutable generation checkpoint started.",
        },
    )






# (B.1) Atlas surgery — GL-CMD-ATLAS-SURGERY-EVE-20260627-18



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



# ════════════════════════════════════════════════════════════════
# v7: Substrate event stream (SSE) + sleep endpoint
# GUALALOOM-V7-AUTONOMY-WC-2026-06-06
# ════════════════════════════════════════════════════════════════











# ════════════════════════════════════════════════════════════════
# v7 Phase 5: Upload endpoints
# GUALALOOM-V7-AUTONOMY-WC-2026-06-06
# ════════════════════════════════════════════════════════════════









class CausalActionBindingReviewRequest(BaseModel):
    binding_id: str
    decision: Literal["confirm", "revoke"]
    source: Literal["joe", "wc"]
    nonce: str

    class Config:
        extra = "forbid"


class EmbodiedPositionRequest(BaseModel):
    x_mm: int
    y_mm: int
    z_mm: int = 0

    class Config:
        extra = "forbid"


class EmbodiedPoseRequest(BaseModel):
    position: EmbodiedPositionRequest
    heading_millidegrees: int

    class Config:
        extra = "forbid"


class EmbodiedActionExperienceRequest(BaseModel):
    tutor_id: Literal["joe", "wc"]
    nonce: str
    port_id: str
    operation: Literal["move", "pick", "place"]
    duration_microseconds: int
    target_pose: Optional[EmbodiedPoseRequest] = None
    object_id: Optional[str] = None
    target_position: Optional[EmbodiedPositionRequest] = None

    class Config:
        extra = "forbid"


class EmbodiedOralContactRequest(BaseModel):
    tutor_id: Literal["joe", "wc"]
    nonce: str
    object_id: str
    duration_microseconds: int

    class Config:
        extra = "forbid"


LEARNED_BODY_ACT_TRANSPORT_SCHEMA = (
    "guala.embodied_action_experience.learned_body_act_transport.v1"
)
_RAW_VOCAL_CAUSAL_ACT_SCHEMA = (
    "guala.embodied_action_experience.vocal_causal_act.v1"
)
_RAW_VOCAL_CAUSAL_ACT_FIELDS = frozenset({
    "act_receipt",
    "additional_world_mutation",
    "pcm_s16le",
    "pcm_sha256",
    "program_custody_receipt_sha256",
    "reason",
    "retained_pcm_bytes",
    "sample_count",
    "sample_rate_hz",
    "schema",
    "selection_authority_hmac_sha256",
    "selection_authority_receipt_sha256",
    "state",
})
_LEARNED_BODY_ACT_COMMON_FIELDS = frozenset({
    "additional_world_mutation",
    "reason",
    "schema",
    "selection_authority_hmac_sha256",
    "selection_authority_receipt_sha256",
    "state",
})
_LEARNED_BODY_ACT_EMITTED_FIELDS = frozenset({
    *_LEARNED_BODY_ACT_COMMON_FIELDS,
    "act_receipt",
    "pcm_s16le_base64",
    "pcm_sha256",
    "program_custody_receipt_sha256",
    "retained_pcm_bytes",
    "sample_count",
    "sample_rate_hz",
})


def _canonical_lower_sha256(value, label):
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(
            character not in "0123456789abcdef"
            for character in value
        )
    ):
        raise ValueError(f"{label} changed")
    return value


def _typed_full_vocal_act_receipt(value):
    del value
    raise RuntimeError(
        "legacy Python learned vocal act is permanently retired"
    )


def _verify_learned_body_act_transport(value):
    del value
    raise RuntimeError(
        "legacy Python learned vocal act is permanently retired"
    )


def _embodied_action_transport(result):
    """Expose physical action evidence without retired vocal cognition."""

    if not isinstance(result, dict):
        raise ValueError("embodied action result is not a mapping")
    has_raw = "vocal_causal_act" in result
    has_transport = "learned_body_act" in result
    if has_raw or has_transport:
        raise RuntimeError(
            "legacy Python learned vocal act is permanently retired"
        )
    return dict(result)


@app.get("/api/v1/auditory/status")
async def auditory_l5_status():
    if _is_remote():
        client = _get_substrate_client()
        return await client.call("auditory_l5_status")
    if _guala is None:
        raise HTTPException(status_code=503, detail="guala_not_ready")
    return _guala.auditory_l5_status()


def _retired_cognition_http_response(capability: str) -> JSONResponse:
    """Return one local/remote invariant permanent-retirement response."""
    return JSONResponse(
        status_code=410,
        content={
            "capability": capability,
            "native_exact_field_preserved": True,
            "reason": "legacy_python_cognition_retired",
            "schema": "guala.retired_cognition.unavailable.v1",
            "status": "unavailable",
        },
    )


@app.post(
    "/api/v1/embodiment/action-experience",
    dependencies=[Depends(_api_key_dep)],
)
async def embodied_action_experience(
    req: EmbodiedActionExperienceRequest,
):
    """Execute and retain one exact physical W1 action without binding it."""
    command_payload = _embodied_action_command_payload(req)
    return await _execute_embodied_action_experience(
        req,
        command_payload=command_payload,
    )


@app.post(
    _EMBODIED_READING_ROUTE_PATH,
    dependencies=[Depends(_api_key_dep)],
)
async def embodied_reading_lesson(request: Request):
    """Reject the retired Python cognition lesson contract immediately."""
    return _retired_cognition_http_response("embodied_reading_lesson")


@app.get(
    _EMBODIED_READING_ROUTE_PATH + "/{operation_id}",
    dependencies=[Depends(_api_key_dep)],
)
async def poll_embodied_reading_lesson(operation_id: str):
    """Reject polling for the retired Python cognition lesson contract."""
    return _retired_cognition_http_response("embodied_reading_lesson")


@app.post(
    _PHYSICAL_SURFACE_LESSON_ROUTE_PATH,
    dependencies=[Depends(_api_key_dep)],
)
async def physical_surface_lesson(request: Request):
    """Reject the retired Python cognition tutoring contract immediately."""
    return _retired_cognition_http_response("physical_surface_tutoring")


@app.get(
    _PHYSICAL_SURFACE_LESSON_ROUTE_PATH + "/{operation_id}",
    dependencies=[Depends(_api_key_dep)],
)
async def poll_physical_surface_lesson(operation_id: str):
    """Reject polling for the retired Python cognition tutoring contract."""
    return _retired_cognition_http_response("physical_surface_tutoring")


def _embodied_action_command_payload(
    req: EmbodiedActionExperienceRequest,
):
    """Encode the exact physical command accepted by both action lanes."""
    from dsf_ai_service.substrate.embodiment_world import (
        MoveCommand,
        PickCommand,
        PlaceCommand,
        PoseMM,
        PositionMM,
        encode_command,
    )

    def _position(value):
        return PositionMM(value.x_mm, value.y_mm, value.z_mm)

    try:
        if req.operation == "move":
            if (
                req.target_pose is None
                or req.object_id is not None
                or req.target_position is not None
            ):
                raise ValueError("move requires only target_pose")
            command = MoveCommand(
                target_pose=PoseMM(
                    _position(req.target_pose.position),
                    req.target_pose.heading_millidegrees,
                ),
                duration_microseconds=req.duration_microseconds,
            )
        elif req.operation == "pick":
            if (
                req.object_id is None
                or req.target_pose is not None
                or req.target_position is not None
            ):
                raise ValueError("pick requires only object_id")
            command = PickCommand(
                object_id=req.object_id,
                duration_microseconds=req.duration_microseconds,
            )
        else:
            if (
                req.object_id is None
                or req.target_position is None
                or req.target_pose is not None
            ):
                raise ValueError(
                    "place requires only object_id and target_position"
                )
            command = PlaceCommand(
                object_id=req.object_id,
                target_position=_position(req.target_position),
                duration_microseconds=req.duration_microseconds,
            )
        command_payload = encode_command(command)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return command_payload


async def _execute_embodied_action_experience(
    req: EmbodiedActionExperienceRequest,
    *,
    command_payload,
):
    """Run the existing durable physical action and verify its transport."""
    if _is_remote():
        client = _get_substrate_client()
        result = await client.call(
            "embodied_action_experience",
            tutor_id=req.tutor_id,
            nonce=req.nonce,
            port_id=req.port_id,
            command_payload_base64=base64.b64encode(
                command_payload
            ).decode("ascii"),
        )
        if isinstance(result, dict) and result.get("error"):
            raise HTTPException(status_code=409, detail=result["error"])
        try:
            return _embodied_action_transport(result)
        except ValueError as error:
            raise HTTPException(
                status_code=409,
                detail=str(error),
            ) from error
    if _guala is None:
        raise HTTPException(status_code=503, detail="guala_not_ready")

    def _experience_and_commit():
        return _guala.durably_experience_embodied_action(
            tutor_id=req.tutor_id,
            nonce=req.nonce,
            port_id=req.port_id,
            command_payload=command_payload,
            state_dir=STATE_DIR,
        )

    try:
        result = await _run_lifecycle_executor(
            _experience_and_commit
        )
        return _embodied_action_transport(result)
    except PermissionError as error:
        raise HTTPException(status_code=403, detail=str(error)) from error
    except (RuntimeError, ValueError) as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


from dsf_ai_service.learned_body_act_trial import (
    LEARNED_BODY_ACT_TRIAL_ACCEPTED_SCHEMA,
    LEARNED_BODY_ACT_TRIAL_REQUEST_SCHEMA,
    LearnedBodyActTrialCapacityError,
    LearnedBodyActTrialRegistry,
    LearnedBodyActTrialUnavailableError,
    LearnedBodyActTrialUnknownError,
    canonical_trial_request_sha256,
)


_learned_body_act_trial_operations = LearnedBodyActTrialRegistry()


@app.post(
    "/api/v1/embodiment/learned-body-act-trial",
    dependencies=[Depends(_api_key_dep)],
)
async def start_learned_body_act_trial(
    req: EmbodiedActionExperienceRequest,
):
    """Start one bounded content-neutral physical-act trial."""
    command_payload = _embodied_action_command_payload(req)
    command_payload_base64 = base64.b64encode(
        command_payload
    ).decode("ascii")
    request_sha256 = canonical_trial_request_sha256({
        "schema": LEARNED_BODY_ACT_TRIAL_REQUEST_SCHEMA,
        "tutor_id": req.tutor_id,
        "nonce": req.nonce,
        "port_id": req.port_id,
        "command_payload_base64": command_payload_base64,
    })
    try:
        operation_id = _learned_body_act_trial_operations.create(
            request_sha256
        )
    except LearnedBodyActTrialCapacityError as error:
        raise HTTPException(
            status_code=429,
            detail=str(error),
            headers={"Retry-After": "300"},
        ) from error

    async def _execute_trial():
        if not _learned_body_act_trial_operations.mark_running(
            operation_id
        ):
            return
        try:
            result = await _execute_embodied_action_experience(
                req,
                command_payload=command_payload,
            )
        except HTTPException:
            _learned_body_act_trial_operations.fail(
                operation_id,
                "execution_rejected",
            )
        except Exception:
            _learned_body_act_trial_operations.fail(
                operation_id,
                "execution_failed",
            )
        else:
            _learned_body_act_trial_operations.complete(
                operation_id,
                result,
            )

    try:
        _schedule_mutating_background(
            lambda: _execute_trial(),
            name=f"learned-body-act-trial-{operation_id}",
        )
    except BaseException:
        _learned_body_act_trial_operations.discard_unstarted(
            operation_id
        )
        raise
    return JSONResponse(
        status_code=202,
        content={
            "schema": LEARNED_BODY_ACT_TRIAL_ACCEPTED_SCHEMA,
            "state": "accepted",
            "operation_id": operation_id,
            "request_sha256": request_sha256,
        },
    )


@app.get(
    "/api/v1/embodiment/learned-body-act-trial/{operation_id}",
    dependencies=[Depends(_api_key_dep)],
)
async def poll_learned_body_act_trial(operation_id: str):
    """Poll and consume one terminal content-neutral trial result."""
    try:
        status_code, content = (
            _learned_body_act_trial_operations.poll(operation_id)
        )
    except LearnedBodyActTrialUnavailableError as error:
        raise HTTPException(
            status_code=410,
            detail=str(error),
        ) from error
    except LearnedBodyActTrialUnknownError as error:
        raise HTTPException(
            status_code=404,
            detail="unknown learned body-act trial operation",
        ) from error
    return JSONResponse(status_code=status_code, content=content)


@app.post(
    "/api/v1/embodiment/ground-latest-sight-contact",
    dependencies=[Depends(_api_key_dep)],
)
async def ground_latest_sight_contact(request: Request):
    """Ground retained live sight through current settled body contact."""
    content_length = request.headers.get("content-length")
    if content_length not in (None, "0"):
        raise HTTPException(
            status_code=400,
            detail="sight grounding accepts no request content",
        )
    if await request.body():
        raise HTTPException(
            status_code=400,
            detail="sight grounding accepts no request content",
        )
    if not _GUALALOOM_API_KEY:
        raise HTTPException(
            status_code=503,
            detail="authenticated sight grounding control is unavailable",
        )
    if _is_remote():
        client = _get_substrate_client()
        result = await client.call("ground_latest_sight_contact")
        if isinstance(result, dict) and result.get("error"):
            raise HTTPException(status_code=409, detail=result["error"])
        return result
    if _guala is None:
        raise HTTPException(status_code=503, detail="guala_not_ready")

    def _ground_and_commit():
        return _guala.durably_ground_latest_retained_sight_to_contact(
            state_dir=STATE_DIR,
        )

    try:
        return await _run_lifecycle_executor(_ground_and_commit)
    except (RuntimeError, ValueError) as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


@app.post(
    "/api/v1/embodiment/oral-contact",
    dependencies=[Depends(_api_key_dep)],
)
async def embodied_oral_contact(req: EmbodiedOralContactRequest):
    """Execute one explicit physical mouth-surface contact."""
    if _is_remote():
        raise HTTPException(
            status_code=501,
            detail=(
                "remote oral-contact transport has no authenticated "
                "material-action boundary"
            ),
        )
    if _guala is None:
        raise HTTPException(status_code=503, detail="guala_not_ready")

    def _execute_contact():
        return _guala.experience_oral_material_contact(
            tutor_id=req.tutor_id,
            nonce=req.nonce,
            object_id=req.object_id,
            duration_microseconds=req.duration_microseconds,
            state_dir=STATE_DIR,
        )

    try:
        return await _run_lifecycle_executor(_execute_contact)
    except PermissionError as error:
        raise HTTPException(status_code=403, detail=str(error)) from error
    except (RuntimeError, ValueError) as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


def _require_canonical_sha256(value: str, field_name: str) -> None:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise ValueError(f"{field_name} must be canonical SHA-256")


def _decode_causal_inquiry_transport(
    req,
):
    from dsf_ai_service.substrate.embodiment_world import (
        MAX_VOCAL_SAMPLE_COUNT,
    )
    raise RuntimeError(
        "legacy Python causal-inquiry transport is permanently retired"
    )

    maximum_pcm_bytes = MAX_VOCAL_SAMPLE_COUNT * 2
    maximum_pcm_base64_characters = (
        4 * ((maximum_pcm_bytes + 2) // 3)
    )
    capability_record = req.client_capability
    try:
        for field_name, value in (
            ("opaque_token", capability_record.opaque_token),
            (
                "authority_hmac_sha256",
                capability_record.authority_hmac_sha256,
            ),
            (
                "authority_receipt_sha256",
                capability_record.authority_receipt_sha256,
            ),
        ):
            _require_canonical_sha256(value, field_name)
        if (
            len(req.nonce_base64) != 44
            or not req.companion_pcm_s16le_base64
            or len(req.companion_pcm_s16le_base64)
            > maximum_pcm_base64_characters
        ):
            raise ValueError(
                "causal inquiry consequence transport exceeds boundary"
            )
        nonce = base64.b64decode(req.nonce_base64, validate=True)
        pcm_s16le = base64.b64decode(
            req.companion_pcm_s16le_base64,
            validate=True,
        )
        if (
            base64.b64encode(nonce).decode("ascii")
            != req.nonce_base64
            or base64.b64encode(pcm_s16le).decode("ascii")
            != req.companion_pcm_s16le_base64
            or len(nonce) != 32
            or not pcm_s16le
            or len(pcm_s16le) % 2
            or len(pcm_s16le) > maximum_pcm_bytes
        ):
            raise ValueError(
                "causal inquiry consequence transport is noncanonical"
            )
        capability = PendingBodyOwnedVocalClientCapability(
            opaque_token=capability_record.opaque_token,
            authority_hmac_sha256=(
                capability_record.authority_hmac_sha256
            ),
            authority_receipt_sha256=(
                capability_record.authority_receipt_sha256
            ),
        )
    except (ValueError, binascii.Error) as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return capability, nonce, pcm_s16le


def _body_owned_vocal_request_one_response(delivery):
    from dsf_ai_service.substrate.embodiment_world import (
        MAX_VOCAL_SAMPLE_COUNT,
    )
    raise RuntimeError(
        "legacy Python causal-inquiry transport is permanently retired"
    )

    if not isinstance(delivery, BodyOwnedVocalRequestOneDelivery):
        raise TypeError("causal inquiry transient act is not typed")
    pcm_s16le = delivery.pcm_s16le
    capability = delivery.client_capability
    if (
        not isinstance(pcm_s16le, bytes)
        or not pcm_s16le
        or len(pcm_s16le) % 2
        or len(pcm_s16le) > MAX_VOCAL_SAMPLE_COUNT * 2
        or delivery.sample_count != len(pcm_s16le) // 2
        or _hashlib.sha256(pcm_s16le).hexdigest()
        != delivery.pressure_sha256
        or not isinstance(
            capability,
            PendingBodyOwnedVocalClientCapability,
        )
    ):
        raise ValueError("causal inquiry transient act changed physical PCM")
    for field_name, value in (
        (
            "pending_authority_receipt_sha256",
            delivery.pending_authority_receipt_sha256,
        ),
        (
            "candidate_authority_receipt_sha256",
            delivery.candidate_authority_receipt_sha256,
        ),
        (
            "need_authority_receipt_sha256",
            delivery.need_authority_receipt_sha256,
        ),
        (
            "witness_authority_receipt_sha256",
            delivery.witness_authority_receipt_sha256,
        ),
        ("pressure_sha256", delivery.pressure_sha256),
        ("opaque_token", capability.opaque_token),
        (
            "authority_hmac_sha256",
            capability.authority_hmac_sha256,
        ),
        (
            "authority_receipt_sha256",
            capability.authority_receipt_sha256,
        ),
    ):
        _require_canonical_sha256(value, field_name)
    return {
        "schema": "guala.causal_inquiry.transient_act.v1",
        "pcm_s16le_base64": base64.b64encode(
            pcm_s16le
        ).decode("ascii"),
        "client_capability": {
            "opaque_token": capability.opaque_token,
            "authority_hmac_sha256": (
                capability.authority_hmac_sha256
            ),
            "authority_receipt_sha256": (
                capability.authority_receipt_sha256
            ),
        },
        "pending_authority_receipt_sha256": (
            delivery.pending_authority_receipt_sha256
        ),
        "candidate_authority_receipt_sha256": (
            delivery.candidate_authority_receipt_sha256
        ),
        "need_authority_receipt_sha256": (
            delivery.need_authority_receipt_sha256
        ),
        "witness_authority_receipt_sha256": (
            delivery.witness_authority_receipt_sha256
        ),
        "pressure_sha256": delivery.pressure_sha256,
        "sample_count": delivery.sample_count,
    }


def _body_owned_vocal_request_two_response(result):
    raise RuntimeError(
        "legacy Python causal-inquiry transport is permanently retired"
    )

    if (
        not isinstance(result, BodyOwnedVocalRequestTwoResult)
        or result.inquiry_resolved is not True
        or result.autonomous_reuse_available is not True
    ):
        raise ValueError(
            "causal inquiry consequence did not close physical learning"
        )
    response = asdict(result)
    for field_name, value in response.items():
        if field_name in {
            "inquiry_resolved",
            "autonomous_reuse_available",
        }:
            continue
        _require_canonical_sha256(value, field_name)
    return response


@app.post(
    "/api/v1/causal-inquiry/transient-act",
    dependencies=[Depends(_api_key_dep)],
)
async def causal_inquiry_transient_act(request: Request):
    """Reject the retired Python cognition vocal-act contract."""
    return _retired_cognition_http_response(
        "causal_inquiry_transient_act"
    )


@app.post(
    "/api/v1/causal-inquiry/transient-consequence",
    dependencies=[Depends(_api_key_dep)],
)
async def causal_inquiry_transient_consequence(
    request: Request,
):
    """Reject the retired Python cognition vocal-consequence contract."""
    return _retired_cognition_http_response(
        "causal_inquiry_transient_consequence"
    )




@app.post(
    "/api/v1/causal-action/review-binding",
    dependencies=[Depends(_api_key_dep)],
)
async def causal_action_review_binding(
    req: CausalActionBindingReviewRequest,
):
    """Durably apply explicit teacher judgment to one observed action."""
    if _is_remote():
        raise HTTPException(
            status_code=501,
            detail="remote action review has no durability barrier",
        )
    if _guala is None:
        raise HTTPException(status_code=503, detail="guala_not_ready")

    def _review_and_commit():
        return _guala.durably_review_causal_action_binding(
            binding_id=req.binding_id,
            decision=req.decision,
            source=req.source,
            nonce=req.nonce,
            state_dir=STATE_DIR,
        )

    try:
        return await _run_lifecycle_executor(_review_and_commit)
    except PermissionError as error:
        raise HTTPException(status_code=403, detail=str(error)) from error
    except (RuntimeError, ValueError) as error:
        raise HTTPException(status_code=409, detail=str(error)) from error



















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
        from dsf_ai_service.v4.guala_physical_runtime import (
            GualaBootIdentityUnreadableHalt,
            GualaBootStateIntegrityHalt,
        )
    except ImportError:
        return None
    named = (
        GualaBootIdentityUnreadableHalt,
        GualaBootStateIntegrityHalt,
        PersistentStorageReadinessHalt,
    )
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
    _start_app_lifecycle_task(_eager_init(), name="guala-eager-init")

    # The isolated V7 session engine is retired. It has no background
    # lifecycle, persistence writer, or admission path in the live service.

    # Persistence backstop in the lifecycle executor. The 60-second lane
    # publishes only after a new causal tick; an unchanged organism performs
    # no serialization or generation publication. The independently bounded
    # cold-safety cadence remains 30 minutes.
    def _do_hot_save_and_compact():
        """Persist only a causally changed, exclusively settled organism."""
        with _guala.settled_external_persistence_transaction():
            if not _guala.settled_hot_persistence_checkpoint_required():
                return None
            t0 = time.time()
            _guala.save_hot_state(STATE_DIR)
            t1 = time.time()
        total_dt = t1 - t0
        print(f"[save-hot] {total_dt:.2f}s core={total_dt:.2f}s")
        return total_dt

    def _do_save_and_compact():
        """Cold lane: one full owner-scoped state save."""
        if _REQUIRE_SEALED_STATE:
            with _guala.settled_external_persistence_transaction():
                if not (
                    _guala
                    .settled_cold_persistence_checkpoint_required()
                ):
                    return None
                t0 = time.time()
                certificate = _checkpoint_authoritative_runtime(
                    "periodic-cold")
                checkpoint_dt = time.time() - t0
                total_dt = time.time() - t0
            print(
                f"[save-cold-authoritative] {total_dt:.2f}s "
                f"checkpoint={checkpoint_dt:.2f}s "
                f"generation={certificate['generation_uuid']} "
                f"tick={certificate['tick']}"
            )
            return total_dt
        with _guala.settled_external_persistence_transaction():
            if not _guala.settled_cold_persistence_checkpoint_required():
                return None
            t0 = time.time()
            results = _guala.save_full_state(STATE_DIR)
            t1 = time.time()
        core_dt = t1 - t0
        grids_dt = results.get("_grids_dt", 0.0) if isinstance(results, dict) else 0.0
        total_dt = t1 - t0
        print(f"[save] {total_dt:.2f}s core={core_dt:.2f}s "
              f"grids={grids_dt:.2f}s")
        return total_dt

    async def _periodic_v6_save():
        save_count = 0
        loop = asyncio.get_event_loop()
        cadence = _PeriodicColdCheckpointCadence(
            monotonic_now=loop.time(),
            wall_now=time.time(),
        )
        _periodic_cold_checkpoint_status["next_eligible_at"] = (
            cadence.next_wall
        )
        while True:
            await asyncio.sleep(60)
            if _guala is None:
                continue
            now = loop.time()
            wall_now = time.time()
            do_cold = cadence.admit(
                monotonic_now=now,
                wall_now=wall_now,
            )
            _periodic_cold_checkpoint_status["next_eligible_at"] = (
                cadence.next_wall
            )
            try:
                if do_cold:
                    _periodic_cold_checkpoint_status.update({
                        "active": True,
                        "last_attempt_at": wall_now,
                        "last_failure": None,
                        "last_failure_at": None,
                    })
                    cold_result = await _run_lifecycle_executor(
                        _do_save_and_compact)
                    if cold_result is None:
                        _periodic_cold_checkpoint_status[
                            "last_unchanged_skip_at"
                        ] = time.time()
                    else:
                        _periodic_cold_checkpoint_status[
                            "last_success_at"
                        ] = time.time()
                else:
                    _periodic_hot_checkpoint_status.update({
                        "active": True,
                        "last_attempt_at": wall_now,
                        "last_failure": None,
                        "last_failure_at": None,
                    })
                    hot_result = await _run_lifecycle_executor(
                        _do_hot_save_and_compact
                    )
                    if hot_result is None:
                        _periodic_hot_checkpoint_status[
                            "last_unchanged_skip_at"
                        ] = time.time()
                    else:
                        _periodic_hot_checkpoint_status.update({
                            "last_success_at": time.time(),
                            "last_success_duration_seconds": hot_result,
                        })
            except Exception as e:
                if do_cold:
                    _periodic_cold_checkpoint_status.update({
                        "last_failure": str(e)[:500],
                        "last_failure_at": time.time(),
                    })
                else:
                    _periodic_hot_checkpoint_status.update({
                        "last_failure": str(e)[:500],
                        "last_failure_at": time.time(),
                    })
                print(f"[save] error: {e}")
            finally:
                if do_cold:
                    _periodic_cold_checkpoint_status["active"] = False
                else:
                    _periodic_hot_checkpoint_status["active"] = False
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
    """Reject the retired unauthenticated local-generation fallback."""
    del state_dir
    raise RuntimeError(
        "unauthenticated local-generation recovery is retired; restore only "
        "an authenticated immutable generation while no owner runs"
    )


def _restore_from_s3(state_dir):
    """Reject the retired mutable flat-file restore consumer."""
    raise RuntimeError(
        "flat S3 restore is retired; use a verified immutable generation "
        "restore while no owner is running"
    )


def _backup_to_s3(state_dir):
    """Reject the retired mutable flat-file backup producer."""
    raise RuntimeError(
        "flat S3 backup is retired; use the authenticated generation "
        "checkpoint authority"
    )


@app.on_event("shutdown")
async def shutdown():
    """Quiesce and seal the active immutable organism generation."""
    import asyncio
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
            await asyncio.to_thread(_guala.strict_shutdown, 120.0)
        except Exception as error:
            print(f"[shutdown] strict local quiescence failed: {error}")

    if snapshot["state"] == "SEALED":
        _deployment_lifecycle.retire()


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


























@app.get("/health")
async def health():
    # Always return 200 for ALB liveness checks.
    result = {
        "status": "ok" if _init_complete else "initializing",
        "service": "dsf-ai",
        "version": "1.0.0",
        "ready": _init_complete,
    }
    result["auditory_pcm_transport"] = _auditory_pcm_streams.status()
    result["browser_binaural_pcm_transport"] = (
        _browser_binaural_pcm_streams.status()
    )
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
            proof = await asyncio.to_thread(
                _production_runtime_readiness_snapshot
            )
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


def _verified_storage_cutover_status():
    """Prove the three inseparable production persistence authorities."""
    if not _REQUIRE_SEALED_STATE:
        raise RuntimeError("sealed content-addressed persistence is disabled")
    if (
        _authoritative_cold_store is None
        or _live_recovery_store is None
        or _physical_byte_authority is None
    ):
        raise RuntimeError("production persistence authority is incomplete")
    cold = _authoritative_cold_store.persistence_status()
    live = _live_recovery_store.persistence_status()
    physical = _physical_byte_authority.configuration()
    if cold.get("content_addressed") is not True:
        raise RuntimeError("cold generation store is not content-addressed")
    if live.get("content_addressed") is not True:
        raise RuntimeError("live recovery store is not content-addressed")
    if (
        physical.get("ceiling_bytes")
        != APPROVED_PERSISTENT_STORAGE_CEILING_BYTES
    ):
        raise RuntimeError("shared physical-byte refusal is not the approved 5 GiB")
    for name, status in (("cold", cold), ("live", live)):
        if status.get("physical_bytes") != physical:
            raise RuntimeError(
                f"{name} store does not use the shared physical-byte authority"
            )
    reconciliation = _remote_generation_reconciliation
    version_aware = (
        isinstance(reconciliation, dict)
        and reconciliation.get("version_aware") is True
    )
    read_only_reuse = (
        isinstance(reconciliation, dict)
        and reconciliation.get("read_only_remote_reuse_verified") is True
    )
    if (
        not isinstance(reconciliation, dict)
        or reconciliation.get("executed") is not True
        or version_aware == read_only_reuse
    ):
        raise RuntimeError(
            "remote generation reconciliation or exact read-only reuse "
            "proof is unproven"
        )
    return {
        "schema": "guala.production.storage_cutover.v1",
        "cold_generation": cold,
        "live_recovery": live,
        "physical_bytes": physical,
        "remote_reconciliation": dict(reconciliation),
        "predecessor_live_recovery_retirement": (
            ()
            if _predecessor_live_recovery_retirement is None
            else tuple(_predecessor_live_recovery_retirement)
        ),
        "retired_flat_full_copy_producer": True,
    }


_CURRENT_SCHEMA_LINEAGE_MEMBER_KEYS = {
    "generation",
    "identity",
    "manifest_sha256",
    "generation_tick",
    "deployment_seal_schema",
    "state_revision",
    "causal_state_sha256",
    "operational_metadata_sha256",
    "seal_hmac_sha256",
}
_CURRENT_SCHEMA_EXTENSION_KEYS = {
    "schema",
    "migration_markers",
    "predecessor",
    "successor",
}


def _same_generation_reference(left, right):
    return all(
        getattr(left, field) == getattr(right, field)
        for field in (
            "generation_uuid",
            "identity",
            "manifest_sha256",
            "tick",
        )
    )


def _authenticated_schema_lineage_member(
    generation,
    authority,
    certificate,
    *,
    name,
):
    """Bind one verified cold generation to its exact HMAC deployment seal."""
    from dsf_ai_service.substrate.deployment_generation import (
        DEPLOYMENT_SEAL_SCHEMA,
    )

    if authority is None:
        raise RuntimeError(
            f"authenticated schema {name} has no causal authority"
        )
    expected = {
        "generation_uuid": generation.generation_uuid,
        "identity": generation.identity,
        "manifest_sha256": generation.manifest_sha256,
        "tick": generation.tick,
        "state_revision": authority.state_revision,
        "causal_state_sha256": authority.causal_state_sha256,
        "operational_metadata_sha256": (
            authority.operational_metadata_sha256
        ),
        "attempt_operational_metadata_sha256": (
            authority.operational_metadata_sha256
        ),
    }
    if certificate.get("schema") != DEPLOYMENT_SEAL_SCHEMA:
        raise RuntimeError(
            f"authenticated schema {name} has no current causal seal"
        )
    for field, expected_value in expected.items():
        if certificate.get(field) != expected_value:
            raise RuntimeError(
                f"authenticated schema {name} seal {field} mismatch"
            )
    return {
        "generation": generation.generation_uuid,
        "identity": generation.identity,
        "manifest_sha256": generation.manifest_sha256,
        "generation_tick": generation.tick,
        "deployment_seal_schema": certificate["schema"],
        "state_revision": authority.state_revision,
        "causal_state_sha256": authority.causal_state_sha256,
        "operational_metadata_sha256": (
            authority.operational_metadata_sha256
        ),
        "seal_hmac_sha256": certificate["seal_hmac_sha256"],
    }


def _build_authenticated_current_schema_extension_certificate(
    *,
    predecessor,
    successor_certificate,
    migration_markers,
):
    """Capture the one reviewed equal-tick successor and its exact lineage."""
    if (
        not isinstance(migration_markers, tuple)
        or not migration_markers
        or tuple(sorted(migration_markers)) != migration_markers
        or len(migration_markers) != len(set(migration_markers))
        or not set(migration_markers).issubset(
            _REVIEWED_CURRENT_SCHEMA_MIGRATIONS
        )
    ):
        raise RuntimeError(
            "authenticated current-schema lineage has unreviewed markers"
        )
    if _authoritative_cold_store is None:
        raise RuntimeError(
            "authenticated current-schema lineage has no cold authority"
        )
    from dsf_ai_service.substrate.deployment_generation import (
        load_generation_deployment_seal,
    )

    with _authoritative_cold_store.exclusive_read_only_transaction(
        require_predecessor=True,
    ) as cold_state:
        if cold_state.predecessor is None:
            raise RuntimeError(
                "authenticated current-schema lineage has no predecessor"
            )
        if not _same_generation_reference(
            cold_state.predecessor,
            predecessor,
        ):
            raise RuntimeError(
                "authenticated current-schema predecessor changed"
            )
        if (
            _deployment_baseline_generation is None
            or not _same_generation_reference(
                cold_state.current,
                _deployment_baseline_generation,
            )
        ):
            raise RuntimeError(
                "authenticated current-schema successor is not CURRENT"
            )
        key = _deploy_hmac_key()
        predecessor_seal = load_generation_deployment_seal(
            GENERATION_STORE_ROOT,
            cold_state.predecessor.generation_uuid,
            hmac_key=key,
        )
        successor_seal = load_generation_deployment_seal(
            GENERATION_STORE_ROOT,
            cold_state.current.generation_uuid,
            hmac_key=key,
        )
        if any(
            successor_certificate.get(field)
            != successor_seal.get(field)
            for field in successor_seal
        ):
            raise RuntimeError(
                "authenticated current-schema successor receipt changed"
            )
        predecessor_record = _authenticated_schema_lineage_member(
            cold_state.predecessor,
            cold_state.predecessor_authority,
            predecessor_seal,
            name="predecessor",
        )
        successor_record = _authenticated_schema_lineage_member(
            cold_state.current,
            cold_state.current_authority,
            successor_seal,
            name="successor",
        )
    if (
        successor_record["identity"] != predecessor_record["identity"]
        or successor_record["generation_tick"]
        != predecessor_record["generation_tick"]
        or successor_record["generation"]
        == predecessor_record["generation"]
        or successor_record["manifest_sha256"]
        == predecessor_record["manifest_sha256"]
        or successor_record["state_revision"]
        != predecessor_record["state_revision"] + 1
        or successor_record["causal_state_sha256"]
        == predecessor_record["causal_state_sha256"]
    ):
        raise RuntimeError(
            "authenticated current-schema successor lineage is invalid"
        )
    retained = set(
        (_remote_generation_reconciliation or {}).get(
            "retained_generation_uuids",
            (),
        )
    )
    if not {
        predecessor_record["generation"],
        successor_record["generation"],
    }.issubset(retained):
        raise RuntimeError(
            "authenticated current-schema lineage is not remotely retained"
        )
    value = {
        "schema": _AUTHENTICATED_CURRENT_SCHEMA_EXTENSION_SCHEMA,
        "migration_markers": list(migration_markers),
        "predecessor": predecessor_record,
        "successor": successor_record,
    }
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("ascii")


def _assert_readiness_lineage_member(record, certificate, *, name):
    if (
        not isinstance(record, dict)
        or set(record) != _CURRENT_SCHEMA_LINEAGE_MEMBER_KEYS
    ):
        raise RuntimeError(
            f"authenticated current-schema {name} field set changed"
        )
    expected = {
        "generation": certificate.get("generation_uuid"),
        "identity": certificate.get("identity"),
        "manifest_sha256": certificate.get("manifest_sha256"),
        "generation_tick": certificate.get("tick"),
        "deployment_seal_schema": certificate.get("schema"),
        "state_revision": certificate.get("state_revision"),
        "causal_state_sha256": certificate.get(
            "causal_state_sha256"
        ),
        "operational_metadata_sha256": certificate.get(
            "operational_metadata_sha256"
        ),
        "seal_hmac_sha256": certificate.get("seal_hmac_sha256"),
    }
    if record != expected:
        raise RuntimeError(
            f"authenticated current-schema {name} seal changed"
        )
    if certificate.get("attempt_operational_metadata_sha256") != record[
        "operational_metadata_sha256"
    ]:
        raise RuntimeError(
            f"authenticated current-schema {name} attempt authority changed"
        )


def _current_authenticated_schema_extension_readiness(
    *,
    current,
    current_certificate,
    storage_cutover,
):
    """Return lineage only while the reviewed boot successor is exact CURRENT."""
    encoded = _authenticated_current_schema_extension_certificate
    if encoded is None:
        return None
    try:
        value = json.loads(encoded)
    except (TypeError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise RuntimeError(
            "authenticated current-schema lineage certificate is unreadable"
        ) from error
    if (
        not isinstance(value, dict)
        or set(value) != _CURRENT_SCHEMA_EXTENSION_KEYS
        or value.get("schema")
        != _AUTHENTICATED_CURRENT_SCHEMA_EXTENSION_SCHEMA
    ):
        raise RuntimeError(
            "authenticated current-schema lineage certificate changed"
        )
    migration_markers = value.get("migration_markers")
    if (
        not isinstance(migration_markers, list)
        or not migration_markers
        or migration_markers != sorted(migration_markers)
        or len(migration_markers) != len(set(migration_markers))
        or not set(migration_markers).issubset(
            _REVIEWED_CURRENT_SCHEMA_MIGRATIONS
        )
    ):
        raise RuntimeError(
            "authenticated current-schema migration markers changed"
        )
    successor = value.get("successor")
    if not isinstance(successor, dict):
        raise RuntimeError(
            "authenticated current-schema successor proof is absent"
        )
    if current.generation_uuid != successor.get("generation"):
        # A later ordinary checkpoint is healthy but is not the one reviewed
        # equal-tick successor.  It receives no schema-extension authority.
        return None
    predecessor = value.get("predecessor")
    from dsf_ai_service.substrate.deployment_generation import (
        load_generation_deployment_seal,
    )
    predecessor_certificate = load_generation_deployment_seal(
        GENERATION_STORE_ROOT,
        predecessor.get("generation") if isinstance(predecessor, dict) else "",
        hmac_key=_deploy_hmac_key(),
    )
    _assert_readiness_lineage_member(
        predecessor,
        predecessor_certificate,
        name="predecessor",
    )
    _assert_readiness_lineage_member(
        successor,
        current_certificate,
        name="successor",
    )
    if (
        successor["identity"] != predecessor["identity"]
        or successor["generation_tick"]
        != predecessor["generation_tick"]
        or successor["generation"] == predecessor["generation"]
        or successor["manifest_sha256"]
        == predecessor["manifest_sha256"]
        or successor["state_revision"]
        != predecessor["state_revision"] + 1
        or successor["causal_state_sha256"]
        == predecessor["causal_state_sha256"]
    ):
        raise RuntimeError(
            "authenticated current-schema readiness lineage is invalid"
        )
    remote = storage_cutover.get("remote_reconciliation", {})
    retained = set(remote.get("retained_generation_uuids", ()))
    if not {
        predecessor["generation"],
        successor["generation"],
    }.issubset(retained):
        raise RuntimeError(
            "authenticated current-schema readiness lineage is not retained"
        )
    return value


def _native_neuron_readiness():
    """Project DSF delivery separately from unavailable neuronal cognition."""
    readiness = getattr(_guala, "native_resident_readiness", None)
    if not callable(readiness):
        return {
            "available": False,
            "joint_field_count": 0,
            "joint_neuron_count": 0,
            "dsf_delivery_count": 0,
            "complete_neuron_fractal_count": 0,
            "recurrent_complete_neuron_fractal_count": 0,
            "joint_transition_sha256": None,
            "episode_relation_candidate_sha256": None,
        }
    record = readiness()
    if not isinstance(record, dict) or record.get("available") is not True:
        raise RuntimeError("native resident organism is not available")
    latest = getattr(_guala, "_latest_native_resident_transition", None)
    if not isinstance(latest, dict):
        raise RuntimeError("native resident observation is absent")
    for field in (
        "state_sha256",
        "state_bytes",
        "fabric_sha256",
        "fabric_bytes",
        "fabric_generation",
        "mounted_generation",
        "organism_tick",
        "joint_field_count",
        "joint_neuron_count",
        "cognitive_ordinal",
        "cognitive_trace_count",
        "cognitive_mosaic_count",
    ):
        if latest.get(field) != record.get(field):
            raise RuntimeError(
                f"native resident observation {field} differs from active state"
            )
    return {
        "available": True,
        "persistence_schema": "guala.native_resident_organism.v3",
        "persistence": record["persistence"],
        "resource_admission": record["resource_admission"],
        "state_sha256": record["state_sha256"],
        "state_bytes": record["state_bytes"],
        "fabric_sha256": record["fabric_sha256"],
        "fabric_bytes": record["fabric_bytes"],
        "fabric_generation": record["fabric_generation"],
        "mounted_generation": record["mounted_generation"],
        "organism_tick": record["organism_tick"],
        "outcome": "resident_native_organism_active",
        "last_transition": latest.get("transition"),
        "joint_field_count": record["joint_field_count"],
        "joint_neuron_count": record["joint_neuron_count"],
        "dsf_delivery_count": latest.get(
            "dsf_delivery_count", 0
        ),
        "complete_neuron_fractal_count": latest.get(
            "complete_neuron_fractal_count", 0
        ),
        "recurrent_complete_neuron_fractal_count": latest.get(
            "recurrent_complete_neuron_fractal_count", 0
        ),
        "cognitive_ordinal": record["cognitive_ordinal"],
        "cognitive_trace_count": record["cognitive_trace_count"],
        "cognitive_mosaic_count": record["cognitive_mosaic_count"],
        "formation_activation_count": record[
            "formation_activation_count"
        ],
        "partial_cue_reassembly_count": record[
            "partial_cue_reassembly_count"
        ],
        "python_callback_count": record["python_callback_count"],
        "joint_transition_sha256": None,
        "episode_relation_candidate_sha256": None,
    }


def _production_runtime_proof_under_authority(nonce=None):
    """Prove code, task, image, native state, CURRENT, and live identity."""
    del nonce
    if not _init_complete or _init_error is not None or _guala is None:
        raise RuntimeError(_init_error or "Guala initialization is incomplete")
    if _deployment_lifecycle.snapshot()["state"] != "RUNNING":
        raise RuntimeError("deployment lifecycle is not RUNNING")
    resident_readiness = getattr(_guala, "native_resident_readiness", None)
    if (
        not callable(resident_readiness)
        or resident_readiness().get("available") is not True
    ):
        raise RuntimeError("live organism has no verified native state")
    if (_loaded_generation is None
            or _deployment_baseline_generation is None
            or _live_recovery_store is None
            or _authoritative_cold_store is None):
        raise RuntimeError("no immutable generation was materialized")

    from dsf_ai_service.substrate.deployment_generation import (
        load_generation_deployment_seal,
    )
    generation_certificate = load_generation_deployment_seal(
        GENERATION_STORE_ROOT,
        _deployment_baseline_generation.generation_uuid,
        hmac_key=_deploy_hmac_key(),
    )
    expected = {
        "generation_uuid": _deployment_baseline_generation.generation_uuid,
        "identity": _deployment_baseline_generation.identity,
        "manifest_sha256": _deployment_baseline_generation.manifest_sha256,
        "tick": _deployment_baseline_generation.tick,
    }
    for field, value in expected.items():
        if generation_certificate.get(field) != value:
            raise RuntimeError(f"deployment seal {field} mismatch")
    cold_current = _authoritative_cold_store.assert_current_reference(
        _deployment_baseline_generation
    )
    for field, value in expected.items():
        if getattr(cold_current, field) != value:
            raise RuntimeError(
                f"authoritative cold CURRENT {field} mismatch")
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
    storage_cutover = _verified_storage_cutover_status()
    authenticated_schema_extension = (
        _current_authenticated_schema_extension_readiness(
            current=_deployment_baseline_generation,
            current_certificate=generation_certificate,
            storage_cutover=storage_cutover,
        )
    )

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
        "native_state": True,
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
        "periodic_cold_checkpoint": dict(
            _periodic_cold_checkpoint_status
        ),
        "periodic_hot_checkpoint": dict(
            _periodic_hot_checkpoint_status
        ),
        "authenticated_current_schema_extension": (
            authenticated_schema_extension
        ),
        "native_neuron": _native_neuron_readiness(),
        "storage_cutover": storage_cutover,
        **task,
    }


def _production_runtime_proof(nonce=None):
    """Read one coherent persistence generation while checkpoints publish."""
    with _persistence_authority_lock:
        return _production_runtime_proof_under_authority(nonce=nonce)


def _production_runtime_readiness_snapshot():
    """Return current proof or the last coherent proof during publication.

    The ALB calls ``/ready`` as its target-health probe.  Waiting behind a
    full checkpoint can exceed that probe's timeout even though the live
    owner, its last committed generation, and its process are healthy.
    A non-blocking authority acquisition publishes a fresh immutable proof.
    If a persistence commit currently owns the authority, return only the
    last proof that completed under that same authority and name its age.
    No half-published generation is observed and no unverified success is
    invented.
    """
    global _last_verified_runtime_readiness
    acquired = _persistence_authority_lock.acquire(blocking=False)
    if acquired:
        try:
            proof = _production_runtime_proof_under_authority()
            verified_at_monotonic_ns = time.monotonic_ns()
            _last_verified_runtime_readiness = (
                dict(proof),
                verified_at_monotonic_ns,
            )
            return {
                **proof,
                "persistence_commit_in_progress": False,
                "readiness_proof_state": "current_committed_generation",
                "readiness_snapshot_age_ms": 0,
            }
        finally:
            _persistence_authority_lock.release()
    cached = _last_verified_runtime_readiness
    if cached is None:
        raise RuntimeError(
            "persistence commit is in progress before any readiness proof"
        )
    proof, verified_at_monotonic_ns = cached
    return {
        **dict(proof),
        "persistence_commit_in_progress": True,
        "readiness_proof_state": "last_verified_committed_generation",
        "readiness_snapshot_age_ms": max(
            0,
            (time.monotonic_ns() - verified_at_monotonic_ns) // 1_000_000,
        ),
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
            proof = await asyncio.to_thread(
                _production_runtime_proof,
                nonce=nonce,
            )
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
        "tick": _guala.tick,
        "runtime": "physical_substrate",
        "causal_play": "event_driven",
    }

def _deploy_hmac_key():
    """Derive a fixed-width seal key from the authenticated control secret."""
    if not _GUALALOOM_API_KEY:
        raise RuntimeError("deployment control credential is not configured")
    return _hashlib.sha256(
        ("guala-deployment-seal-v1\0" + _GUALALOOM_API_KEY).encode("utf-8")
    ).digest()


def _seal_receipt_with_rebased_live_recovery(certificate, rebased):
    """Bind one exact post-seal recovery overlay into the seal receipt."""
    if not isinstance(certificate, dict):
        raise RuntimeError("deployment seal certificate is not an object")
    if rebased is None:
        raise RuntimeError(
            "deployment seal did not publish a live-recovery overlay"
        )
    try:
        generation_uuid = rebased.generation_uuid
        identity = rebased.identity
        manifest_sha256 = rebased.manifest_sha256
        tick = rebased.tick
    except AttributeError as error:
        raise RuntimeError(
            "post-seal live-recovery generation is incomplete"
        ) from error
    if (
        not isinstance(generation_uuid, str)
        or not generation_uuid
        or not isinstance(identity, str)
        or not identity
        or not isinstance(manifest_sha256, str)
        or len(manifest_sha256) != 64
        or any(
            character not in "0123456789abcdef"
            for character in manifest_sha256
        )
        or isinstance(tick, bool)
        or not isinstance(tick, int)
        or tick < 0
    ):
        raise RuntimeError(
            "post-seal live-recovery generation metadata is invalid"
        )
    if identity != certificate.get("identity"):
        raise RuntimeError(
            "post-seal live-recovery identity differs from the seal"
        )
    if tick != certificate.get("tick"):
        raise RuntimeError(
            "post-seal live-recovery tick differs from the seal"
        )
    if generation_uuid == certificate.get("generation_uuid"):
        raise RuntimeError(
            "post-seal live recovery did not form a distinct overlay"
        )
    if manifest_sha256 == certificate.get("manifest_sha256"):
        raise RuntimeError(
            "post-seal live-recovery manifest reused the full seal"
        )
    return {
        **certificate,
        "active_recovery_generation": generation_uuid,
        "active_recovery_is_overlay": True,
        "active_recovery_manifest_sha256": manifest_sha256,
        "active_recovery_tick": tick,
    }


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


def _copy_generation_auxiliary_tree(
        source, destination, *, suffixes, admission):
    """Copy a finite, validated auxiliary tree without following links."""
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
            admission.copy_regular_file(
                path,
                os.path.join(target_root, name),
            )
            copied += 1
    return copied


def _copy_generation_file(
        source, destination, *, admission, required=False):
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
    admission.copy_regular_file(source, destination)
    return True


def _write_runtime_generation_stage(stage, admission, *, runtime=None):
    """Write the complete runtime recovery contract into one private stage."""
    target = _guala if runtime is None else runtime
    if target is None:
        raise RuntimeError("runtime generation stage has no Guala owner")
    with target.bounded_persistence_admission(admission):
        target.save_full_state(str(stage), publish_generation=False)
    if getattr(target, "is_asleep", False):
        with admission.open_text(stage / target.SLEEPING_MARKER) as marker:
            json.dump(
                {
                    "sleep_tick": int(target.tick),
                    "sleep_ts": time.time(),
                },
                marker,
            )
    if not os.path.isfile(stage / target.IDENTITY_FILE):
        raise RuntimeError(
            "full-state save omitted the required identity record")
    for relative_path in (
            "guala_runtime_config.json",
            "curriculum_progress.json",
            "curriculum.json",
            "world_state.json"):
        source = os.path.join(STATE_DIR, relative_path)
        _copy_generation_file(
            source,
            stage / relative_path,
            admission=admission,
        )
    _copy_generation_auxiliary_tree(
        os.path.join(STATE_DIR, "sounds"),
        os.path.join(stage, "sounds"),
        suffixes=(".audio",),
        admission=admission,
    )
    prepared = getattr(
        target,
        "_prepared_authoritative_full_checkpoint",
        None,
    )
    if not isinstance(prepared, dict):
        raise RuntimeError(
            "runtime generation stage has no frozen checkpoint instant")
    captured_tick = prepared.get("tick")
    if (
        isinstance(captured_tick, bool)
        or not isinstance(captured_tick, int)
        or captured_tick < 0
    ):
        raise RuntimeError(
            "runtime generation stage checkpoint tick is invalid")
    return captured_tick


def _authoritative_cold_limits():
    names = (
        "GUALA_MAX_COLD_GENERATION_BYTES",
        "GUALA_MAX_COLD_REQUIRED_FILES",
        "GUALA_MAX_COLD_PATH_BYTES",
    )
    values = []
    for name in names:
        raw = os.environ.get(name)
        try:
            value = int(raw)
        except (TypeError, ValueError) as error:
            raise RuntimeError(
                f"{name} must be configured as a positive integer"
            ) from error
        if value <= 0:
            raise RuntimeError(
                f"{name} must be configured as a positive integer")
        values.append(value)
    return tuple(values)


def _authoritative_physical_storage_config():
    try:
        from dsf_ai_service.substrate.production_storage_profile import (
            ProductionStorageProfile,
            ProductionStorageProfileError,
        )
        profile = ProductionStorageProfile.from_environment()
    except ProductionStorageProfileError as error:
        raise PersistentStorageReadinessHalt(
            f"production storage profile is incomplete: {error}; no "
            "persistent EFS ceiling can be derived from current EFS usage "
            "or the ECS ephemeral-storage limit"
        ) from error
    configured_ceiling = os.environ.get(PERSISTENT_STORAGE_CEILING_ENV)
    if configured_ceiling is None:
        raise PersistentStorageReadinessHalt(
            f"{PERSISTENT_STORAGE_CEILING_ENV} must be configured as the "
            "operator-approved positive integer hard global refusal "
            "ceiling; the derived emergency resource envelope is not a "
            "production readiness authority"
        )
    try:
        ceiling = int(configured_ceiling)
    except ValueError as error:
        raise PersistentStorageReadinessHalt(
            f"{PERSISTENT_STORAGE_CEILING_ENV} must be configured as the "
            "operator-approved positive integer hard global refusal "
            "ceiling"
        ) from error
    if ceiling <= 0:
        raise PersistentStorageReadinessHalt(
            f"{PERSISTENT_STORAGE_CEILING_ENV} must be configured as the "
            "operator-approved positive integer hard global refusal "
            "ceiling"
        )
    if ceiling != APPROVED_PERSISTENT_STORAGE_CEILING_BYTES:
        raise PersistentStorageReadinessHalt(
            f"{PERSISTENT_STORAGE_CEILING_ENV} must equal the approved "
            f"{APPROVED_PERSISTENT_STORAGE_CEILING_BYTES}-byte hard global "
            "refusal ceiling"
        )
    roots = tuple(
        os.path.abspath(path)
        for path in (
            STATE_DIR,
            GENERATION_STORE_ROOT,
            LIVE_RECOVERY_STORE_ROOT,
        )
    )
    scope = os.path.commonpath(roots)
    if not scope or scope == os.path.sep or not os.path.isdir(scope):
        raise PersistentStorageReadinessHalt(
            "persistent state, cold generations, and live recovery do not "
            "share one existing non-root physical-byte scope")
    return ceiling, scope, profile


def _validate_runtime_generation_cold_restore(generation):
    """Prove one immutable candidate outside the live serving process.

    A complete Guala cold restore is intentionally CPU- and memory-intensive.
    Running that Python workload in a thread inside the sole production owner
    can starve the event loop and make a healthy owner fail its load-balancer
    health checks.  Materialization remains here under generation authority;
    the exact engine load executes in one bounded child process whose memory,
    GIL, and worker lifecycle cannot enter the serving owner.
    """
    import subprocess
    import sys
    import tempfile
    from dsf_ai_service.substrate.deployment_generation import (
        materialize_verified_generation,
    )

    with tempfile.TemporaryDirectory(
            prefix="guala-cold-restore-") as validation_root:
        active = os.path.join(validation_root, "active")
        materialized = materialize_verified_generation(
            generation=generation,
            active_directory=active,
        )
        try:
            child_environment = os.environ.copy()
            repository_root = os.path.dirname(
                os.path.dirname(os.path.abspath(__file__))
            )
            inherited_pythonpath = child_environment.get("PYTHONPATH")
            child_environment["PYTHONPATH"] = os.pathsep.join(
                path
                for path in (repository_root, inherited_pythonpath)
                if path
            )
            completed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "dsf_ai_service.cold_restore_probe",
                    "--active-directory",
                    active,
                    "--expected-identity",
                    generation.identity,
                    "--expected-tick",
                    str(generation.tick),
                ],
                check=False,
                capture_output=True,
                text=True,
                timeout=540,
                env=child_environment,
            )
            if completed.returncode != 0:
                diagnostic = (
                    (completed.stdout or "") + (completed.stderr or "")
                )[-4_096:]
                raise RuntimeError(
                    "isolated cold-restore probe failed with process "
                    f"return code {completed.returncode}: "
                    f"{diagnostic or 'no diagnostic output'}"
                )
            if materialized.generation_uuid != generation.generation_uuid:
                raise RuntimeError(
                    "cold-restore materialization differs from generation")
            return True
        except subprocess.TimeoutExpired as error:
            raise RuntimeError(
                "isolated cold-restore probe exceeded the existing "
                "540-second strict seal boundary"
            ) from error


def _seal_runtime_generation(
    nonce,
    *,
    runtime=None,
    authenticated_current_schema_migrations=(),
):
    """Create, upload, read back, and publish one exact stopped generation."""
    global _deployment_baseline_generation, _loaded_generation
    global _live_recovery_store
    global _remote_generation_reconciliation
    if not isinstance(authenticated_current_schema_migrations, tuple):
        raise TypeError(
            "authenticated current-schema migration authority must be a tuple"
        )
    extension_markers = tuple(sorted(
        authenticated_current_schema_migrations
    ))
    if (
        extension_markers
        and (
            len(extension_markers)
            != len(set(extension_markers))
            or not set(extension_markers).issubset(
                _REVIEWED_CURRENT_SCHEMA_MIGRATIONS
            )
        )
    ):
        raise RuntimeError(
            "authenticated current-schema migration authority changed"
        )
    target = _guala if runtime is None else runtime
    if target is None:
        raise RuntimeError("generation seal has no Guala owner")
    import boto3
    from dsf_ai_service.substrate.deployment_generation import (
        stage_authoritative_commit_upload,
        verify_deployment_seal,
    )

    checkpoint_finalized = False
    try:
        with target.persistence_transaction():
            with _persistence_authority_lock:
                identity = getattr(target, "_guala_identity", None)
                if not isinstance(identity, str) or not identity:
                    raise RuntimeError(
                        "Guala identity is absent; generation cannot be sealed")
                bucket = os.environ.get(
                    "GUALA_S3_BACKUP_BUCKET", "dsf-ai-site-backups")
                prefix = os.environ.get(
                    "GUALA_GENERATION_S3_PREFIX", "guala/generations")
                key = _deploy_hmac_key()
                (
                    max_generation_bytes,
                    max_required_files,
                    max_path_bytes,
                ) = _authoritative_cold_limits()
                (
                    persistent_storage_ceiling,
                    persistent_storage_scope,
                    _storage_profile,
                ) = _authoritative_physical_storage_config()
                baseline_generation = _deployment_baseline_generation

                def write_causal_candidate_stage(stage, admission):
                    if runtime is None:
                        captured_tick = _write_runtime_generation_stage(
                            stage,
                            admission,
                        )
                    else:
                        captured_tick = _write_runtime_generation_stage(
                            stage,
                            admission,
                            runtime=target,
                        )
                    # The immutable generation now contains one indivisible
                    # organism state.  Its generation manifest and internal
                    # organism root provide the complete causal binding; no
                    # per-mechanism receipt files are constructed.
                    return captured_tick

                def validate_whole_organism_candidate(candidate):
                    _validate_runtime_generation_cold_restore(candidate)
                    from dsf_ai_service.substrate.whole_organism_persistence import (
                        whole_organism_mutation_root,
                    )
                    whole_organism_mutation_root(
                        candidate.stored_bytes("guala_core.json")
                    )
                    if extension_markers and baseline_generation is None:
                        raise RuntimeError(
                            "current-schema extension has no predecessor"
                        )
                    if extension_markers and (
                        candidate.identity != baseline_generation.identity
                        or candidate.tick != baseline_generation.tick
                        or candidate.generation_uuid
                        == baseline_generation.generation_uuid
                        or candidate.manifest_sha256
                        == baseline_generation.manifest_sha256
                    ):
                        raise RuntimeError(
                            "current-schema extension is not one distinct "
                            "same-identity same-tick successor"
                        )
                    if (
                        not extension_markers
                        and baseline_generation is not None
                        and (
                            candidate.identity
                            != baseline_generation.identity
                            or candidate.tick < baseline_generation.tick
                        )
                    ):
                        raise RuntimeError(
                            "whole-organism candidate regressed identity or time"
                        )
                    return True

                result = stage_authoritative_commit_upload(
                    store_root=GENERATION_STORE_ROOT,
                    identity=identity,
                    save_callback=write_causal_candidate_stage,
                    s3_client=boto3.client("s3", region_name="us-east-1"),
                    bucket=bucket,
                    prefix=prefix,
                    hmac_key=key,
                    nonce=nonce,
                    max_encoded_generation_bytes=max_generation_bytes,
                    max_dynamic_required_files=max_required_files,
                    max_dynamic_path_bytes=max_path_bytes,
                    cold_restore_validator=(
                        validate_whole_organism_candidate
                    ),
                    physical_byte_ceiling=persistent_storage_ceiling,
                    physical_byte_scope=persistent_storage_scope,
                    purge_migration_escrow_prefix=None,
                    allow_equal_tick_schema_migration=(
                        bool(extension_markers)
                    ),
                )
                version_aware = (
                    result.version_aware_remote_reconciliation is True
                )
                read_only_reuse = (
                    result.read_only_remote_reuse_verified is True
                )
                if version_aware == read_only_reuse:
                    raise RuntimeError(
                        "cold checkpoint returned without exactly one "
                        "remote authority proof mode"
                    )
                _remote_generation_reconciliation = {
                    "executed": True,
                    "retained_generation_uuids": (
                        result.remote_retained_generation_uuids
                    ),
                    "retired_generation_uuids": (
                        result.remote_retired_generation_uuids
                    ),
                    "version_aware": version_aware,
                    "read_only_remote_reuse_verified": read_only_reuse,
                    "proof_mode": (
                        "version_aware_reconciliation"
                        if version_aware
                        else "exact_read_only_reuse"
                    ),
                }
                certificate_bytes = result.seal_certificate_bytes()
                certificate = verify_deployment_seal(
                    certificate_bytes,
                    hmac_key=key,
                    expected_nonce=nonce,
                )
                rebased = None
                if _live_recovery_store is not None:
                    hot_payloads = {
                        name: result.generation.stored_bytes(name)
                        for name in Guala.HOT_SAVE_MANIFEST_FILES
                    }
                    rebased = (
                        _live_recovery_store
                        .rebase_after_deployment_seal(
                            baseline=result.generation,
                            tick=result.generation.tick,
                            files=hot_payloads,
                        )
                    )
                    from dsf_ai_service.substrate.live_recovery_generation import (
                        LiveRecoveryGenerationStore,
                    )
                    if isinstance(
                        _live_recovery_store,
                        LiveRecoveryGenerationStore,
                    ):
                        _live_recovery_store = (
                            LiveRecoveryGenerationStore(
                                LIVE_RECOVERY_STORE_ROOT,
                                baseline=result.generation,
                                hot_files=Guala.HOT_SAVE_MANIFEST_FILES,
                                hmac_key=key,
                                state_file_tick_manifest=(
                                    "guala_core.json"
                                ),
                                max_encoded_generation_bytes=(
                                    _production_storage_profile
                                    .max_live_recovery_generation_bytes
                                ),
                                physical_byte_ceiling=(
                                    persistent_storage_ceiling
                                ),
                                physical_byte_scope=(
                                    persistent_storage_scope
                                ),
                            )
                        )
                        app.state.live_recovery_store = (
                            _live_recovery_store
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
                        materialized_files=tuple(
                            sorted(Guala.HOT_SAVE_MANIFEST_FILES)),
                    )
                    app.state.deployment_baseline_generation = (
                        result.generation
                    )
                    app.state.loaded_generation = _loaded_generation

                sealed_core = result.generation.payload("guala_core.json")
                if not isinstance(sealed_core, dict):
                    raise RuntimeError(
                        "sealed generation core payload is not an object")
                sealed_core_data = sealed_core.get("data", sealed_core)
                if not isinstance(sealed_core_data, dict):
                    raise RuntimeError(
                        "sealed generation core data is not an object")
                target.finalize_authoritative_full_checkpoint(
                    expected_tick=result.generation.tick,
                    state_file_ticks=sealed_core_data.get(
                        "state_file_ticks"
                    ),
                )
                _deployment_baseline_generation = result.generation
                app.state.deployment_baseline_generation = (
                    result.generation
                )
                receipt = _seal_receipt_with_rebased_live_recovery(
                    certificate,
                    rebased,
                )
                checkpoint_finalized = True
                return receipt
    finally:
        if not checkpoint_finalized:
            target.discard_prepared_authoritative_full_checkpoint()


def _checkpoint_authoritative_runtime(reason):
    """Commit one live cold checkpoint through the sole sealed authority."""
    if not _REQUIRE_SEALED_STATE:
        raise RuntimeError(
            "authoritative cold checkpoints require sealed production")
    if not isinstance(reason, str) or not reason.strip():
        raise ValueError("checkpoint reason must be a non-empty string")
    import secrets
    return _seal_runtime_generation(secrets.token_hex(32))


def _settled_authoritative_checkpoint(reason):
    """Commit an administrative checkpoint at one settled causal instant."""
    target = _guala
    if target is None:
        raise RuntimeError(
            "authoritative checkpoint has no live Guala organism"
        )
    with target.settled_external_persistence_transaction():
        return _checkpoint_authoritative_runtime(reason)


async def _quiesce_and_seal(nonce):
    """Execute RUNNING -> QUIESCING -> SEALED without a partial resume."""
    import asyncio
    lifecycle = _deployment_lifecycle
    lifecycle.begin_quiescence(nonce)
    destructive_started = False
    try:
        # At this first boundary no component has been stopped.  A drain
        # failure can safely reopen admission because process state is intact.
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
        if _guala is None:
            raise RuntimeError("Guala is not loaded")
        app.state.deployment_quiescing = True
        await asyncio.to_thread(
            _stop_embedded_persistence_components, 120.0)
        import dsf_ai_service.substrate_runner as _sr
        runner_proof = await asyncio.to_thread(
            _sr.quiesce_background_loops, 120.0)

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
            "engine": engine_proof,
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
async def sleep_for_deploy(request: Request):
    """Authenticated canonical sealed deployment handoff."""
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
        "active_recovery_generation": proof[
            "active_recovery_generation"
        ],
        "active_recovery_manifest_sha256": proof[
            "active_recovery_manifest_sha256"
        ],
        "active_recovery_tick": proof["active_recovery_tick"],
        "active_recovery_is_overlay": proof[
            "active_recovery_is_overlay"
        ],
    }
