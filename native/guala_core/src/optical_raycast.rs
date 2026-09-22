//! optical_raycast.rs -- Native (Rust) hot-path optical raycasting & lighting for Guala's focal retina.
//!
//! Evaluates:
//!   1. 19,200 focal rays against room boundary planes and 3D rotated bounding boxes.
//!   2. Direct illumination & shadow ray intersection against point lamps and sun through windows.
//!   3. C-accelerated 6-band fraction tuple packing into the retinal pixel buffer.
//!   4. Ultra-fast fraction-to-float64 extraction for cognitive processing via pointer-cached table.
//!
//! Exact mathematical port of dsf_ai_service/substrate/w1_physical_receptors.py.
//! Thread-safe, lock-free, GIL-released where appropriate.

use pyo3::prelude::*;
use pyo3::types::{PyList, PyTuple};
use std::collections::HashMap;

pub const LAMP_REFERENCE_MM: f64 = 1000.0;
pub const LAMP_NEAR_GAIN: f64 = 4.0;

/// Single box definition passed from Python:
/// (centre_x, centre_y, centre_z, size_x, size_y, size_z, heading_rad, box_id_index)
pub type BoxInput = (f64, f64, f64, f64, f64, f64, f64, i64);

/// Lamp definition:
/// (x, y, z, radius_mm, [ppm0..5], source_id)
pub type LampInput = (f64, f64, f64, f64, Vec<f64>, Option<String>);

/// Window definition: (plane_val, axis, from_mm, to_mm, sill_mm, top_mm)
pub type WindowInput = (f64, usize, f64, f64, f64, f64);

/// Sun definition: (x, y, z, [ppm0..5], windows)
pub type SunInput = (f64, f64, f64, Vec<f64>, Vec<WindowInput>);

/// Occluder definition:
/// (ox, oy, oz, r, oid, Option<(hx, hy, hz, ca, sa)>)
pub type OccluderInput = (f64, f64, f64, f64, Option<String>, Option<(f64, f64, f64, f64, f64)>);

/// Intersect a ray against an axis-aligned box in local coordinates.
#[inline(always)]
fn intersect_box_slabs(
    o_local: &[f64; 3],
    d_local: &[f64; 3],
    half: &[f64; 3],
    best_t: f64,
) -> Option<(f64, usize, f64)> {
    let mut near = f64::NEG_INFINITY;
    let mut far = f64::INFINITY;
    let mut entry_axis = 0usize;

    for axis in 0..3 {
        let d = d_local[axis];
        let o = o_local[axis];
        let h = half[axis];

        if d.abs() < 1e-12 {
            if o.abs() > h {
                return None;
            }
        } else {
            let inv_d = 1.0 / d;
            let mut t1 = (-h - o) * inv_d;
            let mut t2 = (h - o) * inv_d;
            if t1 > t2 {
                std::mem::swap(&mut t1, &mut t2);
            }
            if t1 > near {
                near = t1;
                entry_axis = axis;
            }
            if t2 < far {
                far = t2;
            }
            if near > far || far < 1e-6 {
                return None;
            }
        }
    }

    if far >= near && near > 1e-6 && near < best_t {
        let p_axis = o_local[entry_axis] + d_local[entry_axis] * near;
        let mut sign = if p_axis < 0.0 { -1.0 } else { 1.0 };
        if p_axis.abs() < 1e-12 {
            sign = 1.0;
        }
        Some((near, entry_axis, sign))
    } else {
        None
    }
}

/// Core raycast implementation over N rays.
#[pyfunction]
pub fn cast_focal_rays_native(
    py: Python<'_>,
    eye: (f64, f64, f64),
    heading_rad: f64,
    pitch_rad: f64,
    h_offsets: Vec<f64>,
    v_offsets: Vec<f64>,
    room_bounds: (f64, f64, f64, f64, f64, f64), // min_x, max_x, min_y, max_y, min_z, max_z
    boxes: Vec<BoxInput>,
) -> PyResult<(
    Vec<f64>, // best distances
    Vec<f64>, // box_depth (distance to box hit, or inf)
    Vec<f64>, // point_x
    Vec<f64>, // point_y
    Vec<f64>, // point_z
    Vec<f64>, // normal_x
    Vec<f64>, // normal_y
    Vec<f64>, // normal_z
    Vec<i64>, // face index (0..5 for planes, or 6 for box)
    Vec<i64>, // box index hit (-1 if room plane hit)
)> {
    let count = h_offsets.len();
    if v_offsets.len() != count {
        return Err(pyo3::exceptions::PyValueError::new_err(
            "h_offsets and v_offsets must have identical length",
        ));
    }

    let (min_x, max_x, min_y, max_y, min_z, max_z) = room_bounds;
    let (eye_x, eye_y, eye_z) = eye;

    // Room boundary planes: (plane_val, axis, normal_x, normal_y, normal_z)
    let planes: [(f64, usize, f64, f64, f64); 6] = [
        (min_z, 2, 0.0, 0.0, 1.0),  // 0: floor
        (max_z, 2, 0.0, 0.0, -1.0), // 1: ceiling
        (min_x, 0, 1.0, 0.0, 0.0),  // 2: x-min
        (max_x, 0, -1.0, 0.0, 0.0), // 3: x-max
        (min_y, 1, 0.0, 1.0, 0.0),  // 4: y-min
        (max_y, 1, 0.0, -1.0, 0.0), // 5: y-max
    ];

    py.allow_threads(|| {
        let mut best_distances = vec![f64::INFINITY; count];
        let mut box_depths = vec![f64::INFINITY; count];
        let mut point_x = vec![eye_x; count];
        let mut point_y = vec![eye_y; count];
        let mut point_z = vec![eye_z; count];
        let mut normal_x = vec![0.0f64; count];
        let mut normal_y = vec![0.0f64; count];
        let mut normal_z = vec![0.0f64; count];
        let mut face_indices = vec![-1i64; count];
        let mut box_indices = vec![-1i64; count];

        // Precompute ray directions:
        let mut rays_d = Vec::with_capacity(count);
        for i in 0..count {
            let h = heading_rad + h_offsets[i];
            let v = pitch_rad + v_offsets[i];
            let cos_v = v.cos();
            let dx = cos_v * h.cos();
            let dy = cos_v * h.sin();
            let dz = v.sin();
            rays_d.push([dx, dy, dz]);
        }

        // 1. Intersect room boundary planes
        for i in 0..count {
            let d = &rays_d[i];
            let mut best_t = f64::INFINITY;
            let mut best_face = -1i64;
            let mut best_n = (0.0, 0.0, 0.0);

            for (p_idx, &(plane_val, axis, nx, ny, nz)) in planes.iter().enumerate() {
                let dir_comp = d[axis];
                if dir_comp.abs() > 1e-9 {
                    let orig_comp = match axis {
                        0 => eye_x,
                        1 => eye_y,
                        _ => eye_z,
                    };
                    let t = (plane_val - orig_comp) / dir_comp;
                    if t > 1e-6 && t < best_t {
                        best_t = t;
                        best_face = p_idx as i64;
                        best_n = (nx, ny, nz);
                    }
                }
            }

            if best_face >= 0 {
                best_distances[i] = best_t;
                face_indices[i] = best_face;
                normal_x[i] = best_n.0;
                normal_y[i] = best_n.1;
                normal_z[i] = best_n.2;
                point_x[i] = eye_x + d[0] * best_t;
                point_y[i] = eye_y + d[1] * best_t;
                point_z[i] = eye_z + d[2] * best_t;
            }
        }

        // 2. Intersect 3D boxes
        for &(cx, cy, cz, sx, sy, sz, angle, box_idx) in &boxes {
            let half = [sx * 0.5, sy * 0.5, sz * 0.5];
            let ca = angle.cos();
            let sa = angle.sin();

            let ox = eye_x - cx;
            let oy = eye_y - cy;
            let oz = eye_z - cz;

            let o_local = [ca * ox + sa * oy, -sa * ox + ca * oy, oz];

            for i in 0..count {
                let d = &rays_d[i];
                let d_local = [ca * d[0] + sa * d[1], -sa * d[0] + ca * d[1], d[2]];

                let cur_best = best_distances[i];
                if let Some((near, entry_axis, sign)) =
                    intersect_box_slabs(&o_local, &d_local, &half, cur_best)
                {
                    best_distances[i] = near;
                    box_depths[i] = near;
                    box_indices[i] = box_idx;
                    face_indices[i] = 6; // box surface indicator

                    point_x[i] = eye_x + d[0] * near;
                    point_y[i] = eye_y + d[1] * near;
                    point_z[i] = eye_z + d[2] * near;

                    // Transform local normal to world
                    let mut nl = [0.0f64; 3];
                    nl[entry_axis] = sign;
                    normal_x[i] = ca * nl[0] - sa * nl[1];
                    normal_y[i] = sa * nl[0] + ca * nl[1];
                    normal_z[i] = nl[2];
                }
            }
        }

        Ok((
            best_distances,
            box_depths,
            point_x,
            point_y,
            point_z,
            normal_x,
            normal_y,
            normal_z,
            face_indices,
            box_indices,
        ))
    })
}

/// Native direct lighting and shadow ray intersection kernel.
/// Evaluates point lamps (with inverse-square falloff and near gain) and sun rays through windows.
#[pyfunction]
pub fn compute_direct_lighting_native(
    py: Python<'_>,
    point_x: Vec<f64>,
    point_y: Vec<f64>,
    point_z: Vec<f64>,
    normal_x: Vec<f64>,
    normal_y: Vec<f64>,
    normal_z: Vec<f64>,
    hit: Vec<bool>,
    sources: Vec<i64>,
    lamps: Vec<LampInput>,
    suns: Vec<SunInput>,
    occluders: Vec<OccluderInput>,
) -> PyResult<Vec<Vec<f64>>> {
    let count = point_x.len();
    if count == 0 {
        return Ok(vec![Vec::new(); 6]);
    }

    py.allow_threads(|| {
        let mut direct = vec![vec![0.0f64; count]; 6];

        for i in 0..count {
            if !hit[i] {
                continue;
            }
            let px = point_x[i];
            let py = point_y[i];
            let pz = point_z[i];
            let nx = normal_x[i];
            let ny = normal_y[i];
            let nz = normal_z[i];
            let src_k = sources[i];

            // 1. Point lamps
            for (lx_pos, ly_pos, lz_pos, radius, ppm, ref skip_oid) in &lamps {
                let vx = lx_pos - px;
                let vy = ly_pos - py;
                let vz = lz_pos - pz;
                let dist = (vx * vx + vy * vy + vz * vz).sqrt();
                if dist <= *radius {
                    continue;
                }
                let safe = if dist > 0.0 { dist } else { 1.0 };
                let lx = vx / safe;
                let ly = vy / safe;
                let lz = vz / safe;
                let reach = dist - radius;
                let inv_safe = LAMP_REFERENCE_MM / safe;
                let falloff = (inv_safe * inv_safe).min(LAMP_NEAR_GAIN);

                let factor = nx * lx + ny * ly + nz * lz;
                if factor <= 0.0 {
                    continue;
                }

                // Occluders shadow check
                let mut shadowed = false;
                for (k, (ox, oy, oz, r, ref oid, ref box_opt)) in occluders.iter().enumerate() {
                    if let Some(ref s_id) = skip_oid {
                        if let Some(ref o_id) = oid {
                            if s_id == o_id {
                                continue;
                            }
                        }
                    }
                    let ovx = ox - px;
                    let ovy = oy - py;
                    let ovz = oz - pz;
                    let u = ovx * lx + ovy * ly + ovz * lz;
                    if u <= 0.0 || u >= reach + r {
                        continue;
                    }
                    let cx = ovx - u * lx;
                    let cy = ovy - u * ly;
                    let cz = ovz - u * lz;
                    if cx * cx + cy * cy + cz * cz > r * r {
                        continue;
                    }
                    if src_k == k as i64 {
                        continue;
                    }
                    match box_opt {
                        None => {
                            if u < reach {
                                shadowed = true;
                                break;
                            }
                        }
                        Some((hx, hy, hz, ca, sa)) => {
                            let rx = -ovx;
                            let ry = -ovy;
                            let rz = -ovz;
                            let o_loc = [ca * rx + sa * ry, -sa * rx + ca * ry, rz];
                            let d_loc = [ca * lx + sa * ly, -sa * lx + ca * ly, lz];
                            let half = [*hx, *hy, *hz];

                            let mut near = f64::NEG_INFINITY;
                            let mut far = f64::INFINITY;
                            let mut ok = true;
                            for axis in 0..3 {
                                let d = d_loc[axis];
                                let o = o_loc[axis];
                                let h = half[axis];
                                if d.abs() < 1e-12 {
                                    if o.abs() > h {
                                        ok = false;
                                        break;
                                    }
                                } else {
                                    let inv_d = 1.0 / d;
                                    let mut t1 = (-h - o) * inv_d;
                                    let mut t2 = (h - o) * inv_d;
                                    if t1 > t2 {
                                        std::mem::swap(&mut t1, &mut t2);
                                    }
                                    if t1 > near {
                                        near = t1;
                                    }
                                    if t2 < far {
                                        far = t2;
                                    }
                                }
                            }
                            if ok && far >= near && near > 1e-6 && near < reach {
                                shadowed = true;
                                break;
                            }
                        }
                    }
                }

                if !shadowed {
                    let gain = falloff * factor;
                    for band in 0..6 {
                        direct[band][i] += ppm[band] * gain;
                    }
                }
            }

            // 2. Sun light through windows
            for (sx_pos, sy_pos, sz_pos, ppm, windows) in &suns {
                let lx = *sx_pos;
                let ly = *sy_pos;
                let lz = *sz_pos;
                let mut reach = f64::INFINITY;
                let mut through = false;

                for &(plane, axis, from_mm, to_mm, sill_mm, top_mm) in windows {
                    let s_axis = if axis == 0 { lx } else { ly };
                    if s_axis.abs() < 1e-9 {
                        continue;
                    }
                    let orig = if axis == 0 { px } else { py };
                    let u = (plane - orig) / s_axis;
                    let along = if axis == 0 { py + ly * u } else { px + lx * u };
                    let height = pz + lz * u;
                    let passes = u > 1e-6
                        && along >= from_mm
                        && along <= to_mm
                        && height >= sill_mm
                        && height <= top_mm
                        && !through;
                    if passes {
                        reach = u;
                        through = true;
                    }
                }

                if !through {
                    continue;
                }

                let factor = nx * lx + ny * ly + nz * lz;
                if factor <= 0.0 {
                    continue;
                }

                let mut shadowed = false;
                for (k, (ox, oy, oz, r, _oid, ref box_opt)) in occluders.iter().enumerate() {
                    let ovx = ox - px;
                    let ovy = oy - py;
                    let ovz = oz - pz;
                    let u = ovx * lx + ovy * ly + ovz * lz;
                    if u <= 0.0 || u >= reach + r {
                        continue;
                    }
                    let cx = ovx - u * lx;
                    let cy = ovy - u * ly;
                    let cz = ovz - u * lz;
                    if cx * cx + cy * cy + cz * cz > r * r {
                        continue;
                    }
                    if src_k == k as i64 {
                        continue;
                    }
                    match box_opt {
                        None => {
                            if u < reach {
                                shadowed = true;
                                break;
                            }
                        }
                        Some((hx, hy, hz, ca, sa)) => {
                            let rx = -ovx;
                            let ry = -ovy;
                            let rz = -ovz;
                            let o_loc = [ca * rx + sa * ry, -sa * rx + ca * ry, rz];
                            let d_loc = [ca * lx + sa * ly, -sa * lx + ca * ly, lz];
                            let half = [*hx, *hy, *hz];

                            let mut near = f64::NEG_INFINITY;
                            let mut far = f64::INFINITY;
                            let mut ok = true;
                            for axis in 0..3 {
                                let d = d_loc[axis];
                                let o = o_loc[axis];
                                let h = half[axis];
                                if d.abs() < 1e-12 {
                                    if o.abs() > h {
                                        ok = false;
                                        break;
                                    }
                                } else {
                                    let inv_d = 1.0 / d;
                                    let mut t1 = (-h - o) * inv_d;
                                    let mut t2 = (h - o) * inv_d;
                                    if t1 > t2 {
                                        std::mem::swap(&mut t1, &mut t2);
                                    }
                                    if t1 > near {
                                        near = t1;
                                    }
                                    if t2 < far {
                                        far = t2;
                                    }
                                }
                            }
                            if ok && far >= near && near > 1e-6 && near < reach {
                                shadowed = true;
                                break;
                            }
                        }
                    }
                }

                if !shadowed {
                    for band in 0..6 {
                        direct[band][i] += ppm[band] * factor;
                    }
                }
            }
        }

        Ok(direct)
    })
}

/// Fast native 6-band fraction tuple packing directly into Python list.
#[pyfunction]
pub fn pack_focal_pixels_native(
    py: Python<'_>,
    pixels_list: &Bound<'_, PyList>,
    indices: Vec<usize>,
    changed_cols: Vec<usize>,
    eight_bit_flat: Vec<usize>, // length = count * 6, interleaved: [col0_band0..5, col1_band0..5, ...]
    eb_fractions: &Bound<'_, PyTuple>, // 256 Fraction objects
) -> PyResult<()> {
    for &col in &changed_cols {
        let site_idx = indices[col];
        let base = col * 6;
        let tup = PyTuple::new(
            py,
            &[
                eb_fractions.get_item(eight_bit_flat[base])?,
                eb_fractions.get_item(eight_bit_flat[base + 1])?,
                eb_fractions.get_item(eight_bit_flat[base + 2])?,
                eb_fractions.get_item(eight_bit_flat[base + 3])?,
                eb_fractions.get_item(eight_bit_flat[base + 4])?,
                eb_fractions.get_item(eight_bit_flat[base + 5])?,
            ],
        )?;
        pixels_list.set_item(site_idx, tup)?;
    }
    Ok(())
}

/// Fast native 6-band fraction tuple packing directly from raw byte buffer into Python list.
#[pyfunction]
pub fn pack_focal_pixels_bytes(
    py: Python<'_>,
    pixels_list: &Bound<'_, PyList>,
    indices: Vec<usize>,
    changed_cols: Vec<usize>,
    eight_bit_bytes: &[u8], // length = count * 6, interleaved: [col0_band0..5, col1_band0..5, ...]
    eb_fractions: &Bound<'_, PyTuple>, // 256 Fraction objects
) -> PyResult<()> {
    for &col in &changed_cols {
        let site_idx = indices[col];
        let base = col * 6;
        let tup = PyTuple::new(
            py,
            &[
                eb_fractions.get_item(eight_bit_bytes[base] as usize)?,
                eb_fractions.get_item(eight_bit_bytes[base + 1] as usize)?,
                eb_fractions.get_item(eight_bit_bytes[base + 2] as usize)?,
                eb_fractions.get_item(eight_bit_bytes[base + 3] as usize)?,
                eb_fractions.get_item(eight_bit_bytes[base + 4] as usize)?,
                eb_fractions.get_item(eight_bit_bytes[base + 5] as usize)?,
            ],
        )?;
        pixels_list.set_item(site_idx, tup)?;
    }
    Ok(())
}

/// Ultra-fast conversion of 19,335 x 6 Python Fraction pixels into a flat float64 buffer.
/// Uses a pointer lookup table for the 256 canonical `_EIGHT_BIT` fractions to avoid Python getattr overhead.
#[pyfunction]
#[pyo3(signature = (pixels_obj, eb_fractions=None))]
pub fn fast_pixels_to_bands_f64(
    _py: Python<'_>,
    pixels_obj: &Bound<'_, PyAny>,
    eb_fractions: Option<&Bound<'_, PyTuple>>,
) -> PyResult<Vec<f64>> {
    let count = pixels_obj.len()?;
    let mut out = Vec::with_capacity(count * 6);

    let mut eb_map = HashMap::with_capacity(256);
    if let Some(eb) = eb_fractions {
        let eb_len = eb.len();
        for k in 0..eb_len {
            let item = eb.get_item(k)?;
            eb_map.insert(item.as_ptr() as usize, (k as f64) / 255.0);
        }
    }

    for i in 0..count {
        let pixel = pixels_obj.get_item(i)?;
        for j in 0..6 {
            let item = pixel.get_item(j)?;
            let ptr = item.as_ptr() as usize;
            if let Some(&val) = eb_map.get(&ptr) {
                out.push(val);
            } else {
                let num: f64 = item.getattr("_numerator")?.extract()?;
                let den: f64 = item.getattr("_denominator")?.extract()?;
                let val = num / den;
                eb_map.insert(ptr, val);
                out.push(val);
            }
        }
    }
    Ok(out)
}

pub fn register(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(cast_focal_rays_native, m)?)?;
    m.add_function(wrap_pyfunction!(compute_direct_lighting_native, m)?)?;
    m.add_function(wrap_pyfunction!(pack_focal_pixels_native, m)?)?;
    m.add_function(wrap_pyfunction!(pack_focal_pixels_bytes, m)?)?;
    m.add_function(wrap_pyfunction!(fast_pixels_to_bands_f64, m)?)?;
    Ok(())
}
