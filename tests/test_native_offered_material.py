"""L-008 local media is preserved before physical sensory presentation."""

from __future__ import annotations

import base64
from io import BytesIO
import json
from types import SimpleNamespace

from fastapi.responses import JSONResponse
from PIL import Image

from dsf_ai_service import native_production_app as production
from dsf_ai_service.bounded_source_media_store import BoundedSourceMediaStore


def _source_bytes() -> bytes:
    target = BytesIO()
    Image.new("RGB", (9, 3), color=(32, 64, 96)).save(target, format="PNG")
    return target.getvalue()


def _payload(*, kind: str = "picture", media_type: str = "image/png") -> dict:
    return {
        "schema": production.OFFERED_MATERIAL_SCHEMA,
        "material_kind": kind,
        "media_type": media_type,
        "origin_locator": "local-source.png",
        "attribution": "Test source creator",
        "rights_basis": "owned_by_offeror",
        "rights_statement": "Created by the offeror for this physical test.",
        "bytes_b64": base64.b64encode(_source_bytes()).decode("ascii"),
    }


def _mount_invitation_and_settlement(monkeypatch) -> list[object]:
    events: list[object] = []

    def invite(*, experience_kind, experience_id, media_receipts):
        invitation = {
            "schema": production.CURRICULUM_INVITATION_SCHEMA,
            "experience_kind": experience_kind,
            "experience_id": experience_id,
            **media_receipts,
            "outcome": "presentable",
            "presentation_eligible": True,
            "invitation_receipt_sha256": "a" * 64,
        }
        production._curriculum_invitation = invitation
        events.append(("invite", experience_id))
        return JSONResponse(
            status_code=200,
            content={"accepted": True, "invitation": invitation},
        )

    def settle(episodes, intake):
        events.append(("settle", episodes, intake))
        return {
            "accepted": True,
            "ok": True,
            "hop_count": len(episodes),
            "persisted": {
                "organism_tick": 8,
                "state_sha256": "b" * 64,
            },
            "observation": {
                "organism_tick": 9,
                "sealed": False,
                "state_sha256": None,
            },
            "receptor_ingress": {},
            "totals": {},
        }

    monkeypatch.setattr(production, "_embodied_curriculum_invitation", invite)
    monkeypatch.setattr(production, "_perform_admitted_intake_locked", settle)
    monkeypatch.setattr(production, "_refresh_public_observation_cache", lambda: None)
    return events


def test_picture_is_in_bounded_custody_before_decode_and_invited_once(
    monkeypatch,
    tmp_path,
) -> None:
    store = BoundedSourceMediaStore(tmp_path / "source-media")
    monkeypatch.setattr(production, "_source_media_store", store)
    events = _mount_invitation_and_settlement(monkeypatch)

    def decode(kind, raw, media_type):
        records = store.inventory(verify_source_bytes=True)
        assert len(records) == 1
        assert store.source_bytes(records[0].receipt_sha256) == raw
        events.append(("decode", kind, media_type))
        return [(0.25,) * production.CARD_SURFACE_PORT_COUNT]

    monkeypatch.setattr(production, "_decode_offered_rasters", decode)
    monkeypatch.setattr(
        production,
        "_offered_visual_episodes",
        lambda _prefix, _rosters: [("physical-light", [])],
    )

    response = production.offered_material(_payload())
    body = json.loads(response.body)

    assert response.status_code == 200
    assert body["accepted"] is True
    assert body["source_media"]["retained_source_bytes"] == len(_source_bytes())
    assert body["source_media"]["semantic_authority"] is False
    assert body["transport_metadata_only"] is True
    assert [event[0] for event in events] == ["decode", "invite", "settle"]
    assert production._curriculum_invitation["presentation_eligible"] is False
    assert production._curriculum_invitation["outcome"] == "presented"
    assert production._curriculum_invitation["presented_organism_tick"] == 9
    assert production._curriculum_invitation["status"] == (
        "local_material_presentation_settled"
    )

    inventory = json.loads(production.source_media_custody().body)
    assert inventory["record_count"] == 1
    assert inventory["total_source_bytes"] == len(_source_bytes())
    receipt = body["source_media"]["receipt_sha256"]
    restored = json.loads(production.source_media_custody_record(receipt).body)
    assert restored["source_bytes_restored_and_verified"] is True
    assert restored["restored_source_bytes_sha256"] == body["source_media"][
        "source_bytes_sha256"
    ]


def test_material_invitation_reports_settlement_and_durability_separately(
    monkeypatch,
) -> None:
    production._curriculum_invitation = {
        "outcome": "presented",
        "presentation_eligible": False,
        "presented_organism_tick": 9,
        "reason": "settled",
        "status": "local_material_presentation_settled",
    }
    monkeypatch.setattr(
        production,
        "_restored",
        SimpleNamespace(
            pointer=SimpleNamespace(
                organism_tick=8,
                state_sha256="a" * 64,
            )
        ),
    )

    pending = production._curriculum_invitation_record()

    assert pending["status"] == "local_material_presentation_settled"
    assert pending["presented_organism_tick"] == 9
    assert pending["durable_through_organism_tick"] == 8
    assert pending["presentation_durable"] is False

    production._restored.pointer.organism_tick = 10
    production._restored.pointer.state_sha256 = "b" * 64
    durable = production._curriculum_invitation_record()

    assert durable["status"] == "local_material_presentation_committed"
    assert durable["durable_through_organism_tick"] == 10
    assert durable["durable_state_sha256"] == "b" * 64
    assert durable["presentation_durable"] is True


def test_video_uses_preserved_bytes_and_one_co_clocked_audiovisual_path(
    monkeypatch,
    tmp_path,
) -> None:
    raw = b"bounded-video-source"
    payload = _payload(kind="video", media_type="video/mp4")
    payload["origin_locator"] = "local-source.mp4"
    payload["bytes_b64"] = base64.b64encode(raw).decode("ascii")
    store = BoundedSourceMediaStore(tmp_path / "source-media")
    monkeypatch.setattr(production, "_source_media_store", store)
    monkeypatch.setattr(production, "COCHLEAR_EARS_AUTHORIZED", True)
    monkeypatch.setattr(production, "_live_hearing_evidence", None)
    events = _mount_invitation_and_settlement(monkeypatch)

    def decode(source):
        assert store.inventory(verify_source_bytes=True)
        assert source == raw
        events.append(("video-decode",))
        return SimpleNamespace(
            frame_png_bytes=(b"frame-one", b"frame-two"),
            pcm_s16le=b"\x01\x00" * 8_000,
            sample_rate_hz=16_000,
            public_projection=lambda: {
                "semantic_authority": False,
                "hop_count": 2,
            },
        )

    monkeypatch.setattr(production, "decode_bounded_video", decode)
    monkeypatch.setattr(production, "_live_frame_luminance", lambda _frame: (0.5,) * 27)
    monkeypatch.setattr(
        production,
        "_live_audiovisual_hop_episodes",
        lambda _prefix, rosters, samples, rate: [
            ("audiovisual", len(rosters), len(samples), rate)
        ],
    )

    response = production.offered_material(payload)
    body = json.loads(response.body)

    assert response.status_code == 200
    assert body["accepted"] is True
    assert body["material_kind"] == "video"
    assert body["presented_raster_count"] == 2
    assert body["presented_sample_count"] == 8_000
    assert body["sensory_projection"]["semantic_authority"] is False
    assert [event[0] for event in events] == ["video-decode", "invite", "settle"]


def test_old_or_semantic_payload_is_refused_before_source_custody(
    monkeypatch,
    tmp_path,
) -> None:
    store = BoundedSourceMediaStore(tmp_path / "source-media")
    monkeypatch.setattr(production, "_source_media_store", store)
    payload = _payload()
    payload["title"] = "injected meaning"

    response = production.offered_material(payload)

    assert response.status_code == 422
    assert store.inventory() == ()
