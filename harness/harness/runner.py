"""Runner — the orchestrator.

Follows spec §4.2 runtime sequence step by step. Each numbered step in
run() maps to the corresponding numbered step in the spec.

Design constraints:
- Async throughout so collectors run concurrently with probe injection.
- Every failure mode has a defined verdict. Silent hangs are forbidden;
  every wait has a timeout with a distinct exit code.
- Runner does not judge — checker judges. Runner gathers evidence and
  hands it off. This keeps the runner deterministic and the report
  reproducible.
"""
from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from . import __version__
from .expectations import check_expectations
from .observability import CollectorSnapshot, instantiate_collectors
from .observability.event_stream import EventStreamCollector
from .report import RunReport
from .scenario import Scenario
from .substrate_client import CleanupNotSupported, SubstrateClient, SubstrateStatus
from .types import Finding, TraceId, Verdict


@dataclass
class RunnerConfig:
    """Configuration for one runner invocation."""

    substrate: SubstrateClient
    scenario: Scenario
    reports_dir: Path
    aws_config: dict | None = None
    dry_run: bool = False
    verbose: bool = False
    capture_only: bool = False


class Runner:
    """One-shot orchestrator for a single scenario run."""

    def __init__(self, config: RunnerConfig):
        self.config = config
        self.trace_id = TraceId()
        self.findings: list[Finding] = []
        self.probe_actions: list[dict[str, Any]] = []
        self._pre_status: SubstrateStatus | None = None
        self._post_status: SubstrateStatus | None = None
        self._snapshot_id: str | None = None

    async def run(self) -> RunReport:
        """Execute the full runtime sequence. Returns the RunReport."""
        wall_start = datetime.now(timezone.utc).isoformat()
        run_start = time.monotonic()
        collectors = []
        verdict = Verdict.FAIL  # default until we know otherwise
        events = []
        collector_snapshots: dict[str, CollectorSnapshot] = {}
        check_result = None

        try:
            # Step 1: Parse and validate — already done by caller before we
            # got here. We just verify basics.
            if self.config.dry_run:
                self._add_finding("INFO", "runner",
                                  "dry-run: not executing steps 2-10")
                verdict = Verdict.PASS
                return self._assemble_report(
                    verdict, wall_start, run_start,
                    events, collector_snapshots, check_result
                )

            # Step 2: Precondition check
            try:
                self._pre_status = await self._precondition_check()
            except _PreconditionFailed as e:
                self._add_finding(
                    "CRITICAL", "runner",
                    f"precondition not met: {e}",
                )
                verdict = Verdict.PRECONDITION_NOT_MET
                return self._assemble_report(
                    verdict, wall_start, run_start,
                    events, collector_snapshots, check_result
                )

            # Step 3: Pre-run snapshot
            try:
                self._snapshot_id = await self.config.substrate.snapshot_state(
                    label=f"harness_pre_{self.trace_id.id[:8]}"
                )
            except NotImplementedError as e:
                self._add_finding(
                    "WATCH", "runner",
                    f"pre-run snapshot skipped: {e}"
                )
            except Exception as e:
                self._add_finding(
                    "WARN", "runner",
                    f"pre-run snapshot failed: {type(e).__name__}: {e}"
                )

            # Step 4: Start observability capture
            initial_tick = (
                self._pre_status.tick if self._pre_status else 0
            )
            collectors = instantiate_collectors(
                self.trace_id,
                self.config.substrate,
                initial_tick=initial_tick,
                aws_config=self.config.aws_config,
            )
            for c in collectors:
                await c.start()

            # Step 5: Inject probe
            await self._inject_probe()

            # Step 6: Run to completion
            verdict = await self._wait_for_completion(collectors)

            # Step 7: Stop observability capture
            for c in collectors:
                await c.stop()

            # Collect event stream separately (it's the load-bearing collector)
            for c in collectors:
                snapshot = c.snapshot()
                collector_snapshots[c.name] = snapshot
                if isinstance(c, EventStreamCollector):
                    events = c.events()

            # Grab post_status before cleanup so deltas can be computed
            try:
                self._post_status = await self.config.substrate.status()
            except Exception as e:
                self._add_finding(
                    "WARN", "runner",
                    f"post-run status failed: {type(e).__name__}: {e}"
                )

            # Step 8: Cleanup
            await self._cleanup()

            # Step 9: Assemble report (below via _assemble_report)
            # Step 10: Return verdict — encoded in the report

            # Check expectations unless capture-only
            if not self.config.capture_only:
                check_result = check_expectations(
                    self.config.scenario.expectations,
                    events,
                    self._pre_status or _null_status(),
                    self._post_status,
                    collector_snapshots,
                )
                if not check_result.all_passed:
                    verdict = Verdict.FAIL

        except Exception as e:
            self._add_finding(
                "CRITICAL", "runner",
                f"unhandled runner exception: {type(e).__name__}: {e}"
            )
            verdict = Verdict.FAIL
            # Ensure collectors get stopped even on error
            for c in collectors:
                try:
                    await c.stop()
                except Exception:
                    pass

        return self._assemble_report(
            verdict, wall_start, run_start,
            events, collector_snapshots, check_result
        )

    async def _precondition_check(self) -> SubstrateStatus:
        """Verify substrate state matches scenario preconditions."""
        try:
            status = await self.config.substrate.status()
        except NotImplementedError as e:
            raise _PreconditionFailed(
                f"substrate.status() not implemented on this client: {e}"
            )
        except Exception as e:
            raise _PreconditionFailed(
                f"substrate.status() failed: {type(e).__name__}: {e}"
            )

        pre = self.config.scenario.preconditions

        # Presence state check
        for role in ("joe", "wc", "c1"):
            expected = getattr(pre.presence_state, role)
            actual = status.presence.get(role, False)
            if expected != actual:
                raise _PreconditionFailed(
                    f"presence.{role} expected {expected}, actual {actual}"
                )

        # Substrate state check
        if pre.substrate_state == "clean_slate":
            if status.tick != 0:
                raise _PreconditionFailed(
                    f"clean_slate expected tick=0, actual tick={status.tick}"
                )
            if status.vocab_size != 0:
                raise _PreconditionFailed(
                    f"clean_slate expected vocab_size=0, actual "
                    f"{status.vocab_size}"
                )
            if status.atlas_bindings != 0:
                raise _PreconditionFailed(
                    f"clean_slate expected atlas_bindings=0, actual "
                    f"{status.atlas_bindings}"
                )

        # Suppression flag check — best-effort; the substrate exposes these
        # differently per implementation, so a soft check is more honest
        # than a hard one that reads a field that may not exist.
        # TODO: wire once substrate_client returns suppression state.

        return status

    async def _inject_probe(self) -> None:
        """Fire probe steps at their declared t_offset_ms."""
        probe = self.config.scenario.probe

        if probe.method == "sequence" and probe.sequence:
            steps = probe.sequence
        else:
            # Single-method probe: build a synthetic single-step sequence
            from .scenario import ProbeStep
            steps = [ProbeStep(
                t_offset_ms=0,
                method=probe.method,
                payload={},  # single-method probes don't have declared payload in schema
            )]

        for step in steps:
            # Wait until this step's t_offset_ms
            target_offset = step.t_offset_ms / 1000.0
            elapsed = self.trace_id.t_offset_ms() / 1000.0
            if target_offset > elapsed:
                await asyncio.sleep(target_offset - elapsed)

            action: dict[str, Any] = {
                "t_offset_ms": self.trace_id.t_offset_ms(),
                "method": step.method,
                "auth_as": probe.auth_as,
            }
            try:
                outcome = await self.config.substrate.inject_probe(
                    method=step.method,
                    payload=step.payload,
                    auth_as=probe.auth_as,
                )
                action["outcome"] = "ok"
                action["response"] = outcome
            except NotImplementedError as e:
                action["outcome"] = f"not_implemented: {e}"
                self._add_finding(
                    "WATCH", "runner",
                    f"probe step {step.method} not implemented on this client"
                )
            except Exception as e:
                action["outcome"] = f"error: {type(e).__name__}: {e}"
                self._add_finding(
                    "WARN", "runner",
                    f"probe step {step.method} failed: {e}"
                )
            self.probe_actions.append(action)

    async def _wait_for_completion(
        self, collectors: list
    ) -> Verdict:
        """Wait until timeout or all expectations met.

        Skeleton behavior: simply waits timeout_sec. Real behavior would
        also check expectations as events arrive and finish early on
        expectation-met. That's a v1.1 enhancement — the skeleton runs
        the full window every time to make traces comparable across runs.
        """
        timeout = self.config.scenario.run.timeout_sec
        try:
            await asyncio.sleep(timeout)
        except asyncio.CancelledError:
            raise
        return Verdict.PASS  # Provisional; expectation checker may override

    async def _cleanup(self) -> None:
        """Post-scenario cleanup.

        Under Joe's production operating model, the default is
        leave_in_place: the harness makes no attempt to reset
        substrate state. Data accumulates across scenarios in one
        session; wipe between sessions is Joe's explicit action.
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
                self._add_finding("WATCH", "runner", f"restore skipped: {e}")
            except Exception as e:
                self._add_finding(
                    "WARN", "runner",
                    f"restore failed: {type(e).__name__}: {e}"
                )
            return

    def _assemble_report(
        self,
        verdict: Verdict,
        wall_start: str,
        run_start: float,
        events,
        collector_snapshots: dict[str, CollectorSnapshot],
        check_result,
    ) -> RunReport:
        wall_end = datetime.now(timezone.utc).isoformat()
        duration_ms = int((time.monotonic() - run_start) * 1000)
        return RunReport(
            scenario=self.config.scenario,
            trace_id=self.trace_id,
            verdict=verdict,
            substrate_sha=None,  # populated once substrate exposes it
            harness_version=__version__,
            wall_start=wall_start,
            wall_end=wall_end,
            duration_ms=duration_ms,
            pre_status=self._pre_status,
            post_status=self._post_status,
            probe_actions=self.probe_actions,
            events=list(events),
            collector_snapshots=collector_snapshots,
            check_result=check_result,
            findings=self.findings,
        )

    def _add_finding(self, severity: str, source: str, message: str, **detail):
        self.findings.append(Finding(
            severity=severity,
            source=source,
            message=message,
            detail=detail,
            t_offset_ms=self.trace_id.t_offset_ms(),
        ))


class _PreconditionFailed(Exception):
    """Internal signal: precondition check couldn't be satisfied."""


def _null_status() -> SubstrateStatus:
    """Zero-valued status for cases where pre_status pull failed but we
    still want to run expectation checking against post_status alone."""
    return SubstrateStatus(
        tick=0,
        identity="",
        current_activity=None,
        vocab_size=0,
        atlas_bindings=0,
        deep_atlas_entries=0,
        organism_neurons=0,
        presence={"joe": False, "wc": False, "c1": False},
        ladder={},
        raw={},
    )
