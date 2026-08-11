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

use crate::auditory_receptor_work::{
    derive_auditory_receptor_sample_range_work, derive_auditory_receptor_work,
    quantize_auditory_delivery, AuditoryReceptorAnatomy, AuditoryReceptorWorkError,
    COCHLEAR_BAND_PRESSURE_QUANTITY, COCHLEAR_REFERENCE_PRESSURE_UNIT,
};
use crate::complete_neuron::{
    gate_opening_quantum_window_with_psi, gate_population_opening_schedule_with_psi,
    sparse_physical_state_delta, sparse_retained_physical_state_delta, DnaExpressionContact,
    GateWorkOccurrence, NeuronIntervalInput, RecoveryContact, SparsePhysicalStateDelta,
};
use crate::declared_geometric_anatomy::{declared_neuron_territory, DeclaredNeuronPlace};
use crate::developmental_electrical_anatomy::{
    DevelopmentalElectricalError, DevelopmentalElectricalSeed,
};
use crate::developmental_resting_population::{
    DevelopmentalRestingPopulation, DevelopmentalRestingPopulationError, MaterializedRestingNeuron,
};
use crate::elementary_charge_membrane::{settle_membrane_elementary_charges, MembraneChargeError};
use crate::exact_rational::ExactRational;
use crate::hippocampal_sparse_path::{HippocampalError, ResidentHippocampalIndex};
use crate::joint_source_episode::NativeJointSourceEpisode;
#[cfg(test)]
use crate::joint_uf_neuron_boundary::prepare_complete_joint_field_admitted_fixture;
use crate::joint_uf_neuron_boundary::{
    bind_neuron_perspective, prepare_complete_joint_field_from_evaluated,
    prepare_complete_joint_field_with_admission, required_mathloom_positions,
    JointNeuronBoundaryError,
};
#[cfg(test)]
use crate::joint_uf_source_adapter::admitted_fixture_episode;
use crate::joint_uf_source_adapter::EvaluatedJointSourceOccurrence;
use crate::joint_uf_source_adapter::{AdmittedJointSourceEpisode, JointUfSourceError};
use crate::joint_uf_v1_4::{
    self, JointIntersampleLaw, JointUfCoordinateBounds, JointUfInput, JointUfPhysicalBounds,
};
use crate::metabolic_feeding::MetabolicError;
use crate::neuron_source_anchor::{
    bind_neuron_source_anchor, encode_neuron_source_site, NeuronSourceSite, PhysicalSourceSense,
};
use crate::optical_receptor_work::{
    derive_optical_receptor_sample_range_work, quantize_optical_delivery,
    quantize_optical_population_delivery, OpticalReceptorAnatomy, OpticalReceptorWorkError,
    RETINAL_REFERENCE_IRRADIANCE_UNIT, RETINAL_SPECTRAL_IRRADIANCE_QUANTITY,
};
use crate::physical_mosaic::{
    admit_physical_mosaic, admit_physical_mosaic_original, connected_members,
    decode_admitted_physical_mosaic_for_topology, encode_admitted_physical_mosaic,
    encode_admitted_physical_mosaic_for_topology, prove_physical_mosaic_recurrence,
    AdmittedPhysicalMosaic, PhysicalMosaicCodecError, PhysicalMosaicError,
    StablePhysicalBondReference,
};
use crate::reached_neuron_cohort::{
    decode_reached_cohort_cell, decode_reached_cohort_state, decode_reached_cohort_state_delta,
    encode_reached_cohort_cell, encode_reached_cohort_cell_v5,
    encode_reached_cohort_cell_v5_with_contact_plasticity, encode_reached_cohort_cell_v6,
    encode_reached_cohort_state, encode_reached_cohort_state_delta,
    encode_reached_cohort_state_delta_v1, encode_reached_cohort_state_v4,
    encode_reached_cohort_state_v5,
    expand_legacy_sight_channel_populations as expand_reached_sight_channel_populations,
    extend_reached_cohort_cells, extend_reached_cohort_contacts,
    extend_reached_cohort_positional_fabrics, extend_reached_cohort_state_with_genesis,
    legacy_sight_channel_populations_require_expansion, reached_cohort_energy_state,
    reached_cohort_state_content_digest, reached_cohort_state_v4_content_digest,
    settle_reached_cohort_dark_rest, settle_reached_cohort_interval,
    widen_reached_cohort_state_contacts, ReachedCohortAnatomy, ReachedCohortEnergyState,
    ReachedCohortError, ReachedCohortIntervalInput, ReachedCohortMetabolicObservation,
    ReachedCohortPostExperienceSettlement, ReachedCohortRecurrenceSettlement, ReachedCohortState,
    ReachedNeuronGenesisCell, ReachedNeuronMount, RestReachedCohortState,
};
use crate::receptor_quantum_delivery::big_to_exact_rational;
use crate::resident_electrical_fabric::ResidentElectricalFabric;
use crate::resident_receptor_transition::ResidentVestibularIngress;
use crate::sha256::sha256;
use crate::sparse_electrical_contact::{
    settle_sparse_electrical_transfers, ElectricalContactAnatomy, ElectricalContactState,
    ElectricalContactTransition, SparseElectricalAnatomy, SparseElectricalError,
    SparseElectricalState, SparseElectricalTransferSettlement,
};
use crate::tactile_receptor_work::{
    derive_tactile_receptor_sample_range_work, derive_tactile_receptor_work,
    quantize_tactile_delivery, TactileReceptorAnatomy, TactileReceptorWorkError,
    CONTACT_REFERENCE_OCCUPANCY_UNIT, CONTACT_SITE_OCCUPANCY_QUANTITY,
};
use crate::vestibular_neuron_path::{
    create_single_vertex_vestibular_reached_cohort,
    specialize_single_vertex_vestibular_reached_cohort, FunctionalVestibularError,
};
use crate::virtual_material_neuron_genesis::{
    create_quiescent_virtual_material_neuron, create_virtual_material_neuron,
    definitive_virtual_carriers_per_compartment, reach_quiescent_virtual_material_neuron,
    VirtualMaterialGenesisError,
};
use crate::virtual_vestibular_canal::WORLD_MECHANICAL_TICK_MICROSECONDS;
use num_bigint::BigInt;
use num_rational::BigRational;
use num_traits::{ToPrimitive, Zero};
use std::fmt;
use std::sync::Arc;

const MAGIC: &[u8; 8] = b"GLCOG012";
const VERSION: u16 = 12;
const MAGIC_V13: &[u8; 8] = b"GLCOG013";
const VERSION_V13: u16 = 13;
const MAGIC_V14: &[u8; 8] = b"GLCOG014";
const VERSION_V14: u16 = 14;
const MAGIC_V15: &[u8; 8] = b"GLCOG015";
const VERSION_V15: u16 = 15;
const MAGIC_V16: &[u8; 8] = b"GLCOG016";
const VERSION_V16: u16 = 16;
const LINEAGE_DOMAIN: &[u8; 8] = b"GLNLINE1";
/// Existing authored developmental-contact material shared by the retinal,
/// cochlear, tactile, and growth-DNA paths.  Internal specialization reuses
/// that exact physical contact; it is not a fitted learning coefficient.
const DEVELOPMENTAL_CONTACT_CONDUCTANCE_PICOSIEMENS: i128 = 500;
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
const CURRENT_FIXED_BYTES: usize = FIXED_BYTES + (2 * std::mem::size_of::<u64>());
const EXPERIENCE_MAGIC: &[u8; 8] = b"GLEXP01\0";
const EXPERIENCE_V2_MAGIC: &[u8; 8] = b"GLEXP02\0";
const EXPERIENCE_V3_MAGIC: &[u8; 8] = b"GLEXP03\0";
const EXPERIENCE_V4_MAGIC: &[u8; 8] = b"GLEXP04\0";
const EXPERIENCE_V5_MAGIC: &[u8; 8] = b"GLEXP05\0";
const RECURRENCE_MAGIC: &[u8; 8] = b"GLREC02\0";
const ENDOGENOUS_RECURRENCE_MAGIC: &[u8; 8] = b"GLREC03\0";
const PHYSICAL_RECURRENCE_MAGIC: &[u8; 8] = b"GLREC04\0";
const ENDOGENOUS_PHYSICAL_RECURRENCE_MAGIC: &[u8; 8] = b"GLREC05\0";
const EXCITATION_RECURRENCE_MAGIC: &[u8; 8] = b"GLREC06\0";
const ENDOGENOUS_EXCITATION_RECURRENCE_MAGIC: &[u8; 8] = b"GLREC07\0";
/// Wrapper magic for a retained mosaic reference that carries nonzero
/// reinforcement/relation counts (memory law R3, ratified 2026-08-06).
/// Codec precedent GLEXP02→GLEXP03: the wrapper appears ONLY when the new
/// state differs from the historical default (both counts zero), so every
/// pre-law body and every zero-count reference keeps a byte-identical
/// receipt.
const RETAINED_MOSAIC_COUNTS_MAGIC: &[u8; 8] = b"GLMRC01\0";
const EVIDENCE_DIGEST_BYTES: usize = 32;

/// Which persisted cognitive-image layout a body carries. Historical layouts
/// remain readable at the explicit one-way migration boundary; every ordinary
/// encode emits V15, whose additional field carries the compact developmental
/// resting population.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
enum CognitiveCodecFormat {
    V12,
    V13,
    V14,
    V15,
    V16,
}

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
    /// Declared source-independent cells that remain at exact quiescent rest.
    /// They did not receive the current field and are not included in
    /// `complete_neuron_count`.
    pub(crate) resting_neuron_count: usize,
    pub(crate) physically_transitioned_neuron_count: usize,
    pub(crate) complete_neuron_fractal_count: usize,
    pub(crate) emitted_neuron_fractals: Vec<EmittedNeuronFractal>,
    pub(crate) partial_cue_reassembly_count: usize,
    pub(crate) endogenous_partial_cue_reassembly_count: usize,
    /// Total mosaic-of-mosaics relation events recorded against the retained
    /// formations (memory law R1, overlap branch; self-ratified 2026-08-06 by the overnight session, NO filed instrument — flagged 2026-08-07, awaiting Joe's actual ruling):
    /// each recorded reassembly whose member set overlapped a retained
    /// formation without equalling it counts once per overlapped formation.
    /// Derived from the retained per-mosaic counts, never invented here.
    pub(crate) mosaic_of_mosaics_count: usize,
    /// Metabolic facts of this transition (minimal feeding metabolism,
    /// authorized 2026-08-05).  Every one of these is a settled physical
    /// quantity, including the demands the body could NOT meet: an exhausted
    /// ledger reports itself here instead of succeeding silently.
    pub(crate) rest_recovered_neuron_count: usize,
    pub(crate) rest_drained_dissipation_quanta: u128,
    pub(crate) unmet_dissipation_quanta: u128,
    pub(crate) membrane_returned_elementary_charges: i128,
    pub(crate) membrane_unreturned_elementary_charges: i128,
    pub(crate) metabolic_fuel_quanta: u128,
    pub(crate) nutrition_regenerated_fuel_quanta: u128,
    pub(crate) nutrition_unabsorbed_waste_quanta: u128,
    pub(crate) nutrition_vented_heat_quanta: u128,
    pub(crate) energy: ReachedCohortEnergyState,
}

impl CognitiveFormationObservation {
    pub(crate) fn partial_cue_reassembly_count(&self) -> usize {
        self.partial_cue_reassembly_count
    }

    pub(crate) fn endogenous_partial_cue_reassembly_count(&self) -> usize {
        self.endogenous_partial_cue_reassembly_count
    }
}

// THE DYNAMIC-FORMATION CLASSIFIER IS DELETED, NOT REPLACED.
//
// `observe_dynamic_formation` stood here.  It was the ONLY consumer of the
// hippocampal cold archive: per participating neuron it walked four archived
// postings, decoded each referenced episode's mosaic, and classified the
// current reassembly as a relation / tapestry / deeper tapestry / generative
// recombination.  With the archive retired it has no input, and it cannot be
// rebuilt from her body.  The reasons, stated rather than worked around:
//
//   * It is TEMPORAL and PER-PARTICIPANT.  It needed, for each member neuron,
//     the ORDERED last four episodes that neuron took part in, grouped by
//     depth, and it compared "how many participants have a k-th prior episode"
//     against the current participant count.  Her retained formations
//     (`mosaics`) are a DEDUPLICATED SET with no ordering and no per-neuron
//     history: under memory laws R1-R3 a re-derived formation replaces its
//     reference in place rather than appending, which is exactly why her
//     memory count stays flat.  No body fact means "the k-th prior episode of
//     neuron N", so no faithful reconstruction exists.
//   * Its tapestry, deeper-tapestry and generative outputs all turn on
//     `prior_current_occurrences` — occurrences of the CURRENT mosaic inside
//     that four-deep window.  The nearest body fact is R3's
//     `reinforcement_count`, which is an unbounded lifetime count, not a count
//     within a window.  Substituting it would silently redefine the law while
//     keeping its name.  That is fabrication and it is refused.
//
// MEASURED before deleting, so this is a removal of nothing rather than a
// removal of something: on her restored live body and on a fresh genesis every
// one of the eight counts read ZERO, and no surface anywhere read any of them
// (zero references outside this crate).  What remains truth-coupled is
// `mosaic_of_mosaics_count`, which is derived from her retained per-mosaic
// relation counts — a physical fact in her body — and is unaffected.
//
// The observation no longer carries the eight counts at all.  Reporting them
// as zero would be the step-fact-as-state lie: a reader takes "tapestry
// count 0" for a measurement, when the truth is that nothing measures it.

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) struct FormationActivation;

#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) struct EmittedNeuronFractal {
    pub(crate) neuron_lineage: [u8; 16],
    pub(crate) delta: SparsePhysicalStateDelta,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) struct CognitiveFormationSummary {
    pub(crate) cognitive_ordinal: u64,
    pub(crate) trace_count: usize,
    pub(crate) mosaic_count: usize,
    pub(crate) complete_neuron_count: usize,
    /// Source-independent complete cells retained in their shared exact
    /// quiescent law. They are real declared anatomy, but not reached work and
    /// therefore remain separate from `complete_neuron_count`.
    pub(crate) resting_neuron_count: usize,
    /// The body's decoded energy state.  Present on a restored organism too,
    /// so a restart never hides an exhausted body.
    pub(crate) energy: ReachedCohortEnergyState,
}

/// One caller-AUTHORED contact between two of the caller's own declared
/// receptors, named the way the caller's roster names them.
///
/// This is the same authorship growth DNA carries at genesis
/// (`DevelopmentalElectricalContact`), addressed by declared receptor rather
/// than by seed index because a living cohort's storage order is its own.
#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) struct AuthoredDeclaredContact {
    pub(crate) left_sensor_id: String,
    pub(crate) left_substream_id: String,
    pub(crate) right_sensor_id: String,
    pub(crate) right_substream_id: String,
    pub(crate) conductance_picosiemens: ExactRational,
}

/// Widen one per-contact activity mask for `added` newly authored contacts.
/// A contact that did not exist cannot have been active, so every appended
/// entry is `false`; every existing entry travels through verbatim.
fn extend_contact_mask(mask: &[bool], added: usize) -> Result<Box<[bool]>, FormationError> {
    let width = mask
        .len()
        .checked_add(added)
        .ok_or(FormationError::ArithmeticOverflow)?;
    let mut widened = Vec::new();
    widened
        .try_reserve_exact(width)
        .map_err(|_| FormationError::ArithmeticOverflow)?;
    widened.extend_from_slice(mask);
    widened.resize(width, false);
    Ok(widened.into_boxed_slice())
}

/// Position of one declared receptor within a cohort, or `None` when this
/// cohort does not carry it.  Two members declaring the same receptor would
/// make the name ambiguous and is refused rather than resolved.
fn declared_site_member(
    anatomy: &ReachedCohortAnatomy,
    sensor_id: &str,
    substream_id: &str,
) -> Result<Option<usize>, FormationError> {
    let mut found = None;
    for (index, mount) in anatomy.mounts().iter().enumerate() {
        let Some(site) = mount.source_site() else {
            continue;
        };
        if site.sensor_id() == sensor_id && site.substream_id() == substream_id {
            if found.is_some() {
                return Err(FormationError::AuthoredContactUnavailable);
            }
            found = Some(index);
        }
    }
    Ok(found)
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
enum ExperienceEvidenceCodec {
    V1,
    V2,
    V3,
    V4,
    V5,
}

#[derive(Clone, Debug, Eq, PartialEq)]
struct ResidentExperienceEvidence {
    /// Persistence representation only. Untouched restored evidence retains
    /// its exact bytes; any subsequent physical mutation advances it to V4.
    codec: ExperienceEvidenceCodec,
    pre_experience_rest: ReachedCohortState,
    post_experience_rest: Option<ReachedCohortState>,
    gate_work_perturbed_neurons: Box<[bool]>,
    receptor_excitation_zeptojoules: Box<[Option<ExactRational>]>,
    /// Neurons whose own retained coordinates changed during this occurrence.
    /// This is distinct from gate work: a physically active neuron may retain
    /// nothing, and an electrically reached neighbour may retain change.
    retained_change_neurons: Box<[bool]>,
    /// Neurons whose retained coordinates subsequently completed one exact
    /// unchanged interval. Settlement is neuron-local; another living neuron
    /// may remain active without blocking this one.
    retentively_settled_neurons: Box<[bool]>,
    active_electrical_contacts: Box<[bool]>,
    /// True only after the retained formation has completed one later
    /// settlement carrying no exogenous gate work.  The later settlement is
    /// the exact causal separation: ongoing internal current is life, not a
    /// reason to demand whole-formation electrical silence, and that same
    /// settlement cannot become its own cue.
    local_relaxation_observed: bool,
}

#[derive(Clone, Debug, Eq, PartialEq)]
struct ResidentRecurrenceEvidence {
    carries_physical_change_codec: bool,
    gate_work_perturbed_neurons: Box<[bool]>,
    receptor_excitation_zeptojoules: Box<[Option<ExactRational>]>,
    physically_changed_neurons: Box<[bool]>,
    active_recurrence_contacts: Box<[bool]>,
    endogenous: bool,
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

/// One compact retained physical formation. Identity is its exact original
/// neuronal deltas and bonds, not its member set: the same neurons may belong
/// to many formations. A later physical reassembly may increment the
/// observational reinforcement count but never overwrites the original.
#[derive(Clone, Debug, Eq, PartialEq)]
struct RetainedOrganismMosaic {
    mosaic: AdmittedPhysicalMosaic,
    /// How many later physical recurrences reassembled this exact formation.
    reinforcement_count: u64,
    /// Retired historical codec field. Overlap alone is not a relation, so
    /// current physics never increments it; it remains only to cold-restore
    /// an already lived body without byte loss.
    mosaic_of_mosaics_relation_count: u64,
}

impl RetainedOrganismMosaic {
    /// A first admission: the reference body with both counts at the
    /// historical default of zero (codec: encoded as the bare mosaic body,
    /// byte-identical to every pre-law receipt).
    fn newly_admitted(mosaic: AdmittedPhysicalMosaic) -> Self {
        Self {
            mosaic,
            reinforcement_count: 0,
            mosaic_of_mosaics_relation_count: 0,
        }
    }
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) struct ResidentCognitiveFormationState {
    generation: u64,
    next_lineage_ordinal: u64,
    unexpressed_electrical_seeds: Box<[DevelopmentalElectricalSeed]>,
    dormant_lineage_seeds: Box<[DormantLineageSeed]>,
    resting_population: Option<DevelopmentalRestingPopulation>,
    cohorts: Box<[ResidentReachedCohort]>,
    electrical_fabric: ResidentElectricalFabric,
    mosaics: Box<[RetainedOrganismMosaic]>,
    hippocampal: ResidentHippocampalIndex,
}

impl Default for ResidentCognitiveFormationState {
    fn default() -> Self {
        Self {
            generation: 0,
            next_lineage_ordinal: 1,
            unexpressed_electrical_seeds: Box::new([]),
            dormant_lineage_seeds: Box::new([]),
            resting_population: None,
            cohorts: Box::new([]),
            electrical_fabric: ResidentElectricalFabric::default(),
            mosaics: Box::new([]),
            hippocampal: ResidentHippocampalIndex::default(),
        }
    }
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) struct PreparedCognitiveFormationTransition {
    predecessor_generation: u64,
    predecessor_hippocampal: ResidentHippocampalIndex,
    successor: ResidentCognitiveFormationState,
    successor_encoded: Vec<u8>,
    observation: CognitiveFormationObservation,
}

impl PreparedCognitiveFormationTransition {
    pub(crate) fn observation(&self) -> &CognitiveFormationObservation {
        &self.observation
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
        if predecessor.generation != self.predecessor_generation {
            return Err((FormationError::PreparedPredecessorChanged, self));
        }
        Ok((self.successor, self.observation))
    }
}

fn encode_organism_mosaic(
    cohorts: &[ResidentReachedCohort],
    electrical_fabric: &ResidentElectricalFabric,
    mosaic: &AdmittedPhysicalMosaic,
    max_encoded_bytes: usize,
) -> Result<Vec<u8>, FormationError> {
    let topology = organism_mosaic_topology(cohorts, electrical_fabric)?;
    encode_admitted_physical_mosaic_for_topology(
        &topology.lineages,
        &topology.bonds,
        &topology.fractal_anatomies,
        mosaic,
        max_encoded_bytes,
    )
    .map_err(FormationError::PhysicalMosaicCodecUnavailable)
}

fn decode_organism_mosaic(
    cohorts: &[ResidentReachedCohort],
    electrical_fabric: &ResidentElectricalFabric,
    encoded: &[u8],
    max_encoded_bytes: usize,
) -> Result<AdmittedPhysicalMosaic, FormationError> {
    let topology = organism_mosaic_topology(cohorts, electrical_fabric)?;
    decode_admitted_physical_mosaic_for_topology(
        &topology.lineages,
        &topology.bonds,
        &topology.fractal_anatomies,
        encoded,
        max_encoded_bytes,
    )
    .map_err(FormationError::PhysicalMosaicCodecUnavailable)
}

struct OrganismMosaicTopology {
    lineages: Vec<[u8; 16]>,
    fractal_anatomies: Vec<(usize, usize)>,
    bonds: Vec<StablePhysicalBondReference>,
}

fn organism_mosaic_topology(
    cohorts: &[ResidentReachedCohort],
    electrical_fabric: &ResidentElectricalFabric,
) -> Result<OrganismMosaicTopology, FormationError> {
    let mut lineages = Vec::new();
    let mut fractal_anatomies = Vec::new();
    for cohort in cohorts {
        for (lineage, anatomy) in cohort
            .anatomy
            .neuron_lineages()
            .iter()
            .copied()
            .zip(cohort.anatomy.neuron_anatomies())
        {
            if lineages.contains(&lineage) {
                return Err(FormationError::NeuronLineageAuthorityChanged);
            }
            lineages.push(lineage);
            fractal_anatomies.push((
                anatomy.psi_ring_count(),
                anatomy
                    .sparse_delta_coordinate_count()
                    .ok_or(FormationError::ArithmeticOverflow)?,
            ));
        }
    }
    let mut endpoint_pairs = Vec::<([u8; 16], [u8; 16])>::new();
    for cohort in cohorts {
        for (left, right) in cohort.anatomy.contact_endpoints() {
            endpoint_pairs.push((
                cohort.anatomy.neuron_lineages()[left],
                cohort.anatomy.neuron_lineages()[right],
            ));
        }
    }
    for (left, right) in electrical_fabric.contact_endpoints() {
        endpoint_pairs.push((
            electrical_fabric.lineages()[left],
            electrical_fabric.lineages()[right],
        ));
    }
    let mut bonds = Vec::<StablePhysicalBondReference>::with_capacity(endpoint_pairs.len());
    for (first, second) in endpoint_pairs {
        let canonical = if first < second {
            (first, second)
        } else {
            (second, first)
        };
        let parallel_ordinal = u32::try_from(
            bonds
                .iter()
                .filter(|bond| bond.endpoints() == canonical)
                .count(),
        )
        .map_err(|_| FormationError::ArithmeticOverflow)?;
        bonds.push(
            StablePhysicalBondReference::new(first, second, parallel_ordinal)
                .ok_or(FormationError::NoncanonicalState)?,
        );
    }
    bonds.sort_unstable();
    Ok(OrganismMosaicTopology {
        lineages,
        fractal_anatomies,
        bonds,
    })
}

fn settle_organism_mosaic_boundary(
    cohorts: &[ResidentReachedCohort],
    electrical_fabric: &ResidentElectricalFabric,
    emitted_neuron_fractals: &[EmittedNeuronFractal],
    externally_reached_lineages: &[[u8; 16]],
    active_bonds: &[StablePhysicalBondReference],
    mosaics: &mut Vec<RetainedOrganismMosaic>,
    max_encoded_bytes: usize,
) -> Result<(Option<[u8; 32]>, usize), FormationError> {
    if active_bonds.is_empty() {
        return Ok((None, 0));
    }
    let topology = organism_mosaic_topology(cohorts, electrical_fabric)?;
    let current_fractals = topology
        .lineages
        .iter()
        .map(|lineage| {
            emitted_neuron_fractals
                .iter()
                .rev()
                .find(|fractal| &fractal.neuron_lineage == lineage)
                .map(|fractal| fractal.delta.clone())
        })
        .collect::<Vec<_>>();
    let changed_lineages = topology
        .lineages
        .iter()
        .copied()
        .zip(current_fractals.iter())
        .filter_map(|(lineage, fractal)| fractal.as_ref().map(|_| lineage))
        .collect::<Vec<_>>();
    let mut receipt = None;
    let mut reassemblies = 0usize;
    for retained in mosaics
        .iter_mut()
        .filter(|retained| retained.mosaic.is_original_only())
    {
        let cue = externally_reached_lineages
            .iter()
            .copied()
            .filter(|lineage| {
                retained
                    .mosaic
                    .member_lineages()
                    .binary_search(lineage)
                    .is_ok()
            })
            .collect::<Vec<_>>();
        let recognized = match prove_physical_mosaic_recurrence(
            &retained.mosaic,
            &changed_lineages,
            active_bonds,
            &cue,
        ) {
            Ok(recognized) => recognized,
            Err(error) if physical_mosaic_non_admission(error) => continue,
            Err(error) => return Err(FormationError::PhysicalMosaicUnavailable(error)),
        };
        let encoded = encode_admitted_physical_mosaic_for_topology(
            &topology.lineages,
            &topology.bonds,
            &topology.fractal_anatomies,
            &recognized,
            max_encoded_bytes,
        )
        .map_err(FormationError::PhysicalMosaicCodecUnavailable)?;
        receipt = Some(sha256(&encoded));
        retained.mosaic = recognized;
        reassemblies = reassemblies
            .checked_add(1)
            .ok_or(FormationError::ArithmeticOverflow)?;
    }
    let mut reached_sensory_layers = Vec::new();
    for lineage in externally_reached_lineages {
        for cohort in cohorts {
            for (mount, candidate) in cohort
                .anatomy
                .mounts()
                .iter()
                .zip(cohort.anatomy.neuron_lineages())
            {
                if candidate == lineage && mount.source_site().is_some() {
                    let layer = mount.place().layer();
                    if !reached_sensory_layers.contains(&layer) {
                        reached_sensory_layers.push(layer);
                    }
                }
            }
        }
    }
    if reached_sensory_layers.len() < 2 {
        return Ok((receipt, reassemblies));
    }
    let changed = changed_lineages.clone();
    let mut unvisited = changed.clone();
    while let Some(start) = unvisited.pop() {
        let mut component = vec![start];
        let mut cursor = 0usize;
        while cursor < component.len() {
            let current = component[cursor];
            for bond in active_bonds {
                let (left, right) = bond.endpoints();
                let neighbour = if left == current {
                    Some(right)
                } else if right == current {
                    Some(left)
                } else {
                    None
                };
                if let Some(neighbour) = neighbour {
                    if changed.contains(&neighbour) && !component.contains(&neighbour) {
                        component.push(neighbour);
                        if let Some(index) = unvisited.iter().position(|value| value == &neighbour)
                        {
                            unvisited.swap_remove(index);
                        }
                    }
                }
            }
            cursor += 1;
        }
        let carries_association = component.iter().any(|lineage| {
            cohorts.iter().any(|cohort| {
                cohort
                    .anatomy
                    .mounts()
                    .iter()
                    .zip(cohort.anatomy.neuron_lineages())
                    .any(|(mount, candidate)| {
                        candidate == lineage
                            && mount.source_site().is_none()
                            && mount.place().layer() == 7
                    })
            })
        });
        if component.len() < 3 || !carries_association {
            continue;
        }
        let component_fractals = topology
            .lineages
            .iter()
            .zip(current_fractals.iter())
            .map(|(lineage, fractal)| {
                component
                    .contains(lineage)
                    .then(|| fractal.clone())
                    .flatten()
            })
            .collect::<Vec<_>>();
        let original = match admit_physical_mosaic_original(
            &topology.lineages,
            &topology.fractal_anatomies,
            &component_fractals,
            active_bonds,
        ) {
            Ok(original) => original,
            Err(error) if physical_mosaic_non_admission(error) => continue,
            Err(error) => return Err(FormationError::PhysicalMosaicUnavailable(error)),
        };
        if mosaics
            .iter()
            .any(|prior| prior.mosaic.same_retained_structure(&original))
        {
            continue;
        }
        mosaics
            .try_reserve(1)
            .map_err(|_| FormationError::ArithmeticOverflow)?;
        mosaics.push(RetainedOrganismMosaic::newly_admitted(original));
    }
    Ok((receipt, reassemblies))
}

/// Encode one retained mosaic reference for the organism state body.  Zero
/// counts encode as the bare admitted-mosaic body — byte-identical to every
/// pre-law receipt; nonzero counts prepend the `GLMRC01` wrapper (see the
/// magic's doc for the versioned-magic precedent).
fn encode_retained_organism_mosaic(
    cohorts: &[ResidentReachedCohort],
    electrical_fabric: &ResidentElectricalFabric,
    retained: &RetainedOrganismMosaic,
    max_encoded_bytes: usize,
) -> Result<Vec<u8>, FormationError> {
    let body = encode_organism_mosaic(
        cohorts,
        electrical_fabric,
        &retained.mosaic,
        max_encoded_bytes,
    )?;
    if retained.reinforcement_count == 0 && retained.mosaic_of_mosaics_relation_count == 0 {
        return Ok(body);
    }
    let mut encoded = Vec::new();
    encoded
        .try_reserve_exact(
            RETAINED_MOSAIC_COUNTS_MAGIC
                .len()
                .checked_add(16)
                .and_then(|value| value.checked_add(body.len()))
                .ok_or(FormationError::ArithmeticOverflow)?,
        )
        .map_err(|_| FormationError::ArithmeticOverflow)?;
    encoded.extend_from_slice(RETAINED_MOSAIC_COUNTS_MAGIC);
    encoded.extend_from_slice(&retained.reinforcement_count.to_le_bytes());
    encoded.extend_from_slice(&retained.mosaic_of_mosaics_relation_count.to_le_bytes());
    encoded.extend_from_slice(&body);
    Ok(encoded)
}

/// Decode one retained mosaic reference in whichever admitted layout its
/// leading bytes name: the bare pre-law body (counts zero) or the `GLMRC01`
/// counts wrapper.  A wrapper carrying only zeros is refused — its canonical
/// form is the bare body, so accepting it would let one retained state admit
/// two encodings.
fn decode_retained_organism_mosaic(
    cohorts: &[ResidentReachedCohort],
    electrical_fabric: &ResidentElectricalFabric,
    encoded: &[u8],
    max_encoded_bytes: usize,
) -> Result<RetainedOrganismMosaic, FormationError> {
    if encoded.get(..RETAINED_MOSAIC_COUNTS_MAGIC.len()) != Some(RETAINED_MOSAIC_COUNTS_MAGIC) {
        return Ok(RetainedOrganismMosaic::newly_admitted(
            decode_organism_mosaic(cohorts, electrical_fabric, encoded, max_encoded_bytes)?,
        ));
    }
    let mut cursor = RETAINED_MOSAIC_COUNTS_MAGIC.len();
    let reinforcement_count = take_state_u64(encoded, &mut cursor)?;
    let mosaic_of_mosaics_relation_count = take_state_u64(encoded, &mut cursor)?;
    if reinforcement_count == 0 && mosaic_of_mosaics_relation_count == 0 {
        return Err(FormationError::NoncanonicalState);
    }
    let mosaic = decode_organism_mosaic(
        cohorts,
        electrical_fabric,
        encoded
            .get(cursor..)
            .ok_or(FormationError::NoncanonicalState)?,
        max_encoded_bytes,
    )?;
    Ok(RetainedOrganismMosaic {
        mosaic,
        reinforcement_count,
        mosaic_of_mosaics_relation_count,
    })
}

impl ResidentCognitiveFormationState {
    /// Retire the task-955 local-integration projection that equated
    /// sense-local topology indices across unrelated sensory coordinate
    /// systems.  The correction is identified from the persisted anatomy
    /// itself: an intrinsic layer-6 lineage is retired only when a retained
    /// fabric contact joins it to a receptor whose injective declared-place
    /// projection names a different layer-6 place.
    ///
    /// Receptor neurons, their lineages, physical state, local fluids, and all
    /// unrelated contacts remain exact.  The falsely reached intrinsic cells
    /// and any formations containing them are not preserved as learning; their
    /// claimed places return to the compact quiescent population.
    fn retire_aliased_local_integrators(&self) -> Result<Option<Self>, FormationError> {
        let receptors = self
            .cohorts
            .iter()
            .flat_map(|cohort| {
                cohort
                    .anatomy
                    .mounts()
                    .iter()
                    .zip(cohort.anatomy.neuron_lineages())
            })
            .filter_map(|(mount, lineage)| mount.source_site().map(|_| (*lineage, mount.place())))
            .collect::<Vec<_>>();
        let intrinsic = self
            .cohorts
            .iter()
            .flat_map(|cohort| {
                cohort
                    .anatomy
                    .mounts()
                    .iter()
                    .zip(cohort.anatomy.neuron_lineages())
            })
            .filter_map(|(mount, lineage)| {
                let place = mount.place();
                (mount.source_site().is_none() && place.layer() == 6).then_some((*lineage, place))
            })
            .collect::<Vec<_>>();

        let mut retired = Vec::<[u8; 16]>::new();
        for (left, right) in self.electrical_fabric.contact_endpoints() {
            let left_lineage = self.electrical_fabric.lineages()[left];
            let right_lineage = self.electrical_fabric.lineages()[right];
            for (receptor_lineage, receptor_place) in &receptors {
                let target_lineage = if left_lineage == *receptor_lineage {
                    Some(right_lineage)
                } else if right_lineage == *receptor_lineage {
                    Some(left_lineage)
                } else {
                    None
                };
                let Some(target_lineage) = target_lineage else {
                    continue;
                };
                let Some((_, target_place)) = intrinsic
                    .iter()
                    .find(|(lineage, _)| *lineage == target_lineage)
                else {
                    continue;
                };
                if *target_place != local_integration_place(*receptor_place)?
                    && !retired.contains(&target_lineage)
                {
                    retired.push(target_lineage);
                }
            }
        }
        if retired.is_empty() {
            return Ok(None);
        }

        let mut retired_places = Vec::new();
        let mut cohorts = Vec::with_capacity(self.cohorts.len());
        for cohort in self.cohorts.iter() {
            let retired_members = cohort
                .anatomy
                .neuron_lineages()
                .iter()
                .filter(|lineage| retired.contains(lineage))
                .count();
            if retired_members == 0 {
                cohorts.push(cohort.clone());
                continue;
            }
            if retired_members != cohort.anatomy.neuron_count()
                || cohort.anatomy.neuron_count() != 1
                || cohort.anatomy.mounts()[0].source_site().is_some()
                || cohort.anatomy.mounts()[0].place().layer() != 6
            {
                return Err(FormationError::NeuronLineageAuthorityChanged);
            }
            retired_places.push(cohort.anatomy.mounts()[0].place());
        }

        let mut resting_population = self.resting_population.clone();
        for place in retired_places {
            let Some(population) = resting_population.as_ref() else {
                continue;
            };
            if population.materialized_lineage_ordinal(place).is_none() {
                continue;
            }
            resting_population = Some(
                population
                    .release_claimed_place(place)
                    .map_err(FormationError::DevelopmentalRestingPopulationUnavailable)?,
            );
        }
        let mosaics = self
            .mosaics
            .iter()
            .filter(|retained| {
                !retained
                    .mosaic
                    .member_lineages()
                    .iter()
                    .any(|lineage| retired.contains(lineage))
            })
            .cloned()
            .collect::<Vec<_>>();
        let successor = Self {
            generation: self.generation,
            next_lineage_ordinal: self.next_lineage_ordinal,
            unexpressed_electrical_seeds: self.unexpressed_electrical_seeds.clone(),
            dormant_lineage_seeds: self.dormant_lineage_seeds.clone(),
            resting_population,
            cohorts: cohorts.into_boxed_slice(),
            electrical_fabric: self
                .electrical_fabric
                .without_lineages(&retired)
                .map_err(FormationError::ResidentElectricalUnavailable)?,
            mosaics: mosaics.into_boxed_slice(),
            hippocampal: self.hippocampal,
        };
        validate_lineage_state(&successor)?;
        Ok(Some(successor))
    }

    /// Make the already-declared retinal territory explicit once for bodies
    /// written by the aggregate one-channel implementation. This is a
    /// representation correction, not neuronal growth: stable lineage,
    /// source place, contacts, existing material state, generation and
    /// identity all remain attached. Cognitive formations authored by the
    /// replaced aggregate/self-tail law are deliberately retired rather than
    /// reintroduced as learned authority under the corrected physics.
    fn expand_legacy_sight_channel_populations(&self) -> Result<Self, FormationError> {
        let mut populations_by_lineage = Vec::new();
        let mut cohorts = Vec::with_capacity(self.cohorts.len());
        for cohort in self.cohorts.iter() {
            let (anatomy, state) = expand_reached_sight_channel_populations(
                &cohort.anatomy,
                &cohort.state,
                definitive_virtual_carriers_per_compartment(),
            )
            .map_err(FormationError::PhysicalSettlementUnavailable)?;
            if anatomy == cohort.anatomy {
                cohorts.push(cohort.clone());
                continue;
            }
            for ((lineage, mount), neuron) in anatomy
                .neuron_lineages()
                .iter()
                .zip(anatomy.mounts())
                .zip(anatomy.neuron_anatomies())
            {
                let Some(site) = mount.source_site() else {
                    continue;
                };
                if site.sense() == PhysicalSourceSense::Sight {
                    let population = usize::try_from(neuron.gate_population())
                        .map_err(|_| FormationError::ArithmeticOverflow)?;
                    if population > 1 {
                        populations_by_lineage.push((*lineage, population));
                    }
                }
            }
            cohorts.push(ResidentReachedCohort {
                anatomy,
                state,
                pending_experience: None,
                retained_experience: None,
                pending_recurrence: None,
            });
        }
        if populations_by_lineage.is_empty() {
            return Ok(self.clone());
        }
        for cohort in &mut cohorts {
            cohort.pending_experience = None;
            cohort.retained_experience = None;
            cohort.pending_recurrence = None;
        }
        let successor = Self {
            generation: self.generation,
            next_lineage_ordinal: self.next_lineage_ordinal,
            unexpressed_electrical_seeds: self.unexpressed_electrical_seeds.clone(),
            dormant_lineage_seeds: self.dormant_lineage_seeds.clone(),
            resting_population: self.resting_population.clone(),
            cohorts: cohorts.into_boxed_slice(),
            electrical_fabric: self.electrical_fabric.clone(),
            mosaics: Box::new([]),
            hippocampal: ResidentHippocampalIndex::default(),
        };
        validate_lineage_state(&successor)?;
        Ok(successor)
    }

    /// Carry an already-current body through the retired representation gate
    /// without cloning every reached neuron merely to rediscover that no
    /// migration applies. Historical bodies still take the exact correction
    /// above; current bodies retain the owned state byte-for-byte.
    fn into_expanded_legacy_sight_channel_populations(self) -> Result<Self, FormationError> {
        let mut required = false;
        for cohort in self.cohorts.iter() {
            if legacy_sight_channel_populations_require_expansion(&cohort.anatomy, &cohort.state)
                .map_err(FormationError::PhysicalSettlementUnavailable)?
            {
                required = true;
                break;
            }
        }
        if !required {
            return Ok(self);
        }
        self.expand_legacy_sight_channel_populations()
    }

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
            resting_population: None,
            cohorts: Box::new([]),
            electrical_fabric: ResidentElectricalFabric::default(),
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
            mosaic_count: self
                .mosaics
                .iter()
                .filter(|retained| retained.mosaic.carries_only_retained_neuron_structure())
                .count(),
            complete_neuron_count: self
                .cohorts
                .iter()
                .map(|cohort| cohort.anatomy.neuron_count())
                .sum(),
            resting_neuron_count: self
                .resting_population
                .as_ref()
                .and_then(|population| usize::try_from(population.resting_cell_count()).ok())
                .unwrap_or(0),
            energy: self.energy_state(),
        }
    }

    /// Read-only structural observation of the retained distributed
    /// formations: one entry per admitted mosaic as the stable member
    /// lineages and the retained recurrence-bond count.  Structure only —
    /// no recognition, recall, meaning, or capital is emitted, and reading
    /// advances nothing.
    pub(crate) fn observe_retained_formation_members(&self) -> Vec<(Vec<[u8; 16]>, usize)> {
        self.mosaics
            .iter()
            .filter(|retained| retained.mosaic.carries_only_retained_neuron_structure())
            .map(|retained| {
                (
                    retained.mosaic.member_lineages().to_vec(),
                    retained.mosaic.recurrence_bonds().len(),
                )
            })
            .collect()
    }

    /// Total mosaic-of-mosaics relation events recorded against the retained
    /// formations — the sum of the per-mosaic retained counts (R1 overlap
    /// branch; R3: a count over recorded episodes, never a score).
    pub(crate) fn mosaic_of_mosaics_count(&self) -> Result<usize, FormationError> {
        self.mosaics
            .iter()
            .filter(|retained| retained.mosaic.carries_only_retained_neuron_structure())
            .try_fold(0usize, |total, retained| {
                usize::try_from(retained.mosaic_of_mosaics_relation_count)
                    .ok()
                    .and_then(|count| total.checked_add(count))
                    .ok_or(FormationError::ArithmeticOverflow)
            })
    }

    /// The body's exact energy state, summed over every mounted cohort: the
    /// recovery-fluid reservoir, the dissipation ledgers, and the separated
    /// membrane charge still standing away from rest.
    pub(crate) fn energy_state(&self) -> ReachedCohortEnergyState {
        let mut total = ReachedCohortEnergyState::default();
        for cohort in &self.cohorts {
            let cohort_energy = reached_cohort_energy_state(&cohort.anatomy, &cohort.state);
            total.available_energy_zeptojoules += cohort_energy.available_energy_zeptojoules;
            total.spent_energy_zeptojoules += cohort_energy.spent_energy_zeptojoules;
            total.thermal_energy_zeptojoules += cohort_energy.thermal_energy_zeptojoules;
            total.available_energy_capacity_zeptojoules +=
                cohort_energy.available_energy_capacity_zeptojoules;
            total.spent_energy_capacity_zeptojoules +=
                cohort_energy.spent_energy_capacity_zeptojoules;
            total.thermal_energy_capacity_zeptojoules +=
                cohort_energy.thermal_energy_capacity_zeptojoules;
            total.dissipated_energy_zeptojoules += cohort_energy.dissipated_energy_zeptojoules;
            total.dissipation_capacity_energy_zeptojoules +=
                cohort_energy.dissipation_capacity_energy_zeptojoules;
            total.separated_elementary_charges = total
                .separated_elementary_charges
                .saturating_add(cohort_energy.separated_elementary_charges);
        }
        total
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
        self.prepare_admitted_transition(&admitted_fixture_episode(source), max_encoded_bytes)
    }

    pub(crate) fn prepare_bare_source(
        &self,
        _source: &NativeJointSourceEpisode,
        _max_encoded_bytes: usize,
    ) -> Result<PreparedCognitiveFormationTransition, FormationError> {
        Err(FormationError::JointFieldUnavailable(
            JointNeuronBoundaryError::Source(JointUfSourceError::Unavailable(
                "explicit admitted joint source episode is required",
            )),
        ))
    }

    pub(crate) fn prepare_admitted_transition(
        &self,
        admitted_source: &AdmittedJointSourceEpisode,
        max_encoded_bytes: usize,
    ) -> Result<PreparedCognitiveFormationTransition, FormationError> {
        self.prepare_typed_admitted_transition(admitted_source, None, max_encoded_bytes)
    }

    pub(crate) fn prepare_vestibular_transition(
        &self,
        ingress: &ResidentVestibularIngress,
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
        self.prepare_typed_admitted_transition(&admitted_source, Some(ingress), max_encoded_bytes)
    }

    fn prepare_typed_admitted_transition(
        &self,
        admitted_source: &AdmittedJointSourceEpisode,
        vestibular: Option<&ResidentVestibularIngress>,
        max_encoded_bytes: usize,
    ) -> Result<PreparedCognitiveFormationTransition, FormationError> {
        // A current body crosses each historical one-way correction without
        // deep-copying its complete reached population. At most one owned
        // predecessor copy is made here; all current structures then move
        // into the successor under the ordinary transactional prepare.
        let expanded = self
            .retire_aliased_local_integrators()?
            .unwrap_or_else(|| self.clone())
            .into_expanded_legacy_sight_channel_populations()?;
        Self::prepare_typed_admitted_transition_from_owned(
            expanded,
            self.generation,
            self.hippocampal,
            admitted_source,
            vestibular,
            max_encoded_bytes,
            true,
        )
    }

    fn prepare_typed_admitted_transition_from_owned(
        expanded: Self,
        predecessor_generation_authority: u64,
        predecessor_hippocampal_authority: ResidentHippocampalIndex,
        admitted_source: &AdmittedJointSourceEpisode,
        vestibular: Option<&ResidentVestibularIngress>,
        max_encoded_bytes: usize,
        seal_successor: bool,
    ) -> Result<PreparedCognitiveFormationTransition, FormationError> {
        let Self {
            generation: predecessor_generation,
            next_lineage_ordinal: predecessor_next_lineage_ordinal,
            unexpressed_electrical_seeds: predecessor_unexpressed_electrical_seeds,
            dormant_lineage_seeds: predecessor_dormant_lineage_seeds,
            resting_population: predecessor_resting_population,
            cohorts: predecessor_cohorts,
            electrical_fabric: predecessor_electrical_fabric,
            mosaics: predecessor_mosaics,
            hippocampal: predecessor_hippocampal,
        } = expanded;
        let source = admitted_source.episode();
        if source.joint_source_occurrences().is_empty() {
            return Err(FormationError::SourceOccurrenceAbsent);
        }
        let source_generation = predecessor_generation
            .checked_add(1)
            .ok_or(FormationError::InvalidSourceGeneration)?;
        let auditory_anatomy = exact_auditory_receptor_anatomy()?;
        let tactile_anatomy = exact_tactile_receptor_anatomy()?;
        let mut unexpressed_electrical_seeds = predecessor_unexpressed_electrical_seeds.into_vec();
        let mut dormant_lineage_seeds = predecessor_dormant_lineage_seeds.into_vec();
        let mut resting_population = predecessor_resting_population;
        let mut next_lineage_ordinal = predecessor_next_lineage_ordinal;
        let mut cohorts = predecessor_cohorts.into_vec();
        // Bodies written before the retained-fractal boundary may still carry
        // transient charge, phase, gate, residue, or metabolic coordinates in
        // a mosaic body.  They remain readable only so the living neuron and
        // retained-experience state can cross the release boundary.  They are
        // not cognitive authority and leave on the next physical transition;
        // a later recurrence must form a new mosaic from retained structure.
        let mut mosaics = predecessor_mosaics
            .into_vec()
            .into_iter()
            .filter(|retained| retained.mosaic.carries_retained_original_structure())
            .collect::<Vec<_>>();
        let predecessor_recognized_mosaics = mosaics
            .iter()
            .filter(|retained| retained.mosaic.carries_only_retained_neuron_structure())
            .map(|retained| retained.mosaic.clone())
            .collect::<Vec<_>>();
        cohorts
            .try_reserve(source.joint_source_occurrences().len())
            .map_err(|_| FormationError::ArithmeticOverflow)?;
        let mut physically_transitioned_neuron_lineages = Vec::<[u8; 16]>::new();
        let mut externally_reached_neuron_lineages = Vec::<[u8; 16]>::new();
        let mut externally_reached_by_occurrence =
            vec![Vec::<[u8; 16]>::new(); source.joint_source_occurrences().len()];
        let mut emitted_neuron_fractals = Vec::new();
        let mut mosaic_formed = None;
        // The retired archive checkpoint is carried forward VERBATIM: never
        // advanced, never published, never dereferenced.  A body that already
        // holds one keeps the exact 74 bytes it was persisted with, so the
        // receipt of an untouched field cannot drift.
        let hippocampal = predecessor_hippocampal;
        let mut dsf_delivery_count = 0usize;
        let mut partial_cue_reassembly_count = 0usize;
        let mut endogenous_partial_cue_reassembly_count = 0usize;
        let mut metabolic = ReachedCohortMetabolicObservation::default();
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
            let mut cohort_targets: Vec<(
                usize,
                ResidentReachedCohort,
                Vec<usize>,
                Option<ReceptorLaw>,
            )> = Vec::new();
            let mut next_new_cohort_index = cohorts.len();
            let mut declared_groups = Vec::new();
            let mut physically_claimed = vec![false; reached_source_sites.len()];
            for cohort in &cohorts {
                let group = cohort
                    .anatomy
                    .source_sites()
                    .filter_map(|resident_site| {
                        reached_source_sites
                            .iter()
                            .position(|reached| reached == resident_site)
                    })
                    .collect::<Vec<_>>();
                if group.is_empty() {
                    continue;
                }
                if group
                    .iter()
                    .any(|coordinate_index| physically_claimed[*coordinate_index])
                {
                    return Err(FormationError::NeuronLineageAuthorityChanged);
                }
                for coordinate_index in &group {
                    physically_claimed[*coordinate_index] = true;
                }
                declared_groups.push(group);
            }
            for seed in &unexpressed_electrical_seeds {
                let mut group = Vec::new();
                for seed_site in seed.source_sites() {
                    let Some(coordinate_index) = reached_source_sites
                        .iter()
                        .position(|reached| reached == seed_site)
                    else {
                        group.clear();
                        break;
                    };
                    if physically_claimed[coordinate_index] {
                        group.clear();
                        break;
                    }
                    group.push(coordinate_index);
                }
                if group.len() == seed.source_sites().len() {
                    for coordinate_index in &group {
                        physically_claimed[*coordinate_index] = true;
                    }
                    declared_groups.push(group);
                }
            }
            // DSF groups describe the joint field; they are not neuronal
            // anatomy.  Any reached sites not already claimed by living
            // anatomy or explicit developmental wiring settle together only
            // when this same physical occurrence declares them on the same
            // sensory organ under the same receptor law.  The occurrence is
            // the shared causal instant, the sensor id is the organ, and the
            // receptor law is the local transduction physics.  No semantic or
            // storage grouping is introduced here.
            for coordinate_index in 0..reached_source_sites.len() {
                if physically_claimed[coordinate_index] {
                    continue;
                }
                let receptor_law =
                    receptor_law_for_reached_coordinates(&reached_sources, &[coordinate_index]);
                if receptor_law.is_none() && vestibular.is_none() {
                    continue;
                }
                let matching_group = declared_groups.iter_mut().find(|group| {
                    let Some(first_index) = group.first().copied() else {
                        return false;
                    };
                    let retained_formation_owns_group = cohorts.iter().any(|cohort| {
                        cohort.retained_experience.is_some()
                            && cohort
                                .anatomy
                                .source_sites()
                                .any(|site| site == &reached_source_sites[first_index])
                    });
                    !retained_formation_owns_group
                        && reached_source_sites[first_index].sensor_id()
                            == reached_source_sites[coordinate_index].sensor_id()
                        && receptor_law_for_reached_coordinates(&reached_sources, &[first_index])
                            == receptor_law
                });
                if let Some(group) = matching_group {
                    group.push(coordinate_index);
                } else {
                    declared_groups.push(vec![coordinate_index]);
                }
            }
            for group in &declared_groups {
                for coordinate_index in group {
                    physically_claimed[*coordinate_index] = true;
                }
            }
            for declared_group in &declared_groups {
                let group_sites = declared_group
                    .iter()
                    .map(|coordinate_index| reached_source_sites[*coordinate_index].clone())
                    .collect::<Vec<_>>();
                let group_receptor_law =
                    receptor_law_for_reached_coordinates(&reached_sources, declared_group);
                let overlapping_cohorts = cohorts
                    .iter()
                    .enumerate()
                    .filter(|(_, cohort)| {
                        group_sites.iter().any(|site| {
                            cohort
                                .anatomy
                                .source_sites()
                                .any(|resident| resident == site)
                        })
                    })
                    .map(|(index, _)| index)
                    .collect::<Vec<_>>();
                if overlapping_cohorts.len() > 1 {
                    for coordinate_index in declared_group {
                        let site = &reached_source_sites[*coordinate_index];
                        let resident_matches = overlapping_cohorts
                            .iter()
                            .copied()
                            .filter(|cohort_index| {
                                cohorts[*cohort_index]
                                    .anatomy
                                    .source_sites()
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
                            .find(|(index, _, _, _)| *index == resident_matches[0])
                        {
                            target.2.push(*coordinate_index);
                        } else {
                            cohort_targets.push((
                                resident_matches[0],
                                cohorts[resident_matches[0]].clone(),
                                vec![*coordinate_index],
                                group_receptor_law,
                            ));
                        }
                    }
                    continue;
                }

                let existing_index = overlapping_cohorts.first().copied();
                if group_receptor_law.is_none() && vestibular.is_none() && existing_index.is_none()
                {
                    continue;
                }
                let mut reached_admissions = Vec::new();
                reached_admissions
                    .try_reserve_exact(declared_group.len())
                    .map_err(|_| FormationError::ArithmeticOverflow)?;
                for coordinate_index in declared_group {
                    let port = reached_sources[*coordinate_index].1;
                    let admission =
                        match resolve_lineage_for_port(&cohorts, &dormant_lineage_seeds, port)? {
                            Some(lineage) => ReachedLineageAdmission {
                                lineage,
                                claimed_resting_neuron: None,
                            },
                            None => claim_resting_or_allocate_lineage(
                                &mut resting_population,
                                &reached_source_sites[*coordinate_index],
                                &mut next_lineage_ordinal,
                            )?,
                        };
                    reached_admissions.push(admission);
                }
                let reached_lineages = reached_admissions
                    .iter()
                    .map(|admission| admission.lineage)
                    .collect::<Vec<_>>();
                let cohort = if let Some(index) = existing_index {
                    let additions = declared_group
                        .iter()
                        .zip(group_sites.iter())
                        .zip(reached_admissions.iter())
                        .filter_map(|((coordinate_index, site), admission)| {
                            (!cohorts[index]
                                .anatomy
                                .source_sites()
                                .any(|resident| resident == site))
                            .then_some((*coordinate_index, site.clone(), admission))
                        })
                        .map(|(coordinate_index, site, admission)| {
                            reached_genesis_cell_from_admission(
                                &shared,
                                coordinate_index,
                                site,
                                admission,
                            )
                        })
                        .collect::<Result<Vec<_>, _>>()?;
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
                        let common_positions = vec![resident.anatomy.neuron_anatomies()[0]
                            .mathloom_positions()
                            .max(expected.anatomy.neuron_anatomies()[0].mathloom_positions())];
                        extend_resident_cohort_positional_fabrics(
                            &mut resident,
                            &common_positions,
                        )?;
                        let (expected_anatomy, _) = extend_reached_cohort_positional_fabrics(
                            &expected.anatomy,
                            &expected.state,
                            &common_positions,
                        )
                        .map_err(FormationError::PhysicalSettlementUnavailable)?;
                        if resident.anatomy != expected_anatomy {
                            return Err(FormationError::VestibularUnavailable(
                                FunctionalVestibularError::ReachedAnatomyMismatch,
                            ));
                        }
                    }
                    if !additions.is_empty() {
                        let old_anatomy = resident.anatomy.clone();
                        let old_neuron_count = old_anatomy.neuron_count();
                        let (extended_anatomy, extended_state) = extend_reached_cohort_cells(
                            &resident.anatomy,
                            &resident.state,
                            additions,
                        )
                        .map_err(FormationError::PhysicalSettlementUnavailable)?;
                        extend_resident_cohort_evidence(
                            &mut resident,
                            &old_anatomy,
                            extended_anatomy,
                            extended_state,
                            old_neuron_count,
                        )?;
                        dormant_lineage_seeds.retain(|seed| {
                            !declared_group.iter().any(|coordinate_index| {
                                seed.matches_port(reached_sources[*coordinate_index].1)
                            })
                        });
                    }
                    if group_sites
                        .iter()
                        .zip(reached_lineages.iter())
                        .any(|(site, lineage)| {
                            resident
                                .anatomy
                                .source_site_member(site)
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
                        .position(|seed| seed.source_sites() == group_sites);
                    let electrical = match seed_index {
                        Some(index) => unexpressed_electrical_seeds[index]
                            .resolve(&group_sites)
                            .map_err(FormationError::DevelopmentalElectricalUnavailable)?,
                        None => SparseElectricalAnatomy::new(group_sites.len(), Vec::new())
                            .map_err(|error| {
                                FormationError::PhysicalGenesisUnavailable(
                                    VirtualMaterialGenesisError::Electrical(error),
                                )
                            })?,
                    };
                    let (reached_anatomy, reached_state) = if let Some(ingress) = vestibular {
                        if electrical.contact_count() != 0 || reached_lineages.len() != 1 {
                            return Err(FormationError::VestibularUnavailable(
                                FunctionalVestibularError::NotIsolatedSingleVertex,
                            ));
                        }
                        let genesis = match reached_admissions[0].claimed_resting_neuron.as_ref() {
                            Some(resting) => specialize_single_vertex_vestibular_reached_cohort(
                                ingress.receptor_anatomy(),
                                ingress.source(),
                                &shared,
                                reached_lineages[0],
                                resting,
                            ),
                            None => create_single_vertex_vestibular_reached_cohort(
                                ingress.receptor_anatomy(),
                                ingress.source(),
                                &shared,
                                reached_lineages[0],
                            ),
                        }
                        .map_err(FormationError::VestibularUnavailable)?;
                        (genesis.anatomy, genesis.state)
                    } else {
                        let cells = declared_group
                            .iter()
                            .zip(group_sites.iter())
                            .zip(reached_admissions.iter())
                            .map(|((coordinate_index, site), admission)| {
                                reached_genesis_cell_from_admission(
                                    &shared,
                                    *coordinate_index,
                                    site.clone(),
                                    admission,
                                )
                            })
                            .collect::<Result<Vec<_>, _>>()?;
                        let neuron_anatomies = cells
                            .iter()
                            .map(|cell| cell.anatomy.clone())
                            .collect::<Vec<_>>();
                        let lineages = cells.iter().map(|cell| cell.lineage).collect::<Vec<_>>();
                        let mounts = cells
                            .iter()
                            .map(|cell| cell.mount.clone())
                            .collect::<Vec<_>>();
                        let neuron_states =
                            cells.into_iter().map(|cell| cell.state).collect::<Vec<_>>();
                        let electrical_state = SparseElectricalState::genesis(&electrical);
                        let anatomy = ReachedCohortAnatomy::new_mounted(
                            neuron_anatomies,
                            lineages,
                            mounts,
                            electrical,
                        )
                        .map_err(FormationError::PhysicalSettlementUnavailable)?;
                        let state =
                            ReachedCohortState::new(&anatomy, neuron_states, electrical_state)
                                .map_err(FormationError::PhysicalSettlementUnavailable)?;
                        (anatomy, state)
                    };
                    if let Some(index) = seed_index {
                        unexpressed_electrical_seeds.remove(index);
                    }
                    dormant_lineage_seeds.retain(|seed| {
                        !declared_group.iter().any(|coordinate_index| {
                            seed.matches_port(reached_sources[*coordinate_index].1)
                        })
                    });
                    ResidentReachedCohort {
                        anatomy: reached_anatomy,
                        state: reached_state,
                        pending_experience: None,
                        retained_experience: None,
                        pending_recurrence: None,
                    }
                };
                let target_index = existing_index.unwrap_or_else(|| {
                    let index = next_new_cohort_index;
                    next_new_cohort_index += 1;
                    index
                });
                cohort_targets.push((
                    target_index,
                    cohort,
                    declared_group.clone(),
                    group_receptor_law,
                ));
            }
            for (cohort_index, mut cohort, coordinate_indices, receptor_law) in cohort_targets {
                let field_gate_count = if vestibular.is_some() {
                    1
                } else {
                    shared.result().gates.len()
                };
                if receptor_law.is_some() || vestibular.is_some() {
                    let mut required_positions = cohort
                        .anatomy
                        .neuron_anatomies()
                        .iter()
                        .map(|anatomy| anatomy.mathloom_positions())
                        .collect::<Vec<_>>();
                    for field_gate_index in 0..field_gate_count {
                        for coordinate_index in coordinate_indices.iter().copied() {
                            let perspective = bind_neuron_perspective(
                                &shared,
                                coordinate_index,
                                field_gate_index,
                            )
                            .map_err(FormationError::JointFieldUnavailable)?;
                            let resident_index = cohort
                                .anatomy
                                .source_site_member(&reached_source_sites[coordinate_index])
                                .ok_or(FormationError::NeuronLineageAuthorityAbsent)?;
                            required_positions[resident_index] = required_positions[resident_index]
                                .max(
                                    required_mathloom_positions(perspective)
                                        .map_err(FormationError::JointFieldUnavailable)?,
                                );
                        }
                    }
                    extend_resident_cohort_positional_fabrics(&mut cohort, &required_positions)?;
                }
                let occurrence_predecessor_state = cohort.state.clone();
                if receptor_law.is_some() || vestibular.is_some() {
                    for field_gate_index in 0..field_gate_count {
                        let catalysts = cohort
                            .anatomy
                            .neuron_anatomies()
                            .iter()
                            .map(|anatomy| {
                                vec![0; anatomy.recovery_anatomy().psi_lane_count()]
                                    .into_boxed_slice()
                            })
                            .collect::<Vec<Box<[u128]>>>();
                        let field_gate_interval = shared
                            .result()
                            .gates
                            .get(field_gate_index)
                            .ok_or(FormationError::NoncanonicalState)?
                            .interval;
                        let gate_interval_microseconds = if vestibular.is_some() {
                            None
                        } else {
                            let first = occurrence
                                .source_times
                                .get(field_gate_interval.first_sev)
                                .ok_or(FormationError::NoncanonicalState)?;
                            let last = occurrence
                                .source_times
                                .get(field_gate_interval.last_sev)
                                .ok_or(FormationError::NoncanonicalState)?;
                            Some(exact_duration_microseconds(&(last - first))?)
                        };
                        let mut inputs = Vec::new();
                        inputs
                            .try_reserve_exact(coordinate_indices.len())
                            .map_err(|_| FormationError::ArithmeticOverflow)?;
                        // Stimulus-boundary truth signal (ratified 2026-08-05,
                        // extended to sound 2026-08-06): whether this settlement
                        // interval carried ANY exogenous RECEPTOR energy, derived
                        // from the occurrence's own delivered samples — the exact
                        // `2·L·T` integral each retinal site computes from the
                        // light that really fell on it, or the exact `K·∫s²dt`
                        // integral each cochlear site computes from the pressure
                        // that really reached it.  True dark samples and true
                        // silence both integrate to exactly zero.  `None` means
                        // the occurrence is governed by no receptor law at all
                        // (vestibular ingress), where no boundary law applies.
                        let mut exogenous_receptor_energy: Option<bool> = if vestibular.is_some() {
                            None
                        } else {
                            Some(false)
                        };
                        let mut receptor_excitation_zeptojoules =
                            vec![None; cohort.anatomy.neuron_count()];
                        for coordinate_index in coordinate_indices.iter().copied() {
                            let perspective = bind_neuron_perspective(
                                &shared,
                                coordinate_index,
                                field_gate_index,
                            )
                            .map_err(FormationError::JointFieldUnavailable)?;
                            let resident_index = cohort
                                .anatomy
                                .source_site_member(&reached_source_sites[coordinate_index])
                                .ok_or(FormationError::NeuronLineageAuthorityAbsent)?;
                            let (gate_work, interval_microseconds, receptor_successor_residue) =
                                if let Some(ingress) = vestibular {
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
                                        None,
                                    )
                                } else {
                                    // Quantized receptor transduction (light
                                    // ratified 2026-08-05, sound by the
                                    // 2026-08-06 auditory design): the receptor
                                    // law of THIS occurrence's sense computes an
                                    // exact transduced energy, that energy is
                                    // integrated into the site's retained
                                    // exact-rational accumulator, and whole
                                    // gate-lattice quanta are delivered as work
                                    // ONLY once the accumulation reaches the
                                    // receiving gate's own opening threshold; the
                                    // remainder is retained per-site state.  Both
                                    // senses take the SAME delivery law
                                    // (`receptor_quantum_delivery`), the same
                                    // accumulator field, the same gate window.
                                    // Reachable only under a governing receptor
                                    // law: the enclosing branch admits a
                                    // non-vestibular settlement exactly when
                                    // `receptor_law.is_some()`.  There is no
                                    // fallback law and no default sense.
                                    let law =
                                        receptor_law.ok_or(FormationError::NoncanonicalState)?;
                                    let neuron_anatomy =
                                        &cohort.anatomy.neuron_anatomies()[resident_index];
                                    let transduced_energy_zeptojoules = match law {
                                        ReceptorLaw::Sight => {
                                            let retinal_anatomy = exact_optical_receptor_anatomy(
                                                neuron_anatomy.gate_population(),
                                            )?;
                                            let settlement =
                                                derive_optical_receptor_sample_range_work(
                                                    source,
                                                    perspective,
                                                    &retinal_anatomy,
                                                    field_gate_interval.first_sev,
                                                    field_gate_interval.last_sev,
                                                )
                                                .map_err(FormationError::OpticalWorkUnavailable)?;
                                            settlement.transduced_energy_zeptojoules
                                        }
                                        ReceptorLaw::Sound => {
                                            let settlement =
                                                derive_auditory_receptor_sample_range_work(
                                                    source,
                                                    perspective,
                                                    &auditory_anatomy,
                                                    field_gate_interval.first_sev,
                                                    field_gate_interval.last_sev,
                                                )
                                                .map_err(FormationError::AuditoryWorkUnavailable)?;
                                            settlement.transduced_energy_zeptojoules
                                        }
                                        ReceptorLaw::Touch => {
                                            let settlement =
                                                derive_tactile_receptor_sample_range_work(
                                                    source,
                                                    perspective,
                                                    &tactile_anatomy,
                                                    field_gate_interval.first_sev,
                                                    field_gate_interval.last_sev,
                                                )
                                                .map_err(FormationError::TactileWorkUnavailable)?;
                                            settlement.transduced_energy_zeptojoules
                                        }
                                    };
                                    if !transduced_energy_zeptojoules.is_zero() {
                                        exogenous_receptor_energy = Some(true);
                                    }
                                    receptor_excitation_zeptojoules[resident_index] = Some(
                                        big_to_exact_rational(&transduced_energy_zeptojoules)
                                            .map_err(|_| FormationError::ArithmeticOverflow)?,
                                    );
                                    let predecessor_neuron =
                                        &cohort.state.neurons()[resident_index];
                                    let prepared_psi = neuron_anatomy
                                        .prepare_psi_settlement(predecessor_neuron, perspective)
                                        .map_err(|error| {
                                            FormationError::PhysicalSettlementUnavailable(
                                                ReachedCohortError::Neuron {
                                                    neuron_index: resident_index,
                                                    error,
                                                },
                                            )
                                        })?;
                                    let window = gate_opening_quantum_window_with_psi(
                                        &cohort.anatomy.neuron_anatomies()[resident_index],
                                        &cohort.state.neurons()[resident_index],
                                        &prepared_psi,
                                    )
                                    .map_err(|error| {
                                        FormationError::PhysicalSettlementUnavailable(
                                            ReachedCohortError::Neuron {
                                                neuron_index: resident_index,
                                                error,
                                            },
                                        )
                                    })?;
                                    let delivery = match law {
                                        ReceptorLaw::Sound => quantize_auditory_delivery(
                                            &transduced_energy_zeptojoules,
                                            cohort.state.neurons()[resident_index]
                                                .receptor_quantum_residue,
                                            cohort.anatomy.neuron_anatomies()[resident_index]
                                                .gate_dissipation_quantum_zeptojoules(),
                                            window.opening_threshold_quanta,
                                            window.window_cap_quanta,
                                        )
                                        .map_err(FormationError::AuditoryWorkUnavailable)?,
                                        ReceptorLaw::Sight
                                            if neuron_anatomy.gate_population() > 1 =>
                                        {
                                            let schedule =
                                                gate_population_opening_schedule_with_psi(
                                                    neuron_anatomy,
                                                    predecessor_neuron,
                                                    &prepared_psi,
                                                )
                                                .map_err(|error| {
                                                    FormationError::PhysicalSettlementUnavailable(
                                                        ReachedCohortError::Neuron {
                                                            neuron_index: resident_index,
                                                            error,
                                                        },
                                                    )
                                                })?;
                                            quantize_optical_population_delivery(
                                                &transduced_energy_zeptojoules,
                                                predecessor_neuron.receptor_quantum_residue,
                                                neuron_anatomy
                                                    .gate_dissipation_quantum_zeptojoules(),
                                                schedule.predecessor_open_population(),
                                                schedule.activation_quanta(),
                                            )
                                            .map_err(FormationError::OpticalWorkUnavailable)?
                                        }
                                        ReceptorLaw::Sight => quantize_optical_delivery(
                                            &transduced_energy_zeptojoules,
                                            predecessor_neuron.receptor_quantum_residue,
                                            neuron_anatomy.gate_dissipation_quantum_zeptojoules(),
                                            window.opening_threshold_quanta,
                                            window.window_cap_quanta,
                                        )
                                        .map_err(FormationError::OpticalWorkUnavailable)?,
                                        ReceptorLaw::Touch => quantize_tactile_delivery(
                                            &transduced_energy_zeptojoules,
                                            cohort.state.neurons()[resident_index]
                                                .receptor_quantum_residue,
                                            cohort.anatomy.neuron_anatomies()[resident_index]
                                                .gate_dissipation_quantum_zeptojoules(),
                                            window.opening_threshold_quanta,
                                            window.window_cap_quanta,
                                        )
                                        .map_err(FormationError::TactileWorkUnavailable)?,
                                    };
                                    (
                                        delivery.gate_work,
                                        gate_interval_microseconds
                                            .ok_or(FormationError::NoncanonicalState)?,
                                        Some((delivery.successor_residue, prepared_psi)),
                                    )
                                };
                            let (receptor_successor_residue, prepared_psi) =
                                match receptor_successor_residue {
                                    Some((residue, psi)) => (Some(residue), Some(psi)),
                                    None => {
                                        let prepared = cohort.anatomy.neuron_anatomies()
                                            [resident_index]
                                            .prepare_psi_settlement(
                                                &cohort.state.neurons()[resident_index],
                                                perspective,
                                            )
                                            .map_err(|error| {
                                                FormationError::PhysicalSettlementUnavailable(
                                                    ReachedCohortError::Neuron {
                                                        neuron_index: resident_index,
                                                        error,
                                                    },
                                                )
                                            })?;
                                        (None, Some(prepared))
                                    }
                                };
                            inputs.push(NeuronIntervalInput {
                                perspective,
                                gate_work,
                                interval_microseconds,
                                recovery: RecoveryContact::new(&catalysts[resident_index], 0, 0),
                                dna_expression: DnaExpressionContact::new(0),
                                receptor_successor_residue,
                                prepared_psi,
                            });
                        }
                        let input = ReachedCohortIntervalInput::from_episode(source, inputs)
                            .map_err(FormationError::PhysicalSettlementUnavailable)?;
                        let gate_work_perturbed_neurons = input
                            .resident_gate_work_bits(&cohort.anatomy)
                            .map_err(FormationError::PhysicalSettlementUnavailable)?;
                        let interval_predecessor_neurons = cohort.state.neurons().to_vec();
                        let outcome = settle_resident_physical_interval(
                            &mut cohort,
                            input,
                            gate_work_perturbed_neurons,
                            receptor_excitation_zeptojoules,
                            exogenous_receptor_energy,
                            &mosaics,
                            max_encoded_bytes,
                            source_generation,
                        )?;
                        for ((predecessor, successor), lineage) in interval_predecessor_neurons
                            .iter()
                            .zip(cohort.state.neurons())
                            .zip(cohort.anatomy.neuron_lineages())
                        {
                            if predecessor != successor
                                && !physically_transitioned_neuron_lineages.contains(lineage)
                            {
                                physically_transitioned_neuron_lineages.push(*lineage);
                            }
                        }
                        metabolic.recovered_neuron_count = metabolic
                            .recovered_neuron_count
                            .checked_add(outcome.metabolic.recovered_neuron_count)
                            .ok_or(FormationError::ArithmeticOverflow)?;
                        metabolic.drained_dissipation_quanta = metabolic
                            .drained_dissipation_quanta
                            .checked_add(outcome.metabolic.drained_dissipation_quanta)
                            .ok_or(FormationError::ArithmeticOverflow)?;
                        metabolic.unmet_dissipation_quanta =
                            outcome.metabolic.unmet_dissipation_quanta;
                        metabolic.returned_elementary_charges = metabolic
                            .returned_elementary_charges
                            .checked_add(outcome.metabolic.returned_elementary_charges)
                            .ok_or(FormationError::ArithmeticOverflow)?;
                        metabolic.unreturned_elementary_charges =
                            outcome.metabolic.unreturned_elementary_charges;
                        metabolic.fuel_quanta = metabolic
                            .fuel_quanta
                            .checked_add(outcome.metabolic.fuel_quanta)
                            .ok_or(FormationError::ArithmeticOverflow)?;
                        emitted_neuron_fractals.extend(outcome.emitted_neuron_fractals);
                        partial_cue_reassembly_count = partial_cue_reassembly_count
                            .checked_add(outcome.partial_cue_reassembly_count)
                            .ok_or(FormationError::ArithmeticOverflow)?;
                        endogenous_partial_cue_reassembly_count =
                            endogenous_partial_cue_reassembly_count
                                .checked_add(outcome.endogenous_partial_cue_reassembly_count)
                                .ok_or(FormationError::ArithmeticOverflow)?;
                        if outcome.mosaic_formed.is_some() {
                            mosaic_formed = outcome.mosaic_formed;
                        }
                        for resolution in outcome.mosaic_resolutions {
                            apply_mosaic_structural_resolution(&mut mosaics, resolution)?;
                        }
                        // No episode is admitted to cold custody any more, so
                        // nothing is prepared, published or navigated here.  A
                        // reassembly's receipt is `mosaic_formed`, which is the
                        // sha256 of the admitted mosaic's own encoded body — a
                        // digest of a physical structure she holds, rather than
                        // the address of an archived file.
                    }
                }
                // One admitted occurrence may contain many complete-field gate
                // intervals. Emit at most one cumulative retained delta per
                // reached neuron after all of those local settlements; never
                // expose each internal gate as a separate experience.
                for (neuron_index, (predecessor, successor)) in occurrence_predecessor_state
                    .neurons()
                    .iter()
                    .zip(cohort.state.neurons())
                    .enumerate()
                {
                    if let Some(delta) = sparse_retained_physical_state_delta(
                        predecessor,
                        successor,
                    )
                    .map_err(|error| {
                        FormationError::PhysicalSettlementUnavailable(ReachedCohortError::Neuron {
                            neuron_index,
                            error,
                        })
                    })? {
                        emitted_neuron_fractals.push(EmittedNeuronFractal {
                            neuron_lineage: cohort.anatomy.neuron_lineages()[neuron_index],
                            delta,
                        });
                    }
                }
                for coordinate_index in coordinate_indices.iter().copied() {
                    let resident_index = cohort
                        .anatomy
                        .source_site_member(&reached_source_sites[coordinate_index])
                        .ok_or(FormationError::NeuronLineageAuthorityAbsent)?;
                    let lineage = cohort.anatomy.neuron_lineages()[resident_index];
                    if !externally_reached_neuron_lineages.contains(&lineage) {
                        externally_reached_neuron_lineages.push(lineage);
                    }
                    if !externally_reached_by_occurrence[occurrence_index].contains(&lineage) {
                        externally_reached_by_occurrence[occurrence_index].push(lineage);
                    }
                }
                if cohort_index < cohorts.len() {
                    cohorts[cohort_index] = cohort;
                } else {
                    cohorts.push(cohort);
                }
            }
        }
        let mut electrical_fabric = predecessor_electrical_fabric;
        mount_reached_local_integration(
            &mut cohorts,
            &mut resting_population,
            &mut next_lineage_ordinal,
            &mut electrical_fabric,
        )?;
        for occurrence_lineages in &externally_reached_by_occurrence {
            mount_reached_cross_sensory_association(
                &mut cohorts,
                &mut resting_population,
                &mut next_lineage_ordinal,
                &mut electrical_fabric,
                occurrence_lineages,
            )?;
            mount_reached_body_regulation(
                &mut cohorts,
                &mut resting_population,
                &mut next_lineage_ordinal,
                &mut electrical_fabric,
                occurrence_lineages,
            )?;
        }
        let internal_contact = settle_internal_contact_interval(
            &mut cohorts,
            &mut electrical_fabric,
            &externally_reached_neuron_lineages,
            &mut physically_transitioned_neuron_lineages,
            &mut emitted_neuron_fractals,
        )?;
        dsf_delivery_count = dsf_delivery_count
            .checked_add(internal_contact.dsf_delivery_count)
            .ok_or(FormationError::ArithmeticOverflow)?;
        mount_reached_affective_reach(
            &mut cohorts,
            &mut resting_population,
            &mut next_lineage_ordinal,
            &mut electrical_fabric,
            &physically_transitioned_neuron_lineages,
        )?;
        let (organism_mosaic_receipt, organism_reassemblies) = settle_organism_mosaic_boundary(
            &cohorts,
            &electrical_fabric,
            &emitted_neuron_fractals,
            &externally_reached_neuron_lineages,
            &internal_contact.active_bonds,
            &mut mosaics,
            max_encoded_bytes,
        )?;
        if organism_mosaic_receipt.is_some() {
            mosaic_formed = organism_mosaic_receipt;
        }
        partial_cue_reassembly_count = partial_cue_reassembly_count
            .checked_add(organism_reassemblies)
            .ok_or(FormationError::ArithmeticOverflow)?;
        let newly_retained_mosaic_members = mosaics
            .iter()
            .filter(|retained| retained.mosaic.carries_only_retained_neuron_structure())
            .filter(|retained| {
                !predecessor_recognized_mosaics
                    .iter()
                    .any(|prior| prior.same_retained_structure(&retained.mosaic))
            })
            .map(|retained| retained.mosaic.member_lineages().to_vec())
            .collect::<Vec<_>>();
        mount_new_recurrent_retention(
            &mut cohorts,
            &mut resting_population,
            &mut next_lineage_ordinal,
            &mut electrical_fabric,
            &newly_retained_mosaic_members,
        )?;
        let successor = Self {
            generation: source_generation,
            next_lineage_ordinal,
            unexpressed_electrical_seeds: unexpressed_electrical_seeds.into_boxed_slice(),
            dormant_lineage_seeds: dormant_lineage_seeds.into_boxed_slice(),
            resting_population,
            cohorts: cohorts.into_boxed_slice(),
            electrical_fabric,
            mosaics: mosaics.into_boxed_slice(),
            hippocampal,
        };
        let successor_encoded = if seal_successor {
            successor.encode(max_encoded_bytes)?
        } else {
            Vec::new()
        };
        let summary = successor.summary();
        let successor_energy = summary.energy;
        let complete_neuron_count = summary.complete_neuron_count;
        let physically_transitioned_neuron_count = physically_transitioned_neuron_lineages.len();
        let complete_neuron_fractal_count = emitted_neuron_fractals.len();
        let mosaic_of_mosaics_count = successor.mosaic_of_mosaics_count()?;
        Ok(PreparedCognitiveFormationTransition {
            predecessor_generation: predecessor_generation_authority,
            predecessor_hippocampal: predecessor_hippocampal_authority,
            successor,
            successor_encoded,
            observation: CognitiveFormationObservation {
                cognitive_ordinal: source_generation,
                trace_formed: false,
                mosaic_formed,
                activations: Vec::new(),
                trace_count: 0,
                mosaic_count: summary.mosaic_count,
                dsf_delivery_count,
                complete_neuron_count,
                resting_neuron_count: summary.resting_neuron_count,
                physically_transitioned_neuron_count,
                complete_neuron_fractal_count,
                emitted_neuron_fractals,
                partial_cue_reassembly_count,
                endogenous_partial_cue_reassembly_count,
                mosaic_of_mosaics_count,
                rest_recovered_neuron_count: metabolic.recovered_neuron_count,
                rest_drained_dissipation_quanta: metabolic.drained_dissipation_quanta,
                unmet_dissipation_quanta: metabolic.unmet_dissipation_quanta,
                membrane_returned_elementary_charges: metabolic.returned_elementary_charges,
                membrane_unreturned_elementary_charges: metabolic.unreturned_elementary_charges,
                metabolic_fuel_quanta: metabolic.fuel_quanta,
                nutrition_regenerated_fuel_quanta: 0,
                nutrition_unabsorbed_waste_quanta: 0,
                nutrition_vented_heat_quanta: 0,
                energy: successor_energy,
            },
        })
    }

    pub(crate) fn advance_vestibular_transition(
        self,
        ingress: &ResidentVestibularIngress,
        max_encoded_bytes: usize,
    ) -> Result<(Self, CognitiveFormationObservation), FormationError> {
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
        let predecessor_generation = self.generation;
        let predecessor_hippocampal = self.hippocampal;
        let retired = self.retire_aliased_local_integrators()?;
        let expanded = retired
            .unwrap_or(self)
            .into_expanded_legacy_sight_channel_populations()?;
        let prepared = Self::prepare_typed_admitted_transition_from_owned(
            expanded,
            predecessor_generation,
            predecessor_hippocampal,
            &admitted_source,
            Some(ingress),
            max_encoded_bytes,
            false,
        )?;
        Ok((prepared.successor, prepared.observation))
    }

    /// Deliver one AUTHORED nutrition declaration to the body.
    ///
    /// This is an intake, not a sensory occurrence: it advances the cognitive
    /// generation and nothing else.  The declaration's energy is allocated to
    /// the cohorts that can actually absorb it, in mounted order; whatever no
    /// cohort can absorb leaves as waste, and every cohort's accumulated heat
    /// is vented by the same exchange.  A body that can absorb nothing at all
    /// refuses the intake outright rather than pretending to eat.
    /// Read-only structural observation of the living cohorts' authored
    /// anatomy: one entry per cohort as `(member_count, contact_count)`.
    /// Reading advances nothing.
    pub(crate) fn observe_cohort_contacts(&self) -> Vec<(usize, usize)> {
        self.cohorts
            .iter()
            .map(|cohort| {
                (
                    cohort.anatomy.neuron_count(),
                    cohort.anatomy.contact_count(),
                )
            })
            .collect()
    }

    /// Count reached neurons anchored to one exact declared physical source.
    /// This observes persisted source anatomy only; it assigns no meaning and
    /// advances no state.
    pub(crate) fn observe_reached_source_site_count(
        &self,
        sensor_id: &str,
        substream_id: &str,
    ) -> usize {
        self.cohorts
            .iter()
            .flat_map(|cohort| cohort.anatomy.source_sites())
            .filter(|site| site.sensor_id() == sensor_id && site.substream_id() == substream_id)
            .count()
    }

    /// Append caller-AUTHORED contacts to the living cohorts.
    ///
    /// This is developmental authorship, not sensation and not inference: the
    /// caller names two of its own declared receptors and the conductance of
    /// the contact between them, exactly as growth DNA does at genesis, and
    /// this boundary only resolves those declared names against the members
    /// that already carry them.  Nothing here reads adjacency, coordinates,
    /// storage order, activity, similarity, or semantics.
    ///
    /// Members, lineages, source sites, physical states, retained mosaics and
    /// the hippocampal index all travel through verbatim; only the contact
    /// list grows, only at its end.  Every authored contact must join two
    /// members of one cohort — a contact between cohorts would be an inferred
    /// connection — and a pair that is already contacted is refused rather
    /// than authored twice.
    pub(crate) fn prepare_authored_contacts(
        &self,
        authored: &[AuthoredDeclaredContact],
        max_encoded_bytes: usize,
    ) -> Result<PreparedCognitiveFormationTransition, FormationError> {
        // No episode is admitted, so — exactly as for nutrition — the
        // hippocampal index is untouched and no publication is required.
        if authored.is_empty() || self.cohorts.is_empty() {
            return Err(FormationError::AuthoredContactUnavailable);
        }
        let source_generation = self
            .generation
            .checked_add(1)
            .ok_or(FormationError::InvalidSourceGeneration)?;
        let mut per_cohort: Vec<Vec<(usize, usize, ExactRational)>> =
            vec![Vec::new(); self.cohorts.len()];
        for contact in authored {
            let mut resolved = None;
            for (cohort_index, cohort) in self.cohorts.iter().enumerate() {
                let left = declared_site_member(
                    &cohort.anatomy,
                    &contact.left_sensor_id,
                    &contact.left_substream_id,
                )?;
                let right = declared_site_member(
                    &cohort.anatomy,
                    &contact.right_sensor_id,
                    &contact.right_substream_id,
                )?;
                if let (Some(left), Some(right)) = (left, right) {
                    if resolved.is_some() {
                        return Err(FormationError::AuthoredContactUnavailable);
                    }
                    resolved = Some((cohort_index, left, right));
                } else if left.is_some() || right.is_some() {
                    // One endpoint resident here and one elsewhere: the
                    // caller named a connection this organism cannot have.
                    return Err(FormationError::AuthoredContactUnavailable);
                }
            }
            let (cohort_index, left, right) =
                resolved.ok_or(FormationError::AuthoredContactUnavailable)?;
            per_cohort[cohort_index].push((left, right, contact.conductance_picosiemens));
        }
        let mut cohorts = self.cohorts.to_vec();
        for (cohort, additions) in cohorts.iter_mut().zip(per_cohort) {
            if additions.is_empty() {
                continue;
            }
            let (anatomy, state) =
                extend_reached_cohort_contacts(&cohort.anatomy, &cohort.state, additions)
                    .map_err(FormationError::PhysicalSettlementUnavailable)?;
            let added = anatomy
                .contact_count()
                .checked_sub(cohort.anatomy.contact_count())
                .ok_or(FormationError::ArithmeticOverflow)?;
            // The rest-state snapshots and per-contact activity masks this
            // cohort retains at its experience boundaries are widened the same
            // way: existing entries verbatim, and each newly authored contact
            // recorded as it truthfully was in that experience — at the
            // authored rest state and NOT active, because it did not exist.
            for evidence in [
                cohort.pending_experience.as_mut(),
                cohort.retained_experience.as_mut(),
            ]
            .into_iter()
            .flatten()
            {
                evidence.pre_experience_rest =
                    widen_reached_cohort_state_contacts(&anatomy, &evidence.pre_experience_rest)
                        .map_err(FormationError::PhysicalSettlementUnavailable)?;
                if let Some(post) = evidence.post_experience_rest.as_mut() {
                    *post = widen_reached_cohort_state_contacts(&anatomy, post)
                        .map_err(FormationError::PhysicalSettlementUnavailable)?;
                }
                evidence.active_electrical_contacts =
                    extend_contact_mask(&evidence.active_electrical_contacts, added)?;
            }
            if let Some(recurrence) = cohort.pending_recurrence.as_mut() {
                recurrence.active_recurrence_contacts =
                    extend_contact_mask(&recurrence.active_recurrence_contacts, added)?;
            }
            cohort.anatomy = anatomy;
            cohort.state = state;
        }
        let successor = Self {
            generation: source_generation,
            next_lineage_ordinal: self.next_lineage_ordinal,
            unexpressed_electrical_seeds: self.unexpressed_electrical_seeds.clone(),
            dormant_lineage_seeds: self.dormant_lineage_seeds.clone(),
            resting_population: self.resting_population.clone(),
            cohorts: cohorts.into_boxed_slice(),
            electrical_fabric: self.electrical_fabric.clone(),
            mosaics: self.mosaics.clone(),
            hippocampal: self.hippocampal,
        };
        // Every retained mosaic must still be expressible against the grown
        // anatomy, or the growth is refused and the body is left as it is.
        let successor_encoded = successor.encode(max_encoded_bytes)?;
        let summary = successor.summary();
        let mosaic_of_mosaics_count = successor.mosaic_of_mosaics_count()?;
        Ok(PreparedCognitiveFormationTransition {
            predecessor_generation: self.generation,
            predecessor_hippocampal: self.hippocampal,
            successor,
            successor_encoded,
            observation: CognitiveFormationObservation {
                cognitive_ordinal: source_generation,
                trace_formed: false,
                mosaic_formed: None,
                activations: Vec::new(),
                trace_count: summary.trace_count,
                mosaic_count: summary.mosaic_count,
                dsf_delivery_count: 0,
                complete_neuron_count: summary.complete_neuron_count,
                resting_neuron_count: summary.resting_neuron_count,
                physically_transitioned_neuron_count: 0,
                complete_neuron_fractal_count: 0,
                emitted_neuron_fractals: Vec::new(),
                partial_cue_reassembly_count: 0,
                endogenous_partial_cue_reassembly_count: 0,
                mosaic_of_mosaics_count,
                rest_recovered_neuron_count: 0,
                rest_drained_dissipation_quanta: 0,
                unmet_dissipation_quanta: 0,
                membrane_returned_elementary_charges: 0,
                membrane_unreturned_elementary_charges: summary.energy.separated_elementary_charges,
                metabolic_fuel_quanta: 0,
                nutrition_regenerated_fuel_quanta: 0,
                nutrition_unabsorbed_waste_quanta: 0,
                nutrition_vented_heat_quanta: 0,
                energy: summary.energy,
            },
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
        self.encode_with_format(CognitiveCodecFormat::V16, max_encoded_bytes)
    }

    fn encode_with_format(
        &self,
        format: CognitiveCodecFormat,
        max_encoded_bytes: usize,
    ) -> Result<Vec<u8>, FormationError> {
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
        let resting_population = match format {
            CognitiveCodecFormat::V15 | CognitiveCodecFormat::V16 => self
                .resting_population
                .as_ref()
                .map(DevelopmentalRestingPopulation::encode)
                .transpose()
                .map_err(FormationError::DevelopmentalRestingPopulationUnavailable)?,
            CognitiveCodecFormat::V12 | CognitiveCodecFormat::V13 | CognitiveCodecFormat::V14 => {
                if self.resting_population.is_some() {
                    return Err(FormationError::NoncanonicalState);
                }
                None
            }
        };
        if matches!(
            format,
            CognitiveCodecFormat::V15 | CognitiveCodecFormat::V16
        ) {
            length = length
                .checked_add(8)
                .and_then(|value| {
                    resting_population
                        .as_ref()
                        .map_or(Some(value), |population| {
                            value.checked_add(population.len())
                        })
                })
                .ok_or(FormationError::ArithmeticOverflow)?;
        }
        for cohort in &self.cohorts {
            if cohort
                .pending_experience
                .as_ref()
                .is_some_and(|evidence| evidence.post_experience_rest.is_some())
                || cohort
                    .retained_experience
                    .as_ref()
                    .is_some_and(|evidence| evidence.post_experience_rest.is_none())
                || (cohort.pending_experience.is_some() && cohort.retained_experience.is_some())
            {
                return Err(FormationError::NoncanonicalState);
            }
            let cell = match format {
                CognitiveCodecFormat::V12 => {
                    encode_reached_cohort_cell(&cohort.anatomy, &cohort.state)
                }
                CognitiveCodecFormat::V13 => {
                    encode_reached_cohort_cell_v5(&cohort.anatomy, &cohort.state)
                }
                CognitiveCodecFormat::V14 => encode_reached_cohort_cell_v5_with_contact_plasticity(
                    &cohort.anatomy,
                    &cohort.state,
                ),
                CognitiveCodecFormat::V15 => encode_reached_cohort_cell_v5_with_contact_plasticity(
                    &cohort.anatomy,
                    &cohort.state,
                ),
                CognitiveCodecFormat::V16 => {
                    encode_reached_cohort_cell_v6(&cohort.anatomy, &cohort.state)
                }
            }
            .map_err(|_| FormationError::NoncanonicalState)?;
            let encode_evidence = |evidence: &ResidentExperienceEvidence| {
                encode_experience_evidence_v2(
                    &cohort.anatomy,
                    if format == CognitiveCodecFormat::V12 {
                        None
                    } else {
                        Some(&cohort.state)
                    },
                    evidence,
                    matches!(
                        format,
                        CognitiveCodecFormat::V14
                            | CognitiveCodecFormat::V15
                            | CognitiveCodecFormat::V16
                    ),
                )
            };
            let pending = cohort
                .pending_experience
                .as_ref()
                .map(encode_evidence)
                .transpose()?;
            let retained = cohort
                .retained_experience
                .as_ref()
                .map(encode_evidence)
                .transpose()?;
            let recurrence = cohort
                .pending_recurrence
                .as_ref()
                .map(|evidence| encode_recurrence_evidence(&cohort.anatomy, evidence))
                .transpose()?;
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
        if self.mosaics.iter().enumerate().any(|(index, retained)| {
            self.mosaics[..index]
                .iter()
                .any(|prior| prior.mosaic == retained.mosaic)
        }) {
            return Err(FormationError::NoncanonicalState);
        }
        let mosaics = self
            .mosaics
            .iter()
            .map(|retained| {
                encode_retained_organism_mosaic(
                    &self.cohorts,
                    &self.electrical_fabric,
                    retained,
                    max_encoded_bytes,
                )
            })
            .collect::<Result<Vec<_>, _>>()?;
        length = mosaics
            .iter()
            .try_fold(length, |total, mosaic| {
                total.checked_add(8)?.checked_add(mosaic.len())
            })
            .ok_or(FormationError::ArithmeticOverflow)?;
        let electrical_fabric = if format == CognitiveCodecFormat::V16 {
            let encoded = self
                .electrical_fabric
                .encode()
                .map_err(FormationError::ResidentElectricalUnavailable)?;
            length = length
                .checked_add(8)
                .and_then(|value| value.checked_add(encoded.len()))
                .ok_or(FormationError::ArithmeticOverflow)?;
            Some(encoded)
        } else {
            if self.electrical_fabric != ResidentElectricalFabric::default() {
                return Err(FormationError::NoncanonicalState);
            }
            None
        };
        if length > max_encoded_bytes {
            return Err(FormationError::BudgetExceeded {
                required: length,
                available: max_encoded_bytes,
            });
        }
        let mut output = Vec::with_capacity(length);
        match format {
            CognitiveCodecFormat::V12 => {
                output.extend_from_slice(MAGIC);
                output.extend_from_slice(&VERSION.to_le_bytes());
            }
            CognitiveCodecFormat::V13 => {
                output.extend_from_slice(MAGIC_V13);
                output.extend_from_slice(&VERSION_V13.to_le_bytes());
            }
            CognitiveCodecFormat::V14 => {
                output.extend_from_slice(MAGIC_V14);
                output.extend_from_slice(&VERSION_V14.to_le_bytes());
            }
            CognitiveCodecFormat::V15 => {
                output.extend_from_slice(MAGIC_V15);
                output.extend_from_slice(&VERSION_V15.to_le_bytes());
            }
            CognitiveCodecFormat::V16 => {
                output.extend_from_slice(MAGIC_V16);
                output.extend_from_slice(&VERSION_V16.to_le_bytes());
            }
        }
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
        if matches!(
            format,
            CognitiveCodecFormat::V15 | CognitiveCodecFormat::V16
        ) {
            push_length(&mut output, resting_population.as_ref().map_or(0, Vec::len))?;
            if let Some(population) = resting_population {
                output.extend_from_slice(&population);
            }
        }
        if format == CognitiveCodecFormat::V16 {
            let electrical_fabric = electrical_fabric.ok_or(FormationError::NoncanonicalState)?;
            push_length(&mut output, electrical_fabric.len())?;
            output.extend_from_slice(&electrical_fabric);
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
            .map_err(FormationError::HippocampalCheckpointUnavailable)?;
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
        if self.generation != prepared.predecessor_generation {
            return Err(FormationError::PreparedPredecessorChanged);
        }
        if prepared.successor_encoded.len() > max_encoded_bytes {
            return Err(FormationError::BudgetExceeded {
                required: prepared.successor_encoded.len(),
                available: max_encoded_bytes,
            });
        }
        Ok(prepared.successor_encoded.clone())
    }

    /// The retired archive checkpoint must survive a transition byte-for-byte.
    /// Nothing writes it, so a successor whose checkpoint differs from its
    /// predecessor's is a codec fault, not a lawful advance.
    pub(crate) fn encode_staged_successor(
        &self,
        prepared: &PreparedCognitiveFormationTransition,
        max_encoded_bytes: usize,
    ) -> Result<Vec<u8>, FormationError> {
        if self.generation != prepared.predecessor_generation {
            return Err(FormationError::PreparedPredecessorChanged);
        }
        if prepared.successor.hippocampal != prepared.predecessor_hippocampal {
            return Err(FormationError::NoncanonicalState);
        }
        if prepared.successor_encoded.len() > max_encoded_bytes {
            return Err(FormationError::BudgetExceeded {
                required: prepared.successor_encoded.len(),
                available: max_encoded_bytes,
            });
        }
        Ok(prepared.successor_encoded.clone())
    }

    pub(crate) fn decode(bytes: &[u8], max_encoded_bytes: usize) -> Result<Self, FormationError> {
        Self::decode_with_canonicality(bytes, max_encoded_bytes, true)
    }

    fn decode_for_one_way_migration(
        bytes: &[u8],
        max_encoded_bytes: usize,
    ) -> Result<Self, FormationError> {
        Self::decode_with_canonicality(bytes, max_encoded_bytes, false)
    }

    fn decode_with_canonicality(
        bytes: &[u8],
        max_encoded_bytes: usize,
        require_current_canonical_encoding: bool,
    ) -> Result<Self, FormationError> {
        if bytes.len() > max_encoded_bytes {
            return Err(FormationError::BudgetExceeded {
                required: bytes.len(),
                available: max_encoded_bytes,
            });
        }
        let format = if bytes.len() >= MAGIC_V16.len() && &bytes[..MAGIC_V16.len()] == MAGIC_V16 {
            CognitiveCodecFormat::V16
        } else if bytes.len() >= MAGIC_V15.len() && &bytes[..MAGIC_V15.len()] == MAGIC_V15 {
            CognitiveCodecFormat::V15
        } else if bytes.len() >= MAGIC_V14.len() && &bytes[..MAGIC_V14.len()] == MAGIC_V14 {
            CognitiveCodecFormat::V14
        } else if bytes.len() >= MAGIC_V13.len() && &bytes[..MAGIC_V13.len()] == MAGIC_V13 {
            CognitiveCodecFormat::V13
        } else if bytes.len() >= MAGIC.len() && &bytes[..MAGIC.len()] == MAGIC {
            CognitiveCodecFormat::V12
        } else if bytes.len() >= MAGIC.len() {
            return Err(FormationError::RetiredCognitiveState);
        } else {
            return Err(FormationError::NoncanonicalState);
        };
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
        let expected_version = match format {
            CognitiveCodecFormat::V12 => VERSION,
            CognitiveCodecFormat::V13 => VERSION_V13,
            CognitiveCodecFormat::V14 => VERSION_V14,
            CognitiveCodecFormat::V15 => VERSION_V15,
            CognitiveCodecFormat::V16 => VERSION_V16,
        };
        if version != expected_version {
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
        let resting_population = if matches!(
            format,
            CognitiveCodecFormat::V15 | CognitiveCodecFormat::V16
        ) {
            let population_length = read_length(bytes, &mut cursor)?;
            if population_length == 0 {
                None
            } else {
                let population_end = cursor
                    .checked_add(population_length)
                    .ok_or(FormationError::ArithmeticOverflow)?;
                let population = DevelopmentalRestingPopulation::decode(
                    bytes
                        .get(cursor..population_end)
                        .ok_or(FormationError::NoncanonicalState)?,
                )
                .map_err(FormationError::DevelopmentalRestingPopulationUnavailable)?;
                cursor = population_end;
                Some(population)
            }
        } else {
            None
        };
        let electrical_fabric = if format == CognitiveCodecFormat::V16 {
            let fabric_length = read_length(bytes, &mut cursor)?;
            let fabric_end = cursor
                .checked_add(fabric_length)
                .ok_or(FormationError::ArithmeticOverflow)?;
            let fabric = ResidentElectricalFabric::decode(
                bytes
                    .get(cursor..fabric_end)
                    .ok_or(FormationError::NoncanonicalState)?,
            )
            .map_err(FormationError::ResidentElectricalUnavailable)?;
            cursor = fabric_end;
            fabric
        } else {
            ResidentElectricalFabric::default()
        };
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
            .map_err(FormationError::PhysicalSettlementUnavailable)?;
            cursor = cell_end;
            let pending_experience =
                decode_optional_experience_evidence(bytes, &mut cursor, &anatomy, &state, false)?;
            let retained_experience =
                decode_optional_experience_evidence(bytes, &mut cursor, &anatomy, &state, true)?;
            let pending_recurrence =
                decode_optional_recurrence_evidence(bytes, &mut cursor, &anatomy)?;
            if pending_experience.is_some() && retained_experience.is_some() {
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
            let retained = decode_retained_organism_mosaic(
                &cohorts,
                &electrical_fabric,
                bytes
                    .get(cursor..mosaic_end)
                    .ok_or(FormationError::NoncanonicalState)?,
                max_encoded_bytes,
            )?;
            cursor = mosaic_end;
            if mosaics
                .iter()
                .any(|prior: &RetainedOrganismMosaic| prior.mosaic == retained.mosaic)
            {
                return Err(FormationError::NoncanonicalState);
            }
            mosaics.push(retained);
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
        .map_err(FormationError::HippocampalCheckpointUnavailable)?;
        cursor = hippocampal_end;
        if cursor != bytes.len() {
            return Err(FormationError::NoncanonicalState);
        }
        let state = Self {
            generation,
            next_lineage_ordinal,
            unexpressed_electrical_seeds: unexpressed_electrical_seeds.into_boxed_slice(),
            dormant_lineage_seeds: dormant_lineage_seeds.into_boxed_slice(),
            resting_population,
            cohorts: cohorts.into_boxed_slice(),
            electrical_fabric,
            mosaics: mosaics.into_boxed_slice(),
            hippocampal,
        };
        validate_lineage_state(&state)?;
        let canonical = state.encode_with_format(format, max_encoded_bytes)?;
        if require_current_canonical_encoding && canonical != bytes {
            return Err(FormationError::NoncanonicalState);
        }
        Ok(state)
    }

    /// Rewrite one already-admitted body into the current `GLCOG015` layout.
    /// Existing reached cells and learned physical state remain exact.  The
    /// migration adds the resource-derived source-independent resting
    /// population once; repeating migration is byte-idempotent.
    pub(crate) fn migrate_to_current_format(
        bytes: &[u8],
        max_encoded_bytes: usize,
    ) -> Result<Vec<u8>, FormationError> {
        let state = Self::decode_for_one_way_migration(bytes, max_encoded_bytes)?;
        if state.resting_population.is_some() {
            return state.encode(max_encoded_bytes);
        }

        // Measure the exact current reached body in the immediately preceding
        // V14 cell layout.  Population admission then reserves one complete
        // independently diverged cell plus one sparse contact per declared
        // resting cell, while retaining one further unit for future growth.
        let predecessor = state.encode_with_format(CognitiveCodecFormat::V14, max_encoded_bytes)?;
        let mut occupied_places = state
            .cohorts
            .iter()
            .flat_map(|cohort| cohort.anatomy.mounts().iter())
            .map(ReachedNeuronMount::place)
            .collect::<Vec<_>>();
        occupied_places.extend(
            state
                .dormant_lineage_seeds
                .iter()
                .map(|seed| DeclaredNeuronPlace::new(u32::from(seed.sense), seed.topology_index)),
        );
        let population = DevelopmentalRestingPopulation::admit(
            max_encoded_bytes,
            predecessor.len(),
            state.next_lineage_ordinal,
            &occupied_places,
        )
        .map_err(FormationError::DevelopmentalRestingPopulationUnavailable)?;
        let next_lineage_ordinal = population.lineage_end_exclusive();
        let successor = Self {
            next_lineage_ordinal,
            resting_population: Some(population),
            ..state
        };
        validate_lineage_state(&successor)?;
        successor.encode(max_encoded_bytes)
    }
}

struct ResidentOpticalIntervalOutcome {
    emitted_neuron_fractals: Vec<EmittedNeuronFractal>,
    mosaic_formed: Option<[u8; 32]>,
    /// How this interval's admitted reassembly, if any, relates to the
    /// retained mosaic references under the R1 structural-identity boundary.
    mosaic_resolutions: Vec<MosaicStructuralResolution>,
    partial_cue_reassembly_count: usize,
    endogenous_partial_cue_reassembly_count: usize,
    /// What the rest metabolism did on this interval (zero on every interval
    /// that carried exogenous stimulus energy).
    metabolic: ReachedCohortMetabolicObservation,
}

/// Exact retained-formation resolution.  Identity is the original retained
/// neuronal deltas and their original physical bonds, never the member set.
/// The same neurons may participate in many different formations.  A later
/// cue or recurrence path may vary while reassembling the same retained
/// structure, so those later-path facts do not mint a duplicate formation.
#[derive(Clone, Debug, Eq, PartialEq)]
enum MosaicStructuralResolution {
    /// No retained formation carries the same exact original structure.
    NewFormation(AdmittedPhysicalMosaic),
    /// The exact original retained neuronal structure already exists.
    Reinforces { mosaic_index: usize },
}

/// Resolve one admitted reassembly against retained physical formations.
fn resolve_mosaic_structural_identity(
    existing: &[RetainedOrganismMosaic],
    candidate: AdmittedPhysicalMosaic,
) -> MosaicStructuralResolution {
    if let Some(mosaic_index) = existing
        .iter()
        .position(|prior| prior.mosaic.same_retained_structure(&candidate))
    {
        return MosaicStructuralResolution::Reinforces { mosaic_index };
    }
    MosaicStructuralResolution::NewFormation(candidate)
}

/// Apply one exact retained-formation resolution.
fn apply_mosaic_structural_resolution(
    mosaics: &mut Vec<RetainedOrganismMosaic>,
    resolution: MosaicStructuralResolution,
) -> Result<(), FormationError> {
    match resolution {
        MosaicStructuralResolution::NewFormation(mosaic) => {
            mosaics
                .try_reserve(1)
                .map_err(|_| FormationError::ArithmeticOverflow)?;
            mosaics.push(RetainedOrganismMosaic::newly_admitted(mosaic));
        }
        MosaicStructuralResolution::Reinforces { mosaic_index } => {
            let retained = mosaics
                .get_mut(mosaic_index)
                .ok_or(FormationError::NoncanonicalState)?;
            retained.reinforcement_count = retained
                .reinforcement_count
                .checked_add(1)
                .ok_or(FormationError::ArithmeticOverflow)?;
        }
    }
    Ok(())
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
        evidence.pre_experience_rest = extend_reached_cohort_state_with_genesis(
            predecessor_anatomy,
            &evidence.pre_experience_rest,
            &successor_anatomy,
            genesis_states,
        )
        .map_err(FormationError::PhysicalSettlementUnavailable)?;
        evidence.post_experience_rest = evidence
            .post_experience_rest
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
        let mut excitation = evidence.receptor_excitation_zeptojoules.to_vec();
        excitation.resize(successor_anatomy.neuron_count(), None);
        evidence.receptor_excitation_zeptojoules = excitation.into_boxed_slice();
        let mut retained_change = evidence.retained_change_neurons.to_vec();
        retained_change.resize(successor_anatomy.neuron_count(), false);
        evidence.retained_change_neurons = retained_change.into_boxed_slice();
        let mut settled = evidence.retentively_settled_neurons.to_vec();
        settled.resize(successor_anatomy.neuron_count(), false);
        evidence.retentively_settled_neurons = settled.into_boxed_slice();
        Ok::<(), FormationError>(())
    };
    if let Some(evidence) = cohort.pending_experience.as_mut() {
        extend_experience(evidence)?;
    }
    if let Some(evidence) = cohort.retained_experience.as_mut() {
        extend_experience(evidence)?;
    }
    if let Some(recurrence) = cohort.pending_recurrence.as_mut() {
        recurrence.carries_physical_change_codec = true;
        let mut gate_work = recurrence.gate_work_perturbed_neurons.to_vec();
        gate_work.resize(successor_anatomy.neuron_count(), false);
        recurrence.gate_work_perturbed_neurons = gate_work.into_boxed_slice();
        let mut excitation = recurrence.receptor_excitation_zeptojoules.to_vec();
        excitation.resize(successor_anatomy.neuron_count(), None);
        recurrence.receptor_excitation_zeptojoules = excitation.into_boxed_slice();
        let mut changed = recurrence.physically_changed_neurons.to_vec();
        changed.resize(successor_anatomy.neuron_count(), false);
        recurrence.physically_changed_neurons = changed.into_boxed_slice();
    }
    cohort.anatomy = successor_anatomy;
    cohort.state = successor_state;
    Ok(())
}

fn extend_resident_cohort_positional_fabrics(
    cohort: &mut ResidentReachedCohort,
    required_positions: &[usize],
) -> Result<(), FormationError> {
    let predecessor_anatomy = cohort.anatomy.clone();
    let (successor_anatomy, successor_state) = extend_reached_cohort_positional_fabrics(
        &predecessor_anatomy,
        &cohort.state,
        required_positions,
    )
    .map_err(FormationError::PhysicalSettlementUnavailable)?;
    if successor_anatomy == predecessor_anatomy {
        return Ok(());
    }
    let extend_state = |state: &ReachedCohortState| {
        let (derived_anatomy, derived_state) = extend_reached_cohort_positional_fabrics(
            &predecessor_anatomy,
            state,
            required_positions,
        )
        .map_err(FormationError::PhysicalSettlementUnavailable)?;
        if derived_anatomy != successor_anatomy {
            return Err(FormationError::NoncanonicalState);
        }
        Ok::<ReachedCohortState, FormationError>(derived_state)
    };
    let extend_experience = |evidence: &mut ResidentExperienceEvidence| {
        evidence.pre_experience_rest = extend_state(&evidence.pre_experience_rest)?;
        evidence.post_experience_rest = evidence
            .post_experience_rest
            .as_ref()
            .map(extend_state)
            .transpose()?;
        Ok::<(), FormationError>(())
    };
    if let Some(evidence) = cohort.pending_experience.as_mut() {
        extend_experience(evidence)?;
    }
    if let Some(evidence) = cohort.retained_experience.as_mut() {
        extend_experience(evidence)?;
    }
    cohort.anatomy = successor_anatomy;
    cohort.state = successor_state;
    Ok(())
}

fn settle_resident_physical_interval(
    cohort: &mut ResidentReachedCohort,
    input: ReachedCohortIntervalInput<'_>,
    gate_work_perturbed_neurons: Vec<bool>,
    receptor_excitation_zeptojoules: Vec<Option<ExactRational>>,
    exogenous_receptor_energy: Option<bool>,
    existing_mosaics: &[RetainedOrganismMosaic],
    max_encoded_bytes: usize,
    source_generation: u64,
) -> Result<ResidentOpticalIntervalOutcome, FormationError> {
    // Rest metabolism (minimal feeding metabolism, authorized 2026-08-05).
    // A genuinely dark interval — the stimulus-boundary law's OWN truth
    // signal, derived from the settled occurrence's exact `2·L·T` transduction
    // integral — is when the body's recovery reactions and its membrane return
    // path run.  Nothing here decides when it is dark, and nothing runs while
    // exogenous energy is still arriving.
    let (metabolic, metabolically_perturbed_neurons) = if exogenous_receptor_energy == Some(false) {
        let pre_metabolic_state = cohort.state.clone();
        let (successor, observation) = settle_reached_cohort_dark_rest(
            &cohort.anatomy,
            &cohort.state,
            input.interval_microseconds(),
        )
        .map_err(FormationError::PhysicalSettlementUnavailable)?;
        cohort.state = successor;
        let perturbed = pre_metabolic_state
            .neurons()
            .iter()
            .zip(cohort.state.neurons())
            .map(|(prior, successor)| {
                prior.separated_elementary_charges() != successor.separated_elementary_charges()
            })
            .collect::<Vec<_>>();
        (observation, perturbed)
    } else {
        (
            ReachedCohortMetabolicObservation::default(),
            vec![false; cohort.anatomy.neuron_count()],
        )
    };
    let mut outcome = if cohort.retained_experience.is_some() {
        settle_resident_recurrence_interval(
            cohort,
            input,
            gate_work_perturbed_neurons,
            receptor_excitation_zeptojoules,
            metabolically_perturbed_neurons,
            exogenous_receptor_energy,
            existing_mosaics,
            max_encoded_bytes,
            source_generation,
        )
    } else {
        settle_resident_original_interval(
            cohort,
            input,
            gate_work_perturbed_neurons,
            receptor_excitation_zeptojoules,
            metabolically_perturbed_neurons,
            existing_mosaics,
        )
    }?;
    outcome.metabolic = metabolic;
    Ok(outcome)
}

fn settle_resident_original_interval(
    cohort: &mut ResidentReachedCohort,
    input: ReachedCohortIntervalInput<'_>,
    gate_work_perturbed_neurons: Vec<bool>,
    receptor_excitation_zeptojoules: Vec<Option<ExactRational>>,
    metabolically_perturbed_neurons: Vec<bool>,
    existing_mosaics: &[RetainedOrganismMosaic],
) -> Result<ResidentOpticalIntervalOutcome, FormationError> {
    let mut completed_current_fractals: Option<Box<[Option<SparsePhysicalStateDelta>]>> = None;
    // A new exogenous perturbation begins one compact recognition path.  It
    // is deliberately independent of the simultaneously forming original:
    // the same living neurons can recognize an older formation while their
    // current motion is becoming a different experience.
    let (recognition_cue, endogenous_cue) =
        if gate_work_perturbed_neurons.iter().any(|value| *value) {
            (gate_work_perturbed_neurons.as_slice(), false)
        } else {
            (metabolically_perturbed_neurons.as_slice(), true)
        };
    let starts_new_recognition = if endogenous_cue {
        cohort.pending_recurrence.is_none() && recognition_cue.iter().any(|value| *value)
    } else {
        recognition_cue.iter().any(|value| *value)
    };
    if starts_new_recognition {
        cohort.pending_recurrence =
            (!existing_mosaics.is_empty()).then(|| ResidentRecurrenceEvidence {
                carries_physical_change_codec: true,
                gate_work_perturbed_neurons: recognition_cue.to_vec().into_boxed_slice(),
                receptor_excitation_zeptojoules: if endogenous_cue {
                    vec![None; cohort.anatomy.neuron_count()].into_boxed_slice()
                } else {
                    receptor_excitation_zeptojoules.clone().into_boxed_slice()
                },
                physically_changed_neurons: vec![false; cohort.anatomy.neuron_count()]
                    .into_boxed_slice(),
                active_recurrence_contacts: vec![false; cohort.anatomy.contact_count()]
                    .into_boxed_slice(),
                endogenous: endogenous_cue,
            });
    }
    let experience_preceded_interval = cohort.pending_experience.is_some();
    let predecessor_state = cohort.state.clone();
    let settlement = settle_reached_cohort_interval(&cohort.anatomy, &cohort.state, input)
        .map_err(FormationError::PhysicalSettlementUnavailable)?;
    let retained_change_this_interval = predecessor_state
        .neurons()
        .iter()
        .zip(settlement.successor.neurons())
        .enumerate()
        .map(|(neuron_index, (predecessor, successor))| {
            sparse_retained_physical_state_delta(predecessor, successor)
                .map(|delta| delta.is_some())
                .map_err(|error| {
                    FormationError::PhysicalSettlementUnavailable(ReachedCohortError::Neuron {
                        neuron_index,
                        error,
                    })
                })
        })
        .collect::<Result<Vec<_>, _>>()?;
    // Internal gate intervals are not independent experiences. Their retained
    // changes are compared once at the enclosing admitted-occurrence boundary.
    let emitted = Vec::new();
    let active_electrical_contacts = active_contact_bits(&settlement.contact_transitions);
    let mut physically_changed_neurons = predecessor_state
        .neurons()
        .iter()
        .zip(settlement.successor.neurons())
        .map(|(predecessor, successor)| predecessor != successor)
        .collect::<Vec<_>>();
    or_bits(
        &mut physically_changed_neurons,
        &metabolically_perturbed_neurons,
    )?;
    let mut experience = cohort.pending_experience.take().or_else(|| {
        retained_change_this_interval
            .iter()
            .any(|changed| *changed)
            .then(|| ResidentExperienceEvidence {
                codec: ExperienceEvidenceCodec::V5,
                pre_experience_rest: predecessor_state,
                post_experience_rest: None,
                gate_work_perturbed_neurons: vec![false; cohort.anatomy.neuron_count()]
                    .into_boxed_slice(),
                receptor_excitation_zeptojoules: receptor_excitation_zeptojoules
                    .clone()
                    .into_boxed_slice(),
                retained_change_neurons: vec![false; cohort.anatomy.neuron_count()]
                    .into_boxed_slice(),
                retentively_settled_neurons: vec![false; cohort.anatomy.neuron_count()]
                    .into_boxed_slice(),
                active_electrical_contacts: vec![false; cohort.anatomy.contact_count()]
                    .into_boxed_slice(),
                local_relaxation_observed: false,
            })
    });
    if let Some(experience) = experience.as_mut() {
        experience.codec = ExperienceEvidenceCodec::V5;
        or_bits(
            &mut experience.gate_work_perturbed_neurons,
            &gate_work_perturbed_neurons,
        )?;
        or_bits(
            &mut experience.retained_change_neurons,
            &retained_change_this_interval,
        )?;
        or_bits(
            &mut experience.active_electrical_contacts,
            &active_electrical_contacts,
        )?;
    }
    // Collective formation closure remains a separate later retentive-rest
    // law. It determines which cumulative neuron deltas may participate in a
    // retained original; it does not authorize or suppress the local fractal
    // observation above.
    if let Some(mut experience) = experience {
        if experience_preceded_interval {
            for neuron_index in 0..cohort.anatomy.neuron_count() {
                if !experience.retained_change_neurons[neuron_index]
                    || experience.retentively_settled_neurons[neuron_index]
                    || retained_change_this_interval[neuron_index]
                {
                    continue;
                }
                experience.retentively_settled_neurons[neuron_index] = true;
            }
        }
        let experience_complete = experience
            .retained_change_neurons
            .iter()
            .zip(experience.retentively_settled_neurons.iter())
            .all(|(changed, settled)| !*changed || *settled);
        if experience_complete {
            let mut member_indices = Vec::new();
            for (neuron_index, settled) in experience.retentively_settled_neurons.iter().enumerate()
            {
                if *settled
                    && sparse_retained_physical_state_delta(
                        &experience.pre_experience_rest.neurons()[neuron_index],
                        &settlement.successor.neurons()[neuron_index],
                    )
                    .map_err(|error| {
                        FormationError::PhysicalSettlementUnavailable(ReachedCohortError::Neuron {
                            neuron_index,
                            error,
                        })
                    })?
                    .is_some()
                {
                    member_indices.push(neuron_index);
                }
            }
            // Participation retention (same ratification): the completion is
            // retainable as a recognizable original ONLY if its masks satisfy
            // the admission law's own original-side predicate — at least
            // three changed members connected through the contacts that were
            // physically active during the experience (`connected_members`,
            // reused verbatim from `admit_physical_mosaic`).  A completion
            // failing it does not create a mosaic. Neuronal material remains
            // physical state and the bounded pending occurrence can still
            // acquire later connected participation.
            let mut member_mask = vec![false; cohort.anatomy.neuron_count()];
            for member in &member_indices {
                member_mask[*member] = true;
            }
            let endpoints = cohort.anatomy.contact_endpoints().collect::<Vec<_>>();
            let connected_retention = member_indices.len() >= 3
                && connected_members(
                    cohort.anatomy.neuron_count(),
                    &member_indices,
                    &member_mask,
                    &endpoints,
                    &experience.active_electrical_contacts,
                    &member_indices[..1],
                );
            if connected_retention {
                completed_current_fractals = Some(retained_physical_deltas(
                    &cohort.anatomy,
                    &experience.pre_experience_rest,
                    &settlement.successor,
                    &experience.retentively_settled_neurons,
                )?);
                experience.post_experience_rest = Some(settlement.successor.clone());
                cohort.retained_experience = Some(experience);
                cohort.pending_experience = None;
            } else {
                // One or two settled neuronal impressions are real retained
                // physical changes even though they cannot yet admit a
                // mosaic. Keep this one bounded pending occurrence so later
                // causally connected participation can join it. The minimum
                // of three governs mosaic admission, not erasure of neurons.
                cohort.pending_experience = Some(experience);
            }
        } else {
            cohort.pending_experience = Some(experience);
        }
    } else {
        cohort.pending_experience = None;
    }
    cohort.state = settlement.successor;
    let mut mosaic_resolutions = Vec::new();
    let mut partial_cue_reassembly_count = 0usize;
    let mut recognized_endogenously = false;
    if let Some(mut recurrence) = cohort.pending_recurrence.take() {
        let recurrence_endogenous = recurrence.endogenous;
        recurrence.carries_physical_change_codec = true;
        if !recurrence.endogenous {
            or_bits(
                &mut recurrence.gate_work_perturbed_neurons,
                &gate_work_perturbed_neurons,
            )?;
        }
        or_bits(
            &mut recurrence.physically_changed_neurons,
            &physically_changed_neurons,
        )?;
        or_bits(
            &mut recurrence.active_recurrence_contacts,
            &active_electrical_contacts,
        )?;
        if let Some(current_fractals) = completed_current_fractals.as_deref() {
            for (mosaic_index, retained) in existing_mosaics.iter().enumerate() {
                let reassembled = retained
                    .mosaic
                    .reassembled_by_current_flow(
                        &cohort.anatomy,
                        &recurrence.gate_work_perturbed_neurons,
                        current_fractals,
                        &recurrence.active_recurrence_contacts,
                        recurrence.endogenous,
                    )
                    .map_err(FormationError::PhysicalMosaicUnavailable)?;
                if reassembled {
                    mosaic_resolutions
                        .push(MosaicStructuralResolution::Reinforces { mosaic_index });
                }
            }
        } else {
            cohort.pending_recurrence = Some(recurrence);
        }
        partial_cue_reassembly_count = mosaic_resolutions.len();
        recognized_endogenously = recurrence_endogenous && !mosaic_resolutions.is_empty();
    }
    Ok(ResidentOpticalIntervalOutcome {
        emitted_neuron_fractals: emitted,
        mosaic_formed: None,
        mosaic_resolutions,
        partial_cue_reassembly_count,
        endogenous_partial_cue_reassembly_count: partial_cue_reassembly_count
            * usize::from(recognized_endogenously),
        metabolic: ReachedCohortMetabolicObservation::default(),
    })
}

fn settle_resident_recurrence_interval(
    cohort: &mut ResidentReachedCohort,
    input: ReachedCohortIntervalInput<'_>,
    gate_work_perturbed_neurons: Vec<bool>,
    receptor_excitation_zeptojoules: Vec<Option<ExactRational>>,
    metabolically_perturbed_neurons: Vec<bool>,
    exogenous_receptor_energy: Option<bool>,
    existing_mosaics: &[RetainedOrganismMosaic],
    max_encoded_bytes: usize,
    source_generation: u64,
) -> Result<ResidentOpticalIntervalOutcome, FormationError> {
    let local_relaxation_observed = cohort
        .retained_experience
        .as_ref()
        .ok_or(FormationError::NoncanonicalState)?
        .local_relaxation_observed;
    if exogenous_receptor_energy != Some(false)
        && gate_work_perturbed_neurons
            .iter()
            .any(|perturbed| *perturbed)
    {
        // A new physical perturbation ends any older unfinished cue.  It is
        // a new occurrence, not another interval of the old one.  This also
        // prevents a pre-upgrade transient from blocking the living
        // formation forever.
        cohort.pending_recurrence = None;
        let retained = cohort
            .retained_experience
            .as_ref()
            .ok_or(FormationError::NoncanonicalState)?;
        let learned = retained
            .post_experience_rest
            .as_ref()
            .ok_or(FormationError::NoncanonicalState)?;
        if is_formation_local_proper_partial_cue(retained, learned, &gate_work_perturbed_neurons)? {
            cohort.pending_recurrence = Some(ResidentRecurrenceEvidence {
                carries_physical_change_codec: true,
                gate_work_perturbed_neurons: vec![false; cohort.anatomy.neuron_count()]
                    .into_boxed_slice(),
                receptor_excitation_zeptojoules: receptor_excitation_zeptojoules
                    .clone()
                    .into_boxed_slice(),
                physically_changed_neurons: vec![false; cohort.anatomy.neuron_count()]
                    .into_boxed_slice(),
                active_recurrence_contacts: vec![false; cohort.anatomy.contact_count()]
                    .into_boxed_slice(),
                endogenous: false,
            });
        }
    }

    #[cfg(test)]
    RESIDENT_ACTUAL_RECURRENCE_SETTLEMENTS.with(|count| count.set(count.get() + 1));
    let recurrence_predecessor = cohort.state.clone();
    let actual = settle_reached_cohort_interval(&cohort.anatomy, &cohort.state, input)
        .map_err(FormationError::PhysicalSettlementUnavailable)?;
    let partial_cue_reassembly_count = 0;
    cohort.state = actual.successor.clone();
    let active_contacts = active_contact_bits(&actual.contact_transitions);
    let physically_changed_neurons = recurrence_predecessor
        .neurons()
        .iter()
        .zip(actual.successor.neurons())
        .map(|(predecessor, successor)| predecessor != successor)
        .collect::<Vec<_>>();
    let formation_locally_settled = {
        let retained = cohort
            .retained_experience
            .as_ref()
            .ok_or(FormationError::NoncanonicalState)?;
        retained
            .retentively_settled_neurons
            .iter()
            .zip(&physically_changed_neurons)
            .all(|(member, changed)| !*member || !*changed)
            && !retained_contact_set_flowing(retained, &active_contacts)?
    };

    // A retained formation relaxes through one later settlement with no
    // exogenous gate work.  Internal current may continue: requiring every
    // retained contact to stop would require a living formation to become
    // electrically dead.  Recording happens after the interval, so that
    // exact interval cannot authorize itself as a cue.
    if !local_relaxation_observed
        && gate_work_perturbed_neurons
            .iter()
            .all(|perturbed| !perturbed)
        && formation_locally_settled
    {
        cohort
            .retained_experience
            .as_mut()
            .ok_or(FormationError::NoncanonicalState)?
            .codec = ExperienceEvidenceCodec::V5;
        cohort
            .retained_experience
            .as_mut()
            .ok_or(FormationError::NoncanonicalState)?
            .local_relaxation_observed = true;
    }

    // After formation-local relaxation, a later dark interval may carry a
    // genuinely internal perturbation.  Only membrane movement caused by the
    // organism's own metabolic return may BEGIN that cue. Continuing contact
    // current from the original occurrence may propagate a cue once present,
    // but it cannot re-label its own settling tail as spontaneous recall. No
    // scheduler, timer, semantic label, or scalar selection participates.
    if cohort.pending_recurrence.is_none()
        && local_relaxation_observed
        && gate_work_perturbed_neurons
            .iter()
            .all(|perturbed| !perturbed)
        && !retained_contact_set_flowing(
            cohort
                .retained_experience
                .as_ref()
                .ok_or(FormationError::NoncanonicalState)?,
            &active_contacts,
        )?
    {
        let retained = cohort
            .retained_experience
            .as_ref()
            .ok_or(FormationError::NoncanonicalState)?;
        let learned = retained
            .post_experience_rest
            .as_ref()
            .ok_or(FormationError::NoncanonicalState)?;
        if is_formation_local_proper_partial_cue(
            retained,
            learned,
            &metabolically_perturbed_neurons,
        )? {
            cohort.pending_recurrence = Some(ResidentRecurrenceEvidence {
                carries_physical_change_codec: true,
                gate_work_perturbed_neurons: metabolically_perturbed_neurons.into_boxed_slice(),
                receptor_excitation_zeptojoules: vec![None; cohort.anatomy.neuron_count()]
                    .into_boxed_slice(),
                physically_changed_neurons: vec![false; cohort.anatomy.neuron_count()]
                    .into_boxed_slice(),
                active_recurrence_contacts: vec![false; cohort.anatomy.contact_count()]
                    .into_boxed_slice(),
                endogenous: true,
            });
        }
    }
    let Some(mut recurrence) = cohort.pending_recurrence.take() else {
        return Ok(ResidentOpticalIntervalOutcome {
            emitted_neuron_fractals: Vec::new(),
            mosaic_formed: None,
            mosaic_resolutions: Vec::new(),
            partial_cue_reassembly_count,
            endogenous_partial_cue_reassembly_count: 0,
            metabolic: ReachedCohortMetabolicObservation::default(),
        });
    };
    recurrence.carries_physical_change_codec = true;
    or_bits(
        &mut recurrence.gate_work_perturbed_neurons,
        &gate_work_perturbed_neurons,
    )?;
    or_bits(
        &mut recurrence.physically_changed_neurons,
        &physically_changed_neurons,
    )?;
    or_bits(&mut recurrence.active_recurrence_contacts, &active_contacts)?;
    if exogenous_receptor_energy != Some(false) {
        cohort.pending_recurrence = Some(recurrence);
        return Ok(ResidentOpticalIntervalOutcome {
            emitted_neuron_fractals: Vec::new(),
            mosaic_formed: None,
            mosaic_resolutions: Vec::new(),
            partial_cue_reassembly_count: 0,
            endogenous_partial_cue_reassembly_count: 0,
            metabolic: ReachedCohortMetabolicObservation::default(),
        });
    }
    let retained = cohort
        .retained_experience
        .as_ref()
        .ok_or(FormationError::NoncanonicalState)?;
    let learned = retained
        .post_experience_rest
        .as_ref()
        .ok_or(FormationError::NoncanonicalState)?;
    let original = original_settlement(&cohort.anatomy, retained, learned)?;
    let actual_recurrence = recurrence_settlement(
        &cohort.anatomy,
        learned,
        cohort.state.clone(),
        recurrence.receptor_excitation_zeptojoules.clone(),
        recurrence.gate_work_perturbed_neurons.clone(),
        recurrence.active_recurrence_contacts.clone(),
    )?;
    let mosaic = match admit_physical_mosaic(&cohort.anatomy, &original, &actual_recurrence) {
        Ok(mosaic) => mosaic,
        Err(error) if physical_mosaic_non_admission(error) => {
            // A recurrence inherited before the formation's first later
            // no-exogenous settlement is transient tail state, not learned
            // authority.  If it cannot assemble on that boundary, drop it;
            // otherwise an old unfinished cue can block every later internal
            // perturbation forever.  Recurrences begun after relaxation still
            // remain while their own formation contacts are moving.
            if local_relaxation_observed {
                cohort.pending_recurrence = Some(recurrence);
            }
            return Ok(ResidentOpticalIntervalOutcome {
                emitted_neuron_fractals: Vec::new(),
                mosaic_formed: None,
                mosaic_resolutions: Vec::new(),
                partial_cue_reassembly_count,
                endogenous_partial_cue_reassembly_count: 0,
                metabolic: ReachedCohortMetabolicObservation::default(),
            });
        }
        Err(error) => return Err(FormationError::PhysicalMosaicUnavailable(error)),
    };
    let encoded = encode_admitted_physical_mosaic(&cohort.anatomy, &mosaic, max_encoded_bytes)
        .map_err(FormationError::PhysicalMosaicCodecUnavailable)?;
    let receipt = sha256(&encoded);
    verify_mosaic_members_physically_moved(
        &cohort.anatomy,
        &mosaic,
        &actual_recurrence,
        source_generation,
    )?;
    // The admitted mosaic now carries the exact sparse original neuronal
    // deltas and original physical bonds.  Keeping the complete pre/post
    // cohort snapshots beside it would duplicate the same retained structure
    // and would prevent this cohort from ever retaining another experience.
    // Release that bounded in-progress evidence at admission.  Resident
    // neurons and contacts remain untouched and continue carrying causality.
    cohort.retained_experience = None;
    cohort.pending_recurrence = None;
    let resolution = resolve_mosaic_structural_identity(existing_mosaics, mosaic);
    let newly_formed = matches!(resolution, MosaicStructuralResolution::NewFormation(_));
    Ok(ResidentOpticalIntervalOutcome {
        emitted_neuron_fractals: Vec::new(),
        mosaic_formed: newly_formed.then_some(receipt),
        mosaic_resolutions: vec![resolution],
        partial_cue_reassembly_count: 1,
        endogenous_partial_cue_reassembly_count: usize::from(recurrence.endogenous),
        metabolic: ReachedCohortMetabolicObservation::default(),
    })
}

fn original_settlement(
    anatomy: &ReachedCohortAnatomy,
    retained: &ResidentExperienceEvidence,
    learned: &ReachedCohortState,
) -> Result<ReachedCohortPostExperienceSettlement, FormationError> {
    let neuron_fractals = retained_physical_deltas(
        anatomy,
        &retained.pre_experience_rest,
        learned,
        &retained.retentively_settled_neurons,
    )?;
    Ok(ReachedCohortPostExperienceSettlement {
        rest: RestReachedCohortState::from_state(learned.clone()),
        neuron_fractals,
        receptor_excitation_zeptojoules: retained.receptor_excitation_zeptojoules.clone(),
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
    receptor_excitation_zeptojoules: Box<[Option<ExactRational>]>,
    gate_work_perturbed_neurons: Box<[bool]>,
    active_electrical_contacts: Box<[bool]>,
) -> Result<ReachedCohortRecurrenceSettlement, FormationError> {
    Ok(ReachedCohortRecurrenceSettlement {
        neuron_physical_deltas: physical_deltas(anatomy, predecessor, &successor)?,
        successor,
        receptor_excitation_zeptojoules,
        gate_work_perturbed_neurons,
        active_electrical_contacts,
    })
}

/// The one BODY invariant the retired episode builder used to enforce.
///
/// Everything else `build_typed_hippocampal_episode` checked was a round-trip
/// of the archive record's OWN encoding — it re-encoded the retained
/// experience evidence, the recurrence evidence and two cohort states, then
/// decoded them back and compared.  Those checks validated the record, not
/// Guala, and they left with it.  THIS check is about her: every member of an
/// admitted mosaic must have actually moved in the recurrence that admitted
/// it, and its lineage must be one this cohort's anatomy authored.  It is kept
/// verbatim, at the same point in the transition, with the same two error
/// values, so a body that used to be refused here is still refused here.
fn verify_mosaic_members_physically_moved(
    anatomy: &ReachedCohortAnatomy,
    mosaic: &AdmittedPhysicalMosaic,
    actual_recurrence: &ReachedCohortRecurrenceSettlement,
    source_generation: u64,
) -> Result<(), FormationError> {
    if source_generation == 0 {
        return Err(FormationError::NoncanonicalState);
    }
    for lineage in mosaic.member_lineages() {
        let member_index = anatomy
            .neuron_lineages()
            .iter()
            .position(|candidate| candidate == lineage)
            .ok_or(FormationError::NeuronLineageAuthorityAbsent)?;
        if actual_recurrence.neuron_physical_deltas[member_index].is_none() {
            return Err(FormationError::NoncanonicalState);
        }
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

fn retained_physical_deltas(
    anatomy: &ReachedCohortAnatomy,
    predecessor: &ReachedCohortState,
    successor: &ReachedCohortState,
    retained_members: &[bool],
) -> Result<Box<[Option<SparsePhysicalStateDelta>]>, FormationError> {
    if predecessor.neurons().len() != anatomy.neuron_count()
        || successor.neurons().len() != anatomy.neuron_count()
        || retained_members.len() != anatomy.neuron_count()
    {
        return Err(FormationError::NoncanonicalState);
    }
    predecessor
        .neurons()
        .iter()
        .zip(successor.neurons())
        .enumerate()
        .map(|(neuron_index, (prior, next))| {
            if !retained_members[neuron_index] {
                return Ok(None);
            }
            sparse_retained_physical_state_delta(prior, next).map_err(|error| {
                FormationError::PhysicalSettlementUnavailable(ReachedCohortError::Neuron {
                    neuron_index,
                    error,
                })
            })
        })
        .collect::<Result<Vec<_>, _>>()
        .map(Vec::into_boxed_slice)
}

fn is_formation_local_proper_partial_cue(
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
        .pre_experience_rest
        .neurons()
        .iter()
        .zip(learned.neurons())
        .enumerate()
    {
        let member = retained.retentively_settled_neurons[index]
            && sparse_retained_physical_state_delta(prior, successor)
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
        cue_count = cue_count
            .checked_add(usize::from(member && perturbed[index]))
            .ok_or(FormationError::ArithmeticOverflow)?;
    }
    Ok(cue_count > 0 && cue_count < member_count)
}

fn retained_contact_set_flowing(
    retained: &ResidentExperienceEvidence,
    active_contacts: &[bool],
) -> Result<bool, FormationError> {
    if retained.active_electrical_contacts.len() != active_contacts.len() {
        return Err(FormationError::NoncanonicalState);
    }
    Ok(retained
        .active_electrical_contacts
        .iter()
        .zip(active_contacts)
        .any(|(carried_experience, flowing_now)| *carried_experience && *flowing_now))
}

fn active_contact_bits(
    transitions: &[crate::sparse_electrical_contact::ElectricalContactTransition],
) -> Vec<bool> {
    transitions
        .iter()
        .map(|transition| {
            transition.outward_current_from_left_picoamperes.parts().0 != 0
                || transition.outward_elementary_charges_from_left != 0
                || transition.plastic_changed
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

/// Encode one experience evidence record in the `GLEXP02` layout. With a
/// resident base state (the cohort's current state retained beside the
/// evidence) the PRE snapshot is carried as per-neuron sparse deltas against
/// that base and the POST snapshot collapses to a 32-byte content digest when
/// its canonical encoding is byte-identical to the base's; the byte comparison
/// happens here, at encode. Without a base (hippocampal episode bodies) both
/// snapshots are carried as complete content-addressed cohort states. Every
/// settled value is preserved exactly in all forms.
fn encode_experience_evidence_v2(
    anatomy: &ReachedCohortAnatomy,
    base: Option<&ReachedCohortState>,
    evidence: &ResidentExperienceEvidence,
    carries_contact_plasticity: bool,
) -> Result<Vec<u8>, FormationError> {
    if evidence.gate_work_perturbed_neurons.len() != anatomy.neuron_count()
        || evidence.receptor_excitation_zeptojoules.len() != anatomy.neuron_count()
        || evidence.retained_change_neurons.len() != anatomy.neuron_count()
        || evidence.retentively_settled_neurons.len() != anatomy.neuron_count()
        || evidence.active_electrical_contacts.len() != anatomy.contact_count()
        || evidence
            .retentively_settled_neurons
            .iter()
            .zip(evidence.retained_change_neurons.iter())
            .any(|(settled, changed)| *settled && !*changed)
    {
        return Err(FormationError::NoncanonicalState);
    }
    if evidence.codec == ExperienceEvidenceCodec::V1 {
        return encode_experience_evidence(anatomy, evidence);
    }
    if (evidence.codec == ExperienceEvidenceCodec::V2 && evidence.local_relaxation_observed)
        || (evidence.codec == ExperienceEvidenceCodec::V3 && !evidence.local_relaxation_observed)
    {
        return Err(FormationError::NoncanonicalState);
    }
    let selective_layout = matches!(
        evidence.codec,
        ExperienceEvidenceCodec::V4 | ExperienceEvidenceCodec::V5
    );
    let excitation_layout = evidence.codec == ExperienceEvidenceCodec::V5;
    let mut encoded = Vec::new();
    encoded.extend_from_slice(match evidence.codec {
        ExperienceEvidenceCodec::V1 => unreachable!(),
        ExperienceEvidenceCodec::V2 => EXPERIENCE_V2_MAGIC,
        ExperienceEvidenceCodec::V3 => EXPERIENCE_V3_MAGIC,
        ExperienceEvidenceCodec::V4 => EXPERIENCE_V4_MAGIC,
        ExperienceEvidenceCodec::V5 => EXPERIENCE_V5_MAGIC,
    });
    if selective_layout {
        encoded.push(u8::from(evidence.local_relaxation_observed));
    }
    match base {
        Some(base) => {
            let body = if carries_contact_plasticity {
                encode_reached_cohort_state_delta(anatomy, base, &evidence.pre_experience_rest)
            } else {
                encode_reached_cohort_state_delta_v1(anatomy, base, &evidence.pre_experience_rest)
            }
            .map_err(|_| FormationError::NoncanonicalState)?;
            encoded.push(1);
            push_length(&mut encoded, body.len())?;
            encoded.extend_from_slice(&body);
        }
        None => {
            let body = if carries_contact_plasticity {
                encode_reached_cohort_state_v5(anatomy, &evidence.pre_experience_rest)
            } else {
                encode_reached_cohort_state_v4(anatomy, &evidence.pre_experience_rest)
            }
            .map_err(|_| FormationError::NoncanonicalState)?;
            encoded.push(0);
            push_length(&mut encoded, body.len())?;
            encoded.extend_from_slice(&body);
        }
    }
    match evidence.post_experience_rest.as_ref() {
        None => encoded.push(0),
        Some(post) => {
            let state_body = |state: &ReachedCohortState| {
                if carries_contact_plasticity {
                    encode_reached_cohort_state_v5(anatomy, state)
                } else {
                    encode_reached_cohort_state_v4(anatomy, state)
                }
            };
            let post_body = state_body(post).map_err(|_| FormationError::NoncanonicalState)?;
            let base_body = base
                .map(state_body)
                .transpose()
                .map_err(|_| FormationError::NoncanonicalState)?;
            match base_body {
                Some(base_body) if base_body == post_body => {
                    encoded.push(2);
                    encoded.extend_from_slice(&sha256(&post_body));
                }
                _ => {
                    encoded.push(1);
                    push_length(&mut encoded, post_body.len())?;
                    encoded.extend_from_slice(&post_body);
                }
            }
        }
    }
    push_length(&mut encoded, evidence.gate_work_perturbed_neurons.len())?;
    encoded.extend(
        evidence
            .gate_work_perturbed_neurons
            .iter()
            .map(|value| u8::from(*value)),
    );
    if excitation_layout {
        encode_optional_exact_slice(&mut encoded, &evidence.receptor_excitation_zeptojoules)?;
    }
    if selective_layout {
        push_length(&mut encoded, evidence.retained_change_neurons.len())?;
        encoded.extend(
            evidence
                .retained_change_neurons
                .iter()
                .map(|value| u8::from(*value)),
        );
        push_length(&mut encoded, evidence.retentively_settled_neurons.len())?;
        encoded.extend(
            evidence
                .retentively_settled_neurons
                .iter()
                .map(|value| u8::from(*value)),
        );
    }
    push_length(&mut encoded, evidence.active_electrical_contacts.len())?;
    encoded.extend(
        evidence
            .active_electrical_contacts
            .iter()
            .map(|value| u8::from(*value)),
    );
    Ok(encoded)
}

fn decode_experience_evidence_v2(
    encoded: &[u8],
    anatomy: &ReachedCohortAnatomy,
    base: Option<&ReachedCohortState>,
) -> Result<ResidentExperienceEvidence, FormationError> {
    let (codec, local_relaxation_observed, selective_layout, excitation_layout, mut cursor) =
        if encoded.get(..EXPERIENCE_V2_MAGIC.len()) == Some(EXPERIENCE_V2_MAGIC) {
            (
                ExperienceEvidenceCodec::V2,
                false,
                false,
                false,
                EXPERIENCE_V2_MAGIC.len(),
            )
        } else if encoded.get(..EXPERIENCE_V3_MAGIC.len()) == Some(EXPERIENCE_V3_MAGIC) {
            (
                ExperienceEvidenceCodec::V3,
                true,
                false,
                false,
                EXPERIENCE_V3_MAGIC.len(),
            )
        } else if encoded.get(..EXPERIENCE_V4_MAGIC.len()) == Some(EXPERIENCE_V4_MAGIC) {
            let flag = *encoded
                .get(EXPERIENCE_V4_MAGIC.len())
                .ok_or(FormationError::NoncanonicalState)?;
            if flag > 1 {
                return Err(FormationError::NoncanonicalState);
            }
            (
                ExperienceEvidenceCodec::V4,
                flag == 1,
                true,
                false,
                EXPERIENCE_V4_MAGIC
                    .len()
                    .checked_add(1)
                    .ok_or(FormationError::ArithmeticOverflow)?,
            )
        } else if encoded.get(..EXPERIENCE_V5_MAGIC.len()) == Some(EXPERIENCE_V5_MAGIC) {
            let flag = *encoded
                .get(EXPERIENCE_V5_MAGIC.len())
                .ok_or(FormationError::NoncanonicalState)?;
            if flag > 1 {
                return Err(FormationError::NoncanonicalState);
            }
            (
                ExperienceEvidenceCodec::V5,
                flag == 1,
                true,
                true,
                EXPERIENCE_V5_MAGIC
                    .len()
                    .checked_add(1)
                    .ok_or(FormationError::ArithmeticOverflow)?,
            )
        } else {
            return Err(FormationError::NoncanonicalState);
        };
    let pre_mode = *encoded
        .get(cursor)
        .ok_or(FormationError::NoncanonicalState)?;
    cursor = cursor
        .checked_add(1)
        .ok_or(FormationError::ArithmeticOverflow)?;
    let pre_length = read_length(encoded, &mut cursor)?;
    let pre_end = cursor
        .checked_add(pre_length)
        .ok_or(FormationError::ArithmeticOverflow)?;
    let pre_body = encoded
        .get(cursor..pre_end)
        .ok_or(FormationError::NoncanonicalState)?;
    let pre_experience_rest = match (pre_mode, base) {
        (0, _) => decode_reached_cohort_state(anatomy, pre_body)
            .map_err(|_| FormationError::NoncanonicalState)?,
        (1, Some(base)) => {
            decode_reached_cohort_state_delta(anatomy, base, pre_body).map_err(|error| {
                if error == ReachedCohortError::UntranslatableLegacyRecoveryState {
                    FormationError::PhysicalSettlementUnavailable(error)
                } else {
                    FormationError::NoncanonicalState
                }
            })?
        }
        _ => return Err(FormationError::NoncanonicalState),
    };
    cursor = pre_end;
    let post_mode = *encoded
        .get(cursor)
        .ok_or(FormationError::NoncanonicalState)?;
    cursor = cursor
        .checked_add(1)
        .ok_or(FormationError::ArithmeticOverflow)?;
    let post_experience_rest = match (post_mode, base) {
        (0, _) => None,
        (1, _) => {
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
        (2, Some(base)) => {
            let end = cursor
                .checked_add(EVIDENCE_DIGEST_BYTES)
                .ok_or(FormationError::ArithmeticOverflow)?;
            let claimed: [u8; EVIDENCE_DIGEST_BYTES] = encoded
                .get(cursor..end)
                .ok_or(FormationError::NoncanonicalState)?
                .try_into()
                .map_err(|_| FormationError::NoncanonicalState)?;
            let current = reached_cohort_state_content_digest(anatomy, base)
                .map_err(|_| FormationError::NoncanonicalState)?;
            let legacy = reached_cohort_state_v4_content_digest(anatomy, base).ok();
            if claimed != current && legacy != Some(claimed) {
                return Err(FormationError::NoncanonicalState);
            }
            cursor = end;
            Some(base.clone())
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
    let receptor_excitation_zeptojoules = if excitation_layout {
        decode_optional_exact_slice(encoded, &mut cursor, anatomy.neuron_count())?
    } else {
        vec![None; anatomy.neuron_count()].into_boxed_slice()
    };
    let (retained_change_neurons, retentively_settled_neurons) = if selective_layout {
        let changed_count = read_length(encoded, &mut cursor)?;
        if changed_count != anatomy.neuron_count() {
            return Err(FormationError::NoncanonicalState);
        }
        let changed_end = cursor
            .checked_add(changed_count)
            .ok_or(FormationError::ArithmeticOverflow)?;
        let changed = decode_bools(
            encoded
                .get(cursor..changed_end)
                .ok_or(FormationError::NoncanonicalState)?,
        )?;
        cursor = changed_end;
        let settled_count = read_length(encoded, &mut cursor)?;
        if settled_count != anatomy.neuron_count() {
            return Err(FormationError::NoncanonicalState);
        }
        let settled_end = cursor
            .checked_add(settled_count)
            .ok_or(FormationError::ArithmeticOverflow)?;
        let settled = decode_bools(
            encoded
                .get(cursor..settled_end)
                .ok_or(FormationError::NoncanonicalState)?,
        )?;
        if settled
            .iter()
            .zip(changed.iter())
            .any(|(settled, changed)| *settled && !*changed)
        {
            return Err(FormationError::NoncanonicalState);
        }
        cursor = settled_end;
        (changed, settled)
    } else {
        let comparison = post_experience_rest.as_ref().or(base);
        let mut changed = Vec::with_capacity(anatomy.neuron_count());
        if let Some(comparison) = comparison {
            for (neuron_index, (predecessor, successor)) in pre_experience_rest
                .neurons()
                .iter()
                .zip(comparison.neurons())
                .enumerate()
            {
                changed.push(
                    sparse_retained_physical_state_delta(predecessor, successor)
                        .map_err(|error| {
                            FormationError::PhysicalSettlementUnavailable(
                                ReachedCohortError::Neuron {
                                    neuron_index,
                                    error,
                                },
                            )
                        })?
                        .is_some(),
                );
            }
        } else {
            changed.resize(anatomy.neuron_count(), false);
        }
        let settled = if post_experience_rest.is_some() {
            changed.clone()
        } else {
            vec![false; anatomy.neuron_count()]
        };
        (changed.into_boxed_slice(), settled.into_boxed_slice())
    };
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
        codec,
        pre_experience_rest,
        post_experience_rest,
        gate_work_perturbed_neurons,
        receptor_excitation_zeptojoules,
        retained_change_neurons,
        retentively_settled_neurons,
        active_electrical_contacts,
        local_relaxation_observed,
    })
}

/// Decode one experience evidence body in whichever admitted layout its magic
/// names: the retired inline `GLEXP01` or the current `GLEXP02`.
fn decode_any_experience_evidence(
    encoded: &[u8],
    anatomy: &ReachedCohortAnatomy,
    base: Option<&ReachedCohortState>,
) -> Result<ResidentExperienceEvidence, FormationError> {
    if encoded.get(..EXPERIENCE_V2_MAGIC.len()) == Some(EXPERIENCE_V2_MAGIC)
        || encoded.get(..EXPERIENCE_V3_MAGIC.len()) == Some(EXPERIENCE_V3_MAGIC)
        || encoded.get(..EXPERIENCE_V4_MAGIC.len()) == Some(EXPERIENCE_V4_MAGIC)
        || encoded.get(..EXPERIENCE_V5_MAGIC.len()) == Some(EXPERIENCE_V5_MAGIC)
    {
        decode_experience_evidence_v2(encoded, anatomy, base)
    } else {
        decode_experience_evidence(encoded, anatomy)
    }
}

fn encode_experience_evidence(
    anatomy: &ReachedCohortAnatomy,
    evidence: &ResidentExperienceEvidence,
) -> Result<Vec<u8>, FormationError> {
    if evidence.gate_work_perturbed_neurons.len() != anatomy.neuron_count()
        || evidence.receptor_excitation_zeptojoules.len() != anatomy.neuron_count()
        || evidence
            .receptor_excitation_zeptojoules
            .iter()
            .any(Option::is_some)
        || evidence.retained_change_neurons.len() != anatomy.neuron_count()
        || evidence.retentively_settled_neurons.len() != anatomy.neuron_count()
        || evidence.active_electrical_contacts.len() != anatomy.contact_count()
        || evidence.local_relaxation_observed
    {
        return Err(FormationError::NoncanonicalState);
    }
    let predecessor = encode_reached_cohort_state(anatomy, &evidence.pre_experience_rest)
        .map_err(|_| FormationError::NoncanonicalState)?;
    let successor = evidence
        .post_experience_rest
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
    base: &ReachedCohortState,
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
            let evidence = match decode_any_experience_evidence(
                bytes
                    .get(*cursor..end)
                    .ok_or(FormationError::NoncanonicalState)?,
                anatomy,
                Some(base),
            ) {
                Ok(evidence) => evidence,
                Err(FormationError::PhysicalSettlementUnavailable(
                    ReachedCohortError::UntranslatableLegacyRecoveryState,
                )) if !retained => {
                    *cursor = end;
                    return Ok(None);
                }
                Err(error) => return Err(error),
            };
            *cursor = end;
            if evidence.post_experience_rest.is_some() != retained {
                return Err(FormationError::NoncanonicalState);
            }
            if retained {
                let post = evidence
                    .post_experience_rest
                    .as_ref()
                    .ok_or(FormationError::NoncanonicalState)?;
                let retained = evidence
                    .pre_experience_rest
                    .neurons()
                    .iter()
                    .zip(post.neurons())
                    .enumerate()
                    .try_fold(0usize, |count, (neuron_index, (prior, successor))| {
                        let changed = evidence.retentively_settled_neurons[neuron_index]
                            && sparse_retained_physical_state_delta(prior, successor)
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
    let pre_experience_rest = decode_reached_cohort_state(
        anatomy,
        encoded
            .get(cursor..predecessor_end)
            .ok_or(FormationError::NoncanonicalState)?,
    )
    .map_err(|_| FormationError::NoncanonicalState)?;
    cursor = predecessor_end;
    let post_experience_rest = match encoded
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
    let mut retained_change_neurons = Vec::with_capacity(anatomy.neuron_count());
    for (neuron_index, predecessor) in pre_experience_rest.neurons().iter().enumerate() {
        let changed = post_experience_rest
            .as_ref()
            .map(|successor| {
                sparse_retained_physical_state_delta(
                    predecessor,
                    &successor.neurons()[neuron_index],
                )
                .map(|delta| delta.is_some())
                .map_err(|error| {
                    FormationError::PhysicalSettlementUnavailable(ReachedCohortError::Neuron {
                        neuron_index,
                        error,
                    })
                })
            })
            .transpose()?
            .unwrap_or(false);
        retained_change_neurons.push(changed);
    }
    let retentively_settled_neurons = if post_experience_rest.is_some() {
        retained_change_neurons.clone()
    } else {
        vec![false; anatomy.neuron_count()]
    };
    Ok(ResidentExperienceEvidence {
        codec: ExperienceEvidenceCodec::V1,
        pre_experience_rest,
        post_experience_rest,
        gate_work_perturbed_neurons,
        receptor_excitation_zeptojoules: vec![None; anatomy.neuron_count()].into_boxed_slice(),
        retained_change_neurons: retained_change_neurons.into_boxed_slice(),
        retentively_settled_neurons: retentively_settled_neurons.into_boxed_slice(),
        active_electrical_contacts,
        local_relaxation_observed: false,
    })
}

fn encode_recurrence_evidence(
    anatomy: &ReachedCohortAnatomy,
    evidence: &ResidentRecurrenceEvidence,
) -> Result<Vec<u8>, FormationError> {
    let neuron_count = anatomy.neuron_count();
    let contact_count = anatomy.contact_count();
    if evidence.gate_work_perturbed_neurons.len() != neuron_count
        || evidence.receptor_excitation_zeptojoules.len() != neuron_count
        || evidence.physically_changed_neurons.len() != neuron_count
        || evidence.active_recurrence_contacts.len() != contact_count
        || !evidence
            .gate_work_perturbed_neurons
            .iter()
            .any(|value| *value)
    {
        return Err(FormationError::NoncanonicalState);
    }
    let excitation_layout = evidence
        .receptor_excitation_zeptojoules
        .iter()
        .any(Option::is_some);
    let mut encoded = Vec::new();
    encoded.extend_from_slice(if evidence.endogenous && excitation_layout {
        ENDOGENOUS_EXCITATION_RECURRENCE_MAGIC
    } else if excitation_layout {
        EXCITATION_RECURRENCE_MAGIC
    } else if evidence.endogenous && evidence.carries_physical_change_codec {
        ENDOGENOUS_PHYSICAL_RECURRENCE_MAGIC
    } else if evidence.endogenous {
        ENDOGENOUS_RECURRENCE_MAGIC
    } else if evidence.carries_physical_change_codec {
        PHYSICAL_RECURRENCE_MAGIC
    } else {
        RECURRENCE_MAGIC
    });
    encode_bool_slice(&mut encoded, &evidence.gate_work_perturbed_neurons)?;
    if excitation_layout {
        encode_optional_exact_slice(&mut encoded, &evidence.receptor_excitation_zeptojoules)?;
    }
    if evidence.carries_physical_change_codec {
        encode_bool_slice(&mut encoded, &evidence.physically_changed_neurons)?;
    }
    encode_bool_slice(&mut encoded, &evidence.active_recurrence_contacts)?;
    Ok(encoded)
}

fn decode_recurrence_evidence(
    encoded: &[u8],
    anatomy: &ReachedCohortAnatomy,
) -> Result<ResidentRecurrenceEvidence, FormationError> {
    let (endogenous, carries_physical_change, excitation_layout) = if encoded
        .get(..EXCITATION_RECURRENCE_MAGIC.len())
        == Some(EXCITATION_RECURRENCE_MAGIC)
    {
        (false, true, true)
    } else if encoded.get(..ENDOGENOUS_EXCITATION_RECURRENCE_MAGIC.len())
        == Some(ENDOGENOUS_EXCITATION_RECURRENCE_MAGIC)
    {
        (true, true, true)
    } else if encoded.get(..PHYSICAL_RECURRENCE_MAGIC.len()) == Some(PHYSICAL_RECURRENCE_MAGIC) {
        (false, true, false)
    } else if encoded.get(..ENDOGENOUS_PHYSICAL_RECURRENCE_MAGIC.len())
        == Some(ENDOGENOUS_PHYSICAL_RECURRENCE_MAGIC)
    {
        (true, true, false)
    } else if encoded.get(..RECURRENCE_MAGIC.len()) == Some(RECURRENCE_MAGIC) {
        (false, false, false)
    } else if encoded.get(..ENDOGENOUS_RECURRENCE_MAGIC.len()) == Some(ENDOGENOUS_RECURRENCE_MAGIC)
    {
        (true, false, false)
    } else {
        return Err(FormationError::NoncanonicalState);
    };
    let mut cursor = RECURRENCE_MAGIC.len();
    let gate_work_perturbed_neurons =
        decode_bool_slice(encoded, &mut cursor, anatomy.neuron_count())?;
    let receptor_excitation_zeptojoules = if excitation_layout {
        decode_optional_exact_slice(encoded, &mut cursor, anatomy.neuron_count())?
    } else {
        vec![None; anatomy.neuron_count()].into_boxed_slice()
    };
    let physically_changed_neurons = if carries_physical_change {
        decode_bool_slice(encoded, &mut cursor, anatomy.neuron_count())?
    } else {
        vec![false; anatomy.neuron_count()].into_boxed_slice()
    };
    let active_recurrence_contacts =
        decode_bool_slice(encoded, &mut cursor, anatomy.contact_count())?;
    if cursor != encoded.len() || !gate_work_perturbed_neurons.iter().any(|value| *value) {
        return Err(FormationError::NoncanonicalState);
    }
    Ok(ResidentRecurrenceEvidence {
        carries_physical_change_codec: carries_physical_change,
        gate_work_perturbed_neurons,
        receptor_excitation_zeptojoules,
        physically_changed_neurons,
        active_recurrence_contacts,
        endogenous,
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

fn encode_optional_exact_slice(
    encoded: &mut Vec<u8>,
    values: &[Option<ExactRational>],
) -> Result<(), FormationError> {
    push_length(encoded, values.len())?;
    for value in values {
        match value {
            None => encoded.push(0),
            Some(value) => {
                encoded.push(1);
                let (numerator, denominator) = value.parts();
                encoded.extend_from_slice(&numerator.to_le_bytes());
                encoded.extend_from_slice(&denominator.to_le_bytes());
            }
        }
    }
    Ok(())
}

fn decode_optional_exact_slice(
    encoded: &[u8],
    cursor: &mut usize,
    expected: usize,
) -> Result<Box<[Option<ExactRational>]>, FormationError> {
    if read_length(encoded, cursor)? != expected {
        return Err(FormationError::NoncanonicalState);
    }
    let mut values = Vec::new();
    values
        .try_reserve_exact(expected)
        .map_err(|_| FormationError::ArithmeticOverflow)?;
    for _ in 0..expected {
        let present = *encoded
            .get(*cursor)
            .ok_or(FormationError::NoncanonicalState)?;
        *cursor = cursor
            .checked_add(1)
            .ok_or(FormationError::ArithmeticOverflow)?;
        match present {
            0 => values.push(None),
            1 => {
                let numerator_end = cursor
                    .checked_add(16)
                    .ok_or(FormationError::ArithmeticOverflow)?;
                let numerator = i128::from_le_bytes(
                    encoded
                        .get(*cursor..numerator_end)
                        .ok_or(FormationError::NoncanonicalState)?
                        .try_into()
                        .map_err(|_| FormationError::NoncanonicalState)?,
                );
                *cursor = numerator_end;
                let denominator_end = cursor
                    .checked_add(16)
                    .ok_or(FormationError::ArithmeticOverflow)?;
                let denominator = u128::from_le_bytes(
                    encoded
                        .get(*cursor..denominator_end)
                        .ok_or(FormationError::NoncanonicalState)?
                        .try_into()
                        .map_err(|_| FormationError::NoncanonicalState)?,
                );
                *cursor = denominator_end;
                values.push(Some(
                    ExactRational::new(numerator, denominator)
                        .map_err(|_| FormationError::NoncanonicalState)?,
                ));
            }
            _ => return Err(FormationError::NoncanonicalState),
        }
    }
    Ok(values.into_boxed_slice())
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
    *next_lineage_ordinal = successor;
    local_lineage_from_ordinal(ordinal)
}

fn local_lineage_from_ordinal(ordinal: u64) -> Result<[u8; 16], FormationError> {
    if ordinal == 0 {
        return Err(FormationError::NeuronLineageAuthorityAbsent);
    }
    let mut lineage = [0u8; 16];
    lineage[..8].copy_from_slice(LINEAGE_DOMAIN);
    lineage[8..].copy_from_slice(&ordinal.to_be_bytes());
    Ok(lineage)
}

struct ReachedLineageAdmission {
    lineage: [u8; 16],
    claimed_resting_neuron: Option<MaterializedRestingNeuron>,
}

fn reached_genesis_cell_from_admission(
    shared: &crate::joint_uf_neuron_boundary::SharedCompleteJointField,
    coordinate_index: usize,
    source_site: NeuronSourceSite,
    admission: &ReachedLineageAdmission,
) -> Result<ReachedNeuronGenesisCell, FormationError> {
    let perspective = bind_neuron_perspective(shared, coordinate_index, 0)
        .map_err(FormationError::JointFieldUnavailable)?;
    let neuron = match &admission.claimed_resting_neuron {
        Some(resting) => reach_quiescent_virtual_material_neuron(
            perspective,
            &source_site,
            resting.place,
            &resting.anatomy,
            &resting.state,
        ),
        None => create_virtual_material_neuron(perspective, &source_site),
    }
    .map_err(FormationError::PhysicalGenesisUnavailable)?;
    let (anatomy, state, _) = neuron.into_parts();
    Ok(ReachedNeuronGenesisCell {
        anatomy,
        lineage: admission.lineage,
        mount: ReachedNeuronMount::Receptor(source_site),
        state,
    })
}

fn claim_resting_or_allocate_lineage(
    resting_population: &mut Option<DevelopmentalRestingPopulation>,
    source_site: &NeuronSourceSite,
    next_lineage_ordinal: &mut u64,
) -> Result<ReachedLineageAdmission, FormationError> {
    let place = DeclaredNeuronPlace::from_source_site(source_site);
    if let Some(population) = resting_population.as_ref() {
        if let Some(offset) = population.population_offset(place) {
            let (successor, materialized) = population
                .claim(offset)
                .map_err(FormationError::DevelopmentalRestingPopulationUnavailable)?;
            let lineage = local_lineage_from_ordinal(materialized.lineage_ordinal)?;
            *resting_population = Some(successor);
            return Ok(ReachedLineageAdmission {
                lineage,
                claimed_resting_neuron: Some(materialized),
            });
        }
    }
    Ok(ReachedLineageAdmission {
        lineage: allocate_local_lineage(next_lineage_ordinal)?,
        claimed_resting_neuron: None,
    })
}

fn mount_intrinsic_neuron_at_place(
    cohorts: &mut Vec<ResidentReachedCohort>,
    resting_population: &mut Option<DevelopmentalRestingPopulation>,
    next_lineage_ordinal: &mut u64,
    place: DeclaredNeuronPlace,
) -> Result<[u8; 16], FormationError> {
    let existing = cohorts
        .iter()
        .flat_map(|cohort| {
            cohort
                .anatomy
                .mounts()
                .iter()
                .zip(cohort.anatomy.neuron_lineages())
        })
        .filter(|(mount, _)| mount.place() == place)
        .map(|(_, lineage)| *lineage)
        .collect::<Vec<_>>();
    match existing.as_slice() {
        [lineage] => return Ok(*lineage),
        [] => {}
        _ => return Err(FormationError::NeuronLineageAuthorityChanged),
    }

    let (lineage, anatomy, state) = if let Some(population) = resting_population.as_ref() {
        if let Some(offset) = population.population_offset(place) {
            let (successor, materialized) = population
                .claim(offset)
                .map_err(FormationError::DevelopmentalRestingPopulationUnavailable)?;
            let lineage = local_lineage_from_ordinal(materialized.lineage_ordinal)?;
            *resting_population = Some(successor);
            (lineage, materialized.anatomy, materialized.state)
        } else {
            *resting_population = Some(
                population
                    .admit_one_external_growth_unit()
                    .map_err(FormationError::DevelopmentalRestingPopulationUnavailable)?,
            );
            let neuron = create_quiescent_virtual_material_neuron(place)
                .map_err(FormationError::PhysicalGenesisUnavailable)?;
            (
                allocate_local_lineage(next_lineage_ordinal)?,
                neuron.anatomy,
                neuron.state,
            )
        }
    } else {
        let neuron = create_quiescent_virtual_material_neuron(place)
            .map_err(FormationError::PhysicalGenesisUnavailable)?;
        (
            allocate_local_lineage(next_lineage_ordinal)?,
            neuron.anatomy,
            neuron.state,
        )
    };
    let sparse = SparseElectricalAnatomy::new(1, Vec::new())
        .map_err(FormationError::ResidentElectricalUnavailable)?;
    let sparse_state = SparseElectricalState::genesis(&sparse);
    let cohort_anatomy = ReachedCohortAnatomy::new_mounted(
        vec![anatomy],
        vec![lineage],
        vec![ReachedNeuronMount::Intrinsic(place)],
        sparse,
    )
    .map_err(FormationError::PhysicalSettlementUnavailable)?;
    let cohort_state = ReachedCohortState::new(&cohort_anatomy, vec![state], sparse_state)
        .map_err(FormationError::PhysicalSettlementUnavailable)?;
    cohorts.push(ResidentReachedCohort {
        anatomy: cohort_anatomy,
        state: cohort_state,
        pending_experience: None,
        retained_experience: None,
        pending_recurrence: None,
    });
    Ok(lineage)
}

/// Materialize one source-independent local-integration neuron at a unique
/// declared projection of each reached receptor place, then author one sparse
/// physical contact from the receptor lineage to that local integration
/// lineage. Existing cells and contacts are reused exactly; this is
/// developmental specialization, not a per-occurrence generator.
fn mount_reached_local_integration(
    cohorts: &mut Vec<ResidentReachedCohort>,
    resting_population: &mut Option<DevelopmentalRestingPopulation>,
    next_lineage_ordinal: &mut u64,
    electrical_fabric: &mut ResidentElectricalFabric,
) -> Result<(), FormationError> {
    let receptors = cohorts
        .iter()
        .flat_map(|cohort| {
            cohort
                .anatomy
                .mounts()
                .iter()
                .zip(cohort.anatomy.neuron_lineages())
        })
        .filter_map(|(mount, lineage)| mount.source_site().map(|_| (*lineage, mount.place())))
        .collect::<Vec<_>>();

    for (receptor_lineage, receptor_place) in receptors {
        let integration_place = local_integration_place(receptor_place)?;
        let integration_lineage = mount_intrinsic_neuron_at_place(
            cohorts,
            resting_population,
            next_lineage_ordinal,
            integration_place,
        )?;
        if !electrical_fabric.contains_contact(receptor_lineage, integration_lineage) {
            *electrical_fabric = electrical_fabric
                .append_contact(
                    receptor_lineage,
                    integration_lineage,
                    ExactRational::integer(DEVELOPMENTAL_CONTACT_CONDUCTANCE_PICOSIEMENS),
                )
                .map_err(FormationError::ResidentElectricalUnavailable)?;
        }
    }
    Ok(())
}

/// Project one receptor's own two-dimensional declared place into a unique
/// local-integration topology.  `declared_neuron_territory - 1` is the existing
/// injective Cantor pairing of `(sense layer, topology index)`, so receptors
/// from different sensory coordinate systems can never alias merely because
/// both happen to call one local site `0`.
fn local_integration_place(
    receptor_place: DeclaredNeuronPlace,
) -> Result<DeclaredNeuronPlace, FormationError> {
    let paired = declared_neuron_territory(receptor_place)
        .map_err(|_| FormationError::ArithmeticOverflow)?
        .checked_sub(1)
        .ok_or(FormationError::ArithmeticOverflow)?;
    let topology_index = u32::try_from(paired).map_err(|_| FormationError::ArithmeticOverflow)?;
    Ok(DeclaredNeuronPlace::new(6, topology_index))
}

/// Mount one new source-independent neuron at the first quiescent place in a
/// projection layer.  This is reached-frontier growth: it claims one compactly
/// declared cell and never scans or materializes the resting population.
fn mount_next_intrinsic_in_layer(
    cohorts: &mut Vec<ResidentReachedCohort>,
    resting_population: &mut Option<DevelopmentalRestingPopulation>,
    next_lineage_ordinal: &mut u64,
    layer: u32,
) -> Result<[u8; 16], FormationError> {
    let (lineage, place, anatomy, state) = if let Some(population) = resting_population.as_ref() {
        let (successor, materialized) = population
            .claim_next_in_layer(layer)
            .map_err(FormationError::DevelopmentalRestingPopulationUnavailable)?;
        let lineage = local_lineage_from_ordinal(materialized.lineage_ordinal)?;
        *resting_population = Some(successor);
        (
            lineage,
            materialized.place,
            materialized.anatomy,
            materialized.state,
        )
    } else {
        let next_topology = cohorts
            .iter()
            .flat_map(|cohort| cohort.anatomy.mounts())
            .filter(|mount| mount.place().layer() == layer)
            .map(|mount| mount.place().topology_index())
            .max()
            .map_or(Ok(0), |maximum| {
                maximum
                    .checked_add(1)
                    .ok_or(FormationError::ArithmeticOverflow)
            })?;
        let place = DeclaredNeuronPlace::new(layer, next_topology);
        let neuron = create_quiescent_virtual_material_neuron(place)
            .map_err(FormationError::PhysicalGenesisUnavailable)?;
        (
            allocate_local_lineage(next_lineage_ordinal)?,
            place,
            neuron.anatomy,
            neuron.state,
        )
    };
    let sparse = SparseElectricalAnatomy::new(1, Vec::new())
        .map_err(FormationError::ResidentElectricalUnavailable)?;
    let sparse_state = SparseElectricalState::genesis(&sparse);
    let cohort_anatomy = ReachedCohortAnatomy::new_mounted(
        vec![anatomy],
        vec![lineage],
        vec![ReachedNeuronMount::Intrinsic(place)],
        sparse,
    )
    .map_err(FormationError::PhysicalSettlementUnavailable)?;
    let cohort_state = ReachedCohortState::new(&cohort_anatomy, vec![state], sparse_state)
        .map_err(FormationError::PhysicalSettlementUnavailable)?;
    cohorts.push(ResidentReachedCohort {
        anatomy: cohort_anatomy,
        state: cohort_state,
        pending_experience: None,
        retained_experience: None,
        pending_recurrence: None,
    });
    Ok(lineage)
}

/// Grow or reuse one physical cross-sensory association reached by this exact
/// occurrence.  Membership comes only from distinct layer-6 cells whose own
/// receptors were externally reached; matching indices, labels, and source
/// order have no authority.  The retained sparse contacts are the assembly.
fn mount_reached_cross_sensory_association(
    cohorts: &mut Vec<ResidentReachedCohort>,
    resting_population: &mut Option<DevelopmentalRestingPopulation>,
    next_lineage_ordinal: &mut u64,
    electrical_fabric: &mut ResidentElectricalFabric,
    externally_reached_lineages: &[[u8; 16]],
) -> Result<(), FormationError> {
    let mounted = cohorts
        .iter()
        .flat_map(|cohort| {
            cohort
                .anatomy
                .mounts()
                .iter()
                .zip(cohort.anatomy.neuron_lineages())
        })
        .map(|(mount, lineage)| (*lineage, mount.clone()))
        .collect::<Vec<_>>();
    let mut sensory_layers = Vec::<u32>::new();
    let mut integration_lineages = Vec::<[u8; 16]>::new();
    for receptor_lineage in externally_reached_lineages {
        let Some((_, receptor_mount)) = mounted
            .iter()
            .find(|(lineage, mount)| lineage == receptor_lineage && mount.source_site().is_some())
        else {
            continue;
        };
        let receptor_place = receptor_mount.place();
        if !sensory_layers.contains(&receptor_place.layer()) {
            sensory_layers.push(receptor_place.layer());
        }
        let integration_place = local_integration_place(receptor_place)?;
        let integration = mounted
            .iter()
            .filter(|(_, mount)| {
                mount.source_site().is_none() && mount.place() == integration_place
            })
            .map(|(lineage, _)| *lineage)
            .collect::<Vec<_>>();
        let [integration_lineage] = integration.as_slice() else {
            return Err(FormationError::NeuronLineageAuthorityChanged);
        };
        if !electrical_fabric.contains_contact(*receptor_lineage, *integration_lineage) {
            return Err(FormationError::NeuronLineageAuthorityAbsent);
        }
        if !integration_lineages.contains(integration_lineage) {
            integration_lineages.push(*integration_lineage);
        }
    }
    integration_lineages.sort_unstable();
    sensory_layers.sort_unstable();
    if integration_lineages.len() < 3 || sensory_layers.len() < 2 {
        return Ok(());
    }

    let layer_of = |lineage: [u8; 16]| {
        mounted
            .iter()
            .find(|(candidate, _)| *candidate == lineage)
            .map(|(_, mount)| mount.place().layer())
    };
    let mut matching_associations = Vec::new();
    for (association_lineage, association_mount) in mounted
        .iter()
        .filter(|(_, mount)| mount.source_site().is_none() && mount.place().layer() == 7)
    {
        let mut layer_six_neighbours = Vec::new();
        for (left, right) in electrical_fabric.contact_endpoints() {
            let left_lineage = electrical_fabric.lineages()[left];
            let right_lineage = electrical_fabric.lineages()[right];
            let neighbour = if left_lineage == *association_lineage {
                Some(right_lineage)
            } else if right_lineage == *association_lineage {
                Some(left_lineage)
            } else {
                None
            };
            if let Some(neighbour) = neighbour {
                if layer_of(neighbour) == Some(6) {
                    layer_six_neighbours.push(neighbour);
                }
            }
        }
        layer_six_neighbours.sort_unstable();
        layer_six_neighbours.dedup();
        if layer_six_neighbours == integration_lineages {
            matching_associations.push(*association_lineage);
        }
        let _ = association_mount;
    }
    let association_lineage = match matching_associations.as_slice() {
        [lineage] => *lineage,
        [] => mount_next_intrinsic_in_layer(cohorts, resting_population, next_lineage_ordinal, 7)?,
        _ => return Err(FormationError::NeuronLineageAuthorityChanged),
    };
    for integration_lineage in integration_lineages {
        if !electrical_fabric.contains_contact(integration_lineage, association_lineage) {
            *electrical_fabric = electrical_fabric
                .append_contact(
                    integration_lineage,
                    association_lineage,
                    ExactRational::integer(DEVELOPMENTAL_CONTACT_CONDUCTANCE_PICOSIEMENS),
                )
                .map_err(FormationError::ResidentElectricalUnavailable)?;
        }
    }
    Ok(())
}

/// Couple each genuinely reached body-or-balance receptor to its own local
/// regulatory neuron.  The route is receptor layer 5 -> its already-mounted
/// layer-6 integrator -> the topology-corresponding layer-8 cell.  No body-wide
/// energy total, fuel fraction, readiness value, or other bookkeeping scalar
/// is sensed here: locality and membership come only from the reached physical
/// receptor lineage carried by this exact occurrence.
fn mount_reached_body_regulation(
    cohorts: &mut Vec<ResidentReachedCohort>,
    resting_population: &mut Option<DevelopmentalRestingPopulation>,
    next_lineage_ordinal: &mut u64,
    electrical_fabric: &mut ResidentElectricalFabric,
    externally_reached_lineages: &[[u8; 16]],
) -> Result<(), FormationError> {
    let mounted = cohorts
        .iter()
        .flat_map(|cohort| {
            cohort
                .anatomy
                .mounts()
                .iter()
                .zip(cohort.anatomy.neuron_lineages())
        })
        .map(|(mount, lineage)| (*lineage, mount.clone()))
        .collect::<Vec<_>>();
    let reached_body_receptors = externally_reached_lineages
        .iter()
        .filter_map(|lineage| {
            mounted
                .iter()
                .find(|(candidate, mount)| {
                    candidate == lineage
                        && mount.source_site().is_some()
                        && mount.place().layer() == 5
                })
                .map(|(_, mount)| (*lineage, mount.place()))
        })
        .collect::<Vec<_>>();

    for (receptor_lineage, receptor_place) in reached_body_receptors {
        let integration_place = local_integration_place(receptor_place)?;
        let integration = mounted
            .iter()
            .filter(|(_, mount)| {
                mount.source_site().is_none() && mount.place() == integration_place
            })
            .map(|(lineage, _)| *lineage)
            .collect::<Vec<_>>();
        let [integration_lineage] = integration.as_slice() else {
            return Err(FormationError::NeuronLineageAuthorityChanged);
        };
        if !electrical_fabric.contains_contact(receptor_lineage, *integration_lineage) {
            return Err(FormationError::NeuronLineageAuthorityAbsent);
        }
        let regulation_place = DeclaredNeuronPlace::new(8, integration_place.topology_index());
        let regulation_lineage = mount_intrinsic_neuron_at_place(
            cohorts,
            resting_population,
            next_lineage_ordinal,
            regulation_place,
        )?;
        if !electrical_fabric.contains_contact(*integration_lineage, regulation_lineage) {
            *electrical_fabric = electrical_fabric
                .append_contact(
                    *integration_lineage,
                    regulation_lineage,
                    ExactRational::integer(DEVELOPMENTAL_CONTACT_CONDUCTANCE_PICOSIEMENS),
                )
                .map_err(FormationError::ResidentElectricalUnavailable)?;
        }
    }
    Ok(())
}

/// Relate body regulation to the association material that physically moved
/// with it in this exact organism interval.  Layer 10 is developmental
/// geography, not an emotion label: its only authority is the coincident
/// changed layer-7/layer-8 lineage set and the sparse contacts retained here.
/// Reaching the same set again reuses the same cell without population growth.
fn mount_reached_affective_reach(
    cohorts: &mut Vec<ResidentReachedCohort>,
    resting_population: &mut Option<DevelopmentalRestingPopulation>,
    next_lineage_ordinal: &mut u64,
    electrical_fabric: &mut ResidentElectricalFabric,
    physically_transitioned_lineages: &[[u8; 16]],
) -> Result<(), FormationError> {
    let mounted = cohorts
        .iter()
        .flat_map(|cohort| {
            cohort
                .anatomy
                .mounts()
                .iter()
                .zip(cohort.anatomy.neuron_lineages())
        })
        .map(|(mount, lineage)| (*lineage, mount.clone()))
        .collect::<Vec<_>>();
    let mut association = Vec::new();
    let mut body_regulation = Vec::new();
    for lineage in physically_transitioned_lineages {
        let Some((_, mount)) = mounted.iter().find(|(candidate, _)| candidate == lineage) else {
            return Err(FormationError::NeuronLineageAuthorityAbsent);
        };
        match mount.place().layer() {
            7 if !association.contains(lineage) => association.push(*lineage),
            8 if !body_regulation.contains(lineage) => body_regulation.push(*lineage),
            _ => {}
        }
    }
    if association.is_empty() || body_regulation.is_empty() {
        return Ok(());
    }
    let mut participants = association;
    participants.extend(body_regulation);
    participants.sort_unstable();
    participants.dedup();

    let layer_of = |lineage: [u8; 16]| {
        mounted
            .iter()
            .find(|(candidate, _)| *candidate == lineage)
            .map(|(_, mount)| mount.place().layer())
    };
    let mut matching = Vec::new();
    for (candidate, _) in mounted
        .iter()
        .filter(|(_, mount)| mount.source_site().is_none() && mount.place().layer() == 10)
    {
        let mut neighbours = Vec::new();
        for (left, right) in electrical_fabric.contact_endpoints() {
            let left_lineage = electrical_fabric.lineages()[left];
            let right_lineage = electrical_fabric.lineages()[right];
            let neighbour = if left_lineage == *candidate {
                Some(right_lineage)
            } else if right_lineage == *candidate {
                Some(left_lineage)
            } else {
                None
            };
            if let Some(neighbour) = neighbour {
                if matches!(layer_of(neighbour), Some(7) | Some(8)) {
                    neighbours.push(neighbour);
                }
            }
        }
        neighbours.sort_unstable();
        neighbours.dedup();
        if neighbours == participants {
            matching.push(*candidate);
        }
    }
    let affective_lineage = match matching.as_slice() {
        [lineage] => *lineage,
        [] => mount_next_intrinsic_in_layer(cohorts, resting_population, next_lineage_ordinal, 10)?,
        _ => return Err(FormationError::NeuronLineageAuthorityChanged),
    };
    for participant in participants {
        if !electrical_fabric.contains_contact(participant, affective_lineage) {
            *electrical_fabric = electrical_fabric
                .append_contact(
                    participant,
                    affective_lineage,
                    ExactRational::integer(DEVELOPMENTAL_CONTACT_CONDUCTANCE_PICOSIEMENS),
                )
                .map_err(FormationError::ResidentElectricalUnavailable)?;
        }
    }
    Ok(())
}

/// Give each newly admitted retained mosaic one sparse recurrent route through
/// layer 9.  Admission has already proved the member deltas and physical bonds;
/// this function neither recognizes nor names them.  One intrinsic cell is
/// reached once and connected to the mosaic's actual member lineages.  The
/// retained mosaic remains the complete authority, so a later reassembly can
/// reach distributed members without turning this cell into a stored answer.
fn mount_new_recurrent_retention(
    cohorts: &mut Vec<ResidentReachedCohort>,
    resting_population: &mut Option<DevelopmentalRestingPopulation>,
    next_lineage_ordinal: &mut u64,
    electrical_fabric: &mut ResidentElectricalFabric,
    newly_retained_mosaic_members: &[Vec<[u8; 16]>],
) -> Result<(), FormationError> {
    let resident_lineages = cohorts
        .iter()
        .flat_map(|cohort| cohort.anatomy.neuron_lineages().iter().copied())
        .collect::<Vec<_>>();
    for members in newly_retained_mosaic_members {
        if members.len() < 3
            || members.iter().enumerate().any(|(index, lineage)| {
                !resident_lineages.contains(lineage) || members[..index].contains(lineage)
            })
        {
            return Err(FormationError::NeuronLineageAuthorityChanged);
        }
        let retention_lineage =
            mount_next_intrinsic_in_layer(cohorts, resting_population, next_lineage_ordinal, 9)?;
        for member in members {
            if !electrical_fabric.contains_contact(*member, retention_lineage) {
                *electrical_fabric = electrical_fabric
                    .append_contact(
                        *member,
                        retention_lineage,
                        ExactRational::integer(DEVELOPMENTAL_CONTACT_CONDUCTANCE_PICOSIEMENS),
                    )
                    .map_err(FormationError::ResidentElectricalUnavailable)?;
            }
        }
    }
    Ok(())
}

#[derive(Clone, Copy)]
enum ResidentContactOrigin {
    Local {
        cohort_index: usize,
        contact_index: usize,
        left_member: usize,
        right_member: usize,
    },
    Fabric {
        contact_index: usize,
    },
}

struct ResidentContactEdge {
    left: usize,
    right: usize,
    conductance: ExactRational,
    state: ElectricalContactState,
    stable_bond: StablePhysicalBondReference,
    origin: ResidentContactOrigin,
}

struct InternalContactSettlementObservation {
    dsf_delivery_count: usize,
    active_bonds: Vec<StablePhysicalBondReference>,
}

fn stable_bond_for_next_edge(
    edges: &[ResidentContactEdge],
    first: [u8; 16],
    second: [u8; 16],
) -> Result<StablePhysicalBondReference, FormationError> {
    let canonical = if first < second {
        (first, second)
    } else {
        (second, first)
    };
    let parallel_ordinal = u32::try_from(
        edges
            .iter()
            .filter(|edge| edge.stable_bond.endpoints() == canonical)
            .count(),
    )
    .map_err(|_| FormationError::ArithmeticOverflow)?;
    StablePhysicalBondReference::new(first, second, parallel_ordinal)
        .ok_or(FormationError::NoncanonicalState)
}

/// Advance an already-identified physical seed frontier across exactly one
/// contact boundary.  This is deliberately not a graph traversal: material
/// that reaches the far side of one contact must persist there before it can
/// become authority for another interval.
fn one_interval_electrical_frontier(
    seeds: &[bool],
    contact_endpoints: &[(usize, usize)],
) -> Result<Vec<bool>, FormationError> {
    let mut reached = seeds.to_vec();
    for (left, right) in contact_endpoints.iter().copied() {
        let left_seed = *seeds
            .get(left)
            .ok_or(FormationError::NeuronLineageAuthorityAbsent)?;
        let right_seed = *seeds
            .get(right)
            .ok_or(FormationError::NeuronLineageAuthorityAbsent)?;
        if left_seed || right_seed {
            reached[left] = true;
            reached[right] = true;
        }
    }
    Ok(reached)
}

/// Settle the bounded contact-connected frontier reached by this external
/// occurrence, form one native membrane-potential occurrence from its exact
/// predecessor/successor states, evaluate unchanged full DSF once, and let
/// every reached complete neuron settle that shared field.  Local and
/// cross-cohort contact carrier motion is computed once in one synchronous
/// generation; cohort recovery fluids remain wholly separate.
#[allow(clippy::too_many_arguments)]
fn settle_internal_contact_interval(
    cohorts: &mut [ResidentReachedCohort],
    electrical_fabric: &mut ResidentElectricalFabric,
    externally_reached_lineages: &[[u8; 16]],
    physically_transitioned_neuron_lineages: &mut Vec<[u8; 16]>,
    emitted_neuron_fractals: &mut Vec<EmittedNeuronFractal>,
) -> Result<InternalContactSettlementObservation, FormationError> {
    if externally_reached_lineages.is_empty() || electrical_fabric.contact_count() == 0 {
        return Ok(InternalContactSettlementObservation {
            dsf_delivery_count: 0,
            active_bonds: Vec::new(),
        });
    }

    let mut flat_locations = Vec::<(usize, usize, [u8; 16])>::new();
    for (cohort_index, cohort) in cohorts.iter().enumerate() {
        for (neuron_index, lineage) in cohort.anatomy.neuron_lineages().iter().enumerate() {
            if flat_locations.iter().any(|(_, _, prior)| prior == lineage) {
                return Err(FormationError::NeuronLineageAuthorityChanged);
            }
            flat_locations.push((cohort_index, neuron_index, *lineage));
        }
    }
    let lineage_member = |lineage: [u8; 16]| {
        flat_locations
            .iter()
            .position(|(_, _, retained)| *retained == lineage)
            .ok_or(FormationError::NeuronLineageAuthorityAbsent)
    };

    let mut edges = Vec::<ResidentContactEdge>::new();
    let mut cohort_offsets = Vec::with_capacity(cohorts.len());
    let mut offset = 0usize;
    for (cohort_index, cohort) in cohorts.iter().enumerate() {
        cohort_offsets.push(offset);
        for (contact_index, (contact, state)) in cohort
            .anatomy
            .electrical_anatomy()
            .contact_anatomies()
            .iter()
            .copied()
            .zip(cohort.state.electrical().contact_states().iter().cloned())
            .enumerate()
        {
            let (left_member, right_member) = contact.endpoints();
            let stable_bond = stable_bond_for_next_edge(
                &edges,
                cohort.anatomy.neuron_lineages()[left_member],
                cohort.anatomy.neuron_lineages()[right_member],
            )?;
            edges.push(ResidentContactEdge {
                left: offset
                    .checked_add(left_member)
                    .ok_or(FormationError::ArithmeticOverflow)?,
                right: offset
                    .checked_add(right_member)
                    .ok_or(FormationError::ArithmeticOverflow)?,
                conductance: contact.conductance_picosiemens(),
                state,
                stable_bond,
                origin: ResidentContactOrigin::Local {
                    cohort_index,
                    contact_index,
                    left_member,
                    right_member,
                },
            });
        }
        offset = offset
            .checked_add(cohort.anatomy.neuron_count())
            .ok_or(FormationError::ArithmeticOverflow)?;
    }
    for (contact_index, ((left, right), (contact, state))) in electrical_fabric
        .contact_endpoints()
        .zip(
            electrical_fabric
                .anatomy()
                .contact_anatomies()
                .iter()
                .copied()
                .zip(electrical_fabric.state().contact_states().iter().cloned()),
        )
        .enumerate()
    {
        let left_lineage = *electrical_fabric
            .lineages()
            .get(left)
            .ok_or(FormationError::NeuronLineageAuthorityAbsent)?;
        let right_lineage = *electrical_fabric
            .lineages()
            .get(right)
            .ok_or(FormationError::NeuronLineageAuthorityAbsent)?;
        let stable_bond = stable_bond_for_next_edge(&edges, left_lineage, right_lineage)?;
        edges.push(ResidentContactEdge {
            left: lineage_member(left_lineage)?,
            right: lineage_member(right_lineage)?,
            conductance: contact.conductance_picosiemens(),
            state,
            stable_bond,
            origin: ResidentContactOrigin::Fabric { contact_index },
        });
    }

    // One physical interval reaches only the externally driven or still
    // charged material and its immediate electrical neighbours.  The former
    // transitive graph closure treated a contact as instantaneous authority to
    // poll every neuron in the connected component, even when no carrier had
    // crossed the intervening contacts.  Charge retained in a newly reached
    // neighbour becomes the seed of a later interval, so propagation advances
    // through lived time rather than jumping across the whole brain.
    let mut seeds = flat_locations
        .iter()
        .map(|(cohort_index, neuron_index, lineage)| {
            externally_reached_lineages.contains(lineage)
                || cohorts[*cohort_index].state.neurons()[*neuron_index]
                    .membrane_state()
                    .separated_elementary_charges()
                    != 0
        })
        .collect::<Vec<_>>();
    for edge in &edges {
        if edge.state.carrier_phase()
            != crate::elementary_charge_transfer::ChargeCarrierPhase::zero()
        {
            seeds[edge.left] = true;
            seeds[edge.right] = true;
        }
    }
    let contact_endpoints = edges
        .iter()
        .map(|edge| (edge.left, edge.right))
        .collect::<Vec<_>>();
    let reached = one_interval_electrical_frontier(&seeds, &contact_endpoints)?;
    let selected = reached
        .iter()
        .enumerate()
        .filter_map(|(index, reached)| reached.then_some(index))
        .collect::<Vec<_>>();
    if selected.is_empty() {
        return Ok(InternalContactSettlementObservation {
            dsf_delivery_count: 0,
            active_bonds: Vec::new(),
        });
    }
    let mut compact_index = vec![None; flat_locations.len()];
    for (index, flat) in selected.iter().copied().enumerate() {
        compact_index[flat] = Some(index);
    }

    let mut compact_contacts = Vec::new();
    let mut compact_states = Vec::new();
    let mut compact_origins = Vec::new();
    let mut compact_bonds = Vec::new();
    for edge in &edges {
        let (Some(left), Some(right)) = (compact_index[edge.left], compact_index[edge.right])
        else {
            continue;
        };
        compact_contacts.push(
            ElectricalContactAnatomy::new(left, right, edge.conductance, selected.len())
                .map_err(FormationError::ResidentElectricalUnavailable)?,
        );
        compact_states.push(edge.state.clone());
        compact_origins.push(edge.origin);
        compact_bonds.push(edge.stable_bond);
    }
    if compact_contacts.is_empty() {
        return Ok(InternalContactSettlementObservation {
            dsf_delivery_count: 0,
            active_bonds: Vec::new(),
        });
    }
    let compact_anatomy = SparseElectricalAnatomy::new(selected.len(), compact_contacts)
        .map_err(FormationError::ResidentElectricalUnavailable)?;
    let compact_predecessor =
        SparseElectricalState::from_contact_states(&compact_anatomy, compact_states)
            .map_err(FormationError::ResidentElectricalUnavailable)?;

    let mut capacitances = Vec::with_capacity(selected.len());
    let mut membranes = Vec::with_capacity(selected.len());
    let mut available_carriers = Vec::with_capacity(selected.len());
    let mut total_carriers = Vec::with_capacity(selected.len());
    for flat in selected.iter().copied() {
        let (cohort_index, neuron_index, _) = flat_locations[flat];
        let anatomy = &cohorts[cohort_index].anatomy.neuron_anatomies()[neuron_index];
        let state = &cohorts[cohort_index].state.neurons()[neuron_index];
        capacitances.push(anatomy.capacitance());
        membranes.push(state.membrane_state());
        available_carriers.push(state.carrier_reservoirs().intracellular());
        total_carriers.push(
            state
                .carrier_reservoirs()
                .total()
                .ok_or(FormationError::ArithmeticOverflow)?,
        );
    }
    let interval_microseconds = WORLD_MECHANICAL_TICK_MICROSECONDS;
    let settled = settle_sparse_electrical_transfers(
        &compact_anatomy,
        &compact_predecessor,
        &capacitances,
        &membranes,
        &available_carriers,
        interval_microseconds,
    )
    .map_err(FormationError::ResidentElectricalUnavailable)?;

    let mut pre_field = Vec::with_capacity(selected.len());
    let mut post_field = Vec::with_capacity(selected.len());
    let mut coordinate_bounds = Vec::with_capacity(selected.len());
    let mut post_membranes = Vec::with_capacity(selected.len());
    for coordinate in 0..selected.len() {
        let transition = settle_membrane_elementary_charges(
            capacitances[coordinate],
            membranes[coordinate],
            settled.outward_elementary_charges_by_neuron[coordinate],
            interval_microseconds,
        )
        .map_err(FormationError::InternalMembraneUnavailable)?;
        let pre = exact_rational_binary64(transition.predecessor_potential_millivolts)?;
        let post = exact_rational_binary64(transition.successor_potential_millivolts)?;
        // The live membrane may already hold separated charge established by
        // its own gate paths in addition to the presently mobile contact
        // reservoir.  The internal occurrence's closed physical span must
        // therefore contain exact predecessor separation, exact successor
        // separation, and all finite carrier material that could move through
        // the reached contact.  These are the transition's own conserved
        // physical endpoints/material, not a statistical or tuned range.
        let carrier_bound = i128::try_from(total_carriers[coordinate])
            .map_err(|_| FormationError::ArithmeticOverflow)?
            .max(
                membranes[coordinate]
                    .separated_elementary_charges()
                    .unsigned_abs()
                    .try_into()
                    .map_err(|_| FormationError::ArithmeticOverflow)?,
            )
            .max(
                transition
                    .successor
                    .separated_elementary_charges()
                    .unsigned_abs()
                    .try_into()
                    .map_err(|_| FormationError::ArithmeticOverflow)?,
            );
        let positive_bound = settle_membrane_elementary_charges(
            capacitances[coordinate],
            crate::elementary_charge_membrane::ElementaryChargeMembraneState::genesis(
                carrier_bound,
            ),
            0,
            interval_microseconds,
        )
        .map_err(FormationError::InternalMembraneUnavailable)?
        .predecessor_potential_millivolts;
        let bound = exact_rational_binary64(positive_bound)?.abs();
        pre_field.push(pre);
        post_field.push(post);
        coordinate_bounds.push(
            JointUfCoordinateBounds::new(-bound, bound).map_err(|error| {
                FormationError::JointFieldUnavailable(JointNeuronBoundaryError::Source(
                    JointUfSourceError::Physics(error),
                ))
            })?,
        );
        post_membranes.push(transition.successor);
    }

    let duration = BigRational::from_integer(BigInt::from(interval_microseconds));
    let input = JointUfInput {
        times: vec![BigRational::zero(), duration.clone()],
        fields: vec![pre_field, post_field],
        relevance: vec![1.0, 1.0],
        intersample_law: JointIntersampleLaw::SampledVolumeAndRelevancePiecewiseLinear,
    };
    let bounds = JointUfPhysicalBounds::new(coordinate_bounds, duration).map_err(|error| {
        FormationError::JointFieldUnavailable(JointNeuronBoundaryError::Source(
            JointUfSourceError::Physics(error),
        ))
    })?;
    let field = joint_uf_v1_4::evaluate_with_physical_bounds(input, bounds).map_err(|error| {
        FormationError::JointFieldUnavailable(JointNeuronBoundaryError::Source(
            JointUfSourceError::Physics(error),
        ))
    })?;
    let groups = contact_components(selected.len(), &compact_anatomy);
    let source_body = Arc::<[u8]>::from(encode_internal_contact_source(
        &selected,
        &flat_locations,
        &membranes,
        &post_membranes,
        &capacitances,
        interval_microseconds,
        &compact_anatomy,
    )?);
    let source_authority = sha256(&source_body);
    let shared = prepare_complete_joint_field_from_evaluated(
        source_body,
        source_authority,
        0,
        EvaluatedJointSourceOccurrence {
            port_indices: (0..selected.len()).collect(),
            groups,
            field,
        },
    )
    .map_err(FormationError::JointFieldUnavailable)?;
    if shared.result().gates.len() != 1 {
        return Err(FormationError::NoncanonicalState);
    }

    let mut local_successors = cohorts
        .iter()
        .map(|cohort| cohort.state.electrical().contact_states().to_vec())
        .collect::<Vec<_>>();
    let mut local_transitions = cohorts
        .iter()
        .map(|cohort| {
            cohort
                .state
                .electrical()
                .contact_states()
                .iter()
                .cloned()
                .map(|successor| ElectricalContactTransition {
                    successor,
                    outward_current_from_left_picoamperes: ExactRational::integer(0),
                    outward_elementary_charges_from_left: 0,
                    plastic_changed: false,
                })
                .collect::<Vec<_>>()
        })
        .collect::<Vec<_>>();
    let mut local_outward = cohorts
        .iter()
        .map(|cohort| vec![0_i128; cohort.anatomy.neuron_count()])
        .collect::<Vec<_>>();
    let mut fabric_states = electrical_fabric.state().contact_states().to_vec();
    for (origin, transition) in compact_origins
        .iter()
        .copied()
        .zip(settled.transitions.iter().cloned())
    {
        match origin {
            ResidentContactOrigin::Local {
                cohort_index,
                contact_index,
                left_member,
                right_member,
            } => {
                local_successors[cohort_index][contact_index] = transition.successor.clone();
                local_transitions[cohort_index][contact_index] = transition.clone();
                local_outward[cohort_index][left_member] = local_outward[cohort_index][left_member]
                    .checked_add(transition.outward_elementary_charges_from_left)
                    .ok_or(FormationError::ArithmeticOverflow)?;
                local_outward[cohort_index][right_member] = local_outward[cohort_index]
                    [right_member]
                    .checked_sub(transition.outward_elementary_charges_from_left)
                    .ok_or(FormationError::ArithmeticOverflow)?;
            }
            ResidentContactOrigin::Fabric { contact_index } => {
                fabric_states[contact_index] = transition.successor;
            }
        }
    }
    *electrical_fabric = electrical_fabric
        .with_contact_states(fabric_states)
        .map_err(FormationError::ResidentElectricalUnavailable)?;

    for cohort_index in 0..cohorts.len() {
        let selected_members = selected
            .iter()
            .enumerate()
            .filter_map(|(coordinate, flat)| {
                let (resident_cohort, neuron_index, _) = flat_locations[*flat];
                (resident_cohort == cohort_index).then_some((coordinate, neuron_index))
            })
            .collect::<Vec<_>>();
        if selected_members.is_empty() {
            continue;
        }
        let mut required_positions = cohorts[cohort_index]
            .anatomy
            .neuron_anatomies()
            .iter()
            .map(|anatomy| anatomy.mathloom_positions())
            .collect::<Vec<_>>();
        for (coordinate, neuron_index) in selected_members.iter().copied() {
            let perspective = bind_neuron_perspective(&shared, coordinate, 0)
                .map_err(FormationError::JointFieldUnavailable)?;
            required_positions[neuron_index] = required_positions[neuron_index].max(
                required_mathloom_positions(perspective)
                    .map_err(FormationError::JointFieldUnavailable)?,
            );
        }
        extend_resident_cohort_positional_fabrics(&mut cohorts[cohort_index], &required_positions)?;
        let catalysts = cohorts[cohort_index]
            .anatomy
            .neuron_anatomies()
            .iter()
            .map(|anatomy| vec![0; anatomy.recovery_anatomy().psi_lane_count()].into_boxed_slice())
            .collect::<Vec<Box<[u128]>>>();
        let inputs = selected_members
            .iter()
            .map(|(coordinate, neuron_index)| {
                let perspective = bind_neuron_perspective(&shared, *coordinate, 0)
                    .map_err(FormationError::JointFieldUnavailable)?;
                Ok(NeuronIntervalInput {
                    perspective,
                    gate_work: GateWorkOccurrence::new(BigRational::zero()),
                    interval_microseconds,
                    recovery: RecoveryContact::new(&catalysts[*neuron_index], 0, 0),
                    dna_expression: DnaExpressionContact::new(0),
                    receptor_successor_residue: None,
                    prepared_psi: None,
                })
            })
            .collect::<Result<Vec<_>, FormationError>>()?;
        let resident_indices = selected_members
            .iter()
            .map(|(_, neuron_index)| *neuron_index)
            .collect::<Vec<_>>();
        let combined_outward = selected_members
            .iter()
            .map(|(coordinate, _)| settled.outward_elementary_charges_by_neuron[*coordinate])
            .collect::<Vec<_>>();
        let local_successor = SparseElectricalState::from_contact_states(
            cohorts[cohort_index].anatomy.electrical_anatomy(),
            local_successors[cohort_index].clone(),
        )
        .map_err(FormationError::ResidentElectricalUnavailable)?;
        let precomputed_local = SparseElectricalTransferSettlement {
            successor_contacts: local_successor,
            transitions: local_transitions[cohort_index].clone().into_boxed_slice(),
            outward_elementary_charges_by_neuron: local_outward[cohort_index]
                .clone()
                .into_boxed_slice(),
        };
        let input = ReachedCohortIntervalInput::from_resident_indices_with_precomputed_contacts(
            inputs,
            resident_indices,
            combined_outward,
            precomputed_local,
        )
        .map_err(FormationError::PhysicalSettlementUnavailable)?;
        let predecessor_neurons = cohorts[cohort_index].state.neurons().to_vec();
        // This interval is a native cross-cohort electrical consequence, not
        // a second externally admitted experience.  The legacy cognitive
        // admission path can express only cohort-local contact structure; if
        // it were allowed to interpret this interval it could falsely name a
        // cross-cohort pattern by an older local mosaic.  Persist the exact
        // physical successor and emit its sparse neuronal deltas here.  A
        // later cross-cohort formation law may consume that evidence, but this
        // physical-specialization sprint does not invent one.
        let settlement = settle_reached_cohort_interval(
            &cohorts[cohort_index].anatomy,
            &cohorts[cohort_index].state,
            input,
        )
        .map_err(FormationError::PhysicalSettlementUnavailable)?;
        cohorts[cohort_index].state = settlement.successor;
        for (neuron_index, (predecessor, successor)) in predecessor_neurons
            .iter()
            .zip(cohorts[cohort_index].state.neurons())
            .enumerate()
        {
            if predecessor != successor {
                let lineage = cohorts[cohort_index].anatomy.neuron_lineages()[neuron_index];
                if !physically_transitioned_neuron_lineages.contains(&lineage) {
                    physically_transitioned_neuron_lineages.push(lineage);
                }
            }
            if let Some(delta) = sparse_retained_physical_state_delta(predecessor, successor)
                .map_err(|error| {
                    FormationError::PhysicalSettlementUnavailable(ReachedCohortError::Neuron {
                        neuron_index,
                        error,
                    })
                })?
            {
                emitted_neuron_fractals.push(EmittedNeuronFractal {
                    neuron_lineage: cohorts[cohort_index].anatomy.neuron_lineages()[neuron_index],
                    delta,
                });
            }
        }
    }
    let mut active_bonds = settled
        .transitions
        .iter()
        .zip(compact_bonds)
        .filter_map(|(transition, bond)| {
            (transition.outward_current_from_left_picoamperes.parts().0 != 0
                || transition.outward_elementary_charges_from_left != 0
                || transition.plastic_changed)
                .then_some(bond)
        })
        .collect::<Vec<_>>();
    active_bonds.sort_unstable();
    active_bonds.dedup();
    // One shared full-field occurrence was evaluated for the entire reached
    // contact frontier, irrespective of how many neurons received their
    // coordinate-local perspectives.
    Ok(InternalContactSettlementObservation {
        dsf_delivery_count: 1,
        active_bonds,
    })
}

fn exact_rational_binary64(value: ExactRational) -> Result<f64, FormationError> {
    let (numerator, denominator) = value.parts();
    let numerator = numerator
        .to_f64()
        .filter(|value| value.is_finite())
        .ok_or(FormationError::ArithmeticOverflow)?;
    let denominator = denominator
        .to_f64()
        .filter(|value| value.is_finite() && *value > 0.0)
        .ok_or(FormationError::ArithmeticOverflow)?;
    let value = numerator / denominator;
    value
        .is_finite()
        .then_some(value)
        .ok_or(FormationError::ArithmeticOverflow)
}

fn contact_components(neuron_count: usize, anatomy: &SparseElectricalAnatomy) -> Vec<Vec<usize>> {
    let mut visited = vec![false; neuron_count];
    let endpoints = anatomy.contact_endpoints().collect::<Vec<_>>();
    let mut groups = Vec::new();
    for start in 0..neuron_count {
        if visited[start] {
            continue;
        }
        visited[start] = true;
        let mut group = vec![start];
        let mut cursor = 0usize;
        while cursor < group.len() {
            let member = group[cursor];
            for (left, right) in &endpoints {
                let neighbour = if *left == member {
                    Some(*right)
                } else if *right == member {
                    Some(*left)
                } else {
                    None
                };
                if let Some(neighbour) = neighbour {
                    if !visited[neighbour] {
                        visited[neighbour] = true;
                        group.push(neighbour);
                    }
                }
            }
            cursor += 1;
        }
        groups.push(group);
    }
    groups
}

fn encode_internal_contact_source(
    selected: &[usize],
    flat_locations: &[(usize, usize, [u8; 16])],
    predecessor_membranes: &[crate::elementary_charge_membrane::ElementaryChargeMembraneState],
    successor_membranes: &[crate::elementary_charge_membrane::ElementaryChargeMembraneState],
    capacitances: &[crate::elementary_charge_membrane::MembraneCapacitance],
    interval_microseconds: u32,
    electrical: &SparseElectricalAnatomy,
) -> Result<Vec<u8>, FormationError> {
    let mut encoded = Vec::new();
    encoded.extend_from_slice(b"GLINT01\0");
    encoded.extend_from_slice(&interval_microseconds.to_le_bytes());
    push_length(&mut encoded, selected.len())?;
    for (coordinate, flat) in selected.iter().copied().enumerate() {
        encoded.extend_from_slice(&flat_locations[flat].2);
        encoded.extend_from_slice(
            &predecessor_membranes[coordinate]
                .separated_elementary_charges()
                .to_le_bytes(),
        );
        encoded.extend_from_slice(
            &successor_membranes[coordinate]
                .separated_elementary_charges()
                .to_le_bytes(),
        );
        let (numerator, denominator) = capacitances[coordinate].picofarads().parts();
        encoded.extend_from_slice(&numerator.to_le_bytes());
        encoded.extend_from_slice(&denominator.to_le_bytes());
    }
    push_length(&mut encoded, electrical.contact_count())?;
    for contact in electrical.contact_anatomies() {
        let (left, right) = contact.endpoints();
        push_length(&mut encoded, left)?;
        push_length(&mut encoded, right)?;
        let (numerator, denominator) = contact.conductance_picosiemens().parts();
        encoded.extend_from_slice(&numerator.to_le_bytes());
        encoded.extend_from_slice(&denominator.to_le_bytes());
    }
    Ok(encoded)
}

fn resolve_lineage_for_port(
    cohorts: &[ResidentReachedCohort],
    dormant: &[DormantLineageSeed],
    port: &crate::joint_source_episode::JointSourcePortView,
) -> Result<Option<[u8; 16]>, FormationError> {
    let mut resolved = None;
    for cohort in cohorts {
        for (mount, lineage) in cohort
            .anatomy
            .mounts()
            .iter()
            .zip(cohort.anatomy.neuron_lineages())
        {
            let Some(site) = mount.source_site() else {
                continue;
            };
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
    let mut retained_sources = Vec::new();
    let mut reached_lineages = Vec::new();
    let mut reached_places = Vec::new();
    for cohort in &state.cohorts {
        for (mount, lineage) in cohort
            .anatomy
            .mounts()
            .iter()
            .zip(cohort.anatomy.neuron_lineages())
        {
            let place = mount.place();
            if lineage_ordinal(*lineage)? >= state.next_lineage_ordinal
                || reached_lineages.contains(lineage)
                || reached_places.contains(&place)
            {
                return Err(FormationError::NoncanonicalState);
            }
            reached_lineages.push(*lineage);
            reached_places.push(place);
            if let Some(site) = mount.source_site() {
                let seed = DormantLineageSeed::from_site(site, *lineage)?;
                if retained_sources.iter().any(|prior: &DormantLineageSeed| {
                    prior.same_source(&seed) || prior.neuron_lineage == seed.neuron_lineage
                }) {
                    return Err(FormationError::NoncanonicalState);
                }
                retained_sources.push(seed);
            }
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
            || reached_lineages.contains(&seed.neuron_lineage)
            || retained_sources
                .iter()
                .any(|prior| prior.same_source(seed) || prior.neuron_lineage == seed.neuron_lineage)
        {
            return Err(FormationError::NoncanonicalState);
        }
        retained_sources.push(seed.clone());
    }
    if state
        .electrical_fabric
        .lineages()
        .iter()
        .any(|lineage| !reached_lineages.contains(lineage))
    {
        return Err(FormationError::NoncanonicalState);
    }
    if let Some(population) = &state.resting_population {
        if population.lineage_end_exclusive() > state.next_lineage_ordinal
            || reached_lineages
                .iter()
                .zip(reached_places.iter())
                .any(|(lineage, place)| {
                    let Ok(ordinal) = lineage_ordinal(*lineage) else {
                        return true;
                    };
                    if ordinal < population.lineage_start_ordinal()
                        || ordinal >= population.lineage_end_exclusive()
                    {
                        return false;
                    }
                    population.materialized_lineage_ordinal(*place) != Some(ordinal)
                })
        {
            return Err(FormationError::NoncanonicalState);
        }
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

fn exact_optical_receptor_anatomy(
    aperture_population: u128,
) -> Result<OpticalReceptorAnatomy, FormationError> {
    if aperture_population == 0 {
        return Err(FormationError::NoncanonicalState);
    }
    OpticalReceptorAnatomy::new(
        BigRational::from_integer(BigInt::from(4)),
        BigRational::from_integer(BigInt::from(aperture_population)),
        BigRational::new(BigInt::from(1), BigInt::from(2)),
        BigRational::from_integer(BigInt::from(1)),
    )
    .map_err(FormationError::OpticalWorkUnavailable)
}

/// Auditory transduction anatomy, pinned by OPTICAL PARITY (Law A5,
/// `docs/GUALA_AUDITORY_TRANSDUCTION_DESIGN_2026-08-06.md` §4.3).
///
/// Nothing in this organism's pipeline measures pascals — the samples are
/// normalized to their own capture's full scale — so the declared reference
/// pressure is not a measurement of the world, it is the declaration of the
/// organism's full-scale sensitivity.  Pinning it by optical parity makes
/// full-scale sound exactly as energetic to this body as full-scale light and
/// introduces NO number that is not already in the tree: these are literally
/// `exact_optical_receptor_anatomy`'s own four factors, whose product is the
/// composite constant K = 2 zJ per (dimensionless² · second).  Only the
/// product is a physical claim; the factorization is the optical one.
fn exact_auditory_receptor_anatomy() -> Result<AuditoryReceptorAnatomy, FormationError> {
    AuditoryReceptorAnatomy::new(
        BigRational::from_integer(BigInt::from(4)),
        BigRational::from_integer(BigInt::from(1)),
        BigRational::new(BigInt::from(1), BigInt::from(2)),
        BigRational::from_integer(BigInt::from(1)),
    )
    .map_err(FormationError::AuditoryWorkUnavailable)
}

/// Tactile transduction anatomy, pinned by OPTICAL PARITY (Law T5,
/// `tactile_receptor_work`).
///
/// Nothing in this organism's pipeline measures pascals or newtons — a contact
/// port carries the fraction of its own declared site area that the touched
/// object's footprint covers — so the declared reference contact stress is not
/// a measurement of the world, it is the declaration of the organism's
/// full-scale sensitivity.  Pinning it by optical parity makes FULL CONTACT
/// exactly as energetic to this body as full-scale light and introduces NO
/// number that is not already in the tree: these are literally
/// `exact_optical_receptor_anatomy`'s own four factors, whose product is the
/// composite constant K = 2 zJ per (dimensionless · second) — the same
/// factorization `exact_auditory_receptor_anatomy` already reuses.  Only the
/// product is a physical claim.
fn exact_tactile_receptor_anatomy() -> Result<TactileReceptorAnatomy, FormationError> {
    TactileReceptorAnatomy::new(
        BigRational::from_integer(BigInt::from(4)),
        BigRational::from_integer(BigInt::from(1)),
        BigRational::new(BigInt::from(1), BigInt::from(2)),
        BigRational::from_integer(BigInt::from(1)),
    )
    .map_err(FormationError::TactileWorkUnavailable)
}

/// Which mounted receptor law governs one occurrence.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) enum ReceptorLaw {
    Sight,
    Sound,
    Touch,
}

fn receptor_law_for_reached_coordinates(
    reached_sources: &[(
        NeuronSourceSite,
        &crate::joint_source_episode::JointSourcePortView,
    )],
    coordinate_indices: &[usize],
) -> Option<ReceptorLaw> {
    let ports = coordinate_indices
        .iter()
        .filter_map(|index| reached_sources.get(*index).map(|(_, port)| *port))
        .collect::<Vec<_>>();
    if ports.len() != coordinate_indices.len() {
        return None;
    }
    receptor_law_for_ports(&ports)
}

fn exact_duration_microseconds(duration_seconds: &BigRational) -> Result<u32, FormationError> {
    if duration_seconds <= &BigRational::zero() {
        return Err(FormationError::NoncanonicalState);
    }
    let microseconds = duration_seconds * BigInt::from(1_000_000_u32);
    if !microseconds.is_integer() {
        return Err(FormationError::NoncanonicalState);
    }
    microseconds
        .to_integer()
        .to_u32()
        .filter(|value| *value > 0)
        .ok_or(FormationError::ArithmeticOverflow)
}

fn receptor_law_for_ports(
    ports: &[&crate::joint_source_episode::JointSourcePortView],
) -> Option<ReceptorLaw> {
    if ports.is_empty() {
        return None;
    }
    let all_ports = |predicate: fn(&crate::joint_source_episode::JointSourcePortView) -> bool| {
        ports.iter().all(|port| predicate(port))
    };
    if all_ports(|port| {
        port.sense == 0
            && port.physical_quantity == RETINAL_SPECTRAL_IRRADIANCE_QUANTITY
            && port.physical_unit == RETINAL_REFERENCE_IRRADIANCE_UNIT
    }) {
        return Some(ReceptorLaw::Sight);
    }
    if all_ports(|port| {
        port.sense == 1
            && port.physical_quantity == COCHLEAR_BAND_PRESSURE_QUANTITY
            && port.physical_unit == COCHLEAR_REFERENCE_PRESSURE_UNIT
    }) {
        return Some(ReceptorLaw::Sound);
    }
    if all_ports(|port| {
        port.sense == PhysicalSourceSense::Touch.declared_layer()
            && port.physical_quantity == CONTACT_SITE_OCCUPANCY_QUANTITY
            && port.physical_unit == CONTACT_REFERENCE_OCCUPANCY_UNIT
    }) {
        return Some(ReceptorLaw::Touch);
    }
    None
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) enum FormationError {
    BudgetExceeded {
        required: usize,
        available: usize,
    },
    ArithmeticOverflow,
    InvalidSourceGeneration,
    SourceOccurrenceAbsent,
    JointFieldUnavailable(JointNeuronBoundaryError),
    PhysicalGenesisUnavailable(VirtualMaterialGenesisError),
    VestibularUnavailable(FunctionalVestibularError),
    DevelopmentalElectricalUnavailable(DevelopmentalElectricalError),
    DevelopmentalRestingPopulationUnavailable(DevelopmentalRestingPopulationError),
    OpticalWorkUnavailable(OpticalReceptorWorkError),
    AuditoryWorkUnavailable(AuditoryReceptorWorkError),
    TactileWorkUnavailable(TactileReceptorWorkError),
    PhysicalSettlementUnavailable(ReachedCohortError),
    ResidentElectricalUnavailable(SparseElectricalError),
    InternalMembraneUnavailable(MembraneChargeError),
    PhysicalMosaicUnavailable(PhysicalMosaicError),
    PhysicalMosaicCodecUnavailable(PhysicalMosaicCodecError),
    /// The body truthfully refused an intake: it can absorb nothing, or the
    /// declaration carried no energy at all.
    NutritionUnavailable(MetabolicError),
    /// An authored contact could not be resolved against exactly two members
    /// of exactly one living cohort, or none was authored at all.  Naming a
    /// connection the organism does not have is refused, never inferred.
    AuthoredContactUnavailable,
    NeuronLineageAuthorityAbsent,
    NeuronLineageAuthorityChanged,
    /// The retired archive checkpoint (`GLHST01`) failed to encode or decode.
    /// This is a persisted-layout fault, never an archive availability fault:
    /// nothing reads cold custody any more.
    HippocampalCheckpointUnavailable(HippocampalError),
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
            Self::DevelopmentalRestingPopulationUnavailable(error) => write!(
                output,
                "developmental resting population is unavailable: {error:?}"
            ),
            Self::OpticalWorkUnavailable(error) => {
                write!(output, "exact optical receptor work is unavailable: {error:?}")
            }
            Self::AuditoryWorkUnavailable(error) => {
                write!(output, "exact auditory receptor work is unavailable: {error:?}")
            }
            Self::TactileWorkUnavailable(error) => {
                write!(output, "exact tactile receptor work is unavailable: {error:?}")
            }
            Self::PhysicalSettlementUnavailable(error) => {
                write!(output, "resident physical neuron settlement is unavailable: {error:?}")
            }
            Self::ResidentElectricalUnavailable(error) => {
                write!(output, "resident sparse electrical fabric is unavailable: {error:?}")
            }
            Self::InternalMembraneUnavailable(error) => {
                write!(output, "internal membrane occurrence is unavailable: {error:?}")
            }
            Self::PhysicalMosaicUnavailable(error) => {
                write!(output, "physical mosaic admission is unavailable: {error:?}")
            }
            Self::PhysicalMosaicCodecUnavailable(error) => {
                write!(output, "physical mosaic persistence is unavailable: {error:?}")
            }
            Self::NutritionUnavailable(error) => {
                write!(output, "the body refuses this nutrition intake: {error:?}")
            }
            Self::AuthoredContactUnavailable => write!(
                output,
                "an authored contact does not name exactly two members of one living cohort"
            ),
            Self::NeuronLineageAuthorityAbsent => {
                write!(output, "resident neuron lineage authority is absent")
            }
            Self::NeuronLineageAuthorityChanged => {
                write!(output, "resident neuron lineage authority changed")
            }
            Self::HippocampalCheckpointUnavailable(error) => write!(
                output,
                "the retired hippocampal checkpoint field is malformed: {error:?}"
            ),
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
mod real_body_migration_probe;

#[cfg(test)]
mod tests {
    use super::*;

    /// Quiet (dark, silent) episodes appended after a presentation so the
    /// cohort can descend all the way to electrical rest.  Since the
    /// 2026-08-05 geometric differentiation the members' capacitances differ,
    /// so a settled cohort equalizes POTENTIAL rather than charge and takes
    /// longer to go silent than the tie-frozen anatomy did; the tail is
    /// transport, the quiescence is physics.
    const DARK_TAIL_EPISODES: usize = 64;
    use crate::developmental_electrical_anatomy::{
        DevelopmentalElectricalContact, DevelopmentalElectricalSeed,
    };
    use crate::exact_rational::ExactRational;
    use crate::local_cupula_hair_bundle_geometry::LocalCupulaBundleAnatomy;
    use crate::neuron_source_anchor::tests::{
        exact_dark_optical_episode, exact_episode, exact_five_optical_episode,
        exact_four_dark_optical_episode, exact_four_partial_optical_episode,
        exact_four_reordered_optical_episode, exact_four_single_optical_episode,
        exact_optical_binaural_episode, exact_optical_episode, exact_split_four_optical_episode,
        exact_two_of_four_optical_episode,
    };
    use crate::reached_vestibular_bundle_path::settle_reached_vestibular_bundle_tick;
    use crate::resident_receptor_transition::prepare_resident_vestibular_ingress;
    use crate::vestibular_neuron_path::phase_one_virtual_vestibular_anatomy;
    use crate::virtual_body_yaw_motion::{
        settle_signed_yaw_actuation, SignedYawActuation, YawBodyState,
    };
    use crate::virtual_vestibular_canal::{CanalAnatomy, CanalState, PositiveRatio};

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

    fn local_lineage(ordinal: u64) -> [u8; 16] {
        let mut lineage = [0; 16];
        lineage[..8].copy_from_slice(LINEAGE_DOMAIN);
        lineage[8..].copy_from_slice(&ordinal.to_be_bytes());
        lineage
    }

    #[test]
    fn empty_genesis_is_exact_and_bounded() {
        let state = ResidentCognitiveFormationState::default();
        let encoded = state.encode(CURRENT_FIXED_BYTES).unwrap();
        assert_eq!(encoded.len(), CURRENT_FIXED_BYTES);
        assert_eq!(
            ResidentCognitiveFormationState::decode(&encoded, CURRENT_FIXED_BYTES).unwrap(),
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
        assert_eq!(prepared.successor.next_lineage_ordinal, 9);
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
        assert_eq!(prepared.observation.dsf_delivery_count, 2);
        assert_eq!(prepared.successor.summary().complete_neuron_count, 2);
        assert_eq!(prepared.successor.cohorts.len(), 2);
        assert_eq!(prepared.successor.next_lineage_ordinal, 3);
        assert_eq!(
            prepared.successor.cohorts[0].anatomy.neuron_lineages(),
            &[local_lineage(1)]
        );
        let encoded = state.encode_successor(&prepared, 16_000_000).unwrap();
        let cold = ResidentCognitiveFormationState::decode(&encoded, 16_000_000).unwrap();
        assert_eq!(cold.encode(16_000_000).unwrap(), encoded);
        let recurrent = cold.prepare(&source, 16_000_000).unwrap();
        assert_eq!(recurrent.successor.next_lineage_ordinal, 3);
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
        assert_eq!(original_lineages.len(), 8);

        let prepared = state.prepare(&reordered, 16_000_000).unwrap();
        assert_eq!(prepared.successor.cohorts.len(), 5);
        assert_eq!(prepared.successor.summary().complete_neuron_count, 8);
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
    fn subset_occurrence_advances_receptors_and_still_charged_internal_material() {
        let first = crate::neuron_source_anchor::tests::exact_four_optical_episode();
        let subset = exact_two_of_four_optical_episode();
        let mut state = ResidentCognitiveFormationState::default();
        state
            .commit(state.prepare(&first, 16_000_000).unwrap())
            .unwrap();
        let predecessor = state.cohorts[0].state.clone();
        let lineages = state.retained_neuron_lineages();

        let prepared = state.prepare(&subset, 16_000_000).unwrap();
        assert_eq!(prepared.successor.cohorts.len(), 5);
        assert_eq!(prepared.successor.summary().complete_neuron_count, 8);
        assert_eq!(prepared.successor.retained_neuron_lineages(), lineages);
        let successor = &prepared.successor.cohorts[0].state;
        // Receptors 2 and 3 receive no new external gate work, but their
        // retained physical charge from the preceding occurrence remains an
        // authentic seed. Continuous neuronal settlement therefore advances
        // them without relabelling that motion as new sensory input.
        assert_ne!(successor.neurons()[2], predecessor.neurons()[2]);
        assert_ne!(successor.neurons()[3], predecessor.neurons()[3]);
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
        assert_eq!(warm.successor.cohorts.len(), 6);
        assert_eq!(warm.successor.summary().complete_neuron_count, 10);
        assert_eq!(warm.successor.next_lineage_ordinal, 11);
        assert_eq!(
            &warm.successor.cohorts[0].anatomy.neuron_anatomies()[..4],
            predecessor_anatomy.neuron_anatomies()
        );
        assert_eq!(
            warm.successor.cohorts[0]
                .anatomy
                .source_sites()
                .take(4)
                .collect::<Vec<_>>(),
            predecessor_anatomy.source_sites().collect::<Vec<_>>()
        );
        assert!(predecessor_lineages
            .iter()
            .all(|lineage| warm.successor.retained_neuron_lineages().contains(lineage)));
        assert!(warm
            .successor
            .retained_neuron_lineages()
            .contains(&local_lineage(9)));
        assert!(warm
            .successor
            .retained_neuron_lineages()
            .contains(&local_lineage(10)));
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
        assert_eq!(state.cohorts.len(), 6);
        assert_eq!(state.summary().complete_neuron_count, 8);
        assert_eq!(state.next_lineage_ordinal, 9);
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
        assert_eq!(warm.successor.cohorts.len(), 6);
        assert_eq!(warm.successor.summary().complete_neuron_count, 8);
        assert_eq!(warm.successor.next_lineage_ordinal, 9);
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
        assert_eq!(restored.cohorts.len(), 6);
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
    fn unsupported_ports_do_not_cancel_a_supported_receptor_or_claim_extra_neurons() {
        let source = exact_episode();
        let mut state = ResidentCognitiveFormationState::default();
        let prepared = state.prepare(&source, 16_000_000).unwrap();
        assert_eq!(prepared.observation.cognitive_ordinal, 1);
        assert_eq!(prepared.observation.complete_neuron_count, 2);
        assert_eq!(prepared.observation.physically_transitioned_neuron_count, 2);
        assert_eq!(prepared.observation.complete_neuron_fractal_count, 3);
        assert!(!prepared.observation.trace_formed);
        assert!(prepared.observation.mosaic_formed.is_none());
        state.commit(prepared).unwrap();
        let encoded = state.encode(16_000_000).unwrap();
        let restored = ResidentCognitiveFormationState::decode(&encoded, 16_000_000).unwrap();
        assert_eq!(restored, state);
        assert_eq!(restored.summary().complete_neuron_count, 2);
        assert_eq!(restored.next_lineage_ordinal, 3);
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
        assert_eq!(prepared.successor.cohorts.len(), 5);
        assert_eq!(prepared.successor.summary().complete_neuron_count, 8);
        assert_eq!(prepared.successor.cohorts[0].anatomy.neuron_count(), 4);
        assert_eq!(prepared.successor.cohorts[0].anatomy.contact_count(), 3);
        assert_eq!(prepared.observation.complete_neuron_fractal_count, 9);
        assert!(prepared.observation.mosaic_formed.is_none());

        let expressed = restored.encode_successor(&prepared, 16_000_000).unwrap();
        let cold = ResidentCognitiveFormationState::decode(&expressed, 16_000_000).unwrap();
        assert_eq!(cold, prepared.successor);
        assert_eq!(cold.cohorts[0].anatomy.contact_count(), 3);
        assert_eq!(cold.encode(16_000_000).unwrap(), expressed);
    }

    /// Contact growth on a LIVING body that already holds a retained
    /// formation: append-only, nothing about the members moves, the retained
    /// formation is untouched, and the grown body cold-restores bit-exactly.
    #[test]
    #[ignore = "retired: fixture requires Boolean/member-set mosaic admission"]
    fn authored_contact_growth_appends_without_disturbing_a_living_body() {
        let light = (0..4)
            .map(exact_four_single_optical_episode)
            .collect::<Vec<_>>();
        let dark = exact_four_dark_optical_episode();
        let seed = explicit_optical_seed(&light[0], 500);
        let mut state =
            ResidentCognitiveFormationState::from_developmental_electrical_seeds(vec![seed])
                .unwrap();
        // First settle the complete experience, then present one proper
        // partial cue and its causal dark tail. A second complete presentation
        // is not a partial-cue reassembly and cannot be used to manufacture a
        // mosaic merely for this contact-growth test.
        for source in light
            .iter()
            .chain(std::iter::repeat(&dark).take(DARK_TAIL_EPISODES))
        {
            let prepared = state
                .prepare_admitted_transition(&admitted_fixture_episode(source), 16_000_000)
                .unwrap();
            state.commit(prepared).unwrap();
        }
        let partial = exact_four_partial_optical_episode();
        for source in
            std::iter::once(&partial).chain(std::iter::repeat(&dark).take(DARK_TAIL_EPISODES))
        {
            let prepared = state
                .prepare_admitted_transition(&admitted_fixture_episode(source), 16_000_000)
                .unwrap();
            state.commit(prepared).unwrap();
        }
        assert_eq!(state.summary().mosaic_count, 1);
        let before_bytes = state.encode(16_000_000).unwrap();
        let before_mosaics = state.mosaics.clone();
        let before_neurons = state.cohorts[0].state.neurons().to_vec();
        let before_contacts = state.cohorts[0]
            .anatomy
            .contact_endpoints()
            .collect::<Vec<_>>();
        let before_phases = state.cohorts[0]
            .state
            .electrical()
            .contact_states()
            .to_vec();
        assert_eq!(before_contacts.len(), 3);

        let authored = vec![AuthoredDeclaredContact {
            left_sensor_id: "left-retina".to_owned(),
            left_substream_id: "foveal-receptor-0".to_owned(),
            right_sensor_id: "left-retina".to_owned(),
            right_substream_id: "foveal-receptor-3".to_owned(),
            conductance_picosiemens: ExactRational::integer(500),
        }];
        let grown = state
            .prepare_authored_contacts(&authored, 16_000_000)
            .unwrap();
        // Preparing publishes nothing.
        assert_eq!(state.encode(16_000_000).unwrap(), before_bytes);
        let grown_bytes = state.encode_successor(&grown, 16_000_000).unwrap();
        state.commit(grown).unwrap();

        let after_contacts = state.cohorts[0]
            .anatomy
            .contact_endpoints()
            .collect::<Vec<_>>();
        assert_eq!(after_contacts.len(), 4);
        assert_eq!(after_contacts[..3], before_contacts[..]);
        assert_eq!(after_contacts[3], (0, 3));
        assert_eq!(
            state.cohorts[0].state.electrical().contact_states()[..3],
            before_phases[..]
        );
        // Members, their physical states and the retained formation are all
        // exactly as they were: only the contact list grew.
        assert_eq!(state.cohorts[0].state.neurons(), before_neurons.as_slice());
        assert_eq!(state.cohorts[0].anatomy.neuron_count(), 4);
        assert_eq!(state.mosaics, before_mosaics);
        assert_eq!(state.summary().mosaic_count, 1);
        assert_eq!(state.observe_cohort_contacts(), vec![(4, 4)]);

        // Cold restart of the grown body is bit-exact and re-encodes identically.
        let restored = ResidentCognitiveFormationState::decode(&grown_bytes, 16_000_000).unwrap();
        assert_eq!(restored, state);
        assert_eq!(restored.encode(16_000_000).unwrap(), grown_bytes);
        // The pre-growth body still decodes to exactly what it was: no
        // receipt of any earlier generation drifted.
        let pre_growth =
            ResidentCognitiveFormationState::decode(&before_bytes, 16_000_000).unwrap();
        assert_eq!(pre_growth.encode(16_000_000).unwrap(), before_bytes);
        assert_eq!(pre_growth.observe_cohort_contacts(), vec![(4, 3)]);

        // Re-running the same authorship is refused, not silently doubled.
        assert!(matches!(
            state.prepare_authored_contacts(&authored, 16_000_000),
            Err(FormationError::PhysicalSettlementUnavailable(
                ReachedCohortError::Electrical(
                    crate::sparse_electrical_contact::SparseElectricalError::ContactAlreadyAuthored
                )
            ))
        ));
        // A receptor this organism does not declare cannot be contacted.
        let absent = vec![AuthoredDeclaredContact {
            left_sensor_id: "left-retina".to_owned(),
            left_substream_id: "foveal-receptor-0".to_owned(),
            right_sensor_id: "left-retina".to_owned(),
            right_substream_id: "foveal-receptor-9".to_owned(),
            conductance_picosiemens: ExactRational::integer(500),
        }];
        assert_eq!(
            state.prepare_authored_contacts(&absent, 16_000_000),
            Err(FormationError::AuthoredContactUnavailable)
        );
        assert_eq!(
            state.prepare_authored_contacts(&[], 16_000_000),
            Err(FormationError::AuthoredContactUnavailable)
        );
        // Every refusal left the body exactly as the growth left it.
        assert_eq!(state.encode(16_000_000).unwrap(), grown_bytes);
    }

    #[cfg(any())]
    #[test]
    fn feeding_metabolism_sustains_lessons_across_a_feed_and_rest_cycle() {
        // Served-path proof of the minimal feeding metabolism (authorized
        // 2026-08-05) on a fresh organism.  MEASURED on this four-receptor
        // body: the rest metabolism holds every dissipation ledger at zero
        // for as long as the reservoir can pay, the reservoir is a closed
        // fuel/spent pool, one lit lesson costs 376 quanta of a 2,164-quantum
        // pool, and one authored feed of the body's whole spent load restores
        // it exactly and vents its heat.
        //
        // COST RE-MEASURED 2026-08-06: 376, not the ~312 this comment carried.
        // It was stale BEFORE the exact rest-cost law of the same date and was
        // NOT moved by it — the first lesson costs 376 under both the old
        // ceil-and-discard billing and the exact carried-residue billing, and
        // the exhaustion count below is 7 under both.  On this four-receptor
        // body the lit lesson's cost is the recovery lanes undoing gate work,
        // not the membrane return; the return's overcharge only dominates on a
        // body doing more returning than seeing (measured on the LIVING body:
        // 200 dark intervals cost 1,849 fuel quanta under the old law and 28
        // under the exact one, for exactly the same 1,849 charges returned).
        let light = (0..4)
            .map(exact_four_single_optical_episode)
            .collect::<Vec<_>>();
        let dark = exact_four_dark_optical_episode();
        let seed = explicit_optical_seed(&light[0], 500);
        let mut state =
            ResidentCognitiveFormationState::from_developmental_electrical_seeds(vec![seed])
                .unwrap();
        let mut teach = |state: &mut ResidentCognitiveFormationState| {
            for source in light.iter().chain(std::iter::repeat(&dark).take(8)) {
                let prepared = state
                    .prepare_admitted_transition(&admitted_fixture_episode(source), 16_000_000)
                    .unwrap();
                state.commit(prepared).unwrap();
            }
            state.energy_state()
        };

        let mut lessons_before_exhaustion = 0usize;
        let mut energy = teach(&mut state);
        loop {
            lessons_before_exhaustion += 1;
            // Material conservation: the reservoir is a closed fuel/spent pool.
            assert_eq!(
                energy.fuel_quanta + energy.spent_quanta,
                energy.fuel_capacity_quanta
            );
            // Every quantum of fuel burnt appears as one spent quantum AND one
            // heat quantum, because every burn drained a dissipation ledger or
            // paid for a membrane return.
            assert_eq!(energy.heat_quanta, energy.spent_quanta);
            if energy.fuel_quanta == 0 {
                break;
            }
            // Rest recovery keeps every dissipation ledger empty for as long as
            // the body can pay: the old monotone gate ratchet is closed.
            assert_eq!(energy.dissipated_quanta, 0);
            assert!(
                lessons_before_exhaustion < 40,
                "lessons never exhausted fuel"
            );
            energy = teach(&mut state);
        }
        // The exact exhaustion count changes when the neuron's physically
        // mounted positional fabric changes. What this test requires is the
        // law: the finite body eventually exhausts, never exceeds its own
        // capacity, and can regenerate exactly from its reported spent
        // material. No historical lesson count governs that physics.
        assert!(lessons_before_exhaustion > 0);
        assert!(energy.dissipated_quanta > 0);
        let exhausted_spent = energy.spent_quanta;

        // Feeding a body that cannot absorb is refused honestly.
        let mut sated = state.clone();
        let fed = sated
            .prepare_nutrition(
                AuthoredNutritionDeclaration::new(exhausted_spent).unwrap(),
                16_000_000,
            )
            .unwrap();
        assert_eq!(
            fed.observation.nutrition_regenerated_fuel_quanta,
            exhausted_spent
        );
        assert_eq!(fed.observation.nutrition_unabsorbed_waste_quanta, 0);
        assert_eq!(
            fed.observation.nutrition_vented_heat_quanta,
            exhausted_spent
        );
        sated.commit(fed).unwrap();
        let after_feed = sated.energy_state();
        assert_eq!(after_feed.fuel_quanta, after_feed.fuel_capacity_quanta);
        assert_eq!(after_feed.spent_quanta, 0);
        assert_eq!(after_feed.heat_quanta, 0);
        assert!(matches!(
            sated.prepare_nutrition(AuthoredNutritionDeclaration::new(1).unwrap(), 16_000_000,),
            Err(FormationError::NutritionUnavailable(
                MetabolicError::NothingToRegenerate
            ))
        ));

        // Over-feeding an absorbing body exports the excess as waste rather
        // than inventing capacity.
        let mut overfed = state.clone();
        let excess = exhausted_spent + 1_000;
        let prepared = overfed
            .prepare_nutrition(
                AuthoredNutritionDeclaration::new(excess).unwrap(),
                16_000_000,
            )
            .unwrap();
        assert_eq!(
            prepared.observation.nutrition_regenerated_fuel_quanta
                + prepared.observation.nutrition_unabsorbed_waste_quanta,
            excess
        );
        assert_eq!(
            prepared.observation.nutrition_unabsorbed_waste_quanta,
            1_000
        );

        // The fed body learns again: the cycle is sustainable, not a one-shot.
        let mut lessons_after_feed = 1usize;
        let mut energy = teach(&mut sated);
        while energy.fuel_quanta > 0 {
            lessons_after_feed += 1;
            assert_eq!(energy.dissipated_quanta, 0);
            assert_eq!(
                energy.fuel_quanta + energy.spent_quanta,
                energy.fuel_capacity_quanta
            );
            assert!(lessons_after_feed < 40, "fed body never exhausted fuel");
            energy = teach(&mut sated);
        }
        assert_eq!(lessons_after_feed, lessons_before_exhaustion);
    }

    #[cfg(any())]
    #[test]
    #[ignore = "retired: fixture requires Boolean/member-set mosaic admission"]
    fn four_receptor_experience_selectively_emits_four_real_fractals() {
        let light = (0..4)
            .map(exact_four_single_optical_episode)
            .collect::<Vec<_>>();
        let dark = exact_four_dark_optical_episode();
        let seed = explicit_optical_seed(&light[0], 500);
        let mut state =
            ResidentCognitiveFormationState::from_developmental_electrical_seeds(vec![seed])
                .unwrap();
        let mut emitted = Vec::new();
        for source in light
            .iter()
            .chain(std::iter::repeat(&dark).take(DARK_TAIL_EPISODES))
        {
            let prepared = state.prepare(source, 16_000_000).unwrap();
            assert!(prepared.observation.mosaic_formed.is_none());
            assert_eq!(prepared.observation.mosaic_count, 0);
            emitted.extend(prepared.observation.emitted_neuron_fractals.clone());
            state.commit(prepared).unwrap();
        }
        let mut emitted_lineages = emitted
            .iter()
            .map(|fractal| fractal.neuron_lineage)
            .collect::<Vec<_>>();
        emitted_lineages.sort();
        emitted_lineages.dedup();
        assert_eq!(
            emitted_lineages,
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
            .chain(std::iter::repeat(&dark).take(DARK_TAIL_EPISODES))
            .collect::<Vec<_>>();
        let recurrence_fields = recurrence_sources
            .iter()
            .map(|source| prepare_complete_joint_field_admitted_fixture(source, 0).unwrap())
            .collect::<Vec<_>>();
        assert_eq!(restored.summary().mosaic_count, 0);
        let mut integrated = restored.clone();
        let checkpoint_before_recurrences = restored.hippocampal;
        let mut formed = Vec::new();
        RESIDENT_ACTUAL_RECURRENCE_SETTLEMENTS.with(|count| count.set(0));
        for source in &recurrence_sources {
            let prepared = integrated
                .prepare_admitted_transition(&admitted_fixture_episode(source), 16_000_000)
                .unwrap();
            if let Some(receipt) = prepared.observation.mosaic_formed {
                assert_eq!(prepared.observation.mosaic_count, 1);
                assert!(prepared.observation.activations.is_empty());
                assert_eq!(prepared.observation.partial_cue_reassembly_count(), 1);
                // The receipt of a newly formed mosaic is the sha256 of the
                // mosaic's OWN encoded body, not an archive address: it must
                // be reproducible from her retained formation alone.
                assert_eq!(
                    receipt,
                    sha256(
                        &encode_organism_mosaic(
                            &prepared.successor.cohorts,
                            &prepared.successor.electrical_fabric,
                            &prepared.successor.mosaics[0].mosaic,
                            16_000_000,
                        )
                        .unwrap()
                    )
                );
                formed.push(receipt);
            }
            // A recurrence commits with no publication step of any kind, and
            // the retired archive checkpoint does not move.
            assert_eq!(
                prepared.successor.hippocampal,
                checkpoint_before_recurrences
            );
            let interval_bytes = integrated.encode_successor(&prepared, 16_000_000).unwrap();
            integrated.commit(prepared).unwrap();
            integrated =
                ResidentCognitiveFormationState::decode(&interval_bytes, 16_000_000).unwrap();
            assert_eq!(integrated.encode(16_000_000).unwrap(), interval_bytes);
        }
        RESIDENT_ACTUAL_RECURRENCE_SETTLEMENTS.with(|count| {
            let available_gates = recurrence_fields
                .iter()
                .map(|field| field.result().gates.len())
                .sum::<usize>();
            // Candidate recurrence ends at physical mosaic admission. Later
            // dark gates return to ordinary living settlement; they must not
            // remain trapped in the just-completed candidate path.
            assert!(count.get() > 0);
            assert!(count.get() < available_gates);
        });
        assert_eq!(formed.len(), 1);
        assert_eq!(integrated.summary().mosaic_count, 1);
        assert_eq!(integrated.mosaics.len(), 1);
        assert!(integrated.cohorts[0].pending_recurrence.is_none());
        let integrated_bytes = integrated.encode(16_000_000).unwrap();
        let cold_integrated =
            ResidentCognitiveFormationState::decode(&integrated_bytes, 16_000_000).unwrap();
        assert_eq!(cold_integrated, integrated);
        // A full learn-and-recognize cycle left the retired checkpoint exactly
        // where it started: no episode, no posting, no radix path copy, no
        // address of any kind was produced by admitting a real mosaic.
        assert_eq!(cold_integrated.hippocampal, checkpoint_before_recurrences);
        assert!(!cold_integrated
            .hippocampal
            .carries_retired_archive_reference());

        let five_receptor_occurrence = exact_five_optical_episode();
        let predecessor_anatomy = integrated.cohorts[0].anatomy.clone();
        let predecessor_lineages = integrated.retained_neuron_lineages();
        let predecessor_mosaics = integrated.mosaics.clone();
        RESIDENT_JOINT_FIELD_EVALUATIONS.with(|count| count.set(0));
        let warm_growth = integrated
            .prepare_admitted_transition(
                &admitted_fixture_episode(&five_receptor_occurrence),
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
            .prepare_admitted_transition(
                &admitted_fixture_episode(&five_receptor_occurrence),
                16_000_000,
            )
            .unwrap();
        assert_eq!(cold_growth, warm_growth);
        assert_eq!(warm_growth.successor.cohorts.len(), 1);
        assert_eq!(warm_growth.successor.summary().complete_neuron_count, 5);
        assert_eq!(warm_growth.successor.next_lineage_ordinal, 6);
        for (successor, predecessor) in warm_growth.successor.cohorts[0]
            .anatomy
            .neuron_anatomies()
            .iter()
            .zip(predecessor_anatomy.neuron_anatomies())
        {
            assert_eq!(successor.capacitance(), predecessor.capacitance());
            assert!(successor.mathloom_positions() >= predecessor.mathloom_positions());
        }
        assert_eq!(
            &warm_growth.successor.cohorts[0].anatomy.source_sites()[..4],
            predecessor_anatomy.source_sites()
        );
        assert_eq!(
            &warm_growth.successor.cohorts[0].anatomy.neuron_lineages()[..4],
            predecessor_lineages
        );
        assert_eq!(
            warm_growth.successor.cohorts[0].anatomy.neuron_lineages()[4],
            local_lineage(5)
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
        let extended_bytes = extended.encode_successor(&warm_growth, 16_000_000).unwrap();
        extended.commit(warm_growth).unwrap();
        let cold_extended =
            ResidentCognitiveFormationState::decode(&extended_bytes, 16_000_000).unwrap();
        assert_eq!(cold_extended, extended);
        assert_eq!(cold_extended.encode(16_000_000).unwrap(), extended_bytes);
        assert_eq!(cold_extended.summary().complete_neuron_count, 5);
        assert_eq!(cold_extended.summary().mosaic_count, 1);
        assert_eq!(cold_extended.hippocampal, checkpoint_before_recurrences);

        // The first learn-and-recognize cycle used the body's finite recovery
        // reservoir completely.  An unfed control therefore cannot drive a
        // second whole-formation recurrence: exhausted material is a physical
        // unavailability, not a recall defect to bypass with a controller.
        assert_eq!(integrated.energy_state().fuel_quanta, 0);
        let mut exhausted = integrated.clone();
        let later_cue = exact_four_single_optical_episode(1);
        let mut exhausted_reassemblies = 0usize;
        for source in
            std::iter::once(&later_cue).chain(std::iter::repeat(&dark).take(DARK_TAIL_EPISODES))
        {
            let prepared = exhausted
                .prepare_admitted_transition(&admitted_fixture_episode(source), 16_000_000)
                .unwrap();
            exhausted_reassemblies += prepared.observation.partial_cue_reassembly_count;
            exhausted.commit(prepared).unwrap();
        }
        // Incoming light carries its own physical energy. A metabolically
        // exhausted body may therefore still complete a bounded number of
        // already-yielded receptor transitions using free local dissipation
        // capacity; exhaustion must stop that sequence without a controller.
        assert!(exhausted_reassemblies > 0);
        let exhausted_checkpoint = exhausted.clone();
        let mut later_reassemblies = 0usize;
        for source in
            std::iter::once(&later_cue).chain(std::iter::repeat(&dark).take(DARK_TAIL_EPISODES))
        {
            let prepared = exhausted
                .prepare_admitted_transition(&admitted_fixture_episode(source), 16_000_000)
                .unwrap();
            later_reassemblies += prepared.observation.partial_cue_reassembly_count;
            exhausted.commit(prepared).unwrap();
        }
        assert_eq!(later_reassemblies, 0);
        assert_ne!(exhausted, exhausted_checkpoint);

        // Restore exactly the material the same body reports as spent, then
        // supply the declared dark causal intervals in which its existing
        // recovery physics can act.  No recall threshold, timeout, scheduler,
        // or semantic rule participates.  Recovery itself lawfully provides
        // an internal partial cue, and a later external partial cue also
        // reassembles the one retained distributed formation.
        let mut progressive = integrated.clone();
        let spent = progressive.energy_state().spent_quanta;
        let nutrition = progressive
            .prepare_nutrition(
                AuthoredNutritionDeclaration::new(spent).unwrap(),
                16_000_000,
            )
            .unwrap();
        assert_eq!(
            nutrition.observation.nutrition_regenerated_fuel_quanta,
            spent
        );
        progressive.commit(nutrition).unwrap();
        let mut reassembly_events = 0usize;
        let mut endogenous_reassembly_events = 0usize;
        for _ in 0..DARK_TAIL_EPISODES {
            let prepared = progressive
                .prepare_admitted_transition(&admitted_fixture_episode(&dark), 16_000_000)
                .unwrap();
            reassembly_events += prepared.observation.partial_cue_reassembly_count;
            endogenous_reassembly_events +=
                prepared.observation.endogenous_partial_cue_reassembly_count;
            progressive.commit(prepared).unwrap();
        }
        assert!(endogenous_reassembly_events > 0);
        let reassemblies_before_external_cue = reassembly_events;
        for source in
            std::iter::once(&later_cue).chain(std::iter::repeat(&dark).take(DARK_TAIL_EPISODES))
        {
            let prepared = progressive
                .prepare_admitted_transition(&admitted_fixture_episode(source), 16_000_000)
                .unwrap();
            reassembly_events += prepared.observation.partial_cue_reassembly_count;
            let successor = progressive.encode_successor(&prepared, 16_000_000).unwrap();
            progressive.commit(prepared).unwrap();
            progressive = ResidentCognitiveFormationState::decode(&successor, 16_000_000).unwrap();
        }
        assert!(reassembly_events > reassemblies_before_external_cue);
        assert_eq!(progressive.summary().mosaic_count, 1);
        assert_eq!(progressive.mosaics[0].mosaic_of_mosaics_relation_count, 0);
        assert_eq!(progressive.mosaic_of_mosaics_count().unwrap(), 0);
        assert_eq!(progressive.hippocampal, checkpoint_before_recurrences);

        // The five tamper assertions that stood here checked that a corrupted
        // ARCHIVED EPISODE RECORD failed to validate (damaged source body,
        // damaged mosaic body, trailing bytes on either evidence body, a
        // mismatched participant lineage).  They validated the record, not
        // Guala, and they left with the record.  What still guards her here is
        // the truncation assertion immediately below plus the round-trip law
        // in `decode`, which every restore runs on her real body.
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
            resting_population: None,
            cohorts: vec![ResidentReachedCohort {
                anatomy: restored.cohorts[0].anatomy.clone(),
                state: retained.pre_experience_rest.clone(),
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
    }

    fn structural_test_lineage(value: u8) -> [u8; 16] {
        let mut lineage = [0u8; 16];
        lineage[15] = value;
        lineage
    }

    /// Synthesize an admitted mosaic with explicit member and active-bond
    /// structure for the R1 boundary tests.  `members` must be strictly
    /// ascending; bonds are canonicalized exactly as admission does.
    fn synthetic_admitted_mosaic(
        members: &[u8],
        active_bonds: &[(u8, u8)],
        cue: u8,
    ) -> AdmittedPhysicalMosaic {
        let fractal =
            crate::complete_neuron::SparsePhysicalStateDelta::from_canonical_entries(vec![
                crate::complete_neuron::PhysicalStateDeltaEntry::new(
                    crate::complete_neuron::PhysicalStateCoordinate::PlasticRestLength,
                    crate::complete_neuron::ExactPhysicalStateDelta::Rational(
                        crate::exact_rational::ExactRational::new(1, 3).unwrap(),
                    ),
                )
                .unwrap(),
            ])
            .unwrap();
        let bond = |left: u8, right: u8| {
            crate::physical_mosaic::StablePhysicalBondReference::new(
                structural_test_lineage(left),
                structural_test_lineage(right),
                0,
            )
            .unwrap()
        };
        let mut original_bonds = members
            .windows(2)
            .map(|pair| bond(pair[0], pair[1]))
            .collect::<Vec<_>>();
        original_bonds.sort_unstable();
        let mut recurrence_bonds = active_bonds
            .iter()
            .map(|(left, right)| bond(*left, *right))
            .collect::<Vec<_>>();
        recurrence_bonds.sort_unstable();
        AdmittedPhysicalMosaic::from_parts_for_tests(
            members
                .iter()
                .map(|value| structural_test_lineage(*value))
                .collect(),
            vec![fractal; members.len()],
            original_bonds,
            recurrence_bonds,
            vec![structural_test_lineage(cue)],
        )
    }

    #[test]
    fn legacy_transient_mosaic_is_not_cognitive_authority() {
        let valid = synthetic_admitted_mosaic(&[1, 2, 3], &[(1, 2), (2, 3)], 1);
        let transient =
            crate::complete_neuron::SparsePhysicalStateDelta::from_canonical_entries(vec![
                crate::complete_neuron::PhysicalStateDeltaEntry::new(
                    crate::complete_neuron::PhysicalStateCoordinate::MembraneSeparatedCharge,
                    crate::complete_neuron::ExactPhysicalStateDelta::Integral(
                        crate::complete_neuron::ExactSignedDelta::from_parts(false, 1).unwrap(),
                    ),
                )
                .unwrap(),
            ])
            .unwrap();
        let invalid = AdmittedPhysicalMosaic::from_parts_for_tests(
            valid.member_lineages().to_vec(),
            vec![transient; valid.member_lineages().len()],
            valid.original_bonds().to_vec(),
            valid.recurrence_bonds().to_vec(),
            valid.partial_cue_lineages().to_vec(),
        );
        assert!(!invalid.carries_only_retained_neuron_structure());
        assert!(valid.carries_only_retained_neuron_structure());

        let mut state = ResidentCognitiveFormationState::default();
        state.mosaics = vec![
            RetainedOrganismMosaic::newly_admitted(invalid),
            RetainedOrganismMosaic::newly_admitted(valid),
        ]
        .into_boxed_slice();
        assert_eq!(state.summary().mosaic_count, 1);
        assert_eq!(state.observe_retained_formation_members().len(), 1);
        assert_eq!(state.mosaic_of_mosaics_count().unwrap(), 0);
    }

    /// R1 reinforce branch: same member set and no active bond outside the
    /// retained reference's structure — zero structural difference (R2), so
    /// the reference body stays byte-identical and only the R3 count moves.
    /// The byte-identical reassembly (the former `already_formed` equality
    /// dedup) is the degenerate case of the same branch.
    #[test]
    fn same_members_without_new_active_bonds_reinforce_the_retained_reference() {
        let reference = synthetic_admitted_mosaic(&[1, 2, 3], &[(1, 2), (2, 3)], 1);
        let mut mosaics = vec![RetainedOrganismMosaic::newly_admitted(reference.clone())];
        // A different cue over a strict subset of the active bonds is still
        // the same retained structure.
        let subset = synthetic_admitted_mosaic(&[1, 2, 3], &[(1, 2)], 2);
        let resolution = resolve_mosaic_structural_identity(&mosaics, subset);
        assert_eq!(
            resolution,
            MosaicStructuralResolution::Reinforces { mosaic_index: 0 }
        );
        apply_mosaic_structural_resolution(&mut mosaics, resolution).unwrap();
        let identical = resolve_mosaic_structural_identity(&mosaics, reference.clone());
        assert_eq!(
            identical,
            MosaicStructuralResolution::Reinforces { mosaic_index: 0 }
        );
        apply_mosaic_structural_resolution(&mut mosaics, identical).unwrap();
        assert_eq!(mosaics.len(), 1);
        assert_eq!(mosaics[0].mosaic, reference);
        assert_eq!(mosaics[0].reinforcement_count, 2);
        assert_eq!(mosaics[0].mosaic_of_mosaics_relation_count, 0);
    }

    /// The same neuron membership does not define identity.  A distinct exact
    /// retained neuronal structure is a distinct formation even when every
    /// member lineage is shared.
    #[test]
    fn same_members_with_distinct_retained_structure_admit_distinct_formation() {
        let reference = synthetic_admitted_mosaic(&[1, 2, 3], &[(1, 2), (2, 3)], 1);
        let mut mosaics = vec![RetainedOrganismMosaic {
            mosaic: reference.clone(),
            reinforcement_count: 5,
            mosaic_of_mosaics_relation_count: 1,
        }];
        let mut distinct = synthetic_admitted_mosaic(&[1, 2, 3], &[(1, 3), (2, 3)], 3);
        let changed =
            crate::complete_neuron::SparsePhysicalStateDelta::from_canonical_entries(vec![
                crate::complete_neuron::PhysicalStateDeltaEntry::new(
                    crate::complete_neuron::PhysicalStateCoordinate::PlasticRestLength,
                    crate::complete_neuron::ExactPhysicalStateDelta::Rational(
                        crate::exact_rational::ExactRational::new(2, 3).unwrap(),
                    ),
                )
                .unwrap(),
            ])
            .unwrap();
        distinct = AdmittedPhysicalMosaic::from_parts_for_tests(
            distinct.member_lineages().to_vec(),
            vec![changed; distinct.member_lineages().len()],
            distinct.original_bonds().to_vec(),
            distinct.recurrence_bonds().to_vec(),
            distinct.partial_cue_lineages().to_vec(),
        );
        let resolution = resolve_mosaic_structural_identity(&mosaics, distinct.clone());
        assert_eq!(
            resolution,
            MosaicStructuralResolution::NewFormation(distinct.clone())
        );
        apply_mosaic_structural_resolution(&mut mosaics, resolution).unwrap();
        assert_eq!(mosaics.len(), 2);
        assert_eq!(mosaics[0].mosaic, reference);
        assert_eq!(mosaics[1].mosaic, distinct);
        assert_eq!(mosaics[0].reinforcement_count, 5);
        assert_eq!(mosaics[0].mosaic_of_mosaics_relation_count, 1);
    }

    /// Overlap alone is not a learned relation and cannot suppress a distinct
    /// retained formation.
    #[test]
    fn overlapping_member_sets_retain_each_distinct_formation() {
        let first = synthetic_admitted_mosaic(&[1, 2, 3], &[(1, 2), (2, 3)], 1);
        let second = synthetic_admitted_mosaic(&[7, 8, 9], &[(7, 8), (8, 9)], 7);
        let mut mosaics = vec![
            RetainedOrganismMosaic::newly_admitted(first),
            RetainedOrganismMosaic::newly_admitted(second),
        ];
        let overlapping = synthetic_admitted_mosaic(&[3, 4, 7], &[(3, 4), (4, 7)], 4);
        let resolution = resolve_mosaic_structural_identity(&mosaics, overlapping);
        assert!(matches!(
            resolution,
            MosaicStructuralResolution::NewFormation(_)
        ));
        apply_mosaic_structural_resolution(&mut mosaics, resolution).unwrap();
        assert_eq!(mosaics.len(), 3);
        assert_eq!(mosaics[0].mosaic_of_mosaics_relation_count, 0);
        assert_eq!(mosaics[1].mosaic_of_mosaics_relation_count, 0);
        assert_eq!(mosaics[0].reinforcement_count, 0);
        assert_eq!(mosaics[1].reinforcement_count, 0);
    }

    /// R1 disjoint branch: a member set disjoint from every retained
    /// formation is a genuinely new mosaic — the pre-law behavior, with both
    /// counts at the historical default of zero.
    #[test]
    fn disjoint_member_sets_admit_a_genuinely_new_mosaic() {
        let first = synthetic_admitted_mosaic(&[1, 2, 3], &[(1, 2), (2, 3)], 1);
        let mut mosaics = vec![RetainedOrganismMosaic::newly_admitted(first)];
        let disjoint = synthetic_admitted_mosaic(&[4, 5, 6], &[(4, 5), (5, 6)], 4);
        let resolution = resolve_mosaic_structural_identity(&mosaics, disjoint.clone());
        assert_eq!(
            resolution,
            MosaicStructuralResolution::NewFormation(disjoint.clone())
        );
        apply_mosaic_structural_resolution(&mut mosaics, resolution).unwrap();
        assert_eq!(mosaics.len(), 2);
        assert_eq!(mosaics[1].mosaic, disjoint);
        assert_eq!(mosaics[1].reinforcement_count, 0);
        assert_eq!(mosaics[1].mosaic_of_mosaics_relation_count, 0);
    }

    /// R3 codec: reinforcement/relation counts persist through the organism
    /// state body under the `GLMRC01` wrapper, while zero-count references
    /// keep the bare pre-law encoding byte-identically (GLEXP02/GLEXP03
    /// precedent: the new magic appears only when the retained state differs
    /// from the historical default).
    #[test]
    #[ignore = "retired: fixture requires Boolean/member-set mosaic admission"]
    fn reinforcement_counts_round_trip_and_zero_counts_keep_pre_law_bytes() {
        let light = (0..4)
            .map(exact_four_single_optical_episode)
            .collect::<Vec<_>>();
        let dark = exact_four_dark_optical_episode();
        let seed = explicit_optical_seed(&light[0], 500);
        let mut state =
            ResidentCognitiveFormationState::from_developmental_electrical_seeds(vec![seed])
                .unwrap();
        for source in light
            .iter()
            .chain(std::iter::repeat(&dark).take(DARK_TAIL_EPISODES))
        {
            let prepared = state.prepare(source, 16_000_000).unwrap();
            state.commit(prepared).unwrap();
        }
        let partial = exact_four_partial_optical_episode();
        for source in
            std::iter::once(&partial).chain(std::iter::repeat(&dark).take(DARK_TAIL_EPISODES))
        {
            let prepared = state
                .prepare_admitted_transition(&admitted_fixture_episode(source), 16_000_000)
                .unwrap();
            state.commit(prepared).unwrap();
        }
        assert_eq!(state.summary().mosaic_count, 1);
        assert_eq!(state.mosaics[0].reinforcement_count, 0);

        // Zero counts: the encoded body carries the counts wrapper nowhere,
        // so every pre-law receipt stays byte-identical.
        let bare = state.encode(16_000_000).unwrap();
        assert!(!bare
            .windows(RETAINED_MOSAIC_COUNTS_MAGIC.len())
            .any(|window| window == RETAINED_MOSAIC_COUNTS_MAGIC));

        // Nonzero counts round-trip exactly and re-encode canonically.
        state.mosaics[0].reinforcement_count = 3;
        state.mosaics[0].mosaic_of_mosaics_relation_count = 2;
        let counted = state.encode(16_000_000).unwrap();
        assert!(counted
            .windows(RETAINED_MOSAIC_COUNTS_MAGIC.len())
            .any(|window| window == RETAINED_MOSAIC_COUNTS_MAGIC));
        let restored = ResidentCognitiveFormationState::decode(&counted, 16_000_000).unwrap();
        assert_eq!(restored, state);
        assert_eq!(restored.mosaics[0].reinforcement_count, 3);
        assert_eq!(restored.mosaics[0].mosaic_of_mosaics_relation_count, 2);
        assert_eq!(restored.mosaic_of_mosaics_count().unwrap(), 2);
        assert_eq!(restored.encode(16_000_000).unwrap(), counted);

        // A wrapper claiming zero counts is refused: its canonical form is
        // the bare body, and one retained state never admits two encodings.
        let body = encode_organism_mosaic(
            &state.cohorts,
            &state.electrical_fabric,
            &state.mosaics[0].mosaic,
            16_000_000,
        )
        .unwrap();
        let mut zero_wrapped = Vec::new();
        zero_wrapped.extend_from_slice(RETAINED_MOSAIC_COUNTS_MAGIC);
        zero_wrapped.extend_from_slice(&0u64.to_le_bytes());
        zero_wrapped.extend_from_slice(&0u64.to_le_bytes());
        zero_wrapped.extend_from_slice(&body);
        assert!(matches!(
            decode_retained_organism_mosaic(
                &state.cohorts,
                &state.electrical_fabric,
                &zero_wrapped,
                16_000_000,
            ),
            Err(FormationError::NoncanonicalState)
        ));
    }

    #[test]
    fn exact_optical_occurrence_physically_changes_the_resident_cell() {
        let source = exact_optical_episode();
        let genesis = ResidentCognitiveFormationState::default();
        let genesis_bytes = genesis.encode(16_000_000).unwrap();
        let prepared = genesis.prepare(&source, 16_000_000).unwrap();
        assert_eq!(prepared.observation.complete_neuron_count, 2);
        assert_eq!(prepared.observation.physically_transitioned_neuron_count, 2);
        assert_eq!(prepared.observation.complete_neuron_fractal_count, 3);
        assert_eq!(
            prepared.observation.complete_neuron_fractal_count,
            prepared.observation.emitted_neuron_fractals.len()
        );
        assert_eq!(prepared.successor.electrical_fabric.contact_count(), 1);
        assert!(prepared.successor.cohorts.iter().any(|cohort| {
            cohort
                .anatomy
                .mounts()
                .iter()
                .any(|mount| mount.place() == DeclaredNeuronPlace::new(6, 0))
        }));
        let integration_lineage = prepared
            .successor
            .cohorts
            .iter()
            .find_map(|cohort| {
                cohort
                    .anatomy
                    .mounts()
                    .iter()
                    .position(|mount| mount.place() == DeclaredNeuronPlace::new(6, 0))
                    .map(|index| cohort.anatomy.neuron_lineages()[index])
            })
            .unwrap();
        assert!(prepared
            .observation
            .emitted_neuron_fractals
            .iter()
            .any(|fractal| fractal.neuron_lineage == integration_lineage));
        let successor_bytes = genesis.encode_successor(&prepared, 16_000_000).unwrap();
        assert_ne!(successor_bytes, genesis_bytes);
        let restored =
            ResidentCognitiveFormationState::decode(&successor_bytes, 16_000_000).unwrap();
        assert_eq!(restored.encode(16_000_000).unwrap(), successor_bytes);
    }

    #[test]
    fn local_occurrence_settlement_closes_the_neuronal_fractal() {
        // The completed lit occurrence settles and emits the exact retained
        // projection immediately. Environmental silence and a later
        // scheduler interval are not part of the neuron law. A single
        // receptor cell can never satisfy the three-connected-member
        // participation law, so no mosaic is retained.
        let light = exact_optical_episode();
        let dark = exact_dark_optical_episode();
        let mut state = ResidentCognitiveFormationState::default();
        let light_transition = state.prepare(&light, 16_000_000).unwrap();
        assert_eq!(
            light_transition.observation.complete_neuron_fractal_count,
            3
        );
        assert_eq!(
            light_transition.observation.emitted_neuron_fractals.len(),
            3
        );
        assert!(light_transition
            .observation
            .emitted_neuron_fractals
            .iter()
            .all(|fractal| !fractal.delta.entries().is_empty()));
        state.commit(light_transition).unwrap();

        let mid_experience_bytes = state.encode(16_000_000).unwrap();
        let mut restored =
            ResidentCognitiveFormationState::decode(&mid_experience_bytes, 16_000_000).unwrap();
        assert_eq!(restored, state);

        let mut emitted_after_occurrence = Vec::new();
        for _ in 0..DARK_TAIL_EPISODES {
            let prepared = restored.prepare(&dark, 16_000_000).unwrap();
            emitted_after_occurrence.extend(prepared.observation.emitted_neuron_fractals.clone());
            restored.commit(prepared).unwrap();
            if !emitted_after_occurrence.is_empty() {
                break;
            }
        }
        assert!(emitted_after_occurrence.is_empty());
        // Participation retention: one changed member is fewer than the
        // admission law's three-connected-member floor, so no mosaic is
        // retained. Its real neuronal impression remains as the one bounded
        // pending experience; the mosaic minimum is not an erasure rule.
        assert!(restored.cohorts[0].retained_experience.is_none());
        assert!(restored.cohorts[0].pending_experience.is_some());

        // The boundary emission is one-shot: the cell holds its settled
        // state through the second dark episode, so no new experience opens
        // and nothing further is emitted.
        let later_dark = restored.prepare(&dark, 16_000_000).unwrap();
        assert_eq!(later_dark.observation.complete_neuron_fractal_count, 0);
    }

    #[test]
    fn continued_identical_light_emits_each_retained_physical_change() {
        // The authenticated occurrence boundary closes the exact retained
        // impression even while photons continue. No later unchanged
        // scheduler interval is required.
        let light = exact_optical_episode();
        let mut state = ResidentCognitiveFormationState::default();
        let first = state.prepare(&light, 16_000_000).unwrap();
        assert_eq!(first.observation.complete_neuron_fractal_count, 3);
        assert_eq!(first.observation.emitted_neuron_fractals.len(), 3);
        state.commit(first).unwrap();

        let mut emitted = Vec::new();
        for _ in 0..DARK_TAIL_EPISODES {
            let prepared = state.prepare(&light, 16_000_000).unwrap();
            emitted.extend(prepared.observation.emitted_neuron_fractals.clone());
            state.commit(prepared).unwrap();
            if !emitted.is_empty() {
                break;
            }
        }
        assert!(emitted
            .iter()
            .all(|fractal| !fractal.delta.entries().is_empty()));
        assert!(state.cohorts[0].pending_experience.is_some());
        assert!(state.cohorts[0].retained_experience.is_none());
    }

    #[test]
    fn typed_vestibular_source_persists_one_specialized_neuron_then_emits_after_quiescence() {
        let canal_anatomy =
            CanalAnatomy::new(6, 13_200, PositiveRatio::new(25, 1).unwrap()).unwrap();
        let bundle_anatomy = LocalCupulaBundleAnatomy::new(2, 5, 20_000).unwrap();
        let receptor_anatomy = phase_one_virtual_vestibular_anatomy().unwrap();
        let predecessor_body = YawBodyState::new(0).unwrap();
        let body = settle_signed_yaw_actuation(
            predecessor_body,
            SignedYawActuation::new(360, WORLD_MECHANICAL_TICK_MICROSECONDS).unwrap(),
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
        let retired = ResidentCognitiveFormationState::default()
            .encode_with_format(CognitiveCodecFormat::V12, 16_000_000)
            .unwrap();
        let current =
            ResidentCognitiveFormationState::migrate_to_current_format(&retired, 16_000_000)
                .unwrap();
        let mut state = ResidentCognitiveFormationState::decode(&current, 16_000_000).unwrap();
        let site = NeuronSourceSite::from_source_port(
            &ingress
                .source()
                .joint_source_with_contacts()
                .0
                .joint_source_ports()[0],
        )
        .unwrap();
        let place = DeclaredNeuronPlace::from_source_site(&site);
        let population = state.resting_population.as_ref().unwrap();
        let resting = population
            .materialize(population.population_offset(place).unwrap())
            .unwrap();
        let expected_lineage = local_lineage_from_ordinal(resting.lineage_ordinal).unwrap();
        let predecessor_resting_count = population.resting_cell_count();
        let predecessor_total_neurons = state.summary().complete_neuron_count
            + usize::try_from(predecessor_resting_count).unwrap();
        let stimulating = state
            .prepare_vestibular_transition(&ingress, 16_000_000)
            .unwrap();
        assert_eq!(stimulating.observation.complete_neuron_count, 3);
        assert_eq!(
            stimulating.observation.physically_transitioned_neuron_count,
            2
        );
        assert_eq!(stimulating.observation.emitted_neuron_fractals.len(), 3);
        let emitted = stimulating.observation.emitted_neuron_fractals.clone();
        state.commit(stimulating).unwrap();
        assert_eq!(
            state
                .resting_population
                .as_ref()
                .unwrap()
                .resting_cell_count(),
            predecessor_resting_count - 3
        );
        assert_eq!(state.cohorts.len(), 3);
        assert_eq!(state.cohorts[0].anatomy.neuron_count(), 1);
        assert_eq!(
            state.summary().complete_neuron_count
                + usize::try_from(
                    state
                        .resting_population
                        .as_ref()
                        .unwrap()
                        .resting_cell_count(),
                )
                .unwrap(),
            predecessor_total_neurons
        );
        assert_eq!(
            state.cohorts[0].anatomy.neuron_lineages()[0],
            expected_lineage
        );
        assert_eq!(
            state.cohorts[0].anatomy.neuron_anatomies()[0].capacitance(),
            resting.anatomy.capacitance()
        );
        assert_eq!(
            state.cohorts[0].anatomy.neuron_anatomies()[0].gate_dissipation_capacity_quanta(),
            receptor_anatomy.gate_dissipation_capacity_quanta()
        );
        let layers = state
            .cohorts
            .iter()
            .flat_map(|cohort| cohort.anatomy.mounts())
            .map(|mount| mount.place().layer())
            .collect::<Vec<_>>();
        assert!(layers.contains(&5));
        assert!(layers.contains(&6));
        assert!(layers.contains(&8));

        let encoded = state.encode(16_000_000).unwrap();
        state = ResidentCognitiveFormationState::decode(&encoded, 16_000_000).unwrap();
        let lineage = state.cohorts[0].anatomy.neuron_lineages()[0];
        assert_eq!(emitted.len(), 3);
        assert!(emitted
            .iter()
            .any(|fractal| fractal.neuron_lineage == lineage));
    }

    fn lesson_state_with_retained_experience() -> ResidentCognitiveFormationState {
        let light = (0..4)
            .map(exact_four_single_optical_episode)
            .collect::<Vec<_>>();
        let dark = exact_four_dark_optical_episode();
        let seed = explicit_optical_seed(&light[0], 500);
        let mut state =
            ResidentCognitiveFormationState::from_developmental_electrical_seeds(vec![seed])
                .unwrap();
        for source in light
            .iter()
            .chain(std::iter::repeat(&dark).take(DARK_TAIL_EPISODES))
        {
            let prepared = state.prepare(source, 16_000_000).unwrap();
            state.commit(prepared).unwrap();
        }
        assert!(state.cohorts[0].retained_experience.is_some());
        state
    }

    #[test]
    #[ignore = "retired: fixture requires Boolean/member-set mosaic admission"]
    fn continuing_contact_tail_cannot_begin_endogenous_reassembly() {
        let light = (0..4)
            .map(exact_four_single_optical_episode)
            .collect::<Vec<_>>();
        let dark = exact_four_dark_optical_episode();
        let seed = explicit_optical_seed(&light[0], 500);
        let mut state =
            ResidentCognitiveFormationState::from_developmental_electrical_seeds(vec![seed])
                .unwrap();
        for source in light.iter().chain(std::iter::once(&dark)) {
            let prepared = state.prepare(source, 16_000_000).unwrap();
            assert_eq!(
                prepared
                    .observation
                    .endogenous_partial_cue_reassembly_count(),
                0
            );
            state.commit(prepared).unwrap();
        }
        assert!(state.cohorts[0].pending_experience.is_none());
        assert!(state.cohorts[0].retained_experience.is_some());
        assert!(
            !state.cohorts[0]
                .retained_experience
                .as_ref()
                .unwrap()
                .local_relaxation_observed
        );

        let mut relaxation_observed = false;
        for _ in 0..DARK_TAIL_EPISODES {
            let prepared = state.prepare(&dark, 16_000_000).unwrap();
            assert_eq!(
                prepared
                    .observation
                    .endogenous_partial_cue_reassembly_count(),
                0,
                "the interval that ends the original tail cannot cue itself"
            );
            relaxation_observed = prepared.successor.cohorts[0]
                .retained_experience
                .as_ref()
                .is_some_and(|experience| experience.local_relaxation_observed);
            state.commit(prepared).unwrap();
            if relaxation_observed {
                break;
            }
        }
        assert!(state.cohorts[0].retained_experience.is_some());
        assert!(relaxation_observed);

        let encoded_at_rest = state.encode(16_000_000).unwrap();
        let restored =
            ResidentCognitiveFormationState::decode(&encoded_at_rest, 16_000_000).unwrap();
        assert_eq!(restored, state);
        assert_eq!(restored.encode(16_000_000).unwrap(), encoded_at_rest);

        let retained = state.cohorts[0].retained_experience.as_ref().unwrap();
        let mut unrelated_flow = vec![false; retained.active_electrical_contacts.len()];
        let original_contact = retained
            .active_electrical_contacts
            .iter()
            .position(|active| *active)
            .unwrap();
        let unrelated_contact = (0..unrelated_flow.len())
            .find(|index| *index != original_contact)
            .unwrap();
        let mut one_contact_formation = retained.clone();
        one_contact_formation.active_electrical_contacts.fill(false);
        one_contact_formation.active_electrical_contacts[original_contact] = true;
        unrelated_flow[unrelated_contact] = true;
        assert!(!retained_contact_set_flowing(&one_contact_formation, &unrelated_flow).unwrap());

        let partial = exact_four_partial_optical_episode();
        let mut endogenous = 0usize;
        let mut total = 0usize;
        for source in
            std::iter::once(&partial).chain(std::iter::repeat(&dark).take(DARK_TAIL_EPISODES))
        {
            let prepared = state
                .prepare_admitted_transition(&admitted_fixture_episode(source), 16_000_000)
                .unwrap();
            endogenous += prepared
                .observation
                .endogenous_partial_cue_reassembly_count();
            total += prepared.observation.partial_cue_reassembly_count();
            state.commit(prepared).unwrap();
        }
        // The explicit partial cue may reassemble the retained formation, but
        // its continuing contact current is not an organism-generated cue.
        // Endogenous recurrence must begin from a later metabolic perturbation
        // of a proper partial member set, not from the external cue's tail.
        assert_eq!(total, 1);
        assert_eq!(endogenous, 0);

        let mut severed = restored;
        severed.cohorts[0]
            .retained_experience
            .as_mut()
            .unwrap()
            .active_electrical_contacts
            .fill(false);
        let mut severed_reassemblies = 0usize;
        for source in
            std::iter::once(&partial).chain(std::iter::repeat(&dark).take(DARK_TAIL_EPISODES))
        {
            let prepared = severed
                .prepare_admitted_transition(&admitted_fixture_episode(source), 16_000_000)
                .unwrap();
            severed_reassemblies += prepared.observation.partial_cue_reassembly_count();
            severed.commit(prepared).unwrap();
        }
        assert_eq!(severed_reassemblies, 0);
        assert_eq!(severed.summary().mosaic_count, 0);
    }

    #[test]
    fn content_addressed_body_post_marker_and_current_specialization_are_exact() {
        let state = lesson_state_with_retained_experience();
        let cohort = &state.cohorts[0];
        let retained = cohort.retained_experience.as_ref().unwrap();
        // Retentive closure fixes the exact post-presentation reference while
        // the living neuron's transient membrane, contact, and metabolic
        // coordinates continue moving through the later dark tail.
        let post = retained.post_experience_rest.as_ref().unwrap();
        assert_ne!(post, &cohort.state);
        let current = state.encode(16_000_000).unwrap();
        assert_eq!(
            ResidentCognitiveFormationState::decode(&current, 16_000_000).unwrap(),
            state
        );
        assert_eq!(state.summary().complete_neuron_count, 8);
        assert_eq!(state.electrical_fabric.contact_count(), 4);
        // V12 has no intrinsic mount or cross-cohort fabric representation.
        // Refuse a lossy backward projection instead of silently deleting the
        // specialization. Legacy-to-current migration is exercised by the
        // real-body migration probes.
        assert!(matches!(
            state.encode_with_format(CognitiveCodecFormat::V12, 16_000_000),
            Err(FormationError::NoncanonicalState)
        ));

        // The current living state has moved beyond the retained post state,
        // so a current-state base cannot truthfully stand in for that post
        // state and the evidence carries the exact post body inline.
        let resident_form =
            encode_experience_evidence_v2(&cohort.anatomy, Some(&cohort.state), retained, true)
                .unwrap();
        let mut cursor = EXPERIENCE_V4_MAGIC.len() + 2;
        let pre_length = read_length(&resident_form, &mut cursor).unwrap();
        assert_eq!(
            resident_form[cursor + pre_length],
            1,
            "post distinct from the living-state base is retained inline"
        );
        assert_eq!(
            decode_experience_evidence_v2(&resident_form, &cohort.anatomy, Some(&cohort.state))
                .unwrap(),
            *retained
        );
        // The content-addressed marker (mode 2) still collapses the post
        // body to its digest whenever the base IS byte-identical to it, and
        // a lying digest is still refused.
        let evidence =
            encode_experience_evidence_v2(&cohort.anatomy, Some(post), retained, true).unwrap();
        let mut cursor = EXPERIENCE_V4_MAGIC.len() + 2;
        let pre_length = read_length(&evidence, &mut cursor).unwrap();
        let post_mode_offset = cursor + pre_length;
        assert_eq!(evidence[post_mode_offset], 2, "post retained as marker");
        assert_eq!(
            decode_experience_evidence_v2(&evidence, &cohort.anatomy, Some(post)).unwrap(),
            *retained
        );
        let mut lying = evidence.clone();
        lying[post_mode_offset + 1] ^= 1;
        assert!(decode_experience_evidence_v2(&lying, &cohort.anatomy, Some(post)).is_err());
        assert!(decode_experience_evidence_v2(
            &evidence,
            &cohort.anatomy,
            Some(&retained.pre_experience_rest)
        )
        .is_err());

        let full_form = encode_experience_evidence_v2(
            &cohort.anatomy,
            Some(&retained.pre_experience_rest),
            retained,
            true,
        )
        .unwrap();
        let mut cursor = EXPERIENCE_V4_MAGIC.len() + 2;
        let pre_length = read_length(&full_form, &mut cursor).unwrap();
        assert_eq!(
            full_form[cursor + pre_length],
            1,
            "post differing from the base is retained in full"
        );
        assert_eq!(
            decode_experience_evidence_v2(
                &full_form,
                &cohort.anatomy,
                Some(&retained.pre_experience_rest)
            )
            .unwrap(),
            *retained
        );
    }

    #[test]
    fn first_receptor_contact_claims_receptor_and_local_integration_cells() {
        let empty = ResidentCognitiveFormationState::default();
        let retired = empty
            .encode_with_format(CognitiveCodecFormat::V12, 16_000_000)
            .unwrap();
        let current =
            ResidentCognitiveFormationState::migrate_to_current_format(&retired, 16_000_000)
                .unwrap();
        let state = ResidentCognitiveFormationState::decode(&current, 16_000_000).unwrap();
        let source = exact_optical_episode();
        let shared = prepare_complete_joint_field_admitted_fixture(&source, 0).unwrap();
        let perspective = bind_neuron_perspective(&shared, 0, 0).unwrap();
        let site =
            NeuronSourceSite::from_anchor(bind_neuron_source_anchor(&source, perspective).unwrap());
        let place = DeclaredNeuronPlace::from_source_site(&site);
        let population = state.resting_population.as_ref().unwrap();
        let offset = population.population_offset(place).unwrap();
        let resting = population.materialize(offset).unwrap();
        let resting_count = population.resting_cell_count();
        let expected_lineage = local_lineage_from_ordinal(resting.lineage_ordinal).unwrap();
        let prepared = state
            .prepare_admitted_transition(&admitted_fixture_episode(&source), 16_000_000)
            .unwrap();
        let successor = prepared.successor;
        assert_eq!(
            successor
                .resting_population
                .as_ref()
                .unwrap()
                .resting_cell_count(),
            resting_count - 2
        );
        let cohort = successor
            .cohorts
            .iter()
            .find(|cohort| cohort.anatomy.source_sites().any(|source| source == &site))
            .unwrap();
        let neuron_index = cohort.anatomy.source_site_member(&site).unwrap();
        assert_eq!(
            cohort.anatomy.neuron_lineages()[neuron_index],
            expected_lineage
        );
        assert_eq!(
            cohort.anatomy.neuron_anatomies()[neuron_index].capacitance(),
            resting.anatomy.capacitance()
        );
        assert_eq!(successor.summary().complete_neuron_count, 2);
        assert_eq!(successor.electrical_fabric.contact_count(), 1);
        let encoded = successor.encode(16_000_000).unwrap();
        let cold = ResidentCognitiveFormationState::decode(&encoded, 16_000_000).unwrap();
        assert_eq!(cold, successor);
    }

    #[test]
    fn sense_local_topology_indices_project_to_distinct_integration_places() {
        let sight = local_integration_place(DeclaredNeuronPlace::new(0, 0)).unwrap();
        let sound = local_integration_place(DeclaredNeuronPlace::new(1, 0)).unwrap();
        let body = local_integration_place(DeclaredNeuronPlace::new(5, 0)).unwrap();
        assert_eq!(sight, DeclaredNeuronPlace::new(6, 0));
        assert_eq!(sound, DeclaredNeuronPlace::new(6, 1));
        assert_eq!(body, DeclaredNeuronPlace::new(6, 15));
        assert_ne!(sight, sound);
        assert_ne!(sound, body);
        assert_ne!(sight, body);
    }

    #[test]
    fn one_interval_frontier_does_not_jump_across_a_contact_chain() {
        let reached = one_interval_electrical_frontier(
            &[true, false, false, false],
            &[(0, 1), (1, 2), (2, 3)],
        )
        .unwrap();
        assert_eq!(reached, vec![true, true, false, false]);

        let next = one_interval_electrical_frontier(&reached, &[(0, 1), (1, 2), (2, 3)]).unwrap();
        assert_eq!(next, vec![true, true, true, false]);
    }

    #[test]
    fn one_multisensory_occurrence_mounts_one_reusable_physical_association() {
        fn receptor_cohort(
            sense: PhysicalSourceSense,
            topology_index: u32,
            lineage: [u8; 16],
        ) -> ResidentReachedCohort {
            let site = NeuronSourceSite::fixture_in_sense(sense, topology_index);
            let place = DeclaredNeuronPlace::from_source_site(&site);
            let neuron = create_quiescent_virtual_material_neuron(place).unwrap();
            let sparse = SparseElectricalAnatomy::new(1, Vec::new()).unwrap();
            let anatomy = ReachedCohortAnatomy::new_mounted(
                vec![neuron.anatomy],
                vec![lineage],
                vec![ReachedNeuronMount::Receptor(site)],
                sparse.clone(),
            )
            .unwrap();
            ResidentReachedCohort {
                state: ReachedCohortState::new(
                    &anatomy,
                    vec![neuron.state],
                    SparseElectricalState::genesis(&sparse),
                )
                .unwrap(),
                anatomy,
                pending_experience: None,
                retained_experience: None,
                pending_recurrence: None,
            }
        }

        let receptor_lineages = [local_lineage(1), local_lineage(2), local_lineage(3)];
        let mut cohorts = vec![
            receptor_cohort(PhysicalSourceSense::Sight, 0, receptor_lineages[0]),
            receptor_cohort(PhysicalSourceSense::Sight, 1, receptor_lineages[1]),
            receptor_cohort(PhysicalSourceSense::Sound, 0, receptor_lineages[2]),
        ];
        let occupied = cohorts
            .iter()
            .flat_map(|cohort| cohort.anatomy.mounts().iter().map(|mount| mount.place()))
            .collect::<Vec<_>>();
        let mut population = Some(
            DevelopmentalRestingPopulation::admit(16_000_000, 100_000, 100, &occupied).unwrap(),
        );
        let mut next_lineage = 4;
        let mut fabric = ResidentElectricalFabric::default();
        mount_reached_local_integration(
            &mut cohorts,
            &mut population,
            &mut next_lineage,
            &mut fabric,
        )
        .unwrap();
        mount_reached_cross_sensory_association(
            &mut cohorts,
            &mut population,
            &mut next_lineage,
            &mut fabric,
            &receptor_lineages,
        )
        .unwrap();
        let association = cohorts
            .iter()
            .flat_map(|cohort| {
                cohort
                    .anatomy
                    .mounts()
                    .iter()
                    .zip(cohort.anatomy.neuron_lineages())
            })
            .filter(|(mount, _)| mount.place().layer() == 7)
            .map(|(_, lineage)| *lineage)
            .collect::<Vec<_>>();
        assert_eq!(association.len(), 1);
        assert_eq!(fabric.contact_count(), 6);
        let cohort_count = cohorts.len();
        let contact_count = fabric.contact_count();

        mount_reached_cross_sensory_association(
            &mut cohorts,
            &mut population,
            &mut next_lineage,
            &mut fabric,
            &receptor_lineages,
        )
        .unwrap();
        assert_eq!(cohorts.len(), cohort_count);
        assert_eq!(fabric.contact_count(), contact_count);

        let topology = organism_mosaic_topology(&cohorts, &fabric).unwrap();
        let fractal =
            crate::complete_neuron::SparsePhysicalStateDelta::from_canonical_entries(vec![
                crate::complete_neuron::PhysicalStateDeltaEntry::new(
                    crate::complete_neuron::PhysicalStateCoordinate::PlasticRestLength,
                    crate::complete_neuron::ExactPhysicalStateDelta::Rational(
                        ExactRational::new(1, 3).unwrap(),
                    ),
                )
                .unwrap(),
            ])
            .unwrap();
        let original = admit_physical_mosaic_original(
            &topology.lineages,
            &topology.fractal_anatomies,
            &vec![Some(fractal); topology.lineages.len()],
            &topology.bonds,
        )
        .unwrap();
        let encoded = encode_organism_mosaic(&cohorts, &fabric, &original, 16_000_000).unwrap();
        let cold = decode_organism_mosaic(&cohorts, &fabric, &encoded, 16_000_000).unwrap();
        assert_eq!(cold, original);
        let recognized = prove_physical_mosaic_recurrence(
            &cold,
            &topology.lineages,
            &topology.bonds,
            &receptor_lineages,
        )
        .unwrap();
        assert!(recognized.carries_only_retained_neuron_structure());
    }

    #[test]
    fn coincident_association_and_body_motion_mounts_one_reusable_affective_reach() {
        let mut cohorts = Vec::new();
        let mut population =
            Some(DevelopmentalRestingPopulation::admit(16_000_000, 100_000, 100, &[]).unwrap());
        let mut next_lineage = 1;
        let association = mount_intrinsic_neuron_at_place(
            &mut cohorts,
            &mut population,
            &mut next_lineage,
            DeclaredNeuronPlace::new(7, 0),
        )
        .unwrap();
        let regulation = mount_intrinsic_neuron_at_place(
            &mut cohorts,
            &mut population,
            &mut next_lineage,
            DeclaredNeuronPlace::new(8, 0),
        )
        .unwrap();
        let resting_before = population.as_ref().unwrap().resting_cell_count();
        let mut fabric = ResidentElectricalFabric::default();
        mount_reached_affective_reach(
            &mut cohorts,
            &mut population,
            &mut next_lineage,
            &mut fabric,
            &[association, regulation],
        )
        .unwrap();
        let affective = cohorts
            .iter()
            .flat_map(|cohort| {
                cohort
                    .anatomy
                    .mounts()
                    .iter()
                    .zip(cohort.anatomy.neuron_lineages())
            })
            .filter(|(mount, _)| mount.place().layer() == 10)
            .map(|(_, lineage)| *lineage)
            .collect::<Vec<_>>();
        assert_eq!(affective.len(), 1);
        assert_eq!(
            population.as_ref().unwrap().resting_cell_count(),
            resting_before - 1
        );
        assert!(fabric.contains_contact(association, affective[0]));
        assert!(fabric.contains_contact(regulation, affective[0]));
        let cohort_count = cohorts.len();
        let contact_count = fabric.contact_count();

        mount_reached_affective_reach(
            &mut cohorts,
            &mut population,
            &mut next_lineage,
            &mut fabric,
            &[regulation, association],
        )
        .unwrap();
        assert_eq!(cohorts.len(), cohort_count);
        assert_eq!(fabric.contact_count(), contact_count);
        assert_eq!(
            population.as_ref().unwrap().resting_cell_count(),
            resting_before - 1
        );
    }

    #[test]
    fn whole_organism_activity_reaches_affective_geography_after_lived_propagation() {
        let canal_anatomy =
            CanalAnatomy::new(6, 13_200, PositiveRatio::new(25, 1).unwrap()).unwrap();
        let bundle_anatomy = LocalCupulaBundleAnatomy::new(2, 5, 20_000).unwrap();
        let receptor_anatomy = phase_one_virtual_vestibular_anatomy().unwrap();
        let mut state = ResidentCognitiveFormationState::default();
        let turn = settle_signed_yaw_actuation(
            YawBodyState::new(0).unwrap(),
            SignedYawActuation::new(90_000, 250_000).unwrap(),
        )
        .unwrap();
        let mut canal = CanalState::at_rest();
        let mut heading = 0_u32;
        for (source_tick, signed_step) in turn.trajectory.as_slice().iter().copied().enumerate() {
            let predecessor_body = YawBodyState::new(heading).unwrap();
            heading =
                u32::try_from((i64::from(heading) + i64::from(signed_step)).rem_euclid(360_000))
                    .unwrap();
            let successor_body = YawBodyState::new(heading).unwrap();
            let reached = settle_reached_vestibular_bundle_tick(
                canal_anatomy,
                canal,
                signed_step,
                bundle_anatomy,
            )
            .unwrap();
            canal = reached.successor_canal;
            let ingress = prepare_resident_vestibular_ingress(
                u64::try_from(source_tick).unwrap(),
                predecessor_body,
                successor_body,
                reached,
                &receptor_anatomy,
            )
            .unwrap();
            let vestibular = state
                .prepare_vestibular_transition(&ingress, 16_000_000)
                .unwrap();
            state = vestibular.successor;
        }
        let source = exact_optical_binaural_episode();
        for _ in 0..6 {
            let prepared = state.prepare(&source, 16_000_000).unwrap();
            state = prepared.successor;
        }
        let layer_ten = state
            .cohorts
            .iter()
            .flat_map(|cohort| cohort.anatomy.mounts())
            .filter(|mount| mount.place().layer() == 10)
            .count();
        assert_eq!(layer_ten, 1);
        let encoded = state.encode(16_000_000).unwrap();
        let cold = ResidentCognitiveFormationState::decode(&encoded, 16_000_000).unwrap();
        assert_eq!(cold, state);
    }

    #[test]
    fn one_new_retained_mosaic_mounts_one_sparse_recurrent_route() {
        let mut cohorts = Vec::new();
        let mut population =
            Some(DevelopmentalRestingPopulation::admit(16_000_000, 100_000, 100, &[]).unwrap());
        let mut next_lineage = 1;
        let members = (0..3)
            .map(|topology| {
                mount_intrinsic_neuron_at_place(
                    &mut cohorts,
                    &mut population,
                    &mut next_lineage,
                    DeclaredNeuronPlace::new(6, topology),
                )
                .unwrap()
            })
            .collect::<Vec<_>>();
        let mut fabric = ResidentElectricalFabric::default();
        mount_new_recurrent_retention(
            &mut cohorts,
            &mut population,
            &mut next_lineage,
            &mut fabric,
            &[members.clone()],
        )
        .unwrap();
        let retention = cohorts
            .iter()
            .flat_map(|cohort| {
                cohort
                    .anatomy
                    .mounts()
                    .iter()
                    .zip(cohort.anatomy.neuron_lineages())
            })
            .filter(|(mount, _)| mount.place().layer() == 9)
            .map(|(_, lineage)| *lineage)
            .collect::<Vec<_>>();
        assert_eq!(retention.len(), 1);
        assert_eq!(fabric.contact_count(), members.len());
        assert!(members
            .iter()
            .all(|member| fabric.contains_contact(*member, retention[0])));

        let cohort_count = cohorts.len();
        let contact_count = fabric.contact_count();
        mount_new_recurrent_retention(
            &mut cohorts,
            &mut population,
            &mut next_lineage,
            &mut fabric,
            &[],
        )
        .unwrap();
        assert_eq!(cohorts.len(), cohort_count);
        assert_eq!(fabric.contact_count(), contact_count);
    }

    /// THE HEADLINE LAW, at the crate boundary: admitting a real physical
    /// mosaic — the thing that used to publish ~893 objects per reassembly —
    /// now creates NOTHING on disk, and the retired checkpoint does not move.
    ///
    /// This replaces `episode_by_reference_round_trips_through_directory_cold_custody`,
    /// which proved the opposite law (that a reassembly round-tripped through
    /// a content-addressed directory).  That law is retired by owner's order.
    #[test]
    #[ignore = "retired: fixture requires Boolean/member-set mosaic admission"]
    fn an_admitted_reassembly_writes_no_file_anywhere_and_moves_no_checkpoint() {
        let root = std::env::temp_dir().join(format!(
            "guala-no-archive-{}-{}",
            std::process::id(),
            line!(),
        ));
        let _ = std::fs::remove_dir_all(&root);
        std::fs::create_dir_all(&root).unwrap();
        let entries_before = std::fs::read_dir(&root).unwrap().count();

        let mut state = lesson_state_with_retained_experience();
        let checkpoint_before = state.hippocampal;
        let partial = exact_four_partial_optical_episode();
        let dark = exact_four_dark_optical_episode();
        let sources = std::iter::once(&partial)
            .chain(std::iter::repeat(&dark).take(DARK_TAIL_EPISODES))
            .collect::<Vec<_>>();
        let mut formed = 0usize;
        let mut reassemblies = 0usize;
        let mut endogenous_reassemblies = 0usize;
        for source in sources {
            let prepared = state
                .prepare_admitted_transition(&admitted_fixture_episode(source), 16_000_000)
                .unwrap();
            if prepared.observation.mosaic_formed.is_some() {
                formed += 1;
            }
            reassemblies += prepared.observation.partial_cue_reassembly_count;
            endogenous_reassemblies += prepared.observation.endogenous_partial_cue_reassembly_count;
            // The successor encodes and commits with no publication step.
            state.encode_successor(&prepared, 16_000_000).unwrap();
            state.commit(prepared).unwrap();
        }

        // Reassembly still happened — this is not a test of an inert path.
        // This fixture supplies one external partial cue; the cue's own
        // continuing contact tail is not mislabeled as endogenous activity.
        assert_eq!(formed, 1);
        assert_eq!(reassemblies, 1);
        assert_eq!(endogenous_reassemblies, 0);
        // And the file count did not move by one.
        assert_eq!(std::fs::read_dir(&root).unwrap().count(), entries_before);
        assert_eq!(state.hippocampal, checkpoint_before);
        assert!(!state.hippocampal.carries_retired_archive_reference());
        let _ = std::fs::remove_dir_all(&root);
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
#[cfg(test)]
mod reservoir_probe;
