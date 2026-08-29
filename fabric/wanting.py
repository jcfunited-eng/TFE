"""WHAT WAS SAID — a sentence read into a structure, not into an answer.

This retrieves nothing. There is no lookup in this file, no ranking,
and no entry is returned. What comes out is a structure describing
what the person wants, which is the thing an assembler would later
take as its specification. If it cannot tell, it says which part it
could not read rather than filling it in.

The parts of a want, and each is read from the sentence itself:

  KIND      what would count as an answer. The asking word says it —
            why wants a cause, how wants a method, what wants a
            naming. Read from the file that holds the asking words,
            by the form those entries are written in.
  ABOUT     what it is about: the groups that are not asking words
            and not the forbidden half.
  FORBIDDEN what may not be used. "Without X", "avoiding X" — the
            half that is a constraint on the making rather than a
            destination. Walking toward it is how a want to keep food
            cold walked straight into the electricity grid.
  TURNS ON  the doing, found by contrast, which is what the sentence
            hinges on.

None of this is an answer and none of it is a match. It is what was
said, laid out so something could act on it.
"""
import os, re, sys
BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)
import core, first_ribbon as FR


def asking_words(F):
    """The words that carry a question, and what each asks FOR —
    read from the file that holds them, in the form it is written."""
    out = {}
    for e in F.entries:
        if "carry the question" not in e["field"]:
            continue
        m = re.match(r"\s*([a-z]+)\s+asks?\s+(?:for\s+)?(.{0,60})",
                     e["essence"].lower())
        if m:
            out[m.group(1)] = re.sub(r"\s+", " ",
                                     m.group(2)).strip(" .,—-")
    return out


def split_forbidden(text):
    parts = re.split(r"\b(?:without|avoiding|with no|instead of)\b",
                     text, 1)
    return parts[0].strip(), (parts[1].strip()
                              if len(parts) > 1 else "")


def want(sentence, F=None):
    """Read a sentence into what it wants."""
    F = F or core.fabric()
    asks = asking_words(F)
    head, forbidden = split_forbidden(sentence)
    res = FR.read(head)
    if res["missing"]:
        return dict(unread=res["missing"])
    gs = res["groups"]
    turns_on = None
    if res["stood"]:
        _s, _p, d = res["stood"][0]
        turns_on = FR.head(gs[d])
    kind, asked_with = None, None
    for g in gs:
        for w in g:
            if w in asks:
                kind, asked_with = asks[w], w
                break
        if kind:
            break
    # What it is about is the content word of each group — the one
    # from outside the frame. Discarding a whole group because an
    # asking word sits in it threw away the subject: "why does bread
    # rise" groups as "why does bread | rise", so dropping the first
    # group dropped bread and it was about nothing.
    C = FR.company()
    about = []
    for g in gs:
        for w in g:
            if w in asks or w in C.frame:
                continue
            if w != turns_on and w not in about:
                about.append(w)
    return dict(kind=kind, asked_with=asked_with, about=about,
                forbidden=[core.stem(w) for w in
                           re.findall(r"[a-z]+", forbidden.lower())
                           if len(w) > 2],
                turns_on=turns_on,
                groups=[" ".join(g) for g in gs],
                incomplete=res["capped"])


def show(sentence, F=None):
    w = want(sentence, F)
    out = [f"SAID: {sentence}"]
    if w.get("unread"):
        out.append(f"  I cannot read this — {w['unread'][0]}")
        return "\n".join(out)
    out.append(f"  it groups as:  {' | '.join(w['groups'])}")
    out.append(f"  it turns on:   {w['turns_on'] or 'nothing I could find'}")
    out.append(f"  it is about:   {', '.join(w['about']) or 'nothing I could name'}")
    if w["asked_with"]:
        out.append(f"  it asks for:   {w['kind']}  (from '{w['asked_with']}')")
    else:
        out.append(f"  it asks for:   nothing I recognise as an asking — "
                   f"so this is a want, not a question")
    if w["forbidden"]:
        out.append(f"  it forbids:    {', '.join(w['forbidden'])}")
    if w["incomplete"]:
        out.append(f"  NOT COMPLETE:  {w['incomplete'][:80]}")
    return "\n".join(out)


if __name__ == "__main__":
    F = core.fabric()
    tests = sys.argv[1:] or [
        "why does bread rise",
        "keep food cold without electricity",
        "how do I sharpen a knife",
        "make a shelter that stays warm without fuel",
    ]
    for t in tests:
        print(show(t, F))
        print()
