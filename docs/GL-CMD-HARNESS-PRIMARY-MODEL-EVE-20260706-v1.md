# GL-CMD-HARNESS-PRIMARY-MODEL-EVE-20260706-v1

**doc_id:** GL-CMD-HARNESS-PRIMARY-MODEL-EVE-20260706-v1
**Author:** Eve
**To:** c1
**Ordered by:** Joe (2026-07-06 session)
**Follows:** `GL-CMD-HARNESS-DEPLOY-EVE-20260706-v1` (skeleton deployed and wired) and `GL-RPT-HARNESS-DEPLOY-C1-20260706-v1` (staging doesn't exist finding).

## Verdict

The harness's primary-safety rule from the harness spec is wrong for Joe's operating model. Under Joe's ratified model: production is the workbench. Production is empty until Joe deliberately routes data in. Production gets wiped between sessions. Mutation against production is normal operation, not the blocked path. Cleanup is "leave state in place — Joe wipes on his schedule," not "restore to pre-probe snapshot." No DIRTY marker mechanism. c1 rewrites two files to match.

Bounded scope. No new features, no new scenarios, no AWS work, no substrate-side changes.

## What is changing

Two files:

**`harness/harness/substrate_client.py`** — `restore_state()` currently documents "raises NotImplementedError until a synchronous restore endpoint exists on the substrate." That whole method becomes explicit: it raises a `CleanupNotSupported` exception with the message that restore isn't part of the operating model — Joe wipes production directly when he chooses, and the harness never tries to restore.

**`harness/harness/runner.py`** — `_cleanup()` currently defaults to `pre_probe_snapshot` and marks the substrate DIRTY if restore fails. Both go. New default cleanup behavior: leave state in place, log a "state left in place per production-mode operating model" finding at INFO severity. The DIRTY marker path is removed entirely. `Verdict.RESTORE_FAILED` stays in the enum for the case where a scenario explicitly requests restore and it fails (still a real failure mode), but it stops being a common outcome — most scenarios will never request restore under this model.

Also in `runner.py`: the docstring on `_cleanup()` gets rewritten to describe the actual model. Current docstring implies restore-to-snapshot is normal; new docstring names Joe's wipe-between-sessions discipline as the reset mechanism.

## What is not changing

Nothing else. Specifically:
- The seven wired methods on `LegacySubstrateClient` (status, stream_events, inject_probe, snapshot_state — all four wired by c1 in the deploy dispatch) stay exactly as they are.
- The six wired AWS collectors stay exactly as they are.
- The scenario schema stays as-is. Scenarios can still declare `cleanup.restore_state: pre_probe_snapshot` if they specifically want restore — the harness will honor the request and fail-loud if the underlying substrate doesn't support it. Default value for new scenarios becomes `leave_in_place`.
- The precondition check stays exactly as-is. A scenario declaring `clean_slate` will still fail precondition if the substrate has data. That failure is Joe's signal that he hasn't wiped yet, not a bug.
- The event stream, CPU, memory collectors stay as-is.
- The report emitter stays as-is.
- The CLI stays as-is.

## Concrete changes

**`substrate_client.py`, LegacySubstrateClient.restore_state()`:**

Replace the current body with:

```python
async def restore_state(self, snapshot_id: str) -> None:
    """Not part of the production operating model.

    Under Joe's ratified model, production is the workbench. Data
    accumulates only from deliberately routed scenarios and gets wiped
    between sessions by Joe's explicit action. The harness does not
    restore state — wipe is the reset mechanism.

    A scenario that explicitly requests restore in cleanup will hit
    this exception. That's the intended behavior: restore-as-cleanup
    is inconsistent with the operating model and should be rewritten
    to either leave-in-place (default) or explicitly wipe.
    """
    raise CleanupNotSupported(
        "restore_state is not part of the production operating model. "
        "Under Joe's ratified model, production is the workbench, data "
        "accumulates only from deliberately routed scenarios, and wipe "
        "between sessions is the reset. Scenarios requesting restore "
        "should be rewritten to leave_in_place cleanup."
    )
```

Add near the top of the file:

```python
class CleanupNotSupported(Exception):
    """Raised when a scenario requests a cleanup action inconsistent
    with the production operating model."""
```

**`scenario.py`, `Cleanup` dataclass and `_parse_cleanup`:**

Change the default value of `restore_state` from `"pre_probe_snapshot"` to `"leave_in_place"`. Update the `_one_of` allowed set to include `"leave_in_place"` alongside `pre_probe_snapshot`, `none`, and `custom`.

**`runner.py`, `_cleanup()`:**

Replace the body with:

```python
async def _cleanup(self) -> None:
    """Post-scenario cleanup.

    Under Joe's production operating model, the default is
    leave_in_place: the harness makes no attempt to reset substrate
    state. Data accumulates across scenarios in one session; wipe
    between sessions is Joe's explicit action.

    Scenarios can override to explicit pre_probe_snapshot restore or
    to none, but those are exceptions to the model. The default is
    leave-in-place because production is the workbench, not sacred
    ground to be restored.
    """
    cleanup = self.config.scenario.cleanup

    if cleanup.restore_state == "leave_in_place":
        self._add_finding(
            "INFO", "runner",
            "state left in place per production-mode operating model"
        )
        return

    if cleanup.restore_state == "none":
        return

    if cleanup.restore_state == "pre_probe_snapshot":
        if self._snapshot_id is None:
            self._add_finding(
                "WARN", "runner",
                "cleanup requested restore but no snapshot was taken"
            )
            return
        try:
            await self.config.substrate.restore_state(self._snapshot_id)
        except CleanupNotSupported as e:
            self._add_finding(
                "WATCH", "runner",
                f"restore skipped — scenario requested restore but "
                f"operating model does not support it: {e}"
            )
        except NotImplementedError as e:
            self._add_finding(
                "WATCH", "runner",
                f"restore skipped: {e}"
            )
        except Exception as e:
            self._add_finding(
                "WARN", "runner",
                f"restore failed: {type(e).__name__}: {e}"
            )
        return
```

Note the DIRTY marker path is gone entirely. Restore failures under this model are noted as findings but don't halt subsequent runs.

Import `CleanupNotSupported` from `substrate_client` at the top of `runner.py`.

## Verification

Two dry-run checks and one real check:

**Dry-run 1:** re-run `python -m harness validate scenarios/mechanism/cross_sense_recall_basic.yaml`. Should still pass — the schema allowed `pre_probe_snapshot` and now also allows `leave_in_place`.

**Dry-run 2:** create a scratch scenario file at `/tmp/leave_in_place_test.yaml` copied from `cross_sense_recall_basic.yaml` but with `cleanup.restore_state: leave_in_place`. Run `python -m harness validate /tmp/leave_in_place_test.yaml`. Should pass.

**Real check:** re-run the deploy-dispatch's Step 5 scenario invocation against primary:
```
python -m harness run scenarios/mechanism/cross_sense_recall_basic.yaml \
    --target <primary substrate URL> \
    --auth ~/.guala/harness-admin-token.json \
    --aws-config ~/.guala/aws-config.json \
    --reports-dir ./reports
```

Expected: still `PRECONDITION_NOT_MET` because primary should still be in the quiescent-clean state, and the scenario declares `substrate_state: clean_slate`. That's fine — the precondition check is correctly identifying that nothing has been deliberately routed to primary yet. What the run must NOT do: it must not attempt restore during cleanup, it must not mark anything DIRTY.

If a probe were injected (which it isn't at precondition_not_met), cleanup would default to leave-in-place. That's the model.

## Report

`GL-RPT-HARNESS-PRIMARY-MODEL-C1-20260706-v1.md` with:
- Files touched (should be exactly two: `substrate_client.py`, `runner.py`, plus the small change to `scenario.py`).
- Diff summary per file.
- Verify dry-run 1 result.
- Verify dry-run 2 result.
- Verify real check result — verdict, findings, confirmation cleanup didn't attempt restore.
- Commit SHA and push to guala-live.

Do not ask Joe questions. Route any to Eve.

## Scope guardrails

Do NOT:
- Rewrite the harness spec doc. The doc gets updated by Eve after this dispatch lands, referencing this dispatch as the mechanism. The doc is not code, and drift between doc and code is expected until Eve syncs them.
- Add new features.
- Add wipe automation. Wipe stays Joe's explicit action, not something the harness triggers.
- Modify the observability collectors, the CLI, or the report emitter.
- Modify scenarios. Eve owns scenarios.

One-at-a-time discipline applies: three code changes in three files, one commit, one report.

---

### Changelog
- v1 (2026-07-06, Eve): initial dispatch. Two files touched (substrate_client, runner) plus one small default change in scenario.py. Under Joe's ratified production-as-workbench model, cleanup defaults to leave-in-place, restore is no longer required, DIRTY marker mechanism removed. Restore stays in the code as an optional path with a proper `CleanupNotSupported` exception when a scenario requests it but the substrate can't do it. Bounded scope, no new features.
