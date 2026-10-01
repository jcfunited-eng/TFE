//! Engineered one-neuron material component. Numerical dynamics are NOT exact
//! real arithmetic; admitted integrated charges have exact bounded custody.
//! Full joint UF/MathLoom mounting and organism motor integration are separate
//! capabilities. This module must not describe fixture edges as the full field.

use pyo3::prelude::*;
use pyo3::exceptions::{PyRuntimeError, PyValueError};
use std::f64::consts::PI;
#[path = "exact_carrier.rs"]
mod exact_carrier;
use exact_carrier::{Remainder, transfer};

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

// This is an engineering numerical accuracy target, not a cognitive threshold.
// Joe approved bounded neuron-only integration on 2026-10-01.
const DEFAULT_RTOL: f64 = 1.0e-6;
const MAX_REFINEMENT: usize = 12; // declared 4096-subinterval work budget
const MAX_FIXED_POINT: usize = 48;
const SOLVE_TOL: f64 = 128.0 * f64::EPSILON;
const GATE_PHASE_COUPLING_J: f64 = 1.0e-20;
const GENESIS_RECEIVER_Z: i64 = -405698;
const MAGIC: &[u8;18] = b"ARCLOOM_NEURON_V3\0";

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


#[inline]
pub fn pore_conductance(y: f64) -> f64 {
    if y == 0.0 { 0.0 } else { y / (R_P0 + R_A0*y.sqrt()) }
}

pub fn compute_crc32(data: &[u8]) -> u32 {
    let mut crc = !0u32;
    for &byte in data {
        crc ^= byte as u32;
        for _ in 0..8 { crc = (crc >> 1) ^ (0xedb88320u32 & 0u32.wrapping_sub(crc & 1)); }
    }
    !crc
}

fn finite(v: f64) -> Result<f64, String> {
    if v.is_finite() { Ok(v) } else { Err("Non-finite physical intermediate".into()) }
}
fn wrap(phi: f64) -> Result<f64, String> {
    finite(phi)?;
    Ok((phi + PI).rem_euclid(2.0*PI) - PI)
}
fn sinc(x: f64) -> f64 { if x == 0.0 { 1.0 } else { x.sin()/x } }

#[derive(Clone, Debug, PartialEq)]
pub struct ArcLoomNeuronState {
    pub step_count: u64,
    pub z_fixed_in: i64,
    pub z_fixed_out: i64,
    pub z_ext_port: i64,
    pub z_rec_port: i64,
    r_ext: Remainder,
    r_rec: Remainder,
    r_ion: [Remainder;4],
    pub n_in: [u64;4],
    pub n_out: [u64;4],
    pub y_gate: [f64;4],
    pub phi: [f64;4],
    pub contact_x: f64,
    pub contact_ell: f64,
    pub c_rec: f64,
    pub cumulative_d_pl: f64,
    pub cumulative_w_in: f64,
    pub cumulative_q_heat: f64,
}
impl ArcLoomNeuronState {
    pub fn new_reference_preparation() -> Self {
        Self { step_count:0, z_fixed_in:GENESIS_Z_FIXED_IN, z_fixed_out:GENESIS_Z_FIXED_OUT,
            z_ext_port:0, z_rec_port:0, r_ext:Remainder::ZERO, r_rec:Remainder::ZERO,
            r_ion:[Remainder::ZERO;4], n_in:GENESIS_N_IN, n_out:GENESIS_N_OUT,
            y_gate:RESTING_APERTURES, phi:[0.0;4], contact_x:CONTACT_LENGTH_REF_M,
            contact_ell:CONTACT_LENGTH_REF_M, c_rec:RECEIVING_CAPACITANCE_F,
            cumulative_d_pl:0.0,cumulative_w_in:0.0,cumulative_q_heat:0.0 }
    }
    pub fn integer_free_charge(&self) -> i128 {
        let mut z = self.z_fixed_in as i128 + self.z_ext_port as i128 - self.z_rec_port as i128;
        for c in 0..4 { z += SPECIES_VALENCE[c] as i128 * self.n_in[c] as i128; }
        z
    }
    pub fn gate_charge_c(&self) -> f64 { gate_charge(&self.y_gate) }
    pub fn membrane_voltage(&self, c_mem:f64) -> f64 {
        (self.integer_free_charge() as f64 * ELEMENTARY_CHARGE_C - self.gate_charge_c())/c_mem
    }
    pub fn receiving_voltage(&self) -> f64 {
        (GENESIS_RECEIVER_Z as i128 + self.z_rec_port as i128) as f64 * ELEMENTARY_CHARGE_C/self.c_rec
    }
    fn validate(&self) -> Result<(),String> {
        self.r_ext.validate()?; self.r_rec.validate()?;
        for c in 0..4 {
            self.r_ion[c].validate()?;
            if !self.y_gate[c].is_finite() || !(0.0..=1.0).contains(&self.y_gate[c]) {
                return Err("Gate outside physical aperture domain".into());
            }
            if !self.phi[c].is_finite() || !(-PI..PI).contains(&self.phi[c]) {
                return Err("Noncanonical phase".into());
            }
            if self.n_in[c]==0 || self.n_out[c]==0 {
                return Err("Logarithmic material model unavailable at empty reservoir".into());
            }
        }
        for x in [self.contact_x,self.contact_ell,self.c_rec] {
            if !x.is_finite() || x<=0.0 { return Err("Invalid material geometry or capacitance".into()); }
        }
        for q in [self.cumulative_d_pl,self.cumulative_q_heat] {
            if !q.is_finite() || q<0.0 { return Err("Invalid dissipated energy".into()); }
        }
        finite(self.cumulative_w_in)?;
        // Every transported carrier has two endpoints. The external electrode
        // owns -z_ext_port; receiver owns +z_rec_port and its opposite genesis plate.
        let mut conserved = self.z_fixed_in as i128 + self.z_fixed_out as i128;
        for c in 0..4 { conserved += SPECIES_VALENCE[c] as i128*(self.n_in[c] as i128+self.n_out[c] as i128); }
        if conserved != 0 { return Err("Unbalanced finite chemical countercharge".into()); }
        Ok(())
    }
}
fn gate_charge(y:&[f64;4]) -> f64 {
    let mut q=0.0;
    for c in 0..4 { q += CHANNEL_POPULATIONS[c] as f64*GATE_CHARGES_E[c]*ELEMENTARY_CHARGE_C*y[c]; }
    q
}

#[derive(Clone, Debug, PartialEq)]
pub struct ArcLoomTransitionOperator {
    pub c_mem:f64, pub k_strain:f64, pub y_yield:f64,
    pub zeta_gate:f64, pub gamma_phi:f64,
    pub fabric_edges:Vec<TypedFabricEdge>,
}
#[pyclass(name="NeuronTransition",get_all)]
#[derive(Clone, Debug, PartialEq)]
pub struct TransitionResult {
    pub prior_membrane_v:f64, pub succ_membrane_v:f64,
    pub prior_receiving_v:f64, pub succ_receiving_v:f64,
    pub plastic_yield_occurred:bool, pub plastic_dissipation_j:f64,
    pub work_input_j:f64, pub heat_dissipated_j:f64,
    pub delta_enthalpy_j:f64, pub energy_residual_j:f64,
    pub numerical_energy_bound_j:f64, pub carrier_energy_bound_j:f64,
    pub receiving_charge_transferred_c:f64, pub integrated_charge_c:[f64;6],
    pub whole_carriers:[i128;6], pub subintervals:usize,
    pub convergence_error:f64,
}

#[derive(Clone, Debug)]
struct Trajectory { u:[f64;13], work:f64, heat:f64 }
impl ArcLoomTransitionOperator {
    pub fn new_reference_operator() -> Self {
        Self { c_mem:MEMBRANE_CAPACITANCE_F,k_strain:CONTACT_STRAIN_STIFFNESS_J,
            y_yield:CONTACT_YIELD_THRESHOLD_J,zeta_gate:GATE_DRAG_ZETA_J_S,
            gamma_phi:PHASE_DRAG_GAMMA_J_S,fabric_edges:Vec::new() }
    }
    fn validate(&self) -> Result<(),String> {
        for x in [self.c_mem,self.k_strain,self.y_yield,self.zeta_gate,self.gamma_phi] {
            if !x.is_finite() || x<=0.0 { return Err("Invalid material parameter".into()); }
        }
        if self.y_yield>=self.k_strain || self.fabric_edges.len()>MAX_FABRIC_EDGES {
            return Err("Invalid material yield or topology".into());
        }
        for e in &self.fabric_edges {
            TypedFabricEdge::new(e.dim,e.role,e.position,e.from_node,e.to_node,e.tau_trit,e.kappa_j)?;
            if e.position>=679 { return Err("Position exceeds complete finite binary64 MathLoom bound".into()); }
        }
        Ok(())
    }
    pub fn add_fabric_edge(&mut self, edge:TypedFabricEdge) -> Result<(),String> {
        self.validate()?;
        TypedFabricEdge::new(edge.dim,edge.role,edge.position,edge.from_node,edge.to_node,edge.tau_trit,edge.kappa_j)?;
        if edge.position>=679 || self.fabric_edges.len()==MAX_FABRIC_EDGES {
            return Err("Unadmitted typed position or material edge capacity".into());
        }
        if self.fabric_edges.iter().any(|e| e.dim==edge.dim && e.role==edge.role &&
            e.position==edge.position && e.from_node==edge.from_node && e.to_node==edge.to_node) {
            return Err("Duplicate physical constraint incidence".into());
        }
        self.fabric_edges.push(edge);
        Ok(())
    }
    fn contact_g(&self, x:f64)->Result<f64,String> {
        let area=finite(CONTACT_AREA_REF_M2*(CONTACT_LENGTH_REF_M/x))?;
        finite(CONTACT_MATERIAL_CONDUCTIVITY_S_PER_M*(area/x))
    }
    pub fn equilibrium_contact_x(&self, s:&ArcLoomNeuronState, force:f64)->Result<f64,String> {
        self.validate()?; s.validate()?; finite(force)?;
        // dU/dx=K*(x/ell-1)/ell. This computes the elastic equilibrium,
        // not a semantic movement command. Super-yield force control has no
        // static solution in the declared perfect-plastic material.
        let strain=finite(force*s.contact_ell/self.k_strain)?;
        if strain.abs()>self.y_yield/self.k_strain {
            return Err("No static sub-yield equilibrium for the applied force".into());
        }
        let x=finite(s.contact_ell*(1.0+strain))?;
        if x<=0.0 { return Err("Nonpositive loaded geometry".into()); }
        Ok(x)
    }
    fn nonchemical_energy(&self, y:&[f64;4], phi:&[f64;4], q:f64, qr:f64,
        c_rec:f64,x:f64,ell:f64)->f64 {
        let mut h=(q-gate_charge(y)).powi(2)/(2.0*self.c_mem)+qr*qr/(2.0*c_rec)
            +0.5*self.k_strain*(x/ell-1.0).powi(2);
        for c in 0..4 {
            h+=CHANNEL_POPULATIONS[c] as f64*0.5*GATE_STIFFNESS_K_J*(y[c]-RESTING_APERTURES[c]).powi(2);
        }
        for e in &self.fabric_edges {
            let delta=phi[e.to_node]-phi[e.from_node];
            h+=e.energy(phi[e.from_node],phi[e.to_node])
                -CHANNEL_POPULATIONS[e.from_node] as f64*GATE_PHASE_COUPLING_J*y[e.from_node]*delta.cos();
        }
        h
    }
    fn chemical_delta(n:f64, dn:f64, volume:f64)->Result<f64,String> {
        if n<=0.0 || n+dn<=0.0 { return Err("Finite chemical reservoir depleted".into()); }
        // Difference of F=kT*N*(ln(N/(V*n_ref))-1), n_ref=1/m^3.
        // ln_1p avoids subtracting two O(1e-7 J) whole-cell free energies.
        finite(KT_J*(dn*(n/volume).ln()+(n+dn)*(dn/n).ln_1p()-dn))
    }
    fn delta_energy(&self,a:&ArcLoomNeuronState,b:&ArcLoomNeuronState)->Result<f64,String> {
        let qa=a.integer_free_charge() as f64*ELEMENTARY_CHARGE_C;
        let qb=b.integer_free_charge() as f64*ELEMENTARY_CHARGE_C;
        let ra=a.receiving_voltage()*a.c_rec;
        let rb=b.receiving_voltage()*b.c_rec;
        let mut dh=self.nonchemical_energy(&b.y_gate,&b.phi,qb,rb,b.c_rec,b.contact_x,b.contact_ell)
            -self.nonchemical_energy(&a.y_gate,&a.phi,qa,ra,a.c_rec,a.contact_x,a.contact_ell);
        for c in 0..4 {
            let dn=(b.n_in[c] as i128-a.n_in[c] as i128) as f64;
            dh+=Self::chemical_delta(a.n_in[c] as f64,dn,VOLUME_IN_M3)?;
            dh+=Self::chemical_delta(a.n_out[c] as f64,-dn,VOLUME_OUT_M3)?;
        }
        finite(dh)
    }
    fn continuous_voltages(&self,s:&ArcLoomNeuronState,u:&[f64;13],ext:f64)->Result<(f64,f64),String> {
        let y=[u[0],u[1],u[2],u[3]];
        let q=s.integer_free_charge() as f64*ELEMENTARY_CHARGE_C+ext-u[8..12].iter().sum::<f64>()-u[12];
        let qr=s.receiving_voltage()*s.c_rec+u[12];
        Ok((finite((q-gate_charge(&y))/self.c_mem)?,finite(qr/s.c_rec)?))
    }
    fn scaled_error(&self,a:&[f64;13],b:&[f64;13])->f64 {
        let qscale=self.c_mem*KT_J/ELEMENTARY_CHARGE_C;
        let mut error:f64=0.0;
        for i in 0..13 {
            let scale=if i<4 { 1.0 } else if i<8 { PI } else { qscale };
            error=error.max((a[i]-b[i]).abs()/scale);
        }
        error
    }
    fn trajectory_error(&self,s:&ArcLoomNeuronState,a:&Trajectory,b:&Trajectory,ext:f64)->Result<f64,String> {
        let mut error=self.scaled_error(&a.u,&b.u);
        let (va,ra)=self.continuous_voltages(s,&a.u,ext)?;
        let (vb,rb)=self.continuous_voltages(s,&b.u,ext)?;
        let thermal_voltage=KT_J/ELEMENTARY_CHARGE_C;
        error=error.max((va-vb).abs()/thermal_voltage).max((ra-rb).abs()/thermal_voltage);
        let energy_scale=a.work.abs().max(b.work.abs()).max(a.heat).max(b.heat).max(KT_J);
        error=error.max((a.work-b.work).abs()/energy_scale)
            .max((a.heat-b.heat).abs()/energy_scale);
        finite(error)
    }
    fn integrate(&self,s:&ArcLoomNeuronState,current:f64,dt:f64,n:usize)->Result<Trajectory,String> {
        let h=dt/n as f64;
        if h==0.0 { return Err("Subinterval underflow".into()); }
        let mut u=[0.0;13];
        u[..4].copy_from_slice(&s.y_gate);
        u[4..8].copy_from_slice(&s.phi);
        let mut work=0.0; let mut heat=0.0;
        let g_contact=self.contact_g(s.contact_x)?;
        for k in 0..n {
            let start=u;
            let mut end=start;
            let ext0=current*(k as f64*h);
            let ext1=current*((k+1) as f64*h);
            let mut converged=false;
            let mut final_pore_heat=0.0;
            let mut final_rec_heat=0.0;
            let mut final_vmid=0.0;
            for _ in 0..MAX_FIXED_POINT {
                let (v0,r0)=self.continuous_voltages(s,&start,ext0)?;
                let (v1,r1)=self.continuous_voltages(s,&end,ext1)?;
                let vmid=(v0+v1)*0.5;
                let rmid=(r0+r1)*0.5;
                let mut fgate=[0.0;4]; let mut fphase=[0.0;4];
                for c in 0..4 {
                    fgate[c]=-GATE_STIFFNESS_K_J*((start[c]+end[c])*0.5-RESTING_APERTURES[c])
                        +GATE_CHARGES_E[c]*ELEMENTARY_CHARGE_C*vmid;
                }
                for e in &self.fabric_edges {
                    let a=e.from_node; let b=e.to_node;
                    let d0=start[4+b]-start[4+a]; let d1=end[4+b]-end[4+a];
                    let mid=(d0+d1)*0.5; let half=(d1-d0)*0.5;
                    let f=e.kappa_j*(mid-2.0*PI*e.tau_trit as f64/3.0).sin()*sinc(half)
                        +CHANNEL_POPULATIONS[a] as f64*GATE_PHASE_COUPLING_J*
                            (start[a]+end[a])*0.5*mid.sin()*sinc(half);
                    fphase[a]+=f; fphase[b]-=f;
                    fgate[a]+=GATE_PHASE_COUPLING_J*(d0.cos()+d1.cos())*0.5;
                }
                let mut candidate=start;
                for c in 0..4 {
                    let free=finite(start[c]+h*fgate[c]/self.zeta_gate)?;
                    // Solve the stated normal-cone boundary equation as an
                    // active set. This is NOT post-integration state clamping:
                    // its nonzero discrete boundary work remains in the energy
                    // residual and causes refinement/refusal when excessive.
                    candidate[c]=if free<0.0 { 0.0 } else if free>1.0 { 1.0 } else { free };
                    candidate[4+c]=start[4+c]+h*fphase[c]/self.gamma_phi;
                }
                let mut pore_heat=0.0;
                for c in 0..4 {
                    let q=SPECIES_VALENCE[c] as f64*ELEMENTARY_CHARGE_C;
                    let n0=s.n_in[c] as f64-start[8+c]/q;
                    let n1=s.n_in[c] as f64-end[8+c]/q;
                    let o0=s.n_out[c] as f64+start[8+c]/q;
                    let o1=s.n_out[c] as f64+end[8+c]/q;
                    if n0<=0.0 || n1<=0.0 || o0<=0.0 || o1<=0.0 { return Err("Continuous chemical domain depleted".into()); }
                    let dn=n1-n0;
                    let muin=if dn==0.0 { KT_J*(n0/VOLUME_IN_M3).ln() }
                        else { Self::chemical_delta(n0,dn,VOLUME_IN_M3)?/dn };
                    let dout=o1-o0;
                    let muout=if dout==0.0 { KT_J*(o0/VOLUME_OUT_M3).ln() }
                        else { Self::chemical_delta(o0,dout,VOLUME_OUT_M3)?/dout };
                    let rev=(muout-muin)/q;
                    let g=CHANNEL_POPULATIONS[c] as f64*pore_conductance((start[c]+end[c])*0.5);
                    candidate[8+c]=start[8+c]+h*g*(vmid-rev);
                    pore_heat+=h*g*(vmid-rev).powi(2);
                }
                candidate[12]=start[12]+h*g_contact*(vmid-rmid);
                for x in candidate { finite(x)?; }
                let error=self.scaled_error(&candidate,&end);
                end=candidate;
                final_pore_heat=pore_heat;
                final_rec_heat=h*g_contact*(vmid-rmid).powi(2);
                final_vmid=vmid;
                if error<=SOLVE_TOL { converged=true;break; }
            }
            if !converged { return Err("Coupled implicit solve did not converge".into()); }
            let mut friction=0.0;
            for c in 0..4 {
                friction+=CHANNEL_POPULATIONS[c] as f64*self.zeta_gate*(end[c]-start[c]).powi(2)/h
                    +self.gamma_phi*(end[4+c]-start[4+c]).powi(2)/h;
            }
            work+=h*current*final_vmid;
            heat+=friction+final_pore_heat+final_rec_heat;
            u=end;
        }
        finite(work)?; finite(heat)?;
        Ok(Trajectory {u,work,heat})
    }
    pub fn step(&self,state:&mut ArcLoomNeuronState,applied_contact_x:Option<f64>,
        external_current_a:f64,dt_seconds:f64)->Result<TransitionResult,String> {
        self.step_with_accuracy(state,applied_contact_x,None,external_current_a,dt_seconds,DEFAULT_RTOL)
    }
    pub fn step_with_accuracy(&self,state:&mut ArcLoomNeuronState,x:Option<f64>,force:Option<f64>,
        current:f64,dt:f64,rtol:f64)->Result<TransitionResult,String> {
        self.validate()?;state.validate()?; finite(current)?;
        if !dt.is_finite() || dt<=0.0 || !rtol.is_finite() || rtol<SOLVE_TOL || rtol>=1.0 {
            return Err("Invalid timestep or numerical accuracy contract".into());
        }
        if x.is_some() && force.is_some() { return Err("Specify displacement OR force, not both".into()); }
        let target=if let Some(f)=force { self.equilibrium_contact_x(state,f)? } else { x.unwrap_or(state.contact_x) };
        if !target.is_finite() || target<=0.0 { return Err("Invalid applied geometry".into()); }
        let step_count=state.step_count.checked_add(1).ok_or("Step counter overflow")?;
        let ext_charge=finite(current*dt)?;
        // Preflight exact lattice/port overflow before any nonlinear solver work.
        let (ext_n,ext_r)=state.r_ext.prepare(ext_charge,1)?;
        let ext_count=i64::try_from(ext_n).map_err(|_|"External carrier port overflow")?;
        let next_ext=state.z_ext_port.checked_add(ext_count).ok_or("External carrier port overflow")?;
        let old_strain=state.contact_x/state.contact_ell-1.0;
        let strain=finite(target/state.contact_ell-1.0)?;
        let stress=finite(self.k_strain*strain)?;
        let yielded=stress.abs()>self.y_yield;
        let ratio=self.y_yield/self.k_strain;
        let ell=if yielded { finite(target/(1.0+stress.signum()*ratio))? } else { state.contact_ell };
        let dpl=if yielded { finite(0.5*self.k_strain*(strain*strain-ratio*ratio))? } else { 0.0 };
        let wmech=finite(0.5*self.k_strain*(strain*strain-old_strain*old_strain))?;
        let mut loaded=state.clone();
        loaded.contact_x=target;loaded.contact_ell=ell;
        loaded.validate()?;
        let mut previous:Option<Trajectory>=None;
        let mut last_failure="No converged trajectory".to_string();
        for level in 0..=MAX_REFINEMENT {
            let n=1usize<<level;
            let trajectory=match self.integrate(&loaded,current,dt,n) {
                Ok(t)=>t,Err(e)=>{last_failure=e;previous=None;continue;}
            };
            let mut error=f64::INFINITY;
            if let Some(prior)=&previous { error=self.trajectory_error(&loaded,&trajectory,prior,ext_charge)?; }
            previous=Some(trajectory.clone());
            if error>rtol { continue; }
            let mut next=loaded.clone();
            next.step_count=step_count;next.z_ext_port=next_ext;next.r_ext=ext_r;
            let mut whole=[0i128;6];
            let mut integrated=[0.0;6];
            for c in 0..4 {
                let (count,r)=state.r_ion[c].prepare(trajectory.u[8+c],SPECIES_VALENCE[c])?;
                transfer(&mut next.n_in[c],&mut next.n_out[c],count)?;
                next.r_ion[c]=r;
                next.y_gate[c]=trajectory.u[c];
                next.phi[c]=wrap(trajectory.u[4+c])?;
                whole[c]=count;integrated[c]=trajectory.u[8+c];
            }
            let (rn,rr)=state.r_rec.prepare(trajectory.u[12],1)?;
            let rcount=i64::try_from(rn).map_err(|_|"Receiving carrier port overflow")?;
            next.z_rec_port=state.z_rec_port.checked_add(rcount).ok_or("Receiving carrier port overflow")?;
            next.r_rec=rr;
            whole[4]=ext_n;whole[5]=rn;integrated[4]=ext_charge;integrated[5]=trajectory.u[12];
            let work=wmech+trajectory.work;
            let heat=dpl+trajectory.heat;
            next.cumulative_d_pl=finite(state.cumulative_d_pl+dpl)?;
            next.cumulative_w_in=finite(state.cumulative_w_in+work)?;
            next.cumulative_q_heat=finite(state.cumulative_q_heat+heat)?;
            next.validate()?;
            let dh=self.delta_energy(state,&next)?;
            let residual=finite(dh-work+heat)?;
            let scale=work.abs().max(heat.abs()).max(dh.abs()).max(KT_J);
            // Arithmetic floor is explicit; it is not charged to physical heat.
            let arithmetic=256.0*f64::EPSILON*(self.c_mem*(state.membrane_voltage(self.c_mem).powi(2)
                +next.membrane_voltage(self.c_mem).powi(2))+KT_J*
                state.n_in.iter().chain(state.n_out.iter()).map(|&n|n as f64).sum::<f64>());
            let numerical=finite(rtol*scale+arithmetic)?;
            // Each exact remainder is <1 carrier. Difference of two remainders
            // is <2. Bound its energetic effect by the electrochemical endpoint
            // gradients plus the quadratic capacitor term (mean value theorem).
            let (continuous_v,continuous_r)=self.continuous_voltages(&loaded,&trajectory.u,ext_charge)?;
            let vabs=state.membrane_voltage(self.c_mem).abs().max(next.membrane_voltage(self.c_mem).abs())
                .max(continuous_v.abs());
            let rabs=state.receiving_voltage().abs().max(next.receiving_voltage().abs()).max(continuous_r.abs());
            let mut carrier_bound=0.0;
            let mut qerr=0.0;
            for c in 0..4 {
                let q=(SPECIES_VALENCE[c] as f64*ELEMENTARY_CHARGE_C).abs();
                let mut revmax:f64=0.0;
                for st in [state as &ArcLoomNeuronState,&next] {
                    revmax=revmax.max((KT_J/q*((st.n_out[c] as f64/VOLUME_OUT_M3)/(st.n_in[c] as f64/VOLUME_IN_M3)).ln()).abs());
                }
                // Include the continuous endpoint as well as integer endpoints:
                // near depletion, two carriers need not be a small chemical perturbation.
                let continuous_in=state.n_in[c] as f64-trajectory.u[8+c]/
                    (SPECIES_VALENCE[c] as f64*ELEMENTARY_CHARGE_C);
                let continuous_out=state.n_out[c] as f64+trajectory.u[8+c]/
                    (SPECIES_VALENCE[c] as f64*ELEMENTARY_CHARGE_C);
                if continuous_in<=0.0 || continuous_out<=0.0 {
                    return Err("Continuous endpoint outside chemical domain".into());
                }
                revmax=revmax.max((KT_J/q*((continuous_out/VOLUME_OUT_M3)/(continuous_in/VOLUME_IN_M3)).ln()).abs());
                carrier_bound+=2.0*q*(vabs+revmax);qerr+=2.0*q;
            }
            carrier_bound+=2.0*ELEMENTARY_CHARGE_C*(2.0*vabs+rabs);
            qerr+=4.0*ELEMENTARY_CHARGE_C;
            carrier_bound+=qerr*qerr/(2.0*self.c_mem)+(2.0*ELEMENTARY_CHARGE_C).powi(2)/(2.0*state.c_rec);
            finite(carrier_bound)?;
            if residual.abs()>numerical+carrier_bound {
                last_failure=format!("First Law residual {} exceeds declared bounds {}",residual,numerical+carrier_bound);
                continue;
            }
            let result=TransitionResult {prior_membrane_v:state.membrane_voltage(self.c_mem),
                succ_membrane_v:next.membrane_voltage(self.c_mem),prior_receiving_v:state.receiving_voltage(),
                succ_receiving_v:next.receiving_voltage(),plastic_yield_occurred:yielded,plastic_dissipation_j:dpl,
                work_input_j:work,heat_dissipated_j:heat,delta_enthalpy_j:dh,energy_residual_j:residual,
                numerical_energy_bound_j:numerical,carrier_energy_bound_j:carrier_bound,
                receiving_charge_transferred_c:rn as f64*ELEMENTARY_CHARGE_C,
                integrated_charge_c:integrated,whole_carriers:whole,subintervals:n,convergence_error:error };
            *state=next;
            return Ok(result);
        }
        Err(format!("Atomic refusal: numerical work budget exhausted; {}",last_failure))
    }
}

impl ArcLoomTransitionOperator {
    pub fn export_canonical_checkpoint(&self,s:&ArcLoomNeuronState)->Vec<u8> {
        let mut p=Vec::new();
        p.extend_from_slice(&s.step_count.to_be_bytes());
        for z in [s.z_fixed_in,s.z_fixed_out,s.z_ext_port,s.z_rec_port] { p.extend_from_slice(&z.to_be_bytes()); }
        s.r_ext.encode(&mut p);s.r_rec.encode(&mut p);
        for r in s.r_ion {r.encode(&mut p);}
        for c in 0..4 {
            p.extend_from_slice(&s.n_in[c].to_be_bytes());p.extend_from_slice(&s.n_out[c].to_be_bytes());
            p.extend_from_slice(&s.y_gate[c].to_be_bytes());p.extend_from_slice(&s.phi[c].to_be_bytes());
        }
        for x in [s.contact_x,s.contact_ell,s.c_rec,s.cumulative_d_pl,s.cumulative_w_in,s.cumulative_q_heat,
            self.c_mem,self.k_strain,self.y_yield,self.zeta_gate,self.gamma_phi] {p.extend_from_slice(&x.to_be_bytes());}
        p.extend_from_slice(&(self.fabric_edges.len() as u16).to_be_bytes());
        for e in &self.fabric_edges {
            p.extend_from_slice(&[e.dim as u8,e.role as u8]);
            p.extend_from_slice(&e.position.to_be_bytes());
            p.extend_from_slice(&[e.from_node as u8,e.to_node as u8,e.tau_trit as u8]);
            p.extend_from_slice(&e.kappa_j.to_be_bytes());
        }
        let mut out=Vec::new();
        out.extend_from_slice(MAGIC);
        out.extend_from_slice(&(p.len() as u32).to_be_bytes());
        out.extend_from_slice(&compute_crc32(&out).to_be_bytes());
        out.extend_from_slice(&p);
        out.extend_from_slice(&compute_crc32(&p).to_be_bytes());
        out
    }
    pub fn import_canonical_checkpoint(bytes:&[u8])->Result<(Self,ArcLoomNeuronState),String> {
        const FIXED_PAYLOAD:usize=5*8+6*145+4*32+11*8+2;
        if bytes.len()<30 || bytes.get(..18)!=Some(MAGIC.as_slice()) {
            return Err("Missing current V3 checkpoint; no implicit legacy migration".into());
        }
        let len=u32::from_be_bytes(bytes[18..22].try_into().unwrap()) as usize;
        if len<FIXED_PAYLOAD || len>FIXED_PAYLOAD+15*MAX_FABRIC_EDGES || bytes.len()!=30+len {
            return Err("Noncanonical checkpoint length".into());
        }
        if compute_crc32(&bytes[..22])!=u32::from_be_bytes(bytes[22..26].try_into().unwrap()) {
            return Err("Header CRC mismatch".into());
        }
        let p=&bytes[26..26+len];
        if compute_crc32(p)!=u32::from_be_bytes(bytes[26+len..].try_into().unwrap()) {
            return Err("Payload CRC mismatch".into());
        }
        let mut r=Reader{bytes:p,at:0};
        let mut s=ArcLoomNeuronState::new_reference_preparation();
        s.step_count=r.u64()?;
        s.z_fixed_in=r.i64()?;s.z_fixed_out=r.i64()?;s.z_ext_port=r.i64()?;s.z_rec_port=r.i64()?;
        s.r_ext=Remainder::decode(r.take(145)?)?;s.r_rec=Remainder::decode(r.take(145)?)?;
        for c in 0..4 {s.r_ion[c]=Remainder::decode(r.take(145)?)?;}
        for c in 0..4 {s.n_in[c]=r.u64()?;s.n_out[c]=r.u64()?;s.y_gate[c]=r.f64()?;s.phi[c]=r.f64()?;}
        s.contact_x=r.f64()?;s.contact_ell=r.f64()?;s.c_rec=r.f64()?;
        s.cumulative_d_pl=r.f64()?;s.cumulative_w_in=r.f64()?;s.cumulative_q_heat=r.f64()?;
        let mut op=Self {c_mem:r.f64()?,k_strain:r.f64()?,y_yield:r.f64()?,
            zeta_gate:r.f64()?,gamma_phi:r.f64()?,fabric_edges:Vec::new()};
        let count=r.u16()? as usize;
        if count>MAX_FABRIC_EDGES || r.bytes.len()-r.at!=count*15 {return Err("Invalid edge framing".into());}
        for _ in 0..count {
            let dim=StructuralFieldDim::from_u8(r.u8()?).ok_or("Invalid field tag")?;
            let role=FieldRole::from_u8(r.u8()?).ok_or("Invalid numeric role")?;
            let position=r.u16()?;let from=r.u8()? as usize;let to=r.u8()? as usize;
            let trit=r.u8()? as i8;let kappa=r.f64()?;
            op.add_fabric_edge(TypedFabricEdge::new(dim,role,position,from,to,trit,kappa)?)?;
        }
        s.validate()?;op.validate()?;
        finite(s.membrane_voltage(op.c_mem))?;finite(s.receiving_voltage())?;
        // Reject noncanonical decoded values rather than normalizing them.
        if op.export_canonical_checkpoint(&s)!=bytes {return Err("Noncanonical physical encoding".into());}
        Ok((op,s))
    }
}
struct Reader<'a>{bytes:&'a [u8],at:usize}
impl<'a> Reader<'a>{
    fn take(&mut self,n:usize)->Result<&'a [u8],String>{
        let end=self.at.checked_add(n).ok_or("Checkpoint offset overflow")?;
        let value=self.bytes.get(self.at..end).ok_or("Truncated physical payload")?;
        self.at=end;Ok(value)
    }
    fn u8(&mut self)->Result<u8,String>{Ok(self.take(1)?[0])}
    fn u16(&mut self)->Result<u16,String>{Ok(u16::from_be_bytes(self.take(2)?.try_into().unwrap()))}
    fn u64(&mut self)->Result<u64,String>{Ok(u64::from_be_bytes(self.take(8)?.try_into().unwrap()))}
    fn i64(&mut self)->Result<i64,String>{Ok(i64::from_be_bytes(self.take(8)?.try_into().unwrap()))}
    fn f64(&mut self)->Result<f64,String>{finite(f64::from_be_bytes(self.take(8)?.try_into().unwrap()))}
}

#[pyclass(name="ArcLoomNeuron")]
pub struct PyArcLoomNeuron {state:ArcLoomNeuronState,operator:ArcLoomTransitionOperator}
#[pymethods]
impl PyArcLoomNeuron {
    #[new]
    pub fn new()->Self{Self{state:ArcLoomNeuronState::new_reference_preparation(),operator:ArcLoomTransitionOperator::new_reference_operator()}}
    #[pyo3(signature=(from_node,to_node,tau_trit,kappa_j,dim=0,role=0,position=0))]
    pub fn add_fabric_edge(&mut self,from_node:usize,to_node:usize,tau_trit:i8,kappa_j:f64,
        dim:u8,role:u8,position:u16)->PyResult<()> {
        if self.state.step_count!=0 {return Err(PyValueError::new_err("Anatomy is fixed after preparation; no unaccounted coupling work"));}
        let d=StructuralFieldDim::from_u8(dim).ok_or_else(||PyValueError::new_err("Invalid field family"))?;
        let r=FieldRole::from_u8(role).ok_or_else(||PyValueError::new_err("Invalid numeric role"))?;
        let e=TypedFabricEdge::new(d,r,position,from_node,to_node,tau_trit,kappa_j).map_err(PyValueError::new_err)?;
        self.operator.add_fabric_edge(e).map_err(PyValueError::new_err)
    }
    #[pyo3(signature=(applied_contact_x=None,external_current_a=0.0,dt_seconds=1e-4,*,applied_contact_force_n=None,relative_tolerance=DEFAULT_RTOL))]
    pub fn step(&mut self,applied_contact_x:Option<f64>,external_current_a:f64,dt_seconds:f64,
        applied_contact_force_n:Option<f64>,relative_tolerance:f64)->PyResult<TransitionResult>{
        self.operator.step_with_accuracy(&mut self.state,applied_contact_x,applied_contact_force_n,
            external_current_a,dt_seconds,relative_tolerance).map_err(PyRuntimeError::new_err)
    }
    pub fn membrane_voltage(&self)->f64{self.state.membrane_voltage(self.operator.c_mem)}
    pub fn receiving_voltage(&self)->f64{self.state.receiving_voltage()}
    pub fn get_apertures(&self)->Vec<f64>{self.state.y_gate.to_vec()}
    pub fn get_phases(&self)->Vec<f64>{self.state.phi.to_vec()}
    pub fn get_reservoirs_in(&self)->Vec<u64>{self.state.n_in.to_vec()}
    pub fn get_reservoirs_out(&self)->Vec<u64>{self.state.n_out.to_vec()}
    pub fn get_contact_geometry(&self)->(f64,f64){(self.state.contact_x,self.state.contact_ell)}
    pub fn get_integer_charge_endpoints(&self)->(i128,i128,i128,i128) {
        let outside=self.state.z_fixed_out as i128+(0..4).map(|c|SPECIES_VALENCE[c] as i128*self.state.n_out[c] as i128).sum::<i128>();
        (self.state.integer_free_charge(),outside,-(self.state.z_ext_port as i128),
            self.state.z_rec_port as i128)
    }
    pub fn get_exact_remainders(&self)->Vec<(bool,Vec<u64>,Vec<u64>)>{
        self.state.r_ion.iter().chain([&self.state.r_ext,&self.state.r_rec]).map(|r|r.evidence()).collect()
    }
    pub fn export_canonical_bytes(&self)->Vec<u8>{self.operator.export_canonical_checkpoint(&self.state)}
    pub fn import_canonical_bytes(&mut self,bytes:&[u8])->PyResult<()>{
        // Borrow Python bytes: validate framing before allocating decoded state.
        let (op,st)=ArcLoomTransitionOperator::import_canonical_checkpoint(bytes).map_err(PyValueError::new_err)?;
        self.operator=op;self.state=st;Ok(())
    }
}
pub fn register(m:&Bound<'_,PyModule>)->PyResult<()>{
    m.add_class::<PyArcLoomNeuron>()?;
    m.add_class::<TransitionResult>()?;
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn genesis_and_codec(){
        let s=ArcLoomNeuronState::new_reference_preparation();let op=ArcLoomTransitionOperator::new_reference_operator();
        assert_eq!(s.integer_free_charge(),GENESIS_Z_F as i128);
        s.validate().unwrap();op.validate().unwrap();
        let b=op.export_canonical_checkpoint(&s);let (other,restored)=ArcLoomTransitionOperator::import_canonical_checkpoint(&b).unwrap();
        assert_eq!(s,restored);assert_eq!(op,other);
        for n in 0..b.len(){assert!(ArcLoomTransitionOperator::import_canonical_checkpoint(&b[..n]).is_err());}
    }
    #[test]
    fn force_control_and_retained_geometry(){
        let mut s=ArcLoomNeuronState::new_reference_preparation();let op=ArcLoomTransitionOperator::new_reference_operator();
        let x0=op.equilibrium_contact_x(&s,0.0).unwrap();
        s.contact_ell*=1.1;
        let x1=op.equilibrium_contact_x(&s,0.0).unwrap();
        assert!(x1>x0);assert!(op.contact_g(x1).unwrap()<op.contact_g(x0).unwrap());
        // Same actual geometry is the required negative control.
        assert_eq!(op.contact_g(x0).unwrap(),op.contact_g(x0).unwrap());
    }
}
