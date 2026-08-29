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

WHOSE: the move list is MINE, on trial. Joe has not seen it and it is
not ratified. It is in code rather than in the knowledge, which is a
compromise and the wrong side of the architecture — knowledge is
meant to be the processor. Moving the moves into the corpus, so a
move can be added by writing a sentence, is the next step and it is
named here so it is not quietly forgotten.

WHAT IT WILL NOT DO: pass stored text off as its own speech. When it
says something the corpus holds, it says that is what it is doing.
"""
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
        low = set(re.findall(r"[a-z]+", self.text.lower()))
        self.thin = bool(low & thread.thin) and not self.ground
        self.leaned = None
        if self.thin and thread.subject:
            self.leaned = thread.subject
            self.subject = thread.subject
            self.about = [thread.subject]
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

    # ---------- the moves ----------
    # Each returns the words it would say, or None when it does not
    # apply. Not applying IS the killing: a move that has nothing to
    # say under this reading says nothing, and the turn is whatever
    # survives. Order here is the order a person says things in —
    # answer the person, then the subject, then what is missing.

    def m_greet(self, s):
        if s.unread or (not s.no_subject and (s.about or s.kind)):
            return None
        if self.greeted:
            return None
        self.greeted, self.greeted_on = True, self.turns
        return ("Hello. You have not given me a subject yet — say "
                "what you want and I will tell you what I can reach "
                "and what I cannot.")

    def m_greet_again(self, s):
        if s.unread or not self.greeted:
            return None
        if not s.no_subject and (s.about or s.kind):
            return None
        if self.turns == self.greeted_on:
            return None          # the greeting itself, not a repeat
        if s.no_subject:
            return "Hello again."
        if self.turns == self.greeted_on:
            return None          # the greeting itself, not a repeat
        return "Still nothing in that for me to take hold of."

    def m_unread(self, s):
        if not s.unread:
            return None
        return f"I could not read that. {s.unread[0]}"

    def m_lean(self, s):
        if not s.leaned:
            return None
        asked = (f", and you are asking {s.asked_with}"
                 if s.asked_with else "")
        return f"Still on {s.leaned}{asked}."

    def m_thin_nothing(self, s):
        if not (s.thin and not s.leaned):
            return None
        return ("There is not enough in that on its own, and the "
                "thread is not standing on anything yet for it to "
                "lean on.")

    def m_carry_on(self, s):
        if s.leaned or not (s.same_subject and self.turns):
            return None
        return f"Still on {s.subject}."

    def m_moved(self, s):
        if s.leaned:
            return None
        if not (self.subject and s.new_subject):
            return None
        if self.subject in self.no_subject:
            return None
        return f"We were on {self.subject}; you have moved to {s.subject}."

    def m_heard(self, s):
        if not s.about or s.unread or s.leaned:
            return None
        what = ", ".join(s.about[:3])
        # who did what to whom, when the reading has it. This is the
        # nesting doing its job in the conversation rather than in a
        # test: without it "the dog bit the man" and "the man bit the
        # dog" came back as the same turn.
        if s.doer and s.done_to and s.turns_on:
            return (f"So {s.doer} is what does it, {s.turns_on} is "
                    f"what happens, and {s.done_to} is what it "
                    f"reaches.")
        if s.kind and s.turns_on:
            return (f"You want {self._kind_short(s.kind)}, about "
                    f"{what}, and the sentence turns on {s.turns_on}.")
        if s.turns_on:
            return (f"You want something done — {s.turns_on} — and it "
                    f"is about {what}.")
        return f"I have this as being about {what}."

    def m_forbids(self, s):
        if not s.forbidden:
            return None
        f = ", ".join(s.forbidden)
        return (f"You have ruled out {f}, so that is a limit on what "
                f"I may use, not a place to go looking.")

    def m_guessing(self, s):
        if not (s.guessing and s.turns_on and s.about):
            return None
        return (f"I am not sure {s.turns_on} is the word it turns on. "
                f"Nothing in that sentence marked one part off "
                f"against another, so I went on how the writing "
                f"usually runs, which is the half of me that is "
                f"weaker.")

    def m_sense(self, s):
        """What the word is carrying HERE, produced from the company
        standing with it. Said only when the company actually marks
        something off, and it says how thin the ground under it was."""
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
        return (f"Taking '{w}' the way this company puts it — "
                f"{', '.join(sn['marks'][:4])} — off {sn['near']} of "
                f"the {sn['seen']} places I have it.")

    def m_no_ground(self, s):
        if not s.about or s.ground:
            return None
        return (f"I hold nothing about {', '.join(s.about[:2])}. Not "
                f"that it is unanswerable — there is no ground "
                f"written under it in me.")

    def m_offer(self, s):
        if not s.ground:
            return None
        for e in s.ground:
            if e["id"] in self.offered:
                continue
            self.offered.add(e["id"])
            line = e["essence"].rstrip(".")
            return (f"What is written in me on that: {line}. "
                    f"That sentence was already in me before you "
                    f"asked — I did not work it out just now.")
        return ("What I hold on that I have already said in this "
                "conversation, and saying it again would add nothing.")

    def m_ask_back(self, s):
        if s.unread or not s.about:
            return None
        if s.kind and s.ground:
            return None
        if s.forbidden and not s.ground:
            return (f"What is it FOR? You have told me what I may not "
                    f"use and what it is about, and not what would "
                    f"count as having done it.")
        if not s.kind:
            return (f"What would count as an answer — how it is done, "
                    f"or why it happens, or what it is?")
        return None

    def m_nothing(self, s):
        return None

    MOVES = ["m_unread", "m_greet", "m_greet_again",
             "m_lean", "m_thin_nothing", "m_carry_on",
             "m_moved", "m_heard", "m_forbids", "m_guessing",
             "m_sense", "m_no_ground", "m_offer", "m_ask_back"]

    @staticmethod
    def _kind_short(kind):
        k = kind.split(".")[0].split("—")[0].strip()
        return k[:60] if k else "an answer"

    # ---------- the turn ----------
    def turn(self, text):
        s = Said(text, self, self.F)
        out = []
        for name in self.MOVES:
            said = getattr(self, name)(s)
            if said and said not in self.spoken[-4:]:
                out.append(said)
        if not out:
            out = ["I have nothing to say to that which I have not "
                   "already said."]
        self.spoken.extend(out)
        self.turns += 1
        if s.subject:
            self.subject = s.subject
        return " ".join(out)


def main():
    F = core.fabric()
    t = Thread(F)
    print(f"{len(F.entries)} things written. One thread. "
          f"Empty line to stop.\n")
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
