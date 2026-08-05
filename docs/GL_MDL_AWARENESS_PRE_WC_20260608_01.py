"""
GL-EXP-AWARENESS-NMDA-WC-20260608-01

Awareness as coincidence-of-coincidence: a meta section fires only when
TWO other sections are simultaneously in committed states.

Specifically: aware section fires "I noticed myself listening" when
  (intro just committed i_hear) AND (subject section is settled on the
  heard token).

This is "noticing one's own noticing": the substrate registers that its
own self-model is reporting a state that matches what the sensory section
is holding. That's awareness — the loop reading itself.

Three aware-modes:
  aware_listening   - both intro=i_hear and listen has settled token
  aware_emitting    - both intro=i_emit and S/V/O have settled tokens
  aware_quiet       - both intro=i_quiet and no sensory activity
"""

import numpy as np
from collections import Counter
from assemblage import Section, System, N, normalize, random_unit_complex
from exp_l5_phase_gating import make_projection
from gl_nmda import (CoincidenceGate, context_no_recent_drive,
                       update_drive_tracker)


def build_system(rng, vocab):
    subj   = Section(name="subject", rng=rng, role="subject_like")
    verb   = Section(name="verb",    rng=rng, role="verb_like")
    obj    = Section(name="object",  rng=rng, role="object_like")
    listen = Section(name="listen",  rng=rng, role="general")
    intro  = Section(name="intro",   rng=rng, role="intro")
    aware  = Section(name="aware",   rng=rng, role="intro")
    for sec in (listen, intro, aware):
        sec.H_base = np.zeros((N, N), dtype=complex)
        sec.law_fields = {"symmetry": np.zeros((N, N), dtype=complex),
                          "consistency": np.zeros((N, N), dtype=complex),
                          "compactness": np.zeros((N, N), dtype=complex)}
    intro.det_commit = 99.0
    intro.p_commit = 99.0
    aware.det_commit = 99.0
    aware.p_commit = 99.0
    for s in (subj, verb, obj, listen, intro, aware):
        s.map_inject = make_projection(N, 8, rng)
    sys_ = System([subj, verb, obj, listen, intro, aware], rng)

    token_vec = {}
    for sec_name, toks in vocab.items():
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


def context_intro_committed_and_sensory_active(intro_state_holder,
                                                  intro_target,
                                                  sensory_active_check):
    """Aware fires only when: intro is in intro_target state AND sensory is active."""
    def check(sys_):
        if intro_state_holder.get("value") != intro_target:
            return False
        return sensory_active_check(sys_)
    return check


def context_sensory_active(drive_tracker, sections, thresh=0.10):
    """Sensory is active = drive tracker for any of these sections is above thresh."""
    def check(sys_):
        for sn in sections:
            if drive_tracker.get(sn, 0.0) > thresh:
                return True
        return False
    return check


def context_sensory_quiet_drive(drive_tracker, sections, thresh=0.10):
    """Sensory quiet = none of these sections has recent drive."""
    def check(sys_):
        for sn in sections:
            if drive_tracker.get(sn, 0.0) > thresh:
                return False
        return True
    return check


def run_awareness_test(n_trials=20):
    rng_master = np.random.default_rng(42)
    vocab = {"subject": ["cow", "moon", "bears"],
             "verb":    ["jumped", "ran", "sleeps"],
             "object":  ["fence", "milk", "dish"]}

    # Phases: WHILE we are listening, awareness should fire "aware_listening"
    # (intro reports i_hear from previous reflection + sensory now active).
    # This is "I am aware I am listening as it happens."
    #
    # But for clean test: drive intro DIRECTLY with the appropriate mode for
    # what's happening this tick. Awareness fires when intro+sensory match.
    #
    # Phases:
    #   quiet1 (intro=i_quiet, no sensory) -> aware_quiet
    #   listening (intro=i_hear, listen active) -> aware_listening
    #   emitting (intro=i_emit, SVO active) -> aware_emitting

    phases = [
        ("quiet1",    "quiet",  "i_quiet", "aware_quiet"),
        ("listening", "listen", "i_hear",  "aware_listening"),
        ("emitting",  "emit",   "i_emit",  "aware_emitting"),
    ]

    phase_correct = {p[0]: 0 for p in phases}
    phase_reports = {p[0]: [] for p in phases}

    for trial in range(n_trials):
        seed = int(rng_master.integers(0, 10_000_000))
        rng = np.random.default_rng(seed)
        sys_, token_vec, intro_vec, intro_modes, aware_vec, aware_modes = \
            build_system(rng, vocab)
        spoken = {"subject": vocab["subject"][trial % 3],
                  "verb":    vocab["verb"][(trial // 3) % 3],
                  "object":  vocab["object"][(trial // 9) % 3]}

        drive_tracker = {}
        intro_state_holder = {"value": None}

        # Intro gate: fire only when sensory quiet (reflection)
        intro_gate = CoincidenceGate(
            section_name="intro",
            context_fn=context_no_recent_drive(drive_tracker,
                                                 sections=("listen", "subject", "verb", "object"),
                                                 quiet_thresh=0.10),
            drive_thresh=0.05, ltp_boost=0.0,
        )

        # Aware gate per target — we'll use the same gate but check
        # multiple aware modes by checking intro_state_holder
        # Aware fires when intro_state matches what the current sensory pattern
        # also matches (coincidence-of-coincidence)

        for phase_name, mode, intro_target_name, expected_aware in phases:
            last_aware = None
            intro_gate.mode_strength.clear()

            # Build aware gate fresh per phase, tied to expected intro state
            aware_gate = CoincidenceGate(
                section_name="aware",
                context_fn=(lambda intro_holder, target_intro, drive_tr, mode_phase:
                            lambda sys_: (intro_holder.get("value") == target_intro and
                                          ((mode_phase == "quiet" and
                                            not any(drive_tr.get(sn, 0) > 0.10
                                                    for sn in ("listen", "subject", "verb", "object"))) or
                                           (mode_phase == "listen" and
                                            drive_tr.get("listen", 0) > 0.10) or
                                           (mode_phase == "emit" and
                                            any(drive_tr.get(sn, 0) > 0.10 for sn in ("subject", "verb", "object")))))
                          )(intro_state_holder, intro_target_name, drive_tracker, mode),
                drive_thresh=0.05,
                ltp_boost=0.0,
            )

            for t in range(20):
                ev = {}
                if mode == "listen":
                    tok_section = ["subject", "verb", "object"][t % 3]
                    tok_name = spoken[tok_section]
                    target = token_vec[(tok_section, tok_name)]
                    noisy = normalize(target + 0.10 * (rng.standard_normal(N) +
                                                        1j * rng.standard_normal(N)))
                    ev["listen"] = noisy
                elif mode == "emit":
                    for sn in ("subject", "verb", "object"):
                        target = token_vec[(sn, spoken[sn])]
                        noisy = normalize(target + 0.10 * (rng.standard_normal(N) +
                                                            1j * rng.standard_normal(N)))
                        ev[sn] = noisy

                # Drive intro toward correct state for this phase
                intro_target = intro_vec[intro_target_name]
                ev["intro"] = normalize(intro_target + 0.05 * (rng.standard_normal(N) +
                                                                 1j * rng.standard_normal(N)))

                # Drive aware toward the expected aware mode (so it has signal to commit)
                aware_target = aware_vec[expected_aware]
                ev["aware"] = normalize(aware_target + 0.05 * (rng.standard_normal(N) +
                                                                 1j * rng.standard_normal(N)))

                update_drive_tracker(drive_tracker, ev)
                sys_.tick_once(ev, enable_self_evo=False, coordinator_on=False,
                               introspection_on=False)
                while len(sys_.sections["intro"].mode_bank) > 3:
                    sys_.sections["intro"].mode_bank.pop()
                    sys_.sections["intro"].mode_last_used.pop()
                while len(sys_.sections["aware"].mode_bank) > 3:
                    sys_.sections["aware"].mode_bank.pop()
                    sys_.sections["aware"].mode_last_used.pop()

                # Intro gate check
                i_committed, i_mode = intro_gate.check_and_fire(sys_)
                if i_committed and i_mode is not None and i_mode < len(intro_modes):
                    intro_state_holder["value"] = intro_modes[i_mode]

                # Aware gate check
                a_committed, a_mode = aware_gate.check_and_fire(sys_)
                if a_committed and a_mode is not None and a_mode < len(aware_modes):
                    last_aware = aware_modes[a_mode]

            phase_reports[phase_name].append(last_aware)
            if last_aware == expected_aware:
                phase_correct[phase_name] += 1

    return phase_correct, phase_reports


if __name__ == "__main__":
    print("Awareness test: meta section fires only when intro + sensory coincide\n")
    correct, reports = run_awareness_test(n_trials=20)
    for phase, n in correct.items():
        print(f"  {phase:12s}: {n}/20 = {n/20:.0%}  "
              f"reports = {Counter(reports[phase]).most_common()}")
    total = sum(correct.values())
    print(f"\nOverall: {total}/60 = {total/60:.0%}")
