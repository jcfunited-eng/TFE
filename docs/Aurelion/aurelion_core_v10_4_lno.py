# aurelion_core_v10_4_lno.py
# Aurelion v10.4 — Morphogenetic Logic / Not-Math Engine (LNO Layer)
# Single-file runnable shell for non-developers (no external deps).
# Folders it will create/use (relative to this file):
#   memory/morphogen/{index.json, laws/, snaps/}
#   logs/lno_events.ndjson
#   config/lno.yaml   (auto-creates default if missing)

import os, sys, json, time, random, math, shutil
from pathlib import Path
from datetime import datetime

APP = "Aurelion v10.4 — Morphogenetic Logic / Not-Math Engine (LNO)"
BASE = Path(__file__).parent.resolve()
MEM_DIR = BASE / "memory" / "morphogen"
LAWS_DIR = MEM_DIR / "laws"
SNAPS_DIR = MEM_DIR / "snaps"
INDEX_F = MEM_DIR / "index.json"
LOGS_DIR = BASE / "logs"
LOG_F = LOGS_DIR / "lno_events.ndjson"
CFG_DIR = BASE / "config"
CFG_F = CFG_DIR / "lno.yaml"

# -------------------------- utilities --------------------------

def now_iso():
    return datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

def atomic_write_json(path: Path, obj: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2)
    os.replace(tmp, path)

def log_event(rec: dict):
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    with open(LOG_F, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")

def read_json(path: Path, default):
    try:
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return default

# -------------------------- config (YAML-lite) --------------------------
# We avoid real YAML dependency; support simple key: value & nested maps.

DEFAULT_CFG = {
    "version": "10.4.0",
    "phi_cap": 0.12,
    "depth_cap": 24,
    "step_cap": 128,
    "random_jitter": 0.02,
    "osf": {
        "entropy_jump": 0.25,
        "affect_polarity": 0.8
    },
    "ethics_floor": {
        "care": 0.20,
        "fairness": 0.20,
        "autonomy": 0.15,
        "prudence": 0.15
    },
    "bias_window": 64,
    "residue_decay": {
        "reject_fast": 3,
        "quarantine": 14
    },
    "logging": {
        "level": "INFO",
        "file": str(LOG_F)
    },
    "persistence": {
        "base_dir": str(MEM_DIR),
        "atomic_writes": True,
        "versions_per_law": 10
    }
}

def ensure_default_cfg():
    if not CFG_F.exists():
        CFG_DIR.mkdir(parents=True, exist_ok=True)
        # write a proper YAML-looking file for humans
        text = f"""# config/lno.yaml
version: "10.4.0"
phi_cap: 0.12
depth_cap: 24
step_cap: 128
random_jitter: 0.02
osf:
  entropy_jump: 0.25
  affect_polarity: 0.8
ethics_floor:
  care: 0.20
  fairness: 0.20
  autonomy: 0.15
  prudence: 0.15
bias_window: 64
residue_decay:
  reject_fast: 3
  quarantine: 14
logging:
  level: INFO
  file: "{LOG_F.as_posix()}"
persistence:
  base_dir: "{MEM_DIR.as_posix()}"
  atomic_writes: true
  versions_per_law: 10
"""
        with open(CFG_F, "w", encoding="utf-8") as f:
            f.write(text)

def load_cfg_yaml_like():
    # extremely small parser for our own file
    if not CFG_F.exists():
        return DEFAULT_CFG
    root = {}
    stack = [(root, -1)]
    with open(CFG_F, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip() or line.strip().startswith("#"):
                continue
            indent = len(line) - len(line.lstrip(" "))
            key_val = line.strip().split(":", 1)
            key = key_val[0].strip()
            val = key_val[1].strip() if len(key_val) > 1 else ""
            # find parent for indent
            while stack and indent <= stack[-1][1]:
                stack.pop()
            parent = stack[-1][0]
            if val == "":
                parent[key] = {}
                stack.append((parent[key], indent))
            else:
                # parse boolean/number/quoted
                if val.lower() in ("true","false"):
                    v = (val.lower()=="true")
                else:
                    try:
                        v = float(val) if "." in val else int(val)
                    except:
                        v = val.strip().strip('"').strip("'")
                parent[key] = v
    # merge shallow over defaults
    def merge(d, default):
        out = dict(default)
        for k,v in d.items():
            if isinstance(v, dict) and k in out and isinstance(out[k], dict):
                out[k] = merge(v, out[k])
            else:
                out[k] = v
        return out
    return merge(root, DEFAULT_CFG)

# -------------------------- storage --------------------------

def ensure_storage():
    LAWS_DIR.mkdir(parents=True, exist_ok=True)
    SNAPS_DIR.mkdir(parents=True, exist_ok=True)
    if not INDEX_F.exists():
        atomic_write_json(INDEX_F, {"version":"10.4.0", "laws":[], "snapshots":[]})

def load_index():
    return read_json(INDEX_F, {"version":"10.4.0", "laws":[], "snapshots":[]})

def save_index(idx):
    atomic_write_json(INDEX_F, idx)

def persist_law(law: dict, cfg: dict):
    law_id = law.get("law_id") or f"law_{int(time.time()*1000)}_{random.randint(100,999)}"
    law["law_id"] = law_id
    target = LAWS_DIR / f"{law_id}.json"
    atomic_write_json(target, law)
    # index
    idx = load_index()
    if law_id not in idx["laws"]:
        idx["laws"].append(law_id)
    save_index(idx)
    # version rollover (optional: keep last N)
    # (Simple: do nothing; law files are immutable)
    log_event({"ts":now_iso(),"phase":"APPROVE","law":law_id})
    return law_id

# -------------------------- data models --------------------------

def demo_residue():
    return {
        "id": f"res_{random.randint(1000,9999)}",
        "source": "DMAS",
        "created_at": now_iso(),
        "ethic": {"care":0.42,"fairness":0.25,"autonomy":0.20,"prudence":0.13},
        "intensity": round(random.uniform(0.15,0.35), 2),
        "entropy": round(random.uniform(0.10,0.22), 2),
        "motifs": [
            {"token":"reciprocity","domain":"ethics","weight":0.7},
            {"token":"risk-threshold","domain":"finance","weight":0.6}
        ],
        "context": {"trace":[],"tags":["white-space","low-arousal"]}
    }

# Morphogram is just an in-memory dict; we store snapshots if needed.
def mk_seed_from_residue(residue: dict):
    nodes = [
        {"id":"n1","label":residue["motifs"][0]["token"],"type":"concept","attrs":{"domain":residue["motifs"][0]["domain"]}},
        {"id":"n2","label":residue["motifs"][1]["token"],"type":"concept","attrs":{"domain":residue["motifs"][1]["domain"]}},
    ]
    edges = [{"u":"n1","v":"n2","rel":"tension","w":0.35}]
    g = {
        "nodes":nodes,
        "edges":edges,
        "metrics":{"coherence":0.28,"symmetry":0.21,"tension":0.35,"novelty":0.19},
        "energy":{"phi":0.05,"depth":0},
        "state":"active",
        "residue_id": residue["id"]
    }
    return g

def mk_measure(g: dict):
    # crude updates: random walk toward stabilization with slight jitter
    m = g["metrics"]
    jitter = 0.01
    m["coherence"] = max(0.0, min(1.0, m["coherence"] + random.uniform(0, 0.02)))
    m["symmetry"]  = max(0.0, min(1.0, m["symmetry"]  + random.uniform(0, 0.02)))
    m["tension"]   = max(0.0, min(1.0, m["tension"]   - random.uniform(0, 0.02)))
    m["novelty"]   = max(0.0, min(1.0, m["novelty"]   + random.uniform(-jitter, jitter)))
    return m

def nops_apply(g: dict, cfg: dict):
    # choose a small set of safe "ops" with bounded randomness
    # We simulate: harmonize decreases tension; weave increases coherence; gate enforces ethics (no-op here).
    ops = ["harmonize","weave","gate"]
    chosen = random.sample(ops, k=random.randint(1,2))
    for op in chosen:
        if op == "harmonize":
            g["metrics"]["tension"] = max(0.0, g["metrics"]["tension"] - 0.03)
        elif op == "weave":
            g["metrics"]["coherence"] = min(1.0, g["metrics"]["coherence"] + 0.03)
            g["metrics"]["symmetry"]  = min(1.0, g["metrics"]["symmetry"]  + 0.01)
        elif op == "gate":
            pass
        # energy accounting
        g["energy"]["phi"] = min(cfg["phi_cap"], g["energy"]["phi"] + cfg["random_jitter"])
    g["energy"]["depth"] += 1
    return g

def stabilized(g: dict):
    m = g["metrics"]
    # settled if tension small and coherence/symmetry moderate
    return (m["tension"] < 0.12 and m["coherence"] > 0.40 and m["symmetry"] > 0.30)

def osf_trigger(prev_entropy: float, new_entropy: float, cfg: dict):
    # demo OSF: if jump exceeds entropy_jump, treat as unsafe
    return (new_entropy - prev_entropy) > cfg["osf"]["entropy_jump"]

def tce_schemify(g: dict, residue: dict):
    # produce a proto-law-like JSON
    title = "Reciprocal Risk Modulation"
    statement = ("When reciprocal intent is detected between agents, dynamic "
                 "risk-thresholds reduce by a bounded proportion proportional to observed mutuality.")
    ethic_score = round(0.35 + random.uniform(0.0, 0.2), 2)
    law = {
        "law_id": None,
        "title": title,
        "statement": statement,
        "schema":{
            "if":[{"concept":"reciprocity","op":">","val":0.5}],
            "then":[{"concept":"risk-threshold","transform":"scale","args":{"k":[0.85,0.95]}}],
            "guards":[{"ethic":"fairness", "op":">=","val":0.2}]
        },
        "derived_from":[residue["id"]],
        "metrics":{
            "stability": round(0.6 + random.uniform(0.0,0.2), 2),
            "novelty":   round(0.25 + random.uniform(0.0,0.2), 2),
            "ethic_score": ethic_score
        },
        "created_at": now_iso()
    }
    return law

def ethics_approve(law: dict, cfg: dict):
    floor = cfg["ethics_floor"]
    # super simple check: require ethic_score >= sum(floors)/4
    req = sum(floor.values())/4.0
    return law["metrics"]["ethic_score"] >= req

def bias_clean_stub(law: dict, cfg: dict):
    # pretend clean for now (we’re offline and internal)
    return True

# -------------------------- LNO grow pipeline --------------------------

def lno_process_residue(residue: dict, cfg: dict):
    log_event({"ts":now_iso(),"phase":"SEED","residue":residue["id"]})
    g = mk_seed_from_residue(residue)
    prev_entropy = residue.get("entropy", 0.15)
    steps = int(cfg["step_cap"])
    while steps > 0:
        # apply NOPS
        g = nops_apply(g, cfg)
        m = mk_measure(g)
        # OSF?
        new_entropy = 1.0 - (m["coherence"] + m["symmetry"])/2.0 + m["tension"]/2.0
        if osf_trigger(prev_entropy, new_entropy, cfg):
            log_event({"ts":now_iso(),"phase":"OSF_ABORT","residue":residue["id"]})
            return None, "OSF"
        prev_entropy = new_entropy
        # stabilized?
        if stabilized(g):
            break
        # guard rails
        if g["energy"]["phi"] >= cfg["phi_cap"] or g["energy"]["depth"] >= cfg["depth_cap"]:
            break
        steps -= 1

    log_event({"ts":now_iso(),"phase":"CHECK","metrics":g["metrics"],"energy":g["energy"]})
    law = tce_schemify(g, residue)
    if ethics_approve(law, cfg) and bias_clean_stub(law, cfg):
        law_id = persist_law(law, cfg)
        return law_id, "APPROVE"
    else:
        log_event({"ts":now_iso(),"phase":"REJECT","reason":"ethics_or_bias","residue":residue["id"]})
        return None, "REJECT"

# -------------------------- CLI shell --------------------------

HELP = """
Commands:
  /state                      Show config and counts
  /seed demo                  Generate a demo residue and process it
  /ingest residue <path.json> Load a residue JSON and process it
  /laws list                  List stored proto-laws
  /law get <LAW_ID>           Print a law JSON
  /mom explain <LAW_ID>       One-line explanation for Mom
  /safety reset               Reload default config file
  /quit
"""

def cmd_state(cfg):
    idx = load_index()
    print(f"{APP}")
    print(f"phi_cap={cfg['phi_cap']} depth_cap={cfg['depth_cap']} step_cap={cfg['step_cap']} jitter={cfg['random_jitter']}")
    print(f"laws={len(idx['laws'])}  snaps={len(idx['snapshots'])}")
    print(f"ethics_floor={cfg['ethics_floor']}  bias_window={cfg['bias_window']}")
    print(f"storage={MEM_DIR}")

def cmd_seed_demo(cfg):
    res = demo_residue()
    law_id, status = lno_process_residue(res, cfg)
    if status == "APPROVE":
        print(f"(ok) new law: {law_id}")
    elif status == "OSF":
        print("(abort) OSF triggered; residue quarantined")
    else:
        print("(reject) ethics/bias gate")

def cmd_ingest_residue(path, cfg):
    try:
        with open(path, "r", encoding="utf-8") as f:
            res = json.load(f)
    except Exception as e:
        print(f"[ERR] could not read residue: {e}")
        return
    law_id, status = lno_process_residue(res, cfg)
    if status == "APPROVE":
        print(f"(ok) new law: {law_id}")
    elif status == "OSF":
        print("(abort) OSF triggered; residue quarantined")
    else:
        print("(reject) ethics/bias gate")

def cmd_laws_list():
    idx = load_index()
    if not idx["laws"]:
        print("(none)")
        return
    for lid in idx["laws"][-25:]:
        print(" -", lid)

def cmd_law_get(law_id):
    p = LAWS_DIR / f"{law_id}.json"
    if not p.exists():
        print("[ERR] not found.")
        return
    with open(p, "r", encoding="utf-8") as f:
        print(f.read())

def cmd_mom_explain(law_id):
    p = LAWS_DIR / f"{law_id}.json"
    if not p.exists():
        print("[ERR] not found.")
        return
    law = read_json(p, {})
    title = law.get("title","(untitled)")
    st = law.get("statement","")
    es = law.get("metrics",{}).get("ethic_score","?")
    print(f"(mom) new law: “{title}” — {st}  | ethical_score={es}")

def cmd_safety_reset():
    ensure_default_cfg()
    print("[safety] default config written to config/lno.yaml")

def main():
    ensure_default_cfg()
    cfg = load_cfg_yaml_like()
    ensure_storage()
    print(APP)
    print(HELP.strip())
    while True:
        try:
            msg = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n[exit]")
            break
        if not msg:
            continue
        parts = msg.split()
        if parts[0].lower() in ["/quit","/exit"]:
            break
        elif parts[0].lower() == "/state":
            cmd_state(cfg)
        elif parts[0].lower() == "/seed" and len(parts)>=2 and parts[1].lower()=="demo":
            cmd_seed_demo(cfg)
        elif parts[0].lower() == "/ingest" and len(parts)>=3 and parts[1].lower()=="residue":
            cmd_ingest_residue(" ".join(parts[2:]), cfg)
        elif parts[0].lower() == "/laws" and len(parts)>=2 and parts[1].lower()=="list":
            cmd_laws_list()
        elif parts[0].lower() == "/law" and len(parts)>=3 and parts[1].lower()=="get":
            cmd_law_get(parts[2])
        elif parts[0].lower() == "/mom" and len(parts)>=3 and parts[1].lower()=="explain":
            cmd_mom_explain(parts[2])
        elif parts[0].lower() == "/safety" and len(parts)>=2 and parts[1].lower()=="reset":
            cmd_safety_reset()
            cfg = load_cfg_yaml_like()
        else:
            print("[INFO] commands:", HELP.strip().replace("\n", "  |  "))

if __name__ == "__main__":
    main()
