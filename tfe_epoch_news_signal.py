#!/usr/bin/env python3
"""
tfe_epoch_news_signal.py
News-driven epoch signal detection.

Queries Tavily for current market-moving news and detects epoch-relevant
events that the price-based auto-severity system can't see:
  - Geopolitical escalation (war, sanctions, regime change)
  - Energy supply disruption (OPEC, pipeline, refinery)
  - Central bank policy shifts (rate decisions, hawkish/dovish)
  - Trade war / tariff escalation
  - Pandemic / health crisis
  - Major corporate events (sector-wide earnings shock)

Each detected event boosts the relevant G32 channel severity.
Results are merged with auto-severity scores — news can only
INCREASE severity, never decrease it. Price is the floor,
news is the amplifier.

No ML. Keyword matching against curated event signatures.
"""
from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

# ── Event signatures ─────────────────────────────────────────────────────────
# Each signature maps keywords to a G32 channel and a severity boost.
# If ANY keyword group matches a headline/answer, the channel gets boosted.

EVENT_SIGNATURES: List[Dict[str, Any]] = [
    # WAR / GEOPOLITICS
    {
        "channel": "WAR_GEOPOLITICS",
        "boost": 0.4,
        "keywords": ["iran", "war", "military strike", "missile", "sanctions",
                     "nuclear", "escalat", "invasion", "troops deployed",
                     "peace plan rejected", "ceasefire collapse", "nato",
                     "south china sea", "taiwan strait"],
    },
    {
        "channel": "WAR_GEOPOLITICS",
        "boost": 0.3,
        "keywords": ["geopolitical", "conflict", "tensions", "retaliat",
                     "embargo", "blockade", "defense spending"],
    },
    # ENERGY / COMMODITY
    {
        "channel": "ENERGY_COMMODITY",
        "boost": 0.4,
        "keywords": ["oil surge", "oil spike", "oil shock", "opec cut",
                     "supply disruption", "refinery shutdown", "pipeline",
                     "barrel", "crude above", "energy crisis",
                     "oil above $90", "oil above $100"],
    },
    {
        "channel": "ENERGY_COMMODITY",
        "boost": 0.3,
        "keywords": ["natural gas", "lng", "energy prices", "fuel cost",
                     "gasoline", "heating oil", "commodity surge"],
    },
    # RATES / INFLATION
    {
        "channel": "RATES_PRESSURE",
        "boost": 0.4,
        "keywords": ["rate hike", "fed raises", "hawkish", "inflation surge",
                     "stagflation", "no rate cut", "rate cuts delayed",
                     "higher for longer", "powell warns"],
    },
    {
        "channel": "RATES_PRESSURE",
        "boost": 0.3,
        "keywords": ["inflation", "cpi higher", "yield spike", "bond sell",
                     "treasury yield", "10-year yield"],
    },
    # CONSUMER
    {
        "channel": "CONSUMER_STRESS",
        "boost": 0.3,
        "keywords": ["consumer spending drop", "retail sales miss",
                     "unemployment rise", "jobs report weak",
                     "layoffs", "recession fear", "slowdown"],
    },
    # TECH
    {
        "channel": "TECH_CYCLE",
        "boost": 0.3,
        "keywords": ["chip shortage", "semiconductor", "ai bubble",
                     "tech selloff", "tech reckoning", "antitrust",
                     "big tech regulation"],
    },
    # VOLATILITY
    {
        "channel": "VOLATILITY_REGIME",
        "boost": 0.3,
        "keywords": ["market crash", "sell-off", "panic", "circuit breaker",
                     "flash crash", "black swan", "market correction",
                     "vix spike", "fear index"],
    },
]


def _load_tavily_key() -> Optional[str]:
    """Get Tavily API key from env or AWS Secrets Manager."""
    key = os.environ.get("TAVILY_API_KEY", "").strip()
    if key:
        return key
    try:
        import boto3
        sm = boto3.client("secretsmanager",
                          region_name=os.environ.get("AWS_REGION", "us-east-1"))
        secret = sm.get_secret_value(SecretId="tfe/tavily/prod")
        data = json.loads(secret["SecretString"])
        return data.get("TAVILY_API_KEY", "").strip() or None
    except Exception:
        return None


def _query_tavily(api_key: str, query: str, max_results: int = 5) -> Dict[str, Any]:
    """Query Tavily search API."""
    import urllib.request
    body = json.dumps({
        "query": query,
        "max_results": max_results,
        "include_answer": "basic",
        "topic": "news",
        "days": 3,
    }).encode()
    req = urllib.request.Request(
        "https://api.tavily.com/search",
        data=body,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
    )
    resp = urllib.request.urlopen(req, timeout=15)
    return json.loads(resp.read())


def _match_signatures(text: str) -> Dict[str, float]:
    """Match text against event signatures. Returns channel→boost map."""
    text_lower = text.lower()
    boosts: Dict[str, float] = {}
    for sig in EVENT_SIGNATURES:
        for kw in sig["keywords"]:
            if kw.lower() in text_lower:
                channel = sig["channel"]
                boost = sig["boost"]
                boosts[channel] = max(boosts.get(channel, 0.0), boost)
                break  # one match per signature is enough
    return boosts


def compute_news_boosts() -> Dict[str, float]:
    """Query news and return severity boosts per G32 channel.

    Returns a dict like {"WAR_GEOPOLITICS": 0.4, "ENERGY_COMMODITY": 0.3}
    for channels that have active news signals. Channels with no news
    signal are not in the dict (implicit 0.0 boost).
    """
    api_key = _load_tavily_key()
    if not api_key:
        print("[EPOCH-NEWS] No Tavily API key — skipping news signal")
        return {}

    queries = [
        "stock market today geopolitical risk oil prices",
        "federal reserve interest rates inflation economy",
        "middle east conflict oil supply energy crisis",
    ]

    all_boosts: Dict[str, float] = {}
    for query in queries:
        try:
            result = _query_tavily(api_key, query, max_results=5)
            # Check the answer
            answer = result.get("answer", "")
            if answer:
                boosts = _match_signatures(answer)
                for ch, b in boosts.items():
                    all_boosts[ch] = max(all_boosts.get(ch, 0.0), b)

            # Check individual results
            for r in result.get("results", []):
                title = r.get("title", "")
                snippet = r.get("content", "")[:500]
                text = f"{title} {snippet}"
                boosts = _match_signatures(text)
                for ch, b in boosts.items():
                    all_boosts[ch] = max(all_boosts.get(ch, 0.0), b)

            time.sleep(0.5)  # rate limit
        except Exception as exc:
            print(f"[EPOCH-NEWS] Tavily query failed: {exc}")

    if all_boosts:
        print(f"[EPOCH-NEWS] News signals detected: {all_boosts}")
    else:
        print("[EPOCH-NEWS] No epoch-relevant news signals detected")

    return all_boosts


def merge_with_auto_severity(
    auto_severities: Dict[str, float],
    news_boosts: Dict[str, float],
) -> Dict[str, float]:
    """Merge news boosts into auto-severity scores.

    News can only INCREASE severity, never decrease it.
    Final score is clamped to [0, 1].
    """
    merged = dict(auto_severities)
    for channel, boost in news_boosts.items():
        if channel in merged:
            merged[channel] = min(1.0, merged[channel] + boost)
        else:
            merged[channel] = min(1.0, boost)
    return merged
