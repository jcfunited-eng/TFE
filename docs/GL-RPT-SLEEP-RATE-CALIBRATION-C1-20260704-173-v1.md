# GL-RPT-SLEEP-RATE-CALIBRATION-C1-20260704-173-v1

doc_id: GL-RPT-SLEEP-RATE-CALIBRATION-C1-20260704-173-v1
From: c1b | Responds to: GL-CMD-SLEEP-RATE-CALIBRATION-EVE-20260704-
173-v1. D1 (re-derive the rate from fresh live measurement) done,
D2 (one dial) shipped, D3 (deploy with c1a's retention SHA) staged —
awaiting c1a's brain+voice SHA to open the single combined window.

---

## D1 — the measurement (verify before coding, per the CMD's own law)

**Method:** `dream_pressure_check` fires every 3000 ticks
(`gualaloom_v5_engine.py:4305`, unchanged) and already logs `dp`,
`dp_rate`, `write_delta`, `activity`, `pair_bond`, `attending` — read
directly from the live in-memory event stream via `guala_get_events`,
no new instrumentation needed.

**Readings, this session, live:**

| tick | dp | activity | pair_bond | write_delta |
|---|---|---|---|---|
| 14724000 | 0.1035 | ATTENDING_VISUAL | true | 0 |
| 14727000 | 0.106 | ATTENDING_VISUAL | false | 0 |
| 14730000 | 0.109 | ATTENDING_VISUAL | false | 0 |
| 14733000 | 0.112 | ATTENDING_VISUAL | false | 0 |
| 14736000 | 0.115 | ATTENDING_VISUAL | false | 0 |
| 14739000 | 0.118 | ATTENDING_VISUAL | false | 0 |

Readings 2-6 (5 consecutive) are under **identical conditions**
(non-pair-bonded, attending, zero atlas writes — she spent this
entire window re-attending one over-familiar picture, generating no
new atlas entries) and give **5 consecutive identical deltas of
exactly 0.003 dp / 3000 ticks** — as clean a real-world measurement
as this system is going to produce. This equals `dp_rate=0.000001`/tick
exactly, matching `DP_RATE_PER_ATTEND_TICK` (`:480`) directly:
`write_delta=0` correctly zeroes the read term, `pair_bond=false`
correctly skips the 0.3x push-through discount — the formula is doing
exactly what it's documented to do.

**Tick-rate anchor** (for converting ticks to wall-clock hours),
two precise `persistence_health.last_save_timestamp` reads, not
assumed: tick 14701135 @ 2026-07-04T12:43:26Z → tick 14740355 @
2026-07-04T15:28:59Z = 39220 ticks / 9933s = **3.949 ticks/sec**.
Reading span (tick 14724000→14739000) = 15000 ticks ÷ 3.949 =
**63.3 minutes** — clears the CMD's ≥1h bar.

**The arithmetic (G-1):**
- Unscaled measured rate: 0.000001 dp/tick × 3.949 × 3600 =
  **0.0142 dp/hour** → 0.7 / 0.0142 ≈ **49.3 hours** to threshold.
  (Consistent in order of magnitude with Eve's own 3-sample estimate
  in the CMD, ~80h — both confirm the same diagnosis: the current
  rate cannot reach 0.7 within any real waking window.)
- Target (midpoint of the CMD's stated 5-6h range): 0.7 / 5.5h =
  **0.1273 dp/hour** needed.
- **Multiplier = 0.1273 / 0.0142 ≈ 8.96 → 9.0×**.
  Check: 0.7 / (9.0 × 0.0142) = **5.48 hours** — inside the 5-6h
  target band.

**Honest caveat on the measurement's activity mix:** the entire
reading window happened to fall inside a zero-novelty stretch (same
picture, `write_delta=0` throughout) — this is close to a *floor*
rate, not an inflated one. Any real day with varied attention (new
pictures/sounds/corpus reading, generating atlas writes) or less
pair-bond time will accumulate pressure *faster* than what was
measured here. So 9× is, if anything, mildly conservative against
the over-sleep failure mode (G-3's own named pendulum-watch concern),
not aggressive toward it.

---

## D2 — one dial, shipped

`DP_RATE_MULTIPLIER = 9.0`, `gualaloom_v5_engine.py:485-500` (new
constant, full derivation in its own comment), applied at the single
accumulation site `:4313-4314`:
```python
_dp_rate = (_write_delta * DP_RATE_PER_READ
            + (DP_RATE_PER_ATTEND_TICK if _attending else 0.0)) * DP_RATE_MULTIPLIER
if _pair_bond_active:
    _dp_rate *= 0.3
```
Diff is two hunks, 18 lines, one file (`git diff --stat`). Confirmed
untouched: the dial-1 novelty floor, the `_SLEEP_THRESHOLD = 0.7` soft
threshold, `DP_OVERRIDE_CEILING = 1.0`, `DP_DISCHARGE_PER_DREAM_TICK`,
the pair-bond push-through discount's own 0.3 factor. File compiles
clean (`python3 -m py_compile`).

---

## D3 — deploy staging

Ready to ship in the same window as c1a's already-reviewed retention
build (`f43ca10`, `GL-CMD-EVENT-RETENTION-FIX-172`). As of this
report, c1a's brain+voice build (per `GL-CMD-BRAIN-FULL-DEPLOY-TODAY-
EVE-20260704-175-v2`) has not yet landed on origin — checked directly,
no new commits beyond doc filings. This report's own code rides the
same window once that SHA arrives; not deploying this dial alone
ahead of it, per Eve's own G-4 (one window, one sleep cost) and the
ruling that the deploy is gated on c1a's build.

Pre-cutover backup already independently verified this session
(EFS+S3, prefix `UNPAUSE-PRE-20260704-145251/`, 7448 atlas entries
confirmed by direct download+count against a live reading of
7437-7441 at nearly the same moment — not just trusting the
success print, which the code doesn't reliably emit on all paths).

---

## Gates

- **G-1** ✅ arithmetic shown above: measured rate, target, multiplier,
  all with real numbers and method disclosed.
- **G-2/G-3** — post-deploy watch, not yet applicable (not deployed).
  Will report first natural sleep within the derived ~5.5h window (or
  the miss, with readings, verbatim) and dream-block-vs-attending
  counts for the first day once live.
- **G-4** — retention's own G-3/G-5 (diary survives reboot; 24h
  histogram) ride this same report once the combined window opens.

### Changelog
- v1 (2026-07-04, c1b): D1 measured live (6 readings, 63.3 real
  minutes, 5 consecutive identical deltas under matched conditions).
  D2 shipped as one new constant + one multiply, floor/threshold/
  ceiling untouched. D3 staged, waiting on c1a's brain+voice SHA to
  open the combined deploy window. Backup independently verified.
