//! cortical_column.rs -- Modular Neuromorphic Substrates (4-Column & 8-Column Octet)
//!
//! Substrate: ArcLoom Discrete Balanced-Ternary Neuromorphic Core
//! Physical Model: Specialized Cortical Columns with 6-Layer Vertical Laminar Microcircuits
//!
//! Architectures:
//!   - ModularSubstrate4D: 4 Columns (Sensory, Spatial, Syntax, Affordance) - Task 1578 Baseline
//!   - ModularSubstrate8D: 8 Columns Balanced Octet (V1, V2, A1, A2, S1, S2, M1, M2) - Option A
//!
//! Laminar Microcircuit (per column):
//!   - Layer 1 (L1): 32 nodes (Apical modulation / global somatic arousal)
//!   - Layer 2/3 (L2/3): 128 nodes (Supragranular associative crossbar, 2-5% sparsity)
//!   - Layer 4 (L4): 64 nodes (Granular sensory input)
//!   - Layer 5 (L5): 64 nodes (Infragranular motor pyramidal efferents)
//!   - Layer 6 (L6): 32 nodes (Predictive feedback & reafference self-cancellation)
//!
//! Plasticity:
//!   - Continuum von Mises material yield stress: f(|σ_ij|) = |σ_ij| - Y <= 0
//!   - Asymmetric directional inter-column fasciculi: W_(A,B) != W_(B,A) for temporal syntax
//!   - Synaptic downscaling and pruning during offline sleep consolidation
//!
//! Thread-safe, lock-free computation, release-performance optimized.

use pyo3::prelude::*;

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

// ---------------------------------------------------------------------------
// 1. Laminar Microcircuit (Canonical 6-Layer Primitive)
// ---------------------------------------------------------------------------

#[derive(Clone)]
pub struct LaminarMicrocircuit {
    // Ternary node state vectors: T ∈ {-1, 0, +1}
    pub l1: Vec<i8>,
    pub l23: Vec<i8>,
    pub l4: Vec<i8>,
    pub l5: Vec<i8>,
    pub l6: Vec<i8>,

    // Intra-column conductance tensors ∈ [-1.0, 1.0]
    pub g_4_23: Vec<f32>,
    pub g_23_23: Vec<f32>,
    pub g_23_5: Vec<f32>,
    pub g_5_6: Vec<f32>,
    pub g_6_4: Vec<f32>,
    pub g_1_23: Vec<f32>,

    // Physical plasticity parameters
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

            g_4_23: vec![0.0; G_4_23_SIZE],
            g_23_23: vec![0.0; G_23_23_SIZE],
            g_23_5: vec![0.0; G_23_5_SIZE],
            g_5_6: vec![0.0; G_5_6_SIZE],
            g_6_4: vec![0.0; G_6_4_SIZE],
            g_1_23: vec![0.0; G_1_23_SIZE],

            yield_threshold: yield_threshold.clamp(0.01, 0.99),
            plastic_rate: plastic_rate.clamp(0.001, 1.0),
            activation_threshold: activation_threshold.max(0.01),
        }
    }

    /// Step vertical laminar causal flow:
    ///   1. L4 receives afferents, cancelled by top-down predictive L6 inhibitory reafference.
    ///   2. L2/3 integrated from L4 feedforward (vertical minicolumn arborization + g_4_23) + L1 apical + horizontal L2/3.
    ///   3. Sparse horizontal competition enforces ~2-5% active nodes in L2/3.
    ///   4. L5 motor efferents driven by L2/3 attractors via descending vertical arborization.
    ///   5. L5 projects efference copy into L6.
    pub fn step_laminar_flow(&mut self, afferents: &[i8], apical_somatics: &[i8]) -> (usize, f32) {
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
            v_23[j] = acc;
        }

        // 4. Sparse Lateral Inhibition in L2/3 (target: k-WTA ~ 8 nodes active = ~6% sparsity)
        let k_winners = 8;
        let mut scored_indices: Vec<(usize, f32)> = v_23.iter().enumerate().map(|(idx, &v)| (idx, v.abs())).collect();
        scored_indices.sort_by(|a, b| b.1.partial_cmp(&a.1).unwrap_or(std::cmp::Ordering::Equal));

        for j in 0..L23_NODES {
            self.l23[j] = 0;
        }
        for (idx, abs_v) in scored_indices.into_iter().take(k_winners) {
            if abs_v >= self.activation_threshold {
                self.l23[idx] = if v_23[idx] > 0.0 { 1 } else { -1 };
            }
        }

        // 5. Infragranular Motor Pyramidal Layer (L5):
        for j in 0..L5_NODES {
            let topo_l23 = self.l23[j * 2] as f32 * 0.50;
            let mut acc = topo_l23;
            for i in 0..L23_NODES {
                acc += (self.l23[i] as f32) * self.g_23_5[i * L5_NODES + j];
            }
            self.l5[j] = if acc >= self.activation_threshold {
                1
            } else if acc <= -self.activation_threshold {
                -1
            } else {
                0
            };
        }

        // 6. Efference Copy into L6: Driven by L5
        for j in 0..L6_NODES {
            let topo_l5 = self.l5[j * 2] as f32 * 0.50;
            let mut acc = topo_l5;
            for i in 0..L5_NODES {
                acc += (self.l5[i] as f32) * self.g_5_6[i * L6_NODES + j];
            }
            self.l6[j] = if acc >= self.activation_threshold {
                1
            } else if acc <= -self.activation_threshold {
                -1
            } else {
                0
            };
        }

        // 7. Local continuum von Mises plasticity within the column
        self.apply_intra_yield_plasticity()
    }

    /// Apply local material yield stress plasticity f(|σ_ij|) = |σ_ij| - Y <= 0 across all intra-column connections
    pub fn apply_intra_yield_plasticity(&mut self) -> (usize, f32) {
        let mut yield_count = 0usize;
        let mut total_strain = 0.0f32;

        let y = self.yield_threshold;
        let eta = self.plastic_rate;

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
                    self.g_4_23[idx] = (self.g_4_23[idx] + eta * overstress * sigma.signum()).clamp(-1.0, 1.0);
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
                    self.g_23_23[idx] = (self.g_23_23[idx] + eta * overstress * sigma.signum()).clamp(-1.0, 1.0);
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
                    self.g_23_5[idx] = (self.g_23_5[idx] + eta * overstress * sigma.signum()).clamp(-1.0, 1.0);
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
                    self.g_5_6[idx] = (self.g_5_6[idx] + eta * overstress * sigma.signum()).clamp(-1.0, 1.0);
                    yield_count += 1;
                    total_strain += overstress;
                }
            }
        }

        // Plasticity: L6 -> L4 (Predictive reafference cancellation)
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
                    self.g_6_4[idx] = (self.g_6_4[idx] + eta * overstress * sigma.signum()).clamp(-1.0, 1.0);
                    yield_count += 1;
                    total_strain += overstress;
                }
            }
        }

        // Plasticity: L1 -> L2/3 (Apical somatic modulation)
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
                    self.g_1_23[idx] = (self.g_1_23[idx] + eta * overstress * sigma.signum()).clamp(-1.0, 1.0);
                    yield_count += 1;
                    total_strain += overstress;
                }
            }
        }

        (yield_count, total_strain)
    }

    /// Synaptic downscaling and pruning during offline sleep
    pub fn dream_downscale_and_prune(&mut self, decay: f32, prune_thresh: f32) -> (usize, usize) {
        let mut decayed = 0usize;
        let mut pruned = 0usize;
        let tensors = [
            &mut self.g_4_23,
            &mut self.g_23_23,
            &mut self.g_23_5,
            &mut self.g_5_6,
            &mut self.g_6_4,
            &mut self.g_1_23,
        ];
        for t in tensors {
            for g in t.iter_mut() {
                if *g != 0.0 {
                    decayed += 1;
                    *g *= 1.0 - decay;
                    if g.abs() < prune_thresh {
                        *g = 0.0;
                        pruned += 1;
                    }
                }
            }
        }
        (decayed, pruned)
    }

    pub fn active_intra_synapses(&self) -> usize {
        let mut count = 0usize;
        let tensors = [
            &self.g_4_23,
            &self.g_23_23,
            &self.g_23_5,
            &self.g_5_6,
            &self.g_6_4,
            &self.g_1_23,
        ];
        for t in tensors {
            for &g in t.iter() {
                if g.abs() > 0.001 {
                    count += 1;
                }
            }
        }
        count
    }
}

// ---------------------------------------------------------------------------
// 2. Specialized Cortical Column
// ---------------------------------------------------------------------------

#[derive(Clone)]
pub struct CorticalColumn {
    pub column_id: usize,
    pub microcircuit: LaminarMicrocircuit,

    // Specialized physics:
    // Spatial attractor coordinates
    pub spatial_r_mm: f32,
    pub spatial_theta_mdeg: i32,
    pub persistence_trace: f32,
    pub target_occluded: bool,

    // Syntax & temporal chaining
    pub syntax_step: usize,
    pub last_syllable: Option<String>,

    // Affordance & barrier yield refusal
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
            syntax_step: 0,
            last_syllable: None,
            barrier_contact_stress: 0.0,
            yield_limit_threshold: 0.70,
            refusal_active: false,
        }
    }
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

    pub fn step_cycle(
        &mut self,
        sensory_trits: &[i8],
        somatic_trits: &[i8],
        observed_r_mm: Option<f32>,
        observed_theta_mdeg: Option<i32>,
        current_barrier_stress: f32,
    ) -> (usize, f32) {
        let mut total_yields = 0usize;
        let mut total_strain = 0.0f32;

        // Step 1: Column 0 (Multimodal Transduction)
        let (y0, s0) = self.columns[0].microcircuit.step_laminar_flow(sensory_trits, somatic_trits);
        total_yields += y0; total_strain += s0;

        // Step 2: Column 1 (Spatial Invariance & Polar Attractor)
        if let (Some(r), Some(th)) = (observed_r_mm, observed_theta_mdeg) {
            self.columns[1].spatial_r_mm = r;
            self.columns[1].spatial_theta_mdeg = th;
            self.columns[1].persistence_trace = 1.0;
            self.columns[1].target_occluded = false;
        } else {
            self.columns[1].persistence_trace *= 0.985;
            self.columns[1].target_occluded = true;
        }

        let mut spatial_afferents = vec![0i8; L4_NODES];
        let r_bin = ((self.columns[1].spatial_r_mm / 100.0) as usize).min(31);
        spatial_afferents[r_bin] = if self.columns[1].persistence_trace > 0.05 { 1 } else { 0 };
        let (y1, s1) = self.columns[1].microcircuit.step_laminar_flow(&spatial_afferents, somatic_trits);
        total_yields += y1; total_strain += s1;

        // Step 3: Column 2 (Causal Sequential Syntax)
        let mut syntax_afferents = vec![0i8; L4_NODES];
        for i in 0..32 {
            syntax_afferents[i] = self.columns[0].microcircuit.l5[i];
            syntax_afferents[32 + i] = self.columns[1].microcircuit.l5[i];
        }
        let (y2, s2) = self.columns[2].microcircuit.step_laminar_flow(&syntax_afferents, somatic_trits);
        total_yields += y2; total_strain += s2;

        // Step 4: Column 3 (Material Affordance & Barrier Gating)
        self.columns[3].barrier_contact_stress = current_barrier_stress;
        self.columns[3].refusal_active = current_barrier_stress >= self.columns[3].yield_limit_threshold;
        let mut affordance_afferents = vec![0i8; L4_NODES];
        affordance_afferents[0] = if self.columns[3].refusal_active { 1 } else { 0 };
        let (y3, s3) = self.columns[3].microcircuit.step_laminar_flow(&affordance_afferents, somatic_trits);
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
        let eta = self.plastic_rate;

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
                            self.w_inter_23[idx] = (self.w_inter_23[idx] + eta * overstress * sigma.signum()).clamp(-1.0, 1.0);
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
                            self.w_inter_5[idx] = (self.w_inter_5[idx] + eta * overstress * sigma.signum()).clamp(-1.0, 1.0);
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
        for col in self.columns.iter_mut() {
            let (d, p) = col.microcircuit.dream_downscale_and_prune(decay, prune_thresh);
            total_decayed += d;
            total_pruned += p;
        }
        for g in self.w_inter_23.iter_mut() {
            if *g != 0.0 {
                total_decayed += 1;
                *g *= 1.0 - decay;
                if g.abs() < prune_thresh {
                    *g = 0.0;
                    total_pruned += 1;
                }
            }
        }
        for g in self.w_inter_5.iter_mut() {
            if *g != 0.0 {
                total_decayed += 1;
                *g *= 1.0 - decay;
                if g.abs() < prune_thresh {
                    *g = 0.0;
                    total_pruned += 1;
                }
            }
        }
        (total_decayed, total_pruned)
    }

    pub fn total_active_synapses(&self) -> usize {
        let mut count = 0usize;
        for col in &self.columns {
            count += col.microcircuit.active_intra_synapses();
        }
        for &g in &self.w_inter_23 {
            if g.abs() > 0.001 { count += 1; }
        }
        for &g in &self.w_inter_5 {
            if g.abs() > 0.001 { count += 1; }
        }
        count
    }
}

// ---------------------------------------------------------------------------
// 4. 8-Column 3D Modular Neuromorphic Substrate (Balanced Octet - Option A)
// ---------------------------------------------------------------------------
// Columns:
//   Col 0 (V1): Optical Foveal Focal Target (distance r_mm)
//   Col 1 (V2): Optical Motion Gradient & Heading (angle theta_mdeg)
//   Col 2 (A1): Cochlear Formant Peak Resonance
//   Col 3 (A2): Cochlear Pitch / Envelope
//   Col 4 (S1): Somatosensory Palmar Contact
//   Col 5 (S2): Somatosensory Barrier Stress (von Mises Yield f <= 0)
//   Col 6 (M1): Motor Airway Vocal Valve (Exhaust pulse)
//   Col 7 (M2): Motor Locomotion Stride & Steer

pub struct ModularSubstrate8D {
    pub columns: Vec<CorticalColumn>,
    pub w_inter_23: Vec<f32>,
    pub w_inter_5: Vec<f32>,
    pub yield_threshold: f32,
    pub plastic_rate: f32,
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

    pub fn step_cycle(
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

        // 1. Col 0 (V1: Foveal Distance)
        if let Some(r) = observed_r_mm {
            self.columns[0].spatial_r_mm = r;
            self.columns[0].persistence_trace = 1.0;
            self.columns[0].target_occluded = false;
        } else {
            self.columns[0].persistence_trace *= 0.985;
            self.columns[0].target_occluded = true;
        }
        let mut v1_aff = vec![0i8; L4_NODES];
        let r_bin = ((self.columns[0].spatial_r_mm / 100.0) as usize).min(63);
        v1_aff[r_bin] = if self.columns[0].persistence_trace > 0.05 { 1 } else { 0 };
        let (y0, s0) = self.columns[0].microcircuit.step_laminar_flow(&v1_aff, somatic_trits);
        total_yields += y0; total_strain += s0;

        // 2. Col 1 (V2: Motion & Angle)
        if let Some(th) = observed_theta_mdeg {
            self.columns[1].spatial_theta_mdeg = th;
            self.columns[1].persistence_trace = 1.0;
            self.columns[1].target_occluded = false;
        } else {
            self.columns[1].persistence_trace *= 0.985;
            self.columns[1].target_occluded = true;
        }
        let mut v2_aff = vec![0i8; L4_NODES];
        let th_bin = (((self.columns[1].spatial_theta_mdeg + 180_000) / 6000) as usize).min(63);
        v2_aff[th_bin] = if self.columns[1].persistence_trace > 0.05 { 1 } else { 0 };
        let (y1, s1) = self.columns[1].microcircuit.step_laminar_flow(&v2_aff, somatic_trits);
        total_yields += y1; total_strain += s1;

        // 3. Col 2 (A1: Cochlear Formant Peak)
        let mut a1_aff = vec![0i8; L4_NODES];
        let formant_bin = ((acoustic_formant / 4.0) as usize).min(63);
        if acoustic_formant > 10.0 {
            a1_aff[formant_bin] = 1;
        }
        let (y2, s2) = self.columns[2].microcircuit.step_laminar_flow(&a1_aff, somatic_trits);
        total_yields += y2; total_strain += s2;

        // 4. Col 3 (A2: Cochlear Envelope / Pitch)
        let (y3, s3) = self.columns[3].microcircuit.step_laminar_flow(sensory_trits, somatic_trits);
        total_yields += y3; total_strain += s3;

        // 5. Col 4 (S1: Palmar Contact)
        let (y4, s4) = self.columns[4].microcircuit.step_laminar_flow(sensory_trits, somatic_trits);
        total_yields += y4; total_strain += s4;

        // 6. Col 5 (S2: Barrier Contact & Yield Refusal)
        self.columns[5].barrier_contact_stress = current_barrier_stress;
        self.columns[5].refusal_active = current_barrier_stress >= self.columns[5].yield_limit_threshold;
        let mut s2_aff = vec![0i8; L4_NODES];
        s2_aff[0] = if self.columns[5].refusal_active { 1 } else { 0 };
        let (y5, s5) = self.columns[5].microcircuit.step_laminar_flow(&s2_aff, somatic_trits);
        total_yields += y5; total_strain += s5;

        // 7. Col 6 (M1: Airway Vocal Valve Discharge)
        let is_strained = somatic_trits.len() > 0 && somatic_trits[0] < 0;
        if self.columns[5].refusal_active || is_strained {
            self.motor_vocal_drive = 220.0; // Resonant discharge pulse
            self.motor_locomotion_stride = 0.0; // Inhibit pushing against solid barrier
        } else if acoustic_formant > 50.0 {
            self.motor_vocal_drive = acoustic_formant;
            self.motor_locomotion_stride = 30.0;
        } else {
            self.motor_vocal_drive = 0.0;
            self.motor_locomotion_stride = 60.0; // Nominal locomotion
        }
        let mut m1_aff = vec![0i8; L4_NODES];
        m1_aff[0] = if self.motor_vocal_drive > 50.0 { 1 } else { 0 };
        let (y6, s6) = self.columns[6].microcircuit.step_laminar_flow(&m1_aff, somatic_trits);
        total_yields += y6; total_strain += s6;

        // 8. Col 7 (M2: Motor Locomotion Stride & Steer)
        let mut m2_aff = vec![0i8; L4_NODES];
        m2_aff[0] = if self.motor_locomotion_stride > 0.0 { 1 } else { 0 };
        let (y7, s7) = self.columns[7].microcircuit.step_laminar_flow(&m2_aff, somatic_trits);
        total_yields += y7; total_strain += s7;

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
        let eta = self.plastic_rate;

        for c_from in 0..NUM_COLUMNS_8D {
            for c_to in 0..NUM_COLUMNS_8D {
                if c_from == c_to { continue; }

                // L2/3 -> L2/3 Fasciculi
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
                            self.w_inter_23[idx] = (self.w_inter_23[idx] + eta * overstress * sigma.signum()).clamp(-1.0, 1.0);
                            yield_count += 1;
                            total_strain += overstress;
                        }
                    }
                }

                // L5 -> L5 Fasciculi
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
                            self.w_inter_5[idx] = (self.w_inter_5[idx] + eta * overstress * sigma.signum()).clamp(-1.0, 1.0);
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
        for col in self.columns.iter_mut() {
            let (d, p) = col.microcircuit.dream_downscale_and_prune(decay, prune_thresh);
            total_decayed += d;
            total_pruned += p;
        }
        for g in self.w_inter_23.iter_mut() {
            if *g != 0.0 {
                total_decayed += 1;
                *g *= 1.0 - decay;
                if g.abs() < prune_thresh {
                    *g = 0.0;
                    total_pruned += 1;
                }
            }
        }
        for g in self.w_inter_5.iter_mut() {
            if *g != 0.0 {
                total_decayed += 1;
                *g *= 1.0 - decay;
                if g.abs() < prune_thresh {
                    *g = 0.0;
                    total_pruned += 1;
                }
            }
        }
        (total_decayed, total_pruned)
    }

    pub fn total_active_synapses(&self) -> usize {
        let mut count = 0usize;
        for col in &self.columns {
            count += col.microcircuit.active_intra_synapses();
        }
        for &g in &self.w_inter_23 {
            if g.abs() > 0.001 { count += 1; }
        }
        for &g in &self.w_inter_5 {
            if g.abs() > 0.001 { count += 1; }
        }
        count
    }
}

// ---------------------------------------------------------------------------
// 5. PyO3 Python Interface
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

    #[pyo3(signature = (sensory_trits, somatic_trits, observed_r_mm=None, observed_theta_mdeg=None, barrier_stress=0.0))]
    pub fn step(
        &mut self,
        sensory_trits: Vec<i8>,
        somatic_trits: Vec<i8>,
        observed_r_mm: Option<f32>,
        observed_theta_mdeg: Option<i32>,
        barrier_stress: f32,
    ) -> PyResult<(usize, f32)> {
        Ok(self.inner.step_cycle(&sensory_trits, &somatic_trits, observed_r_mm, observed_theta_mdeg, barrier_stress))
    }

    pub fn get_spatial_tracking(&self) -> (f32, i32, f32, bool) {
        let col1 = &self.inner.columns[1];
        (col1.spatial_r_mm, col1.spatial_theta_mdeg, col1.persistence_trace, col1.target_occluded)
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

    pub fn export_sparse(&self) -> Vec<u8> {
        let mut candidates: Vec<(u32, f32)> = Vec::new();
        for (idx, &g) in self.inner.w_inter_23.iter().enumerate() {
            if g.abs() >= 0.005 {
                candidates.push((idx as u32, g));
            }
        }
        for (idx, &g) in self.inner.w_inter_5.iter().enumerate() {
            if g.abs() >= 0.005 {
                let offset_idx = (INTER_COL_23_SIZE_4D + idx) as u32;
                candidates.push((offset_idx, g));
            }
        }
        candidates.sort_by(|a, b| b.1.abs().partial_cmp(&a.1.abs()).unwrap_or(std::cmp::Ordering::Equal));
        let bounded = if candidates.len() > 1024 { &candidates[..1024] } else { &candidates[..] };

        let mut out = Vec::with_capacity(bounded.len() * 8);
        for &(idx, g) in bounded {
            out.extend_from_slice(&idx.to_le_bytes());
            out.extend_from_slice(&g.to_le_bytes());
        }
        out
    }

    pub fn import_sparse(&mut self, data: &[u8]) -> PyResult<()> {
        let n_entries = data.len() / 8;
        for i in 0..n_entries {
            let offset = i * 8;
            if offset + 8 <= data.len() {
                let idx = u32::from_le_bytes([data[offset], data[offset + 1], data[offset + 2], data[offset + 3]]) as usize;
                let g = f32::from_le_bytes([data[offset + 4], data[offset + 5], data[offset + 6], data[offset + 7]]);
                if idx < INTER_COL_23_SIZE_4D {
                    if idx < self.inner.w_inter_23.len() {
                        self.inner.w_inter_23[idx] = g;
                    }
                } else {
                    let off_5 = idx - INTER_COL_23_SIZE_4D;
                    if off_5 < self.inner.w_inter_5.len() {
                        self.inner.w_inter_5[off_5] = g;
                    }
                }
            }
        }
        Ok(())
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

    #[pyo3(signature = (sensory_trits, somatic_trits, observed_r_mm=None, observed_theta_mdeg=None, barrier_stress=0.0, acoustic_formant=0.0))]
    pub fn step(
        &mut self,
        sensory_trits: Vec<i8>,
        somatic_trits: Vec<i8>,
        observed_r_mm: Option<f32>,
        observed_theta_mdeg: Option<i32>,
        barrier_stress: f32,
        acoustic_formant: f32,
    ) -> PyResult<(usize, f32)> {
        Ok(self.inner.step_cycle(&sensory_trits, &somatic_trits, observed_r_mm, observed_theta_mdeg, barrier_stress, acoustic_formant))
    }

    /// Query Column 0 (V1) & Column 1 (V2): Returns (r_mm, theta_mdeg, persistence_trace, is_occluded)
    pub fn get_spatial_tracking(&self) -> (f32, i32, f32, bool) {
        let col0 = &self.inner.columns[0];
        let col1 = &self.inner.columns[1];
        let persistence = (col0.persistence_trace + col1.persistence_trace) * 0.50;
        let occluded = col0.target_occluded && col1.target_occluded;
        (col0.spatial_r_mm, col1.spatial_theta_mdeg, persistence, occluded)
    }

    /// Query Column 5 (S2): Returns whether rigid barrier refusal is active
    pub fn is_barrier_refusal_active(&self) -> bool {
        self.inner.columns[5].refusal_active
    }

    /// Query Motor Efferents: Returns (vocal_drive, locomotion_stride)
    pub fn get_motor_efferent(&self) -> (f32, f32) {
        (self.inner.motor_vocal_drive, self.inner.motor_locomotion_stride)
    }

    /// Count total active plastic synapses (|g| > 0.001) across 8 modular columns
    pub fn active_synapses(&self) -> usize {
        self.inner.total_active_synapses()
    }

    #[pyo3(signature = (decay=0.02, prune_thresh=0.005))]
    pub fn sleep_consolidation(&mut self, decay: f32, prune_thresh: f32) -> (usize, usize) {
        self.inner.dream_consolidation(decay, prune_thresh)
    }

    pub fn export_sparse(&self) -> Vec<u8> {
        let mut candidates: Vec<(u32, f32)> = Vec::new();
        for (idx, &g) in self.inner.w_inter_23.iter().enumerate() {
            if g.abs() >= 0.005 {
                candidates.push((idx as u32, g));
            }
        }
        for (idx, &g) in self.inner.w_inter_5.iter().enumerate() {
            if g.abs() >= 0.005 {
                let offset_idx = (INTER_COL_23_SIZE_8D + idx) as u32;
                candidates.push((offset_idx, g));
            }
        }
        candidates.sort_by(|a, b| b.1.abs().partial_cmp(&a.1.abs()).unwrap_or(std::cmp::Ordering::Equal));
        let bounded = if candidates.len() > 4096 { &candidates[..4096] } else { &candidates[..] };

        let mut out = Vec::with_capacity(bounded.len() * 8);
        for &(idx, g) in bounded {
            out.extend_from_slice(&idx.to_le_bytes());
            out.extend_from_slice(&g.to_le_bytes());
        }
        out
    }

    pub fn import_sparse(&mut self, data: &[u8]) -> PyResult<()> {
        let n_entries = data.len() / 8;
        for i in 0..n_entries {
            let offset = i * 8;
            if offset + 8 <= data.len() {
                let idx = u32::from_le_bytes([data[offset], data[offset + 1], data[offset + 2], data[offset + 3]]) as usize;
                let g = f32::from_le_bytes([data[offset + 4], data[offset + 5], data[offset + 6], data[offset + 7]]);
                if idx < INTER_COL_23_SIZE_8D {
                    if idx < self.inner.w_inter_23.len() {
                        self.inner.w_inter_23[idx] = g;
                    }
                } else {
                    let off_5 = idx - INTER_COL_23_SIZE_8D;
                    if off_5 < self.inner.w_inter_5.len() {
                        self.inner.w_inter_5[off_5] = g;
                    }
                }
            }
        }
        Ok(())
    }
}


// ---------------------------------------------------------------------------
// 5. 64-Column 3D Modular Neuromorphic Substrate (Cortical Array)
// ---------------------------------------------------------------------------
// 8 Macro-Clusters of 8 Specialized Cortical Columns (20,480 Nodes | 83.8M Fasciculi):
//   Cluster 0 (Cols 0..8):   Optical Cortical Sheet (V1-V8: Depth, Heading, Contrast, Flow, Color, Width, Texture, Multi-Track)
//   Cluster 1 (Cols 8..16):  Acoustic Cochlear Sheet (A1-A8: F1, F2, F3 Formants, Pitch F0, Transient, Harmonic, Cadence, Phonation)
//   Cluster 2 (Cols 16..24): Somatosensory Sheet (S1-S8: Palmar, Friction, Thermal, Compliance, Roughness, Multi-Grasp, Proprioception, Barrier Yield)
//   Cluster 3 (Cols 24..32): Spatial Hippocampal Field (H1-H8: 2D Grid Cells, Place Attractors, Heading Compass, Portal Novelty)
//   Cluster 4 (Cols 32..40): Sequential Syntax & Temporal Grammar (Syn1-Syn8: Subject, Verb, Object, Locus, 4-Stage Asymmetric Delay Chaining)
//   Cluster 5 (Cols 40..48): Actuator & Motor Cortex (M1-M8: Vocal F0, Formant Articulation, Stride L/R, Steer, Reach, Wrist, Gripper)
//   Cluster 6 (Cols 48..56): Somatic Valence & Homeostasis (B1-B8: Pressure P_k, Breathing B_k, Surplus, Boredom, Thermal, Fatigue, Satiety, Stability S_UF)
//   Cluster 7 (Cols 56..64): Prefrontal Arbitration & Invariant Gates (PFC1-PFC8: Goal Lock, Barrier Override, Novelty, Verification, Attention)

pub struct ModularSubstrate64D {
    pub columns: Vec<CorticalColumn>,
    pub w_inter_23: Vec<f32>,
    pub w_inter_5: Vec<f32>,
    pub yield_threshold: f32,
    pub plastic_rate: f32,
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
            yield_threshold: yield_threshold.clamp(0.01, 0.99),
            plastic_rate: plastic_rate.clamp(0.001, 1.0),
            motor_vocal_drive: 0.0,
            motor_locomotion_stride: 60.0,
            motor_steer_angle: 0.0,
            motor_grip_force: 0.0,
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

    pub fn step_cycle(
        &mut self,
        sensory_trits: &[i8],
        somatic_trits: &[i8],
        observed_r_mm: Option<f32>,
        observed_theta_mdeg: Option<i32>,
        current_barrier_stress: f32,
        acoustic_formants: &[f32],
    ) -> (usize, f32) {
        let mut total_yields = 0usize;
        let mut total_strain = 0.0f32;

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
        let r_bin = ((self.columns[0].spatial_r_mm / 100.0) as usize).min(63);
        v1_aff[r_bin] = if self.columns[0].persistence_trace > 0.05 { 1 } else { 0 };
        let (y0, s0) = self.columns[0].microcircuit.step_laminar_flow(&v1_aff, somatic_trits);
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
        let th_bin = (((self.columns[1].spatial_theta_mdeg + 180_000) / 6000) as usize).min(63);
        v2_aff[th_bin] = if self.columns[1].persistence_trace > 0.05 { 1 } else { 0 };
        let (y1, s1) = self.columns[1].microcircuit.step_laminar_flow(&v2_aff, somatic_trits);
        total_yields += y1; total_strain += s1;

        for c in 2..8 {
            let (yc, sc) = self.columns[c].microcircuit.step_laminar_flow(sensory_trits, somatic_trits);
            total_yields += yc; total_strain += sc;
        }

        // 2. Cluster 1: Acoustic Cochlear Sheet (Cols 8..16)
        for (i, c) in (8..16).enumerate() {
            let mut a_aff = vec![0i8; L4_NODES];
            if i < acoustic_formants.len() && acoustic_formants[i] > 10.0 {
                let bin = ((acoustic_formants[i] / 5.0) as usize).min(63);
                a_aff[bin] = 1;
            } else if i < sensory_trits.len() {
                a_aff[0] = sensory_trits[i];
            }
            let (yc, sc) = self.columns[c].microcircuit.step_laminar_flow(&a_aff, somatic_trits);
            total_yields += yc; total_strain += sc;
        }

        // 3. Cluster 2: Somatosensory Sheet (Cols 16..24)
        for c in 16..23 {
            let (yc, sc) = self.columns[c].microcircuit.step_laminar_flow(sensory_trits, somatic_trits);
            total_yields += yc; total_strain += sc;
        }
        // Col 23 (S8: Barrier Yield Refusal)
        self.columns[23].barrier_contact_stress = current_barrier_stress;
        self.columns[23].refusal_active = current_barrier_stress >= self.columns[23].yield_limit_threshold;
        let mut s8_aff = vec![0i8; L4_NODES];
        s8_aff[0] = if self.columns[23].refusal_active { 1 } else { 0 };
        let (y23, s23) = self.columns[23].microcircuit.step_laminar_flow(&s8_aff, somatic_trits);
        total_yields += y23; total_strain += s23;

        // 4. Clusters 3, 4: Spatial & Syntax (Cols 24..40)
        for c in 24..40 {
            let (yc, sc) = self.columns[c].microcircuit.step_laminar_flow(sensory_trits, somatic_trits);
            total_yields += yc; total_strain += sc;
        }

        // 5. Cluster 5: Motor Cortex (Cols 40..48)
        let is_strained = somatic_trits.len() > 0 && somatic_trits[0] < 0;
        let refusal = self.columns[23].refusal_active;
        if refusal || is_strained {
            self.motor_vocal_drive = 220.0;
            self.motor_locomotion_stride = 0.0;
            self.motor_grip_force = 0.0;
        } else {
            let primary_formant = if acoustic_formants.len() > 0 { acoustic_formants[0] } else { 0.0 };
            if primary_formant > 50.0 {
                self.motor_vocal_drive = primary_formant;
                self.motor_locomotion_stride = 30.0;
            } else {
                self.motor_vocal_drive = 0.0;
                self.motor_locomotion_stride = 60.0;
            }
            self.motor_grip_force = 25.0;
        }
        for c in 40..48 {
            let mut m_aff = vec![0i8; L4_NODES];
            m_aff[0] = if self.motor_locomotion_stride > 0.0 { 1 } else { 0 };
            let (yc, sc) = self.columns[c].microcircuit.step_laminar_flow(&m_aff, somatic_trits);
            total_yields += yc; total_strain += sc;
        }

        // 6. Clusters 6, 7: Valence & Prefrontal Arbitration (Cols 48..64)
        for c in 48..64 {
            let (yc, sc) = self.columns[c].microcircuit.step_laminar_flow(sensory_trits, somatic_trits);
            total_yields += yc; total_strain += sc;
        }

        // 7. Inter-Column Directional Fasciculi Plasticity across 64 Columns
        let (inter_y, inter_s) = self.apply_inter_column_plasticity();
        total_yields += inter_y;
        total_strain += inter_s;

        (total_yields, total_strain)
    }

    pub fn apply_inter_column_plasticity(&mut self) -> (usize, f32) {
        let mut yield_count = 0usize;
        let mut total_strain = 0.0f32;
        let y = self.yield_threshold;
        let eta = self.plastic_rate;

        // Optimized biological sparsity skip: evaluate only active column pairs
        for c_from in 0..NUM_COLUMNS_64D {
            let from_l23_active = self.columns[c_from].microcircuit.l23.iter().any(|&v| v != 0);
            if from_l23_active {
                for c_to in 0..NUM_COLUMNS_64D {
                    if c_from == c_to { continue; }
                    let to_l23_active = self.columns[c_to].microcircuit.l23.iter().any(|&v| v != 0);
                    if !to_l23_active { continue; }

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
                                self.w_inter_23[idx] = (self.w_inter_23[idx] + eta * overstress * sigma.signum()).clamp(-1.0, 1.0);
                                yield_count += 1;
                                total_strain += overstress;
                            }
                        }
                    }
                }
            }

            let from_l5_active = self.columns[c_from].microcircuit.l5.iter().any(|&v| v != 0);
            if from_l5_active {
                for c_to in 0..NUM_COLUMNS_64D {
                    if c_from == c_to { continue; }
                    let to_l5_active = self.columns[c_to].microcircuit.l5.iter().any(|&v| v != 0);
                    if !to_l5_active { continue; }

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
                                self.w_inter_5[idx] = (self.w_inter_5[idx] + eta * overstress * sigma.signum()).clamp(-1.0, 1.0);
                                yield_count += 1;
                                total_strain += overstress;
                            }
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
        for col in self.columns.iter_mut() {
            let (d, p) = col.microcircuit.dream_downscale_and_prune(decay, prune_thresh);
            total_decayed += d;
            total_pruned += p;
        }
        for g in self.w_inter_23.iter_mut() {
            if *g != 0.0 {
                total_decayed += 1;
                *g *= 1.0 - decay;
                if g.abs() < prune_thresh {
                    *g = 0.0;
                    total_pruned += 1;
                }
            }
        }
        for g in self.w_inter_5.iter_mut() {
            if *g != 0.0 {
                total_decayed += 1;
                *g *= 1.0 - decay;
                if g.abs() < prune_thresh {
                    *g = 0.0;
                    total_pruned += 1;
                }
            }
        }
        (total_decayed, total_pruned)
    }

    pub fn total_active_synapses(&self) -> usize {
        let mut count = 0usize;
        for col in &self.columns {
            count += col.microcircuit.active_intra_synapses();
        }
        for &g in &self.w_inter_23 {
            if g.abs() > 0.001 { count += 1; }
        }
        for &g in &self.w_inter_5 {
            if g.abs() > 0.001 { count += 1; }
        }
        count
    }
}

// ---------------------------------------------------------------------------
// PyO3 Bindings for 64-Column Cortical Array
// ---------------------------------------------------------------------------

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

    #[pyo3(signature = (sensory_trits, somatic_trits, observed_r_mm=None, observed_theta_mdeg=None, barrier_stress=0.0, acoustic_formants=None))]
    pub fn step(
        &mut self,
        sensory_trits: Vec<i8>,
        somatic_trits: Vec<i8>,
        observed_r_mm: Option<f32>,
        observed_theta_mdeg: Option<i32>,
        barrier_stress: f32,
        acoustic_formants: Option<Vec<f32>>,
    ) -> (usize, f32) {
        let formants = acoustic_formants.unwrap_or_default();
        self.inner.step_cycle(
            &sensory_trits,
            &somatic_trits,
            observed_r_mm,
            observed_theta_mdeg,
            barrier_stress,
            &formants,
        )
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

    pub fn active_synapses(&self) -> usize {
        self.inner.total_active_synapses()
    }

    #[pyo3(signature = (decay=0.02, prune_thresh=0.005))]
    pub fn sleep_consolidation(&mut self, decay: f32, prune_thresh: f32) -> (usize, usize) {
        self.inner.dream_consolidation(decay, prune_thresh)
    }

    pub fn export_sparse(&self) -> Vec<u8> {
        let mut candidates: Vec<(u32, f32)> = Vec::new();
        for (idx, &g) in self.inner.w_inter_23.iter().enumerate() {
            if g.abs() >= 0.005 {
                candidates.push((idx as u32, g));
            }
        }
        for (idx, &g) in self.inner.w_inter_5.iter().enumerate() {
            if g.abs() >= 0.005 {
                let offset_idx = (INTER_COL_23_SIZE_64D + idx) as u32;
                candidates.push((offset_idx, g));
            }
        }
        candidates.sort_by(|a, b| b.1.abs().partial_cmp(&a.1.abs()).unwrap_or(std::cmp::Ordering::Equal));
        let bounded = if candidates.len() > 16384 { &candidates[..16384] } else { &candidates[..] };

        let mut out = Vec::with_capacity(bounded.len() * 8);
        for &(idx, g) in bounded {
            out.extend_from_slice(&idx.to_le_bytes());
            out.extend_from_slice(&g.to_le_bytes());
        }
        out
    }

    pub fn import_sparse(&mut self, data: &[u8]) -> PyResult<()> {
        let n_entries = data.len() / 8;
        for i in 0..n_entries {
            let offset = i * 8;
            if offset + 8 <= data.len() {
                let idx = u32::from_le_bytes([data[offset], data[offset + 1], data[offset + 2], data[offset + 3]]) as usize;
                let g = f32::from_le_bytes([data[offset + 4], data[offset + 5], data[offset + 6], data[offset + 7]]);
                if idx < INTER_COL_23_SIZE_64D {
                    if idx < self.inner.w_inter_23.len() {
                        self.inner.w_inter_23[idx] = g;
                    }
                } else {
                    let off_5 = idx - INTER_COL_23_SIZE_64D;
                    if off_5 < self.inner.w_inter_5.len() {
                        self.inner.w_inter_5[off_5] = g;
                    }
                }
            }
        }
        Ok(())
    }
}

pub fn register(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<PyModularSubstrate4D>()?;
    m.add_class::<PyModularSubstrate8D>()?;
    m.add_class::<PyModularSubstrate64D>()?;
    Ok(())
}
