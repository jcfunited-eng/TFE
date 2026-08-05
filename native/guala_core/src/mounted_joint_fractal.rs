//! Persistent mounting of the exact joint field and reached DSF deliveries.
//!
//! This state is embedded inside the single owner-free materialized-fabric
//! transition. It retains one current exact joint-field authority per mounted
//! physical topology and one current compact delivery impression per reached
//! receptor lineage. A delivery impression is not a neuronal fractal. It
//! does not create mosaics, assign meaning, align clocks, or choose growth.

#[cfg(test)]
use crate::joint_field_l0_l4::reconstruct_cohesion;
use crate::joint_field_l0_l4::{
    bind_neuron_perspective, derive_requirement, run_joint_field_l0_l4,
    settle_dsf_delivery_impression, verify_dsf_delivery_impression, DsfDeliveryImpression,
    DsfDeliveryRecurrence, Exact, JointFieldBudget, JointFieldExperience, JointFieldInput,
    RelationFact, StructuralTrit,
};
use crate::joint_source_episode::{
    JointSourceCoordinate, JointSourcePortView, NativeJointSourceEpisode,
};
use crate::sha256::sha256;
use num_bigint::BigInt;
use num_rational::BigRational;
use num_traits::Zero;
use std::collections::{BTreeMap, BTreeSet};
use std::mem::size_of;
use std::sync::Arc;

const MAGIC: &[u8; 8] = b"GLJDSF03";
const VERSION: u16 = 3;
const PRIOR_MAGIC: &[u8; 8] = b"GLJNFT02";
const PRIOR_VERSION: u16 = 2;
const LEGACY_MAGIC: &[u8; 8] = b"GLJNFT01";
const LEGACY_VERSION: u16 = 1;
const LINEAGE_DOMAIN: &[u8; 8] = b"GLNLINE1";
const EPISODE_RELATION: &[u8] = b"co_observed_capture_occurrence";

#[derive(Clone, Debug, Eq, PartialEq, Ord, PartialOrd)]
struct PhysicalPortKey {
    sense: u8,
    topology_index: u32,
    sensor_id: String,
    substream_id: String,
    coordinates: Vec<JointSourceCoordinate>,
    physical_quantity: String,
    physical_unit: String,
    relevance_rule: String,
    relevance_origin: Option<String>,
    input_map_id: String,
    source_min: BigRational,
    source_max: BigRational,
    field_offset: BigRational,
    field_scale: BigRational,
    input_map_profile: Vec<u8>,
    input_map_group_receipt: [u8; 32],
}

#[derive(Clone, Debug, Eq, PartialEq)]
struct JointFieldSnapshot {
    topology_receipt: [u8; 32],
    group_authority_receipts: Vec<[u8; 32]>,
    input: JointFieldInput,
    experience_receipt: [u8; 32],
    complete_l4_receipt: [u8; 32],
}

#[derive(Clone, Debug, Eq, PartialEq)]
struct EpisodeFieldReference {
    topology_receipt: [u8; 32],
    exact_clock_receipt: [u8; 32],
}

#[derive(Clone, Debug, Eq, PartialEq)]
struct EpisodeRelationCandidate {
    source_authority_receipt: [u8; 32],
    fields: Vec<EpisodeFieldReference>,
    participating_lineages: Vec<[u8; 16]>,
    common_physical_cause_resolved: bool,
    predecessor_candidate_receipt: Option<[u8; 32]>,
    authority_receipt: [u8; 32],
}

#[derive(Clone, Debug, Eq, PartialEq)]
struct MountedNeuron {
    key: PhysicalPortKey,
    lineage: [u8; 16],
    topology_receipt: [u8; 32],
    delivery_impression: DsfDeliveryImpression,
    transition_count: u64,
}

#[derive(Clone, Debug, Eq, PartialEq)]
struct State {
    generation: u64,
    next_lineage_ordinal: u64,
    source_authority_receipt: [u8; 32],
    last_transition_receipt: Option<[u8; 32]>,
    fields: Vec<JointFieldSnapshot>,
    neurons: Vec<MountedNeuron>,
    episode_relation_candidate: Option<EpisodeRelationCandidate>,
}

impl Default for State {
    fn default() -> Self {
        Self {
            generation: 0,
            next_lineage_ordinal: 1,
            source_authority_receipt: [0; 32],
            last_transition_receipt: None,
            fields: Vec::new(),
            neurons: Vec::new(),
            episode_relation_candidate: None,
        }
    }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) struct MountedJointDsfTransition {
    pub(crate) joint_field_count: usize,
    pub(crate) joint_neuron_count: usize,
    pub(crate) l0_l4_evaluation_count: usize,
    pub(crate) dsf_delivery_count: usize,
    pub(crate) recurrent_dsf_delivery_count: usize,
    pub(crate) transition_receipt: Option<[u8; 32]>,
    pub(crate) episode_relation_candidate_receipt: Option<[u8; 32]>,
}

/// Exact cost paid only when a caller supplies a serialized predecessor rather
/// than an already-resident mounted generation.  Every retained predecessor
/// field is rebuilt once to prove that its persisted L4 authority still follows
/// from its persisted full input.  The newly observed generation is not part of
/// this count.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) struct MountedRestoreValidationCost {
    pub(crate) rebuilt_predecessor_field_count: usize,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) struct ResidentMountedRestoreWork {
    pub(crate) authentication_count: usize,
    pub(crate) decode_count: usize,
    pub(crate) rebuilt_predecessor_field_count: usize,
}

/// One already-authenticated mounted generation. Its typed predecessor state is
/// intentionally opaque so recurrence cannot bypass the mounted transition.
#[derive(Debug, Eq, PartialEq)]
pub(crate) struct ResidentMountedState {
    state: State,
    cold_restore_work: ResidentMountedRestoreWork,
}

impl ResidentMountedState {
    pub(crate) fn summary(&self) -> MountedJointDsfSummary {
        mounted_summary(&self.state)
    }

    pub(crate) fn cold_restore_work(&self) -> ResidentMountedRestoreWork {
        self.cold_restore_work
    }
}

/// One neuron delivery retained at the mounted-generation boundary.  These are
/// the same typed values used by settlement; they are not decoded back out of
/// the successor body.
#[derive(Debug, Eq, PartialEq)]
pub(crate) struct PreparedMountedNeuronTransition {
    predecessor_generation: u64,
    successor_generation: u64,
    topology_authority: [u8; 32],
    perspective: crate::joint_field_l0_l4::NeuronFieldPerspective,
    predecessor: Option<DsfDeliveryImpression>,
    successor: DsfDeliveryImpression,
}

impl PreparedMountedNeuronTransition {
    pub(crate) fn predecessor_generation(&self) -> u64 {
        self.predecessor_generation
    }

    pub(crate) fn successor_generation(&self) -> u64 {
        self.successor_generation
    }

    pub(crate) fn topology_authority(&self) -> [u8; 32] {
        self.topology_authority
    }

    pub(crate) fn perspective(&self) -> &crate::joint_field_l0_l4::NeuronFieldPerspective {
        &self.perspective
    }

    pub(crate) fn predecessor(&self) -> Option<&DsfDeliveryImpression> {
        self.predecessor.as_ref()
    }

    pub(crate) fn successor(&self) -> &DsfDeliveryImpression {
        &self.successor
    }
}

/// One full L0--L4 cohort and the exact neuron deliveries bound from it.  The
/// complete field remains the original Arc-backed L4 value produced by this
/// generation's kernel evaluation.
#[derive(Debug, Eq, PartialEq)]
pub(crate) struct PreparedMountedFieldSettlement {
    topology_authority: [u8; 32],
    source_ports: Vec<JointSourcePortView>,
    experience: JointFieldExperience,
    neurons: Vec<PreparedMountedNeuronTransition>,
}

impl PreparedMountedFieldSettlement {
    pub(crate) fn topology_authority(&self) -> [u8; 32] {
        self.topology_authority
    }

    pub(crate) fn experience(&self) -> &JointFieldExperience {
        &self.experience
    }

    pub(crate) fn source_ports(&self) -> &[JointSourcePortView] {
        &self.source_ports
    }

    pub(crate) fn neurons(&self) -> &[PreparedMountedNeuronTransition] {
        &self.neurons
    }
}

/// A prepared but unpublished mounted generation.  Downstream physical, K and
/// hippocampal preparation consumes these typed settlements before the encoded
/// state is moved to the publication boundary.
#[derive(Debug, Eq, PartialEq)]
pub(crate) struct PreparedMountedGeneration {
    predecessor_generation: u64,
    successor_generation: u64,
    source_authority: [u8; 32],
    source_body: Arc<[u8]>,
    restore_validation_cost: MountedRestoreValidationCost,
    fields: Vec<PreparedMountedFieldSettlement>,
    state_bytes: Vec<u8>,
    transition: MountedJointDsfTransition,
    successor_resident_state: ResidentMountedState,
    phase_counts: MountedTransitionPhaseCounts,
}

impl PreparedMountedGeneration {
    pub(crate) fn predecessor_generation(&self) -> u64 {
        self.predecessor_generation
    }

    pub(crate) fn successor_generation(&self) -> u64 {
        self.successor_generation
    }

    pub(crate) fn source_authority(&self) -> [u8; 32] {
        self.source_authority
    }

    pub(crate) fn source_body(&self) -> &[u8] {
        &self.source_body
    }

    pub(crate) fn restore_validation_cost(&self) -> MountedRestoreValidationCost {
        self.restore_validation_cost
    }

    pub(crate) fn fields(&self) -> &[PreparedMountedFieldSettlement] {
        &self.fields
    }

    pub(crate) fn state_bytes(&self) -> &[u8] {
        &self.state_bytes
    }

    pub(crate) fn transition(&self) -> &MountedJointDsfTransition {
        &self.transition
    }

    pub(crate) fn successor_resident_state(&self) -> &ResidentMountedState {
        &self.successor_resident_state
    }

    pub(crate) fn phase_counts(&self) -> MountedTransitionPhaseCounts {
        self.phase_counts
    }

    pub(crate) fn into_serialized_parts(self) -> (Vec<u8>, MountedJointDsfTransition) {
        (self.state_bytes, self.transition)
    }

    pub(crate) fn into_resident_parts(
        self,
    ) -> (ResidentMountedState, Vec<u8>, MountedJointDsfTransition) {
        (
            self.successor_resident_state,
            self.state_bytes,
            self.transition,
        )
    }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) struct MountedJointDsfSummary {
    pub(crate) generation: u64,
    pub(crate) joint_field_count: usize,
    pub(crate) joint_neuron_count: usize,
    pub(crate) transition_receipt: Option<[u8; 32]>,
    pub(crate) episode_relation_candidate_receipt: Option<[u8; 32]>,
}

/// The only receptor-port identity that production D2 GLJNFT02 actually
/// retained. These four fields and the mounted lineage are source evidence;
/// they are not physical anatomy.
#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) struct LegacyMountedNeuronPortInspection {
    pub(crate) lineage: [u8; 16],
    pub(crate) sense: u8,
    pub(crate) topology_index: u32,
    pub(crate) sensor_id: String,
    pub(crate) substream_id: String,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) struct LegacyMountedJointInspection {
    pub(crate) generation: u64,
    pub(crate) next_lineage_ordinal: u64,
    pub(crate) neurons: Vec<LegacyMountedNeuronPortInspection>,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) struct DerivedJointFieldInput {
    pub(crate) input: JointFieldInput,
    pub(crate) topology_authority: [u8; 32],
}

#[derive(Clone, Copy, Debug, Default, Eq, PartialEq)]
pub(crate) struct MountedTransitionPhaseCounts {
    pub(crate) predecessor_authentication_count: usize,
    pub(crate) predecessor_decode_count: usize,
    pub(crate) predecessor_rebuilt_field_count: usize,
    pub(crate) retained_neuron_index_entry_count: usize,
    pub(crate) reached_neuron_lookup_count: usize,
    pub(crate) current_cohort_evaluation_count: usize,
    pub(crate) successor_seal_count: usize,
}

struct ResolvedMountedNeuron {
    neuron_index: usize,
    lineage: [u8; 16],
    predecessor: Option<DsfDeliveryImpression>,
}

struct ResolvedMountedCohort {
    source_ports: Vec<JointSourcePortView>,
    input: JointFieldInput,
    requirement: crate::joint_field_l0_l4::JointFieldRequirement,
    group_authority_receipts: Vec<[u8; 32]>,
    topology_authority: [u8; 32],
    neurons: Vec<ResolvedMountedNeuron>,
}

struct ResolvedMountedTransition {
    state: State,
    predecessor_generation: u64,
    prior_episode_relation_candidate: Option<EpisodeRelationCandidate>,
    restore_validation_cost: MountedRestoreValidationCost,
    source_body: Arc<[u8]>,
    cohorts: Vec<ResolvedMountedCohort>,
    max_state_bytes: usize,
    retained_neuron_index_entry_count: usize,
    reached_neuron_lookup_count: usize,
    cold_restore_work: ResidentMountedRestoreWork,
}

struct CalculatedMountedNeuron {
    neuron_index: usize,
    perspective: crate::joint_field_l0_l4::NeuronFieldPerspective,
    predecessor: Option<DsfDeliveryImpression>,
    successor: DsfDeliveryImpression,
}

struct CalculatedMountedCohort {
    source_ports: Vec<JointSourcePortView>,
    input: JointFieldInput,
    group_authority_receipts: Vec<[u8; 32]>,
    topology_authority: [u8; 32],
    experience: JointFieldExperience,
    neurons: Vec<CalculatedMountedNeuron>,
}

struct CalculatedMountedTransition {
    state: State,
    predecessor_generation: u64,
    prior_episode_relation_candidate: Option<EpisodeRelationCandidate>,
    restore_validation_cost: MountedRestoreValidationCost,
    source_body: Arc<[u8]>,
    cohorts: Vec<CalculatedMountedCohort>,
    max_state_bytes: usize,
    retained_neuron_index_entry_count: usize,
    reached_neuron_lookup_count: usize,
    l0_l4_evaluation_count: usize,
    cold_restore_work: ResidentMountedRestoreWork,
}

pub(crate) fn derive_joint_field_inputs(
    source: &NativeJointSourceEpisode,
) -> Result<Vec<DerivedJointFieldInput>, String> {
    exact_time_cohorts(source.joint_source_ports().to_vec())?
        .into_iter()
        .map(|cohort| {
            let (input, _, _, topology_authority) = joint_input(&cohort)?;
            Ok(DerivedJointFieldInput {
                input,
                topology_authority,
            })
        })
        .collect()
}

/// Legacy serialized predecessor boundary retained for migration and tests.
/// A resident runtime restores once and calls
/// [`prepare_resident_mounted_generation`] for every subsequent generation.
pub(crate) fn transition_mounted_joint_dsf(
    prior_state: &[u8],
    source: &NativeJointSourceEpisode,
    max_state_bytes: usize,
    max_working_bytes: usize,
) -> Result<PreparedMountedGeneration, String> {
    transition_mounted_joint_dsf_with(
        prior_state,
        source,
        max_state_bytes,
        max_working_bytes,
        run_joint_field_l0_l4,
    )
}

/// Perform the one admitted cold decode and full predecessor-field proof needed
/// to establish a typed resident mounted state.
pub(crate) fn restore_resident_mounted_state(
    state_bytes: &[u8],
    max_state_bytes: usize,
    max_working_bytes: usize,
) -> Result<(ResidentMountedState, MountedJointDsfSummary), String> {
    if max_state_bytes == 0 || max_working_bytes == 0 {
        return Err("joint-DSF state or working memory is not admitted".into());
    }
    let (state, decode_count, validation_cost) = if state_bytes.is_empty() {
        (
            State::default(),
            0,
            MountedRestoreValidationCost {
                rebuilt_predecessor_field_count: 0,
            },
        )
    } else {
        let (state, validation_cost) =
            restore_state_with_physics_validation(state_bytes, max_state_bytes, max_working_bytes)?;
        (state, 1, validation_cost)
    };
    let summary = mounted_summary(&state);
    Ok((
        ResidentMountedState {
            state,
            cold_restore_work: ResidentMountedRestoreWork {
                authentication_count: 1,
                decode_count,
                rebuilt_predecessor_field_count: validation_cost.rebuilt_predecessor_field_count,
            },
        },
        summary,
    ))
}

/// Prepare one successor from typed resident custody. This path evaluates only
/// current source cohorts; it performs no predecessor decode or L0--L4 replay.
pub(crate) fn prepare_resident_mounted_generation(
    predecessor: &ResidentMountedState,
    source: &NativeJointSourceEpisode,
    max_state_bytes: usize,
    max_working_bytes: usize,
) -> Result<PreparedMountedGeneration, String> {
    prepare_resident_mounted_generation_with(
        predecessor,
        source,
        max_state_bytes,
        max_working_bytes,
        run_joint_field_l0_l4,
    )
}

fn transition_mounted_joint_dsf_with<F>(
    prior_state: &[u8],
    source: &NativeJointSourceEpisode,
    max_state_bytes: usize,
    max_working_bytes: usize,
    mut evaluate: F,
) -> Result<PreparedMountedGeneration, String>
where
    F: FnMut(
        JointFieldInput,
        JointFieldBudget,
    ) -> Result<JointFieldExperience, crate::joint_field_l0_l4::JointFieldError>,
{
    let (resident, _) =
        restore_resident_mounted_state(prior_state, max_state_bytes, max_working_bytes)?;
    let cold_restore_work = resident.cold_restore_work();
    let mut prepared = prepare_resident_mounted_generation_with(
        &resident,
        source,
        max_state_bytes,
        max_working_bytes,
        &mut evaluate,
    )?;
    prepared.restore_validation_cost = MountedRestoreValidationCost {
        rebuilt_predecessor_field_count: cold_restore_work.rebuilt_predecessor_field_count,
    };
    prepared.phase_counts.predecessor_authentication_count = cold_restore_work.authentication_count;
    prepared.phase_counts.predecessor_decode_count = cold_restore_work.decode_count;
    prepared.phase_counts.predecessor_rebuilt_field_count =
        cold_restore_work.rebuilt_predecessor_field_count;
    Ok(prepared)
}

fn prepare_resident_mounted_generation_with<F>(
    predecessor: &ResidentMountedState,
    source: &NativeJointSourceEpisode,
    max_state_bytes: usize,
    max_working_bytes: usize,
    mut evaluate: F,
) -> Result<PreparedMountedGeneration, String>
where
    F: FnMut(
        JointFieldInput,
        JointFieldBudget,
    ) -> Result<JointFieldExperience, crate::joint_field_l0_l4::JointFieldError>,
{
    let resolved = resolve_resident_mounted_transition(
        predecessor,
        source,
        max_state_bytes,
        max_working_bytes,
    )?;
    let calculated = evaluate_reached_mounted_transition(resolved, &mut evaluate)?;
    seal_mounted_transition(calculated)
}

/// Admit exact source cohorts and resolve every reached neuron and recurrence
/// predecessor from an already-authenticated typed resident state.
fn resolve_resident_mounted_transition(
    predecessor: &ResidentMountedState,
    source: &NativeJointSourceEpisode,
    max_state_bytes: usize,
    max_working_bytes: usize,
) -> Result<ResolvedMountedTransition, String> {
    if max_state_bytes == 0 || max_working_bytes == 0 {
        return Err("joint-DSF state or working memory is not admitted".into());
    }
    let mut state = predecessor.state.clone();
    let restore_validation_cost = MountedRestoreValidationCost {
        rebuilt_predecessor_field_count: 0,
    };
    let predecessor_generation = state.generation;
    let prior_episode_relation_candidate = state.episode_relation_candidate.clone();
    state.generation = state
        .generation
        .checked_add(1)
        .ok_or("joint-DSF generation overflow")?;
    state.source_authority_receipt = source.joint_source_authority_receipt();

    let retained_neuron_index_entry_count = state.neurons.len();
    let mut neuron_indices = mounted_neuron_indices(&state);
    let mut reached_neuron_lookup_count = 0usize;
    let mut resolved_cohorts = Vec::new();
    for source_ports in exact_time_cohorts(source.joint_source_ports().to_vec())? {
        let (input, keys, group_authority_receipts, topology_authority) =
            joint_input(&source_ports)?;
        let requirement = derive_requirement(&input).map_err(|error| error.to_string())?;
        let working_bytes = derived_working_bytes(&input, &requirement)?;
        if working_bytes > max_working_bytes {
            return Err(format!(
                "joint field requires {working_bytes} derived working bytes, admitted {max_working_bytes}"
            ));
        }
        let mut neurons = Vec::with_capacity(keys.len());
        for key in keys {
            reached_neuron_lookup_count = reached_neuron_lookup_count
                .checked_add(1)
                .ok_or("joint reached-neuron lookup count overflow")?;
            let neuron_index = find_or_create_neuron_indexed(&mut state, &mut neuron_indices, key)?;
            let neuron = &state.neurons[neuron_index];
            let predecessor = (neuron.transition_count > 0
                && neuron.topology_receipt == topology_authority)
                .then(|| neuron.delivery_impression.clone());
            neurons.push(ResolvedMountedNeuron {
                neuron_index,
                lineage: neuron.lineage,
                predecessor,
            });
        }
        resolved_cohorts.push(ResolvedMountedCohort {
            source_ports,
            input,
            requirement,
            group_authority_receipts,
            topology_authority,
            neurons,
        });
    }
    let mut topology_authorities = resolved_cohorts
        .iter()
        .map(|cohort| cohort.topology_authority)
        .collect::<Vec<_>>();
    topology_authorities.sort_unstable();
    if topology_authorities
        .windows(2)
        .any(|pair| pair[0] == pair[1])
    {
        return Err("joint field repeats a physical topology".into());
    }
    Ok(ResolvedMountedTransition {
        state,
        predecessor_generation,
        prior_episode_relation_candidate,
        restore_validation_cost,
        source_body: source.joint_source_body(),
        cohorts: resolved_cohorts,
        max_state_bytes,
        retained_neuron_index_entry_count,
        reached_neuron_lookup_count,
        cold_restore_work: predecessor.cold_restore_work,
    })
}

/// The smallest safe mounted calculation boundary. The frozen L0--L4,
/// perspective and delivery-impression functions still seal their own receipts
/// transitively, so this stage is deliberately not described as digest-free.
fn evaluate_reached_mounted_transition<F>(
    resolved: ResolvedMountedTransition,
    evaluate: &mut F,
) -> Result<CalculatedMountedTransition, String>
where
    F: FnMut(
        JointFieldInput,
        JointFieldBudget,
    ) -> Result<JointFieldExperience, crate::joint_field_l0_l4::JointFieldError>,
{
    let mut calculated_cohorts = Vec::with_capacity(resolved.cohorts.len());
    let mut l0_l4_evaluation_count = 0usize;
    for cohort in resolved.cohorts {
        let experience = evaluate(
            cohort.input.clone(),
            JointFieldBudget {
                max_input_bytes: cohort.requirement.input_bytes,
                max_vertices: cohort.requirement.vertices,
                max_frames: cohort.requirement.frames,
                max_edges: cohort.requirement.edges,
                max_relation_facts: cohort.requirement.relation_facts,
                max_vertex_frame_values: cohort.requirement.vertex_frame_values,
            },
        )
        .map_err(|error| error.to_string())?;
        l0_l4_evaluation_count = l0_l4_evaluation_count
            .checked_add(1)
            .ok_or("joint L0-L4 evaluation count overflow")?;
        let frame_index = cohort.requirement.frames - 1;
        let mut neurons = Vec::with_capacity(cohort.neurons.len());
        for (vertex_index, resolved_neuron) in cohort.neurons.into_iter().enumerate() {
            let perspective = bind_neuron_perspective(
                &experience.l4,
                resolved_neuron.lineage,
                vertex_index,
                frame_index,
            )
            .map_err(|error| error.to_string())?;
            let successor = settle_dsf_delivery_impression(
                &experience.l4,
                &perspective,
                resolved_neuron.predecessor.as_ref(),
            )
            .map_err(|error| error.to_string())?;
            neurons.push(CalculatedMountedNeuron {
                neuron_index: resolved_neuron.neuron_index,
                perspective,
                predecessor: resolved_neuron.predecessor,
                successor,
            });
        }
        calculated_cohorts.push(CalculatedMountedCohort {
            source_ports: cohort.source_ports,
            input: cohort.input,
            group_authority_receipts: cohort.group_authority_receipts,
            topology_authority: cohort.topology_authority,
            experience,
            neurons,
        });
    }
    Ok(CalculatedMountedTransition {
        state: resolved.state,
        predecessor_generation: resolved.predecessor_generation,
        prior_episode_relation_candidate: resolved.prior_episode_relation_candidate,
        restore_validation_cost: resolved.restore_validation_cost,
        source_body: resolved.source_body,
        cohorts: calculated_cohorts,
        max_state_bytes: resolved.max_state_bytes,
        retained_neuron_index_entry_count: resolved.retained_neuron_index_entry_count,
        reached_neuron_lookup_count: resolved.reached_neuron_lookup_count,
        l0_l4_evaluation_count,
        cold_restore_work: resolved.cold_restore_work,
    })
}

/// Assemble authority and persistent custody exactly once from the calculated
/// reached result. Constructor invariants are differentially checked against
/// the former whole-successor validation path in this module's tests.
fn seal_mounted_transition(
    calculated: CalculatedMountedTransition,
) -> Result<PreparedMountedGeneration, String> {
    let CalculatedMountedTransition {
        mut state,
        predecessor_generation,
        prior_episode_relation_candidate,
        restore_validation_cost,
        source_body,
        cohorts,
        max_state_bytes,
        retained_neuron_index_entry_count,
        reached_neuron_lookup_count,
        l0_l4_evaluation_count,
        cold_restore_work,
    } = calculated;
    let mut current_fields = Vec::with_capacity(cohorts.len());
    let mut prepared_fields = Vec::with_capacity(cohorts.len());
    let mut participating_lineages = BTreeSet::new();
    let mut transitioned = 0usize;
    let mut recurrent = 0usize;
    let mut transition_authority = Vec::new();
    transition_authority.extend_from_slice(b"guala.native.mounted_joint_dsf_transition.v1");
    transition_authority.extend_from_slice(&state.generation.to_le_bytes());
    transition_authority.extend_from_slice(&state.source_authority_receipt);

    for cohort in cohorts {
        let mut prepared_neurons = Vec::with_capacity(cohort.neurons.len());
        for calculated_neuron in cohort.neurons {
            transitioned = transitioned
                .checked_add(1)
                .ok_or("joint DSF-delivery count overflow")?;
            if calculated_neuron.predecessor.is_some() {
                recurrent = recurrent
                    .checked_add(1)
                    .ok_or("joint recurrent DSF-delivery count overflow")?;
            }
            transition_authority
                .extend_from_slice(&calculated_neuron.successor.authority_receipt_sha256);
            participating_lineages.insert(calculated_neuron.successor.neuron_lineage);
            let neuron = &mut state.neurons[calculated_neuron.neuron_index];
            neuron.topology_receipt = cohort.topology_authority;
            neuron.delivery_impression = calculated_neuron.successor.clone();
            neuron.transition_count = neuron
                .transition_count
                .checked_add(1)
                .ok_or("joint neuron transition count overflow")?;
            prepared_neurons.push(PreparedMountedNeuronTransition {
                predecessor_generation,
                successor_generation: state.generation,
                topology_authority: cohort.topology_authority,
                perspective: calculated_neuron.perspective,
                predecessor: calculated_neuron.predecessor,
                successor: calculated_neuron.successor,
            });
        }
        current_fields.push(snapshot(
            cohort.input,
            cohort.topology_authority,
            cohort.group_authority_receipts,
            &cohort.experience,
        ));
        prepared_fields.push(PreparedMountedFieldSettlement {
            topology_authority: cohort.topology_authority,
            source_ports: cohort.source_ports,
            experience: cohort.experience,
            neurons: prepared_neurons,
        });
    }

    current_fields.sort_by_key(|field| field.topology_receipt);
    prepared_fields.sort_by_key(|field| field.topology_authority);
    state.fields = current_fields;
    state
        .neurons
        .sort_by(|left, right| left.key.cmp(&right.key));
    state.episode_relation_candidate = build_episode_relation_candidate_with_lineages(
        &state,
        prior_episode_relation_candidate.as_ref(),
        participating_lineages.into_iter().collect(),
    )?;
    let transition_receipt = if transitioned == 0 {
        None
    } else {
        Some(sha256(&transition_authority))
    };
    state.last_transition_receipt = transition_receipt;
    let state_bytes = encode_state(&state)?;
    if state_bytes.len() > max_state_bytes {
        return Err(format!(
            "joint-DSF state requires {} bytes, admitted {max_state_bytes}",
            state_bytes.len()
        ));
    }
    let transition = MountedJointDsfTransition {
        joint_field_count: state.fields.len(),
        joint_neuron_count: state.neurons.len(),
        l0_l4_evaluation_count,
        dsf_delivery_count: transitioned,
        recurrent_dsf_delivery_count: recurrent,
        transition_receipt,
        episode_relation_candidate_receipt: state
            .episode_relation_candidate
            .as_ref()
            .map(|candidate| candidate.authority_receipt),
    };
    let successor_generation = state.generation;
    let source_authority = state.source_authority_receipt;
    let successor_resident_state = ResidentMountedState {
        state,
        cold_restore_work,
    };
    Ok(PreparedMountedGeneration {
        predecessor_generation,
        successor_generation,
        source_authority,
        source_body,
        restore_validation_cost,
        fields: prepared_fields,
        state_bytes,
        transition,
        successor_resident_state,
        phase_counts: MountedTransitionPhaseCounts {
            predecessor_authentication_count: 0,
            predecessor_decode_count: 0,
            predecessor_rebuilt_field_count: 0,
            retained_neuron_index_entry_count,
            reached_neuron_lookup_count,
            current_cohort_evaluation_count: l0_l4_evaluation_count,
            successor_seal_count: 1,
        },
    })
}

pub(crate) fn inspect_mounted_joint_dsf(
    state_bytes: &[u8],
    max_state_bytes: usize,
    max_working_bytes: usize,
) -> Result<MountedJointDsfTransition, String> {
    let summary =
        inspect_mounted_joint_dsf_summary(state_bytes, max_state_bytes, max_working_bytes)?;
    Ok(MountedJointDsfTransition {
        joint_field_count: summary.joint_field_count,
        joint_neuron_count: summary.joint_neuron_count,
        l0_l4_evaluation_count: 0,
        dsf_delivery_count: 0,
        recurrent_dsf_delivery_count: 0,
        transition_receipt: summary.transition_receipt,
        episode_relation_candidate_receipt: summary.episode_relation_candidate_receipt,
    })
}

/// Validate the retained joint-DSF body once and return only its fixed-size
/// observation. The caller keeps no second copy of the complete state bytes.
pub(crate) fn inspect_mounted_joint_dsf_summary(
    state_bytes: &[u8],
    max_state_bytes: usize,
    max_working_bytes: usize,
) -> Result<MountedJointDsfSummary, String> {
    if state_bytes.is_empty() {
        return Ok(MountedJointDsfSummary {
            generation: 0,
            joint_field_count: 0,
            joint_neuron_count: 0,
            transition_receipt: None,
            episode_relation_candidate_receipt: None,
        });
    }
    let (state, _) =
        restore_state_with_physics_validation(state_bytes, max_state_bytes, max_working_bytes)?;
    Ok(mounted_summary(&state))
}

fn mounted_summary(state: &State) -> MountedJointDsfSummary {
    MountedJointDsfSummary {
        generation: state.generation,
        joint_field_count: state.fields.len(),
        joint_neuron_count: state.neurons.len(),
        transition_receipt: state.last_transition_receipt,
        episode_relation_candidate_receipt: state
            .episode_relation_candidate
            .as_ref()
            .map(|candidate| candidate.authority_receipt),
    }
}

/// One-way conversion invoked only after the enclosing GLMFAB03 SHA-256 has
/// authenticated the exact historical body. It emits the sole current GLJDSF03
/// encoding; ordinary restore never enters this boundary.
pub(crate) fn convert_gljnft02_after_authenticated_outer_receipt(
    state_bytes: &[u8],
    max_state_bytes: usize,
    max_working_bytes: usize,
) -> Result<(Vec<u8>, MountedJointDsfSummary), String> {
    let (state, _) =
        authenticate_and_convert_gljnft02(state_bytes, max_state_bytes, max_working_bytes)?;
    let summary = mounted_summary(&state);
    let current = encode_state(&state)?;
    if current.len() > max_state_bytes {
        return Err(format!(
            "current joint-DSF state requires {} bytes, admitted {max_state_bytes}",
            current.len()
        ));
    }
    Ok((current, summary))
}

/// Inspect only the production D2 mounted schema. The exact historical
/// receipt authenticator and unchanged L0--L4 rebuild are the sole parsing
/// path. GLJDSF03 is deliberately refused so current state cannot masquerade
/// as production history.
pub(crate) fn inspect_canonical_gljnft02_legacy_ports(
    state_bytes: &[u8],
    max_state_bytes: usize,
    max_working_bytes: usize,
) -> Result<LegacyMountedJointInspection, String> {
    if state_bytes.len() > max_state_bytes {
        return Err("GLJNFT02 input exceeds admitted storage".into());
    }
    if state_bytes.len() < PRIOR_MAGIC.len() + std::mem::size_of::<u16>()
        || &state_bytes[..PRIOR_MAGIC.len()] != PRIOR_MAGIC
        || u16::from_le_bytes(
            state_bytes[PRIOR_MAGIC.len()..PRIOR_MAGIC.len() + 2]
                .try_into()
                .expect("fixed GLJNFT02 version"),
        ) != PRIOR_VERSION
    {
        return Err("mounted source evidence is not GLJNFT02".into());
    }
    let (state, _) =
        authenticate_and_convert_gljnft02(state_bytes, max_state_bytes, max_working_bytes)?;
    let generation = state.generation;
    let next_lineage_ordinal = state.next_lineage_ordinal;
    let neurons = state
        .neurons
        .into_iter()
        .map(
            |neuron| -> Result<LegacyMountedNeuronPortInspection, String> {
                let key = neuron.key;
                if !key.coordinates.is_empty()
                    || !key.physical_quantity.is_empty()
                    || !key.physical_unit.is_empty()
                    || !key.relevance_rule.is_empty()
                    || key.relevance_origin.is_some()
                    || !key.input_map_id.is_empty()
                    || !key.source_min.is_zero()
                    || !key.source_max.is_zero()
                    || !key.field_offset.is_zero()
                    || !key.field_scale.is_zero()
                    || !key.input_map_profile.is_empty()
                    || key.input_map_group_receipt != [0; 32]
                {
                    return Err("GLJNFT02 contains invented receptor anatomy".into());
                }
                Ok(LegacyMountedNeuronPortInspection {
                    lineage: neuron.lineage,
                    sense: key.sense,
                    topology_index: key.topology_index,
                    sensor_id: key.sensor_id,
                    substream_id: key.substream_id,
                })
            },
        )
        .collect::<Result<Vec<_>, _>>()?;
    Ok(LegacyMountedJointInspection {
        generation,
        next_lineage_ordinal,
        neurons,
    })
}

/// Validate current GLJDSF03 against a preflight plan bound to its receipt.
#[cfg(test)]
pub(crate) fn inspect_current_mounted_joint_dsf_summary(
    state_bytes: &[u8],
    max_state_bytes: usize,
    plan: &CurrentInspectionPlan,
) -> Result<MountedJointDsfSummary, String> {
    if state_bytes.len() > max_state_bytes {
        return Err("joint-DSF input exceeds admitted storage".into());
    }
    if &preflight_current_inspection(state_bytes)? != plan {
        return Err("current joint inspection plan does not bind this exact state".into());
    }
    let (state, _) = restore_state_with_physics_validation(
        state_bytes,
        max_state_bytes,
        plan.largest_field_rebuild_logical_bytes.max(1),
    )?;
    verify_canonical_state_encoding(&state, state_bytes)?;
    Ok(MountedJointDsfSummary {
        generation: state.generation,
        joint_field_count: state.fields.len(),
        joint_neuron_count: state.neurons.len(),
        transition_receipt: state.last_transition_receipt,
        episode_relation_candidate_receipt: state
            .episode_relation_candidate
            .as_ref()
            .map(|candidate| candidate.authority_receipt),
    })
}

#[cfg(test)]
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) enum LogicalArenaStatus {
    GeneralAllocatorRequired,
}

#[cfg(test)]
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) struct CurrentInspectionPlan {
    pub(crate) borrowed_joint_bytes: usize,
    pub(crate) joint_receipt: [u8; 32],
    pub(crate) retained_decoded_container_bytes: usize,
    pub(crate) retained_decoded_payload_bytes: usize,
    pub(crate) retained_decoded_limb_bytes: usize,
    pub(crate) retained_decoded_logical_bytes: usize,
    pub(crate) largest_field_rebuild_logical_bytes: usize,
    pub(crate) validation_logical_scratch_bytes: usize,
    pub(crate) canonical_streaming_scratch_bytes: usize,
    pub(crate) additional_logical_arena_bytes: usize,
    pub(crate) arena_status: LogicalArenaStatus,
}

#[cfg(test)]
#[derive(Clone, Copy)]
struct ScannedInput {
    rebuild: usize,
    validation: usize,
}

#[cfg(test)]
struct CurrentScanner<'a> {
    payload: &'a [u8],
    offset: usize,
    containers: usize,
    payloads: usize,
    limbs: usize,
    max_integer: usize,
    validation: usize,
}

#[cfg(test)]
impl<'a> CurrentScanner<'a> {
    fn new(payload: &'a [u8]) -> Self {
        Self {
            payload,
            offset: 0,
            containers: 0,
            payloads: 0,
            limbs: 0,
            max_integer: 0,
            validation: 0,
        }
    }
    fn sum(target: &mut usize, value: usize, message: &'static str) -> Result<(), String> {
        *target = target.checked_add(value).ok_or(message)?;
        Ok(())
    }
    fn add_vec<T>(&mut self, count: usize) -> Result<(), String> {
        let bytes = count
            .checked_mul(size_of::<T>())
            .ok_or("current inspection vector overflow")?;
        Self::sum(
            &mut self.containers,
            bytes,
            "current inspection container overflow",
        )
    }
    fn take(&mut self, count: usize) -> Result<&'a [u8], String> {
        let end = self
            .offset
            .checked_add(count)
            .ok_or("current inspection length overflow")?;
        let value = self
            .payload
            .get(self.offset..end)
            .ok_or("current joint-DSF state ended early")?;
        self.offset = end;
        Ok(value)
    }
    fn u8(&mut self) -> Result<u8, String> {
        Ok(self.take(1)?[0])
    }
    fn u16(&mut self) -> Result<u16, String> {
        Ok(u16::from_le_bytes(
            self.take(2)?.try_into().expect("scanned u16"),
        ))
    }
    fn u32(&mut self) -> Result<u32, String> {
        Ok(u32::from_le_bytes(
            self.take(4)?.try_into().expect("scanned u32"),
        ))
    }
    fn count(&mut self, minimum: usize) -> Result<usize, String> {
        let count = self.u32()? as usize;
        if count
            .checked_mul(minimum)
            .ok_or("current inspection count overflow")?
            > self.payload.len().saturating_sub(self.offset)
        {
            return Err("current inspection count exceeds remaining bytes".into());
        }
        Ok(count)
    }
    fn digest(&mut self) -> Result<(), String> {
        self.take(32).map(|_| ())
    }
    fn optional_digest(&mut self) -> Result<(), String> {
        match self.u8()? {
            0 => Ok(()),
            1 => self.digest(),
            _ => Err("current inspection optional digest flag changed".into()),
        }
    }
    fn encoded_bytes(&mut self) -> Result<&'a [u8], String> {
        let count = self.u32()? as usize;
        self.take(count)
    }
    fn owned_bytes(&mut self) -> Result<usize, String> {
        let len = self.encoded_bytes()?.len();
        Self::sum(
            &mut self.payloads,
            len,
            "current inspection payload overflow",
        )?;
        Ok(len)
    }
    fn string(&mut self) -> Result<usize, String> {
        let len = self.encoded_bytes()?.len();
        if len == 0 {
            return Err("current inspection string is empty".into());
        }
        Self::sum(
            &mut self.payloads,
            len,
            "current inspection payload overflow",
        )?;
        Ok(len)
    }
    fn optional_string(&mut self) -> Result<(), String> {
        match self.u8()? {
            0 => Ok(()),
            1 => self.string().map(|_| ()),
            _ => Err("current inspection optional string flag changed".into()),
        }
    }
    fn rational(&mut self) -> Result<usize, String> {
        let numerator = self.encoded_bytes()?;
        let denominator = self.encoded_bytes()?;
        if denominator.is_empty()
            || denominator[0] & 0x80 != 0
            || denominator.iter().all(|v| *v == 0)
        {
            return Err("current inspection rational denominator is not positive".into());
        }
        self.max_integer = self.max_integer.max(numerator.len()).max(denominator.len());
        for bytes in [numerator, denominator] {
            let words = bytes
                .len()
                .checked_add(size_of::<usize>() - 1)
                .ok_or("current inspection bigint width overflow")?
                / size_of::<usize>();
            let limb = words
                .checked_mul(size_of::<usize>())
                .ok_or("current inspection limb overflow")?;
            Self::sum(&mut self.limbs, limb, "current inspection limb overflow")?;
        }
        numerator
            .len()
            .checked_add(denominator.len())
            .ok_or_else(|| "current inspection rational width overflow".into())
    }
    fn digests(&mut self) -> Result<(), String> {
        let count = self.count(32)?;
        self.add_vec::<[u8; 32]>(count)?;
        self.take(
            count
                .checked_mul(32)
                .ok_or("current inspection digest overflow")?,
        )
        .map(|_| ())
    }
    fn input(&mut self) -> Result<ScannedInput, String> {
        let before = (self.containers, self.payloads, self.limbs);
        let vertices = self.count(4)?;
        self.add_vec::<String>(vertices)?;
        let mut input_bytes = 0usize;
        for _ in 0..vertices {
            input_bytes = input_bytes
                .checked_add(self.string()?)
                .ok_or("current inspection input overflow")?;
        }
        let groups = self.count(4)?;
        self.add_vec::<Vec<usize>>(groups)?;
        let mut max_group = 0usize;
        for _ in 0..groups {
            let count = self.count(8)?;
            max_group = max_group.max(count);
            self.add_vec::<usize>(count)?;
            self.take(
                count
                    .checked_mul(8)
                    .ok_or("current inspection group overflow")?,
            )?;
        }
        let frames = self.count(8)?;
        self.add_vec::<Exact>(frames)?;
        let mut max_value = 1usize;
        for _ in 0..frames {
            let width = self.rational()?;
            input_bytes = input_bytes
                .checked_add(width)
                .ok_or("current inspection input overflow")?;
            max_value = max_value.max(width);
        }
        let vector_count = self.count(4)?;
        self.add_vec::<Vec<Exact>>(vector_count)?;
        let mut vector_values = 0usize;
        for _ in 0..vector_count {
            let count = self.count(8)?;
            self.add_vec::<Exact>(count)?;
            vector_values = vector_values
                .checked_add(count)
                .ok_or("current inspection vector overflow")?;
            for _ in 0..count {
                let width = self.rational()?;
                input_bytes = input_bytes
                    .checked_add(width)
                    .ok_or("current inspection input overflow")?;
                max_value = max_value.max(width);
            }
        }
        let edges = vertices
            .checked_mul(vertices.saturating_sub(1))
            .ok_or("current inspection edge overflow")?
            / 2;
        let relations = frames
            .checked_mul(edges)
            .ok_or("current inspection relation overflow")?;
        let vf = frames
            .checked_mul(vertices)
            .ok_or("current inspection vertex-frame overflow")?;
        let relation_width = max_value
            .checked_mul(4)
            .ok_or("current inspection relation width overflow")?;
        let relation_bytes = relations
            .checked_mul(8)
            .and_then(|v| v.checked_mul(relation_width))
            .and_then(|v| {
                v.checked_add(
                    relations
                        .checked_mul(2)?
                        .checked_mul(size_of::<RelationFact>())?,
                )
            })
            .ok_or("current inspection relation allocation overflow")?;
        let vertex_bytes = vf
            .checked_mul(12)
            .and_then(|v| v.checked_mul(max_value))
            .ok_or("current inspection vertex allocation overflow")?;
        let clone_backing = self
            .containers
            .checked_sub(before.0)
            .and_then(|v| v.checked_add(self.payloads.checked_sub(before.1)?))
            .and_then(|v| v.checked_add(self.limbs.checked_sub(before.2)?))
            .ok_or("current inspection clone backing overflow")?;
        let rebuild = input_bytes
            .checked_add(relation_bytes)
            .and_then(|v| v.checked_add(vertex_bytes))
            .and_then(|v| v.checked_add(clone_backing))
            .and_then(|v| {
                v.checked_add(
                    vector_values
                        .checked_mul(size_of::<Exact>())?
                        .checked_add(size_of::<JointFieldInput>())?,
                )
            })
            .ok_or("current inspection rebuild overflow")?;
        let validation = vertices
            .checked_mul(size_of::<&str>())
            .and_then(|v| v.checked_add(vertices.checked_mul(size_of::<usize>())?))
            .and_then(|v| v.checked_add(max_group.checked_mul(size_of::<usize>())?))
            .ok_or("current inspection validation overflow")?;
        Ok(ScannedInput {
            rebuild,
            validation,
        })
    }
    fn key(&mut self) -> Result<usize, String> {
        self.take(5)?;
        self.string()?;
        self.string()?;
        match self.u8()? {
            0 => return Ok(0),
            1 => {}
            _ => return Err("current inspection receptor-binding flag changed".into()),
        }
        let coordinates = self.count(8)?;
        self.add_vec::<JointSourceCoordinate>(coordinates)?;
        for _ in 0..coordinates {
            self.string()?;
            self.string()?;
        }
        self.string()?;
        self.string()?;
        self.string()?;
        self.optional_string()?;
        self.string()?;
        for _ in 0..4 {
            self.rational()?;
        }
        self.owned_bytes()?;
        self.digest()?;
        coordinates
            .checked_mul(size_of::<&str>())
            .ok_or_else(|| "current inspection axis validation overflow".into())
    }
    fn delivery_impression(&mut self) -> Result<(), String> {
        self.take(16)?;
        self.digest()?;
        self.digest()?;
        self.optional_digest()?;
        let count = self.count(1)?;
        self.add_vec::<StructuralTrit>(count)?;
        for _ in 0..count {
            if self.u8()? > 2 {
                return Err("current inspection structural trit changed".into());
            }
        }
        self.take(32)?;
        if self.u8()? > 1 {
            return Err("current inspection predecessor flag changed".into());
        }
        self.digest()?;
        self.digest()
    }
    fn finish(&self) -> Result<(), String> {
        if self.offset == self.payload.len() {
            Ok(())
        } else {
            Err("current joint-DSF state has trailing bytes".into())
        }
    }
}

#[cfg(test)]
pub(crate) fn preflight_current_inspection(
    state_bytes: &[u8],
) -> Result<CurrentInspectionPlan, String> {
    let mut scan = CurrentScanner::new(state_bytes);
    if scan.take(8)? != MAGIC || scan.u16()? != VERSION {
        return Err("current joint-DSF state is not GLJDSF03".into());
    }
    scan.take(16)?;
    scan.digest()?;
    scan.optional_digest()?;
    let fields = scan.count(100)?;
    scan.add_vec::<JointFieldSnapshot>(fields)?;
    let mut rebuild = 0usize;
    for _ in 0..fields {
        scan.digest()?;
        scan.digests()?;
        let input = scan.input()?;
        rebuild = rebuild.max(input.rebuild);
        scan.validation = scan.validation.max(input.validation);
        scan.digest()?;
        scan.digest()?;
    }
    let neurons = scan.count(230)?;
    scan.add_vec::<MountedNeuron>(neurons)?;
    let lineage_validation = neurons
        .checked_mul(size_of::<[u8; 16]>())
        .ok_or("current inspection lineage validation overflow")?;
    let mut axis_validation = 0usize;
    for _ in 0..neurons {
        axis_validation = axis_validation.max(scan.key()?);
        scan.take(16)?;
        scan.digest()?;
        scan.delivery_impression()?;
        scan.take(8)?;
    }
    scan.validation = scan.validation.max(
        lineage_validation
            .checked_add(axis_validation)
            .ok_or("current inspection neuron validation overflow")?,
    );
    match scan.u8()? {
        0 => {}
        1 => {
            scan.digest()?;
            let refs = scan.count(64)?;
            scan.add_vec::<EpisodeFieldReference>(refs)?;
            scan.take(
                refs.checked_mul(64)
                    .ok_or("current inspection episode overflow")?,
            )?;
            let lineages = scan.count(16)?;
            scan.add_vec::<[u8; 16]>(lineages)?;
            scan.take(
                lineages
                    .checked_mul(16)
                    .ok_or("current inspection lineage overflow")?,
            )?;
            let episode = refs
                .checked_mul(size_of::<EpisodeFieldReference>())
                .and_then(|v| v.checked_add(lineages.checked_mul(size_of::<[u8; 16]>())?))
                .ok_or("current inspection episode validation overflow")?;
            scan.validation = scan.validation.max(episode);
            if scan.u8()? > 1 {
                return Err("current inspection common-cause flag changed".into());
            }
            scan.optional_digest()?;
            scan.digest()?;
        }
        _ => return Err("current inspection episode flag changed".into()),
    }
    scan.finish()?;
    let containers = size_of::<State>()
        .checked_add(scan.containers)
        .ok_or("current inspection containers overflow")?;
    let retained = containers
        .checked_add(scan.payloads)
        .and_then(|v| v.checked_add(scan.limbs))
        .ok_or("current inspection retained overflow")?;
    let phase = rebuild
        .checked_add(scan.validation)
        .ok_or("current inspection phase overflow")?
        .max(scan.max_integer);
    let additional = retained
        .checked_add(phase)
        .ok_or("current inspection arena overflow")?;
    Ok(CurrentInspectionPlan {
        borrowed_joint_bytes: state_bytes.len(),
        joint_receipt: sha256(state_bytes),
        retained_decoded_container_bytes: containers,
        retained_decoded_payload_bytes: scan.payloads,
        retained_decoded_limb_bytes: scan.limbs,
        retained_decoded_logical_bytes: retained,
        largest_field_rebuild_logical_bytes: rebuild,
        validation_logical_scratch_bytes: scan.validation,
        canonical_streaming_scratch_bytes: scan.max_integer,
        additional_logical_arena_bytes: additional,
        arena_status: LogicalArenaStatus::GeneralAllocatorRequired,
    })
}

#[cfg(test)]
struct CanonicalComparator<'a> {
    expected: &'a [u8],
    offset: usize,
}

#[cfg(test)]
impl<'a> CanonicalComparator<'a> {
    fn new(expected: &'a [u8]) -> Self {
        Self {
            expected,
            offset: 0,
        }
    }
    fn bytes(&mut self, value: &[u8]) -> Result<(), String> {
        let end = self
            .offset
            .checked_add(value.len())
            .ok_or("canonical comparison overflow")?;
        if self.expected.get(self.offset..end) != Some(value) {
            return Err("current joint-DSF state encoding is noncanonical".into());
        }
        self.offset = end;
        Ok(())
    }
    fn u32(&mut self, value: usize) -> Result<(), String> {
        self.bytes(
            &u32::try_from(value)
                .map_err(|_| "joint state cardinality exceeds u32")?
                .to_le_bytes(),
        )
    }
    fn length_bytes(&mut self, value: &[u8]) -> Result<(), String> {
        self.u32(value.len())?;
        self.bytes(value)
    }
    fn string(&mut self, value: &str) -> Result<(), String> {
        self.length_bytes(value.as_bytes())
    }
    fn optional_string(&mut self, value: Option<&str>) -> Result<(), String> {
        self.bytes(&[u8::from(value.is_some())])?;
        if let Some(v) = value {
            self.string(v)?;
        }
        Ok(())
    }
    fn optional_digest(&mut self, value: Option<[u8; 32]>) -> Result<(), String> {
        self.bytes(&[u8::from(value.is_some())])?;
        if let Some(v) = value {
            self.bytes(&v)?;
        }
        Ok(())
    }
    fn rational(&mut self, value: &BigRational) -> Result<(), String> {
        let n = value.numer().to_signed_bytes_be();
        self.length_bytes(&n)?;
        drop(n);
        let d = value.denom().to_signed_bytes_be();
        self.length_bytes(&d)
    }
    fn input(&mut self, input: &JointFieldInput) -> Result<(), String> {
        self.u32(input.vertex_ids.len())?;
        for v in &input.vertex_ids {
            self.string(v)?;
        }
        self.u32(input.groups.len())?;
        for g in &input.groups {
            self.u32(g.len())?;
            for i in g {
                self.bytes(
                    &u64::try_from(*i)
                        .map_err(|_| "joint group index overflow")?
                        .to_le_bytes(),
                )?;
            }
        }
        self.u32(input.times.len())?;
        for v in &input.times {
            self.rational(v)?;
        }
        self.u32(input.vectors.len())?;
        for row in &input.vectors {
            self.u32(row.len())?;
            for v in row {
                self.rational(v)?;
            }
        }
        Ok(())
    }
    fn key(&mut self, key: &PhysicalPortKey) -> Result<(), String> {
        self.bytes(&[key.sense])?;
        self.bytes(&key.topology_index.to_le_bytes())?;
        self.string(&key.sensor_id)?;
        self.string(&key.substream_id)?;
        self.bytes(&[u8::from(!key.coordinates.is_empty())])?;
        if key.coordinates.is_empty() {
            return Ok(());
        }
        self.u32(key.coordinates.len())?;
        for c in &key.coordinates {
            self.string(&c.axis_id)?;
            self.string(&c.coordinate_id)?;
        }
        self.string(&key.physical_quantity)?;
        self.string(&key.physical_unit)?;
        self.string(&key.relevance_rule)?;
        self.optional_string(key.relevance_origin.as_deref())?;
        self.string(&key.input_map_id)?;
        for v in [
            &key.source_min,
            &key.source_max,
            &key.field_offset,
            &key.field_scale,
        ] {
            self.rational(v)?;
        }
        self.length_bytes(&key.input_map_profile)?;
        self.bytes(&key.input_map_group_receipt)
    }
    fn delivery_impression(&mut self, v: &DsfDeliveryImpression) -> Result<(), String> {
        self.bytes(&v.neuron_lineage)?;
        self.bytes(&v.complete_field_receipt_sha256)?;
        self.bytes(&v.perspective_receipt_sha256)?;
        self.optional_digest(v.predecessor_impression_receipt_sha256)?;
        self.u32(v.delivery_sign_impression.len())?;
        for t in &v.delivery_sign_impression {
            self.bytes(&[match t {
                StructuralTrit::Negative => 0,
                StructuralTrit::Quiescent => 1,
                StructuralTrit::Positive => 2,
            }])?;
        }
        let g = &v.delivery_recurrence;
        for c in [
            g.coordinate_count,
            g.matching_nonnull,
            g.matching_quiescent,
            g.contradictions,
        ] {
            self.bytes(
                &u64::try_from(c)
                    .map_err(|_| "joint growth count overflow")?
                    .to_le_bytes(),
            )?;
        }
        self.bytes(&[u8::from(g.predecessor_present)])?;
        self.bytes(&g.authority_receipt_sha256)?;
        self.bytes(&v.authority_receipt_sha256)
    }
    fn finish(self) -> Result<(), String> {
        if self.offset == self.expected.len() {
            Ok(())
        } else {
            Err("current joint-DSF state encoding is noncanonical".into())
        }
    }
}

#[cfg(test)]
fn verify_canonical_state_encoding(state: &State, expected: &[u8]) -> Result<(), String> {
    let mut o = CanonicalComparator::new(expected);
    o.bytes(MAGIC)?;
    o.bytes(&VERSION.to_le_bytes())?;
    o.bytes(&state.generation.to_le_bytes())?;
    o.bytes(&state.next_lineage_ordinal.to_le_bytes())?;
    o.bytes(&state.source_authority_receipt)?;
    o.optional_digest(state.last_transition_receipt)?;
    o.u32(state.fields.len())?;
    for f in &state.fields {
        o.bytes(&f.topology_receipt)?;
        o.u32(f.group_authority_receipts.len())?;
        for r in &f.group_authority_receipts {
            o.bytes(r)?;
        }
        o.input(&f.input)?;
        o.bytes(&f.experience_receipt)?;
        o.bytes(&f.complete_l4_receipt)?;
    }
    o.u32(state.neurons.len())?;
    for n in &state.neurons {
        o.key(&n.key)?;
        o.bytes(&n.lineage)?;
        o.bytes(&n.topology_receipt)?;
        o.delivery_impression(&n.delivery_impression)?;
        o.bytes(&n.transition_count.to_le_bytes())?;
    }
    o.bytes(&[u8::from(state.episode_relation_candidate.is_some())])?;
    if let Some(c) = &state.episode_relation_candidate {
        o.bytes(&c.source_authority_receipt)?;
        o.u32(c.fields.len())?;
        for f in &c.fields {
            o.bytes(&f.topology_receipt)?;
            o.bytes(&f.exact_clock_receipt)?;
        }
        o.u32(c.participating_lineages.len())?;
        for l in &c.participating_lineages {
            o.bytes(l)?;
        }
        o.bytes(&[u8::from(c.common_physical_cause_resolved)])?;
        o.optional_digest(c.predecessor_candidate_receipt)?;
        o.bytes(&c.authority_receipt)?;
    }
    o.finish()
}

fn exact_time_cohorts(
    ports: Vec<JointSourcePortView>,
) -> Result<Vec<Vec<JointSourcePortView>>, String> {
    let mut by_times: BTreeMap<Vec<Exact>, Vec<JointSourcePortView>> = BTreeMap::new();
    for port in ports {
        if port.source_times.len() != port.dimensionless_fields.len() {
            return Err("joint source port changed sample cardinality".into());
        }
        by_times
            .entry(port.source_times.clone())
            .or_default()
            .push(port);
    }
    let mut cohorts = Vec::new();
    for (_, mut values) in by_times {
        if values.len() < 2 || values[0].source_times.len() < 2 {
            continue;
        }
        values.sort_by_key(|port| (port.sense, port.topology_index));
        cohorts.push(values);
    }
    cohorts.sort_by(|left, right| port_key(&left[0]).cmp(&port_key(&right[0])));
    Ok(cohorts)
}

fn port_key(port: &JointSourcePortView) -> PhysicalPortKey {
    PhysicalPortKey {
        sense: port.sense,
        topology_index: port.topology_index,
        sensor_id: port.sensor_id.clone(),
        substream_id: port.substream_id.clone(),
        coordinates: port.coordinates.clone(),
        physical_quantity: port.physical_quantity.clone(),
        physical_unit: port.physical_unit.clone(),
        relevance_rule: port.relevance_rule.clone(),
        relevance_origin: port.relevance_origin.clone(),
        input_map_id: port.input_map_id.clone(),
        source_min: port.source_min.clone(),
        source_max: port.source_max.clone(),
        field_offset: port.field_offset.clone(),
        field_scale: port.field_scale.clone(),
        input_map_profile: port.input_map_profile.clone(),
        input_map_group_receipt: port.input_map_group_receipt,
    }
}

fn vertex_id(key: &PhysicalPortKey) -> String {
    format!(
        "sense:{}/topology:{}/sensor:{}/substream:{}",
        key.sense, key.topology_index, key.sensor_id, key.substream_id
    )
}

fn joint_input(
    ports: &[JointSourcePortView],
) -> Result<
    (
        JointFieldInput,
        Vec<PhysicalPortKey>,
        Vec<[u8; 32]>,
        [u8; 32],
    ),
    String,
> {
    let times = ports
        .first()
        .ok_or("joint cohort is empty")?
        .source_times
        .clone();
    if ports.iter().any(|port| port.source_times != times) {
        return Err("joint cohort contains unequal exact time grids".into());
    }
    let keys = ports.iter().map(port_key).collect::<Vec<_>>();
    if keys.windows(2).any(|pair| pair[0] >= pair[1]) {
        return Err("joint physical ports are not strictly canonical".into());
    }
    let mut group_positions: BTreeMap<[u8; 32], Vec<usize>> = BTreeMap::new();
    for (index, port) in ports.iter().enumerate() {
        group_positions
            .entry(port.input_map_group_receipt)
            .or_default()
            .push(index);
    }
    let group_authority_receipts = group_positions.keys().copied().collect::<Vec<_>>();
    let groups = group_positions.into_values().collect::<Vec<_>>();
    let vectors = (0..times.len())
        .map(|frame| {
            ports
                .iter()
                .map(|port| port.dimensionless_fields[frame].clone())
                .collect()
        })
        .collect();
    let input = JointFieldInput {
        vertex_ids: keys.iter().map(vertex_id).collect(),
        groups,
        times,
        vectors,
    };
    let topology_receipt = topology_receipt(&input, &group_authority_receipts);
    Ok((input, keys, group_authority_receipts, topology_receipt))
}

fn topology_receipt(input: &JointFieldInput, group_authority_receipts: &[[u8; 32]]) -> [u8; 32] {
    let mut payload = Vec::new();
    payload.extend_from_slice(b"guala.native.joint_field_topology.v1");
    push_u32_bounded(&mut payload, input.vertex_ids.len());
    for vertex in &input.vertex_ids {
        push_string_bounded(&mut payload, vertex);
    }
    push_u32_bounded(&mut payload, input.groups.len());
    for (group, authority) in input.groups.iter().zip(group_authority_receipts) {
        payload.extend_from_slice(authority);
        push_u32_bounded(&mut payload, group.len());
        for index in group {
            payload.extend_from_slice(&(*index as u64).to_le_bytes());
        }
    }
    sha256(&payload)
}

fn derived_working_bytes(
    input: &JointFieldInput,
    requirement: &crate::joint_field_l0_l4::JointFieldRequirement,
) -> Result<usize, String> {
    let max_value_bytes = input
        .vectors
        .iter()
        .flatten()
        .chain(input.times.iter())
        .map(|value| {
            value
                .numer()
                .to_signed_bytes_be()
                .len()
                .checked_add(value.denom().to_signed_bytes_be().len())
                .ok_or("joint rational byte width overflow")
        })
        .collect::<Result<Vec<_>, _>>()?
        .into_iter()
        .max()
        .unwrap_or(1);
    // L0 and L2 each retain four exact rational facts per edge. A product or
    // difference can require at most four admitted operand widths here. This
    // is a conservative structural allocation bound, not a cognitive cap.
    let relation_value_bytes = max_value_bytes
        .checked_mul(4)
        .ok_or("joint relation width overflow")?;
    let relation_bytes = requirement
        .relation_facts
        .checked_mul(8)
        .and_then(|value| value.checked_mul(relation_value_bytes))
        .and_then(|value| {
            value.checked_add(
                requirement
                    .relation_facts
                    .checked_mul(2)?
                    .checked_mul(size_of::<RelationFact>())?,
            )
        })
        .ok_or("joint relation allocation overflow")?;
    let vertex_bytes = requirement
        .vertex_frame_values
        .checked_mul(12)
        .and_then(|value| value.checked_mul(max_value_bytes))
        .ok_or("joint vertex allocation overflow")?;
    requirement
        .input_bytes
        .checked_add(relation_bytes)
        .and_then(|value| value.checked_add(vertex_bytes))
        .ok_or_else(|| "joint working allocation overflow".to_string())
}

#[cfg(test)]
fn find_or_create_neuron(state: &mut State, key: PhysicalPortKey) -> Result<usize, String> {
    let mut indices = mounted_neuron_indices(state);
    find_or_create_neuron_indexed(state, &mut indices, key)
}

fn mounted_neuron_indices(state: &State) -> BTreeMap<(u8, u32), usize> {
    let mut indices = BTreeMap::new();
    for (index, neuron) in state.neurons.iter().enumerate() {
        indices
            .entry((neuron.key.sense, neuron.key.topology_index))
            .or_insert(index);
    }
    indices
}

fn find_or_create_neuron_indexed(
    state: &mut State,
    indices: &mut BTreeMap<(u8, u32), usize>,
    key: PhysicalPortKey,
) -> Result<usize, String> {
    let address = (key.sense, key.topology_index);
    if let Some(index) = indices.get(&address).copied() {
        if state.neurons[index].key == key {
            return Ok(index);
        }
        let prior = &state.neurons[index].key;
        if prior.sensor_id == key.sensor_id
            && prior.substream_id == key.substream_id
            && prior.coordinates.is_empty()
        {
            state.neurons[index].key = key;
        } else {
            return Err("joint neuron physical binding changed without migration".into());
        }
        return Ok(index);
    }
    let ordinal = state.next_lineage_ordinal;
    state.next_lineage_ordinal = ordinal
        .checked_add(1)
        .ok_or("joint neuron lineage overflow")?;
    let mut lineage = [0u8; 16];
    lineage[..8].copy_from_slice(LINEAGE_DOMAIN);
    lineage[8..].copy_from_slice(&ordinal.to_be_bytes());
    let empty_recurrence = DsfDeliveryRecurrence {
        coordinate_count: 0,
        matching_nonnull: 0,
        matching_quiescent: 0,
        contradictions: 0,
        predecessor_present: false,
        authority_receipt_sha256: [0; 32],
    };
    state.neurons.push(MountedNeuron {
        key,
        lineage,
        topology_receipt: [0; 32],
        delivery_impression: DsfDeliveryImpression {
            neuron_lineage: lineage,
            complete_field_receipt_sha256: [0; 32],
            perspective_receipt_sha256: [0; 32],
            predecessor_impression_receipt_sha256: None,
            delivery_sign_impression: Vec::new(),
            delivery_recurrence: empty_recurrence,
            authority_receipt_sha256: [0; 32],
        },
        transition_count: 0,
    });
    let index = state.neurons.len() - 1;
    indices.insert(address, index);
    Ok(index)
}

fn snapshot(
    input: JointFieldInput,
    topology_receipt: [u8; 32],
    group_authority_receipts: Vec<[u8; 32]>,
    experience: &JointFieldExperience,
) -> JointFieldSnapshot {
    JointFieldSnapshot {
        topology_receipt,
        group_authority_receipts,
        input,
        experience_receipt: experience.authority_receipt_sha256,
        complete_l4_receipt: experience.l4.authority_receipt_sha256,
    }
}

fn exact_clock_receipt(input: &JointFieldInput) -> Result<[u8; 32], String> {
    let mut authority = Vec::new();
    authority.extend_from_slice(b"guala.native.exact_clock.v1");
    push_u32(&mut authority, input.times.len())?;
    for time in &input.times {
        push_rational(&mut authority, time)?;
    }
    Ok(sha256(&authority))
}

fn current_participating_lineages(state: &State) -> Result<Vec<[u8; 16]>, String> {
    let mut lineages = BTreeSet::new();
    for field in &state.fields {
        for vertex in &field.input.vertex_ids {
            let lineage = state
                .neurons
                .iter()
                .find(|neuron| vertex_id(&neuron.key) == *vertex)
                .ok_or("episode relation references an absent neuron")?
                .lineage;
            lineages.insert(lineage);
        }
    }
    Ok(lineages.into_iter().collect())
}

fn episode_relation_authority(candidate: &EpisodeRelationCandidate) -> Result<[u8; 32], String> {
    let mut authority = Vec::new();
    authority.extend_from_slice(b"guala.native.episode_relation_candidate.v1");
    push_bytes(&mut authority, EPISODE_RELATION)?;
    authority.extend_from_slice(&candidate.source_authority_receipt);
    push_u32(&mut authority, candidate.fields.len())?;
    for field in &candidate.fields {
        authority.extend_from_slice(&field.topology_receipt);
        authority.extend_from_slice(&field.exact_clock_receipt);
    }
    push_u32(&mut authority, candidate.participating_lineages.len())?;
    for lineage in &candidate.participating_lineages {
        authority.extend_from_slice(lineage);
    }
    authority.push(u8::from(candidate.common_physical_cause_resolved));
    push_optional_digest(&mut authority, candidate.predecessor_candidate_receipt);
    Ok(sha256(&authority))
}

fn build_episode_relation_candidate(
    state: &State,
    predecessor: Option<&EpisodeRelationCandidate>,
) -> Result<Option<EpisodeRelationCandidate>, String> {
    build_episode_relation_candidate_with_lineages(
        state,
        predecessor,
        current_participating_lineages(state)?,
    )
}

fn build_episode_relation_candidate_with_lineages(
    state: &State,
    predecessor: Option<&EpisodeRelationCandidate>,
    participating_lineages: Vec<[u8; 16]>,
) -> Result<Option<EpisodeRelationCandidate>, String> {
    if state.fields.len() < 2 {
        return Ok(None);
    }
    let fields = state
        .fields
        .iter()
        .map(|field| {
            Ok(EpisodeFieldReference {
                topology_receipt: field.topology_receipt,
                exact_clock_receipt: exact_clock_receipt(&field.input)?,
            })
        })
        .collect::<Result<Vec<_>, String>>()?;
    let predecessor_candidate_receipt = predecessor
        .filter(|candidate| {
            candidate.fields.len() == fields.len()
                && candidate
                    .fields
                    .iter()
                    .zip(&fields)
                    .all(|(left, right)| left.topology_receipt == right.topology_receipt)
        })
        .map(|candidate| candidate.authority_receipt);
    let mut candidate = EpisodeRelationCandidate {
        source_authority_receipt: state.source_authority_receipt,
        fields,
        participating_lineages,
        common_physical_cause_resolved: false,
        predecessor_candidate_receipt,
        authority_receipt: [0; 32],
    };
    candidate.authority_receipt = episode_relation_authority(&candidate)?;
    Ok(Some(candidate))
}

fn validate_state_structure(state: &State, max_working_bytes: usize) -> Result<(), String> {
    if state.next_lineage_ordinal == 0 {
        return Err("joint next lineage is zero".into());
    }
    if state
        .fields
        .windows(2)
        .any(|pair| pair[0].topology_receipt >= pair[1].topology_receipt)
    {
        return Err("joint fields are not strictly canonical".into());
    }
    for field in &state.fields {
        if field.group_authority_receipts.len() != field.input.groups.len()
            || field
                .group_authority_receipts
                .windows(2)
                .any(|pair| pair[0] >= pair[1])
            || topology_receipt(&field.input, &field.group_authority_receipts)
                != field.topology_receipt
        {
            return Err("joint field topology receipt changed".into());
        }
        let required = derive_requirement(&field.input).map_err(|error| error.to_string())?;
        let working_bytes = derived_working_bytes(&field.input, &required)?;
        if working_bytes > max_working_bytes {
            return Err(format!(
                "persisted joint field requires {working_bytes} derived working bytes, admitted {max_working_bytes}"
            ));
        }
        for vertex in &field.input.vertex_ids {
            let neuron = state
                .neurons
                .iter()
                .find(|neuron| vertex_id(&neuron.key) == *vertex)
                .ok_or("joint field references an absent neuron")?;
            if neuron.topology_receipt != field.topology_receipt
                || neuron.delivery_impression.complete_field_receipt_sha256
                    != field.complete_l4_receipt
            {
                return Err("joint neuron lost its current complete field".into());
            }
        }
    }
    if state
        .neurons
        .windows(2)
        .any(|pair| pair[0].key >= pair[1].key)
    {
        return Err("joint neurons are not strictly canonical".into());
    }
    let mut lineages = BTreeSet::new();
    for neuron in &state.neurons {
        if !lineages.insert(neuron.lineage) || neuron.lineage[..8] != *LINEAGE_DOMAIN {
            return Err("joint neuron lineage changed or repeated".into());
        }
        if neuron.transition_count == 0 {
            return Err("joint state retained an untransitioned neuron".into());
        }
        validate_physical_port_key(&neuron.key)?;
        if neuron.delivery_impression.neuron_lineage != neuron.lineage
            || neuron
                .delivery_impression
                .delivery_sign_impression
                .is_empty()
            || neuron.delivery_impression.authority_receipt_sha256 == [0; 32]
        {
            return Err("joint DSF delivery impression is incomplete".into());
        }
        verify_dsf_delivery_impression(&neuron.delivery_impression)
            .map_err(|error| error.to_string())?;
    }
    match &state.episode_relation_candidate {
        None if state.fields.len() >= 2 => {
            return Err("joint state omitted its cross-clock episode relation candidate".into())
        }
        Some(candidate) => {
            if state.fields.len() < 2
                || candidate.source_authority_receipt != state.source_authority_receipt
                || candidate.common_physical_cause_resolved
            {
                return Err("episode relation candidate changed its bounded authority".into());
            }
            let expected_fields = state
                .fields
                .iter()
                .map(|field| {
                    Ok(EpisodeFieldReference {
                        topology_receipt: field.topology_receipt,
                        exact_clock_receipt: exact_clock_receipt(&field.input)?,
                    })
                })
                .collect::<Result<Vec<_>, String>>()?;
            if candidate.fields != expected_fields
                || candidate.participating_lineages != current_participating_lineages(state)?
                || candidate
                    .participating_lineages
                    .windows(2)
                    .any(|pair| pair[0] >= pair[1])
                || episode_relation_authority(candidate)? != candidate.authority_receipt
            {
                return Err("episode relation candidate authority changed".into());
            }
        }
        None => {}
    }
    Ok(())
}

fn validate_physical_port_key(key: &PhysicalPortKey) -> Result<(), String> {
    if key.coordinates.is_empty() {
        if !key.physical_quantity.is_empty()
            || !key.physical_unit.is_empty()
            || !key.relevance_rule.is_empty()
            || key.relevance_origin.is_some()
            || !key.input_map_id.is_empty()
            || !key.source_min.is_zero()
            || !key.source_max.is_zero()
            || !key.field_offset.is_zero()
            || !key.field_scale.is_zero()
            || !key.input_map_profile.is_empty()
            || key.input_map_group_receipt != [0; 32]
        {
            return Err("unresolved prior receptor binding contains partial anatomy".into());
        }
        return Ok(());
    }
    let mut axes = BTreeSet::new();
    if key.coordinates.iter().any(|value| {
        value.axis_id.is_empty()
            || value.coordinate_id.is_empty()
            || !axes.insert(value.axis_id.as_str())
    }) || key.physical_quantity.is_empty()
        || key.physical_unit.is_empty()
        || key.relevance_rule.is_empty()
        || key.input_map_id.is_empty()
        || key.source_max <= key.source_min
        || key.field_scale.is_zero()
        || key.input_map_profile.is_empty()
    {
        return Err("resolved receptor binding is physically incomplete".into());
    }
    if reconstructed_input_map_group_receipt(key)? != key.input_map_group_receipt {
        return Err("resolved receptor binding authority changed".into());
    }
    Ok(())
}

fn reconstructed_input_map_group_receipt(key: &PhysicalPortKey) -> Result<[u8; 32], String> {
    let mut payload = Vec::new();
    push_string(&mut payload, "guala.joint_source.group.v1")?;
    for coordinate in &key.coordinates {
        push_string(&mut payload, &coordinate.axis_id)?;
        push_string(&mut payload, &coordinate.coordinate_id)?;
    }
    for value in [
        &key.physical_quantity,
        &key.physical_unit,
        &key.relevance_rule,
    ] {
        push_string(&mut payload, value)?;
    }
    push_string(&mut payload, key.relevance_origin.as_deref().unwrap_or(""))?;
    push_string(&mut payload, &key.input_map_id)?;
    for value in [
        &key.source_min,
        &key.source_max,
        &key.field_offset,
        &key.field_scale,
    ] {
        push_string(&mut payload, &value.numer().to_string())?;
        push_string(&mut payload, &value.denom().to_string())?;
    }
    push_bytes(&mut payload, &key.input_map_profile)?;
    Ok(sha256(&payload))
}

fn validate_state_physics(state: &State, max_working_bytes: usize) -> Result<(), String> {
    validate_state_structure(state, max_working_bytes)?;
    for field in &state.fields {
        let required = derive_requirement(&field.input).map_err(|error| error.to_string())?;
        let rebuilt = run_joint_field_l0_l4(
            field.input.clone(),
            JointFieldBudget {
                max_input_bytes: required.input_bytes,
                max_vertices: required.vertices,
                max_frames: required.frames,
                max_edges: required.edges,
                max_relation_facts: required.relation_facts,
                max_vertex_frame_values: required.vertex_frame_values,
            },
        )
        .map_err(|error| error.to_string())?;
        if rebuilt.authority_receipt_sha256 != field.experience_receipt
            || rebuilt.l4.authority_receipt_sha256 != field.complete_l4_receipt
        {
            return Err("joint persisted field authority changed".into());
        }
    }
    Ok(())
}

fn encode_state(state: &State) -> Result<Vec<u8>, String> {
    let mut output = Vec::new();
    output.extend_from_slice(MAGIC);
    output.extend_from_slice(&VERSION.to_le_bytes());
    output.extend_from_slice(&state.generation.to_le_bytes());
    output.extend_from_slice(&state.next_lineage_ordinal.to_le_bytes());
    output.extend_from_slice(&state.source_authority_receipt);
    push_optional_digest(&mut output, state.last_transition_receipt);
    push_u32(&mut output, state.fields.len())?;
    for field in &state.fields {
        output.extend_from_slice(&field.topology_receipt);
        push_u32(&mut output, field.group_authority_receipts.len())?;
        for receipt in &field.group_authority_receipts {
            output.extend_from_slice(receipt);
        }
        encode_input(&mut output, &field.input)?;
        output.extend_from_slice(&field.experience_receipt);
        output.extend_from_slice(&field.complete_l4_receipt);
    }
    push_u32(&mut output, state.neurons.len())?;
    for neuron in &state.neurons {
        encode_key(&mut output, &neuron.key)?;
        output.extend_from_slice(&neuron.lineage);
        output.extend_from_slice(&neuron.topology_receipt);
        encode_delivery_impression(&mut output, &neuron.delivery_impression)?;
        output.extend_from_slice(&neuron.transition_count.to_le_bytes());
    }
    output.push(u8::from(state.episode_relation_candidate.is_some()));
    if let Some(candidate) = &state.episode_relation_candidate {
        output.extend_from_slice(&candidate.source_authority_receipt);
        push_u32(&mut output, candidate.fields.len())?;
        for field in &candidate.fields {
            output.extend_from_slice(&field.topology_receipt);
            output.extend_from_slice(&field.exact_clock_receipt);
        }
        push_u32(&mut output, candidate.participating_lineages.len())?;
        for lineage in &candidate.participating_lineages {
            output.extend_from_slice(lineage);
        }
        output.push(u8::from(candidate.common_physical_cause_resolved));
        push_optional_digest(&mut output, candidate.predecessor_candidate_receipt);
        output.extend_from_slice(&candidate.authority_receipt);
    }
    Ok(output)
}

/// Encode the sole canonical empty mounted-neuron state.
///
/// This is a construction boundary for a genuinely new organism, not a
/// fallback for failed restore.  It contains no fields, neurons, learned
/// relation, semantic label, or synthetic experience.
pub(crate) fn encode_empty_mounted_joint_state() -> Result<Vec<u8>, String> {
    encode_state(&State::default())
}

fn restore_state_with_physics_validation(
    payload: &[u8],
    max_state_bytes: usize,
    max_working_bytes: usize,
) -> Result<(State, MountedRestoreValidationCost), String> {
    require_exact_schema(
        payload,
        MAGIC,
        VERSION,
        "current joint-DSF state is not GLJDSF03",
    )?;
    let state = decode_state(payload, max_state_bytes)?;
    let rebuilt_predecessor_field_count = state.fields.len();
    validate_state_physics(&state, max_working_bytes)?;
    Ok((
        state,
        MountedRestoreValidationCost {
            rebuilt_predecessor_field_count,
        },
    ))
}

fn authenticate_and_convert_gljnft02(
    payload: &[u8],
    max_state_bytes: usize,
    max_working_bytes: usize,
) -> Result<(State, MountedRestoreValidationCost), String> {
    require_exact_schema(
        payload,
        PRIOR_MAGIC,
        PRIOR_VERSION,
        "mounted source evidence is not GLJNFT02",
    )?;
    let mut state = decode_state(payload, max_state_bytes)?;
    for neuron in &mut state.neurons {
        authenticate_legacy_delivery_receipts(&neuron.delivery_impression)?;
        reseal_delivery_as_current(&mut neuron.delivery_impression)?;
    }
    state.last_transition_receipt = None;
    let rebuilt_predecessor_field_count = state.fields.len();
    validate_state_physics(&state, max_working_bytes)?;
    Ok((
        state,
        MountedRestoreValidationCost {
            rebuilt_predecessor_field_count,
        },
    ))
}

fn require_exact_schema(
    payload: &[u8],
    magic: &[u8; 8],
    version: u16,
    error: &'static str,
) -> Result<(), String> {
    if payload.len() < magic.len() + std::mem::size_of::<u16>()
        || &payload[..magic.len()] != magic
        || u16::from_le_bytes(
            payload[magic.len()..magic.len() + 2]
                .try_into()
                .expect("fixed mounted-state version"),
        ) != version
    {
        return Err(error.into());
    }
    Ok(())
}

struct DeliveryReceiptAuthority(Vec<u8>);

impl DeliveryReceiptAuthority {
    fn new(domain: &[u8]) -> Self {
        let mut value = Vec::new();
        value.extend_from_slice(&(domain.len() as u64).to_be_bytes());
        value.extend_from_slice(domain);
        Self(value)
    }

    fn bytes(&mut self, value: &[u8]) {
        self.0
            .extend_from_slice(&(value.len() as u64).to_be_bytes());
        self.0.extend_from_slice(value);
    }

    fn usize(&mut self, value: usize) {
        self.0.extend_from_slice(&(value as u64).to_be_bytes());
    }

    fn finish(self) -> [u8; 32] {
        sha256(&self.0)
    }
}

fn verify_delivery_shape(value: &DsfDeliveryImpression) -> Result<(), String> {
    let recurrence = &value.delivery_recurrence;
    if recurrence.coordinate_count != value.delivery_sign_impression.len()
        || recurrence
            .matching_nonnull
            .checked_add(recurrence.matching_quiescent)
            .and_then(|count| count.checked_add(recurrence.contradictions))
            .is_none_or(|count| count > recurrence.coordinate_count)
        || recurrence.predecessor_present != value.predecessor_impression_receipt_sha256.is_some()
    {
        return Err("legacy delivery recurrence evidence is incoherent".into());
    }
    Ok(())
}

fn recurrence_receipt(value: &DsfDeliveryImpression, domain: &[u8]) -> [u8; 32] {
    let recurrence = &value.delivery_recurrence;
    let mut authority = DeliveryReceiptAuthority::new(domain);
    authority.usize(recurrence.coordinate_count);
    authority.usize(recurrence.matching_nonnull);
    authority.usize(recurrence.matching_quiescent);
    authority.usize(recurrence.contradictions);
    authority.bytes(&[u8::from(recurrence.predecessor_present)]);
    authority.finish()
}

fn impression_receipt(
    value: &DsfDeliveryImpression,
    recurrence_authority: [u8; 32],
    domain: &[u8],
) -> [u8; 32] {
    let mut authority = DeliveryReceiptAuthority::new(domain);
    authority.bytes(&value.neuron_lineage);
    authority.bytes(&value.complete_field_receipt_sha256);
    authority.bytes(&value.perspective_receipt_sha256);
    if let Some(prior) = value.predecessor_impression_receipt_sha256 {
        authority.bytes(&prior);
    } else {
        authority.bytes(&[]);
    }
    for trit in &value.delivery_sign_impression {
        authority.bytes(&[*trit as i8 as u8]);
    }
    authority.bytes(&recurrence_authority);
    authority.finish()
}

fn authenticate_legacy_delivery_receipts(value: &DsfDeliveryImpression) -> Result<(), String> {
    verify_delivery_shape(value)?;
    let recurrence = recurrence_receipt(value, b"guala.native.dna_growth_evidence.v1");
    if recurrence != value.delivery_recurrence.authority_receipt_sha256 {
        return Err("legacy delivery recurrence authority changed".into());
    }
    let impression = impression_receipt(value, recurrence, b"guala.native.neuronal_fractal.v1");
    if impression != value.authority_receipt_sha256 {
        return Err("legacy DSF sign-delivery authority changed".into());
    }
    Ok(())
}

fn reseal_delivery_as_current(value: &mut DsfDeliveryImpression) -> Result<(), String> {
    let recurrence = recurrence_receipt(value, b"guala.native.dsf_delivery_recurrence.v1");
    value.delivery_recurrence.authority_receipt_sha256 = recurrence;
    value.authority_receipt_sha256 = impression_receipt(
        value,
        recurrence,
        b"guala.native.dsf_delivery_impression.v1",
    );
    verify_dsf_delivery_impression(value).map_err(|error| error.to_string())
}

/// Decode has no authority on its own.  Production restoration must pass the
/// result through `restore_state_with_physics_validation`, which accounts for
/// and performs the predecessor-field L0--L4 rebuild explicitly.
fn decode_state(payload: &[u8], max_state_bytes: usize) -> Result<State, String> {
    if payload.len() > max_state_bytes {
        return Err("joint-DSF input exceeds admitted storage".into());
    }
    let mut parser = Parser::new(payload);
    let magic = parser.take(8)?;
    let version = parser.u16()?;
    let current = magic == MAGIC && version == VERSION;
    let prior = magic == PRIOR_MAGIC && version == PRIOR_VERSION;
    let legacy = magic == LEGACY_MAGIC && version == LEGACY_VERSION;
    if !current && !prior && !legacy {
        return Err("joint-DSF state schema changed".into());
    }
    let generation = parser.u64()?;
    let next_lineage_ordinal = parser.u64()?;
    let source_authority_receipt = parser.digest()?;
    let last_transition_receipt = parser.optional_digest()?;
    let field_count = parser.u32()? as usize;
    let mut fields = Vec::with_capacity(parser.feasible(field_count, 100)?);
    for _ in 0..field_count {
        fields.push(JointFieldSnapshot {
            topology_receipt: parser.digest()?,
            group_authority_receipts: parser.digests()?,
            input: parser.input()?,
            experience_receipt: parser.digest()?,
            complete_l4_receipt: parser.digest()?,
        });
    }
    let neuron_count = parser.u32()? as usize;
    let mut neurons = Vec::with_capacity(parser.feasible(neuron_count, 230)?);
    for _ in 0..neuron_count {
        neurons.push(MountedNeuron {
            key: parser.key(current)?,
            lineage: parser.fixed()?,
            topology_receipt: parser.digest()?,
            delivery_impression: parser.delivery_impression()?,
            transition_count: parser.u64()?,
        });
    }
    let episode_relation_candidate = if legacy {
        None
    } else {
        match parser.u8()? {
            0 => None,
            1 => {
                let source_authority_receipt = parser.digest()?;
                let field_count = parser.u32()? as usize;
                let mut candidate_fields = Vec::with_capacity(parser.feasible(field_count, 64)?);
                for _ in 0..field_count {
                    candidate_fields.push(EpisodeFieldReference {
                        topology_receipt: parser.digest()?,
                        exact_clock_receipt: parser.digest()?,
                    });
                }
                let lineage_count = parser.u32()? as usize;
                let mut participating_lineages =
                    Vec::with_capacity(parser.feasible(lineage_count, 16)?);
                for _ in 0..lineage_count {
                    participating_lineages.push(parser.fixed()?);
                }
                let common_physical_cause_resolved = match parser.u8()? {
                    0 => false,
                    1 => true,
                    _ => return Err("episode relation cause flag changed".into()),
                };
                Some(EpisodeRelationCandidate {
                    source_authority_receipt,
                    fields: candidate_fields,
                    participating_lineages,
                    common_physical_cause_resolved,
                    predecessor_candidate_receipt: parser.optional_digest()?,
                    authority_receipt: parser.digest()?,
                })
            }
            _ => return Err("episode relation candidate flag changed".into()),
        }
    };
    if !parser.finished() {
        return Err("joint-DSF state has trailing bytes".into());
    }
    let mut state = State {
        generation,
        next_lineage_ordinal,
        source_authority_receipt,
        last_transition_receipt,
        fields,
        neurons,
        episode_relation_candidate,
    };
    if legacy {
        state.episode_relation_candidate = build_episode_relation_candidate(&state, None)?;
    }
    Ok(state)
}

fn encode_input(output: &mut Vec<u8>, input: &JointFieldInput) -> Result<(), String> {
    push_u32(output, input.vertex_ids.len())?;
    for value in &input.vertex_ids {
        push_string(output, value)?;
    }
    push_u32(output, input.groups.len())?;
    for group in &input.groups {
        push_u32(output, group.len())?;
        for index in group {
            output.extend_from_slice(
                &u64::try_from(*index)
                    .map_err(|_| "joint group index overflow")?
                    .to_le_bytes(),
            );
        }
    }
    push_u32(output, input.times.len())?;
    for value in &input.times {
        push_rational(output, value)?;
    }
    push_u32(output, input.vectors.len())?;
    for vector in &input.vectors {
        push_u32(output, vector.len())?;
        for value in vector {
            push_rational(output, value)?;
        }
    }
    Ok(())
}

fn encode_key(output: &mut Vec<u8>, key: &PhysicalPortKey) -> Result<(), String> {
    output.push(key.sense);
    output.extend_from_slice(&key.topology_index.to_le_bytes());
    push_string(output, &key.sensor_id)?;
    push_string(output, &key.substream_id)?;
    output.push(u8::from(!key.coordinates.is_empty()));
    if key.coordinates.is_empty() {
        return Ok(());
    }
    push_u32(output, key.coordinates.len())?;
    for coordinate in &key.coordinates {
        push_string(output, &coordinate.axis_id)?;
        push_string(output, &coordinate.coordinate_id)?;
    }
    push_string(output, &key.physical_quantity)?;
    push_string(output, &key.physical_unit)?;
    push_string(output, &key.relevance_rule)?;
    push_optional_string(output, key.relevance_origin.as_deref())?;
    push_string(output, &key.input_map_id)?;
    for value in [
        &key.source_min,
        &key.source_max,
        &key.field_offset,
        &key.field_scale,
    ] {
        push_rational(output, value)?;
    }
    push_bytes(output, &key.input_map_profile)?;
    output.extend_from_slice(&key.input_map_group_receipt);
    Ok(())
}

fn encode_delivery_impression(
    output: &mut Vec<u8>,
    value: &DsfDeliveryImpression,
) -> Result<(), String> {
    output.extend_from_slice(&value.neuron_lineage);
    output.extend_from_slice(&value.complete_field_receipt_sha256);
    output.extend_from_slice(&value.perspective_receipt_sha256);
    push_optional_digest(output, value.predecessor_impression_receipt_sha256);
    push_u32(output, value.delivery_sign_impression.len())?;
    for trit in &value.delivery_sign_impression {
        output.push(match trit {
            StructuralTrit::Negative => 0,
            StructuralTrit::Quiescent => 1,
            StructuralTrit::Positive => 2,
        });
    }
    let growth = &value.delivery_recurrence;
    for count in [
        growth.coordinate_count,
        growth.matching_nonnull,
        growth.matching_quiescent,
        growth.contradictions,
    ] {
        output.extend_from_slice(
            &u64::try_from(count)
                .map_err(|_| "joint growth count overflow")?
                .to_le_bytes(),
        );
    }
    output.push(u8::from(growth.predecessor_present));
    output.extend_from_slice(&growth.authority_receipt_sha256);
    output.extend_from_slice(&value.authority_receipt_sha256);
    Ok(())
}

fn push_rational(output: &mut Vec<u8>, value: &BigRational) -> Result<(), String> {
    push_bytes(output, &value.numer().to_signed_bytes_be())?;
    push_bytes(output, &value.denom().to_signed_bytes_be())
}

fn push_optional_digest(output: &mut Vec<u8>, value: Option<[u8; 32]>) {
    output.push(u8::from(value.is_some()));
    if let Some(value) = value {
        output.extend_from_slice(&value);
    }
}

fn push_bytes(output: &mut Vec<u8>, value: &[u8]) -> Result<(), String> {
    push_u32(output, value.len())?;
    output.extend_from_slice(value);
    Ok(())
}

fn push_string(output: &mut Vec<u8>, value: &str) -> Result<(), String> {
    push_bytes(output, value.as_bytes())
}

fn push_optional_string(output: &mut Vec<u8>, value: Option<&str>) -> Result<(), String> {
    output.push(u8::from(value.is_some()));
    if let Some(value) = value {
        push_string(output, value)?;
    }
    Ok(())
}

fn push_u32(output: &mut Vec<u8>, value: usize) -> Result<(), String> {
    output.extend_from_slice(
        &u32::try_from(value)
            .map_err(|_| "joint state cardinality exceeds u32")?
            .to_le_bytes(),
    );
    Ok(())
}

fn push_u32_bounded(output: &mut Vec<u8>, value: usize) {
    output.extend_from_slice(
        &u32::try_from(value)
            .expect("joint topology cardinality exceeds u32")
            .to_le_bytes(),
    );
}

fn push_string_bounded(output: &mut Vec<u8>, value: &str) {
    push_u32_bounded(output, value.len());
    output.extend_from_slice(value.as_bytes());
}

struct Parser<'a> {
    payload: &'a [u8],
    offset: usize,
}

impl<'a> Parser<'a> {
    fn new(payload: &'a [u8]) -> Self {
        Self { payload, offset: 0 }
    }
    fn finished(&self) -> bool {
        self.offset == self.payload.len()
    }
    fn feasible(&self, count: usize, minimum: usize) -> Result<usize, String> {
        if count
            .checked_mul(minimum)
            .ok_or("joint state count overflow")?
            > self.payload.len().saturating_sub(self.offset)
        {
            return Err("joint state count exceeds remaining bytes".into());
        }
        Ok(count)
    }
    fn take(&mut self, count: usize) -> Result<&'a [u8], String> {
        let end = self
            .offset
            .checked_add(count)
            .ok_or("joint length overflow")?;
        if end > self.payload.len() {
            return Err("joint state ended early".into());
        }
        let value = &self.payload[self.offset..end];
        self.offset = end;
        Ok(value)
    }
    fn u8(&mut self) -> Result<u8, String> {
        Ok(self.take(1)?[0])
    }
    fn u16(&mut self) -> Result<u16, String> {
        Ok(u16::from_le_bytes(self.take(2)?.try_into().unwrap()))
    }
    fn u32(&mut self) -> Result<u32, String> {
        Ok(u32::from_le_bytes(self.take(4)?.try_into().unwrap()))
    }
    fn u64(&mut self) -> Result<u64, String> {
        Ok(u64::from_le_bytes(self.take(8)?.try_into().unwrap()))
    }
    fn fixed<const N: usize>(&mut self) -> Result<[u8; N], String> {
        Ok(self.take(N)?.try_into().unwrap())
    }
    fn digest(&mut self) -> Result<[u8; 32], String> {
        self.fixed()
    }
    fn optional_digest(&mut self) -> Result<Option<[u8; 32]>, String> {
        match self.u8()? {
            0 => Ok(None),
            1 => Ok(Some(self.digest()?)),
            _ => Err("joint optional digest flag changed".into()),
        }
    }
    fn digests(&mut self) -> Result<Vec<[u8; 32]>, String> {
        let count = self.u32()? as usize;
        let mut values = Vec::with_capacity(self.feasible(count, 32)?);
        for _ in 0..count {
            values.push(self.digest()?);
        }
        Ok(values)
    }
    fn bytes(&mut self) -> Result<&'a [u8], String> {
        let count = self.u32()? as usize;
        self.take(count)
    }
    fn string(&mut self) -> Result<String, String> {
        let value = std::str::from_utf8(self.bytes()?)
            .map_err(|_| "joint string is not UTF-8")?
            .to_string();
        if value.is_empty() {
            return Err("joint string is empty".into());
        }
        Ok(value)
    }
    fn optional_string(&mut self) -> Result<Option<String>, String> {
        match self.u8()? {
            0 => Ok(None),
            1 => Ok(Some(self.string()?)),
            _ => Err("joint optional string flag changed".into()),
        }
    }
    fn rational(&mut self) -> Result<BigRational, String> {
        let numerator = BigInt::from_signed_bytes_be(self.bytes()?);
        let denominator = BigInt::from_signed_bytes_be(self.bytes()?);
        if denominator <= BigInt::zero() {
            return Err("joint rational denominator is not positive".into());
        }
        let value = BigRational::new(numerator, denominator);
        Ok(value)
    }
    fn input(&mut self) -> Result<JointFieldInput, String> {
        let vertex_count = self.u32()? as usize;
        let mut vertex_ids = Vec::with_capacity(self.feasible(vertex_count, 5)?);
        for _ in 0..vertex_count {
            vertex_ids.push(self.string()?);
        }
        let group_count = self.u32()? as usize;
        let mut groups = Vec::with_capacity(self.feasible(group_count, 4)?);
        for _ in 0..group_count {
            let count = self.u32()? as usize;
            let mut group = Vec::with_capacity(self.feasible(count, 8)?);
            for _ in 0..count {
                group.push(
                    usize::try_from(self.u64()?).map_err(|_| "joint group index exceeds usize")?,
                );
            }
            groups.push(group);
        }
        let time_count = self.u32()? as usize;
        let mut times = Vec::with_capacity(self.feasible(time_count, 10)?);
        for _ in 0..time_count {
            times.push(self.rational()?);
        }
        let vector_count = self.u32()? as usize;
        let mut vectors = Vec::with_capacity(self.feasible(vector_count, 4)?);
        for _ in 0..vector_count {
            let count = self.u32()? as usize;
            let mut vector = Vec::with_capacity(self.feasible(count, 10)?);
            for _ in 0..count {
                vector.push(self.rational()?);
            }
            vectors.push(vector);
        }
        Ok(JointFieldInput {
            vertex_ids,
            groups,
            times,
            vectors,
        })
    }
    fn key(&mut self, typed_binding_present: bool) -> Result<PhysicalPortKey, String> {
        let sense = self.u8()?;
        let topology_index = self.u32()?;
        let sensor_id = self.string()?;
        let substream_id = self.string()?;
        let binding_resolved = if typed_binding_present {
            match self.u8()? {
                0 => false,
                1 => true,
                _ => return Err("joint receptor-binding flag changed".into()),
            }
        } else {
            false
        };
        let coordinates = if binding_resolved {
            let count = self.u32()? as usize;
            let mut coordinates = Vec::with_capacity(self.feasible(count, 10)?);
            for _ in 0..count {
                coordinates.push(JointSourceCoordinate {
                    axis_id: self.string()?,
                    coordinate_id: self.string()?,
                });
            }
            coordinates
        } else {
            Vec::new()
        };
        let (
            physical_quantity,
            physical_unit,
            relevance_rule,
            relevance_origin,
            input_map_id,
            source_min,
            source_max,
            field_offset,
            field_scale,
            input_map_profile,
            input_map_group_receipt,
        ) = if binding_resolved {
            (
                self.string()?,
                self.string()?,
                self.string()?,
                self.optional_string()?,
                self.string()?,
                self.rational()?,
                self.rational()?,
                self.rational()?,
                self.rational()?,
                self.bytes()?.to_vec(),
                self.digest()?,
            )
        } else {
            (
                String::new(),
                String::new(),
                String::new(),
                None,
                String::new(),
                BigRational::zero(),
                BigRational::zero(),
                BigRational::zero(),
                BigRational::zero(),
                Vec::new(),
                [0; 32],
            )
        };
        Ok(PhysicalPortKey {
            sense,
            topology_index,
            sensor_id,
            substream_id,
            coordinates,
            physical_quantity,
            physical_unit,
            relevance_rule,
            relevance_origin,
            input_map_id,
            source_min,
            source_max,
            field_offset,
            field_scale,
            input_map_profile,
            input_map_group_receipt,
        })
    }
    fn delivery_impression(&mut self) -> Result<DsfDeliveryImpression, String> {
        let neuron_lineage = self.fixed()?;
        let complete_field_receipt_sha256 = self.digest()?;
        let perspective_receipt_sha256 = self.digest()?;
        let predecessor_impression_receipt_sha256 = self.optional_digest()?;
        let count = self.u32()? as usize;
        let mut delivery_sign_impression = Vec::with_capacity(self.feasible(count, 1)?);
        for _ in 0..count {
            delivery_sign_impression.push(match self.u8()? {
                0 => StructuralTrit::Negative,
                1 => StructuralTrit::Quiescent,
                2 => StructuralTrit::Positive,
                _ => return Err("joint structural trit changed".into()),
            });
        }
        let coordinate_count =
            usize::try_from(self.u64()?).map_err(|_| "joint coordinate count exceeds usize")?;
        let matching_nonnull =
            usize::try_from(self.u64()?).map_err(|_| "joint matching count exceeds usize")?;
        let matching_quiescent =
            usize::try_from(self.u64()?).map_err(|_| "joint quiescent count exceeds usize")?;
        let contradictions =
            usize::try_from(self.u64()?).map_err(|_| "joint contradiction count exceeds usize")?;
        let predecessor_present = match self.u8()? {
            0 => false,
            1 => true,
            _ => return Err("joint predecessor flag changed".into()),
        };
        let growth_receipt = self.digest()?;
        let authority_receipt_sha256 = self.digest()?;
        Ok(DsfDeliveryImpression {
            neuron_lineage,
            complete_field_receipt_sha256,
            perspective_receipt_sha256,
            predecessor_impression_receipt_sha256,
            delivery_sign_impression,
            delivery_recurrence: DsfDeliveryRecurrence {
                coordinate_count,
                matching_nonnull,
                matching_quiescent,
                contradictions,
                predecessor_present,
                authority_receipt_sha256: growth_receipt,
            },
            authority_receipt_sha256,
        })
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::joint_source_episode::decode_native_joint_source_episode;

    fn test_u16(output: &mut Vec<u8>, value: u16) {
        output.extend_from_slice(&value.to_le_bytes());
    }

    fn test_u32(output: &mut Vec<u8>, value: u32) {
        output.extend_from_slice(&value.to_le_bytes());
    }

    fn test_text(output: &mut Vec<u8>, value: &str) {
        test_u16(output, value.len().try_into().unwrap());
        output.extend_from_slice(value.as_bytes());
    }

    fn test_rational(output: &mut Vec<u8>, numerator: i64, denominator: i64) {
        test_text(output, &numerator.to_string());
        test_text(output, &denominator.to_string());
    }

    fn test_source_port(output: &mut Vec<u8>, topology: u32, values: [(i64, f64); 2]) {
        output.push(0);
        test_u32(output, topology);
        test_text(output, &format!("retina-{topology}"));
        test_text(output, "luminance");
        test_u16(output, 1);
        test_text(output, "receptor");
        test_text(output, &topology.to_string());
        test_text(output, "light");
        test_text(output, "normalized");
        test_text(output, "direct");
        test_text(output, "");
        test_text(output, "affine");
        test_rational(output, -1, 1);
        test_rational(output, 1, 1);
        test_rational(output, 1, 1);
        test_rational(output, 1, 1);
        test_u32(output, 1);
        output.push(topology as u8);
        test_u32(output, 2);
        for (time, signal) in values {
            test_rational(output, time, 1);
            output.extend_from_slice(&signal.to_bits().to_le_bytes());
            test_rational(output, 0, 1);
            test_rational(output, 1, 1);
            test_rational(output, (1.0 + signal) as i64, 1);
        }
    }

    fn test_source(episode_id: &str) -> NativeJointSourceEpisode {
        test_source_with_ports(
            episode_id,
            &[(0, [(1, 0.0), (2, 1.0)]), (1, [(1, 1.0), (2, 0.0)])],
        )
    }

    fn test_source_with_ports(
        episode_id: &str,
        ports: &[(u32, [(i64, f64); 2])],
    ) -> NativeJointSourceEpisode {
        let mut output = b"GLJSRC02".to_vec();
        test_u16(&mut output, 2);
        test_text(&mut output, episode_id);
        output.extend_from_slice(&[0, 1, 1, 1, 1, 1]);
        test_u32(&mut output, ports.len().try_into().unwrap());
        for (topology, values) in ports {
            test_source_port(&mut output, *topology, *values);
        }
        test_u32(&mut output, ports.len().try_into().unwrap());
        for (port_index, (_, values)) in ports.iter().enumerate() {
            test_u32(&mut output, 1);
            test_u32(&mut output, port_index.try_into().unwrap());
            test_u32(&mut output, 2);
            for (time, _) in values {
                test_rational(&mut output, *time, 1);
            }
            test_u32(&mut output, 1);
            output.push(2);
            test_u32(&mut output, 1);
            test_u32(&mut output, 1);
            test_u32(&mut output, 0);
            test_u32(&mut output, 1);
            output.push(1);
            test_u32(&mut output, 2);
            test_rational(&mut output, 1, 1);
            test_rational(&mut output, 1, 1);
        }
        decode_native_joint_source_episode(
            &output,
            ports.len(),
            ports.len() * 2,
            ports.len(),
            ports.len() * 2,
        )
        .unwrap()
    }

    fn reference_transition_mounted_joint_dsf(
        prior_state: &[u8],
        source: &NativeJointSourceEpisode,
        max_state_bytes: usize,
        max_working_bytes: usize,
    ) -> Result<PreparedMountedGeneration, String> {
        if max_state_bytes == 0 || max_working_bytes == 0 {
            return Err("joint-DSF state or working memory is not admitted".into());
        }
        let (mut state, restore_validation_cost) = if prior_state.is_empty() {
            (
                State::default(),
                MountedRestoreValidationCost {
                    rebuilt_predecessor_field_count: 0,
                },
            )
        } else {
            restore_state_with_physics_validation(prior_state, max_state_bytes, max_working_bytes)?
        };
        let cold_restore_work = ResidentMountedRestoreWork {
            authentication_count: 1,
            decode_count: usize::from(!prior_state.is_empty()),
            rebuilt_predecessor_field_count: restore_validation_cost
                .rebuilt_predecessor_field_count,
        };
        let predecessor_generation = state.generation;
        let retained_neuron_index_entry_count = state.neurons.len();
        let mut reached_neuron_lookup_count = 0usize;
        let prior_episode_relation_candidate = state.episode_relation_candidate.clone();
        state.generation = state
            .generation
            .checked_add(1)
            .ok_or("joint-DSF generation overflow")?;
        state.source_authority_receipt = source.joint_source_authority_receipt();

        let cohorts = exact_time_cohorts(source.joint_source_ports().to_vec())?;
        let mut current_fields = Vec::new();
        let mut prepared_fields = Vec::new();
        let mut transitioned = 0usize;
        let mut recurrent = 0usize;
        let mut l0_l4_evaluation_count = 0usize;
        let mut transition_authority = Vec::new();
        transition_authority.extend_from_slice(b"guala.native.mounted_joint_dsf_transition.v1");
        transition_authority.extend_from_slice(&state.generation.to_le_bytes());
        transition_authority.extend_from_slice(&state.source_authority_receipt);

        for ports in cohorts {
            let (input, keys, group_authority_receipts, topology_receipt) = joint_input(&ports)?;
            let requirement = derive_requirement(&input).map_err(|error| error.to_string())?;
            let working_bytes = derived_working_bytes(&input, &requirement)?;
            if working_bytes > max_working_bytes {
                return Err(format!(
                    "joint field requires {working_bytes} derived working bytes, admitted {max_working_bytes}"
                ));
            }
            let experience = run_joint_field_l0_l4(
                input.clone(),
                JointFieldBudget {
                    max_input_bytes: requirement.input_bytes,
                    max_vertices: requirement.vertices,
                    max_frames: requirement.frames,
                    max_edges: requirement.edges,
                    max_relation_facts: requirement.relation_facts,
                    max_vertex_frame_values: requirement.vertex_frame_values,
                },
            )
            .map_err(|error| error.to_string())?;
            l0_l4_evaluation_count = l0_l4_evaluation_count
                .checked_add(1)
                .ok_or("joint L0-L4 evaluation count overflow")?;
            let frame_index = requirement.frames - 1;
            let mut perspectives = Vec::with_capacity(keys.len());
            let mut replacements = Vec::with_capacity(keys.len());
            for (vertex_index, key) in keys.iter().enumerate() {
                reached_neuron_lookup_count = reached_neuron_lookup_count
                    .checked_add(1)
                    .ok_or("joint reached-neuron lookup count overflow")?;
                let neuron_index = find_or_create_neuron(&mut state, key.clone())?;
                let lineage = state.neurons[neuron_index].lineage;
                let perspective =
                    bind_neuron_perspective(&experience.l4, lineage, vertex_index, frame_index)
                        .map_err(|error| error.to_string())?;
                let predecessor = (state.neurons[neuron_index].transition_count > 0
                    && state.neurons[neuron_index].topology_receipt == topology_receipt)
                    .then(|| state.neurons[neuron_index].delivery_impression.clone());
                let delivery_impression = settle_dsf_delivery_impression(
                    &experience.l4,
                    &perspective,
                    predecessor.as_ref(),
                )
                .map_err(|error| error.to_string())?;
                transitioned = transitioned
                    .checked_add(1)
                    .ok_or("joint DSF-delivery count overflow")?;
                if predecessor.is_some() {
                    recurrent = recurrent
                        .checked_add(1)
                        .ok_or("joint recurrent DSF-delivery count overflow")?;
                }
                transition_authority
                    .extend_from_slice(&delivery_impression.authority_receipt_sha256);
                perspectives.push(perspective);
                replacements.push((neuron_index, predecessor, delivery_impression));
            }
            reconstruct_cohesion(&experience.l4, &perspectives)
                .map_err(|error| error.to_string())?;
            let mut prepared_neurons = Vec::with_capacity(replacements.len());
            for (perspective, (neuron_index, predecessor, successor)) in
                perspectives.into_iter().zip(replacements)
            {
                let neuron = &mut state.neurons[neuron_index];
                neuron.topology_receipt = topology_receipt;
                neuron.delivery_impression = successor.clone();
                neuron.transition_count = neuron
                    .transition_count
                    .checked_add(1)
                    .ok_or("joint neuron transition count overflow")?;
                prepared_neurons.push(PreparedMountedNeuronTransition {
                    predecessor_generation,
                    successor_generation: state.generation,
                    topology_authority: topology_receipt,
                    perspective,
                    predecessor,
                    successor,
                });
            }
            current_fields.push(snapshot(
                input,
                topology_receipt,
                group_authority_receipts,
                &experience,
            ));
            prepared_fields.push(PreparedMountedFieldSettlement {
                topology_authority: topology_receipt,
                source_ports: ports,
                experience,
                neurons: prepared_neurons,
            });
        }

        current_fields.sort_by_key(|field| field.topology_receipt);
        if current_fields
            .windows(2)
            .any(|pair| pair[0].topology_receipt == pair[1].topology_receipt)
        {
            return Err("joint field repeats a physical topology".into());
        }
        prepared_fields.sort_by_key(|field| field.topology_authority);
        state.fields = current_fields;
        state
            .neurons
            .sort_by(|left, right| left.key.cmp(&right.key));
        state.episode_relation_candidate =
            build_episode_relation_candidate(&state, prior_episode_relation_candidate.as_ref())?;
        let transition_receipt = if transitioned == 0 {
            None
        } else {
            Some(sha256(&transition_authority))
        };
        state.last_transition_receipt = transition_receipt;
        validate_state_structure(&state, max_working_bytes)?;
        let state_bytes = encode_state(&state)?;
        if state_bytes.len() > max_state_bytes {
            return Err(format!(
                "joint-DSF state requires {} bytes, admitted {max_state_bytes}",
                state_bytes.len()
            ));
        }
        let transition = MountedJointDsfTransition {
            joint_field_count: state.fields.len(),
            joint_neuron_count: state.neurons.len(),
            l0_l4_evaluation_count,
            dsf_delivery_count: transitioned,
            recurrent_dsf_delivery_count: recurrent,
            transition_receipt,
            episode_relation_candidate_receipt: state
                .episode_relation_candidate
                .as_ref()
                .map(|candidate| candidate.authority_receipt),
        };
        let successor_generation = state.generation;
        let source_authority = state.source_authority_receipt;
        let successor_resident_state = ResidentMountedState {
            state,
            cold_restore_work,
        };
        Ok(PreparedMountedGeneration {
            predecessor_generation,
            successor_generation,
            source_authority,
            source_body: source.joint_source_body(),
            restore_validation_cost,
            fields: prepared_fields,
            state_bytes,
            transition,
            successor_resident_state,
            phase_counts: MountedTransitionPhaseCounts {
                predecessor_authentication_count: 1,
                predecessor_decode_count: cold_restore_work.decode_count,
                predecessor_rebuilt_field_count: cold_restore_work.rebuilt_predecessor_field_count,
                retained_neuron_index_entry_count,
                reached_neuron_lookup_count,
                current_cohort_evaluation_count: l0_l4_evaluation_count,
                successor_seal_count: 1,
            },
        })
    }

    fn key(coordinate: Option<&str>) -> PhysicalPortKey {
        let resolved = coordinate.is_some();
        let mut result = PhysicalPortKey {
            sense: 0,
            topology_index: 0,
            sensor_id: "retina".into(),
            substream_id: "foveal-0".into(),
            coordinates: coordinate
                .map(|value| {
                    vec![JointSourceCoordinate {
                        axis_id: "column".into(),
                        coordinate_id: value.into(),
                    }]
                })
                .unwrap_or_default(),
            physical_quantity: resolved.then_some("light").unwrap_or("").into(),
            physical_unit: resolved.then_some("normalized").unwrap_or("").into(),
            relevance_rule: resolved.then_some("direct").unwrap_or("").into(),
            relevance_origin: None,
            input_map_id: resolved.then_some("affine").unwrap_or("").into(),
            source_min: if resolved {
                BigRational::from_integer((-1).into())
            } else {
                BigRational::zero()
            },
            source_max: if resolved {
                BigRational::from_integer(1.into())
            } else {
                BigRational::zero()
            },
            field_offset: if resolved {
                BigRational::from_integer(1.into())
            } else {
                BigRational::zero()
            },
            field_scale: if resolved {
                BigRational::new(1.into(), 2.into())
            } else {
                BigRational::zero()
            },
            input_map_profile: resolved.then_some(vec![7]).unwrap_or_default(),
            input_map_group_receipt: [0; 32],
        };
        if resolved {
            result.input_map_group_receipt =
                reconstructed_input_map_group_receipt(&result).unwrap();
        }
        result
    }

    #[test]
    fn prior_coordinate_less_neuron_is_enriched_without_changing_lineage() {
        let mut state = State::default();
        let index = find_or_create_neuron(&mut state, key(None)).unwrap();
        let lineage = state.neurons[index].lineage;

        assert_eq!(
            find_or_create_neuron(&mut state, key(Some("0"))).unwrap(),
            index
        );
        assert_eq!(state.neurons[index].lineage, lineage);
        assert_eq!(state.neurons[index].key, key(Some("0")));
    }

    #[test]
    fn changed_resolved_coordinate_cannot_reuse_a_neuron_lineage() {
        let mut state = State::default();
        find_or_create_neuron(&mut state, key(Some("0"))).unwrap();

        assert_eq!(
            find_or_create_neuron(&mut state, key(Some("1"))).unwrap_err(),
            "joint neuron physical binding changed without migration"
        );
    }

    #[test]
    fn typed_receptor_binding_cannot_diverge_from_its_resolvable_authority() {
        let mut binding = key(Some("0"));
        validate_physical_port_key(&binding).unwrap();
        binding.physical_unit = "fabricated-unit".into();

        assert_eq!(
            validate_physical_port_key(&binding).unwrap_err(),
            "resolved receptor binding authority changed"
        );
    }

    #[test]
    fn prior_unresolved_binding_cannot_contain_partial_anatomy() {
        let mut binding = key(None);
        binding.physical_quantity = "light".into();

        assert_eq!(
            validate_physical_port_key(&binding).unwrap_err(),
            "unresolved prior receptor binding contains partial anatomy"
        );
    }

    #[test]
    fn resolved_and_migrating_receptor_bindings_round_trip_exactly() {
        for expected in [key(None), key(Some("0"))] {
            let mut bytes = Vec::new();
            encode_key(&mut bytes, &expected).unwrap();
            let mut parser = Parser::new(&bytes);
            assert_eq!(parser.key(true).unwrap(), expected);
            assert!(parser.finished());
        }
    }

    #[test]
    fn current_only_summary_rejects_decodable_historical_bodies() {
        let current = encode_state(&State::default()).unwrap();
        let requirement = preflight_current_inspection(&current).unwrap();
        inspect_current_mounted_joint_dsf_summary(&current, current.len(), &requirement).unwrap();

        let mut prior = current.clone();
        prior[..8].copy_from_slice(PRIOR_MAGIC);
        prior[8..10].copy_from_slice(&PRIOR_VERSION.to_le_bytes());
        assert_eq!(
            inspect_mounted_joint_dsf_summary(&prior, prior.len(), 1).unwrap_err(),
            "current joint-DSF state is not GLJDSF03"
        );
        assert_eq!(
            preflight_current_inspection(&prior).unwrap_err(),
            "current joint-DSF state is not GLJDSF03"
        );

        let mut legacy = current;
        legacy[..8].copy_from_slice(LEGACY_MAGIC);
        legacy[8..10].copy_from_slice(&LEGACY_VERSION.to_le_bytes());
        assert_eq!(legacy.pop(), Some(0));
        assert_eq!(
            inspect_mounted_joint_dsf_summary(&legacy, legacy.len(), 1).unwrap_err(),
            "current joint-DSF state is not GLJDSF03"
        );
        assert_eq!(
            preflight_current_inspection(&legacy).unwrap_err(),
            "current joint-DSF state is not GLJDSF03"
        );
    }

    fn synthetic_legacy_delivery() -> DsfDeliveryImpression {
        let mut value = DsfDeliveryImpression {
            neuron_lineage: [7; 16],
            complete_field_receipt_sha256: [8; 32],
            perspective_receipt_sha256: [9; 32],
            predecessor_impression_receipt_sha256: Some([10; 32]),
            delivery_sign_impression: vec![
                StructuralTrit::Negative,
                StructuralTrit::Quiescent,
                StructuralTrit::Positive,
            ],
            delivery_recurrence: DsfDeliveryRecurrence {
                coordinate_count: 3,
                matching_nonnull: 1,
                matching_quiescent: 1,
                contradictions: 1,
                predecessor_present: true,
                authority_receipt_sha256: [0; 32],
            },
            authority_receipt_sha256: [0; 32],
        };
        let recurrence = recurrence_receipt(&value, b"guala.native.dna_growth_evidence.v1");
        value.delivery_recurrence.authority_receipt_sha256 = recurrence;
        value.authority_receipt_sha256 =
            impression_receipt(&value, recurrence, b"guala.native.neuronal_fractal.v1");
        value
    }

    #[test]
    fn historical_delivery_receipts_authenticate_then_reseal_only_as_current_evidence() {
        let mut value = synthetic_legacy_delivery();
        let historical = value.authority_receipt_sha256;
        authenticate_legacy_delivery_receipts(&value).unwrap();
        reseal_delivery_as_current(&mut value).unwrap();
        assert_ne!(value.authority_receipt_sha256, historical);
        verify_dsf_delivery_impression(&value).unwrap();
        assert_eq!(
            authenticate_legacy_delivery_receipts(&value).unwrap_err(),
            "legacy delivery recurrence authority changed"
        );
    }

    #[test]
    fn historical_delivery_tampering_is_refused_before_reseal() {
        let mut recurrence = synthetic_legacy_delivery();
        recurrence.delivery_recurrence.authority_receipt_sha256[0] ^= 1;
        assert_eq!(
            authenticate_legacy_delivery_receipts(&recurrence).unwrap_err(),
            "legacy delivery recurrence authority changed"
        );

        let mut impression = synthetic_legacy_delivery();
        impression.authority_receipt_sha256[0] ^= 1;
        assert_eq!(
            authenticate_legacy_delivery_receipts(&impression).unwrap_err(),
            "legacy DSF sign-delivery authority changed"
        );

        let mut coordinate = synthetic_legacy_delivery();
        coordinate.delivery_sign_impression[0] = StructuralTrit::Positive;
        assert_eq!(
            authenticate_legacy_delivery_receipts(&coordinate).unwrap_err(),
            "legacy DSF sign-delivery authority changed"
        );
    }

    #[test]
    fn parser_can_decode_a_noncanonical_rational_but_canonical_encoder_changes_it() {
        let mut noncanonical = Vec::new();
        push_bytes(&mut noncanonical, &[2]).unwrap();
        push_bytes(&mut noncanonical, &[2]).unwrap();

        let mut parser = Parser::new(&noncanonical);
        let value = parser.rational().unwrap();
        assert!(parser.finished());
        assert_eq!(value, BigRational::from_integer(1.into()));

        let mut canonical = Vec::new();
        push_rational(&mut canonical, &value).unwrap();
        assert_ne!(canonical, noncanonical);
    }

    #[test]
    fn current_inspection_plan_binds_exact_logical_components_and_receipt() {
        let current = encode_state(&State::default()).unwrap();
        let plan = preflight_current_inspection(&current).unwrap();
        assert_eq!(plan.borrowed_joint_bytes, current.len());
        assert_eq!(plan.joint_receipt, sha256(&current));
        assert_eq!(
            plan.retained_decoded_logical_bytes,
            plan.retained_decoded_container_bytes
                + plan.retained_decoded_payload_bytes
                + plan.retained_decoded_limb_bytes
        );
        assert_eq!(
            plan.additional_logical_arena_bytes,
            plan.retained_decoded_logical_bytes
                + (plan.largest_field_rebuild_logical_bytes
                    + plan.validation_logical_scratch_bytes)
                    .max(plan.canonical_streaming_scratch_bytes)
        );
        assert_eq!(
            plan.arena_status,
            LogicalArenaStatus::GeneralAllocatorRequired
        );
        inspect_current_mounted_joint_dsf_summary(&current, current.len(), &plan).unwrap();

        let mut substituted = plan;
        substituted.additional_logical_arena_bytes -= 1;
        assert_eq!(
            inspect_current_mounted_joint_dsf_summary(&current, current.len(), &substituted)
                .unwrap_err(),
            "current joint inspection plan does not bind this exact state"
        );
    }

    #[test]
    fn current_preflight_rejects_adversarial_counts_without_allocation() {
        let mut current = encode_state(&State::default()).unwrap();
        let field_count_offset = 8 + 2 + 8 + 8 + 32 + 1;
        current[field_count_offset..field_count_offset + 4]
            .copy_from_slice(&u32::MAX.to_le_bytes());
        assert_eq!(
            preflight_current_inspection(&current).unwrap_err(),
            "current inspection count exceeds remaining bytes"
        );
    }

    #[test]
    fn repeated_current_preflight_is_constant_and_does_not_change_bytes() {
        let current = encode_state(&State::default()).unwrap();
        let expected = preflight_current_inspection(&current).unwrap();
        for _ in 0..100_000 {
            assert_eq!(preflight_current_inspection(&current).unwrap(), expected);
        }
        assert_eq!(current, encode_state(&State::default()).unwrap());
    }

    #[test]
    fn prepared_generation_retains_the_once_settled_full_field_and_typed_neurons() {
        let source = test_source("prepared-generation-1");
        let mut new_field_evaluations = 0usize;
        let prepared = transition_mounted_joint_dsf_with(
            &[],
            &source,
            1_048_576,
            1_048_576,
            |input, budget| {
                new_field_evaluations += 1;
                run_joint_field_l0_l4(input, budget)
            },
        )
        .unwrap();

        assert_eq!(new_field_evaluations, 1);
        assert_eq!(prepared.predecessor_generation(), 0);
        assert_eq!(prepared.successor_generation(), 1);
        assert_eq!(
            prepared.source_authority(),
            source.joint_source_authority_receipt()
        );
        assert_eq!(
            prepared.restore_validation_cost(),
            MountedRestoreValidationCost {
                rebuilt_predecessor_field_count: 0,
            }
        );
        assert_eq!(prepared.fields().len(), 1);
        assert_eq!(prepared.transition().joint_field_count, 1);
        assert_eq!(prepared.transition().joint_neuron_count, 2);
        assert_eq!(prepared.transition().dsf_delivery_count, 2);

        let field = &prepared.fields()[0];
        assert_eq!(
            field.experience().l4.authority_receipt_sha256,
            field
                .neurons()
                .first()
                .unwrap()
                .perspective()
                .complete_field_receipt_sha256
        );
        for neuron in field.neurons() {
            assert_eq!(neuron.topology_authority(), field.topology_authority());
            assert!(neuron.predecessor().is_none());
            assert_eq!(
                neuron.perspective().authority_receipt_sha256,
                neuron.successor().perspective_receipt_sha256
            );
            assert_eq!(
                neuron.successor().complete_field_receipt_sha256,
                field.experience().l4.authority_receipt_sha256
            );
            assert_eq!(
                neuron.successor().neuron_lineage,
                neuron.perspective().neuron_lineage
            );
        }

        // Typed downstream reads and serialization access do not invoke the
        // evaluator again; no body is parsed to obtain these values.
        assert!(!prepared.state_bytes().is_empty());
        assert_eq!(new_field_evaluations, 1);

        let decoded = decode_state(prepared.state_bytes(), prepared.state_bytes().len()).unwrap();
        assert_eq!(encode_state(&decoded).unwrap(), prepared.state_bytes());
    }

    #[test]
    fn recurrent_prepared_generation_preserves_exact_predecessor_continuity() {
        let first = transition_mounted_joint_dsf(
            &[],
            &test_source("prepared-generation-1"),
            1_048_576,
            1_048_576,
        )
        .unwrap();
        let prior_by_lineage = first.fields()[0]
            .neurons()
            .iter()
            .map(|neuron| {
                (
                    neuron.successor().neuron_lineage,
                    neuron.successor().clone(),
                )
            })
            .collect::<BTreeMap<_, _>>();
        let first_bytes = first.state_bytes().to_vec();

        let mut new_field_evaluations = 0usize;
        let second = transition_mounted_joint_dsf_with(
            &first_bytes,
            &test_source("prepared-generation-2"),
            1_048_576,
            1_048_576,
            |input, budget| {
                new_field_evaluations += 1;
                run_joint_field_l0_l4(input, budget)
            },
        )
        .unwrap();

        assert_eq!(new_field_evaluations, 1);
        assert_eq!(second.predecessor_generation(), 1);
        assert_eq!(second.successor_generation(), 2);
        assert_eq!(
            second.restore_validation_cost(),
            MountedRestoreValidationCost {
                rebuilt_predecessor_field_count: 1,
            }
        );
        assert_eq!(second.transition().recurrent_dsf_delivery_count, 2);
        for neuron in second.fields()[0].neurons() {
            let expected = prior_by_lineage
                .get(&neuron.successor().neuron_lineage)
                .unwrap();
            assert_eq!(neuron.predecessor(), Some(expected));
            assert_eq!(
                neuron.successor().predecessor_impression_receipt_sha256,
                Some(expected.authority_receipt_sha256)
            );
        }
        assert_eq!(new_field_evaluations, 1);

        let decoded = decode_state(second.state_bytes(), second.state_bytes().len()).unwrap();
        assert_eq!(encode_state(&decoded).unwrap(), second.state_bytes());
    }

    fn assert_refactored_transition_matches_reference(
        prior_state: &[u8],
        source: &NativeJointSourceEpisode,
    ) -> PreparedMountedGeneration {
        let expected =
            reference_transition_mounted_joint_dsf(prior_state, source, 8_388_608, 8_388_608)
                .unwrap();
        let actual =
            transition_mounted_joint_dsf(prior_state, source, 8_388_608, 8_388_608).unwrap();
        assert_eq!(actual, expected);
        actual
    }

    #[test]
    fn staged_boundary_is_byte_exact_for_one_two_three_and_four_ports() {
        let cases = [
            test_source_with_ports("one-port", &[(0, [(1, 0.0), (2, 1.0)])]),
            test_source("two-port"),
            test_source_with_ports(
                "three-port",
                &[
                    (0, [(1, 0.0), (2, 1.0)]),
                    (1, [(1, 1.0), (2, 0.0)]),
                    (2, [(1, 0.0), (2, 1.0)]),
                ],
            ),
            test_source_with_ports(
                "four-port",
                &[
                    (0, [(1, 0.0), (2, 1.0)]),
                    (1, [(1, 1.0), (2, 0.0)]),
                    (2, [(1, 0.0), (2, 1.0)]),
                    (3, [(1, 1.0), (2, 0.0)]),
                ],
            ),
        ];
        for source in cases {
            assert_refactored_transition_matches_reference(&[], &source);
        }
    }

    #[test]
    fn staged_boundary_is_byte_exact_for_recurrence_and_multiple_exact_clocks() {
        let first_source = test_source("recurrence-first");
        let first = assert_refactored_transition_matches_reference(&[], &first_source);
        let recurrent_source = test_source("recurrence-second");
        assert_refactored_transition_matches_reference(first.state_bytes(), &recurrent_source);

        let multiple_clocks = test_source_with_ports(
            "multiple-exact-clocks",
            &[
                (0, [(1, 0.0), (2, 1.0)]),
                (1, [(1, 1.0), (2, 0.0)]),
                (2, [(3, 0.0), (4, 1.0)]),
                (3, [(3, 1.0), (4, 0.0)]),
            ],
        );
        let prepared = assert_refactored_transition_matches_reference(&[], &multiple_clocks);
        assert_eq!(prepared.fields().len(), 2);
    }

    #[test]
    fn phase_counts_separate_cold_proof_reached_evaluation_and_single_seal() {
        let one_port = transition_mounted_joint_dsf(
            &[],
            &test_source_with_ports("one-port-phases", &[(0, [(1, 0.0), (2, 1.0)])]),
            8_388_608,
            8_388_608,
        )
        .unwrap();
        assert_eq!(
            one_port.phase_counts(),
            MountedTransitionPhaseCounts {
                predecessor_authentication_count: 1,
                predecessor_decode_count: 0,
                predecessor_rebuilt_field_count: 0,
                retained_neuron_index_entry_count: 0,
                reached_neuron_lookup_count: 0,
                current_cohort_evaluation_count: 0,
                successor_seal_count: 1,
            }
        );

        let first =
            transition_mounted_joint_dsf(&[], &test_source("phase-first"), 8_388_608, 8_388_608)
                .unwrap();
        let recurrent = transition_mounted_joint_dsf(
            first.state_bytes(),
            &test_source("phase-recurrent"),
            8_388_608,
            8_388_608,
        )
        .unwrap();
        assert_eq!(
            recurrent.restore_validation_cost(),
            MountedRestoreValidationCost {
                rebuilt_predecessor_field_count: 1,
            }
        );
        assert_eq!(
            recurrent.phase_counts(),
            MountedTransitionPhaseCounts {
                predecessor_authentication_count: 1,
                predecessor_decode_count: 1,
                predecessor_rebuilt_field_count: 1,
                retained_neuron_index_entry_count: 2,
                reached_neuron_lookup_count: 2,
                current_cohort_evaluation_count: 1,
                successor_seal_count: 1,
            }
        );

        let multiple_clocks = transition_mounted_joint_dsf(
            &[],
            &test_source_with_ports(
                "phase-multiple-clocks",
                &[
                    (0, [(1, 0.0), (2, 1.0)]),
                    (1, [(1, 1.0), (2, 0.0)]),
                    (2, [(3, 0.0), (4, 1.0)]),
                    (3, [(3, 1.0), (4, 0.0)]),
                ],
            ),
            8_388_608,
            8_388_608,
        )
        .unwrap();
        assert_eq!(
            multiple_clocks.phase_counts(),
            MountedTransitionPhaseCounts {
                predecessor_authentication_count: 1,
                predecessor_decode_count: 0,
                predecessor_rebuilt_field_count: 0,
                retained_neuron_index_entry_count: 0,
                reached_neuron_lookup_count: 4,
                current_cohort_evaluation_count: 2,
                successor_seal_count: 1,
            }
        );
    }

    #[test]
    fn resident_recurrence_restores_once_and_prepares_ten_thousand_exact_successors() {
        const MAX_BYTES: usize = 8_388_608;
        const SUCCESSOR_COUNT: usize = 10_000;

        let genesis_source = test_source("resident-genesis");
        let genesis =
            transition_mounted_joint_dsf(&[], &genesis_source, MAX_BYTES, MAX_BYTES).unwrap();
        let genesis_bytes = genesis.state_bytes().to_vec();
        let recurrent_source = test_source("resident-recurrence");

        let stateless_successor =
            transition_mounted_joint_dsf(&genesis_bytes, &recurrent_source, MAX_BYTES, MAX_BYTES)
                .unwrap();
        let (mut resident, cold_summary) =
            restore_resident_mounted_state(&genesis_bytes, MAX_BYTES, MAX_BYTES).unwrap();
        assert_eq!(cold_summary, resident.summary());
        assert_eq!(
            resident.cold_restore_work(),
            ResidentMountedRestoreWork {
                authentication_count: 1,
                decode_count: 1,
                rebuilt_predecessor_field_count: 1,
            }
        );

        let predecessor_bytes = encode_state(&resident.state).unwrap();
        let predecessor_summary = resident.summary();
        let discarded =
            prepare_resident_mounted_generation(&resident, &recurrent_source, MAX_BYTES, MAX_BYTES)
                .unwrap();
        assert_eq!(discarded.state_bytes(), stateless_successor.state_bytes());
        assert_eq!(discarded.transition(), stateless_successor.transition());
        drop(discarded);
        assert_eq!(encode_state(&resident.state).unwrap(), predecessor_bytes);
        assert_eq!(resident.summary(), predecessor_summary);

        let mut final_bytes = genesis_bytes;
        let mut current_cohort_evaluation_count = 0usize;
        for successor_index in 0..SUCCESSOR_COUNT {
            let prepared = prepare_resident_mounted_generation(
                &resident,
                &recurrent_source,
                MAX_BYTES,
                MAX_BYTES,
            )
            .unwrap();
            assert_eq!(
                prepared.restore_validation_cost(),
                MountedRestoreValidationCost {
                    rebuilt_predecessor_field_count: 0,
                }
            );
            assert_eq!(
                prepared.phase_counts(),
                MountedTransitionPhaseCounts {
                    predecessor_authentication_count: 0,
                    predecessor_decode_count: 0,
                    predecessor_rebuilt_field_count: 0,
                    retained_neuron_index_entry_count: 2,
                    reached_neuron_lookup_count: 2,
                    current_cohort_evaluation_count: 1,
                    successor_seal_count: 1,
                }
            );
            assert_eq!(
                prepared.successor_generation(),
                u64::try_from(successor_index).unwrap() + 2
            );
            current_cohort_evaluation_count +=
                prepared.phase_counts().current_cohort_evaluation_count;
            let (successor, state_bytes, transition) = prepared.into_resident_parts();
            assert_eq!(transition.l0_l4_evaluation_count, 1);
            assert_eq!(
                successor.cold_restore_work(),
                ResidentMountedRestoreWork {
                    authentication_count: 1,
                    decode_count: 1,
                    rebuilt_predecessor_field_count: 1,
                }
            );
            resident = successor;
            final_bytes = state_bytes;
        }
        assert_eq!(current_cohort_evaluation_count, SUCCESSOR_COUNT);

        let final_resident_summary = resident.summary();
        let (cold_final, cold_final_summary) =
            restore_resident_mounted_state(&final_bytes, MAX_BYTES, MAX_BYTES).unwrap();
        assert_eq!(cold_final_summary, final_resident_summary);
        assert_eq!(encode_state(&cold_final.state).unwrap(), final_bytes);
    }

    #[test]
    fn resolution_indexes_retained_neurons_once_and_looks_up_only_reached_neurons() {
        let small_prior = transition_mounted_joint_dsf(
            &[],
            &test_source("small-index-prior"),
            8_388_608,
            8_388_608,
        )
        .unwrap();
        let large_prior = transition_mounted_joint_dsf(
            &[],
            &test_source_with_ports(
                "large-index-prior",
                &[
                    (0, [(1, 0.0), (2, 1.0)]),
                    (1, [(1, 1.0), (2, 0.0)]),
                    (2, [(1, 0.0), (2, 1.0)]),
                    (3, [(1, 1.0), (2, 0.0)]),
                ],
            ),
            8_388_608,
            8_388_608,
        )
        .unwrap();
        let reached_source = test_source("same-two-reached-neurons");
        let small = transition_mounted_joint_dsf(
            small_prior.state_bytes(),
            &reached_source,
            8_388_608,
            8_388_608,
        )
        .unwrap();
        let large = transition_mounted_joint_dsf(
            large_prior.state_bytes(),
            &reached_source,
            8_388_608,
            8_388_608,
        )
        .unwrap();

        assert_eq!(small.phase_counts().retained_neuron_index_entry_count, 2);
        assert_eq!(large.phase_counts().retained_neuron_index_entry_count, 4);
        assert_eq!(small.phase_counts().reached_neuron_lookup_count, 2);
        assert_eq!(large.phase_counts().reached_neuron_lookup_count, 2);
        assert_eq!(small.phase_counts().current_cohort_evaluation_count, 1);
        assert_eq!(large.phase_counts().current_cohort_evaluation_count, 1);
    }
}
