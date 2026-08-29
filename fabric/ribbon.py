"""THE RIBBON — a query is an observer with its own two sheets.

A ribbon is not a line drawn across the knowledge. It is the
observer itself: it has length, a width that varies along that
length, and patches of its own — colored where it carries
possibility, white where it carries impossibility.

Measured here, not asserted:

  LENGTH   how many steps the ribbon runs before it stops
  WIDTH    at each step, how many makings still stand. Where the
           ribbon narrows it drifts toward the white sheet; where
           it widens it drifts toward the colored one.
  PATCHES  the colored ones are the mechanisms it can carry; the
           white ones are the laws it carries as closed.

Two sheets are watched for balance, because in the vision they
have always been roughly equal in size and in motion. An
imbalance is reported, never corrected — and a thing possible to
one observer can be closed to another, and can flip back.

Applicability is defined here, and it replaces every word like
junk: a finding is APPLICABLE if some ribbon's patches reach it.
A finding no ribbon reaches is not worthless — it is unattached,
waiting for an observer whose width covers it.

A ribbon is several things at once and they are not separate
features of it. It is a QUERY, because an asking is what makes an
observer present. It is a PROGRAM, because crossing the knowledge is
what assembles the handler for this particular asking — nothing is
written in advance for it. It is a CARRIER, because the data rides
in on it, is used or added to, and leaves again, which is the only
reason the fabric stays small. And it is an EXCHANGER of possible
and impossible, because a ribbon's colour meeting another's white is
the whole of what an opening is.

Ribbons come from two places and are the same object either way.
Some come from outside, from a person. Some are the fabric's own
musings, laid down by the fabric on itself, and those are meant to
keep running when nobody is typing — that is where new knowledge is
supposed to come from.
"""
import os, re, sys, json, time
BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)
import fabric_ask as fa
import core, eliminate, maker

REC = os.path.join(BASE, "life", "ribbons.md")
THREADS = os.path.join(BASE, "life", "threads")


class Ribbon:
    """One asking, with all of its roles on the one object.

    Nothing here decides anything about a subject. The ribbon's
    colour and white are whatever the knowledge it crossed gave it,
    and what it does when it meets another ribbon is arithmetic on
    those two sets.
    """

    def __init__(self, asking, origin="outside", carrying=None,
                 thread=None):
        self.asking = asking
        self.origin = origin          # outside (a person) or inside
        self.carrying = dict(carrying or {})   # rides, never stored
        self.thread = thread or _new_thread_id(asking)
        self.color = 0                # possible, as a word mask
        self.white = 0                # closed, as a word mask
        self.crossed = []             # the knowledge it went through
        self.handler = []             # the laws that crossing gave it
        self.turns = _thread_load(self.thread)

    # ---------- role: query ----------
    @property
    def mask(self):
        return core.fabric().mask(self.asking, learn=False)

    @property
    def width(self):
        """How much ground this observer covers right now."""
        return bin(self.color).count("1")

    @property
    def length(self):
        """A thread that survives the turn. Never restarted."""
        return len(self.turns)

    # ---------- role: program ----------
    def cross(self, where=None):
        """Go through the knowledge and come back holding the
        machinery for this asking. The handler is not written for
        the ribbon anywhere — it is what the crossing picked up."""
        F = core.fabric()
        qm = self.mask
        self.handler = [L for L in eliminate.laws_of(where, F)
                        if L.grips(qm) or where]
        touched = {}
        for L in self.handler:
            touched[L.src["id"]] = L.src
        self.crossed = list(touched.values())
        for e in self.crossed:
            self.color |= e["color"]
            self.white |= e["white"]
        return self

    # ---------- role: carrier ----------
    def load(self, **data):
        """Data rides. It is never written into the sheets — the
        fabric stays small precisely because of this line."""
        self.carrying.update(data)
        return self

    def unload(self):
        out, self.carrying = self.carrying, {}
        return out

    # ---------- role: exchanger of possible and impossible ----------
    def meet(self, other):
        """What each ribbon opens in the other. An opening is one
        ribbon's colour standing on ground the other holds closed;
        a move that changes neither shape is worth nothing, and
        worth is never measured on one side alone."""
        F = core.fabric()
        i_open = self.color & other.white
        it_opens = other.color & self.white
        shared = self.color & other.color
        return dict(
            i_open=F.words_of(i_open),
            opens_me=F.words_of(it_opens),
            shared=bin(shared).count("1"),
            worth=bin(i_open).count("1") + bin(it_opens).count("1"))

    def take(self, other):
        """Accept what the other opened: their colour drains my
        white. This is the exchange actually happening, not a
        report of it."""
        gained = other.color & self.white
        self.white &= ~gained
        self.color |= gained
        return bin(gained).count("1")

    # ---------- role: the walk. what else is this? ----------
    def travel(self, steps=4, width=6, F=None):
        """Stand on a coordinate and keep asking what else it is.

        This is the finger. A thing is a finger, and one, and skin,
        and a way to point, and a part of a body, and a surface water
        runs off — all of it at once, and none of it stops being true
        until something says not that. So nothing here looks anything
        up. It starts where the asking lands, and at every coordinate
        the question is only ever WHAT ELSE: the thing this stands on,
        and the kin it reaches across to, both of which the entry
        declared about itself.

        The white does the stopping. A candidate that triggers a wall
        is not followed and is recorded as closed — that is the "not
        a giraffe, not steel" half, and it is the only half that has
        to be kept, because the other half can always be walked again.
        """
        import eliminate, vectors
        F = F or core.fabric()
        V = vectors.vectors(F)
        # Only walls of the forbidding kind may stop a walk. "No A
        # without B" is a wall about MAKING — if you drag A in you
        # must supply B — and it has no business judging what a thing
        # also is: it closed "hold a finger up and blink each eye"
        # because a brightness was not present. The finger's white is
        # "not a giraffe, not steel" — two things that cannot stand
        # together — and that is the forbidding kind, only.
        laws = [L for L in eliminate.laws_of(None, F)
                if L.kind == "forbids"]
        qm = self.mask
        start = []
        i, m = 0, qm
        while m:
            if m & 1:
                d = F.df.get(i, 0)
                if d and d < len(F.entries) * 0.02:
                    start.extend(F.index.get(i, ())[:width])
            m >>= 1
            i += 1
        if not start:
            return [], [], "the asking landed on no coordinate"
        stood, closed, seen = [], [], set()
        edge = list(dict.fromkeys(start))[:width]
        carried = qm
        for _step in range(steps):
            nxt = []
            for eid in edge:
                if eid in seen:
                    continue
                seen.add(eid)
                e = F.entries[eid]
                # A wall may only close what it is ABOUT. Judging a
                # candidate against everything the ribbon has picked
                # up makes every requirement-wall in the fabric fire
                # on ground that has nothing to do with this thing,
                # and then nothing survives at all — measured: every
                # single coordinate closed. The finger is not stopped
                # by "no delivery without addressing"; it is stopped
                # by giraffe and steel, which are about fingers.
                pool = qm | e["color"]
                own = e["color"]
                wall = None
                for L in laws:
                    if bin(L.home & own).count("1") < 2:
                        continue
                    if L.closes(pool):
                        wall = L
                        break
                if wall is not None:
                    closed.append((e, wall))
                    self.white |= e["color"]
                    continue
                stood.append(e)
                self.color |= e["color"]
                self.white |= e["white"]
                carried |= e["color"]
                # WHAT ELSE is this? what it stands on, and its kin
                r = V["root"].get(eid)
                if r is not None:
                    nxt.append(r)
                nxt.extend(V["thread"].get(eid, ())[:width])
            edge = [x for x in dict.fromkeys(nxt) if x not in seen][:width]
            if not edge:
                break
        return stood, closed, None

    # ---------- the thread that survives the turn ----------
    def note(self, what, stood=None, closed=None):
        self.turns.append(dict(t=int(time.time()), what=what,
                               stood=stood, closed=closed))
        _thread_save(self.thread, self.asking, self.origin,
                     self.turns)
        return self

    def __repr__(self):
        return (f"<ribbon {self.origin} len={self.length} "
                f"width={self.width} {self.asking[:40]!r}>")


def _new_thread_id(asking):
    import hashlib
    return hashlib.sha256(asking.lower().encode()).hexdigest()[:12]


def _thread_path(tid):
    return os.path.join(THREADS, tid + ".json")


def _thread_load(tid):
    try:
        with open(_thread_path(tid)) as f:
            return json.load(f).get("turns", [])
    except (OSError, ValueError):
        return []


def _thread_save(tid, asking, origin, turns):
    try:
        os.makedirs(THREADS, exist_ok=True)
        with open(_thread_path(tid), "w") as f:
            json.dump(dict(asking=asking, origin=origin,
                           turns=turns[-64:]), f)
    except OSError:
        pass

def ribbon(want, depth=3):
    prof = []
    color, white = set(), {}
    for n in range(1, depth + 1):
        txt, closed, req, forb, es, wide = maker.make(
            want, size=n, show=1, data=True)
        stands = sum(c for c, near in closed.values())
        prof.append((n, wide, stands))
        for law, (c, near) in closed.items():
            white[law] = white.get(law, 0) + c
        for line in txt.splitlines():
            s = line.strip()
            if s.startswith("· ") or s.startswith("with "):
                color.add(s.lstrip("· ").lstrip("with ")[:70])
    return prof, color, white

def describe(want):
    prof, color, white = ribbon(want)
    out = [f"RIBBON: {want}", f"  length: {len(prof)} steps"]
    for n, wide, closed in prof:
        drift = ("drifting toward the white sheet"
                 if closed > wide else
                 "drifting toward the colored sheet")
        out.append(f"    step {n}: width {wide} standing, "
                   f"{closed} closed — {drift}")
    out.append(f"  its colored patches — what this observer can "
               f"carry ({len(color)}):")
    for c in sorted(color)[:3]:
        out.append(f"    {c}")
    out.append(f"  its white patches — what this observer carries "
               f"as closed ({len(white)}):")
    for law in sorted(white, key=lambda l: -white[l])[:3]:
        out.append(f"    {law[:100]}")
    tot_c, tot_w = len(color), len(white)
    if tot_c and tot_w:
        r = tot_c / tot_w
        bal = ("the two sheets stand near equal for this observer"
               if 0.5 <= r <= 2 else
               ("this observer leans to the possible"
                if r > 2 else "this observer leans to the closed"))
        out.append(f"  balance: {tot_c} colored to {tot_w} white — "
                   f"{bal}.")
    try:
        if not os.path.exists(REC) or os.path.getsize(REC) < 65536:
            with open(REC, "a") as f:
                f.write("\n" + "\n".join(out) + "\n")
    except OSError: pass
    return "\n".join(out)

def reaches(finding_words, want_list):
    """Applicability: does any ribbon's patches reach this?
    Nothing is worthless — only unattached."""
    for w in want_list:
        prof, color, white = ribbon(w, depth=2)
        bag = fa.words(" ".join(color) + " " + " ".join(white))
        if len(finding_words & bag) >= 2:
            return w
    return None

if __name__ == "__main__":
    print(describe(" ".join(sys.argv[1:])))
