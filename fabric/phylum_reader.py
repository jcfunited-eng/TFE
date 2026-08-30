"""The translation layer: the built phylums (docs/phylums/*) read
into structures a program can hold.

This retrieves nothing and answers nothing. It reads the fabric's
own files — the eight parts of each half of each phylum — so the
machinery that understands a sentence can ground words in the NEW
fabric instead of the old thin files. Generic over every phylum;
no subject is special-cased anywhere in it.
"""
import os, re

BASE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(BASE, "..", "docs", "phylums"))
SECTIONS = ("THINGS", "CLAIMS", "SCIENCE", "METHODS", "MEANS",
            "PURPOSE", "HISTORY", "RELATIONS")

_CACHE = None


def read_half(path):
    """One half of one phylum -> {section: [entry, ...]}.
    An entry is one bullet, or one LAW/RULE/WORKED block, as written."""
    if not os.path.exists(path):
        return {}
    txt = open(path, encoding="utf-8").read()
    parts, cur, buf = {}, None, []
    for line in txt.splitlines():
        m = re.match(r"^## ([A-Z][A-Z ]+)\s*$", line)
        if m and m.group(1).strip() in SECTIONS:
            if cur:
                parts[cur] = _entries("\n".join(buf))
            cur, buf = m.group(1).strip(), []
        elif cur is not None:
            buf.append(line)
    if cur:
        parts[cur] = _entries("\n".join(buf))
    return parts


def _entries(section_text):
    """Split a section into its entries: '- ' bullets, LAW blocks,
    or ### sub-headed runs — tolerant of each builder's hand."""
    out, buf = [], []
    for line in section_text.splitlines():
        starts = (line.startswith("- ") or line.startswith("LAW")
                  or line.startswith("REACTION")
                  or line.startswith("### "))
        if starts and buf:
            out.append("\n".join(buf).strip())
            buf = [line]
        else:
            buf.append(line)
    if buf:
        out.append("\n".join(buf).strip())
    return [e for e in out if e and not e.startswith("### ")
            and len(e) > 20]


def fabric():
    """Every phylum, both halves, cached for the process."""
    global _CACHE
    if _CACHE is None:
        f = {}
        if os.path.isdir(ROOT):
            for slug in sorted(os.listdir(ROOT)):
                d = os.path.join(ROOT, slug)
                if not os.path.isdir(d):
                    continue
                f[slug] = {
                    "color": read_half(os.path.join(d, "color.md")),
                    "white": read_half(os.path.join(d, "white.md")),
                }
        _CACHE = f
    return _CACHE


_WORD = re.compile(r"[a-z]+")


def _stem(w):
    """The same crude stem the old reading uses: plural and -ing/-ed
    tails folded, so 'dresses' finds 'dress' and 'baking' finds
    'bake'. Deliberately dumb; wrong folds are visible, not hidden."""
    for tail in ("ing", "ed", "es", "s"):
        if w.endswith(tail) and len(w) - len(tail) >= 3:
            return w[: -len(tail)]
    return w


def homes(word):
    """Where a word lives in the fabric: [(slug, half, section,
    entry), ...] — every entry whose text carries the word or its
    stem. This is grounding, not answering: the caller decides what
    if anything to do with the places."""
    w = _stem(word.lower())
    found = []
    for slug, halves in fabric().items():
        for half in ("color", "white"):
            for section, entries in halves.get(half, {}).items():
                for e in entries:
                    toks = {_stem(t) for t in
                            _WORD.findall(e.lower())}
                    if w in toks:
                        found.append((slug, half, section, e))
    return found


def first_line(entry):
    """The entry's own opening, for saying where a word lives
    without dumping the whole entry."""
    line = " ".join(entry.split("\n")[:2])
    line = re.sub(r"\s+", " ", line).strip("- ").strip()
    return (line[:140] + "…") if len(line) > 140 else line
