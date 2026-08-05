//! Resident complete-neuron boundary.
//!
//! `GLCOG012` is the current resident complete-neuron carrier. On the first
//! admitted source occurrence it creates and retains exact source-specialized
//! virtual-material neuron cells. Explicit growth-DNA electrical seeds remain
//! unexpressed until their exact source-site cohort is reached, then become the
//! cohort's physical contacts exactly once. It retains at most one bounded
//! in-progress experience and one post-quiescence multi-neuron physical state
//! per cohort, so genuine fractals remain available for later recurrence.
//! A later proper partial cue may admit a physical mosaic only through the
//! complete learned, unlearned-control, and cold-restored recurrence law. The
//! admitted mosaic is retained once at organism scope by stable neuron lineage
//! and stable physical-bond references; cohort-local fluid, electrical, and
//! recovery state remains separate. It
//! never infers contacts or claims cognition merely from a seed, DSF delivery,
//! or three retained fractals.

use crate::complete_neuron::{
    sparse_physical_state_delta, DnaExpressionContact, GateWorkOccurrence, NeuronIntervalInput,
    RecoveryContact, SparsePhysicalStateDelta,
};
use crate::developmental_electrical_anatomy::{
    DevelopmentalElectricalError, DevelopmentalElectricalSeed,
};
#[cfg(test)]
use crate::hippocampal_sparse_path::HippocampalColdStore;
use crate::hippocampal_sparse_path::{
    publish_hippocampal_admission, resolve_hippocampal_episode, validate_hippocampal_checkpoint,
    EpisodeParticipant, HippocampalAdmissionEnvelope, HippocampalColdPort, HippocampalError,
    HippocampalTraversalEnvelope, PreparedHippocampalAdmission, ResidentHippocampalIndex,
    TypedEpisodeAdmission,
};
use crate::joint_source_episode::NativeJointSourceEpisode;
#[cfg(test)]
use crate::joint_uf_neuron_boundary::prepare_complete_joint_field_admitted_fixture;
use crate::joint_uf_neuron_boundary::{
    bind_neuron_perspective, prepare_complete_joint_field_with_admission, JointNeuronBoundaryError,
};
#[cfg(test)]
use crate::joint_uf_source_adapter::admitted_fixture_episode;
use crate::joint_uf_source_adapter::{AdmittedJointSourceEpisode, JointUfSourceError};
use crate::neuron_source_anchor::{
    bind_neuron_source_anchor, encode_neuron_source_site, NeuronSourceSite,
};
use crate::optical_receptor_work::{
    derive_optical_receptor_work, OpticalReceptorAnatomy, OpticalReceptorWorkError,
    RETINAL_REFERENCE_IRRADIANCE_UNIT, RETINAL_SPECTRAL_IRRADIANCE_QUANTITY,
};
use crate::physical_mosaic::{
    admit_physical_mosaic, decode_admitted_physical_mosaic, encode_admitted_physical_mosaic,
    AdmittedPhysicalMosaic, PhysicalMosaicCodecError, PhysicalMosaicError,
};
use crate::reached_neuron_cohort::{
    decode_reached_cohort_cell, decode_reached_cohort_state, encode_reached_cohort_cell,
    encode_reached_cohort_state, extend_reached_cohort_state_with_genesis,
    settle_reached_cohort_interval, QuiescentReachedCohortState, ReachedCohortAnatomy,
    ReachedCohortError, ReachedCohortIntervalInput, ReachedCohortPostExperienceSettlement,
    ReachedCohortRecurrenceSettlement, ReachedCohortState,
};
use crate::resident_receptor_transition::ResidentVestibularIngress;
use crate::sha256::sha256;
use crate::sparse_electrical_contact::SparseElectricalAnatomy;
use crate::vestibular_neuron_path::{
    create_single_vertex_vestibular_reached_cohort, FunctionalVestibularError,
};
use crate::virtual_material_neuron_genesis::{
    create_virtual_material_reached_cohort_from_shared,
    extend_virtual_material_reached_cohort_from_shared, VirtualMaterialGenesisError,
};
use crate::virtual_vestibular_canal::WORLD_MECHANICAL_TICK_MICROSECONDS;
use num_bigint::BigInt;
use num_rational::BigRational;
use std::fmt;

const MAGIC: &[u8; 8] = b"GLCOG012";
const VERSION: u16 = 12;
const LINEAGE_DOMAIN: &[u8; 8] = b"GLNLINE1";
const HIPPOCAMPAL_CHECKPOINT_BYTES: usize = 8 + 33 + 33;
const FIXED_BYTES: usize = MAGIC.len()
    + std::mem::size_of::<u16>()
    + 8
    + 8
    + 8
    + 8
    + 8
    + 8
    + 8
    + HIPPOCAMPAL_CHECKPOINT_BYTES;
const EXPERIENCE_MAGIC: &[u8; 8] = b"GLEXP01\0";
const RECURRENCE_MAGIC: &[u8; 8] = b"GLREC02\0";
const HIPPOCAMPAL_RECURRENCE_MAGIC: &[u8; 8] = b"GLHRE01\0";

#[cfg(test)]
std::thread_local! {
    static RESIDENT_ACTUAL_RECURRENCE_SETTLEMENTS: std::cell::Cell<usize> = const {
        std::cell::Cell::new(0)
    };
    static RESIDENT_JOINT_FIELD_EVALUATIONS: std::cell::Cell<usize> = const {
        std::cell::Cell::new(0)
    };
}

#[cfg(test)]
pub(crate) fn reset_resident_joint_field_evaluation_count() {
    RESIDENT_JOINT_FIELD_EVALUATIONS.with(|count| count.set(0));
}

#[cfg(test)]
pub(crate) fn resident_joint_field_evaluation_count() -> usize {
    RESIDENT_JOINT_FIELD_EVALUATIONS.with(std::cell::Cell::get)
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) struct CognitiveFormationObservation {
    pub(crate) cognitive_ordinal: u64,
    pub(crate) trace_formed: bool,
    pub(crate) mosaic_formed: Option<[u8; 32]>,
    pub(crate) activations: Vec<FormationActivation>,
    pub(crate) trace_count: usize,
    pub(crate) mosaic_count: usize,
    pub(crate) dsf_delivery_count: usize,
    pub(crate) complete_neuron_count: usize,
    pub(crate) physically_transitioned_neuron_count: usize,
    pub(crate) complete_neuron_fractal_count: usize,
    pub(crate) emitted_neuron_fractals: Vec<EmittedNeuronFractal>,
    pub(crate) partial_cue_reassembly_count: usize,
    pub(crate) dynamic_formation_relation_count: usize,
    pub(crate) dynamic_linear_formation_count: usize,
    pub(crate) dynamic_web_formation_count: usize,
    pub(crate) dynamic_formation_prior_count: usize,
    pub(crate) dynamic_formation_active_bond_count: usize,
    pub(crate) tapestry_activity_count: usize,
    pub(crate) deeper_tapestry_activity_count: usize,
    pub(crate) generative_recombination_count: usize,
}

impl CognitiveFormationObservation {
    pub(crate) fn partial_cue_reassembly_count(&self) -> usize {
        self.partial_cue_reassembly_count
    }
}

#[derive(Clone, Copy, Debug, Default, Eq, PartialEq)]
struct DynamicFormationObservation {
    relation_count: usize,
    linear_count: usize,
    web_count: usize,
    prior_count: usize,
    active_bond_count: usize,
    tapestry_activity_count: usize,
    deeper_tapestry_activity_count: usize,
    generative_recombination_count: usize,
}

fn observe_dynamic_formation(
    anatomy: &ReachedCohortAnatomy,
    episode: &TypedEpisodeAdmission,
    newly_formed_mosaic: bool,
    hippocampal: &ResidentHippocampalIndex,
    cold: &dyn HippocampalColdPort,
    max_decoded_bytes: usize,
) -> Result<DynamicFormationObservation, FormationError> {
    if hippocampal.checkpoint().root().is_none() {
        return Ok(DynamicFormationObservation::default());
    }
    let mosaic = decode_admitted_physical_mosaic(
        anatomy,
        &episode.physical_mosaic,
        episode.physical_mosaic.len(),
    )
    .map_err(FormationError::PhysicalMosaicCodecUnavailable)?;
    let mut prior_addresses: [Vec<[u8; 32]>; 4] = std::array::from_fn(|_| Vec::new());
    let mut layer_participants = [0usize; 4];
    for layer in &mut prior_addresses {
        layer
            .try_reserve_exact(episode.participants.len())
            .map_err(|_| FormationError::ArithmeticOverflow)?;
    }
    for participant in episode.participants.iter() {
        let page = hippocampal
            .navigate(
                cold,
                participant.lineage,
                None,
                HippocampalTraversalEnvelope {
                    max_postings: 4,
                    max_decoded_bytes,
                },
            )
            .map_err(FormationError::HippocampalUnavailable)?;
        for (layer_index, posting) in page.postings.iter().enumerate() {
            layer_participants[layer_index] = layer_participants[layer_index]
                .checked_add(1)
                .ok_or(FormationError::ArithmeticOverflow)?;
            if !prior_addresses[layer_index].contains(&posting.episode_address) {
                prior_addresses[layer_index].push(posting.episode_address);
            }
        }
    }
    let mut prior_layers: [Vec<Box<[u8]>>; 4] = std::array::from_fn(|_| Vec::new());
    for (addresses, layer) in prior_addresses.iter().zip(&mut prior_layers) {
        for address in addresses {
            let prior = resolve_hippocampal_episode(cold, *address)
                .map_err(FormationError::HippocampalUnavailable)?;
            let prior_mosaic = decode_admitted_physical_mosaic(
                anatomy,
                &prior.physical_mosaic,
                prior.physical_mosaic.len(),
            )
            .map_err(FormationError::PhysicalMosaicCodecUnavailable)?;
            if mosaics_share_active_bond(&mosaic, &prior_mosaic)
                && !layer
                    .iter()
                    .any(|body| body.as_ref() == prior.physical_mosaic.as_ref())
            {
                layer.push(prior.physical_mosaic);
            }
        }
    }
    let (
        relation_count,
        tapestry_activity_count,
        deeper_tapestry_activity_count,
        generative_recombination_count,
    ) = classify_temporal_reassembly(
        newly_formed_mosaic,
        &episode.physical_mosaic,
        &prior_layers,
        layer_participants,
        episode.participants.len(),
    );
    if relation_count == 0 && tapestry_activity_count == 0 && deeper_tapestry_activity_count == 0 {
        return Ok(DynamicFormationObservation::default());
    }
    let (active_bond_count, linear) =
        classify_dynamic_topology(mosaic.member_lineages(), mosaic.recurrence_bonds())?;
    Ok(DynamicFormationObservation {
        relation_count,
        linear_count: relation_count * usize::from(linear),
        web_count: relation_count * usize::from(!linear),
        prior_count: prior_layers.iter().map(Vec::len).sum(),
        active_bond_count,
        tapestry_activity_count,
        deeper_tapestry_activity_count,
        generative_recombination_count,
    })
}

fn classify_temporal_reassembly(
    newly_formed_mosaic: bool,
    current_mosaic: &[u8],
    prior_layers: &[Vec<Box<[u8]>>; 4],
    layer_participants: [usize; 4],
    current_participants: usize,
) -> (usize, usize, usize, usize) {
    let mut prior_current_occurrences = 0usize;
    for (index, layer) in prior_layers.iter().enumerate() {
        if layer_participants[index] == current_participants
            && layer.len() == 1
            && layer[0].as_ref() == current_mosaic
        {
            prior_current_occurrences += 1;
        }
    }
    let mut supports: Vec<&[u8]> = Vec::new();
    for layer in prior_layers {
        for body in layer {
            if body.as_ref() != current_mosaic
                && !supports.iter().any(|prior| *prior == body.as_ref())
            {
                supports.push(body);
            }
        }
    }
    let relation = usize::from(newly_formed_mosaic && supports.len() >= 2);
    let tapestry =
        usize::from(!newly_formed_mosaic && prior_current_occurrences == 1 && supports.len() >= 2);
    let deeper =
        usize::from(!newly_formed_mosaic && prior_current_occurrences >= 2 && supports.len() >= 2);
    let recurrent_supports = supports
        .iter()
        .filter(|support| {
            prior_layers
                .iter()
                .enumerate()
                .filter(|(index, layer)| {
                    layer_participants[*index] == current_participants
                        && layer.iter().any(|body| body.as_ref() == **support)
                })
                .count()
                >= 2
        })
        .count();
    let generative = usize::from(newly_formed_mosaic && recurrent_supports >= 2);
    (relation, tapestry, deeper, generative)
}

fn mosaics_share_active_bond(
    current: &AdmittedPhysicalMosaic,
    prior: &AdmittedPhysicalMosaic,
) -> bool {
    current
        .recurrence_bonds()
        .iter()
        .any(|contact| prior.recurrence_bonds().binary_search(contact).is_ok())
}

fn classify_dynamic_topology(
    members: &[[u8; 16]],
    active_bonds: &[crate::physical_mosaic::StablePhysicalBondReference],
) -> Result<(usize, bool), FormationError> {
    let mut degree = vec![0usize; members.len()];
    let mut active_bond_count = 0usize;
    for bond in active_bonds {
        let (left, right) = bond.endpoints();
        let left = members
            .binary_search(&left)
            .map_err(|_| FormationError::NoncanonicalState)?;
        let right = members
            .binary_search(&right)
            .map_err(|_| FormationError::NoncanonicalState)?;
        degree[left] = degree[left]
            .checked_add(1)
            .ok_or(FormationError::ArithmeticOverflow)?;
        degree[right] = degree[right]
            .checked_add(1)
            .ok_or(FormationError::ArithmeticOverflow)?;
        active_bond_count = active_bond_count
            .checked_add(1)
            .ok_or(FormationError::ArithmeticOverflow)?;
    }
    let linear = active_bond_count.checked_add(1) == Some(members.len())
        && degree.iter().all(|value| *value <= 2);
    Ok((active_bond_count, linear))
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) struct FormationActivation;

#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) struct EmittedNeuronFractal {
    pub(crate) neuron_lineage: [u8; 16],
    pub(crate) delta: SparsePhysicalStateDelta,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) struct CognitiveFormationSummary {
    pub(crate) cognitive_ordinal: u64,
    pub(crate) trace_count: usize,
    pub(crate) mosaic_count: usize,
    pub(crate) complete_neuron_count: usize,
}

#[derive(Clone, Debug, Eq, PartialEq)]
struct ResidentReachedCohort {
    anatomy: ReachedCohortAnatomy,
    state: ReachedCohortState,
    pending_experience: Option<ResidentExperienceEvidence>,
    retained_experience: Option<ResidentExperienceEvidence>,
    pending_recurrence: Option<ResidentRecurrenceEvidence>,
}

#[derive(Clone, Debug, Eq, PartialEq)]
struct ResidentExperienceEvidence {
    pre_experience_quiescent: ReachedCohortState,
    post_experience_quiescent: Option<ReachedCohortState>,
    gate_work_perturbed_neurons: Box<[bool]>,
    active_electrical_contacts: Box<[bool]>,
}

#[derive(Clone, Debug, Eq, PartialEq)]
struct ResidentRecurrenceEvidence {
    gate_work_perturbed_neurons: Box<[bool]>,
    active_recurrence_contacts: Box<[bool]>,
}

#[derive(Clone, Debug, Eq, Ord, PartialEq, PartialOrd)]
pub(crate) struct DormantLineageSeed {
    sense: u8,
    topology_index: u32,
    sensor_id: Box<str>,
    substream_id: Box<str>,
    neuron_lineage: [u8; 16],
}

impl DormantLineageSeed {
    pub(crate) fn new(
        sense: u8,
        topology_index: u32,
        sensor_id: &str,
        substream_id: &str,
        neuron_lineage: [u8; 16],
    ) -> Result<Self, FormationError> {
        let seed = Self {
            sense,
            topology_index,
            sensor_id: sensor_id.into(),
            substream_id: substream_id.into(),
            neuron_lineage,
        };
        seed.validate()?;
        Ok(seed)
    }

    fn from_port(
        port: &crate::joint_source_episode::JointSourcePortView,
        neuron_lineage: [u8; 16],
    ) -> Result<Self, FormationError> {
        Self::new(
            port.sense,
            port.topology_index,
            &port.sensor_id,
            &port.substream_id,
            neuron_lineage,
        )
    }

    fn from_site(
        site: &NeuronSourceSite,
        neuron_lineage: [u8; 16],
    ) -> Result<Self, FormationError> {
        let encoded = encode_neuron_source_site(site).map_err(|error| {
            FormationError::PhysicalGenesisUnavailable(VirtualMaterialGenesisError::Source(error))
        })?;
        let mut cursor = 8usize;
        let sense = *encoded
            .get(cursor)
            .ok_or(FormationError::NoncanonicalState)?;
        cursor += 1;
        let topology_end = cursor
            .checked_add(4)
            .ok_or(FormationError::ArithmeticOverflow)?;
        let topology_index = u32::from_le_bytes(
            encoded
                .get(cursor..topology_end)
                .ok_or(FormationError::NoncanonicalState)?
                .try_into()
                .map_err(|_| FormationError::NoncanonicalState)?,
        );
        cursor = topology_end;
        let sensor_id = take_seed_text(&encoded, &mut cursor)?;
        let substream_id = take_seed_text(&encoded, &mut cursor)?;
        Self::new(
            sense,
            topology_index,
            &sensor_id,
            &substream_id,
            neuron_lineage,
        )
    }

    fn same_source(&self, other: &Self) -> bool {
        self.sense == other.sense
            && self.topology_index == other.topology_index
            && self.sensor_id == other.sensor_id
            && self.substream_id == other.substream_id
    }

    fn matches_port(&self, port: &crate::joint_source_episode::JointSourcePortView) -> bool {
        self.sense == port.sense
            && self.topology_index == port.topology_index
            && self.sensor_id.as_ref() == port.sensor_id
            && self.substream_id.as_ref() == port.substream_id
    }

    fn validate(&self) -> Result<(), FormationError> {
        if self.sense > 5
            || self.sensor_id.is_empty()
            || self.substream_id.is_empty()
            || !valid_local_lineage(self.neuron_lineage)
        {
            return Err(FormationError::NoncanonicalState);
        }
        Ok(())
    }

    pub(crate) fn lineage(&self) -> [u8; 16] {
        self.neuron_lineage
    }
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) struct ResidentCognitiveFormationState {
    generation: u64,
    next_lineage_ordinal: u64,
    unexpressed_electrical_seeds: Box<[DevelopmentalElectricalSeed]>,
    dormant_lineage_seeds: Box<[DormantLineageSeed]>,
    cohorts: Box<[ResidentReachedCohort]>,
    mosaics: Box<[AdmittedPhysicalMosaic]>,
    hippocampal: ResidentHippocampalIndex,
}

impl Default for ResidentCognitiveFormationState {
    fn default() -> Self {
        Self {
            generation: 0,
            next_lineage_ordinal: 1,
            unexpressed_electrical_seeds: Box::new([]),
            dormant_lineage_seeds: Box::new([]),
            cohorts: Box::new([]),
            mosaics: Box::new([]),
            hippocampal: ResidentHippocampalIndex::default(),
        }
    }
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) struct PreparedCognitiveFormationTransition {
    predecessor: ResidentCognitiveFormationState,
    successor: ResidentCognitiveFormationState,
    observation: CognitiveFormationObservation,
    hippocampal_admission: Option<PreparedHippocampalAdmission>,
    hippocampal_published: bool,
}

impl PreparedCognitiveFormationTransition {
    pub(crate) fn observation(&self) -> &CognitiveFormationObservation {
        &self.observation
    }

    #[cfg(test)]
    pub(crate) fn requires_hippocampal_publication(&self) -> bool {
        self.hippocampal_admission.is_some()
    }

    pub(crate) fn try_into_successor(
        self,
        predecessor: &ResidentCognitiveFormationState,
    ) -> Result<
        (
            ResidentCognitiveFormationState,
            CognitiveFormationObservation,
        ),
        (FormationError, Self),
    > {
        if predecessor != &self.predecessor {
            return Err((FormationError::PreparedPredecessorChanged, self));
        }
        if self.hippocampal_admission.is_some() || !self.hippocampal_published {
            return Err((FormationError::HippocampalPublicationRequired, self));
        }
        Ok((self.successor, self.observation))
    }
}

fn encode_organism_mosaic(
    cohorts: &[ResidentReachedCohort],
    mosaic: &AdmittedPhysicalMosaic,
    max_encoded_bytes: usize,
) -> Result<Vec<u8>, FormationError> {
    let mut encoded = None;
    for cohort in cohorts {
        if let Ok(candidate) =
            encode_admitted_physical_mosaic(&cohort.anatomy, mosaic, max_encoded_bytes)
        {
            if encoded.is_some() {
                return Err(FormationError::NoncanonicalState);
            }
            encoded = Some(candidate);
        }
    }
    encoded.ok_or(FormationError::NoncanonicalState)
}

fn decode_organism_mosaic(
    cohorts: &[ResidentReachedCohort],
    encoded: &[u8],
    max_encoded_bytes: usize,
) -> Result<AdmittedPhysicalMosaic, FormationError> {
    let mut decoded = None;
    for cohort in cohorts {
        if let Ok(candidate) =
            decode_admitted_physical_mosaic(&cohort.anatomy, encoded, max_encoded_bytes)
        {
            if decoded.is_some() {
                return Err(FormationError::NoncanonicalState);
            }
            decoded = Some(candidate);
        }
    }
    decoded.ok_or(FormationError::NoncanonicalState)
}

impl ResidentCognitiveFormationState {
    pub(crate) fn from_developmental_electrical_seeds(
        seeds: Vec<DevelopmentalElectricalSeed>,
    ) -> Result<Self, FormationError> {
        Self::from_genesis_parts(0, 1, seeds, Vec::new())
    }

    pub(crate) fn from_genesis_parts(
        generation: u64,
        next_lineage_ordinal: u64,
        seeds: Vec<DevelopmentalElectricalSeed>,
        mut dormant_lineage_seeds: Vec<DormantLineageSeed>,
    ) -> Result<Self, FormationError> {
        if seeds.iter().enumerate().any(|(index, seed)| {
            seeds[..index]
                .iter()
                .any(|prior| prior.source_sites() == seed.source_sites())
        }) {
            return Err(FormationError::DuplicateDevelopmentalSeed);
        }
        dormant_lineage_seeds.sort();
        if dormant_lineage_seeds
            .iter()
            .enumerate()
            .any(|(index, seed)| {
                seed.validate().is_err()
                    || dormant_lineage_seeds[..index].iter().any(|prior| {
                        prior.same_source(seed) || prior.neuron_lineage == seed.neuron_lineage
                    })
            })
        {
            return Err(FormationError::NoncanonicalState);
        }
        let state = Self {
            generation,
            next_lineage_ordinal,
            unexpressed_electrical_seeds: seeds.into_boxed_slice(),
            dormant_lineage_seeds: dormant_lineage_seeds.into_boxed_slice(),
            cohorts: Box::new([]),
            mosaics: Box::new([]),
            hippocampal: ResidentHippocampalIndex::default(),
        };
        validate_lineage_state(&state)?;
        Ok(state)
    }

    pub(crate) fn summary(&self) -> CognitiveFormationSummary {
        CognitiveFormationSummary {
            cognitive_ordinal: self.generation,
            trace_count: 0,
            mosaic_count: self.mosaics.len(),
            complete_neuron_count: self
                .cohorts
                .iter()
                .map(|cohort| cohort.anatomy.neuron_count())
                .sum(),
        }
    }

    #[cfg(test)]
    pub(crate) fn retained_neuron_lineages(&self) -> Vec<[u8; 16]> {
        self.cohorts
            .iter()
            .flat_map(|cohort| cohort.anatomy.neuron_lineages().iter().copied())
            .collect()
    }

    #[cfg(test)]
    pub(crate) fn retained_electrical_contact_counts(&self) -> Vec<usize> {
        self.cohorts
            .iter()
            .map(|cohort| cohort.anatomy.contact_count())
            .collect()
    }

    #[cfg(test)]
    pub(crate) fn unexpressed_electrical_seed_count(&self) -> usize {
        self.unexpressed_electrical_seeds.len()
    }

    #[cfg(test)]
    pub(crate) fn prepare(
        &self,
        source: &NativeJointSourceEpisode,
        max_encoded_bytes: usize,
    ) -> Result<PreparedCognitiveFormationTransition, FormationError> {
        if self.hippocampal.checkpoint().root().is_some() {
            return Err(FormationError::HippocampalPublicationRequired);
        }
        self.prepare_admitted_with_hippocampal_cold(
            &admitted_fixture_episode(source),
            &HippocampalColdStore::default(),
            max_encoded_bytes,
        )
    }

    pub(crate) fn prepare_with_hippocampal_cold(
        &self,
        _source: &NativeJointSourceEpisode,
        _hippocampal_cold: &dyn HippocampalColdPort,
        _max_encoded_bytes: usize,
    ) -> Result<PreparedCognitiveFormationTransition, FormationError> {
        Err(FormationError::JointFieldUnavailable(
            JointNeuronBoundaryError::Source(JointUfSourceError::Unavailable(
                "explicit admitted joint source episode is required",
            )),
        ))
    }

    pub(crate) fn prepare_admitted_with_hippocampal_cold(
        &self,
        admitted_source: &AdmittedJointSourceEpisode,
        hippocampal_cold: &dyn HippocampalColdPort,
        max_encoded_bytes: usize,
    ) -> Result<PreparedCognitiveFormationTransition, FormationError> {
        self.prepare_typed_admitted_with_hippocampal_cold(
            admitted_source,
            None,
            hippocampal_cold,
            max_encoded_bytes,
        )
    }

    pub(crate) fn prepare_vestibular_with_hippocampal_cold(
        &self,
        ingress: &ResidentVestibularIngress,
        hippocampal_cold: &dyn HippocampalColdPort,
        max_encoded_bytes: usize,
    ) -> Result<PreparedCognitiveFormationTransition, FormationError> {
        let (source, contacts) = ingress.source().joint_source_with_contacts();
        if source.joint_source_occurrences().len() != 1 || !contacts.is_empty() {
            return Err(FormationError::VestibularUnavailable(
                FunctionalVestibularError::NotIsolatedSingleVertex,
            ));
        }
        let admission = ingress
            .source()
            .joint_uf_source_admission()
            .map_err(|error| {
                FormationError::JointFieldUnavailable(JointNeuronBoundaryError::Source(error))
            })?;
        let admitted_source = AdmittedJointSourceEpisode::new(source.clone(), vec![(0, admission)])
            .map_err(|error| {
                FormationError::JointFieldUnavailable(JointNeuronBoundaryError::Source(error))
            })?;
        self.prepare_typed_admitted_with_hippocampal_cold(
            &admitted_source,
            Some(ingress),
            hippocampal_cold,
            max_encoded_bytes,
        )
    }

    fn prepare_typed_admitted_with_hippocampal_cold(
        &self,
        admitted_source: &AdmittedJointSourceEpisode,
        vestibular: Option<&ResidentVestibularIngress>,
        hippocampal_cold: &dyn HippocampalColdPort,
        max_encoded_bytes: usize,
    ) -> Result<PreparedCognitiveFormationTransition, FormationError> {
        let source = admitted_source.episode();
        if source.joint_source_occurrences().is_empty() {
            return Err(FormationError::SourceOccurrenceAbsent);
        }
        let source_generation = self
            .generation
            .checked_add(1)
            .ok_or(FormationError::InvalidSourceGeneration)?;
        let optical_anatomy = exact_optical_receptor_anatomy()?;
        let mut unexpressed_electrical_seeds = self.unexpressed_electrical_seeds.to_vec();
        let mut dormant_lineage_seeds = self.dormant_lineage_seeds.to_vec();
        let mut next_lineage_ordinal = self.next_lineage_ordinal;
        let mut cohorts = self.cohorts.to_vec();
        let mut mosaics = self.mosaics.to_vec();
        cohorts
            .try_reserve(source.joint_source_occurrences().len())
            .map_err(|_| FormationError::ArithmeticOverflow)?;
        let mut physically_transitioned_neuron_count = 0usize;
        let mut emitted_neuron_fractals = Vec::new();
        let mut mosaic_formed = None;
        let mut hippocampal_admission = None;
        let mut hippocampal = self.hippocampal;
        let mut dsf_delivery_count = 0usize;
        let mut partial_cue_reassembly_count = 0usize;
        let mut dynamic_formation_relation_count = 0usize;
        let mut dynamic_linear_formation_count = 0usize;
        let mut dynamic_web_formation_count = 0usize;
        let mut dynamic_formation_prior_count = 0usize;
        let mut dynamic_formation_active_bond_count = 0usize;
        let mut tapestry_activity_count = 0usize;
        let mut deeper_tapestry_activity_count = 0usize;
        let mut generative_recombination_count = 0usize;
        for (occurrence_index, occurrence) in source.joint_source_occurrences().iter().enumerate() {
            #[cfg(test)]
            RESIDENT_JOINT_FIELD_EVALUATIONS.with(|count| count.set(count.get() + 1));
            let admission = admitted_source
                .admission(occurrence_index)
                .ok_or(FormationError::NoncanonicalState)?;
            let shared =
                prepare_complete_joint_field_with_admission(source, occurrence_index, admission)
                    .map_err(FormationError::JointFieldUnavailable)?;
            if vestibular.is_some()
                && (occurrence_index != 0
                    || shared.vertex_count() != 1
                    || shared.groups().len() != 1
                    || shared.groups()[0].as_slice() != [0])
            {
                return Err(FormationError::VestibularUnavailable(
                    FunctionalVestibularError::NotIsolatedSingleVertex,
                ));
            }
            dsf_delivery_count = dsf_delivery_count
                .checked_add(shared.vertex_count())
                .ok_or(FormationError::ArithmeticOverflow)?;
            let reached_sources = (0..shared.vertex_count())
                .map(|coordinate_index| {
                    let perspective = bind_neuron_perspective(&shared, coordinate_index, 0)
                        .map_err(FormationError::JointFieldUnavailable)?;
                    let anchor =
                        bind_neuron_source_anchor(source, perspective).map_err(|error| {
                            FormationError::PhysicalGenesisUnavailable(
                                VirtualMaterialGenesisError::Source(error),
                            )
                        })?;
                    let port = source
                        .joint_source_ports()
                        .get(anchor.source_port_index())
                        .ok_or(FormationError::NoncanonicalState)?;
                    Ok((NeuronSourceSite::from_anchor(anchor), port))
                })
                .collect::<Result<Vec<_>, FormationError>>()?;
            let reached_source_sites = reached_sources
                .iter()
                .map(|(source_site, _)| source_site.clone())
                .collect::<Vec<_>>();
            if reached_sources
                .iter()
                .enumerate()
                .any(|(index, (_, port))| {
                    reached_sources[..index]
                        .iter()
                        .any(|(_, prior)| same_dormant_source(prior, port))
                })
            {
                return Err(FormationError::NoncanonicalState);
            }
            let overlapping_cohorts = cohorts
                .iter()
                .enumerate()
                .filter(|(_, cohort)| {
                    reached_source_sites.iter().any(|site| {
                        cohort
                            .anatomy
                            .source_sites()
                            .iter()
                            .any(|resident| resident == site)
                    })
                })
                .map(|(index, _)| index)
                .collect::<Vec<_>>();
            let mut cohort_targets: Vec<(usize, ResidentReachedCohort, Vec<usize>)> = Vec::new();
            if overlapping_cohorts.len() > 1 {
                for coordinate_index in 0..reached_source_sites.len() {
                    let site = &reached_source_sites[coordinate_index];
                    let resident_matches = overlapping_cohorts
                        .iter()
                        .copied()
                        .filter(|cohort_index| {
                            cohorts[*cohort_index]
                                .anatomy
                                .source_sites()
                                .iter()
                                .any(|resident| resident == site)
                        })
                        .collect::<Vec<_>>();
                    if resident_matches.len() != 1 {
                        return Err(if resident_matches.is_empty() {
                            FormationError::NeuronLineageAuthorityAbsent
                        } else {
                            FormationError::NeuronLineageAuthorityChanged
                        });
                    }
                    if let Some(target) = cohort_targets
                        .iter_mut()
                        .find(|(index, _, _)| *index == resident_matches[0])
                    {
                        target.2.push(coordinate_index);
                    } else {
                        cohort_targets.push((
                            resident_matches[0],
                            cohorts[resident_matches[0]].clone(),
                            vec![coordinate_index],
                        ));
                    }
                }
            } else {
                let existing_index = overlapping_cohorts.first().copied();
                if !exact_optical_occurrence(source, occurrence)
                    && vestibular.is_none()
                    && existing_index.is_none()
                {
                    continue;
                }
                let mut reached_lineages = Vec::new();
                reached_lineages
                    .try_reserve_exact(reached_sources.len())
                    .map_err(|_| FormationError::ArithmeticOverflow)?;
                for (_, port) in &reached_sources {
                    let lineage =
                        match resolve_lineage_for_port(&cohorts, &dormant_lineage_seeds, port)? {
                            Some(lineage) => lineage,
                            None => allocate_local_lineage(&mut next_lineage_ordinal)?,
                        };
                    reached_lineages.push(lineage);
                }
                let cohort = if let Some(index) = existing_index {
                    let additions = reached_source_sites
                        .iter()
                        .zip(reached_lineages.iter())
                        .enumerate()
                        .filter_map(|(coordinate_index, (site, lineage))| {
                            (!cohorts[index]
                                .anatomy
                                .source_sites()
                                .iter()
                                .any(|resident| resident == site))
                            .then_some((coordinate_index, *lineage))
                        })
                        .collect::<Vec<_>>();
                    let mut resident = cohorts[index].clone();
                    if let Some(ingress) = vestibular {
                        if !additions.is_empty() || reached_lineages.len() != 1 {
                            return Err(FormationError::VestibularUnavailable(
                                FunctionalVestibularError::NotIsolatedSingleVertex,
                            ));
                        }
                        let expected = create_single_vertex_vestibular_reached_cohort(
                            ingress.receptor_anatomy(),
                            ingress.source(),
                            &shared,
                            reached_lineages[0],
                        )
                        .map_err(FormationError::VestibularUnavailable)?;
                        if resident.anatomy != expected.anatomy {
                            return Err(FormationError::VestibularUnavailable(
                                FunctionalVestibularError::ReachedAnatomyMismatch,
                            ));
                        }
                    }
                    if !additions.is_empty() {
                        let old_anatomy = resident.anatomy.clone();
                        let old_neuron_count = old_anatomy.neuron_count();
                        let (extended_anatomy, extended_state) =
                            extend_virtual_material_reached_cohort_from_shared(
                                source,
                                &shared,
                                &resident.anatomy,
                                &resident.state,
                                &additions,
                            )
                            .map_err(FormationError::PhysicalGenesisUnavailable)?;
                        extend_resident_cohort_evidence(
                            &mut resident,
                            &old_anatomy,
                            extended_anatomy,
                            extended_state,
                            old_neuron_count,
                        )?;
                        dormant_lineage_seeds.retain(|seed| {
                            !reached_sources
                                .iter()
                                .any(|(_, port)| seed.matches_port(port))
                        });
                    }
                    if reached_source_sites
                        .iter()
                        .zip(reached_lineages.iter())
                        .any(|(site, lineage)| {
                            resident
                                .anatomy
                                .source_sites()
                                .iter()
                                .position(|resident_site| resident_site == site)
                                .is_none_or(|resident_index| {
                                    resident.anatomy.neuron_lineages()[resident_index] != *lineage
                                })
                        })
                    {
                        return Err(FormationError::NeuronLineageAuthorityChanged);
                    }
                    resident
                } else {
                    let seed_index = unexpressed_electrical_seeds
                        .iter()
                        .position(|seed| seed.source_sites() == reached_source_sites);
                    let electrical = match seed_index {
                        Some(index) => unexpressed_electrical_seeds[index]
                            .resolve(&reached_source_sites)
                            .map_err(FormationError::DevelopmentalElectricalUnavailable)?,
                        None => {
                            SparseElectricalAnatomy::new(reached_source_sites.len(), Vec::new())
                                .map_err(|error| {
                                    FormationError::PhysicalGenesisUnavailable(
                                        VirtualMaterialGenesisError::Electrical(error),
                                    )
                                })?
                        }
                    };
                    let genesis = if let Some(ingress) = vestibular {
                        if electrical.contact_count() != 0 || reached_lineages.len() != 1 {
                            return Err(FormationError::VestibularUnavailable(
                                FunctionalVestibularError::NotIsolatedSingleVertex,
                            ));
                        }
                        create_single_vertex_vestibular_reached_cohort(
                            ingress.receptor_anatomy(),
                            ingress.source(),
                            &shared,
                            reached_lineages[0],
                        )
                        .map_err(FormationError::VestibularUnavailable)?
                    } else {
                        create_virtual_material_reached_cohort_from_shared(
                            source,
                            &shared,
                            reached_lineages,
                            electrical,
                        )
                        .map_err(FormationError::PhysicalGenesisUnavailable)?
                    };
                    if let Some(index) = seed_index {
                        unexpressed_electrical_seeds.remove(index);
                    }
                    dormant_lineage_seeds.retain(|seed| {
                        !reached_sources
                            .iter()
                            .any(|(_, port)| seed.matches_port(port))
                    });
                    ResidentReachedCohort {
                        anatomy: genesis.anatomy,
                        state: genesis.state,
                        pending_experience: None,
                        retained_experience: None,
                        pending_recurrence: None,
                    }
                };
                cohort_targets.push((
                    existing_index.unwrap_or(cohorts.len()),
                    cohort,
                    (0..shared.vertex_count()).collect(),
                ));
            }
            for (cohort_index, mut cohort, coordinate_indices) in cohort_targets {
                let optical_occurrence = exact_optical_occurrence(source, occurrence);
                if optical_occurrence || vestibular.is_some() {
                    let catalysts = cohort
                        .anatomy
                        .neuron_anatomies()
                        .iter()
                        .map(|anatomy| {
                            vec![0; anatomy.recovery_anatomy().psi_lane_count()].into_boxed_slice()
                        })
                        .collect::<Vec<Box<[u128]>>>();
                    let mut inputs = Vec::new();
                    inputs
                        .try_reserve_exact(coordinate_indices.len())
                        .map_err(|_| FormationError::ArithmeticOverflow)?;
                    for coordinate_index in coordinate_indices {
                        let perspective = bind_neuron_perspective(&shared, coordinate_index, 0)
                            .map_err(FormationError::JointFieldUnavailable)?;
                        let (gate_work, interval_microseconds) = if let Some(ingress) = vestibular {
                            if coordinate_index != 0 {
                                return Err(FormationError::VestibularUnavailable(
                                    FunctionalVestibularError::NotIsolatedSingleVertex,
                                ));
                            }
                            (
                                GateWorkOccurrence::new(
                                    ingress.transduction().gate_work_zeptojoules.clone(),
                                ),
                                ingress.transduction().reached_tick.interval_microseconds,
                            )
                        } else {
                            let receptor =
                                derive_optical_receptor_work(source, perspective, &optical_anatomy)
                                    .map_err(FormationError::OpticalWorkUnavailable)?;
                            (receptor.gate_work, WORLD_MECHANICAL_TICK_MICROSECONDS)
                        };
                        let resident_index = cohort
                            .anatomy
                            .source_sites()
                            .iter()
                            .position(|resident| {
                                resident == &reached_source_sites[coordinate_index]
                            })
                            .ok_or(FormationError::NeuronLineageAuthorityAbsent)?;
                        inputs.push(NeuronIntervalInput {
                            perspective,
                            gate_work,
                            interval_microseconds,
                            recovery: RecoveryContact::new(&catalysts[resident_index], 0, 0),
                            dna_expression: DnaExpressionContact::new(0),
                        });
                    }
                    let input = ReachedCohortIntervalInput::from_episode(source, inputs)
                        .map_err(FormationError::PhysicalSettlementUnavailable)?;
                    let gate_work_perturbed_neurons = input
                        .resident_gate_work_bits(&cohort.anatomy)
                        .map_err(FormationError::PhysicalSettlementUnavailable)?;
                    let outcome = settle_resident_physical_interval(
                        &mut cohort,
                        input,
                        gate_work_perturbed_neurons,
                        &mosaics,
                        max_encoded_bytes,
                        source_generation,
                        source,
                        occurrence_index,
                    )?;
                    let newly_formed_mosaic = outcome.mosaic_formed.is_some();
                    physically_transitioned_neuron_count = physically_transitioned_neuron_count
                        .checked_add(outcome.changed_neurons)
                        .ok_or(FormationError::ArithmeticOverflow)?;
                    emitted_neuron_fractals.extend(outcome.emitted_neuron_fractals);
                    partial_cue_reassembly_count = partial_cue_reassembly_count
                        .checked_add(outcome.partial_cue_reassembly_count)
                        .ok_or(FormationError::ArithmeticOverflow)?;
                    if outcome.mosaic_formed.is_some() {
                        mosaic_formed = outcome.mosaic_formed;
                    }
                    if let Some(admitted) = outcome.admitted_mosaic {
                        mosaics.push(admitted);
                    }
                    if let Some(episode) = outcome.hippocampal_episode {
                        if hippocampal_admission.is_some() {
                            return Err(FormationError::MultipleHippocampalAdmissions);
                        }
                        let dynamic = observe_dynamic_formation(
                            &cohort.anatomy,
                            &episode,
                            newly_formed_mosaic,
                            &hippocampal,
                            hippocampal_cold,
                            max_encoded_bytes,
                        )?;
                        dynamic_formation_relation_count = dynamic.relation_count;
                        dynamic_linear_formation_count = dynamic.linear_count;
                        dynamic_web_formation_count = dynamic.web_count;
                        dynamic_formation_prior_count = dynamic.prior_count;
                        dynamic_formation_active_bond_count = dynamic.active_bond_count;
                        tapestry_activity_count = dynamic.tapestry_activity_count;
                        deeper_tapestry_activity_count = dynamic.deeper_tapestry_activity_count;
                        generative_recombination_count = dynamic.generative_recombination_count;
                        let participants = episode.participants.len();
                        let prepared = hippocampal
                            .prepare(
                                hippocampal_cold,
                                &episode,
                                HippocampalAdmissionEnvelope {
                                    max_objects: 1usize
                                        .checked_add(
                                            participants
                                                .checked_mul(33)
                                                .ok_or(FormationError::ArithmeticOverflow)?,
                                        )
                                        .ok_or(FormationError::ArithmeticOverflow)?,
                                    max_object_bytes: max_encoded_bytes,
                                },
                            )
                            .map_err(FormationError::HippocampalUnavailable)?;
                        hippocampal =
                            ResidentHippocampalIndex::from_checkpoint(prepared.successor());
                        if newly_formed_mosaic {
                            mosaic_formed = Some(prepared.episode_address());
                        }
                        hippocampal_admission = Some(prepared);
                    }
                }
                if cohort_index < cohorts.len() {
                    cohorts[cohort_index] = cohort;
                } else {
                    cohorts.push(cohort);
                }
            }
        }
        let successor = Self {
            generation: source_generation,
            next_lineage_ordinal,
            unexpressed_electrical_seeds: unexpressed_electrical_seeds.into_boxed_slice(),
            dormant_lineage_seeds: dormant_lineage_seeds.into_boxed_slice(),
            cohorts: cohorts.into_boxed_slice(),
            mosaics: mosaics.into_boxed_slice(),
            hippocampal,
        };
        successor.encode(max_encoded_bytes)?;
        let summary = successor.summary();
        let complete_neuron_count = summary.complete_neuron_count;
        let complete_neuron_fractal_count = emitted_neuron_fractals.len();
        let hippocampal_published = hippocampal_admission.is_none();
        Ok(PreparedCognitiveFormationTransition {
            predecessor: self.clone(),
            successor,
            observation: CognitiveFormationObservation {
                cognitive_ordinal: source_generation,
                trace_formed: false,
                mosaic_formed,
                activations: Vec::new(),
                trace_count: 0,
                mosaic_count: summary.mosaic_count,
                dsf_delivery_count,
                complete_neuron_count,
                physically_transitioned_neuron_count,
                complete_neuron_fractal_count,
                emitted_neuron_fractals,
                partial_cue_reassembly_count,
                dynamic_formation_relation_count,
                dynamic_linear_formation_count,
                dynamic_web_formation_count,
                dynamic_formation_prior_count,
                dynamic_formation_active_bond_count,
                tapestry_activity_count,
                deeper_tapestry_activity_count,
                generative_recombination_count,
            },
            hippocampal_admission,
            hippocampal_published,
        })
    }

    pub(crate) fn commit(
        &mut self,
        prepared: PreparedCognitiveFormationTransition,
    ) -> Result<CognitiveFormationObservation, FormationError> {
        let (successor, observation) = prepared
            .try_into_successor(self)
            .map_err(|(error, _)| error)?;
        *self = successor;
        Ok(observation)
    }

    pub(crate) fn encode(&self, max_encoded_bytes: usize) -> Result<Vec<u8>, FormationError> {
        validate_lineage_state(self)?;
        let mut seeds = Vec::new();
        seeds
            .try_reserve_exact(self.unexpressed_electrical_seeds.len())
            .map_err(|_| FormationError::ArithmeticOverflow)?;
        let mut cells = Vec::new();
        cells
            .try_reserve_exact(self.cohorts.len())
            .map_err(|_| FormationError::ArithmeticOverflow)?;
        let mut length = FIXED_BYTES;
        for seed in &self.unexpressed_electrical_seeds {
            let encoded = seed
                .encode()
                .map_err(FormationError::DevelopmentalElectricalUnavailable)?;
            length = length
                .checked_add(8)
                .and_then(|value| value.checked_add(encoded.len()))
                .ok_or(FormationError::ArithmeticOverflow)?;
            seeds.push(encoded);
        }
        let mut dormant = Vec::new();
        dormant
            .try_reserve_exact(self.dormant_lineage_seeds.len())
            .map_err(|_| FormationError::ArithmeticOverflow)?;
        for seed in &self.dormant_lineage_seeds {
            let encoded = encode_dormant_lineage_seed(seed)?;
            length = length
                .checked_add(8)
                .and_then(|value| value.checked_add(encoded.len()))
                .ok_or(FormationError::ArithmeticOverflow)?;
            dormant.push(encoded);
        }
        for cohort in &self.cohorts {
            if cohort
                .pending_experience
                .as_ref()
                .is_some_and(|evidence| evidence.post_experience_quiescent.is_some())
                || cohort
                    .retained_experience
                    .as_ref()
                    .is_some_and(|evidence| evidence.post_experience_quiescent.is_none())
                || (cohort.pending_experience.is_some() && cohort.retained_experience.is_some())
                || (cohort.pending_recurrence.is_some()
                    && (cohort.retained_experience.is_none()
                        || cohort.pending_experience.is_some()))
            {
                return Err(FormationError::NoncanonicalState);
            }
            let cell = encode_reached_cohort_cell(&cohort.anatomy, &cohort.state)
                .map_err(|_| FormationError::NoncanonicalState)?;
            let pending = cohort
                .pending_experience
                .as_ref()
                .map(|evidence| encode_experience_evidence(&cohort.anatomy, evidence))
                .transpose()?;
            let retained = cohort
                .retained_experience
                .as_ref()
                .map(|evidence| encode_experience_evidence(&cohort.anatomy, evidence))
                .transpose()?;
            let recurrence = cohort
                .pending_recurrence
                .as_ref()
                .map(|evidence| encode_recurrence_evidence(&cohort.anatomy, evidence))
                .transpose()?;
            if recurrence.is_some() && retained.is_none() {
                return Err(FormationError::NoncanonicalState);
            }
            length = length
                .checked_add(8)
                .and_then(|value| value.checked_add(cell.len()))
                .and_then(|value| value.checked_add(1))
                .and_then(|value| {
                    pending.as_ref().map_or(Some(value), |pending| {
                        value.checked_add(8)?.checked_add(pending.len())
                    })
                })
                .and_then(|value| value.checked_add(1))
                .and_then(|value| {
                    retained.as_ref().map_or(Some(value), |retained| {
                        value.checked_add(8)?.checked_add(retained.len())
                    })
                })
                .and_then(|value| value.checked_add(1))
                .and_then(|value| {
                    recurrence.as_ref().map_or(Some(value), |recurrence| {
                        value.checked_add(8)?.checked_add(recurrence.len())
                    })
                })
                .ok_or(FormationError::ArithmeticOverflow)?;
            cells.push((cell, pending, retained, recurrence));
        }
        if self
            .mosaics
            .iter()
            .enumerate()
            .any(|(index, mosaic)| self.mosaics[..index].contains(mosaic))
        {
            return Err(FormationError::NoncanonicalState);
        }
        let mosaics = self
            .mosaics
            .iter()
            .map(|mosaic| encode_organism_mosaic(&self.cohorts, mosaic, max_encoded_bytes))
            .collect::<Result<Vec<_>, _>>()?;
        length = mosaics
            .iter()
            .try_fold(length, |total, mosaic| {
                total.checked_add(8)?.checked_add(mosaic.len())
            })
            .ok_or(FormationError::ArithmeticOverflow)?;
        if length > max_encoded_bytes {
            return Err(FormationError::BudgetExceeded {
                required: length,
                available: max_encoded_bytes,
            });
        }
        let mut output = Vec::with_capacity(length);
        output.extend_from_slice(MAGIC);
        output.extend_from_slice(&VERSION.to_le_bytes());
        output.extend_from_slice(&self.generation.to_le_bytes());
        output.extend_from_slice(&self.next_lineage_ordinal.to_le_bytes());
        output.extend_from_slice(
            &u64::try_from(seeds.len())
                .map_err(|_| FormationError::ArithmeticOverflow)?
                .to_le_bytes(),
        );
        for seed in seeds {
            output.extend_from_slice(
                &u64::try_from(seed.len())
                    .map_err(|_| FormationError::ArithmeticOverflow)?
                    .to_le_bytes(),
            );
            output.extend_from_slice(&seed);
        }
        output.extend_from_slice(
            &u64::try_from(dormant.len())
                .map_err(|_| FormationError::ArithmeticOverflow)?
                .to_le_bytes(),
        );
        for seed in dormant {
            push_length(&mut output, seed.len())?;
            output.extend_from_slice(&seed);
        }
        output.extend_from_slice(
            &u64::try_from(cells.len())
                .map_err(|_| FormationError::ArithmeticOverflow)?
                .to_le_bytes(),
        );
        for (cell, pending, retained, recurrence) in cells {
            output.extend_from_slice(
                &u64::try_from(cell.len())
                    .map_err(|_| FormationError::ArithmeticOverflow)?
                    .to_le_bytes(),
            );
            output.extend_from_slice(&cell);
            output.push(u8::from(pending.is_some()));
            if let Some(pending) = pending {
                output.extend_from_slice(
                    &u64::try_from(pending.len())
                        .map_err(|_| FormationError::ArithmeticOverflow)?
                        .to_le_bytes(),
                );
                output.extend_from_slice(&pending);
            }
            output.push(u8::from(retained.is_some()));
            if let Some(retained) = retained {
                output.extend_from_slice(
                    &u64::try_from(retained.len())
                        .map_err(|_| FormationError::ArithmeticOverflow)?
                        .to_le_bytes(),
                );
                output.extend_from_slice(&retained);
            }
            output.push(u8::from(recurrence.is_some()));
            if let Some(recurrence) = recurrence {
                push_length(&mut output, recurrence.len())?;
                output.extend_from_slice(&recurrence);
            }
        }
        push_length(&mut output, mosaics.len())?;
        for mosaic in mosaics {
            push_length(&mut output, mosaic.len())?;
            output.extend_from_slice(&mosaic);
        }
        let hippocampal = self
            .hippocampal
            .encode()
            .map_err(FormationError::HippocampalUnavailable)?;
        if hippocampal.len() != HIPPOCAMPAL_CHECKPOINT_BYTES {
            return Err(FormationError::NoncanonicalState);
        }
        push_length(&mut output, hippocampal.len())?;
        output.extend_from_slice(&hippocampal);
        if output.len() != length {
            return Err(FormationError::NoncanonicalState);
        }
        Ok(output)
    }

    pub(crate) fn encode_successor(
        &self,
        prepared: &PreparedCognitiveFormationTransition,
        max_encoded_bytes: usize,
    ) -> Result<Vec<u8>, FormationError> {
        if self != &prepared.predecessor {
            return Err(FormationError::PreparedPredecessorChanged);
        }
        if prepared.hippocampal_admission.is_some() {
            return Err(FormationError::HippocampalPublicationRequired);
        }
        prepared.successor.encode(max_encoded_bytes)
    }

    pub(crate) fn encode_staged_successor(
        &self,
        prepared: &PreparedCognitiveFormationTransition,
        max_encoded_bytes: usize,
    ) -> Result<Vec<u8>, FormationError> {
        if self != &prepared.predecessor {
            return Err(FormationError::PreparedPredecessorChanged);
        }
        match prepared.hippocampal_admission.as_ref() {
            Some(admission)
                if prepared.successor.hippocampal.checkpoint() != admission.successor() =>
            {
                return Err(FormationError::NoncanonicalState);
            }
            Some(_) if prepared.hippocampal_published => {
                return Err(FormationError::NoncanonicalState);
            }
            None if !prepared.hippocampal_published => {
                return Err(FormationError::NoncanonicalState);
            }
            _ => {}
        }
        prepared.successor.encode(max_encoded_bytes)
    }

    pub(crate) fn publish_prepared_hippocampal(
        &self,
        prepared: &mut PreparedCognitiveFormationTransition,
        cold: &mut dyn HippocampalColdPort,
    ) -> Result<(), FormationError> {
        if self != &prepared.predecessor {
            return Err(FormationError::PreparedPredecessorChanged);
        }
        if let Some(admission) = prepared.hippocampal_admission.as_ref() {
            let published = publish_hippocampal_admission(cold, admission)
                .map_err(FormationError::HippocampalUnavailable)?;
            let mut checkpoint = self.hippocampal;
            checkpoint
                .adopt(published)
                .map_err(FormationError::HippocampalUnavailable)?;
            if checkpoint != prepared.successor.hippocampal {
                return Err(FormationError::NoncanonicalState);
            }
            validate_hippocampal_checkpoint(cold, checkpoint.checkpoint())
                .map_err(FormationError::HippocampalUnavailable)?;
            prepared.hippocampal_admission = None;
        }
        prepared.hippocampal_published = true;
        Ok(())
    }

    #[cfg(test)]
    pub(crate) fn publish_hippocampal_and_encode_successor(
        &self,
        prepared: &mut PreparedCognitiveFormationTransition,
        cold: &mut dyn HippocampalColdPort,
        max_encoded_bytes: usize,
    ) -> Result<Vec<u8>, FormationError> {
        self.publish_prepared_hippocampal(prepared, cold)?;
        prepared.successor.encode(max_encoded_bytes)
    }

    pub(crate) fn validate_hippocampal_cold(
        &self,
        cold: &dyn HippocampalColdPort,
    ) -> Result<(), FormationError> {
        validate_hippocampal_checkpoint(cold, self.hippocampal.checkpoint())
            .map_err(FormationError::HippocampalUnavailable)
    }

    pub(crate) fn decode(bytes: &[u8], max_encoded_bytes: usize) -> Result<Self, FormationError> {
        if bytes.len() > max_encoded_bytes {
            return Err(FormationError::BudgetExceeded {
                required: bytes.len(),
                available: max_encoded_bytes,
            });
        }
        if bytes.len() >= MAGIC.len() && &bytes[..MAGIC.len()] != MAGIC {
            return Err(FormationError::RetiredCognitiveState);
        }
        if bytes.len() < FIXED_BYTES {
            return Err(FormationError::NoncanonicalState);
        }
        let mut cursor = MAGIC.len();
        let version = u16::from_le_bytes(
            bytes[cursor..cursor + 2]
                .try_into()
                .map_err(|_| FormationError::NoncanonicalState)?,
        );
        cursor += 2;
        if version != VERSION {
            return Err(FormationError::BadVersion);
        }
        let generation = take_state_u64(bytes, &mut cursor)?;
        let next_lineage_ordinal = take_state_u64(bytes, &mut cursor)?;
        let seed_count = usize::try_from(u64::from_le_bytes(
            bytes[cursor..cursor + 8]
                .try_into()
                .map_err(|_| FormationError::NoncanonicalState)?,
        ))
        .map_err(|_| FormationError::ArithmeticOverflow)?;
        cursor += 8;
        if seed_count > bytes.len().saturating_sub(cursor) / 8 {
            return Err(FormationError::NoncanonicalState);
        }
        let mut unexpressed_electrical_seeds = Vec::new();
        unexpressed_electrical_seeds
            .try_reserve_exact(seed_count)
            .map_err(|_| FormationError::ArithmeticOverflow)?;
        for _ in 0..seed_count {
            let length_end = cursor
                .checked_add(8)
                .ok_or(FormationError::ArithmeticOverflow)?;
            let seed_length = usize::try_from(u64::from_le_bytes(
                bytes
                    .get(cursor..length_end)
                    .ok_or(FormationError::NoncanonicalState)?
                    .try_into()
                    .map_err(|_| FormationError::NoncanonicalState)?,
            ))
            .map_err(|_| FormationError::ArithmeticOverflow)?;
            cursor = length_end;
            let seed_end = cursor
                .checked_add(seed_length)
                .ok_or(FormationError::ArithmeticOverflow)?;
            let seed = DevelopmentalElectricalSeed::decode(
                bytes
                    .get(cursor..seed_end)
                    .ok_or(FormationError::NoncanonicalState)?,
            )
            .map_err(FormationError::DevelopmentalElectricalUnavailable)?;
            cursor = seed_end;
            if unexpressed_electrical_seeds
                .iter()
                .any(|prior: &DevelopmentalElectricalSeed| {
                    prior.source_sites() == seed.source_sites()
                })
            {
                return Err(FormationError::DuplicateDevelopmentalSeed);
            }
            unexpressed_electrical_seeds.push(seed);
        }
        let dormant_count = read_length(bytes, &mut cursor)?;
        if dormant_count > bytes.len().saturating_sub(cursor) / 8 {
            return Err(FormationError::NoncanonicalState);
        }
        let mut dormant_lineage_seeds = Vec::new();
        dormant_lineage_seeds
            .try_reserve_exact(dormant_count)
            .map_err(|_| FormationError::ArithmeticOverflow)?;
        for _ in 0..dormant_count {
            let seed_length = read_length(bytes, &mut cursor)?;
            let seed_end = cursor
                .checked_add(seed_length)
                .ok_or(FormationError::ArithmeticOverflow)?;
            let seed = decode_dormant_lineage_seed(
                bytes
                    .get(cursor..seed_end)
                    .ok_or(FormationError::NoncanonicalState)?,
            )?;
            cursor = seed_end;
            if dormant_lineage_seeds
                .last()
                .is_some_and(|prior| prior >= &seed)
            {
                return Err(FormationError::NoncanonicalState);
            }
            dormant_lineage_seeds.push(seed);
        }
        let cohort_count_end = cursor
            .checked_add(8)
            .ok_or(FormationError::ArithmeticOverflow)?;
        let cohort_count = usize::try_from(u64::from_le_bytes(
            bytes
                .get(cursor..cohort_count_end)
                .ok_or(FormationError::NoncanonicalState)?
                .try_into()
                .map_err(|_| FormationError::NoncanonicalState)?,
        ))
        .map_err(|_| FormationError::ArithmeticOverflow)?;
        cursor = cohort_count_end;
        if cohort_count > bytes.len().saturating_sub(cursor) / 9 {
            return Err(FormationError::NoncanonicalState);
        }
        let mut cohorts = Vec::new();
        cohorts
            .try_reserve_exact(cohort_count)
            .map_err(|_| FormationError::ArithmeticOverflow)?;
        for _ in 0..cohort_count {
            let length_end = cursor
                .checked_add(8)
                .ok_or(FormationError::ArithmeticOverflow)?;
            let cell_length = usize::try_from(u64::from_le_bytes(
                bytes
                    .get(cursor..length_end)
                    .ok_or(FormationError::NoncanonicalState)?
                    .try_into()
                    .map_err(|_| FormationError::NoncanonicalState)?,
            ))
            .map_err(|_| FormationError::ArithmeticOverflow)?;
            cursor = length_end;
            let cell_end = cursor
                .checked_add(cell_length)
                .ok_or(FormationError::ArithmeticOverflow)?;
            let (anatomy, state) = decode_reached_cohort_cell(
                bytes
                    .get(cursor..cell_end)
                    .ok_or(FormationError::NoncanonicalState)?,
            )
            .map_err(|_| FormationError::NoncanonicalState)?;
            cursor = cell_end;
            let pending_experience =
                decode_optional_experience_evidence(bytes, &mut cursor, &anatomy, false)?;
            let retained_experience =
                decode_optional_experience_evidence(bytes, &mut cursor, &anatomy, true)?;
            let pending_recurrence =
                decode_optional_recurrence_evidence(bytes, &mut cursor, &anatomy)?;
            if pending_recurrence.is_some() && retained_experience.is_none() {
                return Err(FormationError::NoncanonicalState);
            }
            if pending_experience.is_some() && retained_experience.is_some()
                || pending_recurrence.is_some()
                    && (retained_experience.is_none() || pending_experience.is_some())
            {
                return Err(FormationError::NoncanonicalState);
            }
            cohorts.push(ResidentReachedCohort {
                anatomy,
                state,
                pending_experience,
                retained_experience,
                pending_recurrence,
            });
        }
        let mosaic_count = read_length(bytes, &mut cursor)?;
        if mosaic_count > bytes.len().saturating_sub(cursor) / 8 {
            return Err(FormationError::NoncanonicalState);
        }
        let mut mosaics = Vec::new();
        mosaics
            .try_reserve_exact(mosaic_count)
            .map_err(|_| FormationError::ArithmeticOverflow)?;
        for _ in 0..mosaic_count {
            let mosaic_length = read_length(bytes, &mut cursor)?;
            let mosaic_end = cursor
                .checked_add(mosaic_length)
                .ok_or(FormationError::ArithmeticOverflow)?;
            let mosaic = decode_organism_mosaic(
                &cohorts,
                bytes
                    .get(cursor..mosaic_end)
                    .ok_or(FormationError::NoncanonicalState)?,
                max_encoded_bytes,
            )?;
            cursor = mosaic_end;
            if mosaics.contains(&mosaic) {
                return Err(FormationError::NoncanonicalState);
            }
            mosaics.push(mosaic);
        }
        let hippocampal_length = read_length(bytes, &mut cursor)?;
        if hippocampal_length != HIPPOCAMPAL_CHECKPOINT_BYTES {
            return Err(FormationError::NoncanonicalState);
        }
        let hippocampal_end = cursor
            .checked_add(hippocampal_length)
            .ok_or(FormationError::ArithmeticOverflow)?;
        let hippocampal = ResidentHippocampalIndex::decode(
            bytes
                .get(cursor..hippocampal_end)
                .ok_or(FormationError::NoncanonicalState)?,
        )
        .map_err(FormationError::HippocampalUnavailable)?;
        cursor = hippocampal_end;
        if cursor != bytes.len() {
            return Err(FormationError::NoncanonicalState);
        }
        let state = Self {
            generation,
            next_lineage_ordinal,
            unexpressed_electrical_seeds: unexpressed_electrical_seeds.into_boxed_slice(),
            dormant_lineage_seeds: dormant_lineage_seeds.into_boxed_slice(),
            cohorts: cohorts.into_boxed_slice(),
            mosaics: mosaics.into_boxed_slice(),
            hippocampal,
        };
        validate_lineage_state(&state)?;
        if state.encode(max_encoded_bytes)? != bytes {
            return Err(FormationError::NoncanonicalState);
        }
        Ok(state)
    }
}

struct ResidentOpticalIntervalOutcome {
    changed_neurons: usize,
    emitted_neuron_fractals: Vec<EmittedNeuronFractal>,
    mosaic_formed: Option<[u8; 32]>,
    admitted_mosaic: Option<AdmittedPhysicalMosaic>,
    hippocampal_episode: Option<TypedEpisodeAdmission>,
    partial_cue_reassembly_count: usize,
}

fn extend_resident_cohort_evidence(
    cohort: &mut ResidentReachedCohort,
    predecessor_anatomy: &ReachedCohortAnatomy,
    successor_anatomy: ReachedCohortAnatomy,
    successor_state: ReachedCohortState,
    predecessor_neuron_count: usize,
) -> Result<(), FormationError> {
    let genesis_states = successor_state
        .neurons()
        .get(predecessor_neuron_count..)
        .ok_or(FormationError::NoncanonicalState)?;
    let extend_experience = |evidence: &mut ResidentExperienceEvidence| {
        evidence.pre_experience_quiescent = extend_reached_cohort_state_with_genesis(
            predecessor_anatomy,
            &evidence.pre_experience_quiescent,
            &successor_anatomy,
            genesis_states,
        )
        .map_err(FormationError::PhysicalSettlementUnavailable)?;
        evidence.post_experience_quiescent = evidence
            .post_experience_quiescent
            .as_ref()
            .map(|state| {
                extend_reached_cohort_state_with_genesis(
                    predecessor_anatomy,
                    state,
                    &successor_anatomy,
                    genesis_states,
                )
                .map_err(FormationError::PhysicalSettlementUnavailable)
            })
            .transpose()?;
        let mut gate_work = evidence.gate_work_perturbed_neurons.to_vec();
        gate_work.resize(successor_anatomy.neuron_count(), false);
        evidence.gate_work_perturbed_neurons = gate_work.into_boxed_slice();
        Ok::<(), FormationError>(())
    };
    if let Some(evidence) = cohort.pending_experience.as_mut() {
        extend_experience(evidence)?;
    }
    if let Some(evidence) = cohort.retained_experience.as_mut() {
        extend_experience(evidence)?;
    }
    if let Some(recurrence) = cohort.pending_recurrence.as_mut() {
        let mut gate_work = recurrence.gate_work_perturbed_neurons.to_vec();
        gate_work.resize(successor_anatomy.neuron_count(), false);
        recurrence.gate_work_perturbed_neurons = gate_work.into_boxed_slice();
    }
    cohort.anatomy = successor_anatomy;
    cohort.state = successor_state;
    Ok(())
}

fn settle_resident_physical_interval(
    cohort: &mut ResidentReachedCohort,
    input: ReachedCohortIntervalInput<'_>,
    gate_work_perturbed_neurons: Vec<bool>,
    existing_mosaics: &[AdmittedPhysicalMosaic],
    max_encoded_bytes: usize,
    source_generation: u64,
    source: &NativeJointSourceEpisode,
    source_occurrence_index: usize,
) -> Result<ResidentOpticalIntervalOutcome, FormationError> {
    if cohort.retained_experience.is_some() {
        settle_resident_recurrence_interval(
            cohort,
            input,
            gate_work_perturbed_neurons,
            existing_mosaics,
            max_encoded_bytes,
            source_generation,
            source,
            source_occurrence_index,
        )
    } else {
        settle_resident_original_interval(cohort, input, gate_work_perturbed_neurons)
    }
}

fn settle_resident_original_interval(
    cohort: &mut ResidentReachedCohort,
    input: ReachedCohortIntervalInput<'_>,
    gate_work_perturbed_neurons: Vec<bool>,
) -> Result<ResidentOpticalIntervalOutcome, FormationError> {
    let predecessor_state = cohort.state.clone();
    let settlement = settle_reached_cohort_interval(&cohort.anatomy, &cohort.state, input)
        .map_err(FormationError::PhysicalSettlementUnavailable)?;
    let changed_neurons = predecessor_state
        .neurons()
        .iter()
        .zip(settlement.successor.neurons())
        .filter(|(predecessor, successor)| predecessor != successor)
        .count();
    let active_electrical_contacts = active_contact_bits(&settlement.contact_transitions);
    let mut experience = cohort.pending_experience.clone().or_else(|| {
        (changed_neurons > 0).then(|| ResidentExperienceEvidence {
            pre_experience_quiescent: predecessor_state,
            post_experience_quiescent: None,
            gate_work_perturbed_neurons: vec![false; cohort.anatomy.neuron_count()]
                .into_boxed_slice(),
            active_electrical_contacts: vec![false; cohort.anatomy.contact_count()]
                .into_boxed_slice(),
        })
    });
    if let Some(experience) = experience.as_mut() {
        or_bits(
            &mut experience.gate_work_perturbed_neurons,
            &gate_work_perturbed_neurons,
        )?;
        or_bits(
            &mut experience.active_electrical_contacts,
            &active_electrical_contacts,
        )?;
    }
    let mut emitted = Vec::new();
    if settlement.quiescent {
        if let Some(mut experience) = experience {
            for (neuron_index, (predecessor, successor)) in experience
                .pre_experience_quiescent
                .neurons()
                .iter()
                .zip(settlement.successor.neurons())
                .enumerate()
            {
                if let Some(delta) =
                    sparse_physical_state_delta(predecessor, successor).map_err(|error| {
                        FormationError::PhysicalSettlementUnavailable(ReachedCohortError::Neuron {
                            neuron_index,
                            error,
                        })
                    })?
                {
                    emitted.push(EmittedNeuronFractal {
                        neuron_lineage: cohort.anatomy.neuron_lineages()[neuron_index],
                        delta,
                    });
                }
            }
            if emitted.len() >= 3 {
                experience.post_experience_quiescent = Some(settlement.successor.clone());
                cohort.retained_experience = Some(experience);
            }
        }
        cohort.pending_experience = None;
    } else {
        cohort.pending_experience = experience;
    }
    cohort.state = settlement.successor;
    Ok(ResidentOpticalIntervalOutcome {
        changed_neurons,
        emitted_neuron_fractals: emitted,
        mosaic_formed: None,
        admitted_mosaic: None,
        hippocampal_episode: None,
        partial_cue_reassembly_count: 0,
    })
}

fn settle_resident_recurrence_interval(
    cohort: &mut ResidentReachedCohort,
    input: ReachedCohortIntervalInput<'_>,
    gate_work_perturbed_neurons: Vec<bool>,
    existing_mosaics: &[AdmittedPhysicalMosaic],
    max_encoded_bytes: usize,
    source_generation: u64,
    source: &NativeJointSourceEpisode,
    source_occurrence_index: usize,
) -> Result<ResidentOpticalIntervalOutcome, FormationError> {
    let retained = cohort
        .retained_experience
        .as_ref()
        .ok_or(FormationError::NoncanonicalState)?;
    let learned = retained
        .post_experience_quiescent
        .as_ref()
        .ok_or(FormationError::NoncanonicalState)?;
    if cohort.pending_recurrence.is_none()
        && is_proper_partial_cue(retained, learned, &gate_work_perturbed_neurons)?
    {
        cohort.pending_recurrence = Some(ResidentRecurrenceEvidence {
            gate_work_perturbed_neurons: vec![false; cohort.anatomy.neuron_count()]
                .into_boxed_slice(),
            active_recurrence_contacts: vec![false; cohort.anatomy.contact_count()]
                .into_boxed_slice(),
        });
    }

    let predecessor = cohort.state.clone();
    #[cfg(test)]
    RESIDENT_ACTUAL_RECURRENCE_SETTLEMENTS.with(|count| count.set(count.get() + 1));
    let actual = settle_reached_cohort_interval(&cohort.anatomy, &cohort.state, input)
        .map_err(FormationError::PhysicalSettlementUnavailable)?;
    let changed_neurons = predecessor
        .neurons()
        .iter()
        .zip(actual.successor.neurons())
        .filter(|(prior, successor)| prior != successor)
        .count();
    let partial_cue_reassembly_count = 0;
    cohort.state = actual.successor.clone();
    let Some(mut recurrence) = cohort.pending_recurrence.take() else {
        return Ok(ResidentOpticalIntervalOutcome {
            changed_neurons,
            emitted_neuron_fractals: Vec::new(),
            mosaic_formed: None,
            admitted_mosaic: None,
            hippocampal_episode: None,
            partial_cue_reassembly_count,
        });
    };
    or_bits(
        &mut recurrence.gate_work_perturbed_neurons,
        &gate_work_perturbed_neurons,
    )?;
    or_bits(
        &mut recurrence.active_recurrence_contacts,
        &active_contact_bits(&actual.contact_transitions),
    )?;
    let original = original_settlement(&cohort.anatomy, retained, learned)?;
    let actual_recurrence = recurrence_settlement(
        &cohort.anatomy,
        learned,
        cohort.state.clone(),
        recurrence.gate_work_perturbed_neurons.clone(),
        recurrence.active_recurrence_contacts.clone(),
    )?;
    let mosaic = match admit_physical_mosaic(&cohort.anatomy, &original, &actual_recurrence) {
        Ok(mosaic) => mosaic,
        Err(error) if physical_mosaic_non_admission(error) => {
            if !actual.quiescent {
                cohort.pending_recurrence = Some(recurrence);
            }
            return Ok(ResidentOpticalIntervalOutcome {
                changed_neurons,
                emitted_neuron_fractals: Vec::new(),
                mosaic_formed: None,
                admitted_mosaic: None,
                hippocampal_episode: None,
                partial_cue_reassembly_count,
            });
        }
        Err(error) => return Err(FormationError::PhysicalMosaicUnavailable(error)),
    };
    let already_formed = existing_mosaics.iter().any(|prior| prior == &mosaic);
    let encoded = encode_admitted_physical_mosaic(&cohort.anatomy, &mosaic, max_encoded_bytes)
        .map_err(FormationError::PhysicalMosaicCodecUnavailable)?;
    let receipt = sha256(&encoded);
    let hippocampal_episode = build_typed_hippocampal_episode(
        &cohort.anatomy,
        retained,
        learned,
        &recurrence,
        &actual_recurrence,
        &mosaic,
        encoded.clone(),
        source_generation,
        source,
        source_occurrence_index,
    )?;
    Ok(ResidentOpticalIntervalOutcome {
        changed_neurons,
        emitted_neuron_fractals: Vec::new(),
        mosaic_formed: (!already_formed).then_some(receipt),
        admitted_mosaic: (!already_formed).then_some(mosaic),
        hippocampal_episode: Some(hippocampal_episode),
        partial_cue_reassembly_count: 1,
    })
}

fn original_settlement(
    anatomy: &ReachedCohortAnatomy,
    retained: &ResidentExperienceEvidence,
    learned: &ReachedCohortState,
) -> Result<ReachedCohortPostExperienceSettlement, FormationError> {
    let neuron_fractals = physical_deltas(anatomy, &retained.pre_experience_quiescent, learned)?;
    Ok(ReachedCohortPostExperienceSettlement {
        quiescent: QuiescentReachedCohortState::from_state(learned.clone()),
        neuron_fractals,
        electrical_contact_was_active: retained
            .active_electrical_contacts
            .iter()
            .any(|active| *active),
        gate_work_perturbed_neurons: retained.gate_work_perturbed_neurons.clone(),
        active_electrical_contacts: retained.active_electrical_contacts.clone(),
    })
}

fn recurrence_settlement(
    anatomy: &ReachedCohortAnatomy,
    predecessor: &ReachedCohortState,
    successor: ReachedCohortState,
    gate_work_perturbed_neurons: Box<[bool]>,
    active_electrical_contacts: Box<[bool]>,
) -> Result<ReachedCohortRecurrenceSettlement, FormationError> {
    Ok(ReachedCohortRecurrenceSettlement {
        neuron_physical_deltas: physical_deltas(anatomy, predecessor, &successor)?,
        successor,
        gate_work_perturbed_neurons,
        active_electrical_contacts,
    })
}

#[allow(clippy::too_many_arguments)]
fn build_typed_hippocampal_episode(
    anatomy: &ReachedCohortAnatomy,
    retained: &ResidentExperienceEvidence,
    learned: &ReachedCohortState,
    recurrence: &ResidentRecurrenceEvidence,
    actual_recurrence: &ReachedCohortRecurrenceSettlement,
    mosaic: &AdmittedPhysicalMosaic,
    physical_mosaic: Vec<u8>,
    source_generation: u64,
    source: &NativeJointSourceEpisode,
    source_occurrence_index: usize,
) -> Result<TypedEpisodeAdmission, FormationError> {
    if source_generation == 0 {
        return Err(FormationError::NoncanonicalState);
    }
    let original_transition_evidence = encode_experience_evidence(anatomy, retained)?;
    let recurrence_evidence = encode_recurrence_evidence(anatomy, recurrence)?;
    let learned_state = encode_reached_cohort_state(anatomy, learned)
        .map_err(|_| FormationError::NoncanonicalState)?;
    let recurrent_state = encode_reached_cohort_state(anatomy, &actual_recurrence.successor)
        .map_err(|_| FormationError::NoncanonicalState)?;
    let mut recurrent_transition_evidence = Vec::new();
    recurrent_transition_evidence.extend_from_slice(HIPPOCAMPAL_RECURRENCE_MAGIC);
    push_length(
        &mut recurrent_transition_evidence,
        recurrence_evidence.len(),
    )?;
    recurrent_transition_evidence.extend_from_slice(&recurrence_evidence);
    push_length(&mut recurrent_transition_evidence, learned_state.len())?;
    recurrent_transition_evidence.extend_from_slice(&learned_state);
    push_length(&mut recurrent_transition_evidence, recurrent_state.len())?;
    recurrent_transition_evidence.extend_from_slice(&recurrent_state);

    let mut participants = mosaic
        .member_lineages()
        .iter()
        .map(|lineage| {
            let member_index = anatomy
                .neuron_lineages()
                .iter()
                .position(|candidate| candidate == lineage)
                .ok_or(FormationError::NeuronLineageAuthorityAbsent)?;
            if actual_recurrence.neuron_physical_deltas[member_index].is_none() {
                return Err(FormationError::NoncanonicalState);
            }
            Ok(EpisodeParticipant { lineage: *lineage })
        })
        .collect::<Result<Vec<_>, _>>()?;
    participants.sort_by_key(|participant| participant.lineage);
    let episode = TypedEpisodeAdmission {
        predecessor_generation: source_generation - 1,
        episode_generation: source_generation,
        source_authority: source.joint_source_authority_receipt(),
        source_body: source.joint_source_body().to_vec().into_boxed_slice(),
        source_port_count: source.joint_source_ports().len(),
        source_sample_count: source.joint_source_sample_count(),
        source_occurrence_count: source.joint_source_occurrences().len(),
        source_occurrence_frame_count: source.joint_source_occurrence_frame_count(),
        source_occurrence_index,
        physical_mosaic: physical_mosaic.into_boxed_slice(),
        original_transition_evidence: original_transition_evidence.into_boxed_slice(),
        recurrent_transition_evidence: recurrent_transition_evidence.into_boxed_slice(),
        participants: participants.into_boxed_slice(),
    };
    validate_typed_hippocampal_episode(anatomy, &episode)?;
    Ok(episode)
}

fn validate_typed_hippocampal_episode(
    anatomy: &ReachedCohortAnatomy,
    episode: &TypedEpisodeAdmission,
) -> Result<(), FormationError> {
    let source = crate::joint_source_episode::decode_native_joint_source_episode(
        &episode.source_body,
        episode.source_port_count,
        episode.source_sample_count,
        episode.source_occurrence_count,
        episode.source_occurrence_frame_count,
    )
    .map_err(|_| FormationError::NoncanonicalState)?;
    if source.joint_source_authority_receipt() != episode.source_authority
        || source
            .joint_source_occurrences()
            .get(episode.source_occurrence_index)
            .is_none()
    {
        return Err(FormationError::NoncanonicalState);
    }
    let mosaic = decode_admitted_physical_mosaic(
        anatomy,
        &episode.physical_mosaic,
        episode.physical_mosaic.len(),
    )
    .map_err(FormationError::PhysicalMosaicCodecUnavailable)?;
    let original = decode_experience_evidence(&episode.original_transition_evidence, anatomy)?;
    let learned = original
        .post_experience_quiescent
        .as_ref()
        .ok_or(FormationError::NoncanonicalState)?;
    let mut cursor = HIPPOCAMPAL_RECURRENCE_MAGIC.len();
    if episode.recurrent_transition_evidence.get(..cursor) != Some(HIPPOCAMPAL_RECURRENCE_MAGIC) {
        return Err(FormationError::NoncanonicalState);
    }
    let recurrence_length = read_length(&episode.recurrent_transition_evidence, &mut cursor)?;
    let recurrence_end = cursor
        .checked_add(recurrence_length)
        .ok_or(FormationError::ArithmeticOverflow)?;
    let recurrence = decode_recurrence_evidence(
        episode
            .recurrent_transition_evidence
            .get(cursor..recurrence_end)
            .ok_or(FormationError::NoncanonicalState)?,
        anatomy,
    )?;
    cursor = recurrence_end;
    let learned_length = read_length(&episode.recurrent_transition_evidence, &mut cursor)?;
    let learned_end = cursor
        .checked_add(learned_length)
        .ok_or(FormationError::ArithmeticOverflow)?;
    let recurrent_predecessor = decode_reached_cohort_state(
        anatomy,
        episode
            .recurrent_transition_evidence
            .get(cursor..learned_end)
            .ok_or(FormationError::NoncanonicalState)?,
    )
    .map_err(|_| FormationError::NoncanonicalState)?;
    cursor = learned_end;
    let successor_length = read_length(&episode.recurrent_transition_evidence, &mut cursor)?;
    let successor_end = cursor
        .checked_add(successor_length)
        .ok_or(FormationError::ArithmeticOverflow)?;
    let recurrent_successor = decode_reached_cohort_state(
        anatomy,
        episode
            .recurrent_transition_evidence
            .get(cursor..successor_end)
            .ok_or(FormationError::NoncanonicalState)?,
    )
    .map_err(|_| FormationError::NoncanonicalState)?;
    if successor_end != episode.recurrent_transition_evidence.len()
        || recurrent_predecessor != *learned
    {
        return Err(FormationError::NoncanonicalState);
    }
    let recurrent_deltas = physical_deltas(anatomy, &recurrent_predecessor, &recurrent_successor)?;
    let original_settlement = original_settlement(anatomy, &original, learned)?;
    let recurrent_settlement = ReachedCohortRecurrenceSettlement {
        successor: recurrent_successor,
        neuron_physical_deltas: recurrent_deltas,
        gate_work_perturbed_neurons: recurrence.gate_work_perturbed_neurons,
        active_electrical_contacts: recurrence.active_recurrence_contacts,
    };
    if admit_physical_mosaic(anatomy, &original_settlement, &recurrent_settlement)
        .map_err(FormationError::PhysicalMosaicUnavailable)?
        != mosaic
    {
        return Err(FormationError::NoncanonicalState);
    }
    let mut expected = mosaic
        .member_lineages()
        .iter()
        .map(|lineage| EpisodeParticipant { lineage: *lineage })
        .collect::<Vec<_>>();
    expected.sort_by_key(|participant| participant.lineage);
    if episode.participants.as_ref() != expected.as_slice() {
        return Err(FormationError::NeuronLineageAuthorityChanged);
    }
    Ok(())
}

fn physical_deltas(
    anatomy: &ReachedCohortAnatomy,
    predecessor: &ReachedCohortState,
    successor: &ReachedCohortState,
) -> Result<Box<[Option<SparsePhysicalStateDelta>]>, FormationError> {
    if predecessor.neurons().len() != anatomy.neuron_count()
        || successor.neurons().len() != anatomy.neuron_count()
    {
        return Err(FormationError::NoncanonicalState);
    }
    predecessor
        .neurons()
        .iter()
        .zip(successor.neurons())
        .enumerate()
        .map(|(neuron_index, (prior, next))| {
            sparse_physical_state_delta(prior, next).map_err(|error| {
                FormationError::PhysicalSettlementUnavailable(ReachedCohortError::Neuron {
                    neuron_index,
                    error,
                })
            })
        })
        .collect::<Result<Vec<_>, _>>()
        .map(Vec::into_boxed_slice)
}

fn is_proper_partial_cue(
    retained: &ResidentExperienceEvidence,
    learned: &ReachedCohortState,
    perturbed: &[bool],
) -> Result<bool, FormationError> {
    if perturbed.len() != learned.neurons().len() {
        return Err(FormationError::NoncanonicalState);
    }
    let mut member_count = 0usize;
    let mut cue_count = 0usize;
    for (index, (prior, successor)) in retained
        .pre_experience_quiescent
        .neurons()
        .iter()
        .zip(learned.neurons())
        .enumerate()
    {
        let member = sparse_physical_state_delta(prior, successor)
            .map_err(|error| {
                FormationError::PhysicalSettlementUnavailable(ReachedCohortError::Neuron {
                    neuron_index: index,
                    error,
                })
            })?
            .is_some();
        member_count = member_count
            .checked_add(usize::from(member))
            .ok_or(FormationError::ArithmeticOverflow)?;
        if perturbed[index] {
            if !member {
                return Ok(false);
            }
            cue_count = cue_count
                .checked_add(1)
                .ok_or(FormationError::ArithmeticOverflow)?;
        }
    }
    Ok(cue_count > 0 && cue_count < member_count)
}

fn active_contact_bits(
    transitions: &[crate::sparse_electrical_contact::ElectricalContactTransition],
) -> Vec<bool> {
    transitions
        .iter()
        .map(|transition| {
            transition.outward_current_from_left_picoamperes.parts().0 != 0
                || transition.outward_elementary_charges_from_left != 0
        })
        .collect()
}

fn or_bits(target: &mut [bool], values: &[bool]) -> Result<(), FormationError> {
    if target.len() != values.len() {
        return Err(FormationError::NoncanonicalState);
    }
    for (target, value) in target.iter_mut().zip(values) {
        *target |= *value;
    }
    Ok(())
}

fn physical_mosaic_non_admission(error: PhysicalMosaicError) -> bool {
    matches!(
        error,
        PhysicalMosaicError::FewerThanThreeRetainedFractals
            | PhysicalMosaicError::OriginalRelationNotConnected
            | PhysicalMosaicError::CueIsEmpty
            | PhysicalMosaicError::CueIsNotPartial
            | PhysicalMosaicError::CueOutsideFormation
            | PhysicalMosaicError::RecurrenceDidNotReachFormation
            | PhysicalMosaicError::RecurrenceDidNotChangeEveryMember
    )
}

fn encode_experience_evidence(
    anatomy: &ReachedCohortAnatomy,
    evidence: &ResidentExperienceEvidence,
) -> Result<Vec<u8>, FormationError> {
    if evidence.gate_work_perturbed_neurons.len() != anatomy.neuron_count()
        || evidence.active_electrical_contacts.len() != anatomy.contact_count()
    {
        return Err(FormationError::NoncanonicalState);
    }
    let predecessor = encode_reached_cohort_state(anatomy, &evidence.pre_experience_quiescent)
        .map_err(|_| FormationError::NoncanonicalState)?;
    let successor = evidence
        .post_experience_quiescent
        .as_ref()
        .map(|state| encode_reached_cohort_state(anatomy, state))
        .transpose()
        .map_err(|_| FormationError::NoncanonicalState)?;
    let length = EXPERIENCE_MAGIC
        .len()
        .checked_add(8)
        .and_then(|value| value.checked_add(predecessor.len()))
        .and_then(|value| value.checked_add(1))
        .and_then(|value| {
            successor.as_ref().map_or(Some(value), |successor| {
                value.checked_add(8)?.checked_add(successor.len())
            })
        })
        .and_then(|value| value.checked_add(8))
        .and_then(|value| value.checked_add(evidence.gate_work_perturbed_neurons.len()))
        .and_then(|value| value.checked_add(8))
        .and_then(|value| value.checked_add(evidence.active_electrical_contacts.len()))
        .ok_or(FormationError::ArithmeticOverflow)?;
    let mut encoded = Vec::with_capacity(length);
    encoded.extend_from_slice(EXPERIENCE_MAGIC);
    push_length(&mut encoded, predecessor.len())?;
    encoded.extend_from_slice(&predecessor);
    encoded.push(u8::from(successor.is_some()));
    if let Some(successor) = successor {
        push_length(&mut encoded, successor.len())?;
        encoded.extend_from_slice(&successor);
    }
    push_length(&mut encoded, evidence.gate_work_perturbed_neurons.len())?;
    encoded.extend(
        evidence
            .gate_work_perturbed_neurons
            .iter()
            .map(|value| u8::from(*value)),
    );
    push_length(&mut encoded, evidence.active_electrical_contacts.len())?;
    encoded.extend(
        evidence
            .active_electrical_contacts
            .iter()
            .map(|value| u8::from(*value)),
    );
    Ok(encoded)
}

fn decode_optional_experience_evidence(
    bytes: &[u8],
    cursor: &mut usize,
    anatomy: &ReachedCohortAnatomy,
    retained: bool,
) -> Result<Option<ResidentExperienceEvidence>, FormationError> {
    let present = *bytes
        .get(*cursor)
        .ok_or(FormationError::NoncanonicalState)?;
    *cursor = cursor
        .checked_add(1)
        .ok_or(FormationError::ArithmeticOverflow)?;
    match present {
        0 => Ok(None),
        1 => {
            let length = read_length(bytes, cursor)?;
            let end = cursor
                .checked_add(length)
                .ok_or(FormationError::ArithmeticOverflow)?;
            let evidence = decode_experience_evidence(
                bytes
                    .get(*cursor..end)
                    .ok_or(FormationError::NoncanonicalState)?,
                anatomy,
            )?;
            *cursor = end;
            if evidence.post_experience_quiescent.is_some() != retained {
                return Err(FormationError::NoncanonicalState);
            }
            if retained {
                let post = evidence
                    .post_experience_quiescent
                    .as_ref()
                    .ok_or(FormationError::NoncanonicalState)?;
                let retained = evidence
                    .pre_experience_quiescent
                    .neurons()
                    .iter()
                    .zip(post.neurons())
                    .enumerate()
                    .try_fold(0usize, |count, (neuron_index, (prior, successor))| {
                        let changed = sparse_physical_state_delta(prior, successor)
                            .map_err(|error| {
                                FormationError::PhysicalSettlementUnavailable(
                                    ReachedCohortError::Neuron {
                                        neuron_index,
                                        error,
                                    },
                                )
                            })?
                            .is_some();
                        count
                            .checked_add(usize::from(changed))
                            .ok_or(FormationError::ArithmeticOverflow)
                    })?;
                if retained < 3 {
                    return Err(FormationError::NoncanonicalState);
                }
            }
            Ok(Some(evidence))
        }
        _ => Err(FormationError::NoncanonicalState),
    }
}

fn decode_experience_evidence(
    encoded: &[u8],
    anatomy: &ReachedCohortAnatomy,
) -> Result<ResidentExperienceEvidence, FormationError> {
    if encoded.get(..EXPERIENCE_MAGIC.len()) != Some(EXPERIENCE_MAGIC) {
        return Err(FormationError::NoncanonicalState);
    }
    let mut cursor = EXPERIENCE_MAGIC.len();
    let predecessor_length = read_length(encoded, &mut cursor)?;
    let predecessor_end = cursor
        .checked_add(predecessor_length)
        .ok_or(FormationError::ArithmeticOverflow)?;
    let pre_experience_quiescent = decode_reached_cohort_state(
        anatomy,
        encoded
            .get(cursor..predecessor_end)
            .ok_or(FormationError::NoncanonicalState)?,
    )
    .map_err(|_| FormationError::NoncanonicalState)?;
    cursor = predecessor_end;
    let post_experience_quiescent = match encoded
        .get(cursor)
        .copied()
        .ok_or(FormationError::NoncanonicalState)?
    {
        0 => {
            cursor = cursor
                .checked_add(1)
                .ok_or(FormationError::ArithmeticOverflow)?;
            None
        }
        1 => {
            cursor = cursor
                .checked_add(1)
                .ok_or(FormationError::ArithmeticOverflow)?;
            let length = read_length(encoded, &mut cursor)?;
            let end = cursor
                .checked_add(length)
                .ok_or(FormationError::ArithmeticOverflow)?;
            let state = decode_reached_cohort_state(
                anatomy,
                encoded
                    .get(cursor..end)
                    .ok_or(FormationError::NoncanonicalState)?,
            )
            .map_err(|_| FormationError::NoncanonicalState)?;
            cursor = end;
            Some(state)
        }
        _ => return Err(FormationError::NoncanonicalState),
    };
    let neuron_count = read_length(encoded, &mut cursor)?;
    if neuron_count != anatomy.neuron_count() {
        return Err(FormationError::NoncanonicalState);
    }
    let neuron_end = cursor
        .checked_add(neuron_count)
        .ok_or(FormationError::ArithmeticOverflow)?;
    let gate_work_perturbed_neurons = decode_bools(
        encoded
            .get(cursor..neuron_end)
            .ok_or(FormationError::NoncanonicalState)?,
    )?;
    cursor = neuron_end;
    let contact_count = read_length(encoded, &mut cursor)?;
    if contact_count != anatomy.contact_count() {
        return Err(FormationError::NoncanonicalState);
    }
    let contact_end = cursor
        .checked_add(contact_count)
        .ok_or(FormationError::ArithmeticOverflow)?;
    let active_electrical_contacts = decode_bools(
        encoded
            .get(cursor..contact_end)
            .ok_or(FormationError::NoncanonicalState)?,
    )?;
    if contact_end != encoded.len() {
        return Err(FormationError::NoncanonicalState);
    }
    Ok(ResidentExperienceEvidence {
        pre_experience_quiescent,
        post_experience_quiescent,
        gate_work_perturbed_neurons,
        active_electrical_contacts,
    })
}

fn encode_recurrence_evidence(
    anatomy: &ReachedCohortAnatomy,
    evidence: &ResidentRecurrenceEvidence,
) -> Result<Vec<u8>, FormationError> {
    let neuron_count = anatomy.neuron_count();
    let contact_count = anatomy.contact_count();
    if evidence.gate_work_perturbed_neurons.len() != neuron_count
        || evidence.active_recurrence_contacts.len() != contact_count
        || !evidence
            .gate_work_perturbed_neurons
            .iter()
            .any(|value| *value)
    {
        return Err(FormationError::NoncanonicalState);
    }
    let length = RECURRENCE_MAGIC
        .len()
        .checked_add(8 + neuron_count)
        .and_then(|value| value.checked_add(8 + contact_count))
        .ok_or(FormationError::ArithmeticOverflow)?;
    let mut encoded = Vec::with_capacity(length);
    encoded.extend_from_slice(RECURRENCE_MAGIC);
    encode_bool_slice(&mut encoded, &evidence.gate_work_perturbed_neurons)?;
    encode_bool_slice(&mut encoded, &evidence.active_recurrence_contacts)?;
    Ok(encoded)
}

fn decode_recurrence_evidence(
    encoded: &[u8],
    anatomy: &ReachedCohortAnatomy,
) -> Result<ResidentRecurrenceEvidence, FormationError> {
    if encoded.get(..RECURRENCE_MAGIC.len()) != Some(RECURRENCE_MAGIC) {
        return Err(FormationError::NoncanonicalState);
    }
    let mut cursor = RECURRENCE_MAGIC.len();
    let gate_work_perturbed_neurons =
        decode_bool_slice(encoded, &mut cursor, anatomy.neuron_count())?;
    let active_recurrence_contacts =
        decode_bool_slice(encoded, &mut cursor, anatomy.contact_count())?;
    if cursor != encoded.len() || !gate_work_perturbed_neurons.iter().any(|value| *value) {
        return Err(FormationError::NoncanonicalState);
    }
    Ok(ResidentRecurrenceEvidence {
        gate_work_perturbed_neurons,
        active_recurrence_contacts,
    })
}

fn decode_optional_recurrence_evidence(
    bytes: &[u8],
    cursor: &mut usize,
    anatomy: &ReachedCohortAnatomy,
) -> Result<Option<ResidentRecurrenceEvidence>, FormationError> {
    let present = *bytes
        .get(*cursor)
        .ok_or(FormationError::NoncanonicalState)?;
    *cursor = cursor
        .checked_add(1)
        .ok_or(FormationError::ArithmeticOverflow)?;
    match present {
        0 => Ok(None),
        1 => {
            let length = read_length(bytes, cursor)?;
            let end = cursor
                .checked_add(length)
                .ok_or(FormationError::ArithmeticOverflow)?;
            let evidence = decode_recurrence_evidence(
                bytes
                    .get(*cursor..end)
                    .ok_or(FormationError::NoncanonicalState)?,
                anatomy,
            )?;
            *cursor = end;
            Ok(Some(evidence))
        }
        _ => Err(FormationError::NoncanonicalState),
    }
}

fn encode_bool_slice(encoded: &mut Vec<u8>, values: &[bool]) -> Result<(), FormationError> {
    push_length(encoded, values.len())?;
    encoded.extend(values.iter().map(|value| u8::from(*value)));
    Ok(())
}

fn decode_bool_slice(
    encoded: &[u8],
    cursor: &mut usize,
    expected: usize,
) -> Result<Box<[bool]>, FormationError> {
    let count = read_length(encoded, cursor)?;
    if count != expected {
        return Err(FormationError::NoncanonicalState);
    }
    let end = cursor
        .checked_add(count)
        .ok_or(FormationError::ArithmeticOverflow)?;
    let values = decode_bools(
        encoded
            .get(*cursor..end)
            .ok_or(FormationError::NoncanonicalState)?,
    )?;
    *cursor = end;
    Ok(values)
}

fn push_length(encoded: &mut Vec<u8>, value: usize) -> Result<(), FormationError> {
    encoded.extend_from_slice(
        &u64::try_from(value)
            .map_err(|_| FormationError::ArithmeticOverflow)?
            .to_le_bytes(),
    );
    Ok(())
}

fn read_length(bytes: &[u8], cursor: &mut usize) -> Result<usize, FormationError> {
    let end = cursor
        .checked_add(8)
        .ok_or(FormationError::ArithmeticOverflow)?;
    let value = usize::try_from(u64::from_le_bytes(
        bytes
            .get(*cursor..end)
            .ok_or(FormationError::NoncanonicalState)?
            .try_into()
            .map_err(|_| FormationError::NoncanonicalState)?,
    ))
    .map_err(|_| FormationError::ArithmeticOverflow)?;
    *cursor = end;
    Ok(value)
}

fn decode_bools(encoded: &[u8]) -> Result<Box<[bool]>, FormationError> {
    encoded
        .iter()
        .map(|value| match value {
            0 => Ok(false),
            1 => Ok(true),
            _ => Err(FormationError::NoncanonicalState),
        })
        .collect::<Result<Vec<_>, _>>()
        .map(Vec::into_boxed_slice)
}

const DORMANT_LINEAGE_SEED_MAGIC: &[u8; 8] = b"GLDLS01\0";

fn same_dormant_source(
    left: &crate::joint_source_episode::JointSourcePortView,
    right: &crate::joint_source_episode::JointSourcePortView,
) -> bool {
    left.sense == right.sense
        && left.topology_index == right.topology_index
        && left.sensor_id == right.sensor_id
        && left.substream_id == right.substream_id
}

fn valid_local_lineage(lineage: [u8; 16]) -> bool {
    if lineage[..8] != *LINEAGE_DOMAIN {
        return false;
    }
    let ordinal = u64::from_be_bytes(
        lineage[8..]
            .try_into()
            .expect("fixed local lineage ordinal width"),
    );
    ordinal != 0
}

fn lineage_ordinal(lineage: [u8; 16]) -> Result<u64, FormationError> {
    if !valid_local_lineage(lineage) {
        return Err(FormationError::NoncanonicalState);
    }
    Ok(u64::from_be_bytes(
        lineage[8..]
            .try_into()
            .map_err(|_| FormationError::NoncanonicalState)?,
    ))
}

fn allocate_local_lineage(next_lineage_ordinal: &mut u64) -> Result<[u8; 16], FormationError> {
    let ordinal = *next_lineage_ordinal;
    if ordinal == 0 {
        return Err(FormationError::NeuronLineageAuthorityAbsent);
    }
    let successor = ordinal
        .checked_add(1)
        .ok_or(FormationError::ArithmeticOverflow)?;
    let mut lineage = [0u8; 16];
    lineage[..8].copy_from_slice(LINEAGE_DOMAIN);
    lineage[8..].copy_from_slice(&ordinal.to_be_bytes());
    *next_lineage_ordinal = successor;
    Ok(lineage)
}

fn resolve_lineage_for_port(
    cohorts: &[ResidentReachedCohort],
    dormant: &[DormantLineageSeed],
    port: &crate::joint_source_episode::JointSourcePortView,
) -> Result<Option<[u8; 16]>, FormationError> {
    let mut resolved = None;
    for cohort in cohorts {
        for (site, lineage) in cohort
            .anatomy
            .source_sites()
            .iter()
            .zip(cohort.anatomy.neuron_lineages())
        {
            let key = DormantLineageSeed::from_site(site, *lineage)?;
            if key.matches_port(port) {
                if resolved.is_some_and(|prior| prior != *lineage) {
                    return Err(FormationError::NeuronLineageAuthorityChanged);
                }
                resolved = Some(*lineage);
            }
        }
    }
    for seed in dormant {
        if seed.matches_port(port) {
            if resolved.is_some_and(|prior| prior != seed.neuron_lineage) {
                return Err(FormationError::NeuronLineageAuthorityChanged);
            }
            resolved = Some(seed.neuron_lineage);
        }
    }
    Ok(resolved)
}

fn validate_lineage_state(state: &ResidentCognitiveFormationState) -> Result<(), FormationError> {
    if state.next_lineage_ordinal == 0 {
        return Err(FormationError::NoncanonicalState);
    }
    let mut retained = Vec::new();
    for cohort in &state.cohorts {
        for (site, lineage) in cohort
            .anatomy
            .source_sites()
            .iter()
            .zip(cohort.anatomy.neuron_lineages())
        {
            let seed = DormantLineageSeed::from_site(site, *lineage)?;
            if lineage_ordinal(*lineage)? >= state.next_lineage_ordinal
                || retained.iter().any(|prior: &DormantLineageSeed| {
                    prior.same_source(&seed) || prior.neuron_lineage == seed.neuron_lineage
                })
            {
                return Err(FormationError::NoncanonicalState);
            }
            retained.push(seed);
        }
    }
    for (index, seed) in state.dormant_lineage_seeds.iter().enumerate() {
        seed.validate()?;
        if lineage_ordinal(seed.neuron_lineage)? >= state.next_lineage_ordinal
            || state.dormant_lineage_seeds[..index].iter().any(|prior| {
                prior >= seed
                    || prior.same_source(seed)
                    || prior.neuron_lineage == seed.neuron_lineage
            })
            || retained
                .iter()
                .any(|prior| prior.same_source(seed) || prior.neuron_lineage == seed.neuron_lineage)
        {
            return Err(FormationError::NoncanonicalState);
        }
        retained.push(seed.clone());
    }
    Ok(())
}

fn encode_dormant_lineage_seed(seed: &DormantLineageSeed) -> Result<Vec<u8>, FormationError> {
    seed.validate()?;
    let mut output = Vec::new();
    output.extend_from_slice(DORMANT_LINEAGE_SEED_MAGIC);
    output.push(seed.sense);
    output.extend_from_slice(&seed.topology_index.to_le_bytes());
    push_seed_text(&mut output, &seed.sensor_id)?;
    push_seed_text(&mut output, &seed.substream_id)?;
    output.extend_from_slice(&seed.neuron_lineage);
    Ok(output)
}

fn decode_dormant_lineage_seed(encoded: &[u8]) -> Result<DormantLineageSeed, FormationError> {
    if encoded.get(..DORMANT_LINEAGE_SEED_MAGIC.len()) != Some(DORMANT_LINEAGE_SEED_MAGIC) {
        return Err(FormationError::NoncanonicalState);
    }
    let mut cursor = DORMANT_LINEAGE_SEED_MAGIC.len();
    let sense = *encoded
        .get(cursor)
        .ok_or(FormationError::NoncanonicalState)?;
    cursor += 1;
    let topology_end = cursor
        .checked_add(4)
        .ok_or(FormationError::ArithmeticOverflow)?;
    let topology_index = u32::from_le_bytes(
        encoded
            .get(cursor..topology_end)
            .ok_or(FormationError::NoncanonicalState)?
            .try_into()
            .map_err(|_| FormationError::NoncanonicalState)?,
    );
    cursor = topology_end;
    let sensor_id = take_seed_text(encoded, &mut cursor)?;
    let substream_id = take_seed_text(encoded, &mut cursor)?;
    let lineage_end = cursor
        .checked_add(16)
        .ok_or(FormationError::ArithmeticOverflow)?;
    let neuron_lineage = encoded
        .get(cursor..lineage_end)
        .ok_or(FormationError::NoncanonicalState)?
        .try_into()
        .map_err(|_| FormationError::NoncanonicalState)?;
    if lineage_end != encoded.len() {
        return Err(FormationError::NoncanonicalState);
    }
    DormantLineageSeed::new(
        sense,
        topology_index,
        &sensor_id,
        &substream_id,
        neuron_lineage,
    )
}

fn push_seed_text(output: &mut Vec<u8>, value: &str) -> Result<(), FormationError> {
    push_length(output, value.len())?;
    output.extend_from_slice(value.as_bytes());
    Ok(())
}

fn take_seed_text(encoded: &[u8], cursor: &mut usize) -> Result<String, FormationError> {
    let length = read_length(encoded, cursor)?;
    let end = cursor
        .checked_add(length)
        .ok_or(FormationError::ArithmeticOverflow)?;
    let value = std::str::from_utf8(
        encoded
            .get(*cursor..end)
            .ok_or(FormationError::NoncanonicalState)?,
    )
    .map_err(|_| FormationError::NoncanonicalState)?;
    *cursor = end;
    if value.is_empty() {
        return Err(FormationError::NoncanonicalState);
    }
    Ok(value.to_owned())
}

fn take_state_u64(encoded: &[u8], cursor: &mut usize) -> Result<u64, FormationError> {
    let end = cursor
        .checked_add(8)
        .ok_or(FormationError::ArithmeticOverflow)?;
    let value = u64::from_le_bytes(
        encoded
            .get(*cursor..end)
            .ok_or(FormationError::NoncanonicalState)?
            .try_into()
            .map_err(|_| FormationError::NoncanonicalState)?,
    );
    *cursor = end;
    Ok(value)
}

fn exact_optical_receptor_anatomy() -> Result<OpticalReceptorAnatomy, FormationError> {
    OpticalReceptorAnatomy::new(
        BigRational::from_integer(BigInt::from(4)),
        BigRational::from_integer(BigInt::from(1)),
        BigRational::new(BigInt::from(1), BigInt::from(2)),
        BigRational::from_integer(BigInt::from(1)),
    )
    .map_err(FormationError::OpticalWorkUnavailable)
}

fn exact_optical_occurrence(
    source: &NativeJointSourceEpisode,
    occurrence: &crate::joint_source_episode::JointSourceOccurrenceView,
) -> bool {
    !occurrence.port_indices.is_empty()
        && occurrence.port_indices.iter().all(|index| {
            source.joint_source_ports().get(*index).is_some_and(|port| {
                port.sense == 0
                    && port.physical_quantity == RETINAL_SPECTRAL_IRRADIANCE_QUANTITY
                    && port.physical_unit == RETINAL_REFERENCE_IRRADIANCE_UNIT
            })
        })
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) enum FormationError {
    BudgetExceeded { required: usize, available: usize },
    ArithmeticOverflow,
    InvalidSourceGeneration,
    SourceOccurrenceAbsent,
    JointFieldUnavailable(JointNeuronBoundaryError),
    PhysicalGenesisUnavailable(VirtualMaterialGenesisError),
    VestibularUnavailable(FunctionalVestibularError),
    DevelopmentalElectricalUnavailable(DevelopmentalElectricalError),
    OpticalWorkUnavailable(OpticalReceptorWorkError),
    PhysicalSettlementUnavailable(ReachedCohortError),
    PhysicalMosaicUnavailable(PhysicalMosaicError),
    PhysicalMosaicCodecUnavailable(PhysicalMosaicCodecError),
    NeuronLineageAuthorityAbsent,
    NeuronLineageAuthorityChanged,
    HippocampalUnavailable(HippocampalError),
    MultipleHippocampalAdmissions,
    HippocampalPublicationRequired,
    PreparedPredecessorChanged,
    DuplicateDevelopmentalSeed,
    RetiredCognitiveState,
    BadVersion,
    NoncanonicalState,
}

impl fmt::Display for FormationError {
    fn fmt(&self, output: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::BudgetExceeded {
                required,
                available,
            } => write!(
                output,
                "resident complete-neuron state requires {required} bytes but {available} were admitted"
            ),
            Self::ArithmeticOverflow => write!(output, "resident cognitive arithmetic overflow"),
            Self::InvalidSourceGeneration => {
                write!(output, "resident cognitive generation cannot advance")
            }
            Self::SourceOccurrenceAbsent => write!(output, "source contains no joint occurrence"),
            Self::JointFieldUnavailable(error) => {
                write!(output, "complete joint field is unavailable: {error:?}")
            }
            Self::PhysicalGenesisUnavailable(error) => {
                write!(output, "complete virtual-material neuron genesis is unavailable: {error:?}")
            }
            Self::VestibularUnavailable(error) => {
                write!(output, "typed vestibular neuron path is unavailable: {error:?}")
            }
            Self::DevelopmentalElectricalUnavailable(error) => {
                write!(output, "developmental electrical anatomy is unavailable: {error:?}")
            }
            Self::OpticalWorkUnavailable(error) => {
                write!(output, "exact optical receptor work is unavailable: {error:?}")
            }
            Self::PhysicalSettlementUnavailable(error) => {
                write!(output, "resident physical neuron settlement is unavailable: {error:?}")
            }
            Self::PhysicalMosaicUnavailable(error) => {
                write!(output, "physical mosaic admission is unavailable: {error:?}")
            }
            Self::PhysicalMosaicCodecUnavailable(error) => {
                write!(output, "physical mosaic persistence is unavailable: {error:?}")
            }
            Self::NeuronLineageAuthorityAbsent => {
                write!(output, "resident neuron lineage authority is absent")
            }
            Self::NeuronLineageAuthorityChanged => {
                write!(output, "resident neuron lineage authority changed")
            }
            Self::HippocampalUnavailable(error) => {
                write!(output, "hippocampal custody is unavailable: {error:?}")
            }
            Self::MultipleHippocampalAdmissions => {
                write!(output, "one cognitive transition admitted multiple hippocampal episodes")
            }
            Self::HippocampalPublicationRequired => {
                write!(output, "hippocampal cold publication is required before commit")
            }
            Self::PreparedPredecessorChanged => {
                write!(output, "prepared cognitive predecessor changed before commit")
            }
            Self::DuplicateDevelopmentalSeed => {
                write!(output, "developmental electrical source-site seed is duplicated")
            }
            Self::RetiredCognitiveState => write!(
                output,
                "retired empty or DSF-impression cognitive state cannot be restored"
            ),
            Self::BadVersion => write!(output, "cognitive boundary state has wrong version"),
            Self::NoncanonicalState => write!(output, "cognitive boundary state is noncanonical"),
        }
    }
}

impl std::error::Error for FormationError {}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::developmental_electrical_anatomy::{
        DevelopmentalElectricalContact, DevelopmentalElectricalSeed,
    };
    use crate::exact_rational::ExactRational;
    use crate::local_cupula_hair_bundle_geometry::LocalCupulaBundleAnatomy;
    use crate::local_gating_spring_energy::GatingSpringEnergyAnatomy;
    use crate::local_tip_link_extension::TipLinkInsertionGeometry;
    use crate::neuron_source_anchor::tests::{
        exact_dark_optical_episode, exact_episode, exact_five_optical_episode,
        exact_four_dark_optical_episode, exact_four_partial_optical_episode,
        exact_four_reordered_optical_episode, exact_four_single_optical_episode,
        exact_four_subset_optical_episode, exact_optical_episode, exact_split_four_optical_episode,
        exact_two_of_four_optical_episode,
    };
    use crate::reached_vestibular_bundle_path::settle_reached_vestibular_bundle_tick;
    use crate::resident_receptor_transition::prepare_resident_vestibular_ingress;
    use crate::vestibular_neuron_path::FunctionalVestibularAnatomy;
    use crate::virtual_body_yaw_motion::{
        settle_signed_yaw_actuation, SignedYawActuation, YawBodyState,
    };
    use crate::virtual_vestibular_canal::{
        CanalAnatomy, CanalState, PositiveRatio, WORLD_MAX_ACTION_TICKS,
    };

    fn explicit_optical_seed(
        source: &NativeJointSourceEpisode,
        conductance_picosiemens: i128,
    ) -> DevelopmentalElectricalSeed {
        explicit_optical_seed_for_occurrence(source, 0, conductance_picosiemens)
    }

    fn explicit_optical_seed_for_occurrence(
        source: &NativeJointSourceEpisode,
        occurrence_index: usize,
        conductance_picosiemens: i128,
    ) -> DevelopmentalElectricalSeed {
        let shared =
            prepare_complete_joint_field_admitted_fixture(source, occurrence_index).unwrap();
        let sites = (0..shared.vertex_count())
            .map(|coordinate_index| {
                let perspective = bind_neuron_perspective(&shared, coordinate_index, 0).unwrap();
                NeuronSourceSite::from_anchor(
                    bind_neuron_source_anchor(source, perspective).unwrap(),
                )
            })
            .collect::<Vec<_>>();
        let contacts = (1..sites.len())
            .map(|right| {
                DevelopmentalElectricalContact::new(
                    right - 1,
                    right,
                    ExactRational::integer(conductance_picosiemens),
                    sites.len(),
                )
                .unwrap()
            })
            .collect::<Vec<_>>();
        DevelopmentalElectricalSeed::new(sites, contacts).unwrap()
    }

    fn four_optical_interval<'a>(
        source: &'a NativeJointSourceEpisode,
        shared: &'a crate::joint_uf_neuron_boundary::SharedCompleteJointField,
        anatomy: &ReachedCohortAnatomy,
        catalysts: &'a [Box<[u128]>],
        optical: &OpticalReceptorAnatomy,
    ) -> ReachedCohortIntervalInput<'a> {
        let inputs = (0..shared.vertex_count())
            .map(|coordinate_index| {
                let perspective = bind_neuron_perspective(shared, coordinate_index, 0).unwrap();
                let receptor = derive_optical_receptor_work(source, perspective, optical).unwrap();
                NeuronIntervalInput {
                    perspective,
                    gate_work: receptor.gate_work,
                    interval_microseconds: WORLD_MECHANICAL_TICK_MICROSECONDS,
                    recovery: RecoveryContact::new(&catalysts[coordinate_index], 0, 0),
                    dna_expression: DnaExpressionContact::new(0),
                }
            })
            .collect::<Vec<_>>();
        assert_eq!(inputs.len(), anatomy.neuron_count());
        ReachedCohortIntervalInput::from_episode(source, inputs).unwrap()
    }

    fn local_lineage(ordinal: u64) -> [u8; 16] {
        let mut lineage = [0; 16];
        lineage[..8].copy_from_slice(LINEAGE_DOMAIN);
        lineage[8..].copy_from_slice(&ordinal.to_be_bytes());
        lineage
    }

    #[test]
    fn active_physical_bonds_distinguish_linear_and_web_formation() {
        let members = [
            local_lineage(1),
            local_lineage(2),
            local_lineage(3),
            local_lineage(4),
        ];
        let bond = |left, right| {
            crate::physical_mosaic::StablePhysicalBondReference::new(
                members[left],
                members[right],
                0,
            )
            .unwrap()
        };
        let linear_bonds = vec![bond(0, 1), bond(1, 2), bond(2, 3)];
        assert_eq!(
            classify_dynamic_topology(&members, &linear_bonds).unwrap(),
            (3, true)
        );

        let web_bonds = vec![bond(0, 1), bond(0, 2), bond(0, 3)];
        assert_eq!(
            classify_dynamic_topology(&members, &web_bonds).unwrap(),
            (3, false)
        );
    }

    #[test]
    fn temporal_reassembly_distinguishes_relation_tapestry_and_deeper_activity() {
        let mosaic = |value: u8| vec![value].into_boxed_slice();
        assert_eq!(
            classify_temporal_reassembly(
                true,
                &[0],
                &[vec![mosaic(1)], vec![mosaic(2)], vec![], vec![]],
                [4, 4, 0, 0],
                4,
            ),
            (1, 0, 0, 0)
        );
        assert_eq!(
            classify_temporal_reassembly(
                false,
                &[0],
                &[vec![mosaic(0)], vec![mosaic(1)], vec![mosaic(2)], vec![],],
                [4, 4, 4, 0],
                4,
            ),
            (0, 1, 0, 0)
        );
        assert_eq!(
            classify_temporal_reassembly(
                false,
                &[0],
                &[
                    vec![mosaic(0)],
                    vec![mosaic(0)],
                    vec![mosaic(1)],
                    vec![mosaic(2)],
                ],
                [4, 4, 4, 4],
                4,
            ),
            (0, 0, 1, 0)
        );
        assert_eq!(
            classify_temporal_reassembly(
                true,
                &[0],
                &[
                    vec![mosaic(1)],
                    vec![mosaic(1)],
                    vec![mosaic(2)],
                    vec![mosaic(2)],
                ],
                [4, 4, 4, 4],
                4,
            ),
            (1, 0, 0, 1)
        );
    }

    #[test]
    fn empty_genesis_is_exact_and_bounded() {
        let state = ResidentCognitiveFormationState::default();
        let encoded = state.encode(FIXED_BYTES).unwrap();
        assert_eq!(encoded.len(), FIXED_BYTES);
        assert_eq!(
            ResidentCognitiveFormationState::decode(&encoded, FIXED_BYTES).unwrap(),
            state
        );
    }

    #[test]
    fn dormant_four_field_lineage_seed_is_consumed_once_by_exact_current_source() {
        let source = exact_optical_episode();
        let port = &source.joint_source_ports()[0];
        let seed = DormantLineageSeed::new(
            port.sense,
            port.topology_index,
            &port.sensor_id,
            &port.substream_id,
            local_lineage(7),
        )
        .unwrap();
        let state =
            ResidentCognitiveFormationState::from_genesis_parts(0, 8, Vec::new(), vec![seed])
                .unwrap();
        let dormant_bytes = state.encode(16_000_000).unwrap();
        let restored = ResidentCognitiveFormationState::decode(&dormant_bytes, 16_000_000).unwrap();
        assert_eq!(restored.encode(16_000_000).unwrap(), dormant_bytes);
        assert_eq!(restored.dormant_lineage_seeds.len(), 1);

        let prepared = restored.prepare(&source, 16_000_000).unwrap();
        assert!(prepared.successor.dormant_lineage_seeds.is_empty());
        assert_eq!(prepared.successor.next_lineage_ordinal, 8);
        assert_eq!(
            prepared.successor.cohorts[0].anatomy.neuron_lineages(),
            &[local_lineage(7)]
        );
        let successor = restored.encode_successor(&prepared, 16_000_000).unwrap();
        let cold = ResidentCognitiveFormationState::decode(&successor, 16_000_000).unwrap();
        assert_eq!(cold.encode(16_000_000).unwrap(), successor);
        assert!(cold.dormant_lineage_seeds.is_empty());
        assert_eq!(
            cold.cohorts[0].anatomy.neuron_lineages(),
            &[local_lineage(7)]
        );
    }

    #[test]
    fn one_shared_field_is_evaluated_once_and_new_lineage_survives_restart() {
        let source = exact_optical_episode();
        RESIDENT_JOINT_FIELD_EVALUATIONS.with(|count| count.set(0));
        let state = ResidentCognitiveFormationState::default();
        let prepared = state.prepare(&source, 16_000_000).unwrap();
        RESIDENT_JOINT_FIELD_EVALUATIONS.with(|count| {
            assert_eq!(count.get(), source.joint_source_occurrences().len());
        });
        assert_eq!(prepared.observation.dsf_delivery_count, 1);
        assert_eq!(prepared.successor.next_lineage_ordinal, 2);
        assert_eq!(
            prepared.successor.cohorts[0].anatomy.neuron_lineages(),
            &[local_lineage(1)]
        );
        let encoded = state.encode_successor(&prepared, 16_000_000).unwrap();
        let cold = ResidentCognitiveFormationState::decode(&encoded, 16_000_000).unwrap();
        assert_eq!(cold.encode(16_000_000).unwrap(), encoded);
        let recurrent = cold.prepare(&source, 16_000_000).unwrap();
        assert_eq!(recurrent.successor.next_lineage_ordinal, 2);
        assert_eq!(
            recurrent.successor.cohorts[0].anatomy.neuron_lineages(),
            &[local_lineage(1)]
        );
    }

    #[test]
    fn reordered_occurrence_reuses_the_same_persistent_neurons() {
        let first = crate::neuron_source_anchor::tests::exact_four_optical_episode();
        let reordered = exact_four_reordered_optical_episode();
        let mut state = ResidentCognitiveFormationState::default();
        let prepared = state.prepare(&first, 16_000_000).unwrap();
        state.commit(prepared).unwrap();
        let original_lineages = state.retained_neuron_lineages();
        assert_eq!(original_lineages.len(), 4);

        let prepared = state.prepare(&reordered, 16_000_000).unwrap();
        assert_eq!(prepared.successor.cohorts.len(), 1);
        assert_eq!(prepared.successor.summary().complete_neuron_count, 4);
        assert_eq!(
            prepared.successor.retained_neuron_lineages(),
            original_lineages
        );
        let encoded = state.encode_successor(&prepared, 16_000_000).unwrap();
        let restored = ResidentCognitiveFormationState::decode(&encoded, 16_000_000).unwrap();
        assert_eq!(restored.retained_neuron_lineages(), original_lineages);
        assert_eq!(restored.encode(16_000_000).unwrap(), encoded);
    }

    #[test]
    fn subset_occurrence_advances_only_its_persistent_reached_neurons() {
        let first = crate::neuron_source_anchor::tests::exact_four_optical_episode();
        let subset = exact_two_of_four_optical_episode();
        let mut state = ResidentCognitiveFormationState::default();
        state
            .commit(state.prepare(&first, 16_000_000).unwrap())
            .unwrap();
        let predecessor = state.cohorts[0].state.clone();
        let lineages = state.retained_neuron_lineages();

        let prepared = state.prepare(&subset, 16_000_000).unwrap();
        assert_eq!(prepared.successor.cohorts.len(), 1);
        assert_eq!(prepared.successor.summary().complete_neuron_count, 4);
        assert_eq!(prepared.successor.retained_neuron_lineages(), lineages);
        let successor = &prepared.successor.cohorts[0].state;
        assert_eq!(successor.neurons()[2], predecessor.neurons()[2]);
        assert_eq!(successor.neurons()[3], predecessor.neurons()[3]);
        assert_ne!(successor.neurons()[0], predecessor.neurons()[0]);
        assert_ne!(successor.neurons()[1], predecessor.neurons()[1]);

        let encoded = state.encode_successor(&prepared, 16_000_000).unwrap();
        let restored = ResidentCognitiveFormationState::decode(&encoded, 16_000_000).unwrap();
        assert_eq!(restored.retained_neuron_lineages(), lineages);
        assert_eq!(restored.encode(16_000_000).unwrap(), encoded);
    }

    #[test]
    fn overlapping_occurrence_reuses_four_residents_and_creates_only_one_new_neuron() {
        let four = crate::neuron_source_anchor::tests::exact_four_optical_episode();
        let five = exact_five_optical_episode();
        let mut state = ResidentCognitiveFormationState::default();
        state
            .commit(state.prepare(&four, 16_000_000).unwrap())
            .unwrap();
        let predecessor_bytes = state.encode(16_000_000).unwrap();
        let cold_predecessor =
            ResidentCognitiveFormationState::decode(&predecessor_bytes, 16_000_000).unwrap();
        let predecessor_anatomy = state.cohorts[0].anatomy.clone();
        let predecessor_lineages = state.retained_neuron_lineages();

        RESIDENT_JOINT_FIELD_EVALUATIONS.with(|count| count.set(0));
        let warm = state.prepare(&five, 16_000_000).unwrap();
        RESIDENT_JOINT_FIELD_EVALUATIONS.with(|count| {
            assert_eq!(count.get(), five.joint_source_occurrences().len());
        });
        let cold = cold_predecessor.prepare(&five, 16_000_000).unwrap();
        assert_eq!(cold, warm);
        assert_eq!(warm.successor.cohorts.len(), 1);
        assert_eq!(warm.successor.summary().complete_neuron_count, 5);
        assert_eq!(warm.successor.next_lineage_ordinal, 6);
        assert_eq!(
            &warm.successor.cohorts[0].anatomy.neuron_anatomies()[..4],
            predecessor_anatomy.neuron_anatomies()
        );
        assert_eq!(
            &warm.successor.cohorts[0].anatomy.source_sites()[..4],
            predecessor_anatomy.source_sites()
        );
        assert_eq!(
            &warm.successor.retained_neuron_lineages()[..4],
            predecessor_lineages
        );
        assert_eq!(
            warm.successor.retained_neuron_lineages()[4],
            local_lineage(5)
        );
        let lineages = warm.successor.retained_neuron_lineages();
        assert!(lineages
            .iter()
            .enumerate()
            .all(|(index, lineage)| !lineages[..index].contains(lineage)));

        let encoded = state.encode_successor(&warm, 16_000_000).unwrap();
        let restored = ResidentCognitiveFormationState::decode(&encoded, 16_000_000).unwrap();
        assert_eq!(restored, warm.successor);
        assert_eq!(restored.encode(16_000_000).unwrap(), encoded);
    }

    #[test]
    fn crossed_compartment_occurrence_settles_two_resident_fluids_without_new_neurons() {
        let split = exact_split_four_optical_episode();
        let joint = crate::neuron_source_anchor::tests::exact_four_optical_episode();
        let left_seed = explicit_optical_seed_for_occurrence(&split, 0, 500);
        let right_seed = explicit_optical_seed_for_occurrence(&split, 1, 500);
        let mut state = ResidentCognitiveFormationState::from_developmental_electrical_seeds(vec![
            left_seed, right_seed,
        ])
        .unwrap();
        state
            .commit(state.prepare(&split, 16_000_000).unwrap())
            .unwrap();
        assert_eq!(state.cohorts.len(), 2);
        assert_eq!(state.summary().complete_neuron_count, 4);
        assert_eq!(state.next_lineage_ordinal, 5);
        let predecessor_anatomies = state
            .cohorts
            .iter()
            .map(|cohort| cohort.anatomy.clone())
            .collect::<Vec<_>>();
        let predecessor_lineages = state.retained_neuron_lineages();
        let predecessor_contacts = state
            .cohorts
            .iter()
            .map(|cohort| cohort.anatomy.contact_count())
            .collect::<Vec<_>>();
        let predecessor_mosaics = state.mosaics.clone();
        let predecessor_hippocampal = state.hippocampal;
        let predecessor_bytes = state.encode(16_000_000).unwrap();
        let cold_predecessor =
            ResidentCognitiveFormationState::decode(&predecessor_bytes, 16_000_000).unwrap();

        RESIDENT_JOINT_FIELD_EVALUATIONS.with(|count| count.set(0));
        let warm = state.prepare(&joint, 16_000_000).unwrap();
        RESIDENT_JOINT_FIELD_EVALUATIONS.with(|count| {
            assert_eq!(count.get(), joint.joint_source_occurrences().len());
        });
        let cold = cold_predecessor.prepare(&joint, 16_000_000).unwrap();
        assert_eq!(cold, warm);
        assert_eq!(warm.successor.cohorts.len(), 2);
        assert_eq!(warm.successor.summary().complete_neuron_count, 4);
        assert_eq!(warm.successor.next_lineage_ordinal, 5);
        assert_eq!(
            warm.successor.retained_neuron_lineages(),
            predecessor_lineages
        );
        assert_eq!(warm.successor.hippocampal, predecessor_hippocampal);
        for index in 0..2 {
            assert_eq!(
                warm.successor.cohorts[index].anatomy,
                predecessor_anatomies[index]
            );
            assert_eq!(
                warm.successor.cohorts[index].anatomy.contact_count(),
                predecessor_contacts[index]
            );
            assert_eq!(
                warm.successor.cohorts[index].state.recovery_fluid(),
                cold.successor.cohorts[index].state.recovery_fluid()
            );
        }
        assert_eq!(warm.successor.mosaics, predecessor_mosaics);

        let encoded = state.encode_successor(&warm, 16_000_000).unwrap();
        let restored = ResidentCognitiveFormationState::decode(&encoded, 16_000_000).unwrap();
        assert_eq!(restored, warm.successor);
        assert_eq!(restored.encode(16_000_000).unwrap(), encoded);
        assert_eq!(restored.cohorts.len(), 2);
        assert_eq!(
            restored.cohorts[0].state.recovery_fluid(),
            warm.successor.cohorts[0].state.recovery_fluid()
        );
        assert_eq!(
            restored.cohorts[1].state.recovery_fluid(),
            warm.successor.cohorts[1].state.recovery_fluid()
        );
    }

    #[test]
    fn unsupported_source_remains_unallocated_and_unclaimed() {
        let source = exact_episode();
        let mut state = ResidentCognitiveFormationState::default();
        let prepared = state.prepare(&source, 16_000_000).unwrap();
        assert_eq!(prepared.observation.cognitive_ordinal, 1);
        assert_eq!(prepared.observation.complete_neuron_count, 0);
        assert_eq!(prepared.observation.physically_transitioned_neuron_count, 0);
        assert_eq!(prepared.observation.complete_neuron_fractal_count, 0);
        assert!(!prepared.observation.trace_formed);
        assert!(prepared.observation.mosaic_formed.is_none());
        state.commit(prepared).unwrap();
        let encoded = state.encode(16_000_000).unwrap();
        let restored = ResidentCognitiveFormationState::decode(&encoded, 16_000_000).unwrap();
        assert_eq!(restored, state);
        assert_eq!(restored.summary().complete_neuron_count, 0);
        assert_eq!(restored.next_lineage_ordinal, 1);
        assert!(restored.dormant_lineage_seeds.is_empty());
        assert_eq!(restored.encode(16_000_000).unwrap(), encoded);
    }

    #[test]
    fn explicit_growth_dna_contacts_survive_restart_and_express_once() {
        let source = exact_four_single_optical_episode(0);
        let seed = explicit_optical_seed(&source, 1);
        let state =
            ResidentCognitiveFormationState::from_developmental_electrical_seeds(vec![seed])
                .unwrap();
        let unexpressed = state.encode(16_000_000).unwrap();
        let restored = ResidentCognitiveFormationState::decode(&unexpressed, 16_000_000).unwrap();
        assert_eq!(restored, state);
        assert_eq!(restored.unexpressed_electrical_seeds.len(), 1);

        let prepared = restored.prepare(&source, 16_000_000).unwrap();
        assert_eq!(prepared.successor.unexpressed_electrical_seeds.len(), 0);
        assert_eq!(prepared.successor.cohorts.len(), 1);
        assert_eq!(prepared.successor.cohorts[0].anatomy.neuron_count(), 4);
        assert_eq!(prepared.successor.cohorts[0].anatomy.contact_count(), 3);
        assert_eq!(prepared.observation.complete_neuron_fractal_count, 0);
        assert!(prepared.observation.mosaic_formed.is_none());

        let expressed = restored.encode_successor(&prepared, 16_000_000).unwrap();
        let cold = ResidentCognitiveFormationState::decode(&expressed, 16_000_000).unwrap();
        assert_eq!(cold, prepared.successor);
        assert_eq!(cold.cohorts[0].anatomy.contact_count(), 3);
        assert_eq!(cold.encode(16_000_000).unwrap(), expressed);
    }

    #[test]
    fn four_receptor_experience_emits_four_real_fractals() {
        let light = (0..4)
            .map(exact_four_single_optical_episode)
            .collect::<Vec<_>>();
        let dark = exact_four_dark_optical_episode();
        let seed = explicit_optical_seed(&light[0], 500);
        let mut state =
            ResidentCognitiveFormationState::from_developmental_electrical_seeds(vec![seed])
                .unwrap();
        let mut emitted = Vec::new();
        for source in light.iter().chain(std::iter::repeat(&dark).take(8)) {
            let prepared = state.prepare(source, 16_000_000).unwrap();
            assert!(prepared.observation.mosaic_formed.is_none());
            assert_eq!(prepared.observation.mosaic_count, 0);
            emitted.extend(prepared.observation.emitted_neuron_fractals.clone());
            state.commit(prepared).unwrap();
        }
        assert_eq!(emitted.len(), 4);
        assert_eq!(
            emitted
                .iter()
                .map(|fractal| fractal.neuron_lineage)
                .collect::<Vec<_>>(),
            [
                local_lineage(1),
                local_lineage(2),
                local_lineage(3),
                local_lineage(4)
            ]
        );
        assert!(state.cohorts[0].pending_experience.is_none());
        assert!(state.cohorts[0].retained_experience.is_some());
        let encoded = state.encode(16_000_000).unwrap();
        let restored = ResidentCognitiveFormationState::decode(&encoded, 16_000_000).unwrap();
        assert_eq!(restored, state);
        assert!(restored.cohorts[0].retained_experience.is_some());
        assert_eq!(restored.encode(16_000_000).unwrap(), encoded);

        let partial = exact_four_partial_optical_episode();
        let recurrence_sources = std::iter::once(&partial)
            .chain(std::iter::repeat(&dark).take(8))
            .collect::<Vec<_>>();
        let recurrence_fields = recurrence_sources
            .iter()
            .map(|source| prepare_complete_joint_field_admitted_fixture(source, 0).unwrap())
            .collect::<Vec<_>>();
        let cohort = &restored.cohorts[0];
        let catalysts = cohort
            .anatomy
            .neuron_anatomies()
            .iter()
            .map(|anatomy| vec![0; anatomy.recovery_anatomy().psi_lane_count()].into_boxed_slice())
            .collect::<Vec<_>>();
        let optical = exact_optical_receptor_anatomy().unwrap();
        let recurrence_inputs = recurrence_sources
            .iter()
            .zip(&recurrence_fields)
            .map(|(source, shared)| {
                four_optical_interval(source, shared, &cohort.anatomy, &catalysts, &optical)
            })
            .collect::<Vec<_>>();
        assert_eq!(restored.summary().mosaic_count, 0);
        let mut integrated = restored.clone();
        let mut hippocampal_cold = HippocampalColdStore::default();
        let mut formed = Vec::new();
        RESIDENT_ACTUAL_RECURRENCE_SETTLEMENTS.with(|count| count.set(0));
        for source in &recurrence_sources {
            let mut prepared = integrated
                .prepare_admitted_with_hippocampal_cold(
                    &admitted_fixture_episode(source),
                    &hippocampal_cold,
                    16_000_000,
                )
                .unwrap();
            if let Some(receipt) = prepared.observation.mosaic_formed {
                assert_eq!(prepared.observation.mosaic_count, 1);
                assert!(prepared.observation.activations.is_empty());
                assert_eq!(prepared.observation.partial_cue_reassembly_count(), 1);
                let unchanged_resident = integrated.clone();
                let unchanged_cold = hippocampal_cold.clone();
                let mut premature_resident = integrated.clone();
                assert_eq!(
                    premature_resident.commit(prepared.clone()),
                    Err(FormationError::HippocampalPublicationRequired)
                );
                assert_eq!(premature_resident, unchanged_resident);
                assert_eq!(hippocampal_cold, unchanged_cold);
                formed.push(receipt);
            }
            let interval_bytes = integrated
                .publish_hippocampal_and_encode_successor(
                    &mut prepared,
                    &mut hippocampal_cold,
                    16_000_000,
                )
                .unwrap();
            integrated.commit(prepared).unwrap();
            integrated =
                ResidentCognitiveFormationState::decode(&interval_bytes, 16_000_000).unwrap();
            assert_eq!(integrated.encode(16_000_000).unwrap(), interval_bytes);
        }
        RESIDENT_ACTUAL_RECURRENCE_SETTLEMENTS.with(|count| {
            assert_eq!(count.get(), recurrence_sources.len());
        });
        assert_eq!(formed.len(), 1);
        assert_eq!(integrated.summary().mosaic_count, 1);
        assert_eq!(integrated.mosaics.len(), 1);
        assert!(integrated.cohorts[0].pending_recurrence.is_none());
        let integrated_bytes = integrated.encode(16_000_000).unwrap();
        let cold_integrated =
            ResidentCognitiveFormationState::decode(&integrated_bytes, 16_000_000).unwrap();
        assert_eq!(cold_integrated, integrated);
        hippocampal_cold
            .validate_checkpoint(cold_integrated.hippocampal.checkpoint())
            .unwrap();
        let restored_episode = hippocampal_cold
            .resolve_episode(
                cold_integrated
                    .hippocampal
                    .checkpoint()
                    .latest_episode()
                    .unwrap(),
            )
            .unwrap();
        validate_typed_hippocampal_episode(&cold_integrated.cohorts[0].anatomy, &restored_episode)
            .unwrap();

        let five_receptor_occurrence = exact_five_optical_episode();
        let predecessor_anatomy = integrated.cohorts[0].anatomy.clone();
        let predecessor_lineages = integrated.retained_neuron_lineages();
        let predecessor_mosaics = integrated.mosaics.clone();
        RESIDENT_JOINT_FIELD_EVALUATIONS.with(|count| count.set(0));
        let warm_growth = integrated
            .prepare_admitted_with_hippocampal_cold(
                &admitted_fixture_episode(&five_receptor_occurrence),
                &hippocampal_cold,
                16_000_000,
            )
            .unwrap();
        RESIDENT_JOINT_FIELD_EVALUATIONS.with(|count| {
            assert_eq!(
                count.get(),
                five_receptor_occurrence.joint_source_occurrences().len()
            );
        });
        let cold_growth = cold_integrated
            .prepare_admitted_with_hippocampal_cold(
                &admitted_fixture_episode(&five_receptor_occurrence),
                &hippocampal_cold,
                16_000_000,
            )
            .unwrap();
        assert_eq!(cold_growth, warm_growth);
        assert_eq!(warm_growth.successor.cohorts.len(), 1);
        assert_eq!(warm_growth.successor.summary().complete_neuron_count, 5);
        assert_eq!(warm_growth.successor.next_lineage_ordinal, 6);
        assert_eq!(
            &warm_growth.successor.cohorts[0].anatomy.neuron_anatomies()[..4],
            predecessor_anatomy.neuron_anatomies()
        );
        assert_eq!(
            &warm_growth.successor.cohorts[0].anatomy.source_sites()[..4],
            predecessor_anatomy.source_sites()
        );
        assert_eq!(
            &warm_growth.successor.retained_neuron_lineages()[..4],
            predecessor_lineages
        );
        assert_eq!(
            warm_growth.successor.retained_neuron_lineages()[4],
            local_lineage(5)
        );
        let successor_lineages = warm_growth.successor.retained_neuron_lineages();
        assert!(successor_lineages
            .iter()
            .enumerate()
            .all(|(index, lineage)| { !successor_lineages[..index].contains(lineage) }));
        assert_eq!(warm_growth.successor.mosaics, predecessor_mosaics);
        let mut extended = integrated.clone();
        let mut extended_cold = hippocampal_cold.clone();
        let mut warm_growth = warm_growth;
        let extended_bytes = extended
            .publish_hippocampal_and_encode_successor(
                &mut warm_growth,
                &mut extended_cold,
                16_000_000,
            )
            .unwrap();
        extended.commit(warm_growth).unwrap();
        let cold_extended =
            ResidentCognitiveFormationState::decode(&extended_bytes, 16_000_000).unwrap();
        assert_eq!(cold_extended, extended);
        assert_eq!(cold_extended.encode(16_000_000).unwrap(), extended_bytes);
        assert_eq!(cold_extended.summary().complete_neuron_count, 5);
        assert_eq!(cold_extended.summary().mosaic_count, 1);
        extended_cold
            .validate_checkpoint(cold_extended.hippocampal.checkpoint())
            .unwrap();

        let mut progressive = integrated.clone();
        let mut progressive_cold = hippocampal_cold.clone();
        let mut relation_events = 0usize;
        let mut tapestry_events = 0usize;
        let mut deeper_tapestry_events = 0usize;
        for cue_index in [1usize, 2, 2, 2] {
            let cue = exact_four_single_optical_episode(cue_index);
            for source in std::iter::once(&cue).chain(std::iter::repeat(&dark).take(8)) {
                let mut prepared = progressive
                    .prepare_admitted_with_hippocampal_cold(
                        &admitted_fixture_episode(source),
                        &progressive_cold,
                        16_000_000,
                    )
                    .unwrap();
                relation_events += prepared.observation.dynamic_formation_relation_count;
                tapestry_events += prepared.observation.tapestry_activity_count;
                deeper_tapestry_events += prepared.observation.deeper_tapestry_activity_count;
                let successor = progressive
                    .publish_hippocampal_and_encode_successor(
                        &mut prepared,
                        &mut progressive_cold,
                        16_000_000,
                    )
                    .unwrap();
                progressive.commit(prepared).unwrap();
                progressive =
                    ResidentCognitiveFormationState::decode(&successor, 16_000_000).unwrap();
            }
        }
        assert_eq!(relation_events, 1);
        assert_eq!(tapestry_events, 1);
        assert_eq!(deeper_tapestry_events, 1);
        assert_eq!(progressive.summary().mosaic_count, 3);
        progressive_cold
            .validate_checkpoint(progressive.hippocampal.checkpoint())
            .unwrap();

        let mut generative = integrated.clone();
        let mut generative_cold = hippocampal_cold.clone();
        let mut generative_recombination_events = 0usize;
        let generative_cues = [
            exact_four_single_optical_episode(1),
            exact_four_single_optical_episode(2),
            exact_four_single_optical_episode(2),
            exact_four_single_optical_episode(3),
            exact_four_single_optical_episode(3),
            exact_four_subset_optical_episode(0b0011),
        ];
        for cue in &generative_cues {
            for source in std::iter::once(cue).chain(std::iter::repeat(&dark).take(8)) {
                let mut prepared = generative
                    .prepare_admitted_with_hippocampal_cold(
                        &admitted_fixture_episode(source),
                        &generative_cold,
                        16_000_000,
                    )
                    .unwrap();
                generative_recombination_events +=
                    prepared.observation.generative_recombination_count;
                let successor = generative
                    .publish_hippocampal_and_encode_successor(
                        &mut prepared,
                        &mut generative_cold,
                        16_000_000,
                    )
                    .unwrap();
                generative.commit(prepared).unwrap();
                generative =
                    ResidentCognitiveFormationState::decode(&successor, 16_000_000).unwrap();
            }
        }
        assert_eq!(generative_recombination_events, 1);
        assert_eq!(generative.summary().mosaic_count, 5);
        generative_cold
            .validate_checkpoint(generative.hippocampal.checkpoint())
            .unwrap();

        let mut damaged_source = restored_episode.clone();
        let mut damaged_source_body = damaged_source.source_body.to_vec();
        *damaged_source_body.last_mut().unwrap() ^= 1;
        damaged_source.source_body = damaged_source_body.into_boxed_slice();
        assert!(validate_typed_hippocampal_episode(
            &cold_integrated.cohorts[0].anatomy,
            &damaged_source,
        )
        .is_err());
        let mut damaged_mosaic = restored_episode.clone();
        let mut damaged_mosaic_body = damaged_mosaic.physical_mosaic.to_vec();
        *damaged_mosaic_body.last_mut().unwrap() ^= 1;
        damaged_mosaic.physical_mosaic = damaged_mosaic_body.into_boxed_slice();
        assert!(validate_typed_hippocampal_episode(
            &cold_integrated.cohorts[0].anatomy,
            &damaged_mosaic,
        )
        .is_err());
        let mut trailing_original = restored_episode.clone();
        let mut original_body = trailing_original.original_transition_evidence.to_vec();
        original_body.push(0);
        trailing_original.original_transition_evidence = original_body.into_boxed_slice();
        assert!(validate_typed_hippocampal_episode(
            &cold_integrated.cohorts[0].anatomy,
            &trailing_original,
        )
        .is_err());
        let mut trailing_recurrent = restored_episode.clone();
        let mut recurrent_body = trailing_recurrent.recurrent_transition_evidence.to_vec();
        recurrent_body.push(0);
        trailing_recurrent.recurrent_transition_evidence = recurrent_body.into_boxed_slice();
        assert!(validate_typed_hippocampal_episode(
            &cold_integrated.cohorts[0].anatomy,
            &trailing_recurrent,
        )
        .is_err());
        let mut mismatched_member = restored_episode.clone();
        mismatched_member.participants[0].lineage = [255; 16];
        assert!(validate_typed_hippocampal_episode(
            &cold_integrated.cohorts[0].anatomy,
            &mismatched_member,
        )
        .is_err());
        assert_eq!(cold_integrated.summary().mosaic_count, 1);
        assert!(ResidentCognitiveFormationState::decode(
            &integrated_bytes[..integrated_bytes.len() - 1],
            16_000_000,
        )
        .is_err());
        let mut duplicate = integrated.clone();
        duplicate.mosaics =
            vec![duplicate.mosaics[0].clone(), duplicate.mosaics[0].clone()].into_boxed_slice();
        assert!(matches!(
            duplicate.encode(16_000_000),
            Err(FormationError::NoncanonicalState)
        ));

        let retained = restored.cohorts[0].retained_experience.as_ref().unwrap();
        let mut unlearned = ResidentCognitiveFormationState {
            generation: restored.generation,
            next_lineage_ordinal: restored.next_lineage_ordinal,
            unexpressed_electrical_seeds: Box::new([]),
            dormant_lineage_seeds: Box::new([]),
            cohorts: vec![ResidentReachedCohort {
                anatomy: restored.cohorts[0].anatomy.clone(),
                state: retained.pre_experience_quiescent.clone(),
                pending_experience: None,
                retained_experience: None,
                pending_recurrence: None,
            }]
            .into_boxed_slice(),
            mosaics: Box::new([]),
            hippocampal: ResidentHippocampalIndex::default(),
        };
        for source in &recurrence_sources {
            let prepared = unlearned.prepare(source, 16_000_000).unwrap();
            assert!(prepared.observation.mosaic_formed.is_none());
            assert_eq!(prepared.observation.mosaic_count, 0);
            unlearned.commit(prepared).unwrap();
        }
        assert_eq!(unlearned.summary().mosaic_count, 0);

        let evidence = cohort.retained_experience.as_ref().unwrap();
        let learned = cohort.state.clone();
        let learned_recovery = learned.recovery_fluid().physical_parts();
        let original_fractals = evidence
            .pre_experience_quiescent
            .neurons()
            .iter()
            .zip(learned.neurons())
            .map(|(prior, successor)| sparse_physical_state_delta(prior, successor).unwrap())
            .collect::<Vec<_>>();
        let original = crate::reached_neuron_cohort::ReachedCohortPostExperienceSettlement {
            quiescent: crate::reached_neuron_cohort::QuiescentReachedCohortState::from_state(
                learned.clone(),
            ),
            neuron_fractals: original_fractals.into_boxed_slice(),
            electrical_contact_was_active: evidence
                .active_electrical_contacts
                .iter()
                .any(|active| *active),
            gate_work_perturbed_neurons: evidence.gate_work_perturbed_neurons.clone(),
            active_electrical_contacts: evidence.active_electrical_contacts.clone(),
        };
        assert_eq!(
            evidence.active_electrical_contacts.as_ref(),
            &[true, true, true]
        );
        let recurrence = crate::reached_neuron_cohort::settle_reached_cohort_recurrence(
            &cohort.anatomy,
            &learned,
            &recurrence_inputs,
        )
        .unwrap();
        let recurrence_recovery = recurrence.successor.recovery_fluid().physical_parts();
        let recovered_fuel = learned_recovery.0 - recurrence_recovery.0;
        assert!(recovered_fuel > 0);
        assert_eq!(recurrence_recovery.1 - learned_recovery.1, recovered_fuel);
        assert_eq!(recurrence_recovery.2 - learned_recovery.2, recovered_fuel);
        assert_eq!(
            learned_recovery.0 + learned_recovery.1,
            recurrence_recovery.0 + recurrence_recovery.1
        );
        let control = crate::reached_neuron_cohort::settle_reached_cohort_recurrence(
            &cohort.anatomy,
            &evidence.pre_experience_quiescent,
            &recurrence_inputs,
        )
        .unwrap();
        let learned_bytes = encode_reached_cohort_state(&cohort.anatomy, &learned).unwrap();
        let cold_learned = decode_reached_cohort_state(&cohort.anatomy, &learned_bytes).unwrap();
        let cold_recurrence = crate::reached_neuron_cohort::settle_reached_cohort_recurrence(
            &cohort.anatomy,
            &cold_learned,
            &recurrence_inputs,
        )
        .unwrap();
        assert_eq!(cold_recurrence, recurrence);
        assert_ne!(recurrence.successor, control.successor);
        assert_eq!(
            recurrence.active_electrical_contacts.as_ref(),
            &[true, true, true]
        );
        let mosaic =
            crate::physical_mosaic::admit_physical_mosaic(&cohort.anatomy, &original, &recurrence)
                .unwrap();
        let mut expected_lineages = cohort.anatomy.neuron_lineages().to_vec();
        expected_lineages.sort_unstable();
        assert_eq!(mosaic.member_lineages(), expected_lineages);
        assert_eq!(mosaic.partial_cue_lineages(), &expected_lineages[..1]);
        assert_eq!(mosaic.original_bonds().len(), 3);
        assert_eq!(mosaic.recurrence_bonds().len(), 3);
    }

    #[test]
    fn exact_optical_occurrence_physically_changes_the_resident_cell() {
        let source = exact_optical_episode();
        let genesis = ResidentCognitiveFormationState::default();
        let genesis_bytes = genesis.encode(16_000_000).unwrap();
        let prepared = genesis.prepare(&source, 16_000_000).unwrap();
        assert_eq!(prepared.observation.complete_neuron_count, 1);
        assert_eq!(prepared.observation.physically_transitioned_neuron_count, 1);
        assert_eq!(prepared.observation.complete_neuron_fractal_count, 0);
        assert!(prepared.observation.emitted_neuron_fractals.is_empty());
        let successor_bytes = genesis.encode_successor(&prepared, 16_000_000).unwrap();
        assert_ne!(successor_bytes, genesis_bytes);
        let restored =
            ResidentCognitiveFormationState::decode(&successor_bytes, 16_000_000).unwrap();
        assert_eq!(restored.encode(16_000_000).unwrap(), successor_bytes);
    }

    #[test]
    fn real_dark_successors_emit_only_the_post_quiescence_fractal() {
        let light = exact_optical_episode();
        let dark = exact_dark_optical_episode();
        let mut state = ResidentCognitiveFormationState::default();
        let light_transition = state.prepare(&light, 16_000_000).unwrap();
        assert_eq!(
            light_transition.observation.complete_neuron_fractal_count,
            0
        );
        state.commit(light_transition).unwrap();

        let mid_experience_bytes = state.encode(16_000_000).unwrap();
        let mut restored =
            ResidentCognitiveFormationState::decode(&mid_experience_bytes, 16_000_000).unwrap();
        assert_eq!(restored, state);

        let first_dark = restored.prepare(&dark, 16_000_000).unwrap();
        assert_eq!(first_dark.observation.complete_neuron_fractal_count, 0);
        restored.commit(first_dark).unwrap();

        let second_dark = restored.prepare(&dark, 16_000_000).unwrap();
        assert_eq!(second_dark.observation.complete_neuron_fractal_count, 1);
        assert_eq!(second_dark.observation.emitted_neuron_fractals.len(), 1);
        assert_eq!(
            second_dark.observation.emitted_neuron_fractals[0]
                .delta
                .exact_delta(crate::complete_neuron::PhysicalStateCoordinate::PlasticRestLength),
            Some(crate::complete_neuron::ExactPhysicalStateDelta::Rational(
                crate::exact_rational::ExactRational::new(1, 3).unwrap()
            ))
        );
    }

    #[test]
    fn typed_vestibular_source_persists_one_specialized_neuron_then_emits_after_quiescence() {
        let canal_anatomy =
            CanalAnatomy::new(6, 13_200, PositiveRatio::new(25, 1).unwrap()).unwrap();
        let bundle_anatomy = LocalCupulaBundleAnatomy::new(2, 5, 20_000).unwrap();
        let receptor_anatomy = FunctionalVestibularAnatomy::new(
            canal_anatomy,
            bundle_anatomy,
            TipLinkInsertionGeometry::new(500).unwrap(),
            GatingSpringEnergyAnatomy::new(
                ExactRational::integer(1),
                ExactRational::integer(4),
                ExactRational::integer(2),
                ExactRational::integer(8),
            )
            .unwrap(),
        )
        .unwrap();
        let cold = HippocampalColdStore::default();
        let mut state = ResidentCognitiveFormationState::default();
        let predecessor_body = YawBodyState::new(0).unwrap();
        let body = settle_signed_yaw_actuation(
            predecessor_body,
            SignedYawActuation::new(64, WORLD_MECHANICAL_TICK_MICROSECONDS).unwrap(),
        )
        .unwrap();
        let reached = settle_reached_vestibular_bundle_tick(
            canal_anatomy,
            CanalState::at_rest(),
            body.trajectory.as_slice()[0],
            bundle_anatomy,
        )
        .unwrap();
        let ingress = prepare_resident_vestibular_ingress(
            0,
            predecessor_body,
            body.successor,
            reached,
            &receptor_anatomy,
        )
        .unwrap();
        let stimulating = state
            .prepare_vestibular_with_hippocampal_cold(&ingress, &cold, 16_000_000)
            .unwrap();
        assert_eq!(stimulating.observation.complete_neuron_count, 1);
        assert_eq!(
            stimulating.observation.physically_transitioned_neuron_count,
            1
        );
        assert!(stimulating.observation.emitted_neuron_fractals.is_empty());
        state.commit(stimulating).unwrap();
        assert_eq!(state.cohorts.len(), 1);
        assert_eq!(state.cohorts[0].anatomy.neuron_count(), 1);
        assert_eq!(
            state.cohorts[0].anatomy.neuron_anatomies()[0].gate_dissipation_capacity_quanta(),
            receptor_anatomy.gate_dissipation_capacity_quanta()
        );

        let encoded = state.encode(16_000_000).unwrap();
        state = ResidentCognitiveFormationState::decode(&encoded, 16_000_000).unwrap();
        let lineage = state.cohorts[0].anatomy.neuron_lineages()[0];
        let mut body_state = body.successor;
        let mut canal_state = reached.successor_canal;
        let mut emitted = None;
        for source_tick in 1..=u64::try_from(WORLD_MAX_ACTION_TICKS).unwrap() {
            let resting_body = settle_signed_yaw_actuation(
                body_state,
                SignedYawActuation::new(0, WORLD_MECHANICAL_TICK_MICROSECONDS).unwrap(),
            )
            .unwrap();
            let resting_reached = settle_reached_vestibular_bundle_tick(
                canal_anatomy,
                canal_state,
                resting_body.trajectory.as_slice()[0],
                bundle_anatomy,
            )
            .unwrap();
            let resting_ingress = prepare_resident_vestibular_ingress(
                source_tick,
                body_state,
                resting_body.successor,
                resting_reached,
                &receptor_anatomy,
            )
            .unwrap();
            let prepared = state
                .prepare_vestibular_with_hippocampal_cold(&resting_ingress, &cold, 16_000_000)
                .unwrap();
            let observation = prepared.observation.clone();
            state.commit(prepared).unwrap();
            assert_eq!(state.cohorts[0].anatomy.neuron_lineages(), &[lineage]);
            assert_eq!(state.summary().complete_neuron_count, 1);
            body_state = resting_body.successor;
            canal_state = resting_reached.successor_canal;
            if !observation.emitted_neuron_fractals.is_empty() {
                emitted = Some(observation.emitted_neuron_fractals);
                break;
            }
        }
        let emitted = emitted.expect("exact vestibular recovery did not reach quiescence");
        assert_eq!(emitted.len(), 1);
        assert_eq!(emitted[0].neuron_lineage, lineage);
    }

    #[test]
    fn retired_false_or_empty_cognitive_state_cannot_return() {
        for magic in [
            b"GLCOG003",
            b"GLCOG004",
            b"GLCOG005",
            b"GLCOG006",
            b"GLCOG007",
            b"GLCOG008",
            b"GLCOG009",
            b"GLCOG010",
        ] {
            let mut retired = Vec::from(magic.as_slice());
            retired.extend_from_slice(&4u16.to_le_bytes());
            assert_eq!(
                ResidentCognitiveFormationState::decode(&retired, 1_000_000),
                Err(FormationError::RetiredCognitiveState)
            );
        }
    }
}
