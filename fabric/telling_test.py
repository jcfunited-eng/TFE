"""BEING TOLD WHAT TO DO — the acceptance test for the first ribbon.

The point of the ribbon is that the fabric can be TOLD what to build.
Everything else measured so far is sentences ABOUT things — the
fabric's own writing, or sentences I constructed. An instruction is a
different shape and it is the shape that matters: it has no doer, the
doing comes first, and what follows is what to do it to, with
constraints hung off it.

WANTS is the doing being asked for. ABOUT is what must be named.
FORBIDS is what may not be used.

These are MINE and they are instructions a person would actually give.
That is the point: this is the bench for the goal, not for a metric.
"""
import os, sys
BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)
import core, wanting

# instruction, wants, must-be-about, must-forbid
TELLING = [
    ("make a shelter that stays warm without fuel",
     "make", ["shelter", "warm"], ["fuel"]),
    ("keep food cold without electricity",
     "keep", ["food", "cold"], ["electricity"]),
    ("build me a bridge from rope",
     "build", ["bridge", "rope"], []),
    ("find a way to carry water uphill",
     "find", ["water", "uphill"], []),
    ("explain why bread rises",
     "explain", ["bread"], []),
    ("cool a room without a fan",
     "cool", ["room"], ["fan"]),
    ("carry water across a valley",
     "carry", ["water", "valley"], []),
    ("store grain through a wet winter",
     "store", ["grain", "winter"], []),
    ("light a fire without matches",
     "light", ["fire"], ["matches"]),
    ("clean water without boiling it",
     "clean", ["water"], ["boiling"]),
    ("move a heavy stone up a slope",
     "move", ["stone", "slope"], []),
    ("dry clothes indoors without heat",
     "dry", ["clothes"], ["heat"]),
    ("measure a field with a rope",
     "measure", ["field", "rope"], []),
    ("stop a wound bleeding",
     "stop", ["wound"], []),
    ("teach a child to count",
     "teach", ["child", "count"], []),
]


def same(a, b):
    a, b = core.stem((a or "").lower()), core.stem((b or "").lower())
    if not a or not b:
        return False
    return a.startswith(b) or b.startswith(a)


def grade(F=None):
    F = F or core.fabric()
    rows, good = [], 0
    for sent, wants, about, forbid in TELLING:
        w = wanting.want(sent, F)
        got = w.get("turns_on")
        ab = w.get("about") or []
        fb = w.get("forbidden") or []
        ok_w = same(got, wants)
        miss = [a for a in about if not any(same(a, g) for g in ab)]
        ok_f = all(any(same(f, g) for g in fb) for f in forbid)
        ok = ok_w and not miss and ok_f
        good += ok
        why = []
        if not ok_w:
            why.append(f"wants '{got}', should be '{wants}'")
        if miss:
            why.append("not about " + ",".join(miss))
        if not ok_f:
            why.append("forbidden not read")
        rows.append((sent, ok, "; ".join(why)))
    return rows, good


if __name__ == "__main__":
    rows, good = grade()
    for sent, ok, why in rows:
        print(f"  {'ok  ' if ok else 'FAIL'}  {sent:<48} {why}")
    print(f"\n  TOLD WHAT TO DO: {good}/{len(TELLING)}")
