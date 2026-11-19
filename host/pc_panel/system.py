"""Sistem verileri: CPU, sıcaklık, RAM, disk, ağ, çalışma süresi (psutil).

Linux ve Windows'ta aynı çıktı. Windows'ta psutil'in vermediği saat hızı ve CPU sıcaklığı win/sensors.py'den gelir.
"""

from __future__ import annotations

import os
import re
import sys
import time

import psutil

WINDOWS = sys.platform == "win32"

if WINDOWS:
    from .win.sensors import WinSensors, cpu_name_raw
    # Ağ hızında sayılmayacak sanal arayüzler (Windows adları: "vEthernet (WSL)", "Loopback Pseudo-Interface 1" …)
    _VIRTUAL_NIC = re.compile(r"loopback|vethernet|tailscale|virtualbox|vmware|hyper-v|npcap|zerotier|wireguard|"
                              r"teredo|isatap|bluetooth|tap-windows|openvpn", re.I)
    # Disk hızında sayılacak fiziksel diskler
    _PHYSICAL_DISK = re.compile(r"^PhysicalDrive\d+$", re.I)
    DEFAULT_MOUNTS = ((os.environ.get("SystemDrive") or "C:") + "\\",)
else:
    _VIRTUAL_NIC = re.compile(r"^(lo|tailscale\d*|virbr\d*|docker\d*|br-.*|veth.*|vnet\d*|tun\d*|tap\d*|wg\d*)$")
    _PHYSICAL_DISK = re.compile(r"^(nvme\d+n\d+|sd[a-z]+|vd[a-z]+|mmcblk\d+)$")
    # Panelde gösterilecek bağlama noktaları (en çok 2; ayar dosyasında [sistem] diskler)
    DEFAULT_MOUNTS = ("/",)


def _cpu_name_raw() -> str:
    if WINDOWS:
        return cpu_name_raw()
    try:
        with open("/proc/cpuinfo") as f:
            for line in f:
                if line.startswith("model name"):
                    return line.split(":", 1)[1].strip()
    except OSError:
        pass
    return ""


def cpu_name() -> str:
    """Kısa işlemci adı: "AMD Ryzen 7 9800X3D 8-Core Processor" → "Ryzen 7 9800X3D"."""
    name = _cpu_name_raw()
    if not name:
        return ""
    name = re.sub(r"\b(AMD|Intel\(R\)|Core\(TM\)|\(R\)|\(TM\)|CPU|Processor)\b", "", name)
    name = re.sub(r"\b\d+-Core\b|@.*$", "", name)
    return " ".join(name.split())[:28]


class SystemCollector:
    def __init__(self, mounts: tuple[str, ...] = DEFAULT_MOUNTS) -> None:
        self.mounts = mounts
        self._win = WinSensors() if WINDOWS else None
        # cpu_percent ilk çağrıda 0 döner; burada "sıfır noktası" alınır
        psutil.cpu_percent(percpu=True)
        self._last_time = time.monotonic()
        self._last_net = self._net_totals()
        self._last_disk = self._disk_totals()

    @staticmethod
    def _net_totals() -> tuple[int, int]:
        rx = tx = 0
        for name, c in psutil.net_io_counters(pernic=True).items():
            if not (_VIRTUAL_NIC.search(name) if WINDOWS else _VIRTUAL_NIC.match(name)):
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

    def _cpu_temp(self) -> float | None:
        if self._win is not None:
            return self._win.cpu_temp()
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
        mhz = self._win.cpu_mhz() if self._win is not None else None
        if mhz is None and freq:
            mhz = round(freq.current)
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
            label = m.rstrip("\\") if WINDOWS else m  # "C:\\" → "C:"
            disks.append({"mount": label, "used": u.used, "total": u.total, "pct": round(u.percent, 1)})

        return {
            "cpu": round(cpu_total, 1),
            "cpu_cores": [round(c) for c in cores],
            "cpu_mhz": mhz,
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
