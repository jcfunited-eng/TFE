"""
loom_model — LoomNeuron (Stage 1) + LoomCluster (Stage 2) + Folding Division (Stage 3).

GL-CMD-LOOM-NEURON-STAGE1-EVE-20260620-78
GL-CMD-LOOM-CLUSTER-STAGE2-EVE-20260620-79
GL-CMD-LOOM-STAGE3-FOLDING-CLAUDE-20260620-84
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
from .cluster import LoomCluster
from .substrate_dna import (
    OverflowSignal,
    derive_daughter_parameters,
    KRIMELACK_PRIMITIVES,
    TactileKrimelack,
    OlfactoryKrimelack,
    GustatoryKrimelack,
    VisualKrimelack,
    CochlearBankKrimelack,
    FOLD_TRIGGER_RATIO,
    K_TOTAL,
)

__all__ = [
    "LoomNeuron",
    "LoomCluster",
    "PsiLattice",
    "SpikeBuffer",
    "CouplingsJij",
    "FamiliarityFeedback",
    "LawField",
    "DNAExpressionSite",
    "DEFAULT_LAWS",
    "OverflowSignal",
    "derive_daughter_parameters",
    "KRIMELACK_PRIMITIVES",
    "TactileKrimelack",
    "OlfactoryKrimelack",
    "GustatoryKrimelack",
    "VisualKrimelack",
    "CochlearBankKrimelack",
    "FOLD_TRIGGER_RATIO",
    "K_TOTAL",
]
