"""Claude Code oturumlarının durumu (hook olaylarından, bkz. deploy/claude_hooks.py).

Durumlar: work (çalışıyor) · wait (izin / cevap bekliyor) · done (bitti, sıra sende) · idle (yeni açıldı).
  SessionStart → idle · UserPromptSubmit → work · PostToolUse → (wait idiyse) work
  Notification (izin / soru) → wait · Stop → done · SessionEnd → silinir
Olay gelmeyen oturumlar bir süre sonra unutulur (Claude kapanırken SessionEnd kaçabilir).
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass

FORGET_IDLE_S = 3 * 3600     # bitti/boşta oturumlar
FORGET_ANY_S = 12 * 3600     # takılı kalmış "çalışıyor"
ORDER = {"wait": 0, "work": 1, "done": 2, "idle": 3}


@dataclass
class Session:
    project: str
    state: str = "idle"
    msg: str = ""
    since: float = 0.0       # bu duruma geçtiği an
    work_start: float = 0.0  # son istemin gönderildiği an
    last: float = 0.0        # son olay


def fmt_dur(sec: float) -> str:
    sec = int(sec)
    if sec < 60:
        return f"{sec} sn"
    if sec < 3600:
        return f"{sec // 60} dk {sec % 60} sn" if sec < 600 else f"{sec // 60} dk"
    return f"{sec // 3600} sa {sec // 60 % 60} dk"


def _wait_text(ntype: str, msg: str) -> str | None:
    """Bildirim türünden Türkçe açıklama; beklemeyi gerektirmeyen bildirimlerde None."""
    low = msg.lower()
    if ntype == "permission_prompt" or "permission" in low:
        return "izin bekliyor"
    if ntype == "elicitation_dialog" or "question" in low:
        return "soru soruyor"
    if ntype == "idle_prompt" or "waiting for your input" in low:
        return "cevap bekliyor"
    return None


class ClaudeTracker:
    def __init__(self) -> None:
        self.sessions: dict[str, Session] = {}
        self.version = 0  # durum değişince artar

    def handle(self, ev: dict, min_notify_s: float) -> list[tuple[str, str, str]]:
        """Olayı işler; karta gidecek bildirimler: [(başlık, gövde, düzey)]."""
        sid, name = ev.get("sid", ""), ev.get("ev", "")
        if not sid:
            return []
        now = time.monotonic()
        project = os.path.basename(ev.get("cwd", "").rstrip("/")) or "?"
        if ev.get("acct"):  # ikinci hesap (CLAUDE_CONFIG_DIR=~/.claude-<ad>)
            project = f"{project} · {ev['acct']}"
        s = self.sessions.get(sid)
        if name == "SessionEnd":
            if self.sessions.pop(sid, None):
                self.version += 1
            return []
        if s is None:
            s = self.sessions[sid] = Session(project=project, since=now)
        s.project, s.last = project, now
        old = (s.state, s.msg)
        notes: list[tuple[str, str, str]] = []

        if name == "SessionStart":
            if s.state != "work":
                s.state, s.msg = "idle", ""
        elif name == "UserPromptSubmit":
            s.state, s.msg, s.work_start = "work", "", now
        elif name == "PostToolUse":
            if s.state == "wait":
                s.state, s.msg = "work", ""
        elif name == "Notification":
            text = _wait_text(ev.get("ntype", ""), ev.get("msg", ""))
            if text == "cevap bekliyor":
                # Bitirdikten bir süre sonra gelen "hâlâ bekliyorum" hatırlatması: durum zaten "bitti"
                if s.state != "done":
                    s.state, s.msg = "wait", text
            elif text:
                s.state, s.msg = "wait", text
                notes.append((f"{project}: {text}", ev.get("msg", ""), "wait"))
        elif name == "Stop":
            took = now - s.work_start if s.work_start else 0
            s.state, s.msg = "done", ""
            if s.work_start and took >= min_notify_s:
                notes.append((f"{project}: bitti", f"Claude işini bitirdi ({fmt_dur(took)})", "ok"))
            s.work_start = 0.0

        if (s.state, s.msg) != old:
            s.since = now
            self.version += 1
        return notes

    def prune(self) -> None:
        now = time.monotonic()
        for sid, s in list(self.sessions.items()):
            limit = FORGET_ANY_S if s.state in ("work", "wait") else FORGET_IDLE_S
            if now - s.last > limit:
                del self.sessions[sid]
                self.version += 1

    def items(self) -> list[dict]:
        now = time.monotonic()
        ordered = sorted(self.sessions.values(), key=lambda s: (ORDER.get(s.state, 9), -s.since))
        return [{"p": s.project[:32], "s": s.state, "m": s.msg, "age": int(now - s.since)} for s in ordered]
