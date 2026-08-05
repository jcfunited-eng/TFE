"""
GL-EXP-L5-HABITUATION-V4-WC-20260608-01

Final piece: rhythm doesn't free-run; it advances when the currently-excited
S/V/O section commits. This is the proper bidirectional coupling — rhythm
drives WHICH section is excitable, S/V/O commits drive WHEN rhythm advances.

Per spec: this is the SPPU dead zone feedback loop closing properly.
"""

import numpy as np
from collections import Counter
from assemblage import Section, System, N, normalize, random_unit_complex
from exp_l5_phase_gating import make_projection, first_commit_per_section


def build_system(rng, vocab):
    subj   = Section(name="subject", rng=rng, role="subject_like")
    verb   = Section(name="verb",    rng=rng, role="verb_like")
    obj    = Section(name="object",  rng=rng, role="object_like")
    for s in (subj, verb, obj):
        s.map_inject = make_projection(N, 8, rng)
    sys_ = System([subj, verb, obj], rng)

    token_vec = {}
    for sec_name, toks in vocab.items():
        sec = sys_.sections[sec_name]
        for tok in toks:
            v = random_unit_complex(N, rng)
            sec.mode_bank.append(v.copy())
            sec.mode_last_used.append(0)
            token_vec[(sec_name, tok)] = v

    return sys_, token_vec


def run_v4(n_trials=20, n_ticks=120,
           svo_strength=0.45, max_wait_per_phase=20):
    """Rhythm cycles subject -> verb -> object, advancing when the
       currently-excited section commits OR after max_wait timeout."""
    rng_master = np.random.default_rng(42)
    orders = []
    for trial in range(n_trials):
        seed = int(rng_master.integers(0, 10_000_000))
        rng = np.random.default_rng(seed)
        vocab = {"subject": ["cow", "moon", "bears"],
                 "verb":    ["jumped", "ran", "sleeps"],
                 "object":  ["fence", "milk", "dish"]}
        sys_, token_vec = build_system(rng, vocab)
        sentence = {"subject": "cow", "verb": "jumped", "object": "fence"}
        targets = {sec: token_vec[(sec, tok)] for sec, tok in sentence.items()}

        # Cycle through sections; advance only when current section commits
        cycle = ["subject", "verb", "object"]
        cycle_idx = 0
        wait_counter = 0
        commits = []
        section_already_committed = set()

        for t in range(n_ticks):
            current = cycle[cycle_idx % 3]
            # Apply excitation pattern: excite current, inhibit others
            for sn in ("subject", "verb", "object"):
                sec = sys_.sections[sn]
                sec.excitation_expires_at = sys_.tick + 2
                if sn == current:
                    sec.excitation_strength = svo_strength
                else:
                    sec.excitation_strength = -svo_strength

            ev = {}
            for sec_name in ("subject", "verb", "object"):
                noisy = normalize(targets[sec_name] +
                                  0.10 * (rng.standard_normal(N) +
                                          1j * rng.standard_normal(N)))
                ev[sec_name] = noisy
            these = sys_.tick_once(ev, enable_self_evo=False,
                                   coordinator_on=False,
                                   introspection_on=False)
            advanced = False
            for c in these:
                if c["section"] in ("subject", "verb", "object"):
                    commits.append({"tick": sys_.tick, "section": c["section"]})
                    if c["section"] == current and current not in section_already_committed:
                        section_already_committed.add(current)
                        cycle_idx += 1
                        wait_counter = 0
                        advanced = True
                        if cycle_idx >= 3:
                            break  # all three committed
            if cycle_idx >= 3:
                break
            if not advanced:
                wait_counter += 1
                if wait_counter >= max_wait_per_phase:
                    cycle_idx += 1
                    wait_counter = 0

        order = [sec for sec, _ in first_commit_per_section(commits)]
        orders.append(tuple(order))
    return orders


if __name__ == "__main__":
    target = ("subject", "verb", "object")
    print("Test: rhythm advances on commit (proper coupling)\n")
    for ss in [0.30, 0.45, 0.60]:
        for mw in [10, 20, 40]:
            orders = run_v4(n_trials=20, svo_strength=ss, max_wait_per_phase=mw)
            tgt = Counter(orders).get(target, 0)
            sf = sum(1 for o in orders if len(o) >= 1 and o[0] == "subject")
            print(f"  svo_strength={ss} max_wait={mw}: S->V->O={tgt}/20 subj_first={sf}/20")
