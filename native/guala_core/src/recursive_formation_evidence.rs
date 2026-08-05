//! Isolated evidence boundary for recursive formation claims.
//!
//! This module does not create cognition, own persistence, infer meaning, or
//! register a runtime.  It only rejects formation claims that are not backed
//! by content-addressed decoded bodies and conserved physical transitions.

use sha2::{Digest, Sha256};
use std::collections::{BTreeMap, BTreeSet, VecDeque};
use std::fmt;

pub(crate) type Receipt = [u8; 32];
pub(crate) type Lineage = [u8; 16];

const RECEIPT_BYTES: usize = 32;

fn digest(bytes: &[u8]) -> Receipt {
    Sha256::digest(bytes).into()
}

fn put_tag(out: &mut Vec<u8>, tag: u8) {
    out.push(tag);
}

fn put_u64(out: &mut Vec<u8>, value: u64) {
    out.extend_from_slice(&value.to_be_bytes());
}

fn put_u128(out: &mut Vec<u8>, value: u128) {
    out.extend_from_slice(&value.to_be_bytes());
}

fn put_lineage(out: &mut Vec<u8>, value: Lineage) {
    out.extend_from_slice(&value);
}

fn put_receipt(out: &mut Vec<u8>, value: Receipt) {
    out.extend_from_slice(&value);
}

fn put_len(out: &mut Vec<u8>, value: usize) {
    put_u64(out, u64::try_from(value).unwrap_or(u64::MAX));
}

fn put_receipts(out: &mut Vec<u8>, values: impl IntoIterator<Item = Receipt>) {
    let values = values.into_iter().collect::<Vec<_>>();
    put_len(out, values.len());
    for value in values {
        put_receipt(out, value);
    }
}

pub(crate) trait CanonicalEvidenceBody {
    fn canonical_bytes(&self) -> Vec<u8>;
    fn authority_receipt(&self) -> Receipt;

    fn canonical_len(&self) -> usize {
        self.canonical_bytes().len()
    }

    fn has_valid_authority(&self) -> bool {
        digest(&self.canonical_bytes()) == self.authority_receipt()
    }
}

macro_rules! evidence_ref {
    ($name:ident) => {
        #[derive(Clone, Copy, Debug, Eq, Ord, PartialEq, PartialOrd)]
        pub(crate) struct $name(Receipt);

        impl $name {
            pub(crate) fn receipt(self) -> Receipt {
                self.0
            }
        }
    };
}

evidence_ref!(FractalRef);
evidence_ref!(TransitionRef);
evidence_ref!(RecurrenceRef);
evidence_ref!(PartialCueRef);
evidence_ref!(DurabilityRef);
evidence_ref!(FormationRef);
evidence_ref!(RelationRef);
evidence_ref!(ConsequenceRef);
evidence_ref!(EpisodeContextRef);

impl RecurrenceRef {
    pub(crate) fn from_receipt(receipt: Receipt) -> Self {
        Self(receipt)
    }
}

impl RelationRef {
    pub(crate) fn from_receipt(receipt: Receipt) -> Self {
        Self(receipt)
    }
}

impl FormationRef {
    pub(crate) fn from_receipt(receipt: Receipt) -> Self {
        Self(receipt)
    }
}

#[derive(Clone, Copy, Debug, Eq, Ord, PartialEq, PartialOrd)]
pub(crate) enum FormationKind {
    Mosaic,
    MosaicOfMosaics,
    Tapestry,
    TapestryOfTapestries,
    Weave,
}

impl FormationKind {
    fn tag(self) -> u8 {
        match self {
            Self::Mosaic => 1,
            Self::MosaicOfMosaics => 2,
            Self::Tapestry => 3,
            Self::TapestryOfTapestries => 4,
            Self::Weave => 5,
        }
    }
}

#[derive(Clone, Copy, Debug, Eq, Ord, PartialEq, PartialOrd)]
pub(crate) enum RelationKind {
    LearnedRelation,
    OrderedContinuation,
    GenerativeIntegration,
}

impl RelationKind {
    fn tag(self) -> u8 {
        match self {
            Self::LearnedRelation => 1,
            Self::OrderedContinuation => 2,
            Self::GenerativeIntegration => 3,
        }
    }
}

#[derive(Clone, Copy, Debug, Eq, Ord, PartialEq, PartialOrd)]
pub(crate) enum Provenance {
    Observed,
    SelfSensed,
    Reassembled,
    Endogenous,
}

#[derive(Clone, Copy, Debug, Eq, Ord, PartialEq, PartialOrd)]
pub(crate) enum FluidEpisodeStatus {
    Perturbed,
    Quiescent { quiescence_authority: Receipt },
    Unavailable { unavailability_authority: Receipt },
}

impl FluidEpisodeStatus {
    fn encode(self, out: &mut Vec<u8>) {
        match self {
            Self::Perturbed => put_tag(out, 1),
            Self::Quiescent {
                quiescence_authority,
            } => {
                put_tag(out, 2);
                put_receipt(out, quiescence_authority);
            }
            Self::Unavailable {
                unavailability_authority,
            } => {
                put_tag(out, 3);
                put_receipt(out, unavailability_authority);
            }
        }
    }
}

impl Provenance {
    fn tag(self) -> u8 {
        match self {
            Self::Observed => 1,
            Self::SelfSensed => 2,
            Self::Reassembled => 3,
            Self::Endogenous => 4,
        }
    }
}

#[derive(Clone, Copy, Debug, Eq, Ord, PartialEq, PartialOrd)]
pub(crate) enum PhysicalQuantityKind {
    Charge,
    Energy,
    Material,
}

impl PhysicalQuantityKind {
    fn tag(self) -> u8 {
        match self {
            Self::Charge => 1,
            Self::Energy => 2,
            Self::Material => 3,
        }
    }
}

#[derive(Clone, Copy, Debug, Eq, Ord, PartialEq, PartialOrd)]
pub(crate) enum ConfigurationRole {
    Body,
    Motor,
    Sensory,
}

impl ConfigurationRole {
    fn tag(self) -> u8 {
        match self {
            Self::Body => 1,
            Self::Motor => 2,
            Self::Sensory => 3,
        }
    }
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) struct FractalBody {
    lineage: Lineage,
    generation: u64,
    fractal_state_receipt: Receipt,
    perspective_receipt: Receipt,
    complete_field_receipt: Receipt,
    successful_local_transition_authority: Receipt,
    physical_authorities: ParticipantPhysicalAuthorities,
    authority: Receipt,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) struct ParticipantPhysicalAuthorities {
    pub(crate) source: Receipt,
    pub(crate) receptor: Receipt,
    pub(crate) anatomy: Receipt,
    pub(crate) membrane_transition: Receipt,
    pub(crate) channel_transition: Receipt,
    pub(crate) fluid_transition: Receipt,
}

impl ParticipantPhysicalAuthorities {
    fn is_complete(self) -> bool {
        [
            self.source,
            self.receptor,
            self.anatomy,
            self.membrane_transition,
            self.channel_transition,
            self.fluid_transition,
        ]
        .iter()
        .all(|value| *value != [0; 32])
    }

    fn encode(self, out: &mut Vec<u8>) {
        put_receipt(out, self.source);
        put_receipt(out, self.receptor);
        put_receipt(out, self.anatomy);
        put_receipt(out, self.membrane_transition);
        put_receipt(out, self.channel_transition);
        put_receipt(out, self.fluid_transition);
    }
}

impl FractalBody {
    pub(crate) fn new(
        lineage: Lineage,
        generation: u64,
        fractal_state_receipt: Receipt,
        perspective_receipt: Receipt,
        complete_field_receipt: Receipt,
        successful_local_transition_authority: Receipt,
        physical_authorities: ParticipantPhysicalAuthorities,
    ) -> Self {
        let mut body = Self {
            lineage,
            generation,
            fractal_state_receipt,
            perspective_receipt,
            complete_field_receipt,
            successful_local_transition_authority,
            physical_authorities,
            authority: [0; 32],
        };
        body.authority = digest(&body.canonical_bytes());
        body
    }

    pub(crate) fn reference(&self) -> FractalRef {
        FractalRef(self.authority)
    }

    pub(crate) fn lineage(&self) -> Lineage {
        self.lineage
    }

    pub(crate) fn generation(&self) -> u64 {
        self.generation
    }

    pub(crate) fn perspective_receipt(&self) -> Receipt {
        self.perspective_receipt
    }

    pub(crate) fn successful_local_transition_authority(&self) -> Receipt {
        self.successful_local_transition_authority
    }

    pub(crate) fn physical_authorities(&self) -> ParticipantPhysicalAuthorities {
        self.physical_authorities
    }

    pub(crate) fn complete_field_receipt(&self) -> Receipt {
        self.complete_field_receipt
    }
}

impl CanonicalEvidenceBody for FractalBody {
    fn canonical_bytes(&self) -> Vec<u8> {
        let mut out = Vec::new();
        put_tag(&mut out, 1);
        put_lineage(&mut out, self.lineage);
        put_u64(&mut out, self.generation);
        put_receipt(&mut out, self.fractal_state_receipt);
        put_receipt(&mut out, self.perspective_receipt);
        put_receipt(&mut out, self.complete_field_receipt);
        put_receipt(&mut out, self.successful_local_transition_authority);
        self.physical_authorities.encode(&mut out);
        out
    }

    fn authority_receipt(&self) -> Receipt {
        self.authority
    }
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) struct EpisodeMemberParticipation {
    lineage: Lineage,
    fractal: FractalRef,
    successful_local_transition_authority: Receipt,
    causal_occurrence_authority: Receipt,
    physical_authorities: ParticipantPhysicalAuthorities,
}

impl EpisodeMemberParticipation {
    pub(crate) fn new(
        lineage: Lineage,
        fractal: FractalRef,
        successful_local_transition_authority: Receipt,
        causal_occurrence_authority: Receipt,
        physical_authorities: ParticipantPhysicalAuthorities,
    ) -> Self {
        Self {
            lineage,
            fractal,
            successful_local_transition_authority,
            causal_occurrence_authority,
            physical_authorities,
        }
    }

    pub(crate) fn lineage(&self) -> Lineage {
        self.lineage
    }

    pub(crate) fn fractal(&self) -> FractalRef {
        self.fractal
    }

    pub(crate) fn successful_local_transition_authority(&self) -> Receipt {
        self.successful_local_transition_authority
    }

    pub(crate) fn physical_authorities(&self) -> ParticipantPhysicalAuthorities {
        self.physical_authorities
    }
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) struct ResolvedEpisodeContextBody {
    episode_height: u64,
    causal_occurrence_authority: Receipt,
    body_predecessor_authority: Receipt,
    body_successor_authority: Receipt,
    fluid_predecessor_authority: Receipt,
    fluid_successor_authority: Receipt,
    fluid_status: FluidEpisodeStatus,
    participants: Vec<EpisodeMemberParticipation>,
    provenance: Provenance,
    authority: Receipt,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) struct ResolvedEpisodeContextParts {
    pub(crate) episode_height: u64,
    pub(crate) causal_occurrence_authority: Receipt,
    pub(crate) body_predecessor_authority: Receipt,
    pub(crate) body_successor_authority: Receipt,
    pub(crate) fluid_predecessor_authority: Receipt,
    pub(crate) fluid_successor_authority: Receipt,
    pub(crate) fluid_status: FluidEpisodeStatus,
    pub(crate) participants: Vec<EpisodeMemberParticipation>,
    pub(crate) provenance: Provenance,
}

impl ResolvedEpisodeContextBody {
    pub(crate) fn new(parts: ResolvedEpisodeContextParts) -> Self {
        let mut body = Self {
            episode_height: parts.episode_height,
            causal_occurrence_authority: parts.causal_occurrence_authority,
            body_predecessor_authority: parts.body_predecessor_authority,
            body_successor_authority: parts.body_successor_authority,
            fluid_predecessor_authority: parts.fluid_predecessor_authority,
            fluid_successor_authority: parts.fluid_successor_authority,
            fluid_status: parts.fluid_status,
            participants: parts.participants,
            provenance: parts.provenance,
            authority: [0; 32],
        };
        body.authority = digest(&body.canonical_bytes());
        body
    }

    pub(crate) fn reference(&self) -> EpisodeContextRef {
        EpisodeContextRef(self.authority)
    }

    pub(crate) fn episode_height(&self) -> u64 {
        self.episode_height
    }

    pub(crate) fn causal_occurrence_authority(&self) -> Receipt {
        self.causal_occurrence_authority
    }

    pub(crate) fn participants(&self) -> &[EpisodeMemberParticipation] {
        &self.participants
    }
}

impl CanonicalEvidenceBody for ResolvedEpisodeContextBody {
    fn canonical_bytes(&self) -> Vec<u8> {
        let mut out = Vec::new();
        put_tag(&mut out, 10);
        put_u64(&mut out, self.episode_height);
        put_receipt(&mut out, self.causal_occurrence_authority);
        put_receipt(&mut out, self.body_predecessor_authority);
        put_receipt(&mut out, self.body_successor_authority);
        put_receipt(&mut out, self.fluid_predecessor_authority);
        put_receipt(&mut out, self.fluid_successor_authority);
        self.fluid_status.encode(&mut out);
        put_len(&mut out, self.participants.len());
        for participant in &self.participants {
            put_lineage(&mut out, participant.lineage);
            put_receipt(&mut out, participant.fractal.receipt());
            put_receipt(&mut out, participant.successful_local_transition_authority);
            put_receipt(&mut out, participant.causal_occurrence_authority);
            participant.physical_authorities.encode(&mut out);
        }
        put_tag(&mut out, self.provenance.tag());
        out
    }

    fn authority_receipt(&self) -> Receipt {
        self.authority
    }
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) struct TransitionBody {
    source: Lineage,
    target: Lineage,
    predecessor_generation: u64,
    successor_generation: u64,
    quantity_kind: PhysicalQuantityKind,
    unit_receipt: Receipt,
    quantum_numerator: u128,
    quantum_denominator: u128,
    transferred_quanta: u128,
    source_debit_quanta: u128,
    target_credit_quanta: u128,
    predecessor_state_receipt: Receipt,
    successor_state_receipt: Receipt,
    authority: Receipt,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) struct ConservedQuantity {
    pub(crate) kind: PhysicalQuantityKind,
    pub(crate) unit_receipt: Receipt,
    pub(crate) quantum_numerator: u128,
    pub(crate) quantum_denominator: u128,
    pub(crate) transferred_quanta: u128,
    pub(crate) source_debit_quanta: u128,
    pub(crate) target_credit_quanta: u128,
}

impl TransitionBody {
    pub(crate) fn new(
        source: Lineage,
        target: Lineage,
        predecessor_generation: u64,
        successor_generation: u64,
        quantity: ConservedQuantity,
        predecessor_state_receipt: Receipt,
        successor_state_receipt: Receipt,
    ) -> Self {
        let mut body = Self {
            source,
            target,
            predecessor_generation,
            successor_generation,
            quantity_kind: quantity.kind,
            unit_receipt: quantity.unit_receipt,
            quantum_numerator: quantity.quantum_numerator,
            quantum_denominator: quantity.quantum_denominator,
            transferred_quanta: quantity.transferred_quanta,
            source_debit_quanta: quantity.source_debit_quanta,
            target_credit_quanta: quantity.target_credit_quanta,
            predecessor_state_receipt,
            successor_state_receipt,
            authority: [0; 32],
        };
        body.authority = digest(&body.canonical_bytes());
        body
    }

    pub(crate) fn reference(&self) -> TransitionRef {
        TransitionRef(self.authority)
    }

    pub(crate) fn source(&self) -> Lineage {
        self.source
    }

    pub(crate) fn target(&self) -> Lineage {
        self.target
    }

    pub(crate) fn successor_generation(&self) -> u64 {
        self.successor_generation
    }

    pub(crate) fn predecessor_generation(&self) -> u64 {
        self.predecessor_generation
    }

    pub(crate) fn physical_facts(&self) -> PhysicalTransitionFacts {
        PhysicalTransitionFacts {
            source: self.source,
            target: self.target,
            predecessor_generation: self.predecessor_generation,
            successor_generation: self.successor_generation,
            quantity_kind: self.quantity_kind,
            unit_receipt: self.unit_receipt,
            quantum_numerator: self.quantum_numerator,
            quantum_denominator: self.quantum_denominator,
            transferred_quanta: self.transferred_quanta,
            source_debit_quanta: self.source_debit_quanta,
            target_credit_quanta: self.target_credit_quanta,
            predecessor_state_receipt: self.predecessor_state_receipt,
            successor_state_receipt: self.successor_state_receipt,
        }
    }

    fn is_resolved_physical_change(&self) -> bool {
        self.source != self.target
            && self.predecessor_generation.checked_add(1) == Some(self.successor_generation)
            && self.quantum_numerator > 0
            && self.quantum_denominator > 0
            && self.unit_receipt != [0; 32]
            && self.transferred_quanta > 0
            && self.source_debit_quanta == self.transferred_quanta
            && self.target_credit_quanta == self.transferred_quanta
            && self.predecessor_state_receipt != self.successor_state_receipt
    }
}

#[derive(Clone, Copy, Debug, Eq, Ord, PartialEq, PartialOrd)]
pub(crate) struct PhysicalTransitionFacts {
    pub(crate) source: Lineage,
    pub(crate) target: Lineage,
    pub(crate) predecessor_generation: u64,
    pub(crate) successor_generation: u64,
    pub(crate) quantity_kind: PhysicalQuantityKind,
    pub(crate) unit_receipt: Receipt,
    pub(crate) quantum_numerator: u128,
    pub(crate) quantum_denominator: u128,
    pub(crate) transferred_quanta: u128,
    pub(crate) source_debit_quanta: u128,
    pub(crate) target_credit_quanta: u128,
    pub(crate) predecessor_state_receipt: Receipt,
    pub(crate) successor_state_receipt: Receipt,
}

impl CanonicalEvidenceBody for TransitionBody {
    fn canonical_bytes(&self) -> Vec<u8> {
        let mut out = Vec::new();
        put_tag(&mut out, 2);
        put_lineage(&mut out, self.source);
        put_lineage(&mut out, self.target);
        put_u64(&mut out, self.predecessor_generation);
        put_u64(&mut out, self.successor_generation);
        put_tag(&mut out, self.quantity_kind.tag());
        put_receipt(&mut out, self.unit_receipt);
        put_u128(&mut out, self.quantum_numerator);
        put_u128(&mut out, self.quantum_denominator);
        put_u128(&mut out, self.transferred_quanta);
        put_u128(&mut out, self.source_debit_quanta);
        put_u128(&mut out, self.target_credit_quanta);
        put_receipt(&mut out, self.predecessor_state_receipt);
        put_receipt(&mut out, self.successor_state_receipt);
        out
    }

    fn authority_receipt(&self) -> Receipt {
        self.authority
    }
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) struct RecurrenceBody {
    formation_core_receipt: Receipt,
    event_generation: u64,
    transitions: Vec<TransitionRef>,
    authority: Receipt,
}

impl RecurrenceBody {
    pub(crate) fn new(
        formation_core_receipt: Receipt,
        event_generation: u64,
        transitions: Vec<TransitionRef>,
    ) -> Self {
        let mut body = Self {
            formation_core_receipt,
            event_generation,
            transitions,
            authority: [0; 32],
        };
        body.authority = digest(&body.canonical_bytes());
        body
    }

    pub(crate) fn transitions(&self) -> &[TransitionRef] {
        &self.transitions
    }

    pub(crate) fn event_generation(&self) -> u64 {
        self.event_generation
    }

    pub(crate) fn reference(&self) -> RecurrenceRef {
        RecurrenceRef(self.authority)
    }
}

impl CanonicalEvidenceBody for RecurrenceBody {
    fn canonical_bytes(&self) -> Vec<u8> {
        let mut out = Vec::new();
        put_tag(&mut out, 3);
        put_receipt(&mut out, self.formation_core_receipt);
        put_u64(&mut out, self.event_generation);
        put_receipts(
            &mut out,
            self.transitions.iter().map(|value| value.receipt()),
        );
        out
    }

    fn authority_receipt(&self) -> Receipt {
        self.authority
    }
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) struct PartialCueBody {
    formation_core_receipt: Receipt,
    event_generation: u64,
    provenance: Provenance,
    directly_cued: Vec<Lineage>,
    uncued_changed: Vec<Lineage>,
    transitions: Vec<TransitionRef>,
    authority: Receipt,
}

impl PartialCueBody {
    pub(crate) fn new(
        formation_core_receipt: Receipt,
        event_generation: u64,
        provenance: Provenance,
        directly_cued: Vec<Lineage>,
        uncued_changed: Vec<Lineage>,
        transitions: Vec<TransitionRef>,
    ) -> Self {
        let mut body = Self {
            formation_core_receipt,
            event_generation,
            provenance,
            directly_cued,
            uncued_changed,
            transitions,
            authority: [0; 32],
        };
        body.authority = digest(&body.canonical_bytes());
        body
    }

    pub(crate) fn reference(&self) -> PartialCueRef {
        PartialCueRef(self.authority)
    }
}

impl CanonicalEvidenceBody for PartialCueBody {
    fn canonical_bytes(&self) -> Vec<u8> {
        let mut out = Vec::new();
        put_tag(&mut out, 4);
        put_receipt(&mut out, self.formation_core_receipt);
        put_u64(&mut out, self.event_generation);
        put_tag(&mut out, self.provenance.tag());
        put_len(&mut out, self.directly_cued.len());
        for value in &self.directly_cued {
            put_lineage(&mut out, *value);
        }
        put_len(&mut out, self.uncued_changed.len());
        for value in &self.uncued_changed {
            put_lineage(&mut out, *value);
        }
        put_receipts(
            &mut out,
            self.transitions.iter().map(|value| value.receipt()),
        );
        out
    }

    fn authority_receipt(&self) -> Receipt {
        self.authority
    }
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) struct DurabilityBody {
    formation_core_receipt: Receipt,
    persisted_core_receipt: Receipt,
    reloaded_core_receipt: Receipt,
    persisted_generation: u64,
    restarted_generation: u64,
    reuse_generation: u64,
    reuse_transitions: Vec<TransitionRef>,
    authority: Receipt,
}

impl DurabilityBody {
    pub(crate) fn new(
        formation_core_receipt: Receipt,
        persisted_core_receipt: Receipt,
        reloaded_core_receipt: Receipt,
        persisted_generation: u64,
        restarted_generation: u64,
        reuse_generation: u64,
        reuse_transitions: Vec<TransitionRef>,
    ) -> Self {
        let mut body = Self {
            formation_core_receipt,
            persisted_core_receipt,
            reloaded_core_receipt,
            persisted_generation,
            restarted_generation,
            reuse_generation,
            reuse_transitions,
            authority: [0; 32],
        };
        body.authority = digest(&body.canonical_bytes());
        body
    }

    pub(crate) fn reference(&self) -> DurabilityRef {
        DurabilityRef(self.authority)
    }
}

impl CanonicalEvidenceBody for DurabilityBody {
    fn canonical_bytes(&self) -> Vec<u8> {
        let mut out = Vec::new();
        put_tag(&mut out, 5);
        put_receipt(&mut out, self.formation_core_receipt);
        put_receipt(&mut out, self.persisted_core_receipt);
        put_receipt(&mut out, self.reloaded_core_receipt);
        put_u64(&mut out, self.persisted_generation);
        put_u64(&mut out, self.restarted_generation);
        put_u64(&mut out, self.reuse_generation);
        put_receipts(
            &mut out,
            self.reuse_transitions.iter().map(|value| value.receipt()),
        );
        out
    }

    fn authority_receipt(&self) -> Receipt {
        self.authority
    }
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) struct RelationBody {
    source: FormationRef,
    target: FormationRef,
    kind: RelationKind,
    event_generation: u64,
    supporting_transitions: Vec<TransitionRef>,
    authority: Receipt,
}

impl RelationBody {
    pub(crate) fn new(
        source: FormationRef,
        target: FormationRef,
        kind: RelationKind,
        event_generation: u64,
        supporting_transitions: Vec<TransitionRef>,
    ) -> Self {
        let mut body = Self {
            source,
            target,
            kind,
            event_generation,
            supporting_transitions,
            authority: [0; 32],
        };
        body.authority = digest(&body.canonical_bytes());
        body
    }

    pub(crate) fn reference(&self) -> RelationRef {
        RelationRef(self.authority)
    }

    pub(crate) fn source_formation(&self) -> FormationRef {
        self.source
    }

    pub(crate) fn target_formation(&self) -> FormationRef {
        self.target
    }

    pub(crate) fn kind(&self) -> RelationKind {
        self.kind
    }

    pub(crate) fn event_generation(&self) -> u64 {
        self.event_generation
    }

    pub(crate) fn supporting_transitions(&self) -> &[TransitionRef] {
        &self.supporting_transitions
    }
}

impl CanonicalEvidenceBody for RelationBody {
    fn canonical_bytes(&self) -> Vec<u8> {
        let mut out = Vec::new();
        put_tag(&mut out, 6);
        put_receipt(&mut out, self.source.receipt());
        put_receipt(&mut out, self.target.receipt());
        put_tag(&mut out, self.kind.tag());
        put_u64(&mut out, self.event_generation);
        put_receipts(
            &mut out,
            self.supporting_transitions
                .iter()
                .map(|value| value.receipt()),
        );
        out
    }

    fn authority_receipt(&self) -> Receipt {
        self.authority
    }
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) struct ConsequenceConfiguration {
    pub(crate) role: ConfigurationRole,
    pub(crate) participant_lineages: Vec<Lineage>,
    pub(crate) transitions: Vec<TransitionRef>,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) struct ConsequenceBody {
    formation_core_receipt: Receipt,
    event_generation: u64,
    members: Vec<FormationRef>,
    configurations: Vec<ConsequenceConfiguration>,
    transitions: Vec<TransitionRef>,
    execution_transition: TransitionRef,
    sensed_reentry_transition: TransitionRef,
    authority: Receipt,
}

impl ConsequenceBody {
    pub(crate) fn new(
        formation_core_receipt: Receipt,
        event_generation: u64,
        members: Vec<FormationRef>,
        configurations: Vec<ConsequenceConfiguration>,
        transitions: Vec<TransitionRef>,
        execution_transition: TransitionRef,
        sensed_reentry_transition: TransitionRef,
    ) -> Self {
        let mut body = Self {
            formation_core_receipt,
            event_generation,
            members,
            configurations,
            transitions,
            execution_transition,
            sensed_reentry_transition,
            authority: [0; 32],
        };
        body.authority = digest(&body.canonical_bytes());
        body
    }

    pub(crate) fn reference(&self) -> ConsequenceRef {
        ConsequenceRef(self.authority)
    }
}

impl CanonicalEvidenceBody for ConsequenceBody {
    fn canonical_bytes(&self) -> Vec<u8> {
        let mut out = Vec::new();
        put_tag(&mut out, 7);
        put_receipt(&mut out, self.formation_core_receipt);
        put_u64(&mut out, self.event_generation);
        put_receipts(&mut out, self.members.iter().map(|value| value.receipt()));
        put_len(&mut out, self.configurations.len());
        for configuration in &self.configurations {
            put_tag(&mut out, configuration.role.tag());
            put_len(&mut out, configuration.participant_lineages.len());
            for lineage in &configuration.participant_lineages {
                put_lineage(&mut out, *lineage);
            }
            put_receipts(
                &mut out,
                configuration
                    .transitions
                    .iter()
                    .map(|value| value.receipt()),
            );
        }
        put_receipts(
            &mut out,
            self.transitions.iter().map(|value| value.receipt()),
        );
        put_receipt(&mut out, self.execution_transition.receipt());
        put_receipt(&mut out, self.sensed_reentry_transition.receipt());
        out
    }

    fn authority_receipt(&self) -> Receipt {
        self.authority
    }
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) struct FormationAdmissionBody {
    kind: FormationKind,
    lineage: Lineage,
    generation: u64,
    core_receipt: Receipt,
    member_receipts: Vec<Receipt>,
    ordered_member_receipts: Vec<Receipt>,
    relation_receipts: Vec<Receipt>,
    neuron_lineages: Vec<Lineage>,
    episode_context: Option<EpisodeContextRef>,
    origin_component_authority: Option<Receipt>,
    recurrence_component_authority: Option<Receipt>,
    recurrence: RecurrenceRef,
    partial_cue: PartialCueRef,
    durability: DurabilityRef,
    consequence: Option<ConsequenceRef>,
    authority: Receipt,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) struct FormationAdmissionParts {
    pub(crate) kind: FormationKind,
    pub(crate) lineage: Lineage,
    pub(crate) generation: u64,
    pub(crate) core_receipt: Receipt,
    pub(crate) member_receipts: Vec<Receipt>,
    pub(crate) ordered_member_receipts: Vec<Receipt>,
    pub(crate) relation_receipts: Vec<Receipt>,
    pub(crate) neuron_lineages: Vec<Lineage>,
    pub(crate) episode_context: Option<EpisodeContextRef>,
    pub(crate) origin_component_authority: Option<Receipt>,
    pub(crate) recurrence_component_authority: Option<Receipt>,
    pub(crate) recurrence: RecurrenceRef,
    pub(crate) partial_cue: PartialCueRef,
    pub(crate) durability: DurabilityRef,
    pub(crate) consequence: Option<ConsequenceRef>,
}

impl FormationAdmissionBody {
    pub(crate) fn new(parts: FormationAdmissionParts) -> Self {
        let mut body = Self {
            kind: parts.kind,
            lineage: parts.lineage,
            generation: parts.generation,
            core_receipt: parts.core_receipt,
            member_receipts: parts.member_receipts,
            ordered_member_receipts: parts.ordered_member_receipts,
            relation_receipts: parts.relation_receipts,
            neuron_lineages: parts.neuron_lineages,
            episode_context: parts.episode_context,
            origin_component_authority: parts.origin_component_authority,
            recurrence_component_authority: parts.recurrence_component_authority,
            recurrence: parts.recurrence,
            partial_cue: parts.partial_cue,
            durability: parts.durability,
            consequence: parts.consequence,
            authority: [0; 32],
        };
        body.authority = digest(&body.canonical_bytes());
        body
    }

    pub(crate) fn reference(&self) -> FormationRef {
        FormationRef(self.authority)
    }

    pub(crate) fn kind(&self) -> FormationKind {
        self.kind
    }

    pub(crate) fn lineage(&self) -> Lineage {
        self.lineage
    }

    pub(crate) fn generation(&self) -> u64 {
        self.generation
    }

    pub(crate) fn core_receipt(&self) -> Receipt {
        self.core_receipt
    }

    pub(crate) fn neuron_lineages(&self) -> &[Lineage] {
        &self.neuron_lineages
    }

    pub(crate) fn member_formations(&self) -> Vec<FormationRef> {
        if self.kind == FormationKind::Mosaic {
            return Vec::new();
        }
        self.member_receipts
            .iter()
            .copied()
            .map(FormationRef)
            .collect()
    }

    pub(crate) fn member_receipts(&self) -> &[Receipt] {
        &self.member_receipts
    }

    pub(crate) fn ordered_member_formations(&self) -> Vec<FormationRef> {
        self.ordered_member_receipts
            .iter()
            .copied()
            .map(FormationRef)
            .collect()
    }

    pub(crate) fn episode_context(&self) -> Option<EpisodeContextRef> {
        self.episode_context
    }

    pub(crate) fn component_authorities(&self) -> Option<(Receipt, Receipt)> {
        self.origin_component_authority
            .zip(self.recurrence_component_authority)
    }

    pub(crate) fn relation_receipts(&self) -> &[Receipt] {
        &self.relation_receipts
    }

    pub(crate) fn relation_references(&self) -> Vec<RelationRef> {
        self.relation_receipts
            .iter()
            .copied()
            .map(RelationRef)
            .collect()
    }

    pub(crate) fn recurrence(&self) -> RecurrenceRef {
        self.recurrence
    }

    pub(crate) fn partial_cue(&self) -> PartialCueRef {
        self.partial_cue
    }

    pub(crate) fn durability(&self) -> DurabilityRef {
        self.durability
    }

    pub(crate) fn consequence(&self) -> Option<ConsequenceRef> {
        self.consequence
    }
}

impl CanonicalEvidenceBody for FormationAdmissionBody {
    fn canonical_bytes(&self) -> Vec<u8> {
        let mut out = Vec::new();
        put_tag(&mut out, 12);
        put_tag(&mut out, self.kind.tag());
        put_lineage(&mut out, self.lineage);
        put_u64(&mut out, self.generation);
        put_receipt(&mut out, self.core_receipt);
        put_receipts(&mut out, self.member_receipts.iter().copied());
        put_receipts(&mut out, self.ordered_member_receipts.iter().copied());
        put_receipts(&mut out, self.relation_receipts.iter().copied());
        put_len(&mut out, self.neuron_lineages.len());
        for lineage in &self.neuron_lineages {
            put_lineage(&mut out, *lineage);
        }
        match self.episode_context {
            Some(value) => {
                put_tag(&mut out, 1);
                put_receipt(&mut out, value.receipt());
            }
            None => put_tag(&mut out, 0),
        }
        match self.origin_component_authority {
            Some(value) => {
                put_tag(&mut out, 1);
                put_receipt(&mut out, value);
            }
            None => put_tag(&mut out, 0),
        }
        match self.recurrence_component_authority {
            Some(value) => {
                put_tag(&mut out, 1);
                put_receipt(&mut out, value);
            }
            None => put_tag(&mut out, 0),
        }
        put_receipt(&mut out, self.recurrence.receipt());
        put_receipt(&mut out, self.partial_cue.receipt());
        put_receipt(&mut out, self.durability.receipt());
        match self.consequence {
            Some(value) => {
                put_tag(&mut out, 1);
                put_receipt(&mut out, value.receipt());
            }
            None => put_tag(&mut out, 0),
        }
        out
    }

    fn authority_receipt(&self) -> Receipt {
        self.authority
    }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) struct EvidenceDecodeEnvelope {
    pub(crate) max_body_bytes: usize,
    pub(crate) max_references: usize,
    pub(crate) max_lineages: usize,
    pub(crate) max_configurations: usize,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) enum EvidenceDecodeError {
    BodyTooLarge,
    AddressDoesNotMatchBody,
    TruncatedBody,
    InvalidTag,
    CountOverflow,
    ReferenceLimitExceeded,
    LineageLimitExceeded,
    ConfigurationLimitExceeded,
    TrailingBytes,
    NonCanonicalBody,
}

struct EvidenceReader<'a> {
    body: &'a [u8],
    cursor: usize,
    envelope: EvidenceDecodeEnvelope,
    references: usize,
    lineages: usize,
    configurations: usize,
}

impl<'a> EvidenceReader<'a> {
    fn new(
        expected_receipt: Receipt,
        body: &'a [u8],
        envelope: EvidenceDecodeEnvelope,
    ) -> Result<Self, EvidenceDecodeError> {
        if body.len() > envelope.max_body_bytes {
            return Err(EvidenceDecodeError::BodyTooLarge);
        }
        if digest(body) != expected_receipt {
            return Err(EvidenceDecodeError::AddressDoesNotMatchBody);
        }
        Ok(Self {
            body,
            cursor: 0,
            envelope,
            references: 0,
            lineages: 0,
            configurations: 0,
        })
    }

    fn remaining(&self) -> usize {
        self.body.len().saturating_sub(self.cursor)
    }

    fn array<const N: usize>(&mut self) -> Result<[u8; N], EvidenceDecodeError> {
        let end = self
            .cursor
            .checked_add(N)
            .ok_or(EvidenceDecodeError::CountOverflow)?;
        let bytes = self
            .body
            .get(self.cursor..end)
            .ok_or(EvidenceDecodeError::TruncatedBody)?;
        self.cursor = end;
        Ok(bytes
            .try_into()
            .map_err(|_| EvidenceDecodeError::TruncatedBody)?)
    }

    fn tag(&mut self, expected: u8) -> Result<(), EvidenceDecodeError> {
        if self.array::<1>()?[0] != expected {
            return Err(EvidenceDecodeError::InvalidTag);
        }
        Ok(())
    }

    fn raw_tag(&mut self) -> Result<u8, EvidenceDecodeError> {
        Ok(self.array::<1>()?[0])
    }

    fn u64(&mut self) -> Result<u64, EvidenceDecodeError> {
        Ok(u64::from_be_bytes(self.array()?))
    }

    fn receipt(&mut self) -> Result<Receipt, EvidenceDecodeError> {
        self.add_references(1)?;
        self.array()
    }

    fn lineage(&mut self) -> Result<Lineage, EvidenceDecodeError> {
        self.add_lineages(1)?;
        self.array()
    }

    fn count(&mut self, minimum_item_bytes: usize) -> Result<usize, EvidenceDecodeError> {
        let count = usize::try_from(self.u64()?).map_err(|_| EvidenceDecodeError::CountOverflow)?;
        let minimum = count
            .checked_mul(minimum_item_bytes)
            .ok_or(EvidenceDecodeError::CountOverflow)?;
        if minimum > self.remaining() {
            return Err(EvidenceDecodeError::TruncatedBody);
        }
        Ok(count)
    }

    fn receipts(&mut self) -> Result<Vec<Receipt>, EvidenceDecodeError> {
        let count = self.count(RECEIPT_BYTES)?;
        self.add_references(count)?;
        let mut values = Vec::with_capacity(count);
        for _ in 0..count {
            values.push(self.array()?);
        }
        Ok(values)
    }

    fn lineages(&mut self) -> Result<Vec<Lineage>, EvidenceDecodeError> {
        let count = self.count(16)?;
        self.add_lineages(count)?;
        let mut values = Vec::with_capacity(count);
        for _ in 0..count {
            values.push(self.array()?);
        }
        Ok(values)
    }

    fn optional_receipt(&mut self) -> Result<Option<Receipt>, EvidenceDecodeError> {
        match self.raw_tag()? {
            0 => Ok(None),
            1 => Ok(Some(self.receipt()?)),
            _ => Err(EvidenceDecodeError::InvalidTag),
        }
    }

    fn configuration_count(&mut self) -> Result<usize, EvidenceDecodeError> {
        let count = self.count(17)?;
        self.configurations = self
            .configurations
            .checked_add(count)
            .ok_or(EvidenceDecodeError::CountOverflow)?;
        if self.configurations > self.envelope.max_configurations {
            return Err(EvidenceDecodeError::ConfigurationLimitExceeded);
        }
        Ok(count)
    }

    fn add_references(&mut self, count: usize) -> Result<(), EvidenceDecodeError> {
        self.references = self
            .references
            .checked_add(count)
            .ok_or(EvidenceDecodeError::CountOverflow)?;
        if self.references > self.envelope.max_references {
            return Err(EvidenceDecodeError::ReferenceLimitExceeded);
        }
        Ok(())
    }

    fn add_lineages(&mut self, count: usize) -> Result<(), EvidenceDecodeError> {
        self.lineages = self
            .lineages
            .checked_add(count)
            .ok_or(EvidenceDecodeError::CountOverflow)?;
        if self.lineages > self.envelope.max_lineages {
            return Err(EvidenceDecodeError::LineageLimitExceeded);
        }
        Ok(())
    }

    fn finish(self) -> Result<(), EvidenceDecodeError> {
        if self.cursor != self.body.len() {
            return Err(EvidenceDecodeError::TrailingBytes);
        }
        Ok(())
    }
}

fn decode_formation_kind(tag: u8) -> Result<FormationKind, EvidenceDecodeError> {
    match tag {
        1 => Ok(FormationKind::Mosaic),
        2 => Ok(FormationKind::MosaicOfMosaics),
        3 => Ok(FormationKind::Tapestry),
        4 => Ok(FormationKind::TapestryOfTapestries),
        5 => Ok(FormationKind::Weave),
        _ => Err(EvidenceDecodeError::InvalidTag),
    }
}

fn decode_relation_kind(tag: u8) -> Result<RelationKind, EvidenceDecodeError> {
    match tag {
        1 => Ok(RelationKind::LearnedRelation),
        2 => Ok(RelationKind::OrderedContinuation),
        3 => Ok(RelationKind::GenerativeIntegration),
        _ => Err(EvidenceDecodeError::InvalidTag),
    }
}

fn decode_provenance(tag: u8) -> Result<Provenance, EvidenceDecodeError> {
    match tag {
        1 => Ok(Provenance::Observed),
        2 => Ok(Provenance::SelfSensed),
        3 => Ok(Provenance::Reassembled),
        4 => Ok(Provenance::Endogenous),
        _ => Err(EvidenceDecodeError::InvalidTag),
    }
}

fn decode_configuration_role(tag: u8) -> Result<ConfigurationRole, EvidenceDecodeError> {
    match tag {
        1 => Ok(ConfigurationRole::Body),
        2 => Ok(ConfigurationRole::Motor),
        3 => Ok(ConfigurationRole::Sensory),
        _ => Err(EvidenceDecodeError::InvalidTag),
    }
}

fn require_canonical<B: CanonicalEvidenceBody>(
    decoded: B,
    body: &[u8],
) -> Result<B, EvidenceDecodeError> {
    if decoded.canonical_bytes() != body || !decoded.has_valid_authority() {
        return Err(EvidenceDecodeError::NonCanonicalBody);
    }
    Ok(decoded)
}

pub(crate) fn decode_recurrence_body(
    expected: RecurrenceRef,
    body: &[u8],
    envelope: EvidenceDecodeEnvelope,
) -> Result<RecurrenceBody, EvidenceDecodeError> {
    let mut reader = EvidenceReader::new(expected.receipt(), body, envelope)?;
    reader.tag(3)?;
    let core = reader.receipt()?;
    let generation = reader.u64()?;
    let transitions = reader.receipts()?.into_iter().map(TransitionRef).collect();
    reader.finish()?;
    require_canonical(RecurrenceBody::new(core, generation, transitions), body)
}

pub(crate) fn decode_partial_cue_body(
    expected: PartialCueRef,
    body: &[u8],
    envelope: EvidenceDecodeEnvelope,
) -> Result<PartialCueBody, EvidenceDecodeError> {
    let mut reader = EvidenceReader::new(expected.receipt(), body, envelope)?;
    reader.tag(4)?;
    let core = reader.receipt()?;
    let generation = reader.u64()?;
    let provenance = decode_provenance(reader.raw_tag()?)?;
    let directly_cued = reader.lineages()?;
    let uncued_changed = reader.lineages()?;
    let transitions = reader.receipts()?.into_iter().map(TransitionRef).collect();
    reader.finish()?;
    require_canonical(
        PartialCueBody::new(
            core,
            generation,
            provenance,
            directly_cued,
            uncued_changed,
            transitions,
        ),
        body,
    )
}

pub(crate) fn decode_durability_body(
    expected: DurabilityRef,
    body: &[u8],
    envelope: EvidenceDecodeEnvelope,
) -> Result<DurabilityBody, EvidenceDecodeError> {
    let mut reader = EvidenceReader::new(expected.receipt(), body, envelope)?;
    reader.tag(5)?;
    let core = reader.receipt()?;
    let persisted = reader.receipt()?;
    let reloaded = reader.receipt()?;
    let persisted_generation = reader.u64()?;
    let restarted_generation = reader.u64()?;
    let reuse_generation = reader.u64()?;
    let transitions = reader.receipts()?.into_iter().map(TransitionRef).collect();
    reader.finish()?;
    require_canonical(
        DurabilityBody::new(
            core,
            persisted,
            reloaded,
            persisted_generation,
            restarted_generation,
            reuse_generation,
            transitions,
        ),
        body,
    )
}

pub(crate) fn decode_relation_body(
    expected: RelationRef,
    body: &[u8],
    envelope: EvidenceDecodeEnvelope,
) -> Result<RelationBody, EvidenceDecodeError> {
    let mut reader = EvidenceReader::new(expected.receipt(), body, envelope)?;
    reader.tag(6)?;
    let source = FormationRef(reader.receipt()?);
    let target = FormationRef(reader.receipt()?);
    let kind = decode_relation_kind(reader.raw_tag()?)?;
    let generation = reader.u64()?;
    let transitions = reader.receipts()?.into_iter().map(TransitionRef).collect();
    reader.finish()?;
    require_canonical(
        RelationBody::new(source, target, kind, generation, transitions),
        body,
    )
}

pub(crate) fn decode_consequence_body(
    expected: ConsequenceRef,
    body: &[u8],
    envelope: EvidenceDecodeEnvelope,
) -> Result<ConsequenceBody, EvidenceDecodeError> {
    let mut reader = EvidenceReader::new(expected.receipt(), body, envelope)?;
    reader.tag(7)?;
    let core = reader.receipt()?;
    let generation = reader.u64()?;
    let members = reader.receipts()?.into_iter().map(FormationRef).collect();
    let configuration_count = reader.configuration_count()?;
    let mut configurations = Vec::with_capacity(configuration_count);
    for _ in 0..configuration_count {
        let role = decode_configuration_role(reader.raw_tag()?)?;
        let participant_lineages = reader.lineages()?;
        let transitions = reader.receipts()?.into_iter().map(TransitionRef).collect();
        configurations.push(ConsequenceConfiguration {
            role,
            participant_lineages,
            transitions,
        });
    }
    let transitions = reader.receipts()?.into_iter().map(TransitionRef).collect();
    let execution_transition = TransitionRef(reader.receipt()?);
    let sensed_reentry_transition = TransitionRef(reader.receipt()?);
    reader.finish()?;
    require_canonical(
        ConsequenceBody::new(
            core,
            generation,
            members,
            configurations,
            transitions,
            execution_transition,
            sensed_reentry_transition,
        ),
        body,
    )
}

pub(crate) fn decode_formation_admission_body(
    expected: FormationRef,
    body: &[u8],
    envelope: EvidenceDecodeEnvelope,
) -> Result<FormationAdmissionBody, EvidenceDecodeError> {
    let mut reader = EvidenceReader::new(expected.receipt(), body, envelope)?;
    reader.tag(12)?;
    let kind = decode_formation_kind(reader.raw_tag()?)?;
    let lineage = reader.lineage()?;
    let generation = reader.u64()?;
    let core_receipt = reader.receipt()?;
    let member_receipts = reader.receipts()?;
    let ordered_member_receipts = reader.receipts()?;
    let relation_receipts = reader.receipts()?;
    let neuron_lineages = reader.lineages()?;
    let episode_context = reader.optional_receipt()?.map(EpisodeContextRef);
    let origin_component_authority = reader.optional_receipt()?;
    let recurrence_component_authority = reader.optional_receipt()?;
    let recurrence = RecurrenceRef(reader.receipt()?);
    let partial_cue = PartialCueRef(reader.receipt()?);
    let durability = DurabilityRef(reader.receipt()?);
    let consequence = reader.optional_receipt()?.map(ConsequenceRef);
    reader.finish()?;
    require_canonical(
        FormationAdmissionBody::new(FormationAdmissionParts {
            kind,
            lineage,
            generation,
            core_receipt,
            member_receipts,
            ordered_member_receipts,
            relation_receipts,
            neuron_lineages,
            episode_context,
            origin_component_authority,
            recurrence_component_authority,
            recurrence,
            partial_cue,
            durability,
            consequence,
        }),
        body,
    )
}

pub(crate) trait EvidenceResolver {
    fn resolve_episode_context(
        &self,
        reference: EpisodeContextRef,
    ) -> Option<ResolvedEpisodeContextBody>;
    fn resolve_fractal(&self, reference: FractalRef) -> Option<FractalBody>;
    fn resolve_transition(&self, reference: TransitionRef) -> Option<TransitionBody>;
    fn resolve_recurrence(&self, reference: RecurrenceRef) -> Option<RecurrenceBody>;
    fn resolve_partial_cue(&self, reference: PartialCueRef) -> Option<PartialCueBody>;
    fn resolve_durability(&self, reference: DurabilityRef) -> Option<DurabilityBody>;
    fn resolve_formation(&self, reference: FormationRef) -> Option<FormationAdmissionBody>;
    fn resolve_relation(&self, reference: RelationRef) -> Option<RelationBody>;
    fn resolve_consequence(&self, reference: ConsequenceRef) -> Option<ConsequenceBody>;
}

pub(crate) fn resolve_admitted_mosaic_context<R: EvidenceResolver>(
    admitted: &AdmittedFormationEvidence,
    resolver: &R,
) -> Option<ResolvedEpisodeContextBody> {
    admitted
        .body
        .episode_context()
        .and_then(|reference| resolver.resolve_episode_context(reference))
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) struct FormationAdmissionBudget {
    pub(crate) max_decoded_body_bytes: usize,
    pub(crate) max_total_bytes: usize,
    pub(crate) max_validation_terms: usize,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) struct FormationAdmissionRequirement {
    pub(crate) decoded_body_bytes: usize,
    pub(crate) reference_bytes: usize,
    pub(crate) total_bytes: usize,
    pub(crate) validation_terms: usize,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) struct MatureMosaicCandidate {
    pub(crate) formation_lineage: Lineage,
    pub(crate) generation: u64,
    pub(crate) episode_context: EpisodeContextRef,
    pub(crate) origin_component_authority: Receipt,
    pub(crate) recurrence_component_authority: Receipt,
    pub(crate) members: Vec<FractalRef>,
    pub(crate) inter_neuron_transfers: Vec<TransitionRef>,
    pub(crate) recurrence: RecurrenceRef,
    pub(crate) partial_cue: PartialCueRef,
    pub(crate) durability: DurabilityRef,
}

impl MatureMosaicCandidate {
    pub(crate) fn core_receipt(&self) -> Receipt {
        let structural = formation_core_receipt(
            FormationKind::Mosaic,
            self.formation_lineage,
            self.generation,
            Some(self.episode_context.receipt()),
            self.members.iter().map(|value| value.receipt()),
            self.inter_neuron_transfers
                .iter()
                .map(|value| value.receipt()),
            std::iter::empty(),
        );
        let mut body = Vec::new();
        put_tag(&mut body, 11);
        put_receipt(&mut body, structural);
        put_receipt(&mut body, self.origin_component_authority);
        put_receipt(&mut body, self.recurrence_component_authority);
        digest(&body)
    }
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) struct RecursiveFormationCandidate {
    pub(crate) kind: FormationKind,
    pub(crate) formation_lineage: Lineage,
    pub(crate) generation: u64,
    pub(crate) members: Vec<FormationRef>,
    pub(crate) relations: Vec<RelationRef>,
    pub(crate) ordered_members: Vec<FormationRef>,
    pub(crate) recurrence: RecurrenceRef,
    pub(crate) partial_cue: PartialCueRef,
    pub(crate) durability: DurabilityRef,
    pub(crate) consequence: Option<ConsequenceRef>,
}

impl RecursiveFormationCandidate {
    pub(crate) fn core_receipt(&self) -> Receipt {
        formation_core_receipt(
            self.kind,
            self.formation_lineage,
            self.generation,
            None,
            self.members.iter().map(|value| value.receipt()),
            std::iter::empty(),
            self.relations.iter().map(|value| value.receipt()),
        )
    }
}

fn formation_core_receipt(
    kind: FormationKind,
    lineage: Lineage,
    generation: u64,
    episode_context: Option<Receipt>,
    members: impl IntoIterator<Item = Receipt>,
    transitions: impl IntoIterator<Item = Receipt>,
    relations: impl IntoIterator<Item = Receipt>,
) -> Receipt {
    let mut out = Vec::new();
    put_tag(&mut out, 9);
    put_tag(&mut out, kind.tag());
    put_lineage(&mut out, lineage);
    put_u64(&mut out, generation);
    match episode_context {
        Some(value) => {
            put_tag(&mut out, 1);
            put_receipt(&mut out, value);
        }
        None => put_tag(&mut out, 0),
    }
    put_receipts(&mut out, members);
    put_receipts(&mut out, transitions);
    put_receipts(&mut out, relations);
    digest(&out)
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) struct AdmittedFormationEvidence {
    pub(crate) body: FormationAdmissionBody,
    pub(crate) requirement: FormationAdmissionRequirement,
}

#[derive(Default)]
struct ResourceMeter {
    decoded: BTreeMap<Receipt, usize>,
    references: usize,
    terms: usize,
}

impl ResourceMeter {
    fn body<B: CanonicalEvidenceBody>(&mut self, body: &B) -> Result<(), EvidenceError> {
        if !body.has_valid_authority() {
            return Err(EvidenceError::AuthorityDoesNotMatchDecodedBody);
        }
        self.decoded
            .entry(body.authority_receipt())
            .or_insert_with(|| body.canonical_len());
        self.terms = self
            .terms
            .checked_add(1)
            .ok_or(EvidenceError::ResourceOverflow)?;
        Ok(())
    }

    fn refs(&mut self, count: usize) -> Result<(), EvidenceError> {
        self.references = self
            .references
            .checked_add(count)
            .ok_or(EvidenceError::ResourceOverflow)?;
        self.terms = self
            .terms
            .checked_add(count)
            .ok_or(EvidenceError::ResourceOverflow)?;
        Ok(())
    }

    fn requirement(&self) -> Result<FormationAdmissionRequirement, EvidenceError> {
        let decoded_body_bytes = self.decoded.values().try_fold(0_usize, |sum, value| {
            sum.checked_add(*value)
                .ok_or(EvidenceError::ResourceOverflow)
        })?;
        let reference_bytes = self
            .references
            .checked_mul(RECEIPT_BYTES)
            .ok_or(EvidenceError::ResourceOverflow)?;
        let total_bytes = decoded_body_bytes
            .checked_add(reference_bytes)
            .ok_or(EvidenceError::ResourceOverflow)?;
        Ok(FormationAdmissionRequirement {
            decoded_body_bytes,
            reference_bytes,
            total_bytes,
            validation_terms: self.terms,
        })
    }
}

pub(crate) fn admit_mature_mosaic<R: EvidenceResolver>(
    candidate: &MatureMosaicCandidate,
    resolver: &R,
    budget: FormationAdmissionBudget,
) -> Result<AdmittedFormationEvidence, EvidenceError> {
    if candidate.origin_component_authority == [0; 32]
        || candidate.recurrence_component_authority == [0; 32]
    {
        return Err(EvidenceError::MissingPhysicalComponentAuthority);
    }
    if candidate.members.len() < 3 {
        return Err(EvidenceError::MosaicFloorNotMet(candidate.members.len()));
    }
    ensure_unique(candidate.members.iter().map(|value| value.receipt()))?;
    let core = candidate.core_receipt();
    let mut meter = ResourceMeter::default();
    meter.refs(candidate.members.len() + candidate.inter_neuron_transfers.len() + 4)?;

    let episode = resolver
        .resolve_episode_context(candidate.episode_context)
        .ok_or(EvidenceError::UnresolvedEpisodeContext(
            candidate.episode_context,
        ))?;
    verify_reference(candidate.episode_context, &episode, &mut meter)?;
    let episode_participants = validate_episode_context(&episode)?;

    let mut participants = BTreeSet::new();
    let mut perspectives = BTreeSet::new();
    for reference in &candidate.members {
        let body = resolver
            .resolve_fractal(*reference)
            .ok_or(EvidenceError::UnresolvedFractal(*reference))?;
        verify_reference(*reference, &body, &mut meter)?;
        if body.generation() != candidate.generation {
            return Err(EvidenceError::EventGenerationMismatch);
        }
        if !body.physical_authorities().is_complete() {
            return Err(EvidenceError::IncompleteEpisodeContext);
        }
        if !participants.insert(body.lineage()) {
            return Err(EvidenceError::DuplicateParticipant);
        }
        if !perspectives.insert(body.perspective_receipt()) {
            return Err(EvidenceError::DuplicatePerspective);
        }
        let episode_participant = episode_participants.get(&body.lineage()).ok_or(
            EvidenceError::MemberDidNotParticipateInEpisode(body.lineage()),
        )?;
        if episode_participant.causal_occurrence_authority != episode.causal_occurrence_authority {
            return Err(EvidenceError::MemberCausalOccurrenceMismatch(
                body.lineage(),
            ));
        }
        if episode_participant.fractal != *reference {
            return Err(EvidenceError::EpisodeMemberFractalMismatch(body.lineage()));
        }
        if episode_participant.successful_local_transition_authority == [0; 32]
            || episode_participant.successful_local_transition_authority
                != body.successful_local_transition_authority()
            || episode_participant.physical_authorities != body.physical_authorities()
        {
            return Err(EvidenceError::LocalTransitionAuthorityMismatch(
                body.lineage(),
            ));
        }
    }

    if !candidate.inter_neuron_transfers.is_empty() {
        resolve_transitions(
            &candidate.inter_neuron_transfers,
            resolver,
            &mut meter,
            Some(candidate.generation),
            &participants,
        )?;
    }
    let participant_groups = participants
        .iter()
        .map(|lineage| BTreeSet::from([*lineage]))
        .collect::<Vec<_>>();
    validate_collective_evidence(
        core,
        candidate.generation,
        &participants,
        &participant_groups,
        3,
        candidate.recurrence,
        candidate.partial_cue,
        candidate.durability,
        resolver,
        &mut meter,
    )?;

    let requirement = finish_requirement(&meter, budget)?;
    let body = FormationAdmissionBody::new(FormationAdmissionParts {
        kind: FormationKind::Mosaic,
        lineage: candidate.formation_lineage,
        generation: candidate.generation,
        core_receipt: core,
        member_receipts: candidate
            .members
            .iter()
            .map(|value| value.receipt())
            .collect(),
        ordered_member_receipts: Vec::new(),
        relation_receipts: candidate
            .inter_neuron_transfers
            .iter()
            .map(|value| value.receipt())
            .collect(),
        neuron_lineages: participants.into_iter().collect(),
        episode_context: Some(candidate.episode_context),
        origin_component_authority: Some(candidate.origin_component_authority),
        recurrence_component_authority: Some(candidate.recurrence_component_authority),
        recurrence: candidate.recurrence,
        partial_cue: candidate.partial_cue,
        durability: candidate.durability,
        consequence: None,
    });
    Ok(AdmittedFormationEvidence { body, requirement })
}

pub(crate) fn admit_recursive_formation<R: EvidenceResolver>(
    candidate: &RecursiveFormationCandidate,
    resolver: &R,
    budget: FormationAdmissionBudget,
) -> Result<AdmittedFormationEvidence, EvidenceError> {
    if candidate.kind == FormationKind::Mosaic {
        return Err(EvidenceError::WrongAdmissionBoundary);
    }
    if candidate.members.len() < 2 {
        return Err(EvidenceError::RecursiveRelationNeedsTwoMembers);
    }
    let ordered_kind = matches!(
        candidate.kind,
        FormationKind::Tapestry | FormationKind::TapestryOfTapestries
    );
    if !ordered_kind && !candidate.ordered_members.is_empty() {
        return Err(EvidenceError::OrderedMembersDoNotMatch);
    }
    ensure_unique(candidate.members.iter().map(|value| value.receipt()))?;
    ensure_unique(candidate.relations.iter().map(|value| value.receipt()))?;
    let core = candidate.core_receipt();
    let mut meter = ResourceMeter::default();
    meter.refs(
        candidate.members.len()
            + candidate.relations.len()
            + candidate.ordered_members.len()
            + 3
            + usize::from(candidate.consequence.is_some()),
    )?;

    let mut formations = BTreeMap::new();
    let mut participants = BTreeSet::new();
    let mut participant_groups = Vec::new();
    let mut reached_leaf_cache = BTreeMap::new();
    for reference in &candidate.members {
        let body = resolver
            .resolve_formation(*reference)
            .ok_or(EvidenceError::UnresolvedFormation(*reference))?;
        verify_reference(*reference, &body, &mut meter)?;
        if !member_kind_allowed(candidate.kind, body.kind()) {
            return Err(EvidenceError::IllegalMemberKind {
                parent: candidate.kind,
                member: body.kind(),
            });
        }
        let group =
            resolve_leaf_participants(*reference, resolver, &mut meter, &mut reached_leaf_cache)?;
        if group.is_empty() {
            return Err(EvidenceError::EmptyFormationParticipant);
        }
        participants.extend(group.iter().copied());
        participant_groups.push(group);
        formations.insert(*reference, body);
    }

    let expected_relation_kind = relation_kind_for_parent(candidate.kind);
    let mut relation_edges = BTreeSet::new();
    for reference in &candidate.relations {
        let body = resolver
            .resolve_relation(*reference)
            .ok_or(EvidenceError::UnresolvedRelation(*reference))?;
        verify_reference(*reference, &body, &mut meter)?;
        if body.kind != expected_relation_kind {
            return Err(EvidenceError::RelationKindDoesNotMatchParent);
        }
        let source = formations
            .get(&body.source)
            .ok_or(EvidenceError::RelationLeavesFormationSet)?;
        let target = formations
            .get(&body.target)
            .ok_or(EvidenceError::RelationLeavesFormationSet)?;
        if source.reference() == target.reference()
            || body.event_generation != candidate.generation
            || body.supporting_transitions.is_empty()
        {
            return Err(EvidenceError::RelationLacksCurrentPhysicalSupport);
        }
        meter.refs(body.supporting_transitions.len())?;
        let support = resolve_transitions(
            &body.supporting_transitions,
            resolver,
            &mut meter,
            Some(body.event_generation),
            &participants,
        )?;
        let source_group =
            resolve_leaf_participants(body.source, resolver, &mut meter, &mut reached_leaf_cache)?;
        let target_group =
            resolve_leaf_participants(body.target, resolver, &mut meter, &mut reached_leaf_cache)?;
        let crosses = support.iter().any(|transition| {
            transition.source() != transition.target()
                && source_group.contains(&transition.source())
                && target_group.contains(&transition.target())
        });
        if !crosses {
            return Err(EvidenceError::RelationLacksCurrentPhysicalSupport);
        }
        relation_edges.insert((body.source, body.target));
    }

    match candidate.kind {
        FormationKind::MosaicOfMosaics | FormationKind::Weave => {
            require_weak_formation_connection(&candidate.members, &relation_edges)?;
        }
        FormationKind::Tapestry | FormationKind::TapestryOfTapestries => {
            if candidate.ordered_members.len() != candidate.members.len()
                || candidate
                    .ordered_members
                    .iter()
                    .copied()
                    .collect::<BTreeSet<_>>()
                    != candidate.members.iter().copied().collect::<BTreeSet<_>>()
            {
                return Err(EvidenceError::OrderedMembersDoNotMatch);
            }
            for pair in candidate.ordered_members.windows(2) {
                if !relation_edges.contains(&(pair[0], pair[1])) {
                    return Err(EvidenceError::MissingOrderedContinuation);
                }
            }
        }
        FormationKind::Mosaic => return Err(EvidenceError::WrongAdmissionBoundary),
    }

    if candidate.kind == FormationKind::Weave {
        let reference = candidate
            .consequence
            .ok_or(EvidenceError::MissingWeaveConsequence)?;
        let body = resolver
            .resolve_consequence(reference)
            .ok_or(EvidenceError::UnresolvedConsequence(reference))?;
        verify_reference(reference, &body, &mut meter)?;
        validate_weave_consequence(
            &body,
            core,
            candidate,
            &participant_groups,
            &participants,
            resolver,
            &mut meter,
        )?;
    } else if candidate.consequence.is_some() {
        return Err(EvidenceError::ConsequenceOnlyBelongsToWeave);
    }

    validate_collective_evidence(
        core,
        candidate.generation,
        &participants,
        &participant_groups,
        2,
        candidate.recurrence,
        candidate.partial_cue,
        candidate.durability,
        resolver,
        &mut meter,
    )?;
    let requirement = finish_requirement(&meter, budget)?;
    let body = FormationAdmissionBody::new(FormationAdmissionParts {
        kind: candidate.kind,
        lineage: candidate.formation_lineage,
        generation: candidate.generation,
        core_receipt: core,
        member_receipts: candidate
            .members
            .iter()
            .map(|value| value.receipt())
            .collect(),
        ordered_member_receipts: candidate
            .ordered_members
            .iter()
            .map(|value| value.receipt())
            .collect(),
        relation_receipts: candidate
            .relations
            .iter()
            .map(|value| value.receipt())
            .collect(),
        // Recursive formations retain immediate member references. Descendant
        // lineages are resolved only for the reached operation; copying their
        // union here would amplify every higher hierarchy level.
        neuron_lineages: Vec::new(),
        episode_context: None,
        origin_component_authority: None,
        recurrence_component_authority: None,
        recurrence: candidate.recurrence,
        partial_cue: candidate.partial_cue,
        durability: candidate.durability,
        consequence: candidate.consequence,
    });
    Ok(AdmittedFormationEvidence { body, requirement })
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) enum ColdFormationInspectionError {
    Decode(EvidenceDecodeError),
    MissingMosaicBindings,
    Formation(EvidenceError),
    ReadmissionChangedCanonicalBody,
}

impl From<EvidenceDecodeError> for ColdFormationInspectionError {
    fn from(value: EvidenceDecodeError) -> Self {
        Self::Decode(value)
    }
}

impl From<EvidenceError> for ColdFormationInspectionError {
    fn from(value: EvidenceError) -> Self {
        Self::Formation(value)
    }
}

pub(crate) fn cold_decode_and_readmit_formation<R: EvidenceResolver>(
    expected: FormationRef,
    canonical_body: &[u8],
    decode_envelope: EvidenceDecodeEnvelope,
    resolver: &R,
    admission_budget: FormationAdmissionBudget,
) -> Result<AdmittedFormationEvidence, ColdFormationInspectionError> {
    let decoded = decode_formation_admission_body(expected, canonical_body, decode_envelope)?;
    let readmitted = match decoded.kind() {
        FormationKind::Mosaic => {
            let episode_context = decoded
                .episode_context()
                .ok_or(ColdFormationInspectionError::MissingMosaicBindings)?;
            let (origin_component_authority, recurrence_component_authority) = decoded
                .component_authorities()
                .ok_or(ColdFormationInspectionError::MissingMosaicBindings)?;
            let candidate = MatureMosaicCandidate {
                formation_lineage: decoded.lineage(),
                generation: decoded.generation(),
                episode_context,
                origin_component_authority,
                recurrence_component_authority,
                members: decoded
                    .member_receipts()
                    .iter()
                    .copied()
                    .map(FractalRef)
                    .collect(),
                inter_neuron_transfers: decoded
                    .relation_receipts()
                    .iter()
                    .copied()
                    .map(TransitionRef)
                    .collect(),
                recurrence: decoded.recurrence(),
                partial_cue: decoded.partial_cue(),
                durability: decoded.durability(),
            };
            admit_mature_mosaic(&candidate, resolver, admission_budget)?
        }
        FormationKind::MosaicOfMosaics
        | FormationKind::Tapestry
        | FormationKind::TapestryOfTapestries
        | FormationKind::Weave => {
            let candidate = RecursiveFormationCandidate {
                kind: decoded.kind(),
                formation_lineage: decoded.lineage(),
                generation: decoded.generation(),
                members: decoded.member_formations(),
                relations: decoded.relation_references(),
                ordered_members: decoded.ordered_member_formations(),
                recurrence: decoded.recurrence(),
                partial_cue: decoded.partial_cue(),
                durability: decoded.durability(),
                consequence: decoded.consequence(),
            };
            admit_recursive_formation(&candidate, resolver, admission_budget)?
        }
    };
    if readmitted.body != decoded || readmitted.body.reference() != expected {
        return Err(ColdFormationInspectionError::ReadmissionChangedCanonicalBody);
    }
    Ok(readmitted)
}

pub(crate) trait ColdFormationEvidenceResolver {
    fn resolve_canonical_evidence_body(&self, receipt: Receipt) -> Option<Vec<u8>>;
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) enum ColdFormationGraphError {
    UnresolvedCanonicalBody(Receipt),
    Decode(EvidenceDecodeError),
    Readmission(ColdFormationInspectionError),
}

impl From<EvidenceDecodeError> for ColdFormationGraphError {
    fn from(value: EvidenceDecodeError) -> Self {
        Self::Decode(value)
    }
}

impl From<ColdFormationInspectionError> for ColdFormationGraphError {
    fn from(value: ColdFormationInspectionError) -> Self {
        Self::Readmission(value)
    }
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) struct ColdFormationGraphInspection {
    pub(crate) root: AdmittedFormationEvidence,
    pub(crate) formation_bodies: usize,
    pub(crate) relation_bodies: usize,
    pub(crate) collective_evidence_bodies: usize,
}

struct DecodedHierarchyResolver<'a, R> {
    physical: &'a R,
    recurrences: BTreeMap<RecurrenceRef, RecurrenceBody>,
    cues: BTreeMap<PartialCueRef, PartialCueBody>,
    durability: BTreeMap<DurabilityRef, DurabilityBody>,
    formations: BTreeMap<FormationRef, FormationAdmissionBody>,
    relations: BTreeMap<RelationRef, RelationBody>,
    consequences: BTreeMap<ConsequenceRef, ConsequenceBody>,
}

impl<R: EvidenceResolver> EvidenceResolver for DecodedHierarchyResolver<'_, R> {
    fn resolve_episode_context(
        &self,
        reference: EpisodeContextRef,
    ) -> Option<ResolvedEpisodeContextBody> {
        self.physical.resolve_episode_context(reference)
    }

    fn resolve_fractal(&self, reference: FractalRef) -> Option<FractalBody> {
        self.physical.resolve_fractal(reference)
    }

    fn resolve_transition(&self, reference: TransitionRef) -> Option<TransitionBody> {
        self.physical.resolve_transition(reference)
    }

    fn resolve_recurrence(&self, reference: RecurrenceRef) -> Option<RecurrenceBody> {
        self.recurrences.get(&reference).cloned()
    }

    fn resolve_partial_cue(&self, reference: PartialCueRef) -> Option<PartialCueBody> {
        self.cues.get(&reference).cloned()
    }

    fn resolve_durability(&self, reference: DurabilityRef) -> Option<DurabilityBody> {
        self.durability.get(&reference).cloned()
    }

    fn resolve_formation(&self, reference: FormationRef) -> Option<FormationAdmissionBody> {
        self.formations.get(&reference).cloned()
    }

    fn resolve_relation(&self, reference: RelationRef) -> Option<RelationBody> {
        self.relations.get(&reference).cloned()
    }

    fn resolve_consequence(&self, reference: ConsequenceRef) -> Option<ConsequenceBody> {
        self.consequences.get(&reference).cloned()
    }
}

pub(crate) fn inspect_cold_formation_evidence_graph<
    R: EvidenceResolver,
    C: ColdFormationEvidenceResolver,
>(
    root_reference: FormationRef,
    root_canonical_body: &[u8],
    cold: &C,
    physical: &R,
    decode_envelope: EvidenceDecodeEnvelope,
    admission_budget: FormationAdmissionBudget,
) -> Result<ColdFormationGraphInspection, ColdFormationGraphError> {
    let root =
        decode_formation_admission_body(root_reference, root_canonical_body, decode_envelope)?;
    let mut resolver = DecodedHierarchyResolver {
        physical,
        recurrences: BTreeMap::new(),
        cues: BTreeMap::new(),
        durability: BTreeMap::new(),
        formations: BTreeMap::from([(root_reference, root)]),
        relations: BTreeMap::new(),
        consequences: BTreeMap::new(),
    };
    let mut pending = VecDeque::from([root_reference]);
    let mut expanded = BTreeSet::new();
    while let Some(reference) = pending.pop_front() {
        if !expanded.insert(reference) {
            continue;
        }
        let formation = resolver.formations.get(&reference).cloned().ok_or(
            ColdFormationGraphError::UnresolvedCanonicalBody(reference.receipt()),
        )?;
        for member in formation.member_formations() {
            if !resolver.formations.contains_key(&member) {
                let bytes = cold
                    .resolve_canonical_evidence_body(member.receipt())
                    .ok_or(ColdFormationGraphError::UnresolvedCanonicalBody(
                        member.receipt(),
                    ))?;
                let decoded = decode_formation_admission_body(member, &bytes, decode_envelope)?;
                resolver.formations.insert(member, decoded);
            }
            pending.push_back(member);
        }
        if formation.kind() != FormationKind::Mosaic {
            for relation in formation.relation_references() {
                if resolver.relations.contains_key(&relation) {
                    continue;
                }
                let bytes = cold
                    .resolve_canonical_evidence_body(relation.receipt())
                    .ok_or(ColdFormationGraphError::UnresolvedCanonicalBody(
                        relation.receipt(),
                    ))?;
                resolver.relations.insert(
                    relation,
                    decode_relation_body(relation, &bytes, decode_envelope)?,
                );
            }
        }
        let recurrence = formation.recurrence();
        if !resolver.recurrences.contains_key(&recurrence) {
            let bytes = cold
                .resolve_canonical_evidence_body(recurrence.receipt())
                .ok_or(ColdFormationGraphError::UnresolvedCanonicalBody(
                    recurrence.receipt(),
                ))?;
            resolver.recurrences.insert(
                recurrence,
                decode_recurrence_body(recurrence, &bytes, decode_envelope)?,
            );
        }
        let cue = formation.partial_cue();
        if !resolver.cues.contains_key(&cue) {
            let bytes = cold.resolve_canonical_evidence_body(cue.receipt()).ok_or(
                ColdFormationGraphError::UnresolvedCanonicalBody(cue.receipt()),
            )?;
            resolver
                .cues
                .insert(cue, decode_partial_cue_body(cue, &bytes, decode_envelope)?);
        }
        let durability = formation.durability();
        if !resolver.durability.contains_key(&durability) {
            let bytes = cold
                .resolve_canonical_evidence_body(durability.receipt())
                .ok_or(ColdFormationGraphError::UnresolvedCanonicalBody(
                    durability.receipt(),
                ))?;
            resolver.durability.insert(
                durability,
                decode_durability_body(durability, &bytes, decode_envelope)?,
            );
        }
        if let Some(consequence) = formation.consequence() {
            if !resolver.consequences.contains_key(&consequence) {
                let bytes = cold
                    .resolve_canonical_evidence_body(consequence.receipt())
                    .ok_or(ColdFormationGraphError::UnresolvedCanonicalBody(
                        consequence.receipt(),
                    ))?;
                resolver.consequences.insert(
                    consequence,
                    decode_consequence_body(consequence, &bytes, decode_envelope)?,
                );
            }
        }
    }

    let formation_bodies = resolver.formations.len();
    let relation_bodies = resolver.relations.len();
    let collective_evidence_bodies = resolver
        .recurrences
        .len()
        .checked_add(resolver.cues.len())
        .and_then(|value| value.checked_add(resolver.durability.len()))
        .and_then(|value| value.checked_add(resolver.consequences.len()))
        .ok_or(ColdFormationGraphError::Readmission(
            ColdFormationInspectionError::Formation(EvidenceError::ResourceOverflow),
        ))?;
    let mut root = None;
    for (reference, formation) in &resolver.formations {
        let readmitted = cold_decode_and_readmit_formation(
            *reference,
            &formation.canonical_bytes(),
            decode_envelope,
            &resolver,
            admission_budget,
        )?;
        if *reference == root_reference {
            root = Some(readmitted);
        }
    }
    Ok(ColdFormationGraphInspection {
        root: root.ok_or(ColdFormationGraphError::UnresolvedCanonicalBody(
            root_reference.receipt(),
        ))?,
        formation_bodies,
        relation_bodies,
        collective_evidence_bodies,
    })
}

fn resolve_leaf_participants<R: EvidenceResolver>(
    root: FormationRef,
    resolver: &R,
    meter: &mut ResourceMeter,
    cache: &mut BTreeMap<FormationRef, BTreeSet<Lineage>>,
) -> Result<BTreeSet<Lineage>, EvidenceError> {
    fn walk<R: EvidenceResolver>(
        reference: FormationRef,
        resolver: &R,
        meter: &mut ResourceMeter,
        cache: &mut BTreeMap<FormationRef, BTreeSet<Lineage>>,
        active: &mut BTreeSet<FormationRef>,
    ) -> Result<BTreeSet<Lineage>, EvidenceError> {
        if let Some(leaves) = cache.get(&reference) {
            return Ok(leaves.clone());
        }
        if !active.insert(reference) {
            return Err(EvidenceError::FormationCycle);
        }
        let body = resolver
            .resolve_formation(reference)
            .ok_or(EvidenceError::UnresolvedFormation(reference))?;
        verify_reference(reference, &body, meter)?;
        if body.kind() == FormationKind::Mosaic {
            if body.neuron_lineages().is_empty() {
                return Err(EvidenceError::EmptyFormationParticipant);
            }
            let leaves: BTreeSet<Lineage> = body.neuron_lineages().iter().copied().collect();
            active.remove(&reference);
            cache.insert(reference, leaves.clone());
            return Ok(leaves);
        } else {
            let members = body.member_formations();
            if members.len() < 2 {
                return Err(EvidenceError::EmptyFormationParticipant);
            }
            meter.refs(members.len())?;
            let mut leaves = BTreeSet::new();
            for member in members {
                let child = resolver
                    .resolve_formation(member)
                    .ok_or(EvidenceError::UnresolvedFormation(member))?;
                if !member_kind_allowed(body.kind(), child.kind()) {
                    return Err(EvidenceError::IllegalMemberKind {
                        parent: body.kind(),
                        member: child.kind(),
                    });
                }
                leaves.extend(walk(member, resolver, meter, cache, active)?);
            }
            active.remove(&reference);
            cache.insert(reference, leaves.clone());
            return Ok(leaves);
        }
    }

    let mut active = BTreeSet::new();
    walk(root, resolver, meter, cache, &mut active)
}

fn verify_reference<R, B>(
    reference: R,
    body: &B,
    meter: &mut ResourceMeter,
) -> Result<(), EvidenceError>
where
    R: Copy + IntoReceipt,
    B: CanonicalEvidenceBody,
{
    meter.body(body)?;
    if reference.into_receipt() != body.authority_receipt() {
        return Err(EvidenceError::ResolvedReferenceChanged);
    }
    Ok(())
}

fn validate_episode_context(
    episode: &ResolvedEpisodeContextBody,
) -> Result<BTreeMap<Lineage, &EpisodeMemberParticipation>, EvidenceError> {
    if episode.causal_occurrence_authority == [0; 32]
        || episode.body_predecessor_authority == [0; 32]
        || episode.body_successor_authority == [0; 32]
        || episode.fluid_predecessor_authority == [0; 32]
        || episode.fluid_successor_authority == [0; 32]
    {
        return Err(EvidenceError::IncompleteEpisodeContext);
    }
    let fluid_state_changed =
        episode.fluid_predecessor_authority != episode.fluid_successor_authority;
    match episode.fluid_status {
        FluidEpisodeStatus::Perturbed if !fluid_state_changed => {
            return Err(EvidenceError::FluidStatusContradictsState)
        }
        FluidEpisodeStatus::Quiescent {
            quiescence_authority,
        } if fluid_state_changed || quiescence_authority == [0; 32] => {
            return Err(EvidenceError::FluidStatusContradictsState)
        }
        FluidEpisodeStatus::Unavailable {
            unavailability_authority,
        } if fluid_state_changed || unavailability_authority == [0; 32] => {
            return Err(EvidenceError::FluidStatusContradictsState)
        }
        FluidEpisodeStatus::Perturbed
        | FluidEpisodeStatus::Quiescent { .. }
        | FluidEpisodeStatus::Unavailable { .. } => {}
    }
    if episode
        .participants
        .windows(2)
        .any(|pair| pair[0].lineage >= pair[1].lineage)
    {
        return Err(EvidenceError::NonCanonicalEpisodeParticipants);
    }
    let mut by_lineage = BTreeMap::new();
    let mut fractals = BTreeSet::new();
    let mut local_transitions = BTreeSet::new();
    for participant in &episode.participants {
        if participant.fractal.receipt() == [0; 32]
            || participant.successful_local_transition_authority == [0; 32]
            || participant.causal_occurrence_authority == [0; 32]
            || !participant.physical_authorities.is_complete()
            || !fractals.insert(participant.fractal)
            || !local_transitions.insert(participant.successful_local_transition_authority)
            || by_lineage
                .insert(participant.lineage, participant)
                .is_some()
        {
            return Err(EvidenceError::NonCanonicalEpisodeParticipants);
        }
    }
    Ok(by_lineage)
}

pub(crate) trait IntoReceipt {
    fn into_receipt(self) -> Receipt;
}

macro_rules! into_receipt {
    ($($name:ident),+ $(,)?) => {
        $(impl IntoReceipt for $name {
            fn into_receipt(self) -> Receipt { self.receipt() }
        })+
    };
}

into_receipt!(
    FractalRef,
    TransitionRef,
    RecurrenceRef,
    PartialCueRef,
    DurabilityRef,
    FormationRef,
    RelationRef,
    ConsequenceRef,
    EpisodeContextRef,
);

fn resolve_transitions<R: EvidenceResolver>(
    references: &[TransitionRef],
    resolver: &R,
    meter: &mut ResourceMeter,
    event_generation: Option<u64>,
    permitted_participants: &BTreeSet<Lineage>,
) -> Result<Vec<TransitionBody>, EvidenceError> {
    if references.is_empty() {
        return Err(EvidenceError::MissingPhysicalTransition);
    }
    ensure_unique(references.iter().map(|value| value.receipt()))?;
    let mut bodies = Vec::with_capacity(references.len());
    for reference in references {
        let body = resolver
            .resolve_transition(*reference)
            .ok_or(EvidenceError::UnresolvedTransition(*reference))?;
        verify_reference(*reference, &body, meter)?;
        if !body.is_resolved_physical_change() {
            return Err(EvidenceError::UnresolvedOrNonconservedTransition);
        }
        if event_generation.is_some_and(|generation| body.successor_generation() != generation) {
            return Err(EvidenceError::EventGenerationMismatch);
        }
        if !permitted_participants.contains(&body.source())
            || !permitted_participants.contains(&body.target())
        {
            return Err(EvidenceError::TransitionLeavesParticipantSet);
        }
        bodies.push(body);
    }
    Ok(bodies)
}

#[allow(clippy::too_many_arguments)]
fn validate_collective_evidence<R: EvidenceResolver>(
    core: Receipt,
    formation_generation: u64,
    participants: &BTreeSet<Lineage>,
    participant_groups: &[BTreeSet<Lineage>],
    recurrence_floor: usize,
    recurrence_ref: RecurrenceRef,
    cue_ref: PartialCueRef,
    durability_ref: DurabilityRef,
    resolver: &R,
    meter: &mut ResourceMeter,
) -> Result<(), EvidenceError> {
    let recurrence = resolver
        .resolve_recurrence(recurrence_ref)
        .ok_or(EvidenceError::UnresolvedRecurrence(recurrence_ref))?;
    verify_reference(recurrence_ref, &recurrence, meter)?;
    if recurrence.formation_core_receipt != core
        || recurrence.event_generation <= formation_generation
    {
        return Err(EvidenceError::EvidenceTargetsDifferentFormation);
    }
    meter.refs(recurrence.transitions.len())?;
    let recurrence_transitions = resolve_transitions(
        &recurrence.transitions,
        resolver,
        meter,
        Some(recurrence.event_generation),
        participants,
    )?;
    let reached = recurrence_transitions
        .iter()
        .flat_map(|body| [body.source(), body.target()])
        .collect::<BTreeSet<_>>();
    if recurrence_floor == 3 && &reached != participants {
        return Err(EvidenceError::RecurrentComponentDoesNotEqualMembers);
    }
    let reached_groups = participant_groups
        .iter()
        .filter(|group| !group.is_disjoint(&reached))
        .count();
    if reached_groups < recurrence_floor {
        return Err(EvidenceError::CollectiveRecurrenceFloorNotMet);
    }

    let cue = resolver
        .resolve_partial_cue(cue_ref)
        .ok_or(EvidenceError::UnresolvedPartialCue(cue_ref))?;
    verify_reference(cue_ref, &cue, meter)?;
    if cue.formation_core_receipt != core || cue.event_generation <= formation_generation {
        return Err(EvidenceError::EvidenceTargetsDifferentFormation);
    }
    let directly_cued = cue.directly_cued.iter().copied().collect::<BTreeSet<_>>();
    let uncued_changed = cue.uncued_changed.iter().copied().collect::<BTreeSet<_>>();
    if directly_cued.is_empty()
        || uncued_changed.is_empty()
        || directly_cued.len() != cue.directly_cued.len()
        || uncued_changed.len() != cue.uncued_changed.len()
        || !directly_cued.is_disjoint(&uncued_changed)
        || !directly_cued.is_subset(participants)
        || !uncued_changed.is_subset(participants)
    {
        return Err(EvidenceError::PartialCueDoesNotIdentifyDistinctParticipants);
    }
    meter.refs(cue.transitions.len())?;
    let cue_transitions = resolve_transitions(
        &cue.transitions,
        resolver,
        meter,
        Some(cue.event_generation),
        participants,
    )?;
    let graph = transition_graph(&cue_transitions);
    let mut distinct_group_changed = false;
    for target in &uncued_changed {
        if !cue_transitions.iter().any(|body| body.target() == *target)
            || !directly_cued
                .iter()
                .any(|source| path_exists(*source, *target, &graph))
        {
            return Err(EvidenceError::UncuedParticipantNotCausallyChanged);
        }
        distinct_group_changed |= participant_groups
            .iter()
            .any(|group| group.contains(target) && group.is_disjoint(&directly_cued));
    }
    if !distinct_group_changed {
        return Err(EvidenceError::UncuedParticipantNotCausallyChanged);
    }

    let durability = resolver
        .resolve_durability(durability_ref)
        .ok_or(EvidenceError::UnresolvedDurability(durability_ref))?;
    verify_reference(durability_ref, &durability, meter)?;
    if durability.formation_core_receipt != core
        || durability.persisted_core_receipt != core
        || durability.reloaded_core_receipt != core
        || durability.persisted_generation < formation_generation
        || durability.restarted_generation <= durability.persisted_generation
        || durability.reuse_generation <= durability.restarted_generation
    {
        return Err(EvidenceError::DurabilityDoesNotReuseSameFormation);
    }
    meter.refs(durability.reuse_transitions.len())?;
    resolve_transitions(
        &durability.reuse_transitions,
        resolver,
        meter,
        Some(durability.reuse_generation),
        participants,
    )?;
    Ok(())
}

#[allow(clippy::too_many_arguments)]
fn validate_weave_consequence<R: EvidenceResolver>(
    body: &ConsequenceBody,
    core: Receipt,
    candidate: &RecursiveFormationCandidate,
    participant_groups: &[BTreeSet<Lineage>],
    participants: &BTreeSet<Lineage>,
    resolver: &R,
    meter: &mut ResourceMeter,
) -> Result<(), EvidenceError> {
    if body.formation_core_receipt != core
        || body.event_generation != candidate.generation
        || body.members.iter().copied().collect::<BTreeSet<_>>()
            != candidate.members.iter().copied().collect::<BTreeSet<_>>()
        || body.members.len() != candidate.members.len()
    {
        return Err(EvidenceError::WeaveConsequenceDoesNotUseMembers);
    }
    let roles = body
        .configurations
        .iter()
        .map(|value| value.role)
        .collect::<BTreeSet<_>>();
    if ![
        ConfigurationRole::Body,
        ConfigurationRole::Motor,
        ConfigurationRole::Sensory,
    ]
    .iter()
    .all(|role| roles.contains(role))
    {
        return Err(EvidenceError::WeaveConsequenceMissingConfiguration);
    }
    let configured = body
        .configurations
        .iter()
        .flat_map(|value| value.participant_lineages.iter().copied())
        .collect::<BTreeSet<_>>();
    if participant_groups
        .iter()
        .any(|group| group.is_disjoint(&configured))
    {
        return Err(EvidenceError::WeaveConsequenceDoesNotUseMembers);
    }
    meter.refs(body.transitions.len())?;
    let transitions = resolve_transitions(
        &body.transitions,
        resolver,
        meter,
        Some(body.event_generation),
        participants,
    )?;
    let transition_refs = body.transitions.iter().copied().collect::<BTreeSet<_>>();
    if !transition_refs.contains(&body.execution_transition)
        || !transition_refs.contains(&body.sensed_reentry_transition)
    {
        return Err(EvidenceError::WeaveConsequenceLacksCausalReentry);
    }
    for configuration in &body.configurations {
        if configuration.participant_lineages.is_empty()
            || configuration
                .participant_lineages
                .iter()
                .any(|lineage| !participants.contains(lineage))
            || configuration
                .transitions
                .iter()
                .any(|reference| !transition_refs.contains(reference))
        {
            return Err(EvidenceError::WeaveConsequenceMissingConfiguration);
        }
    }
    let motor = body
        .configurations
        .iter()
        .filter(|value| value.role == ConfigurationRole::Motor)
        .flat_map(|value| value.participant_lineages.iter().copied())
        .collect::<BTreeSet<_>>();
    let sensory = body
        .configurations
        .iter()
        .filter(|value| value.role == ConfigurationRole::Sensory)
        .flat_map(|value| value.participant_lineages.iter().copied())
        .collect::<BTreeSet<_>>();
    let graph = transition_graph(&transitions);
    let sensed = transitions
        .iter()
        .find(|value| value.reference() == body.sensed_reentry_transition)
        .ok_or(EvidenceError::WeaveConsequenceLacksCausalReentry)?;
    if !sensory.contains(&sensed.target())
        || !motor
            .iter()
            .any(|source| path_exists(*source, sensed.target(), &graph))
    {
        return Err(EvidenceError::WeaveConsequenceLacksCausalReentry);
    }
    Ok(())
}

fn ensure_unique(values: impl IntoIterator<Item = Receipt>) -> Result<(), EvidenceError> {
    let mut seen = BTreeSet::new();
    for value in values {
        if !seen.insert(value) {
            return Err(EvidenceError::DuplicateEvidenceReference);
        }
    }
    Ok(())
}

fn transition_graph(transitions: &[TransitionBody]) -> BTreeMap<Lineage, BTreeSet<Lineage>> {
    let mut graph = BTreeMap::new();
    for body in transitions {
        graph
            .entry(body.source())
            .or_insert_with(BTreeSet::new)
            .insert(body.target());
        graph.entry(body.target()).or_insert_with(BTreeSet::new);
    }
    graph
}

fn path_exists(
    source: Lineage,
    target: Lineage,
    graph: &BTreeMap<Lineage, BTreeSet<Lineage>>,
) -> bool {
    let mut seen = BTreeSet::new();
    let mut queue = VecDeque::from([source]);
    while let Some(current) = queue.pop_front() {
        if current == target {
            return true;
        }
        if !seen.insert(current) {
            continue;
        }
        if let Some(next) = graph.get(&current) {
            queue.extend(next.iter().copied());
        }
    }
    false
}

fn require_weak_formation_connection(
    members: &[FormationRef],
    edges: &BTreeSet<(FormationRef, FormationRef)>,
) -> Result<(), EvidenceError> {
    let mut graph: BTreeMap<FormationRef, BTreeSet<FormationRef>> = BTreeMap::new();
    for member in members {
        graph.insert(*member, BTreeSet::new());
    }
    for (source, target) in edges {
        graph.entry(*source).or_default().insert(*target);
        graph.entry(*target).or_default().insert(*source);
    }
    let mut seen = BTreeSet::new();
    let mut queue = VecDeque::from([members[0]]);
    while let Some(current) = queue.pop_front() {
        if seen.insert(current) {
            queue.extend(graph[&current].iter().copied());
        }
    }
    if seen.len() != members.len() {
        return Err(EvidenceError::FormationNotCausallyClosed);
    }
    Ok(())
}

fn member_kind_allowed(parent: FormationKind, member: FormationKind) -> bool {
    matches!(
        (parent, member),
        (FormationKind::MosaicOfMosaics, FormationKind::Mosaic)
            | (FormationKind::Tapestry, FormationKind::MosaicOfMosaics)
            | (FormationKind::TapestryOfTapestries, FormationKind::Tapestry)
            | (FormationKind::Weave, FormationKind::TapestryOfTapestries)
    )
}

fn relation_kind_for_parent(parent: FormationKind) -> RelationKind {
    match parent {
        FormationKind::MosaicOfMosaics => RelationKind::LearnedRelation,
        FormationKind::Tapestry | FormationKind::TapestryOfTapestries => {
            RelationKind::OrderedContinuation
        }
        FormationKind::Weave => RelationKind::GenerativeIntegration,
        FormationKind::Mosaic => RelationKind::LearnedRelation,
    }
}

fn finish_requirement(
    meter: &ResourceMeter,
    budget: FormationAdmissionBudget,
) -> Result<FormationAdmissionRequirement, EvidenceError> {
    let requirement = meter.requirement()?;
    if requirement.decoded_body_bytes > budget.max_decoded_body_bytes
        || requirement.total_bytes > budget.max_total_bytes
        || requirement.validation_terms > budget.max_validation_terms
    {
        return Err(EvidenceError::ResourceBudgetExceeded {
            required: requirement,
            budget,
        });
    }
    Ok(requirement)
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) enum EvidenceError {
    MosaicFloorNotMet(usize),
    RecursiveRelationNeedsTwoMembers,
    WrongAdmissionBoundary,
    DuplicateEvidenceReference,
    DuplicateParticipant,
    EmptyFormationParticipant,
    DuplicatePerspective,
    UnresolvedEpisodeContext(EpisodeContextRef),
    EpisodeGenerationMismatch,
    IncompleteEpisodeContext,
    FluidStatusContradictsState,
    NonCanonicalEpisodeParticipants,
    MemberDidNotParticipateInEpisode(Lineage),
    MemberCausalOccurrenceMismatch(Lineage),
    EpisodeMemberFractalMismatch(Lineage),
    LocalTransitionAuthorityMismatch(Lineage),
    UnresolvedFractal(FractalRef),
    UnresolvedTransition(TransitionRef),
    UnresolvedRecurrence(RecurrenceRef),
    UnresolvedPartialCue(PartialCueRef),
    UnresolvedDurability(DurabilityRef),
    UnresolvedFormation(FormationRef),
    FormationCycle,
    UnresolvedRelation(RelationRef),
    UnresolvedConsequence(ConsequenceRef),
    AuthorityDoesNotMatchDecodedBody,
    ResolvedReferenceChanged,
    MissingPhysicalTransition,
    MissingPhysicalComponentAuthority,
    UnresolvedOrNonconservedTransition,
    EventGenerationMismatch,
    TransitionLeavesParticipantSet,
    FormationNotCausallyClosed,
    CollectiveRecurrenceFloorNotMet,
    RecurrentComponentDoesNotEqualMembers,
    EvidenceTargetsDifferentFormation,
    PartialCueDoesNotIdentifyDistinctParticipants,
    UncuedParticipantNotCausallyChanged,
    DurabilityDoesNotReuseSameFormation,
    IllegalMemberKind {
        parent: FormationKind,
        member: FormationKind,
    },
    RelationKindDoesNotMatchParent,
    RelationLeavesFormationSet,
    RelationLacksCurrentPhysicalSupport,
    OrderedMembersDoNotMatch,
    MissingOrderedContinuation,
    MissingWeaveConsequence,
    ConsequenceOnlyBelongsToWeave,
    WeaveConsequenceDoesNotUseMembers,
    WeaveConsequenceMissingConfiguration,
    WeaveConsequenceLacksCausalReentry,
    ResourceOverflow,
    ResourceBudgetExceeded {
        required: FormationAdmissionRequirement,
        budget: FormationAdmissionBudget,
    },
}

impl fmt::Display for EvidenceError {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(formatter, "{self:?}")
    }
}

impl std::error::Error for EvidenceError {}
