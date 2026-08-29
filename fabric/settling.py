"""THE RIBBON, PROPERLY — settling instead of searching.

Everything before this searched: split the sentence into words,
walk the entries, keep the ones that share letters, rank them,
take the top. That is a program stepping through a list, and it
is the reason a question about bread came back about caching.

This does not search. A ribbon carries data in, is laid across
both sheets at once, and the whole fabric responds in a single
operation. Entries the walls close go dark. What stays lit feeds
back into the ribbon, so the ribbon picks up knowledge as it
crosses, and that changed ribbon is laid down again. It repeats
until it stops changing. Where it comes to rest IS the answer,
and where it rests is also what the question was about — the
reaching is not a separate step because there is no reaching.

Nothing here selects, ranks, or decides. There is one loop and
it is the settling; every pass is one product over the entire
fabric, which is what a crystal does with one pass of light.

  the two sheets   POSSIBLE — what each entry says stands
                   IMPOSSIBLE — what each entry's wall forbids
  the ribbon       a vector over the same words: the data it
                   carries plus whatever it has picked up
  a settling pass  lit = POSSIBLE·ribbon - IMPOSSIBLE·ribbon
                   ribbon = ribbon + POSSIBLEᵀ·lit
  no end           the ribbon is never finished; when the sheets
                   change it settles again, and its answer with it
"""
import os, sys, math
import numpy as np
BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)
import core

class Field:
    """The whole fabric as two sheets that can be met at once."""

    def __init__(self):
        self.built_for = None
        self.build()

    def build(self):
        F = core.fabric()
        n, v = len(F.entries), len(F.words)
        self.F, self.n, self.v = F, n, v
        # weight a word by how rare it is across the fabric: a word
        # in everything carries no news (the information law), and
        # this is the whole of the weighting — no hand-set numbers
        self.w = np.zeros(v, dtype=np.float32)
        for i in range(v):
            d = F.df.get(i, 0)
            self.w[i] = math.log(n / d) if d else 0.0
        self.P = np.zeros((n, v), dtype=np.float32)   # what stands
        self.W = np.zeros((n, v), dtype=np.float32)   # what forbids
        for e in F.entries:
            for i in bits(e["color"] | e["askm"]):
                self.P[e["id"], i] = self.w[i]
            for i in bits(e["white"]):
                self.W[e["id"], i] = self.w[i]
        # an entry's own strength, so long entries do not shout
        pn = np.linalg.norm(self.P, axis=1); pn[pn == 0] = 1
        self.P /= pn[:, None]
        wn = np.linalg.norm(self.W, axis=1); wn[wn == 0] = 1
        self.W /= wn[:, None]
        self.built_for = F.sig

    def fresh(self):
        if core.fabric().sig != self.built_for: self.build()
        return self

def bits(mask):
    i = 0
    while mask:
        if mask & 1: yield i
        mask >>= 1; i += 1

class Ribbon:
    """A question, an observer, and the thing that computes. It
    carries data, has no end, and settles again whenever the
    sheets move."""

    def __init__(self, field, said=""):
        self.f = field
        self.carried = np.zeros(field.v, dtype=np.float32)
        self.lit = np.zeros(field.n, dtype=np.float32)
        self.dark = np.zeros(field.n, dtype=np.float32)
        self.age = 0
        self.data = []
        if said: self.take(said)

    def take(self, said):
        """Data rides in on the ribbon. It is never written into
        the sheets."""
        self.data.append(said)
        v = np.zeros(self.f.v, dtype=np.float32)
        for i in bits(self.f.F.mask(said, learn=False)):
            v[i] = self.f.w[i]
        nrm = np.linalg.norm(v)
        if nrm: v /= nrm
        self.carried = self.carried * 0.5 + v      # newest weighs most
        return self

    def settle(self, passes=8, feed=0.55, wall=1.0, keep=0.72):
        """Lay the ribbon across both sheets. Every entry answers
        in the same instant; the walls darken what they forbid;
        what stays lit feeds back and the ribbon is laid down
        again. Repeat until it stops moving."""
        r = self.carried.copy()
        prev = None
        for p in range(passes):
            self.age += 1
            excite = self.f.P @ r                  # all at once
            forbid = self.f.W @ r                  # all at once
            lit = excite - wall * forbid
            np.maximum(lit, 0.0, out=lit)
            m = lit.max()
            if m > 0: lit /= m
            lit[lit < 0.25] = 0.0                  # what does not hold
            # what is lit must compete: each entry's own strength
            # is set against the whole lit crowd, so a large
            # neighbourhood cannot win by size alone. Without this
            # the ribbon slides into whatever part of the fabric
            # is densest instead of the part that fits.
            if lit.any():
                lit = lit ** 2
                lit /= lit.sum()
            back = self.f.P.T @ lit                # picked up crossing
            bn = np.linalg.norm(back)
            if bn: back /= bn
            r = keep * r + feed * back
            rn = np.linalg.norm(r)
            if rn: r /= rn
            if prev is not None and float(np.dot(r, prev)) > 0.9995:
                break
            prev = r.copy()
        self.carried = r
        self.lit = lit
        self.dark = np.maximum(wall * forbid - excite, 0.0)
        return self

    def standing(self, n=5):
        """What the ribbon is resting on — its coloured patches."""
        idx = np.argsort(-self.lit)[:n]
        return [(float(self.lit[i]), self.f.F.entries[i])
                for i in idx if self.lit[i] > 0]

    def closed(self, n=3):
        """What darkened it — its white patches."""
        idx = np.argsort(-self.dark)[:n]
        return [(float(self.dark[i]), self.f.F.entries[i])
                for i in idx if self.dark[i] > 0]

    def width(self):
        return int((self.lit > 0).sum())

FIELD = None
def field():
    global FIELD
    if FIELD is None: FIELD = Field()
    return FIELD.fresh()

if __name__ == "__main__":
    f = field()
    print(f"fabric as a field: {f.n} entries x {f.v} words")
    for q in sys.argv[1:]:
        r = Ribbon(f, q).settle()
        print(f"\nRIBBON: {q}")
        print(f"  settled after {r.age} passes, width {r.width()}")
        for s, e in r.standing(3):
            print(f"    {s:.2f} ({e['field']}) {e['essence'][:88]}")
