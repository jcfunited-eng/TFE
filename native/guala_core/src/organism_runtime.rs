//! Smallest truthful native organism runtime step.
//!
//! One step consumes one current `GLORUN01` envelope and one authenticated
//! `NativeJointSourceEpisode`. The current `GLMFAB07` fabric retains exact
//! mounted joint-field delivery state and an explicit empty cognitive section.
//! A DSF delivery is not a neuronal fractal and cannot form cognition. Organism tick,
//! fabric generation, and mounted generation are independent local clocks;
//! each must be contiguous within its own mechanism and none is numerically
//! equated with another.
//!
//! This module makes no membrane, channel, fluid, physical-body, hippocampal,
//! motivation, action, or language claim. It performs no Python callback and
//! owns no persistence, owner, lock, or global clock.

use crate::hippocampal_sparse_path::HippocampalColdPort;
#[cfg(test)]
use crate::hippocampal_sparse_path::HippocampalColdStore;
use crate::joint_source_episode::NativeJointSourceEpisode;
use crate::materialized_fabric::migrate_authenticated_glmfab03_to_current;
use crate::mounted_joint_fractal::{
    encode_empty_mounted_joint_state, inspect_mounted_joint_dsf_summary,
    prepare_resident_mounted_generation, restore_resident_mounted_state,
    transition_mounted_joint_dsf, MountedJointDsfSummary, MountedJointDsfTransition,
    MountedTransitionPhaseCounts, ResidentMountedRestoreWork, ResidentMountedState,
};
use crate::resident_cognitive_formation::{
    CognitiveFormationObservation, CognitiveFormationSummary, CognitiveOccurrence,
    PreparedCognitiveFormationTransition, ResidentCognitiveFormationState,
};
use crate::resident_receptor_transition::{
    prepare_resident_receptor_ingress, ResidentReceptorIngressObservation,
};
use crate::sha256::sha256;
use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;
use pyo3::types::PyBytes;
use std::fmt;
use std::sync::Arc;

const MAGIC: &[u8; 8] = b"GLORUN01";
const VERSION: u16 = 1;
const LEGACY_FABRIC_MAGIC: &[u8; 8] = b"GLMFAB04";
const LEGACY_FABRIC_VERSION: u16 = 4;
const FABRIC_MAGIC: &[u8; 8] = b"GLMFAB07";
const FABRIC_VERSION: u16 = 7;
const IDENTITY_BYTES: usize = 36;
const FIXED_BYTES: usize = MAGIC.len()
    + std::mem::size_of::<u16>()
    + IDENTITY_BYTES
    + std::mem::size_of::<u64>()
    + std::mem::size_of::<u32>();
const FABRIC_FIXED_BYTES: usize = FABRIC_MAGIC.len()
    + std::mem::size_of::<u16>()
    + std::mem::size_of::<u64>()
    + std::mem::size_of::<u32>()
    + std::mem::size_of::<u32>();
const LEGACY_FABRIC_FIXED_BYTES: usize = LEGACY_FABRIC_MAGIC.len()
    + std::mem::size_of::<u16>()
    + std::mem::size_of::<u64>()
    + std::mem::size_of::<u32>();
const OBSERVATION_SCHEMA: &str = "guala.native.organism_runtime.observation.v5";
const MIGRATION_SCHEMA: &str = "guala.native.task853_organism_runtime_migration.v1";
const MIGRATION_SCOPE: &str = "authenticated_task853_predecessor_migration_only";
const RESIDENT_RUNTIME_SCHEMA: &str = "guala.native.resident_organism_runtime.v3";
const RESIDENT_OBSERVATION_SCHEMA: &str = "guala.native.resident_organism_observation.v3";
const RESIDENT_PREPARE_SCHEMA: &str = "guala.native.resident_organism_prepare.v3";
const PREPARE_TOKEN_MAGIC: &[u8; 8] = b"GLRTPN01";
const RESTORED_SCOPE: &str = "current_native_state_restored";
const MOUNTED_STEP_SCOPE: &str = "mounted_joint_field_delivery_without_neuronal_cognition";
const TASK853_IDENTITY: &str = "1cc4e70a-f2a0-44c5-a111-f4a5bc915cc1";
const TASK853_ORGANISM_TICK: u64 = 23_723_846;
const TASK853_GLMFAB03_SHA256: [u8; 32] = [
    0xb1, 0xf5, 0x38, 0xe2, 0x5d, 0x0b, 0xf5, 0x95, 0x84, 0x26, 0x61, 0x72, 0xcc, 0xb4, 0x73, 0xb2,
    0xb2, 0xdb, 0x6a, 0xd7, 0xdd, 0xf1, 0xfc, 0x1f, 0x7f, 0xfa, 0x54, 0x2b, 0xd2, 0xcc, 0x7e, 0x14,
];

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) struct RuntimeBudget {
    max_envelope_bytes: usize,
    max_fabric_bytes: usize,
    max_logical_peak_bytes: usize,
}

impl RuntimeBudget {
    pub(crate) fn new(
        max_envelope_bytes: usize,
        max_fabric_bytes: usize,
        max_logical_peak_bytes: usize,
    ) -> Result<Self, RuntimeError> {
        let budget = Self {
            max_envelope_bytes,
            max_fabric_bytes,
            max_logical_peak_bytes,
        };
        budget.derive()?;
        Ok(budget)
    }

    fn derive(self) -> Result<DerivedRuntimeBudget, RuntimeError> {
        if self.max_envelope_bytes <= FIXED_BYTES || self.max_fabric_bytes <= FABRIC_FIXED_BYTES {
            return Err(RuntimeError::InvalidBudget);
        }
        let retained_envelopes = self
            .max_envelope_bytes
            .checked_mul(2)
            .ok_or(RuntimeError::BudgetArithmeticOverflow)?;
        let max_joint_working_bytes = self
            .max_logical_peak_bytes
            .checked_sub(retained_envelopes)
            .filter(|value| *value > 0)
            .ok_or(RuntimeError::InvalidBudget)?;
        Ok(DerivedRuntimeBudget {
            max_joint_state_bytes: self.max_fabric_bytes - FABRIC_FIXED_BYTES,
            max_joint_working_bytes,
            admitted_predecessor_envelope_bytes: self.max_envelope_bytes,
            admitted_successor_envelope_bytes: self.max_envelope_bytes,
            admitted_logical_peak_bytes: self.max_logical_peak_bytes,
        })
    }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) struct DerivedRuntimeBudget {
    pub(crate) max_joint_state_bytes: usize,
    pub(crate) max_joint_working_bytes: usize,
    pub(crate) admitted_predecessor_envelope_bytes: usize,
    pub(crate) admitted_successor_envelope_bytes: usize,
    pub(crate) admitted_logical_peak_bytes: usize,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) enum RuntimeError {
    InvalidBudget,
    BudgetArithmeticOverflow,
    EnvelopeBudgetExceeded,
    FabricBudgetExceeded,
    EnvelopeEndedEarly,
    BadEnvelopeMagic,
    UnsupportedEnvelopeVersion(u16),
    InvalidIdentity,
    FabricLengthOverflow,
    FabricLengthMismatch,
    BadFabricMagic,
    UnsupportedFabricVersion(u16),
    OrganismTickOverflow,
    FabricGenerationOverflow,
    MountedGenerationDiscontinuity,
    MountedSourceSubstitution,
    MountedTransition(String),
    LegacyMigration(String),
    Task853LegacyReceiptMismatch,
    Task853IdentityMismatch,
    Task853TickMismatch,
    MigrationInvariantChanged,
    PendingCandidateExists,
    PendingCandidateMissing,
    PendingTokenMismatch,
    PrepareTokenOrdinalOverflow,
    ResidentMountedInvariantChanged,
    CognitiveFormation(String),
    HippocampalColdCustodyMissing,
    SealedStateChanged,
}

impl fmt::Display for RuntimeError {
    fn fmt(&self, output: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::InvalidBudget => write!(
                output,
                "organism runtime budget is not structurally sufficient"
            ),
            Self::BudgetArithmeticOverflow => {
                write!(output, "organism runtime budget arithmetic overflow")
            }
            Self::EnvelopeBudgetExceeded => {
                write!(output, "organism runtime envelope exceeds admitted bytes")
            }
            Self::FabricBudgetExceeded => {
                write!(output, "organism runtime fabric exceeds admitted bytes")
            }
            Self::EnvelopeEndedEarly => write!(output, "organism runtime envelope ended early"),
            Self::BadEnvelopeMagic => write!(output, "organism runtime envelope is not GLORUN01"),
            Self::UnsupportedEnvelopeVersion(version) => {
                write!(output, "unsupported organism runtime version {version}")
            }
            Self::InvalidIdentity => write!(output, "organism identity is not canonical UUID text"),
            Self::FabricLengthOverflow => {
                write!(output, "organism fabric length exceeds its canonical width")
            }
            Self::FabricLengthMismatch => write!(
                output,
                "organism runtime fabric length or trailing bytes changed"
            ),
            Self::BadFabricMagic => {
                write!(output, "organism fabric is neither GLMFAB07 nor GLMFAB04")
            }
            Self::UnsupportedFabricVersion(version) => {
                write!(output, "unsupported materialized fabric version {version}")
            }
            Self::OrganismTickOverflow => write!(output, "organism tick overflow"),
            Self::FabricGenerationOverflow => {
                write!(output, "materialized fabric generation overflow")
            }
            Self::MountedGenerationDiscontinuity => write!(
                output,
                "mounted joint-DSF generation is not locally contiguous"
            ),
            Self::MountedSourceSubstitution => {
                write!(output, "mounted joint-DSF source authority changed")
            }
            Self::MountedTransition(reason) => {
                write!(output, "mounted joint-DSF transition failed: {reason}")
            }
            Self::LegacyMigration(reason) => {
                write!(output, "authenticated legacy migration failed: {reason}")
            }
            Self::Task853LegacyReceiptMismatch => write!(
                output,
                "authenticated legacy receipt is not the task-853 predecessor receipt"
            ),
            Self::Task853IdentityMismatch => write!(
                output,
                "organism identity is not the authenticated task-853 identity"
            ),
            Self::Task853TickMismatch => write!(
                output,
                "organism tick is not the authenticated task-853 predecessor tick"
            ),
            Self::MigrationInvariantChanged => write!(
                output,
                "authenticated migration changed retained current-state authority"
            ),
            Self::PendingCandidateExists => {
                write!(
                    output,
                    "resident organism already has one pending candidate"
                )
            }
            Self::PendingCandidateMissing => {
                write!(output, "resident organism has no pending candidate")
            }
            Self::PendingTokenMismatch => {
                write!(output, "resident organism pending token does not match")
            }
            Self::PrepareTokenOrdinalOverflow => {
                write!(output, "resident organism prepare-token ordinal overflow")
            }
            Self::ResidentMountedInvariantChanged => write!(
                output,
                "resident mounted preparation violated decode, field, or clock continuity"
            ),
            Self::CognitiveFormation(reason) => {
                write!(output, "resident cognitive formation failed: {reason}")
            }
            Self::HippocampalColdCustodyMissing => write!(
                output,
                "resident cognition requires an external hippocampal cold-custody port"
            ),
            Self::SealedStateChanged => write!(
                output,
                "organism runtime state changed outside its admitted step"
            ),
        }
    }
}

impl std::error::Error for RuntimeError {}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) struct RuntimeObservation {
    pub(crate) schema: &'static str,
    pub(crate) scope: &'static str,
    pub(crate) identity: [u8; IDENTITY_BYTES],
    pub(crate) predecessor_state_receipt: Option<[u8; 32]>,
    pub(crate) predecessor_organism_tick: Option<u64>,
    pub(crate) organism_tick: u64,
    pub(crate) predecessor_fabric_generation: Option<u64>,
    pub(crate) fabric_generation: u64,
    pub(crate) predecessor_mounted_generation: Option<u64>,
    pub(crate) mounted_generation: u64,
    pub(crate) state_bytes: usize,
    pub(crate) state_receipt: [u8; 32],
    pub(crate) fabric_bytes: usize,
    pub(crate) fabric_receipt: [u8; 32],
    pub(crate) joint_field_count: usize,
    pub(crate) joint_neuron_count: usize,
    pub(crate) dsf_delivery_count: usize,
    pub(crate) complete_neuron_count: usize,
    pub(crate) physically_transitioned_neuron_count: usize,
    pub(crate) complete_neuron_fractal_count: usize,
    pub(crate) recurrent_complete_neuron_fractal_count: usize,
    pub(crate) source_cohort_l0_l4_evaluation_count: usize,
    pub(crate) successor_l0_l4_replay_count: usize,
    pub(crate) joint_transition_receipt: Option<[u8; 32]>,
    pub(crate) episode_relation_candidate_receipt: Option<[u8; 32]>,
    pub(crate) source_authority: Option<[u8; 32]>,
    pub(crate) mounted_step_completed: bool,
    pub(crate) physical_transition_claimed: bool,
    pub(crate) cognitive_formation_claimed: bool,
    pub(crate) cognitive_ordinal: u64,
    pub(crate) cognitive_trace_count: usize,
    pub(crate) cognitive_mosaic_count: usize,
    pub(crate) formation_activation_count: usize,
    pub(crate) partial_cue_reassembly_count: usize,
    pub(crate) python_callback_count: u64,
    pub(crate) derived_budget: DerivedRuntimeBudget,
}

#[derive(Debug, Eq, PartialEq)]
pub(crate) struct SealedRuntimeState {
    pub(crate) bytes: Vec<u8>,
    pub(crate) receipt: [u8; 32],
}

#[derive(Debug, Eq, PartialEq)]
pub(crate) struct RuntimeStepResult {
    pub(crate) successor: SealedRuntimeState,
    pub(crate) observation: RuntimeObservation,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct NativeResidentD3Transition {
    successor: Vec<u8>,
    state_receipt: [u8; 32],
    source_authority: [u8; 32],
    complete_neuron_count: usize,
    complete_neuron_fractal_count: usize,
    cognitive_mosaic_count: usize,
    partial_cue_reassembly_count: usize,
}

impl NativeResidentD3Transition {
    pub fn successor(&self) -> &[u8] {
        &self.successor
    }

    pub fn state_receipt(&self) -> [u8; 32] {
        self.state_receipt
    }

    pub fn source_authority(&self) -> [u8; 32] {
        self.source_authority
    }

    pub fn complete_neuron_count(&self) -> usize {
        self.complete_neuron_count
    }

    pub fn complete_neuron_fractal_count(&self) -> usize {
        self.complete_neuron_fractal_count
    }

    pub fn cognitive_mosaic_count(&self) -> usize {
        self.cognitive_mosaic_count
    }

    pub fn partial_cue_reassembly_count(&self) -> usize {
        self.partial_cue_reassembly_count
    }

    pub fn python_callback_count(&self) -> u64 {
        0
    }
}

#[pyclass(frozen, module = "guala_core")]
pub struct NativeOrganismRuntimeTransition {
    payload: Arc<[u8]>,
    observation: RuntimeObservation,
}

#[derive(Debug, Eq, PartialEq)]
struct AuthenticatedTask853RuntimeMigration {
    sealed: SealedRuntimeState,
    observation: RuntimeObservation,
    legacy_fabric_receipt: [u8; 32],
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
struct LegacyMigrationAuthority {
    identity: &'static str,
    organism_tick: u64,
    fabric_receipt: [u8; 32],
    fabric_generation: u64,
    mounted_generation: u64,
}

#[derive(Debug, Eq, PartialEq)]
struct ActiveResidentOrganismState {
    envelope: Vec<u8>,
    mounted: ResidentMountedState,
    cognitive: ResidentCognitiveFormationState,
    observation: RuntimeObservation,
}

#[derive(Debug, Eq, PartialEq)]
struct PendingResidentOrganismState {
    token: [u8; 32],
    envelope: Vec<u8>,
    mounted: ResidentMountedState,
    cognitive: PreparedCognitiveFormationTransition,
    observation: RuntimeObservation,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
struct ResidentPrepareReceipt {
    token: [u8; 32],
    observation: RuntimeObservation,
    phase_counts: MountedTransitionPhaseCounts,
    receptor_ingress: ResidentReceptorIngressObservation,
}

#[derive(Debug, Eq, PartialEq)]
struct ResidentOrganismRuntime {
    active: ActiveResidentOrganismState,
    pending: Option<PendingResidentOrganismState>,
    budget: RuntimeBudget,
    next_prepare_ordinal: u64,
}

#[pyclass(module = "guala_core")]
pub struct NativeResidentOrganismRuntime {
    runtime: ResidentOrganismRuntime,
}

#[pyclass(frozen, module = "guala_core")]
pub struct NativeResidentOrganismObservation {
    observation: RuntimeObservation,
    cold_restore_work: ResidentMountedRestoreWork,
}

#[pyclass(frozen, module = "guala_core")]
pub struct NativeResidentOrganismPrepare {
    token: [u8; 32],
    observation: RuntimeObservation,
    phase_counts: MountedTransitionPhaseCounts,
    receptor_ingress: ResidentReceptorIngressObservation,
}

#[pyclass(frozen, module = "guala_core")]
pub struct NativeAuthenticatedTask853RuntimeMigration {
    payload: Arc<[u8]>,
    observation: RuntimeObservation,
    legacy_fabric_receipt: [u8; 32],
}

#[pymethods]
impl NativeAuthenticatedTask853RuntimeMigration {
    #[getter]
    fn schema(&self) -> &'static str {
        MIGRATION_SCHEMA
    }

    #[getter]
    fn scope(&self) -> &'static str {
        MIGRATION_SCOPE
    }

    #[getter]
    fn identity(&self) -> String {
        std::str::from_utf8(&self.observation.identity)
            .expect("validated canonical organism identity")
            .to_owned()
    }

    #[getter]
    fn authenticated_predecessor_organism_tick(&self) -> u64 {
        self.observation.organism_tick
    }

    #[getter]
    fn organism_tick(&self) -> u64 {
        self.observation.organism_tick
    }

    #[getter]
    fn legacy_fabric_sha256(&self) -> String {
        hex_digest(&self.legacy_fabric_receipt)
    }

    #[getter]
    fn state_bytes(&self) -> usize {
        self.observation.state_bytes
    }

    #[getter]
    fn state_sha256(&self) -> String {
        hex_digest(&self.observation.state_receipt)
    }

    #[getter]
    fn fabric_bytes(&self) -> usize {
        self.observation.fabric_bytes
    }

    #[getter]
    fn fabric_sha256(&self) -> String {
        hex_digest(&self.observation.fabric_receipt)
    }

    #[getter]
    fn fabric_generation(&self) -> u64 {
        self.observation.fabric_generation
    }

    #[getter]
    fn mounted_generation(&self) -> u64 {
        self.observation.mounted_generation
    }

    #[getter]
    fn joint_field_count(&self) -> usize {
        self.observation.joint_field_count
    }

    #[getter]
    fn joint_neuron_count(&self) -> usize {
        self.observation.joint_neuron_count
    }

    #[getter]
    fn complete_neuron_count(&self) -> usize {
        self.observation.complete_neuron_count
    }

    #[getter]
    fn physically_transitioned_neuron_count(&self) -> usize {
        self.observation.physically_transitioned_neuron_count
    }

    #[getter]
    fn mounted_step_completed(&self) -> bool {
        false
    }

    #[getter]
    fn physical_transition_claimed(&self) -> bool {
        false
    }

    #[getter]
    fn cognitive_formation_claimed(&self) -> bool {
        false
    }

    #[getter]
    fn python_callback_count(&self) -> u64 {
        0
    }

    fn as_bytes<'py>(&self, py: Python<'py>) -> Bound<'py, PyBytes> {
        PyBytes::new(py, &self.payload)
    }
}

#[pymethods]
impl NativeResidentOrganismObservation {
    #[getter]
    fn schema(&self) -> &'static str {
        RESIDENT_OBSERVATION_SCHEMA
    }

    #[getter]
    fn identity(&self) -> String {
        std::str::from_utf8(&self.observation.identity)
            .expect("validated canonical organism identity")
            .to_owned()
    }

    #[getter]
    fn organism_tick(&self) -> u64 {
        self.observation.organism_tick
    }

    #[getter]
    fn fabric_generation(&self) -> u64 {
        self.observation.fabric_generation
    }

    #[getter]
    fn mounted_generation(&self) -> u64 {
        self.observation.mounted_generation
    }

    #[getter]
    fn state_bytes(&self) -> usize {
        self.observation.state_bytes
    }

    #[getter]
    fn state_sha256(&self) -> String {
        hex_digest(&self.observation.state_receipt)
    }

    #[getter]
    fn fabric_bytes(&self) -> usize {
        self.observation.fabric_bytes
    }

    #[getter]
    fn fabric_sha256(&self) -> String {
        hex_digest(&self.observation.fabric_receipt)
    }

    #[getter]
    fn joint_field_count(&self) -> usize {
        self.observation.joint_field_count
    }

    #[getter]
    fn joint_neuron_count(&self) -> usize {
        self.observation.joint_neuron_count
    }

    #[getter]
    fn complete_neuron_count(&self) -> usize {
        self.observation.complete_neuron_count
    }

    #[getter]
    fn physically_transitioned_neuron_count(&self) -> usize {
        self.observation.physically_transitioned_neuron_count
    }

    #[getter]
    fn cold_restore_authentication_count(&self) -> usize {
        self.cold_restore_work.authentication_count
    }

    #[getter]
    fn cold_restore_decode_count(&self) -> usize {
        self.cold_restore_work.decode_count
    }

    #[getter]
    fn cold_restore_rebuilt_field_count(&self) -> usize {
        self.cold_restore_work.rebuilt_predecessor_field_count
    }

    #[getter]
    fn mounted_step_completed(&self) -> bool {
        self.observation.mounted_step_completed
    }

    #[getter]
    fn physical_transition_claimed(&self) -> bool {
        self.observation.physical_transition_claimed
    }

    #[getter]
    fn cognitive_formation_claimed(&self) -> bool {
        self.observation.cognitive_formation_claimed
    }

    #[getter]
    fn cognitive_ordinal(&self) -> u64 {
        self.observation.cognitive_ordinal
    }

    #[getter]
    fn cognitive_trace_count(&self) -> usize {
        self.observation.cognitive_trace_count
    }

    #[getter]
    fn cognitive_mosaic_count(&self) -> usize {
        self.observation.cognitive_mosaic_count
    }

    #[getter]
    fn formation_activation_count(&self) -> usize {
        self.observation.formation_activation_count
    }

    #[getter]
    fn partial_cue_reassembly_count(&self) -> usize {
        self.observation.partial_cue_reassembly_count
    }

    #[getter]
    fn python_callback_count(&self) -> u64 {
        self.observation.python_callback_count
    }
}

#[pymethods]
impl NativeResidentOrganismPrepare {
    #[getter]
    fn schema(&self) -> &'static str {
        RESIDENT_PREPARE_SCHEMA
    }

    #[getter]
    fn token<'py>(&self, py: Python<'py>) -> Bound<'py, PyBytes> {
        PyBytes::new(py, &self.token)
    }

    #[getter]
    fn token_hex(&self) -> String {
        hex_digest(&self.token)
    }

    #[getter]
    fn predecessor_state_sha256(&self) -> Option<String> {
        self.observation
            .predecessor_state_receipt
            .as_ref()
            .map(hex_digest)
    }

    #[getter]
    fn prepared_state_sha256(&self) -> String {
        hex_digest(&self.observation.state_receipt)
    }

    #[getter]
    fn predecessor_organism_tick(&self) -> Option<u64> {
        self.observation.predecessor_organism_tick
    }

    #[getter]
    fn organism_tick(&self) -> u64 {
        self.observation.organism_tick
    }

    #[getter]
    fn predecessor_fabric_generation(&self) -> Option<u64> {
        self.observation.predecessor_fabric_generation
    }

    #[getter]
    fn fabric_generation(&self) -> u64 {
        self.observation.fabric_generation
    }

    #[getter]
    fn predecessor_mounted_generation(&self) -> Option<u64> {
        self.observation.predecessor_mounted_generation
    }

    #[getter]
    fn mounted_generation(&self) -> u64 {
        self.observation.mounted_generation
    }

    #[getter]
    fn predecessor_authentication_count(&self) -> usize {
        self.phase_counts.predecessor_authentication_count
    }

    #[getter]
    fn predecessor_decode_count(&self) -> usize {
        self.phase_counts.predecessor_decode_count
    }

    #[getter]
    fn predecessor_rebuilt_field_count(&self) -> usize {
        self.phase_counts.predecessor_rebuilt_field_count
    }

    #[getter]
    fn current_cohort_evaluation_count(&self) -> usize {
        self.phase_counts.current_cohort_evaluation_count
    }

    #[getter]
    fn successor_seal_count(&self) -> usize {
        self.phase_counts.successor_seal_count
    }

    #[getter]
    fn receptor_ingress_field_count(&self) -> usize {
        self.receptor_ingress.field_count()
    }

    #[getter]
    fn receptor_ingress_witness_count(&self) -> usize {
        self.receptor_ingress.witness_count()
    }

    #[getter]
    fn receptor_ingress_sense_counts(&self) -> (usize, usize, usize, usize, usize, usize) {
        let counts = self.receptor_ingress.sense_counts();
        (
            counts[0], counts[1], counts[2], counts[3], counts[4], counts[5],
        )
    }

    #[getter]
    fn receptor_ingress_changing_count(&self) -> usize {
        self.receptor_ingress.changing_count()
    }

    #[getter]
    fn receptor_ingress_quiescent_count(&self) -> usize {
        self.receptor_ingress.quiescent_count()
    }

    #[getter]
    fn receptor_ingress_reached_neuron_visit_count(&self) -> usize {
        self.receptor_ingress.reached_neuron_visit_count()
    }

    #[getter]
    fn receptor_ingress_witness_construction_count(&self) -> usize {
        self.receptor_ingress.witness_construction_count()
    }

    #[getter]
    fn dsf_delivery_count(&self) -> usize {
        self.observation.dsf_delivery_count
    }

    #[getter]
    fn complete_neuron_fractal_count(&self) -> usize {
        self.observation.complete_neuron_fractal_count
    }

    #[getter]
    fn complete_neuron_count(&self) -> usize {
        self.observation.complete_neuron_count
    }

    #[getter]
    fn physically_transitioned_neuron_count(&self) -> usize {
        self.observation.physically_transitioned_neuron_count
    }

    #[getter]
    fn recurrent_complete_neuron_fractal_count(&self) -> usize {
        self.observation.recurrent_complete_neuron_fractal_count
    }

    #[getter]
    fn physical_transition_claimed(&self) -> bool {
        self.observation.physical_transition_claimed
    }

    #[getter]
    fn cognitive_formation_claimed(&self) -> bool {
        self.observation.cognitive_formation_claimed
    }

    #[getter]
    fn cognitive_ordinal(&self) -> u64 {
        self.observation.cognitive_ordinal
    }

    #[getter]
    fn cognitive_trace_count(&self) -> usize {
        self.observation.cognitive_trace_count
    }

    #[getter]
    fn cognitive_mosaic_count(&self) -> usize {
        self.observation.cognitive_mosaic_count
    }

    #[getter]
    fn formation_activation_count(&self) -> usize {
        self.observation.formation_activation_count
    }

    #[getter]
    fn partial_cue_reassembly_count(&self) -> usize {
        self.observation.partial_cue_reassembly_count
    }

    #[getter]
    fn python_callback_count(&self) -> u64 {
        0
    }
}

#[pymethods]
impl NativeOrganismRuntimeTransition {
    #[getter]
    fn schema(&self) -> &'static str {
        self.observation.schema
    }

    #[getter]
    fn scope(&self) -> &'static str {
        self.observation.scope
    }

    #[getter]
    fn identity(&self) -> String {
        std::str::from_utf8(&self.observation.identity)
            .expect("validated canonical organism identity")
            .to_owned()
    }

    #[getter]
    fn predecessor_state_sha256(&self) -> Option<String> {
        self.observation
            .predecessor_state_receipt
            .as_ref()
            .map(hex_digest)
    }

    #[getter]
    fn predecessor_organism_tick(&self) -> Option<u64> {
        self.observation.predecessor_organism_tick
    }

    #[getter]
    fn organism_tick(&self) -> u64 {
        self.observation.organism_tick
    }

    #[getter]
    fn predecessor_fabric_generation(&self) -> Option<u64> {
        self.observation.predecessor_fabric_generation
    }

    #[getter]
    fn fabric_generation(&self) -> u64 {
        self.observation.fabric_generation
    }

    #[getter]
    fn predecessor_mounted_generation(&self) -> Option<u64> {
        self.observation.predecessor_mounted_generation
    }

    #[getter]
    fn mounted_generation(&self) -> u64 {
        self.observation.mounted_generation
    }

    #[getter]
    fn state_bytes(&self) -> usize {
        self.observation.state_bytes
    }

    #[getter]
    fn state_sha256(&self) -> String {
        hex_digest(&self.observation.state_receipt)
    }

    #[getter]
    fn fabric_bytes(&self) -> usize {
        self.observation.fabric_bytes
    }

    #[getter]
    fn fabric_sha256(&self) -> String {
        hex_digest(&self.observation.fabric_receipt)
    }

    #[getter]
    fn joint_field_count(&self) -> usize {
        self.observation.joint_field_count
    }

    #[getter]
    fn joint_neuron_count(&self) -> usize {
        self.observation.joint_neuron_count
    }

    #[getter]
    fn dsf_delivery_count(&self) -> usize {
        self.observation.dsf_delivery_count
    }

    #[getter]
    fn complete_neuron_fractal_count(&self) -> usize {
        self.observation.complete_neuron_fractal_count
    }

    #[getter]
    fn complete_neuron_count(&self) -> usize {
        self.observation.complete_neuron_count
    }

    #[getter]
    fn physically_transitioned_neuron_count(&self) -> usize {
        self.observation.physically_transitioned_neuron_count
    }

    #[getter]
    fn recurrent_complete_neuron_fractal_count(&self) -> usize {
        self.observation.recurrent_complete_neuron_fractal_count
    }

    #[getter]
    fn source_cohort_l0_l4_evaluation_count(&self) -> usize {
        self.observation.source_cohort_l0_l4_evaluation_count
    }

    #[getter]
    fn successor_l0_l4_replay_count(&self) -> usize {
        self.observation.successor_l0_l4_replay_count
    }

    #[getter]
    fn joint_transition_sha256(&self) -> Option<String> {
        self.observation
            .joint_transition_receipt
            .as_ref()
            .map(hex_digest)
    }

    #[getter]
    fn episode_relation_candidate_sha256(&self) -> Option<String> {
        self.observation
            .episode_relation_candidate_receipt
            .as_ref()
            .map(hex_digest)
    }

    #[getter]
    fn source_sha256(&self) -> Option<String> {
        self.observation.source_authority.as_ref().map(hex_digest)
    }

    #[getter]
    fn mounted_step_completed(&self) -> bool {
        self.observation.mounted_step_completed
    }

    #[getter]
    fn physical_transition_claimed(&self) -> bool {
        self.observation.physical_transition_claimed
    }

    #[getter]
    fn cognitive_formation_claimed(&self) -> bool {
        self.observation.cognitive_formation_claimed
    }

    #[getter]
    fn cognitive_ordinal(&self) -> u64 {
        self.observation.cognitive_ordinal
    }

    #[getter]
    fn cognitive_trace_count(&self) -> usize {
        self.observation.cognitive_trace_count
    }

    #[getter]
    fn cognitive_mosaic_count(&self) -> usize {
        self.observation.cognitive_mosaic_count
    }

    #[getter]
    fn formation_activation_count(&self) -> usize {
        self.observation.formation_activation_count
    }

    #[getter]
    fn partial_cue_reassembly_count(&self) -> usize {
        self.observation.partial_cue_reassembly_count
    }

    #[getter]
    fn python_callback_count(&self) -> u64 {
        self.observation.python_callback_count
    }

    #[getter]
    fn derived_budget(&self) -> (usize, usize, usize, usize, usize) {
        let budget = self.observation.derived_budget;
        (
            budget.max_joint_state_bytes,
            budget.max_joint_working_bytes,
            budget.admitted_predecessor_envelope_bytes,
            budget.admitted_successor_envelope_bytes,
            budget.admitted_logical_peak_bytes,
        )
    }

    fn as_bytes<'py>(&self, py: Python<'py>) -> Bound<'py, PyBytes> {
        PyBytes::new(py, &self.payload)
    }
}

impl ResidentOrganismRuntime {
    fn restore_envelope(envelope: Vec<u8>, budget: RuntimeBudget) -> Result<Self, RuntimeError> {
        let derived_budget = budget.derive()?;
        let (mounted, cognitive, observation) = {
            let parsed = parse_current_envelope(&envelope, budget)?;
            let (mounted, summary) = restore_resident_mounted_state(
                parsed.joint_bytes,
                derived_budget.max_joint_state_bytes,
                derived_budget.max_joint_working_bytes,
            )
            .map_err(RuntimeError::MountedTransition)?;
            let cognitive = restore_cognitive_state(&parsed, budget)?;
            let observation = make_restored_observation(
                &envelope,
                parsed,
                summary,
                cognitive.summary(),
                derived_budget,
            );
            (mounted, cognitive, observation)
        };
        Ok(Self {
            active: ActiveResidentOrganismState {
                envelope,
                mounted,
                cognitive,
                observation,
            },
            pending: None,
            budget,
            next_prepare_ordinal: 1,
        })
    }

    fn prepare_with_cold(
        &mut self,
        source: &NativeJointSourceEpisode,
        cold: Option<&mut dyn HippocampalColdPort>,
    ) -> Result<ResidentPrepareReceipt, RuntimeError> {
        if self.pending.is_some() {
            return Err(RuntimeError::PendingCandidateExists);
        }
        let cold = cold.ok_or(RuntimeError::HippocampalColdCustodyMissing)?;
        let derived_budget = self.budget.derive()?;
        let predecessor = self.active.observation;
        let organism_tick = predecessor
            .organism_tick
            .checked_add(1)
            .ok_or(RuntimeError::OrganismTickOverflow)?;
        let fabric_generation = predecessor
            .fabric_generation
            .checked_add(1)
            .ok_or(RuntimeError::FabricGenerationOverflow)?;
        let admitted_source_authority = source.joint_source_authority_receipt();
        let admitted_source_body = source.joint_source_body();
        let prepared = prepare_resident_mounted_generation(
            &self.active.mounted,
            source,
            derived_budget.max_joint_state_bytes,
            derived_budget.max_joint_working_bytes,
        )
        .map_err(RuntimeError::MountedTransition)?;
        let receptor_ingress = prepare_resident_receptor_ingress(&prepared);
        let cognitive_occurrence = CognitiveOccurrence::from_mounted(&prepared, source)
            .map_err(|error| RuntimeError::CognitiveFormation(error.to_string()))?;
        let phase_counts = prepared.phase_counts();
        let dsf_delivery_count = prepared
            .fields()
            .iter()
            .try_fold(0usize, |count, field| {
                count.checked_add(field.neurons().len())
            })
            .ok_or(RuntimeError::BudgetArithmeticOverflow)?;
        if prepared.predecessor_generation() != predecessor.mounted_generation
            || prepared.predecessor_generation().checked_add(1)
                != Some(prepared.successor_generation())
            || prepared.source_authority() != admitted_source_authority
            || prepared.source_body() != admitted_source_body.as_ref()
            || phase_counts.predecessor_authentication_count != 0
            || phase_counts.predecessor_decode_count != 0
            || phase_counts.predecessor_rebuilt_field_count != 0
            || phase_counts.current_cohort_evaluation_count != prepared.fields().len()
            || phase_counts.current_cohort_evaluation_count
                != prepared.transition().l0_l4_evaluation_count
            || dsf_delivery_count != prepared.transition().dsf_delivery_count
            || prepared.successor_resident_state().summary().generation
                != prepared.successor_generation()
        {
            return Err(RuntimeError::ResidentMountedInvariantChanged);
        }
        let successor_mounted_generation = prepared.successor_generation();
        let cognitive_budget =
            cognitive_budget_after_joint(prepared.state_bytes().len(), self.budget)?;
        let mut cognitive = self
            .active
            .cognitive
            .prepare_with_hippocampal_cold(&cognitive_occurrence, source, cold, cognitive_budget)
            .map_err(|error| RuntimeError::CognitiveFormation(error.to_string()))?;
        let cognitive_state = self
            .active
            .cognitive
            .publish_hippocampal_and_encode_successor(&mut cognitive, cold, cognitive_budget)
            .map_err(|error| RuntimeError::CognitiveFormation(error.to_string()))?;
        let cognitive_observation = cognitive.observation().clone();
        let (mounted, joint_state, transition) = prepared.into_resident_parts();
        let fabric = encode_fabric(
            fabric_generation,
            &joint_state,
            &cognitive_state,
            self.budget,
        )?;
        let envelope = encode_envelope(predecessor.identity, organism_tick, &fabric, self.budget)?;
        let observation = make_step_observation(
            &envelope,
            predecessor.identity,
            predecessor.organism_tick,
            organism_tick,
            predecessor.fabric_generation,
            fabric_generation,
            predecessor.mounted_generation,
            successor_mounted_generation,
            &fabric,
            admitted_source_authority,
            transition,
            phase_counts.current_cohort_evaluation_count,
            derived_budget,
            predecessor.state_receipt,
            &cognitive_observation,
        );
        let next_prepare_ordinal = self
            .next_prepare_ordinal
            .checked_add(1)
            .ok_or(RuntimeError::PrepareTokenOrdinalOverflow)?;
        let token = prepare_token(
            predecessor.state_receipt,
            observation.state_receipt,
            admitted_source_authority,
            self.next_prepare_ordinal,
        );
        self.pending = Some(PendingResidentOrganismState {
            token,
            envelope,
            mounted,
            cognitive,
            observation,
        });
        self.next_prepare_ordinal = next_prepare_ordinal;
        Ok(ResidentPrepareReceipt {
            token,
            observation,
            phase_counts,
            receptor_ingress,
        })
    }

    #[cfg(test)]
    fn prepare(
        &mut self,
        source: &NativeJointSourceEpisode,
    ) -> Result<ResidentPrepareReceipt, RuntimeError> {
        let mut cold = HippocampalColdStore::default();
        self.prepare_with_cold(source, Some(&mut cold))
    }

    fn commit(&mut self, token: [u8; 32]) -> Result<(), RuntimeError> {
        let pending = self
            .pending
            .as_ref()
            .ok_or(RuntimeError::PendingCandidateMissing)?;
        if pending.token != token {
            return Err(RuntimeError::PendingTokenMismatch);
        }
        let pending = self
            .pending
            .take()
            .expect("validated resident pending candidate");
        self.active
            .cognitive
            .commit(pending.cognitive)
            .map_err(|error| RuntimeError::CognitiveFormation(error.to_string()))?;
        self.active.envelope = pending.envelope;
        self.active.mounted = pending.mounted;
        self.active.observation = pending.observation;
        Ok(())
    }

    fn discard(&mut self, token: [u8; 32]) -> Result<(), RuntimeError> {
        let pending = self
            .pending
            .as_ref()
            .ok_or(RuntimeError::PendingCandidateMissing)?;
        if pending.token != token {
            return Err(RuntimeError::PendingTokenMismatch);
        }
        self.pending = None;
        Ok(())
    }

    fn observation(&self) -> RuntimeObservation {
        self.active.observation
    }

    fn cold_restore_work(&self) -> ResidentMountedRestoreWork {
        self.active.mounted.cold_restore_work()
    }

    fn active_envelope(&self) -> &[u8] {
        &self.active.envelope
    }
}

fn prepare_token(
    predecessor_receipt: [u8; 32],
    successor_receipt: [u8; 32],
    source_authority: [u8; 32],
    prepare_ordinal: u64,
) -> [u8; 32] {
    let mut body = [0_u8; 112];
    body[..8].copy_from_slice(PREPARE_TOKEN_MAGIC);
    body[8..40].copy_from_slice(&predecessor_receipt);
    body[40..72].copy_from_slice(&successor_receipt);
    body[72..104].copy_from_slice(&source_authority);
    body[104..112].copy_from_slice(&prepare_ordinal.to_le_bytes());
    sha256(&body)
}

fn exact_token(value: Vec<u8>) -> Result<[u8; 32], PyErr> {
    value
        .try_into()
        .map_err(|_| PyValueError::new_err("resident organism token must contain exactly 32 bytes"))
}

fn native_resident_observation(
    runtime: &ResidentOrganismRuntime,
) -> NativeResidentOrganismObservation {
    NativeResidentOrganismObservation {
        observation: runtime.observation(),
        cold_restore_work: runtime.cold_restore_work(),
    }
}

#[pymethods]
impl NativeResidentOrganismRuntime {
    #[getter]
    fn schema(&self) -> &'static str {
        RESIDENT_RUNTIME_SCHEMA
    }

    fn prepare(
        &mut self,
        py: Python<'_>,
        source: PyRef<'_, NativeJointSourceEpisode>,
    ) -> PyResult<NativeResidentOrganismPrepare> {
        let source = source.clone();
        let prepared = py
            .allow_threads(|| self.runtime.prepare_with_cold(&source, None))
            .map_err(|error| PyValueError::new_err(error.to_string()))?;
        Ok(NativeResidentOrganismPrepare {
            token: prepared.token,
            observation: prepared.observation,
            phase_counts: prepared.phase_counts,
            receptor_ingress: prepared.receptor_ingress,
        })
    }

    fn commit(&mut self, token: Vec<u8>) -> PyResult<()> {
        let token = exact_token(token)?;
        self.runtime
            .commit(token)
            .map_err(|error| PyValueError::new_err(error.to_string()))?;
        Ok(())
    }

    fn discard(&mut self, token: Vec<u8>) -> PyResult<()> {
        let token = exact_token(token)?;
        self.runtime
            .discard(token)
            .map_err(|error| PyValueError::new_err(error.to_string()))?;
        Ok(())
    }

    fn readiness(&self) -> NativeResidentOrganismObservation {
        native_resident_observation(&self.runtime)
    }

    fn save<'py>(&self, py: Python<'py>) -> Bound<'py, PyBytes> {
        PyBytes::new(py, self.runtime.active_envelope())
    }
}

#[pyfunction]
#[pyo3(signature = (
    current_envelope,
    max_envelope_bytes=67_108_864,
    max_fabric_bytes=67_108_000,
    max_logical_peak_bytes=536_870_912
))]
fn restore_native_resident_organism_runtime(
    py: Python<'_>,
    current_envelope: Vec<u8>,
    max_envelope_bytes: usize,
    max_fabric_bytes: usize,
    max_logical_peak_bytes: usize,
) -> PyResult<NativeResidentOrganismRuntime> {
    let runtime = py
        .allow_threads(move || {
            let budget =
                RuntimeBudget::new(max_envelope_bytes, max_fabric_bytes, max_logical_peak_bytes)?;
            ResidentOrganismRuntime::restore_envelope(current_envelope, budget)
        })
        .map_err(|error| PyValueError::new_err(error.to_string()))?;
    Ok(NativeResidentOrganismRuntime { runtime })
}

#[pyfunction]
#[pyo3(signature = (
    organism_identity,
    organism_tick=0,
    max_envelope_bytes=67_108_864,
    max_fabric_bytes=67_108_000,
    max_logical_peak_bytes=536_870_912
))]
fn create_native_resident_organism_runtime(
    py: Python<'_>,
    organism_identity: String,
    organism_tick: u64,
    max_envelope_bytes: usize,
    max_fabric_bytes: usize,
    max_logical_peak_bytes: usize,
) -> PyResult<NativeResidentOrganismRuntime> {
    let runtime = py
        .allow_threads(move || {
            let budget =
                RuntimeBudget::new(max_envelope_bytes, max_fabric_bytes, max_logical_peak_bytes)?;
            create_resident_genesis(&organism_identity, organism_tick, budget)
        })
        .map_err(|error| PyValueError::new_err(error.to_string()))?;
    Ok(NativeResidentOrganismRuntime { runtime })
}

fn create_resident_genesis(
    organism_identity: &str,
    organism_tick: u64,
    budget: RuntimeBudget,
) -> Result<ResidentOrganismRuntime, RuntimeError> {
    let identity = canonical_identity(organism_identity)?;
    let joint = encode_empty_mounted_joint_state().map_err(RuntimeError::MountedTransition)?;
    let cognitive = ResidentCognitiveFormationState::default()
        .encode(cognitive_budget_after_joint(joint.len(), budget)?)
        .map_err(|error| RuntimeError::CognitiveFormation(error.to_string()))?;
    let fabric = encode_fabric(0, &joint, &cognitive, budget)?;
    let envelope = encode_envelope(identity, organism_tick, &fabric, budget)?;
    ResidentOrganismRuntime::restore_envelope(envelope, budget)
}

pub fn create_native_resident_d3_genesis(
    organism_identity: &str,
    organism_tick: u64,
    max_envelope_bytes: usize,
    max_fabric_bytes: usize,
    max_logical_peak_bytes: usize,
) -> Result<Vec<u8>, String> {
    let budget = RuntimeBudget::new(max_envelope_bytes, max_fabric_bytes, max_logical_peak_bytes)
        .map_err(|error| error.to_string())?;
    create_resident_genesis(organism_identity, organism_tick, budget)
        .map(|runtime| runtime.active_envelope().to_vec())
        .map_err(|error| error.to_string())
}

pub fn transition_native_resident_d3(
    current_envelope: Vec<u8>,
    source: &NativeJointSourceEpisode,
    cold: Option<&mut dyn HippocampalColdPort>,
    max_envelope_bytes: usize,
    max_fabric_bytes: usize,
    max_logical_peak_bytes: usize,
) -> Result<NativeResidentD3Transition, String> {
    let budget = RuntimeBudget::new(max_envelope_bytes, max_fabric_bytes, max_logical_peak_bytes)
        .map_err(|error| error.to_string())?;
    let mut runtime = ResidentOrganismRuntime::restore_envelope(current_envelope, budget)
        .map_err(|error| error.to_string())?;
    let prepared = runtime
        .prepare_with_cold(source, cold)
        .map_err(|error| error.to_string())?;
    runtime
        .commit(prepared.token)
        .map_err(|error| error.to_string())?;
    let observation = runtime.observation();
    let successor = runtime.active_envelope().to_vec();
    if sha256(&successor) != observation.state_receipt
        || observation.source_authority != Some(source.joint_source_authority_receipt())
        || observation.python_callback_count != 0
    {
        return Err(RuntimeError::SealedStateChanged.to_string());
    }
    Ok(NativeResidentD3Transition {
        successor,
        state_receipt: observation.state_receipt,
        source_authority: source.joint_source_authority_receipt(),
        complete_neuron_count: observation.complete_neuron_count,
        complete_neuron_fractal_count: observation.complete_neuron_fractal_count,
        cognitive_mosaic_count: observation.cognitive_mosaic_count,
        partial_cue_reassembly_count: observation.partial_cue_reassembly_count,
    })
}

#[pyfunction]
#[pyo3(signature = (
    prior_envelope,
    source,
    max_envelope_bytes=67_108_864,
    max_fabric_bytes=67_108_000,
    max_logical_peak_bytes=201_326_592
))]
fn transition_native_organism_runtime(
    py: Python<'_>,
    prior_envelope: Vec<u8>,
    source: PyRef<'_, NativeJointSourceEpisode>,
    max_envelope_bytes: usize,
    max_fabric_bytes: usize,
    max_logical_peak_bytes: usize,
) -> PyResult<NativeOrganismRuntimeTransition> {
    let source = source.clone();
    let result = py
        .allow_threads(move || {
            let budget =
                RuntimeBudget::new(max_envelope_bytes, max_fabric_bytes, max_logical_peak_bytes)?;
            OrganismRuntime::restore_envelope(prior_envelope, budget)?
                .advance_mounted(&source, budget)
        })
        .map_err(|error| PyValueError::new_err(error.to_string()))?;
    if result.observation.state_receipt != result.successor.receipt {
        return Err(PyValueError::new_err(
            RuntimeError::SealedStateChanged.to_string(),
        ));
    }
    Ok(NativeOrganismRuntimeTransition {
        payload: Arc::from(result.successor.bytes),
        observation: result.observation,
    })
}

#[pyfunction]
#[pyo3(signature = (
    current_envelope,
    max_envelope_bytes=67_108_864,
    max_fabric_bytes=67_108_000,
    max_logical_peak_bytes=201_326_592
))]
fn restore_native_organism_runtime(
    py: Python<'_>,
    current_envelope: Vec<u8>,
    max_envelope_bytes: usize,
    max_fabric_bytes: usize,
    max_logical_peak_bytes: usize,
) -> PyResult<NativeOrganismRuntimeTransition> {
    let result = py
        .allow_threads(move || {
            let budget =
                RuntimeBudget::new(max_envelope_bytes, max_fabric_bytes, max_logical_peak_bytes)?;
            let runtime = OrganismRuntime::restore_envelope(current_envelope, budget)?;
            let observation = *runtime.observe();
            let sealed = runtime.seal(max_envelope_bytes)?;
            Ok::<_, RuntimeError>((sealed, observation))
        })
        .map_err(|error| PyValueError::new_err(error.to_string()))?;
    let (sealed, observation) = result;
    if observation.state_receipt != sealed.receipt {
        return Err(PyValueError::new_err(
            RuntimeError::SealedStateChanged.to_string(),
        ));
    }
    Ok(NativeOrganismRuntimeTransition {
        payload: Arc::from(sealed.bytes),
        observation,
    })
}

#[pyfunction]
#[pyo3(signature = (
    legacy_glmfab03,
    expected_content_sha256,
    organism_identity,
    authenticated_predecessor_tick,
    max_envelope_bytes=67_108_864,
    max_fabric_bytes=67_108_000,
    max_logical_peak_bytes=536_870_912
))]
fn migrate_authenticated_task853_predecessor_to_native_organism_runtime(
    py: Python<'_>,
    legacy_glmfab03: Vec<u8>,
    expected_content_sha256: Vec<u8>,
    organism_identity: String,
    authenticated_predecessor_tick: u64,
    max_envelope_bytes: usize,
    max_fabric_bytes: usize,
    max_logical_peak_bytes: usize,
) -> PyResult<NativeAuthenticatedTask853RuntimeMigration> {
    if expected_content_sha256.len() != 32 {
        return Err(PyValueError::new_err(
            "authenticated task-853 GLMFAB03 SHA-256 must contain exactly 32 bytes",
        ));
    }
    let expected_content_sha256: [u8; 32] = expected_content_sha256
        .try_into()
        .expect("checked SHA-256 width");
    let migrated = py
        .allow_threads(move || {
            let budget =
                RuntimeBudget::new(max_envelope_bytes, max_fabric_bytes, max_logical_peak_bytes)?;
            migrate_authenticated_task853_predecessor(
                legacy_glmfab03,
                expected_content_sha256,
                &organism_identity,
                authenticated_predecessor_tick,
                budget,
            )
        })
        .map_err(|error| PyValueError::new_err(error.to_string()))?;
    if migrated.observation.state_receipt != migrated.sealed.receipt {
        return Err(PyValueError::new_err(
            RuntimeError::SealedStateChanged.to_string(),
        ));
    }
    Ok(NativeAuthenticatedTask853RuntimeMigration {
        payload: Arc::from(migrated.sealed.bytes),
        observation: migrated.observation,
        legacy_fabric_receipt: migrated.legacy_fabric_receipt,
    })
}

fn migrate_authenticated_task853_predecessor(
    legacy_glmfab03: Vec<u8>,
    expected_content_sha256: [u8; 32],
    organism_identity: &str,
    authenticated_predecessor_tick: u64,
    budget: RuntimeBudget,
) -> Result<AuthenticatedTask853RuntimeMigration, RuntimeError> {
    migrate_authenticated_legacy_predecessor(
        legacy_glmfab03,
        expected_content_sha256,
        organism_identity,
        authenticated_predecessor_tick,
        budget,
        LegacyMigrationAuthority {
            identity: TASK853_IDENTITY,
            organism_tick: TASK853_ORGANISM_TICK,
            fabric_receipt: TASK853_GLMFAB03_SHA256,
            fabric_generation: 13,
            mounted_generation: 2,
        },
    )
}

fn migrate_authenticated_legacy_predecessor(
    legacy_glmfab03: Vec<u8>,
    expected_content_sha256: [u8; 32],
    organism_identity: &str,
    authenticated_predecessor_tick: u64,
    budget: RuntimeBudget,
    authority: LegacyMigrationAuthority,
) -> Result<AuthenticatedTask853RuntimeMigration, RuntimeError> {
    let identity = canonical_identity(organism_identity)?;
    if identity.as_slice() != authority.identity.as_bytes() {
        return Err(RuntimeError::Task853IdentityMismatch);
    }
    if authenticated_predecessor_tick != authority.organism_tick {
        return Err(RuntimeError::Task853TickMismatch);
    }
    let derived_budget = budget.derive()?;
    let migration = migrate_authenticated_glmfab03_to_current(
        &legacy_glmfab03,
        expected_content_sha256,
        budget.max_fabric_bytes,
        derived_budget.max_joint_working_bytes,
    )
    .map_err(RuntimeError::LegacyMigration)?;
    if migration.legacy_fabric_receipt != authority.fabric_receipt {
        return Err(RuntimeError::Task853LegacyReceiptMismatch);
    }
    let current_fabric_receipt = sha256(&migration.current_fabric);
    let envelope = encode_envelope(
        identity,
        authenticated_predecessor_tick,
        &migration.current_fabric,
        budget,
    )?;
    let parsed = parse_current_envelope(&envelope, budget)?;
    if parsed.identity != identity
        || parsed.organism_tick != authenticated_predecessor_tick
        || sha256(parsed.fabric_bytes) != current_fabric_receipt
        || parsed.fabric_generation != authority.fabric_generation
        || migration.summary.generation != authority.mounted_generation
    {
        return Err(RuntimeError::MigrationInvariantChanged);
    }
    let cognitive = restore_cognitive_state(&parsed, budget)?;
    let observation = make_restored_observation(
        &envelope,
        parsed,
        migration.summary,
        cognitive.summary(),
        derived_budget,
    );
    if observation.mounted_step_completed
        || observation.physical_transition_claimed
        || observation.cognitive_formation_claimed
        || observation.python_callback_count != 0
    {
        return Err(RuntimeError::MigrationInvariantChanged);
    }
    let sealed = SealedRuntimeState {
        receipt: observation.state_receipt,
        bytes: envelope,
    };
    Ok(AuthenticatedTask853RuntimeMigration {
        sealed,
        observation,
        legacy_fabric_receipt: migration.legacy_fabric_receipt,
    })
}

pub(crate) fn register(module: &Bound<'_, PyModule>) -> PyResult<()> {
    module.add_class::<NativeOrganismRuntimeTransition>()?;
    module.add_class::<NativeAuthenticatedTask853RuntimeMigration>()?;
    module.add_class::<NativeResidentOrganismRuntime>()?;
    module.add_class::<NativeResidentOrganismObservation>()?;
    module.add_class::<NativeResidentOrganismPrepare>()?;
    module.add_function(wrap_pyfunction!(
        transition_native_organism_runtime,
        module
    )?)?;
    module.add_function(wrap_pyfunction!(restore_native_organism_runtime, module)?)?;
    module.add_function(wrap_pyfunction!(
        restore_native_resident_organism_runtime,
        module
    )?)?;
    module.add_function(wrap_pyfunction!(
        create_native_resident_organism_runtime,
        module
    )?)?;
    module.add_function(wrap_pyfunction!(
        migrate_authenticated_task853_predecessor_to_native_organism_runtime,
        module
    )?)?;
    Ok(())
}

#[derive(Debug)]
pub(crate) struct OrganismRuntime {
    envelope: Vec<u8>,
    observation: RuntimeObservation,
}

impl OrganismRuntime {
    pub(crate) fn restore_current(
        identity: &str,
        organism_tick: u64,
        fabric: Vec<u8>,
        budget: RuntimeBudget,
    ) -> Result<Self, RuntimeError> {
        let identity = canonical_identity(identity)?;
        parse_current_fabric(&fabric, budget)?;
        let envelope = encode_envelope(identity, organism_tick, &fabric, budget)?;
        Self::restore_envelope(envelope, budget)
    }

    pub(crate) fn restore_envelope(
        envelope: Vec<u8>,
        budget: RuntimeBudget,
    ) -> Result<Self, RuntimeError> {
        let derived_budget = budget.derive()?;
        let parsed = parse_current_envelope(&envelope, budget)?;
        let joint = inspect_mounted_joint_dsf_summary(
            parsed.joint_bytes,
            derived_budget.max_joint_state_bytes,
            derived_budget.max_joint_working_bytes,
        )
        .map_err(RuntimeError::MountedTransition)?;
        let cognitive = restore_cognitive_state(&parsed, budget)?;
        let observation = make_restored_observation(
            &envelope,
            parsed,
            joint,
            cognitive.summary(),
            derived_budget,
        );
        Ok(Self {
            envelope,
            observation,
        })
    }

    pub(crate) fn observe(&self) -> &RuntimeObservation {
        &self.observation
    }

    #[cfg(not(test))]
    pub(crate) fn advance_mounted(
        &self,
        _source: &NativeJointSourceEpisode,
        _budget: RuntimeBudget,
    ) -> Result<RuntimeStepResult, RuntimeError> {
        Err(RuntimeError::HippocampalColdCustodyMissing)
    }

    #[cfg(test)]
    pub(crate) fn advance_mounted(
        &self,
        source: &NativeJointSourceEpisode,
        budget: RuntimeBudget,
    ) -> Result<RuntimeStepResult, RuntimeError> {
        let derived_budget = budget.derive()?;
        let parsed = parse_current_envelope(&self.envelope, budget)?;
        let successor_organism_tick = parsed
            .organism_tick
            .checked_add(1)
            .ok_or(RuntimeError::OrganismTickOverflow)?;
        let successor_fabric_generation = parsed
            .fabric_generation
            .checked_add(1)
            .ok_or(RuntimeError::FabricGenerationOverflow)?;
        let predecessor_mounted_generation = self.observation.mounted_generation;
        // NativeJointSourceEpisode is immutable and its authority was computed
        // once when its canonical source body was admitted. Capture that exact
        // admitted pair before any mounted physics; do not hash it again here.
        let admitted_source_authority = source.joint_source_authority_receipt();
        let admitted_source_body = source.joint_source_body();
        let prepared = transition_mounted_joint_dsf(
            parsed.joint_bytes,
            source,
            derived_budget.max_joint_state_bytes,
            derived_budget.max_joint_working_bytes,
        )
        .map_err(RuntimeError::MountedTransition)?;
        if prepared.predecessor_generation() != predecessor_mounted_generation
            || prepared.predecessor_generation().checked_add(1)
                != Some(prepared.successor_generation())
        {
            return Err(RuntimeError::MountedGenerationDiscontinuity);
        }
        if prepared.source_authority() != admitted_source_authority
            || prepared.source_body() != admitted_source_body.as_ref()
        {
            return Err(RuntimeError::MountedSourceSubstitution);
        }
        let successor_mounted_generation = prepared.successor_generation();
        let source_authority = prepared.source_authority();
        let source_cohort_l0_l4_evaluation_count = prepared.transition().l0_l4_evaluation_count;
        let prepared_dsf_delivery_count = prepared
            .fields()
            .iter()
            .try_fold(0usize, |count, field| {
                count.checked_add(field.neurons().len())
            })
            .ok_or(RuntimeError::BudgetArithmeticOverflow)?;
        if prepared.fields().len() != source_cohort_l0_l4_evaluation_count
            || prepared.transition().joint_field_count != source_cohort_l0_l4_evaluation_count
            || prepared.transition().dsf_delivery_count != prepared_dsf_delivery_count
        {
            return Err(RuntimeError::MountedGenerationDiscontinuity);
        }
        let cognitive_occurrence = CognitiveOccurrence::from_mounted(&prepared, source)
            .map_err(|error| RuntimeError::CognitiveFormation(error.to_string()))?;
        let cognitive_state = restore_cognitive_state(&parsed, budget)?;
        let cognitive_budget = cognitive_budget_after_joint(prepared.state_bytes().len(), budget)?;
        let cognitive = cognitive_state
            .prepare(&cognitive_occurrence, source, cognitive_budget)
            .map_err(|error| RuntimeError::CognitiveFormation(error.to_string()))?;
        let cognitive_bytes = cognitive_state
            .encode_successor(&cognitive, cognitive_budget)
            .map_err(|error| RuntimeError::CognitiveFormation(error.to_string()))?;
        let cognitive_observation = cognitive.observation().clone();
        let (joint_state, transition) = prepared.into_serialized_parts();
        let fabric = encode_fabric(
            successor_fabric_generation,
            &joint_state,
            &cognitive_bytes,
            budget,
        )?;
        let envelope = encode_envelope(parsed.identity, successor_organism_tick, &fabric, budget)?;
        let observation = make_step_observation(
            &envelope,
            parsed.identity,
            parsed.organism_tick,
            successor_organism_tick,
            parsed.fabric_generation,
            successor_fabric_generation,
            predecessor_mounted_generation,
            successor_mounted_generation,
            &fabric,
            source_authority,
            transition,
            source_cohort_l0_l4_evaluation_count,
            derived_budget,
            self.observation.state_receipt,
            &cognitive_observation,
        );
        let sealed = SealedRuntimeState {
            receipt: observation.state_receipt,
            bytes: envelope,
        };
        Ok(RuntimeStepResult {
            successor: sealed,
            observation,
        })
    }

    pub(crate) fn seal(self, max_encoded_bytes: usize) -> Result<SealedRuntimeState, RuntimeError> {
        if self.envelope.len() > max_encoded_bytes {
            return Err(RuntimeError::EnvelopeBudgetExceeded);
        }
        let receipt = sha256(&self.envelope);
        if self.envelope.len() != self.observation.state_bytes
            || receipt != self.observation.state_receipt
        {
            return Err(RuntimeError::SealedStateChanged);
        }
        Ok(SealedRuntimeState {
            bytes: self.envelope,
            receipt,
        })
    }
}

#[derive(Clone, Copy)]
struct ParsedEnvelope<'a> {
    identity: [u8; IDENTITY_BYTES],
    organism_tick: u64,
    fabric_bytes: &'a [u8],
    fabric_generation: u64,
    joint_bytes: &'a [u8],
    cognitive_bytes: Option<&'a [u8]>,
}

fn parse_current_envelope<'a>(
    envelope: &'a [u8],
    budget: RuntimeBudget,
) -> Result<ParsedEnvelope<'a>, RuntimeError> {
    if envelope.len() > budget.max_envelope_bytes {
        return Err(RuntimeError::EnvelopeBudgetExceeded);
    }
    if envelope.len() < FIXED_BYTES {
        return Err(RuntimeError::EnvelopeEndedEarly);
    }
    if &envelope[..MAGIC.len()] != MAGIC {
        return Err(RuntimeError::BadEnvelopeMagic);
    }
    let mut offset = MAGIC.len();
    let version = take_u16(envelope, &mut offset)?;
    if version != VERSION {
        return Err(RuntimeError::UnsupportedEnvelopeVersion(version));
    }
    let identity_end = offset
        .checked_add(IDENTITY_BYTES)
        .ok_or(RuntimeError::EnvelopeEndedEarly)?;
    let identity_text = std::str::from_utf8(
        envelope
            .get(offset..identity_end)
            .ok_or(RuntimeError::EnvelopeEndedEarly)?,
    )
    .map_err(|_| RuntimeError::InvalidIdentity)?;
    let identity = canonical_identity(identity_text)?;
    offset = identity_end;
    let organism_tick = take_u64(envelope, &mut offset)?;
    let fabric_len = take_u32(envelope, &mut offset)? as usize;
    if fabric_len > budget.max_fabric_bytes {
        return Err(RuntimeError::FabricBudgetExceeded);
    }
    let fabric_end = offset
        .checked_add(fabric_len)
        .ok_or(RuntimeError::FabricLengthOverflow)?;
    if fabric_end != envelope.len() {
        return Err(RuntimeError::FabricLengthMismatch);
    }
    let fabric_bytes = &envelope[offset..fabric_end];
    let (fabric_generation, joint_bytes, cognitive_bytes) =
        parse_current_fabric(fabric_bytes, budget)?;
    Ok(ParsedEnvelope {
        identity,
        organism_tick,
        fabric_bytes,
        fabric_generation,
        joint_bytes,
        cognitive_bytes,
    })
}

fn parse_current_fabric(
    fabric: &[u8],
    budget: RuntimeBudget,
) -> Result<(u64, &[u8], Option<&[u8]>), RuntimeError> {
    if fabric.len() > budget.max_fabric_bytes {
        return Err(RuntimeError::FabricBudgetExceeded);
    }
    if fabric.len() < LEGACY_FABRIC_FIXED_BYTES {
        return Err(RuntimeError::BadFabricMagic);
    }
    let magic = &fabric[..FABRIC_MAGIC.len()];
    if magic != FABRIC_MAGIC && magic != LEGACY_FABRIC_MAGIC {
        return Err(RuntimeError::BadFabricMagic);
    }
    let mut offset = FABRIC_MAGIC.len();
    let version = take_u16(fabric, &mut offset)?;
    let legacy = magic == LEGACY_FABRIC_MAGIC && version == LEGACY_FABRIC_VERSION;
    let current = magic == FABRIC_MAGIC && version == FABRIC_VERSION;
    if !legacy && !current {
        return Err(RuntimeError::UnsupportedFabricVersion(version));
    }
    let generation = take_u64(fabric, &mut offset)?;
    let joint_len = take_u32(fabric, &mut offset)? as usize;
    let cognitive_len = if current {
        take_u32(fabric, &mut offset)? as usize
    } else {
        0
    };
    let joint_end = offset
        .checked_add(joint_len)
        .ok_or(RuntimeError::FabricLengthOverflow)?;
    let cognitive_end = joint_end
        .checked_add(cognitive_len)
        .ok_or(RuntimeError::FabricLengthOverflow)?;
    if cognitive_end != fabric.len() {
        return Err(RuntimeError::FabricLengthMismatch);
    }
    Ok((
        generation,
        &fabric[offset..joint_end],
        current.then_some(&fabric[joint_end..cognitive_end]),
    ))
}

fn encode_fabric(
    generation: u64,
    joint: &[u8],
    cognitive: &[u8],
    budget: RuntimeBudget,
) -> Result<Vec<u8>, RuntimeError> {
    let length = FABRIC_FIXED_BYTES
        .checked_add(joint.len())
        .and_then(|value| value.checked_add(cognitive.len()))
        .ok_or(RuntimeError::FabricLengthOverflow)?;
    if length > budget.max_fabric_bytes {
        return Err(RuntimeError::FabricBudgetExceeded);
    }
    let mut output = Vec::with_capacity(length);
    output.extend_from_slice(FABRIC_MAGIC);
    output.extend_from_slice(&FABRIC_VERSION.to_le_bytes());
    output.extend_from_slice(&generation.to_le_bytes());
    output.extend_from_slice(
        &u32::try_from(joint.len())
            .map_err(|_| RuntimeError::FabricLengthOverflow)?
            .to_le_bytes(),
    );
    output.extend_from_slice(
        &u32::try_from(cognitive.len())
            .map_err(|_| RuntimeError::FabricLengthOverflow)?
            .to_le_bytes(),
    );
    output.extend_from_slice(joint);
    output.extend_from_slice(cognitive);
    Ok(output)
}

fn cognitive_budget_after_joint(
    joint_bytes: usize,
    budget: RuntimeBudget,
) -> Result<usize, RuntimeError> {
    budget
        .max_fabric_bytes
        .checked_sub(FABRIC_FIXED_BYTES)
        .and_then(|value| value.checked_sub(joint_bytes))
        .filter(|value| *value > 0)
        .ok_or(RuntimeError::FabricBudgetExceeded)
}

fn restore_cognitive_state(
    parsed: &ParsedEnvelope<'_>,
    budget: RuntimeBudget,
) -> Result<ResidentCognitiveFormationState, RuntimeError> {
    let cognitive_budget = cognitive_budget_after_joint(parsed.joint_bytes.len(), budget)?;
    match parsed.cognitive_bytes {
        Some(bytes) => ResidentCognitiveFormationState::decode(bytes, cognitive_budget)
            .map_err(|error| RuntimeError::CognitiveFormation(error.to_string())),
        None => Ok(ResidentCognitiveFormationState::default()),
    }
}

fn encode_envelope(
    identity: [u8; IDENTITY_BYTES],
    organism_tick: u64,
    fabric: &[u8],
    budget: RuntimeBudget,
) -> Result<Vec<u8>, RuntimeError> {
    if fabric.len() > budget.max_fabric_bytes {
        return Err(RuntimeError::FabricBudgetExceeded);
    }
    let length = FIXED_BYTES
        .checked_add(fabric.len())
        .ok_or(RuntimeError::FabricLengthOverflow)?;
    if length > budget.max_envelope_bytes {
        return Err(RuntimeError::EnvelopeBudgetExceeded);
    }
    let mut output = Vec::with_capacity(length);
    output.extend_from_slice(MAGIC);
    output.extend_from_slice(&VERSION.to_le_bytes());
    output.extend_from_slice(&identity);
    output.extend_from_slice(&organism_tick.to_le_bytes());
    output.extend_from_slice(
        &u32::try_from(fabric.len())
            .map_err(|_| RuntimeError::FabricLengthOverflow)?
            .to_le_bytes(),
    );
    output.extend_from_slice(fabric);
    Ok(output)
}

fn make_restored_observation(
    envelope: &[u8],
    parsed: ParsedEnvelope<'_>,
    joint: MountedJointDsfSummary,
    cognitive: CognitiveFormationSummary,
    derived_budget: DerivedRuntimeBudget,
) -> RuntimeObservation {
    RuntimeObservation {
        schema: OBSERVATION_SCHEMA,
        scope: RESTORED_SCOPE,
        identity: parsed.identity,
        predecessor_state_receipt: None,
        predecessor_organism_tick: None,
        organism_tick: parsed.organism_tick,
        predecessor_fabric_generation: None,
        fabric_generation: parsed.fabric_generation,
        predecessor_mounted_generation: None,
        mounted_generation: joint.generation,
        state_bytes: envelope.len(),
        state_receipt: sha256(envelope),
        fabric_bytes: parsed.fabric_bytes.len(),
        fabric_receipt: sha256(parsed.fabric_bytes),
        joint_field_count: joint.joint_field_count,
        joint_neuron_count: joint.joint_neuron_count,
        dsf_delivery_count: 0,
        complete_neuron_count: cognitive.complete_neuron_count,
        physically_transitioned_neuron_count: 0,
        complete_neuron_fractal_count: 0,
        recurrent_complete_neuron_fractal_count: 0,
        source_cohort_l0_l4_evaluation_count: 0,
        successor_l0_l4_replay_count: 0,
        joint_transition_receipt: joint.transition_receipt,
        episode_relation_candidate_receipt: joint.episode_relation_candidate_receipt,
        source_authority: None,
        mounted_step_completed: false,
        physical_transition_claimed: false,
        cognitive_formation_claimed: false,
        cognitive_ordinal: cognitive.cognitive_ordinal,
        cognitive_trace_count: cognitive.trace_count,
        cognitive_mosaic_count: cognitive.mosaic_count,
        formation_activation_count: 0,
        partial_cue_reassembly_count: 0,
        python_callback_count: 0,
        derived_budget,
    }
}

#[allow(clippy::too_many_arguments)]
fn make_step_observation(
    envelope: &[u8],
    identity: [u8; IDENTITY_BYTES],
    predecessor_organism_tick: u64,
    organism_tick: u64,
    predecessor_fabric_generation: u64,
    fabric_generation: u64,
    predecessor_mounted_generation: u64,
    mounted_generation: u64,
    fabric: &[u8],
    source_authority: [u8; 32],
    transition: MountedJointDsfTransition,
    source_cohort_l0_l4_evaluation_count: usize,
    derived_budget: DerivedRuntimeBudget,
    predecessor_state_receipt: [u8; 32],
    cognitive: &CognitiveFormationObservation,
) -> RuntimeObservation {
    RuntimeObservation {
        schema: OBSERVATION_SCHEMA,
        scope: MOUNTED_STEP_SCOPE,
        identity,
        predecessor_state_receipt: Some(predecessor_state_receipt),
        predecessor_organism_tick: Some(predecessor_organism_tick),
        organism_tick,
        predecessor_fabric_generation: Some(predecessor_fabric_generation),
        fabric_generation,
        predecessor_mounted_generation: Some(predecessor_mounted_generation),
        mounted_generation,
        state_bytes: envelope.len(),
        state_receipt: sha256(envelope),
        fabric_bytes: fabric.len(),
        fabric_receipt: sha256(fabric),
        joint_field_count: transition.joint_field_count,
        joint_neuron_count: transition.joint_neuron_count,
        dsf_delivery_count: transition.dsf_delivery_count,
        complete_neuron_count: cognitive.complete_neuron_count,
        physically_transitioned_neuron_count: cognitive.physically_transitioned_neuron_count,
        complete_neuron_fractal_count: cognitive.complete_neuron_fractal_count,
        recurrent_complete_neuron_fractal_count: 0,
        source_cohort_l0_l4_evaluation_count,
        successor_l0_l4_replay_count: 0,
        joint_transition_receipt: transition.transition_receipt,
        episode_relation_candidate_receipt: transition.episode_relation_candidate_receipt,
        source_authority: Some(source_authority),
        mounted_step_completed: true,
        physical_transition_claimed: cognitive.physically_transitioned_neuron_count > 0,
        cognitive_formation_claimed: cognitive.trace_formed
            || cognitive.mosaic_formed.is_some()
            || !cognitive.activations.is_empty(),
        cognitive_ordinal: cognitive.cognitive_ordinal,
        cognitive_trace_count: cognitive.trace_count,
        cognitive_mosaic_count: cognitive.mosaic_count,
        formation_activation_count: cognitive.activations.len(),
        partial_cue_reassembly_count: cognitive.partial_cue_reassembly_count(),
        python_callback_count: 0,
        derived_budget,
    }
}

fn canonical_identity(value: &str) -> Result<[u8; IDENTITY_BYTES], RuntimeError> {
    let bytes = value.as_bytes();
    if bytes.len() != IDENTITY_BYTES
        || bytes.iter().enumerate().any(|(index, value)| {
            if matches!(index, 8 | 13 | 18 | 23) {
                *value != b'-'
            } else {
                !matches!(*value, b'0'..=b'9' | b'a'..=b'f')
            }
        })
    {
        return Err(RuntimeError::InvalidIdentity);
    }
    let mut identity = [0_u8; IDENTITY_BYTES];
    identity.copy_from_slice(bytes);
    Ok(identity)
}

fn hex_digest(value: &[u8; 32]) -> String {
    const HEX: &[u8; 16] = b"0123456789abcdef";
    let mut output = String::with_capacity(64);
    for byte in value {
        output.push(HEX[(byte >> 4) as usize] as char);
        output.push(HEX[(byte & 0x0f) as usize] as char);
    }
    output
}

fn take_u16(bytes: &[u8], offset: &mut usize) -> Result<u16, RuntimeError> {
    let end = offset
        .checked_add(std::mem::size_of::<u16>())
        .ok_or(RuntimeError::EnvelopeEndedEarly)?;
    let value = bytes
        .get(*offset..end)
        .ok_or(RuntimeError::EnvelopeEndedEarly)?;
    *offset = end;
    Ok(u16::from_le_bytes(value.try_into().expect("fixed u16")))
}

fn take_u32(bytes: &[u8], offset: &mut usize) -> Result<u32, RuntimeError> {
    let end = offset
        .checked_add(std::mem::size_of::<u32>())
        .ok_or(RuntimeError::EnvelopeEndedEarly)?;
    let value = bytes
        .get(*offset..end)
        .ok_or(RuntimeError::EnvelopeEndedEarly)?;
    *offset = end;
    Ok(u32::from_le_bytes(value.try_into().expect("fixed u32")))
}

fn take_u64(bytes: &[u8], offset: &mut usize) -> Result<u64, RuntimeError> {
    let end = offset
        .checked_add(std::mem::size_of::<u64>())
        .ok_or(RuntimeError::EnvelopeEndedEarly)?;
    let value = bytes
        .get(*offset..end)
        .ok_or(RuntimeError::EnvelopeEndedEarly)?;
    *offset = end;
    Ok(u64::from_le_bytes(value.try_into().expect("fixed u64")))
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::joint_source_episode::decode_native_joint_source_episode;
    use crate::neuron_source_anchor::tests::{exact_dark_optical_episode, exact_optical_episode};

    const IDENTITY: &str = "12345678-9abc-4def-8123-456789abcdef";

    fn budget() -> RuntimeBudget {
        RuntimeBudget::new(1_048_576, 1_048_000, 3_145_728).unwrap()
    }

    fn text(output: &mut Vec<u8>, value: &str) {
        output.extend_from_slice(&u16::try_from(value.len()).unwrap().to_le_bytes());
        output.extend_from_slice(value.as_bytes());
    }

    fn rational(output: &mut Vec<u8>, numerator: i64, denominator: i64) {
        text(output, &numerator.to_string());
        text(output, &denominator.to_string());
    }

    fn source_port(output: &mut Vec<u8>, topology: u32, values: [(i64, f64); 2]) {
        output.push(0);
        output.extend_from_slice(&topology.to_le_bytes());
        text(output, &format!("retina-{topology}"));
        text(output, "luminance");
        output.extend_from_slice(&1_u16.to_le_bytes());
        text(output, "receptor");
        text(output, &topology.to_string());
        text(output, "light");
        text(output, "normalized");
        text(output, "direct");
        text(output, "");
        text(output, "affine");
        rational(output, -1, 1);
        rational(output, 1, 1);
        rational(output, 1, 1);
        rational(output, 1, 1);
        output.extend_from_slice(&1_u32.to_le_bytes());
        output.push(topology as u8);
        output.extend_from_slice(&2_u32.to_le_bytes());
        for (time, signal) in values {
            rational(output, time, 1);
            output.extend_from_slice(&signal.to_bits().to_le_bytes());
            rational(output, 0, 1);
            rational(output, 1, 1);
            rational(output, (1.0 + signal) as i64, 1);
        }
    }

    fn source(episode: &str) -> NativeJointSourceEpisode {
        let mut body = b"GLJSRC02".to_vec();
        body.extend_from_slice(&2_u16.to_le_bytes());
        text(&mut body, episode);
        body.extend_from_slice(&[0, 1, 1, 1, 1, 1]);
        body.extend_from_slice(&2_u32.to_le_bytes());
        source_port(&mut body, 0, [(1, 0.0), (2, 1.0)]);
        source_port(&mut body, 1, [(1, 1.0), (2, 0.0)]);
        body.extend_from_slice(&2_u32.to_le_bytes());
        source_occurrence(&mut body, 0, [1, 2]);
        source_occurrence(&mut body, 1, [1, 2]);
        decode_native_joint_source_episode(&body, 2, 4, 2, 4).unwrap()
    }

    fn source_with_port_count(episode: &str, port_count: u32) -> NativeJointSourceEpisode {
        let mut body = b"GLJSRC02".to_vec();
        body.extend_from_slice(&2_u16.to_le_bytes());
        text(&mut body, episode);
        body.extend_from_slice(&[0, 1, 1, 1, 1, 1]);
        body.extend_from_slice(&port_count.to_le_bytes());
        for topology in 0..port_count {
            let values = if topology % 2 == 0 {
                [(1, 0.0), (2, 1.0)]
            } else {
                [(1, 1.0), (2, 0.0)]
            };
            source_port(&mut body, topology, values);
        }
        body.extend_from_slice(&port_count.to_le_bytes());
        for port_index in 0..port_count {
            source_occurrence(&mut body, port_index, [1, 2]);
        }
        decode_native_joint_source_episode(
            &body,
            port_count as usize,
            port_count as usize * 2,
            port_count as usize,
            port_count as usize * 2,
        )
        .unwrap()
    }

    fn source_occurrence(output: &mut Vec<u8>, port_index: u32, times: [i64; 2]) {
        output.extend_from_slice(&1_u32.to_le_bytes());
        output.extend_from_slice(&port_index.to_le_bytes());
        output.extend_from_slice(&2_u32.to_le_bytes());
        for time in times {
            rational(output, time, 1);
        }
        let profile =
            crate::joint_uf_source_adapter::SAMPLED_VOLUME_AND_RELEVANCE_PIECEWISE_LINEAR_PROFILE;
        output.extend_from_slice(&u32::try_from(profile.len()).unwrap().to_le_bytes());
        output.extend_from_slice(profile);
        output.extend_from_slice(&1_u32.to_le_bytes());
        output.extend_from_slice(&1_u32.to_le_bytes());
        output.extend_from_slice(&0_u32.to_le_bytes());
        output.extend_from_slice(&1_u32.to_le_bytes());
        output.push(1);
        output.extend_from_slice(&2_u32.to_le_bytes());
        rational(output, 1, 1);
        rational(output, 1, 1);
    }

    fn genesis_joint() -> Vec<u8> {
        let mut bytes = Vec::new();
        bytes.extend_from_slice(b"GLJDSF03");
        bytes.extend_from_slice(&3_u16.to_le_bytes());
        bytes.extend_from_slice(&0_u64.to_le_bytes());
        bytes.extend_from_slice(&1_u64.to_le_bytes());
        bytes.extend_from_slice(&[0; 32]);
        bytes.push(0);
        bytes.extend_from_slice(&0_u32.to_le_bytes());
        bytes.extend_from_slice(&0_u32.to_le_bytes());
        bytes.push(0);
        bytes
    }

    fn genesis_cognitive() -> Vec<u8> {
        ResidentCognitiveFormationState::default()
            .encode(1_000_000)
            .unwrap()
    }

    fn legacy_joint() -> Vec<u8> {
        let mut bytes = Vec::new();
        bytes.extend_from_slice(b"GLJNFT02");
        bytes.extend_from_slice(&2_u16.to_le_bytes());
        bytes.extend_from_slice(&13_u64.to_le_bytes());
        bytes.extend_from_slice(&1_u64.to_le_bytes());
        bytes.extend_from_slice(&[0; 32]);
        bytes.push(0);
        bytes.extend_from_slice(&0_u32.to_le_bytes());
        bytes.extend_from_slice(&0_u32.to_le_bytes());
        bytes.push(0);
        bytes
    }

    fn legacy_fabric() -> Vec<u8> {
        let joint = legacy_joint();
        let mut bytes = Vec::new();
        bytes.extend_from_slice(b"GLMFAB03");
        bytes.extend_from_slice(&3_u16.to_le_bytes());
        bytes.extend_from_slice(&17_u64.to_le_bytes());
        bytes.extend_from_slice(&0_u32.to_le_bytes());
        bytes.extend_from_slice(&0_u32.to_le_bytes());
        bytes.extend_from_slice(&u32::try_from(joint.len()).unwrap().to_le_bytes());
        bytes.extend_from_slice(&joint);
        bytes
    }

    fn test_migration_authority(fabric: &[u8]) -> LegacyMigrationAuthority {
        LegacyMigrationAuthority {
            identity: IDENTITY,
            organism_tick: 91,
            fabric_receipt: sha256(fabric),
            fabric_generation: 17,
            mounted_generation: 13,
        }
    }

    fn restored(tick: u64, fabric_generation: u64) -> OrganismRuntime {
        let fabric = encode_fabric(
            fabric_generation,
            &genesis_joint(),
            &genesis_cognitive(),
            budget(),
        )
        .unwrap();
        OrganismRuntime::restore_current(IDENTITY, tick, fabric, budget()).unwrap()
    }

    fn resident(tick: u64, fabric_generation: u64) -> ResidentOrganismRuntime {
        let envelope = restored(tick, fabric_generation)
            .seal(budget().max_envelope_bytes)
            .unwrap()
            .bytes;
        ResidentOrganismRuntime::restore_envelope(envelope, budget()).unwrap()
    }

    #[test]
    fn one_episode_advances_only_the_truthful_mounted_step() {
        let episode = source("first-mounted-step");
        let predecessor = restored(91, 17);
        let predecessor_receipt = predecessor.observe().state_receipt;
        let result = predecessor.advance_mounted(&episode, budget()).unwrap();
        let observed = result.observation;
        assert_eq!(observed.schema, OBSERVATION_SCHEMA);
        assert_eq!(observed.scope, MOUNTED_STEP_SCOPE);
        assert_eq!(&observed.identity, IDENTITY.as_bytes());
        assert_eq!(
            (observed.predecessor_organism_tick, observed.organism_tick),
            (Some(91), 92)
        );
        assert_eq!(
            (
                observed.predecessor_fabric_generation,
                observed.fabric_generation
            ),
            (Some(17), 18)
        );
        assert_eq!(
            (
                observed.predecessor_mounted_generation,
                observed.mounted_generation
            ),
            (Some(0), 1)
        );
        assert_eq!(observed.joint_field_count, 1);
        assert_eq!(observed.joint_neuron_count, 2);
        assert_eq!(observed.dsf_delivery_count, 2);
        assert_eq!(observed.complete_neuron_count, 2);
        assert_eq!(observed.complete_neuron_fractal_count, 0);
        assert_eq!(observed.recurrent_complete_neuron_fractal_count, 0);
        assert_eq!(observed.source_cohort_l0_l4_evaluation_count, 1);
        assert_eq!(observed.successor_l0_l4_replay_count, 0);
        assert_eq!(
            observed.source_authority,
            Some(episode.joint_source_authority_receipt())
        );
        assert_eq!(
            observed.predecessor_state_receipt,
            Some(predecessor_receipt)
        );
        assert!(observed.joint_transition_receipt.is_some());
        assert!(observed.mounted_step_completed);
        assert!(!observed.physical_transition_claimed);
        assert!(!observed.cognitive_formation_claimed);
        assert_eq!(observed.python_callback_count, 0);
        assert_eq!(observed.state_receipt, result.successor.receipt);
        assert_eq!(sha256(&result.successor.bytes), result.successor.receipt);
        let expected_successor = result.successor.bytes.clone();
        let cold = OrganismRuntime::restore_envelope(result.successor.bytes, budget()).unwrap();
        assert_eq!(
            cold.seal(budget().max_envelope_bytes).unwrap().bytes,
            expected_successor
        );
    }

    #[test]
    fn recurrent_step_preserves_identity_and_local_continuity() {
        let first = restored(91, 17)
            .advance_mounted(&source("first"), budget())
            .unwrap();
        let runtime = OrganismRuntime::restore_envelope(first.successor.bytes, budget()).unwrap();
        let second = runtime
            .advance_mounted(&source("second"), budget())
            .unwrap();
        assert_eq!(&second.observation.identity, IDENTITY.as_bytes());
        assert_eq!(
            (
                second.observation.organism_tick,
                second.observation.fabric_generation,
                second.observation.mounted_generation
            ),
            (93, 19, 2)
        );
        assert_eq!(second.observation.dsf_delivery_count, 2);
        assert_eq!(second.observation.complete_neuron_fractal_count, 0);
        assert_eq!(
            second.observation.recurrent_complete_neuron_fractal_count,
            0
        );
        assert_eq!(second.observation.source_cohort_l0_l4_evaluation_count, 1);
        assert_eq!(second.observation.successor_l0_l4_replay_count, 0);
    }

    #[test]
    fn independent_clocks_are_not_required_to_share_a_number() {
        let result = restored(8_003, 401)
            .advance_mounted(&source("independent-clocks"), budget())
            .unwrap();
        assert_eq!(
            (
                result.observation.organism_tick,
                result.observation.fabric_generation,
                result.observation.mounted_generation
            ),
            (8_004, 402, 1)
        );
    }

    #[test]
    fn organism_tick_overflow_refuses_before_mounted_transition() {
        let predecessor = restored(u64::MAX, 17);
        let before = *predecessor.observe();
        assert_eq!(
            predecessor
                .advance_mounted(&source("tick-overflow"), budget())
                .unwrap_err(),
            RuntimeError::OrganismTickOverflow
        );
        assert_eq!(*predecessor.observe(), before);
    }

    #[test]
    fn fabric_generation_overflow_refuses_before_mounted_transition() {
        assert_eq!(
            restored(91, u64::MAX)
                .advance_mounted(&source("fabric-overflow"), budget())
                .unwrap_err(),
            RuntimeError::FabricGenerationOverflow
        );
    }

    #[test]
    fn derived_budget_reserves_both_envelopes_before_joint_work() {
        let admitted_envelope = 1_024;
        let admitted_fabric = 900;
        let exact = RuntimeBudget::new(admitted_envelope, admitted_fabric, 2_049).unwrap();
        assert_eq!(exact.derive().unwrap().max_joint_working_bytes, 1);
        assert_eq!(
            RuntimeBudget::new(admitted_envelope, admitted_fabric, 2_048).unwrap_err(),
            RuntimeError::InvalidBudget
        );
    }

    #[test]
    fn restored_observation_does_not_claim_a_step() {
        let runtime = restored(91, 17);
        assert_eq!(runtime.observe().scope, RESTORED_SCOPE);
        assert!(!runtime.observe().mounted_step_completed);
        assert_eq!(runtime.observe().predecessor_organism_tick, None);
        assert_eq!(runtime.observe().python_callback_count, 0);
    }

    #[test]
    fn current_only_restore_returns_exact_unchanged_glorun() {
        let original = restored(91, 17).seal(budget().max_envelope_bytes).unwrap();
        let expected_bytes = original.bytes.clone();
        let runtime = OrganismRuntime::restore_envelope(original.bytes, budget()).unwrap();
        let observation = *runtime.observe();
        let restored = runtime.seal(budget().max_envelope_bytes).unwrap();
        assert_eq!(restored.bytes, expected_bytes);
        assert_eq!(restored.receipt, observation.state_receipt);
        assert_eq!(observation.scope, RESTORED_SCOPE);
        assert_eq!(observation.predecessor_state_receipt, None);
        assert_eq!(observation.predecessor_organism_tick, None);
        assert_eq!(observation.predecessor_fabric_generation, None);
        assert_eq!(observation.predecessor_mounted_generation, None);
        assert!(!observation.mounted_step_completed);
        assert_eq!(observation.source_cohort_l0_l4_evaluation_count, 0);
        assert_eq!(observation.successor_l0_l4_replay_count, 0);
    }

    #[test]
    fn native_genesis_is_empty_current_state_and_not_synthetic_experience() {
        let runtime = create_resident_genesis(IDENTITY, 0, budget()).unwrap();
        let observation = runtime.observation();
        assert_eq!(observation.identity.as_slice(), IDENTITY.as_bytes());
        assert_eq!(observation.organism_tick, 0);
        assert_eq!(observation.fabric_generation, 0);
        assert_eq!(observation.mounted_generation, 0);
        assert_eq!(observation.joint_field_count, 0);
        assert_eq!(observation.joint_neuron_count, 0);
        assert_eq!(observation.complete_neuron_count, 0);
        assert_eq!(observation.cognitive_ordinal, 0);
        assert_eq!(observation.cognitive_trace_count, 0);
        assert_eq!(observation.cognitive_mosaic_count, 0);
        assert!(!observation.mounted_step_completed);
        assert!(!observation.cognitive_formation_claimed);
        assert_eq!(runtime.cold_restore_work().decode_count, 1);
        assert!(runtime.active_envelope().starts_with(MAGIC));
    }

    #[test]
    fn resident_optical_step_reports_only_the_physical_cells_that_changed() {
        let mut runtime = create_resident_genesis(IDENTITY, 0, budget()).unwrap();
        let prepared = runtime.prepare(&exact_optical_episode()).unwrap();
        assert_eq!(prepared.observation.complete_neuron_count, 1);
        assert_eq!(prepared.observation.physically_transitioned_neuron_count, 1);
        assert!(prepared.observation.physical_transition_claimed);
        assert_eq!(prepared.observation.complete_neuron_fractal_count, 0);
        assert!(!prepared.observation.cognitive_formation_claimed);
    }

    #[test]
    fn resident_runtime_reports_fractal_only_after_real_post_quiescence_inputs() {
        let mut runtime = create_resident_genesis(IDENTITY, 0, budget()).unwrap();
        let light = runtime.prepare(&exact_optical_episode()).unwrap();
        assert_eq!(light.observation.complete_neuron_fractal_count, 0);
        runtime.commit(light.token).unwrap();

        let mut runtime =
            ResidentOrganismRuntime::restore_envelope(runtime.active_envelope().to_vec(), budget())
                .unwrap();
        let first_dark = runtime.prepare(&exact_dark_optical_episode()).unwrap();
        assert_eq!(first_dark.observation.complete_neuron_fractal_count, 0);
        runtime.commit(first_dark.token).unwrap();

        let mut runtime =
            ResidentOrganismRuntime::restore_envelope(runtime.active_envelope().to_vec(), budget())
                .unwrap();
        let second_dark = runtime.prepare(&exact_dark_optical_episode()).unwrap();
        assert_eq!(second_dark.observation.complete_neuron_fractal_count, 1);
        assert!(!second_dark.observation.cognitive_formation_claimed);
    }

    #[test]
    fn resident_cold_restore_authenticates_once_and_save_is_exact() {
        let stateless = restored(91, 17).seal(budget().max_envelope_bytes).unwrap();
        let expected = stateless.bytes.clone();
        let runtime = ResidentOrganismRuntime::restore_envelope(stateless.bytes, budget()).unwrap();
        assert_eq!(runtime.active_envelope(), expected);
        assert_eq!(runtime.observation().state_receipt, sha256(&expected));
        assert_eq!(
            runtime.cold_restore_work(),
            ResidentMountedRestoreWork {
                authentication_count: 1,
                decode_count: 1,
                rebuilt_predecessor_field_count: 0,
            }
        );
        assert!(runtime.pending.is_none());
    }

    #[test]
    fn resident_prepare_and_discard_leave_active_state_exact() {
        let mut runtime = resident(91, 17);
        let active_bytes = runtime.active_envelope().to_vec();
        let active_observation = runtime.observation();
        let prepared = runtime.prepare(&source("discarded-resident-step")).unwrap();
        assert_eq!(runtime.active_envelope(), active_bytes);
        assert_eq!(runtime.observation(), active_observation);
        assert_eq!(
            prepared.phase_counts,
            MountedTransitionPhaseCounts {
                predecessor_authentication_count: 0,
                predecessor_decode_count: 0,
                predecessor_rebuilt_field_count: 0,
                retained_neuron_index_entry_count: 0,
                reached_neuron_lookup_count: 2,
                current_cohort_evaluation_count: 1,
                successor_seal_count: 1,
            }
        );
        assert_eq!(prepared.receptor_ingress.field_count(), 1);
        assert_eq!(prepared.receptor_ingress.witness_count(), 2);
        assert_eq!(prepared.receptor_ingress.sense_counts(), [2, 0, 0, 0, 0, 0]);
        assert_eq!(prepared.receptor_ingress.reached_neuron_visit_count(), 2);
        assert_eq!(prepared.receptor_ingress.witness_construction_count(), 2);
        assert!(!prepared.observation.physical_transition_claimed);
        assert!(!prepared.observation.cognitive_formation_claimed);
        assert_eq!(
            runtime.prepare(&source("second-pending-step")).unwrap_err(),
            RuntimeError::PendingCandidateExists
        );
        let mut wrong = prepared.token;
        wrong[0] ^= 1;
        assert_eq!(
            runtime.discard(wrong).unwrap_err(),
            RuntimeError::PendingTokenMismatch
        );
        assert_eq!(runtime.active_envelope(), active_bytes);
        assert_eq!(runtime.observation(), active_observation);
        runtime.discard(prepared.token).unwrap();
        assert_eq!(runtime.active_envelope(), active_bytes);
        assert_eq!(runtime.observation(), active_observation);
        assert_eq!(
            runtime.discard(prepared.token).unwrap_err(),
            RuntimeError::PendingCandidateMissing
        );

        let replacement = runtime.prepare(&source("discarded-resident-step")).unwrap();
        assert_ne!(replacement.token, prepared.token);
        assert_eq!(runtime.active_envelope(), active_bytes);
    }

    #[test]
    fn resident_commit_moves_prepared_state_without_redecode_and_consumes_token() {
        let mut runtime = resident(91, 17);
        let active_receipt = runtime.observation().state_receipt;
        let prepared = runtime.prepare(&source("committed-resident-step")).unwrap();
        assert_eq!(
            prepared.observation.predecessor_state_receipt,
            Some(active_receipt)
        );
        assert_eq!(prepared.phase_counts.predecessor_authentication_count, 0);
        assert_eq!(prepared.phase_counts.predecessor_decode_count, 0);
        assert_eq!(prepared.phase_counts.predecessor_rebuilt_field_count, 0);
        runtime.commit(prepared.token).unwrap();
        let committed = runtime.observation();
        assert_eq!(runtime.observation(), prepared.observation);
        assert_eq!(sha256(runtime.active_envelope()), committed.state_receipt);
        assert_eq!(
            (
                committed.organism_tick,
                committed.fabric_generation,
                committed.mounted_generation,
            ),
            (92, 18, 1)
        );
        assert_eq!(
            runtime.commit(prepared.token).unwrap_err(),
            RuntimeError::PendingCandidateMissing
        );
        assert_eq!(
            runtime.cold_restore_work(),
            ResidentMountedRestoreWork {
                authentication_count: 1,
                decode_count: 1,
                rebuilt_predecessor_field_count: 0,
            }
        );
    }

    #[test]
    fn resident_ingress_preserves_independent_clocks_and_exact_successor_bytes() {
        let episode = source("resident-ingress-independent-clocks");
        let expected = restored(8_003, 401)
            .advance_mounted(&episode, budget())
            .unwrap()
            .successor
            .bytes;
        let mut runtime = resident(8_003, 401);
        let prepared = runtime.prepare(&episode).unwrap();
        assert_eq!(
            (
                prepared.observation.organism_tick,
                prepared.observation.fabric_generation,
                prepared.observation.mounted_generation,
            ),
            (8_004, 402, 1)
        );
        assert_eq!(prepared.receptor_ingress.witness_count(), 2);
        assert_eq!(
            runtime
                .pending
                .as_ref()
                .expect("one prepared resident successor")
                .envelope,
            expected
        );
    }

    #[test]
    fn dsf_delivery_repetition_cannot_claim_cognition_or_survive_as_a_false_mosaic() {
        let mut runtime = resident(91, 17);
        let first = runtime
            .prepare(&source_with_port_count("formation-origin", 4))
            .unwrap();
        assert!(!first.observation.cognitive_formation_claimed);
        assert_eq!(first.observation.cognitive_ordinal, 0);
        assert_eq!(first.observation.cognitive_trace_count, 0);
        assert_eq!(first.observation.cognitive_mosaic_count, 0);
        runtime.commit(first.token).unwrap();

        let second = runtime
            .prepare(&source_with_port_count("formation-recurrence", 4))
            .unwrap();
        assert!(!second.observation.cognitive_formation_claimed);
        assert_eq!(second.observation.cognitive_ordinal, 0);
        assert_eq!(second.observation.cognitive_trace_count, 0);
        assert_eq!(second.observation.cognitive_mosaic_count, 0);
        assert_eq!(second.observation.formation_activation_count, 0);
        assert_eq!(second.observation.partial_cue_reassembly_count, 0);
        runtime.commit(second.token).unwrap();

        let saved = runtime.active_envelope().to_vec();
        let mut restored =
            ResidentOrganismRuntime::restore_envelope(saved.clone(), budget()).unwrap();
        assert_eq!(restored.active_envelope(), saved);
        assert_eq!(restored.observation().cognitive_ordinal, 0);
        assert_eq!(restored.observation().cognitive_trace_count, 0);
        assert_eq!(restored.observation().cognitive_mosaic_count, 0);

        let partial = restored
            .prepare(&source_with_port_count("formation-partial-cue", 3))
            .unwrap();
        assert!(!partial.observation.cognitive_formation_claimed);
        assert_eq!(partial.observation.formation_activation_count, 0);
        assert_eq!(partial.observation.partial_cue_reassembly_count, 0);
        assert_eq!(partial.observation.cognitive_mosaic_count, 0);
        restored.commit(partial.token).unwrap();

        let restarted = ResidentOrganismRuntime::restore_envelope(
            restored.active_envelope().to_vec(),
            budget(),
        )
        .unwrap();
        assert_eq!(restarted.observation().cognitive_ordinal, 0);
        assert_eq!(restarted.observation().cognitive_mosaic_count, 0);
    }

    #[test]
    fn resident_readiness_and_save_observe_active_not_pending() {
        let mut runtime = resident(91, 17);
        let active = runtime.observation();
        let active_bytes = runtime.active_envelope().to_vec();
        let prepared = runtime.prepare(&source("hidden-pending-step")).unwrap();
        assert_ne!(prepared.observation.state_receipt, active.state_receipt);
        assert_eq!(runtime.observation(), active);
        assert_eq!(runtime.active_envelope(), active_bytes);
        runtime.commit(prepared.token).unwrap();
        assert_eq!(runtime.observation(), prepared.observation);
        assert_eq!(
            sha256(runtime.active_envelope()),
            prepared.observation.state_receipt
        );
    }

    #[test]
    fn resident_restore_is_current_envelope_only() {
        let raw_fabric =
            encode_fabric(17, &genesis_joint(), &genesis_cognitive(), budget()).unwrap();
        assert_eq!(
            ResidentOrganismRuntime::restore_envelope(raw_fabric, budget()).unwrap_err(),
            RuntimeError::BadEnvelopeMagic
        );
        let sealed = restored(91, 17).seal(budget().max_envelope_bytes).unwrap();
        let mut old_fabric = sealed.bytes;
        old_fabric[FIXED_BYTES..FIXED_BYTES + 8].copy_from_slice(b"GLMFAB03");
        assert_eq!(
            ResidentOrganismRuntime::restore_envelope(old_fabric, budget()).unwrap_err(),
            RuntimeError::BadFabricMagic
        );
    }

    #[test]
    fn resident_organism_ten_thousand_commits_never_redecode_predecessor() {
        const COMMIT_COUNT: usize = 10_000;
        let mut runtime = resident(91, 17);
        let recurrent_source = source("resident-organism-recurrence");
        let mut evaluations = 0usize;
        for _ in 0..COMMIT_COUNT {
            let prepared = runtime.prepare(&recurrent_source).unwrap();
            assert_eq!(prepared.phase_counts.predecessor_authentication_count, 0);
            assert_eq!(prepared.phase_counts.predecessor_decode_count, 0);
            assert_eq!(prepared.phase_counts.predecessor_rebuilt_field_count, 0);
            assert_eq!(prepared.phase_counts.current_cohort_evaluation_count, 1);
            assert_eq!(prepared.receptor_ingress.witness_count(), 2);
            assert_eq!(prepared.receptor_ingress.reached_neuron_visit_count(), 2);
            assert_eq!(prepared.receptor_ingress.witness_construction_count(), 2);
            evaluations += prepared.phase_counts.current_cohort_evaluation_count;
            runtime.commit(prepared.token).unwrap();
        }
        assert_eq!(evaluations, COMMIT_COUNT);
        assert_eq!(runtime.observation().organism_tick, 10_091);
        assert_eq!(runtime.observation().fabric_generation, 10_017);
        assert_eq!(runtime.observation().mounted_generation, 10_000);
        assert_eq!(
            runtime.cold_restore_work(),
            ResidentMountedRestoreWork {
                authentication_count: 1,
                decode_count: 1,
                rebuilt_predecessor_field_count: 0,
            }
        );
    }

    #[test]
    fn envelope_identity_and_current_schema_are_fail_closed() {
        let raw_fabric =
            encode_fabric(17, &genesis_joint(), &genesis_cognitive(), budget()).unwrap();
        assert_eq!(
            OrganismRuntime::restore_envelope(raw_fabric, budget()).unwrap_err(),
            RuntimeError::BadEnvelopeMagic
        );
        let sealed = restored(91, 17).seal(budget().max_envelope_bytes).unwrap();
        let mut changed_identity = sealed.bytes.clone();
        changed_identity[MAGIC.len() + 2] = b'G';
        assert_eq!(
            OrganismRuntime::restore_envelope(changed_identity, budget()).unwrap_err(),
            RuntimeError::InvalidIdentity
        );
        let mut old_fabric = sealed.bytes;
        old_fabric[FIXED_BYTES..FIXED_BYTES + 8].copy_from_slice(b"GLMFAB03");
        assert_eq!(
            OrganismRuntime::restore_envelope(old_fabric, budget()).unwrap_err(),
            RuntimeError::BadFabricMagic
        );
    }

    #[test]
    fn authenticated_legacy_migration_emits_only_one_current_runtime_envelope() {
        let legacy = legacy_fabric();
        let authority = test_migration_authority(&legacy);
        let result = migrate_authenticated_legacy_predecessor(
            legacy.clone(),
            sha256(&legacy),
            IDENTITY,
            91,
            budget(),
            authority,
        )
        .unwrap();
        assert_eq!(&result.sealed.bytes[..8], MAGIC);
        assert_eq!(result.legacy_fabric_receipt, sha256(&legacy));
        assert_eq!(&result.observation.identity, IDENTITY.as_bytes());
        assert_eq!(result.observation.organism_tick, 91);
        assert_eq!(result.observation.fabric_generation, 17);
        assert_eq!(result.observation.mounted_generation, 13);
        assert!(!result.observation.mounted_step_completed);
        assert!(!result.observation.physical_transition_claimed);
        assert!(!result.observation.cognitive_formation_claimed);
        assert_eq!(result.observation.python_callback_count, 0);
        assert_eq!(result.observation.dsf_delivery_count, 0);
        assert_eq!(result.observation.complete_neuron_fractal_count, 0);
        assert_eq!(
            result.observation.recurrent_complete_neuron_fractal_count,
            0
        );
        assert_eq!(result.observation.source_cohort_l0_l4_evaluation_count, 0);
        assert_eq!(result.observation.successor_l0_l4_replay_count, 0);
        let restored = OrganismRuntime::restore_envelope(result.sealed.bytes, budget()).unwrap();
        assert_eq!(restored.observe().organism_tick, 91);
    }

    #[test]
    fn authenticated_legacy_migration_refuses_wrong_hash_schema_identity_and_tick() {
        let legacy = legacy_fabric();
        let authority = test_migration_authority(&legacy);
        let mut wrong_hash = sha256(&legacy);
        wrong_hash[0] ^= 1;
        assert_eq!(
            migrate_authenticated_legacy_predecessor(
                legacy.clone(),
                wrong_hash,
                IDENTITY,
                91,
                budget(),
                authority,
            )
            .unwrap_err(),
            RuntimeError::LegacyMigration(
                "GLMFAB03 content SHA-256 does not bind the exact body".into()
            )
        );

        let current = encode_fabric(17, &legacy_joint(), &genesis_cognitive(), budget()).unwrap();
        let current_authority = LegacyMigrationAuthority {
            fabric_receipt: sha256(&current),
            ..authority
        };
        assert_eq!(
            migrate_authenticated_legacy_predecessor(
                current.clone(),
                sha256(&current),
                IDENTITY,
                91,
                budget(),
                current_authority,
            )
            .unwrap_err(),
            RuntimeError::LegacyMigration("materialized source evidence is not GLMFAB03".into())
        );

        assert_eq!(
            migrate_authenticated_legacy_predecessor(
                legacy.clone(),
                sha256(&legacy),
                "12345678-9abc-4def-8123-456789abcdeG",
                91,
                budget(),
                authority,
            )
            .unwrap_err(),
            RuntimeError::InvalidIdentity
        );
        assert_eq!(
            migrate_authenticated_legacy_predecessor(
                legacy.clone(),
                sha256(&legacy),
                "22345678-9abc-4def-8123-456789abcdef",
                91,
                budget(),
                authority,
            )
            .unwrap_err(),
            RuntimeError::Task853IdentityMismatch
        );
        assert_eq!(
            migrate_authenticated_legacy_predecessor(
                legacy.clone(),
                sha256(&legacy),
                IDENTITY,
                92,
                budget(),
                authority,
            )
            .unwrap_err(),
            RuntimeError::Task853TickMismatch
        );
    }

    #[test]
    fn migration_output_cannot_reenter_the_one_shot_boundary() {
        let legacy = legacy_fabric();
        let authority = test_migration_authority(&legacy);
        let first = migrate_authenticated_legacy_predecessor(
            legacy.clone(),
            sha256(&legacy),
            IDENTITY,
            91,
            budget(),
            authority,
        )
        .unwrap();
        let output = first.sealed.bytes;
        let output_authority = LegacyMigrationAuthority {
            fabric_receipt: sha256(&output),
            ..authority
        };
        assert_eq!(
            migrate_authenticated_legacy_predecessor(
                output.clone(),
                sha256(&output),
                IDENTITY,
                91,
                budget(),
                output_authority,
            )
            .unwrap_err(),
            RuntimeError::LegacyMigration("materialized source evidence is not GLMFAB03".into())
        );
    }

    #[test]
    #[ignore = "requires GUALA_TASK853_GLMFAB03 to name the authenticated predecessor"]
    fn exact_task853_predecessor_migrates_to_one_current_glorun() {
        let path = std::env::var("GUALA_TASK853_GLMFAB03")
            .expect("GUALA_TASK853_GLMFAB03 must name the authenticated predecessor");
        let legacy = std::fs::read(path).expect("read authenticated task-853 predecessor");
        let migrated = migrate_authenticated_task853_predecessor(
            legacy,
            TASK853_GLMFAB03_SHA256,
            TASK853_IDENTITY,
            TASK853_ORGANISM_TICK,
            RuntimeBudget::new(67_108_864, 67_108_000, 536_870_912).unwrap(),
        )
        .unwrap();
        assert_eq!(&migrated.sealed.bytes[..8], MAGIC);
        assert_eq!(migrated.legacy_fabric_receipt, TASK853_GLMFAB03_SHA256);
        let parsed = parse_current_envelope(
            &migrated.sealed.bytes,
            RuntimeBudget::new(67_108_864, 67_108_000, 536_870_912).unwrap(),
        )
        .unwrap();
        assert_eq!(&parsed.joint_bytes[..8], b"GLJDSF03");
        assert_eq!(migrated.observation.organism_tick, TASK853_ORGANISM_TICK);
        assert_eq!(migrated.observation.fabric_generation, 13);
        assert_eq!(migrated.observation.mounted_generation, 2);
        assert_eq!(migrated.observation.joint_field_count, 2);
        assert_eq!(migrated.observation.joint_neuron_count, 96);
        assert!(!migrated.observation.mounted_step_completed);
        assert!(!migrated.observation.physical_transition_claimed);
        assert!(!migrated.observation.cognitive_formation_claimed);
        assert_eq!(migrated.observation.complete_neuron_fractal_count, 0);
        assert_eq!(
            migrated.observation.recurrent_complete_neuron_fractal_count,
            0
        );
        assert_eq!(migrated.observation.python_callback_count, 0);
    }

    #[test]
    fn pyo3_registration_exports_each_runtime_callable_once() {
        pyo3::prepare_freethreaded_python();
        Python::with_gil(|py| {
            let module = PyModule::new(py, "guala_core_runtime_registration").unwrap();
            register(&module).unwrap();
            let keys = module
                .dict()
                .keys()
                .iter()
                .map(|key| key.extract::<String>().unwrap())
                .collect::<Vec<_>>();
            for name in [
                "transition_native_organism_runtime",
                "restore_native_organism_runtime",
                "restore_native_resident_organism_runtime",
                "migrate_authenticated_task853_predecessor_to_native_organism_runtime",
            ] {
                assert_eq!(
                    keys.iter()
                        .filter(|candidate| candidate.as_str() == name)
                        .count(),
                    1
                );
                assert!(module.getattr(name).unwrap().is_callable());
            }
            for name in [
                "NativeResidentOrganismRuntime",
                "NativeResidentOrganismObservation",
                "NativeResidentOrganismPrepare",
            ] {
                assert_eq!(
                    keys.iter()
                        .filter(|candidate| candidate.as_str() == name)
                        .count(),
                    1
                );
            }
        });
    }

    fn task853_bytes(output: &mut Vec<u8>, value: &[u8]) {
        output.extend_from_slice(&u32::try_from(value.len()).unwrap().to_le_bytes());
        output.extend_from_slice(value);
    }

    #[allow(clippy::too_many_arguments)]
    fn task853_current_source_port(
        output: &mut Vec<u8>,
        sense: u8,
        topology_index: u32,
        sensor_id: &str,
        substream_id: &str,
        coordinates: &[(&str, String)],
        physical_quantity: &str,
        physical_unit: &str,
        source_times: [i64; 3],
        dimensionless_fields: [i64; 3],
    ) {
        output.push(sense);
        output.extend_from_slice(&topology_index.to_le_bytes());
        text(output, sensor_id);
        text(output, substream_id);
        output.extend_from_slice(&u16::try_from(coordinates.len()).unwrap().to_le_bytes());
        for (axis_id, coordinate_id) in coordinates {
            text(output, axis_id);
            text(output, coordinate_id);
        }
        text(output, physical_quantity);
        text(output, physical_unit);
        text(output, "direct-physical-source");
        text(output, "");
        text(output, "identity-binary64");
        rational(output, -1, 1);
        rational(output, 1, 1);
        rational(output, 0, 1);
        rational(output, 1, 1);
        task853_bytes(output, b"identity-binary64-v1");
        output.extend_from_slice(&3_u32.to_le_bytes());
        for (source_time, field) in source_times.into_iter().zip(dimensionless_fields) {
            rational(output, source_time, 1);
            output.extend_from_slice(&(field as f64).to_bits().to_le_bytes());
            rational(output, 0, 1);
            rational(output, 1, 1);
            rational(output, field, 1);
        }
    }

    fn task853_current_occurrence(
        output: &mut Vec<u8>,
        first_port: u32,
        port_count: u32,
        source_times: [i64; 3],
        group_width: u32,
    ) {
        output.extend_from_slice(&port_count.to_le_bytes());
        for port_index in first_port..first_port + port_count {
            output.extend_from_slice(&port_index.to_le_bytes());
        }
        output.extend_from_slice(&3_u32.to_le_bytes());
        for source_time in source_times {
            rational(output, source_time, 1);
        }
        task853_bytes(
            output,
            crate::joint_uf_source_adapter::SAMPLED_VOLUME_AND_RELEVANCE_PIECEWISE_LINEAR_PROFILE,
        );
        assert_eq!(port_count % group_width, 0);
        let group_count = port_count / group_width;
        output.extend_from_slice(&group_count.to_le_bytes());
        for group_index in 0..group_count {
            output.extend_from_slice(&group_width.to_le_bytes());
            for member_offset in 0..group_width {
                output
                    .extend_from_slice(&(group_index * group_width + member_offset).to_le_bytes());
            }
        }
        task853_bytes(output, b"explicit-joint-relevance-v1");
        output.extend_from_slice(&3_u32.to_le_bytes());
        for _ in 0..3 {
            rational(output, 1, 1);
        }
    }

    fn task853_current_two_clock_source() -> NativeJointSourceEpisode {
        let mut output = b"GLJSRC02".to_vec();
        output.extend_from_slice(&2_u16.to_le_bytes());
        text(&mut output, "task853-current-two-clock-sight-sound");
        output.extend_from_slice(&[0, 0, 1, 1, 1, 1]);
        output.extend_from_slice(&96_u32.to_le_bytes());

        for topology_index in 0_u32..64 {
            let row = topology_index / 8;
            let column = topology_index % 8;
            let fields = if topology_index % 2 == 0 {
                [0, 1, 0]
            } else {
                [0, -1, 0]
            };
            task853_current_source_port(
                &mut output,
                0,
                topology_index,
                "browser-camera-retina-8x8",
                &format!("receptor-r{row}-c{column}"),
                &[
                    ("retina-row", row.to_string()),
                    ("retina-column", column.to_string()),
                ],
                "reset-referenced-area-mean-light-intensity",
                "normalized-sensor-code",
                [1, 2, 3],
                fields,
            );
        }

        for topology_index in 0_u32..32 {
            let band = topology_index / 2;
            let is_pressure = topology_index % 2 == 0;
            let component = if is_pressure {
                "pressure-envelope"
            } else {
                "carrier-phase-advance"
            };
            let substream = if is_pressure {
                format!("erb_{band:02}_pressure")
            } else {
                format!("erb_{band:02}_phase_advance")
            };
            let (quantity, unit) = if is_pressure {
                ("cochlear-pressure-envelope", "full-scale-pressure")
            } else {
                (
                    "cochlear-carrier-phase-advance",
                    "nyquist-fraction-per-observation-hop",
                )
            };
            let fields = if topology_index % 4 < 2 {
                [0, 1, 0]
            } else {
                [0, -1, 0]
            };
            task853_current_source_port(
                &mut output,
                1,
                topology_index,
                "microphone-gammatone-cochlear-field",
                &substream,
                &[
                    ("erb-band", format!("{band:02}")),
                    ("cochlear-component", component.to_owned()),
                ],
                quantity,
                unit,
                [10, 12, 14],
                fields,
            );
        }

        output.extend_from_slice(&2_u32.to_le_bytes());
        task853_current_occurrence(&mut output, 0, 64, [1, 2, 3], 8);
        task853_current_occurrence(&mut output, 64, 32, [10, 12, 14], 2);
        decode_native_joint_source_episode(&output, 96, 288, 2, 6).unwrap()
    }

    fn task853_lineage(ordinal: u64) -> [u8; 16] {
        let mut lineage = [0_u8; 16];
        lineage[..8].copy_from_slice(b"GLNLINE1");
        lineage[8..].copy_from_slice(&ordinal.to_be_bytes());
        lineage
    }

    fn task853_prepared_lineages(
        prepared: &crate::mounted_joint_fractal::PreparedMountedGeneration,
    ) -> std::collections::BTreeSet<[u8; 16]> {
        prepared
            .fields()
            .iter()
            .flat_map(|field| field.neurons())
            .map(|neuron| neuron.successor().neuron_lineage)
            .collect()
    }

    fn task853_reconstruct_balanced_ternary(
        trits: &[crate::joint_uf_neuron_boundary::BalancedTrit],
    ) -> num_bigint::BigInt {
        use crate::joint_uf_neuron_boundary::BalancedTrit;
        let mut value = num_bigint::BigInt::from(0);
        let mut place = num_bigint::BigInt::from(1);
        for trit in trits {
            let digit = match trit {
                BalancedTrit::Negative => -1,
                BalancedTrit::Quiescent => 0,
                BalancedTrit::Positive => 1,
            };
            value += num_bigint::BigInt::from(digit) * &place;
            place *= 3_u8;
        }
        value
    }

    #[test]
    #[ignore = "requires the authenticated /tmp/guala-task853-glmfab03.bin predecessor"]
    fn exact_task853_lineages_survive_enriched_two_clock_delivery_and_cold_restore() {
        use num_rational::BigRational;
        use num_traits::ToPrimitive;

        use crate::joint_uf_neuron_boundary::{settle_shared_dsf_mathloom, MathLoomAnatomy};
        use crate::ordered_gate_delivery_candidate::prepare_authenticated_ordered_gate_delivery;

        const STATE_LIMIT: usize = 67_108_000;
        const WORKING_LIMIT: usize = 536_870_912;

        let runtime_budget = RuntimeBudget::new(67_108_864, STATE_LIMIT, WORKING_LIMIT).unwrap();
        let legacy = std::fs::read("/tmp/guala-task853-glmfab03.bin")
            .expect("read authenticated task853 GLMFAB03 predecessor");
        let migrated = migrate_authenticated_task853_predecessor(
            legacy,
            TASK853_GLMFAB03_SHA256,
            TASK853_IDENTITY,
            TASK853_ORGANISM_TICK,
            runtime_budget,
        )
        .unwrap();
        let parsed = parse_current_envelope(&migrated.sealed.bytes, runtime_budget).unwrap();
        assert_eq!(&parsed.joint_bytes[..8], b"GLJDSF03");
        assert_eq!(parsed.fabric_generation, 13);

        let (restored_predecessor, predecessor_summary) =
            restore_resident_mounted_state(parsed.joint_bytes, STATE_LIMIT, WORKING_LIMIT).unwrap();
        assert_eq!(predecessor_summary.generation, 2);
        assert_eq!(predecessor_summary.joint_neuron_count, 96);

        let source = task853_current_two_clock_source();
        assert_eq!(source.joint_source_ports().len(), 96);
        assert_eq!(source.joint_source_occurrences().len(), 2);
        assert_eq!(
            source.joint_source_occurrences()[0].source_times,
            [
                BigRational::from_integer(1.into()),
                BigRational::from_integer(2.into()),
                BigRational::from_integer(3.into()),
            ]
        );
        assert_eq!(
            source.joint_source_occurrences()[1].source_times,
            [
                BigRational::from_integer(10.into()),
                BigRational::from_integer(12.into()),
                BigRational::from_integer(14.into()),
            ]
        );

        let prepared = prepare_resident_mounted_generation(
            &restored_predecessor,
            &source,
            STATE_LIMIT,
            WORKING_LIMIT,
        )
        .unwrap();
        assert_eq!(prepared.predecessor_generation(), 2);
        assert_eq!(prepared.successor_generation(), 3);
        assert_eq!(prepared.transition().joint_neuron_count, 96);
        assert_eq!(
            prepared.phase_counts().retained_neuron_index_entry_count,
            96
        );
        assert_eq!(prepared.phase_counts().reached_neuron_lookup_count, 96);

        let expected_lineages = (1_u64..=96)
            .map(task853_lineage)
            .collect::<std::collections::BTreeSet<_>>();
        assert_eq!(task853_prepared_lineages(&prepared), expected_lineages);
        for field in prepared.fields() {
            assert_eq!(field.source_ports().len(), field.neurons().len());
            for (source_port, neuron) in field.source_ports().iter().zip(field.neurons()) {
                let expected_ordinal = match source_port.sense {
                    0 => u64::from(source_port.topology_index) + 1,
                    1 => u64::from(source_port.topology_index) + 65,
                    other => panic!("unexpected task853 sense {other}"),
                };
                assert_eq!(
                    neuron.successor().neuron_lineage,
                    task853_lineage(expected_ordinal)
                );
                assert_eq!(source_port.coordinates.len(), 2);
            }
        }

        let delivery_plan =
            prepare_authenticated_ordered_gate_delivery(&prepared, &source).unwrap();
        assert_eq!(delivery_plan.occurrence_count(), 2);
        assert_eq!(delivery_plan.lineage_count(), 96);
        assert_eq!(delivery_plan.ordered_occurrences()[0].lineage_count(), 64);
        assert_eq!(delivery_plan.ordered_occurrences()[1].lineage_count(), 32);
        assert_eq!(
            delivery_plan
                .ordered_occurrences()
                .iter()
                .flat_map(|occurrence| occurrence.bindings())
                .map(|binding| binding.lineage())
                .collect::<std::collections::BTreeSet<_>>(),
            expected_lineages
        );

        let anatomy = MathLoomAnatomy::new(delivery_plan.required_mathloom_positions()).unwrap();
        for occurrence in delivery_plan.ordered_occurrences() {
            assert_eq!(
                occurrence.occurrence_index(),
                if occurrence.lineage_count() == 64 {
                    0
                } else {
                    1
                }
            );
            let observed_gate_order = occurrence
                .ordered_gates()
                .map(|gate| {
                    assert_eq!(gate.occurrence_index(), occurrence.occurrence_index());
                    for binding in gate.bindings().iter().copied() {
                        assert_eq!(binding.occurrence_index(), occurrence.occurrence_index());
                        let source_port = &source.joint_source_ports()[binding.source_port_index()];
                        let perspective = gate.perspective(binding).unwrap();
                        assert_eq!(perspective.coordinate_index(), binding.coordinate_index());
                        for local_index in 0..perspective.local_sev_len() {
                            let local = perspective.local_sev(local_index).unwrap();
                            let source_index = local.source_index();
                            let expected_field = source_port.dimensionless_fields[source_index]
                                .to_f64()
                                .unwrap();
                            let expected_delta = if source_index == 0 {
                                0.0
                            } else {
                                expected_field
                                    - source_port.dimensionless_fields[source_index - 1]
                                        .to_f64()
                                        .unwrap()
                            };
                            assert_eq!(local.field().to_bits(), expected_field.to_bits());
                            assert_eq!(local.delta_field().to_bits(), expected_delta.to_bits());
                        }

                        let delivery = settle_shared_dsf_mathloom(perspective, anatomy).unwrap();
                        assert_eq!(delivery.constraints().len(), 7);
                        for (constraint, dsf_value) in delivery
                            .constraints()
                            .iter()
                            .zip(perspective.dsf().ordered())
                        {
                            assert_eq!(constraint.binary64_bits(), dsf_value.to_bits());
                            assert_eq!(
                                constraint.exact_value().to_f64().unwrap().to_bits(),
                                dsf_value.to_bits()
                            );
                            let numerator =
                                task853_reconstruct_balanced_ternary(constraint.word().numerator());
                            let denominator = task853_reconstruct_balanced_ternary(
                                constraint.word().denominator(),
                            );
                            assert_eq!(
                                BigRational::new(numerator, denominator),
                                *constraint.exact_value()
                            );
                        }
                    }
                    gate.gate_index()
                })
                .collect::<Vec<_>>();
            assert_eq!(
                observed_gate_order,
                (0..occurrence.gate_count()).collect::<Vec<_>>()
            );
        }

        let prepared_bytes = prepared.state_bytes().to_vec();
        let (cold_resident, cold_summary) =
            restore_resident_mounted_state(&prepared_bytes, STATE_LIMIT, WORKING_LIMIT).unwrap();
        assert_eq!(cold_summary.generation, 3);
        assert_eq!(cold_summary.joint_neuron_count, 96);

        let recurrent = prepare_resident_mounted_generation(
            &cold_resident,
            &source,
            STATE_LIMIT,
            WORKING_LIMIT,
        )
        .unwrap();
        assert_eq!(recurrent.predecessor_generation(), 3);
        assert_eq!(recurrent.successor_generation(), 4);
        assert_eq!(recurrent.transition().joint_neuron_count, 96);
        assert_eq!(task853_prepared_lineages(&recurrent), expected_lineages);
        assert_eq!(
            recurrent.phase_counts().retained_neuron_index_entry_count,
            96
        );
        assert_eq!(recurrent.phase_counts().reached_neuron_lookup_count, 96);

        let (_, second_cold_summary) =
            restore_resident_mounted_state(recurrent.state_bytes(), STATE_LIMIT, WORKING_LIMIT)
                .unwrap();
        assert_eq!(second_cold_summary.generation, 4);
        assert_eq!(second_cold_summary.joint_neuron_count, 96);
    }
}
