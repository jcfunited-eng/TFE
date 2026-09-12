//! Startup-only logical storage arithmetic for the ordinary physical input path.
//!
//! These values describe source-owned content and UF working objects. They are
//! NOT allocator/cgroup peak measurements: container spare capacity, allocator
//! metadata and bigint-library internal scratch still require the scoped RSS
//! proof. Nothing here reads neurons, emits an occurrence, or retains a profile.

use core::mem::size_of;
use num_rational::BigRational;
use crate::joint_uf_v1_4::{
    ContinuousJointUf, JointUfCoordinateBounds, JointUfGate, JointUfInput,
    JointUfResult, SevFrame,
};

/// A u64 rounding unit is also an upper bound on the payload of u32 limbs.
/// The BigRational header is counted by its containing object, not here.
fn rational_limb_bytes(numerator_bits: u128, denominator_bits: u128) -> u128 {
    (numerator_bits.div_ceil(u64::BITS as u128)
        + denominator_bits.div_ceil(u64::BITS as u128)) * size_of::<u64>() as u128
}

/// One occurrence is processed at a time. Callers take MAX over occurrences,
/// not SUM. P and N are codec-bounded u32 counts; all intermediate products
/// fit u128, and the final host-width conversion refuses rather than truncates.
pub(crate) fn uf_logical_working_bytes(
    ports: u32,
    frames: u32,
    timestamp_integer_bits: u32,
) -> Result<usize, String> {
    if ports == 0 || frames < 2 || timestamp_integer_bits == 0 {
        return Err("ordinary UF storage needs a nonempty temporal occurrence".into());
    }
    let p = u128::from(ports);
    let n = u128::from(frames);
    let b = u128::from(timestamp_integer_bits);
    let float = size_of::<f64>() as u128;
    let vector = size_of::<Vec<f64>>() as u128;
    let rational = size_of::<BigRational>() as u128;
    let index = size_of::<usize>() as u128;

    let input = size_of::<JointUfInput>() as u128
        + n * (vector + rational + rational_limb_bytes(b, b) + float)
        + n * p * float;
    let result = size_of::<JointUfResult>() as u128
        + n * (size_of::<SevFrame>() as u128 + 2 * p * float)
        + (n - 1) * (size_of::<JointUfGate>() as u128
            + 3 * size_of::<[i64; 3]>() as u128);

    // The rolling history cannot contain more than N source frames. Using
    // that upper bound avoids copying or changing the frozen kernel's W.
    // The other five vectors are pending field, open field/delta and two
    // means; each mean also holds two non-coordinate values.
    let stream = size_of::<ContinuousJointUf>() as u128
        + n * vector
        + ((n + 5) * p + 4) * float
        + p * size_of::<JointUfCoordinateBounds>() as u128;
    // Resolved-frame copies, mean/curvature and gate-drift work overlap only
    // within the active occurrence. Index/group copies partition its ports.
    let active_vectors = (6 * p + 2) * float
        + 2 * p * index + p * size_of::<Vec<usize>>() as u128;
    // Adjacent timestamp differences and accumulated gate durations are
    // reduced rationals. This covers the stream's live values, frame copies
    // and native expression results, not bigint-library internal scratch.
    let intervals = 8 * (rational + rational_limb_bytes(4 * b + 3, 4 * b))
        + rational + rational_limb_bytes(u64::BITS as u128, u64::BITS as u128);

    usize::try_from(input + result + stream + active_vectors + intervals)
        .map_err(|_| "ordinary UF logical working size exceeds host width".into())
}

fn rational_encoded_bytes(numerator_bits: u128, denominator_bits: u128) -> u128 {
    // An integer with b bits has at most max(b,1) decimal digits. Include a
    // possible numerator sign and both u16 lengths. This is an integer upper
    // bound, not a floating-point logarithm or a fitted memory multiplier.
    2 * size_of::<u16>() as u128 + numerator_bits.max(1) + 1
        + denominator_bits.max(1)
}

/// The real compact anatomy builder uses binary64 sources, i64 clock pairs,
/// zero phase and unit relevance. Derive its retained layout without generating
/// a lesson or walking any historical/neuronal state. Returned values are
/// (encoded upper bound, retained logical bytes), NOT construction/UF peak.
pub(crate) fn primary_source_logical_layout(
    anatomy: &crate::joint_source_episode::NativeJointSourceEpisode,
    frames: u32,
    selected_sense: Option<u8>,
) -> Result<(usize, usize), String> {
    use crate::joint_source_episode::{
        joint_source_storage_header_bytes, JointSourceCoordinate,
        JointSourceOccurrenceView, JointSourcePortView,
    };
    if frames < 2 || selected_sense.is_some_and(|sense| sense >= 6)
        || anatomy.joint_source_occurrences().len() != 1
    {
        return Err("ordinary source storage requires the mounted anatomy and clock".into());
    }
    let n = u128::from(frames);
    let rat = size_of::<BigRational>() as u128;
    let index = size_of::<usize>() as u128;
    // Metadata/profiles from the immutable template are copied unchanged.
    // Keeping its old samples in this numerical upper bound is conservative.
    let metadata = anatomy.joint_source_body().len() as u128;
    let time_encoded = rational_encoded_bytes(64, 64);
    let time_limbs = rational_limb_bytes(64, 64);
    let unit_encoded = rational_encoded_bytes(1, 1);
    let unit_limbs = rational_limb_bytes(1, 1);
    let zero_encoded = rational_encoded_bytes(0, 1);
    let zero_limbs = rational_limb_bytes(0, 1);
    let mut encoded = metadata + u16::MAX as u128 + size_of::<u16>() as u128;
    let mut retained = joint_source_storage_header_bytes() as u128
        + size_of::<JointSourceOccurrenceView>() as u128 + metadata;
    let mut ports = 0_u128;
    for port in anatomy.joint_source_ports().iter()
        .filter(|port| selected_sense.is_none_or(|sense| port.sense == sense))
    {
        ports += 1;
        let an = u128::from(port.field_offset.numer().bits());
        let ad = u128::from(port.field_offset.denom().bits());
        let bn = u128::from(port.field_scale.numer().bits());
        let bd = u128::from(port.field_scale.denom().bits());
        // For normalized binary64 s, |numerator(s)| uses <=53 bits; its
        // denominator can be 2^1074, which requires 1075 bits.
        // f=a+b*s. Reduction never increases these unreduced widths.
        let field_n = (an + bd + 1075).max(bn + 53 + ad) + 1;
        let field_d = ad + bd + 1075;
        encoded += n * (time_encoded + size_of::<f64>() as u128
            + zero_encoded + unit_encoded + rational_encoded_bytes(field_n, field_d));
        retained += size_of::<JointSourcePortView>() as u128
            + port.coordinates.len() as u128 * size_of::<JointSourceCoordinate>() as u128
            + n * (5 * rat + time_limbs + rational_limb_bytes(53, 1075)
                + zero_limbs + unit_limbs + rational_limb_bytes(field_n, field_d));
        // Map rational headers already live inside JointSourcePortView.
        for value in [&port.source_min, &port.source_max,
            &port.field_offset, &port.field_scale]
        {
            retained += rational_limb_bytes(
                u128::from(value.numer().bits()), u128::from(value.denom().bits()),
            );
        }
    }
    if ports == 0 || ports > u32::MAX as u128 {
        return Err("ordinary source anatomy has no admitted port extent".into());
    }
    encoded += n * (time_encoded + unit_encoded);
    retained += n * (2 * rat + time_limbs + unit_limbs)
        + 2 * ports * index + ports * size_of::<Vec<usize>>() as u128;
    // The Arc payload is retained with the parsed fields.
    retained += encoded;
    Ok((
        usize::try_from(encoded).map_err(|_| "ordinary source encoded size exceeds host width")?,
        usize::try_from(retained).map_err(|_| "ordinary source retained size exceeds host width")?,
    ))
}


/// Layout of the generated identity-map sources below. All their ports have
/// one coordinate. Metadata includes text, profiles and the encoded map, but
/// not sample bodies; rational headers and limbs are separate retained costs.
fn fixed_source_logical_layout(
    ports: u32,
    occurrences: u32,
    frames: u32,
    metadata: usize,
    coordinate_bits: (u32, u32),
    phase_bits: (u32, u32),
) -> Result<(usize, usize), String> {
    use crate::joint_source_episode::{
        joint_source_storage_header_bytes, JointSourceCoordinate,
        JointSourceOccurrenceView, JointSourcePortView,
    };
    let p = u128::from(ports);
    let o = u128::from(occurrences);
    let n = u128::from(frames);
    let samples = p * n;
    let clock_frames = o * n;
    let (cn, cd) = (u128::from(coordinate_bits.0), u128::from(coordinate_bits.1));
    let (pn, pd) = (u128::from(phase_bits.0), u128::from(phase_bits.1));
    let time_encoded = rational_encoded_bytes(64, 64);
    let unit_encoded = rational_encoded_bytes(1, 1);
    let encoded = metadata as u128
        + samples * (time_encoded + size_of::<f64>() as u128
            + rational_encoded_bytes(pn, pd) + unit_encoded
            + rational_encoded_bytes(cn, cd))
        + clock_frames * (time_encoded + unit_encoded);
    let retained = joint_source_storage_header_bytes() as u128
        + metadata as u128 + encoded
        + p * (size_of::<JointSourcePortView>() as u128
            + size_of::<JointSourceCoordinate>() as u128
            + 4 * rational_limb_bytes(1, 1))
        + o * size_of::<JointSourceOccurrenceView>() as u128
        + samples * (5 * size_of::<BigRational>() as u128
            + rational_limb_bytes(64, 64)
            + 2 * rational_limb_bytes(cn, cd)
            + rational_limb_bytes(pn, pd) + rational_limb_bytes(1, 1))
        + clock_frames * (2 * size_of::<BigRational>() as u128
            + rational_limb_bytes(64, 64) + rational_limb_bytes(1, 1))
        + 2 * p * size_of::<usize>() as u128
        + p * size_of::<Vec<usize>>() as u128;
    Ok((
        usize::try_from(encoded).map_err(|_| "ordinary generated source exceeds host width")?,
        usize::try_from(retained).map_err(|_| "ordinary retained source exceeds host width")?,
    ))
}

/// Capacity for the possible fixed body anatomy, never an emitted roster.
/// Impulse/guide and passive ports use identity maps; their exact position or
/// reacted-load ratios are bounded by u128 components. v3 has two endings,
/// v4/passive four; using the existing four-ending metadata bounds both.
pub(crate) fn body_source_logical_layout(
    endings_per_axis: u32,
    frames: u32,
) -> Result<(usize, usize), String> {
    if !matches!(endings_per_axis, 2 | 4) || frames < 2 {
        return Err("ordinary body layout requires its existing ending/clock shape".into());
    }
    let axes = crate::virtual_articulated_body::BODY_AXIS_COUNT as u32;
    fixed_source_logical_layout(
        axes * endings_per_axis, axes, frames,
        crate::articulated_body_joint_source_builder::articulated_source_metadata_bytes(),
        (128, 128), (0, 1),
    )
}

/// One native yaw/bundle occurrence has two samples, signed binary64 field,
/// real cyclic yaw phase, and five retained evidence rationals beside the
/// source. The empty physical contact array has no dynamic payload.
pub(crate) fn vestibular_source_logical_layout() -> Result<(usize, usize), String> {
    use crate::vestibular_joint_source_builder::{
        vestibular_source_metadata_bytes, VestibularJointSourceAdmission,
    };
    // tip = i128 relative velocity * u64 gain * u64-bounded local transfer.
    // Both exact tip components fit this upper bit width; time/height are
    // smaller. Serialized local-transfer *fields* still occupy 128 bits each.
    let evidence_bits = u128::from(i128::BITS) + 2 * u128::from(u64::BITS);
    let evidence_encoded = u32::try_from(rational_encoded_bytes(evidence_bits, evidence_bits))
        .map_err(|_| "ordinary vestibular evidence width exceeds its codec")?;
    let (encoded, retained) = fixed_source_logical_layout(
        1, 1, 2, vestibular_source_metadata_bytes(evidence_encoded)?,
        (53, 1075), (64, 64),
    )?;
    let retained = retained as u128 + size_of::<VestibularJointSourceAdmission>() as u128
        + 5 * rational_limb_bytes(evidence_bits, evidence_bits);
    Ok((encoded, usize::try_from(retained)
        .map_err(|_| "ordinary vestibular retained size exceeds host width")?))
}


/// Extra live content in the common decoder beyond the finished source.
/// This is parser-owned content, not BTree node/allocator or bigint-internal
/// scratch. Only one decoder is active, even when several sources are held.
fn source_parser_logical_temporary_bytes(
    encoded: u128,
    ports: u128,
    coordinates: u128,
    integer_bits: u128,
    borrowed_input: bool,
) -> u128 {
    use std::collections::BTreeSet;
    use crate::joint_source_episode::{
        joint_source_parser_header_bytes, JointSourceOccurrenceView, JointSourcePortView,
    };
    use crate::root_translation_terminal::RootTranslationProprioceptorTerminal;
    use crate::root_yaw_terminal::RootYawProprioceptorTerminal;
    use crate::virtual_articulated_body::BodyProprioceptorTerminal;

    // The public borrowed decoder keeps its input and the Vec copy during
    // Arc conversion. The owned compact builder has only the Vec overlap.
    let input_overlap = if borrowed_input { 2 * encoded } else { encoded };
    // Duplicate port keys/coordinate axes, authority bytes, and integer
    // parse/canonicalization text. Authority has u32 rather than u16 lengths.
    let text = encoded + encoded + 4 * coordinates
        + 26 + 4 + "guala.joint_source.group.v1".len() as u128
        + 2 * encoded;
    let headers = crate::joint_source_episode::joint_source_storage_header_bytes() as u128
        + joint_source_parser_header_bytes() as u128
        + size_of::<JointSourcePortView>() as u128
        + size_of::<JointSourceOccurrenceView>() as u128
        + 6 * size_of::<Vec<u32>>() as u128
        + 5 * size_of::<BTreeSet<usize>>() as u128
        + 4 * size_of::<Vec<usize>>() as u128
        + ports * (size_of::<(u8, String, String)>() as u128
            + size_of::<(BodyProprioceptorTerminal, u32)>() as u128
            + size_of::<RootYawProprioceptorTerminal>() as u128
            + size_of::<RootTranslationProprioceptorTerminal>() as u128)
        + coordinates * size_of::<String>() as u128;
    let indices = ports * (size_of::<u32>() + 2 * size_of::<bool>()
        + 3 * size_of::<usize>()) as u128;
    // Affine inverse/check, prior-time clone and binary64 conversion have
    // at most twelve simultaneously visible integer expression slots. The
    // latter can shift 1074 bits; two more cover comparison/carry. No bound
    // on num-bigint's private multiplication/GCD workspace is claimed.
    let expression_bits = 2 * integer_bits + 1076;
    let arithmetic = 12 * (size_of::<num_bigint::BigInt>() as u128
        + expression_bits.div_ceil(u64::BITS as u128) * size_of::<u64>() as u128)
        + 4 * size_of::<BigRational>() as u128;
    input_overlap + text + headers + indices + arithmetic
}

/// Restored legacy body/yaw/translation records may contain full u16-length
/// rational integers. Their outer byte and aggregate cardinality bounds must
/// be enforced before decoding. A port can have F samples, not necessarily
/// two: the exact two-endpoint partition is checked only after parsing.
///
/// Returns (retained logical content, largest extra parser phase).
pub(crate) fn cold_source_logical_layout(
    encoded_limit: u32,
    ports: u32,
    samples: u32,
    occurrences: u32,
    occurrence_frames: u32,
    source_count: u32,
) -> Result<(usize, usize), String> {
    use crate::joint_source_episode::{
        joint_source_storage_header_bytes, JointSourceCoordinate,
        JointSourceOccurrenceView, JointSourcePortView,
    };
    if encoded_limit == 0 || ports == 0 || samples < ports || occurrences == 0
        || occurrence_frames < occurrences || source_count == 0
    {
        return Err("ordinary cold source bounds are empty or inconsistent".into());
    }
    let e = u128::from(encoded_limit);
    let p = u128::from(ports);
    let s = u128::from(samples);
    let o = u128::from(occurrences);
    let f = u128::from(occurrence_frames);
    // Two nonempty u16-length coordinate texts require at least six bytes.
    let coordinates = e / 6;
    // Decimal digit information is at most four bits per encoded byte.
    // Inversion (field-offset)/scale can reuse map integers F times per
    // port. This counts aggregate limb content, not Q copies of max width.
    let encoded_integer_bits = 4 * e;
    let rational_count = 4 * p + 5 * s + 2 * f;
    let retained_limb_bits = (1 + 2 * f) * encoded_integer_bits + s;
    let retained = 2 * e
        + u128::from(source_count) * joint_source_storage_header_bytes() as u128
        + p * size_of::<JointSourcePortView>() as u128
        + o * size_of::<JointSourceOccurrenceView>() as u128
        + coordinates * size_of::<JointSourceCoordinate>() as u128
        + (5 * s + 2 * f) * size_of::<BigRational>() as u128
        + p * size_of::<Vec<usize>>() as u128 + 2 * p * size_of::<usize>() as u128
        + retained_limb_bits.div_ceil(8)
        + 2 * rational_count * size_of::<u64>() as u128;
    let parser = source_parser_logical_temporary_bytes(
        e, p, coordinates, encoded_integer_bits, true,
    );
    Ok((
        usize::try_from(retained).map_err(|_| "ordinary cold retained size exceeds host width")?,
        usize::try_from(parser).map_err(|_| "ordinary cold parser size exceeds host width")?,
    ))
}


fn primary_source_construction_bytes(
    anatomy: &crate::joint_source_episode::NativeJointSourceEpisode,
    frames: u32,
    selected_sense: Option<u8>,
    encoded: usize,
) -> Result<usize, String> {
    use std::collections::{BTreeMap, BTreeSet};
    let mut ports = 0_u128;
    let mut coordinates = 0_u128;
    let mut integer_bits = 1075_u128;
    for port in anatomy.joint_source_ports().iter()
        .filter(|port| selected_sense.is_none_or(|sense| port.sense == sense))
    {
        ports += 1;
        coordinates += port.coordinates.len() as u128;
        let an = u128::from(port.field_offset.numer().bits());
        let ad = u128::from(port.field_offset.denom().bits());
        let bn = u128::from(port.field_scale.numer().bits());
        let bd = u128::from(port.field_scale.denom().bits());
        integer_bits = integer_bits.max((an + bd + 1075).max(bn + 53 + ad) + 1)
            .max(ad + bd + 1075);
        for value in [&port.source_min, &port.source_max,
            &port.field_offset, &port.field_scale]
        {
            integer_bits = integer_bits.max(u128::from(value.numer().bits()))
                .max(u128::from(value.denom().bits()));
        }
    }
    let n = u128::from(frames);
    // Caller clock pairs and signal bytes; builder selected indices, port
    // references, lookup pairs, projected groups and exact clock vector.
    let construction = n * size_of::<(i64, i64)>() as u128
        + ports * n * size_of::<f64>() as u128
        + 5 * ports * size_of::<usize>() as u128
        + ports * size_of::<Vec<usize>>() as u128
        + (n + 3) * (size_of::<BigRational>() as u128 + rational_limb_bytes(64, 64))
        + size_of::<BTreeMap<usize, usize>>() as u128
        + size_of::<BTreeSet<u8>>() as u128 + 6
        + 5 * size_of::<Vec<usize>>() as u128;
    usize::try_from(construction + source_parser_logical_temporary_bytes(
        encoded as u128, ports, coordinates, integer_bits, false,
    )).map_err(|_| "ordinary primary construction size exceeds host width".into())
}

/// A numerical capacity superset, never a source roster or retained profile.
/// Every real source remains owned by its existing producer. Construction
/// and UF processing are sequential, so SUM retained + MAX extra phase is
/// sufficient for source-owned logical content. Physical RSS is a separate
/// measured acceptance obligation; this is not an allocator guarantee.
pub(crate) fn ordinary_physical_workspace_bytes(
    anatomy: &crate::joint_source_episode::NativeJointSourceEpisode,
    primary_frames: u32,
    hearing_frames: u32,
    hearing_sense: u8,
    passive_frames: u32,
    coupled_encoded_limit: u32,
) -> Result<usize, String> {
    use crate::virtual_articulated_body::{
        BodyAxis, BodyProprioceptiveConsequence, BODY_AXIS_COUNT,
    };
    if primary_frames < 2 || hearing_frames < 2 || passive_frames < 2 {
        return Err("ordinary workspace requires the real temporal source bounds".into());
    }
    let axes = u32::try_from(BODY_AXIS_COUNT)
        .map_err(|_| "ordinary body anatomy exceeds codec width")?;
    let body_ports = 4 * axes;
    // Three old persisted sources: body impulse, root yaw, root translation.
    // Their bytes SHARE the coupled-world envelope, not three full envelopes.
    let cold_ports = body_ports + 2 + 4;
    let cold_occurrences = axes + 1 + 1;
    let (cold_retained, cold_parser) = cold_source_logical_layout(
        coupled_encoded_limit, cold_ports, 2 * cold_ports, cold_occurrences,
        2 * cold_occurrences, 3,
    )?;
    let cold_time_bits = coupled_encoded_limit.checked_mul(4)
        .ok_or("ordinary encoded clock width exceeds codec arithmetic")?;
    let mut retained = cold_retained as u128;
    let mut phase = (cold_parser as u128).max(uf_logical_working_bytes(
        cold_ports, 2 * cold_occurrences, cold_time_bits,
    )? as u128);

    // The cached anatomy is another immutable Arc held by the caller. Its
    // actual extents/bytes are metadata reads, not a scan of sample values.
    let anatomy_ports = u32::try_from(anatomy.joint_source_ports().len())
        .map_err(|_| "ordinary anatomy port count exceeds codec width")?;
    let anatomy_occurrences = anatomy.joint_source_occurrences();
    let anatomy_frames = anatomy_occurrences.iter().try_fold(0_u32, |sum, occurrence| {
        let count = u32::try_from(occurrence.source_times.len())
            .map_err(|_| "ordinary anatomy clock count exceeds codec width")?;
        sum.checked_add(count).ok_or("ordinary anatomy clock count overflows")
    })?;
    let anatomy_samples = anatomy.joint_source_ports().iter().try_fold(0_u32, |sum, port| {
        let count = u32::try_from(port.source_times.len())
            .map_err(|_| "ordinary anatomy sample count exceeds codec width")?;
        sum.checked_add(count).ok_or("ordinary anatomy sample count overflows")
    })?;
    retained += cold_source_logical_layout(
        u32::try_from(anatomy.joint_source_body().len())
            .map_err(|_| "ordinary anatomy payload exceeds codec width")?,
        anatomy_ports, anatomy_samples,
        u32::try_from(anatomy_occurrences.len())
            .map_err(|_| "ordinary anatomy occurrence count exceeds codec width")?,
        anatomy_frames, 1,
    )?.0 as u128;

    for (frames, sense, copies) in [
        (primary_frames, None, 1_u128),
        (hearing_frames, Some(hearing_sense), 2_u128),
    ] {
        let (encoded, held) = primary_source_logical_layout(anatomy, frames, sense)?;
        retained += copies * held as u128;
        phase = phase.max(primary_source_construction_bytes(anatomy, frames, sense, encoded)? as u128);
        let ports = u32::try_from(anatomy.joint_source_ports().iter()
            .filter(|port| sense.is_none_or(|value| port.sense == value)).count())
            .map_err(|_| "ordinary selected anatomy exceeds codec width")?;
        phase = phase.max(uf_logical_working_bytes(ports, frames, 64)? as u128);
    }
    // Passive return, current native guide, and first-use body observation.
    // The old impulse was already counted in the cold-source aggregate.
    for (endings, frames) in [(4_u32, passive_frames), (4, 2), (2, 2)] {
        let (encoded, held) = body_source_logical_layout(endings, frames)?;
        retained += held as u128;
        let p = u128::from(endings * axes);
        let n = u128::from(frames);
        let metadata = crate::articulated_body_joint_source_builder::articulated_source_metadata_bytes()
            as u128;
        // Compact bytes and their parsed axes/positions can coexist. Include
        // the builder's port headers, times and fixed consequence temporary.
        let compact = 21 + u128::from(axes) + 4 * u128::from(axes) * n;
        let construction = 2 * compact + metadata
            + u128::from(axes) * size_of::<BodyAxis>() as u128
            + u128::from(axes) * size_of::<BodyProprioceptiveConsequence>() as u128
            + p * size_of::<Vec<u8>>() as u128
            + (n + 4) * (size_of::<BigRational>() as u128 + rational_limb_bytes(128, 128));
        phase = phase.max(construction + source_parser_logical_temporary_bytes(
            encoded as u128, p, p, 128, true,
        ));
        // The four ports of ONE axis form each occurrence, not all axes.
        phase = phase.max(uf_logical_working_bytes(endings, frames, 64)? as u128);
    }
    let (encoded, held) = vestibular_source_logical_layout()?;
    retained += held as u128;
    // Source producer retains the encoded evidence and its exact validation
    // intermediates while the borrowed decoder runs.
    let vestibular_construction = encoded as u128
        + 16 * (size_of::<BigRational>() as u128 + rational_limb_bytes(256, 256))
        + 2 * size_of::<f64>() as u128;
    phase = phase.max(vestibular_construction + source_parser_logical_temporary_bytes(
        encoded as u128, 1, 1, 1075, true,
    ));
    phase = phase.max(uf_logical_working_bytes(1, 2, 64)? as u128);
    usize::try_from(retained + phase)
        .map_err(|_| "ordinary physical workspace exceeds host width".into())
}
