//! Per-neuron anatomy derived from the neuron's OWN declared geometry.
//!
//! Ratified 2026-08-05 (`docs/GUALA_GEOMETRIC_ANATOMY_DIFFERENTIATION_RATIFICATION_2026-08-05.md`):
//! no two neurons may be authored physically identical.  Identical authored
//! membrane capacitance made stored energy `q^2 e^2 / 2C` tie exactly between
//! neighbours, and the ratified energy-descent transfer law
//! (`sparse_electrical_contact::stored_energy_strictly_decreases`) refuses ties,
//! so a one-charge imbalance could never descend: a permanent Coulomb blockade.
//! Distinctness is not a numerical convenience here, it is the anatomy: a
//! receptor's membrane area is set by the territory its own declared place
//! occupies in its organism's sensory topology, and two receptors cannot occupy
//! the same place.
//!
//! # The declared geometric measure
//!
//! Every mounted receptor site declares (`neuron_source_anchor::NeuronSourceSite`)
//! the sense layer it belongs to and its `topology_index` — its own place in
//! that sense's declared topology (the production app authors
//! `topology_index = row * columns + column` for the retinal card surface and
//! `topology_index = ear_index` for the two ears; the substrate's fixtures
//! author one index per receptor per sense).  A site's place is therefore the
//! integer lattice point
//!
//! ```text
//!   p(site) = (sense_layer, topology_index)   in  N x N
//! ```
//!
//! Its **declared territory** is the count of declared places the site closes
//! off when the lattice is swept outward from the organism's origin by shells
//! of constant declared eccentricity `d = sense_layer + topology_index` (the
//! taxicab/L1 distance from the origin of the sensory lattice), each shell
//! swept in topology order:
//!
//! ```text
//!   A(site) = #{ p' : ecc(p') < d }  +  #{ p' on shell d up to this site }
//!           = d (d + 1) / 2  +  topology_index  +  1
//! ```
//!
//! `A` is a positive integer: the exact number of declared receptor places
//! contained in the closed taxicab triangle whose far corner is this site.
//! The first place in the first sense layer has territory `1` — exactly one
//! unit patch — and territory grows outward, which is the eccentricity
//! dilation real receptor mosaics show.
//!
//! # The capacitance
//!
//! Membrane capacitance is specific capacitance times membrane area.  The
//! existing authored base (`1 pF`, unchanged) is the capacitance of ONE unit
//! patch of this virtual membrane, so a site covering `A` unit patches carries
//!
//! ```text
//!   C(site) = C_base * A(site)
//! ```
//!
//! Scale comes from the existing authored base; spread comes only from the
//! declared geometry.  No new tunable constant is introduced, the value is an
//! exact rational (an exact integer multiple of an exact rational), and the
//! whole derivation reads only declared quantities.
//!
//! # Injectivity
//!
//! `d(d+1)/2 + topology_index` is the Cantor pairing of
//! `(sense_layer, topology_index)`, a bijection `N x N -> N`; adding one keeps
//! it injective.  Distinct declared places therefore always give distinct
//! capacitances, so within any cohort whose members occupy distinct declared
//! places no two stored energies can tie.  A cohort that declares two sites at
//! the same place is refused at construction
//! (`ReachedCohortError::DegenerateDeclaredGeometry`) rather than silently
//! authored with identical pieces.
//!
//! # Alternatives considered (rejected as less simple, not as less honest)
//!
//! - **Declared coordinate box volume** `prod_j (x_j + 1)` over the site's
//!   declared axis coordinates.  Geometrically the most direct reading, but it
//!   is not injective on a two-dimensional lattice (`(0,3)` and `(1,1)` both
//!   give 4), and the substrate's own optical fixtures declare the SAME
//!   coordinate pair (`receptor = 0`) on every port, so it cannot differentiate
//!   them at all.
//! - **Cantor pairing over the full declared coordinate tuple** instead of the
//!   topology index.  Equivalent where coordinates are numeric and complete,
//!   but coordinate ids are declared as free text (they need not be numeric),
//!   and variable-length tuples need a length-folding convention whose
//!   injectivity is more delicate to state.  The topology index is the
//!   declared numeric place those coordinates spell (the app computes it
//!   from row and column), so this measure reads the same geometry with none
//!   of that fragility.
//! - **Bounded dilation** `A' = 1 + A/(1+A)` (all areas within a factor of two
//!   of the base patch).  Injective and exactly rational, but the bound is an
//!   extra unauthored physical claim; the plain territory count is simpler.

use crate::elementary_charge_membrane::{MembraneCapacitance, MembraneChargeError};
use crate::exact_rational::{ExactRational, ExactRationalError};
use crate::neuron_source_anchor::NeuronSourceSite;

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) enum DeclaredGeometryError {
    ArithmeticWidth,
    ExactRational(ExactRationalError),
    Membrane(MembraneChargeError),
}

/// The exact count of declared receptor places the site's own place closes off
/// in its organism's sensory lattice — its declared membrane territory, in
/// unit patches.  Always at least one.
pub(crate) fn declared_geometric_territory(
    site: &NeuronSourceSite,
) -> Result<u128, DeclaredGeometryError> {
    place_territory(
        u128::from(site.sense().declared_layer()),
        u128::from(site.topology_index()),
    )
}

fn place_territory(sense_layer: u128, topology_index: u128) -> Result<u128, DeclaredGeometryError> {
    let eccentricity = sense_layer
        .checked_add(topology_index)
        .ok_or(DeclaredGeometryError::ArithmeticWidth)?;
    let closed_shells = eccentricity
        .checked_mul(
            eccentricity
                .checked_add(1)
                .ok_or(DeclaredGeometryError::ArithmeticWidth)?,
        )
        .ok_or(DeclaredGeometryError::ArithmeticWidth)?
        / 2;
    closed_shells
        .checked_add(topology_index)
        .and_then(|value| value.checked_add(1))
        .ok_or(DeclaredGeometryError::ArithmeticWidth)
}

/// `C(site) = base * A(site)`: the authored base capacitance of one unit patch
/// of membrane times the site's own declared territory in unit patches.
pub(crate) fn membrane_capacitance_from_declared_geometry(
    base_picofarads: ExactRational,
    site: &NeuronSourceSite,
) -> Result<MembraneCapacitance, DeclaredGeometryError> {
    let territory = declared_geometric_territory(site)?;
    let territory = i128::try_from(territory).map_err(|_| DeclaredGeometryError::ArithmeticWidth)?;
    let picofarads = base_picofarads
        .checked_mul(ExactRational::integer(territory))
        .map_err(DeclaredGeometryError::ExactRational)?;
    MembraneCapacitance::new(picofarads).map_err(DeclaredGeometryError::Membrane)
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::neuron_source_anchor::PhysicalSourceSense;

    fn base() -> ExactRational {
        ExactRational::integer(1)
    }

    #[test]
    fn territory_is_the_closed_taxicab_triangle_of_the_declared_place() {
        // Counted directly: every declared place of strictly smaller
        // eccentricity, plus the places up to this one on its own shell.
        for sense_layer in 0..6_u128 {
            for topology_index in 0..40_u128 {
                let eccentricity = sense_layer + topology_index;
                let mut counted = 0_u128;
                for other_layer in 0..=eccentricity {
                    for other_index in 0..=eccentricity {
                        let other = other_layer + other_index;
                        if other < eccentricity
                            || (other == eccentricity && other_index <= topology_index)
                        {
                            counted += 1;
                        }
                    }
                }
                assert_eq!(place_territory(sense_layer, topology_index).unwrap(), counted);
            }
        }
    }

    #[test]
    fn distinct_declared_places_never_share_a_territory_or_a_capacitance() {
        let mut seen = std::collections::BTreeMap::new();
        for sense_layer in 0..6_u128 {
            for topology_index in 0..256_u128 {
                let territory = place_territory(sense_layer, topology_index).unwrap();
                assert!(territory >= 1);
                assert!(
                    seen.insert(territory, (sense_layer, topology_index)).is_none(),
                    "territory {territory} repeated at ({sense_layer}, {topology_index})"
                );
            }
        }
    }

    #[test]
    fn capacitance_is_the_authored_base_times_the_declared_territory() {
        let site = NeuronSourceSite::fixture(0);
        assert_eq!(declared_geometric_territory(&site).unwrap(), 1);
        assert_eq!(
            membrane_capacitance_from_declared_geometry(base(), &site)
                .unwrap()
                .picofarads()
                .parts(),
            (1, 1)
        );
        // Sight layer 0: territories are the triangular numbers
        // (t + 1)(t + 2)/2 — 1, 3, 6, 10, ... unit patches.
        for topology_index in 0..8_u32 {
            let site = NeuronSourceSite::fixture(topology_index);
            let expected =
                u128::from(topology_index + 1) * u128::from(topology_index + 2) / 2;
            assert_eq!(declared_geometric_territory(&site).unwrap(), expected);
            assert_eq!(
                membrane_capacitance_from_declared_geometry(base(), &site)
                    .unwrap()
                    .picofarads()
                    .parts(),
                (i128::try_from(expected).unwrap(), 1)
            );
        }
    }

    #[test]
    fn a_different_sense_layer_at_the_same_topology_index_is_a_different_membrane() {
        let sight = NeuronSourceSite::fixture(0);
        let sound = NeuronSourceSite::fixture_in_sense(PhysicalSourceSense::Sound, 0);
        assert_ne!(
            declared_geometric_territory(&sight).unwrap(),
            declared_geometric_territory(&sound).unwrap()
        );
    }

    #[test]
    fn the_widest_declared_place_still_derives_an_exact_capacitance() {
        let site = NeuronSourceSite::fixture(u32::MAX);
        let capacitance = membrane_capacitance_from_declared_geometry(base(), &site).unwrap();
        assert!(capacitance.picofarads().parts().0 > 0);
    }
}
