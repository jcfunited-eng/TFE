//! Current-only resident D3 organism carrier.
//!
//! The ordinary runtime contains one current cognitive state, one exact virtual
//! yaw-body state, and one exact virtual semicircular-canal state. It contains
//! no mounted-delivery, legacy fabric, owner, database, or fallback cognition.
//! A fixed optional predecessor receipt is migration evidence only; legacy
//! bytes are never resident state and cannot be advanced by this runtime.

use std::fmt;

use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;

use num_bigint::BigInt;
use num_rational::BigRational;

use crate::developmental_electrical_anatomy::build_authored_growth_dna_seeds;
use crate::joint_source_episode::NativeJointSourceEpisode;
use crate::joint_uf_source_adapter::{AdmittedJointSourceEpisode, JointUfSourceAdmission};
use crate::physical_cognitive_capital::{
    observe_transition_cognitive_capital, CognitiveCapability, CognitiveCapitalDimension,
    CognitiveCapitalObservation, COGNITIVE_CAPITAL_SCHEMA,
};
use crate::resident_cognitive_formation::{
    CognitiveFormationObservation, PreparedCognitiveFormationTransition,
    ResidentCognitiveFormationState,
};
use crate::sha256::sha256;
use crate::virtual_body_yaw_motion::{decode_yaw_body_state, encode_yaw_body_state, YawBodyState};
use crate::virtual_vestibular_canal::{encode_canal_state, CanalState};

const ENVELOPE_MAGIC: &[u8; 8] = b"GLORUN01";
const ENVELOPE_VERSION: u16 = 3;
const FABRIC_MAGIC: &[u8; 8] = b"GLD3FAB1";
const FABRIC_VERSION: u16 = 2;
const IDENTITY_BYTES: usize = 36;
const YAW_BODY_STATE_BYTES: usize = 4;
const CANAL_STATE_BYTES: usize = 32;
const EMBODIMENT_STATE_BYTES: usize = YAW_BODY_STATE_BYTES + CANAL_STATE_BYTES;
const ENVELOPE_FIXED_BYTES: usize =
    ENVELOPE_MAGIC.len() + 2 + IDENTITY_BYTES + std::mem::size_of::<u64>() + 4;
const FABRIC_FIXED_BYTES: usize =
    FABRIC_MAGIC.len() + 2 + std::mem::size_of::<u64>() + 1 + 32 + EMBODIMENT_STATE_BYTES + 4;
const PREPARE_TOKEN_DOMAIN: &[u8; 8] = b"GLD3TPN1";
const OBSERVATION_SCHEMA: &str = "guala.native.resident_d3.observation.v1";

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct ResidentD3Budget {
    max_envelope_bytes: usize,
    max_cognitive_bytes: usize,
}

impl ResidentD3Budget {
    pub fn new(
        max_envelope_bytes: usize,
        max_cognitive_bytes: usize,
    ) -> Result<Self, ResidentD3Error> {
        let minimum = ENVELOPE_FIXED_BYTES
            .checked_add(FABRIC_FIXED_BYTES)
            .and_then(|value| value.checked_add(max_cognitive_bytes))
            .ok_or(ResidentD3Error::ArithmeticOverflow)?;
        if max_cognitive_bytes == 0 || minimum > max_envelope_bytes {
            return Err(ResidentD3Error::InvalidBudget);
        }
        Ok(Self {
            max_envelope_bytes,
            max_cognitive_bytes,
        })
    }
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub enum ResidentD3Error {
    InvalidBudget,
    ArithmeticOverflow,
    EnvelopeBudgetExceeded,
    CognitiveBudgetExceeded,
    BadEnvelopeMagic,
    BadEnvelopeVersion(u16),
    BadFabricMagic,
    BadFabricVersion(u16),
    InvalidIdentity,
    InvalidLegacyReceipt,
    InvalidYawBodyState,
    InvalidCanalState,
    TruncatedState,
    NoncanonicalState,
    OrganismTickOverflow,
    FabricGenerationOverflow,
    PendingCandidateExists,
    PendingCandidateMissing,
    PendingTokenMismatch,
    PrepareOrdinalOverflow,
    Cognitive(String),
}

impl fmt::Display for ResidentD3Error {
    fn fmt(&self, output: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::InvalidBudget => write!(output, "resident D3 budget is structurally invalid"),
            Self::ArithmeticOverflow => write!(output, "resident D3 arithmetic overflow"),
            Self::EnvelopeBudgetExceeded => {
                write!(output, "resident D3 envelope exceeds admitted bytes")
            }
            Self::CognitiveBudgetExceeded => {
                write!(output, "resident D3 cognitive state exceeds admitted bytes")
            }
            Self::BadEnvelopeMagic => write!(output, "state is not current GLORUN01"),
            Self::BadEnvelopeVersion(version) => {
                write!(
                    output,
                    "GLORUN01 version {version} is not current resident D3"
                )
            }
            Self::BadFabricMagic => write!(output, "state does not contain GLD3FAB1"),
            Self::BadFabricVersion(version) => {
                write!(output, "GLD3FAB1 version {version} is unsupported")
            }
            Self::InvalidIdentity => write!(output, "organism identity is not canonical UUID text"),
            Self::InvalidLegacyReceipt => {
                write!(output, "legacy predecessor receipt is not canonical")
            }
            Self::InvalidYawBodyState => write!(output, "resident yaw-body state is invalid"),
            Self::InvalidCanalState => write!(
                output,
                "resident canal state is not the current at-rest foundation"
            ),
            Self::TruncatedState => write!(output, "resident D3 state ended early"),
            Self::NoncanonicalState => write!(output, "resident D3 state is noncanonical"),
            Self::OrganismTickOverflow => write!(output, "organism tick overflow"),
            Self::FabricGenerationOverflow => write!(output, "fabric generation overflow"),
            Self::PendingCandidateExists => {
                write!(
                    output,
                    "resident D3 runtime already has one pending successor"
                )
            }
            Self::PendingCandidateMissing => {
                write!(output, "resident D3 runtime has no pending successor")
            }
            Self::PendingTokenMismatch => write!(output, "pending successor token changed"),
            Self::PrepareOrdinalOverflow => write!(output, "prepare ordinal overflow"),
            Self::Cognitive(reason) => write!(output, "resident cognition failed: {reason}"),
        }
    }
}

impl std::error::Error for ResidentD3Error {}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct ResidentD3Observation {
    identity: [u8; IDENTITY_BYTES],
    organism_tick: u64,
    fabric_generation: u64,
    cognitive_generation: u64,
    state_receipt: [u8; 32],
    source_authority: Option<[u8; 32]>,
    legacy_predecessor_receipt: Option<[u8; 32]>,
    state_bytes: usize,
    cognitive_bytes: usize,
    dsf_delivery_count: usize,
    complete_neuron_count: usize,
    physically_transitioned_neuron_count: usize,
    complete_neuron_fractal_count: usize,
    cognitive_mosaic_count: usize,
    partial_cue_reassembly_count: usize,
    endogenous_partial_cue_reassembly_count: usize,
    cognitive_capital: Option<CognitiveCapitalObservation>,
}

impl ResidentD3Observation {
    pub fn schema(&self) -> &'static str {
        OBSERVATION_SCHEMA
    }

    pub fn identity(&self) -> &str {
        std::str::from_utf8(&self.identity).expect("validated resident identity")
    }

    pub fn organism_tick(&self) -> u64 {
        self.organism_tick
    }

    pub fn fabric_generation(&self) -> u64 {
        self.fabric_generation
    }

    pub fn cognitive_generation(&self) -> u64 {
        self.cognitive_generation
    }

    pub fn state_receipt(&self) -> [u8; 32] {
        self.state_receipt
    }

    pub fn source_authority(&self) -> Option<[u8; 32]> {
        self.source_authority
    }

    pub fn legacy_predecessor_receipt(&self) -> Option<[u8; 32]> {
        self.legacy_predecessor_receipt
    }

    pub fn state_bytes(&self) -> usize {
        self.state_bytes
    }

    pub fn cognitive_bytes(&self) -> usize {
        self.cognitive_bytes
    }

    pub fn dsf_delivery_count(&self) -> usize {
        self.dsf_delivery_count
    }

    pub fn complete_neuron_count(&self) -> usize {
        self.complete_neuron_count
    }

    pub fn physically_transitioned_neuron_count(&self) -> usize {
        self.physically_transitioned_neuron_count
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

    pub fn endogenous_partial_cue_reassembly_count(&self) -> usize {
        self.endogenous_partial_cue_reassembly_count
    }

    pub fn cognitive_capital(&self) -> Option<&CognitiveCapitalObservation> {
        self.cognitive_capital.as_ref()
    }

    pub fn python_callback_count(&self) -> u64 {
        0
    }
}

#[derive(Debug, Eq, PartialEq)]
struct ActiveResidentD3 {
    envelope: Vec<u8>,
    yaw_body: YawBodyState,
    canal: CanalState,
    cognitive: ResidentCognitiveFormationState,
    observation: ResidentD3Observation,
}

#[derive(Debug, Eq, PartialEq)]
struct PendingResidentD3 {
    token: [u8; 32],
    envelope: Vec<u8>,
    yaw_body: YawBodyState,
    canal: CanalState,
    cognitive: PreparedCognitiveFormationTransition,
    observation: ResidentD3Observation,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct ResidentD3Prepared {
    token: [u8; 32],
    observation: ResidentD3Observation,
}

impl ResidentD3Prepared {
    pub fn token(&self) -> [u8; 32] {
        self.token
    }

    pub fn observation(&self) -> &ResidentD3Observation {
        &self.observation
    }
}

#[derive(Debug, Eq, PartialEq)]
pub struct ResidentD3Runtime {
    active: ActiveResidentD3,
    pending: Option<PendingResidentD3>,
    budget: ResidentD3Budget,
    next_prepare_ordinal: u64,
}

impl ResidentD3Runtime {
    /// Restore requires NOTHING but her own persisted bytes.
    ///
    /// This used to additionally dereference the archive checkpoint against a
    /// cold-custody directory and refuse the restore if the objects were
    /// missing — which made her un-restorable away from her archive.  Nothing
    /// reads the checkpoint any more, so nothing validates it: her body is
    /// sufficient for her to come back.
    pub fn restore(
        envelope: Vec<u8>,
        budget: ResidentD3Budget,
    ) -> Result<Self, ResidentD3Error> {
        Self::restore_structural(envelope, budget)
    }

    fn restore_structural(
        envelope: Vec<u8>,
        budget: ResidentD3Budget,
    ) -> Result<Self, ResidentD3Error> {
        let parsed = parse_current_state(&envelope, budget)?;
        let cognitive = ResidentCognitiveFormationState::decode(
            parsed.cognitive_bytes,
            budget.max_cognitive_bytes,
        )
        .map_err(|error| ResidentD3Error::Cognitive(error.to_string()))?;
        let summary = cognitive.summary();
        let yaw_body = parsed.yaw_body;
        let canal = parsed.canal;
        let observation = ResidentD3Observation {
            identity: parsed.identity,
            organism_tick: parsed.organism_tick,
            fabric_generation: parsed.fabric_generation,
            cognitive_generation: summary.cognitive_ordinal,
            state_receipt: sha256(&envelope),
            source_authority: None,
            legacy_predecessor_receipt: parsed.legacy_predecessor_receipt,
            state_bytes: envelope.len(),
            cognitive_bytes: parsed.cognitive_bytes.len(),
            dsf_delivery_count: 0,
            complete_neuron_count: summary.complete_neuron_count,
            physically_transitioned_neuron_count: 0,
            complete_neuron_fractal_count: 0,
            cognitive_mosaic_count: summary.mosaic_count,
            partial_cue_reassembly_count: 0,
            endogenous_partial_cue_reassembly_count: 0,
            cognitive_capital: None,
        };
        Ok(Self {
            active: ActiveResidentD3 {
                envelope,
                yaw_body,
                canal,
                cognitive,
                observation,
            },
            pending: None,
            budget,
            next_prepare_ordinal: 1,
        })
    }

    pub fn prepare(
        &mut self,
        _source: &NativeJointSourceEpisode,
    ) -> Result<ResidentD3Prepared, ResidentD3Error> {
        if self.pending.is_some() {
            return Err(ResidentD3Error::PendingCandidateExists);
        }
        Err(ResidentD3Error::Cognitive(
            "explicit admitted joint source episode is required".to_owned(),
        ))
    }

    pub(crate) fn prepare_admitted(
        &mut self,
        admitted_source: &AdmittedJointSourceEpisode,
    ) -> Result<ResidentD3Prepared, ResidentD3Error> {
        if self.pending.is_some() {
            return Err(ResidentD3Error::PendingCandidateExists);
        }
        let source = admitted_source.episode();
        let organism_tick = self
            .active
            .observation
            .organism_tick
            .checked_add(1)
            .ok_or(ResidentD3Error::OrganismTickOverflow)?;
        let fabric_generation = self
            .active
            .observation
            .fabric_generation
            .checked_add(1)
            .ok_or(ResidentD3Error::FabricGenerationOverflow)?;
        let prepared = self
            .active
            .cognitive
            .prepare_admitted_transition(admitted_source, self.budget.max_cognitive_bytes)
            .map_err(|error| ResidentD3Error::Cognitive(error.to_string()))?;
        let cognitive_bytes = self
            .active
            .cognitive
            .encode_staged_successor(&prepared, self.budget.max_cognitive_bytes)
            .map_err(|error| ResidentD3Error::Cognitive(error.to_string()))?;
        let cognitive_observation = prepared.observation().clone();
        let envelope = encode_current_state(
            self.active.observation.identity,
            organism_tick,
            fabric_generation,
            self.active.observation.legacy_predecessor_receipt,
            self.active.yaw_body,
            self.active.canal,
            &cognitive_bytes,
            self.budget,
        )?;
        let state_receipt = sha256(&envelope);
        let observation = step_observation(
            &self.active.observation,
            organism_tick,
            fabric_generation,
            state_receipt,
            envelope.len(),
            cognitive_bytes.len(),
            source.joint_source_authority_receipt(),
            &cognitive_observation,
        );
        let next_prepare_ordinal = self
            .next_prepare_ordinal
            .checked_add(1)
            .ok_or(ResidentD3Error::PrepareOrdinalOverflow)?;
        let token = prepare_token(
            self.active.observation.state_receipt,
            state_receipt,
            source.joint_source_authority_receipt(),
            self.next_prepare_ordinal,
        );
        self.pending = Some(PendingResidentD3 {
            token,
            envelope,
            yaw_body: self.active.yaw_body,
            canal: self.active.canal,
            cognitive: prepared,
            observation: observation.clone(),
        });
        self.next_prepare_ordinal = next_prepare_ordinal;
        Ok(ResidentD3Prepared { token, observation })
    }

    pub fn commit(&mut self, token: [u8; 32]) -> Result<(), ResidentD3Error> {
        let pending = self
            .pending
            .as_ref()
            .ok_or(ResidentD3Error::PendingCandidateMissing)?;
        if pending.token != token {
            return Err(ResidentD3Error::PendingTokenMismatch);
        }
        // Nothing is published to cold custody: a commit moves her body and
        // nothing else.
        let pending = self
            .pending
            .take()
            .ok_or(ResidentD3Error::PendingCandidateMissing)?;
        let PendingResidentD3 {
            token: pending_token,
            envelope,
            yaw_body,
            canal,
            cognitive,
            observation,
        } = pending;
        match cognitive.try_into_successor(&self.active.cognitive) {
            Ok((cognitive, _)) => {
                self.active = ActiveResidentD3 {
                    envelope,
                    yaw_body,
                    canal,
                    cognitive,
                    observation,
                };
                Ok(())
            }
            Err((error, cognitive)) => {
                self.pending = Some(PendingResidentD3 {
                    token: pending_token,
                    envelope,
                    yaw_body,
                    canal,
                    cognitive,
                    observation,
                });
                Err(ResidentD3Error::Cognitive(error.to_string()))
            }
        }
    }

    pub fn discard(&mut self, token: [u8; 32]) -> Result<(), ResidentD3Error> {
        let pending = self
            .pending
            .as_ref()
            .ok_or(ResidentD3Error::PendingCandidateMissing)?;
        if pending.token != token {
            return Err(ResidentD3Error::PendingTokenMismatch);
        }
        self.pending = None;
        Ok(())
    }

    pub fn current_envelope(&self) -> &[u8] {
        &self.active.envelope
    }

    pub fn observation(&self) -> &ResidentD3Observation {
        &self.active.observation
    }

    pub(crate) fn yaw_body_state(&self) -> YawBodyState {
        self.active.yaw_body
    }

    pub(crate) fn canal_state(&self) -> CanalState {
        self.active.canal
    }
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct NativeResidentD3Transition {
    successor: Vec<u8>,
    observation: ResidentD3Observation,
}

impl NativeResidentD3Transition {
    pub fn successor(&self) -> &[u8] {
        &self.successor
    }

    pub fn observation(&self) -> &ResidentD3Observation {
        &self.observation
    }

    pub fn python_callback_count(&self) -> u64 {
        0
    }
}

pub fn create_native_resident_d3_genesis(
    organism_identity: &str,
    organism_tick: u64,
    legacy_predecessor_receipt: Option<[u8; 32]>,
    max_envelope_bytes: usize,
    max_cognitive_bytes: usize,
) -> Result<Vec<u8>, String> {
    let identity = canonical_identity(organism_identity).map_err(|error| error.to_string())?;
    let budget = ResidentD3Budget::new(max_envelope_bytes, max_cognitive_bytes)
        .map_err(|error| error.to_string())?;
    let cognitive = ResidentCognitiveFormationState::default()
        .encode(max_cognitive_bytes)
        .map_err(|error| error.to_string())?;
    encode_current_state(
        identity,
        organism_tick,
        0,
        legacy_predecessor_receipt,
        YawBodyState::new(0).map_err(|error| format!("yaw-body genesis failed: {error:?}"))?,
        CanalState::at_rest(),
        &cognitive,
        budget,
    )
    .map_err(|error| error.to_string())
}

/// Genesis with authored developmental growth DNA.
///
/// Identical to `create_native_resident_d3_genesis` except that the resident
/// cognitive state is born carrying the caller's authored unexpressed
/// electrical seeds instead of an empty seed set. Each seed group names port
/// indices of `anatomy_episode` (its authored physical source sites) and its
/// authored contacts as `(left_seed_index, right_seed_index,
/// conductance_picosiemens)`. Nothing is inferred: a seed expresses later only
/// when a grown cohort's reached source sites exactly equal the seed's sites.
pub fn create_native_resident_d3_genesis_with_growth_dna(
    organism_identity: &str,
    organism_tick: u64,
    legacy_predecessor_receipt: Option<[u8; 32]>,
    anatomy_episode: &NativeJointSourceEpisode,
    seed_groups: Vec<(Vec<usize>, Vec<(usize, usize, i64)>)>,
    max_envelope_bytes: usize,
    max_cognitive_bytes: usize,
) -> Result<Vec<u8>, String> {
    let identity = canonical_identity(organism_identity).map_err(|error| error.to_string())?;
    let budget = ResidentD3Budget::new(max_envelope_bytes, max_cognitive_bytes)
        .map_err(|error| error.to_string())?;
    let seeds = build_authored_growth_dna_seeds(anatomy_episode, &seed_groups)?;
    let cognitive = ResidentCognitiveFormationState::from_developmental_electrical_seeds(seeds)
        .map_err(|error| error.to_string())?
        .encode(max_cognitive_bytes)
        .map_err(|error| error.to_string())?;
    encode_current_state(
        identity,
        organism_tick,
        0,
        legacy_predecessor_receipt,
        YawBodyState::new(0).map_err(|error| format!("yaw-body genesis failed: {error:?}"))?,
        CanalState::at_rest(),
        &cognitive,
        budget,
    )
    .map_err(|error| error.to_string())
}

pub fn transition_native_resident_d3(
    _current_envelope: Vec<u8>,
    _source: &NativeJointSourceEpisode,
    _max_envelope_bytes: usize,
    _max_cognitive_bytes: usize,
) -> Result<NativeResidentD3Transition, String> {
    Err("explicit admitted joint source episode is required".to_owned())
}

/// Library transition with the caller's explicitly authored temporal
/// admissions: one maximum causal interval `(numerator, denominator)` in
/// source-time units per source occurrence, in exact occurrence order. The
/// interval is independent environment/anatomy authority carried by the
/// caller; it is never derived from the occurrence itself.
pub fn transition_native_resident_d3_with_authored_admissions(
    current_envelope: Vec<u8>,
    source: &NativeJointSourceEpisode,
    maximum_causal_intervals: &[(i64, i64)],
    max_envelope_bytes: usize,
    max_cognitive_bytes: usize,
) -> Result<NativeResidentD3Transition, String> {
    let ordered_admissions = maximum_causal_intervals
        .iter()
        .enumerate()
        .map(|(occurrence_index, (numerator, denominator))| {
            if *denominator == 0 {
                return Err(format!(
                    "authored admission {occurrence_index} has a zero denominator"
                ));
            }
            JointUfSourceAdmission::new(BigRational::new(
                BigInt::from(*numerator),
                BigInt::from(*denominator),
            ))
            .map(|admission| (occurrence_index, admission))
            .map_err(|error| format!("authored admission {occurrence_index} is invalid: {error:?}"))
        })
        .collect::<Result<Vec<_>, _>>()?;
    let admitted_source = AdmittedJointSourceEpisode::new(source.clone(), ordered_admissions)
        .map_err(|error| format!("{error:?}"))?;
    transition_native_resident_d3_admitted(
        current_envelope,
        &admitted_source,
        max_envelope_bytes,
        max_cognitive_bytes,
    )
}

pub(crate) fn transition_native_resident_d3_admitted(
    current_envelope: Vec<u8>,
    admitted_source: &AdmittedJointSourceEpisode,
    max_envelope_bytes: usize,
    max_cognitive_bytes: usize,
) -> Result<NativeResidentD3Transition, String> {
    let budget = ResidentD3Budget::new(max_envelope_bytes, max_cognitive_bytes)
        .map_err(|error| error.to_string())?;
    let mut runtime = ResidentD3Runtime::restore(current_envelope, budget)
        .map_err(|error| error.to_string())?;
    let prepared = runtime
        .prepare_admitted(admitted_source)
        .map_err(|error| error.to_string())?;
    runtime
        .commit(prepared.token())
        .map_err(|error| error.to_string())?;
    Ok(NativeResidentD3Transition {
        successor: runtime.current_envelope().to_vec(),
        observation: runtime.observation().clone(),
    })
}

struct ParsedCurrentState<'a> {
    identity: [u8; IDENTITY_BYTES],
    organism_tick: u64,
    fabric_generation: u64,
    legacy_predecessor_receipt: Option<[u8; 32]>,
    yaw_body: YawBodyState,
    canal: CanalState,
    cognitive_bytes: &'a [u8],
}

fn parse_current_state(
    envelope: &[u8],
    budget: ResidentD3Budget,
) -> Result<ParsedCurrentState<'_>, ResidentD3Error> {
    if envelope.len() > budget.max_envelope_bytes {
        return Err(ResidentD3Error::EnvelopeBudgetExceeded);
    }
    if envelope.len() < ENVELOPE_FIXED_BYTES + FABRIC_FIXED_BYTES {
        return Err(ResidentD3Error::TruncatedState);
    }
    let mut cursor = 0usize;
    if take(envelope, &mut cursor, ENVELOPE_MAGIC.len())? != ENVELOPE_MAGIC {
        return Err(ResidentD3Error::BadEnvelopeMagic);
    }
    let envelope_version = take_u16(envelope, &mut cursor)?;
    if envelope_version != ENVELOPE_VERSION {
        return Err(ResidentD3Error::BadEnvelopeVersion(envelope_version));
    }
    let identity: [u8; IDENTITY_BYTES] = take(envelope, &mut cursor, IDENTITY_BYTES)?
        .try_into()
        .map_err(|_| ResidentD3Error::InvalidIdentity)?;
    canonical_identity(
        std::str::from_utf8(&identity).map_err(|_| ResidentD3Error::InvalidIdentity)?,
    )?;
    let organism_tick = take_u64(envelope, &mut cursor)?;
    let fabric_length = take_u32(envelope, &mut cursor)? as usize;
    let fabric_end = cursor
        .checked_add(fabric_length)
        .ok_or(ResidentD3Error::ArithmeticOverflow)?;
    if fabric_end != envelope.len() {
        return Err(ResidentD3Error::NoncanonicalState);
    }
    let fabric = &envelope[cursor..fabric_end];
    let mut fabric_cursor = 0usize;
    if take(fabric, &mut fabric_cursor, FABRIC_MAGIC.len())? != FABRIC_MAGIC {
        return Err(ResidentD3Error::BadFabricMagic);
    }
    let fabric_version = take_u16(fabric, &mut fabric_cursor)?;
    if fabric_version != FABRIC_VERSION {
        return Err(ResidentD3Error::BadFabricVersion(fabric_version));
    }
    let fabric_generation = take_u64(fabric, &mut fabric_cursor)?;
    let legacy_present = *take(fabric, &mut fabric_cursor, 1)?
        .first()
        .ok_or(ResidentD3Error::TruncatedState)?;
    let legacy_body: [u8; 32] = take(fabric, &mut fabric_cursor, 32)?
        .try_into()
        .map_err(|_| ResidentD3Error::InvalidLegacyReceipt)?;
    let legacy_predecessor_receipt = match legacy_present {
        0 if legacy_body == [0; 32] => None,
        1 if legacy_body != [0; 32] => Some(legacy_body),
        _ => return Err(ResidentD3Error::InvalidLegacyReceipt),
    };
    let yaw_body = decode_yaw_body_state(take(fabric, &mut fabric_cursor, YAW_BODY_STATE_BYTES)?)
        .map_err(|_| ResidentD3Error::InvalidYawBodyState)?;
    let canal_bytes = take(fabric, &mut fabric_cursor, CANAL_STATE_BYTES)?;
    let canal = CanalState::at_rest();
    if canal_bytes != encode_canal_state(canal) {
        return Err(ResidentD3Error::InvalidCanalState);
    }
    let cognitive_length = take_u32(fabric, &mut fabric_cursor)? as usize;
    if cognitive_length > budget.max_cognitive_bytes {
        return Err(ResidentD3Error::CognitiveBudgetExceeded);
    }
    let cognitive_end = fabric_cursor
        .checked_add(cognitive_length)
        .ok_or(ResidentD3Error::ArithmeticOverflow)?;
    if cognitive_end != fabric.len() {
        return Err(ResidentD3Error::NoncanonicalState);
    }
    Ok(ParsedCurrentState {
        identity,
        organism_tick,
        fabric_generation,
        legacy_predecessor_receipt,
        yaw_body,
        canal,
        cognitive_bytes: &fabric[fabric_cursor..cognitive_end],
    })
}

fn encode_current_state(
    identity: [u8; IDENTITY_BYTES],
    organism_tick: u64,
    fabric_generation: u64,
    legacy_predecessor_receipt: Option<[u8; 32]>,
    yaw_body: YawBodyState,
    canal: CanalState,
    cognitive: &[u8],
    budget: ResidentD3Budget,
) -> Result<Vec<u8>, ResidentD3Error> {
    if cognitive.len() > budget.max_cognitive_bytes {
        return Err(ResidentD3Error::CognitiveBudgetExceeded);
    }
    let fabric_length = FABRIC_FIXED_BYTES
        .checked_add(cognitive.len())
        .ok_or(ResidentD3Error::ArithmeticOverflow)?;
    let envelope_length = ENVELOPE_FIXED_BYTES
        .checked_add(fabric_length)
        .ok_or(ResidentD3Error::ArithmeticOverflow)?;
    if envelope_length > budget.max_envelope_bytes {
        return Err(ResidentD3Error::EnvelopeBudgetExceeded);
    }
    let mut output = Vec::with_capacity(envelope_length);
    output.extend_from_slice(ENVELOPE_MAGIC);
    output.extend_from_slice(&ENVELOPE_VERSION.to_le_bytes());
    output.extend_from_slice(&identity);
    output.extend_from_slice(&organism_tick.to_le_bytes());
    push_u32(&mut output, fabric_length)?;
    output.extend_from_slice(FABRIC_MAGIC);
    output.extend_from_slice(&FABRIC_VERSION.to_le_bytes());
    output.extend_from_slice(&fabric_generation.to_le_bytes());
    output.push(u8::from(legacy_predecessor_receipt.is_some()));
    output.extend_from_slice(&legacy_predecessor_receipt.unwrap_or([0; 32]));
    output.extend_from_slice(&encode_yaw_body_state(yaw_body));
    output.extend_from_slice(&encode_canal_state(canal));
    push_u32(&mut output, cognitive.len())?;
    output.extend_from_slice(cognitive);
    if output.len() != envelope_length {
        return Err(ResidentD3Error::NoncanonicalState);
    }
    Ok(output)
}

fn step_observation(
    predecessor: &ResidentD3Observation,
    organism_tick: u64,
    fabric_generation: u64,
    state_receipt: [u8; 32],
    state_bytes: usize,
    cognitive_bytes: usize,
    source_authority: [u8; 32],
    cognitive: &CognitiveFormationObservation,
) -> ResidentD3Observation {
    let cognitive_capital = observe_transition_cognitive_capital(
        predecessor.state_receipt,
        state_receipt,
        source_authority,
        organism_tick,
        cognitive,
    );
    ResidentD3Observation {
        identity: predecessor.identity,
        organism_tick,
        fabric_generation,
        cognitive_generation: cognitive.cognitive_ordinal,
        state_receipt,
        source_authority: Some(source_authority),
        legacy_predecessor_receipt: predecessor.legacy_predecessor_receipt,
        state_bytes,
        cognitive_bytes,
        dsf_delivery_count: cognitive.dsf_delivery_count,
        complete_neuron_count: cognitive.complete_neuron_count,
        physically_transitioned_neuron_count: cognitive.physically_transitioned_neuron_count,
        complete_neuron_fractal_count: cognitive.complete_neuron_fractal_count,
        cognitive_mosaic_count: cognitive.mosaic_count,
        partial_cue_reassembly_count: cognitive.partial_cue_reassembly_count(),
        endogenous_partial_cue_reassembly_count: cognitive
            .endogenous_partial_cue_reassembly_count(),
        cognitive_capital: Some(cognitive_capital),
    }
}

fn prepare_token(
    predecessor: [u8; 32],
    successor: [u8; 32],
    source: [u8; 32],
    ordinal: u64,
) -> [u8; 32] {
    let mut body = [0u8; 112];
    body[..8].copy_from_slice(PREPARE_TOKEN_DOMAIN);
    body[8..40].copy_from_slice(&predecessor);
    body[40..72].copy_from_slice(&successor);
    body[72..104].copy_from_slice(&source);
    body[104..].copy_from_slice(&ordinal.to_le_bytes());
    sha256(&body)
}

fn canonical_identity(value: &str) -> Result<[u8; IDENTITY_BYTES], ResidentD3Error> {
    let bytes = value.as_bytes();
    if bytes.len() != IDENTITY_BYTES
        || bytes.iter().enumerate().any(|(index, byte)| match index {
            8 | 13 | 18 | 23 => *byte != b'-',
            _ => !byte.is_ascii_digit() && !(b'a'..=b'f').contains(byte),
        })
    {
        return Err(ResidentD3Error::InvalidIdentity);
    }
    bytes
        .try_into()
        .map_err(|_| ResidentD3Error::InvalidIdentity)
}

fn take<'a>(
    bytes: &'a [u8],
    cursor: &mut usize,
    count: usize,
) -> Result<&'a [u8], ResidentD3Error> {
    let end = cursor
        .checked_add(count)
        .ok_or(ResidentD3Error::ArithmeticOverflow)?;
    let value = bytes
        .get(*cursor..end)
        .ok_or(ResidentD3Error::TruncatedState)?;
    *cursor = end;
    Ok(value)
}

fn take_u16(bytes: &[u8], cursor: &mut usize) -> Result<u16, ResidentD3Error> {
    Ok(u16::from_le_bytes(
        take(bytes, cursor, 2)?
            .try_into()
            .map_err(|_| ResidentD3Error::TruncatedState)?,
    ))
}

fn take_u32(bytes: &[u8], cursor: &mut usize) -> Result<u32, ResidentD3Error> {
    Ok(u32::from_le_bytes(
        take(bytes, cursor, 4)?
            .try_into()
            .map_err(|_| ResidentD3Error::TruncatedState)?,
    ))
}

fn take_u64(bytes: &[u8], cursor: &mut usize) -> Result<u64, ResidentD3Error> {
    Ok(u64::from_le_bytes(
        take(bytes, cursor, 8)?
            .try_into()
            .map_err(|_| ResidentD3Error::TruncatedState)?,
    ))
}

fn push_u32(output: &mut Vec<u8>, value: usize) -> Result<(), ResidentD3Error> {
    output.extend_from_slice(
        &u32::try_from(value)
            .map_err(|_| ResidentD3Error::ArithmeticOverflow)?
            .to_le_bytes(),
    );
    Ok(())
}

#[pyclass(frozen, module = "guala_core")]
struct PyResidentD3Observation {
    value: ResidentD3Observation,
}

#[pymethods]
impl PyResidentD3Observation {
    #[getter]
    fn schema(&self) -> &'static str {
        self.value.schema()
    }

    #[getter]
    fn identity(&self) -> &str {
        self.value.identity()
    }

    #[getter]
    fn organism_tick(&self) -> u64 {
        self.value.organism_tick()
    }

    #[getter]
    fn fabric_generation(&self) -> u64 {
        self.value.fabric_generation()
    }

    #[getter]
    fn cognitive_generation(&self) -> u64 {
        self.value.cognitive_generation()
    }

    #[getter]
    fn partial_cue_reassembly_count(&self) -> usize {
        self.value.partial_cue_reassembly_count()
    }

    #[getter]
    fn endogenous_partial_cue_reassembly_count(&self) -> usize {
        self.value.endogenous_partial_cue_reassembly_count()
    }

    #[getter]
    fn cognitive_capital_schema(&self) -> &'static str {
        COGNITIVE_CAPITAL_SCHEMA
    }

    #[getter]
    fn cognitive_capital_capabilities(&self) -> Vec<&'static str> {
        CognitiveCapability::ALL
            .iter()
            .map(|capability| capability.as_str())
            .collect()
    }

    #[getter]
    fn cognitive_capital_dimensions(&self) -> Vec<&'static str> {
        CognitiveCapitalDimension::ALL
            .iter()
            .map(|dimension| dimension.as_str())
            .collect()
    }

    #[getter]
    fn cognitive_capital_reference(&self) -> Option<(Vec<u8>, Vec<u8>, Vec<u8>, u64, u64)> {
        self.value.cognitive_capital().map(|capital| {
            (
                capital.predecessor_state_receipt().to_vec(),
                capital.successor_state_receipt().to_vec(),
                capital.source_authority().to_vec(),
                capital.organism_tick(),
                capital.cognitive_generation(),
            )
        })
    }

    #[getter]
    fn cognitive_capital_evidence(&self) -> Vec<(String, String, String, usize)> {
        self.value
            .cognitive_capital()
            .map(|capital| {
                capital
                    .evidence()
                    .iter()
                    .map(|entry| {
                        (
                            entry.capability().as_str().to_owned(),
                            entry.dimension().as_str().to_owned(),
                            entry.kind().as_str().to_owned(),
                            entry.occurrence_quantity(),
                        )
                    })
                    .collect()
            })
            .unwrap_or_default()
    }

    #[getter]
    fn python_callback_count(&self) -> u64 {
        0
    }
}

#[pyfunction]
#[pyo3(signature = (
    organism_identity,
    organism_tick,
    legacy_predecessor_receipt=None,
    max_envelope_bytes=67_108_864,
    max_cognitive_bytes=67_108_000
))]
fn create_current_resident_d3(
    organism_identity: String,
    organism_tick: u64,
    legacy_predecessor_receipt: Option<Vec<u8>>,
    max_envelope_bytes: usize,
    max_cognitive_bytes: usize,
) -> PyResult<Vec<u8>> {
    let legacy_predecessor_receipt = legacy_predecessor_receipt
        .map(|value| {
            value
                .try_into()
                .map_err(|_| PyValueError::new_err("legacy predecessor receipt must be 32 bytes"))
        })
        .transpose()?;
    create_native_resident_d3_genesis(
        &organism_identity,
        organism_tick,
        legacy_predecessor_receipt,
        max_envelope_bytes,
        max_cognitive_bytes,
    )
    .map_err(PyValueError::new_err)
}

#[pyfunction]
#[pyo3(signature = (
    current_envelope,
    max_envelope_bytes=67_108_864,
    max_cognitive_bytes=67_108_000
))]
fn observe_current_resident_d3(
    current_envelope: Vec<u8>,
    max_envelope_bytes: usize,
    max_cognitive_bytes: usize,
) -> PyResult<PyResidentD3Observation> {
    let budget = ResidentD3Budget::new(max_envelope_bytes, max_cognitive_bytes)
        .map_err(|error| PyValueError::new_err(error.to_string()))?;
    let runtime = ResidentD3Runtime::restore_structural(current_envelope, budget)
        .map_err(|error| PyValueError::new_err(error.to_string()))?;
    Ok(PyResidentD3Observation {
        value: runtime.observation().clone(),
    })
}

pub(crate) fn register(module: &Bound<'_, PyModule>) -> PyResult<()> {
    module.add_class::<PyResidentD3Observation>()?;
    module.add_function(wrap_pyfunction!(create_current_resident_d3, module)?)?;
    module.add_function(wrap_pyfunction!(observe_current_resident_d3, module)?)?;
    Ok(())
}

#[cfg(test)]
mod tests {
    use std::collections::BTreeMap;

    use super::*;

    /// Quiet (dark, silent) episodes appended after a presentation so the
    /// cohort can descend all the way to electrical rest.  Since the
    /// 2026-08-05 geometric differentiation the members' capacitances differ,
    /// so a settled cohort equalizes POTENTIAL rather than charge and needs a
    /// longer quiet tail to go silent than the tie-frozen anatomy did; the
    /// tail is transport, the quiescence is physics.
    const DARK_TAIL_EPISODES: usize = 64;
    use crate::joint_uf_source_adapter::{admitted_fixture_episode, AdmittedJointSourceEpisode};
    use crate::local_cupula_hair_bundle_geometry::LocalCupulaBundleAnatomy;
    use crate::neuron_source_anchor::tests::{
        exact_four_dark_optical_episode, exact_four_partial_optical_episode,
        exact_four_single_optical_episode, exact_optical_episode,
    };
    use crate::reached_vestibular_bundle_path::settle_reached_vestibular_bundle_tick;
    use crate::resident_cognitive_formation::{
        reset_resident_joint_field_evaluation_count, resident_joint_field_evaluation_count,
    };
    use crate::vestibular_joint_source_builder::admit_same_cause_vestibular_joint_source_interval;
    use crate::virtual_vestibular_canal::{CanalAnatomy, PositiveRatio};

    const IDENTITY: &str = "1cc4e70a-f2a0-44c5-a111-f4a5bc915cc1";

    fn budget() -> ResidentD3Budget {
        ResidentD3Budget::new(16_100_000, 16_000_000).unwrap()
    }

    fn genesis(legacy: Option<[u8; 32]>) -> Vec<u8> {
        create_native_resident_d3_genesis(
            IDENTITY,
            0,
            legacy,
            budget().max_envelope_bytes,
            budget().max_cognitive_bytes,
        )
        .unwrap()
    }

    /// One authored seed group covering every port of the anatomy episode as a
    /// chain of contacts (left = i - 1, right = i) with an authored conductance
    /// of 500 pS, mirroring the formation-level `explicit_optical_seed`.
    fn chain_seed_groups(
        anatomy: &NativeJointSourceEpisode,
        conductance_picosiemens: i64,
    ) -> Vec<(Vec<usize>, Vec<(usize, usize, i64)>)> {
        let port_count = anatomy.joint_source_ports().len();
        let ports = (0..port_count).collect::<Vec<_>>();
        let contacts = (1..port_count)
            .map(|right| (right - 1, right, conductance_picosiemens))
            .collect::<Vec<_>>();
        vec![(ports, contacts)]
    }

    fn seeded_genesis(anatomy: &NativeJointSourceEpisode) -> Vec<u8> {
        create_native_resident_d3_genesis_with_growth_dna(
            IDENTITY,
            0,
            None,
            anatomy,
            chain_seed_groups(anatomy, 500),
            budget().max_envelope_bytes,
            budget().max_cognitive_bytes,
        )
        .unwrap()
    }

    #[test]
    fn genesis_mounts_exact_at_rest_body_and_canal_in_one_envelope() {
        let current = genesis(None);
        let runtime = ResidentD3Runtime::restore(current.clone(), budget()).unwrap();
        assert_eq!(runtime.current_envelope(), current);
        assert_eq!(runtime.yaw_body_state(), YawBodyState::new(0).unwrap());
        assert_eq!(runtime.canal_state(), CanalState::at_rest());
        assert_eq!(runtime.observation().organism_tick(), 0);
        assert_eq!(runtime.observation().fabric_generation(), 0);
    }

    #[test]
    fn exact_current_roundtrip_preserves_body_canal_and_cognition_bytes() {
        let current = genesis(Some([0x35; 32]));
        let parsed = parse_current_state(&current, budget()).unwrap();
        let body = parsed.yaw_body;
        let canal = parsed.canal;
        let cognitive = parsed.cognitive_bytes.to_vec();
        let restored = ResidentD3Runtime::restore(current.clone(), budget()).unwrap();
        assert_eq!(restored.current_envelope(), current);
        assert_eq!(restored.yaw_body_state(), body);
        assert_eq!(restored.canal_state(), canal);
        let reparsed = parse_current_state(restored.current_envelope(), budget()).unwrap();
        assert_eq!(reparsed.cognitive_bytes, cognitive);
    }

    #[test]
    fn resident_embodiment_adds_exactly_thirty_six_bytes() {
        let current = genesis(None);
        let parsed = parse_current_state(&current, budget()).unwrap();
        let cognition_only_equivalent = ENVELOPE_FIXED_BYTES
            + (FABRIC_FIXED_BYTES - EMBODIMENT_STATE_BYTES)
            + parsed.cognitive_bytes.len();
        assert_eq!(YawBodyState::resident_bytes(), YAW_BODY_STATE_BYTES);
        assert_eq!(CanalState::resident_bytes(), CANAL_STATE_BYTES);
        assert_eq!(EMBODIMENT_STATE_BYTES, 36);
        assert_eq!(current.len() - cognition_only_equivalent, 36);
    }

    #[test]
    fn prepare_then_discard_leaves_all_resident_state_unchanged() {
        let source = exact_optical_episode();
        let original = genesis(None);
        let mut runtime = ResidentD3Runtime::restore(original.clone(), budget()).unwrap();
        let body = runtime.yaw_body_state();
        let canal = runtime.canal_state();
        let prepared = runtime
            .prepare_admitted(&admitted_fixture_episode(&source))
            .unwrap();
        let pending = runtime.pending.as_ref().unwrap();
        assert_eq!(pending.yaw_body, body);
        assert_eq!(pending.canal, canal);
        runtime.discard(prepared.token()).unwrap();
        assert_eq!(runtime.current_envelope(), original);
        assert_eq!(runtime.yaw_body_state(), body);
        assert_eq!(runtime.canal_state(), canal);
        assert_eq!(runtime.observation().organism_tick(), 0);
    }

    #[test]
    fn prepare_then_commit_advances_one_atomic_body_canal_cognition_successor() {
        let source = exact_optical_episode();
        let mut runtime = ResidentD3Runtime::restore(genesis(None), budget()).unwrap();
        let body = runtime.yaw_body_state();
        let canal = runtime.canal_state();
        let prepared = runtime
            .prepare_admitted(&admitted_fixture_episode(&source))
            .unwrap();
        let pending_envelope = runtime.pending.as_ref().unwrap().envelope.clone();
        runtime.commit(prepared.token()).unwrap();
        assert_eq!(runtime.current_envelope(), pending_envelope);
        assert_eq!(runtime.yaw_body_state(), body);
        assert_eq!(runtime.canal_state(), canal);
        assert_eq!(runtime.observation().organism_tick(), 1);
        assert_eq!(runtime.observation().fabric_generation(), 1);
        let restored = ResidentD3Runtime::restore(pending_envelope, budget()).unwrap();
        assert_eq!(restored.yaw_body_state(), body);
        assert_eq!(restored.canal_state(), canal);
        assert_eq!(restored.observation().organism_tick(), 1);
    }

    #[test]
    fn admitted_environment_source_advances_one_atomic_runtime_successor() {
        let predecessor_body = YawBodyState::new(0).unwrap();
        let successor_body = YawBodyState::new(1).unwrap();
        let reached = settle_reached_vestibular_bundle_tick(
            CanalAnatomy::new(6, 13_200, PositiveRatio::new(25, 1).unwrap()).unwrap(),
            CanalState::at_rest(),
            1,
            LocalCupulaBundleAnatomy::new(2, 5, 20_000).unwrap(),
        )
        .unwrap();
        let physical_source = admit_same_cause_vestibular_joint_source_interval(
            0,
            predecessor_body,
            successor_body,
            reached,
        )
        .unwrap();
        let source_admission = physical_source.joint_uf_source_admission().unwrap();
        let source = physical_source.joint_source_with_contacts().0.clone();
        let source_authority = source.joint_source_authority_receipt();
        let admitted =
            AdmittedJointSourceEpisode::new(source, vec![(0, source_admission)]).unwrap();

        let mut runtime = ResidentD3Runtime::restore(genesis(None), budget()).unwrap();
        reset_resident_joint_field_evaluation_count();
        let prepared = runtime.prepare_admitted(&admitted).unwrap();
        runtime.commit(prepared.token()).unwrap();

        assert_eq!(resident_joint_field_evaluation_count(), 1);
        assert_eq!(runtime.observation().organism_tick(), 1);
        assert_eq!(runtime.observation().fabric_generation(), 1);
        assert_eq!(
            runtime.observation().source_authority(),
            Some(source_authority)
        );
        assert_eq!(runtime.observation().dsf_delivery_count(), 1);
        assert_eq!(runtime.observation().complete_neuron_count(), 0);
    }

    /// REPLACES `cold_publish_failure_retains_the_same_pending_successor_for_exact_retry`.
    ///
    /// That test proved the retired law: a reassembly staged objects into an
    /// external archive, an injected publication failure held the pending
    /// successor for retry, and — the assertion that mattered most — a body
    /// written by a reassembly REFUSED TO RESTORE against an empty archive.
    /// That last property is precisely what made Guala hostage to a directory
    /// of 230,396 files.  The law is now the opposite and it is pinned here:
    /// a reassembly cannot fail on custody because it touches no custody, and
    /// the body it produces restores on its own bytes alone.
    #[test]
    #[ignore = "retired: fixture requires Boolean/member-set mosaic admission"]
    fn a_reassembled_body_restores_with_no_archive_of_any_kind() {
        let anatomy = exact_four_single_optical_episode(0);
        let mut runtime = ResidentD3Runtime::restore(seeded_genesis(&anatomy), budget()).unwrap();
        let dark = exact_four_dark_optical_episode();

        for receptor in 0..4 {
            let source = exact_four_single_optical_episode(receptor);
            let prepared = runtime
                .prepare_admitted(&admitted_fixture_episode(&source))
                .unwrap();
            runtime.commit(prepared.token()).unwrap();
        }
        for _ in 0..DARK_TAIL_EPISODES {
            let prepared = runtime
                .prepare_admitted(&admitted_fixture_episode(&dark))
                .unwrap();
            runtime.commit(prepared.token()).unwrap();
        }

        let partial = exact_four_partial_optical_episode();
        let mut reassembled = false;
        for source in std::iter::once(&partial)
            .chain(std::iter::repeat(&dark).take(DARK_TAIL_EPISODES))
        {
            let prepared = runtime
                .prepare_admitted(&admitted_fixture_episode(source))
                .unwrap();
            reassembled |= prepared.observation().partial_cue_reassembly_count() > 0;
            runtime.commit(prepared.token()).unwrap();
            if reassembled {
                break;
            }
        }
        assert!(
            reassembled,
            "the deterministic recurrence did not reassemble, so this proves nothing"
        );

        // The body that a REASSEMBLY produced restores with nothing but
        // itself, and keeps learning from there.
        let after_reassembly = runtime.current_envelope().to_vec();
        let mut restored = ResidentD3Runtime::restore(after_reassembly.clone(), budget()).unwrap();
        assert_eq!(restored.current_envelope(), after_reassembly);
        let prepared = restored
            .prepare_admitted(&admitted_fixture_episode(&dark))
            .unwrap();
        restored.commit(prepared.token()).unwrap();
        assert_eq!(restored.observation().organism_tick(), runtime.observation().organism_tick() + 1);
    }

    #[test]
    fn seeded_genesis_envelope_cold_restores_unexpressed_growth_dna_exactly() {
        let anatomy = exact_four_dark_optical_episode();
        let current = seeded_genesis(&anatomy);
        let expected = ResidentCognitiveFormationState::from_developmental_electrical_seeds(
            build_authored_growth_dna_seeds(&anatomy, &chain_seed_groups(&anatomy, 500)).unwrap(),
        )
        .unwrap();
        let runtime = ResidentD3Runtime::restore(current.clone(), budget()).unwrap();
        assert_eq!(runtime.active.cognitive, expected);

        let parsed = parse_current_state(&current, budget()).unwrap();
        let decoded = ResidentCognitiveFormationState::decode(
            parsed.cognitive_bytes,
            budget().max_cognitive_bytes,
        )
        .unwrap();
        assert_eq!(decoded, expected);
        assert_eq!(
            decoded.encode(budget().max_cognitive_bytes).unwrap(),
            parsed.cognitive_bytes
        );

        assert_eq!(runtime.observation().organism_tick(), 0);
        assert_eq!(runtime.observation().cognitive_generation(), 0);
        assert_eq!(runtime.observation().complete_neuron_count(), 0);
        assert_eq!(runtime.observation().cognitive_mosaic_count(), 0);
    }

    #[test]
    #[ignore = "retired: fixture requires Boolean/member-set mosaic admission"]
    fn seeded_genesis_grows_expressed_contacts_and_admits_a_real_mosaic() {
        let anatomy = exact_four_single_optical_episode(0);
        let mut runtime =
            ResidentD3Runtime::restore(seeded_genesis(&anatomy), budget()).unwrap();
        let dark = exact_four_dark_optical_episode();

        for receptor in 0..4 {
            let source = exact_four_single_optical_episode(receptor);
            let prepared = runtime
                .prepare_admitted(&admitted_fixture_episode(&source))
                .unwrap();
            if receptor == 0 {
                assert_eq!(prepared.observation().complete_neuron_count(), 4);
            }
            runtime.commit(prepared.token()).unwrap();
        }
        for _ in 0..DARK_TAIL_EPISODES {
            let prepared = runtime
                .prepare_admitted(&admitted_fixture_episode(&dark))
                .unwrap();
            runtime.commit(prepared.token()).unwrap();
        }
        assert_eq!(runtime.observation().cognitive_mosaic_count(), 0);

        let partial = exact_four_partial_optical_episode();
        let mut admitted_mosaic = false;
        for source in std::iter::once(&partial).chain(std::iter::repeat(&dark).take(DARK_TAIL_EPISODES)) {
            let prepared = runtime
                .prepare_admitted(&admitted_fixture_episode(source))
                .unwrap();
            runtime.commit(prepared.token()).unwrap();
            if runtime.observation().cognitive_mosaic_count() == 1 {
                admitted_mosaic = true;
                break;
            }
        }
        assert!(
            admitted_mosaic,
            "the authored growth DNA did not lead to an admitted mosaic"
        );

        let envelope = runtime.current_envelope().to_vec();
        let restored = ResidentD3Runtime::restore(envelope.clone(), budget()).unwrap();
        assert_eq!(restored.observation().cognitive_mosaic_count(), 1);
        assert_eq!(restored.observation().complete_neuron_count(), 4);
        let parsed = parse_current_state(&envelope, budget()).unwrap();
        let decoded = ResidentCognitiveFormationState::decode(
            parsed.cognitive_bytes,
            budget().max_cognitive_bytes,
        )
        .unwrap();
        assert_eq!(decoded.summary().mosaic_count, 1);
    }

    #[test]
    fn production_surface_uses_one_field_evaluation_and_stable_lineage_after_restart() {
        let source = exact_optical_episode();
        reset_resident_joint_field_evaluation_count();
        let first = transition_native_resident_d3_admitted(
            genesis(None),
            &admitted_fixture_episode(&source),
            budget().max_envelope_bytes,
            budget().max_cognitive_bytes,
        )
        .unwrap();
        assert_eq!(
            resident_joint_field_evaluation_count(),
            source.joint_source_occurrences().len()
        );
        let capital = first.observation().cognitive_capital().unwrap();
        assert_eq!(
            capital.successor_state_receipt(),
            first.observation().state_receipt()
        );
        assert!(capital
            .evidence_for(
                CognitiveCapability::Vision,
                CognitiveCapitalDimension::Availability,
            )
            .next()
            .is_some());
        assert!(capital
            .evidence_for(
                CognitiveCapability::AutonomousCognitionAndAction,
                CognitiveCapitalDimension::AutonomousUse,
            )
            .next()
            .is_none());
        let restored =
            ResidentD3Runtime::restore(first.successor.clone(), budget()).unwrap();
        let first_lineages = restored.active.cognitive.retained_neuron_lineages();
        assert_eq!(first_lineages.len(), 2);
        let second = transition_native_resident_d3_admitted(
            first.successor,
            &admitted_fixture_episode(&source),
            budget().max_envelope_bytes,
            budget().max_cognitive_bytes,
        )
        .unwrap();
        let restarted = ResidentD3Runtime::restore(second.successor, budget()).unwrap();
        assert_eq!(
            restarted.active.cognitive.retained_neuron_lineages(),
            first_lineages
        );
        assert_eq!(restarted.observation().python_callback_count(), 0);
    }

    #[test]
    fn current_successor_contains_no_legacy_state_body_and_preserves_only_fixed_receipt() {
        let legacy_receipt = [0x5a; 32];
        let source = exact_optical_episode();
        let transitioned = transition_native_resident_d3_admitted(
            genesis(Some(legacy_receipt)),
            &admitted_fixture_episode(&source),
            budget().max_envelope_bytes,
            budget().max_cognitive_bytes,
        )
        .unwrap();
        for retired in [
            b"GLJDSF03".as_slice(),
            b"GLMFAB07".as_slice(),
            b"GLMFAB04".as_slice(),
        ] {
            assert!(!transitioned
                .successor()
                .windows(retired.len())
                .any(|window| window == retired));
        }
        assert_eq!(
            transitioned.observation().legacy_predecessor_receipt(),
            Some(legacy_receipt)
        );
    }

    /// REPLACES `missing_cold_port_refuses_without_state_change`.  The bare
    /// source path is still severed, and now for its real reason: the
    /// mandatory-admission law, not a missing archive port.
    #[test]
    fn bare_unadmitted_source_refuses_without_state_change() {
        let source = exact_optical_episode();
        let original = genesis(None);
        let mut runtime = ResidentD3Runtime::restore(original.clone(), budget()).unwrap();
        assert!(matches!(
            runtime.prepare(&source).unwrap_err(),
            ResidentD3Error::Cognitive(_)
        ));
        assert_eq!(runtime.current_envelope(), original);
        assert_eq!(runtime.observation().organism_tick(), 0);
    }

    #[test]
    fn current_restore_is_exact_bounded_and_rejects_every_legacy_version() {
        let current = genesis(None);
        let exact_budget = ResidentD3Budget::new(
            current.len(),
            current.len() - ENVELOPE_FIXED_BYTES - FABRIC_FIXED_BYTES,
        )
        .unwrap();
        let restored = ResidentD3Runtime::restore(current.clone(), exact_budget).unwrap();
        assert_eq!(restored.current_envelope(), current);
        assert_eq!(
            ResidentD3Budget::new(
                current.len() - 1,
                current.len() - ENVELOPE_FIXED_BYTES - FABRIC_FIXED_BYTES,
            )
            .unwrap_err(),
            ResidentD3Error::InvalidBudget
        );
        let mut legacy_version = current;
        legacy_version[ENVELOPE_MAGIC.len()..ENVELOPE_MAGIC.len() + 2]
            .copy_from_slice(&(ENVELOPE_VERSION - 1).to_le_bytes());
        assert_eq!(
            ResidentD3Runtime::restore(legacy_version, exact_budget).unwrap_err(),
            ResidentD3Error::BadEnvelopeVersion(ENVELOPE_VERSION - 1)
        );

        let mut legacy_fabric = genesis(None);
        let fabric_version_start = ENVELOPE_FIXED_BYTES + FABRIC_MAGIC.len();
        legacy_fabric[fabric_version_start..fabric_version_start + 2]
            .copy_from_slice(&(FABRIC_VERSION - 1).to_le_bytes());
        assert_eq!(
            ResidentD3Runtime::restore(legacy_fabric, budget()).unwrap_err(),
            ResidentD3Error::BadFabricVersion(FABRIC_VERSION - 1)
        );
    }
}
