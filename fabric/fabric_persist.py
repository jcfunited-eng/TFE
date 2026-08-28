"""PERSISTENCE — the compute element that keeps the fabric running.

The door (fabric_ask) stays a pure function of floors + door code:
warmth, wrinkles, and wondering NEVER change an answer. The door
reads the floors fresh at every asking, so an edited floor is seen
at once. What persistence adds is a LIFE around that door:

  - askings served from an inbox directory, answers written to an
    answers directory — same three tiers, same white, the very same
    door code produces the text
  - warmth: floors used by answers warm; everything cools every
    beat (x0.999); floors colder than 0.02 are forgotten — real
    decay, leanness kept
  - wondering: in quiet beats it pre-walks one join between warm
    floors of DIFFERENT fields that share words — once each, ever
    (door-memory); when nothing warrants wondering it is QUIET.
    No invented work.
  - wrinkles: a pair of floors co-traveling three times is a worn
    path, recorded in the state as a fact of its life
  - checkpoint: readable state, written atomically every 30 beats
    and on an orderly stop; a hard kill loses at most the beats
    since the last checkpoint; a restart RESUMES the same life —
    continuity, not rebirth
  - ceiling: a state file past 64 KB is an error said out loud,
    and wondering halts until cooling shrinks it
"""
import os, sys, time, signal, hashlib, threading, uuid, json
from io import StringIO
from contextlib import redirect_stdout
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)
import fabric_ask as fa

LIFE = os.path.join(BASE, "life")
INBOX = os.path.join(LIFE, "inbox")
OUT = os.path.join(LIFE, "answers")
STATE = os.path.join(LIFE, "state.txt")
LOG = os.path.join(LIFE, "life.log")
CEIL = 64 * 1024
COOL = 0.999
FORGET = 0.02
WONDER_MIN_WARMTH = 0.5
CHECKPOINT_EVERY = 30
RELEARN_EVERY = 60
HEARTBEAT_EVERY = 120

STOP = False
def _stop(sig, frm):
    global STOP; STOP = True
signal.signal(signal.SIGTERM, _stop)
signal.signal(signal.SIGINT, _stop)

def fid(e):
    return hashlib.sha256(
        (e["field"] + "|" + e["essence"]).encode()).hexdigest()[:8]

def log(line):
    with open(LOG, "a") as f:
        f.write(line + "\n")

def load_state():
    st = dict(beats=0, served=0, warmth={}, co={}, wrinkles=set(),
              wondered=set())
    if not os.path.exists(STATE):
        return st, False
    for line in open(STATE):
        p = line.split()
        if not p: continue
        if p[0] == "BEATS": st["beats"] = int(p[1])
        elif p[0] == "SERVED": st["served"] = int(p[1])
        elif p[0] == "WARM": st["warmth"][p[1]] = float(p[2])
        elif p[0] == "CO": st["co"][p[1]] = int(p[2])
        elif p[0] == "WRINKLE": st["wrinkles"].add(p[1])
        elif p[0] == "WONDERED": st["wondered"].add(p[1])
    return st, True

def save_state(st):
    lines = [f"BEATS {st['beats']}", f"SERVED {st['served']}"]
    for k in sorted(st["warmth"]):
        lines.append(f"WARM {k} {st['warmth'][k]:.3f}")
    for k in sorted(st["co"]):
        lines.append(f"CO {k} {st['co'][k]}")
    for k in sorted(st["wrinkles"]):
        lines.append(f"WRINKLE {k}")
    for k in sorted(st["wondered"]):
        lines.append(f"WONDERED {k}")
    body = "\n".join(lines) + "\n"
    tmp = STATE + ".tmp"
    open(tmp, "w").write(body)
    os.replace(tmp, STATE)
    if len(body) > CEIL:
        log(f"CEILING ERROR: state {len(body)} bytes is past the "
            f"64 KB ceiling — wondering halts until cooling shrinks "
            f"it. Said out loud, not hidden.")
        return False
    return True

def pkey(a, b):
    return "x".join(sorted([a, b]))

def co_travel(st, a, b):
    k = pkey(a, b)
    st["co"][k] = st["co"].get(k, 0) + 1
    if st["co"][k] == 3 and k not in st["wrinkles"]:
        st["wrinkles"].add(k)
        return k
    return None

def serve_one(path, st, floors, wts, byid):
    q = open(path).read().strip()
    buf = StringIO()
    with redirect_stdout(buf):
        fa.ask(q)                    # the very door, unchanged
    txt = buf.getvalue()
    name = os.path.basename(path)
    with open(os.path.join(OUT, name), "w") as f:
        f.write(f"ASKING: {q}\n\n{txt}")
    os.remove(path)
    if "limit of how I read" in txt: tier = "could not read it"
    elif "Recording it as an open question" in txt: \
        tier = "no knowledge yet — recorded"
    elif "recorded as an open question" in txt: \
        tier = "open question, still unanswered"
    elif "different things" in txt: tier = "ambiguous words"
    elif "nearest knowledge" in txt: tier = "near misses shown"
    else: tier = "answered"
    # life bookkeeping on the cached floors (never changes the door)
    qs = fa.words(q)
    if qs:
        rel, direct, houses, good, rare, missing = fa.walk(qs, floors)
        if len(houses) <= 1:   # a split warms nothing — the asker
            used = [fid(e) for e in direct[:3]]       # hasn't said
            for sc, B, A, h in good[:3]:              # what they mean
                used += [fid(B), fid(A)]
                w = co_travel(st, fid(B), fid(A))
                if w: log(f"beat {st['beats']}: a path is worn — {w}")
            for i in used:
                st["warmth"][i] = st["warmth"].get(i, 0.0) + 1.0
            for e in rel:
                i = fid(e)
                if i not in used:
                    st["warmth"][i] = st["warmth"].get(i, 0.0) + 0.2
    st["served"] += 1
    log(f"beat {st['beats']}: answered ({tier}): {q}")

GRIND_EVERY = 240
EXERCISE_EVERY = 45
CANDIDATES = os.path.join(LIFE, "possible_candidates.md")
BRIDGES = os.path.join(LIFE, "missing_bridges.md")
_ground = set()
_exercised = set()
_bridge_misses = {}
PROPOSED = os.path.join(LIFE, "proposed_new_areas.md")

def _grow(path, text, what):
    if os.path.exists(path) and os.path.getsize(path) > CEIL:
        log(f"the {what} record reached its ceiling — growth "
            f"paused there until it is read and cleared")
        return
    with open(path, "a") as f: f.write(text)

def exercise_knowledge(st, floors):
    """The fabric draws its own ribbons: take one entry in turn,
    follow one connection its thread line promises, ask itself the
    bridge question, and record what comes — a candidate
    possibility (growing the possible) or a missing bridge
    (growing the map of its own ignorance)."""
    import assembler
    e = floors[(st["beats"] // EXERCISE_EVERY) % len(floors)]
    th = (e.get("thread") or "").lower()
    if not th: return
    target = None
    for f2 in floors:
        fld = f2["field"]
        if fld != e["field"] and fld.split()[-1] in th:
            target = fld; break
    if not target: return
    key = (e["essence"][:40], target)
    if key in _exercised: return
    _exercised.add(key)
    df = {}
    for x2 in floors:
        for x in fa.words(x2["essence"] + " " + x2["cannot"] + " "
                          + x2["ask"]):
            df[x] = df.get(x, 0) + 1
    seed = sorted(fa.words(e["essence"]),
                  key=lambda x: df.get(x, 99))[:2]
    q = f"{' '.join(seed)} {target}"
    lanes = assembler.play(q, floors, df)
    toys = [ts for _, _, t3 in lanes for ts in t3]
    if toys:
        s, a, b = toys[0]
        _grow(CANDIDATES,
              f"
CANDIDATE (self-asked, un-aimed, ungraded) — "
              f"from the thread of "{e['essence'][:50]}" toward "
              f"{target}:
  maybe: {a['essence'][:90]}
  with: "
              f"{b['essence'][:90]}
", "possible")
        log(f"beat {st['beats']}: exercised its knowledge — a "
            f"candidate possibility recorded "
            f"({e['field']} toward {target})")
    else:
        _grow(BRIDGES,
              f"
MISSING BRIDGE — the entry "{e['essence'][:60]}""
              f" promises a thread toward {target}, but exercising "
              f"it found nothing that connects. The bridge is "
              f"knowledge not yet written.
", "missing-bridge")
        log(f"beat {st['beats']}: exercised its knowledge — found "
            f"a missing bridge ({e['field']} toward {target})")
        _bridge_misses[target] = _bridge_misses.get(target, 0) + 1
        if _bridge_misses[target] == 2:
            _grow(PROPOSED,
                  f"\nPROPOSED NEW AREA — bridges toward "
                  f"\"{target}\" keep failing from different "
                  f"directions. The knowledge keeps pointing at a "
                  f"subject not yet written. A new area may need "
                  f"to exist.\n", "proposed-area")
            log(f"beat {st['beats']}: proposed a NEW AREA of "
                f"knowledge — {target} — its own records keep "
                f"pointing there")
def grind_open_question(st, floors):
    """In quiet time, work one recorded open question: try to
    assemble an answer from scattered pieces. Log only what
    scores well and was not shown before."""
    import assembler
    import re as _re
    wtxt = open(fa.WHITE).read() if os.path.exists(fa.WHITE) else ""
    qs = _re.findall(r"ENTRY: ([^\n]+)\n(?:[^\n]|\n(?!\n))*?"
                     r"STATUS: STANDING", wtxt)
    if not qs: return
    q = qs[st["beats"] // GRIND_EVERY % len(qs)]
    df = {}
    for e in floors:
        for x in fa.words(e["essence"] + " " + e["cannot"] + " "
                          + e["ask"]):
            df[x] = df.get(x, 0) + 1
    for s, e1, e2, g in assembler.run(q, floors, df):
        k = (q, e1["essence"][:40], e2["essence"][:40])
        if s >= 8 and k not in _ground:
            _ground.add(k)
            log(f"beat {st['beats']}: working the open question "
                f"'{q}' — a possible assembly (score {s}): "
                f"{e1['essence'][:70]} | {e2['essence'][:70]}")

def wonder_one(st, wts, byid):
    warm = sorted([i for i, v in st["warmth"].items()
                   if v >= WONDER_MIN_WARMTH and i in byid],
                  key=lambda i: -st["warmth"][i])
    for a in warm:
        for b in warm:
            if a >= b: continue
            k = pkey(a, b)
            if k in st["wondered"]: continue
            if byid[a]["field"] == byid[b]["field"]: continue
            hinge = wts[a] & wts[b]
            if len(hinge) < 2: continue
            st["wondered"].add(k)
            w = co_travel(st, a, b)
            hs = " ".join(sorted(hinge)[:6])
            log(f"beat {st['beats']}: tried a connection — "
                f"{byid[a]['field']} and {byid[b]['field']} "
                f"(shared words: {hs})")
            if w: log(f"beat {st['beats']}: a path is worn — {w}")
            if len(hinge) >= 3:
                log(f"beat {st['beats']}: a connection worth a "
                    f"look — {byid[a]['essence'][:60]} | "
                    f"{byid[b]['essence'][:60]}")
            return True
    return False

PORT = 8765
PAGE = """<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>The Compute Fabric</title><style>
:root{--cloth:#faf8f3;--ink:#221f1b;--thread:#a33b2e;
--dim:#6f6a62;--line:#ddd8cf;--card:#fffdf9}
*{box-sizing:border-box}
body{font-family:Georgia,'Times New Roman',serif;max-width:40em;
margin:0 auto;padding:2.2em 1em 3em;background:var(--cloth);
color:var(--ink);line-height:1.55}
h1{font-size:1.45em;font-weight:normal;margin:0;
border-bottom:2px solid var(--thread);display:inline-block;
padding-bottom:.15em}
.tag{color:var(--dim);margin:.7em 0 1.6em;font-size:.95em}
.askrow{display:flex;gap:.6em}
input{flex:1;font-size:1.05em;padding:.6em .7em;
border:1px solid var(--line);border-radius:2px;
background:var(--card);font-family:inherit;color:var(--ink)}
input:focus{outline:2px solid var(--thread);outline-offset:1px}
button{font-size:1em;padding:.55em 1.5em;font-family:inherit;
background:var(--thread);color:var(--cloth);border:none;
border-radius:2px;cursor:pointer}
button:hover{background:#8d3226}
button:focus-visible{outline:2px solid var(--ink)}
pre{white-space:pre-wrap;background:var(--card);
border:1px solid var(--line);border-left:3px solid var(--thread);
padding:1em 1.1em;font-size:.92em;margin:1.2em 0;
overflow-x:auto;font-family:inherit}
.pulse{display:flex;flex-wrap:wrap;gap:1.4em;margin:1.6em 0 .4em;
padding-top:1em;border-top:1px solid var(--line)}
.pulse div{min-width:4.2em}
.pulse b{display:block;font-size:1.15em;font-weight:normal;
font-variant-numeric:tabular-nums}
.pulse span{font-size:.68em;letter-spacing:.08em;
text-transform:uppercase;color:var(--dim)}
.life{color:var(--dim);font-size:.85em;font-style:italic;
margin-top:1em}
a{color:var(--thread)}
footer{margin-top:2em;font-size:.85em;color:var(--dim)}
</style></head><body>
<h1>The Compute Fabric</h1>
<p class="tag">Ask it anything. It answers from what it knows,
shows near misses honestly, and keeps what it cannot answer as
open questions. It never pretends.</p>
<div class="askrow">
<input id="q" placeholder="why does…" autofocus>
<button onclick="go()">ask</button>
</div>
<pre id="a">—</pre>
<div class="pulse" id="pulse"></div>
<p class="life" id="life"></p>
<footer><a href="/white">the open questions</a> — everything no
knowledge yet reaches, kept until the knowledge arrives.</footer>
<script>
async function go(){
 const q=document.getElementById('q').value.trim();
 if(!q)return;
 document.getElementById('a').textContent='walking the floors…';
 const r=await fetch('/ask',{method:'POST',body:q});
 document.getElementById('a').textContent=await r.text();
 pulse();}
async function pulse(){
 try{
  const p=await (await fetch('/pulse')).json();
  const row=[['heartbeats',p.beats],
   ['questions answered',p.served],
   ['knowledge entries',p.floors],['in recent use',p.warm],
   ['worn paths',p.wrinkles],['connections tried',p.wondered],
   ['open questions',p.white_standing],
   ['answered later',p.white_drained]];
  document.getElementById('pulse').innerHTML=row.map(
   ([k,v])=>`<div><b>${v}</b><span>${k}</span></div>`).join('');
  document.getElementById('life').textContent=p.life;
 }catch(e){
  document.getElementById('life').textContent=
   'the fabric is not breathing — its process is down';}}
document.getElementById('q').addEventListener('keydown',
 e=>{if(e.key==='Enter')go()});
pulse();setInterval(pulse,8000);
</script></body></html>"""

class Door(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def _send(self, body, ctype="text/plain; charset=utf-8"):
        b = body.encode()
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)
    def do_GET(self):
        if self.path == "/":
            self._send(PAGE, "text/html; charset=utf-8")
        elif self.path == "/life":
            tail = open(LOG).read().splitlines()[-3:] \
                if os.path.exists(LOG) else []
            self._send(" · ".join(tail))
        elif self.path == "/white":
            self._send(open(fa.WHITE).read()
                       if os.path.exists(fa.WHITE) else "(empty)")
        elif self.path == "/pulse":
            p = dict(beats=0, served=0, warm=0, wrinkles=0,
                     wondered=0)
            if os.path.exists(STATE):
                for line in open(STATE):
                    w = line.split()
                    if not w: continue
                    if w[0] == "BEATS": p["beats"] = int(w[1])
                    elif w[0] == "SERVED": p["served"] = int(w[1])
                    elif w[0] == "WARM": p["warm"] += 1
                    elif w[0] == "WRINKLE": p["wrinkles"] += 1
                    elif w[0] == "WONDERED": p["wondered"] += 1
            p["floors"] = len(fa.load())
            wt = open(fa.WHITE).read() \
                if os.path.exists(fa.WHITE) else ""
            p["white_standing"] = wt.count("STATUS: STANDING")
            p["white_drained"] = (wt.count("STATUS: DRAINED") +
                                  wt.count("STATUS: ANSWERED"))
            p["life"] = " · ".join(
                open(LOG).read().splitlines()[-2:]
                if os.path.exists(LOG) else [])
            self._send(json.dumps(p),
                       "application/json; charset=utf-8")
        else:
            self._send("no such door")
    def do_POST(self):
        if self.path != "/ask":
            self._send("no such door"); return
        n = int(self.headers.get("Content-Length", 0))
        q = self.rfile.read(n).decode().strip()[:300]
        if not q:
            self._send("(empty asking)"); return
        name = "web_" + uuid.uuid4().hex[:10] + ".txt"
        with open(os.path.join(INBOX, name + ".tmp"), "w") as f:
            f.write(q)
        os.replace(os.path.join(INBOX, name + ".tmp"),
                   os.path.join(INBOX, name))
        ans = os.path.join(OUT, name)
        for _ in range(100):            # the beat serves it
            if os.path.exists(ans):
                self._send(open(ans).read()); return
            time.sleep(0.25)
        self._send("(the fabric did not come back in time — "
                   "its life log will say why)")

def serve_http():
    srv = ThreadingHTTPServer(("0.0.0.0", PORT), Door)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv

def main():
    os.makedirs(INBOX, exist_ok=True)
    os.makedirs(OUT, exist_ok=True)
    st, resumed = load_state()
    serve_http()
    floors = fa.load()
    fp = fa.fingerprint()
    wts = {fid(e): fa.words(e["essence"] + " " + e["cannot"] + " "
                            + e["ask"]) for e in floors}
    byid = {fid(e): e for e in floors}
    over_ceiling = False
    log(f"beat {st['beats']}: " +
        (f"RESUMED — same life continues ({st['served']} "
         f"questions answered so far)" if resumed else
         "FIRST BREATH — new life, knowledge learned"))
    quiet = 0
    while not STOP:
        st["beats"] += 1
        pending = sorted(os.path.join(INBOX, n)
                         for n in os.listdir(INBOX)
                         if n.endswith(".txt"))
        acted = False
        for p in pending:
            serve_one(p, st, floors, wts, byid)
            acted = True
        if not acted and not over_ceiling:
            acted = wonder_one(st, wts, byid)
            if not acted and st["beats"] % GRIND_EVERY == 0:
                grind_open_question(st, floors)
            elif not acted and st["beats"] % EXERCISE_EVERY == 0:
                exercise_knowledge(st, floors)
        if not acted:
            quiet += 1
        elif quiet:
            quiet = 0
        for i in list(st["warmth"]):
            st["warmth"][i] *= COOL
            if st["warmth"][i] < FORGET:
                del st["warmth"][i]
        if st["beats"] % RELEARN_EVERY == 0:
            nf = fa.fingerprint()
            if nf != fp:
                fp = nf; floors = fa.load()
                wts = {fid(e): fa.words(e["essence"] + " " +
                       e["cannot"] + " " + e["ask"]) for e in floors}
                byid = {fid(e): e for e in floors}
                log(f"beat {st['beats']}: the knowledge changed — "
                    f"relearned it")
        if st["beats"] % CHECKPOINT_EVERY == 0:
            over_ceiling = not save_state(st)
        if st["beats"] % HEARTBEAT_EVERY == 0:
            log(f"beat {st['beats']}: alive — "
                f"{st['served']} questions answered, "
                f"{len(st['warmth'])} entries in recent use, "
                f"{len(st['wondered'])} connections tried, "
                f"quiet {quiet}")
        time.sleep(1)
    save_state(st)
    log(f"beat {st['beats']}: orderly stop — checkpoint saved, "
        f"life will resume from here")

if __name__ == "__main__":
    main()
