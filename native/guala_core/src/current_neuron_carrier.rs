//! Isolated current-only carrier for the reached-neuron D2 body.
//!
//! `GLNCAR01` preserves one already-authenticated `GLJNFT03` body byte for
//! byte. It does not decode that private predecessor schema and therefore is
//! not a legacy migration boundary. `GLMFAB05` wraps exactly one `GLNCAR01`
//! carrier. Neither codec is mounted in `lib.rs`.
//!
//! The two successor-status bytes are discriminants only. They have no state
//! payload and cannot be interpreted as zero-valued Krimelack, membrane,
//! channel, synapse, contact, metabolic, mosaic, or cognitive state.

use sha2::{Digest, Sha256};
use std::fmt;

const INNER_MAGIC: &[u8; 8] = b"GLNCAR01";
const INNER_VERSION: u16 = 1;
const OUTER_MAGIC: &[u8; 8] = b"GLMFAB05";
const OUTER_VERSION: u16 = 5;
const D2_MAGIC: &[u8; 8] = b"GLJNFT03";
const D2_VERSION: u16 = 3;

const OPTIONAL_NONE_BYTES: usize = 1;
const OPTIONAL_SOME_BYTES: usize = 1 + 32;
const INNER_FIXED_WITHOUT_OPTIONAL_OR_BODY: usize = 8 + 2 + 8 + 8 + 32 + 1 + 1 + 4 + 32;
const OUTER_FIXED_WITHOUT_INNER: usize = 8 + 2 + 8 + 4 + 32;

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
#[repr(u8)]
pub(crate) enum KrimelackSuccessorStatus {
    MissingRatifiedLocalD1ToKLaw = 0,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
#[repr(u8)]
pub(crate) enum BiophysicalSuccessorStatus {
    MissingProductionAnatomyAndIncorporationLaw = 0,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) struct CarrierLimits {
    pub(crate) max_d2_body_bytes: usize,
    pub(crate) max_inner_bytes: usize,
    pub(crate) max_outer_bytes: usize,
}

impl CarrierLimits {
    pub(crate) fn new(
        max_d2_body_bytes: usize,
        max_inner_bytes: usize,
        max_outer_bytes: usize,
    ) -> Result<Self, CarrierError> {
        if max_d2_body_bytes == 0 || max_inner_bytes == 0 || max_outer_bytes == 0 {
            return Err(CarrierError::InvalidLimit);
        }
        Ok(Self {
            max_d2_body_bytes,
            max_inner_bytes,
            max_outer_bytes,
        })
    }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) struct CarrierResourceRequirement {
    pub(crate) retained_d2_body_bytes: usize,
    pub(crate) inner_encoded_bytes: usize,
    pub(crate) outer_encoded_bytes: usize,
}

impl CarrierResourceRequirement {
    pub(crate) fn atomic_logical_live_bytes_with(
        self,
        successor: Self,
    ) -> Result<usize, CarrierError> {
        self.outer_encoded_bytes
            .checked_add(successor.outer_encoded_bytes)
            .ok_or(CarrierError::LengthOverflow)
    }
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) struct NeuronCarrier {
    generation: u64,
    next_lineage_ordinal: u64,
    source_authority_receipt: [u8; 32],
    last_d1_transition_receipt: Option<[u8; 32]>,
    krimelack_successor_status: KrimelackSuccessorStatus,
    biophysical_successor_status: BiophysicalSuccessorStatus,
    d2_body_receipt: [u8; 32],
    d2_body: Vec<u8>,
}

impl NeuronCarrier {
    /// Retain a D2 body that was authenticated by the existing private D2
    /// decoder. Checking its receipt and schema header here proves byte
    /// continuity only; it is deliberately not described as migration.
    pub(crate) fn retain_authenticated_d2_body(
        generation: u64,
        next_lineage_ordinal: u64,
        source_authority_receipt: [u8; 32],
        last_d1_transition_receipt: Option<[u8; 32]>,
        d2_body: Vec<u8>,
        authenticated_d2_body_receipt: [u8; 32],
        limits: CarrierLimits,
    ) -> Result<Self, CarrierError> {
        validate_d2_body(&d2_body, limits.max_d2_body_bytes)?;
        if sha256(&d2_body) != authenticated_d2_body_receipt {
            return Err(CarrierError::D2BodyReceiptMismatch);
        }
        let value = Self {
            generation,
            next_lineage_ordinal,
            source_authority_receipt,
            last_d1_transition_receipt,
            krimelack_successor_status: KrimelackSuccessorStatus::MissingRatifiedLocalD1ToKLaw,
            biophysical_successor_status:
                BiophysicalSuccessorStatus::MissingProductionAnatomyAndIncorporationLaw,
            d2_body_receipt: authenticated_d2_body_receipt,
            d2_body,
        };
        value.encode_current(limits.max_inner_bytes)?;
        Ok(value)
    }

    pub(crate) fn decode_current(
        encoded: &[u8],
        limits: CarrierLimits,
    ) -> Result<Self, CarrierError> {
        if encoded.len() > limits.max_inner_bytes {
            return Err(CarrierError::InnerBudgetExceeded {
                required: encoded.len(),
                available: limits.max_inner_bytes,
            });
        }
        let mut parser = Parser::new(encoded);
        if parser.take(8)? != INNER_MAGIC {
            return Err(CarrierError::BadInnerMagic);
        }
        let version = parser.u16()?;
        if version != INNER_VERSION {
            return Err(CarrierError::UnsupportedInnerVersion(version));
        }
        let generation = parser.u64()?;
        let next_lineage_ordinal = parser.u64()?;
        let source_authority_receipt = parser.digest()?;
        let last_d1_transition_receipt = parser.optional_digest()?;
        let krimelack_successor_status = match parser.u8()? {
            0 => KrimelackSuccessorStatus::MissingRatifiedLocalD1ToKLaw,
            value => return Err(CarrierError::InvalidKrimelackStatus(value)),
        };
        let biophysical_successor_status = match parser.u8()? {
            0 => BiophysicalSuccessorStatus::MissingProductionAnatomyAndIncorporationLaw,
            value => return Err(CarrierError::InvalidBiophysicalStatus(value)),
        };
        let d2_body_len = parser.u32()? as usize;
        if d2_body_len > limits.max_d2_body_bytes {
            return Err(CarrierError::D2BodyBudgetExceeded {
                required: d2_body_len,
                available: limits.max_d2_body_bytes,
            });
        }
        let d2_body_receipt = parser.digest()?;
        let d2_body = parser.take(d2_body_len)?.to_vec();
        if !parser.finished() {
            return Err(CarrierError::TrailingBytes);
        }
        validate_d2_body(&d2_body, limits.max_d2_body_bytes)?;
        if sha256(&d2_body) != d2_body_receipt {
            return Err(CarrierError::D2BodyReceiptMismatch);
        }
        let value = Self {
            generation,
            next_lineage_ordinal,
            source_authority_receipt,
            last_d1_transition_receipt,
            krimelack_successor_status,
            biophysical_successor_status,
            d2_body_receipt,
            d2_body,
        };
        let canonical = value.encode_current(limits.max_inner_bytes)?;
        if canonical != encoded {
            return Err(CarrierError::NoncanonicalEncoding);
        }
        Ok(value)
    }

    pub(crate) fn encode_current(&self, max_inner_bytes: usize) -> Result<Vec<u8>, CarrierError> {
        let required = self.inner_encoded_len()?;
        if required > max_inner_bytes {
            return Err(CarrierError::InnerBudgetExceeded {
                required,
                available: max_inner_bytes,
            });
        }
        let mut output = Vec::new();
        output
            .try_reserve_exact(required)
            .map_err(|_| CarrierError::AllocationFailed)?;
        output.extend_from_slice(INNER_MAGIC);
        output.extend_from_slice(&INNER_VERSION.to_le_bytes());
        output.extend_from_slice(&self.generation.to_le_bytes());
        output.extend_from_slice(&self.next_lineage_ordinal.to_le_bytes());
        output.extend_from_slice(&self.source_authority_receipt);
        push_optional_digest(&mut output, self.last_d1_transition_receipt);
        output.push(self.krimelack_successor_status as u8);
        output.push(self.biophysical_successor_status as u8);
        output.extend_from_slice(
            &u32::try_from(self.d2_body.len())
                .map_err(|_| CarrierError::LengthOverflow)?
                .to_le_bytes(),
        );
        output.extend_from_slice(&self.d2_body_receipt);
        output.extend_from_slice(&self.d2_body);
        debug_assert_eq!(output.len(), required);
        Ok(output)
    }

    pub(crate) fn inner_encoded_len(&self) -> Result<usize, CarrierError> {
        inner_encoded_len(
            self.d2_body.len(),
            self.last_d1_transition_receipt.is_some(),
        )
    }

    pub(crate) fn generation(&self) -> u64 {
        self.generation
    }

    pub(crate) fn d2_body(&self) -> &[u8] {
        &self.d2_body
    }

    pub(crate) fn d2_body_receipt(&self) -> [u8; 32] {
        self.d2_body_receipt
    }

    pub(crate) fn krimelack_successor_status(&self) -> KrimelackSuccessorStatus {
        self.krimelack_successor_status
    }

    pub(crate) fn biophysical_successor_status(&self) -> BiophysicalSuccessorStatus {
        self.biophysical_successor_status
    }

    pub(crate) fn refuse_local_d1_to_k_successor(&self) -> Result<(), CarrierError> {
        Err(CarrierError::MissingRatifiedLocalD1ToKLaw)
    }

    fn successor_with_authenticated_d2_body(
        &self,
        next_lineage_ordinal: u64,
        source_authority_receipt: [u8; 32],
        last_d1_transition_receipt: Option<[u8; 32]>,
        successor_d2_body: Vec<u8>,
        authenticated_successor_receipt: [u8; 32],
        limits: CarrierLimits,
    ) -> Result<Self, CarrierError> {
        let generation = self
            .generation
            .checked_add(1)
            .ok_or(CarrierError::GenerationOverflow)?;
        Self::retain_authenticated_d2_body(
            generation,
            next_lineage_ordinal,
            source_authority_receipt,
            last_d1_transition_receipt,
            successor_d2_body,
            authenticated_successor_receipt,
            limits,
        )
    }
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) struct MaterializedCarrier {
    generation: u64,
    neuron_carrier: NeuronCarrier,
}

impl MaterializedCarrier {
    pub(crate) fn new(
        generation: u64,
        neuron_carrier: NeuronCarrier,
        limits: CarrierLimits,
    ) -> Result<Self, CarrierError> {
        let value = Self {
            generation,
            neuron_carrier,
        };
        value.encode_current(limits.max_outer_bytes, limits.max_inner_bytes)?;
        Ok(value)
    }

    pub(crate) fn decode_current(
        encoded: &[u8],
        limits: CarrierLimits,
    ) -> Result<Self, CarrierError> {
        if encoded.len() > limits.max_outer_bytes {
            return Err(CarrierError::OuterBudgetExceeded {
                required: encoded.len(),
                available: limits.max_outer_bytes,
            });
        }
        let mut parser = Parser::new(encoded);
        if parser.take(8)? != OUTER_MAGIC {
            return Err(CarrierError::BadOuterMagic);
        }
        let version = parser.u16()?;
        if version != OUTER_VERSION {
            return Err(CarrierError::UnsupportedOuterVersion(version));
        }
        let generation = parser.u64()?;
        let inner_len = parser.u32()? as usize;
        if inner_len > limits.max_inner_bytes {
            return Err(CarrierError::InnerBudgetExceeded {
                required: inner_len,
                available: limits.max_inner_bytes,
            });
        }
        let inner_receipt = parser.digest()?;
        let inner_bytes = parser.take(inner_len)?;
        if !parser.finished() {
            return Err(CarrierError::TrailingBytes);
        }
        if sha256(inner_bytes) != inner_receipt {
            return Err(CarrierError::InnerReceiptMismatch);
        }
        let neuron_carrier = NeuronCarrier::decode_current(inner_bytes, limits)?;
        let value = Self {
            generation,
            neuron_carrier,
        };
        let canonical = value.encode_current(limits.max_outer_bytes, limits.max_inner_bytes)?;
        if canonical != encoded {
            return Err(CarrierError::NoncanonicalEncoding);
        }
        Ok(value)
    }

    pub(crate) fn encode_current(
        &self,
        max_outer_bytes: usize,
        max_inner_bytes: usize,
    ) -> Result<Vec<u8>, CarrierError> {
        let inner = self.neuron_carrier.encode_current(max_inner_bytes)?;
        let required = outer_encoded_len(inner.len())?;
        if required > max_outer_bytes {
            return Err(CarrierError::OuterBudgetExceeded {
                required,
                available: max_outer_bytes,
            });
        }
        let mut output = Vec::new();
        output
            .try_reserve_exact(required)
            .map_err(|_| CarrierError::AllocationFailed)?;
        output.extend_from_slice(OUTER_MAGIC);
        output.extend_from_slice(&OUTER_VERSION.to_le_bytes());
        output.extend_from_slice(&self.generation.to_le_bytes());
        output.extend_from_slice(
            &u32::try_from(inner.len())
                .map_err(|_| CarrierError::LengthOverflow)?
                .to_le_bytes(),
        );
        output.extend_from_slice(&sha256(&inner));
        output.extend_from_slice(&inner);
        debug_assert_eq!(output.len(), required);
        Ok(output)
    }

    /// Construct and fully round-trip a detached successor before returning it.
    /// The predecessor is borrowed immutably, so every failure leaves it
    /// byte-identical. This is carrier atomicity, not D2 neuronal settlement.
    pub(crate) fn replace_d2_atomically(
        &self,
        next_lineage_ordinal: u64,
        source_authority_receipt: [u8; 32],
        last_d1_transition_receipt: Option<[u8; 32]>,
        successor_d2_body: Vec<u8>,
        authenticated_successor_receipt: [u8; 32],
        limits: CarrierLimits,
    ) -> Result<Self, CarrierError> {
        let neuron_carrier = self.neuron_carrier.successor_with_authenticated_d2_body(
            next_lineage_ordinal,
            source_authority_receipt,
            last_d1_transition_receipt,
            successor_d2_body,
            authenticated_successor_receipt,
            limits,
        )?;
        let generation = self
            .generation
            .checked_add(1)
            .ok_or(CarrierError::GenerationOverflow)?;
        let candidate = Self {
            generation,
            neuron_carrier,
        };
        let bytes = candidate.encode_current(limits.max_outer_bytes, limits.max_inner_bytes)?;
        Self::decode_current(&bytes, limits)
    }

    pub(crate) fn resource_requirement(&self) -> Result<CarrierResourceRequirement, CarrierError> {
        let inner_encoded_bytes = self.neuron_carrier.inner_encoded_len()?;
        Ok(CarrierResourceRequirement {
            retained_d2_body_bytes: self.neuron_carrier.d2_body.len(),
            inner_encoded_bytes,
            outer_encoded_bytes: outer_encoded_len(inner_encoded_bytes)?,
        })
    }

    pub(crate) fn generation(&self) -> u64 {
        self.generation
    }

    pub(crate) fn neuron_carrier(&self) -> &NeuronCarrier {
        &self.neuron_carrier
    }
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) enum CarrierError {
    InvalidLimit,
    LengthOverflow,
    AllocationFailed,
    GenerationOverflow,
    EndedEarly,
    TrailingBytes,
    BadInnerMagic,
    UnsupportedInnerVersion(u16),
    BadOuterMagic,
    UnsupportedOuterVersion(u16),
    BadD2Magic,
    UnsupportedD2Version(u16),
    InvalidOptionalDigest(u8),
    InvalidKrimelackStatus(u8),
    InvalidBiophysicalStatus(u8),
    D2BodyReceiptMismatch,
    InnerReceiptMismatch,
    NoncanonicalEncoding,
    D2BodyBudgetExceeded { required: usize, available: usize },
    InnerBudgetExceeded { required: usize, available: usize },
    OuterBudgetExceeded { required: usize, available: usize },
    MissingRatifiedLocalD1ToKLaw,
}

impl fmt::Display for CarrierError {
    fn fmt(&self, output: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::InvalidLimit => write!(output, "carrier limits must be positive"),
            Self::LengthOverflow => write!(output, "carrier length overflow"),
            Self::AllocationFailed => write!(output, "carrier allocation failed"),
            Self::GenerationOverflow => write!(output, "carrier generation overflow"),
            Self::EndedEarly => write!(output, "carrier ended early"),
            Self::TrailingBytes => write!(output, "carrier has trailing bytes"),
            Self::BadInnerMagic => write!(output, "current inner carrier is not GLNCAR01"),
            Self::UnsupportedInnerVersion(version) => {
                write!(output, "unsupported inner carrier version {version}")
            }
            Self::BadOuterMagic => write!(output, "current outer carrier is not GLMFAB05"),
            Self::UnsupportedOuterVersion(version) => {
                write!(output, "unsupported outer carrier version {version}")
            }
            Self::BadD2Magic => write!(output, "retained D2 body is not GLJNFT03"),
            Self::UnsupportedD2Version(version) => {
                write!(output, "unsupported retained D2 version {version}")
            }
            Self::InvalidOptionalDigest(value) => {
                write!(output, "optional digest discriminant changed to {value}")
            }
            Self::InvalidKrimelackStatus(value) => {
                write!(output, "Krimelack status discriminant changed to {value}")
            }
            Self::InvalidBiophysicalStatus(value) => {
                write!(output, "biophysical status discriminant changed to {value}")
            }
            Self::D2BodyReceiptMismatch => write!(output, "retained D2 body receipt changed"),
            Self::InnerReceiptMismatch => write!(output, "inner carrier receipt changed"),
            Self::NoncanonicalEncoding => write!(output, "carrier encoding is not canonical"),
            Self::D2BodyBudgetExceeded {
                required,
                available,
            } => write!(
                output,
                "D2 body requires {required} bytes, admitted {available}"
            ),
            Self::InnerBudgetExceeded {
                required,
                available,
            } => write!(
                output,
                "inner carrier requires {required} bytes, admitted {available}"
            ),
            Self::OuterBudgetExceeded {
                required,
                available,
            } => write!(
                output,
                "outer carrier requires {required} bytes, admitted {available}"
            ),
            Self::MissingRatifiedLocalD1ToKLaw => {
                write!(output, "local D1-to-K successor law is not ratified")
            }
        }
    }
}

impl std::error::Error for CarrierError {}

fn validate_d2_body(body: &[u8], max_d2_body_bytes: usize) -> Result<(), CarrierError> {
    if body.len() > max_d2_body_bytes {
        return Err(CarrierError::D2BodyBudgetExceeded {
            required: body.len(),
            available: max_d2_body_bytes,
        });
    }
    if body.len() < 10 {
        return Err(CarrierError::EndedEarly);
    }
    if &body[..8] != D2_MAGIC {
        return Err(CarrierError::BadD2Magic);
    }
    let version = u16::from_le_bytes(body[8..10].try_into().expect("fixed D2 version"));
    if version != D2_VERSION {
        return Err(CarrierError::UnsupportedD2Version(version));
    }
    Ok(())
}

fn inner_encoded_len(d2_body_len: usize, has_last_transition: bool) -> Result<usize, CarrierError> {
    u32::try_from(d2_body_len).map_err(|_| CarrierError::LengthOverflow)?;
    INNER_FIXED_WITHOUT_OPTIONAL_OR_BODY
        .checked_add(if has_last_transition {
            OPTIONAL_SOME_BYTES
        } else {
            OPTIONAL_NONE_BYTES
        })
        .and_then(|bytes| bytes.checked_add(d2_body_len))
        .ok_or(CarrierError::LengthOverflow)
}

fn outer_encoded_len(inner_len: usize) -> Result<usize, CarrierError> {
    u32::try_from(inner_len).map_err(|_| CarrierError::LengthOverflow)?;
    OUTER_FIXED_WITHOUT_INNER
        .checked_add(inner_len)
        .ok_or(CarrierError::LengthOverflow)
}

fn push_optional_digest(output: &mut Vec<u8>, value: Option<[u8; 32]>) {
    match value {
        Some(value) => {
            output.push(1);
            output.extend_from_slice(&value);
        }
        None => output.push(0),
    }
}

fn sha256(bytes: &[u8]) -> [u8; 32] {
    let digest = Sha256::digest(bytes);
    let mut output = [0_u8; 32];
    output.copy_from_slice(&digest);
    output
}

struct Parser<'a> {
    bytes: &'a [u8],
    offset: usize,
}

impl<'a> Parser<'a> {
    fn new(bytes: &'a [u8]) -> Self {
        Self { bytes, offset: 0 }
    }

    fn take(&mut self, count: usize) -> Result<&'a [u8], CarrierError> {
        let end = self
            .offset
            .checked_add(count)
            .ok_or(CarrierError::LengthOverflow)?;
        let value = self
            .bytes
            .get(self.offset..end)
            .ok_or(CarrierError::EndedEarly)?;
        self.offset = end;
        Ok(value)
    }

    fn u8(&mut self) -> Result<u8, CarrierError> {
        Ok(self.take(1)?[0])
    }

    fn u16(&mut self) -> Result<u16, CarrierError> {
        Ok(u16::from_le_bytes(
            self.take(2)?.try_into().expect("fixed carrier u16"),
        ))
    }

    fn u32(&mut self) -> Result<u32, CarrierError> {
        Ok(u32::from_le_bytes(
            self.take(4)?.try_into().expect("fixed carrier u32"),
        ))
    }

    fn u64(&mut self) -> Result<u64, CarrierError> {
        Ok(u64::from_le_bytes(
            self.take(8)?.try_into().expect("fixed carrier u64"),
        ))
    }

    fn digest(&mut self) -> Result<[u8; 32], CarrierError> {
        Ok(self.take(32)?.try_into().expect("fixed carrier digest"))
    }

    fn optional_digest(&mut self) -> Result<Option<[u8; 32]>, CarrierError> {
        match self.u8()? {
            0 => Ok(None),
            1 => Ok(Some(self.digest()?)),
            value => Err(CarrierError::InvalidOptionalDigest(value)),
        }
    }

    fn finished(&self) -> bool {
        self.offset == self.bytes.len()
    }
}
