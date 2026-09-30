//! ternary_lattice.rs -- Native 1,024-Node Discrete Ternary Contact Matrix
//!
//! Substrate: ArcLoom Discrete Ternary Neuromorphic Core (N = 1,024 nodes)
//!
//! Evaluates:
//!   1. Discrete ternary node states: T_i ∈ {-1, 0, +1} (inhibitory, null/rest, active).
//!   2. 1,024 x 1,024 contact conductance matrix g_ij ∈ [-1.0, 1.0] (signed phase/anti-phase contact bridges).
//!   3. Continuum von Mises yield stress plasticity:
//!        f(σ_ij) = |σ_ij| - Y <= 0
//!        Δg_ij = η * (|σ_ij| - Y) * sgn(σ_ij)
//!      operating locally at the point of physical current/strain with zero backpropagation.
//!   4. Content-Addressable Memory (CAM) parallel Hamming resonance and energy gradient relaxation:
//!        H(T) = -0.5 * Σ_{i != j} g_ij * T_i * T_j
//!        E_i = Σ_j g_ij * T_j
//!   5. Memory capacity and cross-talk boundary measurement without software dictionaries.
//!   6. Compact sparse conductance serialization for persistent body storage.
//!   7. Offline Dream Replay and Sleep Consolidation:
//!        - High-salience waking Krimelack replay with plastic reinforcement.
//!        - Synaptic downscaling and noise pruning (Synaptic Homeostasis Hypothesis).
//!
//! Thread-safe, lock-free computation, release-performance optimized.

use pyo3::prelude::*;
use pyo3::exceptions::PyValueError;

pub const LATTICE_NODES: usize = 1024;
pub const MATRIX_SIZE: usize = LATTICE_NODES * LATTICE_NODES;

/// Core 1,024-Node Discrete Ternary Contact Matrix
pub struct TernaryLattice {
    /// Contact conductance matrix g_ij in [-1.0, 1.0], symmetric flat buffer of size 1024 * 1024
    conductance: Vec<f32>,
    /// Material yield threshold Y ∈ (0.0, 1.0)
    yield_threshold: f32,
    /// Plastic flow rate η > 0.0
    plastic_rate: f32,
    /// Node activation threshold θ for state transitions
    activation_threshold: f32,
}

impl TernaryLattice {
    /// Create a new 1,024-node ternary contact lattice with virgin (zero) conductance
    pub fn new(yield_threshold: f32, plastic_rate: f32, activation_threshold: f32) -> Self {
        Self {
            conductance: vec![0.0f32; MATRIX_SIZE],
            yield_threshold: yield_threshold.clamp(0.01, 0.99),
            plastic_rate: plastic_rate.clamp(0.001, 1.0),
            activation_threshold: activation_threshold.max(0.0),
        }
    }

    #[inline(always)]
    fn index(i: usize, j: usize) -> usize {
        i * LATTICE_NODES + j
    }

    /// Read conductance g_ij
    #[inline(always)]
    pub fn get_conductance(&self, i: usize, j: usize) -> f32 {
        if i >= LATTICE_NODES || j >= LATTICE_NODES {
            return 0.0;
        }
        self.conductance[Self::index(i, j)]
    }

    /// Present a multi-sensory ternary pattern T ∈ {-1, 0, +1}^1024 and apply local material yield plasticity.
    pub fn present_and_yield(&mut self, pattern: &[i8]) -> Result<(usize, f32), &'static str> {
        if pattern.len() != LATTICE_NODES {
            return Err("Pattern length must be exactly 1024 trits");
        }

        let mut yield_count = 0usize;
        let mut total_strain = 0.0f32;

        let active_nodes: Vec<(usize, i8)> = pattern
            .iter()
            .enumerate()
            .filter_map(|(idx, &val)| if val != 0 { Some((idx, val)) } else { None })
            .collect();

        let num_active = active_nodes.len();

        for a in 0..num_active {
            let (i, ti) = active_nodes[a];
            for b in (a + 1)..num_active {
                let (j, tj) = active_nodes[b];

                let target_coupling = (ti * tj) as f32; // +1.0 if correlated, -1.0 if anti-correlated
                let idx_ij = Self::index(i, j);
                let idx_ji = Self::index(j, i);

                let g_cur = self.conductance[idx_ij];
                let stress = target_coupling - g_cur;
                let abs_stress = stress.abs();

                if abs_stress > self.yield_threshold {
                    let over_yield = abs_stress - self.yield_threshold;
                    let delta_g = self.plastic_rate * over_yield * stress.signum();
                    let g_new = (g_cur + delta_g).clamp(-1.0, 1.0);

                    self.conductance[idx_ij] = g_new;
                    self.conductance[idx_ji] = g_new;

                    yield_count += 1;
                    total_strain += over_yield;
                }
            }
        }

        Ok((yield_count, total_strain))
    }

    /// Replay an experiential Krimelack pattern through the matrix during offline sleep.
    /// Applies local yield plasticity with an optional plastic boost factor.
    pub fn replay_pattern(&mut self, pattern: &[i8], plastic_boost: f32) -> Result<(usize, f32), &'static str> {
        if pattern.len() != LATTICE_NODES {
            return Err("Pattern length must be exactly 1024 trits");
        }

        let boost = plastic_boost.clamp(0.1, 5.0);
        let effective_rate = (self.plastic_rate * boost).clamp(0.001, 1.0);

        let mut yield_count = 0usize;
        let mut total_strain = 0.0f32;

        let active_nodes: Vec<(usize, i8)> = pattern
            .iter()
            .enumerate()
            .filter_map(|(idx, &val)| if val != 0 { Some((idx, val)) } else { None })
            .collect();

        let num_active = active_nodes.len();

        for a in 0..num_active {
            let (i, ti) = active_nodes[a];
            for b in (a + 1)..num_active {
                let (j, tj) = active_nodes[b];

                let target_coupling = (ti * tj) as f32;
                let idx_ij = Self::index(i, j);
                let idx_ji = Self::index(j, i);

                let g_cur = self.conductance[idx_ij];
                let stress = target_coupling - g_cur;
                let abs_stress = stress.abs();

                if abs_stress > self.yield_threshold {
                    let over_yield = abs_stress - self.yield_threshold;
                    let delta_g = effective_rate * over_yield * stress.signum();
                    let g_new = (g_cur + delta_g).clamp(-1.0, 1.0);

                    self.conductance[idx_ij] = g_new;
                    self.conductance[idx_ji] = g_new;

                    yield_count += 1;
                    total_strain += over_yield;
                }
            }
        }

        Ok((yield_count, total_strain))
    }

    /// Apply sleep synaptic downscaling and noise pruning (Synaptic Homeostasis Hypothesis).
    /// Conductances decay toward zero: g_ij -> g_ij * (1.0 - decay_factor).
    /// If |g_ij| < min_conductance, the synapse is pruned to 0.0.
    /// Returns (decayed_count, pruned_count).
    pub fn decay_and_prune(&mut self, decay_factor: f32, min_conductance: f32) -> (usize, usize) {
        let decay = decay_factor.clamp(0.0, 1.0);
        let min_g = min_conductance.max(0.0);
        let scale = 1.0 - decay;

        let mut decayed_count = 0usize;
        let mut pruned_count = 0usize;

        for i in 0..LATTICE_NODES {
            let row = i * LATTICE_NODES;
            for j in (i + 1)..LATTICE_NODES {
                let idx_ij = row + j;
                let g = self.conductance[idx_ij];
                if g != 0.0 {
                    let mut g_new = g * scale;
                    if g_new.abs() < min_g {
                        g_new = 0.0;
                        pruned_count += 1;
                    } else {
                        decayed_count += 1;
                    }
                    self.conductance[idx_ij] = g_new;
                    self.conductance[j * LATTICE_NODES + i] = g_new;
                }
            }
        }

        (decayed_count, pruned_count)
    }

    /// Compute parallel node excitations: E_i = Σ_j g_ij * T_j
    pub fn compute_node_excitations(&self, state: &[i8]) -> Result<Vec<f32>, &'static str> {
        if state.len() != LATTICE_NODES {
            return Err("State vector must be exactly 1024 trits");
        }

        let mut excitations = vec![0.0f32; LATTICE_NODES];

        for i in 0..LATTICE_NODES {
            let row_offset = i * LATTICE_NODES;
            let mut sum = 0.0f32;
            for j in 0..LATTICE_NODES {
                let tj = state[j];
                if tj != 0 {
                    sum += self.conductance[row_offset + j] * (tj as f32);
                }
            }
            excitations[i] = sum;
        }

        Ok(excitations)
    }

    /// Perform Content-Addressable Memory (CAM) associative recall.
    pub fn recall(&self, cue: &[i8], steps: usize) -> Result<Vec<i8>, &'static str> {
        if cue.len() != LATTICE_NODES {
            return Err("Cue vector must be exactly 1024 trits");
        }

        let mut current_state = cue.to_vec();

        for _ in 0..steps {
            let mut next_state = vec![0i8; LATTICE_NODES];
            let mut changed = false;

            for i in 0..LATTICE_NODES {
                let row_offset = i * LATTICE_NODES;
                let mut sum = 0.0f32;
                for j in 0..LATTICE_NODES {
                    let tj = current_state[j];
                    if tj != 0 {
                        sum += self.conductance[row_offset + j] * (tj as f32);
                    }
                }

                let new_val = if sum > self.activation_threshold {
                    1i8
                } else if sum < -self.activation_threshold {
                    -1i8
                } else {
                    0i8
                };

                if new_val != current_state[i] {
                    changed = true;
                }
                next_state[i] = new_val;
            }

            current_state = next_state;
            if !changed {
                break;
            }
        }

        Ok(current_state)
    }

    /// Compute total lattice Hamiltonian energy:
    ///   H(T) = -0.5 * Σ_{i != j} g_ij * T_i * T_j
    pub fn compute_energy(&self, state: &[i8]) -> Result<f64, &'static str> {
        if state.len() != LATTICE_NODES {
            return Err("State vector must be exactly 1024 trits");
        }

        let mut energy = 0.0f64;

        for i in 0..LATTICE_NODES {
            let ti = state[i];
            if ti == 0 {
                continue;
            }
            let row_offset = i * LATTICE_NODES;
            let mut inner = 0.0f64;
            for j in 0..LATTICE_NODES {
                if i != j {
                    let tj = state[j];
                    if tj != 0 {
                        inner += (self.conductance[row_offset + j] as f64) * (tj as f64);
                    }
                }
            }
            energy += (ti as f64) * inner;
        }

        Ok(-0.5 * energy)
    }

    /// Return global matrix statistics: (mean_abs_conductance, max_abs_conductance, active_synapse_count)
    pub fn matrix_statistics(&self) -> (f32, f32, usize) {
        let mut sum = 0.0f64;
        let mut max_val = 0.0f32;
        let mut active_count = 0usize;

        for &g in &self.conductance {
            let abs_g = g.abs();
            if abs_g > 1e-6 {
                sum += abs_g as f64;
                if abs_g > max_val {
                    max_val = abs_g;
                }
                active_count += 1;
            }
        }

        let mean = if active_count > 0 {
            (sum / (active_count as f64)) as f32
        } else {
            0.0f32
        };

        (mean, max_val, active_count)
    }

    /// Export all non-zero conductances as (i, j, g_ij) tuples
    pub fn export_sparse_conductances(&self) -> Vec<(usize, usize, f32)> {
        let mut sparse = Vec::new();
        for i in 0..LATTICE_NODES {
            let row = i * LATTICE_NODES;
            for j in (i + 1)..LATTICE_NODES {
                let g = self.conductance[row + j];
                if g.abs() > 1e-5 {
                    sparse.push((i, j, g));
                }
            }
        }
        sparse
    }

    /// Import sparse conductances into the matrix
    pub fn import_sparse_conductances(&mut self, entries: &[(usize, usize, f32)]) {
        self.conductance.fill(0.0f32);
        for &(i, j, g) in entries {
            if i < LATTICE_NODES && j < LATTICE_NODES {
                let g_clamped = g.clamp(-1.0, 1.0);
                self.conductance[Self::index(i, j)] = g_clamped;
                self.conductance[Self::index(j, i)] = g_clamped;
            }
        }
    }

    /// Reset conductance matrix to zero (virgin state)
    pub fn clear(&mut self) {
        self.conductance.fill(0.0f32);
    }
}

// ---------------------------------------------------------------------------
// PyO3 Python Wrapper Class
// ---------------------------------------------------------------------------

#[pyclass(name = "TernaryLattice")]
pub struct PyTernaryLattice {
    inner: TernaryLattice,
}

#[pymethods]
impl PyTernaryLattice {
    #[new]
    #[pyo3(signature = (yield_threshold=0.4, plastic_rate=0.25, activation_threshold=5.0))]
    pub fn new(yield_threshold: f32, plastic_rate: f32, activation_threshold: f32) -> Self {
        Self {
            inner: TernaryLattice::new(yield_threshold, plastic_rate, activation_threshold),
        }
    }

    /// Get total node count (always 1024)
    #[getter]
    pub fn node_count(&self) -> usize {
        LATTICE_NODES
    }

    /// Get total synapse count (1024 * 1024 = 1,048,576)
    #[getter]
    pub fn synapse_count(&self) -> usize {
        MATRIX_SIZE
    }

    /// Present a 1,024-trit pattern and apply local material yield plasticity.
    /// Returns (yielding_synapses_count, total_strain_energy).
    pub fn present_and_yield(&mut self, py: Python<'_>, pattern: Vec<i8>) -> PyResult<(usize, f32)> {
        py.allow_threads(|| {
            self.inner
                .present_and_yield(&pattern)
                .map_err(|e| PyValueError::new_err(e))
        })
    }

    /// Replay an experiential Krimelack pattern during offline sleep with plastic yield reinforcement.
    /// Returns (yielding_synapses_count, total_strain_energy).
    #[pyo3(signature = (pattern, plastic_boost=1.0))]
    pub fn replay_pattern(&mut self, py: Python<'_>, pattern: Vec<i8>, plastic_boost: f32) -> PyResult<(usize, f32)> {
        py.allow_threads(|| {
            self.inner
                .replay_pattern(&pattern, plastic_boost)
                .map_err(|e| PyValueError::new_err(e))
        })
    }

    /// Sleep synaptic downscaling and noise pruning (Synaptic Homeostasis Hypothesis).
    /// Scales conductances by (1.0 - decay_factor) and zeroes out those with |g_ij| < min_conductance.
    /// Returns (decayed_count, pruned_count).
    #[pyo3(signature = (decay_factor=0.05, min_conductance=0.02))]
    pub fn decay_and_prune(&mut self, decay_factor: f32, min_conductance: f32) -> (usize, usize) {
        self.inner.decay_and_prune(decay_factor, min_conductance)
    }

    /// Associative recall from a partial or corrupted 1,024-trit cue.
    pub fn recall(&self, py: Python<'_>, cue: Vec<i8>, steps: usize) -> PyResult<Vec<i8>> {
        py.allow_threads(|| {
            self.inner
                .recall(&cue, steps)
                .map_err(|e| PyValueError::new_err(e))
        })
    }

    /// Compute Hamiltonian energy of a state vector
    pub fn compute_energy(&self, state: Vec<i8>) -> PyResult<f64> {
        self.inner
            .compute_energy(&state)
            .map_err(|e| PyValueError::new_err(e))
    }

    /// Compute node excitation voltages
    pub fn compute_node_excitations(&self, py: Python<'_>, state: Vec<i8>) -> PyResult<Vec<f32>> {
        self.inner
            .compute_node_excitations(&state)
            .map_err(|e| PyValueError::new_err(e))
    }

    /// Read specific conductance g_ij
    pub fn get_conductance(&self, i: usize, j: usize) -> f32 {
        self.inner.get_conductance(i, j)
    }

    /// Return (mean_active_conductance, max_conductance, active_synapse_count)
    pub fn matrix_statistics(&self) -> (f32, f32, usize) {
        self.inner.matrix_statistics()
    }

    /// Export non-zero conductances as list of (i, j, g) tuples for body serialization
    pub fn export_sparse_conductances(&self) -> Vec<(usize, usize, f32)> {
        self.inner.export_sparse_conductances()
    }

    /// Import sparse conductances from list of (i, j, g) tuples
    pub fn import_sparse_conductances(&mut self, entries: Vec<(usize, usize, f32)>) {
        self.inner.import_sparse_conductances(&entries);
    }

    /// Clear all synaptic conductances
    pub fn clear(&mut self) {
        self.inner.clear();
    }
}

pub fn register(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<PyTernaryLattice>()?;
    Ok(())
}
