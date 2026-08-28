"""INSPIRATION — what happens when ribbons touch.

Questions do not run alone. A ribbon laid across the sheets
ripples, and its ripples reach other ribbons. Where they touch,
things happen that neither question could produce by itself:

  OPENING        one ribbon's COLORED stretch meets another's
                 WHITE stretch — what this question can carry may
                 open what that one holds closed. This is the
                 shape of inspiration: an unrelated question's
                 answer opening your dead end.
  CROSSING       two colored stretches share ground — a
                 possibility neither question staged alone.
  SHARED WALL    two white stretches close on the same law — the
                 same wall reached from different directions,
                 which is what a deep law looks like from inside.
  COLORING       a bare ribbon — one carrying no answers — is
                 touched by another's colored stretch.

Nothing here is graded. The events are reported with both
ribbons named; an observer sees which have use.
"""
import os, sys
BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)
import fabric_ask as fa
import ribbon as R
import attach

def contacts(questions, depth=2, need=2):
    laid = {}
    for q in questions:
        try:
            prof, color, white = R.ribbon(q, depth=depth)
        except Exception:
            continue
        laid[q] = (fa.words(" ".join(color)),
                   fa.words(" ".join(white)), white)
    events = []
    qs = list(laid)
    for i, a in enumerate(qs):
        ca, wa, lawa = laid[a]
        for b in qs[i + 1:]:
            cb, wb, lawb = laid[b]
            if len(ca & wb) >= need:
                events.append(("OPENING", a, b,
                               sorted(ca & wb)[:5]))
            if len(cb & wa) >= need:
                events.append(("OPENING", b, a,
                               sorted(cb & wa)[:5]))
            if len(ca & cb) >= need + 1:
                events.append(("CROSSING", a, b,
                               sorted(ca & cb)[:5]))
            shared = set(lawa) & set(lawb)
            if shared:
                events.append(("SHARED WALL", a, b,
                               [list(shared)[0][:70]]))
            if not ca and cb:
                events.append(("COLORING", b, a,
                               sorted(cb)[:5]))
    return events

if __name__ == "__main__":
    qs = attach.questions()
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 6
    qs = qs[:n]
    print(f"laying {len(qs)} ribbons and letting them touch\n")
    for kind, a, b, ground in contacts(qs):
        if kind == "OPENING":
            print(f"OPENING — what \"{a[:52]}\" carries may open "
                  f"what \"{b[:52]}\" holds closed")
        elif kind == "CROSSING":
            print(f"CROSSING — \"{a[:52]}\" and \"{b[:52]}\" share "
                  f"standing ground neither staged alone")
        elif kind == "SHARED WALL":
            print(f"SHARED WALL — \"{a[:44]}\" and \"{b[:44]}\" "
                  f"close on the same law")
        else:
            print(f"COLORING — \"{a[:52]}\" carries color into the "
                  f"bare ribbon \"{b[:52]}\"")
        print(f"    where they touch: {' '.join(str(g) for g in ground)[:110]}")
