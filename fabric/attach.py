"""ATTACHMENT — utility measured against the observers.

The observers are the questions. A finding is useful when some
question reaches it; a finding nothing reaches is unattached and
waits. Nothing here grades anything: it only reports which
question, if any, covers a finding.

Questions come from where the fabric keeps them: the ones it was
asked and could not answer, and the ones it asked itself while
running.
"""
import os, re, sys
BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)
import fabric_ask as fa

LIFE = os.path.join(BASE, "life")

def questions():
    qs = []
    w = fa.WHITE
    if os.path.exists(w):
        t = open(w).read()
        qs += re.findall(r"ENTRY: ([^\n]+)", t)
    for name in ("possible_candidates.md", "impossible_layer.md",
                 "ribbons.md"):
        p = os.path.join(LIFE, name)
        if os.path.exists(p):
            t = open(p).read()
            qs += re.findall(r"WANT: ([^\n]+)", t)
            qs += re.findall(r"RIBBON: ([^\n]+)", t)
    seen, out = set(), []
    for q in qs:
        k = q.strip().lower()
        if k and k not in seen:
            seen.add(k); out.append(q.strip())
    return out

def attach(finding_text, qs=None, need=2, by_patches=True):
    """Which observer reaches this finding, if any.

    A question is a ribbon, so reaching is judged against the
    ribbon's PATCHES — the mechanisms it carries and the laws it
    carries as closed — not against the words of the question.
    A question is a thin thing; the ribbon it names is wide."""
    qs = qs if qs is not None else questions()
    fw = fa.words(finding_text)
    best, score = None, 0
    if by_patches:
        import ribbon as R
        for q in qs:
            try:
                prof, color, white = R.ribbon(q, depth=2)
            except Exception:
                continue
            bag = fa.words(" ".join(color) + " " + " ".join(white))
            v = len(fw & bag)
            if v > score: best, score = q, v
    else:
        for q in qs:
            v = len(fw & fa.words(q))
            if v > score: best, score = q, v
    if score >= need:
        return best, score
    return None, score

if __name__ == "__main__":
    text = " ".join(sys.argv[1:])
    qs = questions()
    q, s = attach(text, qs)
    print(f"observers standing (questions): {len(qs)}")
    if q:
        print(f"reached by: \"{q}\" (shared ground {s})")
        print("that question is the observer this finding has "
              "use for.")
    else:
        print("no standing question reaches this yet — unattached, "
              "not worthless; it waits for an observer wide enough "
              "to cover it.")
