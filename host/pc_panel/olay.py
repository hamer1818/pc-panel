"""pc-panel-olay — dışarıdan servise olay bildiren küçük araç (Claude Code hook'ları, fish, kendi betiklerin).

    pc-panel-olay claude                          # Claude Code hook'u: olay JSON'u stdin'den gelir
    pc-panel-olay komut --sure MS --kod N -- METİN # fish: uzun süren komut bitti
    pc-panel-olay bildir "Başlık" ["Gövde"]       # karta bildirim (ör. betik sonunda)

Olay, servisin Unix soketine ($XDG_RUNTIME_DIR/pc-panel.sock, yalnızca bu kullanıcı) tek satır JSON olarak
yazılır. Servis kapalıysa sessizce çıkar. HER ZAMAN 0 ile çıkar ve stdout'a hiçbir şey yazmaz: Claude Code bazı
hook'ların çıktısını konuşmaya ekler, hata kodu da Claude'u durdurabilir.
Hızlı açılsın diye yalnızca standart kütüphane kullanır.
"""

from __future__ import annotations

import json
import os
import socket
import sys

SOCK_PATH = os.path.join(os.environ.get("XDG_RUNTIME_DIR") or f"/run/user/{os.getuid()}", "pc-panel.sock")
TIMEOUT_S = 0.5


def send(obj: dict) -> bool:
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
            s.settimeout(TIMEOUT_S)
            s.connect(SOCK_PATH)
            s.sendall((json.dumps(obj, ensure_ascii=False) + "\n").encode())
        return True
    except OSError:
        return False


def _claude() -> dict | None:
    try:
        ev = json.loads(sys.stdin.read(1_000_000) or "{}")
    except (ValueError, OSError):
        return None
    if not isinstance(ev, dict):
        return None
    # Yalnızca gereken alanlar (istem metni, araç girdileri vb. gönderilmez)
    return {"k": "claude", "ev": str(ev.get("hook_event_name", "")), "sid": str(ev.get("session_id", "")),
            "cwd": str(ev.get("cwd", "")), "msg": str(ev.get("message", ""))[:200],
            "ntype": str(ev.get("notification_type", ""))}


def _komut(args: list[str]) -> dict | None:
    sure = kod = None
    text: list[str] = []
    it = iter(args)
    for a in it:
        if a == "--sure":
            sure = next(it, None)
        elif a == "--kod":
            kod = next(it, None)
        elif a == "--":
            text = list(it)
    try:
        return {"k": "cmd", "ms": int(sure or 0), "code": int(kod or 0), "cmd": " ".join(text)[:300]}
    except ValueError:
        return None


def main() -> None:
    args = sys.argv[1:]
    msg = None
    try:
        if args[:1] == ["claude"]:
            msg = _claude()
        elif args[:1] == ["komut"]:
            msg = _komut(args[1:])
        elif args[:1] == ["bildir"] and len(args) >= 2:
            msg = {"k": "notif", "title": args[1][:100], "body": " ".join(args[2:])[:200]}
        elif args[:1] in (["-h"], ["--help"], []):
            sys.stderr.write(__doc__ or "")
    except Exception:  # hook'u asla bozma
        msg = None
    if msg:
        send(msg)
    sys.exit(0)


if __name__ == "__main__":
    main()
