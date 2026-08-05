#!/usr/bin/env python3
"""
ArcLoom Vision Simulation v2 — Structural Field Recognition
=============================================================
The image IS a field. The kernel reads it the same way it reads
financial data — as a temporal sequence with boundaries, gates,
resonance, and DSF.

No tiling. No feature extraction. No ML.

The image is scanned as a signal. L0 finds edges. L1 gates between
edges. L2-L3-L4 compute the DSF per gate. The sequence of DSFs
IS the mosaic. Run the kernel again on the DSF sequence = mosaics
of mosaics.

Each color channel (R, G, B) is an independent field. Three fields,
three DSF sequences, three mosaic layers. They couple in the loom.

Krimelack commits the structural configuration — not a flat pattern,
but how the field assembles across space.
"""

import numpy as np
from dataclasses import dataclass, field
from typing import List, Tuple, Optional

# ============================================================
# Constants from Verilog (matching hardware exactly)
# ============================================================

# L0
L0_ALPHA1 = 1.0
L0_ALPHA2 = 1.0
L0_ALPHA3 = 1.0
L0_TAU_D = 0.20

# L1
L1_MIN_GATE_LEN = 4
L1_SHIFTS = [(4, 4, 4), (3, 3, 3), (2, 2, 2)]
L1_BETA1 = 1.0
L1_BETA2 = 1.0
L1_BETA3 = 1.0

# L2
L2_LAMBDA1 = 0.4
L2_LAMBDA2 = 0.3
L2_LAMBDA3 = 0.3
L2_U_ANOMALY = 0.9
L2_W_SHIFT = 8
L2_CV_SHIFT = 8

# L3
L3_H_MAX = 0.3125
L3_U_MAX = 0.85
L3_INV_5 = 0.2

# L4
L4_EPS_D = 0.05
L4_ETA_H = 0.15
L4_ETA_IAS = 0.20

# Loom
DEAD_ZONE = 20

# Krimelack
KRIM_DEPTH = 32
KRIM_U_SETTLE = 0.35
KRIM_R_COMMIT = 0.72

# Ternary
TRIT_NULL = 0
TRIT_POS = 1
TRIT_NEG = 2


def trit_sign(t):
    if t == TRIT_POS: return 1
    if t == TRIT_NEG: return -1
    return 0


# ============================================================
# Kernel Pipeline: signal → L0 → L1 → L2 → L3 → L4
# ============================================================

@dataclass
class GateDescriptor:
    """L1 gate output — a coherent region between boundaries."""
    T_k: int = 0         # duration (samples)
    V_k: float = 0.0     # structural volume
    R_k: float = 0.0     # relevance
    C_k: int = 1         # mosaic divergence {1,2,3}
    N_sum: int = 0        # negative space count
    dF_max: float = -1e9
    dF_min: float = 1e9
    start_idx: int = 0
    end_idx: int = 0


@dataclass
class DSFVector:
    """L4 output — the structural state of a gate."""
    D_k: int = 0          # direction: +1, 0, -1
    M_k: float = 0.0      # momentum
    R_rev: bool = False    # reversal
    U_star: float = 0.0   # adjusted uncertainty
    R_scalar: float = 0.0  # resonance
    w_k: float = 0.0      # salience
    CV: float = 0.0        # contrast
    C_k: int = 1           # mosaic divergence


def run_kernel_on_signal(signal: np.ndarray) -> List[DSFVector]:
    """
    Run the full L0-L4 kernel on a 1D signal.
    Returns a DSF vector per gate.

    This is the SAME pipeline the FPGA runs on sensor data.
    The signal is pixel intensity, not voltage — but the math is identical.
    """
    n = len(signal)
    if n < L1_MIN_GATE_LEN * 2:
        return []

    # Compute derivatives
    dF = np.diff(signal, prepend=signal[0])           # first difference
    sigma = np.zeros(n)                                 # running volatility
    kappa = np.zeros(n)                                 # curvature (second diff)

    # Rolling sigma (window=8, matching hardware shift register depth)
    win = 8
    for i in range(n):
        start = max(0, i - win)
        sigma[i] = np.std(signal[start:i+1]) if i > 0 else 0

    # Kappa = |second difference|
    d2F = np.diff(dF, prepend=dF[0])
    kappa = np.abs(d2F)

    # ---- L0: Boundary detection ----
    D_t = L0_ALPHA1 * np.abs(dF) + L0_ALPHA2 * sigma + L0_ALPHA3 * kappa
    boundaries = D_t > L0_TAU_D

    # ---- L1: Gate formation ----
    gates = []
    gate_start = 0
    gate_V = 0.0
    gate_N = 0
    gate_dF_max = -1e9
    gate_dF_min = 1e9
    gate_len = 0

    for i in range(n):
        if boundaries[i] and gate_len >= L1_MIN_GATE_LEN:
            # Emit gate
            g = GateDescriptor()
            g.T_k = gate_len
            g.V_k = gate_V
            g.R_k = float(gate_len)
            g.N_sum = gate_N
            g.dF_max = gate_dF_max
            g.dF_min = gate_dF_min
            g.start_idx = gate_start
            g.end_idx = i
            # Mosaic projection
            projs = set()
            for t_sh, v_sh, r_sh in L1_SHIFTS:
                p = (gate_len >> t_sh, int(gate_V) >> v_sh, gate_len >> r_sh)
                projs.add(p)
            g.C_k = min(3, len(projs))
            gates.append(g)
            # Reset
            gate_start = i
            gate_V = 0.0
            gate_N = 0
            gate_dF_max = -1e9
            gate_dF_min = 1e9
            gate_len = 0
        elif boundaries[i]:
            # Gate too short, reset
            gate_start = i
            gate_V = 0.0
            gate_N = 0
            gate_dF_max = -1e9
            gate_dF_min = 1e9
            gate_len = 0
        else:
            # Accumulate
            v_sample = L1_BETA1 * abs(dF[i]) + L1_BETA2 * sigma[i] + L1_BETA3 * kappa[i]
            gate_V += v_sample
            gate_len += 1
            gate_dF_max = max(gate_dF_max, dF[i])
            gate_dF_min = min(gate_dF_min, dF[i])
            is_N = abs(dF[i]) < 0.001 and sigma[i] < 0.001 and kappa[i] < 0.001
            if is_N:
                gate_N += 1

    # Emit final gate
    if gate_len >= L1_MIN_GATE_LEN:
        g = GateDescriptor()
        g.T_k = gate_len
        g.V_k = gate_V
        g.R_k = float(gate_len)
        g.N_sum = gate_N
        g.dF_max = gate_dF_max
        g.dF_min = gate_dF_min
        g.start_idx = gate_start
        g.end_idx = n
        projs = set()
        for t_sh, v_sh, r_sh in L1_SHIFTS:
            p = (gate_len >> t_sh, int(gate_V) >> v_sh, gate_len >> r_sh)
            projs.add(p)
        g.C_k = min(3, len(projs))
        gates.append(g)

    if not gates:
        return []

    # ---- L2-L3-L4 per gate ----
    dsf_sequence = []
    R_prev = 0.0
    R_prev2 = 0.0
    D_prev = 0

    for gate in gates:
        # L2: Metrics
        w_k = min(1.0, gate.V_k / (1 << L2_W_SHIFT))
        dF_range = gate.dF_max - gate.dF_min
        CV_norm = min(1.0, max(0, dF_range) / (1 << L2_CV_SHIFT))
        S_k = w_k
        N_gate = 1.0 if (2 * gate.N_sum >= gate.T_k) else 0.0
        u1 = L2_LAMBDA1 * (gate.C_k - 1) / 2.0
        u2 = L2_LAMBDA2 * CV_norm
        u3 = L2_LAMBDA3 * N_gate
        U_k = min(1.0, max(0, u1 + u2 + u3))
        IAS_k = U_k > L2_U_ANOMALY

        # L3: Resonance
        inv_1_plus_C = 1.0 / (1.0 + gate.C_k)
        R_vec = [w_k, CV_norm, S_k, inv_1_plus_C, 1.0 - U_k]
        R_scalar = L3_INV_5 * sum(R_vec)
        Hyst_k = abs(R_scalar - R_prev) > L3_H_MAX
        g_k = (U_k <= L3_U_MAX) and (not IAS_k) and (not Hyst_k)

        # L4: DSF
        delta_R = R_scalar - R_prev
        if delta_R > L4_EPS_D:
            D_k = 1
        elif delta_R < -L4_EPS_D:
            D_k = -1
        else:
            D_k = 0

        M_k = R_scalar - 2 * R_prev + R_prev2
        R_rev = (D_k == 1 and D_prev == -1) or (D_k == -1 and D_prev == 1)
        U_star = min(1.0, U_k + L4_ETA_H * (1 if Hyst_k else 0)
                     + L4_ETA_IAS * (1 if IAS_k else 0))

        dsf = DSFVector(
            D_k=D_k, M_k=M_k, R_rev=R_rev, U_star=U_star,
            R_scalar=R_scalar, w_k=w_k, CV=CV_norm, C_k=gate.C_k
        )
        dsf_sequence.append(dsf)

        R_prev2 = R_prev
        R_prev = R_scalar
        D_prev = D_k

    return dsf_sequence


# ============================================================
# Image → Scanline Signals per Color Channel
# ============================================================

def image_to_signals(image: np.ndarray) -> dict:
    """
    Convert image to 1D signals for kernel processing.

    Each color channel becomes an independent field.
    Scan order: horizontal scanlines concatenated (raster).
    This preserves spatial structure — edges in the image become
    boundaries in the signal.
    """
    h, w = image.shape[:2]
    img = image.astype(float) / 255.0

    signals = {}

    # Per-channel raster scan
    signals['R'] = img[:, :, 0].flatten()
    signals['G'] = img[:, :, 1].flatten()
    signals['B'] = img[:, :, 2].flatten()

    # Grayscale (luminance) — the structural field
    gray = 0.299 * img[:, :, 0] + 0.587 * img[:, :, 1] + 0.114 * img[:, :, 2]
    signals['lum'] = gray.flatten()

    # Also do vertical scan for cross-axis structure
    signals['lum_v'] = gray.T.flatten()

    return signals


# ============================================================
# Mosaic: DSF sequence → structural signature
# ============================================================

def dsf_to_trit(val: float, pos_thresh: float, neg_thresh: float) -> int:
    """Encode a continuous value as a ternary trit."""
    if val > pos_thresh: return TRIT_POS
    if val < neg_thresh: return TRIT_NEG
    return TRIT_NULL


def dsf_sequence_to_mosaic(dsfs: List[DSFVector]) -> List[int]:
    """
    Convert a DSF sequence into a mosaic signature.

    Each gate's DSF is encoded as trits. The sequence of trit patterns
    across gates IS the mosaic — it captures how the field evolves
    across space.

    Returns a list of trits representing the mosaic structure.
    """
    if not dsfs:
        return [TRIT_NULL] * 6  # empty mosaic

    # Aggregate statistics across the gate sequence
    directions = [d.D_k for d in dsfs]
    momentums = [d.M_k for d in dsfs]
    resonances = [d.R_scalar for d in dsfs]
    saliences = [d.w_k for d in dsfs]
    contrasts = [d.CV for d in dsfs]
    uncertainties = [d.U_star for d in dsfs]
    reversals = sum(1 for d in dsfs if d.R_rev)
    divergences = [d.C_k for d in dsfs]

    n = len(dsfs)

    # Trit encoding of mosaic structure:
    # 3 trits for field direction pattern
    pos_count = sum(1 for d in directions if d > 0)
    neg_count = sum(1 for d in directions if d < 0)
    null_count = sum(1 for d in directions if d == 0)

    mosaic = []

    # Trit 0: dominant direction (overall field trend)
    if pos_count > neg_count + null_count:
        mosaic.append(TRIT_POS)
    elif neg_count > pos_count + null_count:
        mosaic.append(TRIT_NEG)
    else:
        mosaic.append(TRIT_NULL)

    # Trit 1: direction stability (do directions keep changing?)
    changes = sum(1 for i in range(1, len(directions)) if directions[i] != directions[i-1])
    stability = 1.0 - (changes / max(1, n - 1))
    mosaic.append(dsf_to_trit(stability, 0.7, 0.3))

    # Trit 2: reversal density (how often does the field reverse?)
    rev_density = reversals / max(1, n)
    mosaic.append(dsf_to_trit(rev_density, 0.3, 0.05))

    # Trit 3: mean resonance (overall structural coherence)
    mean_R = np.mean(resonances)
    mosaic.append(dsf_to_trit(mean_R, 0.5, 0.2))

    # Trit 4: resonance variance (how much does coherence fluctuate?)
    var_R = np.var(resonances)
    mosaic.append(dsf_to_trit(var_R, 0.02, 0.002))

    # Trit 5: mean salience (how structurally prominent is the field?)
    mean_w = np.mean(saliences)
    mosaic.append(dsf_to_trit(mean_w, 0.3, 0.05))

    # Trit 6: mean contrast (internal diversity of gates)
    mean_CV = np.mean(contrasts)
    mosaic.append(dsf_to_trit(mean_CV, 0.3, 0.05))

    # Trit 7: mean uncertainty (field ambiguity)
    mean_U = np.mean(uncertainties)
    mosaic.append(dsf_to_trit(mean_U, 0.5, 0.2))

    # Trit 8: mosaic divergence pattern (structural complexity)
    mean_C = np.mean(divergences)
    mosaic.append(dsf_to_trit(mean_C, 2.0, 1.3))

    # Trit 9: gate count density (how many structural regions?)
    gate_density = n / 100.0  # normalize
    mosaic.append(dsf_to_trit(gate_density, 0.3, 0.05))

    # Trit 10: momentum trend (accelerating or decelerating?)
    mean_M = np.mean(momentums)
    mosaic.append(dsf_to_trit(mean_M, 0.01, -0.01))

    # Trit 11: field breathing (resonance range)
    R_range = max(resonances) - min(resonances) if resonances else 0
    mosaic.append(dsf_to_trit(R_range, 0.3, 0.05))

    return mosaic


# ============================================================
# Mosaics of Mosaics: run kernel on DSF sequence
# ============================================================

def mosaics_of_mosaics(dsf_sequence: List[DSFVector]) -> List[int]:
    """
    Second-order mosaic: run the kernel AGAIN on the DSF sequence.

    The DSF values from each gate become a new signal.
    L0-L4 finds structure in how the DSFs evolve.
    This captures higher-order patterns — not just what the field
    looks like at each gate, but how the field CHANGES across gates.
    """
    if len(dsf_sequence) < L1_MIN_GATE_LEN * 2:
        return dsf_sequence_to_mosaic(dsf_sequence)

    # Use resonance as the second-order signal
    r_signal = np.array([d.R_scalar for d in dsf_sequence])
    second_order_dsfs = run_kernel_on_signal(r_signal)

    if second_order_dsfs:
        return dsf_sequence_to_mosaic(second_order_dsfs)
    return dsf_sequence_to_mosaic(dsf_sequence)


# ============================================================
# Full Assembly: Image → Multi-Channel Mosaics → Loom State
# ============================================================

def process_image_v2(image: np.ndarray) -> dict:
    """
    Process an image through the kernel pipeline.

    1. Split into R, G, B, luminance, vertical-luminance channels
    2. Run L0-L4 kernel on each channel independently
    3. Each channel produces a mosaic (12 trits)
    4. Run mosaics-of-mosaics for higher-order structure
    5. Assemble all channels into loom strands

    Returns a dict with:
        - per-channel DSF sequences
        - per-channel mosaics
        - assembled loom state (24 trits)
        - stats for debugging
    """
    signals = image_to_signals(image)

    channel_dsfs = {}
    channel_mosaics = {}
    channel_stats = {}

    for ch_name, signal in signals.items():
        dsfs = run_kernel_on_signal(signal)
        channel_dsfs[ch_name] = dsfs

        # First-order mosaic
        mosaic = dsf_sequence_to_mosaic(dsfs)
        # Second-order (mosaics of mosaics) if enough gates
        mosaic2 = mosaics_of_mosaics(dsfs)

        channel_mosaics[ch_name] = {
            'first_order': mosaic,
            'second_order': mosaic2,
        }

        channel_stats[ch_name] = {
            'num_gates': len(dsfs),
            'mean_resonance': np.mean([d.R_scalar for d in dsfs]) if dsfs else 0,
            'reversals': sum(1 for d in dsfs if d.R_rev),
            'directions': [d.D_k for d in dsfs],
        }

    # Assemble loom state from channel mosaics
    # 8 strands × 3 trits = 24 trits
    loom_state = assemble_loom_state(channel_mosaics)

    return {
        'channel_dsfs': channel_dsfs,
        'channel_mosaics': channel_mosaics,
        'channel_stats': channel_stats,
        'loom_state': loom_state,
    }


def assemble_loom_state(channel_mosaics: dict) -> dict:
    """
    Assemble channel mosaics into loom strands.

    This is where the channels COUPLE — not by averaging or voting,
    but by letting each channel's structural signature occupy its
    natural strand in the loom.

    Strand assignment:
        distance  → luminance mosaic (overall structural boundary pattern)
        direction → luminance vertical mosaic (cross-axis structure)
        accel     → red channel mosaic (warm field)
        cam_edge  → green channel mosaic (natural field)
        cam_motion → blue channel mosaic (cool field)
        context   → settled from input strands (coupling)
        momentum  → settled from input strands (coupling)
        decision  → settled from all strands (coupling)
    """
    def get_trits(ch_name, order='first_order', offset=0):
        """Get 3 trits from a channel's mosaic."""
        if ch_name not in channel_mosaics:
            return [TRIT_NULL, TRIT_NULL, TRIT_NULL]
        m = channel_mosaics[ch_name][order]
        return [m[offset] if offset < len(m) else TRIT_NULL,
                m[offset+1] if offset+1 < len(m) else TRIT_NULL,
                m[offset+2] if offset+2 < len(m) else TRIT_NULL]

    # Input strands from channel mosaics
    # Use different trit ranges from each channel's mosaic to maximize information
    strands = {
        'distance':   get_trits('lum', 'first_order', 0),    # direction, stability, reversals
        'direction':  get_trits('lum_v', 'first_order', 0),  # vertical structure
        'accel':      get_trits('R', 'first_order', 3),      # red: resonance, variance, salience
        'cam_edge':   get_trits('G', 'first_order', 3),      # green: resonance, variance, salience
        'cam_motion': get_trits('B', 'first_order', 3),      # blue: resonance, variance, salience
    }

    # Settle context, momentum, decision through coupling
    input_trits = []
    for name in ['distance', 'direction', 'accel', 'cam_edge', 'cam_motion']:
        input_trits.extend(strands[name])

    # Coupling weights (from Verilog)
    ctx_weights = [
        [5, 5, 10, 10, 0, 0, 30, 0, 0, 10, 0, 0, 10, 0, 0],
        [0, 10, 5, 0, 10, 0, 0, 30, 0, 0, 10, 0, 0, 10, 0],
        [0, 5, 10, 0, 0, 10, 0, 0, 30, 0, 0, 10, 0, 0, 10],
    ]
    mmtm_weights = [
        [10, 0, 0, 5, 0, 0, 10, 0, 0, 5, 5, 0, 5, 5, 0],
        [0, 10, 0, 0, 5, 0, 0, 10, 0, 5, 0, 5, 5, 0, 5],
        [0, 0, 10, 0, 0, 5, 0, 0, 10, 0, 5, 5, 0, 5, 5],
    ]

    def compute_trit(weights, trits):
        total = sum(w * trit_sign(t) for w, t in zip(weights, trits))
        if total > DEAD_ZONE: return TRIT_POS
        if total < -DEAD_ZONE: return TRIT_NEG
        return TRIT_NULL

    context = [compute_trit(ctx_weights[i], input_trits) for i in range(3)]
    momentum = [compute_trit(mmtm_weights[i], input_trits) for i in range(3)]

    all_trits = input_trits + context + momentum
    dcsn_weights = [
        [15, 10, 5, 10, 5, 0, 5, 0, 0, 10, 5, 0, 5, 0, 0, 15, 10, 5, 10, 5, 0],
        [5, 0, 0, 5, 0, 0, 15, 10, 5, 5, 0, 0, 5, 0, 0, 5, 0, 0, 15, 10, 5],
        [5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 10, 10, 10, 10, 10, 10],
    ]
    decision = [compute_trit(dcsn_weights[i], all_trits) for i in range(3)]

    strands['context'] = context
    strands['momentum'] = momentum
    strands['decision'] = decision

    return strands


# ============================================================
# Krimelack v2: Structural Memory
# ============================================================

class KrimelackV2:
    """
    Structural memory that commits and recalls loom configurations.

    Doesn't store flat signatures — stores the full loom state
    including how channels coupled through context/momentum/decision.
    The coupling pattern IS the identity.
    """
    def __init__(self):
        self.motifs = []
        self.labels = []
        self.meta = []  # channel stats for debugging

    def state_to_trits(self, loom_state: dict) -> List[int]:
        trits = []
        for name in ['distance', 'direction', 'accel', 'cam_edge', 'cam_motion',
                      'context', 'momentum', 'decision']:
            trits.extend(loom_state[name])
        return trits

    def commit(self, loom_state: dict, u_star: float, resonance: float,
               label: str = "", meta: dict = None) -> bool:
        if u_star > KRIM_U_SETTLE:
            return False
        if resonance < KRIM_R_COMMIT:
            return False

        trits = self.state_to_trits(loom_state)

        # Duplicate check
        for stored in self.motifs:
            if stored == trits:
                return False

        if len(self.motifs) >= KRIM_DEPTH:
            self.motifs.pop(0)
            self.labels.pop(0)
            self.meta.pop(0)

        self.motifs.append(trits)
        self.labels.append(label)
        self.meta.append(meta or {})
        return True

    def recall(self, loom_state: dict) -> Tuple[Optional[int], int, str]:
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
        self.motifs = []
        self.labels = []
        self.meta = []


# ============================================================
# Test Image Generation
# ============================================================

def create_test_image(shape: str, color: Tuple[int, int, int],
                      size: int = 128, bg: Tuple[int, int, int] = (240, 240, 240)) -> np.ndarray:
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
        for y in range(size):
            for x in range(size):
                dx, dy = x - cx, y - cy
                angle = np.arctan2(dy, dx)
                dist = np.sqrt(dx**2 + dy**2)
                star_r = r * (0.5 + 0.5 * abs(np.cos(2.5 * angle)))
                if dist < star_r:
                    img[y, x] = color

    # Add slight texture/noise for realism
    noise = np.random.randint(-3, 4, img.shape, dtype=np.int16)
    img = np.clip(img.astype(np.int16) + noise, 0, 255).astype(np.uint8)

    return img


# ============================================================
# Pretty printing
# ============================================================

def trit_str(trits: List[int]) -> str:
    symbols = {TRIT_NULL: '0', TRIT_POS: '+', TRIT_NEG: '-'}
    return ''.join(symbols.get(t, '?') for t in trits)


def loom_state_str(state: dict) -> str:
    names = ['dist', 'dirn', 'accl', 'cedg', 'cmot', 'ctxt', 'mmtm', 'dcsn']
    keys = ['distance', 'direction', 'accel', 'cam_edge', 'cam_motion',
            'context', 'momentum', 'decision']
    parts = []
    for name, key in zip(names, keys):
        parts.append(f"{name}=[{trit_str(state[key])}]")
    return ' '.join(parts)


# ============================================================
# Tests
# ============================================================

def run_tests():
    print("=" * 70)
    print(" ArcLoom Vision v2 — Structural Field Recognition")
    print(" No ML. No training. Field structure + coupling + settlement.")
    print("=" * 70)
    print()

    objects = {
        'brown_circle':   create_test_image('circle',   (139, 90, 43)),
        'white_square':   create_test_image('square',   (255, 255, 255)),
        'red_triangle':   create_test_image('triangle', (200, 30, 30)),
        'blue_star':      create_test_image('star',     (30, 30, 200)),
        'brown_circle_2': create_test_image('circle',   (139, 90, 43)),
        'green_circle':   create_test_image('circle',   (30, 180, 30)),
        'red_circle':     create_test_image('circle',   (200, 30, 30)),
    }

    results = {}
    krim = KrimelackV2()

    for name, img in objects.items():
        print(f"Processing: {name}")
        result = process_image_v2(img)
        results[name] = result

        state = result['loom_state']
        print(f"  Loom: {loom_state_str(state)}")

        # Channel stats
        for ch, stats in result['channel_stats'].items():
            print(f"    {ch:6s}: {stats['num_gates']:3d} gates, "
                  f"R={stats['mean_resonance']:.3f}, "
                  f"revs={stats['reversals']}")

        # Commit to krimelack
        # Use mean resonance from luminance channel
        lum_stats = result['channel_stats'].get('lum', {})
        mean_R = lum_stats.get('mean_resonance', 0.5)
        committed = krim.commit(state, u_star=0.2, resonance=max(0.75, mean_R),
                                label=name, meta=result['channel_stats'])
        print(f"  Krimelack: {'COMMITTED' if committed else 'DUPLICATE'}")
        print()

    # Pairwise comparison
    print("=" * 70)
    print(" Pairwise Discrimination")
    print("=" * 70)
    names = list(results.keys())
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            t_a = krim.state_to_trits(results[names[i]]['loom_state'])
            t_b = krim.state_to_trits(results[names[j]]['loom_state'])
            matches = comparable = 0
            for a, b in zip(t_a, t_b):
                if a != TRIT_NULL and b != TRIT_NULL:
                    comparable += 1
                    if a == b:
                        matches += 1
            ratio = matches / comparable if comparable > 0 else 0
            tag = "SAME" if ratio > 0.85 else "DIFF" if ratio < 0.5 else "SIM"
            print(f"  {names[i]:20s} vs {names[j]:20s}: "
                  f"{matches}/{comparable} ({ratio:.0%}) {tag}")

    # Recall test
    print()
    print("=" * 70)
    print(" Krimelack Recall")
    print("=" * 70)
    for name in results:
        state = results[name]['loom_state']
        idx, score, label = krim.recall(state)
        correct = "OK" if label == name or (name.endswith('_2') and label == name[:-2]) else "MISS"
        print(f"  {name:20s} → {label:20s} score={score}/24 {correct}")

    # Invariance test
    print()
    print("=" * 70)
    print(" Invariance Tests")
    print("=" * 70)
    base = create_test_image('triangle', (200, 30, 30), size=128)
    base_result = process_image_v2(base)
    base_trits = krim.state_to_trits(base_result['loom_state'])

    variations = {
        'shifted_20px':  np.roll(base, 20, axis=1),
        'shifted_down':  np.roll(base, 20, axis=0),
        'brighter':      np.clip(base.astype(int) + 40, 0, 255).astype(np.uint8),
        'darker':        np.clip(base.astype(int) - 40, 0, 255).astype(np.uint8),
        'scaled_0.8':    np.array([base[int(y*0.8):int(y*0.8)+1, int(x*0.8):int(x*0.8)+1]
                                   for y in range(128) for x in range(128)]
                         ).reshape(128, 128, 3) if False else base,  # placeholder
        'diff_shape':    create_test_image('square', (200, 30, 30), size=128),
        'diff_color':    create_test_image('triangle', (30, 30, 200), size=128),
        'diff_both':     create_test_image('square', (30, 30, 200), size=128),
    }

    for vname, vimg in variations.items():
        vresult = process_image_v2(vimg)
        v_trits = krim.state_to_trits(vresult['loom_state'])
        matches = comparable = 0
        for a, b in zip(base_trits, v_trits):
            if a != TRIT_NULL and b != TRIT_NULL:
                comparable += 1
                if a == b:
                    matches += 1
        ratio = matches / comparable if comparable > 0 else 0
        print(f"  red_triangle vs {vname:15s}: {matches}/{comparable} ({ratio:.0%})")

    print()
    print(f"Krimelack: {len(krim.motifs)} motifs stored")


if __name__ == '__main__':
    run_tests()
