# Aurelion v10.11 — Reflective Diary (RDY) & Semantic Memory Bridge
# Place in: C:\Users\joeta\OneDrive\Desktop\Aurelion
# Run: python aurelion_core_v10_11_reflective_diary.py

import os, json, math, random
from datetime import datetime
from pathlib import Path
from collections import defaultdict

def nowz(): return datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

ROOT = Path(__file__).resolve().parent
RES_DIR = ROOT / "memory" / "morphogen" / "residues"
REF_DIR = ROOT / "memory" / "reflective"
REF_DIR.mkdir(parents=True, exist_ok=True)

class ReflectiveDiary:
    def __init__(self):
        self.diary_path = None
        self.themes_path = None
        self.themes = {}
        self.entries = []
        self.mom_summary = ""

    def _trend(self, seq):
        if not seq or len(seq) < 2: return "steady"
        return "up" if seq[-1] > seq[0] else "down"

    def _summarize_residue(self, r):
        ori = r.get("origin","unknown")
        gist = (r.get("image_chard",{}).get("spine",{}) or {}).get("gist","something unknown")
        ethics = r.get("ethical_score",0.0)
        bias = r.get("bias_scan",{}).get("status","clean")
        tapestries = ", ".join(r.get("tapestries",[]))
        e = r.get("energy_curve",[0])
        h = r.get("entropy_curve",[0])
        trend_e = self._trend(e)
        trend_h = self._trend(h)
        line = f"I reflected on {ori} about {gist}. Energy {trend_e}, entropy {trend_h}."
        if ethics < 0.4: line += " I noticed imbalance in care or fairness."
        if bias != "clean": line += " I recognized internal distortion."
        if tapestries: line += f" Themes: {tapestries}."
        return line

    def _update_themes(self, r):
        for t in r.get("tapestries",[]):
            self.themes.setdefault(t, {"count":0,"ethics":[]})
            self.themes[t]["count"] += 1
            self.themes[t]["ethics"].append(r.get("ethical_score",0.0))

    def update(self):
        files = sorted(RES_DIR.glob("*.json"))
        if not files:
            print("[reflect] no residues found")
            return
        diary_lines = []
        for f in files:
            try:
                r = json.load(open(f,"r",encoding="utf-8"))
                q = r.get("quarantine_until","")
                if q and q > datetime.utcnow().strftime("%Y-%m-%d"): continue
                diary_lines.append(self._summarize_residue(r))
                self._update_themes(r)
            except Exception as e:
                print(f"[warn] {f.name}: {e}")
        if not diary_lines:
            print("[reflect] no eligible residues")
            return
        # Write diary
        diary_name = f"diary_{datetime.utcnow().strftime('%Y%m%d')}.txt"
        diary_path = REF_DIR / diary_name
        with open(diary_path,"w",encoding="utf-8") as f:
            f.write(f"{datetime.utcnow().strftime('%Y-%m-%d')} — Reflective Diary\n")
            for line in diary_lines:
                f.write(line+"\n")
        # Write themes
        theme_stats = {t:{"count":v["count"],"ethics_avg":round(sum(v["ethics"])/max(1,len(v["ethics"])),2)}
                       for t,v in self.themes.items()}
        with open(REF_DIR/"themes.json","w",encoding="utf-8") as f: json.dump(theme_stats,f,indent=2)
        self.diary_path = str(diary_path)
        self.themes_path = str(REF_DIR/"themes.json")
        ethics_all = [x["ethics_avg"] for x in theme_stats.values()]
        mean_eth = round(sum(ethics_all)/max(1,len(ethics_all)),2) if ethics_all else 0
        self.mom_summary = f"(mom) diary themes={len(theme_stats)} ethics≈{mean_eth} entries={len(diary_lines)}"
        print(f"[reflect] wrote {self.diary_path}")
        print(f"[reflect] wrote {self.themes_path}")
        print(self.mom_summary)

    def show(self):
        if not self.diary_path:
            files = sorted(REF_DIR.glob("diary_*.txt"))
            if not files: print("[reflect] no diary yet"); return
            self.diary_path = str(files[-1])
        print(open(self.diary_path,"r",encoding="utf-8").read())

    def mom(self):
        print(self.mom_summary or "(mom) no summary yet")

RDY = ReflectiveDiary()

def main():
    print("Aurelion v10.11 — Reflective Diary (RDY)")
    print("Commands:")
    print("  /reflect update | show | mom | export <file> | quit")
    while True:
        try: line = input("You: ").strip()
        except EOFError: break
        if not line: continue
        if line.startswith("/quit"): break
        if line.startswith("/reflect update"):
            RDY.update(); continue
        if line.startswith("/reflect show"):
            RDY.show(); continue
        if line.startswith("/reflect mom"):
            RDY.mom(); continue
        if line.startswith("/reflect export"):
            path = line.replace("/reflect export","").strip()
            if not path: print("[ERR] path needed"); continue
            if not RDY.diary_path: print("[ERR] run update first"); continue
            try:
                os.replace(RDY.diary_path, path)
                print(f"[export] moved to {path}")
            except Exception as e:
                print(f"[ERR] {e}")
            continue
        print("[INFO] commands: /reflect update | show | mom | export <file> | quit")

if __name__ == "__main__":
    main()
