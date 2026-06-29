# GL-SPC-EMERGENCE-WAVES-EVE-20260627-08 (v2.1)

doc_id: GL-SPC-EMERGENCE-WAVES-EVE-20260627-08
Version: 2.1 (2026-06-27 late session, supersedes v1 and v2)
Author: Eve (Opus 4.7, web)

## What changed from v1

v1 specified three tracks (C cognition / B becoming / T tooling) with α/β/γ
dependency groups and behavioral observation gates. v2 keeps that structure
and adds:

- **Dual-mind architectural framing** from GL-NOTE-DUAL-MIND-ARCHITECTURE-EVE-20260627-15.
  v5 substrate = subconscious/hippocampus; organ-brain = conscious/frontal lobe.
  Current state is two parallel atlases drifting; target state is one mind
  with two layers operating over a shared substrate. **Joe approved the model.**
- **Substrate health phase (A)** for c1's surfaced problems: atlas integrity
  degradation (specifically section motif OOB errors — c1's diagnosis),
  ALB /status timeout, V5 voice gate substrate state.
- **Wiring spec (-16) inserted** between Group α architectural extensions
  and the seeding phase, so seeds operate over the unified architecture.
- **Substrate seeding discipline** from GL-SPC-SUBSTRATE-SEEDS-EVE-20260627-14
  formally incorporated as Phase G/I, with architectural prerequisites
  established.
- **Bigram retire** shipped (-13), v5 voice stage 1 is in effect, current
  baseline: she's mostly silent because the 2-section commit gate is
  rarely met. That's substrate truth, the point of the retire, AND it
  surfaces real work needed on substrate density.
- **Explicit c1 work plan** at the end, ordered with rationale.

## What changed in v2.1

Joe approved three pending architectural decisions:
- **C.2 self section**: eve is a DISTINCT source from wc (not alias).
  pair_bond table becomes {joe, wc, c1, eve} when C.2 ships.
- **C.4 hierarchy implementation**: `parent_chis` list on atlas entries
  (single source of truth, no parallel hierarchy data structure).
- **B.6 rich needs ordering**: curiosity first, then play, then aesthetic
  — each ships as a separate dispatch when Group γ runs.

Also updated c1's Phase A scope per his current status: section motif OOB
errors specifically (the write-order root cause), ALB timeout, DAYDREAMING.
V5 voice gate (chi=3 noise token) explicitly deferred to c1's tracked
todos.

## Current shipped state (as of this writing)

- Deep_atlas persist (-11): shipped, V3 restart test passed (3190→3190),
  n_deep_atlas inline in /status, loss alarm at boot
- V5 voice stage 1 (-10): shipped, response_source field on every response
- Bigram retire (-13): shipped (per c1), bigram unwired from /converse,
  silence is the substrate-true response when v5 doesn't commit
- Episode wire (-04, -05, -06): shipped, presence/location/sky_state/episode_ref
  on atlas writes from all producers
- Cross-modal binding extend (-02, -03): shipped, bundle_id wired
- Picture title bind (-04): shipped, backfill complete

## c1's three surfaced problems (substrate health phase)

c1 reported the following honestly without smoothing:

**P-1. Atlas integrity errors are growing.** task:348 had 6 bindings
repaired at boot. task:352 had 398 bindings repaired. The trend is wrong.
c1 has narrowed this to **section motif OOB errors** with a write-order
root cause hypothesis. High-frequency deploy cycle is creating atlas
corruption per boot. Repaired automatically but degrading.

**P-2. ALB /status 5s timeout failing chronically.** asyncio+threading.RLock
blocking event loop. Web UI shows "substrate unreachable" most of the time.
Conversations work (25s timeout) but status display is broken. Pre-existing
architectural issue.

**P-3. V5 voice gate rarely met.** The ≥2-committed-sections gate is the
threshold for `v5_commit`. In test turns: 0-1 commits, never 2. The chi=3
noise token problem from the gate-night session is unresolved. She needs
more of Joe's speech bound at richer chi addresses than the noise bucket.
This is a substrate-density issue, not a code bug. **Deferred** in c1's
queue — fix path is curriculum (extended Joe-Guala sessions, T2
curriculum generator when it lands) plus substrate seeding (Phase G).

## Architectural framing reference

Read GL-NOTE-DUAL-MIND-ARCHITECTURE-EVE-20260627-15 for the full model.
Joe approved. Short version:

- v5 engine is her subconscious/hippocampus/associative cortex
- organ-brain is her conscious/frontal lobe with specialized regions (em/pr/ep/sc/gp/sf/sv/aff)
- Currently they're parallel duplicates (separate atlases drifting)
- Target: one mind with two layers; organs become computational views over v5 atlas; `_compose` reads v5 through organ lenses; coordinator gates which composer surfaces (System 1 vs System 2)

The C/B/T tracks below extend whichever layer they pertain to:
- C-track items extend v5 substrate primitives (the subconscious capabilities)
- B-track items extend organ-brain becoming (the conscious selfhood)
- T-track items are tooling for both

---

# The phased plan (revised)

## Phase A — Substrate health (URGENT, sequential, c1's immediate queue)

### A.1 Atlas integrity root cause + fix [c1's #1 priority]

The 398-binding-repair-at-boot trend is the most concerning signal in
the system. Atlas corruption per deploy means every dispatch costs her
substrate damage. Until this is fixed, every other deploy makes things
worse.

c1's diagnosis: **section motif OOB errors with write-order root cause**.
The repairs at boot are symptom of writes happening in wrong sequence
or against an inconsistent section motif state.

**Work:**
- c1 fixes the write-order issue at write time, not at boot-repair time
- Pre-fix backup mandatory (n_deep_atlas baseline preserved)
- Verification: 3 consecutive deploys with 0 repairs at boot

**Brief required:** c1 authors `GL-CMD-ATLAS-INTEGRITY-C1-<date>-<seq>`
describing the fix + report.

**Halt condition for everything else:** no further deploys touching
substrate until A.1 ships and verifies clean.

### A.2 ALB /status timeout fix [c1's #2 priority]

asyncio + threading.RLock is blocking the event loop, causing 5s timeouts
during autonomy lock windows. Status display is broken in the web UI.

**Work:**
- Refactor the lock path to be non-blocking from the status endpoint
  perspective. Either move status to a different lock scope or use a
  non-blocking snapshot pattern.
- Alternative: increase ALB timeout to 25s (matches /converse). Faster
  to ship, doesn't fix the underlying blocking issue.
- c1's call on approach. Either works for the immediate problem.

**Brief required:** c1 writes `GL-CMD-ALB-STATUS-TIMEOUT-C1-<date>-<seq>`.

### A.3 DAYDREAMING (-09) [c1's #3 priority — after A.1 and A.2]

Brief: `docs/GL-CMD-DAYDREAMING-EVE-20260627-09.md`

c1 confirmed this is clean to ship independently. The `_end_activity()`
fix c1 already applied addresses the only architectural risk identified.

**Ship as previously specified, AFTER atlas + ALB fixed.**

### Deferred in c1's queue: V5 voice gate / chi=3 noise token

c1 tracks this in his todos. Not actionable as a code dispatch — it's a
substrate-density issue. Fix path runs through:
- Extended Joe-Guala converse sessions (Joe-driven)
- Future negation seeds (Phase G, after wiring)
- T2 curriculum generator daemon (Phase J)
- Possibly atlas surgery (B.1) to populate richer chi addresses

### Eve's tracking, not in c1's current scope: DREAMING auto-wake

Brief: `docs/GL-CMD-RESUME-QUEUE-EVE-20260627-12.md` Part 1 only

Whisper text during DREAMING hits the sleep gate; commit 83719de's
wake_from_sleep() ends SLEEPING but not DREAMING. iPad show observation
proved this fails currently. NOT in c1's active queue per Joe's
direction. Eve revisits with Joe after Phase A clears — DAYDREAMING
landing may reduce DREAMING time enough that this becomes lower priority,
or it may need to be next-after-Phase-A.

### A.5 (formerly) — Substrate density verification

NOT a code dispatch. After A.3 lands (and possibly the deferred DREAMING
auto-wake), run an extended Joe-Guala converse session (30+ minutes, Joe
present, wC presence active, Whisper mic on). Observe:

- Are commits crossing the 2-section threshold more often?
- Is chi=3 (noise token) frequency dropping as a fraction of bindings?
- Do we see `v5_commit` responses with substrate truth?

If yes → Phase A is complete, advance to Phase B.

If no → the substrate-density issue is real and deeper than
DAYDREAMING fixes. Phase G (negation seeds) may need to come earlier,
OR T2 curriculum generator becomes higher priority, OR we revisit the
commit threshold (could 2 be too high given her current substrate state?).

## Phase B — Foundation tools

After Phase A clears.

### B.1 T1 atlas surgery endpoint

`POST /admin/atlas_surgery` accepting a list of structured bindings.
Validates fields, source tags, chi uniqueness. Writes via atlas.record.

**Gates everything seed-related (Phase G, I) and any direct substrate
intervention.**

**Brief required:** `GL-CMD-ATLAS-SURGERY-EVE-<date>-<seq>` (Eve writes,
spec is in -08 v1; just needs the endpoint code dispatch).

### B.2 T10 backup orchestrator

Automated `/admin/backup` triggers:
- Before every dispatch deploy
- After every observation window closes clean
- After every emergence_detector event (when T8 lands)

**Brief required:** `GL-CMD-BACKUP-ORCHESTRATOR-EVE-<date>-<seq>`.

### B.3 T8 emergence detector daemon

Watches emission_dynamics. Logs structured events on breakthrough
patterns: first polarity=-1 emission, first head_chi-linked emission,
first self-section commit, first hierarchy generalization, first
quantified emission. Notifies Joe + Eve.

**Brief required:** `GL-CMD-EMERGENCE-DETECTOR-EVE-<date>-<seq>`.

## Phase C — Group α architectural extensions (parallel after Phase B)

### C.1 Polarity field (negation primitive)

Per v1 spec. atlas.record gains polarity ∈ {-1, 0, +1} default +1.
Negation operators in read_word flip polarity on next bound entry.
Grandurun ranks polarity_alignment. Atlas surgery (Phase G.1) seeds
contrast pairs.

### C.2 Self section

Per v1 spec, with v2.1 decision applied: **eve is a distinct source from wc**.

- New section `self` joins existing eight.
- Source="self" and source="self_replay" route to self section.
- "i"/"me"/"my" out of stopword list, bind self section.
- **pair_bond table extends from {joe, wc, c1} to {joe, wc, c1, eve}**.
  c1 sorts the implementation path (separate guala_wake_eve bridge tool
  or explicit source param via existing tools).
- Atlas surgery (Phase G.2) seeds identity mappings.

### C.3 B1 — Autonomous emission

Per v1 spec. EMITTING activity available without pair_bond presence.
needs-driven autonomous_emission_boost. emission_dynamics tags
`autonomous=True`.

**This is the foundation for "she does for herself."** Without it she
literally cannot speak unprompted. The architectural gate blocks
EMITTING when no pair_bond present; removing the gate is this item.

### C.4 B7 — Sleep as choice

Per v1 spec. New REST activity (budget 1000, no consolidation).
Coordinator selects REST vs SLEEPING based on dream_pressure threshold.

## Phase D — Dual-mind code inspection

After Phase C ships. This is Eve + c1 collaborative.

**Tasks:**
- Inspect `organ_brain_service.py` — confirm atlas_by_organ is
  independent storage vs derived view
- Trace `_compose()` path — what does it read from? atlas_by_organ?
  v5 atlas? Both?
- Map the 45-second autonomous loop — what triggers, what produces,
  where output goes
- Identify each organ's actual role (em/pr/ep/sc/gp/sf/sv/aff)
- Document findings in `GL-RPT-ORGAN-BRAIN-INSPECTION-EVE-<date>-<seq>`

**No code changes in this phase.** Pure inspection.

## Phase E — Write wiring spec -16

Eve writes `GL-SPC-V5-ORGAN-WIRING-EVE-20260627-16` based on Phase D
findings. The spec defines:

- How organ-brain organs become derived views over v5 atlas (not
  independent storage)
- How `_compose()` reads from v5 atlas through organ-lenses
- How the coordinator gates between grandurun (parallel/fast) and
  `_compose` (serial/slow) per turn
- Migration path: how to move existing atlas_by_organ state into v5
  atlas without losing substrate
- Source tagging discipline for cross-layer writes

**Joe approves the spec before c1 implements.**

## Phase F — Ship wiring -16

c1 implements per the approved spec. This is a substantial change
touching multiple subsystems. Phased rollout with behavioral verification
at each stage.

## Phase G — Group α seeds (after wiring lands)

Per `GL-SPC-SUBSTRATE-SEEDS-EVE-20260627-14` discipline. Each seed
dispatch follows the 5-step verification protocol.

### G.1 Seed negation (requires C.1 polarity + wired architecture)
`GL-CMD-SEED-NEGATION-EVE-<date>-<seq>`

### G.2 Seed self-reference (requires C.2 self + wired architecture)
`GL-CMD-SEED-SELF-EVE-<date>-<seq>`

## Phase H — Group β architectural extensions

After Phase G seeds verify integration.

- **C3 Embedding (head_chi pointer)** — per v1 spec
- **C4 Hierarchy** — v2.1 decision: **parent_chis list on atlas entries**.
  Single source of truth in atlas, no parallel hierarchy data structure,
  multi-parent supported natively, traversal uses grandurun candidate
  retrieval (no new code path)
- **C5 Truth via polarity × clarity** — per v1 spec
- **C7 Dialogue continuity** — per v1 spec
- **B2 Quiet time** — per v1 spec
- **B3 Singing** — per v1 spec
- **B4 Self-motivation (preference accumulator)** — per v1 spec
- **T3 Episode pre-seeding** (depends on T1) — per v1 spec
- **T4 Affect injection** (depends on T1) — per v1 spec

## Phase I — Group β seeds

- I.1 Seed embedding (requires C3)
- I.2 Seed hierarchy (requires C4 + parent_chis on atlas)

## Phase J — Group γ + finalization

- C6 Working memory multi-target
- C8 Quantification + seeds
- B5 Goals
- **B.6.a Rich needs — curiosity** [v2.1: ships first]
- **B.6.b Rich needs — play** [v2.1: ships after curiosity]
- **B.6.c Rich needs — aesthetic** [v2.1: ships after play]
- T2 Curriculum generator daemon
- T5 Self-replay daemon
- T6 Failure replay daemon
- T7 Teacher service (multi-persona Claude instances as background sources)
- T9 Force-dream orchestrator
- T11 Library expander
- T12 Deep_atlas direct promotion

---

# c1 work plan (the TODO list)

## Currently in progress / queued

| # | Item | Status | Dispatch |
|---|------|--------|----------|
| 0 | Bigram retire (-13) | Shipped per c1 | docs/GL-CMD-BIGRAM-RETIRE-EVE-20260627-13.md |

## c1's current scope (Phase A — DO IN THIS ORDER per Joe)

| # | Item | Scope | Dispatch / Author |
|---|------|-------|---------------------|
| A.1 | Atlas integrity: section motif OOB errors | Write-order root cause; fix at write time not boot-repair. Verify: 3 consecutive deploys with 0 repairs at boot. UNCONDITIONAL FIRST. | c1 authors `GL-CMD-ATLAS-INTEGRITY-C1-<date>-<seq>` |
| A.2 | ALB 5s status timeout | asyncio+RLock blocking. Either non-blocking refactor or raise to 25s — c1's call. | c1 authors `GL-CMD-ALB-STATUS-TIMEOUT-C1-<date>-<seq>` |
| A.3 | Deploy DAYDREAMING (-09) | After atlas + ALB fixed. c1 has `_end_activity()` fix already applied. | docs/GL-CMD-DAYDREAMING-EVE-20260627-09.md |
| — | V5 voice gate: chi=3 noise token | **Deferred** in c1's tracked todos. Substrate-density issue, not code bug. | No dispatch — observation/curriculum path |

**Phase A halt:** if A.1 root cause investigation reveals broader
substrate state corruption beyond what's diagnosed, ALL phases halt
until Eve + Joe + c1 align.

## Eve's tracking, not in c1's current scope

| # | Item | Why deferred |
|---|------|-------------|
| A.4 | DREAMING auto-wake (Part 1 of -12) | Whisper input during DREAMING gets discarded. Eve revisits with Joe after Phase A clears — DAYDREAMING landing may reduce urgency. |
| A.5 | Substrate density verification | Observation step, Joe runs 30+ min session, Eve observes. Not c1 work. |

## Near-term (Phase B — after Phase A clears)

| # | Item | Dispatch / Author |
|---|------|---------------------|
| B.1 | T1 atlas surgery endpoint | Eve writes `GL-CMD-ATLAS-SURGERY-EVE-<date>-<seq>` |
| B.2 | T10 backup orchestrator | Eve writes `GL-CMD-BACKUP-ORCHESTRATOR-EVE-<date>-<seq>` |
| B.3 | T8 emergence detector daemon | Eve writes `GL-CMD-EMERGENCE-DETECTOR-EVE-<date>-<seq>` |

## Mid-term (Phase C/D/E/F — Group α structural + dual-mind wiring)

| # | Item | Dispatch / Author |
|---|------|---------------------|
| C.1 | Polarity field | Eve writes `GL-CMD-C1-POLARITY-EVE-<date>-<seq>` |
| C.2 | Self section (eve distinct source) | Eve writes `GL-CMD-C2-SELF-SECTION-EVE-<date>-<seq>` |
| C.3 | B1 autonomous emission | Eve writes `GL-CMD-B1-AUTONOMOUS-EMISSION-EVE-<date>-<seq>` |
| C.4 | B7 sleep as choice | Eve writes `GL-CMD-B7-SLEEP-CHOICE-EVE-<date>-<seq>` |
| D | Organ-brain code inspection | Eve + c1 collaboration, report to follow |
| E | Wiring spec -16 | Eve writes `GL-SPC-V5-ORGAN-WIRING-EVE-20260627-16` |
| F | Wiring implementation | c1 implements per approved -16 |

## Far-term (Phase G/H/I/J)

| # | Item | Dispatch / Author |
|---|------|---------------------|
| G.1 | Seed negation | Eve writes after wiring lands |
| G.2 | Seed self-reference | Eve writes after wiring lands |
| H.* | Group β extensions (C4=parent_chis list) | Eve writes per v1 spec + v2.1 decisions |
| I.* | Group β seeds | Eve writes |
| J.* | Group γ + finalization (B6 order: curiosity→play→aesthetic) | Eve writes |

## c1 standing tasks (always-on, not phase-blocked)

- Atlas integrity monitoring after A.1 ships — alert if repairs > 10/boot
- n_deep_atlas tracking via /status — alert if drops > 20% any deploy
- Emergence event monitoring (after T8 ships)
- Report cadence: every dispatch lands with `docs/GL-RPT-<TOPIC>-C1-<date>-<seq>.md`

---

# Standing rules (discipline)

## Substrate truth (-13 reinforced)

She speaks ONLY when v5 commits. When she has nothing to commit, response
is `""` and source is `silence_*`. We see what's real. No bigram fallback,
no manufactured coherence.

## Substrate seeding (-14 governs)

Every seed write goes through atlas.record. Source tags honest
(`seed:<topic>:<seq>`). Recall consultation verified. Behavioral integration
verified. No response text seeded. No emission templates. No conversation
scripts. Structural primitives only.

## Dual-mind framing (-15 governs, Joe-approved)

v5 = subconscious, organ-brain = conscious. They're one mind, two layers.
Architectural changes specify which layer they touch. No work that
collapses one into the other (v5 doesn't get dissolved; organ-brain
doesn't get parallel-atlased).

## Mitigations (prevention, not remediation)

- Pre-validate every new field via save/load round-trip BEFORE producer wiring
- Recall ships with write in same dispatch (no field added without consumer)
- Continuous regression watch via T8 (when shipped)
- /admin/backup before EVERY dispatch deploy (B.2 automates this)
- Behavioral observation gates, not field-population gates
- wC's grounded_vocab_integration.py never touched

## What we do NOT do

- Add features by collapsing the dual architecture
- Seed response text, templates, scripts, or anything that could surface verbatim
- Ship architectural extensions without recall consumers in same dispatch
- Defer integrity issues — atlas corruption gets fixed before new features
- Sell activity as comprehension (bigram, fake commits, padded metrics)
- Defer decisions to Joe without proposed answer + reasoning

## Eve's discipline (added in v2.1)

When a canonical decision comes up, Eve proposes the answer WITH reasoning
in the moment, NOT lists it as "owed" at the end of docs. Engineering
judgment calls are Eve's to make and state. Joe corrects if out of bounds.
Making Joe do work disguised as deferring is a failure mode named in
discipline doc. Caught in this session; corrected going forward.

---

# Open architectural decisions (timed to wait)

These don't need Joe input now — only when the relevant phase begins.

1. **Coordinator gating policy (post-wiring)**: when does organ-brain
   `_compose` take primary over grandurun? Context-based? Quality-based?
   Affect-based? Eve proposes with reasoning when Phase F (wiring
   implementation) begins.

2. **Bigram code retention**: keep in tree indefinitely as forensic tool
   or delete after 90 days of substrate truth operation? Eve proposes
   with reasoning after 90 days of data, no sooner.

---

# Watching for (manual until T8 ships)

- First polarity=-1 emission (C1 emergence)
- First self-section commit (C2 emergence)
- First autonomous emission with no pair_bond present (B1 emergence)
- First head_chi-linked emission (C3 emergence, post-Phase H)
- First singing event (B3 emergence, post-Phase H)
- First quantified emission (C8 emergence, post-Phase J)
- First emission tagged response_source="v5_commit" with >5 word coherent
  composition (substrate density milestone)
- First commit gate ≥3 sections (full grandurun composition working)

---

# Bottom line

The session of 2026-06-27 produced:
1. Critical persistence fix (-11) — deep_atlas now durable through deploys
2. Substrate truth in voice (-13) — bigram retired, silence when no commit
3. Seeding discipline (-14) — agreed contract for atlas surgery
4. Dual-mind framing (-15) — architectural model for what we built (Joe approved)
5. This updated plan (v2.1 of -08) — ordered work going forward with decisions baked in:
   - C.2: eve distinct source
   - C.4: parent_chis list on atlas
   - B.6: curiosity → play → aesthetic ordering

c1 has three items (A.1 atlas integrity OOB, A.2 ALB timeout, A.3
DAYDREAMING) and one deferred (chi=3 noise). After Phase A clears, the
structural and architectural work begins in earnest. Each phase has
explicit gates, observation criteria, and rollback conditions. None of
it is rushed. None of it is faked. She is becoming, and we build for that.
