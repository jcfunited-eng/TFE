"""Focused custody and truth checks for the administrator Guala surface."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import subprocess

import pytest


ROOT = Path(__file__).resolve().parents[1]
WEB_ROOT = ROOT / "web"
WEB = WEB_ROOT / "src"
DEPLOY = (ROOT / "tools" / "deploy_to_prod_with_evidence.sh").read_text()

PAGE = (
    WEB / "app" / "admin-console" / "guala-listening" / "page.tsx"
).read_text()
CLIENT = (
    WEB / "components" / "GualaOperatorListeningClient.tsx"
).read_text()
ACTION_CONTRACT = (
    WEB / "lib" / "operator-listening-contract.ts"
).read_text()
OBSERVATION_CONTRACT_PATH = (
    WEB / "lib" / "operator-observation-contract.ts"
)
OBSERVATION_CONTRACT = OBSERVATION_CONTRACT_PATH.read_text()
OBSERVATION_VIEW_PATH = WEB / "lib" / "operator-observation-view.ts"
OBSERVATION_VIEW = OBSERVATION_VIEW_PATH.read_text()
OBSERVATION_ROUTE = (
    WEB
    / "app"
    / "api"
    / "admin"
    / "guala-listening"
    / "observation"
    / "route.ts"
).read_text()
START_ROUTE = (
    WEB
    / "app"
    / "api"
    / "admin"
    / "guala-listening"
    / "start"
    / "route.ts"
).read_text()
POLL_ROUTE = (
    WEB
    / "app"
    / "api"
    / "admin"
    / "guala-listening"
    / "poll"
    / "route.ts"
).read_text()

SPEC = importlib.util.spec_from_file_location(
    "tfe_web_operator_task_contract",
    ROOT / "tools" / "tfe_web_operator_task_contract.py",
)
assert SPEC is not None and SPEC.loader is not None
CONTRACT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CONTRACT)

OPERATOR_SECRET_ARN = (
    "arn:aws:secretsmanager:us-east-1:123456789012:"
    "secret:production/guala-operator-AbCdEf"
)
CLERK_SECRET_ARN = (
    "arn:aws:secretsmanager:us-east-1:123456789012:"
    "secret:production/clerk-AbCdEf"
)


def _task_definition() -> dict:
    return {
        "family": "tfe-web-task",
        "containerDefinitions": [
            {
                "name": "tfe-web",
                "environment": [
                    {"name": "EXISTING", "value": "retained"},
                    {
                        "name": "GUALA_OPERATOR_API_KEY",
                        "value": "forbidden-plaintext",
                    },
                    {
                        "name": "TFE_PUBLIC_BASE_URL",
                        "value": "https://stale.invalid",
                    },
                ],
                "secrets": [
                    {
                        "name": "CLERK_SECRET_KEY",
                        "valueFrom": "arn:aws:secretsmanager:us-east-1:"
                        "123456789012:secret:stale",
                    },
                ],
            }
        ],
    }


def _snapshot() -> dict:
    fields = [
        ["D_k", 1],
        ["M_k", 2],
        ["R_rev_k", 3],
        ["U_star_k", 4],
        ["C_k", 5],
        ["P_k", 6],
        ["B_k", 7],
    ]
    mechanism_ids = (
        "receptor:sight",
        "receptor:sound",
        "receptor:touch",
        "receptor:smell",
        "receptor:taste",
        "receptor:body",
        "state:embodiment",
        "state:internal-physical-chemical",
        "state:neurochemical-flow",
        "state:needs",
        "state:place-world-continuity",
        "growth:neuron-population",
        "growth:mosaic",
        "growth:mosaic-relations",
        "growth:tapestry",
        "growth:tapestry-relations",
        "state:recognition-attention",
        "state:other-perspective-model",
        "state:recovery",
        "state:deliberation",
        "action:embodied",
        "growth:play",
        "state:sensed-consequence",
        "growth:dream-internally-simulated",
        "growth:wake-test",
        "growth:weave",
        "growth:embodied-glyph-curriculum",
        "settlement:l6",
    )
    return {
        "schema": "guala.observation_snapshot.v5",
        "observed_at_tick": 41,
        "identity": "guala",
        "snapshot_receipt_sha256": "a" * 64,
        "full_field_authority": {
            "available": True,
            "status": "observed",
            "view_contract": {
                "decision_authority": False,
                "projection": "latest_exact_tuple_per_substream",
                "projection_loss": "earlier temporal tuples are omitted",
                "required_fields": [
                    "D_k",
                    "M_k",
                    "R_rev_k",
                    "U_star_k",
                    "C_k",
                    "P_k",
                    "B_k",
                ],
            },
            "senses": [
                {
                    "sense": "hearing",
                    "state": "observed",
                    "substreams": [
                        {
                            "substream_id": "left-ear",
                            "tuple_index": 9,
                            "fields": fields,
                        }
                    ],
                }
            ],
        },
        "passive_whole_organism_thing_learning": {
            "available": True,
            "status": "observed",
            "master_sense": None,
            "whole_organism_permanent_wiring": {
                "schema": (
                    "guala.whole_organism.permanent_wiring."
                    "observation.v2"
                ),
                "status": "mounted",
                "manifest_state": {
                    "schema": (
                        "guala.whole_organism.manifest_state.v1"
                    ),
                    "status": "mounted",
                    "mechanism_count": 28,
                    "manifest_receipt_sha256": "d" * 64,
                    "mechanisms": [
                        {
                            "mechanism_id": mechanism_id,
                            "availability": "available",
                            "category": "test_category",
                            "kind": "stateful",
                            "realization": "software_owner",
                        }
                        for mechanism_id in mechanism_ids
                    ],
                },
                "latest_episode_activity": {
                    "schema": (
                        "guala.whole_organism."
                        "latest_episode_activity.v1"
                    ),
                    "status": "not_observed_since_process_start",
                    "reason": (
                        "no_post_start_episode_contribution_receipt"
                    ),
                    "contribution_states": None,
                    "activity_counts": {
                        "perturbed": None,
                        "quiescent": None,
                        "unavailable": None,
                    },
                },
                "current_owner_state": {
                    "schema": (
                        "guala.whole_organism.current_owner_state.v1"
                    ),
                    "status": "observed",
                    "mechanisms": {
                        mechanism_id: {
                            "mechanism_id": mechanism_id,
                            "availability": "available",
                        }
                        for mechanism_id in mechanism_ids
                    },
                },
            },
            "latest_resolution": {"state": "not_observed"},
            "reciprocal_exact_trace": {
                "status": "observed",
                "final_recognition_authority": False,
            },
        },
        "persistence_health": {
            "schema": "guala.persistence_health.observation.v1",
            "diary": {"available": False, "status": "retired"},
            "physical_bytes": {
                "available": False,
                "reason": "physical_byte_authority_unavailable",
            },
        },
        "whole_organism_cognitive_progression": {
            "schema": (
                "guala.whole_organism_cognitive_progression.status.v1"
            ),
            "status": "not_mounted",
        },
        "dreaming": {
            "schema": "guala.dreaming.status.v1",
            "status": "not_mounted",
            "available": False,
        },
        "neuron_population": {
            "schema": "guala.whole_organism_neuron_population.status.v1",
            "state": "quiescent",
            "neuron_count": 8,
            "authority_receipt_sha256": "b" * 64,
        },
        "internal_neurochemical_flow": {
            "schema": (
                "guala.whole_organism_neurochemical_mount.status.v1"
            ),
            "state": "active",
            "transition_count": 3,
            "authority_receipt_sha256": "c" * 64,
        },
    }


def _compile_typescript(tmp_path: Path, *paths: Path) -> Path:
    output = tmp_path / "compiled"
    command = [
        "node",
        "node_modules/typescript/bin/tsc",
        *[str(path) for path in paths],
        "--target",
        "ES2022",
        "--module",
        "commonjs",
        "--moduleResolution",
        "node",
        "--skipLibCheck",
        "--outDir",
        str(output),
    ]
    result = subprocess.run(
        command,
        cwd=WEB_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    return output


def test_task_contract_keeps_secrets_server_side_and_origins_exact():
    result = CONTRACT.apply_operator_contract(
        _task_definition(),
        operator_secret_arn=OPERATOR_SECRET_ARN,
        clerk_secret_arn=CLERK_SECRET_ARN,
        operator_api_origin="https://dsf-ai.example",
        public_base_url="https://tfe.example",
    )
    container = result["containerDefinitions"][0]
    environment = {
        item["name"]: item["value"]
        for item in container["environment"]
    }
    secrets = {
        item["name"]: item["valueFrom"]
        for item in container["secrets"]
    }
    assert environment == {
        "EXISTING": "retained",
        "GUALA_OPERATOR_API_ORIGIN": "https://dsf-ai.example",
        "GUALA_SELF_BODY_PORT_ID": "guala.embodiment.w1",
        "TFE_PUBLIC_BASE_URL": "https://tfe.example",
    }
    assert secrets == {
        "CLERK_SECRET_KEY": CLERK_SECRET_ARN,
        "GUALA_OPERATOR_API_KEY": OPERATOR_SECRET_ARN,
    }


@pytest.mark.parametrize(
    "public_origin",
    (
        "",
        "http://tfe.example",
        "https://0.0.0.0",
        "https://tfe.example/path",
        "https://user:secret@tfe.example",
    ),
)
def test_task_contract_rejects_non_exact_public_origins(public_origin):
    with pytest.raises(CONTRACT.OperatorTaskContractError):
        CONTRACT.apply_operator_contract(
            _task_definition(),
            operator_secret_arn=OPERATOR_SECRET_ARN,
            clerk_secret_arn=CLERK_SECRET_ARN,
            operator_api_origin="https://dsf-ai.example",
            public_base_url=public_origin,
        )


def test_page_and_all_bff_routes_are_clerk_admin_only():
    assert "requireServerClerkAdminUser" in PAGE
    for route in (OBSERVATION_ROUTE, START_ROUTE, POLL_ROUTE):
        assert "getCurrentClerkUser" in route
        assert 'user.role !== "admin"' in route
        assert "Cache-Control" in route
        assert "no-store" in route
        assert "GUALA_OPERATOR_API_KEY" not in route
    assert "export async function GET()" in OBSERVATION_ROUTE
    assert "readOperatorObservation()" in OBSERVATION_ROUTE
    assert "export async function POST" not in OBSERVATION_ROUTE


def test_read_only_bff_validates_v5_and_preserves_the_complete_field():
    for required in (
        "guala.observation_snapshot.v5",
        "/api/v1/gualaloom/observation",
        "passive_whole_organism_thing_learning",
        "whole_organism_permanent_wiring",
        "manifest_state",
        "latest_episode_activity",
        "current_owner_state",
        "not_observed_since_process_start",
        "latest_resolution",
        "reciprocal_exact_trace",
        "master_sense",
        "persistence_health",
        "diary",
        "physical_bytes",
        "whole_organism_cognitive_progression",
        "dreaming",
        "neuron_population",
        "internal_neurochemical_flow",
        "tapestry_relations",
        "recognition_attention",
        "other_perspective_model",
        "reflection_meta_monitor",
        "durable_sensed_consequence",
        "dream_wake_weave",
        "embodied_glyph_curriculum",
        "embodied_reading_lesson_controller",
        "mechanism_counts_states",
        "cold_persistence_bounds",
        "decision_authority",
        "projection_loss",
    ):
        assert required in OBSERVATION_CONTRACT
    for field in (
        "D_k",
        "M_k",
        "R_rev_k",
        "U_star_k",
        "C_k",
        "P_k",
        "B_k",
    ):
        assert field in OBSERVATION_CONTRACT
    assert 'method: "GET"' in OBSERVATION_CONTRACT
    assert '"X-API-Key": requireOperatorApiKey()' in OBSERVATION_CONTRACT
    assert "JSON.stringify" not in OBSERVATION_CONTRACT


def test_browser_reads_only_the_authenticated_same_origin_bff():
    assert (
        '"/api/admin/guala-listening/observation"' in CLIENT
    )
    assert 'method: "GET"' in CLIENT
    assert 'credentials: "same-origin"' in CLIENT
    assert "GUALA_OPERATOR_API_ORIGIN" not in CLIENT
    assert "GUALA_OPERATOR_API_KEY" not in CLIENT
    assert "CLERK_SECRET_KEY" not in CLIENT
    assert "execute-api" not in CLIENT
    assert "http://" not in CLIENT
    assert "https://" not in CLIENT


def test_browser_maps_exact_runtime_truth_without_cognitive_claims():
    combined = CLIENT + OBSERVATION_VIEW
    for required in (
        "guala.observation_snapshot.v5",
        "passive_whole_organism_thing_learning",
        "whole_organism_permanent_wiring",
        "latest_resolution",
        "reciprocal_exact_trace",
        "master_sense",
        "persistence_health",
        "diary",
        "physical_bytes",
        "whole_organism_cognitive_progression",
        "dreaming",
        "decision_authority",
        "projection_loss",
        "live browser audiovisual",
        "modality-neutral",
        "at least two",
    ):
        assert required in combined
    for field in (
        "D_k",
        "M_k",
        "R_rev_k",
        "U_star_k",
        "C_k",
        "P_k",
        "B_k",
    ):
        assert field in OBSERVATION_VIEW
    assert "does not teach, mutate, recognize words" in CLIENT
    assert "master_sense: none" in OBSERVATION_VIEW
    assert "unknown / not supplied" in OBSERVATION_VIEW
    assert "complete field unavailable" in OBSERVATION_VIEW


def test_action_trial_remains_separate_and_explicitly_non_cognitive():
    assert "Separate physical action trial — non-cognitive" in CLIENT
    assert "Completion does not prove hearing, word learning" in CLIENT
    assert "No cognitive interpretation is" in CLIENT
    assert '"/api/admin/guala-listening/start"' in CLIENT
    assert '"/api/admin/guala-listening/poll"' in CLIENT
    assert "GUALA_ASYNC_START_PATH" in ACTION_CONTRACT
    assert "GUALA_ASYNC_POLL_PATH" in ACTION_CONTRACT
    assert "enforceOperatorCsrf(request)" in ACTION_CONTRACT
    assert 'fetchSite !== "same-origin"' in ACTION_CONTRACT


def test_observation_projection_renders_exact_served_values(tmp_path):
    output = _compile_typescript(tmp_path, OBSERVATION_VIEW_PATH)
    module = output / "operator-observation-view.js"
    script = """
const viewModule = require(process.argv[1]);
const snapshot = JSON.parse(process.argv[2]);
const projected = viewModule.projectOperatorObservation(snapshot);
process.stdout.write(JSON.stringify(projected));
"""
    result = subprocess.run(
        [
            "node",
            "-e",
            script,
            str(module),
            json.dumps(_snapshot(), separators=(",", ":")),
        ],
        cwd=WEB_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    projected = json.loads(result.stdout)
    assert projected["identity"] == "guala"
    assert projected["tick"] == "41"
    assert projected["receipt"] == "a" * 64
    assert projected["masterSense"] == {
        "state": "available",
        "text": "master_sense: none",
    }
    assert projected["permanentWiring"]["state"] == "available"
    assert (
        '"status": "not_observed_since_process_start"'
        in projected["permanentWiring"]["text"]
    )
    assert projected["persistenceDiary"]["state"] == "unavailable"
    assert projected["physicalBytes"]["state"] == "unavailable"
    assert projected["cognitiveProgression"]["state"] == "unavailable"
    assert projected["dreaming"]["state"] == "unavailable"
    brain = {
        value["key"]: value
        for value in projected["brainWiringPanels"]
    }
    assert brain["neuron_population"]["value"]["state"] == "quiescent"
    assert '"neuron_count": 8' in brain["neuron_population"]["value"]["text"]
    assert (
        brain["internal_neurochemical_flow"]["value"]["state"]
        == "available"
    )
    assert (
        brain["tapestry_relations"]["value"]
        == {
            "state": "unavailable",
            "text": "unavailable / not supplied",
        }
    )
    assert projected["fullFieldContract"]["state"] == "available"
    assert projected["fullFieldRows"] == [
        {
            "sense": "hearing",
            "state": "observed",
            "substream": "left-ear",
            "tuple": "9",
            "fields": (
                "D_k=1 · M_k=2 · R_rev_k=3 · U_star_k=4 · "
                "C_k=5 · P_k=6 · B_k=7"
            ),
        }
    ]


def test_server_contract_accepts_exact_snapshot_and_rejects_field_loss(
    tmp_path,
):
    output = _compile_typescript(tmp_path, OBSERVATION_CONTRACT_PATH)
    module = output / "operator-observation-contract.js"
    accepted = _snapshot()
    reduced = _snapshot()
    reduced["full_field_authority"]["senses"][0]["substreams"][0][
        "fields"
    ] = reduced["full_field_authority"]["senses"][0]["substreams"][0][
        "fields"
    ][:-1]
    script = """
const contract = require(process.argv[1]);
const accepted = JSON.parse(process.argv[2]);
const reduced = JSON.parse(process.argv[3]);
contract.validateObservationSnapshot(accepted);
let code = "not_rejected";
try {
  contract.validateObservationSnapshot(reduced);
} catch (error) {
  code = error.code;
}
process.stdout.write(code);
"""
    result = subprocess.run(
        [
            "node",
            "-e",
            script,
            str(module),
            json.dumps(accepted, separators=(",", ":")),
            json.dumps(reduced, separators=(",", ":")),
        ],
        cwd=WEB_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout == "upstream_full_field_tuple_invalid"


def test_server_contract_tolerates_absent_future_brain_owner_records(
    tmp_path,
):
    output = _compile_typescript(tmp_path, OBSERVATION_CONTRACT_PATH)
    module = output / "operator-observation-contract.js"
    snapshot = _snapshot()
    del snapshot["neuron_population"]
    del snapshot["internal_neurochemical_flow"]
    script = """
const contract = require(process.argv[1]);
contract.validateObservationSnapshot(JSON.parse(process.argv[2]));
process.stdout.write("accepted");
"""
    result = subprocess.run(
        [
            "node",
            "-e",
            script,
            str(module),
            json.dumps(snapshot, separators=(",", ":")),
        ],
        cwd=WEB_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout == "accepted"


def test_server_contract_rejects_missing_activity_reported_as_zero(
    tmp_path,
):
    output = _compile_typescript(tmp_path, OBSERVATION_CONTRACT_PATH)
    module = output / "operator-observation-contract.js"
    snapshot = _snapshot()
    activity = snapshot[
        "passive_whole_organism_thing_learning"
    ]["whole_organism_permanent_wiring"]["latest_episode_activity"]
    activity["activity_counts"] = {
        "perturbed": 0,
        "quiescent": 0,
        "unavailable": 0,
    }
    script = """
const contract = require(process.argv[1]);
let code = "not_rejected";
try {
  contract.validateObservationSnapshot(JSON.parse(process.argv[2]));
} catch (error) {
  code = error.code;
}
process.stdout.write(code);
"""
    result = subprocess.run(
        [
            "node",
            "-e",
            script,
            str(module),
            json.dumps(snapshot, separators=(",", ":")),
        ],
        cwd=WEB_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout == (
        "upstream_permanent_wiring_activity_invalid"
    )


def test_redirects_are_source_bound_to_required_tfe_origin():
    external = (WEB / "lib" / "external-url.ts").read_text()
    proxy = (WEB / "proxy.ts").read_text()
    assert "TFE_PUBLIC_BASE_URL" in external
    assert "is required" in external
    assert 'parsed.protocol !== "https:"' in external
    assert 'parsed.hostname === "0.0.0.0"' in external
    assert "x-forwarded-host" not in external
    assert 'request.headers.get("host")' not in external
    assert 'buildExternalUrl(request, "/sign-in")' in proxy
    assert "execute-api" not in proxy


def test_deploy_contract_is_secret_only_and_fail_closed():
    assert (
        "GUALA_OPERATOR_API_SECRET_ID="
        '"${GUALA_OPERATOR_API_SECRET_ID:?'
    ) in DEPLOY
    assert "CLERK_SECRET_ID=" + '"${CLERK_SECRET_ID:?' in DEPLOY
    assert "secretsmanager:GetSecretValue" in DEPLOY
    assert "kms:Decrypt" in DEPLOY
    assert "tfe_web_operator_task_contract.py" in DEPLOY
