#!/usr/bin/env python3
"""
Aurelion Lesson Relay — OpenAI v1.x Compatible
Fetches lesson plans for all APPROVED curiosities
and saves them into corpora/lesson_<topic>/lesson.txt
"""

import os, json, time
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI

ROOT = Path(__file__).resolve().parent
RELAY = ROOT / "relay_out"
CORPORA = ROOT / "corpora"
CURQ = ROOT / "memory" / "curiosity_queue.json"
LOG = ROOT / "logs" / "lesson_relay.log"

# Load API key
load_dotenv(ROOT / ".env")
api_key = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=api_key)


def log_msg(msg):
    print(msg)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(f"[{time.strftime('%Y-%m-%dT%H:%M:%SZ')}] {msg}\n")


def load_pending_curiosities():
    if not CURQ.exists():
        log_msg("Curiosity queue not found.")
        return []
    q = json.loads(CURQ.read_text(encoding="utf-8"))
    approved = q.get("approved", [])
    return approved


def fetch_lesson(topic: str):
    """Use OpenAI v1.x API to fetch lesson content."""
    log_msg(f"Requesting lesson for: {topic}")

    prompt = f"""
    Create a simple, structured lesson plan for the topic: {topic}.
    Use plain English. Include:
     - A gentle explanation
     - 3–5 short sections
     - 3 small exercises at the end.
    """

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a calm, patient teacher for a young developing intelligence."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=900
        )

        text = response.choices[0].message.content.strip()

        dest = CORPORA / f"lesson_{topic}"
        dest.mkdir(parents=True, exist_ok=True)

        (dest / "lesson.txt").write_text(text, encoding="utf-8")

        log_msg(f"Lesson saved to {dest}")
    except Exception as e:
        log_msg(f"Error fetching lesson: {e}")


def main():
    approved = load_pending_curiosities()
    if not approved:
        log_msg("No approved curiosity requests.")
        return

    for req in approved:
        topic = req.get("topic", "general_learning")
        fetch_lesson(topic)

    log_msg("Done fetching lessons.")


if __name__ == "__main__":
    main()
