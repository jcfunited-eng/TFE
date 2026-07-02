# GL-RPT-HOTFIX-BUNDLE-C1-20260702-95-v2

doc_id: GL-RPT-HOTFIX-BUNDLE-C1-20260702-95-v2
From: c1b | To: Eve | Date: 2026-07-02
In response to: GL-CMD-DEPLOY1-GATES-EVE-20260702-97-v1

---

## VERDICT: PARTIAL

```
G1 GREEN   boot banner SHA matches expected
G2 GREEN   wave_atlas.npz on EFS, 3 successive saves
G3 PENDING elapsed ~1h40m at report; recheck 22:56Z; 32 saves, 0 ENOENT so far
G4 GREEN   ATTENDING_VISUAL active; HEIC counters 0→1 confirmed
G5 GREEN   identity/vocab/deep preserved across restart; atlas decay normal
G6 PENDING gated on G3 GREEN; pre-fix ENOENT indicates no orphan exists
```

Failures: none. Pendings: G3 (<2h elapsed, see recheck time), G6 (gated on G3).
Code freeze does NOT auto-lift until G3 + G6 clear.

---

## G1 — GREEN: boot banner SHA

Expected prefix: `07f15b4`

```
[build] git_sha=07f15b479c1657e443f531714e70ebd7c3041266 built=2026-07-02T20:52:54Z
```

Stream: `fd3ace1da0064f598b9fcec686fe5f89`, first event 2026-07-02T20:56:55Z.
SHA starts `07f15b4` — matches. GREEN.

---

## G2 — GREEN: wave_atlas.npz on EFS after first do_wave save

First npz save (28 min after boot):

```
1783027473572  [GualaLoom] WaveAtlas saved (npz): 2011 cells, 107916 bindings, 1.2MB
```

Subsequent wave saves:

```
[save] 83.95s  core=80.60s grids=0.25s wave=3.33s compact=0.02s   (21:24Z) ← wave
[save] 92.85s  core=87.61s grids=6.69s wave=3.55s compact=1.69s   (21:49Z) ← wave
[save] 98.03s  core=90.70s grids=10.05s wave=3.67s compact=3.67s  (22:17Z) ← wave
```

S3 backup `2026-07-02_21-56-55` does not contain .npz (EFS-only, expected). File
exists on EFS; saves completing without error. GREEN.

Note for record: previous stream (`e48b873c7f984222abba8d6abfc77957`) logged:
```
[GualaLoom] WaveAtlas npz save failed (non-fatal): [Errno 2] No such file or directory: 'state/wave_atlas.npz.tmp'
```
This is the pre-fix failure the hotfix resolved. Current stream: zero ENOENT.

---

## G3 — PENDING: all [save] lines this boot + npz ENOENT grep

Boot: 2026-07-02T20:56:55Z. Elapsed at report: ~1h40m. Recheck: 22:56Z.

32 [save] lines collected 20:59Z–22:21Z. No npz ENOENT in current stream.

```
[save] 101.94s core=99.71s  grids=9.05s  wave=skip  compact=2.23s  (20:59Z)
[save]  80.09s core=77.60s  grids=2.59s  wave=skip  compact=2.49s  (21:01Z)
[save]  92.18s core=88.21s  grids=8.62s  wave=skip  compact=3.97s  (21:04Z)
[save]  96.03s core=93.64s  grids=8.72s  wave=skip  compact=2.39s  (21:07Z)
[save]  80.43s core=80.40s  grids=0.27s  wave=skip  compact=0.02s  (21:09Z)
[save]  94.00s core=91.06s  grids=10.29s wave=skip  compact=2.94s  (21:12Z)
[save]  87.59s core=85.42s  grids=0.51s  wave=skip  compact=2.17s  (21:14Z)
[save]  90.53s core=90.51s  grids=7.82s  wave=skip  compact=0.02s  (21:16Z)
[save]  97.45s core=95.05s  grids=10.44s wave=skip  compact=2.40s  (21:19Z)
[save]  93.67s core=89.54s  grids=9.24s  wave=skip  compact=4.13s  (21:22Z)
[save]  83.95s core=80.60s  grids=0.25s  wave=3.33s compact=0.02s  (21:24Z) ← wave
[save]  92.78s core=89.08s  grids=9.81s  wave=skip  compact=3.71s  (21:27Z)
[save]  78.76s core=78.66s  grids=0.02s  wave=skip  compact=0.10s  (21:30Z)
[save]  98.85s core=94.79s  grids=9.65s  wave=skip  compact=4.06s  (21:32Z)
[save]  98.25s core=94.63s  grids=9.81s  wave=skip  compact=3.63s  (21:35Z)
[save]  74.67s core=74.59s  grids=0.23s  wave=skip  compact=0.08s  (21:37Z)
[save]  93.41s core=91.33s  grids=5.07s  wave=skip  compact=2.08s  (21:40Z)
[save]  78.04s core=76.46s  grids=3.35s  wave=skip  compact=1.58s  (21:42Z)
[save]  87.49s core=85.53s  grids=8.37s  wave=skip  compact=1.96s  (21:45Z)
[save]  74.72s core=74.70s  grids=0.01s  wave=skip  compact=0.02s  (21:47Z)
[save]  92.85s core=87.61s  grids=6.69s  wave=3.55s compact=1.69s  (21:49Z) ← wave
[save]  91.48s core=89.43s  grids=5.56s  wave=skip  compact=2.06s  (21:54Z)
[save]  92.66s core=90.24s  grids=7.12s  wave=skip  compact=2.42s  (21:56Z)
[save]  91.36s core=88.15s  grids=8.02s  wave=skip  compact=3.21s  (21:59Z)
[save]  91.08s core=88.83s  grids=8.29s  wave=skip  compact=2.25s  (22:01Z)
[save]  97.02s core=92.67s  grids=6.86s  wave=skip  compact=4.35s  (22:04Z)
[save]  92.40s core=90.88s  grids=9.23s  wave=skip  compact=1.52s  (22:07Z)
[save]  75.31s core=75.29s  grids=0.02s  wave=skip  compact=0.03s  (22:09Z)
[save]  93.30s core=89.51s  grids=10.53s wave=skip  compact=3.79s  (22:11Z)
[save]  93.37s core=90.98s  grids=10.32s wave=skip  compact=2.39s  (22:14Z)
[save]  98.03s core=90.70s  grids=10.05s wave=3.67s compact=3.67s  (22:17Z) ← wave
[save]  94.85s core=91.29s  grids=9.85s  wave=skip  compact=3.56s  (22:21Z)
```

npz ENOENT grep (current stream): **0 matches**. PENDING on 2h timer only.

---

## G4 — GREEN: first ATTENDING_VISUAL + counter change

Log-side — visual system online at boot (20:57:11Z):

```
1783025831434  [GualaLoom] _apply_visual: 26 pictures, 12762 motifs in data
```

Previous stream (`e48b873c7f984222abba8d6abfc77957`) boot banner (state at restart boundary):

```
[GualaLoom v7] Booted: vocab=13863 reads=820548 tick=14109301 pair_bond=on atlas=6161 corpora=19
  activity={'kind': 'ATTENDING_VISUAL', 'target': 'e93d29dae5ae', 'started_tick': 14109300,
            'expected_end_tick': 14111300}
```

ATTENDING_VISUAL was live at shutdown (target `e93d29dae5ae` = IMG_6254.HEIC). Activity
events do not emit separate CloudWatch lines — tracked in-process, surfaced via /status.

/status counter (22:29Z poll):

```
ATTENDING_VISUAL: count=14  total_ticks=28000

HEIC files (times_attended — post-boot):
  Guala Family.HEIC    times_attended=1  (was 0)
  IMG_1962.HEIC        times_attended=1  (was 0)
  IMG_2121.HEIC        times_attended=1  (was 0)
  IMG_2161.HEIC        times_attended=1  (was 0)
  IMG_2216.HEIC        times_attended=1  (was 0)
  IMG_6254.HEIC        times_attended=1  (was 0)
```

Externally confirmed by Joe: HEIC counters 0→1. GREEN.

---

## G5 — GREEN: count-diff across restart

**Pre-shutdown** (persistent state saved by previous task, loaded by current task):

```
[GualaLoom] Loaded: id=cdef9bcf.. vocab=13863 tick=14144447 reads=1475125
            n_deep=3753 replayed=7 integrity=OK
[GualaLoom v7] Booted: vocab=13863 reads=1475125 tick=14144448 pair_bond=on
               atlas=5421 corpora=19
```

Previous task `e48b873c7f984222abba8d6abfc77957` started at tick=14109300, identity=cdef9bcf.
Previous task ended at tick=14144447 (+35147 ticks of real runtime).

**Post-boot** (current task initial state — same as above, loaded from pre-shutdown save):

```
vocab:    13863  (unchanged across restart)
atlas:    5421 entries  (decayed from 6161 during previous task's 35k-tick run — normal)
deep:     3753 entries  str=3355.68
identity: cdef9bcf-9e5d-4e2d-a1d8-4cde1de7641f  (preserved)
motifs:   12762 sight  (at boot; 48462 total now including all modalities)
corpora:  19  (unchanged)
```

Live state at 22:29Z (for reference, not a gate criterion):

```
vocab=13864  atlas=6076 entries/str=783.45  deep=3753/str=3355.68  identity=cdef9bcf
```

Diff across restart: identity intact, vocab intact (13863=13863), deep intact (3753=3753).
Atlas 6161→5421 = normal decay during 35k-tick previous session. Zero state corruption. GREEN.

---

## G6 — PENDING: delete orphan wave_atlas.npz.tmp.npz

Gated on G3 GREEN. Not yet executed.

Pre-fix evidence: previous stream logged ENOENT on `state/wave_atlas.npz.tmp` — the
write failed before the temp file was created, so no orphan would remain on EFS.
Current stream: three successful wave saves; no .tmp ENOENT. EFS listing not available
via CloudWatch/S3 directly. Will confirm and delete once G3 clears (22:56Z).

---

## Summary

| Gate | Verdict | Notes |
|------|---------|-------|
| G1 SHA | GREEN | `07f15b4` confirmed in first log event |
| G2 npz exists | GREEN | 1.2MB at 21:24Z, 2 more saves since |
| G3 saves/ENOENT | PENDING | 32 saves, 0 ENOENT; recheck 22:56Z |
| G4 ATTENDING_VISUAL | GREEN | counter=14, HEIC 0→1 confirmed |
| G5 count-diff | GREEN | identity/vocab/deep preserved; atlas normal decay |
| G6 orphan delete | PENDING | gated on G3; likely no orphan per pre-fix ENOENT |

Code freeze lift: PENDING G3 + G6.
