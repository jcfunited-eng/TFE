# Aurelion v10.10 — Scenario Forge (Intentional Forecasting)
# Drop this file in: C:\Users\joeta\OneDrive\Desktop\Aurelion
# Run:  python aurelion_core_v10_10_scenario_forge.py

import os, json, math, random, hashlib
from datetime import datetime, timedelta
from pathlib import Path

def nowz(): return datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")  # OK for our sandbox
ROOT = Path(__file__).resolve().parent
RES_DIR = ROOT / "memory" / "morphogen" / "residues"
RES_DIR.mkdir(parents=True, exist_ok=True)

DEFAULT = {
    "osf": {"entropy_jump": 0.58, "affect_polarity": 0.85},
    "ethics": {"care":0.40,"fairness":0.25,"autonomy":0.20,"prudence":0.15},
    "bias_window": 64,
    "branch_steps": 4,
}

class ScenarioForge:
    def __init__(self):
        self.reset()

    def reset(self):
        self.title = None
        self.horizon = "3m"
        self.risk = "balanced"
        self.elements = []
        self.personas = []  # [{name,type,weight}]
        self.last_residue_path = None
        self.last_mom_line = None

    def _rand_curve(self, n, base=0.45, jitter=0.12):
        e, h = [], []
        val_e = base + random.uniform(-0.05,0.05)
        val_h = base + random.uniform(-0.05,0.05)
        for _ in range(n):
            val_e = max(0.0, min(1.0, val_e + random.uniform(-jitter, jitter)))
            val_h = max(0.0, min(1.0, val_h + random.uniform(-jitter, jitter)))
            e.append(round(val_e, 3)); h.append(round(val_h, 3))
        return e, h

    def _ethics_score(self):
        # simple weighted presence of balanced framing in elements
        txt = " ".join(self.elements).lower()
        pos = sum(1 for k in ["safety","care","fair","prudence","privacy","transparency"] if k in txt)
        return round(min(1.0, 0.25 + 0.12*pos), 2)

    def _persona_eval(self):
        # crude acceptance based on risk + ethics score
        eth = self._ethics_score()
        base = {"conservative":0.45,"balanced":0.55,"aggressive":0.5}[self.risk]
        acc = round(max(0.0, min(1.0, 0.45*eth + 0.55*base + random.uniform(-0.07,0.07))), 2)
        out=[]
        for p in self.personas:
            tweak = 0.05 if p.get("type")=="skilled" else -0.02
            out.append({"name":p["name"],"type":p["type"],"weight":p["weight"],
                        "acceptance": round(max(0, min(1, acc + tweak)),2),
                        "rationale": "Skilled fit" if tweak>0 else "Plain-language clarity"})
        return out

    def _branches(self, k):
        # tiny futures with success/failure; OSF/ethics gates approximate
        eth = self._ethics_score()
        branches=[]
        for i in range(k):
            success_p = max(0.05, min(0.9, 0.35 + 0.4*eth + random.uniform(-0.1,0.1)))
            outcome = "success" if random.random()<success_p else "failure"
            branches.append({
                "step": i+1,
                "outcome": outcome,
                "p": round(success_p,2),
                "note": "Reversible step" if outcome=="failure" else "Forward gain"
            })
        return branches

    def _image_chard(self):
        # optional visual memory scaffold from title/elements (spine/veins/tissue)
        gist = (self.title or "scenario").strip()
        veins=[]
        for w in ["shape","weight","time","cost","risk","domain"]:
            if any(w in el.lower() for el in self.elements):
                veins.append({"feature":w,"type":"text","confidence":0.6})
        if not veins:
            veins=[{"feature":"shape","type":"text","confidence":0.4}]
        return {
            "spine":{"gist":gist,"when":nowz(),"where":"internal","confidence":0.85},
            "primary_veins":veins,
            "secondary_veins":[{"context":"persona-dialog","modality":"affect","confidence":0.45}],
            "tissue_hint":{"mood":"focused","confidence":0.35}
        }

    def run(self):
        if not self.title: self.title = "Untitled Scenario"
        if not self.personas:
            self.personas = [{"name":"Michael","type":"skilled","weight":0.6},
                             {"name":"Mom","type":"mom","weight":0.4}]
        energy, entropy = self._rand_curve(12, base=0.48, jitter=0.10)
        personas = self._persona_eval()
        branches = self._branches(DEFAULT["branch_steps"])
        gaps=[]
        if len(self.elements)<2: gaps.append("Add at least two concrete elements.")
        if all(p["acceptance"]<0.55 for p in personas): gaps.append("Persona acceptance is low—clarify purpose/value.")
        ethical = self._ethics_score()
        bias = {"window": DEFAULT["bias_window"], "status": "clean"}
        tapestries = ["engineering","self","planning","curiosity"]
        overlaps = [{"u":"engineering","v":"planning","w":0.42},{"u":"self","v":"curiosity","w":0.31}]
        rid = hashlib.sha1(f"{nowz()}::{self.title}::{random.random()}".encode()).hexdigest()[:12]
        fname = f"{datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')}-{rid}-scenario.json"
        residue = {
            "id": rid,
            "timestamp": nowz(),
            "origin": "scenario",
            "title": self.title,
            "horizon": self.horizon,
            "risk": self.risk,
            "tapestries": tapestries,
            "overlaps": overlaps,
            "energy_curve": energy,
            "entropy_curve": entropy,
            "semantic_tags": ["scenario","forecast","personas"],
            "ethical_score": ethical,
            "bias_scan": bias,
            "osf_events": [],
            "quarantine_until": (datetime.utcnow()+timedelta(days=0)).strftime("%Y-%m-%d"),  # approved
            "decay_half_life_days": 7,
            "elements": self.elements,
            "personas": personas,
            "branches": branches,
            "knowledge_gaps": gaps,
            "image_chard": self._image_chard()
        }
        RES_DIR.mkdir(parents=True, exist_ok=True)
        outp = RES_DIR / fname
        with open(outp, "w", encoding="utf-8") as f: json.dump(residue, f, indent=2)
        self.last_residue_path = str(outp)
        mom_note = f"(mom) {self.title} — score≈{round(0.5+0.3*ethical,2)} | personas ok={sum(1 for p in personas if p['acceptance']>=0.55)}/{len(personas)} | gaps={len(gaps)}"
        self.last_mom_line = mom_note
        print(f"[scenario] wrote: {outp}")
        print(mom_note)

SF = ScenarioForge()

def main():
    print("Aurelion v10.10 — Scenario Forge (Intentional Forecasting)")
    print("Commands:")
    print("  /sf new \"<title>\" horizon=6m risk=balanced")
    print("  /sf add element \"<text>\"")
    print("  /sf add persona skilled|mom \"<name>\" weight=0.6")
    print("  /sf run | /sf mom | /sf export <path.json>")
    print("  /state | /reset | /quit")
    while True:
        try:
            line = input("You: ").strip()
        except EOFError:
            break
        if not line: continue
        if line.startswith("/quit"): break
        if line.startswith("/reset"):
            SF.reset(); print("[ok] reset"); continue
        if line.startswith("/state"):
            print(f"title={SF.title} horizon={SF.horizon} risk={SF.risk} elems={len(SF.elements)} personas={len(SF.personas)}")
            print(f"last_residue={SF.last_residue_path}"); continue
        if line.startswith("/sf new"):
            # parse title in quotes
            title = None
            if "\"" in line:
                try:
                    title = line.split("\"",1)[1].rsplit("\"",1)[0]
                except: pass
            if not title: title = "Scenario"
            SF.reset(); SF.title = title
            if "horizon=" in line:
                SF.horizon = line.split("horizon=",1)[1].split()[0]
            if "risk=" in line:
                SF.risk = line.split("risk=",1)[1].split()[0]
            print(f"[ok] new scenario: {SF.title} horizon={SF.horizon} risk={SF.risk}")
            continue
        if line.startswith("/sf add element"):
            if "\"" in line:
                txt = line.split("\"",1)[1].rsplit("\"",1)[0]
            else:
                txt = line.replace("/sf add element","").strip()
            SF.elements.append(txt); print(f"[ok] element+ ({len(SF.elements)})"); continue
        if line.startswith("/sf add persona"):
            parts = line.split()
            ptype = "mom" if "mom" in parts else ("skilled" if "skilled" in parts else "other")
            name = "Persona"
            weight = 0.5
            if "\"" in line:
                name = line.split("\"",1)[1].rsplit("\"",1)[0]
            if "weight=" in line:
                try: weight = float(line.split("weight=",1)[1].split()[0])
                except: pass
            SF.personas.append({"name":name,"type":ptype,"weight":weight})
            print(f"[ok] persona+ {name} ({ptype}, w={weight})"); continue
        if line.startswith("/sf run"):
            SF.run(); continue
        if line.startswith("/sf mom"):
            print(SF.last_mom_line or "(mom) no run yet"); continue
        if line.startswith("/sf export"):
            path = line.replace("/sf export","").strip()
            if not path: print("[ERR] provide path"); continue
            if not SF.last_residue_path: print("[ERR] run first"); continue
            try:
                with open(SF.last_residue_path,"r",encoding="utf-8") as f: data=json.load(f)
                with open(ROOT/path,"w",encoding="utf-8") as g: json.dump(data,g,indent=2)
                print(f"[export] wrote {ROOT/path}")
            except Exception as e:
                print(f"[ERR] {e}")
            continue
        print("[INFO] commands: /sf new|add|run|mom|export  /state  /reset  /quit")

if __name__=="__main__":
    main()
