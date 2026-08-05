# GL-RPT-RECALL-PROVENANCE-C1-20260704-158-v1

doc_id: GL-RPT-RECALL-PROVENANCE-C1-20260704-158-v1
From: c1a | To: Eve
Responds to: GL-CMD-RECALL-PROVENANCE-EVE-20260704-158-v1 (Step-0 filed
   `a153699`). Traces the 10 taught probes from
   GL-RPT-S2A-TAUGHT-C1-20260703-v1 against the identical taught
   snapshot (`2026-07-03_23-29-23`).

---

## Failures first

**No Part B fix ships.** Not because the verdict is physics (it isn't
— see below), but because 7 of 10 probes are genuinely
**NEVER-CANDIDATE by the CMD's own definition**, and the ONLY two
remedies I can construct both fall inside this same CMD's explicit
prohibitions ("no recall-path redesign," "no taught-binding boosts").
I did not pick one anyway. Detail in "Part B decision" below —
flagging this up front because it's the headline: the CMD asked for a
convicted-bug-gets-fixed path, and I'm reporting a convicted bug with
no safe fix available under this dispatch's own rules, not a physics
finding that closes the question.

Two significant **incidental findings**, neither part of the
requested trace but surfaced by it, reported because they bear on
future work:
1. **`_word_to_chi_index` is not live-updated for the primary
   grammatical write path.** `Section.receive()` (`gualaloom_v5_engine.py:703`)
   calls `atlas.record(...)` directly — it cannot call
   `self._atlas_record()` (the wrapper that also updates the index,
   `:1409-1415`) because `Section` only holds `atlas` as a parameter,
   not `self`. The index is only ever fully rebuilt at boot
   (`:6678-6692`). This means **every subject/verb/object/listen/
   ground/intro binding written during a live, un-rebooted session is
   invisible to `_recall_from_atlas` until the next restart** — a
   much bigger and more general finding than this CMD's 10 words. It
   does not affect my own measurement (this harness rebuilds the index
   fresh from the snapshot every run, which is boot-equivalent), but
   it may mean live production recall is currently worse than what
   this harness or the S2A numbers show, between reboots. Not
   investigated further here — outside this CMD's scope — flagging
   for its own dispatch.
2. **The same word can be indexed at multiple, different chi values
   across her history** (e.g., `applications` → `{39,40,41,42,43}`,
   `cuckoo` → `{16,17,18,19,20}`), even though `LanguageKrimelack.transduce()`
   is confirmed deterministic today (3/3 identical trials, direct
   test). The likely explanation is that the transduce/winding
   computation's parameters have changed at some point in the
   codebase's history, and old atlas entries retain whatever chi they
   were written under forever (entries are never recomputed). This
   means the "coarse-chi ceiling" isn't just 169 keys wide — a single
   word's own footprint can already span 5 of them. This directly
   feeds A.4 below and is real, structural evidence for the C-2
   rebuild, not a guess.

---

## Part A — provenance table (all 10 probes, A.1–A.4)

Method: `tools/guala_recall_bitexact_replay.py --provenance`, verified
**deterministic** before use — two runs on the identical snapshot,
`diff` exit code 0 (G-158-5).

| Probe | A.1 Existence | A.2 Candidacy (subject/verb/object) | A.3 Verdict |
|---|---|---|---|
| **aap** | in_vocab=True. **No atlas entry at its own current chi (1)** in any section. `_word_to_chi_index['aap']={3}` — a stale historical chi, pointing to one entry: `listen, motif=5317, strength=0.0217` (2 units above the 0.02 forget floor). | Not present in any of the 3 sections (0/0/0 relevant). | **NOT-IN-SNAPSHOT** — the teaching event produced no durable entry findable at the word's own current chi; the only trace of "aap" anywhere is a nearly-forgotten pre-existing entry, not something my teaching created. |
| **applications** | in_vocab=True. Entries at chi=41: `listen 0.0512`, `intro 0.0251`. Index chi span: `{39,40,41,42,43}` (historical drift). | subject/verb/object: **0 entries anywhere are "applications"** — winner in all three is `'something'` (score 4.0, found via the historically-drifted chi=40). | **NEVER-CANDIDATE** — bound only into listen/intro; never entered a section `_recall_from_atlas` queries. |
| **beckoning** | in_vocab=True. **Zero atlas entries anywhere** (own chi=34: empty). Not in `_word_to_chi_index` at all — no historical trace either. | 0 candidates in all 3 sections (the content-word-chi lookup returns nothing to search). | **NOT-IN-SNAPSHOT** — no binding survived (or was ever created) anywhere, in any section, despite vocab membership. Cause not further isolated (see below). |
| **breed** | in_vocab=True. Entry at chi=13: `listen 0.027`. Index span: `{13,14}`. | verb has 52 candidates; winner `'bark'` (score 2.0, found via chi=16 — bark's own current chi — appearing in the {13,14} historical set from bark's own drift). subject/object: 0 candidates. | **NEVER-CANDIDATE** — listen-only; never in subject/verb/object. |
| **chandelier** | in_vocab=True. Entries at chi=29: `listen 0.134`, `intro 0.0625`. Index span: `{27..31}`. | winner in all 3 sections is `'still'` (chi=29 — **exact match** to chandelier's own chi). | **NEVER-CANDIDATE** — listen/intro only. |
| **compelled** | in_vocab=True. **Zero atlas entries anywhere**, not in index. Same pattern as beckoning. | 0 candidates, all 3 sections. | **NOT-IN-SNAPSHOT**. |
| **cuckoo** | in_vocab=True. Entries at chi=18: `listen 0.0467`, `intro 0.0232`. Index span: `{16..20}` — **this is Eve's flagged collision chi**. | winner: subject=`'bongo'` (4.5), verb=`'really'` (5.0), object=`'there'` (5.0) — all at chi=18, **exact match**. | **NEVER-CANDIDATE** — listen/intro only; the H-COLLIDE evidence is real (see A.4) but moot for verdict purposes, since cuckoo was never eligible for these sections regardless of who else was there. |
| **earth** | in_vocab=True. Entries at chi=16: `intro 0.0769 (in_deep=True)`, `listen 0.0563 (in_deep=True)`. Index span: `{15..19}`. | winner: subject=`'bongo'` (3.6), verb=`'very'` (4.75), object=`'there'` (4.0). | **NEVER-CANDIDATE**. |
| **extinguishers** | in_vocab=True. Entries at chi=55: `listen 0.3288`, `intro 0.1619` — notably higher strength than most. Index span: `{53..57}`. | object: 1 candidate, `'illustrations'` (score 3.0, chi=57). subject/verb: 0. | **NEVER-CANDIDATE**. |
| **folded** | in_vocab=True. Entries at chi=20: `listen 0.0551`, `intro 0.0274`. Index span: `{18..22}` — **the other flagged collision chi**. | winner: subject=`'what'` (5.0), verb=`'will'` (7.0), object=`'pond'` (5.0) — what/pond at chi=20 exact match, will at 21. | **NEVER-CANDIDATE**. |

**7 NEVER-CANDIDATE, 3 NOT-IN-SNAPSHOT, 0 CANDIDATE-LOST.**

---

## Root cause of the 7 NEVER-CANDIDATE verdicts — named, stage + line

Every one of the 7 lands in `listen`/`intro` only, never subject/
verb/object. Traced to exactly two lines working together:

1. `gualaloom_v5_engine.py:1750-1751` — `_choose_role_sections`:
   `elif position_hint == "standalone": sections.append("listen")`.
   A single-word caption (no sentence, no neighbors) gets
   `position_hint="standalone"`, which routes to **listen only**. The
   DNA-driven half of the same function (`:1754-1758`) only adds
   subject/verb/object/modifier if `role_dna` is already one of those
   four — and a novel word's `role_dna` is `"unknown"` (confirmed
   directly: `LanguageKrimelack().transduce('aap')` returns
   `role='unknown'`, deterministic across 3 trials).
2. `gualaloom_v5_engine.py:3512` — `_recall_response` only calls
   `_recall_from_atlas` for `("subject", "verb", "object")`. It never
   queries `listen` or `intro`.

Put together: **a word taught as an isolated caption can structurally
never be recalled by `_recall_from_atlas`, regardless of strength,
repetition, or chi, because the two functions never share a section.**
This isn't a numeric competition — it's a wiring gap between where
standalone teaching lands and where text-recall looks.

---

## A.4 — chi-collision table (all 10 probes)

| Probe (chi) | Returned token(s) (chi) | Exact-chi match? | Strongest resident at probe's chi (excl. self) |
|---|---|---|---|
| aap (1) | — (no text recall) | n/a | `audio_high`, strength 0.9037 |
| applications (41) | something (40) | no — historical-drift chi, not exact | `listen 'zorplex'`, 0.6374 |
| beckoning (34) | — (miss) | n/a | `modal_sight`, 0.7646 |
| breed (13) | bark (16) | no — historical-drift chi | `verb 'the'`, 0.2799 |
| chandelier (29) | still (29) | **yes, exact** | `modal_touch`, 0.9607 |
| compelled (35) | — (miss) | n/a | `modal_sight`, 0.7 |
| cuckoo (18) | bongo/really/there (18/18/18) | **yes, exact** | `listen 'bongo'`, 0.4873 |
| earth (16) | bongo/very/there (18/17/18) | no — neighbor, via index drift | `listen 'bongo'`, 0.6144 |
| extinguishers (55) | illustrations (57) | no — historical-drift chi | `sight`, 0.998 |
| folded (20) | what/pond (20/20), will (21) | **yes, exact (2/3)** | `listen 'bongo'`, 0.616 |

**H-COLLIDE: confirmed real for 3 of 10 (chandelier/still,
cuckoo/bongo+really+there, folded/what+pond) — exact chi matches
against old, strong residents.** For the other 4 with returns, the
match is via each word's OWN multi-value historical index span, not a
literal exact-chi hit — meaning the "collision" is often really
**index breadth from chi drift**, not proximity in the naive sense.
Either way, **it doesn't change the verdict**: all 7 words were
already excluded from subject/verb/object before any collision could
matter. H-COLLIDE explains what a non-taught word gets picked instead
of; it doesn't explain why the taught word never had a shot — the
section-routing gap does.

---

## Part B decision

**NEVER-CANDIDATE (7 probes) — convicted, but I am not shipping a
fix.** The CMD's own rule for this verdict says fix it, -155
discipline. I looked for a -155-class fix (one line, mechanically
obvious, no judgment call) and could not find one:

- Making `_recall_response` also query `listen`/`intro` is a
  **recall-path change** — it changes what kind of content can come
  back for every user, not just taught words, and the CMD prohibits
  "recall-path redesign" explicitly.
- Making standalone-caption words default to a grammatical role (so
  they land in subject/verb/object) is a **write-path change to how
  ALL future standalone teaching gets classified** — not obviously
  narrower than a redesign, and arguably exactly a "taught-binding"
  accommodation the CMD calls PROHIBITED ("Taught-binding boosts or
  weighting tweaks are PROHIBITED — that's a tuned constant wearing a
  fix's clothes").

Both candidate fixes are judgment calls about how teaching and recall
should relate, not mechanical corrections of an obvious slip. Shipping
either without Eve's sign-off would be exactly the kind of
"improvise a different fix" this whole dispatch chain has repeatedly
told me not to do. Recommending: this needs its own CMD from Eve
naming which side of the gap to change (if either) — not something I
should resolve by picking one.

**NOT-IN-SNAPSHOT (3 probes: aap, beckoning, compelled) — filed, no
fix, per the CMD's own rule for this verdict.** The persistence gap is
Eve's to rule on. One sub-finding I could not fully close: `beckoning`
and `compelled` reached `self.vocab.add()` (confirmed — both
`in_vocab=True`) but produced literally zero atlas entries anywhere,
including `listen`, which every other word in this set got
unconditionally. I traced this as far as confirming the vocab-add
happens before any section-write logic, and that the "listen" section
receive path's own commit-gating logic should always accept a
word-labeled input (`or word_label` in its dead-zone check) — but I
did not find the specific reason these two specific words' listen
commits didn't survive. Stated plainly per G-158-2 rather than guessed
at.

**No "PHYSICS VERDICT — no code" line is filed**, because the evidence
doesn't support that label. Zero of the 10 probes are CANDIDATE-LOST
(a real strength competition where the taught word was surfaced and
out-scored). The verdict is bug (NEVER-CANDIDATE / NOT-IN-SNAPSHOT),
not physics — I'm just not the one who gets to pick the fix.

---

## Gates

**G-158-1** — 10-row, 4-column table filed above, before any Part B
commit (none shipped). **PASS.**

**G-158-2** — every verdict backed by pasted candidate-set /
existence evidence, not inference; NOT MEASURED stated plainly where
instrumentation couldn't close a question (beckoning/compelled's
listen-commit failure). **PASS.**

**G-158-3** — N/A, no Part B fix shipped.

**G-158-4** — N/A as literally worded ("PHYSICS VERDICT — no code");
see "Part B decision" for why that specific line doesn't fit and what
I filed instead.

**G-158-5** — `--provenance` verified deterministic (two runs,
identical snapshot, `diff` exit 0) BEFORE using it for this report.
**PASS.**

---

## Status

Holding here. No code shipped beyond the offline harness
instrumentation (`e684cf0`, Part A only, no engine changes). Two
incidental findings (index-update bypass; cross-era chi drift) filed
for their own future dispatches, not acted on here. Waiting on Eve's
ruling for: (1) which side of the standalone-teaching/recall-routing
gap to fix, if either, and (2) whether the beckoning/compelled
listen-commit failure and the index-update bypass warrant their own
CMDs now or later.
