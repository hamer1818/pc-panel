"""Kartla seri bağlantı: satır satır JSON, kablo çıkıp takılınca kendiliğinden yeniden bağlanma.

Okuma ve yazma ayrı iş parçacıklarında yapılır (pyserial engelleyici). Gelen satırlar asyncio kuyruğuna aktarılır.
Giden her şey tek bir yazma kuyruğundan sırayla yazılır: 115 KB'lık kapak resmi (≈1,3 sn) hem ana döngüyü
bekletmez hem de ortasına başka bir satır karışmaz.
Port açılırken DTR/RTS pyserial varsayılanında (açık) bırakılır: kapatılırsa kartın otomatik reset devresi
kartı yeniden başlatıyor (deneyle doğrulandı, bkz. docs/02-mimari.md).
"""

from __future__ import annotations

import asyncio
import glob
import json
import os
import queue
import sys
import threading
import time

import serial
from serial.tools import list_ports

WINDOWS = sys.platform == "win32"
CARD_VID, CARD_PID = 0x1A86, 0x55D3  # WCH CH343 (kartın USB-UART girişi)
DEFAULT_BAUD = 921600
RECONNECT_S = 2.0
PACE_MIN, PACE_CHUNK, PACE_RATIO = 4096, 1024, 0.85  # yalnızca Windows, bkz. _write_paced


def find_port(preferred: str | None) -> str | None:
    ports = list_ports.comports()
    if preferred:
        if WINDOWS:  # "COM4" bir dosya yolu değil; takılı portlar arasında mı diye bakılır
            return next((p.device for p in ports if p.device.upper() == preferred.upper()), None)
        return preferred if os.path.exists(preferred) else None
    # Kart USB kimliğiyle (VID:PID) bulunur. Linux'ta varsa kalıcı /dev/serial/by-id yolu tercih edilir
    # (ttyACM numarası takılış sırasına göre değişebilir); Windows'ta COM numarası zaten kalıcıdır.
    for p in ports:
        if p.vid == CARD_VID and p.pid == CARD_PID:
            for link in glob.glob("/dev/serial/by-id/*"):
                if os.path.realpath(link) == os.path.realpath(p.device):
                    return link
            return p.device
    return None


class SerialLink:
    def __init__(self, port: str | None = None, baud: int = DEFAULT_BAUD, log=print) -> None:
        self.port_arg = port
        self.baud = baud
        self.log = log
        self.ser: serial.Serial | None = None
        self.port_name: str | None = None
        self.lines: asyncio.Queue[str] = asyncio.Queue()
        self.last_rx = 0.0
        self._loop: asyncio.AbstractEventLoop | None = None
        self._lock = threading.Lock()
        self._busy_warned = False
        self._lost_reason = ""
        self._outq: queue.Queue[bytes] | None = None
        self.generation = 0  # her yeni bağlantıda artar (ör. kapak resmini yeniden göndermek için)

    @property
    def connected(self) -> bool:
        return self.ser is not None

    def _open(self) -> bool:
        port = find_port(self.port_arg)
        if not port:
            return False
        try:
            # exclusive=True: portu başka bir program (ör. ikinci bir pc-panel ya da `pio device monitor`)
            # açmışsa açılmaz. İki okuyucu aynı portta birbirinin verisini çalıp bağlantıyı koparıyordu.
            ser = serial.Serial(port, self.baud, timeout=0.2, write_timeout=5, exclusive=True)
        except (serial.SerialException, OSError) as e:
            text = str(e).lower()
            # Linux: "Could not exclusively lock port" / "busy". Windows: PermissionError(13, "Erişim engellendi",
            # None, 5) — COM portları Windows'ta zaten tek programa açılır.
            if "lock" in text or "busy" in text or "permissionerror" in text or "winerror 5" in text \
                    or getattr(e, "errno", None) == 13:
                if not self._busy_warned:
                    self.log("port başka bir program tarafından kullanılıyor (başka bir pc-panel ya da seri monitör "
                             "açık mı?); boşalması bekleniyor…")
                    self._busy_warned = True
            return False
        self._busy_warned = False
        ser.reset_input_buffer()
        outq: queue.Queue[bytes] = queue.Queue()
        self.ser, self.port_name, self._outq = ser, port, outq
        self.generation += 1
        threading.Thread(target=self._reader, args=(ser,), daemon=True, name="serial-reader").start()
        threading.Thread(target=self._writer, args=(ser, outq), daemon=True, name="serial-writer").start()
        self.log(f"kart bağlandı: {port}")
        return True

    def _reader(self, ser: serial.Serial) -> None:
        buf = b""
        while self.ser is ser:
            try:
                data = ser.read(4096)
            except (serial.SerialException, OSError, TypeError) as e:
                self._lost_reason = f"okuma: {e}"
                break
            if not data:
                continue
            buf += data
            *lines, buf = buf.split(b"\n")
            for raw in lines:
                text = raw.rstrip(b"\r").decode("utf-8", "replace")
                if text:
                    self._loop.call_soon_threadsafe(self.lines.put_nowait, text)
            if len(buf) > 65536:  # satır sonu gelmeyen çöp veri
                buf = b""
        self._loop.call_soon_threadsafe(self._lost, ser)

    def _writer(self, ser: serial.Serial, outq: "queue.Queue[bytes]") -> None:
        while self.ser is ser:
            try:
                data = outq.get(timeout=0.2)
            except queue.Empty:
                continue
            try:
                if WINDOWS and len(data) > PACE_MIN:
                    self._write_paced(ser, data)
                else:
                    ser.write(data)
            except (serial.SerialException, serial.SerialTimeoutException, OSError, TypeError) as e:
                self._lost_reason = f"yazma: {e}"
                self._loop.call_soon_threadsafe(self._lost, ser)
                return

    def _write_paced(self, ser: serial.Serial, data: bytes) -> None:
        """Büyük ikili blokları (kapak, ikon) hattın ~%85'i hızında, 1 KB'lık parçalarla yazar.

        Windows'un USB-seri sürücüsü baytları boşluksuz, tam baud hızında basıyor; kart o sırada sayfa kuruyor ya da
        ekranı çiziyorsa UART tamponu taşıp birkaç bayt düşüyordu (CRC hatası, ör. 115183/115200 bayt). Linux'ta
        aynı kapak, paketler arasındaki doğal boşluklarla ≈1,5 sn'de gidiyor; burada da o hız taklit edilir.
        """
        period = PACE_CHUNK / (self.baud / 10 * PACE_RATIO)  # 921600 baud: ≈13 ms / 1 KB
        nxt = time.perf_counter()
        for i in range(0, len(data), PACE_CHUNK):
            if self.ser is not ser:
                return
            ser.write(data[i:i + PACE_CHUNK])
            nxt += period
            delay = nxt - time.perf_counter()
            if delay > 0:
                time.sleep(delay)

    def _lost(self, ser: serial.Serial) -> None:
        with self._lock:
            if self.ser is not ser:
                return
            self.ser = None
        try:
            ser.close()
        except Exception:
            pass
        reason, self._lost_reason = self._lost_reason, ""
        self.log(f"kart bağlantısı koptu ({reason or 'neden bilinmiyor'}), yeniden denenecek")

    def send(self, obj: dict, payload: bytes = b"") -> bool:
        """JSON satırını (ve varsa hemen ardından ikili veriyi) yazma kuyruğuna koyar; beklemez."""
        outq = self._outq
        if self.ser is None or outq is None:
            return False
        line = (json.dumps(obj, ensure_ascii=False, separators=(",", ":")) + "\n").encode()
        outq.put(line + payload)  # tek parça: araya başka mesaj giremez
        return True

    async def flush(self, timeout: float = 1.0) -> None:
        """Yazma kuyruğu boşalana kadar (en çok `timeout` sn) bekler."""
        end = time.monotonic() + timeout
        while self._outq is not None and not self._outq.empty() and time.monotonic() < end:
            await asyncio.sleep(0.02)
        await asyncio.sleep(0.05)  # son satırın kabloya çıkması için

    async def maintain(self) -> None:
        """Bağlantıyı açık tutar; kopunca RECONNECT_S arayla yeniden dener."""
        self._loop = asyncio.get_running_loop()
        warned = False
        while True:
            if self.ser is None:
                if self._open():
                    warned = False
                elif not warned and not self._busy_warned:
                    self.log("kart bulunamadı, bekleniyor…")
                    warned = True
            await asyncio.sleep(RECONNECT_S)

    def mark_rx(self) -> None:
        self.last_rx = time.monotonic()
