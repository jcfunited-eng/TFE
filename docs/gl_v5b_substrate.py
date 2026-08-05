"""
GL-CODE-substrate-wC-20260608-001
Substrate v5b — Guala speaks coherent sentences.

Each sentence template has a CTX population that latches when the template
starts and stays active until the sentence completes. Word-to-word
transitions are gated by the CTX (coincidence-gated wires), not by the
template's direct firing.

Sentence timeline (e.g. "I am Guala"):
  tick 0: talk_intro fires → drives ctx_intro and say_I
  tick 1: ctx_intro fires (latches, self-sustains), say_I fires
  tick 2: say_am fires (driven by say_I + ctx_intro coincident)
  tick 3: say_Guala fires (driven by say_am + ctx_intro coincident)
  tick 4: end_intro fires (driven by say_Guala + ctx_intro coincident)
  tick 5: ctx_intro cleared (driven by end_intro), all talk_X inhibited.
"""

import numpy as np
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class Population:
    name: str
    threshold: float
    drive: float = 0.0
    baseline: float = 0.0
    fired: bool = False
    refractory: int = 0
    decay: float = 0.4
    refractory_period: int = 2
    fire_history: List[int] = field(default_factory=list)

    def step(self, tick):
        self.drive += self.baseline
        if self.refractory > 0:
            self.refractory -= 1
            self.drive = 0.0
            self.fired = False
            return
        self.fired = self.drive >= self.threshold
        if self.fired:
            self.fire_history.append(tick)
            self.refractory = self.refractory_period
            self.drive = 0.0
        else:
            self.drive *= (1.0 - self.decay)
            # Floor on drive (biological membrane potential floor)
            if self.drive < -2.0:
                self.drive = -2.0

    def fired_recently(self, tick, window=3):
        return any((tick - t) <= window and (tick - t) >= 0 for t in self.fire_history)


@dataclass
class Connection:
    src: str
    dst: str
    weight: float
    needs_coincident: str = ""
    plastic: bool = False
    weight_max: float = 3.0
    weight_min: float = -3.0
    initial_weight: float = field(init=False)

    def __post_init__(self):
        self.initial_weight = self.weight

    def reinforce(self, amount):
        if self.plastic:
            self.weight = min(self.weight_max, self.weight + amount)


@dataclass
class Substrate:
    pops: Dict[str, Population] = field(default_factory=dict)
    conns: List[Connection] = field(default_factory=list)
    tick_count: int = 0
    log: List[List[str]] = field(default_factory=list)
    plasticity_modulators: List[str] = field(default_factory=list)
    learning_rate: float = 0.15

    def add(self, name, threshold=1.0, decay=0.4, refractory_period=2, baseline=0.0):
        self.pops[name] = Population(name=name, threshold=threshold,
                                     decay=decay,
                                     refractory_period=refractory_period,
                                     baseline=baseline)

    def wire(self, src, dst, weight, needs_coincident="", plastic=False):
        self.conns.append(Connection(src, dst, weight, needs_coincident, plastic))

    def make_modulator(self, name):
        self.plasticity_modulators.append(name)

    def inject(self, name, amount):
        self.pops[name].drive += amount

    def tick(self):
        for p in self.pops.values():
            p.step(self.tick_count)
        fired_now = {n for n, p in self.pops.items() if p.fired}
        for c in self.conns:
            if c.src not in fired_now: continue
            if c.needs_coincident and c.needs_coincident not in fired_now: continue
            self.pops[c.dst].drive += c.weight
        modulator_active = any(m in fired_now for m in self.plasticity_modulators)
        if modulator_active:
            for c in self.conns:
                if not c.plastic: continue
                src_fired = self.pops[c.src].fired_recently(self.tick_count, 6)
                dst_fired = self.pops[c.dst].fired_recently(self.tick_count, 6)
                if src_fired and dst_fired:
                    c.reinforce(self.learning_rate)  # LTP
                elif dst_fired and not src_fired:
                    # Anti-Hebbian LTD: episode-specific specialization
                    if c.dst.startswith("episode_"):
                        c.weight -= self.learning_rate * 0.5
                        if c.weight < 0.0:
                            c.weight = 0.0
        self.log.append(sorted(fired_now))
        self.tick_count += 1

    def run(self, n_ticks):
        for _ in range(n_ticks):
            self.tick()

    def fired_in_run(self) -> set:
        out = set()
        for fl in self.log: out.update(fl)
        return out

    def get_weight(self, src, dst):
        for c in self.conns:
            if c.src == src and c.dst == dst: return c.weight
        return None

    def utterance(self, since_tick=0):
        words = []
        for t in range(since_tick, len(self.log)):
            for f in self.log[t]:
                if f.startswith("say_"):
                    words.append((t, f[4:]))
        return words


WORD_VOCAB = {
    "dog":   ["form_dog", "vis_furry", "aud_bark"],
    "cat":   ["form_cat", "vis_furry", "aud_meow"],
    "man":   ["form_man", "vis_tall", "olf_human"],
    "apple": ["form_apple", "vis_red", "tas_sweet"],
    "you":   ["form_you", "aud_low"],
    "I":     ["form_I", "aud_low"],
    "Guala": ["form_Guala", "vis_smooth"],
    "patterns": ["form_patterns", "vis_smooth"],
    "binding":  ["form_binding", "vis_smooth"],
    "self":     ["form_self", "aud_low"],
    "world":    ["form_world", "vis_smooth"],
    "am":     ["form_am", "aud_low"],
    "is":     ["form_is", "aud_low"],
    "see":    ["form_see", "aud_low"],
    "like":   ["form_like", "aud_low"],
    "bites":  ["form_bites", "aud_speech"],
    "not":    ["form_not", "aud_low"],
    "furry":  ["form_furry", "vis_furry"],
    "red":    ["form_red", "vis_red"],
    "what":   ["form_what", "aud_high"],
    "are":    ["form_are", "aud_speech"],
    "your":   ["form_your", "aud_low"],
    "name":   ["form_name", "aud_low"],
    "tell":   ["form_tell", "aud_high"],
    "me":     ["form_me", "aud_low"],
    "about":  ["form_about", "aud_low"],
    "interests": ["form_interests", "aud_low"],
    "hello":  ["form_hello", "aud_high"],
    "yes":    ["form_yes", "aud_high"],
    "no":     ["form_no", "aud_low"],
}


def build_guala():
    s = Substrate()

    # Modal layer
    modal_pops = set()
    for modals in WORD_VOCAB.values():
        modal_pops.update(modals)
    for m in sorted(modal_pops):
        s.add(m, threshold=1.0)

    # Word percepts
    for word, modals in WORD_VOCAB.items():
        s.add(f"percept_{word}", threshold=1.0)
        for m in modals:
            s.wire(m, f"percept_{word}", 0.5, plastic=True)

    # say_X populations (output)
    for word in WORD_VOCAB.keys():
        s.add(f"say_{word}", threshold=1.0)

    # Sentence types
    s.add("sent_interrog", threshold=1.0)
    s.add("sent_greet",    threshold=1.0)
    s.add("sent_declar",   threshold=1.0)
    s.add("sent_request",  threshold=1.0)
    s.wire("percept_what",  "sent_interrog", 1.2)
    s.wire("percept_are",   "sent_interrog", 1.2)
    s.wire("percept_hello", "sent_greet",    1.5)
    s.wire("percept_tell",  "sent_request",  1.5)
    s.wire("aud_low",       "sent_declar",   0.6)
    for inh_src in ["percept_what", "percept_are", "percept_hello", "percept_tell"]:
        s.wire(inh_src, "sent_declar", -1.5)

    # Role layer
    s.add("role_subj", threshold=1.0, refractory_period=0)
    s.add("role_obj",  threshold=1.0, refractory_period=0)

    for w in ["dog", "cat", "man", "apple", "Guala", "you"]:
        s.add(f"S_{w}", threshold=1.0)
        s.add(f"O_{w}", threshold=1.0)
        s.wire(f"percept_{w}", f"S_{w}", 1.5,
               needs_coincident="role_subj", plastic=True)
        s.wire(f"percept_{w}", f"O_{w}", 1.5,
               needs_coincident="role_obj", plastic=True)

    # WM topics
    wm_topics = ["wm_topic_self", "wm_topic_dog", "wm_topic_cat",
                 "wm_topic_apple", "wm_topic_man", "wm_topic_patterns",
                 "wm_topic_world", "wm_topic_you"]
    for w in wm_topics:
        s.add(w, threshold=1.0, decay=0.05, refractory_period=0)
        s.wire(w, w, 1.0)
    for percept, wm in [
        ("percept_you", "wm_topic_self"), ("percept_your", "wm_topic_self"),
        ("percept_I", "wm_topic_self"), ("percept_self", "wm_topic_self"),
        ("percept_dog", "wm_topic_dog"), ("percept_cat", "wm_topic_cat"),
        ("percept_apple", "wm_topic_apple"), ("percept_man", "wm_topic_man"),
        ("percept_patterns", "wm_topic_patterns"),
        ("percept_binding", "wm_topic_patterns"),
        ("percept_world", "wm_topic_world"),
    ]:
        s.wire(percept, wm, 3.0)
    # Inter-topic cross-inhibition (NON-self topics only — self stays latched
    # because self can host predicate negations like "are you dog").
    nonself_topics = ["wm_topic_dog", "wm_topic_cat", "wm_topic_apple",
                      "wm_topic_man", "wm_topic_patterns", "wm_topic_world"]
    topic_percepts = {
        "wm_topic_dog":     ["percept_dog"],
        "wm_topic_cat":     ["percept_cat"],
        "wm_topic_apple":   ["percept_apple"],
        "wm_topic_man":     ["percept_man"],
        "wm_topic_patterns":["percept_patterns", "percept_binding"],
        "wm_topic_world":   ["percept_world"],
    }
    for wm_target, percepts in topic_percepts.items():
        for wm_other in nonself_topics:
            if wm_other == wm_target: continue
            for p in percepts:
                s.wire(p, wm_other, -2.0)

    # Self-topic clearing: only when a request asks about a thing
    # (tell me about X) — percept_tell + a thing
    # Implemented via direct wires below

    # Topic lateral inhibition between non-self topics
    for w1 in nonself_topics:
        for w2 in nonself_topics:
            if w1 != w2:
                s.wire(w1, w2, -1.5)
    # wm_topic_self only gets weak inhibition from other topics
    for w in nonself_topics:
        s.wire(w, "wm_topic_self", -0.3)
        s.wire("wm_topic_self", w, -0.3)

    # Recent-sentence WM
    for w in ["wm_recent_query", "wm_recent_greet", "wm_recent_request"]:
        s.add(w, threshold=1.0, decay=0.05, refractory_period=0)
        s.wire(w, w, 1.0)
    s.wire("sent_interrog", "wm_recent_query",   1.2)
    s.wire("sent_greet",    "wm_recent_greet",   1.2)
    s.wire("sent_request",  "wm_recent_request", 1.2)

    # sent_request clears wm_topic_self (asking about a thing, not Guala)
    s.wire("sent_request", "wm_topic_self", -2.0)
    # And clears prior interrog memory
    s.wire("sent_request", "wm_recent_query", -2.0)
    s.wire("sent_interrog", "wm_recent_request", -2.0)

    # Self-model
    s.add("self_am_Guala",   threshold=1.0, decay=0.5)
    s.add("self_not_dog",    threshold=1.0, decay=0.5)
    s.add("self_not_person", threshold=1.0, decay=0.5)
    s.wire("wm_topic_self", "self_am_Guala", 0.3)
    s.wire("percept_name",  "self_am_Guala", 1.0,
           needs_coincident="wm_topic_self")
    s.wire("percept_dog", "self_not_dog", 1.5,
           needs_coincident="wm_topic_self")
    s.wire("percept_man", "self_not_person", 1.5,
           needs_coincident="wm_topic_self")

    # Sustained negation WM — once a "are you X" question fires negation,
    # this latches and keeps suppressing the affirmative intro template.
    s.add("wm_negate_active", threshold=1.0, decay=0.05, refractory_period=0)
    s.wire("self_not_dog",    "wm_negate_active", 1.5)
    s.wire("self_not_person", "wm_negate_active", 1.5)
    s.wire("wm_negate_active", "wm_negate_active", 1.0)
    # Cleared when conversation topic shifts
    s.wire("percept_name",  "wm_negate_active", -2.0)
    s.wire("sent_request",  "wm_negate_active", -2.0)
    s.wire("wm_topic_dog",   "wm_negate_active", -2.0)
    s.wire("wm_topic_apple", "wm_negate_active", -2.0)

    # Interests (with baseline activation)
    # interest_patterns has baseline > threshold*decay to spontaneously fire
    s.add("interest_patterns", threshold=1.0, decay=0.3, baseline=0.4)
    s.add("interest_self",     threshold=1.0, decay=0.5, baseline=0.15)
    s.add("interest_you",      threshold=1.0, decay=0.5, baseline=0.15)

    s.wire("percept_patterns",  "interest_patterns", 1.5)
    s.wire("percept_binding",   "interest_patterns", 1.5)
    s.wire("percept_interests", "interest_patterns", 1.5)
    s.wire("wm_topic_patterns", "interest_patterns", 0.4)
    s.wire("wm_topic_self",     "interest_self",     0.4)
    s.wire("percept_you",       "interest_you",      0.6)

    # Hub (awareness)
    s.add("hub", threshold=0.75, decay=0.3)
    for src in ["S_dog", "O_dog", "S_man", "O_man", "S_apple", "O_apple",
                "S_Guala", "sent_interrog", "sent_greet",
                "wm_topic_self", "self_am_Guala"]:
        s.wire(src, "hub", 0.3)
    s.wire("hub", "interest_patterns", 0.5)

    # === Sentence template machinery ===
    talk_pops = ["talk_greet", "talk_intro", "talk_negate_dog",
                 "talk_negate_person", "talk_interest_patterns",
                 "talk_about_dog", "talk_about_apple"]
    ctx_pops = ["ctx_greet", "ctx_intro", "ctx_negate_dog",
                "ctx_negate_person", "ctx_interest_patterns",
                "ctx_about_dog", "ctx_about_apple"]
    end_pops = ["end_greet", "end_intro", "end_negate_dog",
                "end_negate_person", "end_interest_patterns",
                "end_about_dog", "end_about_apple"]

    for t in talk_pops:
        s.add(t, threshold=1.0, refractory_period=20)
    for c in ctx_pops:
        s.add(c, threshold=1.0, decay=0.1, refractory_period=0)
        s.wire(c, c, 1.0)  # self-sustain
    for e in end_pops:
        s.add(e, threshold=1.0)

    # Talk triggers
    s.wire("sent_greet",       "talk_greet", 1.5)

    s.wire("wm_topic_self",    "talk_intro", 0.3)
    s.wire("self_am_Guala",    "talk_intro", 0.8)
    s.wire("wm_negate_active", "talk_intro", -3.0)  # sustained suppression
    s.wire("percept_interests","talk_intro", -3.0)

    s.wire("self_not_dog",     "talk_negate_dog", 1.5)
    s.wire("self_not_person",  "talk_negate_person", 1.5)

    # Interest talk: SPECIFIC percept request OR idle-state spontaneous
    s.wire("percept_interests",  "talk_interest_patterns", 1.5)
    # Idle population: high baseline, but inhibited by any percept firing.
    # In silence: nothing inhibits, drives talk. Under input: suppressed.
    s.add("idle", threshold=1.0, decay=0.1, baseline=0.3)
    for w in WORD_VOCAB.keys():
        s.wire(f"percept_{w}", "idle", -2.0)
    s.wire("idle", "talk_interest_patterns", 1.0)

    s.wire("wm_topic_dog",       "talk_about_dog", 0.5)
    s.wire("wm_recent_request",  "talk_about_dog", 0.5,
           needs_coincident="wm_topic_dog")

    s.wire("wm_topic_apple",     "talk_about_apple", 0.5)
    s.wire("wm_recent_request",  "talk_about_apple", 0.5,
           needs_coincident="wm_topic_apple")

    # Lateral inhibition between talk templates
    for t1 in talk_pops:
        for t2 in talk_pops:
            if t1 != t2:
                s.wire(t1, t2, -2.5)

    # talk → ctx (latch)
    for t, c in zip(talk_pops, ctx_pops):
        s.wire(t, c, 1.5)

    # talk → first word (one-shot, fires only when talk_X fires)
    s.wire("talk_greet",              "say_hello",    1.5)
    s.wire("talk_intro",              "say_I",        1.5)
    s.wire("talk_negate_dog",         "say_I",        1.5)
    s.wire("talk_negate_person",      "say_I",        1.5)
    s.wire("talk_interest_patterns",  "say_I",        1.5)
    s.wire("talk_about_dog",          "say_dog",      1.5)
    s.wire("talk_about_apple",        "say_apple",    1.5)

    # end_X clears ctx_X and inhibits all talk_X for cooldown
    for c, e in zip(ctx_pops, end_pops):
        s.wire(e, c, -3.0)
        for t in talk_pops:
            s.wire(e, t, -3.0)

    # Satiation: saying an interest briefly satisfies it (reduces repetition)
    s.wire("end_interest_patterns", "interest_patterns", -2.0)
    s.wire("end_interest_patterns", "idle", -2.0)

    # === Word chain transitions, gated by ctx (which sustains during sentence) ===
    # No ctx → first-word wires (that would re-fire continuously).
    # Chain transitions only fire once per sentence because each say_X has
    # refractory_period=2 and the chain advances each tick.

    # "hello" — single word, end after say_hello
    s.wire("say_hello", "end_greet", 1.5, needs_coincident="ctx_greet")

    # "I am Guala"
    s.wire("say_I",     "say_am",    1.5, needs_coincident="ctx_intro", plastic=True)
    s.wire("say_am",    "say_Guala", 1.5, needs_coincident="ctx_intro", plastic=True)
    s.wire("say_Guala", "end_intro", 1.5, needs_coincident="ctx_intro")

    # "I am not dog"
    s.wire("say_I",   "say_am",  1.5, needs_coincident="ctx_negate_dog", plastic=True)
    s.wire("say_am",  "say_not", 1.5, needs_coincident="ctx_negate_dog", plastic=True)
    s.wire("say_not", "say_dog", 1.5, needs_coincident="ctx_negate_dog", plastic=True)
    s.wire("say_dog", "end_negate_dog", 1.5, needs_coincident="ctx_negate_dog")

    # "I am not man"
    s.wire("say_I",   "say_am",  1.5, needs_coincident="ctx_negate_person", plastic=True)
    s.wire("say_am",  "say_not", 1.5, needs_coincident="ctx_negate_person", plastic=True)
    s.wire("say_not", "say_man", 1.5, needs_coincident="ctx_negate_person", plastic=True)
    s.wire("say_man", "end_negate_person", 1.5, needs_coincident="ctx_negate_person")

    # "I like patterns"
    s.wire("say_I",        "say_like",     1.5,
           needs_coincident="ctx_interest_patterns", plastic=True)
    s.wire("say_like",     "say_patterns", 1.5,
           needs_coincident="ctx_interest_patterns", plastic=True)
    s.wire("say_patterns", "end_interest_patterns", 1.5,
           needs_coincident="ctx_interest_patterns")

    # "dog is furry"
    s.wire("say_dog", "say_is",    1.5, needs_coincident="ctx_about_dog", plastic=True)
    s.wire("say_is",  "say_furry", 1.5, needs_coincident="ctx_about_dog", plastic=True)
    s.wire("say_furry", "end_about_dog", 1.5, needs_coincident="ctx_about_dog")

    # "apple is red"
    s.wire("say_apple", "say_is",  1.5, needs_coincident="ctx_about_apple", plastic=True)
    s.wire("say_is",    "say_red", 1.5, needs_coincident="ctx_about_apple", plastic=True)
    s.wire("say_red",   "end_about_apple", 1.5, needs_coincident="ctx_about_apple")

    # === FEEDBACK: she hears herself ===
    # say_X drives percept_X with weight less than modal-driven external input.
    # Closes the loop: her output is her input. Substrate basis for self-awareness.
    for word in WORD_VOCAB.keys():
        s.wire(f"say_{word}", f"percept_{word}", 0.7, plastic=True)

    # Plasticity: LTP fires when a sentence completes successfully (any end_X)
    s.add("LTP_say", threshold=1.0, decay=0.1)
    for e in end_pops:
        s.wire(e, "LTP_say", 1.5)
    s.make_modulator("LTP_say")

    # Introspection
    s.add("intro", threshold=1.0, decay=0.5)
    for src in ["self_am_Guala", "self_not_dog", "self_not_person",
                "wm_topic_self", "interest_self", "interest_patterns"]:
        s.wire(src, "intro", 0.35)

    # === HIPPOCAMPAL LAYER: episode memory and mental time travel ===
    EPISODE_COUNT = 8
    episode_pops = [f"episode_{i}" for i in range(EPISODE_COUNT)]

    # Episode pops: high threshold + long refractory so a single episode
    # captures per binding event. WTA between episodes is one-tick lateral,
    # not same-tick — clusters of episodes can fire briefly together but
    # then settle into one-per-cycle via refractory.
    for i, ep in enumerate(episode_pops):
        s.add(ep, threshold=1.0, decay=0.2, refractory_period=60,
              baseline=0.02 + i * 0.02)

    remember_pops = [f"say_{w}" for w in WORD_VOCAB.keys()]
    remember_pops += [
        "wm_topic_self", "wm_topic_dog", "wm_topic_cat", "wm_topic_apple",
        "wm_topic_man", "wm_topic_patterns", "wm_topic_world", "wm_topic_you",
        "interest_patterns", "interest_self", "interest_you",
        "self_am_Guala", "self_not_dog", "self_not_person",
        "hub", "wm_recent_query", "wm_recent_request", "wm_recent_greet",
    ]

    # Small initial in-weights — plasticity grows them per captured pattern
    for ep in episode_pops:
        for src in remember_pops:
            s.wire(src, ep, 0.02, plastic=True)

    # Out-weights start at 0 — plasticity grows them ONLY to pops in the
    # captured pattern
    for ep in episode_pops:
        for dst in remember_pops:
            s.wire(ep, dst, 0.0, plastic=True)

    # Winner-take-all between episodes (one-tick lateral)
    for ep1 in episode_pops:
        for ep2 in episode_pops:
            if ep1 != ep2:
                s.wire(ep1, ep2, -1.5)

    # Capture pulse: hub-driven, rate-limited so capture is rare (one per
    # binding peak)
    s.add("capture_pulse", threshold=1.0, decay=0.5, refractory_period=15)
    s.wire("hub", "capture_pulse", 1.5)
    for ep in episode_pops:
        s.wire("capture_pulse", ep, 1.2)

    # Default Mode Network drive: fires under sustained silence, drives
    # episode replay (mental time travel)
    s.add("dmn_drive", threshold=1.0, decay=0.05, baseline=0.08)
    for w in WORD_VOCAB.keys():
        s.wire(f"percept_{w}", "dmn_drive", -0.6)
        s.wire(f"say_{w}",     "dmn_drive", -0.5)
    for ep in episode_pops:
        s.wire("dmn_drive", ep, 1.0)

    # Episodes are plasticity modulators (consolidation during capture AND replay)
    for ep in episode_pops:
        s.make_modulator(ep)

    return s


def perceive_utterance(s, words, role_sequence=None):
    if role_sequence is None:
        role_sequence = [None] * len(words)
    for word, role in zip(words, role_sequence):
        if word not in WORD_VOCAB:
            continue
        for modal in WORD_VOCAB[word]:
            s.inject(modal, 1.0)
        s.tick()
        if role == "subj":
            s.inject("role_subj", 1.0)
        elif role == "obj":
            s.inject("role_obj", 1.0)
        s.tick()
        s.tick()


def say(s, since_tick=None):
    if since_tick is None: since_tick = 0
    return [w for _, w in s.utterance(since_tick)]


def hear_and_respond(s, words, role_sequence=None, response_ticks=25):
    start = s.tick_count  # Capture from before perception
    perceive_utterance(s, words, role_sequence)
    s.run(response_ticks)
    return say(s, start)


def silence(s, n_ticks=30):
    start = s.tick_count
    s.run(n_ticks)
    return say(s, start)
