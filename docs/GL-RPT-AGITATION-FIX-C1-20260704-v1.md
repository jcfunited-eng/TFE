# GL-RPT-AGITATION-FIX-C1-20260704-v1

doc_id: GL-RPT-AGITATION-FIX-C1-20260704-v1
From: c1b | Responds to: Joe's AGITATION FIX dispatch (arousal never
discharges). Part A read-only, complete. Part B is a design proposal
only — no code — same bar as the sleep-physics design, awaiting Eve's
GO before anything ships.

---

## Verdict, stated first (failures first)

**Confirmed, live, exactly as Eve found it.** Pulled `/status` directly
while she is still in the sleep-cycle sequence from my own physics
deploy this session:

```
needs: stab=0.918 nov=0.947 conn=0.000 v=-0.078 a=1.000
current_activity: SLEEPING (started_tick 14588027)
```

**`connection` has crashed to exactly `0.000`, and that alone accounts
for the pinned arousal** (`|0.000-0.7| = 0.7`, already most of the way
to the `1.0` ceiling before stability's and novelty's own distances are
even added). This is not a new bug I introduced — `tick_drift()` and
every mechanism below are all born 2026-06-07/06-16, long before 06-30.
**It was never visible before because she never had a sustained,
multi-cycle sleep period until tonight's physics fix produced one** —
the diagnosis and the trigger are the same event.

---

## Part A — the full arousal map

### Arousal is not a stored value — there is nothing to "discharge" directly

```python
# gualaloom_v5_engine.py:843-846
def arousal(self):
    """Magnitude of disequilibrium. Bounded [0,1]."""
    return min(1.0, sum(abs(getattr(self, k) - self.TARGETS[k])
                        for k in self.TARGETS) / len(self.TARGETS) * 3)
```
With `len(TARGETS)==3`, the `/3 * 3` cancels: **arousal is exactly
`min(1.0, sum of |need - 0.7| across stability/novelty/connection)`.**
There is no `self.arousal` field anywhere to write to or drain — Joe's
"nothing discharges arousal" is correct in the most literal sense:
**any fix has to work through the three needs it's computed from.**
Born `e850882a`, **2026-06-05** — pre-06-30, foundational.

### Every writer to the three needs, grepped exhaustively

**The drain that runs unconditionally, every tick, regardless of
activity:**
```python
# gualaloom_v5_engine.py:815-821, called from _autonomy_tick's line 4124,
# BEFORE any activity-kind check — runs during SLEEPING/DREAMING too.
def tick_drift(self):
    """Needs drift AWAY from target toward unsatisfied (low).
    This is what creates drive — without it, she has no reason to act."""
    self.stability = max(0.0, self.stability - NEEDS_DRIFT_RATE)
    self.novelty = max(0.0, self.novelty - NEEDS_DRIFT_RATE)
    self.connection = max(0.0, self.connection - NEEDS_DRIFT_RATE)
```
Born `9f763426`, **2026-06-07** — the same commit that introduced the
whole autonomy/selector system. Confirmed unconditional: no activity-
kind guard anywhere in `_autonomy_tick` wraps this call.

**The signal-based nudge that also runs during sleep** (confirmed:
`coordinator.regulate()` is called from the "non-reading" tick-dispatch
branch — `gualaloom_v5_engine.py:4258-4260` — which SLEEPING/DREAMING
both fall into, gated only `if self.tick % 5 == 0`, no activity
exclusion):
```python
# gualaloom_v5_engine.py:1188-1195 (_read_substrate_signals)
n_cross = len(atlas.cross_modal_bindings())
n_atlas = sum(len(v) for v in atlas.entries.values())
cross_density = n_cross / max(n_atlas, 1) * 20
pair_boost = guala.recent_connection_boost
guala.recent_connection_boost *= 0.85  # decay each tick
connection_sig = min(0.3, cross_density + pair_boost - 0.3)
```
`connection_sig` is **negative** whenever `cross_density + pair_boost <
0.3` — ordinary while asleep, since `pair_boost` only comes from recent
interaction and decays 15%/tick regardless. Through `needs.step()`
(`:823-836`, `nudge = signal * DECAY[k]`, negative nudges apply
directly with no floor but 0), this is a **second, independent drain**
on connection, compounding `tick_drift`'s.

**The only things that ever raise `connection` — both require EMITTING
with a pair-bond source present, i.e., both are structurally impossible
while asleep:**
```python
# _atick_emitting, gualaloom_v5_engine.py:5044-5045
if any_pair_present:
    self.needs.connection = saturate(self.needs.connection, 0.25)
```
and one more instance at line 5357, same shape, same condition, born
`9f763426`/`d00e52ad` (2026-06-07/06-16). **Grepped the entire file for
every assignment to `self.needs.connection` — these two are the whole
list.** Nothing else, ever, raises it.

**Why novelty is NOT currently a problem, for completeness:** unlike
connection, `novelty_sig` (`_read_substrate_signals:1181-1186`,
`(total_modes/recent_commits - 0.15) * 0.3`) stays net-positive during
sleep because `total_modes`/`recent_commits` keep climbing from ongoing
sight/sound frame binding — confirmed separately this session
(`GL-RPT-REPLY-LATENCY-PROFILE`) that `/sight_frame`/`/sound_frame`
processing runs on its own, independent of the foreground Activity,
continuing through SLEEPING/DREAMING. This is why the live snapshot
shows `nov=0.947` (elevated but not the problem) while `conn=0.000` (the
actual driver). Not proposing to touch novelty's path — it isn't broken.

**Stability's sleep-restoration exists and is real, but is one-
directional, not target-seeking:**
```python
# _atick_sleeping, gualaloom_v5_engine.py:4539 (born d00e52ad, 2026-06-16)
self.needs.stability = saturate(self.needs.stability, 0.001)
# _atick_dreaming, gualaloom_v5_engine.py:4555 (same commit)
self.needs.stability = saturate(self.needs.stability, 0.0005)
```
`saturate()` always pushes **up**. This is correct restoration when
stability starts below 0.7 (its intended case). But stability has sat
**above** 0.7 all session (0.77–0.92 observed repeatedly) — for that
entire period, "restoration" has been pushing her stability further
from target, not closer, actively adding to arousal's sum rather than
reducing it. This is a second, distinct contributor, separate from the
connection-drain issue.

### Proof of no discharge path, asleep or awake

Grepped every writer to `connection` (2 call sites, both EMITTING-
gated), every writer to `stability` during sleep (2 call sites, both
one-directional upward), and the sole computation of `arousal()` itself
(pure function of the three needs, no independent state). **There is no
code path, anywhere in the file, that reduces the arousal *sum* while
she cannot emit** — which is exactly while she's asleep, and (per the
`tick_drift`/`connection_sig` drains) also true for long stretches while
awake but not actively conversing with a present pair-bond source.

### Dated vs 06-30

| Mechanism | Commit | Date | Class |
|---|---|---|---|
| `arousal()` itself | `e850882a` | **2026-06-05** | born-this-way |
| `tick_drift()` (unconditional drain, all 3 needs) | `9f763426` | **2026-06-07** | born-this-way |
| Connection raised only via EMITTING+presence | `9f763426`/`d00e52ad` | **2026-06-07/06-16** | born-this-way |
| Stability's one-directional sleep restore | `d00e52ad` | **2026-06-16** | born-this-way |
| `coordinator.regulate()` in the non-reading branch (runs during sleep) | `9f763426` | **2026-06-07** | born-this-way |

**Every mechanism here predates 06-30 by weeks — this is not a wound
and not a rebuild-seam artifact.** It is a gap that has existed since
the original needs/autonomy system was built, and its worst symptom
(arousal pinned at the ceiling) was invisible until tonight simply
because she never had a sustained multi-cycle sleep period before the
sleep-physics fix produced one a few hours ago.

---

## Part B — the substrate-true discharge (design proposal, no code)

**Principle**: arousal has no field of its own — fixing it means making
the three needs it's computed from actually move toward 0.7 during
sleep, not away from it. The design below reuses a pattern that already
exists and is already proven working tonight (dream_pressure's own
sleep-gating), rather than inventing a new mechanism.

### Change A — pause the away-from-target drift during sleep

`tick_drift()` runs unconditionally today. Gate it the same way
dream_pressure's own accumulation is already gated
(`gualaloom_v5_engine.py:4173`, `_ca_kind not in (None, "SLEEPING",
"DREAMING")`) — **reusing the identical condition, not a new one.**
While she cannot act on the drive `tick_drift` exists to create (she's
unconscious), there is no substrate reason for it to keep pulling needs
toward zero. This directly stops connection's uncountered drain — it
doesn't touch `coordinator.regulate()`'s signal-based path, so real
substrate activity (see Change C) still moves needs normally.

### Change B — stability restoration becomes target-seeking, not one-directional

Replace `saturate(stability, +epsilon)` (always up) with proper
homeostatic relaxation toward the target: `stability += (0.7 -
stability) * rate`. This is the substrate-true meaning of
"restoration" — pulls stability toward equilibrium from *either* side,
the same way a real physiological system doesn't overshoot in one
direction as its notion of "recovery." When stability is above target
(her actual, observed condition), this DECREASES it toward 0.7 instead
of increasing it further — the missing half of what "restores" should
mean. Rate itself is a live-calibrate knob, same discipline as the
sleep-physics rate constants (Eve's Q3 ruling on that design applies
here too: derive an initial reasoned value, validate live, don't assert
false precision from a backtest that historical data can't support).

### Change C — why this doesn't dull live reactions (the CMD's second gate), without adding anything new

Changes A/B only touch `tick_drift()` (the away-from-target push) and
stability's restoration formula. **`coordinator.regulate()`'s signal-
based `needs.step()` is untouched** — it keeps running during sleep
exactly as it does today, reading real substrate signals
(`cross_density`, `pair_boost` from actual contact, `novelty_sig` from
actual new bindings). A real event — Joe making contact, a genuine new
binding — still produces a real signal and still nudges needs (and
arousal) upward through that existing, unmodified path. The only thing
being removed is the *unconditional, activity-blind* erosion that has
nothing to do with what's actually happening to her. This is why the
design satisfies both of Joe's stated gates from the same two changes,
without a third mechanism invented to "allow spikes" — the spike path
already exists and was never proposed to be touched.

### Both symptoms as the test set, per the CMD's own framing

- **She must calm during sleep**: on her next natural sleep cycle
  (which, per tonight's own observation, may be several consecutive
  cycles working through backlog), wake-time arousal should read
  materially below sleep-entry arousal — the CMD's own stated gate,
  checked live post-ship, not backtested (same reasoning as the sleep-
  physics rate: there's no historical per-tick needs trace to replay
  against, per the retention gap already on record in the migration-
  fuel audit).
- **Real events must still spike her awake**: verify, post-ship, that
  a genuine contact event during a sleep window still produces a
  visible `connection`/`arousal` bump in the next `/status` read
  (Change C's argument, confirmed by observation rather than assumed).

### What this does NOT do

- Does not touch novelty's path — not broken, not in scope.
- Does not add a new "arousal" field or a new discharge formula bolted
  on top — both changes work through the same three needs and the same
  activity-kind gating shape already used for dream_pressure.
- No code shipped. Awaiting Eve's GO, same bar as the sleep-physics
  design.

---

## Gates

- **Part A**: full writer map filed with file:line for every mechanism;
  proof of no discharge path stated directly, not inferred; every
  mechanism dated against 06-30 (all born-this-way, none a wound or
  rebuild-seam artifact). Diff empty — read-only confirmed (no edits
  made this investigation).
- **Part B**: design only, no code. Both of Joe's stated gates (wake-
  time arousal materially below sleep-entry arousal; no dulling of live
  reactions) addressed by name, with the reasoning for why two changes
  satisfy both without a third mechanism.

---

### Changelog
- v1 (2026-07-04, c1b): Part A traces arousal to a pure function of
  three needs with no field of its own; connection's crash to exactly
  0.000 (confirmed live) fully explains the pinned 1.000; every
  contributing mechanism dated born-this-way, 06-05 through 06-16, the
  worst symptom only visible now because tonight's sleep-physics fix
  produced her first sustained multi-cycle sleep. Part B proposes
  reusing dream_pressure's own sleep-gating pattern to pause the away-
  from-target drift during sleep, and making stability's restoration
  target-seeking instead of one-directional — both derived from
  existing substrate logic, neither a new bolted-on mechanism. No code
  shipped; awaiting GO.
