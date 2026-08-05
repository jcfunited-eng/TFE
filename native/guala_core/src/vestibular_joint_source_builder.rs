//! Typed same-cause admission of one reached vestibular mechanical interval.
//!
//! This boundary performs no body, canal, bundle, UF, neuronal, or cognitive
//! transition. It verifies one already-reached one-millisecond body/canal
//! successor, derives both endpoint bundle coordinates from mounted anatomy,
//! and carries that exact unit-bearing evidence into one isolated GLJSRC02
//! occurrence. Missing or inconsistent physical evidence is unavailable; no
//! default relevance, normalization table, owner, lock, database, or semantic
//! meaning participates.

use num_bigint::BigInt;
use num_rational::BigRational;
use num_traits::{One, Signed, ToPrimitive, Zero};

use crate::joint_source_episode::{decode_native_joint_source_episode, NativeJointSourceEpisode};
use crate::joint_uf_source_adapter::{
    JointUfSourceAdmission, JointUfSourceError,
    SAMPLED_VOLUME_AND_RELEVANCE_PIECEWISE_LINEAR_PROFILE,
};
use crate::local_cupula_hair_bundle_geometry::LocalCupulaBundleAnatomy;
use crate::reached_vestibular_bundle_path::ReachedVestibularBundleTick;
use crate::sha256::sha256;
use crate::virtual_body_yaw_motion::YawBodyState;
use crate::virtual_vestibular_canal::{
    decode_canal_state, encode_canal_state, CanalAnatomy, CanalState,
    VELOCITY_STATE_UNITS_PER_DEGREE_PER_SECOND, WORLD_MAX_ACTION_TICKS,
    WORLD_MECHANICAL_TICK_MICROSECONDS,
};

const GLJSRC02_VERSION: u16 = 2;
const MICROSECONDS_PER_SECOND: u64 = 1_000_000;
const WORLD_MECHANICAL_TICKS_PER_SECOND: u64 =
    MICROSECONDS_PER_SECOND / WORLD_MECHANICAL_TICK_MICROSECONDS as u64;
const MILLIDEGREES_PER_TURN: i64 = 360_000;
const EVIDENCE_PROFILE: &[u8; 8] = b"GLVSEV02";
const PORT_RELEVANCE_PROFILE: &str = "guala.vestibular.whole_source_present.r(t)=1.exact.v1";
const JOINT_RELEVANCE_PROFILE: &[u8] =
    b"guala.vestibular.whole_source_present_joint.r(t)=1.exact.v1";
const CYCLIC_BODY_YAW_SOURCE_PHASE_PROFILE: &[u8] =
    b"guala.vestibular.cyclic_body_yaw_source_phase.turns.v1";
const INPUT_MAP_ID: &str = "vestibular-tip-displacement-bundle-height-invertible-v2";
const PHYSICAL_QUANTITY: &str = "local-hair-bundle-tip-displacement";
const PHYSICAL_UNIT: &str = "nanometre";

#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) enum VestibularJointSourceError {
    SourceTickOverflow,
    BodySuccessorMismatch,
    CanalSuccessorMismatch,
    ArithmeticWidth,
    NonFiniteCoordinate,
    Carrier(String),
}

/// No value exists for the isolated one-receptor occurrence. The zero-length
/// array below is therefore an explicit sparse physical contact set, not an
/// omitted or inferred topology.
pub(crate) enum VestibularSparsePhysicalContact {}

pub(crate) struct VestibularJointSourceAdmission {
    episode: NativeJointSourceEpisode,
    source_start: BigRational,
    source_end: BigRational,
    predecessor_tip_displacement_nanometres: BigRational,
    successor_tip_displacement_nanometres: BigRational,
    mounted_bundle_height_nanometres: BigRational,
    reached_tick: ReachedVestibularBundleTick,
    mechanical_evidence_receipt: [u8; 32],
    sparse_contacts: [VestibularSparsePhysicalContact; 0],
}

impl VestibularJointSourceAdmission {
    pub(crate) fn joint_source_with_contacts(
        &self,
    ) -> (
        &NativeJointSourceEpisode,
        &[VestibularSparsePhysicalContact],
    ) {
        (&self.episode, &self.sparse_contacts)
    }

    pub(crate) fn source_interval(&self) -> (&BigRational, &BigRational) {
        (&self.source_start, &self.source_end)
    }

    pub(crate) fn tip_displacements_nanometres(&self) -> (&BigRational, &BigRational) {
        (
            &self.predecessor_tip_displacement_nanometres,
            &self.successor_tip_displacement_nanometres,
        )
    }

    pub(crate) fn mounted_bundle_height_nanometres(&self) -> &BigRational {
        &self.mounted_bundle_height_nanometres
    }

    pub(crate) fn mechanical_canal_transition(&self) -> (CanalState, &ReachedVestibularBundleTick) {
        (self.reached_tick.predecessor_canal, &self.reached_tick)
    }

    pub(crate) fn mechanical_evidence_receipt(&self) -> [u8; 32] {
        self.mechanical_evidence_receipt
    }

    pub(crate) fn sparse_contact_count(&self) -> usize {
        self.sparse_contacts.len()
    }

    /// The vestibular action domain admits at most the world's fixed maximum
    /// number of one-millisecond mechanical ticks. This is environment
    /// authority established before UF evaluation, not an interval inferred
    /// from the observed two-frame occurrence.
    pub(crate) fn joint_uf_source_admission(
        &self,
    ) -> Result<JointUfSourceAdmission, JointUfSourceError> {
        let maximum_microseconds = u64::try_from(WORLD_MAX_ACTION_TICKS)
            .ok()
            .and_then(|ticks| ticks.checked_mul(u64::from(WORLD_MECHANICAL_TICK_MICROSECONDS)))
            .ok_or(JointUfSourceError::Unavailable(
                "vestibular maximum causal interval exceeds exact time width",
            ))?;
        JointUfSourceAdmission::new(BigRational::new(
            BigInt::from(maximum_microseconds),
            BigInt::from(MICROSECONDS_PER_SECOND),
        ))
    }
}

#[allow(clippy::too_many_arguments)]
pub(crate) fn admit_same_cause_vestibular_joint_source_interval(
    source_tick: u64,
    predecessor_body: YawBodyState,
    successor_body: YawBodyState,
    reached_tick: ReachedVestibularBundleTick,
) -> Result<VestibularJointSourceAdmission, VestibularJointSourceError> {
    let source_end_tick = source_tick
        .checked_add(1)
        .ok_or(VestibularJointSourceError::SourceTickOverflow)?;
    let signed_body_motion_millidegrees = reached_tick.signed_body_motion_millidegrees;
    let predecessor_canal = reached_tick.predecessor_canal;
    let canal_anatomy = reached_tick.canal_anatomy;
    let bundle_anatomy = reached_tick.bundle_anatomy;
    let unwrapped_successor_heading = i64::from(predecessor_body.heading_millidegrees())
        .checked_add(i64::from(signed_body_motion_millidegrees))
        .ok_or(VestibularJointSourceError::ArithmeticWidth)?;
    let expected_successor_heading = unwrapped_successor_heading.rem_euclid(MILLIDEGREES_PER_TURN);
    if i64::from(successor_body.heading_millidegrees()) != expected_successor_heading {
        return Err(VestibularJointSourceError::BodySuccessorMismatch);
    }

    admit_canal_state(predecessor_canal, canal_anatomy)?;
    admit_canal_state(reached_tick.successor_canal, canal_anatomy)?;
    if reached_tick.interval_microseconds != WORLD_MECHANICAL_TICK_MICROSECONDS
        || reached_tick.resident_canal_bytes != CanalState::resident_bytes()
        || reached_tick.resident_canal_anatomy_bytes != std::mem::size_of::<CanalAnatomy>()
        || reached_tick.resident_bundle_anatomy_bytes != LocalCupulaBundleAnatomy::resident_bytes()
        || reached_tick.local_bundle.anatomy_bytes != LocalCupulaBundleAnatomy::resident_bytes()
    {
        return Err(VestibularJointSourceError::CanalSuccessorMismatch);
    }

    let predecessor_tip = tip_displacement(predecessor_canal, canal_anatomy, bundle_anatomy)?;
    let successor_tip =
        tip_displacement(reached_tick.successor_canal, canal_anatomy, bundle_anatomy)?;
    let reached_central =
        exact_signed_to_big_rational(reached_tick.central_cupula_displacement_nanometres.parts())?;
    let expected_central =
        central_cupula_displacement(reached_tick.successor_canal, canal_anatomy)?;
    let reached_successor_tip = exact_to_big_rational(
        reached_tick
            .local_bundle
            .signed_tip_displacement_nanometres
            .parts(),
    );
    let reached_successor_slope =
        exact_to_big_rational(reached_tick.local_bundle.signed_bundle_slope.parts());
    let expected_successor_slope = &successor_tip
        / BigRational::from_integer(BigInt::from(bundle_anatomy.bundle_height_nanometres()));
    if reached_central != expected_central
        || successor_tip != reached_successor_tip
        || reached_successor_slope != expected_successor_slope
    {
        return Err(VestibularJointSourceError::CanalSuccessorMismatch);
    }
    let bundle_height =
        BigRational::from_integer(BigInt::from(bundle_anatomy.bundle_height_nanometres()));

    let normalized = [
        rational_to_binary64(&invertible_tip_coordinate(
            &predecessor_tip,
            &bundle_height,
        )?)?,
        rational_to_binary64(&invertible_tip_coordinate(&successor_tip, &bundle_height)?)?,
    ];
    if normalized.iter().any(|value| !(-1.0..=1.0).contains(value)) {
        return Err(VestibularJointSourceError::NonFiniteCoordinate);
    }

    let source_start = BigRational::new(
        BigInt::from(source_tick),
        BigInt::from(WORLD_MECHANICAL_TICKS_PER_SECOND),
    );
    let source_end = BigRational::new(
        BigInt::from(source_end_tick),
        BigInt::from(WORLD_MECHANICAL_TICKS_PER_SECOND),
    );
    let cyclic_body_yaw_source_phases = [
        BigRational::new(
            BigInt::from(predecessor_body.heading_millidegrees()),
            BigInt::from(MILLIDEGREES_PER_TURN),
        ),
        BigRational::new(
            BigInt::from(unwrapped_successor_heading),
            BigInt::from(MILLIDEGREES_PER_TURN),
        ),
    ];
    let times = [source_start.clone(), source_end.clone()];
    let evidence_profile = mechanical_evidence_profile(
        &times,
        predecessor_body,
        successor_body,
        predecessor_canal,
        reached_tick.successor_canal,
        signed_body_motion_millidegrees,
        canal_anatomy,
        bundle_anatomy,
        [&predecessor_tip, &successor_tip],
        &bundle_height,
    )?;
    let evidence_receipt = sha256(&evidence_profile);
    let payload = encode_episode(
        &times,
        &normalized,
        &cyclic_body_yaw_source_phases,
        &evidence_profile,
    )?;
    let episode = decode_native_joint_source_episode(&payload, 1, 2, 1, 2)
        .map_err(VestibularJointSourceError::Carrier)?;

    Ok(VestibularJointSourceAdmission {
        episode,
        source_start,
        source_end,
        predecessor_tip_displacement_nanometres: predecessor_tip,
        successor_tip_displacement_nanometres: successor_tip,
        mounted_bundle_height_nanometres: bundle_height,
        reached_tick,
        mechanical_evidence_receipt: evidence_receipt,
        sparse_contacts: [],
    })
}

fn admit_canal_state(
    state: CanalState,
    anatomy: CanalAnatomy,
) -> Result<(), VestibularJointSourceError> {
    let encoded = encode_canal_state(state);
    let decoded = decode_canal_state(anatomy, &encoded)
        .map_err(|_| VestibularJointSourceError::CanalSuccessorMismatch)?;
    if decoded != state {
        return Err(VestibularJointSourceError::CanalSuccessorMismatch);
    }
    Ok(())
}

fn central_cupula_displacement(
    canal: CanalState,
    canal_anatomy: CanalAnatomy,
) -> Result<BigRational, VestibularJointSourceError> {
    let relative = i128::from(canal.fast_millidegrees_per_second())
        .checked_sub(i128::from(canal.slow_millidegrees_per_second()))
        .ok_or(VestibularJointSourceError::ArithmeticWidth)?;
    let (gain_numerator, gain_denominator) = canal_anatomy.cupula_gain().parts();
    Ok(BigRational::new(
        BigInt::from(relative) * BigInt::from(gain_numerator),
        BigInt::from(VELOCITY_STATE_UNITS_PER_DEGREE_PER_SECOND) * BigInt::from(gain_denominator),
    ))
}

fn tip_displacement(
    canal: CanalState,
    canal_anatomy: CanalAnatomy,
    bundle_anatomy: LocalCupulaBundleAnatomy,
) -> Result<BigRational, VestibularJointSourceError> {
    let relative = i128::from(canal.fast_millidegrees_per_second())
        .checked_sub(i128::from(canal.slow_millidegrees_per_second()))
        .ok_or(VestibularJointSourceError::ArithmeticWidth)?;
    let (gain_numerator, gain_denominator) = canal_anatomy.cupula_gain().parts();
    let (transfer_numerator, transfer_denominator) = bundle_anatomy.local_transfer().parts();
    let numerator =
        BigInt::from(relative) * BigInt::from(gain_numerator) * BigInt::from(transfer_numerator);
    let denominator = BigInt::from(VELOCITY_STATE_UNITS_PER_DEGREE_PER_SECOND)
        * BigInt::from(gain_denominator)
        * BigInt::from(transfer_denominator);
    Ok(BigRational::new(numerator, denominator))
}

fn invertible_tip_coordinate(
    tip: &BigRational,
    bundle_height: &BigRational,
) -> Result<BigRational, VestibularJointSourceError> {
    if bundle_height <= &BigRational::zero() {
        return Err(VestibularJointSourceError::ArithmeticWidth);
    }
    Ok(tip / (bundle_height + tip.abs()))
}

fn exact_to_big_rational(parts: (i128, u128)) -> BigRational {
    BigRational::new(BigInt::from(parts.0), BigInt::from(parts.1))
}

fn exact_signed_to_big_rational(
    parts: (bool, u128, u64),
) -> Result<BigRational, VestibularJointSourceError> {
    let magnitude = BigInt::from(parts.1);
    let numerator = if parts.0 { -magnitude } else { magnitude };
    Ok(BigRational::new(numerator, BigInt::from(parts.2)))
}

fn rational_to_binary64(value: &BigRational) -> Result<f64, VestibularJointSourceError> {
    value
        .to_f64()
        .filter(|candidate| candidate.is_finite())
        .ok_or(VestibularJointSourceError::NonFiniteCoordinate)
}

#[allow(clippy::too_many_arguments)]
fn mechanical_evidence_profile(
    times: &[BigRational; 2],
    predecessor_body: YawBodyState,
    successor_body: YawBodyState,
    predecessor_canal: CanalState,
    successor_canal: CanalState,
    signed_body_motion_millidegrees: i32,
    canal_anatomy: CanalAnatomy,
    bundle_anatomy: LocalCupulaBundleAnatomy,
    tips: [&BigRational; 2],
    mounted_bundle_height: &BigRational,
) -> Result<Vec<u8>, VestibularJointSourceError> {
    let mut output = EVIDENCE_PROFILE.to_vec();
    for time in times {
        rational(&mut output, time)?;
    }
    output.extend_from_slice(&predecessor_body.heading_millidegrees().to_le_bytes());
    output.extend_from_slice(&successor_body.heading_millidegrees().to_le_bytes());
    output.extend_from_slice(&signed_body_motion_millidegrees.to_le_bytes());
    output.extend_from_slice(&encode_canal_state(predecessor_canal));
    output.extend_from_slice(&encode_canal_state(successor_canal));
    let (gain_numerator, gain_denominator) = canal_anatomy.cupula_gain().parts();
    output.extend_from_slice(&canal_anatomy.fast_time_constant_ticks().to_le_bytes());
    output.extend_from_slice(&canal_anatomy.slow_time_constant_ticks().to_le_bytes());
    output.extend_from_slice(&gain_numerator.to_le_bytes());
    output.extend_from_slice(&gain_denominator.to_le_bytes());
    let (transfer_numerator, transfer_denominator) = bundle_anatomy.local_transfer().parts();
    output.extend_from_slice(&transfer_numerator.to_le_bytes());
    output.extend_from_slice(&transfer_denominator.to_le_bytes());
    output.extend_from_slice(&bundle_anatomy.bundle_height_nanometres().to_le_bytes());
    for tip in tips {
        rational(&mut output, tip)?;
    }
    rational(&mut output, mounted_bundle_height)?;
    bytes(&mut output, CYCLIC_BODY_YAW_SOURCE_PHASE_PROFILE)?;
    text(&mut output, PORT_RELEVANCE_PROFILE)?;
    bytes(&mut output, JOINT_RELEVANCE_PROFILE)?;
    Ok(output)
}

fn encode_episode(
    times: &[BigRational; 2],
    normalized: &[f64; 2],
    cyclic_body_yaw_source_phases: &[BigRational; 2],
    evidence_profile: &[u8],
) -> Result<Vec<u8>, VestibularJointSourceError> {
    let mut output = b"GLJSRC02".to_vec();
    output.extend_from_slice(&GLJSRC02_VERSION.to_le_bytes());
    text(&mut output, "vestibular-same-cause-interval")?;
    output.extend_from_slice(&[1, 1, 1, 1, 1, 0]);
    u32_value(&mut output, 1);
    output.push(5);
    u32_value(&mut output, 0);
    text(&mut output, "mounted-yaw-canal")?;
    text(&mut output, "local-hair-bundle-0")?;
    output.extend_from_slice(&1_u16.to_le_bytes());
    text(&mut output, "body-yaw-canal")?;
    text(&mut output, "local-bundle-0")?;
    text(&mut output, PHYSICAL_QUANTITY)?;
    text(&mut output, PHYSICAL_UNIT)?;
    // The admitted whole physical source is present throughout this exact
    // interval, so the ratified port and joint relevance law is r(t)=1. This
    // does not derive relevance from displacement magnitude or a semantic
    // score. The phase coordinate below is cyclic body-yaw source phase in
    // turns; it is neither receptor phase nor Krimelack/Psi phase.
    text(&mut output, PORT_RELEVANCE_PROFILE)?;
    text(&mut output, "")?;
    text(&mut output, INPUT_MAP_ID)?;
    rational(&mut output, &-BigRational::one())?;
    rational(&mut output, &BigRational::one())?;
    rational(&mut output, &BigRational::zero())?;
    rational(&mut output, &BigRational::one())?;
    bytes(&mut output, evidence_profile)?;
    u32_value(&mut output, 2);
    for index in 0..2 {
        rational(&mut output, &times[index])?;
        output.extend_from_slice(&normalized[index].to_bits().to_le_bytes());
        rational(&mut output, &cyclic_body_yaw_source_phases[index])?;
        rational(&mut output, &BigRational::one())?;
        let exact_binary = BigRational::from_float(normalized[index])
            .ok_or(VestibularJointSourceError::NonFiniteCoordinate)?;
        rational(&mut output, &exact_binary)?;
    }
    u32_value(&mut output, 1);
    u32_value(&mut output, 1);
    u32_value(&mut output, 0);
    u32_value(&mut output, 2);
    for time in times {
        rational(&mut output, time)?;
    }
    bytes(
        &mut output,
        SAMPLED_VOLUME_AND_RELEVANCE_PIECEWISE_LINEAR_PROFILE,
    )?;
    u32_value(&mut output, 1);
    u32_value(&mut output, 1);
    u32_value(&mut output, 0);
    bytes(&mut output, JOINT_RELEVANCE_PROFILE)?;
    u32_value(&mut output, 2);
    rational(&mut output, &BigRational::one())?;
    rational(&mut output, &BigRational::one())?;
    Ok(output)
}

fn u32_value(output: &mut Vec<u8>, value: u32) {
    output.extend_from_slice(&value.to_le_bytes());
}

fn text(output: &mut Vec<u8>, value: &str) -> Result<(), VestibularJointSourceError> {
    let length =
        u16::try_from(value.len()).map_err(|_| VestibularJointSourceError::ArithmeticWidth)?;
    output.extend_from_slice(&length.to_le_bytes());
    output.extend_from_slice(value.as_bytes());
    Ok(())
}

fn bytes(output: &mut Vec<u8>, value: &[u8]) -> Result<(), VestibularJointSourceError> {
    if value.is_empty() {
        return Err(VestibularJointSourceError::ArithmeticWidth);
    }
    let length =
        u32::try_from(value.len()).map_err(|_| VestibularJointSourceError::ArithmeticWidth)?;
    u32_value(output, length);
    output.extend_from_slice(value);
    Ok(())
}

fn rational(output: &mut Vec<u8>, value: &BigRational) -> Result<(), VestibularJointSourceError> {
    text(output, &value.numer().to_string())?;
    text(output, &value.denom().to_string())
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::joint_uf_neuron_boundary::prepare_complete_joint_field_with_admission;
    use crate::local_cupula_hair_bundle_geometry::LocalCupulaBundleAnatomy;
    use crate::reached_vestibular_bundle_path::{
        settle_reached_vestibular_bundle_tick as externally_settle_tick,
        ReachedVestibularBundleTick,
    };
    use crate::virtual_body_yaw_motion::{settle_signed_yaw_actuation, SignedYawActuation};
    use crate::virtual_vestibular_canal::PositiveRatio;

    fn canal_anatomy() -> CanalAnatomy {
        CanalAnatomy::new(6, 13_200, PositiveRatio::new(25, 1).unwrap()).unwrap()
    }

    fn bundle_anatomy() -> LocalCupulaBundleAnatomy {
        LocalCupulaBundleAnatomy::new(2, 5, 20_000).unwrap()
    }

    fn settled_inputs(
        step: i32,
        predecessor_canal: CanalState,
    ) -> (YawBodyState, YawBodyState, ReachedVestibularBundleTick) {
        let predecessor_body = YawBodyState::new(359_999).unwrap();
        let body = settle_signed_yaw_actuation(
            predecessor_body,
            SignedYawActuation::new(step, WORLD_MECHANICAL_TICK_MICROSECONDS).unwrap(),
        )
        .unwrap();
        let reached = externally_settle_tick(
            canal_anatomy(),
            predecessor_canal,
            body.trajectory.as_slice()[0],
            bundle_anatomy(),
        )
        .unwrap();
        (predecessor_body, body.successor, reached)
    }

    fn admission(step: i32) -> VestibularJointSourceAdmission {
        let predecessor_canal = CanalState::at_rest();
        let (predecessor_body, successor_body, reached) = settled_inputs(step, predecessor_canal);
        admit_same_cause_vestibular_joint_source_interval(
            700,
            predecessor_body,
            successor_body,
            reached,
        )
        .unwrap()
    }

    #[test]
    fn one_externally_settled_tick_becomes_one_two_frame_body_occurrence() {
        let admission = admission(1);
        let (episode, contacts) = admission.joint_source_with_contacts();
        assert_eq!(episode.joint_source_ports().len(), 1);
        assert_eq!(episode.joint_source_occurrences().len(), 1);
        let port = &episode.joint_source_ports()[0];
        assert_eq!(port.sense, 5);
        assert_eq!(port.physical_quantity, PHYSICAL_QUANTITY);
        assert_eq!(port.physical_unit, PHYSICAL_UNIT);
        assert_eq!(port.relevance_rule, PORT_RELEVANCE_PROFILE);
        assert_eq!(port.input_map_id, INPUT_MAP_ID);
        assert_eq!(port.source_times.len(), 2);
        assert_eq!(port.source_relevances, vec![BigRational::one(); 2]);
        assert!(port.input_map_profile.starts_with(EVIDENCE_PROFILE));
        assert_eq!(
            sha256(&port.input_map_profile),
            admission.mechanical_evidence_receipt()
        );
        let occurrence = &episode.joint_source_occurrences()[0];
        assert_eq!(occurrence.joint_relevances, vec![BigRational::one(); 2]);
        assert_eq!(occurrence.joint_relevance_profile, JOINT_RELEVANCE_PROFILE);
        assert_eq!(
            occurrence.joint_intersample_profile,
            SAMPLED_VOLUME_AND_RELEVANCE_PIECEWISE_LINEAR_PROFILE
        );
        assert_eq!(admission.sparse_contact_count(), 0);
        assert!(contacts.is_empty());
        assert_ne!(
            admission.tip_displacements_nanometres().0,
            admission.tip_displacements_nanometres().1
        );
        let (start, end) = admission.source_interval();
        assert_eq!(
            end - start,
            BigRational::new(BigInt::one(), BigInt::from(1_000))
        );
        assert_eq!(start, &BigRational::new(BigInt::from(7), BigInt::from(10)));
        assert_eq!(
            port.reported_phase_turns,
            vec![
                BigRational::new(BigInt::from(359_999), BigInt::from(360_000)),
                BigRational::one(),
            ]
        );
        let (predecessor_canal, reached) = admission.mechanical_canal_transition();
        assert_eq!(predecessor_canal, CanalState::at_rest());
        assert_eq!(reached.signed_body_motion_millidegrees, 1);
        let uf_admission = admission.joint_uf_source_admission().unwrap();
        let shared =
            prepare_complete_joint_field_with_admission(episode, 0, &uf_admission).unwrap();
        assert_eq!(shared.vertex_count(), 1);
    }

    #[test]
    fn bundle_height_coordinate_is_exactly_invertible_and_preserves_sign() {
        let positive = admission(1);
        let negative = admission(-1);
        let positive_port = &positive.joint_source_with_contacts().0.joint_source_ports()[0];
        let negative_port = &negative.joint_source_with_contacts().0.joint_source_ports()[0];
        assert_eq!(positive_port.dimensionless_fields[0], BigRational::zero());
        assert_eq!(negative_port.dimensionless_fields[0], BigRational::zero());
        assert_eq!(
            positive_port.dimensionless_fields[1],
            -negative_port.dimensionless_fields[1].clone()
        );
        let height = positive.mounted_bundle_height_nanometres();
        let positive_tip = positive.tip_displacements_nanometres().1;
        let exact_coordinate = invertible_tip_coordinate(positive_tip, height).unwrap();
        let recovered_tip =
            height * &exact_coordinate / (BigRational::one() - exact_coordinate.abs());
        assert_eq!(&recovered_tip, positive_tip);
        assert_eq!(
            positive.mounted_bundle_height_nanometres(),
            negative.mounted_bundle_height_nanometres()
        );
        assert_eq!(height, &BigRational::from_integer(BigInt::from(20_000)));
    }

    #[test]
    fn body_canal_tick_and_anatomy_mismatches_are_refused() {
        let anatomy = canal_anatomy();
        let bundle = bundle_anatomy();
        let rest_body = YawBodyState::new(0).unwrap();
        let wrong_body = YawBodyState::new(2).unwrap();
        let rest_canal = CanalState::at_rest();
        let reached = externally_settle_tick(anatomy, rest_canal, 1, bundle).unwrap();
        assert_eq!(
            admit_same_cause_vestibular_joint_source_interval(0, rest_body, wrong_body, reached)
                .err()
                .unwrap(),
            VestibularJointSourceError::BodySuccessorMismatch
        );

        let mut wrong_interval = reached;
        wrong_interval.interval_microseconds = 2 * WORLD_MECHANICAL_TICK_MICROSECONDS;
        assert_eq!(
            admit_same_cause_vestibular_joint_source_interval(
                0,
                rest_body,
                YawBodyState::new(1).unwrap(),
                wrong_interval,
            )
            .err()
            .unwrap(),
            VestibularJointSourceError::CanalSuccessorMismatch
        );

        let mut wrong_canal = reached;
        wrong_canal.successor_canal = CanalState::at_rest();
        assert_eq!(
            admit_same_cause_vestibular_joint_source_interval(
                0,
                rest_body,
                YawBodyState::new(1).unwrap(),
                wrong_canal,
            )
            .err()
            .unwrap(),
            VestibularJointSourceError::CanalSuccessorMismatch
        );

        let mismatched_bundle = LocalCupulaBundleAnatomy::new(3, 5, 20_000).unwrap();
        let mut wrong_bundle_anatomy = reached;
        wrong_bundle_anatomy.bundle_anatomy = mismatched_bundle;
        assert_eq!(
            admit_same_cause_vestibular_joint_source_interval(
                0,
                rest_body,
                YawBodyState::new(1).unwrap(),
                wrong_bundle_anatomy,
            )
            .err()
            .unwrap(),
            VestibularJointSourceError::CanalSuccessorMismatch
        );

        let mut wrong_canal_anatomy = reached;
        wrong_canal_anatomy.canal_anatomy =
            CanalAnatomy::new(6, 13_200, PositiveRatio::new(26, 1).unwrap()).unwrap();
        assert_eq!(
            admit_same_cause_vestibular_joint_source_interval(
                0,
                rest_body,
                YawBodyState::new(1).unwrap(),
                wrong_canal_anatomy,
            )
            .err()
            .unwrap(),
            VestibularJointSourceError::CanalSuccessorMismatch
        );
        assert_eq!(
            admit_same_cause_vestibular_joint_source_interval(
                u64::MAX,
                rest_body,
                YawBodyState::new(1).unwrap(),
                reached,
            )
            .err()
            .unwrap(),
            VestibularJointSourceError::SourceTickOverflow
        );
    }

    #[test]
    fn evidence_receipt_covers_canal_remainders_not_only_velocity() {
        let anatomy = canal_anatomy();
        let bundle = bundle_anatomy();
        let predecessor_body = YawBodyState::new(0).unwrap();
        let successor_body = YawBodyState::new(1).unwrap();
        let predecessor_canal = CanalState::at_rest();
        let reached = externally_settle_tick(anatomy, predecessor_canal, 1, bundle).unwrap();
        let mut alternate_bytes = encode_canal_state(reached.successor_canal);
        let original_fast_remainder =
            i64::from_le_bytes(alternate_bytes[8..16].try_into().unwrap());
        alternate_bytes[8..16].copy_from_slice(&(original_fast_remainder - 1).to_le_bytes());
        let alternate_successor = decode_canal_state(anatomy, &alternate_bytes).unwrap();
        assert_eq!(
            reached.successor_canal.fast_millidegrees_per_second(),
            alternate_successor.fast_millidegrees_per_second()
        );
        assert_eq!(
            reached.successor_canal.slow_millidegrees_per_second(),
            alternate_successor.slow_millidegrees_per_second()
        );
        assert_ne!(
            encode_canal_state(reached.successor_canal),
            encode_canal_state(alternate_successor)
        );
        let times = [
            BigRational::zero(),
            BigRational::new(BigInt::one(), BigInt::from(1_000)),
        ];
        let predecessor_tip = tip_displacement(predecessor_canal, anatomy, bundle).unwrap();
        let successor_tip = tip_displacement(reached.successor_canal, anatomy, bundle).unwrap();
        let height = BigRational::from_integer(BigInt::from(bundle.bundle_height_nanometres()));
        let original = mechanical_evidence_profile(
            &times,
            predecessor_body,
            successor_body,
            predecessor_canal,
            reached.successor_canal,
            1,
            anatomy,
            bundle,
            [&predecessor_tip, &successor_tip],
            &height,
        )
        .unwrap();
        let alternate = mechanical_evidence_profile(
            &times,
            predecessor_body,
            successor_body,
            predecessor_canal,
            alternate_successor,
            1,
            anatomy,
            bundle,
            [&predecessor_tip, &successor_tip],
            &height,
        )
        .unwrap();
        assert_ne!(sha256(&original), sha256(&alternate));
    }

    #[test]
    fn builder_source_contains_no_second_mechanical_settlement_call() {
        let source = include_str!("vestibular_joint_source_builder.rs");
        let forbidden_call = ["settle_reached_vestibular_", "bundle_tick("].concat();
        assert!(!source.contains(&forbidden_call));
    }
}
