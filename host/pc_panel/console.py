"""Konsol modu: toplanan verileri karta göndermeden terminalde canlı gösterir (test için)."""

from __future__ import annotations

import shutil

RESET, DIM, BOLD = "\033[0m", "\033[2m", "\033[1m"
GREEN, YELLOW, RED, CYAN = "\033[32m", "\033[33m", "\033[31m", "\033[36m"


def human_bytes(n: float | None, per_s: bool = False) -> str:
    if n is None:
        return "-"
    units = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    while n >= 1024 and i < len(units) - 1:
        n /= 1024
        i += 1
    s = f"{n:.0f} {units[i]}" if i == 0 else f"{n:.1f} {units[i]}"
    return s + ("/s" if per_s else "")


def hms(sec: int | None) -> str:
    if sec is None:
        return "--:--"
    h, rem = divmod(int(sec), 3600)
    m, s = divmod(rem, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


def bar(pct: float | None, width: int = 24) -> str:
    if pct is None:
        return DIM + "·" * width + RESET
    pct = max(0.0, min(100.0, pct))
    full = round(pct / 100 * width)
    color = GREEN if pct < 60 else YELLOW if pct < 85 else RED
    return color + "█" * full + RESET + DIM + "·" * (width - full) + RESET


def temp(t: float | None) -> str:
    if t is None:
        return "-"
    color = GREEN if t < 65 else YELLOW if t < 80 else RED
    return f"{color}{t:.0f}°C{RESET}"


def render(sysd: dict, gpu: dict | None, media: dict) -> str:
    cols = shutil.get_terminal_size((100, 40)).columns
    L: list[str] = []
    L.append(f"{BOLD}PC Panel — konsol modu{RESET}   {DIM}(çıkmak için Ctrl+C){RESET}")
    L.append("")

    L.append(f"{BOLD}{CYAN}CPU{RESET}  {bar(sysd['cpu'])} {sysd['cpu']:5.1f}%   {temp(sysd['cpu_temp'])}"
             f"   {sysd['cpu_mhz'] or '-'} MHz   yük {sysd['load1']}")
    cores = " ".join(f"{c:3d}" for c in sysd["cpu_cores"])
    L.append(f"     {DIM}çekirdekler:{RESET} {cores}")

    if gpu:
        L.append(f"{BOLD}{CYAN}GPU{RESET}  {bar(gpu['util'])} {gpu['util'] or 0:5.1f}%   {temp(gpu['temp'])}"
                 f"   {gpu['power_w']} / {gpu['power_limit_w']} W   {gpu['clock_mhz']} MHz   fan {gpu['fan_pct']}%")
        vram_pct = gpu["vram_used"] / gpu["vram_total"] * 100 if gpu["vram_total"] else None
        L.append(f"VRAM {bar(vram_pct)} {human_bytes(gpu['vram_used'])} / {human_bytes(gpu['vram_total'])}"
                 f"   {DIM}{gpu['name']}{RESET}")
    else:
        L.append(f"{BOLD}{CYAN}GPU{RESET}  {DIM}NVML yok{RESET}")

    L.append(f"{BOLD}{CYAN}RAM{RESET}  {bar(sysd['ram_pct'])} {human_bytes(sysd['ram_used'])} / "
             f"{human_bytes(sysd['ram_total'])}   swap %{sysd['swap_pct']}")
    for d in sysd["disks"]:
        L.append(f"{BOLD}{CYAN}Disk{RESET} {bar(d['pct'])} {d['pct']:5.1f}%   {human_bytes(d['used'])} / "
                 f"{human_bytes(d['total'])}   {DIM}{d['mount']}{RESET}")
    L.append(f"     okuma {human_bytes(sysd['disk_read_bps'], True):>11}   yazma {human_bytes(sysd['disk_write_bps'], True):>11}")
    L.append(f"{BOLD}{CYAN}Ağ{RESET}   indirme {human_bytes(sysd['net_down_bps'], True):>11}   "
             f"yükleme {human_bytes(sysd['net_up_bps'], True):>11}")
    L.append(f"{BOLD}{CYAN}Açık{RESET} {hms(sysd['uptime_s'])}")
    L.append("")

    a = media.get("active")
    if a:
        icon = {"Playing": "▶", "Paused": "⏸"}.get(a["status"], "■")
        L.append(f"{BOLD}{CYAN}Medya{RESET} {icon} {BOLD}{a['title'] or '(başlık yok)'}{RESET}")
        L.append(f"      {a['artist'] or '-'}   {DIM}{a['album']}{RESET}")
        pos, length = a["position_s"], a["length_s"]
        pct = pos / length * 100 if pos is not None and length else None
        L.append(f"      {bar(pct, 30)} {hms(pos)} / {hms(length)}")
        can = " ".join(k for k, v in a["can"].items() if v)
        L.append(f"      {DIM}çalar: {a['player']}   ses: {a['volume']}%   karışık: {a['shuffle']}   "
                 f"kontroller: {can}{RESET}")
        art = a["art_url"]
        L.append(f"      {DIM}kapak: {art[: max(cols - 14, 10)] if art else '-'}{RESET}")
    else:
        L.append(f"{BOLD}{CYAN}Medya{RESET} {DIM}çalar yok{RESET}")
    if media.get("players"):
        L.append(f"      {DIM}açık çalarlar: " +
                 ", ".join(f"{p['identity']} ({p['status']})" for p in media["players"]) + RESET)
    return "\n".join(L)
