#![deny(warnings)]

#[path = "../src/immutable_evidence_store.rs"]
mod immutable_evidence_store;

use immutable_evidence_store::*;
use std::collections::BTreeMap;
use std::sync::Arc;

struct RestartStore {
    objects: BTreeMap<ContentAddress, Arc<[u8]>>,
}

impl ImmutableObjectResolver for RestartStore {
    fn resolve(&self, address: ContentAddress) -> Option<Arc<[u8]>> {
        self.objects.get(&address).cloned()
    }
}

fn envelope(max_objects: usize, max_object_bytes: usize) -> DeltaEnvelope {
    DeltaEnvelope {
        max_objects,
        max_object_bytes,
    }
}

#[test]
fn identical_body_is_one_object_and_one_byte_charge() {
    let mut builder = BoundedImmutableDeltaBuilder::new(envelope(1, 4)).unwrap();
    let first = builder.add(b"same".to_vec()).unwrap();
    let second = builder.add(b"same".to_vec()).unwrap();
    assert_eq!(first, second);
    assert_eq!(builder.object_count(), 1);
    assert_eq!(builder.total_object_bytes(), 4);
    assert_eq!(builder.objects().get(&first).unwrap().as_ref(), b"same");
}

#[test]
fn absent_declared_address_with_wrong_body_is_rejected() {
    let mut builder = BoundedImmutableDeltaBuilder::new(envelope(1, 16)).unwrap();
    let declared = ContentAddress::of(b"declared");
    let derived = ContentAddress::of(b"different");
    let error = builder
        .add_addressed(AddressedImmutableObject {
            address: declared,
            bytes: Arc::from(b"different".to_vec()),
        })
        .unwrap_err();
    assert_eq!(error, Error::AddressBodyMismatch { declared, derived });
}

#[test]
fn different_body_at_an_admitted_address_is_a_collision() {
    let mut builder = BoundedImmutableDeltaBuilder::new(envelope(2, 32)).unwrap();
    let address = builder.add(b"first".to_vec()).unwrap();
    let error = builder
        .add_addressed(AddressedImmutableObject {
            address,
            bytes: Arc::from(b"second".to_vec()),
        })
        .unwrap_err();
    assert_eq!(error, Error::AddressCollision(address));
}

#[test]
fn object_and_byte_bounds_are_exact_and_deduplication_does_not_consume_them() {
    let mut object_bounded = BoundedImmutableDeltaBuilder::new(envelope(1, 64)).unwrap();
    object_bounded.add(b"one".to_vec()).unwrap();
    object_bounded.add(b"one".to_vec()).unwrap();
    assert_eq!(
        object_bounded.add(b"two".to_vec()).unwrap_err(),
        Error::ObjectBudgetExceeded {
            required: 2,
            admitted: 1,
        }
    );

    let mut byte_bounded = BoundedImmutableDeltaBuilder::new(envelope(2, 5)).unwrap();
    byte_bounded.add(b"123".to_vec()).unwrap();
    assert_eq!(
        byte_bounded.add(b"456".to_vec()).unwrap_err(),
        Error::ByteBudgetExceeded {
            required: 6,
            admitted: 5,
        }
    );
}

#[test]
fn root_and_accounting_are_deterministic_across_insertion_order() {
    let mut forward = BoundedImmutableDeltaBuilder::new(envelope(2, 16)).unwrap();
    forward.add(b"alpha".to_vec()).unwrap();
    forward.add(b"beta".to_vec()).unwrap();
    let forward = forward.finish().unwrap();

    let mut reverse = BoundedImmutableDeltaBuilder::new(envelope(2, 16)).unwrap();
    reverse.add(b"beta".to_vec()).unwrap();
    reverse.add(b"alpha".to_vec()).unwrap();
    let reverse = reverse.finish().unwrap();

    assert_eq!(forward.root, reverse.root);
    assert_eq!(forward.objects, reverse.objects);
    assert_eq!(forward.accounting, reverse.accounting);
    assert_eq!(forward.accounting.object_count, 2);
    assert_eq!(forward.accounting.total_object_bytes, 9);
    assert_eq!(
        forward.accounting.root_input_bytes,
        b"GUALA_IMMUTABLE_EVIDENCE_DELTA_ROOT_V1".len() + 8 + 2 * 40
    );
}

#[test]
fn canonical_restart_replay_reconstitutes_the_same_delta_and_refuses_divergence() {
    let mut builder = BoundedImmutableDeltaBuilder::new(envelope(3, 32)).unwrap();
    builder.add(b"episode".to_vec()).unwrap();
    builder.add(b"capital".to_vec()).unwrap();
    let original = builder.finish().unwrap();

    let replayed =
        BoundedImmutableDeltaBuilder::replay(&original.objects, envelope(3, 32), original.root)
            .unwrap();
    assert_eq!(replayed, original);

    let restart_store = RestartStore {
        objects: replayed
            .objects
            .iter()
            .map(|object| (object.address, object.bytes.clone()))
            .collect(),
    };
    for object in &replayed.objects {
        assert_eq!(restart_store.resolve(object.address).unwrap(), object.bytes);
    }

    let wrong_root = ContentAddress::of(b"wrong root");
    assert_eq!(
        BoundedImmutableDeltaBuilder::replay(&original.objects, envelope(3, 32), wrong_root,)
            .unwrap_err(),
        Error::ReplayRootMismatch {
            expected: wrong_root,
            actual: original.root,
        }
    );

    let mut noncanonical = original.objects.clone();
    noncanonical.reverse();
    assert_eq!(
        BoundedImmutableDeltaBuilder::replay(&noncanonical, envelope(3, 32), original.root,)
            .unwrap_err(),
        Error::NonCanonicalReplay
    );
}
