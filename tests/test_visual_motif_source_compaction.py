"""Visual motifs retain structural source associations, not encounter logs."""

from dsf_ai_service.visual_krimelack import (
    SightSection,
    VisualMotif,
    VisualPerceptFragment,
)


def _fragments():
    return [
        VisualPerceptFragment(
            fixation_coord=(0, 0),
            event_ticks=[0, 2, 4, 6],
            event_records=[
                {"t": 0, "dw": 1, "s": 0.5},
                {"t": 2, "dw": 1, "s": 0.5},
                {"t": 4, "dw": 1, "s": 0.5},
                {"t": 6, "dw": 1, "s": 0.5},
            ],
            winding_count=4,
            source_id="camera_stream",
            born_tick=0,
        )
    ]


def test_repeated_camera_frames_reinforce_without_growing_source_history():
    sight = SightSection()
    motif, is_new, _ = sight.process_viewing(
        _fragments(), "camera_stream", tick=1)
    assert is_new

    for tick in range(2, 10_002):
        repeated, is_new, _ = sight.process_viewing(
            _fragments(), "camera_stream", tick=tick)
        assert repeated is motif
        assert not is_new

    assert motif.n_firings == 10_001
    assert motif.source_history == ["camera_stream"]


def test_legacy_duplicates_compact_without_losing_sources_or_recency():
    motif = VisualMotif(
        motif_id=7,
        n_firings=9,
        source_history=["picture-a", "camera_stream", "picture-a", "picture-b"],
    )

    assert motif.n_firings == 9
    assert motif.source_history == ["camera_stream", "picture-a", "picture-b"]

    motif.observe_source("camera_stream")
    assert motif.source_history == ["picture-a", "picture-b", "camera_stream"]
