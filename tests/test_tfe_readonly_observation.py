import base64
import gzip
import hashlib

import pytest

from tools.tfe_readonly_observation import decode_receipt


def transport():
    raw = b'{"observed_at":"2026-09-22","ledger":[]}'
    encoded = base64.b64encode(gzip.compress(raw, mtime=0)).decode()
    lines = [f"TFE_BEGIN {len(encoded)} {hashlib.sha256(raw).hexdigest()}"]
    lines += [f"TFE_PART {i} {encoded[i:i+16]}" for i in range(0, len(encoded), 16)]
    return raw, lines + ["TFE_END"]


def test_transport_reconstructs_exact_bytes():
    raw, lines = transport()
    assert decode_receipt("\r\n".join(lines)) == raw


def test_truncated_transport_refused():
    _, lines = transport()
    with pytest.raises(ValueError, match="incomplete"):
        decode_receipt("\n".join(lines[:-1]))


def test_missing_middle_chunk_refused():
    _, lines = transport()
    with pytest.raises(ValueError, match="gap/duplicate"):
        decode_receipt("\n".join(lines[:2] + lines[3:]))


def test_duplicate_chunk_refused():
    _, lines = transport()
    with pytest.raises(ValueError, match="gap/duplicate"):
        decode_receipt("\n".join(lines[:2] + lines[1:]))
