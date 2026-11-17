# Donanım

## Kart
- **Model:** Waveshare ESP32-S3-Touch-LCD-4.3. Satıcı sayfası (SAMM, ürün kodu MP03300) modeli
  yazıyla vermiyor; marka ve görsel adından çıkarıldı. Faz 0'da kartın üzerindeki yazıyla doğrulanacak.
- **İşlemci:** ESP32-S3 — çift çekirdek Xtensa LX7, 240 MHz, **16 MB flash** (sayfada 8 MB yazıyordu), 8 MB PSRAM (OPI)
- **Ekran:** 4.3", 800×480, 65K renk, RGB paralel arayüz (sürücü ST7262 — *doğrulanacak*)
- **Dokunmatik:** kapasitif, 5 nokta, I2C + kesme (denetleyici GT911, I2C `0x5D` — doğrulandı)
- **G/Ç genişletici:** CH422G (I2C) — dokunmatik reset, ekran reset, arka ışık, SD CS, USB/CAN seçimi
  bunun üzerinden yönetiliyor (*pin eşlemesi Faz 1'de doğrulanacak*)
- **Kablosuz:** 2.4 GHz Wi‑Fi b/g/n, Bluetooth 5 LE
- **USB:** 2 × Type-C
  - **USB-UART** (CH343P): programlama + seri bağlantı → **ilk tercihimiz**
  - **USB** (ESP32-S3'ün kendi USB'si, FSUSB42 ile çoklanıyor): HID/CDC için, Faz 7
- **Diğer:** microSD yuvası, CAN (TJA1051), RS485 (SP3485), I2C ve sensör konnektörü,
  3.7 V Li-ion/LiPo pil girişi (PH2.0, CS8501 şarj), BOOT ve RESET tuşları

## Dikkat edilecekler
- RGB ekran, görüntü belleğini PSRAM'de tutar; Wi‑Fi açıkken görüntü kayması olabilir →
  "bounce buffer" ayarı gerekebilir (Faz 1 / Faz 7).
- Kartın kendi USB girişi ile CAN aynı hatları paylaşıyor olabilir; CH422G üzerinden seçim
  yapılıyor (*doğrulanacak*).
- Arka ışık büyük ihtimalle sadece aç/kapa (PWM parlaklık yok) — *doğrulanacak*.

## Doğrulanan bilgiler
**2026-11-17 (esptool v5.6.0 + fabrika yazılımının seri çıktısı):**
- Çip: ESP32-S3 (QFN56) rev v0.2, 240 MHz, çift çekirdek, 40 MHz kristal
- **PSRAM: 8 MB gömülü (AP_3v3)** → PlatformIO'da OPI PSRAM olarak ayarlanacak
- **Flash: 16 MB** (üretici 0x46, cihaz 0x4018), quad, 3.3 V.
  ⚠️ Ürün sayfası "N8R8 / 8 MB" diyordu; gerçekte 16 MB. Bölüm tablosu 16 MB'a göre seçilecek.
- USB-UART köprüsü: WCH CH343, `1a86:55d3` "USB Single Serial" → Linux'ta `cdc_acm` sürücüsü,
  bu bilgisayarda **`/dev/ttyACM1`** (`/dev/ttyACM0` başka bir cihaz: Allwinner `1f3a:0008`, dokunma!)
- Otomatik reset/boot çalışıyor: esptool BOOT tuşuna basmadan bağlanıp RTS ile resetliyor.
- Seri konsol: 115200 baud. Fabrika yazılımı: LVGL demosu ("Display LVGL Scatter Chart"), Wi‑Fi testi
  (kayıtlı ağ yok → "WIFI is failure!"), ardından I2C taraması.
- I2C taraması: `0x5D` → **GT911 dokunmatik (doğrulandı)**; `0x20–0x27` ve `0x30–0x3F` → **CH422G**
  (bu çip birden çok adreste yanıt verir).

**Takma notu:** İlk denemede kart yanlış girişe takılıydı. USB tanıma yarıda kaldı: çekirdek logunda
sadece "new full-speed USB device" satırı çıktı. "USB-UART" girişine takınca hemen tanındı.

## Kaynaklar
- Waveshare wiki: ESP32-S3-Touch-LCD-4.3 sayfası (Faz 1'de bağlantı eklenecek)
- Espressif `ESP32_Display_Panel` kütüphanesi (bu kartı hazır destekliyor)
