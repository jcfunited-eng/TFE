"""RUFFLES — answers, and the two ways they decay.

An answer is not stored anywhere. It is a ruffle on its ribbon:
a local settling of one observer where it crosses the sheets. A
ruffle is held only while the knowledge that raised it still
stands, and it can decay two ways:

  INTO IMPOSSIBLE  a law now closes what used to stand. The
                   answer did not become wrong — its region of
                   the sheet closed.
  INTO UNKNOWN     nothing supports it any more, or no ribbon
                   reaches it. Not refuted: unheld. This is how
                   Roman concrete and Damascus steel went.

The ruffles ARE the colors and the white on the ribbon: colored
where an answer stands, white where it is closed, bare where
nothing is held. Nothing here grades — it only reports which of
the three each stretch of the ribbon now is.
"""
import os, sys, hashlib
BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)
import fabric_ask as fa
import maker

REC = os.path.join(BASE, "life", "ruffles.md")

def _key(text):
    return hashlib.sha256(text.encode()).hexdigest()[:10]

def raise_ruffles(want, keep=3):
    """Lay the ribbon, keep the ruffles it settles into."""
    txt, closed, req, forb, es, n = maker.make(want, show=keep,
                                               data=True)
    ruffles, cur = [], []
    for line in txt.splitlines():
        s = line.strip()
        if s.startswith("· "):
            if cur: ruffles.append(cur)
            cur = [s[2:].strip()]
        elif s.startswith("with ") and cur:
            cur.append(s[5:].strip())
    if cur: ruffles.append(cur)
    out = []
    for r in ruffles[:keep]:
        out.append((want, r, _key(want + "|" + "|".join(r))))
    try:
        if not os.path.exists(REC) or os.path.getsize(REC) < 65536:
            with open(REC, "a") as f:
                for w, parts, k in out:
                    f.write(f"\nRUFFLE {k} on the ribbon: {w}\n")
                    for p in parts: f.write(f"  stood on: {p}\n")
                    f.write("  state: STANDING\n")
    except OSError: pass
    return out

def check(ruffle):
    """Does this ruffle still settle the same way?"""
    want, parts, k = ruffle
    es = fa.load()
    req, forb = maker.constraints(es)
    alive = []
    for p in parts:
        head = p[:40]
        if any(head in e["essence"] for e in es): alive.append(p)
    if len(alive) < len(parts):
        return ("GONE BARE — decayed into unknown",
                "the knowledge it stood on is no longer held; the "
                "ribbon has neither color nor white here now")
    pool = set(fa.words(want))
    for p in parts: pool |= fa.words(p)
    rare = {w for w in pool if True}
    dead = maker.judge(pool, req, forb, rare)
    if dead:
        law, parent = dead
        return ("TURNED WHITE — decayed into impossible", law)
    return ("COLORED — the answer still stands here",
            "no law closes it under the knowledge now held")

if __name__ == "__main__":
    want = " ".join(sys.argv[1:])
    rs = raise_ruffles(want)
    print(f"RIBBON: {want}")
    print(f"  ruffles raised: {len(rs)}")
    for r in rs:
        state, why = check(r)
        print(f"  ruffle {r[2]}: {state}")
        print(f"    {why[:110]}")
