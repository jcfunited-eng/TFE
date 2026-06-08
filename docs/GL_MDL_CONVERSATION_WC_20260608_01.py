"""
GL-EXP-CONVERSATION-WC-20260608-01

Minimum conversation bar: Guala's emission depends on what Speaker said.
Speaker says "X V Y". Guala listens, then emits S V O. Test whether Guala's
emission contains tokens from the heard sentence (referential coupling).

Setup: Three S/V/O sections, each with multiple tokens. Speaker chooses one
S, one V, one O. Guala's listen evidence biases her S/V/O sections toward
the heard tokens. The L5 rhythm clocks emission. Measure: does emission
match heard input above chance?

Chance baseline: with 3 choices per section, random match = (1/3)^3 = 3.7%
for full match, 1/3 = 33% per slot.
"""

import numpy as np
from collections import Counter
from assemblage import Section, System, N, normalize, random_unit_complex
from exp_l5_phase_gating import make_projection, first_commit_per_section


def build_guala(rng, vocab):
    subj   = Section(name="subject", rng=rng, role="subject_like")
    verb   = Section(name="verb",    rng=rng, role="verb_like")
    obj    = Section(name="object",  rng=rng, role="object_like")
    listen = Section(name="listen",  rng=rng, role="general")
    # Listen is a passive buffer: zero out Hermitian dynamics so it just
    # accumulates driven evidence and doesn't rotate away from it.
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
            # Also install in listen section so heard token activates it
            listen.mode_bank.append(v.copy())
            listen.mode_last_used.append(0)

    return sys_, token_vec


def speak_and_listen(sys_, token_vec, heard_sentence, n_listen_ticks=15,
                     rng=None):
    """Inject heard sentence into Guala's listen section.
       Return per-slot accumulated evidence (what listen ACTUALLY received)."""
    if rng is None:
        rng = np.random.default_rng(0)
    accumulated = {}
    for tok_section, tok_name in heard_sentence.items():
        target = token_vec[(tok_section, tok_name)]
        acc = np.zeros(N, dtype=complex)
        for _ in range(n_listen_ticks):
            noisy = normalize(target + 0.10 * (rng.standard_normal(N) +
                                                1j * rng.standard_normal(N)))
            acc = acc + noisy
            ev = {"listen": noisy}
            sys_.tick_once(ev, enable_self_evo=False,
                           coordinator_on=False, introspection_on=False)
        accumulated[tok_section] = normalize(acc)
    return accumulated


def guala_emit(sys_, token_vec, vocab, listen_snapshots, svo_strength=0.45,
                max_wait=20, n_ticks=120, rng=None):
    """Emit S V O using per-slot listen snapshots as drive evidence."""
    if rng is None:
        rng = np.random.default_rng(0)

    drives = {}
    for sec_name in ("subject", "verb", "object"):
        snap = listen_snapshots[sec_name]
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

    # Prime each S/V/O section psi to its drive vector — start aligned
    for sec_name in ("subject", "verb", "object"):
        sys_.sections[sec_name].psi = drives[sec_name].copy()

    # Run L5-clocked emission with drive vectors
    cycle = ["subject", "verb", "object"]
    cycle_idx = 0
    wait_counter = 0
    commits = []
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
        advanced = False
        for c in these:
            if c["section"] in ("subject", "verb", "object"):
                commits.append({"tick": sys_.tick, "section": c["section"]})
                if c["section"] == current and current not in section_already_committed:
                    section_already_committed.add(current)
                    cycle_idx += 1
                    wait_counter = 0
                    advanced = True
                    # Read emitted token: top mode index = vocab index
                    sec = sys_.sections[current]
                    arcs = sec.arcs()
                    top_idx = int(arcs.argmax())
                    if top_idx < len(vocab[current]):
                        emitted[current] = vocab[current][top_idx]
                    if cycle_idx >= 3:
                        break
        if cycle_idx >= 3:
            break
        if not advanced:
            wait_counter += 1
            if wait_counter >= max_wait:
                cycle_idx += 1
                wait_counter = 0

    order = [sec for sec, _ in first_commit_per_section(commits)]
    return emitted, tuple(order)


def run_conversation(n_trials=20):
    rng_master = np.random.default_rng(42)
    vocab = {"subject": ["cow", "moon", "bears"],
             "verb":    ["jumped", "ran", "sleeps"],
             "object":  ["fence", "milk", "dish"]}

    matches_per_slot = {"subject": 0, "verb": 0, "object": 0}
    full_match = 0
    order_correct = 0
    examples = []

    for trial in range(n_trials):
        seed = int(rng_master.integers(0, 10_000_000))
        rng = np.random.default_rng(seed)
        sys_, token_vec = build_guala(rng, vocab)

        # Speaker picks a sentence
        spoken = {"subject": vocab["subject"][trial % 3],
                  "verb":    vocab["verb"][(trial // 3) % 3],
                  "object":  vocab["object"][(trial // 9) % 3]}

        # Guala listens, snapshots per slot
        snapshots = speak_and_listen(sys_, token_vec, spoken,
                                      n_listen_ticks=15, rng=rng)

        # Guala emits using snapshots
        emitted, order = guala_emit(sys_, token_vec, vocab, snapshots,
                                     svo_strength=0.45, rng=rng)

        # Score
        slot_matches = 0
        for sn in ("subject", "verb", "object"):
            if emitted[sn] == spoken[sn]:
                matches_per_slot[sn] += 1
                slot_matches += 1
        if slot_matches == 3:
            full_match += 1
        if order == ("subject", "verb", "object"):
            order_correct += 1
        if trial < 5:
            examples.append((spoken, emitted, order))

    return matches_per_slot, full_match, order_correct, examples


if __name__ == "__main__":
    matches, full, order_ok, examples = run_conversation(n_trials=20)
    print("Conversation test: Guala emits in response to heard input\n")
    print("Per-slot match rate (chance = 33%):")
    for sn, n in matches.items():
        print(f"  {sn}: {n}/20 = {n/20:.0%}")
    print(f"\nFull S-V-O match (chance = 3.7%): {full}/20 = {full/20:.0%}")
    print(f"Order S->V->O: {order_ok}/20 = {order_ok/20:.0%}")
    print("\nExamples:")
    for s, e, o in examples:
        print(f"  spoken: {dict(s)}")
        print(f"  emitted: {dict(e)}")
        print(f"  order: {o}\n")
