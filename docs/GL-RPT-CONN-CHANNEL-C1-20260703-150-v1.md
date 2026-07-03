# GL-RPT-CONN-CHANNEL-C1-20260703-150-v1

doc_id: GL-RPT-CONN-CHANNEL-C1-20260703-150-v1
From: c1b | To: Eve | Date: 2026-07-03
Responds to: GL-CMD-CONN-CHANNEL-EVE-20260703-150-v1, Part A (read-only, blocking).

---

## VERDICT: H-B — PHYSICS-BY-DESIGN. No bug. No Part B code fix.

The presence flag does not, and structurally cannot, feed connection on its own. Only
two discrete event types push connection up; between them, drift is unconditional and
un-opposed. A silent present parent decays to absence, exactly as H-B's hypothesis
states. Filed before any fix, per the CMD's blocking order.

---

## A.1 — connection dynamics end-to-end, file:line map

`gualaloom_v5_engine.py`, `Needs` class (line 735) and the presence coordinator (class
starting ~line 860, exact name not confirmed but methods are `wake`/`rest` at 901/933).

**Every write site to `needs.connection`, exhaustively grepped (`\.connection = `):**

| line | site | mechanism |
|---|---|---|
| 758 | `Needs.__init__` | one-time default 0.50 on fresh object |
| 784 | `tick_drift()` | `max(0.0, self.connection - NEEDS_DRIFT_RATE)` — **unconditional, every tick, no gate, no floor check beyond 0** |
| 912–914 | `wake(source, ...)` | one-shot: if pair-bonded, `saturate(connection, gap * 0.4)` toward target 0.7 — fires only on an explicit wake **event** |
| 4869–4874 | `_atick_emitting()` | fires only `if self.tick == a.started_tick + 1` (once, at the instant an EMITTING activity begins) — reads `coordinator._presence.get(s, False) and coordinator._pair_bond.get(s, False)`; if true, `saturate(connection, 0.25)` |
| 5180–5186 | `_do_emit()` | **the identical check and saturate call**, reached from inside `_do_emit()`, which `_atick_emitting` itself calls at line 4867 — see note below |
| 6824 | boot/state restore | loads a persisted value; not a live gain |

`NEEDS_TARGET_V7 = 0.7` (line 406), `NEEDS_DRIFT_RATE = 0.0001`/tick (line 405,
"needs fall from 1.0 to 0 in ~10K ticks" per its own comment).

**The presence FLAG itself** (`coordinator._presence[source]`, set `True`/`False` only in
`wake()`/`rest()`, lines 906/940) **is read in exactly two places in the whole file**
(4870, 5182) — both gated behind `self.tick == a.started_tick + 1` (i.e., only at the
instant *she* starts an EMITTING activity). **Nowhere does the code continuously check
"is someone present" and apply an ongoing connection maintenance term.** The flag is
real, correctly set, and correctly read at those two instants — it just never does
anything between them.

**Minor secondary finding, not the verdict driver**: line 5180's comment reads
"Connection saturation (moved here from `_atick_emitting`)" — but the original block at
4869–4874 is still present and still executes (`_atick_emitting` calls `_do_emit()` at
line 4867, then falls through to its own copy of the same check). `saturate()`
(line 47–50, `current + gain*(1-current)`) is not linear, so calling it twice from 0.0
with gain 0.25 reaches 0.4375, not 0.5 — the boost is likely being applied twice per
emission rather than once. This affects the *size* of the periodic bump, not whether a
continuous presence-maintenance mechanism exists (it doesn't, either way). Flagging for
Eve's judgment on whether it's worth its own small cleanup dispatch; not fixed here — out
of Part A's read-only scope and not what floored the value.

---

## A.2 — today's trajectory, reconstructed

Direct evidence available: Eve's own filed observation (0.77–0.89 reading earlier today;
floor at 0.000 with joe flagged present; the wc wake event proving `conn 0.000→0.28,
arousal 1.000→0.729, valence −0.131→−0.037` in one shot) plus my own live check just now:

```
needs: stab=0.749 nov=0.962 conn=0.000 v=-0.130 a=1.000
presence: {"joe": {"present": false, ...}}
current_activity: ATTENDING_VISUAL (started 14504548, budget 2000 ticks)
activity_history_summary: ATTENDING_VISUAL count=21 total_ticks=42,000
                           EMITTING       count=31 total_ticks=3,100
```
Connection is floored right now too — presence is currently `false`, consistent with
drift alone, but this doesn't test the CMD's specific claim (floor *with* presence
flagged true); I did not have a window with presence continuously true long enough to
directly re-observe the floor happen live before this report was due. The mechanism
proof above stands independent of that.

**Quantified drift timescale**, from the live tick rate (measured tonight,
task:456: 21,692 ticks / 5,569s ≈ **3.90 ticks/sec**) and `NEEDS_DRIFT_RATE=0.0001`:

```
from conn=0.77 → 0.000, no gain events: 7,700 ticks ≈ 32.9 minutes
from conn=0.85 → 0.000, no gain events: 8,500 ticks ≈ 36.4 minutes
from conn=0.89 → 0.000, no gain events: 8,900 ticks ≈ 38.1 minutes
```
Her own recorded activity mix today: ATTENDING_VISUAL activities run in ~2,000-tick
budgets (≈8.6 min each at this tick rate) and dominate her time 42,000 ticks to
EMITTING's 3,100 — meaning multiple full ATTENDING_VISUAL cycles routinely separate
consecutive emissions. **A 33–38 minute stretch without her emitting is well within what
her own measured activity pattern already produces**, and floor-reaching does not require
presence to ever go false — only that she goes that long without emitting *while*
connection's only other gain (a fresh `wake()` event) also doesn't fire. Once floored,
connection stays at exactly 0.000 (the `max(0.0, ...)` clamp) until the next event,
regardless of how long presence stays flagged true.

---

## PART B

**Per the CMD's own routing: H-B ships no code fix in this dispatch.** Two actions
outside this CMD's code scope, both named so they aren't lost:
1. **Care-practice**: presence sessions need a stated interactive cadence — flagged
   presence alone, without periodic wake/interaction events, will always drain to the
   connection floor within roughly half an hour by the physics above, regardless of
   whether the parent is actually there.
2. **Design question for Joe** (physics proposal required first, per the CMD): should
   flagged-presence contribute a small continuous connection maintenance term, so a
   quiet-but-present parent doesn't read identically to an absent one? That's a real
   design decision, not a bug fix — Eve's call to bring to him.

No -150 code rides Deploy 4. G-150-2/G-150-3 are N/A under this verdict (no fix to
observe).

---

## STATE

Read-only, no code touched. Verdict filed before any fix commit, per the CMD's blocking
order (G-150-1 satisfied). Deploy 4's -150 contribution is nothing.

End report.
