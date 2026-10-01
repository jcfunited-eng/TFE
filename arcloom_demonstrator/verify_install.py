"""Verify the actual native extension against the ONE just-built wheel.

Packaging custody only; this module is never imported by organism physics.
Works with the regular maturin package layout. No flattening or deletion.
"""
from __future__ import annotations

import hashlib
import importlib
import importlib.machinery
from pathlib import Path
import sys
import zipfile


def verify(wheel: Path) -> None:
    import guala_core

    if sys.prefix == sys.base_prefix:
        raise RuntimeError("Candidate must run in an isolated virtual environment")
    with zipfile.ZipFile(wheel) as archive:
        members = [name for name in archive.namelist()
                   if any(name.endswith(suffix)
                          for suffix in importlib.machinery.EXTENSION_SUFFIXES)]
        if len(members) != 1:
            raise RuntimeError("Expected exactly one native extension in candidate wheel")
        name = members[0]
        parts = Path(name).parts
        if Path(name).is_absolute() or ".." in parts:
            raise RuntimeError("Invalid candidate wheel member path")
        stem = parts[-1].split(".")[0]
        native = importlib.import_module(".".join((*parts[:-1], stem)))
        loaded = Path(native.__file__).resolve(strict=True)
        prefix = Path(sys.prefix).resolve(strict=True)
        if not loaded.is_relative_to(prefix):
            raise RuntimeError("Loaded native extension is outside the candidate environment")
        expected = archive.read(name)
        actual = loaded.read_bytes()
        if actual != expected:
            raise RuntimeError("Loaded native extension differs from the just-built wheel")
    for symbol in ("ArcLoomNeuron", "ModularSubstrate64D"):
        if not hasattr(native, symbol) or getattr(guala_core, symbol, None) is not getattr(native, symbol):
            raise RuntimeError(f"Missing or shadowed candidate symbol: {symbol}")
    print(f"loaded_native={loaded}")
    print(f"native_sha256={hashlib.sha256(actual).hexdigest()}")
    print(f"wheel_sha256={hashlib.sha256(wheel.read_bytes()).hexdigest()}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Usage: verify_install.py EXACT_WHEEL_PATH")
    verify(Path(sys.argv[1]).resolve(strict=True))
