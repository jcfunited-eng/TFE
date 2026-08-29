"""THE RIBBON AS THE LANGUAGE PROGRAM.

The ribbon is not handled by a program I wrote. It crosses the
knowledge about language and that crossing assembles what handles
it: which words are doing the asking, what kind of answer each
asking word demands, which crowd of words marks which area of
life, and which sense of a two-meaning word is meant here.

Every one of those is read out of the files at the moment of the
question. Nothing in this file lists an asking word, a crowd or a
sense. If the language files were deleted, the ribbon would carry
data and know nothing about how to read it, which is correct.

The data rides in and never enters the sheets.
"""
import os, re, sys, math, collections
BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)
import core, os_fabric

class Language:
    """What the knowledge says about reading a question."""

    def __init__(self):
        F = core.fabric()
        self.F = F
        self.asking = {}     # asking word -> the kind of answer wanted
        self.crowds = []     # (area, words) — the company of a subject
        self.senses = {}     # word -> [(sense, company words)]
        for e in F.entries:
            fld, same = e["field"], (e.get("same") or "")
            words = set(re.findall(r"[a-z]{2,}", same.lower()))
            if not words: continue
            if "carry the question" in fld:
                kind = e["essence"].split("—")[0]
                kind = re.sub(r"^\s*\w+\s+asks?\s+(for\s+)?", "",
                              kind.strip(), flags=re.I)[:60]
                for w in words: self.asking[w] = kind.strip()
            elif "go together" in fld:
                area = e["essence"].split("—")[0].strip()[:60]
                self.crowds.append((area, words))
            for group in same.split("|"):
                gw = set(re.findall(r"[a-z]{3,}", group.lower()))
                if len(gw) > 1:
                    for w in gw:
                        self.senses.setdefault(w, set()).update(gw)
        for e in F.entries:
            sp = e.get("splits") or ""
            if not sp: continue
            for part in sp.split("|"):
                if ":" not in part: continue
                name, comp = part.split(":", 1)
                cw = set(re.findall(r"[a-z]{3,}", comp.lower()))
                for w in re.findall(r"[a-z]{3,}", name.lower())[:1]:
                    self.senses.setdefault(w, set()).update(cw)

    def read(self, question):
        """The ribbon reading itself, using only what it crossed."""
        raw = re.findall(r"[a-z]+", question.lower())
        asked, kind = [], None
        for w in raw:
            if w in self.asking:
                asked.append(w)
                if kind is None: kind = self.asking[w]
        subject = [w for w in raw if w not in self.asking and len(w) > 2]
        # which crowd do the subject words fall into — the crowd is
        # the context, and one word alone never decides it
        best_area, best_hit, best_words = None, 0, set()
        sset = set(subject)
        for area, words in self.crowds:
            hit = len(sset & words)
            if hit > best_hit:
                best_area, best_hit, best_words = area, hit, words
        return dict(kind=kind, asked=asked, subject=subject,
                    area=best_area if best_hit >= 2 else None,
                    crowd=best_words if best_hit >= 2 else set(),
                    crowd_hits=best_hit)

LANG = None
def language():
    global LANG
    if LANG is None: LANG = Language()
    return LANG

def answer(question):
    L = language()
    r = L.read(question)
    # the data that travels is the subject plus its crowd, never the
    # asking words — those said what shape the answer takes
    carried = " ".join(r["subject"]) + " " + " ".join(
        sorted(r["crowd"])[:12])
    settled, stopped, reached = os_fabric.deliver(carried)
    return r, settled, reached

if __name__ == "__main__":
    for q in sys.argv[1:]:
        r, settled, reached = answer(q)
        print(f"\nASKED: {q}")
        print(f"  asking words: {r['asked']}  wants: {r['kind']}")
        print(f"  crowd: {r['area']} ({r['crowd_hits']} words)")
        for s, e in settled[:2]:
            print(f"    {s:.1f} ({e['field']}) {e['essence'][:78]}")
