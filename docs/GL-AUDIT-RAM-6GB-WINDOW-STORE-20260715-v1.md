# GL-AUDIT: 6.1 GB RAM — Window Store, Not ML — 2026-07-15 v1

## Question
Joe observed ~6.1 GB resident memory on the Guala substrate task and suspected
a hidden ML model.

## Verdict
**No ML.** The memory is the substrate's own experience-window store, held in
RAM twice, dominated (97.5%) by 79 giant audio-listening episode windows.

## Evidence chain (all measured live on task dsf-ai-task:640, image b9ddc3d, 2026-07-15 03:40–04:20 UTC)

1. **Single process.** The whole footprint is one python3.11/uvicorn process:
   RSS 6,527,504 kB (~6.2 GiB) at 04:00, 6,584,404 kB at 04:08 (~6 MB/min
   ongoing growth). Task allocation is 16 GB.

2. **Not model weights.** `/proc/1/smaps_rollup`: 6,489,212 kB anonymous
   (Python heap), only 37 MB file-backed. Only native libraries mapped are
   numpy's OpenBLAS + gfortran. Independent code audit: the Dockerfile installs
   `fastapi uvicorn python-multipart numpy pandas cryptography Pillow
   pillow-heif PyMuPDF boto3 websockets python-flint` — zero ML packages; no
   torch/tensorflow/transformers/sklearn/spacy/onnx/faiss imports anywhere in
   the shipped code. The `anthropic` import in narrator.py is inside
   try/except and the package is not installed → dead code. No `openai` usage
   in the service at all. The 1.4 GB diary on EFS is *not* memory-resident
   (only streamed on demand by the events-histogram endpoint).

3. **Boot-time load, not a leak.** Process started 03:40 UTC; already at
   6.5 GB by ~03:52. The WindowManager WAL restore
   (`substrate/window_manager.py::restore_from_wal`) replays the entire
   closed-window store into RAM at startup.

4. **The store itself (measured in-container, read-only side process):**
   - WAL dir `guala_windows_wal`: 7 segments, 1.415 GB, only 1,469 records.
     Two generations on disk (gen 13 ≈ 707 MB stale duplicate of gen 14).
   - Current generation (what RAM holds): **708 MB JSON, 742 windows,
     957,008 entries.**
   - Breakdown by window kind:
     | kind | bytes | windows | entries |
     |---|---|---|---|
     | episode:attending_audio | 690,495,442 (97.5%) | 79 | 950,376 |
     | language | 17,194,801 | 644 | 6,519 |
     | live-conversation | 229,731 | 19 | 113 |
   - Largest single window: `win_…015d` (episode:attending_audio:3355078),
     **33,894 entries, 24.3 MB as JSON**. Median record 28 KB; p90 5.4 MB.
   - Per-entry anatomy: ~774 B JSON each, of which ~581 B is the `provenance`
     dict (affect snapshot, scene, episode refs, bundle ids) duplicated on
     every entry.
   - Measured JSON→Python-object expansion factor: **3.95×**
     (deep-sizeof over a full segment).

5. **Why audio windows are giant** (`v4/gualaloom_v5_engine.py::_atick_attending_audio`,
   ~line 11346): every activity tick while attending a sound loops over *all*
   cochlear bands and calls `window_manager.add_entry(...)` once per band —
   deliberate reinforcement-on-re-attend, but each reinforcement is a **new
   appended entry**, not an in-place strengthening. ~30 bands × hundreds/
   thousands of ticks per listen → ~12k entries average per audio episode.

6. **Held twice.** On restore *and* on every close, the full record is also
   `copy.deepcopy`-ed into `_compatibility_windows` — the atlas-side recall
   authority mirror (Eve's recall-matrix-mirror fix, GL-FIX-RECALL-MATRIX-
   MIRROR-EVE-20260705). deepcopy shares immutable leaves (strings/numbers)
   but duplicates every dict/list container; measured cost ≈ +2.6× the source
   JSON bytes on top of the primary store.

7. **Held a third time (partially).** At boot,
   `_rebuild_language_fact_memory_from_windows` (engine ~:14264) takes a full
   deepcopy snapshot of the store (transient) and permanently retains one
   LanguageFactStrand (frozen dataclass, ~2-6 KB heap: trit tuples, event
   tuples, DSF, sha256 strings) per qualifying word entry — data-dependent,
   est. 0.3–1.5 GB.

8. **No eviction.** There is no cap, pruning, TTL, or lazy-loading of closed
   windows anywhere in WindowManager; `DECAY_PAUSED=1` besides. The store is
   monotonic. (Cross-check: open contexts are NOT part of the problem —
   live manifest shows 0 open contexts.)

9. **Atlases are innocent.** Measured expansions: living atlas 15 MB × 2.83
   ≈ 42 MB; deep atlas 47 MB × 3.56 ≈ 167 MB; wave atlas ≈ 30–70 MB.
   Combined well under 300 MB.

## Arithmetic check
708 MB JSON × 3.95 ≈ 2.8 GB (`_windows`) + ~1.8 GB (deepcopy mirror,
containers only) + ~0.25 GB (chi_index: one small dict per entry × 957k)
+ 0.3–1.5 GB (language-fact strands) + ~0.25 GB (atlases) + organism pickle
expanded + interpreter/numpy baseline ≈ **5.6–6.8 GB** — brackets the
observed 6.53 GB RSS.

## Risk posture
Not an emergency: 6.5 of 16 GB used, growth ~6 MB/min while active. But the
store only grows; every future listening session adds MB-scale windows ×2
copies, and every restart re-parses the full WAL (slower boots). A sustained
audio-study phase would move the OOM horizon materially closer.

## Fix options (routed, NOT shipped — all touch recall semantics)
1. **Reinforce-in-place** for identical (motif, band, chi) bindings within the
   same episode window: bump a count/weight instead of appending a new entry
   per band per tick. Attacks 97.5% of the bytes at the source. Changes what
   recall sees (one weighted entry vs thousands of duplicates) — needs Eve's
   ruling on whether entry multiplicity is load-bearing for recall/first-wrap.
2. **Compact provenance**: the 581 B provenance dict per entry is largely
   identical across a window; interning/sharing it would cut entry cost ~4×
   without changing entry counts.
3. **Lazy closed-window store**: keep chi_index + metadata in RAM, load full
   records from the WAL on recall demand. Biggest structural win, biggest
   change.
4. **Narrow the mirror**: the deepcopy doubling is Eve's design (recall
   authority); only she should rule on sharing vs copying.

Also housekeeping: stale WAL generation 13 (~707 MB) sits on EFS beside gen 14
and should be reaped by the next compaction/restore; worth verifying it
actually is.

## Addendum (multi-agent deep sweep, same day)

Five independent tracing agents cross-checked the above; the ranking holds
(window store + copies ≈ 75–85% of heap). New confirmed details:

- **The mirror is never read by recall.** In-code comment at the per-close
  deepcopy site (window_manager.py:778): "Atlas receives a detached
  compatibility copy. Recall never reads it." So option 4 (narrowing the
  mirror) is lower-risk than assumed — the copy exists for legacy readers of
  `atlas.windows`, not for the recall path. Still Eve's design; her call.
- **Boot-transient triple-copy inflates RSS.** At boot, the language-fact
  rebuild takes `window_manager.snapshot()` — a third full deepcopy — then
  `json.dumps` the entire store into one throwaway multi-hundred-MB string.
  CPython's allocator rarely returns those arenas, so ~1–3 GB of the RSS is
  high-water-mark bloat, not live objects. Fixing the snapshot-based rebuild
  would cut RSS without touching recall data at all.
- **No cap exists even in name:** `MAX_CLOSED_WINDOWS` appears only in a
  comment (engine:3544), never in code.
- Organism pickle expands to ~0.45 GB; substrate ring ceiling ~0.3–0.4 GB;
  both minor. The sweep's "open contexts ~0.15–0.19 GB" claim is WRONG —
  live manifest measured 0 open contexts (the 27 MB manifest bulk is the
  legacy-format `data` payload, not leaked contexts).
- Generation ambiguity resolved empirically (see §4): live store = gen 14
  = 708 MB; gen 13 (~707 MB) is a stale on-disk duplicate.

## Addendum 2 — corrections + fixes shipped (same night, after cross-session handoff)

Cross-checked against GL-RPT-WAL-BLOAT-RAM-ROOT-CAUSE-C1-20260715-v1 (the
concurrent session's independent 3-reader verification). Two corrections to
this document:

- **Gen 13 is NOT stale.** Compaction deliberately retains the previous
  generation as crash fallback until the next compaction (window_manager
  `_compact_locked` deletes only generations below the previous). The
  "should be reaped" housekeeping note above is withdrawn. The real disk
  issue is different: compact() runs unconditionally every ~30 min cold
  save, rewriting the full ~707 MB store each time (their finding F3).
- **My "0 open contexts" rebuttal was wrong.** My probe read the manifest's
  top level; open_contexts sit under the envelope's `data` wrapper. The
  concurrent session verified live: 170 never-closed contexts / 30,507
  entries / 24.5 MB re-embedded in the manifest every ~60 s save, caused by
  the close guard requiring the closing thread's bound contextvar (their
  finding #2 / fix direction F2). The sweep agent was right; my correction
  is retracted.

Fixes shipped this night (verified, 94 tests pass, measured on
production-shaped state):

- **Mirror retired (F1, empty-sentinel variant)**: ~1.7 GB retained cut.
- **Boot rebuild without snapshot() (option 5)**: ~3.6 GB transient
  allocation per boot cut.

Still open, in priority order: F2 (cross-thread close guard — also the
mechanism that lets attending episodes grow without end), F3 (divergence-
gated compaction), lazy closed-window store (RAM prune without deleting any
memory — needs recall-latency design), reinforce-in-place for per-tick
audio band entries (changes learning semantics — Eve), F4 robustness items.

— c1, 2026-07-15
