#!/usr/bin/env python3
"""
GW170817 Photon Wake Analysis

Searches for oscillatory fine structure in the GW170817 gravitational
wave signal correlated with the gamma ray burst (GRB 170817A).

UFCP prediction: the coherence metric produces an oscillatory density
wake behind energetic photon/matter flows. GR predicts smooth perturbation.
If oscillatory structure exists in the post-merger GW signal correlated
with the GRB arrival, the coherence metric is distinguishable from GR.

USAGE:
  1. Download GW170817 strain data from GWOSC Event Portal:
     https://gwosc.org/eventapi/html/GWTC-1-confident/GW170817/
     Download the 4kHz or 16kHz HDF5 files for H1 and L1.

  2. Place the files in this directory or specify paths below.

  3. Run: python3 tools/gw170817_wake_analysis.py

CONFIDENTIAL — Internal use only.
"""

import os
import sys
import numpy as np

# Try to import gwpy/h5py for LIGO data
try:
    import h5py
    HAS_H5PY = True
except ImportError:
    HAS_H5PY = False

# Configuration
GW170817_GPS_TIME = 1187008882.43  # GPS time of GW170817 merger
GRB_DELAY = 1.74  # seconds between GW merger and GRB 170817A arrival

# Analysis window
PRE_MERGER_SECONDS = 2.0
POST_MERGER_SECONDS = 5.0
WAKE_WINDOW_START = GRB_DELAY - 0.5  # start looking 0.5s before GRB
WAKE_WINDOW_END = GRB_DELAY + 2.0    # look up to 2s after GRB

# Data file paths (user should update these)
DATA_DIR = os.path.dirname(os.path.abspath(__file__))
H1_FILE = os.path.join(DATA_DIR, "H-H1_GWOSC_4KHZ_R1-1187006834-4096.hdf5")
L1_FILE = os.path.join(DATA_DIR, "L-L1_GWOSC_4KHZ_R1-1187006834-4096.hdf5")


def load_strain(filepath, gps_center, window_before, window_after):
    """Load strain data from GWOSC HDF5 file."""
    if not os.path.exists(filepath):
        print(f"  File not found: {filepath}")
        return None, None

    with h5py.File(filepath, 'r') as f:
        strain = f['strain/Strain'][:]
        meta = dict(f['strain/Strain'].attrs)
        t0 = meta.get('Xstart', 0)
        dt = meta.get('Xspacing', 1.0 / 4096)

    sample_rate = 1.0 / dt
    times = t0 + np.arange(len(strain)) * dt

    # Extract window around the event
    mask = (times >= gps_center - window_before) & (times <= gps_center + window_after)
    return times[mask] - gps_center, strain[mask]


def analyze_wake(times, strain, wake_start, wake_end):
    """Look for oscillatory structure in the wake window."""
    mask = (times >= wake_start) & (times <= wake_end)
    t_wake = times[mask]
    s_wake = strain[mask]

    if len(s_wake) < 100:
        print("  Insufficient data in wake window")
        return None

    # Bandpass filter: look for structure between 100 Hz and 2000 Hz
    from scipy.signal import butter, filtfilt
    sample_rate = 1.0 / (t_wake[1] - t_wake[0])
    nyquist = sample_rate / 2
    low = 100 / nyquist
    high = min(2000 / nyquist, 0.99)
    b, a = butter(4, [low, high], btype='band')
    s_filtered = filtfilt(b, a, s_wake)

    # Count zero crossings (oscillation indicator)
    crossings = np.sum(np.diff(np.sign(s_filtered)) != 0)

    # FFT to find dominant frequencies
    spectrum = np.abs(np.fft.rfft(s_filtered))
    freqs = np.fft.rfftfreq(len(s_filtered), 1.0 / sample_rate)

    # Find peaks in spectrum
    from scipy.signal import find_peaks
    peaks, props = find_peaks(spectrum, height=np.max(spectrum) * 0.1,
                               distance=10)

    # RMS of wake vs pre-merger (noise baseline)
    pre_mask = (times >= -2.0) & (times <= -1.0)
    if np.sum(pre_mask) > 100:
        s_pre = strain[pre_mask]
        b_pre, a_pre = butter(4, [low, high], btype='band')
        s_pre_filtered = filtfilt(b_pre, a_pre, s_pre)
        rms_pre = np.sqrt(np.mean(s_pre_filtered ** 2))
    else:
        rms_pre = 0

    rms_wake = np.sqrt(np.mean(s_filtered ** 2))
    snr = rms_wake / (rms_pre + 1e-30)

    return {
        'crossings': crossings,
        'rms_wake': rms_wake,
        'rms_noise': rms_pre,
        'snr': snr,
        'peak_freqs': freqs[peaks][:5],
        'peak_amps': spectrum[peaks][:5],
        'duration': wake_end - wake_start,
        'samples': len(s_wake),
    }


def main():
    print("=" * 60)
    print("GW170817 PHOTON WAKE ANALYSIS")
    print("Searching for oscillatory fine structure")
    print("=" * 60)

    if not HAS_H5PY:
        print("\nERROR: h5py not installed. Run: pip install h5py")
        print("Also need scipy: pip install scipy")
        sys.exit(1)

    print(f"\n  Merger GPS time: {GW170817_GPS_TIME}")
    print(f"  GRB delay: {GRB_DELAY} seconds")
    print(f"  Wake window: {WAKE_WINDOW_START:.1f}s to {WAKE_WINDOW_END:.1f}s post-merger")

    for label, filepath in [("H1 (Hanford)", H1_FILE), ("L1 (Livingston)", L1_FILE)]:
        print(f"\n--- {label} ---")
        times, strain = load_strain(filepath, GW170817_GPS_TIME,
                                     PRE_MERGER_SECONDS, POST_MERGER_SECONDS)
        if times is None:
            continue

        print(f"  Loaded {len(strain)} samples")
        print(f"  Time range: {times[0]:.3f}s to {times[-1]:.3f}s")

        result = analyze_wake(times, strain, WAKE_WINDOW_START, WAKE_WINDOW_END)
        if result is None:
            continue

        print(f"  Wake window: {result['samples']} samples, {result['duration']:.1f}s")
        print(f"  Zero crossings: {result['crossings']}")
        print(f"  Wake RMS: {result['rms_wake']:.2e}")
        print(f"  Noise RMS: {result['rms_noise']:.2e}")
        print(f"  SNR: {result['snr']:.2f}")
        print(f"  Peak frequencies: {result['peak_freqs']} Hz")

        if result['snr'] > 2.0 and result['crossings'] > 10:
            print(f"\n  ** OSCILLATORY STRUCTURE DETECTED **")
            print(f"  SNR={result['snr']:.1f}, {result['crossings']} oscillations")
            print(f"  This is CONSISTENT with the UFCP wake prediction.")
        elif result['snr'] > 1.5:
            print(f"\n  Marginal signal. More analysis needed.")
        else:
            print(f"\n  No significant structure above noise floor.")

    print(f"\n{'='*60}")
    print("NOTE: This analysis is preliminary. A rigorous result requires:")
    print("  1. Proper noise characterization (PSD estimation)")
    print("  2. Signal injection tests (to calibrate sensitivity)")
    print("  3. Comparison with GR ringdown models (null hypothesis)")
    print("  4. Multiple event comparison (GW170817 vs other mergers)")


if __name__ == "__main__":
    main()
