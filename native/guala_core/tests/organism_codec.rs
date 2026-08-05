use guala_core::organism::*;

const ENCODE_BUDGET: u64 = 1_000_000;
const DECODE_BUDGET: DecodeBudget = DecodeBudget {
    max_input_bytes: 1_000_000,
    max_heap_bytes: 1_000_000,
};

fn receipt(byte: u8) -> [u8; 32] {
    [byte; 32]
}

fn causal(ordinal: u64, byte: u8) -> CausalReceipt {
    CausalReceipt {
        ordinal,
        receipt: receipt(byte),
    }
}

fn range(start: u64, len: u64) -> ArenaRange {
    ArenaRange { start, len }
}

fn neuron(
    lineage: u8,
    position: u64,
    trit_range: ArenaRange,
    recent_causal_range: ArenaRange,
    authority_index: u64,
) -> NeuronState {
    NeuronState {
        lineage: [lineage; 16],
        growth_dna: receipt(lineage + 1),
        specialization_receipt: receipt(lineage + 2),
        field_position: position,
        trit_range,
        oscillator_phase_bits: 0.25_f64.to_bits(),
        oscillator_winding: i64::from(lineage),
        local_dsf: LocalDsfState {
            coordinate_bits: [
                0.1_f64.to_bits(),
                0.2_f64.to_bits(),
                0.3_f64.to_bits(),
                0.4_f64.to_bits(),
                0.5_f64.to_bits(),
                0.6_f64.to_bits(),
                0.7_f64.to_bits(),
            ],
            authority_index,
        },
        energetic_bits: 0.75_f64.to_bits(),
        refractory_until_generation: 13,
        fractal: receipt(lineage + 5),
        evidence_receipt: receipt(lineage + 6),
        recent_causal_range,
    }
}

fn delivery_authority(marker: u8, port_index: u64) -> DsfDeliveryAuthority {
    DsfDeliveryAuthority {
        field_bank_receipt: receipt(marker),
        kernel_config_receipt: receipt(marker + 1),
        port_index,
        tuple_index: 0,
        trace_receipt: receipt(marker + 2),
        tuple_receipt: receipt(marker + 3),
        basin_receipt: receipt(marker + 4),
    }
}

fn formation(id: u64, kind: FormationKind, member_range: ArenaRange) -> FormationState {
    FormationState {
        id,
        kind,
        member_range,
        structural_impression: receipt(id as u8),
        evidence_receipt: receipt(id as u8 + 1),
    }
}

fn assert_authority_mutation_changes_bytes(mutate: impl FnOnce(&mut DsfDeliveryAuthority)) {
    let baseline = state().encode_unverified(ENCODE_BUDGET).unwrap();
    let mut changed = state();
    mutate(&mut changed.dsf_delivery_authorities[0]);
    let changed_bytes = changed.encode_unverified(ENCODE_BUDGET).unwrap();
    assert_ne!(changed_bytes, baseline);

    let decoded = decode_structure(&changed_bytes, DECODE_BUDGET).unwrap();
    assert_eq!(
        decoded.canonical_unverified_bytes(ENCODE_BUDGET).unwrap(),
        changed_bytes
    );
}

fn state() -> OrganismState {
    OrganismState {
        identity: [7; 16],
        generation: 12,
        prior_state_receipt: receipt(1),
        authenticated_world_revision: receipt(2),
        body_state_receipt: receipt(3),
        // Hash bytes deliberately descend while physical ordinals increase.
        admitted_evidence: vec![causal(100, 250), causal(101, 1)],
        trit_arena: PackedTrits::from_trits(&[-1, 0, 1, 1, 0]).unwrap(),
        causal_receipt_arena: vec![causal(5, 90), causal(7, 20)],
        dsf_delivery_authorities: vec![delivery_authority(30, 0), delivery_authority(40, 1)],
        neurons: vec![
            neuron(10, 3, range(0, 3), range(0, 1), 0),
            neuron(20, 9, range(3, 2), range(1, 1), 1),
        ],
        couplings: vec![CouplingState {
            source_neuron: 0,
            target_neuron: 1,
            numerator: -3,
            denominator: 2,
            causal_receipt: receipt(30),
        }],
        causal_frontier: vec![0, 1],
        formation_member_arena: vec![
            FormationMember::Neuron(0),
            FormationMember::Neuron(1),
            FormationMember::Formation(40),
            FormationMember::Formation(45),
            FormationMember::Formation(50),
            FormationMember::Formation(55),
        ],
        formations: vec![
            formation(40, FormationKind::Mosaic, range(0, 2)),
            formation(45, FormationKind::MosaicOfMosaics, range(2, 1)),
            formation(50, FormationKind::Tapestry, range(3, 1)),
            formation(55, FormationKind::TapestryOfTapestries, range(4, 1)),
            formation(60, FormationKind::Weave, range(5, 1)),
        ],
        stability_evidence_arena: vec![
            receipt(60),
            receipt(61),
            receipt(62),
            receipt(63),
            receipt(64),
        ],
        stability_evidence: StabilityEvidenceRanges {
            coherence: range(0, 1),
            formation_entropy: range(1, 1),
            breathing_variance: range(2, 1),
            uncertainty: range(3, 1),
            tapestry_drift: range(4, 1),
        },
        wake: WakeState::AtBodyTick {
            body_clock_receipt: receipt(70),
            tick: 123_456,
            cause_receipt: receipt(71),
        },
        resources: ResourceObservation {
            cpu_nanoseconds: 80,
            resident_bytes: 81,
            durable_bytes: 82,
            recovery_reserve_bytes: 83,
            python_calls: 1,
            native_calls: 1,
        },
    }
}

#[test]
fn production_crate_round_trip_is_byte_exact_but_unverified() {
    let encoded = state().encode_unverified(ENCODE_BUDGET).unwrap();
    let decoded = decode_structure(&encoded, DECODE_BUDGET).unwrap();
    assert_eq!(
        decoded.canonical_unverified_bytes(ENCODE_BUDGET).unwrap(),
        encoded
    );
    assert_ne!(decoded.source_receipt(), [0; 32]);
}

#[test]
fn causal_chronology_uses_ordinals_not_hash_sorting() {
    assert!(state().validate_structure().is_ok());
    let mut reversed = state();
    reversed.admitted_evidence[1].ordinal = 99;
    assert!(reversed.validate_structure().is_err());
}

#[test]
fn local_l4_slots_change_unverified_structure_without_claiming_authority() {
    let baseline = state().encode_unverified(ENCODE_BUDGET).unwrap();
    for coordinate in 0..7 {
        let mut changed = state();
        changed.neurons[0].local_dsf.coordinate_bits[coordinate] =
            (0.11 + coordinate as f64 / 100.0).to_bits();
        assert_ne!(changed.encode_unverified(ENCODE_BUDGET).unwrap(), baseline);
    }
}

#[test]
fn local_l4_requires_a_canonical_field_bank_binding() {
    let mut missing = state();
    missing.neurons[0].local_dsf.authority_index = 99;
    assert!(missing.validate_structure().is_err());

    let mut reordered = state();
    reordered.dsf_delivery_authorities.swap(0, 1);
    assert!(reordered.validate_structure().is_err());
}

#[test]
fn orphan_delivery_authority_is_rejected() {
    let mut orphaned = state();
    orphaned
        .dsf_delivery_authorities
        .push(delivery_authority(50, 2));
    assert_eq!(
        orphaned.validate_structure().err(),
        Some(CodecError::Invalid(
            "DSF delivery authority is unreferenced"
        ))
    );
}

#[test]
fn every_delivery_authority_field_is_bound_into_unverified_bytes() {
    assert_authority_mutation_changes_bytes(|authority| {
        authority.field_bank_receipt = receipt(31);
    });
    assert_authority_mutation_changes_bytes(|authority| {
        authority.kernel_config_receipt = receipt(32);
    });
    assert_authority_mutation_changes_bytes(|authority| {
        authority.port_index = 9;
    });
    assert_authority_mutation_changes_bytes(|authority| {
        authority.tuple_index = 7;
    });
    assert_authority_mutation_changes_bytes(|authority| {
        authority.trace_receipt = receipt(33);
    });
    assert_authority_mutation_changes_bytes(|authority| {
        authority.tuple_receipt = receipt(34);
    });
    assert_authority_mutation_changes_bytes(|authority| {
        authority.basin_receipt = receipt(35);
    });
}

#[test]
fn decode_is_physically_bounded_before_heap_allocation() {
    let encoded = state().encode_unverified(ENCODE_BUDGET).unwrap();
    let too_small_input = DecodeBudget {
        max_input_bytes: encoded.len() as u64 - 1,
        max_heap_bytes: u64::MAX,
    };
    assert_eq!(
        decode_structure(&encoded, too_small_input).err(),
        Some(CodecError::InputBudgetExceeded)
    );
    let no_heap = DecodeBudget {
        max_input_bytes: encoded.len() as u64,
        max_heap_bytes: 0,
    };
    assert_eq!(
        decode_structure(&encoded, no_heap).err(),
        Some(CodecError::AllocationBudgetExceeded)
    );
    assert_eq!(
        state().encode_unverified(1).err(),
        Some(CodecError::EncodedBudgetExceeded)
    );
}

#[test]
fn packed_arenas_require_unique_positions_and_complete_contiguous_ownership() {
    let mut duplicate_position = state();
    duplicate_position.neurons[1].field_position = 3;
    assert!(duplicate_position.validate_structure().is_err());

    let mut gap = state();
    gap.neurons[1].trit_range.start = 4;
    assert!(gap.validate_structure().is_err());

    let mut unused_member = state();
    unused_member.formations.pop();
    assert!(unused_member.validate_structure().is_err());
}

#[test]
fn recursive_formation_hierarchy_is_enforced() {
    let mut raw_neuron_weave = state();
    raw_neuron_weave.formation_member_arena[5] = FormationMember::Neuron(0);
    assert!(raw_neuron_weave.validate_structure().is_err());

    let mut empty = state();
    empty.formations[0].member_range.len = 0;
    assert!(empty.validate_structure().is_err());
}

#[test]
fn exact_rational_coupling_is_canonical() {
    let mut zero_denominator = state();
    zero_denominator.couplings[0].denominator = 0;
    assert!(zero_denominator.validate_structure().is_err());

    let mut unreduced = state();
    unreduced.couplings[0].numerator = -6;
    unreduced.couplings[0].denominator = 4;
    assert!(unreduced.validate_structure().is_err());
}

#[test]
fn legacy_alternate_layout_trailing_and_every_truncation_fail_closed() {
    let encoded = state().encode_unverified(ENCODE_BUDGET).unwrap();
    let mut legacy = encoded.clone();
    legacy[..8].copy_from_slice(b"OWNERSDB");
    assert_eq!(
        decode_structure(&legacy, DECODE_BUDGET).err(),
        Some(CodecError::BadMagic)
    );

    let mut alternate = encoded.clone();
    alternate[10..26].copy_from_slice(b"SPECIAL_NEURON__");
    assert_eq!(
        decode_structure(&alternate, DECODE_BUDGET).err(),
        Some(CodecError::WrongNeuronLayout)
    );

    let mut trailing = encoded.clone();
    trailing.push(0);
    assert_eq!(
        decode_structure(&trailing, DECODE_BUDGET).err(),
        Some(CodecError::TrailingBytes)
    );

    for cut in 0..encoded.len() {
        assert!(
            decode_structure(&encoded[..cut], DECODE_BUDGET).is_err(),
            "cut {cut}"
        );
    }
}

#[test]
fn schema_v1_is_explicitly_rejected() {
    let mut schema_v1 = state().encode_unverified(ENCODE_BUDGET).unwrap();
    schema_v1[8..10].copy_from_slice(&1_u16.to_le_bytes());
    assert_eq!(
        decode_structure(&schema_v1, DECODE_BUDGET).err(),
        Some(CodecError::UnsupportedVersion(1))
    );
}

#[test]
fn packed_trits_are_total_and_reject_reserved_or_padded_state() {
    assert!(PackedTrits::from_trits(&[2]).is_err());
    let short = PackedTrits {
        trit_len: 5,
        bytes: vec![],
    };
    assert_eq!(short.trit(0), None);
    assert!(short.validate().is_err());
    let reserved = PackedTrits {
        trit_len: 1,
        bytes: vec![0b0000_0011],
    };
    assert!(reserved.validate().is_err());
    let padded = PackedTrits {
        trit_len: 1,
        bytes: vec![0b0000_0101],
    };
    assert!(padded.validate().is_err());
}

#[test]
fn quiescence_is_durable_without_process_clock_state() {
    let mut quiescent = state();
    quiescent.wake = WakeState::Quiescent;
    let encoded = quiescent.encode_unverified(ENCODE_BUDGET).unwrap();
    let decoded = decode_structure(&encoded, DECODE_BUDGET).unwrap();
    assert_eq!(
        decoded.canonical_unverified_bytes(ENCODE_BUDGET).unwrap(),
        encoded
    );
}
