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
class LocalContact:
    # Anatomical surface only; no counterparty identity or hidden world state.
    surface: str
    # Link-local contact position. Force and couple at that point, expressed
    # in the same link axes; NOT a resultant torque about the link origin.
    position_m: tuple[float, ...]
    force_n: tuple[float, ...]
    couple_nm: tuple[float, ...]


@dataclass(frozen=True)
class BodyFeedback:
    time_s: float
    # Joint angle/rate, actual motor effort, site-frame accelerometer and gyro.
    # Uninstrumented quantities are absent, never fabricated as zero.
    sensors: tuple[tuple[str, tuple[float, ...]], ...]
    contacts: tuple[LocalContact, ...]


@dataclass(frozen=True)
class WorldFrame:
    """Rigid transform for world custody/optics, never an organism sensation.

    Columns of the row-major rotation map local x/y/z axes into world axes:
    world_point = position_m + rotation_world @ local_point. No pose rounding
    or yaw-only reconstruction is allowed at this boundary.
    """
    name: str
    position_m: tuple[float, float, float]
    rotation_world: tuple[float, ...]


@dataclass(frozen=True)
class RayGeometry:
    """Transient world optics, NOT organism afference or recognized identities.

    Distances are metres along unit directions; (-1, -1) denotes a miss.
    Packed arrays own their storage and do not alias native scratch. They are
    not serialized or retained by the mechanical/world authority.
    """
    origin_world_m: tuple[float, float, float]
    directions_world: np.ndarray
    geom_indices: np.ndarray
    distances_m: np.ndarray


@dataclass(frozen=True)
class MechanicalObservation:
    # Whole-world custody/diagnostics. Only self_feedback is organism afference.
    time_s: float
    qpos: tuple[float, ...]
    qvel: tuple[float, ...]
    sensors: tuple[tuple[str, tuple[float, ...]], ...]
    contacts: tuple[ContactEvidence, ...]
    potential_j: float
    kinetic_j: float
    self_feedback: BodyFeedback | None
    world_frames: tuple[WorldFrame, ...]


@dataclass(frozen=True)
class MechanicalSuccessor:
    state: bytes
    observation: MechanicalObservation
    # Trapezoidal power quadrature, not exact metabolic consumption.
    positive_motor_work_j: float
    signed_motor_work_j: float
    max_surface_travel_m: float
    motor_braking_work_j: float
    bearing_dissipation_j: float
    # Wmotor - delta(K+U) - Qbearing. Includes unaccounted constraint/fluid/
    # other damping work and numerical error. NEVER deposit this as heat.
    unresolved_energy_exchange_j: float
    # Owned viscous loss only; None means no anatomical subtree was declared.
    self_bearing_dissipation_j: float | None


class NativeBody:
    """Trusted anatomy + bounded scratch, called by the existing world authority.

    No filesystem/network assets, callbacks, actuator servos, or automatic reset.
    XML is a trusted internal model, not an upload format. State is not a public
    deserialization authority: the existing world custody layer must authenticate
    it. The prefix binds it to the exact model, engine and numerical limits.

    sensory_root identifies the anatomical subtree at model construction. It is
    not a perceptual object identifier. Whole-model diagnostics must stay outside
    cognitive input. Sensor membership is compiled once, not inferred each beat.
    """

    def __init__(self, xml: str, limits: MechanicalLimits, *, sensory_root: str | None = None):
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
        if not np.isfinite(m.dof_damping).all() or np.any(m.dof_damping < 0):
            raise ValueError("nonnegative finite passive bearing coefficients required")
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
        self._sensor_names = tuple(mj.mj_id2name(m, mj.mjtObj.mjOBJ_SENSOR, i) or str(i)
                                   for i in range(m.nsensor))
        # Static anatomical addresses, compiled once. These frames let the
        # existing world own body/object geometry and mount head receptors.
        # They are explicitly outside BodyFeedback; no hidden object identity
        # is delivered to cognition as a new sense.
        self._world_frame_bodies = tuple(
            (i, name) for i in range(1, m.nbody)
            if (name := mj.mj_id2name(m, mj.mjtObj.mjOBJ_BODY, i)) is not None
        )
        self._sensory_root = sensory_root
        self._self_sensors, self._self_geoms, self._self_dofs = self._sensory_membership(sensory_root)
        self._data = mj.MjData(m)
        self._size = mj.mj_stateSize(m, STATE_KIND)
        self._header = sha256((ENGINE_VERSION + repr(limits) + repr(sensory_root) + xml).encode()).digest()
        self.state_bytes = 32 + self._size * 8
        self._state_buffer = np.empty(self._size, dtype=np.float64)
        self._limited = tuple(i for i in range(m.njnt) if m.jnt_limited[i])
        if any(m.jnt_type[i] not in (mj.mjtJoint.mjJNT_HINGE, mj.mjtJoint.mjJNT_SLIDE)
               for i in self._limited):
            raise ValueError("limited ball joints require a separate error metric")

    @property
    def model_identity(self) -> str:
        """Binding already sealed into every native integration state."""
        return self._header.hex()

    def _sensory_membership(self, root_name):
        m = self._model
        if root_name is None:
            return (), {}, np.empty(0, dtype=np.intp)
        if not isinstance(root_name, str) or not root_name:
            raise ValueError("named self-body root required")
        root = mj.mj_name2id(m, mj.mjtObj.mjOBJ_BODY, root_name)
        if root <= 0:
            raise ValueError("self-body root must exist and cannot be the world")
        bodies = {root}
        # Native model bodies are ordered parent before child.
        for i in range(root + 1, m.nbody):
            if int(m.body_parentid[i]) in bodies:
                bodies.add(i)
        geoms = {}
        for i, body in enumerate(m.geom_bodyid):
            if int(body) in bodies:
                if self.geom_names[i] is None:
                    raise ValueError("instrumented body surfaces require anatomical names")
                geoms[i] = int(body)
        sensors = []
        for i, kind in enumerate(m.sensor_type):
            obj = int(m.sensor_objid[i])
            if kind in (mj.mjtSensor.mjSENS_JOINTPOS, mj.mjtSensor.mjSENS_JOINTVEL):
                body = int(m.jnt_bodyid[obj])
            elif kind == mj.mjtSensor.mjSENS_ACTUATORFRC:
                body = int(m.jnt_bodyid[m.actuator_trnid[obj, 0]])
            elif kind in (mj.mjtSensor.mjSENS_ACCELEROMETER, mj.mjtSensor.mjSENS_GYRO):
                body = int(m.site_bodyid[obj])
            else:
                # Global poses, rangefinders, frame sensors etc are NOT included
                # by proximity, name prefix or site attachment.
                continue
            if body in bodies:
                sensors.append(i)
        # Bearing ownership follows joint-body ancestry, including links with
        # inertia but no collision geometry or sensor. Names carry no ownership.
        dofs = np.asarray([i for i, body in enumerate(m.dof_bodyid)
                           if int(body) in bodies], dtype=np.intp)
        dofs.flags.writeable = False
        return tuple(sensors), geoms, dofs

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
        # Pinned binding requires writable storage although C consumes the state.
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
        contacts, local = [], []
        for i, c in enumerate(d.contact):
            force = np.empty(6)
            mj.mj_contactForce(m, d, i, force)
            if (not np.isfinite(force).all() or not np.isfinite(c.pos).all()
                    or not np.isfinite(c.frame).all() or not math.isfinite(c.dist)):
                raise ValueError("non-finite physical contact observation")
            contacts.append(ContactEvidence(tuple(int(x) for x in c.geom),
                            tuple(c.pos), tuple(c.frame), float(c.dist), tuple(force)))
            # Inactive margin/gap records are proximity queries, not touch.
            # An exactly unloaded constraint likewise supplies no tactile load.
            # Preserve both in diagnostics; do not expose their locations as
            # bodily sensation. No arbitrary pressure threshold is introduced.
            if c.efc_address < 0 or not np.any(force):
                continue
            for side, geom in enumerate(c.geom):
                link = self._self_geoms.get(int(geom))
                if link is None:
                    continue
                # Contact axes are rows in c.frame; body axes are columns in
                # xmat. Wrench on geom1 is the negative of that on geom2.
                rotation = d.xmat[link].reshape(3, 3)
                transform = rotation.T @ c.frame.reshape(3, 3).T
                sign = -1 if side == 0 else 1
                local.append(LocalContact(self.geom_names[geom],
                    tuple(rotation.T @ (c.pos - d.xpos[link])),
                    tuple(sign * transform @ force[:3]),
                    tuple(sign * transform @ force[3:])))
        sensors = tuple((name, tuple(d.sensordata[a:a + m.sensor_dim[i]]))
                        for i, (name, a) in enumerate(zip(self._sensor_names, m.sensor_adr)))
        feedback = (None if self._sensory_root is None else
                    BodyFeedback(float(d.time), tuple(sensors[i] for i in self._self_sensors),
                                 tuple(local)))
        if not np.isfinite(d.xpos).all() or not np.isfinite(d.xmat).all():
            raise ValueError("non-finite world-frame projection")
        frames = tuple(WorldFrame(name, tuple(float(x) for x in d.xpos[i]),
                                  tuple(float(x) for x in d.xmat[i]))
                       for i, name in self._world_frame_bodies)
        return MechanicalObservation(float(d.time), tuple(d.qpos), tuple(d.qvel),
                                     sensors, tuple(contacts), float(d.energy[0]),
                                     float(d.energy[1]), feedback, frames)

    def observe(self, state):
        self._restore(state)
        return self._observation()

    def ray_geometry(self, state: bytes, frame_name: str,
                     origin_local_m: tuple[float, float, float],
                     directions_local: np.ndarray, *, max_rays: int) -> RayGeometry:
        """Read native visible geometry from the self body's full rigid frame.

        The optical caller declares the origin and sampling grid; this method
        neither selects gaze nor supplies a radiance model. All visible native
        geometry, including the observer, participates. No yaw-only proxy, body
        exclusion, time advancement or per-ray Python/native crossing.
        """
        if type(max_rays) is not int or max_rays <= 0:
            raise ValueError("positive declared optical sample bound required")
        if (not isinstance(directions_local, np.ndarray)
                or directions_local.dtype != np.dtype(np.float64)
                or directions_local.ndim != 2 or directions_local.shape[1] != 3
                or not 0 < directions_local.shape[0] <= max_rays):
            raise ValueError("bounded packed float64 ray directions required")
        if not np.isfinite(directions_local).all():
            raise ValueError("finite ray directions required")
        if (type(origin_local_m) is not tuple or len(origin_local_m) != 3
                or any(type(x) not in (int, float) or not math.isfinite(x)
                       for x in origin_local_m)):
            raise ValueError("finite link-local optical origin required")
        m = self._model
        if type(frame_name) is not str or self._sensory_root is None:
            raise ValueError("declared self optical frame required")
        frame = int(mj.mj_name2id(m, mj.mjtObj.mjOBJ_BODY, frame_name))
        root = int(mj.mj_name2id(m, mj.mjtObj.mjOBJ_BODY, self._sensory_root))
        ancestor = frame
        while ancestor > 0 and ancestor != root:
            ancestor = int(m.body_parentid[ancestor])
        if frame <= 0 or ancestor != root:
            raise ValueError("optical frame must belong to the self body")

        # Rescale before taking a norm: finite subnormal/large directions must
        # neither underflow to zero nor overflow merely during normalization.
        scale = np.max(np.abs(directions_local), axis=1)
        if np.any(scale == 0):
            raise ValueError("zero optical direction")
        unit = directions_local / scale[:, None]
        unit /= np.linalg.norm(unit, axis=1)[:, None]
        self._restore(state)
        d = self._data
        rotation = d.xmat[frame].reshape(3, 3)
        origin = d.xpos[frame] + rotation @ np.asarray(origin_local_m)
        directions = np.ascontiguousarray(unit @ rotation.T)
        if not np.isfinite(origin).all() or not np.isfinite(directions).all():
            raise ValueError("non-finite optical world transform")
        # Pinned multiRay culls geoms whose centre distance exceeds cutoff +
        # radius. Bound every centre inside the cutoff using the L-infinity
        # envelope ||delta||_2 <= sqrt(3) * ||delta||_inf. Otherwise refuse:
        # range culling must never be reported as a physical optical miss.
        if np.any(np.abs(d.geom_xpos - origin) > mj.mjMAXVAL / math.sqrt(3)):
            raise ValueError("optical scene exceeds native ray range")
        count = len(directions)
        geoms = np.empty(count, dtype=np.int32)
        distances = np.empty(count, dtype=np.float64)
        mj.mj_multiRay(m, d, origin, directions.reshape(-1), None, 1, -1,
                      geoms, distances, count, mj.mjMAXVAL)
        if (not np.isfinite(distances).all() or np.any(geoms < -1)
                or np.any(geoms >= m.ngeom)
                or np.any((geoms == -1) != (distances == -1))
                or np.any((geoms >= 0) & (distances < 0))):
            raise ValueError("invalid native optical intersection")
        for array in (directions, geoms, distances):
            array.setflags(write=False)
        return RayGeometry(tuple(float(x) for x in origin), directions, geoms, distances)

    def advance(self, state: bytes, efforts: tuple[float, ...] | None, elapsed_us: int,
                available_work_j: float, *,
                effort_updates: tuple[tuple[int, float], ...] = ()) -> MechanicalSuccessor:
        """Advance one interval with full-vector or sparse anatomical input.

        Full vector replaces every command. None retains the previously applied
        vector; optional updates replace distinct addressed components. Constant
        effort is a declared zero-order-held mechanical input, NOT a posture
        servo, muscle metabolic model, chosen movement or learned coordination.
        Zero effort explicitly releases a motor. Sleep/depletion policy belongs
        to the existing caller, not this solver. No duplicate command store:
        ctrl is already part of the single native integration state.
        """
        lim, m, d = self.limits, self._model, self._data
        if (type(elapsed_us) is not int or elapsed_us <= 0
                or elapsed_us % lim.step_us or elapsed_us // lim.step_us > lim.max_substeps):
            raise ValueError("interval exceeds declared fixed-step budget")
        if not math.isfinite(available_work_j) or available_work_j < 0:
            raise ValueError("finite nonnegative mechanical supply required")
        if type(effort_updates) is not tuple or len(effort_updates) > m.nu:
            raise ValueError("bounded unique anatomical effort updates required")
        if efforts is not None and effort_updates:
            raise ValueError("full vector and incremental effort updates are exclusive")
        addressed = set()
        for item in effort_updates:
            if (type(item) is not tuple or len(item) != 2 or type(item[0]) is not int
                    or not 0 <= item[0] < m.nu or item[0] in addressed):
                raise ValueError("bounded unique anatomical effort updates required")
            addressed.add(item[0])
        self._restore(state)
        effort = d.ctrl.copy() if efforts is None else np.asarray(efforts, dtype=np.float64)
        for index, value in effort_updates:
            effort[index] = value
        if (effort.shape != (m.nu,) or not np.isfinite(effort).all()
                or np.any(effort < m.actuator_forcerange[:, 0])
                or np.any(effort > m.actuator_forcerange[:, 1])):
            raise ValueError("effort exceeds physical motor capacity")
        d.ctrl[:] = effort
        mj.mj_forward(m, d)
        initial_energy = float(sum(d.energy))
        initial_time = float(d.time)
        if math.ulp(initial_time) > m.opt.timestep:
            raise ValueError("mechanical time cannot represent this interval")
        positive_work = signed_work = braking_work = bearing_heat = travel_peak = 0.0
        self_bearing_heat = 0.0
        for _ in range(elapsed_us // lim.step_us):
            position, rotation = d.geom_xpos.copy(), d.geom_xmat.copy().reshape(-1, 3, 3)
            power_before = effort * d.qvel[self._motor_dof]
            bearing_before = float(np.dot(m.dof_damping, d.qvel**2))
            self_bearing_before = (0.0 if self._sensory_root is None else
                float(np.dot(m.dof_damping[self._self_dofs], d.qvel[self._self_dofs]**2)))
            mj.mj_step(m, d)
            mj.mj_kinematics(m, d)
            mj.mj_collision(m, d)
            self._check()
            power_after = effort * d.qvel[self._motor_dof]
            dt_half = m.opt.timestep / 2
            signed_work += float(np.sum(power_before + power_after)) * dt_half
            positive_work += float(np.sum(np.maximum(power_before, 0)
                                         + np.maximum(power_after, 0))) * dt_half
            braking_work += float(np.sum(np.maximum(-power_before, 0)
                                        + np.maximum(-power_after, 0))) * dt_half
            bearing_heat += (bearing_before + float(np.dot(m.dof_damping, d.qvel**2))) * dt_half
            if self._sensory_root is not None:
                self_bearing_after = float(np.dot(
                    m.dof_damping[self._self_dofs], d.qvel[self._self_dofs]**2))
                self_bearing_heat += (self_bearing_before + self_bearing_after) * dt_half
            if not all(math.isfinite(x) for x in (
                    positive_work, signed_work, braking_work, bearing_heat, self_bearing_heat)):
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
        observation = self._observation()
        residual = signed_work - (observation.kinetic_j + observation.potential_j - initial_energy) - bearing_heat
        if not math.isfinite(residual):
            raise ValueError("non-finite mechanical energy balance")
        return MechanicalSuccessor(self._capture(), observation, positive_work,
                                   signed_work, travel_peak, braking_work, bearing_heat, residual,
                                   None if self._sensory_root is None else self_bearing_heat)
