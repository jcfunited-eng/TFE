"""WHAT WOULD OPEN THIS — the road back from impossible.

An impossibility is never free-standing: it stands on a reason.
Resolve the reason and the want opens, while the law itself
stays exactly as true as it was. Man still cannot fly; he rides
a thing that does. That is the honest shape of every opening.

Three roads, searched in the knowledge itself:

  ANOTHER BEARER  the requirement stands, but something else can
                  satisfy it (a heart stops; hands pump instead)
  REMOVE THE
  BLOCKER         the forbidding condition is itself removable
                  (the airway is blocked; clear it and breathing
                  returns — the law never bent)
  NOT A LAW       the closure rests on custom or craft habit, not
                  on physics — those dissolve when tested (paint
                  needed a brush until it did not)
"""
import os, sys
BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)
import fabric_ask as fa
import maker

HARD = ("physic", "chemistr", "mathematic", "premise", "quantum",
        "thermodynam", "conservation", "counting")

def _hard(e):
    r = (e.get("root") or "").lower()
    return any(h in r for h in HARD)

DOERS = ("eat", "eats", "feed", "take", "takes", "carry",
         "carries", "pull", "pulls", "push", "pushes", "hold",
         "holds", "trade", "trades", "spend", "spends", "move",
         "moves", "hire", "pay", "pays", "steal", "steals",
         "burn", "burns", "drink", "drinks", "store", "stores")

def invent(need, blocked, kind, es=None, home=None, count=3):
    """Keep the law; get stupid about who satisfies it.

    The machine never grades these. It orders them by distance
    from the job — nearest last, strangest first — and shows each
    one's parentage. The observer sees what has use.

    Borrow the SHAPE of a doer from a far-off part of the
    knowledge and hand it the job the law demands. That is how
    ice mites that eat heat are built: fermentation's shape (tiny
    living things eat one thing and pay in another) given the job
    of carrying heat away. The law never moves. Every invention
    must differ in kind from the others — the finger rule."""
    ws = sorted(need if kind == "requires" else blocked)
    if not ws: return []
    job = " ".join(ws[:6])
    if es is None:
        return [f"something not in my knowledge that supplies "
                f"[{job}] — imagined, not found."]
    # the stupid is the point: prefer the FARTHEST shapes, the
    # ones sharing least with the job, not the safe neighbours
    jobw = set(need if kind == "requires" else blocked)
    cands = []
    for e in es:
        low = e["essence"].lower()
        if not any(f" {d} " in low for d in DOERS): continue
        if home and set(e["field"].split()) & set(home.split()):
            continue
        cands.append((len(jobw & fa.words(e["essence"])), e))
    cands.sort(key=lambda x: x[0])
    out, used = [], set()
    for _d, e in cands:
        fld = e["field"]
        used.add(fld)
        shape = e["essence"].split("—")[0].strip()[:70]
        out.append(f"borrow the shape of ({fld}): {shape} — and "
                   f"give it the job of supplying [{job}]. "
                   f"Imagined, not found; the law is untouched.")
        if len(out) >= count: break
    return out

def openings(law_text, kind, need, blocked, es, show=2):
    """What, in the knowledge, could open this closure."""
    out = []
    def ew(e): return fa.words(e["essence"])
    if kind == "requires":
        bearers = [e for e in es if need and len(need & ew(e)) >= 2]
        bearers.sort(key=lambda e: -len(need & ew(e)))
        for e in bearers[:show]:
            out.append(("another bearer", e))
    else:
        removers = [e for e in es
                    if blocked and len(blocked & ew(e)) >= 2
                    and e["cannot"]]
        removers.sort(key=lambda e: -len(blocked & ew(e)))
        for e in removers[:show]:
            out.append(("remove the blocker", e))
    return out

def why_closed(want, show=3):
    txt, closed, req, forb, es, _n = maker.make(want, data=True)
    lines = [txt, "",
             "WHAT WOULD OPEN THIS — an impossibility stands on a "
             "reason; resolve the reason and the want opens while "
             "the law stays exactly as true as it was."]
    ranked = sorted(closed.items(),
                    key=lambda x: (-int(x[1][1]), -x[1][0]))[:show]
    for c, (n, near) in ranked:
        kind = "requires" if "requirement unmet" in c else "forbids"
        law = c.rsplit("(", 1)[0]
        law = law.replace("requirement unmet —", "").replace(
            "forbidden together —", "").strip()
        parent = None; need = set(); blocked = set()
        for a, b, e, t in (req if kind == "requires" else forb):
            if t.strip().lower() in law.lower() or \
               law.lower() in t.strip().lower():
                parent, need, blocked = e, b, b
                break
        lines.append(f"  CLOSED BY: {law}")
        if parent is not None and not _hard(parent):
            lines.append("    this closure rests on custom or "
                         "craft, not on physics — those dissolve "
                         "when tested. Paint needed a brush until "
                         "it did not.")
        found = openings(law, kind, need, blocked, es)
        for how, e in found:
            lines.append(f"    {how}: ({e['field']}) "
                         f"{e['essence'][:95]}")
        if not found:
            for inv in invent(need, blocked, kind, es,
                              home=(parent or {}).get("field")):
                lines.append(f"    invented bearer: {inv}")
        if parent is not None and _hard(parent):
            lines.append("    the law itself does not bend: what "
                         "changes is who satisfies it.")
    return "\n".join(lines)

if __name__ == "__main__":
    print(why_closed(" ".join(sys.argv[1:])))
