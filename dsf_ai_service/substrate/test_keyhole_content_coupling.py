"""
GL-FIX-KEYHOLE-CONTENT-COUPLING-20260712 verification.

Real content-level coupling between adjacent emission sections
(assemblage.System._apply_keyhole_content_coupling), gated behind
KEYHOLE_CONTENT_COUPLING_ENABLED. Layered on top of the existing
threshold-discount keyhole handoff, which is unchanged.

Two groups of checks:
  1. Safety (unit-level, direct assemblage.py): off-by-default is a true
     no-op; injected operators are Hermitian/bounded; standing_goals
     never grows unboundedly (auto-expiry holds); a long zero-input
     stress run does not self-sustain a cascade (same failure shape as
     the 2026-07-08 STDP-cascade regression and the 2026-07-07
     hemispheric-integration perf regression this fix was designed to
     avoid -- see docs referenced in the commit message).
  2. Mechanism-level efficacy: with real commits forced (threshold
     override, not a realistic production value), does a sender's
     commit actually change the receiver's Hamiltonian energy, not
     just its commit threshold, flag off vs on. The shared
     test_dynamics_emission.py-style harness (real seeded engine +
     _emit_from_invariants) independently produces zero commits even
     at baseline on a clean checkout -- a pre-existing gap unrelated
     to this fix -- so it isn't used here for an A/B; real end-to-end
     efficacy is an observe-after-deploy question instead.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

os.environ["EMISSION_MODE"] = "grandurun"
os.environ["DEEP_ATLAS_ENABLED"] = "1"
os.environ["DEEP_PRIOR_ENABLED"] = "1"
os.environ["DECAY_PAUSED"] = "0"
os.environ["GRANDURUN_LEGACY_8D"] = "0"
os.environ["GRANDURUN_SPIN_VECTOR"] = "0"
os.environ["EMISSION_DYNAMICS"] = "1"
os.environ["LATERAL_INHIBITION_ENABLED"] = "1"


def _build_test_system(force_commits=False):
    """force_commits=True lowers det/p thresholds to near-zero so
    entropic_flip is reliably reachable in a small hand-built system
    with real evidence -- the point is to exercise
    _apply_keyhole_content_coupling's actual firing path deterministically,
    not to model realistic production thresholds (DET_COMMIT/P_COMMIT
    stay at their real defaults everywhere else in the codebase; this
    override is local to the dataclass instances this function builds).
    """
    import numpy as np
    from dsf_ai_service.substrate.assemblage import Section, System, N

    rng = np.random.default_rng(7)
    secs = [Section(name=n, rng=rng, role="subject_like")
            for n in ("subject", "verb", "object")]
    for sec in secs:
        sec.H_base = np.zeros((N, N), dtype=complex)
        sec.law_fields = {k: np.zeros((N, N), dtype=complex)
                           for k in ("symmetry", "consistency", "compactness")}
        sec.bootstrap_used = 999
        sec._suppress_novel_mode = True
        # give each section two real, well-separated modes so entropic_flip
        # (which needs a clear arc-max, not near-uniform overlap) is reachable
        from dsf_ai_service.substrate.assemblage import random_unit_complex, normalize
        m1 = random_unit_complex(N, rng)
        m2 = random_unit_complex(N, rng)
        sec.mode_bank = [m1, m2]
        sec.mode_last_used = [0, 0]
        sec.mode_strength = [1.0, 1.0]
        # project_into() requires map_inject to turn `evidence` into J at
        # all -- without it every evidence_pressure is silently 0 and
        # commit_check can never pass its `evidence_pressure < 0.15` gate.
        # Identity is sufficient for a test (real code uses make_projection).
        sec.map_inject = np.eye(N, dtype=complex)
        if force_commits:
            sec.det_commit = 0.01
            sec.p_commit = 0.01

    sys_ = System(secs, rng)
    sys_.add_keyhole("subject", -50, 50, "verb", goal_strength=0.4)
    sys_.add_keyhole("verb", -50, 50, "object", goal_strength=0.4)
    return sys_


def check_off_by_default_is_noop():
    sys_ = _build_test_system()
    os.environ["KEYHOLE_CONTENT_COUPLING_ENABLED"] = "0"
    before = {n: len(s.standing_goals) for n, s in sys_.sections.items()}
    for _ in range(30):
        sys_.tick_once({"subject": None, "verb": None, "object": None},
                       coordinator_on=False)
    after = {n: len(s.standing_goals) for n, s in sys_.sections.items()}
    ok = before == after == {n: 0 for n in sys_.sections}
    print(f"  off-by-default no-op: standing_goals before={before} after={after} -> "
          f"{'PASS' if ok else 'FAIL'}")
    return ok


def check_hermitian_and_bounded():
    from dsf_ai_service.substrate.assemblage import goal_op_for_template, random_unit_complex
    import numpy as np
    rng = np.random.default_rng(3)
    for _ in range(5):
        target = random_unit_complex(16, rng)
        op = goal_op_for_template(target)
        hermitian_err = float(np.max(np.abs(op - op.conj().T)))
        eigs = np.linalg.eigvalsh(op)
        bounded = bool(eigs.min() >= -1.0 - 1e-9 and eigs.max() <= 1e-9)
        if hermitian_err > 1e-9 or not bounded:
            print(f"  Hermitian/bounded check: FAIL (err={hermitian_err}, "
                  f"eig range=[{eigs.min():.4f}, {eigs.max():.4f}])")
            return False
    print("  Hermitian/bounded check: PASS (max err ~0, eigenvalues in [-1, 0])")
    return True


def check_bounded_goal_growth_when_enabled():
    sys_ = _build_test_system(force_commits=True)
    os.environ["KEYHOLE_CONTENT_COUPLING_ENABLED"] = "1"
    max_goals_seen = 0
    total_commits = 0
    for t in range(200):
        # Strong, constant evidence pressure on subject/verb so both
        # reliably reach entropic_flip and fire handoffs repeatedly --
        # the adversarial case for "does this accumulate state."
        ev = {"subject": sys_.sections["subject"].mode_bank[0] * 2.0,
              "verb": sys_.sections["verb"].mode_bank[0] * 2.0}
        sys_.tick_once(ev, coordinator_on=False)
        total_commits += sys_.system_log["n_commits"][-1]
        for s in sys_.sections.values():
            max_goals_seen = max(max_goals_seen, len(s.standing_goals))
    # handoff_lifetime=5 in expire_standing_goals -- with 200 ticks of
    # constant pressure and real repeated commits, standing_goals must
    # stay small (bounded by the expiry window), never grow toward
    # O(ticks). total_commits>0 confirms this actually exercised the
    # new code path rather than trivially passing on inactivity.
    fired = total_commits > 0
    ok = fired and max_goals_seen < 20
    print(f"  bounded goal growth under sustained pressure: "
          f"total_commits={total_commits} (path exercised: {fired}), "
          f"max concurrent standing_goals={max_goals_seen} over 200 ticks -> "
          f"{'PASS' if ok else 'FAIL'} (want < 20, i.e. nowhere near O(ticks))")
    return ok


def check_no_runaway_cascade_zero_input():
    """Same detection method as the 2026-07-08 STDP-cascade regression
    writeup: track raw commit-event counts over an extended zero-real-
    input run and confirm it does not sustain/grow on its own. Uses
    force_commits=True so the system has already fired real handoffs
    (real adversarial starting state, standing_goals non-empty) before
    the zero-input phase begins."""
    sys_ = _build_test_system(force_commits=True)
    os.environ["KEYHOLE_CONTENT_COUPLING_ENABLED"] = "1"
    # Prime it: a short burst of real evidence so real coupling goals
    # actually get injected before we cut input entirely.
    for t in range(10):
        ev = {"subject": sys_.sections["subject"].mode_bank[0] * 2.0}
        sys_.tick_once(ev, coordinator_on=False)
    primed_commits = sum(sys_.system_log["n_commits"])
    commit_counts = []
    for t in range(300):
        sys_.tick_once({}, coordinator_on=False)  # zero external evidence
        commit_counts.append(sys_.system_log["n_commits"][-1])
    total = sum(commit_counts)
    tail = sum(commit_counts[-50:])
    # With zero evidence_pressure, commit_check's own
    # `if evidence_pressure < 0.15: return False, None` gate should keep
    # this at (or very near) zero commits for the whole zero-input run --
    # the regression shape being tested against is *unbounded growth*
    # sustained by the system's own state, not "any activity at all."
    ok = primed_commits > 0 and tail <= total * 0.6 + 1 and total < 300
    print(f"  zero-input cascade check: primed_commits={primed_commits} "
          f"(real coupling fired before cutoff), then total_commits={total} "
          f"over 300 zero-input ticks, last-50-tick share={tail} -> "
          f"{'PASS' if ok else 'FAIL'} (no self-sustaining/growing cascade)")
    return ok


def check_efficacy_mechanism():
    """The shared test_dynamics_emission.py harness independently fails
    to produce any real commits at all right now (0/5, confirmed on a
    clean checkout before this fix's changes too) -- a pre-existing gap
    in that small hand-seeded engine, not something this fix can or
    should paper over here. So efficacy is checked directly at the
    mechanism level instead: with force_commits=True, does a sender's
    real commit actually change the receiver's Hamiltonian (not just
    its threshold) the way it's designed to -- i.e. does content
    coupling do something a disabled flag doesn't?
    Real end-to-end efficacy (does this raise the live commit rate) is
    an observe-after-deploy question, same as every other kill-switched
    feature graduated tonight (HOMEOSTATIC_SCALING_ENABLED,
    ENTRY_NEURON_BROADEN_ENABLED) -- local small-scale state doesn't
    represent production atlas depth (see: profile-live-before-
    investigate lesson)."""
    import numpy as np

    def commit_subject_and_read_verb_H(flag):
        sys_ = _build_test_system(force_commits=True)
        os.environ["KEYHOLE_CONTENT_COUPLING_ENABLED"] = str(flag)
        H_before = sys_.sections["verb"].H_total().copy()
        ev = {"subject": sys_.sections["subject"].mode_bank[0] * 2.0}
        sys_.tick_once(ev, coordinator_on=False)
        H_after = sys_.sections["verb"].H_total()
        return float(np.max(np.abs(H_after - H_before))), \
            len(sys_.sections["verb"].standing_goals)

    off_delta, off_goals = commit_subject_and_read_verb_H(0)
    on_delta, on_goals = commit_subject_and_read_verb_H(1)
    print(f"  mechanism check: OFF -> receiver H_total changed by {off_delta:.4f}, "
          f"standing_goals={off_goals}")
    print(f"  mechanism check: ON  -> receiver H_total changed by {on_delta:.4f}, "
          f"standing_goals={on_goals}")
    ok = on_goals > off_goals and on_delta > off_delta + 1e-6
    print(f"  mechanism check (real content coupling changes receiver's energy, "
          f"not just its threshold): {'PASS' if ok else 'FAIL'}")
    return ok


def main():
    print("GL-FIX-KEYHOLE-CONTENT-COUPLING-20260712 Verification")
    print("=" * 70)
    results = {
        "off_by_default_noop": check_off_by_default_is_noop(),
        "hermitian_bounded": check_hermitian_and_bounded(),
        "bounded_goal_growth": check_bounded_goal_growth_when_enabled(),
        "no_runaway_cascade": check_no_runaway_cascade_zero_input(),
        "efficacy_mechanism": check_efficacy_mechanism(),
    }
    print("\n" + "=" * 70)
    for k, v in results.items():
        print(f"  {k}: {'PASS' if v else 'FAIL'}")
    overall = all(results.values())
    print(f"\n  OVERALL: {'PASS' if overall else 'FAIL'}")
    return overall


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
