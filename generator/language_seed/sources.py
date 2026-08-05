"""sources.py -- one class per data source, unified lookup(word) API.

GL-CMD-LANGUAGE-SEED-PHASE2-GENERATOR-EVE-20260707-v1.

Each Source class exposes:
  - .lookup(word: str) -> Optional[dict]   (source-specific fields, None if absent)
  - a bulk-preload step (called once by generate.py) that builds the
    in-memory index a run needs, downloading + caching the raw corpus
    under config.SOURCE_CACHE_DIR if it isn't already there.

Sources integrated (all free/open, no paid licensing):
  WordNetSource     -- WordNet 3.1 via nltk (primary vocabulary + synsets)
  ScowlSource       -- SCOWL 2020.12.07 official release, final/ word lists
                        (word-list coverage supplement; the SAME data Linux
                        distro dictionary packages like wamerican are built
                        from)
  FrequencySource   -- HermitDave FrequencyWords en_50k.txt (OpenSubtitles-
                        derived). SUBSTITUTES for the dispatch's named
                        "COCA + Oxford top-50k" -- both are paid/gated
                        corpora with no free bulk access; this is the
                        standard free open alternative used for the same
                        purpose (frequency-based tiering). Flagged as a
                        finding, not silently swapped.
  ConceptNetSource  -- ConceptNet 5.7.0 full assertions dump (the actual
                        data, not the frequently-unreliable public API --
                        api.conceptnet.io returned 502 throughout this
                        build), CC-BY-SA 4.0 + component licenses.
  ImageNetSource    -- ILSVRC-1000 synset list (the canonical "ImageNet
                        class hierarchy" reference set used throughout ML
                        tooling) cross-referenced against WordNet noun
                        synset offsets -- NOT the full ImageNet-21k corpus,
                        which requires a gated image-net.org account.
                        Flagged as a scope substitution.
  CmuDictSource     -- CMU Pronouncing Dictionary via nltk
  NrcEmotionSource  -- NRC Emotion Lexicon (word-level v0.92)
  NrcVadSource      -- NRC Valence-Arousal-Dominance Lexicon
  WarrinerSource    -- Warriner/Kuperman/Brysbaert (2013) affect ratings
  UDSource          -- Universal Dependencies English EWT treebank
                        (POS transition frequencies)
  Oxford API        -- NOT integrated. No licensing arranged (dispatch:
                        "Oxford API only if licensing arranged (else
                        halt)"). Per the Phase 1 dispatch's own framing
                        ("Paid sources... otherwise WordNet + supplements
                        cover most needs"), omitting it is not a full-
                        generator halt -- just no Oxford-sourced content
                        anywhere in this seed.
"""

from __future__ import annotations

import csv
import gzip
import hashlib
import io
import json
import os
import re
import urllib.request
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple

from generator.language_seed import config

_WORD_RE = re.compile(r"^[a-z]+(?:[-'][a-z]+)*$")


def normalize_word(w: str) -> str:
    return w.strip().lower().replace("_", " ")


def is_wellformed_word(w: str) -> bool:
    """Alphabetic, allows internal hyphen/apostrophe, no digits/punctuation
    runs. Applied per-token for multi-word phrases."""
    return bool(_WORD_RE.match(w))


def _download(url: str, dest: str, timeout: int = 120) -> None:
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    req = urllib.request.Request(url, headers={"User-Agent": "guala-language-seed-generator/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp, open(dest, "wb") as f:
        f.write(resp.read())


# ---------------------------------------------------------------------------
# WordNet
# ---------------------------------------------------------------------------

@dataclass
class WordNetEntry:
    word: str
    pos_set: Set[str] = field(default_factory=set)          # {'n','v','a','r'}
    lexnames: Counter = field(default_factory=Counter)       # 'noun.animal' -> count
    primary_lexname: Optional[str] = None
    definition: Optional[str] = None
    synonyms: Set[str] = field(default_factory=set)
    hypernyms: Set[str] = field(default_factory=set)
    hyponyms: Set[str] = field(default_factory=set)
    familiarity: int = 0                                     # max sense-tagged corpus count
    synset_names: List[str] = field(default_factory=list)    # e.g. ['dog.n.01']
    is_concrete: bool = False
    primary_hypernym: Optional[str] = None                    # direct hypernym of the primary sense only


class WordNetSource:
    """Primary vocabulary + synsets. NLTK WordNet 3.1, permissive license."""

    def __init__(self):
        self._wn = None
        self.index: Dict[str, WordNetEntry] = {}
        self._imagenet_synsets: Set[str] = set()  # populated by ImageNetSource, used for is_concrete override
        self._primary_familiarity: Dict[str, int] = {}

    def _ensure_nltk_data(self):
        import nltk
        for pkg, path in [("wordnet", "corpora/wordnet"), ("omw-1.4", "corpora/omw-1.4")]:
            try:
                nltk.data.find(path)
            except LookupError:
                nltk.download(pkg, quiet=True)

    def preload(self) -> int:
        self._ensure_nltk_data()
        from nltk.corpus import wordnet as wn
        self._wn = wn

        physical = wn.synset("physical_entity.n.01")

        for synset in wn.all_synsets():
            pos = synset.pos()  # n, v, a, s, r
            pos_key = "a" if pos == "s" else pos
            lexname = synset.lexname()
            definition = synset.definition()
            hyper_lemmas = {l.name().replace("_", " ").lower()
                             for h in synset.hypernyms() for l in h.lemmas()}
            hypo_lemmas = {l.name().replace("_", " ").lower()
                            for h in synset.hyponyms() for l in h.lemmas()}
            concrete = False
            if pos_key == "n":
                try:
                    concrete = physical in set(synset.closure(lambda s: s.hypernyms())) or synset == physical
                except Exception:
                    concrete = False

            lemma_words = [l.name().replace("_", " ").lower() for l in synset.lemmas()]
            synonyms = set(lemma_words)

            for lemma in synset.lemmas():
                word = lemma.name().replace("_", " ").lower()
                if not all(is_wellformed_word(tok) for tok in word.split(" ")):
                    continue
                entry = self.index.get(word)
                if entry is None:
                    entry = WordNetEntry(word=word)
                    self.index[word] = entry
                entry.pos_set.add(pos_key)
                entry.lexnames[lexname] += 1
                entry.synonyms.update(synonyms - {word})
                entry.hypernyms.update(hyper_lemmas - {word})
                entry.hyponyms.update(hypo_lemmas - {word})
                entry.synset_names.append(synset.name())
                count = 0
                try:
                    count = lemma.count()
                except Exception:
                    count = 0
                if count > entry.familiarity:
                    entry.familiarity = count
                if entry.definition is None:
                    entry.definition = definition
                # Primary sense = highest corpus-tagged (SemCor) familiarity,
                # not raw sense-count-per-lexname -- a word like "dog" has 3
                # noun.person slang senses vs. 1 noun.animal sense, but the
                # animal sense is the actually-common one; familiarity
                # reflects real usage, sense enumeration order doesn't.
                best_so_far = self._primary_familiarity.get(word, -1)
                if count > best_so_far:
                    self._primary_familiarity[word] = count
                    entry.primary_lexname = lexname
                    entry.definition = definition
                    entry.is_concrete = concrete
                    direct_hypers = synset.hypernyms()
                    if direct_hypers:
                        first_lemma = direct_hypers[0].lemmas()[0].name().replace("_", " ").lower()
                        entry.primary_hypernym = first_lemma if first_lemma != word else None
                    else:
                        entry.primary_hypernym = None

        for entry in self.index.values():
            if entry.primary_lexname is None and entry.lexnames:
                entry.primary_lexname = entry.lexnames.most_common(1)[0][0]

        return len(self.index)

    def lookup(self, word: str) -> Optional[WordNetEntry]:
        return self.index.get(normalize_word(word))

    def synset_from_noun_offset(self, offset: int):
        return self._wn.synset_from_pos_and_offset("n", offset)


# ---------------------------------------------------------------------------
# SCOWL
# ---------------------------------------------------------------------------

class ScowlSource:
    """Official SCOWL 2020.12.07 release, final/ pre-built size-tiered word
    lists (size10 = most common ... size95 = most obscure). Covers common
    words WordNet misses (contractions, proper-name-adjacent forms, etc.)."""

    URL = "https://downloads.sourceforge.net/project/wordlist/SCOWL/2020.12.07/scowl-2020.12.07.zip"
    TIERS = [10, 20, 35, 40, 50, 55, 60, 70, 80, 95]

    def __init__(self, max_tier: int = 70):
        self.max_tier = max_tier
        self.index: Dict[str, int] = {}  # word -> best (lowest) tier seen

    def _final_dir(self) -> str:
        return config.source_path("scowl_final")

    def _ensure_cached(self):
        final_dir = self._final_dir()
        if os.path.isdir(final_dir) and os.listdir(final_dir):
            return
        zpath = config.source_path("scowl.zip")
        if not os.path.exists(zpath):
            _download(self.URL, zpath, timeout=120)
        import zipfile
        with zipfile.ZipFile(zpath) as zf:
            os.makedirs(final_dir, exist_ok=True)
            for name in zf.namelist():
                if name.startswith("final/") and not name.endswith("/"):
                    target = os.path.join(final_dir, os.path.basename(name))
                    with zf.open(name) as src, open(target, "wb") as dst:
                        dst.write(src.read())

    def preload(self) -> int:
        self._ensure_cached()
        final_dir = self._final_dir()
        # Only the core American/British/Canadian + variant word/upper lists,
        # skip abbreviations/contractions/proper-names special categories
        # tier-filtered to max_tier (lower tier = more common/standard).
        wanted_prefixes = (
            "english-words.", "american-words.", "british-words.",
            "british_z-words.", "canadian-words.", "variant_1-words.",
            "variant_2-words.",
        )
        for fname in sorted(os.listdir(final_dir)):
            m = re.match(r"^(.*)\.(\d+)$", fname)
            if not m:
                continue
            base, tier_s = m.group(1), m.group(2)
            tier = int(tier_s)
            if tier > self.max_tier:
                continue
            if not any((base + ".").startswith(p) for p in wanted_prefixes):
                continue
            path = os.path.join(final_dir, fname)
            with open(path, "r", encoding="iso-8859-1") as f:
                for line in f:
                    w = line.strip().lower()
                    if not w or not is_wellformed_word(w):
                        continue
                    prev = self.index.get(w)
                    if prev is None or tier < prev:
                        self.index[w] = tier
        return len(self.index)

    def lookup(self, word: str) -> Optional[int]:
        return self.index.get(normalize_word(word))


# ---------------------------------------------------------------------------
# Frequency (substitutes COCA + Oxford top-50k -- see module docstring)
# ---------------------------------------------------------------------------

class FrequencySource:
    URL = "https://raw.githubusercontent.com/hermitdave/FrequencyWords/master/content/2018/en/en_50k.txt"

    def __init__(self):
        self.rank: Dict[str, int] = {}
        self.count: Dict[str, int] = {}

    def preload(self) -> int:
        path = config.source_path("freq_en_50k.txt")
        if not os.path.exists(path):
            _download(self.URL, path)
        with open(path, encoding="utf-8") as f:
            for i, line in enumerate(f):
                parts = line.strip().split()
                if len(parts) != 2:
                    continue
                word, cnt = parts
                word = word.lower()
                if word not in self.rank:
                    self.rank[word] = i
                    self.count[word] = int(cnt)
        return len(self.rank)

    def lookup(self, word: str) -> Optional[Tuple[int, int]]:
        w = normalize_word(word)
        if w in self.rank:
            return (self.rank[w], self.count[w])
        return None


# ---------------------------------------------------------------------------
# CMU Pronouncing Dictionary
# ---------------------------------------------------------------------------

class CmuDictSource:
    def __init__(self):
        self.index: Dict[str, List[List[str]]] = {}

    def preload(self) -> int:
        import nltk
        try:
            nltk.data.find("corpora/cmudict")
        except LookupError:
            nltk.download("cmudict", quiet=True)
        from nltk.corpus import cmudict
        self.index = cmudict.dict()
        return len(self.index)

    def lookup(self, word: str) -> Optional[List[List[str]]]:
        w = normalize_word(word)
        if " " in w:
            return None
        return self.index.get(w)


# ---------------------------------------------------------------------------
# NRC Emotion Lexicon
# ---------------------------------------------------------------------------

EMOTION_KEYS = ["anger", "anticipation", "disgust", "fear", "joy",
                "negative", "positive", "sadness", "surprise", "trust"]


class NrcEmotionSource:
    def __init__(self):
        self.index: Dict[str, Dict[str, int]] = {}

    def preload(self) -> int:
        path = config.source_path("nrc_emotion_wordlevel.txt")
        with open(path, encoding="utf-8") as f:
            for line in f:
                parts = line.rstrip("\n").split("\t")
                if len(parts) != 3:
                    continue
                word, emo, val = parts
                word = word.lower()
                if emo not in EMOTION_KEYS:
                    continue
                self.index.setdefault(word, {})[emo] = int(val)
        return len(self.index)

    def lookup(self, word: str) -> Optional[Dict[str, int]]:
        return self.index.get(normalize_word(word))


# ---------------------------------------------------------------------------
# NRC VAD Lexicon
# ---------------------------------------------------------------------------

class NrcVadSource:
    def __init__(self):
        self.index: Dict[str, Tuple[float, float, float]] = {}

    def preload(self) -> int:
        path = config.source_path("nrc_vad.txt")
        with open(path, encoding="utf-8") as f:
            for line in f:
                parts = line.rstrip("\n").split("\t")
                if len(parts) != 4:
                    continue
                word, v, a, d = parts
                try:
                    self.index[word.lower()] = (float(v), float(a), float(d))
                except ValueError:
                    continue
        return len(self.index)

    def lookup(self, word: str) -> Optional[Tuple[float, float, float]]:
        return self.index.get(normalize_word(word))


# ---------------------------------------------------------------------------
# Warriner et al. affect ratings
# ---------------------------------------------------------------------------

class WarrinerSource:
    def __init__(self):
        self.index: Dict[str, Tuple[float, float, float]] = {}

    def preload(self) -> int:
        path = config.source_path("warriner.csv")
        with open(path, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                word = row.get("Word", "").strip().lower()
                if not word:
                    continue
                try:
                    v = float(row["V.Mean.Sum"])
                    a = float(row["A.Mean.Sum"])
                    d = float(row["D.Mean.Sum"])
                except (ValueError, KeyError):
                    continue
                self.index[word] = (v, a, d)
        return len(self.index)

    def lookup(self, word: str) -> Optional[Tuple[float, float, float]]:
        return self.index.get(normalize_word(word))


# ---------------------------------------------------------------------------
# ConceptNet 5.7 (real assertions dump, not the API -- api.conceptnet.io
# returned 502 throughout this build)
# ---------------------------------------------------------------------------

_CN_URI_RE = re.compile(r"^/c/en/([^/]+)(?:/([a-z]))?")

RELATION_WEIGHTS = {
    "/r/Synonym": 0.95, "/r/IsA": 0.9, "/r/InstanceOf": 0.85,
    "/r/PartOf": 0.75, "/r/HasA": 0.7, "/r/MadeOf": 0.65,
    "/r/UsedFor": 0.7, "/r/CapableOf": 0.65, "/r/AtLocation": 0.6,
    "/r/HasProperty": 0.7, "/r/HasContext": 0.5, "/r/SimilarTo": 0.8,
    "/r/Causes": 0.6, "/r/CausesDesire": 0.55, "/r/MotivatedByGoal": 0.5,
    "/r/Desires": 0.55, "/r/DerivedFrom": 0.6, "/r/RelatedTo": 0.35,
    "/r/Antonym": 0.3, "/r/DistinctFrom": 0.2, "/r/EtymologicallyRelatedTo": 0.4,
    "/r/FormOf": 0.8, "/r/HasSubevent": 0.5, "/r/HasFirstSubevent": 0.5,
    "/r/HasLastSubevent": 0.5, "/r/HasPrerequisite": 0.5, "/r/ReceivesAction": 0.5,
    "/r/CreatedBy": 0.5, "/r/Entails": 0.55, "/r/MannerOf": 0.5,
    "/r/LocatedNear": 0.4, "/r/SymbolOf": 0.4, "/r/DefinedAs": 0.6,
}
DEFAULT_RELATION_WEIGHT = 0.3


class ConceptNetSource:
    """Streams the official ConceptNet 5.7.0 assertions dump once, filters
    to en-en edges touching the target vocabulary, and caches a compact
    per-word index so repeat runs (and both layer passes) don't re-parse
    the 34M-edge dump."""

    DUMP_URL = "https://s3.amazonaws.com/conceptnet/downloads/2019/edges/conceptnet-assertions-5.7.0.csv.gz"

    def __init__(self):
        self.index: Dict[str, List[Tuple[str, str, float]]] = defaultdict(list)

    @staticmethod
    def _parse_uri(uri: str) -> Optional[str]:
        m = _CN_URI_RE.match(uri)
        if not m:
            return None
        word = m.group(1).replace("_", " ").lower()
        return word

    def build_index(self, vocab: Set[str], cache_name: str = "conceptnet_index.json") -> int:
        cache_path = config.source_path(cache_name)
        if os.path.exists(cache_path):
            with open(cache_path, encoding="utf-8") as f:
                raw = json.load(f)
            self.index = defaultdict(list, {k: [tuple(e) for e in v] for k, v in raw.items()})
            return len(self.index)

        dump_path = config.source_path("conceptnet-assertions-5.7.0.csv.gz")
        if not os.path.exists(dump_path):
            _download(self.DUMP_URL, dump_path, timeout=600)

        seen_pairs = set()
        with gzip.open(dump_path, "rt", encoding="utf-8", errors="ignore") as f:
            for line in f:
                parts = line.rstrip("\n").split("\t")
                if len(parts) < 4:
                    continue
                _, relation, start_uri, end_uri = parts[0], parts[1], parts[2], parts[3]
                if not (start_uri.startswith("/c/en/") and end_uri.startswith("/c/en/")):
                    continue
                start = self._parse_uri(start_uri)
                end = self._parse_uri(end_uri)
                if not start or not end or start == end:
                    continue
                in_vocab_start = start in vocab
                in_vocab_end = end in vocab
                if not (in_vocab_start or in_vocab_end):
                    continue
                weight = RELATION_WEIGHTS.get(relation, DEFAULT_RELATION_WEIGHT)
                key = (start, relation, end)
                if key in seen_pairs:
                    continue
                seen_pairs.add(key)
                if in_vocab_start and end:
                    self.index[start].append((relation, end, weight))
                if in_vocab_end and start:
                    self.index[end].append((relation, start, weight))

        # cap fan-out per word (keep highest-weight edges) to bound output size
        for word, edges in self.index.items():
            if len(edges) > 40:
                edges.sort(key=lambda e: -e[2])
                self.index[word] = edges[:40]

        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump({k: v for k, v in self.index.items()}, f)

        return len(self.index)

    def lookup(self, word: str) -> List[Tuple[str, str, float]]:
        return self.index.get(normalize_word(word), [])


# ---------------------------------------------------------------------------
# ImageNet (ILSVRC-1000 canonical class set, WordNet-synset-aligned -- see
# module docstring for the full-21k scope note)
# ---------------------------------------------------------------------------

class ImageNetSource:
    URL = "https://raw.githubusercontent.com/formigone/tf-imagenet/master/LOC_synset_mapping.txt"

    def __init__(self, wordnet_source: WordNetSource):
        self._wn_source = wordnet_source
        self.synset_names: Set[str] = set()      # e.g. {'tench.n.01', ...}
        self.grounded_lemma_words: Set[str] = set()  # words in/ancestor-of/descendant-of the 1000

    def preload(self) -> int:
        path = config.source_path("imagenet_synset_mapping.txt")
        if not os.path.exists(path):
            _download(self.URL, path)

        wn = self._wn_source
        import nltk
        try:
            nltk.data.find("corpora/wordnet")
        except LookupError:
            nltk.download("wordnet", quiet=True)
        from nltk.corpus import wordnet as _wn

        anchor_synsets = []
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                wnid, _labels = line.split(" ", 1)
                offset = int(wnid[1:])
                try:
                    synset = _wn.synset_from_pos_and_offset("n", offset)
                except Exception:
                    continue
                anchor_synsets.append(synset)
                self.synset_names.add(synset.name())
                for lemma in synset.lemmas():
                    self.grounded_lemma_words.add(lemma.name().replace("_", " ").lower())

        # broaden to ancestors (superordinate categories, e.g. "animal") and
        # descendants (more specific instances) -- both have a legitimate
        # visual grounding via the same ImageNet-anchored subtree.
        for synset in anchor_synsets:
            for anc in synset.closure(lambda s: s.hypernyms()):
                for lemma in anc.lemmas():
                    self.grounded_lemma_words.add(lemma.name().replace("_", " ").lower())
            for desc in synset.closure(lambda s: s.hyponyms()):
                for lemma in desc.lemmas():
                    self.grounded_lemma_words.add(lemma.name().replace("_", " ").lower())

        return len(self.grounded_lemma_words)

    def lookup(self, word: str) -> bool:
        return normalize_word(word) in self.grounded_lemma_words


# ---------------------------------------------------------------------------
# Universal Dependencies English EWT (POS transition frequencies)
# ---------------------------------------------------------------------------

class UDSource:
    FILES_URL_TEMPLATE = (
        "https://raw.githubusercontent.com/UniversalDependencies/"
        "UD_English-EWT/master/{fname}"
    )
    FILES = ["en_ewt-ud-train.conllu", "en_ewt-ud-dev.conllu", "en_ewt-ud-test.conllu"]

    def __init__(self):
        self.transition_counts: Counter = Counter()   # (upos_i, upos_j) -> count
        self.word_pos_counts: Dict[str, Counter] = defaultdict(Counter)  # word -> {UPOS: count}
        self.pos_totals: Counter = Counter()

    def preload(self) -> int:
        ud_dir = config.source_path("ud_ewt")
        os.makedirs(ud_dir, exist_ok=True)
        total_sentences = 0
        for fname in self.FILES:
            path = os.path.join(ud_dir, fname)
            if not os.path.exists(path):
                _download(self.FILES_URL_TEMPLATE.format(fname=fname), path)
            sentence_pos: List[str] = []
            with open(path, encoding="utf-8") as f:
                for line in f:
                    line = line.rstrip("\n")
                    if not line:
                        if len(sentence_pos) >= 2:
                            for i in range(len(sentence_pos) - 1):
                                self.transition_counts[(sentence_pos[i], sentence_pos[i + 1])] += 1
                        if sentence_pos:
                            total_sentences += 1
                        sentence_pos = []
                        continue
                    if line.startswith("#"):
                        continue
                    cols = line.split("\t")
                    if len(cols) < 4:
                        continue
                    tok_id, form, lemma, upos = cols[0], cols[1], cols[2], cols[3]
                    if "-" in tok_id or "." in tok_id:
                        continue  # multiword-token / empty-node lines
                    sentence_pos.append(upos)
                    word = form.lower()
                    self.word_pos_counts[word][upos] += 1
                    self.pos_totals[upos] += 1
        return total_sentences

    def lookup(self, word: str) -> Optional[str]:
        """Most frequent observed UPOS tag for this word form, if any."""
        counts = self.word_pos_counts.get(normalize_word(word))
        if not counts:
            return None
        return counts.most_common(1)[0][0]

    def transition_weight(self, pos_a: str, pos_b: str) -> float:
        total = self.pos_totals.get(pos_a, 0)
        if total == 0:
            return 0.0
        return self.transition_counts.get((pos_a, pos_b), 0) / total
