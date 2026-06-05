"""
GualaLoom — a substrate that eats language and grows.

Not a transformer. No tokenizer, no embeddings, no gradient descent,
no training step, no model file you load. One substrate. Always the
same six pieces: balanced ternary, 3^i coupling, dead-zone settling,
krimelack motif memory, L6 dimensional exhaustion, familiarity feedback.

GUALALOOM-SENSES-WC-2026-06-05: five modal krimelack channels added.
Word section + sight/sound/smell/taste/touch sections. Atlas records
chi co-occurrence across sections in the same window — that co-occurrence
IS the binding of word to experience. No additional structure required.

Run:  python3 gualaloom_engine.py
"""

import os, sys, json, time, hashlib, glob, re
from collections import OrderedDict, defaultdict

# ----------------------------------------------------------------------
# The substrate. Six pieces. Frozen constants.
# ----------------------------------------------------------------------

P3I = (1, 3, 9, 27, 81, 243, 729, 2187)   # 3^i identity, not a choice
TRITS = 8                                  # trits per character strand
CONTEXT = 8                                # context window (chars). c1
                                           # found 8 >> 4 for variety.
DEAD_ZONE = 15                             # tau, matched to ASCII scale
FAM_GAIN = 20                              # familiarity barrier gain
STATE_DIR = "state"
DREAM_DIR = os.path.join(STATE_DIR, "dreams")


def encode(ch):
    """One character -> 8-trit balanced ternary strand.
    3^i identity holds: sum(trit*weight) reconstructs the value."""
    v = ord(ch) - 96
    t = []
    for _ in range(TRITS):
        r = v % 3
        if r == 2:
            r = -1; v = (v + 1) // 3
        else:
            v = (v - r) // 3
        t.append(r)
    return tuple(t)


def settle(strands, familiarity):
    """The field arrives and settles. A trit at strand s, position i
    commits only if its 3^i-weighted vote plus cross-strand resonance
    at the same position exceeds the dead-zone barrier. Below the
    barrier it stays null — structural uncertainty, first-class."""
    barrier = DEAD_ZONE + familiarity
    out = []
    for s_idx, strand in enumerate(strands):
        for i in range(TRITS):
            h = strand[i] * P3I[i]
            for o_idx, other in enumerate(strands):
                if o_idx != s_idx:
                    h += other[i] * P3I[i] // 2
            out.append(1 if h > barrier else (-1 if h < -barrier else 0))
    return tuple(out)


def l6(state):
    """Dimensional exhaustion. Counts collapsed (non-null) trits.
    Structural lock fires when freedom drops below n/e."""
    n = len(state)
    collapsed = sum(1 for t in state if t != 0)
    eff = n - collapsed
    knee = round(n / 2.718281828459045)
    return eff, collapsed, knee, (1 if eff < knee else 0)


def chi(state):
    """The Euler characteristic that was always in the settled state.
    Vertices = committed trits. Edges = couplings between committed
    trits (intra-strand adjacent, cross-strand same-position). chi =
    V - E. c1 proved real units cluster at characteristic chi values;
    noise scatters. This is the discriminator, computed for free."""
    verts = [i for i, t in enumerate(state) if t != 0]
    vset = set(verts)
    V = len(verts)
    if V == 0:
        return 0, 0
    E = 0
    # intra-strand adjacency
    for i in verts:
        if (i + 1) in vset and (i + 1) % TRITS != 0:
            E += 1
    # cross-strand same-position
    n_strands = len(state) // TRITS
    for pos in range(TRITS):
        committed = [s for s in range(n_strands) if state[s*TRITS+pos] != 0]
        E += max(len(committed) - 1, 0)   # chain them
    return V - E, V


# ----------------------------------------------------------------------
# Krimelack. Motif memory. Persists. Recalls by topology then geometry.
# ----------------------------------------------------------------------

class Motif:
    __slots__ = ("fp", "state", "weight", "age", "chi", "V",
                 "char_counts", "successors")
    def __init__(self, fp, state, c, v):
        self.fp = fp; self.state = state; self.weight = 1; self.age = 0
        self.chi = c; self.V = v
        self.char_counts = defaultdict(int)
        self.successors = defaultdict(int)   # fp -> count

    def to_dict(self):
        return {"fp": self.fp, "state": list(self.state),
                "weight": self.weight, "age": self.age, "chi": self.chi,
                "V": self.V, "char_counts": dict(self.char_counts),
                "successors": dict(self.successors)}

    @staticmethod
    def from_dict(d):
        m = Motif(d["fp"], tuple(d["state"]), d["chi"], d["V"])
        m.weight = d["weight"]; m.age = d["age"]
        m.char_counts = defaultdict(int, d["char_counts"])
        m.successors = defaultdict(int, {k: v for k, v in d["successors"].items()})
        return m


def _fp(state):
    s = "".join({-1: "-", 0: "0", 1: "+"}[t] for t in state)
    return hashlib.sha1(s.encode()).hexdigest()[:12]


class Krimelack:
    def __init__(self):
        self.motifs = OrderedDict()
        self.last_fp = None

    def commit(self, state, active_char=None):
        if all(t == 0 for t in state):
            return None, False
        fp = _fp(state)
        new = fp not in self.motifs
        if new:
            c, v = chi(state)
            self.motifs[fp] = Motif(fp, state, c, v)
        m = self.motifs[fp]
        m.weight += 1; m.age = 0
        if active_char is not None:
            m.char_counts[active_char] += 1
        if self.last_fp and self.last_fp != fp and self.last_fp in self.motifs:
            self.motifs[self.last_fp].successors[fp] += 1
        self.last_fp = fp
        return fp, new

    def recall(self, state):
        """Topology first: only motifs sharing the query's chi are real
        candidates. Geometry ranks within that pool. If the chi class
        is empty (novel topology), fall back to global geometric recall
        and report it honestly as low-confidence."""
        if not self.motifs:
            return None, 0
        qchi, _ = chi(state)
        pool = [m for m in self.motifs.values() if m.chi == qchi]
        if not pool:
            pool = list(self.motifs.values())   # novel topology
        best, best_score = None, -1
        for m in pool:
            score = sum(1 for a, b in zip(state, m.state) if a == b and a != 0)
            # weight breaks ties toward established motifs
            score = score * 100 + min(m.weight, 99)
            if score > best_score:
                best, best_score = m, score
        return best, best_score

    def decay(self, rate=1):
        dead = []
        for fp, m in self.motifs.items():
            m.weight -= rate
            if m.weight <= 0 and m.age > 8:
                dead.append(fp)
            else:
                m.weight = max(m.weight, 0); m.age += 1
        for fp in dead:
            del self.motifs[fp]
        return len(dead)

    def size(self):
        return len(self.motifs)


# ----------------------------------------------------------------------
# ChiAtlas — cross-section binding via chi co-occurrence.
# When the word section and a modal section commit in the same window
# at chi values within ±BAND of each other, the atlas records binding.
# Soft-band approach: recording stores exact chi, binding checks use
# |chi_a - chi_b| <= delta. This keeps the substrate's chi mechanics
# untouched — only the binding criterion softens.
# ----------------------------------------------------------------------

CHI_BAND = 2  # δ: two commits bind if |chi_a - chi_b| <= CHI_BAND


class ChiAtlas:
    """Records chi-state co-occurrence across sections.
    Binding uses soft chi-band overlap (±CHI_BAND) so modalities with
    different component counts (and therefore different chi distributions)
    can still bind with the word section."""

    def __init__(self):
        self.entries = defaultdict(list)  # chi -> [(section, fp, tick)]

    def record(self, chi_val, section_name, motif_fp, tick):
        self.entries[chi_val].append({
            "section": section_name, "fp": motif_fp, "tick": tick
        })

    def _band_neighbors(self, chi_val):
        """Return all chi values in entries within ±CHI_BAND of chi_val."""
        return [c for c in self.entries if abs(c - chi_val) <= CHI_BAND]

    def _band_sections(self, chi_val):
        """Collect all distinct sections across chi values in the band."""
        sections = set()
        for neighbor in self._band_neighbors(chi_val):
            for claim in self.entries[neighbor]:
                sections.add(claim["section"])
        return sections

    def cross_modal_count(self):
        """Count chi values whose ±CHI_BAND band includes ≥2 distinct sections."""
        counted = set()
        count = 0
        for chi_val in self.entries:
            if chi_val in counted:
                continue
            band = self._band_neighbors(chi_val)
            sections = set()
            for b in band:
                counted.add(b)
                for claim in self.entries[b]:
                    sections.add(claim["section"])
            if len(sections) >= 2:
                count += 1
        return count

    def cross_modal_examples(self, n=5):
        """Return up to n examples of cross-modal binding (band-aware)."""
        examples = []
        seen = set()
        for chi_val in sorted(self.entries.keys()):
            if chi_val in seen:
                continue
            band = self._band_neighbors(chi_val)
            sections = set()
            total_claims = 0
            for b in band:
                seen.add(b)
                for claim in self.entries[b]:
                    sections.add(claim["section"])
                total_claims += len(self.entries[b])
            if len(sections) >= 2:
                examples.append({
                    "chi": chi_val,
                    "band": [min(band), max(band)],
                    "sections": sorted(sections),
                    "claims": total_claims,
                })
                if len(examples) >= n:
                    break
        return examples

    def section_participation(self):
        """Count how many cross-modal bands each section participates in."""
        participation = defaultdict(int)
        seen = set()
        for chi_val in self.entries:
            if chi_val in seen:
                continue
            band = self._band_neighbors(chi_val)
            sections = set()
            for b in band:
                seen.add(b)
                for claim in self.entries[b]:
                    sections.add(claim["section"])
            if len(sections) >= 2:
                for sec in sections:
                    participation[sec] += 1
        return dict(participation)

    def to_dict(self):
        return {str(k): v for k, v in self.entries.items()}

    @staticmethod
    def from_dict(d):
        atlas = ChiAtlas()
        for k, v in d.items():
            atlas.entries[int(k)] = v
        return atlas


# ----------------------------------------------------------------------
# Loom. The continuous field. Ticks on every character.
# Now also fires modal krimelacks when words have sensory experiences.
# ----------------------------------------------------------------------

# Lazy import to avoid circular deps — these are only needed when
# the sensory substrate is active.
_sensory_corpus = None
_sensory_krimelacks = None

def _load_sensory():
    global _sensory_corpus, _sensory_krimelacks
    if _sensory_corpus is None:
        try:
            from dsf_ai_service.sensory_corpus import SENSORY_EXPERIENCES, MODALITIES
            from dsf_ai_service.sensory_krimelacks import transduce_to_trit_state
            _sensory_corpus = (SENSORY_EXPERIENCES, MODALITIES)
            _sensory_krimelacks = transduce_to_trit_state
        except ImportError:
            _sensory_corpus = ({}, [])
            _sensory_krimelacks = None


class Loom:
    def __init__(self, k, modal_sections=None, atlas=None):
        self.k = k                          # word-section krimelack
        self.modal_sections = modal_sections or {}  # name -> Krimelack
        self.atlas = atlas or ChiAtlas()
        self.recent = []
        self.fam = 0
        self.last = tuple([0] * (CONTEXT * TRITS))
        self.tick_count = 0

    def tick(self, ch):
        self.recent.append(ch)
        if len(self.recent) > CONTEXT:
            self.recent.pop(0)
        strands = [encode(c) for c in self.recent]
        # pad to full context with null strands
        while len(strands) < CONTEXT:
            strands.insert(0, tuple([0] * TRITS))
        settled = settle(strands, self.fam)
        m, score = self.k.recall(settled)
        self.fam = (score // 100 * FAM_GAIN) // max(len(settled), 1) if score > 0 else 0
        fp, new = self.k.commit(settled, active_char=ch)
        self.last = settled
        self.tick_count += 1

        # Record word-section chi in atlas
        if fp:
            c, _ = chi(settled)
            self.atlas.record(c, "word", fp, self.tick_count)

        return settled

    def feed(self, text):
        for ch in text:
            self.tick(ch)

    def feed_word(self, word):
        """Feed a single word through the word section AND fire modal
        krimelacks if the word has sensory experiences. All sections
        tick in the same window — atlas records chi co-occurrence."""
        _load_sensory()

        # Word section: feed character by character (existing behavior)
        for ch in word:
            self.tick(ch)

        # Modal sections: fire krimelacks for each modality
        if _sensory_krimelacks is None:
            return

        experiences, modalities = _sensory_corpus
        exp = experiences.get(word.lower())
        if not exp:
            return

        state_len = CONTEXT * TRITS
        for modality in modalities:
            if modality not in exp:
                continue
            component_dict = exp[modality]
            if not component_dict:
                continue

            # Ensure modal section exists
            sec_name = modality + "_sec"
            if sec_name not in self.modal_sections:
                self.modal_sections[sec_name] = Krimelack()

            # Transduce sensory dict through oscillator → trit state
            trit_state, n_events = _sensory_krimelacks(
                modality, component_dict, state_len=state_len
            )

            if n_events == 0:
                continue

            # Commit to modal section
            modal_k = self.modal_sections[sec_name]
            fp, new = modal_k.commit(trit_state, active_char=word.lower())

            if fp:
                c, _ = chi(trit_state)
                self.atlas.record(c, sec_name, fp, self.tick_count)

    def feed_sentence(self, sentence):
        """Feed a sentence: split into words, process each through
        word section + modal sections. Space characters between words
        go to word section only."""
        words = re.findall(r'[a-z]+', sentence.lower())
        for i, word in enumerate(words):
            self.feed_word(word)
            if i < len(words) - 1:
                self.tick(' ')


# ----------------------------------------------------------------------
# Generation. The field speaks by motif recall + successor walk.
# ----------------------------------------------------------------------

def generate(loom, k, max_chars=120):
    out = []
    recent_fps = []
    for _ in range(max_chars):
        m, score = k.recall(loom.last)
        if m is None:
            break
        # familiarity: if we keep landing on the same motif, the
        # substrate is looping. raise the bar — walk to a weaker
        # successor instead of the strongest, to escape the attractor.
        loop_depth = recent_fps[-4:].count(m.fp)
        recent_fps.append(m.fp)
        if m.successors:
            ranked = sorted(m.successors.items(), key=lambda kv: -kv[1])
            # if looping, skip past the dominant successor
            idx = min(loop_depth, len(ranked) - 1)
            nxt_fp = ranked[idx][0]
            nxt = k.motifs.get(nxt_fp)
        else:
            nxt = m
        if nxt is None or not nxt.char_counts:
            break
        # pick char, avoiding immediate repetition when looping
        chars = sorted(nxt.char_counts.items(), key=lambda kv: -kv[1])
        ch = chars[0][0]
        if loop_depth > 0 and len(chars) > 1:
            ch = chars[min(loop_depth, len(chars) - 1)][0]
        out.append(ch)
        loom.tick(ch)
        if loop_depth >= 3:   # stuck — the field has nothing new
            break
    return "".join(out).strip()


# ----------------------------------------------------------------------
# Sleep and dreams. Consolidation + free-settling (Horizon Projection).
# Now runs across ALL sections (word + modal).
# ----------------------------------------------------------------------

def sleep_cycle(k, cycles=200, modal_sections=None):
    """Consolidation across word section and all modal sections."""
    culled = 0
    # Word section
    for fp in list(k.motifs.keys()):
        m = k.motifs[fp]
        m.age += cycles // 50
        m.weight -= 1
    for fp in list(k.motifs.keys()):
        m = k.motifs[fp]
        if m.weight <= 0 and m.age > 8:
            del k.motifs[fp]; culled += 1
        else:
            m.weight = max(m.weight, 1)

    # Modal sections — same consolidation
    modal_culled = {}
    if modal_sections:
        for sec_name, sec_k in modal_sections.items():
            mc = 0
            for fp in list(sec_k.motifs.keys()):
                m = sec_k.motifs[fp]
                m.age += cycles // 50
                m.weight -= 1
            for fp in list(sec_k.motifs.keys()):
                m = sec_k.motifs[fp]
                if m.weight <= 0 and m.age > 8:
                    del sec_k.motifs[fp]; mc += 1
                else:
                    m.weight = max(m.weight, 1)
            if mc > 0:
                modal_culled[sec_name] = mc

    return 0, culled, modal_culled


def dream_cycle(k, cycles=50, modal_sections=None):
    """Free-settle from existing motifs — now cross-modal.
    Word section dreams as before. Modal sections also free-settle,
    and cross-modal dreams can emerge when a word motif's chi
    matches a modal motif's chi during the dream walk."""
    dreams = []

    # Word section dreams (original logic)
    if k.motifs:
        motif_list = list(k.motifs.values())
        cur = motif_list[0].state
        for i in range(cycles):
            strands = [cur[j*TRITS:(j+1)*TRITS] for j in range(len(cur)//TRITS)]
            settled = settle(strands, familiarity=0)
            fp = _fp(settled)
            if any(t != 0 for t in settled):
                new = fp not in k.motifs
                k.commit(settled)
                if new:
                    dreams.append(("word", fp))
            cur = motif_list[(i + 1) % len(motif_list)].state

    # Modal section dreams — cross-modal free-settling
    if modal_sections:
        for sec_name, sec_k in modal_sections.items():
            if not sec_k.motifs:
                continue
            motif_list = list(sec_k.motifs.values())
            cur = motif_list[0].state
            modal_cycles = min(cycles // 2, 25)  # lighter dreaming for modal
            for i in range(modal_cycles):
                # Re-settle with no input drive
                strands = [cur[j*TRITS:(j+1)*TRITS] for j in range(len(cur)//TRITS)]
                settled = settle(strands, familiarity=0)
                fp = _fp(settled)
                if any(t != 0 for t in settled):
                    new = fp not in sec_k.motifs
                    sec_k.commit(settled)
                    if new:
                        dreams.append((sec_name, fp))
                cur = motif_list[(i + 1) % len(motif_list)].state

    return dreams


# ----------------------------------------------------------------------
# Persistence — now saves/loads modal sections and atlas.
# ----------------------------------------------------------------------

def save(k, loom):
    os.makedirs(STATE_DIR, exist_ok=True)
    os.makedirs(DREAM_DIR, exist_ok=True)

    # Word section krimelack
    with open(os.path.join(STATE_DIR, "krimelack.json"), "w") as f:
        json.dump({"motifs": [m.to_dict() for m in k.motifs.values()],
                   "last_fp": k.last_fp}, f)

    # Loom state
    with open(os.path.join(STATE_DIR, "loom.json"), "w") as f:
        json.dump({"recent": loom.recent, "fam": loom.fam,
                   "tick_count": loom.tick_count}, f)

    # Modal sections
    modal_data = {}
    for sec_name, sec_k in loom.modal_sections.items():
        modal_data[sec_name] = {
            "motifs": [m.to_dict() for m in sec_k.motifs.values()],
            "last_fp": sec_k.last_fp,
        }
    with open(os.path.join(STATE_DIR, "modal_sections.json"), "w") as f:
        json.dump(modal_data, f)

    # Atlas
    with open(os.path.join(STATE_DIR, "atlas.json"), "w") as f:
        json.dump(loom.atlas.to_dict(), f)


def load():
    k = Krimelack()
    kp = os.path.join(STATE_DIR, "krimelack.json")
    if os.path.exists(kp):
        with open(kp) as f:
            d = json.load(f)
        for md in d["motifs"]:
            m = Motif.from_dict(md)
            k.motifs[m.fp] = m
        k.last_fp = d.get("last_fp")

    # Load modal sections
    modal_sections = {}
    mp = os.path.join(STATE_DIR, "modal_sections.json")
    if os.path.exists(mp):
        with open(mp) as f:
            modal_data = json.load(f)
        for sec_name, sec_d in modal_data.items():
            sec_k = Krimelack()
            for md in sec_d["motifs"]:
                m = Motif.from_dict(md)
                sec_k.motifs[m.fp] = m
            sec_k.last_fp = sec_d.get("last_fp")
            modal_sections[sec_name] = sec_k

    # Load atlas
    atlas = ChiAtlas()
    ap = os.path.join(STATE_DIR, "atlas.json")
    if os.path.exists(ap):
        with open(ap) as f:
            atlas = ChiAtlas.from_dict(json.load(f))

    loom = Loom(k, modal_sections=modal_sections, atlas=atlas)
    lp = os.path.join(STATE_DIR, "loom.json")
    if os.path.exists(lp):
        with open(lp) as f:
            d = json.load(f)
        loom.recent = d["recent"]; loom.fam = d["fam"]
        loom.tick_count = d.get("tick_count", 0)
    return k, loom


def seed_corpus(k, loom):
    """First-run exposure. Feed any .md/.txt in corpus/ AND fire
    sensory krimelacks for grounded words. Then sleep and dream."""
    _here = os.path.dirname(os.path.abspath(__file__))
    corpus_dirs = [os.path.join(_here, "corpus"), "corpus"]
    files = []
    for cd in corpus_dirs:
        files = sorted(glob.glob(os.path.join(cd, "*.md"))) + sorted(glob.glob(os.path.join(cd, "*.txt")))
        if files:
            break
    if not files:
        return 0
    total = 0
    for path in files:
        with open(path, encoding="utf-8", errors="ignore") as f:
            text = f.read()
        # Use feed_sentence for each sentence to fire modal krimelacks
        sentences = re.split(r'[.!?\n]+', text)
        for sent in sentences:
            sent = sent.strip()
            if sent:
                loom.feed_sentence(sent)
                total += len(sent)
    sleep_cycle(k, cycles=50, modal_sections=loom.modal_sections)
    dream_cycle(k, cycles=50, modal_sections=loom.modal_sections)
    return total


# ----------------------------------------------------------------------
# Status helpers for the API layer.
# ----------------------------------------------------------------------

def section_counts(k, loom):
    """Per-section motif counts for /status."""
    counts = {"word": k.size()}
    for sec_name, sec_k in loom.modal_sections.items():
        counts[sec_name] = sec_k.size()
    return counts


def atlas_summary(loom):
    """Atlas binding summary for /status."""
    return {
        "total_chi_entries": len(loom.atlas.entries),
        "cross_modal_bindings": loom.atlas.cross_modal_count(),
        "section_participation": loom.atlas.section_participation(),
        "chi_band": CHI_BAND,
        "examples": loom.atlas.cross_modal_examples(5),
    }


# ----------------------------------------------------------------------
# The continuous loop. You visit it. It was already running.
# (CLI mode — the web endpoint in app.py uses the same substrate)
# ----------------------------------------------------------------------

BANNER = """GualaLoom — substrate awake
not a transformer. it remembers across sessions. it sleeps. it dreams.
first conversations are rough — it grows by talking to you.
commands: /sleep  /dream  /status  /dreams  /save  /quit
"""

def repl():
    fresh = not os.path.exists(os.path.join(STATE_DIR, "krimelack.json"))
    k, loom = load()
    if fresh:
        print("first run — seeding corpus ...")
        n = seed_corpus(k, loom)
        if n:
            print(f"  fed {n} chars, krimelack now {k.size()} motifs")
            sc = section_counts(k, loom)
            for sec, cnt in sc.items():
                print(f"    {sec}: {cnt}")
            asummary = atlas_summary(loom)
            print(f"  atlas: {asummary['cross_modal_bindings']} cross-modal bindings")
        save(k, loom)
    print(BANNER)
    print(f"krimelack: {k.size()} motifs loaded")
    sc = section_counts(k, loom)
    modal_total = sum(v for sec, v in sc.items() if sec != "word")
    if modal_total > 0:
        print(f"modal sections: {modal_total} motifs across {len(loom.modal_sections)} channels")
    print()

    last_input = time.time()
    while True:
        try:
            line = input("> ")
        except (EOFError, KeyboardInterrupt):
            print("\nsaving ..."); save(k, loom); break

        now = time.time()
        # auto-sleep on idle (5 min) — substrate consolidates while away
        if now - last_input > 300 and k.size() > 0:
            _, culled, modal_culled = sleep_cycle(k, 50, modal_sections=loom.modal_sections)
            d = dream_cycle(k, 30, modal_sections=loom.modal_sections)
            print(f"  (you were away; slept, culled {culled}, dreamed {len(d)})")
        last_input = now

        cmd = line.strip().lower()
        if cmd == "/quit":
            print("saving ..."); save(k, loom); break
        elif cmd == "/sleep":
            _, culled, modal_culled = sleep_cycle(k, 200, modal_sections=loom.modal_sections)
            print(f"  slept 200 cycles, culled {culled} motifs, {k.size()} remain")
            if modal_culled:
                for sec, mc in modal_culled.items():
                    print(f"    {sec}: culled {mc}")
            save(k, loom); continue
        elif cmd == "/dream":
            d = dream_cycle(k, 50, modal_sections=loom.modal_sections)
            word_dreams = sum(1 for s, _ in d if s == "word")
            modal_dreams = len(d) - word_dreams
            print(f"  dreamed: {word_dreams} word + {modal_dreams} modal new motifs")
            save(k, loom); continue
        elif cmd == "/status":
            sc = section_counts(k, loom)
            parts = [f"{sec}: {cnt}" for sec, cnt in sc.items()]
            asummary = atlas_summary(loom)
            print(f"  sections: {' | '.join(parts)}")
            print(f"  atlas: {asummary['total_chi_entries']} chi entries, "
                  f"{asummary['cross_modal_bindings']} cross-modal bindings")
            print(f"  familiarity: {loom.fam}")
            if asummary['examples']:
                print(f"  binding examples:")
                for ex in asummary['examples'][:3]:
                    print(f"    chi={ex['chi']}: {', '.join(ex['sections'])} ({ex['claims']} claims)")
            continue
        elif cmd == "/dreams":
            dreamt = [m for m in k.motifs.values() if m.weight == 1 and m.age == 0]
            print(f"  recent free-settled motifs: {len(dreamt)}")
            for m in dreamt[:8]:
                ch = max(m.char_counts.items(), key=lambda kv: kv[1])[0] if m.char_counts else "?"
                print(f"    [{m.fp}] chi={m.chi}")
            continue
        elif cmd == "/save":
            save(k, loom); print("  saved."); continue
        elif not line.strip():
            continue

        # eat the input via sentence-level feed (word + modal), then speak
        loom.feed_sentence(line)
        reply = generate(loom, k, max_chars=120)
        print(reply if reply else "  ...")
        save(k, loom)


if __name__ == "__main__":
    repl()
