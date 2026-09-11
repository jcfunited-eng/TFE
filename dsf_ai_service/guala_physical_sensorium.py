"""Compact complete physical sensorium for the lean Guala runtime."""

from __future__ import annotations

from array import array
from dataclasses import dataclass
from fractions import Fraction
import math
import sys

from dsf_ai_service.glew_runtime.native_joint_source_episode import (
    settle_native_joint_source_episode_batch_from_anatomy,
    settle_native_joint_source_episode_for_senses_from_anatomy,
)
from dsf_ai_service.glew_runtime.sensory_full_field_boundary import (
    PhysicalSense,
    SENSE_ORDER,
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


def _validate(
    sensorium: PhysicalSensorium, frame_count: int,
    *, senses: tuple[PhysicalSense, ...] | None = None,
) -> PortTrajectories:
    expected = (
        ("retina", sensorium.retina, RETINAL_PORTS, PhysicalSense.SIGHT),
        ("legacy ears", sensorium.legacy_ears, LEGACY_EAR_PORTS, PhysicalSense.SOUND),
        ("cochleae", sensorium.cochleae, COCHLEAR_PORTS, PhysicalSense.SOUND),
        ("touch", sensorium.touch, TOUCH_PORTS, PhysicalSense.TOUCH),
        ("smell", sensorium.smell, SMELL_PORTS, PhysicalSense.SMELL),
        ("taste", sensorium.taste, TASTE_PORTS, PhysicalSense.TASTE),
        ("displacement", sensorium.displacement, DISPLACEMENT_PORTS, PhysicalSense.BODY),
        ("articulation", sensorium.articulation, ARTICULATORY_PORTS, PhysicalSense.BODY),
        ("thermal", sensorium.thermal, THERMAL_PORTS, PhysicalSense.BODY),
    )
    ordered = []
    for label, ports, width, sense in expected:
        if senses is not None and sense not in senses:
            continue
        if len(ports) != width:
            raise ValueError(f"{label} changed mounted receptor count")
        if any(len(trajectory) != frame_count for trajectory in ports):
            raise ValueError(f"{label} changed the shared physical clock")
        ordered.extend(ports)
    if senses is None and len(ordered) != PORT_COUNT:
        raise RuntimeError("physical sensorium does not cover mounted anatomy")
    for trajectory in ordered:
        for value in trajectory:
            if not math.isfinite(float(value)):
                raise ValueError("physical sensorium contains a non-finite sample")
    return tuple(ordered)

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


def _sense_trajectories(
    sensorium: PhysicalSensorium,
) -> dict[PhysicalSense, PortTrajectories]:
    return {
        PhysicalSense.SIGHT: sensorium.retina,
        PhysicalSense.SOUND: (*sensorium.legacy_ears, *sensorium.cochleae),
        PhysicalSense.TOUCH: sensorium.touch,
        PhysicalSense.SMELL: sensorium.smell,
        PhysicalSense.TASTE: sensorium.taste,
        PhysicalSense.BODY: (
            *sensorium.displacement,
            *sensorium.articulation,
            *sensorium.thermal,
        ),
    }


def settle_projected_physical_sensorium(
    *,
    assembly_id: str,
    source_times: tuple[Fraction, ...],
    sensorium: PhysicalSensorium,
    senses: tuple[PhysicalSense, ...],
) -> object:
    """Settle explicit disjoint senses while preserving mounted port anatomy."""

    if (
        not isinstance(senses, tuple)
        or not senses
        or any(not isinstance(sense, PhysicalSense) for sense in senses)
        or tuple(sorted(senses, key=SENSE_ORDER.index)) != senses
    ):
        raise ValueError("physical sense projection is empty or noncanonical")
    if len(set(senses)) != len(senses):
        raise ValueError("physical sense projection repeats a sense")
    # Only these senses enter this episode. A concurrent return may carry
    # a different exact sample grid for another, independently admitted sense.
    _validate(sensorium, len(source_times), senses=senses)
    by_sense = _sense_trajectories(sensorium)
    selected = tuple(
        trajectory
        for sense in senses
        for trajectory in by_sense[sense]
    )
    if not selected:
        raise RuntimeError("physical sense projection left mounted anatomy")
    signals = array("d")
    for trajectory in selected:
        signals.extend(float(value) for value in trajectory)
    if sys.byteorder != "little":
        signals.byteswap()
    return settle_native_joint_source_episode_for_senses_from_anatomy(
        anatomy=receptor_anatomy(),
        assembly_id=assembly_id,
        source_times=source_times,
        signal_body=signals.tobytes(),
        selected_senses=senses,
    )


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
