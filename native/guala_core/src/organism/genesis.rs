//! Authenticated native genesis identity boundary.
//!
//! This boundary does not choose, derive, label, or interpret an organism
//! identity. It accepts exactly one caller-provided RFC 4122 UUIDv4 byte array,
//! authenticates that opaque value under a genesis-only key epoch, and pins the
//! exact record with a separately held trusted-head receipt. Only successful
//! verification yields [`VerifiedGenesisIdentity`].

use super::wake_admission::SuppliedGlobalOwnerRootKey;
use hmac::{Hmac, Mac};
use sha2::{Digest, Sha256};
use std::fmt;
use zeroize::Zeroizing;

type HmacSha256 = Hmac<Sha256>;

const MAGIC: &[u8; 8] = b"GULGEN02";
const VERSION: u16 = 2;
const AUTHENTICATION_DOMAIN: &[u8] = b"guala.native.genesis.authentication.v2\0";
const TRUSTED_HEAD_DOMAIN: &[u8] = b"guala.native.genesis.trusted-head.v2\0";
const CAPABILITY_BINDING_DOMAIN: &[u8] = b"guala.native.genesis.capability-binding.v2\0";
const HEADER_BYTES: usize = 8 + 2 + 4 + 16;
const TAG_BYTES: usize = 32;

/// The exact encoded size of every native genesis identity record.
pub const GENESIS_RECORD_BYTES: usize = HEADER_BYTES + TAG_BYTES;

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum GenesisError {
    WrongLength,
    BadMagic,
    UnsupportedVersion(u16),
    InvalidUuidVersion,
    InvalidUuidVariant,
    ZeroKeyEpoch,
    ZeroKey,
    ZeroTrustedHead,
    KeyEpochMismatch,
    TrustedHeadMismatch,
    AuthenticationFailed,
}

impl fmt::Display for GenesisError {
    fn fmt(&self, output: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::WrongLength => write!(output, "genesis record has a noncanonical length"),
            Self::BadMagic => write!(output, "genesis record magic differs"),
            Self::UnsupportedVersion(version) => {
                write!(output, "unsupported genesis record version {version}")
            }
            Self::InvalidUuidVersion => {
                write!(output, "genesis identity is not an RFC 4122 UUID version 4")
            }
            Self::InvalidUuidVariant => {
                write!(
                    output,
                    "genesis identity does not use the RFC 4122 UUID variant"
                )
            }
            Self::ZeroKeyEpoch => write!(output, "genesis key epoch is zero"),
            Self::ZeroKey => write!(output, "genesis authentication key is all zero"),
            Self::ZeroTrustedHead => write!(output, "genesis trusted head is all zero"),
            Self::KeyEpochMismatch => write!(output, "genesis key epoch differs"),
            Self::TrustedHeadMismatch => write!(output, "genesis trusted head differs"),
            Self::AuthenticationFailed => write!(output, "genesis authentication failed"),
        }
    }
}

impl std::error::Error for GenesisError {}

/// Genesis-only authentication key material.
///
/// This type is intentionally distinct from every organism-state sealing key.
/// Its internal copy is zeroized on drop. The caller must separately zeroize
/// every source copy it retains after construction.
pub struct GenesisAuthenticationKey {
    epoch: u32,
    bytes: Zeroizing<[u8; 32]>,
}

impl GenesisAuthenticationKey {
    #[cfg(test)]
    pub fn new(epoch: u32, bytes: [u8; 32]) -> Result<Self, GenesisError> {
        Self::from_zeroizing(epoch, Zeroizing::new(bytes))
    }

    fn from_zeroizing(epoch: u32, bytes: Zeroizing<[u8; 32]>) -> Result<Self, GenesisError> {
        if epoch == 0 {
            return Err(GenesisError::ZeroKeyEpoch);
        }
        if *bytes == [0; 32] {
            return Err(GenesisError::ZeroKey);
        }
        Ok(Self { epoch, bytes })
    }

    pub fn epoch(&self) -> u32 {
        self.epoch
    }
}

/// A separately persisted receipt that pins one exact authenticated record.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct GenesisTrustedHead([u8; 32]);

impl GenesisTrustedHead {
    pub fn from_receipt(receipt: [u8; 32]) -> Result<Self, GenesisError> {
        if receipt == [0; 32] {
            return Err(GenesisError::ZeroTrustedHead);
        }
        Ok(Self(receipt))
    }

    pub fn receipt(&self) -> [u8; 32] {
        self.0
    }
}

/// One fixed-size authenticated genesis record ready for durable custody.
pub struct AuthenticatedGenesisRecord {
    bytes: [u8; GENESIS_RECORD_BYTES],
    trusted_head: GenesisTrustedHead,
}

impl AuthenticatedGenesisRecord {
    pub fn as_bytes(&self) -> &[u8; GENESIS_RECORD_BYTES] {
        &self.bytes
    }

    pub fn into_bytes(self) -> [u8; GENESIS_RECORD_BYTES] {
        self.bytes
    }

    pub fn trusted_head(&self) -> GenesisTrustedHead {
        self.trusted_head
    }
}

/// Narrow proof that one exact caller-provided identity passed the authenticated
/// genesis boundary. There is deliberately no public constructor.
pub struct VerifiedGenesisIdentity {
    identity: [u8; 16],
    key_epoch: u32,
    trusted_head: GenesisTrustedHead,
    authority_binding: [u8; 32],
}

impl VerifiedGenesisIdentity {
    pub fn identity_bytes(&self) -> [u8; 16] {
        self.identity
    }

    pub fn key_epoch(&self) -> u32 {
        self.key_epoch
    }

    pub fn trusted_head(&self) -> GenesisTrustedHead {
        self.trusted_head
    }

    pub(super) fn is_bound_to_global_owner(
        &self,
        global_owner: &SuppliedGlobalOwnerRootKey,
    ) -> bool {
        let key = match GenesisAuthenticationKey::from_zeroizing(
            global_owner.epoch(),
            global_owner.derive_genesis_authentication_key(),
        ) {
            Ok(key) => key,
            Err(_) => return false,
        };
        verify_capability_binding(&key, self.trusted_head, &self.authority_binding)
    }
}

/// Authenticates exactly the opaque UUIDv4 supplied by the caller.
pub fn authenticate_genesis_identity(
    caller_identity: [u8; 16],
    key: &GenesisAuthenticationKey,
) -> Result<AuthenticatedGenesisRecord, GenesisError> {
    validate_uuid_v4(caller_identity)?;

    let mut bytes = [0_u8; GENESIS_RECORD_BYTES];
    bytes[..8].copy_from_slice(MAGIC);
    bytes[8..10].copy_from_slice(&VERSION.to_le_bytes());
    bytes[10..14].copy_from_slice(&key.epoch.to_le_bytes());
    bytes[14..HEADER_BYTES].copy_from_slice(&caller_identity);
    let tag = authentication_tag(key, &bytes[..HEADER_BYTES]);
    bytes[HEADER_BYTES..].copy_from_slice(&tag);

    Ok(AuthenticatedGenesisRecord {
        trusted_head: trusted_head(&bytes),
        bytes,
    })
}

pub(crate) fn authenticate_global_owner_genesis(
    caller_identity: [u8; 16],
    global_owner: &SuppliedGlobalOwnerRootKey,
) -> Result<AuthenticatedGenesisRecord, GenesisError> {
    let key = GenesisAuthenticationKey::from_zeroizing(
        global_owner.epoch(),
        global_owner.derive_genesis_authentication_key(),
    )?;
    authenticate_genesis_identity(caller_identity, &key)
}

/// Verifies exact record length, trusted-head custody, format, key epoch, UUIDv4
/// form, and HMAC possession before issuing an identity capability.
pub fn verify_genesis_identity(
    record: &[u8],
    key: &GenesisAuthenticationKey,
    expected_trusted_head: GenesisTrustedHead,
) -> Result<VerifiedGenesisIdentity, GenesisError> {
    let record: &[u8; GENESIS_RECORD_BYTES] =
        record.try_into().map_err(|_| GenesisError::WrongLength)?;
    if trusted_head(record) != expected_trusted_head {
        return Err(GenesisError::TrustedHeadMismatch);
    }
    if &record[..8] != MAGIC {
        return Err(GenesisError::BadMagic);
    }

    let version = u16::from_le_bytes([record[8], record[9]]);
    if version != VERSION {
        return Err(GenesisError::UnsupportedVersion(version));
    }

    let record_epoch = u32::from_le_bytes([record[10], record[11], record[12], record[13]]);
    if record_epoch != key.epoch {
        return Err(GenesisError::KeyEpochMismatch);
    }

    let mut identity = [0_u8; 16];
    identity.copy_from_slice(&record[14..HEADER_BYTES]);
    validate_uuid_v4(identity)?;

    let mut verifier = HmacSha256::new_from_slice(key.bytes.as_ref())
        .expect("HMAC-SHA256 accepts every 32-byte key");
    verifier.update(AUTHENTICATION_DOMAIN);
    verifier.update(&record[..HEADER_BYTES]);
    verifier
        .verify_slice(&record[HEADER_BYTES..])
        .map_err(|_| GenesisError::AuthenticationFailed)?;

    Ok(VerifiedGenesisIdentity {
        identity,
        key_epoch: record_epoch,
        trusted_head: expected_trusted_head,
        authority_binding: capability_binding(key, expected_trusted_head),
    })
}

pub(crate) fn verify_global_owner_genesis(
    record: &[u8],
    global_owner: &SuppliedGlobalOwnerRootKey,
    expected_trusted_head: GenesisTrustedHead,
) -> Result<VerifiedGenesisIdentity, GenesisError> {
    let key = GenesisAuthenticationKey::from_zeroizing(
        global_owner.epoch(),
        global_owner.derive_genesis_authentication_key(),
    )?;
    verify_genesis_identity(record, &key, expected_trusted_head)
}

fn validate_uuid_v4(identity: [u8; 16]) -> Result<(), GenesisError> {
    if identity[6] >> 4 != 4 {
        return Err(GenesisError::InvalidUuidVersion);
    }
    if identity[8] & 0b1100_0000 != 0b1000_0000 {
        return Err(GenesisError::InvalidUuidVariant);
    }
    Ok(())
}

fn authentication_tag(
    key: &GenesisAuthenticationKey,
    authenticated_bytes: &[u8],
) -> [u8; TAG_BYTES] {
    let mut mac = HmacSha256::new_from_slice(key.bytes.as_ref())
        .expect("HMAC-SHA256 accepts every 32-byte key");
    mac.update(AUTHENTICATION_DOMAIN);
    mac.update(authenticated_bytes);
    let mut tag = [0_u8; TAG_BYTES];
    tag.copy_from_slice(&mac.finalize().into_bytes());
    tag
}

fn trusted_head(record: &[u8; GENESIS_RECORD_BYTES]) -> GenesisTrustedHead {
    let mut digest = Sha256::new();
    digest.update(TRUSTED_HEAD_DOMAIN);
    digest.update(record);
    let mut receipt = [0_u8; 32];
    receipt.copy_from_slice(&digest.finalize());
    GenesisTrustedHead(receipt)
}

fn capability_binding(
    key: &GenesisAuthenticationKey,
    trusted_head: GenesisTrustedHead,
) -> [u8; 32] {
    let mut binding = HmacSha256::new_from_slice(key.bytes.as_ref())
        .expect("HMAC-SHA256 accepts every 32-byte key");
    binding.update(CAPABILITY_BINDING_DOMAIN);
    binding.update(&key.epoch.to_le_bytes());
    binding.update(&trusted_head.0);
    binding.finalize().into_bytes().into()
}

fn verify_capability_binding(
    key: &GenesisAuthenticationKey,
    trusted_head: GenesisTrustedHead,
    binding: &[u8; 32],
) -> bool {
    let mut verifier = HmacSha256::new_from_slice(key.bytes.as_ref())
        .expect("HMAC-SHA256 accepts every 32-byte key");
    verifier.update(CAPABILITY_BINDING_DOMAIN);
    verifier.update(&key.epoch.to_le_bytes());
    verifier.update(&trusted_head.0);
    verifier.verify_slice(binding).is_ok()
}

#[cfg(test)]
mod tests {
    use super::*;

    const IDENTITY: [u8; 16] = [
        0x10, 0x53, 0x2f, 0x91, 0x7b, 0x2d, 0x4a, 0xc8, 0x98, 0x04, 0x46, 0x73, 0x5d, 0xa1, 0x28,
        0xfe,
    ];

    fn key(epoch: u32, byte: u8) -> GenesisAuthenticationKey {
        GenesisAuthenticationKey::new(epoch, [byte; 32]).expect("valid test key")
    }

    fn retag(
        record: &mut [u8; GENESIS_RECORD_BYTES],
        key: &GenesisAuthenticationKey,
    ) -> GenesisTrustedHead {
        let tag = authentication_tag(key, &record[..HEADER_BYTES]);
        record[HEADER_BYTES..].copy_from_slice(&tag);
        trusted_head(record)
    }

    #[test]
    fn exact_caller_identity_is_pinned_and_verified() {
        let key = key(7, 0x39);
        let first = authenticate_genesis_identity(IDENTITY, &key).expect("authenticate");
        let second = authenticate_genesis_identity(IDENTITY, &key).expect("repeat");
        assert_eq!(first.as_bytes(), second.as_bytes());
        assert_eq!(first.trusted_head(), second.trusted_head());

        let verified =
            verify_genesis_identity(first.as_bytes(), &key, first.trusted_head()).expect("verify");
        assert_eq!(verified.identity_bytes(), IDENTITY);
        assert_eq!(verified.key_epoch(), 7);
        assert_eq!(verified.trusted_head(), first.trusted_head());
    }

    #[test]
    fn sole_global_root_derives_and_verifies_v2_genesis() {
        let owner = SuppliedGlobalOwnerRootKey::new(9, [0x61; 32]).unwrap();
        let record = authenticate_global_owner_genesis(IDENTITY, &owner).unwrap();
        let verified =
            verify_global_owner_genesis(record.as_bytes(), &owner, record.trusted_head()).unwrap();
        assert_eq!(verified.identity_bytes(), IDENTITY);
        assert_eq!(verified.key_epoch(), owner.epoch());

        let wrong_root = SuppliedGlobalOwnerRootKey::new(9, [0x62; 32]).unwrap();
        assert_eq!(
            verify_global_owner_genesis(record.as_bytes(), &wrong_root, record.trusted_head())
                .err(),
            Some(GenesisError::AuthenticationFailed)
        );
        let wrong_epoch = SuppliedGlobalOwnerRootKey::new(10, [0x61; 32]).unwrap();
        assert_eq!(
            verify_global_owner_genesis(record.as_bytes(), &wrong_epoch, record.trusted_head())
                .err(),
            Some(GenesisError::KeyEpochMismatch)
        );
    }

    #[test]
    fn invalid_uuid_version_and_variant_are_rejected() {
        let key = key(1, 0x11);
        let mut wrong_version = IDENTITY;
        wrong_version[6] = (wrong_version[6] & 0x0f) | 0x50;
        assert_eq!(
            authenticate_genesis_identity(wrong_version, &key).err(),
            Some(GenesisError::InvalidUuidVersion)
        );

        let mut wrong_variant = IDENTITY;
        wrong_variant[8] &= 0x3f;
        assert_eq!(
            authenticate_genesis_identity(wrong_variant, &key).err(),
            Some(GenesisError::InvalidUuidVariant)
        );
    }

    #[test]
    fn malformed_lengths_fail_closed() {
        let key = key(2, 0x22);
        let record = authenticate_genesis_identity(IDENTITY, &key).expect("authenticate");
        let short = &record.as_bytes()[..GENESIS_RECORD_BYTES - 1];
        assert_eq!(
            verify_genesis_identity(short, &key, record.trusted_head()).err(),
            Some(GenesisError::WrongLength)
        );

        let mut long = record.as_bytes().to_vec();
        long.push(0);
        assert_eq!(
            verify_genesis_identity(&long, &key, record.trusted_head()).err(),
            Some(GenesisError::WrongLength)
        );
    }

    #[test]
    fn wrong_trusted_head_key_and_epoch_fail_closed() {
        let authentic_key = key(3, 0x33);
        let record = authenticate_genesis_identity(IDENTITY, &authentic_key).expect("authenticate");
        let other = authenticate_genesis_identity(IDENTITY, &key(3, 0x34))
            .expect("other authenticated record");
        assert_eq!(
            verify_genesis_identity(record.as_bytes(), &authentic_key, other.trusted_head()).err(),
            Some(GenesisError::TrustedHeadMismatch)
        );
        assert_eq!(
            verify_genesis_identity(record.as_bytes(), &key(3, 0x34), record.trusted_head()).err(),
            Some(GenesisError::AuthenticationFailed)
        );
        assert_eq!(
            verify_genesis_identity(record.as_bytes(), &key(4, 0x33), record.trusted_head()).err(),
            Some(GenesisError::KeyEpochMismatch)
        );
    }

    #[test]
    fn authenticated_noncanonical_header_fields_fail_closed() {
        let key = key(5, 0x55);
        let record = authenticate_genesis_identity(IDENTITY, &key).expect("authenticate");

        let mut bad_magic = *record.as_bytes();
        bad_magic[0] ^= 1;
        let head = retag(&mut bad_magic, &key);
        assert_eq!(
            verify_genesis_identity(&bad_magic, &key, head).err(),
            Some(GenesisError::BadMagic)
        );

        let mut bad_version = *record.as_bytes();
        bad_version[8..10].copy_from_slice(&1_u16.to_le_bytes());
        let head = retag(&mut bad_version, &key);
        assert_eq!(
            verify_genesis_identity(&bad_version, &key, head).err(),
            Some(GenesisError::UnsupportedVersion(1))
        );

        let mut bad_uuid = *record.as_bytes();
        bad_uuid[20] = (bad_uuid[20] & 0x0f) | 0x30;
        let head = retag(&mut bad_uuid, &key);
        assert_eq!(
            verify_genesis_identity(&bad_uuid, &key, head).err(),
            Some(GenesisError::InvalidUuidVersion)
        );

        let mut legacy_v1 = *record.as_bytes();
        legacy_v1[..8].copy_from_slice(b"GULGEN01");
        legacy_v1[8..10].copy_from_slice(&1_u16.to_le_bytes());
        let head = retag(&mut legacy_v1, &key);
        assert_eq!(
            verify_genesis_identity(&legacy_v1, &key, head).err(),
            Some(GenesisError::BadMagic)
        );
    }

    #[test]
    fn byte_mutation_cannot_be_accepted_under_a_recomputed_head() {
        let key = key(6, 0x66);
        let record = authenticate_genesis_identity(IDENTITY, &key).expect("authenticate");
        let mut mutated = *record.as_bytes();
        mutated[15] ^= 1;
        let forged_head = trusted_head(&mutated);
        assert_eq!(
            verify_genesis_identity(&mutated, &key, forged_head).err(),
            Some(GenesisError::AuthenticationFailed)
        );
    }

    #[test]
    fn zero_epoch_key_and_trusted_head_are_rejected() {
        assert!(matches!(
            GenesisAuthenticationKey::new(0, [1; 32]),
            Err(GenesisError::ZeroKeyEpoch)
        ));
        assert!(matches!(
            GenesisAuthenticationKey::new(1, [0; 32]),
            Err(GenesisError::ZeroKey)
        ));
        assert_eq!(
            GenesisTrustedHead::from_receipt([0; 32]).err(),
            Some(GenesisError::ZeroTrustedHead)
        );
    }
}
