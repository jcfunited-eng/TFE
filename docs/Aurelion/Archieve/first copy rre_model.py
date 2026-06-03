
from dataclasses import dataclass, field
from typing import List, Optional
import numpy as np
import pandas as pd

@dataclass
class RREConfig:
    ema_windows: List[int] = field(default_factory=lambda: [5, 20, 60])
    vol_lookback: int = 20
    vol_target: float = 0.01
    alpha: float = 0.6
    resonance_threshold: float = 0.2
    allow_short: bool = False
    max_drawdown_brake: float = 0.2
    default_costs_bps: float = 1.0

class RRE:
    def __init__(self, config: RREConfig):
        self.cfg = config

    @staticmethod
    def _ema(arr: np.ndarray, span: int) -> np.ndarray:
        return pd.Series(arr).ewm(span=span, adjust=False).mean().to_numpy()

    def _transform(self, px: pd.Series) -> pd.DataFrame:
        df = pd.DataFrame(index=px.index.copy())
        df['price'] = px.astype(float)
        df['ret'] = df['price'].pct_change().fillna(0.0)
        for w in self.cfg.ema_windows:
            ema = self._ema(df['price'].to_numpy(), span=w)
            df[f'ema_{w}'] = ema
            slope = pd.Series(ema, index=df.index).diff()
            df[f'slope_{w}'] = slope.fillna(0.0)
        return df

    def _relational_coherence(self, df: pd.DataFrame) -> pd.Series:
        slope_cols = [f'slope_{w}' for w in self.cfg.ema_windows]
        S = np.sign(df[slope_cols].to_numpy())
        pos = (S > 0).sum(axis=1)
        neg = (S < 0).sum(axis=1)
        nonzero = np.maximum(1, (S != 0).sum(axis=1))
        raw = (pos - neg) / nonzero
        all_agree = ((pos == nonzero) | (neg == nonzero)) & (nonzero > 1)
        raw = np.clip(raw + 0.15 * np.sign(raw) * all_agree.astype(float), -1.0, 1.0)
        return pd.Series(raw, index=df.index, name='phi_raw')

    def _feedback_memory(self, phi_raw: pd.Series) -> pd.Series:
        a = float(self.cfg.alpha)
        out = np.zeros_like(phi_raw.to_numpy(), dtype=float)
        prev = 0.0
        for i, v in enumerate(phi_raw.to_numpy()):
            out[i] = a * v + (1.0 - a) * prev
            prev = out[i]
        return pd.Series(out, index=phi_raw.index, name='phi')

    def _position_from_phi(self, phi: pd.Series) -> pd.Series:
        th = float(self.cfg.resonance_threshold)
        pos = pd.Series(0.0, index=phi.index)
        pos[phi > th] = 1.0
        if self.cfg.allow_short:
            pos[phi < -th] = -1.0
        return pos

    def _vol_target_scale(self, ret: pd.Series) -> pd.Series:
        lb = int(self.cfg.vol_lookback)
        realized = ret.rolling(lb).std().fillna(method='bfill').replace(0, np.nan).fillna(1e-6)
        s = (self.cfg.vol_target / realized).clip(upper=5.0)
        return s.rename('vol_scale')

    def _apply_brakes(self, equity: pd.Series, position: pd.Series) -> pd.Series:
        peak = equity.cummax()
        dd = (equity / peak - 1.0)
        brake = (dd < -abs(self.cfg.max_drawdown_brake))
        out_pos = position.copy()
        armed = False
        for i in range(len(equity)):
            if brake.iat[i] and not armed:
                armed = True
            if armed:
                out_pos.iat[i] = 0.0
                if equity.iat[i] >= peak.iat[i] - 1e-12:
                    armed = False
        return out_pos

    def backtest(self, price: pd.Series, costs_bps: Optional[float] = None) -> pd.DataFrame:
        if costs_bps is None:
            costs_bps = self.cfg.default_costs_bps

        df = self._transform(price)
        phi_raw = self._relational_coherence(df)
        phi = self._feedback_memory(phi_raw)
        base_pos = self._position_from_phi(phi)

        vol_scale = self._vol_target_scale(df['ret'])
        pos = (base_pos * vol_scale).clip(-1.0 if self.cfg.allow_short else 0.0, 1.5)

        pos_shift = pos.shift().fillna(0.0)
        strat_ret = pos_shift * df['ret']
        turnover = (pos - pos_shift).abs()
        tc = turnover * (costs_bps / 10000.0)
        strat_ret_after_costs = strat_ret - tc
        equity = (1.0 + strat_ret_after_costs).cumprod()

        pos_braked = self._apply_brakes(equity, pos)
        pos_braked_shift = pos_braked.shift().fillna(0.0)
        strat_ret2 = pos_braked_shift * df['ret']
        turnover2 = (pos_braked - pos_braked_shift).abs()
        tc2 = turnover2 * (costs_bps / 10000.0)
        equity2 = (1.0 + (strat_ret2 - tc2)).cumprod()

        out = pd.DataFrame({
            'price': df['price'],
            'ret': df['ret'],
            'phi_raw': phi_raw,
            'phi': phi,
            'position_base': base_pos,
            'vol_scale': vol_scale,
            'position': pos,
            'position_braked': pos_braked,
            'equity_prebrake': equity,
            'equity': equity2
        })
        peak = out['equity'].cummax()
        out['drawdown'] = out['equity'] / peak - 1.0
        return out

    @staticmethod
    def load_price_from_csv(path: str, date_col: Optional[str] = None,
                            price_col_candidates: Optional[List[str]] = None) -> pd.Series:
        if price_col_candidates is None:
            price_col_candidates = ['Close', 'Adj Close', 'AdjClose', 'PX_LAST', 'close', 'adj_close', 'Price']

        df = pd.read_csv(path)
        if date_col is None:
            for c in df.columns:
                try:
                    pd.to_datetime(df[c])
                    date_col = c
                    break
                except Exception:
                    continue
        if date_col is None:
            idx = pd.RangeIndex(len(df))
        else:
            idx = pd.to_datetime(df[date_col])

        price_col = None
        for c in price_col_candidates:
            if c in df.columns:
                price_col = c
                break
        if price_col is None:
            candidates = [c for c in df.columns if c != date_col]
            num_counts = {c: pd.to_numeric(df[c], errors='coerce').notna().sum() for c in candidates}
            price_col = max(num_counts, key=num_counts.get)

        price = pd.to_numeric(df[price_col], errors='coerce')
        s = pd.Series(price.values, index=idx, name='price').dropna()
        s = s.sort_index()
        return s
