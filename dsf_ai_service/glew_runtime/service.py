"""Standalone fail-closed ASGI visibility for the ratified GLEW runtime.

The module-level ``app`` serves only read-only GLEW status and conformance.  It
does not import or start the legacy application, so an isolated production
probe cannot become a second legacy state writer.  ``create_wrapped_application``
is an explicit later-cutover tool; it delegates all non-GLEW routes unchanged.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
from contextlib import asynccontextmanager
from typing import Callable, Mapping

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from .certified_backend import CertifiedBackendUnavailable
from .conformance import (
    RuntimeConfiguration,
    RuntimeConformanceError,
    bind_startup_action,
    run_conformance,
    run_startup_conformance,
)
from .field import TRANSPORT_COORDINATE_ORDER, field_conformance
from .model import ReceiptError


ConfigurationProvider = Callable[[], RuntimeConfiguration]
_FIELD_STATUS = "operator_conformant_no_live_mounted_topology"


def _provider_or_default(
    provider: ConfigurationProvider | None,
) -> ConfigurationProvider:
    selected = RuntimeConfiguration.from_environment if provider is None else provider
    if not callable(selected):
        raise TypeError("configuration_provider must be callable")
    return selected


def _failure_response(error: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=503,
        content={
            "conformant": False,
            "error": {"kind": type(error).__name__, "reason": str(error)},
            "full_glew_language_commit_authority": False,
            "legacy_conversation_routed_through_glew": False,
            "scope": "clean_genesis_and_ratified_GLEW_runtime_only",
        },
    )


def _field_report_digest(report: Mapping[str, object]) -> str:
    encoded = json.dumps(
        report,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _bind_field_conformance(
    report: Mapping[str, object], startup_action: str
) -> dict[str, object]:
    """Execute and bind the operator proof without claiming a live topology."""

    try:
        field_report = field_conformance()
    except (ReceiptError, CertifiedBackendUnavailable) as error:
        raise RuntimeConformanceError(
            f"field operator conformance failed: {error}"
        ) from error
    if not isinstance(field_report, dict):
        raise RuntimeConformanceError("field conformance did not return an object")
    expected_digest = field_report.get("report_sha256")
    unsigned = dict(field_report)
    unsigned.pop("report_sha256", None)
    if (
        not isinstance(expected_digest, str)
        or expected_digest != _field_report_digest(unsigned)
    ):
        raise RuntimeConformanceError("field conformance report hash is invalid")
    empty_genesis = field_report.get("empty_genesis")
    one_port = field_report.get("one_port_vector")
    if (
        field_report.get("status") != _FIELD_STATUS
        or field_report.get("live_mounted_topology") is not False
        or field_report.get("coordinate_order")
        != list(TRANSPORT_COORDINATE_ORDER)
        or not isinstance(empty_genesis, Mapping)
        or empty_genesis.get("available") is not False
        or empty_genesis.get("dimension") != 0
        or not isinstance(one_port, Mapping)
        or one_port.get("dimension") != len(TRANSPORT_COORDINATE_ORDER)
    ):
        raise RuntimeConformanceError(
            "field operator report exceeds or differs from its runtime authority"
        )
    combined = dict(report)
    combined.pop("conformance_report_sha256", None)
    combined.pop("startup_action", None)
    combined["field_evolution"] = field_report
    return bind_startup_action(combined, startup_action)


async def _cold_start(application: FastAPI, provider: ConfigurationProvider) -> None:
    configuration = provider()
    if not isinstance(configuration, RuntimeConfiguration):
        raise RuntimeConformanceError(
            "configuration provider did not return RuntimeConfiguration"
        )
    base_report = await asyncio.to_thread(run_startup_conformance, configuration)
    action = base_report.get("startup_action")
    report = await asyncio.to_thread(_bind_field_conformance, base_report, action)
    application.state.glew_configuration = configuration
    application.state.glew_startup_action = action
    application.state.glew_startup_report = report


def _register_observation_routes(application: FastAPI) -> None:
    @application.get("/glew/status", response_model=None)
    async def glew_status():
        report = getattr(application.state, "glew_startup_report", None)
        if not isinstance(report, dict):
            return _failure_response(
                RuntimeConformanceError(
                    "GLEW startup conformance has not completed"
                )
            )
        return report

    @application.get("/glew/conformance", response_model=None)
    async def glew_conformance():
        configuration = getattr(application.state, "glew_configuration", None)
        action = getattr(application.state, "glew_startup_action", None)
        if not isinstance(configuration, RuntimeConfiguration):
            return _failure_response(
                RuntimeConformanceError(
                    "GLEW startup configuration is unavailable"
                )
            )
        try:
            base_report = await asyncio.to_thread(run_conformance, configuration)
            return await asyncio.to_thread(
                _bind_field_conformance, base_report, action
            )
        except (RuntimeConformanceError, OSError, ValueError, TypeError) as error:
            return _failure_response(error)


def create_status_application(
    *, configuration_provider: ConfigurationProvider | None = None
) -> FastAPI:
    """Create the standalone app used by an isolated production probe."""

    provider = _provider_or_default(configuration_provider)

    @asynccontextmanager
    async def lifespan(application: FastAPI):
        await _cold_start(application, provider)
        yield

    application = FastAPI(
        title="GLEW Runtime Visibility",
        version="1.0.0",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
        lifespan=lifespan,
    )
    _register_observation_routes(application)
    return application


def create_wrapped_application(
    *,
    legacy_application: FastAPI,
    configuration_provider: ConfigurationProvider | None = None,
) -> FastAPI:
    """Create an explicit wrapper for a later authorized route cutover."""

    if not isinstance(legacy_application, FastAPI):
        raise TypeError("legacy_application must be a FastAPI application")
    provider = _provider_or_default(configuration_provider)

    @asynccontextmanager
    async def lifespan(application: FastAPI):
        await _cold_start(application, provider)
        async with legacy_application.router.lifespan_context(legacy_application):
            yield

    application = FastAPI(
        title="GLEW Runtime Visibility Wrapper",
        version="1.0.0",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
        lifespan=lifespan,
    )
    _register_observation_routes(application)
    application.mount("/", legacy_application, name="existing-dsf-service")
    return application


app = create_status_application()


__all__ = [
    "app",
    "create_status_application",
    "create_wrapped_application",
]
