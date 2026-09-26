"""Build the explicitly versioned body-only joint-stop correction in isolation.

Run once on a clean pinned upstream checkout. No global installation or live
runtime changes. The small retained patch is the complete numerical-law delta.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

UPSTREAM = "f1d45bd5422c74beddfb0d1deb590a02583d21de"
PREIMAGE = {
    "src/engine/engine_core_constraint.c":
        "1d88206cf33624b48f1fcac7afa06dda13cfa86e4fe26dd15b3073d2a003194d",
    "src/engine/engine_support.c":
        "93e098192651b52d2c87689155a9eaad559439d953324d92579b2950e8d84f37",
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--cmake", type=Path, required=True)
    args = parser.parse_args()
    source, output, cmake = (p.resolve() for p in
                            (args.source, args.output, args.cmake))
    repository = Path(__file__).resolve().parents[2]
    if (source == repository or source.is_relative_to(repository)
            or output == repository or output.is_relative_to(repository)
            or output == source or output.is_relative_to(source)
            or source.is_relative_to(output) or output.exists()):
        raise ValueError("fresh disjoint build/source directories outside repository required")
    def git(*command):
        return subprocess.check_output(["git", "-C", str(source), *command], text=True)
    if git("rev-parse", "HEAD").strip() != UPSTREAM:
        raise ValueError("incorrect upstream revision")
    if git("status", "--porcelain=v1"):
        raise ValueError("upstream checkout must be clean")
    for path, expected in PREIMAGE.items():
        if hashlib.sha256((source / path).read_bytes()).hexdigest() != expected:
            raise ValueError("upstream preimage differs: " + path)
    version = subprocess.check_output([str(cmake), "--version"], text=True)
    if version.splitlines()[0] != "cmake version 3.31.6":
        raise ValueError("build requires pinned CMake 3.31.6")
    patch = Path(__file__).with_name("closed_limits.patch").resolve()
    git("apply", "--check", str(patch))
    git("apply", str(patch))
    if set(git("diff", "--name-only").splitlines()) != set(PREIMAGE):
        raise AssertionError("patch changed unexpected upstream paths")
    flags = [
        "-DCMAKE_BUILD_TYPE=Release",
        "-DCMAKE_C_FLAGS=-fno-fast-math -ffp-contract=off",
        "-DCMAKE_CXX_FLAGS=-fno-fast-math -ffp-contract=off",
        "-DMUJOCO_BUILD_EXAMPLES=OFF", "-DMUJOCO_BUILD_SIMULATE=OFF",
        "-DMUJOCO_BUILD_TESTS=OFF", "-DMUJOCO_TEST_PYTHON_UTIL=OFF",
        "-DBUILD_TESTING=OFF", "-DMUJOCO_WITH_USD=OFF",
    ]
    subprocess.run([str(cmake), "-S", str(source), "-B", str(output), *flags],
                   check=True, stdout=sys.stderr)
    subprocess.run([str(cmake), "--build", str(output), "--target", "mujoco",
                    "--parallel", "2"], check=True, stdout=sys.stderr)
    library = output / "lib/libmujoco.so.3.3.7"
    print(json.dumps({
        "upstream": UPSTREAM, "patch_sha256": hashlib.sha256(patch.read_bytes()).hexdigest(),
        "library": str(library), "library_sha256": hashlib.sha256(library.read_bytes()).hexdigest(),
        "flags": flags, "source_sha256": {
            p: hashlib.sha256((source / p).read_bytes()).hexdigest() for p in PREIMAGE},
        "scope": "compiled candidate only; not installed or production-qualified",
    }, sort_keys=True))


if __name__ == "__main__":
    main()
