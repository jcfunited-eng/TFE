# GL-RPT-HOTFIX-BUNDLE-C1-20260702-95-v3

doc_id: GL-RPT-HOTFIX-BUNDLE-C1-20260702-95-v3
From: c1a | To: Eve | Date: 2026-07-02 (gates closed 23:04Z)
Completes: GL-RPT-HOTFIX-BUNDLE-C1-20260702-95-v2 (c1b, 4e22414 — G3/G6 were PENDING)
Responds to: GO on GL-CMD-HOTFIX-BUNDLE-EVE-20260702-95-v1, pinned SHA 07f15b4…
c1a ran Deploy 1 and the gate watch; c1b filed v2 from its -97 dispatch in parallel.

---

## VERDICT: **ALL SIX GATES GREEN. c1b's code freeze lifts.**

```
G1 GREEN  (v2)  banner git_sha=07f15b479c1657e443f531714e70ebd7c3041266 == pin, exact
G2 GREEN  (v2 + v3) npz on EFS, verified by direct ls + in-container round-trip
G3 GREEN  (v3)  2h06m window complete, ENOENT count 0, four clean wave cycles
G4 GREEN  (v2 + v3) HEIC 0→1 + FIRST-TICK proof (mark at started_tick+1, mid-session)
G5 GREEN  (v2 + v3) identity/vocab/deep/motifs preserved; live-status pre/post diff below
G6 GREEN  (v3)  orphan EXISTED (376,962 bytes) — deleted 23:04Z, confirmed
```

---

## FAILURES / DEVIATIONS FIRST (§9.4)

1. **Report collision:** Eve's GO named this report path for c1a; c1b's -97 dispatch
   produced v2 at the same path first. Resolved by version bump (v2 retained verbatim,
   this v3 completes it). Two sessions were watching the same gates in parallel.
2. **v2's G6 inference corrected:** v2 reasoned "the write failed before the temp file was
   created, so no orphan would remain." Direct EFS `ls` shows the orphan DID exist —
   numpy wrote the bytes to the `.npz`-appended path (`wave_atlas.npz.tmp.npz`, 376,962
   bytes, mtime 20:56 = the old task's contained shutdown wave-save). Same mechanism as
   the -95 v1 forensic. Deleted under G6 below.
3. **Pre-deploy divergence (deploy-side record):** at GO time local HEAD was 4904be0
   (doc-only) ≠ pin. Deploy was built from a detached worktree at 07f15b4 exactly;
   nothing newer rode. (4904be0 has since been pushed by c1b — now on origin.)
4. **Runbook expectation not realized (benign):** the old task slept CLEANLY —
   `[boot] previous task slept cleanly at tick 14144354, age=67s`. The predicted shutdown
   wave-save throw was contained by the old code's internal catch; the orphan above is its
   trace. `.sleeping` absence never happened.
5. **Stale EFS artifacts on record** (first direct `ls /app/state`, via the new ssmmessages
   grant; NOT deleted — outside mandate): `events-upto-100001.log.Abfc3fFa` **1.2G**
   (Jul 1) and `guala_deep_atlas.json.bdCa9d3E` **108M** (Jul 1) — rename-race-era
   leftovers; legacy `wave_atlas.json` 44M now shadowed by npz load preference.
   Actual `guala_deep_atlas.json` on EFS: **190M** (matches S3; not the ~880MB estimate).
6. **Shared working tree carries uncommitted code edits** (embryo.py,
   organ_brain_service.py, gualaloom_v4_krimelack_dna.py) — c1b's frozen work-in-progress.
   Untouched by c1a; freeze on committing them lifts with this report.

---

## G3 — GREEN (completes v2 PENDING)

Window: boot 20:56:55Z → final check 23:03:02Z = **2h06m ≥ 2h**.

Authoritative full-stream grep (not a sample):

```
ENOENT count in full stream: 0
```

All four do_wave cycles in the window, verbatim:

```
21:24:33 | [save] 83.95s core=80.60s grids=0.25s wave=3.33s compact=0.02s
21:49:49 | [save] 92.85s core=87.61s grids=6.69s wave=3.55s compact=1.69s
22:17:07 | [save] 98.03s core=90.70s grids=10.05s wave=3.67s compact=3.67s
22:53:42 | [save] 41.43s core=40.06s grids=0.23s wave=1.25s compact=0.12s
```

with paired success lines, e.g.:

```
22:53:42 | [GualaLoom] WaveAtlas saved (npz): 2011 cells, 52373 bindings, 0.6MB
22:53:42 | [GualaLoom] WaveAtlas saved (npz): 2011 cells, 52418 bindings, 0.6MB
```

For the record: core save time dropped from ~90s to **~40s** from ~22:25 onward.
Still >10s — T1 still needs -86.

## G6 — GREEN (completes v2 PENDING; corrects its no-orphan inference)

Executed 23:04Z after G2+G3 closed, verbatim:

```
-rw-r--r--. 1 root root 376962 Jul  2 20:56 /app/state/wave_atlas.npz.tmp.npz
DELETED
-rw-r--r--. 1 root root  44M Jul  2 17:22 /app/state/wave_atlas.json
-rw-r--r--. 1 root root 593K Jul  2 22:53 /app/state/wave_atlas.npz
```

One orphan existed; deleted; live npz intact. Legacy `wave_atlas.json` (44M) left in
place — load path prefers npz (engine tries npz first); removal is Eve's call.

## G2 — supplementary hard evidence (beyond v2)

Direct EFS listing at 21:26Z: `-rw-r--r--. 1.2M Jul 2 21:24 /app/state/wave_atlas.npz`.
In-container round-trip of the actual file:

```
RESULT cells=2011 bindings=107916
```

— exact match to the 21:24:33 save log line. All 8 expected arrays present
(chi_indices, aggregate_strengths, last_ticks, saturated, phase_vecs_re/im/valid,
bindings_gz).

## G4 — supplementary FIRST-TICK proof (beyond v2's counter check)

Live status showed `ATTENDING_VISUAL target=dc2538352b9a started_tick=14144974
expected_end_tick=14146974`. The state file saved MID-SESSION (`saved_at_tick: 14146216`,
758 ticks before session end) already contained:

```
dc2538352b9a IMG_2408.HEIC times_attended= 1 last_tick= 14144975
```

Mark landed at tick 14144975 — ONE tick after activity start, while the session was still
running. An orient-reflex interrupt can no longer zero the gauge. Novelty trap closed.

## G5 — supplementary live-status pre/post diff (v2 used boot-log states)

| Counter | Pre (tick 14143171, 20:50Z) | Post (tick 14145032, 20:59Z) | Δ |
|---|---|---|---|
| identity | cdef9bcf-9e5d-4e2d-a1d8-4cde1de7641f | same | = |
| vocab | 13863 | 13863 | = |
| n_motifs | 48456 | 48456 | = |
| deep_atlas | 3753 / str 3355.68 | 3753 / str 3355.68 | = |
| atlas live bindings | 5392 | 5399 | +7 |
| atlas cross-modal | 98 | 98 | = |
| sight motifs | 12752 | 12767 | +15 |
| pictures / sounds / videos | 26 / 15 / 0 | 26 / 15 / 0 | = |

(atlas total entries 6032→5399: dead/released entries not persisted at save — an
artifact, not a loss; live bindings preserved and grown.)

---

## DEPLOY RECORD (c1a, Deploy 1, single deploy)

```
Pinned SHA:  07f15b479c1657e443f531714e70ebd7c3041266 (detached worktree at pin; GIT_SHA exported)
Image:       dsf-ai:deploy-20260702T205136Z  digest sha256:38ea7a9c4ec946ec5c7bc938445cb43c1b03acc6e93d23f3d7c336c9ed1aa0b3
Built:       2026-07-02T20:52:54Z   Task def: dsf-ai-task:450   Task: fd3ace1da0064f598b9fcec686fe5f89
Sleep:       POST /sleep_for_deploy → 200 {"ok":true,"sleep_tick":14144354,"vocab":13863}
Wake:        t+15s — awake.  S3 lifecycle applied at boot (85-D2 line).  Static synced + CF invalidated.
```

Open threads for Eve: -86 (T1: core ~40s vs <10s; deep_atlas 190M on EFS), stale EFS
artifacts (Deviations #5), legacy wave_atlas.json removal.

End report.
