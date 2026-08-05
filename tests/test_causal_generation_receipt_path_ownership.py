from pathlib import Path

from dsf_ai_service.substrate.deployment_generation import (
    CAUSAL_GENERATION_RECEIPT,
)
from dsf_ai_service.substrate.generation_content_delta import (
    changed_stable_stage_paths,
)
from dsf_ai_service.substrate.immutable_generation_store import (
    ImmutableGenerationStore,
)
from dsf_ai_service.substrate.owner_scoped_persistence import (
    ROLE_RECEIPT,
    ownership_for_path,
)


def test_causal_generation_receipt_has_exact_nondynamic_owner():
    ownership = ownership_for_path(CAUSAL_GENERATION_RECEIPT)

    assert ownership.owner_ids == ("causal_generation_authority",)
    assert ownership.role == ROLE_RECEIPT
    assert ownership.stable_body_required is False
    assert ownership.requires_split is False


def test_prior_causal_generation_receipt_is_not_a_deleted_state_path(
    tmp_path,
):
    store = ImmutableGenerationStore(
        Path(tmp_path) / "store",
        identity="organism-identity",
        required_files=(CAUSAL_GENERATION_RECEIPT,),
        content_addressed=True,
    )
    baseline = store.commit(
        tick=1,
        files={
            CAUSAL_GENERATION_RECEIPT: (
                b'{"schema":"guala.causal_generation.v1"}'
            ),
        },
    )

    stage = Path(tmp_path) / "candidate"
    stage.mkdir()
    (stage / "guala_core.json").write_bytes(b'{"tick":2}')

    assert changed_stable_stage_paths(
        baseline,
        candidate_stage_root=stage,
        candidate_relative_paths=("guala_core.json",),
    ) == ()
