//! Native custody sealing for structurally canonical organism bytes.
//!
//! A successful verification proves exact byte custody, identity/generation
//! continuity, and HMAC possession only. It does not verify native field-bank
//! contents or assign meaning to receipt-shaped fields.

use super::{
    decode_structure, generation_store::AuthenticatedCurrentSealCoordinates,
    genesis::VerifiedGenesisIdentity, wake_admission::SuppliedGlobalOwnerRootKey, CodecError,
    DecodeBudget, OrganismState,
};
use hmac::{Hmac, Mac};
use sha2::{Digest, Sha256};
use std::{collections::HashSet, fmt};
use zeroize::Zeroizing;

type HmacSha256 = Hmac<Sha256>;

pub(crate) const MAGIC: &[u8; 8] = b"GULSEAL2";
pub(crate) const VERSION: u16 = 2;
const DOMAIN: &[u8] = b"guala.native.organism-state-seal.v2\0";
const CAPABILITY_BINDING_DOMAIN: &[u8] = b"guala.native.organism-seal.capability-binding.v2\0";
const ZERO_RECEIPT: [u8; 32] = [0; 32];
pub(crate) const BANK_BINDING_BYTES: usize = 96;
pub(crate) const TAG_BYTES: usize = 32;
pub(crate) const FIXED_HEADER_BYTES: usize = 142;
const FIXED_ENVELOPE_BYTES: usize = FIXED_HEADER_BYTES + 8 + TAG_BYTES;

/// Owns and zeroizes its internal key copy on drop. The by-value array input is
/// Copy, so this cannot erase copies retained by the caller; the caller remains
/// responsible for zeroizing every source copy it keeps.
pub(crate) struct SealKey {
    epoch: u32,
    bytes: Zeroizing<[u8; 32]>,
}

impl SealKey {
    #[cfg(test)]
    pub(crate) fn new(epoch: u32, bytes: [u8; 32]) -> Result<Self, SealError> {
        Self::from_zeroizing(epoch, Zeroizing::new(bytes))
    }

    fn from_zeroizing(epoch: u32, bytes: Zeroizing<[u8; 32]>) -> Result<Self, SealError> {
        if epoch == 0 {
            return Err(SealError::Noncanonical("seal key epoch is zero"));
        }
        if *bytes == [0; 32] {
            return Err(SealError::Noncanonical("seal key bytes are all zero"));
        }
        Ok(Self { epoch, bytes })
    }

    pub(crate) fn epoch(&self) -> u32 {
        self.epoch
    }
}

/// Allocation-free streaming authentication authority for one seal envelope.
/// Construction proves that the supplied genesis identity belongs to the same
/// global owner. Seal key bytes remain private to this module.
pub(crate) struct GlobalOwnerSealStreamVerifier {
    key_epoch: u32,
    mac: HmacSha256,
}

impl GlobalOwnerSealStreamVerifier {
    pub(crate) fn begin(
        global_owner: &SuppliedGlobalOwnerRootKey,
        verified_genesis: &VerifiedGenesisIdentity,
    ) -> Result<Self, SealError> {
        if !verified_genesis.is_bound_to_global_owner(global_owner) {
            return Err(SealError::AuthorityMismatch);
        }
        let key = SealKey::from_zeroizing(
            global_owner.epoch(),
            global_owner.derive_organism_seal_key(),
        )?;
        let mut mac =
            HmacSha256::new_from_slice(key.bytes.as_ref()).map_err(|_| SealError::HmacFailed)?;
        mac.update(DOMAIN);
        Ok(Self {
            key_epoch: key.epoch,
            mac,
        })
    }

    pub(crate) fn key_epoch(&self) -> u32 {
        self.key_epoch
    }

    pub(crate) fn update(&mut self, authenticated_bytes: &[u8]) {
        self.mac.update(authenticated_bytes);
    }

    pub(crate) fn verify_tag(self, tag: &[u8; TAG_BYTES]) -> Result<(), SealError> {
        self.mac
            .verify_slice(tag)
            .map_err(|_| SealError::HmacFailed)
    }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) struct CanonicalBankBinding {
    pub(crate) candidate_receipt: [u8; 32],
    pub(crate) bank_receipt: [u8; 32],
    pub(crate) kernel_config_receipt: [u8; 32],
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) struct SealEncodeBudget {
    pub(crate) max_organism_bytes: u64,
    pub(crate) max_output_bytes: u64,
    pub(crate) max_bank_bindings: u64,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) struct SealDecodeBudget {
    pub(crate) max_input_bytes: u64,
    pub(crate) max_organism_bytes: u64,
    pub(crate) max_decoded_heap_bytes: u64,
    pub(crate) max_bank_bindings: u64,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) enum SealError {
    InputBudgetExceeded,
    OutputBudgetExceeded,
    OrganismBudgetExceeded,
    BankBindingBudgetExceeded,
    LengthOverflow,
    AllocationFailed,
    UnexpectedEnd,
    BadMagic,
    UnsupportedVersion(u16),
    KeyEpochMismatch,
    TrustedHeadMismatch,
    HmacFailed,
    TrailingBytes,
    StateDigestMismatch,
    EnvelopeStateMismatch,
    GenesisMismatch,
    SuccessorMismatch,
    CurrentCheckpointMismatch,
    AuthorityMismatch,
    Noncanonical(&'static str),
    Organism(CodecError),
}

impl fmt::Display for SealError {
    fn fmt(&self, output: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::InputBudgetExceeded => write!(output, "seal input budget exceeded"),
            Self::OutputBudgetExceeded => write!(output, "seal output budget exceeded"),
            Self::OrganismBudgetExceeded => write!(output, "sealed organism budget exceeded"),
            Self::BankBindingBudgetExceeded => write!(output, "bank-binding budget exceeded"),
            Self::LengthOverflow => write!(output, "seal length overflow"),
            Self::AllocationFailed => write!(output, "seal allocation failed"),
            Self::UnexpectedEnd => write!(output, "seal ended unexpectedly"),
            Self::BadMagic => write!(output, "seal magic differs"),
            Self::UnsupportedVersion(version) => {
                write!(output, "unsupported seal version {version}")
            }
            Self::KeyEpochMismatch => write!(output, "seal key epoch differs"),
            Self::TrustedHeadMismatch => write!(output, "seal differs from trusted head"),
            Self::HmacFailed => write!(output, "seal HMAC differs"),
            Self::TrailingBytes => write!(output, "seal contains trailing bytes"),
            Self::StateDigestMismatch => write!(output, "organism-state digest differs"),
            Self::EnvelopeStateMismatch => {
                write!(output, "seal header differs from organism state")
            }
            Self::GenesisMismatch => write!(output, "seal is not the expected genesis"),
            Self::SuccessorMismatch => write!(output, "seal is not the exact successor"),
            Self::CurrentCheckpointMismatch => {
                write!(
                    output,
                    "seal is not the exact root-pinned current checkpoint"
                )
            }
            Self::AuthorityMismatch => write!(output, "seal authority differs"),
            Self::Noncanonical(reason) => write!(output, "noncanonical seal: {reason}"),
            Self::Organism(error) => write!(output, "sealed organism structure failed: {error}"),
        }
    }
}

impl std::error::Error for SealError {}

impl From<CodecError> for SealError {
    fn from(value: CodecError) -> Self {
        Self::Organism(value)
    }
}

/// Exact custody proof only. Field-bank semantics and receipt meanings remain
/// unverified and require their own later boundaries.
pub(crate) struct CustodyVerifiedSeal {
    state: OrganismState,
    organism_state_receipt: [u8; 32],
    seal_receipt: [u8; 32],
    key_epoch: u32,
    prior_seal_receipt: [u8; 32],
    bank_bindings: Vec<CanonicalBankBinding>,
    authority_binding: [u8; 32],
}

impl CustodyVerifiedSeal {
    pub(crate) fn state(&self) -> &OrganismState {
        &self.state
    }

    pub(crate) fn organism_state_receipt(&self) -> [u8; 32] {
        self.organism_state_receipt
    }

    pub(crate) fn seal_receipt(&self) -> [u8; 32] {
        self.seal_receipt
    }

    pub(crate) fn key_epoch(&self) -> u32 {
        self.key_epoch
    }

    pub(crate) fn prior_seal_receipt(&self) -> [u8; 32] {
        self.prior_seal_receipt
    }

    pub(crate) fn bank_bindings(&self) -> &[CanonicalBankBinding] {
        &self.bank_bindings
    }

    fn is_bound_to(&self, key: &SealKey) -> bool {
        verify_capability_binding(key, self.seal_receipt, &self.authority_binding)
    }
}

pub(crate) fn seal_genesis(
    state: &OrganismState,
    key: &SealKey,
    bank_bindings: &[CanonicalBankBinding],
    budget: SealEncodeBudget,
) -> Result<Vec<u8>, SealError> {
    if state.generation != 0 || state.prior_state_receipt != ZERO_RECEIPT {
        return Err(SealError::GenesisMismatch);
    }
    encode_seal(state, key, ZERO_RECEIPT, bank_bindings, budget)
}

pub(crate) fn seal_global_owner_genesis(
    state: &OrganismState,
    global_owner: &SuppliedGlobalOwnerRootKey,
    bank_bindings: &[CanonicalBankBinding],
    budget: SealEncodeBudget,
) -> Result<Vec<u8>, SealError> {
    let key = SealKey::from_zeroizing(
        global_owner.epoch(),
        global_owner.derive_organism_seal_key(),
    )?;
    seal_genesis(state, &key, bank_bindings, budget)
}

pub(crate) fn seal_successor(
    state: &OrganismState,
    key: &SealKey,
    prior: &CustodyVerifiedSeal,
    bank_bindings: &[CanonicalBankBinding],
    budget: SealEncodeBudget,
) -> Result<Vec<u8>, SealError> {
    if !prior.is_bound_to(key) {
        return Err(SealError::AuthorityMismatch);
    }
    let expected_generation = prior
        .state
        .generation
        .checked_add(1)
        .ok_or(SealError::SuccessorMismatch)?;
    if state.identity != prior.state.identity
        || state.generation != expected_generation
        || state.prior_state_receipt != prior.organism_state_receipt
    {
        return Err(SealError::SuccessorMismatch);
    }
    encode_seal(state, key, prior.seal_receipt, bank_bindings, budget)
}

pub(crate) fn seal_global_owner_successor(
    state: &OrganismState,
    global_owner: &SuppliedGlobalOwnerRootKey,
    prior: &CustodyVerifiedSeal,
    bank_bindings: &[CanonicalBankBinding],
    budget: SealEncodeBudget,
) -> Result<Vec<u8>, SealError> {
    let key = SealKey::from_zeroizing(
        global_owner.epoch(),
        global_owner.derive_organism_seal_key(),
    )?;
    seal_successor(state, &key, prior, bank_bindings, budget)
}

/// Private primitive used by the continuity constructors. Tests also use it to
/// manufacture authenticated discontinuities and prove verification fails closed.
fn encode_seal(
    state: &OrganismState,
    key: &SealKey,
    prior_seal_receipt: [u8; 32],
    bank_bindings: &[CanonicalBankBinding],
    budget: SealEncodeBudget,
) -> Result<Vec<u8>, SealError> {
    enforce_count_budget(bank_bindings.len(), budget.max_bank_bindings)
        .map_err(|_| SealError::BankBindingBudgetExceeded)?;
    validate_bank_bindings(bank_bindings)?;
    validate_unique_candidates(bank_bindings)?;
    validate_generation_priors(state, prior_seal_receipt)?;
    validate_bank_coverage(state, bank_bindings)?;

    let organism_bytes = state.encode_unverified(budget.max_organism_bytes)?;
    let organism_len = u64_len(organism_bytes.len())?;
    if organism_len > budget.max_organism_bytes {
        return Err(SealError::OrganismBudgetExceeded);
    }
    let organism_state_receipt = digest(&organism_bytes);
    let total = encoded_length(organism_bytes.len(), bank_bindings.len())?;
    if u64_len(total)? > budget.max_output_bytes {
        return Err(SealError::OutputBudgetExceeded);
    }

    let mut output = Vec::new();
    output
        .try_reserve_exact(total)
        .map_err(|_| SealError::AllocationFailed)?;
    output.extend_from_slice(MAGIC);
    output.extend_from_slice(&VERSION.to_le_bytes());
    output.extend_from_slice(&key.epoch.to_le_bytes());
    output.extend_from_slice(&state.identity);
    output.extend_from_slice(&state.generation.to_le_bytes());
    output.extend_from_slice(&state.prior_state_receipt);
    output.extend_from_slice(&prior_seal_receipt);
    output.extend_from_slice(&organism_state_receipt);
    output.extend_from_slice(&u64_len(bank_bindings.len())?.to_le_bytes());
    for binding in bank_bindings {
        output.extend_from_slice(&binding.candidate_receipt);
        output.extend_from_slice(&binding.bank_receipt);
        output.extend_from_slice(&binding.kernel_config_receipt);
    }
    output.extend_from_slice(&organism_len.to_le_bytes());
    output.extend_from_slice(&organism_bytes);
    let tag = hmac_tag(key, &output)?;
    output.extend_from_slice(&tag);
    debug_assert_eq!(output.len(), total);
    Ok(output)
}

pub(crate) fn verify_genesis(
    envelope: &[u8],
    key: &SealKey,
    expected_trusted_head: [u8; 32],
    expected_identity: &VerifiedGenesisIdentity,
    budget: SealDecodeBudget,
) -> Result<CustodyVerifiedSeal, SealError> {
    let verified = verify_custody(envelope, key, expected_trusted_head, budget)?;
    if verified.state.identity != expected_identity.identity_bytes()
        || verified.state.generation != 0
        || verified.state.prior_state_receipt != ZERO_RECEIPT
        || verified.prior_seal_receipt != ZERO_RECEIPT
    {
        return Err(SealError::GenesisMismatch);
    }
    Ok(verified)
}

pub(crate) fn verify_global_owner_genesis_seal(
    envelope: &[u8],
    global_owner: &SuppliedGlobalOwnerRootKey,
    expected_trusted_head: [u8; 32],
    expected_identity: &VerifiedGenesisIdentity,
    budget: SealDecodeBudget,
) -> Result<CustodyVerifiedSeal, SealError> {
    if !expected_identity.is_bound_to_global_owner(global_owner) {
        return Err(SealError::AuthorityMismatch);
    }
    let key = SealKey::from_zeroizing(
        global_owner.epoch(),
        global_owner.derive_organism_seal_key(),
    )?;
    verify_genesis(
        envelope,
        &key,
        expected_trusted_head,
        expected_identity,
        budget,
    )
}

pub(crate) fn verify_successor(
    envelope: &[u8],
    key: &SealKey,
    expected_trusted_head: [u8; 32],
    prior: &CustodyVerifiedSeal,
    budget: SealDecodeBudget,
) -> Result<CustodyVerifiedSeal, SealError> {
    if !prior.is_bound_to(key) {
        return Err(SealError::AuthorityMismatch);
    }
    let verified = verify_custody(envelope, key, expected_trusted_head, budget)?;
    let expected_generation = prior
        .state
        .generation
        .checked_add(1)
        .ok_or(SealError::SuccessorMismatch)?;
    if verified.state.identity != prior.state.identity
        || verified.state.generation != expected_generation
        || verified.state.prior_state_receipt != prior.organism_state_receipt
        || verified.prior_seal_receipt != prior.seal_receipt
    {
        return Err(SealError::SuccessorMismatch);
    }
    Ok(verified)
}

pub(crate) fn verify_global_owner_successor(
    envelope: &[u8],
    global_owner: &SuppliedGlobalOwnerRootKey,
    expected_trusted_head: [u8; 32],
    prior: &CustodyVerifiedSeal,
    budget: SealDecodeBudget,
) -> Result<CustodyVerifiedSeal, SealError> {
    let key = SealKey::from_zeroizing(
        global_owner.epoch(),
        global_owner.derive_organism_seal_key(),
    )?;
    verify_successor(envelope, &key, expected_trusted_head, prior, budget)
}

/// Verifies the one seal named by an authenticated CURRENT record under the
/// same global root as the verified genesis identity. This proves the exact
/// root-pinned checkpoint; it deliberately does not claim that absent prior
/// seal objects form a verified historical chain.
pub(crate) fn verify_global_owner_current_checkpoint(
    envelope: &[u8],
    global_owner: &SuppliedGlobalOwnerRootKey,
    current: &AuthenticatedCurrentSealCoordinates<'_>,
    expected_identity: &VerifiedGenesisIdentity,
    budget: SealDecodeBudget,
) -> Result<CustodyVerifiedSeal, SealError> {
    if !expected_identity.is_bound_to_global_owner(global_owner) {
        return Err(SealError::AuthorityMismatch);
    }
    let key = SealKey::from_zeroizing(
        global_owner.epoch(),
        global_owner.derive_organism_seal_key(),
    )?;
    let verified = verify_custody(envelope, &key, current.seal_receipt(), budget)?;
    let priors_are_canonical = if current.generation() == 0 {
        verified.state.prior_state_receipt == ZERO_RECEIPT
            && verified.prior_seal_receipt == ZERO_RECEIPT
    } else {
        verified.state.prior_state_receipt != ZERO_RECEIPT
            && verified.prior_seal_receipt != ZERO_RECEIPT
    };
    if current.identity() != expected_identity.identity_bytes()
        || verified.state.identity != current.identity()
        || verified.state.generation != current.generation()
        || verified.organism_state_receipt != current.organism_state_receipt()
        || !priors_are_canonical
    {
        return Err(SealError::CurrentCheckpointMismatch);
    }
    Ok(verified)
}

struct ParsedEnvelope<'a> {
    key_epoch: u32,
    identity: [u8; 16],
    generation: u64,
    prior_state_receipt: [u8; 32],
    prior_seal_receipt: [u8; 32],
    organism_state_receipt: [u8; 32],
    bank_binding_bytes: &'a [u8],
    organism_bytes: &'a [u8],
    authenticated_bytes: &'a [u8],
    tag: &'a [u8],
}

fn verify_custody(
    envelope: &[u8],
    key: &SealKey,
    expected_trusted_head: [u8; 32],
    budget: SealDecodeBudget,
) -> Result<CustodyVerifiedSeal, SealError> {
    let input_len = u64_len(envelope.len())?;
    if input_len > budget.max_input_bytes {
        return Err(SealError::InputBudgetExceeded);
    }
    if digest(envelope) != expected_trusted_head {
        return Err(SealError::TrustedHeadMismatch);
    }
    let parsed = parse_envelope(envelope, key, budget)?;
    verify_hmac(key, parsed.authenticated_bytes, parsed.tag)?;
    validate_unique_candidate_bytes(parsed.bank_binding_bytes)?;
    if digest(parsed.organism_bytes) != parsed.organism_state_receipt {
        return Err(SealError::StateDigestMismatch);
    }

    let unverified = decode_structure(
        parsed.organism_bytes,
        DecodeBudget {
            max_input_bytes: budget.max_organism_bytes,
            max_heap_bytes: budget.max_decoded_heap_bytes,
        },
    )?;
    let state = unverified.state;
    if state.identity != parsed.identity
        || state.generation != parsed.generation
        || state.prior_state_receipt != parsed.prior_state_receipt
    {
        return Err(SealError::EnvelopeStateMismatch);
    }
    validate_bank_coverage_bytes(&state, parsed.bank_binding_bytes)?;

    let mut bank_bindings = Vec::new();
    bank_bindings
        .try_reserve_exact(parsed.bank_binding_bytes.len() / BANK_BINDING_BYTES)
        .map_err(|_| SealError::AllocationFailed)?;
    for bytes in parsed.bank_binding_bytes.chunks_exact(BANK_BINDING_BYTES) {
        bank_bindings.push(CanonicalBankBinding {
            candidate_receipt: array(&bytes[0..32]),
            bank_receipt: array(&bytes[32..64]),
            kernel_config_receipt: array(&bytes[64..96]),
        });
    }
    Ok(CustodyVerifiedSeal {
        state,
        organism_state_receipt: parsed.organism_state_receipt,
        seal_receipt: expected_trusted_head,
        key_epoch: parsed.key_epoch,
        prior_seal_receipt: parsed.prior_seal_receipt,
        bank_bindings,
        authority_binding: capability_binding(key, expected_trusted_head),
    })
}

fn capability_binding(key: &SealKey, seal_receipt: [u8; 32]) -> [u8; 32] {
    let mut binding = HmacSha256::new_from_slice(key.bytes.as_ref())
        .expect("HMAC-SHA256 accepts every 32-byte key");
    binding.update(CAPABILITY_BINDING_DOMAIN);
    binding.update(&key.epoch.to_le_bytes());
    binding.update(&seal_receipt);
    binding.finalize().into_bytes().into()
}

fn verify_capability_binding(key: &SealKey, seal_receipt: [u8; 32], binding: &[u8; 32]) -> bool {
    let mut verifier = HmacSha256::new_from_slice(key.bytes.as_ref())
        .expect("HMAC-SHA256 accepts every 32-byte key");
    verifier.update(CAPABILITY_BINDING_DOMAIN);
    verifier.update(&key.epoch.to_le_bytes());
    verifier.update(&seal_receipt);
    verifier.verify_slice(binding).is_ok()
}

fn parse_envelope<'a>(
    envelope: &'a [u8],
    key: &SealKey,
    budget: SealDecodeBudget,
) -> Result<ParsedEnvelope<'a>, SealError> {
    if envelope.len() < FIXED_ENVELOPE_BYTES {
        return Err(SealError::UnexpectedEnd);
    }
    let mut input = Cursor::new(envelope);
    if input.take(8)? != MAGIC {
        return Err(SealError::BadMagic);
    }
    let version = input.u16()?;
    if version != VERSION {
        return Err(SealError::UnsupportedVersion(version));
    }
    let key_epoch = input.u32()?;
    if key_epoch != key.epoch {
        return Err(SealError::KeyEpochMismatch);
    }
    let identity = input.fixed()?;
    let generation = input.u64()?;
    let prior_state_receipt = input.fixed()?;
    let prior_seal_receipt = input.fixed()?;
    let organism_state_receipt = input.fixed()?;

    let bank_count = input.u64()?;
    if bank_count > budget.max_bank_bindings {
        return Err(SealError::BankBindingBudgetExceeded);
    }
    let bank_count = usize::try_from(bank_count).map_err(|_| SealError::LengthOverflow)?;
    let bank_bytes_len = bank_count
        .checked_mul(BANK_BINDING_BYTES)
        .ok_or(SealError::LengthOverflow)?;
    let bank_binding_bytes = input.take(bank_bytes_len)?;
    validate_bank_binding_bytes(bank_binding_bytes)?;

    let organism_len = input.u64()?;
    if organism_len > budget.max_organism_bytes {
        return Err(SealError::OrganismBudgetExceeded);
    }
    let organism_len = usize::try_from(organism_len).map_err(|_| SealError::LengthOverflow)?;
    let organism_bytes = input.take(organism_len)?;
    let tag_offset = input.position;
    let tag = input.take(TAG_BYTES)?;
    if !input.finished() {
        return Err(SealError::TrailingBytes);
    }
    Ok(ParsedEnvelope {
        key_epoch,
        identity,
        generation,
        prior_state_receipt,
        prior_seal_receipt,
        organism_state_receipt,
        bank_binding_bytes,
        organism_bytes,
        authenticated_bytes: &envelope[..tag_offset],
        tag,
    })
}

fn validate_generation_priors(
    state: &OrganismState,
    prior_seal_receipt: [u8; 32],
) -> Result<(), SealError> {
    if state.generation == 0 {
        if state.prior_state_receipt != ZERO_RECEIPT || prior_seal_receipt != ZERO_RECEIPT {
            return Err(SealError::Noncanonical("genesis priors are not zero"));
        }
    } else if state.prior_state_receipt == ZERO_RECEIPT || prior_seal_receipt == ZERO_RECEIPT {
        return Err(SealError::Noncanonical("successor priors are zero"));
    }
    Ok(())
}

fn validate_bank_bindings(values: &[CanonicalBankBinding]) -> Result<(), SealError> {
    let mut prior: Option<([u8; 32], [u8; 32], [u8; 32])> = None;
    for value in values {
        let current = (
            value.bank_receipt,
            value.candidate_receipt,
            value.kernel_config_receipt,
        );
        if prior.is_some_and(|previous| previous >= current) {
            return Err(SealError::Noncanonical(
                "bank bindings are not strictly ordered by bank",
            ));
        }
        if prior.is_some_and(|previous| previous.0 == current.0) {
            return Err(SealError::Noncanonical(
                "bank receipt is mapped more than once",
            ));
        }
        prior = Some(current);
    }
    Ok(())
}

fn validate_bank_binding_bytes(bytes: &[u8]) -> Result<(), SealError> {
    let mut prior: Option<([u8; 32], [u8; 32], [u8; 32])> = None;
    for chunk in bytes.chunks_exact(BANK_BINDING_BYTES) {
        let current = (
            array::<32>(&chunk[32..64]),
            array::<32>(&chunk[0..32]),
            array::<32>(&chunk[64..96]),
        );
        if prior.is_some_and(|previous| previous >= current) {
            return Err(SealError::Noncanonical(
                "bank bindings are not strictly ordered by bank",
            ));
        }
        if prior.is_some_and(|previous| previous.0 == current.0) {
            return Err(SealError::Noncanonical(
                "bank receipt is mapped more than once",
            ));
        }
        prior = Some(current);
    }
    Ok(())
}

fn validate_unique_candidates(values: &[CanonicalBankBinding]) -> Result<(), SealError> {
    let mut candidates = HashSet::new();
    candidates
        .try_reserve(values.len())
        .map_err(|_| SealError::AllocationFailed)?;
    for value in values {
        if !candidates.insert(value.candidate_receipt) {
            return Err(SealError::Noncanonical(
                "candidate receipt is mapped more than once",
            ));
        }
    }
    Ok(())
}

fn validate_unique_candidate_bytes(bytes: &[u8]) -> Result<(), SealError> {
    let count = bytes.len() / BANK_BINDING_BYTES;
    let mut candidates = HashSet::new();
    candidates
        .try_reserve(count)
        .map_err(|_| SealError::AllocationFailed)?;
    for binding in bytes.chunks_exact(BANK_BINDING_BYTES) {
        if !candidates.insert(array::<32>(&binding[0..32])) {
            return Err(SealError::Noncanonical(
                "candidate receipt is mapped more than once",
            ));
        }
    }
    Ok(())
}

fn validate_bank_coverage(
    state: &OrganismState,
    bindings: &[CanonicalBankBinding],
) -> Result<(), SealError> {
    let authorities = &state.dsf_delivery_authorities;
    let mut authority_index = 0;
    let mut binding_index = 0;
    while authority_index < authorities.len() {
        let authority = &authorities[authority_index];
        let binding = bindings
            .get(binding_index)
            .ok_or(SealError::Noncanonical("DSF delivery has no bank binding"))?;
        if binding.bank_receipt != authority.field_bank_receipt
            || binding.kernel_config_receipt != authority.kernel_config_receipt
        {
            return Err(SealError::Noncanonical(
                "DSF bank binding differs from delivery authority",
            ));
        }

        let bank_receipt = authority.field_bank_receipt;
        let kernel_config_receipt = authority.kernel_config_receipt;
        authority_index += 1;
        while authority_index < authorities.len()
            && authorities[authority_index].field_bank_receipt == bank_receipt
        {
            if authorities[authority_index].kernel_config_receipt != kernel_config_receipt {
                return Err(SealError::Noncanonical(
                    "one bank receipt has multiple kernel configurations",
                ));
            }
            authority_index += 1;
        }
        binding_index += 1;
    }
    if binding_index != bindings.len() {
        return Err(SealError::Noncanonical(
            "bank binding is not used by DSF delivery",
        ));
    }
    Ok(())
}

fn validate_bank_coverage_bytes(state: &OrganismState, bytes: &[u8]) -> Result<(), SealError> {
    let authorities = &state.dsf_delivery_authorities;
    let mut authority_index = 0;
    let mut bindings = bytes.chunks_exact(BANK_BINDING_BYTES);
    while authority_index < authorities.len() {
        let authority = &authorities[authority_index];
        let binding = bindings
            .next()
            .ok_or(SealError::Noncanonical("DSF delivery has no bank binding"))?;
        if binding[32..64] != authority.field_bank_receipt
            || binding[64..96] != authority.kernel_config_receipt
        {
            return Err(SealError::Noncanonical(
                "DSF bank binding differs from delivery authority",
            ));
        }

        let bank_receipt = authority.field_bank_receipt;
        let kernel_config_receipt = authority.kernel_config_receipt;
        authority_index += 1;
        while authority_index < authorities.len()
            && authorities[authority_index].field_bank_receipt == bank_receipt
        {
            if authorities[authority_index].kernel_config_receipt != kernel_config_receipt {
                return Err(SealError::Noncanonical(
                    "one bank receipt has multiple kernel configurations",
                ));
            }
            authority_index += 1;
        }
    }
    if bindings.next().is_some() {
        return Err(SealError::Noncanonical(
            "bank binding is not used by DSF delivery",
        ));
    }
    Ok(())
}

fn hmac_tag(key: &SealKey, authenticated_bytes: &[u8]) -> Result<[u8; 32], SealError> {
    let mut mac = HmacSha256::new_from_slice(&*key.bytes).map_err(|_| SealError::HmacFailed)?;
    mac.update(DOMAIN);
    mac.update(authenticated_bytes);
    Ok(mac.finalize().into_bytes().into())
}

fn verify_hmac(key: &SealKey, authenticated_bytes: &[u8], tag: &[u8]) -> Result<(), SealError> {
    let mut mac = HmacSha256::new_from_slice(&*key.bytes).map_err(|_| SealError::HmacFailed)?;
    mac.update(DOMAIN);
    mac.update(authenticated_bytes);
    mac.verify_slice(tag).map_err(|_| SealError::HmacFailed)
}

fn encoded_length(organism_bytes: usize, bank_bindings: usize) -> Result<usize, SealError> {
    FIXED_ENVELOPE_BYTES
        .checked_add(
            bank_bindings
                .checked_mul(BANK_BINDING_BYTES)
                .ok_or(SealError::LengthOverflow)?,
        )
        .and_then(|value| value.checked_add(organism_bytes))
        .ok_or(SealError::LengthOverflow)
}

fn enforce_count_budget(count: usize, maximum: u64) -> Result<(), SealError> {
    if u64_len(count)? > maximum {
        Err(SealError::LengthOverflow)
    } else {
        Ok(())
    }
}

fn digest(bytes: &[u8]) -> [u8; 32] {
    Sha256::digest(bytes).into()
}

fn u64_len(value: usize) -> Result<u64, SealError> {
    u64::try_from(value).map_err(|_| SealError::LengthOverflow)
}

fn array<const N: usize>(bytes: &[u8]) -> [u8; N] {
    bytes.try_into().expect("fixed slice length was checked")
}

struct Cursor<'a> {
    bytes: &'a [u8],
    position: usize,
}

impl<'a> Cursor<'a> {
    fn new(bytes: &'a [u8]) -> Self {
        Self { bytes, position: 0 }
    }

    fn take(&mut self, length: usize) -> Result<&'a [u8], SealError> {
        let end = self
            .position
            .checked_add(length)
            .ok_or(SealError::LengthOverflow)?;
        let value = self
            .bytes
            .get(self.position..end)
            .ok_or(SealError::UnexpectedEnd)?;
        self.position = end;
        Ok(value)
    }

    fn fixed<const N: usize>(&mut self) -> Result<[u8; N], SealError> {
        Ok(array(self.take(N)?))
    }

    fn u16(&mut self) -> Result<u16, SealError> {
        Ok(u16::from_le_bytes(self.fixed()?))
    }

    fn u32(&mut self) -> Result<u32, SealError> {
        Ok(u32::from_le_bytes(self.fixed()?))
    }

    fn u64(&mut self) -> Result<u64, SealError> {
        Ok(u64::from_le_bytes(self.fixed()?))
    }

    fn finished(&self) -> bool {
        self.position == self.bytes.len()
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::organism::{
        genesis::{
            authenticate_genesis_identity, authenticate_global_owner_genesis,
            verify_genesis_identity, verify_global_owner_genesis, GenesisAuthenticationKey,
            VerifiedGenesisIdentity,
        },
        ArenaRange, DsfDeliveryAuthority, LocalDsfState, NeuronState, PackedTrits,
        ResourceObservation, StabilityEvidenceRanges, WakeState,
    };

    const IDENTITY: [u8; 16] = [
        0x10, 0x53, 0x2f, 0x91, 0x7b, 0x2d, 0x4a, 0xc8, 0x98, 0x04, 0x46, 0x73, 0x5d, 0xa1, 0x28,
        0xfe,
    ];
    const OTHER_IDENTITY: [u8; 16] = [
        0x2c, 0x32, 0xe0, 0xd2, 0x29, 0xbb, 0x48, 0xbb, 0xa4, 0x70, 0x13, 0xe5, 0xe1, 0x92, 0x2f,
        0xb8,
    ];

    const ENCODE: SealEncodeBudget = SealEncodeBudget {
        max_organism_bytes: 1_000_000,
        max_output_bytes: 1_000_000,
        max_bank_bindings: 8,
    };
    const DECODE: SealDecodeBudget = SealDecodeBudget {
        max_input_bytes: 1_000_000,
        max_organism_bytes: 1_000_000,
        max_decoded_heap_bytes: 1_000_000,
        max_bank_bindings: 8,
    };

    fn receipt(byte: u8) -> [u8; 32] {
        [byte; 32]
    }

    fn key(epoch: u32, byte: u8) -> SealKey {
        SealKey::new(epoch, [byte; 32]).expect("test key")
    }

    fn verified_identity(identity: [u8; 16]) -> VerifiedGenesisIdentity {
        let genesis_key =
            GenesisAuthenticationKey::new(73, [0xa7; 32]).expect("genesis-only test key");
        let record = authenticate_genesis_identity(identity, &genesis_key).expect("genesis record");
        verify_genesis_identity(record.as_bytes(), &genesis_key, record.trusted_head())
            .expect("verified genesis identity")
    }

    fn authority(marker: u8, port_index: u64) -> DsfDeliveryAuthority {
        DsfDeliveryAuthority {
            field_bank_receipt: receipt(marker),
            kernel_config_receipt: receipt(marker + 1),
            port_index,
            tuple_index: 0,
            trace_receipt: receipt(marker + 2),
            tuple_receipt: receipt(marker + 3),
            basin_receipt: receipt(marker + 4),
        }
    }

    fn neuron(marker: u8, position: u64, authority_index: u64) -> NeuronState {
        NeuronState {
            lineage: [marker; 16],
            growth_dna: receipt(marker + 1),
            specialization_receipt: receipt(marker + 2),
            field_position: position,
            trit_range: ArenaRange { start: 0, len: 0 },
            oscillator_phase_bits: 0.25_f64.to_bits(),
            oscillator_winding: i64::from(marker),
            local_dsf: LocalDsfState {
                coordinate_bits: [
                    0.1_f64.to_bits(),
                    0.2_f64.to_bits(),
                    0.3_f64.to_bits(),
                    0.4_f64.to_bits(),
                    0.5_f64.to_bits(),
                    0.6_f64.to_bits(),
                    0.7_f64.to_bits(),
                ],
                authority_index,
            },
            energetic_bits: 0.75_f64.to_bits(),
            refractory_until_generation: 2,
            fractal: receipt(marker + 5),
            evidence_receipt: receipt(marker + 6),
            recent_causal_range: ArenaRange { start: 0, len: 0 },
        }
    }

    fn state(generation: u64, prior_state_receipt: [u8; 32]) -> OrganismState {
        OrganismState {
            identity: IDENTITY,
            generation,
            prior_state_receipt,
            authenticated_world_revision: receipt(2),
            body_state_receipt: receipt(3),
            admitted_evidence: vec![],
            trit_arena: PackedTrits::from_trits(&[]).expect("empty trit arena"),
            causal_receipt_arena: vec![],
            dsf_delivery_authorities: vec![authority(30, 0), authority(40, 1)],
            neurons: vec![neuron(10, 1, 0), neuron(20, 2, 1)],
            couplings: vec![],
            causal_frontier: vec![],
            formation_member_arena: vec![],
            formations: vec![],
            stability_evidence_arena: vec![],
            stability_evidence: StabilityEvidenceRanges {
                coherence: ArenaRange { start: 0, len: 0 },
                formation_entropy: ArenaRange { start: 0, len: 0 },
                breathing_variance: ArenaRange { start: 0, len: 0 },
                uncertainty: ArenaRange { start: 0, len: 0 },
                tapestry_drift: ArenaRange { start: 0, len: 0 },
            },
            wake: WakeState::Quiescent,
            resources: ResourceObservation {
                cpu_nanoseconds: 1,
                resident_bytes: 2,
                durable_bytes: 3,
                recovery_reserve_bytes: 4,
                python_calls: 0,
                native_calls: 1,
            },
        }
    }

    fn bindings() -> Vec<CanonicalBankBinding> {
        vec![
            CanonicalBankBinding {
                candidate_receipt: receipt(10),
                bank_receipt: receipt(30),
                kernel_config_receipt: receipt(31),
            },
            CanonicalBankBinding {
                candidate_receipt: receipt(20),
                bank_receipt: receipt(40),
                kernel_config_receipt: receipt(41),
            },
        ]
    }

    fn genesis_bytes() -> (SealKey, Vec<u8>) {
        let key = key(1, 9);
        let bytes =
            seal_genesis(&state(0, ZERO_RECEIPT), &key, &bindings(), ENCODE).expect("genesis seal");
        (key, bytes)
    }

    fn head(bytes: &[u8]) -> [u8; 32] {
        digest(bytes)
    }

    fn retag(bytes: &mut [u8], key: &SealKey) {
        let tag_offset = bytes.len() - TAG_BYTES;
        let tag = hmac_tag(key, &bytes[..tag_offset]).expect("test tag");
        bytes[tag_offset..].copy_from_slice(&tag);
    }

    #[test]
    fn deterministic_genuine_state_round_trip_is_exact_custody_only() {
        let (key, first) = genesis_bytes();
        let second =
            seal_genesis(&state(0, ZERO_RECEIPT), &key, &bindings(), ENCODE).expect("repeat seal");
        assert_eq!(first, second);
        let identity = verified_identity(IDENTITY);
        let verified = verify_genesis(&first, &key, head(&first), &identity, DECODE)
            .expect("verified genesis");
        assert_eq!(verified.state().generation, 0);
        assert_eq!(verified.key_epoch(), 1);
        assert_eq!(identity.key_epoch(), 73);
        assert_eq!(verified.prior_seal_receipt(), ZERO_RECEIPT);
        assert_eq!(verified.bank_bindings(), bindings());
    }

    #[test]
    fn v1_seal_magic_and_version_have_no_fallback() {
        let (key, canonical) = genesis_bytes();
        let identity = verified_identity(IDENTITY);

        let mut legacy_magic = canonical.clone();
        legacy_magic[..8].copy_from_slice(b"GULSEAL1");
        legacy_magic[8..10].copy_from_slice(&1_u16.to_le_bytes());
        retag(&mut legacy_magic, &key);
        assert_eq!(
            verify_genesis(&legacy_magic, &key, head(&legacy_magic), &identity, DECODE,).err(),
            Some(SealError::BadMagic)
        );

        let mut legacy_version = canonical;
        legacy_version[8..10].copy_from_slice(&1_u16.to_le_bytes());
        retag(&mut legacy_version, &key);
        assert_eq!(
            verify_genesis(
                &legacy_version,
                &key,
                head(&legacy_version),
                &identity,
                DECODE,
            )
            .err(),
            Some(SealError::UnsupportedVersion(1))
        );
    }

    #[test]
    fn every_envelope_region_and_tag_tamper_fails_closed() {
        let (key, bytes) = genesis_bytes();
        let identity = verified_identity(IDENTITY);
        let organism_offset = bytes.len()
            - TAG_BYTES
            - state(0, ZERO_RECEIPT)
                .encode_unverified(ENCODE.max_organism_bytes)
                .expect("state bytes")
                .len();
        let offsets = [
            0,
            8,
            10,
            14,
            30,
            38,
            70,
            102,
            134,
            142,
            174,
            206,
            238,
            270,
            302,
            334,
            organism_offset,
            bytes.len() - 1,
        ];
        assert_eq!(organism_offset, 342);
        for offset in offsets {
            let mut changed = bytes.clone();
            changed[offset] ^= 1;
            assert!(
                verify_genesis(&changed, &key, head(&changed), &identity, DECODE).is_err(),
                "tamper offset {offset}"
            );
        }
    }

    #[test]
    fn wrong_key_head_and_epoch_fail_in_order() {
        let (seal_key, bytes) = genesis_bytes();
        let identity = verified_identity(IDENTITY);
        assert_eq!(
            verify_genesis(&bytes, &seal_key, receipt(1), &identity, DECODE).err(),
            Some(SealError::TrustedHeadMismatch)
        );
        assert_eq!(
            verify_genesis(&bytes, &key(1, 10), head(&bytes), &identity, DECODE).err(),
            Some(SealError::HmacFailed)
        );
        assert_eq!(
            verify_genesis(&bytes, &key(2, 9), head(&bytes), &identity, DECODE).err(),
            Some(SealError::KeyEpochMismatch)
        );
    }

    #[test]
    fn authenticated_seal_for_another_identity_fails_closed() {
        let (seal_key, bytes) = genesis_bytes();
        let other_identity = verified_identity(OTHER_IDENTITY);
        assert_eq!(
            verify_genesis(&bytes, &seal_key, head(&bytes), &other_identity, DECODE,).err(),
            Some(SealError::GenesisMismatch)
        );
    }

    #[test]
    fn genesis_verification_entry_point_is_capability_typed() {
        let _: fn(
            &[u8],
            &SealKey,
            [u8; 32],
            &VerifiedGenesisIdentity,
            SealDecodeBudget,
        ) -> Result<CustodyVerifiedSeal, SealError> = verify_genesis;
    }

    #[test]
    fn sole_global_root_seals_and_verifies_v2_continuity() {
        let owner = SuppliedGlobalOwnerRootKey::new(11, [0x6a; 32]).unwrap();
        let genesis_record = authenticate_global_owner_genesis(IDENTITY, &owner).unwrap();
        let identity = verify_global_owner_genesis(
            genesis_record.as_bytes(),
            &owner,
            genesis_record.trusted_head(),
        )
        .unwrap();
        let genesis_state = state(0, ZERO_RECEIPT);
        let genesis_bytes =
            seal_global_owner_genesis(&genesis_state, &owner, &bindings(), ENCODE).unwrap();
        let verified = verify_global_owner_genesis_seal(
            &genesis_bytes,
            &owner,
            digest(&genesis_bytes),
            &identity,
            DECODE,
        )
        .unwrap();
        let successor_state = state(1, verified.organism_state_receipt());
        let successor_bytes =
            seal_global_owner_successor(&successor_state, &owner, &verified, &bindings(), ENCODE)
                .unwrap();
        verify_global_owner_successor(
            &successor_bytes,
            &owner,
            digest(&successor_bytes),
            &verified,
            DECODE,
        )
        .unwrap();

        let wrong_root = SuppliedGlobalOwnerRootKey::new(11, [0x6b; 32]).unwrap();
        assert_eq!(
            verify_global_owner_genesis_seal(
                &genesis_bytes,
                &wrong_root,
                digest(&genesis_bytes),
                &identity,
                DECODE,
            )
            .err(),
            Some(SealError::AuthorityMismatch)
        );
        let wrong_epoch = SuppliedGlobalOwnerRootKey::new(12, [0x6a; 32]).unwrap();
        assert_eq!(
            verify_global_owner_genesis_seal(
                &genesis_bytes,
                &wrong_epoch,
                digest(&genesis_bytes),
                &identity,
                DECODE,
            )
            .err(),
            Some(SealError::AuthorityMismatch)
        );

        let other_genesis = authenticate_global_owner_genesis(IDENTITY, &wrong_root).unwrap();
        let other_identity = verify_global_owner_genesis(
            other_genesis.as_bytes(),
            &wrong_root,
            other_genesis.trusted_head(),
        )
        .unwrap();
        assert_eq!(
            verify_global_owner_genesis_seal(
                &genesis_bytes,
                &owner,
                digest(&genesis_bytes),
                &other_identity,
                DECODE,
            )
            .err(),
            Some(SealError::AuthorityMismatch)
        );

        assert_eq!(
            seal_global_owner_successor(
                &successor_state,
                &wrong_root,
                &verified,
                &bindings(),
                ENCODE,
            )
            .err(),
            Some(SealError::AuthorityMismatch)
        );
    }

    #[test]
    fn root_pinned_current_checkpoint_verifies_without_claiming_history() {
        let owner = SuppliedGlobalOwnerRootKey::new(17, [0x71; 32]).unwrap();
        let genesis_record = authenticate_global_owner_genesis(IDENTITY, &owner).unwrap();
        let identity = verify_global_owner_genesis(
            genesis_record.as_bytes(),
            &owner,
            genesis_record.trusted_head(),
        )
        .unwrap();
        let key = SealKey::from_zeroizing(owner.epoch(), owner.derive_organism_seal_key()).unwrap();
        let checkpoint_state = state(7, receipt(91));
        let checkpoint =
            encode_seal(&checkpoint_state, &key, receipt(92), &bindings(), ENCODE).unwrap();
        let state_receipt = digest(
            &checkpoint_state
                .encode_unverified(ENCODE.max_organism_bytes)
                .unwrap(),
        );
        let seal_receipt = digest(&checkpoint);
        let current_identity = IDENTITY;
        let current_generation = 7;
        let current = AuthenticatedCurrentSealCoordinates::for_test(
            &seal_receipt,
            &current_identity,
            &current_generation,
            &state_receipt,
        );
        let verified = verify_global_owner_current_checkpoint(
            &checkpoint,
            &owner,
            &current,
            &identity,
            DECODE,
        )
        .unwrap();
        assert_eq!(verified.state(), &checkpoint_state);
        assert_eq!(verified.prior_seal_receipt(), receipt(92));
    }

    #[test]
    fn root_pinned_current_checkpoint_requires_every_current_coordinate() {
        let owner = SuppliedGlobalOwnerRootKey::new(18, [0x72; 32]).unwrap();
        let genesis_record = authenticate_global_owner_genesis(IDENTITY, &owner).unwrap();
        let identity = verify_global_owner_genesis(
            genesis_record.as_bytes(),
            &owner,
            genesis_record.trusted_head(),
        )
        .unwrap();
        let key = SealKey::from_zeroizing(owner.epoch(), owner.derive_organism_seal_key()).unwrap();
        let checkpoint_state = state(3, receipt(81));
        let checkpoint =
            encode_seal(&checkpoint_state, &key, receipt(82), &bindings(), ENCODE).unwrap();
        let seal_receipt = digest(&checkpoint);
        let state_receipt = digest(
            &checkpoint_state
                .encode_unverified(ENCODE.max_organism_bytes)
                .unwrap(),
        );
        for (current_identity, current_generation, current_state_receipt) in [
            (OTHER_IDENTITY, 3, state_receipt),
            (IDENTITY, 4, state_receipt),
            (IDENTITY, 3, receipt(99)),
        ] {
            let current = AuthenticatedCurrentSealCoordinates::for_test(
                &seal_receipt,
                &current_identity,
                &current_generation,
                &current_state_receipt,
            );
            assert_eq!(
                verify_global_owner_current_checkpoint(
                    &checkpoint,
                    &owner,
                    &current,
                    &identity,
                    DECODE,
                )
                .err(),
                Some(SealError::CurrentCheckpointMismatch)
            );
        }

        let wrong_owner = SuppliedGlobalOwnerRootKey::new(18, [0x73; 32]).unwrap();
        let current_identity = IDENTITY;
        let current_generation = 3;
        let current = AuthenticatedCurrentSealCoordinates::for_test(
            &seal_receipt,
            &current_identity,
            &current_generation,
            &state_receipt,
        );
        assert_eq!(
            verify_global_owner_current_checkpoint(
                &checkpoint,
                &wrong_owner,
                &current,
                &identity,
                DECODE,
            )
            .err(),
            Some(SealError::AuthorityMismatch)
        );
    }

    #[test]
    fn root_pinned_current_checkpoint_rejects_noncanonical_prior_presence() {
        let owner = SuppliedGlobalOwnerRootKey::new(19, [0x74; 32]).unwrap();
        let genesis_record = authenticate_global_owner_genesis(IDENTITY, &owner).unwrap();
        let identity = verify_global_owner_genesis(
            genesis_record.as_bytes(),
            &owner,
            genesis_record.trusted_head(),
        )
        .unwrap();
        let key = SealKey::from_zeroizing(owner.epoch(), owner.derive_organism_seal_key()).unwrap();

        let genesis_state = state(0, ZERO_RECEIPT);
        let mut noncanonical_genesis =
            seal_genesis(&genesis_state, &key, &bindings(), ENCODE).unwrap();
        noncanonical_genesis[70..102].copy_from_slice(&receipt(77));
        retag(&mut noncanonical_genesis, &key);
        let genesis_state_receipt = digest(
            &genesis_state
                .encode_unverified(ENCODE.max_organism_bytes)
                .unwrap(),
        );
        let genesis_seal_receipt = digest(&noncanonical_genesis);
        let current_identity = IDENTITY;
        let genesis_generation = 0;
        let genesis_current = AuthenticatedCurrentSealCoordinates::for_test(
            &genesis_seal_receipt,
            &current_identity,
            &genesis_generation,
            &genesis_state_receipt,
        );
        assert_eq!(
            verify_global_owner_current_checkpoint(
                &noncanonical_genesis,
                &owner,
                &genesis_current,
                &identity,
                DECODE,
            )
            .err(),
            Some(SealError::CurrentCheckpointMismatch)
        );

        let successor_state = state(2, receipt(78));
        let mut missing_prior_seal =
            encode_seal(&successor_state, &key, receipt(79), &bindings(), ENCODE).unwrap();
        missing_prior_seal[70..102].fill(0);
        retag(&mut missing_prior_seal, &key);
        let successor_state_receipt = digest(
            &successor_state
                .encode_unverified(ENCODE.max_organism_bytes)
                .unwrap(),
        );
        let successor_seal_receipt = digest(&missing_prior_seal);
        let successor_generation = 2;
        let successor_current = AuthenticatedCurrentSealCoordinates::for_test(
            &successor_seal_receipt,
            &current_identity,
            &successor_generation,
            &successor_state_receipt,
        );
        assert_eq!(
            verify_global_owner_current_checkpoint(
                &missing_prior_seal,
                &owner,
                &successor_current,
                &identity,
                DECODE,
            )
            .err(),
            Some(SealError::CurrentCheckpointMismatch)
        );
    }

    #[test]
    fn genesis_and_one_successor_require_exact_continuity() {
        let (key, genesis) = genesis_bytes();
        let identity = verified_identity(IDENTITY);
        let prior =
            verify_genesis(&genesis, &key, head(&genesis), &identity, DECODE).expect("genesis");
        let successor_state = state(1, prior.organism_state_receipt());
        let successor = seal_successor(&successor_state, &key, &prior, &bindings(), ENCODE)
            .expect("successor seal");
        let verified = verify_successor(&successor, &key, head(&successor), &prior, DECODE)
            .expect("exact successor");
        assert_eq!(verified.state().generation, 1);

        let unrelated_prior = verify_genesis(&genesis, &key, head(&genesis), &identity, DECODE)
            .expect("second genesis handle");
        let wrong_state = state(2, unrelated_prior.organism_state_receipt());
        let wrong = encode_seal(
            &wrong_state,
            &key,
            unrelated_prior.seal_receipt(),
            &bindings(),
            ENCODE,
        );
        assert!(wrong.is_ok());
        let wrong = wrong.expect("independently canonical non-successor");
        assert_eq!(
            verify_successor(&wrong, &key, head(&wrong), &prior, DECODE).err(),
            Some(SealError::SuccessorMismatch)
        );
    }

    #[test]
    fn zero_key_material_and_non_genesis_state_are_rejected() {
        assert_eq!(
            SealKey::new(1, [0; 32]).err(),
            Some(SealError::Noncanonical("seal key bytes are all zero"))
        );

        let key = key(1, 9);
        assert_eq!(
            seal_genesis(&state(1, receipt(1)), &key, &bindings(), ENCODE).err(),
            Some(SealError::GenesisMismatch)
        );
    }

    #[test]
    fn successor_constructor_rejects_skip_wrong_state_wrong_prior_and_identity() {
        let (key, genesis) = genesis_bytes();
        let identity = verified_identity(IDENTITY);
        let prior =
            verify_genesis(&genesis, &key, head(&genesis), &identity, DECODE).expect("genesis");
        let valid_state = state(1, prior.organism_state_receipt());

        assert_eq!(
            seal_successor(
                &state(2, prior.organism_state_receipt()),
                &key,
                &prior,
                &bindings(),
                ENCODE,
            )
            .err(),
            Some(SealError::SuccessorMismatch)
        );
        assert_eq!(
            seal_successor(&state(1, receipt(99)), &key, &prior, &bindings(), ENCODE,).err(),
            Some(SealError::SuccessorMismatch)
        );

        let mut wrong_identity = valid_state.clone();
        wrong_identity.identity = [8; 16];
        assert_eq!(
            seal_successor(&wrong_identity, &key, &prior, &bindings(), ENCODE).err(),
            Some(SealError::SuccessorMismatch)
        );

        let mut alternate_genesis_state = state(0, ZERO_RECEIPT);
        alternate_genesis_state.body_state_receipt = receipt(99);
        let alternate_genesis = seal_genesis(&alternate_genesis_state, &key, &bindings(), ENCODE)
            .expect("alternate genesis seal");
        let alternate_prior = verify_genesis(
            &alternate_genesis,
            &key,
            head(&alternate_genesis),
            &identity,
            DECODE,
        )
        .expect("alternate verified prior");
        assert_eq!(
            seal_successor(&valid_state, &key, &alternate_prior, &bindings(), ENCODE,).err(),
            Some(SealError::SuccessorMismatch)
        );
    }

    #[test]
    fn duplicate_candidate_mappings_fail_after_authentication_on_decode() {
        let state = state(0, ZERO_RECEIPT);
        let key = key(1, 9);
        let identity = verified_identity(IDENTITY);
        let mut duplicate_candidate = bindings();
        duplicate_candidate[1].candidate_receipt = duplicate_candidate[0].candidate_receipt;
        assert_eq!(
            seal_genesis(&state, &key, &duplicate_candidate, ENCODE).err(),
            Some(SealError::Noncanonical(
                "candidate receipt is mapped more than once"
            ))
        );

        let (_, original) = genesis_bytes();
        let mut malformed = original.clone();
        malformed[238..270].copy_from_slice(&original[142..174]);
        assert_eq!(
            verify_genesis(&malformed, &key, head(&malformed), &identity, DECODE).err(),
            Some(SealError::HmacFailed)
        );
        retag(&mut malformed, &key);
        assert_eq!(
            verify_genesis(&malformed, &key, head(&malformed), &identity, DECODE).err(),
            Some(SealError::Noncanonical(
                "candidate receipt is mapped more than once"
            ))
        );
    }

    #[test]
    fn noncanonical_and_duplicate_lists_are_rejected() {
        let state = state(0, ZERO_RECEIPT);
        let key = key(1, 9);
        let identity = verified_identity(IDENTITY);
        let mut reordered = bindings();
        reordered.swap(0, 1);
        assert!(seal_genesis(&state, &key, &reordered, ENCODE).is_err());
        let mut duplicate = bindings();
        duplicate[1] = duplicate[0];
        assert!(seal_genesis(&state, &key, &duplicate, ENCODE).is_err());
        let (_, original) = genesis_bytes();
        let mut malformed = original.clone();
        malformed[238..334].copy_from_slice(&original[142..238]);
        retag(&mut malformed, &key);
        assert!(verify_genesis(&malformed, &key, head(&malformed), &identity, DECODE).is_err());
    }

    #[test]
    fn one_binding_covers_each_unique_bank_and_exact_configuration() {
        let key = key(1, 9);
        let identity = verified_identity(IDENTITY);
        let mut shared_bank_state = state(0, ZERO_RECEIPT);
        shared_bank_state.dsf_delivery_authorities[1].field_bank_receipt = receipt(30);
        shared_bank_state.dsf_delivery_authorities[1].kernel_config_receipt = receipt(31);
        let one_binding = vec![bindings()[0]];

        let bytes = seal_genesis(&shared_bank_state, &key, &one_binding, ENCODE)
            .expect("one binding for one unique bank");
        let verified = verify_genesis(&bytes, &key, head(&bytes), &identity, DECODE)
            .expect("verified grouping");
        assert_eq!(verified.bank_bindings(), one_binding);

        shared_bank_state.dsf_delivery_authorities[1].kernel_config_receipt = receipt(32);
        assert_eq!(
            seal_genesis(&shared_bank_state, &key, &one_binding, ENCODE,).err(),
            Some(SealError::Noncanonical(
                "one bank receipt has multiple kernel configurations"
            ))
        );
    }

    #[test]
    fn every_truncation_and_trailing_byte_fails_closed() {
        let (key, bytes) = genesis_bytes();
        let identity = verified_identity(IDENTITY);
        for cut in 0..bytes.len() {
            let truncated = &bytes[..cut];
            assert!(
                verify_genesis(truncated, &key, head(truncated), &identity, DECODE).is_err(),
                "cut {cut}"
            );
        }
        let mut trailing = bytes.clone();
        trailing.push(0);
        assert_eq!(
            verify_genesis(&trailing, &key, head(&trailing), &identity, DECODE).err(),
            Some(SealError::TrailingBytes)
        );
    }

    #[test]
    fn all_caller_budgets_fail_closed() {
        let (key, bytes) = genesis_bytes();
        let state = state(0, ZERO_RECEIPT);
        let identity = verified_identity(IDENTITY);
        let small_output = SealEncodeBudget {
            max_output_bytes: bytes.len() as u64 - 1,
            ..ENCODE
        };
        assert_eq!(
            seal_genesis(&state, &key, &bindings(), small_output).err(),
            Some(SealError::OutputBudgetExceeded)
        );
        let small_organism = SealEncodeBudget {
            max_organism_bytes: 1,
            ..ENCODE
        };
        assert!(seal_genesis(&state, &key, &bindings(), small_organism).is_err());
        assert_eq!(
            seal_genesis(
                &state,
                &key,
                &bindings(),
                SealEncodeBudget {
                    max_bank_bindings: 1,
                    ..ENCODE
                }
            )
            .err(),
            Some(SealError::BankBindingBudgetExceeded)
        );
        for (budget, expected) in [
            (
                SealDecodeBudget {
                    max_input_bytes: bytes.len() as u64 - 1,
                    ..DECODE
                },
                SealError::InputBudgetExceeded,
            ),
            (
                SealDecodeBudget {
                    max_organism_bytes: 1,
                    ..DECODE
                },
                SealError::OrganismBudgetExceeded,
            ),
            (
                SealDecodeBudget {
                    max_bank_bindings: 1,
                    ..DECODE
                },
                SealError::BankBindingBudgetExceeded,
            ),
        ] {
            assert_eq!(
                verify_genesis(&bytes, &key, head(&bytes), &identity, budget).err(),
                Some(expected)
            );
        }
        assert!(matches!(
            verify_genesis(
                &bytes,
                &key,
                head(&bytes),
                &identity,
                SealDecodeBudget {
                    max_decoded_heap_bytes: 0,
                    ..DECODE
                }
            ),
            Err(SealError::Organism(CodecError::AllocationBudgetExceeded))
        ));
    }
}
