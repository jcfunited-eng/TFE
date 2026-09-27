//! Multi-Channel Frame Invariance and Observability Harness (Stage P1-C / C19)
//!
//! Unmounted native implementation under `native/guala_core` boundary.
//! Adheres to §4, §9, and §10 of GUALA_P0_LOCAL_LEARNING_A1_CORRECTED_2026-09-27.md:
//!
//! 1. Rigid body frame transformations: World (W) -> Body (B) -> Head (H) -> Eye (E).
//!    x_B = R_WB^T * (x_W - p_WB) is an independent oracle for test validation,
//!    NEVER a perceptual shortcut given to cognition.
//! 2. Multi-channel sensory transductions:
//!    - Retinal bearing angle in eye frame: beta = atan2(y, x)
//!    - Retinal subtended angular diameter: theta_size = 2 * atan(radius / distance)
//!    - Proprioceptive sensorimotor feedback: neck and body rotation
//! 3. C19 Frame-invariance validation:
//!    - Self-rotation: Body rotates by Delta theta in place, stationary world target.
//!      Retinal shift Delta beta = -Delta theta.
//!      Compensated bearing residual epsilon_bearing = Delta beta + Delta theta == 0.
//!    - External target motion: Target moves in world by Delta phi while body is stationary.
//!      Retinal shift Delta beta = Delta phi != 0, proprioception Delta theta = 0.
//!      Compensated bearing residual epsilon_bearing = Delta phi != 0.
//! 4. Corrected Observability Controls (§9):
//!    - Control 1 (In-place object rotation): Object rotates by 60 deg in place.
//!      Bearing residual epsilon_bearing == 0, but orientation changes (Delta psi != 0).
//!      Zero bearing residual != object stationary!
//!    - Control 2 (Radial translation along viewing ray): Target moves along view ray.
//!      Bearing angle unchanged (epsilon_bearing == 0), but apparent size changes (Delta theta_size != 0).
//!      Zero bearing residual != no object motion!
//!    - Control 3 (Missing evidence / FOV limit): Target outside optical cone or occluded
//!      yields SensedValue::Unavailable, NEVER a numeric zero reading.

use std::f64::consts::PI;

// ---------------------------------------------------------------------------
// 2D Vector and Pose Mechanics
// ---------------------------------------------------------------------------

#[derive(Debug, Clone, Copy, PartialEq)]
pub struct Vector2 {
    pub x: f64,
    pub y: f64,
}

impl Vector2 {
    #[inline]
    pub fn new(x: f64, y: f64) -> Self {
        Self { x, y }
    }

    #[inline]
    pub fn norm(&self) -> f64 {
        (self.x * self.x + self.y * self.y).sqrt()
    }

    #[inline]
    pub fn sub(&self, other: &Vector2) -> Vector2 {
        Vector2::new(self.x - other.x, self.y - other.y)
    }

    #[inline]
    pub fn add(&self, other: &Vector2) -> Vector2 {
        Vector2::new(self.x + other.x, self.y + other.y)
    }

    #[inline]
    pub fn rotate(&self, angle_rad: f64) -> Vector2 {
        let c = angle_rad.cos();
        let s = angle_rad.sin();
        Vector2::new(c * self.x - s * self.y, s * self.x + c * self.y)
    }

    #[inline]
    pub fn unrotate(&self, angle_rad: f64) -> Vector2 {
        // R^T * v = R(-angle) * v
        self.rotate(-angle_rad)
    }
}

#[derive(Debug, Clone, Copy, PartialEq)]
pub struct Pose2D {
    pub position: Vector2,
    pub orientation_rad: f64,
}

impl Pose2D {
    pub fn new(x: f64, y: f64, orientation_rad: f64) -> Self {
        Self {
            position: Vector2::new(x, y),
            orientation_rad: normalize_angle(orientation_rad),
        }
    }

    /// World-side oracle transformation:
    ///   x_B = R_WB^T * (x_W - p_WB)
    /// Independent test validation only (§6.4).
    #[inline]
    pub fn transform_point_to_local(&self, point_world: &Vector2) -> Vector2 {
        let diff = point_world.sub(&self.position);
        diff.unrotate(self.orientation_rad)
    }
}

/// Normalizes angle to (-PI, PI] radians.
#[inline]
pub fn normalize_angle(angle_rad: f64) -> f64 {
    let mut a = angle_rad % (2.0 * PI);
    if a <= -PI {
        a += 2.0 * PI;
    } else if a > PI {
        a -= 2.0 * PI;
    }
    a
}

// ---------------------------------------------------------------------------
// Sensory Observation State
// ---------------------------------------------------------------------------

#[derive(Debug, Clone, PartialEq)]
pub enum SensedValue<T> {
    Available(T),
    Unavailable { reason: String },
}

#[derive(Debug, Clone, PartialEq)]
pub struct RetinalPercept {
    /// Bearing angle of target in eye coordinate frame (-PI to PI) [rad].
    pub bearing_rad: f64,
    /// Apparent subtended angular diameter [rad].
    pub apparent_angular_size_rad: f64,
    /// Perceived target surface orientation in eye frame [rad].
    pub surface_aspect_rad: f64,
}

#[derive(Debug, Clone, PartialEq)]
pub struct ProprioceptiveFeedback {
    /// Absolute body trunk orientation in world frame [rad].
    pub body_heading_rad: f64,
    /// Neck joint yaw angle relative to body trunk [rad].
    pub neck_yaw_rad: f64,
    /// Eye gaze yaw angle relative to head [rad].
    pub eye_yaw_rad: f64,
}

impl ProprioceptiveFeedback {
    /// Total net gaze orientation relative to body:
    ///   theta_gaze_rel = neck_yaw + eye_yaw
    #[inline]
    pub fn total_relative_gaze_rad(&self) -> f64 {
        normalize_angle(self.neck_yaw_rad + self.eye_yaw_rad)
    }

    /// Total world-referenced sensor orientation:
    ///   theta_sensor = body_heading + neck_yaw + eye_yaw
    #[inline]
    pub fn total_sensor_heading_rad(&self) -> f64 {
        normalize_angle(self.body_heading_rad + self.neck_yaw_rad + self.eye_yaw_rad)
    }
}

// ---------------------------------------------------------------------------
// Multiframe Optical & Sensorimotor Observer
// ---------------------------------------------------------------------------

#[derive(Debug, Clone, PartialEq)]
pub struct PhysicalTarget {
    pub position: Vector2,
    pub radius_m: f64,
    pub internal_orientation_rad: f64,
}

#[derive(Debug, Clone, PartialEq)]
pub struct ObserverBody {
    pub body_pose: Pose2D,
    pub neck_yaw_rad: f64,
    pub eye_yaw_rad: f64,
    pub field_of_view_rad: f64,
}

impl ObserverBody {
    pub fn new(
        body_x: f64,
        body_y: f64,
        body_yaw_rad: f64,
        neck_yaw_rad: f64,
        eye_yaw_rad: f64,
        field_of_view_rad: f64,
    ) -> Self {
        Self {
            body_pose: Pose2D::new(body_x, body_y, body_yaw_rad),
            neck_yaw_rad: normalize_angle(neck_yaw_rad),
            eye_yaw_rad: normalize_angle(eye_yaw_rad),
            field_of_view_rad,
        }
    }

    /// Sensor frame origin and orientation in world coordinates:
    /// Eye is located at body origin with net heading = body_yaw + neck_yaw + eye_yaw.
    #[inline]
    pub fn sensor_pose(&self) -> Pose2D {
        let net_heading = self.body_pose.orientation_rad + self.neck_yaw_rad + self.eye_yaw_rad;
        Pose2D::new(
            self.body_pose.position.x,
            self.body_pose.position.y,
            net_heading,
        )
    }

    /// Reads proprioceptive sensorimotor feedback.
    pub fn read_proprioception(&self) -> ProprioceptiveFeedback {
        ProprioceptiveFeedback {
            body_heading_rad: self.body_pose.orientation_rad,
            neck_yaw_rad: self.neck_yaw_rad,
            eye_yaw_rad: self.eye_yaw_rad,
        }
    }

    /// Optical receptor observation of target with honest FOV boundary.
    /// Returns SensedValue::Unavailable if target is outside field of view.
    /// NEVER produces a numeric zero or false observation.
    pub fn observe_target(&self, target: &PhysicalTarget) -> SensedValue<RetinalPercept> {
        let sensor = self.sensor_pose();
        let target_in_eye = sensor.transform_point_to_local(&target.position);

        let distance = target_in_eye.norm();
        if distance <= target.radius_m {
            // Target is in contact or intersecting sensor origin
            return SensedValue::Unavailable {
                reason: "Target distance below physical aperture separation".to_string(),
            };
        }

        let bearing = target_in_eye.y.atan2(target_in_eye.x);

        // Check field-of-view limit (e.g. +/- 60 degrees)
        let half_fov = self.field_of_view_rad / 2.0;
        if bearing.abs() > half_fov {
            return SensedValue::Unavailable {
                reason: format!(
                    "Target bearing {:.3} rad exceeds optical FOV limit {:.3} rad",
                    bearing, half_fov
                ),
            };
        }

        // Apparent angular diameter: 2 * atan(radius / distance)
        let apparent_size = 2.0 * (target.radius_m / distance).atan();

        // Target surface aspect angle in eye coordinate frame
        let aspect = normalize_angle(target.internal_orientation_rad - sensor.orientation_rad);

        SensedValue::Available(RetinalPercept {
            bearing_rad: bearing,
            apparent_angular_size_rad: apparent_size,
            surface_aspect_rad: aspect,
        })
    }
}

// ---------------------------------------------------------------------------
// Relational Environmental Constancy Comparator (C19)
// ---------------------------------------------------------------------------

#[derive(Debug, Clone, PartialEq)]
pub struct RelationalObservation {
    pub retinal_bearing_rad: f64,
    pub apparent_angular_size_rad: f64,
    pub surface_aspect_rad: f64,
    pub sensor_heading_rad: f64,
}

#[derive(Debug, Clone, PartialEq)]
pub struct RelationalDifference {
    /// Apparent retinal shift: Delta beta_retinal = beta_1 - beta_0 [rad].
    pub delta_retinal_bearing_rad: f64,
    /// Total sensorimotor rotation change: Delta theta_sensor = theta_1 - theta_0 [rad].
    pub delta_sensor_heading_rad: f64,
    /// Compensated relational bearing residual:
    ///   epsilon_bearing = Delta beta_retinal + Delta theta_sensor
    ///   For pure observer rotation: epsilon_bearing == 0.
    ///   For world target motion: epsilon_bearing != 0.
    pub compensated_bearing_residual_rad: f64,
    /// Change in apparent subtended size: Delta theta_size [rad].
    pub delta_apparent_size_rad: f64,
    /// Change in perceived surface aspect: Delta aspect [rad].
    pub delta_surface_aspect_rad: f64,
}

impl RelationalDifference {
    pub fn compute(
        before: &RelationalObservation,
        after: &RelationalObservation,
    ) -> Self {
        let delta_retinal = normalize_angle(after.retinal_bearing_rad - before.retinal_bearing_rad);
        let delta_sensor = normalize_angle(after.sensor_heading_rad - before.sensor_heading_rad);
        let compensated_bearing = normalize_angle(delta_retinal + delta_sensor);
        let delta_size = after.apparent_angular_size_rad - before.apparent_angular_size_rad;
        let delta_aspect = normalize_angle(after.surface_aspect_rad - before.surface_aspect_rad);

        Self {
            delta_retinal_bearing_rad: delta_retinal,
            delta_sensor_heading_rad: delta_sensor,
            compensated_bearing_residual_rad: compensated_bearing,
            delta_apparent_size_rad: delta_size,
            delta_surface_aspect_rad: delta_aspect,
        }
    }
}

// ===========================================================================
// Tests: Stage P1-C / C19 Frame Invariance & Observability Verification
// ===========================================================================

#[cfg(test)]
mod tests {
    use super::*;

    const DEG_TO_RAD: f64 = PI / 180.0;
    const TURN_60_DEG_RAD: f64 = 60.0 * DEG_TO_RAD;

    #[test]
    fn test_c19_observer_rotation_compensation() {
        // Stationary target at (3.0 m, 0.0 m) in world
        let target = PhysicalTarget {
            position: Vector2::new(3.0, 0.0),
            radius_m: 0.15,
            internal_orientation_rad: 0.0,
        };

        // Initial observer: at origin, pointing along +X (heading = 0)
        let observer_t0 = ObserverBody::new(0.0, 0.0, 0.0, 0.0, 0.0, 120.0 * DEG_TO_RAD);
        let p0 = match observer_t0.observe_target(&target) {
            SensedValue::Available(p) => p,
            _ => panic!("Target must be observed at t0"),
        };
        let fb0 = observer_t0.read_proprioception();
        let obs0 = RelationalObservation {
            retinal_bearing_rad: p0.bearing_rad,
            apparent_angular_size_rad: p0.apparent_angular_size_rad,
            surface_aspect_rad: p0.surface_aspect_rad,
            sensor_heading_rad: fb0.total_sensor_heading_rad(),
        };

        // Observer rotates +60,000 mdeg (+60 degrees) in place
        let observer_t1 = ObserverBody::new(0.0, 0.0, TURN_60_DEG_RAD, 0.0, 0.0, 120.0 * DEG_TO_RAD);
        let p1 = match observer_t1.observe_target(&target) {
            SensedValue::Available(p) => p,
            _ => panic!("Target must be observed at t1"),
        };
        let fb1 = observer_t1.read_proprioception();
        let obs1 = RelationalObservation {
            retinal_bearing_rad: p1.bearing_rad,
            apparent_angular_size_rad: p1.apparent_angular_size_rad,
            surface_aspect_rad: p1.surface_aspect_rad,
            sensor_heading_rad: fb1.total_sensor_heading_rad(),
        };

        let diff = RelationalDifference::compute(&obs0, &obs1);

        // Retinal shift occurred: target moved by -60 degrees on retina
        assert!((diff.delta_retinal_bearing_rad - (-TURN_60_DEG_RAD)).abs() < 1e-12);
        // Sensor rotated by +60 degrees
        assert!((diff.delta_sensor_heading_rad - TURN_60_DEG_RAD).abs() < 1e-12);

        // COMPENSATED BEARING RESIDUAL MUST BE ZERO:
        // Observer rotation is fully compensated by neck/trunk proprioceptive change
        assert!(
            diff.compensated_bearing_residual_rad.abs() < 1e-12,
            "Compensated bearing residual must be 0 for pure self-rotation, got {}",
            diff.compensated_bearing_residual_rad
        );
        // Apparent size must remain unchanged (same distance)
        assert!(diff.delta_apparent_size_rad.abs() < 1e-12);
    }

    #[test]
    fn test_c19_environmental_target_displacement() {
        // Target initially at (3.0 m, 0.0 m)
        let target_t0 = PhysicalTarget {
            position: Vector2::new(3.0, 0.0),
            radius_m: 0.15,
            internal_orientation_rad: 0.0,
        };

        // Observer remains stationary at origin with heading 0
        let observer = ObserverBody::new(0.0, 0.0, 0.0, 0.0, 0.0, 120.0 * DEG_TO_RAD);
        let p0 = match observer.observe_target(&target_t0) {
            SensedValue::Available(p) => p,
            _ => panic!("Target must be observed at t0"),
        };
        let fb = observer.read_proprioception();
        let obs0 = RelationalObservation {
            retinal_bearing_rad: p0.bearing_rad,
            apparent_angular_size_rad: p0.apparent_angular_size_rad,
            surface_aspect_rad: p0.surface_aspect_rad,
            sensor_heading_rad: fb.total_sensor_heading_rad(),
        };

        // Target physically moves by +20 degrees in world on an arc: (3.0 * cos(20 deg), 3.0 * sin(20 deg))
        let target_angle = 20.0 * DEG_TO_RAD;
        let target_t1 = PhysicalTarget {
            position: Vector2::new(3.0 * target_angle.cos(), 3.0 * target_angle.sin()),
            radius_m: 0.15,
            internal_orientation_rad: 0.0,
        };

        let p1 = match observer.observe_target(&target_t1) {
            SensedValue::Available(p) => p,
            _ => panic!("Target must be observed at t1"),
        };
        let obs1 = RelationalObservation {
            retinal_bearing_rad: p1.bearing_rad,
            apparent_angular_size_rad: p1.apparent_angular_size_rad,
            surface_aspect_rad: p1.surface_aspect_rad,
            sensor_heading_rad: fb.total_sensor_heading_rad(),
        };

        let diff = RelationalDifference::compute(&obs0, &obs1);

        // Proprioception is zero (observer did not rotate)
        assert_eq!(diff.delta_sensor_heading_rad, 0.0);
        // Retinal shift is non-zero (+20 degrees)
        assert!((diff.delta_retinal_bearing_rad - target_angle).abs() < 1e-12);

        // COMPENSATED BEARING RESIDUAL MUST BE NON-ZERO (+20 degrees):
        assert!(
            (diff.compensated_bearing_residual_rad - target_angle).abs() < 1e-12,
            "Compensated bearing residual must be non-zero for target motion, got {}",
            diff.compensated_bearing_residual_rad
        );
    }

    #[test]
    fn test_observability_control_in_place_target_rotation() {
        // Target at (3.0 m, 0.0 m) rotates in place by 60 degrees (yaw = 60 deg)
        let target_t0 = PhysicalTarget {
            position: Vector2::new(3.0, 0.0),
            radius_m: 0.15,
            internal_orientation_rad: 0.0,
        };
        let target_t1 = PhysicalTarget {
            position: Vector2::new(3.0, 0.0), // Same position!
            radius_m: 0.15,
            internal_orientation_rad: TURN_60_DEG_RAD, // Rotated!
        };

        let observer = ObserverBody::new(0.0, 0.0, 0.0, 0.0, 0.0, 120.0 * DEG_TO_RAD);
        let p0 = match observer.observe_target(&target_t0) {
            SensedValue::Available(p) => p,
            _ => panic!("Obs 0"),
        };
        let p1 = match observer.observe_target(&target_t1) {
            SensedValue::Available(p) => p,
            _ => panic!("Obs 1"),
        };

        let fb = observer.read_proprioception();
        let obs0 = RelationalObservation {
            retinal_bearing_rad: p0.bearing_rad,
            apparent_angular_size_rad: p0.apparent_angular_size_rad,
            surface_aspect_rad: p0.surface_aspect_rad,
            sensor_heading_rad: fb.total_sensor_heading_rad(),
        };
        let obs1 = RelationalObservation {
            retinal_bearing_rad: p1.bearing_rad,
            apparent_angular_size_rad: p1.apparent_angular_size_rad,
            surface_aspect_rad: p1.surface_aspect_rad,
            sensor_heading_rad: fb.total_sensor_heading_rad(),
        };

        let diff = RelationalDifference::compute(&obs0, &obs1);

        // Bearing residual is zero: position did not translate
        assert!(diff.compensated_bearing_residual_rad.abs() < 1e-12);

        // A1 OBSERVABILITY PROOF:
        // Zero bearing residual != object stationary!
        // The surface aspect angle changed by exactly +60 degrees!
        assert!(
            (diff.delta_surface_aspect_rad - TURN_60_DEG_RAD).abs() < 1e-12,
            "Target rotation must be detected via surface aspect change: {}",
            diff.delta_surface_aspect_rad
        );
    }

    #[test]
    fn test_observability_control_radial_translation() {
        // Target translates directly along viewing ray from 4.0 m to 2.0 m
        let target_t0 = PhysicalTarget {
            position: Vector2::new(4.0, 0.0),
            radius_m: 0.20,
            internal_orientation_rad: 0.0,
        };
        let target_t1 = PhysicalTarget {
            position: Vector2::new(2.0, 0.0), // Closer along viewing ray
            radius_m: 0.20,
            internal_orientation_rad: 0.0,
        };

        let observer = ObserverBody::new(0.0, 0.0, 0.0, 0.0, 0.0, 120.0 * DEG_TO_RAD);
        let p0 = match observer.observe_target(&target_t0) {
            SensedValue::Available(p) => p,
            _ => panic!("Obs 0"),
        };
        let p1 = match observer.observe_target(&target_t1) {
            SensedValue::Available(p) => p,
            _ => panic!("Obs 1"),
        };

        let fb = observer.read_proprioception();
        let obs0 = RelationalObservation {
            retinal_bearing_rad: p0.bearing_rad,
            apparent_angular_size_rad: p0.apparent_angular_size_rad,
            surface_aspect_rad: p0.surface_aspect_rad,
            sensor_heading_rad: fb.total_sensor_heading_rad(),
        };
        let obs1 = RelationalObservation {
            retinal_bearing_rad: p1.bearing_rad,
            apparent_angular_size_rad: p1.apparent_angular_size_rad,
            surface_aspect_rad: p1.surface_aspect_rad,
            sensor_heading_rad: fb.total_sensor_heading_rad(),
        };

        let diff = RelationalDifference::compute(&obs0, &obs1);

        // Bearing residual is zero: target stayed on the viewing ray
        assert!(diff.compensated_bearing_residual_rad.abs() < 1e-12);

        // A1 OBSERVABILITY PROOF:
        // Zero bearing residual != no object motion!
        // Apparent angular size doubled as target approached from 4m to 2m:
        assert!(
            diff.delta_apparent_size_rad > 0.0,
            "Target radial movement must be detected via apparent size expansion: {}",
            diff.delta_apparent_size_rad
        );
        let expected_size_ratio = p1.apparent_angular_size_rad / p0.apparent_angular_size_rad;
        assert!(
            (expected_size_ratio - 2.0).abs() < 0.05,
            "Apparent size ratio should be ~2.0, got {}",
            expected_size_ratio
        );
    }

    #[test]
    fn test_observability_control_missing_evidence_outside_fov() {
        // Target at 90 degrees bearing (outside 60 deg half-FOV)
        let target = PhysicalTarget {
            position: Vector2::new(0.0, 3.0), // Along +Y, bearing = +90 deg
            radius_m: 0.15,
            internal_orientation_rad: 0.0,
        };

        let observer = ObserverBody::new(0.0, 0.0, 0.0, 0.0, 0.0, 100.0 * DEG_TO_RAD); // FOV = 100 deg (half-FOV = 50 deg)
        let percept = observer.observe_target(&target);

        // Honest boundary: MUST return Unavailable, NEVER a numeric zero or false percept
        match percept {
            SensedValue::Unavailable { reason } => {
                assert!(reason.contains("exceeds optical FOV limit"));
            }
            SensedValue::Available(_) => panic!("Target outside FOV must not return Available percept"),
        }
    }
}
