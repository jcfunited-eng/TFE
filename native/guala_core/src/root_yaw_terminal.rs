//! Fixed directional terminals for the embodied world's root-yaw joint.
//!
//! Terminal identity is separate from yaw-trajectory settlement so the latter
//! remains a domain-local mechanical primitive with no articulated-body
//! dependency.

use crate::virtual_articulated_body::{
    BODY_EFFECTOR_LOAD_TOPOLOGY_OFFSET, BODY_EFFECTOR_TERMINAL_COUNT,
};

/// Root-yaw directional endings occupy their own body territory after the
/// articulated position and load endings. They can therefore never alias a
/// local joint receptor merely because both are body sense.
pub(crate) const ROOT_YAW_PROPRIOCEPTOR_TOPOLOGY_OFFSET: usize =
    BODY_EFFECTOR_LOAD_TOPOLOGY_OFFSET + BODY_EFFECTOR_TERMINAL_COUNT;

/// The two fixed antagonist directions of the world's root-yaw actuator.
/// These are physical terminal identities, not action labels or a choice
/// policy. The world remains the sole owner of the resulting heading.
#[derive(Clone, Copy, Debug, Eq, Ord, PartialEq, PartialOrd)]
#[repr(u8)]
pub(crate) enum RootYawDirection {
    Negative = 0,
    Positive = 1,
}

#[derive(Clone, Copy, Debug, Eq, Ord, PartialEq, PartialOrd)]
pub(crate) struct RootYawEffectorTerminal {
    direction: RootYawDirection,
}

#[derive(Clone, Copy, Debug, Eq, Ord, PartialEq, PartialOrd)]
pub(crate) struct RootYawProprioceptorTerminal {
    direction: RootYawDirection,
}

impl RootYawEffectorTerminal {
    pub(crate) fn new(direction: RootYawDirection) -> Self {
        Self { direction }
    }

    pub(crate) fn direction(self) -> RootYawDirection {
        self.direction
    }

    pub(crate) fn from_ordinal(ordinal: u8) -> Option<Self> {
        Some(Self::new(match ordinal {
            0 => RootYawDirection::Negative,
            1 => RootYawDirection::Positive,
            _ => return None,
        }))
    }
}

impl RootYawProprioceptorTerminal {
    pub(crate) fn new(direction: RootYawDirection) -> Self {
        Self { direction }
    }

    pub(crate) fn direction(self) -> RootYawDirection {
        self.direction
    }

    pub(crate) fn ordinal(self) -> usize {
        self.direction as usize
    }

    pub(crate) fn from_ordinal(ordinal: u8) -> Option<Self> {
        Some(Self::new(match ordinal {
            0 => RootYawDirection::Negative,
            1 => RootYawDirection::Positive,
            _ => return None,
        }))
    }

    pub(crate) fn paired_effector(self) -> RootYawEffectorTerminal {
        RootYawEffectorTerminal::new(self.direction)
    }
}
