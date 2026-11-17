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

- [x] **[CLAUDE]** `host/` altında Python projesi (`uv`, `.venv`, Python 3.12): `psutil`, `nvidia-ml-py`, `dbus-fast`.
      (`pyserial` Faz 3'te, `pillow` Faz 5'te eklenecek.)
- [x] **[CLAUDE]** Sistem verileri (`pc_panel/system.py`): CPU toplam + 16 iş parçacığı, MHz, `k10temp` Tctl, RAM, swap,
      `/` ve `/mnt/veri` doluluk, fiziksel NVMe okuma/yazma hızı, fiziksel ağ arayüzleri hızı, çalışma süresi, yük.
- [x] **[CLAUDE]** GPU verileri (`pc_panel/gpu.py`, NVML): yük, bellek yükü, sıcaklık, VRAM, güç / sınır, fan, saat.
- [x] **[CLAUDE]** Medya (`pc_panel/media.py`, MPRIS): etkin çalar seçimi, şarkı, sanatçı, albüm, süre, konum, ses,
      kapak adresi, yetenekler; kontrol komutları (oynat/durdur, ileri, geri, sarma) hazır.
- [x] **[CLAUDE]** Konsol modu (`uv run pc-panel --konsol`) + `--json`, `--once`, `--komut`. Claude kendi denedi: Spotify ile çalışıyor.
- [x] **[SEN]** Konsol modunu çalıştır; değerleri KDE Sistem İzleyicisi / `nvtop` ile karşılaştır → doğru.
- [x] **[SEN]** Spotify, tarayıcıda YouTube ve bir yerel çalar (Elisa/VLC) ile şarkı bilgisinin geldiğini kontrol et → doğru.
- [x] **[SEN]** Kontrol komutlarını dene: `uv run pc-panel --komut play_pause`, `--komut next`, `--komut seek_rel:30` → çalışıyor.

**Bitti ölçütü:** konsolda bütün değerler doğru ve canlı, şarkı değişince bilgi güncelleniyor.

---

## Faz 3 — İletişim protokolü ve bağlantı
Amaç: bilgisayar ile kart arasında güvenilir iki yönlü bağlantı.

- [x] **[CLAUDE]** Protokolü `02-mimari.md`'ye yaz → protokol v1, 921600 baud, satır başına bir JSON.
- [x] **[CLAUDE]** Bilgisayar tarafı (`pc_panel/link.py`, `protocol.py`, servis modu): seri porta yazma, komut dinleme,
      2 sn arayla yeniden bağlanma; `uv run pc-panel` (+ `--debug`).
- [x] **[CLAUDE]** Kart tarafı (`firmware/src/main.cpp`): ArduinoJson 7.4.3 ile ayrıştırma, `hello` + 1 sn kalp atışı,
      3 sn mesaj gelmezse "NO LINK".
- [x] **[CLAUDE]** Geçici ekran (`firmware/src/ui.cpp`): sistem değerleri çubuklarla, medya bilgisi, ⏮ ⏯ ⏭ ve ±10 sn düğmeleri.
      Türkçe harfler geçici olarak ASCII'ye çevriliyor (yazı tipi Faz 4'te).
- [x] **[CLAUDE]** Uçtan uca deneme: `hello`, kalp atışı, `stat`/`media` akışı çalışıyor; karttan `next` komutu Spotify'da uygulandı.
- [x] **[SEN]** Test: servisi kapat-aç → çalışıyor.
- [x] **[SEN]** Test: kabloyu çıkar-tak → kullanıcı yaptı, sorun bildirmedi.
- [x] **[SEN]** Karttaki bütün düğmeleri dene: ⏮ ⏯ ⏭, −10 sn, +10 sn → hepsi "tamam" (log 16:02:49–16:02:56).

**Bitti ölçütü:** değerler karta akıyor, düğmeye basınca müzik duruyor/başlıyor, kopma sonrası kendiliğinden bağlanıyor.

---

## Faz 4 — Arayüz tasarımı
Amaç: panelin son görünümüne karar verip LVGL ile yapmak.

- [x] **[SEN]** Ekranlarda ne görmek istediğine karar ver → hepsi; kaydırmalı sayfalar; koyu, sade tema;
      Kısayollar sayfası olacak (ayrıntı: `kararlar.md`).
- [x] **[CLAUDE]** 800×480 ölçüsünde tıklanabilir bir tasarım taslağı (HTML) hazırla → `docs/tasarim/taslak-v1.html`
      (Sistem, Medya, Kısayollar; sürükleyerek / ← → ile sayfa değişimi; örnek canlı veri).
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
| 2 PC servisi | ✅ bitti (2026-11-17) |
| 3 Protokol | ✅ bitti (2026-11-17) |
| 4 Arayüz | ⏳ sıradaki — kullanıcının içerik/tema tercihleri bekleniyor |
| 5 Medya | — |
| 6 Kalıcı kurulum | — |
| 7 Ekstralar | — |
