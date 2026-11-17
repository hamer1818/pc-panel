"""Ayar dosyası: ~/.config/pc-panel/ayarlar.toml (örnek ve açıklamalar: deploy/ayarlar.ornek.toml).

Dosya yoksa örnek dosya kullanılır. Servis dosyanın değişme zamanını birkaç saniyede bir yoklar; değişince yeniden
okur. Hatalı dosyada son geçerli ayarlarla devam edilir. Tek tek hatalı kısayollar atlanır ve günlüğe yazılır.
"""

from __future__ import annotations

import os
import re
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

CONFIG_DIR = Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config") / "pc-panel"
CONFIG_PATH = CONFIG_DIR / "ayarlar.toml"
EXAMPLE_PATH = Path(__file__).resolve().parents[2] / "deploy" / "ayarlar.ornek.toml"

MAX_TILES = 12
MAX_SERVERS = 8
MAX_APPS = 15
TITLE_MAX = 24  # karakter (kutuya sığsın)
DESC_MAX = 28

# Karttaki ikon tablosuyla aynı olmalı (firmware/src/ui.cpp → ICONS)
ICONS = {
    "lock", "mic", "camera", "volume", "terminal", "globe", "folder", "spotify", "code", "gamepad", "steam",
    "discord", "firefox", "chrome", "youtube", "github", "envelope", "calendar", "calculator", "cog", "power",
    "moon", "sync", "desktop", "download", "home", "bolt", "clipboard", "image", "video", "headphones", "star",
    "bell", "search", "keyboard", "file", "rocket", "tv", "wifi", "telegram", "whatsapp", "music", "play",
    "pause", "next", "prev",
}
SPECIALS = {"lock", "mic", "mute", "screenshot"}
MEDIA_ACTIONS = {"play_pause", "next", "prev"}
STEP_KINDS = ("uygulama", "komut", "adres", "ozel", "medya")


@dataclass(frozen=True)
class Step:
    kind: str           # uygulama | komut | adres | ozel | medya | bekle
    value: object


@dataclass(frozen=True)
class Shortcut:
    id: str
    title: str
    desc: str
    icon: str
    steps: tuple[Step, ...]
    toggle: str = ""     # "mic" / "mute": kutu açık/kapalı durumunu gösterir


@dataclass(frozen=True)
class Server:
    name: str
    url: str = ""                       # http(s) denetimi
    tcp: tuple[str, int] | None = None  # yalnızca bağlantı noktası açık mı


DEFAULT_CMD_EXCLUDE = frozenset({
    "nvim", "vim", "vi", "nano", "micro", "hx", "ssh", "mosh", "claude", "claude2", "htop", "btop", "top", "less", "more",
    "man", "watch", "journalctl", "tail", "yazi", "ranger", "lazygit", "tig", "fish", "zsh", "bash", "tmux",
    "zellij", "python", "python3", "ipython", "node", "psql", "mysql", "sqlite3", "adb", "pio",
})


@dataclass
class Settings:
    lock_clock: bool = True
    lock_min: int = 10
    disks: tuple[str, ...] = ("/",)
    notif_on: bool = True
    notif_locked: bool = False
    notif_secs: int = 6
    notif_exclude: frozenset[str] = frozenset({"spotify"})
    warn_cpu: float = 90
    warn_gpu: float = 85
    warn_ram: float = 95
    warn_disk: float = 90
    claude_on: bool = True
    claude_min_s: int = 20
    claude_usage: bool = True
    git_on: bool = True
    git_roots: tuple[str, ...] = ("~",)
    git_days: int = 7
    cmd_on: bool = True
    cmd_min_s: int = 30
    cmd_exclude: frozenset[str] = DEFAULT_CMD_EXCLUDE
    gh_on: bool = True
    gh_repos: tuple[str, ...] = ()
    gh_every_s: int = 120
    srv_every_s: int = 60
    servers: list[Server] = field(default_factory=list)
    apps: list[tuple[str, str]] = field(default_factory=list)  # (masaüstü kimliği, gösterilecek ad ya da "")
    shortcuts: list[Shortcut] = field(default_factory=list)


_TR = str.maketrans("çğıöşüÇĞİÖŞÜ", "cgiosuCGIOSU")


def _slug(text: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", text.translate(_TR).lower()).strip("-")
    return s[:16].strip("-") or "kisayol"


def _num(sec: dict, key: str, default: float, warn: list[str], lo: float = 0, hi: float = 1e6) -> float:
    v = sec.get(key, default)
    if isinstance(v, bool) or not isinstance(v, (int, float)) or not lo <= v <= hi:
        warn.append(f"{key}: geçersiz değer {v!r}, varsayılan {default} kullanılıyor")
        return default
    return v


def _step(d: dict, warn: list[str], where: str) -> Step | None:
    if "bekle" in d:
        v = d["bekle"]
        if isinstance(v, (int, float)) and not isinstance(v, bool) and 0 <= v <= 30:
            return Step("bekle", float(v))
        warn.append(f"{where}: bekle 0–30 sn olmalı")
        return None
    kinds = [k for k in STEP_KINDS if k in d]
    if len(kinds) != 1:
        warn.append(f"{where}: uygulama / komut / adres / ozel / medya / makro alanlarından tam biri olmalı")
        return None
    kind, v = kinds[0], d[kinds[0]]
    if kind == "komut":
        if isinstance(v, list) and v and all(isinstance(a, str) and a for a in v):
            return Step(kind, tuple(v))
        warn.append(f"{where}: komut bir liste olmalı, ör. [\"spectacle\", \"-b\"]")
        return None
    if not isinstance(v, str) or not v:
        warn.append(f"{where}: {kind} boş olamaz")
        return None
    if kind == "ozel" and v not in SPECIALS:
        warn.append(f"{where}: ozel şunlardan biri olmalı: {', '.join(sorted(SPECIALS))}")
        return None
    if kind == "medya" and v not in MEDIA_ACTIONS:
        warn.append(f"{where}: medya şunlardan biri olmalı: {', '.join(sorted(MEDIA_ACTIONS))}")
        return None
    if kind == "adres" and not re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*:", v):
        warn.append(f"{where}: adres bir şema ile başlamalı (https://, file://, steam:// …)")
        return None
    return Step(kind, v)


def _shortcut(d: dict, i: int, used: set[str], warn: list[str]) -> Shortcut | None:
    where = f"kisayol {i + 1}"
    title = d.get("baslik")
    if not isinstance(title, str) or not title.strip():
        warn.append(f"{where}: baslik zorunlu")
        return None
    where = f"kisayol \"{title}\""
    if "makro" in d:
        raw = d["makro"]
        if not isinstance(raw, list) or not raw or not all(isinstance(x, dict) for x in raw):
            warn.append(f"{where}: makro, adımlardan oluşan bir liste olmalı")
            return None
        steps = [_step(x, warn, f"{where} adım {n + 1}") for n, x in enumerate(raw)]
        if any(s is None for s in steps):
            return None
    else:
        s = _step(d, warn, where)
        if s is None:
            return None
        steps = [s]

    icon = d.get("ikon", "star")
    if icon not in ICONS:
        warn.append(f"{where}: bilinmeyen ikon {icon!r}, yıldız kullanılıyor")
        icon = "star"

    toggle = ""
    if len(steps) == 1 and steps[0].kind == "ozel" and steps[0].value in ("mic", "mute"):
        toggle = str(steps[0].value)

    sid = d.get("id")
    if not (isinstance(sid, str) and re.fullmatch(r"[a-z0-9_-]{1,16}", sid)):
        if sid is not None:
            warn.append(f"{where}: id yalnızca a-z 0-9 _ - olabilir (en çok 16), başlıktan üretiliyor")
        single = steps[0] if len(steps) == 1 else None
        sid = str(single.value) if single and single.kind == "ozel" else _slug(title)
    base, n = sid, 2
    while sid in used:
        sid = f"{base[:13]}-{n}"
        n += 1
    used.add(sid)

    desc = d.get("aciklama", "")
    return Shortcut(id=sid, title=title.strip()[:TITLE_MAX], desc=str(desc)[:DESC_MAX], icon=icon,
                    steps=tuple(steps), toggle=toggle)


def parse(data: dict) -> tuple[Settings, list[str]]:
    """TOML sözlüğünden ayarlar; ikinci değer uyarı listesi."""
    warn: list[str] = []
    s = Settings()

    sy = data.get("sistem", {})
    dl = sy.get("diskler")
    if dl is not None:
        if isinstance(dl, list) and dl and all(isinstance(x, str) and x.startswith("/") for x in dl):
            s.disks = tuple(dl[:2])
        else:
            warn.append("sistem.diskler en çok 2 bağlama noktası listesi olmalı, ör. [\"/\", \"/home\"]")

    k = data.get("kilit_ekrani", {})
    s.lock_clock = bool(k.get("saat", s.lock_clock))
    s.lock_min = int(_num(k, "sure_dk", s.lock_min, warn, 0, 24 * 60))

    b = data.get("bildirim", {})
    s.notif_on = bool(b.get("acik", s.notif_on))
    s.notif_locked = bool(b.get("kilitliyken", s.notif_locked))
    s.notif_secs = int(_num(b, "sure_sn", s.notif_secs, warn, 2, 60))
    excl = b.get("haric", ["Spotify"])
    if isinstance(excl, list) and all(isinstance(x, str) for x in excl):
        s.notif_exclude = frozenset(x.casefold() for x in excl)
    else:
        warn.append("bildirim.haric bir yazı listesi olmalı")

    u = data.get("uyari", {})
    s.warn_cpu = _num(u, "cpu_sicaklik", s.warn_cpu, warn, 0, 150)
    s.warn_gpu = _num(u, "gpu_sicaklik", s.warn_gpu, warn, 0, 150)
    s.warn_ram = _num(u, "ram_yuzde", s.warn_ram, warn, 0, 100)
    s.warn_disk = _num(u, "disk_yuzde", s.warn_disk, warn, 0, 100)

    c = data.get("claude", {})
    s.claude_on = bool(c.get("acik", s.claude_on))
    s.claude_min_s = int(_num(c, "bildir_sure_sn", s.claude_min_s, warn, 0, 86400))
    s.claude_usage = bool(c.get("kullanim", s.claude_usage))

    gt = data.get("git", {})
    s.git_on = bool(gt.get("acik", s.git_on))
    s.git_days = int(_num(gt, "gun", s.git_days, warn, 1, 365))
    roots = gt.get("klasorler")
    if roots is not None:
        if isinstance(roots, list) and all(isinstance(x, str) and x for x in roots):
            s.git_roots = tuple(roots[:5])
        else:
            warn.append("git.klasorler bir yazı listesi olmalı")

    k = data.get("komut", {})
    s.cmd_on = bool(k.get("acik", s.cmd_on))
    s.cmd_min_s = int(_num(k, "sure_sn", s.cmd_min_s, warn, 5, 86400))
    excl = k.get("haric")
    if excl is not None:
        if isinstance(excl, list) and all(isinstance(x, str) for x in excl):
            s.cmd_exclude = frozenset(excl)
        else:
            warn.append("komut.haric bir yazı listesi olmalı")

    g = data.get("github", {})
    s.gh_on = bool(g.get("acik", s.gh_on))
    s.gh_every_s = int(_num(g, "sure_sn", s.gh_every_s, warn, 30, 3600))
    repos = g.get("depolar", [])
    if isinstance(repos, list) and all(isinstance(x, str) and re.fullmatch(r"[\w.-]+/[\w.-]+", x) for x in repos):
        s.gh_repos = tuple(repos[:8])
    else:
        warn.append("github.depolar \"sahip/depo\" biçiminde yazılardan oluşan bir liste olmalı")

    srv_cfg = data.get("sunucular", {})
    s.srv_every_s = int(_num(srv_cfg, "sure_sn", s.srv_every_s, warn, 15, 3600))
    raw_srv = data.get("sunucu", [])
    if not isinstance(raw_srv, list):
        raw_srv = []
        warn.append("sunucu bölümleri [[sunucu]] biçiminde yazılmalı")
    if len(raw_srv) > MAX_SERVERS:
        warn.append(f"en çok {MAX_SERVERS} sunucu gösterilebilir; fazlası atlandı")
    for i, d in enumerate(raw_srv[:MAX_SERVERS]):
        name = d.get("ad") if isinstance(d, dict) else None
        if not isinstance(name, str) or not name.strip():
            warn.append(f"sunucu {i + 1}: ad zorunlu")
            continue
        url, tcp = d.get("adres", ""), d.get("tcp", "")
        if isinstance(url, str) and re.match(r"^https?://", url):
            s.servers.append(Server(name=name.strip()[:20], url=url))
        elif isinstance(tcp, str) and (m := re.fullmatch(r"([\w.-]+):(\d{1,5})", tcp)):
            s.servers.append(Server(name=name.strip()[:20], tcp=(m.group(1), int(m.group(2)))))
        else:
            warn.append(f"sunucu \"{name}\": adres = \"https://…\" ya da tcp = \"makine:port\" olmalı")

    ua = data.get("uygulamalar", {})
    raw_apps = ua.get("liste", [])
    if not isinstance(raw_apps, list):
        warn.append("uygulamalar.liste bir liste olmalı")
        raw_apps = []
    if len(raw_apps) > MAX_APPS:
        warn.append(f"en çok {MAX_APPS} uygulama gösterilebilir; fazlası atlandı")
    for x in raw_apps[:MAX_APPS]:
        app_id, title = (x, "") if isinstance(x, str) else ((x.get("id"), x.get("ad", "")) if isinstance(x, dict)
                                                             else (None, ""))
        if isinstance(app_id, str) and re.fullmatch(r"[\w.+-]{1,80}", app_id) and isinstance(title, str):
            s.apps.append((app_id, title.strip()[:TITLE_MAX]))
        else:
            warn.append(f"uygulamalar: geçersiz kayıt {x!r} (\"kimlik\" ya da {{id = \"kimlik\", ad = \"Ad\"}})")

    raw = data.get("kisayol", [])
    if not isinstance(raw, list):
        warn.append("kisayol bölümleri [[kisayol]] biçiminde yazılmalı")
        raw = []
    if len(raw) > MAX_TILES:
        warn.append(f"en çok {MAX_TILES} kısayol gösterilebilir; fazlası atlandı")
    used: set[str] = set()
    for i, d in enumerate(raw[:MAX_TILES]):
        sc = _shortcut(d, i, used, warn) if isinstance(d, dict) else None
        if sc:
            s.shortcuts.append(sc)
    return s, warn


class ConfigWatcher:
    """Ayar dosyasını okur ve değişince yeniden yükler. `version` her başarılı yüklemede artar."""

    def __init__(self, path: Path = CONFIG_PATH, log=print) -> None:
        self.path = path
        self.log = log
        self.settings = Settings()
        self.version = 0
        self._stamp: tuple | None = None
        self.check()

    def _source(self) -> Path | None:
        if self.path.exists():
            return self.path
        return EXAMPLE_PATH if EXAMPLE_PATH.exists() else None

    def check(self) -> bool:
        """Dosya değiştiyse yeniden yükler; yeni ayarlar yüklendiyse True döner."""
        src = self._source()
        try:
            st = src.stat() if src else None
        except OSError:
            st = None
        stamp = (str(src), st.st_mtime_ns, st.st_size) if st else None
        if stamp == self._stamp:
            return False
        self._stamp = stamp
        if src is None:
            if self.version == 0:
                self.log("ayar dosyası yok, varsayılanlar kullanılıyor")
                self.version = 1
                return True
            return False
        try:
            with open(src, "rb") as f:
                data = tomllib.load(f)
        except (OSError, tomllib.TOMLDecodeError) as e:
            self.log(f"ayar dosyası okunamadı ({src}): {e} — önceki ayarlarla devam")
            if self.version == 0:
                self.version = 1
                return True
            return False
        settings, warnings = parse(data)
        for w in warnings:
            self.log(f"ayar uyarısı: {w}")
        self.settings = settings
        self.version += 1
        self.log(f"ayarlar yüklendi: {src} ({len(settings.shortcuts)} kısayol)")
        return True
