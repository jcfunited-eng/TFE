//! Borrowed complete-neuron admission over one prepared mounted generation.
//!
//! The prepared generation already owns the authenticated source, complete
//! L0--L4 field, neuron perspective, predecessor DSF-delivery impression, and
//! successor DSF-delivery impression. This boundary borrows those exact typed
//! values once per reached
//! neuron. It does not reduce them to receipts, rebuild them, copy their bodies,
//! or claim biological transduction from dimensionless virtual input.

use crate::joint_field_l0_l4::{
    DsfDeliveryImpression, JointFieldExperience, NeuronFieldPerspective,
};
use crate::joint_source_episode::JointSourcePortView;
use crate::mounted_joint_fractal::{
    PreparedMountedFieldSettlement, PreparedMountedGeneration, PreparedMountedNeuronTransition,
};
use crate::reached_vestibular_bundle_path::ReachedVestibularBundleTick;
use crate::vestibular_joint_source_builder::{
    admit_same_cause_vestibular_joint_source_interval, VestibularJointSourceAdmission,
    VestibularJointSourceError,
};
use crate::vestibular_neuron_path::{
    transduce_functional_vestibular_interval, FunctionalVestibularAnatomy,
    FunctionalVestibularError, FunctionalVestibularTransduction,
};
use crate::virtual_body_yaw_motion::YawBodyState;

const TYPED_SENSE_COUNT: usize = 6;

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) enum VirtualTemporalObservation {
    ObservedChanging,
    ObservedQuiescent,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) enum ReceptorPhysicsUnavailable {
    DimensionlessInputWithoutCalibratedStimulusOrKinetics,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) enum PhysicalTransductionAvailability {
    Unavailable(ReceptorPhysicsUnavailable),
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) enum ResidentVestibularIngressError {
    Source(VestibularJointSourceError),
    Transduction(FunctionalVestibularError),
}

pub(crate) struct ResidentVestibularIngress {
    source_tick: u64,
    predecessor_body: YawBodyState,
    successor_body: YawBodyState,
    source: VestibularJointSourceAdmission,
    receptor_anatomy: FunctionalVestibularAnatomy,
    transduction: FunctionalVestibularTransduction,
}

impl ResidentVestibularIngress {
    pub(crate) fn source_tick(&self) -> u64 {
        self.source_tick
    }

    pub(crate) fn predecessor_body(&self) -> YawBodyState {
        self.predecessor_body
    }

    pub(crate) fn successor_body(&self) -> YawBodyState {
        self.successor_body
    }

    pub(crate) fn source(&self) -> &VestibularJointSourceAdmission {
        &self.source
    }

    pub(crate) fn receptor_anatomy(&self) -> &FunctionalVestibularAnatomy {
        &self.receptor_anatomy
    }

    pub(crate) fn transduction(&self) -> &FunctionalVestibularTransduction {
        &self.transduction
    }
}

/// Admit one already-settled vestibular tick as both the joint source and the
/// receptor's physical input. Source admission owns the tick first; receptor
/// transduction consumes that exact admitted value without settling canal or
/// bundle mechanics again.
pub(crate) fn prepare_resident_vestibular_ingress(
    source_tick: u64,
    predecessor_body: YawBodyState,
    successor_body: YawBodyState,
    reached_tick: ReachedVestibularBundleTick,
    receptor_anatomy: &FunctionalVestibularAnatomy,
) -> Result<ResidentVestibularIngress, ResidentVestibularIngressError> {
    let source = admit_same_cause_vestibular_joint_source_interval(
        source_tick,
        predecessor_body,
        successor_body,
        reached_tick,
    )
    .map_err(ResidentVestibularIngressError::Source)?;
    let admitted_tick = *source.mechanical_canal_transition().1;
    let transduction = transduce_functional_vestibular_interval(receptor_anatomy, admitted_tick)
        .map_err(ResidentVestibularIngressError::Transduction)?;
    Ok(ResidentVestibularIngress {
        source_tick,
        predecessor_body,
        successor_body,
        source,
        receptor_anatomy: receptor_anatomy.clone(),
        transduction,
    })
}

/// Ephemeral exact view of one reached neuron. Every large value is borrowed
/// from the prepared generation; constructing the view performs no validation,
/// hashing, source serialization, string cloning, or state transition.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) struct ResidentNeuronAdmission<'a> {
    predecessor_generation: u64,
    successor_generation: u64,
    source_authority: [u8; 32],
    topology_authority: [u8; 32],
    complete_field: &'a JointFieldExperience,
    perspective: &'a NeuronFieldPerspective,
    predecessor_delivery: Option<&'a DsfDeliveryImpression>,
    successor_delivery: &'a DsfDeliveryImpression,
    source_port: &'a JointSourcePortView,
    temporal_observation: VirtualTemporalObservation,
    physical_transduction: PhysicalTransductionAvailability,
}

impl<'a> ResidentNeuronAdmission<'a> {
    fn from_typed_parts(
        prepared: &PreparedMountedGeneration,
        field: &'a PreparedMountedFieldSettlement,
        neuron: &'a PreparedMountedNeuronTransition,
        source_port: &'a JointSourcePortView,
    ) -> Self {
        let temporal_observation = if source_port
            .dimensionless_fields
            .windows(2)
            .all(|pair| pair[0] == pair[1])
        {
            VirtualTemporalObservation::ObservedQuiescent
        } else {
            VirtualTemporalObservation::ObservedChanging
        };
        Self {
            predecessor_generation: prepared.predecessor_generation(),
            successor_generation: prepared.successor_generation(),
            source_authority: prepared.source_authority(),
            topology_authority: field.topology_authority(),
            complete_field: field.experience(),
            perspective: neuron.perspective(),
            predecessor_delivery: neuron.predecessor(),
            successor_delivery: neuron.successor(),
            source_port,
            temporal_observation,
            physical_transduction: PhysicalTransductionAvailability::Unavailable(
                ReceptorPhysicsUnavailable::DimensionlessInputWithoutCalibratedStimulusOrKinetics,
            ),
        }
    }

    pub(crate) fn predecessor_generation(self) -> u64 {
        self.predecessor_generation
    }

    pub(crate) fn successor_generation(self) -> u64 {
        self.successor_generation
    }

    pub(crate) fn source_authority(self) -> [u8; 32] {
        self.source_authority
    }

    pub(crate) fn topology_authority(self) -> [u8; 32] {
        self.topology_authority
    }

    pub(crate) fn complete_field(self) -> &'a JointFieldExperience {
        self.complete_field
    }

    pub(crate) fn perspective(self) -> &'a NeuronFieldPerspective {
        self.perspective
    }

    pub(crate) fn predecessor_delivery(self) -> Option<&'a DsfDeliveryImpression> {
        self.predecessor_delivery
    }

    pub(crate) fn successor_delivery(self) -> &'a DsfDeliveryImpression {
        self.successor_delivery
    }

    pub(crate) fn source_port(self) -> &'a JointSourcePortView {
        self.source_port
    }

    pub(crate) fn temporal_observation(self) -> VirtualTemporalObservation {
        self.temporal_observation
    }

    pub(crate) fn physical_transduction(self) -> PhysicalTransductionAvailability {
        self.physical_transduction
    }
}

#[cfg(test)]
pub(crate) fn inspect_resident_neuron_admission(
    prepared: &PreparedMountedGeneration,
    field_index: usize,
    neuron_index: usize,
) -> ResidentNeuronAdmission<'_> {
    let field = &prepared.fields()[field_index];
    let neuron = &field.neurons()[neuron_index];
    let source_port = &field.source_ports()[neuron.perspective().vertex_index];
    ResidentNeuronAdmission::from_typed_parts(prepared, field, neuron, source_port)
}

/// Fixed-size, non-authoritative observation of work performed at ingress. It
/// contains no source, field, neuron, physical, or cognitive body.
#[derive(Clone, Copy, Debug, Default, Eq, PartialEq)]
pub(crate) struct ResidentReceptorIngressObservation {
    field_count: usize,
    witness_count: usize,
    sense_counts: [usize; TYPED_SENSE_COUNT],
    changing_count: usize,
    quiescent_count: usize,
    reached_neuron_visit_count: usize,
    witness_construction_count: usize,
}

impl ResidentReceptorIngressObservation {
    pub(crate) fn checked_merge(self, observed: Self) -> Option<Self> {
        let mut sense_counts = [0usize; TYPED_SENSE_COUNT];
        for (index, value) in sense_counts.iter_mut().enumerate() {
            *value = self.sense_counts[index].checked_add(observed.sense_counts[index])?;
        }
        Some(Self {
            field_count: self.field_count.checked_add(observed.field_count)?,
            witness_count: self.witness_count.checked_add(observed.witness_count)?,
            sense_counts,
            changing_count: self.changing_count.checked_add(observed.changing_count)?,
            quiescent_count: self.quiescent_count.checked_add(observed.quiescent_count)?,
            reached_neuron_visit_count: self
                .reached_neuron_visit_count
                .checked_add(observed.reached_neuron_visit_count)?,
            witness_construction_count: self
                .witness_construction_count
                .checked_add(observed.witness_construction_count)?,
        })
    }

    pub(crate) fn field_count(self) -> usize {
        self.field_count
    }

    pub(crate) fn witness_count(self) -> usize {
        self.witness_count
    }

    pub(crate) fn sense_counts(self) -> [usize; TYPED_SENSE_COUNT] {
        self.sense_counts
    }

    pub(crate) fn changing_count(self) -> usize {
        self.changing_count
    }

    pub(crate) fn quiescent_count(self) -> usize {
        self.quiescent_count
    }

    pub(crate) fn reached_neuron_visit_count(self) -> usize {
        self.reached_neuron_visit_count
    }

    pub(crate) fn witness_construction_count(self) -> usize {
        self.witness_construction_count
    }
}

pub(crate) fn prepare_resident_receptor_ingress(
    prepared: &PreparedMountedGeneration,
) -> ResidentReceptorIngressObservation {
    let mut witness_count = 0usize;
    let mut sense_counts = [0usize; TYPED_SENSE_COUNT];
    let mut changing_count = 0usize;
    let mut quiescent_count = 0usize;
    let mut reached_neuron_visit_count = 0usize;
    let mut witness_construction_count = 0usize;

    for field in prepared.fields() {
        for neuron in field.neurons() {
            reached_neuron_visit_count += 1;
            let source_port = &field.source_ports()[neuron.perspective().vertex_index];
            let admission =
                ResidentNeuronAdmission::from_typed_parts(prepared, field, neuron, source_port);
            witness_construction_count += 1;
            witness_count += 1;
            sense_counts[usize::from(admission.source_port().sense)] += 1;
            match admission.temporal_observation() {
                VirtualTemporalObservation::ObservedChanging => {
                    changing_count += 1;
                }
                VirtualTemporalObservation::ObservedQuiescent => {
                    quiescent_count += 1;
                }
            }
        }
    }

    ResidentReceptorIngressObservation {
        field_count: prepared.fields().len(),
        witness_count,
        sense_counts,
        changing_count,
        quiescent_count,
        reached_neuron_visit_count,
        witness_construction_count,
    }
}

/// Observe the typed receptors that reached the canonical UF-v1.4 cognition
/// path directly from the immutable source.  This does not construct or visit
/// the retired near-v1.3 mounted-delivery witnesses.
pub(crate) fn observe_canonical_receptor_ingress(
    source: &crate::joint_source_episode::NativeJointSourceEpisode,
) -> ResidentReceptorIngressObservation {
    let mut sense_counts = [0usize; TYPED_SENSE_COUNT];
    let mut changing_count = 0usize;
    let mut quiescent_count = 0usize;
    for port in source.joint_source_ports() {
        sense_counts[usize::from(port.sense)] += 1;
        if port
            .dimensionless_fields
            .windows(2)
            .all(|pair| pair[0] == pair[1])
        {
            quiescent_count += 1;
        } else {
            changing_count += 1;
        }
    }
    let reached = source.joint_source_ports().len();
    ResidentReceptorIngressObservation {
        field_count: source.joint_source_occurrences().len(),
        witness_count: reached,
        sense_counts,
        changing_count,
        quiescent_count,
        reached_neuron_visit_count: reached,
        witness_construction_count: 0,
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::exact_rational::ExactRational;
    use crate::local_cupula_hair_bundle_geometry::LocalCupulaBundleAnatomy;
    use crate::local_gating_spring_energy::GatingSpringEnergyAnatomy;
    use crate::local_tip_link_extension::TipLinkInsertionGeometry;
    use crate::reached_vestibular_bundle_path::settle_reached_vestibular_bundle_tick as externally_settle_tick;
    use crate::virtual_body_yaw_motion::{settle_signed_yaw_actuation, SignedYawActuation};
    use crate::virtual_vestibular_canal::{
        CanalAnatomy, CanalState, PositiveRatio, WORLD_MECHANICAL_TICK_MICROSECONDS,
    };

    fn receptor_anatomy() -> FunctionalVestibularAnatomy {
        FunctionalVestibularAnatomy::new(
            CanalAnatomy::new(6, 13_200, PositiveRatio::new(25, 1).unwrap()).unwrap(),
            LocalCupulaBundleAnatomy::new(2, 5, 20_000).unwrap(),
            TipLinkInsertionGeometry::new(500).unwrap(),
            GatingSpringEnergyAnatomy::new(
                ExactRational::integer(1),
                ExactRational::integer(4),
                ExactRational::integer(2),
                ExactRational::integer(8),
            )
            .unwrap(),
        )
        .unwrap()
    }

    #[test]
    fn one_settled_tick_is_the_exact_source_and_receptor_occurrence() {
        let anatomy = receptor_anatomy();
        let predecessor_body = YawBodyState::new(0).unwrap();
        let body = settle_signed_yaw_actuation(
            predecessor_body,
            SignedYawActuation::new(64, WORLD_MECHANICAL_TICK_MICROSECONDS).unwrap(),
        )
        .unwrap();
        let reached_tick = externally_settle_tick(
            CanalAnatomy::new(6, 13_200, PositiveRatio::new(25, 1).unwrap()).unwrap(),
            CanalState::at_rest(),
            body.trajectory.as_slice()[0],
            LocalCupulaBundleAnatomy::new(2, 5, 20_000).unwrap(),
        )
        .unwrap();
        let ingress = prepare_resident_vestibular_ingress(
            41,
            predecessor_body,
            body.successor,
            reached_tick,
            &anatomy,
        )
        .unwrap();
        let source_tick = *ingress.source().mechanical_canal_transition().1;
        assert_eq!(ingress.source_tick(), 41);
        assert_eq!(ingress.predecessor_body(), predecessor_body);
        assert_eq!(ingress.successor_body(), body.successor);
        assert_eq!(ingress.receptor_anatomy(), &anatomy);
        assert_eq!(source_tick, ingress.transduction().reached_tick);
        assert_eq!(source_tick, reached_tick);
        let (episode, contacts) = ingress.source().joint_source_with_contacts();
        assert_eq!(episode.joint_source_occurrences().len(), 1);
        assert!(contacts.is_empty());
    }

    #[test]
    fn body_successor_mismatch_is_refused_before_ingress_custody_exists() {
        let anatomy = receptor_anatomy();
        let predecessor_body = YawBodyState::new(0).unwrap();
        let reached_tick = externally_settle_tick(
            CanalAnatomy::new(6, 13_200, PositiveRatio::new(25, 1).unwrap()).unwrap(),
            CanalState::at_rest(),
            64,
            LocalCupulaBundleAnatomy::new(2, 5, 20_000).unwrap(),
        )
        .unwrap();
        assert!(matches!(
            prepare_resident_vestibular_ingress(
                41,
                predecessor_body,
                YawBodyState::new(63).unwrap(),
                reached_tick,
                &anatomy,
            ),
            Err(ResidentVestibularIngressError::Source(
                VestibularJointSourceError::BodySuccessorMismatch
            ))
        ));
    }

    #[test]
    fn resident_ingress_source_contains_no_mechanical_settlement_call() {
        let source = include_str!("resident_receptor_transition.rs");
        let forbidden_call = ["settle_reached_vestibular_", "bundle_tick("].concat();
        assert!(!source.contains(&forbidden_call));
    }
}
