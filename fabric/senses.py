"""THE WORDS LAYER — practical data in service of the knowledge.

A dictionary of senses (WordNet) sits under the fabric so the
machine can stop comparing letters. Two jobs only:

  pick(word, company)  — which sense of a word is meant here,
                         decided by the company the word keeps
  family(word, company) — that sense's near-words and its kind,
                         so cold reaches chilly and refrigeration

Knowledge stays the currency: nothing here states a fact about
the world. It only tells the engine which sense a word carries,
which is what turns letter-matching into meaning.
"""
import functools
from nltk.corpus import wordnet as wn

def _words(text):
    return {w.lower().strip("(),.;:") for w in text.split()
            if len(w) > 3}

@functools.lru_cache(maxsize=8192)
def _senses(word):
    return tuple(wn.synsets(word))

def _stem(w):
    for s in ("ing", "ers", "er", "ed", "es", "s", "ly"):
        if w.endswith(s) and len(w) - len(s) >= 3:
            return w[:len(w) - len(s)]
    return w

@functools.lru_cache(maxsize=8192)
def _context_of(name):
    s = wn.synset(name)
    bag = set(_words(s.definition()))
    for ex in s.examples(): bag |= _words(ex)
    for l in s.lemmas(): bag.add(l.name().lower().replace("_", " "))
    rels = (s.hypernyms() + s.hyponyms() + s.part_meronyms()
            + s.member_holonyms() + s.similar_tos()
            + s.also_sees() + s.attributes())
    for rel in rels:
        bag |= set(_words(rel.definition()))
        for l in rel.lemmas():
            bag.add(l.name().lower().replace("_", " "))
        for up in rel.hypernyms()[:2]:
            bag |= set(_words(up.definition()))
    return frozenset(_stem(w) for w in bag if len(w) > 3)

def pick(word, company):
    """Which sense is meant, judged by the company kept."""
    ss = _senses(word)
    if not ss: return None
    if len(ss) == 1: return ss[0].name()
    comp = {_stem(c.lower()) for c in company}
    best, score = None, -1
    for s in ss:
        v = len(_context_of(s.name()) & comp)
        if v > score: best, score = s.name(), v
    return best if score > 0 else ss[0].name()

def family(word, company, depth=1):
    """The near-words of the sense meant here — its own names,
    its kind, and its kinds' names."""
    name = pick(word, company)
    if not name: return {word}
    s = wn.synset(name)
    out = {l.name().lower().replace("_", " ") for l in s.lemmas()}
    rels = s.hypernyms() + s.hyponyms() + s.similar_tos()
    for r in rels[:6]:
        for l in r.lemmas():
            out.add(l.name().lower().replace("_", " "))
    return {w for w in out if len(w) > 3}

def same_sense(word, company_a, company_b):
    """Is this word carrying the same sense in both places?"""
    a, b = pick(word, company_a), pick(word, company_b)
    if not a or not b: return True
    if a == b: return True
    sa, sb = wn.synset(a), wn.synset(b)
    return bool(set(sa.hypernyms()) & set(sb.hypernyms()))
