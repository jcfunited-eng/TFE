//! Exact local conversion from antagonist body position to receptor work.
//!
//! Each terminal carries the length fraction of one member of an antagonist
//! pair. Static length remains physical input; moving a joint lengthens one
//! member while shortening the other. Axis names and effector directions
//! never select an action.

use num_bigint::BigInt;
use num_rational::BigRational;
use num_traits::{One, Zero};

use crate::exact_rational::ExactRational;
use crate::joint_source_episode::{JointSourcePortView, NativeJointSourceEpisode};
use crate::joint_uf_neuron_boundary::JointNeuronPerspective;
use crate::neuron_source_anchor::{
    bind_neuron_source_anchor, NeuronSourceAnchorError, PhysicalSourceSense,
};
use crate::receptor_quantum_delivery::{
    quantize_receptor_delivery, QuantizedReceptorDelivery, ReceptorDeliveryError,
};

pub(crate) const ANTAGONIST_PROPRIOCEPTOR_LENGTH_QUANTITY: &str =
    "antagonist-proprioceptor-length-fraction";
pub(crate) const ARTICULATED_AXIS_SPAN_FRACTION_UNIT: &str =
    "fraction-of-declared-articulated-axis-span";

#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) struct ProprioceptiveReceptorAnatomy {
    reference_mechanical_power_zeptojoules_per_square_nanometre_second: BigRational,
    receptor_area_square_nanometres: BigRational,
    mechanical_transmission: BigRational,
    conformational_coupling: BigRational,
}

impl ProprioceptiveReceptorAnatomy {
    pub(crate) fn new(
        reference_mechanical_power_zeptojoules_per_square_nanometre_second: BigRational,
        receptor_area_square_nanometres: BigRational,
        mechanical_transmission: BigRational,
        conformational_coupling: BigRational,
    ) -> Result<Self, ProprioceptiveReceptorWorkError> {
        if reference_mechanical_power_zeptojoules_per_square_nanometre_second <= BigRational::zero()
            || receptor_area_square_nanometres <= BigRational::zero()
            || mechanical_transmission <= BigRational::zero()
            || mechanical_transmission > BigRational::one()
            || conformational_coupling <= BigRational::zero()
            || conformational_coupling > BigRational::one()
        {
            return Err(ProprioceptiveReceptorWorkError::InvalidAnatomy);
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
pub(crate) struct ProprioceptiveReceptorWorkSettlement {
    pub(crate) transduced_energy_zeptojoules: BigRational,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) enum ProprioceptiveReceptorWorkError {
    Source(NeuronSourceAnchorError),
    InvalidAnatomy,
    NotBodyProprioceptor,
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

impl From<NeuronSourceAnchorError> for ProprioceptiveReceptorWorkError {
    fn from(value: NeuronSourceAnchorError) -> Self {
        Self::Source(value)
    }
}

impl From<ReceptorDeliveryError> for ProprioceptiveReceptorWorkError {
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

pub(crate) fn quantize_proprioceptive_delivery(
    transduced_energy_zeptojoules: &BigRational,
    predecessor_residue: ExactRational,
    lattice_quantum_zeptojoules: &BigRational,
    opening_threshold_quanta: u128,
    window_cap_quanta: u128,
) -> Result<QuantizedReceptorDelivery, ProprioceptiveReceptorWorkError> {
    quantize_receptor_delivery(
        transduced_energy_zeptojoules,
        predecessor_residue,
        lattice_quantum_zeptojoules,
        opening_threshold_quanta,
        window_cap_quanta,
    )
    .map_err(ProprioceptiveReceptorWorkError::from)
}

fn settle_port_range(
    port: &JointSourcePortView,
    anatomy: &ProprioceptiveReceptorAnatomy,
    first_sample: usize,
    last_sample: usize,
) -> Result<ProprioceptiveReceptorWorkSettlement, ProprioceptiveReceptorWorkError> {
    if port.sense != PhysicalSourceSense::Body.declared_layer()
        || port.body_proprioceptor_terminal.is_none()
    {
        return Err(ProprioceptiveReceptorWorkError::NotBodyProprioceptor);
    }
    if port.physical_quantity != ANTAGONIST_PROPRIOCEPTOR_LENGTH_QUANTITY {
        return Err(ProprioceptiveReceptorWorkError::PhysicalQuantityMismatch);
    }
    if port.physical_unit != ARTICULATED_AXIS_SPAN_FRACTION_UNIT {
        return Err(ProprioceptiveReceptorWorkError::PhysicalUnitMismatch);
    }
    if port.source_times.len() < 2 {
        return Err(ProprioceptiveReceptorWorkError::TooFewSamples);
    }
    if port.source_times.len() != port.exact_normalized_sources.len() {
        return Err(ProprioceptiveReceptorWorkError::SampleCardinalityChanged);
    }
    if first_sample >= last_sample || last_sample >= port.source_times.len() {
        return Err(ProprioceptiveReceptorWorkError::SourceIntervalAbsent);
    }
    if port.exact_normalized_sources[first_sample..=last_sample]
        .iter()
        .any(|value| value < &BigRational::zero() || value > &BigRational::one())
    {
        return Err(ProprioceptiveReceptorWorkError::SourceOutsideReferenceInterval);
    }

    let mut integrated_squared_length_fraction_seconds = BigRational::zero();
    for index in first_sample..last_sample {
        let duration = &port.source_times[index + 1] - &port.source_times[index];
        if duration <= BigRational::zero() {
            return Err(ProprioceptiveReceptorWorkError::SourceClockDidNotAdvance);
        }
        let left = &port.exact_normalized_sources[index] * &port.exact_normalized_sources[index];
        let right =
            &port.exact_normalized_sources[index + 1] * &port.exact_normalized_sources[index + 1];
        integrated_squared_length_fraction_seconds += (left + right) / BigInt::from(2) * duration;
    }
    let incident = integrated_squared_length_fraction_seconds
        * &anatomy.reference_mechanical_power_zeptojoules_per_square_nanometre_second
        * &anatomy.receptor_area_square_nanometres;
    let absorbed = incident * &anatomy.mechanical_transmission;
    Ok(ProprioceptiveReceptorWorkSettlement {
        transduced_energy_zeptojoules: absorbed * &anatomy.conformational_coupling,
    })
}

pub(crate) fn derive_proprioceptive_receptor_sample_range_work(
    episode: &NativeJointSourceEpisode,
    perspective: JointNeuronPerspective<'_>,
    anatomy: &ProprioceptiveReceptorAnatomy,
    first_sample: usize,
    last_sample: usize,
) -> Result<ProprioceptiveReceptorWorkSettlement, ProprioceptiveReceptorWorkError> {
    let anchor = bind_neuron_source_anchor(episode, perspective)?;
    if anchor.sense() != PhysicalSourceSense::Body {
        return Err(ProprioceptiveReceptorWorkError::NotBodyProprioceptor);
    }
    let port = episode
        .joint_source_ports()
        .get(anchor.source_port_index())
        .ok_or(ProprioceptiveReceptorWorkError::Source(
            NeuronSourceAnchorError::SourcePortAbsent,
        ))?;
    settle_port_range(port, anatomy, first_sample, last_sample)
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::articulated_body_joint_source_builder::admit_complete_articulated_body_state_source;
    use crate::joint_uf_neuron_boundary::{
        bind_neuron_perspective, prepare_complete_joint_field_admitted_fixture,
    };
    use crate::virtual_articulated_body::ArticulatedBodyState;

    fn exact(numerator: i64, denominator: i64) -> BigRational {
        BigRational::new(BigInt::from(numerator), BigInt::from(denominator))
    }

    #[test]
    fn static_antagonist_lengths_transduce_without_motion_or_direction_label() {
        let source =
            admit_complete_articulated_body_state_source(0, &ArticulatedBodyState::at_neutral())
                .unwrap();
        let shared = prepare_complete_joint_field_admitted_fixture(&source, 0).unwrap();
        let anatomy =
            ProprioceptiveReceptorAnatomy::new(exact(4, 1), exact(1, 1), exact(1, 2), exact(1, 1))
                .unwrap();
        let left = derive_proprioceptive_receptor_sample_range_work(
            &source,
            bind_neuron_perspective(&shared, 0, 0).unwrap(),
            &anatomy,
            0,
            1,
        )
        .unwrap();
        let right = derive_proprioceptive_receptor_sample_range_work(
            &source,
            bind_neuron_perspective(&shared, 1, 0).unwrap(),
            &anatomy,
            0,
            1,
        )
        .unwrap();
        assert!(left.transduced_energy_zeptojoules > BigRational::zero());
        assert!(right.transduced_energy_zeptojoules > BigRational::zero());
        assert_ne!(
            left.transduced_energy_zeptojoules,
            right.transduced_energy_zeptojoules
        );
    }
}
