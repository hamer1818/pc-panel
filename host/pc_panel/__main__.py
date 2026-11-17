"""PC Panel servisi — giriş noktası.

Kullanım (host/ klasöründe):
    uv run pc-panel --konsol          # canlı terminal görünümü (Faz 2 testi)
    uv run pc-panel --json            # her saniye bir JSON satırı
    uv run pc-panel --once            # tek ölçüm, JSON, çık
    uv run pc-panel --komut play_pause   # etkin çalara komut gönder (play_pause, next, prev, seek_rel:10 ...)

Karta seri port üzerinden gönderme Faz 3'te eklenecek.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys

from .console import render
from .gpu import GpuCollector
from .media import MediaWatcher
from .system import SystemCollector


async def collect_once(s: SystemCollector, g: GpuCollector, m: MediaWatcher) -> dict:
    return {"system": s.sample(), "gpu": g.sample(), "media": await m.poll()}


async def run(args: argparse.Namespace) -> int:
    media = MediaWatcher()
    await media.connect()

    if args.komut:
        cmd, _, val = args.komut.partition(":")
        await media.poll()  # etkin çaları belirle
        ok = await media.command(cmd, float(val) if val else None)
        print(f"{cmd}: {'tamam' if ok else 'başarısız'} ({media.active or 'çalar yok'})")
        return 0 if ok else 1

    system, gpu = SystemCollector(), GpuCollector()
    await asyncio.sleep(1)  # hız hesapları için ilk aralık
    try:
        if args.once:
            print(json.dumps(await collect_once(system, gpu, media), ensure_ascii=False, indent=1))
            return 0
        if args.konsol:
            sys.stdout.write("\033[?25l")  # imleci gizle
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


def main() -> None:
    p = argparse.ArgumentParser(prog="pc-panel", description="PC Panel bilgisayar servisi")
    mode = p.add_mutually_exclusive_group()
    mode.add_argument("--konsol", action="store_true", help="canlı terminal görünümü")
    mode.add_argument("--json", action="store_true", help="her ölçümü bir JSON satırı olarak yaz")
    mode.add_argument("--once", action="store_true", help="tek ölçüm yap ve çık")
    mode.add_argument("--komut", metavar="KOMUT[:DEĞER]", help="etkin çalara medya komutu gönder")
    p.add_argument("--aralik", type=float, default=1.0, help="ölçüm aralığı, saniye (varsayılan 1)")
    args = p.parse_args()
    if not (args.konsol or args.json or args.once or args.komut):
        args.konsol = True
    try:
        sys.exit(asyncio.run(run(args)))
    except KeyboardInterrupt:
        sys.exit(0)


if __name__ == "__main__":
    main()
