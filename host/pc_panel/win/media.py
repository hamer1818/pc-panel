"""Medya bilgisi ve kontrolü — Windows: GSMTC (GlobalSystemMediaTransportControlsSessionManager, winrt).

Windows 10/11'deki bütün "medya oturumları" (Spotify, tarayıcılar, Medya Oynatıcı, VLC…) buradan görünür:
sistemin ses açılır penceresindeki medya kutusuyla aynı kaynak. Linux karşılığı: media.py (MPRIS); çıktı
biçimi ve "etkin çalar" seçimi aynıdır:
  1. Çalmakta olanlar arasında en son çalmaya başlayan,
  2. hiçbiri çalmıyorsa en son çalan,
  3. o da yoksa Windows'un "geçerli" saydığı oturum ya da ilk bulunan.

Kapak resmi bir adres değil, oturumun verdiği bir akıştır. `art_url` alanına parça bilgisinden üretilen bir anahtar
("gsmtc:…") yazılır; servis kapağı `fetch_art(anahtar)` ile ister.
Konum: GSMTC konumu yalnızca durum değişince günceller; çalarken geçen süre `last_updated_time`'dan hesaplanır.
"""

from __future__ import annotations

import asyncio
import time
from datetime import datetime, timedelta, timezone

from winrt.windows.media.control import (
    GlobalSystemMediaTransportControlsSessionManager as SessionManager,
    GlobalSystemMediaTransportControlsSessionPlaybackStatus as PlaybackStatus,
)
from winrt.windows.storage.streams import DataReader, InputStreamOptions

from .. import art
from . import session as winsession

CALL_TIMEOUT = 1.0
_STATUS = {PlaybackStatus.PLAYING: "Playing", PlaybackStatus.PAUSED: "Paused"}
# AUMID'den ad çıkarılamayan bilinen tarayıcılar (Firefox türevleri kurulum yoluna göre karma kimlik kullanır)
_KNOWN = {"308046B0AF4A39CB": "Firefox", "F0DC299D809B9700": "Zen", "6F193CCC56814779": "Firefox Nightly"}
_TICKS = 10_000_000  # TimeSpan: 100 ns


def _secs(v) -> float | None:
    if isinstance(v, timedelta):
        return v.total_seconds()
    if isinstance(v, (int, float)):
        return v / _TICKS
    return None


def _friendly(aumid: str) -> str:
    """Uygulama kimliğinden okunur ad: önce Windows'tan (AppInfo), olmazsa kimliğin kendisinden."""
    try:
        from winrt.windows.applicationmodel import AppInfo
        name = AppInfo.get_from_app_user_model_id(aumid).display_info.display_name
        if name:
            return name
    except Exception:
        pass
    if aumid in _KNOWN:
        return _KNOWN[aumid]
    name = aumid.split("!")[-1] if "!" in aumid else aumid
    name = name.rsplit("\\", 1)[-1].removesuffix(".exe").removesuffix(".EXE")
    return {"msedge": "Edge", "chrome": "Chrome", "vlc": "VLC", "app": "Medya"}.get(name.lower(), name) or aumid


class MediaWatcher:
    def __init__(self) -> None:
        self.manager = None
        self._identity: dict[str, str] = {}
        self._status: dict[str, str] = {}
        self._playing_since: dict[str, float] = {}
        self._last_playing: dict[str, float] = {}
        self._sessions: dict[str, object] = {}   # kimlik → oturum (komutlar için)
        self._thumbs: dict[str, object] = {}     # kapak anahtarı → IRandomAccessStreamReference
        self.active: str | None = None

    async def connect(self) -> None:
        try:
            self.manager = await asyncio.wait_for(SessionManager.request_async(), 5.0)
        except Exception:
            self.manager = None  # poll() yeniden dener

    async def screen_locked(self) -> bool | None:
        return winsession.screen_locked()

    def _identity_of(self, aumid: str) -> str:
        if aumid not in self._identity:
            self._identity[aumid] = _friendly(aumid)
        return self._identity[aumid]

    async def poll(self) -> dict:
        """Bütün medya oturumlarını okur; {"active": {...} | None, "players": [...]} döner."""
        if self.manager is None:
            await self.connect()
            if self.manager is None:
                return {"active": None, "players": []}
        try:
            sessions = list(self.manager.get_sessions())
            current = self.manager.get_current_session()
            current_id = current.source_app_user_model_id if current else None
        except Exception:
            self.manager = None  # Explorer yeniden başladıysa yöneticiyi yeniden iste
            return {"active": None, "players": []}

        now = time.monotonic()
        states: dict[str, dict] = {}
        self._sessions = {}
        for s in sessions:
            try:
                sid = s.source_app_user_model_id
                if sid in states:
                    continue  # aynı uygulamanın ikinci oturumu (ör. iki tarayıcı sekmesi): ilki yeter
                info = s.get_playback_info()
                props = await asyncio.wait_for(s.try_get_media_properties_async(), CALL_TIMEOUT)
                timeline = s.get_timeline_properties()
            except Exception:
                continue
            status = _STATUS.get(info.playback_status, "Stopped")
            if status == "Playing":
                if self._status.get(sid) != "Playing":
                    self._playing_since[sid] = now
                self._last_playing[sid] = now
            self._status[sid] = status
            states[sid] = {"status": status, "info": info, "props": props, "timeline": timeline}
            self._sessions[sid] = s

        for d in (self._identity, self._status, self._playing_since, self._last_playing):
            for gone in set(d) - set(states):
                d.pop(gone, None)

        playing = [n for n in states if states[n]["status"] == "Playing"]
        if playing:
            self.active = max(playing, key=lambda n: self._playing_since.get(n, 0))
        elif states:
            self.active = max(states, key=lambda n: (self._last_playing.get(n, 0), n == current_id))
        else:
            self.active = None

        players = [{"name": n, "identity": self._identity_of(n), "status": states[n]["status"]} for n in states]
        active = self._describe(self.active, states[self.active]) if self.active else None
        return {"active": active, "players": players}

    def _describe(self, sid: str, st: dict) -> dict:
        props, info, tl, status = st["props"], st["info"], st["timeline"], st["status"]
        title = props.title or ""
        artist = props.artist or props.album_artist or ""
        album = props.album_title or ""

        art_key = ""
        if props.thumbnail is not None:
            art_key = f"gsmtc:{sid}|{title}|{artist}|{album}"
            if art_key not in self._thumbs:
                if len(self._thumbs) > 20:
                    self._thumbs.clear()
                self._thumbs[art_key] = props.thumbnail

        length = position = None
        try:
            start, end = _secs(tl.start_time) or 0.0, _secs(tl.end_time) or 0.0
            if end > start:
                length = end - start
                position = (_secs(tl.position) or 0.0) - start
                if status == "Playing" and isinstance(tl.last_updated_time, datetime):
                    updated = tl.last_updated_time
                    if updated.tzinfo is None:
                        updated = updated.replace(tzinfo=timezone.utc)
                    position += max(0.0, (datetime.now(timezone.utc) - updated).total_seconds())
                position = max(0.0, min(position, length))
        except Exception:
            pass

        c = info.controls
        return {
            "player": self._identity_of(sid),
            "bus_name": sid,
            "status": status,
            "title": title,
            "artist": artist,
            "album": album,
            "art_url": art_key,
            "track_id": "",
            "length_s": round(length) if length else None,
            "position_s": round(position) if position is not None else None,
            "volume": None,  # uygulama başına ses GSMTC'de yok; kart sistem sesini gösterir
            "shuffle": info.is_shuffle_active,
            "loop": None,
            "can": {
                "play_pause": bool(c.is_play_pause_toggle_enabled or c.is_play_enabled or c.is_pause_enabled),
                "next": bool(c.is_next_enabled),
                "prev": bool(c.is_previous_enabled),
                "seek": bool(c.is_playback_position_enabled) and bool(length),
            },
        }

    async def fetch_art(self, key: str) -> bytes | None:
        """Kapak anahtarı → 240×240 RGB565 (art.from_bytes) ya da None."""
        ref = self._thumbs.get(key)
        if ref is None:
            return None
        try:
            stream = await asyncio.wait_for(ref.open_read_async(), 3.0)
            size = int(stream.size)
            if not size or size > art.MAX_DOWNLOAD:
                return None
            reader = DataReader(stream.get_input_stream_at(0))
            reader.input_stream_options = InputStreamOptions.READ_AHEAD
            await asyncio.wait_for(reader.load_async(size), 3.0)
            data = bytes(reader.read_buffer(size))
        except Exception:
            return None
        return await asyncio.to_thread(art.from_bytes, data)

    # --- Kontrol komutları ---

    async def _position(self, s) -> float | None:
        try:
            tl = s.get_timeline_properties()
            pos = (_secs(tl.position) or 0.0) - (_secs(tl.start_time) or 0.0)
            if s.get_playback_info().playback_status == PlaybackStatus.PLAYING and isinstance(tl.last_updated_time, datetime):
                pos += max(0.0, (datetime.now(timezone.utc) - tl.last_updated_time).total_seconds())
            return pos
        except Exception:
            return None

    async def command(self, cmd: str, value: float | None = None, bus_name: str | None = None) -> bool:
        """cmd: play_pause | play | pause | next | prev | stop | seek_rel (sn) | seek_abs (sn)."""
        s = self._sessions.get(bus_name or self.active or "")
        if s is None:
            return False
        try:
            simple = {"play_pause": s.try_toggle_play_pause_async, "play": s.try_play_async,
                      "pause": s.try_pause_async, "next": s.try_skip_next_async,
                      "prev": s.try_skip_previous_async, "stop": s.try_stop_async}
            if cmd in simple:
                return bool(await asyncio.wait_for(simple[cmd](), CALL_TIMEOUT))
            if cmd in ("seek_rel", "seek_abs") and value is not None:
                target = value
                if cmd == "seek_rel":
                    pos = await self._position(s)
                    if pos is None:
                        return False
                    target = pos + value
                start = _secs(s.get_timeline_properties().start_time) or 0.0
                ticks = int(max(0.0, target + start) * _TICKS)
                return bool(await asyncio.wait_for(s.try_change_playback_position_async(ticks), CALL_TIMEOUT))
        except Exception:
            return False
        return False
