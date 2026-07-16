"""Wave field summary -> organism neurons, via the organism worker's async
sensory queue (GL-CMD-SENSORY-ORGANISM-QUEUE-EVE-20260707-v1).

Per GL-CMD-HEMISPHERIC-INTEGRATION-BUILD-EVE-20260707-v3 (adopts Option 2
from the v2 halt report: read the wave field externally, summarize, push
into neurons through the input path that already exists -- no shared
lattice inside the organism, no new per-neuron chi-coverage concept).

GL-CMD-SENSORY-ORGANISM-QUEUE-EVE-20260707-v1: v3's original design called
LoomNeuron.step() directly, 64 times, SYNCHRONOUSLY inside _autonomy_tick
-- measured live at 233-290ms/call (confirmed via a controlled, isolated
_autonomy_tick timing comparison against the same organism state with and
without this code active), because cost scales with the organism's own
accumulated per-neuron state, not wave-atlas size -- wave-atlas decay
(the prior dispatch series) does not touch this cost at all. This
version enqueues one work item per non-word hemisphere onto
Guala._organism_sensory_queue instead, draining asynchronously on the
SAME background thread the word-processing queue already uses (see
_organism_worker_loop in gualaloom_v5_engine.py) -- off the main tick
loop's critical path entirely. Word hemispheres (language band) are
skipped here; they're already fed through the existing word queue
(_enqueue_organism_remember/_enqueue_organism_experience_explicit),
unchanged.

Read-only w.r.t. the wave field: never writes wave_atlas.
"""
from __future__ import annotations

import heapq
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
        top = heapq.nlargest(top_n, chi_strengths.items(), key=lambda kv: kv[1])
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
    """Enqueue each non-word hemisphere's assigned band as a sensory work
    item, drained asynchronously by the organism worker thread (see
    Guala._organism_worker_loop). Returns the payload for the
    wave_summary_pushed event (observability only). Fires
    sensory_organism_enqueued per hemisphere queued -- sensory_organism_
    processed fires later, from the worker thread, when that item is
    actually drained.

    Skip-when-empty (unchanged from the wave-atlas-decay series): on a
    quiescent tick (every band's aggregate is 0) nothing is enqueued at
    all -- the event still fires (with an honest all-zero payload) from
    the caller in _autonomy_tick."""
    from dsf_ai_service.loom_model.topology import HEMISPHERE_PRIMARY_MODALITY

    if not any(agg > 0.0 for agg, _ in summary.values()):
        return {"tick": tick, "bands": {b: {"aggregate_amplitude": 0.0, "top_chis": []} for b in BANDS}}

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
        if band == "word":
            # Word hemispheres already receive real content through the
            # existing word queue (_enqueue_organism_remember et al.) --
            # not this new sensory path.
            continue
        aggregate, top_chis = summary.get(band, (0.0, []))
        if aggregate <= 0.0:
            # GL-CMD-SINGLE-STACK-ALL-LIVE-20260716 (organ 3): PER-BAND
            # skip-when-empty. The old global skip only fired when EVERY
            # band was zero -- one live band kept enqueueing zero-signal
            # work items for every OTHER (silent) hemisphere too, which is
            # half of the 2026-07-09 continuous-kick incident (the other
            # half was decay never reaching exactly zero -- fixed by the
            # WaveAtlas.tick_decay zero-clamp). A silent band now enqueues
            # NOTHING for its hemisphere: no step work, no injection.
            continue
        input_signal = _band_signal(aggregate, top_chis)
        # GL-CMD-BRAIN-STEP-CHI-DISPATCH-EVE-20260707-v2: reuse the
        # highest-strength chi already computed for this band (top_chis is
        # sorted by strength) as input_chi -- computed once here, not
        # re-derived, since a real chi is already sitting in top_chis.
        input_chi = top_chis[0][0] if top_chis else None
        guala._enqueue_organism_sensory(hemi.hemi_id, input_signal, tick, input_chi)
        # F2 (2026-07-16): sampled to the 500-tick telemetry cadence --
        # per-tick-per-hemisphere events were the third contributor to the
        # observability-ring flood. The enqueue itself stays per-tick.
        if tick % 500 == 0:
            guala._log_substrate_event(
                "sensory_organism_enqueued", tick=tick, hemi_id=hemi.hemi_id,
                band=band, aggregate_amplitude=round(aggregate, 4))

    return {"tick": tick, "bands": payload_bands}
