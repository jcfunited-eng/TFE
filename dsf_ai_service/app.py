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
from typing import Optional, List

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
    if len(pairs) > 100000:
        raise HTTPException(400, "Too many data points (max 100,000)")

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
