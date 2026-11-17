# Kararlar

Her karar: tarih · karar · düşünülen seçenekler · neden.

## 2026-11-17 · Bağlantı ilk aşamada USB seri (CH343) üzerinden
- Seçenekler: USB seri · kartın kendi USB'si (CDC/HID) · Wi‑Fi/WebSocket
- Neden: hem programlama hem veri tek kabloyla; sürücü gerektirmez; en kolay hata ayıklama.
  Wi‑Fi ve HID Faz 7'ye bırakıldı.

## 2026-11-17 · Medya bilgisi MPRIS (D-Bus) ile alınır
- Seçenekler: MPRIS · klavye medya tuşu taklidi (HID)
- Neden: KDE'deki bütün çalarlar MPRIS destekler; şarkı adı, kapak, konum alınabilir.
  HID sadece tuş gönderebilir, bilgi alamaz.

## 2026-11-17 · LVGL 9 yerine LVGL 8.4.0 (önceki kararı değiştirir)
- Seçenekler: LVGL 8.4 + kütüphanenin hazır `lvgl_v8_port`u · LVGL 9 + kendi yazacağımız port
- Neden: ESP32_Display_Panel v1.0.4 sadece LVGL v8 için port ve PlatformIO örneği veriyor. Bu port,
  RGB ekranda yırtılma önleme (çift tampon + direct-mode) ve döndürme desteğini hazır sunuyor.
  LVGL 9'a geçiş ileride gerekirse ayrı bir iş olarak ele alınır.

## 2026-11-17 · Sürüm seti: kütüphane örneğinin test edilmiş kombinasyonu
- Platform `pioarduino/platform-espressif32` 53.03.11 + arduino-esp32 **3.1.1** + `esp32-3.1.1-h`
  (yüksek performans) kütüphaneleri; ESP32_Display_Panel **v1.0.4**, ESP32_IO_Expander **v1.1.1**,
  esp-lib-utils **v0.2.3**, LVGL **v8.4.0** — hepsi `platformio.ini` içinde sabitlendi.
- Neden: resmî `espressif32` platformu Arduino 3.x'i desteklemiyor; daha yeni pioarduino sürümleri
  (55.x, Arduino 3.3) bu kütüphaneyle denenmedi. Önce çalışan bilinen seti kullanıp sonra yükseltmek daha güvenli.
  Bağımlılık aralığı: Display_Panel v1.0.4 → IO_Expander ≥1.0 <2.0, esp-lib-utils ≥0.2 <0.3.

## 2026-11-17 · Yırtılma önleme modu 3 (LCD çift tampon + LVGL direct-mode)
- Seçenekler: 0 kapalı · 1 çift tampon + full-refresh · 2 üçlü tampon + full-refresh · 3 çift tampon + direct-mode
- Neden: kütüphanenin RGB ekranlar için önerdiği mod. 2 × 800×480×2 B ≈ 1,5 MB PSRAM kullanır (8 MB'tan).

## 2026-11-17 · Seri port kalıcı yolla seçilir
- `/dev/serial/by-id/usb-1a86_USB_Single_Serial_5B90123287-if00` (platformio.ini'de `upload_port`/`monitor_port`)
- Neden: `ttyACM` numaraları takma sırasına göre değişiyor ve `/dev/ttyACM0` başka bir cihaz.

## 2026-11-17 · Kart yazılımı: PlatformIO + Arduino çatısı + ESP32_Display_Panel + LVGL 9 *(LVGL kısmı yukarıda 8.4 olarak değişti)*
- Seçenekler: Arduino IDE · PlatformIO · saf ESP-IDF
- Neden: komut satırından derle/yükle (Claude doğrudan yapabilir), kart için hazır ekran sürücüsü,
  LVGL ile zengin arayüz. Performans yetmezse ESP-IDF'ye geçiş ayrıca değerlendirilir.

## 2026-11-17 · PlatformIO kendi venv'ine kuruldu (`~/.platformio/penv`)
- Seçenekler: pipx · pacman paketi (`platformio-core`) · ayrı venv
- Neden: sudo gerektirmez, PlatformIO'nun kendi standart yolu; pipx sistemde yoktu.

## 2026-11-17 · Bilgisayar servisi: Python
- Neden: psutil/NVML/D-Bus kütüphaneleri hazır; systemd kullanıcı servisi olarak kolay çalışır.
