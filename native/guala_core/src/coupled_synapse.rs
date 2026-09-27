//! Coupled Material-and-Receptor Synapse Transition (Stage P1-B)
//!
//! Unmounted native implementation under `native/guala_core` boundary.
//! Composes constitutive operators into the complete physical pathway:
//! 1. Presynaptic arrival -> Quantal vesicle transmitter release (§5)
//! 2. Cleft diffusion and finite receptor kinetics (R + T <=> A -> D + T, D -> R) (§6)
//! 3. Dimensionless aperture gating (y_c = A / R_tot) and pore conductance g_c (§5)
//! 4. Nernst driving force and exact carrier transport with remainder custody (§5)
//! 5. Physical participation tracking (integrated active exposure A_e) (§6)
//! 6. Consequence-driven plastic yield return map with selective participation (§7)
//! 7. Single-counted energy accounting: passive yield releases stored elastic energy;
//!    active remodeling separately accounts metabolic ATP work (§7, §8)
//! 8. Explicit material provenance descriptor and validation gate (§10)
//!
//! UNMOUNTED: No import into production decision selection.

use crate::constitutive::{
    CarrierTransportResult, ChargeCarrierState, ConstitutiveError, MechanicalPlasticState,
    PlasticReturnResult, ReceptorKineticsState, ELEMENTARY_CHARGE,
};

// ---------------------------------------------------------------------------
// Physical Constants
// ---------------------------------------------------------------------------

/// Boltzmann constant in Joules per Kelvin [J / K].
pub const BOLTZMANN_CONSTANT: f64 = 1.380_649e-23;
/// Reference physiological temperature in Kelvin [K] (approx 37 C).
pub const PHYSIOLOGICAL_TEMP_K: f64 = 310.15;

// ---------------------------------------------------------------------------
// Material Provenance Authority (§10)
// ---------------------------------------------------------------------------

#[derive(Debug, Clone, PartialEq)]
pub enum MaterialProvenance {
    /// Explicit mathematical fixture for bounded algebraic testing.
    MathematicalFixture { label: String },
    /// Calibrated physical measurement with authoritative citation and SI units.
    CalibratedMeasurement {
        authority: String,
        measurement_id: String,
    },
    /// Unverified provenance: MUST be rejected from live production mounting.
    Unverified { reason: String },
}

impl MaterialProvenance {
    pub fn validate_for_mounting(&self) -> Result<(), ConstitutiveError> {
        match self {
            MaterialProvenance::MathematicalFixture { .. } => Ok(()),
            MaterialProvenance::CalibratedMeasurement { .. } => Ok(()),
            MaterialProvenance::Unverified { reason } => Err(ConstitutiveError::InvalidDomain(
                format!("Unverified material provenance rejected: {}", reason),
            )),
        }
    }
}

// ---------------------------------------------------------------------------
// Ion Species and Nernst Equilibrium (§5)
// ---------------------------------------------------------------------------

#[derive(Debug, Clone, Copy, PartialEq)]
pub enum IonSpecies {
    Sodium,    // Na+: valence +1
    Potassium, // K+: valence +1
    Calcium,   // Ca2+: valence +2
    Chloride,  // Cl-: valence -1
}

impl IonSpecies {
    #[inline]
    pub fn valence(&self) -> i32 {
        match self {
            IonSpecies::Sodium => 1,
            IonSpecies::Potassium => 1,
            IonSpecies::Calcium => 2,
            IonSpecies::Chloride => -1,
        }
    }

    /// Computes exact Nernst reversal potential E_rev in Volts [V]:
    ///   E_rev = (k_B * T / (z * e_0)) * ln(c_out / c_in)
    pub fn nernst_potential(
        &self,
        c_out: f64,
        c_in: f64,
        temperature_k: f64,
    ) -> Result<f64, ConstitutiveError> {
        if c_out <= 0.0 || c_in <= 0.0 {
            return Err(ConstitutiveError::InvalidDomain(
                "Ion concentrations must be strictly positive".to_string(),
            ));
        }
        if temperature_k <= 0.0 {
            return Err(ConstitutiveError::InvalidDomain(
                "Temperature must be strictly positive Kelvin".to_string(),
            ));
        }
        let z = self.valence() as f64;
        let thermal_voltage = (BOLTZMANN_CONSTANT * temperature_k) / (z * ELEMENTARY_CHARGE);
        Ok(thermal_voltage * (c_out / c_in).ln())
    }
}

// ---------------------------------------------------------------------------
// Presynaptic Vesicle Pool (§5)
// ---------------------------------------------------------------------------

#[derive(Debug, Clone, PartialEq)]
pub struct PresynapticVesiclePool {
    /// Number of discrete vesicles currently available in readily releasable pool.
    pub available_vesicles: u32,
    /// Maximum capacity of the vesicle pool.
    pub pool_capacity: u32,
    /// Moles of transmitter per single vesicle [mol / vesicle].
    pub quantal_moles_per_vesicle: f64,
}

impl PresynapticVesiclePool {
    pub fn new(
        available_vesicles: u32,
        pool_capacity: u32,
        quantal_moles_per_vesicle: f64,
    ) -> Result<Self, ConstitutiveError> {
        if quantal_moles_per_vesicle <= 0.0 || !quantal_moles_per_vesicle.is_finite() {
            return Err(ConstitutiveError::InvalidDomain(
                "quantal_moles_per_vesicle must be positive and finite".to_string(),
            ));
        }
        if available_vesicles > pool_capacity {
            return Err(ConstitutiveError::InvalidDomain(
                "available_vesicles cannot exceed pool_capacity".to_string(),
            ));
        }
        Ok(Self {
            available_vesicles,
            pool_capacity,
            quantal_moles_per_vesicle,
        })
    }

    /// Releases transmitter upon afferent arrivals.
    /// Returns exact moles of transmitter released into the cleft [mol].
    pub fn release(&mut self, arrival_count: u32) -> f64 {
        let vesicles_to_release = arrival_count.min(self.available_vesicles);
        self.available_vesicles -= vesicles_to_release;
        (vesicles_to_release as f64) * self.quantal_moles_per_vesicle
    }
}

// ---------------------------------------------------------------------------
// Coupled Synapse Component (§5, §6, §7, §8, §10)
// ---------------------------------------------------------------------------

#[derive(Debug, Clone, PartialEq)]
pub struct CoupledSynapse {
    /// Material provenance authority.
    pub provenance: MaterialProvenance,
    /// Primary ion species traversing the postsynaptic receptor-channel.
    pub species: IonSpecies,
    /// Presynaptic quantal release pool.
    pub vesicle_pool: PresynapticVesiclePool,
    /// Postsynaptic finite receptor kinetics state.
    pub receptor: ReceptorKineticsState,
    /// Postsynaptic electrical charge and carrier remainder custody.
    pub carrier: ChargeCarrierState,
    /// Spine mechanical plasticity state.
    pub mechanics: MechanicalPlasticState,
    /// Peak open-channel pore conductance g_max in Siemens [S] (> 0).
    pub g_max: f64,
    /// Postsynaptic Nernst reversal potential E_rev in Volts [V].
    pub e_reversal: f64,
    /// Local metabolic reservoir M_i in Joules [J] (>= 0).
    pub metabolic_reserve: f64,
    /// Reference participation time window tau_ref in seconds [s] (> 0).
    pub tau_participation_ref: f64,
}

#[derive(Debug, Clone, PartialEq)]
pub struct SynapseStepReceipt {
    pub transmitter_released_mol: f64,
    pub aperture_fraction: f64,
    pub instantaneous_conductance_s: f64,
    pub ionic_current_a: f64,
    pub carrier_transport: CarrierTransportResult,
    pub membrane_voltage_v: f64,
    pub participation_factor: f64,
}

impl CoupledSynapse {
    #[allow(clippy::too_many_arguments)]
    pub fn new(
        provenance: MaterialProvenance,
        species: IonSpecies,
        vesicle_pool: PresynapticVesiclePool,
        receptor: ReceptorKineticsState,
        carrier: ChargeCarrierState,
        mechanics: MechanicalPlasticState,
        g_max: f64,
        e_reversal: f64,
        metabolic_reserve: f64,
        tau_participation_ref: f64,
    ) -> Result<Self, ConstitutiveError> {
        // Enforce provenance gate
        provenance.validate_for_mounting()?;

        if !g_max.is_finite() || g_max <= 0.0 {
            return Err(ConstitutiveError::InvalidDomain(
                "g_max must be positive and finite".to_string(),
            ));
        }
        if !e_reversal.is_finite() {
            return Err(ConstitutiveError::InvalidDomain(
                "e_reversal must be finite".to_string(),
            ));
        }
        if metabolic_reserve < 0.0 || !metabolic_reserve.is_finite() {
            return Err(ConstitutiveError::InvalidDomain(
                "metabolic_reserve must be non-negative and finite".to_string(),
            ));
        }
        if tau_participation_ref <= 0.0 || !tau_participation_ref.is_finite() {
            return Err(ConstitutiveError::InvalidDomain(
                "tau_participation_ref must be positive and finite".to_string(),
            ));
        }

        Ok(Self {
            provenance,
            species,
            vesicle_pool,
            receptor,
            carrier,
            mechanics,
            g_max,
            e_reversal,
            metabolic_reserve,
            tau_participation_ref,
        })
    }

    /// Instantaneous dimensionless aperture coordinate y_c = A / R_total in [0, 1].
    #[inline]
    pub fn aperture_coordinate(&self) -> f64 {
        let r_tot = self.receptor.total_receptors();
        if r_tot > 0.0 {
            (self.receptor.a_active / r_tot).clamp(0.0, 1.0)
        } else {
            0.0
        }
    }

    /// Instantaneous postsynaptic channel conductance g_c = g_max * y_c in Siemens [S].
    #[inline]
    pub fn conductance(&self) -> f64 {
        self.g_max * self.aperture_coordinate()
    }

    /// Dimensionless physical participation factor Pi_e in [0, 1].
    /// Derived from accumulated active complex exposure integral A dt [mol * s].
    #[inline]
    pub fn participation_factor(&self) -> f64 {
        let r_tot = self.receptor.total_receptors();
        if r_tot > 0.0 && self.tau_participation_ref > 0.0 {
            let denom = r_tot * self.tau_participation_ref;
            (self.receptor.integrated_exposure / denom).clamp(0.0, 1.0)
        } else {
            0.0
        }
    }

    /// Advances coupled synapse state over physical interval dt [s] with presynaptic arrival count.
    ///
    /// Preserves exact sequence:
    ///   1. Afferent arrivals release discrete transmitter into cleft.
    ///   2. Cleft reactions advance stoichiometry with bit-exact conservation.
    ///   3. Active receptor complex A gates pore aperture fraction y_c.
    ///   4. Conductance g_c(y_c) and Nernst gradient drive ionic current I_c.
    ///   5. Exact carrier remainder settlement updates membrane charge and finite reservoirs.
    pub fn advance_afferent_step(
        &mut self,
        arrival_count: u32,
        dt: f64,
    ) -> Result<SynapseStepReceipt, ConstitutiveError> {
        if dt <= 0.0 || !dt.is_finite() {
            return Err(ConstitutiveError::InvalidTimeStep(dt));
        }

        // 1. Quantal release from presynaptic vesicle store
        let t_released = self.vesicle_pool.release(arrival_count);
        self.receptor.t_free += t_released;

        // 2. Finite receptor kinetics step (conserves R+A+D and T+A)
        self.receptor.step_kinetics(dt)?;

        // 3. Aperture gating and conductance
        let aperture = self.aperture_coordinate();
        let g_c = self.g_max * aperture;

        // 4. Ionic current under Nernst driving potential
        let v_m = self.carrier.voltage();
        let driving_potential = v_m - self.e_reversal;
        let i_c = g_c * driving_potential;

        // Continuous charge integral J_c = I_c * dt [C]
        let j_c = i_c * dt;

        // 5. Signed carrier settlement with remainder custody
        let transport_res = self
            .carrier
            .settle_transport(j_c, self.species.valence(), 0.0)?;

        let participation = self.participation_factor();

        Ok(SynapseStepReceipt {
            transmitter_released_mol: t_released,
            aperture_fraction: aperture,
            instantaneous_conductance_s: g_c,
            ionic_current_a: i_c,
            carrier_transport: transport_res,
            membrane_voltage_v: self.carrier.voltage(),
            participation_factor: participation,
        })
    }

    /// Evaluates passive plastic yield at fixed physical coordinate x (§7, §8).
    ///
    /// Energy Conservation Law (§7 line 304, §8):
    ///   Passive plastic dissipation D_pl is energy released from stored elastic energy:
    ///     Delta U_elastic = U(x, l_{n+1}) - U(x, l_n) = -D_pl <= 0
    ///     Q_heat = D_pl >= 0
    ///     Delta U_elastic + Q_heat = 0
    ///   It is NOT charged a second time to metabolic reserves (ATP).
    ///
    /// Participation Gating (§6, §7):
    ///   - If participation factor Pi_e == 0 (unreached pathway):
    ///     No plastic deformation occurs: Delta l = 0, D_pl = 0.
    ///   - If participation factor Pi_e > 0:
    ///     Engages rate-independent mechanical return map.
    pub fn apply_consequence(
        &mut self,
        consequence_x: f64,
    ) -> Result<Option<PlasticReturnResult>, ConstitutiveError> {
        if consequence_x <= 0.0 || !consequence_x.is_finite() {
            return Err(ConstitutiveError::InvalidDomain(
                "consequence_x must be positive and finite".to_string(),
            ));
        }

        let participation = self.participation_factor();

        // Selective participation: unreached pathways do NOT undergo plastic remodeling
        if participation <= 0.0 {
            return Ok(None);
        }

        // Participating pathway: set reached coordinate and evaluate return map
        self.mechanics.x = consequence_x;
        let return_res = self.mechanics.return_map_fixed_x()?;

        // Passive plastic yield energy D_pl is released from stored elastic energy (Delta U = -D_pl).
        // It does NOT debit metabolic reserve M_i.

        Ok(Some(return_res))
    }

    /// Active biochemical remodeling against load (§8).
    /// Unlike passive plastic yield (which releases stored elastic energy into heat),
    /// active remodeling consumes metabolic energy (ATP) to synthesize new reference structure.
    pub fn apply_active_metabolic_remodeling(
        &mut self,
        target_delta_l: f64,
        metabolic_energy_cost: f64,
    ) -> Result<(), ConstitutiveError> {
        if metabolic_energy_cost < 0.0 || !metabolic_energy_cost.is_finite() {
            return Err(ConstitutiveError::InvalidDomain(
                "metabolic_energy_cost must be non-negative and finite".to_string(),
            ));
        }
        if self.metabolic_reserve < metabolic_energy_cost {
            return Err(ConstitutiveError::ExhaustedReservoir {
                required: (metabolic_energy_cost * 1e12).ceil() as u64,
                available: (self.metabolic_reserve * 1e12).floor() as u64,
                reservoir_name: "metabolic_reserve_pJ".to_string(),
            });
        }
        self.metabolic_reserve -= metabolic_energy_cost;
        self.mechanics.l_ref += target_delta_l;
        Ok(())
    }
}

// ===========================================================================
// Tests: Stage P1-B Coupled Synapse Verification Suite
// ===========================================================================

#[cfg(test)]
mod tests {
    use super::*;

    fn create_fixture_synapse(
        label: &str,
        init_vesicles: u32,
        k_elastic: f64,
        yield_energy: f64,
        metabolic_reserve: f64,
    ) -> CoupledSynapse {
        let prov = MaterialProvenance::MathematicalFixture {
            label: label.to_string(),
        };
        let species = IonSpecies::Sodium;
        let pool = PresynapticVesiclePool::new(init_vesicles, 100, 1.0e-20).unwrap();
        let rec = ReceptorKineticsState::new(
            1.0e-12, 0.0, 0.0, 0.0, 1.0e-18, 0.0, 1.0e8, 10.0, 5.0, 2.0,
        )
        .unwrap();
        let carrier = ChargeCarrierState::new(-7.0e-12, 100.0e-12, 0.0, 1_000_000, 500_000).unwrap();
        let mech = MechanicalPlasticState::new(1.0e-6, 1.0e-6, k_elastic, yield_energy, 0.0).unwrap();
        CoupledSynapse::new(
            prov,
            species,
            pool,
            rec,
            carrier,
            mech,
            10.0e-9, // g_max = 10 nS
            0.0,     // E_rev = 0 mV
            metabolic_reserve,
            0.05,    // tau_participation_ref = 50 ms
        )
        .unwrap()
    }

    #[test]
    fn test_coupled_afferent_release_and_channel_gating() {
        let mut synapse = create_fixture_synapse("test_release", 50, 100.0e-9, 20.0e-9, 1.0e-6);

        // Before arrival: zero conductance, zero aperture
        assert_eq!(synapse.aperture_coordinate(), 0.0);
        assert_eq!(synapse.conductance(), 0.0);

        // Advance with 5 presynaptic arrivals over 10 ms
        let receipt = synapse.advance_afferent_step(5, 0.010).unwrap();

        assert_eq!(receipt.transmitter_released_mol, 5.0 * 1.0e-20);
        assert!(receipt.aperture_fraction > 0.0, "Receptor binding must open pore");
        assert!(receipt.instantaneous_conductance_s > 0.0);
        assert_eq!(synapse.vesicle_pool.available_vesicles, 45);

        // Current must flow because V_m = -70 mV and E_rev = 0 mV (driving potential -70 mV)
        assert!(receipt.ionic_current_a < 0.0, "Inward current for Na+");
        assert!(receipt.carrier_transport.identity_residual < 1e-25);
        assert!(synapse.participation_factor() > 0.0, "Active exposure must be recorded");
    }

    #[test]
    fn test_selective_participation_consequence_coupling() {
        // Synapse 1 will receive presynaptic activation
        let mut syn1 = create_fixture_synapse("participating_syn", 50, 100.0e-9, 20.0e-9, 1.0e-6);
        // Synapse 2 will remain completely unreached (zero arrivals)
        let mut syn2 = create_fixture_synapse("unreached_syn", 50, 100.0e-9, 20.0e-9, 1.0e-6);

        // Activate syn1
        syn1.advance_afferent_step(10, 0.010).unwrap();
        assert!(syn1.participation_factor() > 0.0, "Syn1 must be participating");

        // Advance syn2 without arrivals (unreached)
        syn2.advance_afferent_step(0, 0.010).unwrap();
        assert_eq!(syn2.participation_factor(), 0.0, "Syn2 must have ZERO participation");

        // Apply consequence displacement: 1.5 um (tension loading, epsilon_tr = 0.5 > Y/K = 0.2)
        let res1 = syn1.apply_consequence(1.5e-6).unwrap();
        let res2 = syn2.apply_consequence(1.5e-6).unwrap();

        // Syn1 (participating) must undergo plastic remodeling
        assert!(res1.is_some(), "Participating synapse must evaluate consequence");
        let r1 = res1.unwrap();
        assert!(r1.is_yielded);
        assert!(r1.delta_l > 0.0);
        assert!(r1.dissipated_energy > 0.0);

        // Single-counting check (§7 line 305):
        // Passive yield dissipation comes from stored elastic energy release (Delta U = -D_pl).
        // It does NOT debit metabolic ATP reserve!
        assert_eq!(
            syn1.metabolic_reserve, 1.0e-6,
            "Passive yield must not double-charge metabolic ATP"
        );

        // Syn2 (unreached) must undergo ZERO plastic remodeling
        assert!(res2.is_none(), "Unreached synapse must be untouched by consequence");
        assert_eq!(syn2.mechanics.l_ref, 1.0e-6, "Reference length must remain unchanged");
        assert_eq!(syn2.metabolic_reserve, 1.0e-6, "Metabolic reserve must be untouched");
    }

    #[test]
    fn test_active_metabolic_remodeling_accounting() {
        let mut synapse = create_fixture_synapse("active_remodel", 50, 100.0e-9, 20.0e-9, 50.0e-9);

        // Active remodeling work (e.g. ATP-driven actin restructuring: 10 nJ)
        synapse.apply_active_metabolic_remodeling(0.1e-6, 10.0e-9).unwrap();
        assert_eq!(synapse.mechanics.l_ref, 1.1e-6);
        assert!((synapse.metabolic_reserve - 40.0e-9).abs() < 1e-15);

        // Depletion check: request 100 nJ when only 40 nJ remains
        let err = synapse.apply_active_metabolic_remodeling(0.5e-6, 100.0e-9);
        assert!(matches!(
            err,
            Err(ConstitutiveError::ExhaustedReservoir { .. })
        ));
        assert_eq!(synapse.mechanics.l_ref, 1.1e-6, "Length must not mutate on failure");
    }

    #[test]
    fn test_material_provenance_validation() {
        let fixture_prov = MaterialProvenance::MathematicalFixture {
            label: "valid_fixture".to_string(),
        };
        assert!(fixture_prov.validate_for_mounting().is_ok());

        let calib_prov = MaterialProvenance::CalibratedMeasurement {
            authority: "LoomNeuron_V4".to_string(),
            measurement_id: "Spine_Stiffness_01".to_string(),
        };
        assert!(calib_prov.validate_for_mounting().is_ok());

        let unverified_prov = MaterialProvenance::Unverified {
            reason: "Borrowed arbitrary constant without derivation".to_string(),
        };
        assert!(matches!(
            unverified_prov.validate_for_mounting(),
            Err(ConstitutiveError::InvalidDomain(_))
        ));
    }
}
