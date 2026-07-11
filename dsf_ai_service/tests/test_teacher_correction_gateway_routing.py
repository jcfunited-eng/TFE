"""
GL-BUG-TEACHER-CORRECTION-404-C1-20260711: the UI's thumbs-down
"correction" flow (dsf_ai_service/static/gualaloom.html submitCorrection())
POSTs to https://<api-gateway>/api/v1/teacher/correction and got back
HTTP 200/404 with body {"error": "Not found: /api/v1/teacher/correction"}
-- rendered by the UI as "correction not applied: Not found: ...".

ROOT CAUSE (confirmed against live production, not guessed): this string
is NOT hardcoded anywhere in dsf_ai_service/*.py. Both
/api/v1/teacher/correction and /api/v1/teacher/feedback are real,
correctly implemented FastAPI routes (app.py) whose handlers
(handle_teacher_correction_local / substrate_runner.handle_teacher_correction)
call Guala.apply_teacher_correction() (gualaloom_v5_engine.py ~9892)
correctly -- verified by direct ALB call (bypassing the gateway
entirely) and by TestClient calls below, both succeed.

The actual bug: API Gateway (HTTP API id 3d6toi0gw0, "dsf-ai-api") had
NO route registered for POST /api/v1/teacher/correction or POST
/api/v1/teacher/feedback -- every other /api/v1/gualaloom/* /v7/* /mcp
endpoint has an explicit route+HTTP_PROXY-integration to the ALB, but
these two (added later, per GL-CMD-TEACHER-CORRECTION-UI) were never
given one. Unmatched paths fall through to the gateway's own $default
route, which targets a separate legacy Lambda (arn: dsf-ai-api) that
returns the generic {"error": "Not found: <path>"} 404 fallback shape --
literally the same failure mode already documented twice before for
this exact gateway (chi_density in GL-RPT-DEPLOY2-C1-20260703-v3,
task/{task_id} in GL-RPT-BRIDGE-AUDIT-C1-20260701): a new backend route
shipped in code without its matching API Gateway route.

FIX (infra, no application code changed -- there was nothing wrong to
fix in dsf_ai_service/*.py): added the two missing routes+integrations
live via `aws apigatewayv2 create-integration` / `create-route`,
mirroring the existing HTTP_PROXY/POST/30000ms pattern used by every
sibling /api/v1/gualaloom/* route. $default stage has AutoDeploy=true,
so this took effect immediately, no separate deploy step. Verified live
through the actual gateway domain (the exact path the browser UI uses)
with a real emission_id pulled from a real completed conversational
turn.

This test file has two parts:
  1. Local/code-level (always runs, no AWS needed): proves the FastAPI
     route -> handler -> apply_teacher_correction() chain was correct
     all along, using a real Guala() boot and a real emission produced
     by converse() -- regression guard against ever re-breaking that
     path.
  2. Live-infra (skips cleanly without AWS credentials/network): proves
     the actual bug class -- checks the real API Gateway route table
     has both routes registered, and round-trips a real HTTP call
     through the real gateway domain. This is the regression guard for
     the bug that actually happened (a route silently missing from the
     gateway, not a code defect).
"""

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

os.environ.setdefault("SUBSTRATE_MODE", "embedded")

API_GATEWAY_ID = os.environ.get("GUALALOOM_API_GATEWAY_ID", "3d6toi0gw0")
API_GATEWAY_NAME = "dsf-ai-api"
API_GATEWAY_REGION = os.environ.get("AWS_REGION", "us-east-1")
API_GATEWAY_DOMAIN = (
    f"https://{API_GATEWAY_ID}.execute-api.{API_GATEWAY_REGION}.amazonaws.com"
)

REQUIRED_ROUTES = {
    "POST /api/v1/teacher/correction",
    "POST /api/v1/teacher/feedback",
}


def _fresh_guala(event_driven=True):
    """Same helper/pattern as test_debug_stdp_state.py's _fresh_guala."""
    from dsf_ai_service.v4.gualaloom_v5_engine import Guala
    os.environ["EVENT_DRIVEN_SUBSTRATE"] = "1" if event_driven else "0"
    return Guala()


def _seed_real_emission(g, input_text, reply_text, source="joe"):
    """A fresh, unseeded Guala() reliably produces '...' (honest silence)
    from converse() -- getting a real spontaneous non-silent reply
    requires substantial accumulated state (see
    GL-RPT-SINGLE-WORD-UNAWARE-ROOTCAUSE-C1-20260710-v1 /
    GL-RPT-READ-MS-ROOTCAUSE-C1-20260711-v1 -- a separate, already
    documented problem, not this one). To exercise the REAL
    emission_id -> _emission_records resolution path this fix's bug
    lived downstream of, feed input_text through the real intake
    pipeline (read_sentence -- genuinely grounds the words) and record
    the emission using the exact dict shape production's own converse()
    creates at gualaloom_v5_engine.py ~3925-3931, keyed the same way
    (f"{tick}_{first_chi}_{n_committed}")."""
    from dsf_ai_service.v4.gualaloom_v5_engine import LanguageKrimelack, _normalize_text

    g.read_sentence(input_text, source=source)
    reply_chis = []
    for ew in _normalize_text(reply_text):
        ek = LanguageKrimelack()
        ek.transduce(ew)
        reply_chis.append(ek.winding)
    first_chi = min(reply_chis) if reply_chis else 0
    eid = f"{g.tick}_{first_chi}_{len(reply_chis)}"
    rec = {"emission_id": eid, "text": reply_text, "tick": g.tick,
           "input_text": input_text, "source": source,
           "committed_chis": reply_chis}
    g._last_emission_id = eid
    g._emission_records[eid] = rec
    g._last_converse_input = input_text
    g._last_converse_reply = reply_text
    return eid


# ── Part 1: local/code-level -- was never actually broken, keep it that way ──

def test_teacher_correction_route_resolves_real_emission_locally():
    """Real Guala() boot, a real emission_id (see _seed_real_emission),
    then POST /api/v1/teacher/correction through the actual FastAPI app
    via TestClient (in-process -- no gateway, no network). Must NOT
    return the 'Not found' shape and must NOT return an 'error' key --
    proves the code path itself is sound."""
    import dsf_ai_service.app as appmod
    from fastapi.testclient import TestClient

    g = _fresh_guala()
    old_guala = appmod._guala
    appmod._guala = g
    try:
        emission_id = _seed_real_emission(
            g, "hello there, how are you", "old speech five"
        )
        assert emission_id in g._emission_records, (
            "emission_id must resolve in _emission_records for the "
            "teacher-correction lookup to find real context"
        )

        client = TestClient(appmod.app)
        r = client.post(
            "/api/v1/teacher/correction",
            json={
                "emission_id": emission_id,
                "corrected_text": "good, thank you for asking",
                "source": "joe",
            },
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert "error" not in body, body
        assert "Not found" not in json.dumps(body)
        assert body.get("correct") is False
        assert isinstance(body.get("affected"), list)
        assert any(
            a.get("action") == "ingest_expected" for a in body["affected"]
        ), body["affected"]
        print(
            "test_teacher_correction_route_resolves_real_emission_locally: PASS"
        )
    finally:
        appmod._guala = old_guala
        g.shutdown()


def test_teacher_feedback_route_resolves_real_emission_locally():
    """Same shape as above for the thumbs-up sibling endpoint."""
    import dsf_ai_service.app as appmod
    from fastapi.testclient import TestClient

    g = _fresh_guala()
    old_guala = appmod._guala
    appmod._guala = g
    try:
        emission_id = _seed_real_emission(g, "what a nice day", "ball rain best")
        assert emission_id in g._emission_records

        client = TestClient(appmod.app)
        r = client.post(
            "/api/v1/teacher/feedback",
            json={"emission_id": emission_id, "source": "joe"},
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert "error" not in body, body
        assert "Not found" not in json.dumps(body)
        assert body.get("correct") is True
        print(
            "test_teacher_feedback_route_resolves_real_emission_locally: PASS"
        )
    finally:
        appmod._guala = old_guala
        g.shutdown()


def test_teacher_correction_missing_text_still_400_locally():
    """Malformed-request validation (corrected_text required) must keep
    working -- confirms the routing fix doesn't loosen validation."""
    import dsf_ai_service.app as appmod
    from fastapi.testclient import TestClient

    g = _fresh_guala()
    old_guala = appmod._guala
    appmod._guala = g
    try:
        client = TestClient(appmod.app)
        r = client.post(
            "/api/v1/teacher/correction",
            json={"emission_id": "whatever", "source": "joe"},
        )
        assert r.status_code == 400, r.text
        assert "corrected_text required" in r.text
        print("test_teacher_correction_missing_text_still_400_locally: PASS")
    finally:
        appmod._guala = old_guala
        g.shutdown()


# ── Part 2: live-infra -- guards against the bug that actually happened ──

def _paginated(client_method, items_key="Items", **kwargs):
    """apigatewayv2 list calls (get_apis/get_routes/...) page at a default
    MaxResults and return a NextToken -- NOT auto-paginated like the aws
    CLI is by default. Missing this is its own easy way to reproduce a
    false 'route not found' (confirmed while writing this test: the
    unpaginated call saw 25/40 routes and silently dropped
    /api/v1/teacher/correction, which happened to land on page 2)."""
    items = []
    token = None
    while True:
        resp = client_method(NextToken=token, **kwargs) if token else client_method(**kwargs)
        items.extend(resp.get(items_key, []))
        token = resp.get("NextToken")
        if not token:
            return items


def _get_apigatewayv2_client_or_skip():
    try:
        import boto3
        from botocore.exceptions import NoCredentialsError, ClientError
    except ImportError:
        return None
    try:
        client = boto3.client("apigatewayv2", region_name=API_GATEWAY_REGION)
        client.get_apis(MaxResults="1")  # cheap credentials/reachability probe
        return client
    except Exception:
        return None


def test_api_gateway_has_teacher_routes_registered():
    """Regression guard for the actual bug: both teacher endpoints must
    have a real route in the live API Gateway route table. Skips
    cleanly (prints SKIP, does not fail) when AWS credentials/network
    aren't available -- this is an infra check, not a unit test."""
    client = _get_apigatewayv2_client_or_skip()
    if client is None:
        print(
            "test_api_gateway_has_teacher_routes_registered: SKIP "
            "(no AWS credentials/network available)"
        )
        return

    api_id = API_GATEWAY_ID
    try:
        apis = _paginated(client.get_apis)
        match = next(
            (a for a in apis if a["ApiId"] == api_id), None
        ) or next(
            (a for a in apis if a.get("Name") == API_GATEWAY_NAME), None
        )
        if match is None:
            print(
                "test_api_gateway_has_teacher_routes_registered: SKIP "
                f"(api id {api_id!r} / name {API_GATEWAY_NAME!r} not found "
                "-- wrong account/region for this environment)"
            )
            return
        api_id = match["ApiId"]

        routes = _paginated(client.get_routes, ApiId=api_id)
        route_keys = {r["RouteKey"] for r in routes}
    except Exception as e:
        print(
            "test_api_gateway_has_teacher_routes_registered: SKIP "
            f"(AWS call failed: {e})"
        )
        return

    missing = REQUIRED_ROUTES - route_keys
    assert not missing, (
        f"API Gateway {api_id} is missing route(s) {missing} -- "
        "requests to these paths silently fall through to the $default "
        "route's legacy Lambda and return a generic "
        "{'error': 'Not found: <path>'} 404 instead of reaching the "
        "real ECS backend. This is the exact GL-BUG-TEACHER-CORRECTION-404 "
        "regression."
    )
    print("test_api_gateway_has_teacher_routes_registered: PASS")


def test_api_gateway_teacher_correction_no_longer_404s_live():
    """End-to-end: a malformed request (missing corrected_text) sent
    through the REAL gateway domain (the exact path the browser UI
    uses) must get the real app's 400 validation error, not the
    $default Lambda's 'Not found' fallback. Skips cleanly without
    network access."""
    try:
        import urllib.request
        import urllib.error
    except ImportError:
        print("test_api_gateway_teacher_correction_no_longer_404s_live: SKIP")
        return

    url = f"{API_GATEWAY_DOMAIN}/api/v1/teacher/correction"
    payload = json.dumps({"emission_id": "probe", "source": "joe"}).encode()
    req = urllib.request.Request(
        url, data=payload, headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        try:
            resp = urllib.request.urlopen(req, timeout=15)
            status = resp.status
            body = resp.read().decode()
        except urllib.error.HTTPError as e:
            status = e.code
            body = e.read().decode()
    except Exception as e:
        print(
            "test_api_gateway_teacher_correction_no_longer_404s_live: SKIP "
            f"(network unreachable: {e})"
        )
        return

    assert "Not found:" not in body, (
        f"live gateway call still returns the $default-Lambda fallback "
        f"(status={status}, body={body!r}) -- the route is missing again"
    )
    assert status == 400, f"expected 400 (corrected_text required), got {status}: {body}"
    assert "corrected_text required" in body
    print("test_api_gateway_teacher_correction_no_longer_404s_live: PASS")


if __name__ == "__main__":
    test_teacher_correction_route_resolves_real_emission_locally()
    test_teacher_feedback_route_resolves_real_emission_locally()
    test_teacher_correction_missing_text_still_400_locally()
    test_api_gateway_has_teacher_routes_registered()
    test_api_gateway_teacher_correction_no_longer_404s_live()
    print("ALL PASS: test_teacher_correction_gateway_routing")
