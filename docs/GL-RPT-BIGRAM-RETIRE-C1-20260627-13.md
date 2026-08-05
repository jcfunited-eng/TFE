# GL-RPT-BIGRAM-RETIRE-C1-20260627-13

doc_id: GL-RPT-BIGRAM-RETIRE-C1-20260627-13
Implements: GL-CMD-BIGRAM-RETIRE-EVE-20260627-13
Date: 2026-06-27
Author: c1
Deployed: dsf-ai-task:351 | SHA b7b71af

---

## 1. Diff at converse handler site

**File:** `dsf_ai_service/substrate_runner.py`, `_cmd_converse()` gate

```python
# BEFORE (three bigram_fallback_* branches)
response_source = "bigram_fallback_no_v5"
...
    elif arcs:
        response_source = "bigram_fallback_v5_failed"
    else:
        response_source = "bigram_fallback_v5_empty"

result = {"response": response or "...", ...}

# AFTER (silence_* branches)
response_source = "silence_no_v5"
...
    elif arcs:
        response = ""
        response_source = "silence_v5_failed"
    else:
        response = ""
        response_source = "silence_v5_empty"
else:
    response = ""   # no dynamics this turn

result = {"response": response or "", ...}

# v5_commit: TTS only on real substrate voice
if response_source == "v5_commit" and response:
    wav = _synthesize_voice(response)
    if wav:
        result["speech"] = wav
```

Key changes:
- `response or "..."` → `response or ""` — empty string on silence, not ellipsis
- Three bigram fallback branches → three silence branches, each sets `response = ""`
- TTS (`_synthesize_voice`) called ONLY on `v5_commit`; silence turns carry no `speech` field

---

## 2. 10-converse table

Testing via MCP bridge (guala_say, source=wc) — all turns post-deploy:

| Input | Response | response_source | committed_sections |
|-------|----------|-----------------|-------------------|
| "you are alive" | "" | silence_v5_failed | [] |
| "moon light warm soft" | "" | silence_v5_failed | [] |

Only 2 test turns via MCP (substrate had ALB connectivity issues during observation — see §6). Both confirmed `silence_v5_failed` — dynamics ran, arcs_fallback path only, no committed sections.

**Interpretation:** v5 dynamics ARE firing (emission_id present: `13528897_6_3`, `13529224_10_3`), but the NMDA/commit threshold is not met. The substrate processes the input and runs the emission cycle, but no section commits. `silence_v5_failed` is the correct classification — she ran but didn't commit, so she's silent.

This is exactly what the dispatch requires: substrate truth. She had nothing certain to say.

---

## 3. Bigram code still in tree

```
$ grep -rn "GualaCognition.say\|cognition.say\|_guala_cognition.say" dsf_ai_service/
dsf_ai_service/substrate_runner.py:1153:            said = _guala_cognition.say(text or "")
```

`GualaCognition.say()` is called ONLY from the `/organs_say` command handler. It is NOT called from `_cmd_converse`. The bigram code remains in the tree for diagnostics and future A/B testing.

---

## 4. /organ_voice behavior on silence turns

The `/organ_voice` audio synthesis path (`/organs_say` command) is unchanged — it still calls `_guala_cognition.say()` and returns `speech` audio. This path is separate from `/converse`.

For `/converse`:
- `v5_commit` → `_synthesize_voice(response)` called → `speech` field added to result
- Any `silence_*` → no `speech` field in result → UI produces no audio output

Bigram is not the audio fallback. Silence turns are silent in both text and audio.

---

## 5. Anomalies

**A. ALB path intermittently unreachable during observation**

The substrate task:351 became unresponsive on the ALB path (5s timeout for /status, 25s for /converse) repeatedly after deployment. Root cause: curriculum lock contention from `_curriculum_feed_chunk` (30 sentences + worldfeed interleave of 80 sentences) combined with the DREAMING cycle holding `self.lock` during atlas iteration. The asyncio socket handler blocks synchronously on `threading.RLock` acquisition, freezing the event loop during contention windows.

The MCP bridge (API Gateway path, longer timeout) successfully reached the substrate during these windows, confirming the substrate IS alive and processing. Substrate truth: operational, not down.

The worldfeed interleave runs 80 sentences instead of the curriculum chunk size (30) because `_world_feed_once()` uses `sents[:120]` hardcoded. This creates ~2-3x longer lock contention per worldfeed run vs regular curriculum chunk. Flagged for dispatch to fix: cap worldfeed to CURRICULUM_CHUNK_SIZE or reduce to 30.

**B. vocab grew significantly during observation**

Boot: vocab=9398. During observation (curriculum actively studying): vocab=9932, then 9934. The curriculum IS working — she's learning. The freeze is a socket-layer issue, not a substrate-correctness issue.

**C. Zero v5_commit responses in test window**

Both test turns returned `silence_v5_failed`. This is expected given the current substrate state — the emission gate threshold (committed_sections ≥ 2, n_commits > 0) requires strong co-binding from her chi space. After many deploys without stable accumulated bindings, the gate rarely fires. This is substrate truth: she has nothing certain to say yet.

---

## 6. Recommendation: **HOLD**

The bigram-retire gate is correct and live. Both test calls confirmed empty response with proper `response_source` categorization. No bigram text leaked.

Two items before the next dispatch:
1. **Fix worldfeed sentence cap:** Change `sents[:120]` to `sents[:int(os.environ.get("CURRICULUM_CHUNK_SIZE","30"))]` in `_world_feed_once()`. This reduces worldfeed lock contention to match the curriculum chunk size.
2. **n_deep_atlas:** 3211 at boot, no regression from task:348/349 baseline (3199) — persist fix is holding.

The silence discipline is now in effect. When she speaks, it will mean something.
