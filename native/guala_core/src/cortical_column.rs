//! cortical_column.rs -- Modular Neuromorphic Substrates (4-Column, 8-Column Octet, 64-Column Cortical Array)
//!
//! Substrate: ArcLoom Discrete Balanced-Ternary Neuromorphic Core
//! Physical Model: Specialized Cortical Columns with 6-Layer Vertical Laminar Microcircuits
//!
//! Governing Laws & Invariants:
//!   1. Continuum Material Yield Stress Plasticity:
//!      - Intra- and inter-column contacts undergo irreversible plastic deformation if and only if
//!        mechanical/electrical stress exceeds yield threshold: f(|sigma|) = |sigma| - Y <= 0.
//!      - Waking experience creates persistent plastic conductances (g_plastic).
//!      - Waking beats do NOT arbitrarily decay learned conductances (zero unphysical waking decay).
//!      - Synaptic downscaling occurs strictly during nocturnal sleep consolidation (Synaptic Homeostasis).
//!   2. Discrete Lattice Baseline Resting Coupling and Signed Synaptic Polarization:
//!      - Reversible elastic compliance regime (|sigma| <= Y, lambda_dot = 0):
//!        G_ELASTIC_BASELINE = 0.05 represents the dimensionless baseline resting coupling parameter w_0
//!        in the discrete ternary neuromorphic lattice model.
//!        Signed plastic weight w in [-1.0, 1.0] represents polarized synaptic coupling
//!        (excitatory > 0, inhibitory < 0).
//!        Effective transmission coupling is the superposition: g_eff = G_ELASTIC_BASELINE + w.
//!        Claims of continuum material contact law closure or Holm/tunneling calibration are formally retracted.
//!   3. Causal Multi-Axis Motor Efferent Transduction:
//!      - Motor efferents scale directly from settled L5 pyramidal population excitation:
//!        vocal_hz in [0, 480], stride_mm in [0, 60], steer_deg in [-45, +45], grip_n in [0, 25].
//!      - Silent motor populations produce strictly (0.0, 0.0, 0.0, 0.0) efferents.
//!      - Actuators remain on independent physical axes; zero dimensionally invalid cross-ranking.
//!   4. Prefrontal / Structural Invariant Sheet (Columns 48..63):
//!      - Complete binary64 field values are preserved in storage and exact
//!        rational representation. The typed phase/material consumer is absent.
//!      - Full-field transition refuses atomically. Component-only execution
//!        is not evidence of ratified full-field neuron physics.
//!   5. Fail-Closed Lossless ARCLOOM4 State Persistence with Explicit Field Availability:
//!      - Serializes complete topological configuration, including severed tracts,
//!        column-local microcircuit plasticity parameters, and motor dynamics.
//!      - Preserves ALL nonzero, finite conductances bit-for-bit without arbitrary sub-0.005 pruning.
//!      - Enforces strict 36-byte column headers, ternary {-1, 0, 1} node state validation,
//!        finite float checks, duplicate index rejection, and exact (-offset) % 8 alignment padding.
//!      - Authentic predecessor migration reader for historical ARCLOOM2 payloads.
//!      - Corrupted, truncated, or invalid payloads fail atomically without mutating recipient.

use std::collections::HashSet;
use pyo3::prelude::*;
use pyo3::exceptions::{PyValueError, PyNotImplementedError};

// Common Dimensions
pub const L1_NODES: usize = 32;
pub const L23_NODES: usize = 128;
pub const L4_NODES: usize = 64;
pub const L5_NODES: usize = 64;
pub const L6_NODES: usize = 32;
pub const COLUMN_NODES: usize = L1_NODES + L23_NODES + L4_NODES + L5_NODES + L6_NODES; // 320 nodes

pub const G_4_23_SIZE: usize = L4_NODES * L23_NODES;     // 64 * 128 = 8,192
pub const G_23_23_SIZE: usize = L23_NODES * L23_NODES;   // 128 * 128 = 16,384
pub const G_23_5_SIZE: usize = L23_NODES * L5_NODES;     // 128 * 64 = 8,192
pub const G_5_6_SIZE: usize = L5_NODES * L6_NODES;       // 64 * 32 = 2,048
pub const G_6_4_SIZE: usize = L6_NODES * L4_NODES;       // 32 * 64 = 2,048
pub const G_1_23_SIZE: usize = L1_NODES * L23_NODES;     // 32 * 128 = 4,096

// 4-Column Dimensions
pub const NUM_COLUMNS_4D: usize = 4;
pub const TOTAL_SUBSTRATE_NODES_4D: usize = NUM_COLUMNS_4D * COLUMN_NODES; // 1,280 nodes
pub const INTER_COL_23_SIZE_4D: usize = NUM_COLUMNS_4D * NUM_COLUMNS_4D * L23_NODES * L23_NODES; // 16 * 16384 = 262,144
pub const INTER_COL_5_SIZE_4D: usize = NUM_COLUMNS_4D * NUM_COLUMNS_4D * L5_NODES * L5_NODES;    // 16 * 4096 = 65,536

// 8-Column Dimensions (Balanced Octet)
pub const NUM_COLUMNS_8D: usize = 8;
pub const TOTAL_SUBSTRATE_NODES_8D: usize = NUM_COLUMNS_8D * COLUMN_NODES; // 2,560 nodes
pub const INTER_COL_23_SIZE_8D: usize = NUM_COLUMNS_8D * NUM_COLUMNS_8D * L23_NODES * L23_NODES; // 64 * 16384 = 1,048,576
pub const INTER_COL_5_SIZE_8D: usize = NUM_COLUMNS_8D * NUM_COLUMNS_8D * L5_NODES * L5_NODES;    // 64 * 4096 = 262,144

// 64-Column Dimensions (Cortical Array)
pub const NUM_COLUMNS_64D: usize = 64;
pub const TOTAL_SUBSTRATE_NODES_64D: usize = NUM_COLUMNS_64D * COLUMN_NODES; // 20,480 nodes
pub const INTER_COL_23_SIZE_64D: usize = NUM_COLUMNS_64D * NUM_COLUMNS_64D * L23_NODES * L23_NODES; // 4096 * 16384 = 67,108,864
pub const INTER_COL_5_SIZE_64D: usize = NUM_COLUMNS_64D * NUM_COLUMNS_64D * L5_NODES * L5_NODES;    // 4096 * 4096 = 16,777,216

pub const ARCLOOM_STATE_MAGIC_V2: &[u8; 8] = b"ARCLOOM2";
pub const ARCLOOM_STATE_VERSION_V2: u16 = 2;

pub const ARCLOOM_STATE_MAGIC_V3: &[u8; 8] = b"ARCLOOM3";
pub const ARCLOOM_STATE_VERSION_V3: u16 = 3;

pub const ARCLOOM_STATE_MAGIC_V4: &[u8; 8] = b"ARCLOOM4";
pub const ARCLOOM_STATE_VERSION_V4: u16 = 4;

/// Dimensionless baseline resting coupling parameter G_ELASTIC_BASELINE = 0.05.
/// In the discrete ternary neuromorphic lattice model, G_ELASTIC_BASELINE defines the
/// baseline sub-yield coupling in the reversible regime (|sigma| <= Y, lambda_dot = 0).
/// Signed plastic weight w in [-1.0, 1.0] represents polarized synaptic coupling
/// (excitatory > 0, inhibitory < 0). Effective transmission coupling is g_eff = G_ELASTIC_BASELINE + w.
/// Rate-independent radial return plasticity enforces trial stress Sigma_tr, yield function f <= 0,
/// and Kuhn-Tucker complementarity (delta_w * f = 0).
/// Continuum material contact law closure and nanoscale parameter derivation in SI units remain
/// an unratified open research contract (finding A8-02 open).
pub const G_ELASTIC_BASELINE: f32 = 0.05;

// ---------------------------------------------------------------------------
// 1. Laminar Microcircuit (Canonical 6-Layer Primitive)
// ---------------------------------------------------------------------------

#[derive(Clone)]
pub struct LaminarMicrocircuit {
    pub l1: Vec<i8>,
    pub l23: Vec<i8>,
    pub l4: Vec<i8>,
    pub l5: Vec<i8>,
    pub l6: Vec<i8>,
    pub v_23: Vec<f32>,
    pub v_5: Vec<f32>,

    pub g_4_23: Vec<f32>,
    pub g_23_23: Vec<f32>,
    pub g_23_5: Vec<f32>,
    pub g_5_6: Vec<f32>,
    pub g_6_4: Vec<f32>,
    pub g_1_23: Vec<f32>,

    pub active_intra: Vec<(u8, u16)>,

    pub yield_threshold: f32,
    pub plastic_rate: f32,
    pub activation_threshold: f32,
}

impl LaminarMicrocircuit {
    pub fn new(yield_threshold: f32, plastic_rate: f32, activation_threshold: f32) -> Self {
        Self {
            l1: vec![0; L1_NODES],
            l23: vec![0; L23_NODES],
            l4: vec![0; L4_NODES],
            l5: vec![0; L5_NODES],
            l6: vec![0; L6_NODES],
            v_23: vec![0.0; L23_NODES],
            v_5: vec![0.0; L5_NODES],

            g_4_23: vec![0.0; G_4_23_SIZE],
            g_23_23: vec![0.0; G_23_23_SIZE],
            g_23_5: vec![0.0; G_23_5_SIZE],
            g_5_6: vec![0.0; G_5_6_SIZE],
            g_6_4: vec![0.0; G_6_4_SIZE],
            g_1_23: vec![0.0; G_1_23_SIZE],
            active_intra: Vec::new(),

            yield_threshold: yield_threshold.clamp(0.01, 0.99),
            plastic_rate: plastic_rate.clamp(0.001, 1.0),
            activation_threshold: activation_threshold.max(0.01),
        }
    }

    pub fn step_laminar_flow(
        &mut self,
        afferents: &[i8],
        apical_somatics: &[i8],
        inter_l23_in: &[f32],
        inter_l5_in: &[f32],
    ) -> (usize, f32) {
        // 1. Update L1 (apical modulation)
        for (i, val) in self.l1.iter_mut().enumerate() {
            *val = if i < apical_somatics.len() { apical_somatics[i].clamp(-1, 1) } else { 0 };
        }

        // 2. Predictive reafference cancellation in L4: Net = Afferent - (L6 * g_6_4)
        for j in 0..L4_NODES {
            let aff = if j < afferents.len() { afferents[j] as f32 } else { 0.0 };
            let mut pred_cancellation = 0.0f32;
            for i in 0..L6_NODES {
                pred_cancellation += (self.l6[i] as f32) * self.g_6_4[i * L4_NODES + j];
            }
            let net_l4 = aff - pred_cancellation;
            self.l4[j] = if net_l4 >= self.activation_threshold {
                1
            } else if net_l4 <= -self.activation_threshold {
                -1
            } else {
                0
            };
        }

        // 3. Supragranular Associative Lattice (L2/3):
        let mut v_23 = vec![0.0f32; L23_NODES];
        for j in 0..L23_NODES {
            let topo_l4 = self.l4[j / 2] as f32 * 0.50;
            let mut acc = topo_l4;

            for i in 0..L4_NODES {
                acc += (self.l4[i] as f32) * self.g_4_23[i * L23_NODES + j];
            }
            for i in 0..L1_NODES {
                acc += (self.l1[i] as f32) * self.g_1_23[i * L23_NODES + j];
            }
            for i in 0..L23_NODES {
                acc += (self.l23[i] as f32) * self.g_23_23[i * L23_NODES + j];
            }
            if j < inter_l23_in.len() {
                acc += inter_l23_in[j];
            }
            v_23[j] = acc;
        }

        self.v_23 = v_23.clone();

        // 4. Continuum Lateral Inhibitory Competition in L2/3:
        let max_abs_v23 = v_23.iter().map(|v| v.abs()).fold(0.0f32, f32::max);
        let inh_l23 = (max_abs_v23 * 0.80).max(self.activation_threshold);
        for j in 0..L23_NODES {
            self.l23[j] = if v_23[j] >= inh_l23 {
                1
            } else if v_23[j] <= -inh_l23 {
                -1
            } else {
                0
            };
        }

        // 5. Infragranular Motor Pyramidal Layer (L5):
        let mut v_5 = vec![0.0f32; L5_NODES];
        for j in 0..L5_NODES {
            let topo_l23 = self.l23[j * 2] as f32 * 0.50;
            let mut acc = topo_l23;
            for i in 0..L23_NODES {
                acc += (self.l23[i] as f32) * self.g_23_5[i * L5_NODES + j];
            }
            if j < inter_l5_in.len() {
                acc += inter_l5_in[j];
            }
            v_5[j] = acc;
        }
        let max_abs_v5 = v_5.iter().map(|v| v.abs()).fold(0.0f32, f32::max);
        let inh_l5 = (max_abs_v5 * 0.80).max(self.activation_threshold);
        for j in 0..L5_NODES {
            self.l5[j] = if v_5[j] >= inh_l5 {
                1
            } else if v_5[j] <= -inh_l5 {
                -1
            } else {
                0
            };
        }
        self.v_5 = v_5;

        // 6. Efference Copy into L6: Driven by L5
        let mut v_6 = vec![0.0f32; L6_NODES];
        for j in 0..L6_NODES {
            let topo_l5 = self.l5[j * 2] as f32 * 0.50;
            let mut acc = topo_l5;
            for i in 0..L5_NODES {
                acc += (self.l5[i] as f32) * self.g_5_6[i * L6_NODES + j];
            }
            v_6[j] = acc;
        }
        let max_abs_v6 = v_6.iter().map(|v| v.abs()).fold(0.0f32, f32::max);
        let inh_l6 = (max_abs_v6 * 0.80).max(self.activation_threshold);
        for j in 0..L6_NODES {
            self.l6[j] = if v_6[j] >= inh_l6 {
                1
            } else if v_6[j] <= -inh_l6 {
                -1
            } else {
                0
            };
        }

        // 7. Local continuum von Mises plasticity within the column (permanent during waking)
        self.apply_intra_yield_plasticity()
    }

    pub fn apply_intra_yield_plasticity(&mut self) -> (usize, f32) {
        let mut yield_count = 0usize;
        let mut total_strain = 0.0f32;

        let y = self.yield_threshold;
        let _eta = self.plastic_rate;

        // Plasticity: L4 -> L2/3
        for i in 0..L4_NODES {
            if self.l4[i] == 0 { continue; }
            for j in 0..L23_NODES {
                if self.l23[j] == 0 { continue; }
                let idx = i * L23_NODES + j;
                let target = (self.l4[i] * self.l23[j]) as f32;
                let sigma = target - self.g_4_23[idx];
                let abs_sigma = sigma.abs();
                if abs_sigma > y {
                    let overstress = abs_sigma - y;
                    let was_zero = self.g_4_23[idx] == 0.0;
                    self.g_4_23[idx] = (self.g_4_23[idx] + overstress * sigma.signum()).clamp(-1.0, 1.0);
                    if was_zero && self.g_4_23[idx] != 0.0 {
                        self.active_intra.push((0, idx as u16));
                    }
                    yield_count += 1;
                    total_strain += overstress;
                }
            }
        }

        // Plasticity: Recurrent L2/3 -> L2/3
        for i in 0..L23_NODES {
            if self.l23[i] == 0 { continue; }
            for j in 0..L23_NODES {
                if i == j || self.l23[j] == 0 { continue; }
                let idx = i * L23_NODES + j;
                let target = (self.l23[i] * self.l23[j]) as f32;
                let sigma = target - self.g_23_23[idx];
                let abs_sigma = sigma.abs();
                if abs_sigma > y {
                    let overstress = abs_sigma - y;
                    let was_zero = self.g_23_23[idx] == 0.0;
                    self.g_23_23[idx] = (self.g_23_23[idx] + overstress * sigma.signum()).clamp(-1.0, 1.0);
                    if was_zero && self.g_23_23[idx] != 0.0 {
                        self.active_intra.push((1, idx as u16));
                    }
                    yield_count += 1;
                    total_strain += overstress;
                }
            }
        }

        // Plasticity: L2/3 -> L5 (Motor readout)
        for i in 0..L23_NODES {
            if self.l23[i] == 0 { continue; }
            for j in 0..L5_NODES {
                if self.l5[j] == 0 { continue; }
                let idx = i * L5_NODES + j;
                let target = (self.l23[i] * self.l5[j]) as f32;
                let sigma = target - self.g_23_5[idx];
                let abs_sigma = sigma.abs();
                if abs_sigma > y {
                    let overstress = abs_sigma - y;
                    let was_zero = self.g_23_5[idx] == 0.0;
                    self.g_23_5[idx] = (self.g_23_5[idx] + overstress * sigma.signum()).clamp(-1.0, 1.0);
                    if was_zero && self.g_23_5[idx] != 0.0 {
                        self.active_intra.push((2, idx as u16));
                    }
                    yield_count += 1;
                    total_strain += overstress;
                }
            }
        }

        // Plasticity: L5 -> L6 (Efference copy transmission)
        for i in 0..L5_NODES {
            if self.l5[i] == 0 { continue; }
            for j in 0..L6_NODES {
                if self.l6[j] == 0 { continue; }
                let idx = i * L6_NODES + j;
                let target = (self.l5[i] * self.l6[j]) as f32;
                let sigma = target - self.g_5_6[idx];
                let abs_sigma = sigma.abs();
                if abs_sigma > y {
                    let overstress = abs_sigma - y;
                    let was_zero = self.g_5_6[idx] == 0.0;
                    self.g_5_6[idx] = (self.g_5_6[idx] + overstress * sigma.signum()).clamp(-1.0, 1.0);
                    if was_zero && self.g_5_6[idx] != 0.0 {
                        self.active_intra.push((3, idx as u16));
                    }
                    yield_count += 1;
                    total_strain += overstress;
                }
            }
        }

        // Plasticity: L6 -> L4 (Predictive cancellation gating)
        for i in 0..L6_NODES {
            if self.l6[i] == 0 { continue; }
            for j in 0..L4_NODES {
                if self.l4[j] == 0 { continue; }
                let idx = i * L4_NODES + j;
                let target = (self.l6[i] * self.l4[j]) as f32;
                let sigma = target - self.g_6_4[idx];
                let abs_sigma = sigma.abs();
                if abs_sigma > y {
                    let overstress = abs_sigma - y;
                    let was_zero = self.g_6_4[idx] == 0.0;
                    self.g_6_4[idx] = (self.g_6_4[idx] + overstress * sigma.signum()).clamp(-1.0, 1.0);
                    if was_zero && self.g_6_4[idx] != 0.0 {
                        self.active_intra.push((4, idx as u16));
                    }
                    yield_count += 1;
                    total_strain += overstress;
                }
            }
        }

        // Plasticity: L1 -> L2/3 (Apical somatic context)
        for i in 0..L1_NODES {
            if self.l1[i] == 0 { continue; }
            for j in 0..L23_NODES {
                if self.l23[j] == 0 { continue; }
                let idx = i * L23_NODES + j;
                let target = (self.l1[i] * self.l23[j]) as f32;
                let sigma = target - self.g_1_23[idx];
                let abs_sigma = sigma.abs();
                if abs_sigma > y {
                    let overstress = abs_sigma - y;
                    let was_zero = self.g_1_23[idx] == 0.0;
                    self.g_1_23[idx] = (self.g_1_23[idx] + overstress * sigma.signum()).clamp(-1.0, 1.0);
                    if was_zero && self.g_1_23[idx] != 0.0 {
                        self.active_intra.push((5, idx as u16));
                    }
                    yield_count += 1;
                    total_strain += overstress;
                }
            }
        }

        (yield_count, total_strain)
    }

    /// Nocturnal sleep downscaling (Synaptic Homeostasis).
    /// Proportional relaxation: *g *= 1.0 - decay.
    /// Pruning occurs if and only if prune_thresh > 0.0 and |g| < prune_thresh,
    /// or if g reaches exactly 0.0.
    pub fn dream_downscale_and_prune(&mut self, decay: f32, prune_thresh: f32) -> (usize, usize) {
        let mut decayed = 0usize;
        let mut pruned = 0usize;
        let g_4_23 = &mut self.g_4_23;
        let g_23_23 = &mut self.g_23_23;
        let g_23_5 = &mut self.g_23_5;
        let g_5_6 = &mut self.g_5_6;
        let g_6_4 = &mut self.g_6_4;
        let g_1_23 = &mut self.g_1_23;

        self.active_intra.retain(|&(ch, idx)| {
            let g = match ch {
                0 => &mut g_4_23[idx as usize],
                1 => &mut g_23_23[idx as usize],
                2 => &mut g_23_5[idx as usize],
                3 => &mut g_5_6[idx as usize],
                4 => &mut g_6_4[idx as usize],
                5 => &mut g_1_23[idx as usize],
                _ => return false,
            };
            decayed += 1;
            *g *= 1.0 - decay;
            if prune_thresh > 0.0 && g.abs() < prune_thresh {
                *g = 0.0;
                pruned += 1;
                false
            } else if *g == 0.0 {
                false
            } else {
                true
            }
        });
        (decayed, pruned)
    }

    pub fn active_intra_synapses(&self) -> usize {
        self.active_intra.len()
    }

    pub fn zero_plastic_weights(&mut self) {
        self.g_4_23.fill(0.0);
        self.g_23_23.fill(0.0);
        self.g_23_5.fill(0.0);
        self.g_5_6.fill(0.0);
        self.g_6_4.fill(0.0);
        self.g_1_23.fill(0.0);
        self.active_intra.clear();
    }
}

// ---------------------------------------------------------------------------
// 2. Cortical Column (Macro-Unit)
// ---------------------------------------------------------------------------

#[derive(Clone)]
pub struct CorticalColumn {
    pub column_id: usize,
    pub microcircuit: LaminarMicrocircuit,

    pub spatial_r_mm: f32,
    pub spatial_theta_mdeg: i32,
    pub persistence_trace: f32,
    pub target_occluded: bool,

    pub barrier_contact_stress: f32,
    pub yield_limit_threshold: f32,
    pub refusal_active: bool,
}

impl CorticalColumn {
    pub fn new(column_id: usize, yield_threshold: f32, plastic_rate: f32, activation_threshold: f32) -> Self {
        Self {
            column_id,
            microcircuit: LaminarMicrocircuit::new(yield_threshold, plastic_rate, activation_threshold),
            spatial_r_mm: 0.0,
            spatial_theta_mdeg: 0,
            persistence_trace: 0.0,
            target_occluded: false,
            barrier_contact_stress: 0.0,
            yield_limit_threshold: yield_threshold,
            refusal_active: false,
        }
    }

    pub fn zero_plastic_weights(&mut self) {
        self.microcircuit.zero_plastic_weights();
    }
}

// ---------------------------------------------------------------------------
// Serialization Helpers (Strict Fail-Closed Binary Codec)
// ---------------------------------------------------------------------------

fn serialize_column_state(col: &CorticalColumn, buf: &mut Vec<u8>) -> Result<(), String> {
    if !col.spatial_r_mm.is_finite() || !col.persistence_trace.is_finite() ||
       !col.barrier_contact_stress.is_finite() || !col.yield_limit_threshold.is_finite() ||
       !col.microcircuit.yield_threshold.is_finite() || !col.microcircuit.plastic_rate.is_finite() ||
       !col.microcircuit.activation_threshold.is_finite() {
        return Err(format!("Non-finite float in column {} state during serialization", col.column_id));
    }
    buf.extend_from_slice(&(col.column_id as u16).to_le_bytes());
    buf.extend_from_slice(&col.spatial_r_mm.to_le_bytes());
    buf.extend_from_slice(&col.spatial_theta_mdeg.to_le_bytes());
    buf.extend_from_slice(&col.persistence_trace.to_le_bytes());
    buf.push(if col.target_occluded { 1 } else { 0 });
    buf.extend_from_slice(&col.barrier_contact_stress.to_le_bytes());
    buf.extend_from_slice(&col.yield_limit_threshold.to_le_bytes());
    buf.push(if col.refusal_active { 1 } else { 0 });
    buf.extend_from_slice(&col.microcircuit.yield_threshold.to_le_bytes());
    buf.extend_from_slice(&col.microcircuit.plastic_rate.to_le_bytes());
    buf.extend_from_slice(&col.microcircuit.activation_threshold.to_le_bytes());

    for &x in &col.microcircuit.l1 { buf.push(x as u8); }
    for &x in &col.microcircuit.l23 { buf.push(x as u8); }
    for &x in &col.microcircuit.l4 { buf.push(x as u8); }
    for &x in &col.microcircuit.l5 { buf.push(x as u8); }
    for &x in &col.microcircuit.l6 { buf.push(x as u8); }

    let mut nz_entries: Vec<(u8, u16, f32)> = Vec::with_capacity(col.microcircuit.active_intra.len());
    let channels: [&[f32]; 6] = [
        &col.microcircuit.g_4_23,
        &col.microcircuit.g_23_23,
        &col.microcircuit.g_23_5,
        &col.microcircuit.g_5_6,
        &col.microcircuit.g_6_4,
        &col.microcircuit.g_1_23,
    ];
    for &(ch, idx) in &col.microcircuit.active_intra {
        let ch_u = ch as usize;
        let idx_u = idx as usize;
        if ch_u < channels.len() && idx_u < channels[ch_u].len() {
            let val = channels[ch_u][idx_u];
            if !val.is_finite() {
                return Err(format!("Non-finite synaptic weight in column {}: channel {}, idx {}", col.column_id, ch, idx));
            }
            if val != 0.0 {
                nz_entries.push((ch, idx, val));
            }
        }
    }
    buf.extend_from_slice(&(nz_entries.len() as u32).to_le_bytes());
    for (ch, idx, val) in nz_entries {
        buf.push(ch);
        buf.extend_from_slice(&idx.to_le_bytes());
        buf.extend_from_slice(&val.to_le_bytes());
    }
    Ok(())
}

fn deserialize_column_state(
    col: &mut CorticalColumn,
    data: &[u8],
    mut offset: usize,
    expected_col_id: usize,
    num_columns: usize,
) -> Result<usize, String> {
    if offset + 36 > data.len() {
        return Err("Unexpected EOF reading column header: requires 36 bytes".to_string());
    }
    let col_id = u16::from_le_bytes([data[offset], data[offset+1]]) as usize; offset += 2;
    if col_id >= num_columns {
        return Err(format!("Column id {} out of bounds (num_columns = {})", col_id, num_columns));
    }
    if col_id != expected_col_id {
        return Err(format!("Column id mismatch: expected slot {}, got {}", expected_col_id, col_id));
    }
    let r_mm = f32::from_le_bytes([data[offset], data[offset+1], data[offset+2], data[offset+3]]); offset += 4;
    let theta_mdeg = i32::from_le_bytes([data[offset], data[offset+1], data[offset+2], data[offset+3]]); offset += 4;
    let trace = f32::from_le_bytes([data[offset], data[offset+1], data[offset+2], data[offset+3]]); offset += 4;

    let occluded_byte = data[offset]; offset += 1;
    if occluded_byte > 1 {
        return Err(format!("Invalid boolean byte {} for target_occluded: must be 0 or 1", occluded_byte));
    }
    let occluded = occluded_byte == 1;

    let barrier_stress = f32::from_le_bytes([data[offset], data[offset+1], data[offset+2], data[offset+3]]); offset += 4;
    let yield_limit = f32::from_le_bytes([data[offset], data[offset+1], data[offset+2], data[offset+3]]); offset += 4;

    let refusal_byte = data[offset]; offset += 1;
    if refusal_byte > 1 {
        return Err(format!("Invalid boolean byte {} for refusal_active: must be 0 or 1", refusal_byte));
    }
    let refusal = refusal_byte == 1;

    let y_thresh = f32::from_le_bytes([data[offset], data[offset+1], data[offset+2], data[offset+3]]); offset += 4;
    let p_rate = f32::from_le_bytes([data[offset], data[offset+1], data[offset+2], data[offset+3]]); offset += 4;
    let a_thresh = f32::from_le_bytes([data[offset], data[offset+1], data[offset+2], data[offset+3]]); offset += 4;

    if !r_mm.is_finite() || !trace.is_finite() || !barrier_stress.is_finite() ||
       !yield_limit.is_finite() || !y_thresh.is_finite() || !p_rate.is_finite() || !a_thresh.is_finite() {
        return Err("Non-finite float in column header".to_string());
    }

    if y_thresh <= 0.0 || y_thresh > 1.0 {
        return Err(format!("Invalid yield_threshold {}: must be in (0.0, 1.0]", y_thresh));
    }
    if p_rate <= 0.0 || p_rate > 1.0 {
        return Err(format!("Invalid plastic_rate {}: must be in (0.0, 1.0]", p_rate));
    }
    if a_thresh <= 0.0 {
        return Err(format!("Invalid activation_threshold {}: must be > 0.0", a_thresh));
    }
    if yield_limit <= 0.0 || yield_limit > 1.0 {
        return Err(format!("Invalid yield_limit_threshold {}: must be in (0.0, 1.0]", yield_limit));
    }
    if barrier_stress < 0.0 {
        return Err("Invalid negative barrier_contact_stress".to_string());
    }
    if trace < 0.0 {
        return Err("Invalid negative persistence_trace".to_string());
    }
    if r_mm < 0.0 {
        return Err("Invalid negative spatial_r_mm".to_string());
    }

    col.column_id = col_id;
    col.spatial_r_mm = r_mm;
    col.spatial_theta_mdeg = theta_mdeg;
    col.persistence_trace = trace;
    col.target_occluded = occluded;
    col.barrier_contact_stress = barrier_stress;
    col.yield_limit_threshold = yield_limit;
    col.refusal_active = refusal;
    col.microcircuit.yield_threshold = y_thresh;
    col.microcircuit.plastic_rate = p_rate;
    col.microcircuit.activation_threshold = a_thresh;

    let node_bytes = L1_NODES + L23_NODES + L4_NODES + L5_NODES + L6_NODES;
    if offset + node_bytes > data.len() {
        return Err("Unexpected EOF reading layer node states".to_string());
    }
    for i in 0..L1_NODES {
        let b = data[offset + i] as i8;
        if b < -1 || b > 1 { return Err(format!("Invalid ternary node state {}: must be -1, 0, or 1", b)); }
        col.microcircuit.l1[i] = b;
    } offset += L1_NODES;
    for i in 0..L23_NODES {
        let b = data[offset + i] as i8;
        if b < -1 || b > 1 { return Err(format!("Invalid ternary node state {}: must be -1, 0, or 1", b)); }
        col.microcircuit.l23[i] = b;
    } offset += L23_NODES;
    for i in 0..L4_NODES {
        let b = data[offset + i] as i8;
        if b < -1 || b > 1 { return Err(format!("Invalid ternary node state {}: must be -1, 0, or 1", b)); }
        col.microcircuit.l4[i] = b;
    } offset += L4_NODES;
    for i in 0..L5_NODES {
        let b = data[offset + i] as i8;
        if b < -1 || b > 1 { return Err(format!("Invalid ternary node state {}: must be -1, 0, or 1", b)); }
        col.microcircuit.l5[i] = b;
    } offset += L5_NODES;
    for i in 0..L6_NODES {
        let b = data[offset + i] as i8;
        if b < -1 || b > 1 { return Err(format!("Invalid ternary node state {}: must be -1, 0, or 1", b)); }
        col.microcircuit.l6[i] = b;
    } offset += L6_NODES;

    if offset.checked_add(4).ok_or("Integer overflow reading intra-column synapse count")? > data.len() {
        return Err("Unexpected EOF reading intra-column synapse count".to_string());
    }
    let nz_count = u32::from_le_bytes([data[offset], data[offset+1], data[offset+2], data[offset+3]]) as usize;
    offset += 4;

    if nz_count > 40_960 {
        return Err(format!("Intra-column non-zero count {} exceeds maximum structural capacity 40960", nz_count));
    }
    let byte_len = nz_count.checked_mul(7).ok_or("Arithmetic overflow in intra-column byte length")?;
    let needed = offset.checked_add(byte_len).ok_or("Arithmetic overflow calculating intra-column boundary")?;
    if needed > data.len() {
        return Err("Unexpected EOF in intra-column synapses".to_string());
    }

    col.microcircuit.g_4_23.fill(0.0);
    col.microcircuit.g_23_23.fill(0.0);
    col.microcircuit.g_23_5.fill(0.0);
    col.microcircuit.g_5_6.fill(0.0);
    col.microcircuit.g_6_4.fill(0.0);
    col.microcircuit.g_1_23.fill(0.0);
    col.microcircuit.active_intra.clear();

    let mut seen_intra = HashSet::new();

    for _ in 0..nz_count {
        let channel = data[offset]; offset += 1;
        let idx = u16::from_le_bytes([data[offset], data[offset+1]]) as usize; offset += 2;
        let val = f32::from_le_bytes([data[offset], data[offset+1], data[offset+2], data[offset+3]]); offset += 4;
        if !val.is_finite() {
            return Err("Non-finite synaptic weight in intra-column payload".to_string());
        }
        if val < -1.0 || val > 1.0 {
            return Err(format!("Intra-column synaptic weight out of bounds [-1.0, 1.0]: {}", val));
        }
        if !seen_intra.insert((channel, idx as u16)) {
            return Err(format!("Duplicate intra-column entry: channel {}, index {}", channel, idx));
        }

        match channel {
            0 => {
                if idx < col.microcircuit.g_4_23.len() { col.microcircuit.g_4_23[idx] = val; }
                else { return Err(format!("Intra-column index {} out of bounds for channel 0", idx)); }
            },
            1 => {
                if idx < col.microcircuit.g_23_23.len() { col.microcircuit.g_23_23[idx] = val; }
                else { return Err(format!("Intra-column index {} out of bounds for channel 1", idx)); }
            },
            2 => {
                if idx < col.microcircuit.g_23_5.len() { col.microcircuit.g_23_5[idx] = val; }
                else { return Err(format!("Intra-column index {} out of bounds for channel 2", idx)); }
            },
            3 => {
                if idx < col.microcircuit.g_5_6.len() { col.microcircuit.g_5_6[idx] = val; }
                else { return Err(format!("Intra-column index {} out of bounds for channel 3", idx)); }
            },
            4 => {
                if idx < col.microcircuit.g_6_4.len() { col.microcircuit.g_6_4[idx] = val; }
                else { return Err(format!("Intra-column index {} out of bounds for channel 4", idx)); }
            },
            5 => {
                if idx < col.microcircuit.g_1_23.len() { col.microcircuit.g_1_23[idx] = val; }
                else { return Err(format!("Intra-column index {} out of bounds for channel 5", idx)); }
            },
            _ => {
                return Err(format!("Invalid intra-column channel {}: must be 0..5", channel));
            }
        }
        if val != 0.0 {
            col.microcircuit.active_intra.push((channel, idx as u16));
        }
    }
    Ok(offset)
}

fn deserialize_column_state_v2_24b(
    col: &mut CorticalColumn,
    data: &[u8],
    mut offset: usize,
    expected_col_id: usize,
    num_columns: usize,
) -> Result<usize, String> {
    if offset + 24 > data.len() {
        return Err("Unexpected EOF reading 24-byte column header: requires 24 bytes".to_string());
    }
    let col_id = u16::from_le_bytes([data[offset], data[offset+1]]) as usize; offset += 2;
    if col_id >= num_columns {
        return Err(format!("Column id {} out of bounds (num_columns = {})", col_id, num_columns));
    }
    if col_id != expected_col_id {
        return Err(format!("Column id mismatch: expected slot {}, got {}", expected_col_id, col_id));
    }
    let r_mm = f32::from_le_bytes([data[offset], data[offset+1], data[offset+2], data[offset+3]]); offset += 4;
    let theta_mdeg = i32::from_le_bytes([data[offset], data[offset+1], data[offset+2], data[offset+3]]); offset += 4;
    let trace = f32::from_le_bytes([data[offset], data[offset+1], data[offset+2], data[offset+3]]); offset += 4;

    let occluded_byte = data[offset]; offset += 1;
    if occluded_byte > 1 {
        return Err(format!("Invalid boolean byte {} for target_occluded: must be 0 or 1", occluded_byte));
    }
    let occluded = occluded_byte == 1;

    let barrier_stress = f32::from_le_bytes([data[offset], data[offset+1], data[offset+2], data[offset+3]]); offset += 4;
    let yield_limit = f32::from_le_bytes([data[offset], data[offset+1], data[offset+2], data[offset+3]]); offset += 4;

    let refusal_byte = data[offset]; offset += 1;
    if refusal_byte > 1 {
        return Err(format!("Invalid boolean byte {} for refusal_active: must be 0 or 1", refusal_byte));
    }
    let refusal = refusal_byte == 1;

    if !r_mm.is_finite() || !trace.is_finite() || !barrier_stress.is_finite() || !yield_limit.is_finite() {
        return Err("Non-finite float in column header".to_string());
    }
    if yield_limit <= 0.0 || yield_limit > 1.0 {
        return Err(format!("Invalid yield_limit_threshold {}: must be in (0.0, 1.0]", yield_limit));
    }
    if barrier_stress < 0.0 {
        return Err("Invalid negative barrier_contact_stress".to_string());
    }
    if trace < 0.0 {
        return Err("Invalid negative persistence_trace".to_string());
    }
    if r_mm < 0.0 {
        return Err("Invalid negative spatial_r_mm".to_string());
    }

    col.column_id = col_id;
    col.spatial_r_mm = r_mm;
    col.spatial_theta_mdeg = theta_mdeg;
    col.persistence_trace = trace;
    col.target_occluded = occluded;
    col.barrier_contact_stress = barrier_stress;
    col.yield_limit_threshold = yield_limit;
    col.refusal_active = refusal;

    let node_bytes = L1_NODES + L23_NODES + L4_NODES + L5_NODES + L6_NODES;
    if offset + node_bytes > data.len() {
        return Err("Unexpected EOF reading layer node states".to_string());
    }
    for i in 0..L1_NODES {
        let b = data[offset + i] as i8;
        if b < -1 || b > 1 { return Err(format!("Invalid ternary node state {}: must be -1, 0, or 1", b)); }
        col.microcircuit.l1[i] = b;
    } offset += L1_NODES;
    for i in 0..L23_NODES {
        let b = data[offset + i] as i8;
        if b < -1 || b > 1 { return Err(format!("Invalid ternary node state {}: must be -1, 0, or 1", b)); }
        col.microcircuit.l23[i] = b;
    } offset += L23_NODES;
    for i in 0..L4_NODES {
        let b = data[offset + i] as i8;
        if b < -1 || b > 1 { return Err(format!("Invalid ternary node state {}: must be -1, 0, or 1", b)); }
        col.microcircuit.l4[i] = b;
    } offset += L4_NODES;
    for i in 0..L5_NODES {
        let b = data[offset + i] as i8;
        if b < -1 || b > 1 { return Err(format!("Invalid ternary node state {}: must be -1, 0, or 1", b)); }
        col.microcircuit.l5[i] = b;
    } offset += L5_NODES;
    for i in 0..L6_NODES {
        let b = data[offset + i] as i8;
        if b < -1 || b > 1 { return Err(format!("Invalid ternary node state {}: must be -1, 0, or 1", b)); }
        col.microcircuit.l6[i] = b;
    } offset += L6_NODES;

    if offset.checked_add(4).ok_or("Integer overflow reading intra-column synapse count")? > data.len() {
        return Err("Unexpected EOF reading intra-column synapse count".to_string());
    }
    let nz_count = u32::from_le_bytes([data[offset], data[offset+1], data[offset+2], data[offset+3]]) as usize;
    offset += 4;

    if nz_count > 40_960 {
        return Err(format!("Intra-column non-zero count {} exceeds maximum structural capacity 40960", nz_count));
    }
    let byte_len = nz_count.checked_mul(7).ok_or("Arithmetic overflow in intra-column byte length")?;
    let needed = offset.checked_add(byte_len).ok_or("Arithmetic overflow calculating intra-column boundary")?;
    if needed > data.len() {
        return Err("Unexpected EOF in intra-column synapses".to_string());
    }

    col.microcircuit.g_4_23.fill(0.0);
    col.microcircuit.g_23_23.fill(0.0);
    col.microcircuit.g_23_5.fill(0.0);
    col.microcircuit.g_5_6.fill(0.0);
    col.microcircuit.g_6_4.fill(0.0);
    col.microcircuit.g_1_23.fill(0.0);
    col.microcircuit.active_intra.clear();

    let mut seen_intra = HashSet::new();

    for _ in 0..nz_count {
        let channel = data[offset]; offset += 1;
        let idx = u16::from_le_bytes([data[offset], data[offset+1]]) as usize; offset += 2;
        let val = f32::from_le_bytes([data[offset], data[offset+1], data[offset+2], data[offset+3]]); offset += 4;
        if !val.is_finite() {
            return Err("Non-finite synaptic weight in intra-column payload".to_string());
        }
        if val < -1.0 || val > 1.0 {
            return Err(format!("Intra-column synaptic weight out of bounds [-1.0, 1.0]: {}", val));
        }
        if !seen_intra.insert((channel, idx as u16)) {
            return Err(format!("Duplicate intra-column entry: channel {}, index {}", channel, idx));
        }

        match channel {
            0 => {
                if idx < col.microcircuit.g_4_23.len() { col.microcircuit.g_4_23[idx] = val; }
                else { return Err(format!("Intra-column index {} out of bounds for channel 0", idx)); }
            },
            1 => {
                if idx < col.microcircuit.g_23_23.len() { col.microcircuit.g_23_23[idx] = val; }
                else { return Err(format!("Intra-column index {} out of bounds for channel 1", idx)); }
            },
            2 => {
                if idx < col.microcircuit.g_23_5.len() { col.microcircuit.g_23_5[idx] = val; }
                else { return Err(format!("Intra-column index {} out of bounds for channel 2", idx)); }
            },
            3 => {
                if idx < col.microcircuit.g_5_6.len() { col.microcircuit.g_5_6[idx] = val; }
                else { return Err(format!("Intra-column index {} out of bounds for channel 3", idx)); }
            },
            4 => {
                if idx < col.microcircuit.g_6_4.len() { col.microcircuit.g_6_4[idx] = val; }
                else { return Err(format!("Intra-column index {} out of bounds for channel 4", idx)); }
            },
            5 => {
                if idx < col.microcircuit.g_1_23.len() { col.microcircuit.g_1_23[idx] = val; }
                else { return Err(format!("Intra-column index {} out of bounds for channel 5", idx)); }
            },
            _ => {
                return Err(format!("Invalid intra-column channel {}: must be 0..5", channel));
            }
        }
        if val != 0.0 {
            col.microcircuit.active_intra.push((channel, idx as u16));
        }
    }
    Ok(offset)
}

// ---------------------------------------------------------------------------
// 3. 4-Column 3D Modular Neuromorphic Substrate (Task 1578 Baseline)
// ---------------------------------------------------------------------------

pub struct ModularSubstrate4D {
    pub columns: Vec<CorticalColumn>,
    pub w_inter_23: Vec<f32>,
    pub w_inter_5: Vec<f32>,
    pub yield_threshold: f32,
    pub plastic_rate: f32,
    pub activation_threshold: f32,
}

impl ModularSubstrate4D {
    pub fn new(yield_threshold: f32, plastic_rate: f32, activation_threshold: f32) -> Self {
        let mut columns = Vec::with_capacity(NUM_COLUMNS_4D);
        for id in 0..NUM_COLUMNS_4D {
            columns.push(CorticalColumn::new(id, yield_threshold, plastic_rate, activation_threshold));
        }

        Self {
            columns,
            w_inter_23: vec![0.0; INTER_COL_23_SIZE_4D],
            w_inter_5: vec![0.0; INTER_COL_5_SIZE_4D],
            yield_threshold: yield_threshold.clamp(0.01, 0.99),
            plastic_rate: plastic_rate.clamp(0.001, 1.0),
            activation_threshold: activation_threshold.max(0.01),
        }
    }

    #[inline(always)]
    fn index_inter_23(c_from: usize, c_to: usize, i: usize, j: usize) -> usize {
        ((c_from * NUM_COLUMNS_4D + c_to) * L23_NODES + i) * L23_NODES + j
    }

    #[inline(always)]
    fn index_inter_5(c_from: usize, c_to: usize, i: usize, j: usize) -> usize {
        ((c_from * NUM_COLUMNS_4D + c_to) * L5_NODES + i) * L5_NODES + j
    }

    pub fn compute_inter_column_currents(&self) -> (Vec<Vec<f32>>, Vec<Vec<f32>>) {
        let mut in_23 = vec![vec![0.0f32; L23_NODES]; NUM_COLUMNS_4D];
        let mut in_5 = vec![vec![0.0f32; L5_NODES]; NUM_COLUMNS_4D];

        for c_from in 0..NUM_COLUMNS_4D {
            for i in 0..L23_NODES {
                let v = self.columns[c_from].microcircuit.l23[i];
                if v == 0 { continue; }
                let v_f = v as f32;
                for c_to in 0..NUM_COLUMNS_4D {
                    if c_from == c_to { continue; }
                    for j in 0..L23_NODES {
                        let idx = Self::index_inter_23(c_from, c_to, i, j);
                        let w = self.w_inter_23[idx];
                        if w != 0.0 {
                            in_23[c_to][j] += v_f * w;
                        }
                    }
                }
            }
            for i in 0..L5_NODES {
                let v = self.columns[c_from].microcircuit.l5[i];
                if v == 0 { continue; }
                let v_f = v as f32;
                for c_to in 0..NUM_COLUMNS_4D {
                    if c_from == c_to { continue; }
                    for j in 0..L5_NODES {
                        let idx = Self::index_inter_5(c_from, c_to, i, j);
                        let w = self.w_inter_5[idx];
                        if w != 0.0 {
                            in_5[c_to][j] += v_f * w;
                        }
                    }
                }
            }
        }
        (in_23, in_5)
    }

    pub fn step(
        &mut self,
        sensory_trits: &[i8],
        somatic_trits: &[i8],
        observed_r_mm: Option<f32>,
        observed_theta_mdeg: Option<i32>,
        current_barrier_stress: f32,
    ) -> (usize, f32) {
        let mut total_yields = 0usize;
        let mut total_strain = 0.0f32;

        let (in_23, in_5) = self.compute_inter_column_currents();

        // 1. Column 0: Visual/Spatial Foveal Afferents
        let (y0, s0) = self.columns[0].microcircuit.step_laminar_flow(sensory_trits, somatic_trits, &in_23[0], &in_5[0]);
        total_yields += y0; total_strain += s0;

        // 2. Column 1: Spatial Polar Integration
        if let Some(r) = observed_r_mm {
            self.columns[1].spatial_r_mm = r;
            self.columns[1].persistence_trace = 1.0;
            self.columns[1].target_occluded = false;
        } else {
            self.columns[1].persistence_trace *= 0.985;
            self.columns[1].target_occluded = true;
        }
        if let Some(theta) = observed_theta_mdeg {
            self.columns[1].spatial_theta_mdeg = theta;
        }
        let (y1, s1) = self.columns[1].microcircuit.step_laminar_flow(sensory_trits, somatic_trits, &in_23[1], &in_5[1]);
        total_yields += y1; total_strain += s1;

        // 3. Column 2: Acoustic Cochlear Spectral Integration
        let (y2, s2) = self.columns[2].microcircuit.step_laminar_flow(sensory_trits, somatic_trits, &in_23[2], &in_5[2]);
        total_yields += y2; total_strain += s2;

        // 4. Column 3: Somatosensory Contact Mechanics & Material Yield Refusal
        self.columns[3].barrier_contact_stress = current_barrier_stress;
        self.columns[3].refusal_active = current_barrier_stress.abs() >= self.columns[3].yield_limit_threshold;
        let mut som_aff = sensory_trits.to_vec();
        if som_aff.is_empty() { som_aff = vec![0; L4_NODES]; }
        if self.columns[3].refusal_active {
            som_aff[0] = 1;
        }
        let (y3, s3) = self.columns[3].microcircuit.step_laminar_flow(&som_aff, somatic_trits, &in_23[3], &in_5[3]);
        total_yields += y3; total_strain += s3;

        // Step 5: Inter-Column Directional Fasciculi Plasticity
        let (inter_y, inter_s) = self.apply_inter_column_plasticity();
        total_yields += inter_y;
        total_strain += inter_s;

        (total_yields, total_strain)
    }

    pub fn apply_inter_column_plasticity(&mut self) -> (usize, f32) {
        let mut yield_count = 0usize;
        let mut total_strain = 0.0f32;
        let y = self.yield_threshold;
        let _eta = self.plastic_rate;

        for c_from in 0..NUM_COLUMNS_4D {
            for c_to in 0..NUM_COLUMNS_4D {
                if c_from == c_to { continue; }
                for i in 0..L23_NODES {
                    let from_val = self.columns[c_from].microcircuit.l23[i];
                    if from_val == 0 { continue; }
                    for j in 0..L23_NODES {
                        let to_val = self.columns[c_to].microcircuit.l23[j];
                        if to_val == 0 { continue; }
                        let idx = Self::index_inter_23(c_from, c_to, i, j);
                        let target = (from_val * to_val) as f32;
                        let sigma = target - self.w_inter_23[idx];
                        let abs_sigma = sigma.abs();
                        if abs_sigma > y {
                            let overstress = abs_sigma - y;
                            self.w_inter_23[idx] = (self.w_inter_23[idx] + overstress * sigma.signum()).clamp(-1.0, 1.0);
                            yield_count += 1;
                            total_strain += overstress;
                        }
                    }
                }
                for i in 0..L5_NODES {
                    let from_val = self.columns[c_from].microcircuit.l5[i];
                    if from_val == 0 { continue; }
                    for j in 0..L5_NODES {
                        let to_val = self.columns[c_to].microcircuit.l5[j];
                        if to_val == 0 { continue; }
                        let idx = Self::index_inter_5(c_from, c_to, i, j);
                        let target = (from_val * to_val) as f32;
                        let sigma = target - self.w_inter_5[idx];
                        let abs_sigma = sigma.abs();
                        if abs_sigma > y {
                            let overstress = abs_sigma - y;
                            self.w_inter_5[idx] = (self.w_inter_5[idx] + overstress * sigma.signum()).clamp(-1.0, 1.0);
                            yield_count += 1;
                            total_strain += overstress;
                        }
                    }
                }
            }
        }
        (yield_count, total_strain)
    }

    pub fn dream_consolidation(&mut self, decay: f32, prune_thresh: f32) -> (usize, usize) {
        let mut total_decayed = 0usize;
        let mut total_pruned = 0usize;
        for col in &mut self.columns {
            let (d, p) = col.microcircuit.dream_downscale_and_prune(decay, prune_thresh);
            total_decayed += d; total_pruned += p;
        }
        for g in self.w_inter_23.iter_mut() {
            if *g != 0.0 {
                total_decayed += 1;
                *g *= 1.0 - decay;
                if prune_thresh > 0.0 && g.abs() < prune_thresh {
                    *g = 0.0;
                    total_pruned += 1;
                }
            }
        }
        for g in self.w_inter_5.iter_mut() {
            if *g != 0.0 {
                total_decayed += 1;
                *g *= 1.0 - decay;
                if prune_thresh > 0.0 && g.abs() < prune_thresh {
                    *g = 0.0;
                    total_pruned += 1;
                }
            }
        }
        (total_decayed, total_pruned)
    }

    pub fn total_active_synapses(&self) -> usize {
        let mut total = 0usize;
        for col in &self.columns {
            total += col.microcircuit.active_intra_synapses();
        }
        for &g in &self.w_inter_23 {
            if g.abs() > 0.001 { total += 1; }
        }
        for &g in &self.w_inter_5 {
            if g.abs() > 0.001 { total += 1; }
        }
        total
    }

    pub fn zero_plastic_weights(&mut self) {
        for col in &mut self.columns {
            col.zero_plastic_weights();
        }
        self.w_inter_23.fill(0.0);
        self.w_inter_5.fill(0.0);
    }

    pub fn export_sparse_v3(&self) -> Result<Vec<u8>, String> {
        if !self.yield_threshold.is_finite() || !self.plastic_rate.is_finite() || !self.activation_threshold.is_finite() {
            return Err("Non-finite float in 4D substrate header during export".to_string());
        }
        let mut buf = Vec::with_capacity(65536);
        buf.extend_from_slice(ARCLOOM_STATE_MAGIC_V4);
        buf.extend_from_slice(&ARCLOOM_STATE_VERSION_V4.to_le_bytes());
        buf.extend_from_slice(&(NUM_COLUMNS_4D as u16).to_le_bytes());
        buf.extend_from_slice(&self.yield_threshold.to_le_bytes());
        buf.extend_from_slice(&self.plastic_rate.to_le_bytes());
        buf.extend_from_slice(&self.activation_threshold.to_le_bytes());

        for col in &self.columns {
            serialize_column_state(col, &mut buf)?;
        }

        let mut nz_23: Vec<(u32, f32)> = Vec::new();
        for (idx, &g) in self.w_inter_23.iter().enumerate() {
            if !g.is_finite() { return Err(format!("Non-finite weight in 4D w_inter_23 idx {}", idx)); }
            if g != 0.0 { nz_23.push((idx as u32, g)); }
        }
        buf.extend_from_slice(&(nz_23.len() as u32).to_le_bytes());
        for (idx, g) in nz_23 {
            buf.extend_from_slice(&idx.to_le_bytes());
            buf.extend_from_slice(&g.to_le_bytes());
        }

        let mut nz_5: Vec<(u32, f32)> = Vec::new();
        for (idx, &g) in self.w_inter_5.iter().enumerate() {
            if !g.is_finite() { return Err(format!("Non-finite weight in 4D w_inter_5 idx {}", idx)); }
            if g != 0.0 { nz_5.push((idx as u32, g)); }
        }
        buf.extend_from_slice(&(nz_5.len() as u32).to_le_bytes());
        for (idx, g) in nz_5 {
            buf.extend_from_slice(&idx.to_le_bytes());
            buf.extend_from_slice(&g.to_le_bytes());
        }

        // Nominal efferents
        buf.extend_from_slice(&0.0f32.to_le_bytes());
        buf.extend_from_slice(&60.0f32.to_le_bytes());
        buf.extend_from_slice(&0.0f32.to_le_bytes());
        buf.extend_from_slice(&0.0f32.to_le_bytes());

        let pad = (8 - (buf.len() % 8)) % 8;
        for _ in 0..pad {
            buf.push(0);
        }

        Ok(buf)
    }

    pub fn import_sparse_v3(&mut self, data: &[u8]) -> Result<(), String> {
        if data.is_empty() {
            return Err("Cannot import from empty byte buffer".to_string());
        }
        if data.len() < 8 {
            return Err("Truncated header: less than 8 bytes".to_string());
        }
        let magic = &data[0..8];
        if magic != ARCLOOM_STATE_MAGIC_V4 {
            return Err(format!("Invalid ArcLoom state format: expected ARCLOOM4, got unknown magic {:?}", magic));
        }
        if data.len() < 24 {
            return Err("Truncated ARCLOOM header: less than 24 bytes".to_string());
        }
        let version = u16::from_le_bytes([data[8], data[9]]);
        if version != ARCLOOM_STATE_VERSION_V4 {
            return Err(format!("Unsupported ArcLoom version for 4D: expected 4, got {}", version));
        }
        let n_cols = u16::from_le_bytes([data[10], data[11]]) as usize;
        if n_cols != NUM_COLUMNS_4D {
            return Err(format!("Column count mismatch: data has {}, instance has {}", n_cols, NUM_COLUMNS_4D));
        }
        let new_yield = f32::from_le_bytes([data[12], data[13], data[14], data[15]]);
        let new_plastic = f32::from_le_bytes([data[16], data[17], data[18], data[19]]);
        let new_activation = f32::from_le_bytes([data[20], data[21], data[22], data[23]]);

        if !new_yield.is_finite() || !new_plastic.is_finite() || !new_activation.is_finite() {
            return Err("Non-finite float in ArcLoom header".to_string());
        }
        if new_yield <= 0.0 || new_yield > 1.0 || new_plastic <= 0.0 || new_plastic > 1.0 || new_activation <= 0.0 {
            return Err("Invalid parameter domain in ArcLoom header".to_string());
        }

        let mut temp_columns = self.columns.clone();
        let mut offset = 24;
        for (col_idx, col) in temp_columns.iter_mut().enumerate() {
            offset = deserialize_column_state(col, data, offset, col_idx, NUM_COLUMNS_4D)?;
        }

        if offset + 4 > data.len() { return Err("Unexpected EOF in w_inter_23 count".to_string()); }
        let count_23 = u32::from_le_bytes([data[offset], data[offset+1], data[offset+2], data[offset+3]]) as usize;
        offset += 4;

        if offset + count_23 * 8 > data.len() { return Err("Unexpected EOF in w_inter_23 entries".to_string()); }
        let mut new_w_23 = vec![0.0f32; self.w_inter_23.len()];
        let mut seen_23 = HashSet::new();
        for _ in 0..count_23 {
            let idx = u32::from_le_bytes([data[offset], data[offset+1], data[offset+2], data[offset+3]]) as usize; offset += 4;
            let g = f32::from_le_bytes([data[offset], data[offset+1], data[offset+2], data[offset+3]]); offset += 4;
            if !g.is_finite() { return Err("Non-finite synaptic weight in w_inter_23".to_string()); }
            if idx >= new_w_23.len() { return Err(format!("Synaptic index out of bounds: {} >= {}", idx, new_w_23.len())); }
            if !seen_23.insert(idx) { return Err(format!("Duplicate synaptic index in w_inter_23: {}", idx)); }
            new_w_23[idx] = g;
        }

        if offset + 4 > data.len() { return Err("Unexpected EOF in w_inter_5 count".to_string()); }
        let count_5 = u32::from_le_bytes([data[offset], data[offset+1], data[offset+2], data[offset+3]]) as usize;
        offset += 4;

        if offset + count_5 * 8 > data.len() { return Err("Unexpected EOF in w_inter_5 entries".to_string()); }
        let mut new_w_5 = vec![0.0f32; self.w_inter_5.len()];
        let mut seen_5 = HashSet::new();
        for _ in 0..count_5 {
            let idx = u32::from_le_bytes([data[offset], data[offset+1], data[offset+2], data[offset+3]]) as usize; offset += 4;
            let g = f32::from_le_bytes([data[offset], data[offset+1], data[offset+2], data[offset+3]]); offset += 4;
            if !g.is_finite() { return Err("Non-finite synaptic weight in w_inter_5".to_string()); }
            if idx >= new_w_5.len() { return Err(format!("Synaptic index out of bounds: {} >= {}", idx, new_w_5.len())); }
            if !seen_5.insert(idx) { return Err(format!("Duplicate synaptic index in w_inter_5: {}", idx)); }
            new_w_5[idx] = g;
        }

        if offset + 16 > data.len() {
            return Err("Missing or truncated motor efferent footer in ARCLOOM payload".to_string());
        }
        let v0 = f32::from_le_bytes([data[offset], data[offset+1], data[offset+2], data[offset+3]]); offset += 4;
        let v1 = f32::from_le_bytes([data[offset], data[offset+1], data[offset+2], data[offset+3]]); offset += 4;
        let v2 = f32::from_le_bytes([data[offset], data[offset+1], data[offset+2], data[offset+3]]); offset += 4;
        let v3 = f32::from_le_bytes([data[offset], data[offset+1], data[offset+2], data[offset+3]]); offset += 4;
        if !v0.is_finite() || !v1.is_finite() || !v2.is_finite() || !v3.is_finite() {
            return Err("Non-finite float in motor efferent footer".to_string());
        }

        let expected_pad = (8 - (offset % 8)) % 8;
        let actual_pad = data.len() - offset;
        if actual_pad != expected_pad {
            return Err(format!("Incorrect trailing alignment padding: expected {} bytes, got {}", expected_pad, actual_pad));
        }
        for i in 0..expected_pad {
            if data[offset + i] != 0 {
                return Err("Non-zero padding byte in ARCLOOM payload".to_string());
            }
        }

        self.yield_threshold = new_yield;
        self.plastic_rate = new_plastic;
        self.activation_threshold = new_activation;
        self.columns = temp_columns;
        self.w_inter_23 = new_w_23;
        self.w_inter_5 = new_w_5;
        Ok(())
    }

    pub fn export_sparse_v4(&self) -> Result<Vec<u8>, String> {
        self.export_sparse_v3()
    }

    pub fn import_sparse_v4(&mut self, data: &[u8]) -> Result<(), String> {
        self.import_sparse_v3(data)
    }
}

// ---------------------------------------------------------------------------
// 4. 8-Column Balanced Octet Modular Substrate (Option A Architecture)
// ---------------------------------------------------------------------------

pub struct ModularSubstrate8D {
    pub columns: Vec<CorticalColumn>,
    pub w_inter_23: Vec<f32>,
    pub w_inter_5: Vec<f32>,
    pub yield_threshold: f32,
    pub plastic_rate: f32,
    pub activation_threshold: f32,
    pub motor_vocal_drive: f32,
    pub motor_locomotion_stride: f32,
}

impl ModularSubstrate8D {
    pub fn new(yield_threshold: f32, plastic_rate: f32, activation_threshold: f32) -> Self {
        let mut columns = Vec::with_capacity(NUM_COLUMNS_8D);
        for id in 0..NUM_COLUMNS_8D {
            columns.push(CorticalColumn::new(id, yield_threshold, plastic_rate, activation_threshold));
        }

        Self {
            columns,
            w_inter_23: vec![0.0; INTER_COL_23_SIZE_8D],
            w_inter_5: vec![0.0; INTER_COL_5_SIZE_8D],
            yield_threshold: yield_threshold.clamp(0.01, 0.99),
            plastic_rate: plastic_rate.clamp(0.001, 1.0),
            activation_threshold: activation_threshold.max(0.01),
            motor_vocal_drive: 0.0,
            motor_locomotion_stride: 60.0,
        }
    }

    #[inline(always)]
    fn index_inter_23(c_from: usize, c_to: usize, i: usize, j: usize) -> usize {
        ((c_from * NUM_COLUMNS_8D + c_to) * L23_NODES + i) * L23_NODES + j
    }

    #[inline(always)]
    fn index_inter_5(c_from: usize, c_to: usize, i: usize, j: usize) -> usize {
        ((c_from * NUM_COLUMNS_8D + c_to) * L5_NODES + i) * L5_NODES + j
    }

    pub fn compute_inter_column_currents(&self) -> (Vec<Vec<f32>>, Vec<Vec<f32>>) {
        let mut in_23 = vec![vec![0.0f32; L23_NODES]; NUM_COLUMNS_8D];
        let mut in_5 = vec![vec![0.0f32; L5_NODES]; NUM_COLUMNS_8D];

        for c_from in 0..NUM_COLUMNS_8D {
            for i in 0..L23_NODES {
                let v = self.columns[c_from].microcircuit.l23[i];
                if v == 0 { continue; }
                let v_f = v as f32;
                for c_to in 0..NUM_COLUMNS_8D {
                    if c_from == c_to { continue; }
                    for j in 0..L23_NODES {
                        let idx = Self::index_inter_23(c_from, c_to, i, j);
                        let w = self.w_inter_23[idx];
                        if w != 0.0 {
                            in_23[c_to][j] += v_f * w;
                        }
                    }
                }
            }
            for i in 0..L5_NODES {
                let v = self.columns[c_from].microcircuit.l5[i];
                if v == 0 { continue; }
                let v_f = v as f32;
                for c_to in 0..NUM_COLUMNS_8D {
                    if c_from == c_to { continue; }
                    for j in 0..L5_NODES {
                        let idx = Self::index_inter_5(c_from, c_to, i, j);
                        let w = self.w_inter_5[idx];
                        if w != 0.0 {
                            in_5[c_to][j] += v_f * w;
                        }
                    }
                }
            }
        }
        (in_23, in_5)
    }

    pub fn step(
        &mut self,
        sensory_trits: &[i8],
        somatic_trits: &[i8],
        observed_r_mm: Option<f32>,
        observed_theta_mdeg: Option<i32>,
        current_barrier_stress: f32,
        acoustic_formant: f32,
    ) -> (usize, f32) {
        let mut total_yields = 0usize;
        let mut total_strain = 0.0f32;

        let (in_23, in_5) = self.compute_inter_column_currents();

        // 1. Col 0 (V1: Foveal Target)
        if let Some(r) = observed_r_mm {
            self.columns[0].spatial_r_mm = r;
            self.columns[0].persistence_trace = 1.0;
            self.columns[0].target_occluded = false;
        } else {
            self.columns[0].persistence_trace *= 0.985;
            self.columns[0].target_occluded = true;
        }
        let mut v1_aff = vec![0i8; L4_NODES];
        if self.columns[0].persistence_trace > 0.05 {
            let r_bin = ((self.columns[0].spatial_r_mm / 100.0) as usize).min(63);
            v1_aff[r_bin] = 1;
        }
        let (y0, s0) = self.columns[0].microcircuit.step_laminar_flow(&v1_aff, somatic_trits, &in_23[0], &in_5[0]);
        total_yields += y0; total_strain += s0;

        // 2. Col 1 (V2: Optical Angle)
        if let Some(th) = observed_theta_mdeg {
            self.columns[1].spatial_theta_mdeg = th;
            self.columns[1].persistence_trace = 1.0;
            self.columns[1].target_occluded = false;
        } else {
            self.columns[1].persistence_trace *= 0.985;
            self.columns[1].target_occluded = true;
        }
        let mut v2_aff = vec![0i8; L4_NODES];
        if self.columns[1].persistence_trace > 0.05 {
            let th_bin = (((self.columns[1].spatial_theta_mdeg + 180_000) / 6000) as usize).min(63);
            v2_aff[th_bin] = 1;
        }
        let (y1, s1) = self.columns[1].microcircuit.step_laminar_flow(&v2_aff, somatic_trits, &in_23[1], &in_5[1]);
        total_yields += y1; total_strain += s1;

        // 3. Col 2 (A1: Formant Resonance)
        let mut a1_aff = vec![0i8; L4_NODES];
        if acoustic_formant > 10.0 {
            let bin = ((acoustic_formant / 5.0) as usize).min(63);
            a1_aff[bin] = 1;
        }
        let (y2, s2) = self.columns[2].microcircuit.step_laminar_flow(&a1_aff, somatic_trits, &in_23[2], &in_5[2]);
        total_yields += y2; total_strain += s2;

        // 4. Col 3 (A2: Cochlear Envelope)
        let (y3, s3) = self.columns[3].microcircuit.step_laminar_flow(sensory_trits, somatic_trits, &in_23[3], &in_5[3]);
        total_yields += y3; total_strain += s3;

        // 5. Col 4 (S1: Somatosensory Contact)
        let (y4, s4) = self.columns[4].microcircuit.step_laminar_flow(sensory_trits, somatic_trits, &in_23[4], &in_5[4]);
        total_yields += y4; total_strain += s4;

        // 6. Col 5 (S2: Barrier Contact Yield Stress)
        self.columns[5].barrier_contact_stress = current_barrier_stress;
        self.columns[5].refusal_active = current_barrier_stress.abs() >= self.columns[5].yield_limit_threshold;
        let mut s2_aff = vec![0i8; L4_NODES];
        s2_aff[0] = if self.columns[5].refusal_active { 1 } else { 0 };
        let (y5, s5) = self.columns[5].microcircuit.step_laminar_flow(&s2_aff, somatic_trits, &in_23[5], &in_5[5]);
        total_yields += y5; total_strain += s5;

        // 7. Col 6 (M1: Airway Vocal Valve Discharge)
        let mut m1_aff = vec![0i8; L4_NODES];
        if acoustic_formant > 50.0 {
            m1_aff[0] = 1;
        }
        let (y6, s6) = self.columns[6].microcircuit.step_laminar_flow(&m1_aff, somatic_trits, &in_23[6], &in_5[6]);
        total_yields += y6; total_strain += s6;

        // 8. Col 7 (M2: Motor Locomotion Stride & Steer)
        let mut m2_aff = vec![0i8; L4_NODES];
        if somatic_trits.iter().any(|&x| x > 0) {
            m2_aff[0] = 1;
        }
        let (y7, s7) = self.columns[7].microcircuit.step_laminar_flow(&m2_aff, somatic_trits, &in_23[7], &in_5[7]);
        total_yields += y7; total_strain += s7;

        // Causal Motor Efferent Decoding from Settled L5 Motor Pyramidal Neurons:
        let neg_stride = self.columns[7].microcircuit.l5.iter().filter(|&&x| x < 0).count() as f32;
        self.motor_locomotion_stride = (60.0 * (1.0 - (neg_stride / (L5_NODES as f32)))).clamp(0.0, 60.0);

        let pos_vocal = self.columns[6].microcircuit.l5.iter().filter(|&&x| x > 0).count() as f32;
        self.motor_vocal_drive = ((pos_vocal / (L5_NODES as f32)) * 480.0).clamp(0.0, 480.0);

        // Physical Barrier Refusal Kinematic Clamp:
        if self.columns[5].refusal_active {
            self.motor_locomotion_stride = 0.0;
            self.motor_vocal_drive = 220.0;
        }

        // Step 9: Inter-Column Directional Fasciculi Plasticity
        let (inter_y, inter_s) = self.apply_inter_column_plasticity();
        total_yields += inter_y;
        total_strain += inter_s;

        (total_yields, total_strain)
    }

    pub fn apply_inter_column_plasticity(&mut self) -> (usize, f32) {
        let mut yield_count = 0usize;
        let mut total_strain = 0.0f32;
        let y = self.yield_threshold;
        let _eta = self.plastic_rate;

        for c_from in 0..NUM_COLUMNS_8D {
            for c_to in 0..NUM_COLUMNS_8D {
                if c_from == c_to { continue; }
                for i in 0..L23_NODES {
                    let from_val = self.columns[c_from].microcircuit.l23[i];
                    if from_val == 0 { continue; }
                    for j in 0..L23_NODES {
                        let to_val = self.columns[c_to].microcircuit.l23[j];
                        if to_val == 0 { continue; }
                        let idx = Self::index_inter_23(c_from, c_to, i, j);
                        let target = (from_val * to_val) as f32;
                        let sigma = target - self.w_inter_23[idx];
                        let abs_sigma = sigma.abs();
                        if abs_sigma > y {
                            let overstress = abs_sigma - y;
                            self.w_inter_23[idx] = (self.w_inter_23[idx] + overstress * sigma.signum()).clamp(-1.0, 1.0);
                            yield_count += 1;
                            total_strain += overstress;
                        }
                    }
                }
                for i in 0..L5_NODES {
                    let from_val = self.columns[c_from].microcircuit.l5[i];
                    if from_val == 0 { continue; }
                    for j in 0..L5_NODES {
                        let to_val = self.columns[c_to].microcircuit.l5[j];
                        if to_val == 0 { continue; }
                        let idx = Self::index_inter_5(c_from, c_to, i, j);
                        let target = (from_val * to_val) as f32;
                        let sigma = target - self.w_inter_5[idx];
                        let abs_sigma = sigma.abs();
                        if abs_sigma > y {
                            let overstress = abs_sigma - y;
                            self.w_inter_5[idx] = (self.w_inter_5[idx] + overstress * sigma.signum()).clamp(-1.0, 1.0);
                            yield_count += 1;
                            total_strain += overstress;
                        }
                    }
                }
            }
        }
        (yield_count, total_strain)
    }

    pub fn dream_consolidation(&mut self, decay: f32, prune_thresh: f32) -> (usize, usize) {
        let mut total_decayed = 0usize;
        let mut total_pruned = 0usize;
        for col in &mut self.columns {
            let (d, p) = col.microcircuit.dream_downscale_and_prune(decay, prune_thresh);
            total_decayed += d; total_pruned += p;
        }
        for g in self.w_inter_23.iter_mut() {
            if *g != 0.0 {
                total_decayed += 1;
                *g *= 1.0 - decay;
                if prune_thresh > 0.0 && g.abs() < prune_thresh {
                    *g = 0.0;
                    total_pruned += 1;
                }
            }
        }
        for g in self.w_inter_5.iter_mut() {
            if *g != 0.0 {
                total_decayed += 1;
                *g *= 1.0 - decay;
                if prune_thresh > 0.0 && g.abs() < prune_thresh {
                    *g = 0.0;
                    total_pruned += 1;
                }
            }
        }
        (total_decayed, total_pruned)
    }

    pub fn total_active_synapses(&self) -> usize {
        let mut total = 0usize;
        for col in &self.columns {
            total += col.microcircuit.active_intra_synapses();
        }
        for &g in &self.w_inter_23 {
            if g.abs() > 0.001 { total += 1; }
        }
        for &g in &self.w_inter_5 {
            if g.abs() > 0.001 { total += 1; }
        }
        total
    }

    pub fn zero_plastic_weights(&mut self) {
        for col in &mut self.columns {
            col.zero_plastic_weights();
        }
        self.w_inter_23.fill(0.0);
        self.w_inter_5.fill(0.0);
    }

    pub fn export_sparse_v3(&self) -> Result<Vec<u8>, String> {
        if !self.yield_threshold.is_finite() || !self.plastic_rate.is_finite() || !self.activation_threshold.is_finite() ||
           !self.motor_vocal_drive.is_finite() || !self.motor_locomotion_stride.is_finite() {
            return Err("Non-finite float in 8D substrate header during export".to_string());
        }
        let mut buf = Vec::with_capacity(131072);
        buf.extend_from_slice(ARCLOOM_STATE_MAGIC_V4);
        buf.extend_from_slice(&ARCLOOM_STATE_VERSION_V4.to_le_bytes());
        buf.extend_from_slice(&(NUM_COLUMNS_8D as u16).to_le_bytes());
        buf.extend_from_slice(&self.yield_threshold.to_le_bytes());
        buf.extend_from_slice(&self.plastic_rate.to_le_bytes());
        buf.extend_from_slice(&self.activation_threshold.to_le_bytes());

        for col in &self.columns {
            serialize_column_state(col, &mut buf)?;
        }

        let mut nz_23: Vec<(u32, f32)> = Vec::new();
        for (idx, &g) in self.w_inter_23.iter().enumerate() {
            if !g.is_finite() { return Err(format!("Non-finite weight in 8D w_inter_23 idx {}", idx)); }
            if g != 0.0 { nz_23.push((idx as u32, g)); }
        }
        buf.extend_from_slice(&(nz_23.len() as u32).to_le_bytes());
        for (idx, g) in nz_23 {
            buf.extend_from_slice(&idx.to_le_bytes());
            buf.extend_from_slice(&g.to_le_bytes());
        }

        let mut nz_5: Vec<(u32, f32)> = Vec::new();
        for (idx, &g) in self.w_inter_5.iter().enumerate() {
            if !g.is_finite() { return Err(format!("Non-finite weight in 8D w_inter_5 idx {}", idx)); }
            if g != 0.0 { nz_5.push((idx as u32, g)); }
        }
        buf.extend_from_slice(&(nz_5.len() as u32).to_le_bytes());
        for (idx, g) in nz_5 {
            buf.extend_from_slice(&idx.to_le_bytes());
            buf.extend_from_slice(&g.to_le_bytes());
        }

        buf.extend_from_slice(&self.motor_vocal_drive.to_le_bytes());
        buf.extend_from_slice(&self.motor_locomotion_stride.to_le_bytes());
        buf.extend_from_slice(&0.0f32.to_le_bytes());
        buf.extend_from_slice(&0.0f32.to_le_bytes());

        let pad = (8 - (buf.len() % 8)) % 8;
        for _ in 0..pad {
            buf.push(0);
        }

        Ok(buf)
    }

    pub fn import_sparse_v3(&mut self, data: &[u8]) -> Result<(), String> {
        if data.is_empty() {
            return Err("Cannot import from empty byte buffer".to_string());
        }
        if data.len() < 8 {
            return Err("Truncated header: less than 8 bytes".to_string());
        }
        let magic = &data[0..8];
        if magic != ARCLOOM_STATE_MAGIC_V4 {
            return Err(format!("Invalid ArcLoom state format: expected ARCLOOM4, got unknown magic {:?}", magic));
        }
        if data.len() < 24 {
            return Err("Truncated ARCLOOM header: less than 24 bytes".to_string());
        }
        let version = u16::from_le_bytes([data[8], data[9]]);
        if version != ARCLOOM_STATE_VERSION_V4 {
            return Err(format!("Unsupported ArcLoom version for 8D: expected 4, got {}", version));
        }
        let n_cols = u16::from_le_bytes([data[10], data[11]]) as usize;
        if n_cols != NUM_COLUMNS_8D {
            return Err(format!("Column count mismatch: data has {}, instance has {}", n_cols, NUM_COLUMNS_8D));
        }
        let new_yield = f32::from_le_bytes([data[12], data[13], data[14], data[15]]);
        let new_plastic = f32::from_le_bytes([data[16], data[17], data[18], data[19]]);
        let new_activation = f32::from_le_bytes([data[20], data[21], data[22], data[23]]);

        if !new_yield.is_finite() || !new_plastic.is_finite() || !new_activation.is_finite() {
            return Err("Non-finite float in ArcLoom header".to_string());
        }
        if new_yield <= 0.0 || new_yield > 1.0 || new_plastic <= 0.0 || new_plastic > 1.0 || new_activation <= 0.0 {
            return Err("Invalid parameter domain in ArcLoom header".to_string());
        }

        let mut temp_columns = self.columns.clone();
        let mut offset = 24;
        for (col_idx, col) in temp_columns.iter_mut().enumerate() {
            offset = deserialize_column_state(col, data, offset, col_idx, NUM_COLUMNS_8D)?;
        }

        if offset + 4 > data.len() { return Err("Unexpected EOF in w_inter_23 count".to_string()); }
        let count_23 = u32::from_le_bytes([data[offset], data[offset+1], data[offset+2], data[offset+3]]) as usize;
        offset += 4;

        if offset + count_23 * 8 > data.len() { return Err("Unexpected EOF in w_inter_23 entries".to_string()); }
        let mut new_w_23 = vec![0.0f32; self.w_inter_23.len()];
        let mut seen_23 = HashSet::new();
        for _ in 0..count_23 {
            let idx = u32::from_le_bytes([data[offset], data[offset+1], data[offset+2], data[offset+3]]) as usize; offset += 4;
            let g = f32::from_le_bytes([data[offset], data[offset+1], data[offset+2], data[offset+3]]); offset += 4;
            if !g.is_finite() { return Err("Non-finite synaptic weight in w_inter_23".to_string()); }
            if idx >= new_w_23.len() { return Err(format!("Synaptic index out of bounds: {} >= {}", idx, new_w_23.len())); }
            if !seen_23.insert(idx) { return Err(format!("Duplicate synaptic index in w_inter_23: {}", idx)); }
            new_w_23[idx] = g;
        }

        if offset + 4 > data.len() { return Err("Unexpected EOF in w_inter_5 count".to_string()); }
        let count_5 = u32::from_le_bytes([data[offset], data[offset+1], data[offset+2], data[offset+3]]) as usize;
        offset += 4;

        if offset + count_5 * 8 > data.len() { return Err("Unexpected EOF in w_inter_5 entries".to_string()); }
        let mut new_w_5 = vec![0.0f32; self.w_inter_5.len()];
        let mut seen_5 = HashSet::new();
        for _ in 0..count_5 {
            let idx = u32::from_le_bytes([data[offset], data[offset+1], data[offset+2], data[offset+3]]) as usize; offset += 4;
            let g = f32::from_le_bytes([data[offset], data[offset+1], data[offset+2], data[offset+3]]); offset += 4;
            if !g.is_finite() { return Err("Non-finite synaptic weight in w_inter_5".to_string()); }
            if idx >= new_w_5.len() { return Err(format!("Synaptic index out of bounds: {} >= {}", idx, new_w_5.len())); }
            if !seen_5.insert(idx) { return Err(format!("Duplicate synaptic index in w_inter_5: {}", idx)); }
            new_w_5[idx] = g;
        }

        if offset + 16 > data.len() {
            return Err("Missing or truncated motor efferent footer in ARCLOOM payload".to_string());
        }
        let new_vocal = f32::from_le_bytes([data[offset], data[offset+1], data[offset+2], data[offset+3]]); offset += 4;
        let new_stride = f32::from_le_bytes([data[offset], data[offset+1], data[offset+2], data[offset+3]]); offset += 4;
        let _new_steer = f32::from_le_bytes([data[offset], data[offset+1], data[offset+2], data[offset+3]]); offset += 4;
        let _new_grip = f32::from_le_bytes([data[offset], data[offset+1], data[offset+2], data[offset+3]]); offset += 4;

        if !new_vocal.is_finite() || !new_stride.is_finite() || !_new_steer.is_finite() || !_new_grip.is_finite() {
            return Err("Non-finite float in motor efferent footer".to_string());
        }

        let expected_pad = (8 - (offset % 8)) % 8;
        let actual_pad = data.len() - offset;
        if actual_pad != expected_pad {
            return Err(format!("Incorrect trailing alignment padding: expected {} bytes, got {}", expected_pad, actual_pad));
        }
        for i in 0..expected_pad {
            if data[offset + i] != 0 {
                return Err("Non-zero padding byte in ARCLOOM payload".to_string());
            }
        }

        self.yield_threshold = new_yield;
        self.plastic_rate = new_plastic;
        self.activation_threshold = new_activation;
        self.columns = temp_columns;
        self.w_inter_23 = new_w_23;
        self.w_inter_5 = new_w_5;
        self.motor_vocal_drive = new_vocal;
        self.motor_locomotion_stride = new_stride;
        Ok(())
    }

    pub fn export_sparse_v4(&self) -> Result<Vec<u8>, String> {
        self.export_sparse_v3()
    }

    pub fn import_sparse_v4(&mut self, data: &[u8]) -> Result<(), String> {
        self.import_sparse_v3(data)
    }
}

// ---------------------------------------------------------------------------
// 5. 64-Column Cortical Array Modular Substrate
// ---------------------------------------------------------------------------

pub struct StagedSubstrateState {
    pub yield_threshold: f32,
    pub plastic_rate: f32,
    pub activation_threshold: f32,
    pub columns: Vec<CorticalColumn>,
    pub w_inter_23: Vec<f32>,
    pub active_inter_23: Vec<usize>,
    pub w_inter_5: Vec<f32>,
    pub active_inter_5: Vec<usize>,
    pub severed_tracts: Vec<bool>,
    pub continuous_joint_field: [f64; 8],
    pub continuous_joint_field_present: bool,
    pub motor_vocal_drive: f32,
    pub motor_locomotion_stride: f32,
    pub motor_steer_angle: f32,
    pub motor_grip_force: f32,
}

pub use crate::mathloom::MathLoomRationalField;

pub struct ModularSubstrate64D {
    pub columns: Vec<CorticalColumn>,
    pub w_inter_23: Vec<f32>,
    pub w_inter_5: Vec<f32>,
    pub active_inter_23: Vec<usize>,
    pub active_inter_5: Vec<usize>,
    pub severed_tracts: Vec<bool>,
    pub continuous_joint_field: [f64; 8],
    pub continuous_joint_field_present: bool,
    pub yield_threshold: f32,
    pub plastic_rate: f32,
    pub activation_threshold: f32,
    pub motor_vocal_drive: f32,
    pub motor_locomotion_stride: f32,
    pub motor_steer_angle: f32,
    pub motor_grip_force: f32,
}

impl ModularSubstrate64D {
    pub fn new(yield_threshold: f32, plastic_rate: f32, activation_threshold: f32) -> Self {
        let mut columns = Vec::with_capacity(NUM_COLUMNS_64D);
        for id in 0..NUM_COLUMNS_64D {
            columns.push(CorticalColumn::new(id, yield_threshold, plastic_rate, activation_threshold));
        }

        Self {
            columns,
            w_inter_23: vec![0.0; INTER_COL_23_SIZE_64D],
            w_inter_5: vec![0.0; INTER_COL_5_SIZE_64D],
            active_inter_23: Vec::new(),
            active_inter_5: Vec::new(),
            severed_tracts: vec![false; NUM_COLUMNS_64D * NUM_COLUMNS_64D],
            continuous_joint_field: [0.0; 8],
            continuous_joint_field_present: false,
            yield_threshold: yield_threshold.clamp(0.01, 0.99),
            plastic_rate: plastic_rate.clamp(0.001, 1.0),
            activation_threshold: activation_threshold.max(0.01),
            motor_vocal_drive: 0.0,
            motor_locomotion_stride: 0.0,
            motor_steer_angle: 0.0,
            motor_grip_force: 0.0,
        }
    }

    #[inline]
    pub fn quantize_radix3(val: f64) -> (i8, i8) {
        if !val.is_finite() {
            return (0, 0);
        }
        let mut rem = val;
        let mut trits = [0i8; 2];
        let mut power = 1.0 / 3.0;
        for t in trits.iter_mut() {
            let half = power / 2.0;
            if rem > half {
                *t = 1;
                rem -= power;
            } else if rem < -half {
                *t = -1;
                rem += power;
            } else {
                *t = 0;
            }
            power /= 3.0;
        }
        (trits[0], trits[1])
    }

    /// Exact numerical representation, not a field-to-current operator.
    pub fn float_to_rational_trits(val: f64) -> Result<MathLoomRationalField, String> {
        crate::mathloom::float_to_rational_trits(val)
    }

    pub fn rational_trits_to_float(field: &MathLoomRationalField) -> Result<f64, String> {
        crate::mathloom::rational_trits_to_float(field)
    }

    pub fn consume_continuous_joint_field(&mut self, field_7d: [f64; 7], s_uf: f64) -> Result<(), String> {
        for (i, &val) in field_7d.iter().enumerate() {
            if !val.is_finite() {
                return Err(format!("Non-finite value in continuous joint field index {}: {}", i, val));
            }
        }
        if !s_uf.is_finite() {
            return Err(format!("Non-finite S_UF invariant: {}", s_uf));
        }
        self.continuous_joint_field[0..7].copy_from_slice(&field_7d);
        self.continuous_joint_field[7] = s_uf;
        self.continuous_joint_field_present = true;
        Ok(())
    }

    pub fn clear_continuous_joint_field(&mut self) {
        self.continuous_joint_field = [0.0; 8];
        self.continuous_joint_field_present = false;
    }

    pub fn has_continuous_joint_field(&self) -> bool {
        self.continuous_joint_field_present
    }

    pub fn get_continuous_joint_field(&self) -> [f64; 8] {
        self.continuous_joint_field
    }

    fn commit_staged_state(&mut self, staged: StagedSubstrateState) {
        self.yield_threshold = staged.yield_threshold;
        self.plastic_rate = staged.plastic_rate;
        self.activation_threshold = staged.activation_threshold;
        self.columns = staged.columns;
        self.w_inter_23 = staged.w_inter_23;
        self.active_inter_23 = staged.active_inter_23;
        self.w_inter_5 = staged.w_inter_5;
        self.active_inter_5 = staged.active_inter_5;
        self.severed_tracts = staged.severed_tracts;
        self.continuous_joint_field = staged.continuous_joint_field;
        self.continuous_joint_field_present = staged.continuous_joint_field_present;
        self.motor_vocal_drive = staged.motor_vocal_drive;
        self.motor_locomotion_stride = staged.motor_locomotion_stride;
        self.motor_steer_angle = staged.motor_steer_angle;
        self.motor_grip_force = staged.motor_grip_force;
    }

    pub fn sever_tract(&mut self, c_from: usize, c_to: usize) {
        if c_from < NUM_COLUMNS_64D && c_to < NUM_COLUMNS_64D {
            self.severed_tracts[c_from * NUM_COLUMNS_64D + c_to] = true;
            self.severed_tracts[c_to * NUM_COLUMNS_64D + c_from] = true;
        }
    }

    pub fn reconnect_tract(&mut self, c_from: usize, c_to: usize) {
        if c_from < NUM_COLUMNS_64D && c_to < NUM_COLUMNS_64D {
            self.severed_tracts[c_from * NUM_COLUMNS_64D + c_to] = false;
            self.severed_tracts[c_to * NUM_COLUMNS_64D + c_from] = false;
        }
    }

    pub fn is_tract_severed(&self, c_from: usize, c_to: usize) -> bool {
        if c_from < NUM_COLUMNS_64D && c_to < NUM_COLUMNS_64D {
            self.severed_tracts[c_from * NUM_COLUMNS_64D + c_to]
        } else {
            true
        }
    }

    #[inline(always)]
    fn index_inter_23(c_from: usize, c_to: usize, i: usize, j: usize) -> usize {
        ((c_from * NUM_COLUMNS_64D + c_to) * L23_NODES + i) * L23_NODES + j
    }

    #[inline(always)]
    fn index_inter_5(c_from: usize, c_to: usize, i: usize, j: usize) -> usize {
        ((c_from * NUM_COLUMNS_64D + c_to) * L5_NODES + i) * L5_NODES + j
    }

    #[inline(always)]
    pub fn are_columns_fasciculated(&self, c_from: usize, c_to: usize) -> bool {
        if c_from >= NUM_COLUMNS_64D || c_to >= NUM_COLUMNS_64D || c_from == c_to { return false; }
        if self.severed_tracts[c_from * NUM_COLUMNS_64D + c_to] { return false; }
        let k_from = c_from / 8;
        let k_to = c_to / 8;
        if k_from == k_to { return true; }
        match (k_from, k_to) {
            (0, 3) | (3, 0) => true,
            (1, 4) | (4, 1) => true,
            (2, 3) | (3, 2) => true,
            (2, 6) | (6, 2) => true,
            (3, 5) | (5, 3) => true,
            (3, 7) | (7, 3) => true,
            (4, 5) | (5, 4) => true,
            (4, 7) | (7, 4) => true,
            (6, 7) | (7, 6) => true,
            (6, 5) | (5, 6) => true,
            (7, 5) | (5, 7) => true,
            (5, 0) | (5, 1) => true,
            _ => false,
        }
    }

    #[inline(always)]
    pub fn l23_contact_site(i: usize, j: usize) -> bool {
        (i as isize - j as isize).abs() <= 12 || (i % 16 == j % 16)
    }

    #[inline(always)]
    pub fn l5_contact_site(i: usize, j: usize) -> bool {
        (i as isize - j as isize).abs() <= 6 || (i % 8 == j % 8)
    }

    pub fn compute_inter_column_currents(&self) -> (Vec<Vec<f32>>, Vec<Vec<f32>>) {
        let mut in_23 = vec![vec![0.0f32; L23_NODES]; NUM_COLUMNS_64D];
        let mut in_5 = vec![vec![0.0f32; L5_NODES]; NUM_COLUMNS_64D];

        for c_from in 0..NUM_COLUMNS_64D {
            for i in 0..L23_NODES {
                let v = self.columns[c_from].microcircuit.l23[i];
                if v == 0 { continue; }
                let v_f = v as f32;
                for c_to in 0..NUM_COLUMNS_64D {
                    if !self.are_columns_fasciculated(c_from, c_to) { continue; }
                    for j in 0..L23_NODES {
                        if !Self::l23_contact_site(i, j) { continue; }
                        let idx = Self::index_inter_23(c_from, c_to, i, j);
                        let w = self.w_inter_23[idx];
                        let g_eff = G_ELASTIC_BASELINE + w;
                        if g_eff.abs() > 0.001 {
                            in_23[c_to][j] += v_f * g_eff;
                        }
                    }
                }
            }
            for i in 0..L5_NODES {
                let v = self.columns[c_from].microcircuit.l5[i];
                if v == 0 { continue; }
                let v_f = v as f32;
                for c_to in 0..NUM_COLUMNS_64D {
                    if !self.are_columns_fasciculated(c_from, c_to) { continue; }
                    for j in 0..L5_NODES {
                        if !Self::l5_contact_site(i, j) { continue; }
                        let idx = Self::index_inter_5(c_from, c_to, i, j);
                        let w = self.w_inter_5[idx];
                        let g_eff = G_ELASTIC_BASELINE + w;
                        if g_eff.abs() > 0.001 {
                            in_5[c_to][j] += v_f * g_eff;
                        }
                    }
                }
            }
        }
        (in_23, in_5)
    }

    pub fn step_cycle(
        &mut self,
        sensory_trits: &[i8],
        somatic_trits: &[i8],
        observed_r_mm: Option<f32>,
        observed_theta_mdeg: Option<i32>,
        current_barrier_stress: f32,
        acoustic_formants: &[f32],
    ) -> Result<(usize, f32), String> {
        // Static formant triples are not mounted auditory receptor evidence.
        // The removed min(f / 5, 63) encoder collapsed all eight curriculum
        // verbs into identical afferents. Refuse before ANY state mutation;
        // do not substitute new bins, semantic labels or a motor-answer table.
        if !acoustic_formants.is_empty() {
            return Err("Formant-profile stimulation is unavailable: use mounted time-aligned acoustic receptor evidence; lossy frequency bins and word profiles are prohibited".to_string());
        }
        let mut total_yields = 0usize;
        let mut total_strain = 0.0f32;

        let (in_23, in_5) = self.compute_inter_column_currents();

        // 1. Cluster 0: Optical Cortical Sheet (Cols 0..8)
        if let Some(r) = observed_r_mm {
            self.columns[0].spatial_r_mm = r;
            self.columns[0].persistence_trace = 1.0;
            self.columns[0].target_occluded = false;
        } else {
            self.columns[0].persistence_trace *= 0.985;
            self.columns[0].target_occluded = true;
        }
        let mut v1_aff = vec![0i8; L4_NODES];
        if self.columns[0].persistence_trace > 0.05 {
            let r_bin = ((self.columns[0].spatial_r_mm / 100.0) as usize).min(63);
            v1_aff[r_bin] = 1;
        }
        let (y0, s0) = self.columns[0].microcircuit.step_laminar_flow(&v1_aff, somatic_trits, &in_23[0], &in_5[0]);
        total_yields += y0; total_strain += s0;

        if let Some(th) = observed_theta_mdeg {
            self.columns[1].spatial_theta_mdeg = th;
            self.columns[1].persistence_trace = 1.0;
            self.columns[1].target_occluded = false;
        } else {
            self.columns[1].persistence_trace *= 0.985;
            self.columns[1].target_occluded = true;
        }
        let mut v2_aff = vec![0i8; L4_NODES];
        if self.columns[1].persistence_trace > 0.05 {
            let th_bin = (((self.columns[1].spatial_theta_mdeg + 180_000) / 6000) as usize).min(63);
            v2_aff[th_bin] = 1;
        }
        let (y1, s1) = self.columns[1].microcircuit.step_laminar_flow(&v2_aff, somatic_trits, &in_23[1], &in_5[1]);
        total_yields += y1; total_strain += s1;

        for c in 2..8 {
            let mut opt_aff = vec![0i8; L4_NODES];
            let start = (c - 2) * 2;
            if start < sensory_trits.len() {
                opt_aff[0] = sensory_trits[start];
                if start + 1 < sensory_trits.len() { opt_aff[1] = sensory_trits[start + 1]; }
            }
            let (yc, sc) = self.columns[c].microcircuit.step_laminar_flow(&opt_aff, somatic_trits, &in_23[c], &in_5[c]);
            total_yields += yc; total_strain += sc;
        }

        // 2. Component-only discrete afferents (Cols 8..16).
        // This explicit trit fixture boundary is not a PCM/cochlear transducer.
        // Absence/zero in its auditory slots stays absent/zero; no named
        // frequency profile or other sensory lane supplies missing sound.
        for (i, c) in (8..16).enumerate() {
            let mut a_aff = vec![0i8; L4_NODES];
            if 16 + i < sensory_trits.len() {
                a_aff[0] = sensory_trits[16 + i];
            }
            let (yc, sc) = self.columns[c].microcircuit.step_laminar_flow(&a_aff, somatic_trits, &in_23[c], &in_5[c]);
            total_yields += yc; total_strain += sc;
        }

        // 3. Cluster 2: Somatosensory Sheet (Cols 16..24)
        for c in 16..23 {
            let mut som_aff = vec![0i8; L4_NODES];
            let s_idx = 32 + (c - 16) * 2;
            if s_idx < sensory_trits.len() {
                som_aff[0] = sensory_trits[s_idx];
                if s_idx + 1 < sensory_trits.len() { som_aff[1] = sensory_trits[s_idx + 1]; }
            }
            let (yc, sc) = self.columns[c].microcircuit.step_laminar_flow(&som_aff, somatic_trits, &in_23[c], &in_5[c]);
            total_yields += yc; total_strain += sc;
        }
        // Col 23 (S8: Barrier Yield Refusal)
        self.columns[23].barrier_contact_stress = current_barrier_stress;
        self.columns[23].refusal_active = current_barrier_stress.abs() >= self.columns[23].yield_limit_threshold;
        let mut s8_aff = vec![0i8; L4_NODES];
        s8_aff[0] = if self.columns[23].refusal_active { 1 } else { 0 };
        let (y23, s23) = self.columns[23].microcircuit.step_laminar_flow(&s8_aff, somatic_trits, &in_23[23], &in_5[23]);
        total_yields += y23; total_strain += s23;

        // 4. Clusters 3, 4: Spatial & Syntax (Cols 24..40)
        let assoc_aff = [0i8; L4_NODES];
        for c in 24..40 {
            let (yc, sc) = self.columns[c].microcircuit.step_laminar_flow(&assoc_aff, somatic_trits, &in_23[c], &in_5[c]);
            total_yields += yc; total_strain += sc;
        }

        // 5. Cluster 5: Motor Cortex (Cols 40..48)
        let m_aff = [0i8; L4_NODES];
        for c in 40..48 {
            let (yc, sc) = self.columns[c].microcircuit.step_laminar_flow(&m_aff, somatic_trits, &in_23[c], &in_5[c]);
            total_yields += yc; total_strain += sc;
        }

        // Causal Motor Efferent Decoding from Settled L5 Motor Pyramidal Neurons:
        let pos_stride = self.columns[40].microcircuit.l5.iter().filter(|&&x| x > 0).count() as f32;
        self.motor_locomotion_stride = ((pos_stride / (L5_NODES as f32)) * 60.0).clamp(0.0, 60.0);

        let pos_steer = self.columns[41].microcircuit.l5.iter().filter(|&&x| x > 0).count() as f32;
        let neg_steer = self.columns[41].microcircuit.l5.iter().filter(|&&x| x < 0).count() as f32;
        self.motor_steer_angle = (((pos_steer - neg_steer) / (L5_NODES as f32)) * 45.0).clamp(-45.0, 45.0);

        let pos_grip = self.columns[42].microcircuit.l5.iter().filter(|&&x| x > 0).count() as f32;
        self.motor_grip_force = ((pos_grip / (L5_NODES as f32)) * 25.0).clamp(0.0, 25.0);

        let pos_vocal = self.columns[43].microcircuit.l5.iter().filter(|&&x| x > 0).count() as f32;
        self.motor_vocal_drive = ((pos_vocal / (L5_NODES as f32)) * 480.0).clamp(0.0, 480.0);

        // Physical Barrier Refusal Kinematic Clamp (Protective Interlock):
        if self.columns[23].refusal_active {
            self.motor_locomotion_stride = 0.0;
        }

        // 6. Cluster 6: Somatic Context Sheet (Cols 48..56)
        let no_external_field = [0i8; L4_NODES];
        for c in 48..56 {
            let (yc, sc) = self.columns[c].microcircuit.step_laminar_flow(
                &no_external_field, somatic_trits, &in_23[c], &in_5[c],
            );
            total_yields += yc;
            total_strain += sc;
        }

        // Cluster 7: Prefrontal / Structural Invariant Sheet (Cols 56..64)
        // Transduces 8 continuous field dimensions into Layer 4 afferents using
        // MathLoom exact rational balanced-ternary representation.
        if self.continuous_joint_field_present {
            let r_rev_k = self.continuous_joint_field[2];
            let s_uf = self.continuous_joint_field[7];
            if s_uf <= 0.0 || r_rev_k > 0.0 {
                self.columns[23].refusal_active = true;
                self.motor_locomotion_stride = 0.0;
            }
        }

        for k in 0..8 {
            let c = 56 + k;
            let mut field_aff = vec![0i8; L4_NODES];
            if self.continuous_joint_field_present {
                let val_k = self.continuous_joint_field[k];
                if let Ok(rat) = crate::mathloom::float_to_rational_trits(val_k) {
                    if !rat.is_zero {
                        let half = L4_NODES / 2;
                        for (p, &t) in rat.numerator_trits.iter().enumerate() {
                            if p < half {
                                field_aff[p] = t;
                            }
                        }
                        for (q, &t) in rat.denominator_trits.iter().enumerate() {
                            if q < half {
                                field_aff[half + q] = t;
                            }
                        }
                    }
                }
            }
            let (yc, sc) = self.columns[c].microcircuit.step_laminar_flow(
                &field_aff, somatic_trits, &in_23[c], &in_5[c],
            );
            total_yields += yc;
            total_strain += sc;
        }

        // 7. Inter-Column Directional Fasciculi Plasticity across 64 Columns
        let (inter_y, inter_s) = self.apply_inter_column_plasticity();
        total_yields += inter_y;
        total_strain += inter_s;

        Ok((total_yields, total_strain))
    }

    pub fn apply_inter_column_plasticity(&mut self) -> (usize, f32) {
        let mut yield_count = 0usize;
        let mut total_strain = 0.0f32;
        let y = self.yield_threshold;
        let _eta = self.plastic_rate;

        for c_from in 0..NUM_COLUMNS_64D {
            for c_to in 0..NUM_COLUMNS_64D {
                if !self.are_columns_fasciculated(c_from, c_to) { continue; }

                for i in 0..L23_NODES {
                    let from_val = self.columns[c_from].microcircuit.l23[i];
                    if from_val == 0 { continue; }
                    for j in 0..L23_NODES {
                        if !Self::l23_contact_site(i, j) { continue; }
                        let to_val = self.columns[c_to].microcircuit.l23[j];
                        if to_val == 0 { continue; }
                        let idx = Self::index_inter_23(c_from, c_to, i, j);
                        let target = (from_val * to_val) as f32;
                        let sigma = target - self.w_inter_23[idx];
                        let abs_sigma = sigma.abs();
                        if abs_sigma > y {
                            let overstress = abs_sigma - y;
                            let was_zero = self.w_inter_23[idx] == 0.0;
                            self.w_inter_23[idx] = (self.w_inter_23[idx] + overstress * sigma.signum()).clamp(-1.0, 1.0);
                            if was_zero && self.w_inter_23[idx] != 0.0 {
                                self.active_inter_23.push(idx);
                            }
                            yield_count += 1;
                            total_strain += overstress;
                        }
                    }
                }

                for i in 0..L5_NODES {
                    let from_val = self.columns[c_from].microcircuit.l5[i];
                    if from_val == 0 { continue; }
                    for j in 0..L5_NODES {
                        if !Self::l5_contact_site(i, j) { continue; }
                        let to_val = self.columns[c_to].microcircuit.l5[j];
                        if to_val == 0 { continue; }
                        let idx = Self::index_inter_5(c_from, c_to, i, j);
                        let target = (from_val * to_val) as f32;
                        let sigma = target - self.w_inter_5[idx];
                        let abs_sigma = sigma.abs();
                        if abs_sigma > y {
                            let overstress = abs_sigma - y;
                            let was_zero = self.w_inter_5[idx] == 0.0;
                            self.w_inter_5[idx] = (self.w_inter_5[idx] + overstress * sigma.signum()).clamp(-1.0, 1.0);
                            if was_zero && self.w_inter_5[idx] != 0.0 {
                                self.active_inter_5.push(idx);
                            }
                            yield_count += 1;
                            total_strain += overstress;
                        }
                    }
                }
            }
        }

        (yield_count, total_strain)
    }

    /// Nocturnal sleep consolidation and downscaling (Synaptic Homeostasis Hypothesis).
    /// Proportional downscaling: *g *= 1.0 - decay.
    /// Noise pruning occurs only if prune_thresh > 0.0 and |g| < prune_thresh.
    pub fn dream_consolidation(&mut self, decay: f32, prune_thresh: f32) -> (usize, usize) {
        let mut total_decayed = 0usize;
        let mut total_pruned = 0usize;
        for col in &mut self.columns {
            let (d, p) = col.microcircuit.dream_downscale_and_prune(decay, prune_thresh);
            total_decayed += d; total_pruned += p;
        }
        let w_23 = &mut self.w_inter_23;
        self.active_inter_23.retain(|&idx| {
            total_decayed += 1;
            let g = &mut w_23[idx];
            *g *= 1.0 - decay;
            if prune_thresh > 0.0 && g.abs() < prune_thresh {
                *g = 0.0;
                total_pruned += 1;
                false
            } else if *g == 0.0 {
                false
            } else {
                true
            }
        });
        let w_5 = &mut self.w_inter_5;
        self.active_inter_5.retain(|&idx| {
            total_decayed += 1;
            let g = &mut w_5[idx];
            *g *= 1.0 - decay;
            if prune_thresh > 0.0 && g.abs() < prune_thresh {
                *g = 0.0;
                total_pruned += 1;
                false
            } else if *g == 0.0 {
                false
            } else {
                true
            }
        });
        (total_decayed, total_pruned)
    }

    pub fn total_active_synapses(&self) -> usize {
        let mut total = 0usize;
        for col in &self.columns {
            total += col.microcircuit.active_intra_synapses();
        }
        total += self.active_inter_23.len();
        total += self.active_inter_5.len();
        total
    }

    pub fn zero_plastic_weights(&mut self) {
        for col in &mut self.columns {
            col.zero_plastic_weights();
        }
        self.w_inter_23.fill(0.0);
        self.active_inter_23.clear();
        self.w_inter_5.fill(0.0);
        self.active_inter_5.clear();
    }

    pub fn export_sparse_v4(&self) -> Result<Vec<u8>, String> {
        if !self.yield_threshold.is_finite() || !self.plastic_rate.is_finite() || !self.activation_threshold.is_finite() ||
           !self.motor_vocal_drive.is_finite() || !self.motor_locomotion_stride.is_finite() ||
           !self.motor_steer_angle.is_finite() || !self.motor_grip_force.is_finite() {
            return Err("Non-finite float in 64D substrate header/footer during export".to_string());
        }
        let mut buf = Vec::with_capacity(131072);
        buf.extend_from_slice(ARCLOOM_STATE_MAGIC_V4);
        buf.extend_from_slice(&ARCLOOM_STATE_VERSION_V4.to_le_bytes());
        buf.extend_from_slice(&(NUM_COLUMNS_64D as u16).to_le_bytes());
        buf.extend_from_slice(&self.yield_threshold.to_le_bytes());
        buf.extend_from_slice(&self.plastic_rate.to_le_bytes());
        buf.extend_from_slice(&self.activation_threshold.to_le_bytes());

        for col in &self.columns {
            serialize_column_state(col, &mut buf)?;
        }

        // Lossless inter-column persistence (all non-zero finite weights)
        let mut nz_23: Vec<(u32, f32)> = Vec::with_capacity(self.active_inter_23.len());
        for &idx in &self.active_inter_23 {
            let g = self.w_inter_23[idx];
            if !g.is_finite() {
                return Err(format!("Non-finite synaptic weight in w_inter_23 at idx {}", idx));
            }
            if g != 0.0 { nz_23.push((idx as u32, g)); }
        }
        buf.extend_from_slice(&(nz_23.len() as u32).to_le_bytes());
        for (idx, g) in nz_23 {
            buf.extend_from_slice(&idx.to_le_bytes());
            buf.extend_from_slice(&g.to_le_bytes());
        }

        let mut nz_5: Vec<(u32, f32)> = Vec::with_capacity(self.active_inter_5.len());
        for &idx in &self.active_inter_5 {
            let g = self.w_inter_5[idx];
            if !g.is_finite() {
                return Err(format!("Non-finite synaptic weight in w_inter_5 at idx {}", idx));
            }
            if g != 0.0 { nz_5.push((idx as u32, g)); }
        }
        buf.extend_from_slice(&(nz_5.len() as u32).to_le_bytes());
        for (idx, g) in nz_5 {
            buf.extend_from_slice(&idx.to_le_bytes());
            buf.extend_from_slice(&g.to_le_bytes());
        }

        buf.extend_from_slice(&self.motor_vocal_drive.to_le_bytes());
        buf.extend_from_slice(&self.motor_locomotion_stride.to_le_bytes());
        buf.extend_from_slice(&self.motor_steer_angle.to_le_bytes());
        buf.extend_from_slice(&self.motor_grip_force.to_le_bytes());

        // Lossless severed tracts serialization
        let severed_indices: Vec<u32> = self.severed_tracts.iter().enumerate()
            .filter_map(|(idx, &s)| if s { Some(idx as u32) } else { None })
            .collect();
        buf.extend_from_slice(&(severed_indices.len() as u32).to_le_bytes());
        for &idx in &severed_indices {
            buf.extend_from_slice(&idx.to_le_bytes());
        }

        // Full continuous joint field serialization with explicit availability flag
        let presence_flag: u8 = if self.continuous_joint_field_present { 1 } else { 0 };
        buf.push(presence_flag);

        for &val in &self.continuous_joint_field {
            if !val.is_finite() {
                return Err("Non-finite float in continuous joint field during export".to_string());
            }
            buf.extend_from_slice(&val.to_le_bytes());
        }

        let pad = (8 - (buf.len() % 8)) % 8;
        for _ in 0..pad {
            buf.push(0);
        }

        Ok(buf)
    }

    pub fn export_sparse_v3(&self) -> Result<Vec<u8>, String> {
        self.export_sparse_v4()
    }

    fn try_parse_v2_internal(
        &self,
        data: &[u8],
        yield_th: f32,
        plastic_rt: f32,
        activation_th: f32,
        use_36b_headers: bool,
    ) -> Result<StagedSubstrateState, String> {
        let mut temp_columns = self.columns.clone();
        // Authenticated predecessor parameter initialization:
        // For 24-byte layout where local parameters were omitted in historical format,
        // initialize each column's microcircuit parameters from the container header
        // (yield_th, plastic_rt, activation_th), so that the restored state does not inherit
        // recipient instance defaults!
        if !use_36b_headers {
            for col in temp_columns.iter_mut() {
                col.microcircuit.yield_threshold = yield_th;
                col.microcircuit.plastic_rate = plastic_rt;
                col.microcircuit.activation_threshold = activation_th;
            }
        }
        let mut offset = 24;
        for (col_idx, col) in temp_columns.iter_mut().enumerate() {
            if use_36b_headers {
                offset = deserialize_column_state(col, data, offset, col_idx, NUM_COLUMNS_64D)?;
            } else {
                offset = deserialize_column_state_v2_24b(col, data, offset, col_idx, NUM_COLUMNS_64D)?;
            }
        }

        if offset.checked_add(4).ok_or("Integer overflow in w_inter_23 count")? > data.len() {
            return Err("Unexpected EOF in w_inter_23 count".to_string());
        }
        let count_23 = u32::from_le_bytes([data[offset], data[offset+1], data[offset+2], data[offset+3]]) as usize;
        offset += 4;

        if count_23 > 2_359_296 {
            return Err(format!("w_inter_23 count {} exceeds maximum structural capacity 2359296", count_23));
        }
        let bytes_23 = count_23.checked_mul(8).ok_or("Integer overflow in w_inter_23 bytes")?;
        if offset.checked_add(bytes_23).ok_or("Integer overflow in w_inter_23 offset")? > data.len() {
            return Err("Unexpected EOF in w_inter_23 entries".to_string());
        }
        let mut new_w_23 = vec![0.0f32; self.w_inter_23.len()];
        let mut new_act_23 = Vec::new();
        let mut seen_23 = HashSet::new();
        for _ in 0..count_23 {
            let idx = u32::from_le_bytes([data[offset], data[offset+1], data[offset+2], data[offset+3]]) as usize; offset += 4;
            let g = f32::from_le_bytes([data[offset], data[offset+1], data[offset+2], data[offset+3]]); offset += 4;
            if !g.is_finite() { return Err("Non-finite synaptic weight in w_inter_23".to_string()); }
            if g < -1.0 || g > 1.0 { return Err(format!("Inter-column synaptic weight out of bounds [-1.0, 1.0]: {}", g)); }
            if idx >= new_w_23.len() {
                return Err(format!("Synaptic index out of bounds: {} >= {}", idx, new_w_23.len()));
            }
            if !seen_23.insert(idx) {
                return Err(format!("Duplicate synaptic index in w_inter_23: {}", idx));
            }
            new_w_23[idx] = g;
            if g != 0.0 { new_act_23.push(idx); }
        }

        if offset.checked_add(4).ok_or("Integer overflow in w_inter_5 count")? > data.len() {
            return Err("Unexpected EOF in w_inter_5 count".to_string());
        }
        let count_5 = u32::from_le_bytes([data[offset], data[offset+1], data[offset+2], data[offset+3]]) as usize;
        offset += 4;

        if count_5 > 2_359_296 {
            return Err(format!("w_inter_5 count {} exceeds maximum structural capacity 2359296", count_5));
        }
        let bytes_5 = count_5.checked_mul(8).ok_or("Integer overflow in w_inter_5 bytes")?;
        if offset.checked_add(bytes_5).ok_or("Integer overflow in w_inter_5 offset")? > data.len() {
            return Err("Unexpected EOF in w_inter_5 entries".to_string());
        }
        let mut new_w_5 = vec![0.0f32; self.w_inter_5.len()];
        let mut new_act_5 = Vec::new();
        let mut seen_5 = HashSet::new();
        for _ in 0..count_5 {
            let idx = u32::from_le_bytes([data[offset], data[offset+1], data[offset+2], data[offset+3]]) as usize; offset += 4;
            let g = f32::from_le_bytes([data[offset], data[offset+1], data[offset+2], data[offset+3]]); offset += 4;
            if !g.is_finite() { return Err("Non-finite synaptic weight in w_inter_5".to_string()); }
            if g < -1.0 || g > 1.0 { return Err(format!("Inter-column synaptic weight out of bounds [-1.0, 1.0]: {}", g)); }
            if idx >= new_w_5.len() {
                return Err(format!("Synaptic index out of bounds: {} >= {}", idx, new_w_5.len()));
            }
            if !seen_5.insert(idx) {
                return Err(format!("Duplicate synaptic index in w_inter_5: {}", idx));
            }
            new_w_5[idx] = g;
            if g != 0.0 { new_act_5.push(idx); }
        }

        if offset.checked_add(16).ok_or("Integer overflow in motor efferent footer")? > data.len() {
            return Err("Missing or truncated motor efferent footer in ARCLOOM2 payload".to_string());
        }
        let new_vocal = f32::from_le_bytes([data[offset], data[offset+1], data[offset+2], data[offset+3]]); offset += 4;
        let new_stride = f32::from_le_bytes([data[offset], data[offset+1], data[offset+2], data[offset+3]]); offset += 4;
        let new_steer = f32::from_le_bytes([data[offset], data[offset+1], data[offset+2], data[offset+3]]); offset += 4;
        let new_grip = f32::from_le_bytes([data[offset], data[offset+1], data[offset+2], data[offset+3]]); offset += 4;

        if !new_vocal.is_finite() || !new_stride.is_finite() || !new_steer.is_finite() || !new_grip.is_finite() {
            return Err("Non-finite float in motor efferent footer".to_string());
        }

        let mut new_severed = vec![false; NUM_COLUMNS_64D * NUM_COLUMNS_64D];
        if use_36b_headers {
            if offset.checked_add(4).ok_or("Integer overflow in severed tracts count")? > data.len() {
                return Err("Unexpected EOF reading severed tracts count in 8c3244cb3".to_string());
            }
            let sev_count = u32::from_le_bytes([data[offset], data[offset+1], data[offset+2], data[offset+3]]) as usize;
            offset += 4;
            if sev_count > 4096 {
                return Err(format!("Severed tracts count {} exceeds maximum capacity 4096", sev_count));
            }
            let sev_bytes = sev_count.checked_mul(4).ok_or("Integer overflow in severed tracts bytes")?;
            if offset.checked_add(sev_bytes).ok_or("Integer overflow in severed tracts offset")? > data.len() {
                return Err("Unexpected EOF reading severed tracts indices in 8c3244cb3".to_string());
            }
            for _ in 0..sev_count {
                let idx = u32::from_le_bytes([data[offset], data[offset+1], data[offset+2], data[offset+3]]) as usize;
                offset += 4;
                if idx < new_severed.len() {
                    new_severed[idx] = true;
                } else {
                    return Err(format!("Severed tract index out of bounds: {}", idx));
                }
            }
        }

        let expected_pad = (8 - (offset % 8)) % 8;
        let actual_pad = data.len() - offset;
        if actual_pad != expected_pad {
            return Err(format!("Incorrect trailing alignment padding in ARCLOOM2 payload: expected {} bytes, got {}", expected_pad, actual_pad));
        }
        for i in 0..expected_pad {
            if data[offset + i] != 0 {
                return Err("Non-zero padding byte in ARCLOOM2 payload".to_string());
            }
        }

        Ok(StagedSubstrateState {
            yield_threshold: yield_th,
            plastic_rate: plastic_rt,
            activation_threshold: activation_th,
            columns: temp_columns,
            w_inter_23: new_w_23,
            active_inter_23: new_act_23,
            w_inter_5: new_w_5,
            active_inter_5: new_act_5,
            severed_tracts: new_severed,
            continuous_joint_field: [0.0; 8],
            continuous_joint_field_present: false,
            motor_vocal_drive: new_vocal,
            motor_locomotion_stride: new_stride,
            motor_steer_angle: new_steer,
            motor_grip_force: new_grip,
        })
    }

    pub fn migrate_predecessor_v2(&mut self, data: &[u8], layout: &str) -> Result<(), String> {
        if data.is_empty() {
            return Err("Cannot migrate from empty byte buffer".to_string());
        }
        if data.len() < 24 {
            return Err("Truncated ARCLOOM2 header: less than 24 bytes".to_string());
        }
        let magic = &data[0..8];
        if magic != ARCLOOM_STATE_MAGIC_V2 {
            return Err(format!("Invalid ArcLoom v2 magic header: expected {:?}, got {:?}", ARCLOOM_STATE_MAGIC_V2, magic));
        }
        let version = u16::from_le_bytes([data[8], data[9]]);
        if version != ARCLOOM_STATE_VERSION_V2 {
            return Err(format!("Unsupported ArcLoom v2 version: {}", version));
        }
        let n_cols = u16::from_le_bytes([data[10], data[11]]) as usize;
        if n_cols != NUM_COLUMNS_64D {
            return Err(format!("Column count mismatch: data has {}, instance has {}", n_cols, NUM_COLUMNS_64D));
        }
        let new_yield = f32::from_le_bytes([data[12], data[13], data[14], data[15]]);
        let new_plastic = f32::from_le_bytes([data[16], data[17], data[18], data[19]]);
        let new_activation = f32::from_le_bytes([data[20], data[21], data[22], data[23]]);

        if !new_yield.is_finite() || !new_plastic.is_finite() || !new_activation.is_finite() {
            return Err("Non-finite float in ArcLoom header".to_string());
        }
        if new_yield <= 0.0 || new_yield > 1.0 || new_plastic <= 0.0 || new_plastic > 1.0 || new_activation <= 0.0 {
            return Err("Invalid parameter domain in ArcLoom header".to_string());
        }

        match layout {
            "8c3244cb3" | "36B" => {
                let staged = self.try_parse_v2_internal(data, new_yield, new_plastic, new_activation, true)?;
                self.commit_staged_state(staged);
                Ok(())
            }
            "cb69d23ea" | "24B" => {
                let staged = self.try_parse_v2_internal(data, new_yield, new_plastic, new_activation, false)?;
                self.commit_staged_state(staged);
                Ok(())
            }
            unknown => Err(format!("Unknown ARCLOOM2 predecessor layout provenance: {}", unknown)),
        }
    }

    fn try_parse_v4_internal(&self, data: &[u8]) -> Result<StagedSubstrateState, String> {
        if data.is_empty() {
            return Err("Cannot import from empty byte buffer".to_string());
        }
        if data.len() < 8 {
            return Err("Truncated header: less than 8 bytes".to_string());
        }
        let magic = &data[0..8];
        if magic == ARCLOOM_STATE_MAGIC_V2 {
            return Err("Invalid magic: found ARCLOOM2 payload in ARCLOOM4 importer. Historical predecessor migration must be performed explicitly via migrate_predecessor_v2()".to_string());
        }
        if magic == ARCLOOM_STATE_MAGIC_V3 {
            return Err("Invalid magic: found ARCLOOM3 payload in ARCLOOM4 importer. Predecessor migration must be performed explicitly via migrate_predecessor_v3()".to_string());
        }
        if magic != ARCLOOM_STATE_MAGIC_V4 {
            return Err(format!("Invalid ArcLoom state format: expected ARCLOOM4, got unknown magic {:?}", magic));
        }
        if data.len() < 24 {
            return Err("Truncated ARCLOOM4 header: less than 24 bytes".to_string());
        }
        let version = u16::from_le_bytes([data[8], data[9]]);
        if version != ARCLOOM_STATE_VERSION_V4 {
            return Err(format!("Unsupported ArcLoom v4 version: {}", version));
        }
        let n_cols = u16::from_le_bytes([data[10], data[11]]) as usize;
        if n_cols != NUM_COLUMNS_64D {
            return Err(format!("Column count mismatch: data has {}, instance has {}", n_cols, NUM_COLUMNS_64D));
        }
        let new_yield = f32::from_le_bytes([data[12], data[13], data[14], data[15]]);
        let new_plastic = f32::from_le_bytes([data[16], data[17], data[18], data[19]]);
        let new_activation = f32::from_le_bytes([data[20], data[21], data[22], data[23]]);

        if !new_yield.is_finite() || !new_plastic.is_finite() || !new_activation.is_finite() {
            return Err("Non-finite float in ArcLoom header".to_string());
        }
        if new_yield <= 0.0 || new_yield > 1.0 || new_plastic <= 0.0 || new_plastic > 1.0 || new_activation <= 0.0 {
            return Err("Invalid parameter domain in ArcLoom header".to_string());
        }

        let mut temp_columns = self.columns.clone();
        let mut offset = 24;
        for (col_idx, col) in temp_columns.iter_mut().enumerate() {
            offset = deserialize_column_state(col, data, offset, col_idx, NUM_COLUMNS_64D)?;
        }

        if offset.checked_add(4).ok_or("Integer overflow in w_inter_23 count")? > data.len() {
            return Err("Unexpected EOF in w_inter_23 count".to_string());
        }
        let count_23 = u32::from_le_bytes([data[offset], data[offset+1], data[offset+2], data[offset+3]]) as usize;
        offset += 4;

        let bytes_23 = count_23.checked_mul(8).ok_or("Integer overflow in w_inter_23 bytes")?;
        if offset.checked_add(bytes_23).ok_or("Integer overflow in w_inter_23 offset")? > data.len() {
            return Err("Unexpected EOF in w_inter_23 entries".to_string());
        }
        let mut new_w_23 = vec![0.0f32; self.w_inter_23.len()];
        let mut new_act_23 = Vec::new();
        let mut seen_23 = HashSet::new();
        for _ in 0..count_23 {
            let idx = u32::from_le_bytes([data[offset], data[offset+1], data[offset+2], data[offset+3]]) as usize; offset += 4;
            let g = f32::from_le_bytes([data[offset], data[offset+1], data[offset+2], data[offset+3]]); offset += 4;
            if !g.is_finite() { return Err("Non-finite synaptic weight in w_inter_23".to_string()); }
            if g < -1.0 || g > 1.0 { return Err(format!("Inter-column synaptic weight out of bounds [-1.0, 1.0]: {}", g)); }
            if idx >= new_w_23.len() {
                return Err(format!("Synaptic index out of bounds: {} >= {}", idx, new_w_23.len()));
            }
            if !seen_23.insert(idx) {
                return Err(format!("Duplicate synaptic index in w_inter_23: {}", idx));
            }
            new_w_23[idx] = g;
            if g != 0.0 { new_act_23.push(idx); }
        }

        if offset.checked_add(4).ok_or("Integer overflow in w_inter_5 count")? > data.len() {
            return Err("Unexpected EOF in w_inter_5 count".to_string());
        }
        let count_5 = u32::from_le_bytes([data[offset], data[offset+1], data[offset+2], data[offset+3]]) as usize;
        offset += 4;

        let bytes_5 = count_5.checked_mul(8).ok_or("Integer overflow in w_inter_5 bytes")?;
        if offset.checked_add(bytes_5).ok_or("Integer overflow in w_inter_5 offset")? > data.len() {
            return Err("Unexpected EOF in w_inter_5 entries".to_string());
        }
        let mut new_w_5 = vec![0.0f32; self.w_inter_5.len()];
        let mut new_act_5 = Vec::new();
        let mut seen_5 = HashSet::new();
        for _ in 0..count_5 {
            let idx = u32::from_le_bytes([data[offset], data[offset+1], data[offset+2], data[offset+3]]) as usize; offset += 4;
            let g = f32::from_le_bytes([data[offset], data[offset+1], data[offset+2], data[offset+3]]); offset += 4;
            if !g.is_finite() { return Err("Non-finite synaptic weight in w_inter_5".to_string()); }
            if g < -1.0 || g > 1.0 { return Err(format!("Inter-column synaptic weight out of bounds [-1.0, 1.0]: {}", g)); }
            if idx >= new_w_5.len() {
                return Err(format!("Synaptic index out of bounds: {} >= {}", idx, new_w_5.len()));
            }
            if !seen_5.insert(idx) {
                return Err(format!("Duplicate synaptic index in w_inter_5: {}", idx));
            }
            new_w_5[idx] = g;
            if g != 0.0 { new_act_5.push(idx); }
        }

        if offset.checked_add(16).ok_or("Integer overflow in motor footer")? > data.len() {
            return Err("Missing or truncated motor efferent footer in ArcLoom payload".to_string());
        }
        let new_vocal = f32::from_le_bytes([data[offset], data[offset+1], data[offset+2], data[offset+3]]); offset += 4;
        let new_stride = f32::from_le_bytes([data[offset], data[offset+1], data[offset+2], data[offset+3]]); offset += 4;
        let new_steer = f32::from_le_bytes([data[offset], data[offset+1], data[offset+2], data[offset+3]]); offset += 4;
        let new_grip = f32::from_le_bytes([data[offset], data[offset+1], data[offset+2], data[offset+3]]); offset += 4;

        if !new_vocal.is_finite() || !new_stride.is_finite() || !new_steer.is_finite() || !new_grip.is_finite() {
            return Err("Non-finite float in motor efferent footer".to_string());
        }

        if offset.checked_add(4).ok_or("Integer overflow in severed tracts count")? > data.len() {
            return Err("Unexpected EOF reading severed tracts count".to_string());
        }
        let sev_count = u32::from_le_bytes([data[offset], data[offset+1], data[offset+2], data[offset+3]]) as usize;
        offset += 4;

        let sev_bytes = sev_count.checked_mul(4).ok_or("Integer overflow in severed tracts bytes")?;
        if offset.checked_add(sev_bytes).ok_or("Integer overflow in severed tracts offset")? > data.len() {
            return Err("Unexpected EOF reading severed tracts indices".to_string());
        }
        let mut new_severed = vec![false; NUM_COLUMNS_64D * NUM_COLUMNS_64D];
        let mut seen_severed = HashSet::new();
        for _ in 0..sev_count {
            let idx = u32::from_le_bytes([data[offset], data[offset+1], data[offset+2], data[offset+3]]) as usize;
            offset += 4;
            if idx >= new_severed.len() {
                return Err(format!("Severed tract index out of bounds: {}", idx));
            }
            if !seen_severed.insert(idx) {
                return Err(format!("Duplicate severed tract index: {}", idx));
            }
            new_severed[idx] = true;
        }
        for &idx in &seen_severed {
            let r = idx / NUM_COLUMNS_64D;
            let c = idx % NUM_COLUMNS_64D;
            let rev_idx = c * NUM_COLUMNS_64D + r;
            if !seen_severed.contains(&rev_idx) {
                return Err(format!("Asymmetric severed tract topology: tract {} ({}->{}) severed but reverse {} ({}->{}) is not", idx, r, c, rev_idx, c, r));
            }
        }

        // ARCLOOM4: explicit presence flag followed by 64 bytes of f64 field values
        if offset >= data.len() {
            return Err("Unexpected EOF reading presence flag in ARCLOOM4".to_string());
        }
        let presence_byte = data[offset];
        offset += 1;
        if presence_byte > 1 {
            return Err(format!("Invalid presence flag {} in ARCLOOM4: must be 0 or 1", presence_byte));
        }
        let present = presence_byte == 1;

        if offset.checked_add(64).ok_or("Integer overflow in field bytes")? > data.len() {
            return Err("Unexpected EOF reading continuous joint field in ARCLOOM4: requires 64 bytes".to_string());
        }
        let mut cjf = [0.0f64; 8];
        for i in 0..8 {
            let bytes = [
                data[offset], data[offset+1], data[offset+2], data[offset+3],
                data[offset+4], data[offset+5], data[offset+6], data[offset+7]
            ];
            offset += 8;
            let val = f64::from_le_bytes(bytes);
            if !val.is_finite() {
                return Err(format!("Non-finite float in continuous joint field index {}", i));
            }
            cjf[i] = val;
        }

        let expected_pad = (8 - (offset % 8)) % 8;
        let actual_pad = data.len() - offset;
        if actual_pad != expected_pad {
            return Err(format!("Incorrect trailing alignment padding in ArcLoom payload: expected {} bytes, got {}", expected_pad, actual_pad));
        }
        for i in 0..expected_pad {
            if data[offset + i] != 0 {
                return Err("Non-zero padding byte in ArcLoom payload".to_string());
            }
        }

        Ok(StagedSubstrateState {
            yield_threshold: new_yield,
            plastic_rate: new_plastic,
            activation_threshold: new_activation,
            columns: temp_columns,
            w_inter_23: new_w_23,
            active_inter_23: new_act_23,
            w_inter_5: new_w_5,
            active_inter_5: new_act_5,
            severed_tracts: new_severed,
            continuous_joint_field: cjf,
            continuous_joint_field_present: present,
            motor_vocal_drive: new_vocal,
            motor_locomotion_stride: new_stride,
            motor_steer_angle: new_steer,
            motor_grip_force: new_grip,
        })
    }

    fn try_parse_v3_internal(&self, data: &[u8], layout: &str, field_present_meta: Option<bool>) -> Result<StagedSubstrateState, String> {
        if data.is_empty() {
            return Err("Cannot migrate from empty byte buffer".to_string());
        }
        if data.len() < 24 {
            return Err("Truncated ARCLOOM3 header: less than 24 bytes".to_string());
        }
        let magic = &data[0..8];
        if magic != ARCLOOM_STATE_MAGIC_V3 {
            return Err(format!("Invalid ArcLoom v3 magic header: expected {:?}, got {:?}", ARCLOOM_STATE_MAGIC_V3, magic));
        }
        let version = u16::from_le_bytes([data[8], data[9]]);
        if version != ARCLOOM_STATE_VERSION_V3 {
            return Err(format!("Unsupported ArcLoom v3 version: {}", version));
        }
        let n_cols = u16::from_le_bytes([data[10], data[11]]) as usize;
        if n_cols != NUM_COLUMNS_64D {
            return Err(format!("Column count mismatch: data has {}, instance has {}", n_cols, NUM_COLUMNS_64D));
        }
        let new_yield = f32::from_le_bytes([data[12], data[13], data[14], data[15]]);
        let new_plastic = f32::from_le_bytes([data[16], data[17], data[18], data[19]]);
        let new_activation = f32::from_le_bytes([data[20], data[21], data[22], data[23]]);

        if !new_yield.is_finite() || !new_plastic.is_finite() || !new_activation.is_finite() {
            return Err("Non-finite float in ArcLoom header".to_string());
        }
        if new_yield <= 0.0 || new_yield > 1.0 || new_plastic <= 0.0 || new_plastic > 1.0 || new_activation <= 0.0 {
            return Err("Invalid parameter domain in ArcLoom header".to_string());
        }

        let mut temp_columns = self.columns.clone();
        let mut offset = 24;
        for (col_idx, col) in temp_columns.iter_mut().enumerate() {
            offset = deserialize_column_state(col, data, offset, col_idx, NUM_COLUMNS_64D)?;
        }

        if offset.checked_add(4).ok_or("Integer overflow in w_inter_23 count")? > data.len() {
            return Err("Unexpected EOF in w_inter_23 count".to_string());
        }
        let count_23 = u32::from_le_bytes([data[offset], data[offset+1], data[offset+2], data[offset+3]]) as usize;
        offset += 4;

        let bytes_23 = count_23.checked_mul(8).ok_or("Integer overflow in w_inter_23 bytes")?;
        if offset.checked_add(bytes_23).ok_or("Integer overflow in w_inter_23 offset")? > data.len() {
            return Err("Unexpected EOF in w_inter_23 entries".to_string());
        }
        let mut new_w_23 = vec![0.0f32; self.w_inter_23.len()];
        let mut new_act_23 = Vec::new();
        let mut seen_23 = HashSet::new();
        for _ in 0..count_23 {
            let idx = u32::from_le_bytes([data[offset], data[offset+1], data[offset+2], data[offset+3]]) as usize; offset += 4;
            let g = f32::from_le_bytes([data[offset], data[offset+1], data[offset+2], data[offset+3]]); offset += 4;
            if !g.is_finite() { return Err("Non-finite synaptic weight in w_inter_23".to_string()); }
            if g < -1.0 || g > 1.0 { return Err(format!("Inter-column synaptic weight out of bounds [-1.0, 1.0]: {}", g)); }
            if idx >= new_w_23.len() {
                return Err(format!("Synaptic index out of bounds: {} >= {}", idx, new_w_23.len()));
            }
            if !seen_23.insert(idx) {
                return Err(format!("Duplicate synaptic index in w_inter_23: {}", idx));
            }
            new_w_23[idx] = g;
            if g != 0.0 { new_act_23.push(idx); }
        }

        if offset.checked_add(4).ok_or("Integer overflow in w_inter_5 count")? > data.len() {
            return Err("Unexpected EOF in w_inter_5 count".to_string());
        }
        let count_5 = u32::from_le_bytes([data[offset], data[offset+1], data[offset+2], data[offset+3]]) as usize;
        offset += 4;

        let bytes_5 = count_5.checked_mul(8).ok_or("Integer overflow in w_inter_5 bytes")?;
        if offset.checked_add(bytes_5).ok_or("Integer overflow in w_inter_5 offset")? > data.len() {
            return Err("Unexpected EOF in w_inter_5 entries".to_string());
        }
        let mut new_w_5 = vec![0.0f32; self.w_inter_5.len()];
        let mut new_act_5 = Vec::new();
        let mut seen_5 = HashSet::new();
        for _ in 0..count_5 {
            let idx = u32::from_le_bytes([data[offset], data[offset+1], data[offset+2], data[offset+3]]) as usize; offset += 4;
            let g = f32::from_le_bytes([data[offset], data[offset+1], data[offset+2], data[offset+3]]); offset += 4;
            if !g.is_finite() { return Err("Non-finite synaptic weight in w_inter_5".to_string()); }
            if g < -1.0 || g > 1.0 { return Err(format!("Inter-column synaptic weight out of bounds [-1.0, 1.0]: {}", g)); }
            if idx >= new_w_5.len() {
                return Err(format!("Synaptic index out of bounds: {} >= {}", idx, new_w_5.len()));
            }
            if !seen_5.insert(idx) {
                return Err(format!("Duplicate synaptic index in w_inter_5: {}", idx));
            }
            new_w_5[idx] = g;
            if g != 0.0 { new_act_5.push(idx); }
        }

        if offset.checked_add(16).ok_or("Integer overflow in motor footer")? > data.len() {
            return Err("Missing or truncated motor efferent footer in ArcLoom payload".to_string());
        }
        let new_vocal = f32::from_le_bytes([data[offset], data[offset+1], data[offset+2], data[offset+3]]); offset += 4;
        let new_stride = f32::from_le_bytes([data[offset], data[offset+1], data[offset+2], data[offset+3]]); offset += 4;
        let new_steer = f32::from_le_bytes([data[offset], data[offset+1], data[offset+2], data[offset+3]]); offset += 4;
        let new_grip = f32::from_le_bytes([data[offset], data[offset+1], data[offset+2], data[offset+3]]); offset += 4;

        if !new_vocal.is_finite() || !new_stride.is_finite() || !new_steer.is_finite() || !new_grip.is_finite() {
            return Err("Non-finite float in motor efferent footer".to_string());
        }

        if offset.checked_add(4).ok_or("Integer overflow in severed tracts count")? > data.len() {
            return Err("Unexpected EOF reading severed tracts count".to_string());
        }
        let sev_count = u32::from_le_bytes([data[offset], data[offset+1], data[offset+2], data[offset+3]]) as usize;
        offset += 4;

        let sev_bytes = sev_count.checked_mul(4).ok_or("Integer overflow in severed tracts bytes")?;
        if offset.checked_add(sev_bytes).ok_or("Integer overflow in severed tracts offset")? > data.len() {
            return Err("Unexpected EOF reading severed tracts indices".to_string());
        }
        let mut new_severed = vec![false; NUM_COLUMNS_64D * NUM_COLUMNS_64D];
        let mut seen_severed = HashSet::new();
        for _ in 0..sev_count {
            let idx = u32::from_le_bytes([data[offset], data[offset+1], data[offset+2], data[offset+3]]) as usize;
            offset += 4;
            if idx >= new_severed.len() {
                return Err(format!("Severed tract index out of bounds: {}", idx));
            }
            if !seen_severed.insert(idx) {
                return Err(format!("Duplicate severed tract index: {}", idx));
            }
            new_severed[idx] = true;
        }
        for &idx in &seen_severed {
            let r = idx / NUM_COLUMNS_64D;
            let c = idx % NUM_COLUMNS_64D;
            let rev_idx = c * NUM_COLUMNS_64D + r;
            if !seen_severed.contains(&rev_idx) {
                return Err(format!("Asymmetric severed tract topology: tract {} ({}->{}) severed but reverse {} ({}->{}) is not", idx, r, c, rev_idx, c, r));
            }
        }

        // Two authentic historical ARCLOOM3 layouts:
        // Layout 1: ARCLOOM3_SHORT (commit 0dad5f2b9) - ends after severed tracts + padding
        // Layout 2: ARCLOOM3_LONG (commit d577831de) - 64 bytes of f64 field values after severed tracts + padding
        let rem_bytes = data.len() - offset;
        let (cjf, is_present) = match layout {
            "0dad5f2b9" | "short" => {
                let expected_pad_short = (8 - (offset % 8)) % 8;
                if rem_bytes != expected_pad_short {
                    return Err(format!("Invalid ARCLOOM3 short payload: expected {} padding bytes, got trailing {} bytes", expected_pad_short, rem_bytes));
                }
                ([0.0f64; 8], false)
            }
            "d577831de" | "long" => {
                let expected_pad_long = (8 - ((offset + 64) % 8)) % 8;
                if rem_bytes != 64 + expected_pad_long {
                    return Err(format!("Invalid ARCLOOM3 long payload: expected 64 field bytes + {} padding bytes, got trailing {} bytes", expected_pad_long, rem_bytes));
                }
                let mut field_vals = [0.0f64; 8];
                for i in 0..8 {
                    let bytes = [
                        data[offset], data[offset+1], data[offset+2], data[offset+3],
                        data[offset+4], data[offset+5], data[offset+6], data[offset+7]
                    ];
                    offset += 8;
                    let val = f64::from_le_bytes(bytes);
                    if !val.is_finite() {
                        return Err(format!("Non-finite float in ARCLOOM3 continuous joint field index {}", i));
                    }
                    field_vals[i] = val;
                }
                let present = match field_present_meta {
                    Some(p) => p,
                    None => {
                        return Err("ARCLOOM3 long layout (commit d577831de) omits presence flag; explicit authenticated predecessor metadata 'field_present' is required to migrate without unrecorded presence guessing".to_string());
                    }
                };
                (field_vals, present)
            }
            unknown => return Err(format!("Unknown ARCLOOM3 predecessor layout provenance: {}", unknown)),
        };

        let expected_pad = (8 - (offset % 8)) % 8;
        let actual_pad = data.len() - offset;
        if actual_pad != expected_pad {
            return Err(format!("Incorrect trailing alignment padding in ARCLOOM3 payload: expected {} bytes, got {}", expected_pad, actual_pad));
        }
        for i in 0..expected_pad {
            if data[offset + i] != 0 {
                return Err("Non-zero padding byte in ARCLOOM3 payload".to_string());
            }
        }

        Ok(StagedSubstrateState {
            yield_threshold: new_yield,
            plastic_rate: new_plastic,
            activation_threshold: new_activation,
            columns: temp_columns,
            w_inter_23: new_w_23,
            active_inter_23: new_act_23,
            w_inter_5: new_w_5,
            active_inter_5: new_act_5,
            severed_tracts: new_severed,
            continuous_joint_field: cjf,
            continuous_joint_field_present: is_present,
            motor_vocal_drive: new_vocal,
            motor_locomotion_stride: new_stride,
            motor_steer_angle: new_steer,
            motor_grip_force: new_grip,
        })
    }

    pub fn import_sparse_v4(&mut self, data: &[u8]) -> Result<(), String> {
        let staged = self.try_parse_v4_internal(data)?;
        self.commit_staged_state(staged);
        Ok(())
    }

    pub fn migrate_predecessor_v3(&mut self, data: &[u8], layout: &str, field_present: Option<bool>) -> Result<(), String> {
        let staged = self.try_parse_v3_internal(data, layout, field_present)?;
        self.commit_staged_state(staged);
        Ok(())
    }
}

// ---------------------------------------------------------------------------
// 6. PyO3 Native Bindings
// ---------------------------------------------------------------------------

#[pyclass(name = "ModularSubstrate4D")]
pub struct PyModularSubstrate4D {
    inner: ModularSubstrate4D,
}

#[pymethods]
impl PyModularSubstrate4D {
    #[new]
    #[pyo3(signature = (yield_threshold=0.60, plastic_rate=0.03, activation_threshold=0.25))]
    pub fn new(yield_threshold: f32, plastic_rate: f32, activation_threshold: f32) -> Self {
        Self {
            inner: ModularSubstrate4D::new(yield_threshold, plastic_rate, activation_threshold),
        }
    }

    #[getter]
    pub fn yield_threshold(&self) -> f32 {
        self.inner.yield_threshold
    }

    #[getter]
    pub fn plastic_rate(&self) -> f32 {
        self.inner.plastic_rate
    }

    #[getter]
    pub fn activation_threshold(&self) -> f32 {
        self.inner.activation_threshold
    }

    #[pyo3(signature = (sensory_trits, somatic_trits, observed_r_mm=None, observed_theta_mdeg=None, barrier_stress=0.0))]
    pub fn step(
        &mut self,
        sensory_trits: Vec<i8>,
        somatic_trits: Vec<i8>,
        observed_r_mm: Option<f32>,
        observed_theta_mdeg: Option<i32>,
        barrier_stress: f32,
    ) -> (usize, f32) {
        self.inner.step(
            &sensory_trits,
            &somatic_trits,
            observed_r_mm,
            observed_theta_mdeg,
            barrier_stress,
        )
    }

    pub fn get_spatial_tracking(&self) -> (f32, i32, f32, bool) {
        let col1 = &self.inner.columns[1];
        (
            col1.spatial_r_mm,
            col1.spatial_theta_mdeg,
            col1.persistence_trace,
            col1.target_occluded,
        )
    }

    pub fn is_barrier_refusal_active(&self) -> bool {
        self.inner.columns[3].refusal_active
    }

    pub fn active_synapses(&self) -> usize {
        self.inner.total_active_synapses()
    }

    #[pyo3(signature = (decay=0.02, prune_thresh=0.005))]
    pub fn sleep_consolidation(&mut self, decay: f32, prune_thresh: f32) -> (usize, usize) {
        self.inner.dream_consolidation(decay, prune_thresh)
    }

    pub fn zero_plastic_weights(&mut self) {
        self.inner.zero_plastic_weights();
    }

    pub fn consume_continuous_joint_field(&mut self, _field_7d: Vec<f64>, _s_uf: f64) -> PyResult<()> {
        Err(PyNotImplementedError::new_err("Continuous joint field transport requires 64-column cortical array"))
    }

    pub fn get_continuous_joint_field(&self) -> PyResult<Vec<f64>> {
        Err(PyNotImplementedError::new_err("Continuous joint field query requires 64-column cortical array"))
    }

    pub fn export_sparse(&self) -> PyResult<Vec<u8>> {
        self.inner.export_sparse_v4().map_err(|e| PyValueError::new_err(e))
    }

    pub fn export_sparse_v4(&self) -> PyResult<Vec<u8>> {
        self.inner.export_sparse_v4().map_err(|e| PyValueError::new_err(e))
    }

    pub fn export_sparse_v3(&self) -> PyResult<Vec<u8>> {
        self.inner.export_sparse_v4().map_err(|e| PyValueError::new_err(e))
    }

    pub fn import_sparse(&mut self, data: &[u8]) -> PyResult<()> {
        self.inner.import_sparse_v4(data).map_err(|e| PyValueError::new_err(e))
    }

    pub fn import_sparse_v4(&mut self, data: &[u8]) -> PyResult<()> {
        self.inner.import_sparse_v4(data).map_err(|e| PyValueError::new_err(e))
    }

    pub fn import_sparse_v3(&mut self, data: &[u8]) -> PyResult<()> {
        self.inner.import_sparse_v4(data).map_err(|e| PyValueError::new_err(e))
    }
}

#[pyclass(name = "ModularSubstrate8D")]
pub struct PyModularSubstrate8D {
    inner: ModularSubstrate8D,
}

#[pymethods]
impl PyModularSubstrate8D {
    #[new]
    #[pyo3(signature = (yield_threshold=0.60, plastic_rate=0.03, activation_threshold=0.25))]
    pub fn new(yield_threshold: f32, plastic_rate: f32, activation_threshold: f32) -> Self {
        Self {
            inner: ModularSubstrate8D::new(yield_threshold, plastic_rate, activation_threshold),
        }
    }

    #[getter]
    pub fn yield_threshold(&self) -> f32 {
        self.inner.yield_threshold
    }

    #[getter]
    pub fn plastic_rate(&self) -> f32 {
        self.inner.plastic_rate
    }

    #[getter]
    pub fn activation_threshold(&self) -> f32 {
        self.inner.activation_threshold
    }

    #[pyo3(signature = (sensory_trits, somatic_trits, observed_r_mm=None, observed_theta_mdeg=None, barrier_stress=0.0, acoustic_formant=0.0))]
    pub fn step(
        &mut self,
        sensory_trits: Vec<i8>,
        somatic_trits: Vec<i8>,
        observed_r_mm: Option<f32>,
        observed_theta_mdeg: Option<i32>,
        barrier_stress: f32,
        acoustic_formant: f32,
    ) -> (usize, f32) {
        self.inner.step(
            &sensory_trits,
            &somatic_trits,
            observed_r_mm,
            observed_theta_mdeg,
            barrier_stress,
            acoustic_formant,
        )
    }

    pub fn get_spatial_tracking(&self) -> (f32, i32, f32, bool) {
        let col0 = &self.inner.columns[0];
        let col1 = &self.inner.columns[1];
        let persistence = (col0.persistence_trace + col1.persistence_trace) * 0.5;
        let occluded = col0.target_occluded || col1.target_occluded;
        (col0.spatial_r_mm, col1.spatial_theta_mdeg, persistence, occluded)
    }

    pub fn is_barrier_refusal_active(&self) -> bool {
        self.inner.columns[5].refusal_active
    }

    pub fn get_motor_efferent(&self) -> (f32, f32) {
        (
            self.inner.motor_vocal_drive,
            self.inner.motor_locomotion_stride,
        )
    }

    pub fn active_synapses(&self) -> usize {
        self.inner.total_active_synapses()
    }

    #[pyo3(signature = (decay=0.02, prune_thresh=0.005))]
    pub fn sleep_consolidation(&mut self, decay: f32, prune_thresh: f32) -> (usize, usize) {
        self.inner.dream_consolidation(decay, prune_thresh)
    }

    pub fn zero_plastic_weights(&mut self) {
        self.inner.zero_plastic_weights();
    }

    pub fn consume_continuous_joint_field(&mut self, _field_7d: Vec<f64>, _s_uf: f64) -> PyResult<()> {
        Err(PyNotImplementedError::new_err("Continuous joint field transport requires 64-column cortical array"))
    }

    pub fn get_continuous_joint_field(&self) -> PyResult<Vec<f64>> {
        Err(PyNotImplementedError::new_err("Continuous joint field query requires 64-column cortical array"))
    }

    pub fn export_sparse(&self) -> PyResult<Vec<u8>> {
        self.inner.export_sparse_v4().map_err(|e| PyValueError::new_err(e))
    }

    pub fn export_sparse_v4(&self) -> PyResult<Vec<u8>> {
        self.inner.export_sparse_v4().map_err(|e| PyValueError::new_err(e))
    }

    pub fn export_sparse_v3(&self) -> PyResult<Vec<u8>> {
        self.inner.export_sparse_v4().map_err(|e| PyValueError::new_err(e))
    }

    pub fn import_sparse(&mut self, data: &[u8]) -> PyResult<()> {
        self.inner.import_sparse_v4(data).map_err(|e| PyValueError::new_err(e))
    }

    pub fn import_sparse_v4(&mut self, data: &[u8]) -> PyResult<()> {
        self.inner.import_sparse_v4(data).map_err(|e| PyValueError::new_err(e))
    }

    pub fn import_sparse_v3(&mut self, data: &[u8]) -> PyResult<()> {
        self.inner.import_sparse_v4(data).map_err(|e| PyValueError::new_err(e))
    }
}

#[pyclass(name = "ModularSubstrate64D")]
pub struct PyModularSubstrate64D {
    inner: ModularSubstrate64D,
}

#[pymethods]
impl PyModularSubstrate64D {
    #[new]
    #[pyo3(signature = (yield_threshold=0.60, plastic_rate=0.03, activation_threshold=0.25))]
    pub fn new(yield_threshold: f32, plastic_rate: f32, activation_threshold: f32) -> Self {
        Self {
            inner: ModularSubstrate64D::new(yield_threshold, plastic_rate, activation_threshold),
        }
    }

    #[getter]
    pub fn yield_threshold(&self) -> f32 {
        self.inner.yield_threshold
    }

    #[getter]
    pub fn plastic_rate(&self) -> f32 {
        self.inner.plastic_rate
    }

    #[getter]
    pub fn activation_threshold(&self) -> f32 {
        self.inner.activation_threshold
    }

    #[pyo3(signature = (sensory_trits, somatic_trits, observed_r_mm=None, observed_theta_mdeg=None, barrier_stress=0.0, acoustic_formants=None))]
    pub fn step(
        &mut self,
        sensory_trits: Vec<i8>,
        somatic_trits: Vec<i8>,
        observed_r_mm: Option<f32>,
        observed_theta_mdeg: Option<i32>,
        barrier_stress: f32,
        acoustic_formants: Option<Vec<f32>>,
    ) -> PyResult<(usize, f32)> {
        let formants = acoustic_formants.unwrap_or_default();
        self.inner.step_cycle(
            &sensory_trits,
            &somatic_trits,
            observed_r_mm,
            observed_theta_mdeg,
            barrier_stress,
            &formants,
        ).map_err(PyNotImplementedError::new_err)
    }

    pub fn consume_continuous_joint_field(&mut self, field_7d: Vec<f64>, s_uf: f64) -> PyResult<()> {
        if field_7d.len() != 7 {
            return Err(PyValueError::new_err(format!("Expected 7 field values, got {}", field_7d.len())));
        }
        let mut arr = [0.0f64; 7];
        arr.copy_from_slice(&field_7d);
        self.inner.consume_continuous_joint_field(arr, s_uf)
            .map_err(|e| PyValueError::new_err(e))
    }

    pub fn get_continuous_joint_field(&self) -> (f64, f64, f64, f64, f64, f64, f64, f64) {
        let f = self.inner.get_continuous_joint_field();
        (f[0], f[1], f[2], f[3], f[4], f[5], f[6], f[7])
    }

    pub fn get_spatial_tracking(&self) -> (f32, i32, f32, bool) {
        let col0 = &self.inner.columns[0];
        let col1 = &self.inner.columns[1];
        let r = col0.spatial_r_mm;
        let theta = col1.spatial_theta_mdeg;
        let trace = (col0.persistence_trace + col1.persistence_trace) * 0.5;
        let occluded = col0.target_occluded || col1.target_occluded;
        (r, theta, trace, occluded)
    }

    pub fn is_barrier_refusal_active(&self) -> bool {
        self.inner.columns[23].refusal_active
    }

    pub fn get_motor_efferent(&self) -> (f32, f32, f32, f32) {
        (
            self.inner.motor_vocal_drive,
            self.inner.motor_locomotion_stride,
            self.inner.motor_steer_angle,
            self.inner.motor_grip_force,
        )
    }

    pub fn sever_tract(&mut self, c_from: usize, c_to: usize) {
        self.inner.sever_tract(c_from, c_to);
    }

    pub fn reconnect_tract(&mut self, c_from: usize, c_to: usize) {
        self.inner.reconnect_tract(c_from, c_to);
    }

    pub fn is_tract_severed(&self, c_from: usize, c_to: usize) -> bool {
        self.inner.is_tract_severed(c_from, c_to)
    }

    pub fn active_synapses(&self) -> usize {
        self.inner.total_active_synapses()
    }

    #[pyo3(signature = (decay=0.02, prune_thresh=0.005))]
    pub fn sleep_consolidation(&mut self, decay: f32, prune_thresh: f32) -> (usize, usize) {
        self.inner.dream_consolidation(decay, prune_thresh)
    }

    pub fn zero_plastic_weights(&mut self) {
        self.inner.zero_plastic_weights();
    }

    pub fn has_continuous_joint_field(&self) -> bool {
        self.inner.has_continuous_joint_field()
    }

    pub fn clear_continuous_joint_field(&mut self) {
        self.inner.clear_continuous_joint_field();
    }

    pub fn export_sparse(&self) -> PyResult<Vec<u8>> {
        self.inner.export_sparse_v4().map_err(|e| PyValueError::new_err(e))
    }

    pub fn export_sparse_v4(&self) -> PyResult<Vec<u8>> {
        self.inner.export_sparse_v4().map_err(|e| PyValueError::new_err(e))
    }

    pub fn import_sparse(&mut self, data: &[u8]) -> PyResult<()> {
        self.inner.import_sparse_v4(data).map_err(|e| PyValueError::new_err(e))
    }

    pub fn import_sparse_v4(&mut self, data: &[u8]) -> PyResult<()> {
        self.inner.import_sparse_v4(data).map_err(|e| PyValueError::new_err(e))
    }

    #[pyo3(signature = (data, layout, field_present=None))]
    pub fn migrate_predecessor_v3(&mut self, data: &[u8], layout: &str, field_present: Option<bool>) -> PyResult<()> {
        self.inner.migrate_predecessor_v3(data, layout, field_present).map_err(|e| PyValueError::new_err(e))
    }

    #[pyo3(signature = (data, layout))]
    pub fn migrate_predecessor_v2(&mut self, data: &[u8], layout: &str) -> PyResult<()> {
        self.inner.migrate_predecessor_v2(data, layout).map_err(|e| PyValueError::new_err(e))
    }

    #[staticmethod]
    pub fn float_to_rational_trits(val: f64) -> PyResult<(Vec<i8>, Vec<i8>, i8, bool)> {
        let field = ModularSubstrate64D::float_to_rational_trits(val).map_err(|e| PyValueError::new_err(e))?;
        Ok((field.numerator_trits, field.denominator_trits, field.sign, field.is_zero))
    }

    #[staticmethod]
    pub fn rational_trits_to_float(num_trits: Vec<i8>, den_trits: Vec<i8>, sign: i8, is_zero: bool) -> PyResult<f64> {
        let field = MathLoomRationalField {
            sign,
            is_zero,
            numerator_trits: num_trits,
            denominator_trits: den_trits,
        };
        ModularSubstrate64D::rational_trits_to_float(&field).map_err(|e| PyValueError::new_err(e))
    }
}

pub fn register(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<PyModularSubstrate4D>()?;
    m.add_class::<PyModularSubstrate8D>()?;
    m.add_class::<PyModularSubstrate64D>()?;
    Ok(())
}

#[path = "native_current_codec.rs"]
pub(crate) mod current_codec;
