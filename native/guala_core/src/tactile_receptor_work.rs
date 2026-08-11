//! Exact local conversion from one reached contact-sheet source occurrence to
//! gate work — the tactile transduction law.
//!
//! # Why touch joins light's law rather than the vestibular chain
//!
//! The vestibular gating-spring chain is the substrate's other mechanical
//! path, and it is the wrong home for contact for the same structural reason
//! sound could not use it, arrived at from the opposite direction.  The
//! vestibular chain transduces a SIGNED displacement of a hair bundle: it is
//! built to report which way a thing moved.  A card resting against a contact
//! sheet does not move.  What it does is OCCUPY: at each declared place of the
//! sheet, either some of the card's footprint is there or none of it is.  That
//! occupancy is a non-negative, static, area-valued quantity, and integrating
//! it over the dwell is exactly what the optical law already does with
//! luminance.
//!
//! So the tactile law is the optical law with one substitution in the
//! integrand — `mean(cᵢ, cᵢ₊₁)` where light has `mean(Lᵢ, Lᵢ₊₁)`, both of
//! them the plain trapezoid of a non-negative normalized occupancy — and
//! nothing else: the same exact-rational trapezoid, the same clock-advance
//! refusal, the same sample-cardinality refusal, the same declared receptor
//! anatomy shape, and the same shared quantized threshold-integrated delivery
//! (`receptor_quantum_delivery`).  DSF coordinates do not enter this
//! conversion.  Sound needed a squared integrand because acoustic pressure
//! oscillates around zero and would cancel; contact never changes sign, so it
//! needs no such treatment and none is applied.
//!
//! # Non-negativity is a boundary refusal, not a rectifier (Law T3)
//!
//! There is no rectifier here, no absolute value, and no per-sample threshold.
//! A contact fraction is the fraction of a declared receptor site's own area
//! that the touched object's footprint covers, so it lies in `[0, 1]` by
//! construction and anything outside that interval is refused at the boundary
//! exactly as an out-of-range irradiance is.  NO CONTACT delivers exactly zero
//! because zero times anything is zero — the same lawful state darkness is for
//! light and silence is for sound.  A released card is not an absent sense.
//!
//! # The transported quantity
//!
//! Each contact-sheet port carries the exact area fraction of its own declared
//! patch that the touched object's footprint covers over the retained instant.
//! It is computed in the sensor layer, where the camera's luminance extraction
//! already lives, from the object's OWN DECLARED GEOMETRY — for a card, the
//! integer raster dimensions its manifest already declares — and never from
//! the object's picture content.  Ink is flat.  What touch reports about a
//! flat rectangle is its outline: full contact inside the footprint, exactly
//! zero outside it, and a partial fraction at the sites the edge crosses.
//!
//! # The single composite constant (Law T5)
//!
//! `K = σ_ref · A_site · compliance · coupling` is not four free numbers.
//! Nothing in this organism's pipeline measures pascals or newtons — the
//! transported number is a fraction of a site's own declared area — so the
//! declared reference contact stress is not a measurement of the world, it is
//! the declaration of the organism's full-scale sensitivity.  It is pinned by
//! OPTICAL PARITY, exactly as the auditory constant is (auditory transduction
//! design 2026-08-06, Law A5): full contact is exactly as energetic to this
//! organism as full-scale light, which introduces no number that is not
//! already in the tree.  The authored anatomy is therefore the optical
//! anatomy's own factors (see
//! `resident_cognitive_formation::exact_tactile_receptor_anatomy`); only their
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

/// The declared tactile quantity a contact-sheet port carries: the fraction of
/// ONE declared contact site's own area that the touched object's footprint
/// covers over the retained instant.  It is named for what the number is.
pub(crate) const CONTACT_SITE_OCCUPANCY_QUANTITY: &str = "contact-site-occupancy";
pub(crate) const CONTACT_REFERENCE_OCCUPANCY_UNIT: &str =
    "fraction-of-declared-contact-site-area";

#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) struct TactileReceptorAnatomy {
    reference_contact_stress_zeptojoules_per_square_nanometre_second: BigRational,
    site_area_square_nanometres: BigRational,
    membrane_compliance: BigRational,
    conformational_coupling: BigRational,
}

impl TactileReceptorAnatomy {
    pub(crate) fn new(
        reference_contact_stress_zeptojoules_per_square_nanometre_second: BigRational,
        site_area_square_nanometres: BigRational,
        membrane_compliance: BigRational,
        conformational_coupling: BigRational,
    ) -> Result<Self, TactileReceptorWorkError> {
        if reference_contact_stress_zeptojoules_per_square_nanometre_second <= BigRational::zero()
            || site_area_square_nanometres <= BigRational::zero()
            || membrane_compliance <= BigRational::zero()
            || membrane_compliance > BigRational::one()
            || conformational_coupling <= BigRational::zero()
            || conformational_coupling > BigRational::one()
        {
            return Err(TactileReceptorWorkError::InvalidAnatomy);
        }
        Ok(Self {
            reference_contact_stress_zeptojoules_per_square_nanometre_second,
            site_area_square_nanometres,
            membrane_compliance,
            conformational_coupling,
        })
    }

    /// The single composite constant `K` of Law T1, in zeptojoules per
    /// (dimensionless · second).  Derived, never authored separately.
    pub(crate) fn composite_transduction_constant(&self) -> BigRational {
        &self.reference_contact_stress_zeptojoules_per_square_nanometre_second
            * &self.site_area_square_nanometres
            * &self.membrane_compliance
            * &self.conformational_coupling
    }
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) struct TactileReceptorWorkSettlement {
    pub(crate) observed_duration_seconds: BigRational,
    pub(crate) integrated_occupancy_fraction_seconds: BigRational,
    pub(crate) incident_energy_zeptojoules: BigRational,
    pub(crate) absorbed_energy_zeptojoules: BigRational,
    pub(crate) transduced_energy_zeptojoules: BigRational,
    pub(crate) gate_work: GateWorkOccurrence,
}

/// Law T6 — the refusal surface.  Mirrors `OpticalReceptorWorkError`
/// one-for-one.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) enum TactileReceptorWorkError {
    Source(NeuronSourceAnchorError),
    InvalidAnatomy,
    NotTouch,
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

impl From<NeuronSourceAnchorError> for TactileReceptorWorkError {
    fn from(value: NeuronSourceAnchorError) -> Self {
        Self::Source(value)
    }
}

impl From<ReceptorDeliveryError> for TactileReceptorWorkError {
    fn from(value: ReceptorDeliveryError) -> Self {
        match value {
            ReceptorDeliveryError::TransducedEnergyNegative => Self::SourceOutsideReferenceInterval,
            ReceptorDeliveryError::LatticeQuantumUnavailable => Self::LatticeQuantumUnavailable,
            ReceptorDeliveryError::ResidueOutsideLattice => Self::ResidueOutsideLattice,
            ReceptorDeliveryError::ResidueWidth => Self::ResidueWidth,
            ReceptorDeliveryError::OpeningWindowUnavailable => Self::OpeningWindowUnavailable,
        }
    }
}

/// The tactile entry point into the shared, modality-blind delivery law
/// (Law T4).  It adds no arithmetic: it forwards the call and restates
/// refusals on this law's own error surface.  `quantize_optical_delivery` and
/// `quantize_auditory_delivery` are the same call on the same function.
pub(crate) fn quantize_tactile_delivery(
    transduced_energy_zeptojoules: &BigRational,
    predecessor_residue: ExactRational,
    lattice_quantum_zeptojoules: &BigRational,
    opening_threshold_quanta: u128,
    window_cap_quanta: u128,
) -> Result<QuantizedReceptorDelivery, TactileReceptorWorkError> {
    quantize_receptor_delivery(
        transduced_energy_zeptojoules,
        predecessor_residue,
        lattice_quantum_zeptojoules,
        opening_threshold_quanta,
        window_cap_quanta,
    )
    .map_err(TactileReceptorWorkError::from)
}

fn settle_port_range(
    port: &JointSourcePortView,
    anatomy: &TactileReceptorAnatomy,
    first_sample: usize,
    last_sample: usize,
) -> Result<TactileReceptorWorkSettlement, TactileReceptorWorkError> {
    if port.sense != PhysicalSourceSense::Touch.declared_layer() {
        return Err(TactileReceptorWorkError::NotTouch);
    }
    if port.physical_quantity != CONTACT_SITE_OCCUPANCY_QUANTITY {
        return Err(TactileReceptorWorkError::PhysicalQuantityMismatch);
    }
    if port.physical_unit != CONTACT_REFERENCE_OCCUPANCY_UNIT {
        return Err(TactileReceptorWorkError::PhysicalUnitMismatch);
    }
    if port.source_times.len() < 2 {
        return Err(TactileReceptorWorkError::TooFewSamples);
    }
    if port.source_times.len() != port.exact_normalized_sources.len() {
        return Err(TactileReceptorWorkError::SampleCardinalityChanged);
    }
    if first_sample >= last_sample || last_sample >= port.source_times.len() {
        return Err(TactileReceptorWorkError::SourceIntervalAbsent);
    }
    // Law T3: an occupancy is a fraction of a declared area.  It cannot be
    // negative and it cannot exceed the site, so the admitted range is the
    // unsigned unit interval — the optical range, not the signed acoustic one.
    if port.exact_normalized_sources[first_sample..=last_sample]
        .iter()
        .any(|value| value < &BigRational::zero() || value > &BigRational::one())
    {
        return Err(TactileReceptorWorkError::SourceOutsideReferenceInterval);
    }

    // Law T1: exact trapezoidal integral of the occupancy fraction.  This is
    // the optical integrand verbatim; contact never changes sign, so nothing
    // is squared and nothing is rectified.
    let mut integrated = BigRational::zero();
    for index in first_sample..last_sample {
        let duration = &port.source_times[index + 1] - &port.source_times[index];
        if duration <= BigRational::zero() {
            return Err(TactileReceptorWorkError::SourceClockDidNotAdvance);
        }
        let mean = (&port.exact_normalized_sources[index]
            + &port.exact_normalized_sources[index + 1])
            / BigInt::from(2);
        integrated += mean * duration;
    }
    let observed_duration_seconds =
        &port.source_times[last_sample] - &port.source_times[first_sample];
    let incident_energy_zeptojoules = &integrated
        * &anatomy.reference_contact_stress_zeptojoules_per_square_nanometre_second
        * &anatomy.site_area_square_nanometres;
    // Law T2: membrane compliance is what absorptance is on the optical side —
    // the fraction of the incident mechanical energy the receptor membrane
    // actually takes up; conformational coupling is the same conversion into
    // the gate's conformational coordinate.
    let absorbed_energy_zeptojoules = &incident_energy_zeptojoules * &anatomy.membrane_compliance;
    let transduced_energy_zeptojoules =
        &absorbed_energy_zeptojoules * &anatomy.conformational_coupling;

    Ok(TactileReceptorWorkSettlement {
        observed_duration_seconds,
        integrated_occupancy_fraction_seconds: integrated,
        incident_energy_zeptojoules,
        absorbed_energy_zeptojoules,
        gate_work: GateWorkOccurrence::new(-transduced_energy_zeptojoules.clone()),
        transduced_energy_zeptojoules,
    })
}

pub(crate) fn settle_port(
    port: &JointSourcePortView,
    anatomy: &TactileReceptorAnatomy,
) -> Result<TactileReceptorWorkSettlement, TactileReceptorWorkError> {
    settle_port_range(port, anatomy, 0, port.source_times.len().saturating_sub(1))
}

pub(crate) fn derive_tactile_receptor_work(
    episode: &NativeJointSourceEpisode,
    perspective: JointNeuronPerspective<'_>,
    anatomy: &TactileReceptorAnatomy,
) -> Result<TactileReceptorWorkSettlement, TactileReceptorWorkError> {
    let anchor = bind_neuron_source_anchor(episode, perspective)?;
    if anchor.sense() != PhysicalSourceSense::Touch {
        return Err(TactileReceptorWorkError::NotTouch);
    }
    let port = episode
        .joint_source_ports()
        .get(anchor.source_port_index())
        .ok_or(TactileReceptorWorkError::Source(
            NeuronSourceAnchorError::SourcePortAbsent,
        ))?;
    settle_port(port, anatomy)
}

pub(crate) fn derive_tactile_receptor_sample_range_work(
    episode: &NativeJointSourceEpisode,
    perspective: JointNeuronPerspective<'_>,
    anatomy: &TactileReceptorAnatomy,
    first_sample: usize,
    last_sample: usize,
) -> Result<TactileReceptorWorkSettlement, TactileReceptorWorkError> {
    let anchor = bind_neuron_source_anchor(episode, perspective)?;
    if anchor.sense() != PhysicalSourceSense::Touch {
        return Err(TactileReceptorWorkError::NotTouch);
    }
    let port = episode
        .joint_source_ports()
        .get(anchor.source_port_index())
        .ok_or(TactileReceptorWorkError::Source(
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

    /// Optical parity (Law T5): the same four factors the retinal anatomy
    /// declares, so `K` = 2 zJ per (dimensionless · second) exactly.
    fn anatomy() -> TactileReceptorAnatomy {
        TactileReceptorAnatomy::new(exact(4, 1), exact(1, 1), exact(1, 2), exact(1, 1)).unwrap()
    }

    fn port_with(sources: Vec<BigRational>) -> JointSourcePortView {
        let count = sources.len();
        JointSourcePortView {
            sense: PhysicalSourceSense::Touch.declared_layer(),
            topology_index: 0,
            sensor_id: "card-contact-sheet".into(),
            substream_id: "contact-row0-col0".into(),
            coordinates: vec![JointSourceCoordinate {
                axis_id: "row".into(),
                coordinate_id: "0".into(),
            }],
            physical_quantity: CONTACT_SITE_OCCUPANCY_QUANTITY.into(),
            physical_unit: CONTACT_REFERENCE_OCCUPANCY_UNIT.into(),
            relevance_rule: "source-only".into(),
            relevance_origin: None,
            input_map_id: "independent-test-map".into(),
            source_min: exact(0, 1),
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

    /// Law T1 on the simplest possible contact: a site fully covered by the
    /// footprint for two seconds transduces K × 1 × 2 = 4 zJ.
    #[test]
    fn full_contact_becomes_local_negative_gate_work() {
        let settled = settle_port(
            &port_with(vec![exact(1, 1), exact(1, 1), exact(1, 1)]),
            &anatomy(),
        )
        .unwrap();
        assert_eq!(settled.observed_duration_seconds, exact(2, 1));
        assert_eq!(settled.integrated_occupancy_fraction_seconds, exact(2, 1));
        assert_eq!(settled.incident_energy_zeptojoules, exact(8, 1));
        assert_eq!(settled.absorbed_energy_zeptojoules, exact(4, 1));
        assert_eq!(settled.transduced_energy_zeptojoules, exact(4, 1));
        assert!(!settled.gate_work.is_zero());
    }

    /// The composite constant is exactly the optical one: 4 × 1 × 1/2 × 1 = 2
    /// zJ per (dimensionless · second).  Touch introduces NO new number.
    #[test]
    fn the_composite_constant_is_optical_parity() {
        assert_eq!(anatomy().composite_transduction_constant(), exact(2, 1));
    }

    /// NO CONTACT is a lawful state, not an absent sense: a site the footprint
    /// never covers transduces exactly zero and delivers exactly zero work.
    /// This is what makes "nothing outside the card" a physical report rather
    /// than a missing port.
    #[test]
    fn no_contact_transduces_exactly_zero() {
        let settled = settle_port(
            &port_with(vec![exact(0, 1), exact(0, 1), exact(0, 1)]),
            &anatomy(),
        )
        .unwrap();
        assert!(settled.integrated_occupancy_fraction_seconds.is_zero());
        assert!(settled.transduced_energy_zeptojoules.is_zero());
        assert!(settled.gate_work.is_zero());
    }

    /// PARTIAL contact — an edge site — transduces strictly between the two,
    /// which is the entire information content of an outline.
    #[test]
    fn an_edge_site_transduces_strictly_between_contact_and_none() {
        let full = settle_port(
            &port_with(vec![exact(1, 1), exact(1, 1)]),
            &anatomy(),
        )
        .unwrap();
        let edge = settle_port(
            &port_with(vec![exact(709, 1000), exact(709, 1000)]),
            &anatomy(),
        )
        .unwrap();
        let none = settle_port(
            &port_with(vec![exact(0, 1), exact(0, 1)]),
            &anatomy(),
        )
        .unwrap();
        assert!(edge.transduced_energy_zeptojoules < full.transduced_energy_zeptojoules);
        assert!(edge.transduced_energy_zeptojoules > none.transduced_energy_zeptojoules);
        // Exact, not approximately: K × 709/1000 × 1 s.
        assert_eq!(edge.transduced_energy_zeptojoules, exact(709, 500));
    }

    /// Two occupancies that differ AT ALL transduce different energies — the
    /// law loses no shape information before quantization.  The pair here is
    /// the real one: the widest and narrowest edge-column occupancies of the
    /// 36 approved cards differ in the third decimal place.
    #[test]
    fn occupancies_differing_in_the_third_decimal_transduce_differently() {
        let wide = settle_port(&port_with(vec![exact(70902, 100000); 2]), &anatomy()).unwrap();
        let narrow = settle_port(&port_with(vec![exact(70042, 100000); 2]), &anatomy()).unwrap();
        assert_ne!(
            wide.transduced_energy_zeptojoules,
            narrow.transduced_energy_zeptojoules
        );
    }

    /// T3 (2026-08-06), the direct measurement: the FIVE distinct declared
    /// raster geometries among the 36 approved cards, at the real served hop
    /// (249/1000 s), through this law and the shared delivery law.
    ///
    /// The edge occupancies are the exact rationals the sensor layer derives
    /// from each card's own declared integer geometry.  Printed with
    /// `--nocapture` this is the T3 dump; the assertions are what it proves.
    ///
    /// MEASURED, and this is the honest and important part: the five shapes
    /// transduce five DIFFERENT exact energies, but over ONE hop they land on
    /// the SAME whole number of lattice quanta.  Shape reaches the physics
    /// only through ACCUMULATION — the residues differ, so the crossings
    /// diverge as the hops go on.  A single hop cannot tell these cards apart;
    /// a lesson can, and the organism-level measurement confirms it.
    #[test]
    fn the_five_declared_card_shapes_transduce_five_different_energies() {
        let quantum = exact(1, 16);
        let hop = exact(249, 1000);
        // (raster width, raster height, exact edge-column occupancy)
        let declared: &[(i64, i64, BigRational)] = &[
            (1122, 1402, exact(491, 701)),
            (1126, 1397, exact(1981, 2794)),
            (1127, 1395, exact(331, 465)),
            (1127, 1396, exact(1985, 2792)),
            (1128, 1394, exact(995, 1394)),
        ];
        let mut energies = Vec::new();
        let mut first_hop_quanta = Vec::new();
        let mut residues_after_five_hops = Vec::new();
        for (width, height, occupancy) in declared {
            // One hop of one edge site: two retained instants of a static
            // occupancy across the hop's real span.
            let port = JointSourcePortView {
                source_times: vec![exact(0, 1), hop.clone()],
                exact_normalized_sources: vec![occupancy.clone(), occupancy.clone()],
                reported_phase_turns: vec![exact(0, 1); 2],
                source_relevances: vec![exact(1, 1); 2],
                dimensionless_fields: vec![exact(1, 1); 2],
                ..port_with(vec![exact(0, 1), exact(0, 1)])
            };
            let settled = settle_port(&port, &anatomy()).unwrap();
            let energy = settled.transduced_energy_zeptojoules.clone();
            // A real card produces NONZERO tactile work at every site its
            // footprint reaches.
            assert!(energy > BigRational::zero());

            let mut residue = ExactRational::new(0, 1).unwrap();
            let mut first = None;
            for _ in 0..5 {
                let delivery =
                    quantize_tactile_delivery(&energy, residue, &quantum, 17, 52).unwrap();
                residue = delivery.successor_residue;
                if first.is_none() {
                    first = Some(delivery.delivered_quanta);
                }
            }
            println!(
                "{width}x{height} edge_occupancy={occupancy} \
                 transduced_zJ={energy} first_hop_quanta={} residue_after_5={}",
                first.unwrap(),
                exact_rational_to_big(residue)
            );
            energies.push(energy);
            first_hop_quanta.push(first.unwrap());
            residues_after_five_hops.push(exact_rational_to_big(residue));
        }
        // FIVE distinct declared shapes, FIVE distinct transduced energies:
        // the law loses no shape information.
        for index in 0..energies.len() {
            for other in index + 1..energies.len() {
                assert_ne!(energies[index], energies[other]);
                assert_ne!(
                    residues_after_five_hops[index],
                    residues_after_five_hops[other]
                );
            }
        }
        // And the honest limit, asserted rather than hidden: these particular
        // cards are so nearly the same shape that one hop delivers the same
        // whole quantum count for all five.
        assert!(first_hop_quanta.windows(2).all(|pair| pair[0] == pair[1]));
    }

    #[test]
    fn dsf_coordinate_changes_cannot_change_receptor_work() {
        let source = port_with(vec![exact(1, 2), exact(3, 4), exact(1, 1)]);
        let first = settle_port(&source, &anatomy()).unwrap();
        let mut changed_field = source;
        changed_field.dimensionless_fields = vec![exact(-9, 1); 3];
        assert_eq!(first, settle_port(&changed_field, &anatomy()).unwrap());
    }

    /// The shared delivery law, entered through the tactile door: delivered
    /// quanta × lattice step + retained residue equals the exact ∫K·c·dt over
    /// arbitrary interval sequences, with no rounding loss and no decay.  The
    /// sequence deliberately includes RELEASED (zero-contact) intervals: they
    /// add nothing, deliver nothing, and erase nothing.
    #[test]
    fn quantized_delivery_conserves_the_exact_contact_integral() {
        let quantum = exact(1, 16);
        // (occupancy numerator over 1000, dwell numerator, dwell denominator)
        let sequence: &[(i64, i64, i64)] = &[
            (1000, 1, 4),
            (0, 3, 4),
            (709, 1, 4),
            (127, 7, 8),
            (1000, 251, 1000),
            (0, 5, 1),
            (700, 1, 977),
            (500, 2, 7),
            (1000, 13, 64),
            (1, 999983, 1000000),
        ];
        let mut residue = ExactRational::new(0, 1).unwrap();
        let mut delivered_total = BigRational::zero();
        let mut exact_total = BigRational::zero();
        for (occupancy_numerator, dwell_numerator, dwell_denominator) in sequence {
            let energy = exact(2, 1)
                * exact(*occupancy_numerator, 1000)
                * exact(*dwell_numerator, *dwell_denominator);
            exact_total += &energy;
            let delivery = quantize_tactile_delivery(&energy, residue, &quantum, 17, 52).unwrap();
            delivered_total += &delivery.delivered_energy_zeptojoules;
            assert_eq!(
                &delivery.delivered_energy_zeptojoules,
                &(&quantum * BigRational::from_integer(delivery.delivered_quanta.into()))
            );
            assert!(delivery.delivered_quanta == 0 || (17..=52).contains(&delivery.delivered_quanta));
            residue = delivery.successor_residue;
            let residue_big = exact_rational_to_big(residue);
            assert!(residue_big >= BigRational::zero());
            assert_eq!(&delivered_total + &residue_big, exact_total);
        }
        assert!(delivered_total > BigRational::zero());
    }

    /// A RELEASED interval delivers nothing and erases nothing — the tactile
    /// twin of a dark interval and of silence.
    #[test]
    fn releasing_the_object_neither_delivers_nor_erases() {
        let quantum = exact(1, 16);
        let hop = exact(2, 1) * exact(1, 1) * exact(1, 4);
        let mut residue = ExactRational::new(0, 1).unwrap();
        let mut total = BigRational::zero();
        for _ in 0..2 {
            total += &hop;
            let delivery = quantize_tactile_delivery(&hop, residue, &quantum, 17, 52).unwrap();
            assert_eq!(delivery.delivered_quanta, 0);
            residue = delivery.successor_residue;
            assert_eq!(exact_rational_to_big(residue), total);
        }
        let released =
            quantize_tactile_delivery(&BigRational::zero(), residue, &quantum, 17, 52).unwrap();
        assert_eq!(released.delivered_quanta, 0);
        assert_eq!(released.successor_residue, residue);
        // The third contact hop crosses the threshold: 3 × 0.5 zJ = 24 quanta.
        total += &hop;
        let crossed = quantize_tactile_delivery(&hop, residue, &quantum, 17, 52).unwrap();
        assert_eq!(crossed.delivered_quanta, 24);
        assert_eq!(
            &crossed.delivered_energy_zeptojoules
                + exact_rational_to_big(crossed.successor_residue),
            total
        );
    }

    #[test]
    fn wrong_sense_quantity_unit_and_out_of_range_occupancy_are_refused() {
        let base = port_with(vec![exact(1, 2), exact(1, 2)]);

        let mut wrong_sense = base.clone();
        wrong_sense.sense = PhysicalSourceSense::Sight.declared_layer();
        assert_eq!(
            settle_port(&wrong_sense, &anatomy()),
            Err(TactileReceptorWorkError::NotTouch)
        );

        let mut wrong_quantity = base.clone();
        wrong_quantity.physical_quantity = "retinal-spectral-irradiance".into();
        assert_eq!(
            settle_port(&wrong_quantity, &anatomy()),
            Err(TactileReceptorWorkError::PhysicalQuantityMismatch)
        );

        let mut wrong_unit = base.clone();
        wrong_unit.physical_unit = "dimensionless".into();
        assert_eq!(
            settle_port(&wrong_unit, &anatomy()),
            Err(TactileReceptorWorkError::PhysicalUnitMismatch)
        );

        // An occupancy is a fraction of a declared area: neither sign-carrying
        // nor able to exceed the site.
        let mut negative = base.clone();
        negative.exact_normalized_sources[1] = exact(-1, 2);
        assert_eq!(
            settle_port(&negative, &anatomy()),
            Err(TactileReceptorWorkError::SourceOutsideReferenceInterval)
        );

        let mut overfull = base.clone();
        overfull.exact_normalized_sources[1] = exact(3, 2);
        assert_eq!(
            settle_port(&overfull, &anatomy()),
            Err(TactileReceptorWorkError::SourceOutsideReferenceInterval)
        );

        let mut stalled = base;
        stalled.source_times = vec![exact(0, 1), exact(0, 1)];
        assert_eq!(
            settle_port(&stalled, &anatomy()),
            Err(TactileReceptorWorkError::SourceClockDidNotAdvance)
        );
    }

    #[test]
    fn invalid_anatomy_is_refused() {
        assert_eq!(
            TactileReceptorAnatomy::new(exact(0, 1), exact(1, 1), exact(1, 2), exact(1, 1)),
            Err(TactileReceptorWorkError::InvalidAnatomy)
        );
        assert_eq!(
            TactileReceptorAnatomy::new(exact(4, 1), exact(1, 1), exact(3, 2), exact(1, 1)),
            Err(TactileReceptorWorkError::InvalidAnatomy)
        );
    }
}
