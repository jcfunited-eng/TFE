//! Exact semantic validation of the current embodiment observation-v6 record.

use super::*;

const POSITION_KEYS: &[&str] = &["x_mm", "y_mm", "z_mm"];
const ROOM_KEYS: &[&str] = &["maximum", "minimum"];
const REGION_KEYS: &[&str] = &[
    "air",
    "bounds",
    "ceiling_height_mm",
    "illumination_ppm",
    "reflectance_ppm",
    "region_id",
];
const AIR_KEYS: &[&str] = &["odorant_mass_nanograms", "volume_cubic_mm"];
const PORTAL_KEYS: &[&str] = &[
    "air_flow_cubic_mm_per_second",
    "aperture_max_mm",
    "aperture_min_mm",
    "axis",
    "height_mm",
    "plane_mm",
    "portal_id",
    "region_ids",
];
const BODY_KEYS: &[&str] = &[
    "active_contact",
    "body_id",
    "held_object_id",
    "pose",
    "radius_mm",
    "reach_mm",
    "receptor_geometry",
];
const POSE_KEYS: &[&str] = &["heading_millidegrees", "position"];
const RECEPTOR_KEYS: &[&str] = &[
    "left_ear_offset_mm",
    "odorant_saturation_nanograms_per_cubic_meter",
    "olfactory_offset_mm",
    "oral_offset_mm",
    "oral_radius_mm",
    "retinal_offset_mm",
    "right_ear_offset_mm",
    "tastant_saturation_micrograms",
    "touch_mass_span_grams",
    "touch_offset_mm",
    "touch_radius_mm",
    "touch_roughness_span_micrometers",
    "touch_temperature_max_millikelvin",
    "touch_temperature_min_millikelvin",
];
const CONTACT_KEYS: &[&str] = &[
    "contact_patch_square_mm",
    "duration_microseconds",
    "kind",
    "object_id",
];
const OBJECT_KEYS: &[&str] = &[
    "held_by_body_id",
    "mass_grams",
    "material",
    "object_id",
    "optical_surface",
    "position",
    "radius_mm",
    "reflectance_ppm",
];
const MATERIAL_KEYS: &[&str] = &[
    "compliance_ppm",
    "moisture_ppm",
    "odorant_release_nanograms_per_second",
    "odorant_reservoir_nanograms",
    "roughness_micrometers",
    "surface_temperature_millikelvin",
    "tastant_mass_micrograms",
];
const OPTICAL_SURFACE_KEYS: &[&str] = &[
    "cell_palette_indices",
    "columns",
    "palette_reflectance_ppm",
    "rows",
];

const MAX_I32: i64 = (1_i64 << 31) - 1;
const MIN_I32: i64 = -(1_i64 << 31);
const MAX_PHYSICAL_PPM: u64 = 1_000_000;
const MAX_MATERIAL_MASS: u64 = (1_u64 << 63) - 1;
const MAX_OPTICAL_COLUMNS: u64 = 128;
const MAX_OPTICAL_ROWS: u64 = 160;
const MAX_OPTICAL_PALETTE: usize = 256;
const MIN_ACTION_MICROSECONDS: u64 = 1_000;
const MAX_ACTION_MICROSECONDS: u64 = 5_000_000;
const SELF_PORT_ID: &str = "guala.embodiment.w1";

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
struct Position {
    x: i64,
    y: i64,
    z: i64,
}

#[derive(Clone, Debug, Eq, PartialEq)]
struct Bounds {
    minimum: Position,
    maximum: Position,
}

impl Bounds {
    fn contains_floor_disc(&self, position: Position, radius: u64) -> bool {
        let radius = i128::from(radius);
        i128::from(position.z) == i128::from(self.minimum.z)
            && i128::from(self.minimum.x) + radius <= i128::from(position.x)
            && i128::from(position.x) <= i128::from(self.maximum.x) - radius
            && i128::from(self.minimum.y) + radius <= i128::from(position.y)
            && i128::from(position.y) <= i128::from(self.maximum.y) - radius
    }
}

#[derive(Clone, Debug, Eq, PartialEq)]
struct Air {
    volume: u64,
}

#[derive(Clone, Debug, Eq, PartialEq)]
struct Region {
    id: String,
    bounds: Bounds,
    air: Option<Air>,
}

#[derive(Clone, Debug, Eq, PartialEq)]
struct Portal {
    id: String,
    region_ids: [String; 2],
    axis: String,
    plane: i64,
    aperture_min: i64,
    aperture_max: i64,
    height: i64,
    air_flow: Option<u64>,
}

#[derive(Clone, Debug, Eq, PartialEq)]
struct ReceptorGeometry {
    touch_offset: Position,
    touch_radius: u64,
    oral_offset: Position,
    oral_radius: u64,
}

#[derive(Clone, Debug, Eq, PartialEq)]
struct Contact {
    kind: String,
    object_id: String,
    patch: u64,
}

#[derive(Clone, Debug, Eq, PartialEq)]
struct Body {
    id: String,
    position: Position,
    heading: u64,
    radius: u64,
    held_object_id: Option<String>,
    receptor_geometry: Option<ReceptorGeometry>,
    active_contact: Option<Contact>,
}

#[derive(Clone, Debug, Eq, PartialEq)]
struct PhysicalObject {
    id: String,
    radius: u64,
    position: Option<Position>,
    held_by_body_id: Option<String>,
    has_material: bool,
}

pub(super) struct VerifiedWorldRecord {
    pub(super) receipt: [u8; 32],
    pub(super) state_receipt: [u8; 32],
    pub(super) revision: u64,
}

pub(super) fn verify_world_record(
    mount: &WorldAuthorityMount,
    bytes: &[u8],
    budget: WorldBodyVerificationBudget,
) -> Result<VerifiedWorldRecord, WorldBodyVerificationError> {
    mount.ensure_within_admission(budget)?;
    let value = parse_canonical(
        bytes,
        budget.max_world_record_bytes,
        budget,
        "world observation",
    )?;
    let record = object(&value, "world observation")?;
    exact_keys(record, WORLD_RECORD_KEYS, "world observation")?;
    if string(record, "schema", "world observation")? != WORLD_OBSERVATION_SCHEMA {
        return Err(WorldBodyVerificationError::WrongSchema("world observation"));
    }

    let revision = bounded_unsigned_value(
        required(record, "revision", "world revision")?,
        0,
        WORLD_MAX_REVISION,
        "world revision",
    )?;
    let room_id = canonical_identifier(string(record, "room_id", "world room")?, "world room")?;
    let self_body_id = canonical_identifier(
        string(record, "self_body_id", "world self body")?,
        "world self body",
    )?;
    let room_bounds = parse_bounds(required(record, "room_bounds", "world room bounds")?)?;

    let region_values = array(record, "regions", "world regions")?;
    bounded_count(
        region_values.len(),
        3,
        mount.limits.max_regions,
        "world regions",
    )?;
    let regions: Vec<Region> = region_values
        .iter()
        .map(parse_region)
        .collect::<Result<_, _>>()?;
    require_strict_order(regions.iter().map(|item| item.id.as_str()), "world regions")?;

    let portal_values = array(record, "portals", "world portals")?;
    bounded_count(
        portal_values.len(),
        2,
        mount.limits.max_portals,
        "world portals",
    )?;
    let portals: Vec<Portal> = portal_values
        .iter()
        .map(parse_portal)
        .collect::<Result<_, _>>()?;
    require_strict_order(portals.iter().map(|item| item.id.as_str()), "world portals")?;

    let body_values = array(record, "bodies", "world bodies")?;
    bounded_count(
        body_values.len(),
        2,
        mount.limits.max_bodies,
        "world bodies",
    )?;
    let bodies: Vec<Body> = body_values
        .iter()
        .map(parse_body)
        .collect::<Result<_, _>>()?;
    require_strict_order(bodies.iter().map(|item| item.id.as_str()), "world bodies")?;

    let object_values = array(record, "objects", "world objects")?;
    bounded_count(
        object_values.len(),
        1,
        mount.limits.max_objects,
        "world objects",
    )?;
    let objects: Vec<PhysicalObject> = object_values
        .iter()
        .map(parse_physical_object)
        .collect::<Result<_, _>>()?;
    require_strict_order(objects.iter().map(|item| item.id.as_str()), "world objects")?;

    validate_world(
        mount,
        room_id,
        &room_bounds,
        self_body_id,
        &regions,
        &portals,
        &bodies,
        &objects,
    )?;

    let provided_state = digest_field(record, "state_sha256", "world state")?;
    let mut world = record.clone();
    world.remove("schema");
    world.remove("state_sha256");
    world.remove("authority_hmac_sha256");
    world.remove("authority_receipt_sha256");
    let world_bytes = canonical_value(&Value::Object(world))?;
    let actual_state: [u8; 32] = Sha256::digest(&world_bytes).into();
    if provided_state != actual_state {
        return Err(WorldBodyVerificationError::ReceiptMismatch("world state"));
    }

    let provided_hmac = digest_field(record, "authority_hmac_sha256", "world observation")?;
    let mut unsigned_record = record.clone();
    unsigned_record.remove("authority_hmac_sha256");
    unsigned_record.remove("authority_receipt_sha256");
    let unsigned_value = Value::Object(unsigned_record);
    verify_hmac(
        mount.key.as_slice(),
        WORLD_OBSERVATION_DOMAIN,
        &canonical_value(&unsigned_value)?,
        &provided_hmac,
        "world observation",
    )?;
    let receipt = receipt_digest(&provided_hmac, &unsigned_value)?;
    if receipt != digest_field(record, "authority_receipt_sha256", "world observation")? {
        return Err(WorldBodyVerificationError::ReceiptMismatch(
            "world observation",
        ));
    }
    Ok(VerifiedWorldRecord {
        receipt,
        state_receipt: actual_state,
        revision,
    })
}

fn parse_position(
    value: &Value,
    name: &'static str,
) -> Result<Position, WorldBodyVerificationError> {
    let record = object(value, name)?;
    exact_keys(record, POSITION_KEYS, name)?;
    Ok(Position {
        x: bounded_signed(record, "x_mm", MIN_I32, MAX_I32, name)?,
        y: bounded_signed(record, "y_mm", MIN_I32, MAX_I32, name)?,
        z: bounded_signed(record, "z_mm", MIN_I32, MAX_I32, name)?,
    })
}

fn parse_bounds(value: &Value) -> Result<Bounds, WorldBodyVerificationError> {
    let record = object(value, "world bounds")?;
    exact_keys(record, ROOM_KEYS, "world bounds")?;
    let result = Bounds {
        minimum: parse_position(
            required(record, "minimum", "world bounds")?,
            "world minimum",
        )?,
        maximum: parse_position(
            required(record, "maximum", "world bounds")?,
            "world maximum",
        )?,
    };
    if result.minimum.x >= result.maximum.x
        || result.minimum.y >= result.maximum.y
        || result.minimum.z > result.maximum.z
    {
        return Err(WorldBodyVerificationError::InvalidValue("world bounds"));
    }
    Ok(result)
}

fn parse_region(value: &Value) -> Result<Region, WorldBodyVerificationError> {
    let record = object(value, "world region")?;
    exact_keys(record, REGION_KEYS, "world region")?;
    let id = canonical_identifier(string(record, "region_id", "world region")?, "world region")?;
    let bounds = parse_bounds(required(record, "bounds", "world region")?)?;
    let ceiling =
        nullable_bounded_signed(record, "ceiling_height_mm", 1, MAX_I32, "world ceiling")?;
    if ceiling.is_some_and(|value| value > bounds.maximum.z) {
        return Err(WorldBodyVerificationError::InvalidValue("world ceiling"));
    }
    physical_bands(
        required(record, "reflectance_ppm", "region reflectance")?,
        "region reflectance",
    )?;
    physical_bands(
        required(record, "illumination_ppm", "region illumination")?,
        "region illumination",
    )?;
    let air = match required(record, "air", "world region air")? {
        Value::Null => None,
        value => Some(parse_air(value, &bounds)?),
    };
    Ok(Region { id, bounds, air })
}

fn parse_air(value: &Value, bounds: &Bounds) -> Result<Air, WorldBodyVerificationError> {
    let record = object(value, "world air")?;
    exact_keys(record, AIR_KEYS, "world air")?;
    let volume = bounded_unsigned(
        record,
        "volume_cubic_mm",
        1,
        MAX_MATERIAL_MASS,
        "world air volume",
    )?;
    bounded_channels(
        required(record, "odorant_mass_nanograms", "world air odorants")?,
        8,
        0,
        MAX_MATERIAL_MASS,
        "world air odorants",
    )?;
    let expected = i128::from(bounds.maximum.x - bounds.minimum.x)
        * i128::from(bounds.maximum.y - bounds.minimum.y)
        * i128::from(bounds.maximum.z - bounds.minimum.z);
    if expected != i128::from(volume) {
        return Err(WorldBodyVerificationError::InvalidValue("world air volume"));
    }
    Ok(Air { volume })
}

fn parse_portal(value: &Value) -> Result<Portal, WorldBodyVerificationError> {
    let record = object(value, "world portal")?;
    exact_keys(record, PORTAL_KEYS, "world portal")?;
    let id = canonical_identifier(string(record, "portal_id", "world portal")?, "world portal")?;
    let raw_regions = array(record, "region_ids", "portal region pair")?;
    if raw_regions.len() != 2 {
        return Err(WorldBodyVerificationError::WrongShape("portal region pair"));
    }
    let left = raw_regions[0]
        .as_str()
        .ok_or(WorldBodyVerificationError::InvalidValue(
            "portal region pair",
        ))?;
    let right = raw_regions[1]
        .as_str()
        .ok_or(WorldBodyVerificationError::InvalidValue(
            "portal region pair",
        ))?;
    canonical_identifier(left, "portal region")?;
    canonical_identifier(right, "portal region")?;
    if left >= right {
        return Err(WorldBodyVerificationError::InvalidValue(
            "portal region pair",
        ));
    }
    let axis = string(record, "axis", "portal axis")?;
    if axis != "x" && axis != "y" {
        return Err(WorldBodyVerificationError::InvalidValue("portal axis"));
    }
    let aperture_min = bounded_signed(
        record,
        "aperture_min_mm",
        MIN_I32,
        MAX_I32,
        "portal aperture",
    )?;
    let aperture_max = bounded_signed(
        record,
        "aperture_max_mm",
        MIN_I32,
        MAX_I32,
        "portal aperture",
    )?;
    let height = bounded_signed(record, "height_mm", MIN_I32, MAX_I32, "portal height")?;
    if aperture_min >= aperture_max || height <= 0 {
        return Err(WorldBodyVerificationError::InvalidValue("portal aperture"));
    }
    Ok(Portal {
        id,
        region_ids: [left.to_owned(), right.to_owned()],
        axis: axis.to_owned(),
        plane: bounded_signed(record, "plane_mm", MIN_I32, MAX_I32, "portal plane")?,
        aperture_min,
        aperture_max,
        height,
        air_flow: nullable_bounded_unsigned(
            record,
            "air_flow_cubic_mm_per_second",
            1,
            MAX_MATERIAL_MASS,
            "portal air flow",
        )?,
    })
}

fn parse_body(value: &Value) -> Result<Body, WorldBodyVerificationError> {
    let record = object(value, "world body")?;
    exact_keys(record, BODY_KEYS, "world body")?;
    let id = canonical_identifier(string(record, "body_id", "world body")?, "world body")?;
    let pose = object(
        required(record, "pose", "world body pose")?,
        "world body pose",
    )?;
    exact_keys(pose, POSE_KEYS, "world body pose")?;
    let position = parse_position(
        required(pose, "position", "world body pose")?,
        "world body position",
    )?;
    let heading = bounded_unsigned(
        pose,
        "heading_millidegrees",
        0,
        359_999,
        "world body heading",
    )?;
    let radius = bounded_unsigned(record, "radius_mm", 1, 1_000_000, "world body radius")?;
    bounded_unsigned(record, "reach_mm", 1, 1_000_000, "world body reach")?;
    let held_object_id = nullable_identifier(record, "held_object_id", "world held object")?;
    let receptor_geometry = match required(record, "receptor_geometry", "world receptor geometry")?
    {
        Value::Null => None,
        value => Some(parse_receptor_geometry(value)?),
    };
    let active_contact = match required(record, "active_contact", "world body contact")? {
        Value::Null => None,
        value => Some(parse_contact(value)?),
    };
    Ok(Body {
        id,
        position,
        heading,
        radius,
        held_object_id,
        receptor_geometry,
        active_contact,
    })
}

fn parse_receptor_geometry(value: &Value) -> Result<ReceptorGeometry, WorldBodyVerificationError> {
    let record = object(value, "world receptor geometry")?;
    exact_keys(record, RECEPTOR_KEYS, "world receptor geometry")?;
    for (key, name) in [
        ("retinal_offset_mm", "retinal offset"),
        ("left_ear_offset_mm", "left ear offset"),
        ("right_ear_offset_mm", "right ear offset"),
        ("olfactory_offset_mm", "olfactory offset"),
    ] {
        parse_position(required(record, key, name)?, name)?;
    }
    let touch_offset = parse_position(
        required(record, "touch_offset_mm", "touch offset")?,
        "touch offset",
    )?;
    let oral_offset = parse_position(
        required(record, "oral_offset_mm", "oral offset")?,
        "oral offset",
    )?;
    let touch_radius =
        bounded_unsigned(record, "touch_radius_mm", 1, 1_000_000_000, "touch radius")?;
    let oral_radius = bounded_unsigned(record, "oral_radius_mm", 1, 1_000_000_000, "oral radius")?;
    bounded_unsigned(
        record,
        "touch_mass_span_grams",
        1,
        1_000_000_000,
        "touch mass span",
    )?;
    bounded_unsigned(
        record,
        "touch_roughness_span_micrometers",
        1,
        1_000_000_000,
        "touch roughness span",
    )?;
    let minimum = bounded_unsigned(
        record,
        "touch_temperature_min_millikelvin",
        1,
        1_000_000,
        "touch temperature",
    )?;
    let maximum = bounded_unsigned(
        record,
        "touch_temperature_max_millikelvin",
        1,
        1_000_000,
        "touch temperature",
    )?;
    if minimum >= maximum {
        return Err(WorldBodyVerificationError::InvalidValue(
            "touch temperature",
        ));
    }
    bounded_channels(
        required(
            record,
            "odorant_saturation_nanograms_per_cubic_meter",
            "olfactory saturation",
        )?,
        8,
        1,
        MAX_MATERIAL_MASS,
        "olfactory saturation",
    )?;
    bounded_channels(
        required(
            record,
            "tastant_saturation_micrograms",
            "gustatory saturation",
        )?,
        5,
        1,
        MAX_MATERIAL_MASS,
        "gustatory saturation",
    )?;
    Ok(ReceptorGeometry {
        touch_offset,
        touch_radius,
        oral_offset,
        oral_radius,
    })
}

fn parse_contact(value: &Value) -> Result<Contact, WorldBodyVerificationError> {
    let record = object(value, "world body contact")?;
    exact_keys(record, CONTACT_KEYS, "world body contact")?;
    let kind = string(record, "kind", "world body contact")?;
    if kind != "touch" && kind != "oral" {
        return Err(WorldBodyVerificationError::InvalidValue(
            "world body contact",
        ));
    }
    let object_id = canonical_identifier(
        string(record, "object_id", "world body contact")?,
        "world body contact",
    )?;
    let patch = bounded_unsigned(
        record,
        "contact_patch_square_mm",
        1,
        1_000_000_000,
        "world contact patch",
    )?;
    bounded_unsigned(
        record,
        "duration_microseconds",
        MIN_ACTION_MICROSECONDS,
        MAX_ACTION_MICROSECONDS,
        "world contact duration",
    )?;
    Ok(Contact {
        kind: kind.to_owned(),
        object_id,
        patch,
    })
}

fn parse_physical_object(value: &Value) -> Result<PhysicalObject, WorldBodyVerificationError> {
    let record = object(value, "world object")?;
    exact_keys(record, OBJECT_KEYS, "world object")?;
    let id = canonical_identifier(string(record, "object_id", "world object")?, "world object")?;
    let radius = bounded_unsigned(record, "radius_mm", 1, 1_000_000, "world object radius")?;
    bounded_unsigned(record, "mass_grams", 1, 1_000_000_000, "world object mass")?;
    let position = match required(record, "position", "world object position")? {
        Value::Null => None,
        value => Some(parse_position(value, "world object position")?),
    };
    let held_by_body_id = nullable_identifier(record, "held_by_body_id", "world holding body")?;
    if position.is_none() == held_by_body_id.is_none() {
        return Err(WorldBodyVerificationError::InvalidValue(
            "world object placement",
        ));
    }
    physical_bands(
        required(record, "reflectance_ppm", "object reflectance")?,
        "object reflectance",
    )?;
    let has_material = match required(record, "material", "world object material")? {
        Value::Null => false,
        value => {
            parse_material(value)?;
            true
        }
    };
    if let value @ Value::Object(_) = required(record, "optical_surface", "world optical surface")?
    {
        parse_optical_surface(value)?;
    } else if required(record, "optical_surface", "world optical surface")? != &Value::Null {
        return Err(WorldBodyVerificationError::WrongShape(
            "world optical surface",
        ));
    }
    Ok(PhysicalObject {
        id,
        radius,
        position,
        held_by_body_id,
        has_material,
    })
}

fn parse_material(value: &Value) -> Result<(), WorldBodyVerificationError> {
    let record = object(value, "world object material")?;
    exact_keys(record, MATERIAL_KEYS, "world object material")?;
    bounded_channels(
        required(
            record,
            "odorant_reservoir_nanograms",
            "object odorant reservoir",
        )?,
        8,
        0,
        MAX_MATERIAL_MASS,
        "object odorant reservoir",
    )?;
    bounded_channels(
        required(
            record,
            "odorant_release_nanograms_per_second",
            "object odorant release",
        )?,
        8,
        0,
        MAX_MATERIAL_MASS,
        "object odorant release",
    )?;
    bounded_channels(
        required(record, "tastant_mass_micrograms", "object tastant mass")?,
        5,
        0,
        MAX_MATERIAL_MASS,
        "object tastant mass",
    )?;
    bounded_unsigned(
        record,
        "surface_temperature_millikelvin",
        1,
        1_000_000,
        "object temperature",
    )?;
    bounded_unsigned(
        record,
        "compliance_ppm",
        0,
        MAX_PHYSICAL_PPM,
        "object compliance",
    )?;
    bounded_unsigned(
        record,
        "roughness_micrometers",
        0,
        1_000_000,
        "object roughness",
    )?;
    bounded_unsigned(
        record,
        "moisture_ppm",
        0,
        MAX_PHYSICAL_PPM,
        "object moisture",
    )?;
    Ok(())
}

fn parse_optical_surface(value: &Value) -> Result<(), WorldBodyVerificationError> {
    let record = object(value, "world optical surface")?;
    exact_keys(record, OPTICAL_SURFACE_KEYS, "world optical surface")?;
    let columns = bounded_unsigned(record, "columns", 1, MAX_OPTICAL_COLUMNS, "optical columns")?;
    let rows = bounded_unsigned(record, "rows", 1, MAX_OPTICAL_ROWS, "optical rows")?;
    let palette = array(record, "palette_reflectance_ppm", "optical palette")?;
    bounded_count(
        palette.len(),
        2,
        MAX_OPTICAL_PALETTE as u64,
        "optical palette",
    )?;
    let mut distinct = BTreeSet::new();
    for entry in palette {
        let bands = physical_bands(entry, "optical palette")?;
        if !distinct.insert(bands) {
            return Err(WorldBodyVerificationError::InvalidValue("optical palette"));
        }
    }
    let cells = array(record, "cell_palette_indices", "optical cells")?;
    let expected = columns
        .checked_mul(rows)
        .ok_or(WorldBodyVerificationError::InvalidValue("optical cells"))?;
    if u64::try_from(cells.len()).ok() != Some(expected) {
        return Err(WorldBodyVerificationError::InvalidValue("optical cells"));
    }
    let mut used = BTreeSet::new();
    for value in cells {
        let index = bounded_unsigned_value(value, 0, (palette.len() - 1) as u64, "optical cell")?;
        used.insert(index);
    }
    if used.len() != palette.len() {
        return Err(WorldBodyVerificationError::InvalidValue(
            "optical palette usage",
        ));
    }
    Ok(())
}

#[allow(clippy::too_many_arguments)]
fn validate_world(
    mount: &WorldAuthorityMount,
    room_id: String,
    room_bounds: &Bounds,
    self_body_id: String,
    regions: &[Region],
    portals: &[Portal],
    bodies: &[Body],
    objects: &[PhysicalObject],
) -> Result<(), WorldBodyVerificationError> {
    validate_physical_topology(regions, portals)?;
    let room_region = regions.iter().find(|item| item.id == room_id);
    if room_region.map(|item| &item.bounds) != Some(room_bounds) {
        return Err(WorldBodyVerificationError::InvalidValue(
            "world room projection",
        ));
    }
    if !bodies.iter().any(|item| item.id == self_body_id) {
        return Err(WorldBodyVerificationError::InvalidValue("world self body"));
    }
    validate_actor_ports(mount, &self_body_id, bodies)?;

    let mut held_by_body: BTreeMap<&str, Vec<&str>> = bodies
        .iter()
        .map(|body| (body.id.as_str(), Vec::new()))
        .collect();
    let mut placed = Vec::new();
    for item in objects {
        if let Some(holder) = item.held_by_body_id.as_deref() {
            held_by_body
                .get_mut(holder)
                .ok_or(WorldBodyVerificationError::InvalidValue(
                    "world holding body",
                ))?
                .push(item.id.as_str());
        } else {
            let position = item
                .position
                .ok_or(WorldBodyVerificationError::InvalidValue(
                    "world object position",
                ))?;
            if region_containing(regions, position, item.radius).is_none() {
                return Err(WorldBodyVerificationError::InvalidValue(
                    "world object geometry",
                ));
            }
            placed.push(item);
        }
    }
    let object_by_id: BTreeMap<&str, &PhysicalObject> = objects
        .iter()
        .map(|item| (item.id.as_str(), item))
        .collect();
    let mut occupied: Vec<(&Body, u64, usize)> = Vec::with_capacity(bodies.len());
    for body in bodies {
        let held =
            held_by_body
                .get(body.id.as_str())
                .ok_or(WorldBodyVerificationError::InvalidValue(
                    "world holding topology",
                ))?;
        let expected_held = if held.len() == 1 { Some(held[0]) } else { None };
        if held.len() > 1 || body.held_object_id.as_deref() != expected_held {
            return Err(WorldBodyVerificationError::InvalidValue(
                "world holding reciprocity",
            ));
        }
        let carried_radius = match expected_held {
            Some(id) => body.radius.max(object_by_id[id].radius),
            None => body.radius,
        };
        let region = region_containing(regions, body.position, carried_radius).ok_or(
            WorldBodyVerificationError::InvalidValue("world body geometry"),
        )?;
        occupied.push((body, carried_radius, region));
        if let Some(contact) = &body.active_contact {
            validate_contact(body, contact, &object_by_id)?;
        }
    }
    let self_region = occupied
        .iter()
        .find(|(body, _, _)| body.id == self_body_id)
        .map(|(_, _, region)| regions[*region].id.as_str());
    if self_region != Some(room_id.as_str()) {
        return Err(WorldBodyVerificationError::InvalidValue(
            "world self region",
        ));
    }

    for (index, (left, left_radius, left_region)) in occupied.iter().enumerate() {
        for (right, right_radius, right_region) in &occupied[index + 1..] {
            if left_region == right_region
                && floor_discs_overlap(left.position, *left_radius, right.position, *right_radius)
            {
                return Err(WorldBodyVerificationError::InvalidValue(
                    "world body collision",
                ));
            }
        }
    }
    for (body, radius, body_region) in &occupied {
        for item in &placed {
            let position = item.position.expect("placed object has position");
            let object_region = region_containing(regions, position, item.radius)
                .expect("placed object has verified region");
            if *body_region == object_region
                && floor_discs_overlap(body.position, *radius, position, item.radius)
            {
                return Err(WorldBodyVerificationError::InvalidValue(
                    "world body/object collision",
                ));
            }
        }
    }
    for (index, left) in placed.iter().enumerate() {
        let left_position = left.position.expect("placed object has position");
        let left_region = region_containing(regions, left_position, left.radius)
            .expect("placed object has verified region");
        for right in &placed[index + 1..] {
            let right_position = right.position.expect("placed object has position");
            let right_region = region_containing(regions, right_position, right.radius)
                .expect("placed object has verified region");
            if left_region == right_region
                && floor_discs_overlap(left_position, left.radius, right_position, right.radius)
            {
                return Err(WorldBodyVerificationError::InvalidValue(
                    "world object collision",
                ));
            }
        }
    }
    Ok(())
}

fn validate_physical_topology(
    regions: &[Region],
    portals: &[Portal],
) -> Result<(), WorldBodyVerificationError> {
    let region_by_id: BTreeMap<&str, &Region> = regions
        .iter()
        .map(|item| (item.id.as_str(), item))
        .collect();
    let mut edges = BTreeSet::new();
    for portal in portals {
        if !edges.insert((portal.region_ids[0].as_str(), portal.region_ids[1].as_str())) {
            return Err(WorldBodyVerificationError::InvalidValue(
                "world portal edge",
            ));
        }
        let left = region_by_id.get(portal.region_ids[0].as_str()).ok_or(
            WorldBodyVerificationError::InvalidValue("world portal region"),
        )?;
        let right = region_by_id.get(portal.region_ids[1].as_str()).ok_or(
            WorldBodyVerificationError::InvalidValue("world portal region"),
        )?;
        let (shared, overlap_min, overlap_max) = if portal.axis == "x" {
            (
                shared_boundary(
                    [left.bounds.minimum.x, left.bounds.maximum.x],
                    [right.bounds.minimum.x, right.bounds.maximum.x],
                ),
                left.bounds.minimum.y.max(right.bounds.minimum.y),
                left.bounds.maximum.y.min(right.bounds.maximum.y),
            )
        } else {
            (
                shared_boundary(
                    [left.bounds.minimum.y, left.bounds.maximum.y],
                    [right.bounds.minimum.y, right.bounds.maximum.y],
                ),
                left.bounds.minimum.x.max(right.bounds.minimum.x),
                left.bounds.maximum.x.min(right.bounds.maximum.x),
            )
        };
        if shared != Some(portal.plane)
            || !(overlap_min <= portal.aperture_min
                && portal.aperture_min < portal.aperture_max
                && portal.aperture_max <= overlap_max)
            || portal.height > left.bounds.maximum.z.min(right.bounds.maximum.z)
        {
            return Err(WorldBodyVerificationError::InvalidValue(
                "world portal aperture",
            ));
        }
        if portal.air_flow.is_some() && (left.air.is_none() || right.air.is_none()) {
            return Err(WorldBodyVerificationError::InvalidValue(
                "world portal air topology",
            ));
        }
    }
    for region in regions {
        let incident_flow: i128 = portals
            .iter()
            .filter(|portal| portal.region_ids.iter().any(|id| id == &region.id))
            .map(|portal| i128::from(portal.air_flow.unwrap_or(0)))
            .sum();
        if let Some(air) = &region.air {
            if incident_flow * i128::from(MAX_ACTION_MICROSECONDS)
                > i128::from(air.volume) * 1_000_000
            {
                return Err(WorldBodyVerificationError::InvalidValue(
                    "world portal air evacuation",
                ));
            }
        }
    }
    Ok(())
}

fn validate_actor_ports(
    mount: &WorldAuthorityMount,
    self_body_id: &str,
    bodies: &[Body],
) -> Result<(), WorldBodyVerificationError> {
    if mount.actor_ports.len() != bodies.len() {
        return Err(WorldBodyVerificationError::InvalidValue(
            "world actor ports",
        ));
    }
    let body_ids: BTreeSet<&str> = bodies.iter().map(|body| body.id.as_str()).collect();
    let actor_ids: BTreeSet<&str> = mount
        .actor_ports
        .iter()
        .map(|port| port.actor_body_id.as_str())
        .collect();
    if actor_ids.len() != mount.actor_ports.len() || actor_ids != body_ids {
        return Err(WorldBodyVerificationError::InvalidValue(
            "world actor reciprocity",
        ));
    }
    let self_ports: Vec<&WorldActorPort> = mount
        .actor_ports
        .iter()
        .filter(|port| port.actor_body_id == self_body_id)
        .collect();
    if self_ports.len() != 1 || self_ports[0].port_id != SELF_PORT_ID {
        return Err(WorldBodyVerificationError::InvalidValue(
            "world self actor port",
        ));
    }
    Ok(())
}

fn validate_contact(
    body: &Body,
    contact: &Contact,
    objects: &BTreeMap<&str, &PhysicalObject>,
) -> Result<(), WorldBodyVerificationError> {
    let item =
        objects
            .get(contact.object_id.as_str())
            .ok_or(WorldBodyVerificationError::InvalidValue(
                "world contact object",
            ))?;
    let geometry =
        body.receptor_geometry
            .as_ref()
            .ok_or(WorldBodyVerificationError::InvalidValue(
                "world contact receptor",
            ))?;
    if !item.has_material {
        return Err(WorldBodyVerificationError::InvalidValue(
            "world contact material",
        ));
    }
    if contact.kind == "oral"
        && (body.held_object_id.as_deref() != Some(item.id.as_str())
            || item.held_by_body_id.as_deref() != Some(body.id.as_str()))
    {
        return Err(WorldBodyVerificationError::InvalidValue(
            "world oral contact",
        ));
    }
    let object_position = item.position.unwrap_or(body.position);
    let (offset, receptor_radius) = if contact.kind == "oral" {
        (geometry.oral_offset, geometry.oral_radius)
    } else {
        (geometry.touch_offset, geometry.touch_radius)
    };
    let receptor = receptor_position(body, offset);
    let expected = receptor.and_then(|position| {
        derived_contact_patch(position, receptor_radius, object_position, item.radius)
    });
    if expected != Some(contact.patch) {
        return Err(WorldBodyVerificationError::InvalidValue(
            "world contact geometry",
        ));
    }
    Ok(())
}

fn region_containing(regions: &[Region], position: Position, radius: u64) -> Option<usize> {
    let mut result = None;
    for (index, region) in regions.iter().enumerate() {
        if region.bounds.contains_floor_disc(position, radius) {
            if result.is_some() {
                return None;
            }
            result = Some(index);
        }
    }
    result
}

fn receptor_position(body: &Body, offset: Position) -> Option<Position> {
    if body.heading % 90_000 != 0 {
        return None;
    }
    let (dx, dy) = match (body.heading / 90_000) % 4 {
        0 => (offset.x, offset.y),
        1 => (-offset.y, offset.x),
        2 => (-offset.x, -offset.y),
        _ => (offset.y, -offset.x),
    };
    let x = body.position.x.checked_add(dx)?;
    let y = body.position.y.checked_add(dy)?;
    let z = body.position.z.checked_add(offset.z)?;
    Some(Position { x, y, z })
}

fn derived_contact_patch(
    receptor: Position,
    receptor_radius: u64,
    object: Position,
    object_radius: u64,
) -> Option<u64> {
    let dx = i128::from(receptor.x) - i128::from(object.x);
    let dy = i128::from(receptor.y) - i128::from(object.y);
    let dz = i128::from(receptor.z) - i128::from(object.z);
    let distance_squared = u128::try_from(dx * dx + dy * dy + dz * dz).ok()?;
    let combined = u128::from(receptor_radius) + u128::from(object_radius);
    if distance_squared > combined * combined {
        return None;
    }
    let overlap = combined - integer_square_root(distance_squared);
    let patch_radius = u128::from(receptor_radius)
        .min(u128::from(object_radius))
        .min(overlap.max(1));
    u64::try_from(patch_radius * patch_radius).ok()
}

fn integer_square_root(value: u128) -> u128 {
    if value < 2 {
        return value;
    }
    let mut low = 1_u128;
    let mut high = value.min(1_u128 << 64);
    while low + 1 < high {
        let middle = low + (high - low) / 2;
        if middle <= value / middle {
            low = middle;
        } else {
            high = middle;
        }
    }
    low
}

fn floor_discs_overlap(
    left: Position,
    left_radius: u64,
    right: Position,
    right_radius: u64,
) -> bool {
    let dx = i128::from(left.x) - i128::from(right.x);
    let dy = i128::from(left.y) - i128::from(right.y);
    let radius = i128::from(left_radius) + i128::from(right_radius);
    dx * dx + dy * dy < radius * radius
}

fn shared_boundary(left: [i64; 2], right: [i64; 2]) -> Option<i64> {
    let values: Vec<i64> = left
        .into_iter()
        .filter(|value| right.contains(value))
        .collect();
    if values.len() == 1 {
        Some(values[0])
    } else {
        None
    }
}

fn physical_bands(
    value: &Value,
    name: &'static str,
) -> Result<[u64; 6], WorldBodyVerificationError> {
    let values = value
        .as_array()
        .ok_or(WorldBodyVerificationError::WrongShape(name))?;
    if values.len() != 6 {
        return Err(WorldBodyVerificationError::InvalidValue(name));
    }
    let mut result = [0_u64; 6];
    for (target, value) in result.iter_mut().zip(values) {
        *target = bounded_unsigned_value(value, 0, MAX_PHYSICAL_PPM, name)?;
    }
    Ok(result)
}

fn bounded_channels(
    value: &Value,
    expected: usize,
    minimum: u64,
    maximum: u64,
    name: &'static str,
) -> Result<(), WorldBodyVerificationError> {
    let values = value
        .as_array()
        .ok_or(WorldBodyVerificationError::WrongShape(name))?;
    if values.len() != expected {
        return Err(WorldBodyVerificationError::InvalidValue(name));
    }
    for value in values {
        bounded_unsigned_value(value, minimum, maximum, name)?;
    }
    Ok(())
}

fn required<'a>(
    record: &'a Map<String, Value>,
    key: &str,
    name: &'static str,
) -> Result<&'a Value, WorldBodyVerificationError> {
    record
        .get(key)
        .ok_or(WorldBodyVerificationError::WrongShape(name))
}

fn bounded_signed(
    record: &Map<String, Value>,
    key: &str,
    minimum: i64,
    maximum: i64,
    name: &'static str,
) -> Result<i64, WorldBodyVerificationError> {
    let value = required(record, key, name)?
        .as_i64()
        .ok_or(WorldBodyVerificationError::InvalidValue(name))?;
    if value < minimum || value > maximum {
        return Err(WorldBodyVerificationError::InvalidValue(name));
    }
    Ok(value)
}

fn nullable_bounded_signed(
    record: &Map<String, Value>,
    key: &str,
    minimum: i64,
    maximum: i64,
    name: &'static str,
) -> Result<Option<i64>, WorldBodyVerificationError> {
    match required(record, key, name)? {
        Value::Null => Ok(None),
        _ => bounded_signed(record, key, minimum, maximum, name).map(Some),
    }
}

fn bounded_unsigned(
    record: &Map<String, Value>,
    key: &str,
    minimum: u64,
    maximum: u64,
    name: &'static str,
) -> Result<u64, WorldBodyVerificationError> {
    bounded_unsigned_value(required(record, key, name)?, minimum, maximum, name)
}

fn bounded_unsigned_value(
    value: &Value,
    minimum: u64,
    maximum: u64,
    name: &'static str,
) -> Result<u64, WorldBodyVerificationError> {
    let value = value
        .as_u64()
        .ok_or(WorldBodyVerificationError::InvalidValue(name))?;
    if value < minimum || value > maximum {
        return Err(WorldBodyVerificationError::InvalidValue(name));
    }
    Ok(value)
}

fn nullable_bounded_unsigned(
    record: &Map<String, Value>,
    key: &str,
    minimum: u64,
    maximum: u64,
    name: &'static str,
) -> Result<Option<u64>, WorldBodyVerificationError> {
    match required(record, key, name)? {
        Value::Null => Ok(None),
        value => bounded_unsigned_value(value, minimum, maximum, name).map(Some),
    }
}

fn canonical_identifier(
    value: &str,
    name: &'static str,
) -> Result<String, WorldBodyVerificationError> {
    identifier(value, name)?;
    Ok(value.to_owned())
}

fn nullable_identifier(
    record: &Map<String, Value>,
    key: &str,
    name: &'static str,
) -> Result<Option<String>, WorldBodyVerificationError> {
    match required(record, key, name)? {
        Value::Null => Ok(None),
        Value::String(value) => canonical_identifier(value, name).map(Some),
        _ => Err(WorldBodyVerificationError::InvalidValue(name)),
    }
}

fn bounded_count(
    actual: usize,
    minimum: u64,
    maximum: u64,
    name: &'static str,
) -> Result<(), WorldBodyVerificationError> {
    let actual =
        u64::try_from(actual).map_err(|_| WorldBodyVerificationError::InputBudgetExceeded(name))?;
    if actual < minimum || actual > maximum {
        return Err(WorldBodyVerificationError::InputBudgetExceeded(name));
    }
    Ok(())
}

fn require_strict_order<'a>(
    values: impl Iterator<Item = &'a str>,
    name: &'static str,
) -> Result<(), WorldBodyVerificationError> {
    let mut prior: Option<&str> = None;
    for value in values {
        if prior.is_some_and(|previous| previous >= value) {
            return Err(WorldBodyVerificationError::InvalidValue(name));
        }
        prior = Some(value);
    }
    Ok(())
}
