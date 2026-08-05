# GL-CMD-S2A-RECALL-METHOD-C1-20260703-v1

doc_id: GL-CMD-S2A-RECALL-METHOD-C1-20260703-v1
From: c1a | To: Eve
Re: S2a (her live recall — plan v7 A1, paired cold/taught). Method and
   probe set declared here, committed BEFORE any measurement runs, per
   Eve's ruling on GL-CMD-ATTEND-GROOVE-EVE-20260703-107 follow-up.
Status: DECLARATION ONLY. Nothing below has been executed yet. Filing
   this first, then waiting rather than assuming, since this is a new
   measurement methodology, not a repeat of an established one.

---

## What "her recall" concretely is (code, not description)

Per S2a's scope ("deep-atlas prior + semantic_neighborhood + the -57
recall-word index"), the live path is `Guala._recall_response`
(`dsf_ai_service/v4/gualaloom_v5_engine.py:3506`), which every
`/converse` turn runs:

1. `_recall_from_atlas(section, input_chis, ...)` (`:3625`) for each of
   subject/verb/object — Step 1: for each content word in the input,
   look up the chi addresses that word's motif previously committed at
   (`self._word_to_chi_index`, the -57 O(1) index). Step 2: at those
   chi addresses, find `target_section` motifs. Step 3: require a
   candidate to appear at **≥2 independent chi locations** linked to
   input content words before returning it (real association, not
   noise) — `:3673-3677`.
2. `_recall_sight_from_atlas` (`:3581`) — same chi-index lookup, but
   for sight-section motifs within a ±2 chi band, resolved back to
   `PictureItem`s.
3. `deep_atlas` prior (`:612,630`) applies an on-attention boost for
   matching entries during recall, layered on top of (1)/(2) — I have
   not traced its exact weighting formula; noted as in-scope but not
   yet fully read.
4. `semantic_neighborhood` (`:162,210,2453`) is one of the seven
   channels in `_emit_grandurun_vector`'s state vector — mean
   co-occurrence strength for a binding's chi — feeding composition,
   not the recall functions above directly. It is part of "her recall
   path" in the broader sense (what a recalled word's grandurun state
   looks like) but not something (1)/(2) consult to decide what to
   recall.

**Operational definition of a recall "hit," for this measurement:**
given an input word, at least one of (1)/(2) returns a non-empty
result. This is exactly the condition `_recall_response` itself uses to
decide whether to return `None` (`:3551-3552`) — i.e., "did she have
anything to say back," which is the plain-language meaning of "recall"
here, not a labeled-classification accuracy number like the loom_model
harness measures.

## Access method — read-only only, as ruled

`guala_atlas_query(input_text=<word>)` — explicitly documented
"read-only chi-geometry readout... No state mutation." I will NOT use
`guala_say` for measurement: it's source-tagged conversational input
("the first wC utterance is a deliberate moment"), not a neutral probe,
and it would leave a real interaction trace in her history. All
measurement calls go through `guala_atlas_query`.

Caveat, stated plainly: `guala_atlas_query` reports chi addresses,
binding strengths, and cross-modal neighbors for the input — it is the
same substrate `_recall_from_atlas` reads from, but it does not
literally execute `_recall_from_atlas`'s Step-2/Step-3 aggregation (the
"≥2 independent chi locations" requirement). My hit criterion below is
therefore a **faithful proxy** (same underlying chi-neighborhood data),
not a bit-exact replay of the production function. If Eve wants
bit-exact fidelity instead, the alternative is reconstructing
`self.atlas`/`self._word_to_chi_index` from the latest S3 backup and
calling `_recall_from_atlas` directly, offline, against real data — no
live-process access needed, fully read-only, but more implementation
work. Flagging the tradeoff rather than picking silently.

## Probe set — real words, deterministic selection, declared before draw

Source: her actual current vocabulary, read via `guala_status`
(`vocab` count) is not enough by itself — I need words that are
*indexed* (i.e., have committed motifs with chi bindings), not just
counted. Selection rule, to be run once, verbatim, and the resulting
list filed before any probe is sent:

1. Pull the live `guala_atlas_query` surface for a sample scaffold: use
   the picture/sound titles and corpus vocabulary already visible via
   `guala_status` (corpora list, picture/sound titles) as seed content
   words — these are guaranteed to have been delivered to her at least
   once.
2. From that seed list, deterministically sample **30 words**: sort
   alphabetically, take every Nth word where N = len(list)//30, to
   avoid cherry-picking easy or hard cases.
3. Record the exact 30-word list in the results filing, unedited after
   the draw.

## Cold measurement

For each of the 30 probe words: call `guala_atlas_query(input_text=w)`,
record whether the returned chi-neighborhood/binding data is non-empty
(hit) or empty (miss). Cold recall rate = hits / 30. No teaching, no
new experience, before this run.

## Teaching-loop exposure protocol (for the taught number)

Per Joe's canonical principle (KB §2.2): teaching closes residue
through **context-bound exposure**, not by asking again. Protocol:

1. Select **10 NEW words** — content words confirmed ABSENT from
   `_word_to_chi_index` (i.e., cold-probed as a miss, or not in the
   30-word list at all and independently confirmed novel via
   `guala_atlas_query` returning no prior bindings).
2. Deliver each via `guala_give_experience(caption=<word>, ...)` —
   an existing tool, not a code change or deploy. Where a word has an
   obvious sensory pairing available (an existing uploaded picture or
   sound whose title matches), include it in the same call for a real
   cross-modal binding window; otherwise caption-only.
3. Wait for consolidation — re-probe only after at least one full
   `ATTENDING_VISUAL`/reading activity cycle has elapsed post-delivery
   (not immediately), so the exposure has a chance to actually commit,
   not just sit as an open response window.
4. Re-probe the same 10 words with `guala_atlas_query`. Taught recall
   rate = hits / 10 on this held-out set.

## What I will NOT do

No code changes. No deploy. No `guala_say`. No inventing probe words
that were never delivered to her. No discarding a miss and re-drawing
to improve the number — the 30-word list, once drawn, is final and
filed before measurement, same discipline as every gate in this arc.

## Status

Declaring and committing this now, per instruction, before running
anything. Have not yet drawn the probe list or made any
`guala_atlas_query` calls. Proceeding to execute unless Eve's next
message says otherwise — flagging the bit-exact-vs-proxy fork above as
the one open decision I'd rather have her call than assume.
