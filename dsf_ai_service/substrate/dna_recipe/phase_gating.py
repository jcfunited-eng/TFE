"""
GL-EXP-L5-PHASE-GATING-WC-20260608-01

Q: Does ordered SUBJECT -> VERB -> OBJECT emission emerge from substrate
   dynamics when keyhole excitation is time-phase-modulated (L5 primitive),
   vs arbitrary order when ungated?

Setup: Three sections (subject, verb, object), each with a mode bank.
Drive all three with evidence for tokens simultaneously.

Experiment A: NO PHASE GATING. Record commit order across trials.
Experiment B: PHASE-GATED EXCITATION. Subject excitable in phase 0..C/3,
verb in phase C/3..2C/3, object in phase 2C/3..C. Record commit order.

If A is arbitrary and B is consistently S->V->O, L5 carries syntax.
If B doesn't sort, named failure: which primitive refuses to compose.
"""

import numpy as np
from collections import Counter
from dsf_ai_service.substrate.assemblage import Section, System, N, normalize, random_unit_complex

# ---- shared rig ----

def make_projection(n, dim, rng):
    M = rng.standard_normal((n, n)) + 1j * rng.standard_normal((n, n))
    Q, _ = np.linalg.qr(M)
    P = np.zeros((n, n), dtype=complex)
    P[:dim, :dim] = np.eye(dim)
    return Q @ P @ Q.conj().T

def build_svo_system(rng, vocab):
    """Three-section S-V-O system. vocab = {'subject': [...], 'verb': [...], 'object': [...]}."""
    subj = Section(name="subject", rng=rng, role="subject_like")
    verb = Section(name="verb",    rng=rng, role="verb_like")
    obj  = Section(name="object",  rng=rng, role="object_like")
    for s in (subj, verb, obj):
        s.map_inject = make_projection(N, 8, rng)
    sys_ = System([subj, verb, obj], rng)
    # Install modes (one per token per section)
    token_vec = {}
    for sec_name, toks in vocab.items():
        sec = sys_.sections[sec_name]
        for tok in toks:
            v = random_unit_complex(N, rng)
            sec.mode_bank.append(v.copy())
            sec.mode_last_used.append(0)
            token_vec[(sec_name, tok)] = v
    return sys_, token_vec

def drive_one_trial(sys_, token_vec, sentence_dict, n_ticks, phase_gate_fn=None, rng=None):
    """Drive subject, verb, object simultaneously with evidence for the target tokens.
       sentence_dict = {'subject': 'cow', 'verb': 'jumped', 'object': 'fence'}
       phase_gate_fn(tick, sys_) called at start of each tick to set excitation if desired.
       Returns list of commits with (tick, section, mode_id).
    """
    if rng is None:
        rng = np.random.default_rng(0)
    commits = []
    # Evidence vectors: noisy versions of the target token's mode vector
    targets = {sec: token_vec[(sec, tok)] for sec, tok in sentence_dict.items()}
    for t in range(n_ticks):
        if phase_gate_fn is not None:
            phase_gate_fn(sys_.tick + 1, sys_)
        # Build evidence dict — drive each section with noisy target
        ev = {}
        for sec_name, target in targets.items():
            noisy = normalize(target + 0.10 * (rng.standard_normal(N) + 1j * rng.standard_normal(N)))
            ev[sec_name] = noisy
        these_commits = sys_.tick_once(ev,
                                       enable_self_evo=False,
                                       coordinator_on=False,
                                       introspection_on=False)
        for c in these_commits:
            commits.append({"tick": sys_.tick, "section": c["section"], "mode_id": c["mode_id"]})
    return commits

def first_commit_per_section(commits):
    """Return order of sections by first-commit-tick."""
    first = {}
    for c in commits:
        if c["section"] not in first:
            first[c["section"]] = c["tick"]
    # Sort by tick
    return sorted(first.items(), key=lambda kv: kv[1])

# ---- Experiment A: no gating ----

def run_no_gating(n_trials=20, n_ticks=60):
    rng_master = np.random.default_rng(42)
    orders = []
    no_emission = 0
    for trial in range(n_trials):
        seed = int(rng_master.integers(0, 10_000_000))
        rng = np.random.default_rng(seed)
        vocab = {"subject": ["cow", "moon", "bears"],
                 "verb":    ["jumped", "ran", "sleeps"],
                 "object":  ["fence", "milk", "dish"]}
        sys_, token_vec = build_svo_system(rng, vocab)
        sentence = {"subject": "cow", "verb": "jumped", "object": "fence"}
        commits = drive_one_trial(sys_, token_vec, sentence, n_ticks,
                                  phase_gate_fn=None, rng=rng)
        order = [sec for sec, _ in first_commit_per_section(commits)]
        if len(order) < 3:
            no_emission += 1
            orders.append(tuple(order))
        else:
            orders.append(tuple(order))
    return orders, no_emission

# ---- Experiment B: phase-gated excitation ----

def make_phase_gater(cycle, strength):
    """L5 primitive: at tick t in [0..cycle/3) excite subject,
       [cycle/3..2cycle/3) excite verb, [2cycle/3..cycle) excite object.
       Excitation pulse expires after one phase-width."""
    phase_width = cycle // 3
    def gate(tick, sys_):
        phase = tick % cycle
        if phase < phase_width:
            target = "subject"
        elif phase < 2 * phase_width:
            target = "verb"
        else:
            target = "object"
        # Excite target, INHIBIT non-targets (negative strength raises threshold)
        for sec_name in ("subject", "verb", "object"):
            sec = sys_.sections[sec_name]
            sec.excitation_expires_at = tick + 2
            if sec_name == target:
                sec.excitation_strength = strength
            else:
                sec.excitation_strength = -strength  # inhibition
    return gate

def run_phase_gating(n_trials=20, n_ticks=60, cycle=24, strength=0.20):
    rng_master = np.random.default_rng(42)
    orders = []
    no_emission = 0
    gater = make_phase_gater(cycle, strength)
    for trial in range(n_trials):
        seed = int(rng_master.integers(0, 10_000_000))
        rng = np.random.default_rng(seed)
        vocab = {"subject": ["cow", "moon", "bears"],
                 "verb":    ["jumped", "ran", "sleeps"],
                 "object":  ["fence", "milk", "dish"]}
        sys_, token_vec = build_svo_system(rng, vocab)
        sentence = {"subject": "cow", "verb": "jumped", "object": "fence"}
        commits = drive_one_trial(sys_, token_vec, sentence, n_ticks,
                                  phase_gate_fn=gater, rng=rng)
        order = [sec for sec, _ in first_commit_per_section(commits)]
        if len(order) < 3:
            no_emission += 1
            orders.append(tuple(order))
        else:
            orders.append(tuple(order))
    return orders, no_emission

# ---- Report ----

def summarize(label, orders, no_emission):
    print(f"\n=== {label} ===")
    print(f"Trials with <3 commits: {no_emission}/{len(orders)}")
    full = [o for o in orders if len(o) == 3]
    counts = Counter(full)
    target = ("subject", "verb", "object")
    n_target = counts.get(target, 0)
    print(f"S->V->O order: {n_target}/{len(full)} of full-commit trials")
    print("Top 5 orders:")
    for o, n in counts.most_common(5):
        flag = "  <- target" if o == target else ""
        print(f"  {o}: {n}{flag}")

if __name__ == "__main__":
    print("Experiment A — NO GATING (baseline)")
    a_orders, a_none = run_no_gating(n_trials=20, n_ticks=60)
    summarize("A: no gating", a_orders, a_none)

    print("\nExperiment B — PHASE GATING sweep")
    for strength in [0.20, 0.30, 0.45, 0.60]:
        for cycle in [18, 24, 36]:
            b_orders, b_none = run_phase_gating(n_trials=20, n_ticks=60,
                                                cycle=cycle, strength=strength)
            target = Counter(b_orders).get(("subject", "verb", "object"), 0)
            subj_first = sum(1 for o in b_orders if len(o) >= 1 and o[0] == "subject")
            print(f"  strength={strength}, cycle={cycle}: S->V->O={target}/20, subject_first={subj_first}/20")
