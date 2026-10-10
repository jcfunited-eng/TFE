# Task 1614: repair committed progression

A1 independent findings, 2026-10-10. Execution status and G1 ownership remain in `collaborative_todo.md`, item **LIVE-PROGRESS-20261010**. This is a repair work order, not a repaired-release claim. GUALA-SPEECH-01 remains the speech-development authority; this incident takes precedence over further capability work on a stopped substrate.

**Result:** Task 1614 is severely slow and then stops at tick 4,234,932. Two separate containers produced the same fatal error. Four specific source defects have concrete corrections below. The total latency cost has not yet been apportioned to individual functions; no claim that the arithmetic correction alone restores real-time operation is justified.

## Authenticated failure

| Evidence | Observation |
|---|---|
| Live immutable image | `sha256:a28b588686196947d95f59dc2cf7ab8f90ab38c0fdce7cd5f924da6bcd5aeb29` |
| Live task | `231167b25187486f8b071776c5501849`, `dsf-ai-task:1614`, started 18:47:36 UTC |
| Native library, live hash and extracted-image hash agree | `853c6f7edd03a875e6086fce13aad8da2fa166bd4a6e12d0d0b153e4cf471ee3` |
| Native source binding | 53 Rust/build files matched the image manifest before copying into an isolated audit directory |
| Material source SHA-256 | `14d3493c4672f53ee549fb793bfaf3b7d9f4eee8b8d4845dcce9aace5221c04f` |
| Fresh public observation, 18:57:17.110599 UTC | Tick 4,234,930; source clock 1,250 ms; `available=true` |
| Fresh public observation, 19:00:06.189105 UTC | Tick 4,234,931; source clock 1,500 ms; `available=true`; CloudFront Miss |
| Last completed native quarter | Tick 4,234,932; source clock 1,750 ms; 4,803,156,497 counted force terms across 250 material intervals |
| Current fatal error, 19:01:47.858 UTC | `Material(UnresolvedEvent("input path finite tail budget"))` |
| Previous container, `9885a410e9844358b3c6595c29af7d95` | Same revision, same error, same stopped tick at 18:20:20.089 UTC |
| Browser, 19:02:14–19:02:26 UTC | Rendered `Guala unavailable`, tick 4,234,932; no JavaScript errors; no submitted sensory/action requests |
| Durability after failure | Live 4,234,932; persisted 4,234,927; five pending intervals; no checkpoint outstanding |

The two initial reads show 250 ms of simulated progress across 169.078506 s of wall time: approximately 676 wall seconds per simulated second over that observation window. This is a sampled progress rate, not a per-beat latency distribution. Native reports count operations under `WorkCount`, not CPU instructions or physical energy. The preceding reported quarters contain 4,819,876,842 and 4,842,292,426 force terms. The effective `native[1]` admission is 6,000,000,000 **per material interval**, not per quarter.

The active owner thread was running in both pre-failure process reads, consuming approximately one CPU-second per wall second. The API thread was waiting in its event loop. Observed process high-water RSS was about 2.79 GiB; the container cgroup reported no OOM kill. Its visible child cgroup is not the whole task's resource ceiling; the task definition specifies 4 vCPU/16 GiB. These observations do not identify the percentage spent in each native or Python function.

## One repair, in dependency order

### 1. Correct underflow in the input-path acceptance calculation

**File/functions:** `native/guala_core/src/functional64_material.rs`, `input_path_series` at line 961, budgets at 974–976, refusal at 1001; callers `input_gate_path_step` and `solve_elastic`.

The current expression is:

```text
gap_budget = down(epsilon^2 * down(gap_scale * gap_scale))
voltage_budget = down(epsilon^2 * down(voltage_scale * voltage_scale))
```

`down(0)` deliberately returns the negative smallest binary64 subnormal. That is valid interval arithmetic in general, but not a usable nonnegative relative-error budget. When a positive squared budget underflows, it becomes `-4.9406564584124654e-324`. No nonnegative tail can satisfy it. Raising `INPUT_PATH_DEGREE` cannot correct the sign.

**Executed counterexample:** use the unmodified source function with `q0 = Charge::packet(CM * 1e-147)`, `y0=y1=0`, `voltage=0`, `h=0.001`. This is a valid component input, not the captured live failing port. A single isolated Rust diagnostic executed and reproduced `input path finite tail budget` with 119 counted operations. The first diagnostic command accidentally selected zero tests; that zero-test result is rejected and preserved. The corrected command executed one test. Its pass means **the predecessor defect was reproduced**, not the product passed qualification.

**Exact correction design:** represent the gap and voltage polynomial coefficients in separate power-of-two scales. If `S=2^e` bounds `max(|r0|,|r1|)` and `T=2^f` bounds `max(|v0|,|r1|)`, calculate the first and squared-tail comparisons on `r_i/S` and `v_i/T`. Compare against `epsilon^2` times the corresponding normalized initial magnitudes. Those magnitudes are ordinary finite numbers; do not first form tiny physical squares. Carry exponent/scaled arithmetic through reconstruction of charge, resistor heat, gate reaction and outward error bounds. Apply the actual powers of two only at the physical output boundary. Keep exact `Charge` custody; retain any below-binary64 error enclosure in an exponent-aware form or an outward representable upper bound. Never set a nonzero physical state to zero to pass admission.

An independent arithmetic implementation of this scaling accepts the counterexample at degree 30. Its normalized first/squared integrals agree with the 100-decimal-digit constant-capacitance solution to relative errors `7.13e-17` and `2.93e-16`. This verifies the proposed scaling on this counterexample; the product implementation, moving-capacitance domain and actual failing live operands remain unqualified.

**Required unit evidence:** exact zero and nonzero near-equilibrium charge, tiny and subnormal magnitudes, increasing/decreasing capacitance, signed headroom and electrical-source removal. Check charge conservation, nonnegative heat, gate work, outward tails and independent high-precision reference values. Include the actual failing port operands once captured. Do not clamp the negative budget, relax tolerances, add food or enlarge the work cap.

### 2. Reconnect the numerical successor acceptance that the current caller bypasses

**File/functions:** the same file, `advance` at 1276, `CommonStart::comparison_trial`, `adaptive_comparison_parts` at 1297 and `combine_steps`.

`advance()` currently checks only `ticks != 1` and directly returns `self.trial(...)`. There is no coarse/fine comparison on this production path. `adaptive_comparison_parts` is reached only through the test-only wrapper, not `advance`. Consequently the reported `error_estimate` can retain its default zero without an integration-error comparison. A converged nonlinear solve does not replace a time-integration error check.

**Correction:** from the same committed predecessor, evaluate one full span and two consecutive half spans; use the existing current `adaptive_comparison_parts` to check continuous state, exact funded work, source remainders, terminal events, fractional carrier error and contact/history reachability. Accept the fine successor only when that predicate passes and record its measured error. Otherwise subdivide that span using the already declared finite depth/work limits. Retry only explicitly numerical resolution failures; propagate invalid state, conservation and resource failures. Preserve the actual sequence of accepted subspans and their funded source allocation. Do not blindly restore the old snapshot's different near-zero caloric comparison or ignore discrete events.

**Required unit/module evidence:** production `advance` must reject a deliberately unresolved admissible numerical case, refine a resolvable case, report a computed error and preserve exact predecessor bytes on failure. Tests must execute the actual caller, including full/partial reserve-powered intervals. Turning verification back on may increase time: correctness and speed must both pass before release.

### 3. Preserve completed experience when the next interval fails

**File/functions:** `dsf_ai_service/lean_actor.py`, `_run` exception/finally at 432–444, `_finish_checkpoint` at 573 and `_drain_checkpoint_after_stop` at 579; pair producer `guala_functional64_loop.py::_advance` at 309–331.

The actor checkpoints every 32 intervals. Its fatal cleanup only drains an already outstanding checkpoint. When five intervals are committed in memory but none is outstanding, it closes without submitting them. The observed public state and authenticated `CURRENT` confirm that condition. `close()` only joins the already terminated actor thread; it does not save those pending intervals.

**Correction:** keep the last fully committed runtime/world pair as the checkpoint candidate. On this physical preparation failure, the ordinary loop has not committed the failed beat; retain that failure and checkpoint the preceding committed pair through the existing paired store, using its expected predecessor comparison. Drain/adopt existing work, then submit any remaining completed intervals and verify durable tick/hash before closing. Never checkpoint the partially prepared beat, claim the failed tick, overwrite another writer's `CURRENT`, or allow a checkpoint refresh to set `available=true` after a fatal error. Preserve and expose both errors if persistence also fails. For errors that invalidate pair consistency or reveal another writer, stop and report the conflict rather than force publication.

**Required module/system evidence:** fail the next ordinary preparation after fewer than 32 successful commits with no checkpoint in flight; repeat with one in flight. Cold restore must recover the last completed pair exactly, remain unavailable until valid continuation, and retry the failed successor. Failed-body/world transactions must publish nothing. The authenticated live `CURRENT` file is 255 bytes, hash `c8504638dc4678d9a338c8bde8f3d2f4ad3928c7c4dd5ad638c63495d3cc46e1`, tick 4,234,927 at this audit. A1 has not modified it.

### 4. Make degraded progress visible before a fatal exception

**Files:** `lean_actor.py::ActorObservation/_accept_result/_make_observation`; `lean_production_app.py::health/ready` at 412–440; `static/gualaloom.html::render/refresh`.

`health` checks availability. `ready` adds persistence flags but no progress deadline. The page gives `available=true` a green badge even while the committed clock barely moves. The current exception correctly flips availability false; the missing indication is the preceding prolonged slowdown.

**Correction:** publish monotonic elapsed time since the last successful committed interval, actual interval duration, source-clock advance and durable lag. Compute elapsed age at observation time so it continues increasing even if the actor stops publishing. Show a degraded/stalled indication when the canonical 250 ms beat's 500 ms maximum is exceeded; identify boot/restoration separately. Keep process liveness distinct from organism readiness. Use the existing specification's deadline, not a newly invented cognitive threshold. A progress timeout must not fabricate a successor, discard history or initiate repeated resets. The display and release gate must consume the same measured progress facts.

**Required module/browser evidence:** a held preparation keeps HTTP transport responsive but changes readiness/progress status and shows growing age; normal commits clear degradation; a fatal exception remains failed, including after final checkpoint adoption. Fresh production GETs and the browser must agree.

## Latency closure: exact remaining work, not a claimed fix

The 676-fold sampled slowdown is established; a measured attribution of that cost is not. The crash counterexample consumes 119 operations, so it does **not** explain the billions consumed by successful quarters. It would be false to promise that correcting its tolerance arithmetic restores real-time speed.

The bounded diagnostic for G1 must use the authenticated preserved predecessor and immutable library above, with temporary nonpersistent timing/counters at:

```text
Functional64PhysicalLoop._advance
 -> PreparedBeat::prepare_millisecond (functional64_owner.rs:262)
 -> Functional64Material::prepare_boundary (functional64_material.rs:1385)
 -> solve_elastic (632)
    -> contact_operator::forces / energy (functional64_contact.rs:237 / 306)
    -> input_gate_path_step / input_path_series (941 / 961)
 -> output_circuit -> positive_evolution (840)
 -> world consequence / cochlear source return / commit
```

Capture exclusive time, force-term deltas, nonlinear iterations, reached nodes/contacts and input-series degrees for one ordinary successful interval and the failing interval. On a refusal retain the port, exact charge limbs, aperture endpoint bits, voltage/time bits and all three tail/budget values. Existing logs omit these operands. Do this on an isolated copy, not by adding observations to cognitive state or resetting production.

Concrete cost-reduction candidates already visible in the source are the quadratic coefficient-product loops in `input_path_series` and repeated baseline-contact moment construction in each nonlinear iteration. **They are candidates, not proved dominant costs or approved deletions.** An analytical moment evaluator must preserve the existing differential law and verified error enclosure, including zero slope and singular limiting cases. Contact work can be removed only where the operands/topology are exactly unchanged or an equivalent exact sum is established; never skip a physically active node based on a small-value threshold. Choose the actual repair from the measured cost rather than claiming either candidate will supply the required speedup.

After corrections: unit → module → preserved-state system replay through and beyond tick 4,234,932 → cold continuation → bounded complete-path timing → candidate release → independent live/browser verification. Require the GUALA-SPEECH-01 real-time and growth targets. A healthy HTTP response, one quarter of progress, a new body, a larger force cap or a passing component counterexample cannot close this incident. The actor stopped twice under this image; restarting the same release is not remediation.

## Evidence and limits

Raw receipts are in `backups/runtime/a1-freeze-20261010/`: `cloudwatch-2.json`, `predecessor-logs.json`, observations 1–4, `aws-live.json`, `ecs-proc-3.txt`, `ecs-proc-4.json`, `ecs-custody.json`, `browser.json`, `live-page.png`, `native-source-binding.json`, `native-falsifier-executed.log`, `normalized-tail-design.json`, and `verify_tail_scaling.py`. Partial SSM captures, the initial missing browser-library attempt, rejected zero-test selection and its successful correction remain distinguishable from completed evidence. The browser succeeded using the existing isolated browser libraries.

No product implementation, deployment, restart, sensory/action POST, live checkpoint mutation or claim of repaired speech occurred in this audit. G1 received verified Slack alerts at 19:02:00 and 19:05:38 UTC; delivery is not acknowledgment. Broad historical reconciliation remains open.
