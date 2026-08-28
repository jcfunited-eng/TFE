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

def judge(pool, req, forb, touch=None):
    """Every law that grips this pool either passes or kills.
    A law grips only what it touches: its own entry must share
    ground with the making, or it has no business judging it."""
    def grips(e):
        if touch is None: return True
        return bool(touch & content(e["essence"] + " "
                                    + e["cannot"]))
    for a, b, e, txt in forb:
        if not grips(e): continue
        # the forbidden thing must be present, and enough of the
        # condition it is forbidden in
        if a <= pool and len(b & pool) >= min(2, len(b)):
            return f"forbidden together — {txt} ({e['field']})"
    for a, b, e, txt in req:
        if not grips(e): continue
        if a <= pool and not (b & pool):
            return f"requirement unmet — {txt} ({e['field']})"
    return None

def make(want, size=3, show=3):
    es = fa.load()
    req, forb = constraints(es)
    # the command word is how you asked, not part of what you want
    want_body = re.sub(r"^\s*(make|build|design|create|invent|"
                       r"give me a way|a way to|how (do|can) (i|we)|"
                       r"how to)\b", "", want, flags=re.I)
    qs = content(want_body)
    df = {}
    for e in es:
        for w in content(e["essence"] + " " + e["cannot"] + " "
                         + e["ask"]):
            df[w] = df.get(w, 0) + 1
    qkey = {w for w in qs if df.get(w, 99) <= 25} or qs
    # the words layer: each want word carries a sense, and its
    # near-words come with it. Letters stop deciding matches.
    try:
        import senses as S
        fam = {}
        for w in qkey:
            if df.get(w, 99) > 8: continue   # only distinctive
            near = sorted(S.family(w, qs))[:10]
            fam[w] = {content(x).pop() for x in near if content(x)}
        want_words = set(qkey) | (set().union(*fam.values())
                                  if fam else set())
        def sense_ok(w, e):
            return S.same_sense(w, qs, content(e["essence"]))
    except Exception:
        want_words = set(qkey)
        def sense_ok(w, e): return True
    # the mechanisms the knowledge offers toward this want
    def ew(e): return content(e["essence"] + " " + e["ask"])
    offers = [e for e in es
              if (want_words & ew(e)) and
              all(sense_ok(w, e) for w in (qkey & ew(e)))]
    offers.sort(key=lambda e: -len(want_words & ew(e)))
    offers = offers[:16]
    staged = killed = 0
    survivors, deaths, closed = [], [], {}
    for n in range(1, size + 1):
        for combo in itertools.combinations(offers, n):
            staged += 1
            pool = set(qs)
            for e in combo: pool |= content(e["essence"])
            rare_touch = {w for w in pool if df.get(w, 99) <= 14}
            dead = judge(pool, req, forb, rare_touch)
            if dead:
                killed += 1
                # the impossible layer is kept, not discarded: it
                # is what gives the possible its shape
                closed[dead] = closed.get(dead, 0) + 1
                if len(deaths) < 3: deaths.append((combo, dead))
                continue
            # each part must keep company with another part:
            # sharing an uncommon word beyond the want's own.
            # A word that only sounds the same (a steak's crust,
            # the planet's crust) keeps no company and drops out.
            if n > 1:
                def bod(e): return content(e["essence"] + " "
                                           + e["cannot"])
                def rw(s): return {w for w in s
                                   if df.get(w, 99) <= 14} - qs
                if any(not any(rw(bod(e)) & rw(bod(o))
                               for o in combo if o is not e)
                       for e in combo):
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
           f"{len(offers)} mechanisms; {killed} were closed by the "
           f"laws I hold. Judged under those laws only — another "
           f"set of laws gives another answer."]
    if closed:
        out.append("  THE IMPOSSIBLE — this want's other layer, "
                   "equal in standing to what survives:")
        for law, n in sorted(closed.items(), key=lambda x: -x[1])[:4]:
            out.append(f"    closed {n} makings — {law}")
    if survivors:
        out.append("  THE POSSIBLE — what survives, the made "
                   "thing (useful to an observer holding these "
                   "laws; not a verdict on true or false):")
        for sc, _n, combo in survivors[:show]:
            out.append("    · " + "\n      with ".join(
                e["essence"][:110] for e in combo))
            if any("UNSURE" in (e["essence"] + e["cannot"] +
                                e.get("rule", "")) for e in combo):
                out.append("      (one part of this is contested "
                           "knowledge, flagged unsure by its "
                           "writer)")
            out.append("")
    else:
        out.append("  THE POSSIBLE — empty. Under the laws I "
                   "hold, this want lives entirely on the other "
                   "layer. That is a finding, not a failure.")
    if closed:
        rec = os.path.join(BASE, "life", "impossible_layer.md")
        try:
            if not os.path.exists(rec) or os.path.getsize(rec) < 65536:
                with open(rec, "a") as f:
                    f.write(f"\nWANT: {want}\n")
                    for law, n in sorted(closed.items(),
                                         key=lambda x: -x[1])[:5]:
                        f.write(f"  closed {n} — {law}\n")
        except OSError: pass
    return "\n".join(out)

if __name__ == "__main__":
    print(make(" ".join(sys.argv[1:])))
