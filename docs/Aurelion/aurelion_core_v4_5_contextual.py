# Aurelion v4.5 — Contextual Flow & Dialogue Memory
# (console chat with working memory + contextual bias)
#
# Requirements (already in your project from earlier steps):
# - morphospace_multimodal.py  (provides MorphospaceMultimodal, senses_from_text, MOD_ORDER)
# - primitive_sensory_pack.py  (provides DIMS, zeros, clamp01)
# - language_field.py          (updated below)
# - working_memory.py          (new, included below)
#
# Run:
#   python aurelion_core_v4_5_contextual.py
#
# Commands in chat:
#   /state                          -> show φ, H, Energy + memory size
#   /goal <stabilize|explore|focus> -> set intent
#   /show <word>                    -> print learned modal signatures
#   /map <word>                     -> print cross-modal resonance matrix
#   /cluster                        -> cluster learned concepts
#   /save                           -> save language + dialogue memory
#   /load                           -> load language + dialogue memory
#   /reset                          -> clear morphospace state (not memories)
#   /quit                           -> exit

import os, sys, json, math, time
from typing import Dict, Any

import numpy as np

try:
    from morphospace_multimodal import MorphospaceMultimodal, senses_from_text, MOD_ORDER
except Exception as e:
    print("[ERROR] morphospace_multimodal import failed:", e)
    sys.exit(1)

try:
    from primitive_sensory_pack import zeros, DIMS
except Exception as e:
    print("[ERROR] primitive_sensory_pack import failed:", e)
    sys.exit(1)

try:
    from language_field import LanguageFieldLearner
except Exception as e:
    print("[ERROR] language_field import failed:", e)
    sys.exit(1)

try:
    from working_memory import WorkingMemory
except Exception as e:
    print("[ERROR] working_memory import failed:", e)
    sys.exit(1)


# -------- helpers --------

def cosine(a: np.ndarray, b: np.ndarray) -> float:
    a = np.asarray(a).astype(np.float32)
    b = np.asarray(b).astype(np.float32)
    na = float(np.linalg.norm(a) + 1e-9)
    nb = float(np.linalg.norm(b) + 1e-9)
    return float(np.dot(a, b) / (na * nb))

def clamp01(x: float) -> float:
    return max(0.0, min(1.0, float(x)))

# Compute coherence (φ), entropy (H), and energy (E) for the field
def field_metrics(field: MorphospaceMultimodal) -> Dict[str, float]:
    # Gather current modality state vectors in canonical order
    vecs = []
    for name in MOD_ORDER:
        v = field.modalities[name].state
        vecs.append(v.astype(np.float32))

    # φ = mean pairwise cosine across modalities
    cos_vals = []
    for i in range(len(vecs)):
        for j in range(i + 1, len(vecs)):
            cos_vals.append(cosine(vecs[i], vecs[j]))
    phi = float(np.mean(cos_vals)) if cos_vals else 0.0
    phi = clamp01((phi + 1.0) / 2.0)  # map [-1,1] -> [0,1]

    # H = normalized entropy of modality magnitudes (how balanced are modalities)
    mags = np.array([np.linalg.norm(v) + 1e-9 for v in vecs], dtype=np.float32)
    p = mags / np.sum(mags)
    H = float(-np.sum(p * np.log(p + 1e-9)) / np.log(len(vecs)))  # 0..1

    # E = simple energy proxy = mean magnitude normalized by dimension
    norms = []
    for name, v in zip(MOD_ORDER, vecs):
        d = float(DIMS[name])
        norms.append(float(np.linalg.norm(v) / math.sqrt(d)))
    E = float(np.mean(norms))
    E = clamp01(E)

    return {"phi": phi, "H": H, "E": E}


# -------- main chat loop --------

SAVE_LANG = "language_memory.json"
SAVE_DIALOG = "dialogue_memory.json"

INTENTS = {"stabilize": "STABILIZE", "explore": "EXPLORE", "focus": "FOCUS"}

def print_state(field: MorphospaceMultimodal, wm: WorkingMemory, intent: str):
    m = field_metrics(field)
    # Per-mod modality strengths (normalized)
    strengths = []
    for name in MOD_ORDER:
        v = field.modalities[name].state
        strengths.append((name, clamp01(np.linalg.norm(v) / max(1.0, math.sqrt(DIMS[name])))))
    mod_str = "  ".join(f"{n}:{s:.2f}" for n, s in strengths)
    print(f"φ={m['phi']:.3f}  H={m['H']:.3f}  Energy={m['E']:.3f}  |  {mod_str}  |  intent={intent}  mem={wm.size()} turns")

def main():
    field = MorphospaceMultimodal()
    learner = LanguageFieldLearner(memory_path=SAVE_LANG)
    wm = WorkingMemory(memory_path=SAVE_DIALOG, max_turns=200)

    # announce loaded tokens/turns
    try:
        n = learner.vocab_size()
        print(f"[INFO] Loaded {n} learned tokens from {SAVE_LANG}")
    except Exception:
        print("[INFO] No prior language memory found; starting fresh.")

    try:
        t = wm.size()
        if t > 0:
            print(f"[INFO] Loaded {t} dialogue turns from {SAVE_DIALOG}")
        else:
            print("[INFO] No prior dialogue memory found; starting fresh.")
    except Exception:
        print("[INFO] No prior dialogue memory found; starting fresh.")

    print("Aurelion v4.5 — Multimodal Cognition (contextual flow + dialogue memory)")
    print("Commands: /state  /reset  /goal <stabilize|explore|focus>  /show <word>  /map <word>  /cluster  /save  /load  /quit")

    intent = "STABILIZE"  # default intent

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
                print_state(field, wm, intent)

            elif cmd == "/reset":
                field.reset()
                print("[OK] Field state reset.")

            elif cmd == "/goal":
                if len(parts) >= 2 and parts[1].lower() in INTENTS:
                    intent = INTENTS[parts[1].lower()]
                    print(f"[OK] Intent set to {intent}")
                else:
                    print("[ERR] Use /goal <stabilize|explore|focus>")

            elif cmd == "/show":
                if len(parts) < 2:
                    print("[ERR] Use /show <word>")
                else:
                    learner.pretty_show(parts[1].strip().lower())

            elif cmd == "/map":
                if len(parts) < 2:
                    print("[ERR] Use /map <word>")
                else:
                    learner.pretty_resonance_map(parts[1].strip().lower())

            elif cmd == "/cluster":
                learner.pretty_cluster()

            elif cmd == "/save":
                learner.save()
                wm.save()
                print(f"[OK] Saved language memory -> {SAVE_LANG} and dialogue memory -> {SAVE_DIALOG}")

            elif cmd == "/load":
                # Reload both memories
                learner.load()
                wm.load()
                print(f"[OK] Reloaded memories from disk.")

            else:
                print("[ERR] Unknown command.")
            continue

        # ---------- normal conversational turn ----------
        # 1) parse senses from text
        senses = senses_from_text(msg)

        # 2) recall: from long-term language memory (conceptual) and recent dialogue (context)
        #    a) learner recall gives per-modality vectors for words present
        learned = learner.recall(msg)  # dict(mod -> vec)
        #    b) dialogue memory returns decayed context bias per modality
        ctx_bias = wm.recall_bias(decay=0.88)

        # 3) intent-based blending weights
        #    STABILIZE = rely more on context + learned, less on new senses
        #    EXPLORE   = rely more on incoming senses
        #    FOCUS     = boost lexical + emotion coupling
        if intent == "STABILIZE":
            w_sense, w_learn, w_ctx = 0.35, 0.40, 0.25
        elif intent == "EXPLORE":
            w_sense, w_learn, w_ctx = 0.60, 0.25, 0.15
        else:  # FOCUS
            w_sense, w_learn, w_ctx = 0.40, 0.40, 0.20

        # 4) compose final stimulation vectors
        composed = {}
        for name in MOD_ORDER:
            v_s = senses.get(name, zeros(name))
            v_l = learned.get(name, zeros(name))
            v_c = ctx_bias.get(name, zeros(name))
            v = (w_sense * v_s) + (w_learn * v_l) + (w_ctx * v_c)
            # FOCUS tweak: slight cross-coupling lexical<->emotion
            if intent == "FOCUS":
                if name == "lexical":
                    v = v + 0.10 * learned.get("emotion", zeros("emotion"))[:v.shape[0]]
                if name == "emotion":
                    v = v + 0.10 * learned.get("lexical", zeros("lexical"))[:v.shape[0]]
            composed[name] = v.astype(np.float32)

        # 5) stimulate the field
        field.stimulate(composed, alpha=0.60)

        # 6) measure and print status
        m = field_metrics(field)
        mod_str = "  ".join(f"{n}:{clamp01(np.linalg.norm(field.modalities[n].state)/max(1.0, math.sqrt(DIMS[n]))):.2f}" for n in MOD_ORDER)
        print(f"φ={m['phi']:.3f}  H={m['H']:.3f}  Energy={m['E']:.3f}  |  {mod_str}")

        # 7) learn & store context
        learner.learn(msg, senses, context_tag="dialogue")
        wm.push_turn(text=msg, senses=senses, phi=m["phi"], H=m["H"], E=m["E"])

    # graceful exit: save memories
    try:
        learner.save()
        wm.save()
        print(f"[OK] Memories saved -> {SAVE_LANG}, {SAVE_DIALOG}")
    except Exception as e:
        print("[WARN] Could not save on exit:", e)


if __name__ == "__main__":
    main()
