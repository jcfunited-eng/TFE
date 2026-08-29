"""SAYING SOMETHING BACK — a turn made, not fetched.

talk.py holds a thread and then says the fabric's own sentences at
you. Its docstring admits it: "it answers in the fabric's own
sentences rather than in ones composed for you." That is retrieval
with a thread attached, and typing "hello" at it got a lecture about
greetings.

This is the other thing. A turn here is an ARRANGEMENT OF MOVES. The
moves are staged — all of them, every turn — and the reading kills
the ones that do not apply. What survives is said, in order. No move
is an entry, and an arrangement of moves is not a member of the move
list, so what comes out was not stored anywhere. That is the drain
the white already names for stored procedures: knowledge constraining
an act rather than prescribing one.

The difference from the greeting rule that was condemned: that rule
said "when greeting, do this", one situation at a time, and
generalised to nothing. These moves say nothing about situations.
Each one names a condition on the READING — is there a subject, was
something forbidden, did it ask for a method, is this the same
subject as last turn — and the situation is whatever combination
survives. Fifteen moves that each fire or do not give many more turns
than fifteen.

HAND-WRITING IS FORBIDDEN. Every sentence this file used to say was
written by me — "near enough everything X keeps company with" — so
the parts were the fabric's and the English was mine, which makes the
turn my voice wearing its findings. None of that is left. A turn now
emits only two things: TERMS, which are the words 174 and 74 use for
the parts of a reading and are read out of those entries at run time,
and WORDS, which are what the reading and the assembly produced.
Delete the entries and the terms go with them.

It reads terse because the fabric has no prose of its own yet. That is
the true state and it is better than borrowing mine.
"""


def terms(F):
    """The fabric's own words for the parts of a reading, read from
    the entries that define them rather than typed here."""
    out = set()
    for e in F.entries:
        if e["field"] not in ("how a sentence is built",
                              "cognitive syntax"):
            continue
        m = re.match(r"\s*(?:a|an|the)\s+([a-z][a-z-]*)\s+"
                     r"(?:is|holds|hangs|says|leans|carries)",
                     e["essence"].lower())
        if m:
            out.add(m.group(1))
        for w in ("doer", "done-to", "ground", "chunk", "joint"):
            if w in e["essence"].lower():
                out.add(w)
    return out
import os, re, sys
BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)
import core, wanting, first_ribbon as FR


def no_subject_words(F):
    """The words the knowledge itself says carry no subject.

    This is the correction Joe made, built rather than restated. The
    fabric holds an entry saying a greeting carries no subject at all,
    naming its own words, and saying that hunting for the subject of
    one finds whatever is nearest and is wrong every time. Typing
    "hello" made the fabric find that entry and PRINT IT — it had the
    knowledge of how to handle a greeting and used it as an answer
    about greetings.

    Using it means the entry becomes the HANDLER: its words are read
    out of it, and when one of them arrives the subject hunt is closed
    because the entry says to close it. Nothing here is hand-listed —
    delete the entry and this goes empty."""
    out = set()
    for e in F.entries:
        low = e["essence"].lower()
        if "carries no subject" not in low:
            continue
        # the entry names its own words, in the sentence after the one
        # that makes the claim
        for part in re.split(r"[.\u2014]", e["essence"]):
            ws = [w.strip().lower() for w in part.split(",")]
            if len(ws) >= 3 and all(len(w.split()) <= 3 and w
                                    for w in ws):
                out |= {w for w in ws if w.isalpha()}
    return out


def thin_words(F):
    """The words the knowledge says carry no ground of their own.

    74 holds it already and nothing used it: "a thin thing said leans
    on the thread — why? or that or and? carry almost no ground of
    their own, so they take up the ground the thread is already
    standing on." The entry names those words on its own ASKED-AS
    line, so they are read out of it rather than listed here. Same
    move as the greeting: the entry that says how to handle a thing
    becomes the handler for it."""
    for e in F.entries:
        if "leans on the thread" in e["essence"].lower():
            return {w for w in re.findall(r"[a-z]+", e["ask"].lower())
                    if len(w) > 1}
    return set()


class Said:
    """What one turn understood, and what the thread was standing on
    before it. Everything a move may test lives here — a move never
    looks at the raw words, because then it is matching strings."""

    def __init__(self, text, thread, F):
        self.text = text.strip()
        self.F = F
        self.w = wanting.want(self.text, F)
        self.no_subject = self.text.lower().strip(" .!?") in \
            thread.no_subject
        self.unread = self.w.get("unread")
        # the subject is the ABOUT word carrying most — the rarest.
        # Taking the first made "how do I sharpen a knife" a
        # conversation about "I".
        ab = [] if (self.unread or self.no_subject) else self.w["about"]
        C = FR.company()
        self.subject = (min(ab, key=lambda w: C.count.get(w, 0))
                        if ab else None)
        self.about = ([] if (self.unread or self.no_subject)
                      else self.w["about"])
        self.turns_on = None if self.unread else self.w["turns_on"]
        self.kind = None if self.unread else self.w["kind"]
        self.asked_with = None if self.unread else self.w["asked_with"]
        self.forbidden = [] if self.unread else self.w["forbidden"]
        self.settled_by = None if self.unread else self.w.get("settled_by")
        self.doer = None if self.unread else self.w.get("doer")
        self.done_to = None if self.unread else self.w.get("done_to")
        self.senses = {} if self.unread else (self.w.get("senses") or {})
        self.guessing = bool(self.settled_by
                             and "no contrast" in self.settled_by)
        # Does the writing reach this subject at all? Presence, not
        # selection: this asks whether there is any ground under the
        # subject, and it does not choose an entry or rank one.
        # Ground means the writing stands on THIS SUBJECT, not that it
        # shares a word with the question. Any-overlap offered a gene
        # entry for "cake", because both mention a cake recipe.
        self.ground = []
        if self.subject:
            sid = F.vocab.get(core.stem(self.subject))
            if sid is not None:
                bit = 1 << sid
                _qm, hits = F.reach(self.subject, limit=12)
                # An entry's ASKED-AS line is the entry saying what it
                # is about. Requiring the subject there is the entry's
                # own declaration doing the work; requiring it merely
                # in the essence offered a gene entry for "cake",
                # because that entry mentions a cake recipe in passing.
                self.ground = [e for e in hits
                               if (e["askm"] & bit) and (e["color"] & bit)]
                # NO FALLBACK. Loosening this when nothing declares
                # the subject is improving which entry comes back,
                # which is retrieval by definition — and reaching for
                # the nearest thing returned an onion entry for a
                # question about knives. Holding nothing is a lawful
                # answer and a true one.
        # A THIN TURN. It has a thin word in it and no ground of its
        # own, so by 74 it takes up the ground the thread is already
        # standing on. Without this, "why" after a turn about bread
        # was read as a new sentence about nothing and got silence.
        # A turn is thin when it has a thin word AND brings no word of
        # its own. Testing only for a thin word made "what is a quork"
        # lean on the thread, because "what" is thin — but "quork" is
        # the turn's own word and having no ground for it is a finding
        # about quork, not a reason to talk about something else.
        C0 = FR.company()
        low = set(re.findall(r"[a-z]+", self.text.lower()))
        own = [x for x in low
               if x not in thread.thin and x not in C0.frame]
        self.thin = bool(low & thread.thin) and not own
        self.leaned = None
        if self.thin and thread.subject:
            self.leaned = thread.subject
            self.subject = thread.subject
            self.about = [thread.subject]
            # a thin turn takes up the ground the thread stands on,
            # which is the subject AND what was being done to it —
            # without the doing there is only one part and nothing to
            # put together
            self.doer = thread.subject
            self.turns_on = thread.last_doing
            sid = F.vocab.get(core.stem(thread.subject))
            if sid is not None:
                bit = 1 << sid
                _qm, hits = F.reach(thread.subject, limit=12)
                self.ground = [e for e in hits
                               if (e["askm"] & bit) and (e["color"] & bit)]
        self.thread = thread
        self.same_subject = bool(
            thread.subject and self.subject
            and core.stem(thread.subject) == core.stem(self.subject))
        self.new_subject = bool(self.subject and not self.same_subject)


class Thread:
    """One conversation. What it is standing on, and what has been
    said, so nothing is said twice and a thin turn has something to
    lean on."""

    def __init__(self, F=None):
        self.F = F or core.fabric()
        self.subject = None
        self.turns = 0
        self.spoken = []
        self.offered = set()      # entries already read out
        self.greeted = False
        self.greeted_on = None
        self.no_subject = no_subject_words(self.F)
        self.thin = thin_words(self.F)
        self.last_asked_for = None
        self.last_doing = None
        self.met = set()
        self.terms = terms(self.F)

    # ---------- the moves ----------
    # Each returns (TERM, WORDS) or None. The term is the fabric's own
    # word for that part, checked against what 174 and 74 actually
    # define — a term this code names that the knowledge does not hold
    # is refused rather than printed, so the vocabulary cannot drift
    # away from the entries. The words are what the reading produced.
    # Nothing here is a sentence and nothing here is mine.

    def _t(self, term, words):
        if term not in self.terms:
            return None
        w = [x for x in words if x]
        return (term, w) if w else None

    def m_greet(self, s):
        if s.unread or (not s.no_subject and (s.about or s.kind)):
            return None
        if self.greeted:
            return self._t("turn", list(self.no_subject)[:1])
        self.greeted, self.greeted_on = True, self.turns
        return self._t("turn", sorted(self.no_subject)[:1])

    def m_unread(self, s):
        if not s.unread:
            return None
        return self._t("reading", [])

    def m_lean(self, s):
        if not s.leaned:
            return None
        return self._t("conversation", [s.leaned])

    def m_group(self, s):
        if s.unread or not s.w.get("groups"):
            return None
        return self._t("group", s.w["groups"])

    def m_doing(self, s):
        if not s.turns_on:
            return None
        return self._t("doing", [s.turns_on])

    def m_doer(self, s):
        if not s.doer:
            return None
        return self._t("doer", [s.doer])

    def m_done_to(self, s):
        if not s.done_to:
            return None
        return self._t("done-to", [s.done_to])

    def m_forbids(self, s):
        if not s.forbidden:
            return None
        return self._t("ground", ["not:"] + s.forbidden)

    def m_sense(self, s):
        if s.leaned or not s.senses:
            return None
        best = None
        for w, sn in s.senses.items():
            if sn["marks"] and (best is None
                                or sn["near"] > best[1]["near"]):
                best = (w, sn)
        if not best or best[1]["near"] < 3:
            return None
        w, sn = best
        return self._t("sense", [w + ":"] + sn["marks"][:4])

    def m_say(self, s):
        """The reading said back as a sentence, built by 174's own
        ordering rule run forwards. Not carried, not fetched, and not
        mine — the rule that reads a sentence is the rule that sets
        one down."""
        built = FR.say(s.doer, s.turns_on, s.done_to)
        if not built:
            return None
        return self._t("nesting", [built])

    def m_between(self, s):
        parts = [p for p in (s.doer, s.turns_on, s.done_to) if p]
        if len(parts) < 2:
            parts = s.about[:2]
        if len(parts) < 2:
            return None
        a, b = parts[0], parts[1]
        j = FR.joint(a, b)
        ground = (j or {}).get("ground") or []
        key = (core.stem(a), core.stem(b))
        if key in self.met and ground:
            out = FR.beyond(a, b, ground)
            return self._t("ground", [a + "+" + b, "past:"] + out) \
                if len(out) >= 2 else None
        self.met.add(key)
        return self._t("ground", [a + "+" + b] + ground)

    def m_guessing(self, s):
        if s.leaned or not (s.guessing and s.turns_on):
            return None
        return self._t("pointer", ["none"])

    MOVES = ["m_unread", "m_greet", "m_lean", "m_group", "m_say",
             "m_doing", "m_doer", "m_done_to", "m_guessing",
             "m_forbids", "m_sense", "m_between"]

    # ---------- the turn ----------
    def turn(self, text):
        s = Said(text, self, self.F)
        out = []
        for name in self.MOVES:
            got = getattr(self, name)(s)
            if not got:
                continue
            line = got[0] + ": " + " ".join(got[1])
            if line not in self.spoken[-6:]:
                out.append(line)
        if not out:
            out = ["ground: none"]
        self.spoken.extend(out)
        self.turns += 1
        if s.subject:
            self.subject = s.subject
        if s.turns_on and not s.leaned:
            self.last_doing = s.turns_on
        return "\n".join(out)


def main():
    F = core.fabric()
    t = Thread(F)
    while True:
        try:
            line = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return
        if not line:
            return
        print(t.turn(line) + "\n")


if __name__ == "__main__":
    main()
