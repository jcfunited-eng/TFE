//! Read-only, non-flattened cognitive-capital evidence.
//!
//! This module runs after a resident physical successor has been formed. It
//! cannot alter neuronal settlement, formation, recall, action, or persisted
//! organism state. The complete capability and dimension axes are fixed
//! observation vocabulary; only sparse evidence actually produced by the
//! current causal transition is emitted. Absence means `not yet proven`.

use crate::resident_cognitive_formation::CognitiveFormationObservation;

pub const COGNITIVE_CAPITAL_SCHEMA: &str = "guala.cognitive_capital.evidence.v1";

#[derive(Clone, Copy, Debug, Eq, Ord, PartialEq, PartialOrd)]
pub enum CognitiveCapability {
    Vision,
    Hearing,
    Touch,
    Temperature,
    Smell,
    Taste,
    ProprioceptionAndBodyPosition,
    VestibularBalance,
    InteroceptionAndVisceralState,
    MultisensoryIntegration,
    RecognitionAndFamiliarity,
    AttentionAndOrienting,
    ImmediateCausalState,
    EpisodicMemory,
    ProceduralAndPhysicalMemory,
    Recall,
    RelationalThought,
    Prediction,
    DeliberationAndChoice,
    ImaginationAndSimulation,
    LanguageComprehension,
    SpeechAndArticulation,
    OrderedThinking,
    SocialCognitionAndOtherPerspective,
    Empathy,
    EmotionAndAffect,
    EmotionalBalanceAndRegulation,
    MotivationNeedsAndCuriosity,
    SelfAndBodyContinuity,
    MotorAndActuatorControl,
    NavigationAndAvoidance,
    PlayAndExploration,
    SleepAndRest,
    Dreaming,
    Consolidation,
    AutonomousCognitionAndAction,
    LearningAndDevelopmentalGrowth,
    CreativityAndSelfExpression,
    IntegratedPracticedCapability,
}

impl CognitiveCapability {
    pub const ALL: &'static [Self] = &[
        Self::Vision,
        Self::Hearing,
        Self::Touch,
        Self::Temperature,
        Self::Smell,
        Self::Taste,
        Self::ProprioceptionAndBodyPosition,
        Self::VestibularBalance,
        Self::InteroceptionAndVisceralState,
        Self::MultisensoryIntegration,
        Self::RecognitionAndFamiliarity,
        Self::AttentionAndOrienting,
        Self::ImmediateCausalState,
        Self::EpisodicMemory,
        Self::ProceduralAndPhysicalMemory,
        Self::Recall,
        Self::RelationalThought,
        Self::Prediction,
        Self::DeliberationAndChoice,
        Self::ImaginationAndSimulation,
        Self::LanguageComprehension,
        Self::SpeechAndArticulation,
        Self::OrderedThinking,
        Self::SocialCognitionAndOtherPerspective,
        Self::Empathy,
        Self::EmotionAndAffect,
        Self::EmotionalBalanceAndRegulation,
        Self::MotivationNeedsAndCuriosity,
        Self::SelfAndBodyContinuity,
        Self::MotorAndActuatorControl,
        Self::NavigationAndAvoidance,
        Self::PlayAndExploration,
        Self::SleepAndRest,
        Self::Dreaming,
        Self::Consolidation,
        Self::AutonomousCognitionAndAction,
        Self::LearningAndDevelopmentalGrowth,
        Self::CreativityAndSelfExpression,
        Self::IntegratedPracticedCapability,
    ];

    pub const fn as_str(self) -> &'static str {
        match self {
            Self::Vision => "Vision",
            Self::Hearing => "Hearing",
            Self::Touch => "Touch",
            Self::Temperature => "Temperature",
            Self::Smell => "Smell",
            Self::Taste => "Taste",
            Self::ProprioceptionAndBodyPosition => "Proprioception and body position",
            Self::VestibularBalance => "Vestibular balance",
            Self::InteroceptionAndVisceralState => "Interoception and visceral state",
            Self::MultisensoryIntegration => "Multisensory integration",
            Self::RecognitionAndFamiliarity => "Recognition and familiarity",
            Self::AttentionAndOrienting => "Attention and orienting",
            Self::ImmediateCausalState => "Immediate causal state",
            Self::EpisodicMemory => "Episodic memory",
            Self::ProceduralAndPhysicalMemory => "Procedural and physical memory",
            Self::Recall => "Recall",
            Self::RelationalThought => "Relational thought",
            Self::Prediction => "Prediction",
            Self::DeliberationAndChoice => "Deliberation and choice",
            Self::ImaginationAndSimulation => "Imagination and simulation",
            Self::LanguageComprehension => "Language comprehension",
            Self::SpeechAndArticulation => "Speech and articulation",
            Self::OrderedThinking => "Ordered thinking",
            Self::SocialCognitionAndOtherPerspective => "Social cognition and other-perspective",
            Self::Empathy => "Empathy",
            Self::EmotionAndAffect => "Emotion and affect",
            Self::EmotionalBalanceAndRegulation => "Emotional balance and regulation",
            Self::MotivationNeedsAndCuriosity => "Motivation, needs, and curiosity",
            Self::SelfAndBodyContinuity => "Self and body continuity",
            Self::MotorAndActuatorControl => "Motor and actuator control",
            Self::NavigationAndAvoidance => "Navigation and avoidance",
            Self::PlayAndExploration => "Play and exploration",
            Self::SleepAndRest => "Sleep and rest",
            Self::Dreaming => "Dreaming",
            Self::Consolidation => "Consolidation",
            Self::AutonomousCognitionAndAction => "Autonomous cognition and action",
            Self::LearningAndDevelopmentalGrowth => "Learning and developmental growth",
            Self::CreativityAndSelfExpression => "Creativity and self-expression",
            Self::IntegratedPracticedCapability => "Integrated practiced capability",
        }
    }
}

#[derive(Clone, Copy, Debug, Eq, Ord, PartialEq, PartialOrd)]
pub enum CognitiveCapitalDimension {
    Availability,
    Participation,
    Retention,
    Recognition,
    Recall,
    CausalUse,
    CrossContextTransfer,
    AutonomousUse,
    Durability,
    IntegrationDepth,
}

impl CognitiveCapitalDimension {
    pub const ALL: &'static [Self] = &[
        Self::Availability,
        Self::Participation,
        Self::Retention,
        Self::Recognition,
        Self::Recall,
        Self::CausalUse,
        Self::CrossContextTransfer,
        Self::AutonomousUse,
        Self::Durability,
        Self::IntegrationDepth,
    ];

    pub const fn as_str(self) -> &'static str {
        match self {
            Self::Availability => "availability",
            Self::Participation => "participation",
            Self::Retention => "retention",
            Self::Recognition => "recognition",
            Self::Recall => "recall",
            Self::CausalUse => "causal_use",
            Self::CrossContextTransfer => "transfer",
            Self::AutonomousUse => "autonomous_use",
            Self::Durability => "durability",
            Self::IntegrationDepth => "integration_depth",
        }
    }
}

#[derive(Clone, Copy, Debug, Eq, Ord, PartialEq, PartialOrd)]
pub enum CognitiveCapitalEvidenceKind {
    MountedOpticalNeuron,
    OpticalNeuronTransition,
    RetainedOpticalNeuronFractal,
    RecognizedPhysicalMosaic,
    HippocampalEpisodeAdmission,
    PartialCuePhysicalReassembly,
}

impl CognitiveCapitalEvidenceKind {
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::MountedOpticalNeuron => "mounted_optical_neuron",
            Self::OpticalNeuronTransition => "optical_neuron_transition",
            Self::RetainedOpticalNeuronFractal => "retained_optical_neuron_fractal",
            Self::RecognizedPhysicalMosaic => "recognized_physical_mosaic",
            Self::HippocampalEpisodeAdmission => "hippocampal_episode_admission",
            Self::PartialCuePhysicalReassembly => "partial_cue_physical_reassembly",
        }
    }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct CognitiveCapitalEvidence {
    capability: CognitiveCapability,
    dimension: CognitiveCapitalDimension,
    kind: CognitiveCapitalEvidenceKind,
    occurrence_quantity: usize,
}

impl CognitiveCapitalEvidence {
    pub fn capability(&self) -> CognitiveCapability {
        self.capability
    }

    pub fn dimension(&self) -> CognitiveCapitalDimension {
        self.dimension
    }

    pub fn kind(&self) -> CognitiveCapitalEvidenceKind {
        self.kind
    }

    pub fn occurrence_quantity(&self) -> usize {
        self.occurrence_quantity
    }
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct CognitiveCapitalObservation {
    predecessor_state_receipt: [u8; 32],
    successor_state_receipt: [u8; 32],
    source_authority: [u8; 32],
    organism_tick: u64,
    cognitive_generation: u64,
    evidence: Box<[CognitiveCapitalEvidence]>,
}

impl CognitiveCapitalObservation {
    pub fn schema(&self) -> &'static str {
        COGNITIVE_CAPITAL_SCHEMA
    }

    pub fn predecessor_state_receipt(&self) -> [u8; 32] {
        self.predecessor_state_receipt
    }

    pub fn successor_state_receipt(&self) -> [u8; 32] {
        self.successor_state_receipt
    }

    pub fn source_authority(&self) -> [u8; 32] {
        self.source_authority
    }

    pub fn organism_tick(&self) -> u64 {
        self.organism_tick
    }

    pub fn cognitive_generation(&self) -> u64 {
        self.cognitive_generation
    }

    pub fn evidence(&self) -> &[CognitiveCapitalEvidence] {
        &self.evidence
    }

    pub fn evidence_for(
        &self,
        capability: CognitiveCapability,
        dimension: CognitiveCapitalDimension,
    ) -> impl Iterator<Item = &CognitiveCapitalEvidence> {
        self.evidence
            .iter()
            .filter(move |entry| entry.capability == capability && entry.dimension == dimension)
    }
}

fn add(
    evidence: &mut Vec<CognitiveCapitalEvidence>,
    capability: CognitiveCapability,
    dimension: CognitiveCapitalDimension,
    kind: CognitiveCapitalEvidenceKind,
    occurrence_quantity: usize,
) {
    if occurrence_quantity != 0 {
        evidence.push(CognitiveCapitalEvidence {
            capability,
            dimension,
            kind,
            occurrence_quantity,
        });
    }
}

pub(crate) fn observe_transition_cognitive_capital(
    predecessor_state_receipt: [u8; 32],
    successor_state_receipt: [u8; 32],
    source_authority: [u8; 32],
    organism_tick: u64,
    cognitive: &CognitiveFormationObservation,
) -> CognitiveCapitalObservation {
    use CognitiveCapability as Capability;
    use CognitiveCapitalDimension as Dimension;
    use CognitiveCapitalEvidenceKind as Kind;

    let mut evidence = Vec::with_capacity(32);

    add(
        &mut evidence,
        Capability::Vision,
        Dimension::Availability,
        Kind::MountedOpticalNeuron,
        cognitive.complete_neuron_count,
    );
    add(
        &mut evidence,
        Capability::Vision,
        Dimension::Participation,
        Kind::OpticalNeuronTransition,
        cognitive.physically_transitioned_neuron_count,
    );
    add(
        &mut evidence,
        Capability::Vision,
        Dimension::Retention,
        Kind::RetainedOpticalNeuronFractal,
        cognitive.complete_neuron_fractal_count,
    );

    let recognized_mosaic = usize::from(cognitive.mosaic_formed.is_some());
    for capability in [
        Capability::Vision,
        Capability::RecognitionAndFamiliarity,
        Capability::LearningAndDevelopmentalGrowth,
    ] {
        add(
            &mut evidence,
            capability,
            Dimension::Recognition,
            Kind::RecognizedPhysicalMosaic,
            recognized_mosaic,
        );
    }
    for capability in [
        Capability::RecognitionAndFamiliarity,
        Capability::LearningAndDevelopmentalGrowth,
        Capability::EpisodicMemory,
    ] {
        add(
            &mut evidence,
            capability,
            Dimension::Availability,
            Kind::HippocampalEpisodeAdmission,
            recognized_mosaic,
        );
        add(
            &mut evidence,
            capability,
            Dimension::Participation,
            Kind::HippocampalEpisodeAdmission,
            recognized_mosaic,
        );
        add(
            &mut evidence,
            capability,
            Dimension::Retention,
            Kind::HippocampalEpisodeAdmission,
            recognized_mosaic,
        );
    }

    for capability in [
        Capability::Vision,
        Capability::RecognitionAndFamiliarity,
        Capability::EpisodicMemory,
        Capability::Recall,
        Capability::LearningAndDevelopmentalGrowth,
    ] {
        add(
            &mut evidence,
            capability,
            Dimension::Recall,
            Kind::PartialCuePhysicalReassembly,
            cognitive.partial_cue_reassembly_count(),
        );
    }
    for capability in [Capability::Recall] {
        add(
            &mut evidence,
            capability,
            Dimension::Availability,
            Kind::PartialCuePhysicalReassembly,
            cognitive.partial_cue_reassembly_count(),
        );
        add(
            &mut evidence,
            capability,
            Dimension::Participation,
            Kind::PartialCuePhysicalReassembly,
            cognitive.partial_cue_reassembly_count(),
        );
    }

    // RelationalThought, OrderedThinking and the generative-recombination
    // precursor USED TO draw their evidence from the dynamic-formation
    // classifier, which read the retired hippocampal archive.  That classifier
    // is deleted (see resident_cognitive_formation.rs) because it cannot be
    // rebuilt from her body without redefining its law.  No evidence of these
    // kinds is emitted now, and by this module's own rule — "Absence means
    // `not yet proven`" — that is the honest report: nothing measures them.
    // They were also measured at ZERO on her live body before removal, so no
    // capability that was ever proven has become unproven.

    CognitiveCapitalObservation {
        predecessor_state_receipt,
        successor_state_receipt,
        source_authority,
        organism_tick,
        cognitive_generation: cognitive.cognitive_ordinal,
        evidence: evidence.into_boxed_slice(),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn observation() -> CognitiveFormationObservation {
        CognitiveFormationObservation {
            cognitive_ordinal: 9,
            trace_formed: false,
            mosaic_formed: Some([7; 32]),
            activations: Vec::new(),
            trace_count: 0,
            mosaic_count: 1,
            dsf_delivery_count: 4,
            complete_neuron_count: 4,
            resting_neuron_count: 0,
            physically_transitioned_neuron_count: 4,
            complete_neuron_fractal_count: 4,
            emitted_neuron_fractals: Vec::new(),
            partial_cue_reassembly_count: 1,
            endogenous_partial_cue_reassembly_count: 0,
            mosaic_of_mosaics_count: 0,
            rest_recovered_neuron_count: 0,
            rest_drained_dissipation_quanta: 0,
            unmet_dissipation_quanta: 0,
            membrane_returned_elementary_charges: 0,
            membrane_unreturned_elementary_charges: 0,
            metabolic_fuel_quanta: 0,
            nutrition_regenerated_fuel_quanta: 0,
            nutrition_unabsorbed_waste_quanta: 0,
            nutrition_vented_heat_quanta: 0,
            energy: Default::default(),
        }
    }

    #[test]
    fn matrix_axes_are_complete_unique_and_never_flattened() {
        assert_eq!(CognitiveCapability::ALL.len(), 39);
        assert_eq!(CognitiveCapitalDimension::ALL.len(), 10);
        for (index, capability) in CognitiveCapability::ALL.iter().enumerate() {
            assert!(!capability.as_str().is_empty());
            assert!(!CognitiveCapability::ALL[..index].contains(capability));
        }
        for (index, dimension) in CognitiveCapitalDimension::ALL.iter().enumerate() {
            assert!(!dimension.as_str().is_empty());
            assert!(!CognitiveCapitalDimension::ALL[..index].contains(dimension));
        }
    }

    #[test]
    fn transition_evidence_is_sparse_causal_and_does_not_overclaim() {
        let capital =
            observe_transition_cognitive_capital([1; 32], [2; 32], [3; 32], 8, &observation());
        assert_eq!(capital.predecessor_state_receipt(), [1; 32]);
        assert_eq!(capital.successor_state_receipt(), [2; 32]);
        assert_eq!(capital.source_authority(), [3; 32]);
        assert_eq!(capital.organism_tick(), 8);
        assert_eq!(capital.cognitive_generation(), 9);
        assert!(capital
            .evidence_for(
                CognitiveCapability::Vision,
                CognitiveCapitalDimension::Retention
            )
            .any(
                |entry| entry.kind() == CognitiveCapitalEvidenceKind::RetainedOpticalNeuronFractal
            ));
        assert!(capital
            .evidence_for(
                CognitiveCapability::Recall,
                CognitiveCapitalDimension::Recall
            )
            .any(
                |entry| entry.kind() == CognitiveCapitalEvidenceKind::PartialCuePhysicalReassembly
            ));
        // The generative-recombination-precursor assertion that stood here
        // is retired with the archive classifier that produced it (which
        // MEASURED zero on Guala's live body).  Its capability now carries no
        // evidence at all, which by this module's rule reads as
        // "not yet proven" — the honest state.
        assert_eq!(
            capital
                .evidence_for(
                    CognitiveCapability::LearningAndDevelopmentalGrowth,
                    CognitiveCapitalDimension::IntegrationDepth
                )
                .count(),
            0
        );
        for capability in CognitiveCapability::ALL {
            assert_eq!(
                capital
                    .evidence_for(*capability, CognitiveCapitalDimension::CausalUse)
                    .count(),
                0
            );
            assert_eq!(
                capital
                    .evidence_for(*capability, CognitiveCapitalDimension::CrossContextTransfer)
                    .count(),
                0
            );
            assert_eq!(
                capital
                    .evidence_for(*capability, CognitiveCapitalDimension::AutonomousUse)
                    .count(),
                0
            );
            assert_eq!(
                capital
                    .evidence_for(*capability, CognitiveCapitalDimension::Durability)
                    .count(),
                0
            );
        }
        assert_eq!(
            capital
                .evidence_for(
                    CognitiveCapability::CreativityAndSelfExpression,
                    CognitiveCapitalDimension::Availability,
                )
                .count(),
            0
        );
    }

    #[test]
    fn zero_transition_emits_no_false_capital() {
        let mut cognitive = observation();
        cognitive.mosaic_formed = None;
        cognitive.complete_neuron_count = 0;
        cognitive.physically_transitioned_neuron_count = 0;
        cognitive.complete_neuron_fractal_count = 0;
        cognitive.partial_cue_reassembly_count = 0;
        let capital =
            observe_transition_cognitive_capital([1; 32], [2; 32], [3; 32], 8, &cognitive);
        assert!(capital.evidence().is_empty());
    }
}
