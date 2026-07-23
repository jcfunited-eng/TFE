"""Bit-exact continuity gates for full Guala engine persistence."""

import gzip
import json
import hashlib
import pickle
import shutil
import struct
from pathlib import Path

import numpy as np
import pytest

import dsf_ai_service.v4.gualaloom_v5_engine as engine_module
from dsf_ai_service.v4.gualaloom_v5_engine import (
    Activity,
    Guala,
    PictureItem,
    SensoryItem,
    VideoItem,
)
from dsf_ai_service.v4.gualaloom_v4_uf_kernel import DSF


def test_hot_save_reuses_already_current_media_tree(tmp_path, monkeypatch):
    guala = Guala()
    try:
        guala.save_hot_state(str(tmp_path))

        def forbidden_rebuild(*_args, **_kwargs):
            raise AssertionError("unchanged media tree was rebuilt on hot save")

        monkeypatch.setattr(guala, "_materialize_media_assets", forbidden_rebuild)
        guala.save_hot_state(str(tmp_path))
    finally:
        guala.strict_shutdown(timeout=30.0)


def _disable_background_substrate(monkeypatch):
    monkeypatch.setenv("EVENT_DRIVEN_SUBSTRATE", "0")
    monkeypatch.setenv("WAVE_ATLAS_ENABLED", "0")
    monkeypatch.setenv("SELF_HEARING_ENABLED", "0")


def test_full_state_round_trip_is_exact_and_media_is_relocatable(
        tmp_path, monkeypatch):
    _disable_background_substrate(monkeypatch)
    monkeypatch.setenv(
        "GUALA_CAUSAL_ACTION_KEY",
        "anonymous-continuity-round-trip-key",
    )
    identity_source = tmp_path / "identity-source"
    state_dir = tmp_path / "sealed-staging"
    source_media = tmp_path / "source-media"
    source_media.mkdir()

    picture_original = source_media / "fox.webp"
    picture_original.write_bytes(b"exact-picture-original")
    frame_source = source_media / "video-frames"
    frame_source.mkdir()
    frame_zero = np.array([[0.1, 0.2], [0.3, 0.4]], dtype=np.float64)
    frame_one = np.array([[0.9, 0.8], [0.7, 0.6]], dtype=np.float64)
    np.save(frame_source / "frame_00000.npy", frame_zero)
    np.save(frame_source / "frame_00001.npy", frame_one)
    (frame_source / "decoder-metadata.txt").write_bytes(b"15fps-gray")
    audio_source = source_media / "audio.wav"
    audio_source.write_bytes(b"exact-video-audio")

    # Existing stale files prove that a save replaces, rather than grows,
    # each media generation.
    (state_dir / "pictures").mkdir(parents=True)
    (state_dir / "pictures" / "orphan.npy").write_bytes(b"orphan-grid")
    (state_dir / "assets" / "orphan").mkdir(parents=True)
    (state_dir / "assets" / "orphan" / "old.bin").write_bytes(b"orphan")

    writer = Guala()
    restored = None
    corrupted_reader = None
    try:
        writer._generate_genesis_identity(str(identity_source))
        identity = writer._guala_identity

        writer.add_corpus(
            "uploaded-story", "The Uploaded Story",
            ["red fox runs warm", "blue fox sleeps cold"])
        corpus = writer._corpora["uploaded-story"]
        corpus.position = 1
        corpus.times_read_through = 7
        corpus.last_read_tick = 321

        writer._sensory_items = {
            "sensory-picture": SensoryItem(
                item_id="sensory-picture", kind="picture", title="Fox",
                times_attended=4, last_attended_tick=303),
            "sensory-sound": SensoryItem(
                item_id="sensory-sound", kind="sound", title="Rain",
                times_attended=2, last_attended_tick=290),
        }
        writer.coordinator._presence = {
            "joe": True, "wc": False, "guest": True}
        writer.coordinator._last_input_tick = {
            "joe": 410, "wc": 88, "guest": 407}
        writer.tick = 412
        writer._current_activity = Activity(
            kind="ATTENDING_VIDEO",
            target="video-fox",
            started_tick=400,
            expected_end_tick=450,
            metadata={
                "_viewed": True,
                "episode": {"id": "episode-7", "modalities": ["sight", "sound"]},
            },
        )
        section = writer.sections["modifier"]
        section.modes = [(DSF(0.1, -0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8),
                          91, "remembered")]
        section._mode_last_active_tick = [333]
        section._mode_alive = [False]
        section._rebuild_word_index(current_tick=writer.tick)

        picture_grid = np.array(
            [[0.0, 0.25], [0.75, 1.0]], dtype=np.float64)
        picture = PictureItem(
            item_id="picture-fox", title="Fox Portrait",
            intensity_grid=picture_grid, source="upload",
            shown_at_tick=100, times_attended=3, last_attended_tick=390)
        picture.original_path = str(picture_original)
        picture.original_width = 640
        picture.original_height = 480
        writer._pictures[picture.item_id] = picture

        video = VideoItem(
            item_id="video-fox", title="Fox Crossing",
            frame_dir=str(frame_source), audio_path=str(audio_source),
            duration_ms=133, n_frames=2, source="upload",
            shown_at_tick=120, times_attended=5, last_attended_tick=405)
        writer._videos[video.item_id] = video

        vocal_result = writer.experience_companion_vocal_pressure(
            struct.pack(
                "<1024h",
                *(
                    12_000 if index % 16 < 8 else -12_000
                    for index in range(1_024)
                ),
            )
        )
        continuity_status = (
            writer._w1_anonymous_av_continuity_owner.status()
        )
        assert continuity_status["settled"] == 1
        assert len(vocal_result[
            "anonymous_av_continuity_authority_receipt_sha256"
        ]) == 64

        writer.save_full_state(str(state_dir))

        core_record = json.loads((state_dir / "guala_core.json").read_text())
        assert core_record["data"]["binary_binding_contract"] == (
            writer.BINARY_BINDING_CONTRACT)
        for artifact in ("guala_organism.sgr", "guala_tapestry.sgr"):
            binding = json.loads(
                (state_dir / f"{artifact}{writer.BINARY_BINDING_SUFFIX}").read_text())
            assert binding["guala_identity"] == identity
            assert binding["saved_at_tick"] == 412
            assert binding["data"]["artifact"] == artifact
            assert binding["data"]["saved_at_tick"] == 412
            assert binding["data"]["bytes"] == (state_dir / artifact).stat().st_size
            assert len(binding["data"]["sha256"]) == 64

        identity_record = json.loads(
            (state_dir / writer.IDENTITY_FILE).read_text())
        assert identity_record["guala_identity"] == identity
        assert not (state_dir / "pictures").exists()
        assert not (state_dir / "assets" / "orphan").exists()

        visual_record = json.loads(
            (state_dir / "guala_visual.json").read_text())["data"]
        picture_record = visual_record["pictures"]["picture-fox"]
        assert not Path(picture_record["grid_path"]).is_absolute()
        assert not Path(picture_record["original_path"]).is_absolute()
        video_record = json.loads(
            (state_dir / "guala_videos.json").read_text())["data"]["videos"]["video-fox"]
        assert not Path(video_record["frame_dir"]).is_absolute()
        assert not Path(video_record["audio_path"]).is_absolute()

        relocated = tmp_path / "relocated-generation"
        shutil.move(str(state_dir), relocated)
        writer.shutdown()
        writer = None

        restored = Guala()
        restored.load_full_state(str(relocated))
        assert restored._load_successful, restored._load_errors
        assert restored._w1_anonymous_av_continuity_owner.status() == (
            continuity_status
        )
        assert restored._guala_identity == identity
        restored_section = restored.sections["modifier"]
        assert restored_section._mode_last_active_tick == [333]
        assert restored_section._mode_alive == [False]

        restored_corpus = restored._corpora["uploaded-story"]
        assert restored_corpus.title == "The Uploaded Story"
        assert restored_corpus.lines == [
            "red fox runs warm", "blue fox sleeps cold"]
        assert restored_corpus.position == 1
        assert restored_corpus.times_read_through == 7
        assert restored_corpus.last_read_tick == 321

        assert {
            sid: (
                item.item_id, item.kind, item.title,
                item.times_attended, item.last_attended_tick)
            for sid, item in restored._sensory_items.items()
        } == {
            "sensory-picture": (
                "sensory-picture", "picture", "Fox", 4, 303),
            "sensory-sound": (
                "sensory-sound", "sound", "Rain", 2, 290),
        }
        assert restored.coordinator._presence == {
            "joe": True, "wc": False, "guest": True}
        assert restored.coordinator._last_input_tick == {
            "joe": 410, "wc": 88, "guest": 407}

        activity = restored._current_activity
        assert isinstance(activity, Activity)
        assert activity.kind == "ATTENDING_VIDEO"
        assert activity.target == "video-fox"
        assert activity.started_tick == 400
        assert activity.expected_end_tick == 450
        assert activity.metadata == {
            "_viewed": True,
            "episode": {"id": "episode-7", "modalities": ["sight", "sound"]},
        }

        restored_picture = restored._pictures["picture-fox"]
        assert isinstance(restored_picture, PictureItem)
        np.testing.assert_array_equal(
            restored_picture.intensity_grid, picture_grid)
        assert Path(restored_picture.original_path).read_bytes() == (
            b"exact-picture-original")
        assert Path(restored_picture.original_path).is_relative_to(relocated)
        assert restored_picture.original_width == 640
        assert restored_picture.original_height == 480

        restored_video = restored._videos["video-fox"]
        assert isinstance(restored_video, VideoItem)
        assert restored_video.duration_ms == 133
        assert restored_video.n_frames == 2
        assert restored_video.source == "upload"
        assert restored_video.shown_at_tick == 120
        assert restored_video.times_attended == 5
        assert restored_video.last_attended_tick == 405
        assert Path(restored_video.frame_dir).is_relative_to(relocated)
        assert Path(restored_video.audio_path).is_relative_to(relocated)
        np.testing.assert_array_equal(
            np.load(Path(restored_video.frame_dir) / "frame_00000.npy"),
            frame_zero)
        np.testing.assert_array_equal(
            np.load(Path(restored_video.frame_dir) / "frame_00001.npy"),
            frame_one)
        assert (Path(restored_video.frame_dir) / "decoder-metadata.txt").read_bytes() == (
            b"15fps-gray")
        assert Path(restored_video.audio_path).read_bytes() == b"exact-video-audio"

        restored.shutdown()
        restored = None

        # A new-contract state that references missing media is corrupt and
        # must never become a successful boot.
        video_path = relocated / "guala_videos.json"
        broken = json.loads(video_path.read_text())
        broken["data"]["videos"]["video-fox"]["frame_dir"] = (
            "assets/videos/missing/frames")
        video_path.write_text(json.dumps(broken))
        corrupted_reader = Guala()
        corrupted_reader.load_full_state(str(relocated))
        assert not corrupted_reader._load_successful
        assert "persisted directory is unavailable" in " ".join(
            corrupted_reader._load_errors)
    finally:
        if writer is not None:
            writer.shutdown()
        if restored is not None:
            restored.shutdown()
        if corrupted_reader is not None:
            corrupted_reader.shutdown()


def _write_exact_state(state_dir, monkeypatch, *, wave=False):
    _disable_background_substrate(monkeypatch)
    if wave:
        monkeypatch.setenv("WAVE_ATLAS_ENABLED", "1")
    writer = Guala()
    try:
        writer._generate_genesis_identity(str(state_dir))
        writer.tick = 17
        if wave:
            writer.wave_atlas.record(
                "object", 0, 17, tick=writer.tick, salience=1.0)
        writer.save_full_state(str(state_dir))
        if wave:
            writer._save_wave_atlas(str(state_dir))
    finally:
        writer.strict_shutdown(timeout=30.0)


def test_authenticated_legacy_binary_migrates_once_to_structural_graph(
        tmp_path, monkeypatch):
    state_dir = tmp_path / "legacy-generation"
    _disable_background_substrate(monkeypatch)
    writer = Guala()
    reader = None
    refused = None
    try:
        writer._generate_genesis_identity(str(state_dir))
        writer.tick = 31
        writer.organism.tick = 29
        writer.tapestry._tick = 27
        writer.save_full_state(str(state_dir))

        legacy_pairs = (
            (
                writer.organism,
                state_dir / "guala_organism.sgr",
                state_dir / "guala_organism.pkl.gz",
            ),
            (
                writer.tapestry,
                state_dir / "guala_tapestry.sgr",
                state_dir / "guala_tapestry.pkl.gz",
            ),
        )
        for value, structural_path, legacy_path in legacy_pairs:
            structural_path.unlink()
            Path(
                f"{structural_path}{Guala.BINARY_BINDING_SUFFIX}"
            ).unlink()
            with gzip.open(legacy_path, "wb") as stream:
                pickle.dump(value, stream, protocol=pickle.HIGHEST_PROTOCOL)
            writer._write_binary_binding(str(legacy_path), writer.tick)

        writer.strict_shutdown(timeout=30.0)
        writer = None

        refused = Guala()
        refused.load_full_state(
            str(state_dir),
            require_exact_binary=True,
        )
        assert refused._load_successful is False
        assert any(
            "forbidden outside an authenticated immutable migration"
            in str(error)
            for error in refused._load_errors
        )
        refused.strict_shutdown(timeout=30.0)
        refused = None

        reader = Guala()
        reader.load_full_state(
            str(state_dir),
            require_exact_binary=True,
            allow_authenticated_legacy_pickle=True,
        )
        assert reader._load_successful, reader._load_errors
        assert reader.organism.tick == 29
        assert reader.tapestry._tick == 27

        reader.save_full_state(str(state_dir))
        for name in ("guala_organism.sgr", "guala_tapestry.sgr"):
            artifact = state_dir / name
            assert artifact.is_file()
            assert Path(
                f"{artifact}{Guala.BINARY_BINDING_SUFFIX}"
            ).is_file()
    finally:
        if writer is not None:
            writer.strict_shutdown(timeout=30.0)
        if reader is not None:
            reader.strict_shutdown(timeout=30.0)
        if refused is not None:
            refused.strict_shutdown(timeout=30.0)


def test_teaching_state_refuses_oversize_before_json_parse(
        tmp_path, monkeypatch):
    teaching_path = tmp_path / "guala_teaching.json"
    with teaching_path.open("wb") as output:
        output.truncate(
            engine_module.TEACHING_WITH_PREDICTION_MAX_BYTES + 1
        )

    def forbidden_parse(*_args, **_kwargs):
        raise AssertionError("oversized teaching state reached json.load")

    monkeypatch.setattr(engine_module.json, "load", forbidden_parse)
    with pytest.raises(ValueError, match="pre-parse byte boundary"):
        Guala._load_teaching_state_file(str(teaching_path))


def test_verified_exact_state_can_enter_finite_legacy_migration_wall(
        tmp_path, monkeypatch):
    teaching_path = tmp_path / "guala_teaching.json"
    with teaching_path.open("wb") as output:
        output.truncate(engine_module.TEACHING_STATE_MAX_BYTES + 1)

    monkeypatch.setattr(engine_module.json, "load", lambda _stream: {})

    assert Guala._load_teaching_state_file(
        str(teaching_path), allow_legacy_migration=True) == {}


def test_current_teaching_state_restores_inside_preparse_boundary(
        tmp_path, monkeypatch):
    state_dir = tmp_path / "state"
    _write_exact_state(state_dir, monkeypatch)
    teaching_path = state_dir / "guala_teaching.json"
    assert teaching_path.stat().st_size <= engine_module.TEACHING_STATE_MAX_BYTES

    reader = Guala()
    try:
        reader.load_full_state(
            str(state_dir), require_exact_binary=True)
        assert reader._load_successful, reader._load_errors
        assert reader.auditory_l5_status()["reciprocity"][
            "encoded_snapshot_capacity_bytes"
        ] == 15 * 1024 * 1024
    finally:
        reader.strict_shutdown(timeout=30.0)


@pytest.mark.parametrize(
    ("filename", "mutate", "expected"),
    [
        (
            "guala_deep_atlas.json",
            lambda data: data.__setitem__("schema", "unknown"),
            "unknown deep-atlas schema",
        ),
        (
            "guala_survival.json",
            lambda data: data.__setitem__("deep_survival_history", []),
            "deep_survival_history must be an object",
        ),
        (
            "guala_teaching.json",
            lambda data: data.__setitem__("feedback_log", {}),
            "teaching.feedback_log must be a bounded object list",
        ),
        (
            "guala_episodic.json",
            lambda data: data.__setitem__("episodic_memory", []),
            "episodic_memory must be an object",
        ),
        (
            "guala_sounds.json",
            lambda data: data.__setitem__(
                "invalid", {"item_id": "different"}),
            "sound[invalid].item_id mismatch",
        ),
    ],
)
def test_exact_restore_rejects_structurally_invalid_component(
        tmp_path, monkeypatch, filename, mutate, expected):
    state_dir = tmp_path / "state"
    _write_exact_state(state_dir, monkeypatch)
    path = state_dir / filename
    record = json.loads(path.read_text())
    mutate(record["data"])
    path.write_text(json.dumps(record))

    reader = Guala()
    try:
        reader.load_full_state(str(state_dir), require_exact_binary=True)
        assert not reader._load_successful
        assert expected in " ".join(reader._load_errors)
    finally:
        reader.strict_shutdown(timeout=30.0)


@pytest.mark.parametrize(
    ("artifact", "damage", "expected"),
    [
        (
            "guala_organism.sgr",
            "remove_binding",
            "required binary binding is missing",
        ),
        (
            "guala_tapestry.sgr",
            "change_artifact",
            "binary size",
        ),
    ],
)
def test_exact_restore_rejects_unbound_or_changed_binary(
        tmp_path, monkeypatch, artifact, damage, expected):
    state_dir = tmp_path / "state"
    _write_exact_state(state_dir, monkeypatch)
    artifact_path = state_dir / artifact
    binding_path = state_dir / f"{artifact}{Guala.BINARY_BINDING_SUFFIX}"
    if damage == "remove_binding":
        binding_path.unlink()
    else:
        with artifact_path.open("ab") as stream:
            stream.write(b"stale-generation")

    reader = Guala()
    try:
        reader.load_full_state(str(state_dir), require_exact_binary=True)
        assert not reader._load_successful
        assert expected in " ".join(reader._load_errors)
    finally:
        reader.strict_shutdown(timeout=30.0)


def test_exact_wave_restore_preserves_duplicate_structure_without_collapse(
        tmp_path, monkeypatch):
    state_dir = tmp_path / "state"
    _disable_background_substrate(monkeypatch)
    monkeypatch.setenv("WAVE_ATLAS_ENABLED", "1")
    writer = Guala()
    reader = None
    try:
        writer._generate_genesis_identity(str(state_dir))
        writer.tick = 23
        writer.wave_atlas.record(
            "object", 0, 23, tick=writer.tick, salience=1.0)
        cell = next(iter(writer.wave_atlas.cells.values()))
        cell.bindings.append(dict(cell.bindings[0]))
        cell.aggregate_strength += float(cell.bindings[0]["strength"])
        assert writer.wave_atlas.binding_count() == 2
        writer.save_full_state(str(state_dir))
        writer._save_wave_atlas(str(state_dir))
        writer.strict_shutdown(timeout=30.0)
        writer = None

        reader = Guala()
        reader.load_full_state(str(state_dir), require_exact_binary=True)
        assert reader._load_successful, reader._load_errors
        assert reader.wave_atlas.binding_count() == 2
        wave_binding = json.loads(
            (state_dir / f"wave_atlas.npz{Guala.BINARY_BINDING_SUFFIX}").read_text())
        assert wave_binding["saved_at_tick"] == 23
        assert wave_binding["data"]["artifact"] == "wave_atlas.npz"
    finally:
        if writer is not None:
            writer.strict_shutdown(timeout=30.0)
        if reader is not None:
            reader.strict_shutdown(timeout=30.0)


def test_exact_wave_restore_rejects_malformed_payload_even_with_matching_receipt(
        tmp_path, monkeypatch):
    state_dir = tmp_path / "state"
    _write_exact_state(state_dir, monkeypatch, wave=True)
    wave_path = state_dir / "wave_atlas.npz"
    with wave_path.open("wb") as stream:
        np.savez_compressed(
            stream,
            chi_indices=np.array([], dtype=np.int32),
        )

    # Rebind the deliberately malformed bytes.  This proves that the engine
    # validates WaveAtlas structure in addition to matching the artifact
    # receipt; the immutable outer generation would independently reject this
    # coordinated file+receipt replacement.
    binding_path = state_dir / f"wave_atlas.npz{Guala.BINARY_BINDING_SUFFIX}"
    binding = json.loads(binding_path.read_text())
    wave_bytes = wave_path.read_bytes()
    binding["data"]["bytes"] = len(wave_bytes)
    binding["data"]["sha256"] = hashlib.sha256(wave_bytes).hexdigest()
    binding_path.write_text(json.dumps(binding))

    reader = Guala()
    try:
        reader.load_full_state(str(state_dir), require_exact_binary=True)
        assert not reader._load_successful
        assert "WaveAtlas NPZ is missing" in " ".join(reader._load_errors)
    finally:
        reader.strict_shutdown(timeout=30.0)
