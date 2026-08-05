"""
GL-EXP-AWARENESS-V2-WC-20260608-01

Simpler awareness: aware fires when intro recently committed (within last K ticks)
AND aware has drive toward an expected aware mode.

This is the cleanest "noticing one's own noticing": aware emits a token reporting
that introspection just happened, qualified by what intro reported.

Phases:
  quiet1     -> intro fires i_quiet -> aware fires aware_quiet
  post_listen -> intro fires i_hear  -> aware fires aware_listening
  post_emit   -> intro fires i_emit  -> aware fires aware_emitting
"""

import numpy as np
from collections import Counter
from assemblage import Section, System, N, normalize, random_unit_complex
from exp_l5_phase_gating import make_projection
from gl_nmda import (CoincidenceGate, context_no_recent_drive,
                       update_drive_tracker)
from exp_awareness_nmda import build_system


def context_intro_recently_committed(intro_commit_age_tracker, max_age=5):
    """Aware fires only when intro committed within the last max_age ticks."""
    def check(sys_):
        age = intro_commit_age_tracker["age"]
        return age is not None and age <= max_age
    return check


def run_awareness_v2(n_trials=20):
    rng_master = np.random.default_rng(42)
    vocab = {"subject": ["cow", "moon", "bears"],
             "verb":    ["jumped", "ran", "sleeps"],
             "object":  ["fence", "milk", "dish"]}

    # Phases that drive intro then read aware
    phases = [
        ("quiet1",      "quiet",   "i_quiet",  "aware_quiet"),
        ("listen",      "listen",  "i_hear",   None),    # intro gate blocked
        ("post_listen", "quiet",   "i_hear",   "aware_listening"),
        ("emit",        "emit",    "i_emit",   None),    # intro gate blocked
        ("post_emit",   "quiet",   "i_emit",   "aware_emitting"),
    ]
    # Only score the aware-expected phases
    score_phases = [p[0] for p in phases if p[3] is not None]
    phase_correct = {p: 0 for p in score_phases}
    phase_reports = {p: [] for p in score_phases}

    for trial in range(n_trials):
        seed = int(rng_master.integers(0, 10_000_000))
        rng = np.random.default_rng(seed)
        sys_, token_vec, intro_vec, intro_modes, aware_vec, aware_modes = \
            build_system(rng, vocab)
        spoken = {"subject": vocab["subject"][trial % 3],
                  "verb":    vocab["verb"][(trial // 3) % 3],
                  "object":  vocab["object"][(trial // 9) % 3]}

        drive_tracker = {}
        intro_commit_tracker = {"age": None}  # ticks since last intro commit

        intro_gate = CoincidenceGate(
            section_name="intro",
            context_fn=context_no_recent_drive(drive_tracker,
                                                 sections=("listen", "subject", "verb", "object"),
                                                 quiet_thresh=0.10),
            drive_thresh=0.05, ltp_boost=0.0,
        )

        aware_gate = CoincidenceGate(
            section_name="aware",
            context_fn=context_intro_recently_committed(intro_commit_tracker, max_age=5),
            drive_thresh=0.05, ltp_boost=0.0,
        )

        last_aware_per_phase = {}

        for phase_name, mode, intro_target_name, expected_aware in phases:
            last_aware = None
            intro_gate.mode_strength.clear()
            aware_gate.mode_strength.clear()

            # PUMP RESET: actively restore intro/aware psi to fresh baseline
            # at start of each phase (Na+/K+ pump primitive from Joe's spec).
            # This prevents historical mode bias from dominating new drive.
            for sn in ("intro", "aware"):
                sec = sys_.sections[sn]
                sec.psi = normalize(random_unit_complex(N, rng) * 0.3 +
                                     normalize(np.ones(N, dtype=complex)) * 0.7)
            intro_commit_tracker["age"] = None

            for t in range(20):
                ev = {}
                if mode == "listen":
                    tok_section = ["subject", "verb", "object"][t % 3]
                    tok_name = spoken[tok_section]
                    target = token_vec[(tok_section, tok_name)]
                    ev["listen"] = normalize(target + 0.10 * (rng.standard_normal(N) +
                                                                1j * rng.standard_normal(N)))
                elif mode == "emit":
                    for sn in ("subject", "verb", "object"):
                        target = token_vec[(sn, spoken[sn])]
                        ev[sn] = normalize(target + 0.10 * (rng.standard_normal(N) +
                                                              1j * rng.standard_normal(N)))

                intro_target = intro_vec[intro_target_name]
                ev["intro"] = normalize(intro_target + 0.05 * (rng.standard_normal(N) +
                                                                 1j * rng.standard_normal(N)))

                # Drive aware toward the expected aware mode if there is one
                # (always drive aware toward what we'd expect, gate decides whether to commit)
                if expected_aware is None:
                    # During listen/emit phases, drive aware toward what's coming next
                    # (reflects the post-phase aware state)
                    pass
                else:
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

                # Increment intro commit age (or reset to 0 if intro fires this tick)
                if intro_commit_tracker["age"] is not None:
                    intro_commit_tracker["age"] += 1

                # Intro gate check
                i_committed, i_mode = intro_gate.check_and_fire(sys_)
                if i_committed:
                    intro_commit_tracker["age"] = 0

                # Aware gate check (after intro update so age tracks correctly)
                a_committed, a_mode = aware_gate.check_and_fire(sys_)
                if a_committed and a_mode is not None and a_mode < len(aware_modes):
                    last_aware = aware_modes[a_mode]

            last_aware_per_phase[phase_name] = last_aware

        for phase_name in score_phases:
            actual = last_aware_per_phase.get(phase_name)
            expected = dict((p[0], p[3]) for p in phases)[phase_name]
            phase_reports[phase_name].append(actual)
            if actual == expected:
                phase_correct[phase_name] += 1

    return phase_correct, phase_reports


if __name__ == "__main__":
    print("Awareness V2: aware fires when intro recently committed + drive matches\n")
    correct, reports = run_awareness_v2(n_trials=20)
    for phase, n in correct.items():
        print(f"  {phase:14s}: {n}/20 = {n/20:.0%}  "
              f"reports = {Counter(reports[phase]).most_common()}")
    total = sum(correct.values())
    n_phases = len(correct) * 20
    print(f"\nOverall: {total}/{n_phases} = {total/n_phases:.0%}")
