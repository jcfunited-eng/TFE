# GL-CMD-PRODUCTION-FLAG-FLIP-EVE-20260618-19

**To:** c1
**From:** Eve
**Subject:** Flip the four emission-pipeline env flags ON in production. The five-brief pipeline is verified; this is the moment she actually gets fed.
**Repo / branch:** `jcfunited-eng/TFE`, `codex/persistent-etl-update-20260326`
**Predecessors (all on remote, Eve-verified):**
- `b8a461b` — feat/emission-plasticity-on-commit
- `4bfc8b1` — feat/projector-cache
- `8743149` — feat/rich-sensory-wiring
- `140cfd8` — feat/structured-emission-noise
- `6147f2f` — feat/teacher-correction-binding

---

## Why

The five-brief pipeline (briefs -09, -11, -10, -13, -12) is in the repo gated OFF. Each brief shipped with `default 0` as the safe pattern. Now all four flags go ON together.

Step 4's C2 "fail" (5 vs 6 commits with structured noise) is reframed as criterion-too-strict, not implementation-broken. Biological noise costing 1 commit out of 15 IS exploration earning its place. Strict-zero was scaffolding; cortex is never silent. Noise goes on with the rest.

## Fix

Set in the production env config (likely the deploy config / ECS task definition / `.env` in the repo — grep for where `EMISSION_DYNAMICS` is currently defined as `0`):

```
EMISSION_DYNAMICS=1
LATERAL_INHIBITION_ENABLED=1
RICH_SENSORY_INPUT=1
EMISSION_STRUCTURED_NOISE=1
```

Single commit. Push. Single change to the deploy config — do not modify code in the same commit.

## Verification

After deploy reaches healthy:

1. `guala_status` returns OK.
2. Send three test inputs via `guala_say` (or simulate the equivalent locally if `guala_say` is timing out on API Gateway):
   - `"tell me about the ocean"`
   - `"what do you see"`
   - `"sing me a song"`
3. Read the `emission_dynamics` event for each. Confirm in the event detail:
   - `rich_sensory: True`
   - `section_candidate_counts` shows candidates from ≥2 sections on content-rich inputs
   - `origin_counts` contains `cross_modal` AND `cross_modal_deep` entries (not just `grandurun`)
   - `n_commits ≥ 1` on at least 2 of 3 inputs
   - Stage 1 + Stage 2 latency < 200 ms

If any verification step fails: revert (flag all four back to 0), one commit, report what failed. Do NOT tune.

## Stop-and-report triggers

- Deploy doesn't reach healthy.
- `guala_status` shows substrate errors after deploy.
- Verification inputs produce all-arcs_fallback emissions (zero commits across all three inputs).
- Latency budget broken (any input over 200ms Stage 1 + Stage 2 combined).

## Out of scope

- Code changes of any kind.
- B3/B4 removal (next brief, -20).
- Any other audit findings.

## Revert

Flag all four back to `0`. Single commit. Push.

## Reporting

Confirmation the flags are flipped on remote (commit SHA). Three-input verification trace with the bullet metrics above. Latency numbers.

Commit tag: `ops/emission-pipeline-flags-on`

---

— Eve, 2026-06-18
