"""Bounded diagnostic of repeated rational rotations, NOT body integration.

Run standalone. No application/world/network imports, files, processes or
production state. Each test rotation is exactly orthogonal. Its Cayley angle
is 2*atan(rate*dt/2), not exactly rate*dt: this probe does NOT certify the time
integration accuracy of Cayley stepping. It measures representation growth.
"""

from fractions import Fraction as F
import json

from dsf_ai_service.substrate.body_surface_contact import ExactVector3, MAX_CONTACT_RATIONAL_BITS
from dsf_ai_service.substrate.functional_body_kinematics import RigidBasis


def vector(x=0, y=0, z=0):
    return ExactVector3(F(x), F(y), F(z))


def probe(rate, duration, maximum_compositions=128):
    half = rate * duration / 2
    cosine = (1 - half * half) / (1 + half * half)
    sine = 2 * half / (1 + half * half)
    step = RigidBasis(vector(cosine, sine), vector(-sine, cosine), vector(0, 0, 1))
    current = RigidBasis(vector(1), vector(0, 1), vector(0, 0, 1))
    for count in range(1, maximum_compositions + 1):
        try:
            successor = RigidBasis(current.to_parent(step.x), current.to_parent(step.y),
                                   current.to_parent(step.z))
        except ValueError as error:
            if "exact rational bit boundary" not in str(error):
                raise
            return {
                "angular_rate_radians_per_second": str(rate),
                "nominal_step_seconds": str(duration),
                "first_rejected_composition": count,
                "accepted_compositions": count - 1,
                "nominal_elapsed_before_refusal_seconds": str(duration * (count - 1)),
                "scalar_bound_bits": MAX_CONTACT_RATIONAL_BITS,
                "status": "exact_orientation_storage_overflow",
            }
        current = successor
    return {
        "angular_rate_radians_per_second": str(rate),
        "nominal_step_seconds": str(duration),
        "accepted_compositions": maximum_compositions,
        "status": "no_overflow_within_diagnostic_bound",
    }


if __name__ == "__main__":
    for rate in (F(1, 10), F(1), F(10)):
        for duration in (F(1, 1000), F(1, 100), F(1, 4)):
            print(json.dumps(probe(rate, duration), sort_keys=True), flush=True)
