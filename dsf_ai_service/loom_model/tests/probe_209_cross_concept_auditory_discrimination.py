"""probe_209_cross_concept_auditory_discrimination.py —
GL-CMD-CROSS-SENSE-RECALL-EVE-20260705-207/208, root-cause continuation
(GL-RPT-EVENT-COUNT-KRIMELACK-STATE-BUG-C1B-20260705-209).

ACCEPTANCE TEST for whatever replaces BindingAtlas's storage (currently
targeted at -207/GL-CMD-ORGANISM-WAVE-MEMORY's W1/W2). Run this against
the real Guala()/Embryo construction (observable="event_count", the
actual production default — see gualaloom_v5_engine.py:1644) after any
change to the binding/recall representation. It currently FAILS.

ROOT CAUSE (proven, isolated, no engine needed — see the math below):
grandurun's event_count encoding stores ONE RAW, UNBOUNDED SCALAR per
modality (a krimelack event count) in a shared 6-dim vector, matched via
plain cosine similarity (grandurun.recall_best). Cosine similarity
between a query vector with a SINGLE nonzero dimension and any stored
vector is mathematically BLIND to that dimension's magnitude — only
its direction (which axis is populated) affects the score. Two
concepts taught with wildly different auditory event-counts (bell=576,
cat=1381, ocean=1718 events, measured directly) are therefore
indistinguishable by a partial (single-modality) query: querying with
ANY positive auditory magnitude (50, 576, 1381, or 5000 — verified,
identical scores every time) always ranks the same concept highest,
determined only by which stored vector has the smallest *relative*
contribution from its OTHER (irrelevant, non-queried) dimensions — not
by whether the query resembles that concept at all.

This is NOT a krimelack-state-persistence bug (a snapshot/restore
fix around feed_signal() was tried and does not change these numbers —
CochlearBankKrimelack.feed_signal() is already a pure function of its
input; the +=len(events) accumulation pattern makes each feed's delta
history-independent by construction). It is a structural property of
"one scalar per modality, matched by whole-vector cosine" and needs a
representation change, not a state-management patch — see
GL-CMD-ORGANISM-WAVE-MEMORY-EVE-20260705-207 W1/W2.

Isolated proof (no engine, run directly, always reproduces):
    bell  = [0, 576,  0,0,0, 31]
    cat   = [0, 1381, 0,0,0, 24]
    ocean = [0, 1718, 0,0,0, 27]
    query = [0, <any positive value>, 0,0,0,0]
    -> cosine(query, ocean) > cosine(query, cat) > cosine(query, bell)
       for EVERY query magnitude tested (50, 576, 1381, 5000) -- ocean
       always wins because 27/1718 is a smaller relative "other
       dimension" contamination than 31/576, not because the query
       matched it.

GATE: run this file directly (`python3 probe_209_....py`) or via
pytest. It teaches 5 concepts, each with a distinctly-shaped real
auditory signal, then queries each concept's OWN signal (should
recall itself) plus one genuinely novel signal (should not
confidently claim any of the five). Prints per-query top-3 votes.
Passing this (>=80% own-signal recall) on whatever replaces the
current binding storage is the acceptance criterion for "cross-sense
recall works across more than one taught concept" -- a stronger bar
than -207/-208's own test_t7_cross_modal, which only ever taught ONE
concept-family (item_00..item_49, all via the SAME pipeline call in
one batch) and never exercised this specific multi-concept auditory
discrimination question.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

import numpy as np


def make_signal(freq, decay, amp=0.03, n=400, dt=0.04):
    t = np.arange(n) * dt
    return (amp * np.sin(2 * np.pi * freq * t) * np.exp(-t / decay)).tolist()


PAIRS = {
    'bell':  make_signal(3.0, 4.0),
    'cat':   make_signal(0.8, 8.0),
    'dog':   make_signal(1.6, 2.0),
    'ocean': make_signal(0.3, 12.0),
    'drum':  make_signal(5.0, 1.5),
}
NOVEL = make_signal(2.3, 6.0)


def run():
    from dsf_ai_service.v4.gualaloom_v5_engine import Guala, _organism_query_signal_auditory

    g = Guala()
    print(f"observable: {g.organism.brain.observable}")
    assert g.organism.brain.observable == "event_count", (
        "this probe targets production's real observable -- if this "
        "assertion fails, Guala.__init__ changed and the probe needs "
        "updating, not silently skipping"
    )

    # Bind-only (remember()), not experience_word() -- isolates the
    # recall/matching question from growth/fold population dynamics,
    # which is a separate concern (see -198).
    for name, sig in PAIRS.items():
        g.organism.remember(name, {"language": name, "auditory": sig})

    print()
    correct = 0
    for name, sig in PAIRS.items():
        votes = g.organism.recall(_organism_query_signal_auditory(sig))
        top3 = votes.most_common(3)
        got = top3[0][0] if top3 else None
        ok = got == name
        correct += ok
        print(f"  cue={name:6s} top3={top3}  {'OK' if ok else 'MISS'}")
    accuracy = correct / len(PAIRS) * 100
    print(f"\n  {correct}/{len(PAIRS)} correct ({accuracy:.0f}%)")

    novel_votes = g.organism.recall(_organism_query_signal_auditory(NOVEL))
    print(f"  novel (untaught) cue top3 = {novel_votes.most_common(3)}")

    return accuracy


def test_probe_209_cross_concept_auditory_discrimination():
    accuracy = run()
    assert accuracy >= 80.0, (
        f"cross-concept auditory discrimination should be >=80% (5 "
        f"distinct concepts, each queried with its own real teach-time "
        f"signal), got {accuracy:.0f}%. This is the acceptance gate "
        f"for -207/WAVE-MEMORY's binding-storage replacement -- see "
        f"this file's module docstring for the proven root cause if "
        f"this still fails."
    )


if __name__ == "__main__":
    run()
