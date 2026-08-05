from __future__ import annotations

import hashlib
import json
from dataclasses import replace
from pathlib import Path
from urllib.request import Request

import pytest

from tools.verify_guala_loom_live_cutover import (
    CAUSAL_THING_SCHEMA,
    FULL_FIELD_NAMES,
    MAX_OBSERVATION_BYTES,
    OBSERVATION_SCHEMA,
    SIGHT_ARTICULATION_SCHEMA,
    VERIFICATION_SCHEMA,
    CutoverVerificationError,
    VerificationConfig,
    verify_live_cutover,
)


ROOT = Path(__file__).resolve().parents[1]
STATIC = ROOT / "dsf_ai_service" / "static"
BASE = "https://example.test"
OBSERVATION_URL = BASE + "/api/v1/gualaloom/observation"
TRANSIENT_ACT_URL = BASE + "/api/v1/causal-inquiry/transient-act"
TRANSIENT_CONSEQUENCE_URL = (
    BASE + "/api/v1/causal-inquiry/transient-consequence"
)
ACTION_EXPERIENCE_URL = BASE + "/api/v1/embodiment/action-experience"
TRIAL_START_URL = BASE + "/api/v1/embodiment/learned-body-act-trial"
TRIAL_POLL_URL = TRIAL_START_URL + "/" + ("0" * 64)
RETIRED_BOOTSTRAP_URL = BASE + "/api/v1/causal-inquiry/tutor-bootstrap"
GUALALOOM_URL = BASE + "/gualaloom.html"
LOOMSCAN_URL = BASE + "/loomscan.html"


class _Response:
    def __init__(
        self,
        *,
        url: str,
        body: bytes,
        content_type: str,
        status: int = 200,
        content_length: str | None = None,
    ) -> None:
        self.status = status
        self._url = url
        self._body = body
        self._offset = 0
        self.headers = {
            "Content-Type": content_type,
            "Content-Length": (
                str(len(body))
                if content_length is None
                else content_length
            ),
        }

    def read(self, amount: int = -1) -> bytes:
        if amount < 0:
            amount = len(self._body) - self._offset
        result = self._body[self._offset:self._offset + amount]
        self._offset += len(result)
        return result

    def geturl(self) -> str:
        return self._url

    def __enter__(self) -> "_Response":
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        return None


class _Opener:
    def __init__(
        self,
        responses: dict[str, _Response],
        *,
        failure: BaseException | None = None,
    ) -> None:
        self.responses = responses
        self.failure = failure
        self.calls: list[tuple[str, str, int]] = []

    def open(self, request: Request, timeout: int) -> _Response:
        self.calls.append(
            (request.full_url, request.get_method(), timeout)
        )
        if self.failure is not None:
            raise self.failure
        return self.responses[request.full_url]


def _with_receipt(payload: dict[str, object]) -> dict[str, object]:
    encoded = json.dumps(
        payload,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return {
        **payload,
        "snapshot_receipt_sha256": hashlib.sha256(encoded).hexdigest(),
    }


def _observation() -> dict[str, object]:
    payload = {
        "schema": OBSERVATION_SCHEMA,
        "observed_at_tick": 17,
        "identity": "guala-test-identity",
        "embodiment": {"status": "observed"},
        "embodied_action": {"status": "idle"},
        "full_field_authority": {
            "available": True,
            "senses": [{
                "sense": "sound",
                "state": "observed",
                "substreams": [{
                    "substream_id": "left-ear-0",
                    "fields": [
                        [name, f"{index}/1"]
                        for index, name in enumerate(
                            FULL_FIELD_NAMES,
                            start=1,
                        )
                    ],
                }],
            }],
            "view_contract": {
                "decision_authority": False,
                "projection": "latest_exact_tuple_per_substream",
                "projection_loss": "earlier temporal tuples omitted",
                "required_fields": list(FULL_FIELD_NAMES),
            },
        },
        "integrated_thing_memory": {
            "schema": CAUSAL_THING_SCHEMA,
            "status": "observed",
            "authorities": {
                "cognition": False,
                "decision": False,
                "meaning": False,
            },
            "full_field_preserved_upstream": True,
            "reduced_approximation": False,
        },
        "sight_evoked_articulatory_action": {
            "schema": SIGHT_ARTICULATION_SCHEMA,
            "status": "not_observed",
            "authorities": {
                "cognition": False,
                "decision": False,
                "label": False,
                "legacy_route": False,
                "meaning": False,
                "speech_understanding": False,
                "transcript": False,
                "word": False,
            },
            "retained_pcm_bytes": 0,
            "transient_act": {
                "committed": False,
                "pcm_byte_count": 0,
                "pcm_sha256": None,
            },
        },
        "causal_action": {"status": "idle"},
        "causal_thing_action": {
            "full_dsf_field_preserved": True,
            "reduced_approximation": False,
        },
        "passive_whole_organism_thing_learning": {
            "available": True,
            "master_sense": None,
            "whole_organism_permanent_wiring": {
                "status": "not_mounted",
            },
            "latest_resolution": {"state": "not_observed"},
            "reciprocal_exact_trace": {
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
    }
    return _with_receipt(payload)


def _json(value: object) -> bytes:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _config() -> VerificationConfig:
    return VerificationConfig(
        observation_url=OBSERVATION_URL,
        causal_inquiry_transient_act_url=TRANSIENT_ACT_URL,
        causal_inquiry_transient_consequence_url=(
            TRANSIENT_CONSEQUENCE_URL
        ),
        embodiment_action_experience_url=ACTION_EXPERIENCE_URL,
        learned_body_act_trial_start_url=TRIAL_START_URL,
        learned_body_act_trial_poll_url=TRIAL_POLL_URL,
        retired_tutor_bootstrap_url=RETIRED_BOOTSTRAP_URL,
        gualaloom_url=GUALALOOM_URL,
        loomscan_url=LOOMSCAN_URL,
        reviewed_static_dir=STATIC,
        timeout_seconds=7,
    )


def _opener(
    *,
    observation: bytes | None = None,
    gualaloom: bytes | None = None,
    loomscan: bytes | None = None,
    observation_content_length: str | None = None,
    changed_route_status: tuple[str, int] | None = None,
) -> _Opener:
    route_status = {
        TRANSIENT_ACT_URL: 401,
        TRANSIENT_CONSEQUENCE_URL: 401,
        ACTION_EXPERIENCE_URL: 401,
        TRIAL_START_URL: 401,
        TRIAL_POLL_URL: 401,
        RETIRED_BOOTSTRAP_URL: 404,
    }
    if changed_route_status is not None:
        route_status[changed_route_status[0]] = changed_route_status[1]
    responses = {
        OBSERVATION_URL: _Response(
            url=OBSERVATION_URL,
            body=_json(_observation()) if observation is None else observation,
            content_type="application/json",
            content_length=observation_content_length,
        ),
        GUALALOOM_URL: _Response(
            url=GUALALOOM_URL,
            body=(
                (STATIC / "gualaloom.html").read_bytes()
                if gualaloom is None else gualaloom
            ),
            content_type="text/html",
        ),
        LOOMSCAN_URL: _Response(
            url=LOOMSCAN_URL,
            body=(
                (STATIC / "loomscan.html").read_bytes()
                if loomscan is None else loomscan
            ),
            content_type="text/html",
        ),
    }
    for url, status in route_status.items():
        responses[url] = _Response(
            url=url,
            body=b'{"detail":"boundary"}',
            content_type="application/json",
            status=status,
        )
    return _Opener(responses)


def _failure(opener: _Opener) -> CutoverVerificationError:
    with pytest.raises(CutoverVerificationError) as captured:
        verify_live_cutover(_config(), opener=opener)
    return captured.value


def test_exact_reviewed_observation_surfaces_pass() -> None:
    result = verify_live_cutover(_config(), opener=_opener())

    assert result["schema"] == VERIFICATION_SCHEMA
    assert result["status"] == "verified"
    assert set(result["resources"]) == {
        "gualaloom",
        "loomscan",
        "observation",
    }
    assert result["resources"]["observation"]["schema"] == (
        OBSERVATION_SCHEMA
    )
    assert result["resources"]["gualaloom"]["sha256"] == hashlib.sha256(
        (STATIC / "gualaloom.html").read_bytes()
    ).hexdigest()
    assert result["resources"]["loomscan"]["sha256"] == hashlib.sha256(
        (STATIC / "loomscan.html").read_bytes()
    ).hexdigest()
    assert len(result["route_boundaries"]) == 6


@pytest.mark.parametrize(
    "url,status,code",
    (
        (
            TRANSIENT_ACT_URL,
            404,
            "causal_inquiry_transient_act.http_status",
        ),
        (
            TRIAL_POLL_URL,
            404,
            "learned_body_act_trial_poll.http_status",
        ),
        (
            RETIRED_BOOTSTRAP_URL,
            401,
            "retired_causal_inquiry_tutor_bootstrap.http_status",
        ),
    ),
)
def test_route_boundary_change_fails_closed(
    url: str,
    status: int,
    code: str,
) -> None:
    error = _failure(_opener(changed_route_status=(url, status)))
    assert error.code == code


def test_legacy_observation_schema_fails_closed() -> None:
    value = _observation()
    value["schema"] = "guala.observation_snapshot.v4"
    payload = {
        key: item
        for key, item in value.items()
        if key != "snapshot_receipt_sha256"
    }
    error = _failure(_opener(observation=_json(_with_receipt(payload))))
    assert error.code == "observation.schema"


def test_stale_snapshot_receipt_fails_closed() -> None:
    value = _observation()
    value["observed_at_tick"] = 18
    error = _failure(_opener(observation=_json(value)))
    assert error.code == "observation.snapshot_receipt"


@pytest.mark.parametrize(
    "mutation,code",
    (
        (
            b"<input id=\"msg\" type=\"text\"></body>",
            "gualaloom.typed_chat",
        ),
        (
            b"window.speechSynthesis.cancel();</script>",
            "gualaloom.browser_speech",
        ),
        (
            b"fetch('/api/v1/gualaloom/chi_density');</script>",
            "gualaloom.chi_atlas_polling",
        ),
        (
            b"fetch('/api/v1/gualaloom/events');</script>",
            "gualaloom.retired_surface",
        ),
    ),
)
def test_retired_browser_authority_fails_closed(
    mutation: bytes,
    code: str,
) -> None:
    source = (STATIC / "gualaloom.html").read_bytes()
    marker = b"</body>" if mutation.startswith(b"<input") else b"</script>"
    error = _failure(_opener(
        gualaloom=source.replace(marker, mutation),
    ))
    assert error.code == code


def test_unreviewed_static_bytes_fail_closed() -> None:
    source = (STATIC / "loomscan.html").read_bytes()
    error = _failure(_opener(loomscan=source + b"\n<!-- changed -->\n"))
    assert error.code == "loomscan.reviewed_content_mismatch"


def test_declared_oversize_response_fails_without_reading() -> None:
    error = _failure(_opener(
        observation_content_length=str(MAX_OBSERVATION_BYTES + 1),
    ))
    assert error.code == "observation.response_too_large"


def test_timeout_is_stable_and_fail_closed() -> None:
    error = _failure(_Opener({}, failure=TimeoutError()))
    assert error.code == "observation.transport"


@pytest.mark.parametrize("timeout", [True, 0, 61, 1.5])
def test_timeout_configuration_cannot_weaken_boundary(
    timeout: object,
) -> None:
    config = replace(_config(), timeout_seconds=timeout)  # type: ignore[arg-type]
    with pytest.raises(CutoverVerificationError) as captured:
        verify_live_cutover(config, opener=_opener())
    assert captured.value.code == "configuration.timeout"
