"""THE MAKER — one engine. A want goes in, a made thing comes out.

Nothing here knows about cooking, or worlds, or bread. The only
thing this file does is stage possibilities and let the knowledge
kill. Every constraint is read at run time out of the entries'
own CANNOT lines, in the two shapes the writers naturally used:

    "no A without B"   -> if you want A you must have B
    "no A in B"        -> A and B cannot stand together

A made thing is a set of mechanisms (entries) that together cover
what was asked for, satisfy every requirement any chosen mechanism
drags in, and violate no forbidden pairing. What survives is the
answer; what died says which law killed it.
"""
import os, re, sys, itertools
BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)
import fabric_ask as fa

def content(text):
    return fa.words(text)

def constraints(es):
    """Read every CANNOT line into requirements and forbiddings."""
    req, forb = [], []
    for e in es:
        c = e["cannot"]
        for piece in re.split(r"(?<=[.;])\s+", c):
            p = piece.strip().lower()
            m = re.search(r"\bno(?:thing)? (.+?) without (.+)", p)
            if m:
                a, b = content(m.group(1)), content(m.group(2))
                if a and b: req.append((a, b, e, piece.strip()))
                continue
            m = re.search(r"\bno (.+?) (?:in|from|with) (.+)", p)
            if m:
                a, b = content(m.group(1)), content(m.group(2))
                if a and b and not (a & b):
                    forb.append((a, b, e, piece.strip()))
    return req, forb

def judge(pool, req, forb):
    """Every law that grips this pool either passes or kills."""
    for a, b, e, txt in forb:
        # the forbidden thing must be present, and enough of the
        # condition it is forbidden in
        if a <= pool and len(b & pool) >= min(2, len(b)):
            return f"forbidden together — {txt} ({e['field']})"
    for a, b, e, txt in req:
        if a <= pool and not (b & pool):
            return f"requirement unmet — {txt} ({e['field']})"
    return None

def make(want, size=3, show=3):
    es = fa.load()
    req, forb = constraints(es)
    qs = content(want)
    df = {}
    for e in es:
        for w in content(e["essence"] + " " + e["cannot"] + " "
                         + e["ask"]):
            df[w] = df.get(w, 0) + 1
    qkey = {w for w in qs if df.get(w, 99) <= 25} or qs
    # the mechanisms the knowledge offers toward this want
    def ew(e): return content(e["essence"] + " " + e["ask"])
    offers = [e for e in es if qkey & ew(e)]
    offers.sort(key=lambda e: -len(qkey & ew(e)))
    offers = offers[:14]
    staged = killed = 0
    survivors, deaths = [], []
    for n in range(1, size + 1):
        for combo in itertools.combinations(offers, n):
            staged += 1
            pool = set(qs)
            for e in combo: pool |= content(e["essence"])
            dead = judge(pool, req, forb)
            if dead:
                killed += 1
                if len(deaths) < 3: deaths.append((combo, dead))
                continue
            # no free riders: every part must add something the
            # others do not already bring
            if any(ew(e) & qkey <= set().union(
                    *[ew(o) & qkey for o in combo if o is not e],
                    set()) for e in combo) and n > 1:
                continue
            cover = len(qkey & set().union(*[ew(e) for e in combo]))
            survivors.append((cover, -n, combo))
    survivors.sort(key=lambda s: (-s[0], -s[1]))
    out = [f"WANT: {want}",
           f"  staged {staged} possible makings from "
           f"{len(offers)} mechanisms the knowledge offers; "
           f"{killed} were killed by its own laws."]
    if deaths:
        out.append("  killed, for example:")
        for combo, why in deaths:
            names = " + ".join(e["essence"].split("—")[0].strip()[:44]
                               for e in combo)
            out.append(f"    {names}")
            out.append(f"      {why}")
    if survivors:
        out.append("  what survives — the made thing:")
        for sc, _n, combo in survivors[:show]:
            out.append("    · " + "\n      with ".join(
                e["essence"][:110] for e in combo))
            out.append("")
    else:
        out.append("  nothing survives: everything the knowledge "
                   "offers for this want is killed by its own "
                   "laws. That is an answer — it cannot be done "
                   "this way.")
    return "\n".join(out)

if __name__ == "__main__":
    print(make(" ".join(sys.argv[1:])))
