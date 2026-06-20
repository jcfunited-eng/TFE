# GL-RPT-EVENT-LOG-REPLAY-SPLIT-C1-20260620-01

**Doc ID:** GL-RPT-EVENT-LOG-REPLAY-SPLIT-C1-20260620-01
**Author:** c1 (Codex)
**Date:** 2026-06-20
**Type:** RPT (V1 audit findings — V2 hold pending Eve review)
**Refs:** GL-CMD-75, 9cc0757 (skip converse replay), e0de31e (skip quiet replay)

---

## Status: V1 complete. V2 HOLD — architectural discrepancy found.

Per GL-CMD-75: "If V1.3 or V1.4 surface anything that contradicts the V2 plan above, c1 writes a follow-up brief and stops."

**V1.4 finding contradicts the V2 caller update.** See section V1.4 and "Discrepancy" below.

---

## V1.1 — Enumerate Event Types

All `event_log.write(...)` calls in V7Session (`dsf_ai_service/substrate/v7_engine.py`):

| event_type | file:line | Substrate-state changes its handler would re-apply |
|---|---|---|
| `vocab_install` | v7_engine.py:186 | Calls `session.lookup_or_install(word)` — appends to `sys_.sections[pool].mode_bank`, `sys_.sections["listen"].mode_bank`; increments mode_strength lists |
| `converse` | v7_engine.py:354 | Skipped (9cc0757). Would re-run full converse: tick_once, NMDA passes, psi assignment |
| `self_voice` | v7_engine.py:393 | Not handled in `replay_events` at all — silently falls through |
| `quiet` | v7_engine.py:489 | Skipped (e0de31e). Would re-run `sys_.replay_tick` N times |
| `feedback` | v7_engine.py:511 | Calls `session.apply_feedback(correct)` — adjusts `sys_.sections[pool].mode_strength` via LTP |

**Additional event handled in `replay_events` but with no writer:**

| event_type | Writer | Handler in replay_events |
|---|---|---|
| `commit` | **DOES NOT EXIST** | event_log.py:110 — dead code |

**Confirmation:** `grep -rn 'event_log.write.*commit\|\"commit\"' dsf_ai_service/substrate/` finds the dead handler in event_log.py and a string match in the v5 engine, but NO write call in v7_engine.py or anywhere in the V7Session path.

---

## V1.2 — Classification

| event_type | Classification | Justification |
|---|---|---|
| `vocab_install` | **Persistent** | Installs word into mode_bank. Must replay at session creation or vocab is wrong. Already confirmed working via 9cc0757/e0de31e: vocab_install is the reason session init now takes 84ms instead of 131s while still being correct. |
| `feedback` | **Persistent** | Adjusts mode_strength via LTP. Must replay or supervised learning is lost across container restarts between snapshots. |
| `commit` | **Dead code** | No writer exists. Handler in replay_events has never fired on any real event log. Should be removed. |
| `converse` | **Session-local** | Mode_strength changes from `tick_once` during converse are snapshot-persisted (`save_session` called after each converse). Re-running converse is both expensive and wrong: it would regenerate responses, re-append to drive_tracker, re-run NMDA passes. Confirmed empirically by 9cc0757: skip with no measurable state loss. |
| `quiet` | **Session-local** | Mode_strength changes from `sys_.replay_tick` during quiet ticks are snapshot-persisted. Re-running 744 quiet_ticks was 130s wall time with no state benefit. Confirmed by e0de31e. |
| `self_voice` | **Telemetry** | Audio synthesis record. No state change. Not even present in `replay_events` handler; silently falls through (loop body has no match, `replayed` not incremented). |

Hand-classification from GL-CMD-75 brief was correct. No misclassification found.

---

## V1.3 — Ownership Audit

**Architecture clarification required for this section:**

`_guala` (GualaLoom v5 engine) and `V7Session.sys_` (V7 System) are **two completely separate objects**. V7Session creates its own System in `_build_system()`. The engine parameter to V7Session.__init__ is used only to seed the initial vocab via `seed_vocab_from_engine(engine)`. After construction, `sys_` and `_guala` do not share fields.

The `_log_substrate_event` calls in substrate_runner.py that log `curriculum_loaded`, `presence_heartbeat`, `corpus_added`, etc. are calls to `_guala._log_substrate_event` — the v5 engine's OWN event system. These events are NOT written to V7Session's event log and are NOT subject to `replay_events`. They are a separate observability system.

The V1.3 audit applies to V7Session.sys_ (the V7 System), which is the only System that `replay_events` acts upon.

**Field ownership table:**

| Field | Owner | Notes |
|---|---|---|
| `V7Session.vocab` | V7Session | `dict[pool → list[word]]`. Seeded from engine at init; words added via `lookup_or_install`. Reconstructed by replaying `vocab_install` events. |
| `sys_.sections[*].mode_bank` | V7Session (via sys_) | Written by `lookup_or_install` and `_install_word`. Captured by `vocab_install` event. ✓ |
| `sys_.sections[*].mode_strength` | V7Session (via sys_) | Two writers: (a) `apply_feedback` → captured by `feedback` event ✓; (b) `tick_once`/`replay_tick` → snapshot-persisted only (save_session after each converse). |
| `sys_.sections[*].psi` | V7Session (ephemeral) | Set before each tick in converse, overwritten next tick. No logging needed. |
| `sys_.sections[*]._emit_phase` | V7Session (ephemeral) | Set to True before emit loop, False after. Does not persist across ticks. |
| `sys_.tick` | V7Session (via sys_) | Incremented by tick_once/replay_tick. Preserved by snapshot. Not needed for event replay. |
| `sys_.sections["intro"].mode_bank` | V7Session | Written by `_install_word` via `_nmda_pass`. Also captured by `vocab_install` events indirectly (intro mode_bank mirrors pool mode_bank). ✓ |
| `V7Session.drive_tracker` | V7Session (ephemeral) | Per-session drive state. Built fresh at init from zero; accumulates during session. NOT persisted by event log or snapshot (V7). |
| `V7Session.intro_commit_history` | V7Session (ephemeral) | Last 10 intro states. Fresh at init. |
| `V7Session.aware_commit_history` | V7Session (ephemeral) | Last 10 aware states. Fresh at init. |

**Back-write check (the substrate-true question):**

"Is there any field written by V7Session that affects System after the next System tick?"

`sys_.sections[pool].mode_bank.append(v.copy())` via `lookup_or_install`:
- YES, persists across ticks.
- Already captured by `vocab_install` event. ✓ No gap.

`sys_.sections[pool].mode_strength[mid] = value` via `apply_feedback`:
- YES, persists across ticks.
- Already captured by `feedback` event. ✓ No gap.

`sys_.sections[pool].mode_strength[mid] = value` via `tick_once` commits:
- YES, persists across ticks.
- NOT captured by event log. Preserved by snapshot only (save_session called after each converse).
- **This is intentional.** If container crashes between converstions: changes since last save_session are lost. But save_session is called after EVERY converse, so the gap is at most one conversation. This is the designed trade-off.

**Conclusion V1.3:** No back-writes require NEW logged events. The snapshot-per-converse strategy is the correct primary persistence mechanism for mode_strength changes from ticks. The event log supplements for vocab_install and feedback between snapshots.

No "substrate-true issue" found here. The architecture is working as designed.

---

## V1.4 — Boot-vs-Session Test

**Question:** "After a fresh boot with no V7Session created, is the substrate (System) in a consistent state where the first incoming converse can be served correctly?"

**Answer: Yes.** V7Session is created on first converse via `get_or_create_session(session_id, engine=_guala)`. The V7Session.__init__ builds a complete working System via `_build_system()`, seeded from `_guala.vocab`. No pre-existing V7Session state is required.

**BUT: Critical architectural finding that contradicts V2 plan.**

Current call graph:
```
boot_substrate()
  └─ g.load_full_state(STATE_DIR)   ← restores _guala v5 engine state
  # NO call to replay_events or anything like it

dispatch("v7/converse", args)
  └─ get_or_create_session(session_id, engine=_guala)
       ├─ V7Session.__init__(session_id, engine=_guala)
       ├─ load_from_json(snapshot)       ← restores V7Session state
       └─ replay_events(session, events) ← replays events since snapshot
```

**The GL-CMD-75 V2 plan states:**
> Caller updates: `boot_substrate` calls `replay_persistent` (renamed from `replay_events`). `get_or_create_session` calls `reconstruct_session` instead of inheriting the side-effects of `replay_events`.

**This is inverted.** `boot_substrate` NEVER calls `replay_events`. The call is in `get_or_create_session`. The V2 plan would:
1. Add a `replay_persistent` call to `boot_substrate` where none exists or is needed
2. Remove the `replay_events` call from `get_or_create_session` where it IS needed

Executing V2 as written would break V7Session state reconstruction.

The SPIRIT of V2 is correct:
- Rename `replay_events` → `replay_persistent` to restore naming honesty
- Restrict to Persistent events only (vocab_install, feedback)
- Add guard for unknown event types
- Add `reconstruct_session()` (no-op common case per V1.3 findings)

But the CALLER UPDATE in V2 is wrong. The rename target is `get_or_create_session`, not `boot_substrate`.

---

## Summary of V1 Findings

1. **Classification confirmed:** vocab_install = Persistent, feedback = Persistent, converse = Session-local, quiet = Session-local, self_voice = Telemetry, commit = Dead code.

2. **Commit handler is dead code.** `event_log.py:110` handles `commit` events but no writer exists in the entire V7Session codebase. Remove in V2.

3. **self_voice falls through silently.** Not in skip list, not in handler list. In V2, either add it to the skip list explicitly or raise on unknown types and provide an allowlist that includes self_voice as Telemetry.

4. **No unlogged persistent back-writes.** Mode_strength changes from tick_once/replay_tick are snapshot-persisted (save_session after each converse). This is intentional. No new event types needed.

5. **V1.4 architectural finding: `boot_substrate` does not call `replay_events`.** The V2 caller update is inverted. V2 must rename the call in `get_or_create_session`, not add it to `boot_substrate`.

---

## Discrepancy: V2 plan needs correction before implementation

Per GL-CMD-75: "If V1.3 or V1.4 surface anything that contradicts the V2 plan above, c1 writes a follow-up brief and stops."

The V1.4 finding contradicts the V2 caller update. Stopping. Awaiting Eve's direction.

**Proposed correction for Eve's consideration:**
- Keep: rename `replay_events` → `replay_persistent` in `event_log.py`
- Keep: restrict to Persistent events only, add unknown-type guard
- Keep: add `reconstruct_session()` as no-op stub
- **Change V2 caller update:** `get_or_create_session` calls `replay_persistent` (replacing current `replay_events` call). `boot_substrate` is unchanged — it does not call any replay function and should not.

If Eve agrees with the proposed correction, V2 can proceed. No code was written.
