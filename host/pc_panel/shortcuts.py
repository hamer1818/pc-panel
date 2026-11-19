"""Karttaki Kısayollar sayfasının bilgisayardaki karşılıkları.

Kısayollar ayar dosyasından gelir (bkz. config.py, deploy/ayarlar.ornek.toml).

GÜVENLİK: Kart yalnızca bir kısayol kimliği (`id`) gönderir. Bilgisayar bu kimliği o anki ayarlardaki listede arar
ve oradaki adımları uygular. Karttan gelen hiçbir metin komut satırına eklenmez; bilinmeyen kimlikler reddedilir.
Komutlar kabuk olmadan (argüman listesiyle) çalıştırılır.

Linux: kstart / xdg-open / spectacle / loginctl. Windows: Başlat menüsü uygulaması (win/apps.py) / varsayılan
program (os.startfile) / Win+PrtScn / LockWorkStation. Windows'ta komutlar konsol penceresi açmadan çalışır
(Linux'taki gibi arka planda); pencereli programlar (wt, notepad …) normal açılır.
"""

from __future__ import annotations

import asyncio
import os
import subprocess

from .backend import WINDOWS, apps as appmod, audio
from .config import Shortcut, Step

if WINDOWS:
    from .win import session as winsession

    SPECIAL_FN = {"screenshot": winsession.screenshot, "lock": winsession.lock}
    SPAWN_FLAGS = {"creationflags": subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP}
else:
    SPECIAL_ARGV = {
        # Spectacle: arka planda (-b), bildirim olmadan (-n), tam ekran (-f); varsayılan klasöre kaydeder
        "screenshot": ["spectacle", "-b", "-n", "-f"],
        "lock": ["loginctl", "lock-session"],
    }
    SPAWN_FLAGS = {"start_new_session": True}
TOGGLES = {"mute": audio.toggle_mute, "mic": audio.toggle_mic}


def _spawn(argv: list[str]) -> bool:
    try:
        subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                         env=os.environ.copy(), **SPAWN_FLAGS)
        return True
    except OSError:
        return False


def _open(target: str) -> bool:
    """Adresi / dosyayı varsayılan programda açar."""
    if not WINDOWS:
        return _spawn(["xdg-open", target])
    try:
        os.startfile(target)
        return True
    except OSError:
        return False


def _app(app_id: str) -> bool:
    """Uygulamayı açar ya da açıksa öne getirir."""
    if not WINDOWS:
        return _spawn(["kstart", "--application", app_id])  # pencere varsa öne gelir, yoksa açılır
    app = appmod.resolve(app_id)
    return appmod.launch(app) if app else False


async def _step(step: Step, media) -> bool:
    kind, v = step.kind, step.value
    if kind == "bekle":
        await asyncio.sleep(float(v))
        return True
    if kind == "ozel":
        if v in TOGGLES:
            return await TOGGLES[v]()
        if WINDOWS:
            return SPECIAL_FN[v]()
        return await asyncio.to_thread(_spawn, SPECIAL_ARGV[v])
    if kind == "medya":
        await media.poll()  # etkin çalar güncel olsun (ör. makroda az önce açılan Spotify)
        return await media.command(str(v))
    if kind == "uygulama":
        return await asyncio.to_thread(_app, str(v))
    if kind == "adres":
        return await asyncio.to_thread(_open, str(v))
    return await asyncio.to_thread(_spawn, list(v))  # komut


async def run(sc: Shortcut, media) -> bool:
    """Kısayolun adımlarını sırayla uygular. Bir adım başarısız olursa durur."""
    for step in sc.steps:
        if not await _step(step, media):
            return False
    return True
