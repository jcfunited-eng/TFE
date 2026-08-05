#!/usr/bin/env python3
"""
ArcLoom Vision v4 — Scanline Mosaics of Mosaics
================================================
Each scanline is its own signal → kernel → DSF.
The column of per-scanline DSFs is a second-order signal → kernel again.

Circle: scanline widths grow then shrink smoothly (dome)
Triangle: scanline widths grow linearly (ramp)
Square: scanline widths constant then stop (step)
Star: scanline widths oscillate (zigzag)

These are fundamentally different second-order field patterns.
The kernel sees them. Color channels couple differently at each scanline.
"""

import numpy as np
from typing import List, Tuple

TRIT_NULL, TRIT_POS, TRIT_NEG = 0, 1, 2
DEAD_ZONE = 20

def trit_sign(t):
    return 1 if t == TRIT_POS else (-1 if t == TRIT_NEG else 0)

# ============================================================
# Compact kernel: signal → (gate_count, mean_R, mean_V, mean_U, dir_pattern, rev_count)
# ============================================================

def kernel_stats(signal):
    """
    Run L0-L4 on 1D signal. Return per-gate DSF values as arrays.
    """
    n = len(signal)
    if n < 10:
        return {'R': [], 'V': [], 'D': [], 'U': [], 'CV': [], 'gates': 0}

    dF = np.diff(signal, prepend=signal[0])
    win = 8
    sigma = np.array([np.std(signal[max(0,i-win):i+1]) for i in range(n)])
    kappa = np.abs(np.diff(dF, prepend=dF[0]))

    D_t = np.abs(dF) + sigma + kappa
    boundary = D_t > 0.20

    # L1: collect gate volumes
    gates_V = []
    gates_dFrange = []
    gates_N = []
    gates_T = []
    gates_C = []
    g_V, g_N, g_len = 0.0, 0, 0
    g_dFmax, g_dFmin = -1e9, 1e9

    for i in range(n):
        if boundary[i]:
            if g_len >= 4:
                projs = set()
                for ts, vs, rs in [(4,4,4),(3,3,3),(2,2,2)]:
                    projs.add((g_len>>ts, int(g_V)>>vs, g_len>>rs))
                gates_V.append(g_V)
                gates_dFrange.append(g_dFmax - g_dFmin)
                gates_N.append(g_N)
                gates_T.append(g_len)
                gates_C.append(min(3, len(projs)))
            g_V, g_N, g_len = 0.0, 0, 0
            g_dFmax, g_dFmin = -1e9, 1e9
        else:
            g_V += abs(dF[i]) + sigma[i] + kappa[i]
            g_len += 1
            g_dFmax = max(g_dFmax, dF[i])
            g_dFmin = min(g_dFmin, dF[i])
            if abs(dF[i]) < 0.001 and sigma[i] < 0.001:
                g_N += 1

    if g_len >= 4:
        projs = set()
        for ts, vs, rs in [(4,4,4),(3,3,3),(2,2,2)]:
            projs.add((g_len>>ts, int(g_V)>>vs, g_len>>rs))
        gates_V.append(g_V)
        gates_dFrange.append(g_dFmax - g_dFmin)
        gates_N.append(g_N)
        gates_T.append(g_len)
        gates_C.append(min(3, len(projs)))

    ng = len(gates_V)
    if ng == 0:
        return {'R': [], 'V': [], 'D': [], 'U': [], 'CV': [], 'gates': 0}

    # L2-L3-L4 per gate
    Rs, Vs, Ds, Us, CVs = [], [], [], [], []
    R_prev, R_prev2, D_prev = 0.0, 0.0, 0

    for i in range(ng):
        w = min(1.0, gates_V[i] / 256)
        cv = min(1.0, max(0, gates_dFrange[i]) / 256)
        Ng = 1.0 if 2*gates_N[i] >= gates_T[i] else 0.0
        U = min(1.0, max(0, 0.4*(gates_C[i]-1)/2 + 0.3*cv + 0.3*Ng))
        IAS = U > 0.9

        R_vec = [w, cv, w, 1.0/(1.0+gates_C[i]), 1.0-U]
        R = 0.2 * sum(R_vec)
        Hyst = abs(R - R_prev) > 0.3125
        g_k = U <= 0.85 and not IAS and not Hyst

        dR = R - R_prev
        D = 1 if dR > 0.05 else (-1 if dR < -0.05 else 0)
        U_star = min(1.0, U + 0.15*(1 if Hyst else 0) + 0.20*(1 if IAS else 0))

        Rs.append(R)
        Vs.append(gates_V[i])
        Ds.append(D)
        Us.append(U_star)
        CVs.append(cv)

        R_prev2, R_prev, D_prev = R_prev, R, D

    return {'R': Rs, 'V': Vs, 'D': Ds, 'U': Us, 'CV': CVs, 'gates': ng}


# ============================================================
# Per-scanline kernel → second-order signals
# ============================================================

def scanline_kernel(image, channel=None):
    """
    Run kernel on each horizontal scanline of one channel.
    Returns per-scanline: gate_count, mean_resonance, total_volume.
    These become the second-order signals.
    """
    img = image.astype(float) / 255.0
    h, w = img.shape[:2]

    if channel is not None:
        data = img[:, :, channel]
    else:
        data = 0.299*img[:,:,0] + 0.587*img[:,:,1] + 0.114*img[:,:,2]

    gate_counts = []
    mean_resonances = []
    total_volumes = []
    mean_cvs = []

    for row in range(h):
        stats = kernel_stats(data[row])
        gate_counts.append(stats['gates'])
        if stats['R']:
            mean_resonances.append(np.mean(stats['R']))
            total_volumes.append(sum(stats['V']))
            mean_cvs.append(np.mean(stats['CV']))
        else:
            mean_resonances.append(0.0)
            total_volumes.append(0.0)
            mean_cvs.append(0.0)

    return {
        'gate_counts': np.array(gate_counts, dtype=float),
        'resonances': np.array(mean_resonances),
        'volumes': np.array(total_volumes),
        'contrasts': np.array(mean_cvs),
    }


def vertical_scanline_kernel(image, channel=None):
    """Same but vertical scanlines."""
    img = image.astype(float) / 255.0
    h, w = img.shape[:2]

    if channel is not None:
        data = img[:, :, channel]
    else:
        data = 0.299*img[:,:,0] + 0.587*img[:,:,1] + 0.114*img[:,:,2]

    gate_counts = []
    mean_resonances = []
    total_volumes = []

    for col in range(w):
        stats = kernel_stats(data[:, col])
        gate_counts.append(stats['gates'])
        if stats['R']:
            mean_resonances.append(np.mean(stats['R']))
            total_volumes.append(sum(stats['V']))
        else:
            mean_resonances.append(0.0)
            total_volumes.append(0.0)

    return {
        'gate_counts': np.array(gate_counts, dtype=float),
        'resonances': np.array(mean_resonances),
        'volumes': np.array(total_volumes),
    }


# ============================================================
# Second-order kernel: run kernel on per-scanline signals
# ============================================================

def second_order(scanline_data):
    """
    Run the kernel on the COLUMN of per-scanline values.
    This is mosaics of mosaics.

    The gate_counts signal shows how the object's width changes
    from top to bottom:
      Circle: 0,0,...,1,2,3,3,3,2,1,...,0,0 (dome)
      Triangle: 0,...,0,1,1,2,2,3,3,...       (ramp)
      Square: 0,...,2,2,2,2,2,...,0           (plateau)

    The kernel sees these as different field structures.
    """
    results = {}

    for key in ['gate_counts', 'resonances', 'volumes']:
        signal = scanline_data[key]
        if len(signal) > 10:
            stats = kernel_stats(signal)
            results[key] = stats
        else:
            results[key] = {'R': [], 'V': [], 'D': [], 'U': [], 'CV': [], 'gates': 0}

    return results


# ============================================================
# Encode second-order DSFs as ternary strands
# ============================================================

def encode_strand(second_order_stats, key):
    """
    Encode one second-order signal's DSF sequence as 3 trits.
    """
    stats = second_order_stats.get(key, {})
    Rs = stats.get('R', [])
    Ds = stats.get('D', [])
    Vs = stats.get('V', [])
    ng = stats.get('gates', 0)

    if ng == 0 or not Rs:
        return [TRIT_NULL, TRIT_NULL, TRIT_NULL]

    # Trit 0: dominant direction of the second-order field
    pos = sum(1 for d in Ds if d > 0)
    neg = sum(1 for d in Ds if d < 0)
    if pos > neg + 1:
        t0 = TRIT_POS
    elif neg > pos + 1:
        t0 = TRIT_NEG
    else:
        t0 = TRIT_NULL

    # Trit 1: second-order resonance level
    mR = np.mean(Rs)
    if mR > 0.35:
        t1 = TRIT_POS
    elif mR < 0.15:
        t1 = TRIT_NEG
    else:
        t1 = TRIT_NULL

    # Trit 2: gate count (structural complexity at second order)
    if ng > 8:
        t2 = TRIT_POS
    elif ng < 3:
        t2 = TRIT_NEG
    else:
        t2 = TRIT_NULL

    return [t0, t1, t2]


# ============================================================
# Full pipeline: image → loom state
# ============================================================

def process_image(image):
    """
    Full pipeline:
    1. Per-scanline kernel on each channel (R, G, B, lum)
    2. Second-order kernel on per-scanline signals
    3. Encode as loom strands
    4. Coupling settles context/momentum/decision
    5. Cross-channel coupling for color
    """
    # First order: per-scanline
    lum_h = scanline_kernel(image, channel=None)
    lum_v = vertical_scanline_kernel(image, channel=None)
    r_h = scanline_kernel(image, channel=0)
    g_h = scanline_kernel(image, channel=1)
    b_h = scanline_kernel(image, channel=2)

    # Second order: kernel on the column of per-scanline values
    lum_h_2 = second_order(lum_h)
    lum_v_2 = second_order(lum_v)
    r_h_2 = second_order(r_h)
    g_h_2 = second_order(g_h)
    b_h_2 = second_order(b_h)

    # Encode strands from second-order DSFs
    strands = {
        # Luminance horizontal: shape silhouette (how width changes top→bottom)
        'distance': encode_strand(lum_h_2, 'gate_counts'),
        # Luminance vertical: shape silhouette (how height changes left→right)
        'direction': encode_strand(lum_v_2, 'gate_counts'),
        # Red channel: warm field structure
        'accel': encode_strand(r_h_2, 'gate_counts'),
        # Green channel: natural field structure
        'cam_edge': encode_strand(g_h_2, 'gate_counts'),
        # Blue channel: cool field structure
        'cam_motion': encode_strand(b_h_2, 'gate_counts'),
    }

    # Coupling settlement
    input_trits = []
    for k in ['distance', 'direction', 'accel', 'cam_edge', 'cam_motion']:
        input_trits.extend(strands[k])

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

    # Cross-channel coupling: how do R, G, B gate patterns differ?
    coupling = compute_color_coupling(r_h, g_h, b_h)

    # Debug info
    debug = {
        'lum_h_gates_signal': lum_h['gate_counts'].tolist(),
        'lum_h_2nd_gates': lum_h_2.get('gate_counts', {}).get('gates', 0),
        'r_h_2nd_gates': r_h_2.get('gate_counts', {}).get('gates', 0),
        'g_h_2nd_gates': g_h_2.get('gate_counts', {}).get('gates', 0),
        'b_h_2nd_gates': b_h_2.get('gate_counts', {}).get('gates', 0),
    }

    return strands, coupling, debug


def compute_color_coupling(r_data, g_data, b_data):
    """
    Cross-channel coupling: compare per-scanline gate patterns across R, G, B.

    At each scanline, R/G/B have different numbers of gates and volumes
    because color boundaries differ. The PATTERN of these differences
    is the color signature.
    """
    r_gc = r_data['gate_counts']
    g_gc = g_data['gate_counts']
    b_gc = b_data['gate_counts']

    n = min(len(r_gc), len(g_gc), len(b_gc))
    if n == 0:
        return [TRIT_NULL] * 6

    # R-G difference
    rg = r_gc[:n] - g_gc[:n]
    # G-B difference
    gb = g_gc[:n] - b_gc[:n]
    # R-B difference
    rb = r_gc[:n] - b_gc[:n]

    def diff_trit(diff_signal, mean_thresh=0.3, var_thresh=1.0):
        m = np.mean(diff_signal)
        v = np.var(diff_signal)
        t_mean = TRIT_POS if m > mean_thresh else (TRIT_NEG if m < -mean_thresh else TRIT_NULL)
        t_var = TRIT_POS if v > var_thresh else (TRIT_NEG if v < 0.1 else TRIT_NULL)
        return t_mean, t_var

    rg_m, rg_v = diff_trit(rg)
    gb_m, gb_v = diff_trit(gb)
    rb_m, rb_v = diff_trit(rb)

    return [rg_m, rg_v, gb_m, gb_v, rb_m, rb_v]


# ============================================================
# Krimelack
# ============================================================

class Krimelack:
    def __init__(self):
        self.motifs = []
        self.labels = []

    def _flatten(self, strands, coupling):
        t = []
        for k in ['distance','direction','accel','cam_edge','cam_motion',
                   'context','momentum','decision']:
            t.extend(strands[k])
        t.extend(coupling)
        return t

    def commit(self, strands, coupling, label=""):
        t = self._flatten(strands, coupling)
        for stored in self.motifs:
            if stored == t:
                return False
        self.motifs.append(t)
        self.labels.append(label)
        return True

    def recall(self, strands, coupling):
        t = self._flatten(strands, coupling)
        best_idx, best_score = -1, 0
        for i, stored in enumerate(self.motifs):
            score = sum(1 for a, b in zip(t, stored)
                        if a != TRIT_NULL and b != TRIT_NULL and a == b)
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
        mask = (xx-cx)**2 + (yy-cy)**2 < r**2
        img[mask] = color
    elif shape == 'square':
        img[cy-r:cy+r, cx-r:cx+r] = color
    elif shape == 'triangle':
        for y in range(cy-r, cy+r):
            hw = max(0, int(r * (y-(cy-r)) / (2*r)))
            if hw > 0:
                img[y, cx-hw:cx+hw] = color
    elif shape == 'star':
        yy, xx = np.ogrid[:size, :size]
        angles = np.arctan2(yy-cy, xx-cx)
        dists = np.sqrt((xx-cx)**2 + (yy-cy)**2)
        star_r = r * (0.5 + 0.5 * np.abs(np.cos(2.5 * angles)))
        img[dists < star_r] = color

    noise = np.random.randint(-3, 4, img.shape, dtype=np.int16)
    return np.clip(img.astype(np.int16) + noise, 0, 255).astype(np.uint8)


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

def main():
    np.random.seed(42)

    print("=" * 75)
    print(" ArcLoom Vision v4 — Scanline Mosaics of Mosaics")
    print(" Each scanline → kernel → DSF. Column of DSFs → kernel again.")
    print("=" * 75)
    print()

    objects = {
        'brown_circle':  make_image('circle',   (139, 90, 43)),
        'red_circle':    make_image('circle',   (200, 30, 30)),
        'green_circle':  make_image('circle',   (30, 180, 30)),
        'blue_circle':   make_image('circle',   (30, 30, 200)),
        'white_square':  make_image('square',   (255, 255, 255)),
        'red_square':    make_image('square',   (200, 30, 30)),
        'red_triangle':  make_image('triangle', (200, 30, 30)),
        'blue_triangle': make_image('triangle', (30, 30, 200)),
        'blue_star':     make_image('star',     (30, 30, 200)),
        'green_star':    make_image('star',     (30, 180, 30)),
        'brown_circle2': make_image('circle',   (139, 90, 43)),
    }

    results = {}
    krim = Krimelack()

    for name, img in objects.items():
        strands, coupling, debug = process_image(img)
        results[name] = (strands, coupling)

        committed = krim.commit(strands, coupling, label=name)

        print(f"{name:18s}  {loom_str(strands)}  cc=[{trit_str(coupling)}]  "
              f"{'COMMIT' if committed else 'DUP':6s}  "
              f"2nd_gates: L={debug['lum_h_2nd_gates']} "
              f"R={debug['r_h_2nd_gates']} G={debug['g_h_2nd_gates']} B={debug['b_h_2nd_gates']}")

    # Pairwise — show all
    print()
    print("=" * 75)
    print(" Pairwise")
    print("=" * 75)

    names = list(results.keys())
    for i in range(len(names)):
        for j in range(i+1, len(names)):
            s_a, c_a = results[names[i]]
            s_b, c_b = results[names[j]]
            t_a = krim._flatten(s_a, c_a)
            t_b = krim._flatten(s_b, c_b)
            matches = comparable = 0
            for a, b in zip(t_a, t_b):
                if a != TRIT_NULL and b != TRIT_NULL:
                    comparable += 1
                    if a == b: matches += 1
            ratio = matches / comparable if comparable > 0 else 0
            tag = "SAME" if ratio > 0.85 else "DIFF" if ratio < 0.5 else "SIM"
            # Show pairs that are interesting
            same_shape = names[i].split('_')[-1].rstrip('2') == names[j].split('_')[-1].rstrip('2')
            same_color = '_'.join(names[i].split('_')[:-1]) == '_'.join(names[j].split('_')[:-1])
            marker = ""
            if same_shape and not same_color: marker = " [same shape, diff color]"
            elif same_color and not same_shape: marker = " [same color, diff shape]"
            elif names[j].endswith('2'): marker = " [same object]"

            if marker or ratio < 0.95:
                print(f"  {names[i]:18s} vs {names[j]:18s}: "
                      f"{matches}/{comparable} ({ratio:.0%}) {tag}{marker}")

    # Recall
    print()
    print("=" * 75)
    print(" Krimelack Recall")
    print("=" * 75)
    for name in results:
        s, c = results[name]
        idx, score, label = krim.recall(s, c)
        total = len(krim._flatten(s, c))
        ok = "OK" if label == name or label == name.rstrip('2') else "MISS"
        print(f"  {name:18s} → {label:18s} score={score}/{total} {ok}")

    # Shape discrimination summary
    print()
    print("=" * 75)
    print(" Summary: Can it discriminate?")
    print("=" * 75)

    # Same shape, different color
    pairs_shape = [
        ('brown_circle', 'red_circle', 'circle colors'),
        ('brown_circle', 'green_circle', 'circle colors'),
        ('brown_circle', 'blue_circle', 'circle colors'),
        ('red_triangle', 'blue_triangle', 'triangle colors'),
        ('blue_star', 'green_star', 'star colors'),
    ]
    print("  Same shape, different color (should be SIMILAR but distinguishable):")
    for a, b, desc in pairs_shape:
        if a in results and b in results:
            t_a = krim._flatten(*results[a])
            t_b = krim._flatten(*results[b])
            m = sum(1 for x, y in zip(t_a, t_b) if x != TRIT_NULL and y != TRIT_NULL and x == y)
            c = sum(1 for x, y in zip(t_a, t_b) if x != TRIT_NULL and y != TRIT_NULL)
            print(f"    {a:18s} vs {b:18s}: {m}/{c} ({m/c:.0%})" if c > 0 else f"    {a} vs {b}: no data")

    # Same color, different shape
    pairs_color = [
        ('red_circle', 'red_square', 'red shapes'),
        ('red_circle', 'red_triangle', 'red shapes'),
        ('red_square', 'red_triangle', 'red shapes'),
        ('blue_circle', 'blue_triangle', 'blue shapes'),
        ('blue_circle', 'blue_star', 'blue shapes'),
        ('blue_triangle', 'blue_star', 'blue shapes'),
        ('green_circle', 'green_star', 'green shapes'),
    ]
    print("  Same color, different shape (MUST be DIFFERENT):")
    for a, b, desc in pairs_color:
        if a in results and b in results:
            t_a = krim._flatten(*results[a])
            t_b = krim._flatten(*results[b])
            m = sum(1 for x, y in zip(t_a, t_b) if x != TRIT_NULL and y != TRIT_NULL and x == y)
            c = sum(1 for x, y in zip(t_a, t_b) if x != TRIT_NULL and y != TRIT_NULL)
            print(f"    {a:18s} vs {b:18s}: {m}/{c} ({m/c:.0%})" if c > 0 else f"    {a} vs {b}: no data")

    # Same object
    print("  Same object (MUST be SAME):")
    a, b = 'brown_circle', 'brown_circle2'
    t_a = krim._flatten(*results[a])
    t_b = krim._flatten(*results[b])
    m = sum(1 for x, y in zip(t_a, t_b) if x != TRIT_NULL and y != TRIT_NULL and x == y)
    c = sum(1 for x, y in zip(t_a, t_b) if x != TRIT_NULL and y != TRIT_NULL)
    print(f"    {a:18s} vs {b:18s}: {m}/{c} ({m/c:.0%})" if c > 0 else f"    {a} vs {b}: no data")


if __name__ == '__main__':
    main()
