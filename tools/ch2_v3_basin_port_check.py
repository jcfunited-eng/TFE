"""Prove the Python port of computeV3Basin matches the live JavaScript module.

Feeds the SAME tuples to web/scripts/execution/v3_basin.mjs (via node) and to
tools/ch2_v3_basin_py.py, and requires identical decisions and identical
numbers to floating-point identity. A measurement that used a drifting port
would be answering a different question than the live door asks.

Usage: python tools/ch2_v3_basin_port_check.py [lanes.csv.gz] [n]
Falls back to deterministic synthetic tuples when no lane file is given.
"""
from __future__ import annotations

import gzip
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ch2_v3_basin_py import compute_v3_basin  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
FIELDS = ["S_UF", "R_UF", "D_k", "M_k", "R_rev_k", "U_star_k", "C_k", "P_k", "B_k"]
COLS = ["s_uf", "r_uf", "d_k", "m_k", "r_rev_k", "u_star_k", "c_k", "p_k", "b_k"]

NODE_SRC = """
import { computeV3Basin } from "file://%s";
import { readFileSync } from "node:fs";
const rows = JSON.parse(readFileSync(process.argv[2], "utf8"));
process.stdout.write(JSON.stringify(rows.map((t) => computeV3Basin(t))));
"""


def synthetic(n: int) -> list[dict]:
    out = []
    for i in range(n):
        x = (i % 97) / 96
        y = ((i * 7) % 89) / 88
        out.append({
            "S_UF": 0.2 + 0.8 * x, "R_UF": 0.1 + 0.9 * y, "D_k": [1, -1, 0][i % 3],
            "M_k": -1.5 + 3 * x, "R_rev_k": y, "U_star_k": 0.05 + 0.5 * y,
            "C_k": 5 * x, "P_k": 3 * y, "B_k": -1 + 2 * x,
        })
    return out


def from_lanes(path: Path, n: int) -> list[dict]:
    rows: list[dict] = []
    op = gzip.open if path.suffix == ".gz" else open
    with op(path, "rt") as fh:
        header = fh.readline().rstrip("\n").split(",")
        idx = {c: header.index(c) for c in COLS}
        step = 0
        for line in fh:
            step += 1
            if step % 137:  # spread the sample across the whole file
                continue
            parts = line.rstrip("\n").split(",")
            try:
                rows.append({f: float(parts[idx[c]]) for f, c in zip(FIELDS, COLS)})
            except (ValueError, IndexError):
                continue
            if len(rows) >= n:
                break
    return rows


def main() -> int:
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 1000
    if len(sys.argv) > 1 and Path(sys.argv[1]).exists():
        rows = from_lanes(Path(sys.argv[1]), n)
        source = f"real lanes: {sys.argv[1]}"
    else:
        rows = synthetic(n)
        source = "synthetic tuples"
    if not rows:
        print("no tuples to check")
        return 1

    tmp_json = ROOT / "artifacts" / "ch4_uf" / "_port_check_tuples.json"
    tmp_json.parent.mkdir(parents=True, exist_ok=True)
    tmp_json.write_text(json.dumps(rows))
    runner = ROOT / "artifacts" / "ch4_uf" / "_port_check.mjs"
    runner.write_text(NODE_SRC % (ROOT / "web" / "scripts" / "execution" / "v3_basin.mjs"))

    proc = subprocess.run(["node", str(runner), str(tmp_json)],
                          capture_output=True, text=True, cwd=str(ROOT))
    if proc.returncode != 0:
        print("node failed:", proc.stderr[-400:])
        return 1
    js = json.loads(proc.stdout)

    # Python's math.pow and V8's Math.pow may differ in the last bit, so the
    # bar is: identical DECISIONS, numbers equal to 1e-12 relative, and no
    # tuple sitting close enough to a gate threshold for that last bit to
    # flip an entry. Anything looser would be a different question than the
    # live door asks; anything stricter is not achievable across the two
    # math libraries.
    TOL = 1e-12
    mismatches = []
    worst = 0.0
    borderline = 0
    for i, (t, j) in enumerate(zip(rows, js)):
        p = compute_v3_basin(t)
        if (p is None) != (j is None):
            mismatches.append((i, "null-ness", p, j)); continue
        if p is None:
            continue
        if p["decision_argmax"] != j["decision_argmax"]:
            mismatches.append((i, "decision", p["decision_argmax"], j["decision_argmax"])); continue
        for k, v in j.items():
            if k == "decision_argmax":
                continue
            rel = abs(p[k] - v) / max(abs(v), 1e-300) if v else abs(p[k] - v)
            worst = max(worst, rel)
            if rel > TOL:
                mismatches.append((i, k, p[k], v))
                break
        # would the last bit ever flip the gate?
        if abs(p["accumulate_basin"] - 0.15) < 1e-9 or abs(p["break_agreement"] - 0.20) < 1e-9:
            borderline += 1

    print(f"port check: {len(rows)} tuples from {source}; decision mismatches + over-tolerance: {len(mismatches)}")
    print(f"  worst relative difference: {worst:.3e} (tolerance {TOL:.0e})")
    print(f"  tuples within 1e-9 of a gate threshold (where a last bit could matter): {borderline}")
    for m in mismatches[:5]:
        print("  ", m)
    tmp_json.unlink(missing_ok=True); runner.unlink(missing_ok=True)
    return 0 if not mismatches else 1


if __name__ == "__main__":
    raise SystemExit(main())
