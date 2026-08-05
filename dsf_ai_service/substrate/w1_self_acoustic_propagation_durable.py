"""Explicit durable-program exports for the composed W1 vocal authority."""

from dsf_ai_service.substrate.w1_self_acoustic_propagation import (
    PreparedW1SelfAcousticMount,
    W1ArticulatorySelfAcousticCommitUndo,
    W1PreparedArticulatoryCommitment,
    W1SelfAcousticMount,
    W1SelfAcousticPropagationAuthority,
    W1SelfAcousticReceipt,
    W1SelfAcousticState,
    W1_PREPARED_ARTICULATORY_COMMITMENT_SCHEMA,
    _EmissionReceiptCommitment,
    _PreparedEmissionView,
)


__all__ = [
    "PreparedW1SelfAcousticMount",
    "W1ArticulatorySelfAcousticCommitUndo",
    "W1PreparedArticulatoryCommitment",
    "W1_PREPARED_ARTICULATORY_COMMITMENT_SCHEMA",
    "W1SelfAcousticMount",
    "W1SelfAcousticPropagationAuthority",
    "W1SelfAcousticReceipt",
    "W1SelfAcousticState",
]
