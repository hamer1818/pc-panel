"""Medya bilgisi ve kontrolü: MPRIS (D-Bus oturum veri yolu).

KDE'deki bütün çalarlar (Spotify, tarayıcılar, VLC, Elisa, KDE Connect...) `org.mpris.MediaPlayer2.*`
adıyla kaydolur. Her saniye bütün çaların durumunu okuyup "etkin" olanı seçeriz:
  1. Çalmakta olanlar arasında en son çalmaya başlayan,
  2. hiçbiri çalmıyorsa en son çalan,
  3. o da yoksa ilk bulunan.
"""

from __future__ import annotations

import asyncio
import time

from dbus_fast import BusType, Message, MessageType, Variant
from dbus_fast.aio import MessageBus

MPRIS_PREFIX = "org.mpris.MediaPlayer2."
MPRIS_PATH = "/org/mpris/MediaPlayer2"
PLAYER_IFACE = "org.mpris.MediaPlayer2.Player"
ROOT_IFACE = "org.mpris.MediaPlayer2"
PROPS_IFACE = "org.freedesktop.DBus.Properties"
CALL_TIMEOUT = 1.0  # takılan bir çalar bütün servisi bekletmesin


def _unwrap(v):
    if isinstance(v, Variant):
        return _unwrap(v.value)
    if isinstance(v, dict):
        return {k: _unwrap(x) for k, x in v.items()}
    if isinstance(v, list):
        return [_unwrap(x) for x in v]
    return v


class MediaWatcher:
    def __init__(self) -> None:
        self.bus: MessageBus | None = None
        self._identity: dict[str, str] = {}
        self._status: dict[str, str] = {}
        self._playing_since: dict[str, float] = {}  # çalar → en son "Playing"e geçtiği an
        self._last_playing: dict[str, float] = {}   # çalar → en son "Playing" görüldüğü an
        self.active: str | None = None

    async def connect(self) -> None:
        self.bus = await MessageBus(bus_type=BusType.SESSION).connect()

    async def _call(self, **kw) -> Message | None:
        assert self.bus is not None
        try:
            reply = await asyncio.wait_for(self.bus.call(Message(**kw)), CALL_TIMEOUT)
        except (asyncio.TimeoutError, Exception):
            return None
        if reply is None or reply.message_type == MessageType.ERROR:
            return None
        return reply

    async def _list_players(self) -> list[str]:
        r = await self._call(destination="org.freedesktop.DBus", path="/org/freedesktop/DBus",
                             interface="org.freedesktop.DBus", member="ListNames")
        return sorted(n for n in (r.body[0] if r else []) if n.startswith(MPRIS_PREFIX))

    async def _get_all(self, name: str) -> dict | None:
        r = await self._call(destination=name, path=MPRIS_PATH, interface=PROPS_IFACE,
                             member="GetAll", signature="s", body=[PLAYER_IFACE])
        return _unwrap(r.body[0]) if r else None

    async def _get_identity(self, name: str) -> str:
        if name not in self._identity:
            r = await self._call(destination=name, path=MPRIS_PATH, interface=PROPS_IFACE,
                                 member="Get", signature="ss", body=[ROOT_IFACE, "Identity"])
            self._identity[name] = _unwrap(r.body[0]) if r else name[len(MPRIS_PREFIX):]
        return self._identity[name]

    async def poll(self) -> dict:
        """Bütün çalarları okur; {"active": {...} | None, "players": [...]} döner."""
        names = await self._list_players()
        now = time.monotonic()
        states: dict[str, dict] = {}
        for name in names:
            props = await self._get_all(name)
            if props is None:
                continue
            status = props.get("PlaybackStatus", "Stopped")
            if status == "Playing":
                if self._status.get(name) != "Playing":
                    self._playing_since[name] = now
                self._last_playing[name] = now
            self._status[name] = status
            states[name] = props

        # Kapanan çalarları unut
        for d in (self._identity, self._status, self._playing_since, self._last_playing):
            for gone in set(d) - set(names):
                d.pop(gone, None)

        playing = [n for n in states if states[n].get("PlaybackStatus") == "Playing"]
        if playing:
            self.active = max(playing, key=lambda n: self._playing_since.get(n, 0))
        elif states:
            self.active = max(states, key=lambda n: self._last_playing.get(n, 0))
        else:
            self.active = None

        players = [{"name": n, "identity": await self._get_identity(n),
                    "status": states[n].get("PlaybackStatus")} for n in states]
        active = None
        if self.active:
            active = self._describe(self.active, await self._get_identity(self.active), states[self.active])
        return {"active": active, "players": players}

    @staticmethod
    def _describe(name: str, identity: str, p: dict) -> dict:
        md = p.get("Metadata", {}) or {}
        artists = md.get("xesam:artist") or []
        if isinstance(artists, str):
            artists = [artists]
        length_us = md.get("mpris:length")
        return {
            "player": identity,
            "bus_name": name,
            "status": p.get("PlaybackStatus"),        # Playing / Paused / Stopped
            "title": md.get("xesam:title") or "",
            "artist": ", ".join(a for a in artists if a),
            "album": md.get("xesam:album") or "",
            "art_url": md.get("mpris:artUrl") or "",
            "track_id": md.get("mpris:trackid") or "",
            "length_s": round(length_us / 1e6) if length_us else None,
            "position_s": round(p["Position"] / 1e6) if p.get("Position") is not None else None,
            "volume": round(p["Volume"] * 100) if isinstance(p.get("Volume"), (int, float)) else None,
            "shuffle": p.get("Shuffle"),
            "loop": p.get("LoopStatus"),
            "can": {
                "play_pause": bool(p.get("CanPause") or p.get("CanPlay")),
                "next": bool(p.get("CanGoNext")),
                "prev": bool(p.get("CanGoPrevious")),
                "seek": bool(p.get("CanSeek")),
            },
        }

    # --- Kontrol komutları (Faz 3'te karttan gelen dokunmalar bunları çağıracak) ---

    async def command(self, cmd: str, value: float | None = None, bus_name: str | None = None) -> bool:
        """cmd: play_pause | play | pause | next | prev | seek_rel (sn) | seek_abs (sn)."""
        name = bus_name or self.active
        if not name:
            return False
        simple = {"play_pause": "PlayPause", "play": "Play", "pause": "Pause",
                  "next": "Next", "prev": "Previous", "stop": "Stop"}
        if cmd in simple:
            r = await self._call(destination=name, path=MPRIS_PATH, interface=PLAYER_IFACE, member=simple[cmd])
            return r is not None
        if cmd == "seek_rel" and value is not None:
            r = await self._call(destination=name, path=MPRIS_PATH, interface=PLAYER_IFACE,
                                 member="Seek", signature="x", body=[int(value * 1e6)])
            return r is not None
        if cmd == "seek_abs" and value is not None:
            props = await self._get_all(name)
            track = (props or {}).get("Metadata", {}).get("mpris:trackid")
            if not track:
                return False
            r = await self._call(destination=name, path=MPRIS_PATH, interface=PLAYER_IFACE,
                                 member="SetPosition", signature="ox", body=[track, int(value * 1e6)])
            return r is not None
        return False
