"""Sistem verileri: CPU, sıcaklık, RAM, disk, ağ, çalışma süresi (psutil)."""

from __future__ import annotations

import re
import time

import psutil

# Ağ hızında sayılmayacak sanal arayüzler
_VIRTUAL_NIC = re.compile(r"^(lo|tailscale\d*|virbr\d*|docker\d*|br-.*|veth.*|vnet\d*|tun\d*|tap\d*|wg\d*)$")
# Disk hızında sayılacak fiziksel diskler (bölümler değil)
_PHYSICAL_DISK = re.compile(r"^(nvme\d+n\d+|sd[a-z]+|vd[a-z]+|mmcblk\d+)$")

# Panelde gösterilecek bağlama noktaları (en çok 2; ayar dosyasında [sistem] diskler)
DEFAULT_MOUNTS = ("/",)


def cpu_name() -> str:
    """/proc/cpuinfo'dan kısa işlemci adı: "AMD Ryzen 7 9800X3D 8-Core Processor" → "Ryzen 7 9800X3D"."""
    try:
        with open("/proc/cpuinfo") as f:
            for line in f:
                if line.startswith("model name"):
                    name = line.split(":", 1)[1].strip()
                    break
            else:
                return ""
    except OSError:
        return ""
    name = re.sub(r"\b(AMD|Intel\(R\)|Core\(TM\)|\(R\)|\(TM\)|CPU|Processor)\b", "", name)
    name = re.sub(r"\b\d+-Core\b|@.*$", "", name)
    return " ".join(name.split())[:28]


class SystemCollector:
    def __init__(self, mounts: tuple[str, ...] = DEFAULT_MOUNTS) -> None:
        self.mounts = mounts
        # cpu_percent ilk çağrıda 0 döner; burada "sıfır noktası" alınır
        psutil.cpu_percent(percpu=True)
        self._last_time = time.monotonic()
        self._last_net = self._net_totals()
        self._last_disk = self._disk_totals()

    @staticmethod
    def _net_totals() -> tuple[int, int]:
        rx = tx = 0
        for name, c in psutil.net_io_counters(pernic=True).items():
            if not _VIRTUAL_NIC.match(name):
                rx += c.bytes_recv
                tx += c.bytes_sent
        return rx, tx

    @staticmethod
    def _disk_totals() -> tuple[int, int]:
        rd = wr = 0
        for name, c in (psutil.disk_io_counters(perdisk=True) or {}).items():
            if _PHYSICAL_DISK.match(name):
                rd += c.read_bytes
                wr += c.write_bytes
        return rd, wr

    @staticmethod
    def _cpu_temp() -> float | None:
        temps = psutil.sensors_temperatures()
        # AMD: k10temp → Tctl (9800X3D'de ofset yok), yoksa Tdie / ilk değer
        for chip in ("k10temp", "zenpower", "coretemp"):
            sensors = temps.get(chip)
            if not sensors:
                continue
            for wanted in ("Tctl", "Tdie", "Package id 0"):
                for s in sensors:
                    if s.label == wanted:
                        return round(s.current, 1)
            return round(sensors[0].current, 1)
        return None

    def sample(self) -> dict:
        now = time.monotonic()
        dt = max(now - self._last_time, 1e-3)

        cores = psutil.cpu_percent(percpu=True)
        cpu_total = sum(cores) / len(cores) if cores else 0.0
        freq = psutil.cpu_freq()
        vm = psutil.virtual_memory()
        sw = psutil.swap_memory()

        rx, tx = self._net_totals()
        rd, wr = self._disk_totals()
        net_down = (rx - self._last_net[0]) / dt
        net_up = (tx - self._last_net[1]) / dt
        disk_read = (rd - self._last_disk[0]) / dt
        disk_write = (wr - self._last_disk[1]) / dt
        self._last_time, self._last_net, self._last_disk = now, (rx, tx), (rd, wr)

        disks = []
        for m in self.mounts:
            try:
                u = psutil.disk_usage(m)
            except OSError:
                continue
            disks.append({"mount": m, "used": u.used, "total": u.total, "pct": round(u.percent, 1)})

        return {
            "cpu": round(cpu_total, 1),
            "cpu_cores": [round(c) for c in cores],
            "cpu_mhz": round(freq.current) if freq else None,
            "cpu_temp": self._cpu_temp(),
            "ram_used": vm.total - vm.available,
            "ram_total": vm.total,
            "ram_pct": round(vm.percent, 1),
            "swap_pct": round(sw.percent, 1),
            "disks": disks,
            "disk_read_bps": max(disk_read, 0),
            "disk_write_bps": max(disk_write, 0),
            "net_down_bps": max(net_down, 0),
            "net_up_bps": max(net_up, 0),
            "uptime_s": int(time.time() - psutil.boot_time()),
            "load1": round(psutil.getloadavg()[0], 2),
        }
