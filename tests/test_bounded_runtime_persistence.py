from pathlib import Path

import numpy as np
import pytest

from dsf_ai_service.substrate.deployment_generation import (
    BoundedStageAdmission,
    StageValidationError,
    _discover_staged_files,
)
from dsf_ai_service.v4.gualaloom_v5_engine import (
    Guala,
    PictureItem,
    VideoItem,
)
from dsf_ai_service.v4.wave_atlas import WaveAtlas


def test_real_guala_cold_save_uses_only_bounded_writers_and_roundtrips(
    tmp_path: Path,
) -> None:
    stage = tmp_path / "stage"
    stage.mkdir()
    sources = tmp_path / "sources"
    frames = sources / "frames"
    frames.mkdir(parents=True)
    for index in range(64):
        (frames / f"empty-{index:02d}" / "nested").mkdir(parents=True)
    original = sources / "picture.jpg"
    original.write_bytes(b"original-picture")
    (frames / "0001.frame").write_bytes(b"video-frame")
    audio = sources / "video.audio"
    audio.write_bytes(b"video-audio")
    guala = Guala()
    guala.wave_atlas = WaveAtlas()
    picture = PictureItem(
        item_id="picture-1",
        title="bounded picture",
        intensity_grid=np.array(
            [[0.0, 0.5], [0.75, 1.0]],
            dtype=np.float32,
        ),
    )
    picture.original_path = str(original)
    guala._pictures[picture.item_id] = picture
    video = VideoItem(
        item_id="video-1",
        title="bounded video",
        frame_dir=str(frames),
        audio_path=str(audio),
        n_frames=1,
    )
    guala._videos[video.item_id] = video
    admission = BoundedStageAdmission(
        stage,
        max_total_bytes=64 * 1024 * 1024,
        max_required_files=2048,
        max_path_bytes=256 * 1024,
    )

    with guala.bounded_persistence_admission(admission):
        guala.save_full_state(
            str(stage),
            publish_generation=False,
        )
        guala._save_wave_atlas(str(stage))

    files = _discover_staged_files(
        stage,
        max_total_bytes=64 * 1024 * 1024,
        max_required_files=2048,
        max_path_bytes=256 * 1024,
    )
    admission.verify_complete(files)
    restored = Guala()
    restored.load_full_state(
        str(stage),
        require_exact_binary=True,
    )

    assert restored._load_successful is True
    assert restored._guala_identity == guala._guala_identity
    assert restored.tick == guala.tick
    assert {
        "guala_organism.pkl.gz",
        "guala_organism.pkl.gz.binding.json",
        "guala_tapestry.pkl.gz",
        "guala_tapestry.pkl.gz.binding.json",
        "wave_atlas.npz",
        "wave_atlas.npz.binding.json",
    }.issubset(files)
    assert any(
        relative.startswith("assets/pictures/")
        for relative in files
    )
    assert any(
        relative.startswith("assets/videos/")
        for relative in files
    )
    assert not any(
        "empty-" in relative
        for relative in files
    )


def test_real_guala_cold_save_cannot_cross_stage_byte_capacity(
    tmp_path: Path,
) -> None:
    guala = Guala()
    admission = BoundedStageAdmission(
        tmp_path,
        max_total_bytes=1024,
        max_required_files=2048,
        max_path_bytes=256 * 1024,
    )

    with pytest.raises(
        StageValidationError,
        match="aggregate byte capacity",
    ):
        with guala.bounded_persistence_admission(admission):
            guala.save_full_state(
                str(tmp_path),
                publish_generation=False,
            )

    assert sum(
        path.stat().st_size
        for path in tmp_path.rglob("*")
        if path.is_file()
    ) <= 1024
