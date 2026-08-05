"""Production W1 embodiment sensory boundary.

The implementation lives in :mod:`w1_physical_receptors`.  This stable module
name is retained because the engine and persisted authority wiring import it.
The former privileged exact-world-geometry transducer has been removed.
"""

from dsf_ai_service.substrate.w1_physical_receptors import (
    OUTCOME_OBSERVATION_SCHEMA,
    RETINA_COLUMNS,
    RETINA_ROWS,
    RETINA_SUBSTREAM_COUNT,
    TRANSDUCER_PROFILE,
    EmbodiedSensoryOutcome,
    EmbodimentSensoryOutcomeAuthority,
    OutcomeObservationReceipt,
    _is_visible,
    physical_receptor_joint_units,
    physical_receptor_substreams,
)

__all__ = (
    "EmbodiedSensoryOutcome",
    "EmbodimentSensoryOutcomeAuthority",
    "OUTCOME_OBSERVATION_SCHEMA",
    "OutcomeObservationReceipt",
    "RETINA_COLUMNS",
    "RETINA_ROWS",
    "RETINA_SUBSTREAM_COUNT",
    "TRANSDUCER_PROFILE",
    "_is_visible",
    "physical_receptor_joint_units",
    "physical_receptor_substreams",
)
