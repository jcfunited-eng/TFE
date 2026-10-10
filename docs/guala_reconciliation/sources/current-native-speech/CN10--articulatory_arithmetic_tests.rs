//! Width and retained-variant falsifiers. Extreme coordinates below are
//! declared decoder-admitted fixtures, not produced neuronal experience.

use super::*;

#[test]
fn extreme_band_state_refuses_audio_width_without_i32_difference_overflow() {
    let mut acoustic = SpectralAcousticState::at_rest();
    acoustic.band_limit[0] = i32::MIN;
    let mut lung = NEUTRAL_LUNG_AIR_MICROLITRES;
    let result = advance_spectral_organ(
        &mut acoustic, BodyAxis::GlottalAperture.anatomy().neutral,
        [MAX_TRACT_AREA_SQUARE_MILLIMETRES; TRACT_SECTION_COUNT],
        &mut lung, SPECTRAL_ORGAN_MATERIAL,
    );
    // -2^31 + round(2^31 * 11650 / 16000); the final coordinate fits i32.
    assert_eq!(acoustic.band_limit[0], -583_847_117);
    assert_eq!(result, Err(ArticulatoryBodyError::PressureOutsideAudioWidth));
}

#[test]
fn extreme_lip_state_refuses_audio_width_without_i32_difference_overflow() {
    let mut acoustic = SpectralAcousticState::at_rest();
    acoustic.lip_low_pass[0] = i32::MIN;
    let mut lung = NEUTRAL_LUNG_AIR_MICROLITRES;
    let result = advance_spectral_organ(
        &mut acoustic, BodyAxis::GlottalAperture.anatomy().neutral,
        [MIN_TRACT_AREA_SQUARE_MILLIMETRES; TRACT_SECTION_COUNT],
        &mut lung, SPECTRAL_ORGAN_MATERIAL,
    );
    // -2^31 + round(2^31 * 3071 / 16000), with the unchanged rounding law.
    assert_eq!(acoustic.lip_low_pass[0], -1_735_301_005);
    assert_eq!(result, Err(ArticulatoryBodyError::PressureOutsideAudioWidth));
}

#[test]
fn opposite_extreme_fluid_coordinates_use_wide_velocity_and_upstream_difference() {
    let mut acoustic = SpectralAcousticState::at_rest();
    for pair in acoustic.fluid_cells.chunks_exact_mut(2) {
        pair[0] = i32::MAX;
        pair[1] = i32::MIN;
    }
    let result = advance_spectral_fluid_cells(
        &mut acoustic, 1,
        [MAX_TRACT_AREA_SQUARE_MILLIMETRES - 1; TRACT_SECTION_COUNT],
    ).unwrap();
    for pair in acoustic.fluid_cells.chunks_exact(2) {
        // The unchanged fluid law already has this physical saturation.
        assert_eq!(pair, &[-4_096, i32::MAX]);
    }
    assert_eq!(result, -8_765_256);
}

#[test]
fn legacy_tube_keeps_its_original_pcm_saturation_without_clamping_retained_state() {
    for (pressure, expected_pcm) in [(50_000, i16::MAX), (-50_000, i16::MIN)] {
        let mut right = [0; TRACT_SECTION_COUNT];
        right[TRACT_SECTION_COUNT - 1] = pressure;
        let (_, next_left, emitted) = advance_tube(
            right, [0; TRACT_SECTION_COUNT],
            [MAX_TRACT_AREA_SQUARE_MILLIMETRES; TRACT_SECTION_COUNT], 0,
        ).unwrap();
        assert_eq!(emitted, expected_pcm);
        assert_eq!(next_left[TRACT_SECTION_COUNT - 1].signum(), pressure.signum());
        assert_ne!(next_left[TRACT_SECTION_COUNT - 1], i32::from(expected_pcm));
    }
}
