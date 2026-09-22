//! kinematics.rs -- Compiled 2D floor disc kinematics, spatial region containment,
//! and collision validation for the Guala embodiment world loop.
//!
//! Replaces the O(N^2) pure-Python generator loops in `_validate_world`
//! with SIMD/cache-friendly integer arithmetic.
//!
//! Laws preserved:
//!   - Exact Euclidean floor disc overlap: (dx^2 + dy^2) < (r1 + r2)^2
//!   - Region floor disc containment:
//!       pos.z == min_z && min_x + r <= pos.x <= max_x - r && min_y + r <= pos.y <= max_y - r
//!   - Bed exemptions:
//!       - Self-body (Guala) lying on her bed does not trigger collision
//!       - Items on bed (pillow, blanket) do not collide with bed
//!   - Exact identical error message strings on physical violations.

use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;

#[derive(Clone, Debug)]
pub struct RegionBounds {
    pub min_x: i64,
    pub max_x: i64,
    pub min_y: i64,
    pub max_y: i64,
    pub min_z: i64,
    pub region_id: String,
}

#[derive(Clone, Copy, Debug)]
pub struct Disc {
    pub x: i64,
    pub y: i64,
    pub z: i64,
    pub radius: i64,
}

#[inline]
fn disc_in_region(disc: &Disc, region: &RegionBounds) -> bool {
    disc.z == region.min_z
        && region.min_x + disc.radius <= disc.x
        && disc.x <= region.max_x - disc.radius
        && region.min_y + disc.radius <= disc.y
        && disc.y <= region.max_y - disc.radius
}

#[inline]
fn find_region(disc: &Disc, regions: &[RegionBounds]) -> Option<usize> {
    let mut matched: Option<usize> = None;
    for (idx, region) in regions.iter().enumerate() {
        if disc_in_region(disc, region) {
            if matched.is_some() {
                // If more than one region contains the disc, it's ambiguous -> None
                return None;
            }
            matched = Some(idx);
        }
    }
    matched
}

#[inline]
fn discs_overlap(d1: &Disc, d2: &Disc) -> bool {
    let dx = d1.x - d2.x;
    let dy = d1.y - d2.y;
    let r_sum = d1.radius + d2.radius;
    (dx * dx + dy * dy) < (r_sum * r_sum)
}

/// Validate 2D disc kinematics, region containment, and pairwise non-intersection.
///
/// Returns `Ok(())` on valid physical state, or `Err(PyValueError)` matching
/// canonical Python error strings on boundary violations.
#[pyfunction]
pub fn validate_world_kinematics_native(
    py: Python<'_>,
    raw_regions: Vec<(i64, i64, i64, i64, i64, String)>,
    raw_placed: Vec<(i64, i64, i64, i64, bool)>,   // (x, y, z, radius, is_bed)
    raw_occupied: Vec<(i64, i64, i64, i64, bool)>, // (x, y, z, carried_radius, is_self)
    room_id: String,
) -> PyResult<()> {
    py.allow_threads(|| {
        let regions: Vec<RegionBounds> = raw_regions
            .into_iter()
            .map(|(min_x, max_x, min_y, max_y, min_z, region_id)| RegionBounds {
                min_x,
                max_x,
                min_y,
                max_y,
                min_z,
                region_id,
            })
            .collect();

        // 1. Placed objects containment
        let mut placed_regions: Vec<usize> = Vec::with_capacity(raw_placed.len());
        for (x, y, z, radius, _) in &raw_placed {
            let disc = Disc {
                x: *x,
                y: *y,
                z: *z,
                radius: *radius,
            };
            match find_region(&disc, &regions) {
                Some(reg_idx) => placed_regions.push(reg_idx),
                None => {
                    return Err(PyValueError::new_err(
                        "object position is outside room geometry",
                    ));
                }
            }
        }

        // 2. Bodies containment & self-body room check
        let mut occupied_regions: Vec<usize> = Vec::with_capacity(raw_occupied.len());
        for (x, y, z, carried_radius, is_self) in &raw_occupied {
            let disc = Disc {
                x: *x,
                y: *y,
                z: *z,
                radius: *carried_radius,
            };
            match find_region(&disc, &regions) {
                Some(reg_idx) => {
                    if *is_self && regions[reg_idx].region_id != room_id {
                        return Err(PyValueError::new_err(
                            "self body current region changed",
                        ));
                    }
                    occupied_regions.push(reg_idx);
                }
                None => {
                    return Err(PyValueError::new_err(
                        "body and held object are outside room geometry",
                    ));
                }
            }
        }

        // 3. Body-body non-intersection
        let n_occ = raw_occupied.len();
        for i in 0..n_occ {
            let d1 = Disc {
                x: raw_occupied[i].0,
                y: raw_occupied[i].1,
                z: raw_occupied[i].2,
                radius: raw_occupied[i].3,
            };
            for j in (i + 1)..n_occ {
                if occupied_regions[i] == occupied_regions[j] {
                    let d2 = Disc {
                        x: raw_occupied[j].0,
                        y: raw_occupied[j].1,
                        z: raw_occupied[j].2,
                        radius: raw_occupied[j].3,
                    };
                    if discs_overlap(&d1, &d2) {
                        return Err(PyValueError::new_err("body geometries intersect"));
                    }
                }
            }
        }

        // 4. Body-placed non-intersection
        let n_placed = raw_placed.len();
        for i in 0..n_occ {
            let d_body = Disc {
                x: raw_occupied[i].0,
                y: raw_occupied[i].1,
                z: raw_occupied[i].2,
                radius: raw_occupied[i].3,
            };
            let is_self = raw_occupied[i].4;
            for j in 0..n_placed {
                let is_bed = raw_placed[j].4;
                if is_bed && is_self {
                    continue; // Guala lies on her bed
                }
                if occupied_regions[i] == placed_regions[j] {
                    let d_placed = Disc {
                        x: raw_placed[j].0,
                        y: raw_placed[j].1,
                        z: raw_placed[j].2,
                        radius: raw_placed[j].3,
                    };
                    if discs_overlap(&d_body, &d_placed) {
                        return Err(PyValueError::new_err(
                            "body or held object intersects placed object geometry",
                        ));
                    }
                }
            }
        }

        // 5. Placed-placed non-intersection
        for i in 0..n_placed {
            let is_bed_i = raw_placed[i].4;
            let d1 = Disc {
                x: raw_placed[i].0,
                y: raw_placed[i].1,
                z: raw_placed[i].2,
                radius: raw_placed[i].3,
            };
            for j in (i + 1)..n_placed {
                let is_bed_j = raw_placed[j].4;
                if is_bed_i || is_bed_j {
                    continue; // pillow and blanket lie on her bed
                }
                if placed_regions[i] == placed_regions[j] {
                    let d2 = Disc {
                        x: raw_placed[j].0,
                        y: raw_placed[j].1,
                        z: raw_placed[j].2,
                        radius: raw_placed[j].3,
                    };
                    if discs_overlap(&d1, &d2) {
                        return Err(PyValueError::new_err(
                            "placed objects intersect each other",
                        ));
                    }
                }
            }
        }

        Ok(())
    })
}

pub fn register(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(validate_world_kinematics_native, m)?)?;
    Ok(())
}

