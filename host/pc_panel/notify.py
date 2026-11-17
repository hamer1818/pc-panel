"""Masaüstü bildirimlerini izleme (D-Bus `org.freedesktop.Notifications.Notify` çağrıları).

Ayrı bir oturum veri yolu bağlantısı `BecomeMonitor` ile "izleyici" yapılır: uygulamaların bildirim sunucusuna
(KDE'de plasmashell) yaptığı `Notify` çağrılarının bir kopyası bize gelir. Bildirimlere dokunulmaz, yanıt
verilmez; izleyici bağlantı mesaj gönderemez. Ayrıntı: docs/kararlar.md.
"""

from __future__ import annotations

import asyncio
import html
import re
from collections.abc import Callable

from dbus_fast import BusType, Message, MessageType
from dbus_fast.aio import MessageBus

MATCH = "type='method_call',interface='org.freedesktop.Notifications',member='Notify'"
RETRY_S = 5.0
_TAG = re.compile(r"<[^>]*>")
_SPACE = re.compile(r"\s+")


def _plain(text: str) -> str:
    """KDE bildirimleri basit HTML içerebilir (<b>, <a href>, &amp;): düz metne çevir."""
    return _SPACE.sub(" ", html.unescape(_TAG.sub(" ", text or ""))).strip()


class NotificationWatcher:
    def __init__(self, on_notify: Callable[[dict], None], log=print) -> None:
        self.on_notify = on_notify
        self.log = log

    def _handler(self, msg: Message) -> bool:
        # True döndür: dbus-fast "bilinmeyen yöntem" hatasıyla yanıt vermeye kalkmasın (izleyici gönderemez)
        try:
            if msg.message_type == MessageType.METHOD_CALL and msg.member == "Notify" and len(msg.body) >= 7:
                app, _rid, _icon, summary, body, _actions, hints = msg.body[:7]
                entry = hints.get("desktop-entry") if isinstance(hints, dict) else None
                self.on_notify({
                    "app": _plain(str(app)),
                    "entry": str(entry.value) if entry is not None else "",
                    "title": _plain(str(summary)),
                    "body": _plain(str(body)),
                })
        except Exception as e:  # izleyici hiçbir durumda düşmesin
            self.log(f"bildirim okunamadı: {e}")
        return True

    async def run(self) -> None:
        """İzleyici bağlantıyı açık tutar; koparsa RETRY_S sonra yeniden kurar."""
        warned = False
        while True:
            bus = None
            try:
                bus = await MessageBus(bus_type=BusType.SESSION).connect()
                reply = await bus.call(Message(
                    destination="org.freedesktop.DBus", path="/org/freedesktop/DBus",
                    interface="org.freedesktop.DBus.Monitoring", member="BecomeMonitor",
                    signature="asu", body=[[MATCH], 0]))
                if reply is None or reply.message_type == MessageType.ERROR:
                    raise RuntimeError(reply.body[0] if reply and reply.body else "BecomeMonitor reddedildi")
                bus.add_message_handler(self._handler)
                warned = False
                await bus.wait_for_disconnect()
            except asyncio.CancelledError:
                if bus:
                    bus.disconnect()
                raise
            except Exception as e:
                if not warned:
                    self.log(f"bildirimler izlenemiyor: {e} (yeniden denenecek)")
                    warned = True
            await asyncio.sleep(RETRY_S)
