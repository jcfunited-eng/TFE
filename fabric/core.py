"""THE CORE — the knowledge, loaded once and made fast.

Everything above this file treats knowledge as the processor: an
entry is not a record to search, it is a piece of machinery with
a colored face (what it says stands) and a white face (what it
forbids). This file turns the written corpus into the discrete
form that machinery runs on, and nothing here decides anything.

Discrete throughout: every word is an integer, every word-set is
a bitmask, every law is a pair of masks, and judging is bitwise.
No model is consulted anywhere in this file or anything under it.

  vocabulary   word  -> integer id
  entry        colored mask, white mask, ask mask, thread names
  law          (needs mask, then mask, kind, source entry)
  reach index  word id -> entries carrying it

Loaded once and cached against the corpus signature, so an edit
to any entry is picked up on the next call and nothing else is.
"""
import os, re, glob, hashlib, time

DIR = os.path.normpath(os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..", "docs", "fabric_phylums"))
WHITE_SHEET = os.path.join(DIR, "99_the_white.md")

# Words dropped before anything is read. This list is my hand, so
# it is kept to words that carry no subject of their own — never
# to words a procedure might name a doing with. "up", "down",
# "out", "one" and the small numbers were in here once, and the
# counting-down act could not be reached because the very word
# that names it was being thrown away.
STOP = set("""the a an is are of in on at to for with by from and or
not no it its this that what why how when does do same other own
there they if then than as but so off over more most less very
much many few all any some none each every way ways get got can
could would should will shall may might must have has had been
was were being you your our his her him she he them their into
onto upon about just also even still yet too now here make made
makes thing things""".split())

def stem(w):
    for s in ("ing", "ers", "er", "ed", "es", "s", "ly"):
        if w.endswith(s) and len(w) - len(s) >= 3:
            return w[:len(w) - len(s)]
    return w

class Fabric:
    """The corpus in discrete form. One instance, rebuilt only when
    the written knowledge changes."""

    def __init__(self):
        self.sig = None
        self.build()

    # ---------- signature: cheap, catches every edit ----------
    def signature(self):
        h = hashlib.sha256()
        for f in sorted(glob.glob(os.path.join(DIR, "[0-9][0-9]*_*.md"))):
            st = os.stat(f)
            h.update(f.encode())
            h.update(str(st.st_mtime_ns).encode())
            h.update(str(st.st_size).encode())
        return h.hexdigest()[:16]

    _checked = 0.0
    CHECK_EVERY = 2.0        # seconds; an edit is seen within this

    def fresh(self, force=False):
        now = time.monotonic()
        if not force and now - self._checked < self.CHECK_EVERY:
            return self
        self._checked = now
        if self.signature() != self.sig:
            self.build()
        return self

    # ---------- vocabulary ----------
    def wid(self, word):
        i = self.vocab.get(word)
        if i is None:
            i = len(self.words)
            self.vocab[word] = i
            self.words.append(word)
        return i

    def mask(self, text, learn=True):
        m = 0
        for raw in re.findall(r"[a-z]+", text.lower()):
            if raw in STOP or len(raw) < 3: continue
            w = stem(raw)
            if w in STOP: continue
            i = self.vocab.get(w)
            if i is None:
                if not learn: continue
                i = self.wid(w)
            m |= 1 << i
        return m

    def words_of(self, mask):
        out = []
        i = 0
        while mask:
            if mask & 1: out.append(self.words[i])
            mask >>= 1; i += 1
        return out

    # ---------- build ----------
    def build(self):
        t0 = time.perf_counter()
        self.vocab, self.words = {}, []
        self.entries = []
        self.fields = {}
        for path in sorted(glob.glob(os.path.join(DIR,
                                                  "[0-9][0-9]*_*.md"))):
            if path.endswith("99_the_white.md"): continue
            field = re.sub(r"^\d+_|\.md$", "",
                           os.path.basename(path)).replace("_", " ")
            text = open(path).read()
            for block in re.split(r"\n(?=ESSENCE:)", text):
                if not block.startswith("ESSENCE:"): continue
                if "STATE: FADED" in block: continue
                def part(tag):
                    m = re.search(rf"{tag}:(.*?)(?=\n[A-Z-]+:|\Z)",
                                  block, re.S)
                    return re.sub(r"\s+", " ",
                                  m.group(1)).strip() if m else ""
                e = dict(field=field, file=path,
                         essence=part("ESSENCE"),
                         cannot=part("CANNOT"),
                         ask=part("ASKED-AS"),
                         rule=part("RULE"),
                         thread=part("THREAD"),
                         root=part("ROOT"))
                e["id"] = len(self.entries)
                e["color"] = self.mask(e["essence"])      # possible face
                e["white"] = self.mask(e["cannot"])       # impossible face
                e["askm"] = self.mask(e["ask"])
                e["reach"] = e["color"] | e["askm"]
                self.entries.append(e)
                self.fields.setdefault(field, []).append(e["id"])
        self.build_laws()
        self.build_index()
        self.sig = self.signature()
        self.built_ms = (time.perf_counter() - t0) * 1000
        return self

    # ---------- laws, parsed from the entries' own words ----------
    def build_laws(self):
        self.laws = []
        for e in self.entries:
            for piece in re.split(r"(?<=[.;])\s+", e["cannot"]):
                p = piece.strip()
                if not p: continue
                low = p.lower()
                m = re.search(r"\bno(?:thing)? (.+?) without (.+)", low)
                if m:
                    a, b = self.mask(m.group(1)), self.mask(m.group(2))
                    if a and b:
                        self.laws.append(dict(kind="requires", a=a,
                                              b=b, src=e["id"],
                                              text=p))
                    continue
                m = re.search(r"\bno (.+?) (?:in|from|with) (.+)", low)
                if m:
                    a, b = self.mask(m.group(1)), self.mask(m.group(2))
                    if a and b and not (a & b):
                        self.laws.append(dict(kind="forbids", a=a,
                                              b=b, src=e["id"],
                                              text=p))

    # ---------- reach index: word -> entries ----------
    def build_index(self):
        self.index = {}
        self.df = {}
        for e in self.entries:
            seen = e["reach"] | e["white"]
            i, m = 0, seen
            while m:
                if m & 1:
                    self.index.setdefault(i, []).append(e["id"])
                    self.df[i] = self.df.get(i, 0) + 1
                m >>= 1; i += 1

    # ---------- reach: which knowledge a question touches ----------
    def reach(self, question, limit=24):
        qm = self.mask(question, learn=False)
        hits = {}
        i, m = 0, qm
        while m:
            if m & 1:
                rare = 1.0 / max(1, self.df.get(i, 1))
                for eid in self.index.get(i, ()):
                    hits[eid] = hits.get(eid, 0.0) + rare
            m >>= 1; i += 1
        ranked = sorted(hits.items(), key=lambda x: -x[1])[:limit]
        return qm, [self.entries[eid] for eid, _ in ranked]

    # ---------- judging: bitwise, no search ----------
    def judge(self, pool_mask, touch_only=True):
        """Return the first law that closes this pool, or None."""
        for L in self.laws:
            if touch_only:
                srce = self.entries[L["src"]]
                if not (pool_mask & (srce["color"] | srce["white"])):
                    continue
            if L["kind"] == "forbids":
                if (L["a"] & pool_mask) == L["a"] and \
                   bin(L["b"] & pool_mask).count("1") >= \
                   min(2, bin(L["b"]).count("1")):
                    return L
            else:
                if (L["a"] & pool_mask) == L["a"] and \
                   not (L["b"] & pool_mask):
                    return L
        return None

FABRIC = Fabric()

def fabric():
    return FABRIC.fresh()
