# GL-RPT-WAL-BLOAT-RAM-ROOT-CAUSE-C1-20260715-v1

**From:** c1 (this session) — findings handed off to the Fable 5 session that owns the RAM-bloat + boot work, per Joe's direction 2026-07-15.
**Status:** ROOT CAUSE VERIFIED (3 independent code readers; one verified against the live production task via ECS Exec, read-only). A partial fix was started by this session and then **reverted uncommitted** when Joe reassigned the work — the working tree is clean of it. The reverted partial diff is preserved off-tree if wanted (scratchpad `wal-fix-partial-REVERTED-20260715.patch`, this session).
**Scope:** binding-window WAL disk bloat (~1.4GB and growing), 19.9MB/3.8s hot saves, 6.1–6.5GB RSS / 9GB save spikes.

## Verified findings (live production numbers, 2026-07-15)

1. **Two full store generations on disk BY DESIGN.** Cold-lane save (`app.py` `_periodic_v6_save`, every ≥30 min → `gualaloom_v5_engine.py:13775` `save_full_state` → `window_manager.compact()` **unconditionally**) rewrites the ENTIRE closed-window store (~707MB, 744 windows, avg ~0.95MB/record) as a fresh base segment, generation++, while holding `self.lock`. `_compact_locked` (`window_manager.py:1157`) deletes only generations **below the previous** — previous+current are both kept as crash fallback. Live WAL dir: 1.4GB / 1,485 record lines / 7 files. ~10–15GB/day EFS write churn. The design comment "compaction on the rarer cold-save path" is false in production — it runs every 30 minutes regardless of divergence.

2. **Stuck-open context leak — the real cause of the 19.9MB / 3819ms "hot" save.** `snapshot_incremental` embeds the full record of every OPEN context in the manifest every ~60s save. Live: **170 never-closed contexts, 30,507 entries, 24.5MB** — dominated by 4 `episode:episode:attending_audio:*` contexts (up to 8,910 entries / 7MB each) plus 162 leaked `implicit:` contexts. Root cause: the close path's guard requires the closing thread's bound contextvar (`self._bound_context`) to still reference the context — never true when close fires from a different thread than open (autonomy-tick vs converse threads). These windows can NEVER close; they grow unbounded (a single window record can reach 16MB — one WAL line, since window records have no size bound and each entry carries a ~1–2KB provenance blob).

3. **RAM: closed windows held twice; one copy is provably dead weight.** `WindowManager._compatibility_windows` is a full `copy.deepcopy` duplicate of every closed record (`window_manager.py:778` at close; `:885-886` and `:1362-1363` on both restore paths). Its ONLY reader is `manager_for_compatibility_mirror` (`:324-333`) which compares mapping **identity** (`is not mirror`), never content; `recall_query.py:137-141` resolves the manager once, never scans the mirror. Measured cost ≈ **0.65GB**. Store itself: ~300–320MB canonical JSON → ~1.2–1.3GB as Python dicts (measured 4.07× inflation; provenance dicts dominate — ~17 keys stamped per entry at `:644-661`). chi_index ~0.1GB. Windows subsystem ≈ 2.0GB of the 6.1GB steady RSS.

4. **9GB save spikes:** `snapshot()` transiently deepcopies the whole store AND builds the full sorted-JSON string; `language_fact` rebuild structures are a partial fourth copy of window content (`engine :2620-2627`, `:4571-4592`); pymalloc/glibc never return the spike to the OS.

5. **Observability/orphan gaps:** `_delete_wal_generations` swallows every `os.remove` OSError silently (`window_manager.py:967-970`, no log/counter). Orphan `.tmp` base files from a crashed compaction are never cleaned (parse filter excludes them, `:915-916`) and the S3 backup mirrors them. The S3 backup path also `f.read()`s each segment fully into RAM (a 707MB read), gzips in RAM, and uploads BOTH generations (~1.4GB per backup cycle; latest S3 backup predates the WAL deploy so this cost has not landed yet).

6. **Boot path is CORRECT today** (manifest → `restore_from_wal` → `_wal_base_written=True`; no per-save recompaction; the legacy 220MB snapshot was folded exactly once on the first post-deploy save; boot prunes to ONE generation via `keep=generation` at `:1379`).

7. **Unbounded growth is real and separate:** nothing ever prunes a closed window from `self._windows` — store grew 670MB→707MB in 75 min (~0.7GB/day). Pruning = deleting her memories = **Joe's call, not a mechanical fix**; flagged to him 2026-07-15, no decision yet.

## Fix directions this session had validated (not implemented — yours to take or reject)

- F1: stop deep-copying into `_compatibility_windows` (shallow refs to the same immutable records, or empty sentinel; preserve the identity-based API). Records are write-once after close per the WAL design's own invariant — verify no caller mutates before sharing.
- F2: fix the cross-thread close guard so a REAL boundary close succeeds regardless of closing thread (mechanical bug fix; no TTL/timeout policy — that would be fabricated cognition). Already-leaked live contexts should then close at their next real boundary.
- F3: make `compact()` conditional on real divergence (records/bytes appended since base; keep `force=True` for the boot-migration fold in `snapshot_incremental`'s `_wal_base_written=False` path). Preserves the crash-fallback invariant (prev generation retained until the manifest pointing at the new one is durable — comment at `:1152-1156`).
- F4: log deletion failures; clean stale `.tmp` at boot (provably safe point); exclude `.tmp` from the S3 mirror set; stream the S3 segment reads instead of whole-file `f.read()`.

Crash-safety caution for any change here: the restore contract is that the manifest's `(generation, durable_count, digest)` must always find a complete matching generation on disk. This codebase has a documented history of lock-free write races (wave-atlas decay series) — audit `_lock`/`_wal_lock` ordering on any new path.
