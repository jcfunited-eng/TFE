"""FB-01ah standalone bitwise primitive proof; no pytest or live authority."""
import os
from pathlib import Path
import time
import unittest
import numpy as np
import guala_core
from dsf_ai_service.substrate import functional_body_renderer as current
import functional_body_optics_reference as reference


def prior_batch(kind, sizes, origin, velocity, *, paired=None, normal=False):
    if paired is not None:
        return reference.interval_pair(kind, sizes, paired, origin, velocity)
    return reference._primitive_interval(kind, origin, velocity, sizes[..., 0],
                                         sizes[..., 1], sizes, normal=normal)


class NativePrimitiveTests(unittest.TestCase):
    def exact(self, a, b):
        self.assertEqual(a.shape, b.shape)
        self.assertEqual(a.dtype, b.dtype)
        # Includes signed zero and infinities; no numeric tolerance.
        self.assertEqual(a.tobytes(), b.tobytes())

    def test_loaded_extension_is_the_declared_candidate(self):
        actual = Path(guala_core.__file__).resolve()
        expected = os.environ.get("GUALA_BODY_OPTICS_EXTENSION_ROOT")
        if expected is None:
            self.fail("explicit isolated compiled extension root required for this proof")
        self.assertTrue(actual.is_relative_to(Path(expected).resolve()))
        self.assertTrue(callable(guala_core.body_primitive_intervals))
        print(dict(body_optics_extension=str(actual)), flush=True)

    def test_single_and_paired_intervals_are_bitwise_predecessor(self):
        sizes = {current.SPHERE: (.25, 0., 0.), current.CAPSULE: (.15, .3, 0.),
                 current.CYLINDER: (.2, .3, 0.), current.ELLIPSOID: (.25, .15, .35),
                 current.BOX: (.25, .15, .35)}
        checked = 0
        for kind, size in sizes.items():
            coords = (-.5, -.25, np.nextafter(-.25, 0.), -0., 0.,
                      np.nextafter(.25, 0.), .25, .5)
            origins = np.array([(-2., y, z) for y in coords for z in coords])
            ray_sets = (np.broadcast_to((1., 0., 0.), origins.shape).copy(),
                        np.broadcast_to((0., 0., 1.), origins.shape).copy(),
                        np.broadcast_to((.8, -.03, .01), origins.shape).copy(),
                        np.zeros_like(origins), -origins/np.linalg.norm(origins, axis=1)[:, None])
            for v in ray_sets:
                for o in (origins, origins[0], np.array((-0., 0., -0.))):
                    dimensions = np.broadcast_to(size, v.shape).copy()
                    smaller = dimensions.copy()
                    if kind == current.CAPSULE:
                        smaller[:, 0] *= .8
                    elif kind == current.CYLINDER:
                        smaller[:, :2] *= .8
                    else:
                        smaller *= .8
                    for other in (None, smaller):
                        expected = prior_batch(kind, dimensions, o, v, paired=other)
                        actual = current._interval_batch(kind, dimensions, o, v, paired=other)
                        for a, b in zip(actual, expected):
                            self.exact(a, b)
                            checked += a.size
        print(dict(bitwise_primitive_bound_values=checked), flush=True)

    def test_native_surface_points_normals_are_bitwise_predecessor(self):
        origins = np.array(((-2., .03, .04), (.03, -2., .04), (.03, .04, -2.),
                            (2., .03, .04), (.03, 2., .04), (.03, .04, 2.)))
        velocities = -origins/np.linalg.norm(origins, axis=1)[:, None]
        for kind, size in ((current.SPHERE, (.25, 0., 0.)),
                           (current.CAPSULE, (.15, .3, 0.)),
                           (current.CYLINDER, (.2, .3, 0.)),
                           (current.ELLIPSOID, (.25, .15, .35)),
                           (current.BOX, (.25, .15, .35))):
            sizes = np.array((size,))
            for a, b in zip(current._interval_batch(kind, sizes, origins, velocities, normal=True),
                            prior_batch(kind, sizes, origins, velocities, normal=True)):
                self.exact(a, b)

    def test_finite_input_overflow_preserves_predecessor_bytes(self):
        # Admitted finite inputs may overflow intermediate arithmetic. Preserve
        # the predecessor's result, including NaN bits and infinite exit range.
        with np.errstate(over="ignore", invalid="ignore"):
            o = np.array(((-1e308, 0., 0.),))
            v = np.array(((1., 0., 0.),))
            s = np.array(((.25, 0., 0.),))
            expected = prior_batch(current.SPHERE, s, o, v)
            self.assertTrue(np.isnan(expected[0]).all())
            for a, b in zip(current._interval_batch(current.SPHERE, s, o, v), expected):
                self.exact(a, b)
            s = np.array(((1e308, 1., 1.),))
            o = np.array(((-np.nextafter(1e308, np.inf), 0., 0.),))
            expected = prior_batch(current.BOX, s, o, v, normal=True)
            self.assertTrue(np.isfinite(expected[0]).all())
            self.assertTrue(np.isposinf(expected[1]).all())
            for a, b in zip(current._interval_batch(current.BOX, s, o, v, normal=True),
                            expected):
                self.exact(a, b)

    def test_packed_native_boundary_refuses_before_unbounded_work(self):
        o = np.array(((-2., 0., 0.),))
        v = np.array(((1., 0., 0.),))
        s = np.array(((.25, 0., 0.),))
        native = guala_core.body_primitive_intervals
        with self.assertRaises((ValueError, BufferError)):
            native(current.SPHERE, o.astype(np.float32), v, s)
        with self.assertRaisesRegex(ValueError, "bounded"):
            native(current.SPHERE, o, np.empty((262145, 3)), s)
        with self.assertRaisesRegex(ValueError, "contiguous"):
            native(current.SPHERE, o, np.ones((2, 6))[:, ::2], s)
        with self.assertRaisesRegex(ValueError, "finite"):
            native(current.SPHERE, o*np.nan, v, s)
        with self.assertRaisesRegex(ValueError, "positive"):
            native(current.SPHERE, o, v, -s)
        with self.assertRaisesRegex(ValueError, "one actual surface"):
            native(current.SPHERE, o, v, s, s, True)
        with self.assertRaisesRegex(ValueError, "finite exterior"):
            native(current.SPHERE, np.zeros((1, 3)), v, s, None, True)
        encoded = native(current.SPHERE, o, v, s)
        self.assertIsInstance(encoded, bytes)
        self.assertEqual(len(encoded), 16)
        self.assertFalse(np.frombuffer(encoded, dtype=float).flags.writeable)


if __name__ == "__main__":
    start = time.perf_counter()
    result = unittest.TextTestRunner(verbosity=2).run(
        unittest.defaultTestLoader.loadTestsFromTestCase(NativePrimitiveTests))
    print(dict(native_primitive_proof_s=time.perf_counter()-start), flush=True)
    raise SystemExit(not result.wasSuccessful())
