"""Kapak resmi: MPRIS `mpris:artUrl` → 240×240 RGB565 (küçük uçlu) bayt dizisi.

Kaynaklar: https/http (Spotify i.scdn.co vb.) ve file:// (yerel çalarlar, tarayıcıların geçici kapakları).
"""

from __future__ import annotations

import io
import urllib.parse
import urllib.request
import zlib

from PIL import Image, ImageOps

SIZE = 240
MAX_DOWNLOAD = 8 * 1024 * 1024  # 8 MB üstü kapak indirilmez
TIMEOUT_S = 5
USER_AGENT = "pc-panel/0.1"


def _read(url: str) -> bytes | None:
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme == "file":
        path = urllib.parse.unquote(parsed.path)
        try:
            with open(path, "rb") as f:
                return f.read(MAX_DOWNLOAD + 1)
        except OSError:
            return None
    if parsed.scheme in ("http", "https"):
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT_S) as r:
                return r.read(MAX_DOWNLOAD + 1)
        except (OSError, ValueError):
            return None
    return None


def to_rgb565(img: Image.Image) -> bytes:
    """RGB → RGB565, küçük uçlu (LVGL, LV_COLOR_16_SWAP=0)."""
    raw = img.convert("RGB").tobytes()  # getdata() Pillow 14'te kalkıyor
    out = bytearray(len(raw) // 3 * 2)
    i = 0
    for j in range(0, len(raw), 3):
        v = ((raw[j] & 0xF8) << 8) | ((raw[j + 1] & 0xFC) << 3) | (raw[j + 2] >> 3)
        out[i] = v & 0xFF
        out[i + 1] = v >> 8
        i += 2
    return bytes(out)


def load(url: str) -> bytes | None:
    """Kapağı okur, ortadan kare kırpar, 240×240 RGB565 döndürür. Olmazsa None. (Engelleyici; iş parçacığında çağırın.)"""
    return from_bytes(_read(url))


def from_bytes(data: bytes | None) -> bytes | None:
    """Resim dosyası baytları (PNG/JPEG…) → 240×240 RGB565 ya da None. Windows'ta kapak çaların akışından gelir."""
    if not data or len(data) > MAX_DOWNLOAD:
        return None
    try:
        img = Image.open(io.BytesIO(data))
        img = ImageOps.fit(img.convert("RGB"), (SIZE, SIZE), Image.Resampling.LANCZOS)
    except (OSError, ValueError, Image.DecompressionBombError):
        return None
    return to_rgb565(img)


def header(pixels: bytes | None) -> dict:
    if not pixels:
        return {"t": "art", "n": 0}
    return {"t": "art", "w": SIZE, "h": SIZE, "n": len(pixels), "crc": zlib.crc32(pixels)}
