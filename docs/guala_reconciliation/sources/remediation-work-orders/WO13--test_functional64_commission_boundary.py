"""Strict transport rejections only; actual-current cold witness lives in owner tests.

The empty archive deliberately cannot commission an organism. These cases check
that typed validation rejects before a codec/material/current could be built.
"""
import pytest
import guala_core as aaf


def _invalid_transport():
    return [
        b"", b"", b"", 0, "typed-boundary", 0, 0,
        500_000, 1, b"", 41_500_000, 0, b"", b"", (0,) * 97, 0,
        (1,) * 13, (1, 1, 0), (1, 0, 1),
    ]


@pytest.mark.parametrize("index", (3, 5, 6, 7, 8, 10, 11, 15))
def test_scalar_bool_is_rejected_before_any_commission(index):
    arguments = _invalid_transport()
    arguments[index] = False
    with pytest.raises(TypeError, match="not bool or coercion"):
        aaf.exact_commission_functional64_current(*arguments)


def test_terminal_bool_and_missing_terminal_are_not_zero_transport():
    arguments = _invalid_transport()
    arguments[14] = (False,) + (0,) * 96
    with pytest.raises(TypeError, match="not bool or coercion"):
        aaf.exact_commission_functional64_current(*arguments)
    arguments[14] = (0,) * 96
    with pytest.raises(ValueError, match="all97"):
        aaf.exact_commission_functional64_current(*arguments)


def test_nonzero_new_transport_cannot_be_claimed_as_retained_state():
    arguments = _invalid_transport()
    arguments[14] = (1,) + (0,) * 96
    with pytest.raises(ValueError, match="explicit zero"):
        aaf.exact_commission_functional64_current(*arguments)
    arguments[14] = (0,) * 97
    arguments[15] = 1
    with pytest.raises(ValueError, match="explicit zero"):
        aaf.exact_commission_functional64_current(*arguments)


def test_commissioning_never_supplies_implicit_defaults():
    with pytest.raises(TypeError):
        aaf.exact_commission_functional64_current(*_invalid_transport()[:-1])
