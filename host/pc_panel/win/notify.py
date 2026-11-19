"""Masaüstü bildirimlerini izleme — Windows: UserNotificationListener (winrt). Linux karşılığı: notify.py (D-Bus).

Bildirim merkezindeki "toast" bildirimleri saniyede bir okunur; yeni kimlikler karta iletilir. Bildirimlere dokunulmaz.
İzin: Ayarlar → Gizlilik ve güvenlik → Bildirimler → "Uygulamaların bildirimlerime erişmesine izin ver".
İlk okumada zaten bekleyen bildirimler gönderilmez (servis açılınca eski bildirimler yağmasın).
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable

from winrt.windows.ui.notifications import KnownNotificationBindings, NotificationKinds
from winrt.windows.ui.notifications.management import UserNotificationListener, UserNotificationListenerAccessStatus

POLL_S = 1.0
RETRY_S = 30.0


def _toast_binding_name() -> str:
    try:
        return KnownNotificationBindings.toast_generic
    except Exception:
        return "ToastGeneric"


class NotificationWatcher:
    def __init__(self, on_notify: Callable[[dict], None], log=print) -> None:
        self.on_notify = on_notify
        self.log = log

    def _emit(self, n) -> None:
        app = entry = ""
        try:
            info = n.app_info
            entry = info.app_user_model_id or ""
            app = info.display_info.display_name or ""
        except Exception:
            pass
        texts: list[str] = []
        try:
            binding = n.notification.visual.get_binding(_toast_binding_name())
            if binding is not None:
                texts = [t.text for t in binding.get_text_elements() if t.text]
        except Exception:
            pass
        self.on_notify({"app": app, "entry": entry, "title": texts[0] if texts else "",
                        "body": " ".join(texts[1:])})

    async def run(self) -> None:
        warned = False
        while True:
            try:
                listener = UserNotificationListener.current
                status = await listener.request_access_async()
                if status != UserNotificationListenerAccessStatus.ALLOWED:
                    raise PermissionError("erişim izni yok (Ayarlar → Gizlilik ve güvenlik → Bildirimler)")
                seen: set[int] | None = None
                warned = False
                while True:
                    items = await listener.get_notifications_async(NotificationKinds.TOAST)
                    ids = set()
                    for n in items:
                        ids.add(n.id)
                        if seen is not None and n.id not in seen:
                            try:
                                self._emit(n)
                            except Exception as e:  # izleyici hiçbir durumda düşmesin
                                self.log(f"bildirim okunamadı: {e}")
                    seen = ids
                    await asyncio.sleep(POLL_S)
            except asyncio.CancelledError:
                raise
            except Exception as e:
                if not warned:
                    self.log(f"bildirimler izlenemiyor: {e} (yeniden denenecek)")
                    warned = True
            await asyncio.sleep(RETRY_S)
