"""decision_report_page.py — what every channel DECIDED today, on one page.

Built 2026-08-11 after Joe: "I thought I was supposed to see some kind of
decision report." The information existed but only ever arrived inside a
chat message, which scrolls away. A day where a channel bought nothing has
to be readable at a glance, WITH the reason, or silence and breakage look
identical.

Read-only. Runs no engine and places no order. It reads the books each
channel already writes and, for CH2, the refusal reasons production
already logs.

Usage: python tools/decision_report_page.py /path/out.html
"""
from __future__ import annotations

import collections
import datetime
import json
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ART = os.path.join(ROOT, "artifacts", "vtvr_observer")


def _read(name, default=None):
    path = os.path.join(ART, name)
    if not os.path.exists(path):
        return default
    try:
        return json.load(open(path))
    except (ValueError, OSError):
        return default


def _day(ms):
    return datetime.datetime.fromtimestamp(
        ms / 1000, datetime.timezone.utc).date().isoformat()


def _ch2_from_logs(days=2):
    """CH2's scan/buy/refuse counts, straight from production's own log."""
    start = int(
        (datetime.datetime.now(datetime.timezone.utc)
         - datetime.timedelta(days=days)).timestamp() * 1000
    )

    def q(pattern):
        out = subprocess.run(
            ["aws", "logs", "filter-log-events", "--log-group-name", "/ecs/tfe-web",
             "--start-time", str(start), "--filter-pattern", pattern,
             "--max-items", "300", "--query", "events[*].[timestamp,message]",
             "--output", "json"],
            capture_output=True, text=True, timeout=270)
        try:
            return json.loads(out.stdout or "[]")
        except ValueError:
            return []

    scanned = passed = reached = bought = None
    for _ts, m in q('"passed V3 basin"'):
        f = re.search(r"(\d+) candidates → (\d+) passed .*? → (\d+) after", m)
        if f:
            scanned, passed, reached = (int(f.group(1)), int(f.group(2)),
                                        int(f.group(3)))
    for _ts, m in q('"[DAILY-ENTRY] Pass complete"'):
        f = re.search(r"(\d+) entries placed", m)
        if f:
            bought = int(f.group(1))
    reject_rows = []
    for ts, m in q('"[BRIDGE] REJECT"'):
        f = re.search(r"REJECT (\S+) \| (.+)$", m.strip())
        if f:
            reject_rows.append((_day(ts), f.group(1), f.group(2)))
    latest_day = max((d for d, _t, _r in reject_rows), default=None)
    refused = collections.Counter()
    names = set()
    for d, t, r in reject_rows:
        if d != latest_day:
            continue
        names.add(t)
        refused["already past its own sell line — too strong to buy"
                 if r.startswith("s_uf_out_of_ch2_band")
                 else r.split(":")[0]] += 1
    return {"scanned": scanned, "passed": passed, "reached": reached,
            "bought": bought, "refused": refused, "names": sorted(names)}


def main() -> int:
    out_path = sys.argv[1]
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime(
        "%Y-%m-%d %H:%M UTC")

    ch4 = _read("ch4_spring_book.json", {}) or {}
    ch3 = _read("ch3_shadow_log.json", {}) or {}
    ch6 = _read("ch6_book.json", {}) or {}
    try:
        ch2 = _ch2_from_logs()
    except Exception as err:  # noqa: BLE001 — the page must still render
        ch2 = {"error": f"{type(err).__name__}: {err}"}

    ch3_days = sorted(ch3.get("days", {}) or {})
    ch3_today = ch3_days[-1] if ch3_days else "—"
    ch3_found = sum(1 for f in ch3.get("finds", [])
                    if f.get("date") == ch3_today)
    ch3_open = [f for f in ch3.get("finds", []) if f.get("status") == "OPEN"]

    rows = []

    def card(name, what, decided, detail, tone="n"):
        rows.append((name, what, decided, detail, tone))

    # ── CH2 ──────────────────────────────────────────────────────────
    if "error" in ch2:
        card("CH2", "live money channel", "could not be read",
             ch2["error"], "bad")
    else:
        bought = ch2.get("bought")
        refused_total = sum(ch2["refused"].values())
        why = "; ".join(f"{n} — {r}" for r, n in ch2["refused"].most_common())
        card("CH2", "live money channel",
             f"bought {bought if bought is not None else '?'}",
             (f"looked at {ch2['scanned']:,} names · {ch2['passed']} met the "
              f"entry test · {ch2['reached']} reached the order stage<br>"
              f"<b>turned down {refused_total}</b>: {why or 'none'}"
              + (f"<br><span class=nm>{', '.join(ch2['names'])}</span>"
                 if ch2["names"] else ""))
             if ch2.get("scanned") else "no scan found in the log window",
             "warn" if bought == 0 else "ok")

    # ── CH4 ──────────────────────────────────────────────────────────
    card("CH4", "paper, holds to pattern boundary",
         f"{len(ch4.get('positions', {}))} open",
         f"last decided on the {ch4.get('last_processed', '—')} close · "
         f"cash ${ch4.get('cash', 0):,.0f} · "
         f"{len(ch4.get('closed', []))} closed to date", "ok")

    # ── CH3 ──────────────────────────────────────────────────────────
    card("CH3", "paper, fades crowd-less spikes",
         f"found {ch3_found}",
         f"last decided on the {ch3_today} close · {len(ch3_open)} open · "
         f"cash {'-' if ch3.get('book', {}).get('cash', 0) < 0 else ''}${abs(ch3.get('book', {}).get('cash', 0)):,.0f}"
         + (' (on margin)' if ch3.get('book', {}).get('cash', 0) < 0 else '')
         + ("<br>a zero day means every qualifying spike was crowd-backed, "
            "which this channel refuses by design" if ch3_found == 0 else ""),
         "warn" if ch3_found == 0 else "ok")

    # ── CH6 ──────────────────────────────────────────────────────────
    card("CH6", "its own channel · sells anything at +5% before the close",
         f"{len(ch6.get('positions', {}))} open",
         f"last scanned the {ch6.get('last_hunted', '—')} close · "
         f"cash ${ch6.get('cash', 0):,.0f} · "
         f"{len(ch6.get('closed', []))} closed to date", "ok")

    body = ""
    for name, what, decided, detail, tone in rows:
        body += (
            f'<section class="card {tone}"><div class="hd">'
            f'<span class="ch">{name}</span><span class="what">{what}</span>'
            f'<span class="dec">{decided}</span></div>'
            f'<div class="dt">{detail}</div></section>')

    html = f"""<title>TFE Decision Report</title>
<style>
:root {{ --bg:#f2f4f1; --card:#fff; --ink:#232a24; --muted:#6d7a6f;
  --line:#e0e6df; --ok:#12833f; --warn:#b7791f; --bad:#c93a2e; }}
:root[data-theme="dark"] {{ --bg:#171b18; --card:#1f2521; --ink:#e6eae5;
  --muted:#9aa79c; --line:#2e362f; --ok:#4cc47e; --warn:#e0b352; --bad:#e57368; }}
@media (prefers-color-scheme: dark) {{ :root:not([data-theme="light"])
  {{ --bg:#171b18; --card:#1f2521; --ink:#e6eae5; --muted:#9aa79c;
     --line:#2e362f; --ok:#4cc47e; --warn:#e0b352; --bad:#e57368; }} }}
body {{ background:var(--bg); color:var(--ink); margin:0;
  font:14px/1.55 system-ui,-apple-system,"Segoe UI",sans-serif;
  padding:24px 16px 60px; }}
main {{ max-width:900px; margin:0 auto; display:flex;
  flex-direction:column; gap:14px; }}
h1 {{ font-size:1.2rem; margin:0; }}
.sub {{ color:var(--muted); font-size:.8rem; }}
.card {{ background:var(--card); border:1px solid var(--line);
  border-left:4px solid var(--line); border-radius:10px; padding:13px 16px; }}
.card.ok {{ border-left-color:var(--ok); }}
.card.warn {{ border-left-color:var(--warn); }}
.card.bad {{ border-left-color:var(--bad); }}
.hd {{ display:flex; gap:12px; align-items:baseline; flex-wrap:wrap; }}
.ch {{ font-weight:700; font-size:1rem; }}
.what {{ color:var(--muted); font-size:.78rem; flex:1 1 auto; }}
.dec {{ font-weight:650; font-variant-numeric:tabular-nums; }}
.dt {{ color:var(--muted); font-size:.8rem; margin-top:7px; }}
.nm {{ font-family:ui-monospace,monospace; font-size:.72rem; }}
.foot {{ color:var(--muted); font-size:.72rem; max-width:80ch; }}
</style>
<main>
<header>
  <h1>TFE — Decision Report</h1>
  <div class="sub">What each channel decided, and why it decided nothing
   when it decided nothing · updated {stamp}</div>
</header>
{body}
<p class="foot">A channel that buys nothing and a channel that is broken
look identical on a quiet page. Every zero here carries its reason, so the
difference is visible without digging. Read-only: this page runs no engine
and places no order. CH2 is the live money channel; CH3, CH4 and CH6 are
paper.</p>
</main>
"""
    open(out_path, "w").write(html)
    print(f"page written: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
