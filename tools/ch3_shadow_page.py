"""
ch3_shadow_page.py — CH3 shadow book rendered in the TFE platform style.
Columns and conventions mirror taofinancialengine.com/portfolio-advisor.
Usage: python tools/ch3_shadow_page.py /path/out.html
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

LOG = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                   "artifacts", "vtvr_observer", "ch3_shadow_log.json")
CASH0 = 100_000.0


def main():
    out_path = sys.argv[1]
    log = {"finds": [], "days": {}, "book": {"cash": CASH0, "start": CASH0}}
    if os.path.exists(LOG):
        log = json.load(open(LOG))
    book = log.get("book", {"cash": CASH0, "start": CASH0})
    finds = sorted(log.get("finds", []), key=lambda f: f.get("found_at", ""),
                   reverse=True)
    opens = [f for f in finds if f["status"] == "OPEN"]
    closed = [f for f in finds if f["status"] != "OPEN"]
    # live marks for open positions (best effort)
    marks = {}
    try:
        from tools.ch3_shadow_hunter import last_price
        for f in opens:
            try:
                marks[f["symbol"]] = last_price(f["symbol"])
            except Exception:
                pass
    except Exception:
        pass
    held = sum(f.get("notional", 0.0) for f in opens)
    # Display math contract: every row must multiply out by hand.
    # Shares are fractional (stake / entry), marks are rounded to cents
    # BEFORE computing P&L, and the tiles are sums of the row values.
    def row_upl(f):
        entry = f["entry_px"]
        cur = round(marks.get(f["symbol"], entry), 2)
        shares = f.get("shares") or (int(f.get("notional", 0) // entry)
                                     if entry else 0)
        return shares, cur, round(shares * (cur - entry) * f["side"], 2)
    unreal = sum(row_upl(f)[2] for f in opens)
    equity = book["cash"] + held + unreal
    realized = book["cash"] + held - book.get("start", CASH0)
    wins = sum(1 for f in closed if (f.get("pnl") or 0) > 0)
    losses = sum(1 for f in closed if (f.get("pnl") or 0) <= 0)
    wr = f"{100 * wins / len(closed):.1f}%" if closed else "0.0%"
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    def money(x, signed=False):
        s = f"${abs(x):,.2f}"
        if signed:
            s = ("+" if x >= 0 else "-") + s
        return s

    open_rows = ""
    for f in opens:
        shares, cur, upl = row_upl(f)
        pct = 100 * upl / f["notional"] if f.get("notional") else 0.0
        cls = "pos" if upl >= 0 else "neg"
        open_rows += (f'<tr><td class="tk">{f["symbol"]}</td>'
                      f'<td><span class="chip">CH3</span>'
                      f'{"<span class=chip2>SHORT</span>" if f["side"] == -1 else ""}</td>'
                      f'<td class="num">{shares:,}</td>'
                      f'<td class="num">${f["entry_px"]:,.2f}</td>'
                      f'<td class="num">${cur:,.2f}</td>'
                      f'<td class="num {cls}">{money(upl, True)}</td>'
                      f'<td class="num {cls}">{pct:+.2f}%</td>'
                      f'<td><span class="status">SIMULATED</span></td>'
                      f'<td>{f["date"][5:]} {f.get("found_at", "")[11:16]}</td></tr>')
    if not open_rows:
        open_rows = '<tr><td colspan="9" class="empty">No open positions.</td></tr>'

    closed_rows = ""
    for f in closed[:60]:
        pnl = f.get("pnl") or 0.0
        pct = f.get("ret_pct") or 0.0
        shares = f.get("shares") or (int(round(f.get("notional", 0)
                                     / f["entry_px"])) if f["entry_px"] else 0)
        cls = "pos" if pnl >= 0 else "neg"
        closed_rows += (f'<tr><td class="tk">{f["symbol"]}</td>'
                        f'<td><span class="chip">CH3</span>'
                        f'{"<span class=chip2>SHORT</span>" if f["side"] == -1 else ""}</td>'
                        f'<td class="num">{shares:,}</td>'
                        f'<td class="num">${f["entry_px"]:,.2f}</td>'
                        f'<td class="num {cls}">{money(pnl, True)}</td>'
                        f'<td class="num {cls}">{pct:+.2f}%</td>'
                        f'<td><span class="status">{f["status"]}</span></td>'
                        f'<td>{f.get("catalyst", "")}</td>'
                        f'<td>{f["date"][5:]} {f.get("found_at", "")[11:16]}</td></tr>')
    if not closed_rows:
        closed_rows = '<tr><td colspan="9" class="empty">No closed trades yet.</td></tr>'

    html = f"""<title>CH3 Shadow Hunter</title>
<style>
:root {{ --bg:#f2f4f1; --card:#ffffff; --head:#e8efe7; --ink:#232a24;
  --muted:#6d7a6f; --line:#e0e6df; --pos:#12833f; --neg:#c93a2e;
  --chip:#2b3330; --chiptx:#ffffff; --accent:#2e7d4f; }}
:root[data-theme="dark"], html[data-theme="dark"] {{ --bg:#171b18;
  --card:#1f2521; --head:#28302a; --ink:#e6eae5; --muted:#9aa79c;
  --line:#2e362f; --pos:#4cc47e; --neg:#e57368; --chip:#3a423d;
  --chiptx:#fff; --accent:#63b98c; }}
@media (prefers-color-scheme: dark) {{ :root:not([data-theme="light"])
  {{ --bg:#171b18; --card:#1f2521; --head:#28302a; --ink:#e6eae5;
     --muted:#9aa79c; --line:#2e362f; --pos:#4cc47e; --neg:#e57368;
     --chip:#3a423d; --chiptx:#fff; --accent:#63b98c; }} }}
body {{ background:var(--bg); color:var(--ink); margin:0;
  font:14px/1.5 system-ui,-apple-system,"Segoe UI",sans-serif;
  padding:24px 16px 60px; }}
main {{ max-width:1160px; margin:0 auto; display:flex;
  flex-direction:column; gap:16px; }}
h1 {{ font-size:1.2rem; margin:0; }}
.sub {{ color:var(--muted); font-size:.8rem; }}
.acct {{ color:var(--muted); font-size:.78rem; text-align:right; }}
.tiles {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(140px,1fr)); gap:10px; }}
.tile {{ background:var(--card); border:1px solid var(--line);
  border-radius:10px; padding:12px 14px; }}
.tile .k {{ font-size:.62rem; text-transform:uppercase;
  letter-spacing:.08em; color:var(--muted); }}
.tile .v {{ font-size:1.15rem; font-weight:650;
  font-variant-numeric:tabular-nums; margin-top:2px; }}
.v.pos {{ color:var(--pos); }} .v.neg {{ color:var(--neg); }}
.card {{ background:var(--card); border:1px solid var(--line);
  border-radius:12px; overflow:hidden; }}
.card h2 {{ font-size:.9rem; margin:0; padding:14px 16px; }}
.card h2 .count {{ background:var(--head); border-radius:9px;
  font-size:.7rem; padding:2px 8px; color:var(--muted); margin-left:6px; }}
.twrap {{ overflow-x:auto; }}
table {{ border-collapse:collapse; width:100%; font-size:.82rem; }}
thead tr {{ background:var(--head); }}
th {{ text-align:left; padding:9px 14px; font-size:.64rem;
  text-transform:uppercase; letter-spacing:.07em; color:var(--muted);
  white-space:nowrap; }}
td {{ padding:9px 14px; border-top:1px solid var(--line); white-space:nowrap; }}
td.num {{ text-align:right; font-variant-numeric:tabular-nums; }}
td.tk {{ font-weight:700; }}
td.pos {{ color:var(--pos); font-weight:600; }}
td.neg {{ color:var(--neg); font-weight:600; }}
td.empty {{ color:var(--muted); text-align:center; padding:24px; }}
.chip {{ background:var(--chip); color:var(--chiptx); font-size:.62rem;
  font-weight:700; padding:2px 8px; border-radius:5px; }}
.chip2 {{ background:var(--neg); color:#fff; font-size:.6rem;
  font-weight:700; padding:2px 6px; border-radius:5px; margin-left:4px; }}
.status {{ background:var(--head); color:var(--muted); font-size:.62rem;
  font-weight:700; padding:2px 8px; border-radius:5px; }}
.foot {{ color:var(--muted); font-size:.72rem; max-width:80ch; }}
.warn {{ background:var(--head); border:1px solid var(--line);
  border-radius:10px; padding:10px 14px; font-size:.78rem;
  color:var(--muted); }}
</style>
<main>
<header>
  <h1>CH3 — Shadow Hunter</h1>
  <div class="sub">The reveal-fade channel: shorts the day's violent
   up-spikes at the close, holds five sessions, time exit · measured
   +1.33%/event 2016-2026, positive every year since 2021 · SIMULATED —
   no real orders, borrow costs not modeled ·
   engine {log.get("engine", "ch3_reveal_fade_v1")} · updated {stamp}</div>
</header>
<div class="acct">Shadow account: equity {money(equity)} · cash {money(book["cash"])}</div>
<section class="tiles">
  <div class="tile"><div class="k">Equity</div><div class="v">{money(equity)}</div></div>
  <div class="tile"><div class="k">Realized</div>
    <div class="v {"pos" if realized >= 0 else "neg"}">{money(realized, True)}</div></div>
  <div class="tile"><div class="k">Unrealized</div>
    <div class="v {"pos" if unreal >= 0 else "neg"}">{money(unreal, True)}</div></div>
  <div class="tile"><div class="k">Win rate</div><div class="v">{wr}</div></div>
  <div class="tile"><div class="k">Open</div><div class="v">{len(opens)}</div></div>
  <div class="tile"><div class="k">Closed</div><div class="v">{len(closed)}</div></div>
</section>
<section class="card">
  <h2>Open Positions<span class="count">{len(opens)}</span></h2>
  <div class="twrap"><table>
    <thead><tr><th>Ticker</th><th>Signal</th><th>Shares</th><th>Entry</th>
      <th>Current</th><th>Unreal. P&amp;L</th><th>P&amp;L %</th>
      <th>Status</th><th>Detected</th></tr></thead>
    <tbody>{open_rows}</tbody></table></div>
</section>
<section class="card">
  <h2>Closed Trades<span class="count">{len(closed)}</span></h2>
  <div class="twrap"><table>
    <thead><tr><th>Ticker</th><th>Signal</th><th>Shares</th><th>Entry</th>
      <th>P&amp;L $</th><th>P&amp;L %</th><th>Exit</th><th>Catalyst</th>
      <th>Detected</th></tr></thead>
    <tbody>{closed_rows}</tbody></table></div>
</section>
<p class="foot">Shadow record — every row is a simulated fill at real
market prices. HIT = target touched, MISS = stop hit, CUT = closed by
review, EOD = flattened at the close. This record decides when the
live channel re-arms.</p>
</main>
"""
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)
    print("page written:", out_path)


if __name__ == "__main__":
    main()
