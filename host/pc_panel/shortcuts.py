"""Karttaki Kısayollar sayfasının bilgisayardaki karşılıkları.

GÜVENLİK: Kart yalnızca aşağıdaki sözlükte bulunan bir kimlik (`id`) gönderebilir. Karttan gelen hiçbir metin
komut satırına eklenmez; bilinmeyen kimlikler reddedilir. Yeni kısayol eklemek için bu dosyayı düzenleyin
(kart tarafında da `firmware/src/ui.cpp` içindeki kutu listesine eklenmeli).
"""

from __future__ import annotations

import asyncio
import os
import subprocess

from . import audio

# Uygulamaları masaüstü kimlikleriyle başlatır (KDE `kstart`): pencere varsa öne gelir, yoksa açılır.
APPS: dict[str, list[str]] = {
    "terminal": ["kstart", "--application", "org.kde.konsole"],
    "browser": ["kstart", "--application", "userapp-Zen-83YBT3"],   # varsayılan tarayıcı: Zen
    "files": ["kstart", "--application", "org.kde.dolphin"],
    "spotify": ["kstart", "--application", "spotify"],
    # Spectacle: arka planda (-b), bildirim olmadan (-n), tam ekran (-f); varsayılan klasöre kaydeder
    "screenshot": ["spectacle", "-b", "-n", "-f"],
    "lock": ["loginctl", "lock-session"],
}

TOGGLES = {
    "mute": audio.toggle_mute,
    "mic": audio.toggle_mic,
}

ALL_IDS = set(APPS) | set(TOGGLES)


def _spawn(argv: list[str]) -> bool:
    try:
        subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                         start_new_session=True, env=os.environ.copy())
        return True
    except OSError:
        return False


async def run(shortcut_id: str) -> bool:
    if shortcut_id in TOGGLES:
        return await TOGGLES[shortcut_id]()
    argv = APPS.get(shortcut_id)
    if argv is None:
        return False
    return await asyncio.to_thread(_spawn, argv)
