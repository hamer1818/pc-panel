"""Protokol v1: toplanan verileri karta gidecek kısa JSON mesajlarına çevirir (bkz. docs/02-mimari.md)."""

from __future__ import annotations

import time

PROTO_VERSION = 1  # v1.x: geriye uyumlu eklemeler (v1.1 vol/kısayol, v1.2 kapak, v1.3 karartma, v1.4 ayarlar)
MB = 1024 * 1024


def _r(v, nd=0):
    if v is None:
        return None
    return round(v, nd) if nd else round(v)


_DAYS = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"]
_MONTHS = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos", "Eylül", "Ekim",
           "Kasım", "Aralık"]


def _clock() -> tuple[str, str]:
    now = time.localtime()
    return (time.strftime("%H:%M", now),
            f"{now.tm_mday} {_MONTHS[now.tm_mon - 1]} {_DAYS[now.tm_wday]}")


def stat_message(sysd: dict, gpu: dict | None) -> dict:
    clock, date = _clock()
    msg = {
        "t": "stat",
        "clock": clock,
        "date": date,
        "cpu": _r(sysd["cpu"], 1),
        "cpu_max": max(sysd["cpu_cores"]) if sysd["cpu_cores"] else None,
        "cpu_t": _r(sysd["cpu_temp"]),
        "cpu_mhz": sysd["cpu_mhz"],
        "swap": _r(sysd["swap_pct"]),
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
            "gpu_fan": gpu["fan_pct"],
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


def vol_message(a: dict) -> dict:
    return {
        "t": "vol",
        "v": a["volume"],
        "mute": int(bool(a["mute"])),
        "mic": a["mic"],
        "mic_mute": int(bool(a["mic_mute"])),
    }


# --- v1.4 (Faz 7): ayar dosyasından gelenler -----------------------------------------------------

def tiles_message(shortcuts) -> dict:
    """Kısayol kutuları. Kart en çok 12 kutu gösterir; `tg`: "mic"/"mute" durum gösteren kutular."""
    items = []
    for sc in shortcuts:
        it = {"id": sc.id, "ic": sc.icon, "ti": sc.title, "de": sc.desc}
        if sc.toggle:
            it["tg"] = sc.toggle
        items.append(it)
    return {"t": "tiles", "items": items}


def cfg_message(s) -> dict:
    return {"t": "cfg", "lock_clock": int(s.lock_clock), "lock_min": s.lock_min, "notif_s": s.notif_secs}


def notif_message(app: str, title: str, body: str, lvl: str = "info") -> dict:
    """lvl: info (zil) · ok (yeşil ✓) · err (kırmızı ✗) · wait (sarı ⚠) — kartta ikon ve renk."""
    return {"t": "notif", "app": app[:40], "ti": title[:100], "bd": body[:200], "lvl": lvl}


# --- v1.5 (Faz 7B): Geliştirici sayfası ------------------------------------------------------------

def cc_message(items: list[dict]) -> dict:
    """Claude Code oturumları: p proje, s durum (work/wait/done/idle), m açıklama, age sn."""
    return {"t": "cc", "items": items[:5], "wait": sum(1 for x in items if x["s"] == "wait"),
            "work": sum(1 for x in items if x["s"] == "work")}


def gh_message(data: dict | None, error: str = "") -> dict:
    if not data:
        return {"t": "gh", "ok": 0, "err": error[:40]}
    return {"t": "gh", "ok": 1, "runs": data["runs"][:4], "rev": data["review"], "prs": data["my_prs"],
            "ntf": data["notifications"]}


def srv_message(items: list[dict]) -> dict:
    """Sunucular: n ad, ok (1 ayakta / 0 kapalı / -1 henüz bilinmiyor), ms gecikme, ssl kalan gün."""
    return {"t": "srv", "items": items[:8]}
