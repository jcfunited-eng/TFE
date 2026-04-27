#!/usr/bin/env python3
"""
ArcLoom Vision v3 — Let the Kernel Do Its Job
==============================================
Stop summarizing. Stop extracting features. Stop forcing answers.

The image is a field. Feed it to the kernel. The kernel reads structure.
The DSF sequence IS the signature. Krimelack commits and recalls
gate-level structure, not statistics.

Color channels have different field crossings at the same boundaries.
Brown→background: R drops a little, B drops a lot.
Blue→background: B drops a little, R drops a lot.
The kernel sees this in dF, sigma, kappa. Let it.
"""

import numpy as np
from typing import List, Tuple, Optional
from dataclasses import dataclass

# ============================================================
# Constants (from Verilog — exact match)
# ============================================================
L0_TAU_D = 0.20
L1_MIN_GATE_LEN = 4
L1_SHIFTS = [(4, 4, 4), (3, 3, 3), (2, 2, 2)]
L2_LAMBDA1, L2_LAMBDA2, L2_LAMBDA3 = 0.4, 0.3, 0.3
L2_U_ANOMALY = 0.9
L2_W_SHIFT, L2_CV_SHIFT = 8, 8
L3_H_MAX = 0.3125
L3_U_MAX = 0.85
L4_EPS_D = 0.05
DEAD_ZONE = 20
KRIM_U_SETTLE = 0.35
KRIM_R_COMMIT = 0.72

TRIT_NULL, TRIT_POS, TRIT_NEG = 0, 1, 2

def trit_sign(t):
    return 1 if t == TRIT_POS else (-1 if t == TRIT_NEG else 0)


# ============================================================
# Kernel: signal → gate DSF sequence
# ============================================================

@dataclass
class GateDSF:
    """One gate's complete structural state."""
    # L1
    T_k: int = 0
    V_k: float = 0.0
    C_k: int = 1
    # L2
    w_k: float = 0.0
    CV: float = 0.0
    U_k: float = 0.0
    # L3
    R: float = 0.0
    g_k: bool = True
    # L4
    D_k: int = 0      # +1, 0, -1
    M_k: float = 0.0
    R_rev: bool = False
    U_star: float = 0.0


def kernel(signal: np.ndarray) -> List[GateDSF]:
    """
    Full L0-L4 kernel on a 1D signal.
    Returns one GateDSF per structural gate.
    """
    n = len(signal)
    if n < 10:
        return []

    # Derivatives
    dF = np.diff(signal, prepend=signal[0])
    win = 8
    sigma = np.array([np.std(signal[max(0,i-win):i+1]) for i in range(n)])
    kappa = np.abs(np.diff(dF, prepend=dF[0]))

    # L0: boundaries
    D_t = np.abs(dF) + sigma + kappa
    boundary = D_t > L0_TAU_D

    # L1: gates
    gates = []
    g_start = 0
    g_V = 0.0
    g_N = 0
    g_len = 0
    g_dFmax = -1e9
    g_dFmin = 1e9

    for i in range(n):
        if boundary[i]:
            if g_len >= L1_MIN_GATE_LEN:
                projs = set()
                for ts, vs, rs in L1_SHIFTS:
                    projs.add((g_len >> ts, int(g_V) >> vs, g_len >> rs))
                gates.append((g_len, g_V, float(g_len), min(3, len(projs)),
                              g_N, g_dFmax, g_dFmin))
            g_start, g_V, g_N, g_len = i, 0.0, 0, 0
            g_dFmax, g_dFmin = -1e9, 1e9
        else:
            g_V += abs(dF[i]) + sigma[i] + kappa[i]
            g_len += 1
            g_dFmax = max(g_dFmax, dF[i])
            g_dFmin = min(g_dFmin, dF[i])
            if abs(dF[i]) < 0.001 and sigma[i] < 0.001:
                g_N += 1

    if g_len >= L1_MIN_GATE_LEN:
        projs = set()
        for ts, vs, rs in L1_SHIFTS:
            projs.add((g_len >> ts, int(g_V) >> vs, g_len >> rs))
        gates.append((g_len, g_V, float(g_len), min(3, len(projs)),
                      g_N, g_dFmax, g_dFmin))

    if not gates:
        return []

    # L2-L3-L4 per gate
    dsf_seq = []
    R_prev, R_prev2, D_prev = 0.0, 0.0, 0

    for T_k, V_k, R_k, C_k, N_sum, dFmax, dFmin in gates:
        # L2
        w_k = min(1.0, V_k / (1 << L2_W_SHIFT))
        CV = min(1.0, max(0, dFmax - dFmin) / (1 << L2_CV_SHIFT))
        N_gate = 1.0 if 2 * N_sum >= T_k else 0.0
        U_k = min(1.0, max(0, L2_LAMBDA1 * (C_k-1)/2 + L2_LAMBDA2*CV + L2_LAMBDA3*N_gate))
        IAS = U_k > L2_U_ANOMALY

        # L3
        R_vec = [w_k, CV, w_k, 1.0/(1.0+C_k), 1.0-U_k]
        R = 0.2 * sum(R_vec)
        Hyst = abs(R - R_prev) > L3_H_MAX
        g_k = (U_k <= L3_U_MAX) and not IAS and not Hyst

        # L4
        dR = R - R_prev
        D_k = 1 if dR > L4_EPS_D else (-1 if dR < -L4_EPS_D else 0)
        M_k = R - 2*R_prev + R_prev2
        R_rev = (D_k == 1 and D_prev == -1) or (D_k == -1 and D_prev == 1)
        U_star = min(1.0, U_k + 0.15*(1 if Hyst else 0) + 0.20*(1 if IAS else 0))

        dsf_seq.append(GateDSF(
            T_k=T_k, V_k=V_k, C_k=C_k,
            w_k=w_k, CV=CV, U_k=U_k,
            R=R, g_k=g_k,
            D_k=D_k, M_k=M_k, R_rev=R_rev, U_star=U_star
        ))

        R_prev2, R_prev, D_prev = R_prev, R, D_k

    return dsf_seq


# ============================================================
# Image → scan signals (multiple scan patterns)
# ============================================================

def image_to_scans(image: np.ndarray) -> dict:
    """
    Multiple scan patterns extract different structural axes.
    Each scan is a 1D signal fed to the kernel independently.
    """
    img = image.astype(float) / 255.0
    h, w = img.shape[:2]

    scans = {}

    # Per-channel horizontal raster
    scans['R_h'] = img[:, :, 0].flatten()
    scans['G_h'] = img[:, :, 1].flatten()
    scans['B_h'] = img[:, :, 2].flatten()

    # Per-channel vertical raster
    scans['R_v'] = img[:, :, 0].T.flatten()
    scans['G_v'] = img[:, :, 1].T.flatten()
    scans['B_v'] = img[:, :, 2].T.flatten()

    # Luminance horizontal + vertical
    lum = 0.299 * img[:,:,0] + 0.587 * img[:,:,1] + 0.114 * img[:,:,2]
    scans['L_h'] = lum.flatten()
    scans['L_v'] = lum.T.flatten()

    # Diagonal scans (45° and 135°) — captures diagonal structure
    diag_45 = []
    diag_135 = []
    for d in range(-h+1, w):
        for i in range(max(0, -d), min(h, w-d)):
            diag_45.append(lum[i, i+d])
        for i in range(max(0, d-w+1), min(h, d+1)):
            diag_135.append(lum[i, d-i])
    scans['L_d45'] = np.array(diag_45)
    scans['L_d135'] = np.array(diag_135)

    return scans


# ============================================================
# Gate-level BSIL: DSF → trits (per gate, not summarized)
# ============================================================

def dsf_to_trits(dsf: GateDSF) -> List[int]:
    """
    Encode one gate's DSF as 3 trits.
    Trit 0: direction D_k
    Trit 1: resonance level (high/null/low)
    Trit 2: uncertainty level (low=settled/null/high=ambiguous)
    """
    # Direction maps directly
    t0 = TRIT_POS if dsf.D_k > 0 else (TRIT_NEG if dsf.D_k < 0 else TRIT_NULL)

    # Resonance
    t1 = TRIT_POS if dsf.R > 0.4 else (TRIT_NEG if dsf.R < 0.15 else TRIT_NULL)

    # Uncertainty (inverted: low U = positive/settled)
    t2 = TRIT_POS if dsf.U_star < 0.25 else (TRIT_NEG if dsf.U_star > 0.6 else TRIT_NULL)

    return [t0, t1, t2]


# ============================================================
# Structural Fingerprint: gate-level trit sequences
# ============================================================

def structural_fingerprint(scan_dsfs: dict) -> dict:
    """
    Build a structural fingerprint from all scan DSF sequences.

    Instead of summarizing, we keep the GATE-LEVEL trit sequences.
    The fingerprint is the collection of trit sequences across scans.

    For krimelack comparison, we extract coupling patterns:
    how do the channels relate at each structural boundary?
    """
    fp = {}

    for scan_name, dsfs in scan_dsfs.items():
        # Convert each gate's DSF to trits
        trit_seq = [dsf_to_trits(d) for d in dsfs]
        fp[scan_name] = {
            'trit_sequence': trit_seq,
            'num_gates': len(dsfs),
            'gate_dsfs': dsfs,
        }

    return fp


def fingerprint_to_loom(fp: dict) -> dict:
    """
    Assemble fingerprint into loom strands.

    Each strand gets gate-level information from a specific scan.
    The COUPLING between strands (context/momentum/decision) captures
    cross-channel relationships — how R, G, B fields relate to each other
    at structural boundaries.

    Key: use the gate-by-gate cross-channel coupling, not summaries.
    """
    # For each scan, compute the dominant trit pattern across gates
    # But keep it gate-aware: weight gates by salience (w_k)

    def weighted_trit(dsfs, trit_fn):
        """Weighted vote across gates using salience as weight."""
        if not dsfs:
            return TRIT_NULL
        scores = {TRIT_NULL: 0.0, TRIT_POS: 0.0, TRIT_NEG: 0.0}
        for d in dsfs:
            t = trit_fn(d)
            # Weight by salience × gate quality
            weight = d.w_k * (1.0 if d.g_k else 0.1)
            scores[t] += weight
        return max(scores, key=scores.get)

    def dir_trit(d): return TRIT_POS if d.D_k > 0 else (TRIT_NEG if d.D_k < 0 else TRIT_NULL)
    def res_trit(d): return TRIT_POS if d.R > 0.35 else (TRIT_NEG if d.R < 0.15 else TRIT_NULL)
    def vol_trit(d): return TRIT_POS if d.V_k > 5.0 else (TRIT_NEG if d.V_k < 1.0 else TRIT_NULL)
    def unc_trit(d): return TRIT_POS if d.U_star < 0.25 else (TRIT_NEG if d.U_star > 0.5 else TRIT_NULL)
    def cv_trit(d): return TRIT_POS if d.CV > 0.3 else (TRIT_NEG if d.CV < 0.05 else TRIT_NULL)
    def mom_trit(d): return TRIT_POS if d.M_k > 0.01 else (TRIT_NEG if d.M_k < -0.01 else TRIT_NULL)

    def get_dsfs(name):
        return fp.get(name, {}).get('gate_dsfs', [])

    # Strand assignment: each strand captures a different structural axis
    # distance: luminance horizontal — overall spatial boundary pattern
    lh = get_dsfs('L_h')
    strands = {
        'distance': [
            weighted_trit(lh, dir_trit),   # field direction
            weighted_trit(lh, res_trit),   # field coherence
            weighted_trit(lh, vol_trit),   # structural volume
        ],
    }

    # direction: luminance vertical — cross-axis structure
    lv = get_dsfs('L_v')
    strands['direction'] = [
        weighted_trit(lv, dir_trit),
        weighted_trit(lv, res_trit),
        weighted_trit(lv, vol_trit),
    ]

    # accel: RED channel — warm field coupling
    rh, rv = get_dsfs('R_h'), get_dsfs('R_v')
    strands['accel'] = [
        weighted_trit(rh, res_trit),     # red horizontal resonance
        weighted_trit(rv, res_trit),     # red vertical resonance
        weighted_trit(rh, cv_trit),      # red contrast
    ]

    # cam_edge: GREEN channel — natural field coupling
    gh, gv = get_dsfs('G_h'), get_dsfs('G_v')
    strands['cam_edge'] = [
        weighted_trit(gh, res_trit),
        weighted_trit(gv, res_trit),
        weighted_trit(gh, cv_trit),
    ]

    # cam_motion: BLUE channel — cool field coupling
    bh, bv = get_dsfs('B_h'), get_dsfs('B_v')
    strands['cam_motion'] = [
        weighted_trit(bh, res_trit),
        weighted_trit(bv, res_trit),
        weighted_trit(bh, cv_trit),
    ]

    # Settle context, momentum, decision through coupling weights
    input_trits = []
    for name in ['distance', 'direction', 'accel', 'cam_edge', 'cam_motion']:
        input_trits.extend(strands[name])

    ctx_w = [
        [5, 5, 10, 10, 0, 0, 30, 0, 0, 10, 0, 0, 10, 0, 0],
        [0, 10, 5, 0, 10, 0, 0, 30, 0, 0, 10, 0, 0, 10, 0],
        [0, 5, 10, 0, 0, 10, 0, 0, 30, 0, 0, 10, 0, 0, 10],
    ]
    mmtm_w = [
        [10, 0, 0, 5, 0, 0, 10, 0, 0, 5, 5, 0, 5, 5, 0],
        [0, 10, 0, 0, 5, 0, 0, 10, 0, 5, 0, 5, 5, 0, 5],
        [0, 0, 10, 0, 0, 5, 0, 0, 10, 0, 5, 5, 0, 5, 5],
    ]

    def settle(weights, trits):
        total = sum(w * trit_sign(t) for w, t in zip(weights, trits))
        if total > DEAD_ZONE: return TRIT_POS
        if total < -DEAD_ZONE: return TRIT_NEG
        return TRIT_NULL

    strands['context'] = [settle(ctx_w[i], input_trits) for i in range(3)]
    strands['momentum'] = [settle(mmtm_w[i], input_trits) for i in range(3)]

    all_21 = input_trits + strands['context'] + strands['momentum']
    dcsn_w = [
        [15, 10, 5, 10, 5, 0, 5, 0, 0, 10, 5, 0, 5, 0, 0, 15, 10, 5, 10, 5, 0],
        [5, 0, 0, 5, 0, 0, 15, 10, 5, 5, 0, 0, 5, 0, 0, 5, 0, 0, 15, 10, 5],
        [5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 10, 10, 10, 10, 10, 10],
    ]
    strands['decision'] = [settle(dcsn_w[i], all_21) for i in range(3)]

    return strands


# ============================================================
# Cross-channel coupling signature
# ============================================================

def cross_channel_coupling(fp: dict) -> List[int]:
    """
    Compare gate-level DSFs ACROSS channels at the same spatial location.

    At each boundary: how does R differ from G? How does G differ from B?
    These cross-channel couplings are what distinguish colors structurally.

    Returns 6 trits: R-G coupling (3) + G-B coupling (3)
    """
    rh = fp.get('R_h', {}).get('gate_dsfs', [])
    gh = fp.get('G_h', {}).get('gate_dsfs', [])
    bh = fp.get('B_h', {}).get('gate_dsfs', [])

    # Compare resonance levels across channels
    n = min(len(rh), len(gh), len(bh))
    if n == 0:
        return [TRIT_NULL] * 6

    # R vs G: at each gate, is R's resonance higher, lower, or same as G?
    rg_diff = []
    gb_diff = []
    rg_vol_diff = []
    gb_vol_diff = []

    for i in range(n):
        rg_diff.append(rh[i].R - gh[i].R)
        gb_diff.append(gh[i].R - bh[i].R)
        rg_vol_diff.append(rh[i].V_k - gh[i].V_k)
        gb_vol_diff.append(gh[i].V_k - bh[i].V_k)

    def mean_to_trit(vals, thresh=0.005):
        m = np.mean(vals)
        if m > thresh: return TRIT_POS
        if m < -thresh: return TRIT_NEG
        return TRIT_NULL

    def var_to_trit(vals, hi=0.01, lo=0.001):
        v = np.var(vals)
        if v > hi: return TRIT_POS
        if v < lo: return TRIT_NEG
        return TRIT_NULL

    return [
        mean_to_trit(rg_diff),       # R vs G resonance bias
        var_to_trit(rg_diff),        # R vs G resonance stability
        mean_to_trit(rg_vol_diff),   # R vs G volume bias
        mean_to_trit(gb_diff),       # G vs B resonance bias
        var_to_trit(gb_diff),        # G vs B resonance stability
        mean_to_trit(gb_vol_diff),   # G vs B volume bias
    ]


# ============================================================
# Krimelack: stores loom state + cross-channel coupling
# ============================================================

class Krimelack:
    def __init__(self):
        self.motifs = []   # (loom_trits, coupling_trits)
        self.labels = []

    def _extract(self, loom_state, coupling):
        loom_trits = []
        for name in ['distance','direction','accel','cam_edge','cam_motion',
                      'context','momentum','decision']:
            loom_trits.extend(loom_state[name])
        return loom_trits, coupling

    def commit(self, loom_state, coupling, label=""):
        lt, ct = self._extract(loom_state, coupling)
        combined = lt + ct  # 24 + 6 = 30 trits

        for stored_lt, stored_ct in self.motifs:
            if (stored_lt + stored_ct) == combined:
                return False

        self.motifs.append((lt, ct))
        self.labels.append(label)
        return True

    def recall(self, loom_state, coupling):
        lt, ct = self._extract(loom_state, coupling)
        query = lt + ct

        best_idx, best_score = -1, 0
        for i, (s_lt, s_ct) in enumerate(self.motifs):
            stored = s_lt + s_ct
            score = 0
            for q, s in zip(query, stored):
                if q != TRIT_NULL and s != TRIT_NULL and q == s:
                    score += 1
            if score > best_score:
                best_score = score
                best_idx = i

        if best_idx >= 0:
            return best_idx, best_score, self.labels[best_idx]
        return None, 0, ""


# ============================================================
# Test images
# ============================================================

def make_image(shape, color, size=128, bg=(240, 240, 240)):
    img = np.full((size, size, 3), bg, dtype=np.uint8)
    cx, cy, r = size//2, size//2, size//3

    if shape == 'circle':
        yy, xx = np.ogrid[:size, :size]
        mask = (xx - cx)**2 + (yy - cy)**2 < r**2
        img[mask] = color
    elif shape == 'square':
        img[cy-r:cy+r, cx-r:cx+r] = color
    elif shape == 'triangle':
        for y in range(cy-r, cy+r):
            hw = max(0, int(r * (y - (cy-r)) / (2*r)))
            img[y, cx-hw:cx+hw] = color
    elif shape == 'star':
        yy, xx = np.ogrid[:size, :size]
        angles = np.arctan2(yy - cy, xx - cx)
        dists = np.sqrt((xx - cx)**2 + (yy - cy)**2)
        star_r = r * (0.5 + 0.5 * np.abs(np.cos(2.5 * angles)))
        img[dists < star_r] = color

    noise = np.random.randint(-3, 4, img.shape, dtype=np.int16)
    return np.clip(img.astype(np.int16) + noise, 0, 255).astype(np.uint8)


# ============================================================
# Pretty print
# ============================================================

def trit_str(trits):
    return ''.join({TRIT_NULL:'0', TRIT_POS:'+', TRIT_NEG:'-'}.get(t,'?') for t in trits)

def loom_str(state):
    names = [('dist','distance'), ('dirn','direction'), ('accl','accel'),
             ('cedg','cam_edge'), ('cmot','cam_motion'),
             ('ctxt','context'), ('mmtm','momentum'), ('dcsn','decision')]
    return ' '.join(f"{n}=[{trit_str(state[k])}]" for n, k in names)


# ============================================================
# Run
# ============================================================

def process(image):
    scans = image_to_scans(image)
    scan_dsfs = {name: kernel(sig) for name, sig in scans.items()}
    fp = structural_fingerprint(scan_dsfs)
    loom = fingerprint_to_loom(fp)
    coupling = cross_channel_coupling(fp)
    return loom, coupling, fp

def main():
    np.random.seed(42)

    print("=" * 70)
    print(" ArcLoom Vision v3 — Let the Kernel Do Its Job")
    print("=" * 70)
    print()

    objects = {
        'brown_circle':  make_image('circle',   (139, 90, 43)),
        'red_circle':    make_image('circle',   (200, 30, 30)),
        'green_circle':  make_image('circle',   (30, 180, 30)),
        'blue_circle':   make_image('circle',   (30, 30, 200)),
        'white_square':  make_image('square',   (255, 255, 255)),
        'red_square':    make_image('square',   (200, 30, 30)),
        'red_triangle':  make_image('triangle', (200, 30, 30)),
        'blue_star':     make_image('star',     (30, 30, 200)),
        'brown_circle2': make_image('circle',   (139, 90, 43)),
    }

    results = {}
    krim = Krimelack()

    for name, img in objects.items():
        loom, coupling, fp = process(img)
        results[name] = (loom, coupling)

        # Gate counts per channel
        gate_info = []
        for ch in ['R_h', 'G_h', 'B_h', 'L_h']:
            n = fp.get(ch, {}).get('num_gates', 0)
            gate_info.append(f"{ch}={n}")

        committed = krim.commit(loom, coupling, label=name)

        print(f"{name:18s}  {loom_str(loom)}  cc=[{trit_str(coupling)}]  "
              f"{'COMMIT' if committed else 'DUP':6s}  {' '.join(gate_info)}")

    # Pairwise
    print()
    print("=" * 70)
    print(" Pairwise Discrimination")
    print("=" * 70)
    names = list(results.keys())
    for i in range(len(names)):
        for j in range(i+1, len(names)):
            l_a, c_a = results[names[i]]
            l_b, c_b = results[names[j]]
            qa = sum(trit_sign(t) != 0 for name in l_a for t in l_a[name]) + sum(trit_sign(t) != 0 for t in c_a)

            # Compare loom + coupling
            t_a, t_b = [], []
            for name in ['distance','direction','accel','cam_edge','cam_motion',
                          'context','momentum','decision']:
                t_a.extend(l_a[name])
                t_b.extend(l_b[name])
            t_a.extend(c_a)
            t_b.extend(c_b)

            matches = comparable = 0
            for a, b in zip(t_a, t_b):
                if a != TRIT_NULL and b != TRIT_NULL:
                    comparable += 1
                    if a == b: matches += 1
            ratio = matches / comparable if comparable > 0 else 0
            tag = "SAME" if ratio > 0.85 else "DIFF" if ratio < 0.5 else "SIM"
            # Only print interesting pairs
            if ratio < 0.95 or names[j].endswith('2'):
                print(f"  {names[i]:18s} vs {names[j]:18s}: "
                      f"{matches}/{comparable} ({ratio:.0%}) {tag}")

    # Recall
    print()
    print("=" * 70)
    print(" Krimelack Recall")
    print("=" * 70)
    for name in results:
        loom, coupling = results[name]
        idx, score, label = krim.recall(loom, coupling)
        ok = "OK" if label == name or label == name.rstrip('2') else "MISS"
        print(f"  {name:18s} → {label:18s} score={score}/30 {ok}")

    # Invariance
    print()
    print("=" * 70)
    print(" Invariance")
    print("=" * 70)
    base = make_image('triangle', (200, 30, 30))
    base_loom, base_coup, _ = process(base)
    base_t = []
    for k in ['distance','direction','accel','cam_edge','cam_motion',
              'context','momentum','decision']:
        base_t.extend(base_loom[k])
    base_t.extend(base_coup)

    tests = {
        'shift_right':  np.roll(base, 20, axis=1),
        'shift_down':   np.roll(base, 20, axis=0),
        'brighter+40':  np.clip(base.astype(int)+40, 0, 255).astype(np.uint8),
        'darker-40':    np.clip(base.astype(int)-40, 0, 255).astype(np.uint8),
        'diff_shape':   make_image('square', (200, 30, 30)),
        'diff_color':   make_image('triangle', (30, 30, 200)),
        'diff_both':    make_image('star', (30, 180, 30)),
    }

    for tname, timg in tests.items():
        tl, tc, _ = process(timg)
        tt = []
        for k in ['distance','direction','accel','cam_edge','cam_motion',
                   'context','momentum','decision']:
            tt.extend(tl[k])
        tt.extend(tc)

        matches = comparable = 0
        for a, b in zip(base_t, tt):
            if a != TRIT_NULL and b != TRIT_NULL:
                comparable += 1
                if a == b: matches += 1
        ratio = matches / comparable if comparable > 0 else 0
        print(f"  red_triangle vs {tname:15s}: {matches}/{comparable} ({ratio:.0%})")


if __name__ == '__main__':
    main()
