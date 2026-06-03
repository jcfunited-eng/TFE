# -*- coding: utf-8 -*-
from __future__ import annotations
import json, datetime
from pathlib import Path
from typing import Dict, List

class MemoryRing:
    def __init__(self, logdir="memory_logs", short=12, mid=48, long=192, half_life=72.0):
        self.logdir = Path(logdir)
        self.logdir.mkdir(parents=True, exist_ok=True)
        self.short_cap = int(short)
        self.mid_cap = int(mid)
        self.long_cap = int(long)
        self.half_life = float(half_life)
        self.short: List[Dict] = []
        self.mid:   List[Dict] = []
        self.long:  List[Dict] = []
        self.short_path = self.logdir / "ring_short.jsonl"
        self.mid_path   = self.logdir / "ring_mid.jsonl"
        self.long_path  = self.logdir / "ring_long.jsonl"
        self._load_existing()

    def _load_existing(self):
        for path, buf in ((self.short_path, self.short),
                          (self.mid_path, self.mid),
                          (self.long_path, self.long)):
            if path.exists():
                try:
                    lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
                    for ln in lines[-max(self.short_cap, self.mid_cap, self.long_cap):]:
                        try:
                            buf.append(json.loads(ln))
                        except Exception:
                            pass
                except Exception:
                    pass
        self.short = self.short[-self.short_cap:]
        self.mid   = self.mid[-self.mid_cap:]
        self.long  = self.long[-self.long_cap:]

    def append(self, item: Dict):
        item = dict(item)
        item["timestamp"] = datetime.datetime.now().isoformat(timespec="seconds")
        self.short.append(item); self.short[:] = self.short[-self.short_cap:]
        self.mid.append(item);   self.mid[:]   = self.mid[-self.mid_cap:]
        self.long.append(item);  self.long[:]  = self.long[-self.long_cap:]
        self.short_path.open("a", encoding="utf-8").write(json.dumps(item) + "\n")
        self.mid_path.open("a", encoding="utf-8").write(json.dumps(item) + "\n")
        self.long_path.open("a", encoding="utf-8").write(json.dumps(item) + "\n")

    def _decay_weight(self, iso_ts: str) -> float:
        try:
            t0 = datetime.datetime.fromisoformat(iso_ts)
        except Exception:
            return 1.0
        dt_hours = (datetime.datetime.now() - t0).total_seconds() / 3600.0
        if self.half_life <= 0: return 1.0
        return 0.5 ** (dt_hours / self.half_life)

    def snapshot(self) -> Dict:
        def stats(buf: List[Dict]):
            if not buf: return {"n":0,"phi":0,"H":0,"energy":0}
            wsum = 0.0; p=0.0; h=0.0; e=0.0
            for x in buf:
                w = self._decay_weight(x.get("timestamp",""))
                wsum += w
                p += w * x.get("phi",0)
                h += w * x.get("H",0)
                e += w * x.get("energy",0)
            if wsum <= 1e-9: return {"n":len(buf),"phi":0,"H":0,"energy":0}
            return {"n":len(buf),"phi":round(p/wsum,3),"H":round(h/wsum,3),"energy":round(e/wsum,3)}
        return {"short":stats(self.short), "mid":stats(self.mid), "long":stats(self.long)}
