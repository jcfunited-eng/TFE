#!/usr/bin/env python3
"""
tfe_epoch_library.py
L5 Epoch Library — to spec (TFE_Specification_v3_0 §Epoch Source Ingestion
through §Epoch-Symbol Coupling).

Implements:
  1. Event normalization  — raw source event → ν_u tuple
  2. Admission scoring    — Π_epoch(u) determines library entry
  3. Epoch objects         — ε_k with severity, confidence, persistence,
                            sphere-of-impact vector, temporal decay
  4. Epoch mosaic          — Ξ_t = Σ ω_k(t) ξ_k  (32-channel field)
  5. G32 Coordinator       — maintain mosaic, resolve conflicts,
                            project to sector/industry/company
  6. Epoch-symbol coupling — Ω_epoch(s,t) per-symbol pressure

No ML. Deterministic. All event objects carry provenance.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import numpy as np


# ═══════════════════════════════════════════════════════════════════════════
# 1. Constants — 32 sphere-of-impact channels
# ═══════════════════════════════════════════════════════════════════════════

SPHERE_CHANNELS = [
    "RATES_PRESSURE",        # 0
    "CONSUMER_STRESS",       # 1
    "WAR_GEOPOLITICS",       # 2
    "ENERGY_COMMODITY",      # 3
    "TECH_CYCLE",            # 4
    "CURRENCY_FX",           # 5
    "FISCAL_INFRA",          # 6
    "VOLATILITY_REGIME",     # 7
    "LABOR_PRESSURE",        # 8
    "SUPPLY_CHAIN",          # 9
    "REGULATION",            # 10
    "CREDIT_STRESS",         # 11
    "BUILDING_CYCLE",        # 12
    "LOGISTICS",             # 13
    "HEALTHCARE_POLICY",     # 14
    "TRADE_WAR",             # 15
    "PANDEMIC",              # 16
    "EARNINGS_SEASON",       # 17
    "SECTOR_ROTATION",       # 18
    "INSIDER_CONVICTION",    # 19
    "MERGER_DISTRESS",       # 20
    "NEWS_CONTAGION",        # 21
    "COMMODITY_SQUEEZE",     # 22
    "POLICY_SHOCK",          # 23
    "RESERVED_24", "RESERVED_25", "RESERVED_26", "RESERVED_27",
    "RESERVED_28", "RESERVED_29", "RESERVED_30", "RESERVED_31",
]

N_CHANNELS = 32
CHANNEL_INDEX = {name: i for i, name in enumerate(SPHERE_CHANNELS)}


# ═══════════════════════════════════════════════════════════════════════════
# 2. Event class → base sphere-of-impact vector  M_{class}
#    Spec: ξ_u = M_{class} Γ_geo Γ_scope Γ_dir
# ═══════════════════════════════════════════════════════════════════════════

def _sphere_vec(**channels: float) -> np.ndarray:
    v = np.zeros(N_CHANNELS, dtype=np.float64)
    for name, weight in channels.items():
        idx = CHANNEL_INDEX.get(name)
        if idx is not None:
            v[idx] = weight
    return v


EVENT_CLASS_SPHERES: Dict[str, np.ndarray] = {
    "war_escalation": _sphere_vec(
        WAR_GEOPOLITICS=1.0, ENERGY_COMMODITY=0.6, VOLATILITY_REGIME=0.4,
        SUPPLY_CHAIN=0.3, CURRENCY_FX=0.2, TRADE_WAR=0.3,
    ),
    "oil_shock": _sphere_vec(
        ENERGY_COMMODITY=1.0, WAR_GEOPOLITICS=0.4, CONSUMER_STRESS=0.5,
        LOGISTICS=0.3, COMMODITY_SQUEEZE=0.8,
    ),
    "rate_hike": _sphere_vec(
        RATES_PRESSURE=1.0, CREDIT_STRESS=0.5, BUILDING_CYCLE=0.4,
        CONSUMER_STRESS=0.3, CURRENCY_FX=0.3,
    ),
    "stagflation": _sphere_vec(
        RATES_PRESSURE=0.8, CONSUMER_STRESS=0.8, ENERGY_COMMODITY=0.5,
        LABOR_PRESSURE=0.4, VOLATILITY_REGIME=0.3,
    ),
    "tech_selloff": _sphere_vec(
        TECH_CYCLE=1.0, VOLATILITY_REGIME=0.4, SECTOR_ROTATION=0.5,
    ),
    "pandemic": _sphere_vec(
        PANDEMIC=1.0, CONSUMER_STRESS=0.7, SUPPLY_CHAIN=0.8,
        LOGISTICS=0.6, VOLATILITY_REGIME=0.5,
    ),
    "trade_war": _sphere_vec(
        TRADE_WAR=1.0, CURRENCY_FX=0.6, SUPPLY_CHAIN=0.5,
        CONSUMER_STRESS=0.3,
    ),
    "earnings_shock": _sphere_vec(
        EARNINGS_SEASON=1.0, NEWS_CONTAGION=0.5, SECTOR_ROTATION=0.4,
    ),
    "merger_distress": _sphere_vec(
        MERGER_DISTRESS=1.0, CREDIT_STRESS=0.4, VOLATILITY_REGIME=0.2,
    ),
    "regulation": _sphere_vec(
        REGULATION=1.0, TECH_CYCLE=0.3,
    ),
    "commodity_squeeze": _sphere_vec(
        COMMODITY_SQUEEZE=1.0, ENERGY_COMMODITY=0.6, SUPPLY_CHAIN=0.4,
    ),
    "fiscal_stimulus": _sphere_vec(
        FISCAL_INFRA=1.0, BUILDING_CYCLE=0.5, LABOR_PRESSURE=0.3,
    ),
    "generic_macro": _sphere_vec(
        VOLATILITY_REGIME=0.5, CONSUMER_STRESS=0.3, RATES_PRESSURE=0.3,
    ),
}


# ═══════════════════════════════════════════════════════════════════════════
# 3. Source reliability registry
# ═══════════════════════════════════════════════════════════════════════════

SOURCE_RELIABILITY: Dict[str, float] = {
    "tavily_news":      0.7,
    "market_data":      0.9,
    "official_release": 1.0,
    "analyst":          0.5,
    "social":           0.3,
    "unknown":          0.4,
}


# ═══════════════════════════════════════════════════════════════════════════
# 4. Normalized event (ν_u) and Epoch object (ε_k)
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class NormalizedEvent:
    """Spec: ν_u = (id, src, ts, class, scope, dir, sev, conf, pers, geo, sec, ind, textHash)"""
    id: str
    source: str
    timestamp: str
    event_class: str
    scope: float
    direction: float
    severity: float
    confidence: float
    persistence: float
    geography: str
    sector: Optional[str]
    industry: Optional[str]
    text_hash: str


@dataclass
class EpochObject:
    """Spec: ε_k = (id, class, t_start, t_end, sev, conf, pers, ξ_k, src, decay)"""
    id: str
    event_class: str
    t_start: str
    t_end: Optional[str]
    severity: float
    confidence: float
    persistence: float
    sphere_vector: np.ndarray
    source: str
    decay_rate: float
    source_events: List[str] = field(default_factory=list)

    def amplitude(self, t: datetime) -> float:
        """Spec: ω_k(t) = sev × conf × pers × exp(-decay × max(0, t - t_end))"""
        base = self.severity * self.confidence * self.persistence
        if self.t_end is None:
            return base
        t_end = datetime.fromisoformat(self.t_end.replace("Z", "+00:00"))
        if not t.tzinfo:
            t = t.replace(tzinfo=timezone.utc)
        delta_days = max(0.0, (t - t_end).total_seconds() / 86400.0)
        return base * math.exp(-self.decay_rate * delta_days)

    def weighted_sphere(self, t: datetime) -> np.ndarray:
        return self.amplitude(t) * self.sphere_vector


# ═══════════════════════════════════════════════════════════════════════════
# 5. Admission scoring
# ═══════════════════════════════════════════════════════════════════════════

W_SRC  = 0.25
W_SEV  = 0.25
W_CONF = 0.20
W_PERS = 0.15
W_SCOPE = 0.10
W_DUP  = 0.30
PI_MIN = 0.35


def compute_admission_score(
    event: NormalizedEvent,
    existing_library: List[EpochObject],
) -> float:
    rel = SOURCE_RELIABILITY.get(event.source, 0.4)
    dup = 0.0
    for epoch in existing_library:
        if epoch.event_class == event.event_class:
            try:
                t_event = datetime.fromisoformat(event.timestamp.replace("Z", "+00:00"))
                t_epoch = datetime.fromisoformat(epoch.t_start.replace("Z", "+00:00"))
                delta_hours = abs((t_event - t_epoch).total_seconds()) / 3600
                if delta_hours < 24:
                    dup = max(dup, 1.0 - delta_hours / 24.0)
            except (ValueError, TypeError):
                pass
    return (W_SRC * rel + W_SEV * event.severity + W_CONF * event.confidence
            + W_PERS * event.persistence + W_SCOPE * event.scope - W_DUP * dup)


def project_sphere_vector(event: NormalizedEvent) -> np.ndarray:
    """Spec: ξ_u = M_{class} Γ_geo Γ_scope Γ_dir"""
    base = EVENT_CLASS_SPHERES.get(event.event_class,
           EVENT_CLASS_SPHERES.get("generic_macro", np.zeros(N_CHANNELS)))
    vec = base.copy()
    vec *= (0.5 + 0.5 * event.scope)
    if event.direction < 0:
        vec *= abs(event.direction)
    elif event.direction == 0:
        vec *= 0.5
    if event.geography not in ("US", "GLOBAL"):
        vec *= 0.7
    return vec


# ═══════════════════════════════════════════════════════════════════════════
# 6. Event classification from news text
# ═══════════════════════════════════════════════════════════════════════════

CLASSIFICATION_RULES: List[Dict[str, Any]] = [
    {
        "event_class": "war_escalation",
        "keywords": ["iran", "war", "military strike", "missile", "invasion",
                     "troops deployed", "peace plan rejected", "ceasefire collapse",
                     "nato", "south china sea", "taiwan", "sanctions escalat"],
        "severity": 0.8, "persistence": 0.7, "scope": 1.0, "direction": -1,
        "decay_rate": 0.05,
    },
    {
        "event_class": "oil_shock",
        "keywords": ["oil surge", "oil spike", "oil shock", "opec cut",
                     "supply disruption", "refinery", "crude above $90",
                     "crude above $100", "barrel", "energy crisis",
                     "oil above $90", "oil above $100"],
        "severity": 0.8, "persistence": 0.6, "scope": 1.0, "direction": -1,
        "decay_rate": 0.07,
    },
    {
        "event_class": "stagflation",
        "keywords": ["stagflation", "inflation surge", "no rate cut",
                     "higher for longer", "powell warns", "rate cuts delayed"],
        "severity": 0.7, "persistence": 0.8, "scope": 1.0, "direction": -1,
        "decay_rate": 0.04,
    },
    {
        "event_class": "rate_hike",
        "keywords": ["rate hike", "fed raises", "hawkish", "tightening",
                     "yield spike", "bond sell"],
        "severity": 0.7, "persistence": 0.7, "scope": 1.0, "direction": -1,
        "decay_rate": 0.05,
    },
    {
        "event_class": "tech_selloff",
        "keywords": ["tech selloff", "tech reckoning", "ai bubble",
                     "semiconductor shortage", "chip ban", "antitrust big tech"],
        "severity": 0.6, "persistence": 0.5, "scope": 0.7, "direction": -1,
        "decay_rate": 0.08,
    },
    {
        "event_class": "trade_war",
        "keywords": ["tariff", "trade war", "export ban", "import duty",
                     "trade restrictions", "decoupling"],
        "severity": 0.7, "persistence": 0.7, "scope": 1.0, "direction": -1,
        "decay_rate": 0.04,
    },
    {
        "event_class": "commodity_squeeze",
        "keywords": ["commodity surge", "natural gas spike", "metal shortage",
                     "grain shortage", "food prices", "lithium"],
        "severity": 0.6, "persistence": 0.5, "scope": 0.8, "direction": -1,
        "decay_rate": 0.07,
    },
    {
        "event_class": "fiscal_stimulus",
        "keywords": ["stimulus", "infrastructure bill", "fiscal spending",
                     "government investment", "infrastructure package"],
        "severity": 0.6, "persistence": 0.6, "scope": 1.0, "direction": +1,
        "decay_rate": 0.03,
    },
]


def classify_text(text: str) -> List[Dict[str, Any]]:
    text_lower = text.lower()
    matches = []
    for rule in CLASSIFICATION_RULES:
        for kw in rule["keywords"]:
            if kw.lower() in text_lower:
                matches.append(rule)
                break
    return matches


def create_event_from_text(
    text: str, source: str = "tavily_news", geography: str = "US",
) -> List[NormalizedEvent]:
    matches = classify_text(text)
    events = []
    now = datetime.now(timezone.utc).isoformat()
    text_hash = hashlib.sha256(text.encode()).hexdigest()[:16]
    for match in matches:
        events.append(NormalizedEvent(
            id=f"evt_{match['event_class']}_{text_hash}_{int(time.time())}",
            source=source, timestamp=now, event_class=match["event_class"],
            scope=match["scope"], direction=match["direction"],
            severity=match["severity"],
            confidence=SOURCE_RELIABILITY.get(source, 0.4),
            persistence=match["persistence"], geography=geography,
            sector=None, industry=None, text_hash=text_hash,
        ))
    return events


# ═══════════════════════════════════════════════════════════════════════════
# 7. G32 Coordinator
# ═══════════════════════════════════════════════════════════════════════════

class G32Coordinator:
    """Spec: G32_t = (Ξ_t, Ξ̄_t, ΔΞ_t, Π_t^epoch, L_epoch_t, R_t)"""

    def __init__(self, alpha_smooth: float = 0.85):
        self.epoch_library: List[EpochObject] = []
        self.conflict_ledger: List[Dict[str, Any]] = []
        self.alpha_smooth = alpha_smooth
        self.xi_current = np.zeros(N_CHANNELS)
        self.xi_smoothed = np.zeros(N_CHANNELS)
        self.xi_delta = np.zeros(N_CHANNELS)

    def admit_event(self, event: NormalizedEvent) -> Optional[EpochObject]:
        score = compute_admission_score(event, self.epoch_library)
        if score < PI_MIN:
            return None
        # Merge with existing same-class active epoch
        for existing in self.epoch_library:
            if existing.event_class == event.event_class and existing.t_end is None:
                existing.severity = max(existing.severity, event.severity)
                existing.confidence = max(existing.confidence, event.confidence)
                existing.source_events.append(event.id)
                existing.sphere_vector = project_sphere_vector(event)
                return existing
        # New epoch object
        sphere = project_sphere_vector(event)
        decay_rate = 0.05
        for rule in CLASSIFICATION_RULES:
            if rule["event_class"] == event.event_class:
                decay_rate = rule.get("decay_rate", 0.05)
                break
        epoch = EpochObject(
            id=f"epoch_{event.event_class}_{int(time.time())}",
            event_class=event.event_class, t_start=event.timestamp,
            t_end=None, severity=event.severity, confidence=event.confidence,
            persistence=event.persistence, sphere_vector=sphere,
            source=event.source, decay_rate=decay_rate,
            source_events=[event.id],
        )
        self.epoch_library.append(epoch)
        self._resolve_conflicts(epoch)
        return epoch

    def _resolve_conflicts(self, new_epoch: EpochObject) -> None:
        eps = 1e-8
        for existing in self.epoch_library:
            if existing.id == new_epoch.id:
                continue
            norm_prod = (np.linalg.norm(existing.sphere_vector)
                        * np.linalg.norm(new_epoch.sphere_vector) + eps)
            contradiction = max(0.0, float(
                np.dot(existing.sphere_vector, -new_epoch.sphere_vector)
            )) / norm_prod
            if contradiction > 0.5:
                self.conflict_ledger.append({
                    "epoch_a": existing.id, "epoch_b": new_epoch.id,
                    "contradiction": contradiction,
                    "resolved_at": datetime.now(timezone.utc).isoformat(),
                })
                existing.confidence *= 0.8
                new_epoch.confidence *= 0.8

    def compute_mosaic(self, t: Optional[datetime] = None) -> np.ndarray:
        if t is None:
            t = datetime.now(timezone.utc)
        mosaic = np.zeros(N_CHANNELS)
        for epoch in self.epoch_library:
            mosaic += epoch.weighted_sphere(t)
        return mosaic

    def update(self, t: Optional[datetime] = None) -> Dict[str, np.ndarray]:
        if t is None:
            t = datetime.now(timezone.utc)
        self.epoch_library = [e for e in self.epoch_library if e.amplitude(t) >= 0.01]
        self.xi_current = self.compute_mosaic(t)
        self.xi_smoothed = (self.alpha_smooth * self.xi_smoothed
                           + (1 - self.alpha_smooth) * self.xi_current)
        self.xi_delta = self.xi_current - self.xi_smoothed
        return {"xi": self.xi_current, "xi_smoothed": self.xi_smoothed,
                "xi_delta": self.xi_delta}

    def get_channel_severities(self) -> Dict[str, float]:
        return {SPHERE_CHANNELS[i]: round(float(self.xi_current[i]), 4)
                for i in range(N_CHANNELS) if self.xi_current[i] > 0.001}

    def compute_symbol_pressure(
        self, sector: str,
        sector_couplings: Optional[Dict[str, Dict[str, float]]] = None,
    ) -> float:
        if sector_couplings is None:
            return 0.0
        couplings = sector_couplings.get(sector, {})
        pressure = 0.0
        for channel_name, coupling_weight in couplings.items():
            idx = CHANNEL_INDEX.get(channel_name)
            if idx is not None:
                pressure += coupling_weight * self.xi_current[idx]
        return pressure

    def to_dict(self) -> Dict[str, Any]:
        return {
            "xi": {SPHERE_CHANNELS[i]: round(float(self.xi_current[i]), 4)
                   for i in range(N_CHANNELS) if self.xi_current[i] != 0},
            "xi_smoothed": {SPHERE_CHANNELS[i]: round(float(self.xi_smoothed[i]), 4)
                           for i in range(N_CHANNELS) if self.xi_smoothed[i] != 0},
            "xi_delta": {SPHERE_CHANNELS[i]: round(float(self.xi_delta[i]), 4)
                        for i in range(N_CHANNELS) if self.xi_delta[i] != 0},
            "active_epochs": len(self.epoch_library),
            "conflicts": len(self.conflict_ledger),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }


# ═══════════════════════════════════════════════════════════════════════════
# 8. News ingestion pipeline (Tavily)
# ═══════════════════════════════════════════════════════════════════════════

def _load_tavily_key() -> Optional[str]:
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
    import urllib.request
    body = json.dumps({
        "query": query, "max_results": max_results,
        "include_answer": "basic", "topic": "news", "days": 3,
    }).encode()
    req = urllib.request.Request(
        "https://api.tavily.com/search", data=body, method="POST",
        headers={"Content-Type": "application/json",
                 "Authorization": f"Bearer {api_key}"},
    )
    resp = urllib.request.urlopen(req, timeout=15)
    return json.loads(resp.read())


def ingest_news(coordinator: G32Coordinator) -> int:
    api_key = _load_tavily_key()
    if not api_key:
        print("[EPOCH-LIB] No Tavily API key — skipping news ingestion")
        return 0
    queries = [
        "stock market today oil prices geopolitical risk",
        "federal reserve interest rates inflation economy today",
        "middle east conflict energy supply crisis",
        "technology sector stocks semiconductor earnings",
    ]
    admitted = 0
    for query in queries:
        try:
            result = _query_tavily(api_key, query, max_results=5)
            answer = result.get("answer", "")
            if answer:
                for event in create_event_from_text(answer):
                    if coordinator.admit_event(event):
                        admitted += 1
            for r in result.get("results", []):
                text = f"{r.get('title', '')} {r.get('content', '')[:500]}"
                for event in create_event_from_text(text):
                    if coordinator.admit_event(event):
                        admitted += 1
            time.sleep(0.5)
        except Exception as exc:
            print(f"[EPOCH-LIB] Tavily query failed: {exc}")
    return admitted


# ═══════════════════════════════════════════════════════════════════════════
# 9. Public API
# ═══════════════════════════════════════════════════════════════════════════

def build_epoch_mosaic(
    auto_severities: Optional[Dict[str, float]] = None,
) -> Tuple[G32Coordinator, Dict[str, float]]:
    """Build full epoch mosaic from market data + news. Returns (coordinator, severities)."""
    coordinator = G32Coordinator()

    # Inject market data as high-confidence epoch objects
    if auto_severities:
        now = datetime.now(timezone.utc).isoformat()
        for channel, severity in auto_severities.items():
            if severity < 0.2:
                continue
            idx = CHANNEL_INDEX.get(channel)
            if idx is None:
                continue
            sphere = np.zeros(N_CHANNELS)
            sphere[idx] = 1.0
            epoch = EpochObject(
                id=f"market_{channel}_{int(time.time())}",
                event_class=f"market_{channel.lower()}", t_start=now,
                t_end=None, severity=severity, confidence=0.9,
                persistence=0.5, sphere_vector=sphere, source="market_data",
                decay_rate=0.1,
            )
            coordinator.epoch_library.append(epoch)

    admitted = ingest_news(coordinator)
    print(f"[EPOCH-LIB] News events admitted: {admitted}")
    coordinator.update()
    severities = coordinator.get_channel_severities()
    print(f"[EPOCH-LIB] Epoch mosaic: {len(coordinator.epoch_library)} active objects, "
          f"{len(severities)} active channels")
    return coordinator, severities
