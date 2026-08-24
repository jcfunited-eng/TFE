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
    exact_rational_to_big, quantize_receptor_delivery, QuantizedReceptorDelivery,
    ReceptorDeliveryError,
};

pub(crate) const ANTAGONIST_PROPRIOCEPTOR_LENGTH_QUANTITY: &str =
    "antagonist-proprioceptor-length-fraction";
pub(crate) const ARTICULATED_AXIS_SPAN_FRACTION_UNIT: &str =
    "fraction-of-declared-articulated-axis-span";
pub(crate) const EFFECTOR_REACTIVE_LOAD_FRACTION_QUANTITY: &str =
    "reacted-effector-carrier-fraction";
pub(crate) const DISCHARGED_EFFECTOR_CARRIER_FRACTION_UNIT: &str =
    "fraction-of-discharged-effector-carriers";

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

#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) struct EffectorLoadReceptorSettlement {
    pub(crate) transduced_energy_zeptojoules: BigRational,
    pub(crate) elementary_reaction_energy_zeptojoules: BigRational,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) enum ProprioceptiveReceptorWorkError {
    Source(NeuronSourceAnchorError),
    InvalidAnatomy,
    InvalidPhysicalEvidence,
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

/// The retired load-fraction law could leave a rational whose denominator was
/// the product of unrelated action-specific discharge counts. Current load
/// work is additive elementary carrier reaction energy on one fixed native
/// millisecond clock. Its retained state therefore belongs to the finite
/// additive lattice generated by one reaction and the receiving gate quantum.
/// A predecessor outside that lattice is not physical energy from the current
/// law and is retired exactly once when that load ending is next reached.
pub(crate) fn canonical_effector_load_predecessor_residue(
    predecessor: ExactRational,
    elementary_reaction_energy_zeptojoules: &BigRational,
    lattice_quantum_zeptojoules: &BigRational,
) -> Result<ExactRational, ProprioceptiveReceptorWorkError> {
    let predecessor_big = exact_rational_to_big(predecessor);
    if predecessor_big < BigRational::zero() {
        return Err(ProprioceptiveReceptorWorkError::ResidueOutsideLattice);
    }
    if elementary_reaction_energy_zeptojoules <= &BigRational::zero()
        || lattice_quantum_zeptojoules <= &BigRational::zero()
    {
        return Err(ProprioceptiveReceptorWorkError::LatticeQuantumUnavailable);
    }
    let first = elementary_reaction_energy_zeptojoules.denom().clone();
    let second = lattice_quantum_zeptojoules.denom().clone();
    let common_denominator = (&first / positive_big_gcd(first.clone(), second.clone())) * second;
    let on_current_lattice = predecessor_big
        * BigRational::from_integer(common_denominator);
    Ok(if on_current_lattice.is_integer() {
        predecessor
    } else {
        ExactRational::integer(0)
    })
}

fn positive_big_gcd(mut left: BigInt, mut right: BigInt) -> BigInt {
    while !right.is_zero() {
        let remainder = &left % &right;
        left = right;
        right = remainder;
    }
    left
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
    settle_port_range(
        port,
        anatomy,
        first_sample,
        last_sample,
    )
}

pub(crate) fn derive_effector_load_receptor_sample_range_work(
    episode: &NativeJointSourceEpisode,
    perspective: JointNeuronPerspective<'_>,
    anatomy: &ProprioceptiveReceptorAnatomy,
    first_sample: usize,
    last_sample: usize,
) -> Result<EffectorLoadReceptorSettlement, ProprioceptiveReceptorWorkError> {
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
    if port.physical_quantity != EFFECTOR_REACTIVE_LOAD_FRACTION_QUANTITY
        || port.physical_unit != DISCHARGED_EFFECTOR_CARRIER_FRACTION_UNIT
        || first_sample >= last_sample
        || last_sample >= port.source_times.len()
        || port.source_times.len() != port.exact_normalized_sources.len()
    {
        return Err(ProprioceptiveReceptorWorkError::InvalidPhysicalEvidence);
    }
    let terminal = port
        .body_proprioceptor_terminal
        .ok_or(ProprioceptiveReceptorWorkError::NotBodyProprioceptor)?;
    let evidence = decode_body_effector_load_evidence(&port.input_map_profile, terminal)?;
    let expected_first = BigRational::new(
        BigInt::from(evidence.source_tick),
        BigInt::from(BODY_EFFECTOR_TICKS_PER_SECOND),
    );
    let expected_last = BigRational::new(
        BigInt::from(evidence.successor_tick),
        BigInt::from(BODY_EFFECTOR_TICKS_PER_SECOND),
    );
    if first_sample != 0
        || last_sample != 1
        || port.source_times.len() != 2
        || port.source_times[0] != expected_first
        || port.source_times[1] != expected_last
    {
        return Err(ProprioceptiveReceptorWorkError::InvalidPhysicalEvidence);
    }
    let expected_fraction = if evidence.discharged_carriers == 0 {
        BigRational::zero()
    } else {
        BigRational::new(
            BigInt::from(evidence.reacted_carriers),
            BigInt::from(evidence.discharged_carriers),
        )
    };
    if port.exact_normalized_sources[first_sample..=last_sample]
        .iter()
        .any(|sample| sample != &expected_fraction)
    {
        return Err(ProprioceptiveReceptorWorkError::InvalidPhysicalEvidence);
    }
    let interval_seconds = &port.source_times[1] - &port.source_times[0];
    // `receptor_area_square_nanometres` is the complete aperture population
    // used by a normalized position ending. A reacted elementary carrier is
    // already one reached aperture event, so multiplying by the population
    // here would count every reaction once per unrelated aperture.
    let elementary_reaction_energy_zeptojoules = interval_seconds
        * &anatomy.reference_mechanical_power_zeptojoules_per_square_nanometre_second
        * &anatomy.mechanical_transmission
        * &anatomy.conformational_coupling;
    let transduced_energy_zeptojoules = &elementary_reaction_energy_zeptojoules
        * BigRational::from_integer(BigInt::from(evidence.reacted_carriers));
    Ok(EffectorLoadReceptorSettlement {
        transduced_energy_zeptojoules,
        elementary_reaction_energy_zeptojoules,
    })
}

const BODY_EFFECTOR_EVIDENCE_MAGIC: &[u8; 8] = b"GLBPEV01";
const BODY_EFFECTOR_EVIDENCE_BYTES: usize = 118;
const BODY_EFFECTOR_TICKS_PER_SECOND: u64 = 1_000;

#[derive(Clone, Copy)]
struct BodyEffectorLoadEvidence {
    source_tick: u64,
    successor_tick: u64,
    discharged_carriers: u128,
    reacted_carriers: u128,
}

fn take_evidence<const N: usize>(
    bytes: &[u8],
    cursor: &mut usize,
) -> Result<[u8; N], ProprioceptiveReceptorWorkError> {
    let end = cursor
        .checked_add(N)
        .ok_or(ProprioceptiveReceptorWorkError::InvalidPhysicalEvidence)?;
    let value = bytes
        .get(*cursor..end)
        .ok_or(ProprioceptiveReceptorWorkError::InvalidPhysicalEvidence)?
        .try_into()
        .map_err(|_| ProprioceptiveReceptorWorkError::InvalidPhysicalEvidence)?;
    *cursor = end;
    Ok(value)
}

fn decode_body_effector_load_evidence(
    bytes: &[u8],
    terminal: crate::virtual_articulated_body::BodyProprioceptorTerminal,
) -> Result<BodyEffectorLoadEvidence, ProprioceptiveReceptorWorkError> {
    if bytes.len() != BODY_EFFECTOR_EVIDENCE_BYTES
        || bytes.get(..BODY_EFFECTOR_EVIDENCE_MAGIC.len())
            != Some(BODY_EFFECTOR_EVIDENCE_MAGIC)
    {
        return Err(ProprioceptiveReceptorWorkError::InvalidPhysicalEvidence);
    }
    let mut cursor = BODY_EFFECTOR_EVIDENCE_MAGIC.len();
    let source_tick = u64::from_le_bytes(take_evidence(bytes, &mut cursor)?);
    let successor_tick = u64::from_le_bytes(take_evidence(bytes, &mut cursor)?);
    if source_tick.checked_add(1) != Some(successor_tick) {
        return Err(ProprioceptiveReceptorWorkError::InvalidPhysicalEvidence);
    }
    let axis = take_evidence::<1>(bytes, &mut cursor)?[0];
    let direction = take_evidence::<1>(bytes, &mut cursor)?[0];
    if usize::from(axis) != terminal.axis().index() || direction != terminal.direction() as u8 {
        return Err(ProprioceptiveReceptorWorkError::InvalidPhysicalEvidence);
    }
    let predecessor_position = i32::from_le_bytes(take_evidence(bytes, &mut cursor)?);
    let successor_position = i32::from_le_bytes(take_evidence(bytes, &mut cursor)?);
    let signed_displacement = i32::from_le_bytes(take_evidence(bytes, &mut cursor)?);
    let toward_minimum = u128::from_le_bytes(take_evidence(bytes, &mut cursor)?);
    let toward_maximum = u128::from_le_bytes(take_evidence(bytes, &mut cursor)?);
    let opposed = u128::from_le_bytes(take_evidence(bytes, &mut cursor)?);
    let applied = u128::from_le_bytes(take_evidence(bytes, &mut cursor)?);
    let stalled = u128::from_le_bytes(take_evidence(bytes, &mut cursor)?);
    let anatomy = terminal.axis().anatomy();
    let net_magnitude = toward_minimum.abs_diff(toward_maximum);
    if cursor != bytes.len()
        || predecessor_position < anatomy.minimum
        || predecessor_position > anatomy.maximum
        || successor_position < anatomy.minimum
        || successor_position > anatomy.maximum
        || successor_position.checked_sub(predecessor_position) != Some(signed_displacement)
        || opposed != toward_minimum.min(toward_maximum)
        || applied.checked_add(stalled) != Some(net_magnitude)
    {
        return Err(ProprioceptiveReceptorWorkError::InvalidPhysicalEvidence);
    }
    let discharged_carriers = match terminal.direction() {
        crate::virtual_articulated_body::BodyEffectorDirection::TowardMinimum => toward_minimum,
        crate::virtual_articulated_body::BodyEffectorDirection::TowardMaximum => toward_maximum,
    };
    let carries_stall = match terminal.direction() {
        crate::virtual_articulated_body::BodyEffectorDirection::TowardMinimum => {
            toward_minimum > toward_maximum
        }
        crate::virtual_articulated_body::BodyEffectorDirection::TowardMaximum => {
            toward_maximum > toward_minimum
        }
    };
    let reacted_carriers = opposed
        .checked_add(if carries_stall { stalled } else { 0 })
        .ok_or(ProprioceptiveReceptorWorkError::InvalidPhysicalEvidence)?;
    if reacted_carriers > discharged_carriers {
        return Err(ProprioceptiveReceptorWorkError::InvalidPhysicalEvidence);
    }
    Ok(BodyEffectorLoadEvidence {
        source_tick,
        successor_tick,
        discharged_carriers,
        reacted_carriers,
    })
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::articulated_body_joint_source_builder::{
        admit_articulated_body_consequence_source, admit_complete_articulated_body_state_source,
    };
    use crate::joint_uf_neuron_boundary::{
        bind_neuron_perspective, prepare_complete_joint_field_admitted_fixture,
    };
    use crate::virtual_articulated_body::{
        settle_body_effector_drives, AdmittedBodyEffectorDrives, ArticulatedBodyState, BodyAxis,
        BodyEffectorDirection, BodyEffectorDrive, BodyEffectorTerminal,
    };

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

    #[test]
    fn reacted_effector_load_transduces_on_its_own_physical_port() {
        let terminal = BodyEffectorTerminal::new(
            BodyAxis::LeftGripAperture,
            BodyEffectorDirection::TowardMaximum,
        );
        let at_stop = settle_body_effector_drives(
            &ArticulatedBodyState::at_neutral(),
            &AdmittedBodyEffectorDrives::admit(vec![BodyEffectorDrive {
                terminal,
                outward_elementary_carriers: 100_000,
            }])
            .unwrap(),
        )
        .unwrap()
        .successor;
        let stopped = settle_body_effector_drives(
            &at_stop,
            &AdmittedBodyEffectorDrives::admit(vec![BodyEffectorDrive {
                terminal,
                outward_elementary_carriers: 240,
            }])
            .unwrap(),
        )
        .unwrap();
        let source = admit_articulated_body_consequence_source(
            0,
            &stopped.proprioceptive_consequences,
        )
        .unwrap();
        let shared = prepare_complete_joint_field_admitted_fixture(&source, 0).unwrap();
        let anatomy =
            ProprioceptiveReceptorAnatomy::new(exact(4, 1), exact(1, 1), exact(1, 2), exact(1, 1))
                .unwrap();
        let load = derive_effector_load_receptor_sample_range_work(
            &source,
            bind_neuron_perspective(&shared, 3, 0).unwrap(),
            &anatomy,
            0,
            1,
        )
        .unwrap();
        assert_eq!(load.elementary_reaction_energy_zeptojoules, exact(1, 500));
        assert_eq!(load.transduced_energy_zeptojoules, exact(12, 25));
        assert!(matches!(
            derive_proprioceptive_receptor_sample_range_work(
                &source,
                bind_neuron_perspective(&shared, 3, 0).unwrap(),
                &anatomy,
                0,
                1,
            ),
            Err(ProprioceptiveReceptorWorkError::PhysicalQuantityMismatch)
        ));
    }

    #[test]
    fn load_reaction_retires_the_rejected_fraction_law_and_stays_on_fixed_lattice() {
        let legacy = ExactRational::new(
            89_944_548_734_250_453_566_320_293_935_785_217,
            2_188_066_187_409_036_581_378_096_062_335_225_000,
        )
        .unwrap();
        let elementary = exact(1, 500);
        let lattice = exact(1, 16);
        assert_eq!(
            canonical_effector_load_predecessor_residue(legacy, &elementary, &lattice).unwrap(),
            ExactRational::integer(0),
        );
        let first = quantize_proprioceptive_delivery(
            &exact(12, 25),
            canonical_effector_load_predecessor_residue(legacy, &elementary, &lattice).unwrap(),
            &lattice,
            17,
            52,
        )
        .unwrap();
        assert_eq!(first.delivered_quanta, 0);
        assert_eq!(first.successor_residue, ExactRational::new(12, 25).unwrap());
        let second = quantize_proprioceptive_delivery(
            &exact(12, 25),
            first.successor_residue,
            &lattice,
            17,
            52,
        )
        .unwrap();
        assert_eq!(second.delivered_quanta, 0);
        let third = quantize_proprioceptive_delivery(
            &exact(12, 25),
            second.successor_residue,
            &lattice,
            17,
            52,
        )
        .unwrap();
        assert_eq!(third.delivered_quanta, 23);
        assert!(exact_rational_to_big(third.successor_residue) < lattice);
    }
}
