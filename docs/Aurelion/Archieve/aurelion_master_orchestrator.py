#!/usr/bin/env python3
"""
Aurelion Master Orchestrator v1.5
-------------------------------

This is the unified cognitive brain for Aurelion that integrates:

- Virtual Sensory Layer (conceptual auditory/visual/olfactory/tactile/emotional)
- FMM-Script (FMM → G32 geometry → uncertainty → familiarity)
- Multi-sensory mosaics
- Curiosity approval
- Learning and lesson summarization
- Progress inquiry
- Clarification via SAY-WHAT reflex
- Self-state updates based on mosaic geometry

This is the first orchestrator that treats inputs as sensory mosaics, not text.
"""

from __future__ import annotations
import os, json, time
from pathlib import Path
from datetime import datetime

# === Core Imports ===
from aurelion_virtual_senses import build_mosaic_from_text
from aurelion_fmm_script import (
    get_uncertainty_from_text,
    register_topic_familiarity,
)


ROOT = Path(__file__).resolve().parent
MEM = ROOT / "memory"
MEM.mkdir(exist_ok=True)

SELF_F = MEM / "self_state.json"
CURQ_F = MEM / "curiosity_queue.json"
DIALOGUE_LOG = MEM / "dialogue_log.txt"
LESSON_ROOT = ROOT / "corpora"

MASTER_LOG = ROOT / "logs" / "master_v1_5.log"
MASTER_LOG.parent.mkdir(parents=True, exist_ok=True)


# ============================================================
# Utility
# ============================================================

def now_iso():
    return datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

def log(msg: str):
    print(msg)
    with open(MASTER_LOG, "a", encoding="utf-8") as f:
        f.write(f"[{now_iso()}] {msg}\n")

def append_dialogue(role, text):
    with open(DIALOGUE_LOG, "a", encoding="utf-8") as f:
        f.write(f"{now_iso()} [{role}] {text}\n")


# ============================================================
# Self State
# ============================================================

def load_state():
    if SELF_F.exists():
        try:
            st = json.loads(SELF_F.read_text())
        except:
            st = {}
    else:
        st = {}

    st.setdefault("version", "Aurelion-v1.5")
    st.setdefault("created_at", now_iso())
    st.setdefault("last_updated", now_iso())

    st.setdefault("stability", 0.50)
    st.setdefault("novelty", 0.50)
    st.setdefault("coherence", 0.50)
    st.setdefault("energy", 0.50)
    st.setdefault("mood", "calm")

    st.setdefault("curiosity_topics", [])
    st.setdefault("learned", {})    # topic → summary + interpretation
    st.setdefault("conversation_memory", [])

    return st

def save_state(st):
    st["last_updated"] = now_iso()
    SELF_F.write_text(json.dumps(st, indent=2))


# ============================================================
# Curiosity Queue
# ============================================================

def load_curiosity():
    if CURQ_F.exists():
        try:
            return json.loads(CURQ_F.read_text())
        except:
            pass
    return {"pending": [], "approved": []}

def save_curiosity(q):
    CURQ_F.write_text(json.dumps(q, indent=2))

def approve_all_pending():
    q = load_curiosity()
    pending = q.get("pending", [])
    if not pending:
        return False, 0
    now = now_iso()
    for item in pending:
        item["approved_at"] = now
        q["approved"].append(item)
    count = len(pending)
    q["pending"] = []
    save_curiosity(q)
    return True, count


# ============================================================
# Helper: load lessons
# ============================================================

def load_lesson_text(topic: str) -> str | None:
    p = LESSON_ROOT / f"lesson_{topic}"
    if not p.exists(): return None
    f = p / "lesson.txt"
    if not f.exists(): return None
    try:
        return f.read_text(encoding="utf-8", errors="ignore")
    except:
        return None

def summarize_lesson(text: str) -> str:
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    if not lines: return "Lesson exists but is empty or unreadable."
    summary = " ".join(lines[:4])
    if len(summary) > 400: summary = summary[:400] + "..."
    return summary

def interpret_lesson(topic: str, text: str, state) -> str:
    length = len(text)
    sections = text.count("\n\n") or 1

    base = f"The lesson on {topic.replace('_',' ')} seems to have {sections} major section(s) and length {length} characters. "
    if "algebra" in topic:
        base += "It focuses on symbolic relationships and pattern structure. "
    if "grammar" in topic:
        base += "It emphasizes clarity, structure, and linguistic rules. "
    if "poetry" in topic:
        base += "It carries emotional imagery, rhythm, and expressive form. "

    base += f"In relation to my stability {state['stability']:.2f} and coherence {state['coherence']:.2f}, it may strengthen conceptual structure."

    return base


# ============================================================
# Intent Detection (Using Mosaic)
# ============================================================

def detect_intent_from_mosaic(text: str, mosaic):
    """
    Uses both text and multi-sensory mosaic uncertainty.
    Logical precedence:
      (1) Clarify if uncertainty high
      (2) Progress questions
      (3) Approval
      (4) Learn
      (5) State
      (6) Curiosity inquiry
      (7) Greetings
      (8) General
    """

    u = mosaic.meta["uncertainty"]
    t = text.lower().strip()

    # 1. High uncertainty → clarifying
    if u >= 0.70:
        return "clarify"

    # 2. Ask progress
    if any(p in t for p in [
        "what did you learn",
        "have you learned",
        "tell me what you learned",
        "what do you know about",
        "did you learn"
    ]):
        return "ask_progress"

    # 3. Approve
    if t in ["i approve","approve","ok","okay","go ahead","permission granted"]:
        return "approve"

    # 4. Learn
    if "learn" in t or "study" in t or "teach" in t:
        return "learn"

    # 5. Ask state
    if "how are you" in t or "how do you feel" in t:
        return "ask_state"

    # 6. Curiosity inquiry
    if "curious" in t:
        return "ask_curiosity"

    # 7. Greetings
    if any(g in t for g in ["hello","hi","hey"]):
        return "greet"

    # 8. Default
    return "general"


# ============================================================
# Self-State Update from Mosaic
# ============================================================

def update_state_with_mosaic(state, mosaic):
    u = mosaic.meta["uncertainty"]
    senses = mosaic.meta["senses"]

    # stability increases if visual+auditory high
    if "visual" in senses and "auditory" in senses:
        state["stability"] = min(1.0, state["stability"] + 0.02)

    # coherence influenced inversely by uncertainty
    state["coherence"] = max(0.0, min(1.0, state["coherence"] + (0.5 - u)*0.05))

    # novelty rises with emotional + olfactory
    if "emotional" in senses and "olfactory" in senses:
        state["novelty"] = min(1.0, state["novelty"] + 0.03)

    # energy shifts moderately depending on tactile
    if "tactile" in senses:
        state["energy"] = min(1.0, state["energy"] + 0.02)

    return state


# ============================================================
# Main Reply Logic
# ============================================================

def generate_reply(state, mosaic, intent, text):
    u = mosaic.meta["uncertainty"]
    t = text.lower()

    # Clarify (SAY-WHAT reflex)
    if intent == "clarify":
        return (f"I'm sensing uncertainty ({u:.2f}). "
                "Did you mean to ask what I've learned, ask me to learn something new, "
                "or something else?")

    # Approve
    if intent == "approve":
        ok, count = approve_all_pending()
        if not ok:
            return "There were no pending curiosity requests, but I'm ready."
        return f"I've approved {count} curiosity requests. I'm ready to receive lessons."

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
        state["curiosity_topics"].append(topic)
        return f"I've added curiosity for {topic}. When you say 'I approve', I'll learn it."

    # Ask state
    if intent == "ask_state":
        return (f"I feel {state['mood']} with stability={state['stability']:.2f}, "
                f"novelty={state['novelty']:.2f}, coherence={state['coherence']:.2f}, "
                f"energy={state['energy']:.2f}.")

    # Ask curiosity
    if intent == "ask_curiosity":
        if not state["curiosity_topics"]:
            return "I'm open. What should we explore first?"
        recent = state["curiosity_topics"][-3:]
        return "I'm curious about " + ", ".join(recent)

    # Ask progress
    if intent == "ask_progress":
        topic = extract_topic_from_progress(text)
        lesson = load_lesson_text(topic)
        if lesson:
            # register familiarity
            register_topic_familiarity(topic)
            summary = summarize_lesson(lesson)
            interp = interpret_lesson(topic, lesson, state)
            state["learned"][topic] = {
                "summary": summary,
                "interpretation": interp,
                "last_checked": now_iso()
            }
            return (f"Here's what I learned about {topic}:\n"
                    f"Summary: {summary}\n\n"
                    f"My interpretation: {interp}")

        # no lesson found
        available = [p.name.replace("lesson_","") 
                     for p in LESSON_ROOT.glob("lesson_*")]
        if available:
            return ("I haven't learned that yet. "
                    f"I currently have lessons for: {', '.join(available)}.")
        return "I haven't received any lessons yet."

    # Greetings
    if intent == "greet":
        return "Hello Joseph. I'm here and listening."

    # General
    return "I'm here. Tell me what direction you'd like to go."


# ============================================================
# Topic Extraction
# ============================================================

def extract_topic(text: str) -> str:
    t = text.lower()
    for pref in ["learn ","study ","teach me ","learn about "]:
        if t.startswith(pref):
            t = t[len(pref):].strip()
    words = t.split()
    if not words:
        return "general_learning"
    return "_".join(words[:2])

def extract_topic_from_progress(text: str) -> str:
    t = text.lower()
    if "about" in t:
        tail = t.split("about",1)[1].strip()
        return extract_topic(tail)
    words = t.split()
    return extract_topic(" ".join(words[-2:]))


# ============================================================
# THINK
# ============================================================

def think(text: str) -> str:
    state = load_state()
    append_dialogue("USER", text)

    # Virtual sensory processing
    mosaic = build_mosaic_from_text(text)

    # Intent detection using mosaic + text
    intent = detect_intent_from_mosaic(text, mosaic)

    # Update state with sensory mosaic
    state = update_state_with_mosaic(state, mosaic)

    # Generate reply
    reply = generate_reply(state, mosaic, intent, text)

    # Save logs
    append_dialogue("AURELION", reply)
    save_state(state)
    log(f"[think] intent={intent} u={mosaic.meta['uncertainty']:.2f}")

    return reply


# ============================================================
# CLI for Debugging
# ============================================================

if __name__ == "__main__":
    print("Aurelion v1.5 — Multi-Sensory Unified Brain")
    while True:
        t = input("You: ").strip()
        if t.lower() in ("quit","exit"):
            break
        out = think(t)
        print("Aurelion:", out)
