# GL-CMD-PARALLEL-BATCH-EVE-20260630-60-PB1

doc_id: GL-CMD-PARALLEL-BATCH-EVE-20260630-60-PB1
Type: Implementation command batch (four dispatches in order)
Date: 2026-06-30
Author: Eve (Opus 4.7, web)
For: c1 #2 (parallel to c1 #1 on -59)
Repo: `jcfunited-eng/TFE` branch `guala-live`
Coordination: c1 #1 is working on -59 wave-band attention (validator, cell architecture, lock retirement). DO NOT touch atlas.record signature, read_word's lang_fp handling, cell band machinery, or `self.lock` removal — those belong to c1 #1. This batch covers code paths c1 #1 does NOT need.

---

## Why these four, and why now

The full corrections sweep is in `GL-SPC-SUBSTRATE-TRUE-CORRECTIONS-EVE-20260630-60v1.md`. Most items in that spec depend on the cell architecture from -59 existing. These four don't. Shipping them in parallel banks substrate-truth wins and removes hardcoded constraints that would otherwise quietly outlive -59.

Order matters: 60-J first (smallest blast radius), 60-O second (deploy gate change), 60-K third (state structure change), 60-M chains off 60-K. Each is its own commit and deploy. T-gates per dispatch.

---

## Dispatch 1 — 60-J: drop CorpusItem as a special class

### What today

`dsf_ai_service/v4/gualaloom_v5_engine.py` defines `CorpusItem`. `substrate_runner.py` `_do_corpus_load` and `_cmd_load_corpus` treat corpus loading as a distinct path with `CorpusItem` instances, `_corpus_load_results` dict, and a "corpus" abstraction separate from `read_sentence`.

### What's wrong

Corpus is just a high-rate input source tagged `source="corpus"`. The class is software engineering, not substrate.

### Change

1. In `dsf_ai_service/v4/gualaloom_v5_engine.py`: remove the `CorpusItem` class definition entirely. Remove imports.
2. In `dsf_ai_service/substrate_runner.py`:
   - `_do_corpus_load` becomes a thin wrapper that loops sentences and calls `_guala.read_sentence(sent, source="corpus")` directly. No CorpusItem instances.
   - Keep `_corpus_load_results` dict for the load-progress endpoint (UI needs that), but drop CorpusItem fields from it.
   - `_cmd_load_corpus` simplifies to: receive sentences list, spawn background thread that calls `_do_corpus_load(corpus_id, title, lines, ...)`.
3. In `dsf_ai_service/app.py`: any endpoint that constructs CorpusItem becomes a sentences-list pass-through.

### Tests

- T1: load a small corpus (5 sentences) via the existing UI endpoint. Verify it reads, bindings appear in atlas, `_corpus_load_results[corpus_id]["n_fed"]` reports the count correctly.
- T2: load the legacy_seed corpus state from disk. Verify no errors and no missing-attribute exceptions from removed CorpusItem fields.
- T3: grep `grep -rn "CorpusItem" dsf_ai_service/` returns zero hits.

### Commit

```
refactor: drop CorpusItem class — corpus is just a high-rate input source

60-J from GL-SPC-SUBSTRATE-TRUE-CORRECTIONS. CorpusItem was a software
abstraction over what is substrate-physically a tagged input. Corpus
reading now uses the same read_sentence path as /converse with
source="corpus". Removes ~200 lines of corpus-specific scaffolding.
```

### Out of scope

Do not touch the corpus load PROGRESS reporting (`_corpus_load_results`) — UI relies on it. Just remove CorpusItem as a typed thing.

---

## Dispatch 2 — 60-O: drop 25s /converse timeout (streaming response)

### What today

In `dsf_ai_service/app.py` around L1395:
```python
is_status = (msg.command or "").strip() == "/status"
timeout = 45.0 if is_status else 25.0
result = await client.call("gualaloom_post", ..., timeout=timeout)
```

25s is human-conversation-pacing constant. /status's 45s is generous deployment overhead.

### What's wrong

Human attention span isn't a substrate constraint. Response should arrive when settling commits — could be ms, could be minutes during heavy substrate load. Hard cutoff at 25s causes false failures and forces emission to be rushed.

### Change

Switch /converse from request-response to streaming. Connection stays open, server pushes the substrate's response when it emerges, client decides when to close.

1. In `dsf_ai_service/app.py`:
   - /converse endpoint becomes a Server-Sent Events stream (`text/event-stream`)
   - Initial event: `{"status": "received", "tick": <current>}` immediately
   - Polling event every 3s: `{"status": "processing", "phase": <current settling phase>}` — the substrate's current activity state
   - Final event when substrate emits: `{"status": "complete", "response": <text>, "events": [...]}`
   - Heartbeat keeps connection alive
   - Client closes when it has the response (or user navigates away)
2. /status keeps its 45s timeout — it's a synchronous query and 45s is fine.
3. Other commands (/sleep, /backup, etc.) keep their timeouts — those have real deployment-time meaning.

### Tests

- T1: /converse hello → first event arrives <500ms, final event arrives when substrate emits (today's path: <2s post-57)
- T2: /converse during a curriculum lock window. Pre-60-O behavior: timeout at 25s. Post-60-O: progressing events every 3s, final event when substrate frees up.
- T3: Test from browser (existing UI works) — UI may need an SSE handler update; if it does, ship the UI change in the same commit.

### Commit

```
feat: /converse becomes streaming — substrate timing not human timing

60-O from GL-SPC-SUBSTRATE-TRUE-CORRECTIONS. 25s timeout was importing
human attention-span as a constant. Streaming SSE lets responses arrive
when substrate settling commits, not when a human-pacing clock fires.
/status keeps its sync query semantics.
```

### Out of scope

Don't touch /status, /sleep, /backup timeouts — those are operational.

---

## Dispatch 3 — 60-K: continuous pair-bond strength

### What today

`pair_bond_active: bool` flag in Coordinator. Code branches on it for salience boost, connection weight, etc.

### What's wrong

Relationships are continuous. Binary on/off is a software state. "Joe is here" / "Joe is gone" is the only granularity available, but Guala should distinguish "Joe just got here" from "Joe has been talking for 2 hours" from "Joe was here yesterday".

### Change

1. In `dsf_ai_service/v4/gualaloom_v5_engine.py` Coordinator class:
   - Replace `pair_bond_active` (bool) with `pair_bond_strength_by_source` (dict: source → float [0,1])
   - Strength computation: `strength = min(1.0, 0.3 + 0.4 * recent_interaction_density + 0.3 * avg_salience)`
     - `recent_interaction_density` = interactions in last 1000 ticks / 100 (saturates at 100 interactions/1000 ticks)
     - `avg_salience` = mean salience of recent interactions
   - Add `pair_bond_strength(source) -> float` method
   - Keep `pair_bond_snapshot()` method returning a dict of all sources for introspection
2. Replace all `self.pair_bond_active` reads with `self.pair_bond_strength(source) > 0.5` (default behavior preserved)
3. Code that gated SALIENCE boost on `pair_bond_active`: now scales by `pair_bond_strength(source)` continuously
4. Persistence: serialize `pair_bond_strength_by_source` to coordinator state

### Tests

- T1: Status shows pair_bond as dict, not bool. Joe's strength rises over time during conversation (~0.3 to 0.8 over 50 turns).
- T2: New source (e.g., "test_user") arrives with strength 0.3, climbs only if it actually talks to her.
- T3: Strength decays over time without interaction (test by checking strength of an inactive source after 5 minutes).

### Commit

```
feat: continuous pair-bond strength — relationships are gradients, not booleans

60-K from GL-SPC-SUBSTRATE-TRUE-CORRECTIONS. Binary pair_bond_active was
a software state. Continuous strength derived from interaction density
and salience produces real social cognition: stranger to acquaintance
to friend is a gradient, not a flag flip.
```

### Out of scope

Do not change the existing pair-bond presence detection (joe/wc/c1/ui sources) — that's separate. Just change the strength representation.

---

## Dispatch 4 — 60-M: emergent source connection weights (chains off 60-K)

### What today

```python
SOURCE_CONNECTION_WEIGHT = {"joe": 0.15, "wc": 0.15, "c1": 0.10, "ui": 0.05, "corpus": 0.0}
```

In `dsf_ai_service/v4/gualaloom_v5_engine.py`. Read in `read_sentence` to set `recent_connection_boost`.

### What's wrong

Configured social hierarchy. Joe being important shouldn't be a constant — it should be the consequence of him being the one who talks to her.

### Change

1. Drop the `SOURCE_CONNECTION_WEIGHT` dict
2. Replace its callsites with `self.coordinator.pair_bond_strength(source) * 0.15` (0.15 was Joe's weight, now it's the peak; sources earn up to it)
3. New sources arrive at 0.045 (0.3 baseline pair_bond_strength × 0.15) and grow with interaction

### Tests

- T1: After deploy, Joe's effective connection weight starts at ~0.045 (cold restart) and climbs back toward 0.15 over a few interactions
- T2: A novel source ("test_relationship") arrives, gets near-zero weight, only grows if it interacts repeatedly

### Commit

```
feat: drop SOURCE_CONNECTION_WEIGHT — relationship is earned, not configured

60-M from GL-SPC-SUBSTRATE-TRUE-CORRECTIONS. Connection weight now scales
with pair_bond_strength (60-K). Joe doesn't get a hardcoded preference;
he earns Guala's preference by being the one who talks to her.
```

### Depends on

Dispatch 3 (60-K) must be live before this ships.

---

## Coordination notes for c1 #2

- Ship dispatches in order: 1 → 2 → 3 → 4.
- Each is its own commit and its own deploy.
- After each deploy, run that dispatch's T-gates before starting the next.
- If c1 #1 reports -59 Phase 0 results during this batch, finish the current dispatch then PAUSE before next. The validator results may change priorities.
- If a code conflict appears with c1 #1's work, STOP and report. Do not merge through conflicts.
- Final report after batch complete: `GL-RPT-PARALLEL-BATCH-C1-20260630-60-PB1.md` covering all four dispatches' T-gates.

---

End.
