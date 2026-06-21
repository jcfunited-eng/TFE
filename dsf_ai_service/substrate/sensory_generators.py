"""
Sensory Signal Generators — physics-grounded synthetic waveforms for
touch, smell, and taste channels.

GL-PLAN-FULLWIRE-WC-20260611-042 (A4 experience bundles)

NOT labels. NOT lookup tables. Each generator takes physical parameters
and produces a temporal waveform that runs through the real sensory
krimelack, producing chi states that reflect the signal's structure.

GATING RULE: These generators ONLY run inside:
  1. Experience bundle path (/bundle: command)
  2. Dream replay path (when a memory with sensory bindings replays)
  NEVER during reading, conversation, or visual/audio attention.
  The three chemical/somatic senses are gated off during linguistic
  processing — biologically correct, prevents overwhelm.

Two things that feel/smell/taste similar produce similar chi states
because the PHYSICS is similar, not because someone tagged them.
"""

import math
import hashlib
import numpy as np


def deterministic_motif_id(name):
    """1.5: Deterministic motif ID from a name string.
    Replaces hash()%1000 which changes every restart."""
    return int(hashlib.md5(name.encode()).hexdigest()[:8], 16) % 10000


# ============================================================
# TOUCH — thermal + pressure + texture waveforms
# ============================================================
# Physical axes:
#   temperature: thermal conductivity × contact area (0=cold, 0.5=neutral, 1=hot)
#   pressure: force distribution (0=none, 1=crushing)
#   texture_freq: spatial frequency of surface variation (0=glass-smooth, 1=gravel)
#   sharpness: edge acuity (0=rounded, 1=knife)
#   wetness: surface moisture (0=bone-dry, 1=submerged)



def generate_touch_waveform(params, n_samples=200, sample_rate=100):
    """Generate a multi-channel touch waveform from physical parameters.

    Returns dict of channel_name → 1D numpy array (temporal signal).
    Each channel is a physically-motivated waveform, not a flat constant.

    Temperature: exponential approach to equilibrium (thermal contact curve)
    Pressure: force onset ramp + sustained hold + adaptation decay
    Texture: band-limited noise at the surface spatial frequency
    Sharpness: impulse train with narrow peaks
    Wetness: low-frequency fluctuation (capillary spread)
    """
    t = np.linspace(0, 2.0, n_samples)
    signals = {}

    temp = params.get("temperature", 0.5)
    # Thermal contact: exponential approach from skin temp (0.5) to object temp
    tau_thermal = 0.3 + 0.2 * (1.0 - abs(temp - 0.5))
    signals["temperature"] = 0.5 + (temp - 0.5) * (1.0 - np.exp(-t / tau_thermal))

    pres = params.get("pressure", 0.3)
    # Pressure: onset ramp (0-0.3s) + sustained + slow adaptation
    onset = np.minimum(t / 0.3, 1.0) * pres
    adaptation = pres * np.exp(-0.5 * np.maximum(t - 0.3, 0))
    signals["pressure"] = onset * 0.4 + adaptation * 0.6

    tex = params.get("texture_freq", 0.0)
    # Texture: band-limited noise — frequency proportional to texture_freq
    if tex > 0.01:
        rng = np.random.default_rng(int(tex * 1000))
        freq = 5 + tex * 40  # 5-45 Hz
        base = np.sin(2 * math.pi * freq * t)
        noise = rng.standard_normal(n_samples) * 0.3
        signals["texture"] = tex * (base + noise) * 0.5
    else:
        signals["texture"] = np.zeros(n_samples)

    sharp = params.get("sharpness", 0.0)
    # Sharpness: narrow Gaussian pulses (nociceptor-like)
    if sharp > 0.01:
        pulse_times = [0.1, 0.5, 1.0, 1.5]
        sig = np.zeros(n_samples)
        for pt in pulse_times:
            sig += sharp * np.exp(-((t - pt) / 0.02) ** 2)
        signals["sharpness"] = sig
    else:
        signals["sharpness"] = np.zeros(n_samples)

    wet = params.get("wetness", 0.0)
    # Wetness: slow capillary spread oscillation
    if wet > 0.01:
        signals["wetness"] = wet * (0.5 + 0.5 * np.sin(2 * math.pi * 1.5 * t)) * \
                             (1.0 - np.exp(-t / 0.5))
    else:
        signals["wetness"] = np.zeros(n_samples)

    return signals


# ============================================================
# SMELL — combinatorial receptor activation
# ============================================================
# Olfactory receptors respond to molecular shape families.
# 8 receptor channels modeled on primary odor categories:
#   sweet, putrid, floral, fruity, smoky, earthy, sour, fresh
# Real olfaction: ~400 receptor types, but 8 captures the
# major perceptual axes (Amoore's stereochemical theory adapted).



def generate_smell_waveform(params, n_samples=200, sample_rate=100):
    """Generate an 8-channel olfactory receptor activation pattern.

    Each channel has onset dynamics based on molecular volatility:
    - Light/volatile molecules (fresh, fruity) → fast onset, fast decay
    - Heavy molecules (earthy, smoky) → slow onset, persistent
    This means "fresh ocean air" has a different temporal signature
    than "deep forest floor" even if total activation is similar.
    """
    t = np.linspace(0, 2.0, n_samples)
    signals = {}

    # Molecular weight proxy: lighter = faster onset
    volatility = {
        "sweet": 0.6, "putrid": 0.3, "floral": 0.7,
        "fruity": 0.8, "smoky": 0.2, "earthy": 0.15,
        "sour": 0.7, "fresh": 0.9,
    }

    for channel, intensity in params.items():
        if intensity < 0.01:
            signals[channel] = np.zeros(n_samples)
            continue
        vol = volatility.get(channel, 0.5)
        # Onset: fast for volatile, slow for heavy
        tau_on = 0.1 + (1.0 - vol) * 0.8
        # Decay: volatile fades, heavy persists
        tau_off = 0.5 + (1.0 - vol) * 2.0
        # Activation curve: rise then partial decay
        rise = 1.0 - np.exp(-t / tau_on)
        fade = np.exp(-np.maximum(t - 0.8, 0) / tau_off)
        # Add receptor noise (biological jitter) — deterministic seed (1.3)
        channel_seed = sum(ord(c) for c in channel) * 7 + 13
        rng = np.random.default_rng(channel_seed)
        noise = rng.standard_normal(n_samples) * 0.05
        signals[channel] = intensity * rise * fade + noise * intensity

    return signals


# ============================================================
# TASTE — ion channel activation with temporal dynamics
# ============================================================
# Five gustatory receptor types with distinct binding kinetics:
#   sweet: slow onset, sustained (sugar receptor binding)
#   sour: fast onset, fast adaptation (proton concentration)
#   salty: medium onset, sustained (sodium channel gating)
#   bitter: fast onset, VERY slow decay (protective — bitter lingers)
#   umami: slow onset, slow build (glutamate receptor saturation)



def generate_taste_waveform(params, n_samples=200, sample_rate=100):
    """Generate a 5-channel gustatory temporal signal.

    Each channel has biologically-motivated kinetics:
    - Sweet: slow Hill-function onset, sustained plateau
    - Sour: fast exponential onset, rapid adaptation
    - Salty: medium onset, steady state with slow fluctuation
    - Bitter: fast onset, VERY slow decay (warning signal persists)
    - Umami: slowest onset, gradual build to peak
    """
    t = np.linspace(0, 2.0, n_samples)
    signals = {}

    kinetics = {
        "sweet":  {"tau_on": 0.4, "tau_off": 3.0, "hill_n": 2.0},
        "sour":   {"tau_on": 0.05, "tau_off": 0.3, "hill_n": 1.0},
        "salty":  {"tau_on": 0.2, "tau_off": 2.0, "hill_n": 1.5},
        "bitter": {"tau_on": 0.08, "tau_off": 5.0, "hill_n": 1.0},
        "umami":  {"tau_on": 0.6, "tau_off": 4.0, "hill_n": 3.0},
    }

    for channel, intensity in params.items():
        if channel not in kinetics or intensity < 0.01:
            signals[channel] = np.zeros(n_samples)
            continue
        k = kinetics[channel]
        # Hill function onset
        onset = (t / k["tau_on"]) ** k["hill_n"] / \
                (1.0 + (t / k["tau_on"]) ** k["hill_n"])
        # Adaptation decay (after peak)
        peak_t = k["tau_on"] * 1.5
        decay = np.exp(-np.maximum(t - peak_t, 0) / k["tau_off"])
        # Combined: rise to peak, then partial decay
        sig = intensity * onset * decay
        # Receptor saturation cap
        sig = np.minimum(sig, intensity)
        signals[channel] = sig

    return signals


# ============================================================
# Combined interface for experience bundles
# ============================================================

def generate_sensory_signals(sense_name, selections, transducer=None, tick=0):
    """Generate physics-based waveforms for a sense from substrate-discovered params.

    Args:
        sense_name: "touch", "smell", or "taste"
        selections: list of descriptor labels, e.g. ["warm", "rough"]
        transducer: SensoryTransducer instance (uses NullAtlasReader if None)
        tick: substrate tick for deterministic seeding

    Returns:
        dict of channel_name → 1D numpy array (waveform)

    GATING: This function should ONLY be called from:
        - Experience bundle processing (/bundle: command)
        - Dream replay of memories with sensory bindings
    """
    from dsf_ai_service.substrate.sensory_transducer import SensoryTransducer

    generators = {"touch": generate_touch_waveform, "smell": generate_smell_waveform,
                  "taste": generate_taste_waveform}

    gen = generators.get(sense_name)
    if not gen:
        return {}

    if transducer is None:
        transducer = SensoryTransducer()

    # Each descriptor produces params via the transducer; average them
    combined = {}
    n = 0
    for sel in selections:
        profile = transducer.transduce(sense_name, sel, tick + n)
        for k, v in profile.items():
            combined[k] = combined.get(k, 0.0) + v
        n += 1
    if n > 0:
        for k in combined:
            combined[k] /= n

    return gen(combined)


def transduce_sensory_signals(signals):
    """Run generated waveforms through krimelack transduction.
    Returns dict of channel_name → {winding, chi} for per-channel binding (1.2).

    Each channel gets its own krimelack winding → chi_address = winding % 100 (1.1).
    This preserves combinatorial identity: warm+rough ≠ warm+smooth because
    each channel's chi differs."""
    from dsf_ai_service.substrate.krimelack import Krimelack
    import math

    results = {}
    for channel_name, waveform in signals.items():
        if len(waveform) < 2:
            continue
        wmax = np.abs(waveform).max()
        if wmax < 1e-9:
            continue
        normalized = waveform / wmax
        k = Krimelack(omega_0=2.0, kappa=60.0, dt=0.02,
                      integration_threshold=math.pi / 3)
        k.feed_signal(normalized)
        results[channel_name] = {
            "winding": k.winding,
            "chi": k.winding % 100,  # 1.1: canonical chi_address
        }
    return results
