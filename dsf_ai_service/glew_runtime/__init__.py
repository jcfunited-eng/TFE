"""Clean-generation GLEW upstream runtime primitives.

This package is isolated from every legacy Guala engine.  It admits only
explicitly receipted interface events and calibrated native output ports.  It
does not choose a native port, combine ports, infer chemistry, or reduce the
seven-field DSF surface.
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
from .language import (
    BalancedTrit,
    TypedLanguageEvent,
    TypedLanguageState,
    capture_typed_language,
    encode_balanced_ternary_scalar,
    typed_interface_receipt_payload,
    typed_language_event_receipt_payload,
    typed_phase_calibration_receipt_payload,
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
    ResonanceOperatorAuthority,
    ResonanceConfirmation,
    SupportFloor,
    causal_grid_receipt_payload,
    compute_resonance_confirmation,
    compute_support_floor,
    resonance_graph_receipt_payload,
    resonance_operator_receipt_payload,
    support_domain_receipt_payload,
)

__all__ = (
    "BalancedTrit",
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
    "ResonanceOperatorAuthority",
    "ResonanceConfirmation",
    "Sense",
    "SupportFloor",
    "TypedLanguageEvent",
    "TypedLanguageState",
    "capture_typed_language",
    "causal_grid_receipt_payload",
    "compute_resonance_confirmation",
    "compute_support_floor",
    "couple_mounted_sense",
    "couple_native_port",
    "encode_balanced_ternary_scalar",
    "native_port_calibration_receipt_payload",
    "native_sample_batch_receipt_payload",
    "receipt_sha256",
    "resonance_graph_receipt_payload",
    "resonance_operator_receipt_payload",
    "sha256_digest",
    "support_domain_receipt_payload",
    "typed_interface_receipt_payload",
    "typed_language_event_receipt_payload",
    "typed_phase_calibration_receipt_payload",
)
