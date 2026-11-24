"""PC Panel servisi — giriş noktası.

Kullanım (host/ klasöründe):
    uv run pc-panel                   # servis: verileri karta gönder, karttan gelen komutları uygula
    uv run pc-panel --debug           # servis + kartın günlük satırları ve gönderilen mesajlar
    uv run pc-panel --konsol          # karta göndermeden canlı terminal görünümü
    uv run pc-panel --json            # her saniye bir JSON satırı
    uv run pc-panel --once            # tek ölçüm, JSON, çık
    uv run pc-panel --komut play_pause   # etkin çalara komut gönder (play_pause, next, prev, seek_rel:10 ...)
    uv run pc-panel --ayar-kontrol    # ayar dosyasını denetle ve özetle
    uv run pc-panel --uygulamalar     # Uygulamalar sayfasına yazılabilecek kimlikler (Windows: Başlat menüsü)
    pythonw -m pc_panel --gunluk DOSYA   # Windows'ta penceresiz çalışma (deploy/kur.ps1 böyle kurar)

Linux (KDE Plasma) ve Windows 10/11'de çalışır; işletim sistemine özgü kısımlar backend.py'de seçilir.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import signal
import sys
import threading
import time

from . import art, shortcuts  # noqa: F401
from .alerts import AlertTracker
from .backend import WINDOWS, apps as appmod, audio, media as mediamod, notify as notifymod
from .config import CONFIG_PATH, ConfigWatcher
from .console import render
from .gpu import GpuCollector
from .link import DEFAULT_BAUD, SerialLink
from .claude import ClaudeTracker, fmt_dur
from .github import GhError, GitHubWatcher
from .gitwatch import scan as git_scan, summary_text as git_summary
from .olay import EVENT_HOST, EVENT_PORT, SOCK_PATH
from .protocol import (apps_message, cc_message, cfg_message, cu_message, gh_message, git_message, hw_message,
                       media_message, notif_message, srv_message, stat_message, tiles_message, vol_message)
from .servers import ServerWatcher
from .system import SystemCollector, cpu_name
from .usage import UsageTracker

MediaWatcher = mediamod.MediaWatcher
NotificationWatcher = notifymod.NotificationWatcher
LOG_MAX_BYTES = 2 * 1024 * 1024  # --gunluk dosyası bunu aşınca bir önceki ".1" olarak saklanır
BIN_SETTLE_S = 0.5  # sayfa kuran mesajdan (tiles / apps) sonra ikili blok göndermeden önce bekle
HB_TIMEOUT_S = 5.0
ART_MAX_RETRY = 3
MEDIA_COMMANDS = {"play_pause", "play", "pause", "next", "prev", "seek_rel", "seek_abs"}
NOTIF_DEDUP_S = 3.0
CC_REFRESH_S = 10  # Claude oturum sürelerini bu aralıkla tazele
USAGE_EVERY_S = 60
GIT_EVERY_S = 300


def is_kdeconnect_notif(n: dict) -> bool:
    return "kdeconnect" in n["entry"].casefold() or n["app"].casefold() in ("kde connect", "kde bağlan")


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


async def collect_once(s: SystemCollector, g: GpuCollector, m: MediaWatcher) -> dict:
    return {"system": s.sample(), "gpu": g.sample(), "media": await m.poll()}


# --- Servis modu -------------------------------------------------------------------------------

async def serve(args: argparse.Namespace, media: MediaWatcher) -> int:
    system, gpu = SystemCollector(), GpuCollector()
    link = SerialLink(args.port, args.baud, log=log)
    config = ConfigWatcher(log=log)
    alerts = AlertTracker()
    log(f"servis başladı (GPU: {gpu.name or 'yok'}, {args.baud} baud)")

    def send(msg: dict) -> None:
        link.send(msg)
        if args.debug:
            log(f"→ {json.dumps(msg, ensure_ascii=False)}")

    # --- Ayarlardan ve geliştirici kaynaklarından gelenler: bağlantı ya da ayar değişince yeniden gönder ---
    ui_state = {"sent": None, "locked": False}
    dev = {"gh": gh_message(None, "yükleniyor"), "srv": None, "cu": None, "git": None, "wake": asyncio.Event()}
    claude = ClaudeTracker()
    # Uygulamalar: ayar değişince arka planda çözülür (ad + ikon); hazır olunca karta gönderilir
    apps_state = {"version": -1, "apps": [], "icons": [], "sent": None, "task": None, "icon_task": None}
    rx_lost = {"last": 0}  # kartın bildirdiği toplam taşma sayısı
    icon_acks: dict[int, asyncio.Future] = {}  # ikon sırası → kartın {"t":"icon","ok":…} yanıtı
    # İkili bloklar (kapak, ikonlar) hiçbir zaman üst üste gönderilmez: biri gider, kartın onayı beklenir, sonra
    # diğeri. Kart sayfa kurarken (tiles / apps) de bir an beklenir. Aksi hâlde kartın UART tamponu taşabiliyor.
    bin_lock = asyncio.Lock()
    heavy = {"at": 0.0}  # en son sayfa kuran mesajın (tiles / apps) gönderildiği an
    art_ack: dict[str, asyncio.Future | None] = {"fut": None}

    async def settle() -> None:
        wait = heavy["at"] + BIN_SETTLE_S - time.monotonic()
        if wait > 0:
            await asyncio.sleep(wait)

    async def send_icons(key: tuple) -> None:
        """İkonları tek tek gönderir ve her birinin onayını bekler (dur-bekle). Kart sayfayı kurarken seri tampon
        taşabiliyordu; bir ikon bozulunca arkasındakiler de kayboluyordu. Ulaşmayan ikon 2 kez daha denenir."""
        await asyncio.sleep(0.3)  # kart `apps` ile sayfayı kurarken beklesin
        loop = asyncio.get_running_loop()
        for i, data in enumerate(apps_state["icons"]):
            if not data:
                continue
            for attempt in range(3):
                if apps_state["sent"] != key or not link.connected:
                    return  # liste değişti ya da bağlantı koptu: yeni gönderim başlayacak
                async with bin_lock:
                    await settle()
                    fut = loop.create_future()
                    icon_acks[i] = fut
                    link.send(appmod.icon_header(i, data), data)
                    try:
                        ok = await asyncio.wait_for(fut, 5.0)
                    except asyncio.TimeoutError:
                        ok = False
                    finally:
                        icon_acks.pop(i, None)
                if ok:
                    break
                log(f"ikon {i} ulaşmadı" + (", yeniden gönderiliyor" if attempt < 2 else ", bırakıldı"))
                await asyncio.sleep(0.5)

    async def load_apps(version: int, wanted: list[tuple[str, str]]) -> None:
        def work():
            found, icons = [], []
            for app_id, title in wanted:
                a = appmod.resolve(app_id, title)
                if a is None:
                    log(f"uygulama bulunamadı: {app_id} "
                        f"({'Başlat menüsünde yok' if WINDOWS else '.desktop dosyası yok'}; bkz. --uygulamalar)")
                    continue
                found.append(a)
                icons.append(appmod.icon_bytes(a))
            return found, icons
        found, icons = await asyncio.to_thread(work)
        if config.version == version:
            apps_state.update(version=version, apps=found, icons=icons, sent=None)
            log(f"uygulamalar hazır: {len(found)} ({sum(1 for i in icons if i)} ikon)")

    def maybe_send_apps() -> None:
        if apps_state["version"] != config.version:
            task = apps_state["task"]
            if task is None or task.done():
                apps_state["task"] = asyncio.create_task(load_apps(config.version, list(config.settings.apps)))
            return
        key = (apps_state["version"], link.generation)
        if key == apps_state["sent"] or not link.connected:
            return
        send(apps_message(apps_state["apps"]))
        heavy["at"] = time.monotonic()
        apps_state["sent"] = key
        old = apps_state["icon_task"]
        if old and not old.done():
            old.cancel()
        apps_state["icon_task"] = asyncio.create_task(send_icons(key))
    servers = ServerWatcher()

    def maybe_send_settings() -> None:
        key = (config.version, link.generation)
        if key == ui_state["sent"] or not link.connected:
            return
        s = config.settings
        if s.shortcuts:  # liste boşsa kart kendi yerleşik kutularını gösterir
            send(tiles_message(s.shortcuts))
            heavy["at"] = time.monotonic()
        send(cfg_message(s))
        send(hw_message(cpu_name(), gpu.name or ""))
        system.mounts = s.disks
        send(cc_message(claude.items()))
        send(dev["gh"])
        for k in ("srv", "cu", "git"):
            if dev[k]:
                send(dev[k])
        ui_state["sent"] = key

    def push_notif(title: str, body: str, app: str = "PC Panel", lvl: str = "info") -> None:
        """Servisin kendi bildirimleri (Claude, komut, CI, sunucu). Kilitliyken ayara uyar."""
        if not link.connected or (ui_state["locked"] and not config.settings.notif_locked):
            return
        send(notif_message(app, title, body, lvl))

    # --- Bildirimler (masaüstü) ---
    notif_last = {"key": None, "at": 0.0}

    def on_notify(n: dict) -> None:
        s = config.settings
        if not s.notif_on or not link.connected or (ui_state["locked"] and not s.notif_locked):
            return
        if n["app"].casefold() in s.notif_exclude or (n["entry"] and n["entry"].casefold() in s.notif_exclude):
            return
        # KDE Connect telefon bildirimlerini "KDE Connect"/"KDE Bağlan" adıyla aktarır; başlık telefondaki uygulamanın
        # adıdır (ör. "Spotify"). haric listesi onlara da uygulansın: yoksa telefonun "şimdi çalıyor" bildirimi her
        # şarkıda Medya sayfasının üstünü kaplıyordu (2026-11-24).
        if is_kdeconnect_notif(n) and n["title"].casefold() in s.notif_exclude:
            return
        if not (n["title"] or n["body"]):
            return
        key, now = (n["app"], n["title"], n["body"]), time.monotonic()
        if key == notif_last["key"] and now - notif_last["at"] < NOTIF_DEDUP_S:
            return  # aynı bildirim art arda (ilerleme güncellemeleri vb.)
        notif_last.update(key=key, at=now)
        send(notif_message(n["app"] or "Bildirim", n["title"], n["body"]))
        log(f"bildirim karta gönderildi: {n['app']}")

    notifier = NotificationWatcher(on_notify, log=log)

    # --- Olay soketi: Claude Code hook'ları, fish, `pc-panel-olay bildir` ---
    def on_event(ev: dict) -> None:
        s = config.settings
        kind = ev.get("k")
        if kind == "claude":
            if not s.claude_on:
                return
            v = claude.version
            for title, body, lvl in claude.handle(ev, s.claude_min_s):
                push_notif(title, body, "Claude Code", lvl)
                log(f"claude: {title}")
            if claude.version != v and link.connected:
                send(cc_message(claude.items()))
        elif kind == "cmd":
            cmd = str(ev.get("cmd", "")).strip()
            words = cmd.split()

            def prog(w: str) -> str:  # "/usr/bin/nvim" → "nvim", "C:\…\python.exe" → "python"
                name = re.split(r"[\\/]", w)[-1]
                return name[:-4] if WINDOWS and name.lower().endswith(".exe") else name

            first = prog(words[0]) if words else ""
            if first in ("sudo", "doas", "env", "time", "nice", "command", "exec", "gsudo") and len(words) > 1:
                first = prog(words[1])
            ms, code = int(ev.get("ms", 0)), int(ev.get("code", 0))
            if not s.cmd_on or ms < s.cmd_min_s * 1000 or not cmd or first in s.cmd_exclude:
                return
            ok = code == 0
            push_notif(cmd[:100], f"{'tamamlandı' if ok else f'hata, çıkış kodu {code}'} · {fmt_dur(ms / 1000)}",
                       "Terminal", "ok" if ok else "err")
            log(f"komut bitti: {first} (çıkış {code}, {ms // 1000} sn)")
        elif kind == "notif":
            push_notif(str(ev.get("title", "")), str(ev.get("body", "")), "pc-panel-olay", "info")

    async def event_server() -> None:
        async def client(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
            try:
                line = await asyncio.wait_for(reader.readline(), 2.0)
                ev = json.loads(line or b"{}")
                if isinstance(ev, dict):
                    on_event(ev)
            except (asyncio.TimeoutError, ValueError, OSError) as e:
                if args.debug:
                    log(f"olay okunamadı: {e}")
            finally:
                writer.close()

        if WINDOWS:  # Python Windows'ta Unix soketi açamaz: yalnızca bu bilgisayardan erişilen TCP
            try:
                server = await asyncio.start_server(client, EVENT_HOST, EVENT_PORT)
            except OSError as e:
                log(f"olay portu {EVENT_PORT} açılamadı ({e}); Claude / komut olayları gelmeyecek")
                return
        else:
            try:
                os.unlink(SOCK_PATH)  # önceki çalışmadan kalan soket dosyası
            except FileNotFoundError:
                pass
            server = await asyncio.start_unix_server(client, path=SOCK_PATH)
            os.chmod(SOCK_PATH, 0o600)
        async with server:
            await server.serve_forever()

    # --- GitHub ve sunucular: arka planda belirli aralıklarla ---
    async def github_loop() -> None:
        gh = GitHubWatcher()
        while True:
            s = config.settings
            delay = s.gh_every_s
            if s.gh_on:
                try:
                    data, notes = await asyncio.to_thread(gh.poll, s.gh_repos)
                    dev["gh"] = gh_message(data)
                    for title, body, lvl in notes:
                        push_notif(title, body, "GitHub", lvl)
                        log(f"github: {title}")
                except (GhError, ValueError, KeyError, TypeError) as e:
                    log(f"github okunamadı: {e}")
                    dev["gh"] = gh_message(None, str(e))
                    delay = max(delay, 300)
            else:
                dev["gh"] = gh_message(None, "kapalı")
            if link.connected:
                send(dev["gh"])
            dev["wake"].clear()
            try:
                await asyncio.wait_for(dev["wake"].wait(), delay)  # ayar değişince beklemeden yenile
            except asyncio.TimeoutError:
                pass

    async def usage_loop() -> None:
        tracker = await asyncio.to_thread(UsageTracker)
        while True:
            if config.settings.claude_usage:
                try:
                    dev["cu"] = cu_message(await asyncio.to_thread(tracker.poll))
                except Exception as e:  # kayıt biçimi değişse bile servis düşmesin
                    log(f"claude kullanımı okunamadı: {e}")
            else:
                dev["cu"] = cu_message([])
            if link.connected and dev["cu"]:
                send(dev["cu"])
            await asyncio.sleep(USAGE_EVERY_S)

    async def git_loop() -> None:
        while True:
            s = config.settings
            if s.git_on:
                res = await asyncio.to_thread(git_scan, s.git_roots, s.git_days)
                dev["git"] = git_message(*git_summary(res))
            else:
                dev["git"] = git_message("", 0)
            if link.connected:
                send(dev["git"])
            await asyncio.sleep(GIT_EVERY_S)

    async def servers_loop() -> None:
        while True:
            s = config.settings
            if s.servers:
                results = await asyncio.gather(*(asyncio.to_thread(servers.check_one, x) for x in s.servers))
                for title, body, lvl in servers.update(list(results), s.servers):
                    push_notif(title, body, "Sunucular", lvl)
                    log(f"sunucu: {title} ({body})")
                dev["srv"] = srv_message(servers.items)
            else:
                servers.update([], [])
                dev["srv"] = srv_message([])
            if link.connected:
                send(dev["srv"])
            await asyncio.sleep(s.srv_every_s)

    # --- Kapak resmi: değişince bir kez gönder (bkz. docs/02-mimari.md "Kapak resmi") ---
    art_state = {"sent": None, "pending": None, "task": None, "fails": 0, "url": None}

    async def push_art(key: tuple, url: str) -> None:
        pixels = await media.fetch_art(url) if url else None
        async with bin_lock:
            if art_state["pending"] != key:  # bu arada şarkı değişti
                return
            await settle()
            fut = art_ack["fut"] = asyncio.get_running_loop().create_future() if pixels else None
            link.send(art.header(pixels), pixels or b"")
            art_state["sent"], art_state["pending"] = key, None
            if url:
                what = f"{len(pixels) // 1024} KB" if pixels else "okunamadı, yer tutucu"
                log(f"kapak gönderildi ({what})" if args.debug or not pixels else "kapak gönderildi")
            if fut is not None:  # kart onaylayana kadar başka ikili blok gönderme
                try:
                    await asyncio.wait_for(fut, 5.0)
                except asyncio.TimeoutError:
                    pass
                finally:
                    art_ack["fut"] = None

    def maybe_send_art(url: str) -> None:
        key = (url, link.generation)
        if key in (art_state["sent"], art_state["pending"]):
            return
        if url != art_state["url"]:  # yeni kapak: deneme sayacı sıfırdan
            art_state["url"], art_state["fails"] = url, 0
        task = art_state["task"]
        if task and not task.done():
            task.cancel()
        art_state["pending"] = key
        art_state["task"] = asyncio.create_task(push_art(key, url))

    async def send_media() -> None:
        media.ignore = config.settings.media_ignore  # ayar canlı değişebilir
        state = await media.poll()
        send(media_message(state))
        active = state.get("active")
        maybe_send_art(active["art_url"] if active and active["status"] != "Stopped" else "")

    async def send_vol() -> None:
        send(vol_message(await audio.state()))

    async def producer() -> None:
        await asyncio.sleep(1)  # hız hesapları için ilk aralık
        tick = 0
        while True:
            t0 = time.monotonic()
            tick += 1
            if tick % 3 == 0 and config.check():
                dev["wake"].set()  # GitHub depoları değişmiş olabilir
            if tick % CC_REFRESH_S == 0:
                claude.prune()
                if link.connected:
                    send(cc_message(claude.items()))
            if link.connected:
                maybe_send_settings()
                maybe_send_apps()
                sysd, gpud = system.sample(), gpu.sample()
                msg = stat_message(sysd, gpud)
                locked = bool(await media.screen_locked())
                ui_state["locked"] = locked
                msg["locked"] = int(locked)  # kart ekranı karartsın / kilit saatini göstersin
                warn, disk_events = alerts.update(sysd, gpud, config.settings)
                msg["warn"] = " · ".join(x for x in (warn, servers.warn) if x)
                send(msg)
                for ev in disk_events:
                    send(notif_message("PC Panel", "Disk dolmak üzere", ev, "wait"))
                    log(f"uyarı: disk {ev}")
                await send_media()
                await send_vol()
            else:
                system.sample()  # hız sayaçları güncel kalsın
            await asyncio.sleep(max(0.05, args.aralik - (time.monotonic() - t0)))

    async def consumer() -> None:
        while True:
            line = await link.lines.get()
            if not line.startswith("{"):
                if args.debug:
                    log(f"kart günlüğü: {line}")
                continue
            try:
                msg = json.loads(line)
            except json.JSONDecodeError:
                if args.debug:
                    log(f"bozuk satır: {line!r}")
                continue
            link.mark_rx()
            kind = msg.get("t")
            if kind == "hello":
                log(f"kart: merhaba (yazılım {msg.get('fw')}, protokol {msg.get('proto')})")
                art_state["sent"] = None  # kart yeniden başladı: kapağı ve ayarları yeniden gönder
                ui_state["sent"] = None
                apps_state["sent"] = None
            elif kind == "icon":
                fut = icon_acks.get(msg.get("i"))
                if fut and not fut.done():
                    fut.set_result(bool(msg.get("ok")))
                if args.debug:
                    log(f"kart: ikon {msg.get('i')} {'alındı' if msg.get('ok') else 'alınamadı'}")
            elif kind == "art":
                fut = art_ack["fut"]
                if fut and not fut.done():
                    fut.set_result(bool(msg.get("ok")))
                if msg.get("ok"):
                    if args.debug:
                        log("kart: kapak alındı")
                else:
                    art_state["fails"] += 1
                    log(f"kart: kapak alınamadı (deneme {art_state['fails']}/{ART_MAX_RETRY})")
                    if art_state["fails"] < ART_MAX_RETRY:
                        art_state["sent"] = None
            elif kind == "hb":
                if args.debug:
                    log(f"kart: kalp atışı, açık {msg.get('up')} sn")
                # Kartın seri alım taşma sayaçları (0.11.1+): artarsa bayt kaçmış demektir
                lost = (msg.get("ovf") or 0) + (msg.get("full") or 0)
                if lost < rx_lost["last"]:
                    rx_lost["last"] = 0  # kart yeniden başlamış
                if lost > rx_lost["last"]:
                    log(f"kart: seri alımda bayt kaybı (FIFO taşması {msg.get('ovf')}, tampon dolu {msg.get('full')})")
                    rx_lost["last"] = lost
            elif kind == "cmd":
                cmd, val = msg.get("c"), msg.get("v")
                if cmd in MEDIA_COMMANDS:
                    ok = await media.command(cmd, float(val) if isinstance(val, (int, float)) else None)
                    log(f"karttan komut: {cmd}{'' if val is None else ' ' + str(val)} → {'tamam' if ok else 'başarısız'}")
                    await asyncio.sleep(0.15)  # çalar durumunu güncellesin
                    await send_media()     # ekran beklemeden güncellensin
                elif cmd == "vol_set" and isinstance(val, (int, float)):
                    ok = await audio.set_volume(float(val))
                    log(f"karttan komut: ses %{val:.0f} → {'tamam' if ok else 'başarısız'}")
                    await send_vol()
                elif cmd == "app" and (app := next((a for a in apps_state["apps"] if a.id == msg.get("id")), None)):
                    ok = await asyncio.to_thread(appmod.launch, app)
                    log(f"karttan uygulama: {app.title} → {'tamam' if ok else 'başarısız'}")
                elif cmd == "mute":  # Medya sayfasındaki ses simgesi
                    ok = await audio.toggle_mute()
                    log(f"karttan komut: sessiz → {'tamam' if ok else 'başarısız'}")
                    await send_vol()
                elif cmd == "shortcut" and (sc := next((x for x in config.settings.shortcuts
                                                        if x.id == msg.get("id")), None)):
                    ok = await shortcuts.run(sc, media)
                    log(f"karttan kısayol: {sc.id} ({sc.title}) → {'tamam' if ok else 'başarısız'}")
                    await send_vol()       # mikrofon / sessiz durumu hemen yansısın
                else:
                    log(f"bilinmeyen ya da izin verilmeyen komut: {msg}")

    async def watchdog() -> None:
        warned = False
        while True:
            await asyncio.sleep(1)
            silent = link.connected and link.last_rx and time.monotonic() - link.last_rx > HB_TIMEOUT_S
            if silent and not warned:
                log(f"kart {HB_TIMEOUT_S:.0f} sn'dir sessiz (yazılım çalışıyor mu?)")
                warned = True
            elif not silent:
                warned = False

    # SIGTERM (systemd durdururken) ve Ctrl+C: karta "bye" gönder ki ekranı hemen karartsın.
    # Windows: Ctrl+C / Ctrl+Break (konsolda) ve oturum kapanışı (WM_ENDSESSION, win/session.py).
    stop = asyncio.Event()
    bye_sent = threading.Event()
    loop = asyncio.get_running_loop()
    if WINDOWS:
        from .win import session as winsession

        def on_signal(*_):
            loop.call_soon_threadsafe(stop.set)
        for sig in (signal.SIGINT, signal.SIGBREAK):
            signal.signal(sig, on_signal)

        def on_end_session() -> None:  # Windows kapanırken: pencere iş parçacığında, "bye" gidene kadar bekle
            loop.call_soon_threadsafe(stop.set)
            bye_sent.wait(2.0)
        winsession.watch_shutdown(on_end_session)
    else:
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(sig, stop.set)

    tasks = [asyncio.create_task(c) for c in (link.maintain(), producer(), consumer(), watchdog(),
                                              notifier.run(), event_server(), github_loop(), servers_loop(),
                                              usage_loop(), git_loop())]
    if WINDOWS:  # Windows'ta sinyal işleyicisi ancak olay döngüsü uyanınca çalışır; döngü en geç 0,5 sn'de uyansın
        async def wake() -> None:
            while True:
                await asyncio.sleep(0.5)
        tasks.append(asyncio.create_task(wake()))
    try:
        await stop.wait()
        log("kapanıyor")
        if link.connected:
            link.send({"t": "bye"})
            await link.flush()
    finally:
        bye_sent.set()
        for t in tasks:
            t.cancel()
        gpu.close()
        if not WINDOWS:
            try:
                os.unlink(SOCK_PATH)
            except OSError:
                pass
    return 0


# --- Yardımcı modlar ---------------------------------------------------------------------------

async def local_modes(args: argparse.Namespace, media: MediaWatcher) -> int:
    system, gpu = SystemCollector(), GpuCollector()
    await asyncio.sleep(1)
    try:
        if args.once:
            print(json.dumps(await collect_once(system, gpu, media), ensure_ascii=False, indent=1))
            return 0
        if args.konsol:
            sys.stdout.write("\033[?25l")
        while True:
            data = await collect_once(system, gpu, media)
            if args.konsol:
                sys.stdout.write("\033[H\033[J" + render(data["system"], data["gpu"], data["media"]) + "\n")
                sys.stdout.flush()
            else:
                print(json.dumps(data, ensure_ascii=False), flush=True)
            await asyncio.sleep(args.aralik)
    finally:
        if args.konsol:
            sys.stdout.write("\033[?25h")
        gpu.close()


def check_config() -> int:
    cw = ConfigWatcher(log=lambda m: print(m))
    s = cw.settings
    print(f"\nDosya: {CONFIG_PATH}{'' if CONFIG_PATH.exists() else ' (yok — örnek dosya kullanılıyor)'}")
    print(f"Kilit saati: {'açık, ' + (str(s.lock_min) + ' dk' if s.lock_min else 'sürekli') if s.lock_clock else 'kapalı'}")
    print(f"Claude Code: {'açık' if s.claude_on else 'kapalı'} (bitince bildirim: {s.claude_min_s} sn+)")
    print(f"Claude kullanımı: {'açık' if s.claude_usage else 'kapalı'}")
    print(f"Git: {'kapalı' if not s.git_on else ', '.join(s.git_roots) + f' (son {s.git_days} gün)'}")
    print(f"Uzun komut: {'açık' if s.cmd_on else 'kapalı'} ({s.cmd_min_s} sn+), hariç: {len(s.cmd_exclude)} program")
    print(f"GitHub: {'kapalı' if not s.gh_on else ', '.join(s.gh_repos) or 'son 6 depo (otomatik)'}, {s.gh_every_s} sn")
    print(f"Sunucular ({len(s.servers)}, {s.srv_every_s} sn): "
          + (", ".join(f"{x.name}={x.url or ':'.join(map(str, x.tcp))}" for x in s.servers) or "-"))
    print(f"Bildirimler: {'açık' if s.notif_on else 'kapalı'}, hariç: {', '.join(sorted(s.notif_exclude)) or '-'}")
    print(f"Uyarı eşikleri: CPU {s.warn_cpu}°C, GPU {s.warn_gpu}°C, RAM %{s.warn_ram}, disk %{s.warn_disk}")
    print(f"Uygulamalar ({len(s.apps)}):")
    for app_id, title in s.apps:
        a = appmod.resolve(app_id, title)
        icon = appmod.find_icon(a.icon_name) if a else None
        print(f"  [{app_id}] {a.title if a else 'BULUNAMADI'} · ikon: {icon or 'yok'}")
    if any(appmod.resolve(i, t) is None for i, t in s.apps):
        print("  (kullanılabilecek kimlikler: uv run pc-panel --uygulamalar)")
    print(f"Kısayollar ({len(s.shortcuts)}):")
    for sc in s.shortcuts:
        steps = " → ".join(f"{st.kind}={st.value}" for st in sc.steps)
        print(f"  [{sc.id}] {sc.title} ({sc.icon}): {steps}")
    return 0


def list_apps() -> int:
    """Uygulamalar sayfasına / `uygulama =` kısayoluna yazılabilecek kimlikler."""
    if WINDOWS:
        rows = sorted(appmod.start_apps(), key=lambda x: x[0].casefold())
        print(f"Başlat menüsü uygulamaları ({len(rows)}). Ayarda ad (\"steam\", \"Visual Studio Code\") ya da AppID "
              "yazılabilir:\n")
        for name, aumid in rows:
            print(f"  {name:<40} {aumid}")
        return 0
    seen: dict[str, str] = {}
    for base in appmod.DATA_DIRS:
        d = base / "applications"
        if d.is_dir():
            for p in sorted(d.glob("*.desktop")):
                if p.stem not in seen:
                    info = appmod.read_desktop(p)
                    if info and info.get("NoDisplay", "").lower() != "true":
                        seen[p.stem] = info.get("Name[tr]") or info.get("Name") or ""
    print(f"Masaüstü uygulamaları ({len(seen)}). Ayara kimlik (soldaki) yazılır:\n")
    for app_id, name in sorted(seen.items(), key=lambda x: x[1].casefold()):
        print(f"  {app_id:<45} {name}")
    return 0


async def run(args: argparse.Namespace) -> int:
    if args.ayar_kontrol:
        return check_config()
    if args.uygulamalar:
        return list_apps()
    media = MediaWatcher()
    await media.connect()
    if args.komut:
        cmd, _, val = args.komut.partition(":")
        await media.poll()
        ok = await media.command(cmd, float(val) if val else None)
        print(f"{cmd}: {'tamam' if ok else 'başarısız'} ({media.active or 'çalar yok'})")
        return 0 if ok else 1
    if args.konsol or args.json or args.once:
        return await local_modes(args, media)
    return await serve(args, media)


def setup_output(log_file: str | None, console: bool = False) -> None:
    """Çıktı her sistemde UTF-8 olsun (Windows'ta yönlendirilen çıktı cp1254 olur, Türkçe harf / █ düşürür);
    --gunluk verilirse çıktı dosyaya gider (pythonw'da stdout yoktur)."""
    if log_file:
        try:
            if os.path.getsize(log_file) > LOG_MAX_BYTES:
                os.replace(log_file, log_file + ".1")
        except OSError:
            pass
        os.makedirs(os.path.dirname(os.path.abspath(log_file)), exist_ok=True)
        f = open(log_file, "a", encoding="utf-8", buffering=1)  # satır tamponlu
        sys.stdout = sys.stderr = f
        return
    for stream in (sys.stdout, sys.stderr):
        if stream is not None and hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8", errors="replace")
            except (OSError, ValueError):
                pass
    if WINDOWS and console:  # eski konsolda (conhost) ANSI renk / imleç kodları çalışsın
        import ctypes
        k32 = ctypes.windll.kernel32
        h = k32.GetStdHandle(-11)
        mode = ctypes.c_uint32()
        if k32.GetConsoleMode(h, ctypes.byref(mode)):
            k32.SetConsoleMode(h, mode.value | 0x0004)  # ENABLE_VIRTUAL_TERMINAL_PROCESSING


def main() -> None:
    p = argparse.ArgumentParser(prog="pc-panel", description="PC Panel bilgisayar servisi")
    mode = p.add_mutually_exclusive_group()
    mode.add_argument("--konsol", action="store_true", help="karta göndermeden canlı terminal görünümü")
    mode.add_argument("--json", action="store_true", help="her ölçümü bir JSON satırı olarak yaz")
    mode.add_argument("--once", action="store_true", help="tek ölçüm yap ve çık")
    mode.add_argument("--komut", metavar="KOMUT[:DEĞER]", help="etkin çalara medya komutu gönder")
    mode.add_argument("--ayar-kontrol", action="store_true", help="ayar dosyasını denetle ve özetle")
    mode.add_argument("--uygulamalar", action="store_true", help="Uygulamalar sayfasına yazılabilecek kimlikler")
    p.add_argument("--port", help="seri port, ör. /dev/ttyACM0 ya da COM4 (varsayılan: kart USB kimliğiyle bulunur)")
    p.add_argument("--baud", type=int, default=DEFAULT_BAUD, help=f"baud hızı (varsayılan {DEFAULT_BAUD})")
    p.add_argument("--debug", action="store_true", help="gönderilen mesajları ve kart günlüğünü yazdır")
    p.add_argument("--aralik", type=float, default=1.0, help="ölçüm aralığı, saniye (varsayılan 1)")
    p.add_argument("--gunluk", metavar="DOSYA", help="çıktıyı bu dosyaya yaz (Windows'ta pythonw ile penceresiz "
                                                      "çalışırken; 2 MB'ı aşınca .1 olarak saklanır)")
    args = p.parse_args()
    setup_output(args.gunluk, console=args.konsol)
    try:
        sys.exit(asyncio.run(run(args)))
    except KeyboardInterrupt:
        sys.exit(0)


if __name__ == "__main__":
    main()
