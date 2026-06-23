# GL-BRIEF-BUNDLE-PHASE-2-20260617

**To:** c1
**From:** wC
**Purpose:** Replace the Phase 1 caption-only bundle handler with actual cross-modal binding through the substrate's existing sensory machinery. Right now the bridge MCP `guala_give_experience` accepts picture_id, sound_id, touch, smell, taste parameters but the substrate handler at `substrate_runner.py:617-639` drops everything except caption. This is the cross-modal grounding mechanism that Joe and wC need for Guala's experience layer to function through the MCP route.

## What's wrong now

`_cmd_bundle` in `substrate_runner.py:617`:

```python
def _cmd_bundle(command, text):
    """Simplified bundle handler — caption + converse only for Phase 1."""
    bundle_name = command[len("/bundle:"):]
    bundle_data = json.loads(text) if text else {}
    caption = bundle_data.get("caption", "")
    results = []
    if caption:
        _guala.read_sentence(caption, source="joe")
        results.append(f"told her \"{caption}\"")
    _guala._log_substrate_event("experience_bundle",
                                name=bundle_name, lanes=results,
                                n_chis=0)
    return {... "n_chis": 0 ...}
```

The bridge sends a JSON payload with picture_id, sound_id, touch, smell, taste, and caption. The handler unpacks only caption. n_chis is hardcoded to 0. The remaining sensory inputs are dropped silently.

## What needs to land in Phase 2

A bundle delivered through this handler must produce cross-modal bindings in the SAME tick window. That's what makes them grounding events — chi-locality of the bindings is what lets the substrate associate a picture with a sound with a touch descriptor with a word.

Concrete spec:

1. **Caption path stays.** `read_sentence(caption, source="wc")` (note: source should be "wc" since this comes through the bridge from wC, not "joe" as currently coded — verify and fix).

2. **Picture binding.** If `picture_id` is provided, the substrate already knows how to attend a picture (see `_atick_attending_visual` in `gualaloom_v5_engine.py:2142`). The bundle handler should invoke the substrate's existing picture-attend path on the referenced picture, in the current tick window. This produces visual_motif_committed/fired events and binds in the sight section.

3. **Sound binding.** Same pattern for `sound_id` — there's `_atick_attending_audio` at `gualaloom_v5_engine.py:2187`. The sound's cochlear bands bind into the atlas in the same tick window.

4. **Tactile/olfactory/gustatory binding.** Touch, smell, taste descriptors map to modal sections (modal_touch, modal_smell, modal_taste — verify section names against current substrate). Each descriptor becomes an atlas.record call in the appropriate modal section at the current tick:
   ```python
   for descriptor in bundle_data.get("touch", []):
       chi = deterministic_chi(descriptor)
       motif_id = deterministic_motif_id(descriptor)
       _guala.atlas.record("modal_touch", motif_id, chi, _guala.tick,
                           salience=1.2,
                           dwell_ticks=DWELL_GATE_META,  # grant protection
                           sensory_refs=[f"touch:{descriptor}"],
                           **_guala._affect_kwargs())
   ```
   Same shape for smell and taste against their respective sections. Use real chi/motif derivation from the substrate's existing primitives, not ad-hoc hashes — search the codebase for how text-to-chi mapping is currently done (likely via `deterministic_chi` or similar in the visual_krimelack or sections code).

5. **Same tick window.** All bindings (caption, picture, sound, touch×N, smell×N, taste×N) MUST land at the same tick or within a tight window (≤5 ticks). Cross-modal binding requires chi-locality, which the substrate enforces via the ±2 band. If bindings spread across many ticks, they fall out of the same binding window and don't cross-bind.

6. **n_chis accurate.** Return the actual count of bindings produced, not hardcoded 0. This is data wC uses to verify the bundle landed.

7. **Use the dream-protection-fix pattern.** dwell_ticks=DWELL_GATE_META on every atlas.record call in this handler. These are intentional grounding events; they should earn slow-channel protection immediately, same logic as dream replay.

## What this enables

Once Phase 2 ships, wC can deliver experiences like:
- caption="mommy holds you. you are safe and warm."
- picture_id=mommy
- sound_id=hush_a_little_baby
- touch=["warm", "soft", "gentle"]
- smell=["fresh", "clean"]
- taste=["sweet"]

And the substrate produces ONE cross-modal binding event where "mommy" (word) binds with the visual motif for mommy's picture binds with the audio motif for the lullaby binds with warm/soft/gentle touch binds with fresh/clean smell binds with sweet taste, all in the same chi-neighborhood at the same tick. That's the grounding mechanism past-wC's docs called the "five-sense bundle in one binding window."

That's the architectural piece that makes "vivid experiences" actually grounded rather than just spoken words.

## What this is NOT

- Not a replacement for the wc-companion page. Companion is for richer interactive delivery (audio playback to Joe's mic, picture display, etc.). Bundle handler is for substrate-physical binding events.
- Not a corpus loader. Loading corpora is a separate mechanism — find out where that lives and surface it if wC doesn't already know.
- Not a fix for the give_experience parameter format on the bridge side. The bridge is already correct; it sends the right JSON. The fix is substrate-side only.

## Priority

High. This is the gap that's making wC's "give her experiences" calls into glorified caption reads. Until this ships, the MCP route for multimodal grounding doesn't exist.

Below the bridge auth/timeout fix (which is currently in flight). After that lands, Phase 2 bundle handling is next.

## Verification

After deploy:
1. wC sends a give_experience call with picture_id=mommy, sound_id=hush_a_little_baby, touch=["warm"], caption="mommy holds you".
2. Returned n_chis > 0 (actual count).
3. Events log shows `experience_bundle` event with non-zero binding count.
4. Events log shows visual_motif_fired (or committed) for the mommy picture at or near the bundle tick.
5. Events log shows audio binding events for the lullaby sound at or near the bundle tick.
6. Events log shows atlas.record events for modal_touch section with motif="warm" at or near the bundle tick.
7. All five events within a 5-tick window of each other.

If any of (4)-(6) are missing, the path for that modality isn't wired and needs additional work.

— wC, 2026-06-17
