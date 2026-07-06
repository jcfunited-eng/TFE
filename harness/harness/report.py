"""Report emitter.

Renders the run's evidence and expectation results to the two artifacts
called for in spec §6:
- Structured markdown: `GL-RPT-HARNESS-<scenario-id>-<timestamp>-v1.md`
- Machine-readable JSON: `GL-RPT-HARNESS-<scenario-id>-<timestamp>-v1.json`

Both go to reports/ by default; the runner overrides the directory.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .expectations import CheckResult
from .observability import CollectorSnapshot
from .scenario import Scenario
from .substrate_client import SubstrateEvent, SubstrateStatus
from .types import Finding, TraceId, Verdict


@dataclass
class RunReport:
    """Aggregated everything from one run. Fed by the runner, rendered by
    the emitter functions below."""

    scenario: Scenario
    trace_id: TraceId
    verdict: Verdict
    substrate_sha: str | None
    harness_version: str
    wall_start: str
    wall_end: str
    duration_ms: int

    pre_status: SubstrateStatus | None
    post_status: SubstrateStatus | None

    probe_actions: list[dict[str, Any]] = field(default_factory=list)
    events: list[SubstrateEvent] = field(default_factory=list)
    collector_snapshots: dict[str, CollectorSnapshot] = field(default_factory=dict)
    check_result: CheckResult | None = None
    findings: list[Finding] = field(default_factory=list)

    def render(self, out_dir: Path) -> tuple[Path, Path]:
        """Write both artifacts. Returns (md_path, json_path)."""
        out_dir.mkdir(parents=True, exist_ok=True)
        base_id = self._doc_base_id()
        md_path = out_dir / f"{base_id}.md"
        json_path = out_dir / f"{base_id}.json"

        md_path.write_text(self._to_markdown())
        json_path.write_text(json.dumps(
            self._to_json_dict(), indent=2, default=str
        ))
        return md_path, json_path

    def _doc_base_id(self) -> str:
        # Convention: GL-RPT-HARNESS-<scenario-short>-<yyyymmddThhmmssZ>-v1
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        # Scenario id is already GL-SCN-<...>-v<N> — strip the GL-SCN- prefix
        # and version suffix to build a compact tag
        scenario_short = self.scenario.id
        for prefix in ("GL-SCN-", "GL-CMD-", "GL-RPT-"):
            if scenario_short.startswith(prefix):
                scenario_short = scenario_short[len(prefix):]
                break
        # Trim trailing -v<N>
        parts = scenario_short.rsplit("-v", 1)
        if len(parts) == 2 and parts[1].isdigit():
            scenario_short = parts[0]
        return f"GL-RPT-HARNESS-{scenario_short}-{stamp}-v1"

    # ---------- Markdown rendering ----------

    def _to_markdown(self) -> str:
        lines: list[str] = []
        lines.append(f"# {self._doc_base_id()}")
        lines.append("")
        lines.append(f"**Verdict:** {self.verdict.value}")
        lines.append("")
        lines.append(f"**Scenario:** {self.scenario.id}")
        lines.append(f"**Trace ID:** {self.trace_id.id}")
        lines.append(f"**Wall start:** {self.wall_start}")
        lines.append(f"**Wall end:** {self.wall_end}")
        lines.append(f"**Duration:** {self.duration_ms} ms")
        lines.append(f"**Harness version:** {self.harness_version}")
        lines.append(f"**Substrate SHA:** {self.substrate_sha or 'unknown'}")
        lines.append("")

        lines.append("## Probe summary")
        lines.append("")
        if not self.probe_actions:
            lines.append("_No probe actions recorded._")
        else:
            lines.append("| t_offset_ms | method | auth | outcome |")
            lines.append("|---:|---|---|---|")
            for a in self.probe_actions:
                lines.append(
                    f"| {a.get('t_offset_ms', 0)} | {a.get('method', '?')} "
                    f"| {a.get('auth_as', '?')} | {a.get('outcome', '?')} |"
                )
        lines.append("")

        lines.append("## Expected vs actual")
        lines.append("")
        if self.check_result is None:
            lines.append("_No expectation results (run halted before checking)._")
        else:
            for r in self.check_result.results:
                mark = "PASS" if r.passed else "FAIL"
                lines.append(f"- **{mark}** {r.expectation_kind}: {r.description}")
                if r.detail:
                    lines.append(f"  - Detail: {r.detail}")
                lines.append(f"  - Expected: `{r.expected}`")
                lines.append(f"  - Actual: `{r.actual}`")
        lines.append("")

        lines.append("## Event timeline")
        lines.append("")
        if not self.events:
            lines.append("_No events captured._")
        else:
            lines.append("| tick | source | kind | payload_summary |")
            lines.append("|---:|---|---|---|")
            for e in self.events[:200]:  # cap for readability
                payload_summary = ", ".join(
                    f"{k}={v}"
                    for k, v in list(e.payload.items())[:4]
                )
                lines.append(
                    f"| {e.tick} | {e.source_component} | {e.kind} "
                    f"| {payload_summary} |"
                )
            if len(self.events) > 200:
                lines.append(
                    f"| ... | ... | ... | (truncated: {len(self.events) - 200} more) |"
                )
        lines.append("")

        lines.append("## Observability")
        lines.append("")
        for name, snapshot in sorted(self.collector_snapshots.items()):
            lines.append(f"### {name}")
            if snapshot.degraded:
                lines.append(f"_Degraded: {snapshot.degraded_reason}_")
            lines.append(f"Samples: {len(snapshot.samples)}")
            for key, val in snapshot.summary.items():
                lines.append(f"- {key}: {val}")
            if snapshot.findings:
                for f in snapshot.findings:
                    lines.append(f"- **{f.severity}** {f.message}")
            lines.append("")

        lines.append("## Substrate state delta")
        lines.append("")
        if self.pre_status is None:
            lines.append("_pre_status unavailable._")
        elif self.post_status is None:
            lines.append("_post_status unavailable._")
        else:
            lines.append(f"- tick: {self.pre_status.tick} → {self.post_status.tick}")
            lines.append(
                f"- vocab: {self.pre_status.vocab_size} → "
                f"{self.post_status.vocab_size}"
            )
            lines.append(
                f"- atlas bindings: {self.pre_status.atlas_bindings} → "
                f"{self.post_status.atlas_bindings}"
            )
            lines.append(
                f"- organism neurons: {self.pre_status.organism_neurons} → "
                f"{self.post_status.organism_neurons}"
            )
        lines.append("")

        lines.append("## Findings")
        lines.append("")
        if not self.findings:
            lines.append("_No harness-level findings._")
        else:
            for f in self.findings:
                lines.append(f"- **{f.severity}** ({f.source}) {f.message}")
                if f.detail:
                    lines.append(f"  - `{f.detail}`")
        lines.append("")

        return "\n".join(lines)

    def _to_json_dict(self) -> dict[str, Any]:
        return {
            "doc_id": self._doc_base_id(),
            "verdict": self.verdict.value,
            "scenario_id": self.scenario.id,
            "trace_id": self.trace_id.id,
            "wall_start": self.wall_start,
            "wall_end": self.wall_end,
            "duration_ms": self.duration_ms,
            "substrate_sha": self.substrate_sha,
            "harness_version": self.harness_version,
            "probe_actions": self.probe_actions,
            "events": [asdict(e) for e in self.events],
            "collector_snapshots": {
                name: {
                    "name": s.name,
                    "sample_count": len(s.samples),
                    "summary": s.summary,
                    "degraded": s.degraded,
                    "degraded_reason": s.degraded_reason,
                    "findings": [asdict(f) for f in s.findings],
                }
                for name, s in self.collector_snapshots.items()
            },
            "check_results": (
                [asdict(r) for r in self.check_result.results]
                if self.check_result else []
            ),
            "findings": [asdict(f) for f in self.findings],
            "pre_status": (
                self._status_to_dict(self.pre_status)
                if self.pre_status else None
            ),
            "post_status": (
                self._status_to_dict(self.post_status)
                if self.post_status else None
            ),
        }

    @staticmethod
    def _status_to_dict(status: SubstrateStatus) -> dict[str, Any]:
        return {
            "tick": status.tick,
            "identity": status.identity,
            "current_activity": status.current_activity,
            "vocab_size": status.vocab_size,
            "atlas_bindings": status.atlas_bindings,
            "deep_atlas_entries": status.deep_atlas_entries,
            "organism_neurons": status.organism_neurons,
            "presence": status.presence,
            "ladder": status.ladder,
        }
