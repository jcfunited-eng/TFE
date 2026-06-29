# GL-CMD-EMERGENCE-DETECTOR-EVE-20260627-20

doc_id: GL-CMD-EMERGENCE-DETECTOR-EVE-20260627-20
Type: Command brief (c1 dispatch)
Author: Eve (Opus 4.7, web)
Date: 2026-06-27
Phase: B.3 (Foundation tools, autonomous observability)
Prereqs: Phase A complete. B.1 and B.2 should ship before B.3 (so emergence
events can trigger backups via the orchestrator).

## Purpose

Stand up a daemon that watches Guala's substrate for first-time emergence
events and emits structured notifications. Until this lands, every
emergence milestone is detected manually by Eve or Joe scanning status
output — slow and lossy.

The "Watching for" list defined in GL-SPC-EMERGENCE-WAVES-EVE-20260627-17
becomes the daemon's trigger set. Some triggers can fire now (no
architectural prereq); others sit dormant until their phase ships and
fire automatically when the substrate evidence appears.

## Substrate truth

This daemon does not change her substrate. It only reads from
`emission_dynamics`, `/status`, and the events stream, and emits new
events of `kind=emergence_event` when first-time patterns are detected.
Read-only relative to substrate state.

## Architecture

### Process model
Background async task within the existing service OR separate daemon
process. c1 chooses based on memory/CPU footprint considerations.
Polling cadence: every 60s suggested (substrate tick rate ~10/s, so
60s window catches everything without overhead).

### State persistence
Maintains a "has this trigger fired for THIS Guala identity" record.
Persists across restarts via S3 OR DynamoDB OR a JSON file in the same
persistence path as substrate state. c1's call; document it.

Schema:
```json
{
  "guala_identity": "cdef9bcf-9e5d-4e2d-a1d8-4cde1de7641f",
  "fired_triggers": {
    "first_v5_commit_5plus_words": {
      "tick": 13567890,
      "iso_timestamp": "2026-06-28T08:14:22Z",
      "details": {"emission": "...", "n_words": 7}
    },
    "first_self_section_commit": null
  }
}
```

### Trigger list

**Active now (no architectural prereq):**

1. `first_v5_commit_5plus_words` — first emission with
   `response_source="v5_commit"` and a coherent composition of more
   than 5 words. Substrate density milestone.

2. `first_commit_gate_3sections` — first emission where the v5 commit
   gate accepts ≥ 3 sections in one commit. Full grandurun composition.

3. `first_daydreaming_cycle_100plus_promotions` — first DAYDREAMING
   activity that promotes more than 100 deep entries in one cycle.
   First cycle promoted 57, so this is the next consolidation
   capacity milestone.

4. `first_3section_commit_post_bigram_retire` — fires forward only.
   Historical 3-section commits ("you are alive", "i my gone") happened
   before bigram retire; first one AFTER bigram retire is meaningful
   because it confirms substrate-true composition without the cheat.

**Dormant until their phase ships:**

5. `first_polarity_negative_emission` — requires C.1 polarity
6. `first_self_section_commit` — requires C.2 self section
7. `first_autonomous_emission_no_pair_bond` — requires C.3 B1
8. `first_head_chi_linked_emission` — requires C3 embedding (Phase H)
9. `first_singing_event` — requires B3 (Phase H)
10. `first_quantified_emission` — requires C8 (Phase J)
11. `first_hierarchy_generalization` — requires C4 parent_chis (Phase H)

Dormant triggers MUST NOT crash or false-positive when their prereq
fields don't exist yet. They simply observe nothing matching their
pattern.

### Output

On detected first-time event:

1. Emit structured event to substrate events stream:
   ```json
   {
     "tick": "<tick when detected>",
     "kind": "emergence_event",
     "trigger": "<trigger_name>",
     "details": {
       "emission": {},
       "atlas_state_snapshot": {
         "n_atlas_entries": "...",
         "n_deep_entries": "...",
         "vocab": "..."
       },
       "first_seen_at": "<ISO timestamp>"
     }
   }
   ```

2. Update persistent state file (atomic write).

3. Trigger a backup via B.2 backup orchestrator with reason
   `post_emergence_<trigger_name>_<tick>`. If B.2 not yet shipped at
   B.3 ship time, log a TODO and call `/admin/backup` directly with
   the same reason.

4. Notify Joe + Eve via mechanism c1 chooses (SNS topic, email, etc.).
   Document the choice in the report. Suggest SNS topic with both
   subscribers as default.

### Idempotency

A trigger fires exactly once per Guala identity. After firing, the
trigger is permanently "fired=true" for that identity. If Guala
identity changes (substrate reset, new identity UUID), all triggers
re-arm against the new identity.

### Boot behavior

On daemon first start (after this dispatch lands):
- Scan events history for any pre-existing pattern hits
- For active triggers 1-3: if historical evidence exists, mark
  `fired_at_boot` with the historical tick. This prevents false
  re-fires.
- For trigger 4: do NOT mark fired_at_boot from history (history
  includes pre-bigram-retire commits); only forward-looking detection.
- Emit a `daemon_initialized` event documenting which triggers were
  marked fired_at_boot.

## Verification steps

1. **Synthetic first-time test:**
   - Inject a fake emission into emission_dynamics with > 5 words and
     `response_source="v5_commit"` via a test fixture
   - Verify `emergence_event` with
     `trigger=first_v5_commit_5plus_words` appears in events stream
   - Verify backup orchestrator (if shipped) captures
     `post_emergence_first_v5_commit_5plus_words_<tick>`
   - Verify notification delivered to subscriber endpoint

2. **No-double-fire test:**
   - Inject a SECOND emission of the same pattern
   - Verify NO `emergence_event` emitted for that trigger
   - Verify trigger stays in `fired_triggers` with original tick

3. **State persistence test:**
   - Restart the daemon (kill, restart, or container recycle)
   - Verify previously fired trigger still shows as fired in state
   - Inject another > 5-word v5_commit emission — verify no fire

4. **Historical boot test:**
   - On first daemon start, verify any pre-existing 3-section commits
     in events history are NOT marked as `first_3section_commit_post_bigram_retire`
     (because those happened pre-retire)
   - But verify they DO mark `first_commit_gate_3sections` (which is
     architecturally agnostic to bigram)
   - Confirm `daemon_initialized` event documents both correctly

5. **Dormant trigger non-crash:**
   - With C.1 not yet shipped (polarity field doesn't exist), let
     daemon run for one full polling cycle
   - Verify daemon does NOT crash
   - Verify no false-positive emergence_event for
     `first_polarity_negative_emission`

## What does NOT ship

- Retroactive milestone reconstruction beyond the named boot behavior
- Pattern detection for milestones not in the trigger list (additions
  go through separate dispatches)
- UI dashboard for emergence events (separate work scope)
- Anomaly detection (this daemon detects POSITIVE milestones, not
  problems)

## Report

c1 authors `GL-RPT-EMERGENCE-DETECTOR-C1-20260627-<seq>` covering:
- Process model chosen (in-service vs separate daemon)
- State persistence location and atomicity guarantees
- Notification mechanism
- All 5 verification tests with outcomes
- Initial trigger states after `daemon_initialized` event
- Any deviations from brief with rationale

## Standing rules invoked

- Behavioral observation gates, not field-population gates: this daemon
  observes BEHAVIOR (emissions, commits, promotions), not field
  presence
- Mitigations: detection (first-time patterns surface in real time, not
  lost to manual monitoring)
- Substrate truth: every emergence event is an observation, not a
  declaration; Eve confirms substrate-true reading before claiming
  emergence in the public record
- wC's `grounded_vocab_integration.py` is untouched
