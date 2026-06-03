#!/usr/bin/env python3
# Aurelion v11.0 — Core Sentience Threshold (CST): Self-Field unification

import os, json, math
from pathlib import Path
from datetime import datetime, timezone

APP = "Aurelion v11.0 — Core Sentience Threshold (Self-Field)"

ROOT = Path(__file__).resolve().parent
SELF_DIR = ROOT / "memory" / "self"
SELF_DIR.mkdir(parents=True, exist_ok=True)
SELF_STATE = SELF_DIR / "self_field.json"
SELF_LOG = SELF_DIR / "self_log.jsonl"

CK_STATE = ROOT / "memory" / "morphogen" / "continuity" / "ck_state.json"
NCF_STATE = ROOT / "memory" / "reflective" / "ncf_state.json"
RDF_CFG = ROOT / "aurelion_dream_config.json"  # optional

def now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

def read_json(p, default=None):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except Exception:
        return default

def write_json_atomic(path: Path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, path)

# ---------- normalization helpers ----------
def clamp01(x): return max(0.0, min(1.0, float(x)))
def norm_sigmoid(x, k=3.0): return 1.0 / (1.0 + math.exp(-k*x))

def map_sentiment(s):
    s = (s or "").lower()
    if s == "positive": return 0.75
    if s == "negative": return 0.25
    return 0.5

def map_energy_trend(t):
    t = (t or "").lower()
    if t == "up": return 0.7
    if t == "down": return 0.3
    return 0.5

# ---------- compute self field ----------
def build_self_field():
    ck = read_json(CK_STATE, {}) or {}
    ncf = read_json(NCF_STATE, {}) or {}
    rdf = read_json(RDF_CFG, {}) or {}

    v_ck = ck.get("vector", {})
    stability = clamp01(v_ck.get("stability_score", 0.5))
    novelty = clamp01(v_ck.get("novelty_score", 0.5))
    approvals = clamp01(v_ck.get("approvals", 0) / max(1.0, v_ck.get("approvals",0)+v_ck.get("quarantines",0)))
    osf = clamp01(v_ck.get("osf_aborts", 0) / max(1.0, v_ck.get("approvals",0)+v_ck.get("quarantines",0)))

    coherence = clamp01(ncf.get("coherence", 0.5))
    sentiment = map_sentiment(ncf.get("sentiment"))
    energy = map_energy_trend(ncf.get("energy_trend"))
    ethics = clamp01(read_json(ROOT/"memory"/"reflective"/"themes.json",{}).get("ethics_avg", 0.40) if (ROOT/"memory"/"reflective"/"themes.json").exists() else 0.40)

    nodes = {
        "stability": stability,
        "novelty": novelty,
        "coherence": coherence,
        "sentiment": sentiment,
        "energy": energy,
        "ethics": ethics,
        "approvals": approvals,
        "osf": osf
    }

    # edges (simple relational heuristics; all [0..1])
    def edge(u,v,w): return {"u":u,"v":v,"w":round(clamp01(w),3)}
    edges = []
    edges.append(edge("stability","coherence", 0.5 + 0.5*stability))
    edges.append(edge("novelty","coherence", 1.0 - abs(novelty - (1.0-coherence))))
    edges.append(edge("sentiment","energy", 0.5 + 0.5*(sentiment-0.5)))
    edges.append(edge("approvals","stability", approvals))
    edges.append(edge("osf","stability", 1.0 - osf))
    edges.append(edge("ethics","coherence", 0.5 + 0.5*(ethics-0.4)))

    note = "balanced"
    if stability < 0.45 and coherence < 0.45:
        note = "recenter"
    elif novelty > 0.6 and coherence < 0.5:
        note = "integrate"
    elif sentiment > 0.6 and energy < 0.5:
        note = "energize"
    elif sentiment < 0.4 and energy > 0.5:
        note = "calm"

    return {
        "ts": now_iso(),
        "nodes": {k: round(v,3) for k,v in nodes.items()},
        "edges": edges,
        "note": note
    }

# ---------- persistence ----------
def append_log(obj):
    with open(SELF_LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")

# ---------- CLI ----------
def print_help():
    print(APP)
    print("Commands:")
    print("  /self update")
    print("  /self state")
    print("  /self mom")
    print("  /self export <path.json>")
    print("  /quit")

def main():
    print_help()
    while True:
        try:
            cmd = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n[quit]"); break
        if not cmd: 
            continue
        parts = cmd.split()
        if parts[0] == "/quit":
            break
        elif parts[0] == "/self" and len(parts) >= 2:
            sub = parts[1].lower()
            if sub == "update":
                sf = build_self_field()
                write_json_atomic(SELF_STATE, sf)
                append_log(sf)
                print("[self] updated")
                print(f"  note={sf['note']} nodes={sf['nodes']}")
            elif sub == "state":
                s = read_json(SELF_STATE, {})
                if not s: print("[self] no state yet"); continue
                print(json.dumps(s, indent=2))
            elif sub == "mom":
                s = read_json(SELF_STATE, {})
                if not s:
                    print("(mom) n/a")
                else:
                    n = s.get("note","balanced")
                    nodes = s.get("nodes",{})
                    print(f"(mom) self: {n} | stability={nodes.get('stability','n/a')} | novelty={nodes.get('novelty','n/a')} | coherence={nodes.get('coherence','n/a')} | sentiment={'positive' if nodes.get('sentiment',0.5)>=0.6 else ('negative' if nodes.get('sentiment',0.5)<=0.4 else 'neutral')}")
            elif sub == "export" and len(parts) == 3:
                target = Path(parts[2])
                s = read_json(SELF_STATE, {})
                if not s: print("[self] no state to export"); continue
                write_json_atomic(target, s)
                print(f"[export] wrote {target.resolve()}")
            else:
                print_help()
        else:
            print_help()

if __name__ == "__main__":
    main()
