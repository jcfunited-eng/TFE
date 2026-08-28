"""UNDULATION — the sheets breathe, and both are knowledge.

Colored knowledge is possibility: the knowns and the maybes.
White knowledge is impossibility: the unknowns and the cannots.
They are equals, and every entry straddles them — its essence
stands on the colored sheet, its cannot on the white one.

The sheets move. Learning is white becoming colored: an unknown
turning into a known. Forgetting is colored going back to white
— and it goes back as an UNKNOWN, never as a cannot. Nothing is
refuted; it stops being held. Roman concrete went that way.

Forgetting here is real: a faded entry stops being read, so the
ability it carried genuinely dies. What is kept is the question
of it, standing in the white where any ribbon can reach it — and
if one does, it can be learned again.
"""
import os, re, sys, glob
BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)
import fabric_ask as fa

STATE = os.path.join(BASE, "life", "state.txt")
FORGOT = os.path.join(BASE, "life", "forgotten.md")

def sheets():
    es = fa.load()
    colored = sum(1 for e in es if e["essence"])
    cannots = 0
    for e in es:
        cannots += len([p for p in re.split(r"(?<=[.;])\s+",
                                            e["cannot"]) if p.strip()])
    wtxt = open(fa.WHITE).read() if os.path.exists(fa.WHITE) else ""
    unknowns = wtxt.count("STATUS: STANDING")
    faded = 0
    for f in glob.glob(os.path.join(fa.DIR, "[0-9][0-9]_*.md")):
        faded += open(f).read().count("STATE: FADED")
    return colored, cannots, unknowns, faded

def report():
    c, k, u, f = sheets()
    w = k + u
    print("THE TWO SHEETS, both knowledge:")
    print(f"  colored — possibility: {c} claims standing "
          f"(the knowns and the maybes)")
    print(f"  white   — impossibility: {w} standing "
          f"({k} cannots + {u} unknowns)")
    r = c / w if w else 0
    if 0.5 <= r <= 2:
        print(f"  they run near equal ({r:.2f} to 1), as the "
              f"vision says they always have.")
    else:
        print(f"  they are OUT of balance ({r:.2f} to 1) — "
              f"reported, not corrected.")
    print(f"  faded back into the white as unknowns: {f}")

def unused():
    """Entries no ribbon has warmed — candidates for forgetting."""
    import hashlib
    warm = set()
    if os.path.exists(STATE):
        for line in open(STATE):
            p = line.split()
            if p and p[0] == "WARM": warm.add(p[1])
    def fid(e):
        return hashlib.sha256(
            (e["field"] + "|" + e["essence"]).encode()).hexdigest()[:8]
    out = []
    for e in fa.load():
        if fid(e) in warm: continue
        out.append(e)
    return out

def forget(n=3, dry=True):
    """Colored goes back to white as unknown. The knowledge stops
    being held; the question of it stands where a ribbon can find
    it."""
    cands = unused()
    # a wave falls where it is highest, not where it is useful.
    # What fades is what is THINLY HELD: few other entries lean on
    # it, and its field is crowded. Load-bearing knowledge — the
    # kind many entries thread to — holds itself up.
    es_all = fa.load()
    counts, held = {}, {}
    for e in es_all:
        counts[e["field"]] = counts.get(e["field"], 0) + 1
    for e in es_all:
        th = (e.get("thread") or "").lower()
        for o in es_all:
            if o is e: continue
            key = o["field"].split()[-1]
            if key and key in th:
                held[o["essence"][:40]] = held.get(
                    o["essence"][:40], 0) + 1
    def hold(e): return held.get(e["essence"][:40], 0)
    cands.sort(key=lambda e: (hold(e), -counts.get(e["field"], 0)))
    done = []
    for e in cands[:n]:
        head = e["essence"][:50]
        for f in glob.glob(os.path.join(fa.DIR, "[0-9][0-9]_*.md")):
            t = open(f).read()
            if head not in t: continue
            if not dry:
                t2 = t.replace("ESSENCE: " + e["essence"][:50],
                               "STATE: FADED\nESSENCE: "
                               + e["essence"][:50], 1)
                open(f, "w").write(t2)
                with open(fa.WHITE, "a") as w:
                    w.write(f"\nENTRY: what was once held about "
                            f"{e['ask'][:60]}\n"
                            f"  KIND: UNKNOWN — faded from the "
                            f"colored sheet, not refuted. It stopped "
                            f"being held.\n"
                            f"  ONCE SAID: {e['essence'][:90]}\n"
                            f"  STATUS: STANDING (white)\n")
                if not os.path.exists(FORGOT) or \
                        os.path.getsize(FORGOT) < 65536:
                    with open(FORGOT, "a") as g:
                        g.write(f"\nFORGOTTEN from ({e['field']}): "
                                f"{e['essence'][:90]}\n")
            done.append((e["field"], e["essence"][:70]))
            break
    return done

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "forget":
        n = int(sys.argv[2]) if len(sys.argv) > 2 else 3
        for fld, ess in forget(n, dry=False):
            print(f"forgotten from ({fld}): {ess}")
        print()
    report()

def relearn(question, need=2):
    """The other road: white becoming colored again. A ribbon
    reaching a faded thing's question brings it back — this is
    learning, and it is the same motion as forgetting, reversed.
    Nothing is invented here; what returns is what was held."""
    qw = fa.words(question)
    back = []
    for f in glob.glob(os.path.join(fa.DIR, "[0-9][0-9]_*.md")):
        t = open(f).read()
        if "STATE: FADED" not in t: continue
        out, changed = [], False
        blocks = t.split("STATE: FADED\n")
        rebuilt = blocks[0]
        for b in blocks[1:]:
            head = b.split("\n")[0]
            body = b[:600]
            if len(qw & fa.words(body)) >= need:
                rebuilt += b            # returned to the colored sheet
                changed = True
                back.append(head[:70])
            else:
                rebuilt += "STATE: FADED\n" + b
        if changed:
            open(f, "w").write(rebuilt)
    if back:
        w = open(fa.WHITE).read()
        w = w.replace("STATUS: STANDING (white)\n",
                      "STATUS: STANDING (white)\n", 1)
        # mark the matching unknowns as learned again
        w = re.sub(r"(KIND: UNKNOWN — faded[\s\S]*?STATUS: )"
                   r"STANDING \(white\)",
                   r"\1LEARNED AGAIN — a ribbon reached it", w)
        open(fa.WHITE, "w").write(w)
    return back
