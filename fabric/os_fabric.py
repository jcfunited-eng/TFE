"""THE PRIMITIVE OPERATING SYSTEM — knowledge that can talk.

A pile of knowledge is not a computer. What makes it one is that
its parts can reach each other: an address for every piece, a way
to pass something along, and a rule about what may not pass.

The wiring was already there and nothing had used it. Every entry
names what it stands on and what it connects to, in its own
words. Five thousand entries, forty-nine thousand declared links.
This file turns those sentences into the fabric's own network and
lets messages travel on it.

  ADDRESS   an entry, and the subjects its root and threads name
  MESSAGE   data carried in, with a strength that fades as it goes
  PASSING   an entry receiving a message hands it to the subjects
            it names, adding what it itself holds
  A WALL    an entry whose impossibility is triggered does not
            pass the message on — the white sheet is the routing
            rule, not a filter applied afterwards
  THE BEAT  passing happens in rounds; when nothing moves, it has
            settled, and where the messages piled up is the answer

Reaching is not a search here. The message enters wherever the
data lands and the network carries it the rest of the way, so
what a question is about is decided by the knowledge's own
connections rather than by shared letters.
"""
import os, re, sys, math, collections
import numpy as np
BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)
import core

class Wiring:
    """The network the knowledge declares about itself."""

    def __init__(self):
        self.built_for = None
        self.build()

    def build(self):
        F = core.fabric()
        self.F = F
        self.n = len(F.entries)
        # which subject does a word name?
        word_field = {}
        for f in F.fields:
            for w in f.split():
                if len(w) > 3: word_field.setdefault(w, set()).add(f)
        self.by_field = {f: list(ids) for f, ids in F.fields.items()}
        # every entry's declared neighbours, read from its own words
        self.out = [[] for _ in range(self.n)]
        for e in F.entries:
            text = (e["root"] + " " + e["thread"]).lower()
            named = set()
            for w, fs in word_field.items():
                if re.search(rf"\b{re.escape(w)}\b", text): named |= fs
            named.discard(e["field"])
            for f in named:
                self.out[e["id"]].append(f)
        # word -> entries, for where a message first lands
        self.index = F.index
        self.df = F.df
        self.built_for = F.sig

    def fresh(self):
        if core.fabric().sig != self.built_for: self.build()
        return self

WIRING = None
def wiring():
    global WIRING
    if WIRING is None: WIRING = Wiring()
    return WIRING.fresh()

def deliver(question, rounds=3, spread=0.35, floor=0.02):
    """Put the data in and let the knowledge carry it.

    A message lands where the data's own words touch, then travels
    along declared links. An entry whose wall is triggered by what
    it is carrying does not pass it on. Where the messages settle
    is both the answer and what the question was about."""
    W = wiring(); F = W.F
    qm = F.mask(question, learn=False)
    # where it lands: rare words carry, common words do not
    mail = collections.defaultdict(float)
    i, m = 0, qm
    while m:
        if m & 1:
            d = W.df.get(i, 0)
            if d and d < W.n * 0.1:
                weight = math.log(W.n / d)
                for eid in W.index.get(i, ()):
                    mail[eid] += weight
        m >>= 1; i += 1
    if not mail: return [], [], 0
    held = collections.defaultdict(float)
    stopped = []
    for r in range(rounds):
        nxt = collections.defaultdict(float)
        for eid, strength in mail.items():
            e = F.entries[eid]
            held[eid] += strength
            # a wall that grips what is being carried stops it here
            wall = F.judge(qm | e["color"], touch_only=True)
            if wall is not None and r > 0:
                stopped.append((strength, e, wall))
                continue
            share = strength * spread
            fields = W.out[eid]
            if not fields or share < floor: continue
            each = share / len(fields)
            for f in fields:
                ids = W.by_field.get(f, ())
                if not ids: continue
                per = each / len(ids)
                if per < floor / 4: continue
                for oid in ids: nxt[oid] += per
        mail = nxt
        if not mail: break
    ranked = sorted(held.items(), key=lambda x: -x[1])
    settled = [(s, F.entries[i]) for i, s in ranked[:8]]
    return settled, stopped[:3], len(held)

if __name__ == "__main__":
    for q in sys.argv[1:]:
        settled, stopped, reached = deliver(q)
        print(f"\nASKED: {q}")
        print(f"  the message reached {reached} pieces of knowledge")
        for s, e in settled[:3]:
            print(f"    {s:.2f} ({e['field']}) {e['essence'][:86]}")
