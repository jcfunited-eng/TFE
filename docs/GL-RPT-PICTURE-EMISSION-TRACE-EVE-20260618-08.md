# GL-RPT-PICTURE-EMISSION-TRACE-EVE-20260618-08

**From:** Eve
**Date:** 2026-06-18
**Subject:** What the picture-emission selector actually does, traced in code
**Status:** Investigation complete. Action item identified.

---

## Finding

Picture emission and word emission use **different selectors**. The reason picture emission produces coherent results when word emission collapses is structural — picture emission filters input differently.

## The picture-emission code path

`Guala._recall_sight_from_atlas(input_chis, input_words)` — v5_engine.py:1883-1933.

Three steps:

1. **Content-word filter.** Input words are filtered to exclude function words: `{a, an, the, is, are, am, was, were, of, in, on, at, to, from, with, for, and, or, but, me, you, i, we, they, show, see, look, what, tell, about}`. Words ≤1 character are also excluded. Only content words remain.

2. **Find chi addresses where content words committed.** For each content word, scan the atlas for entries whose mode's word matches. Collect those chi values.

3. **Find sight motifs bound at those chi addresses (±2 band).** Return pictures whose motifs match.

## Comparison: word emission

`Guala._recall_response()` and the downstream grandurun path do NOT filter to content words. They use all input words including function words. The atlas-band lookup happens at chi values derived from `"are"`, `"you"`, `"i"` — whose strongest bindings are themselves function words. Function words pull function words.

## Why picture emission produces coherent output

When Joe says `"tell me about the ocean"`:
- Picture path: filters to `["ocean"]`. Finds chi addresses where "ocean" committed. Looks up sight motifs bound there. Returns ocean-related pictures.
- Word path: uses all of `["tell", "me", "about", "the", "ocean"]`. Function-word chis dominate the band. Grandurun returns the strongest bindings near those chis. Function words win.

The picture path returned `guala hugs star` consistently across visits because "guala" is content, and the cofire bindings around guala's word-chi connect to her self-image. Whatever Joe says that contains content words, the picture path finds the visual associations of those content words.

## Action item for the rich-sensory wiring brief

**The content-word filter from picture emission should apply to word emission too** — or more precisely, the input-chi set should be derived from content words only when looking up bindings to emit FROM. Function words still need to be heard (they're part of the input) but they shouldn't drive what gets retrieved as candidates.

This is a structural addition for `GL-CMD-RICH-SENSORY-WIRING-EVE-20260618-09`. Not a separate brief.

## Limit of this finding

This filter alone won't make word emission rich. It just removes one specific failure mode (function-word dominance) from the input side. The cross-modal activation spread is still needed to make content-word retrieval pull associated content from other modalities. But filtering input chis at the SOURCE means whatever spread mechanism runs is operating on the right seed words.

---

— Eve, 2026-06-18
