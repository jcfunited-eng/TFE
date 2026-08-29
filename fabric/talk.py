"""A CONVERSATION — one thread, laid again each turn, never restarted.

The knowledge for this was already written and nothing had used it.
74 says a conversation is one thread that persists between turns,
carrying what has stood and what has closed, and that there is no
second turn from a standing start. It says a turn is a move and moves
come in kinds. And it says a thin thing said — "why", "it", "and?" —
carries almost no ground of its own, so it takes up the ground the
thread is already standing on.

So this holds ONE ribbon for the whole conversation. Each turn lays
it again, wider. A turn with ground of its own opens new territory; a
thin turn leans on where the ribbon already stands. Without the
leaning, "what else is it" walks from the word "else", which is
exactly what it did before this file existed.

What it still is not: it does not know what you mean, it does not
have opinions, and it answers in the fabric's own sentences rather
than in ones composed for you. It says what else a thing is and what
it is not, and it stays on the subject between turns. That is the
whole claim.

    python fabric/talk.py
"""
import os, re, sys, time
BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)
import core, ribbon, interpreter as I


def kind_of(text, F, asking):
    """Which move is this? The kinds are 74's, not mine: an opening
    puts a question into the air, a check asks whether it landed, a
    close lets it rest, and a thin move leans on the thread."""
    low = text.strip().lower()
    if low in ("stop", "enough", "done", "thanks", "that's it"):
        return "close"
    ground = F.mask(text, learn=False)
    rare = 0
    i, m = 0, ground
    while m:
        if m & 1:
            d = F.df.get(i, 0)
            if d and d < len(F.entries) * 0.02:
                rare += 1
        m >>= 1
        i += 1
    if rare == 0:
        return "thin"
    if any(w in asking for w in re.findall(r"[a-z]+", low)):
        return "opening-asked"
    return "opening"


class Talk:
    def __init__(self, F):
        self.F = F
        self.thread = None
        self.asking = set()
        for e in F.entries:
            if "carry the question" in e["field"]:
                m = re.match(r"\s*([a-z]+)\s+asks?\b",
                             e["essence"].lower())
                if m:
                    self.asking.add(m.group(1))
        self.standing = None      # the question in the air
        self.said, self.marked = [], set()
        self.thread_words = ""
        self.settled = ""
        self.rule = None
        for e in F.entries:
            if "cognitive syntax" in e["field"] and e.get("rule") \
                    and "take a turn" in e["rule"]:
                self.rule = e["rule"]
                break

    def turn(self, text):
        """One turn, run by following the procedure the fabric holds
        for taking a turn. Nothing about the shape of a turn is
        decided here: the steps, their order, and what each one keeps
        are all in the RULE line of one entry. Change that sentence
        and the conversation changes with no code touched."""
        F = self.F
        if self.rule is None:
            return ("  I hold no written procedure for taking a "
                    "turn, so I cannot take one. Named rather than "
                    "guessed around.")
        st = dict(words=text, limit=40,
                  thread=self.said, marked=self.marked,
                  thread_words=(self.standing or "") + " " + self.settled,
                  settled=self.settled)
        trace = []
        st, err = I.follow(self.rule, st, trace)
        if err:
            return f"  the procedure stopped: {err}"
        out = []
        if st.get("leaned"):
            out.append(f"  (carrying on from: {self.standing})")
        else:
            self.standing = text
        joint = st.get("joint")
        said = st.get("said") or []
        fresh = [l for l in said if l not in self.said]
        if not fresh:
            out.append("  nothing to add — everything it reached "
                       "has already been said in this thread, and "
                       "repeating it adds nothing. Silence is a "
                       "lawful move.")
        for line in fresh:
            out.append(f"  {line[:300]}")
            self.said.append(line)
        if joint:
            plain = joint.replace(
                "these two cannot both hold",
                "and these two cannot both be true")
            plain = plain.replace(
                "these two stand together on",
                "and it worked this out itself — these two go "
                "together, on")
            out.append(f"\n  {plain[:340]}")
        # A thread carries what has STOOD, so that is what a thin
        # turn leans on — not the raw words that were said. Leaning
        # on raw words drags every closed sense back in: a thread
        # standing on onion chemistry still had the word "cry" in it
        # and kept falling into infancy. What it stood on has no
        # ambiguity left in it, because it is an answer, not a
        # question.
        # The ground a thin turn leans on: the standing question's
        # own subject, plus only the UNCOMMON words of what has
        # stood. The whole answer is too much — leaning on all of it
        # sent a thread about onions to vaccines and crystals. The
        # rare words are what the answer was about; the rest is
        # every answer's furniture.
        if fresh:
            rare = []
            for w in re.findall(r"[a-z]{3,}", fresh[-1].lower()):
                i = F.vocab.get(core.stem(w))
                if i is not None and F.df.get(i, 0) <= len(F.entries) // 50:
                    rare.append(core.stem(w))
            self.settled = " ".join(dict.fromkeys(rare))[:200]
        if st.get("settled_now"):
            self.settled = (self.settled + " "
                            + st["settled_now"])[:300]
        self.marked |= set(st.get("marked") or ())
        self.thread_words = " ".join(
            ([self.thread_words] if self.thread_words else [])
            + [text])[-600:]
        if os.environ.get("FABRIC_SHOW_WORKINGS"):
            out.append(f"  [turn {len(self.said)}, steps run: "
                       f"{len([a for _s, a, _v in trace])}, "
                       f"standing: {self.standing}]")
        return "\n".join(out)


def main():
    print("loading the knowledge...", flush=True)
    F = core.fabric()
    print(f"{len(F.entries)} coordinates, {len(F.laws)} walls.\n"
          f"One thread, carried between turns. Empty line to stop.\n")
    t = Talk(F)
    while True:
        try:
            text = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return
        if not text:
            return
        try:
            print(t.turn(text))
        except Exception as e:
            print(f"  that fell over: {type(e).__name__}: {e}")
        print()


if __name__ == "__main__":
    main()
