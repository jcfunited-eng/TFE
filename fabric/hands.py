"""THE HANDS, first cut — a make-want crossed into a made thing.

This is use, not possession. For a want like "create a pumpkin
cheese cake recipe" it enters the chosen subject and assembles a
PROCEDURE: the followable RULE directives the subject's science
holds — written exactly to be followed — selected because they
grip the want's words, ordered as making orders them (structure
first, then transformation, then settling), with the parts the
subject holds and an honest list of the words it does not. The
composed procedure exists nowhere in the corpus; each directive
is written knowledge being APPLIED, not returned as an answer.

One engine: nothing in this file names any subject or any dish.
Where knowledge is shallow the output is shallow and says so.
"""
import re
import phylum_reader as PR

_WORD = re.compile(r"[a-z]+")

# The three ages of any making, told by a directive's own verbs.
_EARLY = {"mix", "whip", "knead", "beat", "emulsify", "cut",
          "measure", "weigh", "choose", "combine", "dissolve",
          "size", "scale"}
_LATE = {"rest", "chill", "cool", "settle", "store", "keep",
         "wait", "set"}


def _tokens(text):
    return {PR._stem(t) for t in _WORD.findall(text.lower())}


def _directives(half):
    """Every followable RULE the subject holds, each with the LAW
    text it rides on (its justification), as (rule, law_head)."""
    out = []
    for e in half.get("SCIENCE", []) + half.get("METHODS", []):
        m = re.search(r"RULE[^:]*:\s*(.+?)(?=\n[A-Z]{3,}|\Z)", e,
                      re.S)
        if not m:
            continue
        rule = re.sub(r"\s+", " ", m.group(1)).strip()
        head = PR.first_line(e)
        out.append((rule, head))
    return out


def _age(rule):
    toks = _tokens(rule)
    if toks & _EARLY and not (toks & _LATE):
        return 0
    if toks & _LATE and not (toks & _EARLY):
        return 2
    return 1


def make(want_words, slug):
    """Assemble a procedure for the want from one phylum's written
    rules. Returns made text, or None when nothing grips."""
    half = PR.fabric().get(slug, {}).get("color", {})
    if not half:
        return None
    want_toks = {PR._stem(w) for w in want_words}

    things = [e for e in half.get("THINGS", [])
              if _tokens(e) & want_toks]
    # A held part DECOMPOSES into the subject's own things: milk
    # is fat + water + protein + sugar, and only rules gripping
    # those components apply. Word-echo beyond the thing-names
    # selected canning rules for a cheesecake; this is the fence.
    thing_names = set()
    for e in half.get("THINGS", []):
        head = _tokens(e.split("—")[0])
        thing_names |= head
    wide = set(want_toks)
    for e in things[:4]:
        wide |= (_tokens(e) & thing_names)

    if not things:
        return None

    # The one selection that held up under test: DECOMPOSITION.
    # A held part breaks into the subject's own components, and
    # each component's governing laws are found by name. Three
    # procedure-composers were tried tonight and every one chose
    # by word overlap and chose wrong; that failure is filed in
    # the white with its drain condition, not shipped.
    media = {"water", "heat", "air"}  # in everything; grip nothing
    small = {"and", "the", "in", "of", "a", "it", "its", "with"}
    components = sorted((wide & thing_names) - media - small
                        - {PR._stem(w) for w in want_words})

    laws = [e for e in half.get("SCIENCE", [])
            if e.startswith(("LAW", "REACTION"))]

    out = [f"USED FROM {slug.upper()} — not fetched: your want's "
           f"parts broken into what my knowledge says they are "
           f"made of, and what the written laws force on each. "
           f"No composed procedure is offered, because choosing "
           f"and ordering the acts needs a reading of the want "
           f"deeper than I have yet built — I will not fake one."]

    out.append("\nTHE PARTS I hold, and their make-up:")
    for e in things[:4]:
        out.append(f"  · {PR.first_line(e)}")

    missing = [w for w in want_words
               if not any(PR._stem(w) in _tokens(e)
                          for e in things)]
    if missing:
        out.append(f"\nNOT HELD: {', '.join(missing)} — nothing "
                   f"below can see these.")

    if components:
        out.append("\nWHAT THE LAWS FORCE, component by component:")
        for c in components:
            for law in laws:
                # match the law's own statement, never its worked
                # example — "two bags of sugar" in an example must
                # not make the knife law sugar's law.
                stmt = law.split("WORKED")[0]
                if c in _tokens(stmt):
                    out.append(f"  {c.upper()} — "
                               f"{PR.first_line(law)}")
                    break

    out.append("\nWhat this is: the want decomposed and its "
               "components' laws brought to bear — knowledge "
               "used, not returned. What it is not: the made "
               "thing. The missing piece is one mechanism — "
               "reading the want's ACT so the acts can be chosen "
               "and ordered — and it is the next build, named in "
               "the white.")
    return "\n".join(out)
