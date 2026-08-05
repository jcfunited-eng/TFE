//! Exact post-DSF verification for the existing non-cognitive world and body authorities.
//!
//! This module authenticates only current world-observation-v6 and internal-body
//! manifest/state-v1 records. It does not execute either Python authority, infer a
//! common clock, verify wake/cognition, or assign meaning to any other organism receipt.

use super::field_binding::DsfDeliveryVerifiedSeal;
use hmac::{Hmac, Mac};
use num_bigint::BigInt;
use num_rational::BigRational;
use num_traits::Zero;
use serde_json::{Map, Value};
use sha2::{Digest, Sha256};
use std::collections::{BTreeMap, BTreeSet};
use std::fmt;
use zeroize::Zeroizing;

mod world;

type HmacSha256 = Hmac<Sha256>;

const WORLD_OBSERVATION_SCHEMA: &str = "guala.embodiment.observation.v6";
const WORLD_OBSERVATION_DOMAIN: &[u8] = b"guala-embodiment-observation-v6\0";
const BODY_MANIFEST_SCHEMA: &str = "guala.physical_internal_body.manifest.v1";
const BODY_MANIFEST_DOMAIN: &[u8] = b"guala-physical-internal-body-manifest-v1\0";
const BODY_STATE_SCHEMA: &str = "guala.physical_internal_body.state.v1";
const BODY_STATE_DOMAIN: &[u8] = b"guala-physical-internal-body-state-v1\0";

const MAX_WORLD_KEY_BYTES: usize = 4_096;
const MIN_BODY_KEY_BYTES: usize = 32;
const MAX_BODY_KEY_BYTES: usize = 4_096;
const MAX_IDENTIFIER_BYTES: usize = 256;
const MAX_REASON_BYTES: usize = 2_048;
const BODY_MAX_FRACTION_BITS: u64 = 4_096;
const WORLD_MAX_REGIONS: u64 = 4;
const WORLD_MAX_PORTALS: u64 = 6;
const WORLD_MAX_BODIES: u64 = 4;
const WORLD_MAX_OBJECTS: u64 = 64;
const WORLD_MAX_REVISION: u64 = (1_u64 << 63) - 1;

const WORLD_RECORD_KEYS: &[&str] = &[
    "authority_hmac_sha256",
    "authority_receipt_sha256",
    "bodies",
    "objects",
    "portals",
    "regions",
    "revision",
    "room_bounds",
    "room_id",
    "schema",
    "self_body_id",
    "state_sha256",
];
const BODY_MANIFEST_RECORD_KEYS: &[&str] = &[
    "authority_hmac_sha256",
    "authority_receipt_sha256",
    "capacity",
    "manifest_id",
    "mechanisms",
    "neurochemical_references",
    "parameters",
    "quantities",
    "schema",
    "structural_time_unit",
];
const BODY_STATE_RECORD_KEYS: &[&str] = &[
    "authority_hmac_sha256",
    "authority_receipt_sha256",
    "causal_source_receipt_sha256",
    "manifest_receipt_sha256",
    "neurochemical_reference_receipts",
    "prior_state_receipt_sha256",
    "quantity_values",
    "schema",
    "sequence",
    "source_time",
    "unavailable_mechanisms",
];
const CAPACITY_KEYS: &[&str] = &[
    "max_changes_per_transition",
    "max_conservation_exchanges_per_transition",
    "max_neurochemical_references",
    "max_parameters",
    "max_quantities",
    "max_state_bytes",
    "max_transitions",
];
const MECHANISM_KEYS: &[&str] = &[
    "availability",
    "mechanism",
    "quantity_ids",
    "required_parameter_ids",
    "unavailable_reason",
];
const QUANTITY_KEYS: &[&str] = &[
    "conservation_group_id",
    "cyclic_modulus",
    "evolution_kind",
    "initial_value",
    "lower_bound",
    "mechanism",
    "quantity_id",
    "role",
    "unit",
    "upper_bound",
];
const PARAMETER_KEYS: &[&str] = &[
    "derivation_receipt_sha256",
    "mechanism",
    "parameter_id",
    "unit",
    "value",
];
const REFERENCE_KEYS: &[&str] = &[
    "compartment_receipt_sha256",
    "manifest_receipt_sha256",
    "node_id",
    "quantity_unit",
    "reference_id",
    "species_id",
];
const MECHANISMS: &[&str] = &[
    "proprioception",
    "vestibular",
    "thermal",
    "nociception",
    "energy_water",
    "respiration",
    "circulation",
    "visceral",
    "fatigue_recovery",
    "circadian",
    "neurochemical",
];

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) struct WorldAuthorityMountEpoch(u32);

impl WorldAuthorityMountEpoch {
    pub(crate) fn new(value: u32) -> Result<Self, WorldBodyVerificationError> {
        if value == 0 {
            return Err(WorldBodyVerificationError::InvalidMount(
                "world epoch is zero",
            ));
        }
        Ok(Self(value))
    }

    pub(crate) fn get(self) -> u32 {
        self.0
    }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) struct BodyAuthorityMountEpoch(u32);

impl BodyAuthorityMountEpoch {
    pub(crate) fn new(value: u32) -> Result<Self, WorldBodyVerificationError> {
        if value == 0 {
            return Err(WorldBodyVerificationError::InvalidMount(
                "body epoch is zero",
            ));
        }
        Ok(Self(value))
    }

    pub(crate) fn get(self) -> u32 {
        self.0
    }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) struct WorldAuthorityLimits {
    max_regions: u64,
    max_portals: u64,
    max_bodies: u64,
    max_objects: u64,
}

impl WorldAuthorityLimits {
    pub(crate) fn new(
        max_regions: u64,
        max_portals: u64,
        max_bodies: u64,
        max_objects: u64,
    ) -> Result<Self, WorldBodyVerificationError> {
        if !(3..=WORLD_MAX_REGIONS).contains(&max_regions)
            || !(2..=WORLD_MAX_PORTALS).contains(&max_portals)
            || !(2..=WORLD_MAX_BODIES).contains(&max_bodies)
            || !(1..=WORLD_MAX_OBJECTS).contains(&max_objects)
        {
            return Err(WorldBodyVerificationError::InvalidMount(
                "world semantic limits differ from the authority contract",
            ));
        }
        Ok(Self {
            max_regions,
            max_portals,
            max_bodies,
            max_objects,
        })
    }
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) struct WorldActorPort {
    port_id: String,
    actor_body_id: String,
}

impl WorldActorPort {
    pub(crate) fn new(
        port_id: String,
        actor_body_id: String,
    ) -> Result<Self, WorldBodyVerificationError> {
        identifier(&port_id, "world actor port id")?;
        identifier(&actor_body_id, "world actor body id")?;
        Ok(Self {
            port_id,
            actor_body_id,
        })
    }
}

pub(crate) struct WorldAuthorityMount {
    epoch: WorldAuthorityMountEpoch,
    key: Zeroizing<Vec<u8>>,
    limits: WorldAuthorityLimits,
    actor_ports: Box<[WorldActorPort]>,
}

impl WorldAuthorityMount {
    pub(crate) fn new(
        epoch: WorldAuthorityMountEpoch,
        key: Vec<u8>,
        limits: WorldAuthorityLimits,
        actor_ports: Vec<WorldActorPort>,
    ) -> Result<Self, WorldBodyVerificationError> {
        if key.is_empty() || key.len() > MAX_WORLD_KEY_BYTES {
            return Err(WorldBodyVerificationError::InvalidMount(
                "world key length is outside the authority contract",
            ));
        }
        if actor_ports.len() < 2
            || u64::try_from(actor_ports.len())
                .ok()
                .is_none_or(|count| count > limits.max_bodies)
        {
            return Err(WorldBodyVerificationError::InvalidMount(
                "world actor-port count differs from the authority contract",
            ));
        }
        let mut prior_port: Option<&str> = None;
        let mut actor_ids = BTreeSet::new();
        for port in &actor_ports {
            if prior_port.is_some_and(|prior| prior >= port.port_id.as_str())
                || !actor_ids.insert(port.actor_body_id.as_str())
            {
                return Err(WorldBodyVerificationError::InvalidMount(
                    "world actor-port topology is not canonical",
                ));
            }
            prior_port = Some(port.port_id.as_str());
        }
        Ok(Self {
            epoch,
            key: Zeroizing::new(key),
            limits,
            actor_ports: actor_ports.into_boxed_slice(),
        })
    }

    fn ensure_within_admission(
        &self,
        budget: WorldBodyVerificationBudget,
    ) -> Result<(), WorldBodyVerificationError> {
        if self.limits.max_regions > budget.max_regions
            || self.limits.max_portals > budget.max_portals
            || self.limits.max_bodies > budget.max_bodies
            || self.limits.max_objects > budget.max_objects
        {
            return Err(WorldBodyVerificationError::InputBudgetExceeded(
                "world configured authority limits",
            ));
        }
        Ok(())
    }
}

pub(crate) struct BodyAuthorityMount {
    epoch: BodyAuthorityMountEpoch,
    key: Zeroizing<Vec<u8>>,
}

impl BodyAuthorityMount {
    pub(crate) fn new(
        epoch: BodyAuthorityMountEpoch,
        key: Vec<u8>,
    ) -> Result<Self, WorldBodyVerificationError> {
        if !(MIN_BODY_KEY_BYTES..=MAX_BODY_KEY_BYTES).contains(&key.len()) {
            return Err(WorldBodyVerificationError::InvalidMount(
                "body key length is outside the authority contract",
            ));
        }
        Ok(Self {
            epoch,
            key: Zeroizing::new(key),
        })
    }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) struct WorldBodyVerificationBudget {
    pub(crate) max_world_record_bytes: u64,
    pub(crate) max_body_manifest_record_bytes: u64,
    pub(crate) max_body_state_record_bytes: u64,
    pub(crate) max_json_depth: u64,
    pub(crate) max_json_tokens: u64,
    pub(crate) max_regions: u64,
    pub(crate) max_portals: u64,
    pub(crate) max_bodies: u64,
    pub(crate) max_objects: u64,
    pub(crate) max_body_quantities: u64,
    pub(crate) max_body_parameters: u64,
    pub(crate) max_body_neurochemical_references: u64,
    pub(crate) max_body_changes_per_transition: u64,
    pub(crate) max_body_conservation_exchanges_per_transition: u64,
    pub(crate) max_body_transitions: u64,
    pub(crate) max_body_cold_state_bytes: u64,
    pub(crate) max_fraction_bits: u64,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) enum WorldBodyVerificationError {
    InvalidMount(&'static str),
    InputBudgetExceeded(&'static str),
    JsonBudgetExceeded(&'static str),
    NoncanonicalJson(&'static str),
    WrongSchema(&'static str),
    WrongShape(&'static str),
    InvalidValue(&'static str),
    AuthenticationFailed(&'static str),
    ReceiptMismatch(&'static str),
    OrganismReceiptMismatch(&'static str),
}

impl fmt::Display for WorldBodyVerificationError {
    fn fmt(&self, output: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::InvalidMount(reason) => write!(output, "invalid world/body mount: {reason}"),
            Self::InputBudgetExceeded(name) => write!(output, "{name} input budget exceeded"),
            Self::JsonBudgetExceeded(name) => write!(output, "{name} JSON budget exceeded"),
            Self::NoncanonicalJson(name) => write!(output, "{name} is not exact canonical JSON"),
            Self::WrongSchema(name) => write!(output, "{name} schema differs"),
            Self::WrongShape(name) => write!(output, "{name} fields differ"),
            Self::InvalidValue(name) => write!(output, "{name} value differs"),
            Self::AuthenticationFailed(name) => write!(output, "{name} HMAC differs"),
            Self::ReceiptMismatch(name) => write!(output, "{name} receipt differs"),
            Self::OrganismReceiptMismatch(name) => {
                write!(output, "organism {name} receipt differs")
            }
        }
    }
}

impl std::error::Error for WorldBodyVerificationError {}

/// Unforgeable result of exact observation-v6 semantic and authority verification.
pub(crate) struct AuthenticatedWorldObservation {
    canonical_record: Box<[u8]>,
    receipt: [u8; 32],
    state_receipt: [u8; 32],
    revision: u64,
    mount_epoch: WorldAuthorityMountEpoch,
}

impl AuthenticatedWorldObservation {
    pub(crate) fn receipt(&self) -> [u8; 32] {
        self.receipt
    }

    pub(crate) fn state_receipt(&self) -> [u8; 32] {
        self.state_receipt
    }

    pub(crate) fn revision(&self) -> u64 {
        self.revision
    }

    pub(crate) fn mount_epoch(&self) -> WorldAuthorityMountEpoch {
        self.mount_epoch
    }

    pub(crate) fn canonical_record_bytes(&self) -> &[u8] {
        &self.canonical_record
    }
}

/// Unforgeable result of exact manifest-v1 and state-v1 semantic verification.
pub(crate) struct AuthenticatedBodyManifestState {
    manifest_record: Box<[u8]>,
    state_record: Box<[u8]>,
    manifest_receipt: [u8; 32],
    state_receipt: [u8; 32],
    sequence: u64,
    source_time: BigRational,
    mount_epoch: BodyAuthorityMountEpoch,
    prior_state_receipt: Option<[u8; 32]>,
    causal_source_receipt: Option<[u8; 32]>,
}

impl AuthenticatedBodyManifestState {
    pub(crate) fn manifest_receipt(&self) -> [u8; 32] {
        self.manifest_receipt
    }

    pub(crate) fn state_receipt(&self) -> [u8; 32] {
        self.state_receipt
    }

    pub(crate) fn sequence(&self) -> u64 {
        self.sequence
    }

    pub(crate) fn source_time(&self) -> &BigRational {
        &self.source_time
    }

    pub(crate) fn mount_epoch(&self) -> BodyAuthorityMountEpoch {
        self.mount_epoch
    }

    pub(crate) fn manifest_record_bytes(&self) -> &[u8] {
        &self.manifest_record
    }

    pub(crate) fn state_record_bytes(&self) -> &[u8] {
        &self.state_record
    }

    pub(crate) fn prior_state_receipt(&self) -> Option<[u8; 32]> {
        self.prior_state_receipt
    }

    pub(crate) fn causal_source_receipt(&self) -> Option<[u8; 32]> {
        self.causal_source_receipt
    }
}

/// Narrow proof that the two authenticated physical artifacts exactly bind to
/// the already-verified organism. It makes no shared-clock or successor claim.
pub(crate) struct WorldBodyVerifiedSeal {
    dsf: DsfDeliveryVerifiedSeal,
    world: AuthenticatedWorldObservation,
    body: AuthenticatedBodyManifestState,
}

impl WorldBodyVerifiedSeal {
    pub(crate) fn state(&self) -> &super::OrganismState {
        self.dsf.state()
    }

    pub(crate) fn organism_state_receipt(&self) -> [u8; 32] {
        self.dsf.organism_state_receipt()
    }

    pub(crate) fn world(&self) -> &AuthenticatedWorldObservation {
        &self.world
    }

    pub(crate) fn body(&self) -> &AuthenticatedBodyManifestState {
        &self.body
    }

    pub(crate) fn world_receipt(&self) -> [u8; 32] {
        self.world.receipt()
    }

    pub(crate) fn world_state_receipt(&self) -> [u8; 32] {
        self.world.state_receipt()
    }

    pub(crate) fn world_revision(&self) -> u64 {
        self.world.revision()
    }

    pub(crate) fn world_mount_epoch(&self) -> WorldAuthorityMountEpoch {
        self.world.mount_epoch()
    }

    pub(crate) fn body_manifest_receipt(&self) -> [u8; 32] {
        self.body.manifest_receipt()
    }

    pub(crate) fn body_state_receipt(&self) -> [u8; 32] {
        self.body.state_receipt()
    }

    pub(crate) fn body_sequence(&self) -> u64 {
        self.body.sequence()
    }

    pub(crate) fn body_source_time(&self) -> (&BigInt, &BigInt) {
        (
            self.body.source_time().numer(),
            self.body.source_time().denom(),
        )
    }

    pub(crate) fn body_mount_epoch(&self) -> BodyAuthorityMountEpoch {
        self.body.mount_epoch()
    }

    pub(crate) fn into_parts(
        self,
    ) -> (
        DsfDeliveryVerifiedSeal,
        AuthenticatedWorldObservation,
        AuthenticatedBodyManifestState,
    ) {
        (self.dsf, self.world, self.body)
    }
}

#[derive(Clone)]
struct QuantityLaw {
    mechanism: String,
    evolution_kind: String,
    lower: Option<BigRational>,
    upper: Option<BigRational>,
    initial: Option<BigRational>,
    cyclic_modulus: Option<BigRational>,
}

struct VerifiedBodyManifest {
    receipt: [u8; 32],
    quantities: Vec<(String, QuantityLaw)>,
    unavailable: Vec<(String, String)>,
    references: Vec<(String, String)>,
}

struct VerifiedBodyState {
    receipt: [u8; 32],
    sequence: u64,
    source_time: BigRational,
    prior_state_receipt: Option<[u8; 32]>,
    causal_source_receipt: Option<[u8; 32]>,
}

pub(crate) fn authenticate_world_observation(
    mount: &WorldAuthorityMount,
    record_bytes: &[u8],
    budget: WorldBodyVerificationBudget,
) -> Result<AuthenticatedWorldObservation, WorldBodyVerificationError> {
    validate_budget(budget)?;
    let verified = world::verify_world_record(mount, record_bytes, budget)?;
    Ok(AuthenticatedWorldObservation {
        canonical_record: record_bytes.to_vec().into_boxed_slice(),
        receipt: verified.receipt,
        state_receipt: verified.state_receipt,
        revision: verified.revision,
        mount_epoch: mount.epoch,
    })
}

pub(crate) fn authenticate_body_manifest_state(
    mount: &BodyAuthorityMount,
    manifest_record_bytes: &[u8],
    state_record_bytes: &[u8],
    budget: WorldBodyVerificationBudget,
) -> Result<AuthenticatedBodyManifestState, WorldBodyVerificationError> {
    validate_budget(budget)?;
    let manifest = verify_body_manifest(mount, manifest_record_bytes, budget)?;
    let state = verify_body_state(mount, state_record_bytes, &manifest, budget)?;
    Ok(AuthenticatedBodyManifestState {
        manifest_record: manifest_record_bytes.to_vec().into_boxed_slice(),
        state_record: state_record_bytes.to_vec().into_boxed_slice(),
        manifest_receipt: manifest.receipt,
        state_receipt: state.receipt,
        sequence: state.sequence,
        source_time: state.source_time,
        mount_epoch: mount.epoch,
        prior_state_receipt: state.prior_state_receipt,
        causal_source_receipt: state.causal_source_receipt,
    })
}

pub(crate) fn bind_world_body(
    dsf: DsfDeliveryVerifiedSeal,
    world: AuthenticatedWorldObservation,
    body: AuthenticatedBodyManifestState,
) -> Result<WorldBodyVerifiedSeal, WorldBodyVerificationError> {
    if world.receipt() != dsf.state().authenticated_world_revision {
        return Err(WorldBodyVerificationError::OrganismReceiptMismatch(
            "world revision",
        ));
    }
    if body.state_receipt() != dsf.state().body_state_receipt {
        return Err(WorldBodyVerificationError::OrganismReceiptMismatch(
            "body state",
        ));
    }
    Ok(WorldBodyVerifiedSeal { dsf, world, body })
}

fn validate_budget(budget: WorldBodyVerificationBudget) -> Result<(), WorldBodyVerificationError> {
    let values = [
        budget.max_world_record_bytes,
        budget.max_body_manifest_record_bytes,
        budget.max_body_state_record_bytes,
        budget.max_json_depth,
        budget.max_json_tokens,
        budget.max_regions,
        budget.max_portals,
        budget.max_bodies,
        budget.max_objects,
        budget.max_body_quantities,
        budget.max_body_parameters,
        budget.max_body_neurochemical_references,
        budget.max_body_changes_per_transition,
        budget.max_body_conservation_exchanges_per_transition,
        budget.max_body_transitions,
        budget.max_body_cold_state_bytes,
        budget.max_fraction_bits,
    ];
    if values.contains(&0) {
        return Err(WorldBodyVerificationError::InvalidMount(
            "verification budget contains zero",
        ));
    }
    Ok(())
}

fn verify_body_manifest(
    mount: &BodyAuthorityMount,
    bytes: &[u8],
    budget: WorldBodyVerificationBudget,
) -> Result<VerifiedBodyManifest, WorldBodyVerificationError> {
    let value = parse_canonical(
        bytes,
        budget.max_body_manifest_record_bytes,
        budget,
        "body manifest",
    )?;
    let record = object(&value, "body manifest")?;
    exact_keys(record, BODY_MANIFEST_RECORD_KEYS, "body manifest")?;
    if string(record, "schema", "body manifest")? != BODY_MANIFEST_SCHEMA {
        return Err(WorldBodyVerificationError::WrongSchema("body manifest"));
    }
    identifier(
        string(record, "manifest_id", "body manifest id")?,
        "body manifest id",
    )?;
    identifier(
        string(record, "structural_time_unit", "body structural time unit")?,
        "body structural time unit",
    )?;

    let capacity = object(
        record
            .get("capacity")
            .ok_or(WorldBodyVerificationError::WrongShape("body capacity"))?,
        "body capacity",
    )?;
    exact_keys(capacity, CAPACITY_KEYS, "body capacity")?;
    let max_quantities = positive(capacity, "max_quantities", "body quantity capacity")?;
    let max_parameters = positive(capacity, "max_parameters", "body parameter capacity")?;
    let max_references = positive(
        capacity,
        "max_neurochemical_references",
        "body reference capacity",
    )?;
    let max_changes = positive(
        capacity,
        "max_changes_per_transition",
        "body change capacity",
    )?;
    let max_exchanges = positive(
        capacity,
        "max_conservation_exchanges_per_transition",
        "body exchange capacity",
    )?;
    let max_transitions = positive(capacity, "max_transitions", "body transition capacity")?;
    let max_state_bytes = positive(capacity, "max_state_bytes", "body cold-state capacity")?;
    if max_quantities > budget.max_body_quantities
        || max_parameters > budget.max_body_parameters
        || max_references > budget.max_body_neurochemical_references
        || max_changes > budget.max_body_changes_per_transition
        || max_exchanges > budget.max_body_conservation_exchanges_per_transition
        || max_transitions > budget.max_body_transitions
        || max_state_bytes > budget.max_body_cold_state_bytes
    {
        return Err(WorldBodyVerificationError::InputBudgetExceeded(
            "body declared capacity",
        ));
    }

    let quantities_raw = array(record, "quantities", "body quantities")?;
    let parameters_raw = array(record, "parameters", "body parameters")?;
    let references_raw = array(
        record,
        "neurochemical_references",
        "body neurochemical references",
    )?;
    count(quantities_raw.len(), max_quantities, "body quantities")?;
    count(parameters_raw.len(), max_parameters, "body parameters")?;
    count(references_raw.len(), max_references, "body references")?;

    let mut quantities = Vec::with_capacity(quantities_raw.len());
    let mut quantity_ids = BTreeSet::new();
    let mut roles_by_mechanism: BTreeMap<String, BTreeSet<String>> = BTreeMap::new();
    let mut prior_quantity: Option<&str> = None;
    for raw in quantities_raw {
        let item = object(raw, "body quantity")?;
        exact_keys(item, QUANTITY_KEYS, "body quantity")?;
        let id = string(item, "quantity_id", "body quantity id")?;
        identifier(id, "body quantity id")?;
        if prior_quantity.is_some_and(|prior| prior >= id) || !quantity_ids.insert(id.to_owned()) {
            return Err(WorldBodyVerificationError::InvalidValue(
                "body quantity order",
            ));
        }
        prior_quantity = Some(id);
        let mechanism = known_mechanism(string(item, "mechanism", "body quantity mechanism")?)?;
        let role = string(item, "role", "body quantity role")?;
        identifier(role, "body quantity role")?;
        identifier(
            string(item, "unit", "body quantity unit")?,
            "body quantity unit",
        )?;
        if !roles_by_mechanism
            .entry(mechanism.to_owned())
            .or_default()
            .insert(role.to_owned())
        {
            return Err(WorldBodyVerificationError::InvalidValue(
                "body quantity role topology",
            ));
        }
        if let Some(group) =
            nullable_string(item, "conservation_group_id", "body conservation group")?
        {
            identifier(group, "body conservation group")?;
        }
        let kind = string(item, "evolution_kind", "body quantity evolution")?;
        let lower = fraction_or_null(item.get("lower_bound"), budget, "body lower bound")?;
        let upper = fraction_or_null(item.get("upper_bound"), budget, "body upper bound")?;
        let initial = fraction_or_null(item.get("initial_value"), budget, "body initial value")?;
        let modulus = fraction_or_null(item.get("cyclic_modulus"), budget, "body cyclic modulus")?;
        match kind {
            "unavailable" => {
                if lower.is_some() || upper.is_some() || initial.is_some() || modulus.is_some() {
                    return Err(WorldBodyVerificationError::InvalidValue(
                        "unavailable body quantity",
                    ));
                }
            }
            "linear" => {
                validate_interval(&lower, &upper, &initial, "linear body quantity")?;
                if modulus.is_some() {
                    return Err(WorldBodyVerificationError::InvalidValue(
                        "linear body cyclic modulus",
                    ));
                }
            }
            "cyclic" => {
                validate_interval(&lower, &upper, &initial, "cyclic body quantity")?;
                let modulus_value =
                    modulus
                        .as_ref()
                        .ok_or(WorldBodyVerificationError::InvalidValue(
                            "cyclic body modulus",
                        ))?;
                if lower.as_ref().is_none_or(|value| !value.is_zero())
                    || upper.as_ref() != Some(modulus_value)
                    || modulus_value <= &BigRational::zero()
                    || initial.as_ref() == upper.as_ref()
                {
                    return Err(WorldBodyVerificationError::InvalidValue(
                        "cyclic body interval",
                    ));
                }
            }
            _ => {
                return Err(WorldBodyVerificationError::InvalidValue(
                    "body quantity evolution",
                ))
            }
        }
        quantities.push((
            id.to_owned(),
            QuantityLaw {
                mechanism: mechanism.to_owned(),
                evolution_kind: kind.to_owned(),
                lower,
                upper,
                initial,
                cyclic_modulus: modulus,
            },
        ));
    }

    let mut parameter_ids = BTreeMap::new();
    let mut prior_parameter: Option<&str> = None;
    for raw in parameters_raw {
        let item = object(raw, "body parameter")?;
        exact_keys(item, PARAMETER_KEYS, "body parameter")?;
        let id = string(item, "parameter_id", "body parameter id")?;
        identifier(id, "body parameter id")?;
        if prior_parameter.is_some_and(|prior| prior >= id) {
            return Err(WorldBodyVerificationError::InvalidValue(
                "body parameter order",
            ));
        }
        prior_parameter = Some(id);
        let mechanism = known_mechanism(string(item, "mechanism", "body parameter mechanism")?)?;
        identifier(
            string(item, "unit", "body parameter unit")?,
            "body parameter unit",
        )?;
        fraction_text(
            string(item, "value", "body parameter value")?,
            budget,
            "body parameter value",
        )?;
        digest_field(
            item,
            "derivation_receipt_sha256",
            "body parameter derivation",
        )?;
        parameter_ids.insert(id.to_owned(), mechanism.to_owned());
    }

    let mut references = Vec::with_capacity(references_raw.len());
    let mut prior_reference: Option<&str> = None;
    for raw in references_raw {
        let item = object(raw, "body reference")?;
        exact_keys(item, REFERENCE_KEYS, "body reference")?;
        let id = string(item, "reference_id", "body reference id")?;
        identifier(id, "body reference id")?;
        if prior_reference.is_some_and(|prior| prior >= id) {
            return Err(WorldBodyVerificationError::InvalidValue(
                "body reference order",
            ));
        }
        prior_reference = Some(id);
        for key in ["species_id", "node_id", "quantity_unit"] {
            identifier(
                string(item, key, "body reference identifier")?,
                "body reference identifier",
            )?;
        }
        digest_field(item, "manifest_receipt_sha256", "body reference manifest")?;
        let compartment = string(
            item,
            "compartment_receipt_sha256",
            "body compartment reference",
        )?;
        parse_digest(compartment, "body compartment reference")?;
        references.push((id.to_owned(), compartment.to_owned()));
    }

    let mechanisms = array(record, "mechanisms", "body mechanisms")?;
    if mechanisms.len() != MECHANISMS.len() {
        return Err(WorldBodyVerificationError::InvalidValue(
            "body mechanism coverage",
        ));
    }
    let mut unavailable = Vec::new();
    for (raw, expected) in mechanisms.iter().zip(MECHANISMS) {
        let item = object(raw, "body mechanism")?;
        exact_keys(item, MECHANISM_KEYS, "body mechanism")?;
        if string(item, "mechanism", "body mechanism")? != *expected {
            return Err(WorldBodyVerificationError::InvalidValue(
                "body mechanism order",
            ));
        }
        let mounted_ids = string_array(item, "quantity_ids", "body mounted quantities")?;
        strict_identifiers(&mounted_ids, "body mounted quantities")?;
        let actual_ids: Vec<&str> = quantities
            .iter()
            .filter(|(_, law)| law.mechanism == *expected)
            .map(|(id, _)| id.as_str())
            .collect();
        if mounted_ids != actual_ids {
            return Err(WorldBodyVerificationError::InvalidValue(
                "body mechanism quantity membership",
            ));
        }
        let required_parameters =
            string_array(item, "required_parameter_ids", "body required parameters")?;
        strict_identifiers(&required_parameters, "body required parameters")?;
        for id in &required_parameters {
            if parameter_ids
                .get(*id)
                .is_some_and(|owner| owner != *expected)
            {
                return Err(WorldBodyVerificationError::InvalidValue(
                    "body mechanism parameter topology",
                ));
            }
        }
        let availability = string(item, "availability", "body mechanism availability")?;
        match availability {
            "available" => {
                if item.get("unavailable_reason") != Some(&Value::Null)
                    || required_parameters
                        .iter()
                        .any(|id| !parameter_ids.contains_key(*id))
                    || quantities.iter().any(|(_, law)| {
                        law.mechanism == *expected && law.evolution_kind == "unavailable"
                    })
                {
                    return Err(WorldBodyVerificationError::InvalidValue(
                        "available body mechanism",
                    ));
                }
                if *expected == "neurochemical" && references.is_empty() {
                    return Err(WorldBodyVerificationError::InvalidValue(
                        "available neurochemical mechanism",
                    ));
                }
            }
            "unavailable" => {
                let reason = string(item, "unavailable_reason", "body unavailable reason")?;
                bounded_text(reason, MAX_REASON_BYTES, "body unavailable reason")?;
                if quantities.iter().any(|(_, law)| {
                    law.mechanism == *expected && law.evolution_kind != "unavailable"
                }) {
                    return Err(WorldBodyVerificationError::InvalidValue(
                        "unavailable body mechanism",
                    ));
                }
                unavailable.push((expected.to_string(), reason.to_owned()));
            }
            _ => {
                return Err(WorldBodyVerificationError::InvalidValue(
                    "body mechanism availability",
                ))
            }
        }
        validate_required_roles(expected, roles_by_mechanism.get(*expected))?;
    }

    let provided_hmac = digest_field(record, "authority_hmac_sha256", "body manifest")?;
    let mut payload = record.clone();
    payload.remove("authority_hmac_sha256");
    payload.remove("authority_receipt_sha256");
    let payload_value = Value::Object(payload);
    let payload_bytes = canonical_value(&payload_value)?;
    let derived_key = derive_key(BODY_MANIFEST_DOMAIN, mount.key.as_slice());
    verify_hmac(
        &derived_key,
        BODY_MANIFEST_DOMAIN,
        &payload_bytes,
        &provided_hmac,
        "body manifest",
    )?;
    let receipt = receipt_digest(&provided_hmac, &payload_value)?;
    if receipt != digest_field(record, "authority_receipt_sha256", "body manifest")? {
        return Err(WorldBodyVerificationError::ReceiptMismatch("body manifest"));
    }
    Ok(VerifiedBodyManifest {
        receipt,
        quantities,
        unavailable,
        references,
    })
}

fn verify_body_state(
    mount: &BodyAuthorityMount,
    bytes: &[u8],
    manifest: &VerifiedBodyManifest,
    budget: WorldBodyVerificationBudget,
) -> Result<VerifiedBodyState, WorldBodyVerificationError> {
    let value = parse_canonical(
        bytes,
        budget.max_body_state_record_bytes,
        budget,
        "body state",
    )?;
    let record = object(&value, "body state")?;
    exact_keys(record, BODY_STATE_RECORD_KEYS, "body state")?;
    if string(record, "schema", "body state")? != BODY_STATE_SCHEMA {
        return Err(WorldBodyVerificationError::WrongSchema("body state"));
    }
    if digest_field(record, "manifest_receipt_sha256", "body state manifest")? != manifest.receipt {
        return Err(WorldBodyVerificationError::ReceiptMismatch(
            "body state manifest",
        ));
    }
    let sequence = unsigned(record, "sequence", "body state sequence")?;
    let source_time = fraction_text(
        string(record, "source_time", "body state source time")?,
        budget,
        "body state source time",
    )?;
    let prior_state_receipt =
        optional_digest(record.get("prior_state_receipt_sha256"), "body prior state")?;
    let causal_source_receipt = optional_digest(
        record.get("causal_source_receipt_sha256"),
        "body causal source",
    )?;

    let values = array(record, "quantity_values", "body quantity values")?;
    if values.len() != manifest.quantities.len() {
        return Err(WorldBodyVerificationError::InvalidValue(
            "body quantity value topology",
        ));
    }
    for (raw, (expected_id, law)) in values.iter().zip(&manifest.quantities) {
        let pair = raw
            .as_array()
            .ok_or(WorldBodyVerificationError::WrongShape(
                "body quantity value",
            ))?;
        if pair.len() != 2 || pair[0].as_str() != Some(expected_id) {
            return Err(WorldBodyVerificationError::InvalidValue(
                "body quantity value topology",
            ));
        }
        if law.evolution_kind == "unavailable" {
            if pair[1] != Value::Null {
                return Err(WorldBodyVerificationError::InvalidValue(
                    "unavailable body state quantity",
                ));
            }
        } else {
            let text = pair[1]
                .as_str()
                .ok_or(WorldBodyVerificationError::InvalidValue(
                    "body quantity value",
                ))?;
            let exact = fraction_text(text, budget, "body quantity value")?;
            let lower = law.lower.as_ref().expect("verified lower bound");
            let upper = law.upper.as_ref().expect("verified upper bound");
            let inside = if law.evolution_kind == "cyclic" {
                lower <= &exact && &exact < upper
            } else {
                lower <= &exact && &exact <= upper
            };
            if !inside {
                return Err(WorldBodyVerificationError::InvalidValue(
                    "body quantity bound",
                ));
            }
        }
    }

    let unavailable = pair_array(
        array(
            record,
            "unavailable_mechanisms",
            "body unavailable mechanisms",
        )?,
        "body unavailable mechanisms",
    )?;
    if unavailable != manifest.unavailable {
        return Err(WorldBodyVerificationError::InvalidValue(
            "body unavailable mechanism projection",
        ));
    }
    let references = pair_array(
        array(
            record,
            "neurochemical_reference_receipts",
            "body reference receipts",
        )?,
        "body reference receipts",
    )?;
    if references != manifest.references {
        return Err(WorldBodyVerificationError::InvalidValue(
            "body reference projection",
        ));
    }

    let provided_hmac = digest_field(record, "authority_hmac_sha256", "body state")?;
    let mut payload = record.clone();
    payload.remove("authority_hmac_sha256");
    payload.remove("authority_receipt_sha256");
    let payload_value = Value::Object(payload);
    let payload_bytes = canonical_value(&payload_value)?;
    let derived_key = derive_key(BODY_STATE_DOMAIN, mount.key.as_slice());
    verify_hmac(
        &derived_key,
        BODY_STATE_DOMAIN,
        &payload_bytes,
        &provided_hmac,
        "body state",
    )?;
    let receipt = receipt_digest(&provided_hmac, &payload_value)?;
    if receipt != digest_field(record, "authority_receipt_sha256", "body state")? {
        return Err(WorldBodyVerificationError::ReceiptMismatch("body state"));
    }
    Ok(VerifiedBodyState {
        receipt,
        sequence,
        source_time,
        prior_state_receipt,
        causal_source_receipt,
    })
}

fn parse_canonical(
    bytes: &[u8],
    max_bytes: u64,
    budget: WorldBodyVerificationBudget,
    name: &'static str,
) -> Result<Value, WorldBodyVerificationError> {
    let len = u64::try_from(bytes.len())
        .map_err(|_| WorldBodyVerificationError::InputBudgetExceeded(name))?;
    if bytes.is_empty() || len > max_bytes {
        return Err(WorldBodyVerificationError::InputBudgetExceeded(name));
    }
    json_preflight(bytes, budget.max_json_depth, budget.max_json_tokens, name)?;
    std::str::from_utf8(bytes).map_err(|_| WorldBodyVerificationError::NoncanonicalJson(name))?;
    let value: Value = serde_json::from_slice(bytes)
        .map_err(|_| WorldBodyVerificationError::NoncanonicalJson(name))?;
    reject_noninteger_numbers(&value, name)?;
    if canonical_value(&value)?.as_slice() != bytes {
        return Err(WorldBodyVerificationError::NoncanonicalJson(name));
    }
    Ok(value)
}

fn json_preflight(
    bytes: &[u8],
    max_depth: u64,
    max_tokens: u64,
    name: &'static str,
) -> Result<(), WorldBodyVerificationError> {
    let mut depth = 0_u64;
    let mut tokens = 0_u64;
    let mut in_string = false;
    let mut escaped = false;
    for byte in bytes {
        if in_string {
            if escaped {
                escaped = false;
            } else if *byte == b'\\' {
                escaped = true;
            } else if *byte == b'"' {
                in_string = false;
                tokens = tokens.saturating_add(1);
            }
            continue;
        }
        match *byte {
            b'"' => in_string = true,
            b'{' | b'[' => {
                depth = depth.saturating_add(1);
                tokens = tokens.saturating_add(1);
                if depth > max_depth {
                    return Err(WorldBodyVerificationError::JsonBudgetExceeded(name));
                }
            }
            b'}' | b']' => depth = depth.saturating_sub(1),
            b',' | b':' => tokens = tokens.saturating_add(1),
            b' ' | b'\n' | b'\r' | b'\t' => {
                return Err(WorldBodyVerificationError::NoncanonicalJson(name))
            }
            _ => {}
        }
        if tokens > max_tokens {
            return Err(WorldBodyVerificationError::JsonBudgetExceeded(name));
        }
    }
    if in_string || depth != 0 {
        return Err(WorldBodyVerificationError::NoncanonicalJson(name));
    }
    Ok(())
}

fn reject_noninteger_numbers(
    value: &Value,
    name: &'static str,
) -> Result<(), WorldBodyVerificationError> {
    match value {
        Value::Number(number) if number.as_i64().is_none() && number.as_u64().is_none() => {
            Err(WorldBodyVerificationError::InvalidValue(name))
        }
        Value::Array(values) => {
            for value in values {
                reject_noninteger_numbers(value, name)?;
            }
            Ok(())
        }
        Value::Object(values) => {
            for value in values.values() {
                reject_noninteger_numbers(value, name)?;
            }
            Ok(())
        }
        _ => Ok(()),
    }
}

fn canonical_value(value: &Value) -> Result<Vec<u8>, WorldBodyVerificationError> {
    serde_json::to_vec(value)
        .map_err(|_| WorldBodyVerificationError::NoncanonicalJson("canonical value"))
}

fn exact_keys(
    value: &Map<String, Value>,
    expected: &[&str],
    name: &'static str,
) -> Result<(), WorldBodyVerificationError> {
    if value.len() != expected.len() || expected.iter().any(|key| !value.contains_key(*key)) {
        return Err(WorldBodyVerificationError::WrongShape(name));
    }
    Ok(())
}

fn object<'a>(
    value: &'a Value,
    name: &'static str,
) -> Result<&'a Map<String, Value>, WorldBodyVerificationError> {
    value
        .as_object()
        .ok_or(WorldBodyVerificationError::WrongShape(name))
}

fn array<'a>(
    value: &'a Map<String, Value>,
    key: &str,
    name: &'static str,
) -> Result<&'a Vec<Value>, WorldBodyVerificationError> {
    value
        .get(key)
        .and_then(Value::as_array)
        .ok_or(WorldBodyVerificationError::WrongShape(name))
}

fn string<'a>(
    value: &'a Map<String, Value>,
    key: &str,
    name: &'static str,
) -> Result<&'a str, WorldBodyVerificationError> {
    value
        .get(key)
        .and_then(Value::as_str)
        .ok_or(WorldBodyVerificationError::InvalidValue(name))
}

fn nullable_string<'a>(
    value: &'a Map<String, Value>,
    key: &str,
    name: &'static str,
) -> Result<Option<&'a str>, WorldBodyVerificationError> {
    match value.get(key) {
        Some(Value::Null) => Ok(None),
        Some(Value::String(text)) => Ok(Some(text)),
        _ => Err(WorldBodyVerificationError::InvalidValue(name)),
    }
}

fn unsigned(
    value: &Map<String, Value>,
    key: &str,
    name: &'static str,
) -> Result<u64, WorldBodyVerificationError> {
    value
        .get(key)
        .and_then(Value::as_u64)
        .ok_or(WorldBodyVerificationError::InvalidValue(name))
}

fn positive(
    value: &Map<String, Value>,
    key: &str,
    name: &'static str,
) -> Result<u64, WorldBodyVerificationError> {
    let result = unsigned(value, key, name)?;
    if result == 0 {
        return Err(WorldBodyVerificationError::InvalidValue(name));
    }
    Ok(result)
}

fn identifier(value: &str, name: &'static str) -> Result<(), WorldBodyVerificationError> {
    bounded_text(value, MAX_IDENTIFIER_BYTES, name)
}

fn bounded_text(
    value: &str,
    maximum: usize,
    name: &'static str,
) -> Result<(), WorldBodyVerificationError> {
    if value.is_empty()
        || value.len() > maximum
        || value.chars().next().is_some_and(python_strip_whitespace)
        || value
            .chars()
            .next_back()
            .is_some_and(python_strip_whitespace)
    {
        return Err(WorldBodyVerificationError::InvalidValue(name));
    }
    Ok(())
}

fn python_strip_whitespace(value: char) -> bool {
    matches!(
        value as u32,
        0x0009..=0x000d
            | 0x001c..=0x0020
            | 0x0085
            | 0x00a0
            | 0x1680
            | 0x2000..=0x200a
            | 0x2028
            | 0x2029
            | 0x202f
            | 0x205f
            | 0x3000
    )
}

fn count(
    actual: usize,
    maximum: u64,
    name: &'static str,
) -> Result<(), WorldBodyVerificationError> {
    let actual =
        u64::try_from(actual).map_err(|_| WorldBodyVerificationError::InputBudgetExceeded(name))?;
    if actual > maximum {
        return Err(WorldBodyVerificationError::InputBudgetExceeded(name));
    }
    Ok(())
}

fn validate_named_array<'a>(
    values: &'a [Value],
    key: &str,
    minimum: u64,
    maximum: u64,
    name: &'static str,
) -> Result<BTreeSet<&'a str>, WorldBodyVerificationError> {
    let len = u64::try_from(values.len())
        .map_err(|_| WorldBodyVerificationError::InputBudgetExceeded(name))?;
    if len < minimum || len > maximum {
        return Err(WorldBodyVerificationError::InputBudgetExceeded(name));
    }
    let mut ids = BTreeSet::new();
    let mut prior = None;
    for value in values {
        let record = object(value, name)?;
        let id = string(record, key, name)?;
        identifier(id, name)?;
        if prior.is_some_and(|previous| previous >= id) || !ids.insert(id) {
            return Err(WorldBodyVerificationError::InvalidValue(name));
        }
        prior = Some(id);
    }
    Ok(ids)
}

fn string_array<'a>(
    value: &'a Map<String, Value>,
    key: &str,
    name: &'static str,
) -> Result<Vec<&'a str>, WorldBodyVerificationError> {
    array(value, key, name)?
        .iter()
        .map(|value| {
            value
                .as_str()
                .ok_or(WorldBodyVerificationError::InvalidValue(name))
        })
        .collect()
}

fn strict_identifiers(
    values: &[&str],
    name: &'static str,
) -> Result<(), WorldBodyVerificationError> {
    let mut prior = None;
    for value in values {
        identifier(value, name)?;
        if prior.is_some_and(|previous| previous >= *value) {
            return Err(WorldBodyVerificationError::InvalidValue(name));
        }
        prior = Some(*value);
    }
    Ok(())
}

fn known_mechanism(value: &str) -> Result<&str, WorldBodyVerificationError> {
    if MECHANISMS.contains(&value) {
        Ok(value)
    } else {
        Err(WorldBodyVerificationError::InvalidValue("body mechanism"))
    }
}

fn validate_required_roles(
    mechanism: &str,
    roles: Option<&BTreeSet<String>>,
) -> Result<(), WorldBodyVerificationError> {
    let required: &[&str] = match mechanism {
        "proprioception" => &["position_x", "position_y", "position_z", "supported_load"],
        "vestibular" => &[
            "linear_acceleration_x",
            "linear_acceleration_y",
            "linear_acceleration_z",
            "orientation_roll",
            "orientation_pitch",
            "orientation_yaw",
        ],
        "thermal" => &["core_temperature", "compartment_temperature"],
        "nociception" => &["tissue_integrity", "nociceptive_load"],
        "energy_water" => &["energy_inventory", "water_inventory"],
        "respiration" => &[
            "respiratory_volume",
            "respiratory_pressure",
            "oxygen_inventory",
            "carbon_dioxide_inventory",
        ],
        "circulation" => &["pulse_phase", "perfusion_rate"],
        "visceral" => &["visceral_load"],
        "fatigue_recovery" => &["fatigue_load", "recovery_reserve"],
        "circadian" => &["circadian_phase"],
        "neurochemical" => &[],
        _ => return Err(WorldBodyVerificationError::InvalidValue("body mechanism")),
    };
    let empty = BTreeSet::new();
    let actual = roles.unwrap_or(&empty);
    if required.iter().any(|role| !actual.contains(*role)) {
        return Err(WorldBodyVerificationError::InvalidValue(
            "body required quantity roles",
        ));
    }
    Ok(())
}

fn validate_interval(
    lower: &Option<BigRational>,
    upper: &Option<BigRational>,
    initial: &Option<BigRational>,
    name: &'static str,
) -> Result<(), WorldBodyVerificationError> {
    let (Some(lower), Some(upper), Some(initial)) = (lower, upper, initial) else {
        return Err(WorldBodyVerificationError::InvalidValue(name));
    };
    if lower >= upper || initial < lower || initial > upper {
        return Err(WorldBodyVerificationError::InvalidValue(name));
    }
    Ok(())
}

fn fraction_or_null(
    value: Option<&Value>,
    budget: WorldBodyVerificationBudget,
    name: &'static str,
) -> Result<Option<BigRational>, WorldBodyVerificationError> {
    match value {
        Some(Value::Null) => Ok(None),
        Some(Value::String(text)) => Ok(Some(fraction_text(text, budget, name)?)),
        _ => Err(WorldBodyVerificationError::InvalidValue(name)),
    }
}

fn fraction_text(
    value: &str,
    budget: WorldBodyVerificationBudget,
    name: &'static str,
) -> Result<BigRational, WorldBodyVerificationError> {
    let (numerator, denominator) = value
        .split_once('/')
        .ok_or(WorldBodyVerificationError::InvalidValue(name))?;
    if denominator.contains('/') || numerator.is_empty() || denominator.is_empty() {
        return Err(WorldBodyVerificationError::InvalidValue(name));
    }
    let numerator = BigInt::parse_bytes(numerator.as_bytes(), 10)
        .ok_or(WorldBodyVerificationError::InvalidValue(name))?;
    let denominator = BigInt::parse_bytes(denominator.as_bytes(), 10)
        .ok_or(WorldBodyVerificationError::InvalidValue(name))?;
    let maximum_bits = budget.max_fraction_bits.min(BODY_MAX_FRACTION_BITS);
    if denominator <= BigInt::zero()
        || numerator.bits() > maximum_bits
        || denominator.bits() > maximum_bits
    {
        return Err(WorldBodyVerificationError::InvalidValue(name));
    }
    let exact = BigRational::new(numerator, denominator);
    let canonical = format!("{}/{}", exact.numer(), exact.denom());
    if canonical != value {
        return Err(WorldBodyVerificationError::InvalidValue(name));
    }
    Ok(exact)
}

fn pair_array(
    values: &[Value],
    name: &'static str,
) -> Result<Vec<(String, String)>, WorldBodyVerificationError> {
    values
        .iter()
        .map(|value| {
            let pair = value
                .as_array()
                .ok_or(WorldBodyVerificationError::WrongShape(name))?;
            if pair.len() != 2 {
                return Err(WorldBodyVerificationError::WrongShape(name));
            }
            let left = pair[0]
                .as_str()
                .ok_or(WorldBodyVerificationError::InvalidValue(name))?;
            let right = pair[1]
                .as_str()
                .ok_or(WorldBodyVerificationError::InvalidValue(name))?;
            Ok((left.to_owned(), right.to_owned()))
        })
        .collect()
}

fn parse_digest(value: &str, name: &'static str) -> Result<[u8; 32], WorldBodyVerificationError> {
    if value.len() != 64
        || value
            .bytes()
            .any(|byte| !matches!(byte, b'0'..=b'9' | b'a'..=b'f'))
    {
        return Err(WorldBodyVerificationError::InvalidValue(name));
    }
    let mut output = [0_u8; 32];
    for (index, slot) in output.iter_mut().enumerate() {
        let high = hex_nibble(value.as_bytes()[index * 2]);
        let low = hex_nibble(value.as_bytes()[index * 2 + 1]);
        *slot = (high << 4) | low;
    }
    Ok(output)
}

fn hex_nibble(value: u8) -> u8 {
    match value {
        b'0'..=b'9' => value - b'0',
        b'a'..=b'f' => value - b'a' + 10,
        _ => unreachable!("validated lowercase hexadecimal"),
    }
}

fn digest_field(
    value: &Map<String, Value>,
    key: &str,
    name: &'static str,
) -> Result<[u8; 32], WorldBodyVerificationError> {
    parse_digest(string(value, key, name)?, name)
}

fn optional_digest(
    value: Option<&Value>,
    name: &'static str,
) -> Result<Option<[u8; 32]>, WorldBodyVerificationError> {
    match value {
        Some(Value::Null) => Ok(None),
        Some(Value::String(text)) => parse_digest(text, name).map(Some),
        _ => Err(WorldBodyVerificationError::InvalidValue(name)),
    }
}

fn derive_key(domain: &[u8], raw: &[u8]) -> [u8; 32] {
    let mut digest = Sha256::new();
    digest.update(domain);
    digest.update(raw);
    digest.finalize().into()
}

fn verify_hmac(
    key: &[u8],
    domain: &[u8],
    payload: &[u8],
    provided: &[u8; 32],
    name: &'static str,
) -> Result<(), WorldBodyVerificationError> {
    let mut mac = HmacSha256::new_from_slice(key)
        .map_err(|_| WorldBodyVerificationError::InvalidMount("HMAC key rejected"))?;
    mac.update(domain);
    mac.update(payload);
    mac.verify_slice(provided)
        .map_err(|_| WorldBodyVerificationError::AuthenticationFailed(name))
}

fn receipt_digest(
    hmac_digest: &[u8; 32],
    payload: &Value,
) -> Result<[u8; 32], WorldBodyVerificationError> {
    let mut wrapper = Map::new();
    wrapper.insert(
        "authority_hmac_sha256".to_owned(),
        Value::String(hex_digest(hmac_digest)),
    );
    wrapper.insert("payload".to_owned(), payload.clone());
    Ok(Sha256::digest(canonical_value(&Value::Object(wrapper))?).into())
}

fn hex_digest(value: &[u8; 32]) -> String {
    const HEX: &[u8; 16] = b"0123456789abcdef";
    let mut output = String::with_capacity(64);
    for byte in value {
        output.push(HEX[(byte >> 4) as usize] as char);
        output.push(HEX[(byte & 0x0f) as usize] as char);
    }
    output
}

#[cfg(test)]
pub(crate) mod test_support;

#[cfg(test)]
mod tests;
