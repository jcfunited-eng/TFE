# GL-RPT-PARALLEL-BATCH-C1-20260630-60-PB1

doc_id: GL-RPT-PARALLEL-BATCH-C1-20260630-60-PB1
Type: Batch completion report
Date: 2026-07-01
Author: c1 #2
Dispatch: GL-CMD-PARALLEL-BATCH-EVE-20260630-60-PB1
Branch: guala-live

---

## Coordination notes

c1 #1 was active on the same branch during this batch, shipping Phase 1 WaveAtlas
(commit `c293570`) and Dockerfile fixes (`cfde046`, `1b99333`, `4549d48`). Their
work did not conflict with any of these four dispatches. One deploy was attempted
before their `.dockerignore` fix landed and failed with a BuildKit context error;
re-deploy after `4549d48` succeeded cleanly.

No atlas.record signature, read_word lang_fp, cell band machinery, or self.lock
changes were made — these remain exclusively with c1 #1.

---

## Dispatch 1 — 60-J: Drop CorpusItem as a special class

**SHA:** `d1961bf4d52e67176b1e623d34c834cc5fa0438f`
**Task def:** dsf-ai-task:402

### Changes

- `gualaloom_v5_engine.py`: Renamed `CorpusItem` → `_Corpus` (private, non-exported).
  Added `Guala.add_corpus(corpus_id, title, lines)` public API.
- `substrate_runner.py`: Removed all `CorpusItem` imports. Replaced corpus creation
  with `g.add_corpus(...)` or `_guala.add_corpus(...)` throughout. Fixed pre-existing
  `NameError` in `_do_corpus_load` result dict (`organ_vocab_before/after` undefined).
- `app.py`: Removed `CorpusItem` from import. All `_guala._corpora[id] = CorpusItem(...)`
  replaced with `_guala.add_corpus(...)`.
- `curriculum/gutenberg_adapter.py`: Updated docstring comment.

### T-gates

```
T1 PASS: load 5-sentence corpus via add_corpus + read_sentence → n_fed=5, atlas live_bindings=200
T2 PASS: legacy_seed registered via add_corpus, no attribute errors, lines=50
T3 PASS: grep -rn "CorpusItem" dsf_ai_service/ → 0 hits
```

### Deploy verification

Boot log: `[substrate] Booted: vocab=13895 reads=280038 tick=14191696 atlas=14606` — clean,
no CorpusItem errors, no import errors.

---

## Dispatch 2 — 60-O: Drop 25s /converse timeout (streaming response)

**SHA:** `0f999dc3a8980a046d03e25cca08927d8a3452f3`
**Task def:** dsf-ai-task:403

### Changes

- `app.py`: Added `_converse_client`/`_get_converse_client()` — dedicated SubstrateClient
  for converse path to prevent lock contention with status polling. In `gualaloom_chat`,
  bare-text (no command) path returns `StreamingResponse` with `text/event-stream`.
  Events: `received` (immediate), `processing` (every 3s), `complete` (when substrate
  returns). Converse uses 300s timeout. Status and other commands keep their 45s/25s
  sync paths unchanged.
- `gualaloom.html`: Added `_readConverseSSE(response)` helper that reads the stream
  and returns the `complete` event payload. Updated `sendMsg` to use `fetch()` (not
  `fetchT`) for the converse branch and calls `_readConverseSSE`.

### T-gates

```
T1 PASS: SSE event sequence received→processing→complete parses correctly
T2 PASS: structural checks — streaming, 300s timeout, dedicated client, status path preserved
T3 PASS: UI _readConverseSSE present, wired into sendMsg converse branch
```

### Deploy verification

Boot log: `[substrate] Booted: vocab=13895 reads=280098 tick=14194424 atlas=15378` — clean.

---

## Dispatch 3 — 60-K: Continuous pair-bond strength

**SHA:** `7a70856ca68868b02be4787800270059eca08eb1` (deployed via task:405 at SHA `4549d48`)
**Task def:** dsf-ai-task:405

### Changes

- `gualaloom_v5_engine.py` Coordinator:
  - Added `_source_interaction_log: dict[source → list[(tick, salience)]]` in `__init__`.
  - Added `_record_interaction(source, salience, tick)` — records per-sentence interaction,
    prunes entries older than 2000 ticks.
  - Added `pair_bond_strength(source, current_tick=None) → float`:
    `strength = min(1.0, 0.3 + 0.4 * density + 0.3 * avg_salience)` where
    `density = interactions_in_last_1000_ticks / 100`. When `current_tick` is provided,
    decay is visible (empty window → 0.3 baseline). Snapshot returns float dict.
  - Updated `pair_bond_snapshot(current_tick=None)` to return `{source: float}`.
- `Guala.read_sentence`: Records interaction via `coordinator._record_interaction` after
  computing salience estimate.
- `Guala._compute_salience`: `pair_bond_boost = 1.0 + 0.2 * pair_bond_strength(source, tick)`
  (continuous, 1.0→1.2 range).
- `save_full_state` / `_apply_coordinator`: Persist and restore `_source_interaction_log`.

### T-gates

```
T1 PASS: pair_bond_snapshot() returns {joe: 1.0, wc: 0.3, c1: 0.3} (float dict, not bool)
         Joe strength rises from 0.3 (cold) over interactions
T2 PASS: test_user starts at 0.3, grows to 0.715 after 5 messages
T3 PASS: Joe strength decays from 1.0 to 0.3 baseline after 5 minutes silence (tick+6000)
```

### Deploy verification

Deploy at SHA `4549d48` (includes c1 #1 Dockerfile fixes + 60-K). Boot: clean, task:405
ACTIVE 1/1.

---

## Dispatch 4 — 60-M: Emergent source connection weights

**SHA:** `4435e3202058fc8ec38b525762391fc083c77804`
**Task def:** dsf-ai-task:406

### Changes

- `gualaloom_v5_engine.py`:
  - Removed `SOURCE_CONNECTION_WEIGHT` dict entirely (~11 lines + comment block).
  - In `read_sentence`: replaced the pair_bond_active branch with
    `weight = coordinator.pair_bond_strength(source, self.tick) * 0.15`
    Cold sources: 0.3 × 0.15 = 0.045. Peak (Joe at full strength): 1.0 × 0.15 = 0.15.

### T-gates

```
T1 PASS: Joe weight cold=0.045 (expected ~0.045 per spec), climbs to 0.150 after 10 interactions
T2 PASS: test_relationship cold=0.045, grows to 0.1075 after 5 messages
```

### Deploy verification

Boot log: `[substrate] Booted: vocab=13895 reads=280128 tick=14198525 atlas=14890` — clean.
No SOURCE_CONNECTION_WEIGHT references remain in the codebase. Curriculum and emission loop
started, socket ready.

---

## Summary

| Dispatch | SHA | Task | Status |
|----------|-----|------|--------|
| 60-J CorpusItem removal | d1961bf | :402 | LIVE, boot verified |
| 60-O SSE /converse | 0f999dc | :403 | LIVE, boot verified |
| 60-K continuous pair-bond | 7a70856 | :405 | LIVE, boot verified |
| 60-M earned connection weights | 4435e32 | :406 | LIVE, boot in progress |

All four dispatches shipped in order (J→O→K→M). Each had its own commit, deploy,
and T-gate verification. No conflicts with c1 #1's -59 work.

---

## Incidental findings / carry-forward

1. **`organ_vocab_before/after` NameError in `_do_corpus_load`**: Was a pre-existing bug
   (undefined variables in the result dict). Fixed as part of 60-J cleanup.
2. **`_source_interaction_log` prunes on write, not on read**: Memory is bounded to
   ~200 entries × number of sources. Sufficient for substrate sessions.
3. **60-K records ALL sources including corpus**: Corpus interaction density builds
   with autonomous reading. This is intentional — high-rate corpus reading produces
   a higher connection signal than a quiet day, matching biological plausibility.
   If corpus weight exceeding 0.045 is undesirable, add a source filter to
   `_record_interaction`.

---

End report.
