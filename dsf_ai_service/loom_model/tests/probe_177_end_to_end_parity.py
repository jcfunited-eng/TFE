"""probe_177_end_to_end_parity.py — GL-CMD-RECALL-SPEED-INVESTIGATION-EVE-20260704-177.

End-to-end proof, on the REAL Embryo/organism construction (same as
production): Brain.recall_fast() returns the IDENTICAL Counter as
Brain.recall() (via Embryo.recall()), across many probe words and multiple
teaching depths -- including past language's 256-event deque saturation
(the regime the live organism has actually been in this whole time).

Then the two safety invariants Eve's dispatch names explicitly:
  INV-1 read-only:           recall_fast(x) == recall_fast(x), back-to-back
  INV-2 teaching-sensitive:  recall_fast(x) -> remember(y) -> recall_fast(x)
                             changes for at least some x, y pair (not frozen)
"""
import sys
sys.path.insert(0, '/workspaces/Tao_Financial_Engine')

from dsf_ai_service.loom_model.embryo import Embryo
from dsf_ai_service.v4.gualaloom_v5_engine import _organism_signal
from dsf_ai_service.substrate.sensory_transducer import SensoryTransducer, NullAtlasReader

WORDS = ("the cat sat on the mat and looked at the little dog who was "
         "running fast across the green grass near the old wooden fence "
         "while a warm bright sun shone down on them both today happy "
         "sunshine wonderful extraordinarily beautiful morning guala "
         "mommy daddy friend water fire tree flower bird star").split()


def build():
    emb = Embryo(brain_seed=42, seed_size=8, observable="event_count")
    transducer = SensoryTransducer(NullAtlasReader())
    return emb, transducer


def counters_equal(c1, c2):
    return dict(c1) == dict(c2)


def test_parity_at_depths():
    print("=== end-to-end Counter parity: recall_fast() vs recall() ===")
    emb, transducer = build()
    fails = 0
    checkpoints = [0, 5, 20, 50, 120, 250]  # 250 taught words pushes language
                                              # well past the 256-slot deque,
                                              # i.e. into the saturated regime
    taught = 0
    for cp in checkpoints:
        while taught < cp:
            w = WORDS[taught % len(WORDS)]
            emb.remember(w, _organism_signal(w, transducer))
            taught += 1
        mismatches_here = 0
        for w in WORDS[:15]:
            sig = _organism_signal(w, transducer)
            ref = emb.brain.recall(sig)
            fast = emb.brain.recall_fast(sig)
            if not counters_equal(ref, fast):
                mismatches_here += 1
                print(f"  MISMATCH words_taught={taught} query={w!r}")
                print(f"    ref : {dict(ref)}")
                print(f"    fast: {dict(fast)}")
        fails += mismatches_here
        print(f"  words_taught={taught:4d}: {15 - mismatches_here}/15 queries match"
              f"{'  <-- saturated regime' if taught >= 260 else ''}")
    print(f"  {'ALL PASS' if fails == 0 else f'{fails} MISMATCHES'}")
    return fails == 0


def test_inv1_read_only():
    print("=== INV-1: read-only (identical back-to-back queries) ===")
    emb, transducer = build()
    for w in WORDS[:30]:
        emb.remember(w, _organism_signal(w, transducer))
    fails = 0
    for w in WORDS[:15]:
        sig = _organism_signal(w, transducer)
        v1 = emb.brain.recall_fast(sig)
        v2 = emb.brain.recall_fast(sig)
        if not counters_equal(v1, v2):
            fails += 1
            print(f"  MISMATCH (non-read-only!) query={w!r}: {dict(v1)} != {dict(v2)}")
    print(f"  {'ALL PASS' if fails == 0 else f'{fails} FAILURES'}")
    return fails == 0


def test_inv2_teaching_sensitive():
    print("=== INV-2: teaching-sensitive (query -> teach -> same query changes) ===")
    # GL-CMD-LANGUAGE-SATURATION-ROOTCAUSE-EVE-20260704-178: now that
    # language's n_events-based delta is a strong, word-deterministic
    # signal (not silently zero), it's LESS sensitive to unrelated
    # teaching than the old len(events)-frozen behavior was (expected --
    # a real, understood property, not a bug, see -178/-179 reports).
    # A single (probe_word, teach_word) pair can land on 0/N changed by
    # chance at this sample size (confirmed: this exact test showed 0/10
    # with teach_word="extraordinarily" alone, but 3/30 varying the teach
    # word). Broadened to more probes + rotating teach words so the check
    # isn't a coin-flip on one specific pair.
    emb, transducer = build()
    for w in WORDS[:30]:
        emb.remember(w, _organism_signal(w, transducer))

    teach_words = ["extraordinarily", "wonderful", "beautiful", "sunshine"]
    changed = 0
    checked = 0
    for i, probe_word in enumerate(WORDS[:30]):
        sig = _organism_signal(probe_word, transducer)
        before = emb.brain.recall_fast(sig)
        teach_word = teach_words[i % len(teach_words)]
        if teach_word == probe_word:
            teach_word = teach_words[(i + 1) % len(teach_words)]
        emb.remember(teach_word, _organism_signal(teach_word, transducer))
        after = emb.brain.recall_fast(sig)
        checked += 1
        if not counters_equal(before, after):
            changed += 1
    print(f"  {changed}/{checked} probe queries changed after one real teach event")
    ok = changed > 0
    print(f"  {'PASS (not frozen/stale)' if ok else 'FAIL -- looks memoized/stale!'}")
    return ok


if __name__ == "__main__":
    ok1 = test_parity_at_depths()
    ok2 = test_inv1_read_only()
    ok3 = test_inv2_teaching_sensitive()
    print()
    print("OVERALL:", "ALL PASS" if (ok1 and ok2 and ok3) else "FAILURES PRESENT -- DO NOT SHIP")
