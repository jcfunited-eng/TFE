"""Pinned python-flint/Arb authority for certified GLEW phase coherence."""

from __future__ import annotations

import functools
import importlib
import importlib.metadata
from dataclasses import dataclass
from fractions import Fraction

from .model import ReceiptError


PYTHON_FLINT_VERSION = "0.9.0"
FLINT_VERSION = "3.6.0"
PYTHON_FLINT_WHEEL_SHA256 = (
    "376b88cacd30612479e839ffdba887599d3f9c8c0e214852bf80bb2b194e4d76"
)


class CertifiedBackendUnavailable(ReceiptError):
    """Certified arithmetic is absent or does not match the pinned authority."""


@dataclass(frozen=True, slots=True)
class CertifiedBall:
    """Canonical outward dyadic enclosure emitted by pinned Arb.

    Each endpoint is encoded as an integer mantissa times two raised to its
    integer exponent.  No decimal conversion or nominal midpoint is involved.
    """

    lower_mantissa: int
    lower_exponent: int
    upper_mantissa: int
    upper_exponent: int
    working_precision_bits: int
    python_flint_version: str = PYTHON_FLINT_VERSION
    flint_version: str = FLINT_VERSION
    wheel_sha256: str = PYTHON_FLINT_WHEEL_SHA256

    def __post_init__(self) -> None:
        if self.working_precision_bits <= 0:
            raise ReceiptError("certified ball precision must be positive")
        lower = Fraction(self.lower_mantissa) * Fraction(2) ** self.lower_exponent
        upper = Fraction(self.upper_mantissa) * Fraction(2) ** self.upper_exponent
        if lower > upper:
            raise ReceiptError("certified ball lower endpoint exceeds upper endpoint")


@functools.lru_cache(maxsize=1)
def _pinned_flint_identity():
    """Resolve and validate the pinned python-flint/FLINT package identity.

    This covers only static, process-lifetime-invariant facts: which module
    is importable and what version metadata it reports.  Those cannot change
    between calls within one process, so this half of the check is safe to
    memoize.  It deliberately excludes the live execution-context check
    (thread count), which must be re-verified on every call -- see
    ``load_pinned_flint`` below.
    """

    try:
        flint = importlib.import_module("flint")
        installed = importlib.metadata.version("python-flint")
    except (ImportError, importlib.metadata.PackageNotFoundError) as exc:
        raise CertifiedBackendUnavailable(
            "python-flint 0.9.0 with bundled FLINT 3.6.0 is required"
        ) from exc
    bundled = getattr(flint, "__FLINT_VERSION__", None)
    if installed != PYTHON_FLINT_VERSION or bundled != FLINT_VERSION:
        raise CertifiedBackendUnavailable(
            "certified backend mismatch: expected python-flint 0.9.0 / FLINT 3.6.0"
        )
    return flint


def load_pinned_flint():
    """Load only the audited backend.  There is deliberately no fallback."""

    flint = _pinned_flint_identity()
    if getattr(flint.ctx, "threads", None) != 1:
        raise CertifiedBackendUnavailable(
            "certified backend requires the mounted single-thread execution context"
        )
    return flint


def arb_fraction(flint, value: Fraction):
    return flint.arb(flint.fmpq(value.numerator, value.denominator))


def canonical_ball(value, precision_bits: int) -> CertifiedBall:
    if not value.is_finite():
        raise ReceiptError("certified result is not finite")
    lower = value.lower()
    upper = value.upper()
    if not lower.is_exact() or not upper.is_exact() or not lower.is_finite() or not upper.is_finite():
        raise ReceiptError("Arb did not return finite exact outward endpoints")
    lower_mantissa, lower_exponent = lower.man_exp()
    upper_mantissa, upper_exponent = upper.man_exp()
    if lower > upper:
        raise ReceiptError("Arb returned reversed outward endpoints")
    return CertifiedBall(
        lower_mantissa=int(lower_mantissa),
        lower_exponent=int(lower_exponent),
        upper_mantissa=int(upper_mantissa),
        upper_exponent=int(upper_exponent),
        working_precision_bits=precision_bits,
    )
