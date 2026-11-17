"""GitHub: son Actions çalışmaları, inceleme bekleyen PR'lar, okunmamış bildirimler (`gh api` ile).

Kimlik doğrulama `gh`'nin kendisinde (gh auth login); bu servis anahtar saklamaz.
Depolar ayarda yazılmadıysa: en son push yapılan, fork ya da arşiv olmayan 6 depo.
Bildirimler: izlerken biten çalışma (✓/✗) ve yeni görülen başarısız çalışma. İlk yoklamada bildirim yok.
Başarılı sonuçlar yalnızca push / PR / elle başlatılan çalışmalar için bildirilir (zamanlanmış işler gürültü yapmasın).
"""

from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone

AUTO_REPOS = 6
TIMEOUT_S = 20
NOTIFY_SUCCESS_EVENTS = {"push", "pull_request", "workflow_dispatch", "release"}


class GhError(Exception):
    pass


def _gh(path: str):
    try:
        r = subprocess.run(["gh", "api", path], capture_output=True, text=True, timeout=TIMEOUT_S)
    except FileNotFoundError:
        raise GhError("gh kurulu değil") from None
    except subprocess.TimeoutExpired:
        raise GhError("gh zaman aşımı") from None
    if r.returncode != 0:
        err = (r.stderr or "").strip().splitlines()
        raise GhError(err[-1][:80] if err else f"gh hata {r.returncode}")
    return json.loads(r.stdout or "null")


def _ts(iso: str | None) -> float:
    if not iso:
        return 0.0
    return datetime.fromisoformat(iso.replace("Z", "+00:00")).timestamp()


def _state(run: dict) -> str:
    if run.get("status") != "completed":
        return "wait" if run.get("status") in ("queued", "waiting", "pending", "requested") else "run"
    return {"success": "ok", "failure": "fail", "timed_out": "fail", "startup_failure": "fail",
            "cancelled": "cancel", "skipped": "cancel"}.get(run.get("conclusion") or "", "cancel")


class GitHubWatcher:
    def __init__(self) -> None:
        self._seen: dict[int, str] = {}  # çalışma kimliği → son durum
        self._first = True

    def _repos(self, configured: tuple[str, ...]) -> list[str]:
        if configured:
            return list(configured)
        repos = _gh("/user/repos?sort=pushed&per_page=20&affiliation=owner")
        return [r["full_name"] for r in repos if not r.get("fork") and not r.get("archived")][:AUTO_REPOS]

    def poll(self, configured: tuple[str, ...]) -> tuple[dict, list[tuple[str, str, str]]]:
        """Engelleyici (iş parçacığında çağırın). (kart verisi, bildirimler). Hata: GhError."""
        now = datetime.now(timezone.utc).timestamp()
        runs, notes = [], []
        for full in self._repos(configured):
            data = _gh(f"/repos/{full}/actions/runs?per_page=3")
            wr = (data or {}).get("workflow_runs") or []
            if not wr:
                continue
            for run in wr:  # yalnızca en son çalışma gösterilir ama hepsinin geçişleri izlenir
                rid, st = run["id"], _state(run)
                prev = self._seen.get(rid)
                if not self._first and prev != st and st in ("ok", "fail"):
                    repo = full.split("/")[1]
                    dur = max(0, _ts(run.get("updated_at")) - _ts(run.get("run_started_at")))
                    what = f"{run.get('name', 'CI')} · {run.get('head_branch', '')} · {int(dur // 60)} dk {int(dur % 60)} sn"
                    if st == "fail" and prev != "fail":
                        notes.append((f"{repo}: CI başarısız", what, "err"))
                    elif st == "ok" and prev in ("run", "wait") and run.get("event") in NOTIFY_SUCCESS_EVENTS:
                        notes.append((f"{repo}: CI başarılı", what, "ok"))
                self._seen[rid] = st
            last = wr[0]
            runs.append({"r": full.split("/")[1][:20], "w": (last.get("name") or "")[:16], "s": _state(last),
                         "b": (last.get("head_branch") or "")[:16],
                         "age": int(max(0, now - _ts(last.get("updated_at")))), "_t": _ts(last.get("updated_at"))})
        runs.sort(key=lambda x: -x.pop("_t"))
        review = _gh("/search/issues?q=is:pr+is:open+review-requested:@me&per_page=1").get("total_count", 0)
        mine = _gh("/search/issues?q=is:pr+is:open+author:@me&per_page=1").get("total_count", 0)
        notifications = len(_gh("/notifications?per_page=50") or [])
        if len(self._seen) > 500:  # eski kimlikleri unut
            self._seen = dict(list(self._seen.items())[-200:])
        self._first = False
        return {"runs": runs, "review": review, "my_prs": mine, "notifications": notifications}, notes
