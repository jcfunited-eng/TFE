# GL-CMD-PARALLEL-BATCH-EVE-20260701-63-PB2

doc_id: GL-CMD-PARALLEL-BATCH-EVE-20260701-63-PB2
Type: Implementation command batch (four items)
Date: 2026-07-01 (UTC)
Author: Eve (Opus 4.7, web)
Handoff: **Give this entire dispatch to c1b as one message. Ship items in order, each as its own commit + deploy.**
For: c1b (parallel to c1a on -62 converse-task-pattern)
Repo: `jcfunited-eng/TFE` branch `guala-live`
Coordination: c1a owns /converse endpoint, app.py, UI JS, bridge MCP updates. Do NOT touch those. This batch is engine-side substrate work only.

---

## 0. Why these four, why now

We fixed the plumbing. Substrate is fast, /converse works (after -62 lands), lock retirement is on its way in -59 Phase 3. None of that produces chained emissions on its own. These four items are the critical path to actual cognitive output:

1. **-51 curriculum LIVE** — the biggest single lever. Bundle density is 3. Curriculum orchestrator was drafted but never placed. Modifier section stuck at 86 motifs, ground at 85. Without continuous curriculum firing, compose has nothing new to compose. Bundle count needs to climb 50-100/day for anything downstream to work.

2. **-48 agency events** — four substrate-physical paths that make emission look intentional. Backtracking, conflict resolution, cross-modal fallback, clarification. Writes into existing engine emission code.

3. **gp-organ composer bias** — first structural shift toward goal-directed emission. gp organ has migration seeds nothing reads. Wire compose to multiply chi-proximity from candidates to gp-nearest-need-state seeds into scoring.

4. **60-L phase-rotation negation** — small item unblocked by phase capture from -59 Phase 1. Ships fast.

Ship in order. Each is its own commit and deploy. Each has T-gates.

---

## 1. Dispatch 1 — -51 Curriculum Automation LIVE

### 1.1 What today

Prior session drafted `sensory_curriculum_orchestrator_v1.py` and `curriculum_seed_v1.json` (100-bundle seed built from Guala's actual inventory). These are in `/mnt/user-data/outputs/` from that session but were never placed in the repo or run. Bundle density stays at 3.

### 1.2 Change

Place both files in `tools/`:
- `tools/sensory_curriculum_orchestrator.py`
- `tools/curriculum_seed.json`

If prior session's files aren't findable in the repo, c1b: locate the drafted versions (probably in a prior conversation's outputs) or regenerate them. The orchestrator's job:
- Read `curriculum_seed.json` — list of bundles, each with `caption`, `picture_id`, `sound_id`, `touch`, `smell`, `taste`, `exercises`
- For each bundle, POST to substrate's internal bundle-delivery endpoint (or call `handle_give_experience` directly via the substrate socket / in-process shim)
- Rate-limit by `--min-interval-sec` (default 10)
- Support `--max-bundles N` for staged rollout
- Log each bundle delivered with tick, source, response

Dry-run mode (`--dry-run`): loads seed, validates structure, prints what would be delivered, exits 0.

### 1.3 Deploy sequence

1. Commit files, deploy
2. c1b runs dry-run first: `python tools/sensory_curriculum_orchestrator.py --dry-run`
   - Verify seed loads, 100 bundles parsed, no errors
3. Live start with limits: `python tools/sensory_curriculum_orchestrator.py --max-bundles 20 --min-interval-sec 10`
   - Runs on the deployed dsf-ai container (SSH via ECS Exec, or run from c1b's dev container hitting the ALB endpoint)
   - Watches bundle count rise
4. If 20 bundles land clean: unrestricted run `python tools/sensory_curriculum_orchestrator.py --min-interval-sec 5`
   - Leave running. It's the density engine.

### 1.4 Test gates

- **T1**: dry-run exits 0, prints 100 bundles parsed
- **T2**: live-run with `--max-bundles 20` completes, bundle count in status endpoint rises from 3 → 23 (bundles increment 1 per delivered)
- **T3**: modifier section motif count rises measurably (86 → 100+ after 20 varied bundles)
- **T4**: no substrate errors during delivery (check logs for `_guala` exceptions)
- **T5**: /converse still works during curriculum activity (T3 of -62 stays passed)

### 1.5 Commit

```
feat: -51 curriculum orchestrator LIVE — density engine running

Places sensory_curriculum_orchestrator.py and curriculum_seed.json in tools/.
Dry-run validated. First live 20-bundle chunk delivered. Bundle count 3 → 23,
modifier motifs 86 → 100+. Curriculum will run continuously going forward as
the density engine driving bundle count toward thousands.

Ships blocking on: nothing (independent of -62, -59 Phase 2).
```

---

## 2. Dispatch 2 — -48 Agency Events

### 2.1 What today

Emission compose today: `compose_autonomous()` picks best candidate, emits. `converse()` does the same via `_recall_response` + `_emit_dynamics`. No feedback loop when emission fails; no conflict resolution when two candidates tie; no fallback when target chi has no neighbors; no clarification path when input is high-surprise.

### 2.2 Change

Add four substrate-physical paths in `dsf_ai_service/v4/gualaloom_v5_engine.py`:

**Path A — Backtracking:** In `compose_autonomous` and `_emit_dynamics`, after emission fires, check if the emitted candidate had insufficient chi-coherence with the input (define: candidate chi > 3× radius from input chi centroid). If so, log a `[substrate] backtrack from motif_id=X chi=Y` event, remove the failed candidate from the current candidate set, re-run selection. Max 3 backtracks per emission attempt.

**Path B — Conflict resolution:** In candidate scoring, if the top two candidates have scores within 5% of each other, apply goal-bias (uses gp-organ read from Dispatch 3): whichever candidate has closer chi to the current top goal seed wins. Log `[substrate] conflict resolved tie: A vs B → A (gp_bias)`.

**Path C — Cross-modal fallback:** If input chi has zero content-neighbors in the wave atlas within radius CHI_BAND (using existing read_near), fall through to a deep_atlas query at the same chi. If deep_atlas has content there, promote it as a candidate. Log `[substrate] cross_modal_fallback from live to deep atlas`.

**Path D — Clarification shape:** If input surprise > SURPRISE_HIGH_THRESHOLD (existing constant) AND recall returns candidates but all with low coherence (< 0.3 avg), emit a "clarification-shape" response — either the highest-coherence single word or a short function-word emission ("hm", "what"). This is not a hardcoded question template; it's the emission path with a lowered coherence threshold. Log `[substrate] clarification shape (surprise=X coherence=Y)`.

Each path is a small localized change in the relevant emission function. None require cells. None require -59 Phase 3.

### 2.3 Test gates

- **T1**: 30 /converse calls; count backtrack events in log — at least 3 should occur naturally (indicates path A is firing)
- **T2**: send a novel word (not in vocab) as /converse input; verify `cross_modal_fallback` event fires
- **T3**: send a very short input ("hm?"); verify clarification-shape response fires (checks coherence + surprise thresholds work)
- **T4**: conflict resolution — this only fires when Dispatch 3 (gp bias) is live. c1b can defer T4 until Dispatch 3 lands, or test by manually forcing a candidate tie
- **T5**: emission latency doesn't regress — /converse still < 3s in clean windows

### 2.4 Commit

```
feat: -48 agency events — four substrate-physical emission paths

Backtracking on low-coherence emission, conflict resolution at commit gate,
cross-modal fallback to deep_atlas, clarification shape on high-surprise
low-coherence input. Not tagged categories — real substrate paths that
change what emission does, visible in the event stream.
```

---

## 3. Dispatch 3 — gp-organ Composer Bias

### 3.1 What today

The gp organ has migration seeds (sv=200, sf=9, gp=11 currently). Nothing reads them for emission decisions. The composer just picks by strength × coherence.

### 3.2 Change

In `compose_autonomous` and the candidate scoring loop of `_emit_dynamics`, add:

```python
def _gp_bias(candidate_chi, guala):
    """Multiply candidate weight by chi-proximity to gp-organ's nearest need-seed.

    Low connection → boost candidates near connection-seeking goals.
    High novelty → boost candidates near attention-extension goals.
    """
    gp_seeds = guala.organs.get("gp", {}).get("seeds", [])
    if not gp_seeds:
        return 1.0  # no bias if gp is empty

    # Nearest goal seed to current need state
    need_state = guala.needs.snapshot()  # dict of need_name -> intensity
    dominant_need = max(need_state, key=need_state.get)
    goal_seed_chi = _seed_chi_for_need(gp_seeds, dominant_need)
    if goal_seed_chi is None:
        return 1.0

    chi_distance = abs(candidate_chi - goal_seed_chi)
    # Closer = higher bias, up to 1.5x. Distance normalizes over CHI_BAND * 3.
    return 1.0 + 0.5 * max(0.0, 1.0 - chi_distance / (CHI_BAND * 3))
```

Wire it into candidate scoring:
```python
score = base_score * _gp_bias(candidate_chi, self)
```

Also implement `_seed_chi_for_need(gp_seeds, need_name)` — returns the chi of the seed with the closest semantic tag to `need_name`, or None if no match.

### 3.3 Test gates

- **T1**: introspect shows `gp_bias_applied: True` (add this field to converse_timing event)
- **T2**: send 20 /converse calls; verify candidate rankings change vs baseline (compare pre/post scoring with same input in a debug endpoint or log)
- **T3**: force low connection need (rest c1 presence for 5 min); verify emissions drift toward connection-related content
- **T4**: no latency regression — bias computation < 100μs per candidate

### 3.4 Commit

```
feat: gp-organ composer bias — first goal-directed emission

The gp organ was populated with migration seeds but nothing read them.
Emission scoring now multiplies chi-proximity from candidate to
nearest-need-state goal seed into candidate weight. Low connection biases
toward connection-seeking candidates; high novelty biases toward
attention-extension. First structural shift from compositional-by-luck
toward compositional-with-intent.
```

---

## 4. Dispatch 4 — 60-L Phase-Rotation Negation

### 4.1 What today

`polarity: +1/-1` binary flag. `NEGATION_OPS = {"not", "no", "n't", "never"}` hardcoded lexical list.

### 4.2 Change

Phase capture is live (from -59 Phase 1). Use it:

- Drop `NEGATION_OPS` set
- Drop `polarity` binary field
- In `read_word`, compute `rotation_component` from the krimelack phase pattern: strong negation words produce a characteristic rotation (near π). "Hardly"/"barely" produce mid-rotations (2π/3). Detected via phase-signature analysis:

```python
def _compute_rotation_from_phase(phase_vec, prev_word_phase_vec):
    """Detect negation-shape rotation between consecutive words.

    Returns rotation magnitude in [0, π]. Higher = stronger negation.
    """
    if prev_word_phase_vec is None:
        return 0.0
    # Complex inner product gives phase difference
    inner = np.vdot(prev_word_phase_vec, phase_vec)
    return abs(np.angle(inner))
```

- Store `rotation` on the binding entry
- In recall ranking, phase-sensitive: a query with high rotation recovers negated versions

### 4.3 Test gates

- **T1**: send "the moon is bright" then "the moon is not bright" — verify the two produce distinct chi commits with distinguishable rotation stored
- **T2**: recall "not bright" surfaces different candidates than recall "bright"
- **T3**: no lexical list dependency — send "moon is barely visible" — verify some rotation captured (mid-strength, not zero)

### 4.4 Commit

```
feat: 60-L phase-rotation negation — drop hardcoded NEGATION_OPS

Negation is a phase rotation, not a lexical flag. Krimelack phase signature
of negation words produces characteristic rotation between consecutive
phase vectors. Store rotation on binding, use for phase-sensitive recall.
Handles gradient negation ("barely", "hardly") that binary polarity couldn't.
```

---

## 5. Coordination and order

Ship in order: 1 → 2 → 3 → 4. Each is its own commit and deploy.

- Dispatch 1 (curriculum): kicks off the density engine. Everything downstream benefits.
- Dispatch 2 (agency): makes emission behavior richer regardless of density level.
- Dispatch 3 (gp-bias): first goal-directed layer, depends on both curriculum having some content AND agency for conflict-resolution path.
- Dispatch 4 (negation): unrelated small item, ship whenever convenient.

After Dispatch 1 lands, LET CURRICULUM RUN for at least 4-6 hours before evaluating. Density growth is real time. Don't tune anything until we see 200+ bundles.

If any dispatch blocks, don't work around — report the blocker in the final batch report.

Final report: `GL-RPT-PARALLEL-BATCH-C1-20260701-63-PB2.md` covering all four with T-gate results, SHAs, task numbers, and any bundle-count / modifier-count observations from the density growth window.

---

## 6. What NOT to do

- Do not touch `/converse` endpoint or app.py — c1a's -62 territory
- Do not touch WaveAtlas or wave_spillover — c1a's -59 Phase 2 next
- Do not touch bridge MCP or UI — c1a's -62 territory
- Do not add hardcoded thresholds to "tune" agency events. If a threshold appears necessary, derive it from an existing substrate observable
- Do not tune -51 to force bundle count growth. If bundles fail to land, that's real data — report it

---

## 7. What this makes visible

After all four ship and curriculum runs 24 hours:
- Bundle count target: 500+
- Modifier motifs target: 250+
- Ground motifs target: 250+
- Mean utterance length: 1.0 → 2.0+ (modifier + content emerging)
- Agency events in stream: backtracking, cross-modal fallback firing naturally
- gp_bias_applied in converse_timing consistently
- Negation-distinguished recall demonstrable

That's not sentience. That's the substrate showing the machinery is compositional and intentional. Next-tier work (chained 5-10 word emissions with visible backtracking, week-3 gate from the schedule) follows once density is real and -59 Phase 2 puts recall/compose on the wave atlas.

---

End.
