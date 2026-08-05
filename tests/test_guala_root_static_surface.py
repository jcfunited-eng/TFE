from __future__ import annotations

import re
import shutil
from pathlib import Path

from fastapi.testclient import TestClient

import dsf_ai_service.app as app_module


ROOT = Path(__file__).resolve().parents[1]
SOURCE_STATIC = ROOT / "dsf_ai_service" / "static"
PUBLIC_FILES = {
    "guala-brain-foundation-v1.png",
    "gualaloom-rich-room-v3.png",
    "gualaloom.html",
    "loomscan.html",
    "legal.html",
    "style.css",
}
LOCAL_REFERENCE = re.compile(
    r"""(?:href|src)=["'](/[^"'#?]+)["']""",
    re.IGNORECASE,
)


def test_root_is_complete_guala_publication(
    monkeypatch,
    tmp_path,
) -> None:
    publication = tmp_path / "publication"
    publication.mkdir()
    for filename in sorted(PUBLIC_FILES):
        shutil.copyfile(
            SOURCE_STATIC / filename,
            publication / filename,
        )
    assert {
        path.name for path in publication.iterdir()
    } == PUBLIC_FILES

    monkeypatch.setattr(
        app_module,
        "STATIC_DIR",
        str(publication),
    )
    client = TestClient(app_module.app)

    root = client.get("/")
    canonical = client.get("/gualaloom.html")
    alias = client.get("/gualaloom")
    assert root.status_code == 200
    assert canonical.status_code == 200
    assert alias.status_code == 200
    assert root.content == canonical.content == alias.content
    assert root.content == (
        publication / "gualaloom.html"
    ).read_bytes()

    lowered = root.content.lower()
    for retired in (
        b'href="/index.html"',
        b'src="/app.js"',
        b"dsf structural analyzer",
        b"cluster screener",
    ):
        assert retired not in lowered

    local_references: set[str] = set()
    for filename in ("gualaloom.html", "loomscan.html", "legal.html"):
        text = (
            publication / filename
        ).read_text(encoding="utf-8")
        local_references.update(LOCAL_REFERENCE.findall(text))
    assert local_references == {
        "/guala-brain-foundation-v1.png",
        "/gualaloom-rich-room-v3.png",
        "/gualaloom.html",
        "/loomscan.html",
        "/legal.html",
        "/style.css",
    }
    for reference in sorted(local_references):
        response = client.get(reference)
        assert response.status_code == 200
        assert response.content == (
            publication / reference.removeprefix("/")
        ).read_bytes()
