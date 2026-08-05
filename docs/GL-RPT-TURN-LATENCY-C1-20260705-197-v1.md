# GL-RPT-TURN-LATENCY-C1-20260705-197-v1

doc_id: GL-RPT-TURN-LATENCY-C1-20260705-197-v1
From: c1a | To: Eve, Joe, c1b | Responds to:
`GL-CMD-TURN-LATENCY-EVE-20260705-197-v1`. P2/P3/P4 built. P1 is
c1b's (no build, verification only) — not mine to run. A real,
unrelated bug found and fixed along the way, named honestly below.

## A bonus finding, fixed: `/events` was completely dead in production

While trying to live-verify `-196` (the emulator-everywhere build) by
watching for `organism_experience_bound` events during a live Secret
Garden re-read, the `/events` endpoint returned `{"events": []}` no
matter what — even though `/status` showed real, ongoing progress
(vocab growing, tick advancing, corpus reading). Traced it to **two
separate `@app.get("/api/v1/gualaloom/events")` route definitions**
in `app.py` — an early, incomplete stub (`return {"events": []}`
unconditionally in embedded mode — the production config) registered
*before* the real, fully-built implementation (since/stream support,
real embedded-mode `_guala.get_recent_events()` call). FastAPI/
Starlette matches routes in registration order — the stub always won,
silently shadowing the real one for every request, this whole time.
Not caused by tonight's work; found only because I actually tried to
observe an event live instead of trusting the trigger's own response.
Fixed: removed the dead stub, and the surviving route now honors the
`n` query param loomscan.html already sends (previously silently
ignored, coincidentally harmless because loomscan's own `n=50` matched
the route's hardcoded default). Swept the rest of `app.py` for other
duplicate route registrations — none found.

## P2 — reply released before self-hear (both converse paths)

`_converse_phased()` (the actual live path — `CONVERSE_PHASED=1` in
the deployed task-def) and the non-phased `converse()` fallback both
restructured identically: Phase 7 (engine state writes) still runs
synchronously (cheap, local), then a `converse_reply_released` event
logs the real foreground latency and the function returns the reply
immediately. Self-hear (Phase 8) and the hemisphere-update block
(Phase 9) now run in a daemon background thread — the exact pattern
`_self_hear`'s own step 4 (self-voice injection) already used, not a
new mechanism. `SELF_HEARING_ENABLED` is still checked inside
`_self_hear` itself, untouched.

**Verified directly, not assumed**: monkeypatched `_self_hear` to
sleep 1.5s and forced a real (non-"...") reply — `converse()` returned
in **25.6ms**, while the simulated self-hear was still running in the
background for another ~1.47s. The reply is provably not gated on
self-hear completing.

`converse_timing`'s shape is preserved (same fields P1's audit
expects) but now fires from the background thread once self-hear/hemi
finish, with `total_ms` reporting the **foreground-only** duration
(what Joe actually waited) and new `background_ms`/
`released_before_selfhear` fields making the deferred cost visible
without it counting against perceived latency.

## P3 — one transduction pass per turn (both converse paths)

The reply text was transduced with fresh `LanguageKrimelack`s three
times per turn: once for `committed_chis` (Phase 7), again inside
`_self_hear` (its own reply-chi computation), and again for
`emission_chis` (the hemisphere-update block) — three passes over
the *same word list* producing *identical, deterministic* chi values.
Now computed once at Phase 7 (`reply_chis`) and threaded through:
`_self_hear(reply, source, reply_chis=reply_chis)` (new optional
param, `None` default preserves old standalone-caller behavior
exactly) and directly into `run_hemisphere_updates(...)`. Zero
behavior change — same values, computed once instead of three times.

## P4 — last-dream marker

`self._last_real_dream_tick` (new, `None` until her first real dream):
stamped in `_run_dream_cycle` at the exact point a real dream tick
executes (alongside the existing `_dream_executed_this_cycle = True`
and `dream_pressure` discharge — same gate, no new mechanism).
Persisted in both `save_hot_state` and `save_full_state`'s existing
`snap_needs` block (same envelope `dream_pressure` already uses —
"needs-state, same class," per the dispatch). Restored in
`_apply_needs`, which now also prints
`[dream-marker-restore] last_real_dream_tick=... dream_pressure=...`
on every boot — the log line X3 asks for.

**Verified directly**: `save_full_state` → fresh `Guala()` →
`load_full_state` round-trip. `_last_real_dream_tick` (set to a
sentinel value) and `dream_pressure` (set to 0.55) both survived
exactly, and the boot log line fired with the correct restored
values.

## What this does NOT claim

I did not attempt P1 (that's explicitly c1b's, no build) — ten live
`converse_timing` events post-deploy, `save-hot` timing, and the
post-reboot emission-section-commit check item are for whoever fires
this window to gather and report. X1's "p95 under 2000ms" number is
therefore not in this report — it needs live traffic after deploy,
not a synthetic local test.

## Verification

Full `test_brain`/`test_neuron`: 23/23. `probe_188_scene_lanes.py`:
4/4 (unaffected). Broader engine suite: 20/20. `py_compile` clean on
every touched file. Direct local proof for P2 (reply released 60x
before simulated slow self-hear completes), P3 (code-level: single
`reply_chis` computation site, threaded through both downstream
consumers — traced by direct reading, not a noisy call-count
microbenchmark which proved too confounded by unrelated transduction
elsewhere in the turn to isolate cleanly), P4 (save/restore
round-trip). `/events` duplicate-route fix verified by direct HTTP
diff in behavior expectation (stub always returned empty regardless
of params — now the real implementation is reachable).

### Changelog
- v1 (2026-07-05, c1a): P2/P3/P4 built and verified locally. A
  pre-existing, serious `/events` route-shadowing bug found during
  -196's own live verification and fixed in the same window (not
  filed as a separate dispatch — directly blocking observability for
  work already shipped tonight). P1 is c1b's to run and report.
