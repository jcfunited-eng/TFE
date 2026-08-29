//! Fixed-capacity local articulated-body state.
//!
//! The authenticated embodiment world remains the sole authority for root
//! position, root heading, collision, reach, and held-object state. This record
//! persists only causative configuration inside the body: posture, gaze, eyes,
//! eyelids, face, mouth, airway, limbs, and hands. It contains no action names,
//! motor-cell lookup table, learned meaning, history, owner, lock, digest, or
//! observation cache.

use core::mem::size_of;

const BODY_MAGIC: &[u8; 8] = b"GLBODY01";
const LEGACY_BODY_VERSION: u16 = 1;
const BODY_VERSION: u16 = 2;
pub(crate) const LEGACY_BODY_AXIS_COUNT: usize = 37;
pub(crate) const BODY_AXIS_COUNT: usize = 45;
pub(crate) const LEGACY_BODY_EFFECTOR_TERMINAL_COUNT: usize = LEGACY_BODY_AXIS_COUNT * 2;
pub(crate) const BODY_EFFECTOR_TERMINAL_COUNT: usize = BODY_AXIS_COUNT * 2;
/// Body-layer neuronal places 0..9 are the already-live four displacement,
/// four articulatory-body, and two thermal receptors. The local articulated
/// proprioceptors are a distinct organ and therefore begin at the next
/// declared place. This is fixed anatomy, not a runtime offset or an action
/// selector; the original terminal ordinals remain 0..73.
pub(crate) const BODY_PROPRIOCEPTOR_TOPOLOGY_OFFSET: usize = 10;
/// Load endings are distinct from antagonist-length endings.  They occupy the
/// next fixed body territory, preserving both physical quantities without
/// flattening either one into a combined proprioceptive score.
pub(crate) const BODY_EFFECTOR_LOAD_TOPOLOGY_OFFSET: usize =
    BODY_PROPRIOCEPTOR_TOPOLOGY_OFFSET + LEGACY_BODY_EFFECTOR_TERMINAL_COUNT;
/// The six already-persisted root-yaw/root-translation endings occupy body
/// topology 158..163. New tract endings append after them; the original 37
/// axes and every root ending therefore retain their exact resident address.
const LEGACY_ROOT_EFFECTOR_TERMINAL_COUNT: usize = 6;
pub(crate) const ADDED_BODY_PROPRIOCEPTOR_TOPOLOGY_OFFSET: usize =
    BODY_EFFECTOR_LOAD_TOPOLOGY_OFFSET
        + LEGACY_BODY_EFFECTOR_TERMINAL_COUNT
        + LEGACY_ROOT_EFFECTOR_TERMINAL_COUNT;
pub(crate) const ADDED_BODY_EFFECTOR_LOAD_TOPOLOGY_OFFSET: usize =
    ADDED_BODY_PROPRIOCEPTOR_TOPOLOGY_OFFSET
        + (BODY_EFFECTOR_TERMINAL_COUNT - LEGACY_BODY_EFFECTOR_TERMINAL_COUNT);
pub(crate) const VOCAL_TRACT_SECTION_COUNT: usize = 8;
const HEADER_BYTES: usize = BODY_MAGIC.len() + size_of::<u16>();
pub(crate) const ARTICULATED_BODY_STATE_BYTES: usize = HEADER_BYTES
    + BODY_AXIS_COUNT * size_of::<i32>()
    + size_of::<u32>()
    + size_of::<u8>();

pub(crate) const MIN_LUNG_AIR_MICROLITRES: u32 = 500_000;
pub(crate) const NEUTRAL_LUNG_AIR_MICROLITRES: u32 = 2_000_000;
pub(crate) const MAX_LUNG_AIR_MICROLITRES: u32 = 4_000_000;
pub(crate) const MIN_TRACT_AREA_SQUARE_MILLIMETRES: i32 = 20;
pub(crate) const MAX_TRACT_AREA_SQUARE_MILLIMETRES: i32 = 1_000;
pub(crate) const NEUTRAL_TRACT_AREAS_SQUARE_MILLIMETRES: [i32; VOCAL_TRACT_SECTION_COUNT] =
    [125, 145, 165, 185, 205, 225, 245, 265];

#[derive(Clone, Copy, Debug, Eq, Ord, PartialEq, PartialOrd)]
#[repr(u8)]
pub(crate) enum BodyAxis {
    TorsoPitch = 0,
    TorsoRoll,
    NeckYaw,
    NeckPitch,
    LeftEyeYaw,
    LeftEyePitch,
    RightEyeYaw,
    RightEyePitch,
    LeftEyelidAperture,
    RightEyelidAperture,
    LeftBrowHeight,
    RightBrowHeight,
    LeftCheekRaise,
    RightCheekRaise,
    JawOpening,
    LipAperture,
    LipWidth,
    PerioralDisplacement,
    GlottalAperture,
    LeftShoulderPitch,
    LeftShoulderRoll,
    LeftElbowFlexion,
    LeftWristYaw,
    LeftGripAperture,
    RightShoulderPitch,
    RightShoulderRoll,
    RightElbowFlexion,
    RightWristYaw,
    RightGripAperture,
    LeftHipPitch,
    LeftHipRoll,
    LeftKneeFlexion,
    LeftAnklePitch,
    RightHipPitch,
    RightHipRoll,
    RightKneeFlexion,
    RightAnklePitch,
    VocalTractSection0Area,
    VocalTractSection1Area,
    VocalTractSection2Area,
    VocalTractSection3Area,
    VocalTractSection4Area,
    VocalTractSection5Area,
    VocalTractSection6Area,
    VocalTractSection7Area,
}

pub(crate) const BODY_AXES: [BodyAxis; BODY_AXIS_COUNT] = [
    BodyAxis::TorsoPitch,
    BodyAxis::TorsoRoll,
    BodyAxis::NeckYaw,
    BodyAxis::NeckPitch,
    BodyAxis::LeftEyeYaw,
    BodyAxis::LeftEyePitch,
    BodyAxis::RightEyeYaw,
    BodyAxis::RightEyePitch,
    BodyAxis::LeftEyelidAperture,
    BodyAxis::RightEyelidAperture,
    BodyAxis::LeftBrowHeight,
    BodyAxis::RightBrowHeight,
    BodyAxis::LeftCheekRaise,
    BodyAxis::RightCheekRaise,
    BodyAxis::JawOpening,
    BodyAxis::LipAperture,
    BodyAxis::LipWidth,
    BodyAxis::PerioralDisplacement,
    BodyAxis::GlottalAperture,
    BodyAxis::LeftShoulderPitch,
    BodyAxis::LeftShoulderRoll,
    BodyAxis::LeftElbowFlexion,
    BodyAxis::LeftWristYaw,
    BodyAxis::LeftGripAperture,
    BodyAxis::RightShoulderPitch,
    BodyAxis::RightShoulderRoll,
    BodyAxis::RightElbowFlexion,
    BodyAxis::RightWristYaw,
    BodyAxis::RightGripAperture,
    BodyAxis::LeftHipPitch,
    BodyAxis::LeftHipRoll,
    BodyAxis::LeftKneeFlexion,
    BodyAxis::LeftAnklePitch,
    BodyAxis::RightHipPitch,
    BodyAxis::RightHipRoll,
    BodyAxis::RightKneeFlexion,
    BodyAxis::RightAnklePitch,
    BodyAxis::VocalTractSection0Area,
    BodyAxis::VocalTractSection1Area,
    BodyAxis::VocalTractSection2Area,
    BodyAxis::VocalTractSection3Area,
    BodyAxis::VocalTractSection4Area,
    BodyAxis::VocalTractSection5Area,
    BodyAxis::VocalTractSection6Area,
    BodyAxis::VocalTractSection7Area,
];

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) enum BodyAxisUnit {
    Millidegree,
    Micrometre,
    SquareMillimetre,
}

#[derive(Clone, Copy, Debug, Eq, Ord, PartialEq, PartialOrd)]
#[repr(u8)]
pub(crate) enum BodyEffectorDirection {
    TowardMinimum = 0,
    TowardMaximum = 1,
}

#[derive(Clone, Copy, Debug, Eq, Ord, PartialEq, PartialOrd)]
pub(crate) struct BodyEffectorTerminal {
    axis: BodyAxis,
    direction: BodyEffectorDirection,
}

/// One fixed proprioceptive ending paired with an antagonist body direction.
/// This is afferent anatomy.  Its paired effector occupies the same axis and
/// direction, but the two terminals are deliberately different types so a
/// receptor can never become motor authority merely by being reached.
#[derive(Clone, Copy, Debug, Eq, Ord, PartialEq, PartialOrd)]
pub(crate) struct BodyProprioceptorTerminal {
    axis: BodyAxis,
    direction: BodyEffectorDirection,
}

impl BodyEffectorTerminal {
    pub(crate) fn new(axis: BodyAxis, direction: BodyEffectorDirection) -> Self {
        Self { axis, direction }
    }

    pub(crate) fn axis(self) -> BodyAxis {
        self.axis
    }

    pub(crate) fn direction(self) -> BodyEffectorDirection {
        self.direction
    }

    pub(crate) fn ordinal(self) -> usize {
        self.axis.index() * 2 + self.direction as usize
    }

    pub(crate) fn from_ordinals(axis: u8, direction: u8) -> Option<Self> {
        let axis = BODY_AXES.get(usize::from(axis)).copied()?;
        let direction = match direction {
            0 => BodyEffectorDirection::TowardMinimum,
            1 => BodyEffectorDirection::TowardMaximum,
            _ => return None,
        };
        Some(Self::new(axis, direction))
    }
}

impl BodyProprioceptorTerminal {
    pub(crate) fn new(axis: BodyAxis, direction: BodyEffectorDirection) -> Self {
        Self { axis, direction }
    }

    pub(crate) fn axis(self) -> BodyAxis {
        self.axis
    }

    pub(crate) fn direction(self) -> BodyEffectorDirection {
        self.direction
    }

    pub(crate) fn ordinal(self) -> usize {
        self.axis.index() * 2 + self.direction as usize
    }

    pub(crate) fn from_ordinals(axis: u8, direction: u8) -> Option<Self> {
        let axis = BODY_AXES.get(usize::from(axis)).copied()?;
        let direction = match direction {
            0 => BodyEffectorDirection::TowardMinimum,
            1 => BodyEffectorDirection::TowardMaximum,
            _ => return None,
        };
        Some(Self::new(axis, direction))
    }

    pub(crate) fn paired_effector(self) -> BodyEffectorTerminal {
        BodyEffectorTerminal::new(self.axis, self.direction)
    }

    pub(crate) fn proprioceptor_topology_index(self) -> usize {
        if self.ordinal() < LEGACY_BODY_EFFECTOR_TERMINAL_COUNT {
            BODY_PROPRIOCEPTOR_TOPOLOGY_OFFSET + self.ordinal()
        } else {
            ADDED_BODY_PROPRIOCEPTOR_TOPOLOGY_OFFSET
                + self.ordinal() - LEGACY_BODY_EFFECTOR_TERMINAL_COUNT
        }
    }

    pub(crate) fn load_topology_index(self) -> usize {
        if self.ordinal() < LEGACY_BODY_EFFECTOR_TERMINAL_COUNT {
            BODY_EFFECTOR_LOAD_TOPOLOGY_OFFSET + self.ordinal()
        } else {
            ADDED_BODY_EFFECTOR_LOAD_TOPOLOGY_OFFSET
                + self.ordinal() - LEGACY_BODY_EFFECTOR_TERMINAL_COUNT
        }
    }

    /// The antagonist effector on the same articulated axis. A reacted-load
    /// ending uses this terminal for local negative force feedback: load from
    /// a motor pushing toward one stop reaches the motor that can unload it.
    pub(crate) fn opposing_effector(self) -> BodyEffectorTerminal {
        let direction = match self.direction {
            BodyEffectorDirection::TowardMinimum => BodyEffectorDirection::TowardMaximum,
            BodyEffectorDirection::TowardMaximum => BodyEffectorDirection::TowardMinimum,
        };
        BodyEffectorTerminal::new(self.axis, direction)
    }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) struct BodyEffectorDrive {
    pub(crate) terminal: BodyEffectorTerminal,
    pub(crate) outward_elementary_carriers: u128,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) struct AdmittedBodyEffectorDrives {
    drives: Box<[BodyEffectorDrive]>,
}

impl AdmittedBodyEffectorDrives {
    pub(crate) fn admit(mut drives: Vec<BodyEffectorDrive>) -> Result<Self, ArticulatedBodyError> {
        if drives.len() > BODY_EFFECTOR_TERMINAL_COUNT
            || drives
                .iter()
                .any(|drive| drive.outward_elementary_carriers == 0)
        {
            return Err(ArticulatedBodyError::InvalidEffectorDrives);
        }
        drives.sort_unstable_by_key(|drive| drive.terminal);
        if drives
            .windows(2)
            .any(|pair| pair[0].terminal == pair[1].terminal)
        {
            return Err(ArticulatedBodyError::InvalidEffectorDrives);
        }
        Ok(Self {
            drives: drives.into_boxed_slice(),
        })
    }

    pub(crate) fn quiescent() -> Self {
        Self {
            drives: Box::new([]),
        }
    }

    pub(crate) fn drives(&self) -> &[BodyEffectorDrive] {
        &self.drives
    }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) struct BodyProprioceptiveConsequence {
    pub(crate) axis: BodyAxis,
    pub(crate) unit: BodyAxisUnit,
    pub(crate) predecessor_position: i32,
    pub(crate) successor_position: i32,
    pub(crate) signed_displacement: i32,
    pub(crate) toward_minimum_carriers: u128,
    pub(crate) toward_maximum_carriers: u128,
    pub(crate) opposed_carriers_per_terminal: u128,
    pub(crate) applied_displacement_quanta: u128,
    pub(crate) stalled_carriers: u128,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) struct ArticulatedBodyTransition {
    pub(crate) successor: ArticulatedBodyState,
    pub(crate) proprioceptive_consequences: Vec<BodyProprioceptiveConsequence>,
    pub(crate) reached_terminal_count: usize,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) struct BodyAxisAnatomy {
    pub(crate) axis: BodyAxis,
    pub(crate) unit: BodyAxisUnit,
    pub(crate) minimum: i32,
    pub(crate) neutral: i32,
    pub(crate) maximum: i32,
}

impl BodyAxis {
    pub(crate) fn index(self) -> usize {
        self as usize
    }

    pub(crate) fn anatomy(self) -> BodyAxisAnatomy {
        BODY_AXIS_ANATOMY[self.index()]
    }

    /// True only for axes that physically shape or gate the vocal tract.
    /// This is fixed body anatomy, not a phoneme, word, action label, or
    /// learned meaning.  Facial expression and every non-vocal limb axis are
    /// deliberately excluded.
    pub(crate) fn is_vocal_articulator(self) -> bool {
        matches!(
            self,
            Self::JawOpening
                | Self::LipAperture
                | Self::LipWidth
                | Self::PerioralDisplacement
                | Self::GlottalAperture
                | Self::VocalTractSection0Area
                | Self::VocalTractSection1Area
                | Self::VocalTractSection2Area
                | Self::VocalTractSection3Area
                | Self::VocalTractSection4Area
                | Self::VocalTractSection5Area
                | Self::VocalTractSection6Area
                | Self::VocalTractSection7Area
        )
    }

    pub(crate) fn anatomical_name(self) -> &'static str {
        match self {
            Self::TorsoPitch => "torso_pitch",
            Self::TorsoRoll => "torso_roll",
            Self::NeckYaw => "neck_yaw",
            Self::NeckPitch => "neck_pitch",
            Self::LeftEyeYaw => "left_eye_yaw",
            Self::LeftEyePitch => "left_eye_pitch",
            Self::RightEyeYaw => "right_eye_yaw",
            Self::RightEyePitch => "right_eye_pitch",
            Self::LeftEyelidAperture => "left_eyelid_aperture",
            Self::RightEyelidAperture => "right_eyelid_aperture",
            Self::LeftBrowHeight => "left_brow_height",
            Self::RightBrowHeight => "right_brow_height",
            Self::LeftCheekRaise => "left_cheek_raise",
            Self::RightCheekRaise => "right_cheek_raise",
            Self::JawOpening => "jaw_opening",
            Self::LipAperture => "lip_aperture",
            Self::LipWidth => "lip_width",
            Self::PerioralDisplacement => "perioral_displacement",
            Self::GlottalAperture => "glottal_aperture",
            Self::LeftShoulderPitch => "left_shoulder_pitch",
            Self::LeftShoulderRoll => "left_shoulder_roll",
            Self::LeftElbowFlexion => "left_elbow_flexion",
            Self::LeftWristYaw => "left_wrist_yaw",
            Self::LeftGripAperture => "left_grip_aperture",
            Self::RightShoulderPitch => "right_shoulder_pitch",
            Self::RightShoulderRoll => "right_shoulder_roll",
            Self::RightElbowFlexion => "right_elbow_flexion",
            Self::RightWristYaw => "right_wrist_yaw",
            Self::RightGripAperture => "right_grip_aperture",
            Self::LeftHipPitch => "left_hip_pitch",
            Self::LeftHipRoll => "left_hip_roll",
            Self::LeftKneeFlexion => "left_knee_flexion",
            Self::LeftAnklePitch => "left_ankle_pitch",
            Self::RightHipPitch => "right_hip_pitch",
            Self::RightHipRoll => "right_hip_roll",
            Self::RightKneeFlexion => "right_knee_flexion",
            Self::RightAnklePitch => "right_ankle_pitch",
            Self::VocalTractSection0Area => "vocal_tract_section_0_area",
            Self::VocalTractSection1Area => "vocal_tract_section_1_area",
            Self::VocalTractSection2Area => "vocal_tract_section_2_area",
            Self::VocalTractSection3Area => "vocal_tract_section_3_area",
            Self::VocalTractSection4Area => "vocal_tract_section_4_area",
            Self::VocalTractSection5Area => "vocal_tract_section_5_area",
            Self::VocalTractSection6Area => "vocal_tract_section_6_area",
            Self::VocalTractSection7Area => "vocal_tract_section_7_area",
        }
    }
}

impl BodyAxisUnit {
    pub(crate) fn physical_name(self) -> &'static str {
        match self {
            Self::Millidegree => "millidegree",
            Self::Micrometre => "micrometre",
            Self::SquareMillimetre => "square_millimetre",
        }
    }
}

const fn anatomy(
    axis: BodyAxis,
    unit: BodyAxisUnit,
    minimum: i32,
    neutral: i32,
    maximum: i32,
) -> BodyAxisAnatomy {
    BodyAxisAnatomy {
        axis,
        unit,
        minimum,
        neutral,
        maximum,
    }
}

pub(crate) const BODY_AXIS_ANATOMY: [BodyAxisAnatomy; BODY_AXIS_COUNT] = [
    anatomy(
        BodyAxis::TorsoPitch,
        BodyAxisUnit::Millidegree,
        -30_000,
        0,
        45_000,
    ),
    anatomy(
        BodyAxis::TorsoRoll,
        BodyAxisUnit::Millidegree,
        -25_000,
        0,
        25_000,
    ),
    anatomy(
        BodyAxis::NeckYaw,
        BodyAxisUnit::Millidegree,
        -75_000,
        0,
        75_000,
    ),
    anatomy(
        BodyAxis::NeckPitch,
        BodyAxisUnit::Millidegree,
        -35_000,
        0,
        45_000,
    ),
    anatomy(
        BodyAxis::LeftEyeYaw,
        BodyAxisUnit::Millidegree,
        -35_000,
        0,
        35_000,
    ),
    anatomy(
        BodyAxis::LeftEyePitch,
        BodyAxisUnit::Millidegree,
        -25_000,
        0,
        25_000,
    ),
    anatomy(
        BodyAxis::RightEyeYaw,
        BodyAxisUnit::Millidegree,
        -35_000,
        0,
        35_000,
    ),
    anatomy(
        BodyAxis::RightEyePitch,
        BodyAxisUnit::Millidegree,
        -25_000,
        0,
        25_000,
    ),
    anatomy(
        BodyAxis::LeftEyelidAperture,
        BodyAxisUnit::Micrometre,
        0,
        10_000,
        12_000,
    ),
    anatomy(
        BodyAxis::RightEyelidAperture,
        BodyAxisUnit::Micrometre,
        0,
        10_000,
        12_000,
    ),
    anatomy(
        BodyAxis::LeftBrowHeight,
        BodyAxisUnit::Micrometre,
        -5_000,
        0,
        5_000,
    ),
    anatomy(
        BodyAxis::RightBrowHeight,
        BodyAxisUnit::Micrometre,
        -5_000,
        0,
        5_000,
    ),
    anatomy(
        BodyAxis::LeftCheekRaise,
        BodyAxisUnit::Micrometre,
        0,
        0,
        8_000,
    ),
    anatomy(
        BodyAxis::RightCheekRaise,
        BodyAxisUnit::Micrometre,
        0,
        0,
        8_000,
    ),
    anatomy(BodyAxis::JawOpening, BodyAxisUnit::Micrometre, 0, 0, 35_000),
    anatomy(
        BodyAxis::LipAperture,
        BodyAxisUnit::Micrometre,
        0,
        0,
        20_000,
    ),
    anatomy(
        BodyAxis::LipWidth,
        BodyAxisUnit::Micrometre,
        25_000,
        45_000,
        60_000,
    ),
    anatomy(
        BodyAxis::PerioralDisplacement,
        BodyAxisUnit::Micrometre,
        -10_000,
        0,
        10_000,
    ),
    anatomy(
        BodyAxis::GlottalAperture,
        BodyAxisUnit::SquareMillimetre,
        20,
        80,
        400,
    ),
    anatomy(
        BodyAxis::LeftShoulderPitch,
        BodyAxisUnit::Millidegree,
        -180_000,
        0,
        180_000,
    ),
    anatomy(
        BodyAxis::LeftShoulderRoll,
        BodyAxisUnit::Millidegree,
        -90_000,
        0,
        90_000,
    ),
    anatomy(
        BodyAxis::LeftElbowFlexion,
        BodyAxisUnit::Millidegree,
        0,
        0,
        150_000,
    ),
    anatomy(
        BodyAxis::LeftWristYaw,
        BodyAxisUnit::Millidegree,
        -90_000,
        0,
        90_000,
    ),
    anatomy(
        BodyAxis::LeftGripAperture,
        BodyAxisUnit::Micrometre,
        0,
        60_000,
        60_000,
    ),
    anatomy(
        BodyAxis::RightShoulderPitch,
        BodyAxisUnit::Millidegree,
        -180_000,
        0,
        180_000,
    ),
    anatomy(
        BodyAxis::RightShoulderRoll,
        BodyAxisUnit::Millidegree,
        -90_000,
        0,
        90_000,
    ),
    anatomy(
        BodyAxis::RightElbowFlexion,
        BodyAxisUnit::Millidegree,
        0,
        0,
        150_000,
    ),
    anatomy(
        BodyAxis::RightWristYaw,
        BodyAxisUnit::Millidegree,
        -90_000,
        0,
        90_000,
    ),
    anatomy(
        BodyAxis::RightGripAperture,
        BodyAxisUnit::Micrometre,
        0,
        60_000,
        60_000,
    ),
    anatomy(
        BodyAxis::LeftHipPitch,
        BodyAxisUnit::Millidegree,
        -120_000,
        0,
        45_000,
    ),
    anatomy(
        BodyAxis::LeftHipRoll,
        BodyAxisUnit::Millidegree,
        -45_000,
        0,
        45_000,
    ),
    anatomy(
        BodyAxis::LeftKneeFlexion,
        BodyAxisUnit::Millidegree,
        0,
        0,
        150_000,
    ),
    anatomy(
        BodyAxis::LeftAnklePitch,
        BodyAxisUnit::Millidegree,
        -45_000,
        0,
        45_000,
    ),
    anatomy(
        BodyAxis::RightHipPitch,
        BodyAxisUnit::Millidegree,
        -120_000,
        0,
        45_000,
    ),
    anatomy(
        BodyAxis::RightHipRoll,
        BodyAxisUnit::Millidegree,
        -45_000,
        0,
        45_000,
    ),
    anatomy(
        BodyAxis::RightKneeFlexion,
        BodyAxisUnit::Millidegree,
        0,
        0,
        150_000,
    ),
    anatomy(
        BodyAxis::RightAnklePitch,
        BodyAxisUnit::Millidegree,
        -45_000,
        0,
        45_000,
    ),
    anatomy(
        BodyAxis::VocalTractSection0Area,
        BodyAxisUnit::SquareMillimetre,
        MIN_TRACT_AREA_SQUARE_MILLIMETRES,
        NEUTRAL_TRACT_AREAS_SQUARE_MILLIMETRES[0],
        MAX_TRACT_AREA_SQUARE_MILLIMETRES,
    ),
    anatomy(
        BodyAxis::VocalTractSection1Area,
        BodyAxisUnit::SquareMillimetre,
        MIN_TRACT_AREA_SQUARE_MILLIMETRES,
        NEUTRAL_TRACT_AREAS_SQUARE_MILLIMETRES[1],
        MAX_TRACT_AREA_SQUARE_MILLIMETRES,
    ),
    anatomy(
        BodyAxis::VocalTractSection2Area,
        BodyAxisUnit::SquareMillimetre,
        MIN_TRACT_AREA_SQUARE_MILLIMETRES,
        NEUTRAL_TRACT_AREAS_SQUARE_MILLIMETRES[2],
        MAX_TRACT_AREA_SQUARE_MILLIMETRES,
    ),
    anatomy(
        BodyAxis::VocalTractSection3Area,
        BodyAxisUnit::SquareMillimetre,
        MIN_TRACT_AREA_SQUARE_MILLIMETRES,
        NEUTRAL_TRACT_AREAS_SQUARE_MILLIMETRES[3],
        MAX_TRACT_AREA_SQUARE_MILLIMETRES,
    ),
    anatomy(
        BodyAxis::VocalTractSection4Area,
        BodyAxisUnit::SquareMillimetre,
        MIN_TRACT_AREA_SQUARE_MILLIMETRES,
        NEUTRAL_TRACT_AREAS_SQUARE_MILLIMETRES[4],
        MAX_TRACT_AREA_SQUARE_MILLIMETRES,
    ),
    anatomy(
        BodyAxis::VocalTractSection5Area,
        BodyAxisUnit::SquareMillimetre,
        MIN_TRACT_AREA_SQUARE_MILLIMETRES,
        NEUTRAL_TRACT_AREAS_SQUARE_MILLIMETRES[5],
        MAX_TRACT_AREA_SQUARE_MILLIMETRES,
    ),
    anatomy(
        BodyAxis::VocalTractSection6Area,
        BodyAxisUnit::SquareMillimetre,
        MIN_TRACT_AREA_SQUARE_MILLIMETRES,
        NEUTRAL_TRACT_AREAS_SQUARE_MILLIMETRES[6],
        MAX_TRACT_AREA_SQUARE_MILLIMETRES,
    ),
    anatomy(
        BodyAxis::VocalTractSection7Area,
        BodyAxisUnit::SquareMillimetre,
        MIN_TRACT_AREA_SQUARE_MILLIMETRES,
        NEUTRAL_TRACT_AREAS_SQUARE_MILLIMETRES[7],
        MAX_TRACT_AREA_SQUARE_MILLIMETRES,
    ),
];

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) enum ArticulatedBodyError {
    InvalidLength,
    InvalidMagic,
    UnsupportedVersion(u16),
    AxisOutsideAnatomy(BodyAxis),
    LungAirOutsideAnatomy,
    VocalTractOutsideAnatomy(usize),
    InvalidEffectorDrives,
    EffectorArithmeticWidth,
    TrailingBytes,
}

/// Settle one already-admitted sparse terminal frontier. Each outward whole
/// elementary carrier is one smallest lattice displacement toward that
/// terminal's anatomical stop. Opposed carriers meet locally and produce no
/// displacement; carriers beyond a stop are reported as stalled. The function
/// touches only reached terminals and their axes and performs no serialization,
/// authentication, digest, allocation proportional to organism history, or
/// neuronal scan.
pub(crate) fn settle_body_effector_drives(
    predecessor: &ArticulatedBodyState,
    admitted: &AdmittedBodyEffectorDrives,
) -> Result<ArticulatedBodyTransition, ArticulatedBodyError> {
    let mut successor = predecessor.clone();
    let mut consequences = Vec::new();
    consequences
        .try_reserve_exact(admitted.drives.len().min(BODY_AXIS_COUNT))
        .map_err(|_| ArticulatedBodyError::EffectorArithmeticWidth)?;
    let mut cursor = 0usize;
    while cursor < admitted.drives.len() {
        let axis = admitted.drives[cursor].terminal.axis();
        let mut toward_minimum = 0_u128;
        let mut toward_maximum = 0_u128;
        while cursor < admitted.drives.len() && admitted.drives[cursor].terminal.axis() == axis {
            let drive = admitted.drives[cursor];
            match drive.terminal.direction() {
                BodyEffectorDirection::TowardMinimum => {
                    toward_minimum = drive.outward_elementary_carriers
                }
                BodyEffectorDirection::TowardMaximum => {
                    toward_maximum = drive.outward_elementary_carriers
                }
            }
            cursor += 1;
        }
        let opposed = toward_minimum.min(toward_maximum);
        let signed_drive = if toward_maximum >= toward_minimum {
            i128::try_from(toward_maximum - toward_minimum)
                .map_err(|_| ArticulatedBodyError::EffectorArithmeticWidth)?
        } else {
            -i128::try_from(toward_minimum - toward_maximum)
                .map_err(|_| ArticulatedBodyError::EffectorArithmeticWidth)?
        };
        let anatomy = axis.anatomy();
        let predecessor_position = predecessor.axis(axis);
        let available_displacement = if signed_drive.is_negative() {
            i128::from(predecessor_position - anatomy.minimum)
        } else {
            i128::from(anatomy.maximum - predecessor_position)
        };
        let applied = signed_drive.unsigned_abs().min(
            u128::try_from(available_displacement)
                .map_err(|_| ArticulatedBodyError::EffectorArithmeticWidth)?,
        );
        let signed_applied = i32::try_from(applied)
            .map_err(|_| ArticulatedBodyError::EffectorArithmeticWidth)?
            * if signed_drive.is_negative() { -1 } else { 1 };
        let successor_position = predecessor_position
            .checked_add(signed_applied)
            .ok_or(ArticulatedBodyError::EffectorArithmeticWidth)?;
        successor.axes[axis.index()] = successor_position;
        consequences.push(BodyProprioceptiveConsequence {
            axis,
            unit: anatomy.unit,
            predecessor_position,
            successor_position,
            signed_displacement: signed_applied,
            toward_minimum_carriers: toward_minimum,
            toward_maximum_carriers: toward_maximum,
            opposed_carriers_per_terminal: opposed,
            applied_displacement_quanta: applied,
            stalled_carriers: signed_drive.unsigned_abs() - applied,
        });
    }
    Ok(ArticulatedBodyTransition {
        successor,
        proprioceptive_consequences: consequences,
        reached_terminal_count: admitted.drives.len(),
    })
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) struct ArticulatedBodyState {
    axes: [i32; BODY_AXIS_COUNT],
    lung_air_microlitres: u32,
    proprioception_initialized: bool,
}

impl ArticulatedBodyState {
    pub(crate) fn at_neutral() -> Self {
        let mut axes = [0_i32; BODY_AXIS_COUNT];
        for axis in BODY_AXES {
            axes[axis.index()] = axis.anatomy().neutral;
        }
        Self {
            axes,
            lung_air_microlitres: NEUTRAL_LUNG_AIR_MICROLITRES,
            proprioception_initialized: false,
        }
    }

    pub(crate) fn from_physical_state(
        axes: [i32; BODY_AXIS_COUNT],
        lung_air_microlitres: u32,
        proprioception_initialized: bool,
    ) -> Result<Self, ArticulatedBodyError> {
        let state = Self {
            axes,
            lung_air_microlitres,
            proprioception_initialized,
        };
        state.validate()?;
        Ok(state)
    }

    pub(crate) fn axis(&self, axis: BodyAxis) -> i32 {
        self.axes[axis.index()]
    }

    pub(crate) fn axes(&self) -> &[i32; BODY_AXIS_COUNT] {
        &self.axes
    }

    pub(crate) fn lung_air_microlitres(&self) -> u32 {
        self.lung_air_microlitres
    }

    pub(crate) fn vocal_tract_areas_square_millimetres(
        &self,
    ) -> [i32; VOCAL_TRACT_SECTION_COUNT] {
        self.axes[LEGACY_BODY_AXIS_COUNT..BODY_AXIS_COUNT]
            .try_into()
            .expect("the eight tract axes are contiguous")
    }

    pub(crate) fn proprioception_initialized(&self) -> bool {
        self.proprioception_initialized
    }

    pub(crate) fn initialize_proprioception(&mut self) {
        self.proprioception_initialized = true;
    }

    /// Preserve the exact physical body while requiring its complete current
    /// configuration to enter proprioception on the next lived interval.
    /// Used only by an explicit one-way migration when newly mounted innate
    /// sensorimotor anatomy must receive the body it now serves.
    pub(crate) fn requiring_proprioceptive_observation(mut self) -> Self {
        self.proprioception_initialized = false;
        self
    }

    pub(crate) fn resident_bytes() -> usize {
        ARTICULATED_BODY_STATE_BYTES
    }

    pub(crate) fn encode(
        &self,
    ) -> Result<[u8; ARTICULATED_BODY_STATE_BYTES], ArticulatedBodyError> {
        self.validate()?;
        let mut encoded = [0_u8; ARTICULATED_BODY_STATE_BYTES];
        let mut cursor = 0usize;
        encoded[cursor..cursor + BODY_MAGIC.len()].copy_from_slice(BODY_MAGIC);
        cursor += BODY_MAGIC.len();
        encoded[cursor..cursor + size_of::<u16>()].copy_from_slice(&BODY_VERSION.to_be_bytes());
        cursor += size_of::<u16>();
        for value in self.axes {
            encoded[cursor..cursor + size_of::<i32>()].copy_from_slice(&value.to_be_bytes());
            cursor += size_of::<i32>();
        }
        encoded[cursor..cursor + size_of::<u32>()]
            .copy_from_slice(&self.lung_air_microlitres.to_be_bytes());
        cursor += size_of::<u32>();
        encoded[cursor] = u8::from(self.proprioception_initialized);
        cursor += size_of::<u8>();
        debug_assert_eq!(cursor, ARTICULATED_BODY_STATE_BYTES);
        Ok(encoded)
    }

    pub(crate) fn decode(encoded: &[u8]) -> Result<Self, ArticulatedBodyError> {
        if encoded.len() != ARTICULATED_BODY_STATE_BYTES {
            return Err(ArticulatedBodyError::InvalidLength);
        }
        let mut cursor = 0usize;
        if &encoded[cursor..cursor + BODY_MAGIC.len()] != BODY_MAGIC {
            return Err(ArticulatedBodyError::InvalidMagic);
        }
        cursor += BODY_MAGIC.len();
        let version = u16::from_be_bytes(
            encoded[cursor..cursor + size_of::<u16>()]
                .try_into()
                .expect("fixed version width"),
        );
        cursor += size_of::<u16>();
        let mut axes = [0_i32; BODY_AXIS_COUNT];
        let encoded_axis_count = match version {
            LEGACY_BODY_VERSION => LEGACY_BODY_AXIS_COUNT,
            BODY_VERSION => BODY_AXIS_COUNT,
            _ => return Err(ArticulatedBodyError::UnsupportedVersion(version)),
        };
        for value in axes.iter_mut().take(encoded_axis_count) {
            *value = i32::from_be_bytes(
                encoded[cursor..cursor + size_of::<i32>()]
                    .try_into()
                    .expect("fixed axis width"),
            );
            cursor += size_of::<i32>();
        }
        let lung_air_microlitres = u32::from_be_bytes(
            encoded[cursor..cursor + size_of::<u32>()]
                .try_into()
                .expect("fixed lung-air width"),
        );
        cursor += size_of::<u32>();
        if version == LEGACY_BODY_VERSION {
            for value in axes
                .iter_mut()
                .skip(LEGACY_BODY_AXIS_COUNT)
                .take(VOCAL_TRACT_SECTION_COUNT)
            {
                *value = i32::from_be_bytes(
                    encoded[cursor..cursor + size_of::<i32>()]
                        .try_into()
                        .expect("fixed legacy tract-area width"),
                );
                cursor += size_of::<i32>();
            }
        }
        let persisted_proprioception_initialized = match encoded[cursor] {
            0 => false,
            1 => true,
            _ => return Err(ArticulatedBodyError::TrailingBytes),
        };
        cursor += size_of::<u8>();
        if cursor != encoded.len() {
            return Err(ArticulatedBodyError::TrailingBytes);
        }
        Self::from_physical_state(
            axes,
            lung_air_microlitres,
            version == BODY_VERSION && persisted_proprioception_initialized,
        )
    }

    fn validate(&self) -> Result<(), ArticulatedBodyError> {
        for axis in BODY_AXES {
            let anatomy = axis.anatomy();
            let value = self.axis(axis);
            if !(anatomy.minimum..=anatomy.maximum).contains(&value) {
                return Err(ArticulatedBodyError::AxisOutsideAnatomy(axis));
            }
        }
        if !(MIN_LUNG_AIR_MICROLITRES..=MAX_LUNG_AIR_MICROLITRES)
            .contains(&self.lung_air_microlitres)
        {
            return Err(ArticulatedBodyError::LungAirOutsideAnatomy);
        }
        for (index, area) in self
            .vocal_tract_areas_square_millimetres()
            .into_iter()
            .enumerate()
        {
            if !(MIN_TRACT_AREA_SQUARE_MILLIMETRES..=MAX_TRACT_AREA_SQUARE_MILLIMETRES)
                .contains(&area)
            {
                return Err(ArticulatedBodyError::VocalTractOutsideAnatomy(index));
            }
        }
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn neutral_state_is_canonical_and_cold_exact() {
        let state = ArticulatedBodyState::at_neutral();
        let encoded = state.encode().expect("neutral body encodes");
        assert_eq!(encoded.len(), 195);
        assert_eq!(ArticulatedBodyState::resident_bytes(), encoded.len());
        assert_eq!(ArticulatedBodyState::decode(&encoded), Ok(state));
    }

    #[test]
    fn legacy_body_migrates_its_same_tract_geometry_without_growing() {
        let mut legacy = [0_u8; ARTICULATED_BODY_STATE_BYTES];
        let mut legacy_tract = NEUTRAL_TRACT_AREAS_SQUARE_MILLIMETRES;
        for (index, area) in legacy_tract.iter_mut().enumerate() {
            *area += i32::try_from(index + 1).unwrap();
        }
        let mut cursor = 0usize;
        legacy[cursor..cursor + BODY_MAGIC.len()].copy_from_slice(BODY_MAGIC);
        cursor += BODY_MAGIC.len();
        legacy[cursor..cursor + size_of::<u16>()]
            .copy_from_slice(&LEGACY_BODY_VERSION.to_be_bytes());
        cursor += size_of::<u16>();
        for axis in BODY_AXES.iter().copied().take(LEGACY_BODY_AXIS_COUNT) {
            legacy[cursor..cursor + size_of::<i32>()]
                .copy_from_slice(&axis.anatomy().neutral.to_be_bytes());
            cursor += size_of::<i32>();
        }
        legacy[cursor..cursor + size_of::<u32>()]
            .copy_from_slice(&NEUTRAL_LUNG_AIR_MICROLITRES.to_be_bytes());
        cursor += size_of::<u32>();
        for area in legacy_tract {
            legacy[cursor..cursor + size_of::<i32>()].copy_from_slice(&area.to_be_bytes());
            cursor += size_of::<i32>();
        }
        legacy[cursor] = 1;
        cursor += 1;
        assert_eq!(cursor, ARTICULATED_BODY_STATE_BYTES);

        let migrated = ArticulatedBodyState::decode(&legacy).unwrap();
        assert_eq!(
            migrated.vocal_tract_areas_square_millimetres(),
            legacy_tract
        );
        assert!(!migrated.proprioception_initialized());
        let current = migrated.encode().unwrap();
        assert_eq!(current.len(), legacy.len());
        assert_eq!(
            u16::from_be_bytes(current[BODY_MAGIC.len()..HEADER_BYTES].try_into().unwrap()),
            BODY_VERSION
        );
    }

    #[test]
    fn axes_are_complete_ordered_and_neutral_inside_anatomy() {
        assert_eq!(BODY_AXES.len(), BODY_AXIS_COUNT);
        for (index, axis) in BODY_AXES.iter().copied().enumerate() {
            assert_eq!(axis.index(), index);
            let anatomy = axis.anatomy();
            assert_eq!(anatomy.axis, axis);
            assert!(anatomy.minimum <= anatomy.neutral);
            assert!(anatomy.neutral <= anatomy.maximum);
            assert_eq!(
                ArticulatedBodyState::at_neutral().axis(axis),
                anatomy.neutral
            );
        }
    }

    #[test]
    fn codec_refuses_noncanonical_or_out_of_body_state() {
        let state = ArticulatedBodyState::at_neutral();
        let mut encoded = state.encode().expect("neutral body encodes");
        encoded[0] ^= 1;
        assert_eq!(
            ArticulatedBodyState::decode(&encoded),
            Err(ArticulatedBodyError::InvalidMagic)
        );

        let mut axes = state.axes;
        axes[BodyAxis::NeckYaw.index()] = BodyAxis::NeckYaw.anatomy().maximum + 1;
        assert_eq!(
            ArticulatedBodyState::from_physical_state(
                axes,
                state.lung_air_microlitres,
                state.proprioception_initialized,
            ),
            Err(ArticulatedBodyError::AxisOutsideAnatomy(BodyAxis::NeckYaw)),
        );
    }

    #[test]
    fn encoded_size_is_fixed_not_history_dependent() {
        let neutral = ArticulatedBodyState::at_neutral();
        let mut axes = neutral.axes;
        for axis in BODY_AXES {
            axes[axis.index()] = axis.anatomy().maximum;
        }
        let maximum = ArticulatedBodyState::from_physical_state(
            axes,
            MAX_LUNG_AIR_MICROLITRES,
            true,
        )
        .expect("bounded maximum body");
        assert_eq!(
            neutral.encode().expect("neutral").len(),
            maximum.encode().expect("maximum").len()
        );
    }

    #[test]
    fn every_axis_has_one_exact_antagonist_terminal_pair() {
        let ordinals = BODY_AXES
            .iter()
            .copied()
            .flat_map(|axis| {
                [
                    BodyEffectorTerminal::new(axis, BodyEffectorDirection::TowardMinimum),
                    BodyEffectorTerminal::new(axis, BodyEffectorDirection::TowardMaximum),
                ]
            })
            .map(BodyEffectorTerminal::ordinal)
            .collect::<Vec<_>>();
        assert_eq!(
            ordinals,
            (0..BODY_EFFECTOR_TERMINAL_COUNT).collect::<Vec<_>>()
        );
    }

    #[test]
    fn tract_endings_append_without_moving_legacy_body_territory() {
        let legacy_last = BodyProprioceptorTerminal::new(
            BodyAxis::RightAnklePitch,
            BodyEffectorDirection::TowardMaximum,
        );
        assert_eq!(legacy_last.ordinal(), 73);
        assert_eq!(legacy_last.proprioceptor_topology_index(), 83);
        assert_eq!(legacy_last.load_topology_index(), 157);

        let tract_first = BodyProprioceptorTerminal::new(
            BodyAxis::VocalTractSection0Area,
            BodyEffectorDirection::TowardMinimum,
        );
        let tract_last = BodyProprioceptorTerminal::new(
            BodyAxis::VocalTractSection7Area,
            BodyEffectorDirection::TowardMaximum,
        );
        assert_eq!(tract_first.proprioceptor_topology_index(), 164);
        assert_eq!(tract_last.proprioceptor_topology_index(), 179);
        assert_eq!(tract_first.load_topology_index(), 180);
        assert_eq!(tract_last.load_topology_index(), 195);
    }

    #[test]
    fn quiescence_touches_no_axis_and_allocates_no_false_consequence() {
        let predecessor = ArticulatedBodyState::at_neutral();
        let transition =
            settle_body_effector_drives(&predecessor, &AdmittedBodyEffectorDrives::quiescent())
                .unwrap();
        assert_eq!(transition.successor, predecessor);
        assert_eq!(transition.reached_terminal_count, 0);
        assert!(transition.proprioceptive_consequences.is_empty());
    }

    #[test]
    fn sparse_terminal_drive_moves_only_its_axis_and_returns_exact_proprioception() {
        let predecessor = ArticulatedBodyState::at_neutral();
        let admitted = AdmittedBodyEffectorDrives::admit(vec![BodyEffectorDrive {
            terminal: BodyEffectorTerminal::new(
                BodyAxis::LeftEyeYaw,
                BodyEffectorDirection::TowardMaximum,
            ),
            outward_elementary_carriers: 127,
        }])
        .unwrap();
        let transition = settle_body_effector_drives(&predecessor, &admitted).unwrap();
        assert_eq!(transition.reached_terminal_count, 1);
        assert_eq!(transition.proprioceptive_consequences.len(), 1);
        assert_eq!(
            transition.successor.axis(BodyAxis::LeftEyeYaw),
            predecessor.axis(BodyAxis::LeftEyeYaw) + 127,
        );
        for axis in BODY_AXES {
            if axis != BodyAxis::LeftEyeYaw {
                assert_eq!(transition.successor.axis(axis), predecessor.axis(axis));
            }
        }
        assert_eq!(
            transition.proprioceptive_consequences[0],
            BodyProprioceptiveConsequence {
                axis: BodyAxis::LeftEyeYaw,
                unit: BodyAxisUnit::Millidegree,
                predecessor_position: 0,
                successor_position: 127,
                signed_displacement: 127,
                toward_minimum_carriers: 0,
                toward_maximum_carriers: 127,
                opposed_carriers_per_terminal: 0,
                applied_displacement_quanta: 127,
                stalled_carriers: 0,
            },
        );
    }

    #[test]
    fn sparse_tract_terminal_drive_moves_one_persisted_airway_section() {
        let predecessor = ArticulatedBodyState::at_neutral();
        let axis = BodyAxis::VocalTractSection3Area;
        let admitted = AdmittedBodyEffectorDrives::admit(vec![BodyEffectorDrive {
            terminal: BodyEffectorTerminal::new(
                axis,
                BodyEffectorDirection::TowardMaximum,
            ),
            outward_elementary_carriers: 7,
        }])
        .unwrap();
        let transition = settle_body_effector_drives(&predecessor, &admitted).unwrap();

        assert_eq!(transition.successor.axis(axis), predecessor.axis(axis) + 7);
        assert_eq!(
            transition.successor.vocal_tract_areas_square_millimetres()[3],
            predecessor.vocal_tract_areas_square_millimetres()[3] + 7,
        );
        for other in BODY_AXES {
            if other != axis {
                assert_eq!(transition.successor.axis(other), predecessor.axis(other));
            }
        }
        assert_eq!(transition.proprioceptive_consequences.len(), 1);
        assert_eq!(
            transition.proprioceptive_consequences[0].unit,
            BodyAxisUnit::SquareMillimetre,
        );
    }

    #[test]
    fn opposed_drive_cancels_locally_and_anatomical_stop_reports_stall() {
        let predecessor = ArticulatedBodyState::at_neutral();
        let opposed = AdmittedBodyEffectorDrives::admit(vec![
            BodyEffectorDrive {
                terminal: BodyEffectorTerminal::new(
                    BodyAxis::NeckYaw,
                    BodyEffectorDirection::TowardMinimum,
                ),
                outward_elementary_carriers: 30,
            },
            BodyEffectorDrive {
                terminal: BodyEffectorTerminal::new(
                    BodyAxis::NeckYaw,
                    BodyEffectorDirection::TowardMaximum,
                ),
                outward_elementary_carriers: 30,
            },
        ])
        .unwrap();
        let transition = settle_body_effector_drives(&predecessor, &opposed).unwrap();
        assert_eq!(transition.successor, predecessor);
        assert_eq!(
            transition.proprioceptive_consequences[0].opposed_carriers_per_terminal,
            30,
        );

        let beyond_stop = AdmittedBodyEffectorDrives::admit(vec![BodyEffectorDrive {
            terminal: BodyEffectorTerminal::new(
                BodyAxis::NeckYaw,
                BodyEffectorDirection::TowardMaximum,
            ),
            outward_elementary_carriers: 100_000,
        }])
        .unwrap();
        let transition = settle_body_effector_drives(&predecessor, &beyond_stop).unwrap();
        assert_eq!(
            transition.successor.axis(BodyAxis::NeckYaw),
            BodyAxis::NeckYaw.anatomy().maximum,
        );
        assert_eq!(
            transition.proprioceptive_consequences[0].stalled_carriers,
            25_000,
        );
    }

    #[test]
    fn drive_admission_refuses_duplicate_or_zero_terminal_work() {
        let terminal =
            BodyEffectorTerminal::new(BodyAxis::JawOpening, BodyEffectorDirection::TowardMaximum);
        assert_eq!(
            AdmittedBodyEffectorDrives::admit(vec![BodyEffectorDrive {
                terminal,
                outward_elementary_carriers: 0,
            }]),
            Err(ArticulatedBodyError::InvalidEffectorDrives),
        );
        assert_eq!(
            AdmittedBodyEffectorDrives::admit(vec![
                BodyEffectorDrive {
                    terminal,
                    outward_elementary_carriers: 1,
                },
                BodyEffectorDrive {
                    terminal,
                    outward_elementary_carriers: 2,
                },
            ]),
            Err(ArticulatedBodyError::InvalidEffectorDrives),
        );
    }
}
