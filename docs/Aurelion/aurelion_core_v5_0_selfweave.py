# aurelion_core_v5_0_selfweave.py
# v5.0 — Self-weaving cognition (temporal consolidation + schema formation)

from __future__ import annotations
import json, os, sys, time, re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np

# Existing modules from your v4.x setup
from primitive_sensory_pack import DIMS
from morphospace_multimodal import MorphospaceMultimodal, senses_from_text
from language_field import LanguageFieldLearner
from resonance_visualizer import visualize_cross_modal
# New v5 modules
from association_memory_v5 import AssociationMemoryV5
from selfweave import SelfWeave

LANG_MEM = "language_memory.json"
DIALOGUE_MEM = "dialogue_memory.json"
ASSOC_MEM = "associations_v5.json"

INTENTS = {"stabilize": "STABILIZE", "explore": "EXPLORE", "focus": "FOCUS"}

def tokens_from_text(s: str) -> List[str]:
    return re.findall(r"[A-Za-z']+", s.lower())

def pick_anchors(tokens: List[str], k: int = 2) -> List[str]:
    # simple heuristic: middle & last content words
    if not tokens: return []
    uniq = [t for t in tokens if len(t) > 2]
    if not uniq: uniq = tokens
    out = []
    if len(uniq) >= 1:
        out.append(uniq[-1])
    if len(uniq) >= 2:
        out.append(uniq[len(uniq)//2])
    return list(dict.fromkeys(out))[:k]

def safe_load_json(path: str, fallback):
    try:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return fallback

def save_json(path: str, obj) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)

def cosine(a: np.ndarray, b: np.ndarray) -> float:
    na = float(np.linalg.norm(a) + 1e-9)
    nb = float(np.linalg.norm(b) + 1e-9)
    return float(np.dot(a, b) / (na * nb))

def field_metrics(field: MorphospaceMultimodal) -> Tuple[float, float, float]:
    # φ = mean cross-modal cosine; H = 1 - var; E = norm of pooled state
    vecs = [m.state for m in field.modalities.values()]
    coss = []
    for i in range(len(vecs)):
        for j in range(i + 1, len(vecs)):
            coss.append(cosine(vecs[i], vecs[j]))
    phi = float(np.mean(coss)) if coss else 0.0
    H = float(1.0 - np.var(np.stack(vecs))) if vecs else 0.0
    E = float(np.linalg.norm(np.mean(np.stack(vecs), axis=0))) if vecs else 0.0
    return phi, H, E

def print_state(field, goal: str, mem_turns: int, schemas: str) -> None:
    phi, H, E = field_metrics(field)
    # quick gauge for each modality
    parts = []
    for name, m in field.modalities.items():
        parts.append(f"{name}:{np.linalg.norm(m.state):.2f}")
    parts_s = "  ".join(parts)
    print(f"φ={phi:.3f}  H={H:.3f}  Energy={E:.3f}  |  {parts_s}  |  goal={goal}  mem={mem_turns} turns")
    if schemas.strip():
        print("--- Schemas ---")
        print(schemas)

def main() -> None:
    print("Aurelion v5.0 — Self-Weaving Cognition (schemas + consolidation)")
    print("Commands: /state  /goal <stabilize|explore|focus>  /show <word>  /map <word>  /assoc <word>")
    print("          /schemas  /save  /load  /cluster  /quit")

    # field + learner
    field = MorphospaceMultimodal()
    learner = LanguageFieldLearner(memory_path=LANG_MEM)

    # dialogue
    dialogue_memory: List[Dict[str, str]] = safe_load_json(DIALOGUE_MEM, [])
    if not isinstance(dialogue_memory, list):
        dialogue_memory = []
    print(f"[INFO] Loaded {len(dialogue_memory)} prior dialogue turns.")

    # associations + selfweave
    if os.path.exists(ASSOC_MEM):
        try:
            assoc = AssociationMemoryV5.load(ASSOC_MEM)
            print("[INFO] Loaded prior associations.")
        except Exception:
            assoc = AssociationMemoryV5()
            print("[WARN] Could not load prior associations; starting fresh.")
    else:
        assoc = AssociationMemoryV5()
        print("[INFO] No prior associations; starting fresh.")
    weave = SelfWeave(assoc)

    goal = "STABILIZE"
    turns_since_consolidate = 0

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
                print_state(field, goal, len(dialogue_memory), weave.schema_report())

            elif cmd == "/goal" and len(parts) > 1:
                g = parts[1].lower()
                goal = INTENTS.get(g, goal)
                print(f"[OK] Intent set to {goal}")

            elif cmd == "/show" and len(parts) > 1:
                word = parts[1].lower()
                # quick dump of modal signatures if present
                mem = learner.memory.get("lexical", {})
                vec = mem.get(word)
                if vec is None:
                    print(f"[INFO] No memory for '{word}'.")
                else:
                    # preview first few dims
                    pv = ", ".join([f"{float(x):.2f}" for x in vec[:5]])
                    print(f"{word}: |v|={np.linalg.norm(vec):.3f}  sample=[{pv}]")
                    # neighbors from associations
                    nbrs = assoc.top_neighbors(word, k=8)
                    if nbrs:
                        ns = ", ".join([f"{k}:{v:.2f}" for k, v in nbrs])
                        print(f"assoc → {ns}")
                    else:
                        print("assoc → (none)")

            elif cmd == "/map" and len(parts) > 1:
                word = parts[1].lower()
                try:
                    from resonance_visualizer import visualize_cross_modal
                    visualize_cross_modal(word, learner)
                except Exception as e:
                    print(f"[ERR] /map failed: {e}")

            elif cmd == "/assoc" and len(parts) > 1:
                word = parts[1].lower()
                nbrs = assoc.top_neighbors(word, k=10)
                if not nbrs:
                    print("(no associations)")
                else:
                    for k, v in nbrs:
                        print(f"{word} — {k}: {v:.3f}")

            elif cmd == "/schemas":
                print(weave.schema_report())

            elif cmd == "/save":
                try:
                    learner.save(LANG_MEM)
                except Exception:
                    pass
                try:
                    assoc.save(ASSOC_MEM)
                except Exception:
                    pass
                save_json(DIALOGUE_MEM, dialogue_memory)
                print(f"[OK] Saved → {LANG_MEM}, {ASSOC_MEM}, {DIALOGUE_MEM}")

            elif cmd == "/load":
                try:
                    learner2 = LanguageFieldLearner(memory_path=LANG_MEM)
                    learner = learner2
                    print("[OK] Reloaded language memory.")
                except Exception as e:
                    print(f"[WARN] Could not reload language memory: {e}")
                try:
                    assoc2 = AssociationMemoryV5.load(ASSOC_MEM)
                    assoc = assoc2
                    weave = SelfWeave(assoc)  # rebind
                    print("[OK] Reloaded associations.")
                except Exception as e:
                    print(f"[WARN] Could not reload associations: {e}")
                dialogue_memory = safe_load_json(DIALOGUE_MEM, [])
                print(f"[OK] Reloaded dialogue ({len(dialogue_memory)} turns).")

            elif cmd == "/cluster":
                # reuse your earlier concept clustering if present
                try:
                    from resonance_visualizer import cluster_concepts
                    cluster_concepts(learner)
                except Exception as e:
                    print(f"[ERR] /cluster failed: {e}")

            else:
                print("[ERR] Unknown command.")
            continue

        # -------- normal conversational turn --------
        # sensing + stimulation
        senses = senses_from_text(msg)
        field.stimulate(senses, alpha=0.55)

        # learn lexical & cross-modal
        learner.learn(msg, senses)

        # associations + weaving
        toks = tokens_from_text(msg)
        anchors = pick_anchors(toks, k=2)
        assoc.add_cooccurrence_ring(toks, lr=0.02)
        for a in anchors:
            assoc.add_links(a, toks, lr=0.06)

        turns_since_consolidate += 1
        if turns_since_consolidate >= 3:
            weave.consolidate()
            turns_since_consolidate = 0

        # proto-reply (keeps personality minimal and safe)
        print(f"Aurelion: ({goal.lower()}) I’m tracking “{', '.join(anchors)}”. "
              f"{'Schemas ready.' if weave.schemas else 'Weaving…'}")

        # memory the dialogue turn
        dialogue_memory.append({"user": msg, "goal": goal})

    # on exit, autosave
    try:
        learner.save(LANG_MEM)
    except Exception:
        pass
    try:
        assoc.save(ASSOC_MEM)
    except Exception:
        pass
    save_json(DIALOGUE_MEM, dialogue_memory)
    print("[OK] Session saved.")
    
if __name__ == "__main__":
    main()
