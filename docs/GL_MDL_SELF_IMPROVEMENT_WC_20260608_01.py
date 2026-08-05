"""
GL-EXP-SELF-IMPROVEMENT-PLASTICITY-WC-20260608-01

Self-improvement with proper gate-to-section feedback.

Setup: per-trial random heard sentence. Listen, then emit. The S/V/O
sections have plasticity installed. NMDA gates on each S/V/O fire LTP
on whichever mode was the listen-derived target.

Critical: LTP now modifies Section.arcs() directly via mode_strength,
so the substrate's commit dynamics change — not just my post-hoc read.

Test: does match rate improve over trials?
"""

import numpy as np
from collections import Counter
from assemblage import Section, System, N, normalize, random_unit_complex
from exp_l5_phase_gating import make_projection
from gl_nmda import CoincidenceGate
from gl_plasticity import install_plasticity


def build_guala(rng, vocab):
    subj   = Section(name="subject", rng=rng, role="subject_like")
    verb   = Section(name="verb",    rng=rng, role="verb_like")
    obj    = Section(name="object",  rng=rng, role="object_like")
    listen = Section(name="listen",  rng=rng, role="general")
    listen.H_base = np.zeros((N, N), dtype=complex)
    listen.law_fields = {"symmetry": np.zeros((N, N), dtype=complex),
                          "consistency": np.zeros((N, N), dtype=complex),
                          "compactness": np.zeros((N, N), dtype=complex)}
    for s in (subj, verb, obj, listen):
        s.map_inject = make_projection(N, 8, rng)
    sys_ = System([subj, verb, obj, listen], rng)

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

    # INSTALL PLASTICITY on S/V/O
    for sn in ("subject", "verb", "object"):
        install_plasticity(sys_.sections[sn])

    return sys_, token_vec


def listen_then_emit(sys_, token_vec, vocab, heard, gates,
                      svo_strength=0.45, max_wait=20, n_ticks=120,
                      n_listen_ticks=15, rng=None):
    if rng is None:
        rng = np.random.default_rng(0)

    accumulated = {}
    for tok_section, tok_name in heard.items():
        target = token_vec[(tok_section, tok_name)]
        acc = np.zeros(N, dtype=complex)
        for _ in range(n_listen_ticks):
            noisy = normalize(target + 0.10 * (rng.standard_normal(N) +
                                                1j * rng.standard_normal(N)))
            acc = acc + noisy
            ev = {"listen": noisy}
            sys_.tick_once(ev, enable_self_evo=False, coordinator_on=False,
                           introspection_on=False)
        accumulated[tok_section] = normalize(acc)

    drives = {}
    for sec_name in ("subject", "verb", "object"):
        snap = accumulated[sec_name]
        weights = []
        for tok in vocab[sec_name]:
            v = token_vec[(sec_name, tok)]
            w = float(np.abs(np.vdot(v, snap)) ** 2)
            weights.append((tok, w, v))
        weights.sort(key=lambda x: -x[1])
        bias = np.zeros(N, dtype=complex)
        for tok, w, v in weights[:2]:
            bias = bias + w * v
        drives[sec_name] = normalize(bias) if np.linalg.norm(bias) > 0 else \
                            random_unit_complex(N, rng)

    for sec_name in ("subject", "verb", "object"):
        sys_.sections[sec_name].psi = drives[sec_name].copy()

    cycle = ["subject", "verb", "object"]
    cycle_idx = 0
    wait_counter = 0
    section_already_committed = set()
    emitted = {"subject": None, "verb": None, "object": None}

    for t in range(n_ticks):
        current = cycle[cycle_idx % 3]
        for sn in ("subject", "verb", "object"):
            sec = sys_.sections[sn]
            sec.excitation_expires_at = sys_.tick + 2
            if sn == current:
                sec.excitation_strength = svo_strength
            else:
                sec.excitation_strength = -svo_strength
        ev = {}
        for sec_name in ("subject", "verb", "object"):
            target = drives[sec_name]
            noisy = normalize(target + 0.10 * (rng.standard_normal(N) +
                                                1j * rng.standard_normal(N)))
            ev[sec_name] = noisy
        these = sys_.tick_once(ev, enable_self_evo=False,
                               coordinator_on=False, introspection_on=False)

        # NMDA gates fire LTP on whichever mode has highest effective arc
        # Context: always-fire during emit phase (we already listened)
        for sn in ("subject", "verb", "object"):
            if sn in gates:
                gates[sn].check_and_fire(sys_)

        advanced = False
        for c in these:
            if c["section"] in ("subject", "verb", "object"):
                if c["section"] == current and current not in section_already_committed:
                    section_already_committed.add(current)
                    sec = sys_.sections[current]
                    # arcs is now effective arcs (LTP-modified) via plasticity
                    arcs = sec.arcs()
                    top_idx = int(arcs.argmax())
                    if top_idx < len(vocab[current]):
                        emitted[current] = vocab[current][top_idx]
                    cycle_idx += 1
                    wait_counter = 0
                    advanced = True
                    if cycle_idx >= 3:
                        break
        if cycle_idx >= 3:
            break
        if not advanced:
            wait_counter += 1
            if wait_counter >= max_wait:
                cycle_idx += 1
                wait_counter = 0

    return emitted


def run(n_trials=40, ltp_boost=0.05, supervised=True):
    rng = np.random.default_rng(42)
    vocab = {"subject": ["cow", "moon", "bears"],
             "verb":    ["jumped", "ran", "sleeps"],
             "object":  ["fence", "milk", "dish"]}
    sys_, token_vec = build_guala(rng, vocab)

    # Outcome signal holder (dopamine-equivalent): {section: expected_mode_id}
    expected_mode = {"subject": None, "verb": None, "object": None}

    def context_match_expected(sn):
        """Context fires only when section's current top arc matches the
           expected mode from listen-derived drive (dopamine signal)."""
        def check(sys_):
            if not supervised:
                return True
            if expected_mode[sn] is None:
                return False
            sec = sys_.sections[sn]
            arcs = sec.arcs()
            if len(arcs) == 0:
                return False
            return int(arcs.argmax()) == expected_mode[sn]
        return check

    gates = {sn: CoincidenceGate(
        section_name=sn,
        context_fn=context_match_expected(sn),
        drive_thresh=0.05,
        ltp_boost=ltp_boost,
        ltp_decay=0.998,
        ltp_ceiling=2.5,
    ) for sn in ("subject", "verb", "object")}

    history = []
    for trial in range(n_trials):
        # PUMP RESET between trials: clear psi state but keep mode_strength.
        # Episodic boundary primitive (Na+/K+ pump equivalent).
        for sn in ("subject", "verb", "object", "listen"):
            sec = sys_.sections[sn]
            sec.psi = normalize(random_unit_complex(N, rng) * 0.3 +
                                 normalize(np.ones(N, dtype=complex)) * 0.7)

        heard = {"subject": vocab["subject"][rng.integers(0, 3)],
                 "verb":    vocab["verb"][rng.integers(0, 3)],
                 "object":  vocab["object"][rng.integers(0, 3)]}
        for sn in ("subject", "verb", "object"):
            expected_mode[sn] = vocab[sn].index(heard[sn])
        emitted = listen_then_emit(sys_, token_vec, vocab, heard, gates, rng=rng)
        matches = {sn: (emitted[sn] == heard[sn]) for sn in ("subject", "verb", "object")}
        history.append((trial, sum(matches.values()), dict(heard), dict(emitted)))
    return history, sys_


if __name__ == "__main__":
    print("Self-improvement with plasticity + supervised LTP\n")
    print("BASELINE (no LTP):")
    h0, _ = run(n_trials=40, ltp_boost=0.0)
    for lo, hi in [(0,10), (10,20), (20,30), (30,40)]:
        rate = sum(n for t, n, _, _ in h0 if lo <= t < hi) / (3 * (hi - lo))
        print(f"  trials {lo}-{hi}: {rate:.0%}")
    print()
    print("UNSUPERVISED LTP (no outcome signal):")
    h_un, _ = run(n_trials=40, ltp_boost=0.05, supervised=False)
    for lo, hi in [(0,10), (10,20), (20,30), (30,40)]:
        rate = sum(n for t, n, _, _ in h_un if lo <= t < hi) / (3 * (hi - lo))
        print(f"  trials {lo}-{hi}: {rate:.0%}")
    print()
    print("SUPERVISED LTP (dopamine when arc matches expected):")
    h1, sys_ = run(n_trials=40, ltp_boost=0.05, supervised=True)
    for lo, hi in [(0,10), (10,20), (20,30), (30,40)]:
        rate = sum(n for t, n, _, _ in h1 if lo <= t < hi) / (3 * (hi - lo))
        print(f"  trials {lo}-{hi}: {rate:.0%}")

    print(f"\nFinal mode_strength per section (supervised run):")
    label = {"subject": ["cow","moon","bears"], "verb": ["jumped","ran","sleeps"],
              "object": ["fence","milk","dish"]}
    for sn in ("subject", "verb", "object"):
        sec = sys_.sections[sn]
        ms = [round(s, 2) for s in sec.mode_strength[:3]]
        print(f"  {sn}: {dict(zip(label[sn], ms))}")
