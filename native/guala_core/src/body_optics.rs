//! Same-law body optical primitive intervals. No DSF, retained state or world writes.
//! Local coordinates are supplied by the original NumPy transforms. Ordinary
//! IEEE operations only: no fast-math, FMA, approximate roots or hit epsilon.

use pyo3::buffer::{PyBuffer, ReadOnlyCell};
use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;
use pyo3::types::PyBytes;

const SPHERE: u8 = 2;
const CAPSULE: u8 = 3;
const ELLIPSOID: u8 = 4;
const CYLINDER: u8 = 5;
const BOX: u8 = 6;
const MAX_ROWS: usize = 262144;

fn bad(message: &str) -> PyErr { PyValueError::new_err(message.to_owned()) }

// NumPy minimum/maximum propagate NaN and select the second operand on ties.
#[inline] fn minimum(a: f64, b: f64) -> f64 {
    if a.is_nan() || a < b { a } else { b }
}
#[inline] fn maximum(a: f64, b: f64) -> f64 {
    if a.is_nan() || a > b { a } else { b }
}
#[inline] fn dot(a: &[f64; 3], b: &[f64; 3], length: usize) -> f64 {
    let mut value = 0.0;
    for i in 0..length { value += a[i] * b[i]; }
    value
}
#[derive(Clone, Copy)]
struct Quadratic { a: f64, b: f64, square: f64 }
impl Quadratic {
    fn ray(o: &[f64; 3], v: &[f64; 3], length: usize) -> Self {
        Self { a: dot(v, v, length), b: dot(o, v, length), square: dot(o, o, length) }
    }
    fn interval(self, radius: f64) -> (f64, f64) {
        let c = self.square - radius * radius;
        let det = self.b * self.b - self.a * c;
        let root = maximum(det, 0.0).sqrt();
        let q = -self.b - root.copysign(self.b);
        let x = if self.a != 0.0 { q / self.a } else { 0.0 };
        let y = if q != 0.0 { c / q } else { x };
        if det < 0.0 || (self.a == 0.0 && c > 0.0) {
            (f64::INFINITY, f64::NEG_INFINITY)
        } else if self.a == 0.0 && c <= 0.0 {
            (f64::NEG_INFINITY, f64::INFINITY)
        } else { (minimum(x, y), maximum(x, y)) }
    }
}
#[inline]
fn slab(o: f64, v: f64, half: f64) -> (f64, f64) {
    if v == 0.0 {
        if o.abs() > half { (f64::INFINITY, f64::NEG_INFINITY) }
        else { (f64::NEG_INFINITY, f64::INFINITY) }
    } else {
        let a = (-half - o) / v;
        let b = (half - o) / v;
        (minimum(a, b), maximum(a, b))
    }
}

struct Common {
    radial: Option<Quadratic>,
    ends: Option<[Quadratic; 2]>,
}
impl Common {
    fn new(kind: u8, o: &[f64; 3], v: &[f64; 3], half: f64) -> Self {
        let radial = match kind {
            SPHERE => Some(Quadratic::ray(o, v, 3)),
            CAPSULE | CYLINDER => Some(Quadratic::ray(o, v, 2)),
            _ => None,
        };
        let ends = if kind == CAPSULE {
            let mut a = *o;
            let mut b = *o;
            a[2] -= -1.0 * half;
            b[2] -= half;
            Some([Quadratic::ray(&a, v, 3), Quadratic::ray(&b, v, 3)])
        } else { None };
        Self { radial, ends }
    }
    fn interval(&self, kind: u8, o: &[f64; 3], v: &[f64; 3],
                size: &[f64; 3]) -> (f64, f64, usize) {
        match kind {
            SPHERE => { let (a, b) = self.radial.unwrap().interval(size[0]); (a, b, 0) }
            ELLIPSOID => {
                let scaled_o = std::array::from_fn(|i| o[i] / size[i]);
                let scaled_v = std::array::from_fn(|i| v[i] / size[i]);
                let (a, b) = Quadratic::ray(&scaled_o, &scaled_v, 3).interval(1.0);
                (a, b, 0)
            }
            BOX => {
                let (mut lo, mut hi) = slab(o[0], v[0], size[0]);
                let mut axis = 0;
                for i in 1..3 {
                    let (a, b) = slab(o[i], v[i], size[i]);
                    if a > lo { axis = i; }
                    lo = maximum(lo, a);
                    hi = minimum(hi, b);
                }
                (lo, hi, axis)
            }
            CAPSULE | CYLINDER => {
                let (radial, radial_hi) = self.radial.unwrap().interval(size[0]);
                let (cap, cap_hi) = slab(o[2], v[2], size[1]);
                let (mut lo, mut hi) = (maximum(radial, cap), minimum(radial_hi, cap_hi));
                if !(lo <= hi) { lo = f64::INFINITY; hi = f64::NEG_INFINITY; }
                if let Some(ends) = self.ends {
                    for end in ends {
                        let (a, b) = end.interval(size[0]);
                        lo = minimum(lo, a);
                        hi = maximum(hi, b);
                    }
                }
                (lo, hi, usize::from(cap >= radial))
            }
            _ => unreachable!(),
        }
    }
}

struct Records<'a> { cells: &'a [ReadOnlyCell<f64>], rows: usize }
fn rows(buffer: &PyBuffer<f64>) -> PyResult<usize> {
    match buffer.shape() {
        [3] => Ok(1),
        [n, 3] if *n > 0 && *n <= MAX_ROWS => Ok(*n),
        _ => Err(bad("bounded float64 records with three components required")),
    }
}
impl<'a> Records<'a> {
    fn new(buffer: &'a PyBuffer<f64>, py: Python<'a>, n: usize) -> PyResult<Self> {
        let count = rows(buffer)?;
        if count != 1 && count != n { return Err(bad("aligned or shared primitive records required")); }
        let cells = buffer.as_slice(py).ok_or_else(|| bad("contiguous native float64 records required"))?;
        if cells.iter().any(|v| !v.get().is_finite()) { return Err(bad("finite primitive records required")); }
        Ok(Self { cells, rows: count })
    }
    fn get(&self, row: usize) -> [f64; 3] {
        let offset = if self.rows == 1 { 0 } else { 3 * row };
        std::array::from_fn(|i| self.cells[offset+i].get())
    }
    fn dimensions(&self, kind: u8) -> PyResult<()> {
        let count = match kind { SPHERE => 1, CAPSULE | CYLINDER => 2, _ => 3 };
        for row in 0..self.rows {
            if self.get(row)[..count].iter().any(|v| *v <= 0.0) {
                return Err(bad("positive primitive dimensions required"));
            }
        }
        Ok(())
    }
}

#[pyfunction]
#[pyo3(signature = (kind, origins, velocities, dimensions, paired=None, normals=false))]
fn body_primitive_intervals<'py>(
    py: Python<'py>, kind: u8, origins: PyBuffer<f64>, velocities: PyBuffer<f64>,
    dimensions: PyBuffer<f64>, paired: Option<PyBuffer<f64>>, normals: bool,
) -> PyResult<Bound<'py, PyBytes>> {
    if !matches!(kind, SPHERE | CAPSULE | ELLIPSOID | CYLINDER | BOX) {
        return Err(bad("finite primitive required; no silent geometry exclusion"));
    }
    let n = rows(&velocities)?;
    let o = Records::new(&origins, py, n)?;
    let v = Records::new(&velocities, py, n)?;
    let size = Records::new(&dimensions, py, n)?;
    size.dimensions(kind)?;
    let other = paired.as_ref().map(|b| Records::new(b, py, n)).transpose()?;
    if let Some(other) = &other { other.dimensions(kind)?; }
    if normals && other.is_some() { return Err(bad("one actual surface per normal request required")); }
    if kind == CAPSULE {
        if let Some(other) = &other {
            for row in 0..n {
                if size.get(row)[1] != other.get(row)[1] {
                    return Err(bad("paired capsule radial dilation requires equal half-lengths"));
                }
            }
        }
    }
    let width = if normals { 8 } else { 2 };
    let count = if other.is_some() { 2 } else { 1 };
    // Bounds above prove at most 16 MiB. The GIL remains held: borrowed cells
    // cannot be changed by Python callbacks, and no mutable native alias exists.
    PyBytes::new_with(py, n * count * width * 8, |output| {
        for row in 0..n {
            let origin = o.get(row);
            let velocity = v.get(row);
            let first = size.get(row);
            let common = Common::new(kind, &origin, &velocity, first[1]);
            for which in 0..count {
                let s = if which == 0 { first } else { other.as_ref().unwrap().get(row) };
                let (lo, hi, feature) = common.interval(kind, &origin, &velocity, &s);
                let mut values = [0.0; 8];
                values[0] = lo;
                values[1] = hi;
                if normals {
                    if !lo.is_finite() || lo <= 0.0 || hi < lo {
                        return Err(bad("finite exterior central surface hit required"));
                    }
                    let point: [f64; 3] = std::array::from_fn(|i| origin[i] + lo * velocity[i]);
                    let mut outward = [0.0; 3];
                    match kind {
                        SPHERE => { for i in 0..3 { outward[i] = point[i] / s[0]; } }
                        ELLIPSOID => { for i in 0..3 { outward[i] = point[i] / (s[i] * s[i]); } }
                        CAPSULE => {
                            outward = point;
                            outward[2] -= minimum(maximum(point[2], -s[1]), s[1]);
                            for value in &mut outward { *value /= s[0]; }
                        }
                        CYLINDER => {
                            if feature == 1 { outward[2] = -velocity[2].signum(); }
                            else { outward[0] = point[0]/s[0]; outward[1] = point[1]/s[0]; }
                        }
                        BOX => { outward[feature] = -velocity[feature].signum(); }
                        _ => unreachable!(),
                    }
                    values[2..5].copy_from_slice(&point);
                    values[5..8].copy_from_slice(&outward);
                }
                let offset = (which*n+row)*width*8;
                for (i, value) in values[..width].iter().enumerate() {
                    output[offset+i*8..offset+(i+1)*8].copy_from_slice(&value.to_ne_bytes());
                }
            }
        }
        Ok(())
    })
}

pub fn register(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(body_primitive_intervals, m)?)?;
    Ok(())
}
