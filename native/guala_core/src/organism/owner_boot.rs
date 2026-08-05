//! One-use credential ingress for the sole native owner boot boundary.
//!
//! The native PID1 must receive one fixed, versioned Secrets Manager record
//! through one exact environment name and call this boundary before starting
//! any thread or service. The record contains the global-owner epoch/root and
//! the deployment envelope authenticated by that same root. This module reads
//! it once per process, scrubs the original C-environment bytes, removes every
//! matching entry, and exposes no alias or fallback credential. Its completed
//! boot capability also retains the canonical EFS owner lock; the parsed
//! credential alone does not claim global uniqueness.

use super::generation_store::{
    AllocatedZeroedOrganismArena, AuthenticatedCurrentPreflightPlan,
    AuthenticatedCurrentSealFraming, AuthenticatedOrganismStructuralPreflight,
    AuthenticatedPopulatedOrganismArena, CandidateUniquenessError, CandidateUniquenessProof,
    CurrentAuthenticationError, CurrentGenesisVerificationError, CurrentMappingError,
    CurrentObjectVerificationError, CurrentObjectVerificationProof,
    CurrentOrganismArenaAllocationError, CurrentOrganismStructuralPreflightError,
    CurrentPreflightError, CurrentSealFramingAuthenticationError, GenerationStoreError,
    NativeGlobalOwnerLock, UnverifiedCurrentMapping,
};
use super::genesis::VerifiedGenesisIdentity;
use super::platform_envelope::{PlatformEnvelopeError, PLATFORM_ENVELOPE_RECORD_BYTES};
use super::platform_observer::{
    NativePlatformObservation, PlatformBoundGlobalOwner, PostAllocationWindowObservation,
};
use super::wake_admission::{SuppliedGlobalOwnerRootKey, WakeAdmissionError};
use std::fmt;
use std::sync::atomic::{AtomicBool, Ordering};
use zeroize::Zeroizing;

const BOOT_ENVIRONMENT_NAME: &str = "GUALA_GLOBAL_OWNER_BOOT_V1";
const BOOT_ENVIRONMENT_C_NAME: &[u8] = b"GUALA_GLOBAL_OWNER_BOOT_V1\0";
const BOOT_MAGIC: &[u8; 8] = b"GULBOT01";
const BOOT_VERSION: u16 = 1;
const BOOT_FLAGS: u16 = 0;
const BOOT_HEADER_BYTES: usize = 8 + 2 + 2 + 4;
const BOOT_OWNER_BYTES: usize = 4 + 32;
const BOOT_PAYLOAD_BYTES: usize = BOOT_OWNER_BYTES + PLATFORM_ENVELOPE_RECORD_BYTES;
const BOOT_RECORD_BYTES: usize = BOOT_HEADER_BYTES + BOOT_PAYLOAD_BYTES;
const BOOT_HEX_BYTES: usize = BOOT_RECORD_BYTES * 2;

static BOOT_BUNDLE_TAKEN: AtomicBool = AtomicBool::new(false);

/// Safe sibling modules cannot forge this boot-ingress capability because its
/// only field is private to this module.
pub(crate) struct OwnerBootRootIngress {
    _private: (),
}

impl OwnerBootRootIngress {
    #[cfg(test)]
    pub(super) fn for_test() -> Self {
        Self { _private: () }
    }
}

/// Safe sibling modules may name this ingress but cannot construct it. This
/// module creates it only after the owner-held V2 HMAC transition has committed.
pub(super) struct AuthenticatedCurrentPreflightIngress {
    _private: (),
}

/// Safe sibling modules may name this ingress but cannot construct it. This
/// module creates it only for the authenticated owner-held preflight plan.
pub(super) struct CandidateUniquenessIngress {
    _private: (),
}

/// Safe sibling modules may name this ingress but cannot construct it. This
/// module creates it only after candidate uniqueness has been proven.
pub(super) struct CurrentObjectVerificationIngress {
    _private: (),
}

/// Safe sibling modules may name this ingress but cannot construct it. This
/// module creates it only after exact CURRENT object-reference verification.
pub(super) struct CurrentGenesisVerificationIngress {
    _private: (),
}

/// Safe sibling modules may name this ingress but cannot construct it. This
/// module creates it only after exact CURRENT-pinned genesis verification.
pub(super) struct CurrentSealFramingAuthenticationIngress {
    _private: (),
}

/// Safe sibling modules may name this ingress but cannot construct it. This
/// module creates it only after exact CURRENT seal framing authentication.
pub(super) struct CurrentOrganismStructuralPreflightIngress {
    _private: (),
}

/// Safe sibling modules may name this ingress but cannot construct it. This
/// module creates it only after authenticated organism structural preflight.
pub(super) struct CurrentOrganismArenaAllocationIngress {
    _private: (),
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) enum OwnerBootError {
    AlreadyConsumed,
    MissingBundle,
    DuplicateBundle,
    NonUnicodeBundle,
    EnvironmentRemovalFailed,
    WrongHexLength,
    NoncanonicalHex,
    BadMagic,
    UnsupportedVersion,
    WrongFlags,
    PayloadLengthMismatch,
    GlobalOwner(WakeAdmissionError),
    Platform(PlatformEnvelopeError),
    GlobalOwnerLock(GenerationStoreError),
    CurrentMapping(CurrentMappingError),
    CurrentAuthentication(CurrentAuthenticationError),
    CurrentPreflight(CurrentPreflightError),
    CandidateUniqueness(CandidateUniquenessError),
    CurrentObjectVerification(CurrentObjectVerificationError),
    CurrentGenesisVerification(CurrentGenesisVerificationError),
    CurrentSealFramingAuthentication(CurrentSealFramingAuthenticationError),
    CurrentOrganismStructuralPreflight(CurrentOrganismStructuralPreflightError),
    CurrentOrganismArenaAllocation(CurrentOrganismArenaAllocationError),
}

impl fmt::Display for OwnerBootError {
    fn fmt(&self, output: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::AlreadyConsumed => {
                write!(output, "global-owner boot bundle was already consumed")
            }
            Self::MissingBundle => write!(output, "global-owner boot bundle is absent"),
            Self::DuplicateBundle => write!(output, "global-owner boot bundle is duplicated"),
            Self::NonUnicodeBundle => write!(output, "global-owner boot bundle is not UTF-8"),
            Self::EnvironmentRemovalFailed => {
                write!(output, "global-owner boot bundle could not be removed")
            }
            Self::WrongHexLength => write!(output, "global-owner boot bundle length differs"),
            Self::NoncanonicalHex => {
                write!(
                    output,
                    "global-owner boot bundle is not lowercase hexadecimal"
                )
            }
            Self::BadMagic => write!(output, "global-owner boot bundle magic differs"),
            Self::UnsupportedVersion => write!(output, "global-owner boot version differs"),
            Self::WrongFlags => write!(output, "global-owner boot flags differ"),
            Self::PayloadLengthMismatch => {
                write!(output, "global-owner boot payload length differs")
            }
            Self::GlobalOwner(error) => write!(output, "global-owner root failed: {error}"),
            Self::Platform(error) => write!(output, "platform binding failed: {error}"),
            Self::GlobalOwnerLock(error) => write!(output, "global owner lock failed: {error}"),
            Self::CurrentMapping(error) => {
                write!(output, "unverified CURRENT mapping failed: {error}")
            }
            Self::CurrentAuthentication(error) => {
                write!(output, "CURRENT authentication failed: {error}")
            }
            Self::CurrentPreflight(error) => {
                write!(
                    output,
                    "authenticated CURRENT framing preflight failed: {error}"
                )
            }
            Self::CandidateUniqueness(error) => {
                write!(output, "CURRENT candidate uniqueness failed: {error}")
            }
            Self::CurrentObjectVerification(error) => {
                write!(
                    output,
                    "CURRENT object reference verification failed: {error}"
                )
            }
            Self::CurrentGenesisVerification(error) => {
                write!(
                    output,
                    "CURRENT-pinned genesis verification failed: {error}"
                )
            }
            Self::CurrentSealFramingAuthentication(error) => write!(
                output,
                "CURRENT-pinned seal framing authentication failed: {error}"
            ),
            Self::CurrentOrganismStructuralPreflight(error) => write!(
                output,
                "CURRENT-pinned organism structural preflight failed: {error}"
            ),
            Self::CurrentOrganismArenaAllocation(error) => write!(
                output,
                "CURRENT-pinned organism arena allocation failed: {error}"
            ),
        }
    }
}

impl std::error::Error for OwnerBootError {}

impl From<WakeAdmissionError> for OwnerBootError {
    fn from(value: WakeAdmissionError) -> Self {
        Self::GlobalOwner(value)
    }
}

impl From<PlatformEnvelopeError> for OwnerBootError {
    fn from(value: PlatformEnvelopeError) -> Self {
        Self::Platform(value)
    }
}

impl From<GenerationStoreError> for OwnerBootError {
    fn from(value: GenerationStoreError) -> Self {
        Self::GlobalOwnerLock(value)
    }
}

impl From<CurrentMappingError> for OwnerBootError {
    fn from(value: CurrentMappingError) -> Self {
        Self::CurrentMapping(value)
    }
}

impl From<CurrentAuthenticationError> for OwnerBootError {
    fn from(value: CurrentAuthenticationError) -> Self {
        Self::CurrentAuthentication(value)
    }
}

impl From<CurrentPreflightError> for OwnerBootError {
    fn from(value: CurrentPreflightError) -> Self {
        Self::CurrentPreflight(value)
    }
}

impl From<CandidateUniquenessError> for OwnerBootError {
    fn from(value: CandidateUniquenessError) -> Self {
        Self::CandidateUniqueness(value)
    }
}

impl From<CurrentObjectVerificationError> for OwnerBootError {
    fn from(value: CurrentObjectVerificationError) -> Self {
        Self::CurrentObjectVerification(value)
    }
}

impl From<CurrentGenesisVerificationError> for OwnerBootError {
    fn from(value: CurrentGenesisVerificationError) -> Self {
        Self::CurrentGenesisVerification(value)
    }
}

impl From<CurrentSealFramingAuthenticationError> for OwnerBootError {
    fn from(value: CurrentSealFramingAuthenticationError) -> Self {
        Self::CurrentSealFramingAuthentication(value)
    }
}

impl From<CurrentOrganismStructuralPreflightError> for OwnerBootError {
    fn from(value: CurrentOrganismStructuralPreflightError) -> Self {
        Self::CurrentOrganismStructuralPreflight(value)
    }
}

impl From<CurrentOrganismArenaAllocationError> for OwnerBootError {
    fn from(value: CurrentOrganismArenaAllocationError) -> Self {
        Self::CurrentOrganismArenaAllocation(value)
    }
}

/// Non-clonable one-use secret bundle. Its global root moves into the native
/// platform binding; it is never returned or exposed as raw key bytes.
pub(crate) struct NativeOwnerBootBundle {
    global_owner: SuppliedGlobalOwnerRootKey,
    platform_envelope: [u8; PLATFORM_ENVELOPE_RECORD_BYTES],
}

/// Platform-bound global root plus the canonical cross-process EFS flock.
/// The lock is declared last so it is released after the platform/root
/// capability during ordinary field destruction.
pub(crate) struct NativeGlobalOwnerBoot {
    _platform: PlatformBoundGlobalOwner,
    _global_owner_lock: NativeGlobalOwnerLock,
}

/// The platform-bound sole owner retaining the exact, read-only bytes copied
/// from canonical CURRENT. The mapping remains explicitly unverified until a
/// later owner-held authentication boundary parses and authenticates it.
pub(crate) struct NativeCurrentMappedOwner {
    _platform: PlatformBoundGlobalOwner,
    unverified_current: UnverifiedCurrentMapping,
    // Declared last so the canonical global lock outlives both the platform
    // capability and the page-backed CURRENT bytes during ordinary drop.
    _global_owner_lock: NativeGlobalOwnerLock,
}

/// Exact mapped CURRENT bytes after V2 framing, canonical length, and the
/// global-owner-root HMAC have been verified. Construction is private to this
/// owner module, so safe sibling modules cannot promote unverified bytes.
struct AuthenticatedCurrentMapping {
    mapping: UnverifiedCurrentMapping,
}

impl AuthenticatedCurrentMapping {
    fn bytes(&self) -> &[u8] {
        self.mapping.bytes()
    }
}

/// The sole owner after authenticating the immutable CURRENT snapshot. This
/// does not yet claim that variable payload fields were parsed or restored.
pub(crate) struct NativeCurrentAuthenticatedOwner {
    _platform: PlatformBoundGlobalOwner,
    _authenticated_current: AuthenticatedCurrentMapping,
    // Declared last so the canonical global lock outlives the root capability
    // and authenticated snapshot during ordinary destruction.
    _global_owner_lock: NativeGlobalOwnerLock,
}

/// Sole owner after allocation-free framing preflight. The plan contains only
/// checked offsets/counts and confers no object, rational, or DSF semantics.
pub(crate) struct NativeCurrentPreflightOwner {
    _platform: PlatformBoundGlobalOwner,
    _authenticated_current: AuthenticatedCurrentMapping,
    _preflight_plan: AuthenticatedCurrentPreflightPlan,
    // Declared last so the global lock outlives the platform, mapping, and
    // framing plan during ordinary and failure-path destruction.
    _global_owner_lock: NativeGlobalOwnerLock,
}

/// Sole owner after exact candidate-digest uniqueness has been established.
/// The proof retains no sorted order and confers no DSF semantics.
pub(crate) struct NativeCurrentCandidateUniqueOwner {
    _platform: PlatformBoundGlobalOwner,
    _authenticated_current: AuthenticatedCurrentMapping,
    _preflight_plan: AuthenticatedCurrentPreflightPlan,
    _candidate_uniqueness: CandidateUniquenessProof,
    // Declared last so the global lock outlives every prior capability during
    // ordinary and failure-path destruction.
    _global_owner_lock: NativeGlobalOwnerLock,
}

/// Sole owner carrying historical evidence that every authenticated CURRENT
/// object reference passed exact-length and SHA-256 verification in one closed
/// descriptor pass. This owner retains no object inode custody. Any downstream
/// decode must reopen and rehash the exact object in that same decode pass.
pub(crate) struct NativeCurrentObjectReferencesVerifiedOwner {
    _platform: PlatformBoundGlobalOwner,
    _authenticated_current: AuthenticatedCurrentMapping,
    _preflight_plan: AuthenticatedCurrentPreflightPlan,
    _candidate_uniqueness: CandidateUniquenessProof,
    _object_verification: CurrentObjectVerificationProof,
    // Declared last so the global lock outlives the platform, CURRENT mapping,
    // framing plan, and both structural proofs on every destruction path.
    _global_owner_lock: NativeGlobalOwnerLock,
}

/// Sole owner after the exact CURRENT-pinned genesis record has been reopened,
/// rehashed, authenticated under the platform global owner, and proven to
/// carry exactly the identity bytes authenticated by CURRENT.
pub(crate) struct NativeCurrentGenesisVerifiedOwner {
    _platform: PlatformBoundGlobalOwner,
    _authenticated_current: AuthenticatedCurrentMapping,
    _preflight_plan: AuthenticatedCurrentPreflightPlan,
    _candidate_uniqueness: CandidateUniquenessProof,
    _object_verification: CurrentObjectVerificationProof,
    _verified_genesis: VerifiedGenesisIdentity,
    // Declared last so the global lock outlives the platform, mapping,
    // structural proofs, and verified genesis identity on every drop path.
    _global_owner_lock: NativeGlobalOwnerLock,
}

/// Sole owner carrying authenticated seal framing and the exact retained
/// organism descriptor. This proves scalar framing and authority only; it
/// carries no decoded organism, DSF, field-bank, or historical-chain claim.
pub(crate) struct NativeCurrentSealFramingAuthenticatedOwner {
    _platform: PlatformBoundGlobalOwner,
    _authenticated_current: AuthenticatedCurrentMapping,
    _preflight_plan: AuthenticatedCurrentPreflightPlan,
    _candidate_uniqueness: CandidateUniquenessProof,
    _object_verification: CurrentObjectVerificationProof,
    _verified_genesis: VerifiedGenesisIdentity,
    _seal_framing: AuthenticatedCurrentSealFraming,
    // Declared last so the global lock outlives the retained seal descriptor
    // and every preceding authority/proof on every destruction path.
    _global_owner_lock: NativeGlobalOwnerLock,
}

/// Sole owner carrying reauthenticated canonical schema/wire framing, exact
/// contiguous-arena request geometry, and the same retained seal descriptor.
/// This owner carries no decoded organism, semantic structure, DSF, cgroup
/// admission, allocation, or RSS authority.
pub(crate) struct NativeCurrentOrganismStructurallyPreflightedOwner {
    _platform: PlatformBoundGlobalOwner,
    _authenticated_current: AuthenticatedCurrentMapping,
    _preflight_plan: AuthenticatedCurrentPreflightPlan,
    _candidate_uniqueness: CandidateUniquenessProof,
    _object_verification: CurrentObjectVerificationProof,
    _verified_genesis: VerifiedGenesisIdentity,
    _seal_framing: AuthenticatedCurrentSealFraming,
    _organism_structural_preflight: AuthenticatedOrganismStructuralPreflight,
    // Declared last so the global lock outlives the retained descriptor and
    // every preceding authority/proof on every destruction path.
    _global_owner_lock: NativeGlobalOwnerLock,
}

/// Sole owner carrying one live page-touched zero-filled anonymous organism
/// arena with the exact authenticated requested and mapped geometry. The
/// retained before/after cgroup facts describe the allocation window; their
/// delta is not attributed to this mapping. No organism has been decoded or
/// populated, and no semantic or DSF authority is issued here.
pub(crate) struct NativeCurrentOrganismArenaAllocatedOwner {
    _platform: PlatformBoundGlobalOwner,
    _authenticated_current: AuthenticatedCurrentMapping,
    _preflight_plan: AuthenticatedCurrentPreflightPlan,
    _candidate_uniqueness: CandidateUniquenessProof,
    _object_verification: CurrentObjectVerificationProof,
    _verified_genesis: VerifiedGenesisIdentity,
    _seal_framing: AuthenticatedCurrentSealFraming,
    _organism_structural_preflight: AuthenticatedOrganismStructuralPreflight,
    _organism_arena: AllocatedZeroedOrganismArena,
    _organism_arena_observation: PostAllocationWindowObservation,
    // Declared last so the global lock outlives the live mutable mapping,
    // retained descriptor, physical observation, and every preceding proof.
    _global_owner_lock: NativeGlobalOwnerLock,
}

/// The allocated owner and every retained proof remain live after a failed
/// population attempt. The arena is zeroed before this value is returned, so
/// the exact authenticated descriptor can be retried without retaining partial
/// or unauthenticated organism bytes.
pub(crate) struct NativeCurrentOrganismArenaPopulationFailure {
    error: OwnerBootError,
    owner: NativeCurrentOrganismArenaAllocatedOwner,
}

impl NativeCurrentOrganismArenaPopulationFailure {
    pub(crate) fn error(&self) -> &OwnerBootError {
        &self.error
    }

    pub(crate) fn into_owner(self) -> NativeCurrentOrganismArenaAllocatedOwner {
        self.owner
    }
}

/// Sole owner of a directly populated, reauthenticated, structurally validated
/// GARN arena. Global S(UF) is not computed: the retained state contains the
/// five named evidence ranges, including the coherence evidence range. The
/// ratified +Coh direction remains a separate qualitative design constraint;
/// no scalar, component operator, global coupling, semantic, DSF-evaluation,
/// or transition authority is created here.
pub(crate) struct NativeCurrentOrganismArenaPopulatedOwner {
    _platform: PlatformBoundGlobalOwner,
    _authenticated_current: AuthenticatedCurrentMapping,
    _preflight_plan: AuthenticatedCurrentPreflightPlan,
    _candidate_uniqueness: CandidateUniquenessProof,
    _object_verification: CurrentObjectVerificationProof,
    _verified_genesis: VerifiedGenesisIdentity,
    _seal_framing: AuthenticatedCurrentSealFraming,
    _organism_structural_preflight: AuthenticatedOrganismStructuralPreflight,
    _organism_arena: AllocatedZeroedOrganismArena,
    _organism_arena_population: AuthenticatedPopulatedOrganismArena,
    _organism_arena_observation: PostAllocationWindowObservation,
    // Declared last so the global lock outlives the populated private mapping,
    // retained descriptor, observations, and every preceding proof.
    _global_owner_lock: NativeGlobalOwnerLock,
}

impl NativeGlobalOwnerBoot {
    pub(crate) fn map_unverified_current(self) -> Result<NativeCurrentMappedOwner, OwnerBootError> {
        // Keep `self` structurally intact across the fallible call. If mapping
        // fails, NativeGlobalOwnerBoot fields drop in declaration order and the
        // global lock therefore remains held until after the platform/root
        // capability. Move the fields only after every fallible step succeeds.
        let unverified_current = self
            ._global_owner_lock
            .map_unverified_current(self._platform.physical_mapping_window_observer())?;
        let Self {
            _platform: platform,
            _global_owner_lock: global_owner_lock,
        } = self;
        Ok(NativeCurrentMappedOwner {
            _platform: platform,
            unverified_current,
            _global_owner_lock: global_owner_lock,
        })
    }
}

impl NativeCurrentMappedOwner {
    pub(crate) fn authenticate_current_v2(
        self,
    ) -> Result<NativeCurrentAuthenticatedOwner, OwnerBootError> {
        // Keep `self` intact across verification so every error drops the root
        // capability before the global lock. Move fields only after success.
        self.unverified_current
            .verify_v2(self._platform.global_owner())?;
        let Self {
            _platform: platform,
            unverified_current,
            _global_owner_lock: global_owner_lock,
        } = self;
        Ok(NativeCurrentAuthenticatedOwner {
            _platform: platform,
            _authenticated_current: AuthenticatedCurrentMapping {
                mapping: unverified_current,
            },
            _global_owner_lock: global_owner_lock,
        })
    }
}

impl NativeCurrentAuthenticatedOwner {
    pub(crate) fn preflight_current_framing(
        self,
    ) -> Result<NativeCurrentPreflightOwner, OwnerBootError> {
        // Keep the authenticated owner intact over the fallible borrow. On
        // failure its declared field order keeps the global lock last.
        let plan = self
            ._authenticated_current
            .mapping
            .preflight_authenticated_v2(AuthenticatedCurrentPreflightIngress { _private: () })?;
        let Self {
            _platform: platform,
            _authenticated_current: authenticated_current,
            _global_owner_lock: global_owner_lock,
        } = self;
        Ok(NativeCurrentPreflightOwner {
            _platform: platform,
            _authenticated_current: authenticated_current,
            _preflight_plan: plan,
            _global_owner_lock: global_owner_lock,
        })
    }
}

impl NativeCurrentPreflightOwner {
    pub(crate) fn verify_candidate_uniqueness(
        self,
    ) -> Result<NativeCurrentCandidateUniqueOwner, OwnerBootError> {
        // Keep `self` intact over mapping, fill, sort, duplicate comparison,
        // post-observation, and scratch destruction. Every failure therefore
        // drops the platform, mapping, plan, and finally the global lock.
        let candidate_uniqueness = self
            ._authenticated_current
            .mapping
            .verify_candidate_uniqueness(
                self._preflight_plan,
                self._platform.physical_mapping_window_observer(),
                CandidateUniquenessIngress { _private: () },
            )?;
        let Self {
            _platform: platform,
            _authenticated_current: authenticated_current,
            _preflight_plan: preflight_plan,
            _global_owner_lock: global_owner_lock,
        } = self;
        Ok(NativeCurrentCandidateUniqueOwner {
            _platform: platform,
            _authenticated_current: authenticated_current,
            _preflight_plan: preflight_plan,
            _candidate_uniqueness: candidate_uniqueness,
            _global_owner_lock: global_owner_lock,
        })
    }
}

impl NativeCurrentCandidateUniqueOwner {
    pub(crate) fn verify_current_object_references(
        self,
    ) -> Result<NativeCurrentObjectReferencesVerifiedOwner, OwnerBootError> {
        // Keep every capability structurally intact throughout sequential
        // descriptor verification. On failure the lock remains the last field
        // destroyed, after platform, mapping, plan, and uniqueness proof.
        let object_verification = self
            ._authenticated_current
            .mapping
            .verify_current_object_references(
                self._preflight_plan,
                &self._global_owner_lock,
                CurrentObjectVerificationIngress { _private: () },
            )?;
        let Self {
            _platform: platform,
            _authenticated_current: authenticated_current,
            _preflight_plan: preflight_plan,
            _candidate_uniqueness: candidate_uniqueness,
            _global_owner_lock: global_owner_lock,
        } = self;
        Ok(NativeCurrentObjectReferencesVerifiedOwner {
            _platform: platform,
            _authenticated_current: authenticated_current,
            _preflight_plan: preflight_plan,
            _candidate_uniqueness: candidate_uniqueness,
            _object_verification: object_verification,
            _global_owner_lock: global_owner_lock,
        })
    }
}

impl NativeCurrentObjectReferencesVerifiedOwner {
    pub(crate) fn verify_current_genesis(
        self,
    ) -> Result<NativeCurrentGenesisVerifiedOwner, OwnerBootError> {
        // Keep the complete prior owner intact over the fixed-record reopen,
        // exact EOF/hash pass, genesis authentication, and identity comparison.
        // Every failure therefore drops the global lock last.
        let verified_genesis = self._authenticated_current.mapping.verify_current_genesis(
            self._preflight_plan,
            &self._global_owner_lock,
            self._platform.global_owner(),
            CurrentGenesisVerificationIngress { _private: () },
        )?;
        let Self {
            _platform: platform,
            _authenticated_current: authenticated_current,
            _preflight_plan: preflight_plan,
            _candidate_uniqueness: candidate_uniqueness,
            _object_verification: object_verification,
            _global_owner_lock: global_owner_lock,
        } = self;
        Ok(NativeCurrentGenesisVerifiedOwner {
            _platform: platform,
            _authenticated_current: authenticated_current,
            _preflight_plan: preflight_plan,
            _candidate_uniqueness: candidate_uniqueness,
            _object_verification: object_verification,
            _verified_genesis: verified_genesis,
            _global_owner_lock: global_owner_lock,
        })
    }
}

impl NativeCurrentGenesisVerifiedOwner {
    pub(crate) fn authenticate_current_seal_framing(
        self,
    ) -> Result<NativeCurrentSealFramingAuthenticatedOwner, OwnerBootError> {
        // Keep the full genesis-verified owner intact throughout positioned
        // preflight, rewind, streaming authentication, and final revalidation.
        // Move fields only after every fallible operation has succeeded.
        let seal_framing = self
            ._authenticated_current
            .mapping
            .authenticate_current_seal_framing(
                self._preflight_plan,
                &self._global_owner_lock,
                self._platform.global_owner(),
                &self._verified_genesis,
                CurrentSealFramingAuthenticationIngress { _private: () },
            )?;
        let Self {
            _platform: platform,
            _authenticated_current: authenticated_current,
            _preflight_plan: preflight_plan,
            _candidate_uniqueness: candidate_uniqueness,
            _object_verification: object_verification,
            _verified_genesis: verified_genesis,
            _global_owner_lock: global_owner_lock,
        } = self;
        Ok(NativeCurrentSealFramingAuthenticatedOwner {
            _platform: platform,
            _authenticated_current: authenticated_current,
            _preflight_plan: preflight_plan,
            _candidate_uniqueness: candidate_uniqueness,
            _object_verification: object_verification,
            _verified_genesis: verified_genesis,
            _seal_framing: seal_framing,
            _global_owner_lock: global_owner_lock,
        })
    }
}

impl NativeCurrentSealFramingAuthenticatedOwner {
    pub(crate) fn preflight_authenticated_organism_structure(
        mut self,
    ) -> Result<NativeCurrentOrganismStructurallyPreflightedOwner, OwnerBootError> {
        // Keep the complete framing-authenticated owner intact throughout the
        // new rewind, streaming authentication, wire parse, and revalidation.
        let organism_structural_preflight = self
            ._seal_framing
            .preflight_authenticated_organism_structure(
                &self._global_owner_lock,
                self._platform.global_owner(),
                &self._verified_genesis,
                CurrentOrganismStructuralPreflightIngress { _private: () },
            )?;
        let Self {
            _platform: platform,
            _authenticated_current: authenticated_current,
            _preflight_plan: preflight_plan,
            _candidate_uniqueness: candidate_uniqueness,
            _object_verification: object_verification,
            _verified_genesis: verified_genesis,
            _seal_framing: seal_framing,
            _global_owner_lock: global_owner_lock,
        } = self;
        Ok(NativeCurrentOrganismStructurallyPreflightedOwner {
            _platform: platform,
            _authenticated_current: authenticated_current,
            _preflight_plan: preflight_plan,
            _candidate_uniqueness: candidate_uniqueness,
            _object_verification: object_verification,
            _verified_genesis: verified_genesis,
            _seal_framing: seal_framing,
            _organism_structural_preflight: organism_structural_preflight,
            _global_owner_lock: global_owner_lock,
        })
    }
}

impl NativeCurrentOrganismStructurallyPreflightedOwner {
    pub(crate) fn allocate_zeroed_organism_arena(
        self,
    ) -> Result<NativeCurrentOrganismArenaAllocatedOwner, OwnerBootError> {
        // Keep the complete structurally preflighted owner intact until the
        // before/map/page-touch/after window has succeeded. Any failure drops
        // the retained descriptor and proofs before releasing the lock.
        let allocation = self
            ._organism_structural_preflight
            .allocate_zeroed_organism_arena(
                self._platform.physical_mapping_window_observer(),
                CurrentOrganismArenaAllocationIngress { _private: () },
            )?;
        let Self {
            _platform: platform,
            _authenticated_current: authenticated_current,
            _preflight_plan: preflight_plan,
            _candidate_uniqueness: candidate_uniqueness,
            _object_verification: object_verification,
            _verified_genesis: verified_genesis,
            _seal_framing: seal_framing,
            _organism_structural_preflight: organism_structural_preflight,
            _global_owner_lock: global_owner_lock,
        } = self;
        Ok(NativeCurrentOrganismArenaAllocatedOwner {
            _platform: platform,
            _authenticated_current: authenticated_current,
            _preflight_plan: preflight_plan,
            _candidate_uniqueness: candidate_uniqueness,
            _object_verification: object_verification,
            _verified_genesis: verified_genesis,
            _seal_framing: seal_framing,
            _organism_structural_preflight: organism_structural_preflight,
            _organism_arena: allocation.arena,
            _organism_arena_observation: allocation.observation,
            _global_owner_lock: global_owner_lock,
        })
    }
}

impl NativeCurrentOrganismArenaAllocatedOwner {
    pub(crate) fn stream_populate_and_validate(
        mut self,
    ) -> Result<NativeCurrentOrganismArenaPopulatedOwner, NativeCurrentOrganismArenaPopulationFailure>
    {
        let population = match self
            ._seal_framing
            .stream_populate_and_validate_organism_arena(
                self._authenticated_current.bytes(),
                self._preflight_plan,
                &self._candidate_uniqueness,
                self._organism_structural_preflight,
                &mut self._organism_arena,
                &self._global_owner_lock,
                self._platform.global_owner(),
                &self._verified_genesis,
            ) {
            Ok(population) => population,
            Err(error) => {
                return Err(NativeCurrentOrganismArenaPopulationFailure {
                    error: error.into(),
                    owner: self,
                });
            }
        };
        let Self {
            _platform: platform,
            _authenticated_current: authenticated_current,
            _preflight_plan: preflight_plan,
            _candidate_uniqueness: candidate_uniqueness,
            _object_verification: object_verification,
            _verified_genesis: verified_genesis,
            _seal_framing: seal_framing,
            _organism_structural_preflight: organism_structural_preflight,
            _organism_arena: organism_arena,
            _organism_arena_observation: organism_arena_observation,
            _global_owner_lock: global_owner_lock,
        } = self;
        Ok(NativeCurrentOrganismArenaPopulatedOwner {
            _platform: platform,
            _authenticated_current: authenticated_current,
            _preflight_plan: preflight_plan,
            _candidate_uniqueness: candidate_uniqueness,
            _object_verification: object_verification,
            _verified_genesis: verified_genesis,
            _seal_framing: seal_framing,
            _organism_structural_preflight: organism_structural_preflight,
            _organism_arena: organism_arena,
            _organism_arena_population: population,
            _organism_arena_observation: organism_arena_observation,
            _global_owner_lock: global_owner_lock,
        })
    }
}

impl NativeOwnerBootBundle {
    pub(crate) fn take_from_environment() -> Result<Self, OwnerBootError> {
        if BOOT_BUNDLE_TAKEN
            .compare_exchange(false, true, Ordering::SeqCst, Ordering::SeqCst)
            .is_err()
        {
            return Err(OwnerBootError::AlreadyConsumed);
        }
        // Safety: this is the PID1 boot boundary and must run before any thread
        // or service is created. It copies exactly one value, overwrites every
        // matching C-environment value in place, and then removes all entries.
        let encoded = unsafe { take_and_scrub_c_environment_bundle()? };
        if std::str::from_utf8(encoded.as_slice()).is_err() {
            return Err(OwnerBootError::NonUnicodeBundle);
        }
        decode_bundle(encoded)
    }

    pub(crate) fn bind_native_platform_and_acquire_global_lock(
        self,
        observation: NativePlatformObservation,
    ) -> Result<NativeGlobalOwnerBoot, OwnerBootError> {
        let platform = observation
            .authenticate_envelope(&self.platform_envelope, self.global_owner)
            .map_err(OwnerBootError::Platform)?;
        let global_owner_lock =
            NativeGlobalOwnerLock::acquire_production(platform.authority_directory())?;
        Ok(NativeGlobalOwnerBoot {
            _platform: platform,
            _global_owner_lock: global_owner_lock,
        })
    }
}

fn decode_bundle(encoded: Zeroizing<Vec<u8>>) -> Result<NativeOwnerBootBundle, OwnerBootError> {
    if encoded.len() != BOOT_HEX_BYTES {
        return Err(OwnerBootError::WrongHexLength);
    }
    let mut record = Zeroizing::new(vec![0_u8; BOOT_RECORD_BYTES]);
    for (index, output) in record.iter_mut().enumerate() {
        let high = lowercase_nibble(encoded[index * 2])?;
        let low = lowercase_nibble(encoded[index * 2 + 1])?;
        *output = (high << 4) | low;
    }
    if record.get(..8) != Some(BOOT_MAGIC.as_slice()) {
        return Err(OwnerBootError::BadMagic);
    }
    if u16::from_le_bytes(record[8..10].try_into().expect("fixed boot version")) != BOOT_VERSION {
        return Err(OwnerBootError::UnsupportedVersion);
    }
    if u16::from_le_bytes(record[10..12].try_into().expect("fixed boot flags")) != BOOT_FLAGS {
        return Err(OwnerBootError::WrongFlags);
    }
    if u32::from_le_bytes(record[12..16].try_into().expect("fixed boot length")) as usize
        != BOOT_PAYLOAD_BYTES
    {
        return Err(OwnerBootError::PayloadLengthMismatch);
    }
    let epoch = u32::from_le_bytes(record[16..20].try_into().expect("fixed owner epoch"));
    let mut root = Zeroizing::new([0_u8; 32]);
    root.copy_from_slice(&record[20..52]);
    let platform_envelope = record[52..].try_into().expect("fixed platform envelope");
    Ok(NativeOwnerBootBundle {
        global_owner: SuppliedGlobalOwnerRootKey::from_owner_boot(
            epoch,
            root,
            OwnerBootRootIngress { _private: () },
        )?,
        platform_envelope,
    })
}

extern "C" {
    static mut environ: *mut *mut libc::c_char;
}

/// Read and erase the process-start environment storage before `unsetenv`
/// drops its pointers. Linux bounds that storage through the successful
/// `execve` argument/environment envelope; this function allocates only after
/// observing the one exact canonical record length.
unsafe fn take_and_scrub_c_environment_bundle() -> Result<Zeroizing<Vec<u8>>, OwnerBootError> {
    let name = BOOT_ENVIRONMENT_NAME.as_bytes();
    let mut cursor = environ;
    let mut matches = 0_u32;
    let mut encoded: Option<Zeroizing<Vec<u8>>> = None;
    let mut wrong_length = false;

    if !cursor.is_null() {
        while !(*cursor).is_null() {
            let entry = *cursor as *mut u8;
            let entry_length = libc::strlen(entry.cast()) as usize;
            let entry_bytes = std::slice::from_raw_parts(entry, entry_length);
            if entry_length > name.len()
                && entry_bytes.get(..name.len()) == Some(name)
                && entry_bytes[name.len()] == b'='
            {
                matches = matches.saturating_add(1);
                let value = entry.add(name.len() + 1);
                let value_length = entry_length - name.len() - 1;
                if matches == 1 {
                    if value_length == BOOT_HEX_BYTES {
                        encoded = Some(Zeroizing::new(
                            std::slice::from_raw_parts(value, value_length).to_vec(),
                        ));
                    } else {
                        wrong_length = true;
                    }
                }
                for index in 0..value_length {
                    value.add(index).write_volatile(0);
                }
            }
            cursor = cursor.add(1);
        }
    }
    std::sync::atomic::compiler_fence(Ordering::SeqCst);
    if libc::unsetenv(BOOT_ENVIRONMENT_C_NAME.as_ptr().cast()) != 0 {
        return Err(OwnerBootError::EnvironmentRemovalFailed);
    }
    match matches {
        0 => Err(OwnerBootError::MissingBundle),
        1 if wrong_length => Err(OwnerBootError::WrongHexLength),
        1 => encoded.ok_or(OwnerBootError::WrongHexLength),
        _ => Err(OwnerBootError::DuplicateBundle),
    }
}

fn lowercase_nibble(value: u8) -> Result<u8, OwnerBootError> {
    match value {
        b'0'..=b'9' => Ok(value - b'0'),
        b'a'..=b'f' => Ok(value - b'a' + 10),
        _ => Err(OwnerBootError::NoncanonicalHex),
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::organism::generation_store::CurrentObjectRole;

    #[test]
    fn current_mapping_transition_consumes_the_global_owner_boot() {
        let transition: fn(
            NativeGlobalOwnerBoot,
        ) -> Result<NativeCurrentMappedOwner, OwnerBootError> =
            NativeGlobalOwnerBoot::map_unverified_current;
        let _ = transition;
    }

    #[test]
    fn current_authentication_transition_consumes_the_mapped_owner() {
        let transition: fn(
            NativeCurrentMappedOwner,
        ) -> Result<NativeCurrentAuthenticatedOwner, OwnerBootError> =
            NativeCurrentMappedOwner::authenticate_current_v2;
        let _ = transition;
    }

    #[test]
    fn current_preflight_transition_consumes_the_authenticated_owner() {
        let transition: fn(
            NativeCurrentAuthenticatedOwner,
        ) -> Result<NativeCurrentPreflightOwner, OwnerBootError> =
            NativeCurrentAuthenticatedOwner::preflight_current_framing;
        let _ = transition;
    }

    #[test]
    fn candidate_uniqueness_transition_consumes_the_preflight_owner() {
        let transition: fn(
            NativeCurrentPreflightOwner,
        ) -> Result<NativeCurrentCandidateUniqueOwner, OwnerBootError> =
            NativeCurrentPreflightOwner::verify_candidate_uniqueness;
        let _ = transition;
    }

    #[test]
    fn object_verification_transition_consumes_the_candidate_unique_owner() {
        let transition: fn(
            NativeCurrentCandidateUniqueOwner,
        )
            -> Result<NativeCurrentObjectReferencesVerifiedOwner, OwnerBootError> =
            NativeCurrentCandidateUniqueOwner::verify_current_object_references;
        let _ = transition;
    }

    #[test]
    fn genesis_verification_transition_consumes_the_reference_verified_owner() {
        let transition: fn(
            NativeCurrentObjectReferencesVerifiedOwner,
        ) -> Result<NativeCurrentGenesisVerifiedOwner, OwnerBootError> =
            NativeCurrentObjectReferencesVerifiedOwner::verify_current_genesis;
        let _ = transition;
    }

    #[test]
    fn seal_framing_transition_consumes_the_genesis_verified_owner() {
        let transition: fn(
            NativeCurrentGenesisVerifiedOwner,
        )
            -> Result<NativeCurrentSealFramingAuthenticatedOwner, OwnerBootError> =
            NativeCurrentGenesisVerifiedOwner::authenticate_current_seal_framing;
        let _ = transition;
    }

    #[test]
    fn organism_structural_preflight_transition_consumes_the_framing_owner() {
        let transition: fn(
            NativeCurrentSealFramingAuthenticatedOwner,
        ) -> Result<
            NativeCurrentOrganismStructurallyPreflightedOwner,
            OwnerBootError,
        > = NativeCurrentSealFramingAuthenticatedOwner::preflight_authenticated_organism_structure;
        let _ = transition;
    }

    #[test]
    fn organism_arena_allocation_transition_consumes_the_preflighted_owner() {
        let transition: fn(
            NativeCurrentOrganismStructurallyPreflightedOwner,
        )
            -> Result<NativeCurrentOrganismArenaAllocatedOwner, OwnerBootError> =
            NativeCurrentOrganismStructurallyPreflightedOwner::allocate_zeroed_organism_arena;
        let _ = transition;
    }

    #[test]
    fn organism_population_transition_returns_the_live_owner_on_failure() {
        let transition: fn(
            NativeCurrentOrganismArenaAllocatedOwner,
        ) -> Result<
            NativeCurrentOrganismArenaPopulatedOwner,
            NativeCurrentOrganismArenaPopulationFailure,
        > = NativeCurrentOrganismArenaAllocatedOwner::stream_populate_and_validate;
        let recover: fn(
            NativeCurrentOrganismArenaPopulationFailure,
        ) -> NativeCurrentOrganismArenaAllocatedOwner =
            NativeCurrentOrganismArenaPopulationFailure::into_owner;
        let evidence: fn(&NativeCurrentOrganismArenaPopulationFailure) -> &OwnerBootError =
            NativeCurrentOrganismArenaPopulationFailure::error;
        let _ = (transition, recover, evidence);
    }

    #[test]
    fn candidate_uniqueness_error_is_structurally_wrapped() {
        let error = OwnerBootError::from(CandidateUniquenessError::DuplicateCandidateDigests {
            first_ordinal: 2,
            second_ordinal: 7,
        });
        assert_eq!(
            error,
            OwnerBootError::CandidateUniqueness(
                CandidateUniquenessError::DuplicateCandidateDigests {
                    first_ordinal: 2,
                    second_ordinal: 7,
                }
            )
        );
        assert_eq!(
            error.to_string(),
            "CURRENT candidate uniqueness failed: candidate digests at original ordinals 2 and 7 are identical"
        );
    }

    #[test]
    fn object_verification_error_is_structurally_wrapped() {
        let error = OwnerBootError::from(CurrentObjectVerificationError::ObjectDigestMismatch {
            role: CurrentObjectRole::Candidate(4),
        });
        assert_eq!(
            error,
            OwnerBootError::CurrentObjectVerification(
                CurrentObjectVerificationError::ObjectDigestMismatch {
                    role: CurrentObjectRole::Candidate(4),
                }
            )
        );
        assert_eq!(
            error.to_string(),
            "CURRENT object reference verification failed: CURRENT-referenced candidate 4 digest differs"
        );
    }

    #[test]
    fn genesis_verification_error_is_structurally_wrapped() {
        let error = OwnerBootError::from(CurrentGenesisVerificationError::IdentityMismatch {
            role: CurrentObjectRole::Genesis,
            phase: "after global-owner genesis authentication",
        });
        assert!(matches!(
            error,
            OwnerBootError::CurrentGenesisVerification(
                CurrentGenesisVerificationError::IdentityMismatch {
                    role: CurrentObjectRole::Genesis,
                    phase: "after global-owner genesis authentication",
                }
            )
        ));
    }

    #[test]
    fn seal_framing_error_is_structurally_wrapped_without_semantic_overclaim() {
        let error =
            OwnerBootError::from(CurrentSealFramingAuthenticationError::PriorCanonicality {
                role: CurrentObjectRole::Organism,
                phase: "after authenticated CURRENT coordinate comparison",
                generation: 4,
            });
        assert!(matches!(
            error,
            OwnerBootError::CurrentSealFramingAuthentication(
                CurrentSealFramingAuthenticationError::PriorCanonicality {
                    role: CurrentObjectRole::Organism,
                    phase: "after authenticated CURRENT coordinate comparison",
                    generation: 4,
                }
            )
        ));
        assert_eq!(
            error.to_string(),
            "CURRENT-pinned seal framing authentication failed: CURRENT-referenced organism prior receipts are noncanonical for generation 4 after authenticated CURRENT coordinate comparison"
        );
    }

    #[test]
    fn organism_structural_preflight_error_is_wrapped_without_decoded_authority() {
        let error = OwnerBootError::from(CurrentOrganismStructuralPreflightError::WireFraming {
            phase: "while reading wake tag",
            reason: "wake tag is unknown",
        });
        assert!(matches!(
            error,
            OwnerBootError::CurrentOrganismStructuralPreflight(
                CurrentOrganismStructuralPreflightError::WireFraming {
                    phase: "while reading wake tag",
                    reason: "wake tag is unknown",
                }
            )
        ));
        assert_eq!(
            error.to_string(),
            "CURRENT-pinned organism structural preflight failed: organism canonical schema header or wire framing failed while reading wake tag: wake tag is unknown"
        );
    }

    #[test]
    fn organism_arena_allocation_error_is_wrapped_without_semantic_authority() {
        let error = OwnerBootError::from(CurrentOrganismArenaAllocationError::PreObservation(
            crate::organism::platform_observer::PlatformObserverError::CgroupEvidence(
                "requested mapping length is zero",
            ),
        ));
        assert!(matches!(
            error,
            OwnerBootError::CurrentOrganismArenaAllocation(
                CurrentOrganismArenaAllocationError::PreObservation(
                    crate::organism::platform_observer::PlatformObserverError::CgroupEvidence(
                        "requested mapping length is zero"
                    )
                )
            )
        ));
        assert_eq!(
            error.to_string(),
            "CURRENT-pinned organism arena allocation failed: organism arena pre-allocation observation failed: invalid cgroup evidence: requested mapping length is zero"
        );
    }

    #[test]
    fn current_preflight_error_is_wrapped_without_semantic_overclaim() {
        let error = OwnerBootError::from(CurrentPreflightError::ZeroCandidateCount);
        assert_eq!(
            error,
            OwnerBootError::CurrentPreflight(CurrentPreflightError::ZeroCandidateCount)
        );
        assert_eq!(
            error.to_string(),
            "authenticated CURRENT framing preflight failed: authenticated CURRENT candidate count is zero"
        );
    }

    fn secret(value: String) -> Zeroizing<Vec<u8>> {
        Zeroizing::new(value.into_bytes())
    }

    fn encoded(
        epoch: u32,
        root: [u8; 32],
        envelope: [u8; PLATFORM_ENVELOPE_RECORD_BYTES],
    ) -> String {
        let mut record = vec![0_u8; BOOT_RECORD_BYTES];
        record[..8].copy_from_slice(BOOT_MAGIC);
        record[8..10].copy_from_slice(&BOOT_VERSION.to_le_bytes());
        record[10..12].copy_from_slice(&BOOT_FLAGS.to_le_bytes());
        record[12..16].copy_from_slice(&(BOOT_PAYLOAD_BYTES as u32).to_le_bytes());
        record[16..20].copy_from_slice(&epoch.to_le_bytes());
        record[20..52].copy_from_slice(&root);
        record[52..].copy_from_slice(&envelope);
        let mut output = String::with_capacity(BOOT_HEX_BYTES);
        for byte in record {
            output.push(char::from_digit(u32::from(byte >> 4), 16).unwrap());
            output.push(char::from_digit(u32::from(byte & 0x0f), 16).unwrap());
        }
        output
    }

    #[test]
    fn exact_fixed_bundle_decodes_without_exposing_root() {
        let envelope = [0x55; PLATFORM_ENVELOPE_RECORD_BYTES];
        let bundle = decode_bundle(secret(encoded(7, [0x91; 32], envelope))).unwrap();
        assert_eq!(bundle.global_owner.epoch(), 7);
        assert_eq!(bundle.platform_envelope, envelope);
    }

    #[test]
    fn every_header_and_owner_boundary_fails_closed() {
        let valid = encoded(7, [0x91; 32], [0x55; PLATFORM_ENVELOPE_RECORD_BYTES]);
        assert_eq!(
            decode_bundle(secret(valid[..valid.len() - 2].to_owned()))
                .err()
                .unwrap(),
            OwnerBootError::WrongHexLength
        );
        let mut uppercase = valid.clone();
        uppercase.replace_range(0..1, "A");
        assert_eq!(
            decode_bundle(secret(uppercase)).err().unwrap(),
            OwnerBootError::NoncanonicalHex
        );
        for (byte_offset, expected) in [
            (0, OwnerBootError::BadMagic),
            (8, OwnerBootError::UnsupportedVersion),
            (10, OwnerBootError::WrongFlags),
            (12, OwnerBootError::PayloadLengthMismatch),
        ] {
            let mut mutation = valid.clone();
            mutation.replace_range(byte_offset * 2..byte_offset * 2 + 2, "ff");
            assert_eq!(decode_bundle(secret(mutation)).err().unwrap(), expected);
        }
        assert!(matches!(
            decode_bundle(secret(encoded(
                0,
                [0x91; 32],
                [0x55; PLATFORM_ENVELOPE_RECORD_BYTES]
            ))),
            Err(OwnerBootError::GlobalOwner(_))
        ));
        assert!(matches!(
            decode_bundle(secret(encoded(
                7,
                [0; 32],
                [0x55; PLATFORM_ENVELOPE_RECORD_BYTES]
            ))),
            Err(OwnerBootError::GlobalOwner(_))
        ));
    }
}
