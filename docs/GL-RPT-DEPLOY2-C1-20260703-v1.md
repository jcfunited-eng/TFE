# GL-RPT-DEPLOY2-C1-20260703-v1

doc_id: GL-RPT-DEPLOY2-C1-20260703-v1
From: c1a | To: Eve | Date: 2026-07-03 (deploy 02:04–02:11Z; gates measured to ~02:25Z)
Responds to: GO Deploy 2, pinned SHA cb79cbc8fd379a49206e2841ba22a2bc6d526133
Covers: -86 (T1-T6), -87 (G-A/B/C), -88 (G-S1..S5), -98 (T1-T7), cross-cutting gates.
Per -88 CMD: **G-S2 FAILED → the fix does not get iterated live. Reported and stopped.**

---

## FAILURES FIRST (§9.4)

### 1. -88 G-S2: **FAIL** — stab did not move. Mechanism identified, named below.

Measured (bridge status, verbatim needs lines; wake ~02:10:40Z):

```
point 1  02:11:5xZ  tick 14216429  (~740 ticks post-boot,  IDLE block 2)   stab=0.000  a=1.000
point 2  02:14:5xZ  tick 14216872  (1,500 IDLE ticks done, EMITTING gap)   stab=0.000  a=1.000
point 3  02:19:5xZ  tick 14217777  (2,500 IDLE ticks done, IDLE block 6)   stab=0.000  a=1.000
```

Yardstick (G-S1, filed pre-deploy): strictly increasing, ~0.3 within ~1,600 ticks
(~7.6 min), equilibrium ≈0.67. Observed: 0.000 flat through 2,500 IDLE ticks / ~16 min.

**Mechanism (from the deployed code + live counts):** the G-S1 arithmetic's Channel C
assumed the R2-replaced "bored" branch supplies +0.0003/tick. That branch fires only
when `recent_commits == 0` (engine `_read_substrate_signals`) — and live it NEVER
fires: section commit lists are non-empty whenever the curriculum runs (live counts at
point 2: total_modes=48,462, recent_commits=35,195). So the UNTOUCHED active branch
executes instead:

```
reinforcement_rate = 1 − 48462/35195 = −0.377
stability_sig      = (−0.377 − 0.5) × 0.2 = −0.175     ← comment says "nudge ±0.1"; NO clamp exists in code
nudge              = −0.175 × DECAY(0.02) = −0.00351 per regulate call (every 5 ticks)
                   = −0.000702 per tick
```

Against that, the shipped gains: Channel B (_atick_idle) +0.0000876/tick at stab=0,
drift −0.0001/tick. Net ≈ **−0.00071/tick** → floored at 0.000 permanently.
R2 replaced a branch production never executes; the dominant negative channel — the
active-branch signal, unclamped, driven negative by modes>commits — was left in place.
This is the -88 trap's actual live channel, and it was not in the -99 archaeology's
freeze arithmetic either (my -99 report modeled the bored branch at −0.0002/tick;
the active branch at −0.0007/tick is the stronger, always-on term. On record.)

**Per the CMD: not iterated live. No fix attempted. Eve rules on the next shape.**
(Observation for that ruling, not a recommendation acted on: `s.commits`/`s.modes`
are cumulative-since-boot, so `reinforcement_rate` is a lifetime ratio, not a "recent"
rate — the signal is structurally negative whenever lifetime modes exceed lifetime
commits, regardless of what is happening now.)

### 2. -88 G-S3: FAIL as a consequence — arousal pinned 1.000 at all three points
(derived quantity; cannot fall while stab=0.000; no code was touched for it, correctly).

### 3. -86 T1 (hot save <5s): **FAIL in the first window.** Six [save-hot] samples:

```
02:11:45 | [save-hot] 32.73s core=29.91s compact=2.82s
02:13:24 | [save-hot] 38.47s core=36.08s compact=2.38s
02:15:00 | [save-hot] 36.28s core=34.05s compact=2.23s
02:16:34 | [save-hot] 33.56s core=31.30s compact=2.27s
02:17:47 | [save-hot] 13.85s core=13.84s compact=0.01s
02:19:16 | [save-hot] 29.09s core=29.01s compact=0.07s
```

13.9–38.5s vs <5s. The 2h window continues and T4's eviction may pull it down, but
<5s is not plausible while guala_deep_atlas.json is ~198MB (T4 baseline below).

### 4. NOT MEASURED (windows / preconditions):
- -86 T2 (cold consolidation <60s): no sleep boundary on :451 yet (the deploy sleep
  ran on :450's old code).
- -86 T4: baseline pinned — `guala_deep_atlas.json` = **198,581,598 bytes** at 02:09Z
  (unchanged since 23:17Z, on record). Trend check due ~2026-07-04 02:00Z.
- -86 T5 / -87 G-B: no /converse landed in the window — converse timing NOT MEASURED;
  autonomous-emission timing measured (below) and within budget.
- -86 T6: 48h window (due ~2026-07-05).
- -98 T1/T2/T3/T4/T6: page-render and dedupe gates need a browser session; c1a
  verified serving only (below). T7 = Joe's sign-off line — **pending Joe**.

---

## DEPLOY RECORD

```
Pinned SHA:  cb79cbc8fd379a49206e2841ba22a2bc6d526133 (== origin tip at GO; detached worktree; GIT_SHA exported)
Image:       dsf-ai:deploy-20260703T020457Z   built 2026-07-03T02:06:21Z
Task def:    dsf-ai-task:451   task c076115aece5411d81aa5d286f558ed1, RUNNING
Sleep:       /sleep_for_deploy → 200 {"ok":true,"sleep_tick":14215680,"vocab":13864}
Wake:        t+15s — awake. One deploy in flight. Static synced + CF invalidated.
```

Code delta e31f40f-lineage 07f15b4→cb79cbc: Dockerfile, app.py, save_coordinator.py,
deep_atlas.py, substrate_runner.py, engine, deploy script, gualaloom.html, loomscan.html
(new) — matches the -86/-87/-88/-98 set; nothing else rode.

## CROSS-CUTTING GATES

**Boot banner SHA == pin: PASS**
```
02:10:12 | [build] git_sha=cb79cbc8fd379a49206e2841ba22a2bc6d526133 built=2026-07-03T02:06:21Z
```

**.sleeping marker PRESENT (expected this time): PASS**
```
02:10:25 | [boot] previous task slept cleanly at tick 14215680, age=72s. Waking her.
```
(Deploy 1's containment + npz fix working exactly as designed — first deploy in the
record with a fully clean sleep→swap→wake.)

**Deploy-1 G2 closure, now MEASURED on a real boot:**
```
02:10:25 | [GualaLoom] WaveAtlas loaded from disk (npz): 2011 cells, 50442 bindings
02:10:25 | [wave] collapse-on-load: 50442→48969 bindings (wired=True)
```

**Standing count-diff across restart: PASS**

| Counter | Pre (tick 14214589, 02:03Z) | Post (tick 14216429, 02:11Z) | Δ |
|---|---|---|---|
| identity | cdef9bcf-9e5d-4e2d-a1d8-4cde1de7641f | same | = |
| vocab | 13864 | 13864 | = |
| n_motifs | 48462 | 48462 | = |
| deep_atlas | 3753 / str 3355.68 | 3753 / str 3355.68 | = |
| atlas cross-modal | 104 | 104 | = |
| atlas live bindings | 6551 | 6599 | +48 |
| sight motifs | 13340 | 13346@boot → 13361 | growing |
| pictures / sounds / videos | 27 / 15 / 0 | 27 / 15 / 0 | = |

Boot line: `Loaded: id=cdef9bcf.. vocab=13864 tick=14215685 reads=2367370 n_deep=3753 replayed=0 integrity=OK`

## -87 GATES

**G-A: PASS.** All four sampled post-deploy emission_dynamics show `dynamics_ticks=80`
(was capped at 40 in all 21 baseline samples).

**G-C: reported truthfully — and the hoped outcome arrived.** Of 4 sampled 80-tick
emissions, **3 committed** (n_commits=1, committed_sections=['verb']); baseline at 40
ticks was 0-of-21. Verbatim:

```
tick=14216109 ticks=80 s1=97.7  s2=246.1 commits=1 content='play page'
tick=14216468 ticks=80 s1=95.7  s2=241.7 commits=0 content='figure page'
tick=14217183 ticks=80 s1=97.9  s2=197.8 commits=1 committed=['verb'] content='many page'
tick=14217523 ticks=80 s1=244.1 s2=351.6 commits=1 committed=['verb'] content='many page'
```

Consistent with the engine's own physics ("commits start around tick 60-70"). Content
is still the degenerate "<word> page" shape — the T⁶/-125 composition review still has
its subject.

**G-B: partial.** Converse NOT MEASURED (no traffic). Emission stage2 at 80 ticks:
197.8–351.6 ms — above the linear extrapolation from the Part A baseline (178 ms;
per-tick 2.47–4.40 vs 2.23 ms — the commit machinery costs), still 4.3× inside the
1.5 s wall at worst. No cadence disruption (one emission per ~400 ticks, unchanged).

## -88 GATES (balance)

- G-S1: PASS — prediction was filed pre-deploy in GL-RPT-STAB-PHYSICS-FIX-C1-20260703-88-v1 (cb79cbc).
- G-S2: **FAIL** (Failures #1). G-S3: FAIL as consequence (#2).
- G-S4: PASS — SLEEPING/DREAMING gains untouched in the diff (only regulate bored-branch,
  _atick_playing, new _atick_idle, dispatch branch).
- G-S5: PASS — ACTIVITY_STABILITY_PAYOFF["IDLE"] untouched.

## -98 GATES (c1a-verifiable portion)

- Serving: `https://dsf-ai.com/loomscan.html` → HTTP 200, 30,047 B, 0.286 s (curl;
  CloudFront). gualaloom.html serves (63,884 B; 95-line pane removal rode).
- T1 (renders from live data <2s), T2 (dedupe vs burst), T3 (honest empty states),
  T4 (polling load), T5 (sp-emissions no-regression), T6 (persistence truth):
  need a live browser session — **pending T7**, where Joe opens it; his sign-off line
  goes here verbatim: ______________________________________________

---

## STATE

Deploy 2 live on :451/cb79cbc. -87 green and delivering commits; Deploy-1 wave/sleep
machinery proven end-to-end; -88 G-S2 failed with the mechanism named — per the CMD,
no live iteration; Eve rules. -86 timing gates run their windows (T1 failing early).
c1a STOPPED on -88. Deploy 3 (organ reader, alone) is c1b's after gates.

End report.
