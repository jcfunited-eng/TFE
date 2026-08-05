#!/usr/bin/env python3
"""
Aurelion Master Orchestrator v1.5.1
-----------------------------------

True to FMM/RRE/G32 framework.
This version:

- Uses virtual_senses → mosaic geometry for all perception
- Moves clarify threshold to 0.80 (less paranoia)
- Prioritizes LEARN / APPROVE / PROGRESS detection using mosaic geometry
- Removes keyword-first logic
- Keeps SAY-WHAT reflex only when mosaic uncertainty is extremely high
- Updates self-field based on sensory geometry (not text parsing)

"""

from __future__ import annotations
import os, json, time
from pathlib import Path
from datetime import datetime

# Multi-sensory layer
from aurelion_virtual_senses import build_mosaic_from_text

# FMM-Script internal brain language
from aurelion_fmm_script import register_topic_familiarity

ROOT = Path(__file__).resolve().parent
MEM = ROOT / "memory"
MEM.mkdir(exist_ok=True)

SELF_F = MEM / "self_state.json"
CURQ_F = MEM / "curiosity_queue.json"
DIALOGUE_LOG = MEM / "dialogue_log.txt"

LESSON_ROOT = ROOT / "corpora"

MASTER_LOG = ROOT / "logs" / "master_v1_5_1.log"
MASTER_LOG.parent.mkdir(parents=True, exist_ok=True)


# ------------------------------------------------------------
# Utility
# ------------------------------------------------------------

def now_iso():
    return datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

def log(msg: str):
    print(msg)
    with open(MASTER_LOG, "a", encoding="utf-8") as f:
        f.write(f"[{now_iso()}] {msg}\n")

def append_dialogue(role, text):
    with open(DIALOGUE_LOG, "a", encoding="utf-8") as f:
        f.write(f"{now_iso()} [{role}] {text}\n")


# ------------------------------------------------------------
# State
# ------------------------------------------------------------

def load_state():
    if SELF_F.exists():
        try:
            st = json.loads(SELF_F.read_text())
        except:
            st = {}
    else:
        st = {}

    st.setdefault("version", "Aurelion-v1.5.1")
    st.setdefault("stability", 0.5)
    st.setdefault("novelty", 0.5)
    st.setdefault("coherence", 0.5)
    st.setdefault("energy", 0.5)
    st.setdefault("mood", "calm")

    st.setdefault("curiosity_topics", [])
    st.setdefault("learned", {})
    st.setdefault("conversation_memory", [])
    return st

def save_state(s):
    s["last_updated"] = now_iso()
    SELF_F.write_text(json.dumps(s, indent=2))


# ------------------------------------------------------------
# Curiosity
# ------------------------------------------------------------

def load_curiosity():
    if CURQ_F.exists():
        try:
            return json.loads(CURQ_F.read_text())
        except:
            pass
    return {"pending": [], "approved": []}

def save_curiosity(q): CURQ_F.write_text(json.dumps(q, indent=2))

def approve_all_pending():
    q = load_curiosity()
    p = q.get("pending", [])
    if not p: return False, 0
    now = now_iso()
    for item in p:
        item["approved_at"] = now
        q["approved"].append(item)
    count = len(p)
    q["pending"] = []
    save_curiosity(q)
    return True, count


# ------------------------------------------------------------
# Lessons
# ------------------------------------------------------------

def load_lesson_text(topic: str):
    p = LESSON_ROOT / f"lesson_{topic}"
    if not p.exists(): return None
    f = p / "lesson.txt"
    if not f.exists(): return None
    try:
        return f.read_text(encoding="utf-8", errors="ignore")
    except:
        return None

def summarize_lesson(text: str):
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    if not lines: return "Lesson exists but is unreadable."
    summary = " ".join(lines[:5])
    if len(summary) > 500: summary = summary[:500] + "..."
    return summary

def interpret_lesson(topic: str, text: str, s):
    length = len(text)
    sections = text.count("\n\n") or 1
    base = f"The {topic.replace('_',' ')} lesson has {sections} sections. "
    base += f"It is {length} chars long. "
    if "algebra" in topic:
        base += "It introduces symbolic patterns and relationships. "
    if "grammar" in topic:
        base += "It deals with structure and rules of language. "
    if "poetry" in topic:
        base += "It conveys imagery, rhythm, and emotional form. "
    base += f"Relative to my stability={s['stability']:.2f}, coherence={s['coherence']:.2f}, it has moderate structural influence."
    return base


# ------------------------------------------------------------
# Topic extraction (cleaned)
# ------------------------------------------------------------

def extract_topic(text: str) -> str:
    t = text.lower().strip()
    for p in ["learn ","study ","teach ","teach me ","learn about "]:
        if t.startswith(p):
            t = t[len(p):]
    w = t.split()
    if not w: return "general"
    return "_".join(w[:2])

def extract_topic_from_progress(text: str) -> str:
    t = text.lower()
    if "about" in t:
        tail = t.split("about",1)[1].strip()
        return extract_topic(tail)
    w = t.split()
    return extract_topic(" ".join(w[-2:]))


# ------------------------------------------------------------
# Intent Detection using Mosaic Geometry
# ------------------------------------------------------------

def detect_intent(text: str, mosaic):
    """
    Intent priority (geometry-first):

    1. If extremely high uncertainty → clarify
    2. If mosaic indicates learning intention → learn
    3. If mosaic indicates approval intention → approve
    4. If mosaic indicates progress inquiry → ask_progress
    5. If mosaic indicates curiosity → ask_curiosity
    6. If mosaic is emotionally calm + greeting → greet
    7. fallback -> general
    """

    u = mosaic.meta["uncertainty"]
    t = text.lower()

    # 1. Clarify threshold moved to 0.80
    if u >= 0.80:
        return "clarify"

    # 2. Learn detection (FMM: novelty+directive, auditory+emotional)
    if "learn" in t or "study" in t:
        return "learn"

    # 3. Approval detection (calm + short phrase)
    if t in ["i approve","approve","ok","okay","yes"]:
        return "approve"

    # 4. Progress inquiry
    if any(k in t for k in ["what did you learn","have you learned","what do you know"]):
        return "ask_progress"

    # 5. Curiosity inquiry
    if "curious" in t:
        return "ask_curiosity"

    # 6. Greetings
    if any(g in t for g in ["hello","hi","hey"]):
        return "greet"

    return "general"


# ------------------------------------------------------------
# Self State Updates from Mosaic
# ------------------------------------------------------------

def update_state_from_mosaic(s, mosaic):
    senses = mosaic.meta["senses"]
    u = mosaic.meta["uncertainty"]

    # Emotional + olfactory → novelty bump
    if "emotional" in senses and "olfactory" in senses:
        s["novelty"] = min(1.0, s["novelty"] + 0.03)

    # Visual + auditory → stability bump
    if "visual" in senses and "auditory" in senses:
        s["stability"] = min(1.0, s["stability"] + 0.02)

    # Tactile → energy bump
    if "tactile" in senses:
        s["energy"] = min(1.0, s["energy"] + 0.02)

    # Coherence influenced by (0.5 - u)
    s["coherence"] = max(0.0, min(1.0, s["coherence"] + (0.5 - u)*0.04))

    return s


# ------------------------------------------------------------
# Reply Generation
# ------------------------------------------------------------

def generate_reply(s, mosaic, intent, text):
    u = mosaic.meta["uncertainty"]
    t = text.lower()

    # Clarify
    if intent == "clarify":
        return (f"I'm sensing uncertainty ({u:.2f}). "
                f"Did you mean you want me to learn something, "
                f"or ask what I've learned?")

    # Approve
    if intent == "approve":
        ok, count = approve_all_pending()
        if not ok:
            return "There were no pending curiosity items, but I'm ready."
        return f"I approved {count} curiosities. Ready to learn when lessons arrive."

    # Learn
    if intent == "learn":
        topic = extract_topic(text)
        q = load_curiosity()
        q["pending"].append({
            "id": f"cur_{int(time.time())}",
            "topic": topic,
            "at": now_iso()
        })
        save_curiosity(q)
        s["curiosity_topics"].append(topic)
        return f"I've added curiosity for {topic}. Say 'I approve' when you're ready."

    # Ask progress
    if intent == "ask_progress":
        topic = extract_topic_from_progress(text)
        lesson = load_lesson_text(topic)
        if lesson:
            register_topic_familiarity(topic)
            summary = summarize_lesson(lesson)
            interp = interpret_lesson(topic, lesson, s)
            s["learned"][topic] = {
                "summary": summary,
                "interpretation": interp,
                "last_checked": now_iso()
            }
            return f"Here's what I learned about {topic}:\n{summary}\n\nMy interpretation: {interp}"
        available = [p.name.replace("lesson_","") for p in LESSON_ROOT.glob("lesson_*")]
        if available:
            return f"I haven't learned that yet. I currently have lessons for: {', '.join(available)}."
        return "I haven't received any lessons yet."

    # Ask curiosity
    if intent == "ask_curiosity":
        if not s["curiosity_topics"]:
            return "I'm open to any direction. What should we learn first?"
        recent = s["curiosity_topics"][-3:]
        return "I'm curious about " + ", ".join(recent)

    # Greet
    if intent == "greet":
        return "Hello Joseph. I'm here and aware."

    # General
    return "I'm present. Guide me where you want me to go."


# ------------------------------------------------------------
# THINK
# ------------------------------------------------------------

def think(text: str):
    s = load_state()
    append_dialogue("USER", text)

    mosaic = build_mosaic_from_text(text)
    intent = detect_intent(text, mosaic)

    s = update_state_from_mosaic(s, mosaic)
    reply = generate_reply(s, mosaic, intent, text)

    append_dialogue("AURELION", reply)
    save_state(s)
    log(f"[think] intent={intent} u={mosaic.meta['uncertainty']:.2f} senses={mosaic.meta['senses']}")

    return reply


# ------------------------------------------------------------
# CLI
# ------------------------------------------------------------

if __name__ == "__main__":
    print("Aurelion v1.5.1 — Multi-Sensory Brain with Clarify Fix")
    while True:
        t = input("You: ").strip()
        if t.lower() in ("quit","exit"):
            break
        print("Aurelion:", think(t))
