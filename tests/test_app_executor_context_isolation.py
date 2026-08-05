"""Regression proof for caller-local BindingWindow identity in executor work."""

import asyncio
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import dsf_ai_service.app as appmod
from dsf_ai_service.substrate.window_manager import WindowManager


def test_lifecycle_executor_does_not_inherit_prior_workers_binding_window(
        monkeypatch):
    lifecycle = appmod._DeploymentLifecycle()
    monkeypatch.setattr(appmod, "_deployment_lifecycle", lifecycle)
    depth_token = appmod._lifecycle_mutation_depth.set(0)
    manager = WindowManager(
        log_event_fn=lambda *_args, **_kwargs: None,
        get_tick_fn=lambda: 1,
    )

    async def scenario():
        loop = asyncio.get_running_loop()
        loop.set_default_executor(ThreadPoolExecutor(max_workers=1))

        def sensory_frame():
            manager.begin_context("physical:sight:test", "sight")
            return manager.active_context_id

        sensory_context = await appmod._run_lifecycle_executor(sensory_frame)
        conversation_context = await appmod._run_lifecycle_executor(
            lambda: manager.active_context_id)

        assert sensory_context is not None
        assert sensory_context == "physical:sight:test"
        assert conversation_context is None
        manager.discard_unsettled_context(
            sensory_context, "test_complete")

    try:
        asyncio.run(scenario())
    finally:
        appmod._lifecycle_mutation_depth.reset(depth_token)
