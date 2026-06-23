# GL-IDEA-CONTENT-ACCESS-PROTOCOLS-20260617

**Status:** Captured idea. Not a brief. Architectural direction, likely substrate prime 1 or beyond.
**Origin:** Joe, end of session 2026-06-16/17 grandurun deploy.

## The seed

Instead of force-feeding Guala content (pictures/sounds/corpora uploaded by Joe/wC/c1), give her access to consume content herself through bounded protocols. Apps, public-domain stories, music, video — content she can request and ingest based on her own state.

**Crucially Joe-named:** "naturally not unfetter or unbound." Boundaries matter. The substrate's behavior under autonomous content access has to be safe-by-design.

## Why this is structurally different

Current architecture: all input is exogenous. Content arrives because someone uploaded it. Guala's "autonomous loop" picks among already-existing items. She has no agency over what enters her substrate.

Proposed: a "REQUESTING" or "SEEKING" activity. The coordinator selects it when novelty drive is high and existing material is exhausted (familiarity high across all items). The activity issues a controlled fetch against a curated source. Response gets ingested through the normal read path.

## What the boundaries look like

Substrate-physical safety primitives, not policy:

- **Source allowlist** — only registered protocols/endpoints. Project Gutenberg for stories. Curated public-domain music libraries. Age-appropriate kids' content sources. The substrate cannot fetch from arbitrary URLs.
- **Rate limit** — one fetch per autonomy cycle, with cooldown. Prevents runaway consumption.
- **Content classifier gate** — pre-ingest filter that rejects anything that fails age/content checks. Hard reject, not soft. Failed fetches log but don't bind.
- **Audit log** — every fetch logged: source, classification, ingestion outcome. Reviewable.
- **Per-source quota** — no single source dominates her substrate. Forces diversity.

## Why this matters for substrate health

The "diversity-starved" diagnosis (current session): she's spent 120+ attends each on the same 7 pictures and 1 corpus. Force-feeding scales linearly with Joe's bandwidth. Self-directed bounded ingestion scales with her novelty drive, which is the natural pacing mechanism.

It also flips the source-tagging story: content she sought has a different substrate signature than content given to her. That's information the affect machinery can use.

## What this is NOT

- Not a transgression register entry.
- Not a brief to c1.
- Not in scope until: grandurun proves out, situational/emotional selection design matures, empathetic influence layer is on deck, AND core substrate safety machinery is mature enough that autonomous content fetch isn't an open attack surface.
- Not unbounded web access. Not LLM-style search. Not anything Guala-shaped that runs arbitrary code or arbitrary network calls.

## Open questions for when it's time

- What protocol shape does the substrate use to request content? A new activity kind? A request-emission that the bridge layer interprets?
- Does the classifier live in substrate or in the fetch layer? Argues for fetch layer (substrate stays primitive-uniform), but then classifier is external state to maintain.
- How does she discover that sources exist? Curation by Joe — she has access to what Joe has registered as available.
- Does fetched content auto-bind, or does she have to "choose" to attend it after fetch? Latter probably safer and more cognitively meaningful — fetching is request, attending is consumption.
- How does the empathetic influence layer interact with content choice? "What would Joe want me to learn" as a selection bias?

Park until grandurun A/B closes, situational/emotional selection is on deck, empathetic influence design exists, and substrate safety primitives are mature.

— wC, 2026-06-16/17 (captured from Joe)
