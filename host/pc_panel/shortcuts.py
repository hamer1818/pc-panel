"""Karttaki Kısayollar sayfasının bilgisayardaki karşılıkları.

Kısayollar ayar dosyasından gelir (bkz. config.py, deploy/ayarlar.ornek.toml).

GÜVENLİK: Kart yalnızca bir kısayol kimliği (`id`) gönderir. Bilgisayar bu kimliği o anki ayarlardaki listede arar
ve oradaki adımları uygular. Karttan gelen hiçbir metin komut satırına eklenmez; bilinmeyen kimlikler reddedilir.
Komutlar kabuk olmadan (argüman listesiyle) çalıştırılır.
"""

from __future__ import annotations

import asyncio
import os
import subprocess

from . import audio
from .config import Shortcut, Step

SPECIAL_ARGV = {
    # Spectacle: arka planda (-b), bildirim olmadan (-n), tam ekran (-f); varsayılan klasöre kaydeder
    "screenshot": ["spectacle", "-b", "-n", "-f"],
    "lock": ["loginctl", "lock-session"],
}
TOGGLES = {"mute": audio.toggle_mute, "mic": audio.toggle_mic}


def _spawn(argv: list[str]) -> bool:
    try:
        subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                         start_new_session=True, env=os.environ.copy())
        return True
    except OSError:
        return False


async def _step(step: Step, media) -> bool:
    kind, v = step.kind, step.value
    if kind == "bekle":
        await asyncio.sleep(float(v))
        return True
    if kind == "ozel":
        if v in TOGGLES:
            return await TOGGLES[v]()
        return await asyncio.to_thread(_spawn, SPECIAL_ARGV[v])
    if kind == "medya":
        await media.poll()  # etkin çalar güncel olsun (ör. makroda az önce açılan Spotify)
        return await media.command(str(v))
    argv = {
        "uygulama": lambda: ["kstart", "--application", str(v)],  # pencere varsa öne gelir, yoksa açılır
        "komut": lambda: list(v),
        "adres": lambda: ["xdg-open", str(v)],
    }[kind]()
    return await asyncio.to_thread(_spawn, argv)


async def run(sc: Shortcut, media) -> bool:
    """Kısayolun adımlarını sırayla uygular. Bir adım başarısız olursa durur."""
    for step in sc.steps:
        if not await _step(step, media):
            return False
    return True
