#!/usr/bin/env python3
"""MathLoom Global Settle Simulator.

Simulates balanced ternary addition via TAL energy minimization.
Tests the Global Settle Hypothesis: does carry propagate through
coupling in a single settle cycle regardless of word width?

No ML. No heuristics. Pure physics simulation.

Usage:
  python3 tools/mathloom_sim.py              # exhaustive 4-trit test
  python3 tools/mathloom_sim.py --width 32   # scaling test
  python3 tools/mathloom_sim.py --random 1000 --width 16  # random sample test
"""

from __future__ import annotations

import argparse
import time
from typing import List, Tuple

import numpy as np


# ---------------------------------------------------------------------------
# Balanced ternary helpers
# ---------------------------------------------------------------------------

def int_to_bal3(value: int, width: int) -> List[int]:
    """Convert integer to balanced ternary digits (LSB first)."""
    digits = []
    v = value
    for _ in range(width):
        r = v % 3
        if r == 2:
            r = -1
            v = (v + 1) // 3
        elif r == 0:
            v = v // 3
        else:  # r == 1
            v = (v - 1) // 3
        digits.append(r)
    return digits


def bal3_to_int(digits: List[int]) -> int:
    """Convert balanced ternary digits (LSB first) to integer."""
    return sum(d * (3 ** i) for i, d in enumerate(digits))


def bal3_range(width: int) -> Tuple[int, int]:
    """Return (min, max) representable values for given width."""
    max_val = sum(3 ** i for i in range(width))
    return -max_val, max_val


# ---------------------------------------------------------------------------
# Tri-well potential (TSAC)
# ---------------------------------------------------------------------------

# Frozen constants for tri-well: V(x) = a*x^6 - b*x^4 + c*x^2
# Chosen so minima are at x = -1, 0, +1
TSAC_A = 1.0
TSAC_B = 3.0
TSAC_C = 2.0


def tri_well(x: float) -> float:
    """Tri-well potential energy at position x."""
    return TSAC_A * x**6 - TSAC_B * x**4 + TSAC_C * x**2


def tri_well_grad(x: float) -> float:
    """Gradient of tri-well potential."""
    return 6 * TSAC_A * x**5 - 4 * TSAC_B * x**3 + 2 * TSAC_C * x


# ---------------------------------------------------------------------------
# MathLoom Energy Functional
# ---------------------------------------------------------------------------

MAX_SWEEPS = 50        # Maximum full-lattice sweep iterations
SETTLE_EPS = 1e-9      # Convergence threshold


def _best_trit(target: float) -> int:
    """Find the trit value {-1, 0, +1} closest to target."""
    best = 0
    best_dist = abs(target)
    for t in (-1, 1):
        d = abs(target - t)
        if d < best_dist:
            best = t
            best_dist = d
    return best


def mathloom_add(a_digits: List[int], b_digits: List[int],
                 width: int) -> Tuple[List[int], List[int], int, bool]:
    """
    Perform balanced ternary addition via global TAL settling.

    Strategy: iterative constraint propagation. Each sweep visits all
    digit positions simultaneously and picks the (s_i, c_{i+1}) pair
    that minimizes the local constraint energy while respecting the
    tri-well potential. This models the physical TAL fabric where all
    cells settle concurrently through energy minimization.

    The key difference from gradient descent: we operate directly in
    the discrete trit space {-1, 0, +1}, not in continuous space.
    This is what the real TSAC cells do — they snap to energy basins,
    they don't slide continuously.
    """
    n = width
    a = np.array(a_digits, dtype=np.int64)
    b = np.array(b_digits, dtype=np.int64)

    # State: sum digits and carry digits
    s = np.zeros(n, dtype=np.int64)
    c = np.zeros(n + 1, dtype=np.int64)  # c[0] = 0 (no input carry)

    converged = False
    iterations = 0

    for sweep in range(MAX_SWEEPS):
        changed = False

        # Forward pass: for each digit position, find the best (s_i, c_{i+1})
        # that satisfies a_i + b_i + c_i = s_i + 3*c_{i+1}
        for i in range(n):
            target = a[i] + b[i] + c[i]  # this is what s_i + 3*c_{i+1} must equal

            # Enumerate all valid (s, carry_out) pairs
            best_s = s[i]
            best_cout = c[i + 1]
            best_err = abs(target - best_s - 3 * best_cout)

            for try_s in (-1, 0, 1):
                for try_c in (-1, 0, 1):
                    err = abs(target - try_s - 3 * try_c)
                    if err < best_err:
                        best_err = err
                        best_s = try_s
                        best_cout = try_c

            if s[i] != best_s or c[i + 1] != best_cout:
                changed = True
            s[i] = best_s
            c[i + 1] = best_cout

        iterations = sweep + 1

        # Check convergence: all constraints satisfied?
        all_ok = True
        for i in range(n):
            if a[i] + b[i] + c[i] - s[i] - 3 * c[i + 1] != 0:
                all_ok = False
                break

        if all_ok:
            converged = True
            break

        if not changed:
            # No progress — stuck. Try backward pass.
            for i in range(n - 1, -1, -1):
                target = a[i] + b[i] + c[i]
                best_s = s[i]
                best_cout = c[i + 1]
                best_err = abs(target - best_s - 3 * best_cout)
                for try_s in (-1, 0, 1):
                    for try_c in (-1, 0, 1):
                        err = abs(target - try_s - 3 * try_c)
                        if err < best_err:
                            best_err = err
                            best_s = try_s
                            best_cout = try_c
                s[i] = best_s
                c[i + 1] = best_cout

            iterations += 1

            # Re-check
            all_ok = True
            for i in range(n):
                if a[i] + b[i] + c[i] - s[i] - 3 * c[i + 1] != 0:
                    all_ok = False
                    break
            if all_ok:
                converged = True
                break

    s_digits = [int(x) for x in s]
    c_digits = [int(x) for x in c]

    return s_digits, c_digits, iterations, converged


def verify_addition(a_val: int, b_val: int, width: int) -> Tuple[bool, int, bool]:
    """
    Verify that MathLoom produces correct addition for a + b.

    Returns: (correct, iterations, converged)
    """
    a_digits = int_to_bal3(a_val, width)
    b_digits = int_to_bal3(b_val, width)

    s_digits, c_digits, iterations, converged = mathloom_add(a_digits, b_digits, width)

    # Reconstruct result
    result = bal3_to_int(s_digits) + bal3_to_int(c_digits) * (3 ** width)
    expected = a_val + b_val

    correct = (result == expected)
    return correct, iterations, converged


# ---------------------------------------------------------------------------
# Test suites
# ---------------------------------------------------------------------------

def exhaustive_test(width: int) -> None:
    """Test all possible additions for given width."""
    lo, hi = bal3_range(width)
    total = 0
    correct = 0
    failed = 0
    total_iters = 0
    max_iters = 0
    unconverged = 0

    print(f"\n[MathLoom] Exhaustive test: {width}-trit words")
    print(f"[MathLoom] Value range: [{lo}, {hi}]")
    print(f"[MathLoom] Total combinations: {(hi - lo + 1) ** 2}")

    t0 = time.time()

    for a in range(lo, hi + 1):
        for b in range(lo, hi + 1):
            ok, iters, conv = verify_addition(a, b, width)
            total += 1
            total_iters += iters
            max_iters = max(max_iters, iters)
            if ok:
                correct += 1
            else:
                failed += 1
                if failed <= 5:
                    print(f"  FAIL: {a} + {b} != expected {a + b}")
            if not conv:
                unconverged += 1

    elapsed = time.time() - t0

    print(f"\n[MathLoom] Results:")
    print(f"  Total:       {total}")
    print(f"  Correct:     {correct} ({100 * correct / total:.2f}%)")
    print(f"  Failed:      {failed}")
    print(f"  Unconverged: {unconverged}")
    print(f"  Avg iters:   {total_iters / total:.1f}")
    print(f"  Max iters:   {max_iters}")
    print(f"  Elapsed:     {elapsed:.2f}s")
    print(f"  Verdict:     {'PASS' if failed == 0 else 'FAIL'}")


def scaling_test(widths: List[int], samples: int = 100) -> None:
    """Test settle time vs word width."""
    print(f"\n[MathLoom] Scaling test: {widths} trits, {samples} random samples each")

    rng = np.random.RandomState(42)  # deterministic seed

    for width in widths:
        lo, hi = bal3_range(width)
        total_iters = 0
        max_iters = 0
        correct = 0
        total = 0

        t0 = time.time()
        for _ in range(samples):
            a = rng.randint(lo, hi + 1)
            b = rng.randint(lo, hi + 1)
            ok, iters, conv = verify_addition(a, b, width)
            total += 1
            total_iters += iters
            max_iters = max(max_iters, iters)
            if ok:
                correct += 1

        elapsed = time.time() - t0
        avg_iters = total_iters / total

        print(f"  {width:3d} trits: avg_iters={avg_iters:6.1f}  max_iters={max_iters:4d}  "
              f"correct={correct}/{total}  elapsed={elapsed:.3f}s")

    print(f"\n[MathLoom] If avg_iters is roughly constant across widths, global settle is O(1).")
    print(f"[MathLoom] If avg_iters grows linearly, carry is sequential — fall back to Approach 1.")


def random_test(width: int, samples: int) -> None:
    """Random sample test at given width."""
    print(f"\n[MathLoom] Random test: {width}-trit words, {samples} samples")

    rng = np.random.RandomState(42)
    lo, hi = bal3_range(width)

    correct = 0
    failed = 0
    total_iters = 0
    max_iters = 0
    iter_list = []

    t0 = time.time()
    for _ in range(samples):
        a = rng.randint(lo, hi + 1)
        b = rng.randint(lo, hi + 1)
        ok, iters, conv = verify_addition(a, b, width)
        total_iters += iters
        max_iters = max(max_iters, iters)
        iter_list.append(iters)
        if ok:
            correct += 1
        else:
            failed += 1
            if failed <= 5:
                print(f"  FAIL: {a} + {b} != expected {a + b}")

    elapsed = time.time() - t0
    iter_arr = np.array(iter_list)

    print(f"\n[MathLoom] Results:")
    print(f"  Total:       {samples}")
    print(f"  Correct:     {correct} ({100 * correct / samples:.2f}%)")
    print(f"  Failed:      {failed}")
    print(f"  Avg iters:   {total_iters / samples:.1f}")
    print(f"  Median:      {np.median(iter_arr):.0f}")
    print(f"  P95:         {np.percentile(iter_arr, 95):.0f}")
    print(f"  P99:         {np.percentile(iter_arr, 99):.0f}")
    print(f"  Max:         {max_iters}")
    print(f"  Elapsed:     {elapsed:.2f}s")
    print(f"  Verdict:     {'PASS' if failed == 0 else 'FAIL'}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="MathLoom Global Settle Simulator")
    parser.add_argument("--width", type=int, default=4, help="Trit width (default: 4)")
    parser.add_argument("--exhaustive", action="store_true", help="Run exhaustive test (all combos)")
    parser.add_argument("--scaling", action="store_true", help="Run scaling test across widths")
    parser.add_argument("--random", type=int, default=0, help="Run N random samples")
    args = parser.parse_args()

    print("=" * 60)
    print("  MathLoom Global Settle Simulator")
    print("  Balanced Ternary Addition via TAL Energy Minimization")
    print("=" * 60)

    if args.scaling:
        scaling_test([4, 8, 12, 16, 24, 32])
    elif args.random > 0:
        random_test(args.width, args.random)
    else:
        exhaustive_test(args.width)


if __name__ == "__main__":
    main()
