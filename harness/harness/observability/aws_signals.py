"""AWS-side observability collectors.

Wired per `GL-CMD-HARNESS-DEPLOY-EVE-20260706-v1` §4. Each collector maps
to a specific spec §5 subsection:

- CloudWatchMetricsCollector    → §5.3 (task-level CPU), §5.4 (task-level memory)
- EFSBurstCreditCollector       → §5.5 (BurstCreditBalance CloudWatch metric)
- ALBMetricsCollector           → §5.6 network (ALB request/error counts + target health)
- ECSHealthCollector            → §5.8 (task health, deployment events)
- CloudTrailCollector           → §5.9 (auth activity on substrate IAM roles)
- CloudWatchLogsCollector       → §5.11 (log stream during window)

IAM policy required (name: GualaHarnessObservability, attached to the
invoking developer's credential or a dedicated harness role):
    cloudwatch:GetMetricStatistics
    cloudwatch:GetMetricData
    logs:StartQuery
    logs:GetQueryResults
    ecs:DescribeTasks
    ecs:DescribeServices
    cloudtrail:LookupEvents
    elasticloadbalancing:DescribeTargetHealth

Every collector below makes a real boto3 call, not a stub. Failure
handling is the base Collector class's job (collector.py's _run() loop
catches any exception from _sample_once and marks the collector
degraded) — these implementations raise on real errors rather than
swallowing them, so a missing IAM permission or a wrong ARN shows up as a
degraded collector with the actual boto3 error message, not a silent
empty result.
"""
from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone
from typing import Any

from ..types import TraceId
from .collector import Collector, Sample


def _cloudwatch_client():
    import boto3
    return boto3.client("cloudwatch")


def _lb_dimension_value(load_balancer_arn: str) -> str:
    """CloudWatch's LoadBalancer dimension wants 'app/name/id', which is the
    tail of the ARN after 'loadbalancer/' — not the full ARN."""
    marker = "loadbalancer/"
    idx = load_balancer_arn.find(marker)
    return load_balancer_arn[idx + len(marker):] if idx != -1 else load_balancer_arn


def _tg_dimension_value(target_group_arn: str) -> str:
    """CloudWatch's TargetGroup dimension wants 'targetgroup/name/id'."""
    marker = "targetgroup/"
    idx = target_group_arn.find(marker)
    return target_group_arn[idx:] if idx != -1 else target_group_arn


class EFSBurstCreditCollector(Collector):
    """EFS BurstCreditBalance from CloudWatch — spec §5.5, "the sneaky-hang
    catcher". Burst exhaustion produces sudden 10x slowdowns that look like
    substrate hangs; this is the one most-missed cause of AWS-side
    slowness the spec calls out by name."""

    name = "aws_efs_burst_credit"
    sample_interval_ms = 60_000

    def __init__(self, trace_id: TraceId, filesystem_id: str):
        super().__init__(trace_id)
        self.filesystem_id = filesystem_id
        self._client = None

    async def _sample_once(self) -> Sample | None:
        if not self.filesystem_id:
            self._mark_degraded("no filesystem_id in aws_config")
            return None
        if self._client is None:
            self._client = _cloudwatch_client()
        now = datetime.now(timezone.utc)
        resp = self._client.get_metric_statistics(
            Namespace="AWS/EFS",
            MetricName="BurstCreditBalance",
            Dimensions=[{"Name": "FileSystemId", "Value": self.filesystem_id}],
            StartTime=now - timedelta(minutes=10),
            EndTime=now,
            Period=60,
            Statistics=["Average"],
        )
        points = sorted(resp.get("Datapoints", []), key=lambda p: p["Timestamp"])
        if not points:
            return Sample(
                t_offset_ms=self.trace_id.t_offset_ms(),
                values={"burst_credit_balance_bytes": None, "no_datapoints": True},
            )
        latest = points[-1]
        return Sample(
            t_offset_ms=self.trace_id.t_offset_ms(),
            values={"burst_credit_balance_bytes": latest["Average"]},
        )

    def _summarize(self) -> dict[str, Any]:
        vals = [
            s.values["burst_credit_balance_bytes"] for s in self._samples
            if s.values.get("burst_credit_balance_bytes") is not None
        ]
        if not vals:
            return {"sample_count": len(self._samples), "no_useful_samples": True}
        return {
            "sample_count": len(self._samples),
            "min_burst_credit_balance_bytes": min(vals),
            "max_burst_credit_balance_bytes": max(vals),
            "declining": vals[-1] < vals[0] if len(vals) > 1 else False,
        }


class CloudWatchMetricsCollector(Collector):
    """ECS service-level CPU + memory utilization from CloudWatch.

    Uses the standard AWS/ECS namespace (CPUUtilization/MemoryUtilization,
    ClusterName+ServiceName dimensions) rather than Container Insights
    metrics — works without Container Insights being enabled on the
    cluster, and the IAM policy this dispatch grants doesn't scope to it
    specifically.
    """

    name = "aws_cloudwatch_metrics"
    sample_interval_ms = 60_000

    def __init__(self, trace_id: TraceId, cluster: str, service: str):
        super().__init__(trace_id)
        self.cluster = cluster
        self.service = service
        self._client = None

    async def _sample_once(self) -> Sample | None:
        if not self.cluster or not self.service:
            self._mark_degraded("no cluster/service in aws_config")
            return None
        if self._client is None:
            self._client = _cloudwatch_client()
        now = datetime.now(timezone.utc)
        dims = [
            {"Name": "ClusterName", "Value": self.cluster},
            {"Name": "ServiceName", "Value": self.service},
        ]
        values: dict[str, Any] = {}
        for metric in ("CPUUtilization", "MemoryUtilization"):
            resp = self._client.get_metric_statistics(
                Namespace="AWS/ECS",
                MetricName=metric,
                Dimensions=dims,
                StartTime=now - timedelta(minutes=5),
                EndTime=now,
                Period=60,
                Statistics=["Average", "Maximum"],
            )
            points = sorted(resp.get("Datapoints", []), key=lambda p: p["Timestamp"])
            if points:
                values[f"{metric.lower()}_avg"] = points[-1]["Average"]
                values[f"{metric.lower()}_max"] = points[-1]["Maximum"]
        if not values:
            return Sample(
                t_offset_ms=self.trace_id.t_offset_ms(),
                values={"no_datapoints": True},
            )
        return Sample(t_offset_ms=self.trace_id.t_offset_ms(), values=values)


class ALBMetricsCollector(Collector):
    """ALB request/error counts (CloudWatch) + live target health
    (elasticloadbalancing:DescribeTargetHealth) during the run window."""

    name = "aws_alb_metrics"
    sample_interval_ms = 60_000

    def __init__(self, trace_id: TraceId, load_balancer_arn: str,
                 target_group_arn: str):
        super().__init__(trace_id)
        self.load_balancer_arn = load_balancer_arn
        self.target_group_arn = target_group_arn
        self._cw = None
        self._elbv2 = None

    async def _sample_once(self) -> Sample | None:
        if not self.load_balancer_arn or not self.target_group_arn:
            self._mark_degraded("no load_balancer_arn/target_group_arn in aws_config")
            return None
        if self._cw is None:
            self._cw = _cloudwatch_client()
        if self._elbv2 is None:
            import boto3
            self._elbv2 = boto3.client("elbv2")

        now = datetime.now(timezone.utc)
        lb_dim = _lb_dimension_value(self.load_balancer_arn)
        tg_dim = _tg_dimension_value(self.target_group_arn)
        dims = [
            {"Name": "LoadBalancer", "Value": lb_dim},
            {"Name": "TargetGroup", "Value": tg_dim},
        ]
        values: dict[str, Any] = {}
        for metric, stat in (
            ("RequestCount", "Sum"),
            ("HTTPCode_Target_4XX_Count", "Sum"),
            ("HTTPCode_Target_5XX_Count", "Sum"),
            ("TargetResponseTime", "Average"),
        ):
            resp = self._cw.get_metric_statistics(
                Namespace="AWS/ApplicationELB",
                MetricName=metric,
                Dimensions=dims,
                StartTime=now - timedelta(minutes=5),
                EndTime=now,
                Period=60,
                Statistics=[stat],
            )
            points = sorted(resp.get("Datapoints", []), key=lambda p: p["Timestamp"])
            if points:
                values[metric] = points[-1][stat]

        health = self._elbv2.describe_target_health(
            TargetGroupArn=self.target_group_arn
        )
        descriptions = health.get("TargetHealthDescriptions", [])
        healthy = sum(
            1 for d in descriptions
            if d.get("TargetHealth", {}).get("State") == "healthy"
        )
        values["healthy_target_count"] = healthy
        values["unhealthy_target_count"] = len(descriptions) - healthy

        return Sample(t_offset_ms=self.trace_id.t_offset_ms(), values=values)


class ECSHealthCollector(Collector):
    """ECS task health + deployment events. Sampled more frequently (5s)
    than the other 60s AWS collectors since a mid-run deploy invalidates
    the scenario per spec §5.8 — this needs to catch it, not average over
    it."""

    name = "aws_ecs_health"
    sample_interval_ms = 5_000

    def __init__(self, trace_id: TraceId, cluster: str, service: str):
        super().__init__(trace_id)
        self.cluster = cluster
        self.service = service
        self._client = None

    async def _sample_once(self) -> Sample | None:
        if not self.cluster or not self.service:
            self._mark_degraded("no cluster/service in aws_config")
            return None
        if self._client is None:
            import boto3
            self._client = boto3.client("ecs")

        svc_resp = self._client.describe_services(
            cluster=self.cluster, services=[self.service]
        )
        services = svc_resp.get("services", [])
        if not services:
            self._mark_degraded(
                f"describe_services returned no service named {self.service!r}"
            )
            return None
        svc = services[0]
        deployments = svc.get("deployments", [])
        in_progress_deploys = sum(
            1 for d in deployments if d.get("rolloutState") == "IN_PROGRESS"
        )

        task_arns = self._client.list_tasks(
            cluster=self.cluster, serviceName=self.service
        ).get("taskArns", [])
        healthy = 0
        tasks: list[dict[str, Any]] = []
        if task_arns:
            tasks = self._client.describe_tasks(
                cluster=self.cluster, tasks=task_arns
            ).get("tasks", [])
            healthy = sum(
                1 for t in tasks if t.get("healthStatus") == "HEALTHY"
            )

        return Sample(
            t_offset_ms=self.trace_id.t_offset_ms(),
            values={
                "desired_count": svc.get("desiredCount", 0),
                "running_count": svc.get("runningCount", 0),
                "task_count": len(tasks),
                "healthy_task_count": healthy,
                "in_progress_deployments": in_progress_deploys,
            },
        )

    def _summarize(self) -> dict[str, Any]:
        deploy_samples = [
            s for s in self._samples
            if s.values.get("in_progress_deployments", 0) > 0
        ]
        return {
            "sample_count": len(self._samples),
            # Deploys mid-run invalidate the scenario per spec §5.8 —
            # surfaced prominently, not buried in per-sample data.
            "deploy_detected_during_run": bool(deploy_samples),
        }


class CloudTrailCollector(Collector):
    """CloudTrail events attributed to the substrate's IAM roles during the
    run window. Anything beyond the harness's own actions is a finding —
    same "unaccounted-for activity halts" rule as the clean-slate check."""

    name = "aws_cloudtrail"
    sample_interval_ms = 30_000

    def __init__(self, trace_id: TraceId,
                 substrate_task_role_arn: str,
                 substrate_execution_role_arn: str):
        super().__init__(trace_id)
        self.task_role_arn = substrate_task_role_arn
        self.exec_role_arn = substrate_execution_role_arn
        self._client = None
        self._run_start = datetime.now(timezone.utc)

    async def _sample_once(self) -> Sample | None:
        if not self.task_role_arn and not self.exec_role_arn:
            self._mark_degraded("no task_role_arn/execution_role_arn in aws_config")
            return None
        if self._client is None:
            import boto3
            self._client = boto3.client("cloudtrail")

        now = datetime.now(timezone.utc)
        events: list[dict[str, Any]] = []
        for role_arn in (self.task_role_arn, self.exec_role_arn):
            if not role_arn:
                continue
            resp = self._client.lookup_events(
                LookupAttributes=[
                    {"AttributeKey": "Username", "AttributeValue": role_arn}
                ],
                StartTime=self._run_start,
                EndTime=now,
                MaxResults=50,
            )
            events.extend(resp.get("Events", []))

        return Sample(
            t_offset_ms=self.trace_id.t_offset_ms(),
            values={"events_seen_this_sample": len(events)},
        )

    def _summarize(self) -> dict[str, Any]:
        total = sum(s.values.get("events_seen_this_sample", 0) for s in self._samples)
        return {
            "sample_count": len(self._samples),
            "total_events_attributed_to_substrate_roles": total,
        }


class CloudWatchLogsCollector(Collector):
    """CloudWatch Logs Insights query for the substrate log group during
    the run window — severity histogram + error/fatal lines."""

    name = "aws_cloudwatch_logs"
    sample_interval_ms = 10_000

    def __init__(self, trace_id: TraceId, log_group: str):
        super().__init__(trace_id)
        self.log_group = log_group
        self._client = None
        self._run_start = int(time.time())

    async def _sample_once(self) -> Sample | None:
        if not self.log_group:
            self._mark_degraded("no log_group in aws_config")
            return None
        if self._client is None:
            import boto3
            self._client = boto3.client("logs")

        now = int(time.time())
        query = (
            'fields @timestamp, @message '
            '| filter @message like /ERROR/ or @message like /FATAL/ '
            '| sort @timestamp desc | limit 20'
        )
        start_resp = self._client.start_query(
            logGroupName=self.log_group,
            startTime=self._run_start,
            endTime=now,
            queryString=query,
        )
        query_id = start_resp["queryId"]
        # Logs Insights queries are async server-side; poll briefly for this
        # sample's result rather than blocking the collector loop for long.
        result: dict[str, Any] = {"status": "Timeout", "results": []}
        for _ in range(5):
            result = self._client.get_query_results(queryId=query_id)
            if result.get("status") in ("Complete", "Failed", "Cancelled"):
                break
            time.sleep(0.5)

        rows = result.get("results", [])
        error_lines = [
            next((f["value"] for f in row if f["field"] == "@message"), "")
            for row in rows
        ]
        return Sample(
            t_offset_ms=self.trace_id.t_offset_ms(),
            values={
                "query_status": result.get("status", "Unknown"),
                "error_or_fatal_lines_found": len(error_lines),
            },
        )

    def _summarize(self) -> dict[str, Any]:
        max_errors = max(
            (s.values.get("error_or_fatal_lines_found", 0) for s in self._samples),
            default=0,
        )
        return {
            "sample_count": len(self._samples),
            "max_error_or_fatal_lines_in_one_query": max_errors,
        }
