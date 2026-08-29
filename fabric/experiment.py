"""THE EXPERIMENT — can a CLAIM kill a candidate, with no denial?

Everything computed in this fabric so far has been computed on the
CANNOT lines: hand-written denials, parsed into word-masks. Every
disaster came from there. And they are a second copy of what the
claim already says — "heat flows hot to cold, never the reverse
without paid work" forbids a passive fridge whether or not anybody
writes the denial down.

So the question this settles, one way or the other:

  Take a claim. Take a candidate that is NOT in the fabric. Can the
  claim close the candidate, using nothing but what the claim says?

If yes, the denial lines are scaffolding and can go. If no, then
every "constraint" here was only ever a string I matched, and I
should say so.

The method is the only honest one available: read both with the
language program — group them, find what each turns on, and see
what each says about the same two things. A claim that says A goes
to B kills a candidate that says B goes to A about the same pair.
Nothing about heat is written here. Nothing about direction is
written here. The comparison is structural and the sentences supply
the content.
"""
import os, re, sys
BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)
import core, first_ribbon as FR


def shape(sentence, F):
    """What this sentence says, as its parts in the order it puts
    them. Read by the language program, not by a rule about the
    subject."""
    gs = FR.groups(sentence)
    heads = [FR.head(g) for g in gs]
    res = FR.read(sentence)
    doing = None
    if not res["missing"] and res["stood"]:
        _s, _p, d = res["stood"][0]
        doing = FR.head(res["groups"][d])
    # Stem before comparing. The groups come back in the words the
    # sentence used; the vocabulary holds stems. Comparing them raw
    # threw away "hotter" and "cooler" and left one word to reason
    # with, which is not a failed experiment, it is a failed test.
    content, seen = [], set()
    for h in heads:
        st = core.stem(h)
        if st == (core.stem(doing) if doing else None):
            continue
        if st in core.STOP or len(st) < 3 or st in seen:
            continue
        seen.add(st)
        content.append(st)
    return dict(doing=doing, order=content, heads=heads)


def contradicts(claim, candidate, F):
    """Does the claim close the candidate?

    Only one test, and it is not about any subject: the two say
    something about the SAME pair of things, and they put that pair
    in opposite order. That is one thing going to another, reversed.
    """
    a, b = shape(claim, F), shape(candidate, F)
    ca, cb = a["order"], b["order"]
    shared = [w for w in ca if w in cb]
    if len(shared) < 2:
        return None, f"they do not talk about the same things " \
                     f"(shared: {shared})"
    pa = [w for w in ca if w in shared][:2]
    pb = [w for w in cb if w in shared][:2]
    if pa == pb[::-1]:
        return True, (f"the claim puts {pa[0]} before {pa[1]}; "
                      f"this puts them the other way round")
    if pa == pb:
        return False, (f"same pair, same order — it agrees with the "
                       f"claim")
    return None, "same things, no order to compare"


CLAIM = ("heat always moves from the hotter thing to the cooler "
         "thing")

TRIALS = [
    ("heat moves from the cooler thing to the hotter thing",
     "should DIE — it is the claim reversed"),
    ("heat moves from the hotter thing to the cooler thing",
     "should LIVE — it is what the claim says"),
    ("water moves from the higher place to the lower place",
     "should LIVE — the claim is not about it"),
    ("the cooler thing warms the hotter thing",
     "should DIE — the claim reversed, said another way"),
]


def run():
    F = core.fabric()
    print(f"CLAIM (no denial line used): {CLAIM}\n")
    print(f"  the claim reads as: {shape(CLAIM, F)}\n")
    right = 0
    for cand, expect in TRIALS:
        killed, why = contradicts(CLAIM, cand, F)
        verdict = ("CLOSED" if killed else
                   "STANDS" if killed is False else "NO VERDICT")
        want_dead = "DIE" in expect
        ok = (killed is True) == want_dead
        right += ok
        print(f"  {verdict:11s} {cand}")
        print(f"    {why}")
        print(f"    {expect} -> {'correct' if ok else 'WRONG'}\n")
    print(f"{right} of {len(TRIALS)} judged correctly, using the "
          f"claim alone.")
    return right, len(TRIALS)


if __name__ == "__main__":
    run()
