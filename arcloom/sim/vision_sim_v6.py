#!/usr/bin/env python3
"""
ArcLoom Vision v6 — Raw Pixel Temporal Streams
===============================================
Stop extracting features. Feed raw pixels to the kernel.

Take the MIDDLE SCANLINE of each frame. As the camera approaches
an object, that scanline changes: background → edge → object → edge → background.
The shape of this transition is different for each object.

For a circle approaching: the object region WIDENS as a curve.
For a square approaching: the object region WIDENS as a step.
The RGB values in the object region ARE the color.

Feed the middle-scanline pixel values directly. Each frame = one
data point per pixel. Concatenate frames = temporal signal.
The kernel finds structure in how pixels change over time.
"""

import numpy as np
from typing import List, Tuple

TRIT_NULL, TRIT_POS, TRIT_NEG = 0, 1, 2
DEAD_ZONE = 20

def trit_sign(t):
    return 1 if t == TRIT_POS else (-1 if t == TRIT_NEG else 0)


# ============================================================
# Kernel
# ============================================================

def kernel(signal, tau=0.15, min_gate=3):
    """L0-L4 on 1D signal. Returns list of gate DSFs."""
    n = len(signal)
    if n < 8: return []

    dF = np.diff(signal, prepend=signal[0])
    sigma = np.array([np.std(signal[max(0,i-8):i+1]) for i in range(n)])
    kappa = np.abs(np.diff(dF, prepend=dF[0]))
    D_t = np.abs(dF) + sigma + kappa
    boundary = D_t > tau

    gates = []
    g_V, g_len, g_dFmax, g_dFmin, g_N = 0.0, 0, -1e9, 1e9, 0

    for i in range(n):
        if boundary[i] and g_len >= min_gate:
            gates.append((g_len, g_V, g_N, g_dFmax, g_dFmin))
            g_V, g_len, g_dFmax, g_dFmin, g_N = 0.0, 0, -1e9, 1e9, 0
        elif boundary[i]:
            g_V, g_len, g_dFmax, g_dFmin, g_N = 0.0, 0, -1e9, 1e9, 0
        else:
            g_V += abs(dF[i]) + sigma[i] + kappa[i]
            g_len += 1
            g_dFmax = max(g_dFmax, dF[i])
            g_dFmin = min(g_dFmin, dF[i])
            if abs(dF[i]) < 0.001: g_N += 1

    if g_len >= min_gate:
        gates.append((g_len, g_V, g_N, g_dFmax, g_dFmin))

    if not gates: return []

    dsfs = []
    R_prev, R_prev2, D_prev = 0.0, 0.0, 0
    for T, V, N, dFmax, dFmin in gates:
        w = min(1.0, V / 256)
        cv = min(1.0, max(0, dFmax-dFmin) / 256)
        Ng = 1.0 if 2*N >= T else 0.0
        U = min(1.0, max(0, 0.4 + 0.3*cv + 0.3*Ng))
        R = 0.2 * (w + cv + w + 0.5 + 1.0 - U)
        dR = R - R_prev
        D = 1 if dR > 0.03 else (-1 if dR < -0.03 else 0)
        M = R - 2*R_prev + R_prev2
        rev = (D == 1 and D_prev == -1) or (D == -1 and D_prev == 1)
        dsfs.append({'R': R, 'D': D, 'M': M, 'rev': rev, 'w': w, 'V': V, 'T': T})
        R_prev2, R_prev, D_prev = R_prev, R, D

    return dsfs


# ============================================================
# Image generation
# ============================================================

def make_shape(shape, color, size=64, bg=(240, 240, 240)):
    img = np.full((size, size, 3), bg, dtype=np.uint8)
    cx, cy, r = size//2, size//2, size//3
    if shape == 'circle':
        yy, xx = np.ogrid[:size, :size]
        img[(xx-cx)**2 + (yy-cy)**2 < r**2] = color
    elif shape == 'square':
        img[cy-r:cy+r, cx-r:cx+r] = color
    elif shape == 'triangle':
        for y in range(cy-r, cy+r):
            hw = max(1, int(r * (y-(cy-r)) / (2*r)))
            img[y, cx-hw:cx+hw] = color
    elif shape == 'star':
        yy, xx = np.ogrid[:size, :size]
        a = np.arctan2(yy-cy, xx-cx)
        d = np.sqrt((xx-cx)**2 + (yy-cy)**2)
        img[d < r * (0.5 + 0.5*np.abs(np.cos(2.5*a)))] = color
    return img


def approach_sequence(shape, color, num_frames=30, canvas=80):
    """Object grows from small to large as camera approaches."""
    frames = []
    for s in np.linspace(16, canvas-4, num_frames).astype(int):
        obj = make_shape(shape, color, size=s)
        frame = np.full((canvas, canvas, 3), (240,240,240), dtype=np.uint8)
        y0 = (canvas-s)//2
        x0 = (canvas-s)//2
        frame[y0:y0+s, x0:x0+s] = obj
        frames.append(frame)
    return frames


# ============================================================
# Extract temporal pixel streams from frame sequence
# ============================================================

def extract_pixel_streams(frames):
    """
    For each frame, take the middle scanline.
    For each pixel position, track its value across frames.
    This gives per-pixel temporal signals.

    Also extract: center pixel, quarter pixels, edge positions.
    These temporal signals carry both shape and color information.
    """
    h, w = frames[0].shape[:2]
    mid_y = h // 2
    n_frames = len(frames)

    # Normalize
    norm_frames = [f.astype(float) / 255.0 for f in frames]

    streams = {}

    # Center pixel RGB over time (object interior)
    cx = w // 2
    streams['center_R'] = np.array([f[mid_y, cx, 0] for f in norm_frames])
    streams['center_G'] = np.array([f[mid_y, cx, 1] for f in norm_frames])
    streams['center_B'] = np.array([f[mid_y, cx, 2] for f in norm_frames])

    # Quarter pixel (between center and edge — captures edge transition timing)
    qx = w // 4
    streams['quarter_R'] = np.array([f[mid_y, qx, 0] for f in norm_frames])
    streams['quarter_G'] = np.array([f[mid_y, qx, 1] for f in norm_frames])
    streams['quarter_B'] = np.array([f[mid_y, qx, 2] for f in norm_frames])

    # 3/4 pixel (other side)
    q3x = 3 * w // 4
    streams['threequarter_R'] = np.array([f[mid_y, q3x, 0] for f in norm_frames])
    streams['threequarter_G'] = np.array([f[mid_y, q3x, 1] for f in norm_frames])
    streams['threequarter_B'] = np.array([f[mid_y, q3x, 2] for f in norm_frames])

    # Width of object at middle scanline over time
    # (count non-background pixels)
    bg = np.array([240, 240, 240]) / 255.0
    widths = []
    for f in norm_frames:
        row = f[mid_y]
        diff = np.sqrt(np.sum((row - bg)**2, axis=1))
        widths.append(np.sum(diff > 0.1))
    streams['obj_width'] = np.array(widths, dtype=float)

    # Vertical height at center column over time
    heights = []
    for f in norm_frames:
        col = f[:, cx]
        diff = np.sqrt(np.sum((col - bg)**2, axis=1))
        heights.append(np.sum(diff > 0.1))
    streams['obj_height'] = np.array(heights, dtype=float)

    # Width-to-height ratio over time (shape signature!)
    # Circle: ratio ≈ 1.0 always
    # Square: ratio ≈ 1.0 always
    # Triangle: ratio increases (wider at bottom)
    streams['wh_ratio'] = streams['obj_width'] / (streams['obj_height'] + 1e-10)

    # Cross-channel: R-G, G-B at center (color identity)
    streams['center_RG'] = streams['center_R'] - streams['center_G']
    streams['center_GB'] = streams['center_G'] - streams['center_B']

    return streams


# ============================================================
# Process streams through kernel → loom state
# ============================================================

def dsf_summary(dsfs):
    """Summarize a DSF sequence as 3 trits."""
    if not dsfs:
        return [TRIT_NULL, TRIT_NULL, TRIT_NULL]

    n = len(dsfs)

    # T0: dominant direction
    pos = sum(1 for d in dsfs if d['D'] > 0)
    neg = sum(1 for d in dsfs if d['D'] < 0)
    if pos > neg + 1: t0 = TRIT_POS
    elif neg > pos + 1: t0 = TRIT_NEG
    else: t0 = TRIT_NULL

    # T1: gate volume variance (smooth approach vs jagged)
    vols = [d['V'] for d in dsfs]
    if len(vols) > 1:
        vol_var = np.var(vols) / (np.mean(vols)**2 + 1e-10)
        t1 = TRIT_POS if vol_var > 0.5 else (TRIT_NEG if vol_var < 0.1 else TRIT_NULL)
    else:
        t1 = TRIT_NULL

    # T2: gate count (structural complexity)
    t2 = TRIT_POS if n > 5 else (TRIT_NEG if n <= 2 else TRIT_NULL)

    return [t0, t1, t2]


def streams_to_loom(streams):
    """Run kernel on each stream, encode as loom strands."""

    # Shape streams → distance and direction strands
    width_dsfs = kernel(streams['obj_width'], tau=0.5, min_gate=2)
    height_dsfs = kernel(streams['obj_height'], tau=0.5, min_gate=2)

    # Color streams → accel, cam_edge, cam_motion strands
    rg_dsfs = kernel(streams['center_RG'], tau=0.05, min_gate=2)
    gb_dsfs = kernel(streams['center_GB'], tau=0.05, min_gate=2)

    # Edge timing → how fast does the edge reach the quarter point?
    qr_dsfs = kernel(streams['quarter_R'], tau=0.05, min_gate=2)

    strands = {
        'distance': dsf_summary(width_dsfs),
        'direction': dsf_summary(height_dsfs),
        'accel': dsf_summary(rg_dsfs),
        'cam_edge': dsf_summary(gb_dsfs),
        'cam_motion': dsf_summary(qr_dsfs),
    }

    # Also encode raw signal LEVELS as additional trit info
    # This captures what the kernel can't: absolute color
    center_R_mean = np.mean(streams['center_R'][-5:])  # last 5 frames (close up)
    center_G_mean = np.mean(streams['center_G'][-5:])
    center_B_mean = np.mean(streams['center_B'][-5:])

    # Color encoding from signal levels (always apply — DSFs are often empty for constant signals)
    rg_level = center_R_mean - center_G_mean
    gb_level = center_G_mean - center_B_mean
    rb_level = center_R_mean - center_B_mean

    strands['accel'] = [
        # R vs G: warm vs cool/natural
        TRIT_POS if rg_level > 0.05 else (TRIT_NEG if rg_level < -0.05 else TRIT_NULL),
        # R absolute: high red or not
        TRIT_POS if center_R_mean > 0.5 else (TRIT_NEG if center_R_mean < 0.2 else TRIT_NULL),
        # G absolute: high green or not
        TRIT_POS if center_G_mean > 0.5 else (TRIT_NEG if center_G_mean < 0.2 else TRIT_NULL),
    ]

    strands['cam_edge'] = [
        # G vs B: natural vs cool
        TRIT_POS if gb_level > 0.05 else (TRIT_NEG if gb_level < -0.05 else TRIT_NULL),
        # B absolute: high blue or not
        TRIT_POS if center_B_mean > 0.5 else (TRIT_NEG if center_B_mean < 0.2 else TRIT_NULL),
        # R vs B: warm vs cool extreme
        TRIT_POS if rb_level > 0.15 else (TRIT_NEG if rb_level < -0.15 else TRIT_NULL),
    ]

    # cam_motion: encode using quarter-pixel (edge timing) + brightness
    brightness = (center_R_mean + center_G_mean + center_B_mean) / 3.0
    saturation = max(center_R_mean, center_G_mean, center_B_mean) - min(center_R_mean, center_G_mean, center_B_mean)
    dominant = 'R' if center_R_mean >= center_G_mean and center_R_mean >= center_B_mean else \
               'G' if center_G_mean >= center_B_mean else 'B'

    strands['cam_motion'] = [
        # Brightness
        TRIT_POS if brightness > 0.6 else (TRIT_NEG if brightness < 0.3 else TRIT_NULL),
        # Saturation (colorful vs gray)
        TRIT_POS if saturation > 0.3 else (TRIT_NEG if saturation < 0.1 else TRIT_NULL),
        # Dominant channel identity
        TRIT_POS if dominant == 'R' else (TRIT_NEG if dominant == 'B' else TRIT_NULL),
    ]

    # Width/height ratio in last frames → shape
    wh_late = np.mean(streams['wh_ratio'][-5:])
    width_late = np.mean(streams['obj_width'][-5:])
    if not width_dsfs:
        strands['distance'] = [
            TRIT_POS if wh_late > 1.2 else (TRIT_NEG if wh_late < 0.8 else TRIT_NULL),
            TRIT_POS if width_late > 30 else (TRIT_NEG if width_late < 10 else TRIT_NULL),
            TRIT_NULL,
        ]

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
    dcsn_w = [
        [15, 10, 5, 10, 5, 0, 5, 0, 0, 10, 5, 0, 5, 0, 0, 15, 10, 5, 10, 5, 0],
        [5, 0, 0, 5, 0, 0, 15, 10, 5, 5, 0, 0, 5, 0, 0, 5, 0, 0, 15, 10, 5],
        [5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 10, 10, 10, 10, 10, 10],
    ]

    def settle(weights, trits):
        total = sum(w * trit_sign(t) for w, t in zip(weights, trits))
        if total > DEAD_ZONE: return TRIT_POS
        if total < -DEAD_ZONE: return TRIT_NEG
        return TRIT_NULL

    strands['context'] = [settle(ctx_w[i], input_trits) for i in range(3)]
    strands['momentum'] = [settle(mmtm_w[i], input_trits) for i in range(3)]
    all_21 = input_trits + strands['context'] + strands['momentum']
    strands['decision'] = [settle(dcsn_w[i], all_21) for i in range(3)]

    return strands


# ============================================================
# Krimelack
# ============================================================

class Krimelack:
    def __init__(self):
        self.motifs = []
        self.labels = []

    def flatten(self, s):
        t = []
        for k in ['distance','direction','accel','cam_edge','cam_motion',
                   'context','momentum','decision']:
            t.extend(s[k])
        return t

    def commit(self, s, label=""):
        t = self.flatten(s)
        for m in self.motifs:
            if m == t: return False
        self.motifs.append(t)
        self.labels.append(label)
        return True

    def recall(self, s):
        t = self.flatten(s)
        best_i, best_s = -1, 0
        for i, m in enumerate(self.motifs):
            sc = sum(1 for a, b in zip(t, m) if a != TRIT_NULL and b != TRIT_NULL and a == b)
            if sc > best_s: best_s, best_i = sc, i
        if best_i >= 0: return best_i, best_s, self.labels[best_i]
        return None, 0, ""


def trit_str(trits):
    return ''.join({0:'0', 1:'+', 2:'-'}.get(t,'?') for t in trits)

def loom_str(s):
    ns = [('dist','distance'), ('dirn','direction'), ('accl','accel'),
          ('cedg','cam_edge'), ('cmot','cam_motion'),
          ('ctxt','context'), ('mmtm','momentum'), ('dcsn','decision')]
    return ' '.join(f"{n}=[{trit_str(s[k])}]" for n, k in ns)


# ============================================================
# Run
# ============================================================

def main():
    np.random.seed(42)

    print("=" * 75)
    print(" ArcLoom Vision v6 — Raw Pixel Temporal Streams")
    print("=" * 75)
    print()

    krim = Krimelack()

    learn = {
        'brown_bear':  ('circle',   (139, 90, 43)),
        'red_cup':     ('square',   (200, 30, 30)),
        'blue_star':   ('star',     (30, 30, 200)),
        'green_tri':   ('triangle', (30, 180, 30)),
    }

    print("SHOW PHASE")
    print("-" * 75)
    for name, (shape, color) in learn.items():
        frames = approach_sequence(shape, color, num_frames=30, canvas=80)
        streams = extract_pixel_streams(frames)
        loom = streams_to_loom(streams)
        committed = krim.commit(loom, label=name)

        # Debug: show key signal values
        cr = streams['center_R']
        cg = streams['center_G']
        cb = streams['center_B']
        ow = streams['obj_width']

        print(f"  {name:15s}  {loom_str(loom)}  {'COMMIT' if committed else 'DUP'}")
        print(f"    center RGB final: ({cr[-1]:.2f}, {cg[-1]:.2f}, {cb[-1]:.2f})  "
              f"width: {ow[0]:.0f}→{ow[-1]:.0f}  "
              f"R-G={cr[-1]-cg[-1]:.2f}  G-B={cg[-1]-cb[-1]:.2f}")

    print()
    print("VERIFY (same objects again)")
    print("-" * 75)
    for name, (shape, color) in learn.items():
        frames = approach_sequence(shape, color, num_frames=30, canvas=80)
        streams = extract_pixel_streams(frames)
        loom = streams_to_loom(streams)
        _, score, label = krim.recall(loom)
        ok = "OK" if label == name else "MISS"
        print(f"  {name:15s} → {label:15s} score={score}/24 {ok}")

    print()
    print("DISCRIMINATION")
    print("-" * 75)
    tests = {
        'brown_bear_2':  ('circle',   (139, 90, 43)),   # same
        'red_circle':    ('circle',   (200, 30, 30)),    # same shape, diff color
        'blue_circle':   ('circle',   (30, 30, 200)),    # same shape, diff color
        'brown_square':  ('square',   (139, 90, 43)),    # same color, diff shape
        'brown_tri':     ('triangle', (139, 90, 43)),    # same color, diff shape
        'red_star':      ('star',     (200, 30, 30)),    # diff both
        'white_square':  ('square',   (255, 255, 255)),  # white
    }

    for name, (shape, color) in tests.items():
        frames = approach_sequence(shape, color, num_frames=30, canvas=80)
        streams = extract_pixel_streams(frames)
        loom = streams_to_loom(streams)
        _, score, label = krim.recall(loom)
        t_q = krim.flatten(loom)
        # Also show pairwise match to each committed object
        matches = {}
        for i, m in enumerate(krim.motifs):
            sc = sum(1 for a, b in zip(t_q, m) if a != TRIT_NULL and b != TRIT_NULL and a == b)
            tc = sum(1 for a, b in zip(t_q, m) if a != TRIT_NULL and b != TRIT_NULL)
            matches[krim.labels[i]] = f"{sc}/{tc}"

        print(f"  {name:18s}  {loom_str(loom)}")
        print(f"    recall → {label:15s} score={score}/24  "
              f"per-object: {matches}")

    print()
    print(f"Krimelack: {len(krim.motifs)} motifs")


if __name__ == '__main__':
    main()
