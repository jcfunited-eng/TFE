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


class DiscreteWork:
    """Actual discrete update from native solve arrays; no additional solve."""

    def __init__(self, engine):
        self.engine, self.pending = engine, None
        m = engine._model
        self.coupled_step = (mj.mj_versionString() == "3.3.7+guala.coupled-step.1"
                             and m.opt.integrator == mj.mjtIntegrator.mjINT_IMPLICITFAST)
        self.full_implicit = m.opt.integrator == mj.mjtIntegrator.mjINT_IMPLICIT
        if not self.full_implicit and m.opt.integrator != mj.mjtIntegrator.mjINT_IMPLICITFAST:
            raise AssertionError("discrete measurement requires implicit or implicitfast")
        if self.full_implicit:
            if m.ntendon or m.nflex or m.opt.density or m.opt.viscosity:
                raise AssertionError("full derivative probe excludes tendon/flex/fluid forces")
            if (np.any(m.D_rownnz <= 0)
                    or not np.array_equal(m.D_rowadr,
                        np.cumsum(np.r_[0, m.D_rownnz[:-1]]))
                    or int(np.sum(m.D_rownnz)) != m.nD):
                raise AssertionError("native derivative rows are not packed nonempty CSR")
            self.bias_max = np.zeros(m.nv)
            self.bias_abs_sum = np.zeros(m.nv)
            self.same_state_witness_max = np.zeros(m.nv)
            self.bias_samples = []
        self.expected_derivative = np.zeros(m.nD)
        self.expected_derivative[m.D_rowadr + m.D_diag] = -m.dof_damping
        self.product = np.empty(m.nv)
        self.max_impulse_residual = np.zeros(m.nv)
        self.max_force_composition_residual = np.zeros(m.nv)
        self.sum_abs_impulse_energy_bound = 0.
        self.max_abs_energy_closure = self.sum_abs_energy_closure = 0.
        self.work = defaultdict(float)
        self.constraint_row_work = defaultdict(float)
        self.max_row_work_disagreement = 0.
        self.max_coupled_acceleration_disagreement = 0.
        self.completed_steps = 0

    def finish(self, data):
        if self.pending is None:
            return
        pre_k, pre_u, post_k_at_pre_metric, work = self.pending
        post_u, post_k = map(float, data.energy)
        metric = post_k - post_k_at_pre_metric
        delta_k, delta_u = post_k-pre_k, post_u-pre_u
        model_delta_k = math.fsum(work[k] for k in
            ("actuator", "constraint", "passive", "negative_bias", "implicit")) + metric
        closure = delta_k - model_delta_k
        if not all(math.isfinite(x) for x in (metric, delta_k, delta_u, closure)):
            raise AssertionError("nonfinite discrete energy measurement")
        self.max_abs_energy_closure = max(self.max_abs_energy_closure, abs(closure))
        self.sum_abs_energy_closure += abs(closure)
        for key, value in work.items():
            self.work[key] += value
        self.work["metric"] += metric
        self.work["potential_change"] += delta_u
        self.work["kinetic_change"] += delta_k
        self.work["energy_closure"] += closure
        self.completed_steps += 1
        self.pending = None

    def step(self, pre_v, post_v):
        m, d = self.engine._model, self.engine._data
        if self.pending is not None:
            raise AssertionError("previous discrete step was not finished")
        if not self.full_implicit and not self.coupled_step and not np.array_equal(d.qDeriv, self.expected_derivative):
            raise AssertionError("compiled derivative is not bearing-only -B")
        if not np.array_equal(d.qfrc_passive, -m.dof_damping*pre_v):
            raise AssertionError("passive forces are not solely declared bearings")
        dt = m.opt.timestep
        delta_v, mean_v = post_v-pre_v, (pre_v+post_v)/2
        if self.coupled_step:
            disagreement = float(np.max(np.abs(delta_v/dt-d.qacc),initial=0))
            if not math.isfinite(disagreement):
                raise AssertionError("nonfinite coupled acceleration measurement")
            self.max_coupled_acceleration_disagreement = max(
                self.max_coupled_acceleration_disagreement, disagreement)
        force = d.qfrc_smooth + d.qfrc_constraint
        composition = d.qfrc_actuator + d.qfrc_passive - d.qfrc_bias
        self.max_force_composition_residual = np.maximum(
            self.max_force_composition_residual, np.abs(d.qfrc_smooth-composition))
        # qM and solved forces still belong to pre-step q, not advanced qpos.
        # mj_mulM is a const-data product; no extra forward/constraint solve.
        mj.mj_mulM(m, d, self.product, delta_v)
        if self.full_implicit:
            # Native qDeriv is the FULL nonsymmetric CSR matrix, not its
            # lower triangle or a symmetrized/bearing-only approximation.
            derivative_delta = np.add.reduceat(
                d.qDeriv * delta_v[m.D_colind], m.D_rowadr)
            residual = self.product - dt*derivative_delta - dt*force
            bias_impulse = dt*(derivative_delta + m.dof_damping*delta_v)
            fast_equation_at_this_increment = (
                self.product + dt*m.dof_damping*delta_v - dt*force)
            witness = fast_equation_at_this_increment - bias_impulse
            if not all(np.isfinite(v).all() for v in (derivative_delta, bias_impulse, witness)):
                raise AssertionError("nonfinite native derivative evidence")
            self.bias_max = np.maximum(self.bias_max, np.abs(bias_impulse))
            self.bias_abs_sum += np.abs(bias_impulse)
            self.same_state_witness_max = np.maximum(self.same_state_witness_max, np.abs(witness))
            elapsed_us = self.completed_steps*self.engine.limits.step_us
            if elapsed_us % 10000 == 0:
                self.bias_samples.append(dict(elapsed_us=elapsed_us,
                    impulse_by_dof=bias_impulse.tolist(),
                    signed_work_j=float(np.dot(mean_v, bias_impulse))))
        else:
            # Keep the previously proved fast arithmetic/order exactly.
            derivative_delta = -m.dof_damping*delta_v
            residual = self.product + dt*m.dof_damping*delta_v - dt*force
        self.max_impulse_residual = np.maximum(self.max_impulse_residual, np.abs(residual))
        self.sum_abs_impulse_energy_bound += float(np.sum(np.abs(mean_v*residual)))
        mj.mj_mulM(m, d, self.product, post_v)
        post_k_at_pre_metric = .5*float(np.dot(post_v, self.product))
        work = {key: dt*float(np.dot(mean_v, vector)) for key, vector in (
            ("actuator", d.qfrc_actuator), ("constraint", d.qfrc_constraint),
            ("passive", d.qfrc_passive), ("negative_bias", -d.qfrc_bias),
            ("implicit", derivative_delta))}
        if self.full_implicit:
            work["implicit_bias_derivative"] = float(np.dot(mean_v, bias_impulse))
            work["implicit_bearing"] = dt*float(np.dot(mean_v, -m.dof_damping*delta_v))
        work["bearing_trapezoid"] = dt/2 * float(np.dot(m.dof_damping, pre_v**2 + post_v**2))
        row_velocity = np.empty(d.nefc)
        mj.mj_mulJacVec(m,d,row_velocity,mean_v)
        row_work = dt*row_velocity*d.efc_force
        if not np.isfinite(row_work).all():
            raise AssertionError("nonfinite constraint row work")
        contact_types = (mj.mjtConstraint.mjCNSTR_CONTACT_FRICTIONLESS,
                         mj.mjtConstraint.mjCNSTR_CONTACT_PYRAMIDAL,
                         mj.mjtConstraint.mjCNSTR_CONTACT_ELLIPTIC)
        for i,value in enumerate(row_work):
            kind, ident = int(d.efc_type[i]), int(d.efc_id[i])
            physical = (tuple(int(g) for g in d.contact[ident].geom)
                        if kind in contact_types else (ident,))
            self.constraint_row_work[(kind,*physical)] += float(value)
        self.max_row_work_disagreement = max(self.max_row_work_disagreement,
            abs(math.fsum(map(float,row_work))-work["constraint"]))
        if (not np.isfinite(residual).all() or not math.isfinite(post_k_at_pre_metric)
                or not all(math.isfinite(x) for x in work.values())):
            raise AssertionError("nonfinite discrete impulse measurement")
        self.pending = (float(d.energy[1]), float(d.energy[0]), post_k_at_pre_metric, work)

    def report(self, result, trapezoidal_constraint_work):
        if self.pending is not None:
            raise AssertionError("final discrete endpoint missing")
        w = self.work
        physical_remaining = (w["actuator"] + w["constraint"] - w["bearing_trapezoid"]
                              - w["kinetic_change"] - w["potential_change"])
        explained_remaining = -math.fsum(w[k] for k in (
            "bearing_trapezoid", "passive", "implicit", "negative_bias",
            "metric", "potential_change", "energy_closure"))
        report = {
            "scope": "integrator-consistent exchange; NOT a heat law or continuous-error bound",
            "bearing_only_derivative_and_force_exact_each_step": True,
            "completed_steps": self.completed_steps,
            "work_j": dict(w),
            "max_absolute_impulse_residual_by_dof": self.max_impulse_residual.tolist(),
            "max_absolute_force_composition_residual_by_dof": self.max_force_composition_residual.tolist(),
            "sum_absolute_impulse_energy_residual_bound_j": self.sum_abs_impulse_energy_bound,
            "sum_absolute_discrete_energy_closure_j": self.sum_abs_energy_closure,
            "max_absolute_discrete_energy_closure_j": self.max_abs_energy_closure,
            "constraint_trapezoid_minus_discrete_j": trapezoidal_constraint_work-w["constraint"],
            "bearing_trapezoid_plus_passive_and_implicit_j":
                w["bearing_trapezoid"] + w["passive"] + w["implicit"],
            "physical_balance_with_discrete_constraint_j": physical_remaining,
            "explained_physical_balance_j": explained_remaining,
            "explanation_disagreement_j": physical_remaining-explained_remaining,
            "actuator_work_minus_ordinary_j": w["actuator"]-result.signed_motor_work_j,
            "bearing_quadrature_minus_ordinary_j": w["bearing_trapezoid"]-result.bearing_dissipation_j,
        }
        report["constraint_midpoint_work_by_type_and_physical_id"] = [
            {"constraint_type":k[0], "physical_id":k[1:], "signed_j":v}
            for k,v in sorted(self.constraint_row_work.items())]
        report["max_row_generalized_work_disagreement_j"] = self.max_row_work_disagreement
        if self.coupled_step:
            del report["bearing_only_derivative_and_force_exact_each_step"]
            report.update(integrator="coupled Newton/implicitfast",
                passive_force_equals_declared_bearings_each_step=True,
                max_solved_integrated_acceleration_disagreement=self.max_coupled_acceleration_disagreement,
                derivative_source="declared diagonal H=M+hB; stale native qDeriv not consumed")
        if self.full_implicit:
            del report["bearing_only_derivative_and_force_exact_each_step"]
            report.update(
                integrator="implicit",
                passive_force_equals_declared_bearings_each_step=True,
                derivative_source="actual native nonsymmetric qDeriv; no finite-difference solve",
                bias_derivative_max_absolute_impulse_by_dof=self.bias_max.tolist(),
                bias_derivative_sum_absolute_impulse_by_dof=self.bias_abs_sum.tolist(),
                same_state_algebraic_witness_max_residual_by_dof=self.same_state_witness_max.tolist(),
                bias_derivative_samples_every_10ms=self.bias_samples,
                witness_scope="same-state algebraic isolation, NOT a counterfactual trajectory")
        return report


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
        self.discrete = DiscreteWork(engine)

    def sample(self, qpos, qvel, elapsed_us):
        m, d = self.engine._model, self.engine._data
        self.discrete.finish(d)
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
            "constraint_endpoint_estimate_scope": (
                "Hybrid diagnostic: coupled step-start forces plus final instantaneous physical "
                "forward force. Trapezoidal constraint/remaining-closure fields are NOT discrete "
                "work attribution; use discrete_update."
                if self.discrete.coupled_step else
                "Trapezoidal endpoint-force estimate; discrete_update is integrator-consistent."),
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
            "discrete_update": self.discrete.report(result, constraint),
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
        audit.discrete.step(velocity, data.qvel)
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
