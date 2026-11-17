"""PC Panel servisi — giriş noktası.

Kullanım (host/ klasöründe):
    uv run pc-panel                   # servis: verileri karta gönder, karttan gelen komutları uygula
    uv run pc-panel --debug           # servis + kartın günlük satırları ve gönderilen mesajlar
    uv run pc-panel --konsol          # karta göndermeden canlı terminal görünümü
    uv run pc-panel --json            # her saniye bir JSON satırı
    uv run pc-panel --once            # tek ölçüm, JSON, çık
    uv run pc-panel --komut play_pause   # etkin çalara komut gönder (play_pause, next, prev, seek_rel:10 ...)
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time

from .console import render
from .gpu import GpuCollector
from .link import DEFAULT_BAUD, SerialLink
from .media import MediaWatcher
from .protocol import media_message, stat_message
from .system import SystemCollector

HB_TIMEOUT_S = 5.0
CARD_COMMANDS = {"play_pause", "play", "pause", "next", "prev", "seek_rel", "seek_abs"}


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


async def collect_once(s: SystemCollector, g: GpuCollector, m: MediaWatcher) -> dict:
    return {"system": s.sample(), "gpu": g.sample(), "media": await m.poll()}


# --- Servis modu -------------------------------------------------------------------------------

async def serve(args: argparse.Namespace, media: MediaWatcher) -> int:
    system, gpu = SystemCollector(), GpuCollector()
    link = SerialLink(args.port, args.baud, log=log)
    log(f"servis başladı (GPU: {gpu.name or 'yok'}, {args.baud} baud)")

    async def send_media() -> None:
        msg = media_message(await media.poll())
        link.send(msg)
        if args.debug:
            log(f"→ {json.dumps(msg, ensure_ascii=False)}")

    async def producer() -> None:
        await asyncio.sleep(1)  # hız hesapları için ilk aralık
        while True:
            t0 = time.monotonic()
            if link.connected:
                msg = stat_message(system.sample(), gpu.sample())
                link.send(msg)
                if args.debug:
                    log(f"→ {json.dumps(msg, ensure_ascii=False)}")
                await send_media()
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
            elif kind == "hb":
                if args.debug:
                    log(f"kart: kalp atışı, açık {msg.get('up')} sn")
            elif kind == "cmd":
                cmd, val = msg.get("c"), msg.get("v")
                if cmd in CARD_COMMANDS:
                    ok = await media.command(cmd, float(val) if val is not None else None)
                    log(f"karttan komut: {cmd}{'' if val is None else ' ' + str(val)} → {'tamam' if ok else 'başarısız'}")
                    await asyncio.sleep(0.15)  # çalar durumunu güncellesin
                    await send_media()     # ekran beklemeden güncellensin
                else:
                    log(f"bilinmeyen komut: {msg}")

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

    try:
        await asyncio.gather(link.maintain(), producer(), consumer(), watchdog())
    finally:
        gpu.close()
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


async def run(args: argparse.Namespace) -> int:
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


def main() -> None:
    p = argparse.ArgumentParser(prog="pc-panel", description="PC Panel bilgisayar servisi")
    mode = p.add_mutually_exclusive_group()
    mode.add_argument("--konsol", action="store_true", help="karta göndermeden canlı terminal görünümü")
    mode.add_argument("--json", action="store_true", help="her ölçümü bir JSON satırı olarak yaz")
    mode.add_argument("--once", action="store_true", help="tek ölçüm yap ve çık")
    mode.add_argument("--komut", metavar="KOMUT[:DEĞER]", help="etkin çalara medya komutu gönder")
    p.add_argument("--port", help="seri port (varsayılan: kartın /dev/serial/by-id yolu)")
    p.add_argument("--baud", type=int, default=DEFAULT_BAUD, help=f"baud hızı (varsayılan {DEFAULT_BAUD})")
    p.add_argument("--debug", action="store_true", help="gönderilen mesajları ve kart günlüğünü yazdır")
    p.add_argument("--aralik", type=float, default=1.0, help="ölçüm aralığı, saniye (varsayılan 1)")
    args = p.parse_args()
    try:
        sys.exit(asyncio.run(run(args)))
    except KeyboardInterrupt:
        sys.exit(0)


if __name__ == "__main__":
    main()
