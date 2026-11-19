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

**2026-11-17 (kendi yazılımımızla ilk açılış):**
- ESP32_Display_Panel kart tanımı `BOARD_WAVESHARE_ESP32_S3_TOUCH_LCD_4_3` sorunsuz çalıştı (4.3 ve 4.3B
  tanımları kütüphanede isim dışında birebir aynı). Ekran: ST7262, RGB565 16 bit, 16 MHz PCLK.
- Pinler (kütüphanedeki tanımdan): RGB HSYNC 46, VSYNC 3, DE 5, PCLK 7; veri 14,38,18,17,10,39,0,45,48,47,21,1,2,42,41,40.
  I2C SDA 8 / SCL 9 (dokunmatik + CH422G ortak), dokunmatik INT 4. Arka ışık CH422G EXIO2 (sadece aç/kapa).
- GT911 açılışta `Unable to initialize the I2C address` uyarısı veriyor ama TouchPad_ID "911", config v67 okunuyor
  → zararsız (reset pini CH422G üzerinden olduğu için adres seçimi yapılamıyor, varsayılan 0x5D kullanılıyor).
- Yırtılma önleme modu 3 açıkken boş bellek: PSRAM ≈ 5981 KB, dahili SRAM ≈ 277 KB.

**Fabrika yazılımına geri dönmek için** (yedek: `yedek/fabrika-16MB.bin`, git dışı):
```bash
~/.platformio/penv/bin/esptool --port /dev/serial/by-id/usb-1a86_USB_Single_Serial_<seri>-if00 -b 921600 write-flash 0 yedek/fabrika-16MB.bin
```

**Takma notu:** İlk denemede kart yanlış girişe takılıydı. USB tanıma yarıda kaldı: çekirdek logunda
sadece "new full-speed USB device" satırı çıktı. "USB-UART" girişine takınca hemen tanındı.

**2026-11-20 (Windows 11, aynı bilgisayar):**
- Kart Windows'un kendi CDC sürücüsüyle ("USB Seri Cihaz", usbser) **COM4** olarak görünüyor, `1A86:55D3`,
  seri no Linux'takiyle aynı. WCH sürücüsü kurmak gerekmedi. COM3 = Allwinner `1F3A:0008` (Linux'taki
  `/dev/ttyACM0`), dokunma. Servis portu VID:PID ile kendisi bulur.
- Windows'ta port açılınca kart çoğu zaman yeniden başlıyor (otomatik reset devresi, DTR/RTS). Zararsız: kart
  "merhaba" deyince servis her şeyi yeniden gönderir.
- **Windows'un USB-seri sürücüsü baytları boşluksuz basıyor**: 115 KB ≈1,27 sn (Linux ≈1,5 sn). Kart o sırada
  meşgulse UART tamponu taşıp birkaç bayt düşüyordu (ör. `115183 / 115200`). Servis Windows'ta ikili blokları
  hattın %85'i hızında gönderiyor (bkz. `kararlar.md` 2026-11-20). Elektriksel bir sorun değil.
- NVML (RTX 5080) Windows sürücüsüyle de çalışıyor: yük, sıcaklık, VRAM, güç, fan, saat.

### Windows'ta CPU sıcaklığı
Windows, Ryzen sıcaklığını sürücüsüz vermiyor. Servis, **LibreHardwareMonitor** açıksa onun WMI sağlayıcısından
(`root\LibreHardwareMonitor`, "Core (Tctl/Tdie)") okur; kapalıysa kartta CPU sıcaklığı "-" görünür, gerisi çalışır.
Kurulum ve her açılışta başlatma: plandaki Faz 8 [SEN] adımı.

## Kaynaklar
- Waveshare wiki: ESP32-S3-Touch-LCD-4.3 sayfası (Faz 1'de bağlantı eklenecek)
- Espressif `ESP32_Display_Panel` kütüphanesi (bu kartı hazır destekliyor)
