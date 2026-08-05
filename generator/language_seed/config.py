"""config.py -- shared constants and cache-directory resolution for the
language-seed generator (GL-CMD-LANGUAGE-SEED-PHASE2-GENERATOR-EVE-20260707-v1).

Raw source corpora (NLTK data, ConceptNet dump, NRC lexicons, SCOWL, UD
treebank, etc.) are large and re-downloadable -- never committed to the
repo. GUALA_SEED_SOURCE_CACHE points at where they live; defaults to a
local .cache/ dir (gitignored) next to this file.
"""

from __future__ import annotations

import os

HERE = os.path.dirname(os.path.abspath(__file__))

SOURCE_CACHE_DIR = os.environ.get(
    "GUALA_SEED_SOURCE_CACHE",
    os.path.join(HERE, ".cache"),
)

OUTPUT_DIR = os.environ.get(
    "GUALA_SEED_OUTPUT_DIR",
    os.path.join(HERE, "output"),
)

# Wave atlas chi address space -- matches tools/wave_constants.py N_CELLS.
N_CELLS = 262144
CHI_MIN = 0
CHI_MAX = N_CELLS - 1

# J-matrix valid range -- CouplingsJij: J_BASE=1.0, J_MAX=1.5
# (dsf_ai_service/loom_model/neuron.py). Soft convention, not enforced by
# the class itself, but this is what every existing writer targets.
J_BASE = 1.0
J_MAX = 1.5
J_VALID_RANGE = (0.0, J_MAX)

# Real substrate organ tags (Guala.organism.hemi_by_op keys), confirmed by
# reading embryo.py's OPERATIONS list zipped positionally against
# self.brain.hemispheres (H0..H7 in index order, confirmed in brain.py):
#   H0 em   H1 pr   H2 ep   H3 sc   H4 gp   H5 sf   H6 sv   H7 aff
# topology.py's HEMISPHERE_PRIMARY_MODALITY gives the real per-hemisphere
# sensory/language assignment (H0 visual, H1 auditory, H2 tactile,
# H3 olfactory, H4 gustatory, H5 language, H6 auditory-secondary,
# H7 language-secondary). Composing both tables gives the organ tag each
# modality actually writes through -- there is no separate "H5/H7" concept
# a seed file can reference directly; only organ tags are valid
# hemisphere_affinity values (seed_loader.py only understands organ tags).
HEMI_INDEX_TO_ORGAN = {
    "H0": "em", "H1": "pr", "H2": "ep", "H3": "sc",
    "H4": "gp", "H5": "sf", "H6": "sv", "H7": "aff",
}

MODALITY_TO_ORGAN = {
    "visual": HEMI_INDEX_TO_ORGAN["H0"],       # em
    "auditory": [HEMI_INDEX_TO_ORGAN["H1"], HEMI_INDEX_TO_ORGAN["H6"]],  # pr, sv
    "tactile": HEMI_INDEX_TO_ORGAN["H2"],      # ep
    "olfactory": HEMI_INDEX_TO_ORGAN["H3"],    # sc
    "gustatory": HEMI_INDEX_TO_ORGAN["H4"],    # gp
}

# Language vocabulary/grammar itself lives in both language hemispheres.
LANGUAGE_ORGANS = [HEMI_INDEX_TO_ORGAN["H5"], HEMI_INDEX_TO_ORGAN["H7"]]  # sf, aff

ALL_ORGAN_TAGS = ["em", "pr", "ep", "sc", "gp", "sf", "sv", "aff"]

SEED_FORMAT_VERSION = "v1"

# Layer boundary -- rich layer word count (dispatch-specified).
RICH_LAYER_SIZE = 50_000

# Safety ceiling on total vocabulary so chi assignment always has headroom
# in the fixed 262,144-slot address space (dispatch's own 0-262143 bound).
MAX_TOTAL_VOCAB = 200_000


def source_path(*parts: str) -> str:
    return os.path.join(SOURCE_CACHE_DIR, *parts)


def output_path(*parts: str) -> str:
    return os.path.join(OUTPUT_DIR, *parts)
