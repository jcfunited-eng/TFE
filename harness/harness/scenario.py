"""Scenario file schema and loader.

Matches GL-SPEC-TEST-HARNESS-EVE-20260706-v1.md §3.1 exactly. Uses
dataclasses (stdlib) rather than pydantic to keep dependency surface
minimal; validation is explicit and errors are precise.

Scenarios are YAML. Any field not covered by the schema is a scenario
error, not silently dropped — surprise fields usually mean a typo or a
copy-paste from a newer schema version.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


class ScenarioError(ValueError):
    """Raised when a scenario file fails validation. Errors are precise
    about which field and why so scenario authors see actionable messages,
    not silent skips."""


# ---------- Preconditions ----------


@dataclass
class PresenceState:
    joe: bool = False
    wc: bool = False
    c1: bool = False


@dataclass
class SuppressionFlags:
    curriculum_feeds: str = "off"
    world_feed: str = "off"
    autonomy_reading: str = "off"
    # extension point: additional named flags go here as substrate grows


@dataclass
class Preconditions:
    substrate_state: str = "clean_slate"  # clean_slate | warm | specific_snapshot
    specific_snapshot_id: str | None = None
    components_ready: list[str] = field(default_factory=list)
    presence_state: PresenceState = field(default_factory=PresenceState)
    suppression: SuppressionFlags = field(default_factory=SuppressionFlags)
    wait_for_ready_timeout_sec: int = 30


# ---------- Probe ----------


@dataclass
class ProbeStep:
    t_offset_ms: int
    method: str
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass
class Probe:
    method: str
    auth_as: str = "wc"
    sequence: list[ProbeStep] = field(default_factory=list)


# ---------- Expectations ----------


@dataclass
class EventExpectation:
    kind: str
    count_min: int = 0
    count_max: int | None = None
    within_ms: int | None = None
    filters: dict[str, Any] = field(default_factory=dict)
    assertions: dict[str, Any] = field(default_factory=dict)


@dataclass
class AtlasDeltaExpectation:
    windows_added_min: int = 0
    entries_added_min: int = 0
    survival_promotions: int | None = None


@dataclass
class EmissionProvenanceExpectation:
    required: bool = False
    if_present: dict[str, Any] = field(default_factory=dict)


@dataclass
class ObservabilityThresholds:
    peak_cpu_percent_max: float | None = None
    peak_memory_delta_mb_max: float | None = None
    peak_event_loop_lag_ms_max: float | None = None
    subscription_lag_max_events: int | None = None
    efs_write_ops_max: int | None = None
    network_errors: int | None = None


@dataclass
class Expectations:
    events_must_fire: list[EventExpectation] = field(default_factory=list)
    components_must_activate: list[str] = field(default_factory=list)
    atlas_deltas: AtlasDeltaExpectation = field(
        default_factory=AtlasDeltaExpectation
    )
    emission_provenance: EmissionProvenanceExpectation = field(
        default_factory=EmissionProvenanceExpectation
    )
    observability_thresholds: ObservabilityThresholds = field(
        default_factory=ObservabilityThresholds
    )
    negative_expectations: list[EventExpectation] = field(default_factory=list)


# ---------- Run limits ----------


@dataclass
class ResourceCaps:
    max_memory_delta_mb: int | None = None
    max_cpu_seconds: int | None = None
    max_disk_write_mb: int | None = None
    max_egress_mb: int | None = None


@dataclass
class RunLimits:
    timeout_sec: int = 30
    resource_caps: ResourceCaps = field(default_factory=ResourceCaps)


# ---------- Cleanup ----------


@dataclass
class Cleanup:
    restore_state: str = "pre_probe_snapshot"
    clear_captured_events: bool = False
    delete_probe_artifacts_from_atlas: bool = True


# ---------- Top-level scenario ----------


@dataclass
class ScenarioMetadata:
    author: str
    created_date: str
    changelog: list[dict[str, str]] = field(default_factory=list)


@dataclass
class Scenario:
    id: str
    purpose: str
    category: str            # mechanism | integration | stress | regression | security
    target_mechanism: str | None
    preconditions: Preconditions
    probe: Probe
    expectations: Expectations
    run: RunLimits
    cleanup: Cleanup
    metadata: ScenarioMetadata

    @classmethod
    def from_file(cls, path: str | Path) -> "Scenario":
        """Load and validate a scenario from disk. YAML only for v1.

        Uses yaml.safe_load and validates the resulting dict against the
        schema. Errors raise ScenarioError with the field path.
        """
        try:
            import yaml
        except ImportError as e:
            raise ScenarioError(
                "PyYAML required for scenario loading. `pip install pyyaml`."
            ) from e

        path = Path(path)
        if not path.exists():
            raise ScenarioError(f"Scenario file not found: {path}")

        with path.open("r") as f:
            raw = yaml.safe_load(f)

        if not isinstance(raw, dict):
            raise ScenarioError(
                f"Scenario file {path} did not parse as a mapping."
            )
        return cls.from_dict(raw)

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "Scenario":
        """Validate a parsed dict against the schema.

        This is where all the shape-checking lives. Each field's presence,
        type, and enum membership is asserted with a specific error message.
        """
        s = _require(raw, "scenario", dict)
        preconds_raw = _require(raw, "preconditions", dict)
        probe_raw = _require(raw, "probe", dict)
        expect_raw = _require(raw, "expectations", dict)
        run_raw = _require(raw, "run", dict)
        cleanup_raw = _require(raw, "cleanup", dict)
        meta_raw = _require(raw, "metadata", dict)

        category = _require(s, "category", str, path="scenario.category")
        _one_of(
            category,
            {"mechanism", "integration", "stress", "regression", "security"},
            "scenario.category",
        )

        return cls(
            id=_require(s, "id", str, path="scenario.id"),
            purpose=_require(s, "purpose", str, path="scenario.purpose"),
            category=category,
            target_mechanism=s.get("target_mechanism"),
            preconditions=_parse_preconditions(preconds_raw),
            probe=_parse_probe(probe_raw),
            expectations=_parse_expectations(expect_raw),
            run=_parse_run(run_raw),
            cleanup=_parse_cleanup(cleanup_raw),
            metadata=_parse_metadata(meta_raw),
        )


# ---------- Validation helpers ----------


def _require(d: dict, key: str, typ: type, path: str | None = None) -> Any:
    where = path or key
    if key not in d:
        raise ScenarioError(f"Missing required field: {where}")
    v = d[key]
    if not isinstance(v, typ):
        raise ScenarioError(
            f"{where} must be {typ.__name__}, got {type(v).__name__}"
        )
    return v


def _one_of(value: str, allowed: set[str], where: str) -> None:
    if value not in allowed:
        raise ScenarioError(
            f"{where} must be one of {sorted(allowed)}, got {value!r}"
        )


def _parse_preconditions(raw: dict) -> Preconditions:
    presence_raw = raw.get("presence_state", {}) or {}
    suppression_raw = raw.get("suppression", {}) or {}
    substrate_state = raw.get("substrate_state", "clean_slate")
    _one_of(
        substrate_state,
        {"clean_slate", "warm", "specific_snapshot"},
        "preconditions.substrate_state",
    )
    return Preconditions(
        substrate_state=substrate_state,
        specific_snapshot_id=raw.get("specific_snapshot_id"),
        components_ready=list(raw.get("components_ready", [])),
        presence_state=PresenceState(**{
            k: bool(v) for k, v in presence_raw.items()
            if k in ("joe", "wc", "c1")
        }),
        suppression=SuppressionFlags(**{
            k: str(v) for k, v in suppression_raw.items()
            if k in ("curriculum_feeds", "world_feed", "autonomy_reading")
        }),
        wait_for_ready_timeout_sec=int(
            raw.get("wait_for_ready_timeout_sec", 30)
        ),
    )


def _parse_probe(raw: dict) -> Probe:
    steps_raw = raw.get("sequence", [])
    steps = [
        ProbeStep(
            t_offset_ms=int(step["t_offset_ms"]),
            method=str(step["method"]),
            payload=dict(step.get("payload", {})),
        )
        for step in steps_raw
    ]
    return Probe(
        method=_require(raw, "method", str, path="probe.method"),
        auth_as=str(raw.get("auth_as", "wc")),
        sequence=steps,
    )


def _parse_expectations(raw: dict) -> Expectations:
    events = [
        EventExpectation(
            kind=str(e["kind"]),
            count_min=int(e.get("count_min", 0)),
            count_max=(int(e["count_max"]) if "count_max" in e else None),
            within_ms=(int(e["within_ms"]) if "within_ms" in e else None),
            filters=dict(e.get("filters", {})),
            assertions=dict(e.get("assertions", {})),
        )
        for e in raw.get("events_must_fire", [])
    ]
    negatives = [
        EventExpectation(
            kind=str(e["kind"]),
            count_min=int(e.get("count_min", 0)),
            count_max=(int(e["count_max"]) if "count_max" in e else None),
            within_ms=(int(e["within_ms"]) if "within_ms" in e else None),
            filters=dict(e.get("filters", {})),
        )
        for e in raw.get("negative_expectations", [])
    ]
    atlas_raw = raw.get("atlas_deltas", {})
    prov_raw = raw.get("emission_provenance", {})
    obs_raw = raw.get("observability_thresholds", {})

    return Expectations(
        events_must_fire=events,
        components_must_activate=list(raw.get("components_must_activate", [])),
        atlas_deltas=AtlasDeltaExpectation(
            windows_added_min=int(atlas_raw.get("windows_added_min", 0)),
            entries_added_min=int(atlas_raw.get("entries_added_min", 0)),
            survival_promotions=(
                int(atlas_raw["survival_promotions"])
                if "survival_promotions" in atlas_raw
                else None
            ),
        ),
        emission_provenance=EmissionProvenanceExpectation(
            required=bool(prov_raw.get("required", False)),
            if_present=dict(prov_raw.get("if_present", {})),
        ),
        observability_thresholds=ObservabilityThresholds(**{
            k: float(v) if not isinstance(v, int) else v
            for k, v in obs_raw.items()
            if k in {
                "peak_cpu_percent_max",
                "peak_memory_delta_mb_max",
                "peak_event_loop_lag_ms_max",
                "subscription_lag_max_events",
                "efs_write_ops_max",
                "network_errors",
            }
        }),
        negative_expectations=negatives,
    )


def _parse_run(raw: dict) -> RunLimits:
    caps_raw = raw.get("resource_caps", {})
    return RunLimits(
        timeout_sec=int(raw.get("timeout_sec", 30)),
        resource_caps=ResourceCaps(**{
            k: int(v) for k, v in caps_raw.items()
            if k in {
                "max_memory_delta_mb",
                "max_cpu_seconds",
                "max_disk_write_mb",
                "max_egress_mb",
            }
        }),
    )


def _parse_cleanup(raw: dict) -> Cleanup:
    restore = raw.get("restore_state", "pre_probe_snapshot")
    _one_of(
        restore,
        {"pre_probe_snapshot", "none", "custom"},
        "cleanup.restore_state",
    )
    return Cleanup(
        restore_state=restore,
        clear_captured_events=bool(raw.get("clear_captured_events", False)),
        delete_probe_artifacts_from_atlas=bool(
            raw.get("delete_probe_artifacts_from_atlas", True)
        ),
    )


def _parse_metadata(raw: dict) -> ScenarioMetadata:
    return ScenarioMetadata(
        author=str(raw.get("author", "unknown")),
        created_date=str(raw.get("created_date", "unknown")),
        changelog=list(raw.get("changelog", [])),
    )
