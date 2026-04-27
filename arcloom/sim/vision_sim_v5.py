#!/usr/bin/env python3
"""
ArcLoom Vision v5 — Temporal Visual Field Recognition
=====================================================
The kernel processes TIME SERIES. A single image is not a time series.
A camera moving through a scene IS.

Show phase: hold bear in front of camera, rotate slightly.
  → sequence of frames → kernel → krimelack commits motifs.

Search phase: robot moves through course, camera streaming.
  → continuous frame sequence → kernel processes temporal changes
  → krimelack recall spikes when bear-pattern re-enters field.

What the kernel sees at each frame:
  - Mean color per region (R, G, B)
  - Edge density (how many boundaries)
  - Object coverage (how much of frame is non-background)
  - Symmetry

These change OVER TIME as the camera moves. The temporal pattern
of these changes is what the kernel reads.
"""

import numpy as np
from typing import List, Tuple

TRIT_NULL, TRIT_POS, TRIT_NEG = 0, 1, 2
DEAD_ZONE = 20

def trit_sign(t):
    return 1 if t == TRIT_POS else (-1 if t == TRIT_NEG else 0)


# ============================================================
# Frame feature extraction (NOT classification — just measurement)
# ============================================================

def frame_features(image):
    """
    Extract raw field measurements from one frame.
    These become the time series values the kernel processes.
    """
    img = image.astype(float) / 255.0
    h, w = img.shape[:2]

    gray = 0.299*img[:,:,0] + 0.587*img[:,:,1] + 0.114*img[:,:,2]

    # Edge density
    gy = np.diff(gray, axis=0)
    gx = np.diff(gray, axis=1)
    edge_mag = np.sqrt(gy[:, :-1]**2 + gx[:-1, :]**2)
    edge_density = np.mean(edge_mag > 0.08)

    # Object coverage (non-background pixels)
    bg_color = np.median(img.reshape(-1, 3), axis=0)
    diff_from_bg = np.sqrt(np.sum((img - bg_color)**2, axis=2))
    coverage = np.mean(diff_from_bg > 0.15)

    # Mean color of object region
    obj_mask = diff_from_bg > 0.15
    if np.sum(obj_mask) > 10:
        obj_r = np.mean(img[:,:,0][obj_mask])
        obj_g = np.mean(img[:,:,1][obj_mask])
        obj_b = np.mean(img[:,:,2][obj_mask])
    else:
        obj_r = obj_g = obj_b = 0.0

    # Color ratios (channel relationships, not absolute values)
    total = obj_r + obj_g + obj_b + 1e-10
    r_ratio = obj_r / total
    g_ratio = obj_g / total
    b_ratio = obj_b / total

    # Symmetry (left-right)
    left = gray[:, :w//2]
    right = np.fliplr(gray[:, w//2:w//2*2])
    if left.shape == right.shape and left.size > 0:
        sym = np.mean(1.0 - np.abs(left - right))
    else:
        sym = 0.5

    # Vertical extent: how many rows have object pixels?
    row_coverage = np.array([np.mean(diff_from_bg[r] > 0.15) for r in range(h)])
    v_extent = np.mean(row_coverage > 0.05)

    # Shape compactness: coverage / (v_extent * h_extent)
    col_coverage = np.array([np.mean(diff_from_bg[:, c] > 0.15) for c in range(w)])
    h_extent = np.mean(col_coverage > 0.05)
    compactness = coverage / (v_extent * h_extent + 1e-10)

    return {
        'edge_density': edge_density,
        'coverage': coverage,
        'r_ratio': r_ratio,
        'g_ratio': g_ratio,
        'b_ratio': b_ratio,
        'symmetry': sym,
        'v_extent': v_extent,
        'h_extent': h_extent,
        'compactness': compactness,
    }


# ============================================================
# Scene simulation: generate frame sequences
# ============================================================

def make_shape(shape, color, size=64, bg=(240, 240, 240)):
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
            if hw > 0: img[y, cx-hw:cx+hw] = color
    elif shape == 'star':
        yy, xx = np.ogrid[:size, :size]
        angles = np.arctan2(yy-cy, xx-cx)
        dists = np.sqrt((xx-cx)**2 + (yy-cy)**2)
        star_r = r * (0.5 + 0.5 * np.abs(np.cos(2.5 * angles)))
        img[dists < star_r] = color

    return img


def generate_approach_sequence(shape, color, num_frames=20):
    """
    Simulate camera approaching an object.
    Object starts small (far) and grows (closer).
    This is what the robot sees as it drives toward something.
    """
    frames = []
    sizes = np.linspace(20, 64, num_frames).astype(int)
    canvas_size = 64

    for s in sizes:
        obj = make_shape(shape, color, size=s)
        frame = np.full((canvas_size, canvas_size, 3), (240, 240, 240), dtype=np.uint8)
        # Center the object
        y_off = (canvas_size - s) // 2
        x_off = (canvas_size - s) // 2
        frame[y_off:y_off+s, x_off:x_off+s] = obj
        frames.append(frame)

    return frames


def generate_scan_sequence(objects_in_scene, canvas_width=320, canvas_height=64, num_frames=60):
    """
    Simulate camera panning across a scene with objects placed at different positions.

    objects_in_scene: list of (shape, color, x_position)
    Camera pans left to right.
    """
    # Build the full scene
    scene = np.full((canvas_height, canvas_width, 3), (240, 240, 240), dtype=np.uint8)
    obj_size = 48

    for shape, color, x_pos in objects_in_scene:
        obj = make_shape(shape, color, size=obj_size)
        y_off = (canvas_height - obj_size) // 2
        x_start = max(0, x_pos)
        x_end = min(canvas_width, x_pos + obj_size)
        obj_x_start = max(0, -x_pos)
        obj_x_end = obj_x_start + (x_end - x_start)
        if x_end > x_start:
            scene[y_off:y_off+obj_size, x_start:x_end] = obj[0:obj_size, obj_x_start:obj_x_end]

    # Generate frames by sliding a window across the scene
    view_width = 64
    frames = []
    positions = np.linspace(0, canvas_width - view_width, num_frames).astype(int)

    for pos in positions:
        frame = scene[:, pos:pos+view_width].copy()
        frames.append(frame)

    return frames, positions


# ============================================================
# Kernel on time series
# ============================================================

def kernel_on_series(signal):
    """L0-L4 on 1D signal. Returns per-gate DSF tuples."""
    n = len(signal)
    if n < 10:
        return []

    dF = np.diff(signal, prepend=signal[0])
    sigma = np.array([np.std(signal[max(0,i-8):i+1]) for i in range(n)])
    kappa = np.abs(np.diff(dF, prepend=dF[0]))

    D_t = np.abs(dF) + sigma + kappa
    boundary = D_t > 0.15  # slightly lower threshold for temporal data

    # Gates
    gate_data = []
    g_V, g_N, g_len = 0.0, 0, 0
    g_dFmax, g_dFmin = -1e9, 1e9

    for i in range(n):
        if boundary[i] and g_len >= 3:
            gate_data.append((g_len, g_V, g_N, g_dFmax, g_dFmin))
            g_V, g_N, g_len = 0.0, 0, 0
            g_dFmax, g_dFmin = -1e9, 1e9
        elif boundary[i]:
            g_V, g_N, g_len = 0.0, 0, 0
            g_dFmax, g_dFmin = -1e9, 1e9
        else:
            g_V += abs(dF[i]) + sigma[i] + kappa[i]
            g_len += 1
            g_dFmax = max(g_dFmax, dF[i])
            g_dFmin = min(g_dFmin, dF[i])
            if abs(dF[i]) < 0.001 and sigma[i] < 0.001:
                g_N += 1

    if g_len >= 3:
        gate_data.append((g_len, g_V, g_N, g_dFmax, g_dFmin))

    if not gate_data:
        return []

    # L2-L3-L4
    dsfs = []
    R_prev, R_prev2, D_prev = 0.0, 0.0, 0

    for T, V, N, dFmax, dFmin in gate_data:
        w = min(1.0, V / 256)
        cv = min(1.0, max(0, dFmax-dFmin) / 256)
        Ng = 1.0 if 2*N >= T else 0.0
        U = min(1.0, max(0, 0.4 + 0.3*cv + 0.3*Ng))

        R = 0.2 * (w + cv + w + 1.0/(2.0) + 1.0-U)
        dR = R - R_prev
        D = 1 if dR > 0.03 else (-1 if dR < -0.03 else 0)
        M = R - 2*R_prev + R_prev2
        rev = (D == 1 and D_prev == -1) or (D == -1 and D_prev == 1)

        dsfs.append({'R': R, 'D': D, 'M': M, 'rev': rev, 'U': U, 'w': w, 'V': V, 'cv': cv})
        R_prev2, R_prev, D_prev = R_prev, R, D

    return dsfs


# ============================================================
# Process a frame sequence → per-feature time series → kernel → motif
# ============================================================

def process_sequence(frames):
    """
    Extract features from each frame, creating time series.
    Run kernel on each feature's time series.
    The DSF patterns across features = the object's temporal signature.
    """
    # Extract features per frame
    feat_series = {k: [] for k in ['edge_density', 'coverage', 'r_ratio', 'g_ratio',
                                    'b_ratio', 'symmetry', 'compactness']}

    for frame in frames:
        feats = frame_features(frame)
        for k in feat_series:
            feat_series[k].append(feats[k])

    # Add cross-channel signals — these carry color identity
    n = len(frames)
    feat_series['rg_diff'] = [feat_series['r_ratio'][i] - feat_series['g_ratio'][i] for i in range(n)]
    feat_series['gb_diff'] = [feat_series['g_ratio'][i] - feat_series['b_ratio'][i] for i in range(n)]
    feat_series['rb_diff'] = [feat_series['r_ratio'][i] - feat_series['b_ratio'][i] for i in range(n)]

    # Shape signals — coverage rate of change tells shape
    cov = feat_series['coverage']
    feat_series['cov_accel'] = [0] + [cov[i] - 2*cov[i-1] + (cov[i-2] if i > 1 else cov[0]) for i in range(1, n)]

    # Convert to numpy
    for k in feat_series:
        feat_series[k] = np.array(feat_series[k])

    # Run kernel on each feature's time series
    feat_dsfs = {}
    for k, signal in feat_series.items():
        feat_dsfs[k] = kernel_on_series(signal)

    return feat_series, feat_dsfs


def sequence_to_loom(feat_dsfs):
    """
    Encode temporal DSF patterns as loom strands.

    Each strand gets the temporal pattern from one feature channel.
    The coupling between strands captures how features relate
    over time — which IS the object identity.
    """
    def encode_dsfs(dsfs):
        """3 trits from a DSF sequence."""
        if not dsfs:
            return [TRIT_NULL, TRIT_NULL, TRIT_NULL]

        # Trit 0: dominant direction
        pos = sum(1 for d in dsfs if d['D'] > 0)
        neg = sum(1 for d in dsfs if d['D'] < 0)
        t0 = TRIT_POS if pos > neg + 1 else (TRIT_NEG if neg > pos + 1 else TRIT_NULL)

        # Trit 1: mean resonance
        mR = np.mean([d['R'] for d in dsfs])
        t1 = TRIT_POS if mR > 0.35 else (TRIT_NEG if mR < 0.15 else TRIT_NULL)

        # Trit 2: reversals (field instability)
        revs = sum(1 for d in dsfs if d['rev'])
        rev_rate = revs / len(dsfs)
        t2 = TRIT_POS if rev_rate > 0.3 else (TRIT_NEG if rev_rate < 0.05 else TRIT_NULL)

        return [t0, t1, t2]

    # Also encode based on the LEVEL of the signals, not just DSF structure
    def level_trits(feat_series_data, key, hi, lo):
        """Encode the mean level of a signal as a trit."""
        if key not in feat_series_data:
            return TRIT_NULL
        vals = feat_series_data[key]
        if len(vals) == 0:
            return TRIT_NULL
        m = np.mean(vals)
        if m > hi: return TRIT_POS
        if m < lo: return TRIT_NEG
        return TRIT_NULL

    # We need feat_series passed in — add it to the function
    # For now use the DSFs which capture temporal structure
    strands = {
        # Shape: edge density temporal pattern + coverage acceleration
        'distance': encode_dsfs(feat_dsfs.get('edge_density', [])),
        'direction': encode_dsfs(feat_dsfs.get('cov_accel', [])),
        # Color: cross-channel differences (these carry color identity)
        'accel': encode_dsfs(feat_dsfs.get('rg_diff', [])),
        'cam_edge': encode_dsfs(feat_dsfs.get('gb_diff', [])),
        'cam_motion': encode_dsfs(feat_dsfs.get('rb_diff', [])),
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

    def flatten(self, strands):
        t = []
        for k in ['distance','direction','accel','cam_edge','cam_motion',
                   'context','momentum','decision']:
            t.extend(strands[k])
        return t

    def commit(self, strands, label=""):
        t = self.flatten(strands)
        for stored in self.motifs:
            if stored == t: return False
        self.motifs.append(t)
        self.labels.append(label)
        return True

    def recall(self, strands):
        t = self.flatten(strands)
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

    def continuous_recall(self, feat_series, window=10):
        """
        Sliding window recall over a continuous stream.
        At each position, process the last `window` frames,
        run the kernel, and check krimelack recall.
        Returns per-position: (best_label, score)
        """
        n = len(list(feat_series.values())[0])
        results = []

        for end in range(window, n+1):
            # Slice window
            window_series = {k: v[end-window:end] for k, v in feat_series.items()}
            # Kernel on each feature
            feat_dsfs = {}
            for k, signal in window_series.items():
                feat_dsfs[k] = kernel_on_series(signal)
            # Encode and recall
            loom = sequence_to_loom(feat_dsfs)
            idx, score, label = self.recall(loom)
            results.append((label, score))

        return results


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
# Tests
# ============================================================

def main():
    np.random.seed(42)

    print("=" * 75)
    print(" ArcLoom Vision v5 — Temporal Visual Field Recognition")
    print("=" * 75)
    print()

    krim = Krimelack()

    # ---- SHOW PHASE: learn objects by approaching them ----
    print("SHOW PHASE: Camera approaches each object")
    print("-" * 75)

    objects_to_learn = {
        'brown_bear': ('circle', (139, 90, 43)),
        'red_cup': ('square', (200, 30, 30)),
        'blue_star': ('star', (30, 30, 200)),
        'green_tri': ('triangle', (30, 180, 30)),
    }

    for name, (shape, color) in objects_to_learn.items():
        frames = generate_approach_sequence(shape, color, num_frames=20)
        feat_series, feat_dsfs = process_sequence(frames)
        loom = sequence_to_loom(feat_dsfs)
        committed = krim.commit(loom, label=name)

        # Show feature evolution
        ed = feat_series['edge_density']
        cov = feat_series['coverage']
        r = feat_series['r_ratio']

        print(f"  {name:15s}  {loom_str(loom)}  {'COMMIT' if committed else 'DUP':6s}")
        print(f"                   edges: {ed[0]:.3f}→{ed[-1]:.3f}  "
              f"coverage: {cov[0]:.3f}→{cov[-1]:.3f}  "
              f"R_ratio: {r[0]:.3f}→{r[-1]:.3f}")

    # ---- Repeat show to verify stability ----
    print()
    print("VERIFY: Show same objects again")
    print("-" * 75)

    for name, (shape, color) in objects_to_learn.items():
        frames = generate_approach_sequence(shape, color, num_frames=20)
        _, feat_dsfs = process_sequence(frames)
        loom = sequence_to_loom(feat_dsfs)
        idx, score, label = krim.recall(loom)
        ok = "OK" if label == name else "MISS"
        print(f"  {name:15s} → {label:15s} score={score}/24 {ok}")

    # ---- SEARCH PHASE: scan across scene ----
    print()
    print("SEARCH PHASE: Camera pans across scene")
    print("-" * 75)

    # Place objects in a scene
    scene_objects = [
        ('square', (200, 30, 30), 30),     # red cup at x=30
        ('triangle', (30, 180, 30), 120),   # green triangle at x=120
        ('circle', (139, 90, 43), 210),     # brown bear at x=210
    ]

    frames, positions = generate_scan_sequence(scene_objects, canvas_width=320,
                                                canvas_height=64, num_frames=60)

    # Extract features for the whole scan
    feat_series = {k: [] for k in ['edge_density', 'coverage', 'r_ratio', 'g_ratio',
                                    'b_ratio', 'symmetry', 'compactness']}
    for frame in frames:
        feats = frame_features(frame)
        for k in feat_series:
            feat_series[k].append(feats[k])
    for k in feat_series:
        feat_series[k] = np.array(feat_series[k])

    # Continuous recall with sliding window
    results = krim.continuous_recall(feat_series, window=10)

    print(f"  Scene: red_cup@30, green_tri@120, brown_bear@210")
    print(f"  {'Frame':>5s} {'Pos':>4s}  {'Match':15s} {'Score':>5s}  {'Edge':>6s} {'Cov':>6s}")
    print(f"  {'-----':>5s} {'----':>4s}  {'-----':15s} {'-----':>5s}  {'----':>6s} {'---':>6s}")

    for i, (label, score) in enumerate(results):
        frame_idx = i + 10  # window offset
        if frame_idx < len(positions):
            pos = positions[frame_idx]
            ed = feat_series['edge_density'][frame_idx]
            cov = feat_series['coverage'][frame_idx]
            marker = " <<<" if score > 6 else ""
            if label:
                print(f"  {frame_idx:5d} {pos:4d}  {label:15s} {score:5d}  "
                      f"{ed:6.3f} {cov:6.3f}{marker}")

    # ---- DISCRIMINATION TEST ----
    print()
    print("DISCRIMINATION: Different approach sequences")
    print("-" * 75)

    test_objects = {
        'brown_bear_2': ('circle', (139, 90, 43)),    # same bear
        'red_bear': ('circle', (200, 30, 30)),         # same shape diff color
        'brown_square': ('square', (139, 90, 43)),     # same color diff shape
        'blue_tri': ('triangle', (30, 30, 200)),       # different everything
    }

    for name, (shape, color) in test_objects.items():
        frames = generate_approach_sequence(shape, color, num_frames=20)
        _, feat_dsfs = process_sequence(frames)
        loom = sequence_to_loom(feat_dsfs)
        idx, score, label = krim.recall(loom)
        ok = "OK" if (name == 'brown_bear_2' and label == 'brown_bear') else ""
        print(f"  {name:18s} → {label:15s} score={score}/24 {ok}")

    print()
    print(f"Krimelack: {len(krim.motifs)} motifs stored")


if __name__ == '__main__':
    main()
