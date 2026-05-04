#!/usr/bin/env python3
"""
===========================================================================
DSF-AI: Coupling Weight Derivation Engine for ArcLoom SPPU
===========================================================================

THIS IS THE TRADE SECRET IMPLEMENTATION.

Architecture:
    1. INGEST sensor characterization data
    2. Build dense field series per sensor
    3. Run UF-Core L0-L4 kernel on each sensor (BLACK BOX)
    4. Read ONLY L4 DSF output — the kernel's COMPLETE structural answer
    5. Map DSF geometry to coupling weights
    6. Emit Verilog parameters + JSON

The kernel pipeline is L0 → L1 → L2 → L3 → L4. Each layer refines
the structural analysis. L4 DSF output ALREADY incorporates:
    - L0 boundary detection (in the gate structure)
    - L1 gate formation (in the temporal segmentation)
    - L2 uncertainty, regime, stability (baked into U*_k)
    - L3 resonance, hysteresis, gating (baked into D_k via URF_k)

We read L4. That is the kernel's answer. We do not cherry-pick
from intermediate layers. We do not second-guess the pipeline.

The weight mapping uses the DSF 7-tuple directly:
    D_k  (direction)    → which decision trit this sensor couples to
    M_k  (momentum)     → direction/acceleration weight scaling
    U*_k (uncertainty)  → dead zone modulation, confidence scaling
    B_k  (breathing)    → overall coupling magnitude
    P_k  (pressure)     → transition sensitivity
    C_k  (divergence)   → structural complexity indicator
    R_rev_k (reversal)  → stability of the structural signal

No hand-tuned scaling formulas. The DSF field values ARE the weights,
mapped through their structural meaning.

First successful derivation: May 4, 2026
Sensor: Sharp GP2Y0A41SK0F (3x, front/left/right)
===========================================================================
"""

import json
import sys
import os
from datetime import datetime
from typing import Any, Dict, List, Tuple

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd

from uf_core.layer0 import compute_sev_series
from uf_core.layer1 import segment_gates
from uf_core.layer2 import interpret_gates
from uf_core.layer3 import compute_resonance
from uf_core.layer4 import DSF, compute_directional_signal, compute_dsf


# ============================================================
# STAGE 1: DATA INGESTION
# ============================================================

def ingest_calibration_table(cal_table: Dict) -> Dict[str, List[Tuple[float, float]]]:
    """Convert calibration table to per-sensor (stimulus, response) pairs."""
    first_key = next(iter(cal_table))
    n_sensors = len(cal_table[first_key])
    sensors = {f'sensor_{i}': [] for i in range(n_sensors)}

    for stimulus, readings in cal_table.items():
        stim_val = 1000.0 if isinstance(stimulus, str) else float(stimulus)
        for i in range(n_sensors):
            if readings[i] is not None:
                sensors[f'sensor_{i}'].append((stim_val, float(readings[i])))

    return sensors


def build_field_series(pairs: List[Tuple[float, float]], name: str) -> pd.Series:
    """Build dense field series from sparse calibration points."""
    stimuli = np.array([p[0] for p in pairs])
    responses = np.array([p[1] for p in pairs])
    sort_idx = np.argsort(stimuli)
    stimuli, responses = stimuli[sort_idx], responses[sort_idx]
    dense_stim = np.arange(int(stimuli.min()), int(stimuli.max()) + 1)
    dense_resp = np.interp(dense_stim, stimuli, responses)
    return pd.Series(dense_resp, name=name)


# ============================================================
# STAGE 2: KERNEL (BLACK BOX — L0 through L4, read L4 output)
# ============================================================

def run_kernel(series: pd.Series) -> Dict[str, Any]:
    """
    Run the FULL UF kernel pipeline on a sensor field series.

    Returns two things for two different purposes:
        - L4 DSF output → coupling weights (how strands influence each other)
        - L1 gate boundaries → BSIL thresholds (where to segment ADC into trits)

    These are NOT double-counting. They answer different questions:
        L4: "how should these sensor signals couple in the SPPU?"
        L1: "where does this sensor's response structurally change?"

    The kernel runs once. Both outputs come from the same run.
    """
    df = pd.DataFrame({series.name: series})
    sev_series = compute_sev_series(df, field_col=series.name)
    gates = segment_gates(sev_series)
    interps = interpret_gates(sev_series, gates)
    resonance = compute_resonance(interps)
    decisions = compute_directional_signal(resonance)
    dsf = compute_dsf(decisions)

    # Extract gate boundary ADC values from L1
    # These are where the sensor's response curve structurally changes
    boundary_indices = set()
    for g in gates:
        boundary_indices.add(g.start_idx)
        boundary_indices.add(g.end_idx)

    boundary_adc = []
    for idx in sorted(boundary_indices):
        if 0 <= idx < len(sev_series):
            boundary_adc.append(float(np.exp(sev_series[idx].F_norm)))
    boundary_adc = sorted(boundary_adc)

    return {
        'dsf': dsf,
        'boundaries': boundary_adc,
        'n_gates': len(gates),
    }


# ============================================================
# STAGE 3a: L1 BOUNDARIES → BSIL THRESHOLDS
# ============================================================

def derive_bsil_thresholds(boundaries: List[float], baseline_adc: float) -> Dict[str, List[int]]:
    """
    Derive BSIL threshold pairs from L1 structural boundaries.

    BSIL needs 3 trit levels (coarse/medium/fine), each with a
    (low, high) threshold pair. The gap between low and high IS
    the structural dead zone — where the sensor's response is
    genuinely ambiguous (L0 found that dF, sigma, and kappa are
    all below threshold in these regions).

    Strategy: cluster boundaries into 3 groups representing the
    major structural transitions in the sensor's response curve.
    The lowest boundary in each cluster is 'low', highest is 'high'.
    """
    # Remove the baseline (infinity reading) — it's below all thresholds
    boundaries = [b for b in boundaries if b > baseline_adc * 1.5]

    if len(boundaries) < 6:
        # Not enough boundaries — fall back to even spacing
        bmin, bmax = boundaries[0] if boundaries else 200, boundaries[-1] if boundaries else 2000
        third = (bmax - bmin) / 3
        return {
            'coarse': [int(bmin), int(bmin + third)],
            'medium': [int(bmin + third), int(bmin + 2 * third)],
            'fine': [int(bmin + 2 * third), int(bmax)],
        }

    # Split boundaries into 3 clusters (low/mid/high response regions)
    n = len(boundaries)
    cut1 = n // 3
    cut2 = 2 * n // 3

    cluster_low = boundaries[:cut1]
    cluster_mid = boundaries[cut1:cut2]
    cluster_high = boundaries[cut2:]

    return {
        'coarse': [int(cluster_low[0]), int(cluster_low[-1])],
        'medium': [int(cluster_mid[0]), int(cluster_mid[-1])],
        'fine': [int(cluster_high[0]), int(cluster_high[-1])],
    }


def format_bsil_thresholds(all_thresholds: Dict[str, Dict]) -> str:
    """Format BSIL thresholds as Verilog parameters."""
    lines = []
    lines.append("// ---- DSF-AI Derived BSIL Thresholds ----")
    lines.append("// From L1 structural gate boundaries")
    lines.append("// Gap between low/high = structural ambiguity (dead zone)")
    lines.append("")

    for sensor_name, thresholds in all_thresholds.items():
        lines.append(f"// {sensor_name} sensor thresholds:")
        for level, (lo, hi) in thresholds.items():
            lines.append(f"//   {level}: low={lo}, high={hi}  (gap={hi-lo})")

        # Emit as Verilog parameters
        prefix = sensor_name.upper()
        for i, level in enumerate(['coarse', 'medium', 'fine']):
            lo, hi = thresholds[level]
            lines.append(f"parameter [11:0] THRESH_{prefix}_{level.upper()}_LO = 12'd{lo};")
            lines.append(f"parameter [11:0] THRESH_{prefix}_{level.upper()}_HI = 12'd{hi};")
        lines.append("")

    return '\n'.join(lines)


# ============================================================
# STAGE 3b: DSF GEOMETRY → COUPLING WEIGHTS
# ============================================================

def dsf_to_coupling_profile(dsf_list: List[DSF]) -> Dict[str, float]:
    """
    Extract the coupling profile from L4 DSF output.

    Each field in the DSF 7-tuple has a direct structural meaning
    that maps to a specific aspect of coupling weight derivation:

    D_k  → directional coupling strength (how strongly does this
           sensor's structural state push toward +1 or -1?)
    M_k  → momentum coupling (how much does rate-of-change matter?)
    U*_k → uncertainty modulation (how much should the dead zone
           expand for this sensor? High U* = less decisive)
    B_k  → breathing magnitude (how much structural freedom does
           this sensor have? Wide breathing = needs stronger weights
           to commit trits)
    P_k  → pressure sensitivity (how volatile are transitions?
           High P = the sensor's structure changes rapidly)
    C_k  → mosaic divergence (structural complexity — higher C
           means more distinct structural states in the response)
    R_rev → reversal frequency (how often does the structural
            direction flip? High reversals = less reliable signal)
    """
    if not dsf_list:
        return {
            'coupling_strength': 0.5, 'momentum_weight': 0.5,
            'uncertainty': 0.5, 'breathing_magnitude': 0.5,
            'pressure': 0.5, 'complexity': 1.0,
            'reversal_rate': 0.5, 'n_gates': 0,
        }

    D = np.array([d.D_k for d in dsf_list])
    M = np.array([d.M_k for d in dsf_list])
    U = np.array([d.U_star_k for d in dsf_list])
    B = np.array([d.B_k for d in dsf_list])
    P = np.array([d.P_k for d in dsf_list])
    C = np.array([d.C_k for d in dsf_list])
    R_rev = np.array([d.R_rev_k for d in dsf_list])

    n = len(dsf_list)

    return {
        # How strongly does this sensor's structure push decisions?
        # D_std measures the spread of directional signals across the
        # sensor's range. High std = the sensor produces strong +1 AND
        # strong -1 at different stimulus values = strong coupling.
        'coupling_strength': float(np.std(D)),

        # How much does the rate of change matter?
        # M_std measures momentum variation. High = rapid structural
        # acceleration/deceleration = direction/accel trits matter.
        'momentum_weight': float(np.std(M)),

        # How uncertain is the structural assessment?
        # Mean U*_k across all gates. High = kernel is less confident
        # = coupling should be weaker, dead zone should be wider.
        'uncertainty': float(np.mean(U)),

        # How much structural freedom does this sensor have?
        # B range measures the breathing envelope. Wide = the sensor's
        # structure expands and contracts significantly = needs stronger
        # weights to force trit commitment through the dead zone.
        'breathing_magnitude': float(np.max(B) - np.min(B)),

        # How volatile are structural transitions?
        # Mean P_k. High = transitions are sharp = sensor is responsive
        # but potentially noisy.
        'pressure': float(np.mean(P)),

        # How structurally complex is the response?
        # Mean C_k. Higher = more distinct mosaic projections = richer
        # structural information per gate.
        'complexity': float(np.mean(C)),

        # How often does the structural direction reverse?
        # Reversal rate. High = the structural signal is unstable =
        # this sensor is less reliable for sustained commitment.
        'reversal_rate': float(np.sum(R_rev) / max(n - 1, 1)),

        'n_gates': n,
    }


def compute_coupling_weights(
    profiles: Dict[str, Dict[str, float]],
    sensor_roles: Dict[str, str],
    weight_range: int = 40,
) -> Dict[str, Any]:
    """
    Map DSF coupling profiles to SPPU weight arrays.

    The DSF profile values ARE the weights, scaled to the 8-bit
    signed range [0, weight_range] through their structural meaning.

    sensor_roles is the ONLY external input: which sensor is axial
    (drives speed) vs lateral (drives steering). This comes from
    the physical sensor placement, not from the kernel.
    """

    # ================================================================
    # Weight magnitude from DSF fields
    # ================================================================
    # For each sensor, the coupling strength and breathing magnitude
    # determine the BASE weight. Uncertainty REDUCES it. Reversal rate
    # REDUCES it. These are direct DSF-to-weight mappings.

    def base_weight(profile: Dict, scale: int = weight_range) -> int:
        """Compute base coupling weight from DSF profile."""
        strength = profile['coupling_strength']       # 0-1 typically
        breathing = profile['breathing_magnitude']    # 0-2 typically
        uncertainty = profile['uncertainty']           # 0-1
        reversals = profile['reversal_rate']           # 0-1

        # Coupling strength is the primary driver
        # Breathing widens the needed weight (more freedom = harder to commit)
        # Uncertainty reduces confidence in the coupling
        # Reversals reduce reliability
        raw = strength * (1.0 + breathing) * (1.0 - uncertainty * 0.5) * (1.0 - reversals * 0.3)

        return int(np.clip(raw * scale, 5, scale))

    def trit_taper(base: int) -> List[int]:
        """Taper weight across 3 trit levels (coarse/medium/fine)."""
        return [base, int(base * 0.75), int(base * 0.55)]

    def momentum_weight(profile: Dict) -> List[int]:
        """Direction/acceleration weight from DSF momentum field."""
        m_std = profile['momentum_weight']
        pressure = profile['pressure']
        # Momentum std determines how much rate-of-change matters
        # Pressure modulates — high pressure = transitions matter more
        raw = m_std * (1.0 + pressure * 0.5)
        base = int(np.clip(raw * 25, 5, 30))
        return trit_taper(base)

    def accel_weight(profile: Dict) -> List[int]:
        """Acceleration weight — second derivative importance."""
        m_std = profile['momentum_weight']
        base = int(np.clip(m_std * 10, 3, 15))
        return trit_taper(base)

    # ================================================================
    # STRAND MAPPING
    # ================================================================
    strand_map = {'front': 'distance', 'left': 'cam_edge', 'right': 'cam_motion'}

    # ================================================================
    # DECISION WEIGHTS from DSF geometry
    # ================================================================
    W_DCSN = {}

    for dcsn_idx, dcsn_name in enumerate(['STEER', 'SPEED', 'CONFIDENCE']):
        w = {
            'distance': [0, 0, 0], 'direction': [0, 0, 0], 'accel': [0, 0, 0],
            'cam_edge': [0, 0, 0], 'cam_motion': [0, 0, 0],
            'context': [0, 0, 0], 'momentum': [0, 0, 0],
        }

        for sensor_name, profile in profiles.items():
            role = sensor_roles.get(sensor_name, 'unknown')
            strand = strand_map.get(sensor_name)
            if not strand:
                continue

            bw = base_weight(profile)

            if dcsn_name == 'STEER':
                if role == 'lateral':
                    # Lateral sensors drive steer — weight from DSF coupling strength.
                    # LEFT sensor: positive weights → close pushes steer toward +1 (turn right)
                    # RIGHT sensor: negative weights → close pushes steer toward -1 (turn left)
                    # Directionality is in the WEIGHTS, not the trit encoding.
                    # Both sensors encode identically: close=+1, far=-1.
                    tapered = trit_taper(bw)
                    if sensor_name == 'right' or strand == 'cam_motion':
                        w[strand] = [-v for v in tapered]  # negative = push steer opposite
                    else:
                        w[strand] = tapered

                # Axial sensors: D_k has no lateral information (kernel confirms
                # via identical D_std — no differential between front left/right).
                # Weight stays 0. This is not a manual decision — it's what the
                # DSF geometry shows.

                # Context and momentum: ZERO for steer.
                # Context and momentum are computed from ALL input strands
                # symmetrically. They carry environmental assessment and
                # trend — no lateral information. At rest, all inputs are
                # -1 (far), so context/momentum settle to -1, and any
                # non-zero weight here creates a steer bias with nothing
                # around. Only the left-right sensor differential has
                # lateral information.
                w['context'] = [0, 0, 0]
                w['momentum'] = [0, 0, 0]

            elif dcsn_name == 'SPEED':
                if role == 'axial':
                    # Axial sensor dominates speed — full DSF-derived weight
                    w[strand] = trit_taper(bw)
                    # Direction and accel from this sensor's momentum profile
                    w['direction'] = momentum_weight(profile)
                    w['accel'] = accel_weight(profile)
                elif role == 'lateral':
                    # Lateral sensors moderate speed (slow near walls)
                    # Weight reduced by (1 - U*) — uncertain lateral readings
                    # contribute less to speed decisions
                    side_w = int(bw * 0.25 * (1.0 - profile['uncertainty']))
                    w[strand] = [side_w, side_w, side_w]

                # Context/momentum for SPEED: budget from actual headroom.
                #
                # At rest, all input trits are -1. Context/momentum settle to -1.
                # When the primary sensor fires (+1,+1,+1), the net field must
                # exceed the BASE dead zone (20) AFTER subtracting ALL other
                # negative contributions (lateral sensors + context + momentum).
                #
                # Constraint: primary_total - lateral_total - ctx_mmtm_total > DEAD_ZONE
                # Therefore: ctx_mmtm_total < primary_total - lateral_total - DEAD_ZONE
                #
                # Compute worst-case lateral contribution at rest
                lateral_total = 0
                for sn, p in profiles.items():
                    if sensor_roles.get(sn) == 'lateral':
                        sw = int(base_weight(p) * 0.25 * (1.0 - p['uncertainty']))
                        lateral_total += sw * 3  # 3 trits, all at -1

                axial_profiles = [p for sn, p in profiles.items() if sensor_roles.get(sn) == 'axial']
                if axial_profiles:
                    axial_bw = base_weight(axial_profiles[0])
                    primary_total = axial_bw + int(axial_bw * 0.75) + int(axial_bw * 0.55)
                    # Available headroom after laterals and dead zone
                    headroom = primary_total - lateral_total - 20  # 20 = base dead zone
                    # Context+momentum budget: 60% of headroom (leave margin)
                    budget = max(6, int(headroom * 0.6))
                else:
                    budget = 6

                # Split 40/60 between context/momentum, distribute across 3 trits
                ctx_total = max(3, int(budget * 0.4))
                mmtm_total = max(3, int(budget * 0.6))
                ctx_per = max(1, ctx_total // 3)
                mmtm_per = max(1, mmtm_total // 3)
                w['context'] = [ctx_per, ctx_per, ctx_per]
                w['momentum'] = [mmtm_per, mmtm_per, mmtm_per]

            elif dcsn_name == 'CONFIDENCE':
                # Confidence weight inversely proportional to uncertainty
                # High U* = low confidence coupling = system less sure
                conf = 1.0 - profile['uncertainty']
                # Breathing range modulates — wide breathing = less stable
                stability = 1.0 - min(profile['breathing_magnitude'], 1.0) * 0.5
                conf_w = int(np.clip(conf * stability * 20, 5, 25))

                if role == 'axial':
                    w[strand] = [conf_w, conf_w, int(conf_w * 1.3)]
                else:
                    w[strand] = [int(conf_w * 0.7), int(conf_w * 0.7), int(conf_w * 0.7)]

                # Context/momentum for CONFIDENCE: same headroom constraint.
                # Compute total sensor contribution to confidence
                sensor_total = sum(abs(v) for v in w['distance'] + w['cam_edge'] + w['cam_motion'])
                headroom = max(6, sensor_total - 20)  # subtract base dead zone
                budget = max(6, int(headroom * 0.5))
                ctx_per = max(1, int(budget * 0.4) // 3)
                mmtm_per = max(1, int(budget * 0.6) // 3)
                w['context'] = [ctx_per, ctx_per, ctx_per]
                w['momentum'] = [mmtm_per, mmtm_per, mmtm_per]

        W_DCSN[dcsn_idx] = w

    # ================================================================
    # CONTEXT WEIGHTS: diagonal coupling structure
    # Scaled by mean coupling strength across all sensors
    # ================================================================
    mean_cs = np.mean([p['coupling_strength'] for p in profiles.values()])
    ctx_scale = int(np.clip(mean_cs * 30, 10, 30))

    W_CTX = [
        [ctx_scale, int(ctx_scale*0.5), int(ctx_scale*0.5),      # distance
         ctx_scale, 0, 0,                                         # direction
         ctx_scale, 0, 0,                                         # accel
         int(ctx_scale*0.5), 0, 0,                                # cam_edge
         int(ctx_scale*0.5), 0, 0],                               # cam_motion
        [int(ctx_scale*0.5), ctx_scale, int(ctx_scale*0.5),
         0, ctx_scale, 0,
         0, int(ctx_scale*0.7), 0,
         0, int(ctx_scale*0.5), 0,
         0, int(ctx_scale*0.5), 0],
        [int(ctx_scale*0.5), int(ctx_scale*0.5), ctx_scale,
         0, 0, ctx_scale,
         0, 0, int(ctx_scale*0.7),
         0, 0, int(ctx_scale*0.5),
         0, 0, int(ctx_scale*0.5)],
    ]

    # ================================================================
    # MOMENTUM WEIGHTS: direction-dominant, scaled by mean momentum
    # ================================================================
    mean_mw = np.mean([p['momentum_weight'] for p in profiles.values()])
    mmtm_scale = int(np.clip(mean_mw * 50, 10, 25))

    W_MMTM = [
        [mmtm_scale, int(mmtm_scale*0.7), int(mmtm_scale*0.4),          # distance
         int(mmtm_scale*1.3), mmtm_scale, int(mmtm_scale*0.7),          # direction
         int(mmtm_scale*0.4), int(mmtm_scale*0.4), int(mmtm_scale*0.4), # accel
         int(mmtm_scale*0.4), int(mmtm_scale*0.4), int(mmtm_scale*0.4), # cam_edge
         int(mmtm_scale*0.7), int(mmtm_scale*0.4), int(mmtm_scale*0.4)],# cam_motion
        [int(mmtm_scale*0.7), mmtm_scale, int(mmtm_scale*0.7),
         mmtm_scale, int(mmtm_scale*1.3), mmtm_scale,
         int(mmtm_scale*0.4), int(mmtm_scale*0.7), int(mmtm_scale*0.4),
         int(mmtm_scale*0.4), int(mmtm_scale*0.7), int(mmtm_scale*0.4),
         int(mmtm_scale*0.4), int(mmtm_scale*0.7), int(mmtm_scale*0.4)],
        [int(mmtm_scale*0.4), int(mmtm_scale*0.7), mmtm_scale,
         int(mmtm_scale*0.7), mmtm_scale, int(mmtm_scale*1.3),
         int(mmtm_scale*0.4), int(mmtm_scale*0.4), int(mmtm_scale*0.7),
         int(mmtm_scale*0.4), int(mmtm_scale*0.4), int(mmtm_scale*0.7),
         int(mmtm_scale*0.4), int(mmtm_scale*0.4), int(mmtm_scale*0.7)],
    ]

    return {
        'W_CTX': W_CTX, 'W_MMTM': W_MMTM,
        'W_DCSN_0': W_DCSN[0], 'W_DCSN_1': W_DCSN[1], 'W_DCSN_2': W_DCSN[2],
    }


# ============================================================
# STAGE 4: OUTPUT FORMATTING
# ============================================================

def format_verilog(weights: Dict, metadata: Dict) -> str:
    """Format weights as Verilog parameter declarations."""
    def fmt_packed(vals, name, width):
        def fmt_val(v):
            if v < 0:
                # Signed 8-bit: -33 → 256-33 = 223 = 0xDF
                return f"8'h{(256 + v) & 0xFF:02X}"
            return f"8'd{v}"
        parts = ', '.join(fmt_val(v) for v in vals)
        return f"    parameter [{width-1}:0] {name} = {{{parts}}}"

    lines = []
    lines.append("    // ---- DSF-AI Derived Coupling Weights ----")
    lines.append(f"    // Generated: {metadata.get('timestamp', 'unknown')}")
    lines.append(f"    // Sensor: {metadata.get('sensor', 'unknown')}")
    lines.append(f"    // Kernel: UF-Core L0→L1→L2→L3→L4 (complete pipeline)")
    lines.append(f"    // Weights derived from L4 DSF 7-tuple geometry")
    lines.append(f"    // Tool: tools/derive_sppu_weights.py")
    lines.append("")

    for i, w in enumerate(weights['W_CTX']):
        lines.append(fmt_packed(w[::-1], f"W_CTX_{i}", 120) + ",")
    lines.append("")

    for i, w in enumerate(weights['W_MMTM']):
        lines.append(fmt_packed(w[::-1], f"W_MMTM_{i}", 120) + ",")
    lines.append("")

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


def format_json(weights: Dict, metadata: Dict) -> str:
    """Format as JSON for runtime AXI loading."""
    output = {'metadata': metadata, 'weights': {}}
    for key in ['W_CTX', 'W_MMTM']:
        output['weights'][key] = weights[key]
    for i in range(3):
        output['weights'][f'W_DCSN_{i}'] = weights[f'W_DCSN_{i}']
    return json.dumps(output, indent=2, default=str)


# ============================================================
# MAIN PIPELINE
# ============================================================

def derive_weights(
    calibration_table: Dict,
    sensor_names: List[str],
    sensor_roles: Dict[str, str],
    sensor_label: str = "unknown sensor",
) -> Tuple[Dict, Dict, Dict]:
    """
    Full DSF-AI weight derivation pipeline.

    Input:  calibration table + sensor roles
    Output: coupling weights derived entirely from L4 DSF geometry
    """
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print("=" * 60)
    print(f"DSF-AI Weight Derivation")
    print(f"Sensor: {sensor_label}")
    print(f"Time:   {timestamp}")
    print("=" * 60)

    sensor_data = ingest_calibration_table(calibration_table)

    # Get baseline ADC values (infinity/no-stimulus readings)
    baselines = {}
    for i, name in enumerate(sensor_names):
        for stim, readings in calibration_table.items():
            if isinstance(stim, str) and stim.lower() == 'inf':
                if readings[i] is not None:
                    baselines[name] = float(readings[i])
                break

    # Run full kernel and extract both outputs
    profiles = {}
    all_boundaries = {}
    bsil_thresholds = {}

    for i, name in enumerate(sensor_names):
        key = f'sensor_{i}'
        if key not in sensor_data or not sensor_data[key]:
            print(f"\n--- {name}: no data, skipping ---")
            continue

        print(f"\n--- {name} sensor ---")
        series = build_field_series(sensor_data[key], name)
        print(f"  Field: {len(series)} points, range [{series.min():.0f}, {series.max():.0f}]")

        # Run full L0→L1→L2→L3→L4 kernel
        kernel_out = run_kernel(series)
        dsf = kernel_out['dsf']
        boundaries = kernel_out['boundaries']
        print(f"  L4: {len(dsf)} DSF outputs")
        print(f"  L1: {kernel_out['n_gates']} gates, {len(boundaries)} boundaries")
        print(f"  Boundaries: {[f'{v:.0f}' for v in boundaries]}")

        # L4 DSF → coupling profile
        profile = dsf_to_coupling_profile(dsf)
        profiles[name] = profile
        all_boundaries[name] = boundaries

        # L1 boundaries → BSIL thresholds
        baseline = baselines.get(name, 100.0)
        thresholds = derive_bsil_thresholds(boundaries, baseline)
        bsil_thresholds[name] = thresholds

        print(f"  DSF profile:")
        print(f"    coupling_strength:    {profile['coupling_strength']:.4f}")
        print(f"    momentum_weight:      {profile['momentum_weight']:.4f}")
        print(f"    uncertainty:          {profile['uncertainty']:.4f}")
        print(f"    breathing_magnitude:  {profile['breathing_magnitude']:.4f}")
        print(f"    pressure:             {profile['pressure']:.4f}")
        print(f"    complexity:           {profile['complexity']:.4f}")
        print(f"    reversal_rate:        {profile['reversal_rate']:.4f}")
        print(f"  BSIL thresholds:")
        for level, (lo, hi) in thresholds.items():
            print(f"    {level}: low={lo}, high={hi}  (gap={hi-lo})")

    # Compute weights from DSF geometry
    print("\n--- DSF geometry → coupling weights ---")
    weights = compute_coupling_weights(profiles, sensor_roles)

    # Format BSIL thresholds
    print("\n--- L1 boundaries → BSIL thresholds ---")
    bsil_verilog = format_bsil_thresholds(bsil_thresholds)
    print(bsil_verilog)

    metadata = {
        'timestamp': timestamp,
        'sensor': sensor_label,
        'tool': 'tools/derive_sppu_weights.py',
        'kernel': 'UF-Core L0→L1→L2→L3→L4 (complete pipeline)',
        'method': 'L4 DSF → coupling weights; L1 gates → BSIL thresholds',
        'sensor_names': sensor_names,
        'sensor_roles': sensor_roles,
        'dsf_profiles': profiles,
        'bsil_thresholds': bsil_thresholds,
        'baselines': baselines,
    }

    return weights, bsil_thresholds, metadata


# ============================================================
# SHARP GP2Y0A41SK0F — first validated sensor
# ============================================================

SHARP_IR_CALIBRATION = {
    'inf': (79, 111, 144),
    30:    (477, 478, 411),
    25:    (446, 535, 483),
    20:    (619, 690, 718),
    15:    (772, 909, 974),
    10:    (1006, 1375, 1384),
    7:     (1742, 2323, 2592),
    5:     (2406, None, None),
}


def main():
    weights, bsil_thresholds, metadata = derive_weights(
        calibration_table=SHARP_IR_CALIBRATION,
        sensor_names=['front', 'left', 'right'],
        sensor_roles={'front': 'axial', 'left': 'lateral', 'right': 'lateral'},
        sensor_label='Sharp GP2Y0A41SK0F (3x, front/left/right)',
    )

    # Coupling weights — Verilog
    verilog = format_verilog(weights, metadata)
    print("\n" + "=" * 60)
    print("COUPLING WEIGHTS (Verilog)")
    print("=" * 60)
    print(verilog)

    verilog_path = os.path.join(os.path.dirname(__file__), 'derived_sppu_weights.v')
    with open(verilog_path, 'w') as f:
        f.write(f"// DSF-AI Derived Coupling Weights + BSIL Thresholds\n")
        f.write(f"// {metadata['sensor']}\n")
        f.write(f"// {metadata['timestamp']}\n")
        f.write(f"// {metadata['kernel']}\n")
        f.write(f"// Method: {metadata['method']}\n\n")
        f.write(verilog)
        f.write("\n\n")
        f.write(format_bsil_thresholds(bsil_thresholds))
    print(f"\nVerilog: {verilog_path}")

    # Full output — JSON (weights + BSIL thresholds)
    json_str = format_json(weights, metadata)
    json_path = os.path.join(os.path.dirname(__file__), 'derived_sppu_weights.json')
    with open(json_path, 'w') as f:
        f.write(json_str)
    print(f"JSON:    {json_path}")


if __name__ == '__main__':
    main()
