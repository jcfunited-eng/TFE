//! Authenticated deployment facts bound to one explicitly supplied observation.
//!
//! The deployment envelope is authenticated by the one supplied global-owner
//! root. This module keeps the transport-only comparison explicitly named as
//! supplied; `platform_observer` is the sole production path that consumes it
//! behind a non-clonable one-shot native evidence capability. Production still
//! requires the native owner to invoke that path and live-verify it in Fargate.
//!
//! The record carries no work limits, recovery reserve, durable-storage ceiling,
//! or EFS free-space claim. Those values cannot be derived from task capacity.
//! In particular, EFS is elastic and its filesystem ID is not visible through
//! the Fargate kernel mount, so that ID remains a deployer attestation only.
//! Version one also attests the exact current EFS task-definition mode:
//! encrypted transit, no access point, and no EFS IAM authorization. Runtime
//! ephemeral reserve/utilization remain observed facts, separate from the
//! task-definition GiB setting, because Fargate reports additional reserve.

use super::wake_admission::SuppliedGlobalOwnerRootKey;
use hmac::{Hmac, Mac};
use sha2::{Digest, Sha256};
use std::fmt;

type HmacSha256 = Hmac<Sha256>;

const MAGIC: &[u8; 8] = b"GULPLT01";
const VERSION: u16 = 1;
const FLAG_EFS_TRANSIT_ENCRYPTION_ENABLED: u16 = 1;
const FLAG_EFS_ACCESS_POINT_ABSENT: u16 = 1 << 1;
const FLAG_EFS_IAM_AUTHORIZATION_DISABLED: u16 = 1 << 2;
const FLAGS: u16 = FLAG_EFS_TRANSIT_ENCRYPTION_ENABLED
    | FLAG_EFS_ACCESS_POINT_ABSENT
    | FLAG_EFS_IAM_AUTHORIZATION_DISABLED;
const DOMAIN: &[u8] = b"guala.native.platform-envelope.v1\0";
const RECEIPT_DOMAIN: &[u8] = b"guala.native.platform-envelope-receipt.v1\0";
const OBSERVATION_DOMAIN: &[u8] = b"guala.native.supplied-platform-observation.v1\0";
const FACT_DOMAIN: &[u8] = b"guala.native.platform-fact.v1\0";
const CANONICAL_AUTHORITY_ROOT: &[u8] = b"/app/guala";
const ZERO: [u8; 32] = [0; 32];
const RECEIPT_COUNT: usize = 11;
const PAYLOAD_BYTES: usize = (RECEIPT_COUNT * 32) + (3 * 4) + (2 * 8);
const HEADER_BYTES: usize = 8 + 2 + 2 + 4;
const TAG_BYTES: usize = 32;
const RECORD_BYTES: usize = HEADER_BYTES + TAG_BYTES + PAYLOAD_BYTES;
pub(super) const PLATFORM_ENVELOPE_RECORD_BYTES: usize = RECORD_BYTES;

#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) enum PlatformEnvelopeError {
    WrongLength,
    BadMagic,
    UnsupportedVersion,
    WrongFlags,
    PayloadLengthMismatch,
    AuthenticationFailed,
    InvalidEnvelope(&'static str),
    InvalidObservation(&'static str),
    ObservationMismatch(&'static str),
}

impl fmt::Display for PlatformEnvelopeError {
    fn fmt(&self, output: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::WrongLength => write!(output, "platform envelope length differs"),
            Self::BadMagic => write!(output, "platform envelope magic differs"),
            Self::UnsupportedVersion => write!(output, "platform envelope version differs"),
            Self::WrongFlags => write!(output, "platform envelope flags differ"),
            Self::PayloadLengthMismatch => write!(output, "platform payload length differs"),
            Self::AuthenticationFailed => write!(output, "platform envelope HMAC differs"),
            Self::InvalidEnvelope(name) => write!(output, "invalid platform envelope: {name}"),
            Self::InvalidObservation(name) => {
                write!(output, "invalid supplied platform observation: {name}")
            }
            Self::ObservationMismatch(name) => {
                write!(output, "platform observation differs: {name}")
            }
        }
    }
}

impl std::error::Error for PlatformEnvelopeError {}

struct AuthenticatedDeploymentEnvelope {
    aws_account_receipt: [u8; 32],
    region_receipt: [u8; 32],
    cluster_receipt: [u8; 32],
    service_receipt: [u8; 32],
    task_family_receipt: [u8; 32],
    app_container_receipt: [u8; 32],
    image_digest: [u8; 32],
    efs_filesystem_id_receipt: [u8; 32],
    efs_root_directory_receipt: [u8; 32],
    authority_root_receipt: [u8; 32],
    release_source_receipt: [u8; 32],
    global_owner_epoch: u32,
    task_revision: u32,
    task_cpu_millicores: u64,
    task_memory_bytes: u64,
    ephemeral_task_definition_gib: u32,
    receipt: [u8; 32],
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
#[repr(u8)]
pub(crate) enum PlatformFactKind {
    AwsAccount = 1,
    Region = 2,
    Cluster = 3,
    Service = 4,
    TaskFamily = 5,
    AppContainer = 6,
    EfsFilesystemId = 7,
    EfsRootDirectory = 8,
    AuthorityRoot = 9,
    ReleaseSource = 10,
    TaskArn = 11,
    CgroupCpuset = 12,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) enum SuppliedCgroupObservation {
    V1 {
        cpu_usage_nanoseconds: u64,
        memory_current_bytes: u64,
        leaf_cpu_quota_microseconds: Option<u64>,
        leaf_cpu_period_microseconds: u64,
        leaf_memory_limit_bytes: u64,
        hierarchical_memory_limit_bytes: Option<u64>,
        cpuset_receipt: [u8; 32],
        cpuset_cpu_count: u32,
    },
    V2 {
        cpu_usage_nanoseconds: u64,
        memory_current_bytes: u64,
        cpu_quota_microseconds: Option<u64>,
        cpu_period_microseconds: u64,
        memory_max_bytes: Option<u64>,
        cpuset_receipt: [u8; 32],
        cpuset_cpu_count: u32,
    },
}

/// Transport-unverified facts. Construction is confined to the organism
/// boundary; production consumers receive only the non-clonable native binding.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(super) struct SuppliedUnverifiedPlatformObservation {
    pub(super) task_arn_receipt: [u8; 32],
    pub(super) aws_account_receipt: [u8; 32],
    pub(super) region_receipt: [u8; 32],
    pub(super) cluster_receipt: [u8; 32],
    pub(super) service_receipt: [u8; 32],
    pub(super) task_family_receipt: [u8; 32],
    pub(super) app_container_receipt: [u8; 32],
    pub(super) authority_root_receipt: [u8; 32],
    pub(super) task_revision: u32,
    pub(super) image_digest: [u8; 32],
    pub(super) task_cpu_millicores: u64,
    pub(super) task_memory_bytes: u64,
    pub(super) ephemeral_reserved_bytes: u64,
    pub(super) ephemeral_utilized_bytes: u64,
    pub(super) launch_type_is_fargate: bool,
    pub(super) authority_mount_is_nfs_v4: bool,
    pub(super) efs_filesystem_id_is_kernel_observable: bool,
    pub(super) cgroup: SuppliedCgroupObservation,
}

/// Non-clonable result of HMAC verification plus exact consistency comparison
/// with a supplied report. It is not a physical-attestation capability.
pub(crate) struct AuthenticatedEnvelopeConsistentWithSuppliedReport {
    envelope: AuthenticatedDeploymentEnvelope,
    task_arn_receipt: [u8; 32],
    observation_receipt: [u8; 32],
    ephemeral_reserved_bytes: u64,
    ephemeral_utilized_bytes: u64,
    cgroup: SuppliedCgroupObservation,
}

impl AuthenticatedEnvelopeConsistentWithSuppliedReport {
    pub(crate) fn envelope_receipt(&self) -> [u8; 32] {
        self.envelope.receipt
    }

    pub(crate) fn task_arn_receipt(&self) -> [u8; 32] {
        self.task_arn_receipt
    }

    pub(crate) fn observation_receipt(&self) -> [u8; 32] {
        self.observation_receipt
    }

    pub(crate) fn task_cpu_millicores(&self) -> u64 {
        self.envelope.task_cpu_millicores
    }

    pub(crate) fn task_memory_bytes(&self) -> u64 {
        self.envelope.task_memory_bytes
    }

    /// Zero means the task definition omitted the setting and therefore uses
    /// the Fargate platform default. It is not a runtime reserved-byte value.
    pub(crate) fn deployer_attested_ephemeral_task_definition_gib(&self) -> u32 {
        self.envelope.ephemeral_task_definition_gib
    }

    pub(crate) fn reported_ephemeral_reserved_bytes(&self) -> u64 {
        self.ephemeral_reserved_bytes
    }

    pub(crate) fn reported_ephemeral_utilized_bytes(&self) -> u64 {
        self.ephemeral_utilized_bytes
    }

    /// Deployer attestation only; the Fargate NFS mount does not expose this ID.
    pub(crate) fn deployer_attested_efs_filesystem_id_receipt(&self) -> [u8; 32] {
        self.envelope.efs_filesystem_id_receipt
    }

    pub(crate) fn deployer_attested_efs_root_directory_receipt(&self) -> [u8; 32] {
        self.envelope.efs_root_directory_receipt
    }

    /// Version one describes the exact production EFS configuration: encrypted
    /// transit, no access point, and no EFS IAM authorization mode.
    pub(crate) fn deployer_attested_efs_transit_encryption_enabled(&self) -> bool {
        true
    }

    pub(crate) fn deployer_attested_efs_access_point_is_absent(&self) -> bool {
        true
    }

    pub(crate) fn deployer_attested_efs_iam_authorization_enabled(&self) -> bool {
        false
    }

    pub(crate) fn service_receipt(&self) -> [u8; 32] {
        self.envelope.service_receipt
    }

    /// Deployer attestation only; a running task cannot establish its source
    /// revision independently from the image selected by the platform.
    pub(crate) fn deployer_attested_release_source_receipt(&self) -> [u8; 32] {
        self.envelope.release_source_receipt
    }

    pub(crate) fn cgroup(&self) -> SuppliedCgroupObservation {
        self.cgroup
    }
}

pub(super) fn authenticate_and_bind_supplied_platform_observation(
    record: &[u8],
    global_owner: &SuppliedGlobalOwnerRootKey,
    observation: SuppliedUnverifiedPlatformObservation,
) -> Result<AuthenticatedEnvelopeConsistentWithSuppliedReport, PlatformEnvelopeError> {
    let envelope = authenticate(record, global_owner)?;
    validate_observation(observation)?;
    compare(&envelope, observation)?;
    Ok(AuthenticatedEnvelopeConsistentWithSuppliedReport {
        envelope,
        task_arn_receipt: observation.task_arn_receipt,
        observation_receipt: observation_receipt(observation),
        ephemeral_reserved_bytes: observation.ephemeral_reserved_bytes,
        ephemeral_utilized_bytes: observation.ephemeral_utilized_bytes,
        cgroup: observation.cgroup,
    })
}

fn authenticate(
    record: &[u8],
    global_owner: &SuppliedGlobalOwnerRootKey,
) -> Result<AuthenticatedDeploymentEnvelope, PlatformEnvelopeError> {
    if record.len() != RECORD_BYTES {
        return Err(PlatformEnvelopeError::WrongLength);
    }
    if &record[..8] != MAGIC {
        return Err(PlatformEnvelopeError::BadMagic);
    }
    if u16::from_le_bytes(record[8..10].try_into().expect("fixed version")) != VERSION {
        return Err(PlatformEnvelopeError::UnsupportedVersion);
    }
    if u16::from_le_bytes(record[10..12].try_into().expect("fixed flags")) != FLAGS {
        return Err(PlatformEnvelopeError::WrongFlags);
    }
    if u32::from_le_bytes(record[12..16].try_into().expect("fixed length")) as usize
        != PAYLOAD_BYTES
    {
        return Err(PlatformEnvelopeError::PayloadLengthMismatch);
    }
    let key = global_owner.derive_platform_envelope_key();
    let mut hmac =
        HmacSha256::new_from_slice(key.as_ref()).expect("HMAC-SHA256 accepts every 32-byte key");
    hmac.update(DOMAIN);
    hmac.update(&record[..HEADER_BYTES]);
    hmac.update(&record[HEADER_BYTES + TAG_BYTES..]);
    hmac.verify_slice(&record[HEADER_BYTES..HEADER_BYTES + TAG_BYTES])
        .map_err(|_| PlatformEnvelopeError::AuthenticationFailed)?;

    let mut input = FixedDecoder::new(&record[HEADER_BYTES + TAG_BYTES..]);
    let envelope = AuthenticatedDeploymentEnvelope {
        aws_account_receipt: input.receipt(),
        region_receipt: input.receipt(),
        cluster_receipt: input.receipt(),
        service_receipt: input.receipt(),
        task_family_receipt: input.receipt(),
        app_container_receipt: input.receipt(),
        image_digest: input.receipt(),
        efs_filesystem_id_receipt: input.receipt(),
        efs_root_directory_receipt: input.receipt(),
        authority_root_receipt: input.receipt(),
        release_source_receipt: input.receipt(),
        global_owner_epoch: input.u32(),
        task_revision: input.u32(),
        task_cpu_millicores: input.u64(),
        task_memory_bytes: input.u64(),
        ephemeral_task_definition_gib: input.u32(),
        receipt: domain_digest(RECEIPT_DOMAIN, record),
    };
    validate_envelope(&envelope)?;
    if envelope.global_owner_epoch != global_owner.epoch() {
        return Err(PlatformEnvelopeError::InvalidEnvelope(
            "global owner epoch differs",
        ));
    }
    Ok(envelope)
}

fn validate_envelope(value: &AuthenticatedDeploymentEnvelope) -> Result<(), PlatformEnvelopeError> {
    for (receipt, kind, name) in [
        (
            value.aws_account_receipt,
            PlatformFactKind::AwsAccount,
            "AWS account receipt",
        ),
        (
            value.region_receipt,
            PlatformFactKind::Region,
            "region receipt",
        ),
        (
            value.cluster_receipt,
            PlatformFactKind::Cluster,
            "cluster receipt",
        ),
        (
            value.service_receipt,
            PlatformFactKind::Service,
            "service receipt",
        ),
        (
            value.task_family_receipt,
            PlatformFactKind::TaskFamily,
            "task family receipt",
        ),
        (
            value.app_container_receipt,
            PlatformFactKind::AppContainer,
            "app container receipt",
        ),
        (
            value.efs_filesystem_id_receipt,
            PlatformFactKind::EfsFilesystemId,
            "EFS filesystem receipt",
        ),
        (
            value.efs_root_directory_receipt,
            PlatformFactKind::EfsRootDirectory,
            "EFS root receipt",
        ),
        (
            value.authority_root_receipt,
            PlatformFactKind::AuthorityRoot,
            "authority root receipt",
        ),
        (
            value.release_source_receipt,
            PlatformFactKind::ReleaseSource,
            "release source receipt",
        ),
    ] {
        if receipt == ZERO || receipt == canonical_platform_fact_receipt(kind, b"") {
            return Err(PlatformEnvelopeError::InvalidEnvelope(name));
        }
    }
    if value.image_digest == ZERO {
        return Err(PlatformEnvelopeError::InvalidEnvelope("image digest"));
    }
    if value.task_revision == 0 {
        return Err(PlatformEnvelopeError::InvalidEnvelope("task revision"));
    }
    if value.task_cpu_millicores == 0 {
        return Err(PlatformEnvelopeError::InvalidEnvelope("task CPU"));
    }
    if value.task_memory_bytes == 0 {
        return Err(PlatformEnvelopeError::InvalidEnvelope("task memory"));
    }
    if value.ephemeral_task_definition_gib != 0
        && !(21..=200).contains(&value.ephemeral_task_definition_gib)
    {
        return Err(PlatformEnvelopeError::InvalidEnvelope(
            "Fargate ephemeral task-definition GiB",
        ));
    }
    if value.authority_root_receipt
        != canonical_platform_fact_receipt(
            PlatformFactKind::AuthorityRoot,
            CANONICAL_AUTHORITY_ROOT,
        )
    {
        return Err(PlatformEnvelopeError::InvalidEnvelope(
            "authority root is not /app/guala",
        ));
    }
    Ok(())
}

fn validate_observation(
    value: SuppliedUnverifiedPlatformObservation,
) -> Result<(), PlatformEnvelopeError> {
    for (receipt, kind, name) in [
        (
            value.task_arn_receipt,
            PlatformFactKind::TaskArn,
            "task ARN receipt",
        ),
        (
            value.aws_account_receipt,
            PlatformFactKind::AwsAccount,
            "AWS account receipt",
        ),
        (
            value.region_receipt,
            PlatformFactKind::Region,
            "region receipt",
        ),
        (
            value.cluster_receipt,
            PlatformFactKind::Cluster,
            "cluster receipt",
        ),
        (
            value.service_receipt,
            PlatformFactKind::Service,
            "service receipt",
        ),
        (
            value.task_family_receipt,
            PlatformFactKind::TaskFamily,
            "task family receipt",
        ),
        (
            value.app_container_receipt,
            PlatformFactKind::AppContainer,
            "app container receipt",
        ),
        (
            value.authority_root_receipt,
            PlatformFactKind::AuthorityRoot,
            "authority root receipt",
        ),
    ] {
        if receipt == ZERO || receipt == canonical_platform_fact_receipt(kind, b"") {
            return Err(PlatformEnvelopeError::InvalidObservation(name));
        }
    }
    if value.image_digest == ZERO {
        return Err(PlatformEnvelopeError::InvalidObservation("image digest"));
    }
    if value.authority_root_receipt
        != canonical_platform_fact_receipt(
            PlatformFactKind::AuthorityRoot,
            CANONICAL_AUTHORITY_ROOT,
        )
    {
        return Err(PlatformEnvelopeError::InvalidObservation(
            "authority root is not /app/guala",
        ));
    }
    if value.task_revision == 0
        || value.task_cpu_millicores == 0
        || value.task_memory_bytes == 0
        || value.ephemeral_reserved_bytes == 0
    {
        return Err(PlatformEnvelopeError::InvalidObservation(
            "zero task capacity or revision",
        ));
    }
    if value.ephemeral_utilized_bytes > value.ephemeral_reserved_bytes {
        return Err(PlatformEnvelopeError::InvalidObservation(
            "ephemeral utilization exceeds reserve",
        ));
    }
    if !value.launch_type_is_fargate {
        return Err(PlatformEnvelopeError::InvalidObservation(
            "launch type is not Fargate",
        ));
    }
    if !value.authority_mount_is_nfs_v4 {
        return Err(PlatformEnvelopeError::InvalidObservation(
            "authority root is not NFSv4",
        ));
    }
    if value.efs_filesystem_id_is_kernel_observable {
        return Err(PlatformEnvelopeError::InvalidObservation(
            "kernel observation falsely claims an EFS filesystem ID",
        ));
    }
    match value.cgroup {
        SuppliedCgroupObservation::V1 {
            leaf_cpu_quota_microseconds,
            leaf_cpu_period_microseconds,
            leaf_memory_limit_bytes,
            hierarchical_memory_limit_bytes,
            cpuset_receipt,
            cpuset_cpu_count,
            ..
        } => {
            if leaf_cpu_quota_microseconds == Some(0)
                || leaf_cpu_period_microseconds == 0
                || leaf_memory_limit_bytes == 0
                || hierarchical_memory_limit_bytes == Some(0)
                || cpuset_receipt == ZERO
                || cpuset_receipt
                    == canonical_platform_fact_receipt(PlatformFactKind::CgroupCpuset, b"")
                || cpuset_cpu_count == 0
            {
                return Err(PlatformEnvelopeError::InvalidObservation(
                    "invalid cgroup v1 facts",
                ));
            }
        }
        SuppliedCgroupObservation::V2 {
            cpu_quota_microseconds,
            cpu_period_microseconds,
            memory_max_bytes,
            cpuset_receipt,
            cpuset_cpu_count,
            ..
        } => {
            if cpu_period_microseconds == 0
                || cpu_quota_microseconds == Some(0)
                || memory_max_bytes == Some(0)
                || cpuset_receipt == ZERO
                || cpuset_receipt
                    == canonical_platform_fact_receipt(PlatformFactKind::CgroupCpuset, b"")
                || cpuset_cpu_count == 0
            {
                return Err(PlatformEnvelopeError::InvalidObservation(
                    "invalid cgroup v2 facts",
                ));
            }
        }
    }
    Ok(())
}

fn compare(
    expected: &AuthenticatedDeploymentEnvelope,
    actual: SuppliedUnverifiedPlatformObservation,
) -> Result<(), PlatformEnvelopeError> {
    for (matches, name) in [
        (
            expected.aws_account_receipt == actual.aws_account_receipt,
            "AWS account",
        ),
        (expected.region_receipt == actual.region_receipt, "region"),
        (
            expected.cluster_receipt == actual.cluster_receipt,
            "cluster",
        ),
        (
            expected.service_receipt == actual.service_receipt,
            "service",
        ),
        (
            expected.task_family_receipt == actual.task_family_receipt,
            "task family",
        ),
        (
            expected.app_container_receipt == actual.app_container_receipt,
            "app container",
        ),
        (
            expected.authority_root_receipt == actual.authority_root_receipt,
            "authority root",
        ),
        (expected.image_digest == actual.image_digest, "image digest"),
        (
            expected.task_revision == actual.task_revision,
            "task revision",
        ),
        (
            expected.task_cpu_millicores == actual.task_cpu_millicores,
            "task CPU",
        ),
        (
            expected.task_memory_bytes == actual.task_memory_bytes,
            "task memory",
        ),
    ] {
        if !matches {
            return Err(PlatformEnvelopeError::ObservationMismatch(name));
        }
    }
    Ok(())
}

/// Canonical, allocation-free receipt shared by the deployment signer and the
/// later native reader. The fact discriminant prevents receipts from being
/// moved between fields. Bytes are exact: there is no case folding, path
/// normalization, Unicode normalization, or compatibility alias.
pub(crate) fn canonical_platform_fact_receipt(
    kind: PlatformFactKind,
    exact_bytes: &[u8],
) -> [u8; 32] {
    let mut digest = Sha256::new();
    digest.update(FACT_DOMAIN);
    digest.update([kind as u8]);
    digest.update((exact_bytes.len() as u64).to_le_bytes());
    digest.update(exact_bytes);
    digest.finalize().into()
}

fn observation_receipt(value: SuppliedUnverifiedPlatformObservation) -> [u8; 32] {
    let mut digest = Sha256::new();
    digest.update(OBSERVATION_DOMAIN);
    for receipt in [
        value.task_arn_receipt,
        value.aws_account_receipt,
        value.region_receipt,
        value.cluster_receipt,
        value.service_receipt,
        value.task_family_receipt,
        value.app_container_receipt,
        value.authority_root_receipt,
        value.image_digest,
    ] {
        digest.update(receipt);
    }
    digest.update(value.task_revision.to_le_bytes());
    digest.update(value.task_cpu_millicores.to_le_bytes());
    digest.update(value.task_memory_bytes.to_le_bytes());
    digest.update(value.ephemeral_reserved_bytes.to_le_bytes());
    digest.update(value.ephemeral_utilized_bytes.to_le_bytes());
    digest.update([
        value.launch_type_is_fargate as u8,
        value.authority_mount_is_nfs_v4 as u8,
        value.efs_filesystem_id_is_kernel_observable as u8,
    ]);
    match value.cgroup {
        SuppliedCgroupObservation::V1 {
            cpu_usage_nanoseconds,
            memory_current_bytes,
            leaf_cpu_quota_microseconds,
            leaf_cpu_period_microseconds,
            leaf_memory_limit_bytes,
            hierarchical_memory_limit_bytes,
            cpuset_receipt,
            cpuset_cpu_count,
        } => {
            digest.update([1]);
            digest.update(cpu_usage_nanoseconds.to_le_bytes());
            digest.update(memory_current_bytes.to_le_bytes());
            digest_option(&mut digest, leaf_cpu_quota_microseconds);
            digest.update(leaf_cpu_period_microseconds.to_le_bytes());
            digest.update(leaf_memory_limit_bytes.to_le_bytes());
            digest_option(&mut digest, hierarchical_memory_limit_bytes);
            digest.update(cpuset_receipt);
            digest.update(cpuset_cpu_count.to_le_bytes());
        }
        SuppliedCgroupObservation::V2 {
            cpu_usage_nanoseconds,
            memory_current_bytes,
            cpu_quota_microseconds,
            cpu_period_microseconds,
            memory_max_bytes,
            cpuset_receipt,
            cpuset_cpu_count,
        } => {
            digest.update([2]);
            digest.update(cpu_usage_nanoseconds.to_le_bytes());
            digest.update(memory_current_bytes.to_le_bytes());
            digest_option(&mut digest, cpu_quota_microseconds);
            digest.update(cpu_period_microseconds.to_le_bytes());
            digest_option(&mut digest, memory_max_bytes);
            digest.update(cpuset_receipt);
            digest.update(cpuset_cpu_count.to_le_bytes());
        }
    }
    digest.finalize().into()
}

fn digest_option(digest: &mut Sha256, value: Option<u64>) {
    digest.update([value.is_some() as u8]);
    digest.update(value.unwrap_or_default().to_le_bytes());
}

fn domain_digest(domain: &[u8], body: &[u8]) -> [u8; 32] {
    let mut digest = Sha256::new();
    digest.update(domain);
    digest.update(body);
    digest.finalize().into()
}

struct FixedDecoder<'a> {
    bytes: &'a [u8],
    offset: usize,
}

impl<'a> FixedDecoder<'a> {
    fn new(bytes: &'a [u8]) -> Self {
        Self { bytes, offset: 0 }
    }

    fn receipt(&mut self) -> [u8; 32] {
        let end = self.offset + 32;
        let value = self.bytes[self.offset..end]
            .try_into()
            .expect("fixed payload");
        self.offset = end;
        value
    }

    fn u32(&mut self) -> u32 {
        let end = self.offset + 4;
        let value = u32::from_le_bytes(self.bytes[self.offset..end].try_into().expect("fixed u32"));
        self.offset = end;
        value
    }

    fn u64(&mut self) -> u64 {
        let end = self.offset + 8;
        let value = u64::from_le_bytes(self.bytes[self.offset..end].try_into().expect("fixed u64"));
        self.offset = end;
        value
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    const ROOT: [u8; 32] = [0x71; 32];

    fn receipt(value: u8) -> [u8; 32] {
        [value; 32]
    }

    fn fact(kind: PlatformFactKind, value: &str) -> [u8; 32] {
        canonical_platform_fact_receipt(kind, value.as_bytes())
    }

    fn payload() -> Vec<u8> {
        let mut value = Vec::new();
        for item in [
            fact(PlatformFactKind::AwsAccount, "418384447921"),
            fact(PlatformFactKind::Region, "us-east-1"),
            fact(PlatformFactKind::Cluster, "tfe-web-cluster"),
            fact(PlatformFactKind::Service, "dsf-ai-service-lb"),
            fact(PlatformFactKind::TaskFamily, "dsf-ai-task"),
            fact(PlatformFactKind::AppContainer, "dsf-ai"),
            receipt(7),
            fact(PlatformFactKind::EfsFilesystemId, "fs-0abb85854a3251b3c"),
            fact(PlatformFactKind::EfsRootDirectory, "/"),
            fact(PlatformFactKind::AuthorityRoot, "/app/guala"),
            fact(PlatformFactKind::ReleaseSource, "0123456789abcdef"),
        ] {
            value.extend_from_slice(&item);
        }
        value.extend_from_slice(&1_u32.to_le_bytes());
        value.extend_from_slice(&842_u32.to_le_bytes());
        value.extend_from_slice(&4_000_u64.to_le_bytes());
        value.extend_from_slice(&(16_u64 * 1024 * 1024 * 1024).to_le_bytes());
        value.extend_from_slice(&0_u32.to_le_bytes());
        assert_eq!(value.len(), PAYLOAD_BYTES);
        value
    }

    fn record(payload: &[u8]) -> Vec<u8> {
        record_with_owner(payload, 1, ROOT)
    }

    fn payload_with_ephemeral_task_definition_gib(value: u32) -> Vec<u8> {
        let mut body = payload();
        let offset = PAYLOAD_BYTES - 4;
        body[offset..].copy_from_slice(&value.to_le_bytes());
        body
    }

    fn record_with_owner(payload: &[u8], epoch: u32, root: [u8; 32]) -> Vec<u8> {
        let mut value = Vec::new();
        value.extend_from_slice(MAGIC);
        value.extend_from_slice(&VERSION.to_le_bytes());
        value.extend_from_slice(&FLAGS.to_le_bytes());
        value.extend_from_slice(&(payload.len() as u32).to_le_bytes());
        let owner = SuppliedGlobalOwnerRootKey::new(epoch, root).unwrap();
        let key = owner.derive_platform_envelope_key();
        let mut hmac = HmacSha256::new_from_slice(key.as_ref()).unwrap();
        hmac.update(DOMAIN);
        hmac.update(&value);
        hmac.update(payload);
        value.extend_from_slice(&hmac.finalize().into_bytes());
        value.extend_from_slice(payload);
        value
    }

    fn observation() -> SuppliedUnverifiedPlatformObservation {
        SuppliedUnverifiedPlatformObservation {
            task_arn_receipt: fact(
                PlatformFactKind::TaskArn,
                "arn:aws:ecs:us-east-1:418384447921:task/example",
            ),
            aws_account_receipt: fact(PlatformFactKind::AwsAccount, "418384447921"),
            region_receipt: fact(PlatformFactKind::Region, "us-east-1"),
            cluster_receipt: fact(PlatformFactKind::Cluster, "tfe-web-cluster"),
            service_receipt: fact(PlatformFactKind::Service, "dsf-ai-service-lb"),
            task_family_receipt: fact(PlatformFactKind::TaskFamily, "dsf-ai-task"),
            app_container_receipt: fact(PlatformFactKind::AppContainer, "dsf-ai"),
            image_digest: receipt(7),
            authority_root_receipt: fact(PlatformFactKind::AuthorityRoot, "/app/guala"),
            task_revision: 842,
            task_cpu_millicores: 4_000,
            task_memory_bytes: 16 * 1024 * 1024 * 1024,
            ephemeral_reserved_bytes: 20 * 1024 * 1024 * 1024,
            ephemeral_utilized_bytes: 1_500 * 1024 * 1024,
            launch_type_is_fargate: true,
            authority_mount_is_nfs_v4: true,
            efs_filesystem_id_is_kernel_observable: false,
            cgroup: SuppliedCgroupObservation::V1 {
                cpu_usage_nanoseconds: 15,
                memory_current_bytes: 2_300_000_000,
                leaf_cpu_quota_microseconds: None,
                leaf_cpu_period_microseconds: 100_000,
                leaf_memory_limit_bytes: 9_223_372_036_854_771_712,
                hierarchical_memory_limit_bytes: Some(16 * 1024 * 1024 * 1024),
                cpuset_receipt: fact(PlatformFactKind::CgroupCpuset, "0-3"),
                cpuset_cpu_count: 4,
            },
        }
    }

    fn bind(
        bytes: &[u8],
        supplied: SuppliedUnverifiedPlatformObservation,
    ) -> Result<AuthenticatedEnvelopeConsistentWithSuppliedReport, PlatformEnvelopeError> {
        authenticate_and_bind_supplied_platform_observation(
            bytes,
            &SuppliedGlobalOwnerRootKey::new(1, ROOT).unwrap(),
            supplied,
        )
    }

    fn binding_error(
        result: Result<AuthenticatedEnvelopeConsistentWithSuppliedReport, PlatformEnvelopeError>,
    ) -> PlatformEnvelopeError {
        match result {
            Ok(_) => panic!("platform binding unexpectedly succeeded"),
            Err(error) => error,
        }
    }

    #[test]
    fn exact_envelope_binds_supplied_fargate_observation_without_policy_caps() {
        let verified = bind(&record(&payload()), observation()).unwrap();
        assert_eq!(verified.task_cpu_millicores(), 4_000);
        assert_eq!(verified.task_memory_bytes(), 16 * 1024 * 1024 * 1024);
        assert_eq!(
            verified.deployer_attested_ephemeral_task_definition_gib(),
            0
        );
        assert_eq!(
            verified.reported_ephemeral_reserved_bytes(),
            20 * 1024 * 1024 * 1024
        );
        assert_eq!(
            verified.reported_ephemeral_utilized_bytes(),
            1_500 * 1024 * 1024
        );
        assert_eq!(
            verified.deployer_attested_efs_filesystem_id_receipt(),
            fact(PlatformFactKind::EfsFilesystemId, "fs-0abb85854a3251b3c")
        );
        assert_eq!(
            verified.deployer_attested_efs_root_directory_receipt(),
            fact(PlatformFactKind::EfsRootDirectory, "/")
        );
        assert!(verified.deployer_attested_efs_transit_encryption_enabled());
        assert!(verified.deployer_attested_efs_access_point_is_absent());
        assert!(!verified.deployer_attested_efs_iam_authorization_enabled());
        assert_eq!(
            verified.service_receipt(),
            fact(PlatformFactKind::Service, "dsf-ai-service-lb")
        );
        assert_eq!(
            verified.deployer_attested_release_source_receipt(),
            fact(PlatformFactKind::ReleaseSource, "0123456789abcdef")
        );
        assert_ne!(verified.envelope_receipt(), ZERO);
        assert_ne!(verified.observation_receipt(), ZERO);
    }

    #[test]
    fn authentication_precedes_payload_validation() {
        let mut bytes = record(&payload());
        *bytes.last_mut().unwrap() ^= 1;
        assert_eq!(
            binding_error(bind(&bytes, observation())),
            PlatformEnvelopeError::AuthenticationFailed
        );
    }

    #[test]
    fn wrong_root_and_wrong_owner_epoch_fail_closed() {
        let canonical = record(&payload());
        assert_eq!(
            authenticate_and_bind_supplied_platform_observation(
                &canonical,
                &SuppliedGlobalOwnerRootKey::new(1, [0x72; 32]).unwrap(),
                observation(),
            )
            .err()
            .expect("wrong root must fail"),
            PlatformEnvelopeError::AuthenticationFailed
        );

        let signed_by_epoch_two = record_with_owner(&payload(), 2, ROOT);
        assert_eq!(
            authenticate_and_bind_supplied_platform_observation(
                &signed_by_epoch_two,
                &SuppliedGlobalOwnerRootKey::new(2, ROOT).unwrap(),
                observation(),
            )
            .err()
            .expect("payload epoch must match root epoch"),
            PlatformEnvelopeError::InvalidEnvelope("global owner epoch differs")
        );
    }

    #[test]
    fn canonical_fact_receipts_are_field_and_byte_exact() {
        assert_ne!(
            fact(PlatformFactKind::Cluster, "same"),
            fact(PlatformFactKind::Service, "same")
        );
        assert_ne!(
            fact(PlatformFactKind::AuthorityRoot, "/app/guala"),
            fact(PlatformFactKind::AuthorityRoot, "/app/guala/")
        );

        let mut body = payload();
        let authority_offset = 9 * 32;
        body[authority_offset..authority_offset + 32]
            .copy_from_slice(&fact(PlatformFactKind::AuthorityRoot, "/app/not-guala"));
        assert!(matches!(
            bind(&record(&body), observation()),
            Err(PlatformEnvelopeError::InvalidEnvelope(
                "authority root is not /app/guala"
            ))
        ));
    }

    #[test]
    fn fargate_ephemeral_task_definition_setting_is_exact() {
        for invalid in [1, 20, 201, u32::MAX] {
            let body = payload_with_ephemeral_task_definition_gib(invalid);
            assert!(matches!(
                bind(&record(&body), observation()),
                Err(PlatformEnvelopeError::InvalidEnvelope(
                    "Fargate ephemeral task-definition GiB"
                ))
            ));
        }
        for accepted in [0, 21, 200] {
            let body = payload_with_ephemeral_task_definition_gib(accepted);
            assert_eq!(
                bind(&record(&body), observation())
                    .unwrap()
                    .deployer_attested_ephemeral_task_definition_gib(),
                accepted
            );
        }
    }

    #[test]
    fn truncation_trailing_wrong_magic_version_flags_and_length_fail() {
        let canonical = record(&payload());
        assert_eq!(
            binding_error(bind(&canonical[..canonical.len() - 1], observation())),
            PlatformEnvelopeError::WrongLength
        );
        let mut trailing = canonical.clone();
        trailing.push(0);
        assert_eq!(
            binding_error(bind(&trailing, observation())),
            PlatformEnvelopeError::WrongLength
        );
        for (index, expected) in [
            (0, PlatformEnvelopeError::BadMagic),
            (8, PlatformEnvelopeError::UnsupportedVersion),
            (10, PlatformEnvelopeError::WrongFlags),
            (12, PlatformEnvelopeError::PayloadLengthMismatch),
        ] {
            let mut bytes = canonical.clone();
            bytes[index] ^= 1;
            assert_eq!(binding_error(bind(&bytes, observation())), expected);
        }
    }

    #[test]
    fn every_observable_envelope_fact_must_match() {
        let bytes = record(&payload());
        let mutations: &[fn(&mut SuppliedUnverifiedPlatformObservation)] = &[
            |v| v.aws_account_receipt[0] ^= 1,
            |v| v.region_receipt[0] ^= 1,
            |v| v.cluster_receipt[0] ^= 1,
            |v| v.service_receipt[0] ^= 1,
            |v| v.task_family_receipt[0] ^= 1,
            |v| v.app_container_receipt[0] ^= 1,
            |v| v.image_digest[0] ^= 1,
            |v| v.task_revision += 1,
            |v| v.task_cpu_millicores += 1,
            |v| v.task_memory_bytes += 1,
        ];
        for mutate in mutations {
            let mut value = observation();
            mutate(&mut value);
            assert!(matches!(
                bind(&bytes, value),
                Err(PlatformEnvelopeError::ObservationMismatch(_))
            ));
        }
    }

    #[test]
    fn runtime_ephemeral_report_is_not_conflated_with_task_definition_setting() {
        let bytes = record(&payload());
        let first = bind(&bytes, observation()).unwrap();
        let first_receipt = first.observation_receipt();

        let mut changed_runtime_report = observation();
        changed_runtime_report.ephemeral_reserved_bytes = 20_496 * 1024 * 1024;
        changed_runtime_report.ephemeral_utilized_bytes = 1_478 * 1024 * 1024;
        let second = bind(&bytes, changed_runtime_report).unwrap();
        assert_eq!(second.deployer_attested_ephemeral_task_definition_gib(), 0);
        assert_ne!(second.observation_receipt(), first_receipt);

        let mut changed_task = observation();
        changed_task.task_arn_receipt = fact(
            PlatformFactKind::TaskArn,
            "arn:aws:ecs:us-east-1:418384447921:task/another",
        );
        let third = bind(&bytes, changed_task).unwrap();
        assert_ne!(third.task_arn_receipt(), first.task_arn_receipt());
        assert_ne!(third.observation_receipt(), first_receipt);
    }

    #[test]
    fn zero_envelope_receipts_and_capacities_are_rejected_after_hmac() {
        let fixed_values = [
            (RECEIPT_COUNT * 32, 4),
            ((RECEIPT_COUNT * 32) + 4, 4),
            ((RECEIPT_COUNT * 32) + 8, 8),
            ((RECEIPT_COUNT * 32) + 16, 8),
        ];
        for (offset, width) in (0..RECEIPT_COUNT)
            .map(|index| (index * 32, 32))
            .chain(fixed_values)
        {
            let mut body = payload();
            body[offset..offset + width].fill(0);
            assert!(matches!(
                bind(&record(&body), observation()),
                Err(PlatformEnvelopeError::InvalidEnvelope(_))
            ));
        }
    }

    #[test]
    fn invalid_supplied_transport_facts_are_rejected() {
        let bytes = record(&payload());
        let mut value = observation();
        value.authority_root_receipt = fact(PlatformFactKind::AuthorityRoot, "/app/not-guala");
        assert!(matches!(
            bind(&bytes, value),
            Err(PlatformEnvelopeError::InvalidObservation(_))
        ));
        let mut value = observation();
        value.ephemeral_utilized_bytes = value.ephemeral_reserved_bytes + 1;
        assert!(matches!(
            bind(&bytes, value),
            Err(PlatformEnvelopeError::InvalidObservation(_))
        ));
        let mut value = observation();
        value.launch_type_is_fargate = false;
        assert!(matches!(
            bind(&bytes, value),
            Err(PlatformEnvelopeError::InvalidObservation(_))
        ));
        let mut value = observation();
        value.authority_mount_is_nfs_v4 = false;
        assert!(matches!(
            bind(&bytes, value),
            Err(PlatformEnvelopeError::InvalidObservation(_))
        ));
        let mut value = observation();
        value.efs_filesystem_id_is_kernel_observable = true;
        assert!(matches!(
            bind(&bytes, value),
            Err(PlatformEnvelopeError::InvalidObservation(_))
        ));
    }

    #[test]
    fn zero_supplied_identity_and_capacity_facts_are_rejected() {
        let bytes = record(&payload());
        let receipt_mutations: &[fn(&mut SuppliedUnverifiedPlatformObservation)] = &[
            |v| v.task_arn_receipt = ZERO,
            |v| v.aws_account_receipt = ZERO,
            |v| v.region_receipt = ZERO,
            |v| v.cluster_receipt = ZERO,
            |v| v.service_receipt = ZERO,
            |v| v.task_family_receipt = ZERO,
            |v| v.app_container_receipt = ZERO,
            |v| v.authority_root_receipt = ZERO,
            |v| v.image_digest = ZERO,
        ];
        for mutate in receipt_mutations {
            let mut value = observation();
            mutate(&mut value);
            assert!(matches!(
                bind(&bytes, value),
                Err(PlatformEnvelopeError::InvalidObservation(_))
            ));
        }

        let capacity_mutations: &[fn(&mut SuppliedUnverifiedPlatformObservation)] = &[
            |v| v.task_revision = 0,
            |v| v.task_cpu_millicores = 0,
            |v| v.task_memory_bytes = 0,
            |v| v.ephemeral_reserved_bytes = 0,
        ];
        for mutate in capacity_mutations {
            let mut value = observation();
            mutate(&mut value);
            assert!(matches!(
                bind(&bytes, value),
                Err(PlatformEnvelopeError::InvalidObservation(_))
            ));
        }
    }

    #[test]
    fn invalid_cgroup_v1_and_v2_facts_are_rejected() {
        let bytes = record(&payload());
        for cgroup in [
            SuppliedCgroupObservation::V1 {
                cpu_usage_nanoseconds: 15,
                memory_current_bytes: 2_300_000_000,
                leaf_cpu_quota_microseconds: Some(0),
                leaf_cpu_period_microseconds: 100_000,
                leaf_memory_limit_bytes: 9_223_372_036_854_771_712,
                hierarchical_memory_limit_bytes: None,
                cpuset_receipt: fact(PlatformFactKind::CgroupCpuset, "0-3"),
                cpuset_cpu_count: 4,
            },
            SuppliedCgroupObservation::V1 {
                cpu_usage_nanoseconds: 15,
                memory_current_bytes: 2_300_000_000,
                leaf_cpu_quota_microseconds: None,
                leaf_cpu_period_microseconds: 0,
                leaf_memory_limit_bytes: 9_223_372_036_854_771_712,
                hierarchical_memory_limit_bytes: None,
                cpuset_receipt: fact(PlatformFactKind::CgroupCpuset, "0-3"),
                cpuset_cpu_count: 4,
            },
            SuppliedCgroupObservation::V1 {
                cpu_usage_nanoseconds: 15,
                memory_current_bytes: 2_300_000_000,
                leaf_cpu_quota_microseconds: None,
                leaf_cpu_period_microseconds: 100_000,
                leaf_memory_limit_bytes: 0,
                hierarchical_memory_limit_bytes: None,
                cpuset_receipt: fact(PlatformFactKind::CgroupCpuset, "0-3"),
                cpuset_cpu_count: 4,
            },
            SuppliedCgroupObservation::V1 {
                cpu_usage_nanoseconds: 15,
                memory_current_bytes: 2_300_000_000,
                leaf_cpu_quota_microseconds: None,
                leaf_cpu_period_microseconds: 100_000,
                leaf_memory_limit_bytes: 9_223_372_036_854_771_712,
                hierarchical_memory_limit_bytes: None,
                cpuset_receipt: ZERO,
                cpuset_cpu_count: 4,
            },
            SuppliedCgroupObservation::V1 {
                cpu_usage_nanoseconds: 15,
                memory_current_bytes: 2_300_000_000,
                leaf_cpu_quota_microseconds: None,
                leaf_cpu_period_microseconds: 100_000,
                leaf_memory_limit_bytes: 9_223_372_036_854_771_712,
                hierarchical_memory_limit_bytes: Some(0),
                cpuset_receipt: fact(PlatformFactKind::CgroupCpuset, "0-3"),
                cpuset_cpu_count: 4,
            },
            SuppliedCgroupObservation::V1 {
                cpu_usage_nanoseconds: 15,
                memory_current_bytes: 2_300_000_000,
                leaf_cpu_quota_microseconds: None,
                leaf_cpu_period_microseconds: 100_000,
                leaf_memory_limit_bytes: 9_223_372_036_854_771_712,
                hierarchical_memory_limit_bytes: None,
                cpuset_receipt: fact(PlatformFactKind::CgroupCpuset, "0-3"),
                cpuset_cpu_count: 0,
            },
            SuppliedCgroupObservation::V2 {
                cpu_usage_nanoseconds: 15,
                memory_current_bytes: 2_300_000_000,
                cpu_quota_microseconds: Some(0),
                cpu_period_microseconds: 100_000,
                memory_max_bytes: None,
                cpuset_receipt: fact(PlatformFactKind::CgroupCpuset, "0-3"),
                cpuset_cpu_count: 4,
            },
            SuppliedCgroupObservation::V2 {
                cpu_usage_nanoseconds: 15,
                memory_current_bytes: 2_300_000_000,
                cpu_quota_microseconds: None,
                cpu_period_microseconds: 0,
                memory_max_bytes: None,
                cpuset_receipt: fact(PlatformFactKind::CgroupCpuset, "0-3"),
                cpuset_cpu_count: 4,
            },
            SuppliedCgroupObservation::V2 {
                cpu_usage_nanoseconds: 15,
                memory_current_bytes: 2_300_000_000,
                cpu_quota_microseconds: None,
                cpu_period_microseconds: 100_000,
                memory_max_bytes: Some(0),
                cpuset_receipt: fact(PlatformFactKind::CgroupCpuset, "0-3"),
                cpuset_cpu_count: 4,
            },
            SuppliedCgroupObservation::V2 {
                cpu_usage_nanoseconds: 15,
                memory_current_bytes: 2_300_000_000,
                cpu_quota_microseconds: None,
                cpu_period_microseconds: 100_000,
                memory_max_bytes: None,
                cpuset_receipt: ZERO,
                cpuset_cpu_count: 4,
            },
            SuppliedCgroupObservation::V2 {
                cpu_usage_nanoseconds: 15,
                memory_current_bytes: 2_300_000_000,
                cpu_quota_microseconds: None,
                cpu_period_microseconds: 100_000,
                memory_max_bytes: None,
                cpuset_receipt: fact(PlatformFactKind::CgroupCpuset, "0-3"),
                cpuset_cpu_count: 0,
            },
        ] {
            let mut value = observation();
            value.cgroup = cgroup;
            assert!(matches!(
                bind(&bytes, value),
                Err(PlatformEnvelopeError::InvalidObservation(_))
            ));
        }
    }

    #[test]
    fn cgroup_v1_and_v2_remain_distinct_observations() {
        let bytes = record(&payload());
        let v1 = bind(&bytes, observation()).unwrap();
        assert!(matches!(v1.cgroup(), SuppliedCgroupObservation::V1 { .. }));
        let mut value = observation();
        value.cgroup = SuppliedCgroupObservation::V2 {
            cpu_usage_nanoseconds: 15,
            memory_current_bytes: 2_300_000_000,
            cpu_quota_microseconds: Some(400_000),
            cpu_period_microseconds: 100_000,
            memory_max_bytes: Some(16 * 1024 * 1024 * 1024),
            cpuset_receipt: fact(PlatformFactKind::CgroupCpuset, "0-3"),
            cpuset_cpu_count: 4,
        };
        let v2 = bind(&bytes, value).unwrap();
        assert!(matches!(v2.cgroup(), SuppliedCgroupObservation::V2 { .. }));
    }
}
