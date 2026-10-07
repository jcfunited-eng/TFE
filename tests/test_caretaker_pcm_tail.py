"""Exact finite audio transport; no learning or organism speech claim."""
import pytest
from guala_caretaker import media

@pytest.mark.parametrize('samples', [0, 1, 137, 3999, 4000, 4137, 8000])
def test_pcm_stream_preserves_all_samples_and_only_pads_eof(tmp_path, samples):
    raw = b'\x12\x34' * samples
    path = tmp_path / 'voice.pcm'
    path.write_bytes(raw)
    count = (samples + 3999) // 4000
    assert media.block_count(str(path)) == count
    sequential = media.blocks(str(path))
    assert len(sequential) == count
    assert sequential == [media.read_block(str(path), i) for i in range(count)]
    delivered = b''.join(sequential)
    assert delivered == raw + b'\0' * ((-len(raw)) % 8000)
    assert media.read_block(str(path), count) is None
    assert path.read_bytes() == raw

@pytest.mark.parametrize('reader', [media.blocks, media.block_count, lambda p: media.read_block(p, 0)])
def test_partial_signed_sample_is_visible_failure(tmp_path, reader):
    path = tmp_path / 'broken.pcm'
    path.write_bytes(b'\x12\x34\x56')
    with pytest.raises(ValueError, match='inside a signed16 sample'):
        reader(str(path))

def test_missing_stream_is_not_reported_as_silence(tmp_path):
    with pytest.raises(FileNotFoundError):
        media.read_block(str(tmp_path / 'missing.pcm'), 0)
