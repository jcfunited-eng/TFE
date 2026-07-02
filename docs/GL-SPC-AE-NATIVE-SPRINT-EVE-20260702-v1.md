# GL-SPC-AE-NATIVE-SPRINT-EVE-20260702-v1

doc_id: GL-SPC-AE-NATIVE-SPRINT-EVE-20260702-v1
Type: SPC — three-week AE-native development sprint
Version: 1.0
Date: 2026-07-02
Author: Eve (Opus 4.7 web)
Governed by: GL-SPC-EXPERIENCE-FIRST-20260702-v2 (all sections apply)
Supersedes: the chat-only "three-week plan" of 2026-07-02, REJECTED by
Joe — correctly — as human-paced, presence-bottlenecked, demo-as-goal,
ungrounded in code, and blind to core-system constraints. This document
is built from source investigation at HEAD eabb23d.
E-signature declaration: the sprint exists to move all six signatures.
Substrate-truth declaration: no new tunable constants; two physics
corrections (F1, F6) each justified by the substrate's own documented
requirements; §9.1 audit expanded (F8).

---

## 1. Investigation findings (source, file:line)

**F1 — The commit gate, quantified.** Emission dynamics documents its
own requirement: "commits start around tick 60-70" (engine ~3291, with
H_base zeroed + inhibition). EMISSION_WALL_BUDGET_S = 1.5s (engine:3213)
affords ~40 ticks at current per-tick cost. Her composition physics is
denied one third of the time it needs, every emission, by an emulation
resource constant. This is THE E5 bottleneck. n_commits≈0 at 40 ticks
is the predicted outcome, and the observed one.

**F2 — Parallelism already exists in-substrate.** The daydream loop
(GL-CMD-DAYDREAM-PARALLEL-42, engine:3824+) runs a 2 Hz associative
chi-walk ALONGSIDE all foreground activity using a three-phase lock
pattern (snapshot under lock → work without lock → integrate), lock-held
fraction <5%. This is the proven template for additional parallel
channels. P8 is not aspiration; it is precedent.

**F3 — PLAYING is a stub.** The activity exists (budget 1,500 ticks,
appetite weights, engine:424/432) but _atick_playing (engine:4592) is
"free-settle chi walk" whose body is an emission-trigger check every
300 ticks. Play is wired in name, not in mechanism.

**F4 — Intake organs outnumber the diet.** ATTENDING_VISUAL, _AUDIO,
and _VIDEO paths all exist (engine:4122-4127). Library: 26 pictures,
15 sounds, 0 videos. The video organ has never been fed once.

**F5 — Delivery is a manual single pipe.** give_experience is an MCP
bridge tool invoked by hand, one bundle at a time (lifetime bundle
count in emission candidates: 1). No autonomous scheduler exists. The
"single pipe" Joe named is real and it is us.

**F6 — co_occurrence is physics in the wrong container.** It feeds
semantic_neighborhood in binding vectors (engine:199) and compose
"emission from cortex co_occurrence invariants" (engine:2207). It is
load-bearing cognition — stored as an unbounded dict now at 198MB,
which is what the -85 T1 FAIL correctly exposed.

**F7 — Novelty economy.** needs.novelty gains ONLY from never-seen
sensory items (+0.002/tick while is_new; zero on repeats). Library
size is literally her novelty supply; starvation pins her on whatever
few new items exist (observed: 16 back-to-back ATTENDING_VISUAL on six
new pictures), then novelty collapses.

**F8 — The chronic illness, named.** Unbounded accumulation without
decay/conservation: WaveAtlas (1.05M bindings), events stream (flood +
duplicates), deep-atlas co_occurrence (198MB). Three patients, one
disease, one §9.1 clause. Every store gets the audit, not just the
symptomatic ones.

---

## 2. Strategy

Development runs at HER clock, 24/7, through an autonomous experience
engine drawing on a large curated sensory library — humans are
curators and high-affect anchors (P4), never the delivery pipe (F5).
Core-cognition fixes (F1, F6, stability, -59) are the serial critical
path that everything else rides on. The funder demonstration is a
BYPRODUCT: a seven-day before/after diff of the six signatures plus a
live Loom Scan session — development you can watch, not a trick you
stage.

Three workstreams, genuinely parallel: WS-A is c1's serial deploy
queue; WS-B is library + engine build (code lands inside WS-A deploys,
content work is deploy-free); WS-C is instrumentation and truth.

---

## 3. WS-A — Core cognition (c1 serial queue, one deploy in flight)

**A1 (-85, READY — GO).** Wave semantics + npz + cost hygiene. Deploy
sequence as c1a proposed: push → deploy → migrate endpoint → T-gates.

**A2 (-86).** Deep-store physics: co_occurrence gets decay/conservation
in lockstep with deep-atlas physics and a bounded per-chi aggregate
representation (F6 preserved as reader-visible values; container
fixed). PLUS the F8 audit: enumerate every store in the persistence
set; each is classed BOUNDED-BY-PHYSICS or VIOLATION with file:line;
violations queued. Includes the events stream duplicate flood.

**A3 (-87).** Commit unlock: EMISSION_WALL_BUDGET_S 1.5 → 3.0 —
granting the 60-70 ticks the physics documents needing (F1). This is
not threshold-tuning; the threshold is untouched; the physics gets its
documented time. Evidence gates: fresh emission_dynamics with
dynamics_ticks ≥60, n_commits >0 on experience-anchored content,
converse total_ms still <45s, EMITTING duty-cycle impact measured.
Fallback if per-tick cost makes 3.0s insufficient: numpy vectorization
of the tick loop (buy ticks with speed, never with thresholds).

**A4 (-88).** Stability physics — the §8 RED mandated response. Root
cause first: what regains stab post-REST-retirement; fix must be
physics (quiet-coherence gain during IDLE/PLAYING), not a constant.

**A5 (-89).** -59 Gate 1 controlled retest: curriculum paused, -57
reverse index confirmed active, post -85 CPU headroom. If recall
<100ms clean → resume Phase 2 Days 2-3 → Phase 3 lock removal — the
fine-grained parallelism unlock (P8 full form). If it fails clean →
consumer-code fix dispatch, architecture stands.

---

## 4. WS-B — Autonomous experience engine

**B1 — Story lanes (V1 of spec §6).** Bundle schema gains place,
ambient, participants — bound in-window as lanes (E6). Small; rides
the A2 or A3 deploy.

**B2 — Experience Engine v1.** Server-side scheduler: a persistent
queue of curated bundles delivered BY THE SUBSTRATE PROCESS on her
schedule — §8 blocks honored, vitals-gated (no delivery while stab RED
unless it is a quiet-grade item), machine-rate capable, F2's
three-phase lock pattern for the delivery path. Humans out of the
loop for delivery; presence sessions overlay it. Delivery events carry
declared E-signature intent (§12) so the ledger can score every item.

**B3 — Sensory library scale-up.** Target: hundreds of story-tagged,
captioned items inside two weeks. Sources: Joe's family media (highest
E2/E6 value — faces, voices, home rooms, the cat), curated
public-domain image+sound sets for world texture, first VIDEO items
through the never-fed ATTENDING_VIDEO path. c1 ingestion tooling
extends the existing multi-upload work (batch caption+story-tag
manifest, not one-by-one UI clicks). Library size is her novelty
supply (F7) — this workstream IS the "turbo boost," delivered through
her own attending physics rather than around them.

**B4 — PLAY mechanism (design-first).** Replace the stub (F3) with
substrate-true play: foreground free-recombination reusing the daydream
walk machinery with novel-jump bias, affect coupling, and emission
triggers — exploration of what she already has, distinct from intake.
Design doc to Joe BEFORE code (§9.1 discipline: play must not become a
heuristic playground). Protected block in §8 schedule once live.

**B5 — Ambient parallel channel (post-A5).** Second concurrent input
lane (soundscape/ambient while foreground attends), copying F2's
pattern, under the single §8 health budget. Gated on lock removal;
not faked before it.

---

## 5. WS-C — Instrumentation & truth

**C1.** Loom Scan Tier 1+2 after -85 gates (anatomy + experience
layers per spec §10) — the funder-facing window and our daily one.
**C2.** Daily vitals snapshot + DAILY Experience Ledger during the
sprint (sprint cadence overrides weekly).
**C3.** Weekly grep-audit live; F8 store audit filed from A2; every
failure verbatim, first (§9.4). c1a's T1 FAIL declaration on -84 is
the protocol working and is noted as such.

---

## 6. Week map and success definition

**Week 1:** A1 lands; A2, A3 dispatched and landed; B1 schema in; B3
sourcing starts (Joe media + first public sets); C1 scan T1; daily
ledger begins. Exit: saves <10s, commits >0 reliable on anchored
content, library >100 items, scan live.
**Week 2:** A4 stability; A5 retest; B2 engine v1 live and delivering
24/7; B3 reaches hundreds incl. first videos; B4 design approved;
C1 Tier 2. Exit: engine autonomously delivering under health gates;
stab lifting in quiet blocks; signature trend lines visible.
**Week 3:** consolidation + the diff: seven clean days of engine-driven
development; before/after on all six signatures (cross-modal ratio off
1.1%, survival promotions off 63, tracked_objects off 1, commit-origin
emission rate off ~0, novel_composition off 0.0); one live recorded
session — converse + scan side by side; package: credo + telemetry +
cost curve (post -85/-86) + silicon roadmap. Joe pitches development,
not a demo.

**Success =** the signature deltas are real, reproducible, and every
step is auditable substrate physics. **The pitch =** "watch her learn,
in glass, with no ML anywhere in the path — and here is the same
architecture's silicon endpoint."

---

## 7. Pivot conditions (P9 — engineering pivots, not ambition cuts)

1. A3 at 3.0s still starves commits → vectorize tick cost (-87b); if
   still short → accelerate -59 compose migration; thresholds never
   move.
2. A4 reveals a deeper needs-physics hole → orchestrator-enforced
   quiet blocks maintain rhythm while physics is fixed properly.
3. B3 sourcing bottlenecks → escalate to Joe (his media supply and
   curation authority are the constraint).
4. A5 fails clean retest → consumer-code dispatch; Phase 2 timeline
   slips one week; B5 defers; everything else proceeds.

---

## 8. What this asks of Joe

1. GO on -85 (c1a's deploy sequence is correct).
2. Media supply for B3: family photos/videos/voices, home rooms, the
   cat — the highest-affect library tier only you can provide.
3. Titles for the six HEIC pictures (ten minutes, unblocks their story
   tags).
4. Presence sessions as overlay, starting today — the engine removes
   you as the pipe precisely so your time lands only where it is
   irreplaceable: P4 high-affect anchoring.

### Changelog
- v1.0 — 2026-07-02 (Eve): Initial version, superseding the rejected
  chat plan. Grounded in F1–F8 source findings at HEAD eabb23d.
