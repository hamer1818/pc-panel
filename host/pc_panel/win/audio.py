"""Sistem sesi ve mikrofon — Windows Core Audio (pycaw / comtypes). Linux karşılığı: audio.py (wpctl).

Her çağrıda varsayılan aygıt yeniden alınır: kulaklık takılınca / çıkış değişince doğru aygıt kullanılsın.
Çağrılar milisaniyenin altında sürer; ana iş parçacığında (COM MTA) yapılır.
"""

from __future__ import annotations

from ctypes import POINTER, cast

from comtypes import CLSCTX_ALL
from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume


def _endpoint(get_device):
    """Varsayılan aygıtın IAudioEndpointVolume arayüzü ya da None (aygıt yok / hata)."""
    try:
        dev = get_device()
        if dev is None:
            return None
        ev = getattr(dev, "EndpointVolume", None)  # pycaw ≥ 2024: AudioDevice sarmalayıcısı
        if ev is not None:
            return ev
        iface = dev.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)  # ham IMMDevice
        return cast(iface, POINTER(IAudioEndpointVolume))
    except Exception:
        return None


def _speakers():
    return _endpoint(AudioUtilities.GetSpeakers)


def _mic():
    return _endpoint(AudioUtilities.GetMicrophone)


def _get(ev) -> tuple[int | None, bool | None]:
    if ev is None:
        return None, None
    try:
        return round(ev.GetMasterVolumeLevelScalar() * 100), bool(ev.GetMute())
    except Exception:
        return None, None


async def state() -> dict:
    (v, mute), (mic, mic_mute) = _get(_speakers()), _get(_mic())
    return {"volume": v, "mute": mute, "mic": mic, "mic_mute": mic_mute}


async def set_volume(pct: float) -> bool:
    ev = _speakers()
    if ev is None:
        return False
    try:
        ev.SetMasterVolumeLevelScalar(max(0.0, min(100.0, pct)) / 100, None)
        return True
    except Exception:
        return False


def _toggle(ev) -> bool:
    if ev is None:
        return False
    try:
        ev.SetMute(0 if ev.GetMute() else 1, None)
        return True
    except Exception:
        return False


async def toggle_mute() -> bool:
    return _toggle(_speakers())


async def toggle_mic() -> bool:
    return _toggle(_mic())
