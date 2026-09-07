"""Compact complete physical sensorium for the lean Guala runtime."""

from __future__ import annotations

from array import array
from dataclasses import dataclass
from fractions import Fraction
import math
import sys

from dsf_ai_service.glew_runtime.native_joint_source_episode import (
    settle_native_joint_source_episode_batch_from_anatomy,
)
from dsf_ai_service.guala_receptor_anatomy import PORT_COUNT, receptor_anatomy


RETINAL_PORTS = 135
LEGACY_EAR_PORTS = 2
COCHLEAR_PORTS = 32
TOUCH_PORTS = 28
SMELL_PORTS = 8
TASTE_PORTS = 5
DISPLACEMENT_PORTS = 4
ARTICULATORY_PORTS = 4
THERMAL_PORTS = 2


Trajectory = tuple[Fraction | float, ...]
PortTrajectories = tuple[Trajectory, ...]


@dataclass(frozen=True, slots=True)
class PhysicalSensorium:
    """All mounted physical receptor trajectories on one shared clock."""

    retina: PortTrajectories
    legacy_ears: PortTrajectories
    cochleae: PortTrajectories
    touch: PortTrajectories
    smell: PortTrajectories
    taste: PortTrajectories
    displacement: PortTrajectories
    articulation: PortTrajectories
    thermal: PortTrajectories

    def ordered_ports(self) -> PortTrajectories:
        return (
            *self.retina,
            *self.legacy_ears,
            *self.cochleae,
            *self.touch,
            *self.smell,
            *self.taste,
            *self.displacement,
            *self.articulation,
            *self.thermal,
        )

    @classmethod
    def constant(
        cls,
        *,
        frame_count: int,
        retina: tuple[Fraction | float, ...],
        legacy_ears: tuple[Fraction | float, ...],
        cochleae: tuple[Fraction | float, ...],
        touch: tuple[Fraction | float, ...],
        smell: tuple[Fraction | float, ...],
        taste: tuple[Fraction | float, ...],
        displacement: tuple[Fraction | float, ...],
        articulation: tuple[Fraction | float, ...],
        thermal: tuple[Fraction | float, ...],
    ) -> "PhysicalSensorium":
        if frame_count <= 0:
            raise ValueError("physical sensorium requires a positive frame count")

        def hold(values: tuple[Fraction | float, ...]) -> PortTrajectories:
            return tuple((value,) * frame_count for value in values)

        return cls(
            retina=hold(retina),
            legacy_ears=hold(legacy_ears),
            cochleae=hold(cochleae),
            touch=hold(touch),
            smell=hold(smell),
            taste=hold(taste),
            displacement=hold(displacement),
            articulation=hold(articulation),
            thermal=hold(thermal),
        )


def _validate(sensorium: PhysicalSensorium, frame_count: int) -> PortTrajectories:
    expected = (
        ("retina", sensorium.retina, RETINAL_PORTS),
        ("legacy ears", sensorium.legacy_ears, LEGACY_EAR_PORTS),
        ("cochleae", sensorium.cochleae, COCHLEAR_PORTS),
        ("touch", sensorium.touch, TOUCH_PORTS),
        ("smell", sensorium.smell, SMELL_PORTS),
        ("taste", sensorium.taste, TASTE_PORTS),
        ("displacement", sensorium.displacement, DISPLACEMENT_PORTS),
        ("articulation", sensorium.articulation, ARTICULATORY_PORTS),
        ("thermal", sensorium.thermal, THERMAL_PORTS),
    )
    for label, ports, width in expected:
        if len(ports) != width:
            raise ValueError(f"{label} changed mounted receptor count")
        if any(len(trajectory) != frame_count for trajectory in ports):
            raise ValueError(f"{label} changed the shared physical clock")
    ordered = sensorium.ordered_ports()
    if len(ordered) != PORT_COUNT:
        raise RuntimeError("physical sensorium does not cover mounted anatomy")
    for trajectory in ordered:
        for value in trajectory:
            numeric = float(value)
            if not math.isfinite(numeric):
                raise ValueError("physical sensorium contains a non-finite sample")
    return ordered


def compact_signal_body(
    sensorium: PhysicalSensorium,
    *,
    frame_count: int,
) -> bytes:
    """Encode port-major binary64 samples for native anatomy replacement."""

    if not isinstance(sensorium, PhysicalSensorium):
        raise TypeError("physical sensorium changed type")
    if frame_count <= 0:
        raise ValueError("physical sensorium requires a positive frame count")
    ordered = _validate(sensorium, frame_count)
    signals = array("d")
    for trajectory in ordered:
        signals.extend(float(value) for value in trajectory)
    if len(signals) != PORT_COUNT * frame_count:
        raise RuntimeError("physical sensorium signal count changed")
    if sys.byteorder != "little":
        signals.byteswap()
    return signals.tobytes()


def settle_physical_sensorium(
    *,
    assembly_id: str,
    source_times: tuple[Fraction, ...],
    sensorium: PhysicalSensorium,
) -> object:
    """Create one native full-field episode without rebuilding port objects."""

    if not isinstance(assembly_id, str) or not assembly_id:
        raise ValueError("physical sensorium requires a nonempty assembly id")
    if not isinstance(source_times, tuple) or not source_times:
        raise ValueError("physical sensorium requires an exact source clock")
    if any(not isinstance(value, Fraction) for value in source_times):
        raise TypeError("physical sensorium source clock is not exact")
    episodes = settle_native_joint_source_episode_batch_from_anatomy(
        anatomy=receptor_anatomy(),
        assembly_ids=(assembly_id,),
        source_times=(source_times,),
        signal_bodies=(
            compact_signal_body(sensorium, frame_count=len(source_times)),
        ),
    )
    if len(episodes) != 1:
        raise RuntimeError("native physical sensorium lost one episode")
    return episodes[0]
