"""Claude Code kullanımı: her hesap için içinde bulunulan 5 saatlik penceredeki token miktarı.

Kaynak: hesabın ayar dizinindeki konuşma kayıtları (`<dizin>/projects/**/*.jsonl`); her asistan mesajında
`message.usage` var. Yalnızca token sayıları ve zaman damgaları okunur, içerik okunmaz/gönderilmez.

- Token = girdi + çıktı + önbelleğe yazma (önbellekten okuma sayılmaz: çok büyük ve ucuz, sınırı da
  belirleyen o değil). Akış sırasında aynı mesaj birkaç kez yazılır; (mesaj kimliği, istek kimliği) ile tekilleşir.
- 5 saatlik pencereler ccusage'daki gibi: ilk mesajın saat başından başlar, 5 saat sürer; aradaki boşluktan sonraki
  ilk mesaj yeni pencere açar. Sıfırlanma = pencere sonu.
- Plan sınırı yerelde bilinmediği için yüzde, son 7 gündeki en yoğun pencereye göredir.
- Dosyalar baştan okunmaz: her dosyanın okunan konumu saklanır, yalnızca eklenen satırlar okunur.
"""

from __future__ import annotations

import json
import os
import time
from datetime import datetime
from pathlib import Path

WINDOW_S = 5 * 3600
HISTORY_S = 7 * 86400
DEFAULT_DIR = Path.home() / ".claude"


def account_dirs() -> list[tuple[str, Path]]:
    """[("hesap1", ~/.claude), ("hesap2", ~/.claude-hesap2), …] — projects/ klasörü olanlar."""
    out = []
    if (DEFAULT_DIR / "projects").is_dir():
        out.append(("hesap1", DEFAULT_DIR))
    for d in sorted(Path.home().glob(".claude-*")):
        if (d / "projects").is_dir():
            out.append((d.name.removeprefix(".claude-") or d.name, d))
    return out


def fmt_tokens(n: int) -> str:
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f} M".replace(".", ",")
    if n >= 1000:
        return f"{n // 1000} K"
    return str(n)


class _Account:
    def __init__(self, name: str, root: Path) -> None:
        self.name, self.root = name, root
        self.offsets: dict[str, int] = {}            # dosya → okunan bayt
        self.entries: dict[tuple[str, str], tuple[float, int]] = {}  # (mesaj, istek) → (zaman, token)

    def scan(self) -> None:
        cutoff = time.time() - HISTORY_S - 86400
        for path in (self.root / "projects").rglob("*.jsonl"):
            try:
                st = path.stat()
            except OSError:
                continue
            if st.st_mtime < cutoff:
                continue
            key = str(path)
            pos = self.offsets.get(key, 0)
            if st.st_size < pos:  # dosya küçülmüş (yeniden yazılmış): baştan
                pos = 0
            if st.st_size == pos:
                continue
            with open(path, "rb") as f:
                f.seek(pos)
                data = f.read()
            end = data.rfind(b"\n") + 1  # yarım kalan son satırı sonraya bırak
            for line in data[:end].splitlines():
                if b'"usage"' not in line or b'"assistant"' not in line:
                    continue
                self._parse(line)
            self.offsets[key] = pos + end

    def _parse(self, line: bytes) -> None:
        try:
            d = json.loads(line)
        except ValueError:
            return
        msg = d.get("message") or {}
        u = msg.get("usage")
        ts = d.get("timestamp")
        if d.get("type") != "assistant" or not isinstance(u, dict) or not ts:
            return
        try:
            t = datetime.fromisoformat(ts.replace("Z", "+00:00")).timestamp()
        except ValueError:
            return
        tok = sum(int(u.get(k) or 0) for k in ("input_tokens", "output_tokens", "cache_creation_input_tokens"))
        key = (str(msg.get("id", "")), str(d.get("requestId", "")))
        if key == ("", ""):
            key = (ts, str(tok))
        self.entries[key] = (t, tok)  # aynı mesajın sonraki yazımı (son hali) öncekinin yerine geçer

    def summary(self, now: float) -> dict:
        old = now - HISTORY_S
        for k in [k for k, (t, _) in self.entries.items() if t < old]:
            del self.entries[k]
        blocks: list[list[float]] = []  # [başlangıç, son mesaj, token]
        for t, tok in sorted(self.entries.values()):
            if blocks and t < blocks[-1][0] + WINDOW_S:
                blocks[-1][1], blocks[-1][2] = t, blocks[-1][2] + tok
            else:
                start = t - (t % 3600)  # saat başı (UTC; Türkiye saatinde de saat başı)
                blocks.append([start, t, tok])
        cur = blocks[-1] if blocks and now < blocks[-1][0] + WINDOW_S else None
        peak = max((b[2] for b in blocks), default=0)
        tokens = int(cur[2]) if cur else 0
        return {
            "n": self.name,
            "tok": tokens,
            "txt": fmt_tokens(tokens),
            "pct": round(tokens / peak * 100) if peak and cur else 0,
            "rst": int(cur[0] + WINDOW_S - now) if cur else -1,
        }


class UsageTracker:
    def __init__(self) -> None:
        self.accounts = [_Account(n, d) for n, d in account_dirs()]

    def poll(self) -> list[dict]:
        """Engelleyici (iş parçacığında çağırın)."""
        now = time.time()
        out = []
        for a in self.accounts:
            try:
                a.scan()
            except OSError:
                pass
            out.append(a.summary(now))
        return out


if __name__ == "__main__":  # elle deneme: python -m pc_panel.usage
    t0 = time.monotonic()
    for row in UsageTracker().poll():
        print(row)
    print(f"{time.monotonic() - t0:.1f} sn", os.getpid())
