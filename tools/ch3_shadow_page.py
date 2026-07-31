"""
ch3_shadow_page.py — render the CH3 shadow hunter log to HTML.
Usage: python tools/ch3_shadow_page.py /path/out.html
"""
from __future__ import annotations
import json, os, sys
from datetime import datetime, timezone

LOG = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                   "artifacts", "vtvr_observer", "ch3_shadow_log.json")

def main():
    out_path = sys.argv[1]
    log = {"finds": [], "days": {}}
    if os.path.exists(LOG):
        log = json.load(open(LOG))
    finds = sorted(log.get("finds", []), key=lambda f: f.get("found_at", ""), reverse=True)
    days = log.get("days", {})
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    today = stamp[:10]
    tf = [f for f in finds if f.get("date") == today]
    open_n = sum(1 for f in tf if f["status"] == "OPEN")
    hit_n = sum(1 for f in tf if f["status"] == "HIT")

    rows = ""
    for f in finds[:120]:
        st = f["status"]
        cls = "up" if st == "HIT" else ("dn" if st == "MISS" else "")
        ret = f.get("ret_pct")
        rows += (f'<tr><td>{f["date"]}</td><td>{f.get("found_at","")[11:16]}</td>'
                 f'<td class="tk">{f["symbol"]}</td>'
                 f'<td><span class="badge">{"LONG" if f["side"]==1 else "SHORT"}</span></td>'
                 f'<td class="num">${f["entry_px"]}</td>'
                 f'<td class="num">+{f["target_pct"]}%</td>'
                 f'<td class="num">-{f["bound_pct"]}%</td>'
                 f'<td class="{cls}">{st}</td>'
                 f'<td class="num {cls}">{("%+.2f%%" % ret) if ret is not None else "—"}</td></tr>')
    if not rows:
        rows = ('<tr><td colspan="9" class="empty">No finds logged yet — the '
                'hunter cycles every 15 minutes during market hours and only '
                'logs when the intraday spring stands on a stock.</td></tr>')

    day_rows = ""
    for d, s in sorted(days.items(), reverse=True):
        day_rows += (f'<tr><td>{d}</td><td class="num">{s["finds"]}</td>'
                     f'<td class="num">{s["hits"]}</td>'
                     f'<td class="num">{s["hit_rate_pct"] if s["hit_rate_pct"] is not None else "—"}%</td>'
                     f'<td class="num">{("%+.2f%%" % s["mean_ret_pct"]) if s["mean_ret_pct"] is not None else "—"}</td></tr>')
    if not day_rows:
        day_rows = '<tr><td colspan="5" class="empty">First session in progress.</td></tr>'

    html = f"""<title>CH3 Shadow Hunter</title>
<style>
:root {{ --bg:#f6f5f2; --card:#ffffff; --head:#efe9dd; --ink:#2b2620;
  --muted:#7a7263; --line:#e6e1d6; --up:#1a7f4e; --dn:#c24a3a;
  --badge:#8a5a1e; --pill:#efe9dd; --pilltx:#6b5322; }}
@media (prefers-color-scheme: dark) {{ :root {{ --bg:#1b1813; --card:#242019;
  --head:#2e281e; --ink:#e9e4da; --muted:#a49a87; --line:#393225;
  --up:#4fc088; --dn:#e0796a; --badge:#c89044; --pill:#2e281e; --pilltx:#cdb27a; }} }}
:root[data-theme="dark"] {{ --bg:#1b1813; --card:#242019; --head:#2e281e;
  --ink:#e9e4da; --muted:#a49a87; --line:#393225; --up:#4fc088; --dn:#e0796a;
  --badge:#c89044; --pill:#2e281e; --pilltx:#cdb27a; }}
:root[data-theme="light"] {{ --bg:#f6f5f2; --card:#ffffff; --head:#efe9dd;
  --ink:#2b2620; --muted:#7a7263; --line:#e6e1d6; --up:#1a7f4e; --dn:#c24a3a;
  --badge:#8a5a1e; --pill:#efe9dd; --pilltx:#6b5322; }}
body {{ background:var(--bg); color:var(--ink);
  font:14px/1.5 system-ui,-apple-system,"Segoe UI",sans-serif;
  margin:0; padding:24px 16px 60px; }}
main {{ max-width:1080px; margin:0 auto; display:flex; flex-direction:column; gap:18px; }}
h1 {{ font-size:1.15rem; margin:0; }}
.sub {{ color:var(--muted); font-size:.8rem; margin-top:2px; }}
.tiles {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(130px,1fr)); gap:10px; }}
.tile {{ background:var(--card); border:1px solid var(--line); border-radius:8px; padding:12px 14px; }}
.tile .k {{ font-size:.62rem; text-transform:uppercase; letter-spacing:.08em; color:var(--muted); }}
.tile .v {{ font-size:1.15rem; font-weight:650; font-variant-numeric:tabular-nums; margin-top:2px; }}
.card {{ background:var(--card); border:1px solid var(--line); border-radius:10px; overflow:hidden; }}
.card h2 {{ font-size:.8rem; margin:0; padding:12px 16px; }}
.twrap {{ overflow-x:auto; }}
table {{ border-collapse:collapse; width:100%; font-size:.8rem; }}
thead tr {{ background:var(--head); }}
th {{ text-align:left; padding:8px 14px; font-size:.62rem; text-transform:uppercase;
  letter-spacing:.07em; color:var(--muted); white-space:nowrap; }}
td {{ padding:8px 14px; border-top:1px solid var(--line); white-space:nowrap; }}
td.num {{ text-align:right; font-variant-numeric:tabular-nums; }}
td.tk {{ font-weight:700; }}
td.up, .up {{ color:var(--up); font-weight:600; }} td.dn, .dn {{ color:var(--dn); font-weight:600; }}
td.empty {{ color:var(--muted); text-align:center; padding:22px; }}
.badge {{ background:var(--badge); color:#fff; font-size:.6rem; font-weight:700;
  padding:2px 7px; border-radius:4px; }}
.foot {{ color:var(--muted); font-size:.72rem; max-width:78ch; }}
</style>
<main>
<header>
  <h1>CH3 — Shadow Hunter <span class="badge">NO ORDERS</span></h1>
  <div class="sub">Engine ch3_spring_intraday_v1 · cycles every 15 minutes during
   market hours · logs and grades what it WOULD trade · live channel remains
   halted · page updated {stamp}</div>
</header>
<section class="tiles">
  <div class="tile"><div class="k">Finds today</div><div class="v">{len(tf)}</div></div>
  <div class="tile"><div class="k">Open</div><div class="v">{open_n}</div></div>
  <div class="tile"><div class="k">Hits today</div><div class="v">{hit_n}</div></div>
  <div class="tile"><div class="k">Sessions logged</div><div class="v">{len(days)}</div></div>
</section>
<section class="card">
  <h2>Day summaries</h2>
  <div class="twrap"><table>
    <thead><tr><th>Date</th><th>Finds</th><th>Hits</th><th>Hit rate</th><th>Mean result</th></tr></thead>
    <tbody>{day_rows}</tbody></table></div>
</section>
<section class="card">
  <h2>Find log <small></small></h2>
  <div class="twrap"><table>
    <thead><tr><th>Date</th><th>Time</th><th>Ticker</th><th>Side</th>
      <th>Entry</th><th>Target</th><th>Bound</th><th>Status</th><th>Result</th></tr></thead>
    <tbody>{rows}</tbody></table></div>
</section>
<p class="foot">Shadow record only — no orders are placed. Each find shows the
entry, target, and bound the engine would have used; HIT means the target was
touched, MISS means the bound was breached, EOD means the session ended first.
This record decides when the live channel re-arms.</p>
</main>
"""
    open(out_path, "w").write(html)
    print("page written:", out_path)

if __name__ == "__main__":
    main()
