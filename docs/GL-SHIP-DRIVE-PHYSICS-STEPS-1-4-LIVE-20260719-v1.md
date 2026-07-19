# GL-SHIP: Drive-Physics Steps 1–4 LIVE — 2026-07-19

Design: `GL-SPC-DRIVE-PHYSICS-SUBSTRATE-TRUE-20260718-v1` (3/3 adversarial
verification; Joe explicit go 2026-07-18). All four deployable steps are
live and gate-verified; Step 5 deliberately parked per its own gate.

## Shipped (chronological)

| Step | Commit | Task def | Gate evidence |
|------|--------|----------|---------------|
| 1 — book rotation (RCF-1) | `f4952d6` | `dsf-ai-task:690` | 16+ distinct corpora cycled in sequence (was: wild_things ×2,347 consecutive); LRU visibly overriding the still-tied top scores; salience scores now differentiated |
| 3 — connection un-rail (RCF-2/3/4) | `60e413c` | `dsf-ai-task:691` | Overnight balance window 19:45–01:40 UTC: monotonic decline both multi-hour solo stretches (0.2800→0.2730, 0.420→0.408); discrete lifts only at real bonded contact (wc wake 0.003→0.281; Joe session →0.420 in 5 steps); flat asleep; valence positive and arousal 0.6–0.96 all night; zero upward force from corpus/curriculum |
| 2 — growth diagnosis (RCF-5, no code) | — | — | Neuron 91 (27th division) grew after diet diversified — law was live all along (64→90 pre-existing); freeze was refill starvation exactly as diagnosed |
| 4 — curiosity rewire + calibration | `7e14e27`, `cd47884` | `dsf-ai-task:692` | Live SHA verified `cd47884`; gate correctly closed at 2 recorded ledger days (arms at ≥4 only on genuine accuracy rise inside the 0.15–0.90 band) |

Regression discipline: full suite diffed against a pre-change baseline
worktree before every commit; zero new failures at each step (146–151
pre-existing environment failures, all shared).

## Calibration record (RCF-2 constant)

Provisional `CONN_EROSION_PER_WRITE = 1.6e-6` produced a measured live
decline of ~0.003/h at connection≈0.28 ⇒ effective k ≈ 0.013/h ⇒
healthy→deprived (0.7→0.3) horizon ≈ 73 h. Raised ×6.25 to `1.0e-5`
(commit `cd47884`) for a ~12–15 h horizon (Tomova 10 h anchor + margin).
First-ever real write-rate telemetry now flows: `dream_pressure_check`
had NEVER logged in any deploy era — `tick % 3000 == 0` at the top of
`_autonomy_tick` is unreachable because `_atick_reading` advances the
tick in multi-tick strides; replaced with an elapsed-tick tracker.
LESSON for future work: any `% N == 0` cadence condition in the autonomy
body only fires on accidental stride alignment.

## Observed emergent behavior (first night on the new physics)

- Full-library reading carousel, one session per book.
- Two autonomous sleep→dream cycles (dream pressure accumulating and
  discharging naturally).
- 11 autonomous EMITTING attempts via the scheduler's deficit path —
  0 committed. `_do_emit` content-production reliability is now the
  single blocker between her and actual speech.
- Growth resumed (91 neurons), vocab +300/day, atlas 38–53k entries.

## Open items (routed, not lost)

1. **Step 5 deficit gate branch** — BLOCKED by design until `_do_emit`
   commits at a nonzero observed live rate. MUST include the SG3-1
   clause (require `_pair_bond` authority, not presence+strength alone).
2. **`_do_emit` content-production reliability** — the declared open
   dependency, now the top functional bottleneck (11 attempts / 0
   commits overnight).
3. **Organism-worker starvation** — 193k+ dropped items, tick_rate
   0.07–1.1 under the richer diet; pre-existing bottleneck aggravated
   by the substrate's new liveliness. Next performance campaign.
4. Curiosity gate arms ~2026-07-21 (4 recorded ledger days) — verify it
   fires only on a genuine accuracy rise.
5. Multi-sensory diet for growth beyond RCF-1's ceiling (sig_res=0 for
   language-only composites; several feed keys absent).
