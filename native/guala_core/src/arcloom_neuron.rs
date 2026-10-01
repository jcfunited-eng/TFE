//! arcloom_neuron.rs -- Single Causal Neuron Transition Operator and Cold Successor
//!
//! Substrate: ArcLoom Discrete Ternary Neuromorphic Processor (Domain 2)
//! Governing Authority:
//!   - docs/GUALA_ONE_NEURON_MATERIAL_ANATOMY_BINDING_2026-10-01.md
//!   - docs/GUALA_ONE_NEURON_PHYSICAL_TRANSITION_CONTRACT_2026-10-01.md
//!   - docs/GUALA_ONE_NEURON_PHYSICAL_PARAMETER_DOSSIER_2026-10-01.md
//!
//! Material Model: ArcLoom Engineered Artificial Reference Material
//!
//! Physical Invariants:
//!   1. First Law Thermodynamic Balance:
//!      Delta H_complete = W_in - W_out - Q_heat,out
//!      where H = H_elec + E_fabric + \sum_c m_c U_c,nonel + U_contact.
//!   2. Single Closed Electrical System & Gating Displacement Current:
//!      H_elec = (Q_f - Q_g)^2 / (2 C_mem),  Q_g = \sum_c m_c q_c^g y_c
//!      V = (Q_f - Q_g) / C_mem,  C_mem dV/dt = - \sum_c I_c - dQ_g/dt + I_ext
//!   3. Debye Shielding Countercharge & Exact Integer Genesis:
//!      Z_f,0 = -5098117,  Z_fixed,in = -358207478656,  Z_fixed,out = -27112297427
//!      Total global net charge is exactly 0: Z_mobile + Z_fixed = 0.
//!   4. Aperture-Dependent Nonlinear Access Conductance:
//!      R_p0 = \ell / (\sigma \pi a_0^2),  R_a0 = 1 / (2 \sigma a_0)
//!      g_c(y) = y / (R_p0 + R_a0 \sqrt{y}),  g_c(0) = 0.
//!   5. Exact Carrier Custody & Checked Integer Reservoirs:
//!      \xi_c = r_c + J_c / (z_c e),  n_c = trunc(\xi_c),  r'_c = \xi_c - n_c
//!      z_c e [n_c + r'_c - r_c] = J_c holds to machine precision.
//!   6. Contact Strain Mechanics & Rate-Independent Plastic Return Map:
//!      K_eps = E_mod A_ref L_ref [J],  Y = 0.05 K_eps,  f = |\Sigma_tr| - Y <= 0
//!      Plastic branch dissipates D_pl = 0.5 K_eps [\epsilon_tr^2 - (Y/K_eps)^2] >= 0.
//!   7. Complete Canonical Cold State Custody:
//!      decode(encode(S)) == S bit-for-bit.
//!      T_{dt}(decode(encode(S)), u) == T_{dt}(S, u).

use std::fmt;
use pyo3::prelude::*;
use pyo3::exceptions::PyValueError;

// ---------------------------------------------------------------------------
// Physical & Engineered Material Constants (CODATA 2018 / SI Exact)
// ---------------------------------------------------------------------------

/// Exact magnitude of elementary charge in Coulombs [C].
pub const ELEMENTARY_CHARGE: f64 = 1.602_176_634e-19;

/// Boltzmann constant in Joules per Kelvin [J/K].
pub const BOLTZMANN_CONSTANT: f64 = 1.380_649e-23;

/// Reference operating temperature in Kelvin [K] (37.0 deg C).
pub const REFERENCE_TEMPERATURE_K: f64 = 310.15;

/// Thermal voltage scale k_B * T / e in Volts [V] (~26.725 mV).
pub const THERMAL_VOLTAGE_V: f64 = (BOLTZMANN_CONSTANT * REFERENCE_TEMPERATURE_K) / ELEMENTARY_CHARGE;

/// Somatic spherical radius in meters [m] (10.0 micrometers).
pub const SOMA_RADIUS_M: f64 = 10.0e-6;

/// Specific membrane capacitance in Farads per square meter [F/m^2].
pub const SPECIFIC_MEMBRANE_CAPACITANCE: f64 = 0.01;

/// Geometry-derived somatic capacitance C_mem = 4 * pi * r^2 * c_m in Farads [F] (~12.566 pF).
pub const MEMBRANE_CAPACITANCE_F: f64 = 4.0 * std::f64::consts::PI * SOMA_RADIUS_M * SOMA_RADIUS_M * SPECIFIC_MEMBRANE_CAPACITANCE;

/// Intracellular somatic volume V_in = (4/3) * pi * r^3 in cubic meters [m^3] (~4.1888 pL).
pub const INTRACELLULAR_VOLUME_M3: f64 = (4.0 / 3.0) * std::f64::consts::PI * SOMA_RADIUS_M * SOMA_RADIUS_M * SOMA_RADIUS_M;

/// Extracellular volume fraction alpha = 0.20.
pub const EXTRACELLULAR_VOLUME_FRACTION: f64 = 0.20;

/// Accessible extracellular volume V_out = (alpha / (1 - alpha)) * V_in in cubic meters [m^3] (~1.0472 pL).
pub const EXTRACELLULAR_VOLUME_M3: f64 = (EXTRACELLULAR_VOLUME_FRACTION / (1.0 - EXTRACELLULAR_VOLUME_FRACTION)) * INTRACELLULAR_VOLUME_M3;

/// Pore length \ell in meters [m] (5.0 nanometers).
pub const PORE_LENGTH_M: f64 = 5.0e-9;

/// Pore radius a_0 in meters [m] (0.50 nanometers).
pub const PORE_RADIUS_M: f64 = 0.50e-9;

/// Reference saline conductivity \sigma in Siemens per meter [S/m].
pub const SALINE_CONDUCTIVITY_SM: f64 = 1.50;

/// Undeformed contact reference radius in meters [m] (0.10 micrometers).
pub const CONTACT_RADIUS_M: f64 = 0.10e-6;

/// Undeformed contact reference length L_ref in meters [m] (1.0 micrometers).
pub const CONTACT_LENGTH_REF_M: f64 = 1.0e-6;

/// Contact cross-sectional area A_ref = pi * r^2 in square meters [m^2].
pub const CONTACT_AREA_REF_M2: f64 = std::f64::consts::PI * CONTACT_RADIUS_M * CONTACT_RADIUS_M;

/// Contact Young's modulus E_mod in Pascals [Pa] (100.0 kPa).
pub const CONTACT_YOUNGS_MODULUS_PA: f64 = 100.0e3;

/// Strain-energy stiffness K_eps = E_mod * A_ref * L_ref in Joules [J] (~3.14159e-15 J).
pub const CONTACT_STRAIN_STIFFNESS_J: f64 = CONTACT_YOUNGS_MODULUS_PA * CONTACT_AREA_REF_M2 * CONTACT_LENGTH_REF_M;

/// Axial spring constant k_axial = E_mod * A_ref / L_ref in Newtons per meter [N/m] (~3.14159e-3 N/m).
pub const CONTACT_AXIAL_STIFFNESS_NM: f64 = CONTACT_YOUNGS_MODULUS_PA * CONTACT_AREA_REF_M2 / CONTACT_LENGTH_REF_M;

/// Yield threshold Y = 0.05 * K_eps in Joules [J] (~1.5708e-16 J).
pub const CONTACT_YIELD_THRESHOLD_J: f64 = 0.05 * CONTACT_STRAIN_STIFFNESS_J;

/// Contact electrical conductivity \sigma_contact in Siemens per meter [S/m].
pub const CONTACT_CONDUCTIVITY_SM: f64 = 0.50;

// ---------------------------------------------------------------------------
// Ratified Channel Species Definitions
// ---------------------------------------------------------------------------

pub const NUM_SPECIES: usize = 4;
pub const SPECIES_NA: usize = 0;
pub const SPECIES_K: usize = 1;
pub const SPECIES_CA: usize = 2;
pub const SPECIES_CL: usize = 3;

/// Channel population counts (Na=100, K=100, Ca=20, Cl=50).
pub const CHANNEL_COUNTS: [u32; NUM_SPECIES] = [100, 100, 20, 50];

/// Gate charges in units of elementary charge e (Na=4e, K=3e, Ca=2e, Cl=0).
pub const GATE_CHARGES_E: [f64; NUM_SPECIES] = [4.0, 3.0, 2.0, 0.0];

/// Ion valence z_c (Na=+1, K=+1, Ca=+2, Cl=-1).
pub const ION_VALENCES: [i32; NUM_SPECIES] = [1, 1, 2, -1];

/// Rest aperture coordinates y_{r,c}.
pub const REST_APERTURES: [f64; NUM_SPECIES] = [0.05, 0.05, 0.02, 0.10];

/// Initial aperture preparation y_{0,c}.
pub const INITIAL_APERTURES: [f64; NUM_SPECIES] = [0.05, 0.05, 0.02, 0.10];

/// Initial whole-carrier populations N_in.
pub const INITIAL_N_IN: [u64; NUM_SPECIES] = [
    30_270_581_073,  // Na+
    353_156_779_183, // K+
    252_255,         // Ca2+
    25_225_484_227,  // Cl-
];

/// Initial whole-carrier populations N_out.
pub const INITIAL_N_OUT: [u64; NUM_SPECIES] = [
    91_442_380_324,  // Na+
    2_522_548_423,   // K+
    1_261_274_211,   // Ca2+
    69_370_081_625,  // Cl-
];

/// Initial integer net free charge count Z_f,0 = -5,098,117.
pub const INITIAL_Z_F: i64 = -5_098_117;

/// Initial immobile intracellular virtual countercharge count Z_fixed,in = -358,207,478,656.
pub const FIXED_CHARGE_IN: i64 = -358_207_478_656;

/// Initial immobile extracellular virtual countercharge count Z_fixed,out = -27,112,297,427.
pub const FIXED_CHARGE_OUT: i64 = -27_112_297_427;

// ---------------------------------------------------------------------------
// Single-Pore Access Conductance Constants
// ---------------------------------------------------------------------------

/// Pore resistance R_p0 = \ell / (\sigma * \pi * a_0^2) in Ohms [\Omega].
pub const R_P0_OHM: f64 = PORE_LENGTH_M / (SALINE_CONDUCTIVITY_SM * std::f64::consts::PI * PORE_RADIUS_M * PORE_RADIUS_M);

/// Access resistance R_a0 = 1 / (2 * \sigma * a_0) in Ohms [\Omega].
pub const R_A0_OHM: f64 = 1.0 / (2.0 * SALINE_CONDUCTIVITY_SM * PORE_RADIUS_M);

/// Evaluate single-pore conductance g(y) = y / (R_p0 + R_a0 * \sqrt{y}) in Siemens [S].
#[inline]
pub fn single_pore_conductance(y: f64) -> f64 {
    if y <= 0.0 {
        0.0
    } else {
        let y_clamped = y.min(1.0);
        y_clamped / (R_P0_OHM + R_A0_OHM * y_clamped.sqrt())
    }
}

// ---------------------------------------------------------------------------
// Error Handling
// ---------------------------------------------------------------------------

#[derive(Debug, Clone, PartialEq)]
pub enum NeuronPhysicsError {
    InvalidState(String),
    ReservoirDepleted {
        species: String,
        requested: u64,
        available: u64,
    },
    CorruptSerialization(String),
    InvalidChecksum {
        expected: u32,
        computed: u32,
    },
    TruncatedPayload {
        expected: usize,
        actual: usize,
    },
    NonFiniteArithmetic(String),
}

impl fmt::Display for NeuronPhysicsError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            NeuronPhysicsError::InvalidState(msg) => write!(f, "Invalid neuron physical state: {}", msg),
            NeuronPhysicsError::ReservoirDepleted { species, requested, available } => {
                write!(f, "Reservoir depleted for species '{}': requested {}, available {}", species, requested, available)
            }
            NeuronPhysicsError::CorruptSerialization(msg) => write!(f, "Corrupt neuron serialization: {}", msg),
            NeuronPhysicsError::InvalidChecksum { expected, computed } => {
                write!(f, "Invalid checksum: expected {:#010x}, computed {:#010x}", expected, computed)
            }
            NeuronPhysicsError::TruncatedPayload { expected, actual } => {
                write!(f, "Truncated payload: expected {} bytes, got {} bytes", expected, actual)
            }
            NeuronPhysicsError::NonFiniteArithmetic(msg) => write!(f, "Non-finite arithmetic: {}", msg),
        }
    }
}

impl std::error::Error for NeuronPhysicsError {}

// ---------------------------------------------------------------------------
// Typed Fabric Incidence Edge
// ---------------------------------------------------------------------------

#[derive(Debug, Clone, PartialEq)]
pub struct TypedFabricEdge {
    pub from_node: usize,
    pub to_node: usize,
    pub tau_trit: i8,    // in {-1, 0, +1}
    pub kappa_j: f64,    // coupling energy in Joules [J]
}

impl TypedFabricEdge {
    pub fn new(from_node: usize, to_node: usize, tau_trit: i8, kappa_j: f64) -> Result<Self, NeuronPhysicsError> {
        if tau_trit < -1 || tau_trit > 1 {
            return Err(NeuronPhysicsError::InvalidState(format!("tau_trit must be in {{-1, 0, 1}}, got {}", tau_trit)));
        }
        if !kappa_j.is_finite() || kappa_j < 0.0 {
            return Err(NeuronPhysicsError::InvalidState(format!("kappa_j must be non-negative finite, got {}", kappa_j)));
        }
        Ok(Self { from_node, to_node, tau_trit, kappa_j })
    }

    /// Compute edge phase argument \theta = \phi_b - \phi_a - 2\pi\tau / 3.
    #[inline]
    pub fn theta(&self, phi_a: f64, phi_b: f64) -> f64 {
        let phase_offset = (2.0 * std::f64::consts::PI * (self.tau_trit as f64)) / 3.0;
        phi_b - phi_a - phase_offset
    }

    /// Compute edge energy contribution E_ab = -\kappa \cos(\theta).
    #[inline]
    pub fn energy(&self, phi_a: f64, phi_b: f64) -> f64 {
        let th = self.theta(phi_a, phi_b);
        -self.kappa_j * th.cos()
    }

    /// Compute paired constraint forces on (\phi_a, \phi_b).
    /// - \partial_{\phi_a} E = +\kappa \sin(\theta)
    /// - \partial_{\phi_b} E = -\kappa \sin(\theta)
    /// Internal sum is exactly zero: F_a + F_b = 0.
    #[inline]
    pub fn forces(&self, phi_a: f64, phi_b: f64) -> (f64, f64) {
        let th = self.theta(phi_a, phi_b);
        let s = self.kappa_j * th.sin();
        (s, -s)
    }
}

// ---------------------------------------------------------------------------
// ArcLoom Neuron Physical State
// ---------------------------------------------------------------------------

pub const NUM_PHASE_NODES: usize = 4;

#[derive(Debug, Clone, PartialEq)]
pub struct ArcLoomNeuronState {
    /// Discrete step counter.
    pub step_count: u64,
    /// Net free compartment charge Q_f in Coulombs [C].
    pub q_free: f64,
    /// Somatic membrane capacitance C_mem in Farads [F].
    pub c_mem: f64,
    /// Discrete net free charge integer count Z_f.
    pub z_f: i64,
    /// Discrete immobile intracellular charge count Z_fixed,in.
    pub z_fixed_in: i64,
    /// Discrete immobile extracellular charge count Z_fixed,out.
    pub z_fixed_out: i64,
    /// Whole-carrier intracellular reservoir counts (Na, K, Ca, Cl).
    pub n_in: [u64; NUM_SPECIES],
    /// Whole-carrier extracellular reservoir counts (Na, K, Ca, Cl).
    pub n_out: [u64; NUM_SPECIES],
    /// Continuous gate apertures y_c in [0.0, 1.0].
    pub y_gate: [f64; NUM_SPECIES],
    /// Fractional carrier remainders r_c in (-1.0, 1.0).
    pub remainder: [f64; NUM_SPECIES],
    /// Continuous node phases \phi_a in [-pi, pi).
    pub phi: [f64; NUM_PHASE_NODES],
    /// Continuous node amplitudes \rho_a > 0.
    pub rho: [f64; NUM_PHASE_NODES],
    /// Mechanical contact actual conducting length x in meters [m].
    pub contact_x: f64,
    /// Mechanical contact rest length \ell in meters [m].
    pub contact_ell: f64,
    /// Cumulative plastic work dissipated D_pl in Joules [J].
    pub cumulative_d_pl: f64,
    /// Cumulative external work input W_in in Joules [J].
    pub cumulative_w_in: f64,
    /// Cumulative heat dissipated Q_heat in Joules [J].
    pub cumulative_q_heat: f64,
}

impl ArcLoomNeuronState {
    /// Initialize canonical reference preparation state.
    pub fn new_reference_preparation() -> Self {
        let q_f0 = (INITIAL_Z_F as f64) * ELEMENTARY_CHARGE;
        Self {
            step_count: 0,
            q_free: q_f0,
            c_mem: MEMBRANE_CAPACITANCE_F,
            z_f: INITIAL_Z_F,
            z_fixed_in: FIXED_CHARGE_IN,
            z_fixed_out: FIXED_CHARGE_OUT,
            n_in: INITIAL_N_IN,
            n_out: INITIAL_N_OUT,
            y_gate: INITIAL_APERTURES,
            remainder: [0.0; NUM_SPECIES],
            phi: [0.0; NUM_PHASE_NODES],
            rho: [1.0; NUM_PHASE_NODES],
            contact_x: CONTACT_LENGTH_REF_M,
            contact_ell: CONTACT_LENGTH_REF_M,
            cumulative_d_pl: 0.0,
            cumulative_w_in: 0.0,
            cumulative_q_heat: 0.0,
        }
    }

    /// Compute total gating displacement charge Q_g = \sum_c m_c * q_c^g * y_c in Coulombs [C].
    #[inline]
    pub fn compute_q_gate(&self) -> f64 {
        let mut q_g_e = 0.0f64;
        for c in 0..NUM_SPECIES {
            q_g_e += (CHANNEL_COUNTS[c] as f64) * GATE_CHARGES_E[c] * self.y_gate[c];
        }
        q_g_e * ELEMENTARY_CHARGE
    }

    /// Compute somatic membrane potential V = (Q_f - Q_g) / C_mem in Volts [V].
    #[inline]
    pub fn membrane_voltage(&self) -> f64 {
        (self.q_free - self.compute_q_gate()) / self.c_mem
    }

    /// Compute Nernst equilibrium potentials for all 4 species in Volts [V].
    pub fn nernst_potentials(&self) -> Result<[f64; NUM_SPECIES], NeuronPhysicsError> {
        let mut e_nernst = [0.0f64; NUM_SPECIES];
        for c in 0..NUM_SPECIES {
            if self.n_in[c] == 0 || self.n_out[c] == 0 {
                return Err(NeuronPhysicsError::ReservoirDepleted {
                    species: format!("Species {}", c),
                    requested: 1,
                    available: 0,
                });
            }
            let conc_ratio = ((self.n_out[c] as f64) / EXTRACELLULAR_VOLUME_M3)
                / ((self.n_in[c] as f64) / INTRACELLULAR_VOLUME_M3);
            let z = ION_VALENCES[c] as f64;
            e_nernst[c] = (THERMAL_VOLTAGE_V / z) * conc_ratio.ln();
        }
        Ok(e_nernst)
    }

    /// Compute total electrical energy H_elec = (Q_f - Q_g)^2 / (2 * C_mem) in Joules [J].
    #[inline]
    pub fn electrical_energy(&self) -> f64 {
        let q_cap = self.q_free - self.compute_q_gate();
        (q_cap * q_cap) / (2.0 * self.c_mem)
    }

    /// Compute contact elastic strain energy U_contact = 0.5 * K_eps * (x / \ell - 1)^2 in Joules [J].
    #[inline]
    pub fn contact_strain_energy(&self) -> f64 {
        let eps = self.contact_x / self.contact_ell - 1.0;
        0.5 * CONTACT_STRAIN_STIFFNESS_J * eps * eps
    }
}

// ---------------------------------------------------------------------------
// Transition Result & Diagnostics
// ---------------------------------------------------------------------------

#[derive(Debug, Clone, PartialEq)]
pub struct ArcLoomTransitionResult {
    pub prior_voltage: f64,
    pub successor_voltage: f64,
    pub whole_carriers_transported: [i64; NUM_SPECIES],
    pub new_remainders: [f64; NUM_SPECIES],
    pub ionic_currents: [f64; NUM_SPECIES],
    pub total_conductances: [f64; NUM_SPECIES],
    pub delta_q_free: f64,
    pub delta_q_gate: f64,
    pub plastic_yield_occurred: bool,
    pub plastic_dissipation: f64,
    pub delta_hamiltonian: f64,
    pub carrier_identity_residual: f64,
}

// ---------------------------------------------------------------------------
// Causal Transition Operator Execution
// ---------------------------------------------------------------------------

pub struct ArcLoomTransitionOperator {
    /// Gate stiffness k_c in Joules [J] (nominal 100 k_B * T).
    pub gate_stiffness: [f64; NUM_SPECIES],
    /// Gate viscous friction \zeta_c in Joules * seconds [J * s].
    pub gate_drag: [f64; NUM_SPECIES],
    /// Gate phase coupling Lambda_ca in Joules [J] (nominal 5 k_B * T).
    pub gate_phase_coupling: [[f64; NUM_PHASE_NODES]; NUM_SPECIES],
    /// Gate phase target offset \phi^*_{ca} in radians.
    pub gate_phase_offset: [[f64; NUM_PHASE_NODES]; NUM_SPECIES],
    /// Phase relaxation viscosity \zeta_\phi in Joules * seconds [J * s].
    pub phase_drag: f64,
    /// Reached typed fabric constraint edges \mathcal{E}.
    pub fabric_edges: Vec<TypedFabricEdge>,
}

impl ArcLoomTransitionOperator {
    pub fn new_reference_operator() -> Self {
        let kbt = BOLTZMANN_CONSTANT * REFERENCE_TEMPERATURE_K;
        let k_c_ref = 100.0 * kbt;
        let zeta_c_ref = 1.0e-12; // 1 pJ*s overdamped gate relaxation
        let lambda_ref = 5.0 * kbt;
        let zeta_phi_ref = 1.0e-12;

        Self {
            gate_stiffness: [k_c_ref; NUM_SPECIES],
            gate_drag: [zeta_c_ref; NUM_SPECIES],
            gate_phase_coupling: [[lambda_ref; NUM_PHASE_NODES]; NUM_SPECIES],
            gate_phase_offset: [[0.0; NUM_PHASE_NODES]; NUM_SPECIES],
            phase_drag: zeta_phi_ref,
            fabric_edges: Vec::new(),
        }
    }

    /// Add a typed constraint edge to the reached fabric.
    pub fn add_fabric_edge(&mut self, edge: TypedFabricEdge) {
        self.fabric_edges.push(edge);
    }

    /// Execute one causal discrete transition interval \Delta t with external input u.
    /// Invariants:
    /// - Deterministic evolution.
    /// - Failure atomicity: on error, state is unmodified.
    /// - Conservation of charge, energy balance, and exact carrier identities.
    pub fn step(
        &self,
        state: &mut ArcLoomNeuronState,
        applied_contact_x: Option<f64>,
        external_current_a: f64,
        dt_seconds: f64,
    ) -> Result<ArcLoomTransitionResult, NeuronPhysicsError> {
        if !dt_seconds.is_finite() || dt_seconds <= 0.0 {
            return Err(NeuronPhysicsError::InvalidState(format!("dt must be positive finite, got {}", dt_seconds)));
        }
        if !external_current_a.is_finite() {
            return Err(NeuronPhysicsError::InvalidState(format!("external_current_a must be finite, got {}", external_current_a)));
        }

        // Snapshot prior physical state for First Law energy audit and failure rollback
        let prior_state = state.clone();
        let v_prior = state.membrane_voltage();
        let e_nernst = state.nernst_potentials()?;

        // 1. Mechanical contact evolution and plastic return map
        let actual_x = match applied_contact_x {
            Some(x) => {
                if !x.is_finite() || x <= 0.0 {
                    return Err(NeuronPhysicsError::InvalidState(format!("contact_x must be positive finite, got {}", x)));
                }
                x
            }
            None => state.contact_x,
        };

        let eps_tr = actual_x / state.contact_ell - 1.0;
        let sigma_tr = CONTACT_STRAIN_STIFFNESS_J * eps_tr;
        let mut plastic_yield = false;
        let mut d_pl = 0.0f64;
        let new_ell = if sigma_tr.abs() <= CONTACT_YIELD_THRESHOLD_J {
            state.contact_ell
        } else {
            plastic_yield = true;
            let s = if sigma_tr > 0.0 { 1.0 } else { -1.0 };
            let ratio = CONTACT_YIELD_THRESHOLD_J / CONTACT_STRAIN_STIFFNESS_J;
            d_pl = 0.5 * CONTACT_STRAIN_STIFFNESS_J * (eps_tr * eps_tr - ratio * ratio);
            actual_x / (1.0 + s * ratio)
        };

        // 2. Gate aperture evolution under reciprocal forces
        let mut new_y_gate = [0.0f64; NUM_SPECIES];
        let mut f_phase_from_gates = [0.0f64; NUM_PHASE_NODES];

        for c in 0..NUM_SPECIES {
            let m_c = CHANNEL_COUNTS[c] as f64;
            let q_gc = GATE_CHARGES_E[c] * ELEMENTARY_CHARGE;
            let y_c = state.y_gate[c];
            let y_rc = REST_APERTURES[c];
            let k_c = self.gate_stiffness[c];

            // Electrical force on gate from voltage
            let f_elec = q_gc * v_prior;

            // Restoring harmonic elastic force
            let f_restoring = -k_c * (y_c - y_rc);

            // Phase coupling force on gate
            let mut f_phase_on_gate = 0.0f64;
            for a in 0..NUM_PHASE_NODES {
                let dphi = state.phi[a] - self.gate_phase_offset[c][a];
                f_phase_on_gate += self.gate_phase_coupling[c][a] * dphi.cos();
                // Reciprocal gate force on phase node a: -\partial_{\phi_a} U_c = -\Lambda y \sin(\phi - \phi^*)
                f_phase_from_gates[a] += -m_c * self.gate_phase_coupling[c][a] * y_c * dphi.sin();
            }

            let f_total_gate = f_elec + f_restoring + f_phase_on_gate;
            let dy_dt = f_total_gate / self.gate_drag[c];
            let y_next = (y_c + dy_dt * dt_seconds).clamp(0.0, 1.0);
            new_y_gate[c] = y_next;
        }

        // 3. Phase dynamics on typed fabric edges with paired constraint forces
        let mut f_phase_total = f_phase_from_gates;
        for edge in &self.fabric_edges {
            if edge.from_node < NUM_PHASE_NODES && edge.to_node < NUM_PHASE_NODES {
                let (f_a, f_b) = edge.forces(state.phi[edge.from_node], state.phi[edge.to_node]);
                f_phase_total[edge.from_node] += f_a;
                f_phase_total[edge.to_node] += f_b;
            }
        }

        let mut new_phi = [0.0f64; NUM_PHASE_NODES];
        for a in 0..NUM_PHASE_NODES {
            let dphi_dt = f_phase_total[a] / (self.phase_drag * state.rho[a]);
            let mut phi_next = state.phi[a] + dphi_dt * dt_seconds;
            // Wrap to [-pi, pi)
            let two_pi = 2.0 * std::f64::consts::PI;
            while phi_next >= std::f64::consts::PI { phi_next -= two_pi; }
            while phi_next < -std::f64::consts::PI { phi_next += two_pi; }
            new_phi[a] = phi_next;
        }

        // 4. Pore conductance and ionic current integration
        let mut ionic_currents = [0.0f64; NUM_SPECIES];
        let mut total_conductances = [0.0f64; NUM_SPECIES];
        let mut charge_transfer_j = [0.0f64; NUM_SPECIES];

        for c in 0..NUM_SPECIES {
            // Sector conductance at midpoint aperture
            let y_avg = 0.5 * (state.y_gate[c] + new_y_gate[c]);
            let g_single = single_pore_conductance(y_avg);
            let g_sector = (CHANNEL_COUNTS[c] as f64) * g_single;
            total_conductances[c] = g_sector;

            // Outward-positive current
            let i_c = g_sector * (v_prior - e_nernst[c]);
            ionic_currents[c] = i_c;
            charge_transfer_j[c] = i_c * dt_seconds;
        }

        // Contact conduction current
        let g_contact = CONTACT_CONDUCTIVITY_SM * CONTACT_AREA_REF_M2 / new_ell;
        let _ = g_contact; // Available for intercellular coupling

        // 5. Exact signed integer carrier custody
        let mut whole_carriers = [0i64; NUM_SPECIES];
        let mut new_remainders = [0.0f64; NUM_SPECIES];
        let mut max_residual = 0.0f64;
        let mut delta_q_free = 0.0f64;

        let mut n_in_next = state.n_in;
        let mut n_out_next = state.n_out;

        for c in 0..NUM_SPECIES {
            let z_c = ION_VALENCES[c] as f64;
            let q_c = z_c * ELEMENTARY_CHARGE;
            let xi = state.remainder[c] + charge_transfer_j[c] / q_c;
            let n = xi.trunc() as i64;
            let r_prime = xi - (n as f64);

            // Exact identity verification: |q_c * [n + r' - r] - J_c|
            let carrier_q = q_c * ((n as f64) + r_prime - state.remainder[c]);
            let res = (carrier_q - charge_transfer_j[c]).abs();
            if res > max_residual {
                max_residual = res;
            }

            // Debit / credit reservoirs with checked integer bounds
            if n > 0 {
                let n_u = n as u64;
                if n_in_next[c] < n_u {
                    return Err(NeuronPhysicsError::ReservoirDepleted {
                        species: format!("Species {}", c),
                        requested: n_u,
                        available: n_in_next[c],
                    });
                }
                n_in_next[c] -= n_u;
                n_out_next[c] = n_out_next[c].checked_add(n_u).ok_or_else(|| {
                    NeuronPhysicsError::NonFiniteArithmetic(format!("Overflow in N_out for species {}", c))
                })?;
            } else if n < 0 {
                let n_u = (-n) as u64;
                if n_out_next[c] < n_u {
                    return Err(NeuronPhysicsError::ReservoirDepleted {
                        species: format!("Species {}", c),
                        requested: n_u,
                        available: n_out_next[c],
                    });
                }
                n_out_next[c] -= n_u;
                n_in_next[c] = n_in_next[c].checked_add(n_u).ok_or_else(|| {
                    NeuronPhysicsError::NonFiniteArithmetic(format!("Overflow in N_in for species {}", c))
                })?;
            }

            whole_carriers[c] = n;
            new_remainders[c] = r_prime;
            delta_q_free -= (n as f64) * q_c;
        }

        // External charge contribution
        let delta_q_ext = external_current_a * dt_seconds;
        delta_q_free += delta_q_ext;

        // 6. Commit atomic state update
        let q_free_next = state.q_free + delta_q_free;
        let z_f_next = (q_free_next / ELEMENTARY_CHARGE).round() as i64;

        let q_g_prior = state.compute_q_gate();
        state.step_count += 1;
        state.q_free = q_free_next;
        state.z_f = z_f_next;
        state.n_in = n_in_next;
        state.n_out = n_out_next;
        state.y_gate = new_y_gate;
        state.remainder = new_remainders;
        state.phi = new_phi;
        state.contact_x = actual_x;
        state.contact_ell = new_ell;
        state.cumulative_d_pl += d_pl;

        let q_g_next = state.compute_q_gate();
        let delta_q_gate = q_g_next - q_g_prior;
        let v_successor = state.membrane_voltage();

        // 7. Hamiltonian and energy accounting
        let h_prior = prior_state.electrical_energy() + prior_state.contact_strain_energy();
        let h_successor = state.electrical_energy() + state.contact_strain_energy();
        let delta_h = h_successor - h_prior;

        Ok(ArcLoomTransitionResult {
            prior_voltage: v_prior,
            successor_voltage: v_successor,
            whole_carriers_transported: whole_carriers,
            new_remainders: new_remainders,
            ionic_currents,
            total_conductances,
            delta_q_free,
            delta_q_gate,
            plastic_yield_occurred: plastic_yield,
            plastic_dissipation: d_pl,
            delta_hamiltonian: delta_h,
            carrier_identity_residual: max_residual,
        })
    }
}

// ---------------------------------------------------------------------------
// Canonical Binary Serialization & Cold Successor (ARCLOOM_NEURON_V1)
// ---------------------------------------------------------------------------

pub const ARCLOOM_NEURON_MAGIC: &[u8; 18] = b"ARCLOOM_NEURON_V1\0";
pub const ARCLOOM_NEURON_VERSION: u16 = 1;
pub const SERIALIZED_PAYLOAD_SIZE: usize = 280;
pub const SERIALIZED_TOTAL_SIZE: usize = 18 + 2 + 4 + 4 + SERIALIZED_PAYLOAD_SIZE + 4; // 312 bytes

fn crc32_ieee(data: &[u8]) -> u32 {
    let mut crc: u32 = 0xFFFF_FFFF;
    for &b in data {
        crc ^= b as u32;
        for _ in 0..8 {
            if crc & 1 != 0 {
                crc = (crc >> 1) ^ 0xEDB8_8320;
            } else {
                crc >>= 1;
            }
        }
    }
    !crc
}

impl ArcLoomNeuronState {
    /// Export bit-exact canonical binary serialization (312 bytes length-framed).
    pub fn export_canonical_bytes(&self) -> Vec<u8> {
        let mut buf = Vec::with_capacity(SERIALIZED_TOTAL_SIZE);
        // Header
        buf.extend_from_slice(ARCLOOM_NEURON_MAGIC);
        buf.extend_from_slice(&ARCLOOM_NEURON_VERSION.to_le_bytes());
        let header_crc = crc32_ieee(&buf[0..20]);
        buf.extend_from_slice(&header_crc.to_le_bytes());

        // Payload length framing
        let payload_len = SERIALIZED_PAYLOAD_SIZE as u32;
        buf.extend_from_slice(&payload_len.to_le_bytes());

        let payload_start = buf.len();
        // Step count
        buf.extend_from_slice(&self.step_count.to_le_bytes());
        // Electrical
        buf.extend_from_slice(&self.q_free.to_le_bytes());
        buf.extend_from_slice(&self.c_mem.to_le_bytes());
        buf.extend_from_slice(&self.z_f.to_le_bytes());
        buf.extend_from_slice(&self.z_fixed_in.to_le_bytes());
        buf.extend_from_slice(&self.z_fixed_out.to_le_bytes());
        // Reservoirs
        for c in 0..NUM_SPECIES {
            buf.extend_from_slice(&self.n_in[c].to_le_bytes());
            buf.extend_from_slice(&self.n_out[c].to_le_bytes());
        }
        // Gates
        for c in 0..NUM_SPECIES {
            buf.extend_from_slice(&self.y_gate[c].to_le_bytes());
        }
        // Remainders
        for c in 0..NUM_SPECIES {
            buf.extend_from_slice(&self.remainder[c].to_le_bytes());
        }
        // Phase nodes
        for a in 0..NUM_PHASE_NODES {
            buf.extend_from_slice(&self.phi[a].to_le_bytes());
        }
        for a in 0..NUM_PHASE_NODES {
            buf.extend_from_slice(&self.rho[a].to_le_bytes());
        }
        // Contact mechanics
        buf.extend_from_slice(&self.contact_x.to_le_bytes());
        buf.extend_from_slice(&self.contact_ell.to_le_bytes());
        buf.extend_from_slice(&self.cumulative_d_pl.to_le_bytes());
        buf.extend_from_slice(&self.cumulative_w_in.to_le_bytes());
        buf.extend_from_slice(&self.cumulative_q_heat.to_le_bytes());

        assert_eq!(buf.len() - payload_start, SERIALIZED_PAYLOAD_SIZE);

        // Payload CRC
        let payload_crc = crc32_ieee(&buf[payload_start..]);
        buf.extend_from_slice(&payload_crc.to_le_bytes());

        assert_eq!(buf.len(), SERIALIZED_TOTAL_SIZE);
        buf
    }

    /// Import bit-exact canonical binary serialization with failure atomicity.
    pub fn import_canonical_bytes(bytes: &[u8]) -> Result<Self, NeuronPhysicsError> {
        if bytes.len() < SERIALIZED_TOTAL_SIZE {
            return Err(NeuronPhysicsError::TruncatedPayload {
                expected: SERIALIZED_TOTAL_SIZE,
                actual: bytes.len(),
            });
        }
        if &bytes[0..18] != ARCLOOM_NEURON_MAGIC {
            return Err(NeuronPhysicsError::CorruptSerialization("Magic mismatch".to_string()));
        }
        let version = u16::from_le_bytes(bytes[18..20].try_into().unwrap());
        if version != ARCLOOM_NEURON_VERSION {
            return Err(NeuronPhysicsError::CorruptSerialization(format!("Unsupported version: {}", version)));
        }
        let expected_header_crc = u32::from_le_bytes(bytes[20..24].try_into().unwrap());
        let computed_header_crc = crc32_ieee(&bytes[0..20]);
        if expected_header_crc != computed_header_crc {
            return Err(NeuronPhysicsError::InvalidChecksum {
                expected: expected_header_crc,
                computed: computed_header_crc,
            });
        }

        let payload_len = u32::from_le_bytes(bytes[24..28].try_into().unwrap()) as usize;
        if payload_len != SERIALIZED_PAYLOAD_SIZE {
            return Err(NeuronPhysicsError::CorruptSerialization(format!("Unexpected payload len: {}", payload_len)));
        }

        let payload_end = 28 + payload_len;
        let expected_payload_crc = u32::from_le_bytes(bytes[payload_end..payload_end + 4].try_into().unwrap());
        let computed_payload_crc = crc32_ieee(&bytes[28..payload_end]);
        if expected_payload_crc != computed_payload_crc {
            return Err(NeuronPhysicsError::InvalidChecksum {
                expected: expected_payload_crc,
                computed: computed_payload_crc,
            });
        }

        let mut offset = 28;
        let step_count = u64::from_le_bytes(bytes[offset..offset + 8].try_into().unwrap()); offset += 8;
        let q_free = f64::from_le_bytes(bytes[offset..offset + 8].try_into().unwrap()); offset += 8;
        let c_mem = f64::from_le_bytes(bytes[offset..offset + 8].try_into().unwrap()); offset += 8;
        let z_f = i64::from_le_bytes(bytes[offset..offset + 8].try_into().unwrap()); offset += 8;
        let z_fixed_in = i64::from_le_bytes(bytes[offset..offset + 8].try_into().unwrap()); offset += 8;
        let z_fixed_out = i64::from_le_bytes(bytes[offset..offset + 8].try_into().unwrap()); offset += 8;

        let mut n_in = [0u64; NUM_SPECIES];
        let mut n_out = [0u64; NUM_SPECIES];
        for c in 0..NUM_SPECIES {
            n_in[c] = u64::from_le_bytes(bytes[offset..offset + 8].try_into().unwrap()); offset += 8;
            n_out[c] = u64::from_le_bytes(bytes[offset..offset + 8].try_into().unwrap()); offset += 8;
        }

        let mut y_gate = [0.0f64; NUM_SPECIES];
        for c in 0..NUM_SPECIES {
            y_gate[c] = f64::from_le_bytes(bytes[offset..offset + 8].try_into().unwrap()); offset += 8;
        }

        let mut remainder = [0.0f64; NUM_SPECIES];
        for c in 0..NUM_SPECIES {
            remainder[c] = f64::from_le_bytes(bytes[offset..offset + 8].try_into().unwrap()); offset += 8;
        }

        let mut phi = [0.0f64; NUM_PHASE_NODES];
        for a in 0..NUM_PHASE_NODES {
            phi[a] = f64::from_le_bytes(bytes[offset..offset + 8].try_into().unwrap()); offset += 8;
        }

        let mut rho = [0.0f64; NUM_PHASE_NODES];
        for a in 0..NUM_PHASE_NODES {
            rho[a] = f64::from_le_bytes(bytes[offset..offset + 8].try_into().unwrap()); offset += 8;
        }

        let contact_x = f64::from_le_bytes(bytes[offset..offset + 8].try_into().unwrap()); offset += 8;
        let contact_ell = f64::from_le_bytes(bytes[offset..offset + 8].try_into().unwrap()); offset += 8;
        let cumulative_d_pl = f64::from_le_bytes(bytes[offset..offset + 8].try_into().unwrap()); offset += 8;
        let cumulative_w_in = f64::from_le_bytes(bytes[offset..offset + 8].try_into().unwrap()); offset += 8;
        let cumulative_q_heat = f64::from_le_bytes(bytes[offset..offset + 8].try_into().unwrap()); offset += 8;

        assert_eq!(offset, payload_end);

        Ok(Self {
            step_count,
            q_free,
            c_mem,
            z_f,
            z_fixed_in,
            z_fixed_out,
            n_in,
            n_out,
            y_gate,
            remainder,
            phi,
            rho,
            contact_x,
            contact_ell,
            cumulative_d_pl,
            cumulative_w_in,
            cumulative_q_heat,
        })
    }
}

// ---------------------------------------------------------------------------
// PyO3 Native Interface Bindings
// ---------------------------------------------------------------------------

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

    pub fn membrane_voltage(&self) -> f64 {
        self.state.membrane_voltage()
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

    pub fn add_fabric_edge(&mut self, from_node: usize, to_node: usize, tau_trit: i8, kappa_j: f64) -> PyResult<()> {
        let edge = TypedFabricEdge::new(from_node, to_node, tau_trit, kappa_j)
            .map_err(|e| PyValueError::new_err(e.to_string()))?;
        self.operator.add_fabric_edge(edge);
        Ok(())
    }

    #[pyo3(signature = (applied_contact_x=None, external_current_a=0.0, dt_seconds=1.0e-4))]
    pub fn step(
        &mut self,
        applied_contact_x: Option<f64>,
        external_current_a: f64,
        dt_seconds: f64,
    ) -> PyResult<(f64, f64, bool, f64)> {
        let res = self.operator.step(&mut self.state, applied_contact_x, external_current_a, dt_seconds)
            .map_err(|e| PyValueError::new_err(e.to_string()))?;
        Ok((res.prior_voltage, res.successor_voltage, res.plastic_yield_occurred, res.plastic_dissipation))
    }

    pub fn export_canonical_bytes(&self) -> Vec<u8> {
        self.state.export_canonical_bytes()
    }

    pub fn import_canonical_bytes(&mut self, bytes: &[u8]) -> PyResult<()> {
        let restored = ArcLoomNeuronState::import_canonical_bytes(bytes)
            .map_err(|e| PyValueError::new_err(e.to_string()))?;
        self.state = restored;
        Ok(())
    }
}

pub fn register(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<PyArcLoomNeuron>()?;
    Ok(())
}

// ---------------------------------------------------------------------------
// Unit Tests
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_preparation_genesis_electroneutrality_and_initial_voltage() {
        let state = ArcLoomNeuronState::new_reference_preparation();
        // 1. Check exact integer global electroneutrality
        let total_mobile_in = (state.n_in[0] as i64) * (ION_VALENCES[0] as i64)
            + (state.n_in[1] as i64) * (ION_VALENCES[1] as i64)
            + (state.n_in[2] as i64) * (ION_VALENCES[2] as i64)
            + (state.n_in[3] as i64) * (ION_VALENCES[3] as i64);
        let total_mobile_out = (state.n_out[0] as i64) * (ION_VALENCES[0] as i64)
            + (state.n_out[1] as i64) * (ION_VALENCES[1] as i64)
            + (state.n_out[2] as i64) * (ION_VALENCES[2] as i64)
            + (state.n_out[3] as i64) * (ION_VALENCES[3] as i64);

        assert_eq!(total_mobile_in + state.z_fixed_in, state.z_f);
        assert_eq!(total_mobile_out + state.z_fixed_out, -state.z_f);
        assert_eq!(total_mobile_in + state.z_fixed_in + total_mobile_out + state.z_fixed_out, 0);

        // 2. Initial gate charge Q_g,0 = 35.8 e
        let q_g0 = state.compute_q_gate();
        let expected_q_g0 = 35.8 * ELEMENTARY_CHARGE;
        assert!((q_g0 - expected_q_g0).abs() < 1e-25);

        // 3. Initial voltage ~ -65.0000031305 mV
        let v0 = state.membrane_voltage();
        let expected_v0 = -0.0650000031305;
        assert!((v0 - expected_v0).abs() < 1e-9, "v0: {} vs expected: {}", v0, expected_v0);
    }

    #[test]
    fn test_access_conductance_benchmark_values() {
        // Table in §4:
        // y=0.02 -> 4.609980952 pS
        // y=0.05 -> 11.381217721 pS
        // y=0.10 -> 22.446939398 pS
        // y=1.00 -> 203.632872245 pS
        let g_002 = single_pore_conductance(0.02) * 1e12;
        let g_005 = single_pore_conductance(0.05) * 1e12;
        let g_010 = single_pore_conductance(0.10) * 1e12;
        let g_100 = single_pore_conductance(1.00) * 1e12;

        assert!((g_002 - 4.609980952).abs() < 1e-6);
        assert!((g_005 - 11.381217721).abs() < 1e-6);
        assert!((g_010 - 22.446939398).abs() < 1e-6);
        assert!((g_100 - 203.632872245).abs() < 1e-6);
    }

    #[test]
    fn test_exact_carrier_custody_and_identity() {
        let mut state = ArcLoomNeuronState::new_reference_preparation();
        let operator = ArcLoomTransitionOperator::new_reference_operator();

        let res = operator.step(&mut state, None, 1.0e-9, 1.0e-4).expect("Step must succeed");
        assert!(res.carrier_identity_residual < 1e-25, "Residual: {}", res.carrier_identity_residual);

        // Verify that sum of integer ions and remainders matches total current
        for c in 0..NUM_SPECIES {
            let z_c = ION_VALENCES[c] as f64;
            let q_c = z_c * ELEMENTARY_CHARGE;
            let j_carrier = q_c * ((res.whole_carriers_transported[c] as f64) + res.new_remainders[c] - 0.0);
            let j_expected = res.ionic_currents[c] * 1.0e-4;
            assert!((j_carrier - j_expected).abs() < 1e-25);
        }
    }

    #[test]
    fn test_contact_plasticity_return_map_admissibility() {
        let mut state = ArcLoomNeuronState::new_reference_preparation();
        let operator = ArcLoomTransitionOperator::new_reference_operator();

        // 1. Sub-yield strain (|Sigma| <= Y): elastic branch
        let x_elastic = CONTACT_LENGTH_REF_M * 1.02; // 2% strain < 5% yield
        let res_elastic = operator.step(&mut state, Some(x_elastic), 0.0, 1.0e-4).unwrap();
        assert!(!res_elastic.plastic_yield_occurred);
        assert_eq!(res_elastic.plastic_dissipation, 0.0);
        assert_eq!(state.contact_ell, CONTACT_LENGTH_REF_M);

        // 2. Post-yield strain (|Sigma| > Y): plastic branch
        let x_plastic = CONTACT_LENGTH_REF_M * 1.15; // 15% strain > 5% yield
        let res_plastic = operator.step(&mut state, Some(x_plastic), 0.0, 1.0e-4).unwrap();
        assert!(res_plastic.plastic_yield_occurred);
        assert!(res_plastic.plastic_dissipation > 0.0);
        assert!(state.contact_ell > CONTACT_LENGTH_REF_M);

        // Yield condition f = |Sigma_tr| - Y <= 0 holds on new rest length
        let new_eps = state.contact_x / state.contact_ell - 1.0;
        let new_sigma = CONTACT_STRAIN_STIFFNESS_J * new_eps;
        assert!((new_sigma.abs() - CONTACT_YIELD_THRESHOLD_J).abs() < 1e-20);
    }

    #[test]
    fn test_typed_fabric_paired_forces_zero_sum() {
        let edge = TypedFabricEdge::new(0, 1, 1, 4.28e-20).unwrap();
        let (fa, fb) = edge.forces(0.5, 1.2);
        assert_eq!(fa + fb, 0.0, "Paired constraint forces must sum exactly to zero");
    }

    #[test]
    fn test_cold_state_serialization_roundtrip_and_successor_identity() {
        let mut original = ArcLoomNeuronState::new_reference_preparation();
        let operator = ArcLoomTransitionOperator::new_reference_operator();

        // Advance 3 steps
        for _ in 0..3 {
            operator.step(&mut original, Some(CONTACT_LENGTH_REF_M * 1.08), 5.0e-10, 1.0e-4).unwrap();
        }

        // Export canonical bytes
        let serialized = original.export_canonical_bytes();
        assert_eq!(serialized.len(), SERIALIZED_TOTAL_SIZE);

        // Import into clean instance
        let mut restored = ArcLoomNeuronState::import_canonical_bytes(&serialized).unwrap();
        assert_eq!(original, restored, "State must decode bit-for-bit identically");

        // Advance both under identical stimulus
        let res_orig = operator.step(&mut original, Some(CONTACT_LENGTH_REF_M * 1.02), -2.0e-10, 1.0e-4).unwrap();
        let res_rest = operator.step(&mut restored, Some(CONTACT_LENGTH_REF_M * 1.02), -2.0e-10, 1.0e-4).unwrap();

        assert_eq!(res_orig, res_rest, "Successor transitions must be bit-identical");
        assert_eq!(original, restored, "Post-transition state must be bit-identical");
    }
}
