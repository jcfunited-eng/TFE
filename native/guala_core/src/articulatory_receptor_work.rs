//! Exact local conversion from articulatory body mechanics to receptor work.
//!
//! Each port is one local mechanoreceptor: respiratory flow, laryngeal
//! configuration, oral opening, or perioral skin deformation. The source
//! carries signed displacement/flow as a fraction of that site's declared
//! mechanical span. Elastic/kinetic work is quadratic, so opposing directions
//! remain distinct in the joint field while both require nonnegative local
//! transduction energy. No word, phoneme, target, score, or body-wide aggregate
//! enters this law.

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

pub(crate) const RESPIRATORY_VOLUME_VELOCITY_QUANTITY: &str =
    "respiratory-volume-velocity";
pub(crate) const LARYNGEAL_GLOTTAL_OPENING_QUANTITY: &str =
    "laryngeal-glottal-opening";
pub(crate) const ORAL_APERTURE_AREA_QUANTITY: &str = "oral-aperture-area";
pub(crate) const PERIORAL_SKIN_DEFORMATION_QUANTITY: &str =
    "perioral-skin-area-deformation";
pub(crate) const ARTICULATORY_MECHANICAL_FRACTION_UNIT: &str =
    "fraction-of-declared-articulatory-mechanical-span";

fn admitted_quantity(value: &str) -> bool {
    matches!(
        value,
        RESPIRATORY_VOLUME_VELOCITY_QUANTITY
            | LARYNGEAL_GLOTTAL_OPENING_QUANTITY
            | ORAL_APERTURE_AREA_QUANTITY
            | PERIORAL_SKIN_DEFORMATION_QUANTITY
    )
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) struct ArticulatoryReceptorAnatomy {
    reference_mechanical_power_zeptojoules_per_square_nanometre_second: BigRational,
    receptor_area_square_nanometres: BigRational,
    mechanical_transmission: BigRational,
    conformational_coupling: BigRational,
}

impl ArticulatoryReceptorAnatomy {
    pub(crate) fn new(
        reference_mechanical_power_zeptojoules_per_square_nanometre_second: BigRational,
        receptor_area_square_nanometres: BigRational,
        mechanical_transmission: BigRational,
        conformational_coupling: BigRational,
    ) -> Result<Self, ArticulatoryReceptorWorkError> {
        if reference_mechanical_power_zeptojoules_per_square_nanometre_second
            <= BigRational::zero()
            || receptor_area_square_nanometres <= BigRational::zero()
            || mechanical_transmission <= BigRational::zero()
            || mechanical_transmission > BigRational::one()
            || conformational_coupling <= BigRational::zero()
            || conformational_coupling > BigRational::one()
        {
            return Err(ArticulatoryReceptorWorkError::InvalidAnatomy);
        }
        Ok(Self {
            reference_mechanical_power_zeptojoules_per_square_nanometre_second,
            receptor_area_square_nanometres,
            mechanical_transmission,
            conformational_coupling,
        })
    }
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) struct ArticulatoryReceptorWorkSettlement {
    pub(crate) transduced_energy_zeptojoules: BigRational,
    pub(crate) gate_work: GateWorkOccurrence,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) enum ArticulatoryReceptorWorkError {
    Source(NeuronSourceAnchorError),
    InvalidAnatomy,
    NotBody,
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

impl From<NeuronSourceAnchorError> for ArticulatoryReceptorWorkError {
    fn from(value: NeuronSourceAnchorError) -> Self {
        Self::Source(value)
    }
}

impl From<ReceptorDeliveryError> for ArticulatoryReceptorWorkError {
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

pub(crate) fn quantize_articulatory_delivery(
    transduced_energy_zeptojoules: &BigRational,
    predecessor_residue: ExactRational,
    lattice_quantum_zeptojoules: &BigRational,
    opening_threshold_quanta: u128,
    window_cap_quanta: u128,
) -> Result<QuantizedReceptorDelivery, ArticulatoryReceptorWorkError> {
    quantize_receptor_delivery(
        transduced_energy_zeptojoules,
        predecessor_residue,
        lattice_quantum_zeptojoules,
        opening_threshold_quanta,
        window_cap_quanta,
    )
    .map_err(ArticulatoryReceptorWorkError::from)
}

fn settle_port_range(
    port: &JointSourcePortView,
    anatomy: &ArticulatoryReceptorAnatomy,
    first_sample: usize,
    last_sample: usize,
) -> Result<ArticulatoryReceptorWorkSettlement, ArticulatoryReceptorWorkError> {
    if port.sense != PhysicalSourceSense::Body.declared_layer() {
        return Err(ArticulatoryReceptorWorkError::NotBody);
    }
    if !admitted_quantity(&port.physical_quantity) {
        return Err(ArticulatoryReceptorWorkError::PhysicalQuantityMismatch);
    }
    if port.physical_unit != ARTICULATORY_MECHANICAL_FRACTION_UNIT {
        return Err(ArticulatoryReceptorWorkError::PhysicalUnitMismatch);
    }
    if port.source_times.len() < 2 {
        return Err(ArticulatoryReceptorWorkError::TooFewSamples);
    }
    if port.source_times.len() != port.exact_normalized_sources.len() {
        return Err(ArticulatoryReceptorWorkError::SampleCardinalityChanged);
    }
    if first_sample >= last_sample || last_sample >= port.source_times.len() {
        return Err(ArticulatoryReceptorWorkError::SourceIntervalAbsent);
    }
    if port.exact_normalized_sources[first_sample..=last_sample]
        .iter()
        .any(|value| value < &-BigRational::one() || value > &BigRational::one())
    {
        return Err(ArticulatoryReceptorWorkError::SourceOutsideReferenceInterval);
    }

    let mut integrated_squared_mechanical_fraction_seconds = BigRational::zero();
    for index in first_sample..last_sample {
        let duration = &port.source_times[index + 1] - &port.source_times[index];
        if duration <= BigRational::zero() {
            return Err(ArticulatoryReceptorWorkError::SourceClockDidNotAdvance);
        }
        let left = &port.exact_normalized_sources[index]
            * &port.exact_normalized_sources[index];
        let right = &port.exact_normalized_sources[index + 1]
            * &port.exact_normalized_sources[index + 1];
        integrated_squared_mechanical_fraction_seconds +=
            (left + right) / BigInt::from(2) * duration;
    }
    let incident = integrated_squared_mechanical_fraction_seconds
        * &anatomy.reference_mechanical_power_zeptojoules_per_square_nanometre_second
        * &anatomy.receptor_area_square_nanometres;
    let absorbed = incident * &anatomy.mechanical_transmission;
    let transduced_energy_zeptojoules = absorbed * &anatomy.conformational_coupling;
    Ok(ArticulatoryReceptorWorkSettlement {
        gate_work: GateWorkOccurrence::new(-transduced_energy_zeptojoules.clone()),
        transduced_energy_zeptojoules,
    })
}

pub(crate) fn derive_articulatory_receptor_sample_range_work(
    episode: &NativeJointSourceEpisode,
    perspective: JointNeuronPerspective<'_>,
    anatomy: &ArticulatoryReceptorAnatomy,
    first_sample: usize,
    last_sample: usize,
) -> Result<ArticulatoryReceptorWorkSettlement, ArticulatoryReceptorWorkError> {
    let anchor = bind_neuron_source_anchor(episode, perspective)?;
    if anchor.sense() != PhysicalSourceSense::Body {
        return Err(ArticulatoryReceptorWorkError::NotBody);
    }
    let port = episode
        .joint_source_ports()
        .get(anchor.source_port_index())
        .ok_or(ArticulatoryReceptorWorkError::Source(
            NeuronSourceAnchorError::SourcePortAbsent,
        ))?;
    settle_port_range(port, anatomy, first_sample, last_sample)
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::joint_source_episode::JointSourceCoordinate;

    fn exact(numerator: i64, denominator: i64) -> BigRational {
        BigRational::new(BigInt::from(numerator), BigInt::from(denominator))
    }

    fn anatomy() -> ArticulatoryReceptorAnatomy {
        ArticulatoryReceptorAnatomy::new(
            exact(4, 1),
            exact(1, 1),
            exact(1, 2),
            exact(1, 1),
        )
        .unwrap()
    }

    fn port(sources: Vec<BigRational>) -> JointSourcePortView {
        let count = sources.len();
        JointSourcePortView {
            sense: PhysicalSourceSense::Body.declared_layer(),
            topology_index: 4,
            body_proprioceptor_terminal: None,
            sensor_id: "articulatory-mechanoreceptors".into(),
            substream_id: "perioral-skin".into(),
            coordinates: vec![JointSourceCoordinate {
                axis_id: "articulatory-site".into(),
                coordinate_id: "perioral-skin".into(),
            }],
            physical_quantity: PERIORAL_SKIN_DEFORMATION_QUANTITY.into(),
            physical_unit: ARTICULATORY_MECHANICAL_FRACTION_UNIT.into(),
            relevance_rule: "source-only".into(),
            relevance_origin: None,
            input_map_id: "test-map".into(),
            source_min: exact(-1, 1),
            source_max: exact(1, 1),
            field_offset: exact(0, 1),
            field_scale: exact(1, 1),
            input_map_profile: vec![1],
            input_map_group_receipt: [0; 32],
            source_times: (0..count).map(|index| exact(index as i64, 1)).collect(),
            exact_normalized_sources: sources,
            reported_phase_turns: vec![exact(0, 1); count],
            source_relevances: vec![exact(1, 1); count],
            dimensionless_fields: vec![exact(0, 1); count],
        }
    }

    #[test]
    fn quiescence_is_zero_and_opposed_deformation_has_equal_energy() {
        let zero = settle_port_range(
            &port(vec![exact(0, 1), exact(0, 1)]),
            &anatomy(),
            0,
            1,
        )
        .unwrap();
        let positive = settle_port_range(
            &port(vec![exact(1, 2), exact(1, 2)]),
            &anatomy(),
            0,
            1,
        )
        .unwrap();
        let negative = settle_port_range(
            &port(vec![exact(-1, 2), exact(-1, 2)]),
            &anatomy(),
            0,
            1,
        )
        .unwrap();
        assert!(zero.transduced_energy_zeptojoules.is_zero());
        assert_eq!(positive.transduced_energy_zeptojoules, exact(1, 2));
        assert_eq!(positive.transduced_energy_zeptojoules, negative.transduced_energy_zeptojoules);
        assert!(!positive.gate_work.is_zero());
    }

    #[test]
    fn unrelated_body_displacement_is_not_articulatory_receptor_input() {
        let mut candidate = port(vec![exact(1, 2), exact(1, 2)]);
        candidate.physical_quantity = "body-displacement-fraction".into();
        assert_eq!(
            settle_port_range(&candidate, &anatomy(), 0, 1),
            Err(ArticulatoryReceptorWorkError::PhysicalQuantityMismatch)
        );
    }
}
