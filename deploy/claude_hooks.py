#!/usr/bin/env python3
"""Claude Code hook'larını ~/.claude/settings.json'a ekler / kaldırır (PC Panel Geliştirici sayfası için).

    deploy/claude_hooks.py kur      # ekle (önce settings.json'ın yedeğini alır)
    deploy/claude_hooks.py kaldir   # yalnızca PC Panel'in eklediği hook'ları siler
    deploy/claude_hooks.py durum    # kurulu mu?

Eklenen hook'lar yalnızca `pc-panel-olay claude` çalıştırır: olay adı, oturum kimliği, çalışma klasörü ve
bildirim metni yerel Unix soketinden servise gider. İstem metni ve araç girdileri gönderilmez. Araç hiçbir şey
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
OLAY = ROOT / "host" / ".venv" / "bin" / "pc-panel-olay"
SETTINGS = Path.home() / ".claude" / "settings.json"
MARK = "pc-panel-olay"
EVENTS = ["SessionStart", "UserPromptSubmit", "PostToolUse", "Notification", "Stop", "SessionEnd"]


def _load() -> dict:
    if not SETTINGS.exists():
        return {}
    return json.loads(SETTINGS.read_text())


def _save(data: dict) -> None:
    backup = SETTINGS.with_name(f"settings.json.yedek-{time.strftime('%Y%m%d-%H%M%S')}")
    if SETTINGS.exists():
        shutil.copy2(SETTINGS, backup)
        print(f"yedek: {backup}")
    tmp = SETTINGS.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    tmp.replace(SETTINGS)


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


def main() -> int:
    cmd = sys.argv[1] if len(sys.argv) > 1 else "durum"
    data = _load()
    if cmd == "durum":
        hooks = data.get("hooks") or {}
        found = [ev for ev, groups in hooks.items() if any(_ours(g) for g in groups)]
        print("kurulu: " + ", ".join(found) if found else "kurulu değil")
        return 0
    if cmd == "kaldir":
        n = remove(data)
        if n:
            _save(data)
        print(f"{n} hook kaldırıldı")
        return 0
    if cmd == "kur":
        if not OLAY.exists():
            print(f"{OLAY} yok: önce host/ içinde `uv sync` çalıştırın", file=sys.stderr)
            return 1
        remove(data)  # eski sürüm varsa yenisiyle değiştir
        hooks = data.setdefault("hooks", {})
        for ev in EVENTS:
            group = {"hooks": [{"type": "command", "command": f"{OLAY} claude", "timeout": 3}]}
            if ev == "PostToolUse":
                group = {"matcher": "*", **group}
            hooks.setdefault(ev, []).append(group)
        _save(data)
        print(f"{len(EVENTS)} hook eklendi: {', '.join(EVENTS)}")
        print("Yeni açılan Claude Code oturumlarında geçerli olur.")
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main())
