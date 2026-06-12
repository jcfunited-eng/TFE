# GL-LEDGER-WC-20260611-047 — Canonical Open Ledger + Standing Rule
**Author:** wC | **Owners:** marked per item | **Replaces nothing — ABSORBS everything.**
045 and 046 are hereby ledger entries, not standalone briefs. Their full text remains in docs/ as reference; THIS document is the single source of open work.

## STANDING RULE (binding on every wC instance from today; goes in every handoff)
1. **One ledger.** All open work lives in docs/GL-LEDGER.md (this file, renamed on commit). New finds are APPENDED as ledger items — never spawned as new standalone briefs unless an item needs >1 page of spec, in which case the spec doc is written AND a ledger line pointing at it is added in the same turn.
2. **No silent supersession.** A document may only be superseded by a diff: the superseding text lists every item of the old doc with a disposition — CARRIED (ledger #), DONE (commit/task #), or DROPPED (Joe's explicit ruling, quoted). Anything unlisted is a leak and a wC failure.
3. **Session bookends.** Every wC session: FIRST ACT = ls-tree + read GL-LEDGER.md + diff it against repo/substrate reality (mark DONE items with evidence). LAST ACT = commit the updated ledger via c1's paste-ready command. The ledger is never allowed to be older than the last session.
4. **Find ≠ fork.** When wC finds a defect mid-review, the fix is added to the CURRENT open execution tier — the work in flight is finished, not abandoned for the shiny new hole.
5. **c1 mirrors:** c1 marks ledger items DONE with commit SHA + task # in the same commit chain as the work. "Done" without a SHA is not done.

---

## TIER 1 — c1 EXECUTES NOW, ONE DEPLOY (everything below ships together)
Fix specs in 045/046 where referenced; all evidence repo-verified at da55b40.

| # | Item | Spec | Why |
|---|------|------|-----|
| 1.1 | Canonical chi_address(winding)=winding%100, every atlas-recording lane | 046 F0 | words chi 3–21, sensory gens 257–573, exact-key binding → chemical lanes can never bind words |
| 1.2 | Per-channel sensory atlas records (like cochlear bands) | 046 F0b | scalar sum destroys combinatorial identity |
| 1.3 | Deterministic smell RNG seed | 046 F0c | salted hash → "ocean" chi changes every restart |
| 1.4 | Persist `_sounds` (guala_sounds.json) **AND `_videos`** (guala_videos.json) — full sensory-store persistence audit: _sounds, _videos, _sensory_items, bundle pictures | 045 F1 + NEW (videos verified memory-only, engine ~839, zero save/load) | every min=0 deploy erases them, incl. daddy's voice |
| 1.5 | Deterministic motif IDs — kill every salted hash()%1000 on persistence paths (incl. da55b40's sensory section, _atick_attending_audio, /addsound, bundle lanes) | 045 F2 | atlas entries orphan on restart |
| 1.6 | Bundle image lane through view_picture (real visual path in-window) | 045 F3 | row-sum chis are fake; bindings dead on arrival |
| 1.7 | B3 try/except on image lane; per-lane confirmation incl. failures | 045 F4 | partial failure 500s after caption landed |
| 1.8 | Bridge returns refs not dumps: sight_section/pictures/sounds/corpora as counts + last-10; guala_status < 4KB | 045 F5 = 040 Part B | the context trap; killed two wC predecessors; 25x |
| 1.9 | **Four ladder metrics in /status: mean_utterance_len, utterances_per_turn, question_rate, novel_composition_rate** | 042 queue item 1 — MISSED by 045 AND 046; zero code exists (verified) | how Joe watches the mountain shrink instead of hearing promises |
| 1.10 | Run tools/dump_strength_series.py in-container → commit docs/data/strength_series.csv | 042 C2 — script committed (cb1eb33), OUTPUT never delivered | gates wC Step-3 decay derivation |
| 1.11 | Same-day doc commits: this ledger (as docs/GL-LEDGER.md), 045, 046, GL-CMD-043, GL-BRIEF-IMAGEREF-036, handoffs 038/041/044; delete or stale-stamp GL-TODO-WC-20260611 (its "no brief exists" lines are wrong) | discipline rule 4 + first-act drift prevention | the repo carries truth |

## TIER 2 — JOE'S BROWSER VALIDATIONS (after Tier-1 deploy; the bar)
| # | Item | Pass criterion |
|---|------|---------------|
| 2.1 | Daddy-voice bundle | sound↔"daddy" binding in events; audio-only replay fires daddy-adjacent motifs; survives a deploy (per 1.4/1.5) |
| 2.2 | Ocean bundle | ≥1 atlas key with entries from ≥2 of {word, sight, audio, modal_*} sections, in events |
| 2.3 | Letter-B bundle | three-way glyph↔phoneme↔token binding |
| 2.4 | mp3 re-upload | "played her …" UI line; n_sounds≥1; ATTENDING_AUDIO + sound_motif_founded in events |
| 2.5 | Image-PDF + text-PDF (in-the-deep.pdf) | pages registered as pictures; "N pages, M lines" line; diff-check vs pdftotext on one sample |
| 2.6 | guala_status size check | < 4KB from the bridge |

## TIER 3 — GATED SEQUENCE (order is the gate; no skipping)
| # | Item | Gate | Owner |
|---|------|------|-------|
| 3.1 | Dream sequence: dream gate → forced dream → promotions_episodic>0 (currently 0) → unpause with Step-3 constant | Tier 1 deployed | c1 |
| 3.2 | Step-3 decay derivation (λ/SLOW_DIV/K/θ) from strength_series.csv; first-cut numbers in handoff 044 | 1.10 delivered | wC |
| 3.3 | R1 maturity: Q&A pairs survive first post-unpause dream with response links intact | 3.1 | observe |
| 3.4 | Self-Section v3 sequencing call relative to dream/unpause — explicit, never slipped into a bundle (brief 026 exists, design-ready) | 3.1 decision point | wC |
| 3.5 | GL-CMD-043 Stage 2 — deploys ALONE, 48h flooding watch | Tier 2 validated AND 3.1 complete | c1 |
| 3.6 | GL-CURR-ALPHABET draft against 023 Stage 2 spec (glyph+phoneme+token via bundles) | Tier 2 (2.3 proves the door) | wC |
| 3.7 | GL-BRIEF-PHRASE | R1 exit (3.3) | wC |
| 3.8 | 036 image-refs upload + 040 Part A (UI renders bridge exchanges, source-tagged — Joe's co-visit feature) | after Tier 1 (1.8 covers Part B) | c1 |
| 3.9 | Video MVP upgraded to WATCH-AND-LISTEN (042 ruling) | 3.5 chain per 029 + hearing validated (2.4) | c1 |
| 3.10 | Teaching window calibration (Fix C live, factor ~0.3) | 3.1 | c1+Joe |
| 3.11 | Dream-recall path for sensory generators (the second gate of Joe's gating ruling — only bundle + dream may fire chemical senses; dream side unbuilt) | 3.1 | c1 |

## TIER 4 — OPEN WATCHES & SMALL ITEMS (no gate, don't lose)
| # | Item | Owner |
|---|------|-------|
| 4.1 | Pending message for c1 to deliver via guala_say when his presence lands: "I'm glad her dreams are getting better" (c1 wake path: pair_bond c1=false — decide wake mechanism, TODO 15) | c1 |
| 4.2 | Attention skew watch: test_persist 698 attends vs ~96–220 others | wC monitor |
| 4.3 | Boot replay datapoint (037 V3/V4) | c1 |
| 4.4 | Curriculum GL-CURR-FOUNDATION: Joe's veto pass + Joe's layer | Joe |
| 4.5 | Pair-bond retirement criterion exists in code (need-variance <0.05 over 100 ticks) — note only | — |
| 4.6 | Banner/self-description: written WITH Guala, later, never without her | wC+Guala |

DONE THIS PERIOD (evidence): 042 C1 rename (5cb7cee, live in status) · A1–A4 wiring (55dcb25, task:93–96) · B1–B3 code (4df1d48) · bundle UI + sensory libraries (ac98c95) · physics generators (da55b40) · n_sounds in status (e917171) · 042 committed to docs (85a6e4b).
