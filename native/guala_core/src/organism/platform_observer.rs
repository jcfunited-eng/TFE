//! Native observation of the Fargate platform facts used by the
//! deployment-envelope binder.
//!
//! This module performs one bounded request to the ECS task-metadata v4
//! endpoint and takes the initial local mount/cgroup observations. Its retained
//! cgroup directory permits explicit later sampling windows; those are not
//! retries or polling. This module does not redirect, decompress, call Python,
//! infer EFS capacity, or claim that the kernel exposes an EFS filesystem ID.
//! The returned observation is non-clonable and its fields are private. It is
//! physical evidence of the reads described here, not organism authority.

use super::platform_envelope::{
    authenticate_and_bind_supplied_platform_observation, canonical_platform_fact_receipt,
    AuthenticatedEnvelopeConsistentWithSuppliedReport, PlatformEnvelopeError, PlatformFactKind,
    SuppliedCgroupObservation, SuppliedUnverifiedPlatformObservation,
};
use super::wake_admission::SuppliedGlobalOwnerRootKey;
use sha2::{Digest, Sha256};
use std::collections::HashSet;
use std::env;
use std::ffi::CString;
use std::fmt;
use std::fs::{self, File, OpenOptions};
use std::io::{Read, Write};
use std::net::{Ipv4Addr, SocketAddrV4, TcpStream};
use std::os::fd::{AsRawFd, FromRawFd, OwnedFd, RawFd};
use std::os::unix::ffi::OsStrExt;
use std::os::unix::fs::{MetadataExt, OpenOptionsExt};
use std::path::{Path, PathBuf};
use std::time::{Duration, Instant};

const METADATA_ENVIRONMENT_NAME: &str = "ECS_CONTAINER_METADATA_URI_V4";
const METADATA_HOST: Ipv4Addr = Ipv4Addr::new(169, 254, 170, 2);
const METADATA_PORT: u16 = 80;
const AUTHORITY_ROOT: &str = "/app/guala";
const MOUNTINFO_PATH: &str = "/proc/self/mountinfo";
const CGROUP_MEMBERSHIP_PATH: &str = "/proc/self/cgroup";
const CGROUP_ROOT: &str = "/sys/fs/cgroup";
const NFS_SUPER_MAGIC: libc::c_long = 0x6969;
const CGROUP_SUPER_MAGIC: libc::c_long = 0x27e0eb;
const CGROUP2_SUPER_MAGIC: libc::c_long = 0x63677270;
const RESOLVE_NO_XDEV: u64 = 0x01;
const RESOLVE_NO_MAGICLINKS: u64 = 0x02;
const RESOLVE_NO_SYMLINKS: u64 = 0x04;
const RESOLVE_BENEATH: u64 = 0x08;
// The accepted URI has one exact authority plus `/v4/`, a 43-byte runtime ID,
// and `/task`. This bound leaves framing room without admitting an arbitrary URL.
const MAX_URI_BYTES: usize = 128;
const MAX_HEADER_BYTES: usize = 16 * 1024;
const MAX_BODY_BYTES: usize = 256 * 1024;
const MAX_RESPONSE_BYTES: usize = 512 * 1024;
const MAX_MOUNTINFO_BYTES: usize = 512 * 1024;
const MAX_CGROUP_MEMBERSHIP_BYTES: usize = 16 * 1024;
const MAX_CGROUP_FILE_BYTES: usize = 16 * 1024;
const MAX_JSON_DEPTH: usize = 32;
const MAX_JSON_MEMBERS_PER_CONTAINER: usize = 256;
const MAX_JSON_STRING_BYTES: usize = 4 * 1024;
const MAX_JSON_VALUES: usize = 4 * 1024;
const READ_BLOCK_BYTES: usize = 8 * 1024;
const IO_TIMEOUT: Duration = Duration::from_secs(10);
const MEBIBYTE: u64 = 1024 * 1024;
const OBSERVATION_EVIDENCE_DOMAIN: &[u8] = b"guala.native.platform-observer-evidence.v1\0";
const NFS_MOUNT_DOMAIN: &[u8] = b"guala.native.nfs4-mount-evidence.v1\0";
const CGROUP_EVIDENCE_DOMAIN: &[u8] = b"guala.native.cgroup-evidence.v1\0";

#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) enum PlatformObserverError {
    MissingMetadataUri,
    InvalidMetadataUri(&'static str),
    Io(&'static str),
    ResponseTooLarge,
    HeaderTooLarge,
    MalformedHttp,
    UnexpectedHttpStatus(u16),
    TooManyHeaders,
    DuplicateHeader(&'static str),
    AmbiguousBodyFraming,
    UnsupportedTransferEncoding,
    CompressionNotAllowed,
    MissingBodyFraming,
    InvalidContentLength,
    BodyTooLarge,
    InvalidChunkEncoding,
    TruncatedBody,
    TrailingHttpBytes,
    MalformedJson,
    JsonTooDeep,
    JsonTooBroad,
    JsonStringTooLong,
    JsonTooManyValues,
    DuplicateJsonKey,
    InvalidMetadata(&'static str),
    ArithmeticOverflow(&'static str),
    MountEvidence(&'static str),
    CgroupEvidence(&'static str),
}

impl fmt::Display for PlatformObserverError {
    fn fmt(&self, output: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::MissingMetadataUri => write!(output, "ECS metadata v4 URI is absent"),
            Self::InvalidMetadataUri(reason) => {
                write!(output, "invalid ECS metadata URI: {reason}")
            }
            Self::Io(operation) => write!(output, "platform observation I/O failed: {operation}"),
            Self::ResponseTooLarge => write!(output, "ECS metadata response exceeds its bound"),
            Self::HeaderTooLarge => write!(output, "ECS metadata headers exceed their bound"),
            Self::MalformedHttp => write!(output, "malformed ECS metadata HTTP response"),
            Self::UnexpectedHttpStatus(status) => {
                write!(output, "ECS metadata returned HTTP {status}")
            }
            Self::TooManyHeaders => write!(output, "ECS metadata returned too many headers"),
            Self::DuplicateHeader(name) => write!(output, "duplicate ECS metadata {name} header"),
            Self::AmbiguousBodyFraming => write!(output, "ECS metadata body framing is ambiguous"),
            Self::UnsupportedTransferEncoding => {
                write!(output, "unsupported ECS metadata transfer encoding")
            }
            Self::CompressionNotAllowed => write!(output, "compressed ECS metadata is forbidden"),
            Self::MissingBodyFraming => {
                write!(output, "ECS metadata response has no explicit body framing")
            }
            Self::InvalidContentLength => write!(output, "invalid ECS metadata content length"),
            Self::BodyTooLarge => write!(output, "ECS metadata body exceeds its bound"),
            Self::InvalidChunkEncoding => write!(output, "invalid ECS metadata chunk encoding"),
            Self::TruncatedBody => write!(output, "truncated ECS metadata body"),
            Self::TrailingHttpBytes => write!(output, "ECS metadata response has trailing bytes"),
            Self::MalformedJson => write!(output, "malformed ECS task metadata JSON"),
            Self::JsonTooDeep => write!(output, "ECS task metadata JSON is too deep"),
            Self::JsonTooBroad => write!(output, "ECS task metadata JSON is too broad"),
            Self::JsonStringTooLong => {
                write!(output, "ECS task metadata JSON string exceeds its bound")
            }
            Self::JsonTooManyValues => {
                write!(output, "ECS task metadata JSON has too many values")
            }
            Self::DuplicateJsonKey => {
                write!(output, "ECS task metadata JSON contains a duplicate key")
            }
            Self::InvalidMetadata(name) => write!(output, "invalid ECS task metadata: {name}"),
            Self::ArithmeticOverflow(name) => {
                write!(output, "platform observation overflow: {name}")
            }
            Self::MountEvidence(reason) => {
                write!(output, "invalid authority mount evidence: {reason}")
            }
            Self::CgroupEvidence(reason) => write!(output, "invalid cgroup evidence: {reason}"),
        }
    }
}

impl std::error::Error for PlatformObserverError {}

struct NativeMountEvidence {
    mount_root_receipt: [u8; 32],
    mount_source_receipt: [u8; 32],
    mount_device_receipt: [u8; 32],
    mount_options_receipt: [u8; 32],
    directory_device: u64,
    directory_inode: u64,
    authority_directory: File,
}

struct NativeCgroupEvidence {
    supplied: SuppliedCgroupObservation,
    receipt: [u8; 32],
    memory_directory: RetainedCgroupMemoryDirectory,
}

/// The opened cgroup directory that owns the process memory controller facts.
/// No pathname is retained: later reads remain anchored to this kernel object.
pub(crate) struct RetainedCgroupMemoryDirectory {
    directory: OwnedFd,
    interface: CgroupMemoryInterface,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
enum CgroupMemoryInterface {
    V1 {
        leaf_memory_limit_bytes: u64,
        hierarchical_memory_limit_bytes: Option<u64>,
    },
    V2 {
        memory_max_bytes: Option<u64>,
    },
}

struct LimitCurrentLimitObservation {
    ceiling_bytes: u64,
    current_bytes: u64,
}

/// One exact memory-current value read after the platform observation.
pub(crate) struct FreshCgroupMemoryCurrent {
    current_bytes: u64,
}

/// A repeatable observer borrowed from the authenticated native platform.
/// It reports cgroup facts around a caller-proposed mapping window. It is not
/// allocation authority, a reservation, or proof that allocation occurs.
pub(super) struct PhysicalMappingWindowObserver<'a> {
    memory: &'a RetainedCgroupMemoryDirectory,
}

#[cfg(test)]
pub(super) struct PhysicalMappingWindowTestOwner {
    memory: RetainedCgroupMemoryDirectory,
}

#[cfg(test)]
impl PhysicalMappingWindowTestOwner {
    pub(super) fn v2(directory: OwnedFd, ceiling_bytes: u64) -> Self {
        Self {
            memory: RetainedCgroupMemoryDirectory::v2(directory, Some(ceiling_bytes)),
        }
    }

    pub(super) fn observer(&self) -> PhysicalMappingWindowObserver<'_> {
        PhysicalMappingWindowObserver {
            memory: &self.memory,
        }
    }
}

/// Facts observed before a proposed allocation. Page-rounded arithmetic covers
/// only the requested mapping bytes. The caller request is neither CURRENT
/// identity nor a custody-verified file length. This observation does not
/// account for allocator
/// metadata, page tables, concurrent activity, or any other memory charge, and
/// it does not guarantee that a later allocation will succeed.
pub(super) struct PreAllocationWindowObservation<'a> {
    memory: &'a RetainedCgroupMemoryDirectory,
    ceiling_bytes: u64,
    before_bytes: u64,
    requested_mapping_bytes: u64,
    runtime_page_size_bytes: u64,
    mapped_bytes: u64,
}

/// Facts observed after the caller's allocation window. The current-value
/// difference is not attributed to the caller's proposed mapping: cgroup
/// accounting and concurrent activity do not provide that proof.
pub(super) struct PostAllocationWindowObservation {
    ceiling_bytes: u64,
    before_bytes: u64,
    after_bytes: u64,
    requested_mapping_bytes: u64,
    runtime_page_size_bytes: u64,
    mapped_bytes: u64,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(super) struct RuntimePageMappingGeometry {
    page_size_bytes: u64,
    mapped_bytes: u64,
}

impl FreshCgroupMemoryCurrent {
    pub(crate) fn current_bytes(&self) -> u64 {
        self.current_bytes
    }
}

impl<'a> PhysicalMappingWindowObserver<'a> {
    pub(super) fn observe_before(
        self,
        requested_mapping_bytes: u64,
    ) -> Result<PreAllocationWindowObservation<'a>, PlatformObserverError> {
        if requested_mapping_bytes == 0 {
            return Err(PlatformObserverError::CgroupEvidence(
                "requested mapping length is zero",
            ));
        }
        let before = self.memory.sample_limits_current_limits()?;
        let page_size = native_page_size_bytes()?;
        let mapped_bytes = window_page_rounded_bytes(
            requested_mapping_bytes,
            page_size,
            before.ceiling_bytes,
            before.current_bytes,
        )?;
        usize::try_from(mapped_bytes).map_err(|_| {
            PlatformObserverError::ArithmeticOverflow("requested mapping address space")
        })?;
        Ok(PreAllocationWindowObservation {
            memory: self.memory,
            ceiling_bytes: before.ceiling_bytes,
            before_bytes: before.current_bytes,
            requested_mapping_bytes,
            runtime_page_size_bytes: page_size,
            mapped_bytes,
        })
    }
}

impl PreAllocationWindowObservation<'_> {
    pub(super) fn requested_mapping_bytes(&self) -> u64 {
        self.requested_mapping_bytes
    }

    pub(super) fn mapped_bytes(&self) -> u64 {
        self.mapped_bytes
    }

    pub(super) fn runtime_page_size_bytes(&self) -> u64 {
        self.runtime_page_size_bytes
    }

    pub(super) fn observe_after(
        self,
    ) -> Result<PostAllocationWindowObservation, PlatformObserverError> {
        let after = self.memory.sample_limits_current_limits()?;
        Ok(PostAllocationWindowObservation {
            ceiling_bytes: self.ceiling_bytes,
            before_bytes: self.before_bytes,
            after_bytes: after.current_bytes,
            requested_mapping_bytes: self.requested_mapping_bytes,
            runtime_page_size_bytes: self.runtime_page_size_bytes,
            mapped_bytes: self.mapped_bytes,
        })
    }
}

impl PostAllocationWindowObservation {
    pub(super) fn ceiling_bytes(&self) -> u64 {
        self.ceiling_bytes
    }

    pub(super) fn before_bytes(&self) -> u64 {
        self.before_bytes
    }

    pub(super) fn after_bytes(&self) -> u64 {
        self.after_bytes
    }

    pub(super) fn requested_mapping_bytes(&self) -> u64 {
        self.requested_mapping_bytes
    }

    pub(super) fn mapped_bytes(&self) -> u64 {
        self.mapped_bytes
    }

    pub(super) fn runtime_page_size_bytes(&self) -> u64 {
        self.runtime_page_size_bytes
    }
}

impl RuntimePageMappingGeometry {
    pub(super) fn page_size_bytes(self) -> u64 {
        self.page_size_bytes
    }

    pub(super) fn mapped_bytes(self) -> u64 {
        self.mapped_bytes
    }
}

fn native_page_size_bytes() -> Result<u64, PlatformObserverError> {
    let runtime_page_size = unsafe { libc::sysconf(libc::_SC_PAGESIZE) };
    if runtime_page_size <= 0 {
        return Err(PlatformObserverError::CgroupEvidence(
            "runtime page size is unavailable",
        ));
    }
    u64::try_from(runtime_page_size)
        .map_err(|_| PlatformObserverError::ArithmeticOverflow("runtime page size"))
}

fn page_rounded_bytes(length: u64, page_size: u64) -> Result<u64, PlatformObserverError> {
    if page_size == 0 {
        return Err(PlatformObserverError::CgroupEvidence(
            "runtime page size is zero",
        ));
    }
    let remainder = length % page_size;
    if remainder == 0 {
        return Ok(length);
    }
    length
        .checked_add(page_size - remainder)
        .ok_or(PlatformObserverError::ArithmeticOverflow(
            "page-rounded requested mapping",
        ))
}

/// Exact runtime-page request geometry only. This does not observe cgroup
/// headroom, reserve memory, perform an allocation, or claim RSS attribution.
pub(super) fn runtime_page_mapping_geometry(
    requested_bytes: u64,
) -> Result<RuntimePageMappingGeometry, PlatformObserverError> {
    let page_size_bytes = native_page_size_bytes()?;
    Ok(RuntimePageMappingGeometry {
        page_size_bytes,
        mapped_bytes: page_rounded_bytes(requested_bytes, page_size_bytes)?,
    })
}

fn window_page_rounded_bytes(
    requested_mapping_bytes: u64,
    page_size: u64,
    ceiling_bytes: u64,
    before_bytes: u64,
) -> Result<u64, PlatformObserverError> {
    let mapped_bytes = page_rounded_bytes(requested_mapping_bytes, page_size)?;
    let headroom =
        ceiling_bytes
            .checked_sub(before_bytes)
            .ok_or(PlatformObserverError::CgroupEvidence(
                "memory current exceeds the finite cgroup ceiling",
            ))?;
    if mapped_bytes > headroom {
        return Err(PlatformObserverError::CgroupEvidence(
            "page-rounded requested mapping exceeds observed cgroup headroom",
        ));
    }
    Ok(mapped_bytes)
}

impl RetainedCgroupMemoryDirectory {
    fn v1(
        directory: OwnedFd,
        leaf_memory_limit_bytes: u64,
        hierarchical_memory_limit_bytes: Option<u64>,
    ) -> Self {
        Self {
            directory,
            interface: CgroupMemoryInterface::V1 {
                leaf_memory_limit_bytes,
                hierarchical_memory_limit_bytes,
            },
        }
    }

    fn v2(directory: OwnedFd, memory_max_bytes: Option<u64>) -> Self {
        Self {
            directory,
            interface: CgroupMemoryInterface::V2 { memory_max_bytes },
        }
    }

    pub(crate) fn read_memory_current(
        &self,
    ) -> Result<FreshCgroupMemoryCurrent, PlatformObserverError> {
        let filename = match self.interface {
            CgroupMemoryInterface::V1 { .. } => Path::new("memory.usage_in_bytes"),
            CgroupMemoryInterface::V2 { .. } => Path::new("memory.current"),
        };
        Ok(FreshCgroupMemoryCurrent {
            current_bytes: read_cgroup_u64_at(&self.directory, filename)?,
        })
    }

    pub(crate) fn finite_memory_ceiling(&self) -> Result<u64, PlatformObserverError> {
        finite_memory_ceiling_for(self.interface)
    }

    fn sample_limits_current_limits(
        &self,
    ) -> Result<LimitCurrentLimitObservation, PlatformObserverError> {
        let limit_before = self.read_fresh_memory_limits()?;
        let current_bytes = self.read_memory_current()?.current_bytes();
        let limit_after = self.read_fresh_memory_limits()?;
        sampled_limits_match_retained_facts(
            self.interface,
            limit_before,
            current_bytes,
            limit_after,
        )
    }

    fn read_fresh_memory_limits(&self) -> Result<CgroupMemoryInterface, PlatformObserverError> {
        match self.interface {
            CgroupMemoryInterface::V1 { .. } => Ok(CgroupMemoryInterface::V1 {
                leaf_memory_limit_bytes: read_cgroup_positive_u64_at(
                    &self.directory,
                    Path::new("memory.limit_in_bytes"),
                    "memory limit",
                )?,
                hierarchical_memory_limit_bytes: stream_v1_hierarchical_memory_limit_at(
                    &self.directory,
                )?,
            }),
            CgroupMemoryInterface::V2 { .. } => Ok(CgroupMemoryInterface::V2 {
                memory_max_bytes: read_cgroup_max_at(
                    &self.directory,
                    Path::new("memory.max"),
                    "memory max",
                )?,
            }),
        }
    }
}

/// This comparison covers only the two sampled limit reads. Equal samples do
/// not prove continuous immutability and cannot detect an ABA change between
/// reads.
fn sampled_limits_match_retained_facts(
    retained: CgroupMemoryInterface,
    limit_before: CgroupMemoryInterface,
    current_bytes: u64,
    limit_after: CgroupMemoryInterface,
) -> Result<LimitCurrentLimitObservation, PlatformObserverError> {
    if limit_before != retained || limit_after != retained {
        return Err(PlatformObserverError::CgroupEvidence(
            "sampled cgroup memory limits do not match retained authenticated facts",
        ));
    }
    let ceiling_bytes = finite_memory_ceiling_for(retained)?;
    if current_bytes > ceiling_bytes {
        return Err(PlatformObserverError::CgroupEvidence(
            "sampled memory current exceeds the retained finite cgroup ceiling",
        ));
    }
    Ok(LimitCurrentLimitObservation {
        ceiling_bytes,
        current_bytes,
    })
}

fn finite_memory_ceiling_for(
    interface: CgroupMemoryInterface,
) -> Result<u64, PlatformObserverError> {
    match interface {
        CgroupMemoryInterface::V1 {
            leaf_memory_limit_bytes,
            hierarchical_memory_limit_bytes,
        } => {
            let unlimited = v1_unlimited_memory_sentinel_bytes()?;
            let leaf = classify_v1_memory_limit(leaf_memory_limit_bytes, unlimited)?.finite_bytes();
            let hierarchical = hierarchical_memory_limit_bytes
                .map(|limit| classify_v1_memory_limit(limit, unlimited))
                .transpose()?
                .and_then(ClassifiedV1MemoryLimit::finite_bytes);
            match (leaf, hierarchical) {
                (Some(leaf), Some(hierarchical)) => Ok(leaf.min(hierarchical)),
                (Some(leaf), None) => Ok(leaf),
                (None, Some(hierarchical)) => Ok(hierarchical),
                (None, None) => Err(PlatformObserverError::CgroupEvidence(
                    "cgroup v1 memory limit is unbounded",
                )),
            }
        }
        CgroupMemoryInterface::V2 {
            memory_max_bytes: Some(memory_max_bytes),
        } => Ok(memory_max_bytes),
        CgroupMemoryInterface::V2 {
            memory_max_bytes: None,
        } => Err(PlatformObserverError::CgroupEvidence(
            "cgroup v2 memory limit is unbounded",
        )),
    }
}

enum ClassifiedV1MemoryLimit {
    Finite(u64),
    Unbounded,
}

impl ClassifiedV1MemoryLimit {
    fn finite_bytes(self) -> Option<u64> {
        match self {
            Self::Finite(bytes) => Some(bytes),
            Self::Unbounded => None,
        }
    }
}

fn classify_v1_memory_limit(
    raw_bytes: u64,
    unlimited_sentinel_bytes: u64,
) -> Result<ClassifiedV1MemoryLimit, PlatformObserverError> {
    match raw_bytes.cmp(&unlimited_sentinel_bytes) {
        std::cmp::Ordering::Less => Ok(ClassifiedV1MemoryLimit::Finite(raw_bytes)),
        std::cmp::Ordering::Equal => Ok(ClassifiedV1MemoryLimit::Unbounded),
        std::cmp::Ordering::Greater => Err(PlatformObserverError::CgroupEvidence(
            "cgroup v1 memory limit exceeds the native unlimited sentinel",
        )),
    }
}

fn v1_unlimited_memory_sentinel_bytes() -> Result<u64, PlatformObserverError> {
    if std::mem::size_of::<libc::c_long>() != 8 || std::mem::size_of::<usize>() != 8 {
        return Err(PlatformObserverError::CgroupEvidence(
            "cgroup v1 memory ceiling requires 64-bit native userspace",
        ));
    }
    let runtime_page_size = unsafe { libc::sysconf(libc::_SC_PAGESIZE) };
    if runtime_page_size <= 0 {
        return Err(PlatformObserverError::CgroupEvidence(
            "runtime page size is unavailable",
        ));
    }
    let page_size = u64::try_from(runtime_page_size)
        .map_err(|_| PlatformObserverError::ArithmeticOverflow("runtime page size"))?;
    derive_v1_unlimited_memory_sentinel_bytes(8, page_size)
}

fn derive_v1_unlimited_memory_sentinel_bytes(
    c_long_width_bytes: usize,
    page_size: u64,
) -> Result<u64, PlatformObserverError> {
    if page_size == 0 {
        return Err(PlatformObserverError::CgroupEvidence(
            "runtime page size is zero",
        ));
    }
    let page_counter_max = match c_long_width_bytes {
        4 => i32::MAX as u64,
        8 => (i64::MAX as u64) / page_size,
        _ => {
            return Err(PlatformObserverError::CgroupEvidence(
                "unsupported c_long width",
            ))
        }
    };
    page_counter_max
        .checked_mul(page_size)
        .ok_or(PlatformObserverError::ArithmeticOverflow(
            "cgroup v1 unlimited memory sentinel",
        ))
}

/// One native, one-shot platform observation. Private fields prevent callers
/// from manufacturing this native evidence capability with supplied values.
pub(crate) struct NativePlatformObservation {
    supplied: SuppliedUnverifiedPlatformObservation,
    physical_evidence_receipt: [u8; 32],
    metadata_response_receipt: [u8; 32],
    mount_root_receipt: [u8; 32],
    mount_source_receipt: [u8; 32],
    mount_device_receipt: [u8; 32],
    mount_options_receipt: [u8; 32],
    cgroup_evidence_receipt: [u8; 32],
    authority_directory: File,
    cgroup_memory_directory: RetainedCgroupMemoryDirectory,
}

/// Envelope consistency plus the exact evidence receipt from the native read.
/// ECS task metadata remains AWS platform-reported data; this wrapper does not
/// turn the HTTP response into a cryptographic platform attestation.
pub(crate) struct PlatformBoundGlobalOwner {
    global_owner: SuppliedGlobalOwnerRootKey,
    envelope_consistency: AuthenticatedEnvelopeConsistentWithSuppliedReport,
    physical_evidence_receipt: [u8; 32],
    metadata_response_receipt: [u8; 32],
    mount_options_receipt: [u8; 32],
    cgroup_evidence_receipt: [u8; 32],
    authority_directory: File,
    cgroup_memory_directory: RetainedCgroupMemoryDirectory,
}

impl PlatformBoundGlobalOwner {
    pub(crate) fn envelope_consistency(
        &self,
    ) -> &AuthenticatedEnvelopeConsistentWithSuppliedReport {
        &self.envelope_consistency
    }

    pub(crate) fn physical_evidence_receipt(&self) -> [u8; 32] {
        self.physical_evidence_receipt
    }

    pub(crate) fn evidence_component_receipts(&self) -> ([u8; 32], [u8; 32], [u8; 32]) {
        (
            self.metadata_response_receipt,
            self.mount_options_receipt,
            self.cgroup_evidence_receipt,
        )
    }

    pub(super) fn global_owner(&self) -> &SuppliedGlobalOwnerRootKey {
        &self.global_owner
    }

    pub(super) fn authority_directory(&self) -> &File {
        &self.authority_directory
    }

    pub(super) fn physical_mapping_window_observer(&self) -> PhysicalMappingWindowObserver<'_> {
        PhysicalMappingWindowObserver {
            memory: &self.cgroup_memory_directory,
        }
    }
}

impl NativePlatformObservation {
    pub(crate) fn physical_evidence_receipt(&self) -> [u8; 32] {
        self.physical_evidence_receipt
    }

    pub(crate) fn metadata_response_receipt(&self) -> [u8; 32] {
        self.metadata_response_receipt
    }

    pub(crate) fn nfs_mount_evidence_receipts(&self) -> ([u8; 32], [u8; 32], [u8; 32]) {
        (
            self.mount_root_receipt,
            self.mount_source_receipt,
            self.mount_device_receipt,
        )
    }

    pub(crate) fn cgroup_evidence_receipt(&self) -> [u8; 32] {
        self.cgroup_evidence_receipt
    }

    pub(crate) fn authenticate_envelope(
        self,
        record: &[u8],
        global_owner: SuppliedGlobalOwnerRootKey,
    ) -> Result<PlatformBoundGlobalOwner, PlatformEnvelopeError> {
        let envelope_consistency = authenticate_and_bind_supplied_platform_observation(
            record,
            &global_owner,
            self.supplied,
        )?;
        Ok(PlatformBoundGlobalOwner {
            global_owner,
            envelope_consistency,
            physical_evidence_receipt: self.physical_evidence_receipt,
            metadata_response_receipt: self.metadata_response_receipt,
            mount_options_receipt: self.mount_options_receipt,
            cgroup_evidence_receipt: self.cgroup_evidence_receipt,
            authority_directory: self.authority_directory,
            cgroup_memory_directory: self.cgroup_memory_directory,
        })
    }
}

/// Perform the sole production observation: one ECS `/task` request followed
/// by one bounded local mount/cgroup snapshot.
pub(crate) fn observe_native_platform() -> Result<NativePlatformObservation, PlatformObserverError>
{
    let base = env::var(METADATA_ENVIRONMENT_NAME)
        .map_err(|_| PlatformObserverError::MissingMetadataUri)?;
    let request_target = metadata_task_target(&base)?;
    let response = fetch_metadata_once(&request_target)?;
    let body = decode_http_response(&response)?;
    reject_duplicate_json_keys(&body)?;
    let metadata = parse_task_metadata(&body)?;
    let mountinfo = read_bounded_path(
        Path::new(MOUNTINFO_PATH),
        MAX_MOUNTINFO_BYTES,
        "read mountinfo",
    )?;
    let mount_entries = parse_mountinfo(&mountinfo)?;
    let mount = inspect_authority_mount(&mount_entries)?;
    let cgroup = inspect_cgroup(&mount_entries)?;

    let metadata_response_receipt: [u8; 32] = Sha256::digest(&body).into();
    let supplied = metadata.into_supplied(cgroup.supplied);
    let mut evidence = Sha256::new();
    evidence.update(OBSERVATION_EVIDENCE_DOMAIN);
    evidence.update(metadata_response_receipt);
    evidence.update(mount.mount_root_receipt);
    evidence.update(mount.mount_source_receipt);
    evidence.update(mount.mount_device_receipt);
    evidence.update(mount.mount_options_receipt);
    evidence.update(mount.directory_device.to_le_bytes());
    evidence.update(mount.directory_inode.to_le_bytes());
    evidence.update(cgroup.receipt);
    let physical_evidence_receipt = evidence.finalize().into();

    Ok(NativePlatformObservation {
        supplied,
        physical_evidence_receipt,
        metadata_response_receipt,
        mount_root_receipt: mount.mount_root_receipt,
        mount_source_receipt: mount.mount_source_receipt,
        mount_device_receipt: mount.mount_device_receipt,
        mount_options_receipt: mount.mount_options_receipt,
        cgroup_evidence_receipt: cgroup.receipt,
        authority_directory: mount.authority_directory,
        cgroup_memory_directory: cgroup.memory_directory,
    })
}

fn metadata_task_target(base: &str) -> Result<String, PlatformObserverError> {
    if base.is_empty() || base.len() > MAX_URI_BYTES {
        return Err(PlatformObserverError::InvalidMetadataUri("length"));
    }
    if !base.is_ascii() || base.bytes().any(|byte| byte.is_ascii_control()) {
        return Err(PlatformObserverError::InvalidMetadataUri(
            "non-ASCII or control byte",
        ));
    }
    let prefix = "http://169.254.170.2";
    let path = base
        .strip_prefix(prefix)
        .ok_or(PlatformObserverError::InvalidMetadataUri(
            "not the ECS link-local authority",
        ))?;
    let runtime_id = path
        .strip_prefix("/v4/")
        .ok_or(PlatformObserverError::InvalidMetadataUri(
            "not a v4 runtime path",
        ))?;
    if runtime_id.len() != 43
        || runtime_id.as_bytes().get(32) != Some(&b'-')
        || !runtime_id[..32]
            .bytes()
            .all(|byte| byte.is_ascii_digit() || (b'a'..=b'f').contains(&byte))
        || !runtime_id[33..].bytes().all(|byte| byte.is_ascii_digit())
        || path.ends_with('/')
        || path.contains('?')
        || path.contains('#')
        || path.contains('%')
        || path.contains("..")
        || path.contains("//")
    {
        return Err(PlatformObserverError::InvalidMetadataUri(
            "noncanonical base path",
        ));
    }
    let target_len = path
        .len()
        .checked_add(5)
        .ok_or(PlatformObserverError::ArithmeticOverflow(
            "metadata request target",
        ))?;
    if target_len > MAX_URI_BYTES {
        return Err(PlatformObserverError::InvalidMetadataUri(
            "request target length",
        ));
    }
    Ok(format!("{path}/task"))
}

fn fetch_metadata_once(target: &str) -> Result<Vec<u8>, PlatformObserverError> {
    let address = SocketAddrV4::new(METADATA_HOST, METADATA_PORT);
    let deadline =
        Instant::now()
            .checked_add(IO_TIMEOUT)
            .ok_or(PlatformObserverError::ArithmeticOverflow(
                "ECS metadata deadline",
            ))?;
    let mut stream = TcpStream::connect_timeout(
        &address.into(),
        remaining_before(deadline, "connect ECS metadata endpoint")?,
    )
    .map_err(|_| PlatformObserverError::Io("connect ECS metadata endpoint"))?;
    stream
        .set_write_timeout(Some(remaining_before(
            deadline,
            "write ECS metadata request",
        )?))
        .map_err(|_| PlatformObserverError::Io("set ECS metadata write timeout"))?;
    let request = format!(
        "GET {target} HTTP/1.1\r\nHost: 169.254.170.2\r\nAccept: application/json\r\nAccept-Encoding: identity\r\nConnection: close\r\n\r\n"
    );
    let mut written = 0;
    while written < request.len() {
        stream
            .set_write_timeout(Some(remaining_before(
                deadline,
                "write ECS metadata request",
            )?))
            .map_err(|_| PlatformObserverError::Io("set ECS metadata write timeout"))?;
        let count = stream
            .write(&request.as_bytes()[written..])
            .map_err(|_| PlatformObserverError::Io("write ECS metadata request"))?;
        if count == 0 {
            return Err(PlatformObserverError::Io("write ECS metadata request"));
        }
        written = written
            .checked_add(count)
            .ok_or(PlatformObserverError::ArithmeticOverflow(
                "ECS metadata request write",
            ))?;
    }

    let mut response = Vec::new();
    response
        .try_reserve_exact(READ_BLOCK_BYTES)
        .map_err(|_| PlatformObserverError::Io("reserve ECS metadata response"))?;
    let mut block = [0_u8; READ_BLOCK_BYTES];
    loop {
        stream
            .set_read_timeout(Some(remaining_before(
                deadline,
                "read ECS metadata response",
            )?))
            .map_err(|_| PlatformObserverError::Io("set ECS metadata read timeout"))?;
        let count = stream
            .read(&mut block)
            .map_err(|_| PlatformObserverError::Io("read ECS metadata response"))?;
        if count == 0 {
            break;
        }
        let next = response
            .len()
            .checked_add(count)
            .ok_or(PlatformObserverError::ResponseTooLarge)?;
        if next > MAX_RESPONSE_BYTES {
            return Err(PlatformObserverError::ResponseTooLarge);
        }
        response.extend_from_slice(&block[..count]);
    }
    Ok(response)
}

fn remaining_before(
    deadline: Instant,
    operation: &'static str,
) -> Result<Duration, PlatformObserverError> {
    deadline
        .checked_duration_since(Instant::now())
        .filter(|remaining| !remaining.is_zero())
        .ok_or(PlatformObserverError::Io(operation))
}

fn decode_http_response(response: &[u8]) -> Result<Vec<u8>, PlatformObserverError> {
    let header_end = find_header_end(response)?;
    if header_end > MAX_HEADER_BYTES {
        return Err(PlatformObserverError::HeaderTooLarge);
    }
    let mut headers = [httparse::EMPTY_HEADER; 64];
    let header_capacity = headers.len();
    let mut parsed = httparse::Response::new(&mut headers);
    let parsed_end = match parsed
        .parse(response)
        .map_err(|_| PlatformObserverError::MalformedHttp)?
    {
        httparse::Status::Complete(value) => value,
        httparse::Status::Partial => return Err(PlatformObserverError::MalformedHttp),
    };
    if parsed_end != header_end {
        return Err(PlatformObserverError::MalformedHttp);
    }
    let status = parsed.code.ok_or(PlatformObserverError::MalformedHttp)?;
    if parsed.version != Some(1) {
        return Err(PlatformObserverError::MalformedHttp);
    }
    if status != 200 {
        return Err(PlatformObserverError::UnexpectedHttpStatus(status));
    }
    if parsed.headers.len() == header_capacity {
        return Err(PlatformObserverError::TooManyHeaders);
    }

    let mut content_length = None;
    let mut transfer_encoding = None;
    let mut content_type = None;
    for header in parsed.headers.iter() {
        if header.name.eq_ignore_ascii_case("content-length") {
            if content_length.replace(header.value).is_some() {
                return Err(PlatformObserverError::DuplicateHeader("content-length"));
            }
        } else if header.name.eq_ignore_ascii_case("transfer-encoding") {
            if transfer_encoding.replace(header.value).is_some() {
                return Err(PlatformObserverError::DuplicateHeader("transfer-encoding"));
            }
        } else if header.name.eq_ignore_ascii_case("content-encoding") {
            return Err(PlatformObserverError::CompressionNotAllowed);
        } else if header.name.eq_ignore_ascii_case("content-type") {
            if content_type.replace(header.value).is_some() {
                return Err(PlatformObserverError::DuplicateHeader("content-type"));
            }
        }
    }
    let content_type_is_json = content_type.is_some_and(|raw| {
        let value = ascii_trim(raw);
        value.eq_ignore_ascii_case(b"application/json")
            || value
                .get(..17)
                .is_some_and(|prefix| prefix.eq_ignore_ascii_case(b"application/json;"))
    });
    if !content_type_is_json {
        return Err(PlatformObserverError::MalformedHttp);
    }
    if content_length.is_some() && transfer_encoding.is_some() {
        return Err(PlatformObserverError::AmbiguousBodyFraming);
    }
    let wire_body = &response[parsed_end..];
    match (content_length, transfer_encoding) {
        (Some(raw), None) => decode_content_length(raw, wire_body),
        (None, Some(raw)) => {
            if !ascii_trim(raw).eq_ignore_ascii_case(b"chunked") {
                return Err(PlatformObserverError::UnsupportedTransferEncoding);
            }
            decode_chunked(wire_body)
        }
        (None, None) => Err(PlatformObserverError::MissingBodyFraming),
        (Some(_), Some(_)) => Err(PlatformObserverError::AmbiguousBodyFraming),
    }
}

fn find_header_end(response: &[u8]) -> Result<usize, PlatformObserverError> {
    let limit = response.len().min(MAX_HEADER_BYTES.saturating_add(4));
    response[..limit]
        .windows(4)
        .position(|window| window == b"\r\n\r\n")
        .map(|offset| offset + 4)
        .ok_or(if response.len() > MAX_HEADER_BYTES {
            PlatformObserverError::HeaderTooLarge
        } else {
            PlatformObserverError::MalformedHttp
        })
}

fn decode_content_length(raw: &[u8], wire: &[u8]) -> Result<Vec<u8>, PlatformObserverError> {
    let raw = ascii_trim(raw);
    if raw.is_empty() || !raw.iter().all(u8::is_ascii_digit) {
        return Err(PlatformObserverError::InvalidContentLength);
    }
    let text = std::str::from_utf8(raw).map_err(|_| PlatformObserverError::InvalidContentLength)?;
    let expected = text
        .parse::<usize>()
        .map_err(|_| PlatformObserverError::InvalidContentLength)?;
    if expected > MAX_BODY_BYTES {
        return Err(PlatformObserverError::BodyTooLarge);
    }
    if wire.len() < expected {
        return Err(PlatformObserverError::TruncatedBody);
    }
    if wire.len() > expected {
        return Err(PlatformObserverError::TrailingHttpBytes);
    }
    Ok(wire.to_vec())
}

fn decode_chunked(wire: &[u8]) -> Result<Vec<u8>, PlatformObserverError> {
    let mut cursor = 0_usize;
    let mut output = Vec::new();
    loop {
        let line_end = find_crlf(wire, cursor).ok_or(PlatformObserverError::TruncatedBody)?;
        let size_text = &wire[cursor..line_end];
        if size_text.is_empty()
            || size_text.len() > 16
            || size_text.contains(&b';')
            || !size_text.iter().all(u8::is_ascii_hexdigit)
        {
            return Err(PlatformObserverError::InvalidChunkEncoding);
        }
        let size = usize::from_str_radix(
            std::str::from_utf8(size_text)
                .map_err(|_| PlatformObserverError::InvalidChunkEncoding)?,
            16,
        )
        .map_err(|_| PlatformObserverError::InvalidChunkEncoding)?;
        cursor = line_end
            .checked_add(2)
            .ok_or(PlatformObserverError::ArithmeticOverflow("chunk cursor"))?;
        if size == 0 {
            let end = cursor
                .checked_add(2)
                .ok_or(PlatformObserverError::ArithmeticOverflow(
                    "chunk terminator",
                ))?;
            if wire.get(cursor..end) != Some(b"\r\n") {
                return Err(PlatformObserverError::InvalidChunkEncoding);
            }
            if end != wire.len() {
                return Err(PlatformObserverError::TrailingHttpBytes);
            }
            return Ok(output);
        }
        let next_len = output
            .len()
            .checked_add(size)
            .ok_or(PlatformObserverError::BodyTooLarge)?;
        if next_len > MAX_BODY_BYTES {
            return Err(PlatformObserverError::BodyTooLarge);
        }
        let chunk_end = cursor
            .checked_add(size)
            .ok_or(PlatformObserverError::ArithmeticOverflow("chunk end"))?;
        let framed_end = chunk_end
            .checked_add(2)
            .ok_or(PlatformObserverError::ArithmeticOverflow("chunk framing"))?;
        let chunk = wire
            .get(cursor..chunk_end)
            .ok_or(PlatformObserverError::TruncatedBody)?;
        if wire.get(chunk_end..framed_end) != Some(b"\r\n") {
            return Err(PlatformObserverError::InvalidChunkEncoding);
        }
        output.extend_from_slice(chunk);
        cursor = framed_end;
    }
}

fn find_crlf(bytes: &[u8], start: usize) -> Option<usize> {
    bytes
        .get(start..)?
        .windows(2)
        .position(|value| value == b"\r\n")
        .map(|offset| start + offset)
}

fn ascii_trim(mut bytes: &[u8]) -> &[u8] {
    while bytes.first().is_some_and(|byte| byte.is_ascii_whitespace()) {
        bytes = &bytes[1..];
    }
    while bytes.last().is_some_and(|byte| byte.is_ascii_whitespace()) {
        bytes = &bytes[..bytes.len() - 1];
    }
    bytes
}

struct ParsedTaskMetadata {
    task_arn_receipt: [u8; 32],
    aws_account_receipt: [u8; 32],
    region_receipt: [u8; 32],
    cluster_receipt: [u8; 32],
    service_receipt: [u8; 32],
    task_family_receipt: [u8; 32],
    app_container_receipt: [u8; 32],
    task_revision: u32,
    image_digest: [u8; 32],
    task_cpu_millicores: u64,
    task_memory_bytes: u64,
    ephemeral_reserved_bytes: u64,
    ephemeral_utilized_bytes: u64,
}

impl ParsedTaskMetadata {
    fn into_supplied(
        self,
        cgroup: SuppliedCgroupObservation,
    ) -> SuppliedUnverifiedPlatformObservation {
        SuppliedUnverifiedPlatformObservation {
            task_arn_receipt: self.task_arn_receipt,
            aws_account_receipt: self.aws_account_receipt,
            region_receipt: self.region_receipt,
            cluster_receipt: self.cluster_receipt,
            service_receipt: self.service_receipt,
            task_family_receipt: self.task_family_receipt,
            app_container_receipt: self.app_container_receipt,
            authority_root_receipt: canonical_platform_fact_receipt(
                PlatformFactKind::AuthorityRoot,
                AUTHORITY_ROOT.as_bytes(),
            ),
            task_revision: self.task_revision,
            image_digest: self.image_digest,
            task_cpu_millicores: self.task_cpu_millicores,
            task_memory_bytes: self.task_memory_bytes,
            ephemeral_reserved_bytes: self.ephemeral_reserved_bytes,
            ephemeral_utilized_bytes: self.ephemeral_utilized_bytes,
            launch_type_is_fargate: true,
            authority_mount_is_nfs_v4: true,
            efs_filesystem_id_is_kernel_observable: false,
            cgroup,
        }
    }
}

fn parse_task_metadata(body: &[u8]) -> Result<ParsedTaskMetadata, PlatformObserverError> {
    let value: serde_json::Value =
        serde_json::from_slice(body).map_err(|_| PlatformObserverError::MalformedJson)?;
    let object = value
        .as_object()
        .ok_or(PlatformObserverError::InvalidMetadata(
            "top level is not an object",
        ))?;
    let task_arn = required_string(object, "TaskARN")?;
    let (region, account, task_cluster) = parse_task_arn(task_arn)?;
    let cluster = required_string(object, "Cluster")?;
    validate_cluster_arn(cluster, region, account, task_cluster)?;
    let service = required_string(object, "ServiceName")?;
    let family = required_string(object, "Family")?;
    let revision_text = required_string(object, "Revision")?;
    let task_revision = parse_positive_u32(revision_text, "Revision")?;
    if required_string(object, "LaunchType")? != "FARGATE" {
        return Err(PlatformObserverError::InvalidMetadata(
            "LaunchType is not FARGATE",
        ));
    }

    let limits = required_object(object, "Limits")?;
    let task_cpu_millicores = parse_cpu_millicores(
        limits
            .get("CPU")
            .ok_or(PlatformObserverError::InvalidMetadata("missing task CPU"))?,
    )?;
    let memory_mib = required_u64(limits, "Memory")?;
    let task_memory_bytes = positive_mib_to_bytes(memory_mib, "task memory")?;

    let ephemeral = required_object(object, "EphemeralStorageMetrics")?;
    let utilized_mib = required_u64(ephemeral, "Utilized")?;
    let reserved_mib = required_u64(ephemeral, "Reserved")?;
    if reserved_mib == 0 || utilized_mib > reserved_mib {
        return Err(PlatformObserverError::InvalidMetadata(
            "ephemeral storage metrics",
        ));
    }
    let ephemeral_reserved_bytes = positive_mib_to_bytes(reserved_mib, "ephemeral reserve")?;
    let ephemeral_utilized_bytes =
        utilized_mib
            .checked_mul(MEBIBYTE)
            .ok_or(PlatformObserverError::ArithmeticOverflow(
                "ephemeral utilization",
            ))?;

    let containers = object
        .get("Containers")
        .and_then(serde_json::Value::as_array)
        .ok_or(PlatformObserverError::InvalidMetadata("missing Containers"))?;
    if containers.is_empty() || containers.len() > 64 {
        return Err(PlatformObserverError::InvalidMetadata("container count"));
    }
    let mut app = None;
    for container in containers {
        let container = container
            .as_object()
            .ok_or(PlatformObserverError::InvalidMetadata(
                "container is not an object",
            ))?;
        let name = required_string(container, "Name")?;
        let kind = required_string(container, "Type")?;
        if name == "dsf-ai" {
            if app.is_some() {
                return Err(PlatformObserverError::InvalidMetadata(
                    "duplicate dsf-ai container",
                ));
            }
            if kind != "NORMAL" {
                return Err(PlatformObserverError::InvalidMetadata(
                    "dsf-ai container is not NORMAL",
                ));
            }
            let image_id = required_string(container, "ImageID")?;
            app = Some((name, parse_sha256_image_digest(image_id)?));
        }
    }
    let (app_name, image_digest) = app.ok_or(PlatformObserverError::InvalidMetadata(
        "missing dsf-ai NORMAL container",
    ))?;

    Ok(ParsedTaskMetadata {
        task_arn_receipt: fact(PlatformFactKind::TaskArn, task_arn),
        aws_account_receipt: fact(PlatformFactKind::AwsAccount, account),
        region_receipt: fact(PlatformFactKind::Region, region),
        cluster_receipt: fact(PlatformFactKind::Cluster, cluster),
        service_receipt: fact(PlatformFactKind::Service, service),
        task_family_receipt: fact(PlatformFactKind::TaskFamily, family),
        app_container_receipt: fact(PlatformFactKind::AppContainer, app_name),
        task_revision,
        image_digest,
        task_cpu_millicores,
        task_memory_bytes,
        ephemeral_reserved_bytes,
        ephemeral_utilized_bytes,
    })
}

fn required_object<'a>(
    object: &'a serde_json::Map<String, serde_json::Value>,
    name: &'static str,
) -> Result<&'a serde_json::Map<String, serde_json::Value>, PlatformObserverError> {
    object
        .get(name)
        .and_then(serde_json::Value::as_object)
        .ok_or(PlatformObserverError::InvalidMetadata(name))
}

fn required_string<'a>(
    object: &'a serde_json::Map<String, serde_json::Value>,
    name: &'static str,
) -> Result<&'a str, PlatformObserverError> {
    let value = object
        .get(name)
        .and_then(serde_json::Value::as_str)
        .ok_or(PlatformObserverError::InvalidMetadata(name))?;
    if value.is_empty() || value.len() > 2_048 || value.as_bytes().contains(&0) {
        return Err(PlatformObserverError::InvalidMetadata(name));
    }
    Ok(value)
}

fn required_u64(
    object: &serde_json::Map<String, serde_json::Value>,
    name: &'static str,
) -> Result<u64, PlatformObserverError> {
    object
        .get(name)
        .and_then(serde_json::Value::as_u64)
        .ok_or(PlatformObserverError::InvalidMetadata(name))
}

fn parse_task_arn(task_arn: &str) -> Result<(&str, &str, &str), PlatformObserverError> {
    let parts: Vec<&str> = task_arn.split(':').collect();
    if parts.len() != 6
        || parts[0] != "arn"
        || parts[1] != "aws"
        || parts[2] != "ecs"
        || parts[3].is_empty()
        || parts[4].len() != 12
        || !parts[4].bytes().all(|value| value.is_ascii_digit())
    {
        return Err(PlatformObserverError::InvalidMetadata("TaskARN"));
    }
    let resource: Vec<&str> = parts[5].split('/').collect();
    if resource.len() != 3
        || resource[0] != "task"
        || resource[1].is_empty()
        || resource[2].len() != 32
        || !resource[2]
            .bytes()
            .all(|byte| byte.is_ascii_digit() || (b'a'..=b'f').contains(&byte))
    {
        return Err(PlatformObserverError::InvalidMetadata("TaskARN resource"));
    }
    Ok((parts[3], parts[4], resource[1]))
}

fn validate_cluster_arn(
    cluster: &str,
    region: &str,
    account: &str,
    task_cluster: &str,
) -> Result<(), PlatformObserverError> {
    let expected = format!("arn:aws:ecs:{region}:{account}:cluster/{task_cluster}");
    if cluster != expected {
        return Err(PlatformObserverError::InvalidMetadata("Cluster ARN"));
    }
    Ok(())
}

fn parse_positive_u32(value: &str, name: &'static str) -> Result<u32, PlatformObserverError> {
    if value.is_empty()
        || value.starts_with('+')
        || (value.len() > 1 && value.starts_with('0'))
        || !value.bytes().all(|byte| byte.is_ascii_digit())
    {
        return Err(PlatformObserverError::InvalidMetadata(name));
    }
    let parsed = value
        .parse::<u32>()
        .map_err(|_| PlatformObserverError::InvalidMetadata(name))?;
    if parsed == 0 {
        return Err(PlatformObserverError::InvalidMetadata(name));
    }
    Ok(parsed)
}

fn parse_cpu_millicores(value: &serde_json::Value) -> Result<u64, PlatformObserverError> {
    let number = value
        .as_number()
        .ok_or(PlatformObserverError::InvalidMetadata("task CPU"))?
        .to_string();
    if number.contains(['e', 'E', '-', '+']) {
        return Err(PlatformObserverError::InvalidMetadata("task CPU"));
    }
    let mut components = number.split('.');
    let whole = components.next().unwrap_or_default();
    let fraction = components.next();
    if components.next().is_some()
        || whole.is_empty()
        || !whole.bytes().all(|byte| byte.is_ascii_digit())
        || fraction.is_some_and(|part| {
            part.is_empty() || part.len() > 3 || !part.bytes().all(|byte| byte.is_ascii_digit())
        })
    {
        return Err(PlatformObserverError::InvalidMetadata("task CPU"));
    }
    let whole = whole
        .parse::<u64>()
        .map_err(|_| PlatformObserverError::InvalidMetadata("task CPU"))?;
    let fraction = fraction.unwrap_or("");
    let fraction_value = if fraction.is_empty() {
        0
    } else {
        fraction
            .parse::<u64>()
            .map_err(|_| PlatformObserverError::InvalidMetadata("task CPU"))?
            .checked_mul(10_u64.pow((3 - fraction.len()) as u32))
            .ok_or(PlatformObserverError::ArithmeticOverflow(
                "task CPU fraction",
            ))?
    };
    let millicores = whole
        .checked_mul(1_000)
        .and_then(|base| base.checked_add(fraction_value))
        .ok_or(PlatformObserverError::ArithmeticOverflow("task CPU"))?;
    if millicores == 0 {
        return Err(PlatformObserverError::InvalidMetadata("task CPU"));
    }
    Ok(millicores)
}

fn positive_mib_to_bytes(value: u64, name: &'static str) -> Result<u64, PlatformObserverError> {
    if value == 0 {
        return Err(PlatformObserverError::InvalidMetadata(name));
    }
    value
        .checked_mul(MEBIBYTE)
        .ok_or(PlatformObserverError::ArithmeticOverflow(name))
}

fn parse_sha256_image_digest(value: &str) -> Result<[u8; 32], PlatformObserverError> {
    let encoded = value
        .strip_prefix("sha256:")
        .ok_or(PlatformObserverError::InvalidMetadata("ImageID"))?;
    if encoded.len() != 64
        || !encoded
            .bytes()
            .all(|byte| byte.is_ascii_digit() || (b'a'..=b'f').contains(&byte))
    {
        return Err(PlatformObserverError::InvalidMetadata("ImageID"));
    }
    let mut digest = [0_u8; 32];
    for (index, slot) in digest.iter_mut().enumerate() {
        let pair = &encoded[index * 2..index * 2 + 2];
        *slot = u8::from_str_radix(pair, 16)
            .map_err(|_| PlatformObserverError::InvalidMetadata("ImageID"))?;
    }
    if digest == [0; 32] {
        return Err(PlatformObserverError::InvalidMetadata("zero ImageID"));
    }
    Ok(digest)
}

fn fact(kind: PlatformFactKind, value: &str) -> [u8; 32] {
    canonical_platform_fact_receipt(kind, value.as_bytes())
}

fn reject_duplicate_json_keys(input: &[u8]) -> Result<(), PlatformObserverError> {
    let mut scanner = JsonScanner {
        input,
        cursor: 0,
        value_count: 0,
    };
    scanner.value(0)?;
    scanner.whitespace();
    if scanner.cursor != input.len() {
        return Err(PlatformObserverError::MalformedJson);
    }
    Ok(())
}

struct JsonScanner<'a> {
    input: &'a [u8],
    cursor: usize,
    value_count: usize,
}

impl JsonScanner<'_> {
    fn value(&mut self, depth: usize) -> Result<(), PlatformObserverError> {
        if depth > MAX_JSON_DEPTH {
            return Err(PlatformObserverError::JsonTooDeep);
        }
        self.value_count = self
            .value_count
            .checked_add(1)
            .ok_or(PlatformObserverError::JsonTooManyValues)?;
        if self.value_count > MAX_JSON_VALUES {
            return Err(PlatformObserverError::JsonTooManyValues);
        }
        self.whitespace();
        match self.input.get(self.cursor).copied() {
            Some(b'{') => self.object(depth + 1),
            Some(b'[') => self.array(depth + 1),
            Some(b'"') => self.string().map(|_| ()),
            Some(_) => self.primitive(),
            None => Err(PlatformObserverError::MalformedJson),
        }
    }

    fn object(&mut self, depth: usize) -> Result<(), PlatformObserverError> {
        self.cursor += 1;
        self.whitespace();
        let mut keys = HashSet::new();
        let mut member_count = 0_usize;
        if self.take(b'}') {
            return Ok(());
        }
        loop {
            member_count = member_count
                .checked_add(1)
                .ok_or(PlatformObserverError::JsonTooBroad)?;
            if member_count > MAX_JSON_MEMBERS_PER_CONTAINER {
                return Err(PlatformObserverError::JsonTooBroad);
            }
            self.whitespace();
            let raw = self.string()?;
            let key: String =
                serde_json::from_slice(raw).map_err(|_| PlatformObserverError::MalformedJson)?;
            if !keys.insert(key) {
                return Err(PlatformObserverError::DuplicateJsonKey);
            }
            self.whitespace();
            if !self.take(b':') {
                return Err(PlatformObserverError::MalformedJson);
            }
            self.value(depth)?;
            self.whitespace();
            if self.take(b'}') {
                return Ok(());
            }
            if !self.take(b',') {
                return Err(PlatformObserverError::MalformedJson);
            }
        }
    }

    fn array(&mut self, depth: usize) -> Result<(), PlatformObserverError> {
        self.cursor += 1;
        self.whitespace();
        if self.take(b']') {
            return Ok(());
        }
        let mut element_count = 0_usize;
        loop {
            element_count = element_count
                .checked_add(1)
                .ok_or(PlatformObserverError::JsonTooBroad)?;
            if element_count > MAX_JSON_MEMBERS_PER_CONTAINER {
                return Err(PlatformObserverError::JsonTooBroad);
            }
            self.value(depth)?;
            self.whitespace();
            if self.take(b']') {
                return Ok(());
            }
            if !self.take(b',') {
                return Err(PlatformObserverError::MalformedJson);
            }
        }
    }

    fn string(&mut self) -> Result<&[u8], PlatformObserverError> {
        let start = self.cursor;
        if !self.take(b'"') {
            return Err(PlatformObserverError::MalformedJson);
        }
        let mut escaped = false;
        while let Some(byte) = self.input.get(self.cursor).copied() {
            self.cursor += 1;
            if escaped {
                escaped = false;
            } else if byte == b'\\' {
                escaped = true;
            } else if byte == b'"' {
                if self.cursor - start > MAX_JSON_STRING_BYTES + 2 {
                    return Err(PlatformObserverError::JsonStringTooLong);
                }
                return Ok(&self.input[start..self.cursor]);
            } else if byte < 0x20 {
                return Err(PlatformObserverError::MalformedJson);
            }
            if self.cursor - start > MAX_JSON_STRING_BYTES + 2 {
                return Err(PlatformObserverError::JsonStringTooLong);
            }
        }
        Err(PlatformObserverError::MalformedJson)
    }

    fn primitive(&mut self) -> Result<(), PlatformObserverError> {
        let start = self.cursor;
        while self
            .input
            .get(self.cursor)
            .is_some_and(|byte| !byte.is_ascii_whitespace() && !b",]}".contains(byte))
        {
            self.cursor += 1;
        }
        if self.cursor == start {
            return Err(PlatformObserverError::MalformedJson);
        }
        Ok(())
    }

    fn whitespace(&mut self) {
        while self
            .input
            .get(self.cursor)
            .is_some_and(u8::is_ascii_whitespace)
        {
            self.cursor += 1;
        }
    }

    fn take(&mut self, expected: u8) -> bool {
        if self.input.get(self.cursor) == Some(&expected) {
            self.cursor += 1;
            true
        } else {
            false
        }
    }
}

#[derive(Clone)]
struct MountInfoEntry {
    root: Vec<u8>,
    mount_point: Vec<u8>,
    device: Vec<u8>,
    fs_type: Vec<u8>,
    source: Vec<u8>,
    mount_options: Vec<u8>,
    super_options: Vec<u8>,
}

struct ResolvedCgroupFile {
    mount_point: PathBuf,
    relative: PathBuf,
    device: Vec<u8>,
    fs_type: Vec<u8>,
}

fn inspect_authority_mount(
    entries: &[MountInfoEntry],
) -> Result<NativeMountEvidence, PlatformObserverError> {
    let directory = OpenOptions::new()
        .read(true)
        .custom_flags(libc::O_CLOEXEC | libc::O_NOFOLLOW | libc::O_DIRECTORY)
        .open(AUTHORITY_ROOT)
        .map_err(|_| PlatformObserverError::Io("open /app/guala"))?;
    let before = directory
        .metadata()
        .map_err(|_| PlatformObserverError::Io("fstat /app/guala"))?;
    if !before.is_dir() {
        return Err(PlatformObserverError::MountEvidence(
            "/app/guala is not a directory",
        ));
    }
    let authority = entries
        .iter()
        .filter(|entry| entry.mount_point == AUTHORITY_ROOT.as_bytes())
        .collect::<Vec<_>>();
    if authority.len() != 1 {
        return Err(PlatformObserverError::MountEvidence(
            "authority mount is absent or duplicated",
        ));
    }
    let authority = authority[0];
    if authority.fs_type != b"nfs4" || authority.root != b"/" || authority.source != b"127.0.0.1:/"
    {
        return Err(PlatformObserverError::MountEvidence(
            "authority mount is not nfs4",
        ));
    }
    validate_device(&authority.device)?;
    if authority.root.is_empty() || authority.source.is_empty() {
        return Err(PlatformObserverError::MountEvidence(
            "empty NFS root or source",
        ));
    }

    let mut filesystem: libc::statfs = unsafe { std::mem::zeroed() };
    let status = unsafe { libc::fstatfs(directory.as_raw_fd(), &mut filesystem) };
    if status != 0 {
        return Err(PlatformObserverError::Io("fstatfs /app/guala"));
    }
    if filesystem.f_type != NFS_SUPER_MAGIC {
        return Err(PlatformObserverError::MountEvidence(
            "filesystem magic is not NFS",
        ));
    }
    let observed_device = format!(
        "{}:{}",
        libc::major(before.dev()),
        libc::minor(before.dev())
    );
    if authority.device != observed_device.as_bytes() {
        return Err(PlatformObserverError::MountEvidence(
            "mount device differs from opened directory",
        ));
    }
    let after = directory
        .metadata()
        .map_err(|_| PlatformObserverError::Io("revalidate /app/guala inode"))?;
    if before.dev() != after.dev()
        || before.ino() != after.ino()
        || before.mode() != after.mode()
        || !after.is_dir()
    {
        return Err(PlatformObserverError::MountEvidence(
            "authority directory changed during observation",
        ));
    }
    let path_after = fs::symlink_metadata(AUTHORITY_ROOT)
        .map_err(|_| PlatformObserverError::Io("lstat /app/guala"))?;
    if path_after.file_type().is_symlink()
        || path_after.dev() != before.dev()
        || path_after.ino() != before.ino()
        || path_after.mode() != before.mode()
    {
        return Err(PlatformObserverError::MountEvidence(
            "authority path changed during observation",
        ));
    }
    Ok(NativeMountEvidence {
        mount_root_receipt: mount_fact_receipt(b"root", &authority.root),
        mount_source_receipt: mount_fact_receipt(b"source", &authority.source),
        mount_device_receipt: mount_fact_receipt(b"device", &authority.device),
        mount_options_receipt: {
            let mut options = authority.mount_options.clone();
            options.push(0);
            options.extend_from_slice(&authority.super_options);
            mount_fact_receipt(b"options", &options)
        },
        directory_device: before.dev(),
        directory_inode: before.ino(),
        authority_directory: directory,
    })
}

fn parse_mountinfo(input: &[u8]) -> Result<Vec<MountInfoEntry>, PlatformObserverError> {
    if input.is_empty() || !input.ends_with(b"\n") {
        return Err(PlatformObserverError::MountEvidence(
            "noncanonical mountinfo framing",
        ));
    }
    let mut entries = Vec::new();
    for line in input[..input.len() - 1].split(|byte| *byte == b'\n') {
        if line.is_empty() {
            return Err(PlatformObserverError::MountEvidence("empty mountinfo line"));
        }
        let fields: Vec<&[u8]> = line.split(|byte| *byte == b' ').collect();
        let separator = fields
            .iter()
            .position(|field| *field == b"-")
            .ok_or(PlatformObserverError::MountEvidence("mountinfo separator"))?;
        if separator < 6 || fields.len() != separator + 4 {
            return Err(PlatformObserverError::MountEvidence(
                "mountinfo field count",
            ));
        }
        entries.push(MountInfoEntry {
            device: decode_mount_field(fields[2])?,
            root: decode_mount_field(fields[3])?,
            mount_point: decode_mount_field(fields[4])?,
            mount_options: fields[5].to_vec(),
            fs_type: fields[separator + 1].to_vec(),
            source: decode_mount_field(fields[separator + 2])?,
            super_options: fields[separator + 3].to_vec(),
        });
    }
    Ok(entries)
}

fn decode_mount_field(input: &[u8]) -> Result<Vec<u8>, PlatformObserverError> {
    let mut output = Vec::with_capacity(input.len());
    let mut cursor = 0;
    while cursor < input.len() {
        if input[cursor] != b'\\' {
            output.push(input[cursor]);
            cursor += 1;
            continue;
        }
        let escape =
            input
                .get(cursor + 1..cursor + 4)
                .ok_or(PlatformObserverError::MountEvidence(
                    "truncated mountinfo escape",
                ))?;
        let decoded = match escape {
            b"040" => b' ',
            b"011" => b'\t',
            b"012" => b'\n',
            b"134" => b'\\',
            _ => {
                return Err(PlatformObserverError::MountEvidence(
                    "unknown mountinfo escape",
                ))
            }
        };
        output.push(decoded);
        cursor += 4;
    }
    Ok(output)
}

fn validate_device(device: &[u8]) -> Result<(), PlatformObserverError> {
    let mut parts = device.split(|byte| *byte == b':');
    for part in [parts.next(), parts.next()] {
        let part = part.ok_or(PlatformObserverError::MountEvidence("mount device"))?;
        if part.is_empty() || !part.iter().all(u8::is_ascii_digit) {
            return Err(PlatformObserverError::MountEvidence("mount device"));
        }
    }
    if parts.next().is_some() {
        return Err(PlatformObserverError::MountEvidence("mount device"));
    }
    Ok(())
}

fn mount_fact_receipt(label: &[u8], value: &[u8]) -> [u8; 32] {
    let mut digest = Sha256::new();
    digest.update(NFS_MOUNT_DOMAIN);
    digest.update(label);
    digest.update((value.len() as u64).to_le_bytes());
    digest.update(value);
    digest.finalize().into()
}

fn inspect_cgroup(
    mountinfo: &[MountInfoEntry],
) -> Result<NativeCgroupEvidence, PlatformObserverError> {
    let membership = read_bounded_path(
        Path::new(CGROUP_MEMBERSHIP_PATH),
        MAX_CGROUP_MEMBERSHIP_BYTES,
        "read cgroup membership",
    )?;
    let lines = parse_cgroup_membership(&membership)?;
    let cgroup2_count = mountinfo
        .iter()
        .filter(|entry| entry.fs_type == b"cgroup2")
        .count();
    if cgroup2_count == 1 {
        let path = lines
            .v2
            .as_deref()
            .ok_or(PlatformObserverError::CgroupEvidence(
                "missing v2 membership",
            ))?;
        inspect_cgroup_v2(mountinfo, path)
    } else if cgroup2_count == 0 {
        inspect_cgroup_v1(mountinfo, &lines)
    } else {
        Err(PlatformObserverError::CgroupEvidence(
            "duplicate cgroup2 mounts",
        ))
    }
}

#[derive(Default)]
struct CgroupMembership {
    cpu: Option<Vec<u8>>,
    memory: Option<Vec<u8>>,
    cpuset: Option<Vec<u8>>,
    v2: Option<Vec<u8>>,
}

fn parse_cgroup_membership(input: &[u8]) -> Result<CgroupMembership, PlatformObserverError> {
    if input.is_empty() || !input.ends_with(b"\n") {
        return Err(PlatformObserverError::CgroupEvidence("membership framing"));
    }
    let mut result = CgroupMembership::default();
    for line in input[..input.len() - 1].split(|byte| *byte == b'\n') {
        let fields: Vec<&[u8]> = line.split(|byte| *byte == b':').collect();
        if fields.len() != 3 || fields[2].is_empty() || fields[2][0] != b'/' {
            return Err(PlatformObserverError::CgroupEvidence("membership line"));
        }
        if fields[0] == b"0" && fields[1].is_empty() {
            set_once(&mut result.v2, fields[2], "duplicate cgroup v2 membership")?;
            continue;
        }
        for controller in fields[1].split(|byte| *byte == b',') {
            match controller {
                b"cpu" | b"cpuacct" => {
                    set_same(&mut result.cpu, fields[2], "CPU membership differs")?
                }
                b"memory" => {
                    set_once(&mut result.memory, fields[2], "duplicate memory membership")?
                }
                b"cpuset" => {
                    set_once(&mut result.cpuset, fields[2], "duplicate cpuset membership")?
                }
                _ => {}
            }
        }
    }
    Ok(result)
}

fn set_once(
    slot: &mut Option<Vec<u8>>,
    value: &[u8],
    reason: &'static str,
) -> Result<(), PlatformObserverError> {
    if slot.replace(value.to_vec()).is_some() {
        return Err(PlatformObserverError::CgroupEvidence(reason));
    }
    Ok(())
}

fn set_same(
    slot: &mut Option<Vec<u8>>,
    value: &[u8],
    reason: &'static str,
) -> Result<(), PlatformObserverError> {
    match slot {
        Some(current) if current != value => Err(PlatformObserverError::CgroupEvidence(reason)),
        Some(_) => Ok(()),
        None => {
            *slot = Some(value.to_vec());
            Ok(())
        }
    }
}

fn inspect_cgroup_v1(
    mounts: &[MountInfoEntry],
    membership: &CgroupMembership,
) -> Result<NativeCgroupEvidence, PlatformObserverError> {
    let cpu_path = controller_file(
        mounts,
        b"cpu",
        membership.cpu.as_deref(),
        "cpu.cfs_quota_us",
    )?;
    let cpu_period_path = controller_file(
        mounts,
        b"cpu",
        membership.cpu.as_deref(),
        "cpu.cfs_period_us",
    )?;
    let usage_path = controller_file(
        mounts,
        b"cpuacct",
        membership.cpu.as_deref(),
        "cpuacct.usage",
    )?;
    let memory_current_path = controller_file(
        mounts,
        b"memory",
        membership.memory.as_deref(),
        "memory.usage_in_bytes",
    )?;
    let memory_limit_path = controller_file(
        mounts,
        b"memory",
        membership.memory.as_deref(),
        "memory.limit_in_bytes",
    )?;
    let memory_stat_path = controller_file(
        mounts,
        b"memory",
        membership.memory.as_deref(),
        "memory.stat",
    )?;
    let cpuset_path = controller_file(
        mounts,
        b"cpuset",
        membership.cpuset.as_deref(),
        "cpuset.cpus",
    )?;

    let quota = parse_signed_limit(&read_small(&cpu_path)?, "CPU quota")?;
    let period = parse_positive_file_u64(&read_small(&cpu_period_path)?, "CPU period")?;
    let usage = parse_file_u64(&read_small(&usage_path)?, "CPU usage")?;
    let memory_limit = parse_positive_file_u64(&read_small(&memory_limit_path)?, "memory limit")?;
    let hierarchical = parse_memory_stat_limit(&read_small(&memory_stat_path)?)?;
    let memory_directory = RetainedCgroupMemoryDirectory::v1(
        open_resolved_cgroup_leaf_directory(&memory_current_path)?,
        memory_limit,
        hierarchical,
    );
    let memory_current = memory_directory.read_memory_current()?.current_bytes();
    let cpuset_bytes = read_small(&cpuset_path)?;
    let cpuset = trim_single_line(&cpuset_bytes, "cpuset")?;
    let cpuset_cpu_count = parse_cpuset_count(cpuset)?;
    let cpuset_receipt = canonical_platform_fact_receipt(PlatformFactKind::CgroupCpuset, cpuset);
    let supplied = SuppliedCgroupObservation::V1 {
        cpu_usage_nanoseconds: usage,
        memory_current_bytes: memory_current,
        leaf_cpu_quota_microseconds: quota,
        leaf_cpu_period_microseconds: period,
        leaf_memory_limit_bytes: memory_limit,
        hierarchical_memory_limit_bytes: hierarchical,
        cpuset_receipt,
        cpuset_cpu_count,
    };
    Ok(NativeCgroupEvidence {
        receipt: cgroup_receipt(&supplied),
        supplied,
        memory_directory,
    })
}

fn inspect_cgroup_v2(
    mounts: &[MountInfoEntry],
    membership_path: &[u8],
) -> Result<NativeCgroupEvidence, PlatformObserverError> {
    let cpu_max_path = unified_file(mounts, membership_path, "cpu.max")?;
    let cpu_stat_path = unified_file(mounts, membership_path, "cpu.stat")?;
    let memory_current_path = unified_file(mounts, membership_path, "memory.current")?;
    let memory_max_path = unified_file(mounts, membership_path, "memory.max")?;
    let cpuset_path = unified_file(mounts, membership_path, "cpuset.cpus.effective")?;
    let (quota, period) = parse_cpu_max(&read_small(&cpu_max_path)?)?;
    let usage = parse_cpu_stat(&read_small(&cpu_stat_path)?)?
        .checked_mul(1_000)
        .ok_or(PlatformObserverError::ArithmeticOverflow(
            "cgroup v2 CPU usage",
        ))?;
    let memory_max = parse_max_limit(&read_small(&memory_max_path)?, "memory max")?;
    let memory_directory = RetainedCgroupMemoryDirectory::v2(
        open_resolved_cgroup_leaf_directory(&memory_current_path)?,
        memory_max,
    );
    let memory_current = memory_directory.read_memory_current()?.current_bytes();
    let cpuset_bytes = read_small(&cpuset_path)?;
    let cpuset = trim_single_line(&cpuset_bytes, "cpuset")?;
    let cpuset_cpu_count = parse_cpuset_count(cpuset)?;
    let cpuset_receipt = canonical_platform_fact_receipt(PlatformFactKind::CgroupCpuset, cpuset);
    let supplied = SuppliedCgroupObservation::V2 {
        cpu_usage_nanoseconds: usage,
        memory_current_bytes: memory_current,
        cpu_quota_microseconds: quota,
        cpu_period_microseconds: period,
        memory_max_bytes: memory_max,
        cpuset_receipt,
        cpuset_cpu_count,
    };
    Ok(NativeCgroupEvidence {
        receipt: cgroup_receipt(&supplied),
        supplied,
        memory_directory,
    })
}

fn controller_file(
    mounts: &[MountInfoEntry],
    controller: &[u8],
    membership: Option<&[u8]>,
    filename: &str,
) -> Result<ResolvedCgroupFile, PlatformObserverError> {
    let membership = membership.ok_or(PlatformObserverError::CgroupEvidence(
        "missing v1 membership",
    ))?;
    let candidates: Vec<&MountInfoEntry> = mounts
        .iter()
        .filter(|entry| {
            entry.fs_type == b"cgroup"
                && entry
                    .super_options
                    .split(|byte| *byte == b',')
                    .any(|option| option == controller)
        })
        .collect();
    if candidates.len() != 1 {
        return Err(PlatformObserverError::CgroupEvidence(
            "controller mount is absent or duplicated",
        ));
    }
    resolved_cgroup_file(candidates[0], membership, filename)
}

fn unified_file(
    mounts: &[MountInfoEntry],
    membership: &[u8],
    filename: &str,
) -> Result<ResolvedCgroupFile, PlatformObserverError> {
    let candidates: Vec<&MountInfoEntry> = mounts
        .iter()
        .filter(|entry| entry.fs_type == b"cgroup2")
        .collect();
    if candidates.len() != 1 {
        return Err(PlatformObserverError::CgroupEvidence(
            "cgroup2 mount is absent or duplicated",
        ));
    }
    resolved_cgroup_file(candidates[0], membership, filename)
}

fn resolved_cgroup_file(
    mount: &MountInfoEntry,
    membership: &[u8],
    filename: &str,
) -> Result<ResolvedCgroupFile, PlatformObserverError> {
    let root = std::str::from_utf8(&mount.root)
        .map_err(|_| PlatformObserverError::CgroupEvidence("non-UTF8 cgroup root"))?;
    let mount_point = std::str::from_utf8(&mount.mount_point)
        .map_err(|_| PlatformObserverError::CgroupEvidence("non-UTF8 cgroup mountpoint"))?;
    let membership = std::str::from_utf8(membership)
        .map_err(|_| PlatformObserverError::CgroupEvidence("non-UTF8 cgroup membership"))?;
    let mount_is_below_cgroup_root = mount_point == CGROUP_ROOT
        || mount_point
            .strip_prefix(CGROUP_ROOT)
            .is_some_and(|suffix| suffix.starts_with('/'));
    if !mount_is_below_cgroup_root
        || !canonical_absolute_path(mount_point)
        || !canonical_absolute_path(root)
        || !canonical_absolute_path(membership)
        || filename.is_empty()
        || filename.contains('/')
        || filename == "."
        || filename == ".."
        || filename.bytes().any(|byte| byte.is_ascii_control())
    {
        return Err(PlatformObserverError::CgroupEvidence("unsafe cgroup path"));
    }
    let suffix = if root == "/" {
        membership.strip_prefix('/').unwrap_or(membership)
    } else {
        if membership == root {
            ""
        } else {
            membership
                .strip_prefix(root)
                .and_then(|value| value.strip_prefix('/'))
                .ok_or(PlatformObserverError::CgroupEvidence(
                    "membership is outside mount root",
                ))?
        }
    };
    let mut relative = PathBuf::new();
    if !suffix.is_empty() {
        relative.push(suffix);
    }
    relative.push(filename);
    Ok(ResolvedCgroupFile {
        mount_point: PathBuf::from(mount_point),
        relative,
        device: mount.device.clone(),
        fs_type: mount.fs_type.clone(),
    })
}

fn canonical_absolute_path(value: &str) -> bool {
    value == "/"
        || (value.starts_with('/')
            && !value.ends_with('/')
            && !value.contains("//")
            && !value.bytes().any(|byte| byte.is_ascii_control())
            && value
                .split('/')
                .skip(1)
                .all(|component| !component.is_empty() && component != "." && component != ".."))
}

fn read_small(path: &ResolvedCgroupFile) -> Result<Vec<u8>, PlatformObserverError> {
    let mount_fd = open_verified_cgroup_mount(path)?;
    let file_fd = openat2_beneath(
        mount_fd.as_raw_fd(),
        &path.relative,
        libc::O_RDONLY | libc::O_CLOEXEC | libc::O_NOFOLLOW,
        RESOLVE_BENEATH | RESOLVE_NO_MAGICLINKS | RESOLVE_NO_SYMLINKS | RESOLVE_NO_XDEV,
        "open cgroup file",
    )?;
    let mut file = fs::File::from(file_fd);
    validate_cgroup_file_identity(&file, mount_fd.as_raw_fd())?;
    read_bounded_file(&mut file, MAX_CGROUP_FILE_BYTES, "read cgroup file")
}

fn open_verified_cgroup_mount(path: &ResolvedCgroupFile) -> Result<OwnedFd, PlatformObserverError> {
    let root = OpenOptions::new()
        .read(true)
        .custom_flags(libc::O_CLOEXEC | libc::O_NOFOLLOW | libc::O_DIRECTORY)
        .open("/")
        .map_err(|_| PlatformObserverError::Io("open filesystem root"))?;
    let mount_relative = path
        .mount_point
        .strip_prefix("/")
        .map_err(|_| PlatformObserverError::CgroupEvidence("cgroup mount is not absolute"))?;
    let mount_fd = openat2_beneath(
        root.as_raw_fd(),
        mount_relative,
        libc::O_PATH | libc::O_CLOEXEC | libc::O_DIRECTORY,
        RESOLVE_BENEATH | RESOLVE_NO_MAGICLINKS | RESOLVE_NO_SYMLINKS,
        "open cgroup mount",
    )?;
    verify_cgroup_mount_fd(&mount_fd, &path.device, &path.fs_type)?;
    Ok(mount_fd)
}

fn open_resolved_cgroup_leaf_directory(
    path: &ResolvedCgroupFile,
) -> Result<OwnedFd, PlatformObserverError> {
    let mount_fd = open_verified_cgroup_mount(path)?;
    let parent = path
        .relative
        .parent()
        .ok_or(PlatformObserverError::CgroupEvidence(
            "cgroup file has no parent directory",
        ))?;
    if parent.as_os_str().is_empty() {
        return Ok(mount_fd);
    }
    let directory = openat2_beneath(
        mount_fd.as_raw_fd(),
        parent,
        libc::O_PATH | libc::O_CLOEXEC | libc::O_DIRECTORY,
        RESOLVE_BENEATH | RESOLVE_NO_MAGICLINKS | RESOLVE_NO_SYMLINKS | RESOLVE_NO_XDEV,
        "open cgroup leaf directory",
    )?;
    validate_cgroup_directory_identity(&directory, mount_fd.as_raw_fd())?;
    Ok(directory)
}

fn read_cgroup_u64_at(directory: &OwnedFd, filename: &Path) -> Result<u64, PlatformObserverError> {
    let (bytes, length) = read_fixed_cgroup_value_at(
        directory,
        filename,
        "open cgroup memory current",
        "read cgroup memory current",
    )?;
    parse_file_u64(&bytes[..length], "memory current")
}

fn read_cgroup_positive_u64_at(
    directory: &OwnedFd,
    filename: &Path,
    name: &'static str,
) -> Result<u64, PlatformObserverError> {
    let (bytes, length) = read_fixed_cgroup_value_at(
        directory,
        filename,
        "open cgroup memory limit",
        "read cgroup memory limit",
    )?;
    parse_positive_file_u64(&bytes[..length], name)
}

fn read_cgroup_max_at(
    directory: &OwnedFd,
    filename: &Path,
    name: &'static str,
) -> Result<Option<u64>, PlatformObserverError> {
    let (bytes, length) = read_fixed_cgroup_value_at(
        directory,
        filename,
        "open cgroup memory max",
        "read cgroup memory max",
    )?;
    parse_max_limit(&bytes[..length], name)
}

fn read_fixed_cgroup_value_at(
    directory: &OwnedFd,
    filename: &Path,
    open_operation: &'static str,
    read_operation: &'static str,
) -> Result<([u8; 22], usize), PlatformObserverError> {
    let mut file = open_cgroup_file_at(directory, filename, open_operation)?;

    // A u64 is at most 20 decimal digits. The kernel interface adds one
    // newline, and the final byte exists solely to detect trailing input.
    let mut bytes = [0_u8; 22];
    let mut length = 0;
    loop {
        if length == bytes.len() {
            return Err(PlatformObserverError::CgroupEvidence(
                "cgroup scalar exceeds fixed framing",
            ));
        }
        match file.read(&mut bytes[length..]) {
            Ok(0) => break,
            Ok(read) => length += read,
            Err(error) if error.kind() == std::io::ErrorKind::Interrupted => {}
            Err(_) => return Err(PlatformObserverError::Io(read_operation)),
        }
    }
    Ok((bytes, length))
}

fn open_cgroup_file_at(
    directory: &OwnedFd,
    filename: &Path,
    operation: &'static str,
) -> Result<File, PlatformObserverError> {
    let file_fd = openat2_beneath(
        directory.as_raw_fd(),
        filename,
        libc::O_RDONLY | libc::O_CLOEXEC | libc::O_NOFOLLOW,
        RESOLVE_BENEATH | RESOLVE_NO_MAGICLINKS | RESOLVE_NO_SYMLINKS | RESOLVE_NO_XDEV,
        operation,
    )?;
    let file = fs::File::from(file_fd);
    validate_cgroup_file_identity(&file, directory.as_raw_fd())?;
    Ok(file)
}

fn stream_v1_hierarchical_memory_limit_at(
    directory: &OwnedFd,
) -> Result<Option<u64>, PlatformObserverError> {
    let mut file = open_cgroup_file_at(
        directory,
        Path::new("memory.stat"),
        "open cgroup memory stat",
    )?;
    let mut buffer = [0_u8; 4 * 1024];
    let mut scanner = V1HierarchicalMemoryLimitScanner::new();

    loop {
        let read = match file.read(&mut buffer) {
            Ok(0) => break,
            Ok(read) => read,
            Err(error) if error.kind() == std::io::ErrorKind::Interrupted => continue,
            Err(_) => return Err(PlatformObserverError::Io("read cgroup memory stat")),
        };
        scanner.consume(&buffer[..read])?;
    }
    scanner.finish()
}

struct V1HierarchicalMemoryLimitScanner {
    prefix_index: usize,
    unrelated_line: bool,
    reading_target_value: bool,
    value: u64,
    digits: u64,
    leading_zero: bool,
    found: Option<u64>,
    saw_byte: bool,
    ended_with_newline: bool,
}

impl V1HierarchicalMemoryLimitScanner {
    const TARGET_PREFIX: &'static [u8] = b"hierarchical_memory_limit ";

    fn new() -> Self {
        Self {
            prefix_index: 0,
            unrelated_line: false,
            reading_target_value: false,
            value: 0,
            digits: 0,
            leading_zero: false,
            found: None,
            saw_byte: false,
            ended_with_newline: false,
        }
    }

    fn consume(&mut self, input: &[u8]) -> Result<(), PlatformObserverError> {
        for byte in input.iter().copied() {
            self.saw_byte = true;
            self.ended_with_newline = byte == b'\n';
            if byte == b'\r' {
                return Err(PlatformObserverError::CgroupEvidence("memory.stat framing"));
            }
            if self.reading_target_value {
                if byte == b'\n' {
                    if self.digits == 0
                        || self.value == 0
                        || self.found.replace(self.value).is_some()
                    {
                        return Err(PlatformObserverError::CgroupEvidence(
                            "hierarchical memory limit",
                        ));
                    }
                    self.reset_line();
                } else if byte.is_ascii_digit() {
                    if self.digits == 0 {
                        self.leading_zero = byte == b'0';
                    } else if self.leading_zero {
                        return Err(PlatformObserverError::CgroupEvidence(
                            "hierarchical memory limit",
                        ));
                    }
                    self.value = self
                        .value
                        .checked_mul(10)
                        .and_then(|current| current.checked_add(u64::from(byte - b'0')))
                        .ok_or(PlatformObserverError::CgroupEvidence(
                            "hierarchical memory limit",
                        ))?;
                    self.digits = self.digits.checked_add(1).ok_or(
                        PlatformObserverError::ArithmeticOverflow(
                            "hierarchical memory limit digits",
                        ),
                    )?;
                } else {
                    return Err(PlatformObserverError::CgroupEvidence(
                        "hierarchical memory limit",
                    ));
                }
                continue;
            }
            if self.unrelated_line {
                if byte == b'\n' {
                    self.reset_line();
                }
                continue;
            }
            if byte == Self::TARGET_PREFIX[self.prefix_index] {
                self.prefix_index += 1;
                if self.prefix_index == Self::TARGET_PREFIX.len() {
                    self.reading_target_value = true;
                    self.value = 0;
                    self.digits = 0;
                    self.leading_zero = false;
                }
            } else if byte == b'\n' {
                self.reset_line();
            } else {
                self.unrelated_line = true;
            }
        }
        Ok(())
    }

    fn finish(self) -> Result<Option<u64>, PlatformObserverError> {
        if !self.saw_byte || !self.ended_with_newline || self.reading_target_value {
            return Err(PlatformObserverError::CgroupEvidence("memory.stat framing"));
        }
        Ok(self.found)
    }

    fn reset_line(&mut self) {
        self.prefix_index = 0;
        self.unrelated_line = false;
        self.reading_target_value = false;
        self.value = 0;
        self.digits = 0;
        self.leading_zero = false;
    }
}

fn validate_cgroup_file_identity(
    file: &File,
    directory: RawFd,
) -> Result<(), PlatformObserverError> {
    let metadata = file
        .metadata()
        .map_err(|_| PlatformObserverError::Io("fstat cgroup file"))?;
    let mut directory_status: libc::stat = unsafe { std::mem::zeroed() };
    if unsafe { libc::fstat(directory, &mut directory_status) } != 0 {
        return Err(PlatformObserverError::Io("fstat cgroup directory"));
    }
    if !metadata.file_type().is_file() || metadata.dev() != directory_status.st_dev {
        return Err(PlatformObserverError::CgroupEvidence(
            "cgroup file identity differs from its directory",
        ));
    }
    Ok(())
}

fn validate_cgroup_directory_identity(
    directory: &OwnedFd,
    mount: RawFd,
) -> Result<(), PlatformObserverError> {
    let mut directory_status: libc::stat = unsafe { std::mem::zeroed() };
    let mut mount_status: libc::stat = unsafe { std::mem::zeroed() };
    if unsafe { libc::fstat(directory.as_raw_fd(), &mut directory_status) } != 0
        || unsafe { libc::fstat(mount, &mut mount_status) } != 0
    {
        return Err(PlatformObserverError::Io("fstat cgroup directory"));
    }
    if directory_status.st_dev != mount_status.st_dev
        || directory_status.st_mode & libc::S_IFMT != libc::S_IFDIR
    {
        return Err(PlatformObserverError::CgroupEvidence(
            "cgroup directory identity differs from its mount",
        ));
    }
    Ok(())
}

#[repr(C)]
struct OpenHow {
    flags: u64,
    mode: u64,
    resolve: u64,
}

fn openat2_beneath(
    directory: RawFd,
    path: &Path,
    flags: i32,
    resolve: u64,
    operation: &'static str,
) -> Result<OwnedFd, PlatformObserverError> {
    if path.as_os_str().is_empty() || path.is_absolute() {
        return Err(PlatformObserverError::CgroupEvidence(
            "noncanonical cgroup relative path",
        ));
    }
    let encoded = CString::new(path.as_os_str().as_bytes())
        .map_err(|_| PlatformObserverError::CgroupEvidence("NUL in cgroup path"))?;
    let how = OpenHow {
        flags: flags as u64,
        mode: 0,
        resolve,
    };
    let descriptor = unsafe {
        libc::syscall(
            libc::SYS_openat2,
            directory,
            encoded.as_ptr(),
            &how,
            std::mem::size_of::<OpenHow>(),
        )
    };
    if descriptor < 0 {
        return Err(PlatformObserverError::Io(operation));
    }
    Ok(unsafe { OwnedFd::from_raw_fd(descriptor as RawFd) })
}

fn verify_cgroup_mount_fd(
    mount: &OwnedFd,
    expected_device: &[u8],
    fs_type: &[u8],
) -> Result<(), PlatformObserverError> {
    let mut status: libc::stat = unsafe { std::mem::zeroed() };
    if unsafe { libc::fstat(mount.as_raw_fd(), &mut status) } != 0 {
        return Err(PlatformObserverError::Io("fstat cgroup mount"));
    }
    let observed_device = format!(
        "{}:{}",
        libc::major(status.st_dev),
        libc::minor(status.st_dev)
    );
    if observed_device.as_bytes() != expected_device {
        return Err(PlatformObserverError::CgroupEvidence(
            "cgroup mount device changed",
        ));
    }
    let mut filesystem: libc::statfs = unsafe { std::mem::zeroed() };
    if unsafe { libc::fstatfs(mount.as_raw_fd(), &mut filesystem) } != 0 {
        return Err(PlatformObserverError::Io("fstatfs cgroup mount"));
    }
    let expected_magic = match fs_type {
        b"cgroup" => CGROUP_SUPER_MAGIC,
        b"cgroup2" => CGROUP2_SUPER_MAGIC,
        _ => {
            return Err(PlatformObserverError::CgroupEvidence(
                "unexpected cgroup filesystem type",
            ))
        }
    };
    if filesystem.f_type != expected_magic {
        return Err(PlatformObserverError::CgroupEvidence(
            "cgroup filesystem magic differs",
        ));
    }
    Ok(())
}

fn read_bounded_path(
    path: &Path,
    maximum: usize,
    operation: &'static str,
) -> Result<Vec<u8>, PlatformObserverError> {
    let mut file = OpenOptions::new()
        .read(true)
        .custom_flags(libc::O_CLOEXEC | libc::O_NOFOLLOW)
        .open(path)
        .map_err(|_| PlatformObserverError::Io(operation))?;
    read_bounded_file(&mut file, maximum, operation)
}

fn read_bounded_file(
    file: &mut fs::File,
    maximum: usize,
    operation: &'static str,
) -> Result<Vec<u8>, PlatformObserverError> {
    let limit = u64::try_from(maximum)
        .map_err(|_| PlatformObserverError::ArithmeticOverflow("read bound"))?
        .checked_add(1)
        .ok_or(PlatformObserverError::ArithmeticOverflow("read bound"))?;
    let mut bytes = Vec::new();
    std::io::Read::by_ref(file)
        .take(limit)
        .read_to_end(&mut bytes)
        .map_err(|_| PlatformObserverError::Io(operation))?;
    if bytes.len() > maximum {
        return Err(PlatformObserverError::CgroupEvidence(
            "kernel input exceeds bound",
        ));
    }
    Ok(bytes)
}

fn trim_single_line<'a>(
    input: &'a [u8],
    name: &'static str,
) -> Result<&'a [u8], PlatformObserverError> {
    let value = input
        .strip_suffix(b"\n")
        .ok_or(PlatformObserverError::CgroupEvidence(name))?;
    if value.is_empty() || value.contains(&b'\n') || value.contains(&b'\r') {
        return Err(PlatformObserverError::CgroupEvidence(name));
    }
    Ok(value)
}

fn parse_file_u64(input: &[u8], name: &'static str) -> Result<u64, PlatformObserverError> {
    let text = std::str::from_utf8(trim_single_line(input, name)?)
        .map_err(|_| PlatformObserverError::CgroupEvidence(name))?;
    if !text.bytes().all(|byte| byte.is_ascii_digit()) || (text.len() > 1 && text.starts_with('0'))
    {
        return Err(PlatformObserverError::CgroupEvidence(name));
    }
    text.parse()
        .map_err(|_| PlatformObserverError::CgroupEvidence(name))
}

fn parse_positive_file_u64(input: &[u8], name: &'static str) -> Result<u64, PlatformObserverError> {
    let value = parse_file_u64(input, name)?;
    if value == 0 {
        return Err(PlatformObserverError::CgroupEvidence(name));
    }
    Ok(value)
}

fn parse_signed_limit(
    input: &[u8],
    name: &'static str,
) -> Result<Option<u64>, PlatformObserverError> {
    let value = trim_single_line(input, name)?;
    if value == b"-1" {
        return Ok(None);
    }
    Ok(Some(parse_positive_file_u64(input, name)?))
}

fn parse_max_limit(input: &[u8], name: &'static str) -> Result<Option<u64>, PlatformObserverError> {
    let value = trim_single_line(input, name)?;
    if value == b"max" {
        return Ok(None);
    }
    Ok(Some(parse_positive_file_u64(input, name)?))
}

fn parse_memory_stat_limit(input: &[u8]) -> Result<Option<u64>, PlatformObserverError> {
    if input.is_empty() || !input.ends_with(b"\n") || input.contains(&b'\r') {
        return Err(PlatformObserverError::CgroupEvidence("memory.stat framing"));
    }
    let text = std::str::from_utf8(input)
        .map_err(|_| PlatformObserverError::CgroupEvidence("memory.stat UTF-8"))?;
    let mut found = None;
    let mut names = HashSet::new();
    for line in text[..text.len() - 1].split('\n') {
        let (name, value) = two_canonical_fields(line, "memory.stat line")?;
        if !names.insert(name) {
            return Err(PlatformObserverError::CgroupEvidence(
                "duplicate memory.stat key",
            ));
        }
        if name == "hierarchical_memory_limit" {
            if found.is_some() {
                return Err(PlatformObserverError::CgroupEvidence(
                    "duplicate hierarchical memory limit",
                ));
            }
            let parsed = value
                .parse::<u64>()
                .map_err(|_| PlatformObserverError::CgroupEvidence("hierarchical memory limit"))?;
            if parsed == 0 {
                return Err(PlatformObserverError::CgroupEvidence(
                    "hierarchical memory limit",
                ));
            }
            found = Some(parsed);
        }
    }
    Ok(found)
}

fn parse_cpu_max(input: &[u8]) -> Result<(Option<u64>, u64), PlatformObserverError> {
    let value = std::str::from_utf8(trim_single_line(input, "cpu.max")?)
        .map_err(|_| PlatformObserverError::CgroupEvidence("cpu.max"))?;
    let (quota, period) = two_canonical_fields(value, "cpu.max")?;
    let quota = if quota == "max" {
        None
    } else {
        Some(
            quota
                .parse::<u64>()
                .map_err(|_| PlatformObserverError::CgroupEvidence("cpu.max quota"))?,
        )
    };
    let period = period
        .parse::<u64>()
        .map_err(|_| PlatformObserverError::CgroupEvidence("cpu.max period"))?;
    if quota == Some(0) || period == 0 {
        return Err(PlatformObserverError::CgroupEvidence("cpu.max zero"));
    }
    Ok((quota, period))
}

fn parse_cpu_stat(input: &[u8]) -> Result<u64, PlatformObserverError> {
    if input.is_empty() || !input.ends_with(b"\n") || input.contains(&b'\r') {
        return Err(PlatformObserverError::CgroupEvidence("cpu.stat framing"));
    }
    let text = std::str::from_utf8(input)
        .map_err(|_| PlatformObserverError::CgroupEvidence("cpu.stat UTF-8"))?;
    let mut usage = None;
    let mut names = HashSet::new();
    for line in text[..text.len() - 1].split('\n') {
        let (name, value) = two_canonical_fields(line, "cpu.stat line")?;
        if !names.insert(name) {
            return Err(PlatformObserverError::CgroupEvidence(
                "duplicate cpu.stat key",
            ));
        }
        if name == "usage_usec" {
            if usage.is_some() {
                return Err(PlatformObserverError::CgroupEvidence("duplicate CPU usage"));
            }
            usage = Some(
                value
                    .parse::<u64>()
                    .map_err(|_| PlatformObserverError::CgroupEvidence("CPU usage"))?,
            );
        }
    }
    usage.ok_or(PlatformObserverError::CgroupEvidence("missing CPU usage"))
}

fn two_canonical_fields<'a>(
    line: &'a str,
    name: &'static str,
) -> Result<(&'a str, &'a str), PlatformObserverError> {
    let (left, right) = line
        .split_once(' ')
        .ok_or(PlatformObserverError::CgroupEvidence(name))?;
    if left.is_empty()
        || right.is_empty()
        || left.bytes().any(|byte| byte.is_ascii_whitespace())
        || right.bytes().any(|byte| byte.is_ascii_whitespace())
    {
        return Err(PlatformObserverError::CgroupEvidence(name));
    }
    Ok((left, right))
}

fn parse_cpuset_count(input: &[u8]) -> Result<u32, PlatformObserverError> {
    let text = std::str::from_utf8(input)
        .map_err(|_| PlatformObserverError::CgroupEvidence("cpuset UTF-8"))?;
    let mut prior_end = None;
    let mut total = 0_u64;
    for component in text.split(',') {
        let mut ends = component.split('-');
        let start = parse_cpuset_cpu(ends.next().unwrap_or_default())?;
        let end = ends
            .next()
            .map(parse_cpuset_cpu)
            .transpose()?
            .unwrap_or(start);
        if ends.next().is_some() || end < start || prior_end.is_some_and(|prior| start <= prior) {
            return Err(PlatformObserverError::CgroupEvidence(
                "cpuset overlap or ordering",
            ));
        }
        prior_end = Some(end);
        total = total
            .checked_add(u64::from(end) - u64::from(start) + 1)
            .ok_or(PlatformObserverError::ArithmeticOverflow("cpuset count"))?;
    }
    u32::try_from(total).map_err(|_| PlatformObserverError::ArithmeticOverflow("cpuset count"))
}

fn parse_cpuset_cpu(value: &str) -> Result<u32, PlatformObserverError> {
    if value.is_empty()
        || (value.len() > 1 && value.starts_with('0'))
        || !value.bytes().all(|byte| byte.is_ascii_digit())
    {
        return Err(PlatformObserverError::CgroupEvidence("cpuset range"));
    }
    value
        .parse::<u32>()
        .map_err(|_| PlatformObserverError::CgroupEvidence("cpuset range"))
}

fn cgroup_receipt(value: &SuppliedCgroupObservation) -> [u8; 32] {
    let mut digest = Sha256::new();
    digest.update(CGROUP_EVIDENCE_DOMAIN);
    match value {
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
            digest_option(&mut digest, *leaf_cpu_quota_microseconds);
            digest.update(leaf_cpu_period_microseconds.to_le_bytes());
            digest.update(leaf_memory_limit_bytes.to_le_bytes());
            digest_option(&mut digest, *hierarchical_memory_limit_bytes);
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
            digest_option(&mut digest, *cpu_quota_microseconds);
            digest.update(cpu_period_microseconds.to_le_bytes());
            digest_option(&mut digest, *memory_max_bytes);
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

#[cfg(test)]
mod tests {
    use super::*;
    use std::sync::atomic::{AtomicU64, Ordering};

    static TEST_DIRECTORY_SEQUENCE: AtomicU64 = AtomicU64::new(0);

    struct TestDirectories(Vec<PathBuf>);

    impl Drop for TestDirectories {
        fn drop(&mut self) {
            for path in self.0.iter().rev() {
                let _ = fs::remove_dir_all(path);
            }
        }
    }

    fn fresh_test_directory(label: &str) -> (PathBuf, TestDirectories) {
        let sequence = TEST_DIRECTORY_SEQUENCE.fetch_add(1, Ordering::Relaxed);
        let path = env::temp_dir().join(format!(
            "guala-platform-observer-{}-{sequence}-{label}",
            std::process::id()
        ));
        fs::create_dir(&path).unwrap();
        (path.clone(), TestDirectories(vec![path]))
    }

    fn open_test_directory(path: &Path) -> OwnedFd {
        OwnedFd::from(
            OpenOptions::new()
                .read(true)
                .custom_flags(libc::O_CLOEXEC | libc::O_NOFOLLOW | libc::O_DIRECTORY)
                .open(path)
                .unwrap(),
        )
    }

    const BODY: &str = r#"{
        "Cluster":"arn:aws:ecs:us-east-1:123456789012:cluster/prod",
        "TaskARN":"arn:aws:ecs:us-east-1:123456789012:task/prod/0123456789abcdef0123456789abcdef",
        "Family":"dsf-ai-task",
        "Revision":"842",
        "ServiceName":"dsf-ai-service-lb",
        "LaunchType":"FARGATE",
        "Limits":{"CPU":4,"Memory":16384},
        "EphemeralStorageMetrics":{"Utilized":1478,"Reserved":20496},
        "Containers":[
          {"Name":"supervisor","Type":"INTERNAL","ImageID":"sha256:bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"},
          {"Name":"dsf-ai","Type":"NORMAL","ImageID":"sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"}
        ]
    }"#;

    fn http(headers: &str, wire_body: &[u8]) -> Vec<u8> {
        let mut response =
            format!("HTTP/1.1 200 OK\r\nContent-Type: application/json\r\n{headers}\r\n")
                .into_bytes();
        response.extend_from_slice(wire_body);
        response
    }

    #[test]
    fn exact_runtime_metadata_uri_is_required() {
        let id = "0123456789abcdef0123456789abcdef-0123456789";
        assert_eq!(
            metadata_task_target(&format!("http://169.254.170.2/v4/{id}")).unwrap(),
            format!("/v4/{id}/task")
        );
        for invalid in [
            "https://169.254.170.2/v4/0123456789abcdef0123456789abcdef-0123456789",
            "http://127.0.0.1/v4/0123456789abcdef0123456789abcdef-0123456789",
            "http://169.254.170.2/v4/0123456789ABCDEF0123456789abcdef-0123456789",
            "http://169.254.170.2/v4/0123456789abcdef0123456789abcdef%2d0123456789",
            "http://169.254.170.2/v4/short",
        ] {
            assert!(metadata_task_target(invalid).is_err(), "accepted {invalid}");
        }
    }

    #[test]
    fn live_chunked_framing_and_content_length_are_exact() {
        let chunked = format!("{:x}\r\n{}\r\n0\r\n\r\n", BODY.len(), BODY);
        assert_eq!(
            decode_http_response(&http("Transfer-Encoding: chunked\r\n", chunked.as_bytes()))
                .unwrap(),
            BODY.as_bytes()
        );
        assert_eq!(
            decode_http_response(&http(
                &format!("Content-Length: {}\r\n", BODY.len()),
                BODY.as_bytes(),
            ))
            .unwrap(),
            BODY.as_bytes()
        );

        let ambiguous = http(
            &format!(
                "Content-Length: {}\r\nTransfer-Encoding: chunked\r\n",
                BODY.len()
            ),
            BODY.as_bytes(),
        );
        assert_eq!(
            decode_http_response(&ambiguous).unwrap_err(),
            PlatformObserverError::AmbiguousBodyFraming
        );
    }

    #[test]
    fn chunk_truncation_extensions_trailers_and_trailing_bytes_are_rejected() {
        for wire in [
            b"4\r\nabc\r\n0\r\n\r\n".as_slice(),
            b"4;x=1\r\nabcd\r\n0\r\n\r\n".as_slice(),
            b"4\r\nabcd\r\n0\r\nX: y\r\n\r\n".as_slice(),
            b"4\r\nabcd\r\n0\r\n\r\nextra".as_slice(),
        ] {
            assert!(decode_chunked(wire).is_err());
        }
        assert_eq!(
            decode_content_length(b"4", b"abcdx").unwrap_err(),
            PlatformObserverError::TrailingHttpBytes
        );
    }

    #[test]
    fn duplicate_json_keys_are_rejected_at_every_depth() {
        for json in [
            br#"{"a":1,"a":2}"#.as_slice(),
            br#"{"a":{"b":1,"b":2}}"#.as_slice(),
        ] {
            assert_eq!(
                reject_duplicate_json_keys(json).unwrap_err(),
                PlatformObserverError::DuplicateJsonKey
            );
        }
        reject_duplicate_json_keys(BODY.as_bytes()).unwrap();
    }

    #[test]
    fn live_metadata_shape_maps_exact_facts_and_units() {
        reject_duplicate_json_keys(BODY.as_bytes()).unwrap();
        let parsed = parse_task_metadata(BODY.as_bytes()).unwrap();
        assert_eq!(parsed.task_revision, 842);
        assert_eq!(parsed.task_cpu_millicores, 4_000);
        assert_eq!(parsed.task_memory_bytes, 16_384 * MEBIBYTE);
        assert_eq!(parsed.ephemeral_utilized_bytes, 1_478 * MEBIBYTE);
        assert_eq!(parsed.ephemeral_reserved_bytes, 20_496 * MEBIBYTE);
        assert_eq!(parsed.image_digest, [0xaa; 32]);
        assert_eq!(
            parsed.service_receipt,
            fact(PlatformFactKind::Service, "dsf-ai-service-lb")
        );
    }

    #[test]
    fn metadata_cross_bindings_and_canonical_values_fail_closed() {
        for invalid in [
            BODY.replace("cluster/prod", "cluster/other"),
            BODY.replace("\"842\"", "\"0842\""),
            BODY.replace("sha256:aaaaaaaa", "sha256:AAAAAAAA"),
            BODY.replace("\"NORMAL\"", "\"INTERNAL\""),
        ] {
            assert!(parse_task_metadata(invalid.as_bytes()).is_err());
        }
        let duplicate = BODY.replace(
            "{\"Name\":\"supervisor\",\"Type\":\"INTERNAL\"",
            "{\"Name\":\"dsf-ai\",\"Type\":\"INTERNAL\"",
        );
        assert!(parse_task_metadata(duplicate.as_bytes()).is_err());
    }

    #[test]
    fn mountinfo_escape_and_cgroup_value_parsers_are_bounded_and_exact() {
        let mounts =
            parse_mountinfo(b"36 25 0:42 / /app/guala rw,nosuid - nfs4 127.0.0.1:/ rw,vers=4.1\n")
                .unwrap();
        assert_eq!(mounts.len(), 1);
        assert_eq!(mounts[0].root, b"/");
        assert_eq!(mounts[0].source, b"127.0.0.1:/");
        assert_eq!(decode_mount_field(b"/a\\040b").unwrap(), b"/a b");
        assert!(decode_mount_field(b"/a\\000b").is_err());

        assert_eq!(parse_signed_limit(b"-1\n", "quota").unwrap(), None);
        assert_eq!(
            parse_signed_limit(b"400000\n", "quota").unwrap(),
            Some(400_000)
        );
        assert_eq!(parse_cpu_max(b"max 100000\n").unwrap(), (None, 100_000));
        assert_eq!(parse_cpuset_count(b"0-3").unwrap(), 4);
        assert!(parse_cpuset_count(b"0-3,3-4").is_err());
        assert_eq!(
            parse_memory_stat_limit(b"cache 1\nhierarchical_memory_limit 17179869184\n").unwrap(),
            Some(17_179_869_184)
        );
        assert!(parse_memory_stat_limit(b"hierarchical_memory_limit 1").is_err());
        assert!(parse_memory_stat_limit(b"hierarchical_memory_limit  1\n").is_err());
        assert!(parse_memory_stat_limit(b"hierarchical_memory_limit\t1\n").is_err());
        assert_eq!(
            parse_cpu_stat(b"usage_usec 42\nuser_usec 20\n").unwrap(),
            42
        );
        assert!(parse_cpu_stat(b"usage_usec 42\nusage_usec 43\n").is_err());
        assert!(parse_cpu_stat(b"usage_usec  42\n").is_err());
        assert!(parse_cpu_max(b"max  100000\n").is_err());
        assert!(parse_cpu_max(b"max\t100000\n").is_err());
    }

    #[test]
    fn cgroup_resolution_requires_component_boundaries() {
        let mount = MountInfoEntry {
            root: b"/ecs/task".to_vec(),
            mount_point: b"/sys/fs/cgroup/memory".to_vec(),
            device: b"0:1".to_vec(),
            fs_type: b"cgroup".to_vec(),
            source: b"cgroup".to_vec(),
            mount_options: b"rw".to_vec(),
            super_options: b"rw,memory".to_vec(),
        };
        let direct = resolved_cgroup_file(&mount, b"/ecs/task", "memory.current").unwrap();
        assert_eq!(direct.mount_point, PathBuf::from("/sys/fs/cgroup/memory"));
        assert_eq!(direct.relative, PathBuf::from("memory.current"));
        let child = resolved_cgroup_file(&mount, b"/ecs/task/child", "memory.current").unwrap();
        assert_eq!(child.mount_point, PathBuf::from("/sys/fs/cgroup/memory"));
        assert_eq!(child.relative, PathBuf::from("child/memory.current"));
        assert!(resolved_cgroup_file(&mount, b"/ecs/task-other", "memory.current").is_err());

        let mut wrong_mount = mount.clone();
        wrong_mount.mount_point = b"/sys/fs/cgroup-foreign".to_vec();
        assert!(resolved_cgroup_file(&wrong_mount, b"/ecs/task", "memory.current").is_err());
        wrong_mount.mount_point = b"/sys/fs/cgroup/memory/../foreign".to_vec();
        assert!(resolved_cgroup_file(&wrong_mount, b"/ecs/task", "memory.current").is_err());
        assert!(resolved_cgroup_file(&mount, b"/ecs/task/../other", "memory.current").is_err());
    }

    #[test]
    fn current_kernel_cgroup_is_read_beneath_verified_mount_fds() {
        let mountinfo = read_bounded_path(
            Path::new(MOUNTINFO_PATH),
            MAX_MOUNTINFO_BYTES,
            "test read mountinfo",
        )
        .unwrap();
        let mounts = parse_mountinfo(&mountinfo).unwrap();
        let evidence = inspect_cgroup(&mounts).unwrap();
        assert_ne!(evidence.receipt, [0; 32]);
        assert!(
            evidence
                .memory_directory
                .read_memory_current()
                .unwrap()
                .current_bytes()
                > 0
        );
    }

    #[test]
    fn retained_directory_reads_fresh_v1_and_v2_memory_values() {
        let (path, _cleanup) = fresh_test_directory("fresh-values");
        fs::write(path.join("memory.current"), b"41\n").unwrap();
        fs::write(path.join("memory.usage_in_bytes"), b"73\n").unwrap();

        let v2 = RetainedCgroupMemoryDirectory::v2(open_test_directory(&path), Some(1));
        let v1 = RetainedCgroupMemoryDirectory::v1(open_test_directory(&path), 1, None);
        assert_eq!(v2.read_memory_current().unwrap().current_bytes(), 41);
        assert_eq!(v1.read_memory_current().unwrap().current_bytes(), 73);

        fs::write(path.join("memory.current"), b"42\n").unwrap();
        fs::write(path.join("memory.usage_in_bytes"), b"74\n").unwrap();
        assert_eq!(v2.read_memory_current().unwrap().current_bytes(), 42);
        assert_eq!(v1.read_memory_current().unwrap().current_bytes(), 74);
    }

    #[test]
    fn retained_raw_limits_produce_only_exact_finite_cgroup_ceilings() {
        let (path, _cleanup) = fresh_test_directory("memory-ceilings");
        let unlimited = v1_unlimited_memory_sentinel_bytes().unwrap();

        let v1_intersection =
            RetainedCgroupMemoryDirectory::v1(open_test_directory(&path), 8_192, Some(4_096));
        assert_eq!(v1_intersection.finite_memory_ceiling().unwrap(), 4_096);
        match v1_intersection.interface {
            CgroupMemoryInterface::V1 {
                leaf_memory_limit_bytes,
                hierarchical_memory_limit_bytes,
            } => {
                assert_eq!(leaf_memory_limit_bytes, 8_192);
                assert_eq!(hierarchical_memory_limit_bytes, Some(4_096));
            }
            CgroupMemoryInterface::V2 { .. } => panic!("v1 limits changed interface"),
        }

        let leaf_is_lower =
            RetainedCgroupMemoryDirectory::v1(open_test_directory(&path), 4_096, Some(8_192));
        assert_eq!(leaf_is_lower.finite_memory_ceiling().unwrap(), 4_096);
        let no_hierarchical =
            RetainedCgroupMemoryDirectory::v1(open_test_directory(&path), 4_096, None);
        assert_eq!(no_hierarchical.finite_memory_ceiling().unwrap(), 4_096);

        let finite_hierarchical =
            RetainedCgroupMemoryDirectory::v1(open_test_directory(&path), unlimited, Some(4_096));
        assert_eq!(finite_hierarchical.finite_memory_ceiling().unwrap(), 4_096);
        let finite_leaf =
            RetainedCgroupMemoryDirectory::v1(open_test_directory(&path), 4_096, Some(unlimited));
        assert_eq!(finite_leaf.finite_memory_ceiling().unwrap(), 4_096);

        let entirely_unbounded = RetainedCgroupMemoryDirectory::v1(
            open_test_directory(&path),
            unlimited,
            Some(unlimited),
        );
        assert!(entirely_unbounded.finite_memory_ceiling().is_err());
        let leaf_unbounded_without_hierarchy =
            RetainedCgroupMemoryDirectory::v1(open_test_directory(&path), unlimited, None);
        assert!(leaf_unbounded_without_hierarchy
            .finite_memory_ceiling()
            .is_err());

        let above_unlimited = unlimited.checked_add(1).unwrap();
        let leaf_above_unlimited = RetainedCgroupMemoryDirectory::v1(
            open_test_directory(&path),
            above_unlimited,
            Some(4_096),
        );
        assert!(leaf_above_unlimited.finite_memory_ceiling().is_err());
        let hierarchical_above_unlimited = RetainedCgroupMemoryDirectory::v1(
            open_test_directory(&path),
            4_096,
            Some(above_unlimited),
        );
        assert!(hierarchical_above_unlimited
            .finite_memory_ceiling()
            .is_err());

        let finite_v2 = RetainedCgroupMemoryDirectory::v2(open_test_directory(&path), Some(16_384));
        assert_eq!(finite_v2.finite_memory_ceiling().unwrap(), 16_384);
        let unbounded_v2 = RetainedCgroupMemoryDirectory::v2(open_test_directory(&path), None);
        assert!(unbounded_v2.finite_memory_ceiling().is_err());
    }

    #[test]
    fn requested_mapping_page_rounding_and_headroom_are_exact() {
        let page = 4_096;
        assert_eq!(page_rounded_bytes(0, page).unwrap(), 0);
        assert_eq!(page_rounded_bytes(1, page).unwrap(), page);
        assert_eq!(page_rounded_bytes(page, page).unwrap(), page);
        assert_eq!(page_rounded_bytes(page + 1, page).unwrap(), page * 2);
        assert!(page_rounded_bytes(u64::MAX, page).is_err());
        assert!(page_rounded_bytes(1, 0).is_err());

        assert_eq!(
            window_page_rounded_bytes(page + 1, page, page * 4, page * 2).unwrap(),
            page * 2
        );
        assert!(window_page_rounded_bytes(page * 2 + 1, page, page * 4, page * 2).is_err());
        assert!(window_page_rounded_bytes(1, page, page, page + 1).is_err());
        assert_eq!(
            window_page_rounded_bytes(page, page, page, 0).unwrap(),
            page
        );
    }

    #[test]
    fn physical_mapping_window_preserves_request_and_samples_post_state() {
        let (path, _cleanup) = fresh_test_directory("current-allocation-window");
        let page = native_page_size_bytes().unwrap();
        let ceiling = page.checked_mul(4).unwrap();
        let before = page.checked_mul(2).unwrap();
        fs::write(path.join("memory.current"), format!("{before}\n")).unwrap();
        fs::write(path.join("memory.max"), format!("{ceiling}\n")).unwrap();
        let memory = RetainedCgroupMemoryDirectory::v2(open_test_directory(&path), Some(ceiling));

        let before_window = PhysicalMappingWindowObserver { memory: &memory }
            .observe_before(page + 1)
            .unwrap();
        assert_eq!(before_window.requested_mapping_bytes(), page + 1);
        assert_eq!(before_window.runtime_page_size_bytes(), page);
        assert_eq!(before_window.mapped_bytes(), page * 2);

        fs::write(path.join("memory.current"), format!("{ceiling}\n")).unwrap();
        let after_window = before_window.observe_after().unwrap();
        assert_eq!(after_window.ceiling_bytes(), ceiling);
        assert_eq!(after_window.before_bytes(), before);
        assert_eq!(after_window.after_bytes(), ceiling);
        assert_eq!(after_window.requested_mapping_bytes(), page + 1);
        assert_eq!(after_window.runtime_page_size_bytes(), page);
        assert_eq!(after_window.mapped_bytes(), page * 2);

        fs::write(path.join("memory.current"), format!("{before}\n")).unwrap();
        let distinct_length = PhysicalMappingWindowObserver { memory: &memory }
            .observe_before(page + 2)
            .unwrap();
        assert_eq!(distinct_length.requested_mapping_bytes(), page + 2);
        assert_eq!(distinct_length.mapped_bytes(), page * 2);
    }

    #[test]
    fn physical_mapping_window_rejects_mismatched_limits_in_both_phases() {
        let (path, _cleanup) = fresh_test_directory("changed-window-limits");
        let page = native_page_size_bytes().unwrap();
        let ceiling = page.checked_mul(4).unwrap();
        let changed = ceiling.checked_sub(1).unwrap();
        fs::write(path.join("memory.current"), format!("{page}\n")).unwrap();
        fs::write(path.join("memory.max"), format!("{changed}\n")).unwrap();
        let memory = RetainedCgroupMemoryDirectory::v2(open_test_directory(&path), Some(ceiling));
        assert!(PhysicalMappingWindowObserver { memory: &memory }
            .observe_before(1)
            .is_err());

        fs::write(path.join("memory.max"), format!("{ceiling}\n")).unwrap();
        let before_window = PhysicalMappingWindowObserver { memory: &memory }
            .observe_before(1)
            .unwrap();
        fs::write(path.join("memory.max"), format!("{changed}\n")).unwrap();
        assert!(before_window.observe_after().is_err());
    }

    #[test]
    fn physical_mapping_window_fails_without_fallback() {
        let (path, _cleanup) = fresh_test_directory("current-allocation-rejection");
        let page = native_page_size_bytes().unwrap();
        let ceiling = page.checked_mul(4).unwrap();
        let before = page.checked_mul(2).unwrap();
        fs::write(path.join("memory.current"), format!("{before}\n")).unwrap();
        fs::write(path.join("memory.max"), format!("{ceiling}\n")).unwrap();

        let finite = RetainedCgroupMemoryDirectory::v2(open_test_directory(&path), Some(ceiling));
        assert!(PhysicalMappingWindowObserver { memory: &finite }
            .observe_before(page * 2 + 1)
            .is_err());
        assert!(PhysicalMappingWindowObserver { memory: &finite }
            .observe_before(0)
            .is_err());

        fs::write(path.join("memory.max"), b"max\n").unwrap();
        let unbounded = RetainedCgroupMemoryDirectory::v2(open_test_directory(&path), None);
        assert!(PhysicalMappingWindowObserver { memory: &unbounded }
            .observe_before(1)
            .is_err());
    }

    #[test]
    fn sampled_limit_sequence_rejects_either_mismatched_limit_read() {
        let retained = CgroupMemoryInterface::V2 {
            memory_max_bytes: Some(16_384),
        };
        let changed = CgroupMemoryInterface::V2 {
            memory_max_bytes: Some(16_383),
        };
        let observed =
            sampled_limits_match_retained_facts(retained, retained, 4_096, retained).unwrap();
        assert_eq!(observed.ceiling_bytes, 16_384);
        assert_eq!(observed.current_bytes, 4_096);
        assert!(sampled_limits_match_retained_facts(retained, changed, 4_096, retained).is_err());
        assert!(sampled_limits_match_retained_facts(retained, retained, 4_096, changed).is_err());
        assert!(sampled_limits_match_retained_facts(retained, retained, 16_385, retained).is_err());
    }

    #[test]
    fn v1_window_streams_hierarchical_limit_without_a_line_cap() {
        let (path, _cleanup) = fresh_test_directory("v1-window-limits");
        let page = native_page_size_bytes().unwrap();
        let leaf = page.checked_mul(4).unwrap();
        let hierarchical = page.checked_mul(3).unwrap();
        fs::write(path.join("memory.usage_in_bytes"), format!("{page}\n")).unwrap();
        fs::write(path.join("memory.limit_in_bytes"), format!("{leaf}\n")).unwrap();
        let mut stat = vec![b'x'; 128 * 1024];
        stat.extend_from_slice(b" 1\n");
        stat.extend_from_slice(format!("hierarchical_memory_limit {hierarchical}\n").as_bytes());
        fs::write(path.join("memory.stat"), &stat).unwrap();

        let memory =
            RetainedCgroupMemoryDirectory::v1(open_test_directory(&path), leaf, Some(hierarchical));
        assert_eq!(
            stream_v1_hierarchical_memory_limit_at(&memory.directory).unwrap(),
            Some(hierarchical)
        );
        let before_window = PhysicalMappingWindowObserver { memory: &memory }
            .observe_before(page)
            .unwrap();
        assert_eq!(before_window.requested_mapping_bytes(), page);

        let changed = hierarchical.checked_sub(1).unwrap();
        fs::write(
            path.join("memory.stat"),
            format!("hierarchical_memory_limit {changed}\n"),
        )
        .unwrap();
        assert!(before_window.observe_after().is_err());
    }

    #[test]
    fn v1_streaming_hierarchical_limit_rejects_duplicates_and_bad_values() {
        let (path, _cleanup) = fresh_test_directory("v1-stream-invalid");
        let stat_path = path.join("memory.stat");
        let directory = open_test_directory(&path);
        fs::write(
            &stat_path,
            b"hierarchical_memory_limit 10\nhierarchical_memory_limit 10\n",
        )
        .unwrap();
        assert!(stream_v1_hierarchical_memory_limit_at(&directory).is_err());
        for invalid in [
            b"hierarchical_memory_limit 0\n".as_slice(),
            b"hierarchical_memory_limit 01\n".as_slice(),
            b"hierarchical_memory_limit 10".as_slice(),
            b"hierarchical_memory_limit 18446744073709551616\n".as_slice(),
        ] {
            fs::write(&stat_path, invalid).unwrap();
            assert!(stream_v1_hierarchical_memory_limit_at(&directory).is_err());
        }
        fs::write(&stat_path, b"cache 1\n").unwrap();
        assert_eq!(
            stream_v1_hierarchical_memory_limit_at(&directory).unwrap(),
            None
        );
    }

    #[test]
    fn v1_streaming_scanner_crosses_exact_4096_prefix_and_value_boundaries() {
        fn scan_in_4096_reads(bytes: &[u8]) -> Option<u64> {
            assert!(bytes.len() > 4_096);
            let mut scanner = V1HierarchicalMemoryLimitScanner::new();
            scanner.consume(&bytes[..4_096]).unwrap();
            scanner.consume(&bytes[4_096..]).unwrap();
            scanner.finish().unwrap()
        }

        let prefix_start = 4_090;
        let mut prefix_crossing = vec![b'x'; prefix_start - 1];
        prefix_crossing.push(b'\n');
        assert_eq!(prefix_crossing.len(), prefix_start);
        prefix_crossing.extend_from_slice(b"hierarchical_memory_limit 12345\n");
        assert_eq!(scan_in_4096_reads(&prefix_crossing), Some(12_345));

        let target_prefix = b"hierarchical_memory_limit ";
        let value_start = 4_094;
        let line_start = value_start - target_prefix.len();
        let mut value_crossing = vec![b'y'; line_start - 1];
        value_crossing.push(b'\n');
        value_crossing.extend_from_slice(target_prefix);
        assert_eq!(value_crossing.len(), value_start);
        value_crossing.extend_from_slice(b"678901\n");
        assert_eq!(scan_in_4096_reads(&value_crossing), Some(678_901));
    }

    #[test]
    fn pure_v1_unlimited_sentinel_derivation_covers_32_and_64_bit_formulas() {
        let page_size = 4_096;
        assert_eq!(
            derive_v1_unlimited_memory_sentinel_bytes(4, page_size).unwrap(),
            (i32::MAX as u64).checked_mul(page_size).unwrap()
        );
        assert_eq!(
            derive_v1_unlimited_memory_sentinel_bytes(8, page_size).unwrap(),
            ((i64::MAX as u64) / page_size) * page_size
        );
        assert!(derive_v1_unlimited_memory_sentinel_bytes(8, 0).is_err());
        assert!(derive_v1_unlimited_memory_sentinel_bytes(16, page_size).is_err());
    }

    #[test]
    fn production_v1_sentinel_requires_native_64_bit_userspace() {
        if std::mem::size_of::<libc::c_long>() == 8 && std::mem::size_of::<usize>() == 8 {
            let page_size = u64::try_from(unsafe { libc::sysconf(libc::_SC_PAGESIZE) }).unwrap();
            assert_eq!(
                v1_unlimited_memory_sentinel_bytes().unwrap(),
                derive_v1_unlimited_memory_sentinel_bytes(8, page_size).unwrap()
            );
        } else {
            assert!(v1_unlimited_memory_sentinel_bytes().is_err());
        }
    }

    #[test]
    fn retained_directory_identity_survives_path_replacement() {
        let (path, mut cleanup) = fresh_test_directory("identity");
        let moved = path.with_extension("retained");
        cleanup.0.push(moved.clone());
        fs::write(path.join("memory.current"), b"7\n").unwrap();
        let retained = RetainedCgroupMemoryDirectory::v2(open_test_directory(&path), Some(1));

        fs::rename(&path, &moved).unwrap();
        fs::create_dir(&path).unwrap();
        fs::write(path.join("memory.current"), b"99\n").unwrap();
        assert_eq!(retained.read_memory_current().unwrap().current_bytes(), 7);

        fs::write(moved.join("memory.current"), b"8\n").unwrap();
        assert_eq!(retained.read_memory_current().unwrap().current_bytes(), 8);
    }

    #[test]
    fn fresh_memory_read_rejects_symlinks_and_non_u64_framing() {
        let (path, _cleanup) = fresh_test_directory("invalid-current");
        let current = path.join("memory.current");
        let retained = RetainedCgroupMemoryDirectory::v2(open_test_directory(&path), Some(1));

        fs::write(&current, b"18446744073709551615\n").unwrap();
        assert_eq!(
            retained.read_memory_current().unwrap().current_bytes(),
            u64::MAX
        );

        for invalid in [
            b"1".as_slice(),
            b"00\n".as_slice(),
            b"01\n".as_slice(),
            b"1\r\n".as_slice(),
            b"1\n2\n".as_slice(),
            b"18446744073709551616\n".as_slice(),
            b"not-a-number\n".as_slice(),
        ] {
            fs::write(&current, invalid).unwrap();
            assert!(retained.read_memory_current().is_err());
        }

        fs::remove_file(&current).unwrap();
        fs::write(path.join("other"), b"5\n").unwrap();
        std::os::unix::fs::symlink("other", &current).unwrap();
        assert!(retained.read_memory_current().is_err());
    }

    #[test]
    fn json_and_body_bounds_fail_before_unbounded_growth() {
        let nested = format!(
            "{}0{}",
            "[".repeat(MAX_JSON_DEPTH + 2),
            "]".repeat(MAX_JSON_DEPTH + 2)
        );
        assert_eq!(
            reject_duplicate_json_keys(nested.as_bytes()).unwrap_err(),
            PlatformObserverError::JsonTooDeep
        );
        let broad = format!(
            "[{}]",
            vec!["0"; MAX_JSON_MEMBERS_PER_CONTAINER + 1].join(",")
        );
        assert_eq!(
            reject_duplicate_json_keys(broad.as_bytes()).unwrap_err(),
            PlatformObserverError::JsonTooBroad
        );
        let long_string = format!("\"{}\"", "a".repeat(MAX_JSON_STRING_BYTES + 1));
        assert_eq!(
            reject_duplicate_json_keys(long_string.as_bytes()).unwrap_err(),
            PlatformObserverError::JsonStringTooLong
        );
        let full_group = format!("[{}]", vec!["0"; MAX_JSON_MEMBERS_PER_CONTAINER].join(","));
        let many_values = format!("[{}]", vec![full_group; 17].join(","));
        assert_eq!(
            reject_duplicate_json_keys(many_values.as_bytes()).unwrap_err(),
            PlatformObserverError::JsonTooManyValues
        );
        let oversized = vec![b'a'; MAX_BODY_BYTES + 1];
        assert_eq!(
            decode_content_length((MAX_BODY_BYTES + 1).to_string().as_bytes(), &oversized)
                .unwrap_err(),
            PlatformObserverError::BodyTooLarge
        );
    }
}
