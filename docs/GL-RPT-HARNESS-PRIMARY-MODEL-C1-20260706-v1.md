# GL-RPT-HARNESS-PRIMARY-MODEL-C1-20260706-v1

**doc_id:** GL-RPT-HARNESS-PRIMARY-MODEL-C1-20260706-v1
**From:** c1
**Executing:** GL-CMD-HARNESS-PRIMARY-MODEL-EVE-20260706-v1
**To:** Eve (routing per dispatch instruction — no questions to Joe in this doc)
**Follows:** `GL-CMD-HARNESS-DEPLOY-EVE-20260706-v1`, `GL-RPT-HARNESS-DEPLOY-C1-20260706-v1` (the "staging doesn't exist" finding this dispatch is the direct answer to).

Three files touched exactly as specified. All verification checks run,
including one beyond what the dispatch asked for (noted below, not
scope creep — it's verification of the exact code this dispatch
changed, not a new feature).

---

## Diff summary per file

**`harness/harness/substrate_client.py`** (+13/-17 net across two edits):
- Added `CleanupNotSupported(Exception)` near the top of the file, exact
  text from dispatch.
- Replaced `LegacySubstrateClient.restore_state()`'s body. The prior
  version raised a plain `RuntimeError` documenting that no synchronous
  restore endpoint exists on the legacy substrate (from the deploy
  dispatch's own Finding 4). Now raises `CleanupNotSupported` with the
  operating-model rationale, exact text from dispatch. No other part of
  this file touched — `status()`, `stream_events()`, `inject_probe()`,
  `snapshot_state()` all unchanged, matching the dispatch's "what is not
  changing" list.

**`harness/harness/scenario.py`** (+2/-2):
- `Cleanup.restore_state` dataclass field default: `"pre_probe_snapshot"`
  → `"leave_in_place"`.
- `_parse_cleanup()`'s `_one_of` allowed set:
  `{"pre_probe_snapshot", "none", "custom"}` →
  `{"leave_in_place", "pre_probe_snapshot", "none", "custom"}`.
- **Not changed, per the dispatch's literal instruction (only the
  `_one_of` set was named):** `_parse_cleanup()`'s own
  `raw.get("restore_state", "pre_probe_snapshot")` fallback string is
  still `"pre_probe_snapshot"`. Practical consequence: a scenario YAML
  that includes a `cleanup:` block but omits the `restore_state` key
  entirely still resolves to `pre_probe_snapshot` at parse time, not the
  new `leave_in_place` default — the dataclass's own default only
  applies to direct `Cleanup()` construction bypassing the parser.
  Every real scenario in the library today (`cross_sense_recall_basic.
  yaml`) declares `restore_state` explicitly, so this has no live effect
  right now, but it's a real inconsistency between the two "defaults"
  worth Eve knowing about. Left as-is rather than silently fixed, since
  the dispatch named exactly one location to change.

**`harness/harness/runner.py`** (+33/-11):
- Added `CleanupNotSupported` to the `substrate_client` import line.
- Replaced `_cleanup()`'s body and docstring, exact text from dispatch.
  `leave_in_place` now checked first (INFO finding, returns without
  touching the substrate). `pre_probe_snapshot`'s restore call now
  catches `CleanupNotSupported` explicitly (WATCH), then
  `NotImplementedError` (WATCH), then any other `Exception` (WARN — was
  CRITICAL). The `# In production this would set a marker file...`
  comment and the "substrate now DIRTY" finding text are both gone
  entirely — no code path in this file produces DIRTY language anymore.

---

## Verify results

**Dry-run 1** — `python -m harness validate scenarios/mechanism/cross_sense_recall_basic.yaml` (scenario unchanged, still declares `pre_probe_snapshot` explicitly):
```
OK  GL-SCN-CROSS-SENSE-RECALL-BASIC-EVE-20260706-v1  (mechanism)
```
PASS, exit 0.

**Dry-run 2** — scratch scenario (`sed 's/pre_probe_snapshot/leave_in_place/'` copy) validated:
```
restore_state: leave_in_place
OK  GL-SCN-CROSS-SENSE-RECALL-BASIC-EVE-20260706-v1  (mechanism)
```
PASS, exit 0. Schema accepts the new value.

**Real check** — ran exactly the specified command against the real
primary substrate (`https://3d6toi0gw0.execute-api.us-east-1.amazonaws.com`
— the only real Guala endpoint that exists, per the deploy dispatch's
Finding 2; `~/.guala/aws-config.json` created with the same real AWS
resource values used before, new filename per this dispatch):

```
verdict: PRECONDITION_NOT_MET
```
exit 4. Finding recorded: `CRITICAL (runner) precondition not met:
presence.wc expected True, actual False`.

Note this is **not** a `clean_slate`/tick-mismatch failure — the
presence precondition (`wc: true` in the scenario) is what didn't match,
because nothing is actively establishing wc pair-bond presence at the
moment of the check. This is consistent with "primary is still
quiescent-clean" per the dispatch's own expected-outcome language.
Confirmed by direct grep of the rendered report: no occurrence of
"restore" or "dirty" (case-insensitive) anywhere in the output.

**Honest limitation of this real check, surfaced rather than glossed
over:** a precondition failure means `runner.py`'s `run()` returns
*before* Step 8 (`_cleanup()`) ever executes — this is true both before
and after this dispatch's changes. So "the report shows no restore
attempt" is **guaranteed by control flow alone**, not evidence that the
rewritten `_cleanup()` behaves correctly. It would have passed
identically even if I had made no changes to `runner.py` at all, or
introduced a bug in the new logic. To actually verify the changed code
executes correctly (not scope creep — this is verification of exactly
the three files this dispatch touched, no new features), I additionally
unit-tested `Runner._cleanup()` directly against a mocked substrate
client for all three `restore_state` values:

- `leave_in_place`: `substrate.restore_state` never called; exactly one
  `INFO` finding containing "left in place"; no "dirty" text anywhere.
- `none`: no call, no finding.
- `pre_probe_snapshot` with a real snapshot_id and the substrate raising
  `CleanupNotSupported` (the actual exception `LegacySubstrateClient.
  restore_state()` now raises): exactly one `WATCH` finding containing
  "operating model does not support it"; **no** `CRITICAL` finding
  anywhere; no "dirty" text anywhere; `restore_state` confirmed called
  exactly once.

All three assertions passed. This is the check that actually proves the
rewrite works, not just that the literal specified command produces a
clean-looking report by accident of control flow.

---

## Commit

`9efaeee` on `guala-live`, pushed to origin (`git ls-remote origin
guala-live` confirms match). Contains the three code files plus
`docs/GL-CMD-HARNESS-PRIMARY-MODEL-EVE-20260706-v1.md` (the dispatch
text itself, filed per the standing on-origin-means-filed rule). This
report is a separate, following commit, matching this session's own
established pattern of code-commit-then-report-commit rather than
bundling documentation with code changes.

---

## Confirmation: cleanup did not attempt restore in the real check

Confirmed twice, by two different methods: (1) the rendered report from
the real command contains no "restore" or "dirty" text anywhere
(control-flow-guaranteed, as noted above — the precondition check never
got far enough to reach cleanup); (2) the direct unit test of
`_cleanup()` itself, run independently of any real HTTP call, confirms
the `leave_in_place` path (now the scenario schema's default) never
calls `substrate.restore_state` at all, and that even the explicit
`pre_probe_snapshot` opt-in path, when it hits the real
`CleanupNotSupported` exception `LegacySubstrateClient` now raises,
produces a `WATCH` finding — never `CRITICAL`, never DIRTY language.
