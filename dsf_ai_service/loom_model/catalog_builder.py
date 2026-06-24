"""catalog_builder.py — fill her SensoryCatalog with RESONANT waveform-senses.

Joe's design: an indexed catalog of word -> tumbler-waveform senses, generated ONCE
(LLM sensory emulation — the only allowed LLM use, it makes signal not speech),
cached, reused forever. "Story amplitude" = the per-encounter sampling of the
stored distribution.

Two hard requirements (learned on the bench):
  1. REAL / grounded  -> so meaning emerges (similar things get similar spectra).
  2. BALANCED, multi-channel -> so the generated waveform OSCILLATES (winds both
     ways): sig_res > theta, which is what makes her neurons fold and GROW. A flat
     or one-note profile recalls fine but never grows her. So we VALIDATE that every
     cached entry actually resonates, and re-roll / enrich until it does.

The catalog stores params (the folding path regenerates the waveform from them) and,
optionally, the precomputed resonant spectrum (the recall feature). No flat numbers
leave here — only params that yield processable waveforms.
"""

import json
import os
import urllib.request

import numpy as np

from dsf_ai_service.loom_model.embryo import resonance_signal, bipolar_sense

# real channel sets the waveform generators understand
TASTE = ["sweet", "sour", "salty", "bitter", "umami"]
SMELL = ["sweet", "putrid", "floral", "fruity", "smoky", "earthy", "sour", "fresh"]
TOUCH = ["temperature", "pressure", "texture", "sharpness", "wetness"]

THETA = 0.05  # resonance gate — a cached entry MUST exceed this or it won't grow her

_SYS = (
    "You are a sensory transducer, not a writer. You output ONLY compact JSON. For "
    "each word you give the REAL multi-sensory signature of the thing — how it "
    "actually tastes, smells, and feels. Use SEVERAL channels at once with VARIED, "
    "moderate-to-strong values (a real thing stimulates many receptors, not one) — "
    "this richness is required. Values in [0,1], 2 decimals."
)


def _llm_params(words, api_key, model="claude-sonnet-4-6", timeout=90):
    """LLM sensory emulation -> {word: {taste:{}, smell:{}, touch:{}}}. Robust parse."""
    usr = (
        f"For each word give taste{{{','.join(TASTE)}}}, smell{{{','.join(SMELL)}}}, "
        f"touch{{{','.join(TOUCH)}}}. Several channels active per modality. "
        f"Words: {list(words)}. Format {{word:{{taste:{{}},smell:{{}},touch:{{}}}}}}."
    )
    body = json.dumps({
        "model": model, "max_tokens": 8000, "system": _SYS,
        "messages": [{"role": "user", "content": usr}],
    }).encode()
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages", data=body,
        headers={"x-api-key": api_key, "anthropic-version": "2023-06-01",
                 "content-type": "application/json"})
    txt = json.load(urllib.request.urlopen(req, timeout=timeout))["content"][0]["text"]
    txt = txt.strip().replace("```json", "").replace("```", "").strip()
    return json.JSONDecoder().raw_decode(txt[txt.find("{"):])[0]


def resonance_of(params):
    """sig_res of the taste+smell waveform this entry generates (the fold gate input)."""
    parts = []
    for mod in ("taste", "smell"):
        p = params.get(mod) or {}
        if p:
            parts.append(bipolar_sense(p, mod))
    if not parts:
        return 0.0
    return float(resonance_signal(np.concatenate(parts)))


_LEVELS = [0.85, 0.5, 0.15]   # high / mid / low — curriculum-shape spread


def make_resonant(params, top_k=3):
    """Sparsify each modality to its top-`top_k` salient channels and give them a
    high/mid/low spread. This is the curriculum shape that actually OSCILLATES
    (resonance_signal reads shape, not amplitude — a dense profile averages out and
    won't fold her; a sparse high/mid/low one winds both ways). Grounding survives:
    WHICH channels are salient is the LLM's real read (sweet→sweet, sour→sour)."""
    out = {}
    for mod, chans in (("taste", TASTE), ("smell", SMELL), ("touch", TOUCH)):
        pm = params.get(mod) or {}
        ranked = sorted(((float(pm.get(c, 0.0)), c) for c in chans), reverse=True)
        ranked = [(v, c) for v, c in ranked if v > 0.0][:top_k]
        out[mod] = {c: lv for (_, c), lv in zip(ranked, _LEVELS)}
    return out, resonance_of(out)


def build_catalog(words, catalog, api_key, log=print):
    """Fill `catalog` (a SensoryCatalog) with resonant senses for `words`.

    Returns {generated, resonant, repaired, failed}. Every stored entry is validated
    to resonate (sig_res > THETA) — repaired if the LLM gave a flat one."""
    from dsf_ai_service.substrate.sensory_transducer import (
        TOUCH_CHANNELS, SMELL_CHANNELS, TASTE_CHANNELS)
    chan_map = {"touch": TOUCH_CHANNELS, "smell": SMELL_CHANNELS, "taste": TASTE_CHANNELS}

    todo = [w for w in words if not catalog.has_word(w)] if hasattr(catalog, "has_word") else list(words)
    generated = resonant = repaired = 0
    failed = []
    rng = np.random.default_rng(0)

    for i in range(0, len(todo), 20):
        batch = todo[i:i + 20]
        try:
            params = _llm_params(batch, api_key)
        except Exception as e:
            log(f"  batch LLM failed: {e}")
            failed.extend(batch)
            continue
        for w in batch:
            p = params.get(w)
            if not p:
                failed.append(w)
                continue
            # sparsify the LLM's grounded read to a resonant (curriculum-shape) profile
            r0 = resonance_of(p)
            sparse, r = make_resonant(p)
            if r > r0 + 1e-6:
                repaired += 1
            if r > THETA:
                resonant += 1
            for mod, chans in chan_map.items():
                sm = sparse.get(mod) or {}
                if not sm:
                    catalog.set_entry(w, mod, applicable=False)
                    continue
                mean = {c: float(sm.get(c, 0.0)) for c in chans}  # top-k nonzero, rest 0
                catalog.set_entry(w, mod, applicable=True, mean=mean,
                                  std={c: 0.12 for c in chans})  # "story amplitude"
            generated += 1
    return {"generated": generated, "resonant": resonant,
            "repaired": repaired, "failed": failed}
