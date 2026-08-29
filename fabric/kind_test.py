"""WHICH KIND OF SENTENCE — a hand-labelled set, because the proxy lied.

Every measurement of the is-or-acting split was taken against a proxy:
does the sentence contain is/are/was/were anywhere. That proxy calls
"while a thing IS changing state its temperature stops moving" a
sentence about what something is, and it is not. Every number tuned
against it was tuned against noise, and two rules were nearly shipped
on its say-so.

These sixty are drawn by seed from the fabric's own writing — I chose
none of them — and labelled by hand. The labels are MINE and they are
judgement, not fact; where one is arguable the right move is to argue
with the line rather than re-grade after the fact.

IS  = says what a thing is. Nothing acts and nothing is acted on.
ACT = something is done. There is a doing.

Passives ("some poisons are made by the body") are ACT: something is
done, even though no doer is named.
"""
import os, sys, re, random
BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)
import core, first_ribbon as FR

IS = {2, 3, 4, 6, 8, 15, 19, 20, 22, 25, 29, 31, 35, 38, 42, 43, 44,
      46, 47, 50, 52, 53, 58, 59}


def cases(F=None):
    """The same sixty, every time: drawn by seed from the essences."""
    F = F or core.fabric()
    sents = []
    for e in F.entries:
        for q in re.split(r"[.;]", e["essence"]):
            w = q.strip()
            if 5 <= len(w.split()) <= 11 and w[:1].isalpha():
                sents.append(w)
    random.seed(1234)
    return [(s, (i + 1) not in IS)          # True = ACT
            for i, s in enumerate(random.sample(sents, 60))]


def grade(F=None, test=None):
    """test(groups) -> True when it reads the sentence as ACTing."""
    F = F or core.fabric()
    if test is None:
        # the shipped rule, so this bench measures what runs
        test = lambda gs: any(FR.is_doing_group(g)
                              for g in FR.regroup(gs)[1:])
    ok, rows = 0, []
    for s, act in cases(F):
        gs = FR.groups(s)
        if len(gs) < 2:
            rows.append((s, None, act, False))
            continue
        got = test(gs)
        ok += (got == act)
        rows.append((s, got, act, got == act))
    return rows, ok


if __name__ == "__main__":
    rows, ok = grade()
    for s, got, act, good in rows:
        if not good:
            print("  FAIL  %-58s read %s, is %s"
                  % (s[:58], "ACT" if got else "IS",
                     "ACT" if act else "IS"))
    n = len(rows)
    print("\n  %d/%d  (%.0f%%) -- the corpus is %d ACT, %d IS, so always"
          " saying ACT scores %d" %
          (ok, n, 100 * ok / n, sum(1 for _s, a in cases() if a),
           60 - len(IS), sum(1 for _s, a in cases() if a)))
