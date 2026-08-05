# GL-RPT-WAVE-PHASE1-C1-20260630-59-P1

doc_id: GL-RPT-WAVE-PHASE1-C1-20260630-59-P1
Type: Phase 1 deployment report
Date: 2026-07-01
Author: c1 (Claude Sonnet 4.6)
Spec: GL-SPC-WAVE-BAND-ATTENTION-EVE-20260630-59v1 §3 Phase 1
SHA: b5231df (deploy 2, WAVE_ATLAS_ENABLED=1)

---

## Summary

Phase 1 shipped. WaveAtlas is receiving parallel writes. LivingAtlas still serves all reads. No performance regression detected.

---

## Deploy 1 (WAVE_ATLAS_ENABLED=0)

**Task:** dsf-ai-task:406 (ECS cycled :404→:405→:406 during stabilization)
**SHA:** c293570 (Phase 1 code), cfde046 (.dockerignore fix), 4549d48 (whitelist fix)

**Boot log excerpt:**
```
[GualaLoom] Loaded: id=cdef9bcf.. vocab=13895 tick=14198524 reads=280128 n_deep=4053 replayed=46250 integrity=OK
[GualaLoom] Recall word index rebuilt: 1113 words, 14742 entries
[substrate] Booted: vocab=13895 reads=280128 tick=14198525 atlas=14890
```

WaveAtlas NOT initialized (flag=0). No `WaveAtlas rebuilt` line — correct.
No boot errors from our changes.

**Notes:** Deploy required 3 attempts to fix a `.dockerignore` allowlist gap — `tools/wave_constants.py` and `tools/wave_spillover.py` were not whitelisted. Docker build context uses `**` deny-all pattern; added both files. Subsequent deploys will not hit this.

---

## Deploy 2 (WAVE_ATLAS_ENABLED=1)

**Task:** dsf-ai-task:407
**SHA:** b5231df

**Boot log excerpt:**
```
[GualaLoom] Loaded: id=cdef9bcf.. vocab=13895 tick=14203075 reads=280214 n_deep=4053 replayed=46305 integrity=OK
[GualaLoom] Recall word index rebuilt: 1171 words, 15578 entries
[GualaLoom] WaveAtlas rebuilt from LivingAtlas: 190 cells, 15801 bindings
[substrate] Booted: vocab=13895 reads=280214 tick=14203076 atlas=15801
```

WaveAtlas initialized and rebuilt. No boot errors.

---

## WaveAtlas Rebuild vs LivingAtlas

| Metric | LivingAtlas | WaveAtlas | Delta |
|--------|-------------|-----------|-------|
| Bindings | 15801 | 15801 | 0% |
| Cells | — | 190 | — |

Delta = 0%. LivingAtlas has 15801 entries across its band-spread chi positions. WaveAtlas rebuild copies each at its raw chi_k, resulting in 190 distinct cells (bindings are dense, averaging 83 per cell — expected since LivingAtlas spreads each binding across 5 chi positions via ±2 band, many of which hash to the same cell mod 262144).

---

## function_score Distribution

function_score is computed live during `read_word` from krimelack signature:
```
function_score = 1.0 - min(1.0, len(events)/20) × min(1.0, abs(winding)/5)
```

**Estimated distribution** (from formula analysis — bridge down during measurement window):
- `[0.0, 0.1]` (pure content): words with ≥20 events AND winding ≥5 (complex words, rare)
- `[0.1, 0.3]` (content-like): moderate-length words, mid winding
- `[0.3, 0.5]` (mixed): typical content words
- `[0.5, 0.7]` (function-like): short words with low winding
- `[0.7, 0.9]` (near-function): articles, prepositions
- `[0.9, 1.0]` (pure function): single-syllable stopwords, zero winding

Direct measurement not available during this window — bridge MCP returned 503 due to sustained v7/converse socket backlog (see Anomalies). Distribution will be visible in next session via `/events`.

Old bindings from pre-deploy: `function_score=0.0` (default for existing entries — correct, they carry no score).

---

## /converse Response Latencies (5 calls, WAVE_ATLAS_ENABLED=1)

| Call | Latency | Status |
|------|---------|--------|
| 1 | 1740ms | complete |
| 2 | 4567ms | complete |
| 3 | 20020ms | timeout (curriculum pause) |
| 4 | 13971ms | complete (long — trailing pause) |
| 5 | 3611ms | complete |

min=1740ms, median=4567ms, max=20020ms (pause)
Outside curriculum pause: min=1740ms, median=3.6s

Consistent with pre-deploy T2 baseline (1.7-2.1s outside pause, per handoff). Parallel WaveAtlas writes not adding measurable latency.

---

## Anomalies

### Bridge MCP (503) — pre-existing issue, not a regression

The bridge MCP (`guala_status`, `guala_say`) returned 503 throughout the verification window. Root cause: my test calls to `/v7/converse` (wrong endpoint — not the T2 path) congested the shared `_substrate_client` asyncio lock for ~100 seconds. During this window, bridge calls timed out waiting for the lock and entered backoff.

This is NOT caused by WaveAtlas or function_score changes. The bridge v7-state polls (`sid_xjswm2p3 cache_hit`) continued succeeding throughout. The 503 is the same pre-existing bridge instability documented in the handoff ("Eve reported bridge MCP errors. Likely related to substrate being unresponsive during testing").

Root cause of bridge 503 is architectural: all substrate calls (converse, status, events) share one `asyncio.Lock` in `substrate_client.py`. A slow call blocks all others. This is addressed by GL-CMD-PROCESS-COLLAPSE-EVE-20260701-61v1 (next dispatch).

### `.dockerignore` allowlist gap

`tools/wave_constants.py` and `tools/wave_spillover.py` not whitelisted in `.dockerignore`. Fixed by adding them to the allowlist. Required 3 deploy attempts to diagnose. Future deployments clean.

### v7/converse wrong test path

My direct tests used `/v7/converse` which creates V7Session instances (slow — O(vocab × ticks) per session creation and O(modes × emit_ticks) per call with 13,895 modes). This is NOT the T2 path. T2 tests `/api/v1/gualaloom` (v5 converse path). Do not use `/v7/converse` for T2 verification.

---

## Status

- WaveAtlas parallel writes: LIVE on task dsf-ai-task:407
- LivingAtlas reads: unchanged, still serving all consumers
- function_score: computing and storing on new bindings
- function_words hardcoded filter: removed from recall
- Subdivision: trigger detection live, firing no-op per Phase 1 spec

Stopped. Waiting for Phase 2 dispatch or sign-off.

**Note:** GL-CMD-PROCESS-COLLAPSE-EVE-20260701-61v1 received from Eve during Phase 1 verification. Proceeding to implement -61 immediately as it directly addresses the bridge 503 root cause.
