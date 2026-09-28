"""Build the versioned body-only stop, coupled-step and contact-geometry laws.

Run once on a clean pinned upstream checkout. No global installation or live
runtime changes. The small retained patch is the complete numerical-law delta.
"""
from __future__ import annotations

import argparse
import ctypes
import hashlib
import json
from pathlib import Path
import subprocess
import sys

UPSTREAM = "f1d45bd5422c74beddfb0d1deb590a02583d21de"
ENGINE_VERSION = "3.3.7+guala.contact-geometry.1"
PREIMAGE = {
    "src/engine/engine_core_constraint.c":
        "1d88206cf33624b48f1fcac7afa06dda13cfa86e4fe26dd15b3073d2a003194d",
    "src/engine/engine_support.c":
        "93e098192651b52d2c87689155a9eaad559439d953324d92579b2950e8d84f37",
    "src/engine/engine_forward.c":
        "9ee0dbe90e55a74f9a2de89ffe38666245c5d3f15c41f825cc05db21a971641d",
    "src/engine/engine_solver.c":
        "09c9e786dfa7478abc01ee2664fa93127e4896b94613b490d0759ab3361330e2",
    "src/engine/engine_solver.h":
        "d6758cd08e3394e4107cffe8318e9ae3c9550e7516f3140c0b209781011777c2",
    "src/engine/engine_collision_box.c":
        "2c063b1db7ec047c8b27f2f0a75aa2545d7465783d4aebe0a38e6287831145cf",
    "src/engine/engine_collision_driver.c":
        "e22a7d8eba7818a3de742c9267f66980d9188e405dcec9ae915285d0df6bb0fb",
    "src/engine/engine_collision_primitive.h":
        "f57f04c7e89afcde3a8916aa428dbfc334c7dbc39f0b05ed2ad4beccc31f73a2",
    "src/engine/engine_core_smooth.c":
        "3a6d65a5e7e7d8eb023aa742796b84bc927263126dbfa0eaf5967486fea926ca",
    "src/engine/engine_core_smooth.h":
        "7a50fb72114115289c3c76d1fa5f2d8433919588e040964b57e0fa25c8eaa75a",
    "src/engine/engine_core_util.c":
        "4a81bc43a636601f6dda4fd37298c49013b41b8ff6180f220f2065156e02507e",
    "src/engine/engine_core_util.h":
        "617794ae8d45150dc17285c16ae2aeaa6312e901fd592596f2e9ebf5914b0766",
    "src/engine/engine_util_spatial.c":
        "9747faf721ba3e2c9c8c2a11c38e56ffd4aa2a40650ab5d2d37336d02de2f845",
}
# Exact upstream build dependencies, not organism anatomy or decision tables.
DEPENDENCIES = {
    "ccd": "7931e764a19ef6b21b443376c699bbc9c6d4fba8",
    "qhull": "62ccc56af071eaa478bef6ed41fd7a55d3bb2d80",
    "lodepng": "17d08dd26cac4d63f43af217ebd70318bfb8189c",
    "tinyxml2": "e6caeae85799003f4ca74ff26ee16a789bc2af48",
    "tinyobjloader": "1421a10d6ed9742f5b2c1766d22faa6cfbc56248",
    "marchingcubecpp": "f03a1b3ec29b1d7d865691ca8aea4f1eb2c2873d",
    "trianglemeshdistance": "2cb643de1436e1ba8e2be49b07ec5491ac604457",
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--cmake", type=Path, required=True)
    parser.add_argument("--dependencies", type=Path,
                        help="fresh pinned local dependency checkouts for an offline build")
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
    dependency_flags, dependency_sources = [], {}
    if args.dependencies is not None:
        dependencies = args.dependencies.resolve(strict=True)
        for parent in (repository, source, output):
            if dependencies == parent or dependencies.is_relative_to(parent) or parent.is_relative_to(dependencies):
                raise ValueError("dependency source directory must be disjoint")
        for name, revision in DEPENDENCIES.items():
            path = (dependencies / (name + "-src")).resolve(strict=True)
            if path.parent != dependencies:
                raise ValueError("dependency source escapes declared root")
            actual = subprocess.check_output(["git", "-C", str(path), "rev-parse", "HEAD"], text=True).strip()
            dirty = subprocess.check_output(["git", "-C", str(path), "status", "--porcelain=v1"], text=True)
            if actual != revision or dirty:
                raise ValueError("clean pinned dependency required: " + name)
            dependency_sources[name] = {"source": str(path), "revision": actual}
            dependency_flags.append("-DFETCHCONTENT_SOURCE_DIR_" + name.upper() + "=" + str(path))
        dependency_flags.append("-DFETCHCONTENT_FULLY_DISCONNECTED=ON")
    patches = tuple(Path(__file__).with_name(name).resolve()
                    for name in ("closed_limits.patch", "coupled_step.patch",
                                 "contact_guards.patch", "rotation_geometry.patch",
                                 "common_frame.patch", "geometry_version.patch"))
    for patch in patches:
        git("apply", "--check", str(patch))
        git("apply", str(patch))
    if set(git("diff", "--name-only").splitlines()) != set(PREIMAGE):
        raise RuntimeError("patch changed unexpected upstream paths")
    flags = [
        "-DCMAKE_BUILD_TYPE=Release",
        "-DCMAKE_C_FLAGS=-fno-fast-math -ffp-contract=off",
        "-DCMAKE_CXX_FLAGS=-fno-fast-math -ffp-contract=off",
        "-DMUJOCO_BUILD_EXAMPLES=OFF", "-DMUJOCO_BUILD_SIMULATE=OFF",
        "-DMUJOCO_BUILD_TESTS=OFF", "-DMUJOCO_TEST_PYTHON_UTIL=OFF",
        "-DBUILD_TESTING=OFF", "-DMUJOCO_WITH_USD=OFF",
    ] + dependency_flags
    subprocess.run([str(cmake), "-S", str(source), "-B", str(output), *flags],
                   check=True, stdout=sys.stderr)
    subprocess.run([str(cmake), "--build", str(output), "--target", "mujoco",
                    "--parallel", "2"], check=True, stdout=sys.stderr)
    library = output / "lib/libmujoco.so.3.3.7"
    loaded = ctypes.CDLL(str(library))
    loaded.mj_versionString.restype = ctypes.c_char_p
    actual_version = loaded.mj_versionString().decode("ascii")
    if actual_version != ENGINE_VERSION:
        raise RuntimeError("built native law identity differs")
    print(json.dumps({
        "upstream": UPSTREAM, "engine_version": actual_version,
        "dependency_sources": dependency_sources, "patch_sha256": {
            p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in patches},
        "library": str(library), "library_sha256": hashlib.sha256(library.read_bytes()).hexdigest(),
        "flags": flags, "source_sha256": {
            p: hashlib.sha256((source / p).read_bytes()).hexdigest() for p in PREIMAGE},
        "scope": "compiled candidate only; not installed or production-qualified",
    }, sort_keys=True))


if __name__ == "__main__":
    main()
