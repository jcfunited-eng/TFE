"""THE THREAD — keeps what a conversation carries between turns.

This file holds no rule about conversing. It keeps the thread: the
ground the exchange stands on, and what has already been said. The
turn itself is the written procedure in the knowledge, followed by
the interpreter. Nothing here chooses what to say.
"""
import os, sys, json
BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)
import core, interpreter as I

STATE = os.path.join(BASE, "life", "thread.json")

def load():
    if os.path.exists(STATE):
        try:
            d = json.load(open(STATE))
            return set(d.get("said", [])), int(d.get("ground", "0"))
        except Exception:
            pass
    return set(), 0

def save(said, ground):
    tmp = STATE + ".tmp"
    json.dump(dict(said=sorted(said)[-60:], ground=str(ground)),
              open(tmp, "w"))
    os.replace(tmp, STATE)

def turn_rule(F):
    for e in F.entries:
        if e["rule"].startswith("to take a turn"):
            return e["rule"]
    return None

def take_turn(question):
    F = core.fabric()
    rule = turn_rule(F)
    if rule is None:
        return None, ("I hold no written procedure for taking a "
                      "turn, so I cannot take one.")
    said, ground = load()
    qm = F.mask(question, learn=False)
    # a thin thing leans on the thread — the knowledge says so, and
    # the thread is what leaning means here
    words = question
    if bin(qm).count("1") < 3 and ground:
        words = question + " " + " ".join(F.words_of(ground)[:14])
    st = dict(words=words, limit=10, marked=set(said),
              other_white=ground, items=None)
    st, err = I.follow(rule, st)
    if err:
        return None, err
    line = (st.get("said") or [None])[0]
    if not line:
        save(said, ground | qm)
        return None, None
    said.add(line)
    for e in (st.get("items") or []):
        ground |= e["color"]
    save(said, ground | qm)
    return line, None
