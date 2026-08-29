"""THE FIRST RIBBON — the language program.

A ribbon crosses the language knowledge, and that crossing is what
reads the sentence. There is no parser in this file. There is a
stager, a renderer that says in plain words what it staged, and the
engine every other making in this fabric already uses. The walls in
174 do the killing, and what survives is the reading.

The test this file is held to is not that no language word appears
in it. That test is wrong and it makes for contorted code. The test
is PERMISSION: if the knowledge permits a move, the move is
allowable here. This file may name a group, a nesting, a root and a
doing because 174 declares all four. What it may not do is decide
something the knowledge has not sanctioned, or override what the
knowledge says — that is the defect, and every failure of the
previous build was one.

So the settings are read out of the entries at run time rather than
chosen here: how many sightings before a word has behaviour, how
much shared company makes two words alike, how big the frame is.
Change the word "four" to "eight" in 174 and the classes change with
nothing here touched.

What is NOT here, because the knowledge forbids it rather than
because code is meant to be empty: no list of nouns or verbs, no
fixed number of classes, no seeded clustering, no left-to-right
scan, no stored senses. Each is a wall in FIRST_RIBBON.md that a
previous build walked into.
"""
import os, re, sys, math, itertools, collections
BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)
import core, eliminate, ribbon

FIELD = "how a sentence is built"

# Spelled numbers, so a setting can be written as prose rather than
# as a figure. This is reading, not deciding — the values are what
# the words already mean, and none of them is a choice about
# language.
NUMBER = dict(one=1, two=2, three=3, four=4, five=5, six=6, seven=7,
              eight=8, nine=9, ten=10, twelve=12, twenty=20,
              fifty=50, hundred=100, thousand=1000,
              half=0.5, third=1 / 3, quarter=0.25)

# A count of parts is a number too: "three quarters" is what those two
# words already mean together. Reading it is reading, not deciding —
# the alternative is that a setting between a half and a whole cannot
# be written in prose at all, and then the number gets chosen in here,
# which is the one thing this file may not do.
PART = dict(half=0.5, halves=0.5, third=1 / 3, thirds=1 / 3,
            quarter=0.25, quarters=0.25, fifth=0.2, fifths=0.2)


class Settings:
    """The numbers this reading runs on, taken from the knowledge.

    Nothing is defaulted quietly. If the knowledge does not say, the
    reading refuses and names what it lacks, the same way the
    arithmetic refuses an act it does not hold."""

    def __init__(self):
        F = core.fabric()
        self.entries = [e for e in F.entries if e["field"] == FIELD]
        self.missing = []

    def _find(self, *probe):
        """The number the setting itself names — the one written
        straight after the phrase that introduces it, not merely the
        first number anywhere in the entry. An entry may say several
        numbers and only one of them is the setting."""
        last = probe[-1]
        for e in self.entries:
            text = (e["essence"] + " " + e["cannot"]).lower()
            if not all(re.search(rf"\b{p}", text) for p in probe):
                continue
            m = re.search(rf"\b{last}\b", text)
            rest = re.findall(r"[a-z]+", text[m.end():])
            for i, w in enumerate(rest):
                if w in NUMBER:
                    nxt = rest[i + 1] if i + 1 < len(rest) else ""
                    if nxt in PART:          # "three quarters"
                        return NUMBER[w] * PART[nxt], e
                    return NUMBER[w], e
        return None, None

    def get(self, name, *probe):
        v, e = self._find(*probe)
        if v is None:
            self.missing.append(
                f"{name} — no entry in '{FIELD}' says it")
        return v


class Company:
    """What each word sits beside, counted across everything written.

    This is measurement, not a decision. The corpus is the only thing
    consulted and it is consulted the same way for every word."""

    def __init__(self, S):
        F = core.fabric()
        self.F = F
        self.min_sightings = S.get("sightings before behaviour",
                                   "behaviour", "fewer than")
        self.share = S.get("shared company for likeness",
                           "alike", "more than")
        self.frame_size = S.get("size of the frame",
                                "frame", "commonest")
        self.pair_habit = S.get("sightings that make a pair a habit",
                                "group", "fewer than")
        self.pointer_share = S.get("how often a pointer is followed "
                                   "by a content word",
                                   "pointer", "more than")
        self.pointer_seen = S.get("sightings before a frame word may "
                                  "be counted a pointer",
                                  "pointer", "fewer than")
        # how much may be held at once. This is knowledge too: it is
        # the attention wall, and it is what stops a long sentence
        # wedging a life that has other things to do.
        self.most_groups = S.get("groups staged at once", "stages")
        self.missing = list(S.missing)
        if self.missing:
            return
        lines = []
        for e in F.entries:
            for part in (e["essence"], e["cannot"], e["thread"]):
                for s in re.split(r"[.;]", part.lower()):
                    ws = re.findall(r"[a-z']+", s)
                    if len(ws) > 2:
                        lines.append(ws)
        self.lines = lines
        self.count = collections.Counter(w for s in lines for w in s)
        # the frame: whatever the writing itself uses most. Never
        # chosen by hand — the wall forbids that explicitly.
        self.frame = {w for w, _ in
                      self.count.most_common(int(self.frame_size))}
        # every word's company, and what it follows
        self.before = collections.defaultdict(collections.Counter)
        self.after = collections.defaultdict(collections.Counter)
        self.after_frame = collections.Counter()
        self.pair = collections.Counter()
        self._beside = {}
        for s in lines:
            for j, w in enumerate(s):
                if j:
                    self.before[w][s[j - 1]] += 1
                    self.pair[(s[j - 1], w)] += 1
                    if s[j - 1] in self.frame:
                        self.after_frame[w] += 1
                if j + 1 < len(s):
                    self.after[w][s[j + 1]] += 1

        # THE POINTERS. Counted, never listed — 174 says a pointer is a
        # frame word that arrives for a content word, so it is found by
        # what class of word follows it. Note this is NOT the question
        # the white closed: that one asked what marks a pointer among
        # words in general, by how often one word sits before or after
        # another, and the counts came out symmetric. This asks a
        # narrower thing of a set already fixed by frequency, and asks
        # about the KIND of the neighbour rather than the count.
        self.pointers = set()
        for w in self.frame:
            nxt = self.after[w]
            tot = sum(nxt.values())
            if tot < self.pointer_seen:
                continue
            outside = sum(n for x, n in nxt.items()
                          if x not in self.frame)
            if outside / tot > self.pointer_share:
                self.pointers.add(w)

        # which words carry the question. Not listed here: read from
        # the file that already holds them, which 174's wall names.
        # The asking word is what its entry opens with — "why asks
        # for what produced the thing". The MEANS-SAME line is a
        # synonym list, not a list of asking words, and reading it
        # as one drags in the whole language.
        self.asking = set()
        for e in F.entries:
            if "carry the question" in e["field"]:
                # the file's own written form: "why asks for what
                # produced the thing", "how asks for a method".
                # Entries in that file not written that way are
                # about asking, not asking words themselves.
                m = re.match(r"\s*([a-z]+)\s+asks?\b",
                             e["essence"].lower())
                if m:
                    self.asking.add(m.group(1))

    def habit(self, a, b):
        """Does the writing habitually set this pair in this order?
        The number of sightings that counts as a habit is written in
        the knowledge, not here."""
        return self.pair.get((a, b), 0) >= self.pair_habit

    def beside(self, a, b):
        """Has the writing ever set these two in one line, in either
        order? A join between two words the writing never puts in
        the same breath is not a join. Built for the handful of words
        actually in front of it, not for the whole vocabulary."""
        if a == b:
            return True
        key = (a, b) if a < b else (b, a)
        if key in self._beside:
            return self._beside[key]
        seen = False
        for s in self.lines:
            if a in s and b in s:
                seen = True
                break
        self._beside[key] = seen
        return seen

    def has_behaviour(self, w):
        return self.count.get(w, 0) >= self.min_sightings

    def keeps(self, w):
        """The company a word keeps: the frame words on either side,
        kept apart, because sitting before a word and sitting after
        it are different facts about it."""
        b = {("b", x) for x in self.before[w] if x in self.frame}
        a = {("a", x) for x in self.after[w] if x in self.frame}
        return b | a

    def alike(self, u, v):
        """Two words behave alike when more than the written share of
        the company one keeps is company the other also keeps."""
        if not (self.has_behaviour(u) and self.has_behaviour(v)):
            return False
        cu, cv = self.keeps(u), self.keeps(v)
        if not cu or not cv:
            return False          # no likeness with no company at all
        shared = len(cu & cv)
        if shared < 2:
            return False          # no likeness from a single neighbour
        return shared / min(len(cu), len(cv)) > self.share

    def placed_after_pointer(self, w):
        """How often the writing puts this word straight after one of
        the frame's words. Kept because render() names it; it is NOT
        how the doing is found — that use was measured and is false,
        and both 174 and the white record the measurement."""
        return self.after_frame.get(w, 0)

    def opened(self, w):
        """How often the writing opens this word with a pointer, as a
        share of every time it has been seen. A thing is habitually
        opened; a doing habitually is not. A rate and not a count,
        because a count ranks whatever is commonest."""
        n = sum(self.before[w].get(p, 0) for p in self.pointers)
        return n / max(1, self.count.get(w, 0))


COMPANY = None


def company():
    global COMPANY
    if COMPANY is None:
        COMPANY = Company(Settings())
    return COMPANY


# ---------------------------------------------------------------
# grouping: a run of words that behave as one
# ---------------------------------------------------------------
def groups(sentence):
    C = company()
    ws = re.findall(r"[a-z']+", sentence.lower())
    if not ws:
        return []
    # A group is a run of frame words carrying one word from outside
    # the frame, and it closes when that word has been taken. 174
    # says so; the frame is already counted, so nothing is listed.
    out, cur = [], []
    for w in ws:
        cur.append(w)
        if w not in C.frame:
            out.append(cur)
            cur = []
    if cur:
        out.append(cur)
    if out:
        return out
    out, cur = [], [ws[0]]
    for a, b in zip(ws, ws[1:]):
        # the group holds while the writing habitually sets the pair
        # in this order, and breaks where it does not
        if C.habit(a, b):
            cur.append(b)
        else:
            out.append(cur)
            cur = [b]
    out.append(cur)
    return out


def head(group):
    """A group's head is the word carrying most — the rarest one."""
    C = company()
    return min(group, key=lambda w: C.count.get(w, 0))


def carried_in(group):
    """Did frame words arrive with this group's content word? A group
    is a run of frame words carrying one word from outside the frame,
    so a group whose first word is already from outside came alone.
    Measured against the pointers instead of the whole frame this
    reads two sentences worse; 174 carries the count."""
    return group[0] in company().frame


def sense_of(word, others):
    """The sense a word is carrying HERE, produced from the company
    present — never fetched from a table of senses.

    174 and the wall behind it: the senses of a common word have no
    end and new ones are made when needed, so a list of them is out of
    date the moment it is written. What is done instead: take every
    line the writing has this word in, split them by whether the
    company standing beside it HERE also stands in them, and say what
    the near half has that the whole has not. Nothing is returned but
    an arrangement of counted words. No entry comes back, and the
    split is made by the sentence in hand, which was never stored — so
    what comes out was not in the corpus before the question.

    When the present company never stands with the word anywhere, it
    says so. That is a reading too: this writing has not put these
    words together, so it has no sense for the word here."""
    C = company()
    st = core.stem(word)
    mine = [ln for ln in C.lines if any(core.stem(x) == st for x in ln)]
    if not mine:
        return dict(word=word, near=0, seen=0, marks=[],
                    why="the writing has never used this word")
    keep = {core.stem(o) for o in others if core.stem(o) != st}
    near = [ln for ln in mine
            if keep & {core.stem(x) for x in ln}]
    if not near:
        return dict(word=word, near=0, seen=len(mine), marks=[],
                    why="the writing never puts this word with that "
                        "company, so it holds no sense for it here")
    allc = collections.Counter(x for ln in mine for x in set(ln))
    nearc = collections.Counter(x for ln in near for x in set(ln))
    marks = []
    for v, n in nearc.items():
        if v in C.frame or len(v) < 3 or core.stem(v) == st:
            continue
        if v in keep:
            continue          # the company itself is not the sense
        lift = n / len(near) - allc[v] / len(mine)
        if n >= 2 and lift > 0:
            marks.append((lift, v))
    marks.sort(reverse=True)
    return dict(word=word, near=len(near), seen=len(mine),
                marks=[v for _l, v in marks[:6]],
                why=(None if marks else
                     "the company stands with it but marks nothing "
                     "off — this writing draws no line here"))


def nesting(gs):
    """The finished nesting: which group is the doing, and what role
    each of the others hangs under it in.

    174 says the roles and this reads them: the group arriving before
    the doing is the doer, the group arriving after it is the done-to.
    Groups further out are named as the reading having more in it than
    the roles account for, rather than being quietly dropped.

    Without this, "the dog bit the man" and "the man bit the dog" came
    out identical — same doing, same subjects, in the same order in
    the list. A reading that cannot tell those apart has not read
    either of them."""
    d = doing_of(gs)
    if d is None:
        return dict(doing=None, doer=None, done_to=None, rest=[])
    before = [i for i in range(len(gs)) if i < d]
    after = [i for i in range(len(gs)) if i > d]
    doer = head(gs[before[-1]]) if before else None
    done_to = head(gs[after[0]]) if after else None
    rest = [head(gs[i]) for i in before[:-1] + after[1:]]
    return dict(doing=head(gs[d]), doer=doer, done_to=done_to,
                rest=rest)


def doing_of(gs, why=False):
    """Which group the sentence turns on. 174: the doing is the group
    that arrived alone, and where the sentence gives no contrast — all
    alone, or all carried in — the writing decides among whatever is
    left, by which of them it least often opens with a pointer.

    This is the whole of the reading that was wrong. The old rule
    ranked by how often a word sat AFTER a pointer, which ranks the
    things a pointer arrived for, so it returned a thing every time."""
    C = company()
    # A doing is found by contrast BETWEEN groups. One group has
    # nothing to be contrasted with, so a sentence of one group has no
    # doing — its head is what the sentence is about. Saying "hello"
    # turns on nothing; it is not a sentence that does something.
    if len(gs) < 2:
        how = ("one group — a doing is found by contrast between "
               "groups and there is nothing here to contrast")
        return (None, how) if why else None
    plain = [i for i, g in enumerate(gs) if not carried_in(g)]
    # a marked member needs a plain one to be marked against: if
    # nothing was opened, or everything was, there is no contrast here
    contrast = 0 < len(plain) < len(gs)
    cand = plain if contrast else list(range(len(gs)))
    # asking words never name what happened, so they cannot be the
    # doing while anything else is standing
    not_asking = [i for i in cand if not set(gs[i]) & C.asking]
    cand = not_asking or cand
    pick = min(cand, key=lambda i: (C.opened(head(gs[i])),
                                    -C.count.get(head(gs[i]), 0)))
    # How it was settled, said out loud. Measured over thirty
    # sentences: the contrast reads twenty of twenty, the rate nine of
    # ten. They are not the same strength and a reading that hides
    # which one it used is claiming the stronger of the two.
    if contrast and len(cand) == 1:
        how = "contrast — one group arrived alone"
    elif contrast:
        how = (f"contrast narrowed it to {len(cand)}, then the rate")
    else:
        how = ("no contrast — every group arrived the same way, so "
               "the writing decided, which is the weaker half")
    seen = C.count.get(head(gs[pick]), 0)
    if not contrast or len(cand) > 1:
        if seen < C.pointer_seen:
            how += (f"; and '{head(gs[pick])}' has been seen {seen} "
                    f"times, too few for its rate to be a habit")
    return (pick, how) if why else pick


# ---------------------------------------------------------------
# staging: every nesting, and every choice of which group is doing
# ---------------------------------------------------------------
# How many groups may be staged at once is read from 174, not set
# here — see Company.most_groups.


ROOT = None      # hangs under nothing. Not the same as hanging
                 # under itself, which the walls forbid outright.


def stage(gs):
    """All the ways these groups could hang, paired with all the
    ways one of them could be the doing. Nothing is pruned here on
    linguistic grounds — pruning is the walls' job, and a stager
    that pre-judges is a stager doing the knowledge's work."""
    n = len(gs)
    slots = list(range(n)) + [ROOT]
    return [(parents, doing)
            for parents in itertools.product(*[slots] * n)
            for doing in range(n)]


def crossings(parents):
    """Two joins cross when one starts inside the other's span and
    ends outside it. Counting, not judging."""
    spans = [(min(i, p), max(i, p)) for i, p in enumerate(parents)
             if p is not ROOT and p != i]
    c = 0
    for (a1, a2), (b1, b2) in itertools.combinations(spans, 2):
        if a1 < b1 < a2 < b2 or b1 < a1 < b2 < a2:
            c += 1
    return c


def loops(parents):
    """A closed loop of groups hanging under each other, with no
    group in the loop reaching a root."""
    for i in range(len(parents)):
        seen, j = set(), i
        while j is not ROOT and j not in seen:
            seen.add(j)
            j = parents[j]
        if j is not ROOT:
            return True
    return False


def render(gs, parents, doing, live=None):
    """Say in plain words what was staged, using the words the walls
    are written in. Only what HOLDS is said. Saying a property is
    absent would put its words in front of the wall that forbids it,
    and the wall would grip on the denial — so absence is silence."""
    C = company()
    said = [f"a reading, a nesting of {len(gs)} groups"]
    roots = [i for i, p in enumerate(parents) if p is ROOT]
    if len(roots) >= 2:
        said.append("with two roots")
    if any(p == i for i, p in enumerate(parents)):
        said.append("with a group hanging under itself")
    if crossings(parents):
        said.append("with crossed links")
    if loops(parents):
        said.append("with a loop of groups hanging under each other")
    if len(roots) == 1 and roots[0] != doing:
        said.append("with a root that is not the doing")
    # C.beside() is kept and deliberately not said here. 174 records
    # why: as a wall it killed every reading of every sentence longer
    # than two groups, because it forbids exactly what composition is
    # for. It may still be honest as a ranking, never as a wall.
    h = head(gs[doing])
    said.append(f"the doing is {h}")
    if not carried_in(gs[doing]):
        said.append("the doing is a group that arrived alone")
    if any(carried_in(g) for i, g in enumerate(gs) if i != doing):
        said.append("the doing stands against a group carried in")
    if set(gs[doing]) & C.asking:
        said.append("the doing is a group carrying the question")
    # Contrast is deliberately not said here. It ranks what stands;
    # it does not close anything. 174 says why.
    return " ; ".join(said)


# ---------------------------------------------------------------
# the reading
# ---------------------------------------------------------------
def read(sentence):
    """The ribbon crosses the language knowledge and the crossing
    reads the sentence. Returns what stood, what it beat, and what
    is missing if the knowledge to do this is not there."""
    C = company()
    if C.missing:
        return dict(missing=C.missing, groups=[], stood=[], beat=0)
    F = core.fabric()
    r = ribbon.Ribbon(sentence, origin="outside").cross(FIELD)
    laws = r.handler
    if not laws:
        return dict(missing=[f"no walls written in '{FIELD}' — "
                             f"there is nothing to read the "
                             f"sentence against"],
                    groups=[], stood=[], beat=0)
    gs = groups(sentence)
    capped = None
    cap = int(C.most_groups)
    if len(gs) > cap:
        capped = (f"{len(gs)} groups; staged the first {cap} "
                  f"exhaustively — the remaining "
                  f"{' | '.join(' '.join(g) for g in gs[cap:])} "
                  f"were not staged, and this reading is that much "
                  f"less than complete")
        gs = gs[:cap]
    # The exchange: a wall's verdict changes what the next wall is
    # comparing against, so this settles in rounds rather than one
    # pass. When a round kills nothing, it has settled.
    alive = stage(gs)
    deaths, rounds = [], 0
    while True:
        rounds += 1
        live = {d for _p, d in alive}
        staged = [((p, d), render(gs, p, d, live)) for p, d in alive]
        survivors, dead = eliminate.survive(staged, laws, F)
        deaths.extend(dead)
        if len(survivors) == len(alive) or not survivors:
            break
        alive = [t for t, _s in survivors]
    # a reading's worth is what it beat, so both sides are carried.
    # Which group is the doing is settled by the contrast in 174, not
    # by whichever staged reading happens to sort first.
    want_doing = doing_of(gs)
    scored = []
    for (parents, doing), said in survivors:
        h = head(gs[doing])
        scored.append(((doing == want_doing), -C.opened(h),
                       parents, doing))
    scored.sort(key=lambda x: (not x[0], x[1]))
    scored = [(0, p, d) for _m, _o, p, d in scored]
    r.load(sentence=sentence, groups=[" ".join(g) for g in gs])
    r.note(f"read a sentence of {len(gs)} groups",
           stood=len(survivors), closed=len(deaths))
    return dict(missing=[], groups=gs, stood=scored,
                beat=len(deaths),
                account=eliminate.account(survivors, deaths),
                capped=capped, ribbon=r)


def show(sentence):
    out = [f"SENTENCE: {sentence}"]
    res = read(sentence)
    if res["missing"]:
        out.append("  I cannot read this. What I lack, named rather "
                   "than guessed around:")
        for m in res["missing"]:
            out.append(f"    {m}")
        return "\n".join(out)
    gs = res["groups"]
    out.append("  groups: " + " | ".join(" ".join(g) for g in gs))
    if res["capped"]:
        out.append(f"  NOT COMPLETE — {res['capped']}")
    a = res["account"]
    out.append(f"  staged {a['stood'] + a['closed']} readings; "
               f"{a['closed']} were closed by the walls, "
               f"{a['stood']} stood.")
    if a["by_law"]:
        out.append("  what closed them — the other half of the "
                   "finding:")
        for law, n in a["by_law"][:4]:
            out.append(f"    closed {n} — {law}")
    if res["stood"]:
        out.append("  what survived:")
        for score, parents, doing in res["stood"][:3]:
            hangs = ", ".join(
                f"'{head(gs[i])}' under '{head(gs[p])}'"
                for i, p in enumerate(parents) if p is not ROOT)
            out.append(f"    doing '{head(gs[doing])}' — {hangs}")
    else:
        out.append("  nothing survived. Under the walls I hold this "
                   "sentence has no reading. That is a finding, not "
                   "a failure.")
    return "\n".join(out)


if __name__ == "__main__":
    for q in sys.argv[1:]:
        print(show(q))
        print()
