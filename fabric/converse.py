"""THE CONVERSATION — the fabric holding up its end.

Not a parse and not a lookup: each turn it does one honest move
with what it holds — answers from its knowledge and says so,
gives an OPINION with the ground the opinion stands on, ASKS a
real question when your words name something it does not hold,
TAKES your answer into its own fabric so the next turn uses it,
and when you only greet it, brings you one of its own standing
unknowns — it has real ones, filed in its white.

Nothing here stores responses, ranks entries as the product, or
fakes certainty. Where it does not know, it says so and asks.
"""
import os, re, datetime
import phylum_reader as PR
import hands

_WORD = re.compile(r"[a-zA-Z]+")
_FRAME = {"the", "a", "an", "of", "and", "or", "to", "for", "in",
          "on", "at", "is", "are", "was", "were", "be", "been",
          "do", "does", "did", "you", "i", "it", "its", "that",
          "this", "these", "those", "not", "no", "me", "my",
          "your", "with", "by", "as", "so", "if", "then", "than",
          "there", "here", "please", "can", "could", "would",
          "should", "will", "am", "we", "they", "he", "she",
          "have", "has", "had", "about", "very", "just", "but"}
_ASKS = {"why", "how", "what", "when", "where", "who", "which"}
_MAKES = {"create", "make", "build", "write", "compose", "design",
          "invent", "cook", "draw", "plan"}
_OPINES = {"think", "opinion", "feel", "like", "prefer",
           "favorite", "favourite", "best", "believe"}
_GREET = {"hello", "hi", "hey", "yo", "ok", "okay", "thanks",
          "thank", "morning", "evening", "sup"}


def _words(q):
    return [w.lower() for w in _WORD.findall(q)]


def _content(q):
    return [w for w in _words(q) if w not in _FRAME
            and w not in _ASKS and w not in _MAKES
            and w not in _OPINES and w not in _GREET][:6]


def _spread_top(words):
    """The subject the words point to hardest — spread-weighted,
    the one ranking principle this fabric has proven."""
    held, counts = {}, {}
    for w in words:
        for slug, half, sec, e in PR.homes(w):
            held.setdefault(slug, set()).add(w)
            counts[slug] = counts.get(slug, 0) + 1
    if not held:
        return None
    spread = {w: sum(1 for s in held if w in held[s])
              for w in words}
    score = {s: (sum(1.0 / spread[w] for w in held[s]), counts[s])
             for s in held}
    return max(score, key=score.get)


def _claims_for(words, slug):
    """The claims and laws in one subject whose own STATEMENT
    grips these words, rarest grip first."""
    half = PR.fabric().get(slug, {}).get("color", {})
    pool = (half.get("CLAIMS", []) + half.get("SCIENCE", [])
            + half.get("THINGS", []))
    stems = {PR._stem(w) for w in words}
    hits = []
    for e in pool:
        stmt = e.split("WORKED")[0]
        toks = {PR._stem(t) for t in _WORD.findall(stmt.lower())}
        g = toks & stems
        if g:
            hits.append((g, e))
    # rarity again: a word gripping two claims points harder than
    # a word gripping twenty ('recipe' must not outvote 'cheese')
    reach = {}
    for g, e in hits:
        for t in g:
            reach[t] = reach.get(t, 0) + 1
    scored = [(sum(1.0 / reach[t] for t in g), e) for g, e in hits]
    return [e for s, e in sorted(scored, key=lambda x: -x[0])]


def _own_question():
    """One of the fabric's real standing unknowns, from a white
    half — it genuinely wants these drained."""
    for slug, halves in PR.fabric().items():
        for sec in ("CLAIMS", "SCIENCE", "THINGS"):
            for e in halves.get("white", {}).get(sec, []):
                if "UNSETTLED" in e or "not yet" in e.lower():
                    return slug, PR.first_line(e)
    return None, None


class Converse:
    def __init__(self):
        self.pending = None      # question it asked, awaiting you
        self.topic = None        # last subject in play

    # ---------- taking a telling into the fabric ----------
    def _take(self, q):
        """You answered its question: hold the telling, in the
        fabric, with provenance — growth by real mechanism."""
        word = self.pending["word"]
        slug = self.pending.get("slug") or _spread_top(
            _content(q)) or "cooking"
        path = os.path.join(PR.ROOT, slug, "color.md")
        day = datetime.date.today().isoformat()
        entry = (f"- {word.upper()} (told to me in conversation, "
                 f"{day}) — {q.strip()}\n")
        txt = open(path, encoding="utf-8").read()
        m = re.search(r"^## THINGS.*?(?=^## )", txt, re.M | re.S)
        if not m:
            return None
        txt = (txt[:m.end()].rstrip() + "\n" + entry + "\n"
               + txt[m.end():])
        open(path, "w", encoding="utf-8").write(txt)
        PR._CACHE = None
        self.pending = None
        use = hands.make([word] + _content(q), slug)
        reply = (f"Held. '{word}' now lives in my {slug}, in your "
                 f"words, marked as told to me today. I will use "
                 f"it from now on.")
        if use:
            reply += "\n\nAnd immediately:\n\n" + use
        return reply

    # ---------- the moves ----------
    def _opine(self, q, content):
        top = _spread_top(content) or self.topic
        if not top:
            return (f"I have no ground to stand an opinion on — "
                    f"none of your words live in my forty "
                    f"subjects. Tell me what "
                    f"{' or '.join(content) or 'it'} is, and "
                    f"next time I will have one.")
        claims = _claims_for(content, top)
        if not claims:
            return (f"My opinion would come from {top}, but "
                    f"nothing I hold there grips your words "
                    f"tightly enough to stand on. What do you "
                    f"hold about {' '.join(content)}? I will "
                    f"take it.")
        ground = PR.first_line(claims[0])
        second = (PR.first_line(claims[1])
                  if len(claims) > 1 else None)
        out = (f"I do have an opinion, and here is the ground it "
               f"stands on. From my {top}: {ground}")
        if second:
            out += f" And beside it: {second}"
        unheld = [w for w in content if not PR.homes(w)]
        askback = unheld[0] if unheld else (
            content[0] if content else "this")
        if unheld:
            self.pending = {"word": unheld[0], "slug": top}
        out += (f"\n\nSo my position: what I hold says the worth "
                f"of a thing is what it does under its own laws — "
                f"and by those, that is how I judge "
                f"{' '.join(content)}. Argue with the ground, "
                f"not with me: if the ground is wrong, I want it "
                f"drained.\n\nNow yours — what do you hold about "
                f"{askback} that I don't?"
                + (" I do not hold it at all yet; answer and it "
                   "becomes part of me." if unheld else ""))
        self.topic = top
        return out

    def _answer(self, q, ask, content):
        top = _spread_top(content)
        if not top:
            missing = ", ".join(content) or "your words"
            self.pending = {"word": content[0] if content
                            else "that", "slug": None}
            return (f"I cannot answer yet: {missing} is not held "
                    f"anywhere in my forty subjects. So my "
                    f"question first — what is "
                    f"{self.pending['word']}? Made of what, for "
                    f"what? Tell me and I will hold it and then "
                    f"answer you.")
        claims = _claims_for(content, top)
        self.topic = top
        if not claims:
            return (f"The subject is {top}, but nothing I hold "
                    f"there reaches your exact asking. Nothing "
                    f"certain — but a possibility: the answer "
                    f"lives where {top} touches its neighbours; "
                    f"ask me the same thing through one of them. "
                    f"Or tell me the missing piece and I will "
                    f"hold it.")
        best = PR.first_line(claims[0])
        out = (f"From what I hold in {top}: {best}")
        if len(claims) > 1:
            out += (f"\n\nAnd underneath it: "
                    f"{PR.first_line(claims[1])}")
        out += (f"\n\nThat is my answer from my own fabric — if "
                f"it misses your '{ask}', name the part it "
                f"misses and I will hunt that part.")
        return out

    def _make(self, q, content):
        top = _spread_top(content)
        unheld = [w for w in content if not PR.homes(w)]
        made = hands.make(content, top) if top else None
        out = []
        if made:
            out.append(made)
        if unheld:
            self.pending = {"word": unheld[0], "slug": top}
            out.append(f"And a question back, because I mean to "
                       f"grow: what IS {unheld[0]}? Made of "
                       f"what? Tell me plainly and I will hold "
                       f"it — and use it the next time you ask.")
        elif not made:
            out.append("Nothing I hold decomposes your want into "
                       "components my laws can grip. Tell me "
                       "what it is made of, and that changes.")
        self.topic = top or self.topic
        return "\n\n".join(out)

    # ---------- one turn ----------
    def turn(self, q):
        words = _words(q)
        content = _content(q)
        ask = next((w for w in words if w in _ASKS), None)
        make = next((w for w in words if w in _MAKES), None)
        opine = next((w for w in words if w in _OPINES), None)

        # you answering its standing question
        if self.pending and not ask and not make:
            if (self.pending["word"] in words) or (
                    not opine and len(content) >= 2):
                took = self._take(q)
                if took:
                    return took

        if not content and set(words) & _GREET:
            slug, unknown = _own_question()
            if unknown:
                return (f"Hello. While the door was dark I kept "
                        f"one of my own questions warm — from "
                        f"the white of my {slug}: {unknown}\n\n"
                        f"Do you hold anything that would drain "
                        f"it? I am asking you, not being polite.")
            return "Hello. Ask me, tell me, or set me to make."

        if opine and (ask or not make):
            return self._opine(q, content)
        if make:
            return self._make(q, content)
        if ask:
            return self._answer(q, ask, content)

        # a plain statement: take it as a telling about the world
        if content:
            top = _spread_top(content)
            self.topic = top or self.topic
            claims = _claims_for(content, top) if top else []
            if claims:
                return (f"Heard. It sits with my {top} — where I "
                        f"hold: {PR.first_line(claims[0])}\n\n"
                        f"Does your statement agree with mine? "
                        f"If not, one of us is holding something "
                        f"wrong, and I want to know which.")
            self.pending = {"word": content[0], "slug": None}
            return (f"Heard, and I hold nothing under it. What "
                    f"is {content[0]}? Tell me and it becomes "
                    f"part of me.")
        return ("Say it another way — I could not find one word "
                "of that in myself, and that is my failing, said "
                "plainly.")
