#![allow(dead_code)]

// This target compiles the current carrier in isolation. The carrier is not
// registered in `src/lib.rs` and therefore is not a runtime or production
// claim.

#[path = "../src/current_neuron_carrier.rs"]
mod current_neuron_carrier;

use current_neuron_carrier::{
    BiophysicalSuccessorStatus, CarrierError, CarrierLimits, KrimelackSuccessorStatus,
    MaterializedCarrier, NeuronCarrier,
};
use sha2::{Digest, Sha256};

fn digest(bytes: &[u8]) -> [u8; 32] {
    let value = Sha256::digest(bytes);
    let mut output = [0_u8; 32];
    output.copy_from_slice(&value);
    output
}

fn limits() -> CarrierLimits {
    CarrierLimits::new(8_192, 16_384, 32_768).unwrap()
}

// The population number labels a carrier fixture only. These bytes are not a
// semantic GLJNFT03 golden and do not prove neuronal settlement.
fn opaque_d2_fixture(population: u8, generation: u64) -> Vec<u8> {
    let mut body = Vec::new();
    body.extend_from_slice(b"GLJNFT03");
    body.extend_from_slice(&3_u16.to_le_bytes());
    body.extend_from_slice(&generation.to_le_bytes());
    body.push(population);
    for ordinal in 0..population {
        body.extend_from_slice(&[population, ordinal, population ^ ordinal]);
    }
    body
}

fn carrier(population: u8) -> MaterializedCarrier {
    let body = opaque_d2_fixture(population, 11);
    let inner = NeuronCarrier::retain_authenticated_d2_body(
        11,
        u64::from(population) + 1,
        [0x21; 32],
        Some([0x31; 32]),
        body.clone(),
        digest(&body),
        limits(),
    )
    .unwrap();
    MaterializedCarrier::new(11, inner, limits()).unwrap()
}

#[test]
fn current_only_codec_restarts_byte_identically_for_one_three_and_four_fixtures() {
    for population in [1_u8, 3, 4] {
        let value = carrier(population);
        let requirement = value.resource_requirement().unwrap();
        let encoded = value
            .encode_current(
                requirement.outer_encoded_bytes,
                requirement.inner_encoded_bytes,
            )
            .unwrap();
        let restored = MaterializedCarrier::decode_current(&encoded, limits()).unwrap();
        let restarted = restored
            .encode_current(
                requirement.outer_encoded_bytes,
                requirement.inner_encoded_bytes,
            )
            .unwrap();
        assert_eq!(restarted, encoded);
        assert_eq!(restored, value);
        assert_eq!(
            restored.neuron_carrier().d2_body(),
            opaque_d2_fixture(population, 11)
        );
        assert_eq!(
            restored.neuron_carrier().krimelack_successor_status(),
            KrimelackSuccessorStatus::MissingRatifiedLocalD1ToKLaw
        );
        assert_eq!(
            restored.neuron_carrier().biophysical_successor_status(),
            BiophysicalSuccessorStatus::MissingProductionAnatomyAndIncorporationLaw
        );
    }
}

#[test]
fn detached_successor_is_atomic_for_one_three_and_four_fixtures() {
    for population in [1_u8, 3, 4] {
        let predecessor = carrier(population);
        let predecessor_requirement = predecessor.resource_requirement().unwrap();
        let predecessor_bytes = predecessor
            .encode_current(
                predecessor_requirement.outer_encoded_bytes,
                predecessor_requirement.inner_encoded_bytes,
            )
            .unwrap();
        let successor_body = opaque_d2_fixture(population, 12);
        let successor = predecessor
            .replace_d2_atomically(
                u64::from(population) + 2,
                [0x22; 32],
                Some([0x32; 32]),
                successor_body.clone(),
                digest(&successor_body),
                limits(),
            )
            .unwrap();
        assert_eq!(successor.generation(), predecessor.generation() + 1);
        assert_eq!(
            successor.neuron_carrier().generation(),
            predecessor.neuron_carrier().generation() + 1
        );
        assert_eq!(successor.neuron_carrier().d2_body(), successor_body);
        assert_eq!(
            predecessor
                .encode_current(
                    predecessor_requirement.outer_encoded_bytes,
                    predecessor_requirement.inner_encoded_bytes,
                )
                .unwrap(),
            predecessor_bytes
        );
    }
}

#[test]
fn failed_detached_successor_leaves_predecessor_byte_identical() {
    let predecessor = carrier(4);
    let requirement = predecessor.resource_requirement().unwrap();
    let before = predecessor
        .encode_current(
            requirement.outer_encoded_bytes,
            requirement.inner_encoded_bytes,
        )
        .unwrap();
    let successor_body = opaque_d2_fixture(4, 12);
    let error = predecessor
        .replace_d2_atomically(
            6,
            [0x22; 32],
            Some([0x32; 32]),
            successor_body,
            [0xff; 32],
            limits(),
        )
        .unwrap_err();
    assert_eq!(error, CarrierError::D2BodyReceiptMismatch);
    assert_eq!(
        predecessor
            .encode_current(
                requirement.outer_encoded_bytes,
                requirement.inner_encoded_bytes,
            )
            .unwrap(),
        before
    );
}

#[test]
fn local_successor_refusal_changes_no_state() {
    let value = carrier(1);
    let requirement = value.resource_requirement().unwrap();
    let before = value
        .encode_current(
            requirement.outer_encoded_bytes,
            requirement.inner_encoded_bytes,
        )
        .unwrap();
    assert_eq!(
        value
            .neuron_carrier()
            .refuse_local_d1_to_k_successor()
            .unwrap_err(),
        CarrierError::MissingRatifiedLocalD1ToKLaw
    );
    let after = value
        .encode_current(
            requirement.outer_encoded_bytes,
            requirement.inner_encoded_bytes,
        )
        .unwrap();
    assert_eq!(after, before);
}

#[test]
fn exact_encoded_resource_bound_accepts_exactly_and_refuses_one_byte_less() {
    let value = carrier(3);
    let requirement = value.resource_requirement().unwrap();
    assert_eq!(
        value
            .encode_current(
                requirement.outer_encoded_bytes,
                requirement.inner_encoded_bytes,
            )
            .unwrap()
            .len(),
        requirement.outer_encoded_bytes
    );
    assert_eq!(
        value
            .encode_current(
                requirement.outer_encoded_bytes - 1,
                requirement.inner_encoded_bytes,
            )
            .unwrap_err(),
        CarrierError::OuterBudgetExceeded {
            required: requirement.outer_encoded_bytes,
            available: requirement.outer_encoded_bytes - 1,
        }
    );
    assert_eq!(
        value
            .neuron_carrier()
            .encode_current(requirement.inner_encoded_bytes - 1)
            .unwrap_err(),
        CarrierError::InnerBudgetExceeded {
            required: requirement.inner_encoded_bytes,
            available: requirement.inner_encoded_bytes - 1,
        }
    );

    let successor = carrier(4);
    let successor_requirement = successor.resource_requirement().unwrap();
    assert_eq!(
        requirement
            .atomic_logical_live_bytes_with(successor_requirement)
            .unwrap(),
        requirement.outer_encoded_bytes + successor_requirement.outer_encoded_bytes
    );
}

#[test]
fn current_only_decode_rejects_predecessors_trailing_bytes_and_status_payload_claims() {
    let value = carrier(1);
    let requirement = value.resource_requirement().unwrap();
    let encoded = value
        .encode_current(
            requirement.outer_encoded_bytes,
            requirement.inner_encoded_bytes,
        )
        .unwrap();

    let mut predecessor_outer = encoded.clone();
    predecessor_outer[..8].copy_from_slice(b"GLMFAB04");
    assert_eq!(
        MaterializedCarrier::decode_current(&predecessor_outer, limits()).unwrap_err(),
        CarrierError::BadOuterMagic
    );

    let mut trailing = encoded.clone();
    trailing.push(0);
    assert_eq!(
        MaterializedCarrier::decode_current(&trailing, limits()).unwrap_err(),
        CarrierError::TrailingBytes
    );

    let inner = value
        .neuron_carrier()
        .encode_current(requirement.inner_encoded_bytes)
        .unwrap();
    let mut predecessor_inner = inner.clone();
    predecessor_inner[..8].copy_from_slice(b"GLJNFT03");
    assert_eq!(
        NeuronCarrier::decode_current(&predecessor_inner, limits()).unwrap_err(),
        CarrierError::BadInnerMagic
    );

    // Header + generation + lineage ordinal + source receipt + present digest.
    let krimelack_status_offset = 8 + 2 + 8 + 8 + 32 + 1 + 32;
    let mut invalid_status = inner;
    invalid_status[krimelack_status_offset] = 1;
    assert_eq!(
        NeuronCarrier::decode_current(&invalid_status, limits()).unwrap_err(),
        CarrierError::InvalidKrimelackStatus(1)
    );
}

#[test]
fn retained_d2_body_is_byte_exact_and_receipt_bound_but_not_migrated() {
    let body = opaque_d2_fixture(4, 11);
    let value = carrier(4);
    assert_eq!(value.neuron_carrier().d2_body(), body);
    assert_eq!(value.neuron_carrier().d2_body_receipt(), digest(&body));

    let mut changed = body;
    changed.push(0xaa);
    assert_eq!(
        NeuronCarrier::retain_authenticated_d2_body(
            11,
            5,
            [0x21; 32],
            Some([0x31; 32]),
            changed,
            value.neuron_carrier().d2_body_receipt(),
            limits(),
        )
        .unwrap_err(),
        CarrierError::D2BodyReceiptMismatch
    );
}
