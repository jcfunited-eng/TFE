"""TOLD, AND THEN IT DOES IT — the only test that cannot be faked.

Every other bench scores a reading against my judgement of English,
which measures agreement with me. This one does not look at the
reading at all. It says something to the fabric in plain words, and
then checks whether the fabric ARRIVES AT THE RIGHT ANSWER.

The whole path runs: the sentence is read into what is wanted; the
doing reaches into the corpus for a procedure the fabric itself has
written down; that procedure is followed step by step by the
interpreter; and the number that comes out is compared with
arithmetic. Nothing in that chain is my opinion. If the reading is
wrong the answer is wrong.

How big a full bundle is comes from the RULE's own words — the
handler refuses to assume one and says so — so even the ten in
base-ten is read out of the knowledge rather than supplied here.
"""
import os, sys, re
BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)
import core, interpreter as I, wanting

def reach(F, doing):
    """A procedure answers to the words it says it is asked for.
    find_rule needs the top score to beat the second outright, so a
    single word ties across many rules and nothing wins. Where several
    tie, prefer the one whose ASKED-AS names the doing outright: that
    is the entry's own claim to answer to that word, not my ranking.
    Reaches 6 of 9 plain arithmetic words where find_rule reaches 3."""
    st = core.stem(doing or "")
    named = [e for e in F.entries if e.get("rule")
             and any(core.stem(x) == st
                     for x in re.findall(r"[a-z]+", e["ask"].lower()))]
    if named:
        sm = F.mask((doing or "") + " number", learn=False)
        named.sort(key=lambda e: -bin(sm & F.mask(
            e["rule"].split("—")[0] + " " + e["ask"],
            learn=False)).count("1"))
        return named[0]
    return I.find_rule(F, (doing or "") + " number")[0]

CASES = [
    ("add 45 and 47", 92), ("add 8 and 7", 15),
    ("add 123 and 456", 579), ("add 99 and 1", 100),
    ("add 7 and 8", 15), ("add 250 and 250", 500),
    ("add 12 and 34", 46), ("add 606 and 909", 1515),
    # the same act said differently. The procedure is identical, so
    # every failure here is the READING failing to reach it.
    ("sum 45 and 47", 92), ("total 45 and 47", 92),
    ("what is 45 plus 47", 92), ("add together 45 and 47", 92),
    ("work out 45 and 47 added", 92), ("please add 45 and 47", 92),
    ("add 45 to 47", 92), ("count 45 and 47 together", 92),
    # other acts entirely. The reading must reach a DIFFERENT
    # procedure and that procedure must run.
    ("subtract 20 from 56", 36), ("take 12 away from 90", 78),
    ("subtract 7 from 15", 8), ("multiply 12 by 3", 36),
    ("multiply 7 by 8", 56), ("times 9 by 6", 54),
]


def act(sentence, F):
    """told -> read -> find the fabric's own procedure -> follow it."""
    w = wanting.want(sentence, F)
    doing = w.get("turns_on")
    nums = [int(x) for x in re.findall(r"\d+", sentence)]
    # THE ROLES DECIDE WHICH NUMBER IS WHICH. "subtract 20 from 56"
    # reads done-to=20 -- the number being taken -- so it goes second
    # and the other is the one it is taken from. Without this the
    # digits went in sentence order and 56 minus 20 came back 64.
    done = w.get("done_to")
    if done and done.isdigit() and len(nums) == 2:
        d = int(done)
        nums = [n for n in nums if n != d] + [d]
    e = reach(F, doing)
    if not e or len(nums) < 2:
        return doing, None, "no procedure reached"
    # a procedure asks for what it asks for: the times-rule lays the
    # larger number down as many times as the smaller says, so it
    # wants them named that way. The numbers are the same ones read
    # out of the sentence.
    st = dict(big=max(nums), small=min(nums),
              digits=[[int(c) for c in str(n)][::-1] for n in nums],
              bundle=I.bundle_from_knowledge(F, e["rule"]),
              out=[], i=0, carry=0)
    out, err = I.follow(e["rule"], st, [])
    if out and out.get("out"):
        return doing, int("".join(str(x) for x in out["out"][::-1])), err
    return doing, None, err or "the procedure produced nothing"


def grade(F=None):
    F = F or core.fabric()
    rows, good = [], 0
    for s, truth in CASES:
        doing, got, err = act(s, F)
        ok = got == truth
        good += ok
        rows.append((s, doing, got, truth, ok, err))
    return rows, good


if __name__ == "__main__":
    rows, good = grade()
    for s, d, got, truth, ok, err in rows:
        print("  %-4s %-20s read=%-8s got=%-6s truth=%-6s %s"
              % ("ok" if ok else "FAIL", s, d, got, truth, err or ""))
    print("\n  TOLD AND DONE: %d/%d" % (good, len(rows)))
