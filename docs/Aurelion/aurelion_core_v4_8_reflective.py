# aurelion_core_v4_8_reflective.py (fixed)
# v4.8 — Multimodal Cognition (adaptive reflection + growing voice, safe memory validation)

import json, os, sys, time
from pathlib import Path
from typing import Dict, List, Optional
import numpy as np

from primitive_sensory_pack import DIMS
from morphospace_multimodal import MorphospaceMultimodal, senses_from_text
from language_field import LanguageFieldLearner
from resonance_visualizer import visualize_cross_modal
from proto_responder import generate_reply_v48
from reflection_memory import ReflectionState

LANG_MEM = "language_memory.json"
DIALOGUE_MEM = "dialogue_memory.json"
REFLECT_MEM = "reflection_memory.json"


def jload(path: Path, default):
    try:
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data
    except Exception:
        pass
    return default


def jdump(path: Path, obj):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)


def adaptive_alpha(phi_now: float, phi_prev: float, base: float = 0.55) -> float:
    delta = float(phi_now - phi_prev)
    return float(np.clip(base - 0.15 * np.sign(delta), 0.35, 0.75))


def cosine(a: np.ndarray, b: np.ndarray) -> float:
    na = float(np.linalg.norm(a) + 1e-8)
    nb = float(np.linalg.norm(b) + 1e-8)
    return float(np.dot(a, b) / (na * nb))


def field_metrics(field: MorphospaceMultimodal) -> Dict[str, float]:
    names = list(DIMS.keys())
    vecs = []
    for name in names:
        vecs.append(field.modalities[name].state.astype(np.float32))
    vecs = np.stack(vecs, axis=0)
    M = vecs.shape[0]
    cos_vals = []
    for i in range(M):
        for j in range(i + 1, M):
            cos_vals.append(cosine(vecs[i], vecs[j]))
    phi = float(np.mean(cos_vals)) if cos_vals else 0.0
    norms = np.linalg.norm(vecs, axis=1)
    H = float(1.0 - np.clip(np.var(norms), 0.0, 1.0))
    E = float(np.mean(norms))
    return {"phi": phi, "H": H, "E": E}


def main():
    field = MorphospaceMultimodal()
    learner = LanguageFieldLearner(memory_path=LANG_MEM)
    reflect = ReflectionState.load(Path(REFLECT_MEM))

    # ---------- dialogue memory validation ----------
    raw_dialogue = jload(Path(DIALOGUE_MEM), [])
    if not isinstance(raw_dialogue, list):
        print("[WARN] dialogue_memory.json malformed — resetting.")
        dialogue_memory: List[Dict[str, str]] = []
    else:
        dialogue_memory = raw_dialogue

    # safe last user lookup
    last_user: Optional[str] = None
    if isinstance(dialogue_memory, list) and dialogue_memory:
        last_entry = dialogue_memory[-1]
        if isinstance(last_entry, dict) and "user" in last_entry:
            last_user = last_entry["user"]

    goal = "STABILIZE"
    context_window: List[str] = []

    print("Aurelion v4.8 — Multimodal Cognition (adaptive reflection + growing voice)")
    print("Commands: /state  /goal <stabilize|explore|focus>  /show <word>  /map <word>  /cluster  /reflect  /save  /quit")
    print(f"[INFO] Dialogue memory loaded: {len(dialogue_memory)} turns  |  Reflection tokens: {len(reflect.counts)}")

    prev_phi = 0.5

    while True:
        try:
            msg = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not msg:
            continue

        if msg.startswith("/"):
            parts = msg.split()
            cmd = parts[0].lower()

            if cmd == "/quit":
                break

            elif cmd == "/state":
                m = field_metrics(field)
                print(f"φ={m['phi']:.3f}  H={m['H']:.3f}  Energy={m['E']:.3f}  |  goal={goal}  mem={len(dialogue_memory)} turns")

            elif cmd == "/goal" and len(parts) >= 2:
                g = parts[1].strip().upper()
                if g in ("STABILIZE", "EXPLORE", "FOCUS"):
                    goal = g
                    print(f"[OK] Intent set to {goal}")
                else:
                    print("[ERR] goal must be stabilize|explore|focus")

            elif cmd == "/show" and len(parts) >= 2:
                word = parts[1].strip().lower()
                vecs = learner.recall(word)
                if vecs is None:
                    print(f"[INFO] '{word}' not found in memory.")
                else:
                    print(f"Concept: '{word}' — Learned Modal Signatures")
                    for name, v in vecs.items():
                        mag = float(np.linalg.norm(v))
                        sample = np.array(v, dtype=np.float32)[:5]
                        sample_str = ", ".join([f"{x:.2f}" for x in sample])
                        print(f"  {name:<7}: |v|={mag:.3f}  sample=[{sample_str}]")

            elif cmd == "/map" and len(parts) >= 2:
                visualize_cross_modal(parts[1].strip().lower(), learner)

            elif cmd == "/cluster":
                names = learner.learned_tokens()
                if not names:
                    print("[INFO] No learned tokens yet.")
                else:
                    print("\n=== Resonance Neighborhoods (lexical only) ===")
                    L = []
                    for w in names[:128]:
                        vecs = learner.recall(w)
                        if vecs and "lexical" in vecs:
                            L.append((w, vecs["lexical"]))
                    if len(L) < 2:
                        print("[INFO] Not enough items.")
                    else:
                        words, mat = zip(*L)
                        mat = np.stack(mat, axis=0)
                        sims = (mat @ mat.T)
                        norms = np.linalg.norm(mat, axis=1, keepdims=True) + 1e-8
                        sims = sims / (norms @ norms.T)
                        for i, w in enumerate(words[:20]):
                            idx = np.argsort(-sims[i])[:5]
                            neigh = [words[j] for j in idx]
                            print(f"{w:<12} → {', '.join(neigh)}")

            elif cmd == "/reflect":
                top = reflect.top_tokens(10)
                if not top:
                    print("[REFLECTION] (empty) — talk to me and I’ll start forming anchors.")
                else:
                    print("[REFLECTION]", " • ".join([t for t, _ in top]))
                    qs = reflect.make_prompts()
                    for q in qs:
                        print(" -", q)

            elif cmd == "/save":
                learner.save()
                jdump(Path(DIALOGUE_MEM), dialogue_memory)
                reflect.save(Path(REFLECT_MEM))
                print(f"[OK] Saved -> {LANG_MEM}, {DIALOGUE_MEM}, {REFLECT_MEM}")

            else:
                print("[ERR] Unknown command.")
            continue

        # ---- normal message ----
        senses = senses_from_text(msg)
        field.stimulate(senses, alpha=0.55)
        metrics = field_metrics(field)
        prev_phi = metrics["phi"]

        learner.learn(msg, senses)
        reflect.observe(msg, senses)

        context_window.append(msg)
        context_window = context_window[-6:]

        reply = generate_reply_v48(
            msg=msg,
            senses=senses,
            learner=learner,
            intent=goal,
            last_user=last_user,
            context_window=context_window,
            reflection=reflect
        )

        print(f"Aurelion: {reply}")
        dialogue_memory.append({"user": msg, "aurelion": reply, "phi": metrics["phi"], "H": metrics["H"], "E": metrics["E"]})
        last_user = msg

    learner.save()
    jdump(Path(DIALOGUE_MEM), dialogue_memory)
    reflect.save(Path(REFLECT_MEM))
    print("[OK] Session saved. Bye.")


if __name__ == "__main__":
    main()
