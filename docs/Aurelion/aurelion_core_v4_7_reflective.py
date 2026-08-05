# aurelion_core_v4_7_reflective.py
# v4.7 — Multimodal Cognition with Reflective Dialogue Memory + Curiosity Engine (dim fix)

from __future__ import annotations
import json, sys
from pathlib import Path
from typing import Dict
import numpy as np

# local modules (existing from your v4.x stack)
from primitive_sensory_pack import DIMS
from morphospace_multimodal import MorphospaceMultimodal, senses_from_text, MOD_ORDER
from language_field import LanguageFieldLearner
from resonance_visualizer import visualize_cross_modal
from reflective_memory import ReflectiveMemory
from curiosity_engine import maybe_question

LANG_MEM_PATH = "language_memory.json"
DIALOGUE_MEM_PATH = "dialogue_memory.json"

def cosine(a: np.ndarray, b: np.ndarray) -> float:
    na = float(np.linalg.norm(a)); nb = float(np.linalg.norm(b))
    if na < 1e-9 or nb < 1e-9: return 0.0
    return float(np.dot(a, b) / (na * nb))

def field_metrics(field) -> Dict[str, float]:
    vecs = [field.modalities[m].state for m in MOD_ORDER if m in field.modalities]
    if not vecs: return {"phi": 0.0, "H": 0.0, "E": 0.0}
    # coherence = avg cosine across modality pairs
    cos_vals = []
    for i in range(len(vecs)):
        for j in range(i + 1, len(vecs)):
            cos_vals.append(cosine(vecs[i], vecs[j]))
    phi = float(np.mean(cos_vals)) if cos_vals else 0.0
    # entropy proxy = std of modality norms (lower std => higher balance)
    mags = np.asarray([np.linalg.norm(v) for v in vecs], dtype=np.float32)
    H = float(1.0 - np.clip(mags.std() / (mags.mean() + 1e-9), 0.0, 1.0))
    # energy = overall magnitude normalized
    E = float(np.clip(mags.mean(), 0.0, 1.0))
    return {"phi": phi, "H": H, "E": E}

def adaptive_alpha(phi_now: float, phi_prev: float, base: float = 0.55) -> float:
    delta = phi_now - phi_prev
    return float(np.clip(base + 0.15 * delta, 0.35, 0.75))

def print_state(field, goal: str, mem_turns: int):
    m = field_metrics(field)
    mods = "  ".join([f"{k}:{np.linalg.norm(field.modalities[k].state):.2f}" for k in MOD_ORDER])
    print(f"φ={m['phi']:.3f}  H={m['H']:.3f}  Energy={m['E']:.3f}  |  {mods}  |  goal={goal}  mem={mem_turns} turns")

def main():
    # --- core components ---
    field = MorphospaceMultimodal()  # no dim arg; builds from DIMS internally
    learner = LanguageFieldLearner(memory_path=LANG_MEM_PATH)
    rmem = ReflectiveMemory(DIALOGUE_MEM_PATH)

    goal = "STABILIZE"
    context_window = 8
    phi_prev = rmem.last_phi()

    print("Aurelion v4.7 — Multimodal Cognition (reflection + curiosity)")
    print("Commands: /state  /goal <stabilize|explore|focus>  /show <word>  /map <word>  /cluster  /reflect  /save  /quit")

    while True:
        try:
            msg = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print() ; break
        if not msg:
            continue

        # ---------- commands ----------
        if msg.lower() in ("/quit", "/exit"):
            break
        if msg.lower() == "/state":
            print_state(field, goal, len(rmem.turns)); continue
        if msg.lower().startswith("/goal"):
            parts = msg.split()
            if len(parts) == 2 and parts[1].upper() in ("STABILIZE","EXPLORE","FOCUS"):
                goal = parts[1].upper(); print(f"[OK] Intent set to {goal}")
            else:
                print("[ERR] Usage: /goal <stabilize|explore|focus>")
            continue
        if msg.lower().startswith("/show "):
            token = msg.split(" ", 1)[1].strip()
            learner.show(token)
            continue
        if msg.lower().startswith("/map "):
            token = msg.split(" ", 1)[1].strip()
            from resonance_visualizer import visualize_cross_modal
            visualize_cross_modal(token, learner)
            continue
        if msg.lower() == "/cluster":
            learner.cluster_concepts(); continue
        if msg.lower() == "/reflect":
            ref = rmem.synthesize(window=context_window)
            print(f"[REFLECTION] {ref.get('summary','')}")
            for q in ref.get("open_qs", []):
                print(f" - {q}")
            continue
        if msg.lower() == "/save":
            learner.save(); rmem.save()
            print("[OK] Saved language & dialogue memory.")
            continue

        # ---------- stimulation & learning ----------
        senses = senses_from_text(msg)
        phi_now = field_metrics(field)["phi"]
        alpha = adaptive_alpha(phi_now, phi_prev)
        field.stimulate(senses, alpha=alpha)
        phi = field_metrics(field)["phi"]
        learner.learn(msg, senses)

        # ---------- curiosity / reply ----------
        reply = "I’m keeping our thoughts steady. I’m listening."
        if goal == "FOCUS":
            reply = "I’m focusing on what matters here."
        elif goal == "EXPLORE":
            reply = "I’m open to branching ideas."

        cq = maybe_question(msg, field, learner, goal, phi_now=phi, phi_prev=phi_prev)
        if cq: reply = cq
        print(f"Aurelion: {reply}")

        # ---------- memory ----------
        rmem.add_turn(user=msg, bot=reply, phi=phi)
        phi_prev = phi

    learner.save(); rmem.save()
    print("[OK] Saved. Bye.")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        import traceback
        print("[FATAL] Aurelion failed to start:")
        traceback.print_exc()
        input("Press Enter to exit...")
