"""
GL-EXP-NMDA-GATE-CLEAN-WC-20260608-01

Clean test of the NMDA coincidence gate primitive.
Drive intro with known correct target per phase. Test:
  - Gate FIRES during quiet phases (context: sensory quiet) when drive matches target
  - Gate BLOCKS during active phases (context: sensory loud) even with strong drive

Score: was the right thing committed in each phase?
  quiet1: gate fires, commits i_quiet
  listen: gate blocks (sensory loud) — no commit expected
  post_listen: gate fires, commits i_hear (driven by i_hear; sensory now quiet)
  emit: gate blocks — no commit expected  
  post_emit: gate fires, commits i_emit
"""

import numpy as np
from collections import Counter
from dsf_ai_service.substrate.assemblage import Section, System, N, normalize, random_unit_complex
from dsf_ai_service.substrate.dna_recipe.phase_gating import make_projection
from dsf_ai_service.substrate.gl_nmda import (CoincidenceGate, context_no_recent_drive,
                       update_drive_tracker)


def build_system(rng, vocab):
    subj   = Section(name="subject", rng=rng, role="subject_like")
    verb   = Section(name="verb",    rng=rng, role="verb_like")
    obj    = Section(name="object",  rng=rng, role="object_like")
    listen = Section(name="listen",  rng=rng, role="general")
    intro  = Section(name="intro",   rng=rng, role="intro")
    for sec in (listen, intro):
        sec.H_base = np.zeros((N, N), dtype=complex)
        sec.law_fields = {"symmetry": np.zeros((N, N), dtype=complex),
                          "consistency": np.zeros((N, N), dtype=complex),
                          "compactness": np.zeros((N, N), dtype=complex)}
    intro.det_commit = 99.0
    intro.p_commit = 99.0
    for s in (subj, verb, obj, listen, intro):
        s.map_inject = make_projection(N, 8, rng)
    sys_ = System([subj, verb, obj, listen, intro], rng)

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

    return sys_, token_vec, intro_vec, intro_modes


def run_test(n_trials=20):
    rng_master = np.random.default_rng(42)
    vocab = {"subject": ["cow", "moon", "bears"],
             "verb":    ["jumped", "ran", "sleeps"],
             "object":  ["fence", "milk", "dish"]}

    # Phases with (mode, intro_target, expect_gate_fire, expected_commit)
    phases = [
        ("quiet1",      "quiet",  "i_quiet", True,  "i_quiet"),
        ("listen",      "listen", "i_hear",  False, None),
        ("post_listen", "quiet",  "i_hear",  True,  "i_hear"),
        ("emit",        "emit",   "i_emit",  False, None),
        ("post_emit",   "quiet",  "i_emit",  True,  "i_emit"),
    ]

    results = {p[0]: {"correct": 0, "actual": []} for p in phases}

    for trial in range(n_trials):
        seed = int(rng_master.integers(0, 10_000_000))
        rng = np.random.default_rng(seed)
        sys_, token_vec, intro_vec, intro_modes = build_system(rng, vocab)
        spoken = {"subject": vocab["subject"][trial % 3],
                  "verb":    vocab["verb"][(trial // 3) % 3],
                  "object":  vocab["object"][(trial // 9) % 3]}

        # NMDA gate using drive-pressure context (no recent drive to sensory)
        drive_tracker = {}
        gate = CoincidenceGate(
            section_name="intro",
            context_fn=context_no_recent_drive(drive_tracker, quiet_thresh=0.45),
            drive_thresh=0.05,
            ltp_boost=0.0,
        )

        for phase_name, mode, intro_target_name, expect_fire, expected_commit in phases:
            last_commit_this_phase = None
            gate.mode_strength.clear()

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

                intro_target = intro_vec[intro_target_name]
                noisy_intro = normalize(intro_target + 0.05 * (rng.standard_normal(N) +
                                                                1j * rng.standard_normal(N)))
                ev["intro"] = noisy_intro

                # Update drive tracker BEFORE tick
                update_drive_tracker(drive_tracker, ev)

                sys_.tick_once(ev, enable_self_evo=False, coordinator_on=False,
                               introspection_on=False)
                while len(sys_.sections["intro"].mode_bank) > 3:
                    sys_.sections["intro"].mode_bank.pop()
                    sys_.sections["intro"].mode_last_used.pop()

                committed, mode_id = gate.check_and_fire(sys_)
                if committed and mode_id is not None and mode_id < len(intro_modes):
                    last_commit_this_phase = intro_modes[mode_id]

            # Score
            results[phase_name]["actual"].append(last_commit_this_phase)
            if expect_fire:
                if last_commit_this_phase == expected_commit:
                    results[phase_name]["correct"] += 1
            else:
                if last_commit_this_phase is None:
                    results[phase_name]["correct"] += 1

    return results


if __name__ == "__main__":
    print("Clean NMDA gate test (LTP disabled, intro drive direct)\n")
    results = run_test(n_trials=20)
    for phase, data in results.items():
        n = data["correct"]
        print(f"  {phase:14s}: {n}/20 = {n/20:.0%}  reports = {Counter(data['actual']).most_common()}")
    total = sum(d["correct"] for d in results.values())
    n_phases = 5 * 20
    print(f"\nOverall: {total}/{n_phases} = {total/n_phases:.0%}")
