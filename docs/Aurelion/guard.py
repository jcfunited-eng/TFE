# guard.py — Safe ingestion guardrails
import os, re, time, urllib.parse, urllib.robotparser, requests
from typing import List

PII_EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
PII_PHONE = re.compile(r"\+?\d[\d\-\s()]{6,}\d")

class SafeGuard:
    def __init__(self, cfg: dict):
        self.cfg = cfg
        self._fetch_count = 0
        self._last_minute = int(time.time() // 60)

    # ---------- PATH & URL WHITELISTS ----------
    def allowed_path(self, path: str) -> bool:
        allow_ext = tuple(self.cfg.get("file_allow_ext", [".txt", ".csv"]))
        if not path.lower().endswith(allow_ext):
            return False
        for pref in self.cfg.get("path_whitelist", []):
            if path.startswith(pref) or os.path.abspath(path).startswith(os.path.abspath(pref)):
                return True
        return False

    def allowed_url(self, url: str) -> bool:
        ok = False
        for pref in self.cfg.get("url_whitelist", []):
            if url.startswith(pref):
                ok = True; break
        if not ok:
            return False
        # robots.txt check
        try:
            u = urllib.parse.urlparse(url)
            robots = f"{u.scheme}://{u.netloc}/robots.txt"
            rp = urllib.robotparser.RobotFileParser()
            rp.set_url(robots)
            rp.read()
            ua = self.cfg.get("http_fetch", {}).get("user_agent", "AurelionSafeBridge/1.0")
            if not rp.can_fetch(ua, url):
                return False
        except Exception:
            pass  # best effort
        return True

    # ---------- RATE LIMITS ----------
    def _check_rate(self) -> bool:
        now_min = int(time.time() // 60)
        if now_min != self._last_minute:
            self._last_minute = now_min
            self._fetch_count = 0
        per_min = int(self.cfg.get("http_fetch", {}).get("per_minute", 2))
        per_run = int(self.cfg.get("http_fetch", {}).get("per_run", 5))
        if self._fetch_count >= per_run:
            return False
        if self._fetch_count >= per_min:
            return False
        self._fetch_count += 1
        return True

    # ---------- SCRUBBERS ----------
    def scrub_pii(self, text: str) -> str:
        if not self.cfg.get("redact_pii", True):
            return text
        text = PII_EMAIL.sub("[redacted_email]", text)
        text = PII_PHONE.sub("[redacted_phone]", text)
        return text

    # ---------- FETCH ----------
    def fetch_url(self, url: str) -> str:
        http_cfg = self.cfg.get("http_fetch", {})
        if not http_cfg.get("enabled", False):
            return "(http disabled)"
        if not self.allowed_url(url):
            return "(url not allowed by whitelist/robots)"
        if not self._check_rate():
            return "(rate limited)"
        try:
            headers = {"User-Agent": http_cfg.get("user_agent", "AurelionSafeBridge/1.0")}
            r = requests.get(url, headers=headers, timeout=http_cfg.get("timeout_sec", 20))
            r.raise_for_status()
            txt = r.text
            maxb = int(self.cfg.get("max_file_bytes", 2_000_000))
            if len(txt.encode("utf-8", errors="ignore")) > maxb:
                txt = txt[: maxb].rsplit(" ", 1)[0]
            return self.scrub_pii(txt)
        except Exception as e:
            return f"(fetch error: {e})"
