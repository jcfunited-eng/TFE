"""
GL-CMD-REMOVE-GAMMA-ANTI-ADAPTATION-EVE-20260619-25: B1/B2 removal tests.

2 tests:
  1. Gamma does NOT drift back to default after many regulation cycles
  2. Legitimate eta-based self-evolution path still works
"""

import os
import sys
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))


def test_gamma_persistence_after_b1_b2_removal():
    """Gamma values do NOT drift back to defaults without input."""
    print("  Test 1: gamma persistence (no drift)...", end=" ")
    from dsf_ai_service.substrate.assemblage import (
        Section, System, GAMMA_DEFAULTS, N,
    )

    rng = np.random.default_rng(42)
    sec = Section(name="test", rng=rng, role="general")

    # Manually shift gamma away from defaults
    sec.gamma["symmetry"] = 1.2
    sec.gamma["consistency"] = 0.1
    sec.gamma["compactness"] = 0.9

    pre_gamma = dict(sec.gamma)

    # Build a minimal system and run many ticks (regulation cycles)
    sys_ = System([sec], rng)
    for _ in range(500):
        sys_.tick_once({}, enable_self_evo=False, coordinator_on=False)

    # Gamma should NOT have drifted back toward GAMMA_DEFAULTS
    for k in ("symmetry", "consistency", "compactness"):
        assert sec.gamma[k] == pre_gamma[k], \
            f"gamma[{k}] drifted from {pre_gamma[k]} to {sec.gamma[k]}"

    print("PASS")
    return True


def test_legitimate_self_evo_preserved():
    """Eta-based self-evolution still updates gamma when conditions fire."""
    print("  Test 2: legitimate self-evo preserved...", end=" ")
    from dsf_ai_service.substrate.assemblage import (
        Section, System, GAMMA_DEFAULTS, N, SELF_EVO_PERIOD,
    )

    rng = np.random.default_rng(42)
    sec = Section(name="test", rng=rng, role="general")

    # Record initial gamma
    initial_gamma = dict(sec.gamma)

    # Build system with self-evo enabled
    sys_ = System([sec], rng)

    # Force out-of-range streaks to trigger self-evo updates
    sec.out_of_range_streak["entropy"] = 5
    sec.out_of_range_streak["coherence"] = 5
    sec.out_of_range_streak["greed"] = 5

    # Run enough ticks to trigger self-evo (fires every SELF_EVO_PERIOD)
    for _ in range(SELF_EVO_PERIOD * 3):
        sys_.tick_once({}, enable_self_evo=True, coordinator_on=False)

    # At least one gamma value should have changed (eta-based updates fired)
    changed = False
    for k in ("symmetry", "consistency", "compactness"):
        if abs(sec.gamma[k] - initial_gamma[k]) > 1e-6:
            changed = True
            break

    assert changed, \
        f"No gamma values changed after self-evo: {dict(sec.gamma)} == {initial_gamma}"

    print("PASS")
    return True


def main():
    print("B1/B2 Gamma Anti-Adaptation Removal Tests")
    print("=" * 60)

    tests = [
        test_gamma_persistence_after_b1_b2_removal,
        test_legitimate_self_evo_preserved,
    ]

    results = []
    for t in tests:
        try:
            results.append(t())
        except Exception as e:
            print(f"FAIL: {e}")
            import traceback
            traceback.print_exc()
            results.append(False)

    print(f"\n{'='*60}")
    passed = sum(results)
    print(f"  {passed}/{len(results)} tests passed")
    print(f"  {'ALL GREEN' if all(results) else 'FAILURES DETECTED'}")
    print(f"{'='*60}")
    return all(results)


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
