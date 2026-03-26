#!/usr/bin/env python3
from __future__ import annotations

from typing import Any, Dict, List
from unittest.mock import patch

import pandas as pd

from tfe_advisor_api import get_tfe_recommendation


TEST_SECTORS: List[str] = [
    "Information Technology",
    "Health Care",
    "Financials",
    "Industrials",
    "Utilities",
]


def build_golden_record(sector: str) -> Dict[str, Any]:
    return {
        "status": "PASS",
        "reason": "Structurally Sound",
        "sector": sector,
        "sector_source": "golden_record",
        "metrics": {
            "assigned_tier": "Tier 1",
            "current_ratio": 2.5,
            "current_ratio_floor": 0.75,
            "free_cash_flow": 5_000_000.0,
            "gross_margin": 0.6,
            "gross_profit": 12_000_000.0,
            "long_term_debt": 0.0,
            "market_cap": 250_000_000_000.0,
            "operating_cash_flow": 7_000_000.0,
            "revenues": 20_000_000.0,
        },
    }


def main() -> None:
    pristine_structural_proxy = pd.DataFrame([{"S_UF": 0.75}])

    print("Pristine Cognition Test")
    print("=" * 72)
    print(f"{'Sector':28} {'Decision':12} Reason")
    print("-" * 72)

    for sector in TEST_SECTORS:
        golden_record = build_golden_record(sector)
        with patch("tfe_advisor_api.FundamentalCorpora") as mock_fundamental_corpora:
            mock_fundamental_corpora.return_value.evaluate_ticker.return_value = golden_record
            result = get_tfe_recommendation("TEST", sector, pristine_structural_proxy)
        print(f"{sector:28} {str(result.get('action', '')):12} {str(result.get('reason', ''))}")


if __name__ == "__main__":
    main()
