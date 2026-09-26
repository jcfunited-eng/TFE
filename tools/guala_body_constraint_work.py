"""Read-only-in-the-solver diagnostic of constraint work, never runtime authority.

The wrapper calls the original pinned mj_step exactly once, then reads its
pre-integration solve arrays before NativeBody refreshes contact geometry.
No native callback, additional solve, state correction or heat assignment.
Only one isolated single-threaded offline process may use this module.
"""
from collections import defaultdict
import math

import mujoco as mj
import numpy as np


class ConstraintWork:
    def __init__(self, engine):
        self.engine = engine
        self.previous = None
        self.initial_energy = None
        self.work = defaultdict(float)
        self.positive = defaultdict(float)
        self.negative = defaultdict(float)
        self.signed_motor = self.bearing = self.constraint_dof_work = 0.
        self.other_passive_work = 0.
        self.abs_step_imbalance = self.max_step_imbalance = 0.
        self.max_power_disagreement = self.max_other_passive_power = 0.
        self.max_solver_iterations = self.solver_at_cap_samples = 0
        self.events, self.trajectory = [], []
        self.step_count = 0
        self.previous_active = None

    def sample(self, qpos, qvel, elapsed_us):
        m, d = self.engine._model, self.engine._data
        # Contact indices are only meaningful in this same, unrefreshed solve.
        powers = defaultdict(float)
        active = set()
        contacts = (mj.mjtConstraint.mjCNSTR_CONTACT_FRICTIONLESS,
                    mj.mjtConstraint.mjCNSTR_CONTACT_PYRAMIDAL,
                    mj.mjtConstraint.mjCNSTR_CONTACT_ELLIPTIC)
        for i in range(d.nefc):
            kind, ident = int(d.efc_type[i]), int(d.efc_id[i])
            if kind in contacts:
                identity = tuple(int(g) for g in d.contact[ident].geom)
            else:
                identity = (ident,)
            key = (kind, *identity)
            force = float(d.efc_force[i])
            powers[key] += float(d.efc_vel[i]) * force
            if force != 0.:
                active.add(key)
        pc_rows = math.fsum(powers.values())
        pc_dof = float(np.dot(qvel, d.qfrc_constraint))
        self.max_power_disagreement = max(self.max_power_disagreement, abs(pc_rows - pc_dof))
        motor = d.ctrl * qvel[self.engine._motor_dof]
        bearing = float(np.dot(m.dof_damping, qvel**2))
        # Conservative spring work is already represented in d.energy.
        other_passive = float(np.dot(qvel, d.qfrc_passive - d.qfrc_spring + m.dof_damping*qvel))
        self.max_other_passive_power = max(self.max_other_passive_power, abs(other_passive))
        if np.any(d.qfrc_applied) or np.any(d.xfrc_applied):
            raise AssertionError("this diagnostic does not account for external applied force")
        energy = float(sum(d.energy))
        if not all(math.isfinite(x) for x in (pc_rows, pc_dof, bearing, energy, other_passive)):
            raise AssertionError("nonfinite diagnostic physical measurement")
        if not np.isfinite(motor).all() or not np.isfinite(qpos).all() or not np.isfinite(qvel).all():
            raise AssertionError("nonfinite diagnostic state")
        iterations = int(np.max(d.solver_niter, initial=0))
        self.max_solver_iterations = max(self.max_solver_iterations, iterations)
        self.solver_at_cap_samples += int(iterations >= m.opt.iterations)
        current = (powers, pc_dof, motor, bearing, energy, other_passive)
        if self.previous is None:
            self.initial_energy = energy
        else:
            before, dof_before, motor_before, bearing_before, energy_before, passive_before = self.previous
            half_dt = m.opt.timestep / 2
            step_constraint = 0.
            for key in sorted(before.keys() | powers.keys()):
                p, q = before.get(key, 0.), powers.get(key, 0.)
                work = (p+q)*half_dt
                self.work[key] += work
                self.positive[key] += (max(p, 0.) + max(q, 0.))*half_dt
                self.negative[key] += (min(p, 0.) + min(q, 0.))*half_dt
                step_constraint += work
            motor_work = float(np.sum(motor_before + motor)) * half_dt
            bearing_work = (bearing_before + bearing)*half_dt
            passive_work = (passive_before + other_passive)*half_dt
            self.signed_motor += motor_work
            self.bearing += bearing_work
            self.other_passive_work += passive_work
            self.constraint_dof_work += (dof_before + pc_dof)*half_dt
            imbalance = motor_work + step_constraint + passive_work - bearing_work - (energy-energy_before)
            self.abs_step_imbalance += abs(imbalance)
            self.max_step_imbalance = max(self.max_step_imbalance, abs(imbalance))
        self.previous = current
        signature = tuple(sorted(active))
        if signature != self.previous_active:
            self.events.append({"elapsed_us": elapsed_us, "active": signature})
            self.previous_active = signature
        # Diagnostic observation decimation only. ALL samples enter work and
        # per-step imbalance; none is omitted from NativeBody safety checking.
        if elapsed_us % 10000 == 0:
            self.trajectory.append({"elapsed_us": elapsed_us, "qpos": qpos.tolist(),
                                    "qvel": qvel.tolist(), "energy_j": energy,
                                    "constraint_power_w": pc_rows})

    def report(self, result):
        if self.previous is None or self.initial_energy is None:
            raise AssertionError("constraint observation did not see a solve")
        # These sums use the same vector/reduction order as NativeBody.advance.
        if self.signed_motor != result.signed_motor_work_j or self.bearing != result.bearing_dissipation_j:
            raise AssertionError("diagnostic endpoint pairing differs from ordinary work quadrature")
        constraint = math.fsum(self.work.values())
        return {
            "scope": "signed constraint exchange; NOT heat or certified continuous-solution error",
            "ordinary_successor_exact": True,
            "signed_motor_work_j": result.signed_motor_work_j,
            "positive_motor_work_j": result.positive_motor_work_j,
            "motor_braking_work_j": result.motor_braking_work_j,
            "bearing_dissipation_j": result.bearing_dissipation_j,
            "mechanical_energy_change_j": self.previous[4] - self.initial_energy,
            "constraint_work_j": constraint,
            "constraint_dof_work_j": self.constraint_dof_work,
            "other_passive_work_j": self.other_passive_work,
            "remaining_closure_j": result.unresolved_energy_exchange_j + constraint + self.other_passive_work,
            "sum_absolute_discrete_imbalance_j": self.abs_step_imbalance,
            "max_absolute_discrete_imbalance_j": self.max_step_imbalance,
            "max_constraint_power_disagreement_w": self.max_power_disagreement,
            "max_other_passive_power_w": self.max_other_passive_power,
            "max_solver_iterations": self.max_solver_iterations,
            "solver_at_cap_samples": self.solver_at_cap_samples,
            "work_by_type_and_physical_id": [
                {"constraint_type": k[0], "physical_id": k[1:],
                 "signed_j": self.work[k], "positive_j": self.positive[k], "negative_j": self.negative[k]}
                for k in sorted(self.work)],
            "active_constraint_group_events": self.events,
            "event_scope": "active type/entity groups; internal contact-row/manifold churn is not measured",
            "trajectory_every_10ms": self.trajectory,
            "substeps": self.step_count,
        }


def advance_with_constraint_work(engine, state, elapsed_us, supply_j, *, effort_updates):
    """Compare an unchanged ordinary run to one with read-only solve observation."""
    ordinary = engine.advance(state, None, elapsed_us, supply_j, effort_updates=effort_updates)
    audit = ConstraintWork(engine)
    original = mj.mj_step

    def observed_step(model, data):
        if model is not engine._model or data is not engine._data:
            raise AssertionError("diagnostic crossed its isolated native body")
        qpos, velocity = data.qpos.copy(), data.qvel.copy()
        # Native mj_step calls the C forward solver, then implicit integration.
        # Its energy, efc and qfrc fields still describe this PRE-step state.
        original(model, data)
        audit.sample(qpos, velocity, audit.step_count * engine.limits.step_us)
        audit.step_count += 1

    try:
        mj.mj_step = observed_step
        observed = engine.advance(state, None, elapsed_us, supply_j, effort_updates=effort_updates)
    finally:
        mj.mj_step = original
    if observed != ordinary:
        raise AssertionError("constraint observer changed ordinary successor")
    if audit.step_count != elapsed_us // engine.limits.step_us:
        raise AssertionError("unexpected native step count")
    # NativeBody's existing final forward solve has synchronized these arrays.
    # Do not insert a new solve or alter warm-start history to obtain the endpoint.
    audit.sample(engine._data.qpos.copy(), engine._data.qvel.copy(), elapsed_us)
    return observed, audit.report(observed)
