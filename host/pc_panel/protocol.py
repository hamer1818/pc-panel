"""Protokol v1: toplanan verileri karta gidecek kısa JSON mesajlarına çevirir (bkz. docs/02-mimari.md)."""

from __future__ import annotations

PROTO_VERSION = 1
MB = 1024 * 1024


def _r(v, nd=0):
    if v is None:
        return None
    return round(v, nd) if nd else round(v)


def stat_message(sysd: dict, gpu: dict | None) -> dict:
    msg = {
        "t": "stat",
        "cpu": _r(sysd["cpu"], 1),
        "cpu_t": _r(sysd["cpu_temp"]),
        "cpu_mhz": sysd["cpu_mhz"],
        "ram": _r(sysd["ram_used"] / MB),
        "ram_tot": _r(sysd["ram_total"] / MB),
        "disks": [{"m": d["mount"], "p": d["pct"]} for d in sysd["disks"]],
        "net_dn": _r(sysd["net_down_bps"]),
        "net_up": _r(sysd["net_up_bps"]),
        "dsk_r": _r(sysd["disk_read_bps"]),
        "dsk_w": _r(sysd["disk_write_bps"]),
        "up": sysd["uptime_s"],
    }
    if gpu:
        msg.update({
            "gpu": gpu["util"],
            "gpu_t": gpu["temp"],
            "gpu_w": _r(gpu["power_w"]),
            "gpu_wmax": gpu["power_limit_w"],
            "vram": _r(gpu["vram_used"] / MB) if gpu["vram_used"] is not None else None,
            "vram_tot": _r(gpu["vram_total"] / MB) if gpu["vram_total"] is not None else None,
        })
    return msg


_STATUS = {"Playing": "play", "Paused": "pause", "Stopped": "stop"}


def media_message(media: dict) -> dict:
    a = media.get("active")
    if not a:
        return {"t": "media", "st": "none"}
    return {
        "t": "media",
        "st": _STATUS.get(a["status"], "stop"),
        "ti": a["title"][:120],
        "ar": a["artist"][:120],
        "al": a["album"][:120],
        "pl": a["player"][:40],
        "len": a["length_s"] or 0,
        "pos": a["position_s"] or 0,
        "can": {"pp": int(a["can"]["play_pause"]), "nx": int(a["can"]["next"]),
                "pv": int(a["can"]["prev"]), "sk": int(a["can"]["seek"])},
    }
