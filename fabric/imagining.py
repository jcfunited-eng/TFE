"""IMAGINING v1 — un-aimed proposal, verification after.

The minting law demands proposals from the machine's own
materials, before any hand states an expectation. Two springs:

A. JOIN PROPOSALS — every cross-field meeting in the whole corpus
   where one floor's essence presses on another floor's CANNOT,
   kept only if no single floor already states the meeting.
   Ranked by rarity. I do not choose which pairs exist.

B. WALK PROPOSALS — the machine composes digit-family spaces from
   its own column-count law (families it can build: multiples of
   each bundle 2..9 by their ones-digits, odds, evens, the
   square-ending digits) and walks EVERY one for reachability.
   Every receipt is reported. None is cherry-picked before the
   run.

DISCLOSURE, permanent: the two springs are hands — a grammar is
an aim at one remove. The individual finds are not aimed. Each
find's worth is a DEGREE of utility to each observer, graded
after the run, never before, and "already held by every observer
present" is a lawful grade.
"""
import os, sys, re
BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)
import fabric_ask as fa
import fabric_do as fd

def spring_joins(top=8):
    es = fa.load()
    def w(t): return fa.words(t)
    df = {}
    for e in es:
        for x in w(e["essence"] + " " + e["cannot"]):
            df[x] = df.get(x, 0) + 1
    out = []
    for B in es:
        for A in es:
            if B is A or B["field"] == A["field"]: continue
            hinge = w(B["essence"]) & w(A["cannot"])
            hinge = {h for h in hinge if df.get(h, 99) <= 12}
            if len(hinge) < 2: continue
            both = w(B["essence"]) | w(A["cannot"])
            if any(len(both & w(e["essence"] + " " + e["cannot"]))
                   >= 0.8 * len(both) for e in es):
                continue        # already stated in one floor
            rar = sum(1.0 / df[h] for h in hinge)
            out.append((rar, sorted(hinge), B, A))
    out.sort(key=lambda x: -x[0])
    lines = ["SPRING A — cross-field meetings no single floor "
             "states (machine-proposed, unranked by any aim):"]
    for rar, hinge, B, A in out[:top]:
        lines.append(f"  [{B['field']}] {B['essence'][:70]}")
        lines.append(f"    presses on [{A['field']}] CANNOT: "
                     f"{A['cannot'][:70]}")
        lines.append(f"    hinge: {' '.join(hinge[:5])}")
    return "\n".join(lines)

def spring_walks():
    fams = {}
    for b in range(2, 10):
        fams[f"piles of {b}s"] = sorted({(b * k) % 10
                                         for k in range(1, 11)})
    fams["odd piles"] = [1, 3, 5, 7, 9]
    fams["even piles"] = [0, 2, 4, 6, 8]
    fams["square-ending piles"] = [0, 1, 4, 5, 6, 9]
    lines = ["SPRING B — every family the machine can compose from "
             "its column-count law, walked without exception:"]
    for name, D in sorted(fams.items()):
        r = fd.walk(
            [("a", D), ("b", D), ("ones", list(range(10))),
             ("carry", [0, 1])],
            [("column-count (from: mathematics/bundles)", "expr",
              "a + b == ones + 10*carry")])
        reach = sorted(set(s["ones"] for s in r["survivors"]))
        miss = [d for d in range(10) if d not in reach]
        if miss:
            lines.append(f"  {name} (ones-digits {D}): two members "
                         f"can NEVER sum to a ones-digit of "
                         f"{miss} — closed room, "
                         f"{sum(r['kills'].values())} killed.")
        else:
            lines.append(f"  {name} (ones-digits {D}): two members "
                         f"reach EVERY ones-digit — open room.")
    return "\n".join(lines)

if __name__ == "__main__":
    print(spring_joins())
    print()
    print(spring_walks())
