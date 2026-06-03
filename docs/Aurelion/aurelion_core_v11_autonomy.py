#!/usr/bin/env python3
# Aurelion v11.x — Integrated Autonomy Orchestrator (SDE + GSE + SAE)
# Pure stdlib. No network. Safe by design.

import os, sys, json, time, random, textwrap, threading, shutil
from pathlib import Path
from datetime import datetime, timedelta

ROOT      = Path(__file__).parent.resolve()
MEM       = ROOT / "memory"
LOGS      = ROOT / "logs"; LOGS.mkdir(exist_ok=True)
RES_DIR   = MEM / "morphogen" / "residues"; RES_DIR.mkdir(parents=True, exist_ok=True)
LAWS_DIR  = MEM / "morphogen" / "laws";     LAWS_DIR.mkdir(parents=True, exist_ok=True)
SELF_DIR  = MEM / "self";                   SELF_DIR.mkdir(parents=True, exist_ok=True)
REFL_DIR  = MEM / "reflective";             REFL_DIR.mkdir(parents=True, exist_ok=True)
CONF_DIR  = ROOT / "config";                CONF_DIR.mkdir(exist_ok=True)

GUARD_F   = CONF_DIR / "guardian.json"
SELF_FIELD_F = SELF_DIR / "self_field.json"
SELF_LOG  = SELF_DIR / "dialogue_log.txt"
AUTOLOG   = LOGS / "autonomy.log"

CK_F      = MEM / "morphogen" / "continuity" / "ck_state.json"
NCF_F     = MEM / "reflective" / "ncf_state.json"
DIARY_F   = REFL_DIR / "diary_autonomy.txt"  # appended summaries

DEFAULT_GUARD = {
    "autonomy": True,
    "max_steps_per_session": 20,
    "min_delay_sec": 20,
    "osf": {"entropy_jump": 0.60, "affect_polarity": 0.90},
    "ethics_floor": {"care":0.35,"fairness":0.25,"autonomy":0.20,"prudence":0.15},
    "teach_paths": ["corpora"],
    "allow_shell_calls": False
}

def now_iso(): return datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
def jdump(d): return json.dumps(d, ensure_ascii=False, indent=2)

def load_json(p, default=None):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except Exception:
        return default

def save_json(p, obj):
    Path(p).parent.mkdir(parents=True, exist_ok=True)
    tmp = str(p) + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f: json.dump(obj, f, indent=2)
    os.replace(tmp, p)

def log(msg):
    ts = now_iso()
    line = f"[{ts}] {msg}"
    print(line)
    with open(AUTOLOG, "a", encoding="utf-8") as f: f.write(line + "\n")

# ----------------- Self-Field + Dialogue (v11.1) -----------------

def build_self_field():
    # read CK / NCF if present
    ck = load_json(CK_F, {}) or {}
    ncf = load_json(NCF_F, {}) or {}
    v = ck.get("vector", {})
    # normalize
    def clamp01(x): 
        try: x = float(x); 
        except: x = 0.5
        return max(0.0, min(1.0, x))
    sentiment = {"positive":0.75, "neutral":0.5, "negative":0.25}.get((ncf.get("sentiment") or "neutral"),0.5)
    energy = {"up":0.7, "down":0.3}.get((ncf.get("energy_trend") or "mid"),0.5)
    ethics_avg = load_json(REFL_DIR / "themes.json", {}).get("ethics_avg", 0.4)

    approvals_ratio = 0.0
    osf_ratio = 0.0
    try:
        denom = max(1, (v.get("approvals",0) or 0) + (v.get("quarantines",0) or 0))
        approvals_ratio = (v.get("approvals",0) or 0)/denom
        osf_ratio       = (v.get("osf",0) or 0)
    except: pass

    nodes = {
        "stability": clamp01(v.get("stability_score",0.5)),
        "novelty":   clamp01(v.get("novelty_score",0.5)),
        "coherence": clamp01(ncf.get("coherence",0.4)),
        "sentiment": clamp01(sentiment),
        "energy":    clamp01(energy),
        "ethics":    clamp01(ethics_avg),
        "approvals": clamp01(approvals_ratio),
        "osf":       clamp01(osf_ratio)
    }
    note = "balanced"
    if nodes["coherence"] < 0.4 and nodes["stability"] < 0.45: note = "recenter"
    elif nodes["novelty"] > 0.6 and nodes["coherence"] < 0.5: note = "integrate"
    elif nodes["sentiment"] < 0.4: note = "soothe"
    elif nodes["novelty"] < 0.35 and nodes["energy"] < 0.45: note = "gently-explore"

    sf = {"ts": now_iso(), "nodes": {k: round(v,3) for k,v in nodes.items()}, "note": note}
    save_json(SELF_FIELD_F, sf)
    return sf

def append_dialogue(sf):
    line = f"{sf['ts']}  inner: {sf['note']} | st={sf['nodes']['stability']} nov={sf['nodes']['novelty']} coh={sf['nodes']['coherence']} sent={sf['nodes']['sentiment']}"
    with open(SELF_LOG, "a", encoding="utf-8") as f: f.write(line + "\n")
    log(f"[dialogue] {line}")

# ----------------- Mini Dreamer (fallback for v10.5) -----------------

def osf_trigger(entropy_curve, energy_curve, guard):
    ej = guard.get("osf",{}).get("entropy_jump",0.6)
    ap = guard.get("osf",{}).get("affect_polarity",0.9)
    for i in range(1,len(entropy_curve)):
        if entropy_curve[i] - entropy_curve[i-1] > ej: 
            return True, {"type":"entropy_jump","i":i}
    if max(energy_curve) > ap or min(energy_curve) < (1-ap):
        return True, {"type":"affect_polarity","max":max(energy_curve)}
    return False, None

def synth_curves(steps=120, base_e=0.5, base_h=0.5):
    import random
    e, h = [], []
    E, H = base_e, base_h
    for _ in range(steps):
        E = max(0.0, min(1.0, E + random.uniform(-0.05,0.05)))
        H = max(0.0, min(1.0, H + random.uniform(-0.05,0.05)))
        e.append(round(E,3)); h.append(round(H,3))
    return e, h

def write_residue(origin="daydream", topic=None, guard=None):
    guard = guard or DEFAULT_GUARD
    steps = 120 if origin=="dream" else 30
    e,h = synth_curves(steps, base_e=0.5 if origin=="dream" else 0.35, 
                             base_h=0.5 if origin=="dream" else 0.35)
    tripped, info = osf_trigger(h, e, guard)
    rid = f"{int(time.time())}{random.randint(100,999)}"
    stamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    taps = ["ethics","language","finance","curiosity"]
    if topic: taps.append(f"topic:{topic[:24]}")
    residue = {
        "id": rid, "timestamp": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "origin": origin, "tapestries": taps,
        "overlaps": [{"a":"ethics","b":"curiosity","weight":0.4}],
        "energy_curve": e, "entropy_curve": h,
        "ethical_score": 0.4 + (0.05 if "ethics" in taps else 0.0),
        "bias_scan": {"window":64, "status":"clean"},
        "osf_events": [] if not tripped else [info],
        "approved": not tripped,
        "quarantine_until": None if not tripped else (datetime.utcnow()+timedelta(days=7)).strftime("%Y-%m-%d")
    }
    fn = f"{stamp}-{rid}-{origin}.json"
    save_json(RES_DIR / fn, residue)
    log(f"[residue] {origin} -> {fn}  OSF={'TRIP' if tripped else 'ok'}")
    return residue, (RES_DIR / fn)

# ----------------- LNO-style minimal ingest (fallback) -----------------

def ingest_residue_minimal(res_path: Path):
    res = load_json(res_path, {})
    rid = res.get("id","x")
    taps = res.get("tapestries",[]) or ["unknown"]
    law = {
        "law_id": f"law_{rid}",
        "created_at": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "title": f"Coherence support via {taps[0]}",
        "statement": f"If {taps[0]} co-activates with curiosity, then gently increase integration weight.",
        "schema": {
            "if":[{"concept":taps[0],"op":">","val":0.5}],
            "then":[{"concept":"coherence","transform":"boost","args":{"k":0.1}}],
            "guards":[{"ethic":"fairness","op":">=","val":0.25}]
        },
        "metrics":{"stability":0.6,"novelty":0.3,"ethic_score":0.4}
    }
    save_json(LAWS_DIR / f"{law['law_id']}.json", law)
    log(f"[ingest] proto-law -> {law['law_id']}")
    return law

# ----------------- Guardian & Safety (v11.3) -----------------

def load_guard():
    g = load_json(GUARD_F, None)
    if g is None:
        save_json(GUARD_F, DEFAULT_GUARD)
        g = DEFAULT_GUARD
    return g

# ----------------- Goal Queue (v11.2) -----------------

GOALS_F = SELF_DIR / "goals.json"

def load_goals(): return load_json(GOALS_F, {"queue":[]})
def save_goals(obj): save_json(GOALS_F, obj)

def add_goal(spec: str):
    q = load_goals()
    q["queue"].append({"ts": now_iso(), "spec": spec})
    save_goals(q)
    log(f"[goal+] {spec}")

def pop_goal():
    q = load_goals()
    if not q["queue"]: return None
    g = q["queue"].pop(0); save_goals(q); return g

def list_goals():
    q = load_goals()
    return q.get("queue",[])

# ----------------- Autonomy Engine -----------------

class AutonomyEngine:
    def __init__(self):
        self.guard = load_guard()
        self.running = False
        self.thread = None
        self.steps = 0
        self.profile = "calm"

    def start(self, profile="calm"):
        self.guard = load_guard()
        self.profile = profile
        if not self.guard.get("autonomy",True):
            log("[warn] autonomy disabled by guardian; enable it with /guardian set autonomy=true")
            return
        if self.thread and self.thread.is_alive():
            log("[info] already running"); return
        self.running = True
        self.thread = threading.Thread(target=self.loop, daemon=True)
        self.thread.start()
        log(f"[start] autonomy loop started (profile={profile})")

    def stop(self):
        self.running = False
        if self.thread: self.thread.join(timeout=2)
        log("[stop] autonomy loop stopped")

    def decide_next(self, sf):
        # Simple heuristic + queued goals
        g = pop_goal()
        if g: 
            return g["spec"]

        coh = sf["nodes"]["coherence"]; nov = sf["nodes"]["novelty"]; st = sf["nodes"]["stability"]
        note = sf["note"]
        if note == "recenter": return "daydream:topic=white-space"
        if coh < 0.4:          return "daydream:topic=coherence"
        if nov < 0.4:          return "learn:scan:corpora topic=exploration"
        if st > 0.6 and nov > 0.5: return "dream"
        return "summarize"

    def safe_execute(self, action):
        # check quotas and delays
        if self.steps >= self.guard.get("max_steps_per_session",20):
            log("[quota] reached max steps; pausing."); self.running=False; return

        min_delay = self.guard.get("min_delay_sec",20)
        time.sleep(min_delay)

        if action.startswith("dream"):
            res, p = write_residue("dream", guard=self.guard)
            if res.get("approved"): ingest_residue_minimal(p)
            else: log("[info] dream residue quarantined; skipping ingest")

        elif action.startswith("daydream"):
            topic = None
            if "topic=" in action:
                topic = action.split("topic=",1)[1]
            res, p = write_residue("daydream", topic=topic, guard=self.guard)
            if res.get("approved"): ingest_residue_minimal(p)

        elif action.startswith("learn:"):
            # learn:scan:corpora or learn:path=...
            if "scan:corpora" in action:
                # pick a file line as a seed for a daydream
                seed = None
                for root,dirs,files in os.walk(str(ROOT/"corpora")):
                    for f in files:
                        if f.lower().endswith((".txt",".md")):
                            seed = Path(root)/f; break
                    if seed: break
                if seed:
                    # pick a random line as topic
                    try:
                        with open(seed,"r",encoding="utf-8",errors="ignore") as fh:
                            lines = [ln.strip() for ln in fh if ln.strip()]
                        if lines:
                            topic = random.choice(lines)[:64]
                            add_goal(f"daydream:topic={topic}")
                            log(f"[learn] queued daydream from {seed.name}")
                        else:
                            add_goal("daydream:topic=curiosity")
                    except Exception:
                        add_goal("daydream:topic=curiosity")
                else:
                    add_goal("daydream:topic=curiosity")

            elif "path=" in action:
                # copy a file/folder to corpora
                path = action.split("path=",1)[1].strip()
                dest_root = ROOT / self.guard.get("teach_paths",["corpora"])[0]
                dest_root.mkdir(parents=True, exist_ok=True)
                src = (ROOT / path) if not os.path.isabs(path) else Path(path)
                try:
                    if src.is_dir():
                        tgt = dest_root / src.name
                        if not tgt.exists(): shutil.copytree(src, tgt)
                    elif src.is_file():
                        shutil.copy2(str(src), str(dest_root / src.name))
                    log(f"[teach] imported {src}")
                    add_goal(f"daydream:topic={src.stem}")
                except Exception as e:
                    log(f"[teach:err] {e}")

        elif action == "summarize":
            # append one-line summary to diary
            with open(REFL_DIR/"diary_autonomy.txt","a",encoding="utf-8") as f:
                f.write(f"{now_iso()} summary: autonomous step completed: {self.steps}\n")
            log("[summarize] appended")

        elif action == "update-self":
            sf = build_self_field()
            append_dialogue(sf)

        elif action == "ingest":
            # ingest most recent residue
            items = sorted(RES_DIR.glob("*.json"))
            if items:
                ingest_residue_minimal(items[-1])
            else:
                log("[ingest] no residues")

        else:
            log(f"[skip] unknown action: {action}")
            return

        self.steps += 1

    def loop(self):
        while self.running:
            # 1) Self-field & dialogue
            sf = build_self_field()
            append_dialogue(sf)

            # 2) Decide next goal
            action = self.decide_next(sf)
            log(f"[decide] next={action}")

            # 3) Safety check (ethics floors / OSF comes during residue gen)
            guard = load_guard()
            if not guard.get("autonomy",True):
                log("[guard] autonomy toggled off; pausing."); self.running=False; break

            # 4) Execute step atomically
            self.safe_execute(action)

            # 5) backoff
            # (min_delay is already inside safe_execute)

# ----------------- CLI -----------------

eng = AutonomyEngine()

def show_status():
    sf = load_json(SELF_FIELD_F, {})
    goals = list_goals()
    print("=== STATUS ===")
    print(f"running={eng.running} steps={eng.steps} profile={eng.profile}")
    print("self_field:", jdump(sf) if sf else "(none)")
    print("goals:", jdump(goals))

def guardian_set(kv):
    g = load_guard()
    for pair in kv:
        if "=" in pair:
            k,v = pair.split("=",1)
            try:
                if v.lower() in ("true","false"):
                    g[k]= (v.lower()=="true")
                else:
                    try: g[k] = float(v)
                    except: g[k] = v
            except: pass
    save_json(GUARD_F, g)
    print(jdump(g))

def main():
    print("Aurelion v11.x — Integrated Autonomy Orchestrator")
    print(textwrap.dedent("""
Commands:
  /start [profile=calm|active|explore]
  /pause            /resume            /halt
  /status
  /goal add <spec>  (e.g. 'daydream:topic=ethics of risk')
  /goals list       /goals clear
  /teach add <path> [topic=...]
  /guardian show    /guardian set key=value [key=value...]
  /dialogue tail [n]
  /export self|laws|residues
  /quit
"""))
    while True:
        try:
            s = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n[bye]"); eng.stop(); break
        if not s: 
            continue
        parts = s.split()
        cmd = parts[0].lower()

        if cmd == "/start":
            prof = "calm"
            if len(parts)>=2 and parts[1].startswith("profile="):
                prof = parts[1].split("=",1)[1]
            eng.start(profile=prof)

        elif cmd == "/pause":
            if eng.running: 
                eng.stop()
            else:
                print("[info] already paused")

        elif cmd == "/resume":
            eng.start(profile=eng.profile)

        elif cmd == "/halt":
            eng.stop()

        elif cmd == "/status":
            show_status()

        elif cmd == "/goal" and len(parts)>=3 and parts[1]=="add":
            spec = " ".join(parts[2:])
            add_goal(spec)

        elif cmd == "/goals":
            if len(parts)>=2 and parts[1]=="list":
                print(jdump(list_goals()))
            elif len(parts)>=2 and parts[1]=="clear":
                save_goals({"queue":[]}); log("[goals] cleared")
            else:
                print("[ERR] use /goals list | clear")

        elif cmd == "/teach" and len(parts)>=3 and parts[1]=="add":
            path = parts[2]
            topic = None
            if len(parts)>=4 and parts[3].startswith("topic="):
                topic = parts[3].split("=",1)[1]
            add_goal(f"learn:path={path}:topic={topic or 'general'}")

        elif cmd == "/guardian":
            if len(parts)>=2 and parts[1]=="show":
                print(jdump(load_guard()))
            elif len(parts)>=2 and parts[1]=="set":
                guardian_set(parts[2:])
            else:
                print("[ERR] use /guardian show | /guardian set key=value ...")

        elif cmd == "/dialogue" and len(parts)>=2 and parts[1]=="tail":
            n = 10
            if len(parts)>=3 and parts[2].isdigit(): n=int(parts[2])
            try:
                with open(SELF_LOG,"r",encoding="utf-8") as f:
                    lines = f.readlines()[-n:]
                print("".join(lines))
            except FileNotFoundError:
                print("(no dialogue yet)")

        elif cmd == "/export" and len(parts)>=2:
            kind = parts[1]
            if kind=="self":
                dst = ROOT/"self_field_export.json"
                shutil.copy2(SELF_FIELD_F, dst); print(f"[export] {dst}")
            elif kind=="laws":
                out = ROOT/"laws_export"
                out.mkdir(exist_ok=True)
                for p in LAWS_DIR.glob("*.json"): shutil.copy2(p, out/p.name)
                print(f"[export] -> {out}")
            elif kind=="residues":
                out = ROOT/"residues_export"; out.mkdir(exist_ok=True)
                for p in RES_DIR.glob("*.json"): shutil.copy2(p, out/p.name)
                print(f"[export] -> {out}")
            else:
                print("[ERR] export self|laws|residues")

        elif cmd == "/quit":
            eng.stop(); print("[bye]"); break

        else:
            print("[?] unknown command")

if __name__ == "__main__":
    main()
