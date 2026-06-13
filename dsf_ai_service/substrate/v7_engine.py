"""
V7 DNA Recipe Engine — unified lexical-category substrate.
GL-BRIEF-V7-UNIFY-WC-20260613-01

Replaces S/V/O positional slots with proper lexical categories (N, V, Adj,
Adv) plus closed-class sections (Det, P, Aux, etc.). Grammar table drives
emission instead of fixed 3-slot cycle.

Keeps: NMDA gates, drive_tracker, intro/aware, quiet_tick, apply_feedback,
save/load, event_log, all assemblage primitives.
"""
import threading, json, os, time
import numpy as np
from collections import defaultdict

from dsf_ai_service.substrate.assemblage import (
    Section, System, N, normalize, random_unit_complex, goal_op_for_template,
)
from dsf_ai_service.substrate.gl_nmda import (
    CoincidenceGate, context_no_recent_drive, update_drive_tracker,
)
from dsf_ai_service.substrate.gl_plasticity import (
    install_plasticity, decay_plasticity, reinforce_mode,
)
from dsf_ai_service.substrate.dna_recipe.phase_gating import (
    make_projection, first_commit_per_section, make_phase_gater,
)

# ---- Closed-class lexicon ----
CLOSED_CLASS_LEXICON = {}
_CC = {
    "Det": "the a an this that these those my your his her its our their".split(),
    "Quant": "one two three four five many much some any all every few several".split(),
    "P": ("in on at to from with for by about of up down over under through "
          "into out between around near off along across behind before after "
          "above below").split(),
    "Pronoun": "i you he she it we they me him us them myself yourself".split(),
    "Conj": "and or but so yet nor".split(),
    "SubConj": "if when because although while since before after until unless though".split(),
    "RelPronoun": "who whom which whose that".split(),
    "CompConj": "that if whether".split(),
    "Aux": ("is are am was were be been being have has had do does did "
            "will would shall should can could may might must").split(),
}
for _cat, _words in _CC.items():
    for _w in _words:
        if _w not in CLOSED_CLASS_LEXICON:
            CLOSED_CLASS_LEXICON[_w] = _cat

CLOSED_CLASS_CATS = list(_CC.keys())
CONTENT_SECTIONS = ["N", "V", "Adj", "Adv"]
ALL_SECTIONS = CONTENT_SECTIONS + CLOSED_CLASS_CATS + ["listen", "intro", "aware"]

# ---- Grammar table ----
GRAMMAR = {
    "S":    [["NP", "VP"], ["NP", "VP", "PP"]],
    "NP":   [["Det?", "Adj?", "N"], ["Pronoun"], ["N"]],
    "VP":   [["Aux?", "V", "NP?", "AdvP?", "PP?"], ["Aux?", "V", "AdvP?"]],
    "AdjP": [["Adv?", "Adj"]],
    "AdvP": [["Adv"]],
    "PP":   [["P", "NP"]],
}
_TERMINAL_TO_SECTION = {
    "Det": "Det", "Adj": "Adj", "N": "N", "Pronoun": "Pronoun",
    "Aux": "Aux", "V": "V", "Adv": "Adv", "P": "P",
}
_NON_TERMINALS = set(GRAMMAR.keys())

SEED_VOCAB = {
    "N": ["cow", "moon", "bears", "fence", "milk", "dish"],
    "V": ["jumped", "ran", "sleeps"],
}


def seed_vocab_from_engine(engine):
    """Read v6 engine word_modes and categorize into lexical sections."""
    result = defaultdict(list)
    word_modes = getattr(engine, "word_modes", {})
    if not word_modes:
        return dict(SEED_VOCAB)
    for label in word_modes:
        w = label.lower().strip()
        if not w:
            continue
        if w in CLOSED_CLASS_LEXICON:
            cat = CLOSED_CLASS_LEXICON[w]
        else:
            cat = "N"
        if w not in result[cat]:
            result[cat].append(w)
    if not result["N"]:
        result["N"] = list(SEED_VOCAB.get("N", ["thing"]))
    if not result["V"]:
        result["V"] = list(SEED_VOCAB.get("V", ["is"]))
    return dict(result)


def _make_zero_section(name, rng, role="general"):
    """Helper: section with zeroed Hamiltonian."""
    sec = Section(name=name, rng=rng, role=role)
    sec.H_base = np.zeros((N, N), dtype=complex)
    sec.law_fields = {k: np.zeros((N, N), dtype=complex)
                      for k in ("symmetry", "consistency", "compactness")}
    return sec


class V7Session:
    """Per-session v7 substrate with lexical-category sections."""

    def __init__(self, session_id, rng_seed=None, engine=None):
        self.session_id = session_id
        self.lock = threading.Lock()
        self.created_at = time.time()
        from dsf_ai_service.substrate.event_log import EventLog
        self.event_log = EventLog(STATE_DIR, session_id)
        seed = rng_seed or hash(session_id) % (2**31)
        self.rng = np.random.default_rng(seed)
        self.vocab = seed_vocab_from_engine(engine) if engine else \
            {k: list(v) for k, v in SEED_VOCAB.items()}
        self.sys_, self.token_vec, self.intro_vec, self.intro_modes, \
            self.aware_vec, self.aware_modes = self._build_system()
        for sn in CONTENT_SECTIONS + ["intro", "aware"]:
            if sn in self.sys_.sections:
                install_plasticity(self.sys_.sections[sn], initial_strength=1.0)
        self.drive_tracker = {}
        self.intro_gate = CoincidenceGate(
            section_name="intro",
            context_fn=context_no_recent_drive(
                self.drive_tracker, sections=tuple(CONTENT_SECTIONS),
                quiet_thresh=0.45),
            drive_thresh=0.05, ltp_boost=0.05)
        self.aware_gate = CoincidenceGate(
            section_name="aware",
            context_fn=lambda sys_: (
                len(sys_.sections["intro"].krimelack) > 0 and
                (sys_.tick - sys_.sections["intro"].krimelack[-1]["tick"]) <= 5),
            drive_thresh=0.05, ltp_boost=0.05)
        self.last_intro_state = None
        self.last_aware_state = None
        self.last_rhythm_phase = "N"
        self.last_emissions = []
        self.last_nmda_events = []
        self.last_routing_log = []
        self.intro_commit_history = []
        self.aware_commit_history = []
        self.tick_at_last_converse = 0
        self._last_converse_time = time.time()

    def _build_system(self):
        rng = self.rng
        secs = []
        # Content sections (full Hamiltonian)
        for cat in CONTENT_SECTIONS:
            role = "verb_like" if cat == "V" else "subject_like"
            secs.append(Section(name=cat, rng=rng, role=role))
        # Closed-class + listen/intro/aware (zeroed Hamiltonian)
        for cat in CLOSED_CLASS_CATS:
            secs.append(_make_zero_section(cat, rng))
        secs.append(_make_zero_section("listen", rng))
        secs.append(_make_zero_section("intro", rng, role="intro"))
        secs.append(_make_zero_section("aware", rng, role="intro"))
        for s in secs:
            s.map_inject = make_projection(N, 8, rng)
        sys_ = System(secs, rng)

        # Install vocab
        token_vec = {}
        for cat, words in self.vocab.items():
            if cat not in sys_.sections:
                continue
            sec = sys_.sections[cat]
            for word in words:
                v = random_unit_complex(N, rng)
                sec.mode_bank.append(v.copy())
                sec.mode_last_used.append(0)
                sec.mode_strength.append(1.0)
                token_vec[(cat, word)] = v
                sys_.sections["listen"].mode_bank.append(v.copy())
                sys_.sections["listen"].mode_last_used.append(0)
                sys_.sections["listen"].mode_strength.append(1.0)

        # Install closed-class words not already in vocab
        for cat, words in _CC.items():
            sec = sys_.sections[cat]
            for word in words:
                if (cat, word) in token_vec:
                    continue
                v = random_unit_complex(N, rng)
                sec.mode_bank.append(v.copy())
                sec.mode_last_used.append(0)
                sec.mode_strength.append(1.0)
                token_vec[(cat, word)] = v
                self.vocab.setdefault(cat, [])
                if word not in self.vocab[cat]:
                    self.vocab[cat].append(word)

        # Intro + aware modes
        intro_modes = ["i_quiet", "i_hear", "i_emit"]
        intro_vec = {}
        for name in intro_modes:
            v = random_unit_complex(N, rng)
            sys_.sections["intro"].mode_bank.append(v.copy())
            sys_.sections["intro"].mode_last_used.append(0)
            sys_.sections["intro"].mode_strength.append(1.0)
            intro_vec[name] = v
        aware_modes = ["aware_quiet", "aware_listening", "aware_emitting"]
        aware_vec = {}
        for name in aware_modes:
            v = random_unit_complex(N, rng)
            sys_.sections["aware"].mode_bank.append(v.copy())
            sys_.sections["aware"].mode_last_used.append(0)
            sys_.sections["aware"].mode_strength.append(1.0)
            aware_vec[name] = v
        for sec in sys_.sections.values():
            sec.snapshot_initial_modes()
        return sys_, token_vec, intro_vec, intro_modes, aware_vec, aware_modes

    # ---- Lexical routing ----
    def _classify_word(self, word, prev_cat):
        """Classify content word by preceding category heuristic."""
        if word in CLOSED_CLASS_LEXICON:
            return CLOSED_CLASS_LEXICON[word]
        if prev_cat in ("Det", "Adj", "Quant", "P"):
            return "N"
        if prev_cat in ("Aux", "Adv", "Pronoun", "N"):
            return "V"
        if prev_cat == "V":
            return "N"
        return "N"

    def lookup_or_install(self, word, prev_cat=None):
        """Return (word_vec, category, was_new). No position lottery."""
        word = word.lower().strip(".,?!;:'\"")
        if not word:
            return None, None, False
        # Closed-class: already installed
        if word in CLOSED_CLASS_LEXICON:
            cat = CLOSED_CLASS_LEXICON[word]
            key = (cat, word)
            if key in self.token_vec:
                words = self.vocab.get(cat, [])
                idx = words.index(word) if word in words else -1
                sec = self.sys_.sections.get(cat)
                if sec and 0 <= idx < len(sec.mode_bank):
                    return sec.mode_bank[idx], cat, False
            return None, cat, False
        # Already installed content word?
        for cat in CONTENT_SECTIONS:
            words = self.vocab.get(cat, [])
            if word in words:
                idx = words.index(word)
                sec = self.sys_.sections[cat]
                if idx < len(sec.mode_bank):
                    return sec.mode_bank[idx], cat, False
        # New content word
        cat = self._classify_word(word, prev_cat)
        if cat not in self.sys_.sections or cat in CLOSED_CLASS_CATS:
            cat = "N"
        sec = self.sys_.sections[cat]
        word_vec = random_unit_complex(N, self.rng)
        sec.mode_bank.append(word_vec.copy())
        sec.mode_last_used.append(self.sys_.tick)
        sec.mode_strength.append(1.0)
        self.sys_.sections["listen"].mode_bank.append(word_vec.copy())
        self.sys_.sections["listen"].mode_last_used.append(self.sys_.tick)
        self.sys_.sections["listen"].mode_strength.append(1.0)
        self.vocab.setdefault(cat, [])
        self.vocab[cat].append(word)
        self.token_vec[(cat, word)] = word_vec
        sec.snapshot_initial_modes()
        self.sys_.sections["listen"].snapshot_initial_modes()
        self.event_log.write("vocab_install", slot=cat, word=word)
        return word_vec, cat, True

    # ---- Grammar-driven emission ----
    def _section_top_arc(self, cat):
        sec = self.sys_.sections.get(cat)
        if sec is None:
            return None, 0.0
        arcs = sec.arcs()
        if len(arcs) == 0:
            return None, 0.0
        top = int(arcs.argmax())
        return self._mode_to_word(cat, top), float(arcs[top])

    def _expand_grammar(self, max_tokens=12):
        """Recursively expand grammar from S, select top-arc words at terminals."""
        tokens = []
        def expand(symbol):
            if len(tokens) >= max_tokens:
                return
            optional = symbol.endswith("?")
            sym = symbol.rstrip("?")
            if sym in _NON_TERMINALS:
                for prod in GRAMMAR[sym]:
                    for s in prod:
                        expand(s)
                    break
                return
            sec_name = _TERMINAL_TO_SECTION.get(sym, sym)
            word, arc = self._section_top_arc(sec_name)
            if optional and arc < 0.03:
                return
            if word is None:
                return
            sec = self.sys_.sections[sec_name]
            top = int(sec.arcs().argmax())
            ms = sec.mode_strength[top] if hasattr(sec, "mode_strength") and top < len(sec.mode_strength) else 0.0
            tokens.append({"section": sec_name, "token": word,
                           "emit_tick": self.sys_.tick,
                           "mode_strength": round(ms, 3), "arc": round(arc, 3)})
        expand("S")
        return tokens

    # ---- Main conversation ----
    def converse(self, text, source="ui"):
        with self.lock:
            tokens = [t.lower().strip(".,?!;:'\"") for t in text.split() if t.strip()]
            if not tokens:
                return self._empty_response("empty input")
            # Per-turn psi + goals reset
            for sn in ALL_SECTIONS:
                if sn not in self.sys_.sections:
                    continue
                sec = self.sys_.sections[sn]
                sec.psi = normalize(
                    random_unit_complex(N, self.rng) * 0.3 +
                    normalize(np.ones(N, dtype=complex)) * 0.7)
                sec.standing_goals = []
                sec.goals = []
            self.drive_tracker.clear()
            routing_log, nmda_events, rhythm_events = [], [], []

            # PHASE 1: Route words
            heard = {}
            any_routed = False
            prev_cat = None
            for word in tokens:
                word_vec, cat, was_new = self.lookup_or_install(word, prev_cat=prev_cat)
                routing_log.append({"word": word, "routed_to": cat,
                                    "newly_installed": was_new} if cat else
                                   {"word": word, "routed_to": None, "reason": "skipped"})
                if cat:
                    heard[cat] = word
                    prev_cat = cat
                    if word_vec is not None:
                        any_routed = True
            if not any_routed:
                return self._empty_response("no content words routed")

            # PHASE 2: Listen-accumulate
            for sn in ALL_SECTIONS:
                if sn in self.sys_.sections:
                    self.sys_.sections[sn]._emit_phase = True
            accumulated = {}
            for cat, word in heard.items():
                key = (cat, word)
                if key not in self.token_vec:
                    continue
                target = self.token_vec[key]
                acc = np.zeros(N, dtype=complex)
                for _ in range(15):
                    noisy = normalize(target + 0.10 * (
                        self.rng.standard_normal(N) + 1j * self.rng.standard_normal(N)))
                    acc += noisy
                    self.sys_.tick_once({"listen": noisy}, enable_self_evo=True,
                                        coordinator_on=False, introspection_on=False,
                                        allow_rewiring=False)
                accumulated[cat] = normalize(acc)
            self.last_intro_state = "i_hear"
            self.intro_commit_history.append({"state": "i_hear", "tick": self.sys_.tick})
            self.intro_commit_history = self.intro_commit_history[-10:]
            for sn in ALL_SECTIONS:
                if sn != "listen" and sn in self.sys_.sections:
                    self.sys_.sections[sn]._emit_phase = False

            # PHASE 3: Derive drives
            drives = {}
            for cat in CONTENT_SECTIONS:
                snap = accumulated.get(cat)
                sec = self.sys_.sections[cat]
                if snap is None or np.linalg.norm(snap) == 0:
                    drives[cat] = random_unit_complex(N, self.rng) * 0.1
                    continue
                weights = []
                for mid, mvec in enumerate(sec.mode_bank):
                    d = float(np.abs(np.vdot(mvec, snap)) ** 2)
                    s = sec.mode_strength[mid] if mid < len(sec.mode_strength) else 1.0
                    weights.append((mid, d * s, mvec))
                weights.sort(key=lambda x: -x[1])
                bias = sum((w * v for _, w, v in weights[:2]), np.zeros(N, dtype=complex))
                drives[cat] = normalize(bias) if np.linalg.norm(bias) > 0 \
                    else random_unit_complex(N, self.rng)
            for cat in CLOSED_CLASS_CATS:
                if cat in accumulated:
                    drives[cat] = accumulated[cat]
            for cat, drv in drives.items():
                if cat in self.sys_.sections:
                    self.sys_.sections[cat].psi = drv.copy()

            # PHASE 4: Commit-driven emission
            for sec in self.sys_.sections.values():
                sec._emit_phase = True
            emit_commits = []
            strength = 0.45
            for t in range(120):
                for cat in CONTENT_SECTIONS:
                    decay_plasticity(self.sys_.sections[cat], decay=0.998)
                cur = CONTENT_SECTIONS[t % len(CONTENT_SECTIONS)]
                self.last_rhythm_phase = cur
                rhythm_events.append({"tick": self.sys_.tick + 1, "phase": cur})
                for cat in CONTENT_SECTIONS:
                    sec = self.sys_.sections[cat]
                    sec.excitation_expires_at = self.sys_.tick + 2
                    sec.excitation_strength = strength if cat == cur else -strength
                ev = {}
                for cat in CONTENT_SECTIONS:
                    d = drives.get(cat)
                    if d is not None:
                        ev[cat] = normalize(d + 0.10 * (
                            self.rng.standard_normal(N) + 1j * self.rng.standard_normal(N)))
                commits = self.sys_.tick_once(ev, enable_self_evo=True,
                                              coordinator_on=False, introspection_on=False,
                                              allow_rewiring=False)
                emit_commits.extend(commits)
                if len({c["section"] for c in emit_commits if c["section"] in CONTENT_SECTIONS}) >= len(CONTENT_SECTIONS):
                    break
            for sec in self.sys_.sections.values():
                sec._emit_phase = False
            response_tokens = self._expand_grammar(max_tokens=12)

            # POST-EMIT: intro + aware
            for c in emit_commits:
                update_drive_tracker(self.drive_tracker,
                                     {c["section"]: np.ones(N, dtype=complex) * 0.5})
            self._nmda_pass("intro", self.intro_vec.get("i_emit"),
                            self.intro_gate, self.intro_modes,
                            nmda_events, "intro_state", "intro_commit_history")
            aware_name = {"i_quiet": "aware_quiet", "i_hear": "aware_listening",
                          "i_emit": "aware_emitting"}.get(
                self.last_intro_state or "i_emit", "aware_emitting")
            self._nmda_pass("aware", self.aware_vec.get(aware_name),
                            self.aware_gate, self.aware_modes,
                            nmda_events, "aware_state", "aware_commit_history")

            self.last_emissions = emit_commits
            self.last_nmda_events = nmda_events
            self.last_routing_log = routing_log
            self.tick_at_last_converse = self.sys_.tick
            self._last_converse_time = time.time()
            self.event_log.write("converse",
                                 text=" ".join(tokens),
                                 emitted=[t.get("token", "") for t in response_tokens],
                                 tick=self.sys_.tick)
            return {
                "response_tokens": response_tokens,
                "routing_log": routing_log,
                "rhythm_events": rhythm_events[-10:],
                "nmda_events": nmda_events[-20:],
                "introspection": {"reported_state": self.last_intro_state or "i_quiet",
                                  "tick": self.sys_.tick,
                                  "recent_commits": self.intro_commit_history[-3:]},
                "awareness": {"reported_state": self.last_aware_state or "aware_quiet",
                              "tick": self.sys_.tick,
                              "recent_commits": self.aware_commit_history[-3:]},
                "mode_strengths": self._get_mode_strengths(),
                "raw_emissions": [{"section": c["section"], "mode_id": c["mode_id"],
                                   "reason": c["reason"]} for c in emit_commits[-20:]],
                "unknown_words": [r["word"] for r in routing_log if r.get("routed_to") is None],
            }

    def _nmda_pass(self, sec_name, target_vec, gate, mode_names, nmda_events,
                   state_attr, history_attr):
        """Unified post-emit NMDA pass for intro/aware sections."""
        if target_vec is None:
            return
        for _ in range(10):
            noisy = normalize(target_vec + 0.05 * (
                self.rng.standard_normal(N) + 1j * self.rng.standard_normal(N)))
            ev = {sec_name: noisy}
            if sec_name == "intro":
                update_drive_tracker(self.drive_tracker, ev)
            self.sys_.tick_once(ev, enable_self_evo=True,
                                coordinator_on=False, introspection_on=False,
                                allow_rewiring=False)
            sec = self.sys_.sections[sec_name]
            while len(sec.mode_bank) > len(mode_names):
                sec.mode_bank.pop()
                sec.mode_last_used.pop()
            fired, mode_id, eval_d = gate.check_and_fire(self.sys_)
            eval_d["tick"] = self.sys_.tick
            eval_d["fired"] = fired
            if sec_name == "intro":
                eval_d["drive_tracker"] = {k: round(v, 4) for k, v in self.drive_tracker.items()}
            nmda_events.append(eval_d)
            if fired and mode_id is not None and mode_id < len(mode_names):
                new_state = mode_names[mode_id]
                setattr(self, "last_" + state_attr, new_state)
                hist = getattr(self, history_attr)
                hist.append({"state": new_state, "tick": self.sys_.tick})
                while len(hist) > 10:
                    hist.pop(0)

    def _empty_response(self, reason):
        return {
            "response_tokens": [], "routing_log": [], "rhythm_events": [],
            "nmda_events": [],
            "introspection": {"reported_state": "i_quiet",
                              "tick": self.sys_.tick, "recent_commits": []},
            "awareness": {"reported_state": "aware_quiet",
                          "tick": self.sys_.tick, "recent_commits": []},
            "mode_strengths": self._get_mode_strengths(),
            "raw_emissions": [], "unknown_words": [],
            "honest_silence_reason": reason,
        }

    def quiet_tick(self, n_ticks=1):
        """Quiet ticks — substrate Default Mode. C4: evaluate intro gate."""
        with self.lock:
            results = []
            for _ in range(n_ticks):
                result = self.sys_.replay_tick(rng=self.rng)
                update_drive_tracker(self.drive_tracker, {})
                i_fired, i_mode, i_eval = self.intro_gate.check_and_fire(self.sys_)
                i_eval.update(tick=self.sys_.tick, fired=i_fired, source="quiet_tick")
                if not hasattr(self, '_quiet_nmda_events'):
                    self._quiet_nmda_events = []
                self._quiet_nmda_events.append(i_eval)
                self._quiet_nmda_events = self._quiet_nmda_events[-20:]
                if i_fired and i_mode is not None and i_mode < len(self.intro_modes):
                    self.last_intro_state = self.intro_modes[i_mode]
                    self.intro_commit_history.append(
                        {"state": self.last_intro_state, "tick": self.sys_.tick})
                    self.intro_commit_history = self.intro_commit_history[-10:]
                    if len(self.intro_commit_history) <= 1 or \
                       self.intro_commit_history[-1]["state"] != \
                       self.intro_commit_history[-2].get("state"):
                        print(f"[v7-intro] FIRED during quiet: mode={i_mode} "
                              f"state={self.last_intro_state} tick={self.sys_.tick}")
                results.append(result)
            total_r = sum(len(r["replayed"]) for r in results)
            total_c = sum(len(r["commits"]) for r in results)
            self._last_replay_result = {"replayed": total_r, "commits": total_c, "ticks": len(results)}
            if total_r > 0:
                self.event_log.write("quiet", n_ticks=len(results),
                                     replayed=total_r, commits=total_c)
            return results

    def apply_feedback(self, correct, expected_tokens=None):
        """Supervised LTP from thumbs-up/down."""
        with self.lock:
            affected = []
            for cat in CONTENT_SECTIONS:
                sec = self.sys_.sections[cat]
                if not hasattr(sec, "mode_strength"):
                    continue
                arcs = sec.arcs()
                if len(arcs) == 0:
                    continue
                top = int(arcs.argmax())
                if correct:
                    reinforce_mode(sec, top, boost=0.05, ceiling=2.5)
                else:
                    sec.mode_strength[top] = max(0.0, sec.mode_strength[top] - 0.02)
                affected.append({"section": cat, "mode_id": top,
                                 "new_strength": sec.mode_strength[top]})
            self.event_log.write("feedback", correct=correct,
                                 affected=[{"section": a["section"], "mode_id": a["mode_id"],
                                            "strength": a["new_strength"]} for a in affected])
            return {"ltp_applied": correct, "affected_modes": affected}

    def get_state(self, engine=None):
        """Snapshot for UI panel polling."""
        with self.lock:
            state = {
                "tick": self.sys_.tick,
                "rhythm_phase": self.last_rhythm_phase,
                "introspection": self.last_intro_state or "i_quiet",
                "intro_recent": self.intro_commit_history[-3:],
                "awareness": self.last_aware_state or "aware_quiet",
                "aware_recent": self.aware_commit_history[-3:],
                "mode_strengths": self._get_mode_strengths(),
                "nmda_events": self.last_nmda_events[-10:],
                "routing_log": self.last_routing_log,
                "n_commits_total": sum(len(s.krimelack) for s in self.sys_.sections.values()),
                "intro_krimelack_count": len(self.sys_.sections["intro"].krimelack),
                "aware_krimelack_count": len(self.sys_.sections["aware"].krimelack),
                "intro_krimelack_recent": [
                    {"tick": k["tick"], "mode_id": k["mode_id"],
                     "salience": round(k.get("salience", 0), 3)}
                    for k in self.sys_.sections["intro"].krimelack[-5:]],
                "aware_krimelack_recent": [
                    {"tick": k["tick"], "mode_id": k["mode_id"],
                     "salience": round(k.get("salience", 0), 3)}
                    for k in self.sys_.sections["aware"].krimelack[-5:]],
                "last_replay": getattr(self, "_last_replay_result", None),
                "bridge_active": hasattr(self, "_bridge") and self._bridge is not None,
                "vocab_counts": {c: len(self.vocab.get(c, []))
                                 for c in CONTENT_SECTIONS + CLOSED_CLASS_CATS},
            }
            if engine is not None:
                state["v6_vocab_count"] = len(getattr(engine, "word_modes", {}))
                atlas = getattr(self.sys_, "atlas", None)
                state["atlas_count"] = len(atlas.entries) if atlas else 0
            return state

    def _mode_to_word(self, section_name, mode_id):
        toks = self.vocab.get(section_name, [])
        return toks[mode_id] if mode_id < len(toks) else None

    def _get_mode_strengths(self):
        out = {}
        for cat in CONTENT_SECTIONS:
            sec = self.sys_.sections[cat]
            strengths = {}
            toks = self.vocab.get(cat, [])
            if hasattr(sec, "mode_strength"):
                for i, tok in enumerate(toks):
                    if i < len(sec.mode_strength):
                        strengths[tok] = round(sec.mode_strength[i], 3)
            out[cat] = strengths
        return out

    # ---- Serialization ----
    def _serialize_section(self, sec):
        return {
            "name": sec.name,
            "psi_re": sec.psi.real.tolist(),
            "psi_im": sec.psi.imag.tolist(),
            "mode_bank_re": [m.real.tolist() for m in sec.mode_bank],
            "mode_bank_im": [m.imag.tolist() for m in sec.mode_bank],
            "mode_last_used": list(sec.mode_last_used),
            "mode_strength": list(getattr(sec, "mode_strength", [])),
            "gamma": dict(sec.gamma),
            "det_commit": sec.det_commit, "p_commit": sec.p_commit,
            "tick": getattr(sec, "tick", 0),
            "krimelack_count": len(sec.krimelack),
            "krimelack": [
                {"chi": int(k["chi"]), "tick": int(k["tick"]),
                 "mode_id": int(k["mode_id"]), "reason": k.get("reason", ""),
                 "salience": float(k.get("salience", 0.0))}
                for k in sec.krimelack[-200:]],
        }

    def _restore_section(self, sec, data):
        sec.psi = np.array(data["psi_re"]) + 1j * np.array(data["psi_im"])
        sec.mode_bank = [np.array(r) + 1j * np.array(i)
                         for r, i in zip(data["mode_bank_re"], data["mode_bank_im"])]
        sec.mode_last_used = list(data.get("mode_last_used", [0] * len(sec.mode_bank)))
        if "mode_strength" in data:
            sec.mode_strength = list(data["mode_strength"])
        if "gamma" in data:
            sec.gamma = dict(data["gamma"])

    def compact(self):
        data = self.to_json()
        save_session(self)
        self.event_log.truncate_before(self.event_log.count)
        return data

    def to_json(self):
        state = {
            "schema_version": 3,
            "session_id": self.session_id,
            "event_seq": self.event_log.count,
            "vocab": {k: list(v) for k, v in self.vocab.items()},
            "tick": self.sys_.tick,
            "intro_state": self.last_intro_state,
            "aware_state": self.last_aware_state,
            "sections": {},
            "atlas": {str(k): v for k, v in self.sys_.atlas.entries.items()},
            "keyholes": [
                {"sender": kh["sender"], "chi_lo": kh["chi_lo"],
                 "chi_hi": kh["chi_hi"], "receiver": kh["receiver"],
                 "goal_strength": kh["goal_strength"]}
                for kh in self.sys_.keyholes],
        }
        for sn in ALL_SECTIONS:
            if sn in self.sys_.sections:
                state["sections"][sn] = self._serialize_section(self.sys_.sections[sn])
        return state

    def load_from_json(self, data):
        with self.lock:
            sv = data.get("schema_version", 1)
            if sv < 2:
                for old_sn, new_sn in [("subject", "N"), ("verb", "V"), ("object", "N")]:
                    if old_sn in data and new_sn in self.sys_.sections:
                        sec = self.sys_.sections[new_sn]
                        if hasattr(sec, "mode_strength"):
                            sec.mode_strength = list(data[old_sn])
                self.last_intro_state = data.get("intro_state")
                self.last_aware_state = data.get("aware_state")
                if "vocab" in data:
                    self._migrate_vocab_v1(data["vocab"])
                return
            if sv == 2:
                self.last_intro_state = data.get("intro_state")
                self.last_aware_state = data.get("aware_state")
                if "vocab" in data:
                    self._migrate_vocab_v1(data["vocab"])
                sections = data.get("sections", {})
                _v2_map = {"subject": "N", "verb": "V", "object": "N"}
                for old_sn, sec_data in sections.items():
                    new_sn = _v2_map.get(old_sn, old_sn)
                    if new_sn in self.sys_.sections:
                        self._restore_section(self.sys_.sections[new_sn], sec_data)
                for sn, sec_data in data.get("meta_sections", {}).items():
                    if sn in self.sys_.sections:
                        self._restore_section(self.sys_.sections[sn], sec_data)
                return
            # Schema v3
            if "vocab" in data:
                self.vocab = {k: list(v) for k, v in data["vocab"].items()}
            self.last_intro_state = data.get("intro_state")
            self.last_aware_state = data.get("aware_state")
            for sn, sec_data in data.get("sections", {}).items():
                if sn in self.sys_.sections:
                    self._restore_section(self.sys_.sections[sn], sec_data)

    def _migrate_vocab_v1(self, old_vocab):
        """Migrate v1/v2 vocab (subject/verb/object) to new categories."""
        for old_slot, words in old_vocab.items():
            for w in words:
                wl = w.lower()
                cat = CLOSED_CLASS_LEXICON.get(wl, "V" if old_slot == "verb" else "N")
                self.vocab.setdefault(cat, [])
                if wl not in self.vocab[cat]:
                    self.vocab[cat].append(wl)


# ---- Session manager ----
_sessions = {}
_sessions_lock = threading.Lock()
STATE_DIR = "/app/state/v7_sessions"


def get_or_create_session(session_id, engine=None):
    with _sessions_lock:
        if session_id in _sessions:
            return _sessions[session_id]
        session = V7Session(session_id, engine=engine)
        snapshot_path = os.path.join(STATE_DIR, f"{session_id}.json")
        snapshot_seq = -1
        if os.path.exists(snapshot_path):
            try:
                with open(snapshot_path) as f:
                    data = json.load(f)
                session.load_from_json(data)
                snapshot_seq = data.get("event_seq", -1)
                print(f"[v7] Loaded snapshot for {session_id} (seq={snapshot_seq})")
            except Exception as e:
                print(f"[v7] Snapshot load failed for {session_id}: {e}")
        if session.event_log.exists():
            from dsf_ai_service.substrate.event_log import replay_events
            events = session.event_log.read_since(snapshot_seq)
            if events:
                n = replay_events(session, events)
                print(f"[v7] Replayed {n} events for {session_id}")
        _sessions[session_id] = session
        return session


def save_session(session):
    os.makedirs(STATE_DIR, exist_ok=True)
    path = os.path.join(STATE_DIR, f"{session.session_id}.json")
    data = session.to_json()
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(data, f)
    os.rename(tmp, path)
