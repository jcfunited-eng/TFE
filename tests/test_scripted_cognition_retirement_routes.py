"""HTTP proof that retired scripted surfaces cannot mutate Guala."""

from __future__ import annotations

from fastapi.testclient import TestClient
import pytest

import dsf_ai_service.app as appmod


@pytest.fixture
def client_without_engine(monkeypatch):
    class _ExplodingEngine:
        def __getattr__(self, name):
            raise AssertionError(
                f"retired HTTP surface accessed engine attribute {name}"
            )

    monkeypatch.setattr(appmod, "_guala", _ExplodingEngine())
    monkeypatch.setattr(appmod, "_GUALALOOM_API_KEY", "")
    return TestClient(appmod.app)


@pytest.mark.parametrize(
    ("method", "path", "kwargs"),
    [
        (
            "post",
            "/api/v1/gualaloom",
            {"json": {"text": "hello guala", "source": "joe"}},
        ),
        (
            "post",
            "/api/v1/gualaloom",
            {
                "json": {
                    "text": "hello guala",
                    "command": "/listen",
                    "source": "joe",
                }
            },
        ),
        (
            "post",
            "/api/v1/gualaloom",
            {
                "json": {
                    "text": "joe",
                    "command": "/presence",
                    "source": "joe",
                }
            },
        ),
        (
            "post",
            "/api/v1/gualaloom",
            {
                "json": {
                    "text": "",
                    "command": "/room",
                    "source": "joe",
                }
            },
        ),
        ("get", "/api/v1/gualaloom/task/historical-task", {}),
        ("get", "/api/v1/auditory/reply/" + "a" * 64, {}),
        ("get", "/api/v1/gualaloom/organs", {}),
        ("get", "/api/v1/gualaloom/thought", {}),
        ("get", "/api/v1/gualaloom/organ_brain_status", {}),
        ("get", "/api/v1/gualaloom/chi_density", {}),
        (
            "post",
            "/api/v1/gualaloom/chi_trace",
            {"json": {"input_text": "hello"}},
        ),
        (
            "post",
            "/api/v1/gualaloom/admin/force_reading",
            {"json": {"corpus_id": "legacy"}},
        ),
        (
            "post",
            "/api/v1/gualaloom/admin/backfill_picture_titles",
            {},
        ),
        (
            "post",
            "/api/v1/gualaloom/admin/backfill_sound_captions",
            {},
        ),
        (
            "post",
            "/api/v1/gualaloom/admin/atlas_surgery",
            {"json": {"operation_id": "legacy"}},
        ),
        (
            "post",
            "/api/v1/teacher/feedback",
            {"json": {"emission_id": "legacy", "source": "joe"}},
        ),
        (
            "post",
            "/api/v1/teacher/correction",
            {
                "json": {
                    "emission_id": "legacy",
                    "corrected_text": "scripted answer",
                    "source": "joe",
                }
            },
        ),
        (
            "post",
            "/api/v1/curriculum/load_corpus",
            {
                "json": {
                    "corpus_id": "legacy",
                    "title": "Legacy",
                    "lines": ["synthetic sentence"],
                }
            },
        ),
        (
            "get",
            "/api/v1/curriculum/load_corpus/job/legacy",
            {},
        ),
        (
            "get",
            "/api/v1/curriculum/corpus_status/legacy",
            {},
        ),
        (
            "post",
            "/api/v1/gualaloom/upload/book",
            {
                "files": {
                    "file": (
                        "legacy.txt",
                        b"synthetic sentence",
                        "text/plain",
                    )
                }
            },
        ),
        (
            "post",
            "/api/v1/embodiment/companion-vocalize",
            {
                "files": {
                    "file": (
                        "mono.wav",
                        b"not admitted",
                        "audio/wav",
                    )
                },
                "data": {"tutor_id": "joe"},
            },
        ),
    ],
)
def test_removed_route_returns_404_before_engine_access(
    client_without_engine,
    method,
    path,
    kwargs,
):
    response = getattr(client_without_engine, method)(path, **kwargs)

    assert response.status_code == 404, response.text
    assert response.json() == {"detail": "Not Found"}


def test_removed_text_derived_causal_action_teaching_returns_404(
    client_without_engine,
):
    response = client_without_engine.post(
        "/api/v1/causal-action/teach",
        json={
            "trigger_experience_id": "a" * 64,
            "action_experience_id": "b" * 64,
            "source": "joe",
        },
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Not Found"}


@pytest.mark.parametrize(
    ("path", "expected_status"),
    [
        ("/api/v1/gualaloom/admin/backup", 409),
        ("/api/v1/gualaloom/admin/restore_from_s3_prefix", 404),
        ("/api/v1/gualaloom/admin/compact_wave_atlas", 404),
        ("/api/v1/gualaloom/admin/migrate_wave_atlas", 404),
        ("/api/v1/gualaloom/admin/amnesty", 404),
    ],
)
def test_retired_flat_persistence_routes_cannot_upload_or_restore(
    client_without_engine,
    monkeypatch,
    path,
    expected_status,
):
    monkeypatch.setattr(appmod, "_REQUIRE_SEALED_STATE", False)

    response = client_without_engine.post(
        path,
        json={"prefix": "legacy-flat-atlas"},
    )

    assert response.status_code == expected_status, response.text


def test_retired_atlas_snapshot_cannot_read_engine(client_without_engine):
    response = client_without_engine.get(
        "/api/v1/gualaloom/admin/atlas_snapshot"
    )

    assert response.status_code == 404, response.text
    assert response.json() == {"detail": "Not Found"}


def test_retired_flat_s3_helpers_fail_before_external_access(monkeypatch):
    def forbidden_client(*_args, **_kwargs):
        raise AssertionError("retired flat persistence reached S3")

    monkeypatch.setattr("boto3.client", forbidden_client)
    with pytest.raises(RuntimeError, match="flat S3 backup is retired"):
        appmod._backup_to_s3("/tmp/not-used")
    with pytest.raises(RuntimeError, match="flat S3 restore is retired"):
        appmod._restore_from_s3("/tmp/not-used")
    with pytest.raises(
        RuntimeError,
        match="unauthenticated local-generation recovery is retired",
    ):
        appmod._recover_from_local_generations("/tmp/not-used")
