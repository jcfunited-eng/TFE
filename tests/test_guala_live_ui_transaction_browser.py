from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import urlparse

from playwright.sync_api import Browser, Page, Route, sync_playwright


ROOT = Path(__file__).resolve().parents[1]
STATIC = ROOT / "dsf_ai_service" / "static"
ORIGIN = "https://guala-ui.test"
PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
    b"\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89"
    b"\x00\x00\x00\rIDAT\x08\xd7c\xf8\xcf\xc0\xf0\x1f\x00"
    b"\x05\x00\x01\xff\x89\x99=\x1d\x00\x00\x00\x00IEND\xaeB`\x82"
)


def _section(
    available: bool = False,
    status: str = "not_mounted",
    reason: str = "record not supplied",
    **values: object,
) -> dict[str, object]:
    return {"available": available, "status": status, "reason": reason, **values}


def _snapshot(*available_capabilities: str) -> dict[str, object]:
    endpoints = {
        "camera": "/ingress/camera",
        "microphone": "/ingress/microphone",
        "curriculum": "/ingress/curriculum",
        "text_visual": "/ingress/text",
        "picture": "/ingress/picture",
    }
    names = (
        "camera",
        "microphone",
        "curriculum",
        "text_visual",
        "picture",
        "pdf",
        "book",
        "audio",
        "song",
        "gutenberg",
        "youtube",
        "khan_academy",
        "pbs_kids",
        "spotify",
    )
    capabilities = {
        name: _section(
            name in available_capabilities,
            "mounted" if name in available_capabilities else "not_mounted",
            "test ingress mounted" if name in available_capabilities else "not mounted",
            endpoint=endpoints.get(name) if name in available_capabilities else None,
        )
        for name in names
    }
    unavailable = _section()
    return {
        "schema": "guala.native.public_observation.v1",
        "generation": 7,
        "snapshot_receipt_sha256": "a" * 64,
        "identity": _section(True, "observed", "native identity restored", value="guala"),
        "organism": _section(
            True,
            "transport_available",
            "state transport exists; activity is not observed",
            tick=7,
            activity_observed=False,
        ),
        "body": _section(
            True,
            "simulated_record",
            "W1 is a simulated world record",
            simulated=True,
            world_id="W1-region-A",
            native_embodiment_active=False,
        ),
        "capabilities": capabilities,
        "sensory": {
            **unavailable,
            "visual": _section(),
            "auditory": _section(),
        },
        "neuron_activity": _section(),
        "fractals": _section(count=0),
        "formations": _section(
            mosaic_count=0,
            mosaic_of_mosaics_count=0,
            tapestry_count=0,
            tapestry_of_tapestries_count=0,
            weave_count=0,
        ),
        "recall": _section(),
        "cognitive_capital": _section(credits=[]),
        "attention": _section(),
        "autonomy": _section(),
        "articulation": _section(),
        "curriculum": _section(),
        "full_dsf": _section(
            fields=["D_k", "M_k", "R_rev_k", "U_star_k", "C_k", "P_k", "B_k"],
            decision_authority=False,
            projection="none",
            observation_loss="field body not supplied",
        ),
        "persistence": _section(),
        "resources": _section(),
    }


def _mount(
    page: Page,
    name: str,
    snapshot: dict[str, object],
    events: list[tuple[str, str]],
) -> None:
    html = (STATIC / name).read_text(encoding="utf-8")

    def serve(route: Route) -> None:
        request = route.request
        path = urlparse(request.url).path
        events.append((request.method, path))
        if path == f"/{name}":
            route.fulfill(status=200, content_type="text/html", body=html)
        elif path == "/api/v1/guala/native-observation":
            route.fulfill(
                status=200,
                content_type="application/json",
                headers={"ETag": '"generation-7"'},
                body=json.dumps(snapshot),
            )
        elif path.startswith("/ingress/"):
            route.fulfill(
                status=200,
                content_type="application/json",
                body=json.dumps({"accepted": True, "generation": 8}),
            )
        elif path.endswith((".png", ".jpg", ".jpeg")):
            route.fulfill(status=200, content_type="image/png", body=PNG)
        else:
            route.fulfill(status=404, body="not mounted")

    page.route("**/*", serve)
    page.goto(f"{ORIGIN}/{name}", wait_until="domcontentloaded")
    page.wait_for_function("document.querySelector('#connection-mode, #header-state').textContent.includes('connected')")


def _with_browser(test) -> None:
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        try:
            test(browser)
        finally:
            browser.close()


def test_unavailable_state_distinguishes_transport_activity_and_embodiment() -> None:
    def run(browser: Browser) -> None:
        for name in ("gualaloom.html", "loomscan.html"):
            page = browser.new_page()
            errors: list[str] = []
            page.on("pageerror", lambda error: errors.append(str(error)))
            _mount(page, name, _snapshot(), [])
            if name == "gualaloom.html":
                assert "Observation endpoint connected" in page.locator("#connection-mode").inner_text()
                assert "organism activity not observed" in page.locator("#organism-mode").inner_text().lower()
                assert "Simulated W1 record" in page.locator("#embodiment-mode").inner_text()
                assert page.locator("#experience-ledger .ledger-stage.available").count() == 0
            else:
                assert "Observation endpoint connected" in page.locator("#header-state").inner_text()
                assert "organism activity not observed" in page.locator("#organism-state").inner_text().lower()
                assert "Simulated W1 record" in page.locator("#embodiment-state").inner_text()
                assert page.locator("#experience-stage-ledger .available").count() == 0
                assert page.locator("#experience-stage-ledger .unavailable").count() == 12
            assert errors == []
            page.close()

    _with_browser(run)


def test_slow_picture_decode_cannot_repaint_or_send_after_off() -> None:
    def run(browser: Browser) -> None:
        page = browser.new_page()
        page.add_init_script(
            """
            window.__decodePending=false;
            window.__releaseDecode=null;
            window.createImageBitmap=()=>new Promise(resolve=>{
              window.__decodePending=true;
              window.__releaseDecode=()=>resolve({width:2,height:2,close(){}});
            });
            """
        )
        events: list[tuple[str, str]] = []
        _mount(page, "gualaloom.html", _snapshot("picture"), events)
        page.set_input_files(
            "#picture-file",
            {"name": "slow.png", "mimeType": "image/png", "buffer": PNG},
        )
        page.wait_for_function("window.__decodePending===true")
        page.locator("#clear-text").click()
        page.evaluate("window.__releaseDecode()")
        page.wait_for_timeout(50)

        assert page.locator("#offered-surface").get_attribute("data-empty") == "true"
        assert page.locator("#ledger-surface-subject").inner_text().startswith("Off")
        assert page.locator("#experience-ledger .ledger-channel").nth(2).locator(".available").count() == 0
        assert page.evaluate("surfaceKind") == "none"
        assert page.evaluate("surfaceActive") is False
        assert ("POST", "/ingress/picture") not in events

    _with_browser(run)


def test_rapid_camera_and_microphone_toggles_leave_off_as_final_owner() -> None:
    def run(browser: Browser) -> None:
        page = browser.new_page()
        page.add_init_script(
            """
            window.__mediaRequests=[];
            window.__stoppedTracks=0;
            const mediaDevices={getUserMedia:constraints=>new Promise(resolve=>{
              const track={stop(){window.__stoppedTracks+=1},addEventListener(){}};
              window.__mediaRequests.push({constraints,resolve:()=>resolve({getTracks:()=>[track]})});
            })};
            Object.defineProperty(navigator,'mediaDevices',{value:mediaDevices,configurable:true});
            """
        )
        events: list[tuple[str, str]] = []
        _mount(page, "gualaloom.html", _snapshot("camera", "microphone"), events)

        for selector in ("#camera-toggle", "#microphone-toggle"):
            page.locator(selector).click()
            page.wait_for_function("window.__mediaRequests.length>=1")
            page.locator(selector).click()
            page.locator(selector).click()
            page.wait_for_function("window.__mediaRequests.length>=2")
            page.locator(selector).click()
            page.evaluate("window.__mediaRequests.splice(0).reverse().forEach(item=>item.resolve())")
            page.wait_for_timeout(50)
            assert page.locator(selector).get_attribute("aria-pressed") == "false"

        assert page.evaluate("cameraStream===null&&cameraTimer===null&&cameraAbort===null") is True
        assert page.evaluate("microphoneStream===null&&microphoneRecorder===null&&microphoneAbort===null") is True
        assert page.locator("#ledger-camera-subject").inner_text().startswith("Off")
        assert page.locator("#ledger-microphone-subject").inner_text().startswith("Off")
        assert all(method != "POST" for method, _path in events)
        assert page.evaluate("window.__stoppedTracks") == 4

    _with_browser(run)


def test_route_order_and_stage_ledger_never_promote_acceptance_to_learning() -> None:
    def run(browser: Browser) -> None:
        events: list[tuple[str, str]] = []
        page = browser.new_page()
        _mount(page, "gualaloom.html", _snapshot("text_visual"), events)
        page.locator("#glyph-text").fill("A")
        page.locator("#offer-text").click()
        page.wait_for_function("document.querySelector('#ledger-surface-admission strong').textContent==='accepted'")

        mutation_index = events.index(("POST", "/ingress/text"))
        observation_index = events.index(("GET", "/api/v1/guala/native-observation"))
        assert observation_index < mutation_index
        assert page.locator("#ledger-surface-capture").get_attribute("class") == "ledger-stage available"
        assert page.locator("#ledger-surface-presentation").get_attribute("class") == "ledger-stage available"
        assert page.locator("#ledger-surface-admission").get_attribute("class") == "ledger-stage available"
        for stage in (
            "receptor",
            "dsf",
            "attention",
            "recurrence",
            "hierarchy",
            "learning",
            "intent",
            "action",
            "consequence",
        ):
            assert page.locator(f"#ledger-surface-{stage}").get_attribute("class") == "ledger-stage unavailable"

        page.locator("#clear-text").click()
        assert page.locator("#offered-surface").get_attribute("data-empty") == "true"
        assert page.locator("#experience-ledger .ledger-channel").nth(2).locator(".available").count() == 0

    _with_browser(run)


def test_late_server_acceptance_cannot_overwrite_off_state() -> None:
    def run(browser: Browser) -> None:
        page = browser.new_page()
        _mount(page, "gualaloom.html", _snapshot("text_visual"), [])
        page.evaluate(
            """
            window.__realFetch=window.fetch;
            window.__finishLatePost=null;
            window.fetch=(input,options)=>{
              if(options?.method==='POST')return new Promise(resolve=>{
                window.__finishLatePost=()=>resolve(new Response(
                  JSON.stringify({accepted:true,generation:99}),
                  {status:200,headers:{'Content-Type':'application/json'}}
                ));
              });
              return window.__realFetch(input,options);
            };
            """
        )
        page.locator("#glyph-text").fill("late")
        page.locator("#offer-text").click()
        page.wait_for_function("typeof window.__finishLatePost==='function'")
        page.locator("#clear-text").click()
        page.evaluate("window.__finishLatePost()")
        page.wait_for_timeout(50)

        assert page.locator("#offered-surface").get_attribute("data-empty") == "true"
        assert page.locator("#ledger-surface-subject").inner_text().startswith("Off")
        assert page.locator("#ledger-surface-admission strong").inner_text() == "unavailable"
        assert page.locator("#experience-ledger .ledger-channel").nth(2).locator(".available").count() == 0
        assert page.evaluate("surfaceKind==='none'&&surfaceActive===false&&surfaceAbort===null") is True

    _with_browser(run)


def test_tablet_layout_keeps_primary_surfaces_and_all_capital_dimensions_visible() -> None:
    def run(browser: Browser) -> None:
        guala = browser.new_page(viewport={"width": 820, "height": 1180})
        _mount(guala, "gualaloom.html", _snapshot(), [])
        assert guala.evaluate(
            "getComputedStyle(document.querySelector('.experience')).gridTemplateColumns.split(' ').length"
        ) == 1
        assert guala.evaluate(
            "getComputedStyle(document.querySelector('.ledger-grid')).gridTemplateColumns.split(' ').length"
        ) == 1
        assert guala.evaluate(
            "document.documentElement.scrollWidth===window.innerWidth"
        ) is True

        scan = browser.new_page(viewport={"width": 820, "height": 1180})
        _mount(scan, "loomscan.html", _snapshot(), [])
        assert scan.evaluate(
            "getComputedStyle(document.querySelector('.growth')).gridTemplateColumns.split(' ').length"
        ) == 3
        assert scan.locator("#capital-table .capital-row").first.locator(
            ".capital-cell:visible"
        ).count() == 10
        assert scan.evaluate(
            "document.documentElement.scrollWidth===window.innerWidth"
        ) is True

    _with_browser(run)
