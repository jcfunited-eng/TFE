#!/usr/bin/env python3
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict


ACTIVE_EPOCHS: Dict[str, float] = {
    "RATES_PRESSURE": 0.8,
    "CONSUMER_STRESS": 0.6,
    "WAR_GEOPOLITICS": 0.7,
}


SECTOR_SENSITIVITY_MATRIX: Dict[str, Dict[str, float]] = {
    "Communication Services": {
        "RATES_PRESSURE": -0.2,
        "CONSUMER_STRESS": -0.3,
        "WAR_GEOPOLITICS": -0.1,
    },
    "Consumer Discretionary": {
        "RATES_PRESSURE": -0.5,
        "CONSUMER_STRESS": -1.0,
        "WAR_GEOPOLITICS": -0.2,
    },
    "Consumer Staples": {
        "RATES_PRESSURE": 0.1,
        "CONSUMER_STRESS": 0.4,
        "WAR_GEOPOLITICS": -0.1,
    },
    "Energy": {
        "RATES_PRESSURE": 0.0,
        "CONSUMER_STRESS": -0.2,
        "WAR_GEOPOLITICS": 0.9,
    },
    "Financials": {
        "RATES_PRESSURE": 0.2,
        "CONSUMER_STRESS": -0.5,
        "WAR_GEOPOLITICS": -0.2,
    },
    "Health Care": {
        "RATES_PRESSURE": 0.0,
        "CONSUMER_STRESS": 0.3,
        "WAR_GEOPOLITICS": 0.1,
    },
    "Industrials": {
        "RATES_PRESSURE": -0.2,
        "CONSUMER_STRESS": -0.3,
        "WAR_GEOPOLITICS": 0.2,
    },
    "Information Technology": {
        "RATES_PRESSURE": -0.4,
        "CONSUMER_STRESS": -0.3,
        "WAR_GEOPOLITICS": 0.0,
    },
    "Materials": {
        "RATES_PRESSURE": -0.1,
        "CONSUMER_STRESS": -0.3,
        "WAR_GEOPOLITICS": 0.3,
    },
    "Real Estate": {
        "RATES_PRESSURE": -1.0,
        "CONSUMER_STRESS": -0.5,
        "WAR_GEOPOLITICS": 0.0,
    },
    "Utilities": {
        "RATES_PRESSURE": -0.3,
        "CONSUMER_STRESS": 0.2,
        "WAR_GEOPOLITICS": 0.1,
    },
}


@dataclass(frozen=True)
class EpochCorpora:
    active_epochs: Dict[str, float] = None  # type: ignore[assignment]
    sector_sensitivity_matrix: Dict[str, Dict[str, float]] = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        object.__setattr__(self, "active_epochs", dict(ACTIVE_EPOCHS) if self.active_epochs is None else dict(self.active_epochs))
        object.__setattr__(
            self,
            "sector_sensitivity_matrix",
            dict(SECTOR_SENSITIVITY_MATRIX) if self.sector_sensitivity_matrix is None else dict(self.sector_sensitivity_matrix),
        )

    def evaluate_sector_epoch(self, sector: str) -> dict:
        normalized_sector = str(sector).strip()
        if normalized_sector not in self.sector_sensitivity_matrix:
            return {"status": "FAIL", "reason": f"Unknown sector: {sector}"}

        sector_vector = self.sector_sensitivity_matrix[normalized_sector]
        epoch_pressure = sum(
            float(self.active_epochs[epoch_name]) * float(sector_vector.get(epoch_name, 0.0))
            for epoch_name in self.active_epochs
        )

        if epoch_pressure <= -0.5:
            return {"status": "FAIL", "reason": f"Adverse Epoch Pressure: {epoch_pressure}"}

        return {
            "status": "PASS",
            "reason": "Epoch Favorable/Neutral",
            "epoch_pressure": epoch_pressure,
        }


if __name__ == "__main__":
    corpora = EpochCorpora()
    print("Real Estate", corpora.evaluate_sector_epoch("Real Estate"))
    print("Energy", corpora.evaluate_sector_epoch("Energy"))
