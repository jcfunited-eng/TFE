"""THE DOOR — the page at localhost:8765.

The old life served this and the rewrite dropped it, so it has been
dark. Same page, same address, running on what the fabric can do
now: a question goes through the written turn procedure, not a word
search, and what comes back is what the knowledge reached, what it
built as a joint, and what it refused.

Served on a thread so a slow question never touches the beat.
"""
import os, sys, json, html, threading, traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)
import core

PORT = 8765
LIFE = os.path.join(BASE, "life")
STATE = os.path.join(LIFE, "alive.json")
CLAIMS = os.path.normpath(os.path.join(
    BASE, "..", "docs", "fabric_phylums", "93_minted_claims.md"))
AREAS = os.path.join(LIFE, "areas_to_write.md")

PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>The Compute Fabric</title><style>
:root{--cloth:#faf8f3;--ink:#221f1b;--thread:#a33b2e;
--dim:#6f6a62;--line:#ddd8cf;--card:#fffdf9}
@media (prefers-color-scheme:dark){:root{--cloth:#17150f;
--ink:#ece7dc;--thread:#d9705c;--dim:#958e82;--line:#332f27;
--card:#1e1b15}}
*{box-sizing:border-box}
body{font-family:Georgia,'Times New Roman',serif;max-width:42em;
margin:0 auto;padding:2.2em 1em 3em;background:var(--cloth);
color:var(--ink);line-height:1.55}
h1{font-size:1.45em;font-weight:normal;margin:0;
border-bottom:2px solid var(--thread);display:inline-block;
padding-bottom:.15em}
.tag{color:var(--dim);margin:.7em 0 1.6em;font-size:.95em}
.askrow{display:flex;gap:.6em;align-items:flex-start}
textarea#q{flex:1;font-size:1.05em;padding:.6em .7em;
border:1px solid var(--line);border-radius:2px;line-height:1.5;
background:var(--card);font-family:inherit;color:var(--ink);
min-height:5.2em;resize:vertical}
textarea#q:focus{outline:2px solid var(--thread);outline-offset:1px}
button{font-size:1em;padding:.55em 1.5em;font-family:inherit;
background:var(--thread);color:var(--cloth);border:none;
border-radius:2px;cursor:pointer}
button:hover{filter:brightness(1.1)}
button:focus-visible{outline:2px solid var(--ink)}
pre{white-space:pre-wrap;background:var(--card);
border:1px solid var(--line);border-left:3px solid var(--thread);
padding:1em 1.1em;font-size:.92em;margin:1.2em 0;
overflow-x:auto;font-family:inherit}
.pulse{display:flex;flex-wrap:wrap;gap:1.4em;margin:1.6em 0 .4em;
padding-top:1em;border-top:1px solid var(--line)}
.pulse div{min-width:4.6em}
.pulse b{display:block;font-size:1.15em;font-weight:normal;
font-variant-numeric:tabular-nums}
.pulse span{font-size:.68em;letter-spacing:.08em;
text-transform:uppercase;color:var(--dim)}
.life{color:var(--dim);font-size:.85em;font-style:italic;
margin-top:1em}
a{color:var(--thread)}
footer{margin-top:2em;font-size:.85em;color:var(--dim);
border-top:1px solid var(--line);padding-top:1em}
</style></head><body>
<h1>The Compute Fabric</h1>
<p class="tag">Say something to it. What comes back first is what it
understood you to have said &mdash; what the sentence turns on, what
it is about, what would count as an answer, what it rules out &mdash;
and how it settled each of those, including when it was guessing.
Nothing in that part is fetched: no entry of its own is returned by
any of it. Understanding comes before making, so this is the part
that is being built.</p>
<div class="askrow">
<textarea id="q" rows="3" placeholder="why does bread rise"
 autofocus></textarea>
<button onclick="go()">ask</button>
</div>
<pre id="a">&mdash;</pre>
<div class="pulse" id="pulse"></div>
<p class="life" id="life"></p>
<footer>
<a href="/claims">what it worked out itself</a> &mdash; joints it
built where two things stand together and their roots meet.<br>
<a href="/asks">what it is asking for</a> &mdash; ground where
things keep almost connecting and nothing underneath is written.
</footer>
<script>
async function go(){
  const q=document.getElementById('q').value.trim();
  if(!q)return;
  const a=document.getElementById('a');
  a.textContent='thinking\\u2026';
  try{
    const r=await fetch('/ask',{method:'POST',body:q});
    a.textContent=await r.text();
  }catch(e){a.textContent='the door failed: '+e;}
  pulse();
}
document.getElementById('q').addEventListener('keydown',e=>{
  if(e.key==='Enter'&&(e.metaKey||e.ctrlKey))go();
});
async function pulse(){
  try{
    const s=await (await fetch('/pulse')).json();
    document.getElementById('pulse').innerHTML=
      [['beats',s.beats],['questions read',s.read],
       ['claims it wrote',s.minted],['areas it asks for',s.asks],
       ['distinct of last 60',s.distinct]]
      .map(x=>`<div><b>${x[1]}</b><span>${x[0]}</span></div>`).join('');
    document.getElementById('life').textContent=s.alive
      ? 'It is running now, and has been for '+s.beats+' beats.'
      : 'It is not running. Nothing is being added while it is down.';
  }catch(e){}
}
pulse(); setInterval(pulse,15000);
</script></body></html>"""

TALK = None
LOCK = threading.Lock()


def _heard(q):
    """What it understood was said. This comes first and it is the
    part that is actually built: the sentence read into a structure —
    what it turns on, what it is about, what kind of answer would
    count, what it forbids — and no entry is returned by any of it.

    It is first on the page on purpose. Communication before assembly:
    a thing that cannot say what it heard cannot be told what to make,
    and a page that leads with an answer hides which of the two it
    is doing."""
    import wanting
    try:
        return wanting.show(q, core.fabric())
    except Exception as e:
        return (f"I could not read that: {type(e).__name__}: {e}\n"
                f"Said rather than hidden.")


def _answer(q):
    """One turn, through the written procedure — the same one the
    conversation uses.

    Measured 2026-08-29 and not repaired since: five of five answers
    this returned were already written in the corpus before the
    question was asked, so it is retrieval however it is dressed. It
    is kept, below the reading and labelled, because deleting it would
    hide the finding rather than record it."""
    global TALK
    import talk
    with LOCK:
        if TALK is None:
            TALK = talk.Talk(core.fabric())
        try:
            return TALK.turn(q)
        except Exception as e:
            return (f"  that fell over: {type(e).__name__}: {e}\n"
                    f"  Said rather than hidden.")


def _pulse():
    s = {}
    try:
        with open(STATE) as f:
            d = json.load(f)
        s = dict(beats=d.get("beats", 0), read=d.get("read", 0),
                 minted=d.get("minted", 0),
                 asks=d.get("asked_for", 0),
                 distinct=len(set(d.get("recent", []))))
    except (OSError, ValueError):
        s = dict(beats=0, read=0, minted=0, asks=0, distinct=0)
    s["alive"] = True
    return s


def _file_page(title, path, empty):
    try:
        body = open(path).read() if os.path.exists(path) else ""
    except OSError:
        body = ""
    return (f"<!doctype html><meta charset='utf-8'>"
            f"<meta name=viewport content='width=device-width,"
            f"initial-scale=1'><title>{title}</title>"
            f"<style>body{{font-family:Georgia,serif;max-width:46em;"
            f"margin:0 auto;padding:2em 1em;background:#faf8f3;"
            f"color:#221f1b;line-height:1.5}}"
            f"@media(prefers-color-scheme:dark){{body{{"
            f"background:#17150f;color:#ece7dc}}}}"
            f"pre{{white-space:pre-wrap;font-family:inherit;"
            f"font-size:.93em}}a{{color:#a33b2e}}</style>"
            f"<p><a href='/'>&larr; back</a></p><h1>{title}</h1>"
            f"<pre>{html.escape(body) or empty}</pre>")


class Door(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _send(self, body, ctype="text/html; charset=utf-8"):
        b = body.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def do_GET(self):
        p = self.path.split("?")[0]
        if p == "/":
            self._send(PAGE)
        elif p == "/pulse":
            self._send(json.dumps(_pulse()), "application/json")
        elif p == "/claims":
            self._send(_file_page(
                "What it worked out itself", CLAIMS,
                "Nothing yet. It writes a claim only where two "
                "things stand together and their roots actually "
                "meet."))
        elif p == "/asks":
            self._send(_file_page(
                "What it is asking for", AREAS,
                "Nothing yet. It asks for ground where joints keep "
                "failing and nothing underneath is written."))
        else:
            self._send("<p>nothing here. <a href='/'>back</a></p>")

    def do_POST(self):
        n = int(self.headers.get("Content-Length", 0) or 0)
        q = self.rfile.read(n).decode("utf-8", "replace").strip()
        if not q:
            self._send("  nothing asked.", "text/plain; charset=utf-8")
            return
        try:
            out = _heard(q)
            out += ("\n\n" + "-" * 46 +
                    "\nBELOW THIS LINE IS THE OLD ANSWERING PATH, and"
                    "\nit is retrieval: measured, five of five of its"
                    "\nanswers were already written in the corpus"
                    "\nbefore the question was asked. Shown so it is"
                    "\nnot hidden, not because it is the work.\n\n")
            out += _answer(q)
        except Exception:
            out = "  the door fell over:\n" + traceback.format_exc()
        self._send(out, "text/plain; charset=utf-8")


def open_door(log=print):
    """Start serving. Never lets a failure here stop the life."""
    try:
        srv = ThreadingHTTPServer(("0.0.0.0", PORT), Door)
    except OSError as e:
        log(f"the door would not open on {PORT} ({e}) — the life "
            f"carries on without it")
        return None
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    log(f"the door is open at http://localhost:{PORT}/")
    return srv


if __name__ == "__main__":
    core.fabric()
    open_door()
    import time
    while True:
        time.sleep(3600)
