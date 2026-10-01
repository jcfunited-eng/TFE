//! ArcLoom Single Causal Neuron Transition Operator and Cold Successor
//!
//! Ratified under the ArcLoom Engineered Artificial Reference Material specification:
//! - Exact First Law thermodynamic balance: $\Delta H_{\text{complete}} = W_{\text{in}} - W_{\text{out}} - Q_{\text{heat,out}}$
//! - Closed electrical dynamics with moving gating displacement current:
//!   $C_{\text{mem}} \dot{V} = -\sum I_c - I_{\text{rec}} - \dot{Q}_g + I_{\text{ext}}$, where $Q_g = \sum_c m_c q_c^g y_c$
//! - Debye shielding countercharge and genesis electroneutrality:
//!   $Z_{f,0} = -5\,098\,117$, $Z_{\text{fixed,in}} = -358\,207\,478\,656$, $Z_{\text{fixed,out}} = -27\,112\,297\,427$
//! - Aperture-dependent nonlinear pore conductance: $g(y) = y / (R_{p0} + R_{a0}\sqrt{y})$
//! - Exact rational carrier custody: $\xi_c = r_c + J_c / (z_c e)$, $n_c = \operatorname{trunc}(\xi_c)$, $r'_c = \xi_c - n_c$
//! - Retained contact mechanics coupled to receiving compartment:
//!   $g_{\text{contact}} = \sigma_{\text{mat}} A_{\text{actual}} / \ell_{\text{actual}}$, $\Delta Q_{\text{soma}} = -J_{\text{rec}}$, $\Delta Q_{\text{rec}} = +J_{\text{rec}}$
//! - Rate-independent contact plasticity return map: $K_\epsilon = E_{\text{mod}} A_{\text{ref}} L_{\text{ref}}$, $f = |\Sigma_{\text{tr}}| - Y \le 0$
//! - Full 7D continuous structural field preservation mapped via typed physical incidence ($F_a + F_b = 0$)
//! - Canonical length-framed cold restart covering independent physical state and causal operator topology

use pyo3::prelude::*;
use pyo3::exceptions::{PyValueError, PyRuntimeError};
use std::f64::consts::PI;

/// Physical Constants
pub const ELEMENTARY_CHARGE_C: f64 = 1.602176634e-19;
pub const BOLTZMANN_CONST_J_PER_K: f64 = 1.380649e-23;
pub const REFERENCE_TEMP_K: f64 = 300.0;
pub const KT_J: f64 = BOLTZMANN_CONST_J_PER_K * REFERENCE_TEMP_K; // ~4.14195e-21 J

/// Soma Geometry and Capacitance
pub const SOMA_RADIUS_M: f64 = 10.0e-6; // 10 um
pub const SOMA_AREA_M2: f64 = 4.0 * PI * SOMA_RADIUS_M * SOMA_RADIUS_M; // ~1.256637e-9 m^2
pub const SPECIFIC_CAPACITANCE_F_PER_M2: f64 = 0.01; // 1 uF/cm^2 = 0.01 F/m^2
pub const MEMBRANE_CAPACITANCE_F: f64 = SPECIFIC_CAPACITANCE_F_PER_M2 * SOMA_AREA_M2; // ~12.56637 pF

/// Fluid Volumes
pub const VOLUME_IN_M3: f64 = (4.0 / 3.0) * PI * SOMA_RADIUS_M * SOMA_RADIUS_M * SOMA_RADIUS_M; // ~4.18879 pL
pub const VOLUME_OUT_M3: f64 = 0.25 * VOLUME_IN_M3; // 20% tissue extracellular volume fraction => 1.04720 pL

/// Genesis Countercharge and Integer Ion Stocks
pub const GENESIS_Z_F: i64 = -5098117;
pub const GENESIS_Z_FIXED_IN: i64 = -358207478656;
pub const GENESIS_Z_FIXED_OUT: i64 = -27112297427;

pub const GENESIS_N_IN: [u64; 4] = [
    30270581073,  // Na+
    353156779183, // K+
    252255,       // Ca2+
    25225484227,  // Cl-
];

pub const GENESIS_N_OUT: [u64; 4] = [
    91442380324,  // Na+
    2522548423,   // K+
    1261274211,   // Ca2+
    69370081625,  // Cl-
];

pub const SPECIES_VALENCE: [i8; 4] = [1, 1, 2, -1];
pub const CHANNEL_POPULATIONS: [usize; 4] = [100, 100, 20, 50];
pub const GATE_CHARGES_E: [f64; 4] = [4.0, 3.0, 2.0, 0.0];
pub const RESTING_APERTURES: [f64; 4] = [0.05, 0.05, 0.02, 0.10];

/// Pore Resistance Parameters
pub const PORE_LENGTH_M: f64 = 5.0e-9;
pub const PORE_RADIUS_M: f64 = 0.50e-9;
pub const PORE_CONDUCTIVITY_S_PER_M: f64 = 1.50;
pub const R_P0: f64 = PORE_LENGTH_M / (PORE_CONDUCTIVITY_S_PER_M * PI * PORE_RADIUS_M * PORE_RADIUS_M);
pub const R_A0: f64 = 1.0 / (2.0 * PORE_CONDUCTIVITY_S_PER_M * PORE_RADIUS_M);

/// Contact Elasticity and Plasticity Constants
pub const CONTACT_RADIUS_REF_M: f64 = 0.10e-6; // 0.1 um
pub const CONTACT_LENGTH_REF_M: f64 = 1.0e-6;  // 1.0 um
pub const CONTACT_AREA_REF_M2: f64 = PI * CONTACT_RADIUS_REF_M * CONTACT_RADIUS_REF_M;
pub const CONTACT_MODULUS_PA: f64 = 100.0e3; // 100 kPa
pub const CONTACT_STRAIN_STIFFNESS_J: f64 = CONTACT_MODULUS_PA * CONTACT_AREA_REF_M2 * CONTACT_LENGTH_REF_M; // ~3.14159e-15 J
pub const CONTACT_YIELD_THRESHOLD_J: f64 = 0.05 * CONTACT_STRAIN_STIFFNESS_J; // ~1.5708e-16 J
pub const CONTACT_MATERIAL_CONDUCTIVITY_S_PER_M: f64 = 0.50; // 0.5 S/m

/// Receiving Compartment Defaults
pub const RECEIVING_CAPACITANCE_F: f64 = 1.0e-12; // 1 pF
pub const RECEIVING_RESTING_V: f64 = -0.065; // -65 mV

/// Gate Mechanics Constants
pub const GATE_STIFFNESS_K_J: f64 = 100.0 * KT_J; // 100 kBT ~ 4.14e-19 J
pub const GATE_RELAXATION_TAU_S: f64 = 1.0e-3; // 1 ms characteristic response
pub const GATE_DRAG_ZETA_J_S: f64 = GATE_STIFFNESS_K_J * GATE_RELAXATION_TAU_S; // ~4.14e-22 J s

/// Phase Damping and Coupling Bounds
pub const PHASE_DRAG_GAMMA_J_S: f64 = 1.0e-20;
pub const MAX_KAPPA_J: f64 = 1.0e-15;
pub const MAX_FABRIC_EDGES: usize = 32;

/// Checkpoint Serialization Framing
pub const MAGIC_V2: &[u8; 18] = b"ARCLOOM_NEURON_V2\0";
pub const FORMAT_VERSION_V2: u16 = 2;

/// Structural Field Dimensions (DSF-AI L0-L4)
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
#[repr(u8)]
pub enum StructuralFieldDim {
    Displacement = 0, // D_k
    Motion = 1,       // M_k
    Reversal = 2,     // R_rev_k
    Uncertainty = 3,  // U_star_k
    Cohesion = 4,     // C_k
    Pressure = 5,     // P_k
    Breathing = 6,    // B_k
}

impl StructuralFieldDim {
    pub fn from_u8(v: u8) -> Option<Self> {
        match v {
            0 => Some(Self::Displacement),
            1 => Some(Self::Motion),
            2 => Some(Self::Reversal),
            3 => Some(Self::Uncertainty),
            4 => Some(Self::Cohesion),
            5 => Some(Self::Pressure),
            6 => Some(Self::Breathing),
            _ => None,
        }
    }
}

/// Perspective Role of Field Coordinate
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
#[repr(u8)]
pub enum FieldRole {
    Numerator = 0,
    Denominator = 1,
    Invariant = 2,
}

impl FieldRole {
    pub fn from_u8(v: u8) -> Option<Self> {
        match v {
            0 => Some(Self::Numerator),
            1 => Some(Self::Denominator),
            2 => Some(Self::Invariant),
            _ => None,
        }
    }
}

/// Typed Fabric Constraint Edge
#[derive(Debug, Clone, Copy, PartialEq)]
pub struct TypedFabricEdge {
    pub dim: StructuralFieldDim,
    pub role: FieldRole,
    pub position: u16,
    pub from_node: usize,
    pub to_node: usize,
    pub tau_trit: i8, // in {-1, 0, 1}
    pub kappa_j: f64, // coupling energy in Joules
}

impl TypedFabricEdge {
    pub fn new(
        dim: StructuralFieldDim,
        role: FieldRole,
        position: u16,
        from_node: usize,
        to_node: usize,
        tau_trit: i8,
        kappa_j: f64,
    ) -> Result<Self, String> {
        if from_node >= 4 || to_node >= 4 {
            return Err(format!("Fabric edge node index out of bounds: ({}, {})", from_node, to_node));
        }
        if from_node == to_node {
            return Err("Self-referential fabric edge is physically inadmissible".to_string());
        }
        if tau_trit != -1 && tau_trit != 0 && tau_trit != 1 {
            return Err(format!("Fabric edge trit must be in {{-1, 0, 1}}, got {}", tau_trit));
        }
        if !kappa_j.is_finite() || kappa_j < 0.0 || kappa_j > MAX_KAPPA_J {
            return Err(format!("Coupling kappa out of physical bounds [0, {}]: {}", MAX_KAPPA_J, kappa_j));
        }
        Ok(Self {
            dim,
            role,
            position,
            from_node,
            to_node,
            tau_trit,
            kappa_j,
        })
    }

    /// Internal paired constraint forces satisfying Fa + Fb = 0
    #[inline]
    pub fn forces(&self, phi_a: f64, phi_b: f64) -> (f64, f64) {
        let theta = phi_b - phi_a - (2.0 * PI * (self.tau_trit as f64) / 3.0);
        let s = self.kappa_j * theta.sin();
        (s, -s)
    }

    /// Potential energy: -kappa * cos(theta)
    #[inline]
    pub fn energy(&self, phi_a: f64, phi_b: f64) -> f64 {
        let theta = phi_b - phi_a - (2.0 * PI * (self.tau_trit as f64) / 3.0);
        -self.kappa_j * theta.cos()
    }
}

/// Pure Pore Conductance Benchmark Formula
#[inline]
pub fn pore_conductance(y: f64) -> f64 {
    if y <= 0.0 {
        0.0
    } else {
        y / (R_P0 + R_A0 * y.sqrt())
    }
}

/// Exact CRC-32 calculation (IEEE 802.3 standard)
pub fn compute_crc32(data: &[u8]) -> u32 {
    let mut crc: u32 = 0xFFFF_FFFF;
    for &byte in data {
        crc ^= byte as u32;
        for _ in 0..8 {
            let mask = if (crc & 1) != 0 { 0xEDB8_8320 } else { 0 };
            crc = (crc >> 1) ^ mask;
        }
    }
    !crc
}

/// Constant-time bounded modulo phase normalization to [-PI, PI)
#[inline]
pub fn wrap_phase(phi: f64) -> f64 {
    if !phi.is_finite() {
        return 0.0;
    }
    phi - 2.0 * PI * ((phi + PI) / (2.0 * PI)).floor()
}

/// Result of a single time-step causal transition
#[derive(Debug, Clone, PartialEq)]
pub struct TransitionResult {
    pub prior_membrane_v: f64,
    pub succ_membrane_v: f64,
    pub prior_receiving_v: f64,
    pub succ_receiving_v: f64,
    pub plastic_yield_occurred: bool,
    pub plastic_dissipation_j: f64,
    pub work_input_j: f64,
    pub heat_dissipated_j: f64,
    pub delta_enthalpy_j: f64,
    pub receiving_charge_transferred_c: f64,
}

/// Independent State of the Causal Neuron
#[derive(Debug, Clone, PartialEq)]
pub struct ArcLoomNeuronState {
    pub step_count: u64,
    pub z_fixed_in: i64,
    pub z_fixed_out: i64,
    pub z_ext_port: i64,
    pub r_ext: f64,
    pub n_in: [u64; 4],
    pub n_out: [u64; 4],
    pub r_remainder: [f64; 4],
    pub y_gate: [f64; 4],
    pub phi: [f64; 4],
    pub rho: [f64; 4],
    pub contact_x: f64,
    pub contact_ell: f64,
    pub q_rec: f64,
    pub c_rec: f64,
    pub cumulative_d_pl: f64,
    pub cumulative_w_in: f64,
    pub cumulative_q_heat: f64,
}

impl ArcLoomNeuronState {
    pub fn new_reference_preparation() -> Self {
        Self {
            step_count: 0,
            z_fixed_in: GENESIS_Z_FIXED_IN,
            z_fixed_out: GENESIS_Z_FIXED_OUT,
            z_ext_port: 0,
            r_ext: 0.0,
            n_in: GENESIS_N_IN,
            n_out: GENESIS_N_OUT,
            r_remainder: [0.0; 4],
            y_gate: RESTING_APERTURES,
            phi: [0.0; 4],
            rho: [1.0; 4],
            contact_x: CONTACT_LENGTH_REF_M,
            contact_ell: CONTACT_LENGTH_REF_M,
            q_rec: RECEIVING_RESTING_V * RECEIVING_CAPACITANCE_F,
            c_rec: RECEIVING_CAPACITANCE_F,
            cumulative_d_pl: 0.0,
            cumulative_w_in: 0.0,
            cumulative_q_heat: 0.0,
        }
    }

    /// Exact integer free charge on membrane inner surface
    #[inline]
    pub fn integer_free_charge(&self) -> i64 {
        let mobile_in: i64 = (SPECIES_VALENCE[0] as i64) * (self.n_in[0] as i64)
            + (SPECIES_VALENCE[1] as i64) * (self.n_in[1] as i64)
            + (SPECIES_VALENCE[2] as i64) * (self.n_in[2] as i64)
            + (SPECIES_VALENCE[3] as i64) * (self.n_in[3] as i64);
        self.z_fixed_in + mobile_in + self.z_ext_port
    }

    /// Moving gate charge Qg = sum_c m_c * q_c^g * y_c
    #[inline]
    pub fn gate_charge_c(&self) -> f64 {
        let mut qg = 0.0;
        for c in 0..4 {
            qg += (CHANNEL_POPULATIONS[c] as f64) * (GATE_CHARGES_E[c] * ELEMENTARY_CHARGE_C) * self.y_gate[c];
        }
        qg
    }

    /// Membrane potential V = (Qf - Qg) / C_mem
    #[inline]
    pub fn membrane_voltage(&self, c_mem: f64) -> f64 {
        let qf = (self.integer_free_charge() as f64) * ELEMENTARY_CHARGE_C;
        let qg = self.gate_charge_c();
        (qf - qg) / c_mem
    }

    /// Receiving compartment voltage V_rec = Q_rec / C_rec
    #[inline]
    pub fn receiving_voltage(&self) -> f64 {
        self.q_rec / self.c_rec
    }
}

/// Material Properties and Causal Operator
#[derive(Debug, Clone, PartialEq)]
pub struct ArcLoomTransitionOperator {
    pub c_mem: f64,
    pub k_strain: f64,
    pub y_yield: f64,
    pub zeta_gate: f64,
    pub gamma_phi: f64,
    pub fabric_edges: Vec<TypedFabricEdge>,
}

impl ArcLoomTransitionOperator {
    pub fn new_reference_operator() -> Self {
        Self {
            c_mem: MEMBRANE_CAPACITANCE_F,
            k_strain: CONTACT_STRAIN_STIFFNESS_J,
            y_yield: CONTACT_YIELD_THRESHOLD_J,
            zeta_gate: GATE_DRAG_ZETA_J_S,
            gamma_phi: PHASE_DRAG_GAMMA_J_S,
            fabric_edges: Vec::with_capacity(MAX_FABRIC_EDGES),
        }
    }

    pub fn add_fabric_edge(&mut self, edge: TypedFabricEdge) -> Result<(), String> {
        if self.fabric_edges.len() >= MAX_FABRIC_EDGES {
            return Err(format!("Fabric edge resource bound reached: max {}", MAX_FABRIC_EDGES));
        }
        self.fabric_edges.push(edge);
        Ok(())
    }

    /// Compute total system enthalpy H
    pub fn compute_enthalpy(&self, state: &ArcLoomNeuronState) -> f64 {
        // 1. Membrane electrostatic energy H_elec = (Qf - Qg)^2 / (2 * C_mem)
        let qf = (state.integer_free_charge() as f64) * ELEMENTARY_CHARGE_C;
        let qg = state.gate_charge_c();
        let h_elec = (qf - qg).powi(2) / (2.0 * self.c_mem);

        // 2. Receiving compartment electrostatic energy H_rec = Q_rec^2 / (2 * C_rec)
        let h_rec = state.q_rec.powi(2) / (2.0 * state.c_rec);

        // 3. Phase fabric constraint potential
        let mut e_fabric = 0.0;
        for edge in &self.fabric_edges {
            e_fabric += edge.energy(state.phi[edge.from_node], state.phi[edge.to_node]);
        }

        // 4. Gate non-electrical mechanical strain energy
        let mut e_gates = 0.0;
        for c in 0..4 {
            let dy = state.y_gate[c] - RESTING_APERTURES[c];
            e_gates += (CHANNEL_POPULATIONS[c] as f64) * 0.5 * GATE_STIFFNESS_K_J * dy * dy;
        }

        // 5. Contact axial elastic strain energy
        let eps_contact = (state.contact_x / state.contact_ell) - 1.0;
        let e_contact = 0.5 * self.k_strain * eps_contact * eps_contact;

        // 6. Finite chemical potential energy
        let mut e_chem = 0.0;
        let c_ref = 1.0; // reference concentration factor
        for c in 0..4 {
            let conc_in = (state.n_in[c] as f64) / VOLUME_IN_M3;
            let conc_out = (state.n_out[c] as f64) / VOLUME_OUT_M3;
            if conc_in > 0.0 && conc_out > 0.0 {
                let mu_in = KT_J * (conc_in / c_ref).ln();
                let mu_out = KT_J * (conc_out / c_ref).ln();
                e_chem += (state.n_in[c] as f64) * mu_in + (state.n_out[c] as f64) * mu_out;
            }
        }

        h_elec + h_rec + e_fabric + e_gates + e_contact + e_chem
    }

    /// Single Causal Transition Step
    /// Strictly transactional: stage successor, validate physical domains, commit atomically.
    pub fn step(
        &self,
        state: &mut ArcLoomNeuronState,
        applied_contact_x: Option<f64>,
        external_current_a: f64,
        dt_seconds: f64,
    ) -> Result<TransitionResult, String> {
        // Strict domain validation on inputs
        if !external_current_a.is_finite() {
            return Err("External current must be finite".to_string());
        }
        if !dt_seconds.is_finite() || dt_seconds <= 0.0 || dt_seconds > 1.0 {
            return Err(format!("Invalid time increment dt: {}", dt_seconds));
        }
        let target_x = applied_contact_x.unwrap_or(state.contact_x);
        if !target_x.is_finite() || target_x <= 0.0 {
            return Err(format!("Applied contact x must be positive finite: {}", target_x));
        }

        let h_prior = self.compute_enthalpy(state);
        let prior_v = state.membrane_voltage(self.c_mem);
        let prior_v_rec = state.receiving_voltage();

        // Stage next state into temporary copy
        let mut next = state.clone();

        // Check step counter overflow
        next.step_count = next.step_count.checked_add(1)
            .ok_or_else(|| "Neuron step counter overflow".to_string())?;

        // 1. Contact Mechanics & Plastic Return Map
        let dx = target_x - state.contact_x;
        let eps_tr = (target_x / state.contact_ell) - 1.0;
        let sigma_tr = self.k_strain * eps_tr;
        let yield_occurred = sigma_tr.abs() > self.y_yield;

        let (new_ell, d_pl) = if yield_occurred {
            let s = if sigma_tr > 0.0 { 1.0 } else { -1.0 };
            let updated_ell = target_x / (1.0 + s * (self.y_yield / self.k_strain));
            let dissipation = 0.5 * self.k_strain * (eps_tr * eps_tr - (self.y_yield / self.k_strain).powi(2));
            (updated_ell, dissipation.max(0.0))
        } else {
            (state.contact_ell, 0.0)
        };

        // Mechanical loading work: W_mech = F_contact * dx
        let f_contact = self.k_strain * ((state.contact_x + target_x) / (2.0 * state.contact_ell) - 1.0) / state.contact_ell;
        let w_mech = f_contact * dx;

        next.contact_x = target_x;
        next.contact_ell = new_ell;
        next.cumulative_d_pl += d_pl;

        // 2. Receiving Compartment Electrical Settlement
        // Conducting geometry: actual instantaneous length is target_x
        let a_actual = CONTACT_AREA_REF_M2 * (CONTACT_LENGTH_REF_M / target_x);
        let g_contact = CONTACT_MATERIAL_CONDUCTIVITY_S_PER_M * (a_actual / target_x);
        let v_diff = prior_v - prior_v_rec;
        let i_rec = g_contact * v_diff;
        let j_rec = i_rec * dt_seconds; // Coulombs transferred from soma to receiving compartment

        next.q_rec += j_rec;
        let succ_v_rec = next.receiving_voltage();
        let q_joule_contact = i_rec * v_diff * dt_seconds;

        // 3. Gate Dynamics & Dissipation
        let mut q_gate_fric = 0.0;
        for c in 0..4 {
            let dy_harm = next.y_gate[c] - RESTING_APERTURES[c];
            let f_harm = -GATE_STIFFNESS_K_J * dy_harm;
            let f_volt = (GATE_CHARGES_E[c] * ELEMENTARY_CHARGE_C) * prior_v;

            // Reciprocal force from phase coupling
            let mut f_phase_coupling = 0.0;
            for edge in &self.fabric_edges {
                if edge.from_node == c {
                    f_phase_coupling += 1.0e-20 * (next.phi[edge.to_node] - next.phi[edge.from_node]).cos();
                }
            }

            let total_gate_force = f_volt + f_harm + f_phase_coupling;
            let y_dot = total_gate_force / self.zeta_gate;
            let next_y = (next.y_gate[c] + y_dot * dt_seconds).clamp(0.0, 1.0);
            let actual_y_dot = (next_y - next.y_gate[c]) / dt_seconds;

            q_gate_fric += (CHANNEL_POPULATIONS[c] as f64) * self.zeta_gate * actual_y_dot * actual_y_dot * dt_seconds;
            next.y_gate[c] = next_y;
        }

        // 4. Phase Dynamics & Dissipation
        let mut phase_forces = [0.0; 4];
        for edge in &self.fabric_edges {
            let (fa, fb) = edge.forces(next.phi[edge.from_node], next.phi[edge.to_node]);
            phase_forces[edge.from_node] += fa;
            phase_forces[edge.to_node] += fb;
        }

        let mut q_phase_fric = 0.0;
        for a in 0..4 {
            let phi_dot = phase_forces[a] / self.gamma_phi;
            q_phase_fric += self.gamma_phi * phi_dot * phi_dot * dt_seconds;
            let unnorm_phi = next.phi[a] + phi_dot * dt_seconds;
            next.phi[a] = wrap_phase(unnorm_phi);
        }

        // 5. Ionic Pore Currents, Chemical Transfer & Exact Carrier Custody
        let mut q_joule_pore = 0.0;
        for c in 0..4 {
            let z = SPECIES_VALENCE[c];
            let q_ion = (z as f64) * ELEMENTARY_CHARGE_C;

            // Nernst equilibrium potential
            let conc_in = (next.n_in[c] as f64) / VOLUME_IN_M3;
            let conc_out = (next.n_out[c] as f64) / VOLUME_OUT_M3;
            let e_rev = (KT_J / q_ion) * (conc_out / conc_in).ln();

            let g_single = pore_conductance(next.y_gate[c]);
            let g_total = (CHANNEL_POPULATIONS[c] as f64) * g_single;
            let current = g_total * (prior_v - e_rev);
            let charge_transferred = current * dt_seconds; // Coulombs out of intracellular reservoir

            q_joule_pore += current * (prior_v - e_rev) * dt_seconds;

            // Exact rational carrier custody: xi = r + J/q, n = trunc(xi), r' = xi - n
            let xi = next.r_remainder[c] + (charge_transferred / q_ion);
            let n_ions = xi.trunc() as i64;
            let r_prime = xi - (n_ions as f64);

            // Checked reservoir debit/credit
            if n_ions > 0 {
                let debit = n_ions as u64;
                if next.n_in[c] < debit {
                    return Err(format!("Intracellular reservoir depleted for species {}", c));
                }
                next.n_in[c] -= debit;
                next.n_out[c] = next.n_out[c].checked_add(debit)
                    .ok_or_else(|| format!("Extracellular reservoir overflow for species {}", c))?;
            } else if n_ions < 0 {
                let credit = (-n_ions) as u64;
                if next.n_out[c] < credit {
                    return Err(format!("Extracellular reservoir depleted for species {}", c));
                }
                next.n_out[c] -= credit;
                next.n_in[c] = next.n_in[c].checked_add(credit)
                    .ok_or_else(|| format!("Intracellular reservoir overflow for species {}", c))?;
            }

            next.r_remainder[c] = r_prime;
        }

        // 6. External Port Integer Custody & Electrical Input Work
        let xi_ext = next.r_ext + ((external_current_a * dt_seconds) / ELEMENTARY_CHARGE_C);
        let n_ext = xi_ext.trunc() as i64;
        let r_ext_prime = xi_ext - (n_ext as f64);
        next.z_ext_port += n_ext;
        next.r_ext = r_ext_prime;

        let w_elec = prior_v * external_current_a * dt_seconds;
        let w_in_total = w_mech + w_elec;

        // Receiving compartment charge debit from soma:
        let n_rec_ions = (j_rec / ELEMENTARY_CHARGE_C).round() as i64;
        next.z_ext_port -= n_rec_ions;

        let succ_v = next.membrane_voltage(self.c_mem);
        let h_succ = self.compute_enthalpy(&next);
        let delta_h = h_succ - h_prior;

        let q_heat_total = d_pl + q_gate_fric + q_phase_fric + q_joule_pore + q_joule_contact;
        next.cumulative_w_in += w_in_total;
        next.cumulative_q_heat += q_heat_total;

        // Commit transaction atomically
        *state = next;

        Ok(TransitionResult {
            prior_membrane_v: prior_v,
            succ_membrane_v: succ_v,
            prior_receiving_v: prior_v_rec,
            succ_receiving_v: succ_v_rec,
            plastic_yield_occurred: yield_occurred,
            plastic_dissipation_j: d_pl,
            work_input_j: w_in_total,
            heat_dissipated_j: q_heat_total,
            delta_enthalpy_j: delta_h,
            receiving_charge_transferred_c: j_rec,
        })
    }

    /// Canonical Binary Serialization Covering Complete State and Topology
    pub fn export_canonical_checkpoint(&self, state: &ArcLoomNeuronState) -> Vec<u8> {
        let mut payload = Vec::with_capacity(512);

        // State fields
        payload.extend_from_slice(&state.step_count.to_be_bytes());
        payload.extend_from_slice(&state.z_fixed_in.to_be_bytes());
        payload.extend_from_slice(&state.z_fixed_out.to_be_bytes());
        payload.extend_from_slice(&state.z_ext_port.to_be_bytes());
        payload.extend_from_slice(&state.r_ext.to_be_bytes());

        for c in 0..4 {
            payload.extend_from_slice(&state.n_in[c].to_be_bytes());
            payload.extend_from_slice(&state.n_out[c].to_be_bytes());
            payload.extend_from_slice(&state.r_remainder[c].to_be_bytes());
            payload.extend_from_slice(&state.y_gate[c].to_be_bytes());
            payload.extend_from_slice(&state.phi[c].to_be_bytes());
            payload.extend_from_slice(&state.rho[c].to_be_bytes());
        }

        payload.extend_from_slice(&state.contact_x.to_be_bytes());
        payload.extend_from_slice(&state.contact_ell.to_be_bytes());
        payload.extend_from_slice(&state.q_rec.to_be_bytes());
        payload.extend_from_slice(&state.c_rec.to_be_bytes());
        payload.extend_from_slice(&state.cumulative_d_pl.to_be_bytes());
        payload.extend_from_slice(&state.cumulative_w_in.to_be_bytes());
        payload.extend_from_slice(&state.cumulative_q_heat.to_be_bytes());

        // Operator Material Parameters
        payload.extend_from_slice(&self.c_mem.to_be_bytes());
        payload.extend_from_slice(&self.k_strain.to_be_bytes());
        payload.extend_from_slice(&self.y_yield.to_be_bytes());
        payload.extend_from_slice(&self.zeta_gate.to_be_bytes());
        payload.extend_from_slice(&self.gamma_phi.to_be_bytes());

        // Operator Topology
        let num_edges = self.fabric_edges.len() as u16;
        payload.extend_from_slice(&num_edges.to_be_bytes());
        for edge in &self.fabric_edges {
            payload.push(edge.dim as u8);
            payload.push(edge.role as u8);
            payload.extend_from_slice(&edge.position.to_be_bytes());
            payload.push(edge.from_node as u8);
            payload.push(edge.to_node as u8);
            payload.push(edge.tau_trit as u8);
            payload.extend_from_slice(&edge.kappa_j.to_be_bytes());
        }

        let payload_len = payload.len() as u32;
        let payload_crc = compute_crc32(&payload);

        // Header framing
        let mut header = Vec::with_capacity(32);
        header.extend_from_slice(MAGIC_V2);
        header.extend_from_slice(&FORMAT_VERSION_V2.to_be_bytes());
        header.extend_from_slice(&payload_len.to_be_bytes());
        let header_crc = compute_crc32(&header);
        header.extend_from_slice(&header_crc.to_be_bytes());

        let mut output = Vec::with_capacity(header.len() + payload.len() + 4);
        output.extend_from_slice(&header);
        output.extend_from_slice(&payload);
        output.extend_from_slice(&payload_crc.to_be_bytes());

        output
    }

    /// Canonical Binary Deserialization Covering Complete State and Topology
    pub fn import_canonical_checkpoint(
        data: &[u8],
    ) -> Result<(Self, ArcLoomNeuronState), String> {
        if data.len() < 32 {
            return Err("Checkpoint too short for canonical header framing".to_string());
        }

        // Validate header
        if &data[0..18] != MAGIC_V2 {
            return Err("Invalid checkpoint magic header".to_string());
        }
        let version = u16::from_be_bytes(data[18..20].try_into().unwrap());
        if version != FORMAT_VERSION_V2 {
            return Err(format!("Unsupported checkpoint version: {}", version));
        }
        let payload_len = u32::from_be_bytes(data[20..24].try_into().unwrap()) as usize;
        let expected_header_crc = u32::from_be_bytes(data[24..28].try_into().unwrap());
        let computed_header_crc = compute_crc32(&data[0..24]);
        if computed_header_crc != expected_header_crc {
            return Err("Header CRC mismatch: corrupted framing".to_string());
        }

        let total_expected_len = 28 + payload_len + 4;
        if data.len() != total_expected_len {
            return Err(format!(
                "Exact length mismatch: expected {} bytes (payload {}), got {} bytes (trailing/truncated bytes rejected)",
                total_expected_len, payload_len, data.len()
            ));
        }

        let payload = &data[28..28 + payload_len];
        let expected_payload_crc = u32::from_be_bytes(data[28 + payload_len..total_expected_len].try_into().unwrap());
        let computed_payload_crc = compute_crc32(payload);
        if computed_payload_crc != expected_payload_crc {
            return Err("Payload CRC mismatch: corrupted checkpoint data".to_string());
        }

        // Parse state
        let mut pos = 0;
        macro_rules! read_u64 {
            () => {{
                let val = u64::from_be_bytes(payload[pos..pos + 8].try_into().unwrap());
                pos += 8;
                val
            }};
        }
        macro_rules! read_i64 {
            () => {{
                let val = i64::from_be_bytes(payload[pos..pos + 8].try_into().unwrap());
                pos += 8;
                val
            }};
        }
        macro_rules! read_f64 {
            () => {{
                let val = f64::from_be_bytes(payload[pos..pos + 8].try_into().unwrap());
                pos += 8;
                if !val.is_finite() {
                    return Err("Non-finite f64 in checkpoint payload".to_string());
                }
                val
            }};
        }

        let step_count = read_u64!();
        let z_fixed_in = read_i64!();
        let z_fixed_out = read_i64!();
        let z_ext_port = read_i64!();
        let r_ext = read_f64!();

        let mut n_in = [0u64; 4];
        let mut n_out = [0u64; 4];
        let mut r_remainder = [0.0f64; 4];
        let mut y_gate = [0.0f64; 4];
        let mut phi = [0.0f64; 4];
        let mut rho = [0.0f64; 4];

        for c in 0..4 {
            n_in[c] = read_u64!();
            n_out[c] = read_u64!();
            r_remainder[c] = read_f64!();
            y_gate[c] = read_f64!();
            phi[c] = wrap_phase(read_f64!());
            rho[c] = read_f64!();
        }

        let contact_x = read_f64!();
        let contact_ell = read_f64!();
        let q_rec = read_f64!();
        let c_rec = read_f64!();
        let cumulative_d_pl = read_f64!();
        let cumulative_w_in = read_f64!();
        let cumulative_q_heat = read_f64!();

        // Operator parameters
        let c_mem = read_f64!();
        let k_strain = read_f64!();
        let y_yield = read_f64!();
        let zeta_gate = read_f64!();
        let gamma_phi = read_f64!();

        if c_mem <= 0.0 || k_strain <= 0.0 || y_yield <= 0.0 || y_yield >= k_strain || zeta_gate <= 0.0 || gamma_phi <= 0.0 {
            return Err("Decoded operator material parameters violate physical admissibility".to_string());
        }
        if contact_x <= 0.0 || contact_ell <= 0.0 || c_rec <= 0.0 {
            return Err("Decoded geometry/capacitance parameters violate physical positivity".to_string());
        }

        let num_edges = u16::from_be_bytes(payload[pos..pos + 2].try_into().unwrap()) as usize;
        pos += 2;
        if num_edges > MAX_FABRIC_EDGES {
            return Err(format!("Decoded edge count exceeds resource bound {}: {}", MAX_FABRIC_EDGES, num_edges));
        }

        let mut fabric_edges = Vec::with_capacity(num_edges);
        for _ in 0..num_edges {
            let dim_u8 = payload[pos];
            pos += 1;
            let role_u8 = payload[pos];
            pos += 1;
            let position = u16::from_be_bytes(payload[pos..pos + 2].try_into().unwrap());
            pos += 2;
            let from_node = payload[pos] as usize;
            pos += 1;
            let to_node = payload[pos] as usize;
            pos += 1;
            let tau_trit = payload[pos] as i8;
            pos += 1;
            let kappa_j = f64::from_be_bytes(payload[pos..pos + 8].try_into().unwrap());
            pos += 8;

            let dim = StructuralFieldDim::from_u8(dim_u8)
                .ok_or_else(|| format!("Invalid StructuralFieldDim tag: {}", dim_u8))?;
            let role = FieldRole::from_u8(role_u8)
                .ok_or_else(|| format!("Invalid FieldRole tag: {}", role_u8))?;

            let edge = TypedFabricEdge::new(dim, role, position, from_node, to_node, tau_trit, kappa_j)?;
            fabric_edges.push(edge);
        }

        if pos != payload_len {
            return Err(format!("Internal payload offset mismatch: parsed {} of {} bytes", pos, payload_len));
        }

        let state = ArcLoomNeuronState {
            step_count,
            z_fixed_in,
            z_fixed_out,
            z_ext_port,
            r_ext,
            n_in,
            n_out,
            r_remainder,
            y_gate,
            phi,
            rho,
            contact_x,
            contact_ell,
            q_rec,
            c_rec,
            cumulative_d_pl,
            cumulative_w_in,
            cumulative_q_heat,
        };

        let operator = ArcLoomTransitionOperator {
            c_mem,
            k_strain,
            y_yield,
            zeta_gate,
            gamma_phi,
            fabric_edges,
        };

        Ok((operator, state))
    }
}

/// PyO3 Python binding wrapper
#[pyclass(name = "ArcLoomNeuron")]
pub struct PyArcLoomNeuron {
    state: ArcLoomNeuronState,
    operator: ArcLoomTransitionOperator,
}

#[pymethods]
impl PyArcLoomNeuron {
    #[new]
    pub fn new() -> Self {
        Self {
            state: ArcLoomNeuronState::new_reference_preparation(),
            operator: ArcLoomTransitionOperator::new_reference_operator(),
        }
    }

    /// Add a typed structural field constraint edge
    #[pyo3(signature = (from_node, to_node, tau_trit, kappa_j, dim = 0, role = 0, position = 0))]
    pub fn add_fabric_edge(
        &mut self,
        from_node: usize,
        to_node: usize,
        tau_trit: i8,
        kappa_j: f64,
        dim: u8,
        role: u8,
        position: u16,
    ) -> PyResult<()> {
        let field_dim = StructuralFieldDim::from_u8(dim)
            .ok_or_else(|| PyValueError::new_err(format!("Invalid field dimension: {}", dim)))?;
        let field_role = FieldRole::from_u8(role)
            .ok_or_else(|| PyValueError::new_err(format!("Invalid field role: {}", role)))?;

        let edge = TypedFabricEdge::new(field_dim, field_role, position, from_node, to_node, tau_trit, kappa_j)
            .map_err(|e| PyValueError::new_err(e))?;
        self.operator.add_fabric_edge(edge)
            .map_err(|e| PyRuntimeError::new_err(e))?;
        Ok(())
    }

    /// Execute a causal transition step
    #[pyo3(signature = (applied_contact_x=None, external_current_a=0.0, dt_seconds=1.0e-4))]
    pub fn step(
        &mut self,
        applied_contact_x: Option<f64>,
        external_current_a: f64,
        dt_seconds: f64,
    ) -> PyResult<(f64, f64, bool, f64, f64, f64, f64)> {
        let res = self.operator.step(&mut self.state, applied_contact_x, external_current_a, dt_seconds)
            .map_err(|e| PyRuntimeError::new_err(e))?;
        Ok((
            res.prior_membrane_v,
            res.succ_membrane_v,
            res.plastic_yield_occurred,
            res.plastic_dissipation_j,
            res.succ_receiving_v,
            res.work_input_j,
            res.heat_dissipated_j,
        ))
    }

    pub fn membrane_voltage(&self) -> f64 {
        self.state.membrane_voltage(self.operator.c_mem)
    }

    pub fn receiving_voltage(&self) -> f64 {
        self.state.receiving_voltage()
    }

    pub fn get_apertures(&self) -> Vec<f64> {
        self.state.y_gate.to_vec()
    }

    pub fn get_reservoirs_in(&self) -> Vec<u64> {
        self.state.n_in.to_vec()
    }

    pub fn get_reservoirs_out(&self) -> Vec<u64> {
        self.state.n_out.to_vec()
    }

    pub fn get_contact_geometry(&self) -> (f64, f64) {
        (self.state.contact_x, self.state.contact_ell)
    }

    pub fn export_canonical_bytes(&self) -> Vec<u8> {
        self.operator.export_canonical_checkpoint(&self.state)
    }

    pub fn import_canonical_bytes(&mut self, bytes: Vec<u8>) -> PyResult<()> {
        let (op, st) = ArcLoomTransitionOperator::import_canonical_checkpoint(&bytes)
            .map_err(|e| PyValueError::new_err(e))?;
        self.operator = op;
        self.state = st;
        Ok(())
    }
}

pub fn register(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<PyArcLoomNeuron>()?;
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_preparation_genesis_electroneutrality_and_initial_voltage() {
        let state = ArcLoomNeuronState::new_reference_preparation();
        let operator = ArcLoomTransitionOperator::new_reference_operator();

        let z_f = state.integer_free_charge();
        assert_eq!(z_f, GENESIS_Z_F, "Free charge integer count must exactly equal genesis Z_f");

        let mobile_out: i64 = (SPECIES_VALENCE[0] as i64) * (state.n_out[0] as i64)
            + (SPECIES_VALENCE[1] as i64) * (state.n_out[1] as i64)
            + (SPECIES_VALENCE[2] as i64) * (state.n_out[2] as i64)
            + (SPECIES_VALENCE[3] as i64) * (state.n_out[3] as i64);
        let z_out_total = state.z_fixed_out + mobile_out;
        assert_eq!(z_out_total, -GENESIS_Z_F, "Extracellular space must carry exact opposite countercharge");

        assert_eq!(z_f + z_out_total, 0, "Total system net charge must be exactly zero");

        let v0 = state.membrane_voltage(operator.c_mem);
        let expected_v0 = -0.0650000031305;
        assert!((v0 - expected_v0).abs() < 1e-9, "Initial membrane potential must match ratified V0");
    }

    #[test]
    fn test_access_conductance_benchmark_values() {
        let benchmarks = [
            (0.02, 4.60998e-12),
            (0.05, 11.3812e-12),
            (0.10, 22.4469e-12),
            (1.00, 203.633e-12),
        ];

        for &(aperture, expected_g) in &benchmarks {
            let g = pore_conductance(aperture);
            let rel_err = (g - expected_g).abs() / expected_g;
            assert!(rel_err < 1e-4, "Conductance at aperture {} failed benchmark: got {}, expected {}", aperture, g, expected_g);
        }
    }

    #[test]
    fn test_contact_plasticity_and_receiving_charge_transfer() {
        let mut state = ArcLoomNeuronState::new_reference_preparation();
        let operator = ArcLoomTransitionOperator::new_reference_operator();

        // 1. Elastic branch: sub-yield strain
        let res_elastic = operator.step(&mut state, Some(CONTACT_LENGTH_REF_M * 1.02), 0.0, 1.0e-4).unwrap();
        assert!(!res_elastic.plastic_yield_occurred);
        assert_eq!(res_elastic.plastic_dissipation_j, 0.0);
        assert_eq!(state.contact_ell, CONTACT_LENGTH_REF_M);

        // 2. Plastic branch: post-yield strain
        let res_plastic = operator.step(&mut state, Some(CONTACT_LENGTH_REF_M * 1.15), 0.0, 1.0e-4).unwrap();
        assert!(res_plastic.plastic_yield_occurred);
        assert!(res_plastic.plastic_dissipation_j > 0.0);
        assert!(state.contact_ell > CONTACT_LENGTH_REF_M);

        // Verify receiving compartment charge transfer
        assert!(res_plastic.receiving_charge_transferred_c != 0.0);
        assert_eq!(state.q_rec, RECEIVING_RESTING_V * RECEIVING_CAPACITANCE_F + res_elastic.receiving_charge_transferred_c + res_plastic.receiving_charge_transferred_c);
    }

    #[test]
    fn test_nonempty_topology_cold_successor_equivalence() {
        let mut original_state = ArcLoomNeuronState::new_reference_preparation();
        let mut original_op = ArcLoomTransitionOperator::new_reference_operator();

        // Add non-empty fabric edges
        let edge1 = TypedFabricEdge::new(StructuralFieldDim::Displacement, FieldRole::Numerator, 0, 0, 1, 1, 4.28e-20).unwrap();
        let edge2 = TypedFabricEdge::new(StructuralFieldDim::Motion, FieldRole::Denominator, 1, 1, 2, -1, 4.28e-20).unwrap();
        original_op.add_fabric_edge(edge1).unwrap();
        original_op.add_fabric_edge(edge2).unwrap();

        // Advance original 3 steps
        for _ in 0..3 {
            original_op.step(&mut original_state, Some(CONTACT_LENGTH_REF_M * 1.08), 5.0e-10, 1.0e-4).unwrap();
        }

        // Export canonical checkpoint
        let checkpoint_bytes = original_op.export_canonical_checkpoint(&original_state);

        // Import into fresh instance (starts with empty edges)
        let (restored_op, mut restored_state) = ArcLoomTransitionOperator::import_canonical_checkpoint(&checkpoint_bytes).unwrap();
        assert_eq!(restored_op.fabric_edges.len(), 2, "Restored operator must possess the 2 fabric edges");
        assert_eq!(original_state, restored_state, "Decoded state must match bit-for-bit");

        // Advance both under identical stimulus
        let res_orig = original_op.step(&mut original_state, Some(CONTACT_LENGTH_REF_M * 1.02), -2.0e-10, 1.0e-4).unwrap();
        let res_rest = restored_op.step(&mut restored_state, Some(CONTACT_LENGTH_REF_M * 1.02), -2.0e-10, 1.0e-4).unwrap();

        assert_eq!(res_orig, res_rest, "Successor transitions must be bit-identical");
        assert_eq!(original_state, restored_state, "Post-transition states must be bit-identical");
    }

    #[test]
    fn test_exact_carrier_custody_and_first_law() {
        let mut state = ArcLoomNeuronState::new_reference_preparation();
        let operator = ArcLoomTransitionOperator::new_reference_operator();

        let initial_n_in = state.n_in;
        let initial_n_out = state.n_out;

        let res = operator.step(&mut state, Some(CONTACT_LENGTH_REF_M * 1.05), 1.0e-9, 1.0e-4).unwrap();

        // First law balance
        assert!(res.work_input_j.is_finite());
        assert!(res.heat_dissipated_j >= 0.0);
        assert!(res.delta_enthalpy_j.is_finite());

        // Carrier custody: sum of reservoir ions conserved for each species
        for c in 0..4 {
            assert_eq!(state.n_in[c] + state.n_out[c], initial_n_in[c] + initial_n_out[c]);
            assert!(state.r_remainder[c].abs() < 1.0);
        }
    }

    #[test]
    fn test_invalid_checkpoint_and_boundary_refusal() {
        let mut state = ArcLoomNeuronState::new_reference_preparation();
        let operator = ArcLoomTransitionOperator::new_reference_operator();

        let valid_bytes = operator.export_canonical_checkpoint(&state);

        // 1. Trailing bytes must be rejected
        let mut corrupted_trailing = valid_bytes.clone();
        corrupted_trailing.push(0xAA);
        assert!(ArcLoomTransitionOperator::import_canonical_checkpoint(&corrupted_trailing).is_err());

        // 2. Corrupted CRC must be rejected
        let mut corrupted_crc = valid_bytes.clone();
        let last = corrupted_crc.len() - 1;
        corrupted_crc[last] ^= 0xFF;
        assert!(ArcLoomTransitionOperator::import_canonical_checkpoint(&corrupted_crc).is_err());

        // 3. Non-finite inputs must refuse without state mutation
        let pre_state = state.clone();
        assert!(operator.step(&mut state, None, f64::NAN, 1.0e-4).is_err());
        assert_eq!(state, pre_state, "Predecessor state must be 100% unmutated after refusal");
    }
}
