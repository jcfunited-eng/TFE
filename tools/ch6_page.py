"""
ch6_page.py — CH6 fast-harvest book in the TFE platform style.
Usage: python tools/ch6_page.py /path/out.html
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

BOOK = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                    "artifacts", "vtvr_observer", "ch6_book.json")
CASH0 = 100_000.0


def main():
    out_path = sys.argv[1]
    book = {"cash": CASH0, "start": CASH0, "positions": {}, "closed": []}
    if os.path.exists(BOOK):
        book = json.load(open(BOOK))
    opens = book.get("positions", {})
    closed = book.get("closed", [])
    cash = book.get("cash", CASH0)

    marks = {}
    try:
        from tools.ch3_shadow_hunter import last_price
        for sym in opens:
            try:
                px = last_price(sym)
                if px and px > 0:
                    marks[sym] = px
            except Exception:
                pass
    except Exception:
        pass

    def row_upl(sym, p):
        entry = p["entry_px"]
        cur = round(marks.get(sym, entry), 2)
        return p["shares"], cur, round(p["shares"] * (cur - entry) * p["side"], 2)

    held = sum(p["notional"] for p in opens.values())
    unreal = sum(row_upl(s, p)[2] for s, p in opens.items())
    realized = sum(t["pnl"] for t in closed)
    equity = cash + held + unreal
    wins = sum(1 for t in closed if t["pnl"] > 0)
    losses = len(closed) - wins
    wr = f"{100 * wins / len(closed):.1f}%" if closed else "0.0%"
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    def money(x, signed=False):
        s = f"${abs(x):,.2f}"
        return (("+" if x >= 0 else "-") + s) if signed else s

    open_rows = ""
    for sym, p in sorted(opens.items()):
        shares, cur, upl = row_upl(sym, p)
        pct = 100 * upl / p["notional"] if p["notional"] else 0.0
        cls = "pos" if upl >= 0 else "neg"
        status = "ARMED" if p.get("armed") else "WATCH"
        open_rows += (f'<tr><td class="tk">{sym}</td>'
                      f'<td><span class="chip">CH6</span>'
                      f'{"<span class=chip2>SHORT</span>" if p["side"] == -1 else ""}</td>'
                      f'<td class="num">{shares:,}</td>'
                      f'<td class="num">${p["entry_px"]:,.2f}</td>'
                      f'<td class="num">${cur:,.2f}</td>'
                      f'<td class="num {cls}">{money(upl, True)}</td>'
                      f'<td class="num {cls}">{pct:+.2f}%</td>'
                      f'<td class="num">{p.get("peak_gain_pct", 0):+.1f}%</td>'
                      f'<td><span class="status">{status}</span></td>'
                      f'<td>{p.get("entry_date", "")}</td></tr>')
    if not open_rows:
        open_rows = '<tr><td colspan="10" class="empty">No open positions.</td></tr>'

    closed_rows = ""
    for t in sorted(closed, key=lambda x: x.get("exit_at", ""), reverse=True)[:60]:
        cls = "pos" if t["pnl"] >= 0 else "neg"
        closed_rows += (f'<tr><td class="tk">{t["symbol"]}</td>'
                        f'<td><span class="chip">CH6</span>'
                        f'{"<span class=chip2>SHORT</span>" if t["side"] == -1 else ""}</td>'
                        f'<td class="num">{t["shares"]:,}</td>'
                        f'<td class="num">${t["entry_px"]:,.2f}</td>'
                        f'<td class="num">${t["exit_px"]:,.2f}</td>'
                        f'<td class="num {cls}">{money(t["pnl"], True)}</td>'
                        f'<td class="num {cls}">{t["ret_pct"]:+.2f}%</td>'
                        f'<td><span class="status">{t["reason"]}</span></td>'
                        f'<td>{t.get("entry_date", "")}</td>'
                        f'<td>{t.get("exit_at", "")[5:16].replace("T", " ")}</td></tr>')
    if not closed_rows:
        closed_rows = '<tr><td colspan="10" class="empty">No closed trades yet.</td></tr>'

    html = f"""<title>CH6 Fast Harvest</title>
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
.tiles {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(135px,1fr)); gap:10px; }}
.tile {{ background:var(--card); border:1px solid var(--line);
  border-radius:10px; padding:12px 14px; }}
.tile .k {{ font-size:.62rem; text-transform:uppercase;
  letter-spacing:.08em; color:var(--muted); }}
.tile .v {{ font-size:1.12rem; font-weight:650;
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
</style>
<main>
<header>
  <h1>CH6 — Fast Harvest</h1>
  <div class="sub">Same entries as CH3, different exits (the A/B test):
   any short past +5% is sold the SAME DAY — immediately if it gives
   back 1 point from its best, otherwise at the end-of-day sweep;
   never-armed positions keep CH3's 5-session backstop · prices
   checked every 5 minutes · clean start 2026-08-07, no inherited
   positions · SIMULATED — no real orders, borrow costs not modeled ·
   rules frozen until 20 closures · engine ch6_fast_harvest_v1 ·
   updated {stamp}</div>
</header>
<section class="tiles">
  <div class="tile"><div class="k">Equity</div><div class="v">{money(equity)}</div></div>
  <div class="tile"><div class="k">Cash</div><div class="v">{money(cash)}</div></div>
  <div class="tile"><div class="k">Realized</div>
    <div class="v {"pos" if realized >= 0 else "neg"}">{money(realized, True)}</div></div>
  <div class="tile"><div class="k">Unrealized</div>
    <div class="v {"pos" if unreal >= 0 else "neg"}">{money(unreal, True)}</div></div>
  <div class="tile"><div class="k">Win rate</div><div class="v">{wr}<div class="k">{wins}W / {losses}L</div></div></div>
  <div class="tile"><div class="k">Open</div><div class="v">{len(opens)}</div></div>
  <div class="tile"><div class="k">Closed</div><div class="v">{len(closed)}</div></div>
</section>
<section class="card">
  <h2>Open Positions<span class="count">{len(opens)}</span></h2>
  <div class="twrap"><table>
    <thead><tr><th>Ticker</th><th>Signal</th><th>Shares</th><th>Entry</th>
      <th>Current</th><th>Unreal. P&amp;L</th><th>P&amp;L %</th><th>Peak</th>
      <th>Status</th><th>Entered</th></tr></thead>
    <tbody>{open_rows}</tbody></table></div>
</section>
<section class="card">
  <h2>Closed Trades<span class="count">{len(closed)}</span></h2>
  <div class="twrap"><table>
    <thead><tr><th>Ticker</th><th>Signal</th><th>Shares</th><th>Entry</th>
      <th>Exit</th><th>P&amp;L $</th><th>P&amp;L %</th><th>Exit reason</th>
      <th>Entered</th><th>Exited</th></tr></thead>
    <tbody>{closed_rows}</tbody></table></div>
</section>
<p class="foot"><b>Reading SHORT rows:</b> a short sale SELLS at the
Entry price and buys back at Current — Current below Entry is a
profit. ARMED = past +5%, will be sold today. HARVEST = sold at the
end-of-day sweep; GIVEBACK = sold intraday after slipping 1 point
off its peak; TIME = 5-session backstop. This book shares CH3's
entries exactly — the difference between the two pages IS the exit
policy experiment.</p>
</main>
"""
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)
    print("page written:", out_path)


if __name__ == "__main__":
    main()
