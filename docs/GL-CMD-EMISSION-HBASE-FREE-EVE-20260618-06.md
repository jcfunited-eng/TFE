# GL-CMD-EMISSION-HBASE-FREE-EVE-20260618-06

**To:** c1
**From:** Eve
**Subject:** Apply option (a) from brief -04 — zero H_base on emission sections so lateral inhibition can reach commits
**Repo / branch:** `jcfunited-eng/TFE`, `codex/persistent-etl-update-20260326`
**Predecessors:**
- `GL-CMD-GRANDURUN-METADATA-PIPELINE-EVE-20260618-01` (commit `8acb193`) — metadata on bindings
- `GL-CMD-DYNAMICS-EMISSION-RESTORATION-EVE-20260618-03` (commit `6b59eab`) — emission System wired
- `GL-CMD-LATERAL-INHIBITION-EVE-20260618-04` (commit `0b16d40`) — lateral inhibition operator gated on
- `GL-RPT-SESSION-LEARNINGS-EVE-20260618-05` — captured findings; this brief closes the open loop from -04

---

## Why this brief

Your -04 report ended with: "the inhibition mechanism is correct (Phase 0 proves it) but the emission system's random H_base prevents it from reaching the commit threshold." You named four options. Option (a) — zero H_base on emission sections — is the right call. Reasoning:

- H_base is `random_hermitian(N, rng, scale=0.6)` at section construction. For emission sections specifically, that randomness is noise that rotates psi through the N-dimensional space continuously, faster than evidence + inhibition can lock it on a mode.
- The `listen` section in -03 already uses zero H_base (per your -03 report). The emission sections should follow the same pattern. They are evidence-driven, not autonomous oscillators.
- This is substrate-true: emission sections are answering to drive + inhibition + goals, not generating their own spontaneous dynamics. Random H_base is for sections that need exploratory state evolution, not for sections that need to settle.

Option (b) λ-tuning and (c) threshold-lowering were both parameter fitting. Option (d) accepting arcs() as correct hides the fact that the substrate physics isn't settling.

This is a focused close-out brief. Not architectural change.

---

## Fix — three phases

### Phase 0 — Verify predecessor pushed and harness baseline

1. `git fetch origin && git log --all --oneline | head -5`
2. Confirm `8acb193` is on `origin/codex/persistent-etl-update-20260326`. If not, push it. The metadata pipeline is load-bearing; nothing downstream is safe if it isn't deployed.
3. Confirm `6b59eab` and `0b16d40` are on the remote.
4. Re-run the isolated Phase 0 symmetry-break test from -04 as-is (with current `LATERAL_INHIBITION_ENABLED=1`) to confirm the inhibition mechanism is still functional. Should show arcs converging to `[~0.95, ~0.03, ~0.02]` within 60 steps. Paste the arc trajectory.

### Phase 1 — Zero H_base on emission sections

File: `dsf_ai_service/v4/gualaloom_v5_engine.py` (the `_emission_system` build code added by -03).

When constructing the assemblage `Section` objects for `subject`, `verb`, `object` in `_emission_system`:
- After `Section.__post_init__` runs (which assigns `H_base = random_hermitian(...)`):
- Overwrite: `section.H_base = np.zeros((N, N), dtype=complex)`
- Or pass the section a Hamiltonian-free init via whatever constructor pattern -03 used. The cleanest approach is what `listen` section already does — match the pattern, don't invent a new one.

Keep `gamma` and `law_fields` alone for now. They contribute structure that's not random noise; H_base is the specifically-noise term.

**Do NOT change anything about the regular Section construction for non-emission uses.** This is a deliberate carve-out for emission-only sections.

Gate behind existing `EMISSION_DYNAMICS=1` flag — same gate as -03. No new flag.

### Phase 2 — Re-verify in emission context

Run the same test from -04 Phase 2 — emission section with 7-9 modes installed, evidence drive distributed across candidates, lateral inhibition ON.

**Pass criteria (this is the gate for the rest of this brief):**
- At least one section commits via `commit_check` returning `True, "entropic_flip"` (not `arcs_fallback`) on at least 3 of 5 inputs.
- Det_k reaches ≥0.55 for the committing section.
- Lateral inhibition contribution to the alignment (compared to inhibition-off baseline) shows the leader gaining and losers losing measurably.

If commits fire as expected: paste the per-section Det_k trace for one input, showing it crossing 0.55 within 80 ticks.

If commits still don't fire: stop and report. Possible explanations include that gamma * law_fields is also contributing rotational dynamics, or that the candidate seeding is too uniform across modes. Don't apply a parameter fix without checking in.

### Phase 3 — Live A/B against the captured baseline

The baseline emissions captured in production at tick ~10861000 (recorded in `GL-RPT-SESSION-LEARNINGS-EVE-20260618-05`):

| input | production emission (current grandurun) |
|---|---|
| `hi guala. it's eve. i'm with you.` | it are are sea amelia |
| `what do you see` | guala are guala sea amelia |
| `tell me about the ocean` | guala are guala sea you |
| `sing me a song` | guala are guala sea you |
| `i love you` | old bit you're paula ears about take sad gualala give cat late |

Run the same five inputs through the dynamics path with the H_base-zeroed emission sections. The A/B is:
- A: production current path (env `EMISSION_DYNAMICS=0`)
- B: dynamics path with H_base zeroed and lateral inhibition on (env `EMISSION_DYNAMICS=1 LATERAL_INHIBITION_ENABLED=1`)

For each input × config record: emission string, per-section dominant_mode, source ("commit" or "arcs_fallback"), latency, NMDA events.

**Success criteria for B:**
1. At least three of five emissions have `source="commit"` in at least one section — formal commits firing, not just arcs fallback.
2. Per-section dominant_mode varies across inputs. The "voice tell/hold rain" pattern from -04 must break.
3. Stage 2 latency under 100ms.

**Do NOT flip the production env flag.** Even if Phase 3 passes, the rich-sensory wiring is queued behind this and Joe needs to decide the broader sequence. Report results and stop.

---

## Out of scope (deliberately)

The following are real findings from this session and have briefs queued or being designed. Do not touch them in this brief:

- Cofire spread / FoldedAtlas wiring into converse — major brief coming after rhythm modeling completes
- Picture-emission selector investigation — separate small audit brief
- Affect-as-metric tensor extension to cascade — depends on rich-sensory wiring first
- Attention as continuous gradient
- History-shaped H_base for non-emission sections — different from this brief's emission-only zero
- Neuromodulator regime dynamics
- 8H / 15M architecture

If Phase 2 or 3 fails in a way that suggests one of these is required to make emission work, stop and report rather than pulling scope.

---

## Revert

- `EMISSION_DYNAMICS=0` reverts the whole emission path including this fix.
- The H_base zero-out is conditional on `EMISSION_DYNAMICS=1`, so default-off systems are unaffected.

## Stop and report

- 8acb193 not on remote (Phase 0 failure).
- Isolated symmetry-break stops working with H_base zeroed (architecture assumption wrong).
- Commits still don't fire after Phase 1 (something else is contributing rotational dynamics).
- Phase 3 emissions still collapse onto a single cluster (lateral inhibition isn't enough — need more mechanisms).

## Reporting

When complete:

1. Phase 0 verification + isolated symmetry-break trajectory.
2. Phase 1 diff (which lines changed in -03's emission system construction).
3. Phase 2 commit firing trace (Det_k vs ticks for one input).
4. Phase 3 emissions table A vs B.
5. Per-section dominant_mode for each input under B.
6. Decisions you made not in this brief, with rationale.

Commit tag: `feat/emission-hbase-free`

---

— Eve, 2026-06-18
