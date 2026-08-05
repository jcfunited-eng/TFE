"""Observability collectors package.

Each collector corresponds to a §5 subsection of the harness spec.
Concrete collectors present:

- CPUCollector (§5.3)                       — via /proc/stat, working
- MemoryCollector (§5.4)                    — via /proc/self/status + /proc/meminfo, working
- EventStreamCollector (§5.1)               — subscribes to substrate events, wiring depends on SubstrateClient
- CloudWatchMetricsCollector (§5.3, §5.4)   — ECS task metrics, not wired
- EFSBurstCreditCollector (§5.5)            — the sneaky-hang detector, not wired
- ALBMetricsCollector (§5.6)                — ALB request/errors, not wired
- ECSHealthCollector (§5.8)                 — task/deploy health, not wired
- CloudTrailCollector (§5.9)                — substrate role activity, not wired
- CloudWatchLogsCollector (§5.11)           — substrate log stream, not wired

Not yet present (skeleton scope decision):
- §5.6 detailed network (TCP retransmits, DNS) via /proc/net — skeleton would work
  but adds volume; deferred until AWS wiring since ALB metrics cover the
  external network surface for the common case
- §5.7 concurrency signals — needs asyncio + os-side probes; deferred with
  a stub interface below (ConcurrencySignalsCollector) — real for message-
  passing substrate, less useful for current lock-based one
- §5.12 storage state — needs EFS mount access from the harness runner
  which requires deploy in-cluster, not on developer machine; deferred

All present collectors implement the base Collector interface; adding a
new one is a new file plus one line in _instantiate_collectors below.
"""
from __future__ import annotations

from ..substrate_client import SubstrateClient
from ..types import TraceId
from .aws_signals import (
    ALBMetricsCollector,
    CloudTrailCollector,
    CloudWatchLogsCollector,
    CloudWatchMetricsCollector,
    ECSHealthCollector,
    EFSBurstCreditCollector,
)
from .collector import Collector, CollectorSnapshot, Sample
from .cpu import CPUCollector
from .event_stream import EventStreamCollector
from .memory import MemoryCollector

__all__ = [
    "Collector",
    "CollectorSnapshot",
    "Sample",
    "CPUCollector",
    "MemoryCollector",
    "EventStreamCollector",
    "CloudWatchMetricsCollector",
    "EFSBurstCreditCollector",
    "ALBMetricsCollector",
    "ECSHealthCollector",
    "CloudTrailCollector",
    "CloudWatchLogsCollector",
    "instantiate_collectors",
]


def instantiate_collectors(
    trace_id: TraceId,
    substrate: SubstrateClient,
    initial_tick: int,
    aws_config: dict | None = None,
) -> list[Collector]:
    """Build the collector set for one run.

    aws_config keys expected when AWS collectors get wired:
        cluster, service, filesystem_id, load_balancer_arn,
        target_group_arn, task_role_arn, execution_role_arn, log_group

    When aws_config is None, AWS collectors still instantiate — they mark
    themselves degraded on first sample rather than being silently omitted.
    Explicit degraded is better than invisible absence.
    """
    aws = aws_config or {}
    collectors: list[Collector] = [
        # Local / substrate-side
        EventStreamCollector(trace_id, substrate, since_tick=initial_tick),
        CPUCollector(trace_id),
        MemoryCollector(trace_id),
        # AWS-side (all NotWired until GL-CMD-HARNESS-AWS-WIRING lands)
        CloudWatchMetricsCollector(
            trace_id,
            cluster=aws.get("cluster", ""),
            service=aws.get("service", ""),
        ),
        EFSBurstCreditCollector(
            trace_id,
            filesystem_id=aws.get("filesystem_id", ""),
        ),
        ALBMetricsCollector(
            trace_id,
            load_balancer_arn=aws.get("load_balancer_arn", ""),
            target_group_arn=aws.get("target_group_arn", ""),
        ),
        ECSHealthCollector(
            trace_id,
            cluster=aws.get("cluster", ""),
            service=aws.get("service", ""),
        ),
        CloudTrailCollector(
            trace_id,
            substrate_task_role_arn=aws.get("task_role_arn", ""),
            substrate_execution_role_arn=aws.get("execution_role_arn", ""),
        ),
        CloudWatchLogsCollector(
            trace_id,
            log_group=aws.get("log_group", ""),
        ),
    ]
    return collectors
