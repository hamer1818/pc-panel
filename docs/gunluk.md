# Geliştirme Günlüğü

En yeni kayıt en üstte.

## 2026-11-17 — Faz 0 tamamlandı: kart tanındı
- Kullanıcı kartı yeniden taktı → CH343 `1a86:55d3` olarak tanındı, `/dev/ttyACM1` oluştu.
  (`/dev/ttyACM0` = başka cihaz, Allwinner; karıştırma.)
- Fabrika yazılımının açılış logu okundu: LVGL demosu, Wi‑Fi testi başarısız (beklenen), I2C taraması
  → GT911 `0x5D` ve CH422G doğrulandı.
- `esptool` (v5.6.0) PlatformIO venv'ine kuruldu; `flash-id` ile okundu: **16 MB flash** (sayfa 8 MB diyordu),
  8 MB gömülü PSRAM, rev v0.2. Otomatik boot/reset çalışıyor, BOOT tuşuna gerek yok.
- Seri okuma için geçici betik kullanıldı (DTR/RTS reset + 8 sn okuma). Faz 1'de `pio device monitor` kullanılacak.
- **Sıradaki:** Faz 1 — `firmware/` PlatformIO projesi, ESP32_Display_Panel + LVGL test ekranı.

## 2026-11-17 — Faz 0: araçlar ve ilk bağlantı
- Proje klasörü: `/mnt/veri/yazilim/esp32-lcd-controller-card`. Dokümanlar taşındı, `git init` yapıldı.
- Kullanıcı zaten `uucp` grubunda → seri port izni hazır.
- PlatformIO 6.2.0 kuruldu: `python3 -m venv ~/.platformio/penv` + `pip install platformio`,
  `~/.local/bin/pio` sembolik bağlantısı (pipx kurulu olmadığı için bu yol seçildi).
- Kart USB 3.0 porta A→C kabloyla takıldı, ekran açıldı (fabrika yazılımı çalışıyor).
- **Sorun:** çekirdek logunda yalnızca `usb 6-7: new full-speed USB device number 15` satırı var,
  ardından hiçbir mesaj yok; `lsusb`'de kart görünmüyor, `/dev/ttyACM*` oluşmadı → USB tanıma yarıda kalıyor.
  Olası nedenler: (1) sadece şarj taşıyan / zayıf kablo, (2) kart "USB" (yerel) girişine takılı ve fabrika
  yazılımı bu hatları CAN'a yönlendirmiş olabilir, (3) port sorunu.
- **Sonuç:** kullanıcı kartı yeniden taktı, tanındı (bir üstteki kayıt).

## 2026-11-17 — Proje başlangıcı
- Kartın modeli belirlendi: Waveshare ESP32-S3-Touch-LCD-4.3 (SAMM ürün sayfasından).
- Bilgisayar incelendi: CachyOS + KDE, Ryzen 7 9800X3D, RTX 5080, PipeWire; `psutil` ve
  `nvidia-smi` mevcut. PlatformIO ve `playerctl` kurulu değil. Kart henüz takılı değil.
- Mimari ve ilk kararlar yazıldı (`02-mimari.md`, `kararlar.md`).
- Ana plan çıkarıldı (`00-plan.md`), 8 faz.
- **Sıradaki:** Faz 0 — proje klasörü seçimi, araç kurulumu, kartın takılması.
