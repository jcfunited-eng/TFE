#!/usr/bin/env python3
# Aurelion v10.12 — Narrative Continuity Field (NCF)
# Reads latest diary + CK-ESN, computes continuity vector, logs it, and emits bounded feedback for RDF.

import os, re, json
from pathlib import Path
from datetime import datetime, timezone

APP = "Aurelion v10.12 — Narrative Continuity Field (NCF)"

ROOT = Path(__file__).resolve().parent
REF_DIR = ROOT / "memory" / "reflective"
DIARY_DIR = REF_DIR
NCF_STATE = REF_DIR / "ncf_state.json"
NCF_LOG = REF_DIR / "ncf_log.jsonl"
NCF_FEEDBACK = REF_DIR / "ncf_feedback.json"
CK_STATE = ROOT / "memory" / "morphogen" / "continuity" / "ck_state.json"

# ---------- utils ----------
def now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

def read_json(p, default=None):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except Exception:
        return default

def write_json_atomic(path: Path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, path)

def append_log(obj: dict):
    NCF_LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(NCF_LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")

# ---------- diary parsing ----------
STOP = set("""
the a an and or of to in on for with as by at from up down into over under about between within without
i you he she we they it is are was were be been being have has had do did doing this that these those
""".split())

POS_WORDS = set("calm hope gentle steady bright clear align coherence balance growth learn prudent caring fairness".split())
NEG_WORDS = set("fear stress strain chaos anxious confused conflicted restless stuck bias".split())

def latest_diary_path():
    files = sorted(DIARY_DIR.glob("diary_*.txt"))
    return files[-1] if files else None

def tokenize(text: str):
    toks = re.findall(r"[A-Za-z][A-Za-z\-']+", text.lower())
    return [t for t in toks if t not in STOP and len(t) >= 3]

def extract_keywords(lines):
    # naive frequency → top keywords
    freq = {}
    for ln in lines:
        for t in tokenize(ln):
            freq[t] = freq.get(t, 0) + 1
    top = sorted(freq.items(), key=lambda x: x[1], reverse=True)
    return [w for w,_ in top[:20]]

def diary_summary():
    p = latest_diary_path()
    if not p:
        return None, None, []
    text = p.read_text(encoding="utf-8", errors="ignore")
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    # header line is first; date is in it, e.g., "2025-11-12 — Reflective Diary"
    date_line = lines[0] if lines else ""
    date = None
    m = re.search(r"(\d{4}-\d{2}-\d{2})", date_line)
    if m: date = m.group(1)
    body = lines[1:] if len(lines) > 1 else []
    return date, text, body

def simple_sentiment(tokens):
    if not tokens: return "neutral"
    pos = sum(1 for t in tokens if t in POS_WORDS)
    neg = sum(1 for t in tokens if t in NEG_WORDS)
    if pos > neg: return "positive"
    if neg > pos: return "negative"
    return "neutral"

def jaccard(a: set, b: set):
    if not a and not b: return 1.0
    return len(a & b) / max(1, len(a | b))

# ---------- core NCF update ----------
def ncf_update():
    # read diary
    date, full_text, body = diary_summary()
    if full_text is None:
        print("[ncf] no diary found")
        return None

    # tokens & sentiment
    tokens = tokenize(" ".join(body))
    keywords = extract_keywords(body)
    sentiment = simple_sentiment(tokens)

    # read CK-ESN
    ck = read_json(CK_STATE, {})
    v = ck.get("vector", {})
    energy_trend_raw = v.get("energy_trend", 0.0)
    # map slope to label
    if energy_trend_raw > 0.01: energy_trend = "up"
    elif energy_trend_raw < -0.01: energy_trend = "down"
    else: energy_trend = "steady"

    # compute coherence vs last NCF (keywords overlap + stability proximity)
    prev = read_json(NCF_STATE, {})
    prev_kw = set(prev.get("keywords", []))
    jac = jaccard(set(keywords), prev_kw)
    stability_now = float(v.get("stability_score", 0.5) or 0.5)
    stability_prev = float(prev.get("ck_stability", stability_now))
    stab_closeness = max(0.0, 1.0 - abs(stability_now - stability_prev))
    coherence = round(0.6 * jac + 0.4 * stab_closeness, 3)

    # bounded feedback suggestion for RDF
    delta_energy = 0.0
    delta_overlap = 0.0
    hint = "balanced"

    if sentiment == "negative" or coherence < 0.4:
        delta_energy = -0.05  # calm down
        hint = "calm"
    elif sentiment == "neutral" and coherence > 0.8:
        delta_overlap = +0.03  # broaden
        hint = "explore"
    elif sentiment == "positive" and energy_trend == "down":
        delta_energy = +0.04  # small lift
        hint = "energize"

    # build state
    state = {
        "ts": now_iso(),
        "date": date or "unknown",
        "sentiment": sentiment,
        "energy_trend": energy_trend,
        "coherence": coherence,
        "note": hint,
        "keywords": keywords,
        "ck_stability": stability_now
    }
    write_json_atomic(NCF_STATE, state)
    append_log({"ts": state["ts"], "sentiment": sentiment, "coherence": coherence, "note": hint})

    # write feedback
    fb = {"delta_energy": round(delta_energy, 3), "delta_overlap": round(delta_overlap, 3), "hint": hint}
    write_json_atomic(NCF_FEEDBACK, fb)

    print("[ncf] updated")
    print(f"  sentiment={sentiment}  energy={energy_trend}  coherence={coherence}")
    print(f"  feedback: {fb}")
    return state

# ---------- CLI ----------
def print_help():
    print(APP)
    print("Commands:")
    print("  /ncf update")
    print("  /ncf state")
    print("  /ncf mom")
    print("  /ncf export <path.json>")
    print("  /quit")

def main():
    print_help()
    while True:
        try:
            cmd = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n[quit]")
            break
        if not cmd: 
            continue

        parts = cmd.split()
        if parts[0] == "/quit":
            break
        elif parts[0] == "/ncf" and len(parts) >= 2:
            sub = parts[1].lower()
            if sub == "update":
                ncf_update()
            elif sub == "state":
                s = read_json(NCF_STATE, {})
                if not s: print("[ncf] no state yet"); continue
                print(json.dumps(s, indent=2))
            elif sub == "mom":
                s = read_json(NCF_STATE, {})
                if not s:
                    print("(mom) no NCF state yet")
                else:
                    print(f"(mom) coherence={s.get('coherence','n/a')} | sentiment={s.get('sentiment','n/a')} | energy={s.get('energy_trend','n/a')} | note={s.get('note','n/a')}")
            elif sub == "export" and len(parts) == 3:
                target = Path(parts[2])
                s = read_json(NCF_STATE, {})
                if not s: print("[ncf] no state to export"); continue
                write_json_atomic(target, s)
                print(f"[export] wrote {target.resolve()}")
            else:
                print_help()
        else:
            print_help()

if __name__ == "__main__":
    main()
