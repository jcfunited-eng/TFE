#!/usr/bin/env python3
# Aurelion v10.7 — Meta-Dream Observer (MDO)
# Read-only observer over dream/day-dream residues with Mom-friendly summaries.
# Pure stdlib; Windows-friendly.

import os, sys, json, time, threading
from datetime import datetime
from collections import Counter, defaultdict

APP = "Aurelion v10.7 — Meta-Dream Observer (MDO)"

# ------------------------- helpers -------------------------

def utcnow_str():
    # timezone-agnostic short UTC stamp (compatible with your other tools)
    return datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

def safe_read_json(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None

def tail_mean(values):
    if not values: return None
    return sum(values)/len(values)

def trend(last_vals, k=5, eps=1e-6):
    """Very simple trend detector over last k points: up/down/flat."""
    if not last_vals:
        return "n/a"
    arr = last_vals[-k:] if len(last_vals) > k else last_vals[:]
    if len(arr) < 2:
        return "flat"
    diff = arr[-1] - arr[0]
    if diff > eps: return "up"
    if diff < -eps: return "down"
    return "flat"

def ensure_dir(path):
    os.makedirs(path, exist_ok=True)

def last_nonempty(seq, default=None):
    for x in reversed(seq):
        if x is not None: return x
    return default

# ------------------------- core observer -------------------------

class MDO:
    def __init__(self,
                 residues_dir="memory/morphogen/residues",
                 out_dir="memory/morphogen/mdo",
                 lucid_dump="lucid_weights_dump.json",
                 window=50,
                 watch_interval=60):
        self.residues_dir = residues_dir
        self.out_dir = out_dir
        self.lucid_dump = lucid_dump
        self.window = int(window)
        self.watch_interval = int(watch_interval)
        self._watch_thread = None
        self._watch_stop = threading.Event()
        ensure_dir(self.out_dir)

        self._last_scan = None
        self._last_metrics = {}
        self._last_report = ""

    # ---------- scanning & aggregation ----------

    def scan(self):
        files = []
        if os.path.isdir(self.residues_dir):
            for name in os.listdir(self.residues_dir):
                if name.lower().endswith(".json"):
                    files.append(os.path.join(self.residues_dir, name))
        files.sort()  # timestamp-encoded naming sorts naturally

        total = len(files)
        # rolling window
        recent = files[-self.window:] if total > self.window else files[:]

        stats = {
            "scanned_at": utcnow_str(),
            "total_files": total,
            "window_size": self.window,
            "considered_files": len(recent),
            "dream_count": 0,
            "daydream_count": 0,
            "approved": 0,
            "quarantine": 0,
            "osf_aborts": 0,
            "avg_ethics": None,
            "bias_clean": 0,
            "bias_flagged": 0,
            "entropy_tail": [],
            "energy_tail": [],
            "entropy_trend": "n/a",
            "energy_trend": "n/a",
            "top_tapestries": [],
            "top_motifs": [],
            "last_residue": None,
            "last_timestamp": None,
            "lucid_pairs": None,  # optional
        }

        ethics_scores = []
        tapestries = Counter()
        motifs = Counter()
        last_ts = None
        last_id = None

        for p in recent:
            data = safe_read_json(p)
            if not data:
                continue

            origin = data.get("origin", "dream")
            if origin == "dream":
                stats["dream_count"] += 1
            elif origin == "daydream":
                stats["daydream_count"] += 1

            # approval/quarantine heuristic:
            # approved if quarantine_until missing or in the past AND OSF not present
            q_until = data.get("quarantine_until")
            osf_events = data.get("osf_events", [])
            if osf_events:
                stats["osf_aborts"] += 1

            approved = True
            if q_until:
                try:
                    # treat any future date as quarantined
                    approved = (q_until < datetime.utcnow().strftime("%Y-%m-%d"))
                except Exception:
                    approved = False
            if osf_events:
                # conservative: any OSF event => not approved
                approved = False

            if approved:
                stats["approved"] += 1
            else:
                stats["quarantine"] += 1

            # ethics
            e = data.get("ethical_score")
            if isinstance(e, (int, float)):
                ethics_scores.append(float(e))

            # bias
            b = data.get("bias_scan")
            if isinstance(b, dict):
                if (b.get("status") or "").lower() == "clean":
                    stats["bias_clean"] += 1
                else:
                    stats["bias_flagged"] += 1
            elif isinstance(b, str):
                if b.lower() == "clean":
                    stats["bias_clean"] += 1
                else:
                    stats["bias_flagged"] += 1

            # entropy/energy tails (use last point)
            ent = None
            eng = None
            if data.get("entropy_curve"):
                try:
                    ent = data["entropy_curve"][-1]
                except Exception:
                    ent = None
            if data.get("energy_curve"):
                try:
                    eng = data["energy_curve"][-1]
                except Exception:
                    eng = None
            if isinstance(ent, (int, float)): stats["entropy_tail"].append(float(ent))
            if isinstance(eng, (int, float)): stats["energy_tail"].append(float(eng))

            # tapestries & motifs (motifs may be missing in v10.5 residues)
            for t in data.get("tapestries", []) or []:
                tapestries[t] += 1
            for m in data.get("motifs", []) or []:
                tok = m.get("token")
                if tok: motifs[tok] += 1

            # last id/timestamp (from filename or field)
            fname = os.path.basename(p)
            last_id = fname
            try:
                ts = data.get("timestamp")
                if not ts and "-" in fname:
                    ts = fname.split("-")[0]  # 20251112T052000Z-...
                last_ts = ts
            except Exception:
                last_ts = None

        stats["avg_ethics"] = round(tail_mean(ethics_scores), 3) if ethics_scores else None
        stats["entropy_trend"] = trend(stats["entropy_tail"])
        stats["energy_trend"] = trend(stats["energy_tail"])
        stats["top_tapestries"] = [k for k,_ in tapestries.most_common(5)]
        stats["top_motifs"] = [k for k,_ in motifs.most_common(5)]
        stats["last_residue"] = last_id
        stats["last_timestamp"] = last_ts

        # optional: lucid learned pairs
        if os.path.isfile(self.lucid_dump):
            try:
                j = safe_read_json(self.lucid_dump) or {}
                # accept either {"pairs": N} or {"learned_pairs": N} or array
                if isinstance(j, dict):
                    n = j.get("pairs") or j.get("learned_pairs")
                    if isinstance(n, int):
                        stats["lucid_pairs"] = n
                    else:
                        stats["lucid_pairs"] = None
                elif isinstance(j, list):
                    stats["lucid_pairs"] = len(j)
            except Exception:
                stats["lucid_pairs"] = None

        # persist
        ensure_dir(self.out_dir)
        metrics_path = os.path.join(self.out_dir, "mdo_metrics.json")
        with open(metrics_path, "w", encoding="utf-8") as f:
            json.dump(stats, f, ensure_ascii=False, indent=2)

        # human report (short & mom-friendly)
        self._last_metrics = stats
        self._last_scan = utcnow_str()
        self._last_report = self._render_report(stats)
        report_path = os.path.join(self.out_dir, "mdo_report.txt")
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(self._last_report)

        return stats

    def _render_report(self, s):
        def fmt(x):
            return "n/a" if x is None else str(x)
        lines = []
        lines.append(f"[{self._last_scan}] MDO Report")
        lines.append(f"  window={s['window_size']} files={s['considered_files']}/{s['total_files']}  dreams={s['dream_count']} daydreams={s['daydream_count']}")
        lines.append(f"  approved={s['approved']} quarantine={s['quarantine']} osf_aborts={s['osf_aborts']}")
        lines.append(f"  ethics_avg≈{fmt(s['avg_ethics'])}  bias: clean={s['bias_clean']} flagged={s['bias_flagged']}")
        if s["entropy_tail"]:
            lines.append(f"  entropy(last={round(s['entropy_tail'][-1],3)}) trend={s['entropy_trend']}")
        else:
            lines.append("  entropy: n/a")
        if s["energy_tail"]:
            lines.append(f"  energy(last={round(s['energy_tail'][-1],3)}) trend={s['energy_trend']}")
        else:
            lines.append("  energy: n/a")
        if s["top_tapestries"]:
            lines.append(f"  top_tapestries: {', '.join(s['top_tapestries'])}")
        if s["top_motifs"]:
            lines.append(f"  top_motifs: {', '.join(s['top_motifs'])}")
        lines.append(f"  last={s['last_residue']} at {s['last_timestamp']}")
        if s.get("lucid_pairs") is not None:
            lines.append(f"  lucid_pairs={s['lucid_pairs']}")
        return "\n".join(lines)

    # ---------- watch mode ----------

    def watch_on(self):
        if self._watch_thread and self._watch_thread.is_alive():
            print("[watch] already ON")
            return
        self._watch_stop.clear()
        self._watch_thread = threading.Thread(target=self._watch_loop, daemon=True)
        self._watch_thread.start()
        print(f"[watch] started ({self.watch_interval}s interval)")

    def _watch_loop(self):
        while not self._watch_stop.is_set():
            try:
                self.scan()
                # brief console nudge for situational awareness
                mom = self.mom_line(self._last_metrics) if self._last_metrics else "(mom) n/a"
                print(mom)
            except Exception as e:
                print(f"[watch] scan error: {e}")
            self._watch_stop.wait(self.watch_interval)

    def watch_off(self):
        if self._watch_thread and self._watch_thread.is_alive():
            self._watch_stop.set()
            self._watch_thread.join(timeout=self.watch_interval + 1)
            print("[watch] stopped")
        else:
            print("[watch] already OFF")

    # ---------- summaries ----------

    def mom_line(self, s=None):
        if s is None: s = self._last_metrics or {}
        def pick(x, fallback="n/a"):
            return fallback if x in (None, "", []) else x
        ethics = s.get("avg_ethics")
        e_tr = s.get("entropy_trend","n/a")
        n_tr = s.get("energy_trend","n/a")
        tops = s.get("top_tapestries",[])[:2]
        last_ts = pick(s.get("last_timestamp"))
        approved = s.get("approved",0)
        quarantine = s.get("quarantine",0)
        total = s.get("considered_files",0)
        return f"(mom) residues={total} | approved={approved} quarantined={quarantine} | ethics≈{('n/a' if ethics is None else round(ethics,2))} | trend: entropy {e_tr} / energy {n_tr} | top: {', '.join(tops) if tops else 'n/a'} | last: {last_ts}"

# ------------------------- CLI -------------------------

def print_header():
    print(APP)
    print("Commands:")
    print("  /state")
    print("  /scan")
    print("  /report")
    print("  /watch on|off")
    print("  /window set <N>")
    print("  /mom")
    print("  /export <path.json>")
    print("  /quit")

def main():
    mdo = MDO()
    print_header()
    while True:
        try:
            raw = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n[quit]")
            mdo.watch_off()
            break
        if not raw: 
            continue

        parts = raw.split()
        cmd = parts[0].lower()

        if cmd == "/quit":
            mdo.watch_off()
            break

        elif cmd == "/state":
            print(f"residues_dir={mdo.residues_dir}")
            print(f"out_dir={mdo.out_dir}")
            print(f"lucid_dump={mdo.lucid_dump}")
            print(f"window={mdo.window} watch_interval={mdo.watch_interval}")
            if mdo._last_metrics:
                print(mdo._render_report(mdo._last_metrics))

        elif cmd == "/scan":
            stats = mdo.scan()
            print(mdo._render_report(stats))

        elif cmd == "/report":
            if not mdo._last_report:
                print("[info] no prior scan — running one now…")
                stats = mdo.scan()
                print(mdo._render_report(stats))
            else:
                print(mdo._last_report)

        elif cmd == "/watch":
            if len(parts) < 2:
                print("[usage] /watch on|off")
            elif parts[1].lower() == "on":
                mdo.watch_on()
            elif parts[1].lower() == "off":
                mdo.watch_off()
            else:
                print("[usage] /watch on|off")

        elif cmd == "/window":
            if len(parts) == 3 and parts[1].lower() == "set":
                try:
                    mdo.window = max(1, int(parts[2]))
                    print(f"[ok] window={mdo.window}")
                except Exception:
                    print("[err] /window set <N>")
            else:
                print("[usage] /window set <N>")

        elif cmd == "/mom":
            if not mdo._last_metrics:
                m = mdo.mom_line({})
            else:
                m = mdo.mom_line(mdo._last_metrics)
            print(m)

        elif cmd == "/export":
            if len(parts) != 2:
                print("[usage] /export <path.json>")
            else:
                path = parts[1]
                if not mdo._last_metrics:
                    mdo.scan()
                try:
                    with open(path, "w", encoding="utf-8") as f:
                        json.dump(mdo._last_metrics, f, ensure_ascii=False, indent=2)
                    print(f"[export] wrote: {os.path.abspath(path)}")
                except Exception as e:
                    print(f"[export] error: {e}")

        else:
            print("[INFO] commands: /state  /scan  /report  /watch on|off  /window set <N>  /mom  /export <path.json>  /quit")

if __name__ == "__main__":
    main()
