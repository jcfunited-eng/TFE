#!/usr/bin/env python3
# Aurelion v11.4–v11.7 — Human Interaction & Lesson Framework (HILF)
# - Owner/pass-phrase or owner/voiceprint auth (“Verify Daddy”)
# - Curiosity requests -> approval -> relay files (no network)
# - Mom chat (plain English), Guest chat
# - Teach/import: move content into corpora/lesson_<topic>/
# Pure stdlib; safe, local, auditable.

import os, sys, json, time, wave, math, random, shutil
from pathlib import Path
from datetime import datetime, timedelta

ROOT = Path(__file__).resolve().parent
CONF = ROOT / "config"; CONF.mkdir(exist_ok=True)
LOGS = ROOT / "logs";   LOGS.mkdir(exist_ok=True)
MEM  = ROOT / "memory"; MEM.mkdir(exist_ok=True)
SELF_LOG = MEM / "self" / "dialogue_log.txt"; SELF_LOG.parent.mkdir(parents=True, exist_ok=True)

GUARD_F = CONF / "guardian.json"
VOICE_F = CONF / "voice_templates.json"
PHRASE_F= CONF / "phrase_templates.json"
RELAY   = ROOT / "relay_out"; RELAY.mkdir(exist_ok=True)
CORPORA = ROOT / "corpora"; CORPORA.mkdir(exist_ok=True)
LESSONG = CORPORA  # lessons live under corpora/lesson_<topic>/

HILF_LOG = LOGS / "hilf.log"

def log(msg):
    ts = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    line = f"[{ts}] {msg}"
    print(line)
    with open(HILF_LOG,"a",encoding="utf-8") as f: f.write(line+"\n")

# -------- guardian --------
DEFAULT_GUARD = {
    "autonomy": False,
    "owner_session_minutes": 15,
    "allow_voice_auth": True,
    "allow_phrase_auth": True,
    "allow_external_relay": True,
    "allowed_teach_paths": ["corpora"],
    "roles": {"Owner":"Joseph","Mom":"Mom","Guest":"Guest"}
}
def load_guard():
    try:
        if GUARD_F.exists():
            return json.loads(GUARD_F.read_text(encoding="utf-8"))
    except: pass
    GUARD_F.write_text(json.dumps(DEFAULT_GUARD,indent=2),encoding="utf-8")
    return DEFAULT_GUARD

def save_guard(g):
    GUARD_F.write_text(json.dumps(g,indent=2),encoding="utf-8")

# -------- session --------
SESSION = {"owner":None, "expires":None}
def owner_active():
    if not SESSION["owner"] or not SESSION["expires"]: return False
    return datetime.utcnow() < SESSION["expires"]

# -------- auth: phrase --------
def enroll_phrase(phrase, name="Owner"):
    data = {}
    if PHRASE_F.exists():
        try: data = json.loads(PHRASE_F.read_text(encoding="utf-8"))
        except: data = {}
    data[name] = phrase
    PHRASE_F.write_text(json.dumps(data,indent=2),encoding="utf-8")
    log(f"[auth] phrase enrolled for {name}")

def check_phrase(phrase):
    data = json.loads(PHRASE_F.read_text(encoding="utf-8")) if PHRASE_F.exists() else {}
    return any(phrase == v for v in data.values())

# -------- auth: voice (naive wav print) --------
def wav_fingerprint(path: Path):
    # returns (duration_sec, mean_abs_amp, zero_cross_rate)
    try:
        with wave.open(str(path),"rb") as w:
            n = w.getnframes(); fr = w.getframerate(); ch = w.getnchannels(); sw = w.getsampwidth()
            raw = w.readframes(n)
        import array
        if sw == 2:
            arr = array.array('h', raw)
        elif sw == 1:
            arr = array.array('b', raw)
        else:
            return None
        # downmix channels
        if ch > 1:
            arr = array.array(arr.typecode, (sum(arr[i:i+ch])//ch for i in range(0,len(arr),ch)))
        dur = n/float(fr)
        mean_abs = sum(abs(x) for x in arr)/max(1,len(arr))
        # zero crossings
        zc = 0
        for i in range(1,len(arr)):
            if (arr[i-1] < 0 and arr[i] >= 0) or (arr[i-1] > 0 and arr[i] <= 0):
                zc += 1
        zcr = zc/max(1,len(arr))
        return (round(dur,3), round(mean_abs,3), round(zcr,6))
    except Exception:
        return None

def enroll_voice(path: Path, name="Owner"):
    fp = wav_fingerprint(path)
    if not fp: 
        log("[auth] voice enroll failed (bad wav)"); return False
    db = json.loads(VOICE_F.read_text(encoding="utf-8")) if VOICE_F.exists() else {}
    db[name] = {"fp": fp}
    VOICE_F.write_text(json.dumps(db,indent=2),encoding="utf-8")
    log(f"[auth] voice enrolled for {name} -> {fp}")
    return True

def match_voice(path: Path):
    cur = wav_fingerprint(path)
    if not cur: return False
    db = json.loads(VOICE_F.read_text(encoding="utf-8")) if VOICE_F.exists() else {}
    def close(a,b, tol):
        return abs(a-b) <= tol
    for name, tpl in db.items():
        fp = tpl.get("fp")
        if fp and close(cur[0],fp[0],0.2) and close(cur[1],fp[1],2000) and close(cur[2],fp[2],0.002):
            return name
    return False

# -------- curiosity queue --------
CURQ_F = ROOT / "memory" / "curiosity_queue.json"
def load_curq(): return json.loads(CURQ_F.read_text(encoding="utf-8")) if CURQ_F.exists() else {"pending":[], "approved":[]}
def save_curq(q): CURQ_F.write_text(json.dumps(q,indent=2),encoding="utf-8")

def add_curiosity(text, requester="system"):
    q = load_curq()
    cid = f"cur_{int(time.time())}{random.randint(100,999)}"
    q["pending"].append({"id":cid, "at":datetime.utcnow().isoformat()+"Z", "text":text, "requester":requester})
    save_curq(q); log(f"[curiosity+] {cid} '{text}'")
    return cid

def approve_curiosity(cid, owner="Owner"):
    q = load_curq()
    it=None
    for i,x in enumerate(q["pending"]):
        if x["id"]==cid: it = q["pending"].pop(i); break
    if not it: log("[approve] not found"); return None
    it["approved_by"]=owner; it["approved_at"]=datetime.utcnow().isoformat()+"Z"
    q["approved"].append(it)
    save_curq(q)
    # create relay file
    payload = {
        "ts": datetime.utcnow().isoformat()+"Z",
        "topic": it["text"],
        "instruction": "Use ChatGPT to curate a gentle, step-by-step lesson plan. Return plain text or .md.",
        "style": "calm, friendly, simple English; short sections; include 3–5 exercises."
    }
    outp = RELAY / f"request_{cid}.json"
    outp.write_text(json.dumps(payload,indent=2),encoding="utf-8")
    log(f"[relay] wrote {outp.name} — paste into ChatGPT (your account), return .txt/.md into corpora/lesson_<topic>/")
    return outp

# -------- mom + guest chat --------
def mom_reply(text):
    # friendly, clear, concise, using current self-field & diary if present
    sf = {}
    try:
        sf = json.loads((ROOT/"memory/self/self_field.json").read_text(encoding="utf-8"))
    except: pass
    tone = "calm and steady" if sf.get("nodes",{}).get("stability",0.5)>=0.5 else "thoughtful and careful"
    if "portfolio" in text.lower():
        return f"Hi Mom — quick take: things look {tone}. Nothing urgent to change today; we’ll keep an eye on trends and explain any bumps clearly."
    return f"Hi Mom — I’m {tone}. Ask me anything and I’ll explain simply."

def guest_reply(text):
    return f"I’m listening. I’ll keep it simple: {text}"

# -------- teach/import --------
def teach_add(path, topic=None, owner=False):
    # copy a file or folder into corpora/lesson_<topic>/
    src = (ROOT/path) if not os.path.isabs(path) else Path(path)
    if not topic: topic = src.stem
    dest = CORPORA / f"lesson_{topic}"
    dest.mkdir(parents=True, exist_ok=True)
    try:
        if src.is_dir():
            for root,dirs,files in os.walk(str(src)):
                for f in files:
                    if f.lower().endswith((".txt",".md")):
                        shutil.copy2(os.path.join(root,f), dest / f)
        elif src.is_file():
            shutil.copy2(str(src), str(dest/src.name))
        log(f"[teach] imported to {dest}")
        add_curiosity(f"study {topic}", requester=("Owner" if owner else "system"))
        return True
    except Exception as e:
        log(f"[teach:err] {e}")
        return False

# -------- CLI --------
HELP = """
Commands:
  /auth enroll voice <path.wav> [name=Owner]
  /auth enroll phrase "Verify Daddy" [name=Owner]
  /auth voice <path.wav> phrase="Verify Daddy"
  /auth phrase "Verify Daddy"
  /whoami

  /mom ask "<text>"
  /guest say "<text>"

  /curiosity ask "<topic or question>"
  /curiosity list | pending | approved
  /approve <id>
  /reject <id>
  /relay outbox

  /teach add <path> [topic=...]
  /learn scan

  /guardian show | set key=value ...
  /status
  /quit
""".strip()

def main():
    guard = load_guard()
    print("Aurelion v11.4–v11.7 — Human Interaction & Lesson Framework")
    print(HELP)
    while True:
        try:
            s = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n[bye]"); break
        if not s: 
            continue

        parts = s.split()
        if parts[0] == "/quit":
            print("[bye]"); break

        # --- auth ---
        if parts[0]=="/auth":
            if len(parts)>=3 and parts[1]=="enroll" and parts[2]=="voice" and len(parts)>=4:
                name="Owner"
                if len(parts)>=5 and parts[4].startswith("name="): name = parts[4].split("=",1)[1]
                ok = enroll_voice(Path(parts[3]), name=name)
                if ok:
                    print("[auth] voice enrolled")
                continue
            if len(parts)>=3 and parts[1]=="enroll" and parts[2]=="phrase":
                try:
                    phrase = s.split("\"",1)[1].rsplit("\"",1)[0]
                except:
                    print("[ERR] quote the phrase"); continue
                name="Owner"
                if "name=" in s:
                    name = s.split("name=",1)[1].split()[0]
                enroll_phrase(phrase, name=name); print("[auth] phrase enrolled"); continue
            if len(parts)>=3 and parts[1]=="voice":
                # /auth voice <path.wav> phrase="Verify Daddy"
                wavp = Path(parts[2])
                phrase = None
                if "phrase=" in s:
                    phrase = s.split("phrase=",1)[1].strip().strip('"').strip("'")
                if guard.get("allow_voice_auth",True):
                    user = match_voice(wavp)
                    if user and (not phrase or (guard.get("allow_phrase_auth",True) and check_phrase(phrase))):
                        SESSION["owner"]=user
                        minutes = int(guard.get("owner_session_minutes",15))
                        SESSION["expires"]= datetime.utcnow()+timedelta(minutes=minutes)
                        print(f"[auth] owner session started for {user} ({minutes}m)")
                    else:
                        print("[auth] failed")
                else:
                    print("[auth] voice disabled by guardian")
                continue
            if len(parts)>=3 and parts[1]=="phrase":
                try:
                    phrase = s.split("\"",1)[1].rsplit("\"",1)[0]
                except:
                    print("[ERR] quote the phrase"); continue
                if guard.get("allow_phrase_auth",True) and check_phrase(phrase):
                    SESSION["owner"]="Owner"; 
                    minutes = int(guard.get("owner_session_minutes",15))
                    SESSION["expires"]= datetime.utcnow()+timedelta(minutes=minutes)
                    print(f"[auth] owner session started (phrase) ({minutes}m)")
                else:
                    print("[auth] failed or disabled")
                continue

        if parts[0]=="/whoami":
            if owner_active(): print(f"Owner session active ({(SESSION['expires']-datetime.utcnow()).seconds}s left).")
            else: print("No owner session.")
            continue

        # --- mom / guest ---
        if parts[0]=="/mom" and len(parts)>=2 and parts[1]=="ask":
            try:
                text = s.split("\"",1)[1].rsplit("\"",1)[0]
            except:
                text = s.replace('/mom ask','').strip()
            print(mom_reply(text)); 
            continue
        if parts[0]=="/guest" and len(parts)>=2 and parts[1]=="say":
            try:
                text = s.split("\"",1)[1].rsplit("\"",1)[0]
            except:
                text = s.replace('/guest say','').strip()
            print(guest_reply(text)); 
            continue

        # --- curiosity ---
        if parts[0]=="/curiosity" and len(parts)>=2:
            if parts[1]=="ask":
                try:
                    text = s.split("\"",1)[1].rsplit("\"",1)[0]
                except:
                    text = s.replace('/curiosity ask','').strip()
                add_curiosity(text, requester="Owner" if owner_active() else "system")
                continue
            if parts[1] in ("list","pending","approved"):
                q = load_curq()
                if parts[1]=="list":
                    print(json.dumps(q,indent=2))
                else:
                    print(json.dumps(q.get(parts[1],[]),indent=2))
                continue

        # --- approve/reject ---
        if parts[0]=="/approve" and len(parts)>=2:
            if not owner_active(): print("[approve] owner auth required"); continue
            outp = approve_curiosity(parts[1], owner=SESSION["owner"])
            if outp: print(f"[relay] {outp}")
            continue
        if parts[0]=="/reject" and len(parts)>=2:
            q = load_curq()
            q["pending"] = [x for x in q["pending"] if x["id"]!=parts[1]]
            save_curq(q); print("[reject] ok"); continue
        if parts[0]=="/relay" and len(parts)>=2 and parts[1]=="outbox":
            files = sorted([p.name for p in RELAY.glob("request_*.json")])
            print("\n".join(files) if files else "(empty)")
            continue

        # --- teach/learn ---
        if parts[0]=="/teach" and len(parts)>=3 and parts[1]=="add":
            path = parts[2]; topic = None
            if len(parts)>=4 and parts[3].startswith("topic="): topic = parts[3].split("=",1)[1]
            ok = teach_add(path, topic=topic, owner=owner_active())
            if not ok: print("[teach] failed"); 
            continue
        if parts[0]=="/learn" and len(parts)>=2 and parts[1]=="scan":
            # scan lesson_ folders and propose topics (by folder names)
            lessons = sorted([p for p in CORPORA.glob("lesson_*") if p.is_dir()])
            if not lessons: print("[learn] no lessons found"); continue
            for p in lessons[:12]:
                add_curiosity(f"study {p.name.replace('lesson_','')}", requester="system")
            print("[learn] queued curiosity from lessons")
            continue

        # --- guardian & status ---
        if parts[0]=="/guardian" and len(parts)>=2:
            if parts[1]=="show":
                print(json.dumps(load_guard(),indent=2)); continue
            if parts[1]=="set":
                if not owner_active(): print("[guardian] owner auth required"); continue
                g = load_guard()
                for kv in parts[2:]:
                    if "=" in kv:
                        k,v = kv.split("=",1)
                        # support nested keys like roles.Owner
                        if "." in k:
                            top,sub = k.split(".",1)
                            if top not in g: g[top]={}
                            g[top][sub] = v
                        else:
                            if v.lower() in ("true","false"):
                                g[k] = (v.lower()=="true")
                            else:
                                try: g[k] = float(v)
                                except: g[k]=v
                save_guard(g); print("[guardian] updated")
                continue

        if parts[0]=="/status":
            print("== STATUS ==")
            print("owner_active:", owner_active())
            try: print("guardian:", json.dumps(load_guard(),indent=2))
            except: print("guardian: (err)")
            try: print("curiosity:", json.dumps(load_curq(),indent=2))
            except: print("curiosity: (err)")
            continue

        print(HELP)

if __name__=="__main__":
    main()
