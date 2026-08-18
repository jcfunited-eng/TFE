"""Shared, read-only renderer for the legacy CH3 and CH6 static pages."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from html import escape
from pathlib import Path
from typing import Callable

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class OpenRow:
    symbol: str
    side: int
    shares: int
    entry_price: float
    notional: float
    entered_at: str
    armed: bool = False


@dataclass(frozen=True)
class ClosedRow:
    symbol: str
    side: int
    shares: int
    entry_price: float
    exit_price: float | None
    pnl: float
    return_pct: float
    entered_at: str
    exited_at: str
    reason: str


@dataclass(frozen=True)
class ChannelPage:
    code: str
    title: str
    engine: str
    starting_capital: float
    cash: float
    opens: tuple[OpenRow, ...]
    closed: tuple[ClosedRow, ...]
    rules: tuple[str, ...]


def latest_completed_closes() -> dict[str, tuple[float, str]]:
    frames: list[pd.DataFrame] = []
    for filename in ("ch4_live_store.parquet", "ch3_supply_tail.parquet"):
        path = ROOT / filename
        if path.exists():
            frame = pd.read_parquet(path, columns=["Date", "Symbol", "Close"])
            frame["Date"] = pd.to_datetime(frame["Date"])
            frames.append(frame)
    if not frames:
        return {}
    market = pd.concat(frames, ignore_index=True).drop_duplicates(["Date", "Symbol"], keep="last")
    latest = market.sort_values("Date").groupby("Symbol", as_index=False).tail(1)
    return {
        str(symbol): (float(close), pd.Timestamp(day).date().isoformat())
        for symbol, close, day in zip(latest["Symbol"], latest["Close"], latest["Date"])
        if float(close) > 0
    }


def live_marks(symbols: tuple[str, ...]) -> dict[str, tuple[float, str]]:
    try:
        from tools.ch3_shadow_hunter import last_price
    except Exception:
        return {}
    observed_at = datetime.now(timezone.utc).isoformat()
    marks: dict[str, tuple[float, str]] = {}
    for symbol in symbols:
        try:
            price = last_price(symbol)
        except Exception:
            continue
        if price is not None and float(price) > 0:
            marks[symbol] = (float(price), observed_at)
    return marks


def money(value: float, *, signed: bool = False) -> str:
    prefix = ""
    if signed:
        prefix = "+" if value >= 0 else "−"
    return f"{prefix}${abs(value):,.2f}"


def price(value: float | None) -> str:
    return "—" if value is None else f"${value:,.4f}".rstrip("0").rstrip(".")


def position_status(code: str, return_pct: float, armed: bool) -> str:
    if return_pct <= -20:
        return "ANOMALY TRIGGER EXCEEDED"
    if return_pct >= 5:
        return "HARVEST LEVEL"
    if code == "CH6" and armed:
        return "ARMED"
    return "OPEN"


def render_page(page: ChannelPage, destination: Path) -> None:
    symbols = tuple(row.symbol for row in page.opens)
    completed = latest_completed_closes()
    marks = live_marks(symbols)
    marked: dict[str, tuple[float, str, str]] = {}
    for symbol in symbols:
        if symbol in marks:
            observed_price, observed_at = marks[symbol]
            marked[symbol] = (observed_price, observed_at, "live mark")
        elif symbol in completed:
            observed_price, observed_at = completed[symbol]
            marked[symbol] = (observed_price, observed_at, "completed close")

    def tone(v):
        if v is None or v == 0:
            return "number"
        return "number pos" if v > 0 else "number neg"

    open_rows: list[str] = []
    unrealized_values: list[float] = []
    for row in sorted(page.opens, key=lambda item: item.symbol):
        mark = marked.get(row.symbol)
        current_price = mark[0] if mark else None
        pnl = None if current_price is None else (current_price - row.entry_price) * row.shares * row.side
        return_pct = None if current_price is None or row.entry_price <= 0 else 100 * (current_price / row.entry_price - 1) * row.side
        if pnl is not None:
            unrealized_values.append(pnl)
        status = "NO MARK — EXCLUDED" if return_pct is None else position_status(page.code, return_pct, row.armed)
        mark_label = "no valid mark" if mark is None else f"{mark[2]} {mark[1][:10]}"
        open_rows.append(
            "<tr>"
            f"<td class='symbol'>{escape(row.symbol)}</td><td>{'SHORT' if row.side == -1 else 'LONG'}</td>"
            f"<td class='number'>{row.shares:,}</td><td class='number'>{price(row.entry_price)}</td>"
            f"<td class='number'>{price(current_price)}</td><td class='{tone(pnl)}'>{'—' if pnl is None else money(pnl, signed=True)}</td>"
            f"<td class='{tone(return_pct)}'>{'—' if return_pct is None else f'{return_pct:+.2f}%'}</td>"
            f"<td>{escape(status)}</td><td>{escape(row.entered_at)}</td><td>{escape(mark_label)}</td></tr>"
        )
    if not open_rows:
        open_rows.append("<tr><td colspan='10' class='empty'>No open positions.</td></tr>")

    closed_rows: list[str] = []
    for row in sorted(page.closed, key=lambda item: item.exited_at, reverse=True):
        closed_rows.append(
            "<tr>"
            f"<td class='symbol'>{escape(row.symbol)}</td><td>{'SHORT' if row.side == -1 else 'LONG'}</td>"
            f"<td class='number'>{row.shares:,}</td><td class='number'>{price(row.entry_price)}</td>"
            f"<td class='number'>{price(row.exit_price)}</td><td class='{tone(row.pnl)}'>{money(row.pnl, signed=True)}</td>"
            f"<td class='{tone(row.return_pct)}'>{row.return_pct:+.2f}%</td><td>{escape(row.reason)}</td>"
            f"<td>{escape(row.entered_at)}</td><td>{escape(row.exited_at)}</td></tr>"
        )
    if not closed_rows:
        closed_rows.append("<tr><td colspan='10' class='empty'>No closed records.</td></tr>")

    held_notional = sum(row.notional for row in page.opens)
    complete_marks = len(unrealized_values) == len(page.opens)
    unrealized = sum(unrealized_values) if complete_marks else None
    equity = None if unrealized is None else page.cash + held_notional + unrealized
    realized = sum(row.pnl for row in page.closed)
    resolved = [row for row in page.closed if not row.reason.startswith("VOID-")]
    wins = sum(1 for row in resolved if row.pnl > 0)
    win_rate = None if not resolved else 100 * wins / len(resolved)
    rules = "".join(f"<li>{escape(rule)}</li>" for rule in page.rules)
    generated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    equity_text = "UNAVAILABLE — INCOMPLETE MARKS" if equity is None else money(equity)
    unrealized_text = "UNAVAILABLE" if unrealized is None else money(unrealized, signed=True)
    win_rate_text = "—" if win_rate is None else f"{win_rate:.1f}%"

    document = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{escape(page.title)}</title>
<style>
:root{{--bg:#f2f4f1;--card:#fff;--head:#e8efe7;--ink:#232a24;--muted:#68736a;--line:#dce4dc;--pos:#157a3f;--neg:#c03530}}
@media(prefers-color-scheme:dark){{:root{{--bg:#171b18;--card:#1f2521;--head:#28302a;--ink:#e6eae5;--muted:#9aa79c;--line:#344038;--pos:#4fc07e;--neg:#f07f76}}}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--ink);font:14px/1.45 system-ui,sans-serif;padding:24px}}
main{{max-width:1200px;margin:auto}}h1{{font-size:1.35rem;margin-bottom:4px}}.sub,.note{{color:var(--muted)}}
.tiles{{display:grid;grid-template-columns:repeat(auto-fit,minmax(145px,1fr));gap:10px;margin:18px 0}}
.tile,.card{{background:var(--card);border:1px solid var(--line);border-radius:10px}}.tile{{padding:12px}}.label{{font-size:.7rem;color:var(--muted);text-transform:uppercase}}.value{{font-size:1.08rem;font-weight:700;margin-top:3px}}
.card{{overflow:hidden;margin:14px 0}}.card h2{{font-size:.95rem;margin:0;padding:14px}}.scroll{{overflow:auto}}table{{width:100%;border-collapse:collapse}}th{{background:var(--head);color:var(--muted);font-size:.67rem;text-transform:uppercase;text-align:left}}th,td{{padding:9px 12px;border-top:1px solid var(--line);white-space:nowrap}}.number{{text-align:right;font-variant-numeric:tabular-nums}}.pos{{color:var(--pos)}}.neg{{color:var(--neg)}}.symbol{{font-weight:700}}.empty{{text-align:center;color:var(--muted)}}li{{margin:.35rem 0}}
</style></head><body><main>
<h1>{escape(page.title)}</h1><div class="sub">Read-only paper record · no real orders · engine {escape(page.engine)} · generated {generated}</div>
<section class="tiles">
<div class="tile"><div class="label">Equity</div><div class="value">{equity_text}</div></div>
<div class="tile"><div class="label">Cash{' (margin borrowed)' if page.cash < 0 else ''}</div><div class="value">{money(page.cash, signed=True)}</div></div>
<div class="tile"><div class="label">Realized</div><div class="value {'pos' if realized > 0 else ('neg' if realized < 0 else '')}">{money(realized, signed=True)}</div></div>
<div class="tile"><div class="label">Unrealized</div><div class="value {'' if unrealized is None else ('pos' if unrealized > 0 else ('neg' if unrealized < 0 else ''))}">{unrealized_text}</div></div>
<div class="tile"><div class="label">Win rate</div><div class="value">{win_rate_text}</div></div>
<div class="tile"><div class="label">Open / resolved</div><div class="value">{len(page.opens)} / {len(resolved)}</div></div>
</section>
<section class="card"><h2>Custody law</h2><ul>{rules}</ul></section>
<section class="card"><h2>Open positions</h2><div class="scroll"><table><thead><tr><th>Symbol</th><th>Side</th><th>Shares</th><th>Entry</th><th>Mark</th><th>Unrealized</th><th>Return</th><th>Status</th><th>Entered</th><th>Mark source</th></tr></thead><tbody>{''.join(open_rows)}</tbody></table></div></section>
<section class="card"><h2>Closed and voided records</h2><div class="scroll"><table><thead><tr><th>Symbol</th><th>Side</th><th>Shares</th><th>Entry</th><th>Exit</th><th>P&amp;L</th><th>Return</th><th>Reason</th><th>Entered</th><th>Exited</th></tr></thead><tbody>{''.join(closed_rows)}</tbody></table></div></section>
<p class="note">A missing quote is never replaced with the entry price. Equity and total unrealized P&amp;L are unavailable unless every open position has a valid live mark or dated completed-close mark. A 20% anomaly level is a trigger and cannot guarantee a 20% realized-loss ceiling across gaps.</p>
</main></body></html>"""
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(document, encoding="utf-8")


def run_cli(builder: Callable[[], ChannelPage]) -> None:
    import sys

    if len(sys.argv) != 2:
        raise SystemExit(f"usage: {Path(sys.argv[0]).name} OUTPUT.html")
    destination = Path(sys.argv[1]).resolve()
    render_page(builder(), destination)
    print(f"page written: {destination}")
