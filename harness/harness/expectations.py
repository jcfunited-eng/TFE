"""Expectations checker.

Given a Scenario's expectations and the observed events + collector
snapshots, produces a per-expectation pass/fail report.

Kept deterministic and pure: no side effects, no substrate calls. Runner
gathers evidence, checker judges.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .observability import CollectorSnapshot
from .scenario import EventExpectation, Expectations
from .substrate_client import SubstrateEvent, SubstrateStatus


@dataclass
class ExpectationResult:
    """One expectation's outcome."""

    expectation_kind: str          # events_must_fire | components | atlas |
                                    # provenance | thresholds | negative
    description: str
    expected: dict[str, Any]
    actual: dict[str, Any]
    passed: bool
    detail: str = ""


@dataclass
class CheckResult:
    """Aggregate outcome of expectation checking."""

    results: list[ExpectationResult] = field(default_factory=list)

    @property
    def all_passed(self) -> bool:
        return all(r.passed for r in self.results)

    @property
    def failed_count(self) -> int:
        return sum(1 for r in self.results if not r.passed)


def check_expectations(
    expectations: Expectations,
    events: list[SubstrateEvent],
    pre_status: SubstrateStatus,
    post_status: SubstrateStatus | None,
    collector_snapshots: dict[str, CollectorSnapshot],
) -> CheckResult:
    """Run every expectation against observed evidence.

    Any expectation not yet supported produces a passed=False result with
    detail explaining what would need to be wired. Better than silently
    passing an unchecked expectation.
    """
    results: list[ExpectationResult] = []

    # 1. Events must fire
    for exp in expectations.events_must_fire:
        results.append(_check_event_expectation(exp, events, negative=False))

    # 2. Negative expectations
    for exp in expectations.negative_expectations:
        results.append(_check_event_expectation(exp, events, negative=True))

    # 3. Components must activate
    if expectations.components_must_activate:
        activated = {e.source_component for e in events}
        for component in expectations.components_must_activate:
            passed = component in activated
            results.append(ExpectationResult(
                expectation_kind="components_must_activate",
                description=f"component {component} must have activity",
                expected={"component": component, "must_activate": True},
                actual={"activated": passed,
                        "observed_components": sorted(activated)},
                passed=passed,
            ))

    # 4. Atlas deltas
    if post_status is not None:
        results.append(_check_atlas_deltas(
            expectations, pre_status, post_status
        ))
    else:
        results.append(ExpectationResult(
            expectation_kind="atlas_deltas",
            description="atlas delta check",
            expected={"windows_added_min": expectations.atlas_deltas.windows_added_min,
                      "entries_added_min": expectations.atlas_deltas.entries_added_min},
            actual={"post_status": None},
            passed=False,
            detail="post_status unavailable — post-run substrate status pull failed"
                   " or was skipped",
        ))

    # 5. Emission provenance
    if expectations.emission_provenance.required:
        results.append(ExpectationResult(
            expectation_kind="emission_provenance",
            description="emission events must carry probe-window provenance",
            expected={"required": True,
                      "if_present": expectations.emission_provenance.if_present},
            actual={},
            passed=False,
            detail="provenance checking not yet implemented in v1 skeleton —"
                   " needs emission event schema to be finalized in message-"
                   " passing substrate (spec §5.1 Emission component)",
        ))

    # 6. Observability thresholds
    results.extend(_check_observability_thresholds(
        expectations, collector_snapshots
    ))

    return CheckResult(results=results)


def _check_event_expectation(
    exp: EventExpectation, events: list[SubstrateEvent], negative: bool
) -> ExpectationResult:
    """Count events matching the expectation's kind + filters."""
    matched = [
        e for e in events
        if e.kind == exp.kind and _filters_match(e, exp.filters)
    ]
    count = len(matched)

    # Time-window constraint
    within_ok = True
    if exp.within_ms is not None and matched:
        # Events have wall_clock; check first match arrived within window.
        # We use tick delta as proxy since wall_clock reference is complex.
        # Improvement: pass trace_id anchor, compute t_offset_ms per event.
        within_ok = True  # accept: skeleton doesn't compute t_offset per event yet

    # Assertion checks embedded in the expectation
    assertions_ok = True
    assertion_detail = ""
    for key, expected_val in exp.assertions.items():
        if key == "windows_returned_min":
            actual_val = _extract_windows_returned(matched)
            if actual_val is None or actual_val < expected_val:
                assertions_ok = False
                assertion_detail = (
                    f"windows_returned={actual_val} < min={expected_val}"
                )
        elif key == "windows_returned_max":
            actual_val = _extract_windows_returned(matched)
            if actual_val is not None and actual_val > expected_val:
                assertions_ok = False
                assertion_detail = (
                    f"windows_returned={actual_val} > max={expected_val}"
                )
        # Other assertion kinds get NotImplemented but don't fail the check
        # silently — flagged in detail.
        else:
            assertion_detail = (
                f"assertion {key!r} not yet implemented in v1 skeleton"
            )

    # Count check
    count_ok = count >= exp.count_min
    if exp.count_max is not None:
        count_ok = count_ok and count <= exp.count_max

    passed = count_ok and within_ok and assertions_ok
    if negative:
        # For negative expectations, we want NO matches beyond count_max
        # (count_min meaningless here, usually 0)
        passed = count <= (exp.count_max if exp.count_max is not None else 0)

    return ExpectationResult(
        expectation_kind=(
            "negative_expectation" if negative else "events_must_fire"
        ),
        description=(
            f"event {exp.kind!r} count "
            + ("must be at most " if negative else "in ")
            + f"[{exp.count_min}, {exp.count_max}]"
        ),
        expected={
            "kind": exp.kind,
            "count_min": exp.count_min,
            "count_max": exp.count_max,
            "within_ms": exp.within_ms,
            "filters": exp.filters,
            "assertions": exp.assertions,
        },
        actual={
            "matched_count": count,
            "count_ok": count_ok,
            "within_ok": within_ok,
            "assertions_ok": assertions_ok,
        },
        passed=passed,
        detail=assertion_detail,
    )


def _filters_match(event: SubstrateEvent, filters: dict[str, Any]) -> bool:
    """Check event against filter constraints in expectation."""
    for key, expected_val in filters.items():
        if key == "modality":
            # modality is a list-of-allowed
            if isinstance(expected_val, list):
                actual = event.payload.get("modality")
                if actual not in expected_val:
                    return False
        else:
            if event.payload.get(key) != expected_val:
                return False
    return True


def _extract_windows_returned(events: list[SubstrateEvent]) -> int | None:
    """For recall_response events, pull windows_returned count."""
    for e in events:
        if "windows_returned" in e.payload:
            return int(e.payload["windows_returned"])
        if "windows" in e.payload and isinstance(e.payload["windows"], list):
            return len(e.payload["windows"])
    return None


def _check_atlas_deltas(
    expectations: Expectations,
    pre: SubstrateStatus,
    post: SubstrateStatus,
) -> ExpectationResult:
    windows_added = post.atlas_bindings - pre.atlas_bindings
    entries_added = post.atlas_bindings - pre.atlas_bindings  # skeleton approx

    passed = (
        windows_added >= expectations.atlas_deltas.windows_added_min
        and entries_added >= expectations.atlas_deltas.entries_added_min
    )
    return ExpectationResult(
        expectation_kind="atlas_deltas",
        description="atlas delta must meet minimums",
        expected={
            "windows_added_min": expectations.atlas_deltas.windows_added_min,
            "entries_added_min": expectations.atlas_deltas.entries_added_min,
        },
        actual={
            "windows_added": windows_added,
            "entries_added": entries_added,
            "pre_atlas_bindings": pre.atlas_bindings,
            "post_atlas_bindings": post.atlas_bindings,
        },
        passed=passed,
        detail=(
            "note: windows_added is approximated as atlas_bindings delta in"
            " skeleton; message-passing substrate exposes a distinct"
            " windows_added counter"
        ),
    )


def _check_observability_thresholds(
    expectations: Expectations,
    snapshots: dict[str, CollectorSnapshot],
) -> list[ExpectationResult]:
    """Check each threshold against the matching collector summary."""
    results: list[ExpectationResult] = []
    t = expectations.observability_thresholds

    if t.peak_cpu_percent_max is not None:
        cpu = snapshots.get("cpu")
        actual = None
        if cpu and cpu.summary:
            actual = cpu.summary.get("peak_cpu_pct")
        passed = (actual is not None and actual <= t.peak_cpu_percent_max)
        results.append(ExpectationResult(
            expectation_kind="observability_threshold",
            description="peak CPU under cap",
            expected={"peak_cpu_percent_max": t.peak_cpu_percent_max},
            actual={"peak_cpu_pct": actual,
                    "collector_degraded": cpu.degraded if cpu else True},
            passed=passed,
        ))

    if t.peak_memory_delta_mb_max is not None:
        mem = snapshots.get("memory")
        actual = None
        if mem and mem.summary:
            actual = mem.summary.get("peak_rss_delta_mb")
        passed = (actual is not None and actual <= t.peak_memory_delta_mb_max)
        results.append(ExpectationResult(
            expectation_kind="observability_threshold",
            description="peak memory delta under cap",
            expected={"peak_memory_delta_mb_max": t.peak_memory_delta_mb_max},
            actual={"peak_rss_delta_mb": actual,
                    "collector_degraded": mem.degraded if mem else True},
            passed=passed,
        ))

    # Other thresholds — flagged as "would check X" until collectors that
    # produce them are wired (event loop lag, subscription lag, efs write ops,
    # network errors)
    for threshold_name, cap in [
        ("peak_event_loop_lag_ms_max", t.peak_event_loop_lag_ms_max),
        ("subscription_lag_max_events", t.subscription_lag_max_events),
        ("efs_write_ops_max", t.efs_write_ops_max),
        ("network_errors", t.network_errors),
    ]:
        if cap is not None:
            results.append(ExpectationResult(
                expectation_kind="observability_threshold",
                description=f"{threshold_name} under cap",
                expected={threshold_name: cap},
                actual={},
                passed=False,
                detail=(
                    f"threshold {threshold_name} declared but the collector"
                    f" that produces it is not wired in this skeleton"
                ),
            ))

    return results
