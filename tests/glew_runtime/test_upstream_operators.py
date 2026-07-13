import importlib.util
from fractions import Fraction as F

import pytest

from dsf_ai_service.glew_runtime import (
    CausalGrid,
    EvidenceSample,
    EvidenceStream,
    MountedResonanceGraph,
    MountedSupportDomain,
    ReceiptError,
    ReceiptRegistry,
    RequiredEdge,
    ResonanceOperatorAuthority,
    causal_grid_receipt_payload,
    compute_resonance_confirmation,
    compute_support_floor,
    receipt_sha256,
    resonance_graph_receipt_payload,
    resonance_operator_receipt_payload,
    support_domain_receipt_payload,
)
from dsf_ai_service.glew_runtime.certified_backend import (
    CertifiedBackendUnavailable,
    FLINT_VERSION,
    PYTHON_FLINT_VERSION,
    PYTHON_FLINT_WHEEL_SHA256,
    load_pinned_flint,
)


PROFILE = b"glew-profile-fixture-v1"
CALIBRATION = b"port-calibration-fixture-v1"
RELEVANCE = b"port-relevance-fixture-v1"
DIGEST_B = receipt_sha256(RELEVANCE)
CALIBRATION_DIGEST = receipt_sha256(CALIBRATION)
TIMESTAMPS = (F(1), F(2), F(3))
WEIGHTS = (F(1), F(2), F(1))
GRID_RECEIPT = causal_grid_receipt_payload("gate-1", TIMESTAMPS, WEIGHTS)
DIGEST_A = receipt_sha256(GRID_RECEIPT)
OPERATOR_RECEIPT = resonance_operator_receipt_payload("ruf-arb-v1", 256)


def registry(*extra_payloads: bytes) -> ReceiptRegistry:
    return ReceiptRegistry.from_payloads(
        profile_payload=PROFILE,
        receipt_payloads=(
            GRID_RECEIPT,
            CALIBRATION,
            RELEVANCE,
            OPERATOR_RECEIPT,
            *extra_payloads,
        ),
    )


def grid() -> CausalGrid:
    return CausalGrid(
        grid_id="gate-1",
        timestamps=TIMESTAMPS,
        positive_weights=WEIGHTS,
        grid_receipt_sha256=DIGEST_A,
    )


def stream(
    lane: str,
    port: str,
    relevances=(F(1), F(1), F(1)),
    phases=(F(0), F(0), F(0)),
) -> EvidenceStream:
    return EvidenceStream(
        lane_id=lane,
        port_id=port,
        evidence_id=f"{lane}-{port}-fixture",
        source_epoch="epoch-1",
        port_kind="test_receipted_port",
        physical_unit="native_unit",
        profile_binding_sha256=registry().profile_binding_sha256,
        calibration_receipt_sha256=CALIBRATION_DIGEST,
        relevance_receipt_sha256=DIGEST_B,
        samples=tuple(
            EvidenceSample(
                source_index=index,
                timestamp=timestamp,
                signal=F(0),
                relevance=relevance,
                phase_turns=phase,
            )
            for index, (timestamp, relevance, phase) in enumerate(
                zip(grid().timestamps, relevances, phases, strict=True)
            )
        ),
    )


def ball_contains(ball, value: F) -> bool:
    lower = F(ball.lower_mantissa) * F(2) ** ball.lower_exponent
    upper = F(ball.upper_mantissa) * F(2) ** ball.upper_exponent
    return lower <= value <= upper


def support_domain(*keys: tuple[str, str]):
    payload = support_domain_receipt_payload("support-domain-1", keys)
    return (
        MountedSupportDomain(
            domain_id="support-domain-1",
            required_port_keys=keys,
            authority_receipt_sha256=receipt_sha256(payload),
        ),
        payload,
    )


def resonance_authorities(*edges: RequiredEdge):
    graph_payload = resonance_graph_receipt_payload("resonance-graph-1", edges)
    graph = MountedResonanceGraph(
        graph_id="resonance-graph-1",
        required_edges=edges,
        authority_receipt_sha256=receipt_sha256(graph_payload),
    )
    operator = ResonanceOperatorAuthority(
        operator_id="ruf-arb-v1",
        precision_bits=256,
        authority_receipt_sha256=receipt_sha256(OPERATOR_RECEIPT),
    )
    return graph, operator, graph_payload


def test_support_floor_is_exact_lattice_meet_and_retains_optional_port_fact():
    language = stream("language", "typed", (F(1), F(1, 2), F(3, 4)))
    dynamic = stream("touch", "dynamic", (F(2, 3), F(1, 3), F(1, 2)))
    optional = stream("touch", "static", (F(1, 100), F(1, 100), F(1, 100)))

    domain, domain_payload = support_domain(
        ("language", "typed"), ("touch", "dynamic")
    )
    result = compute_support_floor(
        (language, dynamic, optional),
        grid(),
        domain,
        registry(domain_payload),
    )

    assert result.value == F(1, 3)
    facts = {fact.port_key: fact for fact in result.port_facts}
    assert facts[("language", "typed")].support_floor == F(1, 2)
    assert facts[("touch", "dynamic")].support_floor == F(1, 3)
    assert facts[("touch", "static")].support_floor == F(1, 100)
    assert facts[("touch", "static")].required is False


def test_support_floor_empty_required_domain_is_unknown_not_zero():
    with pytest.raises(ReceiptError, match="cannot be empty"):
        # Absence is rejected when mounting, before it could become numeric zero.
        MountedSupportDomain(
            domain_id="empty",
            required_port_keys=(),
            authority_receipt_sha256="a" * 64,
        )


def test_support_floor_missing_required_port_fails_closed():
    domain, domain_payload = support_domain(
        ("language", "typed"), ("sight", "release")
    )
    with pytest.raises(ReceiptError, match="unavailable"):
        compute_support_floor(
            (stream("language", "typed"),),
            grid(),
            domain,
            registry(domain_payload),
        )


def test_support_subset_cannot_change_without_a_matching_mounted_receipt():
    evidence = stream("language", "typed")
    mounted, mounted_payload = support_domain(evidence.key)
    changed = MountedSupportDomain(
        domain_id=mounted.domain_id,
        required_port_keys=(evidence.key, ("sight", "release")),
        authority_receipt_sha256=mounted.authority_receipt_sha256,
    )
    with pytest.raises(ReceiptError, match="does not match"):
        compute_support_floor(
            (evidence,), grid(), changed, registry(mounted_payload)
        )


def test_grid_mismatch_is_not_interpolated():
    evidence = stream("language", "typed")
    other_grid_payload = causal_grid_receipt_payload(
        "other", (F(1), F(5, 2), F(3)), (F(1), F(1), F(1))
    )
    other_grid = CausalGrid(
        grid_id="other",
        timestamps=(F(1), F(5, 2), F(3)),
        positive_weights=(F(1), F(1), F(1)),
        grid_receipt_sha256=receipt_sha256(other_grid_payload),
    )
    domain, domain_payload = support_domain(evidence.key)
    with pytest.raises(ReceiptError, match="interpolation is forbidden"):
        compute_support_floor(
            (evidence,),
            other_grid,
            domain,
            registry(other_grid_payload, domain_payload),
        )


def test_causal_grid_requires_positive_exact_weights():
    with pytest.raises(ReceiptError, match="exactly positive"):
        CausalGrid(
            grid_id="bad-grid",
            timestamps=(F(1),),
            positive_weights=(F(0),),
            grid_receipt_sha256=DIGEST_A,
        )


HAS_FLINT = importlib.util.find_spec("flint") is not None


@pytest.mark.skipif(not HAS_FLINT, reason="pinned certified backend is not on this test path")
def test_pinned_backend_identity_is_enforced_and_receipted():
    flint = load_pinned_flint()
    assert flint.__version__ == PYTHON_FLINT_VERSION
    assert flint.__FLINT_VERSION__ == FLINT_VERSION
    assert PYTHON_FLINT_WHEEL_SHA256 == (
        "376b88cacd30612479e839ffdba887599d3f9c8c0e214852bf80bb2b194e4d76"
    )


@pytest.mark.skipif(not HAS_FLINT, reason="pinned certified backend is not on this test path")
def test_resonance_is_one_for_identical_exact_phase_and_relevance():
    language = stream("language", "typed")
    sight = stream("sight", "release")
    edge = RequiredEdge(language.key, sight.key)
    graph, operator, graph_payload = resonance_authorities(edge)

    result = compute_resonance_confirmation(
        (language, sight), grid(), graph, operator, registry(graph_payload)
    )

    assert ball_contains(result.value, F(1))
    assert ball_contains(result.edge_facts[0].gamma_squared, F(1))
    assert result.edge_facts[0].proved_zero_energy is False


@pytest.mark.skipif(not HAS_FLINT, reason="pinned certified backend is not on this test path")
def test_resonance_cancellation_is_certified_without_float_trigonometry():
    language = stream("language", "typed")
    sight = stream("sight", "release", phases=(F(0), F(1, 2), F(0)))
    # Weights 1,2,1 produce exact cancellation against the fixed language phase.
    edge = RequiredEdge(language.key, sight.key)
    graph, operator, graph_payload = resonance_authorities(edge)

    result = compute_resonance_confirmation(
        (language, sight), grid(), graph, operator, registry(graph_payload)
    )

    assert ball_contains(result.value, F(0))
    assert not ball_contains(result.value, F(1, 1000))


@pytest.mark.skipif(not HAS_FLINT, reason="pinned certified backend is not on this test path")
def test_proved_zero_energy_edge_is_exact_zero():
    language = stream("language", "typed")
    quiet = stream("smell", "native-current", (F(0), F(0), F(0)))
    edge = RequiredEdge(language.key, quiet.key)
    graph, operator, graph_payload = resonance_authorities(edge)

    result = compute_resonance_confirmation(
        (language, quiet), grid(), graph, operator, registry(graph_payload)
    )

    assert result.value.lower_mantissa == 0
    assert result.value.upper_mantissa == 0
    assert ball_contains(result.value, F(0))
    assert result.edge_facts[0].proved_zero_energy is True


def test_missing_certified_backend_fails_closed(monkeypatch):
    import dsf_ai_service.glew_runtime.certified_backend as backend

    real_import = backend.importlib.import_module

    def absent(name):
        if name == "flint":
            raise ImportError("not installed")
        return real_import(name)

    monkeypatch.setattr(backend.importlib, "import_module", absent)
    with pytest.raises(CertifiedBackendUnavailable, match="required"):
        backend.load_pinned_flint()


@pytest.mark.skipif(not HAS_FLINT, reason="pinned certified backend is not on this test path")
def test_multithreaded_arb_context_is_rejected_without_loader_mutation():
    import flint

    original = flint.ctx.threads
    try:
        flint.ctx.threads = 2
        with pytest.raises(CertifiedBackendUnavailable, match="single-thread"):
            load_pinned_flint()
        assert flint.ctx.threads == 2
    finally:
        flint.ctx.threads = original


def test_operator_precision_cannot_change_without_a_matching_mounted_receipt():
    language = stream("language", "typed")
    sight = stream("sight", "release")
    edge = RequiredEdge(language.key, sight.key)
    graph, _, graph_payload = resonance_authorities(edge)
    changed = ResonanceOperatorAuthority(
        operator_id="ruf-arb-v1",
        precision_bits=128,
        authority_receipt_sha256=receipt_sha256(OPERATOR_RECEIPT),
    )
    with pytest.raises(ReceiptError, match="does not match"):
        compute_resonance_confirmation(
            (language, sight),
            grid(),
            graph,
            changed,
            registry(graph_payload),
        )


def test_empty_or_missing_resonance_domain_fails_closed_before_arithmetic():
    language = stream("language", "typed")
    with pytest.raises(ReceiptError, match="empty"):
        MountedResonanceGraph(
            graph_id="empty",
            required_edges=(),
            authority_receipt_sha256="a" * 64,
        )
    edge = RequiredEdge(language.key, ("sight", "release"))
    graph, operator, graph_payload = resonance_authorities(edge)
    with pytest.raises(ReceiptError, match="unavailable"):
        compute_resonance_confirmation(
            (language,),
            grid(),
            graph,
            operator,
            registry(graph_payload),
        )
