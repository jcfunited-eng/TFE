"""CAN IT BE TOLD ENOUGH TO ACT — the only bench with no label of mine.

Every other bench in this fabric scores the reading against my
judgement of English. That measures agreement with me, not
understanding, and it is why every number they gave was suspect: a
control that picks random content words out of the sentence scores 74
per cent against the corpus's own declared subjects, and the reading
scores 73.

This one has no labels. The instructions are generated mechanically —
phrasings crossed with operations crossed with numbers — and the
question asked of the reading is not "does it parse the way I would"
but "does it recover what is needed to act". Whether the recovered
thing is right is arithmetic, not opinion.

It found in one run what none of the labelled benches could: the
reading tokenised sentences as letters only, so every digit was thrown
away before anything looked at it. "add 59 and 73" arrived as "add
and". No bench of sentences I wrote had a number in it.
"""
import os, sys, re, random
BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)
import core, wanting

OPS = ["add", "subtract", "multiply", "divide", "double", "halve",
       "count"]
# "take {a} and {op} {b}" is here BECAUSE it fails. It was dropped from
# this list once and the bench read 126 of 126, which is the whole
# disease in one line: a test you prune until it passes is not a test.
FRAMES = ["{op} {a} and {b}", "{op} {a} by {b}", "work out {a} {op} {b}",
          "take {a} and {op} {b}",
          "{op} the number {a} and the number {b}",
          "please {op} {a} and {b}", "{op} {a} with {b}"]


def cases():
    rnd = random.Random(11)
    out = []
    for f in FRAMES:
        for op in OPS:
            for _ in range(3):
                a, b = rnd.randint(2, 99), rnd.randint(2, 99)
                out.append((f.format(op=op, a=a, b=b), op, {a, b}))
    return out


def grade(F=None):
    F = F or core.fabric()
    good, rows = 0, []
    for s, op, nums in cases():
        w = wanting.want(s, F)
        blob = " ".join(w.get("about") or []) + " " + str(w.get("turns_on"))
        got = {int(x) for x in re.findall(r"\d+", blob)}
        ok = (core.stem(w.get("turns_on") or "") == core.stem(op)
              and got == nums)
        good += ok
        rows.append((s, w.get("turns_on"), ok))
    return rows, good


if __name__ == "__main__":
    rows, good = grade()
    for s, got, ok in rows:
        if not ok:
            print(f"  FAIL  {s:<40} wants {got}")
    print(f"\n  ENOUGH TO ACT ON: {good}/{len(rows)}")
