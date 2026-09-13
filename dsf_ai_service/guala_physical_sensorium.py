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
    settle_native_joint_source_episode_for_retinal_sites_from_anatomy,
)
from dsf_ai_service.glew_runtime.sensory_full_field_boundary import (
    PhysicalSense,
    SENSE_ORDER,
)
from dsf_ai_service.guala_receptor_anatomy import (
    LEGACY_PORT_COUNT, PORT_COUNT, receptor_anatomy,
)


RETINAL_PORTS = 135
RETINAL_FOCAL_PORTS = 768  # () means this source supplies no focal coverage
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
    retina_focal: PortTrajectories = ()

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
            *self.retina_focal,
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
        retina_focal: tuple[Fraction | float, ...] = (),
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
            retina_focal=hold(retina_focal),
        )


def _validate(
    sensorium: PhysicalSensorium, frame_count: int,
    *, senses: tuple[PhysicalSense, ...] | None = None,
    sampled_retina: tuple[PortTrajectories, PortTrajectories] | None = None,
) -> PortTrajectories:
    # Substitute only acquired light, at its declared position among the other
    # senses. A later BODY group must remain later than the focal sight group.
    retina, focal = (
        (sensorium.retina, sensorium.retina_focal)
        if sampled_retina is None else sampled_retina
    )
    expected = (
        ("retina", retina, RETINAL_PORTS if sampled_retina is None else len(retina), PhysicalSense.SIGHT),
        ("legacy ears", sensorium.legacy_ears, LEGACY_EAR_PORTS, PhysicalSense.SOUND),
        ("cochleae", sensorium.cochleae, COCHLEAR_PORTS, PhysicalSense.SOUND),
        ("touch", sensorium.touch, TOUCH_PORTS, PhysicalSense.TOUCH),
        ("smell", sensorium.smell, SMELL_PORTS, PhysicalSense.SMELL),
        ("taste", sensorium.taste, TASTE_PORTS, PhysicalSense.TASTE),
        ("displacement", sensorium.displacement, DISPLACEMENT_PORTS, PhysicalSense.BODY),
        ("articulation", sensorium.articulation, ARTICULATORY_PORTS, PhysicalSense.BODY),
        ("thermal", sensorium.thermal, THERMAL_PORTS, PhysicalSense.BODY),
        ("retina focal", focal,
         (len(focal) and RETINAL_FOCAL_PORTS) if sampled_retina is None else len(focal), PhysicalSense.SIGHT),
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
    if senses is None and len(ordered) != LEGACY_PORT_COUNT + len(sensorium.retina_focal):
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
    if len(signals) != len(ordered) * frame_count:
        raise RuntimeError("physical sensorium signal count changed")
    if sys.byteorder != "little":
        signals.byteswap()
    return signals.tobytes()


def settle_projected_physical_sensorium(
    *,
    assembly_id: str,
    source_times: tuple[Fraction, ...],
    sensorium: PhysicalSensorium,
    senses: tuple[PhysicalSense, ...],
    retinal_sites: tuple[int, ...] | None = None,
    retinal_samples: PortTrajectories | None = None,
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
    # Native projection filters the declared port roster without regrouping
    # its senses. Sampled sight replaces its groups in that declared order.
    if retinal_sites is None:
        if retinal_samples is not None:
            raise ValueError("sampled light lacks explicit retinal coverage")
        selected = _validate(sensorium, len(source_times), senses=senses)
    else:
        if (
            PhysicalSense.SIGHT not in senses
            or not isinstance(retinal_sites, tuple)
            or not retinal_sites
            or any(type(site) is not int or not 0 <= site < RETINAL_PORTS + RETINAL_FOCAL_PORTS
                   for site in retinal_sites)
            or any(left >= right for left, right in zip(retinal_sites, retinal_sites[1:]))
            or not isinstance(retinal_samples, tuple)
            or len(retinal_samples) != len(retinal_sites)
            or any(not isinstance(row, tuple) or len(row) != len(source_times)
                   for row in retinal_samples)
        ):
            raise ValueError("sampled light changed retinal coverage or source clock")
        # Do not validate, copy, or encode omitted world/camera light. The one
        # anatomy-ordered pass keeps each nonvisual group in place even when a
        # group follows focal sight, rather than gathering all of them before it.
        split = sum(site < RETINAL_PORTS for site in retinal_sites)
        selected = _validate(
            sensorium, len(source_times), senses=senses,
            sampled_retina=(retinal_samples[:split], retinal_samples[split:]),
        )
    if not selected:
        raise RuntimeError("physical sense projection left mounted anatomy")
    signals = array("d")
    for trajectory in selected:
        signals.extend(float(value) for value in trajectory)
    if sys.byteorder != "little":
        signals.byteswap()
    if retinal_sites is not None:
        return settle_native_joint_source_episode_for_retinal_sites_from_anatomy(
            anatomy=receptor_anatomy(include_focal=retinal_sites[-1] >= RETINAL_PORTS),
            assembly_id=assembly_id, source_times=source_times,
            signal_body=signals.tobytes(), selected_senses=senses,
            selected_retinal_sites=retinal_sites,
        )
    return settle_native_joint_source_episode_for_senses_from_anatomy(
        anatomy=receptor_anatomy(include_focal=bool(sensorium.retina_focal)),
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
        anatomy=receptor_anatomy(include_focal=bool(sensorium.retina_focal)),
        assembly_ids=(assembly_id,),
        source_times=(source_times,),
        signal_bodies=(
            compact_signal_body(sensorium, frame_count=len(source_times)),
        ),
    )
    if len(episodes) != 1:
        raise RuntimeError("native physical sensorium lost one episode")
    return episodes[0]
