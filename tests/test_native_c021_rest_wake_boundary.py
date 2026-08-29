"""C-021 exact native-rest evidence at the production translation boundary."""

from __future__ import annotations

from types import SimpleNamespace

from dsf_ai_service import native_production_app as production


def test_unattended_interval_preserves_native_recovered_neuron_count(
    monkeypatch,
) -> None:
    before = {
        key: (0, 1) for key in production._UNATTENDED_EXACT_ENERGY_KEYS
    }
    after = dict(before)
    after["dissipated_energy_zeptojoules"] = (1, 1)
    after["organism_tick"] = 9
    after["state_sha256"] = "ab" * 32
    records = iter((before, after))

    monkeypatch.setattr(production, "_restored", SimpleNamespace())
    monkeypatch.setattr(production, "_admission", SimpleNamespace())
    monkeypatch.setattr(production, "_native_record", lambda: next(records))
    monkeypatch.setattr(
        production,
        "_unattended_interval_episodes",
        lambda _interval_id: (
            [(object(), [])],
                {
                    "external_luminance_present": False,
                    "external_smell_present": False,
                    "passive_interval_receipt_sha256": "cd" * 32,
                    "retinal_heading_offset_millidegrees": 0,
                    "world_revision_before": 6,
                    "world_revision": 7,
                },
        ),
    )
    monkeypatch.setattr(
        production,
        "_perform_admitted_intake_locked",
        lambda _episodes, _reason, **_kwargs: {
            "hop_count": 1,
            "observation": {"motor_action": None},
            "receptor_ingress": {},
            "totals": {
                "complete_neuron_fractal_count": 0,
                "metabolically_perturbed_body_receptor_count": 0,
                "partial_cue_reassembly_count": 0,
                "physically_transitioned_neuron_count": 1,
                "rest_recovered_neuron_count": 3,
            },
        },
    )
    monkeypatch.setattr(production, "_refresh_public_observation_cache", lambda: None)
    production._external_intake_waiting.clear()

    result = production._attempt_unattended_interval()

    assert result["delivered"] is True
    assert result["outcome"] == "self_maintenance_observed"
    assert result["measured"]["rest_recovered_neuron_count"] == 3


def test_sleep_dream_wake_requires_ordered_native_physical_evidence(
    monkeypatch,
) -> None:
    rest_interval = {
        "organism_tick": 41,
        "rest_recovered_neuron_count": 2,
        "externally_perturbed_neuron_lineages": (),
        "internally_reassembled_formation_cues": (("formation",),),
        "causal_thought_transitions": (("source", "destination"),),
        "motor_unit_recruitments": (),
        "root_yaw_unit_recruitments": (),
        "root_translation_unit_recruitments": (),
        "articulatory_unit_recruitments": (),
    }
    wake_interval = {
        "organism_tick": 42,
        "rest_recovered_neuron_count": 0,
        "externally_perturbed_neuron_lineages": (),
        "internally_reassembled_formation_cues": (),
        "causal_thought_transitions": (),
        "motor_unit_recruitments": (("motor",),),
        "root_yaw_unit_recruitments": (),
        "root_translation_unit_recruitments": (),
        "articulatory_unit_recruitments": (),
    }
    transition = {
        "causal_interval_evidence": (rest_interval, wake_interval),
        "motor_action": {
            "moved": True,
            "sensory_consequence": {
                "organism_identity": "resident-identity",
                "organism_tick": 42,
            },
        },
    }
    monkeypatch.setattr(production, "_last_transition_evidence", transition)

    observed = production._sleep_dream_wake_record()

    assert observed["available"] is True
    assert observed["recovery_organism_tick"] == 41
    assert observed["wake_organism_tick"] == 42
    assert observed["consequence_organism_identity"] == "resident-identity"

    rest_interval["motor_unit_recruitments"] = (("same-interval-action",),)
    refused = production._sleep_dream_wake_record()
    assert refused["available"] is False

    rest_interval["motor_unit_recruitments"] = ()
    rest_interval["externally_perturbed_neuron_lineages"] = ("external",)
    refused = production._sleep_dream_wake_record()
    assert refused["available"] is False
