//! Exact local conversion from one reached olfactory or gustatory receptor
//! saturation occurrence to gate work.
//!
//! The transported source is already the fraction of this receptor's declared
//! saturating concentration.  It is therefore a receptor-level activation
//! coordinate, not a raw ligand concentration.  We integrate that exact
//! unsigned coordinate over its source clock and do not invent a universal
//! binding affinity, Hill coefficient, chemical species, or semantic identity.

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

pub(crate) const OLFACTORY_VOLATILE_CONCENTRATION_QUANTITY: &str =
    "olfactory-volatile-concentration";
pub(crate) const GUSTATORY_CONTACT_CONCENTRATION_QUANTITY: &str = "gustatory-contact-concentration";
pub(crate) const RECEPTOR_SATURATION_FRACTION_UNIT: &str =
    "fraction-of-declared-saturating-concentration";

#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) struct ChemicalReceptorAnatomy {
    reference_saturation_energy_zeptojoules_per_second: BigRational,
    receptor_population: BigRational,
    membrane_compliance: BigRational,
    conformational_coupling: BigRational,
}

impl ChemicalReceptorAnatomy {
    pub(crate) fn new(
        reference_saturation_energy_zeptojoules_per_second: BigRational,
        receptor_population: BigRational,
        membrane_compliance: BigRational,
        conformational_coupling: BigRational,
    ) -> Result<Self, ChemicalReceptorWorkError> {
        if reference_saturation_energy_zeptojoules_per_second <= BigRational::zero()
            || receptor_population <= BigRational::zero()
            || membrane_compliance <= BigRational::zero()
            || membrane_compliance > BigRational::one()
            || conformational_coupling <= BigRational::zero()
            || conformational_coupling > BigRational::one()
        {
            return Err(ChemicalReceptorWorkError::InvalidAnatomy);
        }
        Ok(Self {
            reference_saturation_energy_zeptojoules_per_second,
            receptor_population,
            membrane_compliance,
            conformational_coupling,
        })
    }

    pub(crate) fn composite_transduction_constant(&self) -> BigRational {
        &self.reference_saturation_energy_zeptojoules_per_second
            * &self.receptor_population
            * &self.membrane_compliance
            * &self.conformational_coupling
    }
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) struct ChemicalReceptorWorkSettlement {
    pub(crate) observed_duration_seconds: BigRational,
    pub(crate) integrated_saturation_fraction_seconds: BigRational,
    pub(crate) incident_energy_zeptojoules: BigRational,
    pub(crate) absorbed_energy_zeptojoules: BigRational,
    pub(crate) transduced_energy_zeptojoules: BigRational,
    pub(crate) gate_work: GateWorkOccurrence,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) enum ChemicalReceptorWorkError {
    Source(NeuronSourceAnchorError),
    InvalidAnatomy,
    NotChemical,
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

impl From<NeuronSourceAnchorError> for ChemicalReceptorWorkError {
    fn from(value: NeuronSourceAnchorError) -> Self {
        Self::Source(value)
    }
}

impl From<ReceptorDeliveryError> for ChemicalReceptorWorkError {
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

pub(crate) fn quantize_chemical_delivery(
    transduced_energy_zeptojoules: &BigRational,
    predecessor_residue: ExactRational,
    lattice_quantum_zeptojoules: &BigRational,
    opening_threshold_quanta: u128,
    window_cap_quanta: u128,
) -> Result<QuantizedReceptorDelivery, ChemicalReceptorWorkError> {
    quantize_receptor_delivery(
        transduced_energy_zeptojoules,
        predecessor_residue,
        lattice_quantum_zeptojoules,
        opening_threshold_quanta,
        window_cap_quanta,
    )
    .map_err(ChemicalReceptorWorkError::from)
}

fn expected_quantity(sense: u8) -> Result<&'static str, ChemicalReceptorWorkError> {
    if sense == PhysicalSourceSense::Smell.declared_layer() {
        Ok(OLFACTORY_VOLATILE_CONCENTRATION_QUANTITY)
    } else if sense == PhysicalSourceSense::Taste.declared_layer() {
        Ok(GUSTATORY_CONTACT_CONCENTRATION_QUANTITY)
    } else {
        Err(ChemicalReceptorWorkError::NotChemical)
    }
}

fn settle_port_range(
    port: &JointSourcePortView,
    anatomy: &ChemicalReceptorAnatomy,
    first_sample: usize,
    last_sample: usize,
) -> Result<ChemicalReceptorWorkSettlement, ChemicalReceptorWorkError> {
    if port.physical_quantity != expected_quantity(port.sense)? {
        return Err(ChemicalReceptorWorkError::PhysicalQuantityMismatch);
    }
    if port.physical_unit != RECEPTOR_SATURATION_FRACTION_UNIT {
        return Err(ChemicalReceptorWorkError::PhysicalUnitMismatch);
    }
    if port.source_times.len() < 2 {
        return Err(ChemicalReceptorWorkError::TooFewSamples);
    }
    if port.source_times.len() != port.exact_normalized_sources.len() {
        return Err(ChemicalReceptorWorkError::SampleCardinalityChanged);
    }
    if first_sample >= last_sample || last_sample >= port.source_times.len() {
        return Err(ChemicalReceptorWorkError::SourceIntervalAbsent);
    }
    if port.exact_normalized_sources[first_sample..=last_sample]
        .iter()
        .any(|value| value < &BigRational::zero() || value > &BigRational::one())
    {
        return Err(ChemicalReceptorWorkError::SourceOutsideReferenceInterval);
    }

    let mut integrated = BigRational::zero();
    for index in first_sample..last_sample {
        let duration = &port.source_times[index + 1] - &port.source_times[index];
        if duration <= BigRational::zero() {
            return Err(ChemicalReceptorWorkError::SourceClockDidNotAdvance);
        }
        let mean = (&port.exact_normalized_sources[index]
            + &port.exact_normalized_sources[index + 1])
            / BigInt::from(2);
        integrated += mean * duration;
    }

    let observed_duration_seconds =
        &port.source_times[last_sample] - &port.source_times[first_sample];
    let incident_energy_zeptojoules = &integrated
        * &anatomy.reference_saturation_energy_zeptojoules_per_second
        * &anatomy.receptor_population;
    let absorbed_energy_zeptojoules = &incident_energy_zeptojoules * &anatomy.membrane_compliance;
    let transduced_energy_zeptojoules =
        &absorbed_energy_zeptojoules * &anatomy.conformational_coupling;

    Ok(ChemicalReceptorWorkSettlement {
        observed_duration_seconds,
        integrated_saturation_fraction_seconds: integrated,
        incident_energy_zeptojoules,
        absorbed_energy_zeptojoules,
        gate_work: GateWorkOccurrence::new(-transduced_energy_zeptojoules.clone()),
        transduced_energy_zeptojoules,
    })
}

pub(crate) fn derive_chemical_receptor_sample_range_work(
    episode: &NativeJointSourceEpisode,
    perspective: JointNeuronPerspective<'_>,
    anatomy: &ChemicalReceptorAnatomy,
    first_sample: usize,
    last_sample: usize,
) -> Result<ChemicalReceptorWorkSettlement, ChemicalReceptorWorkError> {
    let anchor = bind_neuron_source_anchor(episode, perspective)?;
    if !matches!(
        anchor.sense(),
        PhysicalSourceSense::Smell | PhysicalSourceSense::Taste
    ) {
        return Err(ChemicalReceptorWorkError::NotChemical);
    }
    let port = episode
        .joint_source_ports()
        .get(anchor.source_port_index())
        .ok_or(ChemicalReceptorWorkError::Source(
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

    fn anatomy() -> ChemicalReceptorAnatomy {
        ChemicalReceptorAnatomy::new(exact(4, 1), exact(1, 1), exact(1, 2), exact(1, 1)).unwrap()
    }

    fn port(sense: PhysicalSourceSense, values: Vec<BigRational>) -> JointSourcePortView {
        let count = values.len();
        JointSourcePortView {
            sense: sense.declared_layer(),
            topology_index: 0,
            sensor_id: "chemical-receptor-field".into(),
            substream_id: "chemical-receptor-00".into(),
            coordinates: vec![JointSourceCoordinate {
                axis_id: "receptor-index".into(),
                coordinate_id: "00".into(),
            }],
            physical_quantity: expected_quantity(sense.declared_layer()).unwrap().into(),
            physical_unit: RECEPTOR_SATURATION_FRACTION_UNIT.into(),
            relevance_rule: "source-only".into(),
            relevance_origin: None,
            input_map_id: "chemical-test-map".into(),
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
    fn smell_and_taste_share_exact_receptor_saturation_physics() {
        for sense in [PhysicalSourceSense::Smell, PhysicalSourceSense::Taste] {
            let settled = settle_port_range(
                &port(sense, vec![exact(1, 2), exact(1, 2)]),
                &anatomy(),
                0,
                1,
            )
            .unwrap();
            assert_eq!(settled.integrated_saturation_fraction_seconds, exact(1, 2));
            assert_eq!(settled.transduced_energy_zeptojoules, exact(1, 1));
            assert!(!settled.gate_work.is_zero());
        }
        assert_eq!(anatomy().composite_transduction_constant(), exact(2, 1));
    }

    #[test]
    fn zero_saturation_is_a_lawful_zero_and_fractional_states_remain_distinct() {
        let zero = settle_port_range(
            &port(PhysicalSourceSense::Smell, vec![exact(0, 1), exact(0, 1)]),
            &anatomy(),
            0,
            1,
        )
        .unwrap();
        let low = settle_port_range(
            &port(PhysicalSourceSense::Smell, vec![exact(1, 8), exact(1, 8)]),
            &anatomy(),
            0,
            1,
        )
        .unwrap();
        let high = settle_port_range(
            &port(PhysicalSourceSense::Smell, vec![exact(3, 4), exact(3, 4)]),
            &anatomy(),
            0,
            1,
        )
        .unwrap();
        assert!(zero.transduced_energy_zeptojoules.is_zero());
        assert!(low.transduced_energy_zeptojoules > zero.transduced_energy_zeptojoules);
        assert!(high.transduced_energy_zeptojoules > low.transduced_energy_zeptojoules);
    }

    #[test]
    fn wrong_quantity_unit_range_and_clock_are_refused() {
        let mut wrong_quantity = port(PhysicalSourceSense::Smell, vec![exact(1, 2), exact(1, 2)]);
        wrong_quantity.physical_quantity = GUSTATORY_CONTACT_CONCENTRATION_QUANTITY.into();
        assert_eq!(
            settle_port_range(&wrong_quantity, &anatomy(), 0, 1),
            Err(ChemicalReceptorWorkError::PhysicalQuantityMismatch)
        );

        let mut wrong_unit = port(PhysicalSourceSense::Taste, vec![exact(1, 2), exact(1, 2)]);
        wrong_unit.physical_unit = "raw-concentration".into();
        assert_eq!(
            settle_port_range(&wrong_unit, &anatomy(), 0, 1),
            Err(ChemicalReceptorWorkError::PhysicalUnitMismatch)
        );

        let mut out_of_range = port(PhysicalSourceSense::Taste, vec![exact(1, 2), exact(3, 2)]);
        assert_eq!(
            settle_port_range(&out_of_range, &anatomy(), 0, 1),
            Err(ChemicalReceptorWorkError::SourceOutsideReferenceInterval)
        );
        out_of_range.exact_normalized_sources[1] = exact(1, 2);
        out_of_range.source_times[1] = exact(0, 1);
        assert_eq!(
            settle_port_range(&out_of_range, &anatomy(), 0, 1),
            Err(ChemicalReceptorWorkError::SourceClockDidNotAdvance)
        );
    }
}
