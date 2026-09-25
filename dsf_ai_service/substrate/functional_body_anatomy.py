"""Declared engineering morphology for the functional-body precursor.

This is anatomy, not human growth physiology or a motor controller. SI units;
x forward, y left, z up. Uniform material density supplies native mass/inertia.
The approximately one-metre biped has independent digits, no root actuator,
no position targets, no keyframes, and no scripted motion. Assembly occurs once
inside the caller's world model; this module retains no alternate body state.
"""
# Co-located XYZ hinges are a reduced joint workspace, not full human mobility.
# Middle-axis limits plus the declared .03rad overrun stay inside (-pi/2, pi/2),
# where the angular Jacobian has full rank. Do not extend through gimbal lock.
from __future__ import annotations

import math
import xml.etree.ElementTree as ET


# Declared virtual material, not measured biological tissue. Direct joint effort
# capacity = stress * circular effective actuator area * moment arm.
# Effective radius equals the declared load-bearing segment radius; moment arm
# is half that radius. This is a capacity envelope, not muscle metabolism.
DENSITY_KG_M3 = 1000.0
ACTUATOR_STRESS_PA = 200_000.0
BEARING_VISCOSITY_PA_S = 100.0


def bearing_drag(radius_m):
    """Ideal Newtonian annular bearing; ignores end effects/fluid inertia.

    Virtual material choice, not biological calibration. Mechanical dissipation
    B*qdot**2 requires thermal accounting at the later world-mount boundary.
    """
    if not math.isfinite(radius_m) or radius_m <= 0:
        raise ValueError("positive finite bearing radius required")
    inner, outer, length = radius_m / 2, .55 * radius_m, radius_m
    return (4 * math.pi * BEARING_VISCOSITY_PA_S * length * inner**2 * outer**2
            / (outer**2 - inner**2))


def _numbers(values):
    return " ".join(format(float(x), ".17g") for x in values)


def append_reference_biped(worldbody: ET.Element, actuators: ET.Element,
                           sensors: ET.Element, *, root_position_m):
    """Append one morphology to an existing native world, before compilation.

    Caller supplies world gravity, ground/objects, solver/contact material and
    numerical limits. No floor, target object, world clock or engine is created.
    Names are mechanical addresses, not cognitive identities or action labels.
    Only a pristine model may receive this body; duplicate names are refused.
    """
    position = tuple(float(x) for x in root_position_m)
    if len(position) != 3 or not all(math.isfinite(x) for x in position):
        raise ValueError("finite three-dimensional root position required")
    if (worldbody.tag, actuators.tag, sensors.tag) != ("worldbody", "actuator", "sensor"):
        raise ValueError("native world/body assembly elements required")
    if any(e.get("name", "").startswith("guala/")
           for section in (worldbody, actuators, sensors) for e in section.iter()):
        raise ValueError("reference anatomy already present")

    def body(parent, name, pos):
        return ET.SubElement(parent, "body", name="guala/" + name, pos=_numbers(pos))

    def geom(part, kind, *, size, pos=(0, 0, 0), end=None):
        attributes = dict(name=part.get("name") + "/surface", type=kind,
                          size=_numbers(size), density=str(DENSITY_KG_M3))
        if end is None:
            attributes["pos"] = _numbers(pos)
        else:
            attributes["fromto"] = _numbers((*pos, *end))
        ET.SubElement(part, "geom", **attributes)

    def hinge(part, axis_name, axis, bounds, radius):
        name = part.get("name") + "/" + axis_name
        ET.SubElement(part, "joint", name=name, type="hinge", axis=_numbers(axis),
                      limited="true", range=_numbers(bounds), damping=str(bearing_drag(radius)))
        capacity = ACTUATOR_STRESS_PA * math.pi * radius**2 * (radius / 2)
        ET.SubElement(actuators, "motor", name=name + "/effort", joint=name,
                      gear="1", forcelimited="true", forcerange=_numbers((-capacity, capacity)))
        ET.SubElement(sensors, "jointpos", name=name + "/angle", joint=name)
        ET.SubElement(sensors, "jointvel", name=name + "/rate", joint=name)
        ET.SubElement(sensors, "actuatorfrc", name=name + "/effort-return",
                      actuator=name + "/effort")

    def inertial_site(part):
        name = part.get("name") + "/inertial"
        ET.SubElement(part, "site", name=name, size="0.001")
        ET.SubElement(sensors, "accelerometer", name=name + "/specific-force", site=name)
        ET.SubElement(sensors, "gyro", name=name + "/angular-rate", site=name)

    pelvis = body(worldbody, "pelvis", position)
    ET.SubElement(pelvis, "freejoint", name="guala/root")
    geom(pelvis, "box", size=(.06, .08, .045))
    inertial_site(pelvis)
    torso = body(pelvis, "torso", (0, 0, .09))
    for name, axis, bounds in (("roll", (1, 0, 0), (-.5, .5)),
                               ("pitch", (0, 1, 0), (-.7, .7)),
                               ("yaw", (0, 0, 1), (-.7, .7))):
        hinge(torso, name, axis, bounds, .045)
    geom(torso, "box", size=(.06, .10, .11), pos=(0, 0, .115))
    head = body(torso, "head", (0, 0, .30))
    for name, axis, bounds in (("roll", (1, 0, 0), (-.5, .5)),
                               ("pitch", (0, 1, 0), (-.7, .7)),
                               ("yaw", (0, 0, 1), (-1.2, 1.2))):
        hinge(head, name, axis, bounds, .02)
    geom(head, "sphere", size=(.07,), pos=(0, 0, .03))
    inertial_site(head)

    for side, sign in (("left", 1), ("right", -1)):
        thigh = body(pelvis, side + "/thigh", (0, sign * .065, -.04))
        for name, axis, bounds in (("roll", (1, 0, 0), (-.7, .7)),
                                   ("pitch", (0, 1, 0), (-1.4, .6)),
                                   ("yaw", (0, 0, 1), (-.7, .7))):
            hinge(thigh, name, axis, bounds, .032)
        geom(thigh, "capsule", size=(.032,), pos=(0, 0, -.035), end=(0, 0, -.195))
        shin = body(thigh, side + "/shin", (0, 0, -.23))
        hinge(shin, "knee", (0, 1, 0), (0, 2.2), .026)
        geom(shin, "capsule", size=(.026,), pos=(0, 0, -.03), end=(0, 0, -.20))
        foot = body(shin, side + "/foot", (0, 0, -.23))
        hinge(foot, "roll", (1, 0, 0), (-.45, .45), .025)
        hinge(foot, "pitch", (0, 1, 0), (-.65, .65), .025)
        geom(foot, "box", size=(.05, .032, .02), pos=(.025, 0, -.015))
        inertial_site(foot)
        for digit in range(5):
            toe = body(foot, side + f"/toe-{digit}", (.08, (digit - 2) * .012, -.017))
            hinge(toe, "flexion", (0, 1, 0), (-.5, .8), .004)
            geom(toe, "capsule", size=(.004,), pos=(.004, 0, 0), end=(.023, 0, 0))

        upper = body(torso, side + "/upper-arm", (0, sign * .135, .20))
        for name, axis, bounds in (("roll", (1, 0, 0), (-1.8, 1.8)),
                                   ("pitch", (0, 1, 0), (-1.4, 1.4)),
                                   ("yaw", (0, 0, 1), (-1.5, 1.5))):
            hinge(upper, name, axis, bounds, .022)
        geom(upper, "capsule", size=(.022,), pos=(0, 0, -.025), end=(0, 0, -.135))
        forearm = body(upper, side + "/forearm", (0, 0, -.16))
        hinge(forearm, "elbow", (0, -1, 0), (0, 2.3), .018)
        hinge(forearm, "pronation", (0, 0, 1), (-1.5, 1.5), .018)
        geom(forearm, "capsule", size=(.018,), pos=(0, 0, -.02), end=(0, 0, -.12))
        palm = body(forearm, side + "/palm", (0, 0, -.14))
        hinge(palm, "roll", (1, 0, 0), (-.5, .5), .012)
        hinge(palm, "pitch", (0, 1, 0), (-.8, .8), .012)
        geom(palm, "box", size=(.025, .032, .012), pos=(.025, 0, 0))
        inertial_site(palm)
        # Four independent two-link fingers; opposed thumb has an additional
        # rotation at its base. Coupled distal human joints are not duplicated.
        for digit in range(5):
            thumb = digit == 4
            base = (.015, sign * .044, 0) if thumb else (.055, (digit - 1.5) * .016, 0)
            finger = body(palm, side + f"/digit-{digit}/proximal", base)
            if thumb:
                hinge(finger, "opposition", (0, 0, sign), (-1.5, 1.5), .005)
            hinge(finger, "flexion", (0, 1, 0), (-.2, 1.5), .005)
            geom(finger, "capsule", size=(.005,), pos=(.005, 0, 0), end=(.020, 0, 0))
            tip = body(finger, side + f"/digit-{digit}/distal", (.03, 0, 0))
            hinge(tip, "flexion", (0, 1, 0), (0, 1.5), .004)
            geom(tip, "capsule", size=(.004,), pos=(.004, 0, 0), end=(.016, 0, 0))
