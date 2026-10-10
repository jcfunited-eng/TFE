"""Her airway as a practical functional emulation (Joe, 2026-09-14): the voice
Joe's ear accepted on the bench (v17, ledger 2026-09-02), synthesized from her
own drive: a valve with a continuous phase, a child's throat, breath, the
small unsteadiness of a real cycle, a loudness arc, a gentle declination, and
a soft room. Deterministic for one (drive, seed). Sound is made at 32 kHz
and brought to the 16 kHz transport with a lowpass, never by dropping samples.

Expanded to full child articulatory phonetics (11 physical onsets x 5 vowels x 4 pitches = 220 utterances):
plosives (b, d, g, p, t, k), nasals (m, n), liquids/glides (l, w), and open vowels.

Nothing here decides what she says; the organism chooses the drive from its
own state and hears the result through its own ear next beat.
"""

from __future__ import annotations

import math
import struct
from typing import Any

import numpy as np


SYNTHESIS_HZ = 32_000
TRANSPORT_HZ = 16_000
MAX_TRANSPORT_SAMPLES = 4_000            # one 250 ms beat of pressure
SYLLABLE_MS = 236                        # under one beat after pace variation
PEAK = 12_000

# The accepted voice, component by component (frozen v17 recipe).
OPEN_QUOTIENT = 0.71
RISE_TO_FALL = 1.8
TILT_HZ = 1_800.0
BREATH_LOWPASS_HZ = 1_500.0
BREATH_LEVEL = 0.22                      # ~ -13 dB under the voice, moderate
JITTER = 0.0006
SHIMMER = 0.0045
DRIFT = 0.008
DRIFT_PERIOD_MS = 220
ARC_PEAK_MS = 45
ARC_DECAY = 0.45
DECLINATION = 0.045
FINAL_EASE_MS = 130
FINAL_EASE = 0.02
PITCH_VARIATION = 0.035
PACE_VARIATION = 0.07
FADE_MS = 24
REFLECTIONS = ((13, 0.13), (21, 0.09), (30, 0.062), (41, 0.045), (52, 0.033), (63, 0.026), (74, 0.021), (86, 0.017))
REFLECTION_LOWPASS_HZ = 3_200.0
CHILD_BANDWIDTHS_HZ = (180.0, 160.0, 260.0, 340.0, 400.0)
# Peterson-Barney child formants x 1.09 (a girl's tract), F4/F5 fixed.
VOWELS = (
    ("ah", (1_120.0, 1_490.0, 3_455.0)),
    ("eh", (752.0, 2_845.0, 3_891.0)),
    ("ee", (403.0, 3_488.0, 4_066.0)),
    ("oh", (741.0, 1_155.0, 3_466.0)),
    ("oo", (469.0, 1_275.0, 3_553.0)),
)
HIGH_FORMANTS_HZ = (4_375.0, 5_625.0)
PITCHES_DECIHERTZ = (3_450, 3_600, 3_750, 3_900)   # her pitch choices, in tenths of a hertz

# 11 physical articulatory onsets spanning canonical infant phonetics
ONSETS = ("", "m", "b", "d", "g", "p", "t", "k", "l", "n", "w")

ONSET_PROFILES: dict[str, dict[str, Any] | None] = {
    "": None,
    "m": {
        "formants": (280.0, 1_150.0, 2_400.0),
        "lowpass": 600.0,
        "gain": 0.42,
        "onset_ms": 60,
        "glide_ms": 60,
    },
    "b": {
        "formants": (200.0, 800.0, 2_200.0),
        "lowpass": 800.0,
        "gain": 0.45,
        "onset_ms": 30,
        "glide_ms": 40,
    },
    "d": {
        "formants": (200.0, 1_800.0, 2_800.0),
        "lowpass": 1_200.0,
        "gain": 0.48,
        "onset_ms": 30,
        "glide_ms": 40,
    },
    "g": {
        "formants": (200.0, 2_400.0, 2_600.0),
        "lowpass": 1_400.0,
        "gain": 0.46,
        "onset_ms": 35,
        "glide_ms": 45,
    },
    "p": {
        "formants": (350.0, 1_000.0, 2_100.0),
        "lowpass": 900.0,
        "gain": 0.38,
        "onset_ms": 25,
        "glide_ms": 35,
    },
    "t": {
        "formants": (350.0, 2_000.0, 3_200.0),
        "lowpass": 1_500.0,
        "gain": 0.40,
        "onset_ms": 25,
        "glide_ms": 35,
    },
    "k": {
        "formants": (350.0, 2_200.0, 2_700.0),
        "lowpass": 1_600.0,
        "gain": 0.38,
        "onset_ms": 30,
        "glide_ms": 40,
    },
    "l": {
        "formants": (350.0, 1_050.0, 3_000.0),
        "lowpass": 2_500.0,
        "gain": 0.58,
        "onset_ms": 50,
        "glide_ms": 50,
    },
    "n": {
        "formants": (280.0, 1_800.0, 2_800.0),
        "lowpass": 800.0,
        "gain": 0.44,
        "onset_ms": 55,
        "glide_ms": 50,
    },
    "w": {
        "formants": (300.0, 700.0, 2_200.0),
        "lowpass": 1_500.0,
        "gain": 0.55,
        "onset_ms": 55,
        "glide_ms": 60,
    },
}


def _rng(seed: int):
    """A small deterministic generator (SplitMix64), the same on every machine."""

    state = seed & 0xFFFFFFFFFFFFFFFF

    def next_float() -> float:
        nonlocal state
        state = (state + 0x9E3779B97F4A7C15) & 0xFFFFFFFFFFFFFFFF
        z = state
        z = ((z ^ (z >> 30)) * 0xBF58476D1CE4E5B9) & 0xFFFFFFFFFFFFFFFF
        z = ((z ^ (z >> 27)) * 0x94D049BB133111EB) & 0xFFFFFFFFFFFFFFFF
        z ^= z >> 31
        return (z >> 11) / float(1 << 53)

    return next_float


def _one_pole_lowpass(signal: np.ndarray, cutoff_hz: float, rate: int) -> np.ndarray:
    alpha = 1.0 - math.exp(-2.0 * math.pi * cutoff_hz / rate)
    out = np.empty_like(signal)
    y = 0.0
    for index in range(signal.shape[0]):
        y += alpha * (signal[index] - y)
        out[index] = y
    return out


def _resonator(signal: np.ndarray, frequency_hz: np.ndarray | float, bandwidth_hz: float, rate: int) -> np.ndarray:
    """A second-order resonance; the centre may glide sample by sample."""

    out = np.empty_like(signal)
    y1 = y2 = 0.0
    r = math.exp(-math.pi * bandwidth_hz / rate)
    a2 = -r * r
    gliding = isinstance(frequency_hz, np.ndarray)
    if not gliding:
        theta = 2.0 * math.pi * float(frequency_hz) / rate
        a1 = 2.0 * r * math.cos(theta)
        gain = 1.0 - a1 - a2
    for index in range(signal.shape[0]):
        if gliding:
            theta = 2.0 * math.pi * float(frequency_hz[index]) / rate
            a1 = 2.0 * r * math.cos(theta)
            gain = 1.0 - a1 - a2
        y = gain * signal[index] + a1 * y1 + a2 * y2
        out[index] = y
        y2, y1 = y1, y
    return out


def _decimate(signal: np.ndarray) -> np.ndarray:
    """32 kHz to 16 kHz: a windowed-sinc lowpass at 7 kHz, then every second sample."""

    taps = 47
    cutoff = 7_000.0 / SYNTHESIS_HZ
    n = np.arange(taps) - (taps - 1) / 2.0
    kernel = 2.0 * cutoff * np.sinc(2.0 * cutoff * n) * np.hamming(taps)
    kernel /= kernel.sum()
    filtered = np.convolve(signal, kernel, mode="same")
    return filtered[::2]


def syllable_pcm(drive: tuple[int, int, int], seed: int) -> bytes:
    """One syllable through her airway: (pitch in tenths of a hertz, vowel
    index, onset index) with a per-utterance seed. Signed 16-bit at 16 kHz,
    at most one beat long."""

    pitch_decihertz, vowel_index, onset_index = drive
    if pitch_decihertz not in PITCHES_DECIHERTZ or not 0 <= vowel_index < len(VOWELS) or not 0 <= onset_index < len(ONSETS):
        raise ValueError("vocal drive is outside her airway's declared range")
    random = _rng(seed * 1_000_003 + pitch_decihertz * 7 + vowel_index * 11 + onset_index)
    rate = SYNTHESIS_HZ
    pace = 1.0 + PACE_VARIATION * (2.0 * random() - 1.0)
    total_ms = min(SYLLABLE_MS * pace, 2 * MAX_TRANSPORT_SAMPLES * 1000.0 / rate)
    count = int(total_ms * rate / 1000.0)
    base_hz = (pitch_decihertz / 10.0) * (1.0 + PITCH_VARIATION * (2.0 * random() - 1.0))
    onset = ONSETS[onset_index]
    profile = ONSET_PROFILES.get(onset)
    onset_samples = int(profile["onset_ms"] * rate / 1000.0) if profile else 0
    glide_samples = int(profile["glide_ms"] * rate / 1000.0) if profile else 0
    voiced_start = 0  # the murmur is voiced too; the loudness arc anchors at the first voiced sample

    # Pitch law: declination, extra ease under the fade, slow aperiodic drift.
    t = np.arange(count) / rate
    duration = count / rate
    contour = 1.0 - DECLINATION * (t / duration)
    ease_start = max(0.0, duration - FINAL_EASE_MS / 1000.0)
    ease = np.clip((t - ease_start) / max(1e-9, duration - ease_start), 0.0, 1.0)
    contour *= 1.0 - FINAL_EASE * ease
    period = DRIFT_PERIOD_MS / 1000.0
    targets = [DRIFT * (2.0 * random() - 1.0) for _ in range(int(duration / period) + 2)]
    drift = np.empty(count)
    for index in range(count):
        position = t[index] / period
        k = int(position)
        u = 0.5 - 0.5 * math.cos(math.pi * (position - k))
        drift[index] = targets[k] * (1.0 - u) + targets[k + 1] * u
    f0 = base_hz * contour * (1.0 + drift)

    # The valve: continuous phase; half-cosine rise, raised-cosine steep fall,
    # open quotient 0.71, rise:fall 1.8; per-cycle jitter and shimmer.
    rise_fraction = OPEN_QUOTIENT * RISE_TO_FALL / (RISE_TO_FALL + 1.0)
    fall_fraction = OPEN_QUOTIENT - rise_fraction
    flow = np.zeros(count)
    openness = np.zeros(count)
    phase = 0.0
    cycle_jitter = 1.0
    cycle_gain = 1.0
    for index in range(count):
        if phase < rise_fraction:
            value = 0.5 - 0.5 * math.cos(math.pi * phase / rise_fraction)
        elif phase < OPEN_QUOTIENT:
            value = 0.5 + 0.5 * math.cos(math.pi * (phase - rise_fraction) / fall_fraction)
        else:
            value = 0.0
        flow[index] = value * cycle_gain
        openness[index] = value
        phase += f0[index] * cycle_jitter / rate
        if phase >= 1.0:
            phase -= 1.0
            cycle_jitter = 1.0 + JITTER * (2.0 * random() - 1.0)
            cycle_gain = 1.0 + SHIMMER * (2.0 * random() - 1.0)

    # Loudness arc: peak at 45 ms after the first voiced sample, then a 45 percent decay.
    peak_sample = voiced_start + int(ARC_PEAK_MS * rate / 1000.0)
    arc = np.ones(count)
    attack = np.arange(min(peak_sample, count)) / max(1, peak_sample)
    arc[: attack.shape[0]] = 0.5 - 0.5 * np.cos(math.pi * attack)
    if count > peak_sample:
        arc[peak_sample:] = 1.0 - ARC_DECAY * (np.arange(count - peak_sample) / max(1, count - peak_sample))
    fade_samples = int(FADE_MS * rate / 1000.0)
    arc[-fade_samples:] *= 0.5 + 0.5 * np.cos(math.pi * np.arange(fade_samples) / fade_samples)
    flow *= arc

    # Tilt, breath that puffs with the cycle, radiation as the first difference.
    tilted = _one_pole_lowpass(flow, TILT_HZ, rate)
    noise = np.array([2.0 * random() - 1.0 for _ in range(count)])
    breath = _one_pole_lowpass(noise, BREATH_LOWPASS_HZ, rate) * (0.25 + 0.75 * openness) * arc
    breath *= BREATH_LEVEL * (np.abs(tilted).max() or 1.0) / (np.abs(breath).max() or 1.0)
    source = np.diff(np.concatenate(([0.0], tilted + breath)))

    # The throat: three gliding formants (onset murmur/burst to vowel), then F4/F5.
    vowel_formants = VOWELS[vowel_index][1]
    voice = source
    for order in range(3):
        target = vowel_formants[order]
        if profile:
            start = profile["formants"][order]
            track = np.full(count, target)
            track[:onset_samples] = start
            glide_end = min(count, onset_samples + glide_samples)
            if glide_end > onset_samples:
                u = np.arange(glide_end - onset_samples) / max(1, glide_samples)
                track[onset_samples:glide_end] = start + (target - start) * (0.5 - 0.5 * np.cos(math.pi * u))
            voice = _resonator(voice, track, CHILD_BANDWIDTHS_HZ[order], rate)
        else:
            voice = _resonator(voice, target, CHILD_BANDWIDTHS_HZ[order], rate)
    for order, frequency in enumerate(HIGH_FORMANTS_HZ):
        voice = _resonator(voice, frequency, CHILD_BANDWIDTHS_HZ[3 + order], rate)
    if profile:
        # Articulatory closure/constriction: lowpass and specific gain for the onset span.
        murmur = _one_pole_lowpass(voice, profile["lowpass"], rate) * profile["gain"]
        blend = np.ones(count)
        blend[:onset_samples] = 0.0
        glide_end = min(count, onset_samples + glide_samples)
        if glide_end > onset_samples:
            u = np.arange(glide_end - onset_samples) / max(1, glide_samples)
            blend[onset_samples:glide_end] = 0.5 - 0.5 * np.cos(math.pi * u)
        voice = murmur * (1.0 - blend) + voice * blend

    # A soft room: sparse early reflections, wet lowpassed.
    wet = np.zeros(count)
    for delay_ms, gain in REFLECTIONS:
        delay = int(delay_ms * rate / 1000.0)
        if delay < count:
            wet[delay:] += gain * voice[: count - delay]
    voice = voice + _one_pole_lowpass(wet, REFLECTION_LOWPASS_HZ, rate)

    transport = _decimate(voice)[:MAX_TRANSPORT_SAMPLES]
    peak = float(np.abs(transport).max()) or 1.0
    samples = np.clip(np.round(transport * (PEAK / peak)), -32768, 32767).astype(np.int64)
    return struct.pack(f"<{samples.shape[0]}h", *samples.tolist())


__all__ = ("ONSETS", "ONSET_PROFILES", "PITCHES_DECIHERTZ", "VOWELS", "syllable_pcm")
