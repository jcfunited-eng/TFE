"""Bounded lifetime proof for the substrate runner thread registry."""

import dsf_ai_service.substrate_runner as substrate_runner


def test_runner_thread_registry_releases_completed_threads():
    thread = substrate_runner._start_background_thread(
        lambda: None,
        "bounded-registry-proof",
    )
    thread.join(timeout=2.0)
    assert not thread.is_alive()
    with substrate_runner._background_threads_lock:
        assert thread not in substrate_runner._background_threads
