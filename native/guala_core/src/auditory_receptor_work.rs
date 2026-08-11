//! Exact local conversion from one reached cochlear source occurrence to gate
//! work — the auditory transduction law
//! (`docs/GUALA_AUDITORY_TRANSDUCTION_DESIGN_2026-08-06.md`, Laws A1–A6).
//!
//! # Why sound joins light's law rather than the vestibular chain
//!
//! Sound is mechanical in origin, so the vestibular gating-spring chain looks
//! like the obvious home for it, and it is the wrong one for a reason that is
//! itself physics.  Sound has zero mean and its period (0.1–10 ms for speech)
//! is orders of magnitude shorter than a settlement interval, so a SIGNED
//! pressure bias evaluated once per interval integrates to approximately zero:
//! the half cycles cancel, and a loud sound cancels no less exactly than a
//! quiet one.  What survives averaging over many acoustic cycles is acoustic
//! INTENSITY, `I = p²/Z`, which is quadratic and therefore never negative.
//!
//! So the auditory law is the optical law with one substitution in the
//! integrand — `mean(sᵢ², sᵢ₊₁²)` where light has `mean(Lᵢ, Lᵢ₊₁)` — and
//! nothing else: the same exact-rational trapezoid, the same clock-advance
//! refusal, the same sample-cardinality refusal, the same declared receptor
//! anatomy shape, and the same shared quantized threshold-integrated delivery
//! (`receptor_quantum_delivery`).  DSF coordinates do not enter this
//! conversion.
//!
//! # Rectification is a consequence, not a mechanism (Law A3)
//!
//! There is no rectifier here, no envelope detector, no absolute value, and no
//! per-sample threshold.  Non-negativity is a THEOREM of the law: `s² ≥ 0` for
//! every lawful sample, so transduced energy is non-negative, so the shared
//! delivery law's residue invariant holds unchanged.  Silence delivers exactly
//! zero because zero squared is zero — the same lawful state darkness is for
//! light.
//!
//! # The transported quantity
//!
//! Each cochlear port carries its own band's normalized root-mean-square
//! pressure over the retained instant — the declared place coding of the
//! basilar membrane's travelling wave, computed in the sensor layer where the
//! camera's luminance extraction already lives.  Squaring a band RMS gives that
//! band's mean-square pressure, which is exactly the quantity `I = ⟨p²⟩/Z`
//! needs.  The law nonetheless admits the full signed unit interval `[-1, 1]`,
//! because a port carrying an instantaneous signed pressure waveform is equally
//! lawful under it and squares to the same non-negative energy.
//!
//! # The single composite constant (Law A5)
//!
//! `K = p_ref² · A_ear · transmission · coupling / Z_medium` is not four free
//! numbers.  Nothing in this organism's pipeline measures pascals — the samples
//! are normalized to their capture's own full scale — so `p_ref` is not a
//! measurement of the world, it is the declaration of the organism's full-scale
//! sensitivity.  It is pinned by OPTICAL PARITY: full-scale sound is exactly as
//! energetic to this organism as full-scale light, which introduces no number
//! that is not already in the tree.  The authored anatomy is therefore the
//! optical anatomy's own factors (see
//! `resident_cognitive_formation::exact_auditory_receptor_anatomy`); only their
//! product is a physical claim.

use num_bigint::BigInt;
use num_rational::BigRational;
use num_traits::{One, Zero};

use crate::complete_neuron::GateWorkOccurrence;
use crate::exact_rational::ExactRational;
use crate::joint_source_episode::{JointSourcePortView, NativeJointSourceEpisode};
use crate::joint_uf_neuron_boundary::JointNeuronPerspective;
use crate::neuron_source_anchor::{
    bind_neuron_source_anchor, NeuronSourceAnchorError, PhysicalSourceSense,
};
use crate::receptor_quantum_delivery::{
    quantize_receptor_delivery, QuantizedReceptorDelivery, ReceptorDeliveryError,
};

/// The declared acoustic quantity a cochlear port carries: the normalized
/// root-mean-square pressure of ONE tonotopic band of the ambient field over
/// the retained instant.  It is named for what the number is, which is the
/// whole point of replacing the served `normalized_physical_excitation` (a
/// statement that a number was normalized, not a physical quantity).
pub(crate) const COCHLEAR_BAND_PRESSURE_QUANTITY: &str = "cochlear-band-pressure";
pub(crate) const COCHLEAR_REFERENCE_PRESSURE_UNIT: &str =
    "fraction-of-declared-cochlear-reference-pressure";

#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) struct AuditoryReceptorAnatomy {
    reference_intensity_zeptojoules_per_square_nanometre_second: BigRational,
    aperture_square_nanometres: BigRational,
    middle_ear_transmission: BigRational,
    conformational_coupling: BigRational,
}

impl AuditoryReceptorAnatomy {
    pub(crate) fn new(
        reference_intensity_zeptojoules_per_square_nanometre_second: BigRational,
        aperture_square_nanometres: BigRational,
        middle_ear_transmission: BigRational,
        conformational_coupling: BigRational,
    ) -> Result<Self, AuditoryReceptorWorkError> {
        if reference_intensity_zeptojoules_per_square_nanometre_second <= BigRational::zero()
            || aperture_square_nanometres <= BigRational::zero()
            || middle_ear_transmission <= BigRational::zero()
            || middle_ear_transmission > BigRational::one()
            || conformational_coupling <= BigRational::zero()
            || conformational_coupling > BigRational::one()
        {
            return Err(AuditoryReceptorWorkError::InvalidAnatomy);
        }
        Ok(Self {
            reference_intensity_zeptojoules_per_square_nanometre_second,
            aperture_square_nanometres,
            middle_ear_transmission,
            conformational_coupling,
        })
    }

    /// The single composite constant `K` of Law A1, in zeptojoules per
    /// (dimensionless² · second).  Derived, never authored separately.
    pub(crate) fn composite_transduction_constant(&self) -> BigRational {
        &self.reference_intensity_zeptojoules_per_square_nanometre_second
            * &self.aperture_square_nanometres
            * &self.middle_ear_transmission
            * &self.conformational_coupling
    }
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) struct AuditoryReceptorWorkSettlement {
    pub(crate) observed_duration_seconds: BigRational,
    pub(crate) integrated_squared_pressure_fraction_seconds: BigRational,
    pub(crate) incident_energy_zeptojoules: BigRational,
    pub(crate) absorbed_energy_zeptojoules: BigRational,
    pub(crate) transduced_energy_zeptojoules: BigRational,
    pub(crate) gate_work: GateWorkOccurrence,
}

/// Law A6 — the refusal surface.  Mirrors `OpticalReceptorWorkError`
/// one-for-one; the only difference is the admitted source range.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) enum AuditoryReceptorWorkError {
    Source(NeuronSourceAnchorError),
    InvalidAnatomy,
    NotSound,
    PhysicalQuantityMismatch,
    PhysicalUnitMismatch,
    TooFewSamples,
    SampleCardinalityChanged,
    SourceOutsideReferenceInterval,
    SourceClockDidNotAdvance,
    SourceIntervalAbsent,
    LatticeQuantumUnavailable,
    ResidueOutsideLattice,
    ResidueWidth,
    OpeningWindowUnavailable,
}

impl From<NeuronSourceAnchorError> for AuditoryReceptorWorkError {
    fn from(value: NeuronSourceAnchorError) -> Self {
        Self::Source(value)
    }
}

impl From<ReceptorDeliveryError> for AuditoryReceptorWorkError {
    fn from(value: ReceptorDeliveryError) -> Self {
        match value {
            ReceptorDeliveryError::TransducedEnergyNegative => {
                Self::SourceOutsideReferenceInterval
            }
            ReceptorDeliveryError::LatticeQuantumUnavailable => Self::LatticeQuantumUnavailable,
            ReceptorDeliveryError::ResidueOutsideLattice => Self::ResidueOutsideLattice,
            ReceptorDeliveryError::ResidueWidth => Self::ResidueWidth,
            ReceptorDeliveryError::OpeningWindowUnavailable => Self::OpeningWindowUnavailable,
        }
    }
}

/// The auditory entry point into the shared, modality-blind delivery law
/// (Law A4).  It adds no arithmetic: it forwards the call and restates
/// refusals on this law's own error surface.  `quantize_optical_delivery` is
/// the same call on the same function.
pub(crate) fn quantize_auditory_delivery(
    transduced_energy_zeptojoules: &BigRational,
    predecessor_residue: ExactRational,
    lattice_quantum_zeptojoules: &BigRational,
    opening_threshold_quanta: u128,
    window_cap_quanta: u128,
) -> Result<QuantizedReceptorDelivery, AuditoryReceptorWorkError> {
    quantize_receptor_delivery(
        transduced_energy_zeptojoules,
        predecessor_residue,
        lattice_quantum_zeptojoules,
        opening_threshold_quanta,
        window_cap_quanta,
    )
    .map_err(AuditoryReceptorWorkError::from)
}

fn settle_port_range(
    port: &JointSourcePortView,
    anatomy: &AuditoryReceptorAnatomy,
    first_sample: usize,
    last_sample: usize,
) -> Result<AuditoryReceptorWorkSettlement, AuditoryReceptorWorkError> {
    if port.sense != PhysicalSourceSense::Sound.declared_layer() {
        return Err(AuditoryReceptorWorkError::NotSound);
    }
    if port.physical_quantity != COCHLEAR_BAND_PRESSURE_QUANTITY {
        return Err(AuditoryReceptorWorkError::PhysicalQuantityMismatch);
    }
    if port.physical_unit != COCHLEAR_REFERENCE_PRESSURE_UNIT {
        return Err(AuditoryReceptorWorkError::PhysicalUnitMismatch);
    }
    if port.source_times.len() < 2 {
        return Err(AuditoryReceptorWorkError::TooFewSamples);
    }
    if port.source_times.len() != port.exact_normalized_sources.len() {
        return Err(AuditoryReceptorWorkError::SampleCardinalityChanged);
    }
    if first_sample >= last_sample || last_sample >= port.source_times.len() {
        return Err(AuditoryReceptorWorkError::SourceIntervalAbsent);
    }
    // Law A6: pressure is signed, so the admitted range is the FULL signed
    // unit interval — unlike irradiance, which cannot be negative.  The law
    // squares it, so the sign never reaches the gate.
    if port.exact_normalized_sources[first_sample..=last_sample]
        .iter()
        .any(|value| value < &-BigRational::one() || value > &BigRational::one())
    {
        return Err(AuditoryReceptorWorkError::SourceOutsideReferenceInterval);
    }

    // Law A1: exact trapezoidal integral of the SQUARED normalized pressure.
    let mut integrated = BigRational::zero();
    for index in first_sample..last_sample {
        let duration = &port.source_times[index + 1] - &port.source_times[index];
        if duration <= BigRational::zero() {
            return Err(AuditoryReceptorWorkError::SourceClockDidNotAdvance);
        }
        let left = &port.exact_normalized_sources[index] * &port.exact_normalized_sources[index];
        let right =
            &port.exact_normalized_sources[index + 1] * &port.exact_normalized_sources[index + 1];
        let mean = (left + right) / BigInt::from(2);
        integrated += mean * duration;
    }
    let observed_duration_seconds =
        &port.source_times[last_sample] - &port.source_times[first_sample];
    let incident_energy_zeptojoules = &integrated
        * &anatomy.reference_intensity_zeptojoules_per_square_nanometre_second
        * &anatomy.aperture_square_nanometres;
    // Law A2: middle-ear transmission is what absorptance is on the optical
    // side; conformational coupling is the same conversion into the gate's
    // conformational coordinate.
    let absorbed_energy_zeptojoules =
        &incident_energy_zeptojoules * &anatomy.middle_ear_transmission;
    let transduced_energy_zeptojoules =
        &absorbed_energy_zeptojoules * &anatomy.conformational_coupling;

    Ok(AuditoryReceptorWorkSettlement {
        observed_duration_seconds,
        integrated_squared_pressure_fraction_seconds: integrated,
        incident_energy_zeptojoules,
        absorbed_energy_zeptojoules,
        gate_work: GateWorkOccurrence::new(-transduced_energy_zeptojoules.clone()),
        transduced_energy_zeptojoules,
    })
}

pub(crate) fn settle_port(
    port: &JointSourcePortView,
    anatomy: &AuditoryReceptorAnatomy,
) -> Result<AuditoryReceptorWorkSettlement, AuditoryReceptorWorkError> {
    settle_port_range(port, anatomy, 0, port.source_times.len().saturating_sub(1))
}

pub(crate) fn derive_auditory_receptor_work(
    episode: &NativeJointSourceEpisode,
    perspective: JointNeuronPerspective<'_>,
    anatomy: &AuditoryReceptorAnatomy,
) -> Result<AuditoryReceptorWorkSettlement, AuditoryReceptorWorkError> {
    let anchor = bind_neuron_source_anchor(episode, perspective)?;
    if anchor.sense() != PhysicalSourceSense::Sound {
        return Err(AuditoryReceptorWorkError::NotSound);
    }
    let port = episode
        .joint_source_ports()
        .get(anchor.source_port_index())
        .ok_or(AuditoryReceptorWorkError::Source(
            NeuronSourceAnchorError::SourcePortAbsent,
        ))?;
    settle_port(port, anatomy)
}

pub(crate) fn derive_auditory_receptor_sample_range_work(
    episode: &NativeJointSourceEpisode,
    perspective: JointNeuronPerspective<'_>,
    anatomy: &AuditoryReceptorAnatomy,
    first_sample: usize,
    last_sample: usize,
) -> Result<AuditoryReceptorWorkSettlement, AuditoryReceptorWorkError> {
    let anchor = bind_neuron_source_anchor(episode, perspective)?;
    if anchor.sense() != PhysicalSourceSense::Sound {
        return Err(AuditoryReceptorWorkError::NotSound);
    }
    let port = episode
        .joint_source_ports()
        .get(anchor.source_port_index())
        .ok_or(AuditoryReceptorWorkError::Source(
            NeuronSourceAnchorError::SourcePortAbsent,
        ))?;
    settle_port_range(port, anatomy, first_sample, last_sample)
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::joint_source_episode::JointSourceCoordinate;
    use crate::receptor_quantum_delivery::exact_rational_to_big;

    fn exact(numerator: i64, denominator: i64) -> BigRational {
        BigRational::new(BigInt::from(numerator), BigInt::from(denominator))
    }

    /// Optical parity (Law A5): the same four factors the retinal anatomy
    /// declares, so `K` = 2 zJ per (dimensionless² · second) exactly.
    fn anatomy() -> AuditoryReceptorAnatomy {
        AuditoryReceptorAnatomy::new(exact(4, 1), exact(1, 1), exact(1, 2), exact(1, 1)).unwrap()
    }

    fn port_with(sources: Vec<BigRational>) -> JointSourcePortView {
        let count = sources.len();
        JointSourcePortView {
            sense: 1,
            topology_index: 0,
            sensor_id: "W1-cochlea".into(),
            substream_id: "cochlear-ear-0-band-0".into(),
            coordinates: vec![JointSourceCoordinate {
                axis_id: "cochlear-band".into(),
                coordinate_id: "0".into(),
            }],
            physical_quantity: COCHLEAR_BAND_PRESSURE_QUANTITY.into(),
            physical_unit: COCHLEAR_REFERENCE_PRESSURE_UNIT.into(),
            relevance_rule: "source-only".into(),
            relevance_origin: None,
            input_map_id: "independent-test-map".into(),
            source_min: exact(-1, 1),
            source_max: exact(1, 1),
            field_offset: exact(1, 1),
            field_scale: exact(1, 2),
            input_map_profile: vec![1],
            input_map_group_receipt: [0; 32],
            source_times: (0..count).map(|index| exact(index as i64, 1)).collect(),
            exact_normalized_sources: sources,
            reported_phase_turns: vec![exact(0, 1); count],
            source_relevances: vec![exact(1, 1); count],
            dimensionless_fields: vec![exact(1, 1); count],
        }
    }

    /// Law A1: the integrand is the SQUARE of the normalized pressure,
    /// integrated exactly by trapezoid, then scaled by declared anatomy.
    /// Full-scale pressure over one second transduces exactly K = 2 zJ.
    #[test]
    fn exact_squared_pressure_becomes_local_negative_gate_work() {
        let settled = settle_port(
            &port_with(vec![exact(1, 1), exact(1, 1), exact(1, 1)]),
            &anatomy(),
        )
        .unwrap();
        assert_eq!(settled.observed_duration_seconds, exact(2, 1));
        assert_eq!(
            settled.integrated_squared_pressure_fraction_seconds,
            exact(2, 1)
        );
        assert_eq!(settled.incident_energy_zeptojoules, exact(8, 1));
        assert_eq!(settled.absorbed_energy_zeptojoules, exact(4, 1));
        assert_eq!(settled.transduced_energy_zeptojoules, exact(4, 1));
        assert!(!settled.gate_work.is_zero());
        assert_eq!(anatomy().composite_transduction_constant(), exact(2, 1));
    }

    /// Law A3 — the load-bearing theorem.  A zero-mean signed waveform is NOT
    /// cancelled: it transduces exactly the same energy as its rectified
    /// twin, with no rectifier anywhere in the law.  This is the property
    /// that makes a mechanical-bias transcription of the vestibular chain
    /// wrong for sound.
    #[test]
    fn a_zero_mean_signed_waveform_transduces_the_same_energy_as_its_rectified_twin() {
        let signed = settle_port(
            &port_with(vec![exact(1, 1), exact(-1, 1), exact(1, 1), exact(-1, 1)]),
            &anatomy(),
        )
        .unwrap();
        let rectified = settle_port(
            &port_with(vec![exact(1, 1), exact(1, 1), exact(1, 1), exact(1, 1)]),
            &anatomy(),
        )
        .unwrap();
        assert_eq!(
            signed.transduced_energy_zeptojoules,
            rectified.transduced_energy_zeptojoules
        );
        assert!(signed.transduced_energy_zeptojoules > BigRational::zero());
        // The signed mean of that waveform is exactly zero: a bias law would
        // have delivered nothing at all.
        let mean: BigRational = [exact(1, 1), exact(-1, 1), exact(1, 1), exact(-1, 1)]
            .into_iter()
            .fold(BigRational::zero(), |total, value| total + value);
        assert_eq!(mean, BigRational::zero());
    }

    /// Law A3: silence is a lawful state that delivers exactly nothing.
    #[test]
    fn silence_transduces_exactly_zero() {
        let settled = settle_port(
            &port_with(vec![exact(0, 1), exact(0, 1), exact(0, 1)]),
            &anatomy(),
        )
        .unwrap();
        assert!(settled.transduced_energy_zeptojoules.is_zero());
        assert!(settled.gate_work.is_zero());
    }

    /// Law A1/A3 amplitude law: quarter energy for half amplitude (−6 dB),
    /// hundredth energy for a tenth.  Exact rationals, no tolerance.
    #[test]
    fn transduced_energy_is_exactly_quadratic_in_amplitude() {
        let full = settle_port(
            &port_with(vec![exact(1, 1), exact(1, 1), exact(1, 1)]),
            &anatomy(),
        )
        .unwrap()
        .transduced_energy_zeptojoules;
        let half = settle_port(
            &port_with(vec![exact(1, 2), exact(1, 2), exact(1, 2)]),
            &anatomy(),
        )
        .unwrap()
        .transduced_energy_zeptojoules;
        let tenth = settle_port(
            &port_with(vec![exact(1, 10), exact(1, 10), exact(1, 10)]),
            &anatomy(),
        )
        .unwrap()
        .transduced_energy_zeptojoules;
        assert_eq!(&half * BigInt::from(4), full);
        assert_eq!(&tenth * BigInt::from(100), full);
    }

    #[test]
    fn dsf_coordinate_changes_cannot_change_receptor_work() {
        let source = port_with(vec![exact(0, 1), exact(1, 2), exact(1, 1)]);
        let first = settle_port(&source, &anatomy()).unwrap();
        let mut changed_field = source;
        changed_field.dimensionless_fields = vec![exact(-9, 1); 3];
        let second = settle_port(&changed_field, &anatomy()).unwrap();
        assert_eq!(first, second);
    }

    /// Law A6: every refusal is a refusal, never a clamp or a fallback.
    #[test]
    fn the_refusal_surface_refuses_without_fallback() {
        let base = || port_with(vec![exact(0, 1), exact(1, 2), exact(1, 1)]);

        let mut wrong_sense = base();
        wrong_sense.sense = 0;
        assert_eq!(
            settle_port(&wrong_sense, &anatomy()),
            Err(AuditoryReceptorWorkError::NotSound)
        );

        let mut wrong_quantity = base();
        wrong_quantity.physical_quantity = "normalized_physical_excitation".into();
        assert_eq!(
            settle_port(&wrong_quantity, &anatomy()),
            Err(AuditoryReceptorWorkError::PhysicalQuantityMismatch)
        );

        let mut wrong_unit = base();
        wrong_unit.physical_unit = "normalized_binary64".into();
        assert_eq!(
            settle_port(&wrong_unit, &anatomy()),
            Err(AuditoryReceptorWorkError::PhysicalUnitMismatch)
        );

        let mut one_sample = base();
        one_sample.source_times.truncate(1);
        one_sample.exact_normalized_sources.truncate(1);
        assert_eq!(
            settle_port(&one_sample, &anatomy()),
            Err(AuditoryReceptorWorkError::TooFewSamples)
        );

        let mut mismatched = base();
        mismatched.exact_normalized_sources.truncate(2);
        assert_eq!(
            settle_port(&mismatched, &anatomy()),
            Err(AuditoryReceptorWorkError::SampleCardinalityChanged)
        );

        let mut out_of_range = base();
        out_of_range.exact_normalized_sources[1] = exact(-3, 2);
        assert_eq!(
            settle_port(&out_of_range, &anatomy()),
            Err(AuditoryReceptorWorkError::SourceOutsideReferenceInterval)
        );

        let mut stalled_clock = base();
        stalled_clock.source_times[1] = exact(0, 1);
        assert_eq!(
            settle_port(&stalled_clock, &anatomy()),
            Err(AuditoryReceptorWorkError::SourceClockDidNotAdvance)
        );

        // A signed sample INSIDE [-1, 1] is lawful — this is the one place
        // the acoustic law is deliberately wider than the optical one.
        let mut signed = base();
        signed.exact_normalized_sources[1] = exact(-1, 1);
        assert!(settle_port(&signed, &anatomy()).is_ok());

        assert_eq!(
            AuditoryReceptorAnatomy::new(exact(4, 1), exact(1, 1), exact(3, 2), exact(1, 1)),
            Err(AuditoryReceptorWorkError::InvalidAnatomy)
        );
        assert_eq!(
            AuditoryReceptorAnatomy::new(exact(0, 1), exact(1, 1), exact(1, 2), exact(1, 1)),
            Err(AuditoryReceptorWorkError::InvalidAnatomy)
        );
    }

    /// Proof obligation P1 (auditory): over an arbitrary interval sequence of
    /// real signed pressures including silences and full-scale clipping,
    /// delivered quanta × lattice step + retained residue equals the exact
    /// Σ K·∫s²dt at EVERY step, and the residue is never negative.  The
    /// delivery machinery is the shared one, unmodified.
    #[test]
    fn quantized_auditory_delivery_conserves_the_exact_integral_at_every_step() {
        let quantum = exact(1, 16);
        let sequences: &[&[(i64, i64)]] = &[
            &[(0, 1), (1, 1), (-1, 1), (1, 2), (0, 1), (-3, 4), (1, 1)],
            &[(1, 100), (-1, 100), (1, 50), (0, 1), (0, 1), (1, 1000)],
            &[(1, 1), (1, 1), (1, 1), (1, 1), (1, 1), (1, 1)],
        ];
        let mut residue = ExactRational::new(0, 1).unwrap();
        let mut delivered_total = BigRational::zero();
        let mut exact_total = BigRational::zero();
        let mut deliveries = 0_u32;
        for sequence in sequences {
            for window in sequence.windows(3) {
                let sources = window
                    .iter()
                    .map(|(numerator, denominator)| exact(*numerator, *denominator))
                    .collect::<Vec<_>>();
                let settled = settle_port(&port_with(sources), &anatomy()).unwrap();
                assert!(settled.transduced_energy_zeptojoules >= BigRational::zero());
                exact_total += &settled.transduced_energy_zeptojoules;
                let delivery = quantize_auditory_delivery(
                    &settled.transduced_energy_zeptojoules,
                    residue,
                    &quantum,
                    17,
                    52,
                )
                .unwrap();
                if delivery.delivered_quanta > 0 {
                    deliveries += 1;
                    assert!((17..=52).contains(&delivery.delivered_quanta));
                }
                delivered_total += &delivery.delivered_energy_zeptojoules;
                residue = delivery.successor_residue;
                let residue_big = exact_rational_to_big(residue);
                assert!(residue_big >= BigRational::zero());
                assert_eq!(&delivered_total + &residue_big, exact_total);
            }
        }
        assert!(deliveries > 0);
    }

    /// Proof obligation P3 (auditory): a silent interval delivers exactly
    /// zero, changes nothing, and ERASES nothing — the accumulator has no
    /// decay term and none was added.
    #[test]
    fn a_silent_interval_delivers_nothing_and_erases_nothing() {
        let quantum = exact(1, 16);
        let lit = settle_port(
            &port_with(vec![exact(1, 4), exact(1, 4), exact(1, 4)]),
            &anatomy(),
        )
        .unwrap();
        let first = quantize_auditory_delivery(
            &lit.transduced_energy_zeptojoules,
            ExactRational::new(0, 1).unwrap(),
            &quantum,
            17,
            52,
        )
        .unwrap();
        assert_eq!(first.delivered_quanta, 0);
        let silence = settle_port(
            &port_with(vec![exact(0, 1), exact(0, 1), exact(0, 1)]),
            &anatomy(),
        )
        .unwrap();
        let second = quantize_auditory_delivery(
            &silence.transduced_energy_zeptojoules,
            first.successor_residue,
            &quantum,
            17,
            52,
        )
        .unwrap();
        assert_eq!(second.delivered_quanta, 0);
        assert_eq!(second.successor_residue, first.successor_residue);
    }
}
