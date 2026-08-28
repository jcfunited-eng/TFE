"""LIVING RIBBONS — the part that actually moves.

A ribbon is a question, an observer, and a thing with a shape,
all one. Until now mine were computed on demand and thrown away.
Here they persist, they drift, they touch each other, and they
decay — and all of it happens on the beat, whether or not anyone
is asking.

Every step is discrete and cheap: a ribbon is a handful of
integers and two bitmasks, and a beat moves a bounded number of
them. No model is consulted here or anywhere beneath.

  state per ribbon
    color   bitmask — what it carries as standing
    white   bitmask — what it carries as closed
    width   how many makings still stand at its current reach
    drift   +1 toward the coloured sheet, -1 toward the white
    heat    how recently it has been touched; cools every beat
    age     beats lived

  a beat, for one ribbon
    1. reach a little further into the knowledge
    2. let the laws close what they close  (bitwise)
    3. width and drift follow from what survived
    4. if it has narrowed to nothing for long enough it settles
       into the white sheet; if fully coloured and quiet, it
       settles into the coloured one — either way it leaves the
       living set and its shape is kept
"""
import os, sys, json, time, random
BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)
import core

STATE = os.path.join(BASE, "life", "living_ribbons.json")
SETTLED = os.path.join(BASE, "life", "settled_ribbons.md")

COOL = 0.98
SETTLE_WHITE_AFTER = 6      # beats at zero width
SETTLE_COLOR_AFTER = 8      # beats wide and unchanged
MAX_LIVING = 60             # practical ceiling

class Ribbon:
    __slots__ = ("q", "color", "white", "width", "drift", "heat",
                 "age", "flat", "dry", "reach_n", "born")

    def __init__(self, q, born=0):
        self.q = q
        self.color = 0
        self.white = 0
        self.width = 0
        self.drift = 0
        self.heat = 1.0
        self.age = 0
        self.flat = 0
        self.dry = 0
        self.reach_n = 4
        self.born = born

    def to_json(self):
        return dict(q=self.q, color=str(self.color),
                    white=str(self.white), width=self.width,
                    drift=self.drift, heat=round(self.heat, 3),
                    age=self.age, flat=self.flat, dry=self.dry,
                    reach_n=self.reach_n, born=self.born)

    @staticmethod
    def from_json(d):
        r = Ribbon(d["q"], d.get("born", 0))
        r.color = int(d["color"]); r.white = int(d["white"])
        r.width = d["width"]; r.drift = d["drift"]
        r.heat = d["heat"]; r.age = d["age"]
        r.flat = d.get("flat", 0); r.dry = d.get("dry", 0)
        r.reach_n = d.get("reach_n", 4)
        return r

def step(F, r):
    """One beat of one ribbon. Bounded work, all bitwise."""
    qm, es = F.reach(r.q, limit=r.reach_n)
    stood = 0
    color_new, white_new = r.color, r.white
    for e in es:
        pool = qm | e["color"] | r.color
        L = F.judge(pool)
        if L is None:
            stood += 1
            color_new |= e["color"]
        else:
            white_new |= L["a"] | L["b"]
    prev = r.width
    r.width = stood
    r.color, r.white = color_new, white_new
    r.drift = 1 if stood > 0 and stood >= prev else -1
    r.age += 1
    r.heat *= COOL
    r.dry = r.dry + 1 if stood == 0 else 0
    r.flat = r.flat + 1 if stood == prev else 0
    # a ribbon that still stands reaches a little further next beat
    if stood and r.reach_n < 14: r.reach_n += 1
    return r

def touch(a, b):
    """Where two ribbons meet. Returns an event or None."""
    if a.color & b.white:
        return ("opening", a.q, b.q, a.color & b.white)
    if b.color & a.white:
        return ("opening", b.q, a.q, b.color & a.white)
    shared = a.white & b.white
    if bin(shared).count("1") >= 3:
        return ("shared wall", a.q, b.q, shared)
    shared = a.color & b.color
    if bin(shared).count("1") >= 5:
        return ("crossing", a.q, b.q, shared)
    return None

class Life:
    def __init__(self):
        self.ribbons = []
        self.beat = 0
        self.load()

    def load(self):
        if not os.path.exists(STATE): return
        try:
            d = json.load(open(STATE))
            self.beat = d.get("beat", 0)
            self.ribbons = [Ribbon.from_json(x)
                            for x in d.get("ribbons", [])]
        except Exception:
            self.ribbons = []

    def save(self):
        tmp = STATE + ".tmp"
        json.dump(dict(beat=self.beat,
                       ribbons=[r.to_json() for r in self.ribbons]),
                  open(tmp, "w"))
        os.replace(tmp, STATE)

    def add(self, q):
        if any(r.q == q for r in self.ribbons): return False
        if len(self.ribbons) >= MAX_LIVING: return False
        self.ribbons.append(Ribbon(q, born=self.beat))
        return True

    def settle(self, F):
        """Ribbons leave the living set two ways, and both are the
        sheets taking them back."""
        keep, gone = [], []
        for r in self.ribbons:
            if r.dry >= SETTLE_WHITE_AFTER:
                gone.append((r, "white"))
            elif r.flat >= SETTLE_COLOR_AFTER and r.width > 0:
                gone.append((r, "colored"))
            else:
                keep.append(r)
        self.ribbons = keep
        if gone:
            with open(SETTLED, "a") as f:
                for r, where in gone:
                    f.write(f"\nSETTLED into the {where} sheet after "
                            f"{r.age} beats: {r.q}\n"
                            f"  final width {r.width}, carried "
                            f"{bin(r.color).count('1')} coloured and "
                            f"{bin(r.white).count('1')} white marks\n")
        return gone

    def beat_once(self, F, work=6):
        self.beat += 1
        live = sorted(self.ribbons, key=lambda r: -r.heat)[:work]
        for r in live:
            step(F, r)
        events = []
        for i, a in enumerate(live):
            for b in live[i+1:]:
                ev = touch(a, b)
                if ev: events.append(ev)
        gone = self.settle(F)
        return events, gone
