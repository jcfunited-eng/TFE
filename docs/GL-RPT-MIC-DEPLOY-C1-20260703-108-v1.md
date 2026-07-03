# GL-RPT-MIC-DEPLOY-C1-20260703-108-v1

doc_id: GL-RPT-MIC-DEPLOY-C1-20260703-108-v1
From: c1b | To: Eve | Date: 2026-07-03
Responds to: GL-CMD-MIC-DEPLOY-EVE-20260703-108-v1
Amended SHA deployed: b7fd05ec85ab6778a6d3ad5582bd0b3252805400 (task:454), then
consolidated with GL-CMD-DENSITY-RETIRE-EVE-20260703-109-v1 at
16bc0c294fc0c1012ea92a6cd12914cb90d6c31e (task:455, currently live).

---

## FAILURES FIRST

### 1. G-108-2: FAIL. Live voice discrimination is broken by a routing gap — the
### mic-decode fix (332537d and today's A.1) never runs on the path Joe's
### browser actually calls.

**Traced to code, not guessed.** `gualaloom.html`'s mic capture (`startMicSoundStream`,
line ~216) POSTs each WebM chunk to `${API}/sound_frame` with `source:'joe_voice'`.
`POST /sound_frame` (`app.py:1531`) branches on `_is_remote()` (`SUBSTRATE_MODE=="remote"`).
The deployed task env sets `SUBSTRATE_MODE=embedded` (`tools/deploy_dsf_ai.sh:235`), so
`_is_remote()` is `False` — every real mic chunk takes the **embedded-mode direct path**:
`_decode()` → `_guala.process_sound_frame(audio_bytes)` on the **raw, undecoded WebM bytes**.
No ffmpeg step exists on this path. `process_sound_frame`'s own internal fallback
(`wave.open()` fails on WebM → raw bytes reinterpreted as 8-bit PCM) is exactly the
"garbage" path the original -106 diagnosis described, and it is still what runs live today.

The ffmpeg-WebM-decode fix (332537d, and this dispatch's A.1 guard) lives entirely inside
`_start_input_ring_consumer`'s drain loop (`substrate_runner.py`), which only processes
audio that arrives via the `InputRing` — which only happens when `_is_remote()` is `True`,
or via the internal `/api/v1/gualaloom/ring/write` test path. **Neither is the live
website's path.** I proved the drain-loop fix works correctly on its own path (G-108-4,
below); I did not extend it to `/sound_frame`'s embedded branch — that is a third code
change beyond what this CMD's declared scope ("decode plumbing only... adds two log
lines... No constants") authorized. I disclosed this to Joe before running the live test
(transcript, this session) and he chose to proceed and get a measured FAIL on record
rather than skip it.

**Empirical confirmation, live mic, Joe speaking (33 samples, 20:57:17–20:59:38Z,
temporary `[cochlear-debug]` instrumentation, `gualaloom_v5_engine.py` line ~4687,
marked for removal):**

```
1783112237976  {'very_low': 252, 'low': 429, 'low_mid': 518, 'mid': 565, 'mid_high': 258, 'high': 262}
1783112251427  {'very_low': 291, 'low': 428, 'low_mid': 534, 'mid': 515, 'mid_high': 448, 'high': 502}
1783112251573  {'very_low': 227, 'low': 507, 'low_mid': 560, 'mid': 686, 'mid_high': 302, 'high': 336}
1783112263575  {'very_low': 308, 'low': 519, 'low_mid': 486, 'mid': 308, 'mid_high': 422, 'high': 394}
1783112263981  {'very_low': 288, 'low': 556, 'low_mid': 595, 'mid': 330, 'mid_high': 384, 'high': 280}
1783112266958  {'very_low': 258, 'low': 467, 'low_mid': 668, 'mid': 626, 'mid_high': 340, 'high': 412}
1783112280973  {'very_low': 270, 'low': 525, 'low_mid': 588, 'mid': 637, 'mid_high': 530, 'high': 350}
1783112295594  {'very_low': 32,  'low': 44,  'low_mid': 64,  'mid': 58,  'mid_high': 102, 'high': 240}
1783112298152  {'very_low': 251, 'low': 453, 'low_mid': 511, 'mid': 730, 'mid_high': 412, 'high': 258}
1783112298217  {'very_low': 228, 'low': 385, 'low_mid': 597, 'mid': 583, 'mid_high': 513, 'high': 592}
1783112298255  {'very_low': 30,  'low': 34,  'low_mid': 38,  'mid': 62,  'mid_high': 48,  'high': 98}
1783112309071  {'very_low': 288, 'low': 487, 'low_mid': 481, 'mid': 572, 'mid_high': 486, 'high': 490}
1783112314282  {'very_low': 261, 'low': 413, 'low_mid': 645, 'mid': 642, 'mid_high': 366, 'high': 672}
1783112314305  {'very_low': 40,  'low': 60,  'low_mid': 96,  'mid': 58,  'mid_high': 50,  'high': 134}
1783112320753  {'very_low': 44,  'low': 50,  'low_mid': 48,  'mid': 102, 'mid_high': 152, 'high': 72}
1783112320855  {'very_low': 314, 'low': 366, 'low_mid': 597, 'mid': 659, 'mid_high': 492, 'high': 463}
1783112321950  {'very_low': 244, 'low': 391, 'low_mid': 580, 'mid': 641, 'mid_high': 518, 'high': 266}
1783112321958  {'very_low': 48,  'low': 44,  'low_mid': 50,  'mid': 88,  'mid_high': 96,  'high': 146}
1783112331916  {'very_low': 42,  'low': 50,  'low_mid': 92,  'mid': 100, 'mid_high': 92,  'high': 134}
1783112331968  {'very_low': 255, 'low': 351, 'low_mid': 671, 'mid': 678, 'mid_high': 630, 'high': 487}
1783112333866  {'very_low': 238, 'low': 413, 'low_mid': 577, 'mid': 448, 'mid_high': 386, 'high': 372}
1783112343267  {'very_low': 26,  'low': 36,  'low_mid': 64,  'mid': 76,  'mid_high': 44,  'high': 116}
1783112343283  {'very_low': 24,  'low': 54,  'low_mid': 50,  'mid': 84,  'mid_high': 64,  'high': 78}
1783112343333  {'very_low': 244, 'low': 507, 'low_mid': 586, 'mid': 478, 'mid_high': 436, 'high': 310}
1783112366807  {'very_low': 266, 'low': 408, 'low_mid': 623, 'mid': 631, 'mid_high': 392, 'high': 316}
1783112366850  {'very_low': 32,  'low': 42,  'low_mid': 50,  'mid': 76,  'mid_high': 56,  'high': 72}
1783112366889  {'very_low': 235, 'low': 469, 'low_mid': 655, 'mid': 462, 'mid_high': 440, 'high': 598}
1783112366982  {'very_low': 28,  'low': 50,  'low_mid': 52,  'mid': 58,  'mid_high': 72,  'high': 90}
1783112367895  {'very_low': 266, 'low': 453, 'low_mid': 583, 'mid': 514, 'mid_high': 396, 'high': 575}
1783112374246  {'very_low': 230, 'low': 431, 'low_mid': 515, 'mid': 549, 'mid_high': 377, 'high': 240}
1783112376973  {'very_low': 273, 'low': 539, 'low_mid': 500, 'mid': 359, 'mid_high': 502, 'high': 600}
1783112377577  {'very_low': 191, 'low': 486, 'low_mid': 458, 'mid': 493, 'mid_high': 314, 'high': 554}
1783112378013  {'very_low': 42,  'low': 38,  'low_mid': 56,  'mid': 64,  'mid_high': 76,  'high': 52}
```

I asked Joe to stay silent ~10s then speak, but he had no way to mark the transition and I
have no synchronized timestamp for it. The data shows two recurring magnitude clusters
(roughly 200–700 events/band vs roughly 25–150 events/band) **interleaved throughout the
whole ~2m20s session**, not a clean two-phase silence-then-speech split — consecutive
`sound_frame` chunks 1–2 seconds apart flip between clusters repeatedly. Without a marked
transition I cannot attribute a given sample to "silence" or "speech" with confidence, and
mechanistically I already know why: the input to `cochlear_transduce` is raw WebM container
bytes (EBML/cluster framing + Opus payload), not decoded PCM. The magnitude clustering most
plausibly tracks WebM/Opus's own variable bitrate (near-silent frames encode to very few
bytes even before decode) rather than any real spectral property of Joe's voice. **Per the
CMD's own rule: indistinguishable/unattributable → FAIL, stop, report verbatim, no live
iteration.** I am doing exactly that — no further code changes attempted against this
gate today.

**Next step is Eve's call, not mine to build today**: extend the ffmpeg-decode step (or the
InputRing itself) to the embedded `/sound_frame` path, or route `/sound_frame` through
`ring_write` even in embedded mode so one decode path serves both architectures.

---

## PRE-108 RESTART FORENSICS (Joe's mid-session ask, read-only)

**Window: 20:11:49Z–20:13:26Z, task 2572d97b (`:453`, SHA 1b5eca8, Deploy 3) — 97.5s of
total request silence, ECS auto-replaced it independently of any deploy.**

Full timeline (all times UTC, 2026-07-03):
```
20:11:49.041  last /ready response before the stall (task 2572d97b)
20:12:53      ECS service event: "Amazon ECS replaced 1 tasks due to an unhealthy status"
              — this fired BEFORE my -108 deploy's own sleep/redeploy calls (see below)
20:13:23.182  [GualaLoom] WaveAtlas saved (npz): 2011 cells, 38305 bindings, 0.5MB
20:13:24.486  my -108 deploy's POST /sleep_for_deploy lands on 2572d97b, 200 OK
20:13:26.597  BURST of 14 queued /ready responses fires within 135ms (task 2572d97b)
20:13:26      replacement task 6cfb7f0b boots (SAME task def :453, SHA 1b5eca8 —
              NOT a new revision; ECS's own scheduler started it, not my deploy script)
20:13:27.031  ECS: "(task 2572d97b) failed container health checks"
20:14:18.331  2572d97b: "Signal 15 — shutting down cleanly" (SIGTERM received)
20:15:38.011  2572d97b stoppedAt, exitCode 137 (SIGKILL after graceful-shutdown deadline)
```

**Root cause: a ~97.5-second total request-handling stall — not just lock contention on
saves, but complete unresponsiveness including trivial `/ready` checks — tripped the
Docker-level container health check (interval 10s × retries 3 ≈ 30s tolerance) well
before my own deploy sequence started. ECS's scheduler auto-replaced the task on its own
initiative, reusing the unchanged task definition (`:453`) — this is exactly "no deploy
issued."** The stall's end (20:13:23) lines up almost exactly with a `WaveAtlas saved
(npz)` completion one second before the first successful request in over 90s, which is
the strongest available correlate; I did not fully prove the mechanism (e.g., whether the
save runs synchronously on the same thread uvicorn's event loop needs, or contends for
`self.lock` in a way that also blocks unrelated routes) — flagging that as still open if
deeper certainty is wanted.

**Not OOM.** `stoppedReason` for both 2572d97b and the later-replaced 6cfb7f0b was health-
check/scheduler-driven ("Task failed container health checks" / "Scaling activity
initiated by..."), never an ECS out-of-memory report. `exitCode: 137` on both is fully
explained by SIGKILL-after-stopTimeout(30s) on any ECS-initiated shutdown, not specific to
OOM. No `RSS`/`OOM`/`Killed`/`MemoryError` string appears anywhere in either task's logs
for the incident window. **Container Insights is not enabled on this cluster/service**, so
no RSS number is available for the exact stall moment — the closest reference point is
Deploy 3's own post-boot snapshot (VmRSS ≈1.65GB, cgroup memory.current ≈3.96GB of a
4,096MB task limit, filed in `GL-RPT-DEPLOY3-C1-20260703-v1.md`), which was already close
to the ceiling but is not a measurement of this incident.

**F3 checked and ruled out as this restart's cause.** `GL-CMD-DENSITY-RETIRE-109` (riding
this same deploy) independently found and fixed a real bug: `_start_input_ring_consumer`
had no started-guard and was reachable from two call sites. I added the guard
(`substrate_runner.py`) and redeployed. Post-fix, the guard's "`[substrate] ring consumer
already running`" branch **never fired** in the new boot — meaning only one real
thread-start occurred even before the fix. (The apparent double print in every prior boot
log was two *different* statements with identical text: the guarded print inside
`_start_input_ring_consumer` itself, and an unconditional standalone `print(...)` at
`app.py:1327` right after the whole background-loop-start block — not two threads.) The
guard is a correct, harmless defensive fix and stays in; it is not evidenced as a
contributor to the 20:12–20:13 stall specifically. No new restart-cause candidate is
proposed beyond the WaveAtlas/hot-save correlation above.

---

## PASSING GATES

**G-108-1 — boot banner matches amended SHA: PASS.**
```
[build] git_sha=b7fd05ec85ab6778a6d3ad5582bd0b3252805400 built=2026-07-03T20:09:38Z
```
(task:454, first deploy of this dispatch, booted 2026-07-03T20:09:38Z). Superseded live
by the consolidated -108+-109 deploy:
deploy: `[build] git_sha=16bc0c294fc0c1012ea92a6cd12914cb90d6c31e built=2026-07-03T20:41:08Z`
(task:455, currently running) — both match their respective pinned SHAs exactly.

**G-108-3 — loomscan center shows a live tick; both nav links resolve: PASS.**
Public-URL source confirms both fixes shipped:
```
loomscan.html:105  <a href="/gualaloom.html">← back to guala</a>
loomscan.html:580  _tick=(d.atlas_health&&d.atlas_health.tick)||d.tick||_tick;
gualaloom.html -> 200
loomscan.html -> 200
```
Live status confirms the fallback chain resolves to a real, non-zero tick:
`atlas_health.tick: 14468950` (queried via the public API Gateway endpoint the page
itself calls) — the "tick 0" placeholder bug is gone.

**G-108-4 — decode-failure guard proven firable: PASS.**
Pushed a deliberately corrupt (32-byte, non-WebM) chunk through the internal
`/api/v1/gualaloom/ring/write` test path (`kind=sound_window`), drained by
`_start_input_ring_consumer`:
```
[sound] cochlear decode failed: ffmpeg produced 0 bytes from 32 in
```
Exact match to the A.1 spec. (Note: my first attempt 500'd on a pre-existing,
unrelated bug in `ring_write` — `InputRing.publish()` got `source` twice when my test
payload duplicated it inside `data`; not caused by today's changes, worked around by not
duplicating the field, not filed as a separate finding since it's a malformed-test-payload
issue, not a code defect on the path any real caller uses.)

**G-108-5 — rotation held: PASS.**
`dsf-ai-task:454`/`:455`'s `GUALALOOM_API_KEY` env value matches `.env`'s
`GUALALOOM_API_KEY_NEW` byte-for-byte (checked via `aws ecs describe-task-definition`).

---

## SCOPE NOTE: what else rode this deploy

Between my Step-0 commit and this deploy, c1a pushed `GL-CMD-ATTEND-GROOVE-EVE-20260703-107`
(`417b468..51de899`) to `guala-live` — a small, purely additive telemetry change
(`top_scores`/`needs_sd` fields on `activity_started`, no candidate/scoring/selection
logic touched, filed in `GL-RPT-ATTEND-GROOVE-PREDEPLOY-C1-20260703-107-v1.md`). Because
`guala-live` has linear history, this range is an ancestor of both deploys in this report
and rode along in the container image. I read the diff for safety (confirmed benign,
non-overlapping with anything I touched) but did **not** review or gate it — that report
and its own gates are c1a's, filed separately.

`GL-CMD-DENSITY-RETIRE-EVE-20260703-109-v1` also rode this same deploy vehicle per Eve's
explicit instruction; its own findings and gates are filed separately in
`GL-RPT-DENSITY-RETIRE-C1-20260703-109-v1.md`.

---

## OPEN ITEMS FOR NEXT DISPATCH

1. `/sound_frame`'s embedded-mode path needs the same ffmpeg-decode treatment as the
   InputRing drain loop, or needs to be routed through the ring even in embedded mode.
   This is the real -106/-108 closure; nothing today reaches it.
2. The temporary `[cochlear-debug]` print (`gualaloom_v5_engine.py`, marked for removal)
   is still live — it will fire on every future `/sound_frame` call. Low cost (one debug
   line), but should be removed on whichever dispatch next touches this function rather
   than spending a fifth deploy today purely on cleanup.
3. The WaveAtlas/hot-save-blocks-the-whole-process mechanism (restart forensics above) is
   correlated, not proven at the code-path level. Worth its own dispatch if Eve wants
   certainty before the next unattended restart.

---

## STATE

Live: `dsf-ai-task:455`, SHA `16bc0c294fc0c1012ea92a6cd12914cb90d6c31e`, task
`0c731fdcdda349d9a693f8df3933d30e`, booted 2026-07-03T20:41:08Z. Rotation held. Static
fixes shipped and verified. Decode-failure guard proven on its own path. Live mic
discrimination FAILS, root-caused to a routing gap outside today's authorized scope — no
live iteration attempted, per the CMD's own stop condition. Restart forensics filed,
F3 checked and ruled out as this restart's cause, WaveAtlas/hot-save stall remains the
best-supported explanation without full mechanistic proof.

End report.
