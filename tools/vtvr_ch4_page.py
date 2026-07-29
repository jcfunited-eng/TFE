"""
vtvr_ch4_page.py — render the CH4 paper book as a TFE-style trades page.

Reads artifacts/vtvr_observer/ch4_book.json, marks open positions at the
latest trade price (Alpaca data API), writes HTML to the path given as
argv[1]. Format mirrors the taofinancialengine.com portfolio tables:
summary tiles, Open Positions, Closed Trades. Paper only; labeled as such.

Usage: python tools/vtvr_ch4_page.py /path/out.html
"""

from __future__ import annotations

import json
import os
import sys
import urllib.request

BOOK = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "artifacts", "vtvr_observer", "ch4_book.json")


def latest_prices(symbols):
    if not symbols:
        return {}
    key = os.environ.get("APCA_API_KEY_ID") or os.environ.get("ALPACA_API_KEY", "")
    sec = (os.environ.get("APCA_API_SECRET_KEY")
           or os.environ.get("ALPACA_API_SECRET_KEY", ""))
    url = ("https://data.alpaca.markets/v2/stocks/snapshots?symbols="
           + ",".join(symbols) + "&feed=iex")
    req = urllib.request.Request(url, headers={
        "APCA-API-KEY-ID": key, "APCA-API-SECRET-KEY": sec})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            data = json.loads(r.read())
        out = {}
        for s, snap in data.items():
            p = (snap.get("latestTrade") or {}).get("p") \
                or (snap.get("latestQuote") or {}).get("ap")
            if p:
                out[s] = float(p)
        return out
    except Exception:
        return {}


def main():
    out_path = sys.argv[1]
    with open(BOOK, encoding="utf-8") as fh:
        book = json.load(fh)

    open_pos = book.get("open", {})
    closed = book.get("closed", [])
    px = latest_prices(sorted(open_pos.keys()))

    open_rows = ""
    unreal_total = 0.0
    for sym in sorted(open_pos, key=lambda s: open_pos[s]["entry_date"],
                      reverse=True):
        p = open_pos[sym]
        cur = px.get(sym)
        entry = p["entry_px"]
        if cur:
            upl = (cur - entry) * p["shares"]
            pct = (cur / entry - 1) * 100
            unreal_total += upl
            cur_s = f"${cur:,.2f}"
            upl_s = f'<td class="num {"up" if upl >= 0 else "dn"}">${upl:+,.2f}</td>'
            pct_s = f'<td class="num {"up" if pct >= 0 else "dn"}">{pct:+.2f}%</td>'
        else:
            cur_s, upl_s, pct_s = "—", '<td class="num">—</td>', '<td class="num">—</td>'
        open_rows += (f'<tr><td class="tk">{sym}</td>'
                      f'<td><span class="badge">CH4</span></td>'
                      f'<td class="num">{p["shares"]:.2f}</td>'
                      f'<td class="num">${entry:,.2f}</td>'
                      f'<td class="num">{cur_s}</td>'
                      f'{upl_s}{pct_s}'
                      f'<td><span class="pill">PAPER</span></td>'
                      f'<td>{p["entry_date"]}</td></tr>')
    if not open_rows:
        open_rows = ('<tr><td colspan="9" class="empty">No open positions — '
                     'the book enters only when the field engine fires.</td></tr>')

    closed_rows = ""
    realized = 0.0
    wins = 0
    for t in sorted(closed, key=lambda x: x["exit_date"], reverse=True):
        realized += t["pnl"]
        wins += 1 if t["pnl"] > 0 else 0
        cls = "up" if t["pnl"] >= 0 else "dn"
        closed_rows += (f'<tr><td>{t["exit_date"]}</td>'
                        f'<td class="tk">{t["sym"]}</td>'
                        f'<td><span class="badge">CH4</span></td>'
                        f'<td class="num {cls}">${t["pnl"]:+,.2f}</td>'
                        f'<td class="num {cls}">{t["ret_pct"]:+.2f}%</td>'
                        f'<td>{t["reason"]}</td></tr>')
    if not closed_rows:
        closed_rows = '<tr><td colspan="6" class="empty">No closed trades yet.</td></tr>'

    cash = book.get("cash", 100000.0)
    equity = cash + sum(
        (px.get(s, p["entry_px"])) * p["shares"] for s, p in open_pos.items())
    wr = f"{100 * wins / len(closed):.0f}%" if closed else "n/a"

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
.twrap {{ overflow-x:auto; }}
table {{ border-collapse:collapse; width:100%; font-size:.8rem; }}
thead tr {{ background:var(--head); }}
th {{ text-align:left; padding:8px 14px; font-size:.62rem;
  text-transform:uppercase; letter-spacing:.07em; color:var(--muted);
  white-space:nowrap; }}
th.num {{ text-align:right; }}
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
  <div class="sub">Joint-field side kernel · paper book · opened {book.get("started", "—")}
   · last bar {book.get("last_bar", "—")} · entries recorded with engine version, no live claims</div>
</header>

<section class="tiles">
  <div class="tile"><div class="k">Portfolio value</div>
    <div class="v">${equity:,.2f}</div></div>
  <div class="tile"><div class="k">Cash on hand</div>
    <div class="v">${cash:,.2f}</div></div>
  <div class="tile"><div class="k">Realized</div>
    <div class="v {'up' if realized >= 0 else 'dn'}">${realized:+,.2f}</div></div>
  <div class="tile"><div class="k">Unrealized</div>
    <div class="v {'up' if unreal_total >= 0 else 'dn'}">${unreal_total:+,.2f}</div></div>
  <div class="tile"><div class="k">Win rate</div><div class="v">{wr}</div></div>
  <div class="tile"><div class="k">Open positions</div>
    <div class="v">{len(open_pos)}</div></div>
</section>

<section class="card">
  <h2>Open Positions <small>{len(open_pos)}</small></h2>
  <div class="twrap"><table>
    <thead><tr><th>Ticker</th><th>Signal</th><th class="num">Shares</th>
      <th class="num">Entry</th><th class="num">Current</th>
      <th class="num">Unreal. P&amp;L</th><th class="num">P&amp;L %</th>
      <th>Status</th><th>Detected</th></tr></thead>
    <tbody>{open_rows}</tbody>
  </table></div>
</section>

<section class="card">
  <h2>Closed Trades <small>{len(closed)}</small></h2>
  <div class="twrap"><table>
    <thead><tr><th>Date</th><th>Ticker</th><th>CH</th>
      <th class="num">P&amp;L $</th><th class="num">P&amp;L %</th>
      <th>Exit reason</th></tr></thead>
    <tbody>{closed_rows}</tbody>
  </table></div>
</section>

<p class="foot">Paper simulation only — no real orders. Entry engine under
replacement per the 2026-07-29 post-audit: the deployed 3-band rule is
flattened; the whole-object field engine (v2, tempo-tolerant,
dimension-budgeted) is in walk-forward test and will be wired in with its
version stamped on every trade it makes.</p>
</main>
"""
    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write(html)
    print(f"written {out_path} ({len(html)} bytes)")


if __name__ == "__main__":
    main()
