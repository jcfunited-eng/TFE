# aurelion_core_v4_9_associative.py
# v4.9 — Multimodal Cognition with Deep Reflective Associations (fixed init)

from __future__ import annotations
import json, os, re, sys, time
from typing import Dict, List, Optional, Tuple
import numpy as np

from primitive_sensory_pack import DIMS
from morphospace_multimodal import MorphospaceMultimodal, senses_from_text
from language_field import LanguageFieldLearner
from resonance_visualizer import visualize_cross_modal
from association_memory import AssociationMemory

LANG_MEM = "language_memory.json"
DIALOGUE_MEM = "dialogue_memory.json"
ASSOC_MEM = "association_memory.json"

MOD_ORDER = ["visual", "auditory", "smell", "taste", "touch", "emotion", "lexical"]

# ---------- Utilities ----------

def tokenize(s: str) -> List[str]:
    return [w.lower() for w in re.findall(r"[a-zA-Z]+", s)]

def pad_or_trim(vec: np.ndarray, dim: int) -> np.ndarray:
    v = np.asarray(vec, dtype=np.float32).flatten()
    if v.shape[0] == dim:
        return v
    if v.shape[0] > dim:
        return v[:dim]
    out = np.zeros(dim, dtype=np.float32)
    out[: v.shape[0]] = v
    return out

def cosine(a: np.ndarray, b: np.ndarray) -> float:
    na, nb = float(np.linalg.norm(a)), float(np.linalg.norm(b))
    if na == 0.0 or nb == 0.0:
        return 0.0
    return float(np.dot(a, b) / (na * nb))

def field_metrics(field: MorphospaceMultimodal) -> Tuple[float, float, float]:
    vecs = [field.modalities[m].state for m in MOD_ORDER]
    vecs = [pad_or_trim(v, DIMS["visual"]) for v in vecs]
    cs = []
    for i in range(len(vecs)):
        for j in range(i + 1, len(vecs)):
            cs.append(cosine(vecs[i], vecs[j]))
    phi = float(np.clip(np.mean(cs) if cs else 0.0, 0.0, 1.0))
    norms = np.array([np.linalg.norm(v) for v in vecs], dtype=np.float32)
    var = float(np.var(norms)) if norms.size else 0.0
    H = float(np.clip(1.0 - var / (1.0 + var), 0.0, 1.0))
    E = float(np.clip(np.mean(norms) / (1.0 + np.mean(norms)), 0.0, 1.0)) if norms.size else 0.0
    return phi, H, E

def format_status(phi: float, H: float, E: float, goal: str, mem_turns: int, assoc: AssociationMemory) -> str:
    nodes, edges = assoc.stats()
    return (f"φ={phi:.3f}  H={H:.3f}  Energy={E:.3f}  |  goal={goal.upper()}  "
            f"mem={mem_turns} turns  assoc: {nodes} nodes / {edges} edges")

# ---------- Reply generator ----------

INTENT_TONE = {
    "stabilize": "I’m keeping our thoughts steady.",
    "explore":   "I’m open to branching ideas.",
    "focus":     "I’m narrowing to essentials.",
}

def generate_reply(user_msg: str, tokens: List[str], assoc: AssociationMemory,
                   anchor: Optional[str], intent: str) -> str:
    tone = INTENT_TONE.get(intent, INTENT_TONE["stabilize"])
    chosen = None
    for t in reversed(tokens):
        if assoc.neighbors(t, topn=1):
            chosen = t
            break
    if not chosen:
        chosen = anchor or (tokens[-1] if tokens else "")
    additions = []
    if chosen:
        nbrs = [n for n, _ in assoc.neighbors(chosen, topn=3)]
        if nbrs:
            additions.append(f"I’m linking “{chosen}” with " + ", ".join(nbrs) + ".")
    prompt = f"What matters most about “{chosen}” here?" if chosen else ""
    return " ".join([tone] + additions + ([prompt] if prompt else [])).strip()

# ---------- Main ----------

def main() -> None:
    print("Aurelion v4.9 — Multimodal Cognition (deep reflective associations)")
    print("Commands: /state  /goal <stabilize|explore|focus>  /show <word>  /map <word>  /assoc <word>  /cluster  /save  /quit")

    field = MorphospaceMultimodal()   # ← fixed
    learner = LanguageFieldLearner(LANG_MEM)
    assoc = AssociationMemory(ASSOC_MEM)

    dialogue: List[Dict[str, str]] = []
    if os.path.exists(DIALOGUE_MEM):
        try:
            with open(DIALOGUE_MEM, "r", encoding="utf-8") as f:
                obj = json.load(f)
            if isinstance(obj, list):
                dialogue = obj[-200:]
        except Exception:
            dialogue = []
    print(f"[INFO] Loaded {len(dialogue)} prior dialogue turns. Associations: {assoc.stats()[0]} nodes / {assoc.stats()[1]} edges.")

    goal = "stabilize"
    anchor_token: Optional[str] = None

    while True:
        try:
            msg = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not msg:
            continue

        # Commands
        if msg.startswith("/"):
            parts = msg.split()
            cmd = parts[0].lower()
            if cmd == "/quit":
                break
            elif cmd == "/state":
                phi, H, E = field_metrics(field)
                print(format_status(phi, H, E, goal, len(dialogue), assoc))
            elif cmd == "/goal" and len(parts) >= 2:
                g = parts[1].lower()
                if g in INTENT_TONE:
                    goal = g
                    print(f"[OK] Intent set to {goal.upper()}")
                else:
                    print("[ERR] goal must be one of: stabilize | explore | focus")
            elif cmd == "/show" and len(parts) >= 2:
                tok = parts[1].lower()
                vecs = learner.recall(tok)
                print(f"Concept: '{tok}' — Learned Modal Signatures")
                for m in MOD_ORDER:
                    v = vecs.get(m, np.zeros(DIMS["visual"], dtype=np.float32))
                    samp = ", ".join([f"{float(x):.2f}" for x in v[:5]])
                    print(f"  {m:<8}: |v|={np.linalg.norm(v):.3f}  sample=[{samp}]")
            elif cmd == "/map" and len(parts) >= 2:
                try:
                    visualize_cross_modal(parts[1].lower(), learner)
                except Exception as e:
                    print(f"[WARN] map failed: {e}")
            elif cmd == "/assoc" and len(parts) >= 2:
                print("\n".join(assoc.explain(parts[1].lower(), topn=10)))
            elif cmd == "/cluster":
                hubs, seen = [], set()
                for t in list(assoc.graph.keys()):
                    if t in seen:
                        continue
                    nbrs = [n for n, _ in assoc.neighbors(t, topn=6)]
                    group = [t] + [n for n in nbrs if n not in seen]
                    for g in group: seen.add(g)
                    hubs.append(group)
                print("\n=== Resonance Association Hubs ===")
                if not hubs:
                    print("[none yet — talk a bit more]")
                else:
                    for i, g in enumerate(hubs):
                        print(f"Hub {i:02d}: " + ", ".join(g))
            elif cmd == "/save":
                with open(DIALOGUE_MEM, "w", encoding="utf-8") as f:
                    json.dump(dialogue, f, ensure_ascii=False, indent=2)
                learner.save(LANG_MEM)
                assoc.save(ASSOC_MEM)
                print("[OK] Saved dialogue, language memory, and associations.")
            else:
                print("[ERR] Unknown command.")
            continue

        # Normal message
        senses = senses_from_text(msg)
        field.stimulate(senses, alpha=0.58)

        toks = tokenize(msg)
        senses_by_token = {}
        for t in toks:
            mem = learner.recall(t)
            if all(float(np.linalg.norm(mem.get(m, np.zeros(8)))) == 0.0 for m in MOD_ORDER):
                mem = {m: senses[m].copy() for m in MOD_ORDER}
            for m in MOD_ORDER:
                mem[m] = pad_or_trim(mem.get(m, np.zeros(8)), 8)
            senses_by_token[t] = mem

        learner.learn(msg, senses)
        assoc.update_from_tokens(toks, senses_by_token)

        phi, H, E = field_metrics(field)
        anchor_token = next((t for t in reversed(toks) if len(t) > 2), None)
        reply = generate_reply(msg, toks, assoc, anchor_token, goal)
        print(f"Aurelion: {reply}")

        dialogue.append({"user": msg, "bot": reply})

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print("[FATAL] Aurelion failed to start:")
        import traceback; traceback.print_exc()
        input("Press Enter to exit...")
