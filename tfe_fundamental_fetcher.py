#!/usr/bin/env python3
from __future__ import annotations

import os
import threading
import time
from typing import Any, Dict, Iterable, Optional

import pandas as pd
import requests
import yfinance as yf

try:
    from dotenv import load_dotenv

    load_dotenv()
except Exception:
    pass


class FundamentalCorpora:
    _yahoo_lock = threading.Lock()
    _yahoo_session: Optional[requests.Session] = None
    _last_yahoo_call_monotonic = 0.0

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = "https://api.polygon.io",
        timeout_seconds: int = 30,
        max_retries: int = 4,
        base_backoff_seconds: float = 2.0,
        session: Optional[requests.Session] = None,
    ) -> None:
        self._api_key = (
            api_key
            or os.getenv("POLYGON_API_KEY")
            or os.getenv("MASSIVE_API_KEY")
            or ""
        ).strip()
        if not self._api_key:
            raise RuntimeError("POLYGON_API_KEY is required for FundamentalCorpora.")

        self._base_url = base_url.rstrip("/")
        self._timeout_seconds = max(1, int(timeout_seconds))
        self._max_retries = max(0, int(max_retries))
        self._base_backoff_seconds = max(0.1, float(base_backoff_seconds))
        self._session = session or requests.Session()

    def _sleep_for_attempt(self, attempt: int, retry_after: Optional[str] = None) -> None:
        if retry_after:
            try:
                time.sleep(max(self._base_backoff_seconds, float(retry_after)))
                return
            except Exception:
                pass
        time.sleep(self._base_backoff_seconds * (2 ** attempt))

    def _get(self, path: str, params: Dict[str, Any]) -> Dict[str, Any]:
        url = f"{self._base_url}{path}"
        request_params = dict(params)
        request_params["apiKey"] = self._api_key

        last_error: Optional[str] = None
        for attempt in range(self._max_retries + 1):
            try:
                response = self._session.get(url, params=request_params, timeout=self._timeout_seconds)
            except requests.RequestException as exc:
                last_error = f"{type(exc).__name__}: {exc}"
                if attempt >= self._max_retries:
                    raise RuntimeError(f"Financials request failed: {last_error}") from exc
                self._sleep_for_attempt(attempt)
                continue

            if response.status_code == 200:
                return response.json()

            last_error = f"HTTP {response.status_code}: {response.text[:240]}"
            if response.status_code in {429, 500, 502, 503, 504} and attempt < self._max_retries:
                self._sleep_for_attempt(attempt, response.headers.get("Retry-After"))
                continue

            raise RuntimeError(f"Financials request failed: {last_error}")

        raise RuntimeError(f"Financials request failed: {last_error or 'unknown error'}")

    @classmethod
    def _get_yahoo_session(cls) -> requests.Session:
        if cls._yahoo_session is None:
            session = requests.Session()
            session.headers.update(
                {
                    "User-Agent": (
                        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                        "(KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
                    )
                }
            )
            cls._yahoo_session = session
        return cls._yahoo_session

    @staticmethod
    def _extract_value(payload: Dict[str, Any], *path: str) -> Optional[float]:
        current: Any = payload
        for part in path:
            if not isinstance(current, dict):
                return None
            current = current.get(part)
        if not isinstance(current, dict):
            return None
        value = current.get("value")
        if value is None:
            return None
        try:
            return float(value)
        except Exception:
            return None

    @staticmethod
    def _coerce_numeric(value: Any) -> Optional[float]:
        try:
            if value is None or (isinstance(value, str) and not value.strip()):
                return None
            number = float(value)
            if pd.isna(number):
                return None
            return number
        except Exception:
            return None

    def _lookup_frame_value(self, frame: Any, labels: Iterable[str]) -> Optional[float]:
        if not isinstance(frame, pd.DataFrame) or frame.empty:
            return None

        normalized_labels = [str(label).strip().lower() for label in labels]
        index_map = {str(idx).strip().lower(): idx for idx in frame.index}
        for normalized_label in normalized_labels:
            if normalized_label not in index_map:
                continue
            row = frame.loc[index_map[normalized_label]]
            if isinstance(row, pd.Series):
                for value in row.tolist():
                    numeric = self._coerce_numeric(value)
                    if numeric is not None:
                        return numeric

        column_map = {str(col).strip().lower(): col for col in frame.columns}
        for normalized_label in normalized_labels:
            if normalized_label not in column_map:
                continue
            column = frame[column_map[normalized_label]]
            if isinstance(column, pd.Series):
                for value in column.tolist():
                    numeric = self._coerce_numeric(value)
                    if numeric is not None:
                        return numeric

        return None

    def _latest_financials(self, ticker: str) -> Dict[str, Any]:
        payload = self._get(
            "/vX/reference/financials",
            {
                "ticker": ticker.upper().strip(),
                "limit": 1,
                "sort": "filing_date",
                "order": "desc",
            },
        )
        results = payload.get("results")
        if not isinstance(results, list) or not results:
            raise RuntimeError(f"No financial filings returned for {ticker}.")
        latest = results[0]
        financials = latest.get("financials")
        if not isinstance(financials, dict):
            raise RuntimeError(f"Financial payload missing for {ticker}.")
        return financials

    def _get_market_cap(self, ticker: str) -> float:
        try:
            payload = self._get(f"/v3/reference/tickers/{ticker.upper().strip()}", {})
            results = payload.get("results", {})
            mcap = results.get("market_cap")
            if mcap is not None:
                return float(mcap)
        except Exception:
            pass
        return 0.0

    def _polygon_sector_metadata(self, ticker: str) -> Dict[str, str]:
        try:
            payload = self._get(f"/v3/reference/tickers/{ticker.upper().strip()}", {})
        except Exception:
            return {}
        results = payload.get("results", {})
        sector = str(results.get("sic_description") or "").strip()
        if not sector:
            return {}
        return {
            "sector": sector,
            "industry": "",
            "source": "polygon_sic",
        }

    def _get_yfinance_payload(self, ticker: str) -> Dict[str, Any]:
        last_error: Optional[str] = None
        for attempt in range(self._max_retries + 1):
            try:
                with self.__class__._yahoo_lock:
                    now = time.monotonic()
                    wait_seconds = 0.1 - (now - self.__class__._last_yahoo_call_monotonic)
                    if wait_seconds > 0:
                        time.sleep(wait_seconds)

                    yahoo_session = self.__class__._get_yahoo_session()
                    yf_ticker = yf.Ticker(ticker, session=yahoo_session)
                    info_prop = getattr(yf_ticker, "info", None)
                    financials = getattr(yf_ticker, "financials", None)
                    income_stmt = getattr(yf_ticker, "income_stmt", None)
                    cashflow = getattr(yf_ticker, "cashflow", None)
                    cash_flow = getattr(yf_ticker, "cash_flow", None)
                    self.__class__._last_yahoo_call_monotonic = time.monotonic()

                return {
                    "status": "ok",
                    "info": info_prop if isinstance(info_prop, dict) else {},
                    "financials": financials if isinstance(financials, pd.DataFrame) else pd.DataFrame(),
                    "income_stmt": income_stmt if isinstance(income_stmt, pd.DataFrame) else pd.DataFrame(),
                    "cashflow": cashflow if isinstance(cashflow, pd.DataFrame) else pd.DataFrame(),
                    "cash_flow": cash_flow if isinstance(cash_flow, pd.DataFrame) else pd.DataFrame(),
                }
            except Exception as exc:
                self.__class__._last_yahoo_call_monotonic = time.monotonic()
                last_error = f"{type(exc).__name__}: {exc}"
                if attempt >= self._max_retries:
                    break
                time.sleep(max(0.5, self._base_backoff_seconds * (attempt + 1)))

        return {
            "status": "data_unavailable",
            "error": last_error or "unknown yfinance error",
            "info": {},
            "financials": pd.DataFrame(),
            "income_stmt": pd.DataFrame(),
            "cashflow": pd.DataFrame(),
            "cash_flow": pd.DataFrame(),
        }

    def _resolve_sector(
        self,
        *,
        ticker: str,
        sector_hint: Optional[str],
        yfinance_payload: Optional[Dict[str, Any]],
    ) -> Dict[str, str]:
        hint_text = str(sector_hint or "").strip()
        if hint_text and hint_text.lower() != "unknown":
            return {"sector": hint_text, "industry": "", "source": "hint"}

        polygon_meta = self._polygon_sector_metadata(ticker)
        if polygon_meta.get("sector"):
            return polygon_meta

        yahoo_info = (yfinance_payload or {}).get("info") or {}
        yahoo_sector = str(yahoo_info.get("sector") or "").strip()
        yahoo_industry = str(yahoo_info.get("industry") or "").strip()
        if yahoo_sector or yahoo_industry:
            return {
                "sector": yahoo_sector or yahoo_industry,
                "industry": yahoo_industry,
                "source": "yfinance_info",
            }

        return {"sector": "Unknown", "industry": "", "source": "unresolved"}

    def _resolve_gross_profit(
        self,
        *,
        gross_profit: Optional[float],
        revenues: Optional[float],
        yfinance_payload: Optional[Dict[str, Any]],
    ) -> tuple[Optional[float], Optional[float]]:
        payload = yfinance_payload or {}
        financials = payload.get("financials")
        income_stmt = payload.get("income_stmt")

        if gross_profit is None:
            gross_profit = self._lookup_frame_value(financials, {"Gross Profit"})
        if gross_profit is None:
            gross_profit = self._lookup_frame_value(income_stmt, {"Gross Profit"})

        if revenues is None:
            revenues = self._lookup_frame_value(financials, {"Total Revenue", "Revenue", "Operating Revenue"})
        if revenues is None:
            revenues = self._lookup_frame_value(income_stmt, {"Total Revenue", "Revenue", "Operating Revenue"})

        cost_of_revenue = self._lookup_frame_value(income_stmt, {"Cost Of Revenue", "Cost of Revenue"})
        if cost_of_revenue is None:
            cost_of_revenue = self._lookup_frame_value(financials, {"Cost Of Revenue", "Cost of Revenue"})

        if gross_profit is None and revenues is not None and cost_of_revenue is not None:
            gross_profit = revenues - cost_of_revenue

        return gross_profit, revenues

    def _heal_metrics_with_yfinance(
        self,
        *,
        gross_profit: Optional[float],
        revenues: Optional[float],
        operating_cash_flow: Optional[float],
        market_cap: float,
        yfinance_payload: Optional[Dict[str, Any]],
    ) -> Dict[str, Optional[float]]:
        payload = yfinance_payload or {}
        cashflow = payload.get("cashflow")
        cash_flow = payload.get("cash_flow")
        info = payload.get("info") or {}

        gross_profit, revenues = self._resolve_gross_profit(
            gross_profit=gross_profit,
            revenues=revenues,
            yfinance_payload=yfinance_payload,
        )

        if operating_cash_flow is None:
            operating_cash_flow = self._lookup_frame_value(
                cashflow,
                {
                    "Operating Cash Flow",
                    "Cash Flow From Continuing Operating Activities",
                    "Total Cash From Operating Activities",
                },
            )
        if operating_cash_flow is None:
            operating_cash_flow = self._lookup_frame_value(
                cash_flow,
                {
                    "Operating Cash Flow",
                    "Cash Flow From Continuing Operating Activities",
                    "Total Cash From Operating Activities",
                },
            )

        if market_cap <= 0:
            market_cap_value = self._coerce_numeric(info.get("marketCap"))
            if market_cap_value is not None:
                market_cap = market_cap_value

        return {
            "gross_profit": gross_profit,
            "revenues": revenues,
            "operating_cash_flow": operating_cash_flow,
            "market_cap": market_cap,
        }

    def evaluate_ticker(
        self,
        ticker: str,
        asset_class: str = "equity",
        sector_hint: Optional[str] = None,
    ) -> Dict[str, Any]:
        normalized_asset_class = str(asset_class).strip().lower()

        if normalized_asset_class == "crypto":
            return {
                "status": "PASS",
                "reason": "Crypto bypassed fundamental SEC checks",
                "sector": str(sector_hint or "Unknown") or "Unknown",
            }
        if normalized_asset_class != "equity":
            return {"status": "FAIL", "reason": f"Unsupported asset class: {asset_class}", "sector": "Unknown"}

        polygon_available = True
        try:
            financials = self._latest_financials(ticker)
            market_cap = self._get_market_cap(ticker)
        except Exception:
            polygon_available = False
            financials = {}
            market_cap = 0.0

        if polygon_available:
            current_assets = self._extract_value(financials, "balance_sheet", "current_assets")
            current_liabilities = self._extract_value(financials, "balance_sheet", "current_liabilities")
            long_term_debt = self._extract_value(financials, "balance_sheet", "long_term_debt")
            operating_cash_flow = self._extract_value(
                financials,
                "cash_flow_statement",
                "net_cash_flow_from_operating_activities",
            )
            capital_expenditure = self._extract_value(financials, "cash_flow_statement", "capital_expenditure")
            gross_profit = self._extract_value(financials, "income_statement", "gross_profit")
            revenues = self._extract_value(financials, "income_statement", "revenues")
        else:
            current_assets = None
            current_liabilities = None
            long_term_debt = None
            operating_cash_flow = None
            capital_expenditure = None
            gross_profit = None
            revenues = None

        # Yahoo Finance fallback — used when Polygon has no filings at all,
        # or when individual metrics are missing from Polygon data.
        yfinance_payload: Optional[Dict[str, Any]] = None
        needs_yfinance = (
            not polygon_available
            or gross_profit is None
            or revenues is None
            or operating_cash_flow is None
        )
        if needs_yfinance:
            yfinance_payload = self._get_yfinance_payload(ticker)
            if str(yfinance_payload.get("status")) != "data_unavailable":
                healed = self._heal_metrics_with_yfinance(
                    gross_profit=gross_profit,
                    revenues=revenues,
                    operating_cash_flow=operating_cash_flow,
                    market_cap=market_cap,
                    yfinance_payload=yfinance_payload,
                )
                gross_profit = healed["gross_profit"]
                revenues = healed["revenues"]
                operating_cash_flow = healed["operating_cash_flow"]
                market_cap = healed["market_cap"] if healed["market_cap"] is not None else market_cap

                # Fill balance sheet gaps from yfinance when Polygon had nothing
                if current_assets is None or current_liabilities is None:
                    info = (yfinance_payload or {}).get("info") or {}
                    if current_assets is None:
                        current_assets = self._coerce_numeric(info.get("totalCurrentAssets"))
                    if current_liabilities is None:
                        current_liabilities = self._coerce_numeric(info.get("totalCurrentLiabilities"))
                    if long_term_debt is None:
                        long_term_debt = self._coerce_numeric(info.get("longTermDebt"))
                    if capital_expenditure is None:
                        # yfinance reports capex as negative
                        raw_capex = self._coerce_numeric(info.get("capitalExpenditures"))
                        if raw_capex is not None:
                            capital_expenditure = abs(raw_capex)

        sector_meta = self._resolve_sector(
            ticker=ticker,
            sector_hint=sector_hint,
            yfinance_payload=yfinance_payload,
        )
        resolved_sector = sector_meta["sector"]

        required_metrics = {
            "current_assets": current_assets,
            "current_liabilities": current_liabilities,
            "operating_cash_flow": operating_cash_flow,
            "gross_profit": gross_profit,
            "revenues": revenues,
        }
        missing = [name for name, value in required_metrics.items() if value is None]
        if missing:
            return {
                "status": "FAIL",
                "reason": f"Missing financial metric(s): {', '.join(missing)}",
                "sector": resolved_sector,
                "sector_source": sector_meta["source"],
                "metrics": {
                    "gross_profit": gross_profit,
                    "revenues": revenues,
                    "operating_cash_flow": operating_cash_flow,
                },
            }

        if current_liabilities <= 0:
            return {
                "status": "FAIL",
                "reason": "Domain A Failure: current_liabilities missing or nonpositive",
                "sector": resolved_sector,
                "sector_source": sector_meta["source"],
            }

        if revenues <= 0:
            return {
                "status": "FAIL",
                "reason": "Domain C Failure: revenues missing or nonpositive",
                "sector": resolved_sector,
                "sector_source": sector_meta["source"],
            }

        current_ratio = current_assets / current_liabilities
        effective_capex = capital_expenditure if capital_expenditure is not None else 0.0
        free_cash_flow = operating_cash_flow - effective_capex
        gross_margin = gross_profit / revenues
        effective_debt = long_term_debt if long_term_debt is not None else 0.0

        if market_cap >= 200_000_000_000:
            assigned_tier = "Tier 1"
            current_ratio_floor = 0.75
        elif market_cap >= 2_000_000_000:
            assigned_tier = "Tier 2"
            current_ratio_floor = 1.0
        else:
            assigned_tier = "Tier 3"
            current_ratio_floor = 1.5

        if current_ratio <= current_ratio_floor:
            return {
                "status": "FAIL",
                "reason": f"Domain A Failure: {assigned_tier} requires Current Ratio > {current_ratio_floor}",
                "sector": resolved_sector,
                "sector_source": sector_meta["source"],
                "metrics": {
                    "gross_profit": gross_profit,
                    "revenues": revenues,
                    "operating_cash_flow": operating_cash_flow,
                },
            }

        if free_cash_flow <= 0:
            return {
                "status": "FAIL",
                "reason": "Domain B Failure: Free Cash Flow <= 0",
                "sector": resolved_sector,
                "sector_source": sector_meta["source"],
                "metrics": {
                    "gross_profit": gross_profit,
                    "revenues": revenues,
                    "operating_cash_flow": operating_cash_flow,
                },
            }

        if gross_margin <= 0:
            return {
                "status": "FAIL",
                "reason": "Domain C Failure: Gross Margin <= 0",
                "sector": resolved_sector,
                "sector_source": sector_meta["source"],
                "metrics": {
                    "gross_profit": gross_profit,
                    "revenues": revenues,
                    "operating_cash_flow": operating_cash_flow,
                },
            }

        return {
            "status": "PASS",
            "reason": "Structurally Sound",
            "sector": resolved_sector,
            "sector_source": sector_meta["source"],
            "metrics": {
                "market_cap": market_cap,
                "assigned_tier": assigned_tier,
                "current_ratio_floor": current_ratio_floor,
                "current_ratio": current_ratio,
                "free_cash_flow": free_cash_flow,
                "gross_margin": gross_margin,
                "gross_profit": gross_profit,
                "revenues": revenues,
                "operating_cash_flow": operating_cash_flow,
                "long_term_debt": effective_debt,
            },
        }
