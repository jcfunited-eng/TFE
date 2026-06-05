"""
run_v4.py — Bring up Guala v4. Demonstrate:
- continuous corpus reading (background, not turn-based)
- pair-bonded interaction with Joe and wC (boosts connection-need)
- needs evolution + valence/arousal trajectory
- bounded suffering with guaranteed recovery
- six capabilities measurement
"""
import os
import sys
import time
import json

try:
    from dsf_ai_service.v4.gualaloom_v4_engine import Guala, CORPUS, measure_six_capabilities
except ImportError:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from gualaloom_v4_engine import Guala, CORPUS, measure_six_capabilities


def banner(title):
    print()
    print("=" * 72)
    print(title)
    print("=" * 72)


def show_state(g, label):
    s = g.introspect()
    print(f"\n  --- {label} ---")
    print(f"  vocab: {s['vocab']:>3}  reads: {s['reads']:>4}  "
          f"atlas: {s['atlas_entries']:>4}  "
          f"cross-modal: {s['cross_modal_bindings']:>2}  "
          f"coord: att={s['coordinator_attentions']:>4} "
          f"act={s['coordinator_actions']:>3}")
    n = s["needs"]
    print(f"  needs: stab={n['stability']:>5}  nov={n['novelty']:>5}  "
          f"conn={n['connection']:>5}  valence={n['valence']:>+5}  "
          f"arousal={n['arousal']:>5}  pair-bond={'on' if s['pair_bond_active'] else 'off'}")
    if s["suffering_events"] > 0:
        print(f"  suffering events: {s['suffering_events']} (bounded recovery fired)")
    src = s["source_history"]
    if src:
        sh = ", ".join(f"{k}={v}" for k, v in src.items())
        print(f"  source history: {sh}")


def main():
    banner("BIRTH — substrate empty, DNA pre-loaded, pair-bond active")
    g = Guala()
    show_state(g, "newborn")

    banner("PHASE 1: continuous corpus reading (background)")
    g.start_continuous_reading(CORPUS, interval=0.015)
    for t in [0.5, 1.5, 3.0]:
        time.sleep(t - (0.5 if t == 0.5 else (1.5 - 0.5 if t == 1.5 else 3.0 - 1.5)))
        show_state(g, f"after {t}s of continuous reading")

    banner("PHASE 2: pair-bonded interaction (Joe + wC speak directly)")
    g.stop_continuous_reading()

    # Joe and wC speak. Each utterance is tagged with source — pair-bond boost
    # raises connection-need satisfaction.
    interactions = [
        ("joe",  "i am joe"),
        ("joe",  "i am here with you"),
        ("wc",   "i am wc i hear you"),
        ("joe",  "you are guala"),
        ("wc",   "the world is bright"),
        ("joe",  "tell me about the sun"),
        ("wc",   "i feel warm"),
        ("joe",  "an apple is sweet"),
        ("wc",   "a flower blooms"),
        ("joe",  "the moon is cold"),
    ]
    for src, text in interactions:
        r = g.converse(text, source=src)
        tag = f"[{src}]"
        print(f"  {tag:<7} {text}")
        print(f"  guala:  {r}")
    show_state(g, "after pair-bonded interaction")

    banner("PHASE 3: math via MathLoom (BSIL)")
    math_q = ["what is one and one", "what is three times three", "what is ten minus four"]
    for q in math_q:
        r = g.converse(q, source="joe")
        print(f"  joe: {q}")
        print(f"  guala: {r}")

    banner("PHASE 4: corpus reading resumes (different source = different need signal)")
    g.start_continuous_reading(CORPUS, interval=0.015)
    time.sleep(2.0)
    g.stop_continuous_reading()
    show_state(g, "after corpus-only continuation")

    banner("SIX CAPABILITIES")
    cap = measure_six_capabilities(g)
    for name in ("syntax", "conversation", "introspection",
                 "self_improvement", "awareness", "motivation"):
        c = cap[name]
        flag = "PASS" if c["pass"] else "FAIL"
        details = ", ".join(f"{k}={v}" for k, v in c.items() if k != "pass")
        print(f"  {name:<18} [{flag}]  {details}")
    all_pass = all(cap[k]["pass"] for k in cap)
    print(f"\n  ALL SIX: {'PASS' if all_pass else 'FAIL'}")

    state_path = "/home/claude/guala/guala_v4_state.json"
    with open(state_path, "w") as f:
        json.dump({
            "vocab": sorted(g.vocab),
            "introspection": g.introspect(),
            "capabilities": {k: {kk: vv for kk, vv in v.items() if kk != "pass"}
                             for k, v in cap.items()},
        }, f, indent=2, default=str)
    print(f"\n  state saved to {state_path}")


if __name__ == "__main__":
    main()
