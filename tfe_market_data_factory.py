"""
tfe_market_data_factory.py
---------------------------------------------
Factory for constructing a MarketDataService backend.

CRITICAL FIX:
    This version explicitly loads the .env file using python-dotenv.
    Without this, MASSIVE_API_KEY and ALPACA keys DO NOT EXIST
    inside Python and all providers will fail.

Behavior:
    1. Load .env at startup.
    2. Determine provider (config override → env → default).
    3. Construct Massive or Alpaca backend.

"""


from __future__ import annotations

import os
from typing import Mapping, Any

from dotenv import load_dotenv

# Load .env ONCE and FOR ALL
load_dotenv()

from tfe_market_data_service import MarketDataService
from massive_market_data_service import MassiveMarketDataService
from alpaca_market_data_service import AlpacaMarketDataService


def get_market_data_service(config: Mapping[str, Any] | None = None) -> MarketDataService:
    """
    Construct a MarketDataService backend according to configuration rules.

    Precedence:
        1. config["provider"] if supplied
        2. environment variable TFE_MARKET_PROVIDER
        3. default to "massive"
    """
    provider = None

    if config and "provider" in config:
        provider = config["provider"]
    elif "TFE_MARKET_PROVIDER" in os.environ:
        provider = os.environ["TFE_MARKET_PROVIDER"]
    else:
        provider = "massive"

    provider = provider.lower().strip()

    if provider == "massive":
        return MassiveMarketDataService()

    if provider == "alpaca":
        return AlpacaMarketDataService()

    raise ValueError(f"Unknown TFE market data provider: {provider!r}")
