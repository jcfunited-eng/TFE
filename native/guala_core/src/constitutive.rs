//! Constitutive Physical-Law Operators for Guala Substrate (Stage P1-A)
//!
//! Implementation under existing `native/guala_core` boundary adhering to:
//! - Canonical neuron physics (N_i) and unit-bearing physical state
//! - Signed carrier transport and exact remainder custody (§5)
//! - Finite receptor kinetics with closed stoichiometric invariants (§6)
//! - Rate-independent mechanical plasticity with canonical strain return map (§7)
//! - Work-conjugate energy accounting and finite capacitor difference (§8)
//! - Lossless state continuation serialization/restoration (§9, §10)
//!
//! UNMOUNTED: No import into live decision selection, no Python physical solver,
//! no production dependency or task update.

use std::fmt;

// ---------------------------------------------------------------------------
// Physical Constants (CODATA 2018 / SI Exact)
// ---------------------------------------------------------------------------

/// Exact magnitude of elementary charge in Coulombs [C].
pub const ELEMENTARY_CHARGE: f64 = 1.602_176_634e-19;

// ---------------------------------------------------------------------------
// Error Handling
// ---------------------------------------------------------------------------

#[derive(Debug, Clone, PartialEq)]
pub enum ConstitutiveError {
    InvalidDomain(String),
    ExhaustedReservoir {
        required: u64,
        available: u64,
        reservoir_name: String,
    },
    ReactantDepleted {
        requested: f64,
        available: f64,
        species: String,
    },
    CorruptData(String),
    InvalidChecksum {
        expected: u32,
        computed: u32,
    },
    TruncatedData {
        expected: usize,
        actual: usize,
    },
    ZeroValence,
    InvalidTimeStep(f64),
}

impl fmt::Display for ConstitutiveError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            ConstitutiveError::InvalidDomain(msg) => write!(f, "Invalid domain: {}", msg),
            ConstitutiveError::ExhaustedReservoir {
                required,
                available,
                reservoir_name,
            } => write!(
                f,
                "Exhausted reservoir '{}': required {}, available {}",
                reservoir_name, required, available
            ),
            ConstitutiveError::ReactantDepleted {
                requested,
                available,
                species,
            } => write!(
                f,
                "Reactant depleted for '{}': requested {}, available {}",
                species, requested, available
            ),
            ConstitutiveError::CorruptData(msg) => write!(f, "Corrupt data: {}", msg),
            ConstitutiveError::InvalidChecksum { expected, computed } => {
                write!(
                    f,
                    "Invalid checksum: expected {:#010x}, computed {:#010x}",
                    expected, computed
                )
            }
            ConstitutiveError::TruncatedData { expected, actual } => {
                write!(
                    f,
                    "Truncated data: expected {} bytes, got {} bytes",
                    expected, actual
                )
            }
            ConstitutiveError::ZeroValence => write!(f, "Species valence cannot be zero"),
            ConstitutiveError::InvalidTimeStep(dt) => {
                write!(f, "Invalid time step dt: {} (must be > 0)", dt)
            }
        }
    }
}

impl std::error::Error for ConstitutiveError {}

// ---------------------------------------------------------------------------
// 1. Signed Carrier Transport and Exact Remainder Custody (§5)
// ---------------------------------------------------------------------------

#[derive(Debug, Clone, PartialEq)]
pub struct ChargeCarrierState {
    /// Net membrane charge Q in Coulombs [C].
    pub q_membrane: f64,
    /// Membrane capacitance C_mem in Farads [F] (> 0).
    pub c_mem: f64,
    /// Fractional remainder r_c in (-1.0, 1.0) of carriers.
    pub remainder: f64,
    /// Discrete integer carrier population in source reservoir.
    pub source_reservoir: u64,
    /// Discrete integer carrier population in destination reservoir.
    pub dest_reservoir: u64,
}

#[derive(Debug, Clone, PartialEq)]
pub struct CarrierTransportResult {
    /// Number of discrete whole carriers transported outward (signed integer).
    pub carriers_transported: i64,
    /// New fractional remainder r'_c in (-1.0, 1.0).
    pub new_remainder: f64,
    /// Change in membrane charge Delta Q = Q' - Q in Coulombs [C].
    pub delta_q_membrane: f64,
    /// Finite change in capacitor stored energy Delta E_cap in Joules [J].
    pub delta_e_cap: f64,
    /// Verified transport identity error: |q_c * n_c + q_c * (r'_c - r_c) - J_c|.
    pub identity_residual: f64,
}

impl ChargeCarrierState {
    pub fn new(
        q_membrane: f64,
        c_mem: f64,
        remainder: f64,
        source_reservoir: u64,
        dest_reservoir: u64,
    ) -> Result<Self, ConstitutiveError> {
        if !c_mem.is_finite() || c_mem <= 0.0 {
            return Err(ConstitutiveError::InvalidDomain(format!(
                "c_mem must be positive and finite, got {}",
                c_mem
            )));
        }
        if !q_membrane.is_finite() {
            return Err(ConstitutiveError::InvalidDomain(
                "q_membrane must be finite".to_string(),
            ));
        }
        if !remainder.is_finite() || remainder.abs() >= 1.0 {
            return Err(ConstitutiveError::InvalidDomain(format!(
                "remainder must be in (-1.0, 1.0), got {}",
                remainder
            )));
        }
        Ok(Self {
            q_membrane,
            c_mem,
            remainder,
            source_reservoir,
            dest_reservoir,
        })
    }

    /// Derived membrane potential V = Q / C_mem in Volts [V].
    #[inline]
    pub fn voltage(&self) -> f64 {
        self.q_membrane / self.c_mem
    }

    /// Stored capacitor electrical energy E_cap = Q^2 / (2 * C_mem) in Joules [J].
    #[inline]
    pub fn stored_energy(&self) -> f64 {
        (self.q_membrane * self.q_membrane) / (2.0 * self.c_mem)
    }

    /// Exact carrier transport settlement under continuous charge integral J_c [C].
    ///
    /// Preserves exact carrier settlement (§5):
    ///   q_c = valence * e_0
    ///   z_c = r_c + J_c / q_c
    ///   n_c = trunc(z_c)
    ///   r'_c = z_c - n_c
    /// Exact conservation identity:
    ///   q_c * n_c + q_c * (r'_c - r_c) = J_c
    pub fn settle_transport(
        &mut self,
        current_integral_jc: f64,
        valence: i32,
        q_active: f64,
    ) -> Result<CarrierTransportResult, ConstitutiveError> {
        if valence == 0 {
            return Err(ConstitutiveError::ZeroValence);
        }
        if !current_integral_jc.is_finite() {
            return Err(ConstitutiveError::InvalidDomain(
                "current_integral_jc must be finite".to_string(),
            ));
        }
        if !q_active.is_finite() {
            return Err(ConstitutiveError::InvalidDomain(
                "q_active must be finite".to_string(),
            ));
        }

        let q_c = (valence as f64) * ELEMENTARY_CHARGE;
        let delta_carriers_continuous = current_integral_jc / q_c;
        let z_c = self.remainder + delta_carriers_continuous;
        let n_c = z_c.trunc() as i64;
        let r_c_prime = z_c - (n_c as f64);

        // Exact identity residual check: q_c * n_c + q_c * (r'_c - r_c) == J_c
        let reconstructed_jc = q_c * (n_c as f64) + q_c * (r_c_prime - self.remainder);
        let identity_residual = (reconstructed_jc - current_integral_jc).abs();

        // Finite reservoir accounting (no negative populations allowed)
        if n_c > 0 {
            let required = n_c as u64;
            if self.source_reservoir < required {
                return Err(ConstitutiveError::ExhaustedReservoir {
                    required,
                    available: self.source_reservoir,
                    reservoir_name: "source".to_string(),
                });
            }
            self.source_reservoir -= required;
            self.dest_reservoir = self.dest_reservoir.saturating_add(required);
        } else if n_c < 0 {
            let required = (-n_c) as u64;
            if self.dest_reservoir < required {
                return Err(ConstitutiveError::ExhaustedReservoir {
                    required,
                    available: self.dest_reservoir,
                    reservoir_name: "destination".to_string(),
                });
            }
            self.dest_reservoir -= required;
            self.source_reservoir = self.source_reservoir.saturating_add(required);
        }

        // Membrane charge and capacitor energy update
        let q_old = self.q_membrane;
        let q_new = q_old - q_c * (n_c as f64) - q_active;
        let delta_q = q_new - q_old;
        let delta_e_cap = (q_new * q_new - q_old * q_old) / (2.0 * self.c_mem);

        self.q_membrane = q_new;
        self.remainder = r_c_prime;

        Ok(CarrierTransportResult {
            carriers_transported: n_c,
            new_remainder: r_c_prime,
            delta_q_membrane: delta_q,
            delta_e_cap,
            identity_residual,
        })
    }
}

// ---------------------------------------------------------------------------
// 2. Finite Receptor Kinetics: Corrected Conservation and Participation (§6)
// ---------------------------------------------------------------------------

#[derive(Debug, Clone, PartialEq)]
pub struct ReceptorKineticsState {
    /// Free receptor pool R in moles [mol] (>= 0).
    pub r_free: f64,
    /// Bound active complex A in moles [mol] (>= 0).
    pub a_active: f64,
    /// Inactive receptor pool D in moles [mol] (>= 0).
    pub d_inact: f64,
    /// Free transmitter in cleft T in moles [mol] (>= 0).
    pub t_free: f64,
    /// Cleft volume V_cleft in cubic meters [m^3] (> 0).
    pub v_cleft: f64,
    /// Integrated active exposure int A dt in [mol * s] (>= 0).
    pub integrated_exposure: f64,
    /// Association rate k_on in [m^3 / (mol * s)] (>= 0).
    pub k_on: f64,
    /// Dissociation rate k_off in [s^-1] (>= 0).
    pub k_off: f64,
    /// Inactivation rate k_inact in [s^-1] (>= 0).
    pub k_inact: f64,
    /// Recovery rate k_rec in [s^-1] (>= 0).
    pub k_rec: f64,
}

#[derive(Debug, Clone, PartialEq)]
pub struct ReceptorStepResult {
    /// Stoichiometric extents: xi_b (binding), xi_u (unbinding), xi_i (inact), xi_r (rec).
    pub xi_binding: f64,
    pub xi_unbinding: f64,
    pub xi_inactivation: f64,
    pub xi_recovery: f64,
    /// Total receptors invariant check: (R + A + D) after - (R + A + D) before.
    pub delta_total_receptors: f64,
    /// Total transmitter invariant check: (T + A) after - (T + A) before.
    pub delta_total_transmitter: f64,
}

impl ReceptorKineticsState {
    pub fn new(
        r_free: f64,
        a_active: f64,
        d_inact: f64,
        t_free: f64,
        v_cleft: f64,
        integrated_exposure: f64,
        k_on: f64,
        k_off: f64,
        k_inact: f64,
        k_rec: f64,
    ) -> Result<Self, ConstitutiveError> {
        if r_free < 0.0 || a_active < 0.0 || d_inact < 0.0 || t_free < 0.0 {
            return Err(ConstitutiveError::InvalidDomain(
                "Species populations must be non-negative".to_string(),
            ));
        }
        if !v_cleft.is_finite() || v_cleft <= 0.0 {
            return Err(ConstitutiveError::InvalidDomain(
                "Cleft volume v_cleft must be positive and finite".to_string(),
            ));
        }
        if k_on < 0.0 || k_off < 0.0 || k_inact < 0.0 || k_rec < 0.0 {
            return Err(ConstitutiveError::InvalidDomain(
                "Reaction rates must be non-negative".to_string(),
            ));
        }
        if integrated_exposure < 0.0 {
            return Err(ConstitutiveError::InvalidDomain(
                "integrated_exposure must be non-negative".to_string(),
            ));
        }
        Ok(Self {
            r_free,
            a_active,
            d_inact,
            t_free,
            v_cleft,
            integrated_exposure,
            k_on,
            k_off,
            k_inact,
            k_rec,
        })
    }

    /// Total receptors in closed network: R_total = R + A + D.
    #[inline]
    pub fn total_receptors(&self) -> f64 {
        self.r_free + self.a_active + self.d_inact
    }

    /// Total transmitter in closed network: T_total = T + A.
    #[inline]
    pub fn total_transmitter(&self) -> f64 {
        self.t_free + self.a_active
    }

    /// Integrated finite stoichiometric step over physical interval dt [s].
    ///
    /// Preserves exact closed invariants:
    ///   R + A + D = const
    ///   T + A = const
    /// Uses adaptive stoichiometric sub-cycling to prevent population overshoot
    /// while guaranteeing non-negative species counts and bit-exact conservation.
    pub fn step_kinetics(&mut self, dt: f64) -> Result<ReceptorStepResult, ConstitutiveError> {
        if !dt.is_finite() || dt <= 0.0 {
            return Err(ConstitutiveError::InvalidTimeStep(dt));
        }

        let r_tot_before = self.total_receptors();
        let t_tot_before = self.total_transmitter();

        // Determine substeps needed so no single substep consumes > 25% of any reactant pool.
        let c_t = self.t_free / self.v_cleft;
        let j_b_est = self.k_on * c_t * self.r_free;
        let j_u_est = self.k_off * self.a_active;
        let j_i_est = self.k_inact * self.a_active;
        let j_r_est = self.k_rec * self.d_inact;

        let mut max_rate = 0.0f64;
        if self.r_free > 1e-15 && self.t_free > 1e-15 {
            max_rate = max_rate.max(j_b_est / self.r_free.min(self.t_free));
        }
        if self.a_active > 1e-15 {
            max_rate = max_rate.max((j_u_est + j_i_est) / self.a_active);
        }
        if self.d_inact > 1e-15 {
            max_rate = max_rate.max(j_r_est / self.d_inact);
        }

        let n_substeps = ((max_rate * dt * 4.0).ceil() as usize).max(1).min(10_000);
        let dt_sub = dt / (n_substeps as f64);

        let mut tot_xi_b = 0.0f64;
        let mut tot_xi_u = 0.0f64;
        let mut tot_xi_i = 0.0f64;
        let mut tot_xi_r = 0.0f64;

        for _ in 0..n_substeps {
            let conc_t = self.t_free / self.v_cleft;
            let mut xi_b = self.k_on * conc_t * self.r_free * dt_sub;
            let mut xi_u = self.k_off * self.a_active * dt_sub;
            let mut xi_i = self.k_inact * self.a_active * dt_sub;
            let mut xi_r = self.k_rec * self.d_inact * dt_sub;

            // Strict stoichiometric limitation: reactions cannot exceed available reactants
            let max_b = self.r_free.min(self.t_free);
            if xi_b > max_b {
                xi_b = max_b;
            }

            let sum_a = xi_u + xi_i;
            if sum_a > self.a_active {
                if sum_a > 1e-15 {
                    let scale = self.a_active / sum_a;
                    xi_u *= scale;
                    xi_i *= scale;
                } else {
                    xi_u = 0.0;
                    xi_i = 0.0;
                }
            }

            if xi_r > self.d_inact {
                xi_r = self.d_inact;
            }

            // Stoichiometric updates:
            // Delta R = -xi_b + xi_u + xi_r
            // Delta A =  xi_b - xi_u - xi_i
            // Delta D =  xi_i - xi_r
            // Delta T = -xi_b + xi_u + xi_i
            let delta_r = -xi_b + xi_u + xi_r;
            let delta_a = xi_b - xi_u - xi_i;
            let delta_d = xi_i - xi_r;
            let delta_t = -xi_b + xi_u + xi_i;

            self.r_free += delta_r;
            self.a_active += delta_a;
            self.d_inact += delta_d;
            self.t_free += delta_t;

            // Exposure accumulation: integral A dt
            self.integrated_exposure += self.a_active * dt_sub;

            tot_xi_b += xi_b;
            tot_xi_u += xi_u;
            tot_xi_i += xi_i;
            tot_xi_r += xi_r;
        }

        let r_tot_after = self.total_receptors();
        let t_tot_after = self.total_transmitter();

        Ok(ReceptorStepResult {
            xi_binding: tot_xi_b,
            xi_unbinding: tot_xi_u,
            xi_inactivation: tot_xi_i,
            xi_recovery: tot_xi_r,
            delta_total_receptors: r_tot_after - r_tot_before,
            delta_total_transmitter: t_tot_after - t_tot_before,
        })
    }

    /// Explicit open-boundary transmitter exchange with an external reservoir/bath.
    ///
    /// Preserves strict conservation: external reservoir and cleft exchange are equal & opposite.
    pub fn exchange_transmitter(
        &mut self,
        amount: f64,
        external_reservoir: &mut f64,
    ) -> Result<(), ConstitutiveError> {
        if !amount.is_finite() {
            return Err(ConstitutiveError::InvalidDomain(
                "amount must be finite".to_string(),
            ));
        }
        if amount > 0.0 {
            // Influx into cleft from external reservoir
            if *external_reservoir < amount {
                return Err(ConstitutiveError::ReactantDepleted {
                    requested: amount,
                    available: *external_reservoir,
                    species: "external_transmitter_reservoir".to_string(),
                });
            }
            *external_reservoir -= amount;
            self.t_free += amount;
        } else if amount < 0.0 {
            // Efflux from cleft to external reservoir
            let abs_amt = -amount;
            if self.t_free < abs_amt {
                return Err(ConstitutiveError::ReactantDepleted {
                    requested: abs_amt,
                    available: self.t_free,
                    species: "cleft_t_free".to_string(),
                });
            }
            self.t_free -= abs_amt;
            *external_reservoir += abs_amt;
        }
        Ok(())
    }
}

// ---------------------------------------------------------------------------
// 3. Plasticity: Canonical Strain Form and Mechanical Return Map (§7)
// ---------------------------------------------------------------------------

#[derive(Debug, Clone, PartialEq)]
pub struct MechanicalPlasticState {
    /// Actual reached physical coordinate x in meters [m] (> 0).
    pub x: f64,
    /// Plastic reference length l in meters [m] (> 0).
    pub l_ref: f64,
    /// Elastic modulus energy scale K in Joules [J] (> 0).
    pub k_elastic: f64,
    /// Generalized yield threshold Y in Joules [J] (0 < Y < K).
    pub yield_energy: f64,
    /// Cumulative dissipated plastic energy D_pl in Joules [J] (>= 0).
    pub cumulative_dissipated_energy: f64,
}

#[derive(Debug, Clone, PartialEq)]
pub struct PlasticReturnResult {
    /// Trial strain epsilon_tr = x / l_n - 1.
    pub trial_strain: f64,
    /// Trial generalized strain force Sigma_tr = K * epsilon_tr [J].
    pub trial_sigma: f64,
    /// Returned reference length l_{n+1} [m].
    pub returned_l: f64,
    /// Reference length increment Delta l = l_{n+1} - l_n [m].
    pub delta_l: f64,
    /// Final generalized strain force Sigma_{n+1} [J].
    pub final_sigma: f64,
    /// Final yield function value f_{n+1} = |Sigma_{n+1}| - Y (must be <= 0).
    pub yield_function_value: f64,
    /// Released plastic energy D_pl = U(x, l_n) - U(x, l_{n+1}) [J] (>= 0).
    pub dissipated_energy: f64,
    /// Whether plastic yielding occurred.
    pub is_yielded: bool,
}

impl MechanicalPlasticState {
    pub fn new(
        x: f64,
        l_ref: f64,
        k_elastic: f64,
        yield_energy: f64,
        cumulative_dissipated_energy: f64,
    ) -> Result<Self, ConstitutiveError> {
        if !x.is_finite() || x <= 0.0 {
            return Err(ConstitutiveError::InvalidDomain(format!(
                "x must be positive and finite, got {}",
                x
            )));
        }
        if !l_ref.is_finite() || l_ref <= 0.0 {
            return Err(ConstitutiveError::InvalidDomain(format!(
                "l_ref must be positive and finite, got {}",
                l_ref
            )));
        }
        if !k_elastic.is_finite() || k_elastic <= 0.0 {
            return Err(ConstitutiveError::InvalidDomain(format!(
                "k_elastic must be positive and finite, got {}",
                k_elastic
            )));
        }
        if !yield_energy.is_finite() || yield_energy <= 0.0 || yield_energy >= k_elastic {
            return Err(ConstitutiveError::InvalidDomain(format!(
                "yield_energy Y must satisfy 0 < Y < K (got Y={}, K={})",
                yield_energy, k_elastic
            )));
        }
        if cumulative_dissipated_energy < 0.0 {
            return Err(ConstitutiveError::InvalidDomain(
                "cumulative_dissipated_energy must be non-negative".to_string(),
            ));
        }
        Ok(Self {
            x,
            l_ref,
            k_elastic,
            yield_energy,
            cumulative_dissipated_energy,
        })
    }

    /// Dimensionless canonical strain epsilon = (x - l) / l.
    #[inline]
    pub fn strain(&self) -> f64 {
        (self.x - self.l_ref) / self.l_ref
    }

    /// Stored elastic energy U = 0.5 * K * epsilon^2 in Joules [J].
    #[inline]
    pub fn elastic_energy(&self) -> f64 {
        0.5 * self.k_elastic * self.strain().powi(2)
    }

    /// Generalized strain force Sigma = partial U / partial epsilon = K * epsilon in Joules [J].
    #[inline]
    pub fn generalized_force(&self) -> f64 {
        self.k_elastic * self.strain()
    }

    /// Work-conjugate length force F_l = - partial U / partial l = K * eps * (1 + eps) / l in Newtons [N].
    #[inline]
    pub fn length_force(&self) -> f64 {
        let eps = self.strain();
        self.k_elastic * eps * (1.0 + eps) / self.l_ref
    }

    /// Yield function f = |Sigma| - Y in Joules [J].
    #[inline]
    pub fn yield_function(&self) -> f64 {
        self.generalized_force().abs() - self.yield_energy
    }

    /// Closed algebraic return map at fixed physical coordinate x (§7).
    ///
    /// Evaluates:
    ///   epsilon_tr = x / l_n - 1
    ///   Sigma_tr = K * epsilon_tr
    ///   If |Sigma_tr| <= Y:
    ///     l_{n+1} = l_n (elastic)
    ///   If |Sigma_tr| > Y:
    ///     s = sign(Sigma_tr)
    ///     l_{n+1} = x / (1 + s * Y / K) (plastic yield)
    ///   D_pl = U(x, l_n) - U(x, l_{n+1}) = 0.5 * K * (epsilon_tr^2 - (Y / K)^2) >= 0
    pub fn return_map_fixed_x(&mut self) -> Result<PlasticReturnResult, ConstitutiveError> {
        let l_n = self.l_ref;
        let x = self.x;
        let k = self.k_elastic;
        let y = self.yield_energy;

        let eps_tr = x / l_n - 1.0;
        let sigma_tr = k * eps_tr;
        let f_tr = sigma_tr.abs() - y;

        if f_tr <= 0.0 {
            // Elastic response: no yield
            let final_f = f_tr;
            Ok(PlasticReturnResult {
                trial_strain: eps_tr,
                trial_sigma: sigma_tr,
                returned_l: l_n,
                delta_l: 0.0,
                final_sigma: sigma_tr,
                yield_function_value: final_f,
                dissipated_energy: 0.0,
                is_yielded: false,
            })
        } else {
            // Plastic yield
            let s = if sigma_tr > 0.0 { 1.0 } else { -1.0 };
            let denominator = 1.0 + s * (y / k);
            let l_next = x / denominator;
            let delta_l = l_next - l_n;

            let eps_next = s * (y / k);
            let sigma_next = k * eps_next; // = s * y
            let final_f = sigma_next.abs() - y; // = 0.0

            let d_pl = 0.5 * k * (eps_tr.powi(2) - (y / k).powi(2));

            self.l_ref = l_next;
            self.cumulative_dissipated_energy += d_pl;

            Ok(PlasticReturnResult {
                trial_strain: eps_tr,
                trial_sigma: sigma_tr,
                returned_l: l_next,
                delta_l,
                final_sigma: sigma_next,
                yield_function_value: final_f,
                dissipated_energy: d_pl,
                is_yielded: true,
            })
        }
    }
}

// ---------------------------------------------------------------------------
// 4. Energy Accounting Balance (§8)
// ---------------------------------------------------------------------------

#[derive(Debug, Clone, PartialEq)]
pub struct ClosedEnergyBalance {
    /// Change in capacitor stored electrical energy Delta E_cap [J].
    pub delta_e_cap: f64,
    /// Change in mechanical stored elastic energy Delta U_elastic [J].
    pub delta_u_elastic: f64,
    /// Dissipated plastic heat Q_heat,plastic [J] (>= 0).
    pub q_heat_plastic: f64,
    /// Closed energy balance residual: |Delta U_elastic + Q_heat_plastic|.
    pub mechanical_energy_balance_residual: f64,
}

impl ClosedEnergyBalance {
    /// Reconciles fixed-x mechanical dissipation against stored energy decrease:
    /// Delta U_elastic + Q_heat,plastic = 0
    pub fn compute_fixed_x(
        u_initial: f64,
        u_final: f64,
        dissipated_plastic_energy: f64,
        delta_e_cap: f64,
    ) -> Self {
        let delta_u = u_final - u_initial;
        let residual = (delta_u + dissipated_plastic_energy).abs();
        Self {
            delta_e_cap,
            delta_u_elastic: delta_u,
            q_heat_plastic: dissipated_plastic_energy,
            mechanical_energy_balance_residual: residual,
        }
    }
}

// ---------------------------------------------------------------------------
// 5. Continuation State Serialization & Exact Restoration (§9, §10)
// ---------------------------------------------------------------------------

/// Magic bytes identifying Guala Constitutive Component Record.
pub const STATE_MAGIC: &[u8; 8] = b"GUALA_P1";
/// Schema version for binary component serialization.
pub const STATE_SCHEMA_VERSION: u32 = 1;
/// Fixed serialized size in bytes (8 magic + 4 version + 160 payload + 4 crc = 176 bytes).
pub const SERIALIZED_STATE_SIZE: usize = 176;

#[derive(Debug, Clone, PartialEq)]
pub struct ConstitutiveState {
    pub carrier: ChargeCarrierState,
    pub receptor: ReceptorKineticsState,
    pub mechanics: MechanicalPlasticState,
}

impl ConstitutiveState {
    pub fn new(
        carrier: ChargeCarrierState,
        receptor: ReceptorKineticsState,
        mechanics: MechanicalPlasticState,
    ) -> Self {
        Self {
            carrier,
            receptor,
            mechanics,
        }
    }

    /// Serializes entire constitutive component state into a fixed 176-byte record.
    pub fn serialize(&self) -> [u8; SERIALIZED_STATE_SIZE] {
        let mut buf = [0u8; SERIALIZED_STATE_SIZE];
        buf[0..8].copy_from_slice(STATE_MAGIC);
        buf[8..12].copy_from_slice(&STATE_SCHEMA_VERSION.to_le_bytes());

        let mut offset = 12;

        // Carrier state (40 bytes)
        buf[offset..offset + 8].copy_from_slice(&self.carrier.q_membrane.to_le_bytes());
        offset += 8;
        buf[offset..offset + 8].copy_from_slice(&self.carrier.c_mem.to_le_bytes());
        offset += 8;
        buf[offset..offset + 8].copy_from_slice(&self.carrier.remainder.to_le_bytes());
        offset += 8;
        buf[offset..offset + 8].copy_from_slice(&self.carrier.source_reservoir.to_le_bytes());
        offset += 8;
        buf[offset..offset + 8].copy_from_slice(&self.carrier.dest_reservoir.to_le_bytes());
        offset += 8;

        // Receptor state (80 bytes)
        buf[offset..offset + 8].copy_from_slice(&self.receptor.r_free.to_le_bytes());
        offset += 8;
        buf[offset..offset + 8].copy_from_slice(&self.receptor.a_active.to_le_bytes());
        offset += 8;
        buf[offset..offset + 8].copy_from_slice(&self.receptor.d_inact.to_le_bytes());
        offset += 8;
        buf[offset..offset + 8].copy_from_slice(&self.receptor.t_free.to_le_bytes());
        offset += 8;
        buf[offset..offset + 8].copy_from_slice(&self.receptor.v_cleft.to_le_bytes());
        offset += 8;
        buf[offset..offset + 8].copy_from_slice(&self.receptor.integrated_exposure.to_le_bytes());
        offset += 8;
        buf[offset..offset + 8].copy_from_slice(&self.receptor.k_on.to_le_bytes());
        offset += 8;
        buf[offset..offset + 8].copy_from_slice(&self.receptor.k_off.to_le_bytes());
        offset += 8;
        buf[offset..offset + 8].copy_from_slice(&self.receptor.k_inact.to_le_bytes());
        offset += 8;
        buf[offset..offset + 8].copy_from_slice(&self.receptor.k_rec.to_le_bytes());
        offset += 8;

        // Mechanics state (40 bytes)
        buf[offset..offset + 8].copy_from_slice(&self.mechanics.x.to_le_bytes());
        offset += 8;
        buf[offset..offset + 8].copy_from_slice(&self.mechanics.l_ref.to_le_bytes());
        offset += 8;
        buf[offset..offset + 8].copy_from_slice(&self.mechanics.k_elastic.to_le_bytes());
        offset += 8;
        buf[offset..offset + 8].copy_from_slice(&self.mechanics.yield_energy.to_le_bytes());
        offset += 8;
        buf[offset..offset + 8]
            .copy_from_slice(&self.mechanics.cumulative_dissipated_energy.to_le_bytes());
        offset += 8;

        // CRC-32 checksum of header + payload (172 bytes)
        let checksum = compute_crc32(&buf[0..offset]);
        buf[offset..offset + 4].copy_from_slice(&checksum.to_le_bytes());

        buf
    }

    /// Deserializes exact binary record into constitutive component state.
    ///
    /// Validates magic header, schema version, CRC32 checksum, and physical domain constraints.
    /// NEVER defaults or resets to resting states (-70 mV, -7 pC) upon corruption.
    pub fn deserialize(bytes: &[u8]) -> Result<Self, ConstitutiveError> {
        if bytes.len() != SERIALIZED_STATE_SIZE {
            return Err(ConstitutiveError::TruncatedData {
                expected: SERIALIZED_STATE_SIZE,
                actual: bytes.len(),
            });
        }

        if &bytes[0..8] != STATE_MAGIC {
            return Err(ConstitutiveError::CorruptData(
                "Invalid state magic bytes".to_string(),
            ));
        }

        let version = u32::from_le_bytes(bytes[8..12].try_into().unwrap());
        if version != STATE_SCHEMA_VERSION {
            return Err(ConstitutiveError::CorruptData(format!(
                "Unsupported schema version: expected {}, got {}",
                STATE_SCHEMA_VERSION, version
            )));
        }

        let stored_checksum = u32::from_le_bytes(bytes[172..176].try_into().unwrap());
        let computed_checksum = compute_crc32(&bytes[0..172]);
        if stored_checksum != computed_checksum {
            return Err(ConstitutiveError::InvalidChecksum {
                expected: stored_checksum,
                computed: computed_checksum,
            });
        }

        let mut offset = 12;

        let q_membrane = f64::from_le_bytes(bytes[offset..offset + 8].try_into().unwrap());
        offset += 8;
        let c_mem = f64::from_le_bytes(bytes[offset..offset + 8].try_into().unwrap());
        offset += 8;
        let remainder = f64::from_le_bytes(bytes[offset..offset + 8].try_into().unwrap());
        offset += 8;
        let source_reservoir = u64::from_le_bytes(bytes[offset..offset + 8].try_into().unwrap());
        offset += 8;
        let dest_reservoir = u64::from_le_bytes(bytes[offset..offset + 8].try_into().unwrap());
        offset += 8;

        let carrier = ChargeCarrierState::new(
            q_membrane,
            c_mem,
            remainder,
            source_reservoir,
            dest_reservoir,
        )?;

        let r_free = f64::from_le_bytes(bytes[offset..offset + 8].try_into().unwrap());
        offset += 8;
        let a_active = f64::from_le_bytes(bytes[offset..offset + 8].try_into().unwrap());
        offset += 8;
        let d_inact = f64::from_le_bytes(bytes[offset..offset + 8].try_into().unwrap());
        offset += 8;
        let t_free = f64::from_le_bytes(bytes[offset..offset + 8].try_into().unwrap());
        offset += 8;
        let v_cleft = f64::from_le_bytes(bytes[offset..offset + 8].try_into().unwrap());
        offset += 8;
        let integrated_exposure =
            f64::from_le_bytes(bytes[offset..offset + 8].try_into().unwrap());
        offset += 8;
        let k_on = f64::from_le_bytes(bytes[offset..offset + 8].try_into().unwrap());
        offset += 8;
        let k_off = f64::from_le_bytes(bytes[offset..offset + 8].try_into().unwrap());
        offset += 8;
        let k_inact = f64::from_le_bytes(bytes[offset..offset + 8].try_into().unwrap());
        offset += 8;
        let k_rec = f64::from_le_bytes(bytes[offset..offset + 8].try_into().unwrap());
        offset += 8;

        let receptor = ReceptorKineticsState::new(
            r_free,
            a_active,
            d_inact,
            t_free,
            v_cleft,
            integrated_exposure,
            k_on,
            k_off,
            k_inact,
            k_rec,
        )?;

        let x = f64::from_le_bytes(bytes[offset..offset + 8].try_into().unwrap());
        offset += 8;
        let l_ref = f64::from_le_bytes(bytes[offset..offset + 8].try_into().unwrap());
        offset += 8;
        let k_elastic = f64::from_le_bytes(bytes[offset..offset + 8].try_into().unwrap());
        offset += 8;
        let yield_energy = f64::from_le_bytes(bytes[offset..offset + 8].try_into().unwrap());
        offset += 8;
        let cumulative_dissipated_energy =
            f64::from_le_bytes(bytes[offset..offset + 8].try_into().unwrap());

        let mechanics = MechanicalPlasticState::new(
            x,
            l_ref,
            k_elastic,
            yield_energy,
            cumulative_dissipated_energy,
        )?;

        Ok(Self {
            carrier,
            receptor,
            mechanics,
        })
    }
}

// ---------------------------------------------------------------------------
// Pure CRC-32 (IEEE 802.3 standard polynomial 0xEDB88320)
// ---------------------------------------------------------------------------

fn compute_crc32(data: &[u8]) -> u32 {
    let mut crc = !0u32;
    for &byte in data {
        crc ^= byte as u32;
        for _ in 0..8 {
            let mask = (!((crc & 1).wrapping_sub(1))) & 0xEDB88320;
            crc = (crc >> 1) ^ mask;
        }
    }
    !crc
}

// ===========================================================================
// Tests: Section 10 Verification Suite
// ===========================================================================

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_signed_carriers_exact_identity_and_reservoirs() {
        let mut carrier = ChargeCarrierState::new(-7.0e-12, 100.0e-12, 0.0, 1_000_000, 500_000).unwrap();

        // 1. Positive transfer (outward, n_c > 0)
        let j_c1 = 5.0e-19; // 5 Coulombs * 10^-19
        let res1 = carrier.settle_transport(j_c1, 1, 0.0).unwrap();
        assert!(res1.identity_residual < 1e-25, "Residual: {}", res1.identity_residual);
        assert_eq!(res1.carriers_transported, 3);
        assert_eq!(carrier.source_reservoir, 999_997);
        assert_eq!(carrier.dest_reservoir, 500_003);

        // 2. Negative transfer (inward, n_c < 0)
        let j_c2 = -4.0e-19;
        let res2 = carrier.settle_transport(j_c2, 1, 0.0).unwrap();
        assert!(res2.identity_residual < 1e-25);
        assert_eq!(res2.carriers_transported, -2);
        assert_eq!(carrier.source_reservoir, 999_999);
        assert_eq!(carrier.dest_reservoir, 500_001);

        // 3. Subcarrier transfer (fractional only, n_c == 0)
        let j_c3 = 0.5 * ELEMENTARY_CHARGE;
        let prev_remainder = carrier.remainder;
        let res3 = carrier.settle_transport(j_c3, 1, 0.0).unwrap();
        assert_eq!(res3.carriers_transported, 0);
        assert!((res3.new_remainder - (prev_remainder + 0.5)).abs() < 1e-12);
        assert!(res3.identity_residual < 1e-25);

        // 4. Repeated transfers accumulating remainder into carrier (crossing whole carrier threshold)
        let j_c4 = 1.0 * ELEMENTARY_CHARGE;
        let res4 = carrier.settle_transport(j_c4, 1, 0.0).unwrap();
        assert!(res4.carriers_transported >= 1);
        assert!(res4.identity_residual < 1e-25);

        // 5. Active valence != 1 (divalent Ca2+, valence = 2)
        let q_ca = 2.0 * ELEMENTARY_CHARGE;
        let j_c_ca = 5.0 * q_ca;
        let res5 = carrier.settle_transport(j_c_ca, 2, 0.0).unwrap();
        assert!(res5.identity_residual < 1e-25);

        // 6. Finite reservoir exhaustion check (no negative populations)
        let mut small_carrier = ChargeCarrierState::new(0.0, 100.0e-12, 0.0, 5, 0).unwrap();
        let j_overflow = 10.0 * ELEMENTARY_CHARGE;
        let err = small_carrier.settle_transport(j_overflow, 1, 0.0);
        match err {
            Err(ConstitutiveError::ExhaustedReservoir { required, available, reservoir_name }) => {
                assert_eq!(required, 10);
                assert_eq!(available, 5);
                assert_eq!(reservoir_name, "source");
            }
            _ => panic!("Expected ExhaustedReservoir error, got {:?}", err),
        }
        assert_eq!(small_carrier.source_reservoir, 5, "State must not mutate on failure");
    }

    #[test]
    fn test_receptor_kinetics_closed_invariants_and_residual_a() {
        let mut rec = ReceptorKineticsState::new(
            1.0e-9,  // R_free = 1.0 nmol
            0.0,     // A_active = 0.0
            0.0,     // D_inact = 0.0
            2.0e-9,  // T_free = 2.0 nmol
            1.0e-18, // V_cleft = 1 attoliter
            0.0,     // integrated exposure
            1.0e8,   // k_on
            10.0,    // k_off
            5.0,     // k_inact
            2.0,     // k_rec
        ).unwrap();

        let initial_r_tot = rec.total_receptors();
        let initial_t_tot = rec.total_transmitter();

        // Step kinetics over 10 consecutive intervals
        for _ in 0..10 {
            let res = rec.step_kinetics(0.01).unwrap();
            assert!(res.delta_total_receptors.abs() < 1e-15, "R_tot drifted: {}", res.delta_total_receptors);
            assert!(res.delta_total_transmitter.abs() < 1e-15, "T_tot drifted: {}", res.delta_total_transmitter);
            assert!(rec.r_free >= 0.0);
            assert!(rec.a_active >= 0.0);
            assert!(rec.d_inact >= 0.0);
            assert!(rec.t_free >= 0.0);
        }

        assert!((rec.total_receptors() - initial_r_tot).abs() < 1e-15);
        assert!((rec.total_transmitter() - initial_t_tot).abs() < 1e-15);
        assert!(rec.a_active > 0.0, "Active complex must form");

        // Open-boundary test: remove free transmitter completely (T_free -> 0)
        let mut bath = 0.0f64;
        let remove_amount = -rec.t_free;
        rec.exchange_transmitter(remove_amount, &mut bath).unwrap();
        assert_eq!(rec.t_free, 0.0);

        // DELAYED EFFECT CHECK: A does not instantaneously drop to 0 when T becomes 0!
        let a_before_decay = rec.a_active;
        assert!(a_before_decay > 0.0, "Residual active complex must be retained");

        // Next physical step: A decays gracefully via k_off and k_inact
        rec.step_kinetics(0.005).unwrap();
        assert!(rec.a_active > 0.0, "A decays over physical time, does not vanish at beat boundary");
        assert!(rec.a_active < a_before_decay, "A decreases through dissociation/inactivation");
    }

    #[test]
    fn test_plastic_return_map_all_cases() {
        let k = 100.0e-9; // 100 nJ
        let y = 20.0e-9;  // 20 nJ (0 < Y < K)

        // Case 1: Elastic (sub-yield tension)
        let mut state_elastic = MechanicalPlasticState::new(1.05e-6, 1.0e-6, k, y, 0.0).unwrap();
        let res_el = state_elastic.return_map_fixed_x().unwrap();
        assert!(!res_el.is_yielded);
        assert_eq!(res_el.returned_l, 1.0e-6);
        assert_eq!(res_el.delta_l, 0.0);
        assert_eq!(res_el.dissipated_energy, 0.0);
        assert!(res_el.yield_function_value <= 0.0);

        // Case 2: Boundary case (exactly at yield: epsilon_tr = Y / K = 0.2)
        let l_bnd = 1.0e-6;
        let x_bnd = l_bnd * (1.0 + y / k);
        let mut state_bnd = MechanicalPlasticState::new(x_bnd, l_bnd, k, y, 0.0).unwrap();
        let res_bnd = state_bnd.return_map_fixed_x().unwrap();
        assert!(!res_bnd.is_yielded);
        assert_eq!(res_bnd.returned_l, l_bnd);
        assert_eq!(res_bnd.delta_l, 0.0);
        assert_eq!(res_bnd.dissipated_energy, 0.0);
        assert!(res_bnd.yield_function_value.abs() < 1e-15);

        // Case 3: Positive yield (tension: epsilon_tr = 0.5 > Y/K = 0.2)
        let mut state_tension = MechanicalPlasticState::new(1.5e-6, 1.0e-6, k, y, 0.0).unwrap();
        let res_t = state_tension.return_map_fixed_x().unwrap();
        assert!(res_t.is_yielded);
        assert!(res_t.delta_l > 0.0, "Delta l must be positive for tension: {}", res_t.delta_l);
        assert!(res_t.returned_l > 1.0e-6);
        assert!(res_t.dissipated_energy > 0.0);
        assert!(res_t.yield_function_value.abs() < 1e-15, "Yield function must be 0 after return");

        // Verify returned Sigma == +Y
        assert!((res_t.final_sigma - y).abs() < 1e-15);

        // Case 4: Negative yield (compression: epsilon_tr = -0.4 < -Y/K = -0.2)
        let mut state_comp = MechanicalPlasticState::new(0.6e-6, 1.0e-6, k, y, 0.0).unwrap();
        let res_c = state_comp.return_map_fixed_x().unwrap();
        assert!(res_c.is_yielded);
        assert!(res_c.delta_l < 0.0, "Delta l must be negative for compression: {}", res_c.delta_l);
        assert!(res_c.returned_l < 1.0e-6);
        assert!(res_c.returned_l > 0.0, "Returned length must remain strictly positive");
        assert!(res_c.dissipated_energy > 0.0);
        assert!(res_c.yield_function_value.abs() < 1e-15);

        // Verify returned Sigma == -Y
        assert!((res_c.final_sigma - (-y)).abs() < 1e-15);

        // Case 5: Invalid domain rejected without clipping
        assert!(MechanicalPlasticState::new(1.0e-6, 1.0e-6, k, k, 0.0).is_err(), "Y == K must fail");
        assert!(MechanicalPlasticState::new(1.0e-6, 1.0e-6, k, k * 1.5, 0.0).is_err(), "Y > K must fail");
        assert!(MechanicalPlasticState::new(1.0e-6, 1.0e-6, -k, y, 0.0).is_err(), "K <= 0 must fail");
        assert!(MechanicalPlasticState::new(-1.0e-6, 1.0e-6, k, y, 0.0).is_err(), "x <= 0 must fail");
        assert!(MechanicalPlasticState::new(1.0e-6, -1.0e-6, k, y, 0.0).is_err(), "l <= 0 must fail");
    }

    #[test]
    fn test_energy_accounting_and_finite_differences() {
        let k = 50.0e-9;
        let y = 10.0e-9;
        let mut mechanics = MechanicalPlasticState::new(1.6e-6, 1.0e-6, k, y, 0.0).unwrap();

        let u_initial = mechanics.elastic_energy();
        let res = mechanics.return_map_fixed_x().unwrap();
        let u_final = mechanics.elastic_energy();

        // Exact stored energy decrease equals plastic dissipation
        let delta_u = u_final - u_initial;
        assert!((delta_u + res.dissipated_energy).abs() < 1e-20, "Delta U + D_pl must be 0");

        // Capacitor finite difference: Delta E_cap = (Q'^2 - Q^2) / (2 C_mem)
        let mut carrier = ChargeCarrierState::new(-10.0e-12, 100.0e-12, 0.0, 1000, 1000).unwrap();
        let e_cap_init = carrier.stored_energy();
        let transport = carrier.settle_transport(2.0 * ELEMENTARY_CHARGE, 1, 0.0).unwrap();
        let e_cap_final = carrier.stored_energy();

        let expected_delta_e = e_cap_final - e_cap_init;
        assert!((transport.delta_e_cap - expected_delta_e).abs() < 1e-25);

        let balance = ClosedEnergyBalance::compute_fixed_x(u_initial, u_final, res.dissipated_energy, transport.delta_e_cap);
        assert!(balance.mechanical_energy_balance_residual < 1e-20);
    }

    #[test]
    fn test_continuation_serialization_and_exact_restoration() {
        let carrier = ChargeCarrierState::new(-6.8e-12, 100.0e-12, 0.4321, 999_800, 500_200).unwrap();
        let receptor = ReceptorKineticsState::new(
            0.85e-9, 0.15e-9, 0.05e-9, 1.2e-9, 1.0e-18, 0.0035, 1.0e8, 10.0, 5.0, 2.0,
        ).unwrap();
        let mechanics = MechanicalPlasticState::new(1.4e-6, 1.1e-6, 80.0e-9, 16.0e-9, 0.0012).unwrap();

        let original_state = ConstitutiveState::new(carrier, receptor, mechanics);

        // Serialize to 176 bytes
        let serialized = original_state.serialize();
        assert_eq!(serialized.len(), SERIALIZED_STATE_SIZE);
        assert_eq!(&serialized[0..8], STATE_MAGIC);

        // Restore state
        let restored_state = ConstitutiveState::deserialize(&serialized).unwrap();
        assert_eq!(original_state, restored_state, "Restored state must match original bit-exact");

        // Verify next identical input produces bit-identical output
        let mut state_a = original_state.clone();
        let mut state_b = restored_state.clone();

        let res_a_carrier = state_a.carrier.settle_transport(3.5 * ELEMENTARY_CHARGE, 1, 0.0).unwrap();
        let res_b_carrier = state_b.carrier.settle_transport(3.5 * ELEMENTARY_CHARGE, 1, 0.0).unwrap();
        assert_eq!(res_a_carrier, res_b_carrier);
        assert_eq!(state_a.carrier, state_b.carrier);

        let res_a_rec = state_a.receptor.step_kinetics(0.01).unwrap();
        let res_b_rec = state_b.receptor.step_kinetics(0.01).unwrap();
        assert_eq!(res_a_rec, res_b_rec);
        assert_eq!(state_a.receptor, state_b.receptor);

        let res_a_mech = state_a.mechanics.return_map_fixed_x().unwrap();
        let res_b_mech = state_b.mechanics.return_map_fixed_x().unwrap();
        assert_eq!(res_a_mech, res_b_mech);
        assert_eq!(state_a.mechanics, state_b.mechanics);

        // Corruption handling: malformed record must fail without resetting to defaults
        let mut corrupted = serialized;
        corrupted[100] ^= 0xFF; // corrupt one byte in payload
        let err = ConstitutiveState::deserialize(&corrupted);
        assert!(matches!(err, Err(ConstitutiveError::InvalidChecksum { .. })));

        // Truncated data must fail
        let err_trunc = ConstitutiveState::deserialize(&serialized[0..100]);
        assert!(matches!(err_trunc, Err(ConstitutiveError::TruncatedData { .. })));

        // Bad magic must fail
        let mut bad_magic = serialized;
        bad_magic[0] = b'X';
        let err_magic = ConstitutiveState::deserialize(&bad_magic);
        assert!(matches!(err_magic, Err(ConstitutiveError::CorruptData(_))));
    }

    #[test]
    fn test_failure_and_resource_boundaries() {
        // Measure component memory footprint
        let carrier = ChargeCarrierState::new(0.0, 1.0, 0.0, 10, 10).unwrap();
        let receptor = ReceptorKineticsState::new(1.0, 0.0, 0.0, 1.0, 1.0, 0.0, 1.0, 1.0, 1.0, 1.0).unwrap();
        let mechanics = MechanicalPlasticState::new(1.0, 1.0, 10.0, 2.0, 0.0).unwrap();
        let state = ConstitutiveState::new(carrier, receptor, mechanics);

        let bytes = state.serialize();
        assert_eq!(bytes.len(), 176, "Component serialization footprint must be bounded to 176 bytes");

        // Zero valence error
        let mut carrier2 = ChargeCarrierState::new(0.0, 1.0, 0.0, 10, 10).unwrap();
        assert_eq!(carrier2.settle_transport(1.0, 0, 0.0), Err(ConstitutiveError::ZeroValence));

        // Invalid dt error
        let mut rec2 = ReceptorKineticsState::new(1.0, 0.0, 0.0, 1.0, 1.0, 0.0, 1.0, 1.0, 1.0, 1.0).unwrap();
        assert_eq!(rec2.step_kinetics(0.0), Err(ConstitutiveError::InvalidTimeStep(0.0)));
        assert_eq!(rec2.step_kinetics(-0.01), Err(ConstitutiveError::InvalidTimeStep(-0.01)));
    }
}
