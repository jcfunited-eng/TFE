"""
ch4_spring_page.py — CH4 paper book rendered in the TFE platform style.
Columns and conventions mirror taofinancialengine.com/portfolio-advisor.
Usage: python tools/ch4_spring_page.py /path/out.html
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

BOOK = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                    "artifacts", "vtvr_observer", "ch4_spring_book.json")
CASH0 = 100_000.0


def main():
    out_path = sys.argv[1]
    book = {"cash": CASH0, "positions": {}, "closed": [],
            "last_processed": None}
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

    # 2026-08-13 (Joe's catch: every row read "no quote"): when the live
    # quote feed fails, the store's OFFICIAL CLOSE is an honest mark —
    # dated, real, checkable — unlike the fabricated entry-price fallback
    # this page was built to kill. Live quote first; store close second,
    # labeled with its date; "no quote" only when neither exists.
    close_marked = {}
    missing = [s for s in opens if s not in marks]
    if missing:
        try:
            import pandas as pd
            root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            st = pd.read_parquet(
                os.path.join(root, "ch4_live_store.parquet"),
                columns=["Date", "Symbol", "Close"])
            latest = st["Date"].max()
            px_close = dict(
                st[st["Date"] == latest][["Symbol", "Close"]].values)
            close_day = str(latest)[:10]
            for s in missing:
                px = px_close.get(s)
                if px and float(px) > 0:
                    marks[s] = float(px)
                    close_marked[s] = close_day
        except Exception:
            pass

    invested = sum(p["notional"] for p in opens.values())
    # Display math contract: every row must multiply out by hand.
    # Shares are fractional (stake / entry), marks are rounded to cents
    # BEFORE computing P&L, and the tiles are sums of the row values.
    # A MISSING QUOTE IS NOT A FLAT STOCK (2026-08-10, Joe's catch).
    # This used to fall back to the entry price when the feed returned
    # nothing, which draws a row at exactly +0.00% — identical on screen to
    # a name that genuinely did not move, and it quietly fed a fabricated
    # mark into the tiles. A price we do not have is now reported as one we
    # do not have, and it is left out of the sums rather than invented.
    def row_upl(sym, p):
        entry = p["entry_px"]
        px = marks.get(sym)
        shares = p.get("shares") or (int(p["notional"] // entry)
                                     if entry else 0)
        if px is None:
            return shares, None, None
        cur = round(px, 2)
        return shares, cur, round(shares * (cur - entry) * p.get("side", 1), 2)

    unpriced = [s for s in opens if s not in marks]
    unreal = sum(v for v in (row_upl(s, p)[2] for s, p in opens.items())
                 if v is not None)
    realized = sum(t.get("pnl", 0.0) for t in closed)
    value = cash + invested + unreal
    total_pl = value - CASH0
    wins = sum(1 for t in closed if t.get("pnl", 0) > 0)
    losses = len(closed) - wins
    wr = f"{100 * wins / len(closed):.1f}%" if closed else "0.0%"
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    last_bar = book.get("last_processed") or "\u2014"

    # Stated on the page, not buried: which names the totals could not
    # include, because a total that silently omits a position is a total
    # that cannot be checked by hand.
    unpriced_note = (
        f' · <b>NO QUOTE for {", ".join(sorted(unpriced))}</b> — '
        f'{"that position is" if len(unpriced) == 1 else "those positions are"} '
        f'excluded from the totals below'
    ) if unpriced else ""
    if close_marked:
        day = sorted(set(close_marked.values()))[-1]
        unpriced_note += (
            f' · live quotes unavailable for {len(close_marked)} name'
            f'{"s" if len(close_marked) != 1 else ""} — marked at the '
            f'official {day} close instead')

    def money(x, signed=False):
        s = f"${abs(x):,.2f}"
        return (("+" if x >= 0 else "-") + s) if signed else s

    open_rows = ""
    for sym, p in sorted(opens.items()):
        side = p.get("side", 1)
        shares, cur, upl = row_upl(sym, p)
        if cur is None:
            # No quote came back. Say so; do not draw a price we do not have.
            open_rows += (f'<tr><td class="tk">{sym}</td>'
                          f'<td><span class="chip">CH4</span>'
                          f'{"<span class=chip2>SHORT</span>" if side == -1 else ""}</td>'
                          f'<td class="num">{shares:,}</td>'
                          f'<td class="num">${p["entry_px"]:,.2f}</td>'
                          f'<td class="num">no quote</td>'
                          f'<td class="num">\u2014</td>'
                          f'<td class="num">\u2014</td>'
                          f'<td><span class="status">FILLED</span></td>'
                          f'<td>{p.get("entry_date", "")}</td></tr>')
            continue
        pct = 100 * upl / p["notional"] if p["notional"] else 0.0
        cls = "pos" if upl >= 0 else "neg"
        open_rows += (f'<tr><td class="tk">{sym}</td>'
                      f'<td><span class="chip">CH4</span>'
                      f'{"<span class=chip2>SHORT</span>" if side == -1 else ""}</td>'
                      f'<td class="num">{shares:,}</td>'
                      f'<td class="num">${p["entry_px"]:,.2f}</td>'
                      f'<td class="num">${cur:,.2f}</td>'
                      f'<td class="num {cls}">{money(upl, True)}</td>'
                      f'<td class="num {cls}">{pct:+.2f}%</td>'
                      f'<td><span class="status">FILLED</span></td>'
                      f'<td>{p.get("entry_date", "")}</td></tr>')
    if not open_rows:
        open_rows = '<tr><td colspan="9" class="empty">No open positions.</td></tr>'

    closed_rows = ""
    for t in sorted(closed, key=lambda x: x.get("exit_date", ""), reverse=True)[:60]:
        pnl = t.get("pnl", 0.0)
        cls = "pos" if pnl >= 0 else "neg"
        side = t.get("side", 1)
        shares = int(round(t.get("notional", 0) / t["entry_px"])) if t.get("entry_px") else 0
        closed_rows += (f'<tr><td class="tk">{t["sym"]}</td>'
                        f'<td><span class="chip">CH4</span>'
                        f'{"<span class=chip2>SHORT</span>" if side == -1 else ""}</td>'
                        f'<td class="num">${t["entry_px"]:,.2f}</td>'
                        f'<td class="num">${t.get("exit_px", 0):,.2f}</td>'
                        f'<td class="num {cls}">{money(pnl, True)}</td>'
                        f'<td class="num {cls}">{t.get("ret_pct", 0):+.2f}%</td>'
                        f'<td><span class="status">{t.get("reason", "")}</span></td>'
                        f'<td>{t.get("entry_date", "")}</td>'
                        f'<td>{t.get("exit_date", "")}</td></tr>')
    if not closed_rows:
        closed_rows = '<tr><td colspan="9" class="empty">No closed trades yet.</td></tr>'

    html = f"""<title>CH4 Paper Trades</title>
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
.mode {{ background:var(--card); border:1px solid var(--line);
  border-radius:10px; padding:10px 14px; font-size:.8rem;
  display:flex; gap:18px; align-items:center; color:var(--muted); }}
.mode .pill {{ background:#3b6ecc; color:#fff; font-weight:700;
  font-size:.68rem; padding:3px 10px; border-radius:12px; }}
.mode .on {{ background:var(--accent); color:#fff; font-weight:700;
  font-size:.68rem; padding:3px 10px; border-radius:12px; }}
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
  <h1>CH4 — Portfolio</h1>
  <div class="sub">Herd-conditioned structural patterns on the full
   5,200-name field · positions held to the third pattern boundary ·
   no new entries before weekends · engine herd_kgate_v1 ·
   last processed bar {last_bar} · updated {stamp}{unpriced_note}</div>
</header>
<div class="mode"><span>Mode <span class="pill">PAPER</span></span>
  <span>Auto-TFE <span class="on">ON</span></span>
  <span>Funded $ {int(CASH0):,}</span>
  <span>Sizing 10% / position, max 10</span></div>
<section class="tiles">
  <div class="tile"><div class="k">Portfolio value</div><div class="v">{money(value)}</div></div>
  <div class="tile"><div class="k">Cash on hand</div><div class="v">{money(cash)}</div></div>
  <div class="tile"><div class="k">Invested</div><div class="v">{money(invested)}</div></div>
  <div class="tile"><div class="k">Total P&amp;L</div>
    <div class="v {"pos" if total_pl >= 0 else "neg"}">{money(total_pl, True)}</div></div>
  <div class="tile"><div class="k">Realized</div>
    <div class="v {"pos" if realized >= 0 else "neg"}">{money(realized, True)}</div></div>
  <div class="tile"><div class="k">Unrealized</div>
    <div class="v {"pos" if unreal >= 0 else "neg"}">{money(unreal, True)}</div></div>
  <div class="tile"><div class="k">Win rate</div><div class="v">{wr}<div class="k">{wins}W / {losses}L</div></div></div>
  <div class="tile"><div class="k">Open positions</div><div class="v">{len(opens)}</div></div>
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
    <thead><tr><th>Ticker</th><th>Signal</th><th>Entry</th><th>Exit</th>
      <th>P&amp;L $</th><th>P&amp;L %</th><th>Exit reason</th>
      <th>Entered</th><th>Exited</th></tr></thead>
    <tbody>{closed_rows}</tbody></table></div>
</section>
<p class="foot"><b>Reading SHORT rows:</b> a short sale SELLS at the
Entry price and buys back at Current — Current below Entry is a
profit, above Entry a loss; longs read the normal way. Paper
simulation — no real orders. Decisions use closed bars only; the
daily pass runs after each market close. The engine enters only when
a completed pattern's herd-conditioned record calls direction at
75%+ consistency over 20+ prior cases.</p>
</main>
"""
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)
    print("page written:", out_path)


if __name__ == "__main__":
    main()
