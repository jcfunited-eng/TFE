"""
tfe_market_data.py

Thin wrapper exposing a singleton UnifiedMarketDataService
to the rest of the TFE system.

This corrected version:
- Does NOT pass unsupported constructor arguments.
- Uses the new UnifiedMarketDataService() exactly as defined.
- Avoids TA logic.
- Keeps the TFE architecture stable and UF-Spec compliant.
"""

from __future__ import annotations

import logging
from typing import Optional

from unified_market_data_service import UnifiedMarketDataService

log = logging.getLogger(__name__)

# Singleton instance
_UNIFIED_MDS: Optional[UnifiedMarketDataService] = None


def get_unified_market_data() -> UnifiedMarketDataService:
    """
    Return the cached UnifiedMarketDataService.
    Create it on first use.
    """
    global _UNIFIED_MDS

    if _UNIFIED_MDS is None:
        try:
            _UNIFIED_MDS = UnifiedMarketDataService()
        except Exception as exc:
            raise RuntimeError(
                f"Failed to initialize UnifiedMarketDataService: {exc}"
            )

    return _UNIFIED_MDS
