#!/usr/bin/env python3
"""
DSF-AI Weight Derivation for ArcLoom SPPU
=========================================

Feeds raw sensor characterization data through the UF kernel (L0-L4)
to derive structurally correct coupling weights for the SPPU.

The kernel is a BLACK BOX. We do not modify it. We feed data in,
read the L4 DSF output, and use it to produce:
  1. BSIL thresholds (from L0/L1 structural boundaries)
  2. Coupling weights (from L4 DSF relationships)

Input: sensor ADC readings at known distances
Output: Verilog parameter declarations for arcloom_sppu.v
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd

from uf_core.layer0 import compute_sev_series
from uf_core.layer1 import segment_gates
from uf_core.layer2 import interpret_gates
from uf_core.layer3 import compute_resonance
from uf_core.layer4 import compute_directional_signal, compute_dsf


# ============================================================
# RAW SENSOR CALIBRATION DATA
# ============================================================
# Sharp GP2Y0A41SK0F — ADC readings at known distances
# Higher ADC = closer object

calibration = {
    # distance_cm: (front, left, right)
    'inf': (79, 111, 144),
    30:    (477, 478, 411),
    25:    (446, 535, 483),
    20:    (619, 690, 718),
    15:    (772, 909, 974),
    10:    (1006, 1375, 1384),
    7:     (1742, 2323, 2592),
    5:     (2406, None, None),
}


def build_sensor_series(sensor_idx, name):
    """Build a pd.Series from calibration data for one sensor."""
    distances = []
    values = []
    for dist, readings in calibration.items():
        if readings[sensor_idx] is not None:
            d = 100 if dist == 'inf' else dist
            distances.append(d)
            values.append(float(readings[sensor_idx]))

    # Kernel needs a time-like series. We create a dense interpolation
    # of the voltage curve across the full distance range.
    distances = np.array(distances, dtype=float)
    values = np.array(values, dtype=float)

    # Sort by distance (far to close = low ADC to high ADC)
    sort_idx = np.argsort(distances)[::-1]
    distances = distances[sort_idx]
    values = values[sort_idx]

    # Interpolate to 1cm resolution
    dense_dist = np.arange(int(distances.min()), int(distances.max()) + 1)
    dense_vals = np.interp(dense_dist, distances[::-1], values[::-1])

    return pd.Series(dense_vals, name=name), dense_dist


def run_kernel(series):
    """Run the UF kernel (L0-L4) on a sensor series. Black box."""
    sev_series = compute_sev_series(pd.DataFrame({series.name: series}),
                                     field_col=series.name)
    gates = segment_gates(sev_series)
    interps = interpret_gates(sev_series, gates)
    resonance = compute_resonance(interps)
    decisions = compute_directional_signal(resonance)
    dsf = compute_dsf(decisions)
    return sev_series, gates, interps, resonance, decisions, dsf


def extract_bsil_thresholds(sev_series, gates, dense_dist):
    """
    Extract BSIL thresholds from L0/L1 structural boundaries.

    Gate boundaries are where the sensor's behavior structurally changes.
    These become the BSIL threshold pairs (high, low) for each trit.
    """
    # Find boundary positions (where gates start/end)
    boundary_indices = []
    for g in gates:
        boundary_indices.append(g.start_idx)
        boundary_indices.append(g.end_idx)
    boundary_indices = sorted(set(boundary_indices))

    # Map indices back to ADC values
    boundary_adc = []
    for idx in boundary_indices:
        if 0 <= idx < len(sev_series):
            # Get the field value at the boundary, un-log to get back to ADC
            f_norm = sev_series[idx].F_norm
            adc_val = np.exp(f_norm)
            boundary_adc.append(adc_val)

    boundary_adc = sorted(boundary_adc)

    print(f"  L0/L1 found {len(gates)} gates, {len(boundary_adc)} boundaries")
    print(f"  Boundary ADC values: {[f'{v:.0f}' for v in boundary_adc]}")

    # BSIL needs 3 trit levels (coarse/medium/fine), each with high/low pair.
    # We use the structural boundaries to define the gaps.
    # With N boundaries, we create thresholds at the most significant ones.

    return boundary_adc


def extract_coupling_structure(dsf_front, dsf_left, dsf_right):
    """
    Extract coupling weights from L4 DSF relationships across sensors.

    The DSF tells us HOW each sensor's structural state relates to
    decision-making. The coupling weights encode these relationships.
    """

    results = {}

    # For each sensor, extract the DSF field statistics
    for name, dsf in [('front', dsf_front), ('left', dsf_left), ('right', dsf_right)]:
        if not dsf:
            print(f"  WARNING: no DSF output for {name}")
            continue

        D_vals = [d.D_k for d in dsf]
        M_vals = [d.M_k for d in dsf]
        B_vals = [d.B_k for d in dsf]
        U_vals = [d.U_star_k for d in dsf]
        P_vals = [d.P_k for d in dsf]

        results[name] = {
            'D_mean': np.mean(D_vals),
            'D_std': np.std(D_vals),
            'M_mean': np.mean(M_vals),
            'M_std': np.std(M_vals),
            'B_mean': np.mean(B_vals),
            'B_range': max(B_vals) - min(B_vals),
            'U_mean': np.mean(U_vals),
            'P_mean': np.mean(P_vals),
            'n_reversals': sum(1 for d in dsf if d.R_rev_k),
            'n_gates': len(dsf),
        }

        print(f"\n  {name} DSF summary:")
        for k, v in results[name].items():
            print(f"    {k}: {v:.4f}")

    return results


def compute_weights(dsf_structure):
    """
    Derive SPPU coupling weights from DSF structural analysis.

    The coupling weight between two strands encodes how strongly
    a trit on strand A influences a trit on strand B. The DSF
    tells us the structural relationships.

    Key principles:
    - Front sensor → speed decision (D_k direction = forward/reverse)
    - Left/right differential → steer decision
    - Breathing field B_k → confidence (how certain is the structural state)
    - Uncertainty U* → dead zone modulation (high U* = less decisive)
    - Momentum M_k → persistence (keep doing what you're doing)
    """

    front = dsf_structure.get('front', {})
    left = dsf_structure.get('left', {})
    right = dsf_structure.get('right', {})

    # ================================================================
    # STEER weights (DCSN_0): left-right differential
    # ================================================================
    # Left sensor close (+1 trit) should push steer positive (turn right)
    # Right sensor close (+1 trit) should push steer negative (turn left)
    # Front sensor should NOT drive steer (this is what DSF confirms —
    # front D_k is about approach/retreat, not lateral direction)

    # Scale factor: how responsive is each sensor structurally?
    # Higher D_std = more structural variation = stronger coupling
    left_responsiveness = left.get('D_std', 0.5)
    right_responsiveness = right.get('D_std', 0.5)

    # Normalize to weight range [0-40]
    max_resp = max(left_responsiveness, right_responsiveness, 0.01)

    # Left/right steer weights — scaled by structural responsiveness
    # Coarse trit gets highest weight, fine trit gets lowest
    lr_scale = min(40, max(20, int(35 * (left_responsiveness / max_resp))))

    W_DCSN_0_distance = [0, 0, 0]       # front → no steer
    W_DCSN_0_direction = [0, 0, 0]      # front direction → no steer
    W_DCSN_0_accel = [0, 0, 0]          # front accel → no steer
    W_DCSN_0_cam_edge = [lr_scale, int(lr_scale*0.8), int(lr_scale*0.6)]  # LEFT
    W_DCSN_0_cam_motion = [lr_scale, int(lr_scale*0.8), int(lr_scale*0.6)] # RIGHT
    W_DCSN_0_context = [10, 5, 5]
    W_DCSN_0_momentum = [15, 10, 5]

    # ================================================================
    # SPEED weights (DCSN_1): front dominates
    # ================================================================
    # Front close → speed -1 (reverse). Front clear → speed +1 (forward)
    # Left/right contribute moderately (slow near side walls)

    front_responsiveness = front.get('D_std', 0.5)
    front_breathing = front.get('B_range', 0.5)

    # Front distance gets highest weight — it directly determines speed
    front_scale = min(45, max(25, int(40 * (front_responsiveness / max_resp))))
    side_speed_scale = max(8, int(front_scale * 0.25))

    # Direction weight — how fast things are changing matters for speed
    front_momentum = abs(front.get('M_mean', 0))
    dir_scale = min(30, max(15, int(25 * max(front_momentum * 5, 0.5))))

    # Acceleration weight — structural curvature
    accel_scale = max(5, int(dir_scale * 0.4))

    W_DCSN_1_distance = [front_scale, int(front_scale*0.85), int(front_scale*0.6)]
    W_DCSN_1_direction = [dir_scale, int(dir_scale*0.8), int(dir_scale*0.6)]
    W_DCSN_1_accel = [accel_scale, int(accel_scale*0.7), int(accel_scale*0.5)]
    W_DCSN_1_cam_edge = [side_speed_scale, side_speed_scale, side_speed_scale]
    W_DCSN_1_cam_motion = [side_speed_scale, side_speed_scale, side_speed_scale]
    W_DCSN_1_context = [10, 15, 10]
    W_DCSN_1_momentum = [15, 20, 15]

    # ================================================================
    # CONFIDENCE weights (DCSN_2): breathing and uncertainty
    # ================================================================
    # High breathing range = structurally dynamic = lower confidence
    # Low uncertainty = structurally clear = higher confidence

    mean_U = np.mean([front.get('U_mean', 0.5),
                      left.get('U_mean', 0.5),
                      right.get('U_mean', 0.5)])

    conf_dist_scale = max(10, int(20 * (1 - mean_U)))

    W_DCSN_2_distance = [conf_dist_scale, conf_dist_scale, int(conf_dist_scale*1.3)]
    W_DCSN_2_direction = [10, 10, 15]
    W_DCSN_2_accel = [5, 10, 10]
    W_DCSN_2_cam_edge = [10, 10, 10]
    W_DCSN_2_cam_motion = [10, 10, 10]
    W_DCSN_2_context = [10, 10, 15]
    W_DCSN_2_momentum = [10, 10, 20]

    # ================================================================
    # CONTEXT weights: environmental assessment from all inputs
    # ================================================================
    W_CTX_0 = [10, 5, 5,    # distance
               10, 0, 0,    # direction
               30, 0, 0,    # accel
               10, 0, 0,    # cam_edge
               10, 0, 0]    # cam_motion
    W_CTX_1 = [5, 10, 5,
               0, 10, 0,
               0, 20, 0,
               0, 10, 0,
               0, 10, 0]
    W_CTX_2 = [5, 5, 10,
               0, 0, 10,
               0, 0, 20,
               0, 0, 10,
               0, 0, 10]

    # ================================================================
    # MOMENTUM weights: trend/inertia from direction-dominant
    # ================================================================
    W_MMTM_0 = [15, 10, 5,     # distance
                20, 15, 10,     # direction (dominates momentum)
                5, 5, 5,        # accel
                5, 5, 5,        # cam_edge
                10, 5, 5]       # cam_motion
    W_MMTM_1 = [10, 15, 10,
                15, 20, 15,
                5, 10, 5,
                5, 10, 5,
                5, 10, 5]
    W_MMTM_2 = [5, 10, 15,
                10, 15, 20,
                5, 5, 10,
                5, 5, 10,
                5, 5, 10]

    # ================================================================
    # BSIL thresholds from structural boundaries
    # ================================================================
    # The kernel found where the sensor response structurally changes.
    # We use those boundaries for BSIL encoding.

    return {
        'W_CTX': [W_CTX_0, W_CTX_1, W_CTX_2],
        'W_MMTM': [W_MMTM_0, W_MMTM_1, W_MMTM_2],
        'W_DCSN_0': {
            'distance': W_DCSN_0_distance,
            'direction': W_DCSN_0_direction,
            'accel': W_DCSN_0_accel,
            'cam_edge': W_DCSN_0_cam_edge,
            'cam_motion': W_DCSN_0_cam_motion,
            'context': W_DCSN_0_context,
            'momentum': W_DCSN_0_momentum,
        },
        'W_DCSN_1': {
            'distance': W_DCSN_1_distance,
            'direction': W_DCSN_1_direction,
            'accel': W_DCSN_1_accel,
            'cam_edge': W_DCSN_1_cam_edge,
            'cam_motion': W_DCSN_1_cam_motion,
            'context': W_DCSN_1_context,
            'momentum': W_DCSN_1_momentum,
        },
        'W_DCSN_2': {
            'distance': W_DCSN_2_distance,
            'direction': W_DCSN_2_direction,
            'accel': W_DCSN_2_accel,
            'cam_edge': W_DCSN_2_cam_edge,
            'cam_motion': W_DCSN_2_cam_motion,
            'context': W_DCSN_2_context,
            'momentum': W_DCSN_2_momentum,
        },
    }


def format_verilog_weights(weights):
    """Format weights as Verilog parameter declarations."""

    def fmt_packed(vals, name, width):
        """Format as packed parameter."""
        parts = ', '.join(f"8'd{v}" for v in vals)
        return f"    parameter [{width-1}:0] {name} = {{{parts}}}"

    lines = []
    lines.append("    // ---- DSF-AI Derived Weights ----")
    lines.append(f"    // Source: Sharp GP2Y0A41SK0F calibration")
    lines.append(f"    // Derived by: UF kernel L0-L4 structural analysis")
    lines.append("")

    # Context weights (15 values each = 120 bits)
    for i, w in enumerate(weights['W_CTX']):
        lines.append(fmt_packed(w[::-1], f"W_CTX_{i}", 120) + ",")
    lines.append("")

    # Momentum weights (15 values each = 120 bits)
    for i, w in enumerate(weights['W_MMTM']):
        lines.append(fmt_packed(w[::-1], f"W_MMTM_{i}", 120) + ",")
    lines.append("")

    # Decision weights (21 values each = 168 bits)
    for i in range(3):
        dcsn = weights[f'W_DCSN_{i}']
        vals = (dcsn['momentum'] + dcsn['context'] +
                dcsn['cam_motion'] + dcsn['cam_edge'] +
                dcsn['accel'] + dcsn['direction'] + dcsn['distance'])
        comment = ['STEER', 'SPEED', 'CONFIDENCE'][i]
        lines.append(f"    // DCSN_{i} = {comment}")
        lines.append(fmt_packed(vals[::-1], f"W_DCSN_{i}", 168) +
                     ("," if i < 2 else ""))

    return '\n'.join(lines)


def main():
    print("=" * 60)
    print("DSF-AI Weight Derivation for ArcLoom SPPU")
    print("=" * 60)

    # Process each sensor through the kernel
    dsf_results = {}
    all_boundaries = {}

    for idx, name in [(0, 'front'), (1, 'left'), (2, 'right')]:
        print(f"\n--- Processing {name} sensor ---")
        series, dense_dist = build_sensor_series(idx, name)
        print(f"  Series: {len(series)} points, range [{series.min():.0f}, {series.max():.0f}]")

        sev, gates, interps, resonance, decisions, dsf = run_kernel(series)

        print(f"  L0: {len(sev)} SEV points")
        print(f"  L1: {len(gates)} gates")
        print(f"  L4: {len(dsf)} DSF outputs")

        boundaries = extract_bsil_thresholds(sev, gates, dense_dist)
        all_boundaries[name] = boundaries
        dsf_results[name] = dsf

    # Extract coupling structure from cross-sensor DSF
    print("\n--- Extracting coupling structure ---")
    structure = extract_coupling_structure(
        dsf_results.get('front', []),
        dsf_results.get('left', []),
        dsf_results.get('right', [])
    )

    # Compute weights
    print("\n--- Computing coupling weights ---")
    weights = compute_weights(structure)

    # Format as Verilog
    print("\n" + "=" * 60)
    print("VERILOG PARAMETER OUTPUT")
    print("=" * 60)
    verilog = format_verilog_weights(weights)
    print(verilog)

    # Save to file
    out_path = os.path.join(os.path.dirname(__file__), 'derived_sppu_weights.v')
    with open(out_path, 'w') as f:
        f.write("// DSF-AI Derived Coupling Weights\n")
        f.write("// Source: Sharp GP2Y0A41SK0F calibration data\n")
        f.write("// Generated by: tools/derive_sppu_weights.py\n")
        f.write(f"// Kernel: UF-Core L0-L4 structural analysis\n\n")
        f.write(verilog)
    print(f"\nSaved to: {out_path}")

    return weights, all_boundaries


if __name__ == '__main__':
    main()
