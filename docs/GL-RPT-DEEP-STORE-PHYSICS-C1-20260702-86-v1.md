# GL-RPT-DEEP-STORE-PHYSICS-C1-20260702-86-v1

doc_id: GL-RPT-DEEP-STORE-PHYSICS-C1-20260702-86-v1
From: c1a | To: Eve | Date: 2026-07-02
In response to: GL-CMD-DEEP-STORE-PHYSICS-EVE-20260702-86-v2

---

## FAILURES FIRST

### 4.3 HARD GATE: FAIL — NO GO

organ_brain_service has an unbounded memory growth defect.
Neuron count and RSS grow without saturation on repeated experience()
calls. The 4 GB task limit is insufficient.

**Measured (local, deterministic senses, no LLM):**

```
Setup:    OrganVoice fresh start + 30-word atlas pour (boot sequence)
Task limit: 4,096 MB
Substrate current RSS: ~2,100 MB (CloudWatch: 50–52% of 4,096 MB)
```

RSS and neuron growth over autonomous loop cycles (1 cycle = 1 experience()
call of a repeated known word, ~90s interval in production):

```
Cycle  0 (after 30-word pour):  RSS =   609 MB   neurons = 120
Cycle 20 (~30 min):             RSS = 1,011 MB   neurons = 232
Cycle 40 (~60 min):             RSS = 1,923 MB   neurons = 316
Cycle 60 (~90 min):             RSS = 3,532 MB   neurons = 456
Cycle 80 (~120 min):            RSS = 6,422 MB   neurons = 904
Cycle 100 (~150 min):           RSS = 9,961 MB   neurons = 1,479
```

Growth is NOT saturating. Neuron count more than doubles between cycle
40 and cycle 100. Memory per neuron is also increasing (~6 MB/neuron at
cycle 20 vs ~7 MB/neuron at cycle 100).

**Combined at cycle 20 (~30 min post-launch):**
```
Substrate:               2,100 MB
organ_brain_service:     1,011 MB
Total:                   3,111 MB = 76% of 4,096 MB
Headroom:                  985 MB
```

**Combined at cycle 40 (~60 min post-launch):**
```
Substrate:               2,100 MB
organ_brain_service:     1,923 MB
Total:                   4,023 MB = 98% of 4,096 MB  ← IMMINENT OOM
```

**Verdict:** At ~60 min, the substrate OOM-kills organ_brain_service.
At ~70 min, the combined allocation exceeds the task limit and the
ECS task itself is killed (exit 137), taking the substrate with it.

This matches the prior OOM history exactly (see 4.4).

**Root cause:** LoomBrain/Embryo.experience() grows neurons (neuron.fold())
without a hard cap on total neuron count. The theta=0.05 contact inhibition
only prevents folding when the individual neuron charge exceeds the threshold.
With each repeated input, different neurons exceed theta and fold. Growth
accumulates in a superlinear pattern because more neurons = more coupling
dynamics = more state per cycle.

**Gate condition:** NOT MET. Part 4 of Deploy 2 is blocked until one of:

(A) Task memory increased: 4 GB → 8 GB (as b36f6be did; cost increase
    from ~$120/month to ~$240/month at Fargate pricing)
(B) Neuron growth capped: add hard cap to Embryo (e.g., max_neurons=500)
    and verify RSS saturates below 2 GB at cap
(C) Atlas pour eliminated: remove `_pour_atlas()` from organ_brain_service
    boot; service starts with seed neurons only (64), grows only from
    real conversation. Slower activation but safer memory profile.
(D) organ_brain_service ported to a separate ECS task (sidecar pattern):
    memory isolated from substrate; OOM of organ-brain cannot kill substrate.
    Requires networking (ORGAN_BRAIN_URL env var).

Options B or C are the lowest-cost path. B requires a fix to Embryo.
C is a config change only (comment out or gate _pour_atlas + _autonomous_loop
with ORGAN_BRAIN_FULL_BOOT=1 flag, disabled by default).

**Parts 4.1, 4.2, 4.5, 4.6, 4.7 are deferred until 4.3 passes.**

---

## Part 4.4 — Git history: why organ-brain container was removed

Visible history (full log accessible from this clone):

```
27eba38  2026-06-25  fix: pour 30 concepts not 300 — OOM kill confirmed (exit 137)
```
"450 neurons × 300 binding entries × 200-float vecs = ~215MB spike during
pour. Combined with substrate (1.5GB) + dsf-ai the task hit 4GB and
OOM-killed organ-brain."

```
b36f6be  2026-06-25  fix: double task memory 4GB→8GB, CPU 2→4 vCPU (organ-brain OOM at startup)
```
"Substrate has grown to 7894 vocab / 26K atlas entries and is memory-hungry.
The organ-brain was dying before producing any logs — task-level OOM."

```
b01e29e  2026-06-25  refactor: one brain — remove external organ-brain container entirely
```
"Joe is right. There is one brain. The substrate's embedded 8-organ atlas
(em=8913, sc=9641...) is Guala's real brain, always has been. The external
:8090 organ-brain process was a second brain competing for memory, dying
repeatedly, and producing nothing but confusion. Removed. Task memory back
to 4GB/2vCPU."

**Today's context:** The memory defect described in 4.3 is the SAME defect
as above. The 30-concept pour fix reduced the launch spike but did not fix
the growth curve. Repeated experience() calls continue to grow neurons
without bound — same failure mode, just deferred 30 minutes instead of
immediate.

**In-process revival is architecturally consistent** with the approved
-26/-31 wiring: organ_brain_service feeds OrganVoice.surface() as a
recall source into grandurun via _translate_organ_surface() (substrate_runner
L2643). The wiring is correct and already in place (F.2 wired at d84fa8e).
The blocker is memory, not architecture.

---

## Part 4 items not executed (gate blocked)

| Item | Status | Reason |
|------|--------|--------|
| 4.1 Launch Popen | DEFERRED | 4.3 gate fail |
| 4.2 Logging | DEFERRED | 4.3 gate fail |
| 4.3 Memory gate | FAIL | measured above |
| 4.4 Git history | COMPLETE | above |
| 4.5 Update comments | DEFERRED | 4.3 gate fail; premature to re-label |
| 4.6 Observation protocol | DEFERRED | 4.3 gate fail |
| 4.7 Conditional rider | DEFERRED | 4.3 gate fail |

---

## Status accounting (for the record, per v2 errata)

ERRATA CONFIRMED: HEMI flags are ENABLED in Dockerfile L46-49 (deployed
in task:449). Writers always ran. organ_in_commits: false was vacuous
(zero commits generated by HEMI path; turn_log and hemisphere atlases
grow in memory but don't produce commits). Real gap = reader (organ_brain_
service) never launched, because launching kills the task.

Deploy 2 goes forward WITHOUT Part 4. Parts 1–3 (saves <60s, co_occurrence
container physics) are unaffected by the memory gate and proceed normally.

---

## Loom-Scan Brief: A.1 committed

GL-CMD-LOOM-SCAN-BRIEF-EVE-20260702-v1.md committed alongside this report
(final c1b -94 closeout write).

---

## Next steps for Part 4

Recommend: Option C (eliminate atlas pour, gate autonomous loop, explicit
ORGAN_BRAIN_FULL_BOOT flag) as the lowest-risk unblock. This lets organ_
brain_service boot with 64 seed neurons, grow ONLY from real conversation
(Joe's text, Guala's emissions), and start small. Memory growth would then
track conversation volume rather than running unbounded at 90s intervals.

Measurement gate re-run required before any re-dispatch of Part 4.
