from __future__ import annotations

from array import array
from fractions import Fraction
import hashlib
import sys

import pytest

from dsf_ai_service.guala_physical_sensorium import (
    PhysicalSensorium,
    RETINAL_PORTS,
    compact_signal_body,
    settle_physical_sensorium,
)
from dsf_ai_service.guala_receptor_anatomy import (
    ANATOMY_SHA256,
    PORT_COUNT,
    receptor_anatomy,
)


TIMES = tuple(Fraction(index, 4) for index in range(4))


def _values(width: int, value: Fraction | float = Fraction(0)) -> tuple:
    return (value,) * width


def _constant(**changes) -> PhysicalSensorium:
    values = {
        "frame_count": len(TIMES),
        "retina": _values(RETINAL_PORTS),
        "legacy_ears": _values(2),
        "cochleae": _values(32),
        "touch": _values(28),
        "smell": _values(8),
        "taste": _values(5),
        "displacement": _values(4),
        "articulation": _values(4),
        "thermal": _values(2),
    }
    values.update(changes)
    return PhysicalSensorium.constant(**values)


def test_cached_anatomy_is_exact_and_zero_replacement_is_byte_identical() -> None:
    anatomy = receptor_anatomy()
    assert receptor_anatomy() is anatomy
    assert anatomy.python_callback_count == 0
    assert anatomy.port_count == PORT_COUNT
    assert hashlib.sha256(bytes(anatomy.as_bytes())).hexdigest() == ANATOMY_SHA256

    episode = settle_physical_sensorium(
        assembly_id="guala-production-declared-anatomy",
        source_times=TIMES,
        sensorium=_constant(),
    )
    assert episode.python_callback_count == 0
    assert bytes(episode.as_bytes()) == bytes(anatomy.as_bytes())


def test_compact_body_has_explicit_anatomical_order() -> None:
    sensorium = _constant(
        retina=_values(RETINAL_PORTS, 1),
        legacy_ears=_values(2, 2),
        cochleae=_values(32, 3),
        touch=_values(28, 4),
        smell=_values(8, 5),
        taste=_values(5, 6),
        displacement=_values(4, 7),
        articulation=_values(4, 8),
        thermal=_values(2, 9),
    )
    decoded = array("d")
    decoded.frombytes(compact_signal_body(sensorium, frame_count=4))
    if sys.byteorder != "little":
        decoded.byteswap()
    per_port = tuple(decoded[index] for index in range(0, len(decoded), 4))
    assert per_port == (
        (1.0,) * RETINAL_PORTS
        + (2.0,) * 2
        + (3.0,) * 32
        + (4.0,) * 28
        + (5.0,) * 8
        + (6.0,) * 5
        + (7.0,) * 4
        + (8.0,) * 4
        + (9.0,) * 2
    )


def test_compact_body_refuses_changed_anatomy_clock_and_nonfinite_sample() -> None:
    valid = _constant()
    with pytest.raises(ValueError, match="retina changed mounted receptor count"):
        compact_signal_body(
            PhysicalSensorium(
                retina=valid.retina[:-1],
                legacy_ears=valid.legacy_ears,
                cochleae=valid.cochleae,
                touch=valid.touch,
                smell=valid.smell,
                taste=valid.taste,
                displacement=valid.displacement,
                articulation=valid.articulation,
                thermal=valid.thermal,
            ),
            frame_count=4,
        )
    with pytest.raises(ValueError, match="shared physical clock"):
        compact_signal_body(
            PhysicalSensorium(
                retina=((0.0,),) + valid.retina[1:],
                legacy_ears=valid.legacy_ears,
                cochleae=valid.cochleae,
                touch=valid.touch,
                smell=valid.smell,
                taste=valid.taste,
                displacement=valid.displacement,
                articulation=valid.articulation,
                thermal=valid.thermal,
            ),
            frame_count=4,
        )
    with pytest.raises(ValueError, match="non-finite"):
        compact_signal_body(
            _constant(thermal=(0.0, float("nan"))),
            frame_count=4,
        )
