"""
loom_model — per-neuron LoomNeuron stack (Stage 1, K=0 single-neuron isolation).

GL-CMD-LOOM-NEURON-STAGE1-EVE-20260620-78
"""
from .neuron import (
    LoomNeuron,
    PsiLattice,
    SpikeBuffer,
    CouplingsJij,
    FamiliarityFeedback,
    LawField,
    DNAExpressionSite,
    DEFAULT_LAWS,
)

__all__ = [
    "LoomNeuron",
    "PsiLattice",
    "SpikeBuffer",
    "CouplingsJij",
    "FamiliarityFeedback",
    "LawField",
    "DNAExpressionSite",
    "DEFAULT_LAWS",
]
