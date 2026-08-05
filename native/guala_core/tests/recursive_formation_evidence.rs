//! Strict isolated tests for the recursive-formation evidence boundary.
//!
//! Passing these tests does not mount the boundary or prove runtime cognition.

#[path = "../src/recursive_formation_evidence.rs"]
pub mod recursive_formation_evidence;

use recursive_formation_evidence::*;
use sha2::{Digest, Sha256};
use std::collections::BTreeMap;

fn receipt(value: u8) -> Receipt {
    [value; 32]
}

fn lineage(value: u8) -> Lineage {
    [value; 16]
}

fn physical_authorities(value: u8) -> ParticipantPhysicalAuthorities {
    ParticipantPhysicalAuthorities {
        source: receipt(value),
        receptor: receipt(value.wrapping_add(1)),
        anatomy: receipt(value.wrapping_add(2)),
        membrane_transition: receipt(value.wrapping_add(3)),
        channel_transition: receipt(value.wrapping_add(4)),
        fluid_transition: receipt(value.wrapping_add(5)),
    }
}

fn quantity(value: u8) -> ConservedQuantity {
    ConservedQuantity {
        kind: PhysicalQuantityKind::Energy,
        unit_receipt: receipt(240),
        quantum_numerator: 1,
        quantum_denominator: 3,
        transferred_quanta: u128::from(value) + 1,
        source_debit_quanta: u128::from(value) + 1,
        target_credit_quanta: u128::from(value) + 1,
    }
}

fn transition(
    source: u8,
    target: u8,
    predecessor_generation: u64,
    successor_generation: u64,
    marker: u8,
) -> TransitionBody {
    TransitionBody::new(
        lineage(source),
        lineage(target),
        predecessor_generation,
        successor_generation,
        quantity(marker),
        receipt(marker.wrapping_add(1)),
        receipt(marker.wrapping_add(2)),
    )
}

fn budget() -> FormationAdmissionBudget {
    FormationAdmissionBudget {
        max_decoded_body_bytes: 1_000_000,
        max_total_bytes: 2_000_000,
        max_validation_terms: 100_000,
    }
}

fn decode_envelope() -> EvidenceDecodeEnvelope {
    EvidenceDecodeEnvelope {
        max_body_bytes: 1_000_000,
        max_references: 100_000,
        max_lineages: 100_000,
        max_configurations: 100_000,
    }
}

fn body_receipt(body: &[u8]) -> Receipt {
    Sha256::digest(body).into()
}

#[derive(Default)]
struct FixtureResolver {
    episode_contexts: BTreeMap<EpisodeContextRef, ResolvedEpisodeContextBody>,
    fractals: BTreeMap<FractalRef, FractalBody>,
    transitions: BTreeMap<TransitionRef, TransitionBody>,
    recurrences: BTreeMap<RecurrenceRef, RecurrenceBody>,
    cues: BTreeMap<PartialCueRef, PartialCueBody>,
    durability: BTreeMap<DurabilityRef, DurabilityBody>,
    formations: BTreeMap<FormationRef, FormationAdmissionBody>,
    relations: BTreeMap<RelationRef, RelationBody>,
    consequences: BTreeMap<ConsequenceRef, ConsequenceBody>,
}

impl FixtureResolver {
    fn add_transition(&mut self, body: TransitionBody) -> TransitionRef {
        let reference = body.reference();
        self.transitions.insert(reference, body);
        reference
    }

    fn add_recurrence(&mut self, body: RecurrenceBody) -> RecurrenceRef {
        let reference = body.reference();
        self.recurrences.insert(reference, body);
        reference
    }

    fn add_cue(&mut self, body: PartialCueBody) -> PartialCueRef {
        let reference = body.reference();
        self.cues.insert(reference, body);
        reference
    }

    fn add_durability(&mut self, body: DurabilityBody) -> DurabilityRef {
        let reference = body.reference();
        self.durability.insert(reference, body);
        reference
    }

    fn add_consequence(&mut self, body: ConsequenceBody) -> ConsequenceRef {
        let reference = body.reference();
        self.consequences.insert(reference, body);
        reference
    }
}

impl EvidenceResolver for FixtureResolver {
    fn resolve_episode_context(
        &self,
        reference: EpisodeContextRef,
    ) -> Option<ResolvedEpisodeContextBody> {
        self.episode_contexts.get(&reference).cloned()
    }

    fn resolve_fractal(&self, reference: FractalRef) -> Option<FractalBody> {
        self.fractals.get(&reference).cloned()
    }

    fn resolve_transition(&self, reference: TransitionRef) -> Option<TransitionBody> {
        self.transitions.get(&reference).cloned()
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

impl ColdFormationEvidenceResolver for FixtureResolver {
    fn resolve_canonical_evidence_body(&self, receipt: Receipt) -> Option<Vec<u8>> {
        self.recurrences
            .values()
            .find(|body| body.reference().receipt() == receipt)
            .map(CanonicalEvidenceBody::canonical_bytes)
            .or_else(|| {
                self.cues
                    .values()
                    .find(|body| body.reference().receipt() == receipt)
                    .map(CanonicalEvidenceBody::canonical_bytes)
            })
            .or_else(|| {
                self.durability
                    .values()
                    .find(|body| body.reference().receipt() == receipt)
                    .map(CanonicalEvidenceBody::canonical_bytes)
            })
            .or_else(|| {
                self.formations
                    .values()
                    .find(|body| body.reference().receipt() == receipt)
                    .map(CanonicalEvidenceBody::canonical_bytes)
            })
            .or_else(|| {
                self.relations
                    .values()
                    .find(|body| body.reference().receipt() == receipt)
                    .map(CanonicalEvidenceBody::canonical_bytes)
            })
            .or_else(|| {
                self.consequences
                    .values()
                    .find(|body| body.reference().receipt() == receipt)
                    .map(CanonicalEvidenceBody::canonical_bytes)
            })
    }
}

fn mosaic_fixture() -> (FixtureResolver, MatureMosaicCandidate) {
    let mut resolver = FixtureResolver::default();
    let mut members = Vec::new();
    let occurrence = receipt(230);
    let mut episode_participants = Vec::new();
    for value in 1_u8..=3 {
        let local_transition_authority = receipt(100 + value);
        let body = FractalBody::new(
            lineage(value),
            10,
            receipt(10 + value),
            receipt(20 + value),
            receipt(30 + value),
            local_transition_authority,
            physical_authorities(120 + value),
        );
        let reference = body.reference();
        resolver.fractals.insert(reference, body);
        members.push(reference);
        episode_participants.push(EpisodeMemberParticipation::new(
            lineage(value),
            reference,
            local_transition_authority,
            occurrence,
            physical_authorities(120 + value),
        ));
    }

    let episode = ResolvedEpisodeContextBody::new(ResolvedEpisodeContextParts {
        episode_height: 10,
        causal_occurrence_authority: occurrence,
        body_predecessor_authority: receipt(231),
        body_successor_authority: receipt(232),
        fluid_predecessor_authority: receipt(233),
        fluid_successor_authority: receipt(233),
        fluid_status: FluidEpisodeStatus::Quiescent {
            quiescence_authority: receipt(234),
        },
        participants: episode_participants,
        provenance: Provenance::Observed,
    });
    let episode_context = episode.reference();
    resolver.episode_contexts.insert(episode_context, episode);

    let inter_neuron_transfers = vec![
        resolver.add_transition(transition(1, 2, 9, 10, 40)),
        resolver.add_transition(transition(2, 3, 9, 10, 50)),
    ];
    let mut candidate = MatureMosaicCandidate {
        formation_lineage: lineage(90),
        generation: 10,
        episode_context,
        origin_component_authority: receipt(225),
        recurrence_component_authority: receipt(226),
        members,
        inter_neuron_transfers,
        recurrence: RecurrenceBody::new(receipt(0), 0, Vec::new()).reference(),
        partial_cue: PartialCueBody::new(
            receipt(0),
            0,
            Provenance::Observed,
            Vec::new(),
            Vec::new(),
            Vec::new(),
        )
        .reference(),
        durability: DurabilityBody::new(receipt(0), receipt(0), receipt(0), 0, 0, 0, Vec::new())
            .reference(),
    };
    let core = candidate.core_receipt();
    let recurrence_transitions = vec![
        resolver.add_transition(transition(1, 2, 10, 11, 70)),
        resolver.add_transition(transition(2, 3, 10, 11, 80)),
    ];
    candidate.recurrence =
        resolver.add_recurrence(RecurrenceBody::new(core, 11, recurrence_transitions));
    let cue_transitions = vec![
        resolver.add_transition(transition(1, 2, 11, 12, 90)),
        resolver.add_transition(transition(2, 3, 11, 12, 100)),
    ];
    candidate.partial_cue = resolver.add_cue(PartialCueBody::new(
        core,
        12,
        Provenance::Observed,
        vec![lineage(1)],
        vec![lineage(3)],
        cue_transitions,
    ));
    let reuse = resolver.add_transition(transition(1, 2, 14, 15, 110));
    candidate.durability = resolver.add_durability(DurabilityBody::new(
        core,
        core,
        core,
        10,
        14,
        15,
        vec![reuse],
    ));
    (resolver, candidate)
}

fn episode_parts(
    resolver: &FixtureResolver,
    candidate: &MatureMosaicCandidate,
) -> ResolvedEpisodeContextParts {
    let occurrence = receipt(230);
    let participants = candidate
        .members
        .iter()
        .map(|reference| {
            let fractal = &resolver.fractals[reference];
            EpisodeMemberParticipation::new(
                fractal.lineage(),
                *reference,
                fractal.successful_local_transition_authority(),
                occurrence,
                fractal.physical_authorities(),
            )
        })
        .collect();
    ResolvedEpisodeContextParts {
        episode_height: candidate.generation,
        causal_occurrence_authority: occurrence,
        body_predecessor_authority: receipt(231),
        body_successor_authority: receipt(232),
        fluid_predecessor_authority: receipt(233),
        fluid_successor_authority: receipt(233),
        fluid_status: FluidEpisodeStatus::Quiescent {
            quiescence_authority: receipt(234),
        },
        participants,
        provenance: Provenance::Observed,
    }
}

fn replace_episode(
    resolver: &mut FixtureResolver,
    candidate: &mut MatureMosaicCandidate,
    parts: ResolvedEpisodeContextParts,
) {
    let body = ResolvedEpisodeContextBody::new(parts);
    candidate.episode_context = body.reference();
    resolver.episode_contexts.insert(body.reference(), body);
}

fn rebind_collective_evidence(
    resolver: &mut FixtureResolver,
    candidate: &mut MatureMosaicCandidate,
) {
    let core = candidate.core_receipt();
    let recurrence_transitions = vec![
        resolver.add_transition(transition(1, 2, 10, 11, 70)),
        resolver.add_transition(transition(2, 3, 10, 11, 80)),
    ];
    candidate.recurrence =
        resolver.add_recurrence(RecurrenceBody::new(core, 11, recurrence_transitions));
    let cue_transitions = vec![
        resolver.add_transition(transition(1, 2, 11, 12, 90)),
        resolver.add_transition(transition(2, 3, 11, 12, 100)),
    ];
    candidate.partial_cue = resolver.add_cue(PartialCueBody::new(
        core,
        12,
        Provenance::Observed,
        vec![lineage(1)],
        vec![lineage(3)],
        cue_transitions,
    ));
    let reuse = resolver.add_transition(transition(1, 2, 14, 15, 110));
    candidate.durability = resolver.add_durability(DurabilityBody::new(
        core,
        core,
        core,
        10,
        14,
        15,
        vec![reuse],
    ));
}

fn synthetic_formation(
    kind: FormationKind,
    marker: u8,
    generation: u64,
    neuron_lineages: Vec<Lineage>,
    members: Vec<FormationRef>,
) -> FormationAdmissionBody {
    let recurrence = RecurrenceBody::new(receipt(marker), generation + 1, Vec::new()).reference();
    let cue = PartialCueBody::new(
        receipt(marker),
        generation + 2,
        Provenance::Reassembled,
        Vec::new(),
        Vec::new(),
        Vec::new(),
    )
    .reference();
    let durability = DurabilityBody::new(
        receipt(marker),
        receipt(marker),
        receipt(marker),
        generation,
        generation + 1,
        generation + 2,
        Vec::new(),
    )
    .reference();
    FormationAdmissionBody::new(FormationAdmissionParts {
        kind,
        lineage: lineage(marker),
        generation,
        core_receipt: receipt(marker),
        member_receipts: members
            .iter()
            .map(|reference| reference.receipt())
            .collect(),
        ordered_member_receipts: Vec::new(),
        relation_receipts: Vec::new(),
        neuron_lineages,
        episode_context: None,
        origin_component_authority: None,
        recurrence_component_authority: None,
        recurrence,
        partial_cue: cue,
        durability,
        consequence: None,
    })
}

fn synthetic_tree(
    resolver: &mut FixtureResolver,
    kind: FormationKind,
    marker: u8,
    generation: u64,
    primary: u8,
) -> FormationRef {
    let child_kind = match kind {
        FormationKind::Mosaic => None,
        FormationKind::MosaicOfMosaics => Some(FormationKind::Mosaic),
        FormationKind::Tapestry => Some(FormationKind::MosaicOfMosaics),
        FormationKind::TapestryOfTapestries => Some(FormationKind::Tapestry),
        FormationKind::Weave => Some(FormationKind::TapestryOfTapestries),
    };
    let members = child_kind
        .map(|child| {
            vec![
                synthetic_tree(resolver, child, marker.wrapping_add(1), generation, primary),
                synthetic_tree(
                    resolver,
                    child,
                    marker.wrapping_add(17),
                    generation,
                    primary,
                ),
            ]
        })
        .unwrap_or_default();
    let lineages = if kind == FormationKind::Mosaic {
        vec![lineage(primary), lineage(3), lineage(4)]
    } else {
        Vec::new()
    };
    let body = synthetic_formation(kind, marker, generation, lineages, members);
    let reference = body.reference();
    resolver.formations.insert(reference, body);
    reference
}

fn weave_fixture() -> (FixtureResolver, RecursiveFormationCandidate) {
    let mut resolver = FixtureResolver::default();
    let first_ref = synthetic_tree(
        &mut resolver,
        FormationKind::TapestryOfTapestries,
        150,
        15,
        1,
    );
    let second_ref = synthetic_tree(
        &mut resolver,
        FormationKind::TapestryOfTapestries,
        160,
        15,
        2,
    );

    let cross = resolver.add_transition(transition(1, 2, 19, 20, 170));
    let relation = RelationBody::new(
        first_ref,
        second_ref,
        RelationKind::GenerativeIntegration,
        20,
        vec![cross],
    );
    let relation_ref = relation.reference();
    resolver.relations.insert(relation_ref, relation);
    let mut candidate = RecursiveFormationCandidate {
        kind: FormationKind::Weave,
        formation_lineage: lineage(200),
        generation: 20,
        members: vec![first_ref, second_ref],
        relations: vec![relation_ref],
        ordered_members: Vec::new(),
        recurrence: RecurrenceBody::new(receipt(0), 0, Vec::new()).reference(),
        partial_cue: PartialCueBody::new(
            receipt(0),
            0,
            Provenance::Observed,
            Vec::new(),
            Vec::new(),
            Vec::new(),
        )
        .reference(),
        durability: DurabilityBody::new(receipt(0), receipt(0), receipt(0), 0, 0, 0, Vec::new())
            .reference(),
        consequence: None,
    };
    let core = candidate.core_receipt();
    let recurrent = resolver.add_transition(transition(1, 2, 20, 21, 180));
    candidate.recurrence = resolver.add_recurrence(RecurrenceBody::new(core, 21, vec![recurrent]));
    let cue_transition = resolver.add_transition(transition(1, 2, 21, 22, 190));
    candidate.partial_cue = resolver.add_cue(PartialCueBody::new(
        core,
        22,
        Provenance::Reassembled,
        vec![lineage(1)],
        vec![lineage(2)],
        vec![cue_transition],
    ));
    let reuse = resolver.add_transition(transition(2, 1, 24, 25, 200));
    candidate.durability = resolver.add_durability(DurabilityBody::new(
        core,
        core,
        core,
        20,
        24,
        25,
        vec![reuse],
    ));
    let consequence_transition = cross;
    let consequence = ConsequenceBody::new(
        core,
        20,
        candidate.members.clone(),
        vec![
            ConsequenceConfiguration {
                role: ConfigurationRole::Body,
                participant_lineages: vec![lineage(1), lineage(2)],
                transitions: vec![consequence_transition],
            },
            ConsequenceConfiguration {
                role: ConfigurationRole::Motor,
                participant_lineages: vec![lineage(1)],
                transitions: vec![consequence_transition],
            },
            ConsequenceConfiguration {
                role: ConfigurationRole::Sensory,
                participant_lineages: vec![lineage(2)],
                transitions: vec![consequence_transition],
            },
        ],
        vec![consequence_transition],
        consequence_transition,
        consequence_transition,
    );
    let consequence_ref = consequence.reference();
    resolver.consequences.insert(consequence_ref, consequence);
    candidate.consequence = Some(consequence_ref);
    (resolver, candidate)
}

fn admitted_leaf_mosaic(
    resolver: &mut FixtureResolver,
    first: u8,
    marker: u8,
    generation: u64,
) -> AdmittedFormationEvidence {
    let occurrence = receipt(marker.wrapping_add(1));
    let mut members = Vec::new();
    let mut episode_members = Vec::new();
    for offset in 0..3_u8 {
        let neuron = first + offset;
        let local = receipt(marker.wrapping_add(10 + offset));
        let physical = physical_authorities(marker.wrapping_add(20 + offset * 7));
        let fractal = FractalBody::new(
            lineage(neuron),
            generation,
            receipt(marker.wrapping_add(40 + offset)),
            receipt(marker.wrapping_add(50 + offset)),
            receipt(marker.wrapping_add(60 + offset)),
            local,
            physical,
        );
        let reference = fractal.reference();
        resolver.fractals.insert(reference, fractal);
        members.push(reference);
        episode_members.push(EpisodeMemberParticipation::new(
            lineage(neuron),
            reference,
            local,
            occurrence,
            physical,
        ));
    }
    let episode = ResolvedEpisodeContextBody::new(ResolvedEpisodeContextParts {
        episode_height: generation,
        causal_occurrence_authority: occurrence,
        body_predecessor_authority: receipt(marker.wrapping_add(70)),
        body_successor_authority: receipt(marker.wrapping_add(71)),
        fluid_predecessor_authority: receipt(marker.wrapping_add(72)),
        fluid_successor_authority: receipt(marker.wrapping_add(72)),
        fluid_status: FluidEpisodeStatus::Quiescent {
            quiescence_authority: receipt(marker.wrapping_add(73)),
        },
        participants: episode_members,
        provenance: Provenance::Observed,
    });
    let episode_context = episode.reference();
    resolver.episode_contexts.insert(episode_context, episode);
    let inter = resolver.add_transition(transition(
        first,
        first + 1,
        generation - 1,
        generation,
        marker.wrapping_add(80),
    ));
    let mut candidate = MatureMosaicCandidate {
        formation_lineage: lineage(marker),
        generation,
        episode_context,
        origin_component_authority: receipt(marker.wrapping_add(74)),
        recurrence_component_authority: receipt(marker.wrapping_add(75)),
        members,
        inter_neuron_transfers: vec![inter],
        recurrence: RecurrenceBody::new(receipt(1), 1, Vec::new()).reference(),
        partial_cue: PartialCueBody::new(
            receipt(2),
            1,
            Provenance::Observed,
            Vec::new(),
            Vec::new(),
            Vec::new(),
        )
        .reference(),
        durability: DurabilityBody::new(receipt(3), receipt(3), receipt(3), 1, 2, 3, Vec::new())
            .reference(),
    };
    let core = candidate.core_receipt();
    let recurrent = resolver.add_transition(transition(
        first,
        first + 1,
        generation,
        generation + 1,
        marker.wrapping_add(81),
    ));
    let recurrent_tail = resolver.add_transition(transition(
        first + 1,
        first + 2,
        generation,
        generation + 1,
        marker.wrapping_add(84),
    ));
    candidate.recurrence = resolver.add_recurrence(RecurrenceBody::new(
        core,
        generation + 1,
        vec![recurrent, recurrent_tail],
    ));
    let cue = resolver.add_transition(transition(
        first,
        first + 2,
        generation + 1,
        generation + 2,
        marker.wrapping_add(82),
    ));
    candidate.partial_cue = resolver.add_cue(PartialCueBody::new(
        core,
        generation + 2,
        Provenance::Observed,
        vec![lineage(first)],
        vec![lineage(first + 2)],
        vec![cue],
    ));
    let reuse = resolver.add_transition(transition(
        first + 2,
        first,
        generation + 4,
        generation + 5,
        marker.wrapping_add(83),
    ));
    candidate.durability = resolver.add_durability(DurabilityBody::new(
        core,
        core,
        core,
        generation,
        generation + 4,
        generation + 5,
        vec![reuse],
    ));
    let admitted = admit_mature_mosaic(&candidate, resolver, budget()).unwrap();
    resolver
        .formations
        .insert(admitted.body.reference(), admitted.body.clone());
    admitted
}

fn test_leaf_set(resolver: &FixtureResolver, reference: FormationRef) -> BTreeMap<Lineage, ()> {
    fn walk(
        resolver: &FixtureResolver,
        reference: FormationRef,
        output: &mut BTreeMap<Lineage, ()>,
    ) {
        let body = &resolver.formations[&reference];
        if body.kind() == FormationKind::Mosaic {
            output.extend(body.neuron_lineages().iter().map(|lineage| (*lineage, ())));
        } else {
            for member in body.member_formations() {
                walk(resolver, member, output);
            }
        }
    }
    let mut output = BTreeMap::new();
    walk(resolver, reference, &mut output);
    output
}

fn admit_full_tree(
    resolver: &mut FixtureResolver,
    kind: FormationKind,
    generation: u64,
    next_neuron: &mut u8,
    next_marker: &mut u8,
) -> AdmittedFormationEvidence {
    if kind == FormationKind::Mosaic {
        let first = *next_neuron;
        // Adjacent admitted mosaics share one physical neuron. The hierarchy
        // must preserve that lawful overlap rather than impose disjoint sets.
        *next_neuron += 2;
        let marker = *next_marker;
        *next_marker = next_marker.wrapping_add(1);
        return admitted_leaf_mosaic(resolver, first, marker, generation);
    }
    let child_kind = match kind {
        FormationKind::MosaicOfMosaics => FormationKind::Mosaic,
        FormationKind::Tapestry => FormationKind::MosaicOfMosaics,
        FormationKind::TapestryOfTapestries => FormationKind::Tapestry,
        FormationKind::Weave => FormationKind::TapestryOfTapestries,
        FormationKind::Mosaic => unreachable!(),
    };
    let first = admit_full_tree(
        resolver,
        child_kind,
        generation - 10,
        next_neuron,
        next_marker,
    );
    let second = admit_full_tree(
        resolver,
        child_kind,
        generation - 10,
        next_neuron,
        next_marker,
    );
    let first_ref = first.body.reference();
    let second_ref = second.body.reference();
    let first_lineage = *test_leaf_set(resolver, first_ref).keys().next().unwrap();
    let second_lineage = *test_leaf_set(resolver, second_ref).keys().next().unwrap();
    let marker = *next_marker;
    *next_marker = next_marker.wrapping_add(1);
    let relation_transition = resolver.add_transition(TransitionBody::new(
        first_lineage,
        second_lineage,
        generation - 1,
        generation,
        quantity(marker),
        receipt(marker.wrapping_add(1)),
        receipt(marker.wrapping_add(2)),
    ));
    let relation = RelationBody::new(
        first_ref,
        second_ref,
        match kind {
            FormationKind::MosaicOfMosaics => RelationKind::LearnedRelation,
            FormationKind::Tapestry | FormationKind::TapestryOfTapestries => {
                RelationKind::OrderedContinuation
            }
            FormationKind::Weave => RelationKind::GenerativeIntegration,
            FormationKind::Mosaic => unreachable!(),
        },
        generation,
        vec![relation_transition],
    );
    let relation_ref = relation.reference();
    resolver.relations.insert(relation_ref, relation);
    let mut candidate = RecursiveFormationCandidate {
        kind,
        formation_lineage: lineage(marker),
        generation,
        members: vec![first_ref, second_ref],
        relations: vec![relation_ref],
        ordered_members: if matches!(
            kind,
            FormationKind::Tapestry | FormationKind::TapestryOfTapestries
        ) {
            vec![first_ref, second_ref]
        } else {
            Vec::new()
        },
        recurrence: RecurrenceBody::new(receipt(1), 1, Vec::new()).reference(),
        partial_cue: PartialCueBody::new(
            receipt(2),
            1,
            Provenance::Observed,
            Vec::new(),
            Vec::new(),
            Vec::new(),
        )
        .reference(),
        durability: DurabilityBody::new(receipt(3), receipt(3), receipt(3), 1, 2, 3, Vec::new())
            .reference(),
        consequence: None,
    };
    let core = candidate.core_receipt();
    let recurrent = resolver.add_transition(transition(
        first_lineage[0],
        second_lineage[0],
        generation,
        generation + 1,
        marker.wrapping_add(3),
    ));
    candidate.recurrence =
        resolver.add_recurrence(RecurrenceBody::new(core, generation + 1, vec![recurrent]));
    let cue = resolver.add_transition(transition(
        first_lineage[0],
        second_lineage[0],
        generation + 1,
        generation + 2,
        marker.wrapping_add(4),
    ));
    candidate.partial_cue = resolver.add_cue(PartialCueBody::new(
        core,
        generation + 2,
        Provenance::Reassembled,
        vec![first_lineage],
        vec![second_lineage],
        vec![cue],
    ));
    let reuse = resolver.add_transition(transition(
        second_lineage[0],
        first_lineage[0],
        generation + 4,
        generation + 5,
        marker.wrapping_add(5),
    ));
    candidate.durability = resolver.add_durability(DurabilityBody::new(
        core,
        core,
        core,
        generation,
        generation + 4,
        generation + 5,
        vec![reuse],
    ));
    if kind == FormationKind::Weave {
        let consequence = ConsequenceBody::new(
            core,
            generation,
            candidate.members.clone(),
            vec![
                ConsequenceConfiguration {
                    role: ConfigurationRole::Body,
                    participant_lineages: vec![first_lineage, second_lineage],
                    transitions: vec![relation_transition],
                },
                ConsequenceConfiguration {
                    role: ConfigurationRole::Motor,
                    participant_lineages: vec![first_lineage],
                    transitions: vec![relation_transition],
                },
                ConsequenceConfiguration {
                    role: ConfigurationRole::Sensory,
                    participant_lineages: vec![second_lineage],
                    transitions: vec![relation_transition],
                },
            ],
            vec![relation_transition],
            relation_transition,
            relation_transition,
        );
        candidate.consequence = Some(resolver.add_consequence(consequence));
    }
    let admitted = admit_recursive_formation(&candidate, resolver, budget()).unwrap();
    resolver
        .formations
        .insert(admitted.body.reference(), admitted.body.clone());
    admitted
}

#[test]
fn mature_mosaic_requires_decoded_bodies_and_returns_derived_authority() {
    let (resolver, candidate) = mosaic_fixture();
    let admitted = admit_mature_mosaic(&candidate, &resolver, budget()).unwrap();

    assert!(admitted.body.has_valid_authority());
    assert_eq!(admitted.body.core_receipt(), candidate.core_receipt());
    assert_ne!(
        admitted.body.reference().receipt(),
        candidate.core_receipt()
    );
    assert_eq!(
        admitted.body.episode_context(),
        Some(candidate.episode_context)
    );
    assert_eq!(
        admitted.body.relation_receipts(),
        candidate
            .inter_neuron_transfers
            .iter()
            .map(|reference| reference.receipt())
            .collect::<Vec<_>>()
    );
    assert!(admitted.requirement.decoded_body_bytes > admitted.requirement.reference_bytes);
}

#[test]
fn one_resolved_episode_can_bind_members_without_an_original_moment_transfer_cycle() {
    let (mut resolver, mut candidate) = mosaic_fixture();
    candidate.inter_neuron_transfers.clear();
    rebind_collective_evidence(&mut resolver, &mut candidate);

    let admitted = admit_mature_mosaic(&candidate, &resolver, budget()).unwrap();
    assert_eq!(admitted.body.core_receipt(), candidate.core_receipt());
}

#[test]
fn truthful_unavailable_fluid_state_remains_distinct_and_admissible() {
    let (mut resolver, mut candidate) = mosaic_fixture();
    let mut unavailable = episode_parts(&resolver, &candidate);
    unavailable.fluid_status = FluidEpisodeStatus::Unavailable {
        unavailability_authority: receipt(236),
    };
    replace_episode(&mut resolver, &mut candidate, unavailable);
    rebind_collective_evidence(&mut resolver, &mut candidate);

    assert!(admit_mature_mosaic(&candidate, &resolver, budget()).is_ok());
}

#[test]
fn independent_episode_height_is_admitted_but_absent_member_fails_closed() {
    let (mut resolver, mut candidate) = mosaic_fixture();
    let mut independently_numbered_episode = episode_parts(&resolver, &candidate);
    independently_numbered_episode.episode_height = 99;
    replace_episode(
        &mut resolver,
        &mut candidate,
        independently_numbered_episode,
    );
    rebind_collective_evidence(&mut resolver, &mut candidate);
    assert!(admit_mature_mosaic(&candidate, &resolver, budget()).is_ok());

    let (mut resolver, mut candidate) = mosaic_fixture();
    let mut missing_member = episode_parts(&resolver, &candidate);
    missing_member.participants.pop();
    replace_episode(&mut resolver, &mut candidate, missing_member);
    assert_eq!(
        admit_mature_mosaic(&candidate, &resolver, budget()).unwrap_err(),
        EvidenceError::MemberDidNotParticipateInEpisode(lineage(3))
    );
}

#[test]
fn body_and_fluid_authority_and_truthful_quiescence_are_mandatory() {
    let (mut resolver, mut candidate) = mosaic_fixture();
    let mut missing_body = episode_parts(&resolver, &candidate);
    missing_body.body_successor_authority = [0; 32];
    replace_episode(&mut resolver, &mut candidate, missing_body);
    assert_eq!(
        admit_mature_mosaic(&candidate, &resolver, budget()).unwrap_err(),
        EvidenceError::IncompleteEpisodeContext
    );

    let (mut resolver, mut candidate) = mosaic_fixture();
    let mut missing_fluid = episode_parts(&resolver, &candidate);
    missing_fluid.fluid_predecessor_authority = [0; 32];
    replace_episode(&mut resolver, &mut candidate, missing_fluid);
    assert_eq!(
        admit_mature_mosaic(&candidate, &resolver, budget()).unwrap_err(),
        EvidenceError::IncompleteEpisodeContext
    );

    let (mut resolver, mut candidate) = mosaic_fixture();
    let mut false_quiescence = episode_parts(&resolver, &candidate);
    false_quiescence.fluid_successor_authority = receipt(235);
    replace_episode(&mut resolver, &mut candidate, false_quiescence);
    assert_eq!(
        admit_mature_mosaic(&candidate, &resolver, budget()).unwrap_err(),
        EvidenceError::FluidStatusContradictsState
    );
}

#[test]
fn local_transition_mismatch_and_unrelated_simultaneous_member_are_rejected() {
    let (mut resolver, mut candidate) = mosaic_fixture();
    let mut mismatch = episode_parts(&resolver, &candidate);
    mismatch.participants[1] = EpisodeMemberParticipation::new(
        lineage(2),
        candidate.members[1],
        receipt(250),
        receipt(230),
        physical_authorities(122),
    );
    replace_episode(&mut resolver, &mut candidate, mismatch);
    assert_eq!(
        admit_mature_mosaic(&candidate, &resolver, budget()).unwrap_err(),
        EvidenceError::LocalTransitionAuthorityMismatch(lineage(2))
    );

    let (mut resolver, mut candidate) = mosaic_fixture();
    let mut unrelated = episode_parts(&resolver, &candidate);
    unrelated.participants[2] = EpisodeMemberParticipation::new(
        lineage(3),
        candidate.members[2],
        receipt(103),
        receipt(229),
        physical_authorities(123),
    );
    replace_episode(&mut resolver, &mut candidate, unrelated);
    assert_eq!(
        admit_mature_mosaic(&candidate, &resolver, budget()).unwrap_err(),
        EvidenceError::MemberCausalOccurrenceMismatch(lineage(3))
    );
}

#[test]
fn directed_cycle_cannot_substitute_for_a_resolved_episode_context() {
    let (mut resolver, mut candidate) = mosaic_fixture();
    candidate
        .inter_neuron_transfers
        .push(resolver.add_transition(transition(3, 1, 9, 10, 60)));
    resolver.episode_contexts.remove(&candidate.episode_context);

    assert_eq!(
        admit_mature_mosaic(&candidate, &resolver, budget()).unwrap_err(),
        EvidenceError::UnresolvedEpisodeContext(candidate.episode_context)
    );
}

#[test]
fn nonconserved_or_untyped_physical_change_is_rejected() {
    let (mut resolver, mut candidate) = mosaic_fixture();
    let mut broken_quantity = quantity(220);
    broken_quantity.target_credit_quanta += 1;
    let broken = TransitionBody::new(
        lineage(1),
        lineage(2),
        9,
        10,
        broken_quantity,
        receipt(221),
        receipt(222),
    );
    let broken_ref = resolver.add_transition(broken);
    candidate.inter_neuron_transfers[0] = broken_ref;

    assert_eq!(
        admit_mature_mosaic(&candidate, &resolver, budget()).unwrap_err(),
        EvidenceError::UnresolvedOrNonconservedTransition
    );
}

#[test]
fn recurrence_clock_must_be_the_transition_clock() {
    let (mut resolver, mut candidate) = mosaic_fixture();
    let wrong_clock = resolver.add_transition(transition(1, 2, 11, 12, 210));
    candidate.recurrence = resolver.add_recurrence(RecurrenceBody::new(
        candidate.core_receipt(),
        11,
        vec![wrong_clock],
    ));

    assert_eq!(
        admit_mature_mosaic(&candidate, &resolver, budget()).unwrap_err(),
        EvidenceError::EventGenerationMismatch
    );
}

#[test]
fn leaf_mosaic_rejects_an_inactive_passenger_member() {
    let (mut resolver, mut candidate) = mosaic_fixture();
    let only_two = resolver.add_transition(transition(1, 2, 10, 11, 209));
    candidate.recurrence = resolver.add_recurrence(RecurrenceBody::new(
        candidate.core_receipt(),
        11,
        vec![only_two],
    ));
    assert_eq!(
        admit_mature_mosaic(&candidate, &resolver, budget()).unwrap_err(),
        EvidenceError::RecurrentComponentDoesNotEqualMembers
    );
}

#[test]
fn partial_cue_requires_a_path_to_an_identified_uncued_change() {
    let (mut resolver, mut candidate) = mosaic_fixture();
    let disconnected = resolver.add_transition(transition(2, 3, 11, 12, 211));
    candidate.partial_cue = resolver.add_cue(PartialCueBody::new(
        candidate.core_receipt(),
        12,
        Provenance::Observed,
        vec![lineage(1)],
        vec![lineage(3)],
        vec![disconnected],
    ));

    assert_eq!(
        admit_mature_mosaic(&candidate, &resolver, budget()).unwrap_err(),
        EvidenceError::UncuedParticipantNotCausallyChanged
    );
}

#[test]
fn durability_reuse_must_bind_the_same_formation_core() {
    let (mut resolver, mut candidate) = mosaic_fixture();
    let reuse = resolver.add_transition(transition(1, 2, 14, 15, 212));
    candidate.durability = resolver.add_durability(DurabilityBody::new(
        candidate.core_receipt(),
        receipt(250),
        receipt(250),
        10,
        14,
        15,
        vec![reuse],
    ));

    assert_eq!(
        admit_mature_mosaic(&candidate, &resolver, budget()).unwrap_err(),
        EvidenceError::DurabilityDoesNotReuseSameFormation
    );
}

#[test]
fn resource_budget_is_derived_from_decoded_body_bytes() {
    let (resolver, candidate) = mosaic_fixture();
    let admitted = admit_mature_mosaic(&candidate, &resolver, budget()).unwrap();
    let one_byte_short = FormationAdmissionBudget {
        max_decoded_body_bytes: admitted.requirement.decoded_body_bytes - 1,
        max_total_bytes: admitted.requirement.total_bytes,
        max_validation_terms: admitted.requirement.validation_terms,
    };

    assert!(matches!(
        admit_mature_mosaic(&candidate, &resolver, one_byte_short),
        Err(EvidenceError::ResourceBudgetExceeded { .. })
    ));
}

#[test]
fn parent_kind_enforces_relation_kind_before_recursive_admission() {
    let (mut resolver, mut candidate) = weave_fixture();
    let source = candidate.members[0];
    let target = candidate.members[1];
    let support = resolver.add_transition(transition(1, 2, 19, 20, 213));
    let wrong = RelationBody::new(
        source,
        target,
        RelationKind::OrderedContinuation,
        20,
        vec![support],
    );
    let wrong_ref = wrong.reference();
    resolver.relations.insert(wrong_ref, wrong);
    candidate.relations = vec![wrong_ref];

    assert_eq!(
        admit_recursive_formation(&candidate, &resolver, budget()).unwrap_err(),
        EvidenceError::RelationKindDoesNotMatchParent
    );
}

#[test]
fn weave_requires_member_bound_configured_physical_consequence() {
    let (resolver, candidate) = weave_fixture();
    let admitted = admit_recursive_formation(&candidate, &resolver, budget()).unwrap();
    assert_eq!(admitted.body.kind(), FormationKind::Weave);

    let (mut broken_resolver, mut broken_candidate) = weave_fixture();
    let any_transition = *broken_resolver.transitions.keys().next().unwrap();
    let broken = ConsequenceBody::new(
        broken_candidate.core_receipt(),
        20,
        broken_candidate.members.clone(),
        vec![ConsequenceConfiguration {
            role: ConfigurationRole::Body,
            participant_lineages: vec![lineage(1), lineage(2)],
            transitions: vec![any_transition],
        }],
        Vec::new(),
        any_transition,
        any_transition,
    );
    let broken_ref = broken.reference();
    broken_resolver.consequences.insert(broken_ref, broken);
    broken_candidate.consequence = Some(broken_ref);
    assert_eq!(
        admit_recursive_formation(&broken_candidate, &broken_resolver, budget()).unwrap_err(),
        EvidenceError::WeaveConsequenceMissingConfiguration
    );
}

#[test]
fn all_five_hierarchy_kinds_are_admitted_in_sequence_without_descendant_copying() {
    let mut resolver = FixtureResolver::default();
    let mut next_neuron = 1_u8;
    let mut next_marker = 20_u8;
    let weave = admit_full_tree(
        &mut resolver,
        FormationKind::Weave,
        50,
        &mut next_neuron,
        &mut next_marker,
    );

    assert_eq!(weave.body.kind(), FormationKind::Weave);
    assert!(weave.body.neuron_lineages().is_empty());
    assert_eq!(weave.body.member_formations().len(), 2);
    let kinds = resolver
        .formations
        .values()
        .map(FormationAdmissionBody::kind)
        .collect::<std::collections::BTreeSet<_>>();
    assert_eq!(
        kinds,
        std::collections::BTreeSet::from([
            FormationKind::Mosaic,
            FormationKind::MosaicOfMosaics,
            FormationKind::Tapestry,
            FormationKind::TapestryOfTapestries,
            FormationKind::Weave,
        ])
    );
    for body in resolver
        .formations
        .values()
        .filter(|body| body.kind() != FormationKind::Mosaic)
    {
        assert!(body.neuron_lineages().is_empty());
        assert_eq!(body.member_formations().len(), 2);
    }
    let first_mom = resolver
        .formations
        .values()
        .find(|body| body.kind() == FormationKind::MosaicOfMosaics)
        .unwrap();
    let members = first_mom.member_formations();
    let left = test_leaf_set(&resolver, members[0]);
    let right = test_leaf_set(&resolver, members[1]);
    assert!(left.keys().any(|lineage| right.contains_key(lineage)));
}

#[test]
fn ordered_members_are_retained_only_for_ordered_hierarchy_kinds() {
    let mut resolver = FixtureResolver::default();
    let mut next_neuron = 1_u8;
    let mut next_marker = 20_u8;
    admit_full_tree(
        &mut resolver,
        FormationKind::Weave,
        50,
        &mut next_neuron,
        &mut next_marker,
    );

    for body in resolver.formations.values() {
        match body.kind() {
            FormationKind::Tapestry | FormationKind::TapestryOfTapestries => {
                assert_eq!(body.ordered_member_formations(), body.member_formations());
            }
            FormationKind::Mosaic | FormationKind::MosaicOfMosaics | FormationKind::Weave => {
                assert!(body.ordered_member_formations().is_empty());
            }
        }
    }
}

#[test]
fn all_recursive_evidence_bodies_round_trip_through_strict_bounded_decoders() {
    let (mosaic_resolver, mosaic_candidate) = mosaic_fixture();
    let recurrence = &mosaic_resolver.recurrences[&mosaic_candidate.recurrence];
    assert_eq!(
        decode_recurrence_body(
            recurrence.reference(),
            &recurrence.canonical_bytes(),
            decode_envelope()
        )
        .unwrap(),
        *recurrence
    );
    let cue = &mosaic_resolver.cues[&mosaic_candidate.partial_cue];
    assert_eq!(
        decode_partial_cue_body(cue.reference(), &cue.canonical_bytes(), decode_envelope())
            .unwrap(),
        *cue
    );
    let durability = &mosaic_resolver.durability[&mosaic_candidate.durability];
    assert_eq!(
        decode_durability_body(
            durability.reference(),
            &durability.canonical_bytes(),
            decode_envelope()
        )
        .unwrap(),
        *durability
    );

    let (weave_resolver, weave_candidate) = weave_fixture();
    let relation = &weave_resolver.relations[&weave_candidate.relations[0]];
    assert_eq!(
        decode_relation_body(
            relation.reference(),
            &relation.canonical_bytes(),
            decode_envelope()
        )
        .unwrap(),
        *relation
    );
    let consequence = &weave_resolver.consequences[&weave_candidate.consequence.unwrap()];
    assert_eq!(
        decode_consequence_body(
            consequence.reference(),
            &consequence.canonical_bytes(),
            decode_envelope()
        )
        .unwrap(),
        *consequence
    );
}

#[test]
fn cold_formation_body_is_semantically_readmitted_without_body_drift() {
    let (mosaic_resolver, mosaic_candidate) = mosaic_fixture();
    let admitted = admit_mature_mosaic(&mosaic_candidate, &mosaic_resolver, budget()).unwrap();
    let canonical = admitted.body.canonical_bytes();
    let cold = cold_decode_and_readmit_formation(
        admitted.body.reference(),
        &canonical,
        decode_envelope(),
        &mosaic_resolver,
        budget(),
    )
    .unwrap();
    assert_eq!(cold.body, admitted.body);

    let (weave_resolver, weave_candidate) = weave_fixture();
    let admitted = admit_recursive_formation(&weave_candidate, &weave_resolver, budget()).unwrap();
    let canonical = admitted.body.canonical_bytes();
    let cold = cold_decode_and_readmit_formation(
        admitted.body.reference(),
        &canonical,
        decode_envelope(),
        &weave_resolver,
        budget(),
    )
    .unwrap();
    assert_eq!(cold.body, admitted.body);
}

#[test]
fn strict_decoders_reject_trailing_bytes_and_impossible_counts_before_allocation() {
    let (resolver, candidate) = weave_fixture();
    let relation = &resolver.relations[&candidate.relations[0]];
    let mut trailing = relation.canonical_bytes();
    trailing.push(0);
    let addressed = RelationRef::from_receipt(body_receipt(&trailing));
    assert_eq!(
        decode_relation_body(addressed, &trailing, decode_envelope()),
        Err(EvidenceDecodeError::TrailingBytes)
    );

    let recurrence = &resolver.recurrences[&candidate.recurrence];
    let mut impossible = recurrence.canonical_bytes();
    impossible[41..49].copy_from_slice(&u64::MAX.to_be_bytes());
    let addressed = RecurrenceRef::from_receipt(body_receipt(&impossible));
    assert_eq!(
        decode_recurrence_body(addressed, &impossible, decode_envelope()),
        Err(EvidenceDecodeError::CountOverflow)
    );
}

#[test]
fn strict_decoder_envelope_refuses_reference_amplification() {
    let (resolver, candidate) = weave_fixture();
    let relation = &resolver.relations[&candidate.relations[0]];
    let envelope = EvidenceDecodeEnvelope {
        max_references: 1,
        ..decode_envelope()
    };
    assert_eq!(
        decode_relation_body(relation.reference(), &relation.canonical_bytes(), envelope),
        Err(EvidenceDecodeError::ReferenceLimitExceeded)
    );
}

#[test]
fn pre_order_retention_formation_tag_has_no_legacy_decode_path() {
    let (resolver, candidate) = mosaic_fixture();
    let admitted = admit_mature_mosaic(&candidate, &resolver, budget()).unwrap();
    let mut legacy_tagged = admitted.body.canonical_bytes();
    legacy_tagged[0] = 8;
    let addressed = FormationRef::from_receipt(body_receipt(&legacy_tagged));
    assert_eq!(
        decode_formation_admission_body(addressed, &legacy_tagged, decode_envelope()),
        Err(EvidenceDecodeError::InvalidTag)
    );
}

#[test]
fn cold_graph_inspection_decodes_and_readmits_every_hierarchy_body() {
    let mut resolver = FixtureResolver::default();
    let mut next_neuron = 1_u8;
    let mut next_marker = 20_u8;
    let weave = admit_full_tree(
        &mut resolver,
        FormationKind::Weave,
        50,
        &mut next_neuron,
        &mut next_marker,
    );
    let root_body = weave.body.canonical_bytes();
    let inspected = inspect_cold_formation_evidence_graph(
        weave.body.reference(),
        &root_body,
        &resolver,
        &resolver,
        decode_envelope(),
        budget(),
    )
    .unwrap();

    assert_eq!(inspected.root.body, weave.body);
    assert_eq!(inspected.formation_bodies, 31);
    assert_eq!(inspected.relation_bodies, 15);
    assert_eq!(inspected.collective_evidence_bodies, 94);
}
