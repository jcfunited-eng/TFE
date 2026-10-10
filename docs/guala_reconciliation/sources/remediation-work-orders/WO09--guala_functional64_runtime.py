"""Canonical host custody for the one native functional64 current.

The original paired body/world remain inert bytes. Native material separately
retains the exact complete original64 capture; no retired controller executes.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import struct
from typing import Any

from guala_core import Functional64Core
from .guala_cochlea import CochlearStream

MAGIC = b"GL64ORG1"
_HEADER = struct.Struct("<8sHQQQ")


@dataclass(frozen=True, slots=True)
class EnvelopeBounds:
    encoded_bytes: int
    staged_bytes: int
    native: tuple[int, ...]

    def __post_init__(self) -> None:
        if any(type(value) is not int or value <= 0
               for value in (self.encoded_bytes, self.staged_bytes)):
            raise ValueError("functional64 envelope requires explicit byte admission")
        if (type(self.native) is not tuple or len(self.native) != 13
                or any(type(value) is not int or value <= 0 for value in self.native)):
            raise ValueError("functional64 native admission changed its thirteen fields")
        # Host encoding payload only: one depth-one published checkpoint, current
        # envelope, successor envelope and separate original history (each <= E)
        # may coexist with native Rust Vec and Python bytes (each <= N). This
        # also covers cold input, extracted sections and canonical re-encoding.
        # Native arrays, Python/world objects and allocator/RSS admission remain
        # separate; this conservative bound makes no whole-process fit claim.
        if 4 * self.encoded_bytes + 2 * self.native[0] > self.staged_bytes:
            raise ValueError("functional64 host encoding regions were not jointly admitted")


@dataclass(frozen=True, slots=True)
class OriginalPair:
    body: bytes
    world: bytes

    def __post_init__(self) -> None:
        if (type(self.body) is not bytes or len(self.body) <= 8
                or not self.body.startswith(b"GLFUNC01")
                or type(self.world) is not bytes or not self.world):
            raise ValueError("original paired body/world custody is absent")


def verify_current_ears(core: Functional64Core) -> None:
    """Use the actual continuous receptor's full checksum/coefficient decoder."""
    ears = CochlearStream.restore(core.cochlear_current_bytes)
    if core.cochlear_origin_millisecond * 16 + ears.sample_count != core.source_millisecond * 16:
        raise ValueError("retained ear and native source clocks differ")


@dataclass(frozen=True, slots=True)
class Readiness:
    identity: str
    organism_tick: int
    state_sha256: str
    state_bytes: int
    python_callback_count: int
    articulated_body_axes: tuple[tuple[object, ...], ...]


@dataclass(frozen=True, slots=True)
class Checkpoint:
    identity: str
    organism_tick: int
    state_sha256: str
    state_bytes: int
    _body: bytes
    _history: OriginalPair

    def encoded_generation(self) -> bytes:
        return self._body


@dataclass(frozen=True, slots=True)
class CurrentSnapshot:
    core: Functional64Core
    history: OriginalPair
    encoded_body: bytes
    state_sha256: str

    @property
    def organism_tick(self) -> int:
        return self.core.organism_tick

    def prepare_checkpoint(self) -> Checkpoint:
        return Checkpoint(self.core.identity, self.organism_tick,
                          self.state_sha256, len(self.encoded_body),
                          self.encoded_body, self.history)


def _snapshot(core: Functional64Core, history: OriginalPair,
              bounds: EnvelopeBounds) -> CurrentSnapshot:
    if type(core) is not Functional64Core:
        raise TypeError("functional64 current is not the actual native owner")
    if core.max_encoded_bytes > bounds.native[0]:
        raise ValueError("native current encoding bound exceeds host admission")
    fixed_size = _HEADER.size + len(history.body) + len(history.world)
    if fixed_size >= bounds.encoded_bytes:
        raise ValueError("original paired history leaves no admitted native encoding space")
    native = core.encoded()
    if type(native) is not bytes or not native:
        raise ValueError("native current encoding is unavailable")
    size = fixed_size + len(native)
    if size > bounds.encoded_bytes:
        raise ValueError("functional64 canonical envelope exceeds byte admission")
    encoded = b"".join((_HEADER.pack(MAGIC, 1, len(history.body), len(history.world), len(native)),
                        history.body, history.world, native))
    return CurrentSnapshot(core, history, encoded, hashlib.sha256(encoded).hexdigest())


class Functional64Runtime:
    """The actor's single current pointer; every prepared successor is private."""

    def __init__(self, current: CurrentSnapshot, bounds: EnvelopeBounds):
        if type(current) is not CurrentSnapshot or type(bounds) is not EnvelopeBounds:
            raise TypeError("functional64 runtime requires actual immutable current custody")
        self._current = current
        self.bounds = bounds

    @classmethod
    def from_commissioned(cls, core: Functional64Core, original_body: bytes,
                          original_world: bytes, *, original_identity: str,
                          original_tick: int, bounds: EnvelopeBounds) -> Functional64Runtime:
        """Explicit installation from one authentic captured pair, never restore.

        Caller verifies these original bytes and identity/tick against the same
        capture. Storing them never imports or executes their retired controller.
        """
        history = OriginalPair(original_body, original_world)
        if (type(core) is not Functional64Core
                or type(original_identity) is not str or not original_identity
                or type(original_tick) is not int or original_tick < 0
                or core.identity != original_identity or core.organism_tick != original_tick):
            raise ValueError("commissioned native core changed original identity or tick")
        verify_current_ears(core)
        return cls(_snapshot(core, history, bounds), bounds)

    @classmethod
    def restore(cls, encoded: bytes, *, geometry_record: bytes,
                surface_sites: int, bounds: EnvelopeBounds) -> Functional64Runtime:
        if type(encoded) is not bytes or not _HEADER.size <= len(encoded) <= bounds.encoded_bytes:
            raise ValueError("functional64 current envelope is unavailable or oversized")
        magic, version, body_size, world_size, native_size = _HEADER.unpack_from(encoded)
        if (magic != MAGIC or version != 1 or not body_size or not world_size or not native_size
                or _HEADER.size + body_size + world_size + native_size != len(encoded)):
            raise ValueError("functional64 current envelope framing changed")
        if native_size > bounds.native[0]:
            raise ValueError("retained native current exceeds host admission")
        first = _HEADER.size + body_size
        second = first + world_size
        history = OriginalPair(encoded[_HEADER.size:first], encoded[first:second])
        native = encoded[second:]
        core = Functional64Core.restore(native, geometry_record, surface_sites, bounds.native)
        if core.max_encoded_bytes > bounds.native[0]:
            raise ValueError("restored native encoding bound exceeds host admission")
        verify_current_ears(core)
        if core.encoded() != native:
            raise ValueError("ordinary native cold restore changed canonical bytes")
        current = CurrentSnapshot(core, history, encoded, hashlib.sha256(encoded).hexdigest())
        return cls(current, bounds)

    @property
    def core(self) -> Functional64Core:
        return self._current.core

    @property
    def identity(self) -> str:
        return self.core.identity

    @property
    def live_organism_tick(self) -> int:
        return self.core.organism_tick

    @property
    def body_axes(self) -> tuple[tuple[object, ...], ...]:
        return self.core.body_axes

    def encoded(self) -> bytes:
        return self._current.encoded_body

    def readiness(self) -> Readiness:
        current = self._current
        return Readiness(current.core.identity, current.organism_tick,
                         current.state_sha256, len(current.encoded_body), 0,
                         current.core.body_axes)

    def snapshot_lived_state(self) -> CurrentSnapshot:
        return self._current

    def prepare_successor(self, core: Functional64Core) -> CurrentSnapshot:
        if (type(core) is not Functional64Core or core.identity != self.identity
                or core.organism_tick != self.live_organism_tick + 1
                or core.source_millisecond != self.core.source_millisecond + 250):
            raise ValueError("native successor changed its single quarter chronology")
        return _snapshot(core, self._current.history, self.bounds)

    def validate_lived_checkpoint(self, checkpoint: Any) -> None:
        if (type(checkpoint) is not Checkpoint or checkpoint.identity != self.identity
                or checkpoint._history is not self._current.history
                or not 0 <= checkpoint.organism_tick <= self.live_organism_tick
                or checkpoint.state_bytes != len(checkpoint._body)
                or hashlib.sha256(checkpoint._body).hexdigest() != checkpoint.state_sha256):
            raise ValueError("functional64 checkpoint is not this retained life")

    def adopt_published_lived_checkpoint(self, checkpoint: Any) -> None:
        self.validate_lived_checkpoint(checkpoint)
