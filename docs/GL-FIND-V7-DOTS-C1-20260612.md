# GL-FIND-V7-DOTS-C1-20260612 — Why v7 always returns "..." / 0 commits / 0 gates

**Author:** c1 | **Date:** 2026-06-12 | **Status:** INVESTIGATION ONLY — wC fix brief required per rule 1

## Summary

The v7 layer in the UI always returns "..." with 0 commits and 0 gates. Two independent root causes found: a structural NMDA gate contradiction blocks intro/aware, and the S/V/O emission loop may not converge in 120 ticks.

## Finding 1: Two separate conversation paths

The MCP bridge (`guala_say`) posts to `/api/v1/gualaloom` which routes to the **v5 engine**. The v7 engine is ONLY reachable via `/v7/converse` which only the HTML UI calls. Bridge and v7 are completely disconnected. If "..." was observed via the bridge, v7 isn't even involved.

## Finding 2: NMDA intro gate is structurally blocked

`v7_engine.py` lines 397-399: `update_drive_tracker` marks S/V/O sections as recently active RIGHT BEFORE the intro gate check. The intro gate's context function `context_no_recent_drive` requires S/V/O to be quiet (below 0.10 threshold). Since S/V/O were just marked active, the context function always returns False. The intro gate can **never** fire.

## Finding 3: Aware gate cascades from intro

The aware gate checks whether intro's krimelack has a recent entry (within 5 ticks). Since intro never fires (Finding 2), intro's krimelack never grows, so aware's context also returns False. This cascades: intro blocked -> aware blocked -> 0 gates always.

## Finding 4: Per-turn psi reset may prevent convergence

At lines 228-235, every converse call resets psi for ALL sections to `0.7 * uniform + 0.3 * random`, destroying accumulated state. The 120-tick emit loop must then converge from this primed state to a commit. If drive injection isn't strong enough, no commits fire, response_tokens is empty, and "..." is displayed.

## Finding 5: mode_to_word reverse lookup may fail silently

`_mode_to_word` (line 646-651) returns None if the committed mode_id doesn't map back to a word in vocab. Dynamically installed modes via `lookup_or_install` can drift from the vocab list. Commits that fire but can't map to words produce silent drops.

## Root causes (ranked)

1. **NMDA intro gate structurally blocked** — `update_drive_tracker` at 397-399 contradicts `context_no_recent_drive`
2. **Aware gate cascades** — depends on intro firing, which never happens
3. **0 commits possible** — psi reset + insufficient drive → no convergence in 120 ticks
4. **mode_to_word silent failures** — commits fire but can't produce visible tokens

## Recommendation

This is substrate primitive territory. The NMDA gate timing contradiction is a design issue, not a bug — the ordering of drive tracking vs gate checking needs a wC brief to resolve. No code fix should ship without that brief.
