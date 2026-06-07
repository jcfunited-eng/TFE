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
import json

# ════════════════════════════════════════════════════════════════
# GualaLoom v5 — Recall + Question Bucket + Honest Fallback
# GUALALOOM-V5-WC-2026-06-05
# ════════════════════════════════════════════════════════════════

from dsf_ai_service.v4.gualaloom_v5_engine import (
    Guala, CORPUS, CorpusItem, SensoryItem,
)
from fastapi.responses import StreamingResponse

_guala = None
_persist_every = 50   # save every N exchanges
_exchange_count = 0
STATE_DIR = "state"

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

# v7: Legacy corpus as fallback reading material
SEED_CORPORA["legacy_seed"] = {"title": "Seed Corpus", "lines": CORPUS}


def _gl_init():
    global _guala
    if _guala is not None:
        return

    os.makedirs(STATE_DIR, exist_ok=True)
    _guala = Guala()

    # v7: Register seed corpora BEFORE loading state (so positions can restore)
    for cid, cdata in SEED_CORPORA.items():
        _guala._corpora[cid] = CorpusItem(
            corpus_id=cid, title=cdata["title"], lines=cdata["lines"])

    # Load full persisted state from EFS (atomic, validated)
    _guala.load_full_state(STATE_DIR)

    # v7: Start autonomy loop (replaces continuous reading)
    _guala.start_autonomy_loop(interval=0.05)
    s = _guala.introspect()
    print(f"[GualaLoom v7] Booted: vocab={s['vocab']} reads={s['reads']} "
          f"tick={_guala.tick} pair_bond={'on' if s['pair_bond_active'] else 'off'} "
          f"atlas={s['atlas_entries']} corpora={len(_guala._corpora)} "
          f"activity={s['current_activity']}")


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

    # ── /status — real substrate state + continuity health ──
    if cmd == "/status":
        s = _guala.introspect()
        n = s["needs"]
        ph = _guala.persistence_health(STATE_DIR)
        sec_parts = []
        for nm, sec in s["sections"].items():
            sec_parts.append(f"{nm}: {sec['modes']}m/{sec['commits']}c")
        id_short = (ph.get("guala_identity") or "none")[:8]
        return {
            "response": (
                f"id: {id_short}.. | schema: {ph.get('schema_version','?')}\n"
                f"vocab: {s['vocab']} | reads: {s['reads']} | tick: {s['tick']}\n"
                f"sections: {' | '.join(sec_parts)}\n"
                f"atlas: {s['cross_modal_bindings']} cross-modal / {s['atlas_entries']} entries\n"
                f"needs: stab={n['stability']:.3f} nov={n['novelty']:.3f} "
                f"conn={n['connection']:.3f} v={n['valence']:+.3f} a={n['arousal']:.3f}\n"
                f"pair-bond: {'on' if s['pair_bond_active'] else 'off'} | "
                f"suffering: {s['suffering_events']} | "
                f"coord: att={s['coordinator_attentions']} act={s['coordinator_actions']}\n"
                f"persistence: save@tick={ph['last_save_tick']} "
                f"files={'all' if not ph['files_missing'] else 'MISSING:' + ','.join(ph['files_missing'])} "
                f"boot={'ok' if ph['load_successful_at_boot'] else 'FAILED'} "
                f"integrity={'ok' if not ph.get('integrity_errors') else 'ERRORS'}\n"
                f"snapshots: {ph.get('snapshots_available', 0)} | "
                f"events: {ph.get('events_log', {}).get('current_file_size_bytes', 0)}B"
            ),
            "motifs": s["vocab"],
            "persistence_health": ph,
            "atlas_health": s.get("atlas_health", {}),
            "presence": s.get("presence", {}),
            "pair_bond": s.get("pair_bond", {}),
            # v7: autonomy fields
            "current_activity": s.get("current_activity"),
            "activity_history_summary": s.get("activity_history_summary", {}),
            "n_motifs": s.get("n_motifs", 0),
            "corpora": s.get("corpora", []),
            "sensory_items": s.get("sensory_items", []),
        }

    # ── /wake — substrate-physical wake event ──
    if cmd == "/wake":
        # Source from text field (e.g. "joe")
        wake_source = msg.text.strip().lower() if msg.text else "joe"
        if wake_source not in {"joe", "wc", "c1"}:
            return {"response": f"wake: unknown source '{wake_source}'", "motifs": 0}
        result = _guala.coordinator.wake(wake_source, _guala, _guala.needs, _guala.atlas)
        _guala.log_event(STATE_DIR, "wake", source=wake_source)
        return {"response": json.dumps(result), "motifs": _guala.introspect()["vocab"]}

    # ── /rest — substrate-physical rest event ──
    if cmd == "/rest":
        rest_source = msg.text.strip().lower() if msg.text else "joe"
        result = _guala.coordinator.rest(rest_source, _guala, reason="voluntary")
        _guala.log_event(STATE_DIR, "rest", source=rest_source)
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

    # ── Normal conversation — v5 substrate responds ──
    text = msg.text.strip()
    if not text:
        return {"response": "...", "motifs": _guala.introspect()["vocab"]}

    # Source detection: default to "joe" for now
    source = "joe"

    response = _guala.converse(text, source=source)
    _exchange_count += 1

    # Event log
    _guala.log_event(STATE_DIR, "source_interaction",
                     source=source, words_in=len(text.split()),
                     source_count=_guala.source_history.get(source, 0))

    # Periodic full save
    if _exchange_count % _persist_every == 0:
        _guala.save_full_state(STATE_DIR)

    return {"response": response, "motifs": _guala.introspect()["vocab"]}


# ════════════════════════════════════════════════════════════════
# v7: Substrate event stream (SSE) + sleep endpoint
# GUALALOOM-V7-AUTONOMY-WC-2026-06-06
# ════════════════════════════════════════════════════════════════

@app.get("/api/v1/gualaloom/events")
async def gualaloom_events(since: int = 0):
    """Server-sent events of substrate activity."""
    _gl_init()
    import asyncio

    async def event_generator():
        last_tick = since
        while True:
            events = _guala.get_recent_events(since_tick=last_tick, limit=50)
            for ev in events:
                if ev["tick"] > last_tick:
                    last_tick = ev["tick"]
                yield f"data: {json.dumps(ev)}\n\n"
            await asyncio.sleep(1.0)

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.post("/api/v1/gualaloom/sleep")
async def gualaloom_sleep():
    """Manual sleep trigger."""
    _gl_init()
    result = _guala.manual_sleep()
    return result


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
