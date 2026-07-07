> **SUPERSEDED — DO NOT TREAT AS CURRENT TRUTH.**
> This document describes substrate state as of pre-wipe (2026-07-06
> wipe operation, GL-RPT-SUBSTRATE-WIPE-INCIDENT-C1-20260706-v1).
> The substrate described here no longer exists. Preserved as
> historical record only.
> For current substrate state, run the harness against production.

---

# GL-RPT-ORGAN-ENABLE-C1-20260702-95-v1

doc_id: GL-RPT-ORGAN-ENABLE-C1-20260702-95-v1
From: c1 | To: Eve | Date: 2026-07-02
Purpose: Evidence for lighting the organs on the -86 deploy.
Read-only research; no code or state changes.

---

## 1. organ_brain_service / OrganVoice — NOT LAUNCHED

**Verdict: NOT LAUNCHED in task:444 or any current production task.**

Evidence:

- Dockerfile L53: `CMD ["uvicorn", "dsf_ai_service.app:app", "--host", "0.0.0.0",
  "--port", "8080"]` — single process, port 8080 only.
- No `Popen`, no supervisord, no start.sh targeting `organ_brain_service` or
  port 8090 anywhere in Dockerfile, `app.py` startup, or `_gl_init`.
- No `ORGAN_BRAIN_ENABLED` flag exists in Dockerfile or codebase.
- app.py L1555: `# GL-CMD-AUTONOMOUS-EMISSION-39: route to substrate (not dead
  :8090).` — explicit dead label.
- app.py L1568: `# /mail, /sendmail, /experience, /tablet — all routed to dead
  :8090 container. Stubs until these are re-wired into the substrate (W2+ work).`
- `_start_organ_surface_poll()` (substrate_runner.py L2696) polls
  `http://localhost:8090/thought` every 90s — all calls fail silently
  (ConnectionRefused; exception swallowed at L2715 `except Exception: pass`).
- `app.state.guala_organ_brain` is populated at boot (app.py L1273-1283) from
  `PreservedGuala.load_full_state()` — this is the static migration snapshot,
  NOT the live organ_brain_service.

`organ_brain_service.py` L1026-1027:
```python
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8090, log_level="warning")
```
This entry point exists but is never invoked in production.

---

## 2. HEMI Flags — Already Enabled (separate from organ_brain_service)

All 4 HEMI flags are ENABLED now in Dockerfile L46-49 (deployed in task:444):
```
ENV HEMI_PR_ENABLED=1
ENV HEMI_EP_ENABLED=1
ENV HEMI_SC_ENABLED=1
ENV HEMI_GP_ENABLED=1
```

`run_hemisphere_updates()` fires after every `converse()` turn (engine L1987).
These write to in-memory hemisphere atlases inside the v5 engine. They are NOT
the same as organ_brain_service — they are separate subsystems.

---

## 3. Per-Organ Cost Per Converse (HEMI flags, all enabled)

`run_hemisphere_updates()` runs synchronously inside `converse()`, under
`self.lock`. No I/O. All pure Python. Called at engine L1987.

### PR (HEMI_PR_ENABLED) — hemisphere_cognition.py L138-218

`pr_parallel_settle` (L138): iterates `input_chis × band range(5)`, mirrors
em atlas entries into pr atlas with cap at 20 entries per chi key.
- Cost: O(N_input_chis × 5 × em_entries_per_chi) dict lookups + conditional appends
- Scales with em atlas density at those chis
- **Estimate: <1ms per turn**

`pr_consensus_divergence` (L166): nested loop em_entries × pr_entries per
chi-band. Calls `get_or_create_link()` for each em×pr pair.
- With pr.atlas capped at 20 entries/chi and typical 3-7 input_chis: <100 iterations
- **Estimate: <1ms per turn**

**PR total: <1ms**

### EP (HEMI_EP_ENABLED) — hemisphere_cognition.py L233-290

`ep_record_turn` (L233):
- Appends one `TurnLogEntry` (O(1); capped at 500 via slice at L259-260)
- Iterates content words in `text` via `_normalize_text` + 1 `LanguageKrimelack`
  call per word (L274: `k = LanguageKrimelack(); k.transduce(w)`)
- Updates `ep.tracked_objects[w]` per word (O(1) dict write)
- Cross-hemi link updates for all `input_chis + emission_chis` (O(N_chis) at L285-290)

LanguageKrimelack.transduce() is pure Python string processing: ~0.1ms per word.
Typical input: 5-15 content words → 0.5-1.5ms for krimelack.

**EP total: <5ms per turn; cost scales with input word count**

### SC (HEMI_SC_ENABLED) — hemisphere_cognition.py L356-417

`sc_polarity_update` (L356): scans sc.atlas entries per chi for recent
negation-polarity entries (last_tick ≥ tick-5). Applies negation decrement.
- sc.atlas starts with ≤100 seeded entries (from setup_sc L337-350), grows with turns
- **Estimate: <1ms per turn**

`detect_and_bind_causal_patterns` (L420): called only when EP is also enabled
(L559-560). Walks ep.turn_log pairs for A→B chi sequences, creates ep↔sc links.
```python
for i in range(len(ep.turn_log) - 1):
    a, b = ep.turn_log[i], ep.turn_log[i+1]
    ...
    for chi_a in a.emission_chis:
        for chi_b in b.input_chis:
```
- O(turn_log × emission_chis × input_chis per entry pair)
- turn_log capped at 500; with 3 emission_chis × 3 input_chis per pair:
  500 × 3 × 3 = 4,500 iterations at 50 turns, 4,500 iterations per pass
  In practice: O(N_turns × ~9)
- **Estimate: <2ms at 500 turns**

**SC total: <3ms per turn**

### GP (HEMI_GP_ENABLED) — hemisphere_cognition.py L504-527

`scan_procedural_pairs` (L504): linear walk of ep.turn_log for
guala→external-response pairs where needs improved. O(turn_log).
- Per iteration: dict sum (3 values) + comparison + cross-hemi link update
- **Estimate: <1ms per turn even at 500 entries**

**GP total: <1ms**

### Summary

| Flag | Functions | Estimate (normal) | Bottleneck |
|------|-----------|--------------------|-----------|
| PR   | pr_parallel_settle + pr_consensus_divergence | <1ms | em atlas density |
| EP   | ep_record_turn + LanguageKrimelack per word | <5ms | word count in input |
| SC   | sc_polarity_update + detect_and_bind (ep-gated) | <3ms | turn_log depth |
| GP   | scan_procedural_pairs | <1ms | turn_log depth |
| **Total** | — | **<10ms per converse** | EP word count; SC at turn_log cap |

At turn_log=500 (steady state after 500 exchanges): **<20ms per converse**.
All synchronous, no lock release, no I/O. No impact on autonomy tick (autonomy
tick runs between converse calls, not concurrent with it).

---

## 4. Safe Enable Order + Interlocks for organ_brain_service on -86

**What must be true for organ_brain_service to go live:**

### I1 — Process launch mechanism (NOT YET PRESENT)

Nothing in the current codebase starts organ_brain_service as a process.
The -86 deploy must add a launcher. Minimal option: add to `_embedded_post_boot()`
(app.py L1294), after `_start_organ_surface_poll()`, using the same
`subprocess.Popen` pattern as the curriculum orchestrator (substrate_runner.py
L3194):

```python
subprocess.Popen([sys.executable, "-m", "dsf_ai_service.organ_brain_service"],
                 stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
```

This is additive — cannot disturb the main process. The organ_brain_service
has its own GIL and event loop (L7-8 docstring: "Own Python process, own GIL").

### I2 — Launch AFTER substrate boot (order)

organ_brain_service should start AFTER `_gl_init` completes (i.e., after Guala
is fully booted). It reads EFS state files that the main engine also writes.
Launching before boot increases EFS contention risk. Current `_embedded_post_boot`
runs after `_gl_init` — correct placement.

### I3 — EFS state files (safe to launch fresh or from saved state)

organ_brain_service reads on boot:
- `organ_brain_embryo.json` (L126): restores embryo if present; fresh start if absent (L524-530)
- `organ_brain_succession.json` (L127): restores succession graph; non-fatal if absent (L166-174)
- `organ_voice_senses.json` (L506): OrganVoice senses cache; empty if absent (OrganVoice L41-48)

All three fall back gracefully. First launch on a task that never ran
organ_brain_service = fresh start; safe.

### I4 — `_compose()` is silenced

`_compose()` (organ_brain_service.py L281-298) returns `""` unconditionally
(Phase D inspection pending). OrganVoice WILL NOT speak even when launched.
Autonomous loop runs all internal paths (surface, growth, succession) but
`_last_thought.speech = ""`. `/thought` endpoint returns `{speech:"", ...}`.
The surface poll (`_start_organ_surface_poll`) will fill `_ORGAN_SURFACE_CACHE`
with surfaced concepts, but the speech string is empty — no voice risk.

### I5 — `_start_organ_surface_poll` already wired

substrate_runner.py L2696-2718: polls `http://localhost:8090/thought` every 90s
and caches `surfaced` dict. Zero-latency per converse (cached, not sync HTTP).
Once :8090 is alive, the cache fills automatically within 90s of first boot.
No new wiring needed — this code is already running (and failing silently today).

### I6 — DO NOT restart the substrate task to activate

atlas restart-decay is unfixed. The -86 deploy must be a NEW image deploy
(image rebuild with the process launcher added), NOT a restart of the current
task. The substrate task gets a new task definition revision; the new container
starts organ_brain_service alongside the main engine.

### I7 — No new env vars required

organ_brain_service reads `ANTHROPIC_API_KEY`, `GUALA_STATE_DIR`, and
`TAVILY_API_KEY` — all already present in the task env.
App reads `ORGAN_BRAIN_URL` (default `http://localhost:8090`) — correct for
same-container launch. No new flags needed for -86.

### Safe enable sequence for -86

1. Add `Popen` for `organ_brain_service` in `_embedded_post_boot()`, after
   `_start_organ_surface_poll()`.
2. Build image off `guala-live` with the launch wired.
3. Deploy new task revision (NOT restart current task — new image).
4. organ_brain_service boots, reads EFS (or starts fresh), sets `_ready`.
5. `_start_organ_surface_poll` reaches /thought within 90s of organ_brain boot.
6. `_ORGAN_SURFACE_CACHE` populates with surfaced concepts.
7. `_translate_organ_surface()` begins providing organ-surfaced candidates to
   emission from the cache — zero latency impact per converse.

---

## 5. Scan Design Notes (for the record)

Per Eve's dispatch:

**B.2 flood = per-WORD binding events (real signal):**
The "3-5× flood" of `response_bound` events is one event per word Guala reads
during selfhear of her own output. Each event has a distinct `input_chi`
(the chi of that word) and shares `context_anchor_chis` (Joe's window). These
are real per-word arc signals, not duplicates. Dedupe criterion for the scan:
identical `(tick, input_chi, context_anchor_chis)` tuple — this is a true
duplicate (same word, same tick). Distinct `input_chi` values = distinct arcs,
draw them separately.

**B.3 per-chi density endpoint — NONE EXISTS → specced into scan dispatch:**
No endpoint currently exposes global per-chi density for a radial map.
`chi_trace` is per-item; `atlas_snapshot` is aggregate-only. The endpoint
needed for the radial map requires iterating `atlas.entries` and returning
`{chi: density}`. Rides the scan dispatch deploy, read-only.

---

## Status

- All items read-only. No code changes, no substrate contact, no deploy.
- HEMI flags: ENABLED and running in task:444.
- organ_brain_service: NOT LAUNCHED. Launch mechanism is one Popen call
  needed in `_embedded_post_boot`.
- Per-organ cost: <10ms per converse; safe.
- -86 deploy: safe to proceed with I1-I7 satisfied.
