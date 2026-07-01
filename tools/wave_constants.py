"""Shared WaveAtlas constants — imported by wave_spillover, wave_atlas, and validator."""

SATURATION_THRESHOLD = 5.0  # aggregate_strength > this → cell saturated
CHI_BAND = 5                 # spillover search radius
SUBDIVISION_TRIGGER = 8      # hop depth before subdivision fires
N_CELLS = 262144             # chi index space size
PHASE_DIMS = 16              # complex phase vector dimension
