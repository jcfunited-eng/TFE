from __future__ import annotations

from tools.probe_auditory_full_field_causal_recurrence import RAW_SPEC
from tools.probe_auditory_full_field_causal_resonance import (
    ResonantMemory,
    ResonantPartition,
    _partition_relation,
    _relation,
)
from tools.probe_auditory_full_field_hierarchical_census import (
    ExactPartition,
    HierarchicalSignature,
)
from tools.probe_auditory_full_field_separability_census import (
    AUDITORY_KERNEL_COMPONENT_COUNT,
    _digest,
)


def _sha(name: str) -> str:
    return _digest({"name": name})


def _memory_partition(
    *,
    partition_id: str,
    identity: frozenset[str],
    shared: frozenset[str],
) -> ResonantPartition:
    return ResonantPartition(
        partition_id=partition_id,
        observed_token_sha256s=identity | shared,
        recurrent_token_sha256s=identity | shared,
        shared_token_sha256s=shared,
        identity_token_sha256s=identity,
        source_witness_root_sha256=_sha(
            f"witness-{partition_id}"
        ),
    )


def test_directional_resonance_ignores_extras_but_requires_identity_and_context():
    identity = _sha("identity")
    shared_a = _sha("shared-a")
    shared_b = _sha("shared-b")
    extra = _sha("ambient-extra")
    memory = _memory_partition(
        partition_id="component:0",
        identity=frozenset((identity,)),
        shared=frozenset((shared_a, shared_b)),
    )

    complete = _partition_relation(
        frozenset((identity, shared_a, shared_b, extra)),
        memory,
    )
    missing_identity = _partition_relation(
        frozenset((shared_a, shared_b, extra)),
        memory,
    )
    missing_context = _partition_relation(
        frozenset((identity, extra)),
        memory,
    )

    assert complete["locked"] is True
    assert missing_identity["locked"] is False
    assert missing_context["locked"] is False


def test_complete_component_hierarchy_locks_without_oracle_label_input():
    identity = _sha("identity")
    shared = _sha("shared")
    extra = _sha("extra")
    query_partitions = []
    memory_partitions = []
    for index in range(AUDITORY_KERNEL_COMPONENT_COUNT):
        partition_id = f"component:{index}"
        query_partitions.append(ExactPartition(
            partition_id=partition_id,
            token_sha256s=frozenset((identity, shared, extra)),
            token_root_sha256=_sha(f"query-token-root-{index}"),
            witness_root_sha256=_sha(f"query-witness-root-{index}"),
        ))
        memory_partitions.append(_memory_partition(
            partition_id=partition_id,
            identity=frozenset((identity,)),
            shared=frozenset((shared,)),
        ))
    query = HierarchicalSignature(
        candidate_id=RAW_SPEC.candidate_id,
        partitions=tuple(query_partitions),
        quotient_receipt_sha256=_sha("query-receipt"),
    )
    memory = ResonantMemory(
        candidate_id=RAW_SPEC.candidate_id,
        grounding_receipt_sha256=_sha("opaque-grounding"),
        source_item_ids=tuple(_sha(f"source-{index}") for index in range(5)),
        partitions=tuple(memory_partitions),
        memory_receipt_sha256=_sha("memory-receipt"),
    )

    result = _relation(
        spec=RAW_SPEC,
        query_id=_sha("query"),
        query=query,
        memory=memory,
    )

    assert result["relation_locked"] is True
    assert all(result["component_locks"])
    assert "oracle" not in result
    assert "command" not in result
