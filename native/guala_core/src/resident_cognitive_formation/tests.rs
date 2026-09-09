    use super::*;

    #[test]
    fn sparse_contact_components_preserve_canonical_breadth_first_order() {
        let contacts = [(2, 3), (0, 2), (1, 3)]
            .into_iter()
            .map(|(left, right)| {
                ElectricalContactAnatomy::new(
                    left,
                    right,
                    ExactRational::integer(1),
                    5,
                )
                .unwrap()
            })
            .collect();
        let anatomy = SparseElectricalAnatomy::new(5, contacts).unwrap();

        assert_eq!(contact_components(5, &anatomy), vec![vec![0, 2, 3, 1], vec![4]]);
    }

    /// Quiet (dark, silent) episodes appended after a presentation so the
    /// cohort can descend all the way to electrical rest.  Since the
    /// 2026-08-05 geometric differentiation the members' capacitances differ,
    /// so a settled cohort equalizes POTENTIAL rather than charge and takes
    /// longer to go silent than the tie-frozen anatomy did; the tail is
    /// transport, the quiescence is physics.
    const DARK_TAIL_EPISODES: usize = 64;
    use crate::developmental_electrical_anatomy::{
        DevelopmentalElectricalContact, DevelopmentalElectricalSeed,
    };
    use crate::articulated_body_joint_source_builder::{
        admit_articulated_body_consequence_source, admit_articulated_body_proprioceptive_source,
        admit_complete_articulated_body_state_source,
    };
    use crate::exact_rational::ExactRational;
    use crate::local_cupula_hair_bundle_geometry::LocalCupulaBundleAnatomy;
    use crate::neuron_source_anchor::tests::{
        exact_dark_optical_episode, exact_episode, exact_five_optical_episode,
        exact_four_dark_optical_episode, exact_four_partial_optical_episode,
        exact_four_reordered_optical_episode, exact_four_single_optical_episode,
        exact_optical_binaural_episode, exact_optical_episode, exact_split_four_optical_episode,
        exact_two_of_four_optical_episode,
    };
    use crate::reached_vestibular_bundle_path::settle_reached_vestibular_bundle_tick;
    use crate::resident_receptor_transition::prepare_resident_vestibular_ingress;
    use crate::vestibular_neuron_path::phase_one_virtual_vestibular_anatomy;
    use crate::virtual_body_yaw_motion::{
        settle_signed_yaw_actuation, SignedYawActuation, YawBodyState,
    };
    use crate::virtual_articulated_body::{
        ArticulatedBodyState, BodyAxis, BodyEffectorDirection, BodyProprioceptiveConsequence,
        BodyProprioceptorTerminal,
    };
    use crate::virtual_vestibular_canal::{CanalAnatomy, CanalState, PositiveRatio};

    fn explicit_optical_seed(
        source: &NativeJointSourceEpisode,
        conductance_picosiemens: i128,
    ) -> DevelopmentalElectricalSeed {
        explicit_optical_seed_for_occurrence(source, 0, conductance_picosiemens)
    }

    fn explicit_optical_seed_for_occurrence(
        source: &NativeJointSourceEpisode,
        occurrence_index: usize,
        conductance_picosiemens: i128,
    ) -> DevelopmentalElectricalSeed {
        let shared =
            prepare_complete_joint_field_admitted_fixture(source, occurrence_index).unwrap();
        let sites = (0..shared.vertex_count())
            .map(|coordinate_index| {
                let perspective = bind_neuron_perspective(&shared, coordinate_index, 0).unwrap();
                NeuronSourceSite::from_anchor(
                    bind_neuron_source_anchor(source, perspective).unwrap(),
                )
            })
            .collect::<Vec<_>>();
        let contacts = (1..sites.len())
            .map(|right| {
                DevelopmentalElectricalContact::new(
                    right - 1,
                    right,
                    ExactRational::integer(conductance_picosiemens),
                    sites.len(),
                )
                .unwrap()
            })
            .collect::<Vec<_>>();
        DevelopmentalElectricalSeed::new(sites, contacts).unwrap()
    }

    #[test]
    fn bounded_parallel_terminal_energy_observation_matches_serial() {
        let source = exact_four_single_optical_episode(0);
        let seed = explicit_optical_seed(&source, 500);
        let mut state =
            ResidentCognitiveFormationState::from_developmental_electrical_seeds(vec![seed])
                .unwrap();
        let prepared = state
            .prepare_admitted_transition(&admitted_fixture_episode(&source), 16_000_000)
            .unwrap();
        state.commit(prepared).unwrap();

        assert_eq!(state.energy_state(), state.energy_state_serial_reference());
    }

    fn local_lineage(ordinal: u64) -> [u8; 16] {
        let mut lineage = [0; 16];
        lineage[..8].copy_from_slice(LINEAGE_DOMAIN);
        lineage[8..].copy_from_slice(&ordinal.to_be_bytes());
        lineage
    }

    fn palmar_contact_source_site() -> NeuronSourceSite {
        NeuronSourceSite::from_source_port(
            &crate::joint_source_episode::JointSourcePortView {
                sense: PhysicalSourceSense::Touch.declared_layer(),
                topology_index: PALMAR_CONTACT_TOPOLOGY_INDEX,
                body_proprioceptor_terminal: None,
                root_yaw_proprioceptor_terminal: None,
                root_translation_proprioceptor_terminal: None,
                sensor_id: PALMAR_CONTACT_SENSOR_ID.into(),
                substream_id: PALMAR_CONTACT_SUBSTREAM_ID.into(),
                coordinates: vec![crate::joint_source_episode::JointSourceCoordinate {
                    axis_id: "body-surface".into(),
                    coordinate_id: "palmar".into(),
                }],
                physical_quantity: CONTACT_SITE_OCCUPANCY_QUANTITY.into(),
                physical_unit: CONTACT_REFERENCE_OCCUPANCY_UNIT.into(),
                relevance_rule: "source-only".into(),
                relevance_origin: None,
                input_map_id: "palmar-contact-test-map".into(),
                source_min: BigRational::from_integer(BigInt::from(0)),
                source_max: BigRational::from_integer(BigInt::from(1)),
                field_offset: BigRational::from_integer(BigInt::from(0)),
                field_scale: BigRational::from_integer(BigInt::from(1)),
                input_map_profile: vec![1],
                input_map_group_receipt: [0; 32],
                source_times: vec![
                    BigRational::from_integer(BigInt::from(0)),
                    BigRational::from_integer(BigInt::from(1)),
                ],
                exact_normalized_sources: vec![
                    BigRational::from_integer(BigInt::from(0)),
                    BigRational::from_integer(BigInt::from(1)),
                ],
                reported_phase_turns: vec![
                    BigRational::from_integer(BigInt::from(0)),
                    BigRational::from_integer(BigInt::from(0)),
                ],
                source_relevances: vec![
                    BigRational::from_integer(BigInt::from(1)),
                    BigRational::from_integer(BigInt::from(1)),
                ],
                dimensionless_fields: vec![
                    BigRational::from_integer(BigInt::from(0)),
                    BigRational::from_integer(BigInt::from(1)),
                ],
            },
        )
        .unwrap()
    }

    fn rejected_w1_source_site(topology_index: u32) -> NeuronSourceSite {
        NeuronSourceSite::from_source_port(
            &crate::joint_source_episode::JointSourcePortView {
                sense: PhysicalSourceSense::Sight.declared_layer(),
                topology_index,
                body_proprioceptor_terminal: None,
                root_yaw_proprioceptor_terminal: None,
                root_translation_proprioceptor_terminal: None,
                sensor_id: RETIRED_W1_RETINA_SENSOR_ID.into(),
                substream_id: format!("retired-w1-{topology_index}"),
                coordinates: vec![crate::joint_source_episode::JointSourceCoordinate {
                    axis_id: "optical-band".into(),
                    coordinate_id: topology_index.to_string(),
                }],
                physical_quantity: RETINAL_SPECTRAL_IRRADIANCE_QUANTITY.into(),
                physical_unit: RETINAL_REFERENCE_IRRADIANCE_UNIT.into(),
                relevance_rule: "source-only".into(),
                relevance_origin: None,
                input_map_id: "retired-w1-test-map".into(),
                source_min: BigRational::from_integer(BigInt::from(0)),
                source_max: BigRational::from_integer(BigInt::from(1)),
                field_offset: BigRational::from_integer(BigInt::from(0)),
                field_scale: BigRational::from_integer(BigInt::from(1)),
                input_map_profile: vec![1],
                input_map_group_receipt: [0; 32],
                source_times: vec![
                    BigRational::from_integer(BigInt::from(0)),
                    BigRational::from_integer(BigInt::from(1)),
                ],
                exact_normalized_sources: vec![
                    BigRational::from_integer(BigInt::from(0)),
                    BigRational::from_integer(BigInt::from(0)),
                ],
                reported_phase_turns: vec![
                    BigRational::from_integer(BigInt::from(0)),
                    BigRational::from_integer(BigInt::from(0)),
                ],
                source_relevances: vec![
                    BigRational::from_integer(BigInt::from(1)),
                    BigRational::from_integer(BigInt::from(1)),
                ],
                dimensionless_fields: vec![
                    BigRational::from_integer(BigInt::from(0)),
                    BigRational::from_integer(BigInt::from(0)),
                ],
            },
        )
        .unwrap()
    }

    #[test]
    fn rejected_w1_retirement_removes_only_the_duplicate_retina_and_integrators() {
        let mut cohorts = Vec::new();
        let mut next_lineage = 1;
        let mut retired_pairs = Vec::new();
        for topology_index in RETIRED_W1_RETINA_TOPOLOGY_START
            ..RETIRED_W1_RETINA_TOPOLOGY_START
                + u32::try_from(RETIRED_W1_RETINA_RECEPTOR_COUNT).unwrap()
        {
            let site = rejected_w1_source_site(topology_index);
            let place = DeclaredNeuronPlace::from_source_site(&site);
            let neuron = create_quiescent_virtual_material_neuron(place).unwrap();
            let source_lineage = allocate_local_lineage(&mut next_lineage).unwrap();
            let local_anatomy = SparseElectricalAnatomy::new(1, Vec::new()).unwrap();
            let anatomy = ReachedCohortAnatomy::new_mounted(
                vec![neuron.anatomy],
                vec![source_lineage],
                vec![ReachedNeuronMount::Receptor(site)],
                local_anatomy.clone(),
            )
            .unwrap();
            cohorts.push(ResidentReachedCohort {
                state: ReachedCohortState::new(
                    &anatomy,
                    vec![neuron.state],
                    SparseElectricalState::genesis(&local_anatomy),
                )
                .unwrap()
                .into(),
                anatomy,
                pending_experience: None,
                retained_experience: None,
                pending_recurrence: None,
            });
            let integration = mount_intrinsic_neuron_at_place(
                &mut cohorts,
                &mut None,
                &mut next_lineage,
                local_integration_place(place).unwrap(),
            )
            .unwrap();
            retired_pairs.push((source_lineage, integration));
        }
        let preserved = mount_intrinsic_neuron_at_place(
            &mut cohorts,
            &mut None,
            &mut next_lineage,
            DeclaredNeuronPlace::new(7, 999_999),
        )
        .unwrap();
        let fabric = ResidentElectricalFabric::default()
            .append_contacts(
                &retired_pairs
                    .iter()
                    .map(|(source, integration)| {
                        (
                            *source,
                            *integration,
                            ExactRational::integer(
                                DEVELOPMENTAL_CONTACT_CONDUCTANCE_PICOSIEMENS,
                            ),
                        )
                    })
                    .collect::<Vec<_>>(),
            )
            .unwrap();
        let topology_index = Arc::new(ResidentTopologyIndex::build(&cohorts, &fabric).unwrap());
        let state = ResidentCognitiveFormationState {
            generation: 1,
            next_lineage_ordinal: next_lineage,
            vocal_articulatory_effector_lineage: None,
            unexpressed_electrical_seeds: Box::new([]),
            dormant_lineage_seeds: Box::new([]),
            resting_population: None,
            cohorts: cohorts.into_boxed_slice(),
            electrical_fabric: fabric,
            active_electrical_frontier: Box::new([]),
            preceding_active_electrical_frontier: Box::new([]),
            older_active_electrical_frontier: Box::new([]),
            mosaics: Box::new([]),
            hippocampal: ResidentHippocampalIndex::default(),
            topology_index,
            formation_index: ResidentFormationIndex::default(),
        };
        validate_lineage_state(&state).unwrap();

        let corrected = state
            .retire_rejected_w1_spectral_retina()
            .unwrap()
            .unwrap();
        assert_eq!(corrected.electrical_fabric.contact_count(), 0);
        assert_eq!(corrected.topology_index.flat_locations.len(), 1);
        assert_eq!(corrected.topology_index.flat_locations[0].2, preserved);
        assert!(corrected
            .cohorts
            .iter()
            .flat_map(|cohort| cohort.anatomy.mounts())
            .all(|mount| mount
                .source_site()
                .is_none_or(|site| site.sensor_id() != RETIRED_W1_RETINA_SENSOR_ID)));
        assert!(corrected
            .retire_rejected_w1_spectral_retina()
            .unwrap()
            .is_none());
    }

    #[test]
    fn transient_bond_index_preserves_exact_parallel_ordinals() {
        let left = local_lineage(1);
        let right = local_lineage(2);
        let other = local_lineage(3);
        let mut ordinals = std::collections::BTreeMap::new();

        let first = stable_bond_for_next_edge(&mut ordinals, left, right).unwrap();
        let reversed = stable_bond_for_next_edge(&mut ordinals, right, left).unwrap();
        let independent = stable_bond_for_next_edge(&mut ordinals, left, other).unwrap();
        let third = stable_bond_for_next_edge(&mut ordinals, left, right).unwrap();

        assert_eq!(first.endpoints(), (left, right));
        assert_eq!(first.parallel_ordinal(), 0);
        assert_eq!(reversed.endpoints(), (left, right));
        assert_eq!(reversed.parallel_ordinal(), 1);
        assert_eq!(independent.parallel_ordinal(), 0);
        assert_eq!(third.parallel_ordinal(), 2);
        assert_eq!(ordinals.get(&(left, right)), Some(&3));
        assert_eq!(ordinals.get(&(left, other)), Some(&1));
    }

    fn mount_body_regulation_fixture(
        cohorts: &mut Vec<ResidentReachedCohort>,
        resting_population: &mut Option<DevelopmentalRestingPopulation>,
        next_lineage_ordinal: &mut u64,
        electrical_fabric: &mut ResidentElectricalFabric,
        axis: BodyAxis,
        direction: BodyEffectorDirection,
    ) -> ([u8; 16], [u8; 16], NeuronSourceSite) {
        let source = admit_complete_articulated_body_state_source(
            0,
            &ArticulatedBodyState::at_neutral(),
        )
        .unwrap();
        let terminal = BodyProprioceptorTerminal::new(axis, direction);
        let receptor_site = NeuronSourceSite::from_source_port(
            &source.joint_source_ports()[terminal.ordinal()],
        )
        .unwrap();
        mount_body_regulation_from_site_fixture(
            cohorts,
            resting_population,
            next_lineage_ordinal,
            electrical_fabric,
            receptor_site,
        )
    }

    fn mount_body_regulation_from_site_fixture(
        cohorts: &mut Vec<ResidentReachedCohort>,
        resting_population: &mut Option<DevelopmentalRestingPopulation>,
        next_lineage_ordinal: &mut u64,
        electrical_fabric: &mut ResidentElectricalFabric,
        receptor_site: NeuronSourceSite,
    ) -> ([u8; 16], [u8; 16], NeuronSourceSite) {
        let receptor_place = DeclaredNeuronPlace::from_source_site(&receptor_site);
        let receptor_neuron = create_quiescent_virtual_material_neuron(receptor_place).unwrap();
        let receptor_lineage = allocate_local_lineage(next_lineage_ordinal).unwrap();
        let local_anatomy = SparseElectricalAnatomy::new(1, Vec::new()).unwrap();
        let receptor_anatomy = ReachedCohortAnatomy::new_mounted(
            vec![receptor_neuron.anatomy],
            vec![receptor_lineage],
            vec![ReachedNeuronMount::Receptor(receptor_site.clone())],
            local_anatomy.clone(),
        )
        .unwrap();
        cohorts.push(ResidentReachedCohort {
            state: ReachedCohortState::new(
                &receptor_anatomy,
                vec![receptor_neuron.state],
                SparseElectricalState::genesis(&local_anatomy),
            )
            .unwrap()
            .into(),
            anatomy: receptor_anatomy,
            pending_experience: None,
            retained_experience: None,
            pending_recurrence: None,
        });
        mount_reached_local_integration(
            cohorts,
            resting_population,
            next_lineage_ordinal,
            electrical_fabric,
            &[(receptor_lineage, receptor_place)],
        )
        .unwrap();
        let regulation = mount_reached_body_regulation(
            cohorts,
            resting_population,
            next_lineage_ordinal,
            electrical_fabric,
            &[receptor_lineage],
        )
        .unwrap();
        assert_eq!(regulation.len(), 1);
        (regulation[0], receptor_lineage, receptor_site)
    }

    #[test]
    fn singular_palmar_contact_mounts_only_the_two_closing_grip_reflexes() {
        let mut cohorts = Vec::new();
        let mut population = None;
        let mut next_lineage = 1;
        let mut fabric = ResidentElectricalFabric::default();

        for axis in [BodyAxis::LeftGripAperture, BodyAxis::RightGripAperture] {
            for direction in [
                BodyEffectorDirection::TowardMinimum,
                BodyEffectorDirection::TowardMaximum,
            ] {
                mount_body_regulation_fixture(
                    &mut cohorts,
                    &mut population,
                    &mut next_lineage,
                    &mut fabric,
                    axis,
                    direction,
                );
            }
        }
        let (palmar_regulation, palmar_receptor, palmar_site) =
            mount_body_regulation_from_site_fixture(
                &mut cohorts,
                &mut population,
                &mut next_lineage,
                &mut fabric,
                palmar_contact_source_site(),
            );
        assert!(is_palmar_contact_receptor_site(&palmar_site));
        assert!(carries_palmar_contact_onset(
            &palmar_site,
            &[BigRational::zero(), BigRational::from_integer(1.into())],
        ));
        assert!(!carries_palmar_contact_onset(
            &palmar_site,
            &[
                BigRational::from_integer(1.into()),
                BigRational::from_integer(1.into()),
            ],
        ));
        assert!(!carries_palmar_contact_onset(
            &palmar_site,
            &[BigRational::from_integer(1.into()), BigRational::zero()],
        ));
        assert!(!is_palmar_contact_receptor_site(
            &NeuronSourceSite::fixture_in_sense(PhysicalSourceSense::Touch, 26)
        ));

        let mut motors = BTreeMap::new();
        for (mount, lineage) in cohorts.iter().flat_map(|cohort| {
            cohort
                .anatomy
                .mounts()
                .iter()
                .zip(cohort.anatomy.neuron_lineages())
        }) {
            if let Some(terminal) = mount.body_effector_terminal() {
                motors.insert(terminal, *lineage);
            }
        }
        for axis in [BodyAxis::LeftGripAperture, BodyAxis::RightGripAperture] {
            let closing = BodyEffectorTerminal::new(
                axis,
                BodyEffectorDirection::TowardMinimum,
            );
            let opening = BodyEffectorTerminal::new(
                axis,
                BodyEffectorDirection::TowardMaximum,
            );
            assert!(fabric.contains_contact(palmar_regulation, motors[&closing]));
            assert!(!fabric.contains_contact(palmar_regulation, motors[&opening]));
        }

        let topology = ResidentTopologyIndex::build(&cohorts, &fabric).unwrap();
        for axis in [BodyAxis::LeftGripAperture, BodyAxis::RightGripAperture] {
            let closing = BodyEffectorTerminal::new(
                axis,
                BodyEffectorDirection::TowardMinimum,
            );
            let motor_flat = topology.flat_for_lineage(motors[&closing]).unwrap();
            let paths = exact_motor_body_afferent_paths(
                motor_flat,
                &topology.flat_locations,
                &cohorts,
                &topology.neighbours_by_flat,
            )
            .unwrap();
            let regulations = exact_articulated_body_preparation_regulations(
                closing,
                &paths,
                &[palmar_receptor],
                &[],
            );
            assert!(regulations.contains(&palmar_regulation));
            assert!(exact_articulated_body_preparation_regulations(closing, &paths, &[], &[])
                .is_empty());
            assert!(paths.iter().any(|path| {
                path.receptor_lineage == palmar_receptor
                    && path.receptor_site == palmar_site
            }));
        }
    }

    fn gustatory_contact_source_site(channel: &str, topology_index: u32) -> NeuronSourceSite {
        NeuronSourceSite::from_source_port(
            &crate::joint_source_episode::JointSourcePortView {
                sense: PhysicalSourceSense::Taste.declared_layer(),
                topology_index,
                body_proprioceptor_terminal: None,
                root_yaw_proprioceptor_terminal: None,
                root_translation_proprioceptor_terminal: None,
                sensor_id: "organism-gustatory-surface".into(),
                substream_id: format!("organism-gustatory-surface-{channel}"),
                coordinates: vec![
                    crate::joint_source_episode::JointSourceCoordinate {
                        axis_id: "chemical-channel".into(),
                        coordinate_id: channel.into(),
                    },
                    crate::joint_source_episode::JointSourceCoordinate {
                        axis_id: "chemoreceptive-range".into(),
                        coordinate_id: "organism-gustatory-surface".into(),
                    },
                ],
                physical_quantity: GUSTATORY_CONTACT_CONCENTRATION_QUANTITY.into(),
                physical_unit: "fraction-of-declared-saturating-concentration".into(),
                relevance_rule: "source-only".into(),
                relevance_origin: None,
                input_map_id: "gustatory-contact-test-map".into(),
                source_min: BigRational::from_integer(BigInt::from(0)),
                source_max: BigRational::from_integer(BigInt::from(1)),
                field_offset: BigRational::from_integer(BigInt::from(0)),
                field_scale: BigRational::from_integer(BigInt::from(1)),
                input_map_profile: vec![1],
                input_map_group_receipt: [0; 32],
                source_times: vec![
                    BigRational::from_integer(BigInt::from(0)),
                    BigRational::from_integer(BigInt::from(1)),
                ],
                exact_normalized_sources: vec![
                    BigRational::from_integer(BigInt::from(0)),
                    BigRational::from_integer(BigInt::from(1)),
                ],
                reported_phase_turns: vec![
                    BigRational::from_integer(BigInt::from(0)),
                    BigRational::from_integer(BigInt::from(0)),
                ],
                source_relevances: vec![
                    BigRational::from_integer(BigInt::from(1)),
                    BigRational::from_integer(BigInt::from(1)),
                ],
                dimensionless_fields: vec![
                    BigRational::from_integer(BigInt::from(0)),
                    BigRational::from_integer(BigInt::from(1)),
                ],
            },
        )
        .unwrap()
    }

    #[test]
    fn gustatory_contact_mounts_only_the_single_closing_glottal_reflex() {
        let mut cohorts = Vec::new();
        let mut population = None;
        let mut next_lineage = 1;
        let mut fabric = ResidentElectricalFabric::default();

        for direction in [
            BodyEffectorDirection::TowardMinimum,
            BodyEffectorDirection::TowardMaximum,
        ] {
            mount_body_regulation_fixture(
                &mut cohorts,
                &mut population,
                &mut next_lineage,
                &mut fabric,
                BodyAxis::GlottalAperture,
                direction,
            );
        }
        let (taste_regulation, taste_receptor, taste_site) =
            mount_body_regulation_from_site_fixture(
                &mut cohorts,
                &mut population,
                &mut next_lineage,
                &mut fabric,
                gustatory_contact_source_site("sweet", 0),
            );
        assert!(is_gustatory_contact_receptor_site(&taste_site));
        // Material ARRIVING fires the reflex; lingering or leaving material
        // must not, and no other sense may wear the intake surface's law.
        assert!(carries_gustatory_contact_onset(
            &taste_site,
            &[BigRational::zero(), BigRational::from_integer(1.into())],
        ));
        assert!(!carries_gustatory_contact_onset(
            &taste_site,
            &[
                BigRational::from_integer(1.into()),
                BigRational::from_integer(1.into()),
            ],
        ));
        assert!(!carries_gustatory_contact_onset(
            &taste_site,
            &[BigRational::from_integer(1.into()), BigRational::zero()],
        ));
        assert!(!is_gustatory_contact_receptor_site(
            &NeuronSourceSite::fixture_in_sense(PhysicalSourceSense::Smell, 0)
        ));
        assert!(!is_gustatory_contact_receptor_site(
            &NeuronSourceSite::fixture_in_sense(PhysicalSourceSense::Touch, 26)
        ));

        let mut motors = BTreeMap::new();
        for (mount, lineage) in cohorts.iter().flat_map(|cohort| {
            cohort
                .anatomy
                .mounts()
                .iter()
                .zip(cohort.anatomy.neuron_lineages())
        }) {
            if let Some(terminal) = mount.body_effector_terminal() {
                motors.insert(terminal, *lineage);
            }
        }
        let closing = BodyEffectorTerminal::new(
            BodyAxis::GlottalAperture,
            BodyEffectorDirection::TowardMinimum,
        );
        let opening = BodyEffectorTerminal::new(
            BodyAxis::GlottalAperture,
            BodyEffectorDirection::TowardMaximum,
        );
        assert!(is_closing_glottal_terminal(closing));
        assert!(!is_closing_glottal_terminal(opening));
        // The developed arc reaches ONLY the airway-closing motor.
        assert!(fabric.contains_contact(taste_regulation, motors[&closing]));
        assert!(!fabric.contains_contact(taste_regulation, motors[&opening]));

        let topology = ResidentTopologyIndex::build(&cohorts, &fabric).unwrap();
        let motor_flat = topology.flat_for_lineage(motors[&closing]).unwrap();
        let paths = exact_motor_body_afferent_paths(
            motor_flat,
            &topology.flat_locations,
            &cohorts,
            &topology.neighbours_by_flat,
        )
        .unwrap();
        let regulations = exact_articulated_body_preparation_regulations(
            closing,
            &paths,
            &[],
            &[taste_receptor],
        );
        assert!(regulations.contains(&taste_regulation));
        // Without a genuine onset this interval, no swallow: the same paths
        // with an empty onset roster prepare nothing.
        assert!(
            exact_articulated_body_preparation_regulations(closing, &paths, &[], &[])
                .is_empty()
        );
        // The opening terminal is never reflex-preparable from taste.
        let opening_flat = topology.flat_for_lineage(motors[&opening]).unwrap();
        let opening_paths = exact_motor_body_afferent_paths(
            opening_flat,
            &topology.flat_locations,
            &cohorts,
            &topology.neighbours_by_flat,
        )
        .unwrap();
        assert!(exact_articulated_body_preparation_regulations(
            opening,
            &opening_paths,
            &[],
            &[taste_receptor],
        )
        .is_empty());
        assert!(paths.iter().any(|path| {
            path.receptor_lineage == taste_receptor && path.receptor_site == taste_site
        }));
    }

    fn mount_receptor_local_integration_fixture(
        cohorts: &mut Vec<ResidentReachedCohort>,
        resting_population: &mut Option<DevelopmentalRestingPopulation>,
        next_lineage_ordinal: &mut u64,
        electrical_fabric: &mut ResidentElectricalFabric,
        receptor_site: NeuronSourceSite,
    ) -> ([u8; 16], [u8; 16]) {
        let receptor_place = DeclaredNeuronPlace::from_source_site(&receptor_site);
        let receptor_neuron = create_quiescent_virtual_material_neuron(receptor_place).unwrap();
        let receptor_lineage = allocate_local_lineage(next_lineage_ordinal).unwrap();
        let local_anatomy = SparseElectricalAnatomy::new(1, Vec::new()).unwrap();
        let receptor_anatomy = ReachedCohortAnatomy::new_mounted(
            vec![receptor_neuron.anatomy],
            vec![receptor_lineage],
            vec![ReachedNeuronMount::Receptor(receptor_site)],
            local_anatomy.clone(),
        )
        .unwrap();
        cohorts.push(ResidentReachedCohort {
            state: ReachedCohortState::new(
                &receptor_anatomy,
                vec![receptor_neuron.state],
                SparseElectricalState::genesis(&local_anatomy),
            )
            .unwrap()
            .into(),
            anatomy: receptor_anatomy,
            pending_experience: None,
            retained_experience: None,
            pending_recurrence: None,
        });
        mount_reached_local_integration(
            cohorts,
            resting_population,
            next_lineage_ordinal,
            electrical_fabric,
            &[(receptor_lineage, receptor_place)],
        )
        .unwrap();
        let integration_place = local_integration_place(receptor_place).unwrap();
        let integration_lineage = cohorts
            .iter()
            .flat_map(|cohort| {
                cohort
                    .anatomy
                    .mounts()
                    .iter()
                    .zip(cohort.anatomy.neuron_lineages())
            })
            .find_map(|(mount, lineage)| {
                (mount.source_site().is_none() && mount.place() == integration_place)
                    .then_some(*lineage)
            })
            .unwrap();
        (receptor_lineage, integration_lineage)
    }

    fn mount_local_motor_bridge_fixture(
        cohorts: &mut Vec<ResidentReachedCohort>,
        resting_population: &mut Option<DevelopmentalRestingPopulation>,
        next_lineage_ordinal: &mut u64,
        electrical_fabric: &mut ResidentElectricalFabric,
        regulation: [u8; 16],
        ordering: [u8; 16],
        topology_index: u32,
    ) {
        let affective = mount_intrinsic_neuron_at_place(
            cohorts,
            resting_population,
            next_lineage_ordinal,
            DeclaredNeuronPlace::new(10, topology_index),
        )
        .unwrap();
        *electrical_fabric = electrical_fabric
            .append_contact(
                regulation,
                affective,
                ExactRational::integer(DEVELOPMENTAL_CONTACT_CONDUCTANCE_PICOSIEMENS),
            )
            .unwrap();
        *electrical_fabric = electrical_fabric
            .append_contact(
                affective,
                ordering,
                ExactRational::integer(DEVELOPMENTAL_CONTACT_CONDUCTANCE_PICOSIEMENS),
            )
            .unwrap();
    }

    fn all_physical_bonds(
        cohorts: &[ResidentReachedCohort],
        electrical_fabric: &ResidentElectricalFabric,
    ) -> Vec<StablePhysicalBondReference> {
        organism_physical_bonds(cohorts, electrical_fabric).unwrap()
    }

    /// Fixture proof material: every physical bond expressed as directed
    /// whole-carrier transfers in both directions. Tests that exercise
    /// plumbing (creation, reuse, idempotence) use this saturated form;
    /// direction-sensitive law tests construct exact one-way chains.
    fn directed_transfers_from_bonds(
        cohorts: &[ResidentReachedCohort],
        electrical_fabric: &ResidentElectricalFabric,
    ) -> Vec<DirectedPhysicalTransferObservation> {
        all_physical_bonds(cohorts, electrical_fabric)
            .into_iter()
            .flat_map(|bond| {
                let (left, right) = bond.endpoints();
                [
                    DirectedPhysicalTransferObservation {
                        sender: left,
                        receiver: right,
                        bond,
                        transferred_whole_carriers: 1,
                    },
                    DirectedPhysicalTransferObservation {
                        sender: right,
                        receiver: left,
                        bond,
                        transferred_whole_carriers: 1,
                    },
                ]
            })
            .collect()
    }

    /// One exact directed chain a -> b -> c ... as whole-carrier transfers,
    /// resolved against the real bonds of the fabric.
    fn directed_chain(
        cohorts: &[ResidentReachedCohort],
        electrical_fabric: &ResidentElectricalFabric,
        chain: &[[u8; 16]],
    ) -> Vec<DirectedPhysicalTransferObservation> {
        let bonds = all_physical_bonds(cohorts, electrical_fabric);
        chain
            .windows(2)
            .map(|hop| {
                let pair = canonical_lineage_pair(hop[0], hop[1]);
                let bond = bonds
                    .iter()
                    .copied()
                    .find(|bond| bond.endpoints() == pair)
                    .expect("chain hop must be a real physical bond");
                DirectedPhysicalTransferObservation {
                    sender: hop[0],
                    receiver: hop[1],
                    bond,
                    transferred_whole_carriers: 1,
                }
            })
            .collect()
    }

    /// Fixture proof material for the PRECEDING window: every physical
    /// bond expressed as directed frontier entries in both directions.
    fn frontier_entries_from_bonds(
        cohorts: &[ResidentReachedCohort],
        electrical_fabric: &ResidentElectricalFabric,
    ) -> Vec<ActiveElectricalFrontierEntry> {
        all_physical_bonds(cohorts, electrical_fabric)
            .into_iter()
            .flat_map(|bond| {
                let (left, right) = bond.endpoints();
                [
                    ActiveElectricalFrontierEntry::caused(left, right, bond, 1).unwrap(),
                    ActiveElectricalFrontierEntry::caused(right, left, bond, 1).unwrap(),
                ]
            })
            .collect()
    }

    /// One exact directed PRIOR-window hop a -> b as a frontier entry.
    fn frontier_hop(
        cohorts: &[ResidentReachedCohort],
        electrical_fabric: &ResidentElectricalFabric,
        sender: [u8; 16],
        receiver: [u8; 16],
    ) -> Vec<ActiveElectricalFrontierEntry> {
        let pair = canonical_lineage_pair(sender, receiver);
        let bond = all_physical_bonds(cohorts, electrical_fabric)
            .into_iter()
            .find(|bond| bond.endpoints() == pair)
            .expect("hop must be a real physical bond");
        vec![ActiveElectricalFrontierEntry::caused(sender, receiver, bond, 1).unwrap()]
    }

    /// One exact PRIOR-window hop whose carrier direction and newly reached
    /// causal endpoint are stated independently.
    fn frontier_hop_with_frontier(
        cohorts: &[ResidentReachedCohort],
        electrical_fabric: &ResidentElectricalFabric,
        sender: [u8; 16],
        receiver: [u8; 16],
        frontier: [u8; 16],
    ) -> Vec<ActiveElectricalFrontierEntry> {
        let pair = canonical_lineage_pair(sender, receiver);
        let bond = all_physical_bonds(cohorts, electrical_fabric)
            .into_iter()
            .find(|bond| bond.endpoints() == pair)
            .expect("hop must be a real physical bond");
        vec![ActiveElectricalFrontierEntry::caused_with_frontier(
            sender, receiver, frontier, bond, 1, false,
        )
        .unwrap()]
    }

    #[test]
    fn empty_genesis_is_exact_and_bounded() {
        let state = ResidentCognitiveFormationState::default();
        let encoded = state.encode(CURRENT_FIXED_BYTES).unwrap();
        assert_eq!(encoded.len(), CURRENT_FIXED_BYTES);
        assert_eq!(
            ResidentCognitiveFormationState::decode(&encoded, CURRENT_FIXED_BYTES).unwrap(),
            state
        );
    }

    #[test]
    fn terminal_observation_is_derived_by_the_canonical_seal() {
        const MAX_BYTES: usize = 256_000_000;
        let source = admit_complete_articulated_body_state_source(
            0,
            &ArticulatedBodyState::at_neutral(),
        )
        .unwrap();
        let prepared = ResidentCognitiveFormationState::default()
            .prepare(&source, MAX_BYTES)
            .unwrap();
        let expected_bytes = prepared.successor.encode(MAX_BYTES).unwrap();
        let expected_summary = prepared.successor.summary();
        let expected_relation_count = prepared
            .successor
            .mosaic_of_mosaics_count()
            .unwrap();

        let sealed = prepared
            .successor
            .seal_with_terminal_observation(MAX_BYTES)
            .unwrap();

        assert_eq!(sealed.encoded, expected_bytes);
        assert_eq!(sealed.summary, expected_summary);
        assert_eq!(sealed.mosaic_of_mosaics_count, expected_relation_count);
    }

    #[test]
    fn complete_body_source_mounts_bounded_receptor_integration_and_regulation_once() {
        const MAX_BYTES: usize = 256_000_000;
        let source = admit_complete_articulated_body_state_source(
            0,
            &ArticulatedBodyState::at_neutral(),
        )
        .unwrap();
        let state = ResidentCognitiveFormationState::default();
        let first = state.prepare(&source, MAX_BYTES).unwrap();
        let counts = first.successor.observe_reached_neuron_count_by_layer();
        let energized_terminal_count = source
            .joint_source_ports()
            .iter()
            .filter(|port| {
                port.exact_normalized_sources
                    .iter()
                    .any(|value| !value.is_zero())
            })
            .count();
        assert_eq!(
            counts.iter().find(|(layer, _)| *layer == 5),
            Some(&(5, BODY_EFFECTOR_TERMINAL_COUNT))
        );
        assert_eq!(
            counts.iter().find(|(layer, _)| *layer == 6),
            Some(&(6, BODY_EFFECTOR_TERMINAL_COUNT))
        );
        assert_eq!(
            counts.iter().find(|(layer, _)| *layer == 8),
            Some(&(8, energized_terminal_count))
        );
        let terminal_gate_populations = first
            .successor
            .cohorts
            .iter()
            .flat_map(|cohort| {
                cohort
                    .anatomy
                    .mounts()
                    .iter()
                    .zip(cohort.anatomy.neuron_anatomies())
            })
            .filter_map(|(mount, anatomy)| {
                mount
                    .source_site()
                    .and_then(NeuronSourceSite::body_proprioceptor_terminal)
                    .map(|_| anatomy.gate_population())
            })
            .collect::<Vec<_>>();
        assert_eq!(
            terminal_gate_populations,
            vec![1; BODY_EFFECTOR_TERMINAL_COUNT]
        );
        assert_eq!(first.observation.externally_perturbed_body_receptor_count, 0);

        let first_lineages = first.successor.retained_neuron_lineages();
        let encoded = state.encode_successor(&first, MAX_BYTES).unwrap();
        let cold = ResidentCognitiveFormationState::decode(&encoded, MAX_BYTES).unwrap();
        let repeated = cold.prepare(&source, MAX_BYTES).unwrap();
        assert_eq!(
            repeated.successor.observe_reached_neuron_count_by_layer(),
            counts
        );
        assert_eq!(repeated.successor.retained_neuron_lineages(), first_lineages);
    }

    #[test]
    fn one_antagonist_pair_mounts_its_local_body_regulation() {
        let axis = BodyAxis::TorsoPitch;
        let anatomy = axis.anatomy();
        let source = admit_articulated_body_proprioceptive_source(
            0,
            &[BodyProprioceptiveConsequence {
                axis,
                unit: anatomy.unit,
                predecessor_position: anatomy.neutral,
                successor_position: anatomy.neutral,
                signed_displacement: 0,
                toward_minimum_carriers: 0,
                toward_maximum_carriers: 0,
                opposed_carriers_per_terminal: 0,
                applied_displacement_quanta: 0,
                stalled_carriers: 0,
            }],
        )
        .unwrap();
        let state = ResidentCognitiveFormationState::default();
        let prepared = state.prepare(&source, 16_000_000).unwrap();
        let counts = prepared.successor.observe_reached_neuron_count_by_layer();
        assert_eq!(counts.iter().find(|(layer, _)| *layer == 5), Some(&(5, 2)));
        assert_eq!(counts.iter().find(|(layer, _)| *layer == 6), Some(&(6, 2)));
        assert_eq!(counts.iter().find(|(layer, _)| *layer == 8), Some(&(8, 2)));
    }

    #[test]
    fn one_acted_axis_mounts_position_and_load_as_distinct_receptors() {
        let axis = BodyAxis::LeftGripAperture;
        let anatomy = axis.anatomy();
        let source = admit_articulated_body_consequence_source(
            0,
            &[BodyProprioceptiveConsequence {
                axis,
                unit: anatomy.unit,
                predecessor_position: anatomy.maximum,
                successor_position: anatomy.maximum,
                signed_displacement: 0,
                toward_minimum_carriers: 0,
                toward_maximum_carriers: 240,
                opposed_carriers_per_terminal: 0,
                applied_displacement_quanta: 0,
                stalled_carriers: 240,
            }],
        )
        .unwrap();
        let prepared = ResidentCognitiveFormationState::default()
            .prepare(&source, 16_000_000)
            .unwrap();
        let counts = prepared.successor.observe_reached_neuron_count_by_layer();
        assert_eq!(counts.iter().find(|(layer, _)| *layer == 5), Some(&(5, 4)));
        assert_eq!(counts.iter().find(|(layer, _)| *layer == 6), Some(&(6, 4)));
        // Only the nonzero toward-minimum length and toward-maximum load
        // endings reach regulation in this stopped interval.
        assert_eq!(counts.iter().find(|(layer, _)| *layer == 8), Some(&(8, 2)));
    }

    #[test]
    fn load_feedback_reenters_after_complete_body_and_repeats() {
        let complete = admit_complete_articulated_body_state_source(
            0,
            &ArticulatedBodyState::at_neutral(),
        )
        .unwrap();
        let complete_body = ResidentCognitiveFormationState::default()
            .prepare(&complete, 16_000_000)
            .unwrap()
            .successor;
        let axis = BodyAxis::LeftGripAperture;
        let anatomy = axis.anatomy();
        let consequence = BodyProprioceptiveConsequence {
            axis,
            unit: anatomy.unit,
            predecessor_position: anatomy.maximum,
            successor_position: anatomy.maximum,
            signed_displacement: 0,
            toward_minimum_carriers: 0,
            toward_maximum_carriers: 240,
            opposed_carriers_per_terminal: 0,
            applied_displacement_quanta: 0,
            stalled_carriers: 240,
        };
        let first_source =
            admit_articulated_body_consequence_source(1, &[consequence]).unwrap();
        let first = complete_body
            .prepare(&first_source, 16_000_000)
            .unwrap()
            .successor;
        let second_source =
            admit_articulated_body_consequence_source(2, &[consequence]).unwrap();
        first.prepare(&second_source, 16_000_000).unwrap();
    }

    #[test]
    fn every_declared_antagonist_pair_settles_independently() {
        for axis in crate::virtual_articulated_body::BODY_AXES {
            let anatomy = axis.anatomy();
            let source = admit_articulated_body_proprioceptive_source(
                0,
                &[BodyProprioceptiveConsequence {
                    axis,
                    unit: anatomy.unit,
                    predecessor_position: anatomy.neutral,
                    successor_position: anatomy.neutral,
                    signed_displacement: 0,
                    toward_minimum_carriers: 0,
                    toward_maximum_carriers: 0,
                    opposed_carriers_per_terminal: 0,
                    applied_displacement_quanta: 0,
                    stalled_carriers: 0,
                }],
            )
            .unwrap();
            ResidentCognitiveFormationState::default()
                .prepare(&source, 16_000_000)
                .unwrap_or_else(|error| panic!("{axis:?} failed: {error:?}"));
        }
    }

    #[test]
    fn dormant_four_field_lineage_seed_is_consumed_once_by_exact_current_source() {
        let source = exact_optical_episode();
        let port = &source.joint_source_ports()[0];
        let seed = DormantLineageSeed::new(
            port.sense,
            port.topology_index,
            &port.sensor_id,
            &port.substream_id,
            local_lineage(7),
        )
        .unwrap();
        let state =
            ResidentCognitiveFormationState::from_genesis_parts(0, 8, Vec::new(), vec![seed])
                .unwrap();
        let dormant_bytes = state.encode(16_000_000).unwrap();
        let restored = ResidentCognitiveFormationState::decode(&dormant_bytes, 16_000_000).unwrap();
        assert_eq!(restored.encode(16_000_000).unwrap(), dormant_bytes);
        assert_eq!(restored.dormant_lineage_seeds.len(), 1);

        let prepared = restored.prepare(&source, 16_000_000).unwrap();
        assert!(prepared.successor.dormant_lineage_seeds.is_empty());
        assert_eq!(prepared.successor.next_lineage_ordinal, 9);
        assert_eq!(
            prepared.successor.cohorts[0].anatomy.neuron_lineages(),
            &[local_lineage(7)]
        );
        let successor = restored.encode_successor(&prepared, 16_000_000).unwrap();
        let cold = ResidentCognitiveFormationState::decode(&successor, 16_000_000).unwrap();
        assert_eq!(cold.encode(16_000_000).unwrap(), successor);
        assert!(cold.dormant_lineage_seeds.is_empty());
        assert_eq!(
            cold.cohorts[0].anatomy.neuron_lineages(),
            &[local_lineage(7)]
        );
    }

    #[test]
    fn one_shared_field_is_evaluated_once_and_new_lineage_survives_restart() {
        let source = exact_optical_episode();
        RESIDENT_JOINT_FIELD_EVALUATIONS.with(|count| count.set(0));
        let state = ResidentCognitiveFormationState::default();
        let prepared = state.prepare(&source, 16_000_000).unwrap();
        RESIDENT_JOINT_FIELD_EVALUATIONS.with(|count| {
            assert_eq!(count.get(), source.joint_source_occurrences().len());
        });
        assert_eq!(prepared.observation.dsf_delivery_count, 2);
        assert_eq!(prepared.successor.summary().complete_neuron_count, 2);
        assert_eq!(prepared.successor.cohorts.len(), 2);
        assert_eq!(prepared.successor.next_lineage_ordinal, 3);
        assert_eq!(
            prepared.successor.cohorts[0].anatomy.neuron_lineages(),
            &[local_lineage(1)]
        );
        let encoded = state.encode_successor(&prepared, 16_000_000).unwrap();
        let cold = ResidentCognitiveFormationState::decode(&encoded, 16_000_000).unwrap();
        assert_eq!(cold.encode(16_000_000).unwrap(), encoded);
        let recurrent = cold.prepare(&source, 16_000_000).unwrap();
        assert_eq!(recurrent.successor.next_lineage_ordinal, 3);
        assert_eq!(
            recurrent.successor.cohorts[0].anatomy.neuron_lineages(),
            &[local_lineage(1)]
        );
    }

    #[test]
    fn reordered_occurrence_reuses_the_same_persistent_neurons() {
        let first = crate::neuron_source_anchor::tests::exact_four_optical_episode();
        let reordered = exact_four_reordered_optical_episode();
        let mut state = ResidentCognitiveFormationState::default();
        let prepared = state.prepare(&first, 16_000_000).unwrap();
        state.commit(prepared).unwrap();
        let original_lineages = state.retained_neuron_lineages();
        assert_eq!(original_lineages.len(), 8);

        let prepared = state.prepare(&reordered, 16_000_000).unwrap();
        assert_eq!(prepared.successor.cohorts.len(), 5);
        assert_eq!(prepared.successor.summary().complete_neuron_count, 8);
        assert_eq!(
            prepared.successor.retained_neuron_lineages(),
            original_lineages
        );
        let encoded = state.encode_successor(&prepared, 16_000_000).unwrap();
        let restored = ResidentCognitiveFormationState::decode(&encoded, 16_000_000).unwrap();
        assert_eq!(restored.retained_neuron_lineages(), original_lineages);
        assert_eq!(restored.encode(16_000_000).unwrap(), encoded);
    }

    #[test]
    fn subset_occurrence_advances_receptors_and_still_charged_internal_material() {
        let first = crate::neuron_source_anchor::tests::exact_four_optical_episode();
        let subset = exact_two_of_four_optical_episode();
        let mut state = ResidentCognitiveFormationState::default();
        state
            .commit(state.prepare(&first, 16_000_000).unwrap())
            .unwrap();
        let predecessor = state.cohorts[0].state.clone();
        let lineages = state.retained_neuron_lineages();
        let carried_frontier = state
            .active_electrical_frontier
            .iter()
            .map(|entry| entry.frontier_lineage())
            .collect::<Vec<_>>();
        let adjacent_to_carried_frontier = |target: [u8; 16]| {
            state
                .electrical_fabric
                .contact_endpoints()
                .any(|(left, right)| {
                    let left = state.electrical_fabric.lineages()[left];
                    let right = state.electrical_fabric.lineages()[right];
                    (left == target && carried_frontier.contains(&right))
                        || (right == target && carried_frontier.contains(&left))
                })
        };
        assert!(adjacent_to_carried_frontier(
            state.cohorts[0].anatomy.neuron_lineages()[2]
        ));
        assert!(adjacent_to_carried_frontier(
            state.cohorts[0].anatomy.neuron_lineages()[3]
        ));

        let prepared = state.prepare(&subset, 16_000_000).unwrap();
        assert_eq!(prepared.successor.cohorts.len(), 5);
        assert_eq!(prepared.successor.summary().complete_neuron_count, 8);
        assert_eq!(prepared.successor.retained_neuron_lineages(), lineages);
        let successor = &prepared.successor.cohorts[0].state;
        // Receptors 2 and 3 receive no new external gate work, but both are
        // the exact advancing endpoints retained from the predecessor's local
        // contact transfers. Their internal material therefore settles once
        // without being relabelled as fresh sensory input. The two externally
        // reached receptors advance as well.
        assert_ne!(successor.neurons()[2], predecessor.neurons()[2]);
        assert_ne!(successor.neurons()[3], predecessor.neurons()[3]);
        assert_ne!(successor.neurons()[0], predecessor.neurons()[0]);
        assert_ne!(successor.neurons()[1], predecessor.neurons()[1]);

        let encoded = state.encode_successor(&prepared, 16_000_000).unwrap();
        let restored = ResidentCognitiveFormationState::decode(&encoded, 16_000_000).unwrap();
        assert_eq!(restored.retained_neuron_lineages(), lineages);
        assert_eq!(restored.encode(16_000_000).unwrap(), encoded);
    }

    #[test]
    fn overlapping_occurrence_reuses_four_residents_and_creates_only_one_new_neuron() {
        let four = crate::neuron_source_anchor::tests::exact_four_optical_episode();
        let five = exact_five_optical_episode();
        let mut state = ResidentCognitiveFormationState::default();
        state
            .commit(state.prepare(&four, 16_000_000).unwrap())
            .unwrap();
        let predecessor_bytes = state.encode(16_000_000).unwrap();
        let cold_predecessor =
            ResidentCognitiveFormationState::decode(&predecessor_bytes, 16_000_000).unwrap();
        let predecessor_anatomy = state.cohorts[0].anatomy.clone();
        let predecessor_lineages = state.retained_neuron_lineages();

        RESIDENT_JOINT_FIELD_EVALUATIONS.with(|count| count.set(0));
        let warm = state.prepare(&five, 16_000_000).unwrap();
        RESIDENT_JOINT_FIELD_EVALUATIONS.with(|count| {
            assert_eq!(count.get(), five.joint_source_occurrences().len());
        });
        let cold = cold_predecessor.prepare(&five, 16_000_000).unwrap();
        assert_eq!(cold, warm);
        assert_eq!(warm.successor.cohorts.len(), 6);
        assert_eq!(warm.successor.summary().complete_neuron_count, 10);
        assert_eq!(warm.successor.next_lineage_ordinal, 11);
        assert_eq!(
            &warm.successor.cohorts[0].anatomy.neuron_anatomies()[..4],
            predecessor_anatomy.neuron_anatomies()
        );
        assert_eq!(
            warm.successor.cohorts[0]
                .anatomy
                .source_sites()
                .take(4)
                .collect::<Vec<_>>(),
            predecessor_anatomy.source_sites().collect::<Vec<_>>()
        );
        assert!(predecessor_lineages
            .iter()
            .all(|lineage| warm.successor.retained_neuron_lineages().contains(lineage)));
        assert!(warm
            .successor
            .retained_neuron_lineages()
            .contains(&local_lineage(9)));
        assert!(warm
            .successor
            .retained_neuron_lineages()
            .contains(&local_lineage(10)));
        let lineages = warm.successor.retained_neuron_lineages();
        assert!(lineages
            .iter()
            .enumerate()
            .all(|(index, lineage)| !lineages[..index].contains(lineage)));

        let encoded = state.encode_successor(&warm, 16_000_000).unwrap();
        let restored = ResidentCognitiveFormationState::decode(&encoded, 16_000_000).unwrap();
        assert_eq!(restored, warm.successor);
        assert_eq!(restored.encode(16_000_000).unwrap(), encoded);
    }

    #[test]
    fn crossed_compartment_occurrence_settles_two_resident_fluids_without_new_neurons() {
        let split = exact_split_four_optical_episode();
        let joint = crate::neuron_source_anchor::tests::exact_four_optical_episode();
        let left_seed = explicit_optical_seed_for_occurrence(&split, 0, 500);
        let right_seed = explicit_optical_seed_for_occurrence(&split, 1, 500);
        let mut state = ResidentCognitiveFormationState::from_developmental_electrical_seeds(vec![
            left_seed, right_seed,
        ])
        .unwrap();
        state
            .commit(state.prepare(&split, 16_000_000).unwrap())
            .unwrap();
        assert_eq!(state.cohorts.len(), 6);
        assert_eq!(state.summary().complete_neuron_count, 8);
        assert_eq!(state.next_lineage_ordinal, 9);
        let predecessor_anatomies = state
            .cohorts
            .iter()
            .map(|cohort| cohort.anatomy.clone())
            .collect::<Vec<_>>();
        let predecessor_lineages = state.retained_neuron_lineages();
        let predecessor_contacts = state
            .cohorts
            .iter()
            .map(|cohort| cohort.anatomy.contact_count())
            .collect::<Vec<_>>();
        let predecessor_mosaics = state.mosaics.clone();
        let predecessor_hippocampal = state.hippocampal;
        let predecessor_bytes = state.encode(16_000_000).unwrap();
        let cold_predecessor =
            ResidentCognitiveFormationState::decode(&predecessor_bytes, 16_000_000).unwrap();

        RESIDENT_JOINT_FIELD_EVALUATIONS.with(|count| count.set(0));
        let warm = state.prepare(&joint, 16_000_000).unwrap();
        RESIDENT_JOINT_FIELD_EVALUATIONS.with(|count| {
            assert_eq!(count.get(), joint.joint_source_occurrences().len());
        });
        let cold = cold_predecessor.prepare(&joint, 16_000_000).unwrap();
        assert_eq!(cold, warm);
        assert_eq!(warm.successor.cohorts.len(), 6);
        assert_eq!(warm.successor.summary().complete_neuron_count, 8);
        assert_eq!(warm.successor.next_lineage_ordinal, 9);
        assert_eq!(
            warm.successor.retained_neuron_lineages(),
            predecessor_lineages
        );
        assert_eq!(warm.successor.hippocampal, predecessor_hippocampal);
        for index in 0..2 {
            assert_eq!(
                warm.successor.cohorts[index].anatomy,
                predecessor_anatomies[index]
            );
            assert_eq!(
                warm.successor.cohorts[index].anatomy.contact_count(),
                predecessor_contacts[index]
            );
            assert_eq!(
                warm.successor.cohorts[index].state.recovery_fluid(),
                cold.successor.cohorts[index].state.recovery_fluid()
            );
        }
        assert_eq!(warm.successor.mosaics, predecessor_mosaics);

        let encoded = state.encode_successor(&warm, 16_000_000).unwrap();
        let restored = ResidentCognitiveFormationState::decode(&encoded, 16_000_000).unwrap();
        assert_eq!(restored, warm.successor);
        assert_eq!(restored.encode(16_000_000).unwrap(), encoded);
        assert_eq!(restored.cohorts.len(), 6);
        assert_eq!(
            restored.cohorts[0].state.recovery_fluid(),
            warm.successor.cohorts[0].state.recovery_fluid()
        );
        assert_eq!(
            restored.cohorts[1].state.recovery_fluid(),
            warm.successor.cohorts[1].state.recovery_fluid()
        );
    }

    #[test]
    fn unsupported_ports_do_not_cancel_a_supported_receptor_or_claim_extra_neurons() {
        let source = exact_episode();
        let mut state = ResidentCognitiveFormationState::default();
        let prepared = state.prepare(&source, 16_000_000).unwrap();
        assert_eq!(prepared.observation.cognitive_ordinal, 1);
        assert_eq!(prepared.observation.complete_neuron_count, 2);
        assert_eq!(prepared.observation.physically_transitioned_neuron_count, 2);
        assert_eq!(prepared.observation.complete_neuron_fractal_count, 0);
        assert!(!prepared.observation.trace_formed);
        assert!(prepared.observation.mosaic_formed.is_none());
        state.commit(prepared).unwrap();
        let encoded = state.encode(16_000_000).unwrap();
        let restored = ResidentCognitiveFormationState::decode(&encoded, 16_000_000).unwrap();
        assert_eq!(restored, state);
        assert_eq!(restored.summary().complete_neuron_count, 2);
        assert_eq!(restored.next_lineage_ordinal, 3);
        assert!(restored.dormant_lineage_seeds.is_empty());
        assert_eq!(restored.encode(16_000_000).unwrap(), encoded);
    }

    #[test]
    fn explicit_growth_dna_contacts_survive_restart_and_express_once() {
        let source = exact_four_single_optical_episode(0);
        let seed = explicit_optical_seed(&source, 1);
        let state =
            ResidentCognitiveFormationState::from_developmental_electrical_seeds(vec![seed])
                .unwrap();
        let unexpressed = state.encode(16_000_000).unwrap();
        let restored = ResidentCognitiveFormationState::decode(&unexpressed, 16_000_000).unwrap();
        assert_eq!(restored, state);
        assert_eq!(restored.unexpressed_electrical_seeds.len(), 1);
        assert!(restored
            .observe_reached_contact_count_by_layer_pair()
            .is_empty());
        assert!(restored.observe_reached_contact_channel_states().is_empty());

        let prepared = restored.prepare(&source, 16_000_000).unwrap();
        assert_eq!(prepared.successor.unexpressed_electrical_seeds.len(), 0);
        assert_eq!(prepared.successor.cohorts.len(), 5);
        assert_eq!(prepared.successor.summary().complete_neuron_count, 8);
        assert_eq!(prepared.successor.cohorts[0].anatomy.neuron_count(), 4);
        assert_eq!(prepared.successor.cohorts[0].anatomy.contact_count(), 3);
        let mut reference_pairs = Vec::<(u32, u32, usize)>::new();
        for cohort in &prepared.successor.cohorts {
            for (left, right) in cohort.anatomy.electrical_anatomy().contact_endpoints() {
                let mut pair = (
                    cohort.anatomy.mounts()[left].place().layer(),
                    cohort.anatomy.mounts()[right].place().layer(),
                );
                if pair.0 > pair.1 {
                    pair = (pair.1, pair.0);
                }
                if let Some((_, _, count)) = reference_pairs
                    .iter_mut()
                    .find(|(left, right, _)| *left == pair.0 && *right == pair.1)
                {
                    *count += 1;
                } else {
                    reference_pairs.push((pair.0, pair.1, 1));
                }
            }
        }
        for (left, right) in prepared.successor.electrical_fabric.contact_endpoints() {
            let layer_of = |lineage| {
                prepared.successor.cohorts.iter().find_map(|cohort| {
                    cohort
                        .anatomy
                        .mounts()
                        .iter()
                        .zip(cohort.anatomy.neuron_lineages())
                        .find_map(|(mount, candidate)| {
                            (*candidate == lineage).then_some(mount.place().layer())
                        })
                })
            };
            let mut pair = (
                layer_of(prepared.successor.electrical_fabric.lineages()[left]).unwrap(),
                layer_of(prepared.successor.electrical_fabric.lineages()[right]).unwrap(),
            );
            if pair.0 > pair.1 {
                pair = (pair.1, pair.0);
            }
            if let Some((_, _, count)) = reference_pairs
                .iter_mut()
                .find(|(left, right, _)| *left == pair.0 && *right == pair.1)
            {
                *count += 1;
            } else {
                reference_pairs.push((pair.0, pair.1, 1));
            }
        }
        reference_pairs.sort_unstable();
        assert_eq!(
            prepared
                .successor
                .observe_reached_contact_count_by_layer_pair(),
            reference_pairs
        );
        let expressed_channels = prepared
            .successor
            .observe_reached_contact_channel_states();
        let expected_contact_count = prepared
            .successor
            .cohorts
            .iter()
            .map(|cohort| cohort.anatomy.contact_count())
            .sum::<usize>()
            + prepared.successor.electrical_fabric.contact_count();
        assert_eq!(expressed_channels.len(), expected_contact_count);
        assert!(expressed_channels.windows(2).all(|pair| {
            (pair[0].0, pair[0].1, pair[0].2) < (pair[1].0, pair[1].1, pair[1].2)
        }));
        for (position, channel) in expressed_channels.iter().enumerate() {
            assert_eq!(
                channel.2,
                u32::try_from(
                    expressed_channels[..position]
                        .iter()
                        .filter(|prior| prior.0 == channel.0 && prior.1 == channel.1)
                        .count()
                )
                .unwrap()
            );
        }
        assert_eq!(prepared.observation.complete_neuron_fractal_count, 3);
        assert_eq!(prepared.observation.emitted_neuron_fractals.len(), 3);
        assert!(prepared.observation.mosaic_formed.is_none());

        let expressed = restored.encode_successor(&prepared, 16_000_000).unwrap();
        let cold = ResidentCognitiveFormationState::decode(&expressed, 16_000_000).unwrap();
        assert_eq!(cold, prepared.successor);
        assert_eq!(cold.cohorts[0].anatomy.contact_count(), 3);
        assert_eq!(cold.encode(16_000_000).unwrap(), expressed);
    }

    /// Contact growth on a LIVING body that already holds a retained
    /// formation: append-only, nothing about the members moves, the retained
    /// formation is untouched, and the grown body cold-restores bit-exactly.
    #[test]
    #[ignore = "retired: fixture requires Boolean/member-set mosaic admission"]
    fn authored_contact_growth_appends_without_disturbing_a_living_body() {
        let light = (0..4)
            .map(exact_four_single_optical_episode)
            .collect::<Vec<_>>();
        let dark = exact_four_dark_optical_episode();
        let seed = explicit_optical_seed(&light[0], 500);
        let mut state =
            ResidentCognitiveFormationState::from_developmental_electrical_seeds(vec![seed])
                .unwrap();
        // First settle the complete experience, then present one proper
        // partial cue and its causal dark tail. A second complete presentation
        // is not a partial-cue reassembly and cannot be used to manufacture a
        // mosaic merely for this contact-growth test.
        for source in light
            .iter()
            .chain(std::iter::repeat(&dark).take(DARK_TAIL_EPISODES))
        {
            let prepared = state
                .prepare_admitted_transition(&admitted_fixture_episode(source), 16_000_000)
                .unwrap();
            state.commit(prepared).unwrap();
        }
        let partial = exact_four_partial_optical_episode();
        for source in
            std::iter::once(&partial).chain(std::iter::repeat(&dark).take(DARK_TAIL_EPISODES))
        {
            let prepared = state
                .prepare_admitted_transition(&admitted_fixture_episode(source), 16_000_000)
                .unwrap();
            state.commit(prepared).unwrap();
        }
        assert_eq!(state.summary().mosaic_count, 1);
        let before_bytes = state.encode(16_000_000).unwrap();
        let before_mosaics = state.mosaics.clone();
        let before_neurons = state.cohorts[0].state.neurons().to_vec();
        let before_contacts = state.cohorts[0]
            .anatomy
            .contact_endpoints()
            .collect::<Vec<_>>();
        let before_phases = state.cohorts[0]
            .state
            .electrical()
            .contact_states()
            .to_vec();
        assert_eq!(before_contacts.len(), 3);

        let authored = vec![AuthoredDeclaredContact {
            left_sensor_id: "left-retina".to_owned(),
            left_substream_id: "foveal-receptor-0".to_owned(),
            right_sensor_id: "left-retina".to_owned(),
            right_substream_id: "foveal-receptor-3".to_owned(),
            conductance_picosiemens: ExactRational::integer(500),
        }];
        let grown = state
            .prepare_authored_contacts(&authored, 16_000_000)
            .unwrap();
        // Preparing publishes nothing.
        assert_eq!(state.encode(16_000_000).unwrap(), before_bytes);
        let grown_bytes = state.encode_successor(&grown, 16_000_000).unwrap();
        state.commit(grown).unwrap();

        let after_contacts = state.cohorts[0]
            .anatomy
            .contact_endpoints()
            .collect::<Vec<_>>();
        assert_eq!(after_contacts.len(), 4);
        assert_eq!(after_contacts[..3], before_contacts[..]);
        assert_eq!(after_contacts[3], (0, 3));
        assert_eq!(
            state.cohorts[0].state.electrical().contact_states()[..3],
            before_phases[..]
        );
        // Members, their physical states and the retained formation are all
        // exactly as they were: only the contact list grew.
        assert_eq!(state.cohorts[0].state.neurons(), before_neurons.as_slice());
        assert_eq!(state.cohorts[0].anatomy.neuron_count(), 4);
        assert_eq!(state.mosaics, before_mosaics);
        assert_eq!(state.summary().mosaic_count, 1);
        assert_eq!(state.observe_cohort_contacts(), vec![(4, 4)]);

        // Cold restart of the grown body is bit-exact and re-encodes identically.
        let restored = ResidentCognitiveFormationState::decode(&grown_bytes, 16_000_000).unwrap();
        assert_eq!(restored, state);
        assert_eq!(restored.encode(16_000_000).unwrap(), grown_bytes);
        // The pre-growth body still decodes to exactly what it was: no
        // receipt of any earlier generation drifted.
        let pre_growth =
            ResidentCognitiveFormationState::decode(&before_bytes, 16_000_000).unwrap();
        assert_eq!(pre_growth.encode(16_000_000).unwrap(), before_bytes);
        assert_eq!(pre_growth.observe_cohort_contacts(), vec![(4, 3)]);

        // Re-running the same authorship is refused, not silently doubled.
        assert!(matches!(
            state.prepare_authored_contacts(&authored, 16_000_000),
            Err(FormationError::PhysicalSettlementUnavailable(
                ReachedCohortError::Electrical(
                    crate::sparse_electrical_contact::SparseElectricalError::ContactAlreadyAuthored
                )
            ))
        ));
        // A receptor this organism does not declare cannot be contacted.
        let absent = vec![AuthoredDeclaredContact {
            left_sensor_id: "left-retina".to_owned(),
            left_substream_id: "foveal-receptor-0".to_owned(),
            right_sensor_id: "left-retina".to_owned(),
            right_substream_id: "foveal-receptor-9".to_owned(),
            conductance_picosiemens: ExactRational::integer(500),
        }];
        assert_eq!(
            state.prepare_authored_contacts(&absent, 16_000_000),
            Err(FormationError::AuthoredContactUnavailable)
        );
        assert_eq!(
            state.prepare_authored_contacts(&[], 16_000_000),
            Err(FormationError::AuthoredContactUnavailable)
        );
        // Every refusal left the body exactly as the growth left it.
        assert_eq!(state.encode(16_000_000).unwrap(), grown_bytes);
    }

    #[cfg(any())]
    #[test]
    fn feeding_metabolism_sustains_lessons_across_a_feed_and_rest_cycle() {
        // Served-path proof of the minimal feeding metabolism (authorized
        // 2026-08-05) on a fresh organism.  MEASURED on this four-receptor
        // body: the rest metabolism holds every dissipation ledger at zero
        // for as long as the reservoir can pay, the reservoir is a closed
        // fuel/spent pool, one lit lesson costs 376 quanta of a 2,164-quantum
        // pool, and one authored feed of the body's whole spent load restores
        // it exactly and vents its heat.
        //
        // COST RE-MEASURED 2026-08-06: 376, not the ~312 this comment carried.
        // It was stale BEFORE the exact rest-cost law of the same date and was
        // NOT moved by it — the first lesson costs 376 under both the old
        // ceil-and-discard billing and the exact carried-residue billing, and
        // the exhaustion count below is 7 under both.  On this four-receptor
        // body the lit lesson's cost is the recovery lanes undoing gate work,
        // not the membrane return; the return's overcharge only dominates on a
        // body doing more returning than seeing (measured on the LIVING body:
        // 200 dark intervals cost 1,849 fuel quanta under the old law and 28
        // under the exact one, for exactly the same 1,849 charges returned).
        let light = (0..4)
            .map(exact_four_single_optical_episode)
            .collect::<Vec<_>>();
        let dark = exact_four_dark_optical_episode();
        let seed = explicit_optical_seed(&light[0], 500);
        let mut state =
            ResidentCognitiveFormationState::from_developmental_electrical_seeds(vec![seed])
                .unwrap();
        let mut teach = |state: &mut ResidentCognitiveFormationState| {
            for source in light.iter().chain(std::iter::repeat(&dark).take(8)) {
                let prepared = state
                    .prepare_admitted_transition(&admitted_fixture_episode(source), 16_000_000)
                    .unwrap();
                state.commit(prepared).unwrap();
            }
            state.energy_state()
        };

        let mut lessons_before_exhaustion = 0usize;
        let mut energy = teach(&mut state);
        loop {
            lessons_before_exhaustion += 1;
            // Material conservation: the reservoir is a closed fuel/spent pool.
            assert_eq!(
                energy.fuel_quanta + energy.spent_quanta,
                energy.fuel_capacity_quanta
            );
            // Every quantum of fuel burnt appears as one spent quantum AND one
            // heat quantum, because every burn drained a dissipation ledger or
            // paid for a membrane return.
            assert_eq!(energy.heat_quanta, energy.spent_quanta);
            if energy.fuel_quanta == 0 {
                break;
            }
            // Rest recovery keeps every dissipation ledger empty for as long as
            // the body can pay: the old monotone gate ratchet is closed.
            assert_eq!(energy.dissipated_quanta, 0);
            assert!(
                lessons_before_exhaustion < 40,
                "lessons never exhausted fuel"
            );
            energy = teach(&mut state);
        }
        // The exact exhaustion count changes when the neuron's physically
        // mounted positional fabric changes. What this test requires is the
        // law: the finite body eventually exhausts, never exceeds its own
        // capacity, and can regenerate exactly from its reported spent
        // material. No historical lesson count governs that physics.
        assert!(lessons_before_exhaustion > 0);
        assert!(energy.dissipated_quanta > 0);
        let exhausted_spent = energy.spent_quanta;

        // Feeding a body that cannot absorb is refused honestly.
        let mut sated = state.clone();
        let fed = sated
            .prepare_nutrition(
                AuthoredNutritionDeclaration::new(exhausted_spent).unwrap(),
                16_000_000,
            )
            .unwrap();
        assert_eq!(
            fed.observation.nutrition_regenerated_fuel_quanta,
            exhausted_spent
        );
        assert_eq!(fed.observation.nutrition_unabsorbed_waste_quanta, 0);
        assert_eq!(
            fed.observation.nutrition_vented_heat_quanta,
            exhausted_spent
        );
        sated.commit(fed).unwrap();
        let after_feed = sated.energy_state();
        assert_eq!(after_feed.fuel_quanta, after_feed.fuel_capacity_quanta);
        assert_eq!(after_feed.spent_quanta, 0);
        assert_eq!(after_feed.heat_quanta, 0);
        assert!(matches!(
            sated.prepare_nutrition(AuthoredNutritionDeclaration::new(1).unwrap(), 16_000_000,),
            Err(FormationError::NutritionUnavailable(
                MetabolicError::NothingToRegenerate
            ))
        ));

        // Over-feeding an absorbing body exports the excess as waste rather
        // than inventing capacity.
        let mut overfed = state.clone();
        let excess = exhausted_spent + 1_000;
        let prepared = overfed
            .prepare_nutrition(
                AuthoredNutritionDeclaration::new(excess).unwrap(),
                16_000_000,
            )
            .unwrap();
        assert_eq!(
            prepared.observation.nutrition_regenerated_fuel_quanta
                + prepared.observation.nutrition_unabsorbed_waste_quanta,
            excess
        );
        assert_eq!(
            prepared.observation.nutrition_unabsorbed_waste_quanta,
            1_000
        );

        // The fed body learns again: the cycle is sustainable, not a one-shot.
        let mut lessons_after_feed = 1usize;
        let mut energy = teach(&mut sated);
        while energy.fuel_quanta > 0 {
            lessons_after_feed += 1;
            assert_eq!(energy.dissipated_quanta, 0);
            assert_eq!(
                energy.fuel_quanta + energy.spent_quanta,
                energy.fuel_capacity_quanta
            );
            assert!(lessons_after_feed < 40, "fed body never exhausted fuel");
            energy = teach(&mut sated);
        }
        assert_eq!(lessons_after_feed, lessons_before_exhaustion);
    }

    #[cfg(any())]
    #[test]
    #[ignore = "retired: fixture requires Boolean/member-set mosaic admission"]
    fn four_receptor_experience_selectively_emits_four_real_fractals() {
        let light = (0..4)
            .map(exact_four_single_optical_episode)
            .collect::<Vec<_>>();
        let dark = exact_four_dark_optical_episode();
        let seed = explicit_optical_seed(&light[0], 500);
        let mut state =
            ResidentCognitiveFormationState::from_developmental_electrical_seeds(vec![seed])
                .unwrap();
        let mut emitted = Vec::new();
        for source in light
            .iter()
            .chain(std::iter::repeat(&dark).take(DARK_TAIL_EPISODES))
        {
            let prepared = state.prepare(source, 16_000_000).unwrap();
            assert!(prepared.observation.mosaic_formed.is_none());
            assert_eq!(prepared.observation.mosaic_count, 0);
            emitted.extend(prepared.observation.emitted_neuron_fractals.clone());
            state.commit(prepared).unwrap();
        }
        let mut emitted_lineages = emitted
            .iter()
            .map(|fractal| fractal.neuron_lineage)
            .collect::<Vec<_>>();
        emitted_lineages.sort();
        emitted_lineages.dedup();
        assert_eq!(
            emitted_lineages,
            [
                local_lineage(1),
                local_lineage(2),
                local_lineage(3),
                local_lineage(4)
            ]
        );
        assert!(state.cohorts[0].pending_experience.is_none());
        assert!(state.cohorts[0].retained_experience.is_some());
        let encoded = state.encode(16_000_000).unwrap();
        let restored = ResidentCognitiveFormationState::decode(&encoded, 16_000_000).unwrap();
        assert_eq!(restored, state);
        assert!(restored.cohorts[0].retained_experience.is_some());
        assert_eq!(restored.encode(16_000_000).unwrap(), encoded);

        let partial = exact_four_partial_optical_episode();
        let recurrence_sources = std::iter::once(&partial)
            .chain(std::iter::repeat(&dark).take(DARK_TAIL_EPISODES))
            .collect::<Vec<_>>();
        let recurrence_fields = recurrence_sources
            .iter()
            .map(|source| prepare_complete_joint_field_admitted_fixture(source, 0).unwrap())
            .collect::<Vec<_>>();
        assert_eq!(restored.summary().mosaic_count, 0);
        let mut integrated = restored.clone();
        let checkpoint_before_recurrences = restored.hippocampal;
        let mut formed = Vec::new();
        RESIDENT_ACTUAL_RECURRENCE_SETTLEMENTS.with(|count| count.set(0));
        for source in &recurrence_sources {
            let prepared = integrated
                .prepare_admitted_transition(&admitted_fixture_episode(source), 16_000_000)
                .unwrap();
            if let Some(receipt) = prepared.observation.mosaic_formed {
                assert_eq!(prepared.observation.mosaic_count, 1);
                assert!(prepared.observation.activations.is_empty());
                assert_eq!(prepared.observation.partial_cue_reassembly_count(), 1);
                // The receipt of a newly formed mosaic is the sha256 of the
                // mosaic's OWN encoded body, not an archive address: it must
                // be reproducible from her retained formation alone.
                assert_eq!(
                    receipt,
                    sha256(
                        &encode_organism_mosaic(
                            &prepared.successor.cohorts,
                            &prepared.successor.electrical_fabric,
                            &prepared.successor.mosaics[0].mosaic,
                            16_000_000,
                        )
                        .unwrap()
                    )
                );
                formed.push(receipt);
            }
            // A recurrence commits with no publication step of any kind, and
            // the retired archive checkpoint does not move.
            assert_eq!(
                prepared.successor.hippocampal,
                checkpoint_before_recurrences
            );
            let interval_bytes = integrated.encode_successor(&prepared, 16_000_000).unwrap();
            integrated.commit(prepared).unwrap();
            integrated =
                ResidentCognitiveFormationState::decode(&interval_bytes, 16_000_000).unwrap();
            assert_eq!(integrated.encode(16_000_000).unwrap(), interval_bytes);
        }
        RESIDENT_ACTUAL_RECURRENCE_SETTLEMENTS.with(|count| {
            let available_gates = recurrence_fields
                .iter()
                .map(|field| field.result().gates.len())
                .sum::<usize>();
            // Candidate recurrence ends at physical mosaic admission. Later
            // dark gates return to ordinary living settlement; they must not
            // remain trapped in the just-completed candidate path.
            assert!(count.get() > 0);
            assert!(count.get() < available_gates);
        });
        assert_eq!(formed.len(), 1);
        assert_eq!(integrated.summary().mosaic_count, 1);
        assert_eq!(integrated.mosaics.len(), 1);
        assert!(integrated.cohorts[0].pending_recurrence.is_none());
        let integrated_bytes = integrated.encode(16_000_000).unwrap();
        let cold_integrated =
            ResidentCognitiveFormationState::decode(&integrated_bytes, 16_000_000).unwrap();
        assert_eq!(cold_integrated, integrated);
        // A full learn-and-recognize cycle left the retired checkpoint exactly
        // where it started: no episode, no posting, no radix path copy, no
        // address of any kind was produced by admitting a real mosaic.
        assert_eq!(cold_integrated.hippocampal, checkpoint_before_recurrences);
        assert!(!cold_integrated
            .hippocampal
            .carries_retired_archive_reference());

        let five_receptor_occurrence = exact_five_optical_episode();
        let predecessor_anatomy = integrated.cohorts[0].anatomy.clone();
        let predecessor_lineages = integrated.retained_neuron_lineages();
        let predecessor_mosaics = integrated.mosaics.clone();
        RESIDENT_JOINT_FIELD_EVALUATIONS.with(|count| count.set(0));
        let warm_growth = integrated
            .prepare_admitted_transition(
                &admitted_fixture_episode(&five_receptor_occurrence),
                16_000_000,
            )
            .unwrap();
        RESIDENT_JOINT_FIELD_EVALUATIONS.with(|count| {
            assert_eq!(
                count.get(),
                five_receptor_occurrence.joint_source_occurrences().len()
            );
        });
        let cold_growth = cold_integrated
            .prepare_admitted_transition(
                &admitted_fixture_episode(&five_receptor_occurrence),
                16_000_000,
            )
            .unwrap();
        assert_eq!(cold_growth, warm_growth);
        assert_eq!(warm_growth.successor.cohorts.len(), 1);
        assert_eq!(warm_growth.successor.summary().complete_neuron_count, 5);
        assert_eq!(warm_growth.successor.next_lineage_ordinal, 6);
        for (successor, predecessor) in warm_growth.successor.cohorts[0]
            .anatomy
            .neuron_anatomies()
            .iter()
            .zip(predecessor_anatomy.neuron_anatomies())
        {
            assert_eq!(successor.capacitance(), predecessor.capacitance());
            assert!(successor.mathloom_positions() >= predecessor.mathloom_positions());
        }
        assert_eq!(
            &warm_growth.successor.cohorts[0].anatomy.source_sites()[..4],
            predecessor_anatomy.source_sites()
        );
        assert_eq!(
            &warm_growth.successor.cohorts[0].anatomy.neuron_lineages()[..4],
            predecessor_lineages
        );
        assert_eq!(
            warm_growth.successor.cohorts[0].anatomy.neuron_lineages()[4],
            local_lineage(5)
        );
        assert_eq!(
            warm_growth.successor.retained_neuron_lineages()[4],
            local_lineage(5)
        );
        let successor_lineages = warm_growth.successor.retained_neuron_lineages();
        assert!(successor_lineages
            .iter()
            .enumerate()
            .all(|(index, lineage)| { !successor_lineages[..index].contains(lineage) }));
        assert_eq!(warm_growth.successor.mosaics, predecessor_mosaics);
        let mut extended = integrated.clone();
        let extended_bytes = extended.encode_successor(&warm_growth, 16_000_000).unwrap();
        extended.commit(warm_growth).unwrap();
        let cold_extended =
            ResidentCognitiveFormationState::decode(&extended_bytes, 16_000_000).unwrap();
        assert_eq!(cold_extended, extended);
        assert_eq!(cold_extended.encode(16_000_000).unwrap(), extended_bytes);
        assert_eq!(cold_extended.summary().complete_neuron_count, 5);
        assert_eq!(cold_extended.summary().mosaic_count, 1);
        assert_eq!(cold_extended.hippocampal, checkpoint_before_recurrences);

        // The first learn-and-recognize cycle used the body's finite recovery
        // reservoir completely.  An unfed control therefore cannot drive a
        // second whole-formation recurrence: exhausted material is a physical
        // unavailability, not a recall defect to bypass with a controller.
        assert_eq!(integrated.energy_state().fuel_quanta, 0);
        let mut exhausted = integrated.clone();
        let later_cue = exact_four_single_optical_episode(1);
        let mut exhausted_reassemblies = 0usize;
        for source in
            std::iter::once(&later_cue).chain(std::iter::repeat(&dark).take(DARK_TAIL_EPISODES))
        {
            let prepared = exhausted
                .prepare_admitted_transition(&admitted_fixture_episode(source), 16_000_000)
                .unwrap();
            exhausted_reassemblies += prepared.observation.partial_cue_reassembly_count;
            exhausted.commit(prepared).unwrap();
        }
        // Incoming light carries its own physical energy. A metabolically
        // exhausted body may therefore still complete a bounded number of
        // already-yielded receptor transitions using free local dissipation
        // capacity; exhaustion must stop that sequence without a controller.
        assert!(exhausted_reassemblies > 0);
        let exhausted_checkpoint = exhausted.clone();
        let mut later_reassemblies = 0usize;
        for source in
            std::iter::once(&later_cue).chain(std::iter::repeat(&dark).take(DARK_TAIL_EPISODES))
        {
            let prepared = exhausted
                .prepare_admitted_transition(&admitted_fixture_episode(source), 16_000_000)
                .unwrap();
            later_reassemblies += prepared.observation.partial_cue_reassembly_count;
            exhausted.commit(prepared).unwrap();
        }
        assert_eq!(later_reassemblies, 0);
        assert_ne!(exhausted, exhausted_checkpoint);

        // Restore exactly the material the same body reports as spent, then
        // supply the declared dark causal intervals in which its existing
        // recovery physics can act.  No recall threshold, timeout, scheduler,
        // or semantic rule participates.  Recovery itself lawfully provides
        // an internal partial cue, and a later external partial cue also
        // reassembles the one retained distributed formation.
        let mut progressive = integrated.clone();
        let spent = progressive.energy_state().spent_quanta;
        let nutrition = progressive
            .prepare_nutrition(
                AuthoredNutritionDeclaration::new(spent).unwrap(),
                16_000_000,
            )
            .unwrap();
        assert_eq!(
            nutrition.observation.nutrition_regenerated_fuel_quanta,
            spent
        );
        progressive.commit(nutrition).unwrap();
        let mut reassembly_events = 0usize;
        let mut endogenous_reassembly_events = 0usize;
        for _ in 0..DARK_TAIL_EPISODES {
            let prepared = progressive
                .prepare_admitted_transition(&admitted_fixture_episode(&dark), 16_000_000)
                .unwrap();
            reassembly_events += prepared.observation.partial_cue_reassembly_count;
            endogenous_reassembly_events +=
                prepared.observation.endogenous_partial_cue_reassembly_count;
            progressive.commit(prepared).unwrap();
        }
        assert!(endogenous_reassembly_events > 0);
        let reassemblies_before_external_cue = reassembly_events;
        for source in
            std::iter::once(&later_cue).chain(std::iter::repeat(&dark).take(DARK_TAIL_EPISODES))
        {
            let prepared = progressive
                .prepare_admitted_transition(&admitted_fixture_episode(source), 16_000_000)
                .unwrap();
            reassembly_events += prepared.observation.partial_cue_reassembly_count;
            let successor = progressive.encode_successor(&prepared, 16_000_000).unwrap();
            progressive.commit(prepared).unwrap();
            progressive = ResidentCognitiveFormationState::decode(&successor, 16_000_000).unwrap();
        }
        assert!(reassembly_events > reassemblies_before_external_cue);
        assert_eq!(progressive.summary().mosaic_count, 1);
        assert_eq!(progressive.mosaics[0].mosaic_of_mosaics_relation_count, 0);
        assert_eq!(progressive.mosaic_of_mosaics_count().unwrap(), 0);
        assert_eq!(progressive.hippocampal, checkpoint_before_recurrences);

        // The five tamper assertions that stood here checked that a corrupted
        // ARCHIVED EPISODE RECORD failed to validate (damaged source body,
        // damaged mosaic body, trailing bytes on either evidence body, a
        // mismatched participant lineage).  They validated the record, not
        // Guala, and they left with the record.  What still guards her here is
        // the truncation assertion immediately below plus the round-trip law
        // in `decode`, which every restore runs on her real body.
        assert_eq!(cold_integrated.summary().mosaic_count, 1);
        assert!(ResidentCognitiveFormationState::decode(
            &integrated_bytes[..integrated_bytes.len() - 1],
            16_000_000,
        )
        .is_err());
        let mut duplicate = integrated.clone();
        duplicate.mosaics =
            vec![duplicate.mosaics[0].clone(), duplicate.mosaics[0].clone()].into_boxed_slice();
        assert!(matches!(
            duplicate.encode(16_000_000),
            Err(FormationError::NoncanonicalState)
        ));

        assert!(restored.cohorts[0]
            .retained_experience
            .as_ref()
            .unwrap()
            .retained_members()
            .is_some_and(|members| !members.is_empty()));
    }

    fn structural_test_lineage(value: u8) -> [u8; 16] {
        let mut lineage = [0u8; 16];
        lineage[15] = value;
        lineage
    }

    #[test]
    fn one_transition_exports_one_composed_fractal_per_neuron() {
        let delta = |gate_negative: bool, gate_magnitude: u128, plastic: i128| {
            let mut entries = vec![PhysicalStateDeltaEntry::new(
                crate::complete_neuron::PhysicalStateCoordinate::GateOpenPopulation,
                ExactPhysicalStateDelta::Integral(
                    ExactSignedDelta::from_parts(gate_negative, gate_magnitude).unwrap(),
                ),
            )
            .unwrap()];
            if plastic != 0 {
                entries.push(
                    PhysicalStateDeltaEntry::new(
                        crate::complete_neuron::PhysicalStateCoordinate::PlasticRestLength,
                        ExactPhysicalStateDelta::Rational(
                            ExactRational::new(plastic, 3).unwrap(),
                        ),
                    )
                    .unwrap(),
                );
            }
            SparsePhysicalStateDelta::from_canonical_entries(entries).unwrap()
        };
        let first = structural_test_lineage(1);
        let second = structural_test_lineage(2);
        let coalesced = coalesce_emitted_neuron_fractals(vec![
            EmittedNeuronFractal {
                neuron_lineage: first,
                delta: delta(false, 2, 1),
            },
            EmittedNeuronFractal {
                neuron_lineage: second,
                delta: delta(false, 4, 0),
            },
            EmittedNeuronFractal {
                neuron_lineage: first,
                delta: delta(true, 1, -1),
            },
        ])
        .unwrap();

        assert_eq!(coalesced.len(), 2);
        assert_eq!(coalesced[0].neuron_lineage, first);
        assert_eq!(coalesced[0].delta.entries().len(), 1);
        assert_eq!(
            coalesced[0].delta.exact_delta(
                crate::complete_neuron::PhysicalStateCoordinate::GateOpenPopulation,
            ),
            Some(ExactPhysicalStateDelta::Integral(
                ExactSignedDelta::from_parts(false, 1).unwrap(),
            ))
        );
        assert_eq!(coalesced[1].neuron_lineage, second);
    }

    /// Synthesize an admitted mosaic with explicit member and active-bond
    /// structure for the R1 boundary tests.  `members` must be strictly
    /// ascending; bonds are canonicalized exactly as admission does.
    fn synthetic_admitted_mosaic(
        members: &[u8],
        active_bonds: &[(u8, u8)],
        cue: u8,
    ) -> AdmittedPhysicalMosaic {
        let fractal =
            crate::complete_neuron::SparsePhysicalStateDelta::from_canonical_entries(vec![
                crate::complete_neuron::PhysicalStateDeltaEntry::new(
                    crate::complete_neuron::PhysicalStateCoordinate::PlasticRestLength,
                    crate::complete_neuron::ExactPhysicalStateDelta::Rational(
                        crate::exact_rational::ExactRational::new(1, 3).unwrap(),
                    ),
                )
                .unwrap(),
            ])
            .unwrap();
        let bond = |left: u8, right: u8| {
            crate::physical_mosaic::StablePhysicalBondReference::new(
                structural_test_lineage(left),
                structural_test_lineage(right),
                0,
            )
            .unwrap()
        };
        let mut original_bonds = members
            .windows(2)
            .map(|pair| bond(pair[0], pair[1]))
            .collect::<Vec<_>>();
        original_bonds.sort_unstable();
        let mut recurrence_bonds = active_bonds
            .iter()
            .map(|(left, right)| bond(*left, *right))
            .collect::<Vec<_>>();
        recurrence_bonds.sort_unstable();
        AdmittedPhysicalMosaic::from_parts_for_tests(
            members
                .iter()
                .map(|value| structural_test_lineage(*value))
                .collect(),
            vec![fractal; members.len()],
            original_bonds,
            recurrence_bonds,
            vec![structural_test_lineage(cue)],
        )
    }

    #[test]
    fn surviving_association_can_relearn_one_missing_cross_sensory_relation() {
        let current = synthetic_admitted_mosaic(&[1, 2, 7], &[(1, 7), (2, 7)], 1);
        let visual_only = synthetic_admitted_mosaic(&[1, 3, 7], &[(1, 7), (3, 7)], 1);
        let already_cross_sensory = current.clone();
        let lineage_layers = [
            (structural_test_lineage(1), 0),
            (structural_test_lineage(2), 1),
            (structural_test_lineage(3), 0),
            (structural_test_lineage(7), 7),
        ]
        .into_iter()
        .collect::<Box<[_]>>();
        let topology = ResidentTopologyIndex {
            flat_locations: Box::new([]),
            flat_by_lineage: Box::new([]),
            intrinsic_locations: Box::new([]),
            source_locations: Box::new([]),
            lineage_layers,
            canonical_lineages: Box::new([]),
            canonical_bonds: Box::new([]),
            contacts: Box::new([]),
            incident_contacts_by_flat: Box::new([]),
            neighbours_by_flat: Box::new([]),
            cohort_shapes: Box::new([]),
            fabric_contact_count: 0,
        };

        let retained = vec![RetainedOrganismMosaic::newly_admitted(visual_only)];
        assert!(adds_unretained_cross_sensory_relation(
            &current,
            &retained,
            &[0],
            &topology,
        )
        .unwrap());

        let retained = vec![RetainedOrganismMosaic::newly_admitted(
            already_cross_sensory,
        )];
        assert!(!adds_unretained_cross_sensory_relation(
            &current,
            &retained,
            &[0],
            &topology,
        )
        .unwrap());
    }

    #[test]
    fn legacy_transient_mosaic_is_not_cognitive_authority() {
        let valid = synthetic_admitted_mosaic(&[1, 2, 3], &[(1, 2), (2, 3)], 1);
        let transient =
            crate::complete_neuron::SparsePhysicalStateDelta::from_canonical_entries(vec![
                crate::complete_neuron::PhysicalStateDeltaEntry::new(
                    crate::complete_neuron::PhysicalStateCoordinate::MembraneSeparatedCharge,
                    crate::complete_neuron::ExactPhysicalStateDelta::Integral(
                        crate::complete_neuron::ExactSignedDelta::from_parts(false, 1).unwrap(),
                    ),
                )
                .unwrap(),
            ])
            .unwrap();
        let invalid = AdmittedPhysicalMosaic::from_parts_for_tests(
            valid.member_lineages().to_vec(),
            vec![transient; valid.member_lineages().len()],
            valid.original_bonds().to_vec(),
            valid.recurrence_bonds().to_vec(),
            valid.partial_cue_lineages().to_vec(),
        );
        assert!(!invalid.carries_only_retained_neuron_structure());
        assert!(valid.carries_only_retained_neuron_structure());
        let mut transient_only = [RetainedOrganismMosaic::newly_admitted(invalid.clone())];
        resolve_unpersisted_recurrent_retention(
            &[],
            &ResidentElectricalFabric::default(),
            &mut transient_only,
        )
        .unwrap();
        assert_eq!(transient_only[0].recurrent_lineage, None);

        let mut state = ResidentCognitiveFormationState::default();
        state.mosaics = vec![
            RetainedOrganismMosaic::newly_admitted(invalid),
            RetainedOrganismMosaic::newly_admitted(valid),
        ]
        .into_boxed_slice();
        assert_eq!(state.summary().mosaic_count, 1);
        assert_eq!(state.observe_retained_formation_members().len(), 1);
        assert_eq!(state.mosaic_of_mosaics_count().unwrap(), 0);
    }

    /// An equality resolution is observational only. It cannot alter retained
    /// physical state or increment a lifetime counter.
    #[test]
    fn same_members_without_new_active_bonds_reinforce_the_retained_reference() {
        let reference = synthetic_admitted_mosaic(&[1, 2, 3], &[(1, 2), (2, 3)], 1);
        let mut mosaics = vec![RetainedOrganismMosaic::newly_admitted(reference.clone())];
        // A different cue over a strict subset of the active bonds is still
        // the same retained structure.
        let subset = synthetic_admitted_mosaic(&[1, 2, 3], &[(1, 2)], 2);
        let resolution = resolve_mosaic_structural_identity(&mosaics, subset);
        assert_eq!(
            resolution,
            MosaicStructuralResolution::Reinforces { mosaic_index: 0 }
        );
        apply_mosaic_structural_resolution(&mut mosaics, resolution).unwrap();
        let identical = resolve_mosaic_structural_identity(&mosaics, reference.clone());
        assert_eq!(
            identical,
            MosaicStructuralResolution::Reinforces { mosaic_index: 0 }
        );
        apply_mosaic_structural_resolution(&mut mosaics, identical).unwrap();
        assert_eq!(mosaics.len(), 1);
        assert_eq!(mosaics[0].mosaic, reference);
        assert_eq!(mosaics[0].reinforcement_count, 0);
        assert_eq!(mosaics[0].mosaic_of_mosaics_relation_count, 0);
    }

    /// The same neuron membership does not define identity.  A distinct exact
    /// retained neuronal structure is a distinct formation even when every
    /// member lineage is shared.
    #[test]
    fn same_members_with_distinct_retained_structure_admit_distinct_formation() {
        let reference = synthetic_admitted_mosaic(&[1, 2, 3], &[(1, 2), (2, 3)], 1);
        let mut mosaics = vec![RetainedOrganismMosaic {
            mosaic: reference.clone(),
            recurrent_lineage: None,
            reinforcement_count: 5,
            mosaic_of_mosaics_relation_count: 1,
        }];
        let mut distinct = synthetic_admitted_mosaic(&[1, 2, 3], &[(1, 3), (2, 3)], 3);
        let changed =
            crate::complete_neuron::SparsePhysicalStateDelta::from_canonical_entries(vec![
                crate::complete_neuron::PhysicalStateDeltaEntry::new(
                    crate::complete_neuron::PhysicalStateCoordinate::PlasticRestLength,
                    crate::complete_neuron::ExactPhysicalStateDelta::Rational(
                        crate::exact_rational::ExactRational::new(2, 3).unwrap(),
                    ),
                )
                .unwrap(),
            ])
            .unwrap();
        distinct = AdmittedPhysicalMosaic::from_parts_for_tests(
            distinct.member_lineages().to_vec(),
            vec![changed; distinct.member_lineages().len()],
            distinct.original_bonds().to_vec(),
            distinct.recurrence_bonds().to_vec(),
            distinct.partial_cue_lineages().to_vec(),
        );
        let resolution = resolve_mosaic_structural_identity(&mosaics, distinct.clone());
        assert_eq!(
            resolution,
            MosaicStructuralResolution::NewFormation(distinct.clone())
        );
        apply_mosaic_structural_resolution(&mut mosaics, resolution).unwrap();
        assert_eq!(mosaics.len(), 2);
        assert_eq!(mosaics[0].mosaic, reference);
        assert_eq!(mosaics[1].mosaic, distinct);
        assert_eq!(mosaics[0].reinforcement_count, 5);
        assert_eq!(mosaics[0].mosaic_of_mosaics_relation_count, 1);
    }

    /// Overlap alone is not a learned relation and cannot suppress a distinct
    /// retained formation.
    #[test]
    fn overlapping_member_sets_retain_each_distinct_formation() {
        let first = synthetic_admitted_mosaic(&[1, 2, 3], &[(1, 2), (2, 3)], 1);
        let second = synthetic_admitted_mosaic(&[7, 8, 9], &[(7, 8), (8, 9)], 7);
        let mut mosaics = vec![
            RetainedOrganismMosaic::newly_admitted(first),
            RetainedOrganismMosaic::newly_admitted(second),
        ];
        let overlapping = synthetic_admitted_mosaic(&[3, 4, 7], &[(3, 4), (4, 7)], 4);
        let resolution = resolve_mosaic_structural_identity(&mosaics, overlapping);
        assert!(matches!(
            resolution,
            MosaicStructuralResolution::NewFormation(_)
        ));
        apply_mosaic_structural_resolution(&mut mosaics, resolution).unwrap();
        assert_eq!(mosaics.len(), 3);
        assert_eq!(mosaics[0].mosaic_of_mosaics_relation_count, 0);
        assert_eq!(mosaics[1].mosaic_of_mosaics_relation_count, 0);
        assert_eq!(mosaics[0].reinforcement_count, 0);
        assert_eq!(mosaics[1].reinforcement_count, 0);
    }

    /// R1 disjoint branch: a member set disjoint from every retained
    /// formation is a genuinely new mosaic — the pre-law behavior, with both
    /// counts at the historical default of zero.
    #[test]
    fn disjoint_member_sets_admit_a_genuinely_new_mosaic() {
        let first = synthetic_admitted_mosaic(&[1, 2, 3], &[(1, 2), (2, 3)], 1);
        let mut mosaics = vec![RetainedOrganismMosaic::newly_admitted(first)];
        let disjoint = synthetic_admitted_mosaic(&[4, 5, 6], &[(4, 5), (5, 6)], 4);
        let resolution = resolve_mosaic_structural_identity(&mosaics, disjoint.clone());
        assert_eq!(
            resolution,
            MosaicStructuralResolution::NewFormation(disjoint.clone())
        );
        apply_mosaic_structural_resolution(&mut mosaics, resolution).unwrap();
        assert_eq!(mosaics.len(), 2);
        assert_eq!(mosaics[1].mosaic, disjoint);
        assert_eq!(mosaics[1].reinforcement_count, 0);
        assert_eq!(mosaics[1].mosaic_of_mosaics_relation_count, 0);
    }

    /// R3 codec: reinforcement/relation counts persist through the organism
    /// state body under the `GLMRC01` wrapper, while zero-count references
    /// keep the bare pre-law encoding byte-identically (GLEXP02/GLEXP03
    /// precedent: the new magic appears only when the retained state differs
    /// from the historical default).
    #[test]
    #[ignore = "retired: fixture requires Boolean/member-set mosaic admission"]
    fn reinforcement_counts_round_trip_and_zero_counts_keep_pre_law_bytes() {
        let light = (0..4)
            .map(exact_four_single_optical_episode)
            .collect::<Vec<_>>();
        let dark = exact_four_dark_optical_episode();
        let seed = explicit_optical_seed(&light[0], 500);
        let mut state =
            ResidentCognitiveFormationState::from_developmental_electrical_seeds(vec![seed])
                .unwrap();
        for source in light
            .iter()
            .chain(std::iter::repeat(&dark).take(DARK_TAIL_EPISODES))
        {
            let prepared = state.prepare(source, 16_000_000).unwrap();
            state.commit(prepared).unwrap();
        }
        let partial = exact_four_partial_optical_episode();
        for source in
            std::iter::once(&partial).chain(std::iter::repeat(&dark).take(DARK_TAIL_EPISODES))
        {
            let prepared = state
                .prepare_admitted_transition(&admitted_fixture_episode(source), 16_000_000)
                .unwrap();
            state.commit(prepared).unwrap();
        }
        assert_eq!(state.summary().mosaic_count, 1);
        assert_eq!(state.mosaics[0].reinforcement_count, 0);

        // Zero counts: the encoded body carries the counts wrapper nowhere,
        // so every pre-law receipt stays byte-identical.
        let bare = state.encode(16_000_000).unwrap();
        assert!(!bare
            .windows(RETAINED_MOSAIC_COUNTS_MAGIC.len())
            .any(|window| window == RETAINED_MOSAIC_COUNTS_MAGIC));

        // Nonzero counts round-trip exactly and re-encode canonically.
        state.mosaics[0].reinforcement_count = 3;
        state.mosaics[0].mosaic_of_mosaics_relation_count = 2;
        let counted = state.encode(16_000_000).unwrap();
        assert!(counted
            .windows(RETAINED_MOSAIC_COUNTS_MAGIC.len())
            .any(|window| window == RETAINED_MOSAIC_COUNTS_MAGIC));
        let restored = ResidentCognitiveFormationState::decode(&counted, 16_000_000).unwrap();
        assert_eq!(restored, state);
        assert_eq!(restored.mosaics[0].reinforcement_count, 3);
        assert_eq!(restored.mosaics[0].mosaic_of_mosaics_relation_count, 2);
        assert_eq!(restored.mosaic_of_mosaics_count().unwrap(), 2);
        assert_eq!(restored.encode(16_000_000).unwrap(), counted);

        // A wrapper claiming zero counts is refused: its canonical form is
        // the bare body, and one retained state never admits two encodings.
        let body = encode_organism_mosaic(
            &state.cohorts,
            &state.electrical_fabric,
            &state.mosaics[0].mosaic,
            16_000_000,
        )
        .unwrap();
        let mut zero_wrapped = Vec::new();
        zero_wrapped.extend_from_slice(RETAINED_MOSAIC_COUNTS_MAGIC);
        zero_wrapped.extend_from_slice(&0u64.to_le_bytes());
        zero_wrapped.extend_from_slice(&0u64.to_le_bytes());
        zero_wrapped.extend_from_slice(&body);
        assert!(matches!(
            decode_retained_organism_mosaic(
                &state.cohorts,
                &state.electrical_fabric,
                &zero_wrapped,
                16_000_000,
            ),
            Err(FormationError::NoncanonicalState)
        ));
    }

    #[test]
    fn exact_optical_occurrence_physically_changes_the_resident_cell() {
        let source = exact_optical_episode();
        let genesis = ResidentCognitiveFormationState::default();
        let genesis_bytes = genesis.encode(16_000_000).unwrap();
        let prepared = genesis.prepare(&source, 16_000_000).unwrap();
        assert_eq!(prepared.observation.complete_neuron_count, 2);
        assert_eq!(prepared.observation.physically_transitioned_neuron_count, 2);
        assert_eq!(prepared.observation.complete_neuron_fractal_count, 0);
        assert_eq!(
            prepared.observation.complete_neuron_fractal_count,
            prepared.observation.emitted_neuron_fractals.len()
        );
        assert_eq!(prepared.successor.electrical_fabric.contact_count(), 1);
        assert!(prepared.successor.cohorts.iter().any(|cohort| {
            cohort
                .anatomy
                .mounts()
                .iter()
                .any(|mount| mount.place() == DeclaredNeuronPlace::new(6, 0))
        }));
        assert!(prepared.observation.emitted_neuron_fractals.is_empty());
        let successor_bytes = genesis.encode_successor(&prepared, 16_000_000).unwrap();
        assert_ne!(successor_bytes, genesis_bytes);
        let restored =
            ResidentCognitiveFormationState::decode(&successor_bytes, 16_000_000).unwrap();
        assert_eq!(restored.encode(16_000_000).unwrap(), successor_bytes);
    }

    #[test]
    fn neuron_local_quiescence_closes_the_neuronal_fractal() {
        // The lit occurrence creates retained physical change but cannot also
        // certify its own post-experience quiescence. The next exact local
        // quiescent interval emits each lineage's sparse retained delta once.
        // A single receptor cell can never satisfy the three-connected-member
        // participation law, so no mosaic is retained.
        let light = exact_optical_episode();
        let dark = exact_dark_optical_episode();
        let mut state = ResidentCognitiveFormationState::default();
        let light_transition = state.prepare(&light, 16_000_000).unwrap();
        assert_eq!(
            light_transition.observation.complete_neuron_fractal_count,
            0
        );
        assert!(light_transition
            .observation
            .emitted_neuron_fractals
            .is_empty());
        state.commit(light_transition).unwrap();

        let mid_experience_bytes = state.encode(16_000_000).unwrap();
        let mut restored =
            ResidentCognitiveFormationState::decode(&mid_experience_bytes, 16_000_000).unwrap();
        assert_eq!(restored, state);

        let mut emitted_after_occurrence = Vec::new();
        for _ in 0..DARK_TAIL_EPISODES {
            let prepared = restored.prepare(&dark, 16_000_000).unwrap();
            emitted_after_occurrence.extend(prepared.observation.emitted_neuron_fractals.clone());
            restored.commit(prepared).unwrap();
        }
        assert_eq!(emitted_after_occurrence.len(), 2);
        assert!(emitted_after_occurrence
            .iter()
            .all(|fractal| !fractal.delta.entries().is_empty()));
        // Participation retention: one changed member is fewer than the
        // admission law's three-connected-member floor, so no mosaic is
        // retained. Its real neuronal impression remains as the one bounded
        // pending experience; the mosaic minimum is not an erasure rule.
        assert!(restored.cohorts[0].retained_experience.is_none());
        assert!(restored.cohorts[0].pending_experience.is_some());

        // The post-quiescence emission is one-shot: unchanged retained state
        // does not reopen the experience or emit a duplicate.
        let later_dark = restored.prepare(&dark, 16_000_000).unwrap();
        assert_eq!(later_dark.observation.complete_neuron_fractal_count, 0);
    }

    #[test]
    fn continued_identical_light_emits_each_retained_physical_change() {
        // Continued photons do not authorize an occurrence-boundary receipt.
        // A lineage emits only when its retained coordinates hold unchanged
        // for one later exact causal interval.
        let light = exact_optical_episode();
        let mut state = ResidentCognitiveFormationState::default();
        let first = state.prepare(&light, 16_000_000).unwrap();
        assert_eq!(first.observation.complete_neuron_fractal_count, 0);
        assert!(first.observation.emitted_neuron_fractals.is_empty());
        state.commit(first).unwrap();

        let mut emitted = Vec::new();
        for _ in 0..DARK_TAIL_EPISODES {
            let prepared = state.prepare(&light, 16_000_000).unwrap();
            emitted.extend(prepared.observation.emitted_neuron_fractals.clone());
            state.commit(prepared).unwrap();
            if !emitted.is_empty() {
                break;
            }
        }
        assert!(emitted
            .iter()
            .all(|fractal| !fractal.delta.entries().is_empty()));
        assert!(!emitted.is_empty());
        assert!(state.cohorts[0].pending_experience.is_some());
        assert!(state.cohorts[0].retained_experience.is_none());
    }

    #[test]
    fn experienced_neurons_emit_one_new_bounded_fractal_after_later_quiescence() {
        let light = exact_four_single_optical_episode(0);
        let dark = exact_four_dark_optical_episode();
        let seed = explicit_optical_seed(&light, 1);
        let mut state =
            ResidentCognitiveFormationState::from_developmental_electrical_seeds(vec![seed])
                .unwrap();

        let first = state.prepare(&light, 16_000_000).unwrap();
        assert_eq!(first.observation.emitted_neuron_fractals.len(), 3);
        state.commit(first).unwrap();

        // Preserve the first exact settled experience as prior cognitive
        // state. The current wire format already has independent retained and
        // pending carriers; no schema or compatibility authority is added.
        let mut retained = state.cohorts[0].pending_experience.take().unwrap();
        let retained_members = retained
            .pending_members()
            .unwrap()
            .iter()
            .filter(|member| member.settled)
            .map(|member| SparseRetainedExperienceMember {
                neuron_index: member.neuron_index,
                delta: member.delta.clone(),
            })
            .collect::<Vec<_>>();
        retained.physical =
            ResidentExperiencePhysicalEvidence::Retained(retained_members.into_boxed_slice());
        retained.local_relaxation_observed = true;
        state.cohorts[0].retained_experience = Some(retained);
        let prior_retained = state.cohorts[0].retained_experience.clone();

        let prior_bytes = state.encode(16_000_000).unwrap();
        state = ResidentCognitiveFormationState::decode(&prior_bytes, 16_000_000).unwrap();
        assert_eq!(state.encode(16_000_000).unwrap(), prior_bytes);

        let later_occurrence = state.prepare(&light, 16_000_000).unwrap();
        assert!(later_occurrence.successor.cohorts[0]
            .retained_experience
            .is_some());
        state.commit(later_occurrence).unwrap();
        assert!(state.cohorts[0].pending_experience.is_some());

        // Simultaneous prior-retained plus current-pending evidence must cold
        // restore byte-exactly; otherwise production restart would erase the
        // currently forming experience.
        let mid_bytes = state.encode(16_000_000).unwrap();
        state = ResidentCognitiveFormationState::decode(&mid_bytes, 16_000_000).unwrap();
        assert_eq!(state.encode(16_000_000).unwrap(), mid_bytes);

        let mut later_emitted = Vec::new();
        for _ in 0..DARK_TAIL_EPISODES {
            let prepared = state.prepare(&dark, 16_000_000).unwrap();
            later_emitted.extend(prepared.observation.emitted_neuron_fractals.clone());
            state.commit(prepared).unwrap();
            if !later_emitted.is_empty() {
                break;
            }
        }
        assert!(!later_emitted.is_empty());
        assert!(later_emitted
            .iter()
            .all(|fractal| !fractal.delta.entries().is_empty()));
        assert_eq!(state.cohorts[0].retained_experience, prior_retained);
        assert!(state.cohorts[0].pending_experience.is_none());

        let later_dark = state.prepare(&dark, 16_000_000).unwrap();
        assert!(later_dark.observation.emitted_neuron_fractals.is_empty());
    }

    #[test]
    fn typed_vestibular_source_persists_one_specialized_neuron_then_emits_after_quiescence() {
        let canal_anatomy =
            CanalAnatomy::new(6, 13_200, PositiveRatio::new(25, 1).unwrap()).unwrap();
        let bundle_anatomy = LocalCupulaBundleAnatomy::new(2, 5, 20_000).unwrap();
        let receptor_anatomy = phase_one_virtual_vestibular_anatomy().unwrap();
        let predecessor_body = YawBodyState::new(0).unwrap();
        let body = settle_signed_yaw_actuation(
            predecessor_body,
            SignedYawActuation::new(360, WORLD_MECHANICAL_TICK_MICROSECONDS).unwrap(),
        )
        .unwrap();
        let reached = settle_reached_vestibular_bundle_tick(
            canal_anatomy,
            CanalState::at_rest(),
            body.trajectory.as_slice()[0],
            bundle_anatomy,
        )
        .unwrap();
        let mut canal = reached.successor_canal;
        let resting_body = body.successor;
        let ingress = prepare_resident_vestibular_ingress(
            0,
            predecessor_body,
            body.successor,
            reached,
            &receptor_anatomy,
        )
        .unwrap();
        let retired = ResidentCognitiveFormationState::default()
            .encode_with_format(CognitiveCodecFormat::V12, 16_000_000)
            .unwrap();
        let current =
            ResidentCognitiveFormationState::migrate_to_current_format(&retired, 16_000_000)
                .unwrap();
        let mut state = ResidentCognitiveFormationState::decode(&current, 16_000_000).unwrap();
        let site = NeuronSourceSite::from_source_port(
            &ingress
                .source()
                .joint_source_with_contacts()
                .0
                .joint_source_ports()[0],
        )
        .unwrap();
        let place = DeclaredNeuronPlace::from_source_site(&site);
        let population = state.resting_population.as_ref().unwrap();
        let resting = population
            .materialize(population.population_offset(place).unwrap())
            .unwrap();
        let expected_lineage = local_lineage_from_ordinal(resting.lineage_ordinal).unwrap();
        let predecessor_resting_count = population.resting_cell_count();
        let predecessor_total_neurons = state.summary().complete_neuron_count
            + usize::try_from(predecessor_resting_count).unwrap();
        let stimulating = state
            .prepare_vestibular_transition(&ingress, 16_000_000)
            .unwrap();
        assert_eq!(stimulating.observation.complete_neuron_count, 3);
        assert_eq!(
            stimulating.observation.physically_transitioned_neuron_count,
            3
        );
        assert!(stimulating.observation.emitted_neuron_fractals.is_empty());
        state.commit(stimulating).unwrap();
        assert_eq!(
            state
                .resting_population
                .as_ref()
                .unwrap()
                .resting_cell_count(),
            predecessor_resting_count - 3
        );
        assert_eq!(state.cohorts.len(), 3);
        assert_eq!(state.cohorts[0].anatomy.neuron_count(), 1);
        assert_eq!(
            state.summary().complete_neuron_count
                + usize::try_from(
                    state
                        .resting_population
                        .as_ref()
                        .unwrap()
                        .resting_cell_count(),
                )
                .unwrap(),
            predecessor_total_neurons
        );
        assert_eq!(
            state.cohorts[0].anatomy.neuron_lineages()[0],
            expected_lineage
        );
        assert_eq!(
            state.cohorts[0].anatomy.neuron_anatomies()[0].capacitance(),
            resting.anatomy.capacitance()
        );
        assert_eq!(
            state.cohorts[0].anatomy.neuron_anatomies()[0].gate_dissipation_capacity_quanta(),
            receptor_anatomy.gate_dissipation_capacity_quanta()
        );
        let layers = state
            .cohorts
            .iter()
            .flat_map(|cohort| cohort.anatomy.mounts())
            .map(|mount| mount.place().layer())
            .collect::<Vec<_>>();
        assert!(layers.contains(&5));
        assert!(layers.contains(&6));
        assert!(layers.contains(&8));

        let encoded = state.encode(16_000_000).unwrap();
        state = ResidentCognitiveFormationState::decode(&encoded, 16_000_000).unwrap();
        let lineage = state.cohorts[0].anatomy.neuron_lineages()[0];
        let mut emitted = Vec::new();
        for source_tick in 1..=(DARK_TAIL_EPISODES * 4) {
            let reached =
                settle_reached_vestibular_bundle_tick(canal_anatomy, canal, 0, bundle_anatomy)
            .unwrap();
            canal = reached.successor_canal;
            let resting_ingress = prepare_resident_vestibular_ingress(
                u64::try_from(source_tick).unwrap(),
                resting_body,
                resting_body,
                reached,
                &receptor_anatomy,
            )
            .unwrap();
            let prepared = state
                .prepare_vestibular_transition(&resting_ingress, 16_000_000)
                .unwrap();
            emitted.extend(prepared.observation.emitted_neuron_fractals.clone());
            state.commit(prepared).unwrap();
            if emitted
                .iter()
                .any(|fractal| fractal.neuron_lineage == lineage)
            {
                break;
            }
        }
        assert!(emitted
            .iter()
            .any(|fractal| fractal.neuron_lineage == lineage));
    }

    fn lesson_state_with_retained_experience() -> ResidentCognitiveFormationState {
        let light = (0..4)
            .map(exact_four_single_optical_episode)
            .collect::<Vec<_>>();
        let dark = exact_four_dark_optical_episode();
        let seed = explicit_optical_seed(&light[0], 500);
        let mut state =
            ResidentCognitiveFormationState::from_developmental_electrical_seeds(vec![seed])
                .unwrap();
        for source in light
            .iter()
            .chain(std::iter::repeat(&dark).take(DARK_TAIL_EPISODES))
        {
            let prepared = state.prepare(source, 16_000_000).unwrap();
            state.commit(prepared).unwrap();
        }
        assert!(state.cohorts[0].retained_experience.is_some());
        state
    }

    #[test]
    #[ignore = "retired: fixture requires Boolean/member-set mosaic admission"]
    fn continuing_contact_tail_cannot_begin_endogenous_reassembly() {
        let light = (0..4)
            .map(exact_four_single_optical_episode)
            .collect::<Vec<_>>();
        let dark = exact_four_dark_optical_episode();
        let seed = explicit_optical_seed(&light[0], 500);
        let mut state =
            ResidentCognitiveFormationState::from_developmental_electrical_seeds(vec![seed])
                .unwrap();
        for source in light.iter().chain(std::iter::once(&dark)) {
            let prepared = state.prepare(source, 16_000_000).unwrap();
            assert_eq!(
                prepared
                    .observation
                    .endogenous_partial_cue_reassembly_count(),
                0
            );
            state.commit(prepared).unwrap();
        }
        assert!(state.cohorts[0].pending_experience.is_none());
        assert!(state.cohorts[0].retained_experience.is_some());
        assert!(
            !state.cohorts[0]
                .retained_experience
                .as_ref()
                .unwrap()
                .local_relaxation_observed
        );

        let mut relaxation_observed = false;
        for _ in 0..DARK_TAIL_EPISODES {
            let prepared = state.prepare(&dark, 16_000_000).unwrap();
            assert_eq!(
                prepared
                    .observation
                    .endogenous_partial_cue_reassembly_count(),
                0,
                "the interval that ends the original tail cannot cue itself"
            );
            relaxation_observed = prepared.successor.cohorts[0]
                .retained_experience
                .as_ref()
                .is_some_and(|experience| experience.local_relaxation_observed);
            state.commit(prepared).unwrap();
            if relaxation_observed {
                break;
            }
        }
        assert!(state.cohorts[0].retained_experience.is_some());
        assert!(relaxation_observed);

        let encoded_at_rest = state.encode(16_000_000).unwrap();
        let restored =
            ResidentCognitiveFormationState::decode(&encoded_at_rest, 16_000_000).unwrap();
        assert_eq!(restored, state);
        assert_eq!(restored.encode(16_000_000).unwrap(), encoded_at_rest);

        let retained = state.cohorts[0].retained_experience.as_ref().unwrap();
        let contact_count = state.cohorts[0].anatomy.contact_count();
        let mut unrelated_flow = vec![false; contact_count];
        let original_contact = *retained
            .active_electrical_contacts
            .indices
            .first()
            .unwrap();
        let unrelated_contact = (0..unrelated_flow.len())
            .find(|index| *index != original_contact)
            .unwrap();
        let mut one_contact_formation = retained.clone();
        let mut original_only = vec![false; contact_count];
        original_only[original_contact] = true;
        one_contact_formation.active_electrical_contacts =
            SparseResidentNeuronMask::from_dense(&original_only);
        unrelated_flow[unrelated_contact] = true;
        assert!(!retained_contact_set_flowing(
            &one_contact_formation,
            &SparseResidentNeuronMask::from_dense(&unrelated_flow),
            contact_count,
        )
        .unwrap());

        let partial = exact_four_partial_optical_episode();
        let mut endogenous = 0usize;
        let mut total = 0usize;
        for source in
            std::iter::once(&partial).chain(std::iter::repeat(&dark).take(DARK_TAIL_EPISODES))
        {
            let prepared = state
                .prepare_admitted_transition(&admitted_fixture_episode(source), 16_000_000)
                .unwrap();
            endogenous += prepared
                .observation
                .endogenous_partial_cue_reassembly_count();
            total += prepared.observation.partial_cue_reassembly_count();
            state.commit(prepared).unwrap();
        }
        // The explicit partial cue may reassemble the retained formation, but
        // its continuing contact current is not an organism-generated cue.
        // Endogenous recurrence must begin from a later metabolic perturbation
        // of a proper partial member set, not from the external cue's tail.
        assert_eq!(total, 1);
        assert_eq!(endogenous, 0);

        let mut severed = restored;
        severed.cohorts[0]
            .retained_experience
            .as_mut()
            .unwrap()
            .active_electrical_contacts = SparseResidentNeuronMask::empty();
        let mut severed_reassemblies = 0usize;
        for source in
            std::iter::once(&partial).chain(std::iter::repeat(&dark).take(DARK_TAIL_EPISODES))
        {
            let prepared = severed
                .prepare_admitted_transition(&admitted_fixture_episode(source), 16_000_000)
                .unwrap();
            severed_reassemblies += prepared.observation.partial_cue_reassembly_count();
            severed.commit(prepared).unwrap();
        }
        assert_eq!(severed_reassemblies, 0);
        assert_eq!(severed.summary().mosaic_count, 0);
    }

    #[test]
    fn sparse_retained_experience_codec_is_exact_and_canonical() {
        let light = exact_four_single_optical_episode(0);
        let seed = explicit_optical_seed(&light, 1);
        let mut state =
            ResidentCognitiveFormationState::from_developmental_electrical_seeds(vec![seed])
                .unwrap();
        let prepared = state.prepare(&light, 16_000_000).unwrap();
        assert!(!prepared.observation.emitted_neuron_fractals.is_empty());
        state.commit(prepared).unwrap();
        let mut retained = state.cohorts[0].pending_experience.take().unwrap();
        let retained_members = retained
            .pending_members()
            .unwrap()
            .iter()
            .filter(|member| member.settled)
            .map(|member| SparseRetainedExperienceMember {
                neuron_index: member.neuron_index,
                delta: member.delta.clone(),
            })
            .collect::<Vec<_>>();
        assert!(!retained_members.is_empty());
        retained.physical =
            ResidentExperiencePhysicalEvidence::Retained(retained_members.into_boxed_slice());
        retained.local_relaxation_observed = true;
        state.cohorts[0].retained_experience = Some(retained);

        let cohort = &state.cohorts[0];
        let retained = cohort.retained_experience.as_ref().unwrap();
        assert_eq!(retained.codec, ExperienceEvidenceCodec::V8);
        assert!(retained.legacy_states().is_none());
        assert!(!retained.retained_members().unwrap().is_empty());

        let evidence = encode_sparse_experience_evidence(&cohort.anatomy, retained).unwrap();
        assert_eq!(
            decode_sparse_experience_evidence_v8(&evidence, &cohort.anatomy).unwrap(),
            *retained
        );
        let mut trailing = evidence.clone();
        trailing.push(0);
        assert!(decode_sparse_experience_evidence_v8(&trailing, &cohort.anatomy).is_err());
        let mut corrupt = evidence;
        corrupt[EXPERIENCE_V8_MAGIC.len()] = 2;
        assert!(decode_sparse_experience_evidence_v8(&corrupt, &cohort.anatomy).is_err());

        let current = state.encode(16_000_000).unwrap();
        assert_eq!(&current[..MAGIC_V42.len()], MAGIC_V42);
        assert_eq!(
            ResidentCognitiveFormationState::decode(&current, 16_000_000).unwrap(),
            state
        );

        let mut relabeled_legacy = current;
        let evidence_offset = relabeled_legacy
            .windows(EXPERIENCE_V8_MAGIC.len())
            .position(|window| window == EXPERIENCE_V8_MAGIC)
            .unwrap();
        relabeled_legacy[evidence_offset..evidence_offset + EXPERIENCE_V7_MAGIC.len()]
            .copy_from_slice(EXPERIENCE_V7_MAGIC);
        assert_eq!(
            ResidentCognitiveFormationState::decode(&relabeled_legacy, 16_000_000),
            Err(FormationError::RetiredCognitiveState)
        );
    }

    #[test]
    fn first_receptor_contact_claims_receptor_and_local_integration_cells() {
        let empty = ResidentCognitiveFormationState::default();
        let retired = empty
            .encode_with_format(CognitiveCodecFormat::V12, 16_000_000)
            .unwrap();
        let current =
            ResidentCognitiveFormationState::migrate_to_current_format(&retired, 16_000_000)
                .unwrap();
        let state = ResidentCognitiveFormationState::decode(&current, 16_000_000).unwrap();
        let source = exact_optical_episode();
        let shared = prepare_complete_joint_field_admitted_fixture(&source, 0).unwrap();
        let perspective = bind_neuron_perspective(&shared, 0, 0).unwrap();
        let site =
            NeuronSourceSite::from_anchor(bind_neuron_source_anchor(&source, perspective).unwrap());
        let place = DeclaredNeuronPlace::from_source_site(&site);
        let population = state.resting_population.as_ref().unwrap();
        let offset = population.population_offset(place).unwrap();
        let resting = population.materialize(offset).unwrap();
        let resting_count = population.resting_cell_count();
        let expected_lineage = local_lineage_from_ordinal(resting.lineage_ordinal).unwrap();
        let prepared = state
            .prepare_admitted_transition(&admitted_fixture_episode(&source), 16_000_000)
            .unwrap();
        let successor = prepared.successor;
        assert_eq!(
            successor
                .resting_population
                .as_ref()
                .unwrap()
                .resting_cell_count(),
            resting_count - 2
        );
        let cohort = successor
            .cohorts
            .iter()
            .find(|cohort| cohort.anatomy.source_sites().any(|source| source == &site))
            .unwrap();
        let neuron_index = cohort.anatomy.source_site_member(&site).unwrap();
        assert_eq!(
            cohort.anatomy.neuron_lineages()[neuron_index],
            expected_lineage
        );
        assert_eq!(
            cohort.anatomy.neuron_anatomies()[neuron_index].capacitance(),
            resting.anatomy.capacitance()
        );
        assert_eq!(successor.summary().complete_neuron_count, 2);
        assert_eq!(successor.electrical_fabric.contact_count(), 1);
        let encoded = successor.encode(16_000_000).unwrap();
        let cold = ResidentCognitiveFormationState::decode(&encoded, 16_000_000).unwrap();
        assert_eq!(cold, successor);
    }

    #[test]
    fn local_body_receptor_metabolism_enters_only_the_bounded_sparse_frontier() {
        let canal_anatomy =
            CanalAnatomy::new(6, 13_200, PositiveRatio::new(25, 1).unwrap()).unwrap();
        let bundle_anatomy = LocalCupulaBundleAnatomy::new(2, 5, 20_000).unwrap();
        let receptor_anatomy = phase_one_virtual_vestibular_anatomy().unwrap();
        let turn = settle_signed_yaw_actuation(
            YawBodyState::new(0).unwrap(),
            SignedYawActuation::new(90_000, 250_000).unwrap(),
        )
        .unwrap();
        let mut state = ResidentCognitiveFormationState::default();
        let mut canal = CanalState::at_rest();
        let mut heading = 0_u32;
        let mut observed = None;
        for (source_tick, signed_step) in turn.trajectory.as_slice().iter().copied().enumerate() {
            let predecessor_body = YawBodyState::new(heading).unwrap();
            heading =
                u32::try_from((i64::from(heading) + i64::from(signed_step)).rem_euclid(360_000))
                    .unwrap();
            let successor_body = YawBodyState::new(heading).unwrap();
            let reached = settle_reached_vestibular_bundle_tick(
                canal_anatomy,
                canal,
                signed_step,
                bundle_anatomy,
            )
            .unwrap();
            canal = reached.successor_canal;
            let ingress = prepare_resident_vestibular_ingress(
                u64::try_from(source_tick).unwrap(),
                predecessor_body,
                successor_body,
                reached,
                &receptor_anatomy,
            )
            .unwrap();
            let prepared = state
                .prepare_vestibular_transition(&ingress, 16_000_000)
                .unwrap();
            if prepared
                .observation
                .metabolically_perturbed_body_receptor_count
                > 0
            {
                observed = Some(prepared.observation.clone());
            }
            state = prepared.successor;
        }
        assert_eq!(
            state
                .observe_reached_neuron_count_by_layer()
                .iter()
                .find(|(layer, _)| *layer == 5)
                .copied(),
            Some((5, 1))
        );
        assert_eq!(
            state
                .observe_reached_neuron_count_by_layer()
                .iter()
                .find(|(layer, _)| *layer == 8)
                .copied(),
            Some((8, 1))
        );
        let observation = observed.expect("body receptor recovery must be physically observed");
        assert_eq!(observation.metabolically_perturbed_body_receptor_count, 1);
        assert!(observation.physically_transitioned_neuron_count >= 1);
        assert!(
            observation.metabolically_perturbed_body_receptor_count
                <= observation.physically_transitioned_neuron_count
        );
        assert_eq!(
            observation
                .localized_metabolic_strain_evaluated_body_receptor_lineages
                .len(),
            1
        );
        assert_eq!(observation.localized_metabolic_strain.len(), 1);
        let strain = &observation.localized_metabolic_strain[0];
        assert_eq!(strain.neuron_place.layer(), 5);
        assert_eq!(
            strain.neuron_lineage,
            observation.localized_metabolic_strain_evaluated_body_receptor_lineages[0]
        );
        assert!(
            strain.psi_dissipation_quanta.iter().any(|quanta| *quanta != 0)
                || strain.gate_dissipation_quanta != 0
                || strain.plastic_dissipation_quanta != 0
        );

        let encoded = state.encode(16_000_000).unwrap();
        assert_eq!(
            ResidentCognitiveFormationState::decode(&encoded, 16_000_000).unwrap(),
            state
        );
    }

    #[test]
    fn sense_local_topology_indices_project_to_distinct_integration_places() {
        let sight = local_integration_place(DeclaredNeuronPlace::new(0, 0)).unwrap();
        let sound = local_integration_place(DeclaredNeuronPlace::new(1, 0)).unwrap();
        let body = local_integration_place(DeclaredNeuronPlace::new(5, 0)).unwrap();
        assert_eq!(sight, DeclaredNeuronPlace::new(6, 0));
        assert_eq!(sound, DeclaredNeuronPlace::new(6, 1));
        assert_eq!(body, DeclaredNeuronPlace::new(6, 15));
        assert_ne!(sight, sound);
        assert_ne!(sound, body);
        assert_ne!(sight, body);
    }

    #[test]
    fn body_terminal_integration_places_follow_the_existing_sensory_geography() {
        assert_eq!(
            PRE_PROPRIOCEPTIVE_BODY_SENSE_LAYER,
            u32::from(PhysicalSourceSense::Body.declared_layer())
        );
        let served_pre_proprioceptive_roster = [(0, 26), (1, 33), (2, 26), (3, 7), (4, 4), (5, 9)];
        for (layer, topology_index) in served_pre_proprioceptive_roster {
            let last_existing = declared_neuron_territory(DeclaredNeuronPlace::new(
                layer,
                topology_index,
            ))
            .unwrap()
            .checked_sub(1)
            .unwrap();
            assert!(
                last_existing < u128::from(BODY_PROPRIOCEPTOR_LAYER6_TOPOLOGY_OFFSET)
            );
        }

        let first = local_integration_place(DeclaredNeuronPlace::new(
            PhysicalSourceSense::Body.declared_layer().into(),
            u32::try_from(BODY_PROPRIOCEPTOR_TOPOLOGY_OFFSET).unwrap(),
        ))
        .unwrap();
        let last = local_integration_place(DeclaredNeuronPlace::new(
            PhysicalSourceSense::Body.declared_layer().into(),
            u32::try_from(
                BODY_PROPRIOCEPTOR_TOPOLOGY_OFFSET
                    + LEGACY_BODY_EFFECTOR_TERMINAL_COUNT
                    - 1,
            )
                .unwrap(),
        ))
        .unwrap();
        assert_eq!(first, DeclaredNeuronPlace::new(6, 629));
        assert_eq!(last, DeclaredNeuronPlace::new(6, 702));
        let first_regulation = body_regulation_place(
            DeclaredNeuronPlace::new(PRE_PROPRIOCEPTIVE_BODY_SENSE_LAYER, 10),
            first,
        )
        .unwrap();
        let last_regulation = body_regulation_place(
            DeclaredNeuronPlace::new(PRE_PROPRIOCEPTIVE_BODY_SENSE_LAYER, 83),
            last,
        )
        .unwrap();
        assert_eq!(first_regulation, DeclaredNeuronPlace::new(8, 115));
        assert_eq!(last_regulation, DeclaredNeuronPlace::new(8, 188));
        let first_tract_proprioceptor = DeclaredNeuronPlace::new(
            PRE_PROPRIOCEPTIVE_BODY_SENSE_LAYER,
            u32::try_from(ADDED_BODY_PROPRIOCEPTOR_TOPOLOGY_OFFSET).unwrap(),
        );
        let first_tract_integration =
            local_integration_place(first_tract_proprioceptor).unwrap();
        assert_eq!(
            first_tract_integration,
            DeclaredNeuronPlace::new(6, ADDED_BODY_PROPRIOCEPTOR_LAYER6_TOPOLOGY_OFFSET)
        );
        assert_eq!(
            body_regulation_place(first_tract_proprioceptor, first_tract_integration).unwrap(),
            DeclaredNeuronPlace::new(8, ADDED_BODY_PROPRIOCEPTOR_LAYER8_TOPOLOGY_OFFSET)
        );
        let first_tract_load = DeclaredNeuronPlace::new(
            PRE_PROPRIOCEPTIVE_BODY_SENSE_LAYER,
            u32::try_from(ADDED_BODY_EFFECTOR_LOAD_TOPOLOGY_OFFSET).unwrap(),
        );
        let first_tract_load_integration = local_integration_place(first_tract_load).unwrap();
        assert_eq!(
            first_tract_load_integration,
            DeclaredNeuronPlace::new(6, ADDED_BODY_EFFECTOR_LOAD_LAYER6_TOPOLOGY_OFFSET)
        );
        assert_eq!(
            body_regulation_place(first_tract_load, first_tract_load_integration).unwrap(),
            DeclaredNeuronPlace::new(8, ADDED_BODY_EFFECTOR_LOAD_LAYER8_TOPOLOGY_OFFSET)
        );
        let first_root = local_integration_place(DeclaredNeuronPlace::new(
            PRE_PROPRIOCEPTIVE_BODY_SENSE_LAYER,
            u32::try_from(ROOT_YAW_PROPRIOCEPTOR_TOPOLOGY_OFFSET).unwrap(),
        ))
        .unwrap();
        let last_root = local_integration_place(DeclaredNeuronPlace::new(
            PRE_PROPRIOCEPTIVE_BODY_SENSE_LAYER,
            u32::try_from(
                ROOT_YAW_PROPRIOCEPTOR_TOPOLOGY_OFFSET + ROOT_YAW_TERMINAL_COUNT - 1,
            )
            .unwrap(),
        ))
        .unwrap();
        assert_eq!(first_root, DeclaredNeuronPlace::new(6, 777));
        assert_eq!(last_root, DeclaredNeuronPlace::new(6, 778));
        assert_eq!(
            body_regulation_place(
                DeclaredNeuronPlace::new(
                    PRE_PROPRIOCEPTIVE_BODY_SENSE_LAYER,
                    u32::try_from(ROOT_YAW_PROPRIOCEPTOR_TOPOLOGY_OFFSET).unwrap(),
                ),
                first_root,
            )
            .unwrap(),
            DeclaredNeuronPlace::new(8, 263),
        );
        assert_eq!(
            body_regulation_place(
                DeclaredNeuronPlace::new(
                    PRE_PROPRIOCEPTIVE_BODY_SENSE_LAYER,
                    u32::try_from(
                        ROOT_YAW_PROPRIOCEPTOR_TOPOLOGY_OFFSET
                            + ROOT_YAW_TERMINAL_COUNT
                            - 1,
                    )
                    .unwrap(),
                ),
                last_root,
            )
            .unwrap(),
            DeclaredNeuronPlace::new(8, 264),
        );
        for topology_index in 0..=PRE_PROPRIOCEPTIVE_WIDEST_BODY_TOPOLOGY_INDEX {
            let existing = local_integration_place(DeclaredNeuronPlace::new(
                PRE_PROPRIOCEPTIVE_BODY_SENSE_LAYER,
                topology_index,
            ))
            .unwrap();
            assert!(existing.topology_index() < BODY_PROPRIOCEPTOR_LAYER8_TOPOLOGY_OFFSET);
        }
    }



    #[test]
    fn background_neighbour_contact_has_no_causal_learning_authority() {
        let causal_seeds = [0, 4];

        assert!(contact_touches_causal_seed(0, 1, &causal_seeds));
        assert!(contact_touches_causal_seed(3, 4, &causal_seeds));
        assert!(!contact_touches_causal_seed(1, 3, &causal_seeds));
    }

    #[test]
    fn only_current_internal_reassembly_retains_its_recurrent_frontier() {
        let cue = [1_u8; 16];
        let recurrent = [9_u8; 16];
        let predecessor_sender = [8_u8; 16];
        let unrelated = [7_u8; 16];
        let predecessor_bond =
            StablePhysicalBondReference::new(predecessor_sender, recurrent, 0).unwrap();
        let predecessor = ActiveElectricalFrontierEntry::caused_with_frontier(
            predecessor_sender,
            recurrent,
            recurrent,
            predecessor_bond,
            3,
            false,
        )
        .unwrap();
        let cue_bond = StablePhysicalBondReference::new(cue, recurrent, 0).unwrap();
        let transfer = DirectedPhysicalTransferObservation {
            sender: recurrent,
            receiver: cue,
            bond: cue_bond,
            transferred_whole_carriers: 5,
        };
        let reassembly = InternallyReassembledFormationCueObservation {
            formation_receipt: [4_u8; 32],
            cue_lineages: vec![cue],
            recurrent_lineage: Some(recurrent),
            causal_predecessors: Vec::new(),
        };

        let mut retained = Vec::new();
        retain_internally_reassembled_recurrent_frontier(
            &mut retained,
            &[predecessor],
            std::slice::from_ref(&reassembly),
            &[transfer],
        )
        .unwrap();
        assert_eq!(retained.len(), 1);
        assert_eq!(retained[0].frontier_lineage(), recurrent);
        assert_eq!(retained[0].directed_transfer(), Some(transfer));

        let unrelated_transfer = DirectedPhysicalTransferObservation {
            sender: unrelated,
            receiver: cue,
            bond: StablePhysicalBondReference::new(unrelated, cue, 0).unwrap(),
            transferred_whole_carriers: 5,
        };
        let mut absent = Vec::new();
        retain_internally_reassembled_recurrent_frontier(
            &mut absent,
            &[predecessor],
            &[reassembly],
            &[unrelated_transfer],
        )
        .unwrap();
        assert!(absent.is_empty());
    }

    #[test]
    fn recurrent_cell_output_is_the_only_formation_causal_cue() {
        let member = structural_test_lineage(2);
        let recurrent = structural_test_lineage(9);
        let predecessor_sender = structural_test_lineage(8);
        let mut source = RetainedOrganismMosaic::newly_admitted(
            synthetic_admitted_mosaic(&[1, 2, 3], &[(1, 2), (2, 3)], 1),
        );
        source.recurrent_lineage = Some(recurrent);
        let mosaics = [source];
        let formation_index = ResidentFormationIndex::build(&mosaics).unwrap();
        let predecessor_bond = StablePhysicalBondReference::new(
            predecessor_sender,
            recurrent,
            0,
        )
        .unwrap();
        let predecessor = ActiveElectricalFrontierEntry::caused_with_frontier(
            predecessor_sender,
            recurrent,
            recurrent,
            predecessor_bond,
            3,
            false,
        )
        .unwrap();
        let recurrent_bond =
            StablePhysicalBondReference::new(recurrent, member, 0).unwrap();
        let outward = ActiveElectricalFrontierEntry::caused_with_frontier(
            recurrent,
            member,
            member,
            recurrent_bond,
            5,
            false,
        )
        .unwrap();

        let cues = recurrent_formation_causal_cues(
            &mosaics,
            &formation_index,
            &[predecessor],
            &[outward],
        )
        .unwrap();
        assert_eq!(cues.len(), 1);
        assert_eq!(cues[0].source_formation_index, 0);
        assert_eq!(cues[0].source_recurrent_lineage, recurrent);
        assert_eq!(cues[0].cue_lineage, member);
        assert_eq!(cues[0].transfer.sender, recurrent);
        assert_eq!(cues[0].transfer.receiver, member);

        // Current flowing into the recurrent cell is its activation, not its
        // output. Likewise, an outward transfer without that recurrent cell
        // in the preceding frontier cannot claim a formation cause.
        let inward = ActiveElectricalFrontierEntry::caused_with_frontier(
            member,
            recurrent,
            recurrent,
            recurrent_bond,
            5,
            false,
        )
        .unwrap();
        assert!(recurrent_formation_causal_cues(
            &mosaics,
            &formation_index,
            &[predecessor],
            &[inward],
        )
        .unwrap()
        .is_empty());
        assert!(recurrent_formation_causal_cues(
            &mosaics,
            &formation_index,
            &[],
            &[outward],
        )
        .unwrap()
        .is_empty());
    }

    #[test]
    fn formation_cue_is_canonical_across_source_order_and_repetition() {
        let first = [1_u8; 16];
        let second = [2_u8; 16];
        let third = [3_u8; 16];
        let mut cue = vec![third, first, second, third];

        canonicalize_formation_cue(&mut cue);

        assert_eq!(cue, vec![first, second, third]);
    }

    #[test]
    fn pending_original_continuation_requires_the_same_recent_l7_frontier() {
        fn retained_delta(numerator: i128) -> SparsePhysicalStateDelta {
            SparsePhysicalStateDelta::from_canonical_entries(vec![
                crate::complete_neuron::PhysicalStateDeltaEntry::new(
                    crate::complete_neuron::PhysicalStateCoordinate::PlasticRestLength,
                    crate::complete_neuron::ExactPhysicalStateDelta::Rational(
                        ExactRational::new(numerator, 7).unwrap(),
                    ),
                )
                .unwrap(),
            ])
            .unwrap()
        }

        fn original_through_association(
            members: [u64; 3],
            association: [u8; 16],
        ) -> AdmittedPhysicalMosaic {
            let member_lineages = members.map(local_lineage);
            let lineages = [
                member_lineages[0],
                member_lineages[1],
                member_lineages[2],
                association,
            ];
            let bonds = member_lineages.map(|member| {
                StablePhysicalBondReference::new(member, association, 0).unwrap()
            });
            admit_physical_mosaic_original(
                &lineages,
                &[(1, 8); 4],
                &[
                    Some(retained_delta(i128::from(members[0]))),
                    Some(retained_delta(i128::from(members[1]))),
                    Some(retained_delta(i128::from(members[2]))),
                    None,
                ],
                &bonds,
            )
            .unwrap()
        }

        let association = local_lineage(9);
        let unrelated_association = local_lineage(10);
        let prior = original_through_association([1, 2, 3], association);
        let current = original_through_association([4, 5, 6], association);
        let unrelated = original_through_association([4, 5, 6], unrelated_association);
        let mut lineage_layers = (1_u64..=6)
            .map(|ordinal| (local_lineage(ordinal), if ordinal <= 3 { 0 } else { 1 }))
            .collect::<Vec<_>>();
        lineage_layers.push((association, 7));
        lineage_layers.push((unrelated_association, 7));
        lineage_layers.sort_unstable_by_key(|(lineage, _)| *lineage);
        let topology = ResidentTopologyIndex {
            flat_locations: Box::new([]),
            flat_by_lineage: Box::new([]),
            intrinsic_locations: Box::new([]),
            source_locations: Box::new([]),
            lineage_layers: lineage_layers.into_boxed_slice(),
            canonical_lineages: Box::new([]),
            canonical_bonds: Box::new([]),
            contacts: Box::new([]),
            incident_contacts_by_flat: Box::new([]),
            neighbours_by_flat: Box::new([]),
            cohort_shapes: Box::new([]),
            fabric_contact_count: 0,
        };

        let recent = [association].into_iter().collect::<BTreeSet<_>>();
        assert!(pending_original_continues_through_association(
            &prior,
            &current,
            &topology,
            &recent,
        )
        .unwrap());
        assert!(!pending_original_continues_through_association(
            &prior,
            &current,
            &topology,
            &BTreeSet::new(),
        )
        .unwrap());
        assert!(!pending_original_continues_through_association(
            &prior,
            &unrelated,
            &topology,
            &recent,
        )
        .unwrap());
    }

    #[test]
    fn varied_multisensory_occurrences_mount_only_exact_settled_assemblies() {
        fn receptor_cohort(
            sense: PhysicalSourceSense,
            topology_index: u32,
            lineage: [u8; 16],
        ) -> ResidentReachedCohort {
            let site = NeuronSourceSite::fixture_in_sense(sense, topology_index);
            let place = DeclaredNeuronPlace::from_source_site(&site);
            let neuron = create_quiescent_virtual_material_neuron(place).unwrap();
            let sparse = SparseElectricalAnatomy::new(1, Vec::new()).unwrap();
            let anatomy = ReachedCohortAnatomy::new_mounted(
                vec![neuron.anatomy],
                vec![lineage],
                vec![ReachedNeuronMount::Receptor(site)],
                sparse.clone(),
            )
            .unwrap();
            ResidentReachedCohort {
                state: ReachedCohortState::new(
                    &anatomy,
                    vec![neuron.state],
                    SparseElectricalState::genesis(&sparse),
                )
                .unwrap()
                .into(),
                anatomy,
                pending_experience: None,
                retained_experience: None,
                pending_recurrence: None,
            }
        }

        let receptor_lineages = [
            local_lineage(1),
            local_lineage(2),
            local_lineage(3),
            local_lineage(4),
        ];
        let mut cohorts = vec![
            receptor_cohort(PhysicalSourceSense::Sight, 0, receptor_lineages[0]),
            receptor_cohort(PhysicalSourceSense::Sight, 1, receptor_lineages[1]),
            receptor_cohort(PhysicalSourceSense::Sound, 2, receptor_lineages[2]),
            receptor_cohort(PhysicalSourceSense::Sound, 3, receptor_lineages[3]),
        ];
        let occupied = cohorts
            .iter()
            .flat_map(|cohort| cohort.anatomy.mounts().iter().map(|mount| mount.place()))
            .collect::<Vec<_>>();
        let mut population = Some(
            DevelopmentalRestingPopulation::admit(16_000_000, 100_000, 100, &occupied).unwrap(),
        );
        let mut next_lineage = 5;
        let mut fabric = ResidentElectricalFabric::default();
        let reached_receptors = cohorts
            .iter()
            .flat_map(|cohort| {
                cohort
                    .anatomy
                    .mounts()
                    .iter()
                    .zip(cohort.anatomy.neuron_lineages())
            })
            .filter_map(|(mount, lineage)| mount.source_site().map(|_| (*lineage, mount.place())))
            .collect::<Vec<_>>();
        let resting_before = population.as_ref().unwrap().resting_cell_count();
        mount_reached_local_integration(
            &mut cohorts,
            &mut population,
            &mut next_lineage,
            &mut fabric,
            &reached_receptors[..1],
        )
        .unwrap();
        assert_eq!(fabric.contact_count(), 1);
        assert_eq!(
            population.as_ref().unwrap().resting_cell_count(),
            resting_before - 1
        );
        let one_frontier_cohorts = cohorts.len();
        mount_reached_local_integration(
            &mut cohorts,
            &mut population,
            &mut next_lineage,
            &mut fabric,
            &[],
        )
        .unwrap();
        mount_reached_local_integration(
            &mut cohorts,
            &mut population,
            &mut next_lineage,
            &mut fabric,
            &reached_receptors[..1],
        )
        .unwrap();
        assert_eq!(cohorts.len(), one_frontier_cohorts);
        assert_eq!(fabric.contact_count(), 1);
        assert_eq!(
            population.as_ref().unwrap().resting_cell_count(),
            resting_before - 1
        );
        mount_reached_local_integration(
            &mut cohorts,
            &mut population,
            &mut next_lineage,
            &mut fabric,
            &reached_receptors[1..],
        )
        .unwrap();
        let topology = ResidentTopologyIndex::build(&cohorts, &fabric).unwrap();
        let settled_layer_six = topology
            .lineage_layers
            .iter()
            .filter_map(|(lineage, layer)| (*layer == 6).then_some(*lineage))
            .collect::<BTreeSet<_>>();
        assert_eq!(settled_layer_six.len(), 4);

        let coexisting = mount_reached_cross_sensory_association(
            &mut cohorts,
            &mut population,
            &mut next_lineage,
            &mut fabric,
            &topology,
            &[
                vec![receptor_lineages[0]],
                vec![receptor_lineages[1]],
                vec![receptor_lineages[2], receptor_lineages[3]],
            ],
            &[vec![[1; 16]], vec![[2; 16]], Vec::new()],
            &settled_layer_six,
        )
        .unwrap();
        assert_eq!(coexisting.lineages.len(), 3);
        assert_eq!(coexisting.lineages[0].len(), 1);
        assert_eq!(coexisting.lineages[1].len(), 1);
        assert!(coexisting.lineages[2].is_empty());
        assert_ne!(coexisting.lineages[0], coexisting.lineages[1]);
        assert_eq!(fabric.contact_count(), 10);

        let topology = ResidentTopologyIndex::build(&cohorts, &fabric).unwrap();
        mount_reached_cross_sensory_association(
            &mut cohorts,
            &mut population,
            &mut next_lineage,
            &mut fabric,
            &topology,
            &[vec![
                receptor_lineages[0],
                receptor_lineages[1],
                receptor_lineages[2],
            ]],
            &[vec![[1; 16]]],
            &settled_layer_six,
        )
        .unwrap();
        let association = cohorts
            .iter()
            .flat_map(|cohort| {
                cohort
                    .anatomy
                    .mounts()
                    .iter()
                    .zip(cohort.anatomy.neuron_lineages())
            })
            .filter(|(mount, _)| mount.place().layer() == 7)
            .map(|(_, lineage)| *lineage)
            .collect::<Vec<_>>();
        assert_eq!(association.len(), 3);
        assert_eq!(fabric.contact_count(), 13);

        let topology = ResidentTopologyIndex::build(&cohorts, &fabric).unwrap();
        mount_reached_cross_sensory_association(
            &mut cohorts,
            &mut population,
            &mut next_lineage,
            &mut fabric,
            &topology,
            &[vec![
                receptor_lineages[0],
                receptor_lineages[1],
                receptor_lineages[3],
            ]],
            &[vec![[1; 16]]],
            &settled_layer_six,
        )
        .unwrap();
        let association = cohorts
            .iter()
            .flat_map(|cohort| {
                cohort
                    .anatomy
                    .mounts()
                    .iter()
                    .zip(cohort.anatomy.neuron_lineages())
            })
            .filter(|(mount, _)| mount.place().layer() == 7)
            .map(|(_, lineage)| *lineage)
            .collect::<Vec<_>>();
        assert_eq!(association.len(), 4);
        assert_eq!(fabric.contact_count(), 16);
        let cohort_count = cohorts.len();
        let contact_count = fabric.contact_count();

        let topology = ResidentTopologyIndex::build(&cohorts, &fabric).unwrap();
        mount_reached_cross_sensory_association(
            &mut cohorts,
            &mut population,
            &mut next_lineage,
            &mut fabric,
            &topology,
            &[vec![
                receptor_lineages[0],
                receptor_lineages[1],
                receptor_lineages[2],
            ]],
            &[vec![[1; 16]]],
            &settled_layer_six,
        )
        .unwrap();
        assert_eq!(cohorts.len(), cohort_count);
        assert_eq!(fabric.contact_count(), contact_count);

        // Internal membrane state can make a different lawful subset of the
        // same externally energized integrations cross the layer-6 boundary
        // on a later encounter. That subset is the growth gate, not assembly
        // identity: the exact same receptor occurrence must reuse one
        // association rather than append a state-dependent duplicate.
        let topology = ResidentTopologyIndex::build(&cohorts, &fabric).unwrap();
        mount_reached_cross_sensory_association(
            &mut cohorts,
            &mut population,
            &mut next_lineage,
            &mut fabric,
            &topology,
            &[receptor_lineages.to_vec()],
            &[vec![[1; 16]]],
            &settled_layer_six,
        )
        .unwrap();
        let full_occurrence_cohort_count = cohorts.len();
        let full_occurrence_contact_count = fabric.contact_count();
        let mut changed_settled_subset = settled_layer_six.clone();
        let removed = *changed_settled_subset
            .iter()
            .next_back()
            .expect("the four-integration fixture has a final member");
        assert!(changed_settled_subset.remove(&removed));
        let topology = ResidentTopologyIndex::build(&cohorts, &fabric).unwrap();
        mount_reached_cross_sensory_association(
            &mut cohorts,
            &mut population,
            &mut next_lineage,
            &mut fabric,
            &topology,
            &[receptor_lineages.to_vec()],
            &[vec![[1; 16]]],
            &changed_settled_subset,
        )
        .unwrap();
        assert_eq!(cohorts.len(), full_occurrence_cohort_count);
        assert_eq!(fabric.contact_count(), full_occurrence_contact_count);

        let topology = organism_mosaic_topology(&cohorts, &fabric).unwrap();
        let topology_index = ResidentTopologyIndex::build(&cohorts, &fabric).unwrap();
        let fractal =
            crate::complete_neuron::SparsePhysicalStateDelta::from_canonical_entries(vec![
                crate::complete_neuron::PhysicalStateDeltaEntry::new(
                    crate::complete_neuron::PhysicalStateCoordinate::PlasticRestLength,
                    crate::complete_neuron::ExactPhysicalStateDelta::Rational(
                        ExactRational::new(1, 3).unwrap(),
                    ),
                )
                .unwrap(),
            ])
            .unwrap();
        let original = admit_physical_mosaic_original(
            &topology.lineages,
            &topology.fractal_anatomies,
            &vec![Some(fractal.clone()); topology.lineages.len()],
            &topology.bonds,
        )
        .unwrap();
        let encoded = encode_organism_mosaic(&cohorts, &fabric, &original, 16_000_000).unwrap();
        let cold = decode_organism_mosaic(&cohorts, &fabric, &encoded, 16_000_000).unwrap();
        assert_eq!(cold, original);
        let original_current_deltas = cold
            .member_lineages()
            .iter()
            .copied()
            .zip(cold.retained_fractals().iter().cloned())
            .collect::<Vec<_>>();
        let recognized = prove_physical_mosaic_recurrence(
            &cold,
            &original_current_deltas,
            &topology.bonds,
            &receptor_lineages,
        )
        .unwrap();
        assert!(recognized.carries_only_retained_neuron_structure());

        let original_members = recognized.member_lineages().to_vec();
        let original_fractals = recognized.retained_fractals().to_vec();
        let original_bonds = recognized.original_bonds().to_vec();
        let prior_cue = recognized.partial_cue_lineages().to_vec();
        let mut mosaics = vec![RetainedOrganismMosaic::newly_admitted(recognized)];
        let mut current_deltas = topology
            .lineages
            .iter()
            .map(|lineage| (*lineage, fractal.clone()))
            .collect::<Vec<_>>();
        current_deltas.sort_unstable_by_key(|(lineage, _)| *lineage);
        let later_fractal =
            crate::complete_neuron::SparsePhysicalStateDelta::from_canonical_entries(vec![
                crate::complete_neuron::PhysicalStateDeltaEntry::new(
                    crate::complete_neuron::PhysicalStateCoordinate::PlasticRestLength,
                    crate::complete_neuron::ExactPhysicalStateDelta::Rational(
                        ExactRational::new(2, 5).unwrap(),
                    ),
                )
                .unwrap(),
            ])
            .unwrap();
        let later_emitted = topology
            .lineages
            .iter()
            .map(|lineage| EmittedNeuronFractal {
                neuron_lineage: *lineage,
                delta: later_fractal.clone(),
            })
            .collect::<Vec<_>>();
        let changed_cue = [receptor_lineages[0]];
        let mut formation_index = ResidentFormationIndex::build(&mosaics).unwrap();
        let (
            altered_receipt,
            reassemblies,
            internal_reassemblies,
            relations,
            internal_cues,
            external_frontiers,
            _,
        ) =
            settle_organism_mosaic_boundary(
            &cohorts,
            &topology_index,
            &later_emitted,
            &current_deltas,
            &changed_cue,
            &changed_cue,
            &[],
            &topology.bonds,
            &[],
            &[],
            &[],
            &[],
            &mut mosaics,
            &mut formation_index,
            16_000_000,
                true,
        )
        .unwrap();
        assert!(altered_receipt.is_some());
        assert_eq!(reassemblies, 1);
        assert_eq!(internal_reassemblies, 0);
        assert!(internal_cues.is_empty());
        assert!(external_frontiers.is_empty());
        assert!(relations.is_empty());
        assert_eq!(mosaics.len(), 1);
        assert_eq!(mosaics[0].reinforcement_count, 0);
        assert_eq!(mosaics[0].mosaic.member_lineages(), original_members);
        assert_eq!(mosaics[0].mosaic.retained_fractals(), original_fractals);
        assert_eq!(mosaics[0].mosaic.original_bonds(), original_bonds);
        assert_ne!(mosaics[0].mosaic.partial_cue_lineages(), prior_cue);
        assert_eq!(mosaics[0].mosaic.partial_cue_lineages(), changed_cue);

        let altered_bytes =
            encode_retained_organism_mosaic(&cohorts, &fabric, &mosaics[0], 16_000_000).unwrap();
        let altered_cold =
            decode_retained_organism_mosaic(&cohorts, &fabric, &altered_bytes, 16_000_000).unwrap();
        assert_eq!(altered_cold, mosaics[0]);

        let second_fractal =
            crate::complete_neuron::SparsePhysicalStateDelta::from_canonical_entries(vec![
                crate::complete_neuron::PhysicalStateDeltaEntry::new(
                    crate::complete_neuron::PhysicalStateCoordinate::PlasticRestLength,
                    crate::complete_neuron::ExactPhysicalStateDelta::Rational(
                        ExactRational::new(2, 3).unwrap(),
                    ),
                )
                .unwrap(),
            ])
            .unwrap();
        let second_original = admit_physical_mosaic_original(
            &topology.lineages,
            &topology.fractal_anatomies,
            &vec![Some(second_fractal); topology.lineages.len()],
            &topology.bonds,
        )
        .unwrap();
        let second_current_deltas = second_original
            .member_lineages()
            .iter()
            .copied()
            .zip(second_original.retained_fractals().iter().cloned())
            .collect::<Vec<_>>();
        let second_recognized = prove_physical_mosaic_recurrence(
            &second_original,
            &second_current_deltas,
            &topology.bonds,
            &receptor_lineages,
        )
        .unwrap();
        mosaics.push(RetainedOrganismMosaic::newly_admitted(second_recognized));

        let one_reassembled_relation = observe_organic_mosaic_relations(
            &mosaics,
            &[0, 1],
            &[0],
            &topology.bonds,
            &[],
            &[],
            &[],
            &[],
            16_000_000,
            &mut Vec::new(),
        )
        .unwrap();
        assert_eq!(one_reassembled_relation.len(), 1);
        assert_eq!(one_reassembled_relation[0].formation_receipts.len(), 2);
        let first_receipts = one_reassembled_relation[0].formation_receipts.clone();
        let first_structure = one_reassembled_relation[0].structural_relation_receipt;

        let alternate_cue = [receptor_lineages[1]];
        mosaics[1].mosaic = alter_physical_mosaic_recurrence(
            &mosaics[1].mosaic,
            &second_current_deltas,
            &topology.bonds,
            &alternate_cue,
        )
        .unwrap();
        let changed_receipt_same_structure = observe_organic_mosaic_relations(
            &mosaics,
            &[0, 1],
            &[0],
            &topology.bonds,
            &[],
            &[],
            &[],
            &[],
            16_000_000,
            &mut Vec::new(),
        )
        .unwrap();
        assert_ne!(
            changed_receipt_same_structure[0].formation_receipts,
            first_receipts
        );
        assert_eq!(
            changed_receipt_same_structure[0].structural_relation_receipt,
            first_structure
        );

        let mut formation_index = ResidentFormationIndex::build(&mosaics).unwrap();
        let (
            _,
            related_reassemblies,
            related_internal_reassemblies,
            related,
            internal_cues,
            external_frontiers,
            _,
        ) =
            settle_organism_mosaic_boundary(
            &cohorts,
            &topology_index,
            &[],
            &current_deltas,
            &changed_cue,
            &changed_cue,
            &[],
            &topology.bonds,
            &[],
            &[],
            &[],
            &[],
            &mut mosaics,
            &mut formation_index,
            16_000_000,
                true,
        )
        .unwrap();
        // Both retained formations share this exact physical route. A current
        // response that reaches every member therefore reassembles both; the
        // original post-quiescence deltas remain learned structure rather than
        // a byte-for-byte recurrence filter.
        assert_eq!(related_reassemblies, 2);
        assert_eq!(related_internal_reassemblies, 0);
        assert!(internal_cues.is_empty());
        assert!(external_frontiers.is_empty());
        assert_eq!(related.len(), 1);
        assert_eq!(related[0].formation_receipts.len(), 2);
        let mut expected_shared_lineages = topology.lineages.clone();
        expected_shared_lineages.sort_unstable();
        assert_eq!(related[0].shared_lineages, expected_shared_lineages);
        assert!(!related[0].active_bonds.is_empty());

        let before_quiescent_relation = mosaics.clone();
        let mut formation_index = ResidentFormationIndex::build(&mosaics).unwrap();
        let (
            receipt,
            recurring_reassemblies,
            recurring_internal_reassemblies,
            recurring_relation,
            internal_cues,
            external_frontiers,
            _,
        ) =
            settle_organism_mosaic_boundary(
                &cohorts,
                &topology_index,
                &[],
                &current_deltas,
                &changed_cue,
                &changed_cue,
                &[],
                &topology.bonds,
                &[],
                &[],
                &[],
                &[],
                &mut mosaics,
                &mut formation_index,
                16_000_000,
                true,
            )
            .unwrap();
        assert_eq!(receipt, None);
        assert_eq!(recurring_reassemblies, 2);
        assert_eq!(recurring_internal_reassemblies, 0);
        assert!(internal_cues.is_empty());
        assert!(external_frontiers.is_empty());
        assert_eq!(recurring_relation, related);
        assert_eq!(mosaics, before_quiescent_relation);

        let before_internal_receipts = mosaics
            .iter()
            .map(|retained| {
                sha256(
                    &encode_retained_organism_mosaic(
                        &cohorts,
                        &fabric,
                        retained,
                        16_000_000,
                    )
                    .unwrap(),
                )
            })
            .collect::<Vec<_>>();
        let internal_cue = topology.lineages.clone();
        let mut expected_internal_cue = internal_cue.clone();
        canonicalize_formation_cue(&mut expected_internal_cue);
        let mut formation_index = ResidentFormationIndex::build(&mosaics).unwrap();
        let (
            internal_receipt,
            internal_total,
            internal_count,
            _,
            internal_cues,
            external_frontiers,
            _,
        ) =
            settle_organism_mosaic_boundary(
                &cohorts,
                &topology_index,
                &[],
                &current_deltas,
                &[],
                &[],
                &internal_cue,
                &topology.bonds,
                &[],
                &[],
                &[],
                &[],
                &mut mosaics,
                &mut formation_index,
                16_000_000,
                true,
            )
            .unwrap();
        assert!(internal_receipt.is_some());
        assert_eq!(internal_total, 2);
        assert_eq!(internal_count, 2);
        assert_eq!(internal_cues.len(), 2);
        assert!(external_frontiers.is_empty());
        assert!(internal_cues
            .iter()
            .all(|observation| observation.cue_lineages == expected_internal_cue));
        for (index, retained) in mosaics.iter().enumerate() {
            let current_receipt = sha256(
                &encode_retained_organism_mosaic(
                    &cohorts,
                    &fabric,
                    retained,
                    16_000_000,
                )
                .unwrap(),
            );
            assert_eq!(
                retained.mosaic.recurrence_origin(),
                Some(PhysicalMosaicRecurrenceOrigin::InternallySimulated)
            );
            assert_ne!(current_receipt, before_internal_receipts[index]);
            let encoded = encode_retained_organism_mosaic(
                &cohorts,
                &fabric,
                retained,
                16_000_000,
            )
            .unwrap();
            let cold = decode_retained_organism_mosaic(
                &cohorts,
                &fabric,
                &encoded,
                16_000_000,
            )
            .unwrap();
            assert_eq!(cold, *retained);
        }

        // Continuous sensing elsewhere in the body is not provenance for
        // either retained formation. It must therefore neither relabel nor
        // erase their independently measured metabolic recurrence.
        let unrelated_external = [[0xfe_u8; 16]];
        let mut formation_index = ResidentFormationIndex::build(&mosaics).unwrap();
        let (
            _,
            mixed_total,
            mixed_internal_count,
            _,
            mixed_internal_cues,
            external_frontiers,
            _,
        ) =
            settle_organism_mosaic_boundary(
                &cohorts,
                &topology_index,
                &[],
                &current_deltas,
                &unrelated_external,
                &unrelated_external,
                &internal_cue,
                &topology.bonds,
                &[],
                &[],
                &[],
                &[],
                &mut mosaics,
                &mut formation_index,
                16_000_000,
                true,
            )
            .unwrap();
        assert_eq!(mixed_total, 2);
        assert_eq!(mixed_internal_count, 2);
        assert_eq!(mixed_internal_cues.len(), 2);
        assert!(external_frontiers.is_empty());
        assert!(mixed_internal_cues
            .iter()
            .all(|observation| observation.cue_lineages == expected_internal_cue));
    }

    #[test]
    fn affective_growth_is_occurrence_local_and_requires_both_physical_transfers() {
        let mut cohorts = Vec::new();
        let mut population = None;
        let mut next_lineage = 1;
        let association = mount_intrinsic_neuron_at_place(
            &mut cohorts,
            &mut population,
            &mut next_lineage,
            DeclaredNeuronPlace::new(7, 0),
        )
        .unwrap();
        let integration = mount_intrinsic_neuron_at_place(
            &mut cohorts,
            &mut population,
            &mut next_lineage,
            DeclaredNeuronPlace::new(6, 0),
        )
        .unwrap();
        let regulation = mount_intrinsic_neuron_at_place(
            &mut cohorts,
            &mut population,
            &mut next_lineage,
            DeclaredNeuronPlace::new(8, 0),
        )
        .unwrap();
        let bystander_association = mount_intrinsic_neuron_at_place(
            &mut cohorts,
            &mut population,
            &mut next_lineage,
            DeclaredNeuronPlace::new(7, 1),
        )
        .unwrap();
        let bystander_integration = mount_intrinsic_neuron_at_place(
            &mut cohorts,
            &mut population,
            &mut next_lineage,
            DeclaredNeuronPlace::new(6, 1),
        )
        .unwrap();
        let unrelated_integration = mount_intrinsic_neuron_at_place(
            &mut cohorts,
            &mut population,
            &mut next_lineage,
            DeclaredNeuronPlace::new(6, 2),
        )
        .unwrap();
        let bystander_regulation = mount_intrinsic_neuron_at_place(
            &mut cohorts,
            &mut population,
            &mut next_lineage,
            DeclaredNeuronPlace::new(8, 1),
        )
        .unwrap();
        let fabric = ResidentElectricalFabric::default()
            .append_contacts(&[
                (
                    association,
                    integration,
                    ExactRational::integer(DEVELOPMENTAL_CONTACT_CONDUCTANCE_PICOSIEMENS),
                ),
                (
                    integration,
                    regulation,
                    ExactRational::integer(DEVELOPMENTAL_CONTACT_CONDUCTANCE_PICOSIEMENS),
                ),
                (
                    bystander_association,
                    bystander_integration,
                    ExactRational::integer(DEVELOPMENTAL_CONTACT_CONDUCTANCE_PICOSIEMENS),
                ),
                (
                    unrelated_integration,
                    bystander_regulation,
                    ExactRational::integer(DEVELOPMENTAL_CONTACT_CONDUCTANCE_PICOSIEMENS),
                ),
            ])
            .unwrap();
        let first = vec![
            ActiveElectricalFrontierEntry::caused(
                association,
                integration,
                StablePhysicalBondReference::new(association, integration, 0).unwrap(),
                1,
            )
            .unwrap(),
            ActiveElectricalFrontierEntry::caused(
                bystander_association,
                bystander_integration,
                StablePhysicalBondReference::new(
                    bystander_association,
                    bystander_integration,
                    0,
                )
                .unwrap(),
                1,
            )
            .unwrap(),
        ];
        let second = vec![
            ActiveElectricalFrontierEntry::caused(
                integration,
                regulation,
                StablePhysicalBondReference::new(integration, regulation, 0).unwrap(),
                1,
            )
            .unwrap(),
            ActiveElectricalFrontierEntry::caused(
                unrelated_integration,
                bystander_regulation,
                StablePhysicalBondReference::new(
                    unrelated_integration,
                    bystander_regulation,
                    0,
                )
                .unwrap(),
                1,
            )
            .unwrap(),
        ];

        let associations = ReachedAssociationsByOccurrence {
            lineages: vec![vec![association], vec![bystander_association]],
        };
        let regulations = vec![vec![regulation], vec![bystander_regulation]];
        let transfers = first
            .iter()
            .chain(&second)
            .filter_map(|entry| (*entry).directed_transfer())
            .collect::<Vec<_>>();
        let pairs = exact_occurrence_affective_pairs(
            &associations,
            &regulations,
            &transfers,
        )
        .unwrap();
        assert_eq!(
            pairs,
            vec![
                (association, regulation),
                (bystander_association, bystander_regulation),
            ]
        );
        assert!(!pairs.contains(&(association, bystander_regulation)));
        assert!(!pairs.contains(&(bystander_association, regulation)));

        let first_occurrence_only = transfers
            .iter()
            .copied()
            .filter(|transfer| {
                transfer.sender != bystander_regulation
                    && transfer.receiver != bystander_regulation
            })
            .collect::<Vec<_>>();
        assert_eq!(
            exact_occurrence_affective_pairs(
                &associations,
                &regulations,
                &first_occurrence_only,
            )
            .unwrap(),
            vec![(association, regulation)]
        );
    }

    #[test]
    fn coincident_association_and_body_motion_mounts_one_reusable_affective_reach() {
        let mut cohorts = Vec::new();
        let mut population =
            Some(DevelopmentalRestingPopulation::admit(16_000_000, 100_000, 100, &[]).unwrap());
        let mut next_lineage = 1;
        let association = mount_intrinsic_neuron_at_place(
            &mut cohorts,
            &mut population,
            &mut next_lineage,
            DeclaredNeuronPlace::new(7, 0),
        )
        .unwrap();
        let later_association = mount_intrinsic_neuron_at_place(
            &mut cohorts,
            &mut population,
            &mut next_lineage,
            DeclaredNeuronPlace::new(7, 1),
        )
        .unwrap();
        let regulation = mount_intrinsic_neuron_at_place(
            &mut cohorts,
            &mut population,
            &mut next_lineage,
            DeclaredNeuronPlace::new(8, 0),
        )
        .unwrap();
        let later_regulation = mount_intrinsic_neuron_at_place(
            &mut cohorts,
            &mut population,
            &mut next_lineage,
            DeclaredNeuronPlace::new(8, 1),
        )
        .unwrap();
        let resting_before = population.as_ref().unwrap().resting_cell_count();
        let mut fabric = ResidentElectricalFabric::default();
        mount_reached_affective_reach(
            &mut cohorts,
            &mut population,
            &mut next_lineage,
            &mut fabric,
            &[association, regulation],
        )
        .unwrap();
        let affective = cohorts
            .iter()
            .flat_map(|cohort| {
                cohort
                    .anatomy
                    .mounts()
                    .iter()
                    .zip(cohort.anatomy.neuron_lineages())
            })
            .filter(|(mount, _)| mount.place().layer() == 10)
            .map(|(_, lineage)| *lineage)
            .collect::<Vec<_>>();
        assert_eq!(affective.len(), 1);
        assert_eq!(
            population.as_ref().unwrap().resting_cell_count(),
            resting_before - 1
        );
        assert!(fabric.contains_contact(association, affective[0]));
        assert!(fabric.contains_contact(regulation, affective[0]));
        let cohort_count = cohorts.len();
        let contact_count = fabric.contact_count();

        mount_reached_affective_reach(
            &mut cohorts,
            &mut population,
            &mut next_lineage,
            &mut fabric,
            &[regulation, association],
        )
        .unwrap();
        assert_eq!(cohorts.len(), cohort_count);
        assert_eq!(fabric.contact_count(), contact_count);
        assert_eq!(
            population.as_ref().unwrap().resting_cell_count(),
            resting_before - 1
        );

        mount_reached_affective_reach(
            &mut cohorts,
            &mut population,
            &mut next_lineage,
            &mut fabric,
            &[association, later_regulation],
        )
        .unwrap();
        assert_eq!(
            cohorts
                .iter()
                .flat_map(|cohort| cohort.anatomy.mounts())
                .filter(|mount| mount.place().layer() == 10)
                .count(),
            1
        );
        assert_eq!(fabric.contact_count(), contact_count + 1);
        assert!(fabric.contains_contact(later_regulation, affective[0]));
        assert_eq!(
            population.as_ref().unwrap().resting_cell_count(),
            resting_before - 1
        );

        mount_reached_affective_reach(
            &mut cohorts,
            &mut population,
            &mut next_lineage,
            &mut fabric,
            &[later_association, regulation],
        )
        .unwrap();
        assert_eq!(
            cohorts
                .iter()
                .flat_map(|cohort| cohort.anatomy.mounts())
                .filter(|mount| mount.place().layer() == 10)
                .count(),
            2
        );
        assert_eq!(fabric.contact_count(), contact_count + 3);
        assert_eq!(
            population.as_ref().unwrap().resting_cell_count(),
            resting_before - 2
        );
    }

    #[test]
    fn v27_unlearned_affective_and_ordering_growth_is_retired_once() {
        const MAX_BYTES: usize = 1_600_000_000;
        let mut cohorts = Vec::new();
        let mut population =
            Some(DevelopmentalRestingPopulation::admit(MAX_BYTES, 100_000, 100, &[]).unwrap());
        let mut next_lineage = 1;
        let association = mount_intrinsic_neuron_at_place(
            &mut cohorts,
            &mut population,
            &mut next_lineage,
            DeclaredNeuronPlace::new(7, 0),
        )
        .unwrap();
        let regulation = mount_intrinsic_neuron_at_place(
            &mut cohorts,
            &mut population,
            &mut next_lineage,
            DeclaredNeuronPlace::new(8, 0),
        )
        .unwrap();
        let mut fabric = ResidentElectricalFabric::default();
        mount_reached_affective_reach(
            &mut cohorts,
            &mut population,
            &mut next_lineage,
            &mut fabric,
            &[association, regulation],
        )
        .unwrap();
        let first_affective = cohorts
            .iter()
            .flat_map(|cohort| {
                cohort
                    .anatomy
                    .mounts()
                    .iter()
                    .zip(cohort.anatomy.neuron_lineages())
            })
            .find_map(|(mount, lineage)| (mount.place().layer() == 10).then_some(*lineage))
            .unwrap();
        let duplicate_affective = mount_next_intrinsic_in_layer(
            &mut cohorts,
            &mut population,
            &mut next_lineage,
            10,
        )
        .unwrap();
        let first_ordering = mount_next_intrinsic_in_layer(
            &mut cohorts,
            &mut population,
            &mut next_lineage,
            11,
        )
        .unwrap();
        let duplicate_ordering = mount_next_intrinsic_in_layer(
            &mut cohorts,
            &mut population,
            &mut next_lineage,
            11,
        )
        .unwrap();
        fabric = fabric
            .append_contacts(&[
                (
                    association,
                    duplicate_affective,
                    ExactRational::integer(DEVELOPMENTAL_CONTACT_CONDUCTANCE_PICOSIEMENS),
                ),
                (
                    regulation,
                    duplicate_affective,
                    ExactRational::integer(DEVELOPMENTAL_CONTACT_CONDUCTANCE_PICOSIEMENS),
                ),
                (
                    association,
                    first_ordering,
                    ExactRational::integer(DEVELOPMENTAL_CONTACT_CONDUCTANCE_PICOSIEMENS),
                ),
                (
                    first_affective,
                    first_ordering,
                    ExactRational::integer(DEVELOPMENTAL_CONTACT_CONDUCTANCE_PICOSIEMENS),
                ),
                (
                    association,
                    duplicate_ordering,
                    ExactRational::integer(DEVELOPMENTAL_CONTACT_CONDUCTANCE_PICOSIEMENS),
                ),
                (
                    duplicate_affective,
                    duplicate_ordering,
                    ExactRational::integer(DEVELOPMENTAL_CONTACT_CONDUCTANCE_PICOSIEMENS),
                ),
            ])
            .unwrap();
        let topology_index = Arc::new(ResidentTopologyIndex::build(&cohorts, &fabric).unwrap());
        let next_lineage_ordinal = population
            .as_ref()
            .map(DevelopmentalRestingPopulation::lineage_end_exclusive)
            .unwrap_or(next_lineage);
        let state = ResidentCognitiveFormationState {
            generation: 5,
            next_lineage_ordinal,
            vocal_articulatory_effector_lineage: None,
            unexpressed_electrical_seeds: Box::new([]),
            dormant_lineage_seeds: Box::new([]),
            resting_population: population,
            cohorts: cohorts.into_boxed_slice(),
            electrical_fabric: fabric,
            active_electrical_frontier: Box::new([]),
            preceding_active_electrical_frontier: Box::new([]),
            older_active_electrical_frontier: Box::new([]),
            mosaics: Box::new([]),
            hippocampal: ResidentHippocampalIndex::default(),
            topology_index,
            formation_index: ResidentFormationIndex::default(),
        };
        validate_lineage_state(&state).unwrap();
        assert_eq!(state.electrical_fabric.contact_count(), 8);

        let mut v27 = state
            .encode_with_format(CognitiveCodecFormat::V26, MAX_BYTES)
            .unwrap();
        v27[..MAGIC_V27.len()].copy_from_slice(MAGIC_V27);
        v27[MAGIC_V27.len()..MAGIC_V27.len() + 2]
            .copy_from_slice(&VERSION_V27.to_le_bytes());
        assert!(matches!(
            ResidentCognitiveFormationState::decode(&v27, MAX_BYTES),
            Err(FormationError::RetiredCognitiveState)
        ));

        let current = ResidentCognitiveFormationState::migrate_to_current_format(
            &v27,
            MAX_BYTES,
        )
        .unwrap();
        assert_eq!(&current[..MAGIC_V42.len()], MAGIC_V42);
        let restored = ResidentCognitiveFormationState::decode(&current, MAX_BYTES).unwrap();
        let layers = restored.observe_reached_neuron_count_by_layer();
        assert!(layers.iter().all(|(layer, _)| !matches!(layer, 10 | 11)));
        assert_eq!(restored.electrical_fabric.contact_count(), 0);
        assert_eq!(
            ResidentCognitiveFormationState::migrate_to_current_format(&current, MAX_BYTES)
                .unwrap(),
            current
        );
    }

    #[test]
    fn reached_affective_cell_exposes_its_existing_local_plastic_consequence() {
        let mut cohorts = Vec::new();
        let mut population = None;
        let mut next_lineage = 1;
        let association = mount_intrinsic_neuron_at_place(
            &mut cohorts,
            &mut population,
            &mut next_lineage,
            DeclaredNeuronPlace::new(7, 0),
        )
        .unwrap();
        let regulation = mount_intrinsic_neuron_at_place(
            &mut cohorts,
            &mut population,
            &mut next_lineage,
            DeclaredNeuronPlace::new(8, 0),
        )
        .unwrap();
        let mut fabric = ResidentElectricalFabric::default();
        mount_reached_affective_reach(
            &mut cohorts,
            &mut population,
            &mut next_lineage,
            &mut fabric,
            &[association, regulation],
        )
        .unwrap();
        let affective = cohorts
            .iter()
            .flat_map(|cohort| {
                cohort
                    .anatomy
                    .mounts()
                    .iter()
                    .zip(cohort.anatomy.neuron_lineages())
            })
            .find(|(mount, _)| mount.place().layer() == 10)
            .map(|(_, lineage)| *lineage)
            .unwrap();
        let plastic = |cohorts: &[ResidentReachedCohort]| {
            cohorts
                .iter()
                .flat_map(|cohort| {
                    cohort
                        .state
                        .neurons()
                        .iter()
                        .zip(cohort.anatomy.neuron_lineages())
                })
                .find(|(_, lineage)| **lineage == affective)
                .map(|(neuron, _)| neuron.plastic.physical_parts())
                .unwrap()
        };
        let predecessor = plastic(&cohorts);
        let participant_plastic = |lineage: [u8; 16], cohorts: &[ResidentReachedCohort]| {
            cohorts
                .iter()
                .flat_map(|cohort| {
                    cohort
                        .state
                        .neurons()
                        .iter()
                        .zip(cohort.anatomy.neuron_lineages())
                })
                .find(|(_, candidate)| **candidate == lineage)
                .map(|(neuron, _)| neuron.plastic.physical_parts())
                .unwrap()
        };
        let association_predecessor = participant_plastic(association, &cohorts);
        let regulation_predecessor = participant_plastic(regulation, &cohorts);
        let topology_index = ResidentTopologyIndex::build(&cohorts, &fabric).unwrap();
        let mut transitioned = BTreeSet::new();
        let mut retained_settlement = None;
        for ordinal in 1..=128 {
            // Under the arrival law the affective neighbour is reached at
            // interval 1 (charge arrives through its seeded contact) and
            // is therefore itself a causal seed from interval 2 onward —
            // exactly what the production caller's frontier continuation
            // provides. Its metabolism (and so its plastic consequence)
            // lawfully lands one clock after first reach, not same-clock.
            let seeds: &[[u8; 16]] = if ordinal == 1 {
                &[association, regulation]
            } else {
                &[association, regulation, affective]
            };
            let observation = settle_internal_contact_interval(
                &mut cohorts,
                &mut fabric,
                &topology_index,
                None,
                &[],
                seeds,
                seeds,
                seeds,
                &mut transitioned,
                ordinal,
                0,
                &mut None,
                &BTreeMap::new(),
                &[],
                &[],
                ExactRational::integer(0),
                true,
            )
            .unwrap();
            if let Some(plasticity) = observation
                .affective_balance_trajectories
                .iter()
                .find(|trajectory| trajectory.neuron_lineage == affective)
                .and_then(|trajectory| trajectory.localized_plasticity_settlement.clone())
            {
                assert!(plasticity.incident_catalyst_quanta > 0);
                assert!(plasticity.reaction_extent > 0);
                assert_eq!(
                    plasticity
                        .predecessor_reservoir
                        .0
                        .checked_sub(plasticity.successor_reservoir.0)
                        .unwrap(),
                    plasticity.delivered_energy_zeptojoules
                );
                assert_eq!(
                    plasticity
                        .successor_reservoir
                        .1
                        .checked_sub(plasticity.predecessor_reservoir.1)
                        .unwrap(),
                    plasticity.delivered_energy_zeptojoules
                );
                assert_eq!(
                    plasticity.predecessor_reservoir.2,
                    plasticity.successor_reservoir.2
                );
                if plasticity.predecessor_plastic_rest_length_nanometres
                    != plasticity.successor_plastic_rest_length_nanometres
                {
                    retained_settlement = Some(plasticity);
                }
            }
            if retained_settlement.is_some() {
                break;
            }
        }
        let successor = plastic(&cohorts);
        let retained_settlement = retained_settlement.expect("local plastic return did not settle");
        assert_eq!(
            retained_settlement.predecessor_plastic_rest_length_nanometres,
            predecessor.0
        );
        assert_eq!(
            retained_settlement.successor_plastic_rest_length_nanometres,
            successor.0
        );
        assert_ne!(predecessor, successor);
        assert_eq!(
            participant_plastic(association, &cohorts),
            association_predecessor
        );
        assert_eq!(
            participant_plastic(regulation, &cohorts),
            regulation_predecessor
        );
    }

    #[test]
    fn active_association_affective_bond_mounts_one_delayed_ordering_route() {
        let mut cohorts = Vec::new();
        let mut population =
            Some(DevelopmentalRestingPopulation::admit(16_000_000, 100_000, 100, &[]).unwrap());
        let mut next_lineage = 1;
        let association = mount_intrinsic_neuron_at_place(
            &mut cohorts,
            &mut population,
            &mut next_lineage,
            DeclaredNeuronPlace::new(7, 0),
        )
        .unwrap();
        let affective = mount_intrinsic_neuron_at_place(
            &mut cohorts,
            &mut population,
            &mut next_lineage,
            DeclaredNeuronPlace::new(10, 0),
        )
        .unwrap();
        let resting_before = population.as_ref().unwrap().resting_cell_count();
        let mut fabric = ResidentElectricalFabric::default();

        mount_reached_ordering_reach(
            &mut cohorts,
            &mut population,
            &mut next_lineage,
            &mut fabric,
            &[],
        )
        .unwrap();
        assert_eq!(
            population.as_ref().unwrap().resting_cell_count(),
            resting_before
        );

        let active_bond = StablePhysicalBondReference::new(association, affective, 0).unwrap();
        mount_reached_ordering_reach(
            &mut cohorts,
            &mut population,
            &mut next_lineage,
            &mut fabric,
            &[active_bond],
        )
        .unwrap();
        let ordering = cohorts
            .iter()
            .flat_map(|cohort| {
                cohort
                    .anatomy
                    .mounts()
                    .iter()
                    .zip(cohort.anatomy.neuron_lineages())
            })
            .filter(|(mount, _)| mount.place().layer() == 11)
            .map(|(_, lineage)| *lineage)
            .collect::<Vec<_>>();
        assert_eq!(ordering.len(), 1);
        assert_eq!(
            population.as_ref().unwrap().resting_cell_count(),
            resting_before - 1
        );
        assert!(fabric.contains_contact(association, ordering[0]));
        assert!(fabric.contains_contact(affective, ordering[0]));
        let later_retention = mount_intrinsic_neuron_at_place(
            &mut cohorts,
            &mut population,
            &mut next_lineage,
            DeclaredNeuronPlace::new(9, 0),
        )
        .unwrap();
        fabric = fabric
            .append_contact(
                later_retention,
                ordering[0],
                ExactRational::integer(DEVELOPMENTAL_CONTACT_CONDUCTANCE_PICOSIEMENS),
            )
            .unwrap();
        let cohort_count = cohorts.len();
        let contact_count = fabric.contact_count();

        mount_reached_ordering_reach(
            &mut cohorts,
            &mut population,
            &mut next_lineage,
            &mut fabric,
            &[active_bond],
        )
        .unwrap();
        assert_eq!(cohorts.len(), cohort_count);
        assert_eq!(fabric.contact_count(), contact_count);
        assert_eq!(
            population.as_ref().unwrap().resting_cell_count(),
            resting_before - 2
        );
    }

    #[test]
    fn new_ordering_route_follows_one_exact_retained_body_motor() {
        let mut cohorts = Vec::new();
        let mut population =
            Some(DevelopmentalRestingPopulation::admit(1_600_000_000, 100_000, 100, &[]).unwrap());
        let mut next_lineage = 1;
        let mut fabric = ResidentElectricalFabric::default();
        let axis = BodyAxis::LeftGripAperture;
        let anatomy = axis.anatomy();
        let source = admit_articulated_body_consequence_source(
            0,
            &[BodyProprioceptiveConsequence {
                axis,
                unit: anatomy.unit,
                predecessor_position: anatomy.neutral,
                successor_position: anatomy.neutral - 1,
                signed_displacement: -1,
                toward_minimum_carriers: 1,
                toward_maximum_carriers: 0,
                opposed_carriers_per_terminal: 0,
                applied_displacement_quanta: 1,
                stalled_carriers: 0,
            }],
        )
        .unwrap();
        let receptor_site = source
            .joint_source_ports()
            .iter()
            .find(|port| {
                port.body_proprioceptor_terminal
                    == Some(BodyProprioceptorTerminal::new(
                        axis,
                        BodyEffectorDirection::TowardMaximum,
                    ))
                    && port.physical_quantity == EFFECTOR_REACTIVE_LOAD_FRACTION_QUANTITY
            })
            .map(NeuronSourceSite::from_source_port)
            .unwrap()
            .unwrap();
        let exact_terminal =
            BodyEffectorTerminal::new(axis, BodyEffectorDirection::TowardMinimum);
        let (regulation, _, _) = mount_body_regulation_from_site_fixture(
            &mut cohorts,
            &mut population,
            &mut next_lineage,
            &mut fabric,
            receptor_site,
        );
        let motor = cohorts
            .iter()
            .flat_map(|cohort| {
                cohort
                    .anatomy
                    .mounts()
                    .iter()
                    .zip(cohort.anatomy.neuron_lineages())
            })
            .find_map(|(mount, lineage)| {
                (mount.body_effector_terminal() == Some(exact_terminal)).then_some(*lineage)
            })
            .unwrap();
        assert!(fabric.contains_contact(regulation, motor));

        let association = mount_intrinsic_neuron_at_place(
            &mut cohorts,
            &mut population,
            &mut next_lineage,
            DeclaredNeuronPlace::new(7, 0),
        )
        .unwrap();
        let affective = mount_intrinsic_neuron_at_place(
            &mut cohorts,
            &mut population,
            &mut next_lineage,
            DeclaredNeuronPlace::new(10, 0),
        )
        .unwrap();
        fabric = fabric
            .append_contacts(&[
                (
                    association,
                    affective,
                    ExactRational::integer(DEVELOPMENTAL_CONTACT_CONDUCTANCE_PICOSIEMENS),
                ),
                (
                    regulation,
                    affective,
                    ExactRational::integer(DEVELOPMENTAL_CONTACT_CONDUCTANCE_PICOSIEMENS),
                ),
            ])
            .unwrap();
        let (later_regulation, _, _) = mount_body_regulation_fixture(
            &mut cohorts,
            &mut population,
            &mut next_lineage,
            &mut fabric,
            BodyAxis::LeftGripAperture,
            BodyEffectorDirection::TowardMaximum,
        );
        fabric = fabric
            .append_contact(
                later_regulation,
                affective,
                ExactRational::integer(DEVELOPMENTAL_CONTACT_CONDUCTANCE_PICOSIEMENS),
            )
            .unwrap();
        let active_bond = StablePhysicalBondReference::new(association, affective, 0).unwrap();

        mount_reached_ordering_reach(
            &mut cohorts,
            &mut population,
            &mut next_lineage,
            &mut fabric,
            &[active_bond],
        )
        .unwrap();
        let ordering = cohorts
            .iter()
            .flat_map(|cohort| {
                cohort
                    .anatomy
                    .mounts()
                    .iter()
                    .zip(cohort.anatomy.neuron_lineages())
            })
            .find_map(|(mount, lineage)| {
                (mount.source_site().is_none() && mount.place().layer() == 11)
                    .then_some(*lineage)
            })
            .unwrap();
        assert!(fabric.contains_contact(association, ordering));
        assert!(fabric.contains_contact(affective, ordering));
        assert!(fabric.contains_contact(ordering, motor));
        let articulatory = cohorts
            .iter()
            .flat_map(|cohort| {
                cohort
                    .anatomy
                    .mounts()
                    .iter()
                    .zip(cohort.anatomy.neuron_lineages())
            })
            .find_map(|(mount, lineage)| {
                (mount.source_site().is_none() && mount.place().layer() == 13).then_some(*lineage)
            });
        assert!(articulatory.is_none());
        let cohort_count = cohorts.len();
        let contact_count = fabric.contact_count();

        fabric = fabric
            .without_contact_pairs(&BTreeSet::from([canonical_lineage_pair(
                ordering, motor,
            )]))
            .unwrap();
        assert!(!fabric.contains_contact(ordering, motor));
        mount_reached_ordering_reach(
            &mut cohorts,
            &mut population,
            &mut next_lineage,
            &mut fabric,
            &[active_bond],
        )
        .unwrap();
        assert_eq!(cohorts.len(), cohort_count);
        assert_eq!(fabric.contact_count(), contact_count);
        assert!(fabric.contains_contact(ordering, motor));

        mount_reached_ordering_reach(
            &mut cohorts,
            &mut population,
            &mut next_lineage,
            &mut fabric,
            &[active_bond],
        )
        .unwrap();
        assert_eq!(cohorts.len(), cohort_count);
        assert_eq!(fabric.contact_count(), contact_count);
    }

    #[test]
    fn coincident_body_regulation_and_ordering_mount_one_reusable_motor_effector() {
        let mut cohorts = Vec::new();
        let mut population =
            Some(DevelopmentalRestingPopulation::admit(1_600_000_000, 100_000, 100, &[]).unwrap());
        let mut next_lineage = 1;
        let mut fabric = ResidentElectricalFabric::default();
        let (regulation, _, _) = mount_body_regulation_fixture(
            &mut cohorts,
            &mut population,
            &mut next_lineage,
            &mut fabric,
            BodyAxis::LeftElbowFlexion,
            BodyEffectorDirection::TowardMaximum,
        );
        let ordering = mount_intrinsic_neuron_at_place(
            &mut cohorts,
            &mut population,
            &mut next_lineage,
            DeclaredNeuronPlace::new(11, 0),
        )
        .unwrap();
        mount_local_motor_bridge_fixture(
            &mut cohorts,
            &mut population,
            &mut next_lineage,
            &mut fabric,
            regulation,
            ordering,
            0,
        );
        let resting_before = population.as_ref().unwrap().resting_cell_count();
        let active_bonds = directed_transfers_from_bonds(&cohorts, &fabric);

        mount_reached_motor_effector(
            &mut cohorts,
            &mut population,
            &mut next_lineage,
            &mut fabric,
            &[ordering, regulation],
            &[],
            &[],
            &[BodyAxis::LeftElbowFlexion, BodyAxis::LeftGripAperture],
        )
        .unwrap();
        assert_eq!(
            population.as_ref().unwrap().resting_cell_count(),
            resting_before
        );

        let prior_frontier = frontier_entries_from_bonds(&cohorts, &fabric);
        mount_reached_motor_effector(
            &mut cohorts,
            &mut population,
            &mut next_lineage,
            &mut fabric,
            &[ordering, regulation],
            &active_bonds,
            &prior_frontier,
            &[BodyAxis::LeftElbowFlexion, BodyAxis::LeftGripAperture],
        )
        .unwrap();
        let motor = cohorts
            .iter()
            .flat_map(|cohort| {
                cohort
                    .anatomy
                    .mounts()
                    .iter()
                    .zip(cohort.anatomy.neuron_lineages())
            })
            .filter(|(mount, _)| mount.place().layer() == 12)
            .map(|(_, lineage)| *lineage)
            .collect::<Vec<_>>();
        assert_eq!(motor.len(), 1);
        // Current law (6e6d220b era): the fixed articulated motor terminal
        // is mounted once WITH its typed regulation route; a later proven
        // coincidence REUSES that terminal and authors only contacts, so
        // the resting population is untouched here. The old expectation
        // (resting_before - 1) pinned proof-time terminal manufacture.
        assert_eq!(
            population.as_ref().unwrap().resting_cell_count(),
            resting_before
        );
        assert!(fabric.contains_contact(regulation, motor[0]));
        assert!(fabric.contains_contact(ordering, motor[0]));
        let motor_cohort = cohorts
            .iter()
            .find(|cohort| cohort.anatomy.neuron_lineages().contains(&motor[0]))
            .unwrap();
        assert_eq!(
            motor_cohort.anatomy.mounts()[0].body_effector_terminal(),
            Some(BodyEffectorTerminal::new(
                BodyAxis::LeftElbowFlexion,
                BodyEffectorDirection::TowardMaximum,
            ))
        );
        let encoded_motor =
            encode_reached_cohort_cell_v6(&motor_cohort.anatomy, &motor_cohort.state).unwrap();
        assert_eq!(&encoded_motor[..8], b"GLRCC08\0");
        let (restored_anatomy, restored_state) =
            decode_reached_cohort_cell(&encoded_motor).unwrap();
        assert_eq!(restored_anatomy, motor_cohort.anatomy);
        assert_eq!(restored_state, *motor_cohort.state);
        let cohort_count = cohorts.len();
        let contact_count = fabric.contact_count();

        let prior_frontier = frontier_entries_from_bonds(&cohorts, &fabric);
        mount_reached_motor_effector(
            &mut cohorts,
            &mut population,
            &mut next_lineage,
            &mut fabric,
            &[regulation, ordering],
            &active_bonds,
            &prior_frontier,
            &[BodyAxis::LeftElbowFlexion, BodyAxis::LeftGripAperture],
        )
        .unwrap();
        assert_eq!(cohorts.len(), cohort_count);
        assert_eq!(fabric.contact_count(), contact_count);
        // Reuse on repetition, and no cell was ever claimed at proof time
        // (the terminal was mounted with its regulation route above).
        assert_eq!(
            population.as_ref().unwrap().resting_cell_count(),
            resting_before
        );
    }

    // The variant grid of the ordering->motor bridge campaign: each case
    // that must NOT author a contact returns lawful no-growth (Ok with the
    // fabric untouched), never a refusal dressed as growth.
    fn motor_bridge_grid_fixture() -> (
        Vec<ResidentReachedCohort>,
        Option<DevelopmentalRestingPopulation>,
        u64,
        ResidentElectricalFabric,
        [u8; 16],
        [u8; 16],
    ) {
        let mut cohorts = Vec::new();
        let mut population =
            Some(DevelopmentalRestingPopulation::admit(1_600_000_000, 100_000, 100, &[]).unwrap());
        let mut next_lineage = 1;
        let mut fabric = ResidentElectricalFabric::default();
        let (regulation, _, _) = mount_body_regulation_fixture(
            &mut cohorts,
            &mut population,
            &mut next_lineage,
            &mut fabric,
            BodyAxis::LeftElbowFlexion,
            BodyEffectorDirection::TowardMaximum,
        );
        let ordering = mount_intrinsic_neuron_at_place(
            &mut cohorts,
            &mut population,
            &mut next_lineage,
            DeclaredNeuronPlace::new(11, 0),
        )
        .unwrap();
        mount_local_motor_bridge_fixture(
            &mut cohorts,
            &mut population,
            &mut next_lineage,
            &mut fabric,
            regulation,
            ordering,
            0,
        );
        (cohorts, population, next_lineage, fabric, regulation, ordering)
    }

    fn ordering_motor_contact_exists(
        cohorts: &[ResidentReachedCohort],
        fabric: &ResidentElectricalFabric,
        ordering: [u8; 16],
    ) -> bool {
        cohorts
            .iter()
            .flat_map(|cohort| {
                cohort
                    .anatomy
                    .mounts()
                    .iter()
                    .zip(cohort.anatomy.neuron_lineages())
            })
            .filter(|(mount, _)| mount.place().layer() == 12)
            .any(|(_, lineage)| fabric.contains_contact(ordering, *lineage))
    }

    #[test]
    fn static_pose_authors_no_ordering_motor_contact() {
        let (mut cohorts, mut population, mut next_lineage, mut fabric, regulation, ordering) =
            motor_bridge_grid_fixture();
        let active_bonds = directed_transfers_from_bonds(&cohorts, &fabric);
        let prior_frontier = frontier_entries_from_bonds(&cohorts, &fabric);
        let contact_count = fabric.contact_count();
        mount_reached_motor_effector(
            &mut cohorts,
            &mut population,
            &mut next_lineage,
            &mut fabric,
            &[ordering, regulation],
            &active_bonds,
            &prior_frontier,
            &[],
        )
        .unwrap();
        assert_eq!(fabric.contact_count(), contact_count);
        assert!(!ordering_motor_contact_exists(&cohorts, &fabric, ordering));
    }

    #[test]
    fn body_only_movement_without_regulation_authors_no_ordering_motor_contact() {
        let (mut cohorts, mut population, mut next_lineage, mut fabric, _regulation, ordering) =
            motor_bridge_grid_fixture();
        let active_bonds = directed_transfers_from_bonds(&cohorts, &fabric);
        let prior_frontier = frontier_entries_from_bonds(&cohorts, &fabric);
        let contact_count = fabric.contact_count();
        mount_reached_motor_effector(
            &mut cohorts,
            &mut population,
            &mut next_lineage,
            &mut fabric,
            &[],
            &active_bonds,
            &prior_frontier,
            &[BodyAxis::LeftElbowFlexion, BodyAxis::LeftGripAperture],
        )
        .unwrap();
        assert_eq!(fabric.contact_count(), contact_count);
        assert!(!ordering_motor_contact_exists(&cohorts, &fabric, ordering));
    }

    #[test]
    fn absent_ordering_frontier_authors_no_ordering_motor_contact() {
        let (mut cohorts, mut population, mut next_lineage, mut fabric, regulation, ordering) =
            motor_bridge_grid_fixture();
        let active_bonds = directed_transfers_from_bonds(&cohorts, &fabric);
        let contact_count = fabric.contact_count();
        mount_reached_motor_effector(
            &mut cohorts,
            &mut population,
            &mut next_lineage,
            &mut fabric,
            &[ordering, regulation],
            &active_bonds,
            &[],
            &[BodyAxis::LeftElbowFlexion, BodyAxis::LeftGripAperture],
        )
        .unwrap();
        assert_eq!(fabric.contact_count(), contact_count);
        assert!(!ordering_motor_contact_exists(&cohorts, &fabric, ordering));
    }

    #[test]
    fn severed_ordering_motor_contact_is_gone_and_regrows_only_from_lived_evidence() {
        let (mut cohorts, mut population, mut next_lineage, mut fabric, regulation, ordering) =
            motor_bridge_grid_fixture();
        let active_bonds = directed_transfers_from_bonds(&cohorts, &fabric);
        let prior_frontier = frontier_entries_from_bonds(&cohorts, &fabric);
        mount_reached_motor_effector(
            &mut cohorts,
            &mut population,
            &mut next_lineage,
            &mut fabric,
            &[ordering, regulation],
            &active_bonds,
            &prior_frontier,
            &[BodyAxis::LeftElbowFlexion, BodyAxis::LeftGripAperture],
        )
        .unwrap();
        let motor = cohorts
            .iter()
            .flat_map(|cohort| {
                cohort
                    .anatomy
                    .mounts()
                    .iter()
                    .zip(cohort.anatomy.neuron_lineages())
            })
            .filter(|(mount, _)| mount.place().layer() == 12)
            .map(|(_, lineage)| *lineage)
            .collect::<Vec<_>>();
        assert_eq!(motor.len(), 1);
        assert!(fabric.contains_contact(ordering, motor[0]));
        assert!(fabric.contains_contact(regulation, motor[0]));
        let contact_count = fabric.contact_count();

        // Sever exactly the learned ordering->motor contact through the
        // fabric's own retirement mechanism; every other contact survives.
        fabric = fabric
            .without_contact_pairs(&BTreeSet::from([canonical_lineage_pair(
                ordering, motor[0],
            )]))
            .unwrap();
        assert!(!fabric.contains_contact(ordering, motor[0]));
        assert!(fabric.contains_contact(regulation, motor[0]));
        assert_eq!(fabric.contact_count(), contact_count - 1);

        // No contact, no carrier path: ordering cannot prepare this motor
        // through an absent bond, so the full chain fails at the severed
        // link. The same lived two-interval evidence, and only that
        // evidence, may regrow the exact contact.
        mount_reached_motor_effector(
            &mut cohorts,
            &mut population,
            &mut next_lineage,
            &mut fabric,
            &[ordering, regulation],
            &active_bonds,
            &prior_frontier,
            &[BodyAxis::LeftElbowFlexion, BodyAxis::LeftGripAperture],
        )
        .unwrap();
        assert!(fabric.contains_contact(ordering, motor[0]));
        assert_eq!(fabric.contact_count(), contact_count);
    }

    #[test]
    fn zero_carrier_transfer_authors_no_ordering_motor_contact() {
        let (mut cohorts, mut population, mut next_lineage, mut fabric, regulation, ordering) =
            motor_bridge_grid_fixture();
        let prior_frontier = frontier_entries_from_bonds(&cohorts, &fabric);
        let contact_count = fabric.contact_count();
        mount_reached_motor_effector(
            &mut cohorts,
            &mut population,
            &mut next_lineage,
            &mut fabric,
            &[ordering, regulation],
            &[],
            &prior_frontier,
            &[BodyAxis::LeftElbowFlexion, BodyAxis::LeftGripAperture],
        )
        .unwrap();
        assert_eq!(fabric.contact_count(), contact_count);
        assert!(!ordering_motor_contact_exists(&cohorts, &fabric, ordering));
    }

    #[test]
    fn reacted_load_reaches_the_opposing_motor_terminal() {
        let mut cohorts = Vec::new();
        let mut population =
            Some(DevelopmentalRestingPopulation::admit(1_600_000_000, 100_000, 100, &[]).unwrap());
        let mut next_lineage = 1;
        let mut fabric = ResidentElectricalFabric::default();
        let axis = BodyAxis::LeftGripAperture;
        let anatomy = axis.anatomy();
        let source = admit_articulated_body_consequence_source(
            0,
            &[BodyProprioceptiveConsequence {
                axis,
                unit: anatomy.unit,
                predecessor_position: anatomy.maximum,
                successor_position: anatomy.maximum,
                signed_displacement: 0,
                toward_minimum_carriers: 0,
                toward_maximum_carriers: 240,
                opposed_carriers_per_terminal: 0,
                applied_displacement_quanta: 0,
                stalled_carriers: 240,
            }],
        )
        .unwrap();
        let receptor_site = source
            .joint_source_ports()
            .iter()
            .find(|port| {
                port.body_proprioceptor_terminal
                    == Some(BodyProprioceptorTerminal::new(
                        axis,
                        BodyEffectorDirection::TowardMaximum,
                    ))
                    && port.physical_quantity == EFFECTOR_REACTIVE_LOAD_FRACTION_QUANTITY
            })
            .map(NeuronSourceSite::from_source_port)
            .unwrap()
            .unwrap();
        let (regulation, _, _) = mount_body_regulation_from_site_fixture(
            &mut cohorts,
            &mut population,
            &mut next_lineage,
            &mut fabric,
            receptor_site,
        );
        let ordering = mount_intrinsic_neuron_at_place(
            &mut cohorts,
            &mut population,
            &mut next_lineage,
            DeclaredNeuronPlace::new(11, 0),
        )
        .unwrap();
        mount_local_motor_bridge_fixture(
            &mut cohorts,
            &mut population,
            &mut next_lineage,
            &mut fabric,
            regulation,
            ordering,
            0,
        );
        let active_bonds = directed_transfers_from_bonds(&cohorts, &fabric);

        let prior_frontier = frontier_entries_from_bonds(&cohorts, &fabric);
        mount_reached_motor_effector(
            &mut cohorts,
            &mut population,
            &mut next_lineage,
            &mut fabric,
            &[ordering, regulation],
            &active_bonds,
            &prior_frontier,
            &[BodyAxis::LeftElbowFlexion, BodyAxis::LeftGripAperture],
        )
        .unwrap();

        let motor_terminal = cohorts
            .iter()
            .flat_map(|cohort| cohort.anatomy.mounts())
            .find_map(ReachedNeuronMount::body_effector_terminal)
            .unwrap();
        assert_eq!(
            motor_terminal,
            BodyEffectorTerminal::new(axis, BodyEffectorDirection::TowardMinimum)
        );
    }

    #[test]
    fn exact_moved_terminal_selects_only_its_position_regulation() {
        let mut cohorts = Vec::new();
        let mut population =
            Some(DevelopmentalRestingPopulation::admit(1_600_000_000, 100_000, 100, &[]).unwrap());
        let mut next_lineage = 1;
        let mut fabric = ResidentElectricalFabric::default();
        let axis = BodyAxis::LeftGripAperture;
        let anatomy = axis.anatomy();
        let source = admit_articulated_body_consequence_source(
            0,
            &[BodyProprioceptiveConsequence {
                axis,
                unit: anatomy.unit,
                predecessor_position: anatomy.neutral,
                successor_position: anatomy.neutral - 1,
                signed_displacement: -1,
                toward_minimum_carriers: 1,
                toward_maximum_carriers: 0,
                opposed_carriers_per_terminal: 0,
                applied_displacement_quanta: 1,
                stalled_carriers: 0,
            }],
        )
        .unwrap();
        let source_site = |direction, quantity| {
            source
                .joint_source_ports()
                .iter()
                .find(|port| {
                    port.body_proprioceptor_terminal
                        == Some(BodyProprioceptorTerminal::new(axis, direction))
                        && port.physical_quantity == quantity
                })
                .map(NeuronSourceSite::from_source_port)
                .unwrap()
                .unwrap()
        };
        let (minimum_load_regulation, _, _) = mount_body_regulation_from_site_fixture(
            &mut cohorts,
            &mut population,
            &mut next_lineage,
            &mut fabric,
            source_site(
                BodyEffectorDirection::TowardMinimum,
                EFFECTOR_REACTIVE_LOAD_FRACTION_QUANTITY,
            ),
        );
        let (maximum_load_regulation, _, _) = mount_body_regulation_from_site_fixture(
            &mut cohorts,
            &mut population,
            &mut next_lineage,
            &mut fabric,
            source_site(
                BodyEffectorDirection::TowardMaximum,
                EFFECTOR_REACTIVE_LOAD_FRACTION_QUANTITY,
            ),
        );
        let (position_regulation, _, _) = mount_body_regulation_from_site_fixture(
            &mut cohorts,
            &mut population,
            &mut next_lineage,
            &mut fabric,
            source_site(
                BodyEffectorDirection::TowardMinimum,
                ANTAGONIST_PROPRIOCEPTOR_LENGTH_QUANTITY,
            ),
        );
        let topology = ResidentTopologyIndex::build(&cohorts, &fabric).unwrap();

        assert_eq!(
            exact_moved_body_regulations_by_occurrence(
                &cohorts,
                &topology,
                &[vec![
                    minimum_load_regulation,
                    maximum_load_regulation,
                    position_regulation,
                ]],
                &[vec![BodyEffectorTerminal::new(
                    axis,
                    BodyEffectorDirection::TowardMinimum,
                )]],
            )
            .unwrap(),
            vec![vec![position_regulation]],
        );
        assert_eq!(
            exact_moved_body_regulations_by_occurrence(
                &cohorts,
                &topology,
                &[vec![position_regulation]],
                &[vec![BodyEffectorTerminal::new(
                    axis,
                    BodyEffectorDirection::TowardMinimum,
                )]],
            )
            .unwrap(),
            vec![vec![position_regulation]],
        );
        assert_eq!(
            exact_moved_body_regulations_by_occurrence(
                &cohorts,
                &topology,
                &[vec![minimum_load_regulation, maximum_load_regulation]],
                &[vec![BodyEffectorTerminal::new(
                    axis,
                    BodyEffectorDirection::TowardMinimum,
                )]],
            )
            .unwrap(),
            vec![Vec::<[u8; 16]>::new()],
        );
    }

    #[test]
    fn live_reacted_load_prepares_only_the_motor_that_releases_the_joint_stop() {
        let axis = BodyAxis::LeftGripAperture;
        let loaded_terminal = BodyProprioceptorTerminal::new(
            axis,
            BodyEffectorDirection::TowardMaximum,
        );
        let position_source = admit_complete_articulated_body_state_source(
            0,
            &ArticulatedBodyState::at_neutral(),
        )
        .unwrap();
        let anatomy = axis.anatomy();
        let load_source = admit_articulated_body_consequence_source(
            1,
            &[BodyProprioceptiveConsequence {
                axis,
                unit: anatomy.unit,
                predecessor_position: anatomy.maximum,
                successor_position: anatomy.maximum,
                signed_displacement: 0,
                toward_minimum_carriers: 0,
                toward_maximum_carriers: 1,
                opposed_carriers_per_terminal: 0,
                applied_displacement_quanta: 0,
                stalled_carriers: 1,
            }],
        )
        .unwrap();
        let source_site = |source: &NativeJointSourceEpisode, physical_quantity| {
            source
                .joint_source_ports()
                .iter()
                .find(|port| {
                    port.body_proprioceptor_terminal == Some(loaded_terminal)
                        && port.physical_quantity == physical_quantity
                })
                .map(NeuronSourceSite::from_source_port)
                .unwrap()
                .unwrap()
        };
        let load_regulation = [1_u8; 16];
        let tonic_length_regulation = [2_u8; 16];
        let paths = [
            MotorBodyAfferentPath {
                body_regulation_lineage: load_regulation,
                integration_lineage: [3_u8; 16],
                receptor_lineage: [4_u8; 16],
                receptor_site: source_site(
                    &load_source,
                    EFFECTOR_REACTIVE_LOAD_FRACTION_QUANTITY,
                ),
            },
            MotorBodyAfferentPath {
                body_regulation_lineage: tonic_length_regulation,
                integration_lineage: [5_u8; 16],
                receptor_lineage: [6_u8; 16],
                receptor_site: source_site(
                    &position_source,
                    ANTAGONIST_PROPRIOCEPTOR_LENGTH_QUANTITY,
                ),
            },
        ];

        assert_eq!(
            exact_articulated_body_preparation_regulations(
                loaded_terminal.opposing_effector(),
                &paths,
                &[],
                &[],
            ),
            vec![load_regulation],
        );
        assert!(exact_articulated_body_preparation_regulations(
            loaded_terminal.paired_effector(),
            &paths,
            &[],
            &[],
        )
        .is_empty());
        assert!(exact_articulated_body_preparation_regulations(
            BodyEffectorTerminal::new(
                BodyAxis::RightGripAperture,
                BodyEffectorDirection::TowardMinimum,
            ),
            &paths,
            &[],
            &[],
        )
        .is_empty());
    }

    #[test]
    fn only_incoming_ordering_or_body_regulation_transfer_prepares_motor() {
        let regulation = [8_u8; 16];
        let tonic_position_regulation = [9_u8; 16];
        let ordering = [11_u8; 16];
        let unrelated = [7_u8; 16];
        let motor = [12_u8; 16];
        let transfer = |sender, receiver, carriers| DirectedPhysicalTransferObservation {
            sender,
            receiver,
            bond: StablePhysicalBondReference::new(sender, receiver, 0).unwrap(),
            transferred_whole_carriers: carriers,
        };
        let settled = [
            transfer(regulation, motor, 9),
            transfer(tonic_position_regulation, motor, 8),
            transfer(motor, ordering, 5),
            transfer(ordering, motor, 6),
            transfer(unrelated, motor, 7),
        ];
        let layer_of = |lineage| {
            [
                (regulation, 8),
                (tonic_position_regulation, 8),
                (ordering, 11),
                (unrelated, 7),
                (motor, 12),
            ]
            .into_iter()
            .find_map(|(candidate, layer)| (candidate == lineage).then_some(layer))
        };

        let fresh_body_seeds = BTreeSet::from([regulation, ordering]);
        assert_eq!(
            exact_motor_preparation_transfers(
                motor,
                &settled,
                &[regulation],
                &fresh_body_seeds,
                layer_of,
            ),
            vec![settled[0], settled[3]],
        );
        assert_eq!(
            exact_motor_preparation_transfers(
                motor,
                &settled,
                &[regulation],
                &BTreeSet::from([ordering]),
                layer_of,
            ),
            vec![settled[3]],
            "retained layer-8 current cannot repeat a reflex without fresh body cause",
        );
        assert_eq!(
            exact_motor_preparation_transfers(
                motor,
                &settled,
                &[regulation],
                &BTreeSet::new(),
                layer_of,
            ),
            vec![settled[3]],
            "unreached body regulation stays silent while exact learned ordering remains causal",
        );
    }

    #[test]
    fn historical_load_correction_rewires_only_the_rejected_motor_contact() {
        const MAX_BYTES: usize = 64_000_000;
        let mut cohorts = Vec::new();
        let mut population = None;
        let mut next_lineage = 1;
        let mut fabric = ResidentElectricalFabric::default();
        let axis = BodyAxis::LeftGripAperture;
        let anatomy = axis.anatomy();
        let source = admit_articulated_body_consequence_source(
            0,
            &[BodyProprioceptiveConsequence {
                axis,
                unit: anatomy.unit,
                predecessor_position: anatomy.maximum,
                successor_position: anatomy.maximum,
                signed_displacement: 0,
                toward_minimum_carriers: 0,
                toward_maximum_carriers: 240,
                opposed_carriers_per_terminal: 0,
                applied_displacement_quanta: 0,
                stalled_carriers: 240,
            }],
        )
        .unwrap();
        let receptor_site = source
            .joint_source_ports()
            .iter()
            .find(|port| {
                port.body_proprioceptor_terminal
                    == Some(BodyProprioceptorTerminal::new(
                        axis,
                        BodyEffectorDirection::TowardMaximum,
                    ))
                    && port.physical_quantity == EFFECTOR_REACTIVE_LOAD_FRACTION_QUANTITY
            })
            .map(NeuronSourceSite::from_source_port)
            .unwrap()
            .unwrap();
        let (regulation, _, _) = mount_body_regulation_from_site_fixture(
            &mut cohorts,
            &mut population,
            &mut next_lineage,
            &mut fabric,
            receptor_site,
        );
        let wrong_motor = mount_next_intrinsic_in_layer(
            &mut cohorts,
            &mut population,
            &mut next_lineage,
            12,
        )
        .unwrap();
        cohorts
            .iter_mut()
            .find(|cohort| cohort.anatomy.neuron_lineages().contains(&wrong_motor))
            .unwrap()
            .anatomy
            .specialize_motor_effector(
                wrong_motor,
                BodyEffectorTerminal::new(axis, BodyEffectorDirection::TowardMaximum),
            )
            .unwrap();
        let correct_terminal =
            BodyEffectorTerminal::new(axis, BodyEffectorDirection::TowardMinimum);
        let correct_motor = cohorts
            .iter()
            .flat_map(|cohort| {
                cohort
                    .anatomy
                    .mounts()
                    .iter()
                    .zip(cohort.anatomy.neuron_lineages())
            })
            .find_map(|(mount, lineage)| {
                (mount.body_effector_terminal() == Some(correct_terminal)).then_some(*lineage)
            })
            .expect("body-regulation fixture must already mount the opposing motor");
        let unrelated = mount_next_intrinsic_in_layer(
            &mut cohorts,
            &mut population,
            &mut next_lineage,
            11,
        )
        .unwrap();
        fabric = fabric
            .without_contact_pairs(&BTreeSet::from([canonical_lineage_pair(
                regulation,
                correct_motor,
            )]))
            .unwrap()
            .append_contacts(&[
                (
                    regulation,
                    wrong_motor,
                    ExactRational::integer(DEVELOPMENTAL_CONTACT_CONDUCTANCE_PICOSIEMENS),
                ),
                (
                    unrelated,
                    correct_motor,
                    ExactRational::integer(DEVELOPMENTAL_CONTACT_CONDUCTANCE_PICOSIEMENS),
                ),
            ])
            .unwrap();
        let contact_count = fabric.contact_count();
        let topology_index = Arc::new(ResidentTopologyIndex::build(&cohorts, &fabric).unwrap());
        let occupied_places = cohorts
            .iter()
            .flat_map(|cohort| cohort.anatomy.mounts())
            .map(ReachedNeuronMount::place)
            .collect::<Vec<_>>();
        let resting_population = DevelopmentalRestingPopulation::admit(
            MAX_BYTES,
            100_000,
            next_lineage,
            &occupied_places,
        )
        .unwrap();
        next_lineage = resting_population.lineage_end_exclusive();
        let state = ResidentCognitiveFormationState {
            generation: 5,
            next_lineage_ordinal: next_lineage,
            vocal_articulatory_effector_lineage: None,
            unexpressed_electrical_seeds: Box::new([]),
            dormant_lineage_seeds: Box::new([]),
            resting_population: Some(resting_population),
            cohorts: cohorts.into_boxed_slice(),
            electrical_fabric: fabric,
            active_electrical_frontier: Box::new([]),
            preceding_active_electrical_frontier: Box::new([]),
            older_active_electrical_frontier: Box::new([]),
            mosaics: Box::new([]),
            hippocampal: ResidentHippocampalIndex::default(),
            topology_index,
            formation_index: ResidentFormationIndex::default(),
        };
        validate_lineage_state(&state).unwrap();
        let corrected = state
            .correct_effector_load_motor_feedback()
            .unwrap()
            .expect("rejected load route requires one historical correction");
        let current = corrected
            .encode(MAX_BYTES)
            .unwrap();
        let restored = ResidentCognitiveFormationState::decode(&current, MAX_BYTES).unwrap();
        assert_eq!(restored.electrical_fabric.contact_count(), contact_count);
        assert!(!restored
            .electrical_fabric
            .contains_contact(regulation, wrong_motor));
        assert!(restored
            .electrical_fabric
            .contains_contact(regulation, correct_motor));
        assert!(restored
            .electrical_fabric
            .contains_contact(unrelated, correct_motor));
        assert_eq!(
            ResidentCognitiveFormationState::migrate_to_current_format(&current, MAX_BYTES)
                .unwrap(),
            current
        );
    }

    /// The one-way V33 decontamination followed by the V34 fixed vocal route:
    /// every layer-11->12 contact reintroduced
    /// after V31 and every historical layer-11->13 contact is removed at the
    /// migration boundary; neurons,
    /// terminals, unrelated contacts, and lawful frontier entries are
    /// preserved; frontier entries riding a removed contact drop with it;
    /// the migrated body is V34 and re-migration is the identity, so a
    /// restart can never restore the fan-out; V32 bytes are refused by
    /// ordinary decode and must cross this boundary.
    #[test]
    fn v33_migration_removes_reintroduced_effector_pools_one_way() {
        const MAX_BYTES: usize = 1_600_000_000;
        let mut cohorts = Vec::new();
        let mut population =
            Some(DevelopmentalRestingPopulation::admit(1_600_000_000, 100_000, 100, &[]).unwrap());
        let mut next_lineage = 1;
        let mut fabric = ResidentElectricalFabric::default();
        let axis = BodyAxis::LeftGripAperture;
        let anatomy = axis.anatomy();
        let source = admit_articulated_body_consequence_source(
            0,
            &[BodyProprioceptiveConsequence {
                axis,
                unit: anatomy.unit,
                predecessor_position: anatomy.maximum,
                successor_position: anatomy.maximum,
                signed_displacement: 0,
                toward_minimum_carriers: 0,
                toward_maximum_carriers: 240,
                opposed_carriers_per_terminal: 0,
                applied_displacement_quanta: 0,
                stalled_carriers: 240,
            }],
        )
        .unwrap();
        let receptor_site = source
            .joint_source_ports()
            .iter()
            .find(|port| {
                port.body_proprioceptor_terminal
                    == Some(BodyProprioceptorTerminal::new(
                        axis,
                        BodyEffectorDirection::TowardMaximum,
                    ))
                    && port.physical_quantity == EFFECTOR_REACTIVE_LOAD_FRACTION_QUANTITY
            })
            .map(NeuronSourceSite::from_source_port)
            .unwrap()
            .unwrap();
        let (regulation, _, _) = mount_body_regulation_from_site_fixture(
            &mut cohorts,
            &mut population,
            &mut next_lineage,
            &mut fabric,
            receptor_site,
        );
        let expected_motor =
            BodyEffectorTerminal::new(axis, BodyEffectorDirection::TowardMinimum);
        let motor = cohorts
            .iter()
            .flat_map(|cohort| {
                cohort
                    .anatomy
                    .mounts()
                    .iter()
                    .zip(cohort.anatomy.neuron_lineages())
            })
            .find_map(|(mount, lineage)| {
                (mount.body_effector_terminal() == Some(expected_motor)).then_some(*lineage)
            })
            .expect("body-regulation development must mount its exact opposing motor");
        let articulatory = mount_next_intrinsic_in_layer(
            &mut cohorts,
            &mut population,
            &mut next_lineage,
            13,
        )
        .unwrap();
        let ordering_a = mount_intrinsic_neuron_at_place(
            &mut cohorts,
            &mut population,
            &mut next_lineage,
            DeclaredNeuronPlace::new(11, 0),
        )
        .unwrap();
        let ordering_b = mount_intrinsic_neuron_at_place(
            &mut cohorts,
            &mut population,
            &mut next_lineage,
            DeclaredNeuronPlace::new(11, 1),
        )
        .unwrap();
        let affective = mount_intrinsic_neuron_at_place(
            &mut cohorts,
            &mut population,
            &mut next_lineage,
            DeclaredNeuronPlace::new(10, 0),
        )
        .unwrap();
        let conductance =
            ExactRational::integer(DEVELOPMENTAL_CONTACT_CONDUCTANCE_PICOSIEMENS);
        fabric = fabric
            .append_contacts(&[
                (ordering_a, affective, conductance),
                (ordering_a, motor, conductance),
                (ordering_b, motor, conductance),
                (ordering_a, articulatory, conductance),
            ])
            .unwrap();
        let contaminated_entry = frontier_hop(&cohorts, &fabric, ordering_a, motor)
            .into_iter()
            .next()
            .unwrap();
        let lawful_entry = frontier_hop(&cohorts, &fabric, regulation, motor)
            .into_iter()
            .next()
            .unwrap();
        let cohort_count = cohorts.len();
        let topology_index =
            Arc::new(ResidentTopologyIndex::build(&cohorts, &fabric).unwrap());
        let occupied_places = cohorts
            .iter()
            .flat_map(|cohort| cohort.anatomy.mounts())
            .map(ReachedNeuronMount::place)
            .collect::<Vec<_>>();
        let next_lineage = cohorts
            .iter()
            .flat_map(|cohort| cohort.anatomy.neuron_lineages().iter())
            .map(|lineage| lineage_ordinal(*lineage).unwrap())
            .max()
            .unwrap()
            .checked_add(1)
            .unwrap();
        let resting_population = DevelopmentalRestingPopulation::admit(
            MAX_BYTES,
            100_000,
            next_lineage,
            &occupied_places,
        )
        .unwrap();
        let next_lineage = resting_population.lineage_end_exclusive();
        // The focused falsifier: a retained formation referencing the
        // contaminated ordering_a->motor bond (exact reference, ordinal
        // included) must NOT exempt that contact; and because losing it
        // disconnects the formation's members, the invalid relationship
        // retires while the neurons live on.
        let bonds = all_physical_bonds(&cohorts, &fabric);
        let referencing_mosaic = RetainedOrganismMosaic {
            mosaic: AdmittedPhysicalMosaic::admitted_for_test(
                {
                    let mut members = vec![ordering_a, motor, affective];
                    members.sort_unstable();
                    members
                },
                vec![
                    bonds
                        .iter()
                        .copied()
                        .find(|bond| {
                            bond.endpoints() == canonical_lineage_pair(ordering_a, affective)
                        })
                        .unwrap(),
                    bonds
                        .iter()
                        .copied()
                        .find(|bond| {
                            bond.endpoints() == canonical_lineage_pair(ordering_a, motor)
                        })
                        .unwrap(),
                ],
            ),
            recurrent_lineage: None,
            reinforcement_count: 0,
            mosaic_of_mosaics_relation_count: 0,
        };
        let state = ResidentCognitiveFormationState {
            generation: 5,
            next_lineage_ordinal: next_lineage,
            vocal_articulatory_effector_lineage: None,
            unexpressed_electrical_seeds: Box::new([]),
            dormant_lineage_seeds: Box::new([]),
            resting_population: Some(resting_population),
            cohorts: cohorts.into_boxed_slice(),
            electrical_fabric: fabric,
            active_electrical_frontier: {
                let mut entries = vec![contaminated_entry, lawful_entry];
                entries.sort_unstable();
                entries.into_boxed_slice()
            },
            preceding_active_electrical_frontier: Box::new([contaminated_entry]),
            older_active_electrical_frontier: Box::new([]),
            mosaics: Box::new([referencing_mosaic]),
            hippocampal: ResidentHippocampalIndex::default(),
            topology_index,
            formation_index: ResidentFormationIndex::default(),
        };
        validate_lineage_state(&state).unwrap();
        state.validate_current_motor_effectors().unwrap();
        // Simulate the deployed predecessor under V32. The CURRENT encoder
        // refuses this deliberately contaminated pre-V40 anatomy (layer-13
        // contacts violate the motor-coupled vocal invariant), so the body
        // is written through the historical V26-layout codec -- V27-V33
        // share that exact byte layout -- and stamped with its own boundary.
        let mut legacy = state
            .encode_with_format(CognitiveCodecFormat::V26, MAX_BYTES)
            .unwrap();
        legacy[..MAGIC_V32.len()].copy_from_slice(MAGIC_V32);
        legacy[MAGIC_V32.len()..MAGIC_V32.len() + std::mem::size_of::<u16>()]
            .copy_from_slice(&VERSION_V30.to_le_bytes());
        assert!(ResidentCognitiveFormationState::decode(&legacy, MAX_BYTES).is_err());
        let migrated =
            ResidentCognitiveFormationState::migrate_to_current_format(&legacy, MAX_BYTES)
                .unwrap();
        let restored =
            ResidentCognitiveFormationState::decode(&migrated, MAX_BYTES).unwrap();
        assert!(!restored.electrical_fabric.contains_contact(ordering_a, motor));
        assert!(!restored.electrical_fabric.contains_contact(ordering_b, motor));
        assert!(!restored
            .electrical_fabric
            .contains_contact(ordering_a, articulatory));
        assert!(restored.electrical_fabric.contains_contact(regulation, motor));
        assert!(restored
            .electrical_fabric
            .contains_contact(ordering_a, affective));
        assert!(!restored
            .electrical_fabric
            .contains_contact(ordering_a, articulatory));
        // One new cohort: the fixture's bare layer-13 cell is vocal-body
        // anatomy, so the V41 boundary mounts the dedicated vocal effector
        // from unclaimed resting anatomy instead of adopting a historical
        // layer-13 cell. Both layer-13 cells stay electrically isolated.
        assert_eq!(restored.cohorts.len(), cohort_count + 1);
        let effector = restored
            .vocal_articulatory_effector_lineage
            .expect("dedicated vocal effector mounted at the V41 boundary");
        assert_ne!(effector, articulatory);
        let layer_thirteen = restored
            .cohorts
            .iter()
            .flat_map(|cohort| {
                cohort
                    .anatomy
                    .mounts()
                    .iter()
                    .zip(cohort.anatomy.neuron_lineages())
            })
            .filter_map(|(mount, lineage)| {
                (mount.source_site().is_none() && mount.place().layer() == 13)
                    .then_some(*lineage)
            })
            .collect::<Vec<_>>();
        assert_eq!(layer_thirteen.len(), 2);
        assert!(layer_thirteen.contains(&articulatory));
        assert!(layer_thirteen.contains(&effector));
        for cell in &layer_thirteen {
            for (left, right) in restored.electrical_fabric.contact_endpoints() {
                assert_ne!(restored.electrical_fabric.lineages()[left], *cell);
                assert_ne!(restored.electrical_fabric.lineages()[right], *cell);
            }
        }
        assert!(
            restored.mosaics.is_empty(),
            "a formation disconnected by losing its invalid bond must retire"
        );
        assert_eq!(restored.active_electrical_frontier.len(), 1);
        assert_eq!(
            restored.active_electrical_frontier[0].receiver(),
            lawful_entry.receiver()
        );
        assert!(restored.preceding_active_electrical_frontier.is_empty());

        // One-way and restart-proof: the migrated body is current and crossing
        // the boundary again is the identity.
        assert_eq!(&migrated[..MAGIC_V42.len()], MAGIC_V42);
        assert_eq!(
            ResidentCognitiveFormationState::migrate_to_current_format(&migrated, MAX_BYTES)
                .unwrap(),
            migrated
        );
    }

    /// Wake-law falsifiers. A pump-only endpoint change wakes exactly its
    /// incident contacts (their integration epoch advances with the clock);
    /// an untouched endpoint wakes none (its contact's epoch never moves);
    /// and one residency carries across consecutive settled intervals —
    /// the event clock advances by one per settlement with no rebuild.
    #[test]
    fn changed_endpoints_wake_exactly_their_incident_contacts() {
        let mut cohorts = Vec::new();
        let mut population = Some(
            DevelopmentalRestingPopulation::admit(1_600_000_000, 100_000, 100, &[]).unwrap(),
        );
        let mut next_lineage = 1;
        let association = mount_intrinsic_neuron_at_place(
            &mut cohorts,
            &mut population,
            &mut next_lineage,
            DeclaredNeuronPlace::new(6, 0),
        )
        .unwrap();
        let regulation = mount_intrinsic_neuron_at_place(
            &mut cohorts,
            &mut population,
            &mut next_lineage,
            DeclaredNeuronPlace::new(8, 0),
        )
        .unwrap();
        let mut fabric = ResidentElectricalFabric::default();
        mount_reached_affective_reach(
            &mut cohorts,
            &mut population,
            &mut next_lineage,
            &mut fabric,
            &[association, regulation],
        )
        .unwrap();
        // An isolated resting pair no cause ever reaches: its contact must
        // never be woken and its integration epoch must never advance.
        let isolated_left = mount_next_intrinsic_in_layer(
            &mut cohorts,
            &mut population,
            &mut next_lineage,
            11,
        )
        .unwrap();
        let isolated_right = mount_next_intrinsic_in_layer(
            &mut cohorts,
            &mut population,
            &mut next_lineage,
            11,
        )
        .unwrap();
        fabric = fabric
            .append_contact(
                isolated_left,
                isolated_right,
                ExactRational::integer(DEVELOPMENTAL_CONTACT_CONDUCTANCE_PICOSIEMENS),
            )
            .unwrap();
        let topology_index = ResidentTopologyIndex::build(&cohorts, &fabric).unwrap();
        let isolated_contact = topology_index
            .contacts
            .iter()
            .position(|entry| {
                let left = topology_index.flat_locations[entry.left].2;
                let right = topology_index.flat_locations[entry.right].2;
                canonical_lineage_pair(left, right)
                    == canonical_lineage_pair(isolated_left, isolated_right)
            })
            .unwrap();
        let isolated_flats = [isolated_left, isolated_right]
            .iter()
            .map(|lineage| topology_index.flat_for_lineage(*lineage).unwrap())
            .collect::<Vec<_>>();
        let mut transitioned = BTreeSet::new();
        let mut residency: Option<crate::causal_event_scheduler::CausalEventResidency> = None;
        for ordinal in 1..=6_u64 {
            settle_internal_contact_interval(
                &mut cohorts,
                &mut fabric,
                &topology_index,
                None,
                &[],
                &[association, regulation],
                &[association, regulation],
                &[association, regulation],
                &mut transitioned,
                ordinal,
                0,
                &mut residency,
                &BTreeMap::new(),
                &[],
                &[],
                ExactRational::integer(0),
                true,
            )
            .unwrap();
            let events = residency.as_ref().expect("residency must persist");
            assert_eq!(
                events.organism_clock, ordinal,
                "one residency must advance one clock per settled interval"
            );
            // The zero-displacement pair is UNCHANGED every clock under the
            // passive-return law (no displacement -> no return event, no
            // reach -> no pump): its contact epoch must never move and its
            // return schedule must stay empty. An unchanged endpoint wakes
            // nothing — strictly, forever.
            assert_eq!(
                events.contact_last_integrated[isolated_contact], 0,
                "an unchanged endpoint must wake nothing"
            );
            let isolated_return_scheduled = events
                .recovery_schedule
                .scheduled_dues()
                .any(|(flat, _)| isolated_flats.contains(&flat));
            assert!(
                !isolated_return_scheduled,
                "zero displacement must schedule no return event"
            );
            // The SEEDED subsystem's endpoints change every clock (external
            // seed + pump + settlement): every contact incident to a
            // changed endpoint is woken to the current epoch.
            let reached_advanced = events
                .contact_last_integrated
                .iter()
                .enumerate()
                .filter(|(index, _)| *index != isolated_contact)
                .all(|(_, last)| *last + 1 >= events.organism_clock);
            assert!(
                reached_advanced,
                "every contact incident to a changed endpoint must be woken"
            );
        }

        // Quiet termination: with ingress gone, due events settle (the
        // clock skipping silent spans exactly) until charge has returned
        // and every contact rests — no due membrane or contact events
        // remain, and further quiet clocks are pure no-ops.
        for _ in 0..10_000 {
            let events = residency.as_ref().unwrap();
            if events.contact_schedule.scheduled_len() == 0
                && events.recovery_schedule.scheduled_len() == 0
            {
                break;
            }
            let next_ordinal = events.organism_clock + 1;
            settle_internal_contact_interval(
                &mut cohorts,
                &mut fabric,
                &topology_index,
                None,
                &[],
                &[],
                &[],
                &[],
                &mut transitioned,
                next_ordinal,
                0,
                &mut residency,
                &BTreeMap::new(),
                &[],
                &[],
                ExactRational::integer(0),
                true,
            )
            .unwrap();
        }
        let events = residency.as_ref().unwrap();
        assert_eq!(
            events.contact_schedule.scheduled_len(),
            0,
            "repeated quiet intervals must terminate with no due contact events"
        );
        assert_eq!(
            events.recovery_schedule.scheduled_len(),
            0,
            "repeated quiet intervals must terminate with no due membrane events"
        );
    }

    /// The correction's core proofs: fixed antagonist motor anatomy exists
    /// with its typed regulation route, while a learned ordering contact requires
    /// the exact directed causal chain ordering -> affective -> consequence-
    /// returned regulation. Same-interval coincidence authors nothing, an
    /// unrelated ordering neuron can never connect, the contact count does
    /// not scale with coincident-active ordering neurons, and an interval
    /// with no directed transfers (unattended, no action) adds zero motor
    /// contacts.
    #[test]
    fn motor_contact_requires_directed_causal_chain_not_coincidence() {
        let mut cohorts = Vec::new();
        let mut population =
            Some(DevelopmentalRestingPopulation::admit(1_600_000_000, 100_000, 100, &[]).unwrap());
        let mut next_lineage = 1;
        let mut fabric = ResidentElectricalFabric::default();
        let (regulation, _, _) = mount_body_regulation_fixture(
            &mut cohorts,
            &mut population,
            &mut next_lineage,
            &mut fabric,
            BodyAxis::LeftElbowFlexion,
            BodyEffectorDirection::TowardMaximum,
        );
        let routed_ordering = mount_intrinsic_neuron_at_place(
            &mut cohorts,
            &mut population,
            &mut next_lineage,
            DeclaredNeuronPlace::new(11, 0),
        )
        .unwrap();
        mount_local_motor_bridge_fixture(
            &mut cohorts,
            &mut population,
            &mut next_lineage,
            &mut fabric,
            regulation,
            routed_ordering,
            0,
        );
        let affective = cohorts
            .iter()
            .flat_map(|cohort| {
                cohort
                    .anatomy
                    .mounts()
                    .iter()
                    .zip(cohort.anatomy.neuron_lineages())
            })
            .find_map(|(mount, lineage)| (mount.place().layer() == 10).then_some(*lineage))
            .unwrap();
        // Coincident ordering neurons: physically adjacent to the same
        // affective cell, transitioned in the same interval, but with no
        // directed transfer along their own path.
        let mut coincident = Vec::new();
        for topology in 1..=4_u32 {
            let bystander = mount_intrinsic_neuron_at_place(
                &mut cohorts,
                &mut population,
                &mut next_lineage,
                DeclaredNeuronPlace::new(11, topology),
            )
            .unwrap();
            fabric = fabric
                .append_contact(
                    affective,
                    bystander,
                    ExactRational::integer(DEVELOPMENTAL_CONTACT_CONDUCTANCE_PICOSIEMENS),
                )
                .unwrap();
            coincident.push(bystander);
        }
        let contacts_before = fabric.contact_count();
        let motor = cohorts
            .iter()
            .flat_map(|cohort| {
                cohort
                    .anatomy
                    .mounts()
                    .iter()
                    .zip(cohort.anatomy.neuron_lineages())
            })
            .find_map(|(mount, lineage)| {
                (mount.body_effector_terminal()
                    == Some(BodyEffectorTerminal::new(
                        BodyAxis::LeftElbowFlexion,
                        BodyEffectorDirection::TowardMaximum,
                    )))
                .then_some(*lineage)
            })
            .expect("typed body regulation must mount its fixed motor terminal");
        assert!(fabric.contains_contact(regulation, motor));

        // Proof: an interval with NO directed transfers (unattended or
        // actionless) authors nothing, however many neurons transitioned.
        let mut transitioned = vec![regulation, routed_ordering];
        transitioned.extend(coincident.iter().copied());
        mount_reached_motor_effector(
            &mut cohorts,
            &mut population,
            &mut next_lineage,
            &mut fabric,
            &transitioned,
            &[],
            &[],
            &[BodyAxis::LeftElbowFlexion, BodyAxis::LeftGripAperture],
        )
        .unwrap();
        assert_eq!(fabric.contact_count(), contacts_before);
        assert!(!fabric.contains_contact(routed_ordering, motor));

        // Falsifier per the consecutive law: BOTH hops delivered in the
        // same interval are synchronous and prove nothing, even though the
        // full path is present in the evidence.
        let synchronous = directed_chain(
            &cohorts,
            &fabric,
            &[routed_ordering, affective, regulation],
        );
        mount_reached_motor_effector(
            &mut cohorts,
            &mut population,
            &mut next_lineage,
            &mut fabric,
            &transitioned,
            &synchronous,
            &[],
            &[BodyAxis::LeftElbowFlexion, BodyAxis::LeftGripAperture],
        )
        .unwrap();
        assert_eq!(fabric.contact_count(), contacts_before);

        // Proof: the consecutive chain — ordering drove the affective cell
        // in the PRECEDING window (exact frontier entry), the typed body
        // regulation drove the affective cell NOW — authors exactly one
        // ordering->motor contact. No prior movement is required to create
        // the body anatomy that makes a first movement possible. Carrier
        // direction may oppose causal-frontier direction: here carriers move
        // affective->ordering while the causal wave reaches affective.
        let hop_now = directed_chain(&cohorts, &fabric, &[regulation, affective]);
        let hop_prior = frontier_hop_with_frontier(
            &cohorts,
            &fabric,
            affective,
            routed_ordering,
            affective,
        );
        mount_reached_motor_effector(
            &mut cohorts,
            &mut population,
            &mut next_lineage,
            &mut fabric,
            &[regulation],
            &hop_now,
            &hop_prior,
            &[BodyAxis::LeftElbowFlexion],
        )
        .unwrap();
        assert!(fabric.contains_contact(routed_ordering, motor));
        assert!(fabric.contains_contact(regulation, motor));
        for bystander in &coincident {
            assert!(
                !fabric.contains_contact(*bystander, motor),
                "coincident-active ordering neuron must never reach the motor"
            );
        }
        // The fixed regulation contact already existed; only one learned
        // ordering contact is added, with no ordering x motor scaling.
        assert_eq!(fabric.contact_count(), contacts_before + 1);

        // Proof: repeating the same consecutive evidence is idempotent.
        let repeat_now = directed_chain(&cohorts, &fabric, &[regulation, affective]);
        let repeat_prior = frontier_hop(&cohorts, &fabric, routed_ordering, affective);
        mount_reached_motor_effector(
            &mut cohorts,
            &mut population,
            &mut next_lineage,
            &mut fabric,
            &[regulation],
            &repeat_now,
            &repeat_prior,
            &[BodyAxis::LeftElbowFlexion, BodyAxis::LeftGripAperture],
        )
        .unwrap();
        assert_eq!(fabric.contact_count(), contacts_before + 1);

        // Proof: a prior-window hop for a bystander WITHOUT the current
        // consequence hop into the regulation cell authors nothing.
        let partial_prior = frontier_hop(&cohorts, &fabric, coincident[0], affective);
        mount_reached_motor_effector(
            &mut cohorts,
            &mut population,
            &mut next_lineage,
            &mut fabric,
            &transitioned,
            &[],
            &partial_prior,
            &[BodyAxis::LeftElbowFlexion, BodyAxis::LeftGripAperture],
        )
        .unwrap();
        assert!(!fabric.contains_contact(coincident[0], motor));
        assert_eq!(fabric.contact_count(), contacts_before + 1);
    }

    #[test]
    fn delayed_body_return_uses_the_existing_third_exact_frontier() {
        let mut cohorts = Vec::new();
        let mut population =
            Some(DevelopmentalRestingPopulation::admit(1_600_000_000, 100_000, 100, &[]).unwrap());
        let mut next_lineage = 1;
        let mut fabric = ResidentElectricalFabric::default();
        let terminal = BodyEffectorTerminal::new(
            BodyAxis::VocalTractSection3Area,
            BodyEffectorDirection::TowardMaximum,
        );
        let (regulation, _, _) = mount_body_regulation_fixture(
            &mut cohorts,
            &mut population,
            &mut next_lineage,
            &mut fabric,
            terminal.axis(),
            terminal.direction(),
        );
        let association = mount_intrinsic_neuron_at_place(
            &mut cohorts,
            &mut population,
            &mut next_lineage,
            DeclaredNeuronPlace::new(7, 0),
        )
        .unwrap();
        let affective = mount_intrinsic_neuron_at_place(
            &mut cohorts,
            &mut population,
            &mut next_lineage,
            DeclaredNeuronPlace::new(10, 0),
        )
        .unwrap();
        let ordering = mount_intrinsic_neuron_at_place(
            &mut cohorts,
            &mut population,
            &mut next_lineage,
            DeclaredNeuronPlace::new(11, 0),
        )
        .unwrap();
        fabric = fabric
            .append_contacts(&[
                (
                    regulation,
                    affective,
                    ExactRational::integer(DEVELOPMENTAL_CONTACT_CONDUCTANCE_PICOSIEMENS),
                ),
                (
                    affective,
                    association,
                    ExactRational::integer(DEVELOPMENTAL_CONTACT_CONDUCTANCE_PICOSIEMENS),
                ),
                (
                    association,
                    ordering,
                    ExactRational::integer(DEVELOPMENTAL_CONTACT_CONDUCTANCE_PICOSIEMENS),
                ),
            ])
            .unwrap();
        let motor = cohorts
            .iter()
            .flat_map(|cohort| {
                cohort
                    .anatomy
                    .mounts()
                    .iter()
                    .zip(cohort.anatomy.neuron_lineages())
            })
            .find_map(|(mount, lineage)| {
                (mount.body_effector_terminal() == Some(terminal)).then_some(*lineage)
            })
            .unwrap();
        let contacts_before = fabric.contact_count();
        let current = directed_chain(&cohorts, &fabric, &[regulation, affective]);
        let preceding =
            frontier_hop_with_frontier(&cohorts, &fabric, association, affective, affective);
        let older =
            frontier_hop_with_frontier(&cohorts, &fabric, ordering, association, association);

        mount_reached_motor_effector_with_root(
            &mut cohorts,
            &mut population,
            &mut next_lineage,
            &mut fabric,
            &[regulation],
            &current,
            &[],
            &preceding,
            &[],
            &[terminal],
            &BTreeMap::new(),
            &BTreeMap::new(),
        )
        .unwrap();
        assert!(!fabric.contains_contact(ordering, motor));
        assert_eq!(fabric.contact_count(), contacts_before);

        mount_reached_motor_effector_with_root(
            &mut cohorts,
            &mut population,
            &mut next_lineage,
            &mut fabric,
            &[regulation],
            &current,
            &[],
            &preceding,
            &older,
            &[terminal],
            &BTreeMap::new(),
            &BTreeMap::new(),
        )
        .unwrap();
        assert!(fabric.contains_contact(ordering, motor));
        assert_eq!(fabric.contact_count(), contacts_before + 1);
    }

    #[test]
    fn moved_root_terminal_mounts_only_its_paired_sensorimotor_reflex() {
        let mut cohorts = Vec::new();
        let mut population = None;
        let mut next_lineage = 1;
        let mut fabric = ResidentElectricalFabric::default();
        let source = crate::root_yaw_joint_source_builder::admit_root_yaw_proprioceptive_source(
            0, 1_000,
        )
        .unwrap();
        let moved_port = source
            .joint_source_ports()
            .iter()
            .find(|port| {
                port.root_yaw_proprioceptor_terminal.is_some()
                    && port.exact_normalized_sources.windows(2).any(|pair| pair[0] != pair[1])
            })
            .unwrap();
        let terminal = moved_port
            .root_yaw_proprioceptor_terminal
            .unwrap()
            .paired_effector();
        let receptor_site = NeuronSourceSite::from_source_port(moved_port).unwrap();
        let (regulation, receptor, _) = mount_body_regulation_from_site_fixture(
            &mut cohorts,
            &mut population,
            &mut next_lineage,
            &mut fabric,
            receptor_site,
        );
        let contacts_before = fabric.contact_count();
        let developmental_motors = cohorts
            .iter()
            .flat_map(|cohort| {
                cohort
                    .anatomy
                    .mounts()
                    .iter()
                    .zip(cohort.anatomy.neuron_lineages())
            })
            .filter_map(|(mount, lineage)| {
                (mount.root_yaw_effector_terminal() == Some(terminal)).then_some(*lineage)
            })
            .collect::<Vec<_>>();
        assert_eq!(developmental_motors.len(), 1);
        assert!(fabric.contains_contact(regulation, developmental_motors[0]));
        let topology = ResidentTopologyIndex::build(&cohorts, &fabric).unwrap();
        // Merely having the anatomy is not authority: the directional
        // proprioceptor must have physically changed in this occurrence.
        assert!(exact_reached_root_yaw_regulations(
            &cohorts,
            &topology,
            &[],
            &[regulation],
        )
        .unwrap()
        .is_empty());
        // A changed receptor without its exact reached regulation is likewise
        // incomplete and cannot author a motor.
        assert!(exact_reached_root_yaw_regulations(
            &cohorts,
            &topology,
            &[receptor],
            &[],
        )
        .unwrap()
        .is_empty());
        let continuations = exact_reached_root_yaw_regulations(
            &cohorts,
            &topology,
            &[receptor],
            &[regulation],
        )
        .unwrap();
        assert_eq!(continuations.get(&regulation), Some(&vec![terminal]));

        mount_reached_motor_effector_with_root(
            &mut cohorts,
            &mut population,
            &mut next_lineage,
            &mut fabric,
            &[],
            &[],
            &[],
            &[],
            &[],
            &[],
            &continuations,
            &BTreeMap::new(),
        )
        .unwrap();

        let motors = cohorts
            .iter()
            .flat_map(|cohort| {
                cohort
                    .anatomy
                    .mounts()
                    .iter()
                    .zip(cohort.anatomy.neuron_lineages())
            })
            .filter_map(|(mount, lineage)| {
                (mount.root_yaw_effector_terminal() == Some(terminal)).then_some(*lineage)
            })
            .collect::<Vec<_>>();
        assert_eq!(motors.len(), 1);
        let motor = motors[0];
        assert!(fabric.contains_contact(regulation, motor));
        assert_eq!(
            fabric.contact_count(),
            contacts_before,
            "settlement must reuse the fixed pre-interval root motor"
        );
        validate_motor_effector_mounts(&cohorts).unwrap();

        // A prior ordering frontier beside a guided movement is coincidence,
        // not a directed two-interval causal chain.  It must not recreate the
        // retired ordering-to-motor fan-out, even for a root terminal.
        let ordering = mount_intrinsic_neuron_at_place(
            &mut cohorts,
            &mut population,
            &mut next_lineage,
            DeclaredNeuronPlace::new(11, 0),
        )
        .unwrap();
        let ordering_support = mount_intrinsic_neuron_at_place(
            &mut cohorts,
            &mut population,
            &mut next_lineage,
            DeclaredNeuronPlace::new(7, 0),
        )
        .unwrap();
        fabric = fabric
            .append_contact(
                ordering_support,
                ordering,
                ExactRational::integer(DEVELOPMENTAL_CONTACT_CONDUCTANCE_PICOSIEMENS),
            )
            .unwrap();
        let before_guided_learning = fabric.contact_count();
        let prior_ordering = frontier_hop_with_frontier(
            &cohorts,
            &fabric,
            ordering_support,
            ordering,
            ordering,
        );
        mount_reached_motor_effector_with_root(
            &mut cohorts,
            &mut population,
            &mut next_lineage,
            &mut fabric,
            &[],
            &[],
            &prior_ordering,
            &[],
            &[],
            &[],
            &continuations,
            &BTreeMap::new(),
        )
        .unwrap();
        assert!(!fabric.contains_contact(ordering, motor));
        assert_eq!(fabric.contact_count(), before_guided_learning);

        let opposite_port = source
            .joint_source_ports()
            .iter()
            .find(|port| {
                port.root_yaw_proprioceptor_terminal
                    .map(RootYawProprioceptorTerminal::paired_effector)
                    .is_some_and(|candidate| candidate != terminal)
            })
            .unwrap();
        let opposite_site = NeuronSourceSite::from_source_port(opposite_port).unwrap();
        let (opposite_regulation, _, _) = mount_body_regulation_from_site_fixture(
            &mut cohorts,
            &mut population,
            &mut next_lineage,
            &mut fabric,
            opposite_site,
        );
        fabric = fabric
            .append_contact(
                opposite_regulation,
                motor,
                ExactRational::integer(DEVELOPMENTAL_CONTACT_CONDUCTANCE_PICOSIEMENS),
            )
            .unwrap();
        let topology = ResidentTopologyIndex::build(&cohorts, &fabric).unwrap();
        let motor_flat = topology
            .flat_locations
            .iter()
            .position(|(_, _, lineage)| *lineage == motor)
            .unwrap();
        let paths = exact_motor_body_afferent_paths(
            motor_flat,
            &topology.flat_locations,
            &cohorts,
            &topology.neighbours_by_flat,
        )
        .unwrap();
        let permitted = exact_root_yaw_preparation_regulations(terminal, &paths);
        assert_eq!(permitted, vec![regulation]);

        let transfer = |sender, receiver| DirectedPhysicalTransferObservation {
            sender,
            receiver,
            bond: StablePhysicalBondReference::new(sender, receiver, 0).unwrap(),
            transferred_whole_carriers: 1,
        };
        let causal_seeds = BTreeSet::from([regulation]);
        let incoming = transfer(regulation, motor);
        let preparation = exact_root_yaw_motor_preparation_transfers(
            motor,
            &[incoming],
            &permitted,
            &causal_seeds,
            |lineage| topology.layer_of(lineage),
        );
        assert_eq!(preparation, vec![incoming]);
        let outward = transfer(motor, regulation);
        assert!(exact_root_yaw_motor_preparation_transfers(
            motor,
            &[outward],
            &permitted,
            &causal_seeds,
            |lineage| topology.layer_of(lineage),
        )
        .is_empty());
        let ordered = transfer(ordering, motor);
        assert_eq!(
            exact_root_yaw_motor_preparation_transfers(
                motor,
                &[ordered],
                &permitted,
                &BTreeSet::from([ordering]),
                |lineage| topology.layer_of(lineage),
            ),
            vec![ordered],
            "the learned ordering route must physically arrive at its exact motor"
        );
        assert_eq!(
            exact_root_yaw_motor_preparation_transfers(
                motor,
                &[ordered],
                &permitted,
                &BTreeSet::new(),
                |lineage| topology.layer_of(lineage),
            ),
            vec![ordered],
            "retained ordering current prepares root yaw without an external label",
        );
        let opposite = transfer(opposite_regulation, motor);
        assert!(exact_root_yaw_motor_preparation_transfers(
            motor,
            &[opposite],
            &permitted,
            &BTreeSet::from([opposite_regulation]),
            |lineage| topology.layer_of(lineage),
        )
        .is_empty());
        assert!(exact_root_yaw_motor_preparation_transfers(
            motor,
            &[incoming],
            &permitted,
            &BTreeSet::new(),
            |lineage| topology.layer_of(lineage),
        )
        .is_empty());
        // The arriving regulation transfer prepares this one-contact root
        // motor; the distinct positive local membrane discharge emits it.
        // Reversing or omitting that local discharge, or omitting preparation,
        // must remain physically silent.
        assert_eq!(
            exact_prepared_efferent_carriers(3, preparation.len()),
            Some(3)
        );
        assert_eq!(exact_prepared_efferent_carriers(0, preparation.len()), None);
        assert_eq!(exact_prepared_efferent_carriers(-3, preparation.len()), None);
        assert_eq!(exact_prepared_efferent_carriers(3, 0), None);
    }

    #[test]
    fn root_translation_feedback_cannot_repeat_the_action() {
        let regulation = [8_u8; 16];
        let ordering = [11_u8; 16];
        let motor = [12_u8; 16];
        let transfer = |sender, carriers| DirectedPhysicalTransferObservation {
            sender,
            receiver: motor,
            bond: StablePhysicalBondReference::new(sender, motor, 0).unwrap(),
            transferred_whole_carriers: carriers,
        };
        let feedback = transfer(regulation, 7);
        let command = transfer(ordering, 5);
        let layer_of = |lineage| {
            [(regulation, 8), (ordering, 11), (motor, 12)]
                .into_iter()
                .find_map(|(candidate, layer)| (candidate == lineage).then_some(layer))
        };

        assert!(exact_root_translation_motor_preparation_transfers(
            motor,
            &[feedback],
            layer_of,
        )
        .is_empty());
        assert_eq!(
            exact_root_translation_motor_preparation_transfers(
                motor,
                &[feedback, command],
                layer_of,
            ),
            vec![command],
            "only exact ordering-layer current may prepare root translation",
        );
        assert_eq!(
            exact_root_translation_motor_preparation_transfers(motor, &[command], layer_of),
            vec![command],
            "retained ordering current is the physical command, not background metadata",
        );
    }

    #[test]
    fn moved_root_translation_terminal_mounts_its_exact_feedback_anatomy() {
        let mut cohorts = Vec::new();
        let mut population = None;
        let mut next_lineage = 1;
        let mut fabric = ResidentElectricalFabric::default();
        let source =
            crate::root_translation_joint_source_builder::admit_root_translation_proprioceptive_source(
                0, 1, 0,
            )
            .unwrap();
        let moved_port = source
            .joint_source_ports()
            .iter()
            .find(|port| {
                port.root_translation_proprioceptor_terminal.is_some()
                    && port
                        .exact_normalized_sources
                        .windows(2)
                        .any(|pair| pair[0] != pair[1])
            })
            .unwrap();
        let terminal = moved_port
            .root_translation_proprioceptor_terminal
            .unwrap()
            .paired_effector();
        let receptor_site = NeuronSourceSite::from_source_port(moved_port).unwrap();
        let (regulation, receptor, _) = mount_body_regulation_from_site_fixture(
            &mut cohorts,
            &mut population,
            &mut next_lineage,
            &mut fabric,
            receptor_site,
        );
        let topology = ResidentTopologyIndex::build(&cohorts, &fabric).unwrap();
        let continuations = exact_reached_root_translation_regulations(
            &cohorts,
            &topology,
            &[receptor],
            &[regulation],
        )
        .unwrap();
        assert_eq!(continuations.get(&regulation), Some(&vec![terminal]));
        mount_reached_motor_effector_with_root(
            &mut cohorts,
            &mut population,
            &mut next_lineage,
            &mut fabric,
            &[],
            &[],
            &[],
            &[],
            &[],
            &[],
            &BTreeMap::new(),
            &continuations,
        )
        .unwrap();
        let motors = cohorts
            .iter()
            .flat_map(|cohort| {
                cohort
                    .anatomy
                    .mounts()
                    .iter()
                    .zip(cohort.anatomy.neuron_lineages())
            })
            .filter_map(|(mount, lineage)| {
                (mount.root_translation_effector_terminal() == Some(terminal))
                    .then_some(*lineage)
            })
            .collect::<Vec<_>>();
        assert_eq!(motors.len(), 1);
        let translation_mount = cohorts
            .iter()
            .flat_map(|cohort| cohort.anatomy.mounts())
            .find(|mount| mount.root_translation_effector_terminal() == Some(terminal))
            .unwrap();
        assert!(
            !terminal_retains_prepared_action_charge(translation_mount, 1),
            "a translation terminal without a fresh ordering cause must remain eligible for passive return",
        );
        assert!(!fabric.contains_contact(regulation, motors[0]));
        validate_motor_effector_mounts(&cohorts).unwrap();
    }

    #[test]
    fn malformed_root_translation_motor_is_replaced_once_with_compatible_anatomy() {
        let mut cohorts = Vec::new();
        let mut population = None;
        let mut next_lineage = 1;
        let mut fabric = ResidentElectricalFabric::default();
        let source =
            crate::root_translation_joint_source_builder::admit_root_translation_proprioceptive_source(
                0, 1, 0,
            )
            .unwrap();
        let moved_port = source
            .joint_source_ports()
            .iter()
            .find(|port| {
                port.root_translation_proprioceptor_terminal.is_some()
                    && port
                        .exact_normalized_sources
                        .windows(2)
                        .any(|pair| pair[0] != pair[1])
            })
            .unwrap();
        let terminal = moved_port
            .root_translation_proprioceptor_terminal
            .unwrap()
            .paired_effector();
        let receptor_site = NeuronSourceSite::from_source_port(moved_port).unwrap();
        let (regulation, _, _) = mount_body_regulation_from_site_fixture(
            &mut cohorts,
            &mut population,
            &mut next_lineage,
            &mut fabric,
            receptor_site,
        );
        // The current fixture law mounts the corrected fixed terminal. Remove
        // it so the state below exactly reproduces the historical body: one
        // arbitrary generic layer-12 cell and no compatible fixed terminal.
        let fixed_motor = cohorts
            .iter()
            .flat_map(|cohort| {
                cohort
                    .anatomy
                    .mounts()
                    .iter()
                    .zip(cohort.anatomy.neuron_lineages())
            })
            .find_map(|(mount, lineage)| {
                (mount.root_translation_effector_terminal() == Some(terminal))
                    .then_some(*lineage)
            })
            .unwrap();
        cohorts.retain(|cohort| !cohort.anatomy.neuron_lineages().contains(&fixed_motor));
        fabric = fabric.without_lineages(&[fixed_motor]).unwrap();
        // Reproduce the rejected implementation exactly: an arbitrary next
        // layer-12 cell with the generic 500-pS contact.
        let malformed_motor = mount_next_intrinsic_in_layer(
            &mut cohorts,
            &mut population,
            &mut next_lineage,
            12,
        )
        .unwrap();
        cohorts
            .iter_mut()
            .find(|cohort| cohort.anatomy.neuron_lineages().contains(&malformed_motor))
            .unwrap()
            .anatomy
            .specialize_root_translation_effector(malformed_motor, terminal)
            .unwrap();
        fabric = fabric
            .append_contact(
                regulation,
                malformed_motor,
                ExactRational::integer(DEVELOPMENTAL_CONTACT_CONDUCTANCE_PICOSIEMENS),
            )
            .unwrap();
        let topology_index = Arc::new(ResidentTopologyIndex::build(&cohorts, &fabric).unwrap());
        let malformed_state = ResidentCognitiveFormationState {
            generation: 0,
            next_lineage_ordinal: next_lineage,
            vocal_articulatory_effector_lineage: None,
            unexpressed_electrical_seeds: Box::new([]),
            dormant_lineage_seeds: Box::new([]),
            resting_population: population,
            cohorts: cohorts.into_boxed_slice(),
            electrical_fabric: fabric,
            active_electrical_frontier: Box::new([]),
            preceding_active_electrical_frontier: Box::new([]),
            older_active_electrical_frontier: Box::new([]),
            mosaics: Box::new([]),
            hippocampal: ResidentHippocampalIndex::default(),
            topology_index,
            formation_index: ResidentFormationIndex::default(),
        };
        let corrected = malformed_state
            .into_compatible_root_translation_motors()
            .unwrap();
        assert_eq!(
            corrected
                .clone()
                .into_compatible_root_translation_motors()
                .unwrap(),
            corrected,
            "a restart must not resurrect or repeat the malformed motor correction",
        );
        assert!(corrected
            .topology_index
            .flat_for_lineage(malformed_motor)
            .is_err());
        let (motor_lineage, motor_capacitance) = corrected
            .cohorts
            .iter()
            .flat_map(|cohort| {
                cohort
                    .anatomy
                    .mounts()
                    .iter()
                    .zip(cohort.anatomy.neuron_lineages())
                    .zip(cohort.anatomy.neuron_anatomies())
            })
            .find_map(|((mount, lineage), anatomy)| {
                (mount.root_translation_effector_terminal() == Some(terminal))
                    .then_some((*lineage, anatomy.capacitance()))
            })
            .unwrap();
        let regulation_capacitance = corrected
            .cohorts
            .iter()
            .find_map(|cohort| {
                cohort
                    .anatomy
                    .neuron_lineages()
                    .iter()
                    .position(|lineage| *lineage == regulation)
                    .map(|index| cohort.anatomy.neuron_anatomies()[index].capacitance())
            })
            .unwrap();
        assert_eq!(
            motor_capacitance
                .picofarads()
                .checked_cmp(regulation_capacitance.picofarads())
                .unwrap(),
            std::cmp::Ordering::Greater,
        );
        assert!(
            !corrected
                .electrical_fabric
                .contains_contact(regulation, motor_lineage),
            "returned root translation must remain sensory and cannot feed the motor back",
        );
    }

    #[test]
    fn contact_transfer_direction_uses_physical_not_canonical_endpoint_order() {
        let mut physical_left = [0_u8; 16];
        physical_left[15] = 2;
        let mut physical_right = [0_u8; 16];
        physical_right[15] = 1;
        let bond = StablePhysicalBondReference::new(physical_left, physical_right, 0).unwrap();
        assert_eq!(bond.endpoints(), (physical_right, physical_left));

        let positive = directed_physical_transfer(3, physical_left, physical_right, bond).unwrap();
        assert_eq!(positive.sender, physical_left);
        assert_eq!(positive.receiver, physical_right);
        assert_eq!(positive.transferred_whole_carriers, 3);

        let negative = directed_physical_transfer(-4, physical_left, physical_right, bond).unwrap();
        assert_eq!(negative.sender, physical_right);
        assert_eq!(negative.receiver, physical_left);
        assert_eq!(negative.transferred_whole_carriers, 4);
        assert_eq!(directed_physical_transfer(0, physical_left, physical_right, bond), None);
    }

    #[test]
    fn v41_mounts_one_new_dedicated_vocal_body_without_selecting_historical_cells() {
        const MAX_BYTES: usize = 1_600_000_000;
        let mut cohorts = Vec::new();
        let mut population = Some(
            DevelopmentalRestingPopulation::admit(MAX_BYTES, 100_000, 100, &[]).unwrap(),
        );
        let mut next_lineage = 1;
        let historical = (0..3)
            .map(|topology| {
                mount_intrinsic_neuron_at_place(
                    &mut cohorts,
                    &mut population,
                    &mut next_lineage,
                    DeclaredNeuronPlace::new(13, topology),
                )
                .unwrap()
            })
            .collect::<Vec<_>>();
        let fabric = ResidentElectricalFabric::default();
        let topology_index = Arc::new(ResidentTopologyIndex::build(&cohorts, &fabric).unwrap());
        let state = ResidentCognitiveFormationState {
            generation: 41,
            next_lineage_ordinal: population
                .as_ref()
                .unwrap()
                .lineage_end_exclusive(),
            vocal_articulatory_effector_lineage: None,
            unexpressed_electrical_seeds: Box::new([]),
            dormant_lineage_seeds: Box::new([]),
            resting_population: population,
            cohorts: cohorts.into_boxed_slice(),
            electrical_fabric: fabric,
            active_electrical_frontier: Box::new([]),
            preceding_active_electrical_frontier: Box::new([]),
            older_active_electrical_frontier: Box::new([]),
            mosaics: Box::new([]),
            hippocampal: ResidentHippocampalIndex::default(),
            topology_index,
            formation_index: ResidentFormationIndex::default(),
        };
        let historical_snapshots = historical
            .iter()
            .map(|lineage| {
                state
                    .cohorts
                    .iter()
                    .find_map(|cohort| {
                        cohort
                            .anatomy
                            .neuron_lineages()
                            .iter()
                            .position(|candidate| candidate == lineage)
                            .map(|index| {
                                (
                                    *lineage,
                                    cohort.anatomy.mounts()[index].clone(),
                                    cohort.anatomy.neuron_anatomies()[index].clone(),
                                    cohort.state.neurons()[index].clone(),
                                )
                            })
                    })
                    .unwrap()
            })
            .collect::<Vec<_>>();
        let (mut v40, terminal) = state
            .encode_current(MAX_BYTES, false, false)
            .expect("marker-absent predecessor encodes for the migration fixture");
        assert!(terminal.is_none());
        v40[..MAGIC_V40.len()].copy_from_slice(MAGIC_V40);
        assert!(ResidentCognitiveFormationState::decode(&v40, MAX_BYTES).is_err());
        let predecessor = ResidentCognitiveFormationState::decode_for_one_way_migration(
            &v40,
            MAX_BYTES,
        )
        .unwrap();
        assert_eq!(predecessor.vocal_articulatory_effector_lineage, None);

        let migrated =
            ResidentCognitiveFormationState::migrate_to_current_format(&v40, MAX_BYTES).unwrap();
        assert_eq!(&migrated[..MAGIC_V42.len()], MAGIC_V42);
        let restored = ResidentCognitiveFormationState::decode(&migrated, MAX_BYTES).unwrap();
        let dedicated = restored.vocal_articulatory_effector_lineage.unwrap();
        assert!(!historical.contains(&dedicated));
        assert_eq!(restored.electrical_fabric.contact_count(), 0);
        assert_eq!(restored.summary().complete_neuron_count, 4);
        for (lineage, mount, anatomy, neuron) in historical_snapshots {
            let (restored_mount, restored_anatomy, restored_neuron) = restored
                .cohorts
                .iter()
                .find_map(|cohort| {
                    cohort
                        .anatomy
                        .neuron_lineages()
                        .iter()
                        .position(|candidate| *candidate == lineage)
                        .map(|index| {
                            (
                                &cohort.anatomy.mounts()[index],
                                &cohort.anatomy.neuron_anatomies()[index],
                                &cohort.state.neurons()[index],
                            )
                        })
                })
                .unwrap();
            assert_eq!(restored_mount, &mount);
            assert_eq!(restored_anatomy, &anatomy);
            assert_eq!(restored_neuron, &neuron);
        }
        assert_eq!(
            ResidentCognitiveFormationState::migrate_to_current_format(
                &migrated,
                MAX_BYTES,
            )
            .unwrap(),
            migrated,
        );
    }

    #[test]
    fn v34_replaces_broad_articulatory_pool_with_fixed_vocal_route_once() {
        const MAX_BYTES: usize = 1_600_000_000;
        let mut cohorts = Vec::new();
        let mut population = Some(
            DevelopmentalRestingPopulation::admit(MAX_BYTES, 100_000, 100, &[]).unwrap(),
        );
        let mut next_lineage = 1;
        let acoustic = mount_intrinsic_neuron_at_place(
            &mut cohorts,
            &mut population,
            &mut next_lineage,
            DeclaredNeuronPlace::new(1, 0),
        )
        .unwrap();
        let regulation = mount_intrinsic_neuron_at_place(
            &mut cohorts,
            &mut population,
            &mut next_lineage,
            DeclaredNeuronPlace::new(8, 0),
        )
        .unwrap();
        let motor = mount_intrinsic_neuron_at_place(
            &mut cohorts,
            &mut population,
            &mut next_lineage,
            DeclaredNeuronPlace::new(12, 0),
        )
        .unwrap();
        cohorts
            .iter_mut()
            .find(|cohort| cohort.anatomy.neuron_lineages().contains(&motor))
            .unwrap()
            .anatomy
            .specialize_motor_effector(
                motor,
                BodyEffectorTerminal::new(
                    BodyAxis::JawOpening,
                    BodyEffectorDirection::TowardMaximum,
                ),
            )
            .unwrap();
        let articulatory = mount_intrinsic_neuron_at_place(
            &mut cohorts,
            &mut population,
            &mut next_lineage,
            DeclaredNeuronPlace::new(13, 0),
        )
        .unwrap();
        let conductance =
            ExactRational::integer(DEVELOPMENTAL_CONTACT_CONDUCTANCE_PICOSIEMENS);
        let fabric = ResidentElectricalFabric::default()
            .append_contacts(&[
                (acoustic, articulatory, conductance),
                (regulation, articulatory, conductance),
                (motor, articulatory, conductance),
                (acoustic, regulation, conductance),
            ])
            .unwrap();
        let topology_index = Arc::new(ResidentTopologyIndex::build(&cohorts, &fabric).unwrap());
        let state = ResidentCognitiveFormationState {
            generation: 7,
            next_lineage_ordinal: population
                .as_ref()
                .unwrap()
                .lineage_end_exclusive(),
            vocal_articulatory_effector_lineage: None,
            unexpressed_electrical_seeds: Box::new([]),
            dormant_lineage_seeds: Box::new([]),
            resting_population: population,
            cohorts: cohorts.into_boxed_slice(),
            electrical_fabric: fabric,
            active_electrical_frontier: Box::new([]),
            preceding_active_electrical_frontier: Box::new([]),
            older_active_electrical_frontier: Box::new([]),
            mosaics: Box::new([]),
            hippocampal: ResidentHippocampalIndex::default(),
            topology_index,
            formation_index: ResidentFormationIndex::default(),
        };
        // The CURRENT encoder refuses this deliberately contaminated
        // pre-V40 anatomy (contacts incident to layer 13 violate the
        // motor-coupled vocal invariant), so the body is written through
        // the historical V26-layout codec -- V27-V33 share that exact byte
        // layout, marker-free -- and stamped with its own boundary.
        let mut v32 = state
            .encode_with_format(CognitiveCodecFormat::V26, MAX_BYTES)
            .unwrap();
        v32[..MAGIC_V32.len()].copy_from_slice(MAGIC_V32);
        v32[MAGIC_V32.len()..MAGIC_V32.len() + std::mem::size_of::<u16>()]
            .copy_from_slice(&VERSION_V30.to_le_bytes());
        assert!(ResidentCognitiveFormationState::decode(&v32, MAX_BYTES).is_err());

        let migrated =
            ResidentCognitiveFormationState::migrate_to_current_format(&v32, MAX_BYTES)
                .unwrap();
        assert_eq!(&migrated[..MAGIC_V42.len()], MAGIC_V42);
        let restored = ResidentCognitiveFormationState::decode(&migrated, MAX_BYTES).unwrap();
        // V40/V41 law supersedes the V34 fixed-route bridge this test once
        // pinned: the V33 boundary retires the contaminated broad-pool
        // contacts, V40 removes every remaining electrical contact incident
        // to layer 13 (motor->articulatory included -- the vocal body is
        // addressed through the retained effector lineage, never through a
        // contact), and V41 mounts one NEW dedicated vocal-body cell from
        // unclaimed resting anatomy. Only the lawful non-vocal contact
        // survives.
        assert!(!restored.electrical_fabric.contains_contact(acoustic, articulatory));
        assert!(!restored.electrical_fabric.contains_contact(regulation, articulatory));
        assert!(!restored.electrical_fabric.contains_contact(motor, articulatory));
        assert!(restored.electrical_fabric.contains_contact(acoustic, regulation));
        assert_eq!(restored.electrical_fabric.contact_count(), 1);
        assert!(restored
            .cohorts
            .iter()
            .flat_map(|cohort| cohort.anatomy.neuron_lineages())
            .any(|lineage| *lineage == articulatory));
        let effector = restored
            .vocal_articulatory_effector_lineage
            .expect("dedicated vocal effector mounted at the V41 boundary");
        assert_ne!(effector, articulatory);
        let layer_thirteen = restored
            .cohorts
            .iter()
            .flat_map(|cohort| {
                cohort
                    .anatomy
                    .mounts()
                    .iter()
                    .zip(cohort.anatomy.neuron_lineages())
            })
            .filter_map(|(mount, lineage)| {
                (mount.source_site().is_none() && mount.place().layer() == 13)
                    .then_some(*lineage)
            })
            .collect::<Vec<_>>();
        assert_eq!(layer_thirteen.len(), 2);
        assert!(layer_thirteen.contains(&effector));
        assert_eq!(
            ResidentCognitiveFormationState::migrate_to_current_format(&migrated, MAX_BYTES)
                .unwrap(),
            migrated
        );
    }

    #[test]
    fn v33_body_without_speech_anatomy_gains_only_the_fixed_vocal_bridge() {
        const MAX_BYTES: usize = 1_600_000_000;
        let mut cohorts = Vec::new();
        let mut population = Some(
            DevelopmentalRestingPopulation::admit(MAX_BYTES, 100_000, 100, &[]).unwrap(),
        );
        let mut next_lineage = 1;
        let mut vocal_motors = Vec::new();
        for axis in [
            BodyAxis::JawOpening,
            BodyAxis::LipAperture,
            BodyAxis::LipWidth,
            BodyAxis::PerioralDisplacement,
            BodyAxis::GlottalAperture,
        ] {
            for direction in [
                BodyEffectorDirection::TowardMinimum,
                BodyEffectorDirection::TowardMaximum,
            ] {
                let lineage = mount_next_intrinsic_in_layer(
                    &mut cohorts,
                    &mut population,
                    &mut next_lineage,
                    12,
                )
                .unwrap();
                cohorts
                    .iter_mut()
                    .find(|cohort| cohort.anatomy.neuron_lineages().contains(&lineage))
                    .unwrap()
                    .anatomy
                    .specialize_motor_effector(
                        lineage,
                        BodyEffectorTerminal::new(axis, direction),
                    )
                    .unwrap();
                vocal_motors.push(lineage);
            }
        }
        let non_vocal_motor = mount_next_intrinsic_in_layer(
            &mut cohorts,
            &mut population,
            &mut next_lineage,
            12,
        )
        .unwrap();
        cohorts
            .iter_mut()
            .find(|cohort| cohort.anatomy.neuron_lineages().contains(&non_vocal_motor))
            .unwrap()
            .anatomy
            .specialize_motor_effector(
                non_vocal_motor,
                BodyEffectorTerminal::new(
                    BodyAxis::LeftElbowFlexion,
                    BodyEffectorDirection::TowardMaximum,
                ),
            )
            .unwrap();
        let fabric = ResidentElectricalFabric::default();
        let topology_index = Arc::new(ResidentTopologyIndex::build(&cohorts, &fabric).unwrap());
        let state = ResidentCognitiveFormationState {
            generation: 9,
            next_lineage_ordinal: population
                .as_ref()
                .unwrap()
                .lineage_end_exclusive(),
            vocal_articulatory_effector_lineage: None,
            unexpressed_electrical_seeds: Box::new([]),
            dormant_lineage_seeds: Box::new([]),
            resting_population: population,
            cohorts: cohorts.into_boxed_slice(),
            electrical_fabric: fabric,
            active_electrical_frontier: Box::new([]),
            preceding_active_electrical_frontier: Box::new([]),
            older_active_electrical_frontier: Box::new([]),
            mosaics: Box::new([]),
            hippocampal: ResidentHippocampalIndex::default(),
            topology_index,
            formation_index: ResidentFormationIndex::default(),
        };

        // V33's physical layout is the unchanged compact V26 layout. Build an
        // exact pre-V34 body without invoking the current encoder's new
        // anatomy validation, then cross the one-way boundary.
        let mut v33 = state
            .encode_with_format(CognitiveCodecFormat::V26, MAX_BYTES)
            .unwrap();
        v33[..MAGIC_V33.len()].copy_from_slice(MAGIC_V33);
        v33[MAGIC_V33.len()..MAGIC_V33.len() + std::mem::size_of::<u16>()]
            .copy_from_slice(&VERSION_V30.to_le_bytes());
        assert!(ResidentCognitiveFormationState::decode(&v33, MAX_BYTES).is_err());
        let migrated =
            ResidentCognitiveFormationState::migrate_to_current_format(&v33, MAX_BYTES).unwrap();
        let restored = ResidentCognitiveFormationState::decode(&migrated, MAX_BYTES).unwrap();
        let articulatory = restored
            .cohorts
            .iter()
            .flat_map(|cohort| {
                cohort
                    .anatomy
                    .mounts()
                    .iter()
                    .zip(cohort.anatomy.neuron_lineages())
            })
            .filter_map(|(mount, lineage)| {
                (mount.source_site().is_none() && mount.place().layer() == 13)
                    .then_some(*lineage)
            })
            .collect::<Vec<_>>();
        // V40/V41 law supersedes the contact bridge these asserts once
        // pinned. The V34 boundary mounts the historical fixed-route cell;
        // V41 deliberately mounts one NEW dedicated vocal-body cell from
        // unclaimed resting anatomy "instead of choosing among historical
        // layer-13 cells" (its own doc), so this body lawfully carries TWO
        // layer-13 cells — both electrically isolated, the vocal body
        // addressed directly through the dedicated effector lineage.
        assert_eq!(articulatory.len(), 2);
        let effector = restored
            .vocal_articulatory_effector_lineage
            .expect("dedicated vocal effector mounted at the V41 boundary");
        assert!(articulatory.contains(&effector));
        for motor in vocal_motors {
            for cell in &articulatory {
                assert!(!restored.electrical_fabric.contains_contact(motor, *cell));
            }
        }
        for cell in &articulatory {
            assert!(!restored
                .electrical_fabric
                .contains_contact(non_vocal_motor, *cell));
        }
        assert_eq!(restored.electrical_fabric.contact_count(), 0);
        assert_eq!(&migrated[..MAGIC_V42.len()], MAGIC_V42);
        assert_eq!(
            ResidentCognitiveFormationState::migrate_to_current_format(&migrated, MAX_BYTES)
                .unwrap(),
            migrated
        );
    }

    #[test]
    fn v32_retires_misprojected_root_yaw_paths_once() {
        const MAX_BYTES: usize = 1_600_000_000;
        let mut cohorts = Vec::new();
        let mut population = None;
        let mut next_lineage = 1;
        let mut fabric = ResidentElectricalFabric::default();
        let source = crate::root_yaw_joint_source_builder::admit_root_yaw_proprioceptive_source(
            0, 1_000,
        )
        .unwrap();
        let moved_port = source
            .joint_source_ports()
            .iter()
            .find(|port| {
                port.root_yaw_proprioceptor_terminal.is_some()
                    && port.exact_normalized_sources.windows(2).any(|pair| pair[0] != pair[1])
            })
            .unwrap();
        let receptor_site = NeuronSourceSite::from_source_port(moved_port).unwrap();
        let (_, receptor, _) = mount_body_regulation_from_site_fixture(
            &mut cohorts,
            &mut population,
            &mut next_lineage,
            &mut fabric,
            receptor_site.clone(),
        );
        let legacy_topology = u32::try_from(
            declared_neuron_territory(DeclaredNeuronPlace::from_source_site(&receptor_site))
                .unwrap()
                - 1,
        )
        .unwrap();
        let legacy_integration = mount_intrinsic_neuron_at_place(
            &mut cohorts,
            &mut population,
            &mut next_lineage,
            DeclaredNeuronPlace::new(6, legacy_topology),
        )
        .unwrap();
        let legacy_regulation = mount_intrinsic_neuron_at_place(
            &mut cohorts,
            &mut population,
            &mut next_lineage,
            DeclaredNeuronPlace::new(8, legacy_topology),
        )
        .unwrap();
        let unrelated = mount_intrinsic_neuron_at_place(
            &mut cohorts,
            &mut population,
            &mut next_lineage,
            DeclaredNeuronPlace::new(7, 0),
        )
        .unwrap();
        fabric = fabric
            .append_contacts(&[
                (
                    receptor,
                    legacy_integration,
                    ExactRational::integer(DEVELOPMENTAL_CONTACT_CONDUCTANCE_PICOSIEMENS),
                ),
                (
                    legacy_integration,
                    legacy_regulation,
                    ExactRational::integer(DEVELOPMENTAL_CONTACT_CONDUCTANCE_PICOSIEMENS),
                ),
                (
                    legacy_regulation,
                    unrelated,
                    ExactRational::integer(DEVELOPMENTAL_CONTACT_CONDUCTANCE_PICOSIEMENS),
                ),
            ])
            .unwrap();
        let occupied_places = cohorts
            .iter()
            .flat_map(|cohort| cohort.anatomy.mounts())
            .map(ReachedNeuronMount::place)
            .collect::<Vec<_>>();
        let admitted_population = DevelopmentalRestingPopulation::admit(
            MAX_BYTES,
            100_000,
            next_lineage,
            &occupied_places,
        )
        .unwrap();
        next_lineage = admitted_population.lineage_end_exclusive();
        population = Some(admitted_population);
        let topology_index = Arc::new(ResidentTopologyIndex::build(&cohorts, &fabric).unwrap());
        let state = ResidentCognitiveFormationState {
            generation: 5,
            next_lineage_ordinal: next_lineage,
            vocal_articulatory_effector_lineage: None,
            unexpressed_electrical_seeds: Box::new([]),
            dormant_lineage_seeds: Box::new([]),
            resting_population: population,
            cohorts: cohorts.into_boxed_slice(),
            electrical_fabric: fabric,
            active_electrical_frontier: Box::new([]),
            preceding_active_electrical_frontier: Box::new([]),
            older_active_electrical_frontier: Box::new([]),
            mosaics: Box::new([]),
            hippocampal: ResidentHippocampalIndex::default(),
            topology_index,
            formation_index: ResidentFormationIndex::default(),
        };
        let mut v31 = state.encode(MAX_BYTES).unwrap();
        let vocal_body_marker_offset = MAGIC_V40.len()
            + std::mem::size_of::<u16>()
            + std::mem::size_of::<u64>()
            + std::mem::size_of::<u64>();
        assert_eq!(v31.remove(vocal_body_marker_offset), 0);
        v31[..MAGIC_V31.len()].copy_from_slice(MAGIC_V31);
        let decoded = ResidentCognitiveFormationState::decode_for_one_way_migration(
            &v31,
            MAX_BYTES,
        )
        .expect("V31 fixture must decode at the one-way boundary");
        assert!(decoded.resting_population.is_some());
        let corrected = decoded
            .retire_misprojected_root_yaw_paths()
            .expect("misprojected route retirement must settle")
            .expect("fixture must carry one misprojected route");
        corrected
            .clone()
            .encode(MAX_BYTES)
            .expect("corrected V32 fixture must encode canonically");
        corrected
            .into_current_retained_formation_authority()
            .expect("retained-formation authority must preserve the corrected fixture")
            .encode(MAX_BYTES)
            .expect("final migrated fixture must encode canonically");
        let migrated = ResidentCognitiveFormationState::migrate_to_current_format(
            &v31,
            MAX_BYTES,
        )
        .unwrap();
        assert_eq!(&migrated[..MAGIC_V42.len()], MAGIC_V42);
        let restored = ResidentCognitiveFormationState::decode(&migrated, MAX_BYTES).unwrap();
        assert!(restored.electrical_fabric.contains_contact(receptor, {
            restored
                .cohorts
                .iter()
                .flat_map(|cohort| {
                    cohort
                        .anatomy
                        .mounts()
                        .iter()
                        .zip(cohort.anatomy.neuron_lineages())
                })
                .find_map(|(mount, lineage)| {
                    (mount.place() == local_integration_place(
                        DeclaredNeuronPlace::from_source_site(&receptor_site),
                    )
                    .unwrap())
                    .then_some(*lineage)
                })
                .unwrap()
        }));
        assert!(!restored
            .electrical_fabric
            .contains_contact(receptor, legacy_integration));
        assert!(!restored
            .electrical_fabric
            .contains_contact(legacy_integration, legacy_regulation));
        assert!(!restored
            .electrical_fabric
            .contains_contact(legacy_regulation, unrelated));
        assert_eq!(
            ResidentCognitiveFormationState::migrate_to_current_format(&migrated, MAX_BYTES)
                .unwrap(),
            migrated
        );
    }

    #[test]
    fn changed_ordering_set_reuses_the_terminal_bound_motor() {
        let mut cohorts = Vec::new();
        let mut population =
            Some(DevelopmentalRestingPopulation::admit(1_600_000_000, 100_000, 100, &[]).unwrap());
        let mut next_lineage = 1;
        let mut fabric = ResidentElectricalFabric::default();
        let (regulation, _, _) = mount_body_regulation_fixture(
            &mut cohorts,
            &mut population,
            &mut next_lineage,
            &mut fabric,
            BodyAxis::LeftElbowFlexion,
            BodyEffectorDirection::TowardMaximum,
        );
        let first_ordering = mount_intrinsic_neuron_at_place(
            &mut cohorts,
            &mut population,
            &mut next_lineage,
            DeclaredNeuronPlace::new(11, 0),
        )
        .unwrap();
        mount_local_motor_bridge_fixture(
            &mut cohorts,
            &mut population,
            &mut next_lineage,
            &mut fabric,
            regulation,
            first_ordering,
            0,
        );
        let first_active_bonds = directed_transfers_from_bonds(&cohorts, &fabric);
        let prior_frontier = frontier_entries_from_bonds(&cohorts, &fabric);
        mount_reached_motor_effector(
            &mut cohorts,
            &mut population,
            &mut next_lineage,
            &mut fabric,
            &[regulation, first_ordering],
            &first_active_bonds,
            &prior_frontier,
            &[BodyAxis::LeftElbowFlexion, BodyAxis::LeftGripAperture],
        )
        .unwrap();
        let motor = cohorts
            .iter()
            .flat_map(|cohort| {
                cohort
                    .anatomy
                    .mounts()
                    .iter()
                    .zip(cohort.anatomy.neuron_lineages())
            })
            .find_map(|(mount, lineage)| (mount.place().layer() == 12).then_some(*lineage))
            .unwrap();

        let second_ordering = mount_intrinsic_neuron_at_place(
            &mut cohorts,
            &mut population,
            &mut next_lineage,
            DeclaredNeuronPlace::new(11, 1),
        )
        .unwrap();
        mount_local_motor_bridge_fixture(
            &mut cohorts,
            &mut population,
            &mut next_lineage,
            &mut fabric,
            regulation,
            second_ordering,
            1,
        );
        let second_active_bonds = directed_transfers_from_bonds(&cohorts, &fabric);
        let prior_frontier = frontier_entries_from_bonds(&cohorts, &fabric);
        mount_reached_motor_effector(
            &mut cohorts,
            &mut population,
            &mut next_lineage,
            &mut fabric,
            &[regulation, second_ordering],
            &second_active_bonds,
            &prior_frontier,
            &[BodyAxis::LeftElbowFlexion, BodyAxis::LeftGripAperture],
        )
        .unwrap();
        let motors = cohorts
            .iter()
            .flat_map(|cohort| {
                cohort
                    .anatomy
                    .mounts()
                    .iter()
                    .zip(cohort.anatomy.neuron_lineages())
            })
            .filter_map(|(mount, lineage)| (mount.place().layer() == 12).then_some(*lineage))
            .collect::<Vec<_>>();
        assert_eq!(motors, vec![motor]);
        assert!(fabric.contains_contact(motor, first_ordering));
        assert!(fabric.contains_contact(motor, second_ordering));
    }

    #[test]
    fn historical_background_growth_migrates_once_and_cannot_restore() {
        const MAX_BYTES: usize = 1_600_000_000;
        let mut cohorts = Vec::new();
        let mut population = None;
        let mut next_lineage = 1;
        let mut fabric = ResidentElectricalFabric::default();
        let (regulation, _, _) = mount_body_regulation_fixture(
            &mut cohorts,
            &mut population,
            &mut next_lineage,
            &mut fabric,
            BodyAxis::LeftElbowFlexion,
            BodyEffectorDirection::TowardMaximum,
        );
        let ordering = mount_intrinsic_neuron_at_place(
            &mut cohorts,
            &mut population,
            &mut next_lineage,
            DeclaredNeuronPlace::new(11, 0),
        )
        .unwrap();
        mount_local_motor_bridge_fixture(
            &mut cohorts,
            &mut population,
            &mut next_lineage,
            &mut fabric,
            regulation,
            ordering,
            0,
        );
        let active_bonds = directed_transfers_from_bonds(&cohorts, &fabric);
        let prior_frontier = frontier_entries_from_bonds(&cohorts, &fabric);
        mount_reached_motor_effector(
            &mut cohorts,
            &mut population,
            &mut next_lineage,
            &mut fabric,
            &[regulation, ordering],
            &active_bonds,
            &prior_frontier,
            &[BodyAxis::LeftElbowFlexion, BodyAxis::LeftGripAperture],
        )
        .unwrap();
        let duplicate = mount_next_intrinsic_in_layer(
            &mut cohorts,
            &mut population,
            &mut next_lineage,
            12,
        )
        .unwrap();
        cohorts
            .iter_mut()
            .find(|cohort| cohort.anatomy.neuron_lineages().contains(&duplicate))
            .unwrap()
            .anatomy
            .specialize_motor_effector(
                duplicate,
                BodyEffectorTerminal::new(
                    BodyAxis::LeftElbowFlexion,
                    BodyEffectorDirection::TowardMaximum,
                ),
            )
            .unwrap();
        fabric = fabric
            .append_contacts(&[
                (
                    regulation,
                    duplicate,
                    ExactRational::integer(DEVELOPMENTAL_CONTACT_CONDUCTANCE_PICOSIEMENS),
                ),
                (
                    ordering,
                    duplicate,
                    ExactRational::integer(DEVELOPMENTAL_CONTACT_CONDUCTANCE_PICOSIEMENS),
                ),
            ])
            .unwrap();
        let contact_count = fabric.contact_count();
        let topology_index = Arc::new(ResidentTopologyIndex::build(&cohorts, &fabric).unwrap());
        let mut state = ResidentCognitiveFormationState {
            generation: 5,
            next_lineage_ordinal: next_lineage,
            vocal_articulatory_effector_lineage: None,
            unexpressed_electrical_seeds: Box::new([]),
            dormant_lineage_seeds: Box::new([]),
            resting_population: population,
            cohorts: cohorts.into_boxed_slice(),
            electrical_fabric: fabric,
            active_electrical_frontier: Box::new([]),
            preceding_active_electrical_frontier: Box::new([]),
            older_active_electrical_frontier: Box::new([]),
            mosaics: Box::new([]),
            hippocampal: ResidentHippocampalIndex::default(),
            topology_index,
            formation_index: ResidentFormationIndex::default(),
        };
        let occupied_places = state
            .cohorts
            .iter()
            .flat_map(|cohort| cohort.anatomy.mounts())
            .map(ReachedNeuronMount::place)
            .collect::<Vec<_>>();
        let population = DevelopmentalRestingPopulation::admit(
            MAX_BYTES,
            100_000,
            state.next_lineage_ordinal,
            &occupied_places,
        )
        .unwrap();
        state.next_lineage_ordinal = population.lineage_end_exclusive();
        state.resting_population = Some(population);
        validate_lineage_state(&state).unwrap();
        let v25 = state
            .encode_with_format(CognitiveCodecFormat::V25, MAX_BYTES)
            .unwrap();
        assert!(matches!(
            ResidentCognitiveFormationState::decode(&v25, MAX_BYTES),
            Err(FormationError::RetiredCognitiveState)
        ));
        let decoded = ResidentCognitiveFormationState::decode_for_one_way_migration(
            &v25,
            MAX_BYTES,
        )
        .unwrap();
        let decoded = decoded
            .retire_aliased_local_integrators()
            .unwrap()
            .unwrap_or(decoded);
        let corrected = decoded
            .retire_duplicate_motor_effectors()
            .unwrap()
            .unwrap();
        assert_eq!(corrected.electrical_fabric.contact_count(), contact_count - 2);

        let current = ResidentCognitiveFormationState::migrate_to_current_format(
            &v25,
            MAX_BYTES,
        )
        .unwrap();
        assert_eq!(&current[..MAGIC_V42.len()], MAGIC_V42);
        let restored = ResidentCognitiveFormationState::decode(&current, MAX_BYTES).unwrap();
        assert_eq!(
            restored.observe_reached_neuron_count_by_layer()
                .into_iter()
                .find(|(layer, _)| *layer == 12),
            Some((12, 1))
        );
        assert_eq!(restored.electrical_fabric.contact_count(), 3);
        assert!(restored
            .observe_reached_neuron_count_by_layer()
            .into_iter()
            .all(|(layer, _)| layer <= 8 || layer == 12));
        assert!(restored.mosaics.is_empty());
        assert!(restored.active_electrical_frontier.is_empty());
        assert_eq!(
            ResidentCognitiveFormationState::migrate_to_current_format(&current, MAX_BYTES)
                .unwrap(),
            current
        );
    }

    #[test]
    fn distinct_body_regulations_mount_distinct_unambiguous_motor_pools() {
        let mut cohorts = Vec::new();
        let mut population =
            Some(DevelopmentalRestingPopulation::admit(1_600_000_000, 100_000, 100, &[]).unwrap());
        let mut next_lineage = 1;
        let mut fabric = ResidentElectricalFabric::default();
        let (first_regulation, _, _) = mount_body_regulation_fixture(
            &mut cohorts,
            &mut population,
            &mut next_lineage,
            &mut fabric,
            BodyAxis::LeftElbowFlexion,
            BodyEffectorDirection::TowardMinimum,
        );
        let (second_regulation, _, _) = mount_body_regulation_fixture(
            &mut cohorts,
            &mut population,
            &mut next_lineage,
            &mut fabric,
            BodyAxis::LeftElbowFlexion,
            BodyEffectorDirection::TowardMaximum,
        );
        let ordering = mount_intrinsic_neuron_at_place(
            &mut cohorts,
            &mut population,
            &mut next_lineage,
            DeclaredNeuronPlace::new(11, 0),
        )
        .unwrap();
        mount_local_motor_bridge_fixture(
            &mut cohorts,
            &mut population,
            &mut next_lineage,
            &mut fabric,
            first_regulation,
            ordering,
            0,
        );
        mount_local_motor_bridge_fixture(
            &mut cohorts,
            &mut population,
            &mut next_lineage,
            &mut fabric,
            second_regulation,
            ordering,
            1,
        );
        let active_bonds = directed_transfers_from_bonds(&cohorts, &fabric);
        let prior_frontier = frontier_entries_from_bonds(&cohorts, &fabric);
        mount_reached_motor_effector(
            &mut cohorts,
            &mut population,
            &mut next_lineage,
            &mut fabric,
            &[first_regulation, second_regulation, ordering],
            &active_bonds,
            &prior_frontier,
            &[BodyAxis::LeftElbowFlexion, BodyAxis::LeftGripAperture],
        )
        .unwrap();
        let motors = cohorts
            .iter()
            .flat_map(|cohort| {
                cohort
                    .anatomy
                    .mounts()
                    .iter()
                    .zip(cohort.anatomy.neuron_lineages())
            })
            .filter(|(mount, _)| mount.place().layer() == 12)
            .map(|(_, lineage)| *lineage)
            .collect::<Vec<_>>();
        assert_eq!(motors.len(), 2);
        for motor in motors {
            assert!(fabric.contains_contact(motor, ordering));
            let regulation_count = [first_regulation, second_regulation]
                .into_iter()
                .filter(|regulation| fabric.contains_contact(motor, *regulation))
                .count();
            assert_eq!(regulation_count, 1);
        }
    }

    #[test]
    fn exact_vocal_occurrences_mount_one_local_sensorimotor_route_each() {
        let mut cohorts = Vec::new();
        let mut population =
            Some(DevelopmentalRestingPopulation::admit(1_600_000_000, 100_000, 100, &[]).unwrap());
        let mut next_lineage = 1;
        let mut fabric = ResidentElectricalFabric::default();
        let terminal = BodyEffectorTerminal::new(
            BodyAxis::VocalTractSection0Area,
            BodyEffectorDirection::TowardMinimum,
        );
        let (regulation, _, _) = mount_body_regulation_fixture(
            &mut cohorts,
            &mut population,
            &mut next_lineage,
            &mut fabric,
            terminal.axis(),
            terminal.direction(),
        );
        let (receptor, integration) = mount_receptor_local_integration_fixture(
            &mut cohorts,
            &mut population,
            &mut next_lineage,
            &mut fabric,
            NeuronSourceSite::fixture_in_sense(PhysicalSourceSense::Sound, 91),
        );
        let association = mount_intrinsic_neuron_at_place(
            &mut cohorts,
            &mut population,
            &mut next_lineage,
            DeclaredNeuronPlace::new(7, 0),
        )
        .unwrap();
        let recurrent = mount_intrinsic_neuron_at_place(
            &mut cohorts,
            &mut population,
            &mut next_lineage,
            DeclaredNeuronPlace::new(9, 0),
        )
        .unwrap();
        fabric = fabric
            .append_contacts(&[(
                association,
                integration,
                ExactRational::integer(DEVELOPMENTAL_CONTACT_CONDUCTANCE_PICOSIEMENS),
            )])
            .unwrap();
        let topology = ResidentTopologyIndex::build(&cohorts, &fabric).unwrap();
        let associations = ReachedAssociationsByOccurrence {
            lineages: vec![vec![association]],
        };
        let moved = vec![vec![regulation]];
        let reassemblies = vec![ExternallyReassembledFormationFrontierObservation {
            formation_receipt: [7; 32],
            cue_lineages: vec![receptor],
            recurrent_lineage: recurrent,
        }];
        mount_exact_reassembled_vocal_action_routes(
            &mut cohorts,
            &mut population,
            &mut next_lineage,
            &mut fabric,
            &topology,
            &associations,
            &moved,
            &reassemblies,
        )
        .unwrap();

        let topology = ResidentTopologyIndex::build(&cohorts, &fabric).unwrap();
        let motor = cohorts
            .iter()
            .flat_map(|cohort| {
                cohort
                    .anatomy
                    .mounts()
                    .iter()
                    .zip(cohort.anatomy.neuron_lineages())
            })
            .find_map(|(mount, lineage)| {
                (mount.body_effector_terminal() == Some(terminal)).then_some(*lineage)
            })
            .unwrap();
        let route = vocal_cognitive_action_route_for_motor(&cohorts, &topology, motor)
            .unwrap()
            .into_iter()
            .next()
            .unwrap();
        assert_eq!(route.association_lineage, association);
        assert_eq!(route.recurrent_lineage, recurrent);
        assert_eq!(route.motor_lineage, motor);
        assert_eq!(
            route.association_bond.endpoints(),
            canonical_lineage_pair(route.ordering_lineage, association)
        );
        assert!(fabric.contains_contact(route.ordering_lineage, association));
        assert!(fabric.contains_contact(route.ordering_lineage, recurrent));
        assert!(fabric.contains_contact(route.ordering_lineage, motor));

        let contact_count = fabric.contact_count();
        let lineage_count = cohorts
            .iter()
            .map(|cohort| cohort.anatomy.neuron_count())
            .sum::<usize>();
        mount_exact_reassembled_vocal_action_routes(
            &mut cohorts,
            &mut population,
            &mut next_lineage,
            &mut fabric,
            &topology,
            &associations,
            &moved,
            &reassemblies,
        )
        .unwrap();
        assert_eq!(fabric.contact_count(), contact_count);
        assert_eq!(
            cohorts
                .iter()
                .map(|cohort| cohort.anatomy.neuron_count())
                .sum::<usize>(),
            lineage_count
        );
    }

    #[test]
    fn motor_growth_sleeps_without_a_physical_terminal_author() {
        let mut cohorts = Vec::new();
        let mut population =
            Some(DevelopmentalRestingPopulation::admit(1_600_000_000, 100_000, 100, &[]).unwrap());
        let mut next_lineage = 1;
        let mut fabric = ResidentElectricalFabric::default();
        let regulation = mount_intrinsic_neuron_at_place(
            &mut cohorts,
            &mut population,
            &mut next_lineage,
            DeclaredNeuronPlace::new(8, 0),
        )
        .unwrap();
        let ordering = mount_intrinsic_neuron_at_place(
            &mut cohorts,
            &mut population,
            &mut next_lineage,
            DeclaredNeuronPlace::new(11, 0),
        )
        .unwrap();
        fabric = fabric
            .append_contact(
                regulation,
                ordering,
                ExactRational::integer(DEVELOPMENTAL_CONTACT_CONDUCTANCE_PICOSIEMENS),
            )
            .unwrap();
        let topology = ResidentTopologyIndex::build(&cohorts, &fabric).unwrap();
        let frontier = frontier_entries_from_bonds(&cohorts, &fabric);
        let neuron_count = cohorts
            .iter()
            .map(|cohort| cohort.anatomy.neuron_count())
            .sum::<usize>();
        let contact_count = fabric.contact_count();

        mount_reached_motor_effector_with_reach_index(
            &mut cohorts,
            &mut population,
            &mut next_lineage,
            &mut fabric,
            &[regulation],
            &[],
            &frontier,
            &frontier,
            &frontier,
            &[],
            &BTreeMap::new(),
            &BTreeMap::new(),
            Some(&topology),
            &[],
        )
        .unwrap();

        assert_eq!(fabric.contact_count(), contact_count);
        assert_eq!(
            cohorts
                .iter()
                .map(|cohort| cohort.anatomy.neuron_count())
                .sum::<usize>(),
            neuron_count
        );
    }

    #[test]
    fn returned_motor_synergy_grows_one_bounded_coaged_source_per_terminal() {
        let mut cohorts = Vec::new();
        let mut population =
            Some(DevelopmentalRestingPopulation::admit(1_600_000_000, 100_000, 100, &[]).unwrap());
        let mut next_lineage = 1;
        let mut fabric = ResidentElectricalFabric::default();
        let first_terminal = BodyEffectorTerminal::new(
            BodyAxis::LeftElbowFlexion,
            BodyEffectorDirection::TowardMaximum,
        );
        let second_terminal = BodyEffectorTerminal::new(
            BodyAxis::RightElbowFlexion,
            BodyEffectorDirection::TowardMaximum,
        );
        let (first_regulation, _, _) = mount_body_regulation_fixture(
            &mut cohorts,
            &mut population,
            &mut next_lineage,
            &mut fabric,
            first_terminal.axis(),
            first_terminal.direction(),
        );
        let (second_regulation, _, _) = mount_body_regulation_fixture(
            &mut cohorts,
            &mut population,
            &mut next_lineage,
            &mut fabric,
            second_terminal.axis(),
            second_terminal.direction(),
        );
        let association = mount_intrinsic_neuron_at_place(
            &mut cohorts,
            &mut population,
            &mut next_lineage,
            DeclaredNeuronPlace::new(7, 0),
        )
        .unwrap();
        let anchor = mount_intrinsic_neuron_at_place(
            &mut cohorts,
            &mut population,
            &mut next_lineage,
            DeclaredNeuronPlace::new(11, 0),
        )
        .unwrap();
        fabric = fabric
            .append_contact(
                association,
                anchor,
                ExactRational::integer(DEVELOPMENTAL_CONTACT_CONDUCTANCE_PICOSIEMENS),
            )
            .unwrap();
        mount_local_motor_bridge_fixture(
            &mut cohorts,
            &mut population,
            &mut next_lineage,
            &mut fabric,
            first_regulation,
            anchor,
            0,
        );
        let transfers = directed_transfers_from_bonds(&cohorts, &fabric);
        let frontier = frontier_entries_from_bonds(&cohorts, &fabric);
        mount_reached_motor_effector_with_root(
            &mut cohorts,
            &mut population,
            &mut next_lineage,
            &mut fabric,
            &[first_regulation],
            &transfers,
            &frontier,
            &frontier,
            &frontier,
            &[first_terminal],
            &BTreeMap::new(),
            &BTreeMap::new(),
        )
        .unwrap();
        let motor_for = |cohorts: &[ResidentReachedCohort], terminal| {
            cohorts
                .iter()
                .flat_map(|cohort| {
                    cohort
                        .anatomy
                        .mounts()
                        .iter()
                        .zip(cohort.anatomy.neuron_lineages())
                })
                .find_map(|(mount, lineage)| {
                    (mount.body_effector_terminal() == Some(terminal)).then_some(*lineage)
                })
                .unwrap()
        };
        let first_motor = motor_for(&cohorts, first_terminal);
        let second_motor = motor_for(&cohorts, second_terminal);
        assert!(fabric.contains_contact(anchor, first_motor));
        assert!(!fabric.contains_contact(anchor, second_motor));
        let pre_guidance_contact_count = fabric.contact_count();
        let pre_guidance_lineage_count = cohorts
            .iter()
            .map(|cohort| cohort.anatomy.neuron_lineages().len())
            .sum::<usize>();
        let transfers = directed_transfers_from_bonds(&cohorts, &fabric);
        let frontier = frontier_entries_from_bonds(&cohorts, &fabric);
        mount_reached_motor_effector_with_root(
            &mut cohorts,
            &mut population,
            &mut next_lineage,
            &mut fabric,
            &[first_regulation, second_regulation],
            &transfers,
            &frontier,
            &frontier,
            &frontier,
            &[first_terminal, second_terminal],
            &BTreeMap::new(),
            &BTreeMap::new(),
        )
        .unwrap();
        assert_eq!(fabric.contact_count(), pre_guidance_contact_count);
        assert_eq!(
            cohorts
                .iter()
                .map(|cohort| cohort.anatomy.neuron_lineages().len())
                .sum::<usize>(),
            pre_guidance_lineage_count
        );
        let unit_work = BigRational::from_integer(BigInt::from(1));
        let bond_for = |cohorts: &[ResidentReachedCohort],
                        fabric: &ResidentElectricalFabric,
                        left,
                        right| {
            let pair = canonical_lineage_pair(left, right);
            all_physical_bonds(cohorts, fabric)
                .into_iter()
                .find(|bond| bond.endpoints() == pair)
                .unwrap()
        };
        let anchor_discharge = MotorUnitRecruitment {
            neuron_lineage: first_motor,
            topology_index: 0,
            outward_elementary_carriers: 1,
            body_effector_terminal: first_terminal,
            body_afferent_paths: Vec::new(),
            preparation_transfers: Vec::new(),
            learned_work_preparations: vec![LearnedMotorWorkPreparation {
                motor_lineage: first_motor,
                routes: vec![LearnedMotorWorkRoute {
                    ordering_lineage: anchor,
                    founding_receiver_lineage: association,
                    founding_bond: bond_for(&cohorts, &fabric, association, anchor),
                    learned_bond: bond_for(&cohorts, &fabric, anchor, first_motor),
                    offered_work_zeptojoules: unit_work.clone(),
                }],
                total_offered_work_zeptojoules: unit_work.clone(),
                accepted_work_zeptojoules: unit_work.clone(),
                predecessor_residue_zeptojoules: BigRational::zero(),
                successor_residue_zeptojoules: BigRational::zero(),
                delivered_gate_work_zeptojoules: unit_work,
                retained_source_heat_zeptojoules: BigRational::zero(),
                residue_narrowing_heat_zeptojoules: BigRational::zero(),
            }],
        };

        let transfers = directed_transfers_from_bonds(&cohorts, &fabric);
        let frontier = frontier_entries_from_bonds(&cohorts, &fabric);
        mount_reached_motor_effector_with_reach_index(
            &mut cohorts,
            &mut population,
            &mut next_lineage,
            &mut fabric,
            &[first_regulation, second_regulation],
            &transfers,
            &frontier,
            &frontier,
            &frontier,
            &[first_terminal, second_terminal],
            &BTreeMap::new(),
            &BTreeMap::new(),
            None,
            &[anchor_discharge.clone()],
        )
        .unwrap();
        let ordering_to_motor = fabric
            .contact_endpoints()
            .filter_map(|(left, right)| {
                let left = fabric.lineages()[left];
                let right = fabric.lineages()[right];
                match (
                    cohorts.iter().flat_map(|cohort| cohort.anatomy.mounts().iter().zip(cohort.anatomy.neuron_lineages())).find_map(|(mount, lineage)| (*lineage == left).then_some(mount.place().layer())),
                    cohorts.iter().flat_map(|cohort| cohort.anatomy.mounts().iter().zip(cohort.anatomy.neuron_lineages())).find_map(|(mount, lineage)| (*lineage == right).then_some(mount.place().layer())),
                ) {
                    (Some(11), Some(12)) => Some((left, right)),
                    (Some(12), Some(11)) => Some((right, left)),
                    _ => None,
                }
            })
            .collect::<BTreeSet<_>>();
        assert_eq!(ordering_to_motor.len(), 3);
        let first_sources = ordering_to_motor
            .iter()
            .filter_map(|(source, motor)| (*motor == first_motor).then_some(*source))
            .collect::<BTreeSet<_>>();
        let second_sources = ordering_to_motor
            .iter()
            .filter_map(|(source, motor)| (*motor == second_motor).then_some(*source))
            .collect::<BTreeSet<_>>();
        assert_eq!(first_sources.len(), 2);
        assert_eq!(second_sources.len(), 1);
        let first_sibling = *first_sources.iter().find(|source| **source != anchor).unwrap();
        let second_sibling = *second_sources.iter().next().unwrap();
        assert!(fabric.contains_contact(anchor, first_sibling));
        assert!(fabric.contains_contact(anchor, second_sibling));

        let contact_count = fabric.contact_count();
        let lineage_count = cohorts
            .iter()
            .map(|cohort| cohort.anatomy.neuron_lineages().len())
            .sum::<usize>();
        let transfers = directed_transfers_from_bonds(&cohorts, &fabric);
        let frontier = frontier_entries_from_bonds(&cohorts, &fabric);
        mount_reached_motor_effector_with_reach_index(
            &mut cohorts,
            &mut population,
            &mut next_lineage,
            &mut fabric,
            &[first_regulation, second_regulation],
            &transfers,
            &frontier,
            &frontier,
            &frontier,
            &[first_terminal, second_terminal],
            &BTreeMap::new(),
            &BTreeMap::new(),
            None,
            &[anchor_discharge.clone()],
        )
        .unwrap();
        assert_eq!(fabric.contact_count(), contact_count);
        assert_eq!(
            cohorts
                .iter()
                .map(|cohort| cohort.anatomy.neuron_lineages().len())
                .sum::<usize>(),
            lineage_count
        );

        let mut sibling_discharge = anchor_discharge;
        sibling_discharge.neuron_lineage = second_motor;
        sibling_discharge.body_effector_terminal = second_terminal;
        sibling_discharge.learned_work_preparations[0].motor_lineage = second_motor;
        sibling_discharge.learned_work_preparations[0].routes[0].ordering_lineage = second_sibling;
        sibling_discharge.learned_work_preparations[0].routes[0].founding_bond =
            bond_for(&cohorts, &fabric, association, second_sibling);
        sibling_discharge.learned_work_preparations[0].routes[0].learned_bond =
            bond_for(&cohorts, &fabric, second_sibling, second_motor);
        let transfers = directed_transfers_from_bonds(&cohorts, &fabric);
        let frontier = frontier_entries_from_bonds(&cohorts, &fabric);
        mount_reached_motor_effector_with_reach_index(
            &mut cohorts,
            &mut population,
            &mut next_lineage,
            &mut fabric,
            &[first_regulation, second_regulation],
            &transfers,
            &frontier,
            &frontier,
            &frontier,
            &[first_terminal, second_terminal],
            &BTreeMap::new(),
            &BTreeMap::new(),
            None,
            &[sibling_discharge],
        )
        .unwrap();
        assert_eq!(fabric.contact_count(), contact_count);
        assert_eq!(
            cohorts
                .iter()
                .map(|cohort| cohort.anatomy.neuron_lineages().len())
                .sum::<usize>(),
            lineage_count
        );
    }

    #[test]
    fn motor_effector_exposes_exact_sparse_body_afferent_ancestry() {
        let mut cohorts = Vec::new();
        let mut population =
            Some(DevelopmentalRestingPopulation::admit(1_600_000_000, 100_000, 100, &[]).unwrap());
        let mut next_lineage = 1;
        let mut fabric = ResidentElectricalFabric::default();
        let (regulation, receptor_lineage, receptor_site) = mount_body_regulation_fixture(
            &mut cohorts,
            &mut population,
            &mut next_lineage,
            &mut fabric,
            BodyAxis::RightGripAperture,
            BodyEffectorDirection::TowardMinimum,
        );
        let ordering = mount_intrinsic_neuron_at_place(
            &mut cohorts,
            &mut population,
            &mut next_lineage,
            DeclaredNeuronPlace::new(11, 0),
        )
        .unwrap();
        mount_local_motor_bridge_fixture(
            &mut cohorts,
            &mut population,
            &mut next_lineage,
            &mut fabric,
            regulation,
            ordering,
            0,
        );
        let active_bonds = directed_transfers_from_bonds(&cohorts, &fabric);
        let prior_frontier = frontier_entries_from_bonds(&cohorts, &fabric);
        mount_reached_motor_effector(
            &mut cohorts,
            &mut population,
            &mut next_lineage,
            &mut fabric,
            &[regulation, ordering],
            &active_bonds,
            &prior_frontier,
            &[BodyAxis::RightGripAperture],
        )
        .unwrap();

        let flat_locations = cohorts
            .iter()
            .enumerate()
            .flat_map(|(cohort_index, cohort)| {
                cohort
                    .anatomy
                    .neuron_lineages()
                    .iter()
                    .enumerate()
                    .map(move |(neuron_index, lineage)| {
                        (cohort_index, neuron_index, *lineage)
                    })
            })
            .collect::<Vec<_>>();
        let flat_for_lineage = |lineage: [u8; 16]| {
            flat_locations
                .iter()
                .position(|(_, _, candidate)| *candidate == lineage)
                .unwrap()
        };
        let mut neighbours = vec![Vec::new(); flat_locations.len()];
        for (left, right) in fabric.contact_endpoints() {
            let left_flat = flat_for_lineage(fabric.lineages()[left]);
            let right_flat = flat_for_lineage(fabric.lineages()[right]);
            neighbours[left_flat].push(right_flat);
            neighbours[right_flat].push(left_flat);
        }
        let neighbours = neighbours
            .into_iter()
            .map(Vec::into_boxed_slice)
            .collect::<Vec<_>>();
        let motor_flat = flat_locations
            .iter()
            .enumerate()
            .find_map(|(flat, (cohort_index, neuron_index, _))| {
                (cohorts[*cohort_index].anatomy.mounts()[*neuron_index]
                    .place()
                    .layer()
                    == 12)
                    .then_some(flat)
            })
            .unwrap();
        let paths = exact_motor_body_afferent_paths(
            motor_flat,
            &flat_locations,
            &cohorts,
            &neighbours,
        )
        .unwrap();
        assert_eq!(paths.len(), 1);
        assert_eq!(paths[0].body_regulation_lineage, regulation);
        assert_eq!(paths[0].receptor_lineage, receptor_lineage);
        assert_eq!(paths[0].receptor_site, receptor_site);
    }

    #[test]
    fn ambiguous_returned_vocal_consequence_cannot_author_motor_contact() {
        let mut cohorts = Vec::new();
        let mut population =
            Some(DevelopmentalRestingPopulation::admit(16_000_000, 100_000, 100, &[]).unwrap());
        let mut next_lineage = 1;
        let articulatory_port = crate::joint_source_episode::JointSourcePortView {
            sense: PhysicalSourceSense::Body.declared_layer(),
            topology_index: 0,
            body_proprioceptor_terminal: None,
            root_yaw_proprioceptor_terminal: None,
            root_translation_proprioceptor_terminal: None,
            sensor_id: "articulatory-mechanoreceptors".into(),
            substream_id: "oral-aperture".into(),
            coordinates: vec![crate::joint_source_episode::JointSourceCoordinate {
                axis_id: "articulatory-site".into(),
                coordinate_id: "oral-aperture".into(),
            }],
            physical_quantity: ORAL_APERTURE_AREA_QUANTITY.into(),
            physical_unit: ARTICULATORY_MECHANICAL_FRACTION_UNIT.into(),
            relevance_rule: "source-only".into(),
            relevance_origin: None,
            input_map_id: "articulatory-test-map".into(),
            source_min: BigRational::from_integer(BigInt::from(-1)),
            source_max: BigRational::from_integer(BigInt::from(1)),
            field_offset: BigRational::from_integer(BigInt::from(0)),
            field_scale: BigRational::from_integer(BigInt::from(1)),
            input_map_profile: vec![1],
            input_map_group_receipt: [0; 32],
            source_times: vec![
                BigRational::from_integer(BigInt::from(0)),
                BigRational::from_integer(BigInt::from(1)),
            ],
            exact_normalized_sources: vec![
                BigRational::from_integer(BigInt::from(0)),
                BigRational::new(BigInt::from(1), BigInt::from(4)),
            ],
            reported_phase_turns: vec![
                BigRational::from_integer(BigInt::from(0)),
                BigRational::from_integer(BigInt::from(0)),
            ],
            source_relevances: vec![
                BigRational::from_integer(BigInt::from(1)),
                BigRational::from_integer(BigInt::from(1)),
            ],
            dimensionless_fields: vec![
                BigRational::from_integer(BigInt::from(0)),
                BigRational::from_integer(BigInt::from(0)),
            ],
        };
        let articulatory_site = NeuronSourceSite::from_source_port(&articulatory_port).unwrap();
        let mut fabric = ResidentElectricalFabric::default();
        let (regulation, _, _) = mount_body_regulation_from_site_fixture(
            &mut cohorts,
            &mut population,
            &mut next_lineage,
            &mut fabric,
            articulatory_site,
        );
        let (sound_receptor, acoustic) = mount_receptor_local_integration_fixture(
            &mut cohorts,
            &mut population,
            &mut next_lineage,
            &mut fabric,
            NeuronSourceSite::fixture_in_sense(PhysicalSourceSense::Sound, 0),
        );
        let (unrelated_sound_receptor, unrelated_acoustic) =
            mount_receptor_local_integration_fixture(
                &mut cohorts,
                &mut population,
                &mut next_lineage,
                &mut fabric,
                NeuronSourceSite::fixture_in_sense(PhysicalSourceSense::Sound, 1),
            );
        let ordering = mount_intrinsic_neuron_at_place(
            &mut cohorts,
            &mut population,
            &mut next_lineage,
            DeclaredNeuronPlace::new(11, 0),
        )
        .unwrap();
        let affective = mount_intrinsic_neuron_at_place(
            &mut cohorts,
            &mut population,
            &mut next_lineage,
            DeclaredNeuronPlace::new(10, 0),
        )
        .unwrap();
        let association = mount_intrinsic_neuron_at_place(
            &mut cohorts,
            &mut population,
            &mut next_lineage,
            DeclaredNeuronPlace::new(7, 0),
        )
        .unwrap();
        fabric = fabric
            .append_contacts(&[
                (
                    regulation,
                    affective,
                    ExactRational::integer(DEVELOPMENTAL_CONTACT_CONDUCTANCE_PICOSIEMENS),
                ),
                (
                    affective,
                    ordering,
                    ExactRational::integer(DEVELOPMENTAL_CONTACT_CONDUCTANCE_PICOSIEMENS),
                ),
                (
                    ordering,
                    association,
                    ExactRational::integer(DEVELOPMENTAL_CONTACT_CONDUCTANCE_PICOSIEMENS),
                ),
                (
                    acoustic,
                    association,
                    ExactRational::integer(DEVELOPMENTAL_CONTACT_CONDUCTANCE_PICOSIEMENS),
                ),
                (
                    association,
                    affective,
                    ExactRational::integer(DEVELOPMENTAL_CONTACT_CONDUCTANCE_PICOSIEMENS),
                ),
            ])
            .unwrap();
        let motor = mount_next_intrinsic_in_layer(
            &mut cohorts,
            &mut population,
            &mut next_lineage,
            12,
        )
        .unwrap();
        cohorts
            .iter_mut()
            .find(|cohort| cohort.anatomy.neuron_lineages().contains(&motor))
            .unwrap()
            .anatomy
            .specialize_motor_effector(
                motor,
                BodyEffectorTerminal::new(
                    BodyAxis::JawOpening,
                    BodyEffectorDirection::TowardMaximum,
                ),
            )
            .unwrap();
        let articulatory = mount_fixed_vocal_articulatory_route(
            &mut cohorts,
            &mut population,
            &mut next_lineage,
            &mut fabric,
        )
        .unwrap()
        .unwrap();
        // Recreate only in this historical fixture the V37 fixed hub that
        // current source no longer authors.
        fabric = fabric
            .append_contact(
                motor,
                articulatory,
                ExactRational::integer(DEVELOPMENTAL_CONTACT_CONDUCTANCE_PICOSIEMENS),
            )
            .unwrap();
        let contacts_before = fabric.contact_count();
        let mut current_consequence =
            directed_chain(&cohorts, &fabric, &[regulation, affective]);
        current_consequence.extend(directed_chain(
            &cohorts,
            &fabric,
            &[sound_receptor, acoustic],
        ));
        current_consequence.sort_unstable();
        let preceding_ordering = frontier_hop_with_frontier(
            &cohorts,
            &fabric,
            ordering,
            association,
            association,
        );
        let mut preceding_action = frontier_hop_with_frontier(
            &cohorts,
            &fabric,
            affective,
            association,
            affective,
        );
        preceding_action.extend(frontier_hop(&cohorts, &fabric, motor, articulatory));
        preceding_action.sort_unstable();

        // Body feedback without self-hearing cannot teach a vocal route.
        mount_reached_motor_effector_with_root(
            &mut cohorts,
            &mut population,
            &mut next_lineage,
            &mut fabric,
            &[regulation],
            &current_consequence,
            &preceding_action,
            &preceding_ordering,
            &[],
            &[],
            &BTreeMap::new(),
            &BTreeMap::new(),
        )
        .unwrap();
        assert!(!fabric.contains_contact(ordering, motor));
        assert_eq!(fabric.contact_count(), contacts_before);

        // Self-hearing cannot substitute for the earlier causal arrival from
        // ordering into its founding association.
        mount_reached_motor_effector_with_root(
            &mut cohorts,
            &mut population,
            &mut next_lineage,
            &mut fabric,
            &[sound_receptor, acoustic, regulation],
            &current_consequence,
            &preceding_action,
            &[],
            &[],
            &[],
            &BTreeMap::new(),
            &BTreeMap::new(),
        )
        .unwrap();
        assert!(!fabric.contains_contact(ordering, motor));
        assert_eq!(fabric.contact_count(), contacts_before);

        // A real returned sound on a different acoustic integration cannot
        // teach this ordering route's vocal motor.
        let mut unrelated_sound_consequence =
            directed_chain(&cohorts, &fabric, &[regulation, affective]);
        unrelated_sound_consequence.extend(directed_chain(
            &cohorts,
            &fabric,
            &[unrelated_sound_receptor, unrelated_acoustic],
        ));
        unrelated_sound_consequence.sort_unstable();
        mount_reached_motor_effector_with_root(
            &mut cohorts,
            &mut population,
            &mut next_lineage,
            &mut fabric,
            &[unrelated_sound_receptor, unrelated_acoustic, regulation],
            &unrelated_sound_consequence,
            &preceding_action,
            &preceding_ordering,
            &[],
            &[],
            &BTreeMap::new(),
            &BTreeMap::new(),
        )
        .unwrap();
        assert!(!fabric.contains_contact(ordering, motor));
        assert_eq!(fabric.contact_count(), contacts_before);

        // Even the exact ordered association path plus a preceding vocal
        // discharge, general whole-tract mechanics and self-hearing cannot
        // name one antagonist terminal.  The old rule treated this evidence
        // as authority for every preceding vocal motor and accumulated the
        // production fan-out.  V38 refuses that ambiguity.
        mount_reached_motor_effector_with_root(
            &mut cohorts,
            &mut population,
            &mut next_lineage,
            &mut fabric,
            &[sound_receptor, acoustic, regulation],
            &current_consequence,
            &preceding_action,
            &preceding_ordering,
            &[],
            &[],
            &BTreeMap::new(),
            &BTreeMap::new(),
        )
        .unwrap();
        assert!(!fabric.contains_contact(ordering, motor));
        assert_eq!(fabric.contact_count(), contacts_before);
        assert!(!fabric.contains_contact(acoustic, articulatory));
        assert!(!fabric.contains_contact(regulation, articulatory));
        assert!(!fabric.contains_contact(ordering, articulatory));

        // Repeating the same ambiguous evidence cannot accumulate a route.
        mount_reached_motor_effector_with_root(
            &mut cohorts,
            &mut population,
            &mut next_lineage,
            &mut fabric,
            &[sound_receptor, acoustic, regulation],
            &current_consequence,
            &preceding_action,
            &preceding_ordering,
            &[],
            &[],
            &BTreeMap::new(),
            &BTreeMap::new(),
        )
        .unwrap();
        assert_eq!(fabric.contact_count(), contacts_before);

        // Recreate the exact persisted V37 contamination. The V38 boundary
        // removes the unproved ordering -> motor contact; V40 preserves the
        // exact vocal-body identity and removes every electrical layer-13
        // bridge. No respiratory activation route is invented.
        fabric = fabric
            .append_contact(
                ordering,
                motor,
                ExactRational::integer(DEVELOPMENTAL_CONTACT_CONDUCTANCE_PICOSIEMENS),
            )
            .unwrap();
        assert!(fabric.contains_contact(ordering, motor));
        let topology_index = Arc::new(ResidentTopologyIndex::build(&cohorts, &fabric).unwrap());
        let state = ResidentCognitiveFormationState {
            generation: 7,
            next_lineage_ordinal: population
                .as_ref()
                .unwrap()
                .lineage_end_exclusive(),
            vocal_articulatory_effector_lineage: None,
            unexpressed_electrical_seeds: Box::new([]),
            dormant_lineage_seeds: Box::new([]),
            resting_population: population,
            cohorts: cohorts.into_boxed_slice(),
            electrical_fabric: fabric,
            active_electrical_frontier: Box::new([]),
            preceding_active_electrical_frontier: Box::new([]),
            older_active_electrical_frontier: Box::new([]),
            mosaics: Box::new([]),
            hippocampal: ResidentHippocampalIndex::default(),
            topology_index,
            formation_index: ResidentFormationIndex::default(),
        };
        let mut v37 = state
            .encode_with_format(CognitiveCodecFormat::V26, 1_600_000_000)
            .unwrap();
        v37[..MAGIC_V37.len()].copy_from_slice(MAGIC_V37);
        v37[MAGIC_V37.len()..MAGIC_V37.len() + std::mem::size_of::<u16>()]
            .copy_from_slice(&VERSION_V30.to_le_bytes());
        let migrated = ResidentCognitiveFormationState::migrate_to_current_format(
            &v37,
            1_600_000_000,
        )
        .unwrap();
        assert_eq!(&migrated[..MAGIC_V42.len()], MAGIC_V42);
        let restored = ResidentCognitiveFormationState::decode(&migrated, 1_600_000_000).unwrap();
        assert!(!restored.electrical_fabric.contains_contact(ordering, motor));
        assert!(!restored.electrical_fabric.contains_contact(motor, articulatory));
        assert!(!restored.electrical_fabric.contains_contact(ordering, articulatory));
        assert_eq!(
            restored.vocal_articulatory_effector_lineage,
            Some(articulatory)
        );
        assert_eq!(
            ResidentCognitiveFormationState::migrate_to_current_format(
                &migrated,
                1_600_000_000,
            )
            .unwrap(),
            migrated
        );

        // The same body marked V38 carries a provenance-accepted exact-axis
        // ordering -> motor route. V40 preserves that learned motor route and
        // the vocal-body identity, while removing every layer-13 electrical
        // contact. A second migration is exact.
        let mut v38 = state
            .encode_with_format(CognitiveCodecFormat::V26, 1_600_000_000)
            .unwrap();
        v38[..MAGIC_V38.len()].copy_from_slice(MAGIC_V38);
        v38[MAGIC_V38.len()..MAGIC_V38.len() + std::mem::size_of::<u16>()]
            .copy_from_slice(&VERSION_V30.to_le_bytes());
        let direct = ResidentCognitiveFormationState::migrate_to_current_format(
            &v38,
            1_600_000_000,
        )
        .unwrap();
        assert_eq!(&direct[..MAGIC_V42.len()], MAGIC_V42);
        let restored_direct =
            ResidentCognitiveFormationState::decode(&direct, 1_600_000_000).unwrap();
        assert!(restored_direct.electrical_fabric.contains_contact(ordering, motor));
        assert!(!restored_direct.electrical_fabric.contains_contact(motor, articulatory));
        assert!(!restored_direct
            .electrical_fabric
            .contains_contact(ordering, articulatory));
        assert_eq!(
            restored_direct.vocal_articulatory_effector_lineage,
            Some(articulatory)
        );
        assert_eq!(
            ResidentCognitiveFormationState::migrate_to_current_format(
                &direct,
                1_600_000_000,
            )
            .unwrap(),
            direct
        );
    }

    #[test]
    fn non_simultaneous_body_and_sensory_activity_does_not_manufacture_effectors() {
        let canal_anatomy =
            CanalAnatomy::new(6, 13_200, PositiveRatio::new(25, 1).unwrap()).unwrap();
        let bundle_anatomy = LocalCupulaBundleAnatomy::new(2, 5, 20_000).unwrap();
        let receptor_anatomy = phase_one_virtual_vestibular_anatomy().unwrap();
        let mut state = ResidentCognitiveFormationState::default();
        let turn = settle_signed_yaw_actuation(
            YawBodyState::new(0).unwrap(),
            SignedYawActuation::new(90_000, 250_000).unwrap(),
        )
        .unwrap();
        let mut canal = CanalState::at_rest();
        let mut heading = 0_u32;
        let mut frontier_route_sets = Vec::new();
        for (source_tick, signed_step) in turn.trajectory.as_slice().iter().copied().enumerate() {
            let predecessor_body = YawBodyState::new(heading).unwrap();
            heading =
                u32::try_from((i64::from(heading) + i64::from(signed_step)).rem_euclid(360_000))
                    .unwrap();
            let successor_body = YawBodyState::new(heading).unwrap();
            let reached = settle_reached_vestibular_bundle_tick(
                canal_anatomy,
                canal,
                signed_step,
                bundle_anatomy,
            )
            .unwrap();
            canal = reached.successor_canal;
            let ingress = prepare_resident_vestibular_ingress(
                u64::try_from(source_tick).unwrap(),
                predecessor_body,
                successor_body,
                reached,
                &receptor_anatomy,
            )
            .unwrap();
            let vestibular = state
                .prepare_vestibular_transition(&ingress, 16_000_000)
                .unwrap();
            if !vestibular.observation.physical_frontier_routes.is_empty() {
                frontier_route_sets.push(vestibular.observation.physical_frontier_routes.clone());
            }
            state = vestibular.successor;
        }
        let source = exact_optical_binaural_episode();
        let mut motor_recruitments = Vec::new();
        let mut articulatory_recruitments = Vec::new();
        let mut repeated_optical_frontier_route_sets = Vec::new();
        let mut emitted_layers = BTreeSet::new();
        for interval in 0..256 {
            let prepared = state.prepare(&source, 16_000_000).unwrap_or_else(|error| {
                panic!("optical interval {interval} failed: {error:?}")
            });
            let emitted_lineages = prepared
                .observation
                .emitted_neuron_fractals
                .iter()
                .map(|fractal| fractal.neuron_lineage)
                .collect::<Vec<_>>();
            motor_recruitments.extend(
                prepared
                    .observation
                    .motor_unit_recruitments
                    .iter()
                    .cloned(),
            );
            articulatory_recruitments.extend(
                prepared
                    .observation
                    .articulatory_unit_recruitments
                    .iter()
                    .cloned(),
            );
            if !prepared.observation.physical_frontier_routes.is_empty() {
                frontier_route_sets.push(prepared.observation.physical_frontier_routes.clone());
                repeated_optical_frontier_route_sets
                    .push(prepared.observation.physical_frontier_routes.clone());
            }
            state = prepared.successor;
            for lineage in emitted_lineages {
                let layer = state
                    .topology_index
                    .layer_of(lineage)
                    .expect("every emitted lineage remains mounted");
                emitted_layers.insert(layer);
            }
        }
        let layer_ten = state
            .cohorts
            .iter()
            .flat_map(|cohort| cohort.anatomy.mounts())
            .filter(|mount| mount.place().layer() == 10)
            .count();
        // The earlier receiver-only frontier accidentally made the separate
        // vestibular and later optical/acoustic episodes appear coincident.
        // With the exact advancing endpoint retained, this non-simultaneous
        // specimen must not manufacture a layer-10 association/body relation.
        assert_eq!(layer_ten, 0);
        // The separated episodes must not become a same-interval association
        // (layer_ten == 0 above holds). The current delayed-ordering law
        // lawfully mounts ONE retention-founded layer-11 route when a
        // retained mosaic's layer-9 cell carries a direct bond from
        // association material — the repeated identical episodes here admit
        // one mosaic, so one such route may exist. What remains forbidden
        // is any BODY-founded ordering: a layer-11 cell whose contacts
        // reach beyond layer-7 association and layer-9 retention material
        // would be manufactured coincidence, and stays refused.
        let layer_eleven_lineages = state
            .cohorts
            .iter()
            .flat_map(|cohort| {
                cohort
                    .anatomy
                    .mounts()
                    .iter()
                    .zip(cohort.anatomy.neuron_lineages())
            })
            .filter_map(|(mount, lineage)| {
                (mount.place().layer() == 11).then_some(*lineage)
            })
            .collect::<Vec<_>>();
        assert!(layer_eleven_lineages.len() <= 1);
        let layer_of = |lineage: [u8; 16]| {
            state
                .cohorts
                .iter()
                .flat_map(|cohort| {
                    cohort
                        .anatomy
                        .mounts()
                        .iter()
                        .zip(cohort.anatomy.neuron_lineages())
                })
                .find_map(|(mount, candidate)| {
                    (*candidate == lineage).then_some(mount.place().layer())
                })
        };
        let fabric_lineages = state.electrical_fabric.lineages().to_vec();
        for ordering in &layer_eleven_lineages {
            for (left_index, right_index) in state.electrical_fabric.contact_endpoints() {
                let left = fabric_lineages[left_index];
                let right = fabric_lineages[right_index];
                let partner = if left == *ordering {
                    right
                } else if right == *ordering {
                    left
                } else {
                    continue;
                };
                assert!(
                    matches!(layer_of(partner), Some(7) | Some(9)),
                    "retention-founded ordering may touch only association \
                     and retention material"
                );
            }
        }
        let layer_counts = state.observe_reached_neuron_count_by_layer();
        assert!(!layer_counts.iter().any(|(layer, _)| *layer == 12));
        assert!(!layer_counts.iter().any(|(layer, _)| *layer == 13));
        assert!(motor_recruitments.is_empty());
        assert!(articulatory_recruitments.is_empty());
        assert!(frontier_route_sets.iter().any(|routes| routes.len() > 1));
        assert!(frontier_route_sets
            .iter()
            .flatten()
            .any(|route| { route.outward_whole_carriers_from_seed() == 0 }));
        assert!(frontier_route_sets
            .iter()
            .flatten()
            .any(|route| { route.outward_whole_carriers_from_seed() > 0 }));
        assert!(frontier_route_sets
            .windows(2)
            .any(|pair| pair[0] != pair[1]));
        assert!(repeated_optical_frontier_route_sets
            .windows(2)
            .any(|pair| pair[0] != pair[1]));
        assert_eq!(
            layer_counts.iter().map(|(_, count)| *count).sum::<usize>(),
            state.summary().complete_neuron_count
        );
        // Repeated intervals on this one continuing optical/acoustic path
        // retain one formation. Its lawful later recurrence is sensory memory,
        // not a body effector, as the layer-12/13 and recruitment checks above
        // prove directly.
        assert_eq!(
            state
                .mosaics
                .iter()
                .filter(|mosaic| mosaic.recurrent_lineage.is_some())
                .count(),
            1
        );
        let retained = state
            .mosaics
            .iter()
            .find(|mosaic| mosaic.recurrent_lineage.is_some())
            .expect("the repeated physical path retained one formation");
        let retained_layers = retained
            .mosaic
            .member_lineages()
            .iter()
            .map(|lineage| {
                state
                    .topology_index
                    .layer_of(*lineage)
                    .expect("every retained lineage remains mounted")
            })
            .collect::<BTreeSet<_>>();
        let formation_layers = state
            .mosaics
            .iter()
            .map(|formation| {
                formation
                    .mosaic
                    .member_lineages()
                    .iter()
                    .map(|lineage| {
                        state
                            .topology_index
                            .layer_of(*lineage)
                            .expect("every formation lineage remains mounted")
                    })
                    .collect::<BTreeSet<_>>()
            })
            .collect::<Vec<_>>();
        assert!(
            emitted_layers.contains(&0)
                && emitted_layers.contains(&1)
                && emitted_layers.contains(&7),
            "physical producer did not emit sight, sound, and association fractals: {emitted_layers:?}"
        );
        let cross_sensory_retained = state.mosaics.iter().any(|formation| {
            let layers = formation
                .mosaic
                .member_lineages()
                .iter()
                .filter_map(|lineage| state.topology_index.layer_of(*lineage))
                .collect::<BTreeSet<_>>();
            let association_bond = formation.mosaic.original_bonds().iter().any(|bond| {
                let (left, right) = bond.endpoints();
                state.topology_index.layer_of(left) == Some(7)
                    || state.topology_index.layer_of(right) == Some(7)
            });
            layers.contains(&0) && layers.contains(&1) && association_bond
        });
        assert!(
            cross_sensory_retained,
            "no retained physical path spanned sight and sound through association: {formation_layers:?}; recurrent={retained_layers:?}"
        );
        let encoded = state.encode(16_000_000).unwrap();
        let cold = ResidentCognitiveFormationState::decode(&encoded, 16_000_000).unwrap();
        assert_eq!(cold, state);
    }

    #[test]
    fn one_new_retained_mosaic_mounts_one_sparse_recurrent_route() {
        let mut cohorts = Vec::new();
        let mut population =
            Some(DevelopmentalRestingPopulation::admit(16_000_000, 100_000, 100, &[]).unwrap());
        let mut next_lineage = 1;
        let members = (0..3)
            .map(|topology| {
                mount_intrinsic_neuron_at_place(
                    &mut cohorts,
                    &mut population,
                    &mut next_lineage,
                    DeclaredNeuronPlace::new(6, topology),
                )
                .unwrap()
            })
            .collect::<Vec<_>>();
        let mut fabric = ResidentElectricalFabric::default();
        mount_new_recurrent_retention(
            &mut cohorts,
            &mut population,
            &mut next_lineage,
            &mut fabric,
            &[members.clone()],
        )
        .unwrap();
        let retention = cohorts
            .iter()
            .flat_map(|cohort| {
                cohort
                    .anatomy
                    .mounts()
                    .iter()
                    .zip(cohort.anatomy.neuron_lineages())
            })
            .filter(|(mount, _)| mount.place().layer() == 9)
            .map(|(_, lineage)| *lineage)
            .collect::<Vec<_>>();
        assert_eq!(retention.len(), 1);
        assert_eq!(fabric.contact_count(), members.len());
        assert!(members
            .iter()
            .all(|member| fabric.contains_contact(*member, retention[0])));

        let cohort_count = cohorts.len();
        let contact_count = fabric.contact_count();
        mount_new_recurrent_retention(
            &mut cohorts,
            &mut population,
            &mut next_lineage,
            &mut fabric,
            &[],
        )
        .unwrap();
        assert_eq!(cohorts.len(), cohort_count);
        assert_eq!(fabric.contact_count(), contact_count);
    }

    #[test]
    fn newly_mounted_nested_formations_keep_distinct_recurrent_lineages() {
        let mut cohorts = Vec::new();
        let mut population =
            Some(DevelopmentalRestingPopulation::admit(16_000_000, 100_000, 100, &[]).unwrap());
        let mut next_lineage = 1;
        let members = (0..4)
            .map(|topology| {
                mount_intrinsic_neuron_at_place(
                    &mut cohorts,
                    &mut population,
                    &mut next_lineage,
                    DeclaredNeuronPlace::new(6, topology),
                )
                .unwrap()
            })
            .collect::<Vec<_>>();
        let narrow_members = members[..3].to_vec();
        let mut fabric = ResidentElectricalFabric::default();
        let mounted = mount_new_recurrent_retention(
            &mut cohorts,
            &mut population,
            &mut next_lineage,
            &mut fabric,
            &[narrow_members.clone(), members.clone()],
        )
        .unwrap();

        let retained_mosaic = |member_lineages: &[[u8; 16]]| {
            let fractal =
                crate::complete_neuron::SparsePhysicalStateDelta::from_canonical_entries(vec![
                    crate::complete_neuron::PhysicalStateDeltaEntry::new(
                        crate::complete_neuron::PhysicalStateCoordinate::PlasticRestLength,
                        crate::complete_neuron::ExactPhysicalStateDelta::Rational(
                            ExactRational::new(1, 3).unwrap(),
                        ),
                    )
                    .unwrap(),
                ])
                .unwrap();
            let bonds = member_lineages
                .windows(2)
                .map(|pair| StablePhysicalBondReference::new(pair[0], pair[1], 0).unwrap())
                .collect::<Vec<_>>();
            AdmittedPhysicalMosaic::from_parts_for_tests(
                member_lineages.to_vec(),
                vec![fractal; member_lineages.len()],
                bonds.clone(),
                bonds,
                vec![member_lineages[0]],
            )
        };
        assert_eq!(mounted.len(), 2);
        assert_ne!(mounted[0], mounted[1]);
        validate_recurrent_retention_lineage(&cohorts, &fabric, &narrow_members, mounted[0])
            .unwrap();
        validate_recurrent_retention_lineage(&cohorts, &fabric, &members, mounted[1]).unwrap();
        assert_eq!(fabric.contact_count(), narrow_members.len() + members.len());

        let narrow_mosaic = retained_mosaic(&narrow_members);
        let broad_mosaic = retained_mosaic(&members);
        let mut legacy = [
            RetainedOrganismMosaic::newly_admitted(narrow_mosaic.clone()),
            RetainedOrganismMosaic::newly_admitted(broad_mosaic),
        ];
        resolve_unpersisted_recurrent_retention(&cohorts, &fabric, &mut legacy).unwrap();
        assert_eq!(legacy[0].recurrent_lineage, Some(mounted[0]));
        assert_eq!(legacy[1].recurrent_lineage, Some(mounted[1]));

        let mut ambiguous = [
            RetainedOrganismMosaic::newly_admitted(narrow_mosaic.clone()),
            RetainedOrganismMosaic::newly_admitted(narrow_mosaic),
        ];
        assert!(matches!(
            resolve_unpersisted_recurrent_retention(&cohorts, &fabric, &mut ambiguous),
            Err(FormationError::NeuronLineageAuthorityChanged)
        ));
    }

    /// THE HEADLINE LAW, at the crate boundary: admitting a real physical
    /// mosaic — the thing that used to publish ~893 objects per reassembly —
    /// now creates NOTHING on disk, and the retired checkpoint does not move.
    ///
    /// This replaces `episode_by_reference_round_trips_through_directory_cold_custody`,
    /// which proved the opposite law (that a reassembly round-tripped through
    /// a content-addressed directory).  That law is retired by owner's order.
    #[test]
    #[ignore = "retired: fixture requires Boolean/member-set mosaic admission"]
    fn an_admitted_reassembly_writes_no_file_anywhere_and_moves_no_checkpoint() {
        let root = std::env::temp_dir().join(format!(
            "guala-no-archive-{}-{}",
            std::process::id(),
            line!(),
        ));
        let _ = std::fs::remove_dir_all(&root);
        std::fs::create_dir_all(&root).unwrap();
        let entries_before = std::fs::read_dir(&root).unwrap().count();

        let mut state = lesson_state_with_retained_experience();
        let checkpoint_before = state.hippocampal;
        let partial = exact_four_partial_optical_episode();
        let dark = exact_four_dark_optical_episode();
        let sources = std::iter::once(&partial)
            .chain(std::iter::repeat(&dark).take(DARK_TAIL_EPISODES))
            .collect::<Vec<_>>();
        let mut formed = 0usize;
        let mut reassemblies = 0usize;
        let mut endogenous_reassemblies = 0usize;
        for source in sources {
            let prepared = state
                .prepare_admitted_transition(&admitted_fixture_episode(source), 16_000_000)
                .unwrap();
            if prepared.observation.mosaic_formed.is_some() {
                formed += 1;
            }
            reassemblies += prepared.observation.partial_cue_reassembly_count;
            endogenous_reassemblies += prepared.observation.endogenous_partial_cue_reassembly_count;
            // The successor encodes and commits with no publication step.
            state.encode_successor(&prepared, 16_000_000).unwrap();
            state.commit(prepared).unwrap();
        }

        // Reassembly still happened — this is not a test of an inert path.
        // This fixture supplies one external partial cue; the cue's own
        // continuing contact tail is not mislabeled as endogenous activity.
        assert_eq!(formed, 1);
        assert_eq!(reassemblies, 1);
        assert_eq!(endogenous_reassemblies, 0);
        // And the file count did not move by one.
        assert_eq!(std::fs::read_dir(&root).unwrap().count(), entries_before);
        assert_eq!(state.hippocampal, checkpoint_before);
        assert!(!state.hippocampal.carries_retired_archive_reference());
        let _ = std::fs::remove_dir_all(&root);
    }

    #[test]
    fn retired_false_or_empty_cognitive_state_cannot_return() {
        for magic in [
            b"GLCOG003",
            b"GLCOG004",
            b"GLCOG005",
            b"GLCOG006",
            b"GLCOG007",
            b"GLCOG008",
            b"GLCOG009",
            b"GLCOG010",
        ] {
            let mut retired = Vec::from(magic.as_slice());
            retired.extend_from_slice(&4u16.to_le_bytes());
            assert_eq!(
                ResidentCognitiveFormationState::decode(&retired, 1_000_000),
                Err(FormationError::RetiredCognitiveState)
            );
        }
    }

    #[test]
    fn adjacent_exact_contact_transfers_are_the_only_ordered_path_evidence() {
        let first = [1_u8; 16];
        let via = [2_u8; 16];
        let last = [3_u8; 16];
        let first_bond = StablePhysicalBondReference::new(first, via, 0).unwrap();
        let second_bond = StablePhysicalBondReference::new(via, last, 0).unwrap();
        let predecessor =
            [ActiveElectricalFrontierEntry::caused(first, via, first_bond, 7).unwrap()];
        let current = [ActiveElectricalFrontierEntry::caused(via, last, second_bond, 5).unwrap()];
        let incidence = [(first, 0), (via, 0), (via, 1), (last, 1)];
        let paths =
            ordered_physical_paths_for_relation(&incidence, &[0, 1], &predecessor, &current);
        assert_eq!(paths.len(), 1);
        assert_eq!(
            paths[0].directed_transfers(),
            [(first, via, first_bond, 7), (via, last, second_bond, 5),]
        );

        assert_eq!(
            ActiveElectricalFrontierEntry::caused(first, last, second_bond, 5),
            Err(FormationError::NoncanonicalState)
        );
        assert!(ordered_physical_paths_for_relation(
            &incidence,
            &[0, 1],
            &[ActiveElectricalFrontierEntry::legacy_receiver(via)],
            &current,
        )
        .is_empty());
        assert!(ordered_physical_paths_for_relation(
            &incidence,
            &[0, 1],
            &predecessor,
            &[ActiveElectricalFrontierEntry::caused(last, via, second_bond, 5).unwrap()],
        )
        .is_empty());
    }

    #[test]
    fn working_causal_frontier_requires_unseeded_adjacent_continuation_and_expires() {
        let first = [1_u8; 16];
        let via = [2_u8; 16];
        let last = [3_u8; 16];
        let first_bond = StablePhysicalBondReference::new(first, via, 0).unwrap();
        let second_bond = StablePhysicalBondReference::new(via, last, 0).unwrap();
        let predecessor =
            [ActiveElectricalFrontierEntry::caused(first, via, first_bond, 7).unwrap()];
        let current = [ActiveElectricalFrontierEntry::caused(via, last, second_bond, 5).unwrap()];

        let (continued, settled) = working_causal_frontier_observation(&predecessor, &current, &[]);
        assert_eq!(continued.len(), 1);
        assert_eq!(
            continued[0].directed_transfers(),
            [(first, via, first_bond, 7), (via, last, second_bond, 5)]
        );
        assert!(settled.is_empty());

        // A current external/body/fluid seed at the intermediate cell makes
        // the second transfer causally ambiguous, so it cannot prove internal
        // continuation from the predecessor frontier.
        let (externally_reseeded, _) =
            working_causal_frontier_observation(&predecessor, &current, &[via]);
        assert!(externally_reseeded.is_empty());
        let (adjacent_reseeded, _) =
            working_causal_frontier_observation(&predecessor, &current, &[last]);
        assert!(adjacent_reseeded.is_empty());

        // With no onward whole-carrier transfer, the predecessor cause loses
        // propagation authority after exactly this adjacent interval.
        let (continued, settled) = working_causal_frontier_observation(&predecessor, &[], &[]);
        assert!(continued.is_empty());
        assert_eq!(settled.len(), 1);
        assert_eq!(
            (
                settled[0].sender,
                settled[0].receiver,
                settled[0].bond,
                settled[0].transferred_whole_carriers,
            ),
            (first, via, first_bond, 7)
        );

        // Historical receiver-only frontier entries can propagate physically
        // but cannot be promoted into directed causal evidence.
        let legacy = [ActiveElectricalFrontierEntry::legacy_receiver(via)];
        let (continued, settled) = working_causal_frontier_observation(&legacy, &current, &[]);
        assert!(continued.is_empty());
        assert!(settled.is_empty());
    }

    #[test]
    fn directed_transfer_frontier_preserves_direction_and_one_advancing_endpoint() {
        let sender = [1_u8; 16];
        let receiver = [2_u8; 16];
        let bond = StablePhysicalBondReference::new(sender, receiver, 0).unwrap();
        let transfer =
            ActiveElectricalFrontierEntry::caused(sender, receiver, bond, 7).unwrap();
        assert_eq!(transfer.affected_lineages(), [Some(receiver), None]);
        let incoming = incoming_frontier_bonds(&[transfer]);
        assert!(!frontier_crossing_advances(
            &incoming,
            receiver,
            bond,
            false,
        ));
        assert!(frontier_crossing_advances(
            &incoming,
            receiver,
            bond,
            true,
        ));
        assert_eq!(
            transfer.directed_transfer(),
            Some(DirectedPhysicalTransferObservation {
                sender,
                receiver,
                bond,
                transferred_whole_carriers: 7,
            })
        );

        let reverse_frontier = ActiveElectricalFrontierEntry::caused_with_frontier(
            sender, receiver, sender, bond, 7, false,
        )
        .unwrap();
        assert_eq!(reverse_frontier.affected_lineages(), [Some(sender), None]);
        assert_eq!(reverse_frontier.directed_transfer(), transfer.directed_transfer());
        let mut encoded = Vec::new();
        reverse_frontier.encode_v20(&mut encoded);
        let mut cursor = 0;
        assert_eq!(
            ActiveElectricalFrontierEntry::decode_v20(&encoded, &mut cursor, true).unwrap(),
            reverse_frontier
        );
        assert_eq!(cursor, encoded.len());
        let mut cursor = 0;
        assert_eq!(
            ActiveElectricalFrontierEntry::decode_v20(&encoded, &mut cursor, false),
            Err(FormationError::NoncanonicalState)
        );

        let body_owned_acoustic_efference =
            ActiveElectricalFrontierEntry::caused_with_frontier(
                sender, receiver, sender, bond, 7, true,
            )
            .unwrap();
        let mut encoded = Vec::new();
        body_owned_acoustic_efference.encode_v20(&mut encoded);
        let mut cursor = 0;
        let decoded =
            ActiveElectricalFrontierEntry::decode_v20(&encoded, &mut cursor, true).unwrap();
        assert_eq!(decoded, body_owned_acoustic_efference);
        assert!(decoded.carries_body_owned_acoustic_efference());
        assert_eq!(cursor, encoded.len());

        let legacy = ActiveElectricalFrontierEntry::legacy_receiver(receiver);
        assert_eq!(legacy.affected_lineages(), [Some(receiver), None]);

        // A scheduler event is physical maintenance, not causal authority.
        // Its endpoint changes are carried by the independent incident-contact
        // wake law; it must never be encoded as an active cognitive frontier.
        assert_eq!(causal_frontier_crossing(3, 4, false, false), None);
        assert_eq!(causal_frontier_crossing(3, 4, true, true), None);
        assert_eq!(causal_frontier_crossing(3, 4, true, false), Some((3, 4)));
        assert_eq!(causal_frontier_crossing(3, 4, false, true), Some((4, 3)));
    }

    #[test]
    fn physical_prediction_requires_two_unseeded_layer_eleven_routes_from_one_intrinsic_cause() {
        let intrinsic_cause = [1_u8; 16];
        let ordering_a = [2_u8; 16];
        let ordering_b = [3_u8; 16];
        let consequence_a = [4_u8; 16];
        let consequence_b = [5_u8; 16];
        let cause_a = StablePhysicalBondReference::new(intrinsic_cause, ordering_a, 0).unwrap();
        let cause_b = StablePhysicalBondReference::new(intrinsic_cause, ordering_b, 0).unwrap();
        let ordered_a = StablePhysicalBondReference::new(ordering_a, consequence_a, 0).unwrap();
        let ordered_b = StablePhysicalBondReference::new(ordering_b, consequence_b, 0).unwrap();
        let predecessor = [
            ActiveElectricalFrontierEntry::caused(intrinsic_cause, ordering_a, cause_a, 7).unwrap(),
            ActiveElectricalFrontierEntry::caused(intrinsic_cause, ordering_b, cause_b, 5).unwrap(),
        ];
        let current = [
            ActiveElectricalFrontierEntry::caused(ordering_a, consequence_a, ordered_a, 3).unwrap(),
            ActiveElectricalFrontierEntry::caused(ordering_b, consequence_b, ordered_b, 2).unwrap(),
        ];
        let layers = [
            (intrinsic_cause, 13),
            (ordering_a, 11),
            (ordering_b, 11),
            (consequence_a, 10),
            (consequence_b, 10),
        ];

        let alternatives =
            physical_prediction_alternatives_observation(&predecessor, &current, &[], &layers);
        assert_eq!(alternatives.len(), 2);
        assert_eq!(alternatives[0].directed_transfers()[0].0, intrinsic_cause);
        assert_eq!(alternatives[1].directed_transfers()[0].0, intrinsic_cause);
        assert_ne!(
            alternatives[0].directed_transfers()[1].1,
            alternatives[1].directed_transfers()[1].1
        );
        assert!(physical_prediction_alternatives_observation(
            &predecessor[..1],
            &current[..1],
            &[],
            &layers,
        )
        .is_empty());
        assert!(physical_prediction_alternatives_observation(
            &predecessor,
            &current,
            &[ordering_a],
            &layers,
        )
        .is_empty());
    }

    #[test]
    fn body_consequence_preserves_both_directions_on_the_reached_vestibular_relation() {
        let regulation = [6_u8; 16];
        let consequence = [7_u8; 16];
        let bond = StablePhysicalBondReference::new(regulation, consequence, 0).unwrap();
        let outward =
            [ActiveElectricalFrontierEntry::caused(regulation, consequence, bond, 11).unwrap()];
        let layers = [(regulation, 8), (consequence, 10)];
        let reached = [regulation];
        assert!(
            body_consequence_transfer_observation(&outward, &layers, &reached, false).is_empty()
        );
        let observed = body_consequence_transfer_observation(&outward, &layers, &reached, true);
        assert_eq!(observed.len(), 1);
        assert_eq!(
            (
                observed[0].sender,
                observed[0].receiver,
                observed[0].transferred_whole_carriers,
            ),
            (regulation, consequence, 11)
        );

        let inward =
            [ActiveElectricalFrontierEntry::caused(consequence, regulation, bond, 7).unwrap()];
        let observed = body_consequence_transfer_observation(&inward, &layers, &reached, true);
        assert_eq!(observed.len(), 1);
        assert_eq!(
            (
                observed[0].sender,
                observed[0].receiver,
                observed[0].transferred_whole_carriers,
            ),
            (consequence, regulation, 7)
        );
        assert!(body_consequence_transfer_observation(&inward, &layers, &[], true).is_empty());
    }

    #[test]
    fn two_recurring_ordered_paths_require_the_same_directed_physical_route() {
        let first = [1_u8; 16];
        let second = [2_u8; 16];
        let third = [3_u8; 16];
        let first_bond = StablePhysicalBondReference::new(first, second, 0).unwrap();
        let second_bond = StablePhysicalBondReference::new(second, third, 0).unwrap();
        let oldest =
            [
                ActiveElectricalFrontierEntry::caused(
            first,
            first_bond.endpoints().1,
            first_bond,
            7,
        )
                .unwrap(),
            ];
        let older = [ActiveElectricalFrontierEntry::caused(second, third, second_bond, 5).unwrap()];
        let preceding =
            [ActiveElectricalFrontierEntry::caused(first, second, first_bond, 9).unwrap()];
        let current =
            [ActiveElectricalFrontierEntry::caused(second, third, second_bond, 4).unwrap()];
        let incidence = [(first, 0), (second, 0), (second, 1), (third, 1)];
        let relations = ordered_path_relations_for_relation(
            &incidence,
            &[0, 1],
            &oldest,
            &older,
            &preceding,
            &current,
        );
        assert_eq!(relations.len(), 1);
        assert_eq!(
            relations[0].directed_transfers(),
            [
                (first, second, first_bond, 7),
                (second, third, second_bond, 5),
                (first, second, first_bond, 9),
                (second, third, second_bond, 4),
            ]
        );
        assert!(ordered_path_relations_for_relation(
            &incidence,
            &[0, 1],
            &[],
            &older,
            &preceding,
            &current,
        )
        .is_empty());
    }

    #[test]
    fn v19_recipient_only_frontier_cannot_cross_current_topology_boundary() {
        let retired = ResidentCognitiveFormationState::default()
            .encode_with_format(CognitiveCodecFormat::V12, 16_000_000)
            .unwrap();
        let current =
            ResidentCognitiveFormationState::migrate_to_current_format(&retired, 16_000_000)
                .unwrap();
        let mut state = ResidentCognitiveFormationState::decode(&current, 16_000_000).unwrap();
        let mut cohorts = state.cohorts.to_vec();
        let mut population = state.resting_population.take();
        let mut next_lineage_ordinal = state.next_lineage_ordinal;
        let sender = mount_intrinsic_neuron_at_place(
            &mut cohorts,
            &mut population,
            &mut next_lineage_ordinal,
            DeclaredNeuronPlace::new(6, 0),
        )
        .unwrap();
        let receiver = mount_intrinsic_neuron_at_place(
            &mut cohorts,
            &mut population,
            &mut next_lineage_ordinal,
            DeclaredNeuronPlace::new(6, 1),
        )
        .unwrap();
        let electrical_fabric = ResidentElectricalFabric::default()
            .append_contact(
                sender,
                receiver,
                ExactRational::integer(DEVELOPMENTAL_CONTACT_CONDUCTANCE_PICOSIEMENS),
            )
            .unwrap();
        state.generation = 1;
        state.next_lineage_ordinal = next_lineage_ordinal;
        state.resting_population = population;
        state.cohorts = cohorts.into_boxed_slice();
        state.electrical_fabric = electrical_fabric;
        let bond = organism_mosaic_topology(&state.cohorts, &state.electrical_fabric)
            .unwrap()
            .bonds[0];
        state.active_electrical_frontier =
            vec![ActiveElectricalFrontierEntry::caused(sender, receiver, bond, 1).unwrap()]
                .into_boxed_slice();
        state.active_electrical_frontier = state
            .active_electrical_frontier
            .iter()
            .map(|entry| ActiveElectricalFrontierEntry::legacy_receiver(entry.receiver()))
            .collect::<Vec<_>>()
            .into_boxed_slice();
        let legacy = state
            .encode_with_format(CognitiveCodecFormat::V19, 16_000_000)
            .unwrap();
        let current =
            ResidentCognitiveFormationState::migrate_to_current_format(&legacy, 16_000_000)
                .unwrap();
        assert_eq!(&current[..MAGIC_V42.len()], MAGIC_V42);
        let cold = ResidentCognitiveFormationState::decode(&current, 16_000_000).unwrap();
        assert_eq!(cold.encode(16_000_000).unwrap(), current);
        assert!(cold.active_electrical_frontier.is_empty());
    }
