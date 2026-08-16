//! One-way adapter from an admitted GLJSRC02 occurrence to closed UF v1.4.
//!
//! This boundary selects no ports, clocks, groups, relevance, or interpolation
//! rule.  It preserves the explicit occurrence order, converts the already
//! derived dimensionless rational coordinates to deterministic binary64, and
//! invokes the shared vector evaluator once.

use num_rational::BigRational;
use num_traits::{ToPrimitive, Zero};

use crate::joint_source_episode::{
    JointSourceOccurrenceView, JointSourcePortView, NativeJointSourceEpisode,
};
use crate::joint_uf_v1_4::{
    self, JointIntersampleLaw, JointUfCoordinateBounds, JointUfError, JointUfInput,
    JointUfPhysicalBounds, JointUfResult,
};

pub(crate) const SAMPLED_VOLUME_AND_RELEVANCE_PIECEWISE_LINEAR_PROFILE: &[u8] =
    b"guala.uf.v1.4.sampled_volume_and_relevance_piecewise_linear.v1";

#[derive(Clone, Debug, PartialEq)]
pub(crate) struct EvaluatedJointSourceOccurrence {
    pub(crate) port_indices: Vec<usize>,
    pub(crate) groups: Vec<Vec<usize>>,
    pub(crate) field: JointUfResult,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) enum JointUfSourceError {
    Unavailable(&'static str),
    NonFinite(&'static str),
    Physics(JointUfError),
}

/// The part of physical admission that GLJSRC02 does not carry.
///
/// Coordinate bounds remain source-authored: each one is derived from that
/// port's declared source interval and exact affine input map.  The maximum
/// causal interval is independent anatomy/environment authority and therefore
/// must be supplied explicitly; it is never learned from an occurrence.
#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) struct JointUfSourceAdmission {
    maximum_causal_interval: BigRational,
}

impl JointUfSourceAdmission {
    pub(crate) fn new(maximum_causal_interval: BigRational) -> Result<Self, JointUfSourceError> {
        if maximum_causal_interval <= BigRational::zero() {
            return Err(JointUfSourceError::Unavailable(
                "maximum admitted causal interval is not positive",
            ));
        }
        Ok(Self {
            maximum_causal_interval,
        })
    }
}

/// One exact source episode paired with the independently authored temporal
/// anatomy required to evaluate each of its declared occurrences.
///
/// GLJSRC02 remains unchanged source evidence.  This transient native
/// composite preserves an explicit one-to-one order between that evidence and
/// its environment/anatomy admission without deriving either from the other.
#[derive(Clone)]
pub(crate) struct AdmittedJointSourceEpisode {
    episode: NativeJointSourceEpisode,
    occurrence_admissions: Box<[JointUfSourceAdmission]>,
}

impl AdmittedJointSourceEpisode {
    pub(crate) fn new(
        episode: NativeJointSourceEpisode,
        ordered_admissions: Vec<(usize, JointUfSourceAdmission)>,
    ) -> Result<Self, JointUfSourceError> {
        let occurrence_count = episode.joint_source_occurrences().len();
        if occurrence_count == 0 {
            return Err(JointUfSourceError::Unavailable(
                "admitted joint source episode has no occurrence",
            ));
        }
        if ordered_admissions.len() != occurrence_count {
            return Err(JointUfSourceError::Unavailable(
                "joint source admission cardinality differs from source occurrences",
            ));
        }
        let mut occurrence_admissions = Vec::with_capacity(occurrence_count);
        for (expected_index, (occurrence_index, admission)) in
            ordered_admissions.into_iter().enumerate()
        {
            if occurrence_index != expected_index {
                return Err(JointUfSourceError::Unavailable(
                    "joint source admissions are not in exact occurrence order",
                ));
            }
            occurrence_admissions.push(admission);
        }
        Ok(Self {
            episode,
            occurrence_admissions: occurrence_admissions.into_boxed_slice(),
        })
    }

    pub(crate) fn episode(&self) -> &NativeJointSourceEpisode {
        &self.episode
    }

    pub(crate) fn occurrence_count(&self) -> usize {
        self.occurrence_admissions.len()
    }

    pub(crate) fn admission(&self, occurrence_index: usize) -> Option<&JointUfSourceAdmission> {
        self.occurrence_admissions.get(occurrence_index)
    }
}

/// Test-only fixture admission: every fixture episode authors its own
/// coordinate bounds, and every fixture occurrence's source times span at
/// most two units, so an explicit five-unit maximum causal interval admits
/// every fixture gate without changing any evaluated value.
#[cfg(test)]
pub(crate) fn admitted_fixture_episode(
    episode: &NativeJointSourceEpisode,
) -> AdmittedJointSourceEpisode {
    let ordered_admissions = (0..episode.joint_source_occurrences().len())
        .map(|occurrence_index| {
            (
                occurrence_index,
                JointUfSourceAdmission::new(BigRational::from_integer(5.into())).unwrap(),
            )
        })
        .collect();
    AdmittedJointSourceEpisode::new(episode.clone(), ordered_admissions).unwrap()
}

/// Pair one exact source episode with the caller's explicitly authored
/// temporal admissions: one maximum causal interval `(numerator,
/// denominator)` in source-time units per source occurrence, in exact
/// occurrence order. The interval is independent environment/anatomy
/// authority carried by the caller; it is never derived from the occurrence
/// itself.
pub(crate) fn admitted_episode_with_authored_intervals(
    episode: &NativeJointSourceEpisode,
    maximum_causal_intervals: &[(i64, i64)],
) -> Result<AdmittedJointSourceEpisode, String> {
    let ordered_admissions = maximum_causal_intervals
        .iter()
        .enumerate()
        .map(|(occurrence_index, (numerator, denominator))| {
            if *denominator == 0 {
                return Err(format!(
                    "authored admission {occurrence_index} has a zero denominator"
                ));
            }
            JointUfSourceAdmission::new(BigRational::new(
                num_bigint::BigInt::from(*numerator),
                num_bigint::BigInt::from(*denominator),
            ))
            .map(|admission| (occurrence_index, admission))
            .map_err(|error| format!("authored admission {occurrence_index} is invalid: {error:?}"))
        })
        .collect::<Result<Vec<_>, _>>()?;
    AdmittedJointSourceEpisode::new(episode.clone(), ordered_admissions)
        .map_err(|error| format!("{error:?}"))
}

fn intersample_law(profile: &[u8]) -> Result<JointIntersampleLaw, JointUfSourceError> {
    if profile == SAMPLED_VOLUME_AND_RELEVANCE_PIECEWISE_LINEAR_PROFILE {
        Ok(JointIntersampleLaw::SampledVolumeAndRelevancePiecewiseLinear)
    } else {
        Err(JointUfSourceError::Unavailable(
            "joint occurrence intersample law is not a recognized UF v1.4 law",
        ))
    }
}

fn binary64(value: &BigRational, label: &'static str) -> Result<f64, JointUfSourceError> {
    value
        .to_f64()
        .filter(|candidate| candidate.is_finite())
        .ok_or(JointUfSourceError::NonFinite(label))
}

fn build_input(
    ports: &[JointSourcePortView],
    occurrence: &JointSourceOccurrenceView,
) -> Result<JointUfInput, JointUfSourceError> {
    let law = intersample_law(&occurrence.joint_intersample_profile)?;
    if occurrence.port_indices.is_empty() || occurrence.source_times.len() < 2 {
        return Err(JointUfSourceError::Unavailable(
            "joint occurrence lacks a positive vector field",
        ));
    }
    let mut fields = Vec::with_capacity(occurrence.source_times.len());
    for frame in 0..occurrence.source_times.len() {
        let mut vector = Vec::with_capacity(occurrence.port_indices.len());
        for port_index in &occurrence.port_indices {
            let port = ports
                .get(*port_index)
                .ok_or(JointUfSourceError::Unavailable(
                    "joint occurrence references an absent source port",
                ))?;
            let coordinate =
                port.dimensionless_fields
                    .get(frame)
                    .ok_or(JointUfSourceError::Unavailable(
                        "joint occurrence source field changed cardinality",
                    ))?;
            vector.push(binary64(
                coordinate,
                "joint source coordinate is not finite binary64",
            )?);
        }
        fields.push(vector);
    }
    let relevance = occurrence
        .joint_relevances
        .iter()
        .map(|value| binary64(value, "joint relevance is not finite binary64"))
        .collect::<Result<Vec<_>, _>>()?;
    Ok(JointUfInput {
        times: occurrence.source_times.clone(),
        fields,
        relevance,
        intersample_law: law,
    })
}

fn build_physical_bounds(
    ports: &[JointSourcePortView],
    occurrence: &JointSourceOccurrenceView,
    admission: &JointUfSourceAdmission,
) -> Result<JointUfPhysicalBounds, JointUfSourceError> {
    if occurrence.port_indices.is_empty() {
        return Err(JointUfSourceError::Unavailable(
            "joint occurrence has no source coordinate bounds",
        ));
    }
    let mut coordinates = Vec::with_capacity(occurrence.port_indices.len());
    for port_index in &occurrence.port_indices {
        let port = ports
            .get(*port_index)
            .ok_or(JointUfSourceError::Unavailable(
                "joint occurrence references an absent source port",
            ))?;
        let mapped_source_min = &port.field_offset + &port.field_scale * &port.source_min;
        let mapped_source_max = &port.field_offset + &port.field_scale * &port.source_max;
        let (minimum, maximum) = if mapped_source_min <= mapped_source_max {
            (mapped_source_min, mapped_source_max)
        } else {
            (mapped_source_max, mapped_source_min)
        };
        coordinates.push(
            JointUfCoordinateBounds::new(
                binary64(&minimum, "joint coordinate minimum is not finite binary64")?,
                binary64(&maximum, "joint coordinate maximum is not finite binary64")?,
            )
            .map_err(JointUfSourceError::Physics)?,
        );
    }
    JointUfPhysicalBounds::new(coordinates, admission.maximum_causal_interval.clone())
        .map_err(JointUfSourceError::Physics)
}

fn evaluate_admitted_occurrence(
    ports: &[JointSourcePortView],
    occurrence: &JointSourceOccurrenceView,
    admission: &JointUfSourceAdmission,
) -> Result<JointUfResult, JointUfSourceError> {
    let input = build_input(ports, occurrence)?;
    let bounds = build_physical_bounds(ports, occurrence, admission)?;
    joint_uf_v1_4::evaluate_with_physical_bounds(input, bounds).map_err(JointUfSourceError::Physics)
}

pub(crate) fn evaluate_occurrence(
    _episode: &NativeJointSourceEpisode,
    _occurrence_index: usize,
) -> Result<EvaluatedJointSourceOccurrence, JointUfSourceError> {
    Err(JointUfSourceError::Unavailable(
        "explicit maximum admitted causal interval is required",
    ))
}

pub(crate) fn evaluate_occurrence_with_admission(
    episode: &NativeJointSourceEpisode,
    occurrence_index: usize,
    admission: &JointUfSourceAdmission,
) -> Result<EvaluatedJointSourceOccurrence, JointUfSourceError> {
    let occurrence = episode
        .joint_source_occurrences()
        .get(occurrence_index)
        .ok_or(JointUfSourceError::Unavailable(
            "joint source occurrence is absent",
        ))?;
    let field = evaluate_admitted_occurrence(episode.joint_source_ports(), occurrence, admission)?;
    Ok(EvaluatedJointSourceOccurrence {
        port_indices: occurrence.port_indices.clone(),
        groups: occurrence.groups.clone(),
        field,
    })
}

#[cfg(test)]
mod tests {
    use num_bigint::BigInt;

    use super::*;
    use crate::joint_source_episode::JointSourceCoordinate;
    use crate::neuron_source_anchor::tests::exact_episode;

    fn rational(numerator: i64, denominator: i64) -> BigRational {
        BigRational::new(BigInt::from(numerator), BigInt::from(denominator))
    }

    fn port(values: &[(i64, i64)]) -> JointSourcePortView {
        JointSourcePortView {
            sense: 0,
            topology_index: 0,
            body_proprioceptor_terminal: None,
            sensor_id: "retina".into(),
            substream_id: "pixel".into(),
            coordinates: vec![JointSourceCoordinate {
                axis_id: "receptor".into(),
                coordinate_id: "0".into(),
            }],
            physical_quantity: "light".into(),
            physical_unit: "normalized".into(),
            relevance_rule: "source-only".into(),
            relevance_origin: None,
            input_map_id: "derived-coordinate".into(),
            source_min: rational(-1, 1),
            source_max: rational(1, 1),
            field_offset: rational(0, 1),
            field_scale: rational(1, 1),
            input_map_profile: vec![1],
            input_map_group_receipt: [0; 32],
            source_times: vec![rational(0, 1), rational(1, 4), rational(1, 1)],
            exact_normalized_sources: values.iter().map(|(n, d)| rational(*n, *d)).collect(),
            reported_phase_turns: vec![rational(0, 1); values.len()],
            source_relevances: vec![rational(1, 1); values.len()],
            dimensionless_fields: values.iter().map(|(n, d)| rational(*n, *d)).collect(),
        }
    }

    fn occurrence(profile: &[u8]) -> JointSourceOccurrenceView {
        JointSourceOccurrenceView {
            port_indices: vec![0, 1],
            source_times: vec![rational(0, 1), rational(1, 4), rational(1, 1)],
            joint_intersample_profile: profile.to_vec(),
            groups: vec![vec![0], vec![1]],
            joint_relevance_profile: b"explicit-joint-r".to_vec(),
            joint_relevances: vec![rational(1, 2); 3],
            authority_receipt: [0; 32],
        }
    }

    #[test]
    fn explicit_occurrence_becomes_one_shared_vector_evaluation() {
        let ports = vec![
            port(&[(0, 1), (0, 1), (0, 1)]),
            port(&[(0, 1), (0, 1), (0, 1)]),
        ];
        let occurrence = occurrence(SAMPLED_VOLUME_AND_RELEVANCE_PIECEWISE_LINEAR_PROFILE);
        let input = build_input(&ports, &occurrence).unwrap();
        assert_eq!(input.times, occurrence.source_times);
        assert_eq!(input.fields, vec![vec![0.0, 0.0]; 3]);
        let admission = JointUfSourceAdmission::new(rational(1, 1)).unwrap();
        let bounds = build_physical_bounds(&ports, &occurrence, &admission).unwrap();
        let result = joint_uf_v1_4::evaluate_with_physical_bounds(input, bounds).unwrap();
        assert_eq!(result.sev.len(), 3);
        assert_eq!(result.gates.len(), 1);
        assert_eq!(result.gates[0].l1.tvr, [1.0, 0.0, 0.5]);
    }

    #[test]
    fn source_authored_affine_bounds_and_explicit_time_bound_are_required() {
        let mut descending = port(&[(0, 1), (0, 1), (0, 1)]);
        descending.source_min = rational(-1, 1);
        descending.source_max = rational(1, 1);
        descending.field_offset = rational(1, 1);
        descending.field_scale = rational(-1, 2);
        descending.dimensionless_fields = vec![rational(1, 1); 3];
        let ports = vec![descending, port(&[(0, 1), (0, 1), (0, 1)])];
        let occurrence = occurrence(SAMPLED_VOLUME_AND_RELEVANCE_PIECEWISE_LINEAR_PROFILE);

        let too_short = JointUfSourceAdmission::new(rational(1, 2)).unwrap();
        assert_eq!(
            evaluate_admitted_occurrence(&ports, &occurrence, &too_short),
            Err(JointUfSourceError::Physics(JointUfError::Unavailable(
                "gate exceeds declared maximum causal interval"
            )))
        );
        assert_eq!(
            JointUfSourceAdmission::new(rational(0, 1)),
            Err(JointUfSourceError::Unavailable(
                "maximum admitted causal interval is not positive"
            ))
        );
    }

    #[test]
    fn unknown_law_and_missing_coordinate_refuse_without_fallback() {
        let ports = vec![
            port(&[(0, 1), (0, 1), (0, 1)]),
            port(&[(0, 1), (0, 1), (0, 1)]),
        ];
        assert_eq!(
            build_input(&ports, &occurrence(b"unknown")),
            Err(JointUfSourceError::Unavailable(
                "joint occurrence intersample law is not a recognized UF v1.4 law"
            ))
        );

        let short_ports = vec![port(&[(0, 1), (0, 1)]), port(&[(0, 1), (0, 1), (0, 1)])];
        assert_eq!(
            build_input(
                &short_ports,
                &occurrence(SAMPLED_VOLUME_AND_RELEVANCE_PIECEWISE_LINEAR_PROFILE),
            ),
            Err(JointUfSourceError::Unavailable(
                "joint occurrence source field changed cardinality"
            ))
        );
    }

    #[test]
    fn admitted_episode_round_trips_exact_source_and_occurrence_admission() {
        let episode = exact_episode();
        let source_authority = episode.joint_source_authority_receipt();
        let admission = JointUfSourceAdmission::new(rational(5, 1)).unwrap();
        let admitted =
            AdmittedJointSourceEpisode::new(episode, vec![(0, admission.clone())]).unwrap();

        assert_eq!(admitted.occurrence_count(), 1);
        assert_eq!(
            admitted.episode().joint_source_authority_receipt(),
            source_authority
        );
        assert_eq!(admitted.admission(0), Some(&admission));
        assert_eq!(admitted.admission(1), None);
    }

    #[test]
    fn admitted_episode_refuses_missing_extra_or_reordered_authority() {
        assert_eq!(
            AdmittedJointSourceEpisode::new(exact_episode(), Vec::new()).err(),
            Some(JointUfSourceError::Unavailable(
                "joint source admission cardinality differs from source occurrences"
            ))
        );
        assert_eq!(
            AdmittedJointSourceEpisode::new(
                exact_episode(),
                vec![
                    (0, JointUfSourceAdmission::new(rational(1, 1)).unwrap()),
                    (1, JointUfSourceAdmission::new(rational(2, 1)).unwrap()),
                ],
            )
            .err(),
            Some(JointUfSourceError::Unavailable(
                "joint source admission cardinality differs from source occurrences"
            ))
        );
        assert_eq!(
            AdmittedJointSourceEpisode::new(
                exact_episode(),
                vec![(1, JointUfSourceAdmission::new(rational(1, 1)).unwrap())],
            )
            .err(),
            Some(JointUfSourceError::Unavailable(
                "joint source admissions are not in exact occurrence order"
            ))
        );
    }
}
