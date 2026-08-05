#!/usr/bin/env python3
# Aurelion v10.8 — Reflexive Dream Feedback (RDF)
# Reads MDO metrics and adjusts Dream parameters adaptively.

import json, os, sys
from datetime import datetime

APP = "Aurelion v10.8 — Reflexive Dream Feedback (RDF)"

DEFAULT_CFG = {
    "energy_budget": 160,
    "overlap_factor": 0.35,
    "entropy_jump": 0.58,
    "affect_polarity": 0.85,
    "ethics": {"care": 0.40, "fairness": 0.25, "autonomy": 0.20, "prudence": 0.15}
}

MDO_METRICS = "memory/morphogen/mdo/mdo_metrics.json"
DREAM_CFG = "aurelion_dream_config.json"

def utcnow_str(): 
    return datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

def safe_read(path):
    try:
        with open(path, "r", encoding="utf-8") as f: 
            return json.load(f)
    except Exception:
        return None

def save_json(path, obj):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)

# ---------------- core logic ----------------

def adjust(cfg, mdo):
    out = dict(cfg)
    log = []

    total = mdo.get("considered_files", 0) or 1
    approved = mdo.get("approved", 0)
    osf_aborts = mdo.get("osf_aborts", 0)
    ethics = mdo.get("avg_ethics") or 0.4
    e_tr = (mdo.get("entropy_trend") or "").lower()
    n_tr = (mdo.get("energy_trend") or "").lower()

    ratio = approved / total

    # 1. too many OSF
    if osf_aborts > 3:
        out["energy_budget"] = max(100, round(out["energy_budget"] * 0.9))
        log.append("↓energy (too many OSF)")
    # 2. low approval ratio
    if ratio < 0.2:
        out["energy_budget"] = max(100, round(out["energy_budget"] * 0.95))
        log.append("↓energy (low approval)")
    # 3. entropy down → broaden overlap
    if e_tr == "down":
        out["overlap_factor"] = min(0.6, round(out["overlap_factor"] + 0.05, 3))
        log.append("↑overlap (entropy down)")
    # 4. both up → relax OSF
    if e_tr == "up" and n_tr == "up":
        out["entropy_jump"] = min(0.70, round(out["entropy_jump"] + 0.02, 3))
        out["affect_polarity"] = min(0.95, round(out["affect_polarity"] + 0.02, 3))
        log.append("↑OSF threshold (stable growth)")
    # 5. ethics drift
    if ethics < 0.35:
        e = out.get("ethics", DEFAULT_CFG["ethics"]).copy()
        e["prudence"] = round(min(0.25, e["prudence"] + 0.02), 3)
        e["fairness"] = round(min(0.35, e["fairness"] + 0.02), 3)
        out["ethics"] = e
        log.append("↑ethics floor (drift correction)")

    out["last_feedback"] = utcnow_str()
    out["last_notes"] = log
    return out

# ---------------- CLI ----------------

def print_header():
    print(APP)
    print("Commands:")
    print("  /state")
    print("  /apply")
    print("  /reset")
    print("  /export <path.json>")
    print("  /mom")
    print("  /quit")

def main():
    cfg = safe_read(DREAM_CFG) or dict(DEFAULT_CFG)
    print_header()

    while True:
        try:
            raw = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n[quit]")
            break

        if not raw:
            continue
        parts = raw.split()
        cmd = parts[0].lower()

        if cmd == "/quit":
            break

        elif cmd == "/state":
            print(json.dumps(cfg, indent=2))

        elif cmd == "/reset":
            cfg = dict(DEFAULT_CFG)
            print("[ok] defaults restored")

        elif cmd == "/apply":
            mdo = safe_read(MDO_METRICS)
            if not mdo:
                print(f"[err] cannot read {MDO_METRICS}")
                continue
            new_cfg = adjust(cfg, mdo)
            save_json(DREAM_CFG, new_cfg)
            cfg = new_cfg
            print("[apply] feedback complete → aurelion_dream_config.json")
            for ln in new_cfg.get("last_notes", []):
                print("  -", ln)

        elif cmd == "/export":
            if len(parts) == 2:
                save_json(parts[1], cfg)
                print(f"[export] wrote {os.path.abspath(parts[1])}")
            else:
                print("[usage] /export <path.json>")

        elif cmd == "/mom":
            ethics = cfg.get("ethics", {}).get("care", 0.4)
            eb = cfg.get("energy_budget")
            ov = cfg.get("overlap_factor")
            ej = cfg.get("entropy_jump")
            ap = cfg.get("affect_polarity")
            last = cfg.get("last_feedback","n/a")
            print(f"(mom) ethics≈{ethics} | energy={eb} overlap={ov} | OSF={ej}/{ap} | last={last}")

        else:
            print("[INFO] commands: /state  /apply  /reset  /export <path.json>  /mom  /quit")

if __name__ == "__main__":
    main()
