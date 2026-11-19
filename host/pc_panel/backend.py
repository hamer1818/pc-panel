"""İşletim sistemine göre medya / ses / bildirim / uygulama modüllerini seçer.

Linux (KDE Plasma): MPRIS + D-Bus, PipeWire (`wpctl`), `.desktop` dosyaları + `kstart`.
Windows 10/11: GSMTC (medya), Core Audio (ses), UserNotificationListener, Başlat menüsü uygulamaları.
İki taraf da aynı adları sunar: MediaWatcher, NotificationWatcher, audio.state/set_volume/…, apps.resolve/launch/….
"""

from __future__ import annotations

import sys

WINDOWS = sys.platform == "win32"

if WINDOWS:
    from .win import apps, audio, media, notify  # noqa: F401
else:
    from . import apps, audio, media, notify  # noqa: F401
