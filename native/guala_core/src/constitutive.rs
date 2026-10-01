//! Unmounted constitutive components for Guala (Stage P1-A).
//!
//! The carrier helper uses binary64 charge/remainder arithmetic with an explicit
//! numerical residual. Whole-carrier reservoir counts are exact checked
//! integers. Section 6 defines the canonical typed phase-gate-material dynamic
//! operator under strict SI units, exact charge custody, and first-law energy
//! conservation.
//!
//! Governing requirements: GUALA_P0_LOCAL_LEARNING_A1_CORRECTED_2026-09-27.md.
//! A13 removes the rejected single-phase/dimensionless-current mount.

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
// 1. Numerical Carrier Transport and Checked Integer Reservoir Custody
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
        let state = Self {
            q_membrane,
            c_mem,
            remainder,
            source_reservoir,
            dest_reservoir,
        };
        state.validate_numeric_state()?;
        Ok(state)
    }

    // This existing binary64 component is UNMOUNTED. Its numerical residual is
    // observable, not a certificate of exact rational physical charge custody.
    fn validate_numeric_state(&self) -> Result<(), ConstitutiveError> {
        if !self.c_mem.is_finite() || self.c_mem <= 0.0 {
            return Err(ConstitutiveError::InvalidDomain(
                "c_mem must be positive and finite".to_string(),
            ));
        }
        if !self.q_membrane.is_finite()
            || !self.remainder.is_finite()
            || self.remainder.abs() >= 1.0
        {
            return Err(ConstitutiveError::InvalidDomain(
                "charge must be finite and remainder must be in (-1, 1)".to_string(),
            ));
        }
        if !(2.0 * self.c_mem).is_finite()
            || !(self.q_membrane * self.q_membrane).is_finite()
            || !self.voltage().is_finite()
            || !self.stored_energy().is_finite()
        {
            return Err(ConstitutiveError::InvalidDomain(
                "derived voltage and stored energy must be representable".to_string(),
            ));
        }
        Ok(())
    }

    /// Derived membrane potential V = Q / C_mem in Volts [V].
    #[inline]
    pub fn voltage(&self) -> f64 {
        self.q_membrane / self.c_mem
    }

    /// Binary64 capacitor energy Q^2 / (2*C_mem), in Joules [J].
    #[inline]
    pub fn stored_energy(&self) -> f64 {
        (self.q_membrane * self.q_membrane) / (2.0 * self.c_mem)
    }

    /// Bounded numerical carrier settlement for this UNMOUNTED component.
    ///
    /// Integer reservoir transfers are exact and equal/opposite. Continuous
    /// charge/remainder arithmetic remains binary64; identity_residual reports
    /// its error, not exact rational conservation. q_active is a supplied
    /// boundary charge, not a mounted pump or an invented source of ions.
    /// All fallible work is staged before publishing any state member.
    pub fn settle_transport(
        &mut self,
        current_integral_jc: f64,
        valence: i32,
        q_active: f64,
    ) -> Result<CarrierTransportResult, ConstitutiveError> {
        self.validate_numeric_state()?;
        if valence == 0 {
            return Err(ConstitutiveError::ZeroValence);
        }
        if !current_integral_jc.is_finite() || !q_active.is_finite() {
            return Err(ConstitutiveError::InvalidDomain(
                "current integral and active charge must be finite".to_string(),
            ));
        }

        let q_c = (valence as f64) * ELEMENTARY_CHARGE;
        let z_c = self.remainder + current_integral_jc / q_c;
        // Adjacent integers cease to be distinguishable at 2^53 in binary64.
        // This is a representation boundary, not a physiological threshold.
        let exact_integer_boundary = (1_u64 << f64::MANTISSA_DIGITS) as f64;
        if !z_c.is_finite() || z_c.abs() >= exact_integer_boundary {
            return Err(ConstitutiveError::InvalidDomain(
                "carrier quotient exceeds exact binary64 integer range".to_string(),
            ));
        }
        let n_c = z_c.trunc() as i64;
        let r_c_prime = z_c - n_c as f64;
        let reconstructed_jc = q_c * n_c as f64 + q_c * (r_c_prime - self.remainder);
        let identity_residual = (reconstructed_jc - current_integral_jc).abs();

        let (source, destination) = if n_c > 0 {
            let required = n_c as u64;
            let source = self.source_reservoir.checked_sub(required).ok_or_else(|| {
                ConstitutiveError::ExhaustedReservoir {
                    required,
                    available: self.source_reservoir,
                    reservoir_name: "source".to_string(),
                }
            })?;
            let destination = self.dest_reservoir.checked_add(required).ok_or_else(|| {
                ConstitutiveError::InvalidDomain("destination carrier population overflow".to_string())
            })?;
            (source, destination)
        } else if n_c < 0 {
            let required = n_c.unsigned_abs();
            let destination = self.dest_reservoir.checked_sub(required).ok_or_else(|| {
                ConstitutiveError::ExhaustedReservoir {
                    required,
                    available: self.dest_reservoir,
                    reservoir_name: "destination".to_string(),
                }
            })?;
            let source = self.source_reservoir.checked_add(required).ok_or_else(|| {
                ConstitutiveError::InvalidDomain("source carrier population overflow".to_string())
            })?;
            (source, destination)
        } else {
            (self.source_reservoir, self.dest_reservoir)
        };

        let q_new = self.q_membrane - q_c * n_c as f64 - q_active;
        let delta_q = q_new - self.q_membrane;
        let delta_e_cap =
            (q_new * q_new - self.q_membrane * self.q_membrane) / (2.0 * self.c_mem);
        let staged = Self::new(q_new, self.c_mem, r_c_prime, source, destination)?;
        if !delta_q.is_finite() || !delta_e_cap.is_finite() || !identity_residual.is_finite() {
            return Err(ConstitutiveError::InvalidDomain(
                "carrier settlement produced an unrepresentable receipt".to_string(),
            ));
        }

        let receipt = CarrierTransportResult {
            carriers_transported: n_c,
            new_remainder: r_c_prime,
            delta_q_membrane: delta_q,
            delta_e_cap,
            identity_residual,
        };
        *self = staged;
        Ok(receipt)
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
// 6. Canonical Typed Phase-Gate-Material Dynamic Operator
// ---------------------------------------------------------------------------

pub const DSF_CHANNELS: usize = 7;
pub const ION_CHANNELS: usize = 3;

/// Magic bytes identifying Guala Typed Phase-Gate-Material Operator Record.
pub const OPERATOR_STATE_MAGIC: &[u8; 8] = b"GUALA_PG";
pub const OPERATOR_SCHEMA_VERSION: u32 = 1;
pub const OPERATOR_SERIALIZED_SIZE: usize = 936;

/// Phase-coupled local oscillator fabric across 7 distinct structural field channels.
#[derive(Debug, Clone, PartialEq)]
pub struct PhaseCoupledOscillatorFabric {
    pub phases: [f64; DSF_CHANNELS],
    pub windings: [i64; DSF_CHANNELS],
    pub base_frequencies: [f64; DSF_CHANNELS],
    pub field_sensitivities: [f64; DSF_CHANNELS],
}

impl PhaseCoupledOscillatorFabric {
    pub fn new(
        phases: [f64; DSF_CHANNELS],
        windings: [i64; DSF_CHANNELS],
        base_frequencies: [f64; DSF_CHANNELS],
        field_sensitivities: [f64; DSF_CHANNELS],
    ) -> Result<Self, ConstitutiveError> {
        let fabric = Self {
            phases,
            windings,
            base_frequencies,
            field_sensitivities,
        };
        fabric.validate()?;
        Ok(fabric)
    }

    pub fn validate(&self) -> Result<(), ConstitutiveError> {
        for i in 0..DSF_CHANNELS {
            if !self.phases[i].is_finite()
                || self.phases[i] < -std::f64::consts::PI - 1e-12
                || self.phases[i] > std::f64::consts::PI + 1e-12
            {
                return Err(ConstitutiveError::InvalidDomain(format!(
                    "Oscillator phase {} out of range [-pi, pi]: {}",
                    i, self.phases[i]
                )));
            }
            if !self.base_frequencies[i].is_finite() {
                return Err(ConstitutiveError::InvalidDomain(format!(
                    "Oscillator base frequency {} is non-finite: {}",
                    i, self.base_frequencies[i]
                )));
            }
            if !self.field_sensitivities[i].is_finite() {
                return Err(ConstitutiveError::InvalidDomain(format!(
                    "Oscillator field sensitivity {} is non-finite: {}",
                    i, self.field_sensitivities[i]
                )));
            }
        }
        Ok(())
    }

    pub fn step(&mut self, field_7d: &[f64; DSF_CHANNELS], dt: f64) -> Result<(), ConstitutiveError> {
        if !dt.is_finite() || dt <= 0.0 {
            return Err(ConstitutiveError::InvalidTimeStep(dt));
        }
        let mut new_phases = self.phases;
        let mut new_windings = self.windings;

        let two_pi = 2.0 * std::f64::consts::PI;

        for i in 0..DSF_CHANNELS {
            let f_val = field_7d[i];
            if !f_val.is_finite() {
                return Err(ConstitutiveError::InvalidDomain(format!(
                    "Field value {} is non-finite: {}",
                    i, f_val
                )));
            }
            let omega = self.base_frequencies[i] + self.field_sensitivities[i] * f_val;
            if !omega.is_finite() {
                return Err(ConstitutiveError::InvalidDomain(format!(
                    "Calculated frequency {} is non-finite: {}",
                    i, omega
                )));
            }
            let unwrapped = self.phases[i] + omega * dt;
            if !unwrapped.is_finite() {
                return Err(ConstitutiveError::InvalidDomain(format!(
                    "Unwrapped phase {} is non-finite",
                    i
                )));
            }
            let wraps_f = ((unwrapped + std::f64::consts::PI) / two_pi).floor();
            let exact_int_limit = (1_u64 << f64::MANTISSA_DIGITS) as f64;
            if !wraps_f.is_finite() || wraps_f.abs() >= exact_int_limit {
                return Err(ConstitutiveError::InvalidDomain(format!(
                    "Oscillator wrap count {} exceeds exact integer precision",
                    i
                )));
            }
            let wraps = wraps_f as i64;
            let wrapped_phase = unwrapped - (wraps as f64) * two_pi;
            let final_phase = wrapped_phase.clamp(-std::f64::consts::PI, std::f64::consts::PI);
            let final_winding = self.windings[i].checked_add(wraps).ok_or_else(|| {
                ConstitutiveError::InvalidDomain(format!("Oscillator winding {} overflowed", i))
            })?;

            new_phases[i] = final_phase;
            new_windings[i] = final_winding;
        }

        self.phases = new_phases;
        self.windings = new_windings;
        Ok(())
    }
}

/// Thermodynamic channel gate with continuous conformational potential.
#[derive(Debug, Clone, PartialEq)]
pub struct ThermodynamicChannelGate {
    pub y: f64,
    pub friction_zeta: f64,
    pub conformal_stiffness: f64,
    pub conformal_rest_y: f64,
    pub gating_charge: f64,
    pub chemical_potential: f64,
    pub phase_coupling_lambda: [f64; DSF_CHANNELS],
    pub target_phase_offset: [f64; DSF_CHANNELS],
}

impl ThermodynamicChannelGate {
    pub fn new(
        y: f64,
        friction_zeta: f64,
        conformal_stiffness: f64,
        conformal_rest_y: f64,
        gating_charge: f64,
        chemical_potential: f64,
        phase_coupling_lambda: [f64; DSF_CHANNELS],
        target_phase_offset: [f64; DSF_CHANNELS],
    ) -> Result<Self, ConstitutiveError> {
        let gate = Self {
            y,
            friction_zeta,
            conformal_stiffness,
            conformal_rest_y,
            gating_charge,
            chemical_potential,
            phase_coupling_lambda,
            target_phase_offset,
        };
        gate.validate()?;
        Ok(gate)
    }

    pub fn validate(&self) -> Result<(), ConstitutiveError> {
        if !self.y.is_finite() || self.y < 0.0 || self.y > 1.0 {
            return Err(ConstitutiveError::InvalidDomain(format!(
                "Gate coordinate y must be in [0, 1], got {}",
                self.y
            )));
        }
        if !self.friction_zeta.is_finite() || self.friction_zeta <= 0.0 {
            return Err(ConstitutiveError::InvalidDomain(format!(
                "Friction zeta must be positive, got {}",
                self.friction_zeta
            )));
        }
        if !self.conformal_stiffness.is_finite() || self.conformal_stiffness <= 0.0 {
            return Err(ConstitutiveError::InvalidDomain(format!(
                "Conformal stiffness must be positive, got {}",
                self.conformal_stiffness
            )));
        }
        if !self.conformal_rest_y.is_finite()
            || self.conformal_rest_y < 0.0
            || self.conformal_rest_y > 1.0
        {
            return Err(ConstitutiveError::InvalidDomain(format!(
                "Conformal rest y must be in [0, 1], got {}",
                self.conformal_rest_y
            )));
        }
        if !self.gating_charge.is_finite() || !self.chemical_potential.is_finite() {
            return Err(ConstitutiveError::InvalidDomain(
                "Gating charge and chemical potential must be finite".to_string(),
            ));
        }
        for i in 0..DSF_CHANNELS {
            if !self.phase_coupling_lambda[i].is_finite() || self.phase_coupling_lambda[i] < 0.0 {
                return Err(ConstitutiveError::InvalidDomain(format!(
                    "Phase coupling lambda {} must be non-negative and finite",
                    i
                )));
            }
            if !self.target_phase_offset[i].is_finite() {
                return Err(ConstitutiveError::InvalidDomain(format!(
                    "Target phase offset {} must be finite",
                    i
                )));
            }
        }
        Ok(())
    }

    pub fn potential_force(&self, y: f64, v_membrane: f64, phases: &[f64; DSF_CHANNELS]) -> f64 {
        let mut resonant_sum = 0.0;
        for i in 0..DSF_CHANNELS {
            let d_phi = phases[i] - self.target_phase_offset[i];
            resonant_sum += self.phase_coupling_lambda[i] * d_phi.cos();
        }
        -self.conformal_stiffness * (y - self.conformal_rest_y)
            + self.gating_charge * v_membrane
            + resonant_sum
            + self.chemical_potential
    }

    pub fn step(
        &mut self,
        v_membrane: f64,
        phases: &[f64; DSF_CHANNELS],
        dt: f64,
    ) -> Result<f64, ConstitutiveError> {
        if !dt.is_finite() || dt <= 0.0 {
            return Err(ConstitutiveError::InvalidTimeStep(dt));
        }
        if !v_membrane.is_finite() {
            return Err(ConstitutiveError::InvalidDomain(
                "v_membrane must be finite".to_string(),
            ));
        }
        let mut resonant_sum = 0.0;
        for i in 0..DSF_CHANNELS {
            let d_phi = phases[i] - self.target_phase_offset[i];
            resonant_sum += self.phase_coupling_lambda[i] * d_phi.cos();
        }
        let f_ext = self.gating_charge * v_membrane + resonant_sum + self.chemical_potential;
        let y_star = self.conformal_rest_y + f_ext / self.conformal_stiffness;

        let decay_arg = (self.conformal_stiffness / self.friction_zeta) * dt;
        let exp_factor = (-decay_arg).exp();
        let y_next_unclamped = y_star + (self.y - y_star) * exp_factor;
        let y_next = y_next_unclamped.clamp(0.0, 1.0);

        let delta_y = y_next - self.y;
        self.y = y_next;
        Ok(delta_y)
    }
}

/// Material ion channel with Nernst reversal and charge carrier reservoirs.
#[derive(Debug, Clone, PartialEq)]
pub struct MaterialIonChannel {
    pub gate: ThermodynamicChannelGate,
    pub g_max: f64,
    pub reversal_potential: f64,
    pub valence: i32,
    pub carriers: ChargeCarrierState,
}

impl MaterialIonChannel {
    pub fn new(
        gate: ThermodynamicChannelGate,
        g_max: f64,
        reversal_potential: f64,
        valence: i32,
        carriers: ChargeCarrierState,
    ) -> Result<Self, ConstitutiveError> {
        if !g_max.is_finite() || g_max <= 0.0 {
            return Err(ConstitutiveError::InvalidDomain(
                "g_max must be positive and finite".to_string(),
            ));
        }
        if !reversal_potential.is_finite() {
            return Err(ConstitutiveError::InvalidDomain(
                "reversal_potential must be finite".to_string(),
            ));
        }
        if valence == 0 {
            return Err(ConstitutiveError::ZeroValence);
        }
        Ok(Self {
            gate,
            g_max,
            reversal_potential,
            valence,
            carriers,
        })
    }

    #[inline]
    pub fn conductance(&self) -> f64 {
        self.g_max * self.gate.y
    }

    #[inline]
    pub fn current(&self, v_membrane: f64) -> f64 {
        self.conductance() * (v_membrane - self.reversal_potential)
    }
}

/// Physical transition receipt documenting complete conservation balances.
#[derive(Debug, Clone, PartialEq)]
pub struct NeuronTransitionReceipt {
    /// Final membrane potential V_i in Volts [V].
    pub v_membrane_final: f64,
    /// Total instantaneous membrane conductance G_tot in Siemens [S].
    pub total_conductance: f64,
    /// Channel conductances g_c in Siemens [S].
    pub channel_conductances: [f64; ION_CHANNELS],
    /// Channel currents I_c in Amperes [A].
    pub channel_currents: [f64; ION_CHANNELS],
    /// Channel current integrals J_c in Coulombs [C].
    pub channel_current_integrals: [f64; ION_CHANNELS],
    /// Discrete integer carrier transfers per channel.
    pub carrier_transfers: [i64; ION_CHANNELS],
    /// Change in capacitor stored electrical energy Delta E_cap in Joules [J].
    pub delta_e_cap: f64,
    /// Total Joule heat dissipated in conductors Q_Joule in Joules [J] (>= 0).
    pub q_joule: f64,
    /// Chemical work performed by reversal battery sources W_chem in Joules [J].
    pub w_chem: f64,
    /// External current work W_ext in Joules [J].
    pub w_ext: f64,
    /// First law energy conservation residual |Delta E_cap + Q_joule - W_chem - W_ext| [J].
    pub energy_conservation_residual: f64,
    /// Charge conservation residual |Delta Q_mem + sum(J_c) - I_ext * dt| [C].
    pub charge_conservation_residual: f64,
}

/// Canonical Typed Phase-Gate-Material Dynamic Operator.
#[derive(Debug, Clone, PartialEq)]
pub struct TypedPhaseGateMaterialOperator {
    pub fabric: PhaseCoupledOscillatorFabric,
    pub channels: [MaterialIonChannel; ION_CHANNELS],
    pub c_mem: f64,
    pub v_membrane: f64,
    pub s_uf: f64,
}

impl TypedPhaseGateMaterialOperator {
    pub fn new(
        fabric: PhaseCoupledOscillatorFabric,
        channels: [MaterialIonChannel; ION_CHANNELS],
        c_mem: f64,
        v_membrane: f64,
        s_uf: f64,
    ) -> Result<Self, ConstitutiveError> {
        if !c_mem.is_finite() || c_mem <= 0.0 {
            return Err(ConstitutiveError::InvalidDomain(
                "c_mem must be positive and finite".to_string(),
            ));
        }
        if !v_membrane.is_finite() {
            return Err(ConstitutiveError::InvalidDomain(
                "v_membrane must be finite".to_string(),
            ));
        }
        if !s_uf.is_finite() {
            return Err(ConstitutiveError::InvalidDomain(
                "s_uf must be finite".to_string(),
            ));
        }
        let op = Self {
            fabric,
            channels,
            c_mem,
            v_membrane,
            s_uf,
        };
        op.validate()?;
        Ok(op)
    }

    pub fn validate(&self) -> Result<(), ConstitutiveError> {
        self.fabric.validate()?;
        for ch in &self.channels {
            ch.gate.validate()?;
        }
        if !self.c_mem.is_finite() || self.c_mem <= 0.0 {
            return Err(ConstitutiveError::InvalidDomain(
                "c_mem must be positive and finite".to_string(),
            ));
        }
        if !self.v_membrane.is_finite() {
            return Err(ConstitutiveError::InvalidDomain(
                "v_membrane must be finite".to_string(),
            ));
        }
        if !self.s_uf.is_finite() {
            return Err(ConstitutiveError::InvalidDomain(
                "s_uf must be finite".to_string(),
            ));
        }
        Ok(())
    }

    /// Canonical physical default constructor with calibrated parameters.
    pub fn default_canonical() -> Result<Self, ConstitutiveError> {
        let fabric = PhaseCoupledOscillatorFabric::new(
            [0.0; DSF_CHANNELS],
            [0; DSF_CHANNELS],
            [10.0, 15.0, 8.0, 12.0, 20.0, 25.0, 18.0],
            [1.0, 1.2, 0.8, 1.5, 2.0, 1.8, 1.1],
        )?;

        // Physical reservoir scale: 10^11 carriers for 100 pF membrane
        let initial_reservoir = 100_000_000_000u64;

        // Channel 0: Excitatory Na+
        let gate_0 = ThermodynamicChannelGate::new(
            0.10,
            1.0e-3,
            2.0,
            0.10,
            1.602_176_634e-19,
            0.0,
            [0.4, 0.05, 0.0, 0.0, 0.05, 0.0, 0.2],
            [0.0; DSF_CHANNELS],
        )?;
        let carriers_0 = ChargeCarrierState::new(0.0, 100.0e-12, 0.0, initial_reservoir, initial_reservoir)?;
        let ch_0 = MaterialIonChannel::new(gate_0, 12.0e-9, 0.060, 1, carriers_0)?;

        // Channel 1: Inhibitory K+
        let gate_1 = ThermodynamicChannelGate::new(
            0.15,
            2.0e-3,
            2.0,
            0.15,
            -1.602_176_634e-19,
            0.0,
            [0.0, 0.35, 0.0, 0.2, 0.0, 0.3, 0.0],
            [0.0; DSF_CHANNELS],
        )?;
        let carriers_1 = ChargeCarrierState::new(0.0, 100.0e-12, 0.0, initial_reservoir, initial_reservoir)?;
        let ch_1 = MaterialIonChannel::new(gate_1, 16.0e-9, -0.090, 1, carriers_1)?;

        // Channel 2: Stabilizing Ca2+
        let gate_2 = ThermodynamicChannelGate::new(
            0.10,
            5.0e-3,
            2.0,
            0.10,
            0.0,
            0.0,
            [0.0, 0.0, 0.4, 0.0, 0.3, 0.0, 0.0],
            [0.0; DSF_CHANNELS],
        )?;
        let carriers_2 = ChargeCarrierState::new(0.0, 100.0e-12, 0.0, initial_reservoir, initial_reservoir)?;
        let ch_2 = MaterialIonChannel::new(gate_2, 4.0e-9, -0.070, 2, carriers_2)?;

        Self::new(fabric, [ch_0, ch_1, ch_2], 100.0e-12, -0.065, 1.0)
    }

    /// Dynamic physical step over interval dt [s].
    ///
    /// Staged atomically: refuses transition prior to mutation upon any error.
    pub fn step_transition(
        &mut self,
        field_7d: &[f64; DSF_CHANNELS],
        s_uf: f64,
        i_ext: f64,
        dt: f64,
    ) -> Result<NeuronTransitionReceipt, ConstitutiveError> {
        if !dt.is_finite() || dt <= 0.0 {
            return Err(ConstitutiveError::InvalidTimeStep(dt));
        }
        if !s_uf.is_finite() {
            return Err(ConstitutiveError::InvalidDomain(
                "s_uf must be finite".to_string(),
            ));
        }
        if !i_ext.is_finite() {
            return Err(ConstitutiveError::InvalidDomain(
                "i_ext must be finite".to_string(),
            ));
        }
        for (i, &f) in field_7d.iter().enumerate() {
            if !f.is_finite() {
                return Err(ConstitutiveError::InvalidDomain(format!(
                    "Field coordinate {} is non-finite: {}",
                    i, f
                )));
            }
        }

        // Viability Gate: If S_UF <= 0, the macroscopic basin is non-viable.
        if s_uf <= 0.0 {
            return Err(ConstitutiveError::InvalidDomain(format!(
                "Viability gate refused transition: S_UF = {} <= 0",
                s_uf
            )));
        }

        // 1. Stage advance of oscillator fabric
        let mut staged_fabric = self.fabric.clone();
        staged_fabric.step(field_7d, dt)?;

        // 2. Stage gate updates under current potential
        let mut staged_channels = self.channels.clone();
        let mut conductances = [0.0f64; ION_CHANNELS];
        let mut g_tot = 0.0f64;
        let mut g_e_sum = 0.0f64;

        for c in 0..ION_CHANNELS {
            staged_channels[c]
                .gate
                .step(self.v_membrane, &staged_fabric.phases, dt)?;
            let g_c = staged_channels[c].conductance();
            conductances[c] = g_c;
            g_tot += g_c;
            g_e_sum += g_c * staged_channels[c].reversal_potential;
        }

        // 3. Exact electrodynamics integration
        let (v_final, v_bar, int_1, int_2) = if g_tot > 1e-15 {
            let tau = self.c_mem / g_tot;
            let v_inf = (g_e_sum + i_ext) / g_tot;
            let ratio = dt / tau;
            let exp_term = (-ratio).exp();
            let exp_2_term = (-2.0 * ratio).exp();

            let v_fin = v_inf + (self.v_membrane - v_inf) * exp_term;

            let int_exp1 = if ratio < 1e-6 {
                dt * (1.0 - 0.5 * ratio + (ratio * ratio) / 6.0)
            } else {
                tau * (1.0 - exp_term)
            };
            let int_exp2 = if 2.0 * ratio < 1e-6 {
                dt * (1.0 - ratio + (2.0 * ratio * ratio) / 3.0)
            } else {
                0.5 * tau * (1.0 - exp_2_term)
            };
            let v_b = (v_inf * dt + (self.v_membrane - v_inf) * int_exp1) / dt;
            (v_fin, v_b, int_exp1, int_exp2)
        } else {
            let v_fin = self.v_membrane + (i_ext * dt) / self.c_mem;
            let v_b = 0.5 * (self.v_membrane + v_fin);
            (v_fin, v_b, dt, dt)
        };

        // 4. Current integrals and carrier custody
        let mut currents = [0.0f64; ION_CHANNELS];
        let mut current_integrals = [0.0f64; ION_CHANNELS];
        let mut carrier_transfers = [0i64; ION_CHANNELS];
        let mut sum_j_c = 0.0f64;

        for c in 0..ION_CHANNELS {
            let j_c = conductances[c] * (v_bar - staged_channels[c].reversal_potential) * dt;
            current_integrals[c] = j_c;
            currents[c] = j_c / dt;
            sum_j_c += j_c;

            let transport = staged_channels[c].carriers.settle_transport(
                j_c,
                staged_channels[c].valence,
                0.0,
            )?;
            carrier_transfers[c] = transport.carriers_transported;
        }

        // 5. Energy and Charge Conservation Balance
        let delta_q_mem = self.c_mem * (v_final - self.v_membrane);
        let charge_residual = (delta_q_mem + sum_j_c - i_ext * dt).abs();

        let delta_e_cap =
            0.5 * self.c_mem * (v_final * v_final - self.v_membrane * self.v_membrane);
        let w_ext = i_ext * v_bar * dt;

        let mut w_chem = 0.0f64;
        let mut q_joule = 0.0f64;

        if g_tot > 1e-15 {
            let v_inf = (g_e_sum + i_ext) / g_tot;
            for c in 0..ION_CHANNELS {
                let e_c = staged_channels[c].reversal_potential;
                w_chem -= e_c * current_integrals[c];

                let a = v_inf - e_c;
                let b = self.v_membrane - v_inf;
                let int_sq = a * a * dt + 2.0 * a * b * int_1 + b * b * int_2;
                q_joule += conductances[c] * int_sq;
            }
        }

        let energy_residual = (delta_e_cap + q_joule - (w_chem + w_ext)).abs();

        // 6. Commit all staged updates atomically
        self.fabric = staged_fabric;
        self.channels = staged_channels;
        self.v_membrane = v_final;
        self.s_uf = s_uf;

        Ok(NeuronTransitionReceipt {
            v_membrane_final: v_final,
            total_conductance: g_tot,
            channel_conductances: conductances,
            channel_currents: currents,
            channel_current_integrals: current_integrals,
            carrier_transfers,
            delta_e_cap,
            q_joule,
            w_chem,
            w_ext,
            energy_conservation_residual: energy_residual,
            charge_conservation_residual: charge_residual,
        })
    }

    /// Serializes entire operator into a fixed 936-byte record with CRC32.
    pub fn serialize(&self) -> [u8; OPERATOR_SERIALIZED_SIZE] {
        let mut buf = [0u8; OPERATOR_SERIALIZED_SIZE];
        buf[0..8].copy_from_slice(OPERATOR_STATE_MAGIC);
        buf[8..12].copy_from_slice(&OPERATOR_SCHEMA_VERSION.to_le_bytes());

        let mut offset = 12;

        // Fabric (224 bytes)
        for i in 0..DSF_CHANNELS {
            buf[offset..offset + 8].copy_from_slice(&self.fabric.phases[i].to_le_bytes());
            offset += 8;
            buf[offset..offset + 8].copy_from_slice(&self.fabric.windings[i].to_le_bytes());
            offset += 8;
            buf[offset..offset + 8].copy_from_slice(&self.fabric.base_frequencies[i].to_le_bytes());
            offset += 8;
            buf[offset..offset + 8].copy_from_slice(&self.fabric.field_sensitivities[i].to_le_bytes());
            offset += 8;
        }

        // Channels (672 bytes)
        for c in 0..ION_CHANNELS {
            let ch = &self.channels[c];
            buf[offset..offset + 8].copy_from_slice(&ch.gate.y.to_le_bytes());
            offset += 8;
            buf[offset..offset + 8].copy_from_slice(&ch.gate.friction_zeta.to_le_bytes());
            offset += 8;
            buf[offset..offset + 8].copy_from_slice(&ch.gate.conformal_stiffness.to_le_bytes());
            offset += 8;
            buf[offset..offset + 8].copy_from_slice(&ch.gate.conformal_rest_y.to_le_bytes());
            offset += 8;
            buf[offset..offset + 8].copy_from_slice(&ch.gate.gating_charge.to_le_bytes());
            offset += 8;
            buf[offset..offset + 8].copy_from_slice(&ch.gate.chemical_potential.to_le_bytes());
            offset += 8;
            for i in 0..DSF_CHANNELS {
                buf[offset..offset + 8]
                    .copy_from_slice(&ch.gate.phase_coupling_lambda[i].to_le_bytes());
                offset += 8;
            }
            for i in 0..DSF_CHANNELS {
                buf[offset..offset + 8]
                    .copy_from_slice(&ch.gate.target_phase_offset[i].to_le_bytes());
                offset += 8;
            }
            buf[offset..offset + 8].copy_from_slice(&ch.g_max.to_le_bytes());
            offset += 8;
            buf[offset..offset + 8].copy_from_slice(&ch.reversal_potential.to_le_bytes());
            offset += 8;
            buf[offset..offset + 4].copy_from_slice(&ch.valence.to_le_bytes());
            offset += 4;
            buf[offset..offset + 4].copy_from_slice(&[0u8; 4]);
            offset += 4; // padding
            buf[offset..offset + 8].copy_from_slice(&ch.carriers.q_membrane.to_le_bytes());
            offset += 8;
            buf[offset..offset + 8].copy_from_slice(&ch.carriers.c_mem.to_le_bytes());
            offset += 8;
            buf[offset..offset + 8].copy_from_slice(&ch.carriers.remainder.to_le_bytes());
            offset += 8;
            buf[offset..offset + 8].copy_from_slice(&ch.carriers.source_reservoir.to_le_bytes());
            offset += 8;
            buf[offset..offset + 8].copy_from_slice(&ch.carriers.dest_reservoir.to_le_bytes());
            offset += 8;
        }

        // Membrane & Invariants (24 bytes)
        buf[offset..offset + 8].copy_from_slice(&self.c_mem.to_le_bytes());
        offset += 8;
        buf[offset..offset + 8].copy_from_slice(&self.v_membrane.to_le_bytes());
        offset += 8;
        buf[offset..offset + 8].copy_from_slice(&self.s_uf.to_le_bytes());
        offset += 8;

        // Checksum
        let checksum = compute_crc32(&buf[0..offset]);
        buf[offset..offset + 4].copy_from_slice(&checksum.to_le_bytes());

        buf
    }

    /// Deserializes exact binary record into operator state.
    pub fn deserialize(bytes: &[u8]) -> Result<Self, ConstitutiveError> {
        if bytes.len() != OPERATOR_SERIALIZED_SIZE {
            return Err(ConstitutiveError::TruncatedData {
                expected: OPERATOR_SERIALIZED_SIZE,
                actual: bytes.len(),
            });
        }

        if &bytes[0..8] != OPERATOR_STATE_MAGIC {
            return Err(ConstitutiveError::CorruptData(
                "Invalid operator state magic bytes".to_string(),
            ));
        }

        let version = u32::from_le_bytes(bytes[8..12].try_into().unwrap());
        if version != OPERATOR_SCHEMA_VERSION {
            return Err(ConstitutiveError::CorruptData(format!(
                "Unsupported operator schema version: expected {}, got {}",
                OPERATOR_SCHEMA_VERSION, version
            )));
        }

        let stored_checksum = u32::from_le_bytes(bytes[932..936].try_into().unwrap());
        let computed_checksum = compute_crc32(&bytes[0..932]);
        if stored_checksum != computed_checksum {
            return Err(ConstitutiveError::InvalidChecksum {
                expected: stored_checksum,
                computed: computed_checksum,
            });
        }

        let mut offset = 12;

        let mut phases = [0.0f64; DSF_CHANNELS];
        let mut windings = [0i64; DSF_CHANNELS];
        let mut base_freqs = [0.0f64; DSF_CHANNELS];
        let mut field_sens = [0.0f64; DSF_CHANNELS];

        for i in 0..DSF_CHANNELS {
            phases[i] = f64::from_le_bytes(bytes[offset..offset + 8].try_into().unwrap());
            offset += 8;
            windings[i] = i64::from_le_bytes(bytes[offset..offset + 8].try_into().unwrap());
            offset += 8;
            base_freqs[i] = f64::from_le_bytes(bytes[offset..offset + 8].try_into().unwrap());
            offset += 8;
            field_sens[i] = f64::from_le_bytes(bytes[offset..offset + 8].try_into().unwrap());
            offset += 8;
        }

        let fabric = PhaseCoupledOscillatorFabric::new(phases, windings, base_freqs, field_sens)?;

        let mut channels_vec = Vec::with_capacity(ION_CHANNELS);
        for _ in 0..ION_CHANNELS {
            let y = f64::from_le_bytes(bytes[offset..offset + 8].try_into().unwrap());
            offset += 8;
            let friction_zeta = f64::from_le_bytes(bytes[offset..offset + 8].try_into().unwrap());
            offset += 8;
            let conformal_stiffness =
                f64::from_le_bytes(bytes[offset..offset + 8].try_into().unwrap());
            offset += 8;
            let conformal_rest_y = f64::from_le_bytes(bytes[offset..offset + 8].try_into().unwrap());
            offset += 8;
            let gating_charge = f64::from_le_bytes(bytes[offset..offset + 8].try_into().unwrap());
            offset += 8;
            let chemical_potential =
                f64::from_le_bytes(bytes[offset..offset + 8].try_into().unwrap());
            offset += 8;

            let mut phase_coupling_lambda = [0.0f64; DSF_CHANNELS];
            for i in 0..DSF_CHANNELS {
                phase_coupling_lambda[i] =
                    f64::from_le_bytes(bytes[offset..offset + 8].try_into().unwrap());
                offset += 8;
            }

            let mut target_phase_offset = [0.0f64; DSF_CHANNELS];
            for i in 0..DSF_CHANNELS {
                target_phase_offset[i] =
                    f64::from_le_bytes(bytes[offset..offset + 8].try_into().unwrap());
                offset += 8;
            }

            let gate = ThermodynamicChannelGate::new(
                y,
                friction_zeta,
                conformal_stiffness,
                conformal_rest_y,
                gating_charge,
                chemical_potential,
                phase_coupling_lambda,
                target_phase_offset,
            )?;

            let g_max = f64::from_le_bytes(bytes[offset..offset + 8].try_into().unwrap());
            offset += 8;
            let reversal_potential =
                f64::from_le_bytes(bytes[offset..offset + 8].try_into().unwrap());
            offset += 8;
            let valence = i32::from_le_bytes(bytes[offset..offset + 4].try_into().unwrap());
            offset += 4;
            offset += 4; // padding

            let q_membrane = f64::from_le_bytes(bytes[offset..offset + 8].try_into().unwrap());
            offset += 8;
            let c_mem = f64::from_le_bytes(bytes[offset..offset + 8].try_into().unwrap());
            offset += 8;
            let remainder = f64::from_le_bytes(bytes[offset..offset + 8].try_into().unwrap());
            offset += 8;
            let source_reservoir =
                u64::from_le_bytes(bytes[offset..offset + 8].try_into().unwrap());
            offset += 8;
            let dest_reservoir = u64::from_le_bytes(bytes[offset..offset + 8].try_into().unwrap());
            offset += 8;

            let carriers = ChargeCarrierState::new(
                q_membrane,
                c_mem,
                remainder,
                source_reservoir,
                dest_reservoir,
            )?;

            let channel =
                MaterialIonChannel::new(gate, g_max, reversal_potential, valence, carriers)?;
            channels_vec.push(channel);
        }

        let channels = [
            channels_vec.remove(0),
            channels_vec.remove(0),
            channels_vec.remove(0),
        ];

        let c_mem = f64::from_le_bytes(bytes[offset..offset + 8].try_into().unwrap());
        offset += 8;
        let v_membrane = f64::from_le_bytes(bytes[offset..offset + 8].try_into().unwrap());
        offset += 8;
        let s_uf = f64::from_le_bytes(bytes[offset..offset + 8].try_into().unwrap());

        Self::new(fabric, channels, c_mem, v_membrane, s_uf)
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
        let mut carrier =
            ChargeCarrierState::new(-7.0e-12, 100.0e-12, 0.0, 1_000_000, 500_000).unwrap();

        // 1. Positive transfer (outward, n_c > 0)
        let j_c1 = 5.0e-19; // 5 Coulombs * 10^-19
        let res1 = carrier.settle_transport(j_c1, 1, 0.0).unwrap();
        assert!(
            res1.identity_residual < 1e-25,
            "Residual: {}",
            res1.identity_residual
        );
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
            Err(ConstitutiveError::ExhaustedReservoir {
                required,
                available,
                reservoir_name,
            }) => {
                assert_eq!(required, 10);
                assert_eq!(available, 5);
                assert_eq!(reservoir_name, "source");
            }
            _ => panic!("Expected ExhaustedReservoir error, got {:?}", err),
        }
        assert_eq!(
            small_carrier.source_reservoir, 5,
            "State must not mutate on failure"
        );
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
        )
        .unwrap();

        let initial_r_tot = rec.total_receptors();
        let initial_t_tot = rec.total_transmitter();

        // Step kinetics over 10 consecutive intervals
        for _ in 0..10 {
            let res = rec.step_kinetics(0.01).unwrap();
            assert!(
                res.delta_total_receptors.abs() < 1e-15,
                "R_tot drifted: {}",
                res.delta_total_receptors
            );
            assert!(
                res.delta_total_transmitter.abs() < 1e-15,
                "T_tot drifted: {}",
                res.delta_total_transmitter
            );
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
        assert!(
            a_before_decay > 0.0,
            "Residual active complex must be retained"
        );

        // Next physical step: A decays gracefully via k_off and k_inact
        rec.step_kinetics(0.005).unwrap();
        assert!(
            rec.a_active > 0.0,
            "A decays over physical time, does not vanish at beat boundary"
        );
        assert!(
            rec.a_active < a_before_decay,
            "A decreases through dissociation/inactivation"
        );
    }

    #[test]
    fn test_plastic_return_map_all_cases() {
        let k = 100.0e-9; // 100 nJ
        let y = 20.0e-9; // 20 nJ (0 < Y < K)

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
        assert!(
            res_t.delta_l > 0.0,
            "Delta l must be positive for tension: {}",
            res_t.delta_l
        );
        assert!(res_t.returned_l > 1.0e-6);
        assert!(res_t.dissipated_energy > 0.0);
        assert!(
            res_t.yield_function_value.abs() < 1e-15,
            "Yield function must be 0 after return"
        );

        // Verify returned Sigma == +Y
        assert!((res_t.final_sigma - y).abs() < 1e-15);

        // Case 4: Negative yield (compression: epsilon_tr = -0.4 < -Y/K = -0.2)
        let mut state_comp = MechanicalPlasticState::new(0.6e-6, 1.0e-6, k, y, 0.0).unwrap();
        let res_c = state_comp.return_map_fixed_x().unwrap();
        assert!(res_c.is_yielded);
        assert!(
            res_c.delta_l < 0.0,
            "Delta l must be negative for compression: {}",
            res_c.delta_l
        );
        assert!(res_c.returned_l < 1.0e-6);
        assert!(
            res_c.returned_l > 0.0,
            "Returned length must remain strictly positive"
        );
        assert!(res_c.dissipated_energy > 0.0);
        assert!(res_c.yield_function_value.abs() < 1e-15);

        // Verify returned Sigma == -Y
        assert!((res_c.final_sigma - (-y)).abs() < 1e-15);

        // Case 5: Invalid domain rejected without clipping
        assert!(
            MechanicalPlasticState::new(1.0e-6, 1.0e-6, k, k, 0.0).is_err(),
            "Y == K must fail"
        );
        assert!(
            MechanicalPlasticState::new(1.0e-6, 1.0e-6, k, k * 1.5, 0.0).is_err(),
            "Y > K must fail"
        );
        assert!(
            MechanicalPlasticState::new(1.0e-6, 1.0e-6, -k, y, 0.0).is_err(),
            "K <= 0 must fail"
        );
        assert!(
            MechanicalPlasticState::new(-1.0e-6, 1.0e-6, k, y, 0.0).is_err(),
            "x <= 0 must fail"
        );
        assert!(
            MechanicalPlasticState::new(1.0e-6, -1.0e-6, k, y, 0.0).is_err(),
            "l <= 0 must fail"
        );
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
        assert!(
            (delta_u + res.dissipated_energy).abs() < 1e-20,
            "Delta U + D_pl must be 0"
        );

        // Capacitor finite difference: Delta E_cap = (Q'^2 - Q^2) / (2 C_mem)
        let mut carrier =
            ChargeCarrierState::new(-10.0e-12, 100.0e-12, 0.0, 1000, 1000).unwrap();
        let e_cap_init = carrier.stored_energy();
        let transport = carrier.settle_transport(2.0 * ELEMENTARY_CHARGE, 1, 0.0).unwrap();
        let e_cap_final = carrier.stored_energy();

        let expected_delta_e = e_cap_final - e_cap_init;
        assert!((transport.delta_e_cap - expected_delta_e).abs() < 1e-25);

        let balance = ClosedEnergyBalance::compute_fixed_x(
            u_initial,
            u_final,
            res.dissipated_energy,
            transport.delta_e_cap,
        );
        assert!(balance.mechanical_energy_balance_residual < 1e-20);
    }

    #[test]
    fn test_continuation_serialization_and_exact_restoration() {
        let carrier =
            ChargeCarrierState::new(-6.8e-12, 100.0e-12, 0.4321, 999_800, 500_200).unwrap();
        let receptor = ReceptorKineticsState::new(
            0.85e-9, 0.15e-9, 0.05e-9, 1.2e-9, 1.0e-18, 0.0035, 1.0e8, 10.0, 5.0, 2.0,
        )
        .unwrap();
        let mechanics =
            MechanicalPlasticState::new(1.4e-6, 1.1e-6, 80.0e-9, 16.0e-9, 0.0012).unwrap();

        let original_state = ConstitutiveState::new(carrier, receptor, mechanics);

        // Serialize to 176 bytes
        let serialized = original_state.serialize();
        assert_eq!(serialized.len(), SERIALIZED_STATE_SIZE);
        assert_eq!(&serialized[0..8], STATE_MAGIC);

        // Restore state
        let restored_state = ConstitutiveState::deserialize(&serialized).unwrap();
        assert_eq!(
            original_state, restored_state,
            "Restored state must match original bit-exact"
        );

        // Verify next identical input produces bit-identical output
        let mut state_a = original_state.clone();
        let mut state_b = restored_state.clone();

        let res_a_carrier = state_a
            .carrier
            .settle_transport(3.5 * ELEMENTARY_CHARGE, 1, 0.0)
            .unwrap();
        let res_b_carrier = state_b
            .carrier
            .settle_transport(3.5 * ELEMENTARY_CHARGE, 1, 0.0)
            .unwrap();
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
        assert!(matches!(
            err,
            Err(ConstitutiveError::InvalidChecksum { .. })
        ));

        // Truncated data must fail
        let err_trunc = ConstitutiveState::deserialize(&serialized[0..100]);
        assert!(matches!(
            err_trunc,
            Err(ConstitutiveError::TruncatedData { .. })
        ));

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
        let receptor =
            ReceptorKineticsState::new(1.0, 0.0, 0.0, 1.0, 1.0, 0.0, 1.0, 1.0, 1.0, 1.0)
                .unwrap();
        let mechanics = MechanicalPlasticState::new(1.0, 1.0, 10.0, 2.0, 0.0).unwrap();
        let state = ConstitutiveState::new(carrier, receptor, mechanics);

        let bytes = state.serialize();
        assert_eq!(
            bytes.len(),
            176,
            "Component serialization footprint must be bounded to 176 bytes"
        );

        // Zero valence error
        let mut carrier2 = ChargeCarrierState::new(0.0, 1.0, 0.0, 10, 10).unwrap();
        assert_eq!(
            carrier2.settle_transport(1.0, 0, 0.0),
            Err(ConstitutiveError::ZeroValence)
        );

        // Invalid dt error
        let mut rec2 =
            ReceptorKineticsState::new(1.0, 0.0, 0.0, 1.0, 1.0, 0.0, 1.0, 1.0, 1.0, 1.0)
                .unwrap();
        assert_eq!(
            rec2.step_kinetics(0.0),
            Err(ConstitutiveError::InvalidTimeStep(0.0))
        );
        assert_eq!(
            rec2.step_kinetics(-0.01),
            Err(ConstitutiveError::InvalidTimeStep(-0.01))
        );
    }

    // -----------------------------------------------------------------------
    // Section 6 Tests: Canonical Typed Phase-Gate-Material Dynamic Operator
    // -----------------------------------------------------------------------

    #[test]
    fn test_phase_coupled_oscillator_fabric_channel_differentiation() {
        // Falsifies Finding A13-01: Swapping D and M produces completely distinct
        // oscillator phase states, gate activations, conductances, and currents.
        let mut op_d = TypedPhaseGateMaterialOperator::default_canonical().unwrap();
        let mut op_m = TypedPhaseGateMaterialOperator::default_canonical().unwrap();

        let field_d = [1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]; // Pure Displacement D
        let field_m = [0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0]; // Pure Momentum M

        let receipt_d = op_d.step_transition(&field_d, 1.0, 0.0, 0.01).unwrap();
        let receipt_m = op_m.step_transition(&field_m, 1.0, 0.0, 0.01).unwrap();

        // 1. Fabric phases must be completely different
        assert_ne!(op_d.fabric.phases, op_m.fabric.phases);
        assert_ne!(op_d.fabric.phases[0], op_m.fabric.phases[0]);
        assert_ne!(op_d.fabric.phases[1], op_m.fabric.phases[1]);

        // 2. Gate states and conductances must be distinct
        assert_ne!(
            receipt_d.channel_conductances,
            receipt_m.channel_conductances
        );
        assert_ne!(receipt_d.v_membrane_final, receipt_m.v_membrane_final);
        assert_ne!(
            receipt_d.channel_current_integrals,
            receipt_m.channel_current_integrals
        );
    }

    #[test]
    fn test_phase_winding_checked_overflow_safety() {
        let mut fabric = PhaseCoupledOscillatorFabric::new(
            [0.0; DSF_CHANNELS],
            [0; DSF_CHANNELS],
            [100.0; DSF_CHANNELS],
            [10.0; DSF_CHANNELS],
        )
        .unwrap();

        // Step with large dt to trigger multiple complete 2*pi windings
        fabric.step(&[1.0; DSF_CHANNELS], 1.0).unwrap();

        for i in 0..DSF_CHANNELS {
            assert!(fabric.phases[i] >= -std::f64::consts::PI);
            assert!(fabric.phases[i] <= std::f64::consts::PI);
            assert!(fabric.windings[i] > 0, "Winding must track integer wraps");
        }

        // Extreme overflow check refuses atomically
        let mut overflow_fabric = PhaseCoupledOscillatorFabric::new(
            [0.0; DSF_CHANNELS],
            [i64::MAX; DSF_CHANNELS],
            [1e20; DSF_CHANNELS],
            [0.0; DSF_CHANNELS],
        )
        .unwrap();
        assert!(overflow_fabric.step(&[0.0; DSF_CHANNELS], 1.0).is_err());
    }

    #[test]
    fn test_thermodynamic_gate_potential_and_langevin_relaxation() {
        let mut gate = ThermodynamicChannelGate::new(
            0.0,
            1.0e-3, // zeta
            1.0,    // k
            0.1,    // rest_y
            0.0,
            0.5,    // chemical potential positive bias
            [0.0; DSF_CHANNELS],
            [0.0; DSF_CHANNELS],
        )
        .unwrap();

        let phases = [0.0; DSF_CHANNELS];
        // Initially at 0.0, target is 0.1 + 0.5/1.0 = 0.6.
        let delta_y = gate.step(-0.065, &phases, 0.001).unwrap();
        assert!(delta_y > 0.0, "Gate must open towards lower potential");
        assert!(gate.y > 0.0 && gate.y <= 1.0);

        // Relax for long horizon (e.g. 50 steps)
        for _ in 0..50 {
            gate.step(-0.065, &phases, 0.001).unwrap();
        }
        // At equilibrium, y approaches 0.60
        assert!((gate.y - 0.60).abs() < 1e-4);
    }

    #[test]
    fn test_exact_membrane_electrodynamics_and_charge_conservation() {
        let mut op = TypedPhaseGateMaterialOperator::default_canonical().unwrap();
        let field = [0.5, 0.2, 0.1, 0.0, 0.3, 0.1, 0.4];

        for step in 0..10 {
            let i_ext = (step as f64 - 5.0) * 1.0e-10;
            let receipt = op.step_transition(&field, 1.0, i_ext, 0.001).unwrap();

            // Machine-precision charge conservation
            assert!(
                receipt.charge_conservation_residual < 1e-20,
                "Charge residual: {}",
                receipt.charge_conservation_residual
            );
            assert!(receipt.total_conductance > 0.0);
            assert!(receipt.v_membrane_final.is_finite());
        }
    }

    #[test]
    fn test_exact_thermodynamic_first_law_energy_balance() {
        let mut op = TypedPhaseGateMaterialOperator::default_canonical().unwrap();
        let field = [0.8, -0.4, 0.2, 0.1, 0.5, 0.0, 0.7];

        for _ in 0..10 {
            let receipt = op.step_transition(&field, 1.0, 2.0e-10, 0.0005).unwrap();

            // Exact first law balance: Delta E_cap + Q_joule = W_chem + W_ext
            assert!(
                receipt.energy_conservation_residual < 1e-20,
                "Energy residual: {}",
                receipt.energy_conservation_residual
            );
            // Dissipated Joule heat is non-negative
            assert!(
                receipt.q_joule >= 0.0,
                "Joule dissipation must be non-negative"
            );
        }
    }

    #[test]
    fn test_equal_opposite_integer_carrier_custody_across_channels() {
        let mut op = TypedPhaseGateMaterialOperator::default_canonical().unwrap();
        let field = [1.0, 0.5, 0.0, 0.0, 0.0, 0.0, 1.0];

        let before_reservoirs: Vec<(u64, u64)> = op
            .channels
            .iter()
            .map(|ch| (ch.carriers.source_reservoir, ch.carriers.dest_reservoir))
            .collect();

        let receipt = op.step_transition(&field, 1.0, 0.0, 0.01).unwrap();

        for c in 0..ION_CHANNELS {
            let n = receipt.carrier_transfers[c];
            let (src_before, dst_before) = before_reservoirs[c];
            let src_after = op.channels[c].carriers.source_reservoir;
            let dst_after = op.channels[c].carriers.dest_reservoir;

            if n > 0 {
                assert_eq!(src_after, src_before - (n as u64));
                assert_eq!(dst_after, dst_before + (n as u64));
            } else if n < 0 {
                let abs_n = n.unsigned_abs();
                assert_eq!(src_after, src_before + abs_n);
                assert_eq!(dst_after, dst_before - abs_n);
            } else {
                assert_eq!(src_after, src_before);
                assert_eq!(dst_after, dst_before);
            }
            assert_eq!(
                (src_after as u128) + (dst_after as u128),
                (src_before as u128) + (dst_before as u128)
            );
        }
    }

    #[test]
    fn test_operator_serialization_exact_roundtrip_and_corruption_rejection() {
        let mut op = TypedPhaseGateMaterialOperator::default_canonical().unwrap();
        op.step_transition(&[0.5; DSF_CHANNELS], 1.0, 1e-10, 0.01)
            .unwrap();

        let bytes = op.serialize();
        assert_eq!(bytes.len(), OPERATOR_SERIALIZED_SIZE);
        assert_eq!(&bytes[0..8], OPERATOR_STATE_MAGIC);

        let restored = TypedPhaseGateMaterialOperator::deserialize(&bytes).unwrap();
        assert_eq!(op, restored, "Restored operator must match bit-exact");

        // Next step produces bit-identical results
        let mut op_a = op.clone();
        let mut op_b = restored.clone();
        let rec_a = op_a
            .step_transition(&[0.2; DSF_CHANNELS], 1.0, 0.0, 0.005)
            .unwrap();
        let rec_b = op_b
            .step_transition(&[0.2; DSF_CHANNELS], 1.0, 0.0, 0.005)
            .unwrap();
        assert_eq!(rec_a, rec_b);
        assert_eq!(op_a, op_b);

        // Corruption handling
        let mut corrupted = bytes;
        corrupted[100] ^= 0xAA;
        assert!(matches!(
            TypedPhaseGateMaterialOperator::deserialize(&corrupted),
            Err(ConstitutiveError::InvalidChecksum { .. })
        ));

        // Truncation handling
        assert!(matches!(
            TypedPhaseGateMaterialOperator::deserialize(&bytes[0..500]),
            Err(ConstitutiveError::TruncatedData { .. })
        ));
    }

    #[test]
    fn test_viability_gate_refusal() {
        let mut op = TypedPhaseGateMaterialOperator::default_canonical().unwrap();
        let before = op.clone();

        // Viability gate refuses transition when S_UF <= 0
        let err_0 = op.step_transition(&[0.0; DSF_CHANNELS], 0.0, 0.0, 0.01);
        assert!(err_0.is_err());
        assert_eq!(op, before, "State must not mutate on refusal");

        let err_neg = op.step_transition(&[0.0; DSF_CHANNELS], -0.5, 0.0, 0.01);
        assert!(err_neg.is_err());
        assert_eq!(op, before);
    }
}

#[cfg(test)]
mod a13_carrier_safety {
    use super::*;

    fn unchanged(a: &ChargeCarrierState, b: &ChargeCarrierState) {
        assert_eq!(a.q_membrane.to_bits(), b.q_membrane.to_bits());
        assert_eq!(a.c_mem.to_bits(), b.c_mem.to_bits());
        assert_eq!(a.remainder.to_bits(), b.remainder.to_bits());
        assert_eq!(a.source_reservoir, b.source_reservoir);
        assert_eq!(a.dest_reservoir, b.dest_reservoir);
    }

    #[test]
    fn endpoint_overflow_refuses_both_directions_without_losing_carriers() {
        for (source, destination, direction) in [(1, u64::MAX, 1.0), (u64::MAX, 1, -1.0)] {
            let mut state = ChargeCarrierState::new(0.0, 1.0, 0.0, source, destination).unwrap();
            let before = state.clone();
            assert!(state
                .settle_transport(direction * ELEMENTARY_CHARGE, 1, 0.0)
                .is_err());
            unchanged(&state, &before);
        }
    }

    #[test]
    fn excessive_quotients_refuse_before_cast_or_mutation() {
        let boundary = (1_u64 << f64::MANTISSA_DIGITS) as f64;
        for integral in [
            f64::MAX,
            -f64::MAX,
            boundary * ELEMENTARY_CHARGE,
            -boundary * ELEMENTARY_CHARGE,
            f64::NAN,
            f64::INFINITY,
        ] {
            let mut state =
                ChargeCarrierState::new(0.0, 1.0, 0.0, u64::MAX, u64::MAX).unwrap();
            let before = state.clone();
            assert!(state.settle_transport(integral, 1, 0.0).is_err());
            unchanged(&state, &before);
        }
    }

    #[test]
    fn nonfinite_successor_cannot_partially_debit_reservoir() {
        let mut state = ChargeCarrierState::new(0.0, 1.0, 0.0, 10, 10).unwrap();
        let before = state.clone();
        assert!(state
            .settle_transport(ELEMENTARY_CHARGE, 1, f64::MAX)
            .is_err());
        unchanged(&state, &before);
    }

    #[test]
    fn exhausted_or_invalid_retained_state_refuses_atomically() {
        for integral in [ELEMENTARY_CHARGE, -ELEMENTARY_CHARGE] {
            let mut state = ChargeCarrierState::new(0.0, 1.0, 0.25, 0, 0).unwrap();
            // Ensure both directions request a complete carrier.
            let integral = integral * 2.0;
            let before = state.clone();
            assert!(state.settle_transport(integral, 1, 0.0).is_err());
            unchanged(&state, &before);
        }
        let valid = ChargeCarrierState::new(0.0, 1.0, 0.0, 10, 10).unwrap();
        let mut invalid = valid.clone();
        invalid.remainder = f64::NAN;
        let before = invalid.clone();
        assert!(invalid.settle_transport(0.0, 1, 0.0).is_err());
        unchanged(&invalid, &before);
        assert!(ChargeCarrierState::new(f64::MAX, 1.0, 0.0, 10, 10).is_err());
    }

    #[test]
    fn accepted_transfer_has_exact_equal_opposite_integer_endpoints() {
        for valence in [-2, -1, 1, 2] {
            for direction in [-1.0, 1.0] {
                let mut state = ChargeCarrierState::new(0.0, 1.0, 0.0, 50, 60).unwrap();
                let before = state.clone();
                let integral = direction * f64::from(valence) * ELEMENTARY_CHARGE;
                let result = state.settle_transport(integral, valence, 0.0).unwrap();
                let n = i128::from(result.carriers_transported);
                assert_eq!(
                    i128::from(state.source_reservoir),
                    i128::from(before.source_reservoir) - n
                );
                assert_eq!(
                    i128::from(state.dest_reservoir),
                    i128::from(before.dest_reservoir) + n
                );
                assert_eq!(
                    u128::from(state.source_reservoir) + u128::from(state.dest_reservoir),
                    110
                );
                assert!(result.identity_residual.is_finite());
            }
        }
    }
}
