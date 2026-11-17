"""Uygulamalar sayfası: masaüstü kimliklerinden ad + ikon bulma, ikonu karta uygun biçime çevirme, başlatma.

- Kimlik = `.desktop` dosyasının adı (ör. "steam", "com.microsoft.VSCode"); `~/.local/share/applications`,
  `/usr/share/applications` ve flatpak dizinlerinde aranır.
- İkon: `.desktop` içindeki `Icon=` → KDE ikon teması (kdeglobals, varsayılan breeze) + mirası + hicolor +
  /usr/share/pixmaps. 64 px ve üstü PNG tercih edilir; yoksa SVG `rsvg-convert` ile çizilir.
- Kart biçimi: 64×64, LVGL `LV_IMG_CF_TRUE_COLOR_ALPHA` (16 bit renk): piksel başına RGB565 küçük uçlu + alfa
  = 3 bayt, toplam 12 288 bayt. Kapak resmi gibi ikili blok olarak gider (bkz. docs/02-mimari.md).
- Başlatma: `kstart --application <kimlik>` (kabuk yok; yalnızca listedeki kimlikler).
"""

from __future__ import annotations

import configparser
import io
import os
import re
import subprocess
import zlib
from dataclasses import dataclass
from pathlib import Path

from PIL import Image

ICON_PX = 64
HOME = Path.home()
DATA_DIRS = [HOME / ".local/share", Path("/usr/local/share"), Path("/usr/share"),
             HOME / ".local/share/flatpak/exports/share", Path("/var/lib/flatpak/exports/share")]
for _d in os.environ.get("XDG_DATA_DIRS", "").split(":"):
    if _d and Path(_d) not in DATA_DIRS:
        DATA_DIRS.append(Path(_d))
_SIZE_RE = re.compile(r"/(\d+)(?:x\d+)?(?:@\d+x?)?/")


@dataclass(frozen=True)
class App:
    id: str          # masaüstü kimliği
    title: str
    icon_name: str
    desktop: Path


def find_desktop(app_id: str) -> Path | None:
    for base in DATA_DIRS:
        p = base / "applications" / f"{app_id}.desktop"
        if p.is_file():
            return p
    return None


def read_desktop(path: Path) -> dict:
    cp = configparser.RawConfigParser(interpolation=None, strict=False)
    cp.optionxform = str  # anahtarlar büyük/küçük harf duyarlı
    try:
        cp.read(path, encoding="utf-8")
    except (configparser.Error, UnicodeDecodeError):
        return {}
    return dict(cp["Desktop Entry"]) if cp.has_section("Desktop Entry") else {}


def resolve(app_id: str, title: str = "") -> App | None:
    path = find_desktop(app_id)
    if path is None:
        return None
    d = read_desktop(path)
    name = title or d.get("Name[tr]") or d.get("Name") or app_id
    return App(id=app_id, title=name, icon_name=d.get("Icon", ""), desktop=path)


# --- İkon teması -------------------------------------------------------------------------------

def _theme_chain() -> list[str]:
    theme = "breeze"
    for kdeglobals in (Path("/etc/xdg/kdeglobals"), HOME / ".config/kdeglobals"):  # kullanıcınınki sonra, üstün
        if kdeglobals.exists():
            m = re.search(r"^\[Icons\][^\[]*?^Theme=(.+?)$", kdeglobals.read_text(errors="replace"), re.M | re.S)
            if m:
                theme = m.group(1).strip()
    chain, todo = [], [theme]
    while todo:
        t = todo.pop(0)
        if t in chain:
            continue
        chain.append(t)
        for base in DATA_DIRS:
            idx = base / "icons" / t / "index.theme"
            if idx.exists():
                m = re.search(r"^Inherits=(.+)$", idx.read_text(errors="replace"), re.M)
                if m:
                    todo += [x.strip() for x in m.group(1).split(",") if x.strip()]
                break
    if "hicolor" not in chain:
        chain.append("hicolor")
    return chain


def find_icon(name: str) -> Path | None:
    if not name:
        return None
    if name.startswith("/"):
        return Path(name) if Path(name).is_file() else None
    for theme in _theme_chain():
        best_png, best_size, svg = None, 0, None
        for base in DATA_DIRS:
            root = base / "icons" / theme
            if not root.is_dir():
                continue
            for p in root.glob(f"**/{name}.*"):
                if p.suffix == ".svg" and svg is None:
                    svg = p
                elif p.suffix == ".png":
                    m = _SIZE_RE.search(str(p))
                    size = int(m.group(1)) if m else 0
                    # 64'e en yakın büyük boy; küçükler en son
                    score = size if size < ICON_PX else 10_000 - size
                    if score > best_size:
                        best_png, best_size = p, score
        if best_png is not None and best_size >= 10_000 - 512:  # 64..512 px PNG
            return best_png
        if svg is not None:
            return svg
        if best_png is not None:
            return best_png
    for ext in (".png", ".svg", ".xpm"):
        p = Path("/usr/share/pixmaps") / f"{name}{ext}"
        if p.is_file():
            return p
    return None


def _load_image(path: Path) -> Image.Image | None:
    try:
        if path.suffix == ".svg":
            r = subprocess.run(["rsvg-convert", "-w", str(ICON_PX), "-h", str(ICON_PX), "--keep-aspect-ratio",
                                str(path)], capture_output=True, timeout=10)
            if r.returncode != 0:
                return None
            return Image.open(io.BytesIO(r.stdout))
        return Image.open(path)
    except (OSError, subprocess.TimeoutExpired, Image.DecompressionBombError):
        return None


def icon_bytes(app: App) -> bytes | None:
    """64×64 LVGL TRUE_COLOR_ALPHA (RGB565 LE + A) ya da None."""
    path = find_icon(app.icon_name)
    img = _load_image(path) if path else None
    if img is None:
        return None
    img = img.convert("RGBA")
    img.thumbnail((ICON_PX, ICON_PX), Image.LANCZOS)
    canvas = Image.new("RGBA", (ICON_PX, ICON_PX), (0, 0, 0, 0))
    canvas.paste(img, ((ICON_PX - img.width) // 2, (ICON_PX - img.height) // 2))
    out = bytearray()
    for r, g, b, a in canvas.getdata():
        v = ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)
        out += bytes((v & 0xFF, v >> 8, a))
    return bytes(out)


def icon_header(index: int, data: bytes) -> dict:
    return {"t": "icon", "i": index, "w": ICON_PX, "h": ICON_PX, "n": len(data), "crc": zlib.crc32(data)}


def launch(app: App) -> bool:
    try:
        subprocess.Popen(["kstart", "--application", app.id], stdin=subprocess.DEVNULL,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True,
                         env=os.environ.copy())
        return True
    except OSError:
        return False
