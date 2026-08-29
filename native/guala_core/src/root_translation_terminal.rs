//! Fixed directional terminals for the embodied world's root translation.
//!
//! The authenticated world remains the sole owner of root position. These
//! terminals carry only the physical direction of one native layer-12
//! discharge and of its returned displacement; they contain no destination,
//! object identity, route, action label, or selection policy.

use crate::root_yaw_terminal::{
    ROOT_YAW_PROPRIOCEPTOR_TOPOLOGY_OFFSET, ROOT_YAW_TERMINAL_COUNT,
};

pub(crate) const ROOT_TRANSLATION_PROPRIOCEPTOR_TOPOLOGY_OFFSET: usize =
    ROOT_YAW_PROPRIOCEPTOR_TOPOLOGY_OFFSET + ROOT_YAW_TERMINAL_COUNT;
pub(crate) const ROOT_TRANSLATION_TERMINAL_COUNT: usize = 4;

#[derive(Clone, Copy, Debug, Eq, Ord, PartialEq, PartialOrd)]
#[repr(u8)]
pub(crate) enum RootTranslationAxis {
    X = 0,
    Y = 1,
}

#[derive(Clone, Copy, Debug, Eq, Ord, PartialEq, PartialOrd)]
#[repr(u8)]
pub(crate) enum RootTranslationDirection {
    Negative = 0,
    Positive = 1,
}

#[derive(Clone, Copy, Debug, Eq, Ord, PartialEq, PartialOrd)]
pub(crate) struct RootTranslationEffectorTerminal {
    axis: RootTranslationAxis,
    direction: RootTranslationDirection,
}

#[derive(Clone, Copy, Debug, Eq, Ord, PartialEq, PartialOrd)]
pub(crate) struct RootTranslationProprioceptorTerminal {
    axis: RootTranslationAxis,
    direction: RootTranslationDirection,
}

impl RootTranslationEffectorTerminal {
    pub(crate) fn new(
        axis: RootTranslationAxis,
        direction: RootTranslationDirection,
    ) -> Self {
        Self { axis, direction }
    }

    pub(crate) fn axis(self) -> RootTranslationAxis {
        self.axis
    }

    pub(crate) fn direction(self) -> RootTranslationDirection {
        self.direction
    }

    pub(crate) fn ordinal(self) -> u32 {
        self.axis as u32 * 2 + self.direction as u32
    }

    pub(crate) fn from_ordinals(axis: u8, direction: u8) -> Option<Self> {
        Some(Self::new(decode_axis(axis)?, decode_direction(direction)?))
    }
}

impl RootTranslationProprioceptorTerminal {
    pub(crate) fn new(
        axis: RootTranslationAxis,
        direction: RootTranslationDirection,
    ) -> Self {
        Self { axis, direction }
    }

    pub(crate) fn axis(self) -> RootTranslationAxis {
        self.axis
    }

    pub(crate) fn direction(self) -> RootTranslationDirection {
        self.direction
    }

    pub(crate) fn ordinal(self) -> usize {
        self.axis as usize * 2 + self.direction as usize
    }

    pub(crate) fn from_ordinals(axis: u8, direction: u8) -> Option<Self> {
        Some(Self::new(decode_axis(axis)?, decode_direction(direction)?))
    }

    pub(crate) fn paired_effector(self) -> RootTranslationEffectorTerminal {
        RootTranslationEffectorTerminal::new(self.axis, self.direction)
    }
}

fn decode_axis(value: u8) -> Option<RootTranslationAxis> {
    match value {
        0 => Some(RootTranslationAxis::X),
        1 => Some(RootTranslationAxis::Y),
        _ => None,
    }
}

fn decode_direction(value: u8) -> Option<RootTranslationDirection> {
    match value {
        0 => Some(RootTranslationDirection::Negative),
        1 => Some(RootTranslationDirection::Positive),
        _ => None,
    }
}
