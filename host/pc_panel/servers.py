"""Sunucu / site sağlığı (ayar dosyasında [[sunucu]]).

- `adres = "https://…"`: GET isteği; 500'den küçük her yanıt "ayakta" sayılır (404/401 de sunucunun cevap
  verdiğini gösterir). Gecikme ms. https ise sertifikanın bitmesine kalan gün (6 saatte bir).
- `tcp = "makine:port"`: yalnızca bağlantı açılıyor mu (ör. SSH 22).
Art arda 2 başarısız denetimde "kapalı" sayılır (tek seferlik takılmalar uyarı üretmesin).
"""

from __future__ import annotations

import socket
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request

from .config import Server

TIMEOUT_S = 8
SSL_EVERY_S = 6 * 3600
SSL_WARN_DAYS = 7
FAILS_FOR_DOWN = 2
USER_AGENT = "pc-panel-saglik/0.1"


def _http(url: str) -> tuple[bool, int | None, str]:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    t0 = time.monotonic()
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_S) as r:
            r.read(1024)
            code = r.status
    except urllib.error.HTTPError as e:
        code = e.code
    except (OSError, ValueError) as e:
        reason = getattr(e, "reason", e)
        return False, None, str(reason)[:60]
    ms = int((time.monotonic() - t0) * 1000)
    return code < 500, ms, f"HTTP {code}"


def _tcp(host: str, port: int) -> tuple[bool, int | None, str]:
    t0 = time.monotonic()
    try:
        with socket.create_connection((host, port), timeout=TIMEOUT_S):
            pass
    except OSError as e:
        return False, None, str(e)[:60]
    return True, int((time.monotonic() - t0) * 1000), "açık"


def _ssl_days(host: str, port: int = 443) -> int | None:
    ctx = ssl.create_default_context()
    try:
        with socket.create_connection((host, port), timeout=TIMEOUT_S) as sock:
            with ctx.wrap_socket(sock, server_hostname=host) as tls:
                cert = tls.getpeercert()
    except (OSError, ssl.SSLError):
        return None
    if not cert or "notAfter" not in cert:
        return None
    return int((ssl.cert_time_to_seconds(cert["notAfter"]) - time.time()) // 86400)


class ServerWatcher:
    def __init__(self) -> None:
        self._fails: dict[str, int] = {}
        self._down: dict[str, bool] = {}
        self._ssl: dict[str, tuple[float, int | None]] = {}  # makine → (ölçüm anı, gün)
        self.items: list[dict] = []
        self.warn = ""

    def check_one(self, s: Server) -> dict:
        """Engelleyici (iş parçacığında). Kart satırı + iç bilgi."""
        if s.url:
            ok, ms, detail = _http(s.url)
            u = urllib.parse.urlparse(s.url)
            days = None
            if u.scheme == "https" and u.hostname:
                at, cached = self._ssl.get(u.hostname, (0.0, None))
                if time.monotonic() - at > SSL_EVERY_S or (cached is None and ok):
                    cached = _ssl_days(u.hostname, u.port or 443)
                    self._ssl[u.hostname] = (time.monotonic(), cached)
                days = cached
        else:
            host, port = s.tcp
            ok, ms, detail = _tcp(host, port)
            days = None
        return {"name": s.name, "ok": ok, "ms": ms, "ssl": days, "detail": detail}

    def update(self, results: list[dict], known: list[Server]) -> list[tuple[str, str, str]]:
        """Denetim sonuçlarını işler; kapandı / düzeldi bildirimleri döner."""
        names = {s.name for s in known}
        for d in (self._fails, self._down):
            for gone in set(d) - names:
                d.pop(gone)
        notes, items, warns = [], [], []
        for r in results:
            n = r["name"]
            self._fails[n] = 0 if r["ok"] else self._fails.get(n, 0) + 1
            was_down = self._down.get(n)
            down = self._fails[n] >= FAILS_FOR_DOWN
            if down and not was_down:
                notes.append((f"{n} kapalı", r["detail"], "err"))
            elif was_down and not down:
                notes.append((f"{n} yeniden ayakta", f"{r['ms']} ms", "ok"))
            self._down[n] = down
            state = 0 if down else (1 if r["ok"] else -1)  # tek başarısızlık: henüz bilinmiyor/şüpheli
            items.append({"n": n, "ok": state, "ms": r["ms"], "ssl": r["ssl"]})
            if down:
                warns.append(f"{n} kapalı")
            elif r["ssl"] is not None and r["ssl"] < SSL_WARN_DAYS:
                warns.append(f"{n} SSL {r['ssl']} gün")
        self.items, self.warn = items, " · ".join(warns)
        return notes
