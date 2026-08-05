//! Exact local conversion from one reached retinal source occurrence to gate work.
//!
//! The source carrier preserves a spectral-irradiance fraction and its physical
//! clock.  Fixed receptor anatomy supplies the declared reference irradiance,
//! aperture area, absorptance, and conformational coupling.  Exact trapezoidal
//! integration yields incident energy and the local negative free-energy work
//! applied to the receptor gate.  DSF coordinates do not enter this conversion:
//! the unchanged full DSF field reaches the neuron's Psi/MathLoom path separately.

use num_bigint::BigInt;
use num_rational::BigRational;
use num_traits::{One, Signed, ToPrimitive, Zero};

use crate::complete_neuron::GateWorkOccurrence;
use crate::exact_rational::ExactRational;
use crate::joint_source_episode::{JointSourcePortView, NativeJointSourceEpisode};
use crate::joint_uf_neuron_boundary::JointNeuronPerspective;
use crate::neuron_source_anchor::{
    bind_neuron_source_anchor, NeuronSourceAnchorError, PhysicalSourceSense,
};

pub(crate) const RETINAL_SPECTRAL_IRRADIANCE_QUANTITY: &str = "retinal-spectral-irradiance";
pub(crate) const RETINAL_REFERENCE_IRRADIANCE_UNIT: &str =
    "fraction-of-declared-retinal-reference-irradiance";

#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) struct OpticalReceptorAnatomy {
    reference_irradiance_zeptojoules_per_square_nanometre_second: BigRational,
    aperture_square_nanometres: BigRational,
    absorptance: BigRational,
    conformational_coupling: BigRational,
}

impl OpticalReceptorAnatomy {
    pub(crate) fn new(
        reference_irradiance_zeptojoules_per_square_nanometre_second: BigRational,
        aperture_square_nanometres: BigRational,
        absorptance: BigRational,
        conformational_coupling: BigRational,
    ) -> Result<Self, OpticalReceptorWorkError> {
        if reference_irradiance_zeptojoules_per_square_nanometre_second <= BigRational::zero()
            || aperture_square_nanometres <= BigRational::zero()
            || absorptance <= BigRational::zero()
            || absorptance > BigRational::one()
            || conformational_coupling <= BigRational::zero()
            || conformational_coupling > BigRational::one()
        {
            return Err(OpticalReceptorWorkError::InvalidAnatomy);
        }
        Ok(Self {
            reference_irradiance_zeptojoules_per_square_nanometre_second,
            aperture_square_nanometres,
            absorptance,
            conformational_coupling,
        })
    }
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) struct OpticalReceptorWorkSettlement {
    pub(crate) observed_duration_seconds: BigRational,
    pub(crate) integrated_irradiance_fraction_seconds: BigRational,
    pub(crate) incident_energy_zeptojoules: BigRational,
    pub(crate) absorbed_energy_zeptojoules: BigRational,
    pub(crate) transduced_energy_zeptojoules: BigRational,
    pub(crate) gate_work: GateWorkOccurrence,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) enum OpticalReceptorWorkError {
    Source(NeuronSourceAnchorError),
    InvalidAnatomy,
    NotSight,
    PhysicalQuantityMismatch,
    PhysicalUnitMismatch,
    TooFewSamples,
    SampleCardinalityChanged,
    SourceOutsideReferenceInterval,
    SourceClockDidNotAdvance,
    LatticeQuantumUnavailable,
    ResidueOutsideLattice,
    ResidueWidth,
    OpeningWindowUnavailable,
}

/// One quantized optical delivery under the ratified 2026-08-05 law: light
/// arrives as whole quanta on the receiving gate's existing dissipation
/// lattice. The quantum count is DERIVED from the unchanged continuous
/// `2·L·T` transduction law by exact-rational accumulation; the remainder is
/// retained per-site state (same discipline as the retained charge-carrier
/// phase residue), so delivered energy plus retained residue equals the exact
/// `2·L·T` integral over any interval sequence — no rounding loss and no
/// tuned coefficients.
///
/// Law 1 (threshold-integrated delivery, ratified 2026-08-05): the receptor
/// site INTEGRATES to threshold. The accumulator retains its energy across
/// intervals and delivers only when the accumulated whole-quantum count
/// reaches the receiving gate's own opening threshold; it then passes at most
/// the gate's own window cap and retains the exact remainder. Both numbers
/// are read from the gate's existing anatomy and state
/// (`gate_opening_quantum_window`) — no new constant. A dark interval adds
/// nothing, delivers nothing, and erases nothing: the law has no residue
/// decay term and none was added.
#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) struct QuantizedOpticalDelivery {
    pub(crate) delivered_quanta: u128,
    pub(crate) delivered_energy_zeptojoules: BigRational,
    pub(crate) successor_residue: ExactRational,
    pub(crate) gate_work: GateWorkOccurrence,
}

pub(crate) fn exact_rational_to_big(value: ExactRational) -> BigRational {
    let (numerator, denominator) = value.parts();
    BigRational::new(BigInt::from(numerator), BigInt::from(denominator))
}

fn big_to_exact_rational(value: &BigRational) -> Result<ExactRational, OpticalReceptorWorkError> {
    let numerator = value
        .numer()
        .to_i128()
        .ok_or(OpticalReceptorWorkError::ResidueWidth)?;
    let denominator = value
        .denom()
        .to_u128()
        .ok_or(OpticalReceptorWorkError::ResidueWidth)?;
    ExactRational::new(numerator, denominator)
        .map_err(|_| OpticalReceptorWorkError::ResidueWidth)
}

/// Integrate one interval's exact transduced energy into the per-site
/// accumulator and deliver whole lattice quanta only once the accumulated
/// count reaches the receiving gate's opening threshold. The predecessor
/// residue must be non-negative; the successor residue always is.
pub(crate) fn quantize_optical_delivery(
    transduced_energy_zeptojoules: &BigRational,
    predecessor_residue: ExactRational,
    lattice_quantum_zeptojoules: &BigRational,
    opening_threshold_quanta: u128,
    window_cap_quanta: u128,
) -> Result<QuantizedOpticalDelivery, OpticalReceptorWorkError> {
    if lattice_quantum_zeptojoules <= &BigRational::zero() {
        return Err(OpticalReceptorWorkError::LatticeQuantumUnavailable);
    }
    if opening_threshold_quanta == 0 {
        return Err(OpticalReceptorWorkError::OpeningWindowUnavailable);
    }
    if transduced_energy_zeptojoules.is_negative() {
        return Err(OpticalReceptorWorkError::SourceOutsideReferenceInterval);
    }
    let residue = exact_rational_to_big(predecessor_residue);
    if residue.is_negative() {
        return Err(OpticalReceptorWorkError::ResidueOutsideLattice);
    }
    let accumulated = residue + transduced_energy_zeptojoules;
    let accumulated_quanta = (&accumulated / lattice_quantum_zeptojoules)
        .floor()
        .to_integer()
        .to_u128()
        .ok_or(OpticalReceptorWorkError::ResidueWidth)?;
    // Threshold-integrated delivery: below the receiving gate's own opening
    // threshold NOTHING is delivered and everything is retained; at or above
    // it, at most the gate's own window cap is passed.
    let delivered_quanta = if accumulated_quanta < opening_threshold_quanta {
        0
    } else {
        accumulated_quanta.min(window_cap_quanta)
    };
    let delivered_energy_zeptojoules =
        lattice_quantum_zeptojoules * BigRational::from_integer(BigInt::from(delivered_quanta));
    let successor_residue_big = accumulated - &delivered_energy_zeptojoules;
    debug_assert!(!successor_residue_big.is_negative());
    let successor_residue = big_to_exact_rational(&successor_residue_big)?;
    Ok(QuantizedOpticalDelivery {
        delivered_quanta,
        gate_work: GateWorkOccurrence::new(-delivered_energy_zeptojoules.clone()),
        delivered_energy_zeptojoules,
        successor_residue,
    })
}

impl From<NeuronSourceAnchorError> for OpticalReceptorWorkError {
    fn from(value: NeuronSourceAnchorError) -> Self {
        Self::Source(value)
    }
}

fn settle_port(
    port: &JointSourcePortView,
    anatomy: &OpticalReceptorAnatomy,
) -> Result<OpticalReceptorWorkSettlement, OpticalReceptorWorkError> {
    if port.sense != 0 {
        return Err(OpticalReceptorWorkError::NotSight);
    }
    if port.physical_quantity != RETINAL_SPECTRAL_IRRADIANCE_QUANTITY {
        return Err(OpticalReceptorWorkError::PhysicalQuantityMismatch);
    }
    if port.physical_unit != RETINAL_REFERENCE_IRRADIANCE_UNIT {
        return Err(OpticalReceptorWorkError::PhysicalUnitMismatch);
    }
    if port.source_times.len() < 2 {
        return Err(OpticalReceptorWorkError::TooFewSamples);
    }
    if port.source_times.len() != port.exact_normalized_sources.len() {
        return Err(OpticalReceptorWorkError::SampleCardinalityChanged);
    }
    if port
        .exact_normalized_sources
        .iter()
        .any(|value| value < &BigRational::zero() || value > &BigRational::one())
    {
        return Err(OpticalReceptorWorkError::SourceOutsideReferenceInterval);
    }

    let mut integrated = BigRational::zero();
    for index in 0..port.source_times.len() - 1 {
        let duration = &port.source_times[index + 1] - &port.source_times[index];
        if duration <= BigRational::zero() {
            return Err(OpticalReceptorWorkError::SourceClockDidNotAdvance);
        }
        let mean = (&port.exact_normalized_sources[index]
            + &port.exact_normalized_sources[index + 1])
            / BigInt::from(2);
        integrated += mean * duration;
    }
    let observed_duration_seconds =
        port.source_times.last().unwrap() - port.source_times.first().unwrap();
    let incident_energy_zeptojoules = &integrated
        * &anatomy.reference_irradiance_zeptojoules_per_square_nanometre_second
        * &anatomy.aperture_square_nanometres;
    let absorbed_energy_zeptojoules = &incident_energy_zeptojoules * &anatomy.absorptance;
    let transduced_energy_zeptojoules =
        &absorbed_energy_zeptojoules * &anatomy.conformational_coupling;

    Ok(OpticalReceptorWorkSettlement {
        observed_duration_seconds,
        integrated_irradiance_fraction_seconds: integrated,
        incident_energy_zeptojoules,
        absorbed_energy_zeptojoules,
        gate_work: GateWorkOccurrence::new(-transduced_energy_zeptojoules.clone()),
        transduced_energy_zeptojoules,
    })
}

pub(crate) fn derive_optical_receptor_work(
    episode: &NativeJointSourceEpisode,
    perspective: JointNeuronPerspective<'_>,
    anatomy: &OpticalReceptorAnatomy,
) -> Result<OpticalReceptorWorkSettlement, OpticalReceptorWorkError> {
    let anchor = bind_neuron_source_anchor(episode, perspective)?;
    if anchor.sense() != PhysicalSourceSense::Sight {
        return Err(OpticalReceptorWorkError::NotSight);
    }
    let port = episode
        .joint_source_ports()
        .get(anchor.source_port_index())
        .ok_or(OpticalReceptorWorkError::Source(
            NeuronSourceAnchorError::SourcePortAbsent,
        ))?;
    settle_port(port, anatomy)
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::joint_source_episode::JointSourceCoordinate;

    fn exact(numerator: i64, denominator: i64) -> BigRational {
        BigRational::new(BigInt::from(numerator), BigInt::from(denominator))
    }

    fn anatomy() -> OpticalReceptorAnatomy {
        OpticalReceptorAnatomy::new(exact(4, 1), exact(1, 1), exact(1, 2), exact(1, 1)).unwrap()
    }

    fn port() -> JointSourcePortView {
        JointSourcePortView {
            sense: 0,
            topology_index: 0,
            sensor_id: "W1-retina".into(),
            substream_id: "retinal-cell-0-0-band-0".into(),
            coordinates: vec![JointSourceCoordinate {
                axis_id: "optical-band".into(),
                coordinate_id: "0".into(),
            }],
            physical_quantity: RETINAL_SPECTRAL_IRRADIANCE_QUANTITY.into(),
            physical_unit: RETINAL_REFERENCE_IRRADIANCE_UNIT.into(),
            relevance_rule: "source-only".into(),
            relevance_origin: None,
            input_map_id: "independent-test-map".into(),
            source_min: exact(0, 1),
            source_max: exact(1, 1),
            field_offset: exact(1, 1),
            field_scale: exact(1, 2),
            input_map_profile: vec![1],
            input_map_group_receipt: [0; 32],
            source_times: vec![exact(0, 1), exact(1, 1), exact(2, 1)],
            exact_normalized_sources: vec![exact(0, 1), exact(1, 2), exact(1, 1)],
            reported_phase_turns: vec![exact(0, 1); 3],
            source_relevances: vec![exact(1, 1); 3],
            dimensionless_fields: vec![exact(1, 1), exact(5, 4), exact(3, 2)],
        }
    }

    #[test]
    fn exact_retinal_energy_becomes_local_negative_gate_work() {
        let settled = settle_port(&port(), &anatomy()).unwrap();
        assert_eq!(settled.observed_duration_seconds, exact(2, 1));
        assert_eq!(settled.integrated_irradiance_fraction_seconds, exact(1, 1));
        assert_eq!(settled.incident_energy_zeptojoules, exact(4, 1));
        assert_eq!(settled.absorbed_energy_zeptojoules, exact(2, 1));
        assert_eq!(settled.transduced_energy_zeptojoules, exact(2, 1));
        assert!(!settled.gate_work.is_zero());
    }

    #[test]
    fn dsf_coordinate_changes_cannot_change_receptor_work() {
        let source = port();
        let first = settle_port(&source, &anatomy()).unwrap();
        let mut changed_field = source;
        changed_field.dimensionless_fields = vec![exact(-9, 1); 3];
        let second = settle_port(&changed_field, &anatomy()).unwrap();
        assert_eq!(first, second);
    }

    /// Ratification 2026-08-05 proof obligation 1: over arbitrary interval
    /// sequences, delivered-quanta × lattice-step + retained residue equals
    /// the exact-rational Σ 2·L·T with no rounding loss and no tuned
    /// constants. Luminances span the full 8-bit lattice (k/255), dwell
    /// durations are deliberately irregular, and the sequence includes dark
    /// intervals; every step is checked bit-exactly and the invariant
    /// `0 ≤ residue` is checked at every step.
    #[test]
    fn quantized_delivery_conserves_exact_2lt_over_arbitrary_interval_sequences() {
        let quantum = exact(1, 16);
        // (luminance numerator over 255, dwell numerator over dwell denominator)
        let sequence: &[(i64, i64, i64)] = &[
            (217, 1, 4),
            (0, 3, 4),
            (255, 1, 4),
            (1, 7, 8),
            (89, 251, 1000),
            (13, 1, 3),
            (0, 5, 1),
            (254, 1, 977),
            (127, 2, 7),
            (42, 13, 64),
            (255, 1, 1000000),
            (3, 999983, 1000000),
        ];
        let mut residue = ExactRational::new(0, 1).unwrap();
        let mut delivered_total = BigRational::zero();
        let mut exact_total = BigRational::zero();
        for (luminance_numerator, dwell_numerator, dwell_denominator) in sequence {
            // Unchanged ratified law: 2·L·T (transduction chain 4 × 1/2 × 1 = 2).
            let energy = exact(2, 1)
                * exact(*luminance_numerator, 255)
                * exact(*dwell_numerator, *dwell_denominator);
            exact_total += &energy;
            let delivery = quantize_optical_delivery(&energy, residue, &quantum, 17, 52).unwrap();
            delivered_total += &delivery.delivered_energy_zeptojoules;
            // Delivered energy is always a whole number of lattice quanta.
            assert_eq!(
                &delivery.delivered_energy_zeptojoules,
                &(&quantum * BigRational::from_integer(delivery.delivered_quanta.into()))
            );
            // Law 1: a delivery is either nothing at all or lies inside the
            // receiving gate's own opening window.
            assert!(
                delivery.delivered_quanta == 0
                    || (17..=52).contains(&delivery.delivered_quanta)
            );
            residue = delivery.successor_residue;
            let residue_big = exact_rational_to_big(residue);
            assert!(residue_big >= BigRational::zero());
            // Bit-exact conservation at EVERY step, not only at the end.
            assert_eq!(&delivered_total + &residue_big, exact_total);
        }
        // The sequence must have exercised both delivery and retention.
        assert!(delivered_total > BigRational::zero());
        assert!(exact_rational_to_big(residue) > BigRational::zero());
    }

    /// Law 1 proof obligation: a sequence that never reaches the receiving
    /// gate's opening threshold delivers EXACTLY ZERO and retains ALL of it,
    /// and dark intervals neither deliver nor erase the retained residue.
    /// These are the real served numbers: a 250 ms hop of the brightest real
    /// card site (L = 217/255) transduces 2·L·T ≈ 0.4255 zJ ≈ 6.8 lattice
    /// quanta, far under the 17-quantum barrier of a fresh gate.
    #[test]
    fn sub_threshold_sequences_deliver_nothing_and_retain_everything() {
        let quantum = exact(1, 16);
        let hop = exact(2, 1) * exact(217, 255) * exact(1, 4);
        let mut residue = ExactRational::new(0, 1).unwrap();
        let mut exact_total = BigRational::zero();
        // Two lit hops stay under the threshold (about 13.6 quanta).
        for _ in 0..2 {
            exact_total += &hop;
            let delivery = quantize_optical_delivery(&hop, residue, &quantum, 17, 52).unwrap();
            assert_eq!(delivery.delivered_quanta, 0);
            assert!(delivery.gate_work.is_zero());
            residue = delivery.successor_residue;
            assert_eq!(exact_rational_to_big(residue), exact_total);
        }
        // A dark interval delivers nothing and erases nothing.
        let dark =
            quantize_optical_delivery(&BigRational::zero(), residue, &quantum, 17, 52).unwrap();
        assert_eq!(dark.delivered_quanta, 0);
        assert_eq!(dark.successor_residue, residue);
        // The third lit hop crosses the threshold (about 20.4 quanta).
        exact_total += &hop;
        let crossed = quantize_optical_delivery(&hop, residue, &quantum, 17, 52).unwrap();
        assert_eq!(crossed.delivered_quanta, 20);
        assert_eq!(
            &crossed.delivered_energy_zeptojoules
                + exact_rational_to_big(crossed.successor_residue),
            exact_total
        );
    }

    /// Law 1 proof obligation: an accumulation beyond the receiving gate's
    /// own window cap passes exactly the cap and RETAINS the whole exact
    /// remainder — several quanta, not a sub-quantum crumb.
    #[test]
    fn accumulation_beyond_the_window_cap_delivers_the_cap_and_retains_the_rest() {
        let quantum = exact(1, 16);
        let energy = &quantum * BigRational::from_integer(70.into()) + exact(1, 32);
        let delivery = quantize_optical_delivery(
            &energy,
            ExactRational::new(0, 1).unwrap(),
            &quantum,
            17,
            52,
        )
        .unwrap();
        assert_eq!(delivery.delivered_quanta, 52);
        assert_eq!(
            exact_rational_to_big(delivery.successor_residue),
            &quantum * BigRational::from_integer(18.into()) + exact(1, 32)
        );
        assert_eq!(
            &delivery.delivered_energy_zeptojoules
                + exact_rational_to_big(delivery.successor_residue),
            energy
        );
    }

    #[test]
    fn quantized_delivery_refuses_unlawful_residue_and_lattice() {
        let quantum = exact(1, 16);
        let energy = exact(1, 8);
        assert_eq!(
            quantize_optical_delivery(
                &energy,
                ExactRational::new(-1, 32).unwrap(),
                &quantum,
                17,
                52
            ),
            Err(OpticalReceptorWorkError::ResidueOutsideLattice)
        );
        assert_eq!(
            quantize_optical_delivery(
                &energy,
                ExactRational::new(0, 1).unwrap(),
                &exact(0, 1),
                17,
                52
            ),
            Err(OpticalReceptorWorkError::LatticeQuantumUnavailable)
        );
        assert_eq!(
            quantize_optical_delivery(
                &exact(-1, 16),
                ExactRational::new(0, 1).unwrap(),
                &quantum,
                17,
                52
            ),
            Err(OpticalReceptorWorkError::SourceOutsideReferenceInterval)
        );
        assert_eq!(
            quantize_optical_delivery(
                &energy,
                ExactRational::new(0, 1).unwrap(),
                &quantum,
                0,
                52
            ),
            Err(OpticalReceptorWorkError::OpeningWindowUnavailable)
        );
    }

    #[test]
    fn wrong_unit_and_negative_irradiance_are_refused() {
        let mut wrong_unit = port();
        wrong_unit.physical_unit = "dimensionless".into();
        assert_eq!(
            settle_port(&wrong_unit, &anatomy()),
            Err(OpticalReceptorWorkError::PhysicalUnitMismatch)
        );

        let mut negative = port();
        negative.exact_normalized_sources[1] = exact(-1, 2);
        assert_eq!(
            settle_port(&negative, &anatomy()),
            Err(OpticalReceptorWorkError::SourceOutsideReferenceInterval)
        );
    }
}
