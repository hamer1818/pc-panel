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

## 2026-11-17 · Kart yazılımı: PlatformIO + Arduino çatısı + ESP32_Display_Panel + LVGL 9
- Seçenekler: Arduino IDE · PlatformIO · saf ESP-IDF
- Neden: komut satırından derle/yükle (Claude doğrudan yapabilir), kart için hazır ekran sürücüsü,
  LVGL ile zengin arayüz. Performans yetmezse ESP-IDF'ye geçiş ayrıca değerlendirilir.

## 2026-11-17 · PlatformIO kendi venv'ine kuruldu (`~/.platformio/penv`)
- Seçenekler: pipx · pacman paketi (`platformio-core`) · ayrı venv
- Neden: sudo gerektirmez, PlatformIO'nun kendi standart yolu; pipx sistemde yoktu.

## 2026-11-17 · Bilgisayar servisi: Python
- Neden: psutil/NVML/D-Bus kütüphaneleri hazır; systemd kullanıcı servisi olarak kolay çalışır.
