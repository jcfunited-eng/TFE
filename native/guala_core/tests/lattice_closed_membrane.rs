#[path = "../src/lattice_closed_membrane.rs"]
mod lattice_closed_membrane;

use core::mem::size_of;
use lattice_closed_membrane::{
    transition_membrane, ChargeQuantum, ExactSignedCharge, FiniteChargeDomain,
    MembraneAdmissionError, MembraneAnatomy, MembraneState, SpecificCapacitanceScale,
    SurfaceAreaScale, TimeQuantum,
};

fn anatomy() -> MembraneAnatomy {
    MembraneAnatomy::admit(
        SurfaceAreaScale::new(3, 1).unwrap(),
        SpecificCapacitanceScale::new(1, 2).unwrap(),
        ChargeQuantum::new(1, 6).unwrap(),
        TimeQuantum::new(1, 1_000).unwrap(),
        FiniteChargeDomain::new(-9, 9).unwrap(),
    )
    .unwrap()
}

#[test]
fn canonical_scales_derive_exact_capacitance_current_and_potential() {
    let anatomy = anatomy();
    assert_eq!(anatomy.surface_area().parts(), (3, 1));
    assert_eq!(anatomy.specific_capacitance().parts(), (1, 2));
    assert_eq!(anatomy.charge_quantum().parts(), (1, 6));
    assert_eq!(anatomy.time_quantum().parts(), (1, 1_000));
    assert_eq!(anatomy.capacitance(), (3, 2));
    assert_eq!(anatomy.current_quantum(), (500, 3));
    assert_eq!(anatomy.charge_domain().bounds(), (-9, 9));
    assert_eq!(
        anatomy.genesis(3).unwrap().potential().parts(),
        (false, 1, 3)
    );
    assert_eq!(
        anatomy.genesis(-3).unwrap().potential().parts(),
        (true, 1, 3)
    );
}

#[test]
fn noncanonical_zero_and_overwide_scales_are_refused_at_admission() {
    assert_eq!(
        SurfaceAreaScale::new(0, 1),
        Err(MembraneAdmissionError::ZeroScale)
    );
    assert_eq!(
        SurfaceAreaScale::new(2, 4),
        Err(MembraneAdmissionError::NonCanonicalScale)
    );
    assert_eq!(
        MembraneAnatomy::admit(
            SurfaceAreaScale::new(u128::MAX, 1).unwrap(),
            SpecificCapacitanceScale::new(u128::MAX, 1).unwrap(),
            ChargeQuantum::new(1, 1).unwrap(),
            TimeQuantum::new(1, 1).unwrap(),
            FiniteChargeDomain::new(-1, 1).unwrap(),
        ),
        Err(MembraneAdmissionError::ArithmeticWidth)
    );
}

#[test]
fn quiescence_binds_exact_predecessor_and_successor() {
    let predecessor = anatomy().genesis(4).unwrap();
    let event = predecessor
        .admit_outward_charge(ExactSignedCharge::new(0, 1).unwrap())
        .unwrap();
    assert_eq!(event.predecessor(), predecessor);
    assert_eq!(event.successor(), predecessor);
    assert_eq!(event.outward_charge_quanta(), 0);
    assert_eq!(transition_membrane(event), predecessor);
}

#[test]
fn exact_outward_and_inward_transfers_change_only_charge() {
    let predecessor = anatomy().genesis(3).unwrap();
    let outward = predecessor
        .admit_outward_charge(ExactSignedCharge::new(1, 3).unwrap())
        .unwrap();
    assert_eq!(outward.outward_charge_quanta(), 2);
    let after_outward = transition_membrane(outward);
    assert_eq!(after_outward.charge_quanta(), 1);
    assert_eq!(after_outward.potential().parts(), (false, 1, 9));

    let inward = after_outward
        .admit_outward_charge(ExactSignedCharge::new(-1, 2).unwrap())
        .unwrap();
    assert_eq!(inward.outward_charge_quanta(), -3);
    let after_inward = transition_membrane(inward);
    assert_eq!(after_inward.charge_quanta(), 4);
    assert_eq!(after_inward.anatomy(), predecessor.anatomy());
}

#[test]
fn exact_non_lattice_half_step_is_refused_not_rounded() {
    let predecessor = anatomy().genesis(0).unwrap();
    let half_quantum = ExactSignedCharge::new(1, 12).unwrap();
    assert_eq!(half_quantum.parts(), (false, 1, 12));
    assert_eq!(
        predecessor.admit_outward_charge(half_quantum),
        Err(MembraneAdmissionError::NonLatticeChargeTransfer)
    );
    assert_eq!(predecessor.charge_quanta(), 0);
}

#[test]
fn constant_drive_that_would_exit_the_physical_domain_is_refused() {
    let at_upper_domain = anatomy().genesis(9).unwrap();
    assert_eq!(
        at_upper_domain.admit_outward_charge(ExactSignedCharge::new(-1, 6).unwrap()),
        Err(MembraneAdmissionError::ChargeOutsideDomain)
    );
    assert_eq!(at_upper_domain.charge_quanta(), 9);
    assert_eq!(
        anatomy().genesis(10),
        Err(MembraneAdmissionError::ChargeOutsideDomain)
    );
}

#[test]
fn one_hundred_thousand_steps_retain_fixed_residency_and_exact_state() {
    let outward = ExactSignedCharge::new(1, 6).unwrap();
    let inward = ExactSignedCharge::new(-1, 6).unwrap();
    let expected_state_bytes = size_of::<MembraneState>();
    let mut state = anatomy().genesis(0).unwrap();
    for _ in 0..100_000 {
        state = transition_membrane(state.admit_outward_charge(outward).unwrap());
        state = transition_membrane(state.admit_outward_charge(inward).unwrap());
        assert_eq!(size_of::<MembraneState>(), expected_state_bytes);
    }
    assert_eq!(state.charge_quanta(), 0);
    assert_eq!(state.potential().parts(), (false, 0, 1));
}

#[test]
fn production_source_has_only_fixed_residency_local_physics_shape() {
    let source = include_str!("../src/lattice_closed_membrane.rs");
    for forbidden in [
        "BigInt",
        "BigRational",
        "Vec<",
        "HashMap",
        "BTreeMap",
        "Mutex",
        "RwLock",
        "Arc<",
        "serde",
        "database",
        "owner",
        "receipt",
        "authority",
        ".clamp(",
        "saturating_",
        "wrapping_",
        "unsafe",
        "codec",
        "serialize",
    ] {
        assert!(
            !source.contains(forbidden),
            "forbidden source shape: {forbidden}"
        );
    }
    assert!(source.contains("checked_mul"));
    assert!(source.contains("checked_sub"));
    assert!(source.contains("pub(crate) fn transition_membrane"));
}
