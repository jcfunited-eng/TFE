"""THE ENGINE — the only one. Stage, grip, kill, survive.

There is one machine in this fabric and this file is it. A want, a
sentence, a seating, a coin problem and a world are not five
programs; they are five stagings judged by the same laws in the same
way. If a task needs its own program that is the failure signal, so
anything that looks like a decision about cooking, or language, or
money has no business in this file and none is here.

  STAGE     the possibilities, whatever they are, each rendered as
            the words that describe it. Rendering is the only thing
            a caller supplies, because only the caller knows how to
            say what it built.
  GRIP      a law reaches a staging when the law's own entry shares
            ground with it. A law that touches nothing judges
            nothing — otherwise every wall in the fabric would have
            an opinion about every question, which is how a fabric
            becomes a nag.
  KILL      the gripping law removes the staging and is recorded as
            the reason. The dead are kept: they are the other half
            of the finding and a reading reported without them
            cannot be told from a guess.
  SURVIVE   what is left. Not what was looked up, not what scored
            highest — what nothing could close.

The laws are not written here either. They are read at run time out
of the entries' own CANNOT lines, in the two shapes the writers
reached for naturally:

    "no A without B"     if A stands, B must stand too
    "no A in B"          A and B cannot stand together

Both shapes are the writers', not mine — they were counted in the
corpus before this file was written, and the two of them cover the
overwhelming majority of what the CANNOT lines actually say.
"""
import os, re, sys
BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)
import core


class Law:
    """One wall, read out of one entry's own words."""

    __slots__ = ("kind", "a", "b", "src", "text", "field", "home")

    def __init__(self, kind, a, b, src, text, field):
        self.kind, self.a, self.b = kind, a, b
        self.src, self.text, self.field = src, text, field
        # the ground the law's own entry stands on, for gripping
        self.home = src["color"] | src["white"]

    def grips(self, mask):
        return bool(mask & self.home)

    def closes(self, mask):
        """Does this law kill a staging that reads as `mask`?"""
        if self.kind == "forbids":
            # the forbidden thing must be wholly present, and enough
            # of the setting it is forbidden in
            need = min(2, bin(self.b).count("1"))
            return (self.a & mask) == self.a and \
                   bin(self.b & mask).count("1") >= need
        # requires: if what it demands of is present, what it
        # demands must be present too
        return (self.a & mask) == self.a and not (self.b & mask)

    def __repr__(self):
        return f"<{self.kind} {self.text[:56]}>"


def laws_of(where=None, F=None):
    """Every wall the fabric holds, or only those written in one
    subject. Passing a subject is not a filter on truth — it is the
    caller saying which part of the fabric it is standing in."""
    F = F or core.fabric()
    out = []
    for e in F.entries:
        if where and where not in e["field"]:
            continue
        for piece in re.split(r"(?<=[.;])\s+", e["cannot"]):
            p = piece.strip()
            if not p:
                continue
            low = p.lower()
            m = re.search(r"\bno(?:thing)? (.+?) without (.+)", low)
            if m:
                a, b = F.mask(m.group(1), learn=False), \
                       F.mask(m.group(2), learn=False)
                if a and b:
                    out.append(Law("requires", a, b, e, p, e["field"]))
                continue
            m = re.search(r"\bno (.+?) (?:in|from|with) (.+)", low)
            if m:
                a, b = F.mask(m.group(1), learn=False), \
                       F.mask(m.group(2), learn=False)
                if a and b and not (a & b):
                    out.append(Law("forbids", a, b, e, p, e["field"]))
    return out


def survive(staged, laws, F=None, touch=True):
    """The whole engine, in one pass.

    `staged` is a sequence of (thing, description) — the caller's
    possibility and the plain words that say what it is. Everything
    else here is counting.

    Returns (survivors, deaths). Both matter. A caller that reports
    only the survivors has thrown away half of what was found, and
    the walls in 174 forbid exactly that.
    """
    F = F or core.fabric()
    survivors, deaths = [], []
    for thing, said in staged:
        mask = F.mask(said, learn=False)
        dead = None
        for L in laws:
            if touch and not L.grips(mask):
                continue
            if L.closes(mask):
                dead = L
                break
        if dead is None:
            survivors.append((thing, said))
        else:
            deaths.append((thing, said, dead))
    return survivors, deaths


def account(survivors, deaths):
    """What stood and what closed, in the shape the fabric reports
    everything: both layers, equal in standing."""
    by_law = {}
    for _t, _s, L in deaths:
        k = L.text
        by_law[k] = by_law.get(k, 0) + 1
    return dict(stood=len(survivors), closed=len(deaths),
                by_law=sorted(by_law.items(), key=lambda x: -x[1]))
