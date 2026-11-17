"""Sistem sesi ve mikrofon (PipeWire / WirePlumber `wpctl`)."""

from __future__ import annotations

import asyncio
import re

SINK = "@DEFAULT_AUDIO_SINK@"
SOURCE = "@DEFAULT_AUDIO_SOURCE@"
MAX_VOLUME = 1.0  # %100 üstüne çıkılmasın (wpctl -l)
_VOL_RE = re.compile(r"Volume:\s*([0-9.]+)(\s*\[MUTED\])?")


async def _run(*args: str) -> str | None:
    try:
        proc = await asyncio.create_subprocess_exec(
            "wpctl", *args, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL)
        out, _ = await asyncio.wait_for(proc.communicate(), 2.0)
    except (OSError, asyncio.TimeoutError):
        return None
    return out.decode(errors="replace") if proc.returncode == 0 else None


async def _get(node: str) -> tuple[int | None, bool | None]:
    out = await _run("get-volume", node)
    m = _VOL_RE.search(out or "")
    if not m:
        return None, None
    return round(float(m.group(1)) * 100), bool(m.group(2))


async def state() -> dict:
    (v, mute), (mic, mic_mute) = await asyncio.gather(_get(SINK), _get(SOURCE))
    return {"volume": v, "mute": mute, "mic": mic, "mic_mute": mic_mute}


async def set_volume(pct: float) -> bool:
    pct = max(0.0, min(100.0, pct))
    return await _run("set-volume", "-l", str(MAX_VOLUME), SINK, f"{pct / 100:.2f}") is not None


async def toggle_mute() -> bool:
    return await _run("set-mute", SINK, "toggle") is not None


async def toggle_mic() -> bool:
    return await _run("set-mute", SOURCE, "toggle") is not None
