//! One bounded source-unresolved occurrence over one exact shared time grid.
//!
//! A cohort may contain many exact frames. Cross-capture continuity comes from
//! immediate DSF delivery generation and a locally validated prior occurrence, not
//! from assuming one new frame. Recurrent deltas retain only new successor
//! objects and compact predecessor addresses. This module is unmounted and
//! performs no storage, lookup, recall, formation, labeling, ownership, or lock.

use crate::canonical_causal_evidence::{
    content_address, decode_complete_field, decode_field_bound_delivery_impression,
    encode_complete_field, encode_delivery_impression, encoded_exact_bytes, exact_heap_bytes,
    exact_parse_logical_temporary_bytes, immutable_object, measure_complete_field,
    measure_delivery_impression, parse_exact_at, push_exact, scan_complete_field_requirement,
    scan_delivery_impression_requirement, ContentAddress, EvidenceBudget, EvidenceError,
    ImmutableObject, ObjectKind,
};
use crate::joint_field_l0_l4::{
    settle_dsf_delivery_impression, DsfDeliveryImpression, Exact, L4JointDsf,
    NeuronFieldPerspective,
};
use std::mem::size_of;

const MAGIC: &[u8; 8] = b"GLCOCCUR";
const VERSION: u16 = 3;
const SOURCE_UNRESOLVED: u8 = 0;
const DELIVERY_GENESIS: u8 = 0;
const CUSTODY_ORIGIN: u8 = 1;
const RECURRENT: u8 = 2;

#[derive(Clone, Copy, Debug)]
pub(crate) struct ResolvedDeliveryImpression<'a> {
    pub(crate) perspective: &'a NeuronFieldPerspective,
    pub(crate) delivery_impression: &'a DsfDeliveryImpression,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) struct LocallyValidatedPredecessor {
    delivery_generation: u64,
    sequence: u64,
    occurrence: ContentAddress,
}

#[derive(Clone, Copy, Debug)]
pub(crate) enum CohortPredecessor<'a> {
    DeliveryGenesis,
    CustodyOrigin {
        delivery_generation: u64,
        field: &'a L4JointDsf,
        delivery_impressions: &'a [ResolvedDeliveryImpression<'a>],
    },
    Recurrent {
        predecessor: LocallyValidatedPredecessor,
        prior_batch: &'a PreparedOccurrenceBatch,
        field: &'a L4JointDsf,
        delivery_impressions: &'a [ResolvedDeliveryImpression<'a>],
    },
}

#[derive(Clone, Copy, Debug)]
pub(crate) struct ExactTimeGridCohort<'a> {
    pub(crate) delivery_generation: u64,
    pub(crate) sequence: u64,
    pub(crate) terminal_source_clock: &'a Exact,
    pub(crate) predecessor: CohortPredecessor<'a>,
    pub(crate) successor_field: &'a L4JointDsf,
    pub(crate) successor: &'a [ResolvedDeliveryImpression<'a>],
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) struct PreparedOccurrenceBatch {
    pub(crate) occurrence: ContentAddress,
    /// Genesis/recurrent order: successor field, successor delivery_impressions, occurrence.
    /// Migration custody-origin order: predecessor field, successor field,
    /// alternating predecessor/successor delivery_impressions, occurrence.
    pub(crate) objects: Vec<ImmutableObject>,
}

#[derive(Clone, Copy, Debug)]
pub(crate) enum OccurrenceAuthority<'a> {
    GenesisOrCustodyOrigin(&'a PreparedOccurrenceBatch),
    Recurrent {
        batch: &'a PreparedOccurrenceBatch,
        predecessor: LocallyValidatedPredecessor,
        prior_batch: &'a PreparedOccurrenceBatch,
        predecessor_field: &'a L4JointDsf,
        predecessor_delivery_impressions: &'a [ResolvedDeliveryImpression<'a>],
    },
}

impl<'a> OccurrenceAuthority<'a> {
    pub(crate) fn batch(self) -> &'a PreparedOccurrenceBatch {
        match self {
            Self::GenesisOrCustodyOrigin(batch) | Self::Recurrent { batch, .. } => batch,
        }
    }
}

#[derive(Clone, Debug)]
pub(crate) struct ValidatedOccurrence<'a> {
    authority: OccurrenceAuthority<'a>,
    view: OccurrenceReferenceView,
}

impl<'a> ValidatedOccurrence<'a> {
    pub(crate) fn batch(&self) -> &'a PreparedOccurrenceBatch {
        self.authority.batch()
    }

    pub(crate) fn view(&self) -> &OccurrenceReferenceView {
        &self.view
    }

    pub(crate) fn transition_count(&self) -> usize {
        self.view.transitions.len()
    }

    /// This token proves local object and recurrence validation only. It is
    /// not a mounted commit decision and does not select a production head.
    pub(crate) fn locally_validated_predecessor(&self) -> LocallyValidatedPredecessor {
        LocallyValidatedPredecessor {
            delivery_generation: self.view.delivery_generation,
            sequence: self.view.sequence,
            occurrence: self.batch().occurrence,
        }
    }

    pub(crate) fn retained_working_bytes(
        &self,
        budget: EvidenceBudget,
    ) -> Result<usize, EvidenceError> {
        let mut total = measure_retained_batch_bytes(self.authority.batch())?;
        if let OccurrenceAuthority::Recurrent {
            prior_batch,
            predecessor_field,
            predecessor_delivery_impressions,
            ..
        } = self.authority
        {
            total = checked_add(total, measure_retained_batch_bytes(prior_batch)?)?;
            total = checked_add(
                total,
                measure_complete_field(predecessor_field, budget)?.decoded_working_bytes,
            )?;
            for predecessor in predecessor_delivery_impressions {
                total = checked_add(
                    total,
                    measure_delivery_impression(
                        predecessor.perspective,
                        predecessor.delivery_impression,
                        budget,
                    )?
                    .decoded_working_bytes,
                )?;
            }
        }
        checked_add(
            total,
            checked_add(
                checked_add(
                    size_of::<OccurrenceReferenceView>(),
                    exact_heap_bytes(&self.view.terminal_source_clock)?,
                )?,
                checked_mul(
                    self.view.transitions.capacity(),
                    size_of::<OccurrenceTransitionReference>(),
                )?,
            )?,
        )
    }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
enum OccurrenceKind {
    DeliveryGenesis,
    CustodyOrigin,
    Recurrent,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) struct OccurrenceTransitionReference {
    pub(crate) lineage: [u8; 16],
    pub(crate) predecessor_delivery_impression: Option<ContentAddress>,
    pub(crate) successor_delivery_impression: ContentAddress,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) struct OccurrenceReferenceView {
    pub(crate) delivery_generation: u64,
    pub(crate) sequence: u64,
    pub(crate) predecessor_delivery_generation: Option<u64>,
    pub(crate) predecessor_sequence: Option<u64>,
    pub(crate) predecessor_occurrence: Option<ContentAddress>,
    pub(crate) terminal_source_clock: Exact,
    pub(crate) predecessor_field: Option<ContentAddress>,
    pub(crate) successor_field: ContentAddress,
    pub(crate) transitions: Vec<OccurrenceTransitionReference>,
}

impl OccurrenceReferenceView {
    fn kind(&self) -> Result<OccurrenceKind, EvidenceError> {
        let has_transition_predecessors = self
            .transitions
            .iter()
            .all(|transition| transition.predecessor_delivery_impression.is_some());
        let lacks_transition_predecessors = self
            .transitions
            .iter()
            .all(|transition| transition.predecessor_delivery_impression.is_none());
        match (
            self.predecessor_delivery_generation,
            self.predecessor_sequence,
            self.predecessor_occurrence,
            self.predecessor_field,
            has_transition_predecessors,
            lacks_transition_predecessors,
        ) {
            (None, None, None, None, false, true) => Ok(OccurrenceKind::DeliveryGenesis),
            (Some(_), None, None, Some(_), true, false) => Ok(OccurrenceKind::CustodyOrigin),
            (Some(_), Some(_), Some(_), Some(_), true, false) => Ok(OccurrenceKind::Recurrent),
            _ => Err(EvidenceError::Invalid(
                "occurrence causal predecessor structure is incoherent",
            )),
        }
    }
}

pub(crate) fn inspect_unverified_occurrence_reference(
    bytes: &[u8],
    budget: EvidenceBudget,
) -> Result<OccurrenceReferenceView, EvidenceError> {
    decode_occurrence(bytes, budget)
}

pub(crate) fn prepare_exact_time_grid_occurrence(
    cohort: ExactTimeGridCohort<'_>,
    budget: EvidenceBudget,
) -> Result<PreparedOccurrenceBatch, EvidenceError> {
    let vertices = cohort.successor_field.vertex_count();
    require("vertices", vertices, budget.max_vertices)?;
    if vertices == 0 || cohort.successor.len() != vertices {
        return Err(EvidenceError::Invalid("successor cohort is partial"));
    }
    validate_terminal_clock(cohort.terminal_source_clock, cohort.successor_field)?;
    let successor_field_requirement = measure_complete_field(cohort.successor_field, budget)?;
    let (kind, object_count, predecessor_field_requirement, serialize_predecessor) = match cohort
        .predecessor
    {
        CohortPredecessor::DeliveryGenesis => {
            if cohort.delivery_generation != 1 || cohort.sequence != 1 {
                return Err(EvidenceError::Invalid(
                    "DSF delivery genesis does not begin both generation and custody sequence",
                ));
            }
            (
                OccurrenceKind::DeliveryGenesis,
                checked_add(2, vertices)?,
                None,
                false,
            )
        }
        CohortPredecessor::CustodyOrigin {
            delivery_generation,
            field,
            delivery_impressions,
        } => {
            require_immediate_generation(delivery_generation, cohort.delivery_generation)?;
            if cohort.sequence != 1 || delivery_impressions.len() != vertices {
                return Err(EvidenceError::Invalid(
                    "migration custody origin changed sequence or predecessor cohort",
                ));
            }
            validate_field_continuity(cohort.terminal_source_clock, field, cohort.successor_field)?;
            (
                OccurrenceKind::CustodyOrigin,
                checked_add(3, checked_mul(2, vertices)?)?,
                Some(measure_complete_field(field, budget)?),
                true,
            )
        }
        CohortPredecessor::Recurrent {
            predecessor,
            prior_batch,
            field,
            delivery_impressions,
        } => {
            require_immediate_generation(
                predecessor.delivery_generation,
                cohort.delivery_generation,
            )?;
            if predecessor
                .sequence
                .checked_add(1)
                .is_none_or(|expected| expected != cohort.sequence)
                || prior_batch.occurrence != predecessor.occurrence
                || delivery_impressions.len() != vertices
            {
                return Err(EvidenceError::Invalid(
                    "recurrent predecessor claim, sequence, or cohort changed",
                ));
            }
            validate_field_continuity(cohort.terminal_source_clock, field, cohort.successor_field)?;
            (
                OccurrenceKind::Recurrent,
                checked_add(2, vertices)?,
                Some(measure_complete_field(field, budget)?),
                false,
            )
        }
    };
    require("objects", object_count, budget.max_objects)?;

    let occurrence_bytes = occurrence_encoded_bytes(cohort.terminal_source_clock, vertices, kind)?;
    require("object bytes", occurrence_bytes, budget.max_object_bytes)?;
    require(
        "exact component bytes",
        encoded_exact_bytes(cohort.terminal_source_clock)? - 8,
        budget.max_exact_component_bytes,
    )?;
    let mut serialized_bytes = checked_add(successor_field_requirement.bytes, occurrence_bytes)?;
    let mut retained_field_working = successor_field_requirement.decoded_working_bytes;
    let mut largest_field_working = successor_field_requirement.decoded_working_bytes;
    let mut largest_temporary = checked_add(
        successor_field_requirement.bytes,
        successor_field_requirement.largest_exact_component_bytes,
    )?
    .max(checked_add(
        occurrence_bytes,
        encoded_exact_bytes(cohort.terminal_source_clock)? - 8,
    )?);
    if let Some(requirement) = predecessor_field_requirement {
        if serialize_predecessor {
            serialized_bytes = checked_add(serialized_bytes, requirement.bytes)?;
        }
        retained_field_working =
            checked_add(retained_field_working, requirement.decoded_working_bytes)?;
        largest_field_working = largest_field_working.max(requirement.decoded_working_bytes);
        largest_temporary = largest_temporary.max(checked_add(
            requirement.bytes,
            requirement.largest_exact_component_bytes,
        )?);
    }
    let mut retained_delivery_impression_working = 0usize;
    let mut largest_delivery_impression_validation_working = 0usize;
    for (vertex, successor) in cohort.successor.iter().enumerate() {
        let successor_requirement = measure_delivery_impression(
            successor.perspective,
            successor.delivery_impression,
            budget,
        )?;
        serialized_bytes = checked_add(serialized_bytes, successor_requirement.bytes)?;
        largest_temporary = largest_temporary.max(checked_add(
            successor_requirement.bytes,
            successor_requirement.largest_exact_component_bytes,
        )?);
        retained_delivery_impression_working = checked_add(
            retained_delivery_impression_working,
            successor_requirement.decoded_working_bytes,
        )?;
        largest_delivery_impression_validation_working =
            largest_delivery_impression_validation_working
                .max(checked_mul(2, successor_requirement.decoded_working_bytes)?);
        if let CohortPredecessor::CustodyOrigin {
            delivery_impressions,
            ..
        }
        | CohortPredecessor::Recurrent {
            delivery_impressions,
            ..
        } = cohort.predecessor
        {
            let predecessor = &delivery_impressions[vertex];
            let predecessor_requirement = measure_delivery_impression(
                predecessor.perspective,
                predecessor.delivery_impression,
                budget,
            )?;
            if serialize_predecessor {
                serialized_bytes = checked_add(serialized_bytes, predecessor_requirement.bytes)?;
            }
            retained_delivery_impression_working = checked_add(
                retained_delivery_impression_working,
                predecessor_requirement.decoded_working_bytes,
            )?;
            largest_delivery_impression_validation_working =
                largest_delivery_impression_validation_working.max(checked_mul(
                    2,
                    predecessor_requirement.decoded_working_bytes,
                )?);
            largest_temporary = largest_temporary.max(checked_add(
                predecessor_requirement.bytes,
                predecessor_requirement.largest_exact_component_bytes,
            )?);
        }
    }
    require(
        "serialized batch bytes",
        serialized_bytes,
        budget.max_serialized_batch_bytes,
    )?;
    let occurrence_working = checked_add(
        checked_add(
            size_of::<OccurrenceReferenceView>(),
            exact_heap_bytes(cohort.terminal_source_clock)?,
        )?,
        checked_mul(vertices, size_of::<OccurrenceTransitionReference>())?,
    )?;
    let retained_object_arena = checked_add(
        size_of::<PreparedOccurrenceBatch>(),
        checked_mul(object_count, size_of::<ImmutableObject>())?,
    )?;
    let prior_batch_bytes = match cohort.predecessor {
        CohortPredecessor::Recurrent { prior_batch, .. } => {
            measure_retained_batch_bytes(prior_batch)?
        }
        _ => 0,
    };
    let peak_live = checked_add(
        serialized_bytes,
        checked_add(
            prior_batch_bytes,
            checked_add(
                retained_object_arena,
                checked_add(
                    retained_field_working,
                    checked_add(
                        retained_delivery_impression_working,
                        checked_add(
                            largest_field_working,
                            checked_add(
                                largest_delivery_impression_validation_working,
                                checked_add(largest_temporary, occurrence_working)?,
                            )?,
                        )?,
                    )?,
                )?,
            )?,
        )?,
    )?;
    require("peak live bytes", peak_live, budget.max_peak_live_bytes)?;
    validate_in_memory_cohort(&cohort)?;

    let mut objects = Vec::new();
    objects
        .try_reserve_exact(object_count)
        .map_err(|_| EvidenceError::AllocationFailed)?;
    let successor_field_object = field_object(cohort.successor_field, budget)?;
    let mut transitions = Vec::new();
    transitions
        .try_reserve_exact(vertices)
        .map_err(|_| EvidenceError::AllocationFailed)?;
    match cohort.predecessor {
        CohortPredecessor::DeliveryGenesis => {
            objects.push(successor_field_object);
            for successor in cohort.successor {
                let successor_object =
                    delivery_impression_object(*successor, cohort.successor_field, budget)?;
                transitions.push(OccurrenceTransitionReference {
                    lineage: successor.delivery_impression.neuron_lineage,
                    predecessor_delivery_impression: None,
                    successor_delivery_impression: successor_object.address,
                });
                objects.push(successor_object);
            }
        }
        CohortPredecessor::CustodyOrigin {
            delivery_generation: _,
            field,
            delivery_impressions,
        } => {
            let predecessor_field_object = field_object(field, budget)?;
            objects.push(predecessor_field_object);
            objects.push(successor_field_object);
            for (predecessor, successor) in delivery_impressions.iter().zip(cohort.successor) {
                let predecessor_object = delivery_impression_object(*predecessor, field, budget)?;
                let successor_object =
                    delivery_impression_object(*successor, cohort.successor_field, budget)?;
                transitions.push(OccurrenceTransitionReference {
                    lineage: successor.delivery_impression.neuron_lineage,
                    predecessor_delivery_impression: Some(predecessor_object.address),
                    successor_delivery_impression: successor_object.address,
                });
                objects.push(predecessor_object);
                objects.push(successor_object);
            }
        }
        CohortPredecessor::Recurrent {
            predecessor: _,
            prior_batch,
            field: _,
            delivery_impressions: _,
        } => {
            let prior = occurrence_view(prior_batch, budget)?;
            objects.push(successor_field_object);
            for (prior_transition, successor) in prior.transitions.iter().zip(cohort.successor) {
                let successor_object =
                    delivery_impression_object(*successor, cohort.successor_field, budget)?;
                transitions.push(OccurrenceTransitionReference {
                    lineage: successor.delivery_impression.neuron_lineage,
                    predecessor_delivery_impression: Some(
                        prior_transition.successor_delivery_impression,
                    ),
                    successor_delivery_impression: successor_object.address,
                });
                objects.push(successor_object);
            }
        }
    }
    reject_duplicate_objects(&objects)?;
    let (predecessor_delivery_generation, predecessor_sequence, predecessor_occurrence) =
        match cohort.predecessor {
            CohortPredecessor::DeliveryGenesis => (None, None, None),
            CohortPredecessor::CustodyOrigin {
                delivery_generation,
                ..
            } => (Some(delivery_generation), None, None),
            CohortPredecessor::Recurrent { predecessor, .. } => (
                Some(predecessor.delivery_generation),
                Some(predecessor.sequence),
                Some(predecessor.occurrence),
            ),
        };
    let predecessor_field = match kind {
        OccurrenceKind::DeliveryGenesis => None,
        OccurrenceKind::CustodyOrigin => Some(objects[0].address),
        OccurrenceKind::Recurrent => Some(
            occurrence_view(
                match cohort.predecessor {
                    CohortPredecessor::Recurrent { prior_batch, .. } => prior_batch,
                    _ => return Err(EvidenceError::Invalid("recurrent predecessor disappeared")),
                },
                budget,
            )?
            .successor_field,
        ),
    };
    let successor_field = match kind {
        OccurrenceKind::CustodyOrigin => objects[1].address,
        _ => objects[0].address,
    };
    let occurrence_view = OccurrenceReferenceView {
        delivery_generation: cohort.delivery_generation,
        sequence: cohort.sequence,
        predecessor_delivery_generation,
        predecessor_sequence,
        predecessor_occurrence,
        terminal_source_clock: cohort.terminal_source_clock.clone(),
        predecessor_field,
        successor_field,
        transitions,
    };
    let occurrence_object = immutable_object(
        ObjectKind::Occurrence,
        encode_occurrence(&occurrence_view, budget)?,
    );
    if objects
        .iter()
        .any(|object| object.address == occurrence_object.address)
    {
        return Err(EvidenceError::Invalid(
            "occurrence duplicates a content object",
        ));
    }
    let occurrence = occurrence_object.address;
    objects.push(occurrence_object);
    let batch = PreparedOccurrenceBatch {
        occurrence,
        objects,
    };
    validate_prepared_occurrence_structure(&batch, budget)?;
    if let CohortPredecessor::Recurrent {
        predecessor,
        prior_batch,
        field,
        delivery_impressions,
    } = cohort.predecessor
    {
        validate_recurrent_against_predecessor(
            &batch,
            predecessor,
            prior_batch,
            field,
            delivery_impressions,
            budget,
        )?;
    }
    Ok(batch)
}

fn validate_prepared_occurrence_structure(
    batch: &PreparedOccurrenceBatch,
    budget: EvidenceBudget,
) -> Result<(), EvidenceError> {
    require("objects", batch.objects.len(), budget.max_objects)?;
    let serialized = batch.objects.iter().try_fold(0usize, |total, object| {
        require("object bytes", object.bytes.len(), budget.max_object_bytes)?;
        if content_address(&object.bytes) != object.address {
            return Err(EvidenceError::Invalid("object address and bytes differ"));
        }
        checked_add(total, object.bytes.len())
    })?;
    require(
        "serialized batch bytes",
        serialized,
        budget.max_serialized_batch_bytes,
    )?;
    reject_duplicate_objects(&batch.objects)?;
    let occurrence = occurrence_view(batch, budget)?;
    match occurrence.kind()? {
        OccurrenceKind::DeliveryGenesis => validate_genesis_layout(batch, &occurrence, budget),
        OccurrenceKind::CustodyOrigin => validate_origin_layout(batch, &occurrence, budget),
        OccurrenceKind::Recurrent => validate_recurrent_delta_layout(batch, &occurrence, budget),
    }
}

fn validate_recurrent_against_predecessor(
    batch: &PreparedOccurrenceBatch,
    predecessor: LocallyValidatedPredecessor,
    prior_batch: &PreparedOccurrenceBatch,
    predecessor_field: &L4JointDsf,
    predecessor_delivery_impressions: &[ResolvedDeliveryImpression<'_>],
    budget: EvidenceBudget,
) -> Result<(), EvidenceError> {
    validate_prepared_occurrence_structure(batch, budget)?;
    validate_prior_batch_predecessor(
        predecessor,
        prior_batch,
        predecessor_field,
        predecessor_delivery_impressions,
        budget,
    )?;
    let current = occurrence_view(batch, budget)?;
    if current.predecessor_occurrence != Some(predecessor.occurrence)
        || current.predecessor_sequence != Some(predecessor.sequence)
        || current.predecessor_delivery_generation != Some(predecessor.delivery_generation)
    {
        return Err(EvidenceError::Invalid(
            "recurrent delta changed its locally validated predecessor",
        ));
    }
    let prior = occurrence_view(prior_batch, budget)?;
    validate_reference_continuity(&current, &prior)?;
    let current_field = resolve_successor_field(batch, &current, budget)?;
    validate_field_continuity(
        &current.terminal_source_clock,
        predecessor_field,
        &current_field,
    )?;
    for (vertex, predecessor) in predecessor_delivery_impressions.iter().enumerate() {
        let successor =
            resolve_successor_delivery_impression(batch, &current, vertex, &current_field, budget)?;
        validate_recurrent_transition(
            vertex,
            current.transitions[vertex].lineage,
            predecessor_field,
            &current_field,
            predecessor.perspective,
            predecessor.delivery_impression,
            &successor.perspective,
            &successor.delivery_impression,
        )?;
    }
    Ok(())
}

pub(crate) fn validate_occurrence_authority(
    authority: OccurrenceAuthority<'_>,
    budget: EvidenceBudget,
) -> Result<ValidatedOccurrence<'_>, EvidenceError> {
    let current_requirement = measure_batch_validation(authority.batch(), budget)?;
    match authority {
        OccurrenceAuthority::GenesisOrCustodyOrigin(batch) => {
            require(
                "peak live bytes",
                checked_add(
                    current_requirement.retained_bytes,
                    current_requirement.transient_bytes,
                )?,
                budget.max_peak_live_bytes,
            )?;
            validate_prepared_occurrence_structure(batch, budget)?;
            if occurrence_view(batch, budget)?.kind()? == OccurrenceKind::Recurrent {
                return Err(EvidenceError::Invalid(
                    "recurrent occurrence requires locally validated predecessor authority",
                ));
            }
            Ok(())
        }
        OccurrenceAuthority::Recurrent {
            batch,
            predecessor,
            prior_batch,
            predecessor_field,
            predecessor_delivery_impressions,
        } => {
            let prior_requirement = measure_batch_validation(prior_batch, budget)?;
            let mut predecessor_working =
                measure_complete_field(predecessor_field, budget)?.decoded_working_bytes;
            for predecessor in predecessor_delivery_impressions {
                predecessor_working = checked_add(
                    predecessor_working,
                    measure_delivery_impression(
                        predecessor.perspective,
                        predecessor.delivery_impression,
                        budget,
                    )?
                    .decoded_working_bytes,
                )?;
            }
            require(
                "peak live bytes",
                checked_add(
                    checked_add(
                        current_requirement.retained_bytes,
                        prior_requirement.retained_bytes,
                    )?,
                    checked_add(
                        predecessor_working,
                        checked_add(
                            current_requirement.transient_bytes,
                            prior_requirement.transient_bytes,
                        )?,
                    )?,
                )?,
                budget.max_peak_live_bytes,
            )?;
            validate_recurrent_against_predecessor(
                batch,
                predecessor,
                prior_batch,
                predecessor_field,
                predecessor_delivery_impressions,
                budget,
            )
        }
    }?;
    let view = occurrence_view(authority.batch(), budget)?;
    Ok(ValidatedOccurrence { authority, view })
}

#[derive(Clone, Copy, Debug)]
struct BatchValidationRequirement {
    retained_bytes: usize,
    transient_bytes: usize,
}

fn measure_batch_validation(
    batch: &PreparedOccurrenceBatch,
    budget: EvidenceBudget,
) -> Result<BatchValidationRequirement, EvidenceError> {
    require("objects", batch.objects.len(), budget.max_objects)?;
    let mut serialized = 0usize;
    let mut field_working = 0usize;
    let mut largest_delivery_impression_working = 0usize;
    let mut occurrence_working = 0usize;
    let mut largest_exact_temporary = 0usize;
    for object in &batch.objects {
        require("object bytes", object.bytes.len(), budget.max_object_bytes)?;
        serialized = checked_add(serialized, object.bytes.len())?;
        match object.kind {
            ObjectKind::CompleteField => {
                let requirement = scan_complete_field_requirement(&object.bytes, budget)?;
                field_working = checked_add(field_working, requirement.decoded_working_bytes)?;
                largest_exact_temporary = largest_exact_temporary.max(
                    exact_parse_logical_temporary_bytes(requirement.largest_exact_component_bytes)?,
                );
            }
            ObjectKind::DsfDeliveryImpression => {
                let requirement = scan_delivery_impression_requirement(&object.bytes, budget)?;
                largest_delivery_impression_working = largest_delivery_impression_working
                    .max(checked_mul(2, requirement.decoded_working_bytes)?);
                largest_exact_temporary = largest_exact_temporary.max(
                    exact_parse_logical_temporary_bytes(requirement.largest_exact_component_bytes)?,
                );
            }
            ObjectKind::Occurrence => {
                let requirement = scan_occurrence(&object.bytes, budget)?;
                occurrence_working = occurrence_working.max(requirement.decoded_working_bytes);
                largest_exact_temporary = largest_exact_temporary.max(
                    exact_parse_logical_temporary_bytes(requirement.largest_exact_component_bytes)?,
                );
            }
            ObjectKind::RetiredHippocampalReferencePage => {
                return Err(EvidenceError::Invalid(
                    "hippocampal page is not an occurrence body",
                ));
            }
        }
    }
    require(
        "serialized batch bytes",
        serialized,
        budget.max_serialized_batch_bytes,
    )?;
    Ok(BatchValidationRequirement {
        retained_bytes: measure_retained_batch_bytes(batch)?,
        transient_bytes: checked_add(
            checked_mul(batch.objects.len(), size_of::<ContentAddress>())?,
            checked_add(
                field_working,
                checked_add(
                    largest_delivery_impression_working,
                    checked_add(occurrence_working, largest_exact_temporary)?,
                )?,
            )?,
        )?,
    })
}

fn validate_genesis_layout(
    batch: &PreparedOccurrenceBatch,
    occurrence: &OccurrenceReferenceView,
    budget: EvidenceBudget,
) -> Result<(), EvidenceError> {
    if occurrence.delivery_generation != 1 || occurrence.sequence != 1 {
        return Err(EvidenceError::Invalid(
            "DSF delivery genesis lineage changed",
        ));
    }
    validate_successor_only_layout(batch, occurrence, budget, true)
}

fn validate_recurrent_delta_layout(
    batch: &PreparedOccurrenceBatch,
    occurrence: &OccurrenceReferenceView,
    budget: EvidenceBudget,
) -> Result<(), EvidenceError> {
    let predecessor_generation =
        occurrence
            .predecessor_delivery_generation
            .ok_or(EvidenceError::Invalid(
                "predecessor DSF delivery generation is absent",
            ))?;
    let predecessor_sequence = occurrence
        .predecessor_sequence
        .ok_or(EvidenceError::Invalid("predecessor sequence is absent"))?;
    require_immediate_generation(predecessor_generation, occurrence.delivery_generation)?;
    if predecessor_sequence
        .checked_add(1)
        .is_none_or(|expected| expected != occurrence.sequence)
    {
        return Err(EvidenceError::Invalid(
            "occurrence sequence is not immediate",
        ));
    }
    validate_successor_only_layout(batch, occurrence, budget, false)
}

fn validate_successor_only_layout(
    batch: &PreparedOccurrenceBatch,
    occurrence: &OccurrenceReferenceView,
    budget: EvidenceBudget,
    genesis: bool,
) -> Result<(), EvidenceError> {
    if batch.objects.len() != checked_add(2, occurrence.transitions.len())?
        || batch.objects.first().is_none_or(|object| {
            object.kind != ObjectKind::CompleteField || object.address != occurrence.successor_field
        })
    {
        return Err(EvidenceError::Invalid(
            "successor-only object layout changed",
        ));
    }
    let field = decode_complete_field(&batch.objects[0].bytes, budget)?;
    validate_terminal_clock(&occurrence.terminal_source_clock, &field)?;
    if field.vertex_count() != occurrence.transitions.len() {
        return Err(EvidenceError::Invalid("successor cohort is partial"));
    }
    for (vertex, transition) in occurrence.transitions.iter().enumerate() {
        if genesis != transition.predecessor_delivery_impression.is_none() {
            return Err(EvidenceError::Invalid(
                "transition predecessor kind changed",
            ));
        }
        let object = &batch.objects[1 + vertex];
        if object.kind != ObjectKind::DsfDeliveryImpression
            || object.address != transition.successor_delivery_impression
        {
            return Err(EvidenceError::Invalid(
                "successor delivery_impression substitution detected",
            ));
        }
        let decoded = decode_field_bound_delivery_impression(&object.bytes, &field, budget)?;
        if genesis {
            validate_genesis_transition(
                vertex,
                transition.lineage,
                &field,
                &decoded.perspective,
                &decoded.delivery_impression,
            )?;
        } else if decoded.delivery_impression.neuron_lineage != transition.lineage {
            return Err(EvidenceError::Invalid("successor lineage changed"));
        }
    }
    reject_duplicate_lineages(&occurrence.transitions)
}

fn validate_origin_layout(
    batch: &PreparedOccurrenceBatch,
    occurrence: &OccurrenceReferenceView,
    budget: EvidenceBudget,
) -> Result<(), EvidenceError> {
    if occurrence.sequence != 1 {
        return Err(EvidenceError::Invalid("custody origin is not sequence one"));
    }
    let predecessor_generation =
        occurrence
            .predecessor_delivery_generation
            .ok_or(EvidenceError::Invalid(
                "custody-origin predecessor is absent",
            ))?;
    require_immediate_generation(predecessor_generation, occurrence.delivery_generation)?;
    let count = occurrence.transitions.len();
    if batch.objects.len() != checked_add(3, checked_mul(2, count)?)?
        || batch.objects[0].address
            != occurrence
                .predecessor_field
                .ok_or(EvidenceError::Invalid("origin predecessor field is absent"))?
        || batch.objects[1].address != occurrence.successor_field
    {
        return Err(EvidenceError::Invalid(
            "custody-origin object layout changed",
        ));
    }
    let predecessor_field = decode_complete_field(&batch.objects[0].bytes, budget)?;
    let successor_field = decode_complete_field(&batch.objects[1].bytes, budget)?;
    validate_field_continuity(
        &occurrence.terminal_source_clock,
        &predecessor_field,
        &successor_field,
    )?;
    if predecessor_field.vertex_count() != count || successor_field.vertex_count() != count {
        return Err(EvidenceError::Invalid("custody-origin cohort is partial"));
    }
    for (vertex, transition) in occurrence.transitions.iter().enumerate() {
        let predecessor_object = &batch.objects[2 + vertex * 2];
        let successor_object = &batch.objects[3 + vertex * 2];
        if Some(predecessor_object.address) != transition.predecessor_delivery_impression
            || successor_object.address != transition.successor_delivery_impression
        {
            return Err(EvidenceError::Invalid("custody-origin references changed"));
        }
        let predecessor = decode_field_bound_delivery_impression(
            &predecessor_object.bytes,
            &predecessor_field,
            budget,
        )?;
        let successor = decode_field_bound_delivery_impression(
            &successor_object.bytes,
            &successor_field,
            budget,
        )?;
        validate_recurrent_transition(
            vertex,
            transition.lineage,
            &predecessor_field,
            &successor_field,
            &predecessor.perspective,
            &predecessor.delivery_impression,
            &successor.perspective,
            &successor.delivery_impression,
        )?;
    }
    reject_duplicate_lineages(&occurrence.transitions)
}

fn validate_prior_batch_predecessor(
    predecessor: LocallyValidatedPredecessor,
    prior_batch: &PreparedOccurrenceBatch,
    field: &L4JointDsf,
    delivery_impressions: &[ResolvedDeliveryImpression<'_>],
    budget: EvidenceBudget,
) -> Result<(), EvidenceError> {
    if prior_batch.occurrence != predecessor.occurrence {
        return Err(EvidenceError::Invalid(
            "supplied predecessor differs from its locally validated token",
        ));
    }
    validate_prepared_occurrence_structure(prior_batch, budget)?;
    let prior = occurrence_view(prior_batch, budget)?;
    if prior.delivery_generation != predecessor.delivery_generation
        || prior.sequence != predecessor.sequence
        || prior.transitions.len() != delivery_impressions.len()
    {
        return Err(EvidenceError::Invalid(
            "locally validated predecessor lineage changed",
        ));
    }
    let resolved_field = resolve_successor_field(prior_batch, &prior, budget)?;
    if resolved_field.as_ref() != field {
        return Err(EvidenceError::Invalid(
            "predecessor field is not the locally validated prior successor body",
        ));
    }
    for (vertex, (resolved, transition)) in delivery_impressions
        .iter()
        .zip(&prior.transitions)
        .enumerate()
    {
        let body = resolve_successor_delivery_impression(
            prior_batch,
            &prior,
            vertex,
            &resolved_field,
            budget,
        )?;
        if transition.lineage != resolved.delivery_impression.neuron_lineage
            || body.perspective != *resolved.perspective
            || body.delivery_impression != *resolved.delivery_impression
        {
            return Err(EvidenceError::Invalid(
                "predecessor delivery_impression is not the locally validated prior successor body",
            ));
        }
    }
    Ok(())
}

fn resolve_successor_field(
    batch: &PreparedOccurrenceBatch,
    occurrence: &OccurrenceReferenceView,
    budget: EvidenceBudget,
) -> Result<std::sync::Arc<L4JointDsf>, EvidenceError> {
    let index = match occurrence.kind()? {
        OccurrenceKind::CustodyOrigin => 1,
        _ => 0,
    };
    let object = batch
        .objects
        .get(index)
        .ok_or(EvidenceError::Invalid("successor field object is absent"))?;
    if object.address != occurrence.successor_field {
        return Err(EvidenceError::Invalid("successor field address changed"));
    }
    decode_complete_field(&object.bytes, budget)
}

fn resolve_successor_delivery_impression(
    batch: &PreparedOccurrenceBatch,
    occurrence: &OccurrenceReferenceView,
    vertex: usize,
    field: &L4JointDsf,
    budget: EvidenceBudget,
) -> Result<crate::canonical_causal_evidence::DecodedDeliveryImpression, EvidenceError> {
    let index = match occurrence.kind()? {
        OccurrenceKind::CustodyOrigin => 3 + vertex * 2,
        _ => 1 + vertex,
    };
    let object = batch.objects.get(index).ok_or(EvidenceError::Invalid(
        "successor delivery_impression object is absent",
    ))?;
    if object.address != occurrence.transitions[vertex].successor_delivery_impression {
        return Err(EvidenceError::Invalid(
            "successor delivery_impression address changed",
        ));
    }
    decode_field_bound_delivery_impression(&object.bytes, field, budget)
}

fn validate_reference_continuity(
    current: &OccurrenceReferenceView,
    prior: &OccurrenceReferenceView,
) -> Result<(), EvidenceError> {
    if current.predecessor_field != Some(prior.successor_field)
        || current.transitions.len() != prior.transitions.len()
        || current
            .transitions
            .iter()
            .zip(&prior.transitions)
            .any(|(now, before)| {
                now.lineage != before.lineage
                    || now.predecessor_delivery_impression
                        != Some(before.successor_delivery_impression)
            })
    {
        return Err(EvidenceError::Invalid(
            "recurrent occurrence references changed prior successor bodies",
        ));
    }
    Ok(())
}

fn validate_in_memory_cohort(cohort: &ExactTimeGridCohort<'_>) -> Result<(), EvidenceError> {
    match cohort.predecessor {
        CohortPredecessor::DeliveryGenesis => {
            for (vertex, successor) in cohort.successor.iter().enumerate() {
                validate_genesis_transition(
                    vertex,
                    successor.delivery_impression.neuron_lineage,
                    cohort.successor_field,
                    successor.perspective,
                    successor.delivery_impression,
                )?;
            }
        }
        CohortPredecessor::CustodyOrigin {
            delivery_generation: _,
            field,
            delivery_impressions,
        }
        | CohortPredecessor::Recurrent {
            predecessor: _,
            prior_batch: _,
            field,
            delivery_impressions,
        } => {
            for (vertex, (predecessor, successor)) in delivery_impressions
                .iter()
                .zip(cohort.successor)
                .enumerate()
            {
                validate_recurrent_transition(
                    vertex,
                    successor.delivery_impression.neuron_lineage,
                    field,
                    cohort.successor_field,
                    predecessor.perspective,
                    predecessor.delivery_impression,
                    successor.perspective,
                    successor.delivery_impression,
                )?;
            }
        }
    }
    let transitions = cohort
        .successor
        .iter()
        .map(|value| OccurrenceTransitionReference {
            lineage: value.delivery_impression.neuron_lineage,
            predecessor_delivery_impression: None,
            successor_delivery_impression: ContentAddress(
                value.delivery_impression.authority_receipt_sha256,
            ),
        })
        .collect::<Vec<_>>();
    reject_duplicate_lineages(&transitions)
}

fn validate_terminal_clock(clock: &Exact, field: &L4JointDsf) -> Result<(), EvidenceError> {
    if field.l3.l2.l1.l0.input.times.last() != Some(clock) {
        return Err(EvidenceError::Invalid("terminal source clock changed"));
    }
    Ok(())
}

fn validate_field_continuity(
    successor_clock: &Exact,
    predecessor: &L4JointDsf,
    successor: &L4JointDsf,
) -> Result<(), EvidenceError> {
    validate_terminal_clock(successor_clock, successor)?;
    let before = predecessor.l3.l2.l1.l0.input.as_ref();
    let after = successor.l3.l2.l1.l0.input.as_ref();
    let predecessor_clock = before
        .times
        .last()
        .ok_or(EvidenceError::Invalid("predecessor time grid is empty"))?;
    if predecessor_clock >= successor_clock {
        return Err(EvidenceError::Invalid(
            "replayed or reversed source grid cannot become a new occurrence",
        ));
    }
    if before.vertex_ids != after.vertex_ids
        || before.groups != after.groups
        || predecessor.l3.l2.l1.l0.edges != successor.l3.l2.l1.l0.edges
    {
        return Err(EvidenceError::Invalid("field topology changed"));
    }
    for (after_index, time) in after.times.iter().enumerate() {
        if time <= predecessor_clock {
            let before_index = before
                .times
                .iter()
                .position(|candidate| candidate == time)
                .ok_or(EvidenceError::Invalid(
                    "successor introduced backfilled source history",
                ))?;
            if before.vectors[before_index] != after.vectors[after_index] {
                return Err(EvidenceError::Invalid(
                    "overlapping source timestamp changed its full vector",
                ));
            }
        }
    }
    Ok(())
}

fn measure_retained_batch_bytes(batch: &PreparedOccurrenceBatch) -> Result<usize, EvidenceError> {
    let payloads = batch.objects.iter().try_fold(0usize, |total, object| {
        checked_add(total, object.bytes.capacity())
    })?;
    checked_add(
        checked_add(size_of::<PreparedOccurrenceBatch>(), payloads)?,
        checked_mul(batch.objects.capacity(), size_of::<ImmutableObject>())?,
    )
}

fn require_immediate_generation(before: u64, after: u64) -> Result<(), EvidenceError> {
    if before.checked_add(1) != Some(after) {
        return Err(EvidenceError::Invalid(
            "DSF delivery generations are not immediate",
        ));
    }
    Ok(())
}

fn validate_genesis_transition(
    vertex: usize,
    lineage: [u8; 16],
    field: &L4JointDsf,
    perspective: &NeuronFieldPerspective,
    delivery_impression: &DsfDeliveryImpression,
) -> Result<(), EvidenceError> {
    if perspective.vertex_index != vertex
        || !is_terminal_frame(perspective.frame_index, field.l3.l2.l1.l0.frames.len())
        || perspective.neuron_lineage != lineage
        || delivery_impression.neuron_lineage != lineage
        || delivery_impression
            .predecessor_impression_receipt_sha256
            .is_some()
    {
        return Err(EvidenceError::Invalid(
            "genesis neuronal continuity changed",
        ));
    }
    let expected = settle_dsf_delivery_impression(field, perspective, None)
        .map_err(|_| EvidenceError::Invalid("genesis delivery_impression cannot reconstruct"))?;
    if expected != *delivery_impression {
        return Err(EvidenceError::Invalid(
            "genesis delivery_impression changed",
        ));
    }
    Ok(())
}

#[allow(clippy::too_many_arguments)]
fn validate_recurrent_transition(
    vertex: usize,
    lineage: [u8; 16],
    predecessor_field: &L4JointDsf,
    successor_field: &L4JointDsf,
    predecessor_perspective: &NeuronFieldPerspective,
    predecessor_delivery_impression: &DsfDeliveryImpression,
    successor_perspective: &NeuronFieldPerspective,
    successor_delivery_impression: &DsfDeliveryImpression,
) -> Result<(), EvidenceError> {
    if predecessor_perspective.vertex_index != vertex
        || successor_perspective.vertex_index != vertex
        || !is_terminal_frame(
            predecessor_perspective.frame_index,
            predecessor_field.l3.l2.l1.l0.frames.len(),
        )
        || !is_terminal_frame(
            successor_perspective.frame_index,
            successor_field.l3.l2.l1.l0.frames.len(),
        )
        || predecessor_delivery_impression.neuron_lineage != lineage
        || successor_delivery_impression.neuron_lineage != lineage
    {
        return Err(EvidenceError::Invalid(
            "recurrent neuronal continuity changed",
        ));
    }
    let expected = settle_dsf_delivery_impression(
        successor_field,
        successor_perspective,
        Some(predecessor_delivery_impression),
    )
    .map_err(|_| EvidenceError::Invalid("successor delivery_impression cannot reconstruct"))?;
    if expected != *successor_delivery_impression {
        return Err(EvidenceError::Invalid(
            "successor delivery_impression changed",
        ));
    }
    Ok(())
}

fn is_terminal_frame(index: usize, count: usize) -> bool {
    index.checked_add(1) == Some(count)
}

fn field_object(
    field: &L4JointDsf,
    budget: EvidenceBudget,
) -> Result<ImmutableObject, EvidenceError> {
    let bytes = encode_complete_field(field, budget)?;
    decode_complete_field(&bytes, budget)?;
    Ok(immutable_object(ObjectKind::CompleteField, bytes))
}

fn delivery_impression_object(
    value: ResolvedDeliveryImpression<'_>,
    field: &L4JointDsf,
    budget: EvidenceBudget,
) -> Result<ImmutableObject, EvidenceError> {
    let bytes = encode_delivery_impression(value.perspective, value.delivery_impression, budget)?;
    decode_field_bound_delivery_impression(&bytes, field, budget)?;
    Ok(immutable_object(ObjectKind::DsfDeliveryImpression, bytes))
}

fn occurrence_view(
    batch: &PreparedOccurrenceBatch,
    budget: EvidenceBudget,
) -> Result<OccurrenceReferenceView, EvidenceError> {
    let object = batch
        .objects
        .last()
        .ok_or(EvidenceError::Invalid("occurrence object is absent"))?;
    if object.kind != ObjectKind::Occurrence
        || object.address != batch.occurrence
        || content_address(&object.bytes) != object.address
    {
        return Err(EvidenceError::Invalid("occurrence object changed"));
    }
    decode_occurrence(&object.bytes, budget)
}

fn occurrence_encoded_bytes(
    clock: &Exact,
    count: usize,
    kind: OccurrenceKind,
) -> Result<usize, EvidenceError> {
    let predecessor_bytes = match kind {
        OccurrenceKind::DeliveryGenesis => 0,
        OccurrenceKind::CustodyOrigin => 8 + 32,
        OccurrenceKind::Recurrent => 8 + 8 + 32 + 32,
    };
    let per_transition = match kind {
        OccurrenceKind::DeliveryGenesis => 16 + 32,
        _ => 16 + 32 + 32,
    };
    checked_add(
        checked_add(
            MAGIC.len() + 2 + 1 + 1 + 8 + 8 + predecessor_bytes + 32 + 4,
            encoded_exact_bytes(clock)?,
        )?,
        checked_mul(count, per_transition)?,
    )
}

fn encode_occurrence(
    value: &OccurrenceReferenceView,
    budget: EvidenceBudget,
) -> Result<Vec<u8>, EvidenceError> {
    let kind = value.kind()?;
    let required =
        occurrence_encoded_bytes(&value.terminal_source_clock, value.transitions.len(), kind)?;
    require("object bytes", required, budget.max_object_bytes)?;
    let mut output = Vec::new();
    output
        .try_reserve_exact(required)
        .map_err(|_| EvidenceError::AllocationFailed)?;
    output.extend_from_slice(MAGIC);
    output.extend_from_slice(&VERSION.to_le_bytes());
    output.push(SOURCE_UNRESOLVED);
    output.push(match kind {
        OccurrenceKind::DeliveryGenesis => DELIVERY_GENESIS,
        OccurrenceKind::CustodyOrigin => CUSTODY_ORIGIN,
        OccurrenceKind::Recurrent => RECURRENT,
    });
    output.extend_from_slice(&value.delivery_generation.to_le_bytes());
    output.extend_from_slice(&value.sequence.to_le_bytes());
    if kind != OccurrenceKind::DeliveryGenesis {
        output.extend_from_slice(
            &value
                .predecessor_delivery_generation
                .ok_or(EvidenceError::Invalid("predecessor generation is absent"))?
                .to_le_bytes(),
        );
        if kind == OccurrenceKind::Recurrent {
            output.extend_from_slice(
                &value
                    .predecessor_sequence
                    .ok_or(EvidenceError::Invalid("predecessor sequence is absent"))?
                    .to_le_bytes(),
            );
            output.extend_from_slice(
                &value
                    .predecessor_occurrence
                    .ok_or(EvidenceError::Invalid("predecessor occurrence is absent"))?
                    .0,
            );
        }
        output.extend_from_slice(
            &value
                .predecessor_field
                .ok_or(EvidenceError::Invalid("predecessor field is absent"))?
                .0,
        );
    }
    push_exact(&mut output, &value.terminal_source_clock)?;
    output.extend_from_slice(&value.successor_field.0);
    output.extend_from_slice(
        &u32::try_from(value.transitions.len())
            .map_err(|_| EvidenceError::ArithmeticOverflow)?
            .to_le_bytes(),
    );
    for transition in &value.transitions {
        output.extend_from_slice(&transition.lineage);
        if kind != OccurrenceKind::DeliveryGenesis {
            output.extend_from_slice(
                &transition
                    .predecessor_delivery_impression
                    .ok_or(EvidenceError::Invalid(
                        "predecessor delivery_impression is absent",
                    ))?
                    .0,
            );
        }
        output.extend_from_slice(&transition.successor_delivery_impression.0);
    }
    if output.len() != required {
        return Err(EvidenceError::Invalid("occurrence measurement changed"));
    }
    Ok(output)
}

fn decode_occurrence(
    bytes: &[u8],
    budget: EvidenceBudget,
) -> Result<OccurrenceReferenceView, EvidenceError> {
    let requirement = scan_occurrence(bytes, budget)?;
    require(
        "peak live bytes",
        checked_add(
            bytes.len(),
            checked_add(
                requirement.decoded_working_bytes,
                exact_parse_logical_temporary_bytes(requirement.largest_exact_component_bytes)?,
            )?,
        )?,
        budget.max_peak_live_bytes,
    )?;
    let mut offset = 0usize;
    take(bytes, &mut offset, MAGIC.len())?;
    take(bytes, &mut offset, 2)?;
    take(bytes, &mut offset, 1)?;
    let kind = decode_kind(take(bytes, &mut offset, 1)?[0])?;
    let delivery_generation = read_u64(bytes, &mut offset)?;
    let sequence = read_u64(bytes, &mut offset)?;
    let (
        predecessor_delivery_generation,
        predecessor_sequence,
        predecessor_occurrence,
        predecessor_field,
    ) = match kind {
        OccurrenceKind::DeliveryGenesis => (None, None, None, None),
        OccurrenceKind::CustodyOrigin => (
            Some(read_u64(bytes, &mut offset)?),
            None,
            None,
            Some(read_address(bytes, &mut offset)?),
        ),
        OccurrenceKind::Recurrent => (
            Some(read_u64(bytes, &mut offset)?),
            Some(read_u64(bytes, &mut offset)?),
            Some(read_address(bytes, &mut offset)?),
            Some(read_address(bytes, &mut offset)?),
        ),
    };
    let terminal_source_clock = parse_exact_at(bytes, &mut offset)?;
    let successor_field = read_address(bytes, &mut offset)?;
    let count = read_u32(bytes, &mut offset)? as usize;
    let mut transitions = Vec::new();
    transitions
        .try_reserve_exact(count)
        .map_err(|_| EvidenceError::AllocationFailed)?;
    for _ in 0..count {
        let lineage = fixed_array(take(bytes, &mut offset, 16)?)?;
        let predecessor_delivery_impression = if kind == OccurrenceKind::DeliveryGenesis {
            None
        } else {
            Some(read_address(bytes, &mut offset)?)
        };
        transitions.push(OccurrenceTransitionReference {
            lineage,
            predecessor_delivery_impression,
            successor_delivery_impression: read_address(bytes, &mut offset)?,
        });
    }
    let value = OccurrenceReferenceView {
        delivery_generation,
        sequence,
        predecessor_delivery_generation,
        predecessor_sequence,
        predecessor_occurrence,
        terminal_source_clock,
        predecessor_field,
        successor_field,
        transitions,
    };
    reject_duplicate_lineages(&value.transitions)?;
    if offset != bytes.len() || encode_occurrence(&value, budget)? != bytes {
        return Err(EvidenceError::Invalid(
            "occurrence encoding is noncanonical",
        ));
    }
    Ok(value)
}

#[derive(Clone, Copy, Debug)]
struct OccurrenceScanRequirement {
    decoded_working_bytes: usize,
    largest_exact_component_bytes: usize,
}

fn scan_occurrence(
    bytes: &[u8],
    budget: EvidenceBudget,
) -> Result<OccurrenceScanRequirement, EvidenceError> {
    require("object bytes", bytes.len(), budget.max_object_bytes)?;
    let mut offset = 0usize;
    if take(bytes, &mut offset, MAGIC.len())? != MAGIC
        || u16::from_le_bytes(fixed_array(take(bytes, &mut offset, 2)?)?) != VERSION
        || take(bytes, &mut offset, 1)?[0] != SOURCE_UNRESOLVED
    {
        return Err(EvidenceError::Invalid("occurrence header changed"));
    }
    let kind = decode_kind(take(bytes, &mut offset, 1)?[0])?;
    take(bytes, &mut offset, 8 + 8)?;
    match kind {
        OccurrenceKind::DeliveryGenesis => {}
        OccurrenceKind::CustodyOrigin => {
            take(bytes, &mut offset, 8 + 32)?;
        }
        OccurrenceKind::Recurrent => {
            take(bytes, &mut offset, 8 + 8 + 32 + 32)?;
        }
    }
    let numerator = read_u32(bytes, &mut offset)? as usize;
    take(bytes, &mut offset, numerator)?;
    let denominator = read_u32(bytes, &mut offset)? as usize;
    if denominator == 0 {
        return Err(EvidenceError::Invalid("exact denominator is empty"));
    }
    take(bytes, &mut offset, denominator)?;
    require(
        "exact component bytes",
        checked_add(numerator, denominator)?,
        budget.max_exact_component_bytes,
    )?;
    take(bytes, &mut offset, 32)?;
    let count = read_u32(bytes, &mut offset)? as usize;
    let objects = match kind {
        OccurrenceKind::CustodyOrigin => checked_add(3, checked_mul(2, count)?)?,
        _ => checked_add(2, count)?,
    };
    require("objects", objects, budget.max_objects)?;
    let per_transition = match kind {
        OccurrenceKind::DeliveryGenesis => 16 + 32,
        _ => 16 + 32 + 32,
    };
    if bytes.len().saturating_sub(offset) != checked_mul(count, per_transition)? {
        return Err(EvidenceError::Invalid(
            "occurrence is partial or has trailing bytes",
        ));
    }
    let word_bytes = size_of::<usize>();
    let numerator_heap = checked_mul(numerator.div_ceil(word_bytes), word_bytes)?;
    let denominator_heap = checked_mul(denominator.div_ceil(word_bytes), word_bytes)?;
    Ok(OccurrenceScanRequirement {
        decoded_working_bytes: checked_add(
            checked_add(
                size_of::<OccurrenceReferenceView>(),
                checked_add(numerator_heap, denominator_heap)?,
            )?,
            checked_mul(count, size_of::<OccurrenceTransitionReference>())?,
        )?,
        largest_exact_component_bytes: numerator.max(denominator),
    })
}

fn decode_kind(value: u8) -> Result<OccurrenceKind, EvidenceError> {
    match value {
        DELIVERY_GENESIS => Ok(OccurrenceKind::DeliveryGenesis),
        CUSTODY_ORIGIN => Ok(OccurrenceKind::CustodyOrigin),
        RECURRENT => Ok(OccurrenceKind::Recurrent),
        _ => Err(EvidenceError::Invalid("occurrence causal kind changed")),
    }
}

fn read_u32(bytes: &[u8], offset: &mut usize) -> Result<u32, EvidenceError> {
    Ok(u32::from_le_bytes(fixed_array(take(bytes, offset, 4)?)?))
}

fn read_u64(bytes: &[u8], offset: &mut usize) -> Result<u64, EvidenceError> {
    Ok(u64::from_le_bytes(fixed_array(take(bytes, offset, 8)?)?))
}

fn read_address(bytes: &[u8], offset: &mut usize) -> Result<ContentAddress, EvidenceError> {
    Ok(ContentAddress(fixed_array(take(bytes, offset, 32)?)?))
}

fn reject_duplicate_lineages(
    transitions: &[OccurrenceTransitionReference],
) -> Result<(), EvidenceError> {
    let mut values = Vec::new();
    values
        .try_reserve_exact(transitions.len())
        .map_err(|_| EvidenceError::AllocationFailed)?;
    values.extend(transitions.iter().map(|transition| transition.lineage));
    values.sort_unstable();
    if values.windows(2).any(|pair| pair[0] == pair[1]) {
        return Err(EvidenceError::Invalid("occurrence repeats a lineage"));
    }
    Ok(())
}

fn reject_duplicate_objects(objects: &[ImmutableObject]) -> Result<(), EvidenceError> {
    let mut values = Vec::new();
    values
        .try_reserve_exact(objects.len())
        .map_err(|_| EvidenceError::AllocationFailed)?;
    values.extend(objects.iter().map(|object| object.address));
    values.sort_unstable();
    if values.windows(2).any(|pair| pair[0] == pair[1]) {
        return Err(EvidenceError::Invalid("batch repeats a content object"));
    }
    Ok(())
}

fn take<'a>(bytes: &'a [u8], offset: &mut usize, count: usize) -> Result<&'a [u8], EvidenceError> {
    let end = checked_add(*offset, count)?;
    if end > bytes.len() {
        return Err(EvidenceError::Invalid("object ended early"));
    }
    let value = &bytes[*offset..end];
    *offset = end;
    Ok(value)
}

fn fixed_array<const N: usize>(value: &[u8]) -> Result<[u8; N], EvidenceError> {
    value
        .try_into()
        .map_err(|_| EvidenceError::Invalid("fixed-width component changed"))
}

fn checked_add(left: usize, right: usize) -> Result<usize, EvidenceError> {
    left.checked_add(right)
        .ok_or(EvidenceError::ArithmeticOverflow)
}

fn checked_mul(left: usize, right: usize) -> Result<usize, EvidenceError> {
    left.checked_mul(right)
        .ok_or(EvidenceError::ArithmeticOverflow)
}

fn require(resource: &'static str, required: usize, available: usize) -> Result<(), EvidenceError> {
    if required > available {
        return Err(EvidenceError::BudgetExceeded {
            resource,
            required,
            available,
        });
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::canonical_causal_evidence::canonical_test_budget;
    use crate::joint_field_l0_l4::{
        bind_neuron_perspective, derive_requirement, run_joint_field_l0_l4, JointFieldBudget,
        JointFieldExperience, JointFieldInput,
    };
    use num_rational::BigRational;

    fn ratio(value: i64) -> Exact {
        BigRational::from_integer(value.into())
    }

    fn field(times: &[i64], values: &[[i64; 2]]) -> JointFieldExperience {
        let input = JointFieldInput {
            vertex_ids: vec!["left".into(), "right".into()],
            groups: vec![vec![0], vec![1]],
            times: times.iter().copied().map(ratio).collect(),
            vectors: values
                .iter()
                .map(|frame| frame.iter().copied().map(ratio).collect())
                .collect(),
        };
        let required = derive_requirement(&input).unwrap();
        run_joint_field_l0_l4(
            input,
            JointFieldBudget {
                max_input_bytes: required.input_bytes,
                max_vertices: required.vertices,
                max_frames: required.frames,
                max_edges: required.edges,
                max_relation_facts: required.relation_facts,
                max_vertex_frame_values: required.vertex_frame_values,
            },
        )
        .unwrap()
    }

    fn genesis_parts(
        value: &JointFieldExperience,
    ) -> (Vec<NeuronFieldPerspective>, Vec<DsfDeliveryImpression>) {
        let perspectives = (0..2)
            .map(|vertex| {
                bind_neuron_perspective(
                    &value.l4,
                    [u8::try_from(vertex + 1).unwrap(); 16],
                    vertex,
                    value.l4.l3.l2.l1.l0.frames.len() - 1,
                )
                .unwrap()
            })
            .collect::<Vec<_>>();
        let delivery_impressions = perspectives
            .iter()
            .map(|perspective| {
                settle_dsf_delivery_impression(&value.l4, perspective, None).unwrap()
            })
            .collect();
        (perspectives, delivery_impressions)
    }

    fn successor_parts(
        field: &JointFieldExperience,
        predecessor: &[DsfDeliveryImpression],
    ) -> (Vec<NeuronFieldPerspective>, Vec<DsfDeliveryImpression>) {
        let perspectives = predecessor
            .iter()
            .enumerate()
            .map(|(vertex, prior)| {
                bind_neuron_perspective(
                    &field.l4,
                    prior.neuron_lineage,
                    vertex,
                    field.l4.l3.l2.l1.l0.frames.len() - 1,
                )
                .unwrap()
            })
            .collect::<Vec<_>>();
        let delivery_impressions = perspectives
            .iter()
            .zip(predecessor)
            .map(|(perspective, prior)| {
                settle_dsf_delivery_impression(&field.l4, perspective, Some(prior)).unwrap()
            })
            .collect();
        (perspectives, delivery_impressions)
    }

    fn resolved<'a>(
        perspectives: &'a [NeuronFieldPerspective],
        delivery_impressions: &'a [DsfDeliveryImpression],
    ) -> Vec<ResolvedDeliveryImpression<'a>> {
        perspectives
            .iter()
            .zip(delivery_impressions)
            .map(
                |(perspective, delivery_impression)| ResolvedDeliveryImpression {
                    perspective,
                    delivery_impression,
                },
            )
            .collect()
    }

    fn locally_validated_predecessor(
        batch: &PreparedOccurrenceBatch,
    ) -> LocallyValidatedPredecessor {
        validate_occurrence_authority(
            OccurrenceAuthority::GenesisOrCustodyOrigin(batch),
            canonical_test_budget(),
        )
        .unwrap()
        .locally_validated_predecessor()
    }

    #[test]
    fn delivery_genesis_retains_first_full_grid() {
        let current = field(&[1, 2], &[[1, 2], [2, 4]]);
        let (perspectives, delivery_impressions) = genesis_parts(&current);
        let values = resolved(&perspectives, &delivery_impressions);
        let batch = prepare_exact_time_grid_occurrence(
            ExactTimeGridCohort {
                delivery_generation: 1,
                sequence: 1,
                terminal_source_clock: &ratio(2),
                predecessor: CohortPredecessor::DeliveryGenesis,
                successor_field: &current.l4,
                successor: &values,
            },
            canonical_test_budget(),
        )
        .unwrap();
        assert_eq!(batch.objects.len(), 4);
    }

    #[test]
    fn migration_origin_preserves_existing_delivery_generation() {
        let before = field(&[1, 2], &[[1, 2], [2, 4]]);
        let after = field(&[3, 4], &[[3, 7], [4, 9]]);
        let (before_p, before_f) = genesis_parts(&before);
        let (after_p, after_f) = successor_parts(&after, &before_f);
        let predecessors = resolved(&before_p, &before_f);
        let successors = resolved(&after_p, &after_f);
        let batch = prepare_exact_time_grid_occurrence(
            ExactTimeGridCohort {
                delivery_generation: 23_000_001,
                sequence: 1,
                terminal_source_clock: &ratio(4),
                predecessor: CohortPredecessor::CustodyOrigin {
                    delivery_generation: 23_000_000,
                    field: &before.l4,
                    delivery_impressions: &predecessors,
                },
                successor_field: &after.l4,
                successor: &successors,
            },
            canonical_test_budget(),
        )
        .unwrap();
        let view = occurrence_view(&batch, canonical_test_budget()).unwrap();
        assert_eq!(view.delivery_generation, 23_000_001);
        assert_eq!(view.sequence, 1);
        assert_eq!(view.predecessor_occurrence, None);
    }

    #[test]
    fn recurrent_delta_references_prior_without_republishing_it() {
        let before = field(&[1, 2], &[[1, 2], [2, 4]]);
        let middle = field(&[3, 4], &[[3, 7], [4, 9]]);
        let after = field(&[5, 6], &[[5, 10], [6, 12]]);
        let (before_p, before_f) = genesis_parts(&before);
        let (middle_p, middle_f) = successor_parts(&middle, &before_f);
        let origin = prepare_exact_time_grid_occurrence(
            ExactTimeGridCohort {
                delivery_generation: 100,
                sequence: 1,
                terminal_source_clock: &ratio(4),
                predecessor: CohortPredecessor::CustodyOrigin {
                    delivery_generation: 99,
                    field: &before.l4,
                    delivery_impressions: &resolved(&before_p, &before_f),
                },
                successor_field: &middle.l4,
                successor: &resolved(&middle_p, &middle_f),
            },
            canonical_test_budget(),
        )
        .unwrap();
        let (after_p, after_f) = successor_parts(&after, &middle_f);
        let batch = prepare_exact_time_grid_occurrence(
            ExactTimeGridCohort {
                delivery_generation: 101,
                sequence: 2,
                terminal_source_clock: &ratio(6),
                predecessor: CohortPredecessor::Recurrent {
                    predecessor: locally_validated_predecessor(&origin),
                    prior_batch: &origin,
                    field: &middle.l4,
                    delivery_impressions: &resolved(&middle_p, &middle_f),
                },
                successor_field: &after.l4,
                successor: &resolved(&after_p, &after_f),
            },
            canonical_test_budget(),
        )
        .unwrap();
        assert_eq!(batch.objects.len(), 4);
        assert!(batch.objects.iter().all(|object| {
            !origin
                .objects
                .iter()
                .any(|prior| prior.address == object.address)
        }));
    }

    #[test]
    fn replay_reversal_and_conflicting_overlap_are_rejected() {
        let before = field(&[1, 2], &[[1, 2], [2, 4]]);
        let replay = before.clone();
        assert!(validate_field_continuity(&ratio(2), &before.l4, &replay.l4).is_err());
        let conflict = field(&[2, 3], &[[20, 40], [3, 7]]);
        assert!(validate_field_continuity(&ratio(3), &before.l4, &conflict.l4).is_err());
        let backfill = field(&[0, 3], &[[0, 0], [3, 7]]);
        assert!(validate_field_continuity(&ratio(3), &before.l4, &backfill.l4).is_err());
    }

    #[test]
    fn recurrent_authority_recomputes_dna_against_locally_validated_predecessor() {
        let before = field(&[1, 2], &[[1, 2], [2, 4]]);
        let middle = field(&[3, 4], &[[3, 7], [4, 9]]);
        let after = field(&[5, 6], &[[5, 10], [6, 12]]);
        let (before_p, before_f) = genesis_parts(&before);
        let (middle_p, middle_f) = successor_parts(&middle, &before_f);
        let origin = prepare_exact_time_grid_occurrence(
            ExactTimeGridCohort {
                delivery_generation: 100,
                sequence: 1,
                terminal_source_clock: &ratio(4),
                predecessor: CohortPredecessor::CustodyOrigin {
                    delivery_generation: 99,
                    field: &before.l4,
                    delivery_impressions: &resolved(&before_p, &before_f),
                },
                successor_field: &middle.l4,
                successor: &resolved(&middle_p, &middle_f),
            },
            canonical_test_budget(),
        )
        .unwrap();
        let (after_p, after_f) = successor_parts(&after, &middle_f);
        let valid = prepare_exact_time_grid_occurrence(
            ExactTimeGridCohort {
                delivery_generation: 101,
                sequence: 2,
                terminal_source_clock: &ratio(6),
                predecessor: CohortPredecessor::Recurrent {
                    predecessor: locally_validated_predecessor(&origin),
                    prior_batch: &origin,
                    field: &middle.l4,
                    delivery_impressions: &resolved(&middle_p, &middle_f),
                },
                successor_field: &after.l4,
                successor: &resolved(&after_p, &after_f),
            },
            canonical_test_budget(),
        )
        .unwrap();

        validate_occurrence_authority(
            OccurrenceAuthority::Recurrent {
                batch: &valid,
                predecessor: locally_validated_predecessor(&origin),
                prior_batch: &origin,
                predecessor_field: &middle.l4,
                predecessor_delivery_impressions: &resolved(&middle_p, &middle_f),
            },
            canonical_test_budget(),
        )
        .unwrap();

        let (_, wrong_prior) = genesis_parts(&before);
        let (wrong_after_p, wrong_after_f) = successor_parts(&after, &wrong_prior);
        let mut substituted = valid.clone();
        let mut view = occurrence_view(&substituted, canonical_test_budget()).unwrap();
        for vertex in 0..2 {
            let replacement = delivery_impression_object(
                ResolvedDeliveryImpression {
                    perspective: &wrong_after_p[vertex],
                    delivery_impression: &wrong_after_f[vertex],
                },
                &after.l4,
                canonical_test_budget(),
            )
            .unwrap();
            view.transitions[vertex].successor_delivery_impression = replacement.address;
            substituted.objects[1 + vertex] = replacement;
        }
        let occurrence = immutable_object(
            ObjectKind::Occurrence,
            encode_occurrence(&view, canonical_test_budget()).unwrap(),
        );
        substituted.occurrence = occurrence.address;
        *substituted.objects.last_mut().unwrap() = occurrence;

        validate_prepared_occurrence_structure(&substituted, canonical_test_budget()).unwrap();
        assert!(validate_occurrence_authority(
            OccurrenceAuthority::GenesisOrCustodyOrigin(&substituted),
            canonical_test_budget()
        )
        .is_err());
        assert!(validate_recurrent_against_predecessor(
            &substituted,
            locally_validated_predecessor(&origin),
            &origin,
            &middle.l4,
            &resolved(&middle_p, &middle_f),
            canonical_test_budget(),
        )
        .is_err());
    }

    #[test]
    fn multi_frame_disjoint_capture_is_lawful() {
        let before = field(&[1, 2, 3], &[[1, 2], [2, 4], [3, 6]]);
        let after = field(&[4, 5, 6], &[[4, 8], [5, 10], [6, 12]]);
        validate_field_continuity(&ratio(6), &before.l4, &after.l4).unwrap();
    }

    #[test]
    fn exact_clock_budget_is_scanned_before_decode() {
        let current = field(&[1, 2], &[[1, 2], [2, 4]]);
        let (perspectives, delivery_impressions) = genesis_parts(&current);
        let batch = prepare_exact_time_grid_occurrence(
            ExactTimeGridCohort {
                delivery_generation: 1,
                sequence: 1,
                terminal_source_clock: &ratio(2),
                predecessor: CohortPredecessor::DeliveryGenesis,
                successor_field: &current.l4,
                successor: &resolved(&perspectives, &delivery_impressions),
            },
            canonical_test_budget(),
        )
        .unwrap();
        let mut budget = canonical_test_budget();
        budget.max_exact_component_bytes = 1;
        assert!(matches!(
            inspect_unverified_occurrence_reference(&batch.objects.last().unwrap().bytes, budget),
            Err(EvidenceError::BudgetExceeded {
                resource: "exact component bytes",
                ..
            })
        ));
    }

    #[test]
    fn serialized_and_peak_live_budgets_are_distinct() {
        let current = field(&[1, 2], &[[1, 2], [2, 4]]);
        let (perspectives, delivery_impressions) = genesis_parts(&current);
        let values = resolved(&perspectives, &delivery_impressions);
        let mut budget = canonical_test_budget();
        budget.max_peak_live_bytes = 1;
        assert!(matches!(
            prepare_exact_time_grid_occurrence(
                ExactTimeGridCohort {
                    delivery_generation: 1,
                    sequence: 1,
                    terminal_source_clock: &ratio(2),
                    predecessor: CohortPredecessor::DeliveryGenesis,
                    successor_field: &current.l4,
                    successor: &values,
                },
                budget,
            ),
            Err(EvidenceError::BudgetExceeded {
                resource: "peak live bytes",
                ..
            })
        ));

        let batch = prepare_exact_time_grid_occurrence(
            ExactTimeGridCohort {
                delivery_generation: 1,
                sequence: 1,
                terminal_source_clock: &ratio(2),
                predecessor: CohortPredecessor::DeliveryGenesis,
                successor_field: &current.l4,
                successor: &values,
            },
            canonical_test_budget(),
        )
        .unwrap();
        assert!(matches!(
            inspect_unverified_occurrence_reference(&batch.objects.last().unwrap().bytes, budget),
            Err(EvidenceError::BudgetExceeded {
                resource: "peak live bytes",
                ..
            })
        ));
        assert!(matches!(
            validate_occurrence_authority(
                OccurrenceAuthority::GenesisOrCustodyOrigin(&batch),
                budget,
            ),
            Err(EvidenceError::BudgetExceeded {
                resource: "peak live bytes",
                ..
            })
        ));
    }
}
