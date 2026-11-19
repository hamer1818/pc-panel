"""Windows'ta psutil'in vermediği sistem değerleri: işlemci adı, anlık saat hızı, CPU sıcaklığı.

- İşlemci adı: kayıt defteri (HARDWARE\\DESCRIPTION\\System\\CentralProcessor\\0 → ProcessorNameString).
- Saat hızı: psutil Windows'ta yalnızca taban hızı verir. Görev Yöneticisi'nin yaptığı gibi
  "taban MHz × % İşlemci Performansı" hesaplanır (PDH sayaçları, yönetici gerekmez).
- CPU sıcaklığı: Windows'un kendisi Ryzen/Core sıcaklığını kullanıcıya vermez (sürücü gerekir).
  LibreHardwareMonitor açıksa onun WMI sağlayıcısından (root\\LibreHardwareMonitor) okunur; yoksa None
  (kartta "-"). Kurulum: docs/01-donanim.md → "Windows'ta CPU sıcaklığı".
"""

from __future__ import annotations

import ctypes
import time
import winreg
from ctypes import byref, wintypes

PERF = r"\Processor Information(_Total)\% Processor Performance"
BASE = r"\Processor Information(_Total)\Processor Frequency"
LHM_NAMESPACE = "winmgmts:root/LibreHardwareMonitor"
LHM_RETRY_S = 30.0
# Tercih sırası: AMD Tctl/Tdie, Intel paket
_CPU_TEMP_NAMES = ("Core (Tctl/Tdie)", "Core (Tctl)", "Tctl", "Tdie", "CPU Package", "Package")


def cpu_name_raw() -> str:
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"HARDWARE\DESCRIPTION\System\CentralProcessor\0") as k:
            return str(winreg.QueryValueEx(k, "ProcessorNameString")[0]).strip()
    except OSError:
        return ""


class _PdhValue(ctypes.Structure):
    _fields_ = [("CStatus", wintypes.DWORD), ("doubleValue", ctypes.c_double)]  # birlik 8 bayta hizalı


class _Pdh:
    PDH_FMT_DOUBLE = 0x00000200
    PDH_FMT_NOCAP100 = 0x00008000

    def __init__(self, paths: list[str]) -> None:
        self.dll = ctypes.WinDLL("pdh")
        self.query = wintypes.HANDLE()
        self.counters: list[wintypes.HANDLE] = []
        if self.dll.PdhOpenQueryW(None, None, byref(self.query)) != 0:
            raise OSError("PdhOpenQuery")
        for p in paths:
            c = wintypes.HANDLE()
            if self.dll.PdhAddEnglishCounterW(self.query, ctypes.c_wchar_p(p), None, byref(c)) != 0:
                raise OSError(f"PdhAddEnglishCounter {p}")
            self.counters.append(c)
        self.dll.PdhCollectQueryData(self.query)

    def read(self) -> list[float | None]:
        if self.dll.PdhCollectQueryData(self.query) != 0:
            return [None] * len(self.counters)
        out: list[float | None] = []
        for c in self.counters:
            v = _PdhValue()
            ok = self.dll.PdhGetFormattedCounterValue(c, self.PDH_FMT_DOUBLE | self.PDH_FMT_NOCAP100, None, byref(v))
            out.append(v.doubleValue if ok == 0 else None)
        return out


class WinSensors:
    def __init__(self) -> None:
        try:
            self._pdh: _Pdh | None = _Pdh([PERF, BASE])
        except OSError:
            self._pdh = None
        self._lhm = None
        self._lhm_next = 0.0

    def cpu_mhz(self) -> int | None:
        if self._pdh is None:
            return None
        perf, base = self._pdh.read()
        if not perf or not base:
            return None
        return round(base * perf / 100)

    def _lhm_service(self):
        if self._lhm is None and time.monotonic() >= self._lhm_next:
            self._lhm_next = time.monotonic() + LHM_RETRY_S
            try:
                from comtypes.client import CoGetObject
                self._lhm = CoGetObject(LHM_NAMESPACE)
            except Exception:  # LibreHardwareMonitor kapalı / kurulu değil
                self._lhm = None
        return self._lhm

    def cpu_temp(self) -> float | None:
        svc = self._lhm_service()
        if svc is None:
            return None
        try:
            rows = svc.ExecQuery("SELECT Identifier, Name, Value FROM Sensor WHERE SensorType='Temperature'")
            temps: dict[str, float] = {}
            for r in rows:
                ident = str(r.Properties_("Identifier").Value or "")
                if ident.startswith(("/amdcpu/", "/intelcpu/")):
                    temps.setdefault(str(r.Properties_("Name").Value or ""), float(r.Properties_("Value").Value))
        except Exception:
            self._lhm = None  # LibreHardwareMonitor kapandı: bir süre sonra yeniden bağlan
            return None
        for name in _CPU_TEMP_NAMES:
            if name in temps:
                return round(temps[name], 1)
        return round(next(iter(temps.values())), 1) if temps else None
