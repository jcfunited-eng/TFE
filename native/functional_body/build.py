"""Build a selected body-only numerical extension in an isolated directory.

Cython is a build dependency only. No generated C/binary is stored in source.
Selection compiles an artifact; it never installs, mounts or deploys a law.
The existing interval remains the default; Radau is an unmounted candidate.
"""
import argparse
from pathlib import Path

import Cython
from Cython.Build import cythonize
from setuptools import Extension, setup


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--module", choices=("interval", "radau"), default="interval")
    args = parser.parse_args()
    if Cython.__version__ != "3.1.2":
        raise RuntimeError("body numerical build requires Cython 3.1.2")
    source = Path(__file__).resolve()
    output = args.output.resolve()
    repository = source.parents[2]
    if output == repository or output.is_relative_to(repository):
        raise ValueError("build output must be outside the source repository")
    output.mkdir(parents=True, exist_ok=True)
    extension = Extension(
        "guala_body_" + args.module,
        [str(source.with_name(args.module + ".pyx"))],
        extra_compile_args=["-O3", "-fno-fast-math", "-ffp-contract=off"],
    )
    setup(
        name="guala-body-" + args.module, version="1.0.0",
        ext_modules=cythonize(
            [extension], build_dir=str(output / "generated"),
            compiler_directives={"language_level": 3},
        ),
        script_args=["build_ext", "--build-lib", str(output / "python"),
                     "--build-temp", str(output / "objects")],
    )


if __name__ == "__main__":
    main()
