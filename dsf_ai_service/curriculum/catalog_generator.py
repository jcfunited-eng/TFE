"""
catalog_generator.py — LLM-powered sensory distribution generation.

GL-CMD-112 Phase B, per GL-SPC-SENSORY-CATALOG-EVE-20260621-111 §6.3.

Generates sensory parameter distributions for batches of words using Claude.
Stores results in the SensoryCatalog. Retry with exponential backoff.
"""

import json
import os
import time
from typing import Any, Dict, List, Optional

from .sensory_catalog import SensoryCatalog, MODALITY_CHANNELS_MAP

# LLM brief template — uses the canonical 8-channel smell set
_BRIEF_TEMPLATE = """You are generating sensory parameter distributions for a substrate that experiences words physically.

For each word, provide the mean and standard deviation for each channel of each applicable modality.
All values must be in [0.0, 1.0]. If a word has no sensory grounding for a modality, mark it "not_applicable".

Modalities and their channels:
- touch: temperature, pressure, texture_freq, sharpness, wetness (all 0-1)
- smell: sweet, putrid, floral, fruity, smoky, earthy, sour, fresh (all 0-1)
- taste: sweet, sour, salty, bitter, umami (all 0-1)

Story context: {story_context}

Words to process: {words_json}

Respond with ONLY valid JSON — an array of objects, one per word:
[
  {{
    "word": "warm",
    "touch": {{"mean": {{"temperature": 0.7, "pressure": 0.2, ...}}, "std": {{"temperature": 0.1, ...}}}},
    "smell": "not_applicable",
    "taste": "not_applicable"
  }},
  ...
]

Rules:
- Every channel for every applicable modality MUST have both mean and std
- std values should be 0.05-0.25 (tight for specific words like "ice", wider for abstract like "happy")
- If a word is abstract with no sensory grounding at all, mark ALL modalities "not_applicable"
- Respond with ONLY the JSON array, no markdown, no explanation
"""

MAX_RETRIES = 3
RETRY_DELAYS = [1.0, 2.0, 4.0]  # exponential backoff


class CatalogGenerator:
    """Generates sensory catalog entries from word batches via LLM."""

    def __init__(self, catalog: SensoryCatalog, api_key: Optional[str] = None):
        self.catalog = catalog
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")

    def generate(self, words: List[str], story_context: str = "") -> Dict[str, Any]:
        """Generate catalog entries for a batch of words.

        Returns dict with:
            generated: int — words successfully cataloged
            failed: List[str] — words that failed after retries
            skipped: int — words already in catalog
        """
        # Filter out words already in catalog
        unknown = self.catalog.list_unknown(words)
        if not unknown:
            return {"generated": 0, "failed": [], "skipped": len(words)}

        # Batch in groups of 20 for LLM context efficiency
        batch_size = 20
        total_generated = 0
        total_failed = []

        for i in range(0, len(unknown), batch_size):
            batch = unknown[i:i + batch_size]
            result = self._generate_batch(batch, story_context)
            if result is not None:
                total_generated += self._store_results(result, batch)
            else:
                total_failed.extend(batch)

        return {
            "generated": total_generated,
            "failed": total_failed,
            "skipped": len(words) - len(unknown),
        }

    def _generate_batch(self, words: List[str], story_context: str) -> Optional[List[Dict]]:
        """Call LLM for a batch. Returns parsed results or None on permanent failure."""
        prompt = _BRIEF_TEMPLATE.format(
            story_context=story_context or "(no context)",
            words_json=json.dumps(words),
        )

        for attempt in range(MAX_RETRIES):
            try:
                response_text = self._call_llm(prompt)
                results = self._parse_response(response_text, words)
                if results is not None:
                    return results
            except (ConnectionError, TimeoutError, OSError) as e:
                if attempt < MAX_RETRIES - 1:
                    time.sleep(RETRY_DELAYS[attempt])
                    continue
                return None
            except Exception:
                if attempt < MAX_RETRIES - 1:
                    time.sleep(RETRY_DELAYS[attempt])
                    continue
                return None

        return None

    def _call_llm(self, prompt: str) -> str:
        """Call Anthropic API. Raises on network/auth errors."""
        if not self.api_key:
            raise RuntimeError("ANTHROPIC_API_KEY not set")

        import anthropic
        client = anthropic.Anthropic(api_key=self.api_key)
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4096,
            messages=[{"role": "user", "content": prompt}],
        )
        return message.content[0].text

    def _parse_response(self, text: str, expected_words: List[str]) -> Optional[List[Dict]]:
        """Parse LLM JSON response. Returns list of word dicts or None if malformed."""
        text = text.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1] if "\n" in text else text[3:]
            if text.endswith("```"):
                text = text[:-3]
            text = text.strip()

        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            return None

        if not isinstance(data, list):
            return None

        # Validate structure
        for entry in data:
            if not isinstance(entry, dict) or "word" not in entry:
                return None

        return data

    def _store_results(self, results: List[Dict], batch_words: List[str]) -> int:
        """Store parsed LLM results in catalog. Returns count of words stored."""
        stored = 0
        result_map = {r["word"]: r for r in results if "word" in r}

        for word in batch_words:
            entry = result_map.get(word)
            if entry is None:
                continue

            word_stored = False
            for modality, channels in MODALITY_CHANNELS_MAP.items():
                mod_data = entry.get(modality)
                if mod_data == "not_applicable" or mod_data is None:
                    self.catalog.set_entry(word, modality, applicable=False)
                    word_stored = True
                    continue

                if not isinstance(mod_data, dict):
                    continue

                mean = mod_data.get("mean", {})
                std = mod_data.get("std", {})

                # Validate all values in [0, 1]
                valid = True
                for ch in channels:
                    m = mean.get(ch)
                    s = std.get(ch)
                    if m is None or s is None:
                        valid = False
                        break
                    if not (0.0 <= m <= 1.0) or not (0.0 <= s <= 1.0):
                        valid = False
                        break

                if valid:
                    self.catalog.set_entry(
                        word, modality, applicable=True,
                        mean={ch: mean[ch] for ch in channels},
                        std={ch: std[ch] for ch in channels},
                    )
                    word_stored = True

            if word_stored:
                stored += 1

        return stored
