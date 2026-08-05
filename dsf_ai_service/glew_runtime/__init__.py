"""Non-semantic GLEW structural primitives.

The package root exports only calibrated native coupling, authenticated
evidence, and structural operators.  Domain-specific modules must be imported
explicitly and are not loaded as a side effect of the physical Guala runtime.
"""

from .coupling import (
    CouplingFailure,
    CouplingResult,
    NativePortCalibration,
    NativePortSample,
    NativePortState,
    NativeSampleBatch,
    PortKind,
    Sense,
    couple_mounted_sense,
    couple_native_port,
    native_port_calibration_receipt_payload,
    native_sample_batch_receipt_payload,
)
from .model import (
    EvidenceSample,
    EvidenceStream,
    ReceiptError,
    ReceiptRecord,
    ReceiptRegistry,
    receipt_sha256,
    sha256_digest,
)
from .operators import (
    CausalGrid,
    MountedResonanceGraph,
    MountedSupportDomain,
    RequiredEdge,
    ResonanceConfirmation,
    ResonanceOperatorAuthority,
    SupportFloor,
    causal_grid_receipt_payload,
    compute_resonance_confirmation,
    compute_support_floor,
    resonance_graph_receipt_payload,
    resonance_operator_receipt_payload,
    support_domain_receipt_payload,
)

__all__ = (
    "CausalGrid",
    "CouplingFailure",
    "CouplingResult",
    "EvidenceSample",
    "EvidenceStream",
    "MountedResonanceGraph",
    "MountedSupportDomain",
    "NativePortCalibration",
    "NativePortSample",
    "NativePortState",
    "NativeSampleBatch",
    "PortKind",
    "ReceiptError",
    "ReceiptRecord",
    "ReceiptRegistry",
    "RequiredEdge",
    "ResonanceConfirmation",
    "ResonanceOperatorAuthority",
    "Sense",
    "SupportFloor",
    "causal_grid_receipt_payload",
    "compute_resonance_confirmation",
    "compute_support_floor",
    "couple_mounted_sense",
    "couple_native_port",
    "native_port_calibration_receipt_payload",
    "native_sample_batch_receipt_payload",
    "receipt_sha256",
    "resonance_graph_receipt_payload",
    "resonance_operator_receipt_payload",
    "sha256_digest",
    "support_domain_receipt_payload",
)
