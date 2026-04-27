#!/usr/bin/env python3
"""
ArcLoom Vision Simulation — Mosaic Field Recognition
=====================================================
Tests whether the L0-L4 kernel + krimelack can discriminate objects
from camera frames WITHOUT training. Uses exact thresholds and
coupling weights from the FPGA Verilog.

This is NOT ML. No gradients, no loss functions, no training.
The kernel reads field structure. Krimelack commits and recalls.
"""

import numpy as np
from dataclasses import dataclass, field
from typing import List, Tuple, Optional
import json

# ============================================================
# Fixed-point helpers (16.16 format, matching Verilog)
# ============================================================
FP_SHIFT = 16
FP_ONE = 1 << FP_SHIFT  # 0x00010000 = 1.0

def fp(x: float) -> int:
    """Convert float to 16.16 fixed-point."""
    return int(x * FP_ONE)

def fp_to_float(x: int) -> float:
    """Convert 16.16 fixed-point to float."""
    return x / FP_ONE

def fp_mul(a: int, b: int) -> int:
    """16.16 multiply."""
    return (a * b) >> FP_SHIFT

def fp_clamp(x: int, lo: int = 0, hi: int = FP_ONE) -> int:
    """Clamp to [lo, hi]."""
    return max(lo, min(hi, x))


# ============================================================
# Ternary encoding (matching Verilog 2-bit: 00=null, 01=+1, 10=-1)
# ============================================================
TRIT_NULL = 0   # 0b00
TRIT_POS  = 1   # 0b01
TRIT_NEG  = 2   # 0b10

def trit_from_value(val: float, hi_thresh: float, lo_thresh: float) -> int:
    """BSIL-style threshold encoding."""
    if val > hi_thresh:
        return TRIT_POS
    elif val < lo_thresh:
        return TRIT_NEG
    return TRIT_NULL

def trit_sign(t: int) -> int:
    """Trit to signed value: +1, -1, or 0."""
    if t == TRIT_POS: return 1
    if t == TRIT_NEG: return -1
    return 0


# ============================================================
# L0: Boundary Detection
# ============================================================
# From arcloom_l0_boundary.v
L0_ALPHA1 = 1.0  # weight on |dF|
L0_ALPHA2 = 1.0  # weight on sigma
L0_ALPHA3 = 1.0  # weight on kappa
L0_TAU_D  = 0.20 # boundary threshold

def l0_boundary(dF: float, sigma: float, kappa: float) -> Tuple[float, bool]:
    """
    Structural boundary operator.
    D(t) = alpha1*|dF| + alpha2*sigma + alpha3*kappa
    Returns (D_t, is_boundary).
    """
    D_t = L0_ALPHA1 * abs(dF) + L0_ALPHA2 * sigma + L0_ALPHA3 * kappa
    return D_t, D_t > L0_TAU_D


# ============================================================
# L1: Gate Formation
# ============================================================
# From arcloom_l1_gate.v
L1_BETA1 = 1.0
L1_BETA2 = 1.0
L1_BETA3 = 1.0
L1_MIN_GATE_LEN = 4
L1_SHIFTS = [(4, 4, 4), (3, 3, 3), (2, 2, 2)]  # coarse, medium, fine

@dataclass
class Gate:
    T_k: float = 0.0       # duration
    V_k: float = 0.0       # structural volume
    R_k: float = 0.0       # accumulated relevance
    C_k: int = 1           # mosaic divergence {1,2,3}
    N_sum: int = 0          # negative space count
    T_count: int = 0        # sample count
    dF_max: float = -1e9
    dF_min: float = 1e9

def l1_gate_process(samples: List[dict]) -> List[Gate]:
    """
    Process a sequence of L0 outputs into gates.
    Each sample: {dF, sigma, kappa, abs_dF}
    Gates form between boundaries.
    """
    gates = []
    current = Gate()

    for s in samples:
        D_t, is_boundary = l0_boundary(s['dF'], s['sigma'], s['kappa'])

        if is_boundary and current.T_count >= L1_MIN_GATE_LEN:
            # Emit gate
            current.T_k = float(current.T_count)
            # Mosaic projection
            projections = set()
            for t_sh, v_sh, r_sh in L1_SHIFTS:
                p = (current.T_count >> t_sh,
                     int(current.V_k) >> v_sh,
                     int(current.R_k) >> r_sh)
                projections.add(p)
            current.C_k = len(projections)
            gates.append(current)
            current = Gate()
        elif is_boundary:
            current = Gate()
        else:
            # Accumulate within gate
            v_sample = L1_BETA1 * abs(s['dF']) + L1_BETA2 * s['sigma'] + L1_BETA3 * s['kappa']
            current.V_k += v_sample
            current.R_k += 1.0
            current.T_count += 1
            current.dF_max = max(current.dF_max, s['dF'])
            current.dF_min = min(current.dF_min, s['dF'])
            is_N = abs(s['dF']) < 0.001 and s['sigma'] < 0.001 and s['kappa'] < 0.001
            if is_N:
                current.N_sum += 1

    # Emit final gate if long enough
    if current.T_count >= L1_MIN_GATE_LEN:
        current.T_k = float(current.T_count)
        projections = set()
        for t_sh, v_sh, r_sh in L1_SHIFTS:
            p = (current.T_count >> t_sh,
                 int(current.V_k) >> v_sh,
                 int(current.R_k) >> r_sh)
            projections.add(p)
        current.C_k = len(projections)
        gates.append(current)

    return gates


# ============================================================
# L2: Interpretive Metrics
# ============================================================
# From arcloom_l2_metrics.v
L2_W_SHIFT  = 8
L2_CV_SHIFT = 8
L2_LAMBDA1  = 0.4   # mosaic divergence weight
L2_LAMBDA2  = 0.3   # contrast weight
L2_LAMBDA3  = 0.3   # negative space weight
L2_U_ANOMALY = 0.9

@dataclass
class Metrics:
    w_k: float = 0.0       # weight/salience
    CV_norm: float = 0.0   # contrast
    S_k: float = 0.0       # score
    U_k: float = 0.0       # uncertainty
    IAS_k: bool = False     # anomaly suppression
    C_k: int = 1

def l2_metrics(gate: Gate) -> Metrics:
    """Compute interpretive metrics from gate descriptor."""
    m = Metrics()
    m.C_k = gate.C_k

    # Weight from volume
    m.w_k = min(1.0, gate.V_k / (1 << L2_W_SHIFT))

    # Contrast from dF range
    dF_range = gate.dF_max - gate.dF_min if gate.T_count > 0 else 0
    m.CV_norm = min(1.0, max(0, dF_range) / (1 << L2_CV_SHIFT))

    # Score = salience
    m.S_k = m.w_k

    # Uncertainty
    N_gate = 1.0 if (2 * gate.N_sum >= gate.T_count) else 0.0
    L = 3  # lattice count
    u1 = L2_LAMBDA1 * (gate.C_k - 1) / (L - 1) if L > 1 else 0
    u2 = L2_LAMBDA2 * m.CV_norm
    u3 = L2_LAMBDA3 * N_gate
    m.U_k = min(1.0, max(0, u1 + u2 + u3))

    # Anomaly suppression
    m.IAS_k = m.U_k > L2_U_ANOMALY

    return m


# ============================================================
# L3: Resonance
# ============================================================
# From arcloom_l3_resonance.v
L3_H_MAX = 0.3125
L3_U_MAX = 0.85
L3_INV_5 = 0.2

def l3_resonance(metrics: Metrics, R_prev: float = 0.0) -> Tuple[float, float, bool, bool]:
    """
    Compute resonance.
    Returns (R_scalar, URF_k, g_k, Hyst_k).
    """
    # Resonance vector: [w, CV, S, 1/(1+C), 1-U]
    inv_1_plus_C = 1.0 / (1.0 + metrics.C_k)
    R_vec = [metrics.w_k, metrics.CV_norm, metrics.S_k, inv_1_plus_C, 1.0 - metrics.U_k]
    R_scalar = L3_INV_5 * sum(R_vec)

    # Hysteresis
    Hyst_k = abs(R_scalar - R_prev) > L3_H_MAX

    # Contextual gate
    g_k = (metrics.U_k <= L3_U_MAX) and (not metrics.IAS_k) and (not Hyst_k)

    # Unified resonance field
    URF_k = R_scalar if g_k else 0.0

    return R_scalar, URF_k, g_k, Hyst_k


# ============================================================
# L4: DSF (Decision Surface Vector)
# ============================================================
# From arcloom_l4_dsf.v
L4_EPS_D = 0.05

@dataclass
class DSF:
    D_k: int = 0           # direction: +1, 0, -1
    M_k: float = 0.0       # momentum
    R_rev: bool = False     # reversal
    U_star: float = 0.0    # adjusted uncertainty

def l4_dsf(R_k: float, R_prev: float, R_prev2: float, D_prev: int,
           Hyst: bool, U_k: float, IAS: bool) -> DSF:
    """Compute DSF tuple."""
    dsf = DSF()

    delta_R = R_k - R_prev
    if delta_R > L4_EPS_D:
        dsf.D_k = 1
    elif delta_R < -L4_EPS_D:
        dsf.D_k = -1
    else:
        dsf.D_k = 0

    dsf.M_k = R_k - 2 * R_prev + R_prev2
    dsf.R_rev = (dsf.D_k == 1 and D_prev == -1) or (dsf.D_k == -1 and D_prev == 1)

    # Adjusted uncertainty
    eta_H = 0.15
    eta_IAS = 0.20
    dsf.U_star = min(1.0, U_k + eta_H * (1 if Hyst else 0) + eta_IAS * (1 if IAS else 0))

    return dsf


# ============================================================
# BSIL: Image → Ternary Strands
# ============================================================
# Adapted from arcloom_ternary_loom.v BSIL thresholds
# For vision: each tile's field metrics become strand trits

def image_bsil(tile_metrics: dict) -> dict:
    """
    Encode a tile's field analysis into ternary strands.

    The key insight: BSIL thresholds create three zones per trit:
      +1 = above high threshold (strong presence)
      -1 = below low threshold (strong absence)
       0 = dead zone (ambiguous, not enough signal)

    Thresholds calibrated for normalized image metrics (0-1 range).
    Three trits per strand = coarse/medium/fine resolution.

    Output: dict of strand names → 3-trit lists
    """
    strands = {}

    # EDGE DENSITY: how many boundary pixels in this tile
    ed = tile_metrics.get('edge_density', 0)
    strands['distance'] = [
        trit_from_value(ed, 0.15, 0.02),  # coarse: any edges at all?
        trit_from_value(ed, 0.30, 0.08),  # medium: moderate edge count
        trit_from_value(ed, 0.50, 0.15),  # fine: edge-dense region
    ]

    # EDGE SHAPE: angle variance — low = round (uniform edges), high = angular (clustered)
    eav = tile_metrics.get('edge_angle_var', 0)
    strands['direction'] = [
        trit_from_value(eav, 0.15, 0.03),  # coarse: round vs angular
        trit_from_value(eav, 0.25, 0.08),  # medium
        trit_from_value(eav, 0.40, 0.15),  # fine
    ]

    # CONTRAST + COMPACTNESS: internal variation and edge-to-area ratio
    ct = tile_metrics.get('contrast', 0)
    cp = tile_metrics.get('compactness', 0)
    strands['accel'] = [
        trit_from_value(ct, 0.05, 0.01),   # coarse: any variation?
        trit_from_value(ct, 0.12, 0.03),   # medium
        trit_from_value(cp, 0.30, 0.05),   # fine: compactness (shape structure)
    ]

    # COLOR HUE: warm (red-dominant) vs cool (blue-dominant)
    r = tile_metrics.get('color_r', 0)
    g = tile_metrics.get('color_g', 0)
    b = tile_metrics.get('color_b', 0)
    hue = r - b  # positive = warm, negative = cool
    strands['cam_edge'] = [
        trit_from_value(hue, 0.03, -0.03),  # coarse
        trit_from_value(hue, 0.08, -0.08),  # medium
        trit_from_value(hue, 0.15, -0.15),  # fine
    ]

    # COLOR INTENSITY: bright vs dark
    intensity = (r + g + b) / 3.0
    strands['cam_motion'] = [
        trit_from_value(intensity, 0.65, 0.35),  # coarse: bright vs dark
        trit_from_value(intensity, 0.75, 0.25),  # medium
        trit_from_value(intensity, 0.85, 0.15),  # fine
    ]

    return strands


# ============================================================
# Loom: Ternary Coupling Settlement
# ============================================================
# From arcloom_ternary_loom.v — coupling weights and dead zone

DEAD_ZONE = 20

# Coupling weights from Verilog (simplified — using dominant weights)
# Context trit 0 weights: distance[0]=5, distance[1]=5, distance[2]=10,
#   direction=10, accel=30, cam_edge=10, cam_motion=10
# These are 8-bit signed weights per input trit

def loom_settle(strands: dict) -> dict:
    """
    Two-level combinational settlement.
    Level 1: context + momentum from 5 input strands
    Level 2: decision from all 7 strands

    Returns full loom state as dict of strand → 3 trits.
    """
    # Flatten input trits
    input_trits = []
    for name in ['distance', 'direction', 'accel', 'cam_edge', 'cam_motion']:
        input_trits.extend(strands[name])
    # 15 input trits

    # Coupling weights for context (3 trits, each weighted from 15 inputs)
    # From Verilog W_CTX_0, W_CTX_1, W_CTX_2
    ctx_weights = [
        # ctx[0]: broad context
        [5, 5, 10, 10, 0, 0, 30, 0, 0, 10, 0, 0, 10, 0, 0],
        # ctx[1]: medium context
        [0, 10, 5, 0, 10, 0, 0, 30, 0, 0, 10, 0, 0, 10, 0],
        # ctx[2]: fine context
        [0, 5, 10, 0, 0, 10, 0, 0, 30, 0, 0, 10, 0, 0, 10],
    ]

    # Coupling weights for momentum
    mmtm_weights = [
        [10, 0, 0, 5, 0, 0, 10, 0, 0, 5, 5, 0, 5, 5, 0],
        [0, 10, 0, 0, 5, 0, 0, 10, 0, 5, 0, 5, 5, 0, 5],
        [0, 0, 10, 0, 0, 5, 0, 0, 10, 0, 5, 5, 0, 5, 5],
    ]

    def compute_trit(weights, trits):
        total = 0
        for w, t in zip(weights, trits):
            total += w * trit_sign(t)
        if total > DEAD_ZONE:
            return TRIT_POS
        elif total < -DEAD_ZONE:
            return TRIT_NEG
        return TRIT_NULL

    # Level 1: settle context and momentum
    context = [compute_trit(ctx_weights[i], input_trits) for i in range(3)]
    momentum = [compute_trit(mmtm_weights[i], input_trits) for i in range(3)]

    # Level 2: decision from all 21 trits (15 input + 3 context + 3 momentum)
    all_trits = input_trits + context + momentum  # 21 trits

    # Decision weights (21 inputs each)
    dcsn_weights = [
        # decision[0]: steer — heavy on distance, context
        [15, 10, 5, 10, 5, 0, 5, 0, 0, 10, 5, 0, 5, 0, 0, 15, 10, 5, 10, 5, 0],
        # decision[1]: speed — heavy on accel, momentum
        [5, 0, 0, 5, 0, 0, 15, 10, 5, 5, 0, 0, 5, 0, 0, 5, 0, 0, 15, 10, 5],
        # decision[2]: confidence — balanced
        [5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 10, 10, 10, 10, 10, 10],
    ]

    decision = [compute_trit(dcsn_weights[i], all_trits) for i in range(3)]

    return {
        'distance': strands['distance'],
        'direction': strands['direction'],
        'accel': strands['accel'],
        'cam_edge': strands['cam_edge'],
        'cam_motion': strands['cam_motion'],
        'context': context,
        'momentum': momentum,
        'decision': decision,
    }


# ============================================================
# Krimelack: Structural Memory
# ============================================================
# From arcloom_krimelack.v
KRIM_DEPTH = 32
KRIM_U_SETTLE = 0.35
KRIM_R_COMMIT = 0.72

class Krimelack:
    def __init__(self):
        self.motifs = []  # list of 48-bit states (as 24-trit lists)
        self.labels = []  # optional label for debugging

    def state_to_trits(self, loom_state: dict) -> List[int]:
        """Flatten loom state to 24 trits."""
        trits = []
        for name in ['distance', 'direction', 'accel', 'cam_edge', 'cam_motion',
                      'context', 'momentum', 'decision']:
            trits.extend(loom_state[name])
        return trits

    def commit(self, loom_state: dict, u_star: float, resonance: float,
               safe_mode: bool = False, label: str = "") -> bool:
        """
        Attempt to commit a motif.
        Returns True if committed, False if rejected.
        """
        if safe_mode:
            return False
        if u_star > KRIM_U_SETTLE:
            return False
        if resonance < KRIM_R_COMMIT:
            return False

        trits = self.state_to_trits(loom_state)

        # Duplicate check
        for stored in self.motifs:
            if stored == trits:
                return False

        # Commit
        if len(self.motifs) >= KRIM_DEPTH:
            self.motifs.pop(0)  # circular buffer
            self.labels.pop(0)
        self.motifs.append(trits)
        self.labels.append(label)
        return True

    def recall(self, loom_state: dict) -> Tuple[Optional[int], int, str]:
        """
        Pattern match against stored motifs.
        Returns (best_index, match_score, label).
        """
        if not self.motifs:
            return None, 0, ""

        query = self.state_to_trits(loom_state)
        best_idx = -1
        best_score = 0

        for i, motif in enumerate(self.motifs):
            score = 0
            for q, m in zip(query, motif):
                if q != TRIT_NULL and m != TRIT_NULL and q == m:
                    score += 1
            if score > best_score:
                best_score = score
                best_idx = i

        if best_idx >= 0 and best_score > 0:
            return best_idx, best_score, self.labels[best_idx]
        return None, 0, ""

    def clear(self):
        """Reset memory."""
        self.motifs = []
        self.labels = []


# ============================================================
# Image Processing: Frame → Tiled Mosaics
# ============================================================

def frame_to_tiles(image: np.ndarray, tile_size: int = 16) -> List[dict]:
    """
    Tile an image and compute field metrics per tile.

    image: HxWx3 numpy array (RGB, 0-255)
    tile_size: pixels per tile edge

    Returns list of tile metric dicts.
    """
    h, w = image.shape[:2]
    tiles = []

    for y in range(0, h - tile_size + 1, tile_size):
        for x in range(0, w - tile_size + 1, tile_size):
            tile = image[y:y+tile_size, x:x+tile_size].astype(float) / 255.0

            # Grayscale for edge detection
            gray = np.mean(tile, axis=2)

            # Edge detection: Sobel-like gradients
            if gray.shape[0] > 1 and gray.shape[1] > 1:
                gy = np.diff(gray, axis=0)
                gx = np.diff(gray, axis=1)
                edge_mag = np.sqrt(gy[:, :-1]**2 + gx[:-1, :]**2)
                edge_density = np.mean(edge_mag > 0.1)

                # Dominant edge direction: horizontal vs vertical
                h_energy = np.sum(gx[:-1, :]**2)
                v_energy = np.sum(gy[:, :-1]**2)
                total = h_energy + v_energy + 1e-10
                edge_direction = (h_energy - v_energy) / total  # -1 to +1
            else:
                edge_density = 0
                edge_direction = 0

            # Color channels (mean per tile, 0-1)
            color_r = np.mean(tile[:, :, 0])
            color_g = np.mean(tile[:, :, 1])
            color_b = np.mean(tile[:, :, 2])

            # Contrast: std of grayscale
            contrast = np.std(gray)

            # Symmetry: left-right correlation
            left = gray[:, :gray.shape[1]//2]
            right = np.fliplr(gray[:, gray.shape[1]//2:gray.shape[1]//2*2])
            if left.shape == right.shape and left.size > 0:
                corr = np.corrcoef(left.flatten(), right.flatten())[0, 1]
                symmetry = max(0, corr) if not np.isnan(corr) else 0
            else:
                symmetry = 0

            # Edge orientation variance: uniform (circle) vs clustered (triangle/square)
            # Low variance = edges point in all directions (round shapes)
            # High variance = edges cluster at specific angles (angular shapes)
            if gray.shape[0] > 2 and gray.shape[1] > 2:
                gy_full = np.diff(gray, axis=0)[:, :-1]
                gx_full = np.diff(gray, axis=1)[:-1, :]
                magnitudes = np.sqrt(gy_full**2 + gx_full**2)
                mask = magnitudes > 0.05
                if np.sum(mask) > 3:
                    angles = np.arctan2(gy_full[mask], gx_full[mask])
                    edge_angle_var = np.var(angles) / (np.pi**2)  # normalize to ~0-1
                    edge_angle_var = min(1.0, edge_angle_var)
                else:
                    edge_angle_var = 0
            else:
                edge_angle_var = 0

            # Compactness: ratio of edge pixels to total area
            # Round shapes have lower edge-to-area ratio than angular shapes
            if edge_density > 0:
                compactness = contrast / (edge_density + 0.001)
                compactness = min(1.0, compactness)
            else:
                compactness = 0

            tiles.append({
                'x': x, 'y': y,
                'edge_density': edge_density,
                'edge_direction': edge_direction,
                'edge_angle_var': edge_angle_var,
                'compactness': compactness,
                'color_r': color_r,
                'color_g': color_g,
                'color_b': color_b,
                'contrast': contrast,
                'symmetry': symmetry,
            })

    return tiles


# ============================================================
# Full Pipeline: Image → Mosaic Signature → Krimelack
# ============================================================

def process_image(image: np.ndarray, tile_size: int = 16) -> List[dict]:
    """
    Run full kernel pipeline on an image.
    Returns list of loom states (one per tile).
    """
    tiles = frame_to_tiles(image, tile_size)
    loom_states = []

    for tile in tiles:
        # BSIL encode
        strands = image_bsil(tile)
        # Loom settle
        state = loom_settle(strands)
        state['tile_info'] = tile
        loom_states.append(state)

    return loom_states


def mosaic_signature(loom_states: List[dict]) -> List[int]:
    """
    Compute aggregate mosaic signature from all tile loom states.
    This is the object's structural fingerprint.

    Uses edge-weighted voting: tiles with more edges (object boundaries)
    contribute more to the signature than background tiles. This prevents
    the background from drowning out the object's field structure.
    """
    strand_names = ['distance', 'direction', 'accel', 'cam_edge', 'cam_motion',
                    'context', 'momentum', 'decision']

    # Weight each tile by its edge density — object tiles dominate
    weights = []
    for state in loom_states:
        ed = state.get('tile_info', {}).get('edge_density', 0)
        ct = state.get('tile_info', {}).get('contrast', 0)
        # Weight = edge_density + contrast (both indicate structural content)
        w = ed + ct + 0.01  # small floor so pure-background tiles still count a little
        weights.append(w)

    sig = []
    for name in strand_names:
        for i in range(3):
            scores = {TRIT_NULL: 0.0, TRIT_POS: 0.0, TRIT_NEG: 0.0}
            for j, state in enumerate(loom_states):
                t = state[name][i]
                scores[t] += weights[j]
            dominant = max(scores, key=scores.get)
            sig.append(dominant)

    return sig


def compare_signatures(sig_a: List[int], sig_b: List[int]) -> Tuple[int, int, float]:
    """
    Compare two mosaic signatures.
    Returns (matching_trits, comparable_trits, match_ratio).
    """
    matches = 0
    comparable = 0
    for a, b in zip(sig_a, sig_b):
        if a != TRIT_NULL and b != TRIT_NULL:
            comparable += 1
            if a == b:
                matches += 1

    ratio = matches / comparable if comparable > 0 else 0
    return matches, comparable, ratio


def signature_to_str(sig: List[int]) -> str:
    """Pretty-print a signature."""
    symbols = {TRIT_NULL: '0', TRIT_POS: '+', TRIT_NEG: '-'}
    names = ['dist', 'dirn', 'accl', 'cedg', 'cmot', 'ctxt', 'mmtm', 'dcsn']
    parts = []
    for i, name in enumerate(names):
        trits = sig[i*3:(i+1)*3]
        parts.append(f"{name}=[{''.join(symbols[t] for t in trits)}]")
    return ' '.join(parts)


# ============================================================
# Test harness
# ============================================================

def create_test_image(shape: str, color: Tuple[int, int, int],
                      size: int = 128, bg: Tuple[int, int, int] = (240, 240, 240)) -> np.ndarray:
    """
    Create a simple test image with a shape on a background.
    shape: 'circle', 'square', 'triangle', 'star'
    """
    img = np.full((size, size, 3), bg, dtype=np.uint8)
    cx, cy = size // 2, size // 2
    r = size // 3

    if shape == 'circle':
        for y in range(size):
            for x in range(size):
                if (x - cx)**2 + (y - cy)**2 < r**2:
                    img[y, x] = color

    elif shape == 'square':
        img[cy-r:cy+r, cx-r:cx+r] = color

    elif shape == 'triangle':
        for y in range(cy - r, cy + r):
            half_w = max(0, int(r * (y - (cy - r)) / (2 * r)))
            img[y, cx-half_w:cx+half_w] = color

    elif shape == 'star':
        # Simple 5-point star approximation
        for y in range(size):
            for x in range(size):
                dx, dy = x - cx, y - cy
                angle = np.arctan2(dy, dx)
                dist = np.sqrt(dx**2 + dy**2)
                # Star radius varies with angle
                star_r = r * (0.5 + 0.5 * abs(np.cos(2.5 * angle)))
                if dist < star_r:
                    img[y, x] = color

    return img


def run_discrimination_test():
    """
    Test: can the kernel discriminate between different objects?
    """
    print("=" * 60)
    print(" ArcLoom Vision Simulation — Object Discrimination Test")
    print("=" * 60)
    print()

    # Create test objects
    objects = {
        'brown_bear': create_test_image('circle', (139, 90, 43)),      # brown circle (bear-like)
        'white_cup': create_test_image('square', (255, 255, 255)),      # white square (cup-like)
        'red_triangle': create_test_image('triangle', (200, 30, 30)),   # red triangle
        'blue_star': create_test_image('star', (30, 30, 200)),          # blue star
        'brown_bear_2': create_test_image('circle', (139, 90, 43)),     # same bear again
    }

    signatures = {}
    krim = Krimelack()

    for name, img in objects.items():
        print(f"Processing: {name} ({img.shape})")
        loom_states = process_image(img, tile_size=16)
        sig = mosaic_signature(loom_states)
        signatures[name] = sig
        print(f"  Signature: {signature_to_str(sig)}")
        print(f"  Tiles: {len(loom_states)}")

        # Build aggregate loom state for krimelack
        agg_state = {
            'distance': sig[0:3],
            'direction': sig[3:6],
            'accel': sig[6:9],
            'cam_edge': sig[9:12],
            'cam_motion': sig[12:15],
            'context': sig[15:18],
            'momentum': sig[18:21],
            'decision': sig[21:24],
        }

        # Try to commit (low uncertainty, high resonance for test)
        committed = krim.commit(agg_state, u_star=0.2, resonance=0.8, label=name)
        print(f"  Krimelack commit: {'ACCEPTED' if committed else 'REJECTED (duplicate)'}")
        print()

    # Compare all pairs
    print("=" * 60)
    print(" Pairwise Discrimination")
    print("=" * 60)
    names = list(signatures.keys())
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            matches, comparable, ratio = compare_signatures(
                signatures[names[i]], signatures[names[j]])
            same = "SAME" if ratio > 0.8 else "DIFFERENT" if ratio < 0.5 else "SIMILAR"
            print(f"  {names[i]:20s} vs {names[j]:20s}: "
                  f"{matches}/{comparable} match ({ratio:.1%}) → {same}")

    print()

    # Test recall
    print("=" * 60)
    print(" Krimelack Recall Test")
    print("=" * 60)
    for name, sig in signatures.items():
        agg_state = {
            'distance': sig[0:3],
            'direction': sig[3:6],
            'accel': sig[6:9],
            'cam_edge': sig[9:12],
            'cam_motion': sig[12:15],
            'context': sig[15:18],
            'momentum': sig[18:21],
            'decision': sig[21:24],
        }
        idx, score, label = krim.recall(agg_state)
        print(f"  Query: {name:20s} → Match: {label:20s} (score={score}/24)")

    print()
    print(f"Krimelack has {len(krim.motifs)} stored motifs")


def run_rotation_test():
    """
    Test: does krimelack recall across rotations/angles?
    """
    print()
    print("=" * 60)
    print(" Rotation Invariance Test")
    print("=" * 60)
    print()

    krim = Krimelack()
    base_img = create_test_image('triangle', (200, 30, 30), size=128)

    # Commit the base view
    loom_states = process_image(base_img, tile_size=16)
    sig = mosaic_signature(loom_states)
    agg = {
        'distance': sig[0:3], 'direction': sig[3:6], 'accel': sig[6:9],
        'cam_edge': sig[9:12], 'cam_motion': sig[12:15],
        'context': sig[15:18], 'momentum': sig[18:21], 'decision': sig[21:24],
    }
    krim.commit(agg, u_star=0.2, resonance=0.8, label="triangle_front")
    print(f"Committed: triangle_front → {signature_to_str(sig)}")

    # Test with variations
    variations = {
        'shifted_right': np.roll(base_img, 20, axis=1),
        'shifted_down': np.roll(base_img, 20, axis=0),
        'brighter': np.clip(base_img.astype(int) + 30, 0, 255).astype(np.uint8),
        'darker': np.clip(base_img.astype(int) - 30, 0, 255).astype(np.uint8),
        'different_object': create_test_image('square', (30, 30, 200), size=128),
    }

    for vname, vimg in variations.items():
        loom_states = process_image(vimg, tile_size=16)
        sig = mosaic_signature(loom_states)
        agg = {
            'distance': sig[0:3], 'direction': sig[3:6], 'accel': sig[6:9],
            'cam_edge': sig[9:12], 'cam_motion': sig[12:15],
            'context': sig[15:18], 'momentum': sig[18:21], 'decision': sig[21:24],
        }
        idx, score, label = krim.recall(agg)
        base_matches, base_comp, base_ratio = compare_signatures(
            mosaic_signature(process_image(base_img, 16)), sig)
        print(f"  {vname:20s}: recall={label:20s} score={score}/24  "
              f"sig_match={base_ratio:.0%}")


if __name__ == '__main__':
    run_discrimination_test()
    run_rotation_test()
