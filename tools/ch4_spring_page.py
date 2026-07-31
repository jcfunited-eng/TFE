"""
ch4_spring_page.py — render the CH4 spring-channel paper book to HTML.

Reads artifacts/vtvr_observer/ch4_spring_book.json and writes the page
(same visual system as the established CH4 page). The published artifact
is updated from sessions; this file is regenerated after every pass.

Usage: python tools/ch4_spring_page.py /path/out.html
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone

BOOK = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                    "artifacts", "vtvr_observer", "ch4_spring_book.json")


def main():
    out_path = sys.argv[1]
    if os.path.exists(BOOK):
        with open(BOOK, encoding="utf-8") as fh:
            book = json.load(fh)
    else:
        book = {"cash": 100000.0, "positions": {}, "closed": [],
                "last_processed": None, "equity_mark": 100000.0}

    open_pos = book.get("positions", {})
    closed = book.get("closed", [])
    cash = book.get("cash", 100000.0)
    equity = book.get("equity_mark", cash)
    realized = sum(t.get("pnl", 0.0) for t in closed)
    wins = sum(1 for t in closed if t.get("pnl", 0) > 0)
    wr = f"{100 * wins / len(closed):.0f}%" if closed else "n/a"
    last_bar = book.get("last_processed") or "—"

    open_rows = ""
    for sym, p in sorted(open_pos.items()):
        side = "LONG" if p.get("side", 1) == 1 else "SHORT"
        open_rows += (f'<tr><td class="tk">{sym}</td>'
                      f'<td><span class="badge">{side}</span></td>'
                      f'<td class="num">${p["notional"]:,.0f}</td>'
                      f'<td class="num">${p["entry_px"]:,.2f}</td>'
                      f'<td class="num">{p["bound_pct"]:.1f}%</td>'
                      f'<td><span class="pill">PAPER</span></td>'
                      f'<td>{p["entry_date"]}</td></tr>')
    if not open_rows:
        open_rows = ('<tr><td colspan="7" class="empty">No open positions — '
                     'the engine enters only when energy, compression, and '
                     'release stand together on a vertex.</td></tr>')

    closed_rows = ""
    for t in sorted(closed, key=lambda x: x["exit_date"], reverse=True):
        cls = "up" if t["pnl"] >= 0 else "dn"
        side = "LONG" if t.get("side", 1) == 1 else "SHORT"
        closed_rows += (f'<tr><td>{t["exit_date"]}</td>'
                        f'<td class="tk">{t["sym"]}</td>'
                        f'<td><span class="badge">{side}</span></td>'
                        f'<td class="num {cls}">${t["pnl"]:+,.2f}</td>'
                        f'<td class="num {cls}">{t["ret_pct"]:+.2f}%</td>'
                        f'<td>{t["reason"]}</td>'
                        f'<td>{t.get("engine", "")}</td></tr>')
    if not closed_rows:
        closed_rows = '<tr><td colspan="7" class="empty">No closed trades yet.</td></tr>'

    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    html = f"""<title>CH4 Paper Trades</title>
<style>
:root {{ --bg:#f4f6f4; --card:#ffffff; --head:#e7f2ea; --ink:#22302a;
  --muted:#6b7a72; --line:#e2e7e2; --up:#1a9550; --dn:#d64545;
  --badge:#0a7ea4; --pill:#e7f2ea; --pilltx:#2c6b47; }}
@media (prefers-color-scheme: dark) {{ :root {{ --bg:#151d18; --card:#1d2721;
  --head:#24332a; --ink:#e4e9e4; --muted:#93a09a; --line:#2c3a33;
  --up:#4fc07f; --dn:#e57a7a; --badge:#2b95b3; --pill:#24332a; --pilltx:#8fc7a6; }} }}
:root[data-theme="dark"] {{ --bg:#151d18; --card:#1d2721; --head:#24332a;
  --ink:#e4e9e4; --muted:#93a09a; --line:#2c3a33; --up:#4fc07f; --dn:#e57a7a;
  --badge:#2b95b3; --pill:#24332a; --pilltx:#8fc7a6; }}
:root[data-theme="light"] {{ --bg:#f4f6f4; --card:#ffffff; --head:#e7f2ea;
  --ink:#22302a; --muted:#6b7a72; --line:#e2e7e2; --up:#1a9550; --dn:#d64545;
  --badge:#0a7ea4; --pill:#e7f2ea; --pilltx:#2c6b47; }}
body {{ background:var(--bg); color:var(--ink);
  font:14px/1.5 system-ui,-apple-system,"Segoe UI",sans-serif;
  margin:0; padding:24px 16px 60px; }}
main {{ max-width:1080px; margin:0 auto; display:flex;
  flex-direction:column; gap:18px; }}
h1 {{ font-size:1.15rem; margin:0; }}
.sub {{ color:var(--muted); font-size:.8rem; margin-top:2px; }}
.tiles {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(130px,1fr));
  gap:10px; }}
.tile {{ background:var(--card); border:1px solid var(--line);
  border-radius:8px; padding:12px 14px; }}
.tile .k {{ font-size:.62rem; text-transform:uppercase; letter-spacing:.08em;
  color:var(--muted); }}
.tile .v {{ font-size:1.15rem; font-weight:650;
  font-variant-numeric:tabular-nums; margin-top:2px; }}
.v.up {{ color:var(--up); }} .v.dn {{ color:var(--dn); }}
.card {{ background:var(--card); border:1px solid var(--line);
  border-radius:10px; overflow:hidden; }}
.card h2 {{ font-size:.8rem; margin:0; padding:12px 16px; }}
.card h2 small {{ color:var(--muted); font-weight:400; }}
.method {{ padding:0 16px 14px; color:var(--muted); font-size:.78rem;
  max-width:78ch; }}
.method b {{ color:var(--ink); }}
.twrap {{ overflow-x:auto; }}
table {{ border-collapse:collapse; width:100%; font-size:.8rem; }}
thead tr {{ background:var(--head); }}
th {{ text-align:left; padding:8px 14px; font-size:.62rem;
  text-transform:uppercase; letter-spacing:.07em; color:var(--muted);
  white-space:nowrap; }}
td {{ padding:8px 14px; border-top:1px solid var(--line); white-space:nowrap; }}
td.num {{ text-align:right; font-variant-numeric:tabular-nums; }}
td.tk {{ font-weight:700; letter-spacing:.02em; }}
td.up {{ color:var(--up); font-weight:600; }} td.dn {{ color:var(--dn); font-weight:600; }}
td.empty {{ color:var(--muted); text-align:center; padding:22px; }}
.badge {{ background:var(--badge); color:#fff; font-size:.6rem;
  font-weight:700; padding:2px 7px; border-radius:4px; letter-spacing:.04em; }}
.pill {{ background:var(--pill); color:var(--pilltx); font-size:.6rem;
  font-weight:700; padding:2px 8px; border-radius:9px; }}
.foot {{ color:var(--muted); font-size:.72rem; max-width:78ch; }}
</style>
<main>
<header>
  <h1>CH4 — Paper Trades <span class="badge">CH4</span></h1>
  <div class="sub">Engine vtvr_spring_v1 · original VTVR joint-field kernel ·
   last processed bar {last_bar} · page updated {stamp} · paper only</div>
</header>

<section class="tiles">
  <div class="tile"><div class="k">Portfolio value</div>
    <div class="v">${equity:,.2f}</div></div>
  <div class="tile"><div class="k">Cash on hand</div>
    <div class="v">${cash:,.2f}</div></div>
  <div class="tile"><div class="k">Realized</div>
    <div class="v {'up' if realized >= 0 else 'dn'}">${realized:+,.2f}</div></div>
  <div class="tile"><div class="k">Win rate</div><div class="v">{wr}</div></div>
  <div class="tile"><div class="k">Open positions</div>
    <div class="v">{len(open_pos)}</div></div>
  <div class="tile"><div class="k">Closed trades</div>
    <div class="v">{len(closed)}</div></div>
</section>

<section class="card">
  <h2>How this engine decides</h2>
  <div class="method">
    Structural computation runs on the original VTVR joint-field kernel
    (exact arithmetic, full retention, 60-name field). A position opens only
    when three physical facts stand together at a closed bar:
    <b>energy</b> — the stock has declined at least 26.8% from the origin of
    its large structure (26.8 is derived from the 36.7% harvest target, not
    chosen); <b>compression</b> — the kernel's swept-volume field has gone
    quiet against its own recent normal; <b>release</b> — the kernel's
    structural-share momentum has turned and the fine price structure has
    flipped with it. Exits: the +36.7% harvest, the large structure turning
    against the position, or the reversal bound. Short side by mirror
    symmetry. Sizing risks 1% of equity per position against each
    stock's own reversal bound. Every trade carries its engine version.
  </div>
</section>

<section class="card">
  <h2>Open Positions <small>{len(open_pos)}</small></h2>
  <div class="twrap"><table>
    <thead><tr><th>Ticker</th><th>Side</th><th>Notional</th>
      <th>Entry</th><th>Bound</th><th>Status</th><th>Entered</th></tr></thead>
    <tbody>{open_rows}</tbody>
  </table></div>
</section>

<section class="card">
  <h2>Closed Trades <small>{len(closed)}</small></h2>
  <div class="twrap"><table>
    <thead><tr><th>Date</th><th>Ticker</th><th>Side</th>
      <th>P&amp;L $</th><th>P&amp;L %</th><th>Exit reason</th><th>Engine</th></tr></thead>
    <tbody>{closed_rows}</tbody>
  </table></div>
</section>

<p class="foot">Paper simulation only — no real orders. This channel replaced
the earlier 3-band engine (bands_v1, retired 2026-07-31 with a $100,000
untouched book and no demonstrated edge). The daily pass runs after each
market close; decisions use closed bars only.</p>
</main>
"""
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"page written: {out_path}")


if __name__ == "__main__":
    main()
