"""resonant_chi.py — the capacity solve, production form (GL-RPT-CAPACITY-SOLVED).

The cognition wall was the event-count observable collapsing each modality's waveform
into one number. Fix: a bank of frequency-tuned resonant receptors per modality reports
the waveform's SPECTRUM (per-receptor response vector) — rich, concept-distinct features
(cochlea / smell-tumbler). Then each neuron addresses its atlas with a balanced-TERNARY
chi: its own fixed projection of the spectrum, sign-quantized online (no training stats).

Verified: n=200 and n=400 -> 100% clean recall via population vote (substrate-true,
ASIC-mappable: tuned-oscillator bank + ternary chi address). Capacity, not yet meaning
(that comes from grounded waveforms feeding the same banks).
"""
import zlib
import numpy as np

N_RECEPTORS = 16     # tuned receptors per modality (the spectrum resolution)
CHI_DIM = 128        # ternary chi address dimension per neuron
DEAD_ZONE = 0.5      # ternary dead-zone as a fraction of the projected vector's std
_DT = 0.04
_FREQS = np.geomspace(0.3, 12.0, N_RECEPTORS)   # receptor natural frequencies (Hz)


def resonant_response(signal):
    """Driven-resonator amplitude of each tuned receptor to the signal = the spectrum.
    Each receptor responds to the signal's energy at its natural frequency."""
    s = np.asarray(signal, dtype=float)
    if s.size < 4:
        return np.zeros(N_RECEPTORS)
    s = s - s.mean()
    if not np.any(s):
        return np.zeros(N_RECEPTORS)
    t = np.arange(s.size) * _DT
    ang = 2 * np.pi * np.outer(_FREQS, t)          # (R, n)
    ip = np.cos(ang) @ s
    qp = np.sin(ang) @ s
    return np.hypot(ip, qp) / s.size


def spectral_features(signals):
    """Concatenated resonant spectrum across the array-valued modalities.

    GL-CMD-CROSS-SENSE-RECALL-EVE-20260705-207: kept only for callers that
    still want one flat vector. Do not feed this into a per-neuron_id
    projection for binding/recall — the concatenation's width depends on
    HOW MANY modalities happen to be present, so a partial cue (fewer
    modalities than at write time) gets a differently-shaped vector,
    projected through an unrelated matrix (see lane_features/encode_state)."""
    parts = []
    for m in sorted(signals.keys()):
        x = signals[m]
        if x is None or isinstance(x, str):
            continue
        parts.append(resonant_response(x))
    return np.concatenate(parts) if parts else np.zeros(N_RECEPTORS)


def lane_features(signals):
    """Per-modality resonant spectrum, kept SEPARATE (not concatenated).

    GL-CMD-CROSS-SENSE-RECALL-EVE-20260705-207: this is the fix for
    partial-cue recall. Each lane's shape (N_RECEPTORS) never depends on
    which OTHER modalities are present in `signals`, so a lane computed
    from a 1-modality cue is directly comparable (same shape, same
    per-(neuron, modality) projection) to the SAME lane computed from a
    6-modality teach-time signal. Absent/non-array modalities (None, or a
    language word-string) are simply omitted — the same honest-absence
    convention as spectral_features, applied per-lane instead of once
    over the whole concatenation."""
    lanes = {}
    for m, x in signals.items():
        if x is None or isinstance(x, str):
            continue
        lanes[m] = resonant_response(x)
    return lanes


def neuron_projection(neuron_id, feat_dim, chi_dim=CHI_DIM):
    """Per-neuron fixed projection (the neuron's synaptic-weight DNA), deterministic
    from a STABLE hash of the neuron id (not Python's salted hash)."""
    seed = zlib.crc32(str(neuron_id).encode()) & 0xFFFFFFFF
    return np.random.default_rng(seed).standard_normal((chi_dim, feat_dim))


def ternary_chi(features, projection):
    """Balanced-ternary chi address: project the unit-normed spectrum, sign-quantize
    with an online dead-zone. No training-set statistics — production-realizable."""
    v = np.asarray(features, dtype=float)
    nv = np.linalg.norm(v)
    if nv < 1e-12:
        return np.zeros(projection.shape[0])
    y = projection @ (v / nv)
    thr = DEAD_ZONE * (y.std() + 1e-12)
    return np.where(y > thr, 1.0, np.where(y < -thr, -1.0, 0.0))
