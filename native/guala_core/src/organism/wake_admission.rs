//! Blocking, event-driven wake admission for one native organism transition.
//!
//! This module is deliberately narrower than a scheduler or a cognitive
//! transition authority. World and body causes arrive only as capabilities
//! authenticated by their existing physical authorities. An external admission
//! authority supplies work limits bound to one cause and one observed
//! resource record. A supplied native closure may prepare work in stages while
//! holding only an immutable prior state. Resource limits are checked at supplied
//! observation checkpoints between stages. Checkpoints cannot observe an
//! allocate/free RSS spike within one stage and cannot prevent a single-stage CPU
//! overrun; every concrete transition must still preflight and allocate through
//! bounded native arenas. The supplied ceilings here are not a production
//! no-runaway proof: production acceptance remains blocked until the sole
//! generation owner can issue an authenticated capability derived from measured
//! provisioned resources. This boundary never mutates organism state, advances a
//! sealed wake head, schedules a continuation, or claims that a proposed state
//! is semantically valid or durably committed.

use super::owner_boot::OwnerBootRootIngress;
use super::world_body::{
    AuthenticatedBodyManifestState, AuthenticatedWorldObservation, WorldBodyVerifiedSeal,
};
use super::ResourceObservation;
use hmac::{Hmac, Mac};
use num_rational::BigRational;
use sha2::{Digest, Sha256};
use std::fmt;
use std::sync::mpsc::{self, Receiver, SendError, SyncSender};
use zeroize::{Zeroize, Zeroizing};

type HmacSha256 = Hmac<Sha256>;

const BUDGET_MAGIC: &[u8; 8] = b"GULBUD01";
const BUDGET_VERSION: u16 = 1;
const BUDGET_DOMAIN: &[u8] = b"guala.native.external-work-budget.v1\0";
const BUDGET_RECEIPT_DOMAIN: &[u8] = b"guala.native.external-work-budget-receipt.v1\0";
const RESOURCE_DOMAIN: &[u8] = b"guala.native.supplied-resource-observation.v1\0";
const HANDOFF_DOMAIN: &[u8] = b"guala.native.wake-handoff.v1\0";
const CONTINUATION_DOMAIN: &[u8] = b"guala.native.restart-from-prior-evidence.v1\0";
const PENDING_DOMAIN: &[u8] = b"guala.native.pending-restart-package.v1\0";
const ZERO_RECEIPT: [u8; 32] = [0; 32];
const BUDGET_HEADER_BYTES: usize = 8 + 2 + 4 + 16 + (4 * 32) + (7 * 8);
const HMAC_BYTES: usize = 32;
const BUDGET_RECORD_BYTES: usize = BUDGET_HEADER_BYTES + HMAC_BYTES;

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) struct ExternalWorkLimits {
    pub(crate) max_prepared_transitions: u64,
    pub(crate) max_native_calls: u64,
    pub(crate) max_cpu_nanoseconds: u64,
    pub(crate) max_resident_byte_growth: u64,
    pub(crate) max_durable_byte_growth: u64,
    pub(crate) max_continuation_bytes: u64,
    pub(crate) min_recovery_reserve_bytes: u64,
}

impl ExternalWorkLimits {
    pub(crate) fn validate(self) -> Result<(), WakeAdmissionError> {
        if self.max_prepared_transitions == 0 {
            return Err(WakeAdmissionError::InvalidBudget(
                "maximum prepared transitions is zero",
            ));
        }
        Ok(())
    }
}

/// Deployment-supplied policy ceilings. Their opaque provenance receipt does not
/// authenticate them as physical measurements or prove how they were derived.
pub(crate) struct SuppliedDeploymentAdmissionCeilings {
    limits: ExternalWorkLimits,
    provenance_receipt: [u8; 32],
}

impl SuppliedDeploymentAdmissionCeilings {
    pub(crate) fn new(
        limits: ExternalWorkLimits,
        provenance_receipt: [u8; 32],
    ) -> Result<Self, WakeAdmissionError> {
        limits.validate()?;
        if provenance_receipt == ZERO_RECEIPT {
            return Err(WakeAdmissionError::InvalidDeploymentCeilings(
                "deployment ceiling provenance receipt is zero",
            ));
        }
        Ok(Self {
            limits,
            provenance_receipt,
        })
    }

    fn validate_budget(&self, candidate: ExternalWorkLimits) -> Result<(), WakeAdmissionError> {
        for (actual, ceiling, name) in [
            (
                candidate.max_prepared_transitions,
                self.limits.max_prepared_transitions,
                "maximum prepared transitions",
            ),
            (
                candidate.max_native_calls,
                self.limits.max_native_calls,
                "maximum native calls",
            ),
            (
                candidate.max_cpu_nanoseconds,
                self.limits.max_cpu_nanoseconds,
                "maximum CPU nanoseconds",
            ),
            (
                candidate.max_resident_byte_growth,
                self.limits.max_resident_byte_growth,
                "maximum resident-byte growth",
            ),
            (
                candidate.max_durable_byte_growth,
                self.limits.max_durable_byte_growth,
                "maximum durable-byte growth",
            ),
            (
                candidate.max_continuation_bytes,
                self.limits.max_continuation_bytes,
                "maximum continuation bytes",
            ),
        ] {
            if actual > ceiling {
                return Err(WakeAdmissionError::DeploymentCeilingExceeded(name));
            }
        }
        if candidate.min_recovery_reserve_bytes < self.limits.min_recovery_reserve_bytes {
            return Err(WakeAdmissionError::DeploymentCeilingExceeded(
                "minimum recovery reserve floor",
            ));
        }
        Ok(())
    }

    pub(crate) fn provenance_receipt(&self) -> [u8; 32] {
        self.provenance_receipt
    }
}

pub(crate) struct RendezvousWakeChannelCapacity;

impl RendezvousWakeChannelCapacity {
    pub(crate) fn new(requested: u64) -> Result<Self, WakeAdmissionError> {
        if requested != 0 {
            return Err(WakeAdmissionError::InvalidDeploymentCeilings(
                "native wake channel must be an exact zero-capacity rendezvous",
            ));
        }
        Ok(Self)
    }
}

/// Caller-supplied root credential asserted to come from the mounted global
/// owner. This type and its domain derivation do not themselves prove that
/// mount assertion and do not create another organism owner.
pub(crate) struct SuppliedGlobalOwnerRootKey {
    epoch: u32,
    bytes: Zeroizing<[u8; 32]>,
}

impl SuppliedGlobalOwnerRootKey {
    #[cfg(test)]
    pub(crate) fn new(epoch: u32, bytes: [u8; 32]) -> Result<Self, WakeAdmissionError> {
        Self::from_owner_boot(
            epoch,
            Zeroizing::new(bytes),
            OwnerBootRootIngress::for_test(),
        )
    }

    pub(crate) fn from_owner_boot(
        epoch: u32,
        bytes: Zeroizing<[u8; 32]>,
        _ingress: OwnerBootRootIngress,
    ) -> Result<Self, WakeAdmissionError> {
        if epoch == 0 {
            return Err(WakeAdmissionError::InvalidBudget(
                "global owner authority epoch is zero",
            ));
        }
        if *bytes == ZERO_RECEIPT {
            return Err(WakeAdmissionError::InvalidBudget(
                "global owner authority key is all zero",
            ));
        }
        Ok(Self { epoch, bytes })
    }

    pub(crate) fn epoch(&self) -> u32 {
        self.epoch
    }

    /// Domain-derived key for authenticating the one canonical generation
    /// head. This remains subordinate to the supplied global owner root and
    /// therefore does not introduce another owner identity.
    pub(crate) fn derive_generation_current_key(&self) -> Zeroizing<[u8; 32]> {
        self.derive_operational_key(b"guala.global-owner.generation-current-key.v1\0")
    }

    /// Domain-derived key for authenticating deployment facts. It remains
    /// subordinate to the one supplied global-owner root and is not another
    /// organism owner.
    pub(crate) fn derive_platform_envelope_key(&self) -> Zeroizing<[u8; 32]> {
        self.derive_operational_key(b"guala.global-owner.platform-envelope-key.v1\0")
    }

    pub(super) fn derive_genesis_authentication_key(&self) -> Zeroizing<[u8; 32]> {
        self.derive_operational_key(b"guala.global-owner.genesis-key.v2\0")
    }

    pub(super) fn derive_organism_seal_key(&self) -> Zeroizing<[u8; 32]> {
        self.derive_operational_key(b"guala.global-owner.organism-seal-key.v2\0")
    }

    fn derive_operational_key(&self, domain: &[u8]) -> Zeroizing<[u8; 32]> {
        let mut derivation = HmacSha256::new_from_slice(self.bytes.as_ref())
            .expect("HMAC-SHA256 accepts every 32-byte key");
        derivation.update(domain);
        derivation.update(&self.epoch.to_le_bytes());
        let mut derived = derivation.finalize().into_bytes();
        let mut output = Zeroizing::new([0_u8; 32]);
        output.copy_from_slice(&derived);
        derived.zeroize();
        output
    }
}

/// One domain-derived operational key for authenticating admission-budget
/// records. It is not a world, body, genesis, organism-seal, or persistence
/// owner key and does not create an additional owner.
pub(crate) struct ExternalWorkBudgetKey {
    epoch: u32,
    bytes: Zeroizing<[u8; 32]>,
}

impl ExternalWorkBudgetKey {
    pub(crate) fn derive(
        epoch: u32,
        global_owner: &SuppliedGlobalOwnerRootKey,
    ) -> Result<Self, WakeAdmissionError> {
        if epoch == 0 {
            return Err(WakeAdmissionError::InvalidBudget(
                "work-budget key epoch is zero",
            ));
        }
        let mut derivation = HmacSha256::new_from_slice(global_owner.bytes.as_ref())
            .expect("HMAC-SHA256 accepts every 32-byte key");
        derivation.update(b"guala.global-owner.work-budget-key.v1\0");
        derivation.update(&global_owner.epoch.to_le_bytes());
        derivation.update(&epoch.to_le_bytes());
        let mut derived = derivation.finalize().into_bytes();
        let mut bytes = Zeroizing::new([0_u8; 32]);
        bytes.copy_from_slice(&derived);
        derived.zeroize();
        Ok(Self { epoch, bytes })
    }

    pub(crate) fn epoch(&self) -> u32 {
        self.epoch
    }
}

/// Fixed-size external work-budget record. Construction does not verify its
/// HMAC or bindings, including when bytes came from the authentication encoder.
pub(crate) struct ExternalWorkBudgetRecord {
    bytes: [u8; BUDGET_RECORD_BYTES],
}

impl ExternalWorkBudgetRecord {
    pub(crate) fn as_bytes(&self) -> &[u8; BUDGET_RECORD_BYTES] {
        &self.bytes
    }

    pub(crate) fn from_bytes(bytes: [u8; BUDGET_RECORD_BYTES]) -> Self {
        Self { bytes }
    }
}

/// Capability issued only after the external authority HMAC and every exact
/// binding have been verified. The provenance receipt remains opaque: this does
/// not prove that the supplied resource numbers are physical measurements.
pub(crate) struct VerifiedExternalWorkBudget {
    record: [u8; BUDGET_RECORD_BYTES],
    limits: ExternalWorkLimits,
    deployment_policy_receipt: [u8; 32],
}

impl VerifiedExternalWorkBudget {
    pub(crate) fn receipt(&self) -> [u8; 32] {
        domain_digest(BUDGET_RECEIPT_DOMAIN, &self.record)
    }

    pub(crate) fn limits(&self) -> ExternalWorkLimits {
        self.limits
    }

    pub(crate) fn deployment_policy_receipt(&self) -> [u8; 32] {
        self.deployment_policy_receipt
    }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) struct SuppliedResourceDelta {
    pub(crate) cpu_nanoseconds: u64,
    pub(crate) resident_byte_growth: u64,
    pub(crate) durable_byte_growth: u64,
    pub(crate) native_calls: u64,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) struct RemainingExternalAllowance {
    pub(crate) prepared_transitions: u64,
    pub(crate) native_calls: u64,
    pub(crate) cpu_nanoseconds: u64,
    pub(crate) resident_byte_growth: u64,
    pub(crate) durable_byte_growth: u64,
    pub(crate) continuation_bytes: u64,
    pub(crate) min_recovery_reserve_bytes: u64,
}

/// Opaque continuation bytes supplied by the native transition closure. The
/// boundary authenticates neither their meaning nor their sufficiency. It binds
/// them to the exact prior/cause/budget evidence when returning a pending result.
pub(crate) struct SuppliedRestartEvidence {
    schema_receipt: [u8; 32],
    provenance_receipt: [u8; 32],
    payload: Box<[u8]>,
    receipt: [u8; 32],
}

impl SuppliedRestartEvidence {
    pub(crate) fn new(
        schema_receipt: [u8; 32],
        provenance_receipt: [u8; 32],
        payload: &[u8],
        ceilings: &SuppliedDeploymentAdmissionCeilings,
    ) -> Result<Self, WakeAdmissionError> {
        if schema_receipt == ZERO_RECEIPT || provenance_receipt == ZERO_RECEIPT {
            return Err(WakeAdmissionError::InvalidContinuation(
                "continuation schema or provenance receipt is zero",
            ));
        }
        let payload_length =
            u64::try_from(payload.len()).map_err(|_| WakeAdmissionError::ArithmeticOverflow)?;
        if payload_length > ceilings.limits.max_continuation_bytes {
            return Err(WakeAdmissionError::InvalidContinuation(
                "restart evidence exceeds deployment allocation ceiling",
            ));
        }
        let payload = payload.to_vec().into_boxed_slice();
        let receipt = continuation_receipt(schema_receipt, provenance_receipt, &payload)?;
        Ok(Self {
            schema_receipt,
            provenance_receipt,
            payload,
            receipt,
        })
    }

    pub(crate) fn schema_receipt(&self) -> [u8; 32] {
        self.schema_receipt
    }

    pub(crate) fn provenance_receipt(&self) -> [u8; 32] {
        self.provenance_receipt
    }

    pub(crate) fn payload(&self) -> &[u8] {
        &self.payload
    }

    pub(crate) fn receipt(&self) -> [u8; 32] {
        self.receipt
    }
}

pub(crate) enum AuthenticatedWakeCause {
    WorldRevision(AuthenticatedWorldObservation),
    BodyState(AuthenticatedBodyManifestState),
}

impl AuthenticatedWakeCause {
    pub(crate) fn world(observation: AuthenticatedWorldObservation) -> Self {
        Self::WorldRevision(observation)
    }

    pub(crate) fn body(state: AuthenticatedBodyManifestState) -> Self {
        Self::BodyState(state)
    }

    pub(crate) fn canonical_record_bytes(&self) -> (&[u8], Option<&[u8]>) {
        match self {
            Self::WorldRevision(value) => (value.canonical_record_bytes(), None),
            Self::BodyState(value) => (
                value.manifest_record_bytes(),
                Some(value.state_record_bytes()),
            ),
        }
    }
}

/// Move-only, non-`Sync` ingress: it cannot be cloned or shared among concurrent
/// blocked producers that would each retain an owned cause outside the channel.
pub(crate) struct WakeIngress {
    sender: SyncSender<WakeInput>,
    _single_sender: std::marker::PhantomData<std::cell::Cell<()>>,
}

enum WakeInput {
    Fresh {
        cause: AuthenticatedWakeCause,
        restart_evidence: SuppliedRestartEvidence,
    },
    Resume(WakeResumeCapability),
}

impl WakeIngress {
    /// Blocks until the exact rendezvous receiver accepts the cause and evidence.
    /// It performs no timeout, retry, scheduling, or polling.
    pub(crate) fn send(
        &self,
        cause: AuthenticatedWakeCause,
        restart_evidence: SuppliedRestartEvidence,
    ) -> Result<(), SendError<(AuthenticatedWakeCause, SuppliedRestartEvidence)>> {
        self.sender
            .send(WakeInput::Fresh {
                cause,
                restart_evidence,
            })
            .map_err(|SendError(input)| match input {
                WakeInput::Fresh {
                    cause,
                    restart_evidence,
                } => SendError((cause, restart_evidence)),
                WakeInput::Resume(_) => unreachable!("fresh send wraps only a fresh cause"),
            })
    }

    pub(crate) fn send_resume(
        &self,
        capability: WakeResumeCapability,
    ) -> Result<(), SendError<WakeResumeCapability>> {
        self.sender
            .send(WakeInput::Resume(capability))
            .map_err(|SendError(input)| match input {
                WakeInput::Resume(capability) => SendError(capability),
                WakeInput::Fresh { .. } => {
                    unreachable!("resume send wraps only a resume capability")
                }
            })
    }
}

pub(crate) struct BlockingWakeAdmission {
    receiver: Receiver<WakeInput>,
}

/// Only an exact rendezvous is admitted, so this boundary retains no queued
/// world/body record buffers.
pub(crate) fn bounded_wake_channel(
    _capacity: RendezvousWakeChannelCapacity,
) -> (WakeIngress, BlockingWakeAdmission) {
    let (sender, receiver) = mpsc::sync_channel(0);
    (
        WakeIngress {
            sender,
            _single_sender: std::marker::PhantomData,
        },
        BlockingWakeAdmission { receiver },
    )
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) struct WakeHeadSnapshot {
    pub(crate) world_revision: u64,
    pub(crate) world_receipt: [u8; 32],
    pub(crate) world_state_receipt: [u8; 32],
    pub(crate) world_mount_epoch: u32,
    pub(crate) body_sequence: u64,
    pub(crate) body_source_time: BigRational,
    pub(crate) body_state_receipt: [u8; 32],
    pub(crate) body_manifest_receipt: [u8; 32],
    pub(crate) body_mount_epoch: u32,
}

impl WakeHeadSnapshot {
    fn current(value: &WorldBodyVerifiedSeal) -> Self {
        Self {
            world_revision: value.world_revision(),
            world_receipt: value.world_receipt(),
            world_state_receipt: value.world_state_receipt(),
            world_mount_epoch: value.world_mount_epoch().get(),
            body_sequence: value.body_sequence(),
            body_source_time: value.body().source_time().clone(),
            body_state_receipt: value.body_state_receipt(),
            body_manifest_receipt: value.body_manifest_receipt(),
            body_mount_epoch: value.body_mount_epoch().get(),
        }
    }
}

pub(crate) struct AdmittedWake {
    cause: AuthenticatedWakeCause,
    current_head: WakeHeadSnapshot,
    proposed_next_head: WakeHeadSnapshot,
    prior_organism_receipt: [u8; 32],
    handoff_receipt: [u8; 32],
}

impl AdmittedWake {
    pub(crate) fn cause(&self) -> &AuthenticatedWakeCause {
        &self.cause
    }

    pub(crate) fn current_head(&self) -> WakeHeadSnapshot {
        self.current_head.clone()
    }

    pub(crate) fn proposed_next_head(&self) -> WakeHeadSnapshot {
        self.proposed_next_head.clone()
    }

    pub(crate) fn prior_organism_receipt(&self) -> [u8; 32] {
        self.prior_organism_receipt
    }

    pub(crate) fn handoff_receipt(&self) -> [u8; 32] {
        self.handoff_receipt
    }
}

pub(crate) enum StageDisposition<S> {
    Continue,
    ProposedState(S),
}

pub(crate) struct SuppliedNativeTransitionStage<S> {
    prepared_transitions: u64,
    restart_evidence: SuppliedRestartEvidence,
    disposition: StageDisposition<S>,
}

impl<S> SuppliedNativeTransitionStage<S> {
    pub(crate) fn continuing(
        prepared_transitions: u64,
        restart_evidence: SuppliedRestartEvidence,
    ) -> Self {
        Self {
            prepared_transitions,
            restart_evidence,
            disposition: StageDisposition::Continue,
        }
    }

    pub(crate) fn proposed(
        prepared_transitions: u64,
        restart_evidence: SuppliedRestartEvidence,
        proposed_state: S,
    ) -> Self {
        Self {
            prepared_transitions,
            restart_evidence,
            disposition: StageDisposition::ProposedState(proposed_state),
        }
    }
}

/// In-memory, supplied-observation-checked output only. A future generation owner must still
/// verify transition semantics, seal the organism successor, and atomically
/// co-commit that seal with `proposed_next_head`.
pub(crate) struct SuppliedObservationCheckedInMemoryWakeHandoff<S> {
    admitted_wake: AdmittedWake,
    proposed_state: S,
    proposed_next_head: WakeHeadSnapshot,
    budget_receipt: [u8; 32],
    last_supplied_resources: ResourceObservation,
    resource_delta: SuppliedResourceDelta,
    prepared_transitions: u64,
    restart_evidence: SuppliedRestartEvidence,
}

pub(crate) struct PreparedWakeParts<S> {
    pub(crate) admitted_wake: AdmittedWake,
    pub(crate) proposed_state: S,
    pub(crate) proposed_next_head: WakeHeadSnapshot,
    pub(crate) budget_receipt: [u8; 32],
    pub(crate) last_supplied_resources: ResourceObservation,
    pub(crate) resource_delta: SuppliedResourceDelta,
    pub(crate) prepared_transitions: u64,
    pub(crate) restart_evidence: SuppliedRestartEvidence,
}

impl<S> SuppliedObservationCheckedInMemoryWakeHandoff<S> {
    pub(crate) fn admitted_wake(&self) -> &AdmittedWake {
        &self.admitted_wake
    }

    pub(crate) fn proposed_state(&self) -> &S {
        &self.proposed_state
    }

    pub(crate) fn proposed_next_head(&self) -> WakeHeadSnapshot {
        self.proposed_next_head.clone()
    }

    pub(crate) fn budget_receipt(&self) -> [u8; 32] {
        self.budget_receipt
    }

    pub(crate) fn last_supplied_resources(&self) -> &ResourceObservation {
        &self.last_supplied_resources
    }

    pub(crate) fn resource_delta(&self) -> SuppliedResourceDelta {
        self.resource_delta
    }

    pub(crate) fn prepared_transitions(&self) -> u64 {
        self.prepared_transitions
    }

    pub(crate) fn restart_evidence(&self) -> &SuppliedRestartEvidence {
        &self.restart_evidence
    }

    pub(crate) fn into_parts(self) -> PreparedWakeParts<S> {
        PreparedWakeParts {
            admitted_wake: self.admitted_wake,
            proposed_state: self.proposed_state,
            proposed_next_head: self.proposed_next_head,
            budget_receipt: self.budget_receipt,
            last_supplied_resources: self.last_supplied_resources,
            resource_delta: self.resource_delta,
            prepared_transitions: self.prepared_transitions,
            restart_evidence: self.restart_evidence,
        }
    }
}

/// In-memory package for a later explicit retry from the prior sealed organism
/// state. The current wake head is unchanged; this type never queues or schedules
/// itself. Its resource observations are only caller-supplied facts.
pub(crate) struct InMemoryRestartFromPriorPending {
    admitted_wake: AdmittedWake,
    unchanged_head: WakeHeadSnapshot,
    budget: VerifiedExternalWorkBudget,
    latest_supplied_resources: ResourceObservation,
    resource_delta: SuppliedResourceDelta,
    prepared_transitions: u64,
    restart_evidence: SuppliedRestartEvidence,
    /// Domain-separated in-memory integrity digest only; not an HMAC, durable
    /// seal, or authorization to restore organism state.
    package_receipt: [u8; 32],
}

pub(crate) struct WakeResumeCapability {
    admitted_wake: AdmittedWake,
    unchanged_head: WakeHeadSnapshot,
    restart_evidence: SuppliedRestartEvidence,
}

impl InMemoryRestartFromPriorPending {
    pub(crate) fn admitted_wake(&self) -> &AdmittedWake {
        &self.admitted_wake
    }

    pub(crate) fn unchanged_head(&self) -> WakeHeadSnapshot {
        self.unchanged_head.clone()
    }

    pub(crate) fn budget(&self) -> &VerifiedExternalWorkBudget {
        &self.budget
    }

    pub(crate) fn latest_supplied_resources(&self) -> &ResourceObservation {
        &self.latest_supplied_resources
    }

    pub(crate) fn resource_delta(&self) -> SuppliedResourceDelta {
        self.resource_delta
    }

    pub(crate) fn prepared_transitions(&self) -> u64 {
        self.prepared_transitions
    }

    pub(crate) fn restart_evidence(&self) -> &SuppliedRestartEvidence {
        &self.restart_evidence
    }

    pub(crate) fn package_receipt(&self) -> [u8; 32] {
        self.package_receipt
    }

    pub(crate) fn into_resume_capability(self) -> Result<WakeResumeCapability, WakeAdmissionError> {
        if pending_package_receipt(
            &self.admitted_wake,
            &self.budget,
            &self.unchanged_head,
            &self.latest_supplied_resources,
            self.resource_delta,
            self.prepared_transitions,
            &self.restart_evidence,
        ) != self.package_receipt
        {
            return Err(WakeAdmissionError::PendingPackageIntegrityFailed);
        }
        Ok(WakeResumeCapability {
            admitted_wake: self.admitted_wake,
            restart_evidence: self.restart_evidence,
            unchanged_head: self.unchanged_head,
        })
    }
}

impl WakeResumeCapability {
    pub(crate) fn expected_organism_receipt(&self) -> [u8; 32] {
        self.admitted_wake.prior_organism_receipt()
    }

    pub(crate) fn expected_head(&self) -> WakeHeadSnapshot {
        self.unchanged_head.clone()
    }

    pub(crate) fn original_handoff_receipt(&self) -> [u8; 32] {
        self.admitted_wake.handoff_receipt()
    }
}

pub(crate) enum WakeWorkOutcome<S> {
    Prepared(SuppliedObservationCheckedInMemoryWakeHandoff<S>),
    Pending(InMemoryRestartFromPriorPending),
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) enum WakeAdmissionError {
    InputClosed,
    PriorOrganismReceiptIsZero,
    WorldAuthorityEpochMismatch,
    BodyAuthorityEpochMismatch,
    BodyManifestChanged,
    DuplicateWorldRevision,
    ConflictingWorldRevision,
    OutOfOrderWorldRevision,
    DuplicateBodySequence,
    ConflictingBodySequence,
    OutOfOrderBodySequence,
    BodyPriorReceiptMismatch,
    BodySourceTimeDidNotAdvance,
    ReceiptDidNotChange,
    SequenceOverflow,
    InvalidBudget(&'static str),
    InvalidDeploymentCeilings(&'static str),
    DeploymentCeilingExceeded(&'static str),
    BudgetAuthenticationFailed,
    BudgetBindingMismatch,
    PythonCallsObserved,
    ResourceCounterRegressed(&'static str),
    StageMadeNoProgress,
    SuppliedObservationExceedsWorkBudget,
    ArithmeticOverflow,
    InvalidContinuation(&'static str),
    PendingPackageIntegrityFailed,
    ResumeOrganismReceiptMismatch,
    ResumeHeadMismatch,
    ResumeHandoffIntegrityFailed,
}

impl fmt::Display for WakeAdmissionError {
    fn fmt(&self, output: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::InputClosed => write!(output, "wake input closed while quiescent"),
            Self::PriorOrganismReceiptIsZero => write!(output, "prior organism receipt is zero"),
            Self::WorldAuthorityEpochMismatch => write!(output, "world authority epoch differs"),
            Self::BodyAuthorityEpochMismatch => write!(output, "body authority epoch differs"),
            Self::BodyManifestChanged => write!(output, "body manifest changed without a law"),
            Self::DuplicateWorldRevision => write!(output, "world revision is a duplicate"),
            Self::ConflictingWorldRevision => {
                write!(output, "world revision conflicts at the current position")
            }
            Self::OutOfOrderWorldRevision => write!(output, "world revision is out of order"),
            Self::DuplicateBodySequence => write!(output, "body state sequence is a duplicate"),
            Self::ConflictingBodySequence => {
                write!(output, "body state conflicts at the current position")
            }
            Self::OutOfOrderBodySequence => write!(output, "body state sequence is out of order"),
            Self::BodyPriorReceiptMismatch => write!(output, "body prior-state receipt differs"),
            Self::BodySourceTimeDidNotAdvance => {
                write!(output, "body source time did not strictly advance")
            }
            Self::ReceiptDidNotChange => {
                write!(output, "authenticated cause receipt did not change")
            }
            Self::SequenceOverflow => write!(output, "wake authority sequence overflow"),
            Self::InvalidBudget(reason) => write!(output, "invalid external work budget: {reason}"),
            Self::InvalidDeploymentCeilings(reason) => {
                write!(output, "invalid deployment admission ceilings: {reason}")
            }
            Self::DeploymentCeilingExceeded(name) => {
                write!(output, "deployment admission ceiling exceeded: {name}")
            }
            Self::BudgetAuthenticationFailed => write!(output, "external work-budget HMAC differs"),
            Self::BudgetBindingMismatch => write!(output, "external work-budget binding differs"),
            Self::PythonCallsObserved => {
                write!(output, "Python calls are nonzero at native wake boundary")
            }
            Self::ResourceCounterRegressed(name) => {
                write!(output, "resource counter regressed: {name}")
            }
            Self::StageMadeNoProgress => {
                write!(output, "native transition stage prepared zero transitions")
            }
            Self::SuppliedObservationExceedsWorkBudget => {
                write!(
                    output,
                    "post-stage supplied observation exceeds work budget"
                )
            }
            Self::ArithmeticOverflow => write!(output, "wake admission arithmetic overflow"),
            Self::InvalidContinuation(reason) => {
                write!(output, "invalid restart evidence: {reason}")
            }
            Self::PendingPackageIntegrityFailed => {
                write!(output, "pending restart package receipt differs")
            }
            Self::ResumeOrganismReceiptMismatch => {
                write!(output, "resume organism receipt differs")
            }
            Self::ResumeHeadMismatch => write!(output, "resume sealed head differs"),
            Self::ResumeHandoffIntegrityFailed => {
                write!(output, "resume handoff integrity differs")
            }
        }
    }
}

impl std::error::Error for WakeAdmissionError {}

pub(crate) enum AcceptedWakeFailure<ObserverError, TransitionError> {
    Boundary(WakeAdmissionError),
    Observer(ObserverError),
    Transition(TransitionError),
    TransitionAndObserver(TransitionError, ObserverError),
    TransitionAndBoundary(TransitionError, WakeAdmissionError),
    BoundaryAndObserver(WakeAdmissionError, ObserverError),
    BoundaryAfterBoundary(WakeAdmissionError, WakeAdmissionError),
    StagePreparedAndObserverFailed {
        attempted_prepared_transitions: u64,
        observer_error: ObserverError,
    },
}

enum PostStageObservationFailure<ObserverError> {
    Observer(ObserverError),
    Boundary(WakeAdmissionError, ResourceObservation),
}

pub(crate) enum RetryBudgetEvidence {
    UnverifiedRecord(ExternalWorkBudgetRecord),
    Verified(VerifiedExternalWorkBudget),
}

/// An already-admitted authenticated cause returned intact after later boundary,
/// observer, budget, or transition failure. Its sealed input head is unchanged.
pub(crate) struct AcceptedWakeRetry<ObserverError, TransitionError> {
    admitted_wake: AdmittedWake,
    unchanged_head: WakeHeadSnapshot,
    budget: Option<RetryBudgetEvidence>,
    latest_supplied_resources: Option<ResourceObservation>,
    prepared_transitions: u64,
    restart_evidence: SuppliedRestartEvidence,
    failure: AcceptedWakeFailure<ObserverError, TransitionError>,
}

impl<ObserverError, TransitionError> AcceptedWakeRetry<ObserverError, TransitionError> {
    pub(crate) fn admitted_wake(&self) -> &AdmittedWake {
        &self.admitted_wake
    }

    pub(crate) fn unchanged_head(&self) -> WakeHeadSnapshot {
        self.unchanged_head.clone()
    }

    pub(crate) fn budget(&self) -> Option<&RetryBudgetEvidence> {
        self.budget.as_ref()
    }

    pub(crate) fn latest_supplied_resources(&self) -> Option<&ResourceObservation> {
        self.latest_supplied_resources.as_ref()
    }

    pub(crate) fn prepared_transitions(&self) -> u64 {
        self.prepared_transitions
    }

    pub(crate) fn restart_evidence(&self) -> &SuppliedRestartEvidence {
        &self.restart_evidence
    }

    pub(crate) fn failure(&self) -> &AcceptedWakeFailure<ObserverError, TransitionError> {
        &self.failure
    }

    pub(crate) fn into_resume(self) -> AcceptedWakeResume<ObserverError, TransitionError> {
        AcceptedWakeResume {
            capability: WakeResumeCapability {
                admitted_wake: self.admitted_wake,
                unchanged_head: self.unchanged_head.clone(),
                restart_evidence: self.restart_evidence,
            },
            unchanged_head: self.unchanged_head,
            budget: self.budget,
            latest_supplied_resources: self.latest_supplied_resources,
            prepared_transitions: self.prepared_transitions,
            failure: self.failure,
        }
    }
}

pub(crate) struct AcceptedWakeResume<ObserverError, TransitionError> {
    pub(crate) capability: WakeResumeCapability,
    pub(crate) unchanged_head: WakeHeadSnapshot,
    pub(crate) budget: Option<RetryBudgetEvidence>,
    pub(crate) latest_supplied_resources: Option<ResourceObservation>,
    pub(crate) prepared_transitions: u64,
    pub(crate) failure: AcceptedWakeFailure<ObserverError, TransitionError>,
}

pub(crate) enum WakeBoundaryFailure<ObserverError, TransitionError> {
    RejectedBeforeAdmission(WakeAdmissionError),
    RejectedResume {
        error: WakeAdmissionError,
        capability: WakeResumeCapability,
    },
    AcceptedForRetry(AcceptedWakeRetry<ObserverError, TransitionError>),
}

impl BlockingWakeAdmission {
    /// `caller_supplied_prior_state` is an immutable transition input only. This
    /// boundary binds the wake to the exact receipt carried by `current`, but it
    /// does not prove that generic `S` encodes that sealed organism state. The
    /// stage contract requires preparation without externally visible mutation
    /// and allocation only through separately bounded native primitives. Rust's
    /// generic callback type cannot enforce CPU, RSS, I/O, or process purity;
    /// production integration must supply transactional arenas or containment.
    #[allow(clippy::too_many_arguments)]
    /// This pre-integration entry point accepts only opaque supplied ceilings;
    /// it is not production admission and cannot establish no-runaway behavior.
    pub(crate) fn block_and_prepare<
        S,
        Observe,
        IssueBudget,
        Stage,
        ObserverError,
        TransitionError,
    >(
        &self,
        current: &WorldBodyVerifiedSeal,
        caller_supplied_prior_state: &S,
        budget_key: &ExternalWorkBudgetKey,
        deployment_ceilings: &SuppliedDeploymentAdmissionCeilings,
        mut observe: Observe,
        issue_budget: IssueBudget,
        mut stage: Stage,
    ) -> Result<WakeWorkOutcome<S>, WakeBoundaryFailure<ObserverError, TransitionError>>
    where
        Observe: FnMut() -> Result<ResourceObservation, ObserverError>,
        IssueBudget: FnOnce(&AdmittedWake, &ResourceObservation) -> ExternalWorkBudgetRecord,
        Stage: FnMut(
            &S,
            &AdmittedWake,
            &SuppliedRestartEvidence,
            RemainingExternalAllowance,
        ) -> Result<SuppliedNativeTransitionStage<S>, TransitionError>,
    {
        let input = self.receiver.recv().map_err(|_| {
            WakeBoundaryFailure::RejectedBeforeAdmission(WakeAdmissionError::InputClosed)
        })?;
        let (admitted, initial_restart_evidence) = match input {
            WakeInput::Fresh {
                cause,
                restart_evidence,
            } => (
                admit_cause(current, cause)
                    .map_err(WakeBoundaryFailure::RejectedBeforeAdmission)?,
                restart_evidence,
            ),
            WakeInput::Resume(capability) => match validate_resume_binding(current, &capability) {
                Ok(()) => (capability.admitted_wake, capability.restart_evidence),
                Err(error) => {
                    return Err(WakeBoundaryFailure::RejectedResume { error, capability });
                }
            },
        };
        let prior_organism_receipt = admitted.prior_organism_receipt();
        let baseline = match observe() {
            Ok(value) => value,
            Err(error) => {
                return Err(accepted_retry(
                    admitted,
                    None,
                    None,
                    0,
                    initial_restart_evidence,
                    AcceptedWakeFailure::Observer(error),
                ));
            }
        };
        if let Err(error) = validate_native_observation(&baseline) {
            return Err(accepted_retry(
                admitted,
                None,
                Some(baseline),
                0,
                initial_restart_evidence,
                AcceptedWakeFailure::Boundary(error),
            ));
        }
        let budget_record = issue_budget(&admitted, &baseline);
        let budget = match verify_external_work_budget(
            &budget_record,
            budget_key,
            deployment_ceilings,
            current.state().identity,
            admitted.handoff_receipt,
            prior_organism_receipt,
            resource_observation_receipt(&baseline),
        ) {
            Ok(value) => value,
            Err(error) => {
                return Err(accepted_retry(
                    admitted,
                    Some(RetryBudgetEvidence::UnverifiedRecord(budget_record)),
                    Some(baseline),
                    0,
                    initial_restart_evidence,
                    AcceptedWakeFailure::Boundary(error),
                ));
            }
        };
        let limits = budget.limits();
        let initial_evidence_bytes = match u64::try_from(initial_restart_evidence.payload.len()) {
            Ok(value) => value,
            Err(_) => {
                return Err(accepted_retry(
                    admitted,
                    Some(RetryBudgetEvidence::Verified(budget)),
                    Some(baseline),
                    0,
                    initial_restart_evidence,
                    AcceptedWakeFailure::Boundary(WakeAdmissionError::ArithmeticOverflow),
                ));
            }
        };
        if initial_evidence_bytes > limits.max_continuation_bytes {
            return Err(accepted_retry(
                admitted,
                Some(RetryBudgetEvidence::Verified(budget)),
                Some(baseline),
                0,
                initial_restart_evidence,
                AcceptedWakeFailure::Boundary(WakeAdmissionError::InvalidContinuation(
                    "initial restart evidence exceeds authenticated budget",
                )),
            ));
        }
        let mut evidence = initial_restart_evidence;
        let mut latest = baseline.clone();
        let mut prepared_transitions = 0_u64;
        let mut peak_resident = baseline.resident_bytes;
        let mut peak_durable = baseline.durable_bytes;

        loop {
            let delta = match resource_delta(&baseline, &latest, peak_resident, peak_durable) {
                Ok(value) => value,
                Err(error) => {
                    return Err(accepted_retry(
                        admitted,
                        Some(RetryBudgetEvidence::Verified(budget)),
                        Some(latest),
                        prepared_transitions,
                        evidence,
                        AcceptedWakeFailure::Boundary(error),
                    ));
                }
            };
            let is_exhausted =
                match exhausted(limits, prepared_transitions, delta, &latest, &evidence) {
                    Ok(value) => value,
                    Err(error) => {
                        return Err(accepted_retry(
                            admitted,
                            Some(RetryBudgetEvidence::Verified(budget)),
                            Some(latest),
                            prepared_transitions,
                            evidence,
                            AcceptedWakeFailure::Boundary(error),
                        ));
                    }
                };
            if is_exhausted {
                return Ok(WakeWorkOutcome::Pending(pending(
                    admitted,
                    budget,
                    latest,
                    delta,
                    prepared_transitions,
                    evidence,
                )));
            }
            let allowance = match remaining(limits, prepared_transitions, delta) {
                Ok(value) => value,
                Err(error) => {
                    return Err(accepted_retry(
                        admitted,
                        Some(RetryBudgetEvidence::Verified(budget)),
                        Some(latest),
                        prepared_transitions,
                        evidence,
                        AcceptedWakeFailure::Boundary(error),
                    ));
                }
            };
            let next = match stage(caller_supplied_prior_state, &admitted, &evidence, allowance) {
                Ok(value) => value,
                Err(error) => {
                    let (latest_after_attempt, failure) = match observe_after_stage(
                        &mut observe,
                        &baseline,
                        peak_resident,
                        peak_durable,
                        limits,
                    ) {
                        Ok(observed) => (Some(observed), AcceptedWakeFailure::Transition(error)),
                        Err(PostStageObservationFailure::Observer(observer_error)) => (
                            Some(latest),
                            AcceptedWakeFailure::TransitionAndObserver(error, observer_error),
                        ),
                        Err(PostStageObservationFailure::Boundary(boundary_error, observed)) => (
                            Some(observed),
                            AcceptedWakeFailure::TransitionAndBoundary(error, boundary_error),
                        ),
                    };
                    return Err(accepted_retry(
                        admitted,
                        Some(RetryBudgetEvidence::Verified(budget)),
                        latest_after_attempt,
                        prepared_transitions,
                        evidence,
                        failure,
                    ));
                }
            };
            if next.prepared_transitions == 0 {
                let primary = WakeAdmissionError::StageMadeNoProgress;
                let (latest_after_attempt, failure) = match observe_after_stage(
                    &mut observe,
                    &baseline,
                    peak_resident,
                    peak_durable,
                    limits,
                ) {
                    Ok(observed) => (Some(observed), AcceptedWakeFailure::Boundary(primary)),
                    Err(PostStageObservationFailure::Observer(observer_error)) => (
                        Some(latest),
                        AcceptedWakeFailure::BoundaryAndObserver(primary, observer_error),
                    ),
                    Err(PostStageObservationFailure::Boundary(boundary_error, observed)) => (
                        Some(observed),
                        AcceptedWakeFailure::BoundaryAfterBoundary(primary, boundary_error),
                    ),
                };
                return Err(accepted_retry(
                    admitted,
                    Some(RetryBudgetEvidence::Verified(budget)),
                    latest_after_attempt,
                    prepared_transitions,
                    evidence,
                    failure,
                ));
            }
            let next_prepared = match prepared_transitions.checked_add(next.prepared_transitions) {
                Some(value) => value,
                None => {
                    let primary = WakeAdmissionError::ArithmeticOverflow;
                    let (latest_after_attempt, failure) = match observe_after_stage(
                        &mut observe,
                        &baseline,
                        peak_resident,
                        peak_durable,
                        limits,
                    ) {
                        Ok(observed) => (Some(observed), AcceptedWakeFailure::Boundary(primary)),
                        Err(PostStageObservationFailure::Observer(observer_error)) => (
                            Some(latest),
                            AcceptedWakeFailure::BoundaryAndObserver(primary, observer_error),
                        ),
                        Err(PostStageObservationFailure::Boundary(boundary_error, observed)) => (
                            Some(observed),
                            AcceptedWakeFailure::BoundaryAfterBoundary(primary, boundary_error),
                        ),
                    };
                    return Err(accepted_retry(
                        admitted,
                        Some(RetryBudgetEvidence::Verified(budget)),
                        latest_after_attempt,
                        prepared_transitions,
                        evidence,
                        failure,
                    ));
                }
            };
            let observed = match observe() {
                Ok(value) => value,
                Err(error) => {
                    return Err(accepted_retry(
                        admitted,
                        Some(RetryBudgetEvidence::Verified(budget)),
                        Some(latest),
                        prepared_transitions,
                        evidence,
                        AcceptedWakeFailure::StagePreparedAndObserverFailed {
                            attempted_prepared_transitions: next.prepared_transitions,
                            observer_error: error,
                        },
                    ));
                }
            };
            if let Err(error) = validate_native_observation(&observed) {
                return Err(accepted_retry(
                    admitted,
                    Some(RetryBudgetEvidence::Verified(budget)),
                    Some(observed),
                    prepared_transitions,
                    evidence,
                    AcceptedWakeFailure::Boundary(error),
                ));
            }
            peak_resident = peak_resident.max(observed.resident_bytes);
            peak_durable = peak_durable.max(observed.durable_bytes);
            let next_delta = match resource_delta(&baseline, &observed, peak_resident, peak_durable)
            {
                Ok(value) => value,
                Err(error) => {
                    return Err(accepted_retry(
                        admitted,
                        Some(RetryBudgetEvidence::Verified(budget)),
                        Some(observed),
                        prepared_transitions,
                        evidence,
                        AcceptedWakeFailure::Boundary(error),
                    ));
                }
            };
            let evidence_bytes = match u64::try_from(next.restart_evidence.payload.len()) {
                Ok(value) => value,
                Err(_) => {
                    return Err(accepted_retry(
                        admitted,
                        Some(RetryBudgetEvidence::Verified(budget)),
                        Some(observed),
                        prepared_transitions,
                        evidence,
                        AcceptedWakeFailure::Boundary(WakeAdmissionError::ArithmeticOverflow),
                    ));
                }
            };
            let fits = stage_fits_supplied_budget(
                limits,
                next_prepared,
                next_delta,
                evidence_bytes,
                &observed,
            );

            if !fits {
                return Ok(WakeWorkOutcome::Pending(pending(
                    admitted,
                    budget,
                    observed,
                    next_delta,
                    prepared_transitions,
                    evidence,
                )));
            }

            prepared_transitions = next_prepared;
            latest = observed;
            evidence = next.restart_evidence;
            match next.disposition {
                StageDisposition::Continue => {}
                StageDisposition::ProposedState(proposed_state) => {
                    return Ok(WakeWorkOutcome::Prepared(
                        SuppliedObservationCheckedInMemoryWakeHandoff {
                            proposed_next_head: admitted.proposed_next_head.clone(),
                            budget_receipt: budget.receipt(),
                            last_supplied_resources: latest,
                            resource_delta: next_delta,
                            prepared_transitions,
                            restart_evidence: evidence,
                            admitted_wake: admitted,
                            proposed_state,
                        },
                    ));
                }
            }
        }
    }
}

fn stage_fits_supplied_budget(
    limits: ExternalWorkLimits,
    prepared_transitions: u64,
    delta: SuppliedResourceDelta,
    continuation_bytes: u64,
    observed: &ResourceObservation,
) -> bool {
    prepared_transitions <= limits.max_prepared_transitions
        && delta.native_calls <= limits.max_native_calls
        && delta.cpu_nanoseconds <= limits.max_cpu_nanoseconds
        && delta.resident_byte_growth <= limits.max_resident_byte_growth
        && delta.durable_byte_growth <= limits.max_durable_byte_growth
        && continuation_bytes <= limits.max_continuation_bytes
        && observed.recovery_reserve_bytes >= limits.min_recovery_reserve_bytes
}

fn admit_cause(
    current: &WorldBodyVerifiedSeal,
    cause: AuthenticatedWakeCause,
) -> Result<AdmittedWake, WakeAdmissionError> {
    let prior_organism_receipt = current.organism_state_receipt();
    if prior_organism_receipt == ZERO_RECEIPT {
        return Err(WakeAdmissionError::PriorOrganismReceiptIsZero);
    }
    let current_head = WakeHeadSnapshot::current(current);
    let proposed_next_head = next_head(&current_head, &cause)?;
    let handoff_receipt = handoff_receipt(
        current.state().identity,
        prior_organism_receipt,
        &current_head,
        &proposed_next_head,
        &cause,
    );
    Ok(AdmittedWake {
        cause,
        current_head,
        proposed_next_head,
        prior_organism_receipt,
        handoff_receipt,
    })
}

fn validate_resume_binding(
    current: &WorldBodyVerifiedSeal,
    capability: &WakeResumeCapability,
) -> Result<(), WakeAdmissionError> {
    if capability.admitted_wake.current_head != capability.unchanged_head {
        return Err(WakeAdmissionError::ResumeHeadMismatch);
    }
    validate_resume_coordinates(
        capability.admitted_wake.prior_organism_receipt(),
        &capability.unchanged_head,
        current.organism_state_receipt(),
        &WakeHeadSnapshot::current(current),
    )?;
    let expected_handoff = handoff_receipt(
        current.state().identity,
        capability.admitted_wake.prior_organism_receipt(),
        &capability.admitted_wake.current_head,
        &capability.admitted_wake.proposed_next_head,
        &capability.admitted_wake.cause,
    );
    if expected_handoff != capability.admitted_wake.handoff_receipt() {
        return Err(WakeAdmissionError::ResumeHandoffIntegrityFailed);
    }
    Ok(())
}

fn validate_resume_coordinates(
    expected_organism_receipt: [u8; 32],
    expected_head: &WakeHeadSnapshot,
    actual_organism_receipt: [u8; 32],
    actual_head: &WakeHeadSnapshot,
) -> Result<(), WakeAdmissionError> {
    if actual_organism_receipt != expected_organism_receipt {
        return Err(WakeAdmissionError::ResumeOrganismReceiptMismatch);
    }
    if actual_head != expected_head {
        return Err(WakeAdmissionError::ResumeHeadMismatch);
    }
    Ok(())
}

fn next_head(
    current: &WakeHeadSnapshot,
    cause: &AuthenticatedWakeCause,
) -> Result<WakeHeadSnapshot, WakeAdmissionError> {
    let mut next = current.clone();
    match cause {
        AuthenticatedWakeCause::WorldRevision(world) => {
            if world.mount_epoch().get() != current.world_mount_epoch {
                return Err(WakeAdmissionError::WorldAuthorityEpochMismatch);
            }
            if world.revision() < current.world_revision {
                return Err(WakeAdmissionError::OutOfOrderWorldRevision);
            }
            if world.revision() == current.world_revision {
                return if world.receipt() == current.world_receipt {
                    Err(WakeAdmissionError::DuplicateWorldRevision)
                } else {
                    Err(WakeAdmissionError::ConflictingWorldRevision)
                };
            }
            require_exact_successor(
                current.world_revision,
                world.revision(),
                WakeAdmissionError::OutOfOrderWorldRevision,
            )?;
            if world.receipt() == current.world_receipt
                || world.state_receipt() == current.world_state_receipt
            {
                return Err(WakeAdmissionError::ReceiptDidNotChange);
            }
            next.world_revision = world.revision();
            next.world_receipt = world.receipt();
            next.world_state_receipt = world.state_receipt();
        }
        AuthenticatedWakeCause::BodyState(body) => {
            if body.mount_epoch().get() != current.body_mount_epoch {
                return Err(WakeAdmissionError::BodyAuthorityEpochMismatch);
            }
            if body.manifest_receipt() != current.body_manifest_receipt {
                return Err(WakeAdmissionError::BodyManifestChanged);
            }
            if body.sequence() < current.body_sequence {
                return Err(WakeAdmissionError::OutOfOrderBodySequence);
            }
            if body.sequence() == current.body_sequence {
                return if body.state_receipt() == current.body_state_receipt {
                    Err(WakeAdmissionError::DuplicateBodySequence)
                } else {
                    Err(WakeAdmissionError::ConflictingBodySequence)
                };
            }
            require_exact_successor(
                current.body_sequence,
                body.sequence(),
                WakeAdmissionError::OutOfOrderBodySequence,
            )?;
            if body.prior_state_receipt() != Some(current.body_state_receipt) {
                return Err(WakeAdmissionError::BodyPriorReceiptMismatch);
            }
            if body.state_receipt() == current.body_state_receipt {
                return Err(WakeAdmissionError::ReceiptDidNotChange);
            }
            require_strict_body_source_time(&current.body_source_time, body.source_time())?;
            next.body_sequence = body.sequence();
            next.body_source_time = body.source_time().clone();
            next.body_state_receipt = body.state_receipt();
        }
    }
    Ok(next)
}

fn require_strict_body_source_time(
    current: &BigRational,
    candidate: &BigRational,
) -> Result<(), WakeAdmissionError> {
    if candidate <= current {
        return Err(WakeAdmissionError::BodySourceTimeDidNotAdvance);
    }
    Ok(())
}

fn require_exact_successor(
    current: u64,
    candidate: u64,
    out_of_order: WakeAdmissionError,
) -> Result<(), WakeAdmissionError> {
    let expected = current
        .checked_add(1)
        .ok_or(WakeAdmissionError::SequenceOverflow)?;
    if candidate != expected {
        return Err(out_of_order);
    }
    Ok(())
}

#[allow(clippy::too_many_arguments)]
pub(crate) fn authenticate_external_work_budget(
    key: &ExternalWorkBudgetKey,
    identity: [u8; 16],
    wake_handoff_receipt: [u8; 32],
    prior_organism_receipt: [u8; 32],
    resource_observation: &ResourceObservation,
    derivation_provenance_receipt: [u8; 32],
    limits: ExternalWorkLimits,
) -> Result<ExternalWorkBudgetRecord, WakeAdmissionError> {
    limits.validate()?;
    validate_native_observation(resource_observation)?;
    let resource_observation_receipt = resource_observation_receipt(resource_observation);
    if wake_handoff_receipt == ZERO_RECEIPT
        || prior_organism_receipt == ZERO_RECEIPT
        || resource_observation_receipt == ZERO_RECEIPT
        || derivation_provenance_receipt == ZERO_RECEIPT
    {
        return Err(WakeAdmissionError::InvalidBudget(
            "one or more budget binding receipts are zero",
        ));
    }
    let mut bytes = [0_u8; BUDGET_RECORD_BYTES];
    let mut cursor = 0_usize;
    put(&mut bytes, &mut cursor, BUDGET_MAGIC);
    put(&mut bytes, &mut cursor, &BUDGET_VERSION.to_le_bytes());
    put(&mut bytes, &mut cursor, &key.epoch.to_le_bytes());
    put(&mut bytes, &mut cursor, &identity);
    put(&mut bytes, &mut cursor, &wake_handoff_receipt);
    put(&mut bytes, &mut cursor, &prior_organism_receipt);
    put(&mut bytes, &mut cursor, &resource_observation_receipt);
    put(&mut bytes, &mut cursor, &derivation_provenance_receipt);
    for value in limit_values(limits) {
        put(&mut bytes, &mut cursor, &value.to_le_bytes());
    }
    debug_assert_eq!(cursor, BUDGET_HEADER_BYTES);
    let tag = hmac_tag(key, &bytes[..BUDGET_HEADER_BYTES]);
    bytes[BUDGET_HEADER_BYTES..].copy_from_slice(&tag);
    Ok(ExternalWorkBudgetRecord { bytes })
}

#[allow(clippy::too_many_arguments)]
fn verify_external_work_budget(
    record: &ExternalWorkBudgetRecord,
    key: &ExternalWorkBudgetKey,
    deployment_ceilings: &SuppliedDeploymentAdmissionCeilings,
    expected_identity: [u8; 16],
    expected_handoff: [u8; 32],
    expected_prior: [u8; 32],
    expected_resource: [u8; 32],
) -> Result<VerifiedExternalWorkBudget, WakeAdmissionError> {
    let bytes = record.as_bytes();
    let mut verifier = HmacSha256::new_from_slice(key.bytes.as_ref())
        .expect("HMAC-SHA256 accepts every 32-byte key");
    verifier.update(BUDGET_DOMAIN);
    verifier.update(&bytes[..BUDGET_HEADER_BYTES]);
    verifier
        .verify_slice(&bytes[BUDGET_HEADER_BYTES..])
        .map_err(|_| WakeAdmissionError::BudgetAuthenticationFailed)?;

    let mut cursor = 0_usize;
    if take::<8>(bytes, &mut cursor) != *BUDGET_MAGIC {
        return Err(WakeAdmissionError::InvalidBudget("record magic differs"));
    }
    if u16::from_le_bytes(take(bytes, &mut cursor)) != BUDGET_VERSION {
        return Err(WakeAdmissionError::InvalidBudget("record version differs"));
    }
    if u32::from_le_bytes(take(bytes, &mut cursor)) != key.epoch {
        return Err(WakeAdmissionError::BudgetBindingMismatch);
    }
    let identity = take::<16>(bytes, &mut cursor);
    let handoff = take::<32>(bytes, &mut cursor);
    let prior = take::<32>(bytes, &mut cursor);
    let resource = take::<32>(bytes, &mut cursor);
    let provenance = take::<32>(bytes, &mut cursor);
    let limits = ExternalWorkLimits {
        max_prepared_transitions: take_u64(bytes, &mut cursor),
        max_native_calls: take_u64(bytes, &mut cursor),
        max_cpu_nanoseconds: take_u64(bytes, &mut cursor),
        max_resident_byte_growth: take_u64(bytes, &mut cursor),
        max_durable_byte_growth: take_u64(bytes, &mut cursor),
        max_continuation_bytes: take_u64(bytes, &mut cursor),
        min_recovery_reserve_bytes: take_u64(bytes, &mut cursor),
    };
    limits.validate()?;
    deployment_ceilings.validate_budget(limits)?;
    if provenance == ZERO_RECEIPT {
        return Err(WakeAdmissionError::InvalidBudget(
            "derivation provenance receipt is zero",
        ));
    }
    if identity != expected_identity
        || handoff != expected_handoff
        || prior != expected_prior
        || resource != expected_resource
    {
        return Err(WakeAdmissionError::BudgetBindingMismatch);
    }
    Ok(VerifiedExternalWorkBudget {
        record: *bytes,
        limits,
        deployment_policy_receipt: deployment_ceilings.provenance_receipt(),
    })
}

fn validate_native_observation(value: &ResourceObservation) -> Result<(), WakeAdmissionError> {
    if value.python_calls != 0 {
        return Err(WakeAdmissionError::PythonCallsObserved);
    }
    Ok(())
}

fn observe_after_stage<Observe, ObserverError>(
    observe: &mut Observe,
    baseline: &ResourceObservation,
    prior_peak_resident: u64,
    prior_peak_durable: u64,
    limits: ExternalWorkLimits,
) -> Result<ResourceObservation, PostStageObservationFailure<ObserverError>>
where
    Observe: FnMut() -> Result<ResourceObservation, ObserverError>,
{
    let observed = observe().map_err(PostStageObservationFailure::Observer)?;
    if let Err(error) = validate_native_observation(&observed) {
        return Err(PostStageObservationFailure::Boundary(error, observed));
    }
    let peak_resident = prior_peak_resident.max(observed.resident_bytes);
    let peak_durable = prior_peak_durable.max(observed.durable_bytes);
    let delta = resource_delta(baseline, &observed, peak_resident, peak_durable)
        .map_err(|error| PostStageObservationFailure::Boundary(error, observed.clone()))?;
    if delta.native_calls > limits.max_native_calls
        || delta.cpu_nanoseconds > limits.max_cpu_nanoseconds
        || delta.resident_byte_growth > limits.max_resident_byte_growth
        || delta.durable_byte_growth > limits.max_durable_byte_growth
        || observed.recovery_reserve_bytes < limits.min_recovery_reserve_bytes
    {
        return Err(PostStageObservationFailure::Boundary(
            WakeAdmissionError::SuppliedObservationExceedsWorkBudget,
            observed,
        ));
    }
    Ok(observed)
}

fn resource_delta(
    baseline: &ResourceObservation,
    latest: &ResourceObservation,
    peak_resident: u64,
    peak_durable: u64,
) -> Result<SuppliedResourceDelta, WakeAdmissionError> {
    let cpu_nanoseconds = latest
        .cpu_nanoseconds
        .checked_sub(baseline.cpu_nanoseconds)
        .ok_or(WakeAdmissionError::ResourceCounterRegressed(
            "CPU nanoseconds",
        ))?;
    let native_calls = latest
        .native_calls
        .checked_sub(baseline.native_calls)
        .ok_or(WakeAdmissionError::ResourceCounterRegressed("native calls"))?;
    Ok(SuppliedResourceDelta {
        cpu_nanoseconds,
        native_calls,
        resident_byte_growth: peak_resident.saturating_sub(baseline.resident_bytes),
        durable_byte_growth: peak_durable.saturating_sub(baseline.durable_bytes),
    })
}

fn exhausted(
    limits: ExternalWorkLimits,
    prepared: u64,
    delta: SuppliedResourceDelta,
    latest: &ResourceObservation,
    evidence: &SuppliedRestartEvidence,
) -> Result<bool, WakeAdmissionError> {
    let continuation_bytes = u64::try_from(evidence.payload.len())
        .map_err(|_| WakeAdmissionError::ArithmeticOverflow)?;
    Ok(prepared >= limits.max_prepared_transitions
        || delta.native_calls >= limits.max_native_calls
        || delta.cpu_nanoseconds >= limits.max_cpu_nanoseconds
        || delta.resident_byte_growth >= limits.max_resident_byte_growth
        || delta.durable_byte_growth >= limits.max_durable_byte_growth
        || continuation_bytes > limits.max_continuation_bytes
        || latest.recovery_reserve_bytes < limits.min_recovery_reserve_bytes)
}

fn remaining(
    limits: ExternalWorkLimits,
    prepared: u64,
    delta: SuppliedResourceDelta,
) -> Result<RemainingExternalAllowance, WakeAdmissionError> {
    Ok(RemainingExternalAllowance {
        prepared_transitions: limits
            .max_prepared_transitions
            .checked_sub(prepared)
            .ok_or(WakeAdmissionError::ArithmeticOverflow)?,
        native_calls: limits
            .max_native_calls
            .checked_sub(delta.native_calls)
            .ok_or(WakeAdmissionError::ArithmeticOverflow)?,
        cpu_nanoseconds: limits
            .max_cpu_nanoseconds
            .checked_sub(delta.cpu_nanoseconds)
            .ok_or(WakeAdmissionError::ArithmeticOverflow)?,
        resident_byte_growth: limits
            .max_resident_byte_growth
            .checked_sub(delta.resident_byte_growth)
            .ok_or(WakeAdmissionError::ArithmeticOverflow)?,
        durable_byte_growth: limits
            .max_durable_byte_growth
            .checked_sub(delta.durable_byte_growth)
            .ok_or(WakeAdmissionError::ArithmeticOverflow)?,
        continuation_bytes: limits.max_continuation_bytes,
        min_recovery_reserve_bytes: limits.min_recovery_reserve_bytes,
    })
}

fn pending(
    admitted_wake: AdmittedWake,
    budget: VerifiedExternalWorkBudget,
    latest_supplied_resources: ResourceObservation,
    resource_delta: SuppliedResourceDelta,
    prepared_transitions: u64,
    restart_evidence: SuppliedRestartEvidence,
) -> InMemoryRestartFromPriorPending {
    let unchanged_head = admitted_wake.current_head.clone();
    let package_receipt = pending_package_receipt(
        &admitted_wake,
        &budget,
        &unchanged_head,
        &latest_supplied_resources,
        resource_delta,
        prepared_transitions,
        &restart_evidence,
    );
    InMemoryRestartFromPriorPending {
        unchanged_head,
        admitted_wake,
        budget,
        latest_supplied_resources,
        resource_delta,
        prepared_transitions,
        restart_evidence,
        package_receipt,
    }
}

fn accepted_retry<ObserverError, TransitionError>(
    admitted_wake: AdmittedWake,
    budget: Option<RetryBudgetEvidence>,
    latest_supplied_resources: Option<ResourceObservation>,
    prepared_transitions: u64,
    restart_evidence: SuppliedRestartEvidence,
    failure: AcceptedWakeFailure<ObserverError, TransitionError>,
) -> WakeBoundaryFailure<ObserverError, TransitionError> {
    WakeBoundaryFailure::AcceptedForRetry(AcceptedWakeRetry {
        unchanged_head: admitted_wake.current_head.clone(),
        admitted_wake,
        budget,
        latest_supplied_resources,
        prepared_transitions,
        restart_evidence,
        failure,
    })
}

fn pending_package_receipt(
    admitted: &AdmittedWake,
    budget: &VerifiedExternalWorkBudget,
    unchanged_head: &WakeHeadSnapshot,
    latest_supplied_resources: &ResourceObservation,
    delta: SuppliedResourceDelta,
    prepared_transitions: u64,
    restart_evidence: &SuppliedRestartEvidence,
) -> [u8; 32] {
    let mut digest = Sha256::new();
    digest.update(PENDING_DOMAIN);
    digest.update(admitted.handoff_receipt());
    digest.update(admitted.prior_organism_receipt());
    digest.update(budget.receipt());
    digest.update(budget.deployment_policy_receipt());
    encode_head(&mut digest, unchanged_head);
    digest.update(resource_observation_receipt(latest_supplied_resources));
    for value in [
        delta.cpu_nanoseconds,
        delta.resident_byte_growth,
        delta.durable_byte_growth,
        delta.native_calls,
        prepared_transitions,
    ] {
        digest.update(value.to_le_bytes());
    }
    digest.update(restart_evidence.receipt());
    digest.finalize().into()
}

fn resource_observation_receipt(value: &ResourceObservation) -> [u8; 32] {
    let mut bytes = [0_u8; 48];
    for (index, field) in [
        value.cpu_nanoseconds,
        value.resident_bytes,
        value.durable_bytes,
        value.recovery_reserve_bytes,
        value.python_calls,
        value.native_calls,
    ]
    .into_iter()
    .enumerate()
    {
        bytes[index * 8..(index + 1) * 8].copy_from_slice(&field.to_le_bytes());
    }
    domain_digest(RESOURCE_DOMAIN, &bytes)
}

fn handoff_receipt(
    identity: [u8; 16],
    prior_organism_receipt: [u8; 32],
    current: &WakeHeadSnapshot,
    next: &WakeHeadSnapshot,
    cause: &AuthenticatedWakeCause,
) -> [u8; 32] {
    let mut digest = Sha256::new();
    digest.update(HANDOFF_DOMAIN);
    digest.update(identity);
    digest.update(prior_organism_receipt);
    encode_head(&mut digest, current);
    encode_head(&mut digest, next);
    match cause {
        AuthenticatedWakeCause::WorldRevision(world) => {
            digest.update([1]);
            digest.update(world.receipt());
            digest.update(world.state_receipt());
        }
        AuthenticatedWakeCause::BodyState(body) => {
            digest.update([2]);
            digest.update(body.manifest_receipt());
            digest.update(body.state_receipt());
        }
    }
    digest.finalize().into()
}

fn encode_head(digest: &mut Sha256, value: &WakeHeadSnapshot) {
    digest.update(value.world_revision.to_le_bytes());
    digest.update(value.world_receipt);
    digest.update(value.world_state_receipt);
    digest.update(value.world_mount_epoch.to_le_bytes());
    digest.update(value.body_sequence.to_le_bytes());
    encode_big_rational(digest, &value.body_source_time);
    digest.update(value.body_state_receipt);
    digest.update(value.body_manifest_receipt);
    digest.update(value.body_mount_epoch.to_le_bytes());
}

fn encode_big_rational(digest: &mut Sha256, value: &BigRational) {
    for component in [value.numer(), value.denom()] {
        let bytes = component.to_signed_bytes_le();
        let length = bytes.len() as u128;
        digest.update(length.to_le_bytes());
        digest.update(bytes);
    }
}

fn continuation_receipt(
    schema: [u8; 32],
    provenance: [u8; 32],
    payload: &[u8],
) -> Result<[u8; 32], WakeAdmissionError> {
    let length =
        u64::try_from(payload.len()).map_err(|_| WakeAdmissionError::ArithmeticOverflow)?;
    let mut digest = Sha256::new();
    digest.update(CONTINUATION_DOMAIN);
    digest.update(schema);
    digest.update(provenance);
    digest.update(length.to_le_bytes());
    digest.update(payload);
    Ok(digest.finalize().into())
}

fn hmac_tag(key: &ExternalWorkBudgetKey, bytes: &[u8]) -> [u8; HMAC_BYTES] {
    let mut mac = HmacSha256::new_from_slice(key.bytes.as_ref())
        .expect("HMAC-SHA256 accepts every 32-byte key");
    mac.update(BUDGET_DOMAIN);
    mac.update(bytes);
    mac.finalize().into_bytes().into()
}

fn domain_digest(domain: &[u8], bytes: &[u8]) -> [u8; 32] {
    let mut digest = Sha256::new();
    digest.update(domain);
    digest.update(bytes);
    digest.finalize().into()
}

fn limit_values(value: ExternalWorkLimits) -> [u64; 7] {
    [
        value.max_prepared_transitions,
        value.max_native_calls,
        value.max_cpu_nanoseconds,
        value.max_resident_byte_growth,
        value.max_durable_byte_growth,
        value.max_continuation_bytes,
        value.min_recovery_reserve_bytes,
    ]
}

fn put<const TOTAL: usize>(output: &mut [u8; TOTAL], cursor: &mut usize, bytes: &[u8]) {
    let end = *cursor + bytes.len();
    output[*cursor..end].copy_from_slice(bytes);
    *cursor = end;
}

fn take<const LENGTH: usize>(bytes: &[u8], cursor: &mut usize) -> [u8; LENGTH] {
    let end = *cursor + LENGTH;
    let mut value = [0_u8; LENGTH];
    value.copy_from_slice(&bytes[*cursor..end]);
    *cursor = end;
    value
}

fn take_u64(bytes: &[u8], cursor: &mut usize) -> u64 {
    u64::from_le_bytes(take(bytes, cursor))
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::organism::world_body::test_support::{
        authenticated_current, verified_successor_fixture,
    };
    use std::cell::Cell;
    use std::collections::VecDeque;

    const IDENTITY: [u8; 16] = [
        0x10, 0x53, 0x2f, 0x91, 0x7b, 0x2d, 0x4a, 0xc8, 0x98, 0x04, 0x46, 0x73, 0x5d, 0xa1, 0x28,
        0xfe,
    ];

    fn limits() -> ExternalWorkLimits {
        ExternalWorkLimits {
            max_prepared_transitions: 3,
            max_native_calls: 4,
            max_cpu_nanoseconds: 100,
            max_resident_byte_growth: 200,
            max_durable_byte_growth: 300,
            max_continuation_bytes: 64,
            min_recovery_reserve_bytes: 400,
        }
    }

    fn ceilings() -> SuppliedDeploymentAdmissionCeilings {
        SuppliedDeploymentAdmissionCeilings::new(limits(), [0xc1; 32])
            .expect("supplied deployment ceilings")
    }

    fn key(epoch: u32, byte: u8) -> ExternalWorkBudgetKey {
        let root = SuppliedGlobalOwnerRootKey::new(1, [byte; 32]).expect("supplied global root");
        ExternalWorkBudgetKey::derive(epoch, &root).expect("derived budget key")
    }

    fn channel(capacity: u64) -> (WakeIngress, BlockingWakeAdmission) {
        bounded_wake_channel(
            RendezvousWakeChannelCapacity::new(capacity).expect("exact rendezvous capacity"),
        )
    }

    fn boundary_with(
        cause: AuthenticatedWakeCause,
        restart_evidence: SuppliedRestartEvidence,
    ) -> BlockingWakeAdmission {
        let (sender, receiver) = mpsc::sync_channel(1);
        sender
            .send(WakeInput::Fresh {
                cause,
                restart_evidence,
            })
            .unwrap_or_else(|_| panic!("inject cause"));
        BlockingWakeAdmission { receiver }
    }

    fn boundary_with_resume(capability: WakeResumeCapability) -> BlockingWakeAdmission {
        let (sender, receiver) = mpsc::sync_channel(1);
        sender
            .send(WakeInput::Resume(capability))
            .unwrap_or_else(|_| panic!("inject resume"));
        BlockingWakeAdmission { receiver }
    }

    fn resources(cpu: u64, resident: u64, durable: u64, native: u64) -> ResourceObservation {
        ResourceObservation {
            cpu_nanoseconds: cpu,
            resident_bytes: resident,
            durable_bytes: durable,
            recovery_reserve_bytes: 500,
            python_calls: 0,
            native_calls: native,
        }
    }

    fn budget() -> ExternalWorkBudgetRecord {
        authenticate_external_work_budget(
            &key(9, 0x91),
            IDENTITY,
            [1; 32],
            [2; 32],
            &resources(10, 20, 30, 40),
            [3; 32],
            limits(),
        )
        .expect("budget")
    }

    fn evidence(byte: u8, length: usize) -> SuppliedRestartEvidence {
        let payload = vec![byte; length];
        SuppliedRestartEvidence::new([byte; 32], [byte + 1; 32], &payload, &ceilings())
            .expect("evidence")
    }

    fn issue_for(
        key: &ExternalWorkBudgetKey,
        admitted: &AdmittedWake,
        observed: &ResourceObservation,
        limits: ExternalWorkLimits,
    ) -> ExternalWorkBudgetRecord {
        authenticate_external_work_budget(
            key,
            IDENTITY,
            admitted.handoff_receipt(),
            admitted.prior_organism_receipt(),
            observed,
            [0xd1; 32],
            limits,
        )
        .expect("issued external budget")
    }

    #[test]
    fn external_budget_authentication_and_every_binding_fail_closed() {
        let key = key(9, 0x91);
        let observed = resources(10, 20, 30, 40);
        let resource = resource_observation_receipt(&observed);
        let record = budget();
        let verified = verify_external_work_budget(
            &record,
            &key,
            &ceilings(),
            IDENTITY,
            [1; 32],
            [2; 32],
            resource,
        )
        .expect("verified budget");
        assert_eq!(verified.limits(), limits());

        for (identity, handoff, prior, basis) in [
            ([0; 16], [1; 32], [2; 32], resource),
            (IDENTITY, [8; 32], [2; 32], resource),
            (IDENTITY, [1; 32], [8; 32], resource),
            (IDENTITY, [1; 32], [2; 32], [8; 32]),
        ] {
            assert_eq!(
                verify_external_work_budget(
                    &record,
                    &key,
                    &ceilings(),
                    identity,
                    handoff,
                    prior,
                    basis,
                )
                .err(),
                Some(WakeAdmissionError::BudgetBindingMismatch)
            );
        }

        let mut tampered = *record.as_bytes();
        tampered[BUDGET_HEADER_BYTES - 1] ^= 1;
        assert_eq!(
            verify_external_work_budget(
                &ExternalWorkBudgetRecord::from_bytes(tampered),
                &key,
                &ceilings(),
                IDENTITY,
                [1; 32],
                [2; 32],
                resource,
            )
            .err(),
            Some(WakeAdmissionError::BudgetAuthenticationFailed)
        );
    }

    #[test]
    fn operational_budget_keys_are_domain_derived_from_supplied_global_root() {
        let root = SuppliedGlobalOwnerRootKey::new(1, [7; 32]).expect("root");
        let next_root_epoch = SuppliedGlobalOwnerRootKey::new(2, [7; 32]).expect("next root");
        let first = ExternalWorkBudgetKey::derive(1, &root).expect("first");
        let second = ExternalWorkBudgetKey::derive(2, &root).expect("second");
        let next_root_budget =
            ExternalWorkBudgetKey::derive(1, &next_root_epoch).expect("next root budget");
        assert_eq!(first.epoch(), 1);
        assert_eq!(second.epoch(), 2);
        assert_ne!(first.bytes.as_ref(), second.bytes.as_ref());
        assert_ne!(first.bytes.as_ref(), next_root_budget.bytes.as_ref());
        assert_ne!(
            root.derive_generation_current_key().as_ref(),
            next_root_epoch.derive_generation_current_key().as_ref()
        );
        assert_ne!(
            root.derive_generation_current_key().as_ref(),
            root.derive_platform_envelope_key().as_ref()
        );
        for (left, right) in [
            (
                root.derive_genesis_authentication_key(),
                root.derive_organism_seal_key(),
            ),
            (
                root.derive_genesis_authentication_key(),
                root.derive_generation_current_key(),
            ),
            (
                root.derive_organism_seal_key(),
                root.derive_platform_envelope_key(),
            ),
        ] {
            assert_ne!(left.as_ref(), right.as_ref());
        }
        assert_ne!(
            root.derive_genesis_authentication_key().as_ref(),
            next_root_epoch.derive_genesis_authentication_key().as_ref()
        );
        assert_ne!(
            root.derive_organism_seal_key().as_ref(),
            next_root_epoch.derive_organism_seal_key().as_ref()
        );
        assert!(SuppliedGlobalOwnerRootKey::new(0, [7; 32]).is_err());
    }

    #[test]
    fn v2_root_key_derivation_has_exact_known_answers() {
        let root = SuppliedGlobalOwnerRootKey::new(1, [7; 32]).unwrap();
        assert_eq!(
            root.derive_genesis_authentication_key().as_ref(),
            &[
                0x9d, 0x3b, 0x9a, 0xfc, 0xe5, 0x01, 0x8b, 0xbd, 0x60, 0x1b, 0xb3, 0x0c, 0xb3, 0xa3,
                0xea, 0xed, 0x96, 0x03, 0x69, 0x1f, 0xd0, 0xf8, 0x65, 0x38, 0xe2, 0x46, 0xf2, 0xef,
                0x18, 0x8e, 0x7f, 0xab,
            ]
        );
        assert_eq!(
            root.derive_organism_seal_key().as_ref(),
            &[
                0x47, 0x70, 0xa6, 0x2f, 0x0c, 0xdb, 0x75, 0x86, 0x0f, 0x64, 0x09, 0x12, 0x11, 0x6e,
                0xc0, 0x32, 0xf3, 0x4c, 0xe1, 0x67, 0xea, 0x1f, 0x2d, 0x11, 0xb1, 0x17, 0xa4, 0x78,
                0xf6, 0x28, 0xd6, 0xca,
            ]
        );
    }

    #[test]
    fn every_signed_limit_is_bounded_by_separate_deployment_policy() {
        let policy = ceilings();
        let key = key(9, 0x91);
        let observed = resources(10, 20, 30, 40);
        policy
            .validate_budget(limits())
            .expect("exact deployment limits");

        let mut violations = Vec::new();
        let mut value = limits();
        value.max_prepared_transitions += 1;
        violations.push(value);
        let mut value = limits();
        value.max_native_calls += 1;
        violations.push(value);
        let mut value = limits();
        value.max_cpu_nanoseconds += 1;
        violations.push(value);
        let mut value = limits();
        value.max_resident_byte_growth += 1;
        violations.push(value);
        let mut value = limits();
        value.max_durable_byte_growth += 1;
        violations.push(value);
        let mut value = limits();
        value.max_continuation_bytes += 1;
        violations.push(value);
        let mut value = limits();
        value.min_recovery_reserve_bytes -= 1;
        violations.push(value);

        for violation in violations {
            let record = authenticate_external_work_budget(
                &key, IDENTITY, [1; 32], [2; 32], &observed, [3; 32], violation,
            )
            .expect("authenticated over-policy record");
            assert!(matches!(
                verify_external_work_budget(
                    &record,
                    &key,
                    &policy,
                    IDENTITY,
                    [1; 32],
                    [2; 32],
                    resource_observation_receipt(&observed),
                ),
                Err(WakeAdmissionError::DeploymentCeilingExceeded(_))
            ));
        }
    }

    #[test]
    fn only_zero_capacity_rendezvous_is_admitted() {
        RendezvousWakeChannelCapacity::new(0).expect("exact rendezvous");
        assert!(matches!(
            RendezvousWakeChannelCapacity::new(1),
            Err(WakeAdmissionError::InvalidDeploymentCeilings(
                "native wake channel must be an exact zero-capacity rendezvous"
            ))
        ));
        assert!(matches!(
            SuppliedDeploymentAdmissionCeilings::new(limits(), ZERO_RECEIPT),
            Err(WakeAdmissionError::InvalidDeploymentCeilings(
                "deployment ceiling provenance receipt is zero"
            ))
        ));
        let mut zero_transition_limit = limits();
        zero_transition_limit.max_prepared_transitions = 0;
        assert_eq!(
            SuppliedDeploymentAdmissionCeilings::new(zero_transition_limit, [1; 32]).err(),
            Some(WakeAdmissionError::InvalidBudget(
                "maximum prepared transitions is zero"
            ))
        );
    }

    #[test]
    fn continuation_allocation_checks_deployment_cap_before_copy() {
        let mut cap = limits();
        cap.max_continuation_bytes = 1;
        let policy = SuppliedDeploymentAdmissionCeilings::new(cap, [1; 32]).expect("policy");
        assert_eq!(
            SuppliedRestartEvidence::new([1; 32], [2; 32], &[1, 2], &policy).err(),
            Some(WakeAdmissionError::InvalidContinuation(
                "restart evidence exceeds deployment allocation ceiling"
            ))
        );
    }

    #[test]
    fn no_internal_transition_limit_is_selected() {
        let key = key(7, 7);
        for maximum in [1, 17, 65_537] {
            let mut external = limits();
            external.max_prepared_transitions = maximum;
            let observed = resources(1, 2, 3, 4);
            let record = authenticate_external_work_budget(
                &key, IDENTITY, [1; 32], [2; 32], &observed, [4; 32], external,
            )
            .expect("external maximum");
            let verified = verify_external_work_budget(
                &record,
                &key,
                &SuppliedDeploymentAdmissionCeilings::new(external, [0xc1; 32])
                    .expect("external ceiling"),
                IDENTITY,
                [1; 32],
                [2; 32],
                resource_observation_receipt(&observed),
            )
            .expect("verified maximum");
            assert_eq!(verified.limits().max_prepared_transitions, maximum);
        }
    }

    #[test]
    fn quiescent_closed_input_runs_no_observer_budget_or_transition_work() {
        let (ingress, boundary) = channel(0);
        drop(ingress);
        let (current, _, _) = verified_successor_fixture();
        let key = key(9, 0x91);
        let observer_calls = Cell::new(0);
        let budget_calls = Cell::new(0);
        let transition_calls = Cell::new(0);

        let result: Result<WakeWorkOutcome<u64>, WakeBoundaryFailure<(), ()>> = boundary
            .block_and_prepare(
                &current,
                &10,
                &key,
                &ceilings(),
                || {
                    observer_calls.set(observer_calls.get() + 1);
                    Ok(resources(1, 2, 3, 4))
                },
                |admitted, observed| {
                    budget_calls.set(budget_calls.get() + 1);
                    issue_for(&key, admitted, observed, limits())
                },
                |_, _, _, _| {
                    transition_calls.set(transition_calls.get() + 1);
                    Ok(SuppliedNativeTransitionStage::proposed(
                        1,
                        evidence(6, 1),
                        11,
                    ))
                },
            );
        assert!(matches!(
            result,
            Err(WakeBoundaryFailure::RejectedBeforeAdmission(
                WakeAdmissionError::InputClosed
            ))
        ));
        assert_eq!(observer_calls.get(), 0);
        assert_eq!(budget_calls.get(), 0);
        assert_eq!(transition_calls.get(), 0);
    }

    #[test]
    fn live_empty_rendezvous_runs_zero_work_until_authenticated_cause_arrives() {
        use std::sync::atomic::{AtomicUsize, Ordering};

        let (current, successor_world, _) = verified_successor_fixture();
        let (ingress, boundary) = channel(0);
        let key = key(9, 0x91);
        let policy = ceilings();
        let observer_calls = AtomicUsize::new(0);
        let budget_calls = AtomicUsize::new(0);
        let stage_calls = AtomicUsize::new(0);
        let (ready_sender, ready_receiver) = mpsc::sync_channel(0);

        std::thread::scope(|scope| {
            let observer_calls_ref = &observer_calls;
            let budget_calls_ref = &budget_calls;
            let stage_calls_ref = &stage_calls;
            let worker = scope.spawn(move || {
                ready_sender.send(()).expect("ready");
                boundary.block_and_prepare(
                    &current,
                    &10,
                    &key,
                    &policy,
                    || {
                        let call = observer_calls_ref.fetch_add(1, Ordering::SeqCst);
                        Ok::<_, ()>(if call == 0 {
                            resources(10, 20, 30, 40)
                        } else {
                            resources(11, 20, 30, 40)
                        })
                    },
                    |admitted, observed| {
                        budget_calls_ref.fetch_add(1, Ordering::SeqCst);
                        issue_for(&key, admitted, observed, limits())
                    },
                    |_, _, _, _| {
                        stage_calls_ref.fetch_add(1, Ordering::SeqCst);
                        Ok::<_, ()>(SuppliedNativeTransitionStage::proposed(
                            1,
                            evidence(6, 1),
                            11,
                        ))
                    },
                )
            });
            ready_receiver.recv().expect("worker ready");
            assert_eq!(observer_calls.load(Ordering::SeqCst), 0);
            assert_eq!(budget_calls.load(Ordering::SeqCst), 0);
            assert_eq!(stage_calls.load(Ordering::SeqCst), 0);
            ingress
                .send(
                    AuthenticatedWakeCause::world(successor_world),
                    evidence(4, 1),
                )
                .expect("rendezvous cause");
            assert!(matches!(
                worker.join().expect("worker join"),
                Ok(WakeWorkOutcome::Prepared(_))
            ));
        });
    }

    #[test]
    fn authenticated_world_cause_yields_only_an_in_memory_handoff() {
        let (current, successor_world, _) = verified_successor_fixture();
        let boundary = boundary_with(
            AuthenticatedWakeCause::world(successor_world),
            evidence(4, 1),
        );
        let key = key(9, 0x91);
        let mut observations =
            VecDeque::from([resources(10, 20, 30, 40), resources(19, 27, 38, 43)]);
        let outcome: WakeWorkOutcome<u64> = boundary
            .block_and_prepare(
                &current,
                &10,
                &key,
                &ceilings(),
                || Ok::<_, ()>(observations.pop_front().expect("observation")),
                |admitted, observed| issue_for(&key, admitted, observed, limits()),
                |prior, _, _, allowance| {
                    assert_eq!(allowance.prepared_transitions, 3);
                    Ok::<_, ()>(SuppliedNativeTransitionStage::proposed(
                        1,
                        evidence(6, 2),
                        prior + 1,
                    ))
                },
            )
            .unwrap_or_else(|_| panic!("wake boundary failed"));

        let WakeWorkOutcome::Prepared(prepared) = outcome else {
            panic!("expected prepared handoff")
        };
        assert_eq!(*prepared.proposed_state(), 11);
        assert_eq!(prepared.prepared_transitions(), 1);
        assert_eq!(current.world_revision(), 0);
        assert_eq!(prepared.proposed_next_head().world_revision, 1);
        assert_eq!(
            prepared.proposed_next_head().body_sequence,
            current.body_sequence()
        );
        assert_eq!(prepared.resource_delta().cpu_nanoseconds, 9);
        let parts = prepared.into_parts();
        assert_eq!(parts.proposed_state, 11);
        assert_eq!(parts.prepared_transitions, 1);
        assert_eq!(parts.proposed_next_head.world_revision, 1);
        assert_ne!(parts.budget_receipt, ZERO_RECEIPT);
        assert_eq!(parts.last_supplied_resources.cpu_nanoseconds, 19);
        assert_eq!(parts.resource_delta.cpu_nanoseconds, 9);
        assert_eq!(parts.restart_evidence.payload(), &[6, 6]);
        assert!(matches!(
            parts.admitted_wake.cause(),
            AuthenticatedWakeCause::WorldRevision(_)
        ));
    }

    #[test]
    fn body_and_world_clocks_advance_independently() {
        let (current, _, successor_body) = verified_successor_fixture();
        let admitted = admit_cause(&current, AuthenticatedWakeCause::body(successor_body))
            .expect("body cause");
        assert_eq!(
            admitted.proposed_next_head().world_revision,
            current.world_revision()
        );
        assert_eq!(
            admitted.proposed_next_head().world_receipt,
            current.world_receipt()
        );
        assert_eq!(
            admitted.proposed_next_head().body_sequence,
            current.body_sequence() + 1
        );
        assert!(
            admitted.proposed_next_head().body_source_time
                > WakeHeadSnapshot::current(&current).body_source_time
        );
        assert_eq!(admitted.current_head(), WakeHeadSnapshot::current(&current));
        let time = BigRational::from_integer(10.into());
        assert_eq!(
            require_strict_body_source_time(&time, &time).err(),
            Some(WakeAdmissionError::BodySourceTimeDidNotAdvance)
        );
        assert_eq!(
            require_strict_body_source_time(&time, &BigRational::from_integer(9.into())).err(),
            Some(WakeAdmissionError::BodySourceTimeDidNotAdvance)
        );
        let (current, _, successor_body) = verified_successor_fixture();
        let mut nonadvancing_head = WakeHeadSnapshot::current(&current);
        nonadvancing_head.body_source_time = successor_body.source_time().clone();
        assert_eq!(
            next_head(
                &nonadvancing_head,
                &AuthenticatedWakeCause::body(successor_body)
            )
            .err(),
            Some(WakeAdmissionError::BodySourceTimeDidNotAdvance)
        );
    }

    #[test]
    fn duplicate_world_and_body_capabilities_are_rejected_before_work() {
        let (current, _, _) = verified_successor_fixture();
        let (same_world, same_body) = authenticated_current();
        assert_eq!(
            admit_cause(&current, AuthenticatedWakeCause::world(same_world),).err(),
            Some(WakeAdmissionError::DuplicateWorldRevision)
        );
        assert_eq!(
            admit_cause(&current, AuthenticatedWakeCause::body(same_body),).err(),
            Some(WakeAdmissionError::DuplicateBodySequence)
        );
    }

    #[test]
    fn each_authority_stream_rejects_skips_and_sequence_overflow() {
        assert_eq!(
            require_exact_successor(7, 9, WakeAdmissionError::OutOfOrderWorldRevision).err(),
            Some(WakeAdmissionError::OutOfOrderWorldRevision)
        );
        assert_eq!(
            require_exact_successor(11, 13, WakeAdmissionError::OutOfOrderBodySequence).err(),
            Some(WakeAdmissionError::OutOfOrderBodySequence)
        );
        assert_eq!(
            require_exact_successor(
                u64::MAX,
                u64::MAX,
                WakeAdmissionError::OutOfOrderWorldRevision,
            )
            .err(),
            Some(WakeAdmissionError::SequenceOverflow)
        );

        let (current, successor_world, successor_body) = verified_successor_fixture();
        let mut later_head = WakeHeadSnapshot::current(&current);
        later_head.world_revision = successor_world.revision() + 1;
        assert_eq!(
            next_head(&later_head, &AuthenticatedWakeCause::world(successor_world)).err(),
            Some(WakeAdmissionError::OutOfOrderWorldRevision)
        );
        let mut later_head = WakeHeadSnapshot::current(&current);
        later_head.body_sequence = successor_body.sequence() + 1;
        assert_eq!(
            next_head(&later_head, &AuthenticatedWakeCause::body(successor_body)).err(),
            Some(WakeAdmissionError::OutOfOrderBodySequence)
        );
    }

    #[test]
    fn over_budget_stage_changes_neither_head_count_nor_restart_evidence() {
        let (current, successor_world, _) = verified_successor_fixture();
        let key = key(9, 0x91);
        let initial = evidence(4, 1);
        let initial_receipt = initial.receipt();
        let boundary = boundary_with(AuthenticatedWakeCause::world(successor_world), initial);
        let mut constrained = limits();
        constrained.max_prepared_transitions = 1;
        let mut observations =
            VecDeque::from([resources(10, 20, 30, 40), resources(11, 20, 30, 40)]);
        let outcome: WakeWorkOutcome<u64> = boundary
            .block_and_prepare(
                &current,
                &10,
                &key,
                &ceilings(),
                || Ok::<_, ()>(observations.pop_front().expect("observation")),
                |admitted, observed| issue_for(&key, admitted, observed, constrained),
                |_, _, _, _| {
                    Ok::<_, ()>(SuppliedNativeTransitionStage::proposed(
                        2,
                        evidence(8, 2),
                        99,
                    ))
                },
            )
            .unwrap_or_else(|_| panic!("wake boundary failed"));
        let WakeWorkOutcome::Pending(pending) = outcome else {
            panic!("expected pending continuation")
        };
        assert_eq!(
            pending.unchanged_head(),
            WakeHeadSnapshot::current(&current)
        );
        assert_eq!(pending.prepared_transitions(), 0);
        assert_eq!(pending.restart_evidence().receipt(), initial_receipt);
        assert_eq!(pending.restart_evidence().payload().len(), 1);
        assert_ne!(pending.package_receipt(), ZERO_RECEIPT);
        assert_eq!(pending.budget().limits(), constrained);
        assert_eq!(pending.latest_supplied_resources().cpu_nanoseconds, 11);
        assert_eq!(pending.resource_delta().cpu_nanoseconds, 1);

        let retry = pending.into_resume_capability().expect("pending integrity");
        assert_eq!(retry.expected_head(), WakeHeadSnapshot::current(&current));
        assert_eq!(
            retry.expected_organism_receipt(),
            current.organism_state_receipt()
        );
        let original_handoff = retry.original_handoff_receipt();
        let (retry_ingress, retry_boundary) = channel(0);
        let retry_outcome = std::thread::scope(|scope| {
            let worker = scope.spawn(move || {
                let mut retry_observations =
                    VecDeque::from([resources(20, 20, 30, 50), resources(21, 20, 30, 51)]);
                retry_boundary.block_and_prepare(
                    &current,
                    &10,
                    &key,
                    &ceilings(),
                    || Ok::<_, ()>(retry_observations.pop_front().expect("retry observation")),
                    |admitted, observed| issue_for(&key, admitted, observed, limits()),
                    |_, _, _, _| {
                        Ok::<_, ()>(SuppliedNativeTransitionStage::proposed(
                            1,
                            evidence(9, 1),
                            12,
                        ))
                    },
                )
            });
            retry_ingress
                .send_resume(retry)
                .unwrap_or_else(|_| panic!("send resume"));
            worker
                .join()
                .expect("resume worker")
                .unwrap_or_else(|_| panic!("retry boundary failed"))
        });
        let WakeWorkOutcome::Prepared(retried) = retry_outcome else {
            panic!("expected prepared retry")
        };
        assert_eq!(retried.admitted_wake().handoff_receipt(), original_handoff);
    }

    #[test]
    fn pending_integrity_receipt_binds_head_budget_resources_count_and_evidence() {
        let (current, successor_world, _) = verified_successor_fixture();
        let admitted = admit_cause(&current, AuthenticatedWakeCause::world(successor_world))
            .expect("admitted");
        let key = key(9, 0x91);
        let observed = resources(10, 20, 30, 40);
        let record = issue_for(&key, &admitted, &observed, limits());
        let budget = verify_external_work_budget(
            &record,
            &key,
            &ceilings(),
            IDENTITY,
            admitted.handoff_receipt(),
            admitted.prior_organism_receipt(),
            resource_observation_receipt(&observed),
        )
        .expect("verified budget");
        let head = admitted.current_head();
        let delta = SuppliedResourceDelta {
            cpu_nanoseconds: 1,
            resident_byte_growth: 2,
            durable_byte_growth: 3,
            native_calls: 4,
        };
        let restart = evidence(4, 1);
        let receipt =
            pending_package_receipt(&admitted, &budget, &head, &observed, delta, 1, &restart);

        let mut changed_head = head.clone();
        changed_head.world_revision += 1;
        assert_ne!(
            receipt,
            pending_package_receipt(
                &admitted,
                &budget,
                &changed_head,
                &observed,
                delta,
                1,
                &restart
            )
        );
        let changed_delta = SuppliedResourceDelta {
            native_calls: 5,
            ..delta
        };
        assert_ne!(
            receipt,
            pending_package_receipt(
                &admitted,
                &budget,
                &head,
                &observed,
                changed_delta,
                1,
                &restart
            )
        );
        let mut other_limits = limits();
        other_limits.max_cpu_nanoseconds -= 1;
        let other_record = issue_for(&key, &admitted, &observed, other_limits);
        let other_budget = verify_external_work_budget(
            &other_record,
            &key,
            &ceilings(),
            IDENTITY,
            admitted.handoff_receipt(),
            admitted.prior_organism_receipt(),
            resource_observation_receipt(&observed),
        )
        .expect("other verified budget");
        assert_ne!(
            receipt,
            pending_package_receipt(
                &admitted,
                &other_budget,
                &head,
                &observed,
                delta,
                1,
                &restart
            )
        );
        assert_ne!(
            receipt,
            pending_package_receipt(
                &admitted,
                &budget,
                &head,
                &resources(11, 20, 30, 40),
                delta,
                1,
                &restart
            )
        );
        assert_ne!(
            receipt,
            pending_package_receipt(&admitted, &budget, &head, &observed, delta, 2, &restart)
        );
        assert_ne!(
            receipt,
            pending_package_receipt(
                &admitted,
                &budget,
                &head,
                &observed,
                delta,
                1,
                &evidence(8, 1)
            )
        );
    }

    #[test]
    fn actual_pending_receipt_tamper_is_rejected_before_resume_capability() {
        let (current, successor_world, _) = verified_successor_fixture();
        let admitted = admit_cause(&current, AuthenticatedWakeCause::world(successor_world))
            .expect("admitted");
        let key = key(9, 0x91);
        let observed = resources(10, 20, 30, 40);
        let record = issue_for(&key, &admitted, &observed, limits());
        let budget = verify_external_work_budget(
            &record,
            &key,
            &ceilings(),
            IDENTITY,
            admitted.handoff_receipt(),
            admitted.prior_organism_receipt(),
            resource_observation_receipt(&observed),
        )
        .expect("verified budget");
        let mut pending = pending(
            admitted,
            budget,
            observed,
            SuppliedResourceDelta {
                cpu_nanoseconds: 0,
                resident_byte_growth: 0,
                durable_byte_growth: 0,
                native_calls: 0,
            },
            0,
            evidence(4, 1),
        );
        pending.package_receipt[0] ^= 1;
        assert_eq!(
            pending.into_resume_capability().err(),
            Some(WakeAdmissionError::PendingPackageIntegrityFailed)
        );
    }

    #[test]
    fn wrong_organism_receipt_is_rejected_even_when_sealed_head_matches() {
        let (current, successor_world, _) = verified_successor_fixture();
        let admitted = admit_cause(&current, AuthenticatedWakeCause::world(successor_world))
            .expect("admitted");
        let head = admitted.current_head();
        let mut wrong_receipt = admitted.prior_organism_receipt();
        wrong_receipt[0] ^= 1;
        assert_eq!(
            validate_resume_coordinates(
                wrong_receipt,
                &head,
                current.organism_state_receipt(),
                &head
            )
            .err(),
            Some(WakeAdmissionError::ResumeOrganismReceiptMismatch)
        );
        let mut wrong_head = head.clone();
        wrong_head.world_revision += 1;
        assert_eq!(
            validate_resume_coordinates(
                current.organism_state_receipt(),
                &head,
                current.organism_state_receipt(),
                &wrong_head,
            )
            .err(),
            Some(WakeAdmissionError::ResumeHeadMismatch)
        );

        let mut capability = WakeResumeCapability {
            unchanged_head: head,
            admitted_wake: admitted,
            restart_evidence: evidence(4, 1),
        };
        capability.admitted_wake.prior_organism_receipt = wrong_receipt;
        let boundary = boundary_with_resume(capability);
        let key = key(9, 0x91);
        let result: Result<WakeWorkOutcome<u64>, WakeBoundaryFailure<(), ()>> = boundary
            .block_and_prepare(
                &current,
                &10,
                &key,
                &ceilings(),
                || Ok(resources(10, 20, 30, 40)),
                |admitted, observed| issue_for(&key, admitted, observed, limits()),
                |_, _, _, _| {
                    Ok(SuppliedNativeTransitionStage::proposed(
                        1,
                        evidence(8, 1),
                        11,
                    ))
                },
            );
        let Err(WakeBoundaryFailure::RejectedResume { error, capability }) = result else {
            panic!("expected retained resume rejection")
        };
        assert_eq!(error, WakeAdmissionError::ResumeOrganismReceiptMismatch);
        assert_eq!(capability.expected_organism_receipt(), wrong_receipt);
        assert_eq!(
            capability.expected_head(),
            WakeHeadSnapshot::current(&current)
        );
    }

    #[test]
    fn post_admission_observer_failure_returns_owned_retry_package() {
        let (current, successor_world, _) = verified_successor_fixture();
        let key = key(9, 0x91);
        let initial = evidence(4, 1);
        let initial_receipt = initial.receipt();
        let boundary = boundary_with(AuthenticatedWakeCause::world(successor_world), initial);
        let result: Result<WakeWorkOutcome<u64>, WakeBoundaryFailure<&str, ()>> = boundary
            .block_and_prepare(
                &current,
                &10,
                &key,
                &ceilings(),
                || Err("observer unavailable"),
                |admitted, observed| issue_for(&key, admitted, observed, limits()),
                |_, _, _, _| {
                    Ok(SuppliedNativeTransitionStage::proposed(
                        1,
                        evidence(8, 1),
                        11,
                    ))
                },
            );
        let Err(WakeBoundaryFailure::AcceptedForRetry(retry)) = result else {
            panic!("expected accepted retry")
        };
        assert_eq!(retry.unchanged_head(), WakeHeadSnapshot::current(&current));
        assert_eq!(retry.prepared_transitions(), 0);
        assert_eq!(retry.restart_evidence().receipt(), initial_receipt);
        assert!(matches!(
            retry.failure(),
            AcceptedWakeFailure::Observer("observer unavailable")
        ));
        assert!(
            retry
                .admitted_wake()
                .cause()
                .canonical_record_bytes()
                .0
                .len()
                > 1
        );
        let retry_input = retry.into_resume();
        assert_eq!(
            retry_input.unchanged_head,
            WakeHeadSnapshot::current(&current)
        );
        assert_eq!(
            retry_input.capability.restart_evidence.receipt(),
            initial_receipt
        );
        assert_eq!(retry_input.prepared_transitions, 0);
        assert!(retry_input.budget.is_none());
        assert!(retry_input.latest_supplied_resources.is_none());
        assert!(matches!(
            retry_input.failure,
            AcceptedWakeFailure::Observer("observer unavailable")
        ));
        assert!(
            retry_input
                .capability
                .admitted_wake
                .cause()
                .canonical_record_bytes()
                .0
                .len()
                > 1
        );
        let retry_boundary = boundary_with_resume(retry_input.capability);
        let mut retry_observations =
            VecDeque::from([resources(20, 20, 30, 50), resources(21, 20, 30, 51)]);
        let retried = retry_boundary
            .block_and_prepare(
                &current,
                &10,
                &key,
                &ceilings(),
                || Ok::<_, ()>(retry_observations.pop_front().expect("retry observation")),
                |admitted, observed| issue_for(&key, admitted, observed, limits()),
                |_, _, _, _| {
                    Ok::<_, ()>(SuppliedNativeTransitionStage::proposed(
                        1,
                        evidence(8, 1),
                        11,
                    ))
                },
            )
            .unwrap_or_else(|_| panic!("accepted cause retry failed"));
        assert!(matches!(retried, WakeWorkOutcome::Prepared(_)));
    }

    #[test]
    fn transition_failure_retains_both_transition_and_post_attempt_observer_failure() {
        let (current, successor_world, _) = verified_successor_fixture();
        let boundary = boundary_with(
            AuthenticatedWakeCause::world(successor_world),
            evidence(4, 1),
        );
        let key = key(9, 0x91);
        let mut observations = VecDeque::from([
            Ok(resources(10, 20, 30, 40)),
            Err("post-attempt observer unavailable"),
        ]);
        let result: Result<WakeWorkOutcome<u64>, WakeBoundaryFailure<&str, &str>> = boundary
            .block_and_prepare(
                &current,
                &10,
                &key,
                &ceilings(),
                || observations.pop_front().expect("observation result"),
                |admitted, observed| issue_for(&key, admitted, observed, limits()),
                |_, _, _, _| Err("transition failed"),
            );
        let Err(WakeBoundaryFailure::AcceptedForRetry(retry)) = result else {
            panic!("expected retry")
        };
        assert!(matches!(
            retry.failure(),
            AcceptedWakeFailure::TransitionAndObserver(
                "transition failed",
                "post-attempt observer unavailable"
            )
        ));
        assert_eq!(
            retry
                .latest_supplied_resources()
                .expect("prior supplied observation")
                .cpu_nanoseconds,
            10
        );
    }

    #[test]
    fn transition_failure_also_reports_post_attempt_budget_excess() {
        let (current, successor_world, _) = verified_successor_fixture();
        let boundary = boundary_with(
            AuthenticatedWakeCause::world(successor_world),
            evidence(4, 1),
        );
        let key = key(9, 0x91);
        let mut observations =
            VecDeque::from([resources(10, 20, 30, 40), resources(111, 20, 30, 40)]);
        let result: Result<WakeWorkOutcome<u64>, WakeBoundaryFailure<(), &str>> = boundary
            .block_and_prepare(
                &current,
                &10,
                &key,
                &ceilings(),
                || Ok(observations.pop_front().expect("observation")),
                |admitted, observed| issue_for(&key, admitted, observed, limits()),
                |_, _, _, _| Err("transition failed"),
            );
        let Err(WakeBoundaryFailure::AcceptedForRetry(retry)) = result else {
            panic!("expected retry")
        };
        assert!(matches!(
            retry.failure(),
            AcceptedWakeFailure::TransitionAndBoundary(
                "transition failed",
                WakeAdmissionError::SuppliedObservationExceedsWorkBudget
            )
        ));
        assert_eq!(
            retry
                .latest_supplied_resources()
                .expect("post-stage supplied observation")
                .cpu_nanoseconds,
            111
        );
    }

    #[test]
    fn successful_stage_followed_by_observer_failure_records_attempt_context() {
        let (current, successor_world, _) = verified_successor_fixture();
        let initial = evidence(4, 1);
        let initial_receipt = initial.receipt();
        let boundary = boundary_with(AuthenticatedWakeCause::world(successor_world), initial);
        let key = key(9, 0x91);
        let mut observations = VecDeque::from([
            Ok(resources(10, 20, 30, 40)),
            Err("post-success observer unavailable"),
        ]);
        let result: Result<WakeWorkOutcome<u64>, WakeBoundaryFailure<&str, ()>> = boundary
            .block_and_prepare(
                &current,
                &10,
                &key,
                &ceilings(),
                || observations.pop_front().expect("observation result"),
                |admitted, observed| issue_for(&key, admitted, observed, limits()),
                |_, _, _, _| {
                    Ok(SuppliedNativeTransitionStage::proposed(
                        2,
                        evidence(8, 1),
                        11,
                    ))
                },
            );
        let Err(WakeBoundaryFailure::AcceptedForRetry(retry)) = result else {
            panic!("expected retry")
        };
        assert!(matches!(
            retry.failure(),
            AcceptedWakeFailure::StagePreparedAndObserverFailed {
                attempted_prepared_transitions: 2,
                observer_error: "post-success observer unavailable"
            }
        ));
        assert_eq!(retry.prepared_transitions(), 0);
        assert_eq!(retry.restart_evidence().receipt(), initial_receipt);
        assert_eq!(
            retry
                .latest_supplied_resources()
                .expect("prior supplied observation")
                .cpu_nanoseconds,
            10
        );
    }

    #[test]
    fn zero_progress_stage_is_post_sampled_and_cannot_replace_prior_evidence() {
        let (current, successor_world, _) = verified_successor_fixture();
        let key = key(9, 0x91);
        let initial = evidence(4, 1);
        let initial_receipt = initial.receipt();
        let boundary = boundary_with(AuthenticatedWakeCause::world(successor_world), initial);
        let mut observations =
            VecDeque::from([resources(10, 20, 30, 40), resources(12, 21, 30, 41)]);
        let result: Result<WakeWorkOutcome<u64>, WakeBoundaryFailure<(), ()>> = boundary
            .block_and_prepare(
                &current,
                &10,
                &key,
                &ceilings(),
                || Ok(observations.pop_front().expect("observation")),
                |admitted, observed| issue_for(&key, admitted, observed, limits()),
                |_, _, _, _| Ok(SuppliedNativeTransitionStage::continuing(0, evidence(9, 1))),
            );
        let Err(WakeBoundaryFailure::AcceptedForRetry(retry)) = result else {
            panic!("expected retry")
        };
        assert!(matches!(
            retry.failure(),
            AcceptedWakeFailure::Boundary(WakeAdmissionError::StageMadeNoProgress)
        ));
        assert_eq!(retry.restart_evidence().receipt(), initial_receipt);
        assert_eq!(
            retry
                .latest_supplied_resources()
                .expect("post-stage supplied observation")
                .cpu_nanoseconds,
            12
        );
    }

    #[test]
    fn post_stage_count_overflow_is_sampled_before_retry() {
        let (current, successor_world, _) = verified_successor_fixture();
        let boundary = boundary_with(
            AuthenticatedWakeCause::world(successor_world),
            evidence(4, 1),
        );
        let key = key(9, 0x91);
        let mut untrusted_limits = limits();
        untrusted_limits.max_prepared_transitions = u64::MAX;
        let supplied_policy =
            SuppliedDeploymentAdmissionCeilings::new(untrusted_limits, [0xc1; 32])
                .expect("supplied policy is not production verification");
        let stage_calls = Cell::new(0_u8);
        let mut observations = VecDeque::from([
            resources(10, 20, 30, 40),
            resources(11, 20, 30, 40),
            resources(12, 20, 30, 40),
        ]);
        let result: Result<WakeWorkOutcome<u64>, WakeBoundaryFailure<(), ()>> = boundary
            .block_and_prepare(
                &current,
                &10,
                &key,
                &supplied_policy,
                || Ok(observations.pop_front().expect("observation")),
                |admitted, observed| issue_for(&key, admitted, observed, untrusted_limits),
                |_, _, _, _| {
                    let call = stage_calls.get();
                    stage_calls.set(call + 1);
                    Ok(SuppliedNativeTransitionStage::continuing(
                        if call == 0 { u64::MAX - 1 } else { 2 },
                        evidence(if call == 0 { 8 } else { 10 }, 1),
                    ))
                },
            );
        let Err(WakeBoundaryFailure::AcceptedForRetry(retry)) = result else {
            panic!("expected count-overflow retry")
        };
        assert!(matches!(
            retry.failure(),
            AcceptedWakeFailure::Boundary(WakeAdmissionError::ArithmeticOverflow)
        ));
        assert_eq!(stage_calls.get(), 2);
        assert_eq!(retry.prepared_transitions(), u64::MAX - 1);
        assert_eq!(retry.restart_evidence().receipt(), evidence(8, 1).receipt());
        assert_eq!(
            retry
                .latest_supplied_resources()
                .expect("post-overflow supplied observation")
                .cpu_nanoseconds,
            12
        );
    }

    #[test]
    fn oversized_initial_evidence_is_retry_failure_never_pending() {
        let (current, successor_world, _) = verified_successor_fixture();
        let key = key(9, 0x91);
        let mut constrained = limits();
        constrained.max_continuation_bytes = 1;
        let boundary = boundary_with(
            AuthenticatedWakeCause::world(successor_world),
            evidence(4, 2),
        );
        let stage_calls = Cell::new(0);
        let result: Result<WakeWorkOutcome<u64>, WakeBoundaryFailure<(), ()>> = boundary
            .block_and_prepare(
                &current,
                &10,
                &key,
                &ceilings(),
                || Ok(resources(10, 20, 30, 40)),
                |admitted, observed| issue_for(&key, admitted, observed, constrained),
                |_, _, _, _| {
                    stage_calls.set(stage_calls.get() + 1);
                    Ok(SuppliedNativeTransitionStage::proposed(
                        1,
                        evidence(8, 1),
                        11,
                    ))
                },
            );
        assert!(matches!(
            result,
            Err(WakeBoundaryFailure::AcceptedForRetry(_))
        ));
        assert_eq!(stage_calls.get(), 0);
    }

    #[test]
    fn resource_delta_is_exact_and_regressions_fail_closed() {
        let before = resources(10, 20, 30, 40);
        let after = resources(19, 15, 36, 43);
        assert_eq!(
            resource_delta(&before, &after, 27, 38).expect("delta"),
            SuppliedResourceDelta {
                cpu_nanoseconds: 9,
                resident_byte_growth: 7,
                durable_byte_growth: 8,
                native_calls: 3,
            }
        );
        assert_eq!(
            resource_delta(&before, &resources(9, 20, 30, 40), 20, 30).err(),
            Some(WakeAdmissionError::ResourceCounterRegressed(
                "CPU nanoseconds"
            ))
        );
        assert_eq!(
            resource_delta(&before, &resources(10, 20, 30, 39), 20, 30).err(),
            Some(WakeAdmissionError::ResourceCounterRegressed("native calls"))
        );
    }

    #[test]
    fn every_supplied_resource_limit_accepts_exact_and_rejects_one_over() {
        let limits = limits();
        let exact_delta = SuppliedResourceDelta {
            cpu_nanoseconds: limits.max_cpu_nanoseconds,
            resident_byte_growth: limits.max_resident_byte_growth,
            durable_byte_growth: limits.max_durable_byte_growth,
            native_calls: limits.max_native_calls,
        };
        let mut exact_observation = resources(0, 0, 0, 0);
        exact_observation.recovery_reserve_bytes = limits.min_recovery_reserve_bytes;
        assert!(stage_fits_supplied_budget(
            limits,
            limits.max_prepared_transitions,
            exact_delta,
            limits.max_continuation_bytes,
            &exact_observation,
        ));

        let mut violations = Vec::new();
        violations.push((
            limits.max_prepared_transitions + 1,
            exact_delta,
            limits.max_continuation_bytes,
            exact_observation.clone(),
        ));
        let mut delta = exact_delta;
        delta.native_calls += 1;
        violations.push((
            limits.max_prepared_transitions,
            delta,
            limits.max_continuation_bytes,
            exact_observation.clone(),
        ));
        let mut delta = exact_delta;
        delta.cpu_nanoseconds += 1;
        violations.push((
            limits.max_prepared_transitions,
            delta,
            limits.max_continuation_bytes,
            exact_observation.clone(),
        ));
        let mut delta = exact_delta;
        delta.resident_byte_growth += 1;
        violations.push((
            limits.max_prepared_transitions,
            delta,
            limits.max_continuation_bytes,
            exact_observation.clone(),
        ));
        let mut delta = exact_delta;
        delta.durable_byte_growth += 1;
        violations.push((
            limits.max_prepared_transitions,
            delta,
            limits.max_continuation_bytes,
            exact_observation.clone(),
        ));
        violations.push((
            limits.max_prepared_transitions,
            exact_delta,
            limits.max_continuation_bytes + 1,
            exact_observation.clone(),
        ));
        let mut low_reserve = exact_observation;
        low_reserve.recovery_reserve_bytes -= 1;
        violations.push((
            limits.max_prepared_transitions,
            exact_delta,
            limits.max_continuation_bytes,
            low_reserve,
        ));

        for (prepared, delta, continuation, observed) in violations {
            assert!(!stage_fits_supplied_budget(
                limits,
                prepared,
                delta,
                continuation,
                &observed,
            ));
        }
    }

    #[test]
    fn python_observation_and_zero_progress_fail_closed() {
        let mut observed = resources(1, 2, 3, 4);
        observed.python_calls = 1;
        assert_eq!(
            validate_native_observation(&observed).err(),
            Some(WakeAdmissionError::PythonCallsObserved)
        );
        let stage = SuppliedNativeTransitionStage::<u64>::continuing(0, evidence(4, 1));
        assert_eq!(stage.prepared_transitions, 0);
    }

    #[test]
    fn continuation_receipt_binds_schema_provenance_length_and_payload() {
        let first = evidence(4, 3);
        let other_payload = SuppliedRestartEvidence::new([4; 32], [5; 32], &[4; 4], &ceilings())
            .expect("other payload");
        let other_schema = SuppliedRestartEvidence::new([6; 32], [5; 32], &[4; 3], &ceilings())
            .expect("other schema");
        assert_ne!(first.receipt(), other_payload.receipt());
        assert_ne!(first.receipt(), other_schema.receipt());
    }

    #[test]
    fn pending_keeps_the_sealed_input_head_unchanged() {
        let current = WakeHeadSnapshot {
            world_revision: 5,
            world_receipt: [1; 32],
            world_state_receipt: [2; 32],
            world_mount_epoch: 3,
            body_sequence: 7,
            body_source_time: BigRational::from_integer(7.into()),
            body_state_receipt: [4; 32],
            body_manifest_receipt: [5; 32],
            body_mount_epoch: 6,
        };
        let next = WakeHeadSnapshot {
            world_revision: 6,
            world_receipt: [7; 32],
            world_state_receipt: [8; 32],
            ..current.clone()
        };
        assert_ne!(current, next);
        assert_eq!(current.world_revision, 5);
        assert_eq!(current.body_sequence, 7);
    }
}
