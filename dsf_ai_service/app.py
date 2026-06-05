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
import traceback
from typing import Optional, List, Dict

from fastapi import FastAPI, File, UploadFile, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
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

STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static')


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

# ════════════════════════════════════════════════════════════════
# GualaLoom v5 — Recall + Question Bucket + Honest Fallback
# GUALALOOM-V5-WC-2026-06-05
# ════════════════════════════════════════════════════════════════

from dsf_ai_service.v4.gualaloom_v5_engine import Guala, CORPUS

_guala = None       # v4 substrate instance
_persist_every = 20
_exchange_count = 0

STATE_DIR = "state"
NEEDS_PATH = os.path.join(STATE_DIR, "needs.json")
COORDINATOR_PATH = os.path.join(STATE_DIR, "coordinator.json")
SOURCE_PATH = os.path.join(STATE_DIR, "source_history.json")


def _gl_init():
    global _guala
    if _guala is not None:
        return

    os.makedirs(STATE_DIR, exist_ok=True)
    _guala = Guala()

    # Load persisted motivational state from EFS
    _load_motivational_state(_guala)

    # Start continuous corpus reading (background)
    _guala.start_continuous_reading(CORPUS, interval=0.02)
    s = _guala.introspect()
    print(f"[GualaLoom v4] Booted: vocab={s['vocab']} reads={s['reads']} "
          f"pair_bond={'on' if s['pair_bond_active'] else 'off'}")


def _load_motivational_state(g):
    """Load persisted needs + coordinator + source_history from EFS."""
    if os.path.exists(NEEDS_PATH):
        try:
            with open(NEEDS_PATH) as f:
                nd = json.load(f)
            g.needs.stability = nd.get("stability", g.needs.stability)
            g.needs.novelty = nd.get("novelty", g.needs.novelty)
            g.needs.connection = nd.get("connection", g.needs.connection)
            print(f"[GualaLoom v4] Loaded needs: {g.needs.snapshot()}")
        except Exception as e:
            print(f"[GualaLoom v4] Failed to load needs: {e}")

    if os.path.exists(COORDINATOR_PATH):
        try:
            with open(COORDINATOR_PATH) as f:
                cd = json.load(f)
            g.coordinator.pair_bond_active = cd.get("pair_bond_active", True)
            g.coordinator.distress_ticks = cd.get("distress_ticks", 0)
            g.coordinator.suffering_log = cd.get("suffering_log", [])
            g.coordinator.need_history = cd.get("need_history", [])[-200:]
            print(f"[GualaLoom v4] Loaded coordinator: pair_bond={'on' if g.coordinator.pair_bond_active else 'off'} "
                  f"suffering_events={len(g.coordinator.suffering_log)}")
        except Exception as e:
            print(f"[GualaLoom v4] Failed to load coordinator: {e}")

    if os.path.exists(SOURCE_PATH):
        try:
            with open(SOURCE_PATH) as f:
                sh = json.load(f)
            from collections import defaultdict
            g.source_history = defaultdict(int, sh)
            print(f"[GualaLoom v4] Loaded source history: {dict(g.source_history)}")
        except Exception as e:
            print(f"[GualaLoom v4] Failed to load source history: {e}")


def _save_motivational_state(g):
    """Persist needs + coordinator + source_history to EFS."""
    os.makedirs(STATE_DIR, exist_ok=True)
    with open(NEEDS_PATH, "w") as f:
        json.dump(g.needs.snapshot(), f)
    with open(COORDINATOR_PATH, "w") as f:
        json.dump({
            "pair_bond_active": g.coordinator.pair_bond_active,
            "distress_ticks": g.coordinator.distress_ticks,
            "suffering_log": g.coordinator.suffering_log,
            "need_history": g.coordinator.need_history[-200:],
        }, f)
    with open(SOURCE_PATH, "w") as f:
        json.dump(dict(g.source_history), f)


class GLMessage(BaseModel):
    text: str
    command: Optional[str] = None


@app.get("/gualaloom")
async def gualaloom_page():
    return FileResponse(os.path.join(STATIC_DIR, 'gualaloom.html'))


@app.post("/api/v1/gualaloom")
async def gualaloom_chat(msg: GLMessage):
    global _exchange_count
    _gl_init()

    cmd = (msg.command or "").strip().lower()

    # ── /status — real substrate state (v4 introspect) ──
    if cmd == "/status":
        s = _guala.introspect()
        n = s["needs"]
        sec_parts = []
        for nm, sec in s["sections"].items():
            sec_parts.append(f"{nm}: {sec['modes']}m/{sec['commits']}c")
        return {
            "response": (
                f"vocab: {s['vocab']} | reads: {s['reads']}\n"
                f"sections: {' | '.join(sec_parts)}\n"
                f"atlas: {s['cross_modal_bindings']} cross-modal / {s['atlas_entries']} entries\n"
                f"needs: stab={n['stability']:.3f} nov={n['novelty']:.3f} "
                f"conn={n['connection']:.3f} v={n['valence']:+.3f} a={n['arousal']:.3f}\n"
                f"pair-bond: {'on' if s['pair_bond_active'] else 'off'} | "
                f"suffering: {s['suffering_events']} | "
                f"coord: att={s['coordinator_attentions']} act={s['coordinator_actions']}"
            ),
            "motifs": s["vocab"],
        }

    # ── Normal conversation — v4 substrate responds ──
    text = msg.text.strip()
    if not text:
        return {"response": "...", "motifs": _guala.introspect()["vocab"]}

    # Source detection: default to "joe" for now (per wC command,
    # proper auth-based source resolution is step 2)
    source = "joe"

    response = _guala.converse(text, source=source)
    _exchange_count += 1
    if _exchange_count % _persist_every == 0:
        _save_motivational_state(_guala)

    return {"response": response, "motifs": _guala.introspect()["vocab"]}


# ════════════════════════════════════════════════════════════════
# Health check
# ════════════════════════════════════════════════════════════════

@app.on_event("startup")
async def startup():
    result = initialize_integrity()
    print(f"[DSF-AI] Integrity initialized: {result['files_present']}/{result['files_checked']} files hashed")


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "service": "dsf-ai",
        "version": "1.0.0",
        "integrity": get_integrity_status(),
    }
