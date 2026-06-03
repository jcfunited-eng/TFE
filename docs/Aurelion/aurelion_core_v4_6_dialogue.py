# aurelion_core_v4_6_dialogue.py
# v4.6 — Multimodal cognition with adaptive plasticity + proto dialogue
# Corrected: sends sensory dict to generate_reply() instead of raw text

import traceback

try:
    import json, os, sys, time
    from pathlib import Path
    import numpy as np

    # === Core Aurelion Modules ===
    from primitive_sensory_pack import DIMS
    from morphospace_multimodal import MorphospaceMultimodal, senses_from_text, MOD_ORDER
    from language_field import LanguageFieldLearner
    from resonance_visualizer import visualize_cross_modal
    from proto_responder import generate_reply

    LANG_MEM = "language_memory.json"
    DIALOGUE_MEM = "dialogue_memory.json"

    # ---------------------------------------------------------
    # Helper functions
    # ---------------------------------------------------------

    def adaptive_alpha(phi_now: float, phi_prev: float, base: float = 0.55) -> float:
        """Adaptive weighting for field plasticity."""
        delta = phi_now - phi_prev
        return max(0.1, min(0.9, base + delta * 0.5))

    def field_metrics(field):
        """Compute coherence, entropy, and energy across modalities."""
        vecs = []
        for name in DIMS.keys():
            v = getattr(field, name, None)
            if v is None or not hasattr(v, "state"):
                continue
            vecs.append(v.state)
        if len(vecs) < 2:
            return 0.0, 0.0, 0.0
        cos_vals = []
        for i in range(len(vecs)):
            for j in range(i + 1, len(vecs)):
                a, b = vecs[i], vecs[j]
                na, nb = np.linalg.norm(a), np.linalg.norm(b)
                if na == 0 or nb == 0:
                    continue
                cos_vals.append(float(np.dot(a, b) / (na * nb)))
        phi = float(np.mean(cos_vals)) if cos_vals else 0.0
        H = float(np.std(cos_vals))
        E = float(np.mean([np.linalg.norm(v) for v in vecs]))
        return phi, H, E

    def safe_load_json(path):
        """Load JSON safely and return empty list if invalid."""
        if not os.path.exists(path):
            return []
        try:
            data = json.load(open(path, "r"))
            if isinstance(data, list):
                return [d for d in data if isinstance(d, dict) and "user" in d]
            return []
        except Exception:
            print("[WARN] Failed to parse dialogue memory; starting clean.")
            return []

    # ---------------------------------------------------------
    # Main Aurelion Dialogue Core
    # ---------------------------------------------------------

    def main():
        print("Aurelion v4.6 — Multimodal Cognition (adaptive + proto dialogue)")
        print("Commands: /state  /goal <stabilize|explore|focus>  /show <word>  /map <word>  /cluster  /quit")

        field = MorphospaceMultimodal()
        learner = LanguageFieldLearner(memory_path=LANG_MEM)
        phi_prev = 0.5
        goal = "STABILIZE"
        dialogue_memory = safe_load_json(DIALOGUE_MEM)
        print(f"[INFO] Loaded {len(dialogue_memory)} prior dialogue turns (validated).")

        while True:
            msg = input("You: ").strip()
            if not msg:
                continue

            # ---- Commands ----
            if msg.lower() in ("/quit", "quit", "exit"):
                print("[OK] Exiting and saving memories...")
                with open(DIALOGUE_MEM, "w") as f:
                    json.dump(dialogue_memory, f, indent=2)
                learner.save(LANG_MEM)
                break

            if msg.lower() == "/state":
                phi, H, E = field_metrics(field)
                print(f"φ={phi:.3f}  H={H:.3f}  Energy={E:.3f}  |  goal={goal}  mem={len(dialogue_memory)} turns")
                continue

            if msg.lower().startswith("/goal"):
                parts = msg.split()
                if len(parts) > 1:
                    goal = parts[1].upper()
                    print(f"[OK] Intent set to {goal}")
                else:
                    print("[ERR] Usage: /goal <stabilize|explore|focus>")
                continue

            if msg.lower().startswith("/show"):
                parts = msg.split()
                if len(parts) > 1:
                    visualize_cross_modal(parts[1], learner)
                else:
                    print("[ERR] Usage: /show <word>")
                continue

            if msg.lower().startswith("/cluster"):
                learner.cluster_concepts()
                continue

            # ---- Sensory Stimulus ----
            senses = senses_from_text(msg)
            phi_now, _, _ = field_metrics(field)
            alpha = adaptive_alpha(phi_now, phi_prev)
            field.stimulate(senses, alpha=alpha)
            phi_prev = phi_now

            # ---- Learning & Dialogue ----
            learner.learn(msg, senses)

            last_user = dialogue_memory[-1]["user"] if dialogue_memory else None
            context_window = [turn.get("user", "") for turn in dialogue_memory[-5:]]
            # *** Key Fix: pass senses dict to generate_reply() ***
            reply = generate_reply(senses, learner, goal, last_user, context_window)

            dialogue_memory.append({"user": msg, "reply": reply})
            print(f"Aurelion: {reply}")

    if __name__ == "__main__":
        main()

except Exception as e:
    print("[FATAL] Aurelion failed to start:")
    traceback.print_exc()
    input("Press Enter to exit...")
