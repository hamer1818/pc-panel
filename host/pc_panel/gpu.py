"""NVIDIA GPU verileri (NVML / nvidia-ml-py). GPU ya da sürücü yoksa sessizce devre dışı kalır."""

from __future__ import annotations

import pynvml


class GpuCollector:
    def __init__(self, index: int = 0) -> None:
        self.available = False
        self.name: str | None = None
        try:
            pynvml.nvmlInit()
            self._h = pynvml.nvmlDeviceGetHandleByIndex(index)
            name = pynvml.nvmlDeviceGetName(self._h)
            self.name = name.decode() if isinstance(name, bytes) else name
            self.available = True
        except pynvml.NVMLError:
            self._h = None

    def _try(self, fn, *args):
        try:
            return fn(self._h, *args)
        except pynvml.NVMLError:
            return None

    def sample(self) -> dict | None:
        if not self.available:
            return None
        util = self._try(pynvml.nvmlDeviceGetUtilizationRates)
        mem = self._try(pynvml.nvmlDeviceGetMemoryInfo)
        power_mw = self._try(pynvml.nvmlDeviceGetPowerUsage)
        limit_mw = self._try(pynvml.nvmlDeviceGetEnforcedPowerLimit)
        return {
            "name": self.name,
            "util": util.gpu if util else None,
            "mem_util": util.memory if util else None,
            "temp": self._try(pynvml.nvmlDeviceGetTemperature, pynvml.NVML_TEMPERATURE_GPU),
            "vram_used": mem.used if mem else None,
            "vram_total": mem.total if mem else None,
            "power_w": round(power_mw / 1000, 1) if power_mw is not None else None,
            "power_limit_w": round(limit_mw / 1000) if limit_mw is not None else None,
            "fan_pct": self._try(pynvml.nvmlDeviceGetFanSpeed),
            "clock_mhz": self._try(pynvml.nvmlDeviceGetClockInfo, pynvml.NVML_CLOCK_GRAPHICS),
        }

    def close(self) -> None:
        if self.available:
            try:
                pynvml.nvmlShutdown()
            except pynvml.NVMLError:
                pass
