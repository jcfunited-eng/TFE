//! Anatomy and physical continuation fixtures, not mature migration or cognition.
use super::*;
use crate::passive_body_source::{PassiveBodySourceError, PassiveBodyTrajectory};

fn neutral_known() -> [i32; 8] {
    [0, 0, 0, 0, 0, 0, 10_000, 10_000]
}

#[test]
fn explicit_commission_preserves_all_eight_positions_and_declares_new_material() {
    let v8 = ArticulatedBodyState::at_neutral();
    assert_eq!(&v8.encode().unwrap()[..10], b"GLBODY01\0\x08");
    assert_eq!(v8.anatomy(BodyAxis::NeckPitch).minimum, -35_000);
    assert_eq!(v8.anatomy(BodyAxis::NeckPitch).maximum, 45_000);
    for upper in [false, true] {
        let mut known = neutral_known();
        for (position, axis) in known.iter_mut().zip(&BODY_AXES[2..10]) {
            let anatomy = BodyAnatomyProfile::V9.anatomy(*axis);
            *position = if upper { anatomy.maximum } else { anatomy.minimum };
        }
        let body = ArticulatedBodyState::commission_v9(known).unwrap();
        assert_eq!(&body.axes()[2..10], &known);
        assert_eq!(body.profile(), BodyAnatomyProfile::V9);
        for axis in BODY_AXES {
            if !(2..10).contains(&axis.index()) {
                assert_eq!(body.axis(axis), v8.axis(axis));
            }
            assert_eq!(body.anatomy(axis).neutral, v8.anatomy(axis).neutral);
            for direction in [BodyEffectorDirection::TowardMinimum, BodyEffectorDirection::TowardMaximum] {
                assert_eq!(body.antagonist_activation(BodyEffectorTerminal::new(axis, direction)), 0);
            }
        }
        assert_eq!(body.lung_air_microlitres(), NEUTRAL_LUNG_AIR_MICROLITRES);
        assert!(!body.proprioception_initialized());
        assert_eq!(body.articulatory_acoustic_state(), ArticulatoryAcousticState::at_rest());
        let bytes = body.encode().unwrap();
        assert_eq!(bytes.len(), 680);
        assert_eq!(&bytes[..10], b"GLBODY01\0\x09");
        assert_eq!(ArticulatedBodyState::decode(&bytes).unwrap(), body);
        for index in 0..8 {
            let mut outside = known;
            outside[index] += if upper { 1 } else { -1 };
            assert_eq!(ArticulatedBodyState::commission_v9(outside),
                       Err(ArticulatedBodyError::AxisOutsideAnatomy(BODY_AXES[index + 2])));
        }
    }
}

#[test]
fn profiles_preserve_existing_settlement_and_keep_distinct_real_capacities() {
    let v8 = ArticulatedBodyState::at_neutral();
    let v9 = ArticulatedBodyState::commission_v9(neutral_known()).unwrap();
    let terminal = BodyEffectorTerminal::new(BodyAxis::NeckPitch, BodyEffectorDirection::TowardMaximum);
    let small = AdmittedBodyEffectorDrives::admit(vec![BodyEffectorDrive {
        terminal, outward_elementary_carriers: 2_048,
    }]).unwrap();
    let mut old = settle_body_effector_drives(&v8, &small, 64_000).unwrap().successor;
    let mut new = settle_body_effector_drives(&v9, &small, 64_000).unwrap().successor;
    assert_eq!(&old.encode().unwrap()[10..], &new.encode().unwrap()[10..]);
    old = settle_body_effector_drives(&old, &AdmittedBodyEffectorDrives::quiescent(), 186_000).unwrap().successor;
    new = settle_body_effector_drives(&new, &AdmittedBodyEffectorDrives::quiescent(), 186_000).unwrap().successor;
    assert_eq!(&old.encode().unwrap()[10..], &new.encode().unwrap()[10..]);
    let full = AdmittedBodyEffectorDrives::admit(vec![BodyEffectorDrive {
        terminal, outward_elementary_carriers: 70_000,
    }]).unwrap();
    let old = settle_body_effector_drives(&v8, &full, 1_000).unwrap();
    let new = settle_body_effector_drives(&v9, &full, 1_000).unwrap();
    assert_eq!(old.successor.axis(BodyAxis::NeckPitch), 1_407);
    assert_eq!(new.successor.axis(BodyAxis::NeckPitch), 2_188);
    assert_eq!(old.successor.antagonist_activation(terminal), 45_000 * 31);
    assert_eq!(new.successor.antagonist_activation(terminal), 70_000 * 31);
    assert_eq!(old.proprioceptive_consequences[0].stalled_carriers, 25_000);
    assert_eq!(new.proprioceptive_consequences[0].stalled_carriers, 0);
    assert_eq!(&old.successor.encode().unwrap()[..10], b"GLBODY01\0\x08");
    assert_eq!(&new.successor.encode().unwrap()[..10], b"GLBODY01\0\x09");
}

#[test]
fn v8_cannot_decode_v9_position_or_activation_capacity() {
    let mut known = neutral_known();
    known[1] = 70_000;
    let mut encoded = ArticulatedBodyState::commission_v9(known).unwrap().encode().unwrap();
    encoded[9] = 8;
    assert_eq!(ArticulatedBodyState::decode(&encoded),
               Err(ArticulatedBodyError::AxisOutsideAnatomy(BodyAxis::NeckPitch)));
    let terminal = BodyEffectorTerminal::new(BodyAxis::LeftEyePitch, BodyEffectorDirection::TowardMinimum);
    let mut body = ArticulatedBodyState::commission_v9(neutral_known()).unwrap();
    body.antagonist_activation[terminal.ordinal()] = 45_000 * 32;
    let mut encoded = body.encode().unwrap();
    assert_eq!(ArticulatedBodyState::decode(&encoded).unwrap(), body);
    encoded[9] = 8;
    assert_eq!(ArticulatedBodyState::decode(&encoded),
               Err(ArticulatedBodyError::ActivationOutsideAnatomy(terminal)));
    body.antagonist_activation[terminal.ordinal()] += 1;
    assert_eq!(body.encode(), Err(ArticulatedBodyError::ActivationOutsideAnatomy(terminal)));
}

#[test]
fn passive_profile_is_explicit_cold_exact_and_never_inferred_from_position() {
    for version in [8, 9] {
        let mut body = if version == 8 {
            ArticulatedBodyState::at_neutral()
        } else {
            ArticulatedBodyState::commission_v9(neutral_known()).unwrap()
        };
        body.axes[BodyAxis::NeckPitch.index()] = body.anatomy(BodyAxis::NeckPitch).maximum;
        let mut capture = PassiveBodyTrajectory::begin(&body, 2, 1_024).unwrap().unwrap();
        let next = settle_body_effector_drives(&body, &AdmittedBodyEffectorDrives::quiescent(), 1_000).unwrap();
        capture.append_quiescent(&next).unwrap();
        let encoded = capture.clone().into_compact(17, 1_024).unwrap();
        let mut expected = if version == 8 { b"GLBPTR01".to_vec() } else { b"GLBPTR02".to_vec() };
        expected.extend_from_slice(&17_u64.to_le_bytes());
        expected.extend_from_slice(&2_u32.to_le_bytes());
        expected.extend_from_slice(&[1, BodyAxis::NeckPitch as u8]);
        expected.extend_from_slice(&body.axis(BodyAxis::NeckPitch).to_le_bytes());
        expected.extend_from_slice(&next.successor.axis(BodyAxis::NeckPitch).to_le_bytes());
        assert_eq!(encoded, expected);
        let (tick, restored) = PassiveBodyTrajectory::from_compact(&encoded, 2, 1_024).unwrap();
        assert_eq!(tick, 17);
        assert_eq!(restored, capture);
        assert_eq!(restored.into_compact(tick, 1_024).unwrap(), encoded);
        if version == 9 {
            let mut falsely_v8 = encoded;
            falsely_v8[7] = b'1';
            assert_eq!(PassiveBodyTrajectory::from_compact(&falsely_v8, 2, 1_024),
                       Err(PassiveBodySourceError::InvalidPosition));
        }
    }
    let mut known = neutral_known();
    known[1] = 70_000;
    let body = ArticulatedBodyState::commission_v9(known).unwrap();
    let mut capture = PassiveBodyTrajectory::begin(&body, 2, 1_024).unwrap().unwrap();
    let before = capture.clone();
    let other = settle_body_effector_drives(&ArticulatedBodyState::at_neutral(),
        &AdmittedBodyEffectorDrives::quiescent(), 1_000).unwrap();
    assert_eq!(capture.append_quiescent(&other), Err(PassiveBodySourceError::InvalidProfile));
    assert_eq!(capture, before);
}
