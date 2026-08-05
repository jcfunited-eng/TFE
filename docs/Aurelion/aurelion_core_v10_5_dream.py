# aurelion_core_v10_5_dream.py
# Aurelion v10.5 — Dream & Day-Dream Integration (TFF + DMA + DDD)
# - No external dependencies. Pure stdlib.
# - Emits residue JSONs compatible with v10.4 LNO's /ingest residue <path.json>.
# - Safe defaults; OSF abort + quarantine + decay; ethics/bias scan stubs.

import json, math, random, threading, time, uuid
from pathlib import Path
from datetime import datetime, timedelta

APP = "Aurelion v10.5 — Dream & Day-Dream Core"

# ---------- Paths ----------
BASE = Path(__file__).parent.resolve()
STORE = BASE / "memory" / "morphogen"
RES_DIR = STORE / "residues"
LOG_DIR = BASE / "logs"
for p in [STORE, RES_DIR, LOG_DIR]:
    p.mkdir(parents=True, exist_ok=True)

# ---------- Helpers ----------
def utcnow_iso():
    return datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

def save_json(path: Path, obj: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2)

def load_json(path: Path, default):
    try:
        if path.exists():
            return json.load(open(path, "r", encoding="utf-8"))
    except Exception:
        pass
    return default

# ---------- Config (safe defaults) ----------
CFG_FILE = BASE / "config" / "dream.yaml"

DEFAULT_CFG = {
    "energy_budget": 160,        # steps per dream
    "overlap_factor": 0.35,      # cross-tapestry intensity (0..1)
    "daydream_budget": 28,       # steps per day-dream
    "daydream_overlap": 0.18,
    "higgs_kernel_chance": 0.08, # dream novelty burst
    "higgs_kernel_daydream": 0.04,
    "osf": {
        "entropy_jump": 0.58,    # abort if sudden jump above
        "affect_polarity": 0.85  # abort if polarity saturates
    },
    "decay": {
        "quarantine_days": 7,    # quarantine window
        "half_life_days": 7
    },
    "ethics_floor": {"care":0.40,"fairness":0.25,"autonomy":0.20,"prudence":0.15},
    "bias_window": 64,
    "dream_interval_sec": 900,   # 15 min between auto dreams
    "random_seed": None          # set int for reproducibility
}

def ensure_default_cfg():
    CFG_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not CFG_FILE.exists():
        # write YAML-ish (we only read JSON via helper, so we mirror in JSON too)
        # for simplicity we persist as JSON twin:
        save_json(CFG_FILE.with_suffix(".json"), DEFAULT_CFG)

def load_cfg():
    # Prefer JSON twin
    ensure_default_cfg()
    j = load_json(CFG_FILE.with_suffix(".json"), DEFAULT_CFG)
    # seed RNG if requested
    if j.get("random_seed") is not None:
        random.seed(int(j["random_seed"]))
    return j

# ---------- Ethics / Bias scan (simple stubs, extensible) ----------
def ethics_score_stub(tapestries, overlaps):
    # Positive if diversity and overlap are balanced; negative if mono-dominated.
    diversity = len(set(tapestries))
    density = len(overlaps)
    score = 0.1*diversity + 0.02*density
    return round(max(min(score, 1.0), -1.0), 2)

def bias_scan_stub(tapestries, overlaps, window=64):
    # Lightweight: if one tapestry dominates too much, flag "drift".
    counts = {}
    for t in tapestries:
        counts[t] = counts.get(t,0)+1
    dom = max(counts.values()) if counts else 0
    drift = (dom/len(tapestries))>0.66 if tapestries else False
    return {"window": window, "status": "clean" if not drift else "drift"}

# ---------- Curves ----------
def synth_curves(steps, base=0.3, jitter=0.18):
    # produce energy & entropy curves across steps
    energy, entropy = [], []
    e = base + random.uniform(-0.05, 0.05)
    h = base + random.uniform(-0.05, 0.05)
    for i in range(steps):
        e = max(0.0, min(1.0, e + random.uniform(-jitter, jitter)))
        h = max(0.0, min(1.0, h + random.uniform(-jitter, jitter)))
        energy.append(e)
        entropy.append(h)
    return energy, entropy

def detect_osf(energy_curve, entropy_curve, entropy_jump_thr, affect_polarity_thr):
    # simple OSF: if any delta in entropy exceeds thr OR energy saturates high/low with polarity proxy
    for i in range(1, len(entropy_curve)):
        if entropy_curve[i] - entropy_curve[i-1] > entropy_jump_thr:
            return True, {"type":"entropy_jump", "at": i}
    # polarity proxy: if energy stuck near extremes
    if max(energy_curve) > affect_polarity_thr or min(energy_curve) < (1-affect_polarity_thr):
        return True, {"type":"affect_polarity", "max_e": max(energy_curve), "min_e": min(energy_curve)}
    return False, None

# ---------- Dream Engine ----------
class DreamEngine:
    def __init__(self, cfg):
        self.cfg = cfg
        self._autorun = False
        self._thread = None
        self._last_residue_path = None

    @property
    def last_residue_path(self):
        return self._last_residue_path

    def _pick_tapestries(self, k, allow_random=True):
        base = ["ethics","language","finance","science","memory","self","curiosity"]
        picks = []
        for _ in range(k):
            if allow_random and random.random()<0.25:
                picks.append("random_"+str(random.randint(1,7)))
            else:
                picks.append(random.choice(base))
        return picks

    def _make_overlaps(self, taps, overlap_factor):
        overlaps = []
        if len(taps)<2: return overlaps
        pairs = []
        for i in range(len(taps)):
            for j in range(i+1, len(taps)):
                pairs.append((taps[i], taps[j]))
        # sample some pairs proportional to overlap factor
        take = max(1, int(len(pairs)*overlap_factor))
        for (a,b) in random.sample(pairs, min(take, len(pairs))):
            overlaps.append({"a":a, "b":b, "weight": round(random.uniform(0.1, 0.9),2)})
        return overlaps

    def _make_residue(self, origin, steps, overlap_factor, allow_higgs, topic=None):
        taps = self._pick_tapestries(k=random.randint(2,4), allow_random=True)
        if topic:
            taps.append(f"topic:{topic.lower()[:24]}")
        if allow_higgs and random.random()< (self.cfg["higgs_kernel_daydream"] if origin=="daydream" else self.cfg["higgs_kernel_chance"]):
            taps.append("higgs-kernel")

        energy, entropy = synth_curves(steps, base=0.3 if origin=="daydream" else 0.45,
                                       jitter=0.12 if origin=="daydream" else 0.16)

        osf_on, osf_info = detect_osf(energy, entropy,
                                      self.cfg["osf"]["entropy_jump"],
                                      self.cfg["osf"]["affect_polarity"])

        overlaps = self._make_overlaps(taps, overlap_factor)
        ethics = ethics_score_stub(taps, overlaps)
        bias = bias_scan_stub(taps, overlaps, window=self.cfg["bias_window"])

        rid = uuid.uuid4().hex[:12]
        stamp = utcnow_iso()
        residue = {
            "id": rid,
            "timestamp": stamp,
            "origin": origin,
            "tapestries": taps,
            "overlaps": overlaps,
            "energy_curve": [round(x,3) for x in energy],
            "entropy_curve": [round(x,3) for x in entropy],
            "semantic_tags": sorted(list({t.split(':')[0] for t in taps})),
            "hints": ["white-space" if origin=="daydream" else "tapestry-of-tapestries"],
            "ethical_score": ethics,
            "bias_scan": bias,
            "osf_events": [] if not osf_on else [osf_info],
            "quarantine_until": None,
            "decay_half_life_days": self.cfg["decay"]["half_life_days"],
            "approved": False
        }

        # apply OSF + quarantine logic
        if osf_on:
            until = (datetime.utcnow() + timedelta(days=self.cfg["decay"]["quarantine_days"])).strftime("%Y-%m-%d")
            residue["quarantine_until"] = until
            residue["approved"] = False
            status = "(abort) OSF triggered; residue quarantined"
        else:
            residue["approved"] = True
            status = "(ok) residue approved"

        # write file
        fn = f"{residue['timestamp'].replace(':','').replace('-','')}-{residue['id']}-{residue['origin']}.json"
        out = RES_DIR / fn
        save_json(out, residue)
        self._last_residue_path = str(out)

        # console summary
        print(f"[{origin}] {status}  | ethics={residue['ethical_score']}  bias={residue['bias_scan']['status']}  -> {out.name}")
        return residue, out

    # --- public actions ---
    def dream_once(self, energy=None, overlap=None):
        steps = int(energy) if energy else int(self.cfg["energy_budget"])
        ofac = float(overlap) if overlap else float(self.cfg["overlap_factor"])
        return self._make_residue("dream", steps, ofac, allow_higgs=True)

    def daydream_now(self, topic=None):
        steps = int(self.cfg["daydream_budget"])
        ofac = float(self.cfg["daydream_overlap"])
        return self._make_residue("daydream", steps, ofac, allow_higgs=True, topic=topic)

    def autorun_start(self):
        if self._autorun: 
            print("[auto] dreamer already running")
            return
        self._autorun = True
        self._thread = threading.Thread(target=self._autorun_loop, daemon=True)
        self._thread.start()
        print(f"[auto] dreamer started (interval={self.cfg['dream_interval_sec']}s)")

    def autorun_stop(self):
        self._autorun = False
        print("[auto] dreamer stopping... (wait up to one interval)")

    def _autorun_loop(self):
        while self._autorun:
            try:
                self.dream_once()
            except Exception as e:
                print("[auto] dream error:", e)
            # sleep interval
            for _ in range(int(self.cfg["dream_interval_sec"])):
                if not self._autorun: break
                time.sleep(1)

# ---------- Optional LNO integration ----------
def try_ingest_lno(residue_path: str):
    # If v10.4 LNO is present, call its CLI entry to process this residue
    try:
        import aurelion_core_v10_4_lno as lno
    except Exception:
        print("[lno] v10.4 not found; skipping LNO ingest.")
        return False
    try:
        cfg = lno.load_cfg_yaml_like() if hasattr(lno, "load_cfg_yaml_like") else lno.load_cfg_yaml_like
    except Exception:
        cfg = None
    try:
        if hasattr(lno, "cmd_ingest_residue"):
            lno.cmd_ingest_residue(residue_path)
            print("[lno] residue ingested:", residue_path)
            return True
        else:
            print("[lno] cmd_ingest_residue not found; skipping.")
            return False
    except Exception as e:
        print("[lno] ingest failed:", e)
        return False

# ---------- CLI ----------
def print_help():
    print(APP)
    print("Commands:")
    print("  /state                                   Show config and counts")
    print("  /dream once [energy=..] [overlap=..]     Run one dream cycle")
    print("  /dream start                              Start periodic dreams")
    print("  /dream stop                               Stop periodic dreams")
    print("  /daydream now [topic=..]                  Immediate day-dream")
    print("  /osf set entropy=.. affect=..             Adjust OSF thresholds")
    print("  /decay set half_life_days=..              Adjust decay")
    print("  /energy set budget=..                     Adjust dream energy budget")
    print("  /ingest lno <path.json>                   Send residue to LNO (if present)")
    print("  /quit")

def cmd_state(engine: DreamEngine):
    cfg = engine.cfg
    files = list(RES_DIR.glob("*.json"))
    approved = quarantined = 0
    for f in files:
        try:
            j = json.load(open(f, "r", encoding="utf-8"))
            if j.get("approved"): approved += 1
            else: quarantined += 1
        except Exception:
            pass
    print(APP)
    print(f"residues: total={len(files)} approved={approved} quarantine={quarantined}")
    print(f"energy_budget={cfg['energy_budget']} overlap_factor={cfg['overlap_factor']}")
    print(f"daydream_budget={cfg['daydream_budget']} daydream_overlap={cfg['daydream_overlap']}")
    print(f"higgs_kernel_chance={cfg['higgs_kernel_chance']} (dream)  {cfg['higgs_kernel_daydream']} (day-dream)")
    print(f"osf: entropy_jump={cfg['osf']['entropy_jump']} affect_polarity={cfg['osf']['affect_polarity']}")
    print(f"decay: quarantine_days={cfg['decay']['quarantine_days']} half_life_days={cfg['decay']['half_life_days']}")
    if engine.last_residue_path:
        print("last_residue:", engine.last_residue_path)

def main():
    ensure_default_cfg()
    cfg = load_cfg()
    engine = DreamEngine(cfg)
    print_help()

    while True:
        try:
            line = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n[exit]")
            break
        if not line:
            continue
        parts = line.split()
        cmd = parts[0].lower()

        if cmd in ["/quit","/exit"]:
            engine.autorun_stop()
            break

        if cmd == "/state":
            cmd_state(engine)
            continue

        if cmd == "/dream":
            if len(parts)>=2:
                sub = parts[1].lower()
                if sub == "once":
                    # optional key=val args
                    kwargs = {}
                    for p in parts[2:]:
                        if "=" in p:
                            k,v = p.split("=",1)
                            kwargs[k.strip()] = v.strip()
                    engine.dream_once(energy=kwargs.get("energy"), overlap=kwargs.get("overlap"))
                elif sub == "start":
                    engine.autorun_start()
                elif sub == "stop":
                    engine.autorun_stop()
                else:
                    print("[ERR] /dream once | start | stop")
            else:
                print("[ERR] /dream once | start | stop")
            continue

        if cmd == "/daydream":
            # /daydream now [topic=..]
            if len(parts)>=2 and parts[1].lower()=="now":
                topic = None
                for p in parts[2:]:
                    if p.startswith("topic="):
                        topic = p.split("=",1)[1]
                engine.daydream_now(topic=topic)
            else:
                print("[ERR] /daydream now [topic=..]")
            continue

        if cmd == "/osf":
            # /osf set entropy=.. affect=..
            if len(parts)>=2 and parts[1].lower()=="set":
                for p in parts[2:]:
                    if p.startswith("entropy="):
                        cfg["osf"]["entropy_jump"]=float(p.split("=",1)[1])
                    if p.startswith("affect="):
                        cfg["osf"]["affect_polarity"]=float(p.split("=",1)[1])
                save_json(CFG_FILE.with_suffix(".json"), cfg)
                print("[ok] OSF updated")
            else:
                print("[ERR] /osf set entropy=.. affect=..")
            continue

        if cmd == "/decay":
            # /decay set half_life_days=..
            if len(parts)>=2 and parts[1].lower()=="set":
                for p in parts[2:]:
                    if p.startswith("half_life_days="):
                        cfg["decay"]["half_life_days"]=int(p.split("=",1)[1])
                save_json(CFG_FILE.with_suffix(".json"), cfg)
                print("[ok] decay updated")
            else:
                print("[ERR] /decay set half_life_days=..")
            continue

        if cmd == "/energy":
            # /energy set budget=..
            if len(parts)>=2 and parts[1].lower()=="set":
                for p in parts[2:]:
                    if p.startswith("budget="):
                        cfg["energy_budget"]=int(p.split("=",1)[1])
                save_json(CFG_FILE.with_suffix(".json"), cfg)
                print("[ok] energy budget updated")
            else:
                print("[ERR] /energy set budget=..")
            continue

        if cmd == "/ingest":
            # /ingest lno <path.json>
            if len(parts)>=3 and parts[1].lower()=="lno":
                pth = Path(" ".join(parts[2:])).resolve()
                if pth.exists():
                    try_ingest_lno(str(pth))
                else:
                    print("[ERR] file not found:", pth)
            else:
                print("[ERR] /ingest lno <path.json>")
            continue

        print_help()

if __name__ == "__main__":
    main()
