# Geliştirme Günlüğü

En yeni kayıt en üstte.

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
