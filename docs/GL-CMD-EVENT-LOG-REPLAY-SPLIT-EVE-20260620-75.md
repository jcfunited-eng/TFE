# GL-CMD-EVENT-LOG-REPLAY-SPLIT-EVE-20260620-75

**Doc ID:** GL-CMD-EVENT-LOG-REPLAY-SPLIT-EVE-20260620-75
**Author:** Eve
**Date:** 2026-06-20
**Type:** CMD (dispatch)
**Subject:** Split `EventLog.replay_events` into boot-replay and session-reconstruct paths
**Refs:** 9cc0757 (skip converse replay), e0de31e (skip quiet replay), GL-CMD-73

---

## Why this brief exists

`EventLog.replay_events` was doing two conceptually different jobs under one name:

1. **Rebuild persistent substrate state** at substrate boot. Required: re-running events like vocab_install, commit, feedback is how the substrate's persistent state is reconstructed from the event log if a snapshot is stale or missing. Without it the substrate would be wrong.

2. **Rebuild V7Session ephemeral state** at session creation. Re-running `quiet_tick` and full `converse` for every historical event was, in effect, redoing all of Guala's prior conversations to "catch the session up." This took 131 seconds for 744 events. The session does not need this — the substrate it sits on top of is already current.

The 9cc0757 and e0de31e patches fixed the symptom by adding conditional skips inside `replay_events`. The function's name now lies: it claims to replay events but silently skips two of them. This is a foot-gun the next time a new event type is added — the implementer will reasonably assume `replay_events` does what it says and miss the skip-list.

This brief restores the architectural distinction the codebase already implicitly has: persistent state lives in the substrate (System), ephemeral state lives in the session (V7Session). Each has its own restoration path.

---

## Substrate-true check

| Concern | Status |
|---|---|
| Does the brief change what events are logged? | No. Same `_log_substrate_event` calls remain. |
| Does the brief change substrate physics (decay, binding, atlas behavior)? | No. Only changes how state is restored across container restarts. |
| Does the brief introduce a heuristic about which events "matter"? | No. The split is by event *type* and is grounded in V1 audit findings, not by a salience guess. |
| Does the brief preserve the property that a substrate restored from snapshot+event-log is bit-for-bit equivalent to a substrate that was never restarted? | Required: yes. V1.3 audit must confirm this. If V1.3 finds drift, write follow-up brief before shipping. |

---

## V1 — Audit (required BEFORE any code changes)

### V1.1 — Enumerate event types

For every call to `_guala._log_substrate_event(event_type, ...)` in the codebase, list:
- event_type (string)
- file:line where it is logged
- the substrate-state changes its handler in `replay_events` would re-apply

Produce a table. Required event_types known from the codebase: `vocab_install`, `feedback`, `commit`, `quiet_tick`, `converse`, `curriculum_loaded`, plus whatever others the grep finds.

### V1.2 — Classify each event type

For each event_type, assign one classification with one-sentence justification:

- **Persistent** — Re-applying the event in `replay_events` changes substrate state (engine fields, atlas entries, vocab, plasticity). Must be replayed at substrate boot or the substrate is wrong.
- **Session-local** — Re-applying changes only V7Session fields (drive_tracker, intro_commit_history, recent_words ring). Does not need to be replayed at substrate boot; session state can be rebuilt from current substrate state.
- **Telemetry** — Re-applying changes nothing observable. Pure logging.

Hand-classification expected:
- `vocab_install` → Persistent
- `commit` → Persistent
- `feedback` → Persistent
- `quiet_tick` → Session-local (already empirically confirmed: e0de31e skips it without measurable state loss; V1.3 must confirm formally)
- `converse` → Session-local
- `curriculum_loaded` → Telemetry

Hand-check, do not assume. If any of the above is misclassified the rest of the brief is wrong; surface it.

### V1.3 — Ownership audit

For each *field* that varies during a session, identify owner:

| Field | Owner | Notes |
|---|---|---|
| `engine.vocab` | System (persistent) | |
| `engine.atlas.entries` | System (persistent) | |
| `engine.read_count` | System (persistent) | |
| `engine.sections[*].mode_strength` | System (persistent) | |
| `engine.sections[*].mode_bank` | System (persistent) | |
| `V7Session.sys_` | V7Session (reference to System) | Not owned, referenced |
| `V7Session.drive_tracker` | V7Session (ephemeral) | |
| `V7Session.intro_commit_history` | V7Session (ephemeral) | |
| `V7Session.aware_vec/aware_modes` | V7Session (ephemeral, rebuildable from System) | |

Required check: is there any field written by V7Session that affects System after the next System tick? If yes, the back-write needs to flow through a logged event so it survives restart. Surface any such cases — they are the substrate-true issue this brief is really about.

### V1.4 — Boot-vs-session test

Confirm: after a fresh boot with no V7Session created, the substrate (System) is in a consistent state where the first incoming converse can be served correctly. If not — i.e. some V7Session state is required to handle the first converse — surface this. It would mean session state IS persistent in disguise and the current architecture is the bug, not the function name.

---

## V2 — The split (only after V1 lands and is reviewed)

### Rename and remove conditionals

`EventLog.replay_events` → `EventLog.replay_persistent`.

Inside `replay_persistent`, remove the explicit skips for converse and quiet (added by 9cc0757 / e0de31e). The function now only iterates over event types classified as Persistent in V1.2.

Add a guard: any event type *not* in the Persistent allowlist raises a clear error if encountered. This forces a brief next time someone adds a new event type — they must decide which bucket it belongs in. No silent skips.

### Add session reconstruct

`EventLog.reconstruct_session(session, engine)` — new method. Based on V1.3 audit findings, this either:

- **(Common case, expected from current architecture)** does nothing. V7Session is created fresh; it reads from `engine` at construction; nothing to reconstruct. Method exists for clarity and for future extension.
- **(If V1.3 finds back-writes)** rebuilds V7Session ephemeral fields from current `engine` state. Specific fields populated determined by V1.3 findings.

### Caller updates

- `boot_substrate` calls `replay_persistent` (renamed from `replay_events`).
- `get_or_create_session` calls `reconstruct_session` instead of inheriting the side-effects of `replay_events`.

---

## V3 — Verification

### V3.a — Session init regression budget

Cold session init from substrate boot:
- Pre-fix baseline (post-e0de31e): ~21ms (transcript)
- Post-split target: ≤100ms

### V3.b — Substrate state bit-for-bit equivalence

Boot substrate twice with identical EFS state:
- Run 1: from snapshot only (event log empty)
- Run 2: from snapshot + replay persistent events

For both runs capture: vocab size, atlas count, atlas total_strength, read_count, engine tick. Required: all five identical. If not, V1.3 missed an event type — surface and write follow-up brief before shipping.

### V3.c — End-to-end Peter Rabbit via async load

Run GL-CMD-74's V3.a after this split lands. Required: no regression — same result.

### V3.d — Unknown event type fails loud

Inject a fake event type into the event log. Boot substrate. Required: `replay_persistent` raises with a clear message naming the unknown event type. (Not a silent skip.)

---

## Out of scope

- Changing what events are logged.
- Changing substrate physics, atlas mechanics, autonomy loop behavior.
- Adding V7Session persistence across container restart. If V1.3 surfaces a real need for it, that's a separate brief — this one is about restoring architectural honesty, not adding capability.
- Optimizing `replay_persistent` further. It's fast enough as-is.

---

## Filing

c1 files report `GL-RPT-EVENT-LOG-REPLAY-SPLIT-C1-20260620-01.md` (or next-day if after midnight UTC).

V1 audit findings are filed as part of the report, not separately. V1 must be filed before V2 code is written; if V1.3 or V1.4 surface anything that contradicts the V2 plan above, c1 writes a follow-up brief and stops.
