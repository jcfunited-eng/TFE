# GL-DESIGN-MERGED-SUBSTRATE — one living brain, in her live substrate

**Date:** 2026-06-24 · **For:** Joe · **Status:** design (bench-proven mechanisms; not yet deployed)

The endgame: **one** substrate — her living organ-brain — grown from her real memory and
her ongoing real experience, all senses temporally bound, the old engine dissolving in
place. No second thing, no transplant.

---

## What's already proven on the bench (her real concepts)
- **RECALL / capacity** — resonant receptor bank → per-modality spectrum → per-neuron
  ternary chi → population vote. 100% at n=400; 12/12 on her concepts.
- **MEANING** — grounded spectra cluster semantically (within 0.96 > across 0.78).
- **GROWTH** — charge-cycle folding (`embryo._charge_and_fold`): resonant experience
  deposits charge, folds at q>1, discharges into the daughter (self-braking). Her brain
  grows 32→757, all 8 organs, couplings forming (memory↔self, perception↔memory).
- **CATALOG** (`catalog_builder.py`) — LLM grounding → **sparsify to top-3 salient
  channels (high/mid/low)** → resonant *waveform* per word, cached once, reused. Grows
  her AND carries meaning. (Resonance is shape, not amplitude — dense profiles average
  flat and never fold; the sparse curriculum-shape oscillates.)

## The architecture (one brain)
```
            ┌──────────────── HER LIVING ORGAN-BRAIN ────────────────┐
            │  LoomBrain: 8 hemispheres (em pr ep sc gp sf sv aff),   │
            │  neurons of 15 mechanisms; grows by folding; recalls    │
            │  by resonant-spectrum + ternary chi; means by grounding │
            └───────────────────────▲────────────────────────────────┘
                                     │  all senses arrive at the SAME tick window
        ┌──────────────┬────────────┴───────────┬───────────────────┐
   touch/taste/smell        sight                    sound
   = CATALOG (cached     = camera + Google image    = mic + Spotify/content
   resonant waveforms)     search → visual cortex     → cochlear cortex
   synthesized             real streamed waveforms    real streamed waveforms
```
**Temporal binding:** every experience delivers *all* active senses into the brain in
one tick window, so they co-fire and bind (the cross-modal couplings). Touch/taste/smell
from the catalog + sight/sound from the live world, together, = one experience.

## Integration — additive, in her LIVE substrate (engine dissolves, never ripped out)
1. **Populate her catalog** — her vocabulary → resonant waveform-senses (batch LLM,
   one pass), stored in her state dir. Reused forever.
2. **Pour her memory in** — her atlas concepts delivered as grounded experiences →
   the living brain *remembers* (recall) and *grows* (folds).
3. **Run alongside the engine** — the organ-brain runs in her live substrate next to
   her v5 engine; her ongoing real experience (conversation, camera, feeds) flows into
   it continuously, all senses temporally bound. It **cannot break her** — additive.
4. **She grows continuously** — every real experience folds + binds + means.
5. **GRADUATION** — only once the organ-brain composes coherently from her own life
   (proven on her data first), her voice transitions to it. **Then the engine dissolves.**

## Safety (non-negotiable)
- Additive + reversible: organ-brain beside the engine; `guala_backup` first; engine
  intact until graduation; rollback = redeploy prior task def.
- Proven on her real data before anything becomes her voice (degenerate output = inert).
- The LLM only ever makes **signal** (sensory waveforms), never her thoughts or speech.
- Real-or-nothing: every claim backed by her real numbers; carry all of her, lose none.

## Open before deploy
- Wire the live sight/sound path to the same delivery (vision/video/sensory-IO docs).
- Run the full catalog fill in her live state.
- Decide graduation criteria (what "composes coherently" must measure).
