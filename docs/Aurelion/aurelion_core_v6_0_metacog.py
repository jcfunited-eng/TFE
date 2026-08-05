# aurelion_core_v6_0_metacog.py
# Aurelion v6.0 — Emergent Meta-Cognition (schema monitor + reflections + goal drift)

from __future__ import annotations
import json, sys, time
from pathlib import Path
from typing import List, Optional, Dict

import numpy as np

# Aurelion building blocks you already have
from primitive_sensory_pack import DIMS
from morphospace_multimodal import MorphospaceMultimodal, senses_from_text
from language_field import LanguageFieldLearner
from selfweave import SelfWeave
from meta_monitor import MetaMonitor

LANG_MEM = "language_memory.json"
DIALOGUE_MEM = "dialogue_memory.json"
ASSOC_MEM = "associations_v6.json"

GOALS = ("STABILIZE", "EXPLORE", "FOCUS")

def adaptive_alpha(phi_now: float, phi_prev: float, base: float = 0.55) -> float:
    delta = float(phi_now - phi_prev)
    alpha = base + np.clip(delta, -0.1, 0.1) * 0.5
    return float(np.clip(alpha, 0.45, 0.65))

def load_dialogue() -> List[Dict]:
    p = Path(DIALOGUE_MEM)
    if not p.exists():
        return []
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        if isinstance(data, list):
            # basic shape check
            ok = []
            for d in data:
                if isinstance(d, dict) and "user" in d and "aurelion" in d:
                    ok.append(d)
            return ok
    except Exception:
        pass
    return []

def save_dialogue(buf: List[Dict]) -> None:
    Path(DIALOGUE_MEM).write_text(json.dumps(buf, indent=2), encoding="utf-8")

def field_metrics(field: MorphospaceMultimodal) -> Dict[str,float]:
    # simple norms as proxies (your Morphospace likely has these or we approximate)
    try:
        phi = float(field.coherence())
    except Exception:
        phi = 0.5
    try:
        H = float(field.entropy())
    except Exception:
        H = 0.5
    try:
        E = float(field.energy())
    except Exception:
        E = 0.5
    return {"phi":phi, "H":H, "E":E}

def format_status(field: MorphospaceMultimodal, goal:str, turns:int, schemas:List[str]) -> str:
    m = field_metrics(field)
    return (f"φ={m['phi']:.3f}  H={m['H']:.3f}  Energy={m['E']:.3f}  |  "
            f"goal={goal}  mem={turns} turns  schemas={len(schemas)}")

def base_style(goal:str) -> str:
    if goal == "STABILIZE": return "(steady) "
    if goal == "EXPLORE":   return "(open) "
    if goal == "FOCUS":     return "(focused) "
    return ""

def reflect_line(reflection:str) -> str:
    if not reflection: return ""
    return f" [meta] {reflection}"

def run():
    # Core objects
    field = MorphospaceMultimodal()  # uses unified dims from primitive_sensory_pack
    learner = LanguageFieldLearner(memory_path=LANG_MEM, load=True)
    weave = SelfWeave(ASSOC_MEM)
    monitor = MetaMonitor(window=12)
    dialogue = load_dialogue()

    goal = "STABILIZE"
    prev_phi = 0.5

    print("Aurelion v6.0 — Emergent Meta-Cognition")
    print("Commands: /state  /goal <stabilize|explore|focus>  /show <word>  /map <word>  /schemas  /save  /load  /quit")

    if dialogue:
        print(f"[INFO] Loaded {len(dialogue)} prior dialogue turns.")

    while True:
        try:
            msg = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not msg:
            continue

        if msg.lower() in ("/quit", "/exit"):
            break

        # Commands
        if msg.startswith("/goal"):
            parts = msg.split()
            if len(parts) == 2:
                g = parts[1].strip().upper()
                if g in GOALS:
                    goal = g
                    print(f"[OK] Intent set to {goal}")
                else:
                    print("[ERR] Unknown goal. Use stabilize|explore|focus")
            else:
                print("[ERR] Usage: /goal focus")
            continue

        if msg == "/state":
            active_schemas = weave.list_schemas()[:3]
            print(format_status(field, goal, len(dialogue), active_schemas))
            continue

        if msg == "/schemas":
            names = weave.list_schemas()
            if not names:
                print("(no schemas yet)")
            else:
                print("— Schemas —")
                for n in names[:25]:
                    print(" ", n)
            continue

        if msg == "/save":
            try:
                learner.save()  # persists language_memory.json
            except Exception:
                pass
            weave.save()
            save_dialogue(dialogue)
            print("[OK] Saved.")
            continue

        if msg == "/load":
            # reload language and associations
            try:
                LanguageFieldLearner(memory_path=LANG_MEM, load=True)  # refresh file exists
            except Exception:
                pass
            weave = SelfWeave(ASSOC_MEM)
            dialogue = load_dialogue()
            print("[OK] Reloaded memory.")
            continue

        # Otherwise: user utterance
        senses = senses_from_text(msg)
        # stimulate field (adaptive alpha)
        cur_phi = field.coherence() if hasattr(field, "coherence") else 0.5
        alpha = adaptive_alpha(cur_phi, prev_phi, base=0.55)
        prev_phi = cur_phi
        field.stimulate(senses, alpha=alpha)

        # learn token signatures
        learner.learn(msg, senses)
        tokens = learner.tokenize(msg)

        # grow associations/schemas & read active schemas
        weave.learn_from_tokens(tokens)
        active = weave.active_schemas(tokens)

        # monitor internal pulse
        met = field_metrics(field)
        monitor.pulse(met["phi"], met["H"], met["E"], goal, tokens, active)
        reflection, drift = monitor.summarize()
        if drift:
            goal = drift

        # craft reply: short, reflective, grounded in goal
        style = base_style(goal)
        # pick 1–2 salient tokens to echo
        echo = ", ".join(tokens[:2]) if tokens else ""
        line = f"{style}I'm reading {('‘'+echo+'’ ') if echo else ''}and weaving."
        rline = reflect_line(reflection)
        out = line + (rline if rline else "")

        print(f"Aurelion: {out}")

        # append dialogue
        dialogue.append({"user": msg, "aurelion": out})
        # keep it small
        if len(dialogue) > 200:
            dialogue = dialogue[-120:]

def main():
    try:
        run()
    except Exception as e:
        print("[FATAL] Aurelion failed to start:")
        import traceback; traceback.print_exc()
        input("Press Enter to exit...")

if __name__ == "__main__":
    main()
