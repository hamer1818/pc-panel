"""Uygulamalar sayfası — Windows: Başlat menüsü uygulamaları, kabuk ikonları, başlatma / öne getirme.

Linux karşılığı: apps.py (.desktop + ikon teması + kstart). Arayüz aynı: App, resolve, icon_bytes, icon_header,
launch, find_icon.

- Uygulama listesi: kabuğun "shell:AppsFolder" klasörü (Get-StartApps'ın da kaynağı): Ad + AppID + varsa exe yolu;
  masaüstü programları ve Mağaza uygulamaları birlikte.
- Ayardaki kimlik şu sırayla eşleşir: tam AppID → bilinen Linux kimlikleri (ör. "com.microsoft.VSCode" →
  "Visual Studio Code"; aynı ayar dosyası iki sistemde de iş görsün) → ad (büyük/küçük harf, boşluk, noktalama
  önemsiz: "steam" → "Steam") → adın başı → adın içi. Kimlikleri görmek için: `uv run pc-panel --uygulamalar`.
- İkon: IShellItemImageFactory("shell:AppsFolder\\<AppID>") — Gezgin'in gösterdiği ikonun aynısı, 64 px, alfa ile.
- Başlatma: program zaten açıksa penceresi öne getirilir (Linux'taki `kstart` gibi); değilse
  "shell:AppsFolder\\<AppID>" açılır. Yalnızca ayar dosyasındaki uygulamalar başlatılır.
"""

from __future__ import annotations

import ctypes
import json
import os
import re
import subprocess
import threading
import time
from ctypes import POINTER, byref, wintypes
from dataclasses import dataclass

import psutil
from comtypes import COMMETHOD, GUID, HRESULT, IUnknown
from PIL import Image

from ..apps import ICON_PX, encode_icon, icon_header  # noqa: F401  (icon_header dışarıya da sunulur)
from . import session as winsession

NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)
LIST_TTL_S = 120
_SKIP = re.compile(r"uninstall|kald[ıi]r|readme|beni oku|help|yard[ıi]m|support|destek|website", re.I)

# Linux masaüstü kimliği → Windows'taki olası adlar (ilk bulunan)
ALIASES = {
    "com.microsoft.vscode": ["Visual Studio Code"],
    "code": ["Visual Studio Code"],
    "code-oss": ["Visual Studio Code"],
    "org.kde.konsole": ["Terminal", "Windows Terminal", "Windows PowerShell"],
    "konsole": ["Terminal", "Windows Terminal"],
    "org.kde.dolphin": ["Dosya Gezgini", "File Explorer"],
    "dolphin": ["Dosya Gezgini", "File Explorer"],
    "org.kde.spectacle": ["Ekran Alıntısı Aracı", "Snipping Tool"],
    "org.kde.kcalc": ["Hesap Makinesi", "Calculator"],
    "org.kde.systemmonitor": ["Görev Yöneticisi", "Task Manager"],
    "systemsettings": ["Ayarlar", "Settings"],
    "zen": ["Zen"],
    "app.zen_browser.zen": ["Zen"],
    "zen-browser": ["Zen"],
    "firefox": ["Firefox"],
    "org.mozilla.firefox": ["Firefox"],
    "org.mozilla.thunderbird": ["Thunderbird"],
    "thunderbird": ["Thunderbird"],
    "com.discordapp.discord": ["Discord"],
    "com.spotify.client": ["Spotify"],
    "com.valvesoftware.steam": ["Steam"],
    "com.heroicgameslauncher.hgl": ["Epic Games Launcher", "Heroic Games Launcher"],
    "epic-games": ["Epic Games Launcher"],
    "com.rustdesk.rustdesk": ["RustDesk"],
    "anydesk": ["AnyDesk"],
    "google-chrome": ["Google Chrome"],
    "chromium": ["Chromium", "Google Chrome"],
    "brave-browser": ["Brave"],
    "org.telegram.desktop": ["Telegram"],
    "obsidian": ["Obsidian"],
}


@dataclass(frozen=True)
class App:
    id: str          # ayardaki kimlik
    title: str
    icon_name: str   # Windows AppID (shell:AppsFolder\<AppID>)
    desktop: str     # çalıştırılabilir dosya yolu biliniyorsa (öne getirmek için), yoksa ""


# --- Başlat menüsü listesi -----------------------------------------------------------------

_cache: dict = {"at": 0.0, "apps": []}
_cache_lock = threading.Lock()


_LIST_PS = (
    "[Console]::OutputEncoding=[Text.Encoding]::UTF8; "
    "(New-Object -ComObject Shell.Application).NameSpace('shell:AppsFolder').Items() | ForEach-Object { "
    "[pscustomobject]@{n=$_.Name; a=$_.Path; e=$_.ExtendedProperty('System.Link.TargetParsingPath')} } "
    "| ConvertTo-Json -Compress"
)


def _start_apps() -> list[tuple[str, str, str]]:
    """[(Ad, AppID, exe yolu ya da "")] — kabuğun "Uygulamalar" klasörü (Get-StartApps'ın kaynağı); 2 dk önbellekli."""
    with _cache_lock:
        if _cache["apps"] and time.monotonic() - _cache["at"] < LIST_TTL_S:
            return _cache["apps"]
        try:
            r = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", _LIST_PS],
                               capture_output=True, timeout=30, creationflags=NO_WINDOW)
            data = json.loads(r.stdout.decode("utf-8", "replace") or "[]")
        except (OSError, subprocess.TimeoutExpired, ValueError):
            return _cache["apps"]
        if isinstance(data, dict):
            data = [data]
        apps = []
        for d in data if isinstance(data, list) else []:
            if not isinstance(d, dict):
                continue
            name, aumid, exe = (str(d.get(k) or "") for k in ("n", "a", "e"))
            if name and aumid and not aumid.lower().startswith(("http:", "https:")):
                apps.append((name, aumid, exe if exe.lower().endswith(".exe") else ""))
        _cache.update(at=time.monotonic(), apps=apps)
        return apps


def start_apps() -> list[tuple[str, str]]:
    """[(Ad, AppID)] — `--uygulamalar` listesi."""
    return [(n, a) for n, a, _ in _start_apps()]


def _norm(s: str) -> str:
    return re.sub(r"[^0-9a-zçğıöşü]+", "", s.casefold())


def _match(app_id: str, apps: list[tuple[str, str, str]]) -> tuple[str, str, str] | None:
    key = app_id.casefold()
    for row in apps:
        if row[1].casefold() == key:
            return row
    for alias in ALIASES.get(key, []):
        for row in apps:
            if row[0].casefold() == alias.casefold():
                return row
    if key in ALIASES:
        return None  # bilinen Linux kimliği ama karşılığı kurulu değil
    want = _norm(app_id)
    if len(want) < 2:
        return None
    usable = [row for row in apps if not _SKIP.search(row[0])]
    for test in (lambda x: x == want, lambda x: x.startswith(want), lambda x: len(want) >= 4 and want in x):
        found = sorted((row for row in usable if test(_norm(row[0]))), key=lambda x: len(x[0]))
        if found:
            return found[0]
    return None


# --- Bilinen klasör GUID'leri: "{6D809377-…}\\Program\\x.exe" → gerçek yol --------------------

shell32 = ctypes.WinDLL("shell32")
ole32 = ctypes.WinDLL("ole32")
user32 = ctypes.WinDLL("user32")
gdi32 = ctypes.WinDLL("gdi32")
shell32.SHGetKnownFolderPath.argtypes = [POINTER(GUID), wintypes.DWORD, wintypes.HANDLE,
                                         POINTER(ctypes.c_wchar_p)]
shell32.SHGetKnownFolderPath.restype = ctypes.c_long
ole32.CoTaskMemFree.argtypes = [ctypes.c_void_p]
ole32.CoInitializeEx.argtypes = [ctypes.c_void_p, wintypes.DWORD]
ole32.CoInitializeEx.restype = ctypes.c_long
_KF_RE = re.compile(r"^(\{[0-9A-Fa-f-]{36}\})\\(.+)$")


def _known_folder(guid: str) -> str | None:
    p = ctypes.c_wchar_p()
    try:
        if shell32.SHGetKnownFolderPath(byref(GUID(guid)), 0, None, byref(p)) != 0:
            return None
        return p.value
    except OSError:
        return None
    finally:
        if p:
            ole32.CoTaskMemFree(p)


def _exe_path(aumid: str) -> str:
    m = _KF_RE.match(aumid)
    path = None
    if m and (base := _known_folder(m.group(1))):
        path = os.path.join(base, m.group(2))
    elif re.match(r"^[A-Za-z]:\\", aumid):
        path = aumid
    return path if path and path.lower().endswith(".exe") and os.path.isfile(path) else ""


def resolve(app_id: str, title: str = "") -> App | None:
    found = _match(app_id, _start_apps())
    if found is None:
        return None
    name, aumid, exe = found
    exe = exe if exe and os.path.isfile(exe) else _exe_path(aumid)
    return App(id=app_id, title=title or name, icon_name=aumid, desktop=exe)


# --- İkon -------------------------------------------------------------------------------------

class IShellItemImageFactory(IUnknown):
    _iid_ = GUID("{bcc18b79-ba16-442f-80c4-8a59c30c463b}")
    _methods_ = [COMMETHOD([], HRESULT, "GetImage", (["in"], wintypes.SIZE, "size"), (["in"], ctypes.c_int, "flags"),
                           (["out"], POINTER(wintypes.HBITMAP), "phbm"))]


class BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [("biSize", wintypes.DWORD), ("biWidth", wintypes.LONG), ("biHeight", wintypes.LONG),
                ("biPlanes", wintypes.WORD), ("biBitCount", wintypes.WORD), ("biCompression", wintypes.DWORD),
                ("biSizeImage", wintypes.DWORD), ("biXPelsPerMeter", wintypes.LONG),
                ("biYPelsPerMeter", wintypes.LONG), ("biClrUsed", wintypes.DWORD), ("biClrImportant", wintypes.DWORD)]


class BITMAP(ctypes.Structure):
    _fields_ = [("bmType", wintypes.LONG), ("bmWidth", wintypes.LONG), ("bmHeight", wintypes.LONG),
                ("bmWidthBytes", wintypes.LONG), ("bmPlanes", wintypes.WORD), ("bmBitsPixel", wintypes.WORD),
                ("bmBits", ctypes.c_void_p)]


shell32.SHCreateItemFromParsingName.argtypes = [wintypes.LPCWSTR, ctypes.c_void_p, POINTER(GUID),
                                                POINTER(POINTER(IShellItemImageFactory))]
shell32.SHCreateItemFromParsingName.restype = ctypes.c_long
gdi32.GetObjectW.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p]
gdi32.GetDIBits.argtypes = [wintypes.HDC, wintypes.HBITMAP, wintypes.UINT, wintypes.UINT, ctypes.c_void_p,
                            ctypes.c_void_p, wintypes.UINT]
gdi32.DeleteObject.argtypes = [wintypes.HANDLE]
user32.GetDC.argtypes = [wintypes.HWND]
user32.GetDC.restype = wintypes.HDC
user32.ReleaseDC.argtypes = [wintypes.HWND, wintypes.HDC]
SIIGBF_BIGGERSIZEOK, SIIGBF_ICONONLY = 0x1, 0x4


def _shell_image(aumid: str) -> Image.Image | None:
    ole32.CoInitializeEx(None, 0)  # iş parçacığı havuzunda: MTA (zaten başlatılmışsa zararsız)
    fac = POINTER(IShellItemImageFactory)()
    try:
        if shell32.SHCreateItemFromParsingName("shell:AppsFolder\\" + aumid, None,
                                               byref(IShellItemImageFactory._iid_), byref(fac)) != 0:
            return None
        hbmp = fac.GetImage(wintypes.SIZE(ICON_PX, ICON_PX), SIIGBF_ICONONLY | SIIGBF_BIGGERSIZEOK)
    except (OSError, ValueError):
        return None
    try:
        bm = BITMAP()
        gdi32.GetObjectW(hbmp, ctypes.sizeof(bm), byref(bm))
        w, h = bm.bmWidth, abs(bm.bmHeight)
        if not (0 < w <= 1024 and 0 < h <= 1024):
            return None
        bi = BITMAPINFOHEADER(ctypes.sizeof(BITMAPINFOHEADER), w, -h, 1, 32, 0, 0, 0, 0, 0, 0)  # üstten alta
        buf = ctypes.create_string_buffer(w * h * 4)
        dc = user32.GetDC(None)
        try:
            if gdi32.GetDIBits(dc, hbmp, 0, h, buf, byref(bi), 0) != h:
                return None
        finally:
            user32.ReleaseDC(None, dc)
        # Alfa önçarpımsız geliyor (denendi: renk > alfa olan pikseller var)
        return Image.frombuffer("RGBA", (w, h), buf.raw, "raw", "BGRA", 0, 1).copy()
    finally:
        gdi32.DeleteObject(hbmp)


def find_icon(aumid: str) -> str | None:
    """--ayar-kontrol için: ikon alınabiliyorsa kaynağı."""
    return f"shell:AppsFolder\\{aumid}" if aumid and _shell_image(aumid) is not None else None


def icon_bytes(app: App) -> bytes | None:
    img = _shell_image(app.icon_name)
    return encode_icon(img) if img is not None else None


# --- Başlatma / öne getirme --------------------------------------------------------------------

WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
user32.EnumWindows.argtypes = [WNDENUMPROC, wintypes.LPARAM]
user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, POINTER(wintypes.DWORD)]
user32.IsWindowVisible.argtypes = [wintypes.HWND]
user32.GetWindow.argtypes = [wintypes.HWND, wintypes.UINT]
user32.GetWindow.restype = wintypes.HWND
user32.GetWindowTextLengthW.argtypes = [wintypes.HWND]
user32.IsIconic.argtypes = [wintypes.HWND]
user32.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
user32.SetForegroundWindow.argtypes = [wintypes.HWND]
GW_OWNER, SW_RESTORE = 4, 9


def _window_of(exe: str) -> int | None:
    want = os.path.normcase(exe)
    found: list[int] = []
    exe_of: dict[int, str] = {}

    def cb(hwnd, _):
        if not user32.IsWindowVisible(hwnd) or user32.GetWindow(hwnd, GW_OWNER) or not user32.GetWindowTextLengthW(hwnd):
            return True
        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, byref(pid))
        if pid.value not in exe_of:
            try:
                exe_of[pid.value] = os.path.normcase(psutil.Process(pid.value).exe())
            except (psutil.Error, OSError):
                exe_of[pid.value] = ""
        if exe_of[pid.value] == want:
            found.append(hwnd)
            return False
        return True

    user32.EnumWindows(WNDENUMPROC(cb), 0)
    return found[0] if found else None


def _focus(hwnd: int) -> None:
    if user32.IsIconic(hwnd):
        user32.ShowWindow(hwnd, SW_RESTORE)
    winsession.alt_tap()
    user32.SetForegroundWindow(hwnd)


def launch(app: App) -> bool:
    if app.desktop:
        hwnd = _window_of(app.desktop)
        if hwnd:
            _focus(hwnd)
            return True
    try:
        os.startfile("shell:AppsFolder\\" + app.icon_name)  # Mağaza uygulamaları açıksa kendileri öne gelir
        return True
    except OSError:
        pass
    try:
        subprocess.Popen(["explorer.exe", "shell:AppsFolder\\" + app.icon_name], creationflags=NO_WINDOW)
        return True
    except OSError:
        return False
