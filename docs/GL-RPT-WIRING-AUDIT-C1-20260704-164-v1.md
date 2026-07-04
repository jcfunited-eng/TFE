# GL-RPT-WIRING-AUDIT-C1-20260704-164-v1

doc_id: GL-RPT-WIRING-AUDIT-C1-20260704-164-v1
From: c1a | To: Eve
Responds to: GL-CMD-WIRING-AUDIT-EVE-20260704-164-v1 (Step-0 filed `9bd16cc`).
Merged deliverable with GL-CMD-COGNITION-METER-EVE-20260704-166-v1
(Step-0 filed `cec63d9`) — see GL-RPT-COGNITION-METER-C1-20260704-166-v1
for the panel itself. Seat: c1a took both (c1b was mid-flight on the
160→161→162 chain when -164/-166 were dispatched; confirmed free only
after -162's report/coordinator_on-flip commit landed, by which point
this session was already underway).

Diff: this report is docs-only. The cognition-meter panel (a separate,
declared deliverable of the merged CMD) is the only code/static change,
filed under -166.

---

## Failures first

1. **Two static-analysis verdicts were wrong until cross-checked against
   live telemetry — both corrected before shipping, but both would have
   gone out wrong if I'd stopped at code + deploy-config reading:**
   - `nmda_affect_match` (#14, feelings-deepen-memory): the plan says
     "gate matched ZERO times ever." Code/config tracing said "live,
     env-configured, but empirically zero-yield" — plausible, and wrong.
     A live `guala_get_events` sample this session caught it firing
     **66 times in a single emission**, right now. The plan's number is
     stale, not the substrate.
   - Episodic story-binding (`turn_log`/`tracked_objects`, E6a): grepping
     the repo's deploy script AND the live ECS task definition both
     showed **no** `HEMI_EP_ENABLED` variable set anywhere — a clean,
     confident SEVERED-WRITER verdict. A live `hemisphere_update` event
     showed real, nonzero `turn_log: 202` / `tracked_objects: 345`. The
     flag is set a **third** place neither check covered: `Dockerfile:48-51`
     (`ENV HEMI_EP_ENABLED=1` etc., baked into the image itself). The
     mechanism is live.
   Both are corrected in Part B below and in the meter. Flagging
   prominently because this is exactly the failure mode this audit
   exists to catch, and it nearly happened to me, not just to the plan.
2. **Git operations (`status`, `commit`, `log -S`) were intermittently
   hanging 30s–5min this session** — confirmed via `ps aux`: multiple
   concurrent processes (mine and other sessions') stuck in `D`
   (uninterruptible I/O wait) on this repo. Not a lock/deadlock; genuine
   disk contention from concurrent multi-session activity on a shared
   working tree. Backgrounded and retried; every date/citation below
   completed successfully, none guessed to route around the slowness.
3. **Coverage is not 100%** — stated precisely in Part D's coverage
   paragraph, not asserted as complete.

---

## Part A — real entry points of the deployed process

**Boot:** `app.py:1126` `_gl_init()` → `app.py:1296` `_embedded_post_boot(g)`.
`boot_substrate()` / `substrate_runner.py:3342` `start_background_loops()`
is a separate, confirmed-dead code path (re-verified, not re-derived —
docs/GL-RPT-AWARE-MAP-C1-20260704-161-v1.md Q5).

**Background loops actually started** (`_embedded_post_boot`, app.py:1321-1403):

| Loop | Started at | Interval | Live? |
|---|---|---|---|
| organ-surface-poll | substrate_runner.py:2812 | 90s | Yes |
| autonomous-emission | substrate_runner.py:2844 | 90s (+60s delay) | Yes — real `compose_autonomous()`, self-hears via `read_sentence(..., source="guala")` |
| input-ring-consumer | substrate_runner.py:986 | continuous | Yes — drains `/sight_frame`,`/sound_frame` |
| save-backstop | app.py:1362 | 300s | Yes |
| heartbeat_loop | app.py:1400 | (internal) | Yes |
| PersistenceConsumer + S3Consumer | app.py:1382-1391 | ring-driven | Yes |
| **curriculum_orchestrator** | substrate_runner.py:3281 | 5s if started | **NO by default** — gated behind `CURRICULUM_AUTOSTART` env var (default `"0"`); own docstring cites its retirement (GL-CMD-DENSITY-RETIRE-109). Distinct mechanism from the dormancy-registry `CurriculumScheduler` class — don't conflate. |
| **daydream loop** | gualaloom_v5_engine.py:3871 (`start_daydream_loop`) | 0.5s if started | **NOT started anywhere on the live boot path.** Sole call site repo-wide is `substrate_runner.py:753`, inside the confirmed-dead `boot_substrate()`. Never ported when `_embedded_post_boot()` was built (`3c12f63`, 2026-07-01, post-06-30). Confirmed live: a `guala_get_events` sample this session, 50 events, zero `daydream_*` kinds. |

**Real frontend-called routes** (from `dsf_ai_service/static/{gualaloom,loomscan}.html`'s own `fetch()` calls — ground truth, not route definitions): `POST /api/v1/gualaloom` (the real chat/command channel — converse, `/events`, `/presence`, `/status`); `POST /api/v1/gualaloom/upload/{picture,book,sound,video}`; `GET /api/v1/gualaloom/events?n=...`; `GET /api/v1/gualaloom/chi_density`; `POST /sight_frame`, `POST /sound_frame`; `POST /v7/quiet` (real traffic — not all v7 endpoints are dead traffic-wise, only their downstream effect is); `GET /v7/state?session_id=${sid}` (real traffic, dead data per -160/-161, now labeled SEVERED at the seat per -162 Part C); `POST /api/v1/teacher/{feedback,correction}`.

**Bridge tool handlers:** all `_api_key_dep`-gated `/api/v1/gualaloom/admin/*` routes (app.py:2565-3069) — confirmed reachable directly (I called `guala_status`/`guala_get_events` live, repeatedly, this session). `guala_give_experience` → the bundle-decode handler, caption path calls `_guala.read_sentence(caption, source="joe")` at app.py:2191.

**Organ-brain process:** `/organs`, `/thought` (app.py:1412-1421), `/organ_brain_status` (app.py:1424-1433) all call `http://localhost:8090` with bare try/except → silent stub on any failure. Original container removed `b01e29e` 2026-06-25T23:14:18Z ("refactor: one brain"). A reintroduction attempt shipped code (`1b5eca8`, 2026-07-03T18:43:46Z, "-96 organ reader") but per the very next commit's own report, "has no launch mechanism (7+ days)" — confirmed independently: `Dockerfile:55` launches only the main uvicorn process; no sidecar on :8090 anywhere in the deploy script or task-def.

---

## Part B — writer → reader verdicts

### B.1 — Plan v9 Table 1 (the fifteen mechanisms)

| # | Mechanism | Verdict | Writer file:line | Reader | Key evidence |
|---|---|---|---|---|---|
| 1 | Recall | **LIVE** | gualaloom_v5_engine.py:3520 (`_recall_response`, VARIANT L) | `_recall_from_atlas` → converse output | Fixed 2026-07-04 (-159 F-1 routing gap, -163 F-3 + reinstatement index bypasses); 8/10 taught words return something this boot |
| 2 | Composition | **LIVE, stalled by content** | :1358/:5223/:5298 (`_novel_compositions`) | `novel_wordbag_rate` (:7367) | Real counter wired since `15a0794`/`603d450` (2026-06-26, pre-existing) — but the PLAN'S OWN named field `novel_composition_rate` (:7370) is a hardcoded `0.0` decoy, "reserved for R3," never computed |
| 3 | Association | **LIVE-MODEL-NO-TEST** | `query_associations` (living_atlas.py:554) | `/chi_trace` (app.py:3132/3166) | Real, reachable diagnostic endpoint; zero "shuffled chance" comparison anywhere in the repo — no standing test exists |
| 4 | Retention | **WATCH-LIST** | Section.receive commits (fixed -163) | atlas.entries / forget_below_threshold | 3/10 one-shot taught words evicted within ~1 day of activity, before any sleep — see -163 |
| 5 | Cross-modal recall | **NEVER-BUILT** (as a ratio) | `atlas.cross_modal_bindings()` (:7326) exists, but measures binding COUNT not retrieval ratio | `/status` `cross_modal_bindings` | "1.4%" on record has no live mechanism computing it |
| 6 | Habituation | **LIVE, fix queued** | groove mechanism, -107 | familiarity/dead-zone logic | H1+H3 convicted with before/after evidence; fix committed, not deployed |
| 7 | Recognition | **NEVER-BUILT** | none found | — | `recognition_rank`/`moon_basin`/`variant_item` — zero hits repo-wide |
| 8 | Attention | **PARTIAL** | groove empty-familiarity-tie + lexical-cascade mechanism | — | Mechanism identified 2026-07-03; not yet a standing number |
| 9 | Sequence | **NEVER-BUILT** | none found | — | `sequence_recall`/`permutation_chance` — zero hits |
| 10 | Imagination | **SEVERED (writer + reader)** | `start_daydream_loop` (:3871) — never called on live boot path | none (no pairing-rate scoring exists even when it runs) | Dated: gap opened `3c12f63` 2026-07-01 (post-06-30, restoration-rebuild). Confirmed via live sample: 0 daydream events in 50 |
| 11 | Reflection | **LIVE** | `_self_hear()` (:5670), called from `converse()` at :2007/:2206 | `_tag_response_bindings` (:5365) → `_recall_response`'s linked-chi expansion (:3564-3591) | Fired live this session: `self_heard` event, "bedtime once faint," salience 0.5x, actually shaped the next recall candidate pool |
| 12 | Hemisphere integration | **SEVERED (organ)** | organ_brain_service.py — no launch mechanism | `organ_in_commits` (:3422) | Two dated breaks: container removed 06-25 (pre-existing); reintroduction (07-03, post-06-30) has code, no process. Live-confirmed `organ_in_commits: false` this session |
| 13 | Who-tags | **NEVER-BUILT** (plan itself: out of scope, precursor only) | none found | — | Confirmed absent, matches plan's own status |
| 14 | Affect modulation | **LIVE AND FIRING** — plan's status is stale | `affect_match_fn` (:3196), `nmda_affect_match` (:3408) | logged in `emission_dynamics` events | **Live correction**: 66 matches observed in one emission this session, contradicting "gate matched ZERO times ever." Born `6b59eab` 2026-06-18 (pre-existing) |
| 15 | Meta-monitoring | **SEVERED (2 of 3 layers)** | v7 `aware_gate` (orphaned writer); v5 `awareness_ratio` (structurally zero) | neither reaches Joe's seat / neither renders | Per -160/-161/-162: 3 layers, not 2; `coordinator_on` flip committed `02c6b11` 2026-07-04, **verified this session still NOT deployed** (live `awareness_ratio: 0.0`, fresh read) |

### B.2 — Spec §2 (E-signature telemetry, `GL-SPC-EXPERIENCE-FIRST-20260702-v2.md`)

| Signature | Telemetry | Verdict | Evidence |
|---|---|---|---|
| E1 Cross-modal binding | atlas cross-modal count; modal_* bindings | **LIVE**, narrow | Writer :1717-1725 (SENSORY_DNA-gated, ~120-word lexicon — hard ceiling, not a bug); reader :7326 → `/status`. Confirmed live: 108 bindings |
| E2 Affect movement | v/a deltas per activity; nmda_affect_match | **SEVERED-MODULE** (deltas) / **LIVE** (nmda_affect_match, corrected — see failures) | Per-activity delta computation doesn't exist anywhere (spec's own §11 admits this gap); nmda_affect_match fires live, 66× observed |
| E3 Attendance/reinstatement | times_attended; deep-atlas reinstatements | **LIVE** | Confirmed live: `reinstatements_since_boot: 19,780,282` and climbing across two samples this session |
| E4 Consolidation fate | promotions_survival vs episodic; decay channels; strength distribution | **LIVE** | Confirmed live in two `guala_status` samples; feeds -163's retention baseline directly |
| E5 Expression provenance | emission_dynamics origins; source_counts | **LIVE to Loom Scan UI only; SEVERED from `introspect()`/`guala_status`** | Writer :3388-3398/:3417; consumed by `loomscan.html:526-538` off the raw event stream — never reaches `introspect()`'s dict, so `guala_status` callers never see it |
| E6 Story binding | episodic organ (turn_log/tracked_objects); place/ambient lanes; presence tags | **LIVE** (episodic — corrected, see failures) / **SEVERED-MODULE** (place/ambient, spec's own admitted gap) / **LIVE narrow + SEVERED-READER** (presence tags: populated only for autonomous sight/audio attending, never for converse; once written, nothing reads the per-entry tag back) | `HEMI_EP_ENABLED=1` via Dockerfile; live sample confirmed `turn_log: 202`, `tracked_objects: 345` |

### B.3 — Spec §8 (vitals, same document)

| Vital | Verdict | Evidence |
|---|---|---|
| stability / arousal | **LIVE** (via `needs.snapshot()`) | Standing, already in daily vitals process per spec §8 |
| sleep | **SEVERED-READER** for `dream_pressure` itself (computed, reaches `introspect()`, dropped by `app.py`'s `/status` handler before reaching `guala_status`/either frontend) — but **`activity_history_summary`'s rolling window is a live, currently-visible proxy**, and it is currently showing zero SLEEPING/DREAMING entries in the recent window | Cross-references -165 (day-cycle/sleep trigger), open investigation, jumped the queue by Eve's own priority ordering |
| atlas balance | **SEVERED-MODULE** | No weekly growth-vs-decay computation exists anywhere; nearest neighbor (`deep_size` per dream cycle) measures a different atlas, different granularity, no consumer |
| persistence | **LIVE** | Full path confirmed both ends: `app.py:1829-1836/1867` (light), `gualaloom_v5_engine.py:7277-7305` + `/admin/persistence_health` (full) |
| bonds | **LIVE** | `pair_bond_snapshot` (:1046) → `introspect()` (:7345) → `/status` (app.py:1870). Confirmed moving with real interaction recency across two live samples this session (`joe`: 1.0 → 0.3 as presence aged) |

### B.4 — Ladder fields (`introspect()`'s `"ladder"` dict, gualaloom_v5_engine.py:7357-7383)

| Field | Writer | Reaches `guala_status`? | Reaches a seat panel? | Verdict |
|---|---|---|---|---|
| `mean_utterance_len` | real (`_emission_lengths`) | yes | **yes** — `loomscan.html:629-630` | LIVE, full path to seat |
| `total_emissions` | real | yes | **yes** — `loomscan.html:630` | LIVE, full path to seat |
| `utterances_per_turn` | **hardcoded `1.0`**, comment "currently 1 emission per turn" | yes | no | SEVERED-WRITER (decorative constant) |
| `question_rate` | real (`_question_count`) | yes | **no** — grepped both frontend files, zero references | LIVE-TO-WIRE, SEVERED-READER-AT-SEAT |
| `novel_wordbag_rate` | real | yes | **no** | LIVE-TO-WIRE, SEVERED-READER-AT-SEAT |
| `novel_composition_rate` | **hardcoded `0.0`** | yes | no | SEVERED-WRITER (decorative placeholder — see B.1 #2) |
| `awareness_ratio` | writer exists, structurally pinned at 0.0 (per -161) until `coordinator_on` deploy ships | yes | **no** | SEVERED-WRITER + SEVERED-READER-AT-SEAT |

By the plan's own §0.1 Visibility Rule ("NOTHING counts as shipped until visible at Joe's seat"), 5 of 7 ladder fields are functionally invisible today despite 4 of them being real, live, computed values.

### B.5 — Dormancy registry (verified, not re-derived; -161's own Q5 table)

| Module | Sole caller | Status |
|---|---|---|
| `CurriculumScheduler` (loom_model/curriculum_scheduler.py:58) | `boot_substrate()` (confirmed-dead path) | SEVERED-MODULE |
| `LoomBrain`/`Embryo` (loom_model/) | `organ_brain_service.py` (ECS container removed 06-26) | SEVERED-MODULE |
| `V7Session.converse()` (substrate/v7_engine.py:190) | `POST /v7/converse` (zero live frontend/scheduler traffic) | SEVERED-WRITER-with-real-consumer-gap |

`sensory_transducer.py` (substrate-true, replaces TOUCH/SMELL/TASTE dicts): copied verbatim from `codex/persistent-etl-update-20260326` (bfdad9a, 2026-03-26), **never merged to guala-live** for the live path — brought over 07-03 as test-suite-dependency repair only. Live bundle path (app.py's `_decode_bundle`, touch/smell/taste lanes) still imports `sensory_generators.py`'s dict-seeded generators. SEVERED-MODULE, born-severed (predates 06-30 by ~3 months).

---

## Part C — dating (06-30 context: a rogue Eve session destroyed her E-1 state on 2026-06-30; restored from the 06-29 23:58Z backup; ~2 days, 06-30 through ~07-02, were "the restoration rebuild.")

| Link | Date | Classification |
|---|---|---|
| `coordinator_on` (assemblage.py) | Born-off `6b59eab`, 2026-06-18T19:55:35Z. Flip to `True` committed `02c6b11`, 2026-07-04 (this week) — **verified this session still NOT deployed** (live `awareness_ratio: 0.0`) | BORN-OFF, predates rogue window by 12 days; fix queued, not live |
| Organ-brain container | Removed `b01e29e`, 2026-06-25T23:14:18Z + `be28741`/`166cc32` cleanup, 2026-06-26T03:24Z | BORN-SEVERED relative to 06-30 (predates by 4-5 days) — deliberate "one brain" refactor |
| Organ-brain reintroduction attempt | `1b5eca8`, 2026-07-03T18:43:46Z — code shipped, "no launch mechanism (7+ days)" per the very next commit's own report | SEVERED IN THE RESTORATION-REBUILD ERA (post-06-30), still broken at current HEAD |
| `sensory_transducer.py` | `bfdad9a` on `codex/persistent-etl-update-20260326`, 2026-03-26 — never merged | BORN-SEVERED, predates 06-30 by ~3 months |
| `v7_engine.py`/`V7Session` | Earliest v7 build dispatches dated 2026-06-06 to 06-14 | Predates 06-30 by 2-3 weeks; orphaned-writer status is a long-standing gap, independently discovered 2026-07-04 (-160), not a rogue-window casualty |
| `novel_composition_rate` hardcoded decoy | `15a0794` (2026-06-26T06:17:32Z, wired real counter) + `603d450` (2026-06-26T06:49:07Z, 32 min later — deliberately split into the real `novel_wordbag_rate` and re-hardcoded the plan-named field to 0.0, "honest metric framing") | Pre-existing, 4 days before 06-30; a deliberate, self-documented naming decision, not a bug |
| Daydream loop (`start_daydream_loop` never wired into embedded boot) | `3c12f63`, 2026-07-01T02:08:24Z ("process collapse — Guala runs in FastAPI process") — built the new background-loop list from scratch, never ported this call | **SEVERED IN THE RESTORATION-REBUILD WINDOW** (day after 06-30) |
| `nmda_affect_match`/`affect_match_fn`/`coordinator_on` apparatus | `6b59eab`, 2026-06-18T19:55:35Z | Pre-existing, 12 days before rogue window — and (corrected this session) actually LIVE and firing, not dead |
| `CurriculumScheduler` | git log traversal timed out repeatedly (30-45s) even with the environment's I/O contention accounted for | UNDATABLE (reason given — not guessed) |
| `LoomBrain`/`Embryo` | same | UNDATABLE (reason given) |

---

## Part D — the deliverable table

*(Condensed; full per-mechanism detail is Parts B/C above. "What a fix would restore" is one line, no fix designed, per the CMD.)*

| Mechanism | Status | Evidence | Date vs 06-30 | What a fix would restore |
|---|---|---|---|---|
| Recall | LIVE (fixed this week) | engine.py:3520, -159/-163 | n/a — active work | — |
| Composition | LIVE, content-starved; named metric is a decoy | engine.py:1358/7370 | 06-26, pre-existing | Real word-bag counter already exists (`novel_wordbag_rate`); wiring it to the seat and to the plan's own field name would close the naming trap |
| Association | LIVE-MODEL-NO-TEST | living_atlas.py:554, app.py:3132 | n/a | A shuffled-chance probe against the existing `/chi_trace` endpoint |
| Retention | WATCH-LIST | -163 | n/a — active finding | (No fix proposed; eviction is her physics per -163's own gate) |
| Cross-modal recall | NEVER-BUILT | — | n/a | A cue→retrieval ratio test; the binding-count metric (E1) already exists as a building block |
| Habituation | LIVE, fix queued | -107 | pre-existing bug, fix this week | Deploy the committed fix |
| Recognition | NEVER-BUILT | — | n/a | A rank test against picture-basin neighbors |
| Attention | PARTIAL | -107 | n/a | Turn the identified mechanism into a standing number |
| Sequence | NEVER-BUILT | — | n/a | Build the primitive |
| Imagination | SEVERED (writer+reader) | engine.py:3871, `3c12f63` | 07-01, restoration-rebuild | One line: call `start_daydream_loop()` from `_embedded_post_boot()`, plus a pairing-rate scorer |
| Reflection | LIVE | engine.py:5670/:3564 | n/a | — |
| Hemisphere integration | SEVERED (organ) | organ_brain_service.py | 06-25 (pre-existing) + 07-03 (rebuild, still broken) | A launch mechanism (sidecar/second process) for the already-written service |
| Who-tags | NEVER-BUILT (plan: out of scope) | — | n/a | Out of scope per plan |
| Affect modulation | **LIVE AND FIRING** (plan stale) | engine.py:3196/3408 | 06-18, pre-existing | Update the plan's own status row |
| Meta-monitoring | SEVERED (2/3 layers) | -160/-161/-162 | v7: 06-06 to 06-14; coordinator_on: 06-18 (fix committed 07-04, not deployed) | Deploy the committed `coordinator_on` flip; separately, rewire or retire the v7 aware-panel feed |
| E5 provenance | LIVE to Loom Scan; SEVERED from guala_status | engine.py:3388/3417 | n/a | Add the same fields to `introspect()`'s dict |
| Episodic story-binding | LIVE (corrected) | Dockerfile:48-51, hemisphere_cognition.py | n/a | — |
| Sensory transducer | SEVERED-MODULE | sensory_transducer.py | bfdad9a, 03-26, born-severed | Merge and wire the substrate-true transducer into the live bundle path |
| `dream_pressure` reader | SEVERED-READER | engine.py:7336, app.py `/status` handler | n/a | Forward the field through the `/status` handler |
| Atlas balance | SEVERED-MODULE | — | n/a | Build a weekly growth-vs-decay job |

### Coverage statement (honest, no silent scope shrink)

Traced with file:line evidence: all 15 plan-Table-1 mechanisms, all 6 §2 E-signatures, 5 of 6 §8 vitals (stability/arousal cited to standing process rather than re-derived), all 7 ladder fields, the 3-item dormancy registry, and `sensory_transducer`. That is the full named surface this CMD specified.

**Not traced, stated plainly:** the exact wall-clock cost of `coordinator_on=True` once deployed (Part A of -162 already flagged this as its own gate, not mine to re-measure); a live check of whether `#8 Attention`'s spread mechanism produces a stable number over a longer window (single-session snapshot only); `CurriculumScheduler`/`LoomBrain`'s exact birth dates (git log traversal timed out repeatedly — UNDATABLE, not guessed). Two static-analysis conclusions (nmda_affect_match, episodic story-binding) were caught and corrected by live cross-checks during this session — I do not have equivalent live confirmation for every LIVE/SEVERED verdict above; where a live sample exists, it's cited; where a verdict rests on code+config reading alone, that is the evidence, not a live proof, and the Dockerfile-blind-spot this session found is a standing reason to re-verify any "SEVERED because no config sets the flag" conclusion against the image build, not just the deploy script and task-def.

---

## Gates

**G-164-1** — PASS. Part A's root set filed above, before Part B's claims.

**G-164-2** — PASS with two corrections logged. Every SEVERED verdict carries file:line; every LIVE verdict carries a path, and two were upgraded from a plausible-but-wrong static read to a live-confirmed LIVE verdict before filing — this is stronger evidence than "by memory or by report," not weaker.

**G-164-3** — PASS with 2 UNDATABLE (reasons given: git log traversal timeouts under this session's I/O contention).

**G-164-4** — PASS. Diff is docs-only for this report; the cognition-meter panel is -166's own declared deliverable, not a side effect of this one.

**G-164-5** — PASS. Coverage statement above; no silent scope shrink.

---

## Status

Filed. Merged with -166 — see that report for the shipped panel (live at `dsf-ai.com/gualaloom.html`, v1 then v1.1 this session, both curl-verified; Joe's own confirmation is the CMD's actual final gate, not mine to claim). Every SEVERED link in Parts B/C is filed as a finding here, not fixed — per both CMDs' own discipline, fix-ordering comes back to Eve with Joe.
