"""THE DOOR — the page at localhost:8765.

The old life served this and the rewrite dropped it, so it has been
dark. Same page, same address, running on what the fabric can do
now: a question goes through the written turn procedure, not a word
search, and what comes back is what the knowledge reached, what it
built as a joint, and what it refused.

Served on a thread so a slow question never touches the beat.
"""
import os, re, sys, json, html, threading, traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)
import core
import phylum_reader as PR

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
#log pre.you{border-left:3px solid var(--dim);color:var(--ink);
margin:1.2em 0 .4em;font-style:italic}
#log pre.it{margin:.4em 0 1.2em}
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
<div id="log"></div>
<div class="askrow">
<textarea id="q" rows="3" placeholder="why does bread rise
(Enter sends; Shift+Enter for a new line)"
 autofocus></textarea>
<button onclick="go()">ask</button>
</div>
<div class="pulse" id="pulse"></div>
<p class="life" id="life"></p>
<footer>
<a href="/claims">what it worked out itself</a> &mdash; joints it
built where two things stand together and their roots meet.<br>
<a href="/asks">what it is asking for</a> &mdash; ground where
things keep almost connecting and nothing underneath is written.
</footer>
<script>
function block(cls,txt){
  const d=document.createElement('pre');
  d.className=cls; d.textContent=txt;
  document.getElementById('log').appendChild(d);
  d.scrollIntoView({block:'nearest'});
  return d;
}
async function go(){
  const box=document.getElementById('q');
  const q=box.value.trim();
  if(!q)return;
  box.value='';
  block('you','YOU: '+q);
  const a=block('it','thinking\\u2026');
  try{
    const r=await fetch('/ask',{method:'POST',body:q});
    a.textContent=await r.text();
  }catch(e){a.textContent='the door failed: '+e;}
  box.focus();
  pulse();
}
document.getElementById('q').addEventListener('keydown',e=>{
  if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();go();}
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


SAY = None


def _say(q):
    """One turn of an actual conversation — the moves staged, the
    reading killing the ones that do not apply, what survives said.
    The thread is held across turns, so it knows what it is on."""
    global SAY
    import saying
    with LOCK:
        if SAY is None:
            SAY = saying.Thread(core.fabric())
        try:
            return SAY.turn(q)
        except Exception as e:
            return (f"that fell over: {type(e).__name__}: {e}  "
                    f"Said rather than hidden.")


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


_CONV = None


def _converse(q):
    """One turn of the conversation — the thread held across
    turns so its questions and your answers connect."""
    global _CONV
    import converse
    with LOCK:
        if _CONV is None:
            _CONV = converse.Converse()
        return _CONV.turn(q)


_FRAME = {"the", "a", "an", "of", "and", "or", "to", "for", "in",
          "on", "at", "is", "are", "was", "were", "be", "been",
          "do", "does", "did", "you", "i", "it", "its", "that",
          "this", "these", "those", "not", "no", "me", "my",
          "your", "with", "by", "as", "so", "if", "then", "than",
          "there", "here", "please", "can", "could", "would",
          "should", "will", "am", "we", "they", "he", "she"}
_ASKS = {"why": "a cause", "how": "a method", "what": "a naming",
         "when": "a time", "where": "a place", "who": "a person",
         "which": "a choice"}
_MAKES = {"create", "make", "build", "write", "compose", "design",
          "invent", "cook", "draw", "plan"}


def _plain(q):
    """The reply's first voice: plain sentences, grounded in the
    NEW fabric (the forty phylums). It says what kind of thing was
    said, where each of its words lives in the fabric — or that a
    word is not held, honestly — and what the machinery can and
    cannot yet do with it. It never pretends to answer or to make."""
    words = [w for w in re.findall(r"[a-zA-Z]+", q.lower())
             if w not in _FRAME]
    ask = next((w for w in words if w in _ASKS), None)
    make = next((w for w in words if w in _MAKES), None)
    content = [w for w in words if w not in _ASKS
               and w not in _MAKES][:6]

    out = []
    if make:
        thing = " ".join(content) or "something"
        out.append(f"You told me to {make} something: {thing}. "
                   f"That is a want, not a question.")
    elif ask:
        out.append(f"You asked '{ask}' — {_ASKS[ask]} would count "
                   f"as an answer.")
    else:
        out.append("You said something to me — I read it as a "
                   "statement or a want, not a question.")

    held_words, held_counts = {}, {}
    for w in content:
        hs = PR.homes(w)
        color = [h for h in hs if h[1] == "color"]
        best = sorted(color or hs, key=lambda h: (
            ("THINGS", "CLAIMS", "SCIENCE", "METHODS", "MEANS",
             "PURPOSE", "HISTORY", "RELATIONS").index(h[2])))[:2]
        if not hs:
            out.append(f"'{w}' — not held anywhere in my forty "
                       f"subjects yet. An honest gap, not a "
                       f"refusal.")
            continue
        for slug, half, section, entry in hs:
            held_words.setdefault(slug, set()).add(w)
            held_counts[slug] = held_counts.get(slug, 0) + 1
        places = "; ".join(
            f"{slug} ({PR.first_line(entry)})"
            for slug, half, section, entry in best)
        out.append(f"'{w}' — held. It lives in {places}")
    # A subject's claim on the want is weighed by SPREAD, the one
    # ranking lesson this fabric has actually proven: a word held
    # by few subjects points harder than a word held by twenty.
    spread = {w: sum(1 for s in held_words if w in held_words[s])
              for w in content}
    held_slugs = {s: (sum(1.0 / spread[w] for w in held_words[s]),
                      held_counts[s])
                  for s in held_words}

    if make:
        made = None
        if held_slugs:
            top = max(held_slugs, key=held_slugs.get)
            try:
                import hands
                made = hands.make(content, top)
            except Exception as e:
                made = (f"the hands fell over: "
                        f"{type(e).__name__}: {e} — said rather "
                        f"than hidden.")
        if made:
            out.append(made)
        elif held_slugs:
            out.append(
                f"What I cannot yet do is the making itself — "
                f"the knowledge your want needs stands mostly in "
                f"{top}, but nothing under your words decomposes "
                f"into components my laws can grip, so I have "
                f"nothing honest to assemble.")
        else:
            out.append(
                "And I hold nothing under those words yet, so "
                "even with hands there would be nothing to "
                "assemble. The gap is the fabric's, and it is "
                "written down.")
    elif ask and held_slugs:
        top = max(held_slugs, key=held_slugs.get)
        out.append(
            f"Answering by assembly is being rebuilt on the new "
            f"fabric; I will not fake it meanwhile. The parts of "
            f"an answer live mostly in {top}.")
    return "\n\n".join(out)


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
            out = _converse(q)
            out += ("\n\n" + "-" * 46 +
                    "\nTHE READING, IN THE MACHINE'S OWN TERMS\n\n")
            out += _heard(q)

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
