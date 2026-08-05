//! Canonical native persistence boundary for one Guala organism.
//!
//! This module encodes structure only. Decoded bytes remain explicitly
//! unauthenticated until a later authority boundary verifies identity, prior
//! generation, frozen-L4 receipts, evidence, body/world state, and wake cause.

use sha2::{Digest, Sha256};
use std::collections::{BTreeMap, BTreeSet};
use std::fmt;
use std::mem::size_of;

const MAGIC: &[u8; 8] = b"GUALAORG";
const SCHEMA_VERSION: u16 = 2;
const NEURON_LAYOUT: &[u8; 16] = b"GUALA_NEURON_V2_";

#[derive(Clone, Debug, PartialEq, Eq)]
pub enum CodecError {
    UnexpectedEnd,
    BadMagic,
    UnsupportedVersion(u16),
    WrongNeuronLayout,
    LengthOverflow,
    InputBudgetExceeded,
    AllocationBudgetExceeded,
    EncodedBudgetExceeded,
    TrailingBytes,
    Invalid(&'static str),
}

impl fmt::Display for CodecError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::UnexpectedEnd => write!(f, "organism state ended unexpectedly"),
            Self::BadMagic => write!(f, "organism state has non-native schema magic"),
            Self::UnsupportedVersion(version) => write!(f, "unsupported schema version {version}"),
            Self::WrongNeuronLayout => write!(f, "organism state contains another neuron kind"),
            Self::LengthOverflow => write!(f, "organism state length overflow"),
            Self::InputBudgetExceeded => write!(f, "encoded state exceeds admitted input budget"),
            Self::AllocationBudgetExceeded => write!(f, "decoded state exceeds allocation budget"),
            Self::EncodedBudgetExceeded => write!(f, "encoded state exceeds output budget"),
            Self::TrailingBytes => write!(f, "organism state contains trailing bytes"),
            Self::Invalid(reason) => write!(f, "invalid organism state: {reason}"),
        }
    }
}

impl std::error::Error for CodecError {}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct DecodeBudget {
    pub max_input_bytes: u64,
    pub max_heap_bytes: u64,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq, PartialOrd, Ord)]
pub struct ArenaRange {
    pub start: u64,
    pub len: u64,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct CausalReceipt {
    pub ordinal: u64,
    pub receipt: [u8; 32],
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct PackedTrits {
    pub trit_len: u64,
    pub bytes: Vec<u8>,
}

impl PackedTrits {
    pub fn from_trits(trits: &[i8]) -> Result<Self, CodecError> {
        let trit_len = u64::try_from(trits.len()).map_err(|_| CodecError::LengthOverflow)?;
        let byte_len = trits
            .len()
            .checked_add(3)
            .ok_or(CodecError::LengthOverflow)?
            / 4;
        let mut bytes = vec![0_u8; byte_len];
        for (index, trit) in trits.iter().copied().enumerate() {
            let code = match trit {
                -1 => 0_u8,
                0 => 1_u8,
                1 => 2_u8,
                _ => return Err(CodecError::Invalid("balanced trit must be -1, 0, or 1")),
            };
            bytes[index / 4] |= code << ((index % 4) * 2);
        }
        Ok(Self { trit_len, bytes })
    }

    pub fn trit(&self, index: u64) -> Option<i8> {
        if index >= self.trit_len {
            return None;
        }
        let index = usize::try_from(index).ok()?;
        let byte = self.bytes.get(index / 4)?;
        match (byte >> ((index % 4) * 2)) & 0b11 {
            0 => Some(-1),
            1 => Some(0),
            2 => Some(1),
            _ => None,
        }
    }

    pub fn validate(&self) -> Result<(), CodecError> {
        let expected = packed_byte_len(self.trit_len)?;
        if self.bytes.len() != expected {
            return Err(CodecError::Invalid(
                "packed trit byte length is not canonical",
            ));
        }
        for index in 0..self.trit_len {
            if self.trit(index).is_none() {
                return Err(CodecError::Invalid("packed trit contains reserved code"));
            }
        }
        if !self.trit_len.is_multiple_of(4) {
            let used = (self.trit_len % 4) as u8;
            let mask = !((1_u8 << (used * 2)) - 1);
            if self.bytes.last().copied().unwrap_or_default() & mask != 0 {
                return Err(CodecError::Invalid("packed trit padding is nonzero"));
            }
        }
        Ok(())
    }
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct LocalDsfState {
    /// Exact binary64 slots in frozen order D, M, R_rev, U_star, C, P, B.
    /// Structural decoding does not authenticate the referenced bank evidence.
    pub coordinate_bits: [u64; 7],
    pub authority_index: u64,
}

/// Compact reference into immutable native field-bank custody. Restore must
/// resolve the bank and every named record before this delivery is authoritative.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct DsfDeliveryAuthority {
    pub field_bank_receipt: [u8; 32],
    pub kernel_config_receipt: [u8; 32],
    pub port_index: u64,
    pub tuple_index: u64,
    pub trace_receipt: [u8; 32],
    pub tuple_receipt: [u8; 32],
    pub basin_receipt: [u8; 32],
}

/// The only neuron record. All variable data lives in organism-owned arenas.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct NeuronState {
    pub lineage: [u8; 16],
    pub growth_dna: [u8; 32],
    pub specialization_receipt: [u8; 32],
    pub field_position: u64,
    pub trit_range: ArenaRange,
    pub oscillator_phase_bits: u64,
    pub oscillator_winding: i64,
    pub local_dsf: LocalDsfState,
    pub energetic_bits: u64,
    pub refractory_until_generation: u64,
    pub fractal: [u8; 32],
    pub evidence_receipt: [u8; 32],
    pub recent_causal_range: ArenaRange,
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct CouplingState {
    pub source_neuron: u64,
    pub target_neuron: u64,
    pub numerator: i64,
    pub denominator: u64,
    pub causal_receipt: [u8; 32],
}

#[derive(Clone, Copy, Debug, PartialEq, Eq, PartialOrd, Ord)]
#[repr(u8)]
pub enum FormationKind {
    Mosaic = 1,
    MosaicOfMosaics = 2,
    Tapestry = 3,
    TapestryOfTapestries = 4,
    Weave = 5,
}

impl FormationKind {
    fn decode(value: u8) -> Result<Self, CodecError> {
        match value {
            1 => Ok(Self::Mosaic),
            2 => Ok(Self::MosaicOfMosaics),
            3 => Ok(Self::Tapestry),
            4 => Ok(Self::TapestryOfTapestries),
            5 => Ok(Self::Weave),
            _ => Err(CodecError::Invalid("unknown recursive formation kind")),
        }
    }
}

#[derive(Clone, Copy, Debug, PartialEq, Eq, PartialOrd, Ord)]
pub enum FormationMember {
    Neuron(u64),
    Formation(u64),
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct FormationState {
    pub id: u64,
    pub kind: FormationKind,
    pub member_range: ArenaRange,
    pub structural_impression: [u8; 32],
    pub evidence_receipt: [u8; 32],
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct StabilityEvidenceRanges {
    pub coherence: ArenaRange,
    pub formation_entropy: ArenaRange,
    pub breathing_variance: ArenaRange,
    pub uncertainty: ArenaRange,
    pub tapestry_drift: ArenaRange,
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub enum WakeState {
    Quiescent,
    AtBodyTick {
        body_clock_receipt: [u8; 32],
        tick: u64,
        cause_receipt: [u8; 32],
    },
    WorldRevision {
        revision: u64,
        cause_receipt: [u8; 32],
    },
    PhysicalCondition {
        condition_receipt: [u8; 32],
    },
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct ResourceObservation {
    pub cpu_nanoseconds: u64,
    pub resident_bytes: u64,
    pub durable_bytes: u64,
    pub recovery_reserve_bytes: u64,
    pub python_calls: u64,
    pub native_calls: u64,
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct OrganismState {
    pub identity: [u8; 16],
    pub generation: u64,
    pub prior_state_receipt: [u8; 32],
    pub authenticated_world_revision: [u8; 32],
    pub body_state_receipt: [u8; 32],
    pub admitted_evidence: Vec<CausalReceipt>,
    pub trit_arena: PackedTrits,
    pub causal_receipt_arena: Vec<CausalReceipt>,
    pub dsf_delivery_authorities: Vec<DsfDeliveryAuthority>,
    pub neurons: Vec<NeuronState>,
    pub couplings: Vec<CouplingState>,
    pub causal_frontier: Vec<u64>,
    pub formation_member_arena: Vec<FormationMember>,
    pub formations: Vec<FormationState>,
    pub stability_evidence_arena: Vec<[u8; 32]>,
    pub stability_evidence: StabilityEvidenceRanges,
    pub wake: WakeState,
    pub resources: ResourceObservation,
}

/// Structural decoding is never restoration authority.
pub struct UnverifiedOrganismState {
    state: OrganismState,
    source_receipt: [u8; 32],
}

impl UnverifiedOrganismState {
    pub fn source_receipt(&self) -> [u8; 32] {
        self.source_receipt
    }

    pub fn canonical_unverified_bytes(
        &self,
        max_encoded_bytes: u64,
    ) -> Result<Vec<u8>, CodecError> {
        self.state.encode_unverified(max_encoded_bytes)
    }
}

impl OrganismState {
    pub fn validate_structure(&self) -> Result<(), CodecError> {
        validate_causal_sequence(&self.admitted_evidence)?;
        self.trit_arena.validate()?;
        let neuron_count =
            u64::try_from(self.neurons.len()).map_err(|_| CodecError::LengthOverflow)?;

        let mut prior_delivery = None;
        for authority in &self.dsf_delivery_authorities {
            let key = (
                authority.field_bank_receipt,
                authority.port_index,
                authority.tuple_index,
            );
            if prior_delivery.is_some_and(|prior| prior >= key) {
                return Err(CodecError::Invalid(
                    "DSF delivery authorities are not strictly canonical",
                ));
            }
            prior_delivery = Some(key);
        }
        let delivery_count = u64_len(self.dsf_delivery_authorities.len())?;
        let mut delivery_referenced = vec![false; self.dsf_delivery_authorities.len()];

        let mut lineages = BTreeSet::new();
        let mut prior_position = None;
        let mut trit_cursor = 0_u64;
        let mut causal_cursor = 0_u64;
        for neuron in &self.neurons {
            if !lineages.insert(neuron.lineage) {
                return Err(CodecError::Invalid("neuron lineage is duplicated"));
            }
            if prior_position.is_some_and(|prior| prior >= neuron.field_position) {
                return Err(CodecError::Invalid(
                    "neuron positions are not strictly canonical",
                ));
            }
            validate_partition_range(
                neuron.trit_range,
                &mut trit_cursor,
                self.trit_arena.trit_len,
            )?;
            validate_partition_range(
                neuron.recent_causal_range,
                &mut causal_cursor,
                u64_len(self.causal_receipt_arena.len())?,
            )?;
            validate_causal_sequence(slice_range(
                &self.causal_receipt_arena,
                neuron.recent_causal_range,
            )?)?;
            validate_finite(
                neuron.oscillator_phase_bits,
                "oscillator phase is not finite",
            )?;
            validate_finite(neuron.energetic_bits, "neuron energy is not finite")?;
            for bits in neuron.local_dsf.coordinate_bits {
                validate_finite(bits, "local DSF coordinate is not finite")?;
            }
            if neuron.local_dsf.authority_index >= delivery_count {
                return Err(CodecError::Invalid(
                    "local DSF references missing field-bank authority",
                ));
            }
            let authority_index = usize::try_from(neuron.local_dsf.authority_index)
                .map_err(|_| CodecError::LengthOverflow)?;
            delivery_referenced[authority_index] = true;
            prior_position = Some(neuron.field_position);
        }
        if delivery_referenced.iter().any(|referenced| !referenced) {
            return Err(CodecError::Invalid(
                "DSF delivery authority is unreferenced",
            ));
        }
        if trit_cursor != self.trit_arena.trit_len {
            return Err(CodecError::Invalid("trit arena is not fully owned"));
        }
        if causal_cursor != u64_len(self.causal_receipt_arena.len())? {
            return Err(CodecError::Invalid(
                "causal receipt arena is not fully owned",
            ));
        }

        let mut prior_edge = None;
        for coupling in &self.couplings {
            if coupling.source_neuron >= neuron_count || coupling.target_neuron >= neuron_count {
                return Err(CodecError::Invalid(
                    "coupling endpoint is outside neuron arena",
                ));
            }
            if coupling.denominator == 0 {
                return Err(CodecError::Invalid("coupling denominator is zero"));
            }
            if gcd_u64(coupling.numerator.unsigned_abs(), coupling.denominator) != 1 {
                return Err(CodecError::Invalid("coupling rational is not reduced"));
            }
            let key = (coupling.source_neuron, coupling.target_neuron);
            if prior_edge.is_some_and(|prior| prior >= key) {
                return Err(CodecError::Invalid("couplings are not strictly canonical"));
            }
            prior_edge = Some(key);
        }
        validate_strict_indices(&self.causal_frontier, neuron_count)?;

        let mut member_cursor = 0_u64;
        let mut prior_formation_id = None;
        let mut known = BTreeMap::new();
        for formation in &self.formations {
            if prior_formation_id.is_some_and(|prior| prior >= formation.id) {
                return Err(CodecError::Invalid(
                    "formation ids are not strictly ordered",
                ));
            }
            validate_partition_range(
                formation.member_range,
                &mut member_cursor,
                u64_len(self.formation_member_arena.len())?,
            )?;
            let members = slice_range(&self.formation_member_arena, formation.member_range)?;
            validate_formation_members(formation.kind, members, neuron_count, &known)?;
            known.insert(formation.id, formation.kind);
            prior_formation_id = Some(formation.id);
        }
        if member_cursor != u64_len(self.formation_member_arena.len())? {
            return Err(CodecError::Invalid(
                "formation member arena is not fully owned",
            ));
        }

        let mut evidence_cursor = 0_u64;
        for range in stability_ranges(&self.stability_evidence) {
            validate_partition_range(
                range,
                &mut evidence_cursor,
                u64_len(self.stability_evidence_arena.len())?,
            )?;
            validate_receipt_set(slice_range(&self.stability_evidence_arena, range)?)?;
        }
        if evidence_cursor != u64_len(self.stability_evidence_arena.len())? {
            return Err(CodecError::Invalid(
                "stability evidence arena is not fully owned",
            ));
        }
        Ok(())
    }

    /// Emits structurally canonical but unauthenticated bytes. This method is
    /// deliberately unavailable under an authoritative name; only a future
    /// verified transition/restore capability may emit committable state.
    pub fn encode_unverified(&self, max_encoded_bytes: u64) -> Result<Vec<u8>, CodecError> {
        self.validate_structure()?;
        let mut out = Encoder::new(max_encoded_bytes)?;
        out.fixed(MAGIC)?;
        out.u16(SCHEMA_VERSION)?;
        out.fixed(NEURON_LAYOUT)?;
        out.fixed(&self.identity)?;
        out.u64(self.generation)?;
        out.fixed(&self.prior_state_receipt)?;
        out.fixed(&self.authenticated_world_revision)?;
        out.fixed(&self.body_state_receipt)?;
        encode_causal_receipts(&mut out, &self.admitted_evidence)?;
        encode_trits(&mut out, &self.trit_arena)?;
        encode_causal_receipts(&mut out, &self.causal_receipt_arena)?;
        out.len(self.dsf_delivery_authorities.len())?;
        for value in &self.dsf_delivery_authorities {
            encode_dsf_authority(&mut out, value)?;
        }
        out.len(self.neurons.len())?;
        for value in &self.neurons {
            encode_neuron(&mut out, value)?;
        }
        out.len(self.couplings.len())?;
        for value in &self.couplings {
            encode_coupling(&mut out, value)?;
        }
        out.len(self.causal_frontier.len())?;
        for value in &self.causal_frontier {
            out.u64(*value)?;
        }
        encode_formation_members(&mut out, &self.formation_member_arena)?;
        out.len(self.formations.len())?;
        for value in &self.formations {
            encode_formation(&mut out, value)?;
        }
        encode_receipts(&mut out, &self.stability_evidence_arena)?;
        for range in stability_ranges(&self.stability_evidence) {
            encode_range(&mut out, range)?;
        }
        encode_wake(&mut out, &self.wake)?;
        out.u64(self.resources.cpu_nanoseconds)?;
        out.u64(self.resources.resident_bytes)?;
        out.u64(self.resources.durable_bytes)?;
        out.u64(self.resources.recovery_reserve_bytes)?;
        out.u64(self.resources.python_calls)?;
        out.u64(self.resources.native_calls)?;
        Ok(out.bytes)
    }
}

pub fn decode_structure(
    bytes: &[u8],
    budget: DecodeBudget,
) -> Result<UnverifiedOrganismState, CodecError> {
    if u64_len(bytes.len())? > budget.max_input_bytes {
        return Err(CodecError::InputBudgetExceeded);
    }
    let mut input = Decoder::new(bytes, budget.max_heap_bytes);
    if input.fixed::<8>()? != *MAGIC {
        return Err(CodecError::BadMagic);
    }
    let version = input.u16()?;
    if version != SCHEMA_VERSION {
        return Err(CodecError::UnsupportedVersion(version));
    }
    if input.fixed::<16>()? != *NEURON_LAYOUT {
        return Err(CodecError::WrongNeuronLayout);
    }
    let identity = input.fixed()?;
    let generation = input.u64()?;
    let prior_state_receipt = input.fixed()?;
    let authenticated_world_revision = input.fixed()?;
    let body_state_receipt = input.fixed()?;
    let admitted_evidence = decode_causal_receipts(&mut input)?;
    let trit_arena = decode_trits(&mut input)?;
    let causal_receipt_arena = decode_causal_receipts(&mut input)?;
    let dsf_delivery_authorities = decode_vec(&mut input, 176, decode_dsf_authority)?;
    let neurons = decode_vec(&mut input, 280, decode_neuron)?;
    let couplings = decode_vec(&mut input, 64, decode_coupling)?;
    let causal_frontier = decode_u64_vec(&mut input)?;
    let formation_member_arena = decode_formation_members(&mut input)?;
    let formations = decode_vec(&mut input, 89, decode_formation)?;
    let stability_evidence_arena = decode_receipts(&mut input)?;
    let stability_evidence = StabilityEvidenceRanges {
        coherence: decode_range(&mut input)?,
        formation_entropy: decode_range(&mut input)?,
        breathing_variance: decode_range(&mut input)?,
        uncertainty: decode_range(&mut input)?,
        tapestry_drift: decode_range(&mut input)?,
    };
    let wake = decode_wake(&mut input)?;
    let resources = ResourceObservation {
        cpu_nanoseconds: input.u64()?,
        resident_bytes: input.u64()?,
        durable_bytes: input.u64()?,
        recovery_reserve_bytes: input.u64()?,
        python_calls: input.u64()?,
        native_calls: input.u64()?,
    };
    if !input.is_finished() {
        return Err(CodecError::TrailingBytes);
    }
    let state = OrganismState {
        identity,
        generation,
        prior_state_receipt,
        authenticated_world_revision,
        body_state_receipt,
        admitted_evidence,
        trit_arena,
        causal_receipt_arena,
        dsf_delivery_authorities,
        neurons,
        couplings,
        causal_frontier,
        formation_member_arena,
        formations,
        stability_evidence_arena,
        stability_evidence,
        wake,
        resources,
    };
    state.validate_structure()?;
    let digest = Sha256::digest(bytes);
    let mut source_receipt = [0_u8; 32];
    source_receipt.copy_from_slice(&digest);
    Ok(UnverifiedOrganismState {
        state,
        source_receipt,
    })
}

fn validate_causal_sequence(values: &[CausalReceipt]) -> Result<(), CodecError> {
    let mut prior = None;
    for value in values {
        if prior.is_some_and(|ordinal| ordinal >= value.ordinal) {
            return Err(CodecError::Invalid(
                "causal ordinals are not strictly increasing",
            ));
        }
        prior = Some(value.ordinal);
    }
    Ok(())
}

fn validate_receipt_set(values: &[[u8; 32]]) -> Result<(), CodecError> {
    let mut prior = None;
    for value in values {
        if prior.is_some_and(|receipt: [u8; 32]| receipt >= *value) {
            return Err(CodecError::Invalid(
                "evidence set is not strictly canonical",
            ));
        }
        prior = Some(*value);
    }
    Ok(())
}

fn validate_partition_range(
    range: ArenaRange,
    cursor: &mut u64,
    total: u64,
) -> Result<(), CodecError> {
    if range.start != *cursor {
        return Err(CodecError::Invalid("arena ranges are not contiguous"));
    }
    let end = range
        .start
        .checked_add(range.len)
        .ok_or(CodecError::LengthOverflow)?;
    if end > total {
        return Err(CodecError::Invalid("arena range exceeds its arena"));
    }
    *cursor = end;
    Ok(())
}

fn slice_range<T>(values: &[T], range: ArenaRange) -> Result<&[T], CodecError> {
    let start = usize::try_from(range.start).map_err(|_| CodecError::LengthOverflow)?;
    let end_u64 = range
        .start
        .checked_add(range.len)
        .ok_or(CodecError::LengthOverflow)?;
    let end = usize::try_from(end_u64).map_err(|_| CodecError::LengthOverflow)?;
    values
        .get(start..end)
        .ok_or(CodecError::Invalid("arena slice is outside its arena"))
}

fn validate_strict_indices(values: &[u64], upper: u64) -> Result<(), CodecError> {
    let mut prior = None;
    for value in values {
        if *value >= upper || prior.is_some_and(|index| index >= *value) {
            return Err(CodecError::Invalid(
                "causal frontier is not strictly canonical",
            ));
        }
        prior = Some(*value);
    }
    Ok(())
}

fn validate_formation_members(
    kind: FormationKind,
    members: &[FormationMember],
    neuron_count: u64,
    known: &BTreeMap<u64, FormationKind>,
) -> Result<(), CodecError> {
    if members.is_empty() {
        return Err(CodecError::Invalid("formation is empty"));
    }
    let mut prior = None;
    for member in members {
        if prior.is_some_and(|value| value >= *member) {
            return Err(CodecError::Invalid(
                "formation members are not strictly canonical",
            ));
        }
        let valid = match (kind, member) {
            (FormationKind::Mosaic, FormationMember::Neuron(index)) => *index < neuron_count,
            (FormationKind::MosaicOfMosaics, FormationMember::Formation(id)) => {
                known.get(id) == Some(&FormationKind::Mosaic)
            }
            (FormationKind::Tapestry, FormationMember::Formation(id)) => matches!(
                known.get(id),
                Some(FormationKind::Mosaic | FormationKind::MosaicOfMosaics)
            ),
            (FormationKind::TapestryOfTapestries, FormationMember::Formation(id)) => {
                known.get(id) == Some(&FormationKind::Tapestry)
            }
            (FormationKind::Weave, FormationMember::Formation(id)) => matches!(
                known.get(id),
                Some(FormationKind::Tapestry | FormationKind::TapestryOfTapestries)
            ),
            _ => false,
        };
        if !valid {
            return Err(CodecError::Invalid(
                "formation violates recursive hierarchy",
            ));
        }
        prior = Some(*member);
    }
    Ok(())
}

fn stability_ranges(value: &StabilityEvidenceRanges) -> [ArenaRange; 5] {
    [
        value.coherence,
        value.formation_entropy,
        value.breathing_variance,
        value.uncertainty,
        value.tapestry_drift,
    ]
}

fn validate_finite(bits: u64, reason: &'static str) -> Result<(), CodecError> {
    if f64::from_bits(bits).is_finite() {
        Ok(())
    } else {
        Err(CodecError::Invalid(reason))
    }
}

fn gcd_u64(mut left: u64, mut right: u64) -> u64 {
    while right != 0 {
        let remainder = left % right;
        left = right;
        right = remainder;
    }
    left
}

fn packed_byte_len(trit_len: u64) -> Result<usize, CodecError> {
    let value = trit_len.checked_add(3).ok_or(CodecError::LengthOverflow)? / 4;
    usize::try_from(value).map_err(|_| CodecError::LengthOverflow)
}

fn u64_len(value: usize) -> Result<u64, CodecError> {
    u64::try_from(value).map_err(|_| CodecError::LengthOverflow)
}

fn encode_range(out: &mut Encoder, value: ArenaRange) -> Result<(), CodecError> {
    out.u64(value.start)?;
    out.u64(value.len)
}

fn decode_range(input: &mut Decoder<'_>) -> Result<ArenaRange, CodecError> {
    Ok(ArenaRange {
        start: input.u64()?,
        len: input.u64()?,
    })
}

fn encode_causal_receipts(out: &mut Encoder, values: &[CausalReceipt]) -> Result<(), CodecError> {
    out.len(values.len())?;
    for value in values {
        out.u64(value.ordinal)?;
        out.fixed(&value.receipt)?;
    }
    Ok(())
}

fn decode_causal_receipts(input: &mut Decoder<'_>) -> Result<Vec<CausalReceipt>, CodecError> {
    decode_vec(input, 40, |source| {
        Ok(CausalReceipt {
            ordinal: source.u64()?,
            receipt: source.fixed()?,
        })
    })
}

fn encode_trits(out: &mut Encoder, value: &PackedTrits) -> Result<(), CodecError> {
    value.validate()?;
    out.u64(value.trit_len)?;
    out.len(value.bytes.len())?;
    out.raw(&value.bytes)
}

fn decode_trits(input: &mut Decoder<'_>) -> Result<PackedTrits, CodecError> {
    let trit_len = input.u64()?;
    let byte_len = input.count(1)?;
    if byte_len != packed_byte_len(trit_len)? {
        return Err(CodecError::Invalid(
            "packed trit byte length is not canonical",
        ));
    }
    input.reserve_allocation(byte_len, 1)?;
    let value = PackedTrits {
        trit_len,
        bytes: input.take(byte_len)?.to_vec(),
    };
    value.validate()?;
    Ok(value)
}

fn encode_neuron(out: &mut Encoder, value: &NeuronState) -> Result<(), CodecError> {
    out.fixed(&value.lineage)?;
    out.fixed(&value.growth_dna)?;
    out.fixed(&value.specialization_receipt)?;
    out.u64(value.field_position)?;
    encode_range(out, value.trit_range)?;
    out.u64(value.oscillator_phase_bits)?;
    out.i64(value.oscillator_winding)?;
    for bits in value.local_dsf.coordinate_bits {
        out.u64(bits)?;
    }
    out.u64(value.local_dsf.authority_index)?;
    out.u64(value.energetic_bits)?;
    out.u64(value.refractory_until_generation)?;
    out.fixed(&value.fractal)?;
    out.fixed(&value.evidence_receipt)?;
    encode_range(out, value.recent_causal_range)
}

fn decode_neuron(input: &mut Decoder<'_>) -> Result<NeuronState, CodecError> {
    let lineage = input.fixed()?;
    let growth_dna = input.fixed()?;
    let specialization_receipt = input.fixed()?;
    let field_position = input.u64()?;
    let trit_range = decode_range(input)?;
    let oscillator_phase_bits = input.u64()?;
    let oscillator_winding = input.i64()?;
    let mut coordinate_bits = [0_u64; 7];
    for bits in &mut coordinate_bits {
        *bits = input.u64()?;
    }
    Ok(NeuronState {
        lineage,
        growth_dna,
        specialization_receipt,
        field_position,
        trit_range,
        oscillator_phase_bits,
        oscillator_winding,
        local_dsf: LocalDsfState {
            coordinate_bits,
            authority_index: input.u64()?,
        },
        energetic_bits: input.u64()?,
        refractory_until_generation: input.u64()?,
        fractal: input.fixed()?,
        evidence_receipt: input.fixed()?,
        recent_causal_range: decode_range(input)?,
    })
}

fn encode_dsf_authority(out: &mut Encoder, value: &DsfDeliveryAuthority) -> Result<(), CodecError> {
    out.fixed(&value.field_bank_receipt)?;
    out.fixed(&value.kernel_config_receipt)?;
    out.u64(value.port_index)?;
    out.u64(value.tuple_index)?;
    out.fixed(&value.trace_receipt)?;
    out.fixed(&value.tuple_receipt)?;
    out.fixed(&value.basin_receipt)
}

fn decode_dsf_authority(input: &mut Decoder<'_>) -> Result<DsfDeliveryAuthority, CodecError> {
    Ok(DsfDeliveryAuthority {
        field_bank_receipt: input.fixed()?,
        kernel_config_receipt: input.fixed()?,
        port_index: input.u64()?,
        tuple_index: input.u64()?,
        trace_receipt: input.fixed()?,
        tuple_receipt: input.fixed()?,
        basin_receipt: input.fixed()?,
    })
}

fn encode_coupling(out: &mut Encoder, value: &CouplingState) -> Result<(), CodecError> {
    out.u64(value.source_neuron)?;
    out.u64(value.target_neuron)?;
    out.i64(value.numerator)?;
    out.u64(value.denominator)?;
    out.fixed(&value.causal_receipt)
}

fn decode_coupling(input: &mut Decoder<'_>) -> Result<CouplingState, CodecError> {
    Ok(CouplingState {
        source_neuron: input.u64()?,
        target_neuron: input.u64()?,
        numerator: input.i64()?,
        denominator: input.u64()?,
        causal_receipt: input.fixed()?,
    })
}

fn encode_formation_members(
    out: &mut Encoder,
    values: &[FormationMember],
) -> Result<(), CodecError> {
    out.len(values.len())?;
    for value in values {
        match value {
            FormationMember::Neuron(index) => {
                out.u8(0)?;
                out.u64(*index)?;
            }
            FormationMember::Formation(id) => {
                out.u8(1)?;
                out.u64(*id)?;
            }
        }
    }
    Ok(())
}

fn decode_formation_members(input: &mut Decoder<'_>) -> Result<Vec<FormationMember>, CodecError> {
    decode_vec(input, 9, |source| {
        let tag = source.u8()?;
        let value = source.u64()?;
        match tag {
            0 => Ok(FormationMember::Neuron(value)),
            1 => Ok(FormationMember::Formation(value)),
            _ => Err(CodecError::Invalid("unknown formation member kind")),
        }
    })
}

fn encode_formation(out: &mut Encoder, value: &FormationState) -> Result<(), CodecError> {
    out.u64(value.id)?;
    out.u8(value.kind as u8)?;
    encode_range(out, value.member_range)?;
    out.fixed(&value.structural_impression)?;
    out.fixed(&value.evidence_receipt)
}

fn decode_formation(input: &mut Decoder<'_>) -> Result<FormationState, CodecError> {
    Ok(FormationState {
        id: input.u64()?,
        kind: FormationKind::decode(input.u8()?)?,
        member_range: decode_range(input)?,
        structural_impression: input.fixed()?,
        evidence_receipt: input.fixed()?,
    })
}

fn encode_receipts(out: &mut Encoder, values: &[[u8; 32]]) -> Result<(), CodecError> {
    out.len(values.len())?;
    for value in values {
        out.fixed(value)?;
    }
    Ok(())
}

fn decode_receipts(input: &mut Decoder<'_>) -> Result<Vec<[u8; 32]>, CodecError> {
    decode_vec(input, 32, |source| source.fixed())
}

fn encode_wake(out: &mut Encoder, value: &WakeState) -> Result<(), CodecError> {
    match value {
        WakeState::Quiescent => out.u8(0),
        WakeState::AtBodyTick {
            body_clock_receipt,
            tick,
            cause_receipt,
        } => {
            out.u8(1)?;
            out.fixed(body_clock_receipt)?;
            out.u64(*tick)?;
            out.fixed(cause_receipt)
        }
        WakeState::WorldRevision {
            revision,
            cause_receipt,
        } => {
            out.u8(2)?;
            out.u64(*revision)?;
            out.fixed(cause_receipt)
        }
        WakeState::PhysicalCondition { condition_receipt } => {
            out.u8(3)?;
            out.fixed(condition_receipt)
        }
    }
}

fn decode_wake(input: &mut Decoder<'_>) -> Result<WakeState, CodecError> {
    match input.u8()? {
        0 => Ok(WakeState::Quiescent),
        1 => Ok(WakeState::AtBodyTick {
            body_clock_receipt: input.fixed()?,
            tick: input.u64()?,
            cause_receipt: input.fixed()?,
        }),
        2 => Ok(WakeState::WorldRevision {
            revision: input.u64()?,
            cause_receipt: input.fixed()?,
        }),
        3 => Ok(WakeState::PhysicalCondition {
            condition_receipt: input.fixed()?,
        }),
        _ => Err(CodecError::Invalid("unknown wake-state kind")),
    }
}

fn decode_vec<T, F>(
    input: &mut Decoder<'_>,
    minimum: usize,
    mut item: F,
) -> Result<Vec<T>, CodecError>
where
    F: FnMut(&mut Decoder<'_>) -> Result<T, CodecError>,
{
    let count = input.count(minimum)?;
    input.reserve_allocation(count, size_of::<T>())?;
    let mut values = Vec::with_capacity(count);
    for _ in 0..count {
        values.push(item(input)?);
    }
    Ok(values)
}

fn decode_u64_vec(input: &mut Decoder<'_>) -> Result<Vec<u64>, CodecError> {
    decode_vec(input, 8, |source| source.u64())
}

struct Encoder {
    bytes: Vec<u8>,
    max_bytes: usize,
}

impl Encoder {
    fn new(max_bytes: u64) -> Result<Self, CodecError> {
        Ok(Self {
            bytes: Vec::new(),
            max_bytes: usize::try_from(max_bytes).map_err(|_| CodecError::LengthOverflow)?,
        })
    }
    fn raw(&mut self, value: &[u8]) -> Result<(), CodecError> {
        let end = self
            .bytes
            .len()
            .checked_add(value.len())
            .ok_or(CodecError::LengthOverflow)?;
        if end > self.max_bytes {
            return Err(CodecError::EncodedBudgetExceeded);
        }
        self.bytes.extend_from_slice(value);
        Ok(())
    }
    fn u8(&mut self, value: u8) -> Result<(), CodecError> {
        self.raw(&[value])
    }
    fn u16(&mut self, value: u16) -> Result<(), CodecError> {
        self.raw(&value.to_le_bytes())
    }
    fn u64(&mut self, value: u64) -> Result<(), CodecError> {
        self.raw(&value.to_le_bytes())
    }
    fn i64(&mut self, value: i64) -> Result<(), CodecError> {
        self.raw(&value.to_le_bytes())
    }
    fn fixed<const N: usize>(&mut self, value: &[u8; N]) -> Result<(), CodecError> {
        self.raw(value)
    }
    fn len(&mut self, value: usize) -> Result<(), CodecError> {
        self.u64(u64_len(value)?)
    }
}

struct Decoder<'a> {
    bytes: &'a [u8],
    position: usize,
    heap_remaining: u64,
}

impl<'a> Decoder<'a> {
    fn new(bytes: &'a [u8], heap_remaining: u64) -> Self {
        Self {
            bytes,
            position: 0,
            heap_remaining,
        }
    }
    fn remaining(&self) -> usize {
        self.bytes.len() - self.position
    }
    fn take(&mut self, length: usize) -> Result<&'a [u8], CodecError> {
        let end = self
            .position
            .checked_add(length)
            .ok_or(CodecError::LengthOverflow)?;
        if end > self.bytes.len() {
            return Err(CodecError::UnexpectedEnd);
        }
        let value = &self.bytes[self.position..end];
        self.position = end;
        Ok(value)
    }
    fn reserve_allocation(&mut self, count: usize, item_size: usize) -> Result<(), CodecError> {
        let bytes = count
            .checked_mul(item_size)
            .ok_or(CodecError::LengthOverflow)?;
        let bytes = u64_len(bytes)?;
        if bytes > self.heap_remaining {
            return Err(CodecError::AllocationBudgetExceeded);
        }
        self.heap_remaining -= bytes;
        Ok(())
    }
    fn count(&mut self, minimum: usize) -> Result<usize, CodecError> {
        let count = usize::try_from(self.u64()?).map_err(|_| CodecError::LengthOverflow)?;
        if count > self.remaining() / minimum {
            return Err(CodecError::UnexpectedEnd);
        }
        Ok(count)
    }
    fn u8(&mut self) -> Result<u8, CodecError> {
        Ok(self.take(1)?[0])
    }
    fn u16(&mut self) -> Result<u16, CodecError> {
        Ok(u16::from_le_bytes(self.fixed()?))
    }
    fn u64(&mut self) -> Result<u64, CodecError> {
        Ok(u64::from_le_bytes(self.fixed()?))
    }
    fn i64(&mut self) -> Result<i64, CodecError> {
        Ok(i64::from_le_bytes(self.fixed()?))
    }
    fn fixed<const N: usize>(&mut self) -> Result<[u8; N], CodecError> {
        let mut value = [0_u8; N];
        value.copy_from_slice(self.take(N)?);
        Ok(value)
    }
    fn is_finished(&self) -> bool {
        self.position == self.bytes.len()
    }
}
