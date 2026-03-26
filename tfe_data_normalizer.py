#!/usr/bin/env python3
from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import Any, Callable, TypeVar

import psycopg2
import requests
from openai import OpenAI
from tavily import TavilyClient


T = TypeVar("T")

PGHOST = os.getenv("PGHOST")
PGDATABASE = os.getenv("PGDATABASE")
PGUSER = os.getenv("PGUSER")
PGPASSWORD = os.getenv("PGPASSWORD")
POLYGON_API_KEY = os.getenv("MASSIVE_API_KEY") or os.getenv("POLYGON_API_KEY")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-5.4-mini")

UNKNOWN_SECTOR = "Unknown"
MISSING_SIC = "<<MISSING_SIC_DESCRIPTION>>"
RETRY_SLEEP_SECONDS = 5
DEFAULT_BATCH_SIZE = int(os.getenv("TFE_NORMALIZER_BATCH_SIZE", "6000"))
PROGRESS_INTERVAL = 500
MAX_ATTEMPTS = 3
APPROVED_EPOCH_SECTORS = [
    "Communication Services",
    "Consumer Discretionary",
    "Consumer Staples",
    "Energy",
    "Financials",
    "Health Care",
    "Industrials",
    "Information Technology",
    "Materials",
    "Real Estate",
    "Utilities",
    "Unknown",
]


@dataclass(frozen=True)
class UnknownRow:
    ticker: str
    market_cap: float


@dataclass(frozen=True)
class CandidateContext:
    ticker: str
    company_name: str
    raw_sic: str
    market_cap: float


@dataclass(frozen=True)
class EnrichmentRecord:
    ticker: str
    sector: str
    market_cap: float


def get_db_connection():
    return psycopg2.connect(
        host=PGHOST,
        database=PGDATABASE,
        user=PGUSER,
        password=PGPASSWORD,
    )


def _with_retry(label: str, fn: Callable[..., T], *args: Any, **kwargs: Any) -> T:
    try:
        return fn(*args, **kwargs)
    except Exception as first_exc:
        print(f"{label} transient failure: {first_exc}; retrying in {RETRY_SLEEP_SECONDS}s")
        time.sleep(RETRY_SLEEP_SECONDS)
        return fn(*args, **kwargs)


def _tavily_client() -> TavilyClient:
    if not TAVILY_API_KEY:
        raise RuntimeError("Missing TAVILY_API_KEY.")
    return TavilyClient(api_key=TAVILY_API_KEY)


def _openai_client() -> OpenAI:
    if not OPENAI_API_KEY:
        raise RuntimeError("Missing OPENAI_API_KEY.")
    return OpenAI(api_key=OPENAI_API_KEY)


def count_unknown_rows() -> int:
    query = "SELECT COUNT(*) FROM l5_fundamentals_normalized WHERE sector = 'Unknown'"
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query)
            return int(cur.fetchone()[0])


def fetch_unknown_rows(limit: int) -> list[UnknownRow]:
    query = """
        SELECT ticker, COALESCE(market_cap, 0)
        FROM l5_fundamentals_normalized
        WHERE sector = 'Unknown'
          AND COALESCE(attempt_count, 0) < %s
        ORDER BY COALESCE(market_cap, 0) DESC, updated_at ASC NULLS FIRST, ticker ASC
        LIMIT %s
    """
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, (MAX_ATTEMPTS, limit))
            return [
                UnknownRow(ticker=str(row[0]).strip(), market_cap=float(row[1] or 0.0))
                for row in cur.fetchall()
                if str(row[0]).strip()
            ]


def _polygon_payload(ticker: str) -> dict[str, Any]:
    response = requests.get(
        f"https://api.polygon.io/v3/reference/tickers/{ticker}",
        params={"apiKey": POLYGON_API_KEY},
        timeout=30,
    )
    response.raise_for_status()
    payload = response.json()
    results = payload.get("results")
    return results if isinstance(results, dict) else {}


def _candidate_context(row: UnknownRow) -> CandidateContext:
    company_name = ""
    raw_sic = MISSING_SIC
    market_cap = row.market_cap

    try:
        payload = _polygon_payload(row.ticker)
    except Exception as exc:
        payload = {}
        print(f"Massive fetch failed for {row.ticker}: {exc}")

    if payload:
        company_name = str(payload.get("name") or "").strip()
        raw_sic = str(payload.get("sic_description") or "").strip() or MISSING_SIC
        try:
            market_cap = float(payload.get("market_cap") or market_cap or 0.0)
        except Exception:
            market_cap = float(market_cap or 0.0)

    return CandidateContext(
        ticker=row.ticker,
        company_name=company_name,
        raw_sic=raw_sic,
        market_cap=market_cap,
    )


def _search_context(context: CandidateContext) -> list[dict[str, Any]]:
    query = (
        f"{context.ticker} {context.company_name} "
        f"SIC {context.raw_sic} "
        "core business operations sector"
    )
    response = _tavily_client().search(
        query=query.strip(),
        search_depth="advanced",
        max_results=5,
        include_answer=False,
        include_raw_content=False,
    )
    results = response.get("results")
    return list(results) if isinstance(results, list) else []


def _classification_prompt(context: CandidateContext, snippets: list[dict[str, Any]]) -> str:
    rendered_snippets: list[str] = []
    for index, item in enumerate(snippets, start=1):
        title = str(item.get("title") or "").strip()
        content = str(item.get("content") or "").strip()
        url = str(item.get("url") or "").strip()
        rendered_snippets.append(
            f"Result {index}\nTitle: {title}\nURL: {url}\nSnippet: {content}"
        )

    snippets_block = "\n\n".join(rendered_snippets) if rendered_snippets else "No search results."
    sectors = ", ".join(APPROVED_EPOCH_SECTORS)
    return (
        f"Ticker: {context.ticker}\n"
        f"Company Name: {context.company_name or 'Unknown'}\n"
        f"Polygon SIC Description: {context.raw_sic}\n\n"
        f"Approved Epoch sectors: {sectors}\n\n"
        "Read the evidence and classify the company's core business into exactly one approved sector. "
        "Return ONLY the sector name. If the data is ambiguous, insufficient, mixed, or unclear, "
        "return ONLY Unknown. Do not guess.\n\n"
        f"{snippets_block}"
    )


def _classify_with_openai(context: CandidateContext, snippets: list[dict[str, Any]]) -> str:
    response = _openai_client().responses.create(
        model=OPENAI_MODEL,
        input=_classification_prompt(context=context, snippets=snippets),
    )
    output = str(getattr(response, "output_text", "") or "").strip()
    return output if output in APPROVED_EPOCH_SECTORS else UNKNOWN_SECTOR


def write_enrichment(record: EnrichmentRecord) -> None:
    query = """
        UPDATE l5_fundamentals_normalized
        SET sector = %s,
            market_cap = %s,
            last_attempt_at = CURRENT_TIMESTAMP,
            attempt_count = COALESCE(attempt_count, 0) + 1,
            updated_at = CURRENT_TIMESTAMP
        WHERE ticker = %s
    """
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, (record.sector, record.market_cap, record.ticker))
        conn.commit()


def process_unknown_batch(limit: int = DEFAULT_BATCH_SIZE) -> dict[str, int]:
    before_unknown = count_unknown_rows()
    rows = fetch_unknown_rows(limit)
    if not rows:
        print("No Unknown-sector rows available below the attempt limit.")
        return {
            "before_unknown": before_unknown,
            "processed": 0,
            "rescued": 0,
            "remaining_unknown": before_unknown,
        }

    print(f"Starting brute-force AI enrichment for {len(rows)} Unknown-sector tickers...")

    rescued = 0
    confirmed_unknown = 0

    for index, row in enumerate(rows, start=1):
        context = _candidate_context(row)
        try:
            snippets = _with_retry(f"Tavily {row.ticker}", _search_context, context)
            sector = _with_retry(f"OpenAI {row.ticker}", _classify_with_openai, context, snippets)
        except Exception as exc:
            print(f"AI enrichment failed for {row.ticker}: {exc}")
            sector = UNKNOWN_SECTOR

        if sector == UNKNOWN_SECTOR:
            confirmed_unknown += 1
        else:
            rescued += 1

        write_enrichment(
            EnrichmentRecord(
                ticker=row.ticker,
                sector=sector,
                market_cap=context.market_cap,
            )
        )

        if index % PROGRESS_INTERVAL == 0:
            print(f"PROGRESS processed={index} rescued={rescued} confirmed_unknown={confirmed_unknown}")

    remaining_unknown = count_unknown_rows()

    print("Brute-force AI enrichment complete.")
    print(f"Processed: {len(rows)}")
    print(f"Rescued this batch: {rescued}")
    print(f"Confirmed Unknown this batch: {confirmed_unknown}")
    print(f"Unknown before: {before_unknown}")
    print(f"Unknown after: {remaining_unknown}")

    return {
        "before_unknown": before_unknown,
        "processed": len(rows),
        "rescued": rescued,
        "remaining_unknown": remaining_unknown,
    }


if __name__ == "__main__":
    process_unknown_batch(limit=DEFAULT_BATCH_SIZE)
