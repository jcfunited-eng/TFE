from __future__ import annotations

import pytest

from dsf_ai_service.substrate.w1_acoustic_emitter import (
    AuthenticatedW1AcousticEmission,
    W1AcousticEmitterAuthority,
)
from tests.test_w1_audiovisual_physical_evidence import (
    EMISSION_KEY,
    _authority,
    _emission,
    _execution,
    _vocal_execution,
    _world,
)


def test_retained_emission_remains_verifiable_after_causal_world_advance():
    world = _world()
    physical = _authority(world)
    epoch = physical.open_epoch()
    vocal = _vocal_execution(world, epoch)
    emission = _emission(physical, epoch, vocal)
    physical.mount(
        epoch_token=epoch,
        sequence=0,
        execution_receipt=vocal,
        acoustic_emission=emission,
    )
    _execution(world)
    emitter = W1AcousticEmitterAuthority(
        authority_key=EMISSION_KEY,
        world_authority=world,
    )

    emitter.verify_retained_emission(
        emission,
        observation_snapshot=vocal.after,
        execution_receipt=vocal,
    )
    with pytest.raises(
        ValueError,
        match="differs from its authenticated emission",
    ):
        emitter.verify_emission(
            emission,
            observation_snapshot=vocal.after,
            execution_receipt=vocal,
        )
    tampered_pcm = bytes([emission.pcm_s16le[0] ^ 1]) + (
        emission.pcm_s16le[1:]
    )
    with pytest.raises(
        ValueError,
        match="retained acoustic pressure differs",
    ):
        emitter.verify_retained_emission(
            AuthenticatedW1AcousticEmission(
                receipt=emission.receipt,
                pcm_s16le=tampered_pcm,
            ),
            observation_snapshot=vocal.after,
            execution_receipt=vocal,
        )
