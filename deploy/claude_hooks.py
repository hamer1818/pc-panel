#!/usr/bin/env python3
"""Claude Code hook'larını settings.json'a ekler / kaldırır (PC Panel Geliştirici sayfası için).

    deploy/claude_hooks.py kur      [DİZİN…]   # ekle (önce settings.json'ın yedeğini alır)
    deploy/claude_hooks.py kaldir   [DİZİN…]   # yalnızca PC Panel'in eklediği hook'ları siler
    deploy/claude_hooks.py durum    [DİZİN…]   # kurulu mu?

DİZİN verilmezse bütün Claude Code ayar dizinleri işlenir: ~/.claude ve CLAUDE_CONFIG_DIR ile kullanılan
~/.claude-* dizinleri (ör. ~/.claude-hesap2). Varsayılan dışındaki dizinlerde hook `--hesap <ad>` ile çağrılır
(ad: ".claude-" sonrası, ör. "hesap2"); kartta oturum adının yanında görünür.

Eklenen hook'lar yalnızca `pc-panel-olay claude` çalıştırır: olay adı, oturum kimliği, çalışma klasörü ve
bildirim metni yerel Unix soketinden (Windows'ta 127.0.0.1 TCP) servise gider.
Windows'ta: host/.venv/Scripts/python.exe deploy/claude_hooks.py kur   (deploy/kur.ps1 bunu kendisi çalıştırır) İstem metni ve araç girdileri gönderilmez. Araç hiçbir şey
yazdırmaz ve her zaman 0 ile çıkar, yani Claude'un çalışmasını etkilemez.
Yeni ayarlar yeni açılan Claude Code oturumlarında geçerli olur.
"""

from __future__ import annotations

import json
import shutil
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WINDOWS = sys.platform == "win32"
OLAY = ROOT / "host" / ".venv" / ("Scripts/pc-panel-olay.exe" if WINDOWS else "bin/pc-panel-olay")


def olay_command() -> str:
    """Hook komutundaki program yolu. Windows'ta Claude Code hook'ları Git Bash ile çalıştırır: ters bölü yerine
    düz bölü ("C:/…/pc-panel-olay.exe"), boşluk varsa tırnak."""
    path = OLAY.as_posix()
    return f'"{path}"' if " " in path else path
DEFAULT_DIR = Path.home() / ".claude"
MARK = "pc-panel-olay"
EVENTS = ["SessionStart", "UserPromptSubmit", "PostToolUse", "Notification", "Stop", "SessionEnd"]


def find_dirs() -> list[Path]:
    """~/.claude ve içinde settings.json ya da projects/ olan ~/.claude-* dizinleri."""
    dirs = [DEFAULT_DIR] if DEFAULT_DIR.is_dir() else []
    for d in sorted(Path.home().glob(".claude-*")):
        if d.is_dir() and ((d / "settings.json").exists() or (d / "projects").is_dir()):
            dirs.append(d)
    return dirs


def account(d: Path) -> str:
    """Varsayılan dizin için "", ~/.claude-hesap2 için "hesap2"."""
    name = d.name
    return "" if d.resolve() == DEFAULT_DIR.resolve() else (name.removeprefix(".claude-") or name).lstrip(".")


def _load(settings: Path) -> dict:
    if not settings.exists():
        return {}
    return json.loads(settings.read_text(encoding="utf-8-sig"))  # Windows'ta varsayılan cp1254 olurdu


def _save(settings: Path, data: dict) -> None:
    backup = settings.with_name(f"settings.json.yedek-{time.strftime('%Y%m%d-%H%M%S')}")
    if settings.exists():
        shutil.copy2(settings, backup)
        print(f"  yedek: {backup}")
    tmp = settings.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    tmp.replace(settings)


def _ours(group: dict) -> bool:
    return any(MARK in str(h.get("command", "")) for h in group.get("hooks", []))


def remove(data: dict) -> int:
    hooks = data.get("hooks") or {}
    n = 0
    for ev in list(hooks):
        groups = hooks[ev]
        keep = [g for g in groups if not _ours(g)]
        n += len(groups) - len(keep)
        if keep:
            hooks[ev] = keep
        else:
            del hooks[ev]
    if not hooks:
        data.pop("hooks", None)
    return n


def handle(cmd: str, d: Path) -> None:
    settings = d / "settings.json"
    data = _load(settings)
    acct = account(d)
    print(f"{d}{f'  (hesap: {acct})' if acct else ''}")
    if cmd == "durum":
        hooks = data.get("hooks") or {}
        found = [ev for ev, groups in hooks.items() if any(_ours(g) for g in groups)]
        print("  kurulu: " + ", ".join(found) if found else "  kurulu değil")
    elif cmd == "kaldir":
        n = remove(data)
        if n:
            _save(settings, data)
        print(f"  {n} hook kaldırıldı")
    elif cmd == "kur":
        remove(data)  # eski sürüm varsa yenisiyle değiştir
        hooks = data.setdefault("hooks", {})
        command = f"{olay_command()} claude" + (f" --hesap {acct}" if acct else "")
        for ev in EVENTS:
            group = {"hooks": [{"type": "command", "command": command, "timeout": 3}]}
            if ev == "PostToolUse":
                group = {"matcher": "*", **group}
            hooks.setdefault(ev, []).append(group)
        _save(settings, data)
        print(f"  {len(EVENTS)} hook eklendi: {', '.join(EVENTS)}")


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    cmd = sys.argv[1] if len(sys.argv) > 1 else "durum"
    if cmd not in ("kur", "kaldir", "durum"):
        print(__doc__)
        return 2
    if cmd == "kur" and not OLAY.exists():
        print(f"{OLAY} yok: önce host/ içinde `uv sync` çalıştırın", file=sys.stderr)
        return 1
    dirs = [Path(a).expanduser() for a in sys.argv[2:]] or find_dirs()
    if not dirs:
        print("Claude Code ayar dizini bulunamadı (~/.claude)")
        return 1
    for d in dirs:
        handle(cmd, d)
    if cmd == "kur":
        print("Yeni açılan Claude Code oturumlarında geçerli olur.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
