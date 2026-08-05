#[path = "../src/immutable_evidence_store.rs"]
mod immutable_evidence_store;
#[path = "../src/cognitive_capital_ledger.rs"]
mod ledger;

use ledger::*;
use std::collections::{BTreeMap, BTreeSet};
use std::sync::Arc;

#[derive(Clone, Debug, Default, Eq, PartialEq)]
struct Store {
    objects: BTreeMap<ContentAddress, Arc<[u8]>>,
    checkpoint: LedgerCheckpoint,
}

impl ObjectResolver for Store {
    fn resolve(&self, address: ContentAddress) -> Option<Arc<[u8]>> {
        self.objects.get(&address).cloned()
    }
}

impl Store {
    fn publish(&mut self, delta: &PreparedLedgerDelta) {
        for object in &delta.objects {
            assert_eq!(ContentAddress::of(&object.bytes), object.address);
            self.objects.insert(object.address, object.bytes.clone());
        }
        self.checkpoint = delta.successor.clone();
    }
}

struct Decoder;

impl CausalEvidenceDecoder for Decoder {
    fn inspect_complete_evidence(&self, body: &[u8]) -> Result<EvidenceInspection, String> {
        if body.len() != 4 + 1 + 1 + 1 + 8 + 16 + 32 * 5 + 2 || &body[..4] != b"CCE3" {
            return Err("typed evidence malformed or trailing".into());
        }
        let capability = Capability::ALL
            .get(body[4] as usize)
            .copied()
            .ok_or("capability")?;
        let mechanism = Mechanism::ALL
            .get(body[5] as usize)
            .copied()
            .ok_or("mechanism")?;
        let dimension = Dimension::ALL
            .get(body[6] as usize)
            .copied()
            .ok_or("dimension")?;
        let generation = u64::from_le_bytes(body[7..15].try_into().unwrap());
        let evidence_lineage = body[15..31].try_into().unwrap();
        let mut authorities = [[0u8; 32]; 5];
        for (index, authority) in authorities.iter_mut().enumerate() {
            *authority = body[31 + index * 32..63 + index * 32].try_into().unwrap();
        }
        let flag = body[191] != 0;
        let depth = match body[192] {
            0 => FormationDepth::Mosaic,
            1 => FormationDepth::MosaicOfMosaics,
            2 => FormationDepth::Tapestry,
            3 => FormationDepth::TapestryOfTapestries,
            4 => FormationDepth::Weave,
            _ => return Err("depth".into()),
        };
        let evidence = match dimension {
            Dimension::Availability => DimensionEvidence::Availability {
                physical_path: authorities[0],
            },
            Dimension::Participation => DimensionEvidence::Participation {
                admitted_transition: authorities[0],
            },
            Dimension::Retention => DimensionEvidence::Retention {
                retained_structure: authorities[0],
                persistence: authorities[1],
            },
            Dimension::Recognition => DimensionEvidence::Recognition {
                prior_structure: authorities[0],
                recurrence: authorities[1],
                changed_substrate: authorities[2],
            },
            Dimension::Recall => DimensionEvidence::Recall {
                lawful_cue: authorities[0],
                retained_structure: authorities[1],
                reactivation: authorities[2],
                original_occurrence_replayed: flag,
            },
            Dimension::CausalUse => DimensionEvidence::CausalUse {
                used_structure: authorities[0],
                changed_transition: authorities[1],
                returned_consequence: authorities[2],
            },
            Dimension::Transfer => DimensionEvidence::Transfer {
                learned_structure: authorities[0],
                first_context: authorities[1],
                distinct_context: authorities[2],
                semantic_injection: flag,
            },
            Dimension::AutonomousUse => DimensionEvidence::AutonomousUse {
                endogenous_cause: authorities[0],
                use_transition: authorities[1],
                returned_consequence: authorities[2],
                operator_selected: flag,
            },
            Dimension::Durability => DimensionEvidence::Durability {
                retained_capital: authorities[0],
                sleep_or_consolidation: authorities[1],
                persistence_restart: authorities[2],
                later_reuse: authorities[3],
                identity_continuity: authorities[4],
            },
            Dimension::IntegrationDepth => DimensionEvidence::IntegrationDepth {
                formation: authorities[0],
                depth,
                causal_use: authorities[1],
            },
        };
        Ok(EvidenceInspection {
            capability,
            mechanism,
            evidence_local_ordinal: generation,
            evidence_lineage,
            evidence,
        })
    }
}

fn evidence(
    capability: Capability,
    mechanism: Mechanism,
    dimension: Dimension,
    generation: u64,
    key: u8,
) -> Vec<u8> {
    let mut output = b"CCE3".to_vec();
    output.push(capability as u8);
    output.push(mechanism as u8);
    output.push(dimension as u8);
    output.extend_from_slice(&generation.to_le_bytes());
    output.extend_from_slice(&[key; 16]);
    for value in 1..=5 {
        output.extend_from_slice(&[key.wrapping_add(value); 32]);
    }
    output.push(0);
    output.push(4);
    output
}

fn credit(
    capability: Capability,
    mechanism: Mechanism,
    dimension: Dimension,
    generation: u64,
    key: u8,
) -> ProposedCredit {
    unmounted_test_credit(
        capability,
        mechanism,
        dimension,
        evidence(capability, mechanism, dimension, generation, key),
    )
}

fn envelope() -> PreparationEnvelope {
    PreparationEnvelope {
        max_resolved_bytes: 16_000_000,
        max_delta_objects: 10_000,
        max_delta_bytes: 16_000_000,
    }
}

fn prepare(store: &Store, generation: u64, credits: &[ProposedCredit]) -> PreparedLedgerDelta {
    match prepare_credits(
        store.checkpoint.clone(),
        generation,
        credits,
        store,
        &Decoder,
        envelope(),
    )
    .unwrap()
    {
        PreparedCapitalUpdate::Credits(delta) => delta,
        PreparedCapitalUpdate::NoCapitalEvent { .. } => {
            panic!("nonempty evidence produced no delta")
        }
    }
}

fn query(
    store: &Store,
    capability: Capability,
    mechanism: Mechanism,
    dimension: Dimension,
) -> EvidencePage {
    page_evidence(
        &store.checkpoint,
        capability,
        mechanism,
        dimension,
        None,
        store,
        &Decoder,
        PageEnvelope {
            max_entries: 64,
            max_decoded_bytes: 1_000_000,
        },
    )
    .unwrap()
}

#[test]
fn exact_ratified_capability_catalog_and_orthogonal_path_catalog_are_distinct() {
    assert_eq!(Capability::COUNT, 39);
    assert_eq!(Mechanism::COUNT, 40);
    assert_eq!(Dimension::COUNT, 10);
    assert_eq!(Capability::ALL[0].observational_name(), "Vision");
    assert_eq!(
        Capability::ALL[38].observational_name(),
        "Integrated practiced capability"
    );
    assert_eq!(Mechanism::ALL[0].observational_name(), "Recall");
    assert_eq!(
        Mechanism::ALL[39].observational_name(),
        "Creativity and self-expression"
    );
    assert_eq!(
        Capability::ALL
            .iter()
            .map(|item| item.observational_name())
            .collect::<BTreeSet<_>>()
            .len(),
        39
    );
}

#[test]
fn six_external_senses_are_separately_addressable_without_a_sensory_bucket() {
    let senses = [
        Capability::Vision,
        Capability::Hearing,
        Capability::Touch,
        Capability::Temperature,
        Capability::Smell,
        Capability::Taste,
    ];
    let store = Store::default();
    let credits: Vec<_> = senses
        .iter()
        .enumerate()
        .map(|(index, capability)| {
            credit(
                *capability,
                Mechanism::ReceptorAndSensoryMechanics,
                Dimension::Participation,
                900,
                index as u8 + 1,
            )
        })
        .collect();
    let delta = prepare(&store, 1, &credits);
    assert_eq!(delta.successor.capability_pages.len(), 6);
    assert_eq!(delta.work.capability_pages_created, 6);
    assert_eq!(delta.work.mechanism_pages_created, 6);
    let mut published = store;
    published.publish(&delta);
    for capability in senses {
        let page = query(
            &published,
            capability,
            Mechanism::ReceptorAndSensoryMechanics,
            Dimension::Participation,
        );
        assert_eq!(page.entries.len(), 1);
        assert_eq!(page.exact_inventory_count, 1);
        assert_eq!(page.entries[0].credit_ordinal, 1);
        assert_eq!(page.entries[0].evidence_local_ordinal, 900);
        assert_eq!(
            Decoder
                .inspect_complete_evidence(&page.entries[0].complete_evidence_body)
                .unwrap()
                .capability,
            capability
        );
    }
}

#[test]
fn sparse_pages_materialize_only_observed_axis_combinations() {
    let store = Store::default();
    let delta = prepare(
        &store,
        1,
        &[
            credit(
                Capability::Vision,
                Mechanism::ReceptorAndSensoryMechanics,
                Dimension::Availability,
                1,
                1,
            ),
            credit(
                Capability::Vision,
                Mechanism::SensoryCorticalOrganization,
                Dimension::Participation,
                1,
                2,
            ),
            credit(
                Capability::Hearing,
                Mechanism::ReceptorAndSensoryMechanics,
                Dimension::Availability,
                1,
                3,
            ),
        ],
    );
    assert_eq!(delta.successor.capability_pages.len(), 2);
    assert_eq!(delta.work.capability_pages_created, 2);
    assert_eq!(delta.work.mechanism_pages_created, 3);
    assert_eq!(delta.work.entries_created, 3);
    assert!(delta.objects.len() < Capability::COUNT * Mechanism::COUNT * Dimension::COUNT);
}

#[test]
fn ten_dimensions_remain_separate_and_evidence_is_stored_once() {
    let store = Store::default();
    let credits: Vec<_> = Dimension::ALL
        .iter()
        .enumerate()
        .map(|(index, dimension)| {
            credit(
                Capability::Recall,
                Mechanism::HippocampalIndexing,
                *dimension,
                1,
                index as u8 + 1,
            )
        })
        .collect();
    let delta = prepare(&store, 1, &credits);
    assert_eq!(delta.work.entries_created, 10);
    assert_eq!(delta.work.evidence_objects_created, 10);
    assert_eq!(delta.work.mechanism_pages_created, 1);
    assert_eq!(delta.work.capability_pages_created, 1);
    assert!(delta.total_object_bytes < 15_000);
    for (index, dimension) in Dimension::ALL.iter().enumerate() {
        let body = evidence(
            Capability::Recall,
            Mechanism::HippocampalIndexing,
            *dimension,
            1,
            index as u8 + 1,
        );
        assert_eq!(
            delta
                .objects
                .iter()
                .filter(|object| object.bytes.as_ref() == body.as_slice())
                .count(),
            1
        );
    }
}

#[test]
fn caller_axes_must_match_axes_derived_from_complete_evidence() {
    let store = Store::default();
    let wrong_capability = unmounted_test_credit(
        Capability::Hearing,
        Mechanism::ReceptorAndSensoryMechanics,
        Dimension::Participation,
        evidence(
            Capability::Vision,
            Mechanism::ReceptorAndSensoryMechanics,
            Dimension::Participation,
            1,
            1,
        ),
    );
    assert_eq!(
        prepare_credits(
            store.checkpoint.clone(),
            1,
            &[wrong_capability],
            &store,
            &Decoder,
            envelope()
        ),
        Err(Error::EvidenceTypeMismatch)
    );
    let wrong_path = unmounted_test_credit(
        Capability::Vision,
        Mechanism::SensoryCorticalOrganization,
        Dimension::Participation,
        evidence(
            Capability::Vision,
            Mechanism::ReceptorAndSensoryMechanics,
            Dimension::Participation,
            1,
            2,
        ),
    );
    assert_eq!(
        prepare_credits(
            store.checkpoint.clone(),
            1,
            &[wrong_path],
            &store,
            &Decoder,
            envelope()
        ),
        Err(Error::EvidenceTypeMismatch)
    );
}

#[test]
fn duplicate_lineage_and_noncanonical_input_fail_before_publication() {
    let store = Store::default();
    let same = credit(
        Capability::Recall,
        Mechanism::Recall,
        Dimension::Participation,
        1,
        1,
    );
    assert_eq!(
        prepare_credits(
            store.checkpoint.clone(),
            1,
            &[same.clone(), same],
            &store,
            &Decoder,
            envelope()
        ),
        Err(Error::DuplicateCredit)
    );
    let reversed = [
        credit(
            Capability::Hearing,
            Mechanism::Recall,
            Dimension::Participation,
            1,
            2,
        ),
        credit(
            Capability::Vision,
            Mechanism::Recall,
            Dimension::Participation,
            1,
            3,
        ),
    ];
    assert_eq!(
        prepare_credits(
            store.checkpoint.clone(),
            1,
            &reversed,
            &store,
            &Decoder,
            envelope()
        ),
        Err(Error::NonCanonicalOrder)
    );
    assert_eq!(store, Store::default());
}

#[test]
fn no_capital_event_creates_zero_objects_and_does_not_advance_time() {
    let store = Store::default();
    let result = prepare_credits(
        store.checkpoint.clone(),
        99,
        &[],
        &store,
        &Decoder,
        PreparationEnvelope {
            max_resolved_bytes: 0,
            max_delta_objects: 0,
            max_delta_bytes: 0,
        },
    )
    .unwrap();
    assert_eq!(
        result,
        PreparedCapitalUpdate::NoCapitalEvent {
            unchanged: LedgerCheckpoint::default()
        }
    );
    assert!(store.objects.is_empty());
}

#[test]
fn cold_pagination_resolves_exact_body_and_continuation_is_axis_bound() {
    let mut store = Store::default();
    for generation in 1..=7 {
        let delta = prepare(
            &store,
            generation,
            &[credit(
                Capability::Prediction,
                Mechanism::Prediction,
                Dimension::CausalUse,
                generation,
                generation as u8,
            )],
        );
        store.publish(&delta);
    }
    let first = page_evidence(
        &store.checkpoint,
        Capability::Prediction,
        Mechanism::Prediction,
        Dimension::CausalUse,
        None,
        &store,
        &Decoder,
        PageEnvelope {
            max_entries: 3,
            max_decoded_bytes: 1_000_000,
        },
    )
    .unwrap();
    assert_eq!(first.entries.len(), 3);
    assert_eq!(first.exact_inventory_count, 7);
    for entry in &first.entries {
        assert_eq!(
            ContentAddress::of(&entry.complete_evidence_body),
            entry.evidence_address
        );
    }
    let continuation = first.continuation.unwrap();
    let second = page_evidence(
        &store.checkpoint,
        Capability::Prediction,
        Mechanism::Prediction,
        Dimension::CausalUse,
        Some(continuation),
        &store,
        &Decoder,
        PageEnvelope {
            max_entries: 3,
            max_decoded_bytes: 1_000_000,
        },
    )
    .unwrap();
    assert_eq!(second.entries.len(), 3);
    assert_eq!(
        page_evidence(
            &store.checkpoint,
            Capability::Vision,
            Mechanism::Prediction,
            Dimension::CausalUse,
            Some(continuation),
            &store,
            &Decoder,
            PageEnvelope {
                max_entries: 3,
                max_decoded_bytes: 1_000_000
            }
        ),
        Err(Error::NoEvidence)
    );
}

#[test]
fn historical_lineage_replay_is_refused_by_path_compressed_membership() {
    let mut store = Store::default();
    let first = prepare(
        &store,
        1,
        &[credit(
            Capability::Recall,
            Mechanism::Recall,
            Dimension::Recall,
            1,
            7,
        )],
    );
    store.publish(&first);
    assert_eq!(
        prepare_credits(
            store.checkpoint.clone(),
            2,
            &[credit(
                Capability::Recall,
                Mechanism::Recall,
                Dimension::Recall,
                2,
                7
            )],
            &store,
            &Decoder,
            envelope()
        ),
        Err(Error::DuplicateCredit)
    );
}

#[test]
fn dimension_specific_false_claims_are_rejected() {
    for dimension in [
        Dimension::Recall,
        Dimension::Transfer,
        Dimension::AutonomousUse,
    ] {
        let mut candidate = credit(Capability::Recall, Mechanism::Recall, dimension, 1, 3);
        unmounted_test_body_mut(&mut candidate)[191] = 1;
        assert!(matches!(
            prepare_credits(
                LedgerCheckpoint::default(),
                1,
                &[candidate],
                &Store::default(),
                &Decoder,
                envelope()
            ),
            Err(Error::InvalidCausalEvidence(_))
        ));
    }
}

#[test]
fn missing_or_divergent_addressed_evidence_fails_closed() {
    let mut store = Store::default();
    let delta = prepare(
        &store,
        1,
        &[credit(
            Capability::Touch,
            Mechanism::ReceptorAndSensoryMechanics,
            Dimension::Retention,
            1,
            8,
        )],
    );
    store.publish(&delta);
    let evidence_address = query(
        &store,
        Capability::Touch,
        Mechanism::ReceptorAndSensoryMechanics,
        Dimension::Retention,
    )
    .entries[0]
        .evidence_address;
    let mut missing = store.clone();
    missing.objects.remove(&evidence_address);
    assert_eq!(
        page_evidence(
            &missing.checkpoint,
            Capability::Touch,
            Mechanism::ReceptorAndSensoryMechanics,
            Dimension::Retention,
            None,
            &missing,
            &Decoder,
            PageEnvelope {
                max_entries: 1,
                max_decoded_bytes: 100_000
            }
        ),
        Err(Error::MissingObject(evidence_address))
    );
    let mut altered = store;
    altered
        .objects
        .insert(evidence_address, Arc::from(b"altered".as_slice()));
    assert_eq!(
        page_evidence(
            &altered.checkpoint,
            Capability::Touch,
            Mechanism::ReceptorAndSensoryMechanics,
            Dimension::Retention,
            None,
            &altered,
            &Decoder,
            PageEnvelope {
                max_entries: 1,
                max_decoded_bytes: 100_000
            }
        ),
        Err(Error::AddressContentDivergence(evidence_address))
    );
}

#[test]
fn prior_dense_v2_page_is_rejected_instead_of_migrated_by_shim() {
    let mut store = Store::default();
    let legacy = Arc::<[u8]>::from(b"GCCPAG02\x01\x00legacy".as_slice());
    let address = ContentAddress::of(&legacy);
    store.objects.insert(address, legacy);
    store.checkpoint.capability_pages.push(CapabilityPageRoot {
        capability: Capability::Vision,
        page: address,
    });
    assert!(matches!(
        page_evidence(
            &store.checkpoint,
            Capability::Vision,
            Mechanism::ReceptorAndSensoryMechanics,
            Dimension::Availability,
            None,
            &store,
            &Decoder,
            PageEnvelope {
                max_entries: 1,
                max_decoded_bytes: 1_000
            }
        ),
        Err(Error::Malformed(_))
    ));
}

#[test]
fn path_compression_does_not_create_fixed_depth_per_credit() {
    let store = Store::default();
    let credits: Vec<_> = (1..=64)
        .map(|key| {
            credit(
                Capability::RelationalThought,
                Mechanism::Association,
                Dimension::Participation,
                1,
                key,
            )
        })
        .collect();
    let delta = prepare(&store, 1, &credits);
    assert_eq!(delta.work.entries_created, 64);
    assert!(delta.work.patricia_nodes_created < 64 * 16);
}
