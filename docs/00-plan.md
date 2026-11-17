# Ana Plan — adım adım

**[SEN]** = senin yapacağın iş · **[CLAUDE]** = benim yapacağım iş · **[BİRLİKTE]** = ikimiz

Her fazın sonunda: Claude `gunluk.md`'yi ve bu dosyadaki kutucukları günceller, sen onaylarsan commit atılır.

---

## Faz 0 — Hazırlık
Amaç: proje klasörü, araçlar ve kartın bilgisayarda görünmesi.

- [x] **[SEN]** Proje klasörünü seç → `/mnt/veri/yazilim/esp32-lcd-controller-card`
- [x] **[CLAUDE]** Klasöre bu dokümanları taşı, `git init` yap, `.gitignore` ekle.
- [x] **[SEN]** Seri port izni için `uucp` grubu → kullanıcı zaten bu grupta, gerek kalmadı.
- [ ] **[SEN]** Test için yardımcı araçları kur:
      ```bash
      sudo pacman -S --needed playerctl python-pipx
      ```
- [x] **[CLAUDE]** PlatformIO'yu kullanıcı alanına kur → `~/.platformio/penv` venv'ine kuruldu (6.2.0), `~/.local/bin/pio` bağlantısı.
- [x] **[SEN]** Kartı bilgisayara tak → ilk denemede yanlış giriş; "USB-UART" girişine takınca tanındı.
- [x] **[CLAUDE]** Kartın göründüğünü doğrula ve fabrika yazılımının seri çıktısını oku → `/dev/ttyACM1`,
      CH343; çip/flash/PSRAM esptool ile okundu (16 MB flash, 8 MB PSRAM). Ayrıntı: `01-donanim.md`.

**Bitti ölçütü:** `pio` komutu çalışıyor, kart `/dev/ttyACM0` gibi bir portta görünüyor.

---

## Faz 1 — Kartı ayağa kaldırma (ekran + dokunmatik)
Amaç: kendi yazılımımızla ekrana bir şey çizmek ve dokunmayı okumak.

- [x] **[CLAUDE]** Fabrika yazılımının yedeğini al → `yedek/fabrika-16MB.bin` (+ `.sha256`), geri yükleme komutu `01-donanim.md`'de.
- [x] **[CLAUDE]** `firmware/` altında PlatformIO projesi aç: ESP32-S3, 16 MB flash, 8 MB OPI PSRAM ayarları.
- [x] **[CLAUDE]** `ESP32_Display_Panel` v1.0.4 + LVGL **8.4** ekle (9 yerine; bkz. `kararlar.md`); hazır kart tanımı
      `BOARD_WAVESHARE_ESP32_S3_TOUCH_LCD_4_3`, yırtılma önleme modu 3.
- [x] **[CLAUDE]** Test ekranı: başlık/sürümler, renk çubukları, gri geçiş, kenar çerçevesi, dokunma imleci + koordinat,
      sayaçlı düğme, dönen yay, çalışma süresi, FPS/CPU göstergesi (`firmware/src/main.cpp`).
- [x] **[CLAUDE]** Derle ve karta yükle → başarılı, açılış logunda hata yok.
- [x] **[SEN]** Yükleme takılırsa BOOT tuşu → gerek kalmadı, otomatik yükleniyor.
- [x] **[SEN]** Ekranı kontrol et → "hepsi düzgün": renkler, gri geçiş, kenarlar, dokunmatik (köşeler dahil), düğme, akıcılık.
- [x] **[CLAUDE]** Sorun varsa ekran zamanlamalarını / dokunmatik eksenlerini düzelt → gerek kalmadı, varsayılan kart tanımı doğru.

**Bitti ölçütü:** ekran düzgün, dokunmatik doğru noktada, 5 dakika titremesiz çalışıyor.

---

## Faz 2 — Bilgisayar servisi (veri toplama)
Amaç: karta gönderilecek bütün bilgileri bilgisayarda doğru toplamak.

- [ ] **[CLAUDE]** `host/` altında Python projesi (venv): `psutil`, `pynvml`, `dbus-next`, `pyserial`, `pillow`.
- [ ] **[CLAUDE]** Sistem verileri: CPU yükü (toplam + çekirdek başına), CPU sıcaklığı (`k10temp`), RAM, disk doluluk + okuma/yazma, ağ indirme/yükleme hızı, çalışma süresi.
- [ ] **[CLAUDE]** GPU verileri (RTX 5080, NVML): yük, sıcaklık, VRAM, güç, fan.
- [ ] **[CLAUDE]** Medya (MPRIS / D-Bus): aktif çalar, şarkı, sanatçı, albüm, süre, konum, durum, kapak resmi adresi; çalar değişimini takip et.
- [ ] **[CLAUDE]** `--konsol` modu: karta göndermeden terminale canlı yazdırır.
- [ ] **[SEN]** Konsol modunu çalıştır; değerleri KDE Sistem İzleyicisi / `nvtop` ile karşılaştır.
- [ ] **[SEN]** Spotify, tarayıcıda YouTube ve bir yerel çalar (Elisa/VLC) ile şarkı bilgisinin geldiğini kontrol et.

**Bitti ölçütü:** konsolda bütün değerler doğru ve canlı, şarkı değişince bilgi güncelleniyor.

---

## Faz 3 — İletişim protokolü ve bağlantı
Amaç: bilgisayar ile kart arasında güvenilir iki yönlü bağlantı.

- [ ] **[CLAUDE]** Protokolü `02-mimari.md`'ye yaz (mesaj tipleri, alanlar, hızlar).
- [ ] **[CLAUDE]** Bilgisayar tarafı: seri porta yazma, karttan gelen komutları dinleme, kart çıkarılıp takılınca yeniden bağlanma.
- [ ] **[CLAUDE]** Kart tarafı: mesajları ayrıştırma (ArduinoJson), "bağlantı yok" durumu, kalp atışı (heartbeat).
- [ ] **[CLAUDE]** Geçici basit ekran: gelen değerleri düz yazı olarak göster, bir düğme ile oynat/durdur gönder.
- [ ] **[SEN]** Test: kabloyu çıkar-tak, servisi kapat-aç; ekran "bağlantı yok" deyip sonra kendini toparlıyor mu?

**Bitti ölçütü:** değerler karta akıyor, düğmeye basınca müzik duruyor/başlıyor, kopma sonrası kendiliğinden bağlanıyor.

---

## Faz 4 — Arayüz tasarımı
Amaç: panelin son görünümüne karar verip LVGL ile yapmak.

- [ ] **[SEN]** Ekranlarda ne görmek istediğine karar ver (liste aşağıda); öncelik sırası ver. Beğendiğin bir görünüm/renk/tema varsa referans görsel gönder.
- [ ] **[CLAUDE]** 800×480 ölçüsünde tıklanabilir bir tasarım taslağı (HTML) hazırla: Sistem sayfası, Medya sayfası, (Kısayollar sayfası).
- [ ] **[SEN]** Taslağı incele, değişiklik iste; **onay ver**.
- [ ] **[CLAUDE]** Onaylanan tasarımı LVGL'ye aktar: sayfalar arası kaydırma, göstergeler, son 60 saniyelik grafikler, yazı tipleri (Türkçe karakterli).
- [ ] **[SEN]** Gerçek ekranda okunabilirlik, düğme büyüklüğü, akıcılık kontrolü.

Karar verilecek içerik listesi:
- Sistem: CPU %, CPU °C, GPU %, GPU °C, VRAM, RAM, disk, ağ, saat/tarih, çalışma süresi
- Medya: kapak, şarkı/sanatçı, ilerleme çubuğu, ⏮ ⏯ ⏭, ses kaydırıcısı, sessiz
- Kısayollar (isteğe bağlı): uygulama aç, ekran kilitle, mikrofonu kapat, ekran görüntüsü

**Bitti ölçütü:** onaylı tasarım kart üzerinde akıcı çalışıyor.

---

## Faz 5 — Medya kontrolünü tamamlama
- [ ] **[CLAUDE]** Kapak resmini indir/oku → 200×200'e küçült → RGB565 olarak karta gönder; aynı kapağı tekrar gönderme.
- [ ] **[CLAUDE]** Sistem sesi (PipeWire, `wpctl`) okuma/ayarlama, sessiz; kaydırıcı ile çift yönlü eşleme.
- [ ] **[CLAUDE]** İlerleme çubuğuna dokunarak sarma (seek); birden çok çalar varsa seçim.
- [ ] **[SEN]** Farklı çalarlarla test, hataları bana bildir.

**Bitti ölçütü:** Spotify ve tarayıcıda bütün kontroller ve kapak çalışıyor.

---

## Faz 6 — Kalıcı kurulum (her açılışta kendiliğinden çalışsın)
- [ ] **[CLAUDE]** `deploy/99-pc-panel.rules`: kart her zaman `/dev/pcpanel` adıyla görünsün.
- [ ] **[CLAUDE]** `deploy/pc-panel.service`: systemd kullanıcı servisi; `deploy/kur.sh` kurulum betiği.
- [ ] **[SEN]** udev kuralını kur (sudo gerekir):
      ```bash
      sudo cp deploy/99-pc-panel.rules /etc/udev/rules.d/ && sudo udevadm control --reload && sudo udevadm trigger
      ```
- [ ] **[SEN]** Servisi aç: `systemctl --user enable --now pc-panel`
- [ ] **[CLAUDE]** Ekran davranışı: bilgisayar kilitlenince/uykuya geçince ekranı karart, açılınca geri getir.
- [ ] **[SEN]** Bilgisayarı yeniden başlat; panel kendiliğinden geliyor mu?

**Bitti ölçütü:** yeniden başlatma sonrası hiçbir şeye dokunmadan panel çalışıyor.

---

## Faz 7 — İsteğe bağlı geliştirmeler (sonra karar verilecek)
- [ ] Wi‑Fi + WebSocket ile kablosuz çalışma (pil konnektörü de var)
- [ ] Kartın kendi USB girişinden HID medya tuşları (servis kapalıyken de ⏯ çalışsın)
- [ ] Kısayol sayfası / makro düğmeleri
- [ ] Kablosuz yazılım güncelleme (OTA)
- [ ] **[SEN]** Stand / kasa (3D baskı ya da hazır stand)

---

## İlerleme özeti
| Faz | Durum |
|-----|-------|
| 0 Hazırlık | ✅ bitti (2026-11-17) |
| 1 Ekran + dokunmatik | ✅ bitti (2026-11-17) |
| 2 PC servisi | ⏳ sıradaki |
| 3 Protokol | — |
| 4 Arayüz | — |
| 5 Medya | — |
| 6 Kalıcı kurulum | — |
| 7 Ekstralar | — |
