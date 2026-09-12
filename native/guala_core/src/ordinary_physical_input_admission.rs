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
