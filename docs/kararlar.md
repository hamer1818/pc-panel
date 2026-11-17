# Kararlar

Her karar: tarih · karar · düşünülen seçenekler · neden.

## 2026-11-17 · Faz 4 arayüz tercihleri (kullanıcı seçti)
- **İçerik (Sistem sayfası):** hepsi. CPU ve GPU yükü ile sıcaklığı; RAM ve VRAM; diskler ve ağ hızı;
  son 60 sn grafikleri.
- **Düzen:** kaydırmalı sayfalar. Sistem, Medya ve Kısayollar ayrı tam ekran sayfalar, sola/sağa kaydırılarak geçiliyor.
  - Diğer seçenekler: tek ekran ikiye bölünmüş · özet ekranı ve ayrıntı sayfaları.
- **Tema:** koyu, sade. Siyaha yakın zemin, tek vurgu rengi, süs yok.
  - Diğer seçenekler: koyu "oyuncu" (neon) · aydınlık.
- **Kısayollar sayfası:** olacak (Faz 7'ye bırakılmadı).

## 2026-11-17 · Kapak resmi: aynı seri hatta ikili blok, 240×240 RGB565, CRC-32
- Seçenekler: base64 JSON içinde (≈%33 büyür, ayrıştırması pahalı) · ikili blok · JPEG gönderip kartta açmak
  (TJpgDec; daha az veri ama ek kütüphane ve işlemci yükü)
- Neden: ikili blok en basit ve hızlısı. 115 KB, 921600 baud'da ≈1,3 sn sürüyor; şarkı başına bir kez
  gönderildiği için yeterli. CRC ve zaman aşımı, kayan baytlara karşı protokolü kendiliğinden toparlıyor.
  Kartta iki PSRAM tamponu kullanılıyor (230 KB / 8 MB); yeni kapak tamamen gelince yer değiştiriyor.
- Kapak 240×240: tasarımdaki kapak alanıyla birebir, kartta ölçekleme gerekmiyor.

## 2026-11-17 · Giden mesajlar tek bir yazma iş parçacığından
- Neden: 115 KB'lık yazma asyncio döngüsünü ≈1,3 sn bekletiyordu ve ortasına başka bir satır karışabilirdi.
  Kuyruk + tek yazıcı ile ikisi de çözüldü; `send()` artık beklemiyor.

## 2026-11-17 · Sistem sesi ve kısayollar Faz 5 yerine Faz 4'te
- Neden: onaylanan tasarımda ses kaydırıcısı ve kısayol kutuları var. Çalışmayan düğme bırakmak test etmeyi
  zorlaştırırdı, iş de küçük (`wpctl` + sabit komut listesi). Faz 5'te yalnızca kapak resmi kaldı.

## 2026-11-17 · Kısayollar: kart yalnızca kimlik gönderir, komutlar bilgisayarda sabit listede
- Neden: seri port üzerinden gelen veriyle komut satırı kurmak tehlikeli olurdu. `shortcuts.py` dışındaki hiçbir
  kimlik çalıştırılmaz. Uygulamalar `kstart --application <masaüstü-kimliği>` ile açılıyor; pencere zaten açıksa
  öne geliyor.

## 2026-11-17 · Yazı tipleri: Montserrat Medium + Font Awesome 5, lv_font_conv ile üretim
- Seçenekler: LVGL'nin hazır yazı tipleri (Türkçe yok) · lv_font_conv · çevrimiçi LVGL font dönüştürücü (elle)
- Neden: komut satırından tekrarlanabilir üretim (`tools/fontlari_uret.sh`), Türkçe + Latin-1 + Latin Ext-A
  aralığı (yabancı şarkı adları için de), 4 bpp. Taslaktaki kalın ağırlık yok, LVGL deposunda yalnızca Medium var.

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

## 2026-11-17 · Seri port açılırken DTR/RTS açık bırakılır (kart resetlenmesin)
- Deney: pyserial varsayılanı (DTR=RTS=açık) ile port açılınca kart **resetlenmedi**; ikisi kapatılınca **resetlendi**.
- Karar: `link.py` portu varsayılan ayarlarla açar. Kartı bilerek resetlemek gerekirse RTS kısa süre kapatılıp açılır.

## 2026-11-17 · Seri port özel (exclusive) modda açılır
- Sorun: aynı anda iki servis kopyası çalışınca ikisi de portu okudu ve bağlantı her birkaç saniyede koptu.
- Seçenekler: port kilidi (`exclusive=True`) · ayrı bir "tek kopya" kilit dosyası · ikisi birden
- Neden: port kilidi seri monitör gibi başka programlara karşı da korur ve ek dosya gerektirmez.

## 2026-11-17 · Bağlantı hızı 921600 baud, kart günlükleri aynı hattan
- Neden: `stat`/`media` için 115200 bile yeterli, ama Faz 5'teki 80 KB'lık kapak resmi 921600'de ≈1 sn sürer.
  Kütüphane günlükleri de aynı UART'tan geliyor; `{` ile başlamayan satırlar günlük sayılıyor, ayrı kanal gerekmedi.

## 2026-11-17 · Kartın kendi mesajları elle `printf` ile, gelenler ArduinoJson 7 ile
- Neden: giden mesajlar küçük ve sabit biçimli, tek `printf` = tek yazma, satırlar karışmıyor; gelenler değişken.

## 2026-11-17 · Türkçe harfler Faz 4'e kadar ASCII'ye çevrilir
- Neden: LVGL'nin hazır Montserrat yazı tiplerinde ç/ğ/ı/ö/ş/ü yok. Faz 4'te Türkçe glifli yazı tipi üretilecek;
  `ui.cpp` içindeki `translit` o zaman kaldırılacak.

## 2026-11-17 · D-Bus kütüphanesi: dbus-fast (dbus-next yerine)
- Seçenekler: dbus-next · dbus-fast · dbus-python (C, sistem paketi)
- Neden: dbus-next 2021'den beri güncellenmiyor; dbus-fast onun bakımı süren, aynı API'li devamı, saf Python
  olarak da çalışıyor. dbus-python sanal ortama kurulması zahmetli.

## 2026-11-17 · MPRIS için yoklama (polling), sinyal değil
- Seçenekler: her sn `GetAll` ile yoklama · `PropertiesChanged` sinyallerini dinleme
- Neden: yoklama daha basit ve sağlam. Konum (`Position`) zaten sinyal üretmiyor, onun için yoklama şart.
  1 sn gecikme panel için yeterli. Şarkı değişimi çok geç gelirse sinyal dinleme sonradan eklenir.

## 2026-11-17 · Python ortamı `uv` ile yönetilir (`host/.venv`)
- Neden: sistemde kurulu, hızlı, `pyproject.toml` + kilit dosyası (`uv.lock`) ile tekrarlanabilir kurulum.

## 2026-11-17 · Bilgisayar servisi: Python
- Neden: psutil/NVML/D-Bus kütüphaneleri hazır; systemd kullanıcı servisi olarak kolay çalışır.
