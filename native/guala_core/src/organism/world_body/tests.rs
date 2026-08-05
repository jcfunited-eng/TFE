use super::test_support::*;
use super::*;

fn mutate(bytes: &[u8], change: impl FnOnce(&mut Value)) -> Vec<u8> {
    let mut value: Value = serde_json::from_slice(bytes).expect("fixture JSON");
    change(&mut value);
    serde_json::to_vec(&value).expect("canonical mutation")
}

fn authenticate_world_with(
    bytes: &[u8],
    mount: &WorldAuthorityMount,
    limits: WorldBodyVerificationBudget,
) -> Result<AuthenticatedWorldObservation, WorldBodyVerificationError> {
    authenticate_world_observation(mount, bytes, limits)
}

#[test]
fn python_golden_records_authenticate_then_bind_after_dsf() {
    let (world_mount, body_mount) = mounts();
    let world = authenticate_world_observation(&world_mount, world_bytes(), budget())
        .expect("world authentication");
    let body = authenticate_body_manifest_state(
        &body_mount,
        body_manifest_bytes(),
        body_state_bytes(),
        budget(),
    )
    .expect("body authentication");
    assert_eq!(world.revision(), 0);
    assert_eq!(body.sequence(), 0);
    assert_eq!(
        body.source_time(),
        &BigRational::from_integer(BigInt::zero())
    );
    assert_eq!(body.prior_state_receipt(), None);
    assert_eq!(body.causal_source_receipt(), None);
    assert_eq!(world.canonical_record_bytes(), world_bytes());
    assert_eq!(body.manifest_record_bytes(), body_manifest_bytes());
    assert_eq!(body.state_record_bytes(), body_state_bytes());

    let verified = bind_world_body(dsf(), world, body).expect("world/body binding");
    assert_eq!(verified.world_revision(), 0);
    assert_eq!(verified.body_sequence(), 0);
    assert_eq!(verified.world_mount_epoch().get(), 11);
    assert_eq!(verified.body_mount_epoch().get(), 29);
    assert_eq!(
        verified.world_receipt(),
        verified.state().authenticated_world_revision
    );
    assert_eq!(
        verified.body_state_receipt(),
        verified.state().body_state_receipt
    );
}

#[test]
fn authority_produced_successors_expose_exact_lineage() {
    let (current, world, body) = verified_successor_fixture();
    assert_eq!(world.revision(), current.world_revision() + 1);
    assert_ne!(world.receipt(), current.world_receipt());
    assert_eq!(body.sequence(), current.body_sequence() + 1);
    assert_eq!(
        body.prior_state_receipt(),
        Some(current.body_state_receipt())
    );
    assert_eq!(body.causal_source_receipt(), Some(world.receipt()));
}

#[test]
fn record_and_json_budgets_fail_closed_before_promotion() {
    let (world_mount, body_mount) = mounts();
    let mut limits = budget();
    limits.max_world_record_bytes = (world_bytes().len() - 1) as u64;
    assert!(matches!(
        authenticate_world_observation(&world_mount, world_bytes(), limits),
        Err(WorldBodyVerificationError::InputBudgetExceeded(
            "world observation"
        ))
    ));

    let mut limits = budget();
    limits.max_body_manifest_record_bytes = (body_manifest_bytes().len() - 1) as u64;
    assert!(matches!(
        authenticate_body_manifest_state(
            &body_mount,
            body_manifest_bytes(),
            body_state_bytes(),
            limits,
        ),
        Err(WorldBodyVerificationError::InputBudgetExceeded(
            "body manifest"
        ))
    ));

    let mut limits = budget();
    limits.max_body_state_record_bytes = (body_state_bytes().len() - 1) as u64;
    assert!(matches!(
        authenticate_body_manifest_state(
            &body_mount,
            body_manifest_bytes(),
            body_state_bytes(),
            limits,
        ),
        Err(WorldBodyVerificationError::InputBudgetExceeded(
            "body state"
        ))
    ));

    let mut limits = budget();
    limits.max_json_tokens = 8;
    assert!(matches!(
        authenticate_world_observation(&world_mount, world_bytes(), limits),
        Err(WorldBodyVerificationError::JsonBudgetExceeded(
            "world observation"
        ))
    ));
}

#[test]
fn nested_exact_keys_types_and_integer_bounds_fail_closed() {
    let (world_mount, _) = mounts();
    let extra_key = mutate(world_bytes(), |root| {
        root["room_bounds"]["invented"] = Value::Null;
    });
    assert!(matches!(
        authenticate_world_with(&extra_key, &world_mount, budget()),
        Err(WorldBodyVerificationError::WrongShape("world bounds"))
    ));

    let wrong_type = mutate(world_bytes(), |root| {
        root["bodies"][0]["held_object_id"] = Value::from(7);
    });
    assert!(matches!(
        authenticate_world_with(&wrong_type, &world_mount, budget()),
        Err(WorldBodyVerificationError::InvalidValue(
            "world held object"
        ))
    ));

    let outside_bound = mutate(world_bytes(), |root| {
        root["bodies"][0]["radius_mm"] = Value::from(1_000_001_u64);
    });
    assert!(matches!(
        authenticate_world_with(&outside_bound, &world_mount, budget()),
        Err(WorldBodyVerificationError::InvalidValue(
            "world body radius"
        ))
    ));
}

#[test]
fn configured_limits_are_semantic_and_separate_from_admission_budgets() {
    let mount = world_mount(
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
    );
    let mut limits = budget();
    limits.max_objects = 1;
    assert!(matches!(
        authenticate_world_with(world_bytes(), &mount, limits),
        Err(WorldBodyVerificationError::InputBudgetExceeded(
            "world configured authority limits"
        ))
    ));

    let exact_mount = world_mount(
        WorldAuthorityLimits::new(3, 2, 2, 1).expect("exact mounted limits"),
        vec![
            WorldActorPort::new("guala.embodiment.w1".to_owned(), "guala-body-1".to_owned())
                .expect("self port"),
            WorldActorPort::new(
                "guala.embodiment.w1.body-2".to_owned(),
                "w1-body-2".to_owned(),
            )
            .expect("second port"),
        ],
    );
    assert!(authenticate_world_with(world_bytes(), &exact_mount, budget()).is_ok());
}

#[test]
fn actor_port_reciprocity_and_canonical_self_port_fail_closed() {
    let wrong_actor = world_mount(
        WorldAuthorityLimits::new(4, 6, 4, 64).expect("world limits"),
        vec![
            WorldActorPort::new("guala.embodiment.w1".to_owned(), "outside-body".to_owned())
                .expect("outside port"),
            WorldActorPort::new(
                "guala.embodiment.w1.body-2".to_owned(),
                "w1-body-2".to_owned(),
            )
            .expect("second port"),
        ],
    );
    assert!(matches!(
        authenticate_world_with(world_bytes(), &wrong_actor, budget()),
        Err(WorldBodyVerificationError::InvalidValue(
            "world actor reciprocity"
        ))
    ));

    let wrong_self_port = world_mount(
        WorldAuthorityLimits::new(4, 6, 4, 64).expect("world limits"),
        vec![
            WorldActorPort::new("a.noncanonical.self".to_owned(), "guala-body-1".to_owned())
                .expect("wrong self port"),
            WorldActorPort::new(
                "guala.embodiment.w1.body-2".to_owned(),
                "w1-body-2".to_owned(),
            )
            .expect("second port"),
        ],
    );
    assert!(matches!(
        authenticate_world_with(world_bytes(), &wrong_self_port, budget()),
        Err(WorldBodyVerificationError::InvalidValue(
            "world self actor port"
        ))
    ));
}

#[test]
fn region_portal_flow_and_room_projection_laws_fail_closed() {
    let (world_mount, _) = mounts();
    let wrong_plane = mutate(world_bytes(), |root| {
        root["portals"][0]["plane_mm"] = Value::from(5_001);
    });
    assert!(matches!(
        authenticate_world_with(&wrong_plane, &world_mount, budget()),
        Err(WorldBodyVerificationError::InvalidValue(
            "world portal aperture"
        ))
    ));

    let evacuation = mutate(world_bytes(), |root| {
        root["portals"][0]["air_flow_cubic_mm_per_second"] = Value::from((1_u64 << 63) - 1);
    });
    assert!(matches!(
        authenticate_world_with(&evacuation, &world_mount, budget()),
        Err(WorldBodyVerificationError::InvalidValue(
            "world portal air evacuation"
        ))
    ));

    let room_projection = mutate(world_bytes(), |root| {
        root["room_bounds"] = root["regions"][1]["bounds"].clone();
    });
    assert!(matches!(
        authenticate_world_with(&room_projection, &world_mount, budget()),
        Err(WorldBodyVerificationError::InvalidValue(
            "world room projection"
        ))
    ));
}

#[test]
fn hold_reciprocity_contact_and_containment_laws_fail_closed() {
    let (world_mount, _) = mounts();
    let hold = mutate(world_bytes(), |root| {
        let object_id = root["objects"][0]["object_id"].clone();
        root["bodies"][0]["held_object_id"] = object_id;
    });
    assert!(matches!(
        authenticate_world_with(&hold, &world_mount, budget()),
        Err(WorldBodyVerificationError::InvalidValue(
            "world holding reciprocity"
        ))
    ));

    let contact = mutate(world_bytes(), |root| {
        root["bodies"][0]["active_contact"] = serde_json::json!({
            "contact_patch_square_mm": 1,
            "duration_microseconds": 1000,
            "kind": "touch",
            "object_id": root["objects"][0]["object_id"].clone(),
        });
    });
    assert!(matches!(
        authenticate_world_with(&contact, &world_mount, budget()),
        Err(WorldBodyVerificationError::InvalidValue(
            "world contact geometry"
        ))
    ));

    let containment = mutate(world_bytes(), |root| {
        root["objects"][0]["position"]["x_mm"] = Value::from(-1);
    });
    assert!(matches!(
        authenticate_world_with(&containment, &world_mount, budget()),
        Err(WorldBodyVerificationError::InvalidValue(
            "world object geometry"
        ))
    ));
}

#[test]
fn all_three_collision_families_fail_closed() {
    let (world_mount, _) = mounts();
    let body_body = mutate(world_bytes(), |root| {
        root["bodies"][1]["pose"]["position"] = root["bodies"][0]["pose"]["position"].clone();
    });
    assert!(matches!(
        authenticate_world_with(&body_body, &world_mount, budget()),
        Err(WorldBodyVerificationError::InvalidValue(
            "world body collision"
        ))
    ));

    let body_object = mutate(world_bytes(), |root| {
        root["objects"][0]["position"] = root["bodies"][0]["pose"]["position"].clone();
    });
    assert!(matches!(
        authenticate_world_with(&body_object, &world_mount, budget()),
        Err(WorldBodyVerificationError::InvalidValue(
            "world body/object collision"
        ))
    ));

    let object_object = mutate(world_bytes(), |root| {
        let mut second = root["objects"][0].clone();
        second["object_id"] = Value::String("Z-object-2".to_owned());
        root["objects"]
            .as_array_mut()
            .expect("objects")
            .push(second);
    });
    assert!(matches!(
        authenticate_world_with(&object_object, &world_mount, budget()),
        Err(WorldBodyVerificationError::InvalidValue(
            "world object collision"
        ))
    ));
}

#[test]
fn optical_palette_cell_extent_and_usage_laws_fail_closed() {
    let (world_mount, _) = mounts();
    let unused_palette = mutate(world_bytes(), |root| {
        root["objects"][0]["optical_surface"]["cell_palette_indices"] = serde_json::json!([0, 0]);
    });
    assert!(matches!(
        authenticate_world_with(&unused_palette, &world_mount, budget()),
        Err(WorldBodyVerificationError::InvalidValue(
            "optical palette usage"
        ))
    ));

    let wrong_extent = mutate(world_bytes(), |root| {
        root["objects"][0]["optical_surface"]["columns"] = Value::from(3);
    });
    assert!(matches!(
        authenticate_world_with(&wrong_extent, &world_mount, budget()),
        Err(WorldBodyVerificationError::InvalidValue("optical cells"))
    ));
}

#[test]
fn python_canonical_unicode_control_negative_and_strip_boundary_match() {
    let value: Value =
        serde_json::from_slice(canonical_edge_bytes()).expect("canonical edge fixture JSON");
    assert_eq!(
        canonical_value(&value).expect("Rust canonical edge"),
        canonical_edge_bytes()
    );
    assert!(canonical_edge_bytes().windows(2).any(|pair| pair == b"-7"));
    assert!(canonical_edge_bytes()
        .windows(2)
        .any(|pair| pair == [0xc3, 0xa9]));
    assert!(canonical_edge_bytes()
        .windows(6)
        .any(|window| window == br"\u0001"));
    assert!(identifier("\u{001c}edge", "identifier").is_err());
    assert!(identifier("edge\u{001f}", "identifier").is_err());
    assert!(identifier("inside\u{001c}edge", "identifier").is_ok());
    assert!(bounded_text("\u{3000}reason", MAX_REASON_BYTES, "reason").is_err());
}

#[test]
fn noncanonical_bytes_wrong_keys_domains_and_receipts_fail_closed() {
    let (world_mount, _) = mounts();
    let mut whitespace = world_bytes().to_vec();
    whitespace.push(b' ');
    assert!(matches!(
        authenticate_world_with(&whitespace, &world_mount, budget()),
        Err(WorldBodyVerificationError::NoncanonicalJson(
            "world observation"
        ))
    ));

    let wrong_body = BodyAuthorityMount::new(
        BodyAuthorityMountEpoch::new(29).expect("body epoch"),
        vec![0x11; 32],
    )
    .expect("wrong body mount");
    assert!(matches!(
        authenticate_body_manifest_state(
            &wrong_body,
            body_manifest_bytes(),
            body_state_bytes(),
            budget(),
        ),
        Err(WorldBodyVerificationError::AuthenticationFailed(
            "body manifest"
        ))
    ));

    let changed_receipt = mutate(world_bytes(), |root| {
        root["authority_receipt_sha256"] = Value::String("00".repeat(32));
    });
    assert!(matches!(
        authenticate_world_with(&changed_receipt, &world_mount, budget()),
        Err(WorldBodyVerificationError::ReceiptMismatch(
            "world observation"
        ))
    ));
}

#[test]
fn body_manifest_state_fractions_capacity_topology_and_lineage_fail_closed() {
    let (_, body_mount) = mounts();
    let changed_fraction = mutate(body_state_bytes(), |root| {
        root["source_time"] = Value::String("2/4".to_owned());
    });
    assert!(matches!(
        authenticate_body_manifest_state(
            &body_mount,
            body_manifest_bytes(),
            &changed_fraction,
            budget(),
        ),
        Err(WorldBodyVerificationError::InvalidValue(
            "body state source time"
        ))
    ));

    let oversized_fraction = mutate(body_state_bytes(), |root| {
        root["source_time"] = Value::String(format!("{}/1", "9".repeat(1_234)));
    });
    assert!(matches!(
        authenticate_body_manifest_state(
            &body_mount,
            body_manifest_bytes(),
            &oversized_fraction,
            budget(),
        ),
        Err(WorldBodyVerificationError::InvalidValue(
            "body state source time"
        ))
    ));

    let changed_manifest = mutate(body_state_bytes(), |root| {
        root["manifest_receipt_sha256"] = Value::String("00".repeat(32));
    });
    assert!(matches!(
        authenticate_body_manifest_state(
            &body_mount,
            body_manifest_bytes(),
            &changed_manifest,
            budget(),
        ),
        Err(WorldBodyVerificationError::ReceiptMismatch(
            "body state manifest"
        ))
    ));

    let mut limits = budget();
    limits.max_body_quantities = 25;
    assert!(matches!(
        authenticate_body_manifest_state(
            &body_mount,
            body_manifest_bytes(),
            body_state_bytes(),
            limits,
        ),
        Err(WorldBodyVerificationError::InputBudgetExceeded(
            "body declared capacity"
        ))
    ));

    let changed_topology = mutate(body_state_bytes(), |root| {
        root["quantity_values"]
            .as_array_mut()
            .expect("values")
            .swap(0, 1);
    });
    assert!(matches!(
        authenticate_body_manifest_state(
            &body_mount,
            body_manifest_bytes(),
            &changed_topology,
            budget(),
        ),
        Err(WorldBodyVerificationError::InvalidValue(
            "body quantity value topology"
        ))
    ));
}

#[test]
fn organism_binding_rejects_independently_valid_wrong_revision() {
    let (world_mount, body_mount) = mounts();
    let successor = authenticate_world_observation(&world_mount, world_successor_bytes(), budget())
        .expect("successor world");
    let current_body = authenticate_body_manifest_state(
        &body_mount,
        body_manifest_bytes(),
        body_state_bytes(),
        budget(),
    )
    .expect("current body");
    assert!(matches!(
        bind_world_body(dsf(), successor, current_body),
        Err(WorldBodyVerificationError::OrganismReceiptMismatch(
            "world revision"
        ))
    ));
}

#[test]
fn mount_epochs_are_external_distinct_types_not_artifact_claims() {
    assert!(WorldAuthorityMountEpoch::new(0).is_err());
    assert!(BodyAuthorityMountEpoch::new(0).is_err());
    let world = WorldAuthorityMountEpoch::new(1).expect("world epoch");
    let body = BodyAuthorityMountEpoch::new(1).expect("body epoch");
    assert_eq!(world.get(), body.get());
}
