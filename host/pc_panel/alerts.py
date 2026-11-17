"""Sıcaklık / bellek / disk uyarıları (eşikler ayar dosyasında, `[uyari]`).

- CPU, GPU sıcaklığı ve RAM: eşik aşılınca uyarı başlar, eşiğin HYST altına inince biter (titreşmesin diye).
  Etkin uyarılar `stat` mesajındaki `warn` alanıyla kartın üst şeridinde gösterilir.
- Disk: eşik aşılınca bir kez bildirim; disk eşiğin HYST altına inince yeniden kurulur.
"""

from __future__ import annotations

from .config import Settings

HYST = 5.0


class AlertTracker:
    def __init__(self) -> None:
        self._active: dict[str, bool] = {}
        self._disk_fired: set[str] = set()

    def _check(self, key: str, value: float | None, limit: float) -> bool:
        if not limit or value is None:
            self._active[key] = False
            return False
        on = self._active.get(key, False)
        on = value >= limit - HYST if on else value >= limit
        self._active[key] = on
        return on

    def update(self, sysd: dict, gpu: dict | None, s: Settings) -> tuple[str, list[str]]:
        """(üst şerit uyarı metni ya da "", yeni disk bildirimleri)."""
        parts = []
        if self._check("cpu", sysd.get("cpu_temp"), s.warn_cpu):
            parts.append(f"CPU {sysd['cpu_temp']:.0f}°C")
        gt = gpu.get("temp") if gpu else None
        if self._check("gpu", gt, s.warn_gpu):
            parts.append(f"GPU {gt:.0f}°C")
        if self._check("ram", sysd.get("ram_pct"), s.warn_ram):
            parts.append(f"RAM %{sysd['ram_pct']:.0f}")

        events = []
        for d in sysd.get("disks", []):
            m, p = d["mount"], d["pct"]
            if s.warn_disk and p >= s.warn_disk and m not in self._disk_fired:
                self._disk_fired.add(m)
                events.append(f"{m} %{p:.0f} dolu")
            elif m in self._disk_fired and (not s.warn_disk or p < s.warn_disk - HYST):
                self._disk_fired.discard(m)
        return " · ".join(parts), events
