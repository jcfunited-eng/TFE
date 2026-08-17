//! Exact local conversion from one core or cutaneous temperature receptor to
//! gate work.
//!
//! The source is the measured node temperature expressed as a fraction of the
//! receptor's declared 273000..323000 millikelvin physical interval.  This is
//! a monotonic receptor coordinate, not a comfort score: it contains no set
//! point, warm/cold label, preference, action, or semantic identity.  A steady
//! temperature lawfully produces tonic receptor work; changes in physical
//! temperature change that work on the same retained source clock.

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

pub(crate) const THERMORECEPTOR_TEMPERATURE_QUANTITY: &str = "thermoreceptor-temperature";
pub(crate) const THERMORECEPTOR_REFERENCE_INTERVAL_UNIT: &str =
    "fraction-of-declared-273000-to-323000-millikelvin-span";

#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) struct ThermalReceptorAnatomy {
    reference_interval_energy_zeptojoules_per_second: BigRational,
    receptor_population: BigRational,
    membrane_compliance: BigRational,
    conformational_coupling: BigRational,
}

impl ThermalReceptorAnatomy {
    pub(crate) fn new(
        reference_interval_energy_zeptojoules_per_second: BigRational,
        receptor_population: BigRational,
        membrane_compliance: BigRational,
        conformational_coupling: BigRational,
    ) -> Result<Self, ThermalReceptorWorkError> {
        if reference_interval_energy_zeptojoules_per_second <= BigRational::zero()
            || receptor_population <= BigRational::zero()
            || membrane_compliance <= BigRational::zero()
            || membrane_compliance > BigRational::one()
            || conformational_coupling <= BigRational::zero()
            || conformational_coupling > BigRational::one()
        {
            return Err(ThermalReceptorWorkError::InvalidAnatomy);
        }
        Ok(Self {
            reference_interval_energy_zeptojoules_per_second,
            receptor_population,
            membrane_compliance,
            conformational_coupling,
        })
    }
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) struct ThermalReceptorWorkSettlement {
    pub(crate) integrated_temperature_fraction_seconds: BigRational,
    pub(crate) transduced_energy_zeptojoules: BigRational,
    pub(crate) gate_work: GateWorkOccurrence,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) enum ThermalReceptorWorkError {
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

impl From<NeuronSourceAnchorError> for ThermalReceptorWorkError {
    fn from(value: NeuronSourceAnchorError) -> Self {
        Self::Source(value)
    }
}

impl From<ReceptorDeliveryError> for ThermalReceptorWorkError {
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

pub(crate) fn quantize_thermal_delivery(
    transduced_energy_zeptojoules: &BigRational,
    predecessor_residue: ExactRational,
    lattice_quantum_zeptojoules: &BigRational,
    opening_threshold_quanta: u128,
    window_cap_quanta: u128,
) -> Result<QuantizedReceptorDelivery, ThermalReceptorWorkError> {
    quantize_receptor_delivery(
        transduced_energy_zeptojoules,
        predecessor_residue,
        lattice_quantum_zeptojoules,
        opening_threshold_quanta,
        window_cap_quanta,
    )
    .map_err(ThermalReceptorWorkError::from)
}

fn settle_port_range(
    port: &JointSourcePortView,
    anatomy: &ThermalReceptorAnatomy,
    first_sample: usize,
    last_sample: usize,
) -> Result<ThermalReceptorWorkSettlement, ThermalReceptorWorkError> {
    if port.sense != PhysicalSourceSense::Body.declared_layer() {
        return Err(ThermalReceptorWorkError::NotBody);
    }
    if port.physical_quantity != THERMORECEPTOR_TEMPERATURE_QUANTITY {
        return Err(ThermalReceptorWorkError::PhysicalQuantityMismatch);
    }
    if port.physical_unit != THERMORECEPTOR_REFERENCE_INTERVAL_UNIT {
        return Err(ThermalReceptorWorkError::PhysicalUnitMismatch);
    }
    if port.source_times.len() < 2 {
        return Err(ThermalReceptorWorkError::TooFewSamples);
    }
    if port.source_times.len() != port.exact_normalized_sources.len() {
        return Err(ThermalReceptorWorkError::SampleCardinalityChanged);
    }
    if first_sample >= last_sample || last_sample >= port.source_times.len() {
        return Err(ThermalReceptorWorkError::SourceIntervalAbsent);
    }
    if port.exact_normalized_sources[first_sample..=last_sample]
        .iter()
        .any(|value| value < &BigRational::zero() || value > &BigRational::one())
    {
        return Err(ThermalReceptorWorkError::SourceOutsideReferenceInterval);
    }

    let mut integrated = BigRational::zero();
    for index in first_sample..last_sample {
        let duration = &port.source_times[index + 1] - &port.source_times[index];
        if duration <= BigRational::zero() {
            return Err(ThermalReceptorWorkError::SourceClockDidNotAdvance);
        }
        let mean = (&port.exact_normalized_sources[index]
            + &port.exact_normalized_sources[index + 1])
            / BigInt::from(2);
        integrated += mean * duration;
    }
    let transduced_energy_zeptojoules = &integrated
        * &anatomy.reference_interval_energy_zeptojoules_per_second
        * &anatomy.receptor_population
        * &anatomy.membrane_compliance
        * &anatomy.conformational_coupling;
    Ok(ThermalReceptorWorkSettlement {
        integrated_temperature_fraction_seconds: integrated,
        gate_work: GateWorkOccurrence::new(-transduced_energy_zeptojoules.clone()),
        transduced_energy_zeptojoules,
    })
}

pub(crate) fn derive_thermal_receptor_sample_range_work(
    episode: &NativeJointSourceEpisode,
    perspective: JointNeuronPerspective<'_>,
    anatomy: &ThermalReceptorAnatomy,
    first_sample: usize,
    last_sample: usize,
) -> Result<ThermalReceptorWorkSettlement, ThermalReceptorWorkError> {
    let anchor = bind_neuron_source_anchor(episode, perspective)?;
    if anchor.sense() != PhysicalSourceSense::Body {
        return Err(ThermalReceptorWorkError::NotBody);
    }
    let port = episode
        .joint_source_ports()
        .get(anchor.source_port_index())
        .ok_or(ThermalReceptorWorkError::Source(
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

    fn anatomy() -> ThermalReceptorAnatomy {
        ThermalReceptorAnatomy::new(exact(4, 1), exact(1, 1), exact(1, 2), exact(1, 1)).unwrap()
    }

    fn port(values: Vec<BigRational>) -> JointSourcePortView {
        let count = values.len();
        JointSourcePortView {
            sense: PhysicalSourceSense::Body.declared_layer(),
            topology_index: 0,
            body_proprioceptor_terminal: None,
            sensor_id: "body-thermoreceptors".into(),
            substream_id: "cutaneous-temperature".into(),
            coordinates: vec![JointSourceCoordinate {
                axis_id: "body-compartment".into(),
                coordinate_id: "cutaneous-shell".into(),
            }],
            physical_quantity: THERMORECEPTOR_TEMPERATURE_QUANTITY.into(),
            physical_unit: THERMORECEPTOR_REFERENCE_INTERVAL_UNIT.into(),
            relevance_rule: "source-only".into(),
            relevance_origin: None,
            input_map_id: "thermal-test-map".into(),
            source_min: exact(0, 1),
            source_max: exact(1, 1),
            field_offset: exact(1, 1),
            field_scale: exact(1, 2),
            input_map_profile: vec![1],
            input_map_group_receipt: [0; 32],
            source_times: (0..count).map(|index| exact(index as i64, 1)).collect(),
            exact_normalized_sources: values,
            reported_phase_turns: vec![exact(0, 1); count],
            source_relevances: vec![exact(1, 1); count],
            dimensionless_fields: vec![exact(1, 1); count],
        }
    }

    #[test]
    fn stable_temperature_is_tonic_and_distinct_temperatures_remain_distinct() {
        let low =
            settle_port_range(&port(vec![exact(1, 4), exact(1, 4)]), &anatomy(), 0, 1).unwrap();
        let high =
            settle_port_range(&port(vec![exact(3, 4), exact(3, 4)]), &anatomy(), 0, 1).unwrap();
        assert_eq!(low.integrated_temperature_fraction_seconds, exact(1, 4));
        assert_eq!(low.transduced_energy_zeptojoules, exact(1, 2));
        assert!(high.transduced_energy_zeptojoules > low.transduced_energy_zeptojoules);
        assert!(!low.gate_work.is_zero());
    }

    #[test]
    fn wrong_unit_and_out_of_range_temperature_are_refused() {
        let mut wrong = port(vec![exact(1, 2), exact(1, 2)]);
        wrong.physical_unit = "comfort-score".into();
        assert_eq!(
            settle_port_range(&wrong, &anatomy(), 0, 1),
            Err(ThermalReceptorWorkError::PhysicalUnitMismatch)
        );
        let outside = port(vec![exact(1, 2), exact(3, 2)]);
        assert_eq!(
            settle_port_range(&outside, &anatomy(), 0, 1),
            Err(ThermalReceptorWorkError::SourceOutsideReferenceInterval)
        );
    }
}
