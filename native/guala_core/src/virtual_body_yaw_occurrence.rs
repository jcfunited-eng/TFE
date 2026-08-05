//! Exact cyclic yaw occurrence derived from virtual-body geometry.
//!
//! The body's admitted heading is an integer number of millidegrees in one
//! complete turn. Its turn position is therefore the exact reduced ratio of
//! that heading to 360,000 millidegrees. This is a geometric body occurrence;
//! it is not vestibular tissue deformation, receptor-channel state, neuronal
//! phase, Krimelack, DSF, recognition, or cognition.

use crate::exact_rational::{ExactRational, ExactRationalError};
use crate::virtual_body_yaw_motion::YawBodyState;

const MILLIDEGREES_PER_COMPLETE_TURN: u128 = 360_000;

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) struct ExactYawTurnPosition {
    turns: ExactRational,
}

impl ExactYawTurnPosition {
    pub(crate) fn from_body_state(state: YawBodyState) -> Result<Self, ExactRationalError> {
        Ok(Self {
            turns: ExactRational::from_ratio(
                i128::from(state.heading_millidegrees()),
                MILLIDEGREES_PER_COMPLETE_TURN,
            )?,
        })
    }

    pub(crate) fn exact_turns(self) -> ExactRational {
        self.turns
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::virtual_body_yaw_motion::{
        decode_yaw_body_state, encode_yaw_body_state, settle_signed_yaw_actuation,
        SignedYawActuation,
    };

    #[test]
    fn cardinal_headings_are_exact_geometric_turn_positions() {
        let cases = [
            (0, (0, 1)),
            (90_000, (1, 4)),
            (180_000, (1, 2)),
            (270_000, (3, 4)),
        ];
        for (heading, expected) in cases {
            let position =
                ExactYawTurnPosition::from_body_state(YawBodyState::new(heading).unwrap()).unwrap();
            assert_eq!(position.exact_turns().parts(), expected);
        }
    }

    #[test]
    fn wrap_and_restart_preserve_the_same_exact_occurrence() {
        let transition = settle_signed_yaw_actuation(
            YawBodyState::new(350_000).unwrap(),
            SignedYawActuation::new(20_000, 200_000).unwrap(),
        )
        .unwrap();
        let encoded = encode_yaw_body_state(transition.successor);
        let restored = decode_yaw_body_state(&encoded).unwrap();
        let live = ExactYawTurnPosition::from_body_state(transition.successor).unwrap();
        let restarted = ExactYawTurnPosition::from_body_state(restored).unwrap();
        assert_eq!(live, restarted);
        assert_eq!(live.exact_turns().parts(), (1, 36));
    }

    #[test]
    fn arbitrary_heading_is_reduced_without_rounding() {
        let position =
            ExactYawTurnPosition::from_body_state(YawBodyState::new(123_456).unwrap()).unwrap();
        assert_eq!(position.exact_turns().parts(), (643, 1_875));
    }
}
