from __future__ import annotations

from dataclasses import dataclass

import pytest

from dsf_ai_service.glew_runtime import native_materialized_fabric as boundary


@dataclass(frozen=True)
class _Inspection:
    schema: str
    fabric_generation: int
    mounted_generation: int
    neuron_count: int
    neurons: list[tuple[str, int, int, str, str]]
    python_callback_count: int


class _Native:
    def __init__(self) -> None:
        self.arguments = None

    def inspect_authenticated_legacy_materialized_fabric(self, *arguments):
        self.arguments = arguments
        return _Inspection(
            schema="guala.native.authenticated_legacy_fabric_inspection.v1",
            fabric_generation=13,
            mounted_generation=2,
            neuron_count=1,
            neurons=[("11" * 16, 1, 7, "cochlea", "erb-07")],
            python_callback_count=0,
        )


def test_one_native_call_returns_only_authenticated_legacy_roster(monkeypatch) -> None:
    native = _Native()
    monkeypatch.setattr(boundary, "_native_core", lambda: native)
    payload = b"GLMFAB03-exact-body"
    digest = "ab" * 32

    inspected = boundary.inspect_authenticated_legacy_materialized_fabric(
        payload=payload,
        expected_content_sha256=digest,
        max_state_bytes=4096,
        max_working_bytes=8192,
    )

    assert inspected.neurons == [("11" * 16, 1, 7, "cochlea", "erb-07")]
    assert native.arguments == (payload, bytes.fromhex(digest), 4096, 8192)


@pytest.mark.parametrize(
    "digest",
    ("", "00", "z" * 64, "00" * 31),
)
def test_malformed_expected_digest_never_reaches_native(monkeypatch, digest) -> None:
    monkeypatch.setattr(
        boundary,
        "_native_core",
        lambda: (_ for _ in ()).throw(AssertionError("native call occurred")),
    )
    with pytest.raises(ValueError, match="SHA-256"):
        boundary.inspect_authenticated_legacy_materialized_fabric(
            payload=b"GLMFAB03-exact-body",
            expected_content_sha256=digest,
        )
