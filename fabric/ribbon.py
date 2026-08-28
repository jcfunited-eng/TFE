"""THE RIBBON — a query is an observer with its own two sheets.

A ribbon is not a line drawn across the knowledge. It is the
observer itself: it has length, a width that varies along that
length, and patches of its own — colored where it carries
possibility, white where it carries impossibility.

Measured here, not asserted:

  LENGTH   how many steps the ribbon runs before it stops
  WIDTH    at each step, how many makings still stand. Where the
           ribbon narrows it drifts toward the white sheet; where
           it widens it drifts toward the colored one.
  PATCHES  the colored ones are the mechanisms it can carry; the
           white ones are the laws it carries as closed.

Two sheets are watched for balance, because in the vision they
have always been roughly equal in size and in motion. An
imbalance is reported, never corrected — and a thing possible to
one observer can be closed to another, and can flip back.

Applicability is defined here, and it replaces every word like
junk: a finding is APPLICABLE if some ribbon's patches reach it.
A finding no ribbon reaches is not worthless — it is unattached,
waiting for an observer whose width covers it.
"""
import os, sys
BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)
import fabric_ask as fa
import maker

REC = os.path.join(BASE, "life", "ribbons.md")

def ribbon(want, depth=3):
    prof = []
    color, white = set(), {}
    for n in range(1, depth + 1):
        txt, closed, req, forb, es, wide = maker.make(
            want, size=n, show=1, data=True)
        stands = sum(c for c, near in closed.values())
        prof.append((n, wide, stands))
        for law, (c, near) in closed.items():
            white[law] = white.get(law, 0) + c
        for line in txt.splitlines():
            s = line.strip()
            if s.startswith("· ") or s.startswith("with "):
                color.add(s.lstrip("· ").lstrip("with ")[:70])
    return prof, color, white

def describe(want):
    prof, color, white = ribbon(want)
    out = [f"RIBBON: {want}", f"  length: {len(prof)} steps"]
    for n, wide, closed in prof:
        drift = ("drifting toward the white sheet"
                 if closed > wide else
                 "drifting toward the colored sheet")
        out.append(f"    step {n}: width {wide} standing, "
                   f"{closed} closed — {drift}")
    out.append(f"  its colored patches — what this observer can "
               f"carry ({len(color)}):")
    for c in sorted(color)[:3]:
        out.append(f"    {c}")
    out.append(f"  its white patches — what this observer carries "
               f"as closed ({len(white)}):")
    for law in sorted(white, key=lambda l: -white[l])[:3]:
        out.append(f"    {law[:100]}")
    tot_c, tot_w = len(color), len(white)
    if tot_c and tot_w:
        r = tot_c / tot_w
        bal = ("the two sheets stand near equal for this observer"
               if 0.5 <= r <= 2 else
               ("this observer leans to the possible"
                if r > 2 else "this observer leans to the closed"))
        out.append(f"  balance: {tot_c} colored to {tot_w} white — "
                   f"{bal}.")
    try:
        if not os.path.exists(REC) or os.path.getsize(REC) < 65536:
            with open(REC, "a") as f:
                f.write("\n" + "\n".join(out) + "\n")
    except OSError: pass
    return "\n".join(out)

def reaches(finding_words, want_list):
    """Applicability: does any ribbon's patches reach this?
    Nothing is worthless — only unattached."""
    for w in want_list:
        prof, color, white = ribbon(w, depth=2)
        bag = fa.words(" ".join(color) + " " + " ".join(white))
        if len(finding_words & bag) >= 2:
            return w
    return None

if __name__ == "__main__":
    print(describe(" ".join(sys.argv[1:])))
