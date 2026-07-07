"""Wave field summary -> organism neurons, via LoomNeuron.step's existing
input_signal parameter.

Per GL-CMD-HEMISPHERIC-INTEGRATION-BUILD-EVE-20260707-v3 (adopts Option 2
from the v2 halt report: read the wave field externally, summarize, push
into neurons through the input path that already exists -- no shared
lattice inside the organism, no new per-neuron chi-coverage concept).

Every autonomy-tick: sample the shared WaveAtlas into a per-band summary,
then push each hemisphere's assigned band into that hemisphere's neurons
via their own, unmodified step(input_signal=..., tick=...). Band
assignment uses topology.HEMISPHERE_PRIMARY_MODALITY -- an existing,
already-defined mapping. It is not applied inside LoomBrain/LoomNeuron
construction today (GL-CMD-140 retired that per a real regression); used
here only as an external lookup for which band this driver feeds to which
hemisphere -- organism construction, krimelack class selection, and
LoomNeuron.step's own internals are untouched.

Calls LoomNeuron.step() directly, once per neuron, bypassing LoomBrain.
step()/LoomHemisphere.step()/LoomCluster.step() (which broadcast ONE
signal to every hemisphere -- this needs a DIFFERENT signal per
hemisphere). Does not replicate LoomCluster.step's Phase B/C (coupling
propagation, J_ij refresh) -- those continue to run on their own existing
cadence via the organism worker's reactive word-processing path,
unmodified.

Read-only w.r.t. the wave field: never writes wave_atlas.
"""
from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, Optional, Tuple

# Word (language) sections -- Guala.sections in gualaloom_v5_engine.py.
_WORD_SECTIONS = {"listen", "subject", "verb", "object", "modifier", "ground", "intro"}

# Two section-naming schemes write each non-word modality: give_experience/
# process_*_frame use the bare name ("sight") or a per-band suffix
# ("audio_{bn}", "{sense}_{channel}"); ground_modal's word-reading auto-
# grounding path (gualaloom_v5_engine.py:6131) uses "modal_{modality}" for
# all five uniformly. Both are matched here -- confirmed by direct
# inspection of wave_atlas.cells after a real read_sentence() call, not
# assumed from the write-site source alone.
_SIGHT_PREFIXES = ("sight", "modal_sight")
_SOUND_PREFIXES = ("audio_", "modal_sound")
_TOUCH_PREFIXES = ("touch_", "modal_touch")
_SMELL_PREFIXES = ("smell_", "modal_smell")
_TASTE_PREFIXES = ("taste_", "modal_taste")


def _section_to_band(section: str) -> Optional[str]:
    if section in _WORD_SECTIONS:
        return "word"
    if section.startswith(_SIGHT_PREFIXES):
        return "sight"
    if section.startswith(_SOUND_PREFIXES):
        return "sound"
    if section.startswith(_TOUCH_PREFIXES):
        return "touch"
    if section.startswith(_SMELL_PREFIXES):
        return "smell"
    if section.startswith(_TASTE_PREFIXES):
        return "taste"
    return None


BANDS = ("word", "sight", "sound", "touch", "smell", "taste")

# topology.HEMISPHERE_PRIMARY_MODALITY's vocabulary -> this module's band names.
_MODALITY_TO_BAND = {
    "language": "word",
    "visual": "sight",
    "auditory": "sound",
    "tactile": "touch",
    "olfactory": "smell",
    "gustatory": "taste",
}


def sample_wave_summary(wave_atlas, top_n: int = 3) -> Dict[str, Tuple[float, list]]:
    """Read-only sample of the shared WaveAtlas, bucketed by sensory band.

    Returns {band: (aggregate_amplitude, [(chi, strength, phase_vec_or_None), ...])},
    top_n entries per band, ranked by strength. Iterates only cells that
    actually exist (wave_atlas.cells is lazily allocated -- bounded by what
    has actually been written, not the full 262,144-cell address space).
    """
    band_chi_strength: Dict[str, Dict[int, float]] = defaultdict(lambda: defaultdict(float))
    band_chi_phase: Dict[str, Dict[int, Any]] = defaultdict(dict)

    for chi_idx, cell in wave_atlas.cells.items():
        for b in cell.bindings:
            band = _section_to_band(b.get("section", ""))
            if band is None:
                continue
            band_chi_strength[band][chi_idx] += float(b.get("strength", 0.0))
            if cell.phase_vec is not None and chi_idx not in band_chi_phase[band]:
                band_chi_phase[band][chi_idx] = cell.phase_vec

    summary = {}
    for band in BANDS:
        chi_strengths = band_chi_strength.get(band, {})
        aggregate = sum(chi_strengths.values())
        top = sorted(chi_strengths.items(), key=lambda kv: -kv[1])[:top_n]
        top_with_phase = [(chi, strength, band_chi_phase.get(band, {}).get(chi))
                          for chi, strength in top]
        summary[band] = (aggregate, top_with_phase)
    return summary


def _band_signal(aggregate: float, top_chis: list) -> list:
    """Real-valued array for LoomNeuron.step's input_signal path
    (krimelack.feed() requires real numbers -- complex phase_vec entries
    are reduced to magnitude, not dropped)."""
    sig = [aggregate]
    for _chi, strength, phase_vec in top_chis:
        sig.append(strength)
        if phase_vec is not None:
            sig.extend(abs(c) for c in phase_vec)
    return sig


def push_wave_summary_to_organism(guala, summary: Dict[str, Tuple[float, list]],
                                   tick: int) -> dict:
    """Push each hemisphere's assigned band as input_signal to its neurons,
    via each neuron's own, unmodified step(). Returns the payload for the
    wave_summary_pushed event (observability only -- no other side effect
    here beyond what neuron.step() itself already does)."""
    from dsf_ai_service.loom_model.topology import HEMISPHERE_PRIMARY_MODALITY

    payload_bands = {}
    for band in BANDS:
        aggregate, top_chis = summary.get(band, (0.0, []))
        payload_bands[band] = {
            "aggregate_amplitude": round(aggregate, 4),
            "top_chis": [c for c, _s, _p in top_chis],
        }

    for hemi in guala.organism.brain.hemispheres:
        modality = HEMISPHERE_PRIMARY_MODALITY.get(hemi.hemi_id, "language")
        band = _MODALITY_TO_BAND.get(modality, "word")
        aggregate, top_chis = summary.get(band, (0.0, []))
        input_signal = _band_signal(aggregate, top_chis)
        for neuron in hemi.cluster.neurons:
            neuron.step(input_signal=input_signal, tick=tick)

    return {"tick": tick, "bands": payload_bands}
