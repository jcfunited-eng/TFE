"""Body-only numerical mechanics. No behavior controller or cognitive authority.

MuJoCo 3.3.7 is the sole motion/contact solver here. Its soft contact law and
finite time sampling are approved approximations, not exact skin thermodynamics.
Caller-owned integration bytes are authoritative; MjData is reusable scratch.
Only direct, unit-gear, effort-limited hinge/slide motors are admitted.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import math
import xml.etree.ElementTree as ET

import mujoco as mj
import numpy as np


ENGINE_VERSION = "3.3.7"
STATE_KIND = mj.mjtState.mjSTATE_INTEGRATION
_CALLBACK_GETTERS = (
    mj.get_mjcb_control, mj.get_mjcb_passive, mj.get_mjcb_contactfilter,
    mj.get_mjcb_sensor, mj.get_mjcb_time, mj.get_mjcb_act_dyn,
    mj.get_mjcb_act_gain, mj.get_mjcb_act_bias,
)


def _no_callbacks():
    # This adapter has one world caller; no concurrent native callback writers.
    # Never clear callbacks owned by another participant.
    if any(getter() is not None for getter in _CALLBACK_GETTERS):
        raise ValueError("external native callbacks are outside body authority")


@dataclass(frozen=True)
class MechanicalLimits:
    step_us: int
    max_substeps: int
    max_penetration_m: float
    max_hinge_overrun_rad: float
    max_slide_overrun_m: float
    max_surface_travel_m: float

    def __post_init__(self):
        for x in (self.step_us, self.max_substeps):
            if type(x) is not int or x <= 0:
                raise ValueError("positive integer work/time limits required")
        for x in (self.max_penetration_m, self.max_hinge_overrun_rad,
                  self.max_slide_overrun_m, self.max_surface_travel_m):
            if not math.isfinite(x) or x <= 0:
                raise ValueError("positive finite SI numerical limits required")


@dataclass(frozen=True)
class ContactEvidence:
    geom_pair: tuple[int, int]
    position_m: tuple[float, ...]
    frame_world: tuple[float, ...]
    separation_m: float
    # Native contact frame: force xyz, then torque xyz, on geom2 from geom1.
    wrench: tuple[float, ...]


@dataclass(frozen=True)
class MechanicalObservation:
    time_s: float
    qpos: tuple[float, ...]
    qvel: tuple[float, ...]
    sensors: tuple[tuple[str, tuple[float, ...]], ...]
    contacts: tuple[ContactEvidence, ...]
    potential_j: float
    kinetic_j: float


@dataclass(frozen=True)
class MechanicalSuccessor:
    state: bytes
    observation: MechanicalObservation
    # Trapezoidal power quadrature, not exact metabolic consumption.
    positive_motor_work_j: float
    signed_motor_work_j: float
    max_surface_travel_m: float


class NativeBody:
    """Trusted anatomy + bounded scratch, called by the existing world authority.

    No filesystem/network assets, callbacks, actuator servos, or automatic reset.
    XML is a trusted internal model, not an upload format. State is not a public
    deserialization authority: the existing world custody layer must authenticate
    it. The prefix binds it to the exact model, engine and numerical limits.
    """

    def __init__(self, xml: str, limits: MechanicalLimits):
        if mj.__version__ != ENGINE_VERSION:
            raise ValueError("unverified body engine version")
        _no_callbacks()
        root = ET.fromstring(xml)
        if any(e.tag in {"include", "extension", "plugin", "keyframe"}
               or "file" in e.attrib for e in root.iter()):
            raise ValueError("body model must be self-contained without plugins")
        if any(e.tag != "motor" for a in root.findall("actuator") for e in a):
            raise ValueError("only direct effort motors are supported")
        option, size = root.find("option"), root.find("size")
        if option is None or size is None or "memory" not in size.attrib:
            raise ValueError("explicit numerical option and native arena required")
        if not {"iterations", "tolerance", "integrator"} <= option.attrib.keys():
            raise ValueError("explicit solver limits required")
        self.limits = limits
        self._model = m = mj.MjModel.from_xml_string(xml)
        if m.nmocap or m.nplugin or m.na or m.nflex:
            raise ValueError("only rigid bodies without plugins/mocap/activation")
        if (m.opt.disableactuator or np.any(m.jnt_actfrclimited)
                or np.any(m.jnt_actgravcomp) or np.any(m.body_gravcomp)):
            raise ValueError("additional motor limits/compensation are outside scope")
        if int(m.opt.disableflags):
            raise ValueError("body model may not disable physical constraints")
        m.opt.disableflags |= int(mj.mjtDisableBit.mjDSBL_AUTORESET)
        m.opt.enableflags |= int(mj.mjtEnableBit.mjENBL_ENERGY)
        m.opt.timestep = limits.step_us / 1_000_000
        if m.opt.iterations <= 0 or not 0 < m.opt.tolerance < math.inf:
            raise ValueError("finite solver work and convergence limits required")
        if np.any(m.sensor_noise):
            raise ValueError("random sensor noise is not enabled")
        self._motor_dof = []
        for i in range(m.nu):
            joint = int(m.actuator_trnid[i, 0])
            if (m.actuator_trntype[i] != mj.mjtTrn.mjTRN_JOINT or joint < 0
                    or m.jnt_type[joint] not in (mj.mjtJoint.mjJNT_HINGE,
                                                 mj.mjtJoint.mjJNT_SLIDE)
                    or m.actuator_dyntype[i] != mj.mjtDyn.mjDYN_NONE
                    or m.actuator_gaintype[i] != mj.mjtGain.mjGAIN_FIXED
                    or m.actuator_biastype[i] != mj.mjtBias.mjBIAS_NONE
                    or m.actuator_gainprm[i, 0] != 1
                    or not np.array_equal(m.actuator_gear[i], [1, 0, 0, 0, 0, 0])
                    or not m.actuator_forcelimited[i]
                    or not np.isfinite(m.actuator_forcerange[i]).all()
                    or not m.actuator_forcerange[i, 0] < m.actuator_forcerange[i, 1]):
                raise ValueError("motor must be bounded direct unit-gear effort")
            if m.actuator_ctrllimited[i] and not np.array_equal(
                    m.actuator_ctrlrange[i], m.actuator_forcerange[i]):
                raise ValueError("control/force bounds must coincide")
            self._motor_dof.append(int(m.jnt_dofadr[joint]))
        if len(set(self._motor_dof)) != len(self._motor_dof):
            raise ValueError("duplicate motors on one degree of freedom")
        self.actuator_names = tuple(mj.mj_id2name(m, mj.mjtObj.mjOBJ_ACTUATOR, i)
                                    for i in range(m.nu))
        self.joint_names = tuple(mj.mj_id2name(m, mj.mjtObj.mjOBJ_JOINT, i)
                                for i in range(m.njnt))
        self.qpos_addresses = tuple(int(x) for x in m.jnt_qposadr)
        self.geom_names = tuple(mj.mj_id2name(m, mj.mjtObj.mjOBJ_GEOM, i)
                                for i in range(m.ngeom))
        self._data = mj.MjData(m)
        self._size = mj.mj_stateSize(m, STATE_KIND)
        self._header = sha256((ENGINE_VERSION + repr(limits) + xml).encode()).digest()
        self.state_bytes = 32 + self._size * 8
        self._state_buffer = np.empty(self._size, dtype=np.float64)
        self._limited = tuple(i for i in range(m.njnt) if m.jnt_limited[i])
        if any(m.jnt_type[i] not in (mj.mjtJoint.mjJNT_HINGE, mj.mjtJoint.mjJNT_SLIDE)
               for i in self._limited):
            raise ValueError("limited ball joints require a separate error metric")

    def _capture(self):
        mj.mj_getState(self._model, self._data, self._state_buffer, STATE_KIND)
        if not np.isfinite(self._state_buffer).all():
            raise ValueError("non-finite native integration state")
        return self._header + self._state_buffer.astype("<f8", copy=False).tobytes()

    def _restore(self, state):
        _no_callbacks()
        if (type(state) is not bytes or len(state) != self.state_bytes
                or state[:32] != self._header):
            raise ValueError("body state/model mismatch")
        values = np.frombuffer(state, dtype="<f8", offset=32)
        if not np.isfinite(values).all():
            raise ValueError("non-finite body state")
        mj.mj_resetData(self._model, self._data)
        # The pinned Python binding requires writable storage even though the C
        # API consumes this state. Reuse the existing buffer; preserve input bytes.
        self._state_buffer[:] = values
        mj.mj_setState(self._model, self._data, self._state_buffer, STATE_KIND)
        mj.mj_forward(self._model, self._data)
        self._check()

    def initial_state(self):
        _no_callbacks()
        mj.mj_resetData(self._model, self._data)
        mj.mj_forward(self._model, self._data)
        self._check()
        return self._capture()

    def _check(self):
        m, d, lim = self._model, self._data, self.limits
        if any(w.number for w in d.warning):
            raise ValueError("native mechanics warning; no successor admitted")
        if not all(np.isfinite(x).all() for x in (d.qpos, d.qvel, d.qacc)):
            raise ValueError("non-finite mechanical state")
        if not math.isfinite(d.time):
            raise ValueError("non-finite mechanical time")
        if np.any(np.spacing(np.abs(d.geom_xpos)) > lim.max_surface_travel_m):
            raise ValueError("body coordinates exceed declared numerical resolution")
        if any(c.dist < -lim.max_penetration_m for c in d.contact):
            raise ValueError("contact penetration exceeds declared resolution")
        for i in self._limited:
            q = d.qpos[m.jnt_qposadr[i]]
            tolerance = (lim.max_hinge_overrun_rad if m.jnt_type[i] == mj.mjtJoint.mjJNT_HINGE
                         else lim.max_slide_overrun_m)
            if not m.jnt_range[i, 0] - tolerance <= q <= m.jnt_range[i, 1] + tolerance:
                raise ValueError("joint limit overrun exceeds declared resolution")

    def _observation(self):
        m, d = self._model, self._data
        if not np.isfinite(d.energy).all() or not np.isfinite(d.sensordata).all():
            raise ValueError("non-finite mechanical sensory/energy observation")
        contacts = []
        for i, c in enumerate(d.contact):
            force = np.empty(6)
            mj.mj_contactForce(m, d, i, force)
            if (not np.isfinite(force).all() or not np.isfinite(c.pos).all()
                    or not np.isfinite(c.frame).all() or not math.isfinite(c.dist)):
                raise ValueError("non-finite physical contact observation")
            contacts.append(ContactEvidence(tuple(int(x) for x in c.geom),
                            tuple(c.pos), tuple(c.frame), float(c.dist), tuple(force)))
        sensors = tuple((mj.mj_id2name(m, mj.mjtObj.mjOBJ_SENSOR, i) or str(i),
                         tuple(d.sensordata[a:a + m.sensor_dim[i]]))
                        for i, a in enumerate(m.sensor_adr))
        return MechanicalObservation(float(d.time), tuple(d.qpos), tuple(d.qvel),
                                     sensors, tuple(contacts), float(d.energy[0]),
                                     float(d.energy[1]))

    def observe(self, state):
        self._restore(state)
        return self._observation()

    def advance(self, state: bytes, efforts: tuple[float, ...], elapsed_us: int,
                available_work_j: float) -> MechanicalSuccessor:
        lim, m, d = self.limits, self._model, self._data
        if (type(elapsed_us) is not int or elapsed_us <= 0
                or elapsed_us % lim.step_us or elapsed_us // lim.step_us > lim.max_substeps):
            raise ValueError("interval exceeds declared fixed-step budget")
        effort = np.asarray(efforts, dtype=np.float64)
        if (effort.shape != (m.nu,) or not np.isfinite(effort).all()
                or np.any(effort < m.actuator_forcerange[:, 0])
                or np.any(effort > m.actuator_forcerange[:, 1])):
            raise ValueError("effort exceeds physical motor capacity")
        if not math.isfinite(available_work_j) or available_work_j < 0:
            raise ValueError("finite nonnegative mechanical supply required")
        self._restore(state)
        d.ctrl[:] = effort
        # State stores the old command; refresh acceleration/sensors for this effort.
        mj.mj_forward(m, d)
        initial_time = float(d.time)
        if math.ulp(initial_time) > m.opt.timestep:
            raise ValueError("mechanical time cannot represent this interval")
        positive_work = signed_work = travel_peak = 0.0
        for _ in range(elapsed_us // lim.step_us):
            position, rotation = d.geom_xpos.copy(), d.geom_xmat.copy().reshape(-1, 3, 3)
            power_before = effort * d.qvel[self._motor_dof]
            mj.mj_step(m, d)
            # Refresh only geometry/collision here; full sensory forces at final time.
            mj.mj_kinematics(m, d)
            mj.mj_collision(m, d)
            self._check()
            power_after = effort * d.qvel[self._motor_dof]
            signed_work += float(np.sum(power_before + power_after)) * m.opt.timestep / 2
            positive_work += float(np.sum(np.maximum(power_before, 0)
                                         + np.maximum(power_after, 0))) * m.opt.timestep / 2
            if not math.isfinite(positive_work) or not math.isfinite(signed_work):
                raise ValueError("non-finite mechanical work")
            if positive_work > available_work_j:
                raise ValueError("mechanical energy supply exhausted; no successor")
            new_rotation = d.geom_xmat.reshape(-1, 3, 3)
            trace = np.einsum("ijk,ijk->i", rotation, new_rotation)
            angle = np.arccos(np.clip((trace - 1) / 2, -1, 1))
            travel = np.linalg.norm(d.geom_xpos - position, axis=1) + m.geom_rbound * angle
            travel_peak = max(travel_peak, float(np.max(travel, initial=0)))
            if not np.isfinite(travel).all():
                raise ValueError("non-finite surface motion")
            if travel_peak > lim.max_surface_travel_m:
                raise ValueError("surface movement exceeds collision sampling resolution")
        expected = initial_time + elapsed_us / 1_000_000
        if abs(d.time - expected) > (elapsed_us // lim.step_us + 1) * math.ulp(expected):
            raise ValueError("native mechanical time diverged")
        mj.mj_forward(m, d)
        self._check()
        successor = self._capture()
        return MechanicalSuccessor(successor, self._observation(), positive_work,
                                   signed_work, travel_peak)
