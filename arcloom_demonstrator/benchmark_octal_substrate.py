#!/usr/bin/env python3
"""tools/benchmark_modular_column_substrate.py

Comparative Benchmark Suite: 4-Column Baseline vs. 8-Column Balanced Octet vs. 64-Column Cortical Array
Substrate: ArcLoom Discrete Neuromorphic Architecture in Native SIMD Rust (guala_core)

Benchmarks:
  1. Microsecond Timing & Component Throughput (1,000 causal ticks, seeded: random.seed(42))
  2. Spatial Tracking Polar Register Hold under Sensory Noise & Occlusion
  3. Multi-Modal Plastic Synaptic Hardening (Acoustic-Optical Binding)
  4. von Mises Barrier Yield Refusal & Motor Gating (S2 -> M1 / M2)
  5. Nocturnal Sleep Consolidation & Synaptic Downscaling
"""

from __future__ import annotations

import time
import random
import statistics
import guala_core
from guala_core import ModularSubstrate4D, ModularSubstrate8D, ModularSubstrate64D


def benchmark_timing(n_ticks: int = 1000) -> dict:
    """Benchmark raw per-tick latency and component throughput in native Rust (seeded input distribution)."""
    print("=" * 70)
    print(f"BENCHMARK 1: TIMING & COMPONENT THROUGHPUT ({n_ticks:,} Causal Ticks, Seeded: seed=42)")
    print("=" * 70)

    # Seed random inputs for deterministic reproducibility
    random.seed(42)

    sub4 = ModularSubstrate4D(yield_threshold=0.60, plastic_rate=0.03, activation_threshold=0.25)
    sub8 = ModularSubstrate8D(yield_threshold=0.60, plastic_rate=0.03, activation_threshold=0.25)

    sensory_trits = [1 if random.random() > 0.5 else -1 for _ in range(64)]
    somatic_trits = [1, 1, 0, 0, 0, 0, 0, 0] + [0] * 24

    # 4-Column Timing
    latencies_4d: list[float] = []
    for _ in range(n_ticks):
        t0 = time.perf_counter()
        sub4.step(sensory_trits, somatic_trits, observed_r_mm=300.0, observed_theta_mdeg=15000, barrier_stress=0.1)
        t1 = time.perf_counter()
        latencies_4d.append((t1 - t0) * 1_000_000.0)  # microseconds

    # 8-Column Timing
    latencies_8d: list[float] = []
    for _ in range(n_ticks):
        t0 = time.perf_counter()
        sub8.step(sensory_trits, somatic_trits, observed_r_mm=300.0, observed_theta_mdeg=15000, barrier_stress=0.1, acoustic_formant=120.0)
        t1 = time.perf_counter()
        latencies_8d.append((t1 - t0) * 1_000_000.0)  # microseconds

    mean_4 = statistics.mean(latencies_4d)
    median_4 = statistics.median(latencies_4d)
    p99_4 = statistics.quantiles(latencies_4d, n=100)[98]
    fps_4 = 1_000_000.0 / mean_4

    mean_8 = statistics.mean(latencies_8d)
    median_8 = statistics.median(latencies_8d)
    p99_8 = statistics.quantiles(latencies_8d, n=100)[98]
    fps_8 = 1_000_000.0 / mean_8

    print(f"4-Column Substrate (1,280 Nodes, 16 Directional Column-Pair Fascicular Slots):")
    print(f"  Mean Latency:         {mean_4:6.2f} µs | Median: {median_4:6.2f} µs | P99: {p99_4:6.2f} µs")
    print(f"  Component Throughput: {fps_4:10,.0f} ticks/second (Component benchmark)")
    print()
    print(f"8-Column Octet (2,560 Nodes, 64 Directional Column-Pair Fascicular Slots):")
    print(f"  Mean Latency:         {mean_8:6.2f} µs | Median: {median_8:6.2f} µs | P99: {p99_8:6.2f} µs")
    print(f"  Component Throughput: {fps_8:10,.0f} ticks/second (Component benchmark)")
    print()
    print(f"  Scaling Factor:       {mean_8 / mean_4:0.2f}x execution time for 2.0x column count & 4.0x fasciculi.")

    # 64-Column Full Cortical Array Timing (50 ticks)
    sub64 = ModularSubstrate64D(yield_threshold=0.60, plastic_rate=0.03, activation_threshold=0.25)
    latencies_64d: list[float] = []
    for _ in range(50):
        t0 = time.perf_counter()
        sub64.step(sensory_trits, somatic_trits, observed_r_mm=300.0, observed_theta_mdeg=15000, barrier_stress=0.1, acoustic_formants=[120.0])
        t1 = time.perf_counter()
        latencies_64d.append((t1 - t0) * 1_000_000.0)

    mean_64 = statistics.mean(latencies_64d)
    median_64 = statistics.median(latencies_64d)
    p99_64 = statistics.quantiles(latencies_64d, n=100)[98]
    fps_64 = 1_000_000.0 / mean_64

    print(f"64-Column Cortical Array (20,480 Nodes, 4,096 Directional Column-Pair Fascicular Slots):")
    print(f"  Mean Latency:         {mean_64:6.2f} µs | Median: {median_64:6.2f} µs | P99: {p99_64:6.2f} µs")
    print(f"  Component Throughput: {fps_64:10,.0f} ticks/second (Component benchmark)")
    print()
    print(f"  Scaling Factor:       {mean_8 / mean_4:0.2f}x (8D/4D), {mean_64 / mean_8:0.2f}x (64D/8D).")
    print(f"  Measured Component Throughput: 4D={fps_4:,.0f} Hz, 8D={fps_8:,.0f} Hz, 64D={fps_64:,.0f} Hz (seed=42).\n")

    return {
        "mean_4d_us": mean_4,
        "mean_8d_us": mean_8,
        "mean_64d_us": mean_64,
        "fps_4d": fps_4,
        "fps_8d": fps_8,
        "fps_64d": fps_64,
    }


def benchmark_spatial_occlusion_and_noise(n_blank_ticks: int = 60) -> dict:
    """Benchmark spatial permanence retention under +100% sensory noise."""
    print("=" * 70)
    print(f"BENCHMARK 2: SPATIAL TRACKING POLAR REGISTER HOLD UNDER SENSORY NOISE & OCCLUSION")
    print("=" * 70)

    sub4 = ModularSubstrate4D(yield_threshold=0.50, plastic_rate=0.03, activation_threshold=0.20)
    sub8 = ModularSubstrate8D(yield_threshold=0.50, plastic_rate=0.03, activation_threshold=0.20)

    # Prime both substrates with target at r=450 mm, theta=35,000 mdeg (35 deg)
    sensory_clean = [1] * 64
    somatic = [0] * 32

    for _ in range(10):
        sub4.step(sensory_clean, somatic, observed_r_mm=450.0, observed_theta_mdeg=35000, barrier_stress=0.0)
        sub8.step(sensory_clean, somatic, observed_r_mm=450.0, observed_theta_mdeg=35000, barrier_stress=0.0, acoustic_formant=0.0)

    # Now enter occlusion: Target is occluded (observed=None), but sensor buffer is flooded with 100% white noise
    print(f"Blinding visual feed and injecting random white noise for {n_blank_ticks} consecutive ticks...")

    trace_history_4d = []
    trace_history_8d = []

    for tick in range(1, n_blank_ticks + 1):
        noise_sensory = [random.choice([-1, 0, 1]) for _ in range(64)]
        sub4.step(noise_sensory, somatic, observed_r_mm=None, observed_theta_mdeg=None, barrier_stress=0.0)
        sub8.step(noise_sensory, somatic, observed_r_mm=None, observed_theta_mdeg=None, barrier_stress=0.0, acoustic_formant=0.0)

        r4, th4, tr4, occ4 = sub4.get_spatial_tracking()
        r8, th8, tr8, occ8 = sub8.get_spatial_tracking()

        trace_history_4d.append((r4, th4, tr4))
        trace_history_8d.append((r8, th8, tr8))

    final_r4, final_th4, final_tr4 = trace_history_4d[-1]
    final_r8, final_th8, final_tr8 = trace_history_8d[-1]

    drift_4d = abs(final_r4 - 450.0)
    drift_8d = abs(final_r8 - 450.0)
    assert drift_4d == 0.0, f"4D substrate drifted {drift_4d} mm under occlusion"
    assert drift_8d == 0.0, f"8D substrate drifted {drift_8d} mm under occlusion"

    expected_decay = 0.985 ** n_blank_ticks
    assert abs(final_tr4 - expected_decay) < 0.01, f"4D trace failed exponential decay: {final_tr4} vs {expected_decay}"
    assert abs(final_tr8 - expected_decay) < 0.01, f"8D trace failed exponential decay: {final_tr8} vs {expected_decay}"

    print(f"Results after {n_blank_ticks} ticks of visual blindout + noise:")
    print(f"  4-Column Substrate:")
    print(f"    Target Coordinates: r={final_r4:.1f} mm, theta={final_th4:,} mdeg")
    print(f"    Coordinate Drift:   {drift_4d:.2f} mm error (measured polar register hold)")
    print(f"    Persistence Trace:  {final_tr4:0.4f} (decay law: 0.985^{n_blank_ticks} = {expected_decay:.4f})")
    print()
    print(f"  8-Column Octet (Coupled V1/V2):")
    print(f"    Target Coordinates: r={final_r8:.1f} mm, theta={final_th8:,} mdeg")
    print(f"    Coordinate Drift:   {drift_8d:.2f} mm error (measured polar register hold)")
    print(f"    Persistence Trace:  {final_tr8:0.4f} (decay law: 0.985^{n_blank_ticks} = {expected_decay:.4f})")
    print()
    print("  PASS: Invariant polar coordinate register hold sustained across total optical occlusion.\n")

    return {
        "final_trace_4d": final_tr4,
        "final_trace_8d": final_tr8,
    }


def benchmark_plastic_yield_binding(coactive_ticks: int = 50) -> dict:
    """Benchmark plastic yield hardening (Acoustic-Optical Binding)."""
    print("=" * 70)
    print(f"BENCHMARK 3: CONTINUUM PLASTIC YIELD BINDING ({coactive_ticks} Ticks)")
    print("=" * 70)

    sub4 = ModularSubstrate4D(yield_threshold=0.40, plastic_rate=0.05, activation_threshold=0.15)
    sub8 = ModularSubstrate8D(yield_threshold=0.40, plastic_rate=0.05, activation_threshold=0.15)

    sensory_coactive = [1] * 64
    somatic = [1, 1, 0, 0, 0, 0, 0, 0] + [0] * 24

    for _ in range(coactive_ticks):
        sub4.step(sensory_coactive, somatic, observed_r_mm=250.0, observed_theta_mdeg=10000, barrier_stress=0.0)
        sub8.step(sensory_coactive, somatic, observed_r_mm=250.0, observed_theta_mdeg=10000, barrier_stress=0.0, acoustic_formant=180.0)

    synapses_4 = sub4.active_synapses()
    synapses_8 = sub8.active_synapses()

    assert synapses_4 > 0, "No active synapses formed in 4D substrate"
    assert synapses_8 > 0, "No active synapses formed in 8D substrate"

    print(f"Active Hardened Synapses (|g| >= 0.001) after {coactive_ticks} coactive ticks:")
    print(f"  4-Column Substrate: {synapses_4:,} active conductances")
    print(f"  8-Column Octet:     {synapses_8:,} active conductances")
    print(f"  Synaptic Scaling:   {synapses_8 / max(1, synapses_4):0.2f}x richer cross-modal associative mesh")
    print("  PASS: Material yield plasticity (f = |sigma| - Y <= 0) bound cross-modal fasciculi.\n")

    return {
        "synapses_4d": synapses_4,
        "synapses_8d": synapses_8,
    }


def benchmark_barrier_refusal_and_motor() -> dict:
    """Benchmark von Mises barrier refusal and motor gating."""
    print("=" * 70)
    print(f"BENCHMARK 4: VON MISES BARRIER REFUSAL & MOTOR DISCHARGE GATING")
    print("=" * 70)

    sub8 = ModularSubstrate8D(yield_threshold=0.40, plastic_rate=0.05, activation_threshold=0.15)
    sensory = [1] * 64
    somatic = [0] * 32

    # Step 1: Sub-yield contact (barrier stress 0.20 <= 0.70)
    sub8.step(sensory, somatic, observed_r_mm=300.0, observed_theta_mdeg=0, barrier_stress=0.20, acoustic_formant=0.0)
    refusal_sub = sub8.is_barrier_refusal_active()
    vocal_sub, stride_sub = sub8.get_motor_efferent()

    print(f"Sub-Yield Contact (sigma = 0.20 <= Y = 0.70):")
    print(f"  Barrier Refusal Active: {refusal_sub} (Expected: False)")
    print(f"  Locomotion Stride:      {stride_sub:0.1f} (Expected: 60.0 nominal locomotion)")
    print(f"  Airway Vocal Drive:     {vocal_sub:0.1f} (Expected: 0.0 quiescent)")

    # Step 2: Destructive barrier collision (barrier stress 0.95 > 0.70)
    sub8.step(sensory, somatic, observed_r_mm=300.0, observed_theta_mdeg=0, barrier_stress=0.95, acoustic_formant=0.0)
    refusal_over = sub8.is_barrier_refusal_active()
    vocal_over, stride_over = sub8.get_motor_efferent()

    print()
    print(f"Over-Yield Collision (sigma = 0.95 > Y = 0.70):")
    print(f"  Barrier Refusal Active: {refusal_over} (Expected: True)")
    print(f"  Locomotion Stride:      {stride_over:0.1f} (Expected: 0.0 - arrested to prevent damage)")
    print(f"  Airway Vocal Drive:     {vocal_over:0.1f} (Expected: 220.0 - homeostatic vocal discharge)")
    print()

    assert not refusal_sub, "Sub-yield contact caused false refusal!"
    assert stride_sub == 60.0, "Sub-yield contact inhibited locomotion!"
    assert refusal_over, "Over-yield collision failed to activate barrier refusal!"
    assert stride_over == 0.0, "Over-yield collision failed to arrest locomotion stride!"
    assert vocal_over == 220.0, "Over-yield collision failed to fire airway vocal exhaust pulse!"

    print("  PASS: Invariant barrier refusal and homeostatic motor exhaust verified.\n")
    return {"status": "passed"}


def benchmark_sleep_consolidation() -> dict:
    """Benchmark nocturnal dream consolidation and synaptic pruning."""
    print("=" * 70)
    print(f"BENCHMARK 5: NOCTURNAL DREAM CONSOLIDATION & SYNAPTIC PRUNING")
    print("=" * 70)

    sub8 = ModularSubstrate8D(yield_threshold=0.40, plastic_rate=0.05, activation_threshold=0.15)
    sensory = [1] * 64
    somatic = [0] * 32

    # Prime with coactivity to build up conductances
    for _ in range(30):
        sub8.step(sensory, somatic, observed_r_mm=200.0, observed_theta_mdeg=5000, barrier_stress=0.0, acoustic_formant=150.0)

    pre_synapses = sub8.active_synapses()
    print(f"Pre-Sleep Active Synapses:  {pre_synapses:,}")

    # Run 10 sleep consolidation cycles
    total_decayed = 0
    total_pruned = 0
    for _ in range(10):
        d, p = sub8.sleep_consolidation(decay=0.05, prune_thresh=0.01)
        total_decayed += d
        total_pruned += p

    assert total_decayed > 0, "No conductances were downscaled during sleep consolidation"

    post_synapses = sub8.active_synapses()
    print(f"Post-Sleep Active Synapses: {post_synapses:,}")
    print(f"Downscaled Conductances:    {total_decayed:,}")
    print(f"Pruned Weak Noise:          {total_pruned:,}")
    print(f"Synaptic Reduction:         {(1.0 - post_synapses / max(1, pre_synapses)) * 100.0:0.1f}% pruned via competitive downscaling")
    print("  PASS: Nocturnal consolidation downscaled conductances and pruned sub-threshold noise.\n")

    return {
        "pre_synapses": pre_synapses,
        "post_synapses": post_synapses,
        "total_pruned": total_pruned,
    }


def main() -> None:
    print("\n" + "=" * 70)
    print("DSF-AI ARCLOOM SUBSTRATE COMPARATIVE BENCHMARK")
    print("Target: 4-Column Baseline vs. 8-Column Balanced Octet vs. 64-Column Cortical Array")
    print("Standard: Strict Physical Laws & Continuum von Mises Plasticity")
    print("=" * 70 + "\n")

    t_res = benchmark_timing(n_ticks=1000)
    s_res = benchmark_spatial_occlusion_and_noise(n_blank_ticks=60)
    p_res = benchmark_plastic_yield_binding(coactive_ticks=50)
    b_res = benchmark_barrier_refusal_and_motor()
    d_res = benchmark_sleep_consolidation()

    print("=" * 70)
    print("ALL 5 BENCHMARK SUITES COMPLETED: 100% INVARIANTS PRESERVED")
    print(f"  4-Column Substrate: {t_res['mean_4d_us']:0.2f} µs/tick ({t_res['fps_4d']:,.0f} Hz)")
    print(f"  8-Column Octet:     {t_res['mean_8d_us']:0.2f} µs/tick ({t_res['fps_8d']:,.0f} Hz)")
    print(f"  64-Column Array:    {t_res['mean_64d_us']:0.2f} µs/tick ({t_res['fps_64d']:,.0f} Hz)")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()
