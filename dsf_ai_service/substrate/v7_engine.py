"""
V7 DNA Recipe Engine — wires assemblage + NMDA gates + plasticity + rhythm
+ introspection + awareness into a single conversational substrate.

GL-CMD-DEPLOY-DNA-RECIPE-WC-20260608-01
GL-CMD-FIX-CONVERSATION-WC-20260608-02 (listen-prime + lookup_or_install)

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


# Seed vocabulary — minimal (matches wC's tested experiment).
# Everything else installs on-the-fly via lookup_or_install.
SEED_VOCAB = {
    "subject": ["cow", "moon", "bears"],
    "verb": ["jumped", "ran", "sleeps"],
    "object": ["fence", "milk", "dish"],
}

# Words to skip (don't install as modes — they don't carry content)
SKIP_WORDS = {"a", "an", "the", "is", "are", "am", "was", "were", "of", "in",
              "on", "at", "to", "from", "with", "for", "and", "or", "but", "it",
              "i", "you", "we", "they", "he", "she", "my", "your", "his", "her"}


class V7Session:
    """Per-session v7 substrate state with full DNA recipe wiring."""

    def __init__(self, session_id, rng_seed=None):
        self.session_id = session_id
        self.lock = threading.Lock()
        self.created_at = time.time()

        # Event log — write-ahead, canonical record
        from dsf_ai_service.substrate.event_log import EventLog
        self.event_log = EventLog(STATE_DIR, session_id)

        seed = rng_seed or hash(session_id) % (2**31)
        self.rng = np.random.default_rng(seed)

        # Per-session mutable vocab: slot -> [word_list]
        self.vocab = {k: list(v) for k, v in SEED_VOCAB.items()}

        # Build integrated 6-section system: S/V/O + listen + intro + aware
        # Respec Item 5: intro/aware live in the SAME System, commit via
        # post-emit evidence injection + NMDA gates
        self.sys_, self.token_vec, self.intro_vec, self.intro_modes, \
            self.aware_vec, self.aware_modes = self._build_system()

        # Install plasticity on S/V/O + intro + aware
        for sn in ("subject", "verb", "object", "intro", "aware"):
            install_plasticity(self.sys_.sections[sn], initial_strength=1.0)

        # NMDA gates (respec Item 5 — integrated, not meta-system)
        self.drive_tracker = {}
        self.intro_gate = CoincidenceGate(
            section_name="intro",
            context_fn=context_no_recent_drive(
                self.drive_tracker,
                sections=("subject", "verb", "object"),
                quiet_thresh=0.45),
            drive_thresh=0.05, ltp_boost=0.05,
        )
        self.aware_gate = CoincidenceGate(
            section_name="aware",
            context_fn=lambda sys_: (
                len(sys_.sections["intro"].krimelack) > 0 and
                (sys_.tick - sys_.sections["intro"].krimelack[-1]["tick"]) <= 5
            ),
            drive_thresh=0.05, ltp_boost=0.05,
        )

        # State tracking
        self.last_intro_state = None
        self.last_aware_state = None
        self.last_rhythm_phase = "subject"
        self.last_emissions = []
        self.last_nmda_events = []
        self.last_routing_log = []
        self.intro_commit_history = []  # last N intro commits
        self.aware_commit_history = []  # last N aware commits
        self.tick_at_last_converse = 0
        self._last_converse_time = time.time()

    def _build_system(self):
        """Build integrated 6-section system: S/V/O + listen + intro + aware.
        Respec Item 5: all sections in one System. Intro/aware receive NO
        evidence during S/V/O emit phase — they get evidence in the post-emit
        pass only. This avoids the interference that broke conversation pre-
        cognition-v1, while keeping everything in one System."""
        rng = self.rng
        subj = Section(name="subject", rng=rng, role="subject_like")
        verb = Section(name="verb", rng=rng, role="verb_like")
        obj = Section(name="object", rng=rng, role="object_like")
        listen = Section(name="listen", rng=rng, role="general")
        intro = Section(name="intro", rng=rng, role="intro")
        aware = Section(name="aware", rng=rng, role="intro")

        # Listen: passive buffer (zero Hamiltonian)
        listen.H_base = np.zeros((N, N), dtype=complex)
        listen.law_fields = {k: np.zeros((N, N), dtype=complex)
                             for k in ("symmetry", "consistency", "compactness")}

        # Intro/aware: zeroed Hamiltonian, normal commit thresholds
        # (commits happen through evidence injection in post-emit pass)
        for sec in (intro, aware):
            sec.H_base = np.zeros((N, N), dtype=complex)
            sec.law_fields = {k: np.zeros((N, N), dtype=complex)
                              for k in ("symmetry", "consistency", "compactness")}

        for s in (subj, verb, obj, listen, intro, aware):
            s.map_inject = make_projection(N, 8, rng)

        sys_ = System([subj, verb, obj, listen, intro, aware], rng)

        # Install S/V/O vocab
        token_vec = {}
        for sec_name, toks in self.vocab.items():
            sec = sys_.sections[sec_name]
            for tok in toks:
                v = random_unit_complex(N, rng)
                sec.mode_bank.append(v.copy())
                sec.mode_last_used.append(0)
                sec.mode_strength.append(1.0)
                token_vec[(sec_name, tok)] = v
                listen.mode_bank.append(v.copy())
                listen.mode_last_used.append(0)
                listen.mode_strength.append(1.0)

        # Install intro modes
        intro_modes = ["i_quiet", "i_hear", "i_emit"]
        intro_vec = {}
        for name in intro_modes:
            v = random_unit_complex(N, rng)
            intro.mode_bank.append(v.copy())
            intro.mode_last_used.append(0)
            intro.mode_strength.append(1.0)
            intro_vec[name] = v

        # Install aware modes
        aware_modes = ["aware_quiet", "aware_listening", "aware_emitting"]
        aware_vec = {}
        for name in aware_modes:
            v = random_unit_complex(N, rng)
            aware.mode_bank.append(v.copy())
            aware.mode_last_used.append(0)
            aware.mode_strength.append(1.0)
            aware_vec[name] = v

        # Snapshot initial mode_bank for homeostasis pull
        for sec in sys_.sections.values():
            sec.snapshot_initial_modes()

        return sys_, token_vec, intro_vec, intro_modes, aware_vec, aware_modes

    # ------------------------------------------------------------------
    # Fix 2: lookup_or_install — on-the-fly vocabulary
    # ------------------------------------------------------------------
    def lookup_or_install(self, word, position):
        """Return (word_vec, slot, was_new). Install new words by position."""
        word = word.lower().strip(".,?!;:'\"")
        if not word or word in SKIP_WORDS:
            return None, None, False

        # Already installed?
        for slot in ("subject", "verb", "object"):
            if word in self.vocab[slot]:
                idx = self.vocab[slot].index(word)
                sec = self.sys_.sections[slot]
                if idx < len(sec.mode_bank):
                    return sec.mode_bank[idx], slot, False

        # New word — install based on position
        slot = ["subject", "verb", "object"][min(position, 2)]
        sec = self.sys_.sections[slot]
        word_vec = random_unit_complex(N, self.rng)
        sec.mode_bank.append(word_vec.copy())
        sec.mode_last_used.append(self.sys_.tick)
        sec.mode_strength.append(1.0)
        # Also install in listen
        self.sys_.sections["listen"].mode_bank.append(word_vec.copy())
        self.sys_.sections["listen"].mode_last_used.append(self.sys_.tick)
        self.sys_.sections["listen"].mode_strength.append(1.0)
        self.vocab[slot].append(word)
        self.token_vec[(slot, word)] = word_vec
        sec.snapshot_initial_modes()
        self.sys_.sections["listen"].snapshot_initial_modes()
        # Event log: vocab install (write-ahead)
        self.event_log.write("vocab_install", slot=slot, word=word)
        return word_vec, slot, True

    # ------------------------------------------------------------------
    # Fix 1: Listen-prime conversation architecture
    # ------------------------------------------------------------------
    def converse(self, text, source="ui"):
        """Main conversation using wC's proven pipeline:
        Route → Listen-accumulate → Derive drives → Prime psi → Rhythm emit."""
        with self.lock:
            tokens = [t.lower().strip(".,?!;:'\"") for t in text.split() if t.strip()]
            if not tokens:
                return self._empty_response("empty input")

            # Per-turn reset: psi + goals only. Everything else persists.
            # Atlas, keyholes, krimelack, mode_bank all accumulate across turns.
            # Per-turn reset: psi + goals only. Use ORIGINAL session rng
            # (not re-seeded) to preserve H_base/mode_bank/map_inject correlation.
            for slot in ("subject", "verb", "object", "listen", "intro", "aware"):
                sec = self.sys_.sections[slot]
                sec.psi = normalize(
                    random_unit_complex(N, self.rng) * 0.3 +
                    normalize(np.ones(N, dtype=complex)) * 0.7)
                sec.standing_goals = []
                sec.goals = []
            self.drive_tracker.clear()

            routing_log = []
            nmda_events = []
            rhythm_events = []

            # PHASE 1: Route words, build heard_sentence dict
            heard = {}  # slot -> word
            any_routed = False
            for pos, word in enumerate(tokens):
                word_vec, slot, was_new = self.lookup_or_install(word, position=pos)
                if word_vec is None:
                    routing_log.append({"word": word, "routed_to": None,
                                        "reason": "skipped"})
                    continue
                routing_log.append({"word": word, "routed_to": slot,
                                    "newly_installed": was_new})
                heard[slot] = word
                any_routed = True

            if not any_routed:
                return self._empty_response("no content words in vocabulary")

            # PHASE 2: Listen-accumulate (matches wC's speak_and_listen)
            # Block ALL blending during listen — no mode_bank warping
            for sn in ("subject", "verb", "object", "listen", "intro", "aware"):
                self.sys_.sections[sn]._emit_phase = True
            accumulated = {}
            for slot, word in heard.items():
                vec_key = (slot, word)
                if vec_key not in self.token_vec:
                    continue
                target = self.token_vec[vec_key]
                acc = np.zeros(N, dtype=complex)
                for _ in range(15):
                    noisy = normalize(target + 0.10 * (
                        self.rng.standard_normal(N) +
                        1j * self.rng.standard_normal(N)))
                    acc = acc + noisy
                    ev = {"listen": noisy}
                    self.sys_.tick_once(ev, enable_self_evo=True,
                                        coordinator_on=False, introspection_on=False,
                                        allow_rewiring=False)
                accumulated[slot] = normalize(acc)

            # Introspection: heard phase
            self.last_intro_state = "i_hear"
            self.intro_commit_history.append({
                "state": "i_hear", "tick": self.sys_.tick})
            self.intro_commit_history = self.intro_commit_history[-10:]

            # Clear listen-phase blend gating
            for sn in ("subject", "verb", "object", "intro", "aware"):
                self.sys_.sections[sn]._emit_phase = False

            # PHASE 3: Derive drives from listen accumulators
            # (matches wC's guala_emit drive derivation)
            drives = {}
            for slot in ("subject", "verb", "object"):
                snap = accumulated.get(slot)
                sec = self.sys_.sections[slot]
                if snap is None or np.linalg.norm(snap) == 0:
                    drives[slot] = random_unit_complex(N, self.rng) * 0.1
                    continue
                weights = []
                for mode_id, mode_vec in enumerate(sec.mode_bank):
                    directional = float(np.abs(np.vdot(mode_vec, snap)) ** 2)
                    sal = sec.mode_strength[mode_id] if mode_id < len(sec.mode_strength) else 1.0
                    w = directional * sal
                    weights.append((mode_id, w, mode_vec))
                weights.sort(key=lambda x: -x[1])
                bias = np.zeros(N, dtype=complex)
                for mode_id, w, v in weights[:2]:
                    bias = bias + w * v
                drives[slot] = normalize(bias) if np.linalg.norm(bias) > 0 \
                    else random_unit_complex(N, self.rng)

            # Prime S/V/O psi to drives
            for slot in ("subject", "verb", "object"):
                self.sys_.sections[slot].psi = drives[slot].copy()

            # PHASE 4: Commit-driven rhythm emission
            # Set emit_phase flag — blocks mode_bank blending during emit
            for sec in self.sys_.sections.values():
                sec._emit_phase = True

            emit_commits = []
            svo_cycle = ["subject", "verb", "object"]
            cycle_idx = 0
            wait_counter = 0
            max_wait = 20
            svo_strength = 0.45
            emitted_sections = set()
            emitted_words = {}

            for t in range(120):
                # Decay plasticity per tick
                for sn in ("subject", "verb", "object"):
                    decay_plasticity(self.sys_.sections[sn], decay=0.998)


                current = svo_cycle[cycle_idx % 3]
                self.last_rhythm_phase = current
                rhythm_events.append({"tick": self.sys_.tick + 1, "phase": current})

                # Excite current, inhibit others
                for sn in ("subject", "verb", "object"):
                    sec = self.sys_.sections[sn]
                    sec.excitation_expires_at = self.sys_.tick + 2
                    if sn == current:
                        sec.excitation_strength = svo_strength
                    else:
                        sec.excitation_strength = -svo_strength

                # Evidence: same drive vector re-noised every tick
                ev = {}
                for slot in ("subject", "verb", "object"):
                    target = drives[slot]
                    ev[slot] = normalize(target + 0.10 * (
                        self.rng.standard_normal(N) +
                        1j * self.rng.standard_normal(N)))

                commits = self.sys_.tick_once(
                    ev, enable_self_evo=True,
                    coordinator_on=False, introspection_on=False,
                    allow_rewiring=False)
                emit_commits.extend(commits)

                # Advance cycle on commit
                advanced = False
                for c in commits:
                    if c["section"] == current and current not in emitted_sections:
                        emitted_sections.add(current)
                        # Read emitted word
                        sec = self.sys_.sections[current]
                        arcs = sec.arcs()
                        top = int(arcs.argmax())
                        word = self._mode_to_word(current, top)
                        emitted_words[current] = word
                        cycle_idx += 1
                        wait_counter = 0
                        advanced = True

                if not advanced:
                    wait_counter += 1
                    if wait_counter >= max_wait:
                        cycle_idx += 1
                        wait_counter = 0

                if len(emitted_sections) >= 3:
                    break

            # Clear emit_phase flag
            for sec in self.sys_.sections.values():
                sec._emit_phase = False

            # POST-EMIT EVIDENCE PASS: intro + aware in integrated System
            # (Respec Item 5 — single System, post-emit evidence injection)
            # SVO emit is done. Now inject evidence into intro/aware sections
            # and let NMDA gates decide whether to commit.

            # Update drive tracker from emit (marks SVO as recently active)
            for c in emit_commits:
                update_drive_tracker(self.drive_tracker,
                                     {c["section"]: np.ones(N, dtype=complex) * 0.5})

            # Intro pass: drive intro toward i_emit (SVO just committed)
            intro_target = self.intro_vec.get("i_emit")
            if intro_target is not None:
                for _ in range(10):
                    noisy = normalize(intro_target + 0.05 * (
                        self.rng.standard_normal(N) +
                        1j * self.rng.standard_normal(N)))
                    # Only inject into intro — S/V/O/listen get nothing
                    ev = {"intro": noisy}
                    update_drive_tracker(self.drive_tracker, ev)
                    self.sys_.tick_once(ev, enable_self_evo=True,
                                        coordinator_on=False,
                                        introspection_on=False,
                                        allow_rewiring=False)
                    # Cap intro mode bank to prevent novel_mode spawning
                    intro_sec = self.sys_.sections["intro"]
                    while len(intro_sec.mode_bank) > len(self.intro_modes):
                        intro_sec.mode_bank.pop()
                        intro_sec.mode_last_used.pop()
                    # NMDA gate check — C4: log every evaluation
                    i_fired, i_mode, i_eval = self.intro_gate.check_and_fire(self.sys_)
                    i_eval["tick"] = self.sys_.tick
                    i_eval["fired"] = i_fired
                    i_eval["drive_tracker"] = {k: round(v, 4) for k, v in self.drive_tracker.items()}
                    nmda_events.append(i_eval)
                    if i_fired and i_mode is not None and i_mode < len(self.intro_modes):
                        self.last_intro_state = self.intro_modes[i_mode]
                        self.intro_commit_history.append({
                            "state": self.last_intro_state,
                            "tick": self.sys_.tick})
                        self.intro_commit_history = self.intro_commit_history[-10:]

            # Aware pass: drive toward matching aware mode
            aware_target_name = {
                "i_quiet": "aware_quiet",
                "i_hear": "aware_listening",
                "i_emit": "aware_emitting",
            }.get(self.last_intro_state or "i_emit", "aware_emitting")
            aware_target = self.aware_vec.get(aware_target_name)
            if aware_target is not None:
                for _ in range(10):
                    noisy = normalize(aware_target + 0.05 * (
                        self.rng.standard_normal(N) +
                        1j * self.rng.standard_normal(N)))
                    ev = {"aware": noisy}
                    self.sys_.tick_once(ev, enable_self_evo=True,
                                        coordinator_on=False,
                                        introspection_on=False,
                                        allow_rewiring=False)
                    aware_sec = self.sys_.sections["aware"]
                    while len(aware_sec.mode_bank) > len(self.aware_modes):
                        aware_sec.mode_bank.pop()
                        aware_sec.mode_last_used.pop()
                    a_fired, a_mode, a_eval = self.aware_gate.check_and_fire(self.sys_)
                    a_eval["tick"] = self.sys_.tick
                    a_eval["fired"] = a_fired
                    nmda_events.append(a_eval)
                    if a_fired and a_mode is not None and a_mode < len(self.aware_modes):
                        self.last_aware_state = self.aware_modes[a_mode]
                        self.aware_commit_history.append({
                            "state": self.last_aware_state,
                            "tick": self.sys_.tick})
                        self.aware_commit_history = self.aware_commit_history[-10:]

            # Build response tokens from emitted_words
            response_tokens = []
            for slot in ("subject", "verb", "object"):
                word = emitted_words.get(slot)
                if word:
                    sec = self.sys_.sections[slot]
                    arcs = sec.arcs()
                    top = int(arcs.argmax())
                    ms = 0.0
                    if hasattr(sec, "mode_strength") and top < len(sec.mode_strength):
                        ms = sec.mode_strength[top]
                    response_tokens.append({
                        "section": slot, "token": word,
                        "emit_tick": self.sys_.tick,
                        "mode_strength": round(ms, 3),
                        "arc": round(float(arcs[top]), 3),
                    })

            self.last_emissions = emit_commits
            self.last_nmda_events = nmda_events
            self.last_routing_log = routing_log
            self.tick_at_last_converse = self.sys_.tick
            self._last_converse_time = time.time()

            # Event log: full conversation turn
            emitted = [t.get("token", "") for t in response_tokens]
            self.event_log.write("converse",
                                 text=" ".join(tokens),
                                 emitted=emitted,
                                 tick=self.sys_.tick)

            return {
                "response_tokens": response_tokens,
                "routing_log": routing_log,
                "rhythm_events": rhythm_events[-10:],
                "nmda_events": nmda_events[-20:],
                "introspection": {
                    "reported_state": self.last_intro_state or "i_quiet",
                    "tick": self.sys_.tick,
                    "recent_commits": self.intro_commit_history[-3:],
                },
                "awareness": {
                    "reported_state": self.last_aware_state or "aware_quiet",
                    "tick": self.sys_.tick,
                    "recent_commits": self.aware_commit_history[-3:],
                },
                "mode_strengths": self._get_mode_strengths(),
                "raw_emissions": [
                    {"section": c["section"], "mode_id": c["mode_id"],
                     "reason": c["reason"]}
                    for c in emit_commits[-20:]
                ],
                "unknown_words": [r["word"] for r in routing_log
                                  if r.get("routed_to") is None],
            }

    def _empty_response(self, reason):
        return {
            "response_tokens": [],
            "routing_log": [],
            "rhythm_events": [],
            "nmda_events": [],
            "introspection": {"reported_state": "i_quiet",
                              "tick": self.sys_.tick, "recent_commits": []},
            "awareness": {"reported_state": "aware_quiet",
                          "tick": self.sys_.tick, "recent_commits": []},
            "mode_strengths": self._get_mode_strengths(),
            "raw_emissions": [],
            "unknown_words": [],
            "honest_silence_reason": reason,
        }

    def quiet_tick(self, n_ticks=1):
        """Quiet ticks — substrate's Default Mode (spec Item 3.3).
        Replay drives commits, which strengthen mode_bank via existing
        blending plasticity. This is consolidation. This is mental time travel.
        C4: also evaluate intro gate — introspection should fire during quiet."""
        with self.lock:
            results = []
            for _ in range(n_ticks):
                result = self.sys_.replay_tick(rng=self.rng)
                # C4: evaluate intro gate during quiet ticks (Change 2)
                # Drive tracker decays naturally between converse calls;
                # the quiet window the gate needs lives HERE.
                update_drive_tracker(self.drive_tracker, {})  # decay only
                i_fired, i_mode, i_eval = self.intro_gate.check_and_fire(self.sys_)
                i_eval["tick"] = self.sys_.tick
                i_eval["fired"] = i_fired
                i_eval["source"] = "quiet_tick"
                if not hasattr(self, '_quiet_nmda_events'):
                    self._quiet_nmda_events = []
                self._quiet_nmda_events.append(i_eval)
                self._quiet_nmda_events = self._quiet_nmda_events[-20:]
                if i_fired and i_mode is not None and i_mode < len(self.intro_modes):
                    self.last_intro_state = self.intro_modes[i_mode]
                    self.intro_commit_history.append({
                        "state": self.last_intro_state,
                        "tick": self.sys_.tick})
                    self.intro_commit_history = self.intro_commit_history[-10:]
                    # Log sparingly — only on state transitions, not every tick
                    if len(self.intro_commit_history) <= 1 or \
                       self.intro_commit_history[-1]["state"] != self.intro_commit_history[-2].get("state"):
                        print(f"[v7-intro] FIRED during quiet: mode={i_mode} "
                              f"state={self.last_intro_state} tick={self.sys_.tick}")
                results.append(result)
            # Store for state endpoint reporting
            total_r = sum(len(r["replayed"]) for r in results)
            total_c = sum(len(r["commits"]) for r in results)
            self._last_replay_result = {
                "replayed": total_r, "commits": total_c, "ticks": len(results)
            }
            if total_r > 0:
                self.event_log.write("quiet", n_ticks=len(results),
                                     replayed=total_r, commits=total_c)
            return results

    def apply_feedback(self, correct, expected_tokens=None):
        """Supervised LTP from thumbs-up/down."""
        with self.lock:
            affected = []
            if correct:
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
            # Event log: feedback
            self.event_log.write("feedback", correct=correct,
                                 affected=[{"section": a["section"],
                                            "mode_id": a["mode_id"],
                                            "strength": a["new_strength"]}
                                           for a in affected])
            return {"ltp_applied": correct, "affected_modes": affected}

    def get_state(self):
        """Snapshot for UI panel polling."""
        with self.lock:
            return {
                "tick": self.sys_.tick,
                "rhythm_phase": self.last_rhythm_phase,
                "introspection": self.last_intro_state or "i_quiet",
                "intro_recent": self.intro_commit_history[-3:],
                "awareness": self.last_aware_state or "aware_quiet",
                "aware_recent": self.aware_commit_history[-3:],
                "mode_strengths": self._get_mode_strengths(),
                "nmda_events": self.last_nmda_events[-10:],
                "routing_log": self.last_routing_log,
                "n_commits_total": sum(
                    len(sec.krimelack) for sec in self.sys_.sections.values()),
                "intro_krimelack_count": len(self.sys_.sections["intro"].krimelack),
                "aware_krimelack_count": len(self.sys_.sections["aware"].krimelack),
                "intro_krimelack_recent": [
                    {"tick": k["tick"], "mode_id": k["mode_id"],
                     "salience": round(k.get("salience", 0), 3)}
                    for k in self.sys_.sections["intro"].krimelack[-5:]
                ],
                "aware_krimelack_recent": [
                    {"tick": k["tick"], "mode_id": k["mode_id"],
                     "salience": round(k.get("salience", 0), 3)}
                    for k in self.sys_.sections["aware"].krimelack[-5:]
                ],
                "last_replay": getattr(self, "_last_replay_result", None),
                "bridge_active": hasattr(self, "_bridge") and self._bridge is not None,
            }

    def _extract_response_tokens(self, commits):
        """Extract the best emitted token per section from commits."""
        tokens = []
        seen_sections = set()
        for target_sec in ("subject", "verb", "object"):
            sec = self.sys_.sections[target_sec]
            arcs = sec.arcs()
            if len(arcs) == 0:
                continue
            top = int(arcs.argmax())
            strength = float(arcs[top])
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
        toks = self.vocab.get(section_name, [])
        if mode_id < len(toks):
            return toks[mode_id]
        return None

    def _get_mode_strengths(self):
        """Mode strengths per section for UI."""
        out = {}
        for sn in ("subject", "verb", "object"):
            sec = self.sys_.sections[sn]
            strengths = {}
            toks = self.vocab.get(sn, [])
            if hasattr(sec, "mode_strength"):
                for i, tok in enumerate(toks):
                    if i < len(sec.mode_strength):
                        strengths[tok] = round(sec.mode_strength[i], 3)
            out[sn] = strengths
        return out

    def _serialize_section(self, sec):
        """Serialize a Section's live substrate state."""
        return {
            "name": sec.name,
            "psi_re": sec.psi.real.tolist(),
            "psi_im": sec.psi.imag.tolist(),
            "mode_bank_re": [m.real.tolist() for m in sec.mode_bank],
            "mode_bank_im": [m.imag.tolist() for m in sec.mode_bank],
            "mode_last_used": list(sec.mode_last_used),
            "mode_strength": list(getattr(sec, "mode_strength", [])),
            "gamma": dict(sec.gamma),
            "det_commit": sec.det_commit,
            "p_commit": sec.p_commit,
            "tick": getattr(sec, "tick", 0),
            "krimelack_count": len(sec.krimelack),
            # Persist last 200 krimelack entries (keep size bounded)
            "krimelack": [
                {"chi": int(k["chi"]), "tick": int(k["tick"]),
                 "mode_id": int(k["mode_id"]), "reason": k.get("reason", ""),
                 "salience": float(k.get("salience", 0.0))}
                for k in sec.krimelack[-200:]
            ],
        }

    def _restore_section(self, sec, data):
        """Restore a Section from serialized state."""
        sec.psi = np.array(data["psi_re"]) + 1j * np.array(data["psi_im"])
        sec.mode_bank = [
            np.array(r) + 1j * np.array(i)
            for r, i in zip(data["mode_bank_re"], data["mode_bank_im"])
        ]
        sec.mode_last_used = list(data.get("mode_last_used",
                                            [0] * len(sec.mode_bank)))
        if "mode_strength" in data:
            sec.mode_strength = list(data["mode_strength"])
        if "gamma" in data:
            sec.gamma = dict(data["gamma"])

    def compact(self):
        """Compaction: snapshot current state + truncate events log.
        Snapshot becomes the checkpoint; events after this seq are kept."""
        data = self.to_json()
        save_session(self)
        # Truncate events log to events after this snapshot
        self.event_log.truncate_before(self.event_log.count)
        return data

    def to_json(self):
        """Full substrate state serialization (spec Item 2)."""
        state = {
            "schema_version": 2,
            "session_id": self.session_id,
            "event_seq": self.event_log.count,  # for replay-after-snapshot
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
                for kh in self.sys_.keyholes
            ],
        }
        for sn in ("subject", "verb", "object", "listen", "intro", "aware"):
            state["sections"][sn] = self._serialize_section(
                self.sys_.sections[sn])
        return state

    def load_from_json(self, data):
        """Restore full substrate state."""
        with self.lock:
            sv = data.get("schema_version", 1)
            if sv < 2:
                # Legacy: just mode_strength + vocab
                for sn in ("subject", "verb", "object"):
                    if sn in data:
                        sec = self.sys_.sections[sn]
                        if hasattr(sec, "mode_strength"):
                            sec.mode_strength = list(data[sn])
                self.last_intro_state = data.get("intro_state")
                self.last_aware_state = data.get("aware_state")
                if "vocab" in data:
                    self.vocab = {k: list(v) for k, v in data["vocab"].items()}
                return

            # Schema v2: full state
            if "vocab" in data:
                self.vocab = {k: list(v) for k, v in data["vocab"].items()}
            self.last_intro_state = data.get("intro_state")
            self.last_aware_state = data.get("aware_state")
            for sn, sec_data in data.get("sections", {}).items():
                if sn in self.sys_.sections:
                    self._restore_section(self.sys_.sections[sn], sec_data)
            # Legacy: meta_sections → main system sections
            for sn, sec_data in data.get("meta_sections", {}).items():
                if sn in self.sys_.sections:
                    self._restore_section(self.sys_.sections[sn], sec_data)


# Session manager
_sessions = {}
_sessions_lock = threading.Lock()
STATE_DIR = "/app/state/v7_sessions"


def get_or_create_session(session_id):
    with _sessions_lock:
        if session_id in _sessions:
            return _sessions[session_id]
        session = V7Session(session_id)
        # Step 1: Load latest snapshot (compaction checkpoint)
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
        # Step 2: Replay events since snapshot
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
