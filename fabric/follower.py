"""THE FOLLOWER — arithmetic with nothing wired.

This file used to look for phrases: "right to left", "set aside
every full ten". Those were the procedure living in my hands
while pretending to live in the knowledge. They are gone.

What happens now: the question says which written rule is wanted,
the rule's own steps are bound to acts by reaching, and the
interpreter runs them. The only machinery is the twelve hands in
interpreter.py, each of which is named by an entry in the
knowledge. Delete a rule and the ability dies. Delete an act
entry and the procedure stops, naming what it lacks.
"""
import os, re, sys
BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)
import core
import interpreter as I

def _digits(n): return [int(c) for c in str(n)][::-1]

def _num(out):
    o = list(out)
    while len(o) > 1 and o[-1] == 0: o.pop()
    return int("".join(map(str, o[::-1])))

def _rule_for(want):
    """Which written procedure does this asking want? Found by
    reaching over the rules themselves — no list of operations."""
    F = core.fabric()
    wm = F.mask(want, learn=False)
    best, score = None, 0
    for e in F.entries:
        if not e["rule"]: continue
        head = e["rule"].split("\u2014")[0]
        v = bin(wm & F.mask(head + " " + e["ask"],
                            learn=False)).count("1")
        if v > score: best, score = e, v
    return (best, score) if score >= 1 else (None, score)

def try_numbers(question):
    nums = [int(x) for x in re.findall(r"\d+", question)]
    if len(nums) < 2: return None
    entry, score = _rule_for(question)
    if entry is None:
        return ("I can see numbers here, but no written rule of "
                "mine reaches what this asking wants done. The "
                "missing procedure is the whole answer.")
    st = dict(digits=[_digits(n) for n in nums],
              places=len(_digits(nums[0])), i=0,
              big=max(nums), small=min(nums))
    trace = []
    st, err = I.follow(entry["rule"], st, trace)
    if err: return err
    if "out" not in st:
        return ("I followed the rule but it produced nothing I can "
                "read as a number. Said plainly rather than "
                "guessed.")
    got = _num(st["out"])
    steps = ", ".join(a for _s, a, _v in trace[:4])
    return (f"{got:,}\n"
            f"  followed my own written rule: \"{entry['rule'][:70]}"
            f"...\"\n"
            f"  acts used, bound by knowledge: {steps}\n"
            f"  nothing about this operation is written in my code.")
