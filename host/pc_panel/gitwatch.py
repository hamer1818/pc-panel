"""Push / commit edilmemiş iş: ayardaki klasörlerin altındaki git depoları (bir seviye).

Yalnızca son `gun` gün içinde dokunulan depolar sayılır (aylardır açılmayan depolar gürültü yapmasın):
- push bekleyen: geçerli dalda hiçbir uzak depoda olmayan commit (`git rev-list HEAD --not --remotes`),
  depo son `gun` günde commit/checkout gördüyse (.git/logs/HEAD);
- değişiklik: `git status` boş değil ve değişen dosyalardan biri son `gun` gün içinde değişmiş (silinen dosyalar
  yalnızca depo son `gun` günde etkinse sayılır).
`--no-optional-locks`: tarama .git/index'e yazmaz, açık editör/IDE ile çakışmaz.
"""

from __future__ import annotations

import subprocess
import time
from pathlib import Path

TIMEOUT_S = 10
NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)  # Windows: konsol penceresi açılmasın


def _git(repo: Path, *args: str) -> str | None:
    try:
        r = subprocess.run(["git", "--no-optional-locks", "-C", str(repo), *args],
                           capture_output=True, text=True, encoding="utf-8", errors="replace",
                           timeout=TIMEOUT_S, creationflags=NO_WINDOW)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return r.stdout if r.returncode == 0 else None


def _recent(path: Path, since: float, missing: bool = False) -> bool:
    try:
        return path.stat().st_mtime >= since
    except OSError:
        return missing  # silinmiş dosya: zamanı bilinmez


def _is_repo(p: Path) -> bool:
    try:
        return (p / ".git").is_dir()
    except OSError:  # Windows: ev klasöründeki erişimi kapalı bağlantılar ("Application Data" …)
        return False


def scan(roots: tuple[str, ...], days: int) -> dict:
    """Engelleyici. {"ahead": [(ad, sayı)], "dirty": [ad]}"""
    since = time.time() - days * 86400
    ahead, dirty = [], []
    for root in roots:
        base = Path(root).expanduser()
        if not base.is_dir():
            continue
        for repo in sorted(p for p in base.iterdir() if _is_repo(p)):
            active = _recent(repo / ".git" / "logs" / "HEAD", since)
            if active and _git(repo, "remote"):
                n = _git(repo, "rev-list", "--count", "HEAD", "--not", "--remotes")
                if n and n.strip().isdigit() and int(n) > 0:
                    ahead.append((repo.name, int(n)))
            status = _git(repo, "status", "--porcelain=v1", "-z")
            if status:
                # -z: "XY yol\0" (yeniden adlandırmada ek bir "eski yol\0")
                parts = [p for p in status.split("\0") if p]
                paths = [p[3:] for p in parts if len(p) > 3 and p[2] == " "]
                # silinmiş dosyalar yalnızca depo yakın zamanda etkinse sayılır
                if any(_recent(repo / p, since, missing=active) for p in paths[:200]):
                    dirty.append(repo.name)
    return {"ahead": ahead, "dirty": dirty}


def summary_text(res: dict) -> tuple[str, int]:
    """Kart için tek satır ve dikkat isteyen depo sayısı."""
    parts = []
    if res["ahead"]:
        parts.append("Push bekliyor: " + ", ".join(f"{n} ({c})" for n, c in res["ahead"]))
    if res["dirty"]:
        parts.append("commit edilmemiş: " + ", ".join(res["dirty"]))
    count = len({n for n, _ in res["ahead"]} | set(res["dirty"]))
    return (" · ".join(parts) if parts else "Git: bekleyen iş yok"), count
