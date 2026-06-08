"""
V7 DNA Recipe Engine — wires assemblage + NMDA gates + plasticity + rhythm
+ introspection + awareness into a single conversational substrate.

GL-CMD-DEPLOY-DNA-RECIPE-WC-20260608-01

NOT the v6 engine. NOT the multimodal DeepMultiModalCognition. This is the
assemblage-based substrate with all DNA recipe capabilities.
"""

import threading
import json
import os
import time
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


VOCAB = {
    "subject": ["cow", "moon", "bears", "stars", "kittens", "room",
                 "cat", "dog", "bird", "frog", "fish", "boy", "girl"],
    "verb": ["jumped", "ran", "sleeps", "sat", "flew", "swam", "sang",
             "ate", "said", "went", "looked", "played"],
    "object": ["fence", "milk", "dish", "moon", "hill", "tree",
               "ball", "house", "water", "food", "bed", "song"],
}


class V7Session:
    """Per-session v7 substrate state with full DNA recipe wiring."""

    def __init__(self, session_id, rng_seed=None):
        self.session_id = session_id
        self.lock = threading.Lock()
        self.created_at = time.time()

        seed = rng_seed or hash(session_id) % (2**31)
        self.rng = np.random.default_rng(seed)

        # Build 6-section system: S/V/O + listen + intro + aware
        self.sys_, self.token_vec, self.intro_vec, self.intro_modes, \
            self.aware_vec, self.aware_modes = self._build_system()

        # Install plasticity on S/V/O
        for sn in ("subject", "verb", "object"):
            install_plasticity(self.sys_.sections[sn])

        # Drive tracker for NMDA context
        self.drive_tracker = {}
        self.intro_commit_tracker = {"age": None}

        # NMDA gates
        self.intro_gate = CoincidenceGate(
            section_name="intro",
            context_fn=context_no_recent_drive(
                self.drive_tracker,
                sections=("listen", "subject", "verb", "object"),
                quiet_thresh=0.10),
            drive_thresh=0.05, ltp_boost=0.0,
        )

        # Supervised LTP gates on S/V/O
        self.svo_gates = {}
        for sn in ("subject", "verb", "object"):
            self.svo_gates[sn] = CoincidenceGate(
                section_name=sn,
                context_fn=lambda sys_: True,  # always open; LTP only via feedback
                drive_thresh=0.15,
                ltp_boost=0.0,  # no auto-LTP; feedback drives it
            )

        # Phase gater (L5 rhythm)
        self.phase_gater = make_phase_gater(cycle=24, strength=0.35)

        # State tracking
        self.last_intro_state = None
        self.last_aware_state = None
        self.last_rhythm_phase = "subject"
        self.last_emissions = []
        self.last_nmda_events = []
        self.conversation_log = []
        self.tick_at_last_converse = 0

    def _build_system(self):
        rng = self.rng
        subj = Section(name="subject", rng=rng, role="subject_like")
        verb = Section(name="verb", rng=rng, role="verb_like")
        obj = Section(name="object", rng=rng, role="object_like")
        listen = Section(name="listen", rng=rng, role="general")
        intro = Section(name="intro", rng=rng, role="intro")
        aware = Section(name="aware", rng=rng, role="intro")

        for sec in (listen, intro, aware):
            sec.H_base = np.zeros((N, N), dtype=complex)
            sec.law_fields = {
                "symmetry": np.zeros((N, N), dtype=complex),
                "consistency": np.zeros((N, N), dtype=complex),
                "compactness": np.zeros((N, N), dtype=complex),
            }
        intro.det_commit = 99.0
        intro.p_commit = 99.0
        aware.det_commit = 99.0
        aware.p_commit = 99.0

        for s in (subj, verb, obj, listen, intro, aware):
            s.map_inject = make_projection(N, 8, rng)

        sys_ = System([subj, verb, obj, listen, intro, aware], rng)

        token_vec = {}
        for sec_name, toks in VOCAB.items():
            sec = sys_.sections[sec_name]
            for tok in toks:
                v = random_unit_complex(N, rng)
                sec.mode_bank.append(v.copy())
                sec.mode_last_used.append(0)
                token_vec[(sec_name, tok)] = v
                listen.mode_bank.append(v.copy())
                listen.mode_last_used.append(0)

        intro_modes = ["i_quiet", "i_hear", "i_emit"]
        intro_vec = {}
        for name in intro_modes:
            v = random_unit_complex(N, rng)
            intro.mode_bank.append(v.copy())
            intro.mode_last_used.append(0)
            intro_vec[name] = v

        aware_modes = ["aware_quiet", "aware_listening", "aware_emitting"]
        aware_vec = {}
        for name in aware_modes:
            v = random_unit_complex(N, rng)
            aware.mode_bank.append(v.copy())
            aware.mode_last_used.append(0)
            aware_vec[name] = v

        return sys_, token_vec, intro_vec, intro_modes, aware_vec, aware_modes

    def converse(self, text, source="ui"):
        """Main conversation entry point. Returns structured response."""
        with self.lock:
            words = [w.lower().strip(".,!?;:'\"") for w in text.split() if w.strip()]
            known = [w for w in words if self._word_known(w)]
            unknown = [w for w in words if not self._word_known(w)]

            all_commits = []
            nmda_events = []
            rhythm_events = []

            if not known:
                return {
                    "response_tokens": [],
                    "rhythm_events": [],
                    "nmda_events": [],
                    "introspection": {"reported_state": "i_quiet",
                                      "tick": self.sys_.tick},
                    "awareness": {"reported_state": "aware_quiet",
                                  "tick": self.sys_.tick},
                    "mode_strengths": self._get_mode_strengths(),
                    "raw_emissions": [],
                    "unknown_words": unknown,
                    "honest_silence_reason": "no words in vocabulary",
                }

            # Phase 1: Listen — inject heard words into listen section
            for w in known:
                sec_name, tok_name = self._find_token(w)
                if sec_name and (sec_name, tok_name) in self.token_vec:
                    target = self.token_vec[(sec_name, tok_name)]
                    noisy = normalize(target + 0.10 * (
                        self.rng.standard_normal(N) +
                        1j * self.rng.standard_normal(N)))
                    ev = {"listen": noisy}
                    # Drive intro toward i_hear
                    ev["intro"] = normalize(
                        self.intro_vec["i_hear"] + 0.05 * (
                            self.rng.standard_normal(N) +
                            1j * self.rng.standard_normal(N)))
                    update_drive_tracker(self.drive_tracker, ev)
                    commits = self.sys_.tick_once(
                        ev, enable_self_evo=False,
                        coordinator_on=False, introspection_on=False)
                    all_commits.extend(commits)

                    # NMDA intro check
                    i_fired, i_mode = self.intro_gate.check_and_fire(self.sys_)
                    if i_fired and i_mode is not None and i_mode < len(self.intro_modes):
                        self.last_intro_state = self.intro_modes[i_mode]
                        self.intro_commit_tracker["age"] = 0
                    elif self.intro_commit_tracker["age"] is not None:
                        self.intro_commit_tracker["age"] += 1
                    nmda_events.append({
                        "tick": self.sys_.tick, "gate": "intro",
                        "fired": i_fired,
                        "reason": "fired" if i_fired else "context_blocked"
                    })

            # Run a few quiet ticks for intro reflection
            for _ in range(5):
                ev = {}
                ev["intro"] = normalize(
                    self.intro_vec.get(self.last_intro_state or "i_hear",
                                       self.intro_vec["i_hear"]) + 0.05 * (
                        self.rng.standard_normal(N) +
                        1j * self.rng.standard_normal(N)))
                update_drive_tracker(self.drive_tracker, ev)
                self.sys_.tick_once(ev, enable_self_evo=False,
                                    coordinator_on=False, introspection_on=False)
                i_fired, i_mode = self.intro_gate.check_and_fire(self.sys_)
                if i_fired and i_mode is not None and i_mode < len(self.intro_modes):
                    self.last_intro_state = self.intro_modes[i_mode]
                    self.intro_commit_tracker["age"] = 0

            # Phase 2: Emit — L5 rhythm-gated S->V->O emission
            emit_commits = []
            for w in known:
                sec_name, tok_name = self._find_token(w)
                if sec_name and (sec_name, tok_name) in self.token_vec:
                    target = self.token_vec[(sec_name, tok_name)]
                    ev = {}
                    ev[sec_name] = normalize(target + 0.10 * (
                        self.rng.standard_normal(N) +
                        1j * self.rng.standard_normal(N)))
                    # Drive intro toward i_emit
                    ev["intro"] = normalize(
                        self.intro_vec["i_emit"] + 0.05 * (
                            self.rng.standard_normal(N) +
                            1j * self.rng.standard_normal(N)))
                    update_drive_tracker(self.drive_tracker, ev)

            # Sustained cascade with phase gating
            for t in range(40):
                self.phase_gater(self.sys_.tick + 1, self.sys_)
                phase_tick = (self.sys_.tick + 1) % 24
                if phase_tick < 8:
                    cur_phase = "subject"
                elif phase_tick < 16:
                    cur_phase = "verb"
                else:
                    cur_phase = "object"
                self.last_rhythm_phase = cur_phase
                rhythm_events.append({"tick": self.sys_.tick + 1, "phase": cur_phase})

                # Re-inject evidence each tick with noise
                ev = {}
                for w in known:
                    sn, tn = self._find_token(w)
                    if sn and (sn, tn) in self.token_vec:
                        target = self.token_vec[(sn, tn)]
                        ev[sn] = normalize(target + 0.10 * (
                            self.rng.standard_normal(N) +
                            1j * self.rng.standard_normal(N)))

                update_drive_tracker(self.drive_tracker, ev)
                commits = self.sys_.tick_once(
                    ev, enable_self_evo=False,
                    coordinator_on=False, introspection_on=False)
                emit_commits.extend(commits)
                all_commits.extend(commits)

                # NMDA gate checks on S/V/O
                for sn in ("subject", "verb", "object"):
                    gate = self.svo_gates[sn]
                    fired, mode_id = gate.check_and_fire(self.sys_)
                    if fired:
                        nmda_events.append({
                            "tick": self.sys_.tick, "gate": sn,
                            "fired": True, "reason": "fired",
                            "mode_id": mode_id,
                        })

                # Intro gate during emit
                i_fired, i_mode = self.intro_gate.check_and_fire(self.sys_)
                if i_fired and i_mode is not None and i_mode < len(self.intro_modes):
                    self.last_intro_state = self.intro_modes[i_mode]
                    self.intro_commit_tracker["age"] = 0
                elif self.intro_commit_tracker["age"] is not None:
                    self.intro_commit_tracker["age"] += 1

            # Post-emit quiet for intro/aware reflection
            for _ in range(10):
                ev = {}
                ev["intro"] = normalize(
                    self.intro_vec.get(self.last_intro_state or "i_emit",
                                       self.intro_vec["i_emit"]) + 0.05 * (
                        self.rng.standard_normal(N) +
                        1j * self.rng.standard_normal(N)))
                # Drive aware
                aware_target_name = {
                    "i_quiet": "aware_quiet",
                    "i_hear": "aware_listening",
                    "i_emit": "aware_emitting",
                }.get(self.last_intro_state or "i_quiet", "aware_quiet")
                ev["aware"] = normalize(
                    self.aware_vec[aware_target_name] + 0.05 * (
                        self.rng.standard_normal(N) +
                        1j * self.rng.standard_normal(N)))
                update_drive_tracker(self.drive_tracker, ev)
                self.sys_.tick_once(ev, enable_self_evo=False,
                                    coordinator_on=False, introspection_on=False)
                # Intro check
                i_fired, i_mode = self.intro_gate.check_and_fire(self.sys_)
                if i_fired and i_mode is not None and i_mode < len(self.intro_modes):
                    self.last_intro_state = self.intro_modes[i_mode]
                    self.intro_commit_tracker["age"] = 0
                nmda_events.append({
                    "tick": self.sys_.tick, "gate": "intro",
                    "fired": i_fired,
                    "reason": "fired" if i_fired else "drive_low"
                })

                # Aware gate — fires when intro recently committed
                age = self.intro_commit_tracker.get("age")
                if age is not None and age <= 5:
                    # Manual aware commit via arc check
                    aware_sec = self.sys_.sections["aware"]
                    arcs = aware_sec.arcs()
                    if len(arcs) > 0 and float(arcs.max()) > 0.05:
                        top = int(arcs.argmax())
                        if top < len(self.aware_modes):
                            self.last_aware_state = self.aware_modes[top]
                            nmda_events.append({
                                "tick": self.sys_.tick, "gate": "aware",
                                "fired": True, "reason": "fired",
                            })

            # Build response tokens from emit commits
            response_tokens = self._extract_response_tokens(emit_commits)

            self.last_emissions = all_commits
            self.last_nmda_events = nmda_events
            self.tick_at_last_converse = self.sys_.tick

            return {
                "response_tokens": response_tokens,
                "rhythm_events": rhythm_events[-10:],
                "nmda_events": nmda_events,
                "introspection": {
                    "reported_state": self.last_intro_state or "i_quiet",
                    "tick": self.sys_.tick,
                },
                "awareness": {
                    "reported_state": self.last_aware_state or "aware_quiet",
                    "tick": self.sys_.tick,
                },
                "mode_strengths": self._get_mode_strengths(),
                "raw_emissions": [
                    {"section": c["section"], "mode_id": c["mode_id"],
                     "reason": c["reason"]}
                    for c in all_commits[-20:]
                ],
                "unknown_words": unknown,
            }

    def apply_feedback(self, correct, expected_tokens=None):
        """Supervised LTP from thumbs-up/down."""
        with self.lock:
            affected = []
            if correct:
                # Boost modes that fired in last emission
                for sn in ("subject", "verb", "object"):
                    sec = self.sys_.sections[sn]
                    if not hasattr(sec, "mode_strength"):
                        continue
                    arcs = sec.arcs()
                    if len(arcs) > 0:
                        top = int(arcs.argmax())
                        reinforce_mode(sec, top, boost=0.05, ceiling=2.5)
                        affected.append({"section": sn, "mode_id": top,
                                         "new_strength": sec.mode_strength[top]})
            else:
                # Anti-LTP: slight decay on top modes
                for sn in ("subject", "verb", "object"):
                    sec = self.sys_.sections[sn]
                    if not hasattr(sec, "mode_strength"):
                        continue
                    arcs = sec.arcs()
                    if len(arcs) > 0:
                        top = int(arcs.argmax())
                        sec.mode_strength[top] = max(
                            0.0, sec.mode_strength[top] - 0.02)
                        affected.append({"section": sn, "mode_id": top,
                                         "new_strength": sec.mode_strength[top]})
            return {"ltp_applied": correct, "affected_modes": affected}

    def get_state(self):
        """Snapshot for UI panel polling."""
        with self.lock:
            return {
                "tick": self.sys_.tick,
                "rhythm_phase": self.last_rhythm_phase,
                "introspection": self.last_intro_state or "i_quiet",
                "awareness": self.last_aware_state or "aware_quiet",
                "mode_strengths": self._get_mode_strengths(),
                "nmda_events": self.last_nmda_events[-10:],
                "n_commits_total": sum(
                    len(sec.krimelack) for sec in self.sys_.sections.values()),
            }

    def _word_known(self, word):
        for sn in ("subject", "verb", "object"):
            if (sn, word) in self.token_vec:
                return True
        return False

    def _find_token(self, word):
        """Find which section a word belongs to. Returns (section_name, word)."""
        for sn in ("subject", "verb", "object"):
            if (sn, word) in self.token_vec:
                return sn, word
        return None, None

    def _extract_response_tokens(self, commits):
        """Extract the best emitted token per section from commits."""
        tokens = []
        seen_sections = set()
        # Sort by section order S->V->O
        for target_sec in ("subject", "verb", "object"):
            sec = self.sys_.sections[target_sec]
            arcs = sec.arcs()
            if len(arcs) == 0:
                continue
            top = int(arcs.argmax())
            strength = float(arcs[top])
            # Find word label for this mode
            word = self._mode_to_word(target_sec, top)
            if word and target_sec not in seen_sections:
                ms = 0.0
                if hasattr(sec, "mode_strength") and top < len(sec.mode_strength):
                    ms = sec.mode_strength[top]
                tokens.append({
                    "section": target_sec,
                    "token": word,
                    "emit_tick": self.sys_.tick,
                    "mode_strength": round(ms, 3),
                    "arc": round(strength, 3),
                })
                seen_sections.add(target_sec)
        return tokens

    def _mode_to_word(self, section_name, mode_id):
        """Reverse lookup: mode_id in section -> word label."""
        toks = VOCAB.get(section_name, [])
        if mode_id < len(toks):
            return toks[mode_id]
        return None

    def _get_mode_strengths(self):
        """Mode strengths per section for UI."""
        out = {}
        for sn in ("subject", "verb", "object"):
            sec = self.sys_.sections[sn]
            strengths = {}
            toks = VOCAB.get(sn, [])
            if hasattr(sec, "mode_strength"):
                for i, tok in enumerate(toks):
                    if i < len(sec.mode_strength):
                        strengths[tok] = round(sec.mode_strength[i], 3)
            out[sn] = strengths
        return out

    def to_json(self):
        """Serialize session state for persistence."""
        state = {}
        for sn in ("subject", "verb", "object"):
            sec = self.sys_.sections[sn]
            if hasattr(sec, "mode_strength"):
                state[sn] = list(sec.mode_strength)
        state["intro_state"] = self.last_intro_state
        state["aware_state"] = self.last_aware_state
        state["tick"] = self.sys_.tick
        state["session_id"] = self.session_id
        return state

    def load_from_json(self, data):
        """Restore session state from persistence."""
        with self.lock:
            for sn in ("subject", "verb", "object"):
                if sn in data:
                    sec = self.sys_.sections[sn]
                    if hasattr(sec, "mode_strength"):
                        sec.mode_strength = list(data[sn])
            self.last_intro_state = data.get("intro_state")
            self.last_aware_state = data.get("aware_state")


# Session manager
_sessions = {}
_sessions_lock = threading.Lock()
STATE_DIR = "/app/state/v7_sessions"


def get_or_create_session(session_id):
    with _sessions_lock:
        if session_id in _sessions:
            return _sessions[session_id]
        session = V7Session(session_id)
        # Try loading from EFS
        path = os.path.join(STATE_DIR, f"{session_id}.json")
        if os.path.exists(path):
            try:
                with open(path) as f:
                    data = json.load(f)
                session.load_from_json(data)
            except Exception:
                pass
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
