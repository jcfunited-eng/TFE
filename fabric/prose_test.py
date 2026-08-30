"""THE DOING IN REAL WRITING — forty sentences, hand-labelled.

Every doing-label the fabric had was on sentences I wrote. This is
the fabric's own prose with the doing named by hand, drawn by a seed
used once. The corpus pool is largely burned — 400-sentence samples
have been drawn from it six times and looked at — so this set is
LOCKED: it is measured against, never tuned on. If a change is made
because of what this bench showed, it stops being a test.

None = the sentence says what a thing is and has no doing.
"""
import os, sys, re, random
BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)
import core, wanting

DOING = {
    2: "moves", 5: "stand", 7: "has", 8: "holds", 9: "justifies",
    10: "made", 11: "comes", 14: "fixed", 15: "sets", 18: "predict",
    19: "defeat", 20: "removes", 26: "needs", 27: "cracks",
    31: "says", 32: "read", 33: "pushes", 35: "buy", 38: "say",
    39: "written",
}


def cases(F=None):
    F = F or core.fabric()
    sents = []
    for e in F.entries:
        for q in re.split(r"[.;]", e["essence"]):
            w = q.strip()
            if 5 <= len(w.split()) <= 10 and w[:1].isalpha():
                sents.append(w)
    random.seed(555)
    return [(s, DOING.get(i + 1))
            for i, s in enumerate(random.sample(sents, 40))]


def same(a, b):
    a, b = core.stem((a or "").lower()), core.stem((b or "").lower())
    if not a or not b:
        return False
    return a.startswith(b) or b.startswith(a)


def grade(F=None):
    F = F or core.fabric()
    rows, good = [], 0
    for s, want in cases(F):
        got = wanting.want(s, F).get("turns_on")
        ok = (same(got, want) if want else got is None)
        good += ok
        rows.append((s, got, want, ok))
    return rows, good


if __name__ == "__main__":
    rows, good = grade()
    for s, got, want, ok in rows:
        if not ok:
            print(f"  FAIL  {s[:52]:<52} got {got}, want {want}")
    print(f"\n  DOING IN REAL WRITING: {good}/40"
          f"   (saying IS every time scores 20)")
