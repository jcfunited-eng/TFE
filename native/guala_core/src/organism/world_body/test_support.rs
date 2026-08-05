use super::*;
use crate::organism::field_binding::{verify_dsf_deliveries, DsfDeliveryVerificationBudget};
use crate::organism::genesis::{
    authenticate_genesis_identity, verify_genesis_identity, GenesisAuthenticationKey,
};
use crate::organism::seal::{
    seal_genesis, verify_genesis, SealDecodeBudget, SealEncodeBudget, SealKey,
};
use crate::organism::{
    ArenaRange, OrganismState, PackedTrits, ResourceObservation, StabilityEvidenceRanges, WakeState,
};
use std::sync::OnceLock;

const IDENTITY: [u8; 16] = [
    0x10, 0x53, 0x2f, 0x91, 0x7b, 0x2d, 0x4a, 0xc8, 0x98, 0x04, 0x46, 0x73, 0x5d, 0xa1, 0x28, 0xfe,
];

static WORLD: OnceLock<Box<[u8]>> = OnceLock::new();
static WORLD_SUCCESSOR: OnceLock<Box<[u8]>> = OnceLock::new();
static BODY_MANIFEST: OnceLock<Box<[u8]>> = OnceLock::new();
static BODY_STATE: OnceLock<Box<[u8]>> = OnceLock::new();
static BODY_STATE_SUCCESSOR: OnceLock<Box<[u8]>> = OnceLock::new();
static CANONICAL_EDGE: OnceLock<Box<[u8]>> = OnceLock::new();

pub(crate) fn world_bytes() -> &'static [u8] {
    WORLD.get_or_init(|| {
        decode_hex(include_str!(
            "../../../tests/fixtures/world_observation_v6.hex"
        ))
    })
}

pub(crate) fn world_successor_bytes() -> &'static [u8] {
    WORLD_SUCCESSOR.get_or_init(|| {
        decode_hex(include_str!(
            "../../../tests/fixtures/world_observation_v6_successor.hex"
        ))
    })
}

pub(crate) fn body_manifest_bytes() -> &'static [u8] {
    BODY_MANIFEST
        .get_or_init(|| decode_hex(include_str!("../../../tests/fixtures/body_manifest_v1.hex")))
}

pub(crate) fn body_state_bytes() -> &'static [u8] {
    BODY_STATE.get_or_init(|| decode_hex(include_str!("../../../tests/fixtures/body_state_v1.hex")))
}

pub(crate) fn body_state_successor_bytes() -> &'static [u8] {
    BODY_STATE_SUCCESSOR.get_or_init(|| {
        decode_hex(include_str!(
            "../../../tests/fixtures/body_state_v1_successor.hex"
        ))
    })
}

pub(crate) fn canonical_edge_bytes() -> &'static [u8] {
    CANONICAL_EDGE.get_or_init(|| {
        decode_hex(include_str!(
            "../../../tests/fixtures/canonical_unicode_control_negative.hex"
        ))
    })
}

pub(crate) fn budget() -> WorldBodyVerificationBudget {
    WorldBodyVerificationBudget {
        max_world_record_bytes: 32_768,
        max_body_manifest_record_bytes: 32_768,
        max_body_state_record_bytes: 8_192,
        max_json_depth: 32,
        max_json_tokens: 100_000,
        max_regions: 4,
        max_portals: 6,
        max_bodies: 4,
        max_objects: 64,
        max_body_quantities: 64,
        max_body_parameters: 1,
        max_body_neurochemical_references: 16,
        max_body_changes_per_transition: 4,
        max_body_conservation_exchanges_per_transition: 1,
        max_body_transitions: 1_024,
        max_body_cold_state_bytes: 16 * 1024 * 1024,
        max_fraction_bits: 4_096,
    }
}

pub(crate) fn mounts() -> (WorldAuthorityMount, BodyAuthorityMount) {
    (
        world_mount(
            WorldAuthorityLimits::new(4, 6, 4, 64).expect("world limits"),
            vec![
                WorldActorPort::new("guala.embodiment.w1".to_owned(), "guala-body-1".to_owned())
                    .expect("self port"),
                WorldActorPort::new(
                    "guala.embodiment.w1.body-2".to_owned(),
                    "w1-body-2".to_owned(),
                )
                .expect("second port"),
            ],
        ),
        BodyAuthorityMount::new(
            BodyAuthorityMountEpoch::new(29).expect("body epoch"),
            vec![0x22; 32],
        )
        .expect("body mount"),
    )
}

pub(crate) fn world_mount(
    limits: WorldAuthorityLimits,
    actor_ports: Vec<WorldActorPort>,
) -> WorldAuthorityMount {
    WorldAuthorityMount::new(
        WorldAuthorityMountEpoch::new(11).expect("world epoch"),
        vec![0x11; 32],
        limits,
        actor_ports,
    )
    .expect("world mount")
}

pub(crate) fn authenticated_current() -> (
    AuthenticatedWorldObservation,
    AuthenticatedBodyManifestState,
) {
    let (world_mount, body_mount) = mounts();
    let world = authenticate_world_observation(&world_mount, world_bytes(), budget())
        .expect("authenticated current world");
    let body = authenticate_body_manifest_state(
        &body_mount,
        body_manifest_bytes(),
        body_state_bytes(),
        budget(),
    )
    .expect("authenticated current body");
    (world, body)
}

pub(crate) fn verified_successor_fixture() -> (
    WorldBodyVerifiedSeal,
    AuthenticatedWorldObservation,
    AuthenticatedBodyManifestState,
) {
    let (world_mount, body_mount) = mounts();
    let current_world = authenticate_world_observation(&world_mount, world_bytes(), budget())
        .expect("current world");
    let current_body = authenticate_body_manifest_state(
        &body_mount,
        body_manifest_bytes(),
        body_state_bytes(),
        budget(),
    )
    .expect("current body");
    let current = bind_world_body(dsf(), current_world, current_body).expect("current binding");
    let successor_world =
        authenticate_world_observation(&world_mount, world_successor_bytes(), budget())
            .expect("successor world");
    let successor_body = authenticate_body_manifest_state(
        &body_mount,
        body_manifest_bytes(),
        body_state_successor_bytes(),
        budget(),
    )
    .expect("successor body");
    (current, successor_world, successor_body)
}

pub(crate) fn fixture_receipt(bytes: &[u8], name: &'static str) -> [u8; 32] {
    let value: Value = serde_json::from_slice(bytes).expect("fixture JSON");
    digest_field(
        value.as_object().expect("fixture record"),
        "authority_receipt_sha256",
        name,
    )
    .expect("fixture receipt")
}

pub(crate) fn dsf() -> DsfDeliveryVerifiedSeal {
    let state = OrganismState {
        identity: IDENTITY,
        generation: 0,
        prior_state_receipt: [0; 32],
        authenticated_world_revision: fixture_receipt(world_bytes(), "fixture world"),
        body_state_receipt: fixture_receipt(body_state_bytes(), "fixture body"),
        admitted_evidence: vec![],
        trit_arena: PackedTrits::from_trits(&[]).expect("empty trits"),
        causal_receipt_arena: vec![],
        dsf_delivery_authorities: vec![],
        neurons: vec![],
        couplings: vec![],
        causal_frontier: vec![],
        formation_member_arena: vec![],
        formations: vec![],
        stability_evidence_arena: vec![],
        stability_evidence: StabilityEvidenceRanges {
            coherence: ArenaRange { start: 0, len: 0 },
            formation_entropy: ArenaRange { start: 0, len: 0 },
            breathing_variance: ArenaRange { start: 0, len: 0 },
            uncertainty: ArenaRange { start: 0, len: 0 },
            tapestry_drift: ArenaRange { start: 0, len: 0 },
        },
        wake: WakeState::Quiescent,
        resources: ResourceObservation {
            cpu_nanoseconds: 0,
            resident_bytes: 0,
            durable_bytes: 0,
            recovery_reserve_bytes: 0,
            python_calls: 0,
            native_calls: 0,
        },
    };
    let seal_key = SealKey::new(7, [0x44; 32]).expect("seal key");
    let encoded = seal_genesis(
        &state,
        &seal_key,
        &[],
        SealEncodeBudget {
            max_organism_bytes: 1_000_000,
            max_output_bytes: 1_000_000,
            max_bank_bindings: 1,
        },
    )
    .expect("seal genesis");
    let trusted_head: [u8; 32] = Sha256::digest(&encoded).into();
    let genesis_key = GenesisAuthenticationKey::new(3, [0x55; 32]).expect("genesis key");
    let record = authenticate_genesis_identity(IDENTITY, &genesis_key).expect("genesis record");
    let identity = verify_genesis_identity(record.as_bytes(), &genesis_key, record.trusted_head())
        .expect("verified genesis");
    let custody = verify_genesis(
        &encoded,
        &seal_key,
        trusted_head,
        &identity,
        SealDecodeBudget {
            max_input_bytes: 1_000_000,
            max_organism_bytes: 1_000_000,
            max_decoded_heap_bytes: 1_000_000,
            max_bank_bindings: 1,
        },
    )
    .expect("verified custody");
    verify_dsf_deliveries(
        custody,
        &[],
        DsfDeliveryVerificationBudget {
            max_candidate_count: 0,
            max_single_candidate_bytes: 1,
            max_total_candidate_bytes: 1,
            max_single_generated_bank_bytes: 1,
            max_total_generated_bank_bytes: 1,
            max_total_port_count: 1,
            max_total_sample_count: 1,
            max_total_field_row_count: 1,
            max_authority_count: 0,
            max_neuron_count: 0,
            max_verified_row_bytes: 0,
        },
    )
    .expect("verified empty DSF delivery set")
}

fn decode_hex(source: &str) -> Box<[u8]> {
    let source = source.strip_suffix('\n').unwrap_or(source);
    assert_eq!(source.len() % 2, 0, "fixture hex length");
    let bytes = source.as_bytes();
    let mut result = Vec::with_capacity(source.len() / 2);
    for pair in bytes.chunks_exact(2) {
        result.push((nibble(pair[0]) << 4) | nibble(pair[1]));
    }
    result.into_boxed_slice()
}

fn nibble(value: u8) -> u8 {
    match value {
        b'0'..=b'9' => value - b'0',
        b'a'..=b'f' => value - b'a' + 10,
        _ => panic!("fixture contains non-hexadecimal byte"),
    }
}
