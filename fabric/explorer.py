"""EXPLORING BOTH FRONTIERS — where discoveries come from.

The knowledge holds two kinds of law, read from the entries' own
words:  A requires B  and  A cannot stand with B.

They chain, and chaining produces statements nobody wrote:

  POSSIBLE FRONTIER   A requires B, B requires C
                      -> to have A you must also have C
  IMPOSSIBLE FRONTIER A requires B, B cannot stand with C
                      -> A and C can never stand together

Anything already stated by an existing law is dropped, so what
remains is unwritten. Nothing here judges worth: each finding is
recorded with both parents named, for a reader to grade by its
usefulness to them.
"""
import os, sys
BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)
import fabric_ask as fa
import maker

REC = os.path.join(BASE, "life", "frontier_findings.md")

def _known(concl, req, forb, kind):
    """Is this conclusion already written down somewhere?"""
    a, b = concl
    pool = req if kind == "requires" else forb
    for x, y, e, txt in pool:
        if a <= x and (b <= y or y <= b): return True
        if kind == "forbids" and b <= x and a <= y: return True
    return False

def _link_ok(link, e1, e2):
    """Does the joining word carry the same sense in both laws?
    Same sense makes a tight derivation. A different sense makes
    an echo across domains — metaphor, which is how vocabulary
    grows. Neither is discarded and neither is graded here."""
    try:
        import senses as S
    except Exception:
        return True
    c1 = fa.words(e1["essence"] + " " + e1["cannot"])
    c2 = fa.words(e2["essence"] + " " + e2["cannot"])
    for w in link:
        if len(w) < 4: continue
        if not S.same_sense(w, c1, c2): return False
    return True

def explore(limit=6):
    es = fa.load()
    req, forb = maker.constraints(es)
    poss, imposs, echoes = [], [], []
    for a1, b1, e1, t1 in req:
        for a2, b2, e2, t2 in req:
            if e2 is e1: continue
            if a2 <= b1 and not (b2 <= b1) and not (b2 & a1):
                if _known((a1, b2), req, forb, "requires"): continue
                tight = _link_ok(a2, e1, e2)
                (poss if tight else echoes).append(
                    (a1, b2, e1, t1, e2, t2))
        for a2, b2, e2, t2 in forb:
            if e2 is e1: continue
            if a2 <= b1 and not (b2 & a1) and not (b2 & b1):
                if _known((a1, b2), req, forb, "forbids"): continue
                tight = _link_ok(a2, e1, e2)
                (imposs if tight else echoes).append(
                    (a1, b2, e1, t1, e2, t2))
    def say(ws): return " ".join(sorted(ws))
    lines = []
    lines.append("THE POSSIBLE FRONTIER — requirements nobody "
                 "wrote, chained from two that were written:")
    for a, c, e1, t1, e2, t2 in poss[:limit]:
        lines.append(f"  to have [{say(a)}] you must also have "
                     f"[{say(c)}]")
        lines.append(f"    because: {t1} ({e1['field']})")
        lines.append(f"    and:     {t2} ({e2['field']})")
    lines.append("")
    lines.append("THE IMPOSSIBLE FRONTIER — closures nobody wrote, "
                 "chained from two that were written:")
    for a, c, e1, t1, e2, t2 in imposs[:limit]:
        lines.append(f"  [{say(a)}] and [{say(c)}] can never stand "
                     f"together")
        lines.append(f"    because: {t1} ({e1['field']})")
        lines.append(f"    and:     {t2} ({e2['field']})")
    lines.append("")
    lines.append("ECHOES ACROSS DOMAINS — the joining word carries "
                 "a different sense in each law. These are "
                 "metaphors, and metaphor is how vocabulary grows. "
                 "Kept, not graded:")
    for a, c, e1, t1, e2, t2 in echoes[:limit]:
        lines.append(f"  [{say(a)}] reaches [{say(c)}]")
        lines.append(f"    from: {t1} ({e1['field']})")
        lines.append(f"    to:   {t2} ({e2['field']})")
    lines.append("")
    lines.append(f"({len(echoes)} echoes kept alongside "
                 f"{len(poss)} unwritten requirements and "
                 f"{len(imposs)} unwritten closures. None is "
                 f"graded here — worth is the reader's, by what it "
                 f"is useful for.)")
    text = "\n".join(lines)
    try:
        if not os.path.exists(REC) or os.path.getsize(REC) < 65536:
            with open(REC, "a") as f: f.write("\n" + text + "\n")
    except OSError: pass
    return text

if __name__ == "__main__":
    print(explore())
