
"""
aurelion_env.py — Real-world environment manager for Aurelion
-------------------------------------------------------------
- Looks for CSV files under ./aurelion_envs/
- Auto-detects numeric columns, uses the first one unless specified
- Normalizes the selected series into [0, 1]
- Persists "last used environment" so sessions can resume automatically

Public API:
    mgr = EnvironmentManager()
    mgr.list_envs() -> List[str]
    s = mgr.load_env("mydata.csv") -> pd.Series (normalized 0..1)
    mgr.info() -> Dict[str, Any]  # current environment metadata
"""

import os
import json
import pandas as pd
from typing import Dict, Any, List, Optional

ENV_DIR = "aurelion_envs"
STATE_DIR = "aurelion_logs"
STATE_PATH = os.path.join(STATE_DIR, "env_state.json")

os.makedirs(ENV_DIR, exist_ok=True)
os.makedirs(STATE_DIR, exist_ok=True)

def _is_numeric(series: pd.Series) -> bool:
    try:
        return pd.api.types.is_numeric_dtype(series)
    except Exception:
        return False

class EnvironmentManager:
    def __init__(self):
        self.current_series: Optional[pd.Series] = None
        self.metadata: Dict[str, Any] = {}
        # Try to restore last environment
        self._restore_last()

    # ---------- Persistence ----------
    def _save_last(self, filename: str, col: str):
        data = {"filename": filename, "column": col}
        with open(STATE_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def _restore_last(self):
        if not os.path.exists(STATE_PATH):
            return
        try:
            with open(STATE_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            fn = data.get("filename")
            col = data.get("column")
            if fn:
                self.load_env(fn, preferred_column=col, persist=False)
        except Exception:
            pass

    # ---------- Core API ----------
    def list_envs(self) -> List[str]:
        files = []
        for name in sorted(os.listdir(ENV_DIR)):
            if name.lower().endswith(".csv"):
                files.append(name)
        return files

    def load_env(self, filename: str, preferred_column: Optional[str] = None, persist: bool = True) -> pd.Series:
        path = os.path.join(ENV_DIR, filename)
        if not os.path.exists(path):
            raise FileNotFoundError(f"No such file in {ENV_DIR}: {filename}")

        df = pd.read_csv(path)
        # Choose column
        col = None
        if preferred_column and preferred_column in df.columns and _is_numeric(df[preferred_column]):
            col = preferred_column
        else:
            for c in df.columns:
                if _is_numeric(df[c]):
                    col = c
                    break
        if col is None:
            raise ValueError("No numeric column found in CSV.")

        s_raw = pd.to_numeric(df[col], errors="coerce").dropna().reset_index(drop=True)
        if len(s_raw) < 3:
            raise ValueError("Series too short after cleaning.")

        # normalize to [0,1]
        mn, mx = float(s_raw.min()), float(s_raw.max())
        rng = mx - mn if mx != mn else 1.0
        s_norm = (s_raw - mn) / rng
        s_norm.name = "signal_norm"

        self.current_series = s_norm
        self.metadata = {
            "filename": filename,
            "column": col,
            "length": int(len(s_norm)),
            "min_raw": mn,
            "max_raw": mx,
            "normalized": True,
        }

        if persist:
            self._save_last(filename, col)

        return s_norm

    def info(self) -> Dict[str, Any]:
        return dict(self.metadata)

if __name__ == "__main__":
    mgr = EnvironmentManager()
    print("Available:", mgr.list_envs())
    if mgr.current_series is not None:
        print("Restored:", mgr.info())
