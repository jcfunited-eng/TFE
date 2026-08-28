"""MINTING — the machine writing knowledge, under the law.

Nothing in this fabric has ever added to its own knowledge. Every
entry was written by a hand. This file is the one place where the
machine may write, and it is fenced by the minting law that was
bought with a failure:

  UN-AIMED       the candidate must come from the fabric's own
                 structure, not from anyone's expectation. Here
                 that means a chain of two written laws, found by
                 walking, never by asking for a particular answer.
  VERIFIED AFTER the chain must survive checks made after it
                 exists: both parents alive, the conclusion not
                 already written, the joining ground not a single
                 common word, and the conclusion must not itself
                 be closed by the knowledge.
  REACHED        it must be reached by a standing question. A
                 finding no question reaches is unattached — kept,
                 not minted.

What is minted is a WHITE entry: a wall nobody wrote, standing
where two written walls meet. It carries both parents by name, so
any reader can refuse it at the source.
"""
import os, re, sys, collections
BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)
import core

MINTED = os.path.join(core.DIR, "92_minted_walls.md")
HEADER = """# 92 MINTED WALLS — impossibilities the fabric derived itself

Every wall here was chained by the machine from two written laws,
checked after the fact, and reached by a question that was already
standing. None was authored by a hand; each names both parents so
it can be argued with at the source. If a parent falls, its
children should fall with it.
"""

def _existing(F, a, b, kind):
    for L in F.laws:
        if L["kind"] != kind: continue
        if (a & L["a"]) == a and (b & L["b"]) == b: return True
    return False

def candidates(F, max_out=40):
    """Chain two written laws into one nobody wrote."""
    by_a = collections.defaultdict(list)
    for i, L in enumerate(F.laws):
        i2, m = 0, L["a"]
        while m:
            if m & 1: by_a[i2].append(i)
            m >>= 1; i2 += 1
    out, seen = [], set()
    for L1 in F.laws:
        if L1["kind"] != "requires": continue
        # who needs what L1 gives?
        cands = set()
        i2, m = 0, L1["b"]
        while m:
            if m & 1: cands.update(by_a.get(i2, ()))
            m >>= 1; i2 += 1
        for j in cands:
            L2 = F.laws[j]
            if L2["src"] == L1["src"]: continue
            link = L1["b"] & L2["a"]
            if bin(link).count("1") < 2: continue      # not one word
            if L2["kind"] == "requires":
                a, b, kind = L1["a"], L2["b"], "requires"
            else:
                a, b, kind = L1["a"], L2["b"], "forbids"
            if not a or not b or (a & b): continue
            key = (a, b, kind)
            if key in seen: continue
            seen.add(key)
            if _existing(F, a, b, kind): continue
            # the conclusion must not itself be closed
            if F.judge(a | b) is not None and kind == "requires":
                continue
            out.append(dict(a=a, b=b, kind=kind, p1=L1, p2=L2,
                            link=link))
            if len(out) >= max_out: return out
    return out

def reached_by(F, cand, questions):
    """Which standing question reaches this candidate."""
    ground = cand["a"] | cand["b"]
    best, score = None, 0
    for q in questions:
        qm = F.mask(q.get("text", "") + " " + q.get("about", ""),
                    learn=False)
        v = bin(qm & ground).count("1")
        if v > score: best, score = q, v
    return (best, score) if score >= 2 else (None, score)

def mint(limit=6):
    F = core.fabric()
    import standing, white_kinds
    _F, kinds, _c = white_kinds.derive()
    qs = standing.all_standing(F, kinds)
    made = []
    for c in candidates(F):
        q, score = reached_by(F, c, qs)
        if q is None: continue
        aw = " ".join(F.words_of(c["a"])[:6])
        bw = " ".join(F.words_of(c["b"])[:6])
        if c["kind"] == "requires":
            claim = (f"no [{aw}] without [{bw}] — a wall nobody "
                     f"wrote, standing where two written walls meet.")
        else:
            claim = (f"no [{aw}] together with [{bw}] — a wall "
                     f"nobody wrote, standing where two written "
                     f"walls meet.")
        made.append(dict(claim=claim, cand=c, question=q,
                         score=score))
        if len(made) >= limit: break
    if made:
        if not os.path.exists(MINTED):
            open(MINTED, "w").write(HEADER)
        with open(MINTED, "a") as f:
            for m in made:
                c = m["cand"]
                f.write(f"\nESSENCE: {m['claim']}\n")
                f.write(f"ROOT: derived / two written walls chained "
                        f"by the machine.\n")
                f.write(f"CANNOT: {m['claim']}\n")
                f.write(f"THREAD: parent one — {c['p1']['text'][:80]} "
                        f"({F.entries[c['p1']['src']]['field']}); "
                        f"parent two — {c['p2']['text'][:80]} "
                        f"({F.entries[c['p2']['src']]['field']}).\n")
                f.write(f"ASKED-AS: {' '.join(F.words_of(c['a'])[:6])} "
                        f"{' '.join(F.words_of(c['b'])[:6])}\n")
                f.write(f"REACHED-BY: [{m['question']['kind']}] "
                        f"{m['question']['text'][:70]}\n")
    return made

if __name__ == "__main__":
    made = mint()
    print(f"minted {len(made)} walls the fabric derived itself")
    for m in made:
        print(f"  · {m['claim'][:100]}")
        print(f"      reached by [{m['question']['kind']}] "
              f"{m['question']['text'][:60]}")
