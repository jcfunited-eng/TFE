"""THE READING BENCH — every sentence that must keep reading correctly.

This exists because a grouping change fixed two sentences and silently
broke a third, and it was found by accident. Nothing in the language
side may be changed without this being run before and after.

WHOSE JUDGEMENT: the expected readings below are MINE. They are what I
say the sentence turns on and what I say it is about, written down in
advance so a change cannot be graded after the fact. They are not
Joe's and they are not the fabric's. If one of them is wrong, the
right move is to argue with the line, not to quietly re-grade.

TURNS-ON is the one word the sentence hinges on. ABOUT is what must
appear; extra words in about are not counted wrong here, because the
frame words differ between sentences and over-naming is a lesser fault
than missing the subject. Missing a named ABOUT word is a fault.
"""
import os, sys
BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)
import core, wanting

# sentence, turns-on, must-be-about, must-forbid
CASES = [
    ("why does bread rise",                    "rise",   ["bread"], []),
    ("how do I sharpen a knife",               "sharpen", ["knife"], []),
    ("the dog bit the man",                    "bit",    ["dog", "man"], []),
    ("the man bit the dog",                    "bit",    ["dog", "man"], []),
    ("salt melts ice",                         "melt",   ["salt", "ice"], []),
    ("the fire heated the water",              "heat",   ["fire", "water"], []),
    ("the wind moved the trees",               "move",   ["wind", "tree"], []),
    ("why do onions make you cry",             "make",   ["onion", "cry"], []),
    ("how does a whip crack",                  "crack",  ["whip"], []),
    ("why do we shake hands",                  "shake",  ["hand"], []),
    ("keep food cold without electricity",     "keep",   ["food", "cold"],
     ["electricity"]),
    ("build a shelter that stays warm",        "build",  ["shelter", "warm"], []),
    ("why does the moon look bigger near the horizon",
     "look", ["moon", "horizon"], []),
    ("how do I boil an egg",                   "boil",   ["egg"], []),
    ("the child dropped the cup",              "drop",   ["child", "cup"], []),
]


# HELD OUT. Written after the doing rule was already settled on the
# set above, and never consulted while settling it. A rule tuned on
# the cases it is scored against has been scored on nothing. If these
# read much worse than the set above, the rule is fitted, not found.
HELD_OUT = [
    ("the river carved the canyon",   "carve",  ["river", "canyon"], []),
    ("why does milk spoil",           "spoil",  ["milk"], []),
    ("how do I plant a seed",         "plant",  ["seed"], []),
    ("the engine burns fuel",         "burn",   ["engine", "fuel"], []),
    ("yeast raises dough",            "raise",  ["yeast", "dough"], []),
    ("why do birds migrate",          "migrate", ["bird"], []),
    ("the hammer struck the nail",    "struck", ["hammer", "nail"], []),
    ("how does a magnet attract iron", "attract", ["magnet", "iron"], []),
    ("the frost killed the plants",   "kill",   ["frost", "plant"], []),
    ("why does paper burn",           "burn",   ["paper"], []),
    ("sand scratches glass",          "scratch", ["sand", "glass"], []),
    ("how do I clean a wound",        "clean",  ["wound"], []),
    ("the sun warms the stone",       "warm",   ["sun", "stone"], []),
    ("why do leaves change colour",   "change", ["leaves", "colour"], []),
    ("boil the water first",          "boil",   ["water"], []),
]


def same_word(a, b):
    """The stemmer clips hard — water becomes wat, moved becomes mov.
    That is a real defect and it is filed separately; it must not be
    allowed to score a correct reading as wrong here."""
    a, b = core.stem(a.lower()), core.stem(b.lower())
    return a.startswith(b) or b.startswith(a)


def grade(F=None, cases=None):
    F = F or core.fabric()
    rows, good = [], 0
    for sent, doing, about, forbid in (cases or CASES):
        w = wanting.want(sent, F)
        if w.get("unread"):
            rows.append((sent, "UNREAD", w["unread"][0][:40], False))
            continue
        got = (w["turns_on"] or "").lower()
        gotabout = list(w["about"])
        gotforbid = set(w["forbidden"])
        ok_doing = same_word(got, doing)
        miss = [a for a in about
                if not any(same_word(a, g) for g in gotabout)]
        ok_forbid = all(any(same_word(f, g) for g in gotforbid)
                        for f in forbid)
        ok = ok_doing and not miss and ok_forbid
        good += ok
        why = []
        if not ok_doing:
            why.append(f"turns on '{got}', should be '{doing}'")
        if miss:
            why.append(f"not about {','.join(miss)}")
        if not ok_forbid:
            why.append("forbidden not read")
        rows.append((sent, got, "; ".join(why), ok))
    return rows, good


if __name__ == "__main__":
    F = core.fabric()
    for name, cases in (("SETTLED ON", CASES), ("HELD OUT", HELD_OUT)):
        rows, good = grade(F, cases)
        print(f"\n{name}")
        for sent, got, why, ok in rows:
            print(f"  {'ok  ' if ok else 'FAIL'}  {sent:<50} -> {got}")
            if why:
                print(f"          {why}")
        print(f"  {good}/{len(cases)} read correctly")
