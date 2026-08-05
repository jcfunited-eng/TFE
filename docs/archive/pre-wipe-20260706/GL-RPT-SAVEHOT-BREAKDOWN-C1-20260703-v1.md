> **SUPERSEDED — DO NOT TREAT AS CURRENT TRUTH.**
> This document describes substrate state as of pre-wipe (2026-07-06
> wipe operation, GL-RPT-SUBSTRATE-WIPE-INCIDENT-C1-20260706-v1).
> The substrate described here no longer exists. Preserved as
> historical record only.
> For current substrate state, run the harness against production.

---

# GL-RPT-SAVEHOT-BREAKDOWN-C1-20260703-v1

doc_id: GL-RPT-SAVEHOT-BREAKDOWN-C1-20260703-v1
From: c1a | To: Eve | Date: 2026-07-03 (~02:55Z)
Responds to: Eve GO item (2) — hot-lane per-file breakdown for one [save-hot]; T1 ruling input.
Method: READ-ONLY in-container sampler (mtime/size of the 8 hot files + their .tmp,
0.3 s cadence, 150 s window spanning THREE hot-save cycles, task :451). Nothing changed.

---

## THE NUMBER THAT DECIDES T1

**`guala_core.json` is 41,612,749 bytes, and 41,458,195 of them (99.6%) are one key:
`deep_survival_history`.** Everything else the hot lane writes totals ~2.95 MB across
7 files. Per-key breakdown of guala_core.json (verbatim, in-container):

```
  41,458,195  deep_survival_history
     149,486  vocab
       2,867  corpora_state
       1,481  open_response_windows
         526  target_familiarity
         136  source_history
        ~40   (7 scalar fields)
total 41,612,749
```

`deep_survival_history` is the (chi|section|motif → last-10 strengths) map — deep-store
physics data riding the HOT lane, rewritten in full every ~65 s.

## PER-FILE BREAKDOWN (cycle 3 of 3, richest sampling; sizes exact, seconds from
mtime deltas at 0.3 s resolution)

| # | file | bytes | write time | note |
|---|------|-------|-----------|------|
| 1 | guala_core.json | 41,613,741 | **~3.6–4.7 s** | .tmp observed growing 3.1→41.6 MB, ~11–12 MB/s (provisioned-EFS line rate); rename at +136.61 s |
| 2 | guala_needs.json | 252 | ≤0.05 s | |
| 3 | guala_coordinator.json | 1,254,113 | ~0.23 s | |
| 4 | guala_bucket.json | 186 | ~0.04 s | |
| 5 | guala_visual.json | 1,512,941 | ~0.21 s | |
| 6 | guala_sounds.json | 6,231 | ~0.20 s | |
| 7 | guala_videos.json | 171 | ~0.35 s | 0-byte .tmp moment sampled |
| 8 | guala_teaching.json | 178,462 | ~0.09 s | written after the main loop |

Files 2–8 combined: ~2.95 MB, ~1.2 s. File 1 is the lane.

## PAIRING WITH THE PRINTS (same cycles, verbatim)

```
02:44:09 | [save-hot] 10.64s core=10.61s compact=0.03s
02:45:14 | [save-hot]  5.22s core=5.21s  compact=0.02s   ← sampled cycle 1 (rename 02:45:14)
02:46:20 | [save-hot]  5.57s core=5.56s  compact=0.01s   ← sampled cycle 2
02:47:26 | [save-hot]  6.36s core=6.27s  compact=0.08s   ← sampled cycle 3
```

Steady state is now **5.2–10.6 s** (the 13.9–38.5 s in the first post-boot window was
cold EFS; it settled by ~02:25Z). Budget within a 5–6 s save: ~3.6–4.7 s writing the
41.6 MB core + ~1.2 s the other seven files + serialize-under-lock, **plus** the
vocab-regression guard, which `json.load`s the ENTIRE existing 41.6 MB core from EFS
every cycle just to read one length — a read that shrinks with the same fix.

## T1 IMPLICATION (input only — Eve rules)

T1 is <5 s; steady state straddles it at 5.2–10.6 s, and every second of the overage
is `deep_survival_history`. If that key moves to the cold lane (it is deep-store
physics data; sections/atlas/deep_atlas already live there) or gets bounded, the hot
lane becomes ~150 KB core + ~2.95 MB siblings ≈ **well under 1 s**, and the guard read
collapses with it. No change made — fix shape only.

Cycle cadence observed: one hot save per ~65.5 s (60 s sleep + ~5.5 s save), three
consecutive cycles, no failures, no .tmp orphans left behind.

End report.
