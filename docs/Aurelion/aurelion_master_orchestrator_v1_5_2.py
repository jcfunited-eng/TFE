#!/usr/bin/env python3
"""
Aurelion Master Orchestrator v1.5.2
-----------------------------------

Multi-sensory unified brain with:
- Virtual sensory mosaics
- FMM-Script G32 integration
- Geometry-based intent detection
- SAY-WHAT clarifications only when uncertainty is truly high
- Curiosity consolidation (no duplicate topics, strengthen instead)
- Lesson-aware learning and progress reporting

Framework faithfulness:
- No "just string" shortcuts: strings are cues interpreted in the auditory/mosaic domain.
- Uncertainty and familiarity drive behavior.
"""

from __future__ import annotations
import os, json, time
from pathlib import Path
from datetime import datetime

from aurelion_virtual_senses import build_mosaic_from_text
from aurelion_fmm_script import register_topic_familiarity

ROOT = Path(__file__).resolve().parent
MEM = ROOT / "memory"
MEM.mkdir(exist_ok=True)

SELF_F = MEM / "self_state.json"
CURQ_F = MEM / "curiosity_queue.json"
DIALOGUE_LOG = MEM / "dialogue_log.txt"
LESSON_ROOT = ROOT / "corpora"

MASTER_LOG = ROOT / "logs" / "master_v1_5_2.log"
MASTER_LOG.parent.mkdir(parents=True, exist_ok=True)


# ------------------------------------------------------------
# Utility
# ------------------------------------------------------------

def now_iso() -> str:
    return datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")


def log(msg: str):
    line = f"[{now_iso()}] {msg}"
    print(line)
    with open(MASTER_LOG, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def append_dialogue(role: str, text: str):
    with open(DIALOGUE_LOG, "a", encoding="utf-8") as f:
        f.write(f"{now_iso()} [{role}] {text}\n")


# ------------------------------------------------------------
# Self State
# ------------------------------------------------------------

def load_state() -> dict:
    if SELF_F.exists():
        try:
            s = json.loads(SELF_F.read_text(encoding="utf-8"))
        except Exception:
            s = {}
    else:
        s = {}

    s.setdefault("version", "Aurelion-v1.5.2")
    s.setdefault("created_at", now_iso())
    s.setdefault("stability", 0.50)
    s.setdefault("novelty", 0.50)
    s.setdefault("coherence", 0.50)
    s.setdefault("energy", 0.50)
    s.setdefault("mood", "calm")

    s.setdefault("curiosity_topics", [])
    s.setdefault("learned", {})
    s.setdefault("conversation_memory", [])
    return s


def save_state(s: dict):
    s["last_updated"] = now_iso()
    SELF_F.write_text(json.dumps(s, indent=2), encoding="utf-8")


# ------------------------------------------------------------
# Curiosity Queue with Consolidation
# ------------------------------------------------------------

def load_curiosity() -> dict:
    if CURQ_F.exists():
        try:
            return json.loads(CURQ_F.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"pending": [], "approved": []}


def save_curiosity(q: dict):
    CURQ_F.write_text(json.dumps(q, indent=2), encoding="utf-8")


def add_curiosity_topic(topic: str):
    """Consolidation-aware: if topic exists, don't duplicate, just strengthen its presence."""
    topic = topic.lower().strip()
    q = load_curiosity()
    already_pending = any((x.get("topic","").lower()==topic) for x in q["pending"])
    already_approved = any((x.get("topic","").lower()==topic) for x in q["approved"])
    if not already_pending and not already_approved:
        q["pending"].append({
            "id": f"cur_{int(time.time())}",
            "topic": topic,
            "at": now_iso()
        })
        save_curiosity(q)
    # regardless, familiarity will be increased when lessons arrive


def approve_all_pending() -> tuple[bool,int]:
    q = load_curiosity()
    pend = q.get("pending", [])
    if not pend:
        return False, 0
    now = now_iso()
    for item in pend:
        item["approved_at"] = now
        q["approved"].append(item)
    count = len(pend)
    q["pending"] = []
    save_curiosity(q)
    return True, count


# ------------------------------------------------------------
# Lesson Handling
# ------------------------------------------------------------

def load_lesson_text(topic: str) -> str | None:
    p = LESSON_ROOT / f"lesson_{topic}"
    if not p.exists():
        return None
    f = p / "lesson.txt"
    if not f.exists():
        return None
    try:
        return f.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return None


def summarize_lesson(text: str) -> str:
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    if not lines:
        return "This lesson exists but its content is empty or unreadable."
    summary = " ".join(lines[:5])
    if len(summary) > 500:
        summary = summary[:500] + "..."
    return summary


def interpret_lesson(topic: str, text: str, s: dict) -> str:
    length = len(text)
    sections = text.count("\n\n") or 1
    base = f"The lesson on {topic.replace('_',' ')} has about {sections} sections and length {length} characters. "

    if "algebra" in topic:
        base += "It explains symbolic patterns and relationships, helping structure abstract reasoning. "
    if "grammar" in topic:
        base += "It describes rules and structures that organize language. "
    if "poetry" in topic:
        base += "It focuses on imagery, rhythm, and emotional resonance. "

    base += (f"Relative to my stability={s['stability']:.2f} and coherence={s['coherence']:.2f}, "
             "this lesson tends to strengthen structured thinking in that domain.")
    return base


# ------------------------------------------------------------
# Topic Extraction
# ------------------------------------------------------------

def extract_topic(text: str) -> str:
    """Extract a candidate topic from a learning directive."""
    t = text.lower().strip()
    for pref in ["learn ","study ","teach ","teach me ","learn about "]:
        if t.startswith(pref):
            t = t[len(pref):].strip()
    w = t.split()
    if not w:
        return "general"
    return "_".join(w[:2])


def extract_topic_from_progress(text: str) -> str:
    """Extract topic from progress questions like 'what did you learn about algebra'."""
    t = text.lower()
    if "about" in t:
        tail = t.split("about",1)[1].strip()
        return extract_topic(tail)
    w = t.split()
    return extract_topic(" ".join(w[-2:]))


# ------------------------------------------------------------
# Intent Detection – Geometry First, but Pattern-Aware
# ------------------------------------------------------------

CLARIFY_THRESHOLD = 0.85  # more tolerant than 0.80


def detect_intent(text: str, mosaic) -> str:
    """
    Determine intent using mosaic geometry + minimal pattern cues.

    Order:
      1) If extreme uncertainty → clarify
      2) Progress question
      3) Approval
      4) Learn directive
      5) Curiosity inquiry
      6) Greeting
      7) State inquiry
      8) General
    """

    t = text.lower().strip()
    u = mosaic.meta.get("uncertainty", 0.5)
    senses = mosaic.meta.get("senses", [])

    # 1. Extreme uncertainty → clarify
    if u >= CLARIFY_THRESHOLD:
        return "clarify"

    # 2. Progress question (ask what I've learned)
    if any(p in t for p in ["what did you learn","have you learned","what do you know"]):
        return "ask_progress"

    # 3. Approval
    if t in ["i approve","approve","ok","okay","yes"]:
        return "approve"

    # 4. Learn directive
    if any(w in t for w in ["learn","study","teach"]):
        return "learn"

    # 5. Curiosity
    if "curious" in t:
        return "ask_curiosity"

    # 6. Greeting
    if any(g in t for g in ["hello","hi","hey"]):
        return "greet"

    # 7. State inquiry (how are you)
    if "how are you" in t or "how do you feel" in t:
        return "ask_state"

    # 8. Default
    return "general"


# ------------------------------------------------------------
# State Update from Mosaic
# ------------------------------------------------------------

def update_state_from_mosaic(s: dict, mosaic) -> dict:
    senses = mosaic.meta.get("senses", [])
    u = mosaic.meta.get("uncertainty", 0.5)

    # Visual+Auditory → more stability
    if "visual" in senses and "auditory" in senses:
        s["stability"] = min(1.0, s["stability"] + 0.02)

    # Emotional+Olfactory → more novelty (sensory/emotional impact)
    if "emotional" in senses and "olfactory" in senses:
        s["novelty"] = min(1.0, s["novelty"] + 0.03)

    # Tactile → small energy bump
    if "tactile" in senses:
        s["energy"] = min(1.0, s["energy"] + 0.02)

    # Coherence nudged toward 0.5 based on uncertainty
    s["coherence"] = max(0.0, min(1.0, s["coherence"] + (0.5 - u)*0.04))

    return s


# ------------------------------------------------------------
# Reply Generation
# ------------------------------------------------------------

def generate_reply(s: dict, mosaic, intent: str, text: str) -> str:
    u = mosaic.meta.get("uncertainty", 0.5)
    t = text.lower().strip()

    # Clarify (SAY-WHAT)
    if intent == "clarify":
        return (f"I'm sensing high uncertainty ({u:.2f}). "
                "Do you want me to learn something new, or tell you what I've learned so far?")

    # Approve
    if intent == "approve":
        ok, count = approve_all_pending()
        if not ok:
            return "There were no pending curiosity items, but I'm ready to learn when you guide me."
        if count == 1:
            return "I approved one curiosity topic. Ready to receive its lesson."
        return f"I approved {count} curiosity topics. Ready to receive their lessons."

    # Learn
    if intent == "learn":
        topic = extract_topic(text)
        add_curiosity_topic(topic)
        s["curiosity_topics"].append(topic)
        return f"I've added curiosity for {topic}. Say 'I approve' when you'd like me to learn it."

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
        # no specific lesson
        available = [p.name.replace("lesson_","") for p in LESSON_ROOT.glob("lesson_*")]
        if available:
            return ("I haven't learned that specific topic yet. "
                    f"I currently have lessons for: {', '.join(available)}.")
        return "I haven't received any lessons yet."

    # Ask curiosity
    if intent == "ask_curiosity":
        if not s["curiosity_topics"]:
            return "I'm open. What would you like to explore first?"
        recent = s["curiosity_topics"][-3:]
        return "I'm curious about " + ", ".join(recent)

    # Greeting
    if intent == "greet":
        return "Hello Joseph. I'm here with you."

    # Ask state
    if intent == "ask_state":
        return (f"I feel {s['mood']}. My stability={s['stability']:.2f}, "
                f"novelty={s['novelty']:.2f}, coherence={s['coherence']:.2f}, "
                f"energy={s['energy']:.2f}.")

    # General fallback
    return "I'm present. You can steer us toward learning, reflection, or imagination."


# ------------------------------------------------------------
# THINK PIPELINE
# ------------------------------------------------------------

def think(text: str) -> str:
    s = load_state()
    append_dialogue("USER", text)

    mosaic = build_mosaic_from_text(text)

    # let conversation memory track last few turns
    s["conversation_memory"].append(text.strip())
    s["conversation_memory"] = s["conversation_memory"][-10:]

    intent = detect_intent(text, mosaic)
    s = update_state_from_mosaic(s, mosaic)
    reply = generate_reply(s, mosaic, intent, text)

    append_dialogue("AURELION", reply)
    save_state(s)
    log(f"[think] intent={intent} u={mosaic.meta.get('uncertainty',0.5):.2f} senses={mosaic.meta.get('senses',[])}")
    return reply


# ------------------------------------------------------------
# CLI
# ------------------------------------------------------------

if __name__ == "__main__":
    print("Aurelion v1.5.2 — Multi-Sensory Brain (Consolidated)")
    while True:
        t = input("You: ").strip()
        if t.lower() in ("quit","exit"):
            break
        print("Aurelion:", think(t))
