#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests
from bs4 import BeautifulSoup, Tag

BASE_URL = ""
SCREENERS_PATH = "/screener.ashx"
DEFAULT_USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
RETRYABLE_HTTP = {403, 429, 500, 502, 503, 504}


@dataclass(frozen=True)
class FetchTarget:
    url: str
    view_v: str


def parse_v_from_href(href: str | None) -> str | None:
    if not href:
        return None
    m = re.search(r"[?&]v=(\d+)", href)
    if not m:
        return None
    return m.group(1)


def normalize_href(href: str | None) -> str:
    raw = str(href or "").strip()
    if not raw:
        return ""
    if raw.startswith("http://") or raw.startswith("https://"):
        return raw
    if raw.startswith("/"):
        return f"{BASE_URL}{raw}"
    return f"{BASE_URL}/{raw}"


def fetch_html(session: requests.Session, url: str, max_attempts: int = 6) -> str:
    last_status: int | None = None
    last_error: str = ""

    for attempt in range(1, max_attempts + 1):
        try:
            resp = session.get(url, timeout=30)
            last_status = resp.status_code
            if resp.status_code == 200:
                return resp.text

            if resp.status_code in RETRYABLE_HTTP:
                wait_s = min(12.0, 0.8 * attempt)
                time.sleep(wait_s)
                continue

            resp.raise_for_status()
        except requests.RequestException as exc:
            last_error = str(exc)
            wait_s = min(12.0, 0.8 * attempt)
            time.sleep(wait_s)

    if last_status is not None:
        raise RuntimeError(f"Failed to fetch {url}; status={last_status}")
    raise RuntimeError(f"Failed to fetch {url}; error={last_error or 'unknown'}")


def to_option_list(select_tag: Tag) -> list[dict[str, Any]]:
    options: list[dict[str, Any]] = []
    for opt in select_tag.find_all("option"):
        if not isinstance(opt, Tag):
            continue
        options.append(
            {
                "value": str(opt.get("value", "")),
                "label": opt.get_text(" ", strip=True),
                "elite_only": opt.has_attr("data-elite-only"),
                "selected": opt.has_attr("selected"),
            }
        )
    return options


def extract_top_controls(soup: BeautifulSoup) -> list[dict[str, Any]]:
    table = soup.find("table", id="filter-table-top")
    if not isinstance(table, Tag):
        return []

    controls: list[dict[str, Any]] = []
    for select in table.find_all("select"):
        if not isinstance(select, Tag):
            continue

        controls.append(
            {
                "id": str(select.get("id", "")),
                "name": str(select.get("name", "")),
                "class": " ".join(select.get("class", [])),
                "options": to_option_list(select),
            }
        )

    return controls


def extract_filter_selects(soup: BeautifulSoup) -> list[dict[str, Any]]:
    table = soup.find("table", id="filter-table-filters")
    if not isinstance(table, Tag):
        return []

    selects: list[dict[str, Any]] = []
    for select in table.find_all("select"):
        if not isinstance(select, Tag):
            continue

        select_id = str(select.get("id", "")).strip()
        if not select_id.startswith("fs_"):
            continue

        label = ""
        td = select.find_parent("td")
        if isinstance(td, Tag):
            prev_td = td.find_previous_sibling("td")
            if isinstance(prev_td, Tag):
                label = prev_td.get_text(" ", strip=True)

        selects.append(
            {
                "id": select_id,
                "label": label,
                "data_filter": str(select.get("data-filter", "")),
                "data_url": str(select.get("data-url", "")),
                "data_url_selected": str(select.get("data-url-selected", "")),
                "selected_raw": str(select.get("data-selected", "")),
                "options": to_option_list(select),
            }
        )

    return selects


def extract_tab_links(soup: BeautifulSoup) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for a in soup.select(".screener-view-button a"):
        if not isinstance(a, Tag):
            continue

        href = str(a.get("href", "")).strip()
        label = a.get_text(" ", strip=True)
        v = parse_v_from_href(href)
        out.append(
            {
                "label": label,
                "href": href,
                "href_absolute": normalize_href(href),
                "view_v": v,
                "is_javascript": href.startswith("javascript:"),
            }
        )

    return out


def extract_table_headers(soup: BeautifulSoup) -> list[dict[str, Any]]:
    headers: list[dict[str, Any]] = []
    for th in soup.select("#screener-table th.table-header"):
        if not isinstance(th, Tag):
            continue

        onclick = str(th.get("onclick", "")).strip()
        sort_href = ""
        sort_key = ""
        if onclick:
            m = re.search(r"window\.location='([^']+)'", onclick)
            if m:
                sort_href = m.group(1)
                m2 = re.search(r"[?&]o=([^&]+)", sort_href)
                if m2:
                    sort_key = m2.group(1)

        headers.append(
            {
                "label": th.get_text(" ", strip=True),
                "sort_href": sort_href,
                "sort_key": sort_key,
            }
        )

    return headers


def extract_view_payload(session: requests.Session, target: FetchTarget) -> dict[str, Any]:
    html = fetch_html(session, target.url)
    soup = BeautifulSoup(html, "html.parser")

    payload: dict[str, Any] = {
        "view_v": target.view_v,
        "url": target.url,
        "table_headers": extract_table_headers(soup),
    }

    if target.view_v == "111":
        payload["tabs"] = extract_tab_links(soup)
        payload["top_controls"] = extract_top_controls(soup)
        payload["filter_selects"] = extract_filter_selects(soup)

    return payload


def unique_targets_from_tabs(base_url: str, tabs: list[dict[str, Any]]) -> list[FetchTarget]:
    seen: set[str] = set()
    out: list[FetchTarget] = [FetchTarget(url=base_url, view_v="111")]
    seen.add("111")

    for tab in tabs:
        if tab.get("is_javascript"):
            continue
        view_v = str(tab.get("view_v") or "").strip()
        href = str(tab.get("href_absolute") or "").strip()
        if not view_v or not href:
            continue
        if view_v in seen:
            continue
        seen.add(view_v)
        out.append(FetchTarget(url=href, view_v=view_v))

    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True, help="Output JSON path")
    parser.add_argument("--base-url", required=True, help="External screener base URL (for example: https://example.com)")
    parser.add_argument("--user-agent", default=DEFAULT_USER_AGENT)
    args = parser.parse_args()

    normalized_base_url = str(args.base_url).strip().rstrip("/")
    if not normalized_base_url.startswith(("http://", "https://")):
        raise ValueError("base-url must start with http:// or https://")

    global BASE_URL
    BASE_URL = normalized_base_url

    out_path = Path(args.out).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)

    session = requests.Session()
    session.headers.update({"user-agent": args.user_agent})

    base_url = f"{BASE_URL}{SCREENERS_PATH}?v=111"
    base_html = fetch_html(session, base_url)
    base_soup = BeautifulSoup(base_html, "html.parser")
    tabs = extract_tab_links(base_soup)
    targets = unique_targets_from_tabs(base_url, tabs)

    views: list[dict[str, Any]] = []
    for target in targets:
        try:
            views.append(extract_view_payload(session, target))
        except Exception as exc:
            views.append(
                {
                    "view_v": target.view_v,
                    "url": target.url,
                    "table_headers": [],
                    "error": str(exc),
                }
            )
        time.sleep(0.8)

    payload = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "source": {
            "site": BASE_URL,
            "entry": base_url,
        },
        "views": views,
    }

    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(str(out_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
