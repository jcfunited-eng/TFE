"""Tries to ASSEMBLE answers to the open questions from pieces
scattered across the knowledge — pieces placed for other reasons,
never for these questions. Chains are anchored to the question,
must cross subjects, and must share uncommon ground. Output is
whatever comes out; most attempts are expected to fail and say so.
"""
import sys, os
BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)
import fabric_ask as fa

def run(question, es, df):
    qs = fa.words(question)
    def w(e):
        return fa.words(e["essence"] + " " + e["cannot"] + " "
                        + e["ask"])
    def rare(s): return {x for x in s if df.get(x, 99) <= 10}
    touched = [e for e in es if len(qs & w(e)) >= 1]
    # the pieces of a real situation know each other: keep only
    # touched entries that share uncommon ground with another
    # touched entry. Isolated word-matches fall away.
    anchored = [e for e in touched
                if any(len(rare(w(e)) & rare(w(o))) >= 1
                       for o in touched if o is not e)]
    if not anchored: anchored = []
    out = []
    for e1 in anchored:
        for e2 in es:
            if e2 is e1: continue
            if set(e1["field"].split()) & set(e2["field"].split()):
                continue
            g = rare(w(e1)) & rare(w(e2))
            if len(g) < 2: continue
            cover = len(qs & (w(e1) | w(e2)))
            if cover < 2: continue
            out.append((cover * 2 + len(g), e1, e2, sorted(g)[:4]))
    out.sort(key=lambda x: -x[0])
    seen, top = set(), []
    for s, e1, e2, g in out:
        k = frozenset((id(e1), id(e2)))
        if k in seen: continue
        seen.add(k); top.append((s, e1, e2, g))
        if len(top) == 2: break
    return top

if __name__ == "__main__":
    es = fa.load()
    df = {}
    for e in es:
        for x in fa.words(e["essence"] + " " + e["cannot"] + " "
                          + e["ask"]):
            df[x] = df.get(x, 0) + 1
    QS = ["why do we cry emotional tears",
          "why does a kite need a tail",
          "why do onions make you cry",
          "why does the moon look bigger near the horizon",
          "where is denver"]
    for q in QS:
        print(f"QUESTION: {q}")
        top = run(q, es, df)
        if not top:
            print("  nothing assembles — no scattered pieces "
                  "touch this question. The missing knowledge is "
                  "the whole answer.\n")
            continue
        for s, e1, e2, g in top:
            print(f"  maybe (score {s}): ({e1['field']}) "
                  f"{e1['essence'][:90]}")
            print(f"     with ({e2['field']}) {e2['essence'][:90]}")
            print(f"     shared uncommon ground: {' '.join(g)}")
        print()

def play(question, es, df):
    """A question asks possibility. Split the touched knowledge
    into territories (one word can live in several), and inside
    each: what is known, what is known to fail, and unproven play
    — combinations nothing known forbids, labeled as play."""
    qs = fa.words(question)
    def w(e):
        return fa.words(e["essence"] + " " + e["cannot"] + " "
                        + e["ask"])
    def rare(s): return {x for x in s if df.get(x, 99) <= 10}
    qkey = {x for x in qs if df.get(x, 99) <= 15} or qs
    touched = [e for e in es if len(qkey & w(e)) >= 1]
    houses = []
    for e in touched:
        for h in houses:
            if any(len(rare(w(e)) & rare(w(o))) >= 1 for o in h):
                h.append(e); break
        else:
            houses.append([e])
    def hcover(h): return len(qkey & set().union(*[w(e) for e in h]))
    houses.sort(key=lambda h: (-hcover(h), -len(h)))
    out = []
    for h in houses[:3]:
        terr = list(h)
        for e in es:
            if e in terr: continue
            if any(len(rare(w(e)) & rare(w(m))) >= 2 for m in h):
                terr.append(e)
        def qc(e): return len(qkey & w(e)) * 3 + len(qs & w(e))
        known = sorted(terr, key=lambda e: -qc(e))[:2]
        failed = sorted([e for e in terr if e["cannot"]],
                        key=lambda e: -qc(e))[:1]
        toys = []
        for i2, a in enumerate(terr):
            for b in terr[i2 + 1:]:
                g = rare(w(a)) & rare(w(b))
                if not g: continue
                cov = len(qs & (w(a) | w(b)))
                if cov < 1: continue
                toys.append((cov * 2 + len(g), a, b))
        toys.sort(key=lambda x: -x[0])
        out.append((known, failed, toys[:1]))
    return out
