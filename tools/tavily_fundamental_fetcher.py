#!/usr/bin/env python3
"""Tavily-based fallback for fetching fundamental financial metrics.

Used ONLY when Polygon and Yahoo Finance both fail to provide required
metrics (typically gross_profit).  Queries Tavily's finance-topic search
for SEC filing data, parses the results, and returns metrics in the same
format as FundamentalCorpora.evaluate_ticker().

Design constraints:
  - Each ticker is queried AT MOST ONCE.  The caller marks tavily_tried_at
    in the DB so we never repeat a lookup.
  - No ML, no heuristics — just structured data extraction from search results.
  - Rate limited: 1 second between calls.
"""

from __future__ import annotations

import json
import os
import re
import time
from typing import Any, Dict, List, Optional

import requests


class TavilyFundamentalFetcher:
    """Fetch missing fundamental metrics via Tavily search API."""

    def __init__(self, api_key: Optional[str] = None, timeout: int = 30) -> None:
        self._api_key = (api_key or os.environ.get("TAVILY_API_KEY", "")).strip()
        if not self._api_key:
            raise RuntimeError("TAVILY_API_KEY is required for TavilyFundamentalFetcher.")
        self._timeout = timeout
        self._session = requests.Session()
        self._last_call = 0.0

    def _rate_limit(self) -> None:
        elapsed = time.monotonic() - self._last_call
        if elapsed < 1.0:
            time.sleep(1.0 - elapsed)

    def _search(self, query: str) -> Dict[str, Any]:
        self._rate_limit()
        try:
            resp = self._session.post(
                "https://api.tavily.com/search",
                json={
                    "query": query,
                    "search_depth": "advanced",
                    "topic": "finance",
                    "max_results": 5,
                    "include_answer": "advanced",
                    "include_raw_content": "markdown",
                },
                headers={"Authorization": f"Bearer {self._api_key}"},
                timeout=self._timeout,
            )
            self._last_call = time.monotonic()
            if resp.status_code == 200:
                return resp.json()
            else:
                return {"error": f"HTTP {resp.status_code}: {resp.text[:200]}"}
        except Exception as exc:
            self._last_call = time.monotonic()
            return {"error": str(exc)}

    @staticmethod
    def _parse_number(text: str) -> Optional[float]:
        """Parse a number from text, handling B/M/K suffixes and commas."""
        if not text:
            return None
        text = text.strip().replace(",", "").replace("$", "")
        # Handle negative in parens: (1.5B) -> -1.5B
        if text.startswith("(") and text.endswith(")"):
            text = "-" + text[1:-1]

        multiplier = 1.0
        if text.upper().endswith("T"):
            multiplier = 1e12
            text = text[:-1]
        elif text.upper().endswith("B"):
            multiplier = 1e9
            text = text[:-1]
        elif text.upper().endswith("M"):
            multiplier = 1e6
            text = text[:-1]
        elif text.upper().endswith("K"):
            multiplier = 1e3
            text = text[:-1]

        try:
            return float(text) * multiplier
        except (ValueError, TypeError):
            return None

    def _extract_metrics_from_results(
        self, results: List[Dict[str, Any]], answer: Optional[str], missing_fields: List[str]
    ) -> Dict[str, Optional[float]]:
        """Extract specific financial metrics from Tavily search results."""
        metrics: Dict[str, Optional[float]] = {}

        # Combine all text content, strip markdown bold markers
        all_text = (answer or "") + "\n"
        for r in results:
            all_text += (r.get("content") or "") + "\n"
            all_text += (r.get("raw_content") or "") + "\n"
        all_text = all_text.replace("**", "")

        # Patterns for each metric we might need.
        # NUMBER captures: "$2.5B", "2.5 billion", "45,628", "$800M"
        _NUM = r"\$?([\d,.]+)\s*(?:billion|million|trillion|[TBMK])?"
        _NUM_WORD = r"\$?([\d,.]+)\s+(billion|million|trillion)"
        patterns: Dict[str, List[str]] = {
            "gross_profit": [
                r"gross\s+profit[s]?\s+(?:of\s+)?(?:roughly\s+|approximately\s+|about\s+)?" + _NUM_WORD,
                r"gross\s+profit[s]?[:\s]*\$?([\d,.]+[TBMK]?)",
                r"gross\s+profit[s]?\s+(?:was|of|is|at)\s+\$?([\d,.]+[TBMK]?)",
            ],
            "revenues": [
                r"(?:total\s+)?revenue[s]?\s+(?:of\s+)?(?:roughly\s+|approximately\s+|about\s+)?" + _NUM_WORD,
                r"(?:total\s+)?revenue[s]?[:\s]*\$?([\d,.]+[TBMK]?)",
                r"revenue[s]?\s+(?:was|of|is|at|reached)\s+\$?([\d,.]+[TBMK]?)",
            ],
            "operating_cash_flow": [
                r"operating\s+cash\s+flow\s+(?:of\s+)?(?:roughly\s+|approximately\s+|about\s+)?" + _NUM_WORD,
                r"operating\s+cash\s+flow[:\s]*\$?([\-\d,.]+[TBMK]?)",
                r"operating\s+cash\s+flow\s+(?:was|of|is|at)\s+\$?([\-\d,.]+[TBMK]?)",
                r"cash\s+(?:flow\s+)?from\s+operations?\s+(?:of\s+)?(?:roughly\s+|approximately\s+|about\s+)?" + _NUM_WORD,
                r"cash\s+(?:flow\s+)?from\s+operations?[:\s]*\$?([\-\d,.]+[TBMK]?)",
            ],
            "current_ratio": [
                r"current\s+ratio[:\s]*([\d]+(?:\.\d+)?)",
                r"current\s+ratio\s+(?:was|of|is|at)\s+([\d]+(?:\.\d+)?)",
            ],
            "free_cash_flow": [
                r"free\s+cash\s+flow\s+(?:of\s+)?(?:roughly\s+|approximately\s+|about\s+)?" + _NUM_WORD,
                r"free\s+cash\s+flow[:\s]*\$?([\-\d,.]+[TBMK]?)",
                r"free\s+cash\s+flow\s+(?:was|of|is|at)\s+\$?([\-\d,.]+[TBMK]?)",
                r"FCF[:\s]*\$?([\-\d,.]+[TBMK]?)",
            ],
            "gross_margin": [
                r"gross\s+margin[:\s]*([\d,.]+)%",
                r"gross\s+margin\s+(?:was|of|is|at)\s+([\d,.]+)%",
            ],
            "market_cap": [
                r"market\s+cap(?:italization)?[:\s]*\$?([\d,.]+[TBMK]?)",
                r"market\s+cap(?:italization)?\s+(?:was|of|is|at)\s+\$?([\d,.]+[TBMK]?)",
            ],
        }

        word_multipliers = {
            "trillion": 1e12, "billion": 1e9, "million": 1e6,
        }

        for field in missing_fields:
            if field not in patterns:
                continue
            for pattern in patterns[field]:
                match = re.search(pattern, all_text, re.IGNORECASE)
                if match:
                    raw_num = match.group(1)
                    # Check if there's a word multiplier in group(2)
                    word_mult = 1.0
                    if match.lastindex and match.lastindex >= 2:
                        word = (match.group(2) or "").strip().lower()
                        word_mult = word_multipliers.get(word, 1.0)
                    value = self._parse_number(raw_num)
                    if value is not None:
                        value *= word_mult
                        # gross_margin comes as percentage, convert to decimal
                        if field == "gross_margin" and value > 1:
                            value = value / 100.0
                        metrics[field] = value
                        break

        return metrics

    def fetch_missing_metrics(
        self, ticker: str, missing_fields: List[str]
    ) -> Dict[str, Any]:
        """Fetch missing financial metrics for a ticker via Tavily.

        Returns dict with:
          - status: "TAVILY_PASS" | "TAVILY_PARTIAL" | "TAVILY_FAIL"
          - metrics: dict of field_name -> value (only fields that were found)
          - fields_found: list of field names successfully extracted
          - fields_still_missing: list of fields still not found
        """
        if not missing_fields:
            return {"status": "TAVILY_PASS", "metrics": {}, "fields_found": [], "fields_still_missing": []}

        # Build a targeted query pointing at income statement / balance sheet sites
        field_names = ", ".join(f.replace("_", " ") for f in missing_fields[:4])
        query = (
            f"{ticker} annual income statement balance sheet {field_names} "
            f"site:macrotrends.net OR site:stockanalysis.com OR site:wsj.com OR site:marketwatch.com"
        )

        print(f"  → [TAVILY] Searching for {ticker}: {field_names}", flush=True)
        result = self._search(query)

        if "error" in result:
            print(f"  → [TAVILY] Search failed: {result['error']}", flush=True)
            return {
                "status": "TAVILY_FAIL",
                "metrics": {},
                "fields_found": [],
                "fields_still_missing": missing_fields,
                "error": result["error"],
            }

        answer = result.get("answer")
        results = result.get("results", [])

        metrics = self._extract_metrics_from_results(results, answer, missing_fields)

        fields_found = [f for f in missing_fields if f in metrics and metrics[f] is not None]
        fields_still_missing = [f for f in missing_fields if f not in fields_found]

        if fields_found:
            print(f"  → [TAVILY] Found: {', '.join(fields_found)} = {[metrics[f] for f in fields_found]}", flush=True)
        if fields_still_missing:
            print(f"  → [TAVILY] Still missing: {', '.join(fields_still_missing)}", flush=True)

        if len(fields_still_missing) == 0:
            status = "TAVILY_PASS"
        elif len(fields_found) > 0:
            status = "TAVILY_PARTIAL"
        else:
            status = "TAVILY_FAIL"

        return {
            "status": status,
            "metrics": metrics,
            "fields_found": fields_found,
            "fields_still_missing": fields_still_missing,
        }
