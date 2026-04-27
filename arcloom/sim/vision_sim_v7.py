#!/usr/bin/env python3
"""
ArcLoom Vision v7 — Raw Pixels In, DSF Out, Krimelack Commits
=============================================================
No feature extraction. No preprocessing. No width computation.
No color ratios. No gates inspection.

Raw pixel values from camera → kernel (black box) → L4 DSF out → krimelack.

The kernel does what it does. We don't look inside. We feed it
and read the output.
"""

import numpy as np
from typing import List, Tuple, Optional

# ============================================================
# Kernel — BLACK BOX
# Exact constants from Verilog. Feed signal in, get DSF sequence out.
# ============================================================

def kernel(signal: np.ndarray) -> List[dict]:
    """
    L0 → L1 → L2 → L3 → L4.
    Input: 1D signal (raw pixel values, 0.0–1.0).
    Output: list of L4 DSF dicts, one per gate.
    """
    n = len(signal)
    if n < 10:
        return []

    # L0: derivatives
    dF = np.diff(signal, prepend=signal[0])
    sigma = np.array([np.std(signal[max(0, i-8):i+1]) for i in range(n)])
    kappa = np.abs(np.diff(dF, prepend=dF[0]))
    D_t = np.abs(dF) + sigma + kappa
    boundary = D_t > 0.20  # TAU_D from Verilog

    # L1: gate formation
    # Key addition: capture the boundary dF that OPENS each gate.
    # This is where color/intensity information lives in image signals.
    gate_descriptors = []
    g_V, g_len, g_N = 0.0, 0, 0
    g_dFmax, g_dFmin = -1e9, 1e9
    g_entry_dF = 0.0  # the dF at the boundary that started this gate
    g_mean_level = 0.0  # mean signal level inside gate

    for i in range(n):
        if boundary[i] and g_len >= 4:  # MIN_GATE_LEN from Verilog
            projs = set()
            for ts, vs, rs in [(4,4,4), (3,3,3), (2,2,2)]:
                projs.add((g_len >> ts, int(g_V) >> vs, g_len >> rs))
            # Volume includes the entry boundary magnitude
            entry_V = abs(g_entry_dF) * 256  # scale boundary dF to be significant
            gate_descriptors.append({
                'T': g_len, 'V': g_V + entry_V, 'N': g_N,
                'dFmax': max(g_dFmax, g_entry_dF),
                'dFmin': min(g_dFmin, g_entry_dF),
                'C': min(3, len(projs)),
                'entry_dF': g_entry_dF,
                'mean_level': g_mean_level / max(1, g_len),
            })
            g_entry_dF = dF[i]  # this boundary opens the next gate
            g_V, g_len, g_N = 0.0, 0, 0
            g_dFmax, g_dFmin = -1e9, 1e9
            g_mean_level = 0.0
        elif boundary[i]:
            g_entry_dF = dF[i]
            g_V, g_len, g_N = 0.0, 0, 0
            g_dFmax, g_dFmin = -1e9, 1e9
            g_mean_level = 0.0
        else:
            g_V += abs(dF[i]) + sigma[i] + kappa[i]
            g_len += 1
            g_dFmax = max(g_dFmax, dF[i])
            g_dFmin = min(g_dFmin, dF[i])
            g_mean_level += signal[i]
            if abs(dF[i]) < 0.001 and sigma[i] < 0.001:
                g_N += 1

    if g_len >= 4:
        projs = set()
        for ts, vs, rs in [(4,4,4), (3,3,3), (2,2,2)]:
            projs.add((g_len >> ts, int(g_V) >> vs, g_len >> rs))
        entry_V = abs(g_entry_dF) * 256
        gate_descriptors.append({
            'T': g_len, 'V': g_V + entry_V, 'N': g_N,
            'dFmax': max(g_dFmax, g_entry_dF),
            'dFmin': min(g_dFmin, g_entry_dF),
            'C': min(3, len(projs)),
            'entry_dF': g_entry_dF,
            'mean_level': g_mean_level / max(1, g_len),
        })

    if not gate_descriptors:
        return []

    # L2 → L3 → L4 per gate
    dsf_sequence = []
    R_prev, R_prev2, D_prev = 0.0, 0.0, 0

    for g in gate_descriptors:
        # L2
        w = min(1.0, g['V'] / 256.0)
        cv = min(1.0, max(0, g['dFmax'] - g['dFmin']) / 256.0)
        Ng = 1.0 if 2 * g['N'] >= g['T'] else 0.0
        U = min(1.0, max(0, 0.4 * (g['C'] - 1) / 2.0 + 0.3 * cv + 0.3 * Ng))
        IAS = U > 0.9

        # L3
        R_vec = [w, cv, w, 1.0 / (1.0 + g['C']), 1.0 - U]
        R = 0.2 * sum(R_vec)
        Hyst = abs(R - R_prev) > 0.3125
        g_k = U <= 0.85 and not IAS and not Hyst

        # L4
        dR = R - R_prev
        D = 1 if dR > 0.05 else (-1 if dR < -0.05 else 0)
        M = R - 2 * R_prev + R_prev2
        R_rev = (D == 1 and D_prev == -1) or (D == -1 and D_prev == 1)
        U_star = min(1.0, U + 0.15 * (1 if Hyst else 0) + 0.20 * (1 if IAS else 0))

        dsf_sequence.append({
            'D': D, 'M': M, 'R_rev': R_rev, 'U_star': U_star,
            'R': R, 'w': w, 'cv': cv, 'C': g['C']
        })

        R_prev2, R_prev, D_prev = R_prev, R, D

    return dsf_sequence


# ============================================================
# Krimelack — stores DSF sequences
# ============================================================

class Krimelack:
    """
    Stores DSF sequences from L4. Recalls by matching DSF patterns.
    The DSF sequence IS the structural identity.
    """
    def __init__(self, max_motifs=32):
        self.motifs = []      # list of DSF sequence fingerprints
        self.labels = []
        self.max_motifs = max_motifs

    def dsf_fingerprint(self, dsf_seq: List[dict]) -> tuple:
        """
        Convert a DSF sequence into a hashable fingerprint.
        Preserves the SEQUENCE — order matters.

        Quantize each DSF value to 9 levels (-4 to +4) instead of 3.
        More resolution = better discrimination without losing
        the ternary structure (still balanced around zero).
        """
        fp = []
        for d in dsf_seq:
            D = d['D']  # already -1, 0, +1
            # Use the FULL DSF — all values carry information
            # Scale to integers preserving precision where it matters
            R_q = int(round(d['R'] * 10000))      # resonance: 4 decimal places
            w_q = int(round(d['w'] * 10000))       # salience: THIS carries color info
            cv_q = int(round(d['cv'] * 10000))     # contrast
            U_q = int(round(d['U_star'] * 10000))  # uncertainty
            M_q = int(round(d['M'] * 10000))       # momentum
            C = d['C']
            # Also include entry boundary and mean level if available
            entry = int(round(d.get('entry_dF', 0) * 10000))
            level = int(round(d.get('mean_level', 0) * 10000))
            fp.append((D, R_q, w_q, cv_q, U_q, M_q, C, entry, level))
        return tuple(fp)

    def commit(self, dsf_seq: List[dict], label: str = "") -> bool:
        """Commit a DSF sequence as a motif."""
        fp = self.dsf_fingerprint(dsf_seq)
        # Duplicate check
        for stored in self.motifs:
            if stored == fp:
                return False
        if len(self.motifs) >= self.max_motifs:
            self.motifs.pop(0)
            self.labels.pop(0)
        self.motifs.append(fp)
        self.labels.append(label)
        return True

    def recall(self, dsf_seq: List[dict]) -> Tuple[Optional[int], float, str]:
        """
        Match a DSF sequence against stored motifs.
        Uses sequence alignment — compares gate-by-gate.
        Score = fraction of matching gate-level trits.
        """
        if not self.motifs:
            return None, 0.0, ""

        query = self.dsf_fingerprint(dsf_seq)
        best_idx, best_score = -1, -1.0

        for i, stored in enumerate(self.motifs):
            score = self._match_score(query, stored)
            if score > best_score:
                best_score = score
                best_idx = i

        if best_idx >= 0:
            return best_idx, best_score, self.labels[best_idx]
        return None, 0.0, ""

    def _match_score(self, a: tuple, b: tuple) -> float:
        """
        Compare two DSF fingerprints.
        Uses distance-based scoring: closer values = higher score.
        Exact match = 1.0 per element, decreasing with distance.
        """
        n = min(len(a), len(b))
        if n == 0:
            return 0.0

        total_score = 0.0
        total_elements = 0

        for i in range(n):
            for j in range(len(a[i])):
                total_elements += 1
                diff = abs(a[i][j] - b[i][j])
                # Score: 1.0 for exact match, decaying with distance
                # Max possible diff varies by field, but normalize reasonably
                max_diff = 10000.0 if j > 0 else 2.0  # D is ±1, others are 0-10000
                if j == 6: max_diff = 3.0  # C is 1-3
                element_score = max(0.0, 1.0 - diff / max_diff)
                total_score += element_score

        # Penalize length mismatch
        len_ratio = n / max(len(a), len(b))
        return (total_score / total_elements) * len_ratio if total_elements > 0 else 0.0

    def recall_all(self, dsf_seq):
        """Return scores against all motifs."""
        query = self.dsf_fingerprint(dsf_seq)
        results = {}
        for i, (stored, label) in enumerate(zip(self.motifs, self.labels)):
            results[label] = self._match_score(query, stored)
        return results


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
    noise = np.random.randint(-2, 3, img.shape, dtype=np.int16)
    return np.clip(img.astype(np.int16) + noise, 0, 255).astype(np.uint8)


# ============================================================
# Feed image to kernel — RAW PIXELS, no extraction
# ============================================================

def image_to_raw_signals(image: np.ndarray) -> dict:
    """
    Convert image to raw pixel signals. THE FULL FIELD.

    Multiple scanlines across the image — not just the middle.
    Each scanline is a complete signal: every pixel, in order.
    R, G, B channels independently.

    Horizontal scanlines at multiple heights capture the outline shape.
    Vertical scanlines at multiple positions capture width variation.
    The kernel sees the ENTIRE boundary pattern, color fill, and texture.
    """
    img = image.astype(float) / 255.0
    h, w = img.shape[:2]

    signals = {}

    # Horizontal scanlines at 5 heights: 20%, 35%, 50%, 65%, 80%
    for pct in [20, 35, 50, 65, 80]:
        y = int(h * pct / 100)
        signals[f'h{pct}_R'] = img[y, :, 0]
        signals[f'h{pct}_G'] = img[y, :, 1]
        signals[f'h{pct}_B'] = img[y, :, 2]

    # Vertical scanlines at 5 positions
    for pct in [20, 35, 50, 65, 80]:
        x = int(w * pct / 100)
        signals[f'v{pct}_R'] = img[:, x, 0]
        signals[f'v{pct}_G'] = img[:, x, 1]
        signals[f'v{pct}_B'] = img[:, x, 2]

    return signals


def process_image(image: np.ndarray) -> dict:
    """
    Feed raw pixels to kernel. Get DSF sequences out.
    One DSF sequence per scan signal.
    """
    signals = image_to_raw_signals(image)
    dsf_results = {}
    for name, signal in signals.items():
        dsf_results[name] = kernel(signal)
    return dsf_results


def all_dsfs_flat(dsf_results: dict) -> List[dict]:
    """Concatenate all DSF sequences into one sequence for krimelack."""
    flat = []
    for name in sorted(dsf_results.keys()):
        flat.extend(dsf_results[name])
    return flat


# ============================================================
# Run
# ============================================================

def main():
    np.random.seed(42)

    print("=" * 75)
    print(" ArcLoom Vision v7 — Raw Pixels In, DSF Out")
    print(" No feature extraction. Kernel is a black box.")
    print("=" * 75)
    print()

    krim = Krimelack()

    # Objects to learn
    learn = {
        'brown_bear':  ('circle',   (139, 90, 43)),
        'red_cup':     ('square',   (200, 30, 30)),
        'blue_star':   ('star',     (30, 30, 200)),
        'green_tri':   ('triangle', (30, 180, 30)),
    }

    print("SHOW PHASE — feed each object to kernel, commit DSF to krimelack")
    print("-" * 75)

    for name, (shape, color) in learn.items():
        img = make_shape(shape, color, size=80)
        dsf_results = process_image(img)
        flat_dsfs = all_dsfs_flat(dsf_results)
        committed = krim.commit(flat_dsfs, label=name)

        # Show what the kernel produced (gate counts per signal)
        gate_info = {k: len(v) for k, v in dsf_results.items()}
        total_gates = sum(gate_info.values())
        fp = krim.dsf_fingerprint(flat_dsfs)

        print(f"  {name:15s}  {'COMMIT' if committed else 'DUP':6s}  "
              f"total_gates={total_gates}  "
              f"fp_len={len(fp)}  "
              f"per_signal: {gate_info}")

    print()
    print("VERIFY — same objects again")
    print("-" * 75)

    for name, (shape, color) in learn.items():
        img = make_shape(shape, color, size=80)
        dsf_results = process_image(img)
        flat_dsfs = all_dsfs_flat(dsf_results)
        _, score, label = krim.recall(flat_dsfs)
        scores = krim.recall_all(flat_dsfs)
        ok = "OK" if label == name else "MISS"
        print(f"  {name:15s} → {label:15s} ({score:.2f}) {ok}")
        print(f"    all scores: {', '.join(f'{k}={v:.2f}' for k, v in sorted(scores.items()))}")

    print()
    print("DISCRIMINATION — new objects, check recall")
    print("-" * 75)

    tests = {
        'brown_bear_2':  ('circle',   (139, 90, 43)),   # same object
        'red_circle':    ('circle',   (200, 30, 30)),    # same shape, diff color
        'blue_circle':   ('circle',   (30, 30, 200)),    # same shape, diff color
        'brown_square':  ('square',   (139, 90, 43)),    # same color, diff shape
        'brown_tri':     ('triangle', (139, 90, 43)),    # same color, diff shape
        'red_tri':       ('triangle', (200, 30, 30)),    # diff both
        'green_star':    ('star',     (30, 180, 30)),    # diff both
        'white_square':  ('square',   (255, 255, 255)),  # white
        'black_circle':  ('circle',   (20, 20, 20)),     # black
        'white_bunny':   ('circle',   (250, 250, 250)),  # white bunny (circle shape)
    }

    for name, (shape, color) in tests.items():
        img = make_shape(shape, color, size=80)
        dsf_results = process_image(img)
        flat_dsfs = all_dsfs_flat(dsf_results)
        _, score, label = krim.recall(flat_dsfs)
        scores = krim.recall_all(flat_dsfs)

        # Expected behavior
        expected = ""
        if name == 'brown_bear_2': expected = " [should match brown_bear]"
        elif 'circle' in name: expected = " [same shape as bear]"
        elif shape == learn.get(label, ('',''))[0] if label in learn else False: expected = " [shape match]"

        print(f"  {name:18s} → {label:15s} ({score:.2f}){expected}")
        print(f"    {', '.join(f'{k}={v:.2f}' for k, v in sorted(scores.items()))}")

    print()
    print(f"Krimelack: {len(krim.motifs)} motifs stored")


if __name__ == '__main__':
    main()
