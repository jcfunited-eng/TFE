#!/usr/bin/env python3
"""Retired synthetic 64D curriculum entry point.

This program deliberately does not import the native core, create an organism,
load/save a checkpoint, or present stimuli. The old named-formant/target loop
was neither Guala's live sensory path nor evidence of command learning.
Existing checkpoint bytes remain historical synthetic-component evidence.
"""

from __future__ import annotations

import sys

RETIRED_EXIT_STATUS = 78


def main() -> int:
    print(
        "REFUSED: synthetic 64D hardening is retired. No state was loaded, "
        "reset or written. Present real PCM/world experience through Guala's "
        "existing organism sensory boundary; do not inject named formants, "
        "target coordinates or motor answers. Spoken-command learning and "
        "A10/A11 closure are not established.",
        file=sys.stderr,
    )
    return RETIRED_EXIT_STATUS


if __name__ == "__main__":
    raise SystemExit(main())
