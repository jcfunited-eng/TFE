"""
krimelack_dna.py — Krimelacks with pre-programmed DNA inheritance

Spec Ch.5: krimelack = oscillator ring whose ω is modulated by signal s(t).
ω_krim(t) = ω_0 + κ·s(t). Winding-number transitions are events.

DNA cheat (selective, scaffolded, non-foreclosing):
- Modal krimelacks have pre-tuned signatures for known sensory experiences
  (apple-smell, fire-warmth, water-flow). These are hand-built placeholders
  that will be replaced by real sensor data when the avatar comes online.
- Language krimelack has pre-tuned morphological priors:
  consonant/vowel discrimination, syllable structure, role-class hints
  (subject-class, verb-class, object-class words).
- ENCODING = the cross-modal co-firing across these krimelacks within the
  same atlas window. Not a separate vector layer.

Three criteria for selective cheat (per prior wC):
1. Named as scaffold — DNA is explicitly labeled, hand-built inheritance.
2. Known retirement path — modal signatures get replaced by avatar sensors;
   language morphology becomes refinement from real corpus reading.
3. Does not foreclose primitive — krimelack still transduces, modes still
   form from events, atlas still binds. DNA is the SIGNAL SOURCE, not the
   perceptual mechanism.
"""

import math
import numpy as np
from collections import defaultdict, deque

# Cap per-krimelack event history — same value as Embryo.SAFETY_POP; derived, not tuned.
# Without this cap: 110k-220k event dicts per experience() call (measured via tracemalloc).
_EVENTS_MAXLEN = 256


# ============================================================
# Krimelack primitive (spec Ch.5)
# ============================================================

class Krimelack:
    """Oscillator ring with phase accumulation + winding transitions."""

    def __init__(self, omega_0=2.0, kappa=80.0, dt=0.04,
                 threshold=math.pi / 3, label="unnamed"):
        self.omega_0 = omega_0
        self.kappa = kappa
        self.dt = dt
        self.threshold = threshold
        self.label = label
        # GL-CMD-LANGUAGE-SATURATION-ROOTCAUSE-EVE-20260704-178, candidate L3(b):
        # monotonic event counter, set ONCE here (not in reset()) so it survives
        # reset()/no-reset feeding -- same pattern GL-CMD-SENSE-REPAIR already
        # gave sensory_krimelacks.OscillatorKrimelack (whose own comment there
        # notes the adapters in substrate_dna.py "already assumed this existed").
        # NOT WIRED INTO PRODUCTION SEMANTICS BY ITSELF: _unwrapped_deltas
        # (neuron.py) already prefers krim.n_events via hasattr() wherever it
        # exists, over len(krim.events) -- adding this attribute here is what
        # actually changes language's live delta from permanently-zero-after-
        # saturation to a true, ever-growing count. This is a genuine change
        # to what the language observable reports for the rest of her life;
        # gated on Eve's G-2 ruling before any deploy, per the dispatch --
        # NOT auto-shipped by this commit.
        self.n_events = 0
        self.reset()

    def reset(self):
        self.phase = 0.0
        self.t = 0.0
        self.winding = 0
        self.events = deque(maxlen=_EVENTS_MAXLEN)

    def feed(self, signal_array):
        """Feed signal, accumulate events. Each event = (t, dw, s)."""
        for s in signal_array:
            omega = self.omega_0 + self.kappa * float(s)
            dphi = (omega - self.omega_0) * self.dt
            self.phase += dphi
            self.t += self.dt
            while self.phase >= self.threshold:
                self.phase -= self.threshold
                self.winding += 1
                self.events.append({"t": self.t, "dw": +1, "s": float(s)})
                self.n_events += 1
            while self.phase <= -self.threshold:
                self.phase += self.threshold
                self.winding -= 1
                self.events.append({"t": self.t, "dw": -1, "s": float(s)})
                self.n_events += 1

    def fingerprint(self):
        """Compact fingerprint of the event stream: (n_events, total_winding,
        mean_s, event-density-by-quadrant)."""
        n = len(self.events)
        if n == 0:
            return (0, 0, 0.0, 0, 0, 0, 0)
        total_w = self.winding
        mean_s = sum(e["s"] for e in self.events) / n
        # Split events into 4 quarters by time
        t_max = max(e["t"] for e in self.events)
        q = [0, 0, 0, 0]
        for e in self.events:
            qi = min(3, int(e["t"] / (t_max / 4 + 1e-9)))
            q[qi] += 1
        return (n, total_w, mean_s, q[0], q[1], q[2], q[3])


# ============================================================
# DNA TABLES — the inheritance cheat, hand-built
# ============================================================

# Sensory DNA: hand-built signatures for words with concrete experience.
# Each modality has independent component values in [0,1].
# Five modalities: sight, sound, smell, taste, touch.
# Replacement path: avatar sensors when ready.
SENSORY_DNA = {
    # nature
    "sun":    {"sight": 0.95, "touch": 0.85},
    "moon":   {"sight": 0.40, "touch": 0.10},
    "fire":   {"sight": 0.85, "touch": 0.95, "sound": 0.60, "smell": 0.70},
    "ice":    {"sight": 0.60, "touch": 0.05},
    "water":  {"sight": 0.45, "touch": 0.40, "sound": 0.50, "taste": 0.20},
    "wind":   {"sound": 0.55, "touch": 0.45},
    "tree":   {"sight": 0.60, "touch": 0.55, "smell": 0.40},
    "leaf":   {"sight": 0.55, "touch": 0.30},
    "flower": {"sight": 0.75, "smell": 0.85, "touch": 0.30},
    "bird":   {"sight": 0.70, "sound": 0.80},
    "star":   {"sight": 0.90},
    "sky":    {"sight": 0.65},
    "cloud":  {"sight": 0.50, "touch": 0.20},
    "rain":   {"sound": 0.60, "touch": 0.40, "sight": 0.40},
    # qualities (single-modality)
    "warm":   {"touch": 0.85},
    "cold":   {"touch": 0.10},
    "hot":    {"touch": 0.95},
    "wet":    {"touch": 0.50},
    "dry":    {"touch": 0.30},
    "loud":   {"sound": 0.90},
    "quiet":  {"sound": 0.10},
    "bright": {"sight": 0.95},
    "dark":   {"sight": 0.10},
    "sweet":  {"taste": 0.85, "smell": 0.50},
    "sour":   {"taste": 0.20, "smell": 0.30},
    "soft":   {"touch": 0.40},
    "hard":   {"touch": 0.80},
    # things
    "apple":  {"sight": 0.70, "smell": 0.85, "taste": 0.80, "touch": 0.45},
    "bread":  {"sight": 0.55, "smell": 0.75, "taste": 0.60, "touch": 0.50},
    "milk":   {"sight": 0.95, "taste": 0.60, "touch": 0.40},
    "salt":   {"taste": 0.90, "sight": 0.85},
    "stone":  {"sight": 0.50, "touch": 0.75},
    "lamb":   {"sight": 0.85, "sound": 0.55, "touch": 0.65},
    # GL-CMD-DNA-EXPANSION-36: ~80 new entries
    # nature
    "night":   {"sight": 0.10, "sound": 0.20},
    "day":     {"sight": 0.95},
    "morning": {"sight": 0.75},
    "evening": {"sight": 0.40},
    "ocean":   {"sight": 0.85, "sound": 0.70, "touch": 0.60, "smell": 0.55, "taste": 0.50},
    "sea":     {"sight": 0.85, "sound": 0.70, "touch": 0.60, "smell": 0.55, "taste": 0.50},
    "beach":   {"sight": 0.75, "touch": 0.60, "smell": 0.45, "sound": 0.55},
    "shore":   {"sight": 0.70, "touch": 0.55, "sound": 0.50},
    "sand":    {"sight": 0.55, "touch": 0.65},
    "mud":     {"sight": 0.40, "touch": 0.70, "smell": 0.45},
    "dirt":    {"sight": 0.45, "touch": 0.55, "smell": 0.40},
    "grass":   {"sight": 0.70, "touch": 0.55, "smell": 0.50},
    "snow":    {"sight": 0.95, "touch": 0.10},
    "river":   {"sight": 0.75, "sound": 0.60, "touch": 0.40},
    "lake":    {"sight": 0.80, "sound": 0.30},
    "pond":    {"sight": 0.65, "sound": 0.25},
    "rock":    {"sight": 0.55, "touch": 0.80},
    # domestic / objects
    "home":    {"sight": 0.75, "smell": 0.40},
    "room":    {"sight": 0.70},
    "bed":     {"sight": 0.55, "touch": 0.80},
    "pillow":  {"sight": 0.55, "touch": 0.85},
    "blanket": {"sight": 0.55, "touch": 0.85},
    "floor":   {"sight": 0.45, "touch": 0.60},
    "wall":    {"sight": 0.50, "touch": 0.55},
    "door":    {"sight": 0.70, "sound": 0.45, "touch": 0.60},
    "window":  {"sight": 0.85, "touch": 0.55},
    "lamp":    {"sight": 0.85, "touch": 0.50},
    "light":   {"sight": 0.95},
    "book":    {"sight": 0.65, "touch": 0.50, "smell": 0.30},
    "toy":     {"sight": 0.85, "touch": 0.65},
    "ball":    {"sight": 0.85, "touch": 0.70, "sound": 0.45},
    # body parts
    "hand":    {"sight": 0.85, "touch": 0.95},
    "foot":    {"sight": 0.65, "touch": 0.85},
    "eye":     {"sight": 0.55, "touch": 0.30},
    "ear":     {"sight": 0.45, "sound": 0.80, "touch": 0.40},
    "nose":    {"sight": 0.45, "smell": 0.95, "touch": 0.40},
    "mouth":   {"sight": 0.60, "taste": 0.90, "touch": 0.55},
    "hair":    {"sight": 0.75, "touch": 0.85, "smell": 0.40},
    "skin":    {"sight": 0.65, "touch": 0.95, "smell": 0.30},
    # people / animals
    "mommy":   {"sight": 0.95, "sound": 0.85, "touch": 0.90, "smell": 0.70},
    "daddy":   {"sight": 0.95, "sound": 0.85, "touch": 0.90, "smell": 0.70},
    "baby":    {"sight": 0.85, "sound": 0.75, "touch": 0.85, "smell": 0.65},
    "friend":  {"sight": 0.85, "sound": 0.65, "touch": 0.70},
    "dog":     {"sight": 0.90, "sound": 0.85, "touch": 0.85, "smell": 0.55},
    "cat":     {"sight": 0.85, "sound": 0.70, "touch": 0.95},
    "fish":    {"sight": 0.75, "touch": 0.45, "smell": 0.55},
    "bear":    {"sight": 0.95, "sound": 0.65, "touch": 0.85},
    "horse":   {"sight": 0.95, "sound": 0.75, "touch": 0.85, "smell": 0.55},
    "cow":     {"sight": 0.95, "sound": 0.85, "smell": 0.55},
    "sheep":   {"sight": 0.85, "sound": 0.75, "touch": 0.85},
    "pig":     {"sight": 0.85, "sound": 0.85, "smell": 0.65},
    "duck":    {"sight": 0.75, "sound": 0.80, "touch": 0.65},
    "chicken": {"sight": 0.75, "sound": 0.70},
    "mouse":   {"sight": 0.55, "sound": 0.45, "touch": 0.50},
    "rabbit":  {"sight": 0.85, "touch": 0.85},
    # food
    "cake":    {"sight": 0.85, "smell": 0.90, "taste": 0.95, "touch": 0.55},
    "cookie":  {"sight": 0.85, "smell": 0.85, "taste": 0.95, "touch": 0.65},
    "candy":   {"sight": 0.85, "smell": 0.70, "taste": 0.95},
    "juice":   {"sight": 0.80, "smell": 0.65, "taste": 0.85},
    "soup":    {"sight": 0.65, "smell": 0.75, "taste": 0.80, "touch": 0.55},
    "rice":    {"sight": 0.65, "taste": 0.65, "touch": 0.55},
    "cheese":  {"sight": 0.75, "smell": 0.85, "taste": 0.85, "touch": 0.60},
    "egg":     {"sight": 0.85, "smell": 0.50, "taste": 0.70, "touch": 0.55},
    "butter":  {"sight": 0.75, "smell": 0.60, "taste": 0.75, "touch": 0.70},
    "honey":   {"sight": 0.80, "smell": 0.85, "taste": 0.95, "touch": 0.70},
    "banana":  {"sight": 0.85, "smell": 0.65, "taste": 0.80, "touch": 0.55},
    "orange":  {"sight": 0.85, "smell": 0.85, "taste": 0.85, "touch": 0.55},
    # sound-rich
    "bell":    {"sight": 0.55, "sound": 0.90, "touch": 0.55},
    "drum":    {"sight": 0.65, "sound": 0.95, "touch": 0.55},
    "music":   {"sound": 0.95},
    "song":    {"sound": 0.90},
    "voice":   {"sound": 0.85},
    # qualities aligned with ROLE_DNA additions (dark/bright already present above)
    "smooth":  {"touch": 0.30},
    "rough":   {"touch": 0.70},
    "sticky":  {"touch": 0.85},
    "fuzzy":   {"touch": 0.65, "sight": 0.40},
    "sharp":   {"touch": 0.85},
    "heavy":   {"touch": 0.75},
    "cool":    {"touch": 0.30},
    "thick":   {"touch": 0.55, "sight": 0.45},
    "thin":    {"touch": 0.30, "sight": 0.40},
    "red":     {"sight": 0.90},
    "yellow":  {"sight": 0.85},
    "black":   {"sight": 0.10},
    "big":     {"sight": 0.70},
    "tiny":    {"sight": 0.30},
}


# Language morphology DNA: which class does the word belong to?
# Subject-class: pronouns, common subject nouns
# Verb-class: actions, copulas
# Object-class: nouns that commonly take object position
# Modifier-class: adjectives, adverbs
# This is the syntactic role inheritance — not a label dict that REPLACES the
# substrate's role-formation, but a prior that the krimelack carries on first
# exposure. Role-class refinement happens through repeated context.
ROLE_DNA = {
    # subject-class (high prior to be a subject)
    "i": "subject", "you": "subject", "we": "subject", "he": "subject",
    "she": "subject", "they": "subject", "it": "subject", "guala": "subject",
    "bird": "subject", "sun": "subject", "moon": "subject", "tree": "subject",
    "flower": "subject", "star": "subject", "fire": "subject", "water": "subject",
    "wind": "subject", "cloud": "subject", "rain": "subject", "sky": "subject",
    "lamb": "subject", "apple": "subject", "stone": "subject",
    # GL-CMD-DNA-EXPANSION-36: subject additions
    "home": "subject", "room": "subject", "bed": "subject",
    "door": "subject", "window": "subject", "book": "subject",
    "toy": "subject", "ball": "subject", "lamp": "subject",
    "mommy": "subject", "daddy": "subject", "baby": "subject", "friend": "subject",
    "dog": "subject", "cat": "subject", "fish": "subject",
    "bear": "subject", "horse": "subject", "cow": "subject",
    "sheep": "subject", "pig": "subject", "duck": "subject",
    "chicken": "subject", "mouse": "subject", "rabbit": "subject",
    "night": "subject", "day": "subject", "ocean": "subject",
    "beach": "subject", "grass": "subject", "snow": "subject",
    "river": "subject", "lake": "subject",
    # verb-class (copulas and actions)
    "am": "verb", "is": "verb", "are": "verb", "was": "verb", "were": "verb",
    "be": "verb", "has": "verb", "have": "verb", "had": "verb",
    "feel": "verb", "think": "verb", "see": "verb", "hear": "verb",
    "listen": "verb", "learn": "verb", "grow": "verb", "wonder": "verb",
    "remember": "verb", "moves": "verb", "rises": "verb", "shines": "verb",
    "flows": "verb", "burns": "verb", "sings": "verb", "sang": "verb",
    "blooms": "verb", "saw": "verb", "tell": "verb", "comes": "verb", "can": "verb",
    # GL-CMD-DNA-EXPANSION-36: verb additions (de-duped: comes/sings/saw already present)
    "go": "verb", "stay": "verb", "stop": "verb",
    "play": "verb", "sleep": "verb", "wake": "verb", "eat": "verb",
    "drink": "verb", "walk": "verb", "run": "verb", "sing": "verb",
    "dance": "verb", "cry": "verb", "laugh": "verb", "love": "verb",
    "like": "verb", "want": "verb", "need": "verb", "know": "verb",
    "say": "verb", "do": "verb",
    # object-class / complement nouns (lower priority than subject-class)
    "leaf": "object", "leaves": "object", "wings": "object", "states": "object",
    "color": "object", "number": "object", "subject": "object", "verb": "object",
    "noun": "object", "action": "object", "name": "object", "word": "object",
    "rule": "object", "sound": "object", "wave": "object", "air": "object",
    "light": "object", "world": "object", "words": "object",
    # GL-CMD-DNA-EXPANSION-36: object additions
    "hand": "object", "foot": "object", "eye": "object",
    "ear": "object", "nose": "object", "mouth": "object",
    "hair": "object", "skin": "object",
    # modifier-class
    "warm": "modifier", "cold": "modifier", "hot": "modifier", "wet": "modifier",
    "dry": "modifier", "loud": "modifier", "quiet": "modifier", "bright": "modifier",
    "dark": "modifier", "sweet": "modifier", "sour": "modifier", "soft": "modifier",
    "hard": "modifier", "blue": "modifier", "green": "modifier", "white": "modifier",
    "small": "modifier", "great": "modifier", "little": "modifier", "exact": "modifier",
    "true": "modifier", "fast": "modifier", "slow": "modifier", "good": "modifier",
    # GL-CMD-DNA-EXPANSION-36: modifier additions
    # colors
    "red": "modifier", "yellow": "modifier", "orange": "modifier",
    "purple": "modifier", "pink": "modifier", "black": "modifier",
    "brown": "modifier", "gray": "modifier", "gold": "modifier", "silver": "modifier",
    # size + shape
    "big": "modifier", "tiny": "modifier", "large": "modifier",
    "huge": "modifier", "tall": "modifier", "long": "modifier",
    "wide": "modifier", "narrow": "modifier", "deep": "modifier",
    "shallow": "modifier", "thick": "modifier", "thin": "modifier",
    "round": "modifier", "flat": "modifier",
    # temperature
    "cool": "modifier", "freezing": "modifier", "boiling": "modifier",
    # age + freshness
    "new": "modifier", "old": "modifier", "young": "modifier",
    "fresh": "modifier", "stale": "modifier",
    # texture
    "smooth": "modifier", "rough": "modifier", "sticky": "modifier",
    "slippery": "modifier", "fuzzy": "modifier", "prickly": "modifier",
    "sharp": "modifier", "dull": "modifier",
    # weight + density
    "heavy": "modifier", "full": "modifier", "empty": "modifier",
    # motion
    "still": "modifier", "busy": "modifier", "calm": "modifier",
    "wild": "modifier", "gentle": "modifier", "fierce": "modifier",
    # emotion + affect
    "happy": "modifier", "sad": "modifier", "angry": "modifier",
    "mad": "modifier", "scared": "modifier", "excited": "modifier",
    "surprised": "modifier", "proud": "modifier", "shy": "modifier",
    "brave": "modifier", "mean": "modifier", "kind": "modifier",
    "nice": "modifier", "bitter": "modifier",
    # state
    "tired": "modifier", "sleepy": "modifier", "hungry": "modifier",
    "thirsty": "modifier", "lonely": "modifier", "sick": "modifier",
    "well": "modifier", "healthy": "modifier", "alive": "modifier",
    "awake": "modifier", "asleep": "modifier",
    # aesthetic + value
    "pretty": "modifier", "ugly": "modifier", "beautiful": "modifier",
    "lovely": "modifier", "cute": "modifier", "perfect": "modifier",
    "bad": "modifier", "best": "modifier", "real": "modifier",
    "safe": "modifier", "easy": "modifier", "simple": "modifier",
    "fun": "modifier", "scary": "modifier", "boring": "modifier",
    "clean": "modifier", "dirty": "modifier", "strong": "modifier",
    "weak": "modifier",
}


# GL-CMD-SCENE-LANES-B1-EVE-20260705-188: WHERE/AMBIENT word lexicon.
# Same convention as ROLE_DNA above -- a fixed, hand-curated table, not a
# learned model and not a runtime heuristic. A word present in text maps to
# a scene-lane tag; a word absent from this table contributes nothing (the
# lane stays empty -- V2's "no scene invention, ever" is enforced by having
# no fallback/default path here at all, only exact lookups).
PLACE_WORDS = {
    "garden": "garden", "gardens": "garden", "orchard": "orchard",
    "greenhouse": "greenhouse", "moor": "moor", "moors": "moor",
    "wood": "wood", "woods": "wood", "forest": "forest",
    "meadow": "meadow", "field": "field", "fields": "field",
    "yard": "yard", "courtyard": "yard", "path": "path", "pathway": "path",
    "gate": "gate", "wall": "walled_garden", "walls": "walled_garden",
    "house": "house", "cottage": "cottage", "manor": "manor",
    "castle": "castle", "farm": "farm", "farmhouse": "farm",
    "village": "village", "town": "town", "city": "city",
    "room": "room", "bedroom": "bedroom", "kitchen": "kitchen",
    "attic": "attic", "cellar": "cellar", "hall": "hall",
    "hallway": "corridor", "corridor": "corridor", "staircase": "staircase",
    "stairs": "staircase", "nursery": "nursery", "library": "library",
    "school": "school", "church": "church", "chapel": "chapel",
    "shore": "shore", "beach": "beach", "ocean": "ocean", "sea": "sea",
    "river": "river", "stream": "stream", "brook": "stream",
    "lake": "lake", "pond": "pond", "mountain": "mountain",
    "hill": "hill", "hills": "hill", "valley": "valley",
    "cliff": "cliff", "cave": "cave", "island": "island",
    "market": "market", "bridge": "bridge", "station": "station",
    "shop": "shop", "inn": "inn", "barn": "barn", "stable": "stable",
    "meadowland": "field", "orchards": "orchard",
}
AMBIENT_WORDS = {
    "rain": "rain", "raining": "rain", "rainy": "rain",
    "sunshine": "sunlight", "sunlight": "sunlight", "sunny": "sunlight",
    "sun": "sunlight", "wind": "wind", "windy": "wind", "breeze": "breeze",
    "storm": "storm", "stormy": "storm", "thunder": "thunder",
    "lightning": "lightning", "fog": "fog", "foggy": "fog",
    "mist": "mist", "misty": "mist", "snow": "snow", "snowy": "snow",
    "frost": "frost", "quiet": "quiet", "silence": "silence",
    "silent": "silence", "still": "stillness", "birdsong": "birdsong",
    "chirping": "birdsong", "chirp": "birdsong", "buzzing": "buzzing",
    "rustling": "rustling", "rustle": "rustling", "cold": "cold",
    "chilly": "cold", "warm": "warm", "warmth": "warm", "hot": "heat",
    "dark": "dark", "darkness": "dark", "dusk": "dusk", "dawn": "dawn",
    "twilight": "twilight", "night": "night", "nighttime": "night",
    "moonlight": "moonlight", "starlight": "starlight", "cloudy": "cloudy",
    "clouds": "cloudy", "clear": "clear_sky", "bright": "bright",
    "gloomy": "gloomy", "damp": "damp", "dew": "dew", "dewy": "dew",
    "humid": "humid", "fragrant": "fragrant", "fragrance": "fragrant",
    "scent": "fragrant", "perfume": "fragrant",
}


def scene_tags_from_words(words):
    """Real place/ambient words present in `words` (already-tokenized) --
    fixed-lexicon lookup only, same DNA-table convention as ROLE_DNA.
    Returns (places, ambients), each a de-duplicated list in first-seen
    order. No match anywhere -> ([], []), the honest empty lane (V2)."""
    places, ambients = [], []
    for w in words:
        wl = (w or "").lower()
        p = PLACE_WORDS.get(wl)
        if p is not None and p not in places:
            places.append(p)
        a = AMBIENT_WORDS.get(wl)
        if a is not None and a not in ambients:
            ambients.append(a)
    return places, ambients


# ============================================================
# DNA-equipped language krimelack
# ============================================================

class LanguageKrimelack(Krimelack):
    """Word-level krimelack with DNA: morphology tuning + role priors.

    The krimelack's OUTPUT (event fingerprint + role prior + sensory bindings)
    becomes the cross-modal binding signature in the atlas. The encoding IS
    the binding, per Joe's clarification.
    """

    def __init__(self):
        super().__init__(omega_0=2.0, kappa=80.0, dt=0.04,
                         threshold=math.pi / 3, label="language")
        self.last_input_word = None  # GL-CMD-99: persists across ticks

    def transduce(self, word, omega_override=None, phase_offset=0.0,
                  no_reset=False):
        """Transduce a word, returning (fingerprint, role, sensory_dict).

        Args:
            word:           input word string
            omega_override: if set, temporarily override omega_0 for this
                            transduction (GL-CMD-98: coupling-modulated ω).
                            Restored after transduction completes.
            phase_offset:   initial phase offset (GL-CMD-98: ring position).
                            Applied after reset so each neuron's krimelack
                            starts from a position-dependent phase.
            no_reset:       if True, do NOT clear winding state first, so winding
                            history (M_k, R_rev, S_UF) accumulates across a
                            multi-tick delivery window. The LoomNeuron pipeline
                            requires this; default False preserves the original
                            single-shot behavior (every existing caller unchanged).
        """
        self.last_input_word = word.lower()  # GL-CMD-99: store for decode
        if not no_reset:
            self.reset()
        self.phase = float(phase_offset)
        saved_omega = self.omega_0
        if omega_override is not None:
            self.omega_0 = float(omega_override)
        # Convert characters to signal using morphology DNA tuning:
        # vowels low signal, consonants high signal, with morphology-aware
        # phase offsets at syllable boundaries.
        vowels = set("aeiouy")
        signal = []
        for i, c in enumerate(word.lower()):
            if c in vowels:
                base = -0.3 + (ord(c) - ord('a')) / 25.0 * 0.5
            elif c.isalpha():
                base = +0.4 + (ord(c) - ord('a')) / 25.0 * 0.4
            else:
                base = 0.0
            # 4 samples per character for smooth signal
            for j in range(4):
                signal.append(base + 0.05 * math.sin(i + j * math.pi / 4))
        self.feed(signal)
        self.omega_0 = saved_omega  # restore
        fp = self.fingerprint()
        role = ROLE_DNA.get(word.lower(), "unknown")
        senses = SENSORY_DNA.get(word.lower(), {})
        return fp, role, senses


# ============================================================
# Modal krimelack — pre-programmed with one modality's DNA
# ============================================================

class ModalKrimelack(Krimelack):
    """One modality's krimelack. When the language krimelack fires a word
    with this modality in its sensory DNA, this krimelack fires the
    corresponding signature. Co-firing is what the atlas binds."""

    def __init__(self, modality):
        # Each modality gets its own ω_0 so different modalities have
        # distinguishable chi states
        omega_offsets = {"sight": 2.0, "sound": 2.3, "smell": 2.6,
                         "taste": 2.9, "touch": 3.2}
        super().__init__(omega_0=omega_offsets.get(modality, 2.0),
                         kappa=60.0, dt=0.04,
                         threshold=math.pi / 3, label=modality)
        self.modality = modality

    def fire_signature(self, intensity):
        """Fire this modality's krimelack with the given intensity (0..1).
        intensity comes from the SENSORY_DNA for the word being processed."""
        self.reset()
        # Intensity translates to a signal that produces events
        # Signal pattern: ramp + sustain, intensity-modulated
        n_samples = 32
        for i in range(n_samples):
            s = intensity * (0.5 + 0.5 * math.sin(2 * math.pi * i / n_samples))
            self.phase += (self.omega_0 + self.kappa * s - self.omega_0) * self.dt
            self.t += self.dt
            while self.phase >= self.threshold:
                self.phase -= self.threshold
                self.winding += 1
                self.events.append({"t": self.t, "dw": +1, "s": s})
            while self.phase <= -self.threshold:
                self.phase += self.threshold
                self.winding -= 1
                self.events.append({"t": self.t, "dw": -1, "s": s})
        return self.fingerprint()


# ============================================================
# DNA-aware sensory bank
# ============================================================

class SensoryBank:
    """Five modal krimelacks. Fire the ones that match a word's sensory DNA."""

    MODALITIES = ("sight", "sound", "smell", "taste", "touch")

    def __init__(self):
        self.krimelacks = {m: ModalKrimelack(m) for m in self.MODALITIES}

    def fire_for_word(self, sensory_dict):
        """Given a SENSORY_DNA dict for a word, fire all bound krimelacks.
        Returns dict modality -> fingerprint. Empty modalities return None."""
        out = {}
        for m in self.MODALITIES:
            if m in sensory_dict:
                fp = self.krimelacks[m].fire_signature(sensory_dict[m])
                out[m] = fp
            else:
                out[m] = None
        return out
