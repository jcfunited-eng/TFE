
# aurelion_core_v6_1_self_explaining.py
# v6.1 — Self-Explaining Meta-Monitor (coherence/entropy deltas + reasons)
# + v6.2 Emotional Cognition plugin integration (Option 2)

import json, os, sys, time
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import numpy as np

# --- Local modules (already in your repo) ---
from primitive_sensory_pack import DIMS
from morphospace_multimodal import MorphospaceMultimodal, senses_from_text
from language_field import LanguageFieldLearner
from resonance_visualizer import visualize_cross_modal

# --- Emotional Cognition plugin (Option 2) ---
_EMO_AVAILABLE = True
try:
    from emotion_layer import EmotionEngine
    from modules.state_manager import SystemToneTarget
except Exception as _e:
    _EMO_AVAILABLE = False

LANG_MEM = "language_memory.json"
DIALOGUE_MEM = "dialogue_memory.json"
ASSOC_MEM = "associations_v5.json"   # optional, if present we’ll surface schemas

MOD_ORDER = ["visual","auditory","smell","taste","touch","emotion","lexical"]

# ------------------------ metric helpers ------------------------

def _unit(v: np.ndarray) -> np.ndarray:
    n = np.linalg.norm(v) + 1e-9
    return v / n

def coherence(field: MorphospaceMultimodal) -> float:
    """Average pairwise cosine similarity across modalities."""
    vecs = [_unit(field.modalities[m].state) for m in MOD_ORDER]
    cs = []
    for i in range(len(vecs)):
        for j in range(i+1, len(vecs)):
            cs.append(float(np.dot(vecs[i], vecs[j])))
    return float(np.mean(cs)) if cs else 0.0

def entropy(field: MorphospaceMultimodal) -> float:
    """Shannon entropy of modality magnitudes normalized to 1."""
    mags = np.array([np.linalg.norm(field.modalities[m].state) for m in MOD_ORDER], dtype=np.float32)
    s = mags.sum()
    if s <= 1e-9: 
        return 0.0
    p = mags / s
    p = np.clip(p, 1e-9, 1.0)
    H = -float(np.sum(p * np.log(p)))
    # normalize by ln(K) so H in [0,1]
    return float(H / np.log(len(MOD_ORDER)))

def energy(field: MorphospaceMultimodal) -> float:
    """Simple bounded energy proxy."""
    mags = np.array([np.linalg.norm(field.modalities[m].state) for m in MOD_ORDER], dtype=np.float32)
    # squash to [0,1]
    return float(np.tanh(mags.mean()))

def modality_contributions(before: Dict[str,float], after: Dict[str,float]) -> List[Tuple[str,float]]:
    """Return modalities ranked by |Δnorm|."""
    deltas = []
    for m in MOD_ORDER:
        deltas.append((m, after[m] - before[m]))
    # sort by absolute change desc
    return sorted(deltas, key=lambda x: abs(x[1]), reverse=True)

def modality_norms(field: MorphospaceMultimodal) -> Dict[str,float]:
    return {m: float(np.linalg.norm(field.modalities[m].state)) for m in MOD_ORDER}

# ------------------------ meta voice ------------------------

def explain_turn(goal: str,
                 phi_prev: float, H_prev: float,
                 phi_now: float, H_now: float,
                 mods_before: Dict[str,float],
                 field: MorphospaceMultimodal) -> str:
    dphi = phi_now - phi_prev
    dH   = H_now  - H_prev
    trend_phi = "↑" if dphi >  1e-3 else ("↓" if dphi < -1e-3 else "→")
    trend_H   = "↑" if dH   >  1e-3 else ("↓" if dH   < -1e-3 else "→")

    mods_after = modality_norms(field)
    ranked = modality_contributions(mods_before, mods_after)[:3]
    top_txt = ", ".join([f"{m}({('+' if dv>=0 else '')}{dv:.2f})" for m,dv in ranked])

    # intent alignment
    if goal == "STABILIZE":
        reason = "stability"
        policy = "settle similar patterns"
        alignment = "aligned" if (dphi>=0 and dH<=0) else "probing"
    elif goal == "EXPLORE":
        reason = "diversification"
        policy = "seek novel contrasts"
        alignment = "aligned" if (dphi<=0 or dH>=0) else "cautious"
    else: # FOCUS
        reason = "focus"
        policy = "sharpen a dominant signal"
        alignment = "aligned" if (dphi>=0 and dH<=0) else "re-centering"

    return (f"(meta) φ{trend_phi} H{trend_H} — I chose **{reason}** to {policy}; "
            f"intent={goal}, {alignment}. Strongest shifts: {top_txt}.")

# ------------------------ IO helpers ------------------------

def safe_load_json(path: str, default):
    try:
        if Path(path).exists():
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return default

def safe_save_json(path: str, obj) -> bool:
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(obj, f, indent=2)
        return True
    except Exception:
        return False

# ------------------------ goal→tone helper ------------------------

def goal_to_tone(goal: str) -> Tuple[float,float,str]:
    """Map control goal to a default system tone target."""
    g = goal.upper()
    if g == "STABILIZE":
        return (0.25, 0.28, "supportive")
    if g == "EXPLORE":
        return (0.30, 0.40, "curious")
    # FOCUS
    return (0.20, 0.34, "attentive")

# ------------------------ main loop ------------------------

def main():
    print("Aurelion v6.1 — Self-Explaining Meta-Monitor  +  v6.2 Emotional Cognition (plugin)")
    print("Commands: /state  /goal <stabilize|explore|focus>  /emotion <on|off|status>  /show <word>  /map <word>  /schemas  /reflect  /save  /load  /quit")

    # field + learner
    field = MorphospaceMultimodal()                 # uses unified dims from primitive_sensory_pack
    learner = LanguageFieldLearner(memory_path=LANG_MEM)
    learner.load_memory()
    assoc = safe_load_json(ASSOC_MEM, {"nodes":{}, "edges":[]})
    dialogue = safe_load_json(DIALOGUE_MEM, [])

    goal = "STABILIZE"

    # Emotional layer
    emo = None
    emotion_enabled = False
    if _EMO_AVAILABLE:
        try:
            emo = EmotionEngine(config_path="config_emotion.json")
            emotion_enabled = True
            print("[EMOTION] plugin loaded (on)")
        except Exception as e:
            print(f"[EMOTION] failed to initialize: {e}")
            emotion_enabled = False
    else:
        print("[EMOTION] plugin not available — continuing without affect")

    # initial metrics
    phi_prev = coherence(field)
    H_prev   = entropy(field)
    E_prev   = energy(field)

    while True:
        try:
            msg = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n[exit]")
            break

        if not msg:
            continue

        # ---- commands ----
        low = msg.lower()
        if low in ["/quit", "/exit"]:
            break

        if low.startswith("/goal"):
            parts = msg.split()
            if len(parts)>=2:
                val = parts[1].strip().upper()
                if val in ["STABILIZE","EXPLORE","FOCUS"]:
                    goal = val
                    print(f"[OK] intent set to {goal}")
                else:
                    print("[ERR] goal must be stabilize|explore|focus")
            else:
                print(f"[INFO] current goal = {goal}")
            continue

        if low.startswith("/emotion"):
            parts = msg.split()
            if len(parts)==1 or parts[1].lower()=="status":
                state_txt = "on" if (emotion_enabled and emo is not None) else "off"
                if emo is not None:
                    v = getattr(emo.state, "valence", 0.0)
                    a = getattr(emo.state, "arousal", 0.25)
                    print(f"[EMOTION] {state_txt}  v={v:.2f} a={a:.2f}")
                else:
                    print(f"[EMOTION] {state_txt}")
            else:
                sub = parts[1].lower()
                if sub=="on":
                    if emo is None and _EMO_AVAILABLE:
                        try:
                            emo = EmotionEngine(config_path="config_emotion.json")
                        except Exception as e:
                            print(f"[EMOTION] failed to initialize: {e}")
                            emo = None
                    emotion_enabled = (emo is not None)
                    print("[EMOTION] on" if emotion_enabled else "[EMOTION] failed to turn on")
                elif sub=="off":
                    emotion_enabled = False
                    print("[EMOTION] off")
                else:
                    print("[EMOTION] usage: /emotion <on|off|status>")
            continue

        if low.startswith("/state"):
            phi_now = coherence(field); H_now = entropy(field); E_now = energy(field)
            norms = modality_norms(field)
            norm_text = "  ".join([f"{m}:{norms[m]:.2f}" for m in MOD_ORDER])
            print(f"φ={phi_now:.3f}  H={H_now:.3f}  E={E_now:.3f}  |  goal={goal}")
            print(" " + norm_text)
            if emotion_enabled and emo is not None:
                es = emo.state
                print(f" emotion: v={es.valence:.2f} a={es.arousal:.2f} tags={es.tags} conf={es.confidence:.2f}")
            continue

        if low.startswith("/show"):
            parts = msg.split(maxsplit=1)
            if len(parts)<2:
                print("[ERR] /show <word>")
                continue
            w = parts[1].strip().lower()
            sig = learner.memory.get(w)
            if not sig:
                print(f"[INFO] no memory for '{w}'")
            else:
                print(f"Concept: '{w}' — Learned Modal Signatures")
                for m in MOD_ORDER:
                    v = sig.get(m, [0.0]*DIMS[m])
                    v = np.array(v, dtype=np.float32)
                    samp = ", ".join([f"{x:.2f}" for x in v[:5]])
                    print(f"  {m:8s}: |v|={np.linalg.norm(v):.3f}  sample=[{samp}]")
            continue

        if low.startswith("/map"):
            parts = msg.split(maxsplit=1)
            if len(parts)<2:
                print("[ERR] /map <word>")
                continue
            w = parts[1].strip().lower()
            visualize_cross_modal(w, learner)
            continue

        if low.startswith("/schemas"):
            edges = assoc.get("edges", [])
            if not edges:
                print("(no schemas yet)")
            else:
                print("--- Learned edges (top 15) ---")
                for (a,b,w) in sorted(edges, key=lambda e: e[2], reverse=True)[:15]:
                    print(f"{a:16s} -> {b:16s}  {w:.3f}")
            continue

        if low.startswith("/reflect"):
            # simple keyword reflection from dialogue
            toks = []
            for turn in dialogue[-5:]:
                toks.extend(turn.get("user","").split()[:2])
            toks = [t.lower().strip(",.!?;:") for t in toks if t]
            toks = [t for t in toks if t]
            if toks:
                uniq = sorted(list(dict.fromkeys(toks)))
                print("[REFLECT] " + " • ".join(uniq))
                print(" - What should be clarified next?")
            else:
                print("[REFLECT] (no recent material)")
            continue

        if low.startswith("/save"):
            ok1 = learner.save_memory(LANG_MEM)
            ok2 = safe_save_json(DIALOGUE_MEM, dialogue)
            print(f"[OK] saved language={ok1} dialogue={ok2}")
            continue

        if low.startswith("/load"):
            learner.load_memory()
            dialogue[:] = safe_load_json(DIALOGUE_MEM, [])
            print("[OK] loaded memories")
            continue

        # ---- normal turn ----

        # record state before
        mods_before = modality_norms(field)

        # senses from text
        senses = senses_from_text(msg)
        # bias by goal
        alpha = 0.58
        if goal == "EXPLORE":
            alpha = 0.50
        elif goal == "FOCUS":
            alpha = 0.66

        # stimulate / learn / log dialogue
        field.stimulate(senses, alpha=alpha)
        learner.learn(msg, senses)
        dialogue.append({"user": msg, "goal": goal, "t": time.time()})

        # compute now
        phi_now = coherence(field)
        H_now   = entropy(field)
        E_now   = energy(field)

        # self-explanation
        meta = explain_turn(goal, phi_prev, H_prev, phi_now, H_now, mods_before, field)

        # Emotional layer (optional)
        emo_txt = ""
        if emotion_enabled and emo is not None:
            try:
                es = emo.update_from_text(msg)
                # pick tone target based on goal
                v_t, a_t, label_t = goal_to_tone(goal)
                system_target = SystemToneTarget(valence=v_t, arousal=a_t, label=label_t).to_tone()
                blended_tone = emo.blend_with_system_tone(system_target)
                emo_meta = emo.meta_summary(intent=goal, tone=blended_tone)
                emo_txt = f" (affect) {emo_meta['tone_label']} — {emo_meta['explain']}"
            except Exception as e:
                emo_txt = f" (affect) [error: {e}]"

        # lightweight response “style” based on goal
        if goal == "STABILIZE":
            lead = "(steady)"
        elif goal == "EXPLORE":
            lead = "(open)"
        else:
            lead = "(focus)"

        print(f"Aurelion: {lead} {meta}{emo_txt}")

        # roll metrics
        phi_prev, H_prev, E_prev = phi_now, H_now, E_now


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print("[FATAL] Aurelion failed to start:")
        import traceback; traceback.print_exc()
        input("Press Enter to exit...")
