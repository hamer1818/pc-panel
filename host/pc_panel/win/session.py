"""Windows oturumu: kilit durumu, ekranı kilitleme, ekran görüntüsü tuşu, kapanışı yakalama (ctypes, Win32).

- Kilit: kilitliyken giriş masaüstü "Winlogon"dur ve kullanıcı süreci onu açamaz (OpenInputDesktop başarısız).
  Açılabiliyorsa adı "Default" mu diye bakılır. (UAC onay penceresi de kısa süre kilitli görünür; zararsız.)
- Ekran görüntüsü: Win+PrtScn (Windows sessizce Resimler\\Ekran Görüntüleri klasörüne kaydeder; Linux'taki
  `spectacle -b -n -f` ile aynı davranış).
- Kapanış: görünmez bir üst düzey pencere WM_ENDSESSION'ı (oturum kapatma / yeniden başlatma / kapatma) yakalar;
  servis karta "bye" gönderip ekranı hemen karartabilsin. (pythonw'nun konsolu olmadığı için Ctrl+C / SIGTERM yok.)
"""

from __future__ import annotations

import ctypes
import threading
from collections.abc import Callable
from ctypes import wintypes

user32 = ctypes.WinDLL("user32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

DESKTOP_SWITCHDESKTOP = 0x0100
UOI_NAME = 2
VK_LWIN, VK_SNAPSHOT, VK_MENU = 0x5B, 0x2C, 0x12
KEYEVENTF_KEYUP = 0x0002
WM_QUERYENDSESSION, WM_ENDSESSION, WM_CLOSE, WM_DESTROY = 0x0011, 0x0016, 0x0010, 0x0002

user32.OpenInputDesktop.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
user32.OpenInputDesktop.restype = wintypes.HANDLE
user32.CloseDesktop.argtypes = [wintypes.HANDLE]
user32.GetUserObjectInformationW.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD,
                                             ctypes.POINTER(wintypes.DWORD)]
user32.keybd_event.argtypes = [wintypes.BYTE, wintypes.BYTE, wintypes.DWORD, ctypes.c_void_p]
user32.LockWorkStation.restype = wintypes.BOOL


def screen_locked() -> bool | None:
    """Oturum kilitli mi? Bilinmiyorsa None."""
    h = user32.OpenInputDesktop(0, False, DESKTOP_SWITCHDESKTOP)
    if not h:
        return True
    try:
        name = ctypes.create_unicode_buffer(64)
        need = wintypes.DWORD()
        if not user32.GetUserObjectInformationW(h, UOI_NAME, name, ctypes.sizeof(name), ctypes.byref(need)):
            return None
        return name.value.lower() != "default"
    finally:
        user32.CloseDesktop(h)


def lock() -> bool:
    return bool(user32.LockWorkStation())


def _tap(*keys: int) -> None:
    for k in keys:
        user32.keybd_event(k, 0, 0, None)
    for k in reversed(keys):
        user32.keybd_event(k, 0, KEYEVENTF_KEYUP, None)


def screenshot() -> bool:
    _tap(VK_LWIN, VK_SNAPSHOT)
    return True


def alt_tap() -> None:
    """Alt'a bas-bırak: Windows, arka plandaki bir sürecin SetForegroundWindow çağrısına ancak son giriş olayı
    ondan geldiyse izin verir (apps.py pencereyi öne getirirken kullanır)."""
    _tap(VK_MENU)


# --- Kapanışı yakalama -------------------------------------------------------------------------

LRESULT = ctypes.c_ssize_t
WNDPROC = ctypes.WINFUNCTYPE(LRESULT, wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM)


class WNDCLASSW(ctypes.Structure):
    _fields_ = [("style", wintypes.UINT), ("lpfnWndProc", WNDPROC), ("cbClsExtra", ctypes.c_int),
                ("cbWndExtra", ctypes.c_int), ("hInstance", wintypes.HINSTANCE), ("hIcon", wintypes.HICON),
                ("hCursor", wintypes.HANDLE), ("hbrBackground", wintypes.HBRUSH),
                ("lpszMenuName", wintypes.LPCWSTR), ("lpszClassName", wintypes.LPCWSTR)]


user32.DefWindowProcW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
user32.DefWindowProcW.restype = LRESULT
user32.RegisterClassW.argtypes = [ctypes.POINTER(WNDCLASSW)]
user32.RegisterClassW.restype = wintypes.ATOM
user32.CreateWindowExW.argtypes = [wintypes.DWORD, wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.DWORD,
                                   ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, wintypes.HWND,
                                   wintypes.HMENU, wintypes.HINSTANCE, ctypes.c_void_p]
user32.CreateWindowExW.restype = wintypes.HWND
user32.GetMessageW.argtypes = [ctypes.POINTER(wintypes.MSG), wintypes.HWND, wintypes.UINT, wintypes.UINT]
user32.TranslateMessage.argtypes = [ctypes.POINTER(wintypes.MSG)]
user32.DispatchMessageW.argtypes = [ctypes.POINTER(wintypes.MSG)]
kernel32.GetModuleHandleW.argtypes = [wintypes.LPCWSTR]
kernel32.GetModuleHandleW.restype = wintypes.HMODULE


def watch_shutdown(on_end: Callable[[], None]) -> None:
    """Arka planda görünmez bir pencere açar; Windows oturumu kapanırken `on_end()` o pencerenin iş parçacığında
    çağrılır (dönene kadar Windows birkaç saniye bekler)."""

    def proc(hwnd, msg, wp, lp):
        if msg == WM_QUERYENDSESSION:
            return 1  # kapanmaya izin ver
        if msg == WM_ENDSESSION:
            if wp:
                try:
                    on_end()
                except Exception:
                    pass
            return 0
        if msg == WM_CLOSE:  # görev yöneticisi vb. pencereyi kapatmak isterse süreç kapanmasın
            return 0
        return user32.DefWindowProcW(hwnd, msg, wp, lp)

    def run() -> None:
        wndproc = WNDPROC(proc)  # çöp toplayıcı silmesin: iş parçacığı boyunca yerel değişkende
        hinst = kernel32.GetModuleHandleW(None)
        wc = WNDCLASSW(lpfnWndProc=wndproc, hInstance=hinst, lpszClassName="PcPanelShutdownWatcher")
        if not user32.RegisterClassW(ctypes.byref(wc)):
            return
        hwnd = user32.CreateWindowExW(0, wc.lpszClassName, "PC Panel", 0, 0, 0, 0, 0, None, None, hinst, None)
        if not hwnd:
            return
        msg = wintypes.MSG()
        while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
            user32.TranslateMessage(ctypes.byref(msg))
            user32.DispatchMessageW(ctypes.byref(msg))

    threading.Thread(target=run, daemon=True, name="shutdown-watcher").start()
