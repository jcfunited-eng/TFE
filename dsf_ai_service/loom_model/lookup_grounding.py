"""lookup_grounding.py — ground what Guala focuses on in real-world knowledge.

Joe's intent: a vision/audio "lookup" that takes an item she focuses on and feeds
a description of it through her senses + organ-brain, so her words mean real things.
He named Google; the repo has no Google/Vision key, but it DOES have OPENAI_API_KEY
(and TAVILY_API_KEY). So this uses OpenAI as the controlled substitute: a tightly
constrained prompt that returns ONE simple, warm, child-appropriate sentence — safe
to feed a child-like learner, unlike raw web scrape. Network IO lives here; feeding
the substrate stays in the caller.

No SDK dependency (uses stdlib urllib, like the Gutenberg adapter). Fully
exception-walled and key-optional: returns None on any miss, never raises.

SAFETY/COST: each call is one short gpt-4o-mini completion (~fractions of a cent).
The prompt forbids anything not suitable for a young child. Autonomous use is OFF by
default in the scheduler (LOOKUP_AUTONOMOUS) — a human enables it.
"""

import json
import os
import urllib.request

_OPENAI_URL = "https://api.openai.com/v1/chat/completions"
_MODEL = os.environ.get("LOOKUP_MODEL", "gpt-4o-mini")

_SYSTEM = (
    "You describe things for a gentle three-year-old child. Reply with ONE short, "
    "warm, simple sentence in plain words a small child knows. Include what it looks, "
    "feels, sounds, or smells like when natural. No lists, no scary or adult content, "
    "no questions. Just the one kind sentence."
)


def _openai_key():
    key = os.environ.get("OPENAI_API_KEY")
    if key:
        return key
    # fall back to a local .env (dev); container provides it via env
    try:
        here = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        for line in open(os.path.join(here, ".env")):
            if line.startswith("OPENAI_API_KEY="):
                return line.split("=", 1)[1].strip()
    except Exception:
        pass
    return None


def describe(term, timeout=20):
    """Return one child-safe sentence describing `term`, or None. Never raises."""
    term = (term or "").strip()
    if not term:
        return None
    key = _openai_key()
    if not key:
        return None
    try:
        body = json.dumps({
            "model": _MODEL,
            "messages": [
                {"role": "system", "content": _SYSTEM},
                {"role": "user", "content": f"Describe: {term}"},
            ],
            "max_tokens": 60,
            "temperature": 0.4,
        }).encode()
        req = urllib.request.Request(
            _OPENAI_URL, data=body,
            headers={"Authorization": f"Bearer {key}",
                     "Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.load(resp)
        text = (data["choices"][0]["message"]["content"] or "").strip()
        # one sentence, sane length
        return text[:300] if text else None
    except Exception:
        return None
