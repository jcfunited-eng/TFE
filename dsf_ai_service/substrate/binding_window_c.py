"""ctypes wrapper for binding_window.c's storage + add_entry hot path.

Per GL-CMD-BINDING-WINDOW-C-PORT-EVE-20260707-v1. WindowManager and its
callbacks (_atlas_record, _log_event) stay Python, unchanged -- only
BindingWindow's entries storage and add_entry move to C, so a ctypes
call into it releases the GIL for its duration (concurrent adds from
different threads run in actual parallel across cores instead of
serializing on the interpreter).

Design choices, stated plainly (this dispatch explicitly authorizes
"use them or refine" on the reference C code):

- BindingWindow* is a fully opaque ctypes.c_void_p on the Python side --
  never mirrored as a ctypes.Structure. It embeds a pthread_mutex_t,
  whose layout is platform/libc-specific; replicating that in Python
  would be the single riskiest thing this file could do (a mismatch is
  silent memory corruption, not a caught exception). Every field access
  goes through a real C function (bw_entry_count, bw_get_entry, ...).

- WindowEntry IS mirrored as a ctypes.Structure -- it's fixed-size
  scalar fields only (no embedded lock), the low-risk case, and
  bw_get_entry needs somewhere to copy an entry's fields into.

- modality has a small, fixed, six-value enum (matches the C file's own
  comment: 0=sight,1=sound,2=word,3=touch,4=smell,5=taste) -- the one
  enum this dispatch's "DO NOT: change... without updating both C and
  Python" refers to.

- section_id is NOT a fixed enum. Section names are open-ended at
  runtime (e.g. "audio_low"/"audio_high" per cochlear band,
  "modal_sight"/"modal_touch" etc. from ground_modal, the seven fixed
  word sections) -- enumerating every possible one in C would be
  fragile against a future new channel name. Instead this file keeps a
  plain Python dict assigning each distinct section name the next
  integer id the first time it's seen, guarded by a small lock (this
  assignment is a quick dict check-and-insert, not the hot path itself
  -- the actual add_entry call is what releases the GIL). C only ever
  sees/returns the opaque integer; this file translates it back to the
  real string in get_entries().
"""
from __future__ import annotations

import ctypes
import os
import threading
from typing import Optional

_MODALITY_TO_ID = {"sight": 0, "sound": 1, "word": 2, "touch": 3, "smell": 4, "taste": 5}
_ID_TO_MODALITY = {v: k for k, v in _MODALITY_TO_ID.items()}

SOURCE_TAG_MAX = 32
MAX_ENTRIES_PER_WINDOW = 1024


class _WindowEntryStruct(ctypes.Structure):
    _fields_ = [
        ("modality_id", ctypes.c_int32),
        ("section_id", ctypes.c_int32),
        ("motif_id", ctypes.c_int64),
        ("chi", ctypes.c_int64),
        ("tick", ctypes.c_int64),
        ("source_tag", ctypes.c_char * SOURCE_TAG_MAX),
    ]


_SO_NAME = "libbindingwindow.so"
_lib = None
_lib_load_error: Optional[str] = None


def _load_lib():
    global _lib, _lib_load_error
    if _lib is not None or _lib_load_error is not None:
        return
    so_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), _SO_NAME)
    try:
        lib = ctypes.CDLL(so_path)
        lib.bw_open.restype = ctypes.c_void_p
        lib.bw_open.argtypes = [ctypes.c_char_p, ctypes.c_int64, ctypes.c_double]
        lib.bw_add_entry.restype = ctypes.c_int32
        lib.bw_add_entry.argtypes = [
            ctypes.c_void_p, ctypes.c_int32, ctypes.c_int32,
            ctypes.c_int64, ctypes.c_int64, ctypes.c_int64, ctypes.c_char_p,
        ]
        lib.bw_close.argtypes = [ctypes.c_void_p, ctypes.c_int64, ctypes.c_double]
        lib.bw_entry_count.restype = ctypes.c_int32
        lib.bw_entry_count.argtypes = [ctypes.c_void_p]
        lib.bw_get_entry.restype = ctypes.c_int32
        lib.bw_get_entry.argtypes = [ctypes.c_void_p, ctypes.c_int32,
                                     ctypes.POINTER(_WindowEntryStruct)]
        lib.bw_free.argtypes = [ctypes.c_void_p]
        _lib = lib
    except OSError as e:
        _lib_load_error = str(e)


_load_lib()


def c_backend_available() -> bool:
    return _lib is not None


# Section-name <-> id table. Guarded by a lock for the check-and-insert
# on a new name -- quick, not the hot path (the C call itself is).
_section_lock = threading.Lock()
_section_to_id: dict = {}
_id_to_section: dict = {}


def _section_id_for(section_name: str) -> int:
    sid = _section_to_id.get(section_name)
    if sid is not None:
        return sid
    with _section_lock:
        sid = _section_to_id.get(section_name)
        if sid is None:
            sid = len(_section_to_id)
            _section_to_id[section_name] = sid
            _id_to_section[sid] = section_name
    return sid


class CBindingWindowOverflow(Exception):
    """Raised by add_entry when the C-side fixed array is full
    (MAX_ENTRIES_PER_WINDOW) -- callers must decide how to handle this,
    it is never silently swallowed here."""


class CBindingWindow:
    """Drop-in replacement for the Python BindingWindow dataclass.
    Metadata fields stay plain Python attributes, unchanged in shape
    from the dataclass version; only entries storage + add_entry
    delegate to the C library."""

    def __init__(self, window_id: str, opened_tick: int, opened_wall_clock: float,
                 trigger_reason: str, presence_state: Optional[dict] = None,
                 affect_snapshot: Optional[dict] = None):
        if _lib is None:
            raise RuntimeError(f"libbindingwindow.so not loaded: {_lib_load_error}")
        self.window_id = window_id
        self.opened_tick = opened_tick
        self.opened_wall_clock = opened_wall_clock
        self.trigger_reason = trigger_reason
        self.presence_state = dict(presence_state) if presence_state else {}
        self.affect_snapshot = dict(affect_snapshot) if affect_snapshot else {}
        self.closed_tick = None
        self.closed_wall_clock = None
        self.close_reason = None
        self._handle = _lib.bw_open(
            window_id.encode("utf-8"), int(opened_tick), float(opened_wall_clock))
        if not self._handle:
            raise MemoryError("bw_open returned NULL (native allocation failed)")
        self._freed = False

    def add_entry(self, modality: str, section: str, motif_id: int, chi: int,
                  tick: int, source_tag: str = "") -> int:
        modality_id = _MODALITY_TO_ID.get(modality, -1)
        section_id = _section_id_for(section)
        tag_bytes = source_tag.encode("utf-8")[:SOURCE_TAG_MAX - 1]
        idx = _lib.bw_add_entry(
            self._handle, modality_id, section_id, int(motif_id), int(chi),
            int(tick), tag_bytes)
        if idx < 0:
            raise CBindingWindowOverflow(
                f"window {self.window_id!r} is full "
                f"({MAX_ENTRIES_PER_WINDOW} entries) or already closed")
        return idx

    def close(self, closed_tick: int, closed_wall_clock: float, close_reason: str) -> None:
        self.closed_tick = closed_tick
        self.closed_wall_clock = closed_wall_clock
        self.close_reason = close_reason
        _lib.bw_close(self._handle, int(closed_tick), float(closed_wall_clock))

    def get_entries(self) -> list:
        """Read all entries back as plain dicts -- same shape the
        dataclass version's own close() snapshot already produced."""
        n = _lib.bw_entry_count(self._handle)
        out = []
        entry = _WindowEntryStruct()
        for i in range(n):
            ok = _lib.bw_get_entry(self._handle, i, ctypes.byref(entry))
            if not ok:
                break
            out.append({
                "modality": _ID_TO_MODALITY.get(entry.modality_id, "?"),
                "section": _id_to_section.get(entry.section_id, "?"),
                "motif_id": entry.motif_id,
                "chi": entry.chi,
                "tick": entry.tick,
                "source_tag": entry.source_tag.decode("utf-8", errors="replace"),
                "provenance": {},
            })
        return out

    def free(self) -> None:
        if not self._freed and self._handle:
            _lib.bw_free(self._handle)
            self._handle = None
            self._freed = True

    def __del__(self):
        # Safety net only -- WindowManager.close() must call free()
        # explicitly once entries are read back. Without this, a
        # dropped reference that skipped free() would leak the
        # ~65KB native allocation (MAX_ENTRIES_PER_WINDOW entries are
        # allocated inline in the struct, not lazily) for good --
        # unlike Python memory, the C heap has no garbage collector.
        try:
            self.free()
        except Exception:
            pass
