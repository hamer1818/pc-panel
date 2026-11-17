# Geliştirme Günlüğü

En yeni kayıt en üstte.

## 2026-11-17 — Faz 4: tasarım onaylandı, LVGL'ye aktarıldı (yazı tipleri bekliyor)
- Kullanıcı taslak v1'i olduğu gibi onayladı.
- Yoklama: node 26 / npm var. Varsayılan tarayıcı Zen (`userapp-Zen-83YBT3.desktop`); konsole, dolphin, spectacle,
  spotify, kstart, wpctl kurulu. Sistem sesi %95, mikrofon %100.
- `npx --yes lv_font_conv` çalıştırılamadı: otomatik npm paket kurulumu güvenlik kuralına takıldı.
  → Kullanıcıdan kurulum onayı istenecek. Betik `tools/node` altına yerel kurulum bekliyor (git dışı).
- Kaynak yazı tipleri LVGL deposundan `firmware/fonts/kaynak/` klasörüne kopyalandı: Montserrat-Medium (OFL),
  FontAwesome 5 (Free). Taslaktaki kalın Montserrat yerine tek ağırlık (Medium) kullanılacak.
- Bilgisayar: `audio.py` (wpctl get/set, sessiz/mikrofon aç-kapa), `shortcuts.py` (sabit kimlik → komut listesi;
  karttan serbest komut çalıştırılamaz), protokol v1.1 (`docs/02-mimari.md`).
- Kart: `ui.cpp` baştan yazıldı (Sistem / Medya / Kısayollar, tileview), `ui_fonts.h` (Türkçe yazı tipi yoksa
  hazır Montserrat'a düşer), yazılım 0.4.0. Yedek yazı tipiyle hatasız derlendi: RAM %7,7, flash %13,9.
  Karta henüz yüklenmedi: Türkçe yazı tipi olmadan sabit etiketlerde (Sıcaklık, yük…) harf eksik çıkar.
- **Sıradaki:** lv_font_conv kurulumu → yazı tiplerini üret → derle, yükle, dene.

## 2026-11-17 — Faz 4: tercihler ve tasarım taslağı v1
- Kullanıcı tercihleri alındı (`kararlar.md`): Sistem sayfasında her şey; kaydırmalı sayfalar; koyu, sade tema;
  Kısayollar sayfası olacak.
- Taslak `docs/tasarim/taslak-v1.html` hazırlandı (tek dosya, Montserrat, yalnızca LVGL'de yapılabilecek öğeler).
  - **Sistem:** CPU ve GPU için yay gösterge, sıcaklık, frekans/güç/fan ve 60 sn çizgi grafik. Altta 4 küçük kart:
    RAM, VRAM, Diskler (iki çubuk + okuma/yazma), Ağ (+ PC açık kalma süresi).
  - **Medya:** 240×240 kapak alanı, çalar etiketi, başlık/sanatçı/albüm, dokunarak sarılabilen ilerleme çubuğu,
    −10 / ⏮ / ⏯ / ⏭ / +10 ve ses kaydırıcısı (sessiz düğmesiyle).
  - **Kısayollar:** 4×2 kutu: kilitle, mikrofon (aç/kapa), ekran görüntüsü, ses (aç/kapa), Terminal, Tarayıcı,
    Dosyalar, Spotify. Liste örnek; kesin listeyi kullanıcı belirleyecek.
  - Renk kuralı: tek vurgu rengi mavi `#3aa0ff`. Yalnızca uyarıda renk değişiyor: %60 / 65 °C üstü sarı,
    %85 / 80 °C üstü kırmızı.
- Tarayıcıda üç sayfa kontrol edildi. Disk okuma/yazma satırı taşıyordu, tek satıra alındı.
- Önizleme: `docs/tasarim` klasörü `python3 -m http.server 8765` ile sunuluyor (`.claude/launch.json` → "tasarim").
- **Sıradaki:** kullanıcı taslağı inceleyip değişiklik isteyecek ya da onay verecek.

## 2026-11-17 — Faz 3: protokol ve iki yönlü bağlantı
- Faz 2 commit'lendi (`b264911`).
- Reset deneyi: pyserial varsayılan (DTR/RTS açık) ile açınca kart resetlenmiyor, ikisi kapalıyken resetleniyor
  → varsayılan kullanılıyor (bkz. `kararlar.md`).
- Protokol v1 yazıldı (`02-mimari.md`): 921600 baud, satır başına JSON; `stat` ve `media` mesajları bilgisayardan
  karta, `hello`, `hb` ve `cmd` karttan bilgisayara.
- Bilgisayar: `protocol.py`, `link.py` eklendi; varsayılan mod artık servis. `pyserial` 3.5 eklendi.
- Kart: yazılım 0.3.0; ArduinoJson 7.4.3; `ui.cpp` geçici ekranı; seri RX tamponu 16 KB. Derleme RAM %7,6,
  flash %12,5.
- Uçtan uca deneme (`--debug`, 15 sn): kart günlükleri, `hello`, kalp atışı ve 1 sn'lik `stat`/`media` akışı
  sorunsuz. Kullanıcı deneme sırasında karttaki ⏭ düğmesine bastı → `karttan komut: next → tamam`,
  Spotify sonraki şarkıya geçti, ekran hemen güncellendi.
- **Hata ve düzeltme:** Claude servisi arka planda çalıştırıyordu. Kullanıcı da kendi terminalinden ikinci bir
  kopya açınca iki süreç aynı portu okudu ve 1–5 sn arayla sürekli "bağlantı koptu / bağlandı" oldu (iki logda da
  aynı saatlerde). pyserial iki okuyucu olunca `SerialException` veriyor. Çözüm: `link.py` portu `exclusive=True`
  ile açıyor (TIOCEXCL + flock). İkinci kopya artık bir kez "port başka bir program tarafından kullanılıyor"
  yazıp bekliyor. Deneyle doğrulandı: ilk kopya 12 sn kopmadan bağlı kaldı.
  Not: `pio device monitor` açıkken servis bağlanamaz (ve tersi). Bu artık beklenen davranış.
- Claude'un arka plandaki servisi durduruldu. Servisi bundan sonra kullanıcı kendi terminalinde çalıştırıyor
  (Claude Code terminal panelindeki sekmeye komut yazılamadı).
- Kullanıcı testi (servis kendi terminalinde, 16:02): tek kopya, kopma yok. Karttaki düğmelerin hepsi çalıştı:
  play_pause ×2, next ×2, prev, seek_rel +10, seek_rel −10 → hepsi "tamam". Servisi Ctrl+C ile kapatıp açma da sorunsuz.
- Kablo çıkar-tak testi: kullanıcı yaptı ve sorun bildirmedi. O testin logu paylaşılmadı.
- **Faz 3 tamamlandı.** Sıradaki: Faz 4 — arayüz tasarımı; önce kullanıcının tercihleri alınacak.

## 2026-11-17 — Faz 2: bilgisayar servisi (veri toplama)
- Faz 1 commit'lendi (`962731b`).
- Yoklama: `k10temp` (Tctl, Tccd1), 2× NVMe sıcaklığı, RAM (spd5118) sıcaklığı mevcut; psutil fan bulamıyor.
  Diskler: `/` = nvme1n1p2 (btrfs, 1 TB), `/mnt/veri` = nvme0n1p2 (btrfs, 460 GB). Ağ: wlan0 (etkin),
  enp7s0, tailscale0, virbr0. NVIDIA sürücü 620.70.06. MPRIS'te açık çalar: Spotify.
- `host/` kuruldu (`uv sync`, Python 3.12.10): psutil 7.2.2, nvidia-ml-py 13.615.71, dbus-fast 5.2.0.
- Toplayıcılar yazıldı ve tek tek denendi. Hepsi doğru değer veriyor; Spotify'da Türkçe karakterli şarkı
  bilgisi, konum, süre ve kapak adresi okunuyor.
- Konsol, `--json` ve `--once` modları denendi. `--komut` (oynat/durdur vb.) yazıldı ama Claude denemedi:
  kullanıcının müziğini durdurmamak için bu testi kullanıcı yapacak.
- Kullanıcı testi: **hepsi doğru** — değerler KDE Sistem İzleyicisi / nvtop ile uyumlu; Spotify, YouTube ve yerel
  çalarda şarkı bilgisi geliyor; `--komut` ile oynat/durdur, ileri, sarma çalışıyor.
- **Faz 2 tamamlandı.**

## 2026-11-17 — Faz 1: ilk kendi yazılımımız karta yüklendi
- Faz 0 commit'lendi (`cbdcc48`).
- Fabrika yazılımı yedeklendi: 16 MB, 203 sn, 921600 baud → `yedek/fabrika-16MB.bin` (ilk bayt 0xE9, geçerli imaj).
- Kütüphane araştırması: ESP32_Display_Panel v1.0.4 (en son) yalnızca LVGL v8 portu ve PlatformIO örneği içeriyor
  → LVGL 8.4 seçildi. Örneğin test edilmiş sürüm seti (pioarduino 53.03.11 / Arduino 3.1.1-h) sabitlendi.
- `firmware/` oluşturuldu: örnekten `lvgl_v8_port.*`, `lv_conf.h`, `esp_*_conf.h` alındı; kart dosyası
  `boards/waveshare_esp32s3_touch_lcd_43.json`; yırtılma önleme modu 3; test ekranı `src/main.cpp`.
- İlk derleme 96 sn (platform indirmeleri dahil). RAM %6,9, flash %11,7 (6,5 MB uygulama bölümünden).
- Yükleme 18 sn, BOOT tuşuna gerek yok. Açılış logu temiz; GT911 adres uyarısı zararsız (bkz. `01-donanim.md`).
- Kullanıcı kontrolü: **hepsi düzgün** — renk sırası doğru (R/B karışıklığı yok), gri geçiş, dört kenar,
  dokunmatik eksenleri ve köşeler, düğme sayacı, dönen yay akıcı. Ekran ayarlarında değişiklik gerekmedi.
- **Faz 1 tamamlandı.** Sıradaki: Faz 2 — bilgisayar servisi (`host/`, sistem + GPU + MPRIS verileri, konsol modu).

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
