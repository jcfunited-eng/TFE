import base64
import hashlib
import json
import sys
from pathlib import Path

import pytest

from tools.publish_channel_books import ChannelSource, build_envelope, main, object_key, parse_s3_uri


def test_envelope_preserves_exact_book_bytes_and_receipt(tmp_path: Path) -> None:
    raw = b'{\n "engine": "test", "cash": 100000.0\n}\n'
    source_path = tmp_path / "book.json"
    source_path.write_bytes(raw)

    body, digest = build_envelope(ChannelSource(channel="CH3", path=source_path))
    envelope = json.loads(body)

    assert envelope["schema"] == "tfe.channel-book.snapshot.v1"
    assert envelope["channel"] == "CH3"
    assert base64.b64decode(envelope["source_bytes_base64"]) == raw
    assert digest == hashlib.sha256(raw).hexdigest()
    assert envelope["source_sha256"] == digest


def test_envelope_rejects_non_object_json(tmp_path: Path) -> None:
    source_path = tmp_path / "book.json"
    source_path.write_text("[]", encoding="utf-8")

    with pytest.raises(ValueError, match="one JSON object"):
        build_envelope(ChannelSource(channel="CH4", path=source_path))


def test_s3_uri_and_key_are_exact() -> None:
    bucket, prefix = parse_s3_uri("s3://example-bucket/a/b/")
    assert bucket == "example-bucket"
    assert prefix == "a/b"
    assert object_key(prefix, "CH6") == "a/b/ch6.json"


def test_non_s3_uri_fails_closed() -> None:
    with pytest.raises(ValueError, match="s3://bucket/prefix"):
        parse_s3_uri("https://example.com/channel-books")


def test_no_channel_arguments_publish_all_in_dry_run(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setattr(sys, "argv", ["publish_channel_books.py", "--dry-run"])

    assert main() == 0

    output = capsys.readouterr().out
    assert "DRY CH3" in output
    assert "DRY CH4" in output
    assert "DRY CH6" in output
