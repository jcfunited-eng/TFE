//! Sparse, non-flattened cognitive-capital evidence inventory.
//!
//! Cognitive capital observes physically evidenced organism capability. It is
//! not a score, reward, decision authority, or second cognition system. Each
//! immutable credit preserves three orthogonal axes: one of the thirty-nine
//! ratified capabilities, the participating physical mechanism/path, and one
//! of ten evidence dimensions. Only observed axis combinations exist on disk.
//!
//! Complete causal evidence is stored once by content address. Ledger entries
//! contain its address and immutable lineage. Membership is a persistent,
//! path-compressed Patricia tree over that exact lineage.

pub use crate::immutable_evidence_store::{
    AddressedImmutableObject as AddressedObject, ContentAddress,
    ImmutableObjectResolver as ObjectResolver,
};
use crate::immutable_evidence_store::{
    BoundedImmutableDeltaBuilder, DeltaEnvelope, Error as ImmutableEvidenceError,
};
use std::collections::{BTreeMap, BTreeSet};
use std::fmt;
use std::sync::Arc;

const ENTRY_MAGIC: &[u8; 8] = b"GCCENT04";
const CAPABILITY_PAGE_MAGIC: &[u8; 8] = b"GCCCAP03";
const MECHANISM_PAGE_MAGIC: &[u8; 8] = b"GCCMEC03";
const PATRICIA_MAGIC: &[u8; 8] = b"GCCPAT03";
const VERSION: u16 = 3;
const LINEAGE_BITS: usize = 128;

pub type EvidenceLineage = [u8; 16];
pub type CausalAuthority = [u8; 32];

macro_rules! catalog {
    ($type_name:ident, $count:expr, $error:literal, {$($variant:ident => $name:literal),+ $(,)?}) => {
        #[derive(Clone, Copy, Debug, Eq, Ord, PartialEq, PartialOrd)]
        #[repr(u8)]
        pub enum $type_name { $($variant),+ }

        impl $type_name {
            pub const COUNT: usize = $count;
            pub const ALL: [Self; Self::COUNT] = [$(Self::$variant),+];
            pub const fn observational_name(self) -> &'static str {
                match self { $(Self::$variant => $name),+ }
            }
            fn code(self) -> u8 { self as u8 }
            fn from_code(code: u8) -> Result<Self, Error> {
                Self::ALL.get(code as usize).copied().ok_or(Error::Malformed($error))
            }
        }
    };
}

catalog!(Capability, 39, "capability code is outside the thirty-nine-row catalog", {
    Vision => "Vision",
    Hearing => "Hearing",
    Touch => "Touch",
    Temperature => "Temperature",
    Smell => "Smell",
    Taste => "Taste",
    ProprioceptionAndBodyPosition => "Proprioception and body position",
    VestibularBalance => "Vestibular balance",
    InteroceptionAndVisceralState => "Interoception and visceral state",
    MultisensoryIntegration => "Multisensory integration",
    RecognitionAndFamiliarity => "Recognition and familiarity",
    AttentionAndOrienting => "Attention and orienting",
    ImmediateCausalState => "Immediate causal state",
    EpisodicMemory => "Episodic memory",
    ProceduralAndPhysicalMemory => "Procedural and physical memory",
    Recall => "Recall",
    RelationalThought => "Relational thought",
    Prediction => "Prediction",
    DeliberationAndChoice => "Deliberation and choice",
    ImaginationAndSimulation => "Imagination and simulation",
    LanguageComprehension => "Language comprehension",
    SpeechAndArticulation => "Speech and articulation",
    OrderedThinking => "Ordered thinking",
    SocialCognitionAndOtherPerspective => "Social cognition and other-perspective",
    Empathy => "Empathy",
    EmotionAndAffect => "Emotion and affect",
    EmotionalBalanceAndRegulation => "Emotional balance and regulation",
    MotivationNeedsAndCuriosity => "Motivation, needs, and curiosity",
    SelfAndBodyContinuity => "Self and body continuity",
    MotorAndActuatorControl => "Motor and actuator control",
    NavigationAndAvoidance => "Navigation and avoidance",
    PlayAndExploration => "Play and exploration",
    SleepAndRest => "Sleep and rest",
    Dreaming => "Dreaming",
    Consolidation => "Consolidation",
    AutonomousCognitionAndAction => "Autonomous cognition and action",
    LearningAndDevelopmentalGrowth => "Learning and developmental growth",
    CreativityAndSelfExpression => "Creativity and self-expression",
    IntegratedPracticedCapability => "Integrated practiced capability",
});

// This is an orthogonal physical-observation axis. It does not stand in for a
// capability and is never converted into one by lookup or compatibility map.
catalog!(Mechanism, 40, "mechanism code is outside the forty-path catalog", {
    Recall => "Recall",
    CompositionAndSyntax => "Composition and syntax",
    Association => "Association",
    Retention => "Retention",
    CrossModalBinding => "Cross-modal binding",
    Habituation => "Habituation",
    RecognitionAndFamiliarity => "Recognition and familiarity",
    AttentionAndOrienting => "Attention and orienting",
    Sequence => "Sequence",
    ImaginationAndInternalSimulation => "Imagination and internal simulation",
    Reflection => "Reflection",
    WholeBrainIntegration => "Whole-brain integration",
    OtherMindModelling => "Other-mind modelling",
    AffectModulation => "Affect modulation",
    MetaMonitoring => "Meta-monitoring",
    ReceptorAndSensoryMechanics => "Receptor and sensory mechanics",
    SensoryCorticalOrganization => "Sensory cortical organization",
    ImmediateWorkingCausalState => "Immediate/working causal state",
    HippocampalIndexing => "Hippocampal indexing",
    NeocorticalDistributedRetention => "Neocortical distributed retention",
    PrefrontalOrderingAndDeliberation => "Prefrontal ordering and deliberation",
    AmygdalaAffectiveReach => "Amygdala/affective reach",
    EmotionAndRegulation => "Emotion and regulation",
    FluidBrainAndMetabolicRegulation => "Fluid brain and metabolic regulation",
    MotivationNeedsAndCuriosity => "Motivation, needs, and curiosity",
    Prediction => "Prediction",
    ChoiceAndActionPreparation => "Choice and action preparation",
    MotorBodyControl => "Motor/body control",
    SpeechAndArticulation => "Speech and articulation",
    LanguageComprehension => "Language comprehension",
    SelfBodyContinuity => "Self/body continuity",
    JointAttentionAndResponseBinding => "Joint attention and response binding",
    SocialCognitionAndEmpathy => "Social cognition and empathy",
    SleepAndRest => "Sleep and rest",
    DreamAndConsolidation => "Dream and consolidation",
    SubconsciousBackgroundCognition => "Subconscious/background cognition",
    AutonomyPlayAndExploration => "Autonomy, play, and exploration",
    NavigationAndAvoidance => "Navigation and avoidance",
    ProceduralCapability => "Procedural capability",
    CreativityAndSelfExpression => "Creativity and self-expression",
});

#[derive(Clone, Copy, Debug, Eq, Ord, PartialEq, PartialOrd)]
#[repr(u8)]
pub enum Dimension {
    Availability,
    Participation,
    Retention,
    Recognition,
    Recall,
    CausalUse,
    Transfer,
    AutonomousUse,
    Durability,
    IntegrationDepth,
}

impl Dimension {
    pub const COUNT: usize = 10;
    pub const ALL: [Self; Self::COUNT] = [
        Self::Availability,
        Self::Participation,
        Self::Retention,
        Self::Recognition,
        Self::Recall,
        Self::CausalUse,
        Self::Transfer,
        Self::AutonomousUse,
        Self::Durability,
        Self::IntegrationDepth,
    ];
    fn code(self) -> u8 {
        self as u8
    }
    fn from_code(code: u8) -> Result<Self, Error> {
        Self::ALL
            .get(code as usize)
            .copied()
            .ok_or(Error::Malformed(
                "capital dimension code is outside the ten-dimension catalog",
            ))
    }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum FormationDepth {
    // DSF delivery impressions are deliberately absent: they are observation
    // evidence, not retained formation or cognitive capital.
    Mosaic,
    MosaicOfMosaics,
    Tapestry,
    TapestryOfTapestries,
    Weave,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub enum DimensionEvidence {
    Availability {
        physical_path: CausalAuthority,
    },
    Participation {
        admitted_transition: CausalAuthority,
    },
    Retention {
        retained_structure: CausalAuthority,
        persistence: CausalAuthority,
    },
    Recognition {
        prior_structure: CausalAuthority,
        recurrence: CausalAuthority,
        changed_substrate: CausalAuthority,
    },
    Recall {
        lawful_cue: CausalAuthority,
        retained_structure: CausalAuthority,
        reactivation: CausalAuthority,
        original_occurrence_replayed: bool,
    },
    CausalUse {
        used_structure: CausalAuthority,
        changed_transition: CausalAuthority,
        returned_consequence: CausalAuthority,
    },
    Transfer {
        learned_structure: CausalAuthority,
        first_context: CausalAuthority,
        distinct_context: CausalAuthority,
        semantic_injection: bool,
    },
    AutonomousUse {
        endogenous_cause: CausalAuthority,
        use_transition: CausalAuthority,
        returned_consequence: CausalAuthority,
        operator_selected: bool,
    },
    Durability {
        retained_capital: CausalAuthority,
        sleep_or_consolidation: CausalAuthority,
        persistence_restart: CausalAuthority,
        later_reuse: CausalAuthority,
        identity_continuity: CausalAuthority,
    },
    IntegrationDepth {
        formation: CausalAuthority,
        depth: FormationDepth,
        causal_use: CausalAuthority,
    },
}

impl DimensionEvidence {
    fn dimension(&self) -> Dimension {
        match self {
            Self::Availability { .. } => Dimension::Availability,
            Self::Participation { .. } => Dimension::Participation,
            Self::Retention { .. } => Dimension::Retention,
            Self::Recognition { .. } => Dimension::Recognition,
            Self::Recall { .. } => Dimension::Recall,
            Self::CausalUse { .. } => Dimension::CausalUse,
            Self::Transfer { .. } => Dimension::Transfer,
            Self::AutonomousUse { .. } => Dimension::AutonomousUse,
            Self::Durability { .. } => Dimension::Durability,
            Self::IntegrationDepth { .. } => Dimension::IntegrationDepth,
        }
    }
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct EvidenceInspection {
    pub capability: Capability,
    pub mechanism: Mechanism,
    pub evidence_local_ordinal: u64,
    pub evidence_lineage: EvidenceLineage,
    pub evidence: DimensionEvidence,
}

pub trait CausalEvidenceDecoder {
    fn inspect_complete_evidence(&self, body: &[u8]) -> Result<EvidenceInspection, String>;
}

#[derive(Clone, Copy, Debug, Eq, Ord, PartialEq, PartialOrd)]
pub struct CapabilityPageRoot {
    pub capability: Capability,
    pub page: ContentAddress,
}

#[derive(Clone, Debug, Default, Eq, PartialEq)]
pub struct LedgerCheckpoint {
    pub latest_credit_ordinal: Option<u64>,
    pub capability_pages: Vec<CapabilityPageRoot>,
}

/// Internal staging carrier. Private axes prevent production callers from
/// inventing a capability, path, or dimension independently of sealed evidence.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct ProposedCredit {
    capability: Capability,
    mechanism: Mechanism,
    dimension: Dimension,
    complete_evidence_body: Vec<u8>,
}

pub(crate) fn proposed_native_credit(
    capability: Capability,
    mechanism: Mechanism,
    evidence: DimensionEvidence,
    evidence_local_ordinal: u64,
    evidence_lineage: EvidenceLineage,
    complete_evidence_body: Vec<u8>,
) -> Result<ProposedCredit, Error> {
    validate_dimension_evidence(&evidence)?;
    if evidence_local_ordinal == 0
        || evidence_lineage == [0; 16]
        || complete_evidence_body.is_empty()
    {
        return Err(Error::InvalidCausalEvidence(
            "native cognitive evidence lacks local ordinal, lineage, or body",
        ));
    }
    Ok(ProposedCredit {
        capability,
        mechanism,
        dimension: evidence.dimension(),
        complete_evidence_body,
    })
}

#[cfg(test)]
pub fn unmounted_test_credit(
    capability: Capability,
    mechanism: Mechanism,
    dimension: Dimension,
    complete_evidence_body: Vec<u8>,
) -> ProposedCredit {
    ProposedCredit {
        capability,
        mechanism,
        dimension,
        complete_evidence_body,
    }
}

#[cfg(test)]
pub fn unmounted_test_body_mut(credit: &mut ProposedCredit) -> &mut Vec<u8> {
    &mut credit.complete_evidence_body
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct PreparationEnvelope {
    pub max_resolved_bytes: usize,
    pub max_delta_objects: usize,
    pub max_delta_bytes: usize,
}

#[derive(Clone, Copy, Debug, Default, Eq, PartialEq)]
pub struct PreparationWork {
    pub resolved_bytes: usize,
    pub patricia_nodes_visited: usize,
    pub patricia_nodes_created: usize,
    pub evidence_objects_created: usize,
    pub entries_created: usize,
    pub mechanism_pages_created: usize,
    pub capability_pages_created: usize,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct PreparedLedgerDelta {
    pub objects: Vec<AddressedObject>,
    pub successor: LedgerCheckpoint,
    pub total_object_bytes: usize,
    pub work: PreparationWork,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub enum PreparedCapitalUpdate {
    NoCapitalEvent { unchanged: LedgerCheckpoint },
    Credits(PreparedLedgerDelta),
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct PageEnvelope {
    pub max_entries: usize,
    pub max_decoded_bytes: usize,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct PageCursor {
    pub mechanism_page: ContentAddress,
    pub capability: Capability,
    pub mechanism: Mechanism,
    pub dimension: Dimension,
    pub next_entry: ContentAddress,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct CreditedEvidence {
    pub entry_address: ContentAddress,
    pub evidence_address: ContentAddress,
    pub credit_ordinal: u64,
    pub evidence_local_ordinal: u64,
    pub evidence_lineage: EvidenceLineage,
    pub complete_evidence_body: Vec<u8>,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct EvidencePage {
    pub entries: Vec<CreditedEvidence>,
    pub continuation: Option<PageCursor>,
    pub decoded_bytes: usize,
    pub exact_inventory_count: u64,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub enum Error {
    EmptyEnvelope,
    ArithmeticOverflow,
    MissingObject(ContentAddress),
    AddressContentDivergence(ContentAddress),
    ResolvedByteBudgetExceeded,
    DeltaObjectBudgetExceeded,
    DeltaByteBudgetExceeded,
    Malformed(&'static str),
    TypedEvidence(String),
    EvidenceTypeMismatch,
    InvalidCausalEvidence(&'static str),
    DuplicateCredit,
    NonCanonicalOrder,
    NonIncreasingCreditOrdinal,
    CursorMismatch,
    NoEvidence,
}

impl fmt::Display for Error {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "{self:?}")
    }
}
impl std::error::Error for Error {}

#[derive(Clone, Copy)]
struct Entry {
    capability: Capability,
    mechanism: Mechanism,
    dimension: Dimension,
    credit_ordinal: u64,
    evidence_lineage: EvidenceLineage,
    evidence_address: ContentAddress,
    prior: Option<ContentAddress>,
}

#[derive(Clone, Copy, Default)]
struct DimensionHead {
    latest: Option<ContentAddress>,
    membership_root: Option<ContentAddress>,
    inventory_count: u64,
}

#[derive(Clone, Copy)]
struct DimensionRecord {
    dimension: Dimension,
    head: DimensionHead,
}

#[derive(Clone)]
struct MechanismPage {
    capability: Capability,
    mechanism: Mechanism,
    dimensions: Vec<DimensionRecord>,
}

#[derive(Clone, Copy)]
struct MechanismPageRoot {
    mechanism: Mechanism,
    page: ContentAddress,
}

#[derive(Clone)]
struct CapabilityPage {
    capability: Capability,
    mechanisms: Vec<MechanismPageRoot>,
}

#[derive(Clone, Copy)]
enum PatriciaNode {
    Leaf {
        key: EvidenceLineage,
        value: ContentAddress,
    },
    Branch {
        prefix_bits: u16,
        prefix: EvidenceLineage,
        left: ContentAddress,
        right: ContentAddress,
    },
}

struct Builder {
    shared: BoundedImmutableDeltaBuilder,
}
impl Builder {
    fn new(envelope: PreparationEnvelope) -> Result<Self, Error> {
        Ok(Self {
            shared: BoundedImmutableDeltaBuilder::new(DeltaEnvelope {
                max_objects: envelope.max_delta_objects,
                max_object_bytes: envelope.max_delta_bytes,
            })
            .map_err(map_immutable_error)?,
        })
    }
    fn add(&mut self, bytes: Vec<u8>) -> Result<ContentAddress, Error> {
        self.shared.add(bytes).map_err(map_immutable_error)
    }
    fn objects(&self) -> &BTreeMap<ContentAddress, Arc<[u8]>> {
        self.shared.objects()
    }
    fn finish(self) -> Result<crate::immutable_evidence_store::ImmutableDelta, Error> {
        self.shared.finish().map_err(map_immutable_error)
    }
}

fn map_immutable_error(error: ImmutableEvidenceError) -> Error {
    match error {
        ImmutableEvidenceError::EmptyEnvelope => Error::EmptyEnvelope,
        ImmutableEvidenceError::ArithmeticOverflow => Error::ArithmeticOverflow,
        ImmutableEvidenceError::ObjectBudgetExceeded { .. } => Error::DeltaObjectBudgetExceeded,
        ImmutableEvidenceError::ByteBudgetExceeded { .. } => Error::DeltaByteBudgetExceeded,
        ImmutableEvidenceError::AddressBodyMismatch { declared, .. }
        | ImmutableEvidenceError::AddressCollision(declared) => {
            Error::AddressContentDivergence(declared)
        }
        ImmutableEvidenceError::NonCanonicalReplay
        | ImmutableEvidenceError::ReplayRootMismatch { .. } => {
            Error::Malformed("immutable evidence replay diverged")
        }
    }
}

struct Context<'a, R: ObjectResolver> {
    resolver: &'a R,
    resolved: usize,
    max_resolved: usize,
}
impl<R: ObjectResolver> Context<'_, R> {
    fn load(
        &mut self,
        address: ContentAddress,
        overlay: &BTreeMap<ContentAddress, Arc<[u8]>>,
    ) -> Result<Arc<[u8]>, Error> {
        let bytes = overlay
            .get(&address)
            .cloned()
            .or_else(|| self.resolver.resolve(address))
            .ok_or(Error::MissingObject(address))?;
        if ContentAddress::of(&bytes) != address {
            return Err(Error::AddressContentDivergence(address));
        }
        let required = self
            .resolved
            .checked_add(bytes.len())
            .ok_or(Error::ArithmeticOverflow)?;
        if required > self.max_resolved {
            return Err(Error::ResolvedByteBudgetExceeded);
        }
        self.resolved = required;
        Ok(bytes)
    }
}

pub fn prepare_credits<R: ObjectResolver, D: CausalEvidenceDecoder>(
    prior: LedgerCheckpoint,
    credit_ordinal: u64,
    credits: &[ProposedCredit],
    resolver: &R,
    decoder: &D,
    envelope: PreparationEnvelope,
) -> Result<PreparedCapitalUpdate, Error> {
    if credits.is_empty() {
        return Ok(PreparedCapitalUpdate::NoCapitalEvent { unchanged: prior });
    }
    if envelope.max_resolved_bytes == 0
        || envelope.max_delta_objects == 0
        || envelope.max_delta_bytes == 0
    {
        return Err(Error::EmptyEnvelope);
    }
    validate_checkpoint(&prior)?;
    if prior
        .latest_credit_ordinal
        .is_some_and(|value| value >= credit_ordinal)
    {
        return Err(Error::NonIncreasingCreditOrdinal);
    }

    let mut decoded = Vec::with_capacity(credits.len());
    let mut batch_keys = BTreeSet::new();
    for credit in credits {
        let inspected = decoder
            .inspect_complete_evidence(&credit.complete_evidence_body)
            .map_err(Error::TypedEvidence)?;
        if inspected.capability != credit.capability
            || inspected.mechanism != credit.mechanism
            || inspected.evidence.dimension() != credit.dimension
        {
            return Err(Error::EvidenceTypeMismatch);
        }
        validate_dimension_evidence(&inspected.evidence)?;
        let key = (
            credit.capability,
            credit.mechanism,
            credit.dimension,
            inspected.evidence_lineage,
        );
        if !batch_keys.insert(key) {
            return Err(Error::DuplicateCredit);
        }
        decoded.push(inspected);
    }
    if decoded
        .windows(2)
        .any(|pair| inspection_key(&pair[0]) > inspection_key(&pair[1]))
    {
        return Err(Error::NonCanonicalOrder);
    }

    let mut builder = Builder::new(envelope)?;
    let mut context = Context {
        resolver,
        resolved: 0,
        max_resolved: envelope.max_resolved_bytes,
    };
    let mut checkpoint = prior;
    let mut work = PreparationWork::default();
    let mut index = 0;
    while index < credits.len() {
        let capability = credits[index].capability;
        let cap_position = checkpoint
            .capability_pages
            .binary_search_by_key(&capability, |root| root.capability);
        let mut capability_page = match cap_position {
            Ok(position) => decode_capability_page(&context.load(
                checkpoint.capability_pages[position].page,
                builder.objects(),
            )?)?,
            Err(_) => CapabilityPage {
                capability,
                mechanisms: Vec::new(),
            },
        };
        if capability_page.capability != capability {
            return Err(Error::Malformed("capability page identity changed"));
        }

        while index < credits.len() && credits[index].capability == capability {
            let mechanism = credits[index].mechanism;
            let mechanism_position = capability_page
                .mechanisms
                .binary_search_by_key(&mechanism, |root| root.mechanism);
            let mut page = match mechanism_position {
                Ok(position) => decode_mechanism_page(
                    &context.load(capability_page.mechanisms[position].page, builder.objects())?,
                )?,
                Err(_) => MechanismPage {
                    capability,
                    mechanism,
                    dimensions: Vec::new(),
                },
            };
            if page.capability != capability || page.mechanism != mechanism {
                return Err(Error::Malformed("mechanism page axes changed"));
            }

            while index < credits.len()
                && credits[index].capability == capability
                && credits[index].mechanism == mechanism
            {
                let credit = &credits[index];
                let inspected = &decoded[index];
                let dimension_position = page
                    .dimensions
                    .binary_search_by_key(&credit.dimension, |record| record.dimension);
                let mut record = match dimension_position {
                    Ok(position) => page.dimensions[position],
                    Err(_) => DimensionRecord {
                        dimension: credit.dimension,
                        head: DimensionHead::default(),
                    },
                };
                let (found, visited) = membership_lookup(
                    record.head.membership_root,
                    inspected.evidence_lineage,
                    &mut context,
                    builder.objects(),
                )?;
                work.patricia_nodes_visited = work
                    .patricia_nodes_visited
                    .checked_add(visited)
                    .ok_or(Error::ArithmeticOverflow)?;
                if found.is_some() {
                    return Err(Error::DuplicateCredit);
                }
                if let Some(latest) = record.head.latest {
                    let previous = decode_entry(&context.load(latest, builder.objects())?)?;
                    let staged = builder.objects().contains_key(&latest);
                    if previous.credit_ordinal > credit_ordinal
                        || (previous.credit_ordinal == credit_ordinal && !staged)
                    {
                        return Err(Error::NonIncreasingCreditOrdinal);
                    }
                }
                let evidence_address = stage_evidence_body(
                    &credit.complete_evidence_body,
                    &mut context,
                    &mut builder,
                    &mut work,
                )?;
                let entry_address = builder.add(encode_entry(Entry {
                    capability,
                    mechanism,
                    dimension: credit.dimension,
                    credit_ordinal,
                    evidence_lineage: inspected.evidence_lineage,
                    evidence_address,
                    prior: record.head.latest,
                }))?;
                record.head.membership_root = Some(patricia_insert(
                    record.head.membership_root,
                    inspected.evidence_lineage,
                    entry_address,
                    &mut context,
                    &mut builder,
                    &mut work,
                )?);
                record.head.latest = Some(entry_address);
                record.head.inventory_count = record
                    .head
                    .inventory_count
                    .checked_add(1)
                    .ok_or(Error::ArithmeticOverflow)?;
                match dimension_position {
                    Ok(position) => page.dimensions[position] = record,
                    Err(position) => page.dimensions.insert(position, record),
                }
                work.entries_created = work
                    .entries_created
                    .checked_add(1)
                    .ok_or(Error::ArithmeticOverflow)?;
                index += 1;
            }
            let page_address = builder.add(encode_mechanism_page(&page))?;
            match mechanism_position {
                Ok(position) => capability_page.mechanisms[position].page = page_address,
                Err(position) => capability_page.mechanisms.insert(
                    position,
                    MechanismPageRoot {
                        mechanism,
                        page: page_address,
                    },
                ),
            }
            work.mechanism_pages_created = work
                .mechanism_pages_created
                .checked_add(1)
                .ok_or(Error::ArithmeticOverflow)?;
        }
        let cap_address = builder.add(encode_capability_page(&capability_page))?;
        match cap_position {
            Ok(position) => checkpoint.capability_pages[position].page = cap_address,
            Err(position) => checkpoint.capability_pages.insert(
                position,
                CapabilityPageRoot {
                    capability,
                    page: cap_address,
                },
            ),
        }
        work.capability_pages_created = work
            .capability_pages_created
            .checked_add(1)
            .ok_or(Error::ArithmeticOverflow)?;
    }
    checkpoint.latest_credit_ordinal = Some(credit_ordinal);
    work.resolved_bytes = context.resolved;
    let delta = builder.finish()?;
    Ok(PreparedCapitalUpdate::Credits(PreparedLedgerDelta {
        total_object_bytes: delta.accounting.total_object_bytes,
        objects: delta.objects,
        successor: checkpoint,
        work,
    }))
}

fn inspection_key(
    value: &EvidenceInspection,
) -> (Capability, Mechanism, Dimension, EvidenceLineage) {
    (
        value.capability,
        value.mechanism,
        value.evidence.dimension(),
        value.evidence_lineage,
    )
}

fn validate_checkpoint(value: &LedgerCheckpoint) -> Result<(), Error> {
    if value
        .capability_pages
        .windows(2)
        .any(|pair| pair[0].capability >= pair[1].capability)
    {
        return Err(Error::NonCanonicalOrder);
    }
    Ok(())
}

fn stage_evidence_body<R: ObjectResolver>(
    body: &[u8],
    context: &mut Context<'_, R>,
    builder: &mut Builder,
    work: &mut PreparationWork,
) -> Result<ContentAddress, Error> {
    let address = ContentAddress::of(body);
    if builder.objects().contains_key(&address) {
        return Ok(address);
    }
    if let Some(existing) = context.resolver.resolve(address) {
        if ContentAddress::of(&existing) != address || existing.as_ref() != body {
            return Err(Error::AddressContentDivergence(address));
        }
        let required = context
            .resolved
            .checked_add(existing.len())
            .ok_or(Error::ArithmeticOverflow)?;
        if required > context.max_resolved {
            return Err(Error::ResolvedByteBudgetExceeded);
        }
        context.resolved = required;
        return Ok(address);
    }
    let staged = builder.add(body.to_vec())?;
    if staged != address {
        return Err(Error::AddressContentDivergence(address));
    }
    work.evidence_objects_created = work
        .evidence_objects_created
        .checked_add(1)
        .ok_or(Error::ArithmeticOverflow)?;
    Ok(address)
}

pub fn page_evidence<R: ObjectResolver, D: CausalEvidenceDecoder>(
    checkpoint: &LedgerCheckpoint,
    capability: Capability,
    mechanism: Mechanism,
    dimension: Dimension,
    cursor: Option<PageCursor>,
    resolver: &R,
    decoder: &D,
    envelope: PageEnvelope,
) -> Result<EvidencePage, Error> {
    if envelope.max_entries == 0 || envelope.max_decoded_bytes == 0 {
        return Err(Error::EmptyEnvelope);
    }
    validate_checkpoint(checkpoint)?;
    let cap_root = checkpoint
        .capability_pages
        .binary_search_by_key(&capability, |root| root.capability)
        .ok()
        .map(|position| checkpoint.capability_pages[position])
        .ok_or(Error::NoEvidence)?;
    let empty = BTreeMap::new();
    let mut context = Context {
        resolver,
        resolved: 0,
        max_resolved: envelope.max_decoded_bytes,
    };
    let cap_page = decode_capability_page(&context.load(cap_root.page, &empty)?)?;
    if cap_page.capability != capability {
        return Err(Error::EvidenceTypeMismatch);
    }
    let mechanism_root = cap_page
        .mechanisms
        .binary_search_by_key(&mechanism, |root| root.mechanism)
        .ok()
        .map(|position| cap_page.mechanisms[position])
        .ok_or(Error::NoEvidence)?;
    let page = decode_mechanism_page(&context.load(mechanism_root.page, &empty)?)?;
    if page.capability != capability || page.mechanism != mechanism {
        return Err(Error::EvidenceTypeMismatch);
    }
    let head = page
        .dimensions
        .binary_search_by_key(&dimension, |record| record.dimension)
        .ok()
        .map(|position| page.dimensions[position].head)
        .ok_or(Error::NoEvidence)?;
    let mut next = match cursor {
        None => head.latest,
        Some(value)
            if value.mechanism_page == mechanism_root.page
                && value.capability == capability
                && value.mechanism == mechanism
                && value.dimension == dimension =>
        {
            Some(value.next_entry)
        }
        Some(_) => return Err(Error::CursorMismatch),
    };
    let mut entries = Vec::new();
    while let Some(address) = next {
        if entries.len() == envelope.max_entries {
            break;
        }
        let before = context.resolved;
        let result = (|| {
            let entry = decode_entry(&context.load(address, &empty)?)?;
            if entry.capability != capability
                || entry.mechanism != mechanism
                || entry.dimension != dimension
            {
                return Err(Error::EvidenceTypeMismatch);
            }
            let body = context.load(entry.evidence_address, &empty)?;
            let inspected = decoder
                .inspect_complete_evidence(&body)
                .map_err(Error::TypedEvidence)?;
            if inspected.capability != capability
                || inspected.mechanism != mechanism
                || inspected.evidence.dimension() != dimension
                || inspected.evidence_lineage != entry.evidence_lineage
            {
                return Err(Error::EvidenceTypeMismatch);
            }
            validate_dimension_evidence(&inspected.evidence)?;
            Ok((entry, body, inspected.evidence_local_ordinal))
        })();
        let (entry, body, evidence_local_ordinal) = match result {
            Ok(value) => value,
            Err(Error::ResolvedByteBudgetExceeded) if !entries.is_empty() => {
                context.resolved = before;
                break;
            }
            Err(error) => return Err(error),
        };
        next = entry.prior;
        entries.push(CreditedEvidence {
            entry_address: address,
            evidence_address: entry.evidence_address,
            credit_ordinal: entry.credit_ordinal,
            evidence_local_ordinal,
            evidence_lineage: entry.evidence_lineage,
            complete_evidence_body: body.as_ref().to_vec(),
        });
    }
    Ok(EvidencePage {
        entries,
        continuation: next.map(|next_entry| PageCursor {
            mechanism_page: mechanism_root.page,
            capability,
            mechanism,
            dimension,
            next_entry,
        }),
        decoded_bytes: context.resolved,
        exact_inventory_count: head.inventory_count,
    })
}

fn validate_dimension_evidence(value: &DimensionEvidence) -> Result<(), Error> {
    let nonzero = |authority: &CausalAuthority| authority.iter().any(|byte| *byte != 0);
    let valid = match value {
        DimensionEvidence::Availability { physical_path } => nonzero(physical_path),
        DimensionEvidence::Participation {
            admitted_transition,
        } => nonzero(admitted_transition),
        DimensionEvidence::Retention {
            retained_structure,
            persistence,
        } => nonzero(retained_structure) && nonzero(persistence),
        DimensionEvidence::Recognition {
            prior_structure,
            recurrence,
            changed_substrate,
        } => nonzero(prior_structure) && nonzero(recurrence) && nonzero(changed_substrate),
        DimensionEvidence::Recall {
            lawful_cue,
            retained_structure,
            reactivation,
            original_occurrence_replayed,
        } => {
            nonzero(lawful_cue)
                && nonzero(retained_structure)
                && nonzero(reactivation)
                && !original_occurrence_replayed
        }
        DimensionEvidence::CausalUse {
            used_structure,
            changed_transition,
            returned_consequence,
        } => {
            nonzero(used_structure) && nonzero(changed_transition) && nonzero(returned_consequence)
        }
        DimensionEvidence::Transfer {
            learned_structure,
            first_context,
            distinct_context,
            semantic_injection,
        } => {
            nonzero(learned_structure)
                && nonzero(first_context)
                && nonzero(distinct_context)
                && first_context != distinct_context
                && !semantic_injection
        }
        DimensionEvidence::AutonomousUse {
            endogenous_cause,
            use_transition,
            returned_consequence,
            operator_selected,
        } => {
            nonzero(endogenous_cause)
                && nonzero(use_transition)
                && nonzero(returned_consequence)
                && !operator_selected
        }
        DimensionEvidence::Durability {
            retained_capital,
            sleep_or_consolidation,
            persistence_restart,
            later_reuse,
            identity_continuity,
        } => [
            retained_capital,
            sleep_or_consolidation,
            persistence_restart,
            later_reuse,
            identity_continuity,
        ]
        .into_iter()
        .all(nonzero),
        DimensionEvidence::IntegrationDepth {
            formation,
            causal_use,
            ..
        } => nonzero(formation) && nonzero(causal_use),
    };
    if valid {
        Ok(())
    } else {
        Err(Error::InvalidCausalEvidence(
            "dimension evidence lacks its required causal body",
        ))
    }
}

fn membership_lookup<R: ObjectResolver>(
    root: Option<ContentAddress>,
    key: EvidenceLineage,
    context: &mut Context<'_, R>,
    overlay: &BTreeMap<ContentAddress, Arc<[u8]>>,
) -> Result<(Option<ContentAddress>, usize), Error> {
    let Some(mut current) = root else {
        return Ok((None, 0));
    };
    let mut visited = 0usize;
    loop {
        let node = decode_patricia(&context.load(current, overlay)?)?;
        visited = visited.checked_add(1).ok_or(Error::ArithmeticOverflow)?;
        match node {
            PatriciaNode::Leaf {
                key: candidate,
                value,
            } => return Ok((if candidate == key { Some(value) } else { None }, visited)),
            PatriciaNode::Branch {
                prefix_bits,
                prefix,
                left,
                right,
            } => {
                if !prefix_matches(key, prefix, prefix_bits as usize) {
                    return Ok((None, visited));
                }
                current = if bit(key, prefix_bits as usize) {
                    right
                } else {
                    left
                };
            }
        }
    }
}

fn patricia_insert<R: ObjectResolver>(
    root: Option<ContentAddress>,
    key: EvidenceLineage,
    value: ContentAddress,
    context: &mut Context<'_, R>,
    builder: &mut Builder,
    work: &mut PreparationWork,
) -> Result<ContentAddress, Error> {
    let Some(root_address) = root else {
        work.patricia_nodes_created = work
            .patricia_nodes_created
            .checked_add(1)
            .ok_or(Error::ArithmeticOverflow)?;
        return builder.add(encode_patricia(PatriciaNode::Leaf { key, value }));
    };
    let node = decode_patricia(&context.load(root_address, builder.objects())?)?;
    work.patricia_nodes_visited = work
        .patricia_nodes_visited
        .checked_add(1)
        .ok_or(Error::ArithmeticOverflow)?;
    match node {
        PatriciaNode::Leaf { key: existing, .. } => {
            if existing == key {
                return Err(Error::DuplicateCredit);
            }
            split_with_new_leaf(root_address, existing, key, value, builder, work)
        }
        PatriciaNode::Branch {
            prefix_bits,
            prefix,
            left,
            right,
        } => {
            let bits = prefix_bits as usize;
            if !prefix_matches(key, prefix, bits) {
                return split_with_new_leaf(root_address, prefix, key, value, builder, work);
            }
            let (new_left, new_right) = if bit(key, bits) {
                (
                    left,
                    patricia_insert(Some(right), key, value, context, builder, work)?,
                )
            } else {
                (
                    patricia_insert(Some(left), key, value, context, builder, work)?,
                    right,
                )
            };
            work.patricia_nodes_created = work
                .patricia_nodes_created
                .checked_add(1)
                .ok_or(Error::ArithmeticOverflow)?;
            builder.add(encode_patricia(PatriciaNode::Branch {
                prefix_bits,
                prefix,
                left: new_left,
                right: new_right,
            }))
        }
    }
}

fn split_with_new_leaf(
    existing_root: ContentAddress,
    representative: EvidenceLineage,
    key: EvidenceLineage,
    value: ContentAddress,
    builder: &mut Builder,
    work: &mut PreparationWork,
) -> Result<ContentAddress, Error> {
    let common = common_prefix_bits(representative, key);
    if common >= LINEAGE_BITS {
        return Err(Error::DuplicateCredit);
    }
    let leaf = builder.add(encode_patricia(PatriciaNode::Leaf { key, value }))?;
    let (left, right) = if bit(key, common) {
        (existing_root, leaf)
    } else {
        (leaf, existing_root)
    };
    work.patricia_nodes_created = work
        .patricia_nodes_created
        .checked_add(2)
        .ok_or(Error::ArithmeticOverflow)?;
    builder.add(encode_patricia(PatriciaNode::Branch {
        prefix_bits: common as u16,
        prefix: masked_prefix(key, common),
        left,
        right,
    }))
}

fn common_prefix_bits(left: EvidenceLineage, right: EvidenceLineage) -> usize {
    for (index, (a, b)) in left.into_iter().zip(right).enumerate() {
        let changed = a ^ b;
        if changed != 0 {
            return index * 8 + changed.leading_zeros() as usize;
        }
    }
    LINEAGE_BITS
}
fn bit(key: EvidenceLineage, index: usize) -> bool {
    key[index / 8] & (0x80 >> (index % 8)) != 0
}
fn masked_prefix(mut key: EvidenceLineage, bits: usize) -> EvidenceLineage {
    if bits >= LINEAGE_BITS {
        return key;
    }
    let byte = bits / 8;
    let within = bits % 8;
    if within == 0 {
        key[byte..].fill(0);
    } else {
        key[byte] &= 0xff << (8 - within);
        key[byte + 1..].fill(0);
    }
    key
}
fn prefix_matches(key: EvidenceLineage, prefix: EvidenceLineage, bits: usize) -> bool {
    bits <= LINEAGE_BITS && masked_prefix(key, bits) == prefix
}

fn encode_entry(value: Entry) -> Vec<u8> {
    let mut out = Vec::new();
    out.extend_from_slice(ENTRY_MAGIC);
    out.extend_from_slice(&VERSION.to_le_bytes());
    out.push(value.capability.code());
    out.push(value.mechanism.code());
    out.push(value.dimension.code());
    out.extend_from_slice(&value.credit_ordinal.to_le_bytes());
    out.extend_from_slice(&value.evidence_lineage);
    out.extend_from_slice(&value.evidence_address.0);
    push_address(&mut out, value.prior);
    out
}
fn decode_entry(bytes: &[u8]) -> Result<Entry, Error> {
    let mut parser = Parser::new(bytes);
    parser.magic(ENTRY_MAGIC)?;
    parser.version()?;
    let value = Entry {
        capability: Capability::from_code(parser.u8()?)?,
        mechanism: Mechanism::from_code(parser.u8()?)?,
        dimension: Dimension::from_code(parser.u8()?)?,
        credit_ordinal: parser.u64()?,
        evidence_lineage: parser.lineage()?,
        evidence_address: parser.address()?,
        prior: parser.optional_address()?,
    };
    parser.finish()?;
    Ok(value)
}

fn encode_capability_page(value: &CapabilityPage) -> Vec<u8> {
    let mut out = Vec::new();
    out.extend_from_slice(CAPABILITY_PAGE_MAGIC);
    out.extend_from_slice(&VERSION.to_le_bytes());
    out.push(value.capability.code());
    out.extend_from_slice(&(value.mechanisms.len() as u16).to_le_bytes());
    for root in &value.mechanisms {
        out.push(root.mechanism.code());
        out.extend_from_slice(&root.page.0);
    }
    out
}
fn decode_capability_page(bytes: &[u8]) -> Result<CapabilityPage, Error> {
    let mut parser = Parser::new(bytes);
    parser.magic(CAPABILITY_PAGE_MAGIC)?;
    parser.version()?;
    let capability = Capability::from_code(parser.u8()?)?;
    let count = parser.u16()? as usize;
    if count == 0 || count > Mechanism::COUNT {
        return Err(Error::Malformed(
            "capability page has invalid sparse mechanism count",
        ));
    }
    let mut mechanisms = Vec::with_capacity(count);
    for _ in 0..count {
        mechanisms.push(MechanismPageRoot {
            mechanism: Mechanism::from_code(parser.u8()?)?,
            page: parser.address()?,
        });
    }
    if mechanisms
        .windows(2)
        .any(|pair| pair[0].mechanism >= pair[1].mechanism)
    {
        return Err(Error::NonCanonicalOrder);
    }
    parser.finish()?;
    Ok(CapabilityPage {
        capability,
        mechanisms,
    })
}

fn encode_mechanism_page(value: &MechanismPage) -> Vec<u8> {
    let mut out = Vec::new();
    out.extend_from_slice(MECHANISM_PAGE_MAGIC);
    out.extend_from_slice(&VERSION.to_le_bytes());
    out.push(value.capability.code());
    out.push(value.mechanism.code());
    out.push(value.dimensions.len() as u8);
    for record in &value.dimensions {
        out.push(record.dimension.code());
        push_address(&mut out, record.head.latest);
        push_address(&mut out, record.head.membership_root);
        out.extend_from_slice(&record.head.inventory_count.to_le_bytes());
    }
    out
}
fn decode_mechanism_page(bytes: &[u8]) -> Result<MechanismPage, Error> {
    let mut parser = Parser::new(bytes);
    parser.magic(MECHANISM_PAGE_MAGIC)?;
    parser.version()?;
    let capability = Capability::from_code(parser.u8()?)?;
    let mechanism = Mechanism::from_code(parser.u8()?)?;
    let count = parser.u8()? as usize;
    if count == 0 || count > Dimension::COUNT {
        return Err(Error::Malformed(
            "mechanism page has invalid sparse dimension count",
        ));
    }
    let mut dimensions = Vec::with_capacity(count);
    for _ in 0..count {
        let dimension = Dimension::from_code(parser.u8()?)?;
        let head = DimensionHead {
            latest: parser.optional_address()?,
            membership_root: parser.optional_address()?,
            inventory_count: parser.u64()?,
        };
        if head.latest.is_none() || head.membership_root.is_none() || head.inventory_count == 0 {
            return Err(Error::Malformed("sparse dimension head is empty"));
        }
        dimensions.push(DimensionRecord { dimension, head });
    }
    if dimensions
        .windows(2)
        .any(|pair| pair[0].dimension >= pair[1].dimension)
    {
        return Err(Error::NonCanonicalOrder);
    }
    parser.finish()?;
    Ok(MechanismPage {
        capability,
        mechanism,
        dimensions,
    })
}

fn encode_patricia(value: PatriciaNode) -> Vec<u8> {
    let mut out = Vec::new();
    out.extend_from_slice(PATRICIA_MAGIC);
    out.extend_from_slice(&VERSION.to_le_bytes());
    match value {
        PatriciaNode::Leaf { key, value } => {
            out.push(0);
            out.extend_from_slice(&key);
            out.extend_from_slice(&value.0);
        }
        PatriciaNode::Branch {
            prefix_bits,
            prefix,
            left,
            right,
        } => {
            out.push(1);
            out.extend_from_slice(&prefix_bits.to_le_bytes());
            out.extend_from_slice(&prefix);
            out.extend_from_slice(&left.0);
            out.extend_from_slice(&right.0);
        }
    }
    out
}
fn decode_patricia(bytes: &[u8]) -> Result<PatriciaNode, Error> {
    let mut parser = Parser::new(bytes);
    parser.magic(PATRICIA_MAGIC)?;
    parser.version()?;
    let node = match parser.u8()? {
        0 => PatriciaNode::Leaf {
            key: parser.lineage()?,
            value: parser.address()?,
        },
        1 => {
            let prefix_bits = parser.u16()?;
            let prefix = parser.lineage()?;
            let left = parser.address()?;
            let right = parser.address()?;
            if prefix_bits as usize >= LINEAGE_BITS
                || masked_prefix(prefix, prefix_bits as usize) != prefix
                || left == right
            {
                return Err(Error::Malformed("Patricia branch is noncanonical"));
            }
            PatriciaNode::Branch {
                prefix_bits,
                prefix,
                left,
                right,
            }
        }
        _ => return Err(Error::Malformed("Patricia node kind is invalid")),
    };
    parser.finish()?;
    Ok(node)
}

struct Parser<'a> {
    bytes: &'a [u8],
    offset: usize,
}
impl<'a> Parser<'a> {
    fn new(bytes: &'a [u8]) -> Self {
        Self { bytes, offset: 0 }
    }
    fn take(&mut self, count: usize) -> Result<&'a [u8], Error> {
        let end = self
            .offset
            .checked_add(count)
            .ok_or(Error::ArithmeticOverflow)?;
        if end > self.bytes.len() {
            return Err(Error::Malformed("addressed object ended early"));
        }
        let value = &self.bytes[self.offset..end];
        self.offset = end;
        Ok(value)
    }
    fn magic(&mut self, expected: &[u8; 8]) -> Result<(), Error> {
        if self.take(8)? != expected {
            return Err(Error::Malformed("addressed object has wrong typed magic"));
        }
        Ok(())
    }
    fn version(&mut self) -> Result<(), Error> {
        if self.u16()? != VERSION {
            return Err(Error::Malformed("addressed object version is invalid"));
        }
        Ok(())
    }
    fn u8(&mut self) -> Result<u8, Error> {
        Ok(self.take(1)?[0])
    }
    fn u16(&mut self) -> Result<u16, Error> {
        Ok(u16::from_le_bytes(self.take(2)?.try_into().expect("u16")))
    }
    fn u64(&mut self) -> Result<u64, Error> {
        Ok(u64::from_le_bytes(self.take(8)?.try_into().expect("u64")))
    }
    fn lineage(&mut self) -> Result<EvidenceLineage, Error> {
        Ok(self.take(16)?.try_into().expect("lineage"))
    }
    fn address(&mut self) -> Result<ContentAddress, Error> {
        Ok(ContentAddress(self.take(32)?.try_into().expect("address")))
    }
    fn optional_address(&mut self) -> Result<Option<ContentAddress>, Error> {
        match self.u8()? {
            0 => Ok(None),
            1 => Ok(Some(self.address()?)),
            _ => Err(Error::Malformed("optional address flag is invalid")),
        }
    }
    fn finish(self) -> Result<(), Error> {
        if self.offset == self.bytes.len() {
            Ok(())
        } else {
            Err(Error::Malformed("addressed object has trailing bytes"))
        }
    }
}

fn push_address(out: &mut Vec<u8>, value: Option<ContentAddress>) {
    match value {
        None => out.push(0),
        Some(address) => {
            out.push(1);
            out.extend_from_slice(&address.0);
        }
    }
}
