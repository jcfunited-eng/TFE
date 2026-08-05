from __future__ import annotations

from tools.audit_auditory_source_filter_mapping import run


def test_source_filter_audit_proves_exact_nonidentifiability() -> None:
    report = run()
    assert report["direct_mapping_exists"] is False
    assert report["implementation_performed"] is False
    assert report["identifiability_proofs"]["magnitude"][
        "products_are_exactly_equal"
    ]
    assert report["identifiability_proofs"]["phase"][
        "phase_sums_are_exactly_equal"
    ]
    assert not any(report["operator_presence"].values())


def test_source_filter_audit_requires_independent_physical_authority() -> None:
    report = run()
    mapping = {
        value["required_quantity"]: value["mapping_state"]
        for value in report["mapping"]
    }
    assert mapping[
        "independently observed glottal excitation event train"
    ] == "missing"
    assert mapping[
        "vocal-tract transfer magnitude and phase independent of excitation"
    ] == "not_identifiable"
    assert "causally independent vocal-excitation field" in report[
        "smallest_missing_physical_authority"
    ]
