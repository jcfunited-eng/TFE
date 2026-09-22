"""Capture all unchanged TFE kernel outputs available at a known cutoff.

Observation only, not L5 governance. Future bars are removed before L0 runs.
All gates as known at this cutoff are retained without field substitution.
A final-history tape must not be mistaken for historical knowledge.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict, is_dataclass
import gzip
import hashlib
import json
import math
from pathlib import Path
import sys

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
FIELDS = ("D_k", "M_k", "R_rev_k", "U_star_k", "C_k", "P_k", "B_k")


def plain(value):
    if is_dataclass(value):
        return plain(asdict(value))
    if isinstance(value, dict):
        return {str(k): plain(v) for k, v in value.items()}
    if isinstance(value, (tuple, list, np.ndarray)):
        return [plain(v) for v in value]
    if isinstance(value, np.generic):
        return plain(value.item())
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError("nonfinite kernel output; receipt refused")
    return value


def kernel_hashes():
    return {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted((ROOT / "uf_core").glob("*.py"))}


def capture(market, symbol, as_of):
    from uf_core.layer0 import compute_sev_series
    from uf_core.layer1 import segment_gates
    from uf_core.layer2 import interpret_gates
    from uf_core.layer3 import compute_resonance
    from uf_core.layer4 import compute_directional_signal, compute_dsf
    from uf_core.uf_structural_engine import compute_uf_structural_state

    before = kernel_hashes()
    frame = market[market.Symbol == symbol].copy()
    frame["Date"] = pd.to_datetime(frame.Date)
    cutoff = pd.Timestamp(as_of)
    frame = frame[frame.Date <= cutoff].sort_values("Date")
    if frame.empty or frame.Date.iloc[-1] != cutoff:
        raise ValueError("exact cutoff bar missing")
    if frame.Date.duplicated().any():
        raise ValueError("duplicate input timestamps")
    values = frame.Close.to_numpy(dtype=float)
    if not np.isfinite(values).all() or (values <= 0).any():
        raise ValueError("invalid raw closes")
    close = pd.Series(values, index=pd.DatetimeIndex(frame.Date))
    sev = compute_sev_series(pd.DataFrame({"Close": close}), field_col="Close")
    gates = segment_gates(sev)
    interpretations = interpret_gates(sev, gates)
    resonance = compute_resonance(interpretations)
    dsf = compute_dsf(compute_directional_signal(resonance))
    if not dsf or not len(gates) == len(interpretations) == len(resonance) == len(dsf):
        raise ValueError("incomplete gate/field delivery")
    adapter = compute_uf_structural_state(close)
    for name in FIELDS:
        if adapter.level5[name] != getattr(dsf[-1], name):
            raise ValueError(f"adapter changed raw L4 field: {name}")
    tape = []
    for gate, interpreted, resonated, delivered in zip(gates, interpretations, resonance, dsf):
        if not gate == interpreted.gate == resonated.gate == delivered.gate:
            raise ValueError("gate identity mismatch")
        tape.append({"gate": plain(gate), "l2": plain(interpreted),
                     "l3": plain(resonated), "l4": plain(delivered)})
    if kernel_hashes() != before:
        raise RuntimeError("kernel source changed during capture")
    raw_input = [{"date": d.isoformat(), "close": float(c)} for d, c in close.items()]
    input_json = json.dumps(raw_input, separators=(",", ":"), allow_nan=False)
    result = {
        "symbol": symbol, "as_of": str(cutoff.date()),
        "input_start": str(close.index[0].date()), "input_bars": len(close),
        "input_sha256": hashlib.sha256(input_json.encode()).hexdigest(),
        "kernel_sha256": before, "raw_input": raw_input,
        "l0": plain(sev), "gate_history": tape,
        "adapter_context": {"S_UF": adapter.level4["S_UF"], "R_UF": adapter.level4["R_UF"]},
        "adapter_context_authority": "existing adapter aggregates, not substituted per-gate fields",
        "l4_adapter_exact_match": True,
        "evidence_class": "unchanged-kernel transport verification, not strategy validation",
        "history_scope": "all supplied bars through cutoff; listing-history completeness unverified",
    }
    json.dumps(result, allow_nan=False)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bars", type=Path, required=True)
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--as-of", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    bars = pd.read_parquet(args.bars, columns=["Date", "Symbol", "Close"],
                           filters=[("Symbol", "==", args.symbol)])
    result = capture(bars, args.symbol, args.as_of)
    result["source_bars"] = str(args.bars)
    encoded = json.dumps(result, allow_nan=False, separators=(",", ":")).encode()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("xb") as raw:
        raw.write(gzip.compress(encoded, mtime=0))
    print(json.dumps({"symbol": args.symbol, "as_of": args.as_of,
                      "input_bars": result["input_bars"],
                      "gates_retained": len(result["gate_history"]),
                      "l4_adapter_exact_match": result["l4_adapter_exact_match"],
                      "receipt_sha256": hashlib.sha256(encoded).hexdigest(),
                      "output": str(args.output)}))


if __name__ == "__main__":
    main()
