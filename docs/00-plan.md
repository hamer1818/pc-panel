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
- [x] **[SEN]** Taslağı incele, değişiklik iste; **onay ver** → taslak v1 olduğu gibi onaylandı.
- [x] **[CLAUDE]** Onaylanan tasarımı LVGL'ye aktar (`firmware/src/ui.cpp`, yazılım 0.4.0): tileview ile 3 sayfa,
      yay göstergeler, 60 sn grafikler, ilerleme ve ses kaydırıcıları, 8 kısayol kutusu, bildirim balonu.
      Yedek yazı tipiyle hatasız derlendi.
- [x] **[CLAUDE]** Protokol v1.1 + bilgisayar tarafı: saat/tarih, `cpu_max`, `gpu_fan`, `swap`, `vol` mesajı;
      `vol_set` ve `shortcut` komutları (`audio.py`, `shortcuts.py`). Ses ve kısayollar Faz 5'ten öne alındı.
- [x] **[CLAUDE]** Yazı tipi üretme betiği: `firmware/tools/fontlari_uret.sh` (Montserrat + Türkçe + ikonlar, 12–30 px + 40 px ikon).
- [x] **[SEN]** Yazı tipi dönüştürücüsünü kur → kullanıcı kurdu (`firmware/tools/node`, lv_font_conv 1.5.2).
- [x] **[CLAUDE]** Yazı tiplerini üret, `PC_PANEL_TR_FONTS=1` ile derle, karta yükle → 7 yazı tipi; flash %15,5;
      yazılım 0.4.0 yüklendi, servis bağlandı, 12 sn denemede hata yok.
- [x] **[SEN]** Gerçek ekranda kontrol: Türkçe harfler, okunabilirlik, düğme büyüklüğü, sayfa kaydırma akıcılığı;
      ilerleme ve ses kaydırıcıları; 8 kısayolun her biri → **hepsi düzgün**.

Karar verilecek içerik listesi:
- Sistem: CPU %, CPU °C, GPU %, GPU °C, VRAM, RAM, disk, ağ, saat/tarih, çalışma süresi
- Medya: kapak, şarkı/sanatçı, ilerleme çubuğu, ⏮ ⏯ ⏭, ses kaydırıcısı, sessiz
- Kısayollar (isteğe bağlı): uygulama aç, ekran kilitle, mikrofonu kapat, ekran görüntüsü

**Bitti ölçütü:** onaylı tasarım kart üzerinde akıcı çalışıyor.

---

## Faz 5 — Medya kontrolünü tamamlama
- [x] **[CLAUDE]** Kapak resmini indir/oku → 240×240'a küçült → RGB565 olarak karta gönder; aynı kapağı tekrar gönderme.
      → `host/pc_panel/art.py` (Pillow), yazma iş parçacığı (`link.py`), protokol v1.2; kart 0.5.0: çift PSRAM tamponu,
      CRC-32 kontrolü, 2 sn hareketsizlik zaman aşımı. İlk deneme: 112 KB ≈1,5 sn'de alındı, CRC tuttu.
- [x] **[CLAUDE]** Sistem sesi (PipeWire, `wpctl`) okuma/ayarlama, sessiz; kaydırıcı ile çift yönlü eşleme → Faz 4'te yapıldı.
- [x] **[CLAUDE]** İlerleme çubuğuna dokunarak sarma (seek) → Faz 4'te yapıldı.
- [ ] **[CLAUDE]** Birden çok çalar varsa karttan çalar seçimi (isteğe bağlı).
- [x] **[SEN]** Farklı çalarlarla test: şarkı değişince kapak geliyor mu? Spotify, tarayıcıda YouTube, yerel çalar;
      çalar kapatılınca yer tutucuya dönüyor mu? → **hepsi düzgün**.

**Bitti ölçütü:** Spotify ve tarayıcıda bütün kontroller ve kapak çalışıyor.

---

## Faz 6 — Kalıcı kurulum (her açılışta kendiliğinden çalışsın)
- [x] ~~**[CLAUDE]** `deploy/99-pc-panel.rules`: kart her zaman `/dev/pcpanel` adıyla görünsün.~~
      → Gerek kalmadı: `/dev/serial/by-id/…` yolu zaten kalıcı (bkz. `kararlar.md`). [SEN] udev/sudo adımı da kalktı.
- [x] **[CLAUDE]** `deploy/pc-panel.service` (systemd kullanıcı servisi) + `deploy/kur.sh` (kur / `kaldir`).
      `systemd-analyze --user verify` temiz.
- [x] **[CLAUDE]** Ekran davranışı (kart 0.6.0): PC kilitliyken (`locked`), servis kapanırken (`bye`) ya da 60 sn
      bağlantı yoksa arka ışık kapanır; karanlıkta dokununca 20 sn açılır (dokunma düğmelere geçmez).
      Bilgisayarda: KDE kilit sorgusu, SIGTERM/Ctrl+C'de `bye`. Deneme: SIGTERM → çıkış 0, ekran karardı ve
      yeniden bağlanınca açıldı.
- [x] **[SEN]** Elle çalışan `pc-panel` varsa kapat (Ctrl+C), sonra servisi kur → kuruldu (enabled, active):
      ```bash
      /mnt/veri/yazilim/esp32-lcd-controller-card/deploy/kur.sh
      ```
- [x] **[SEN]** Kilit testi: ekranı kilitle (Meta+L) → kart kararmalı; karta dokun → 20 sn açılmalı; kilidi aç → panel geri gelmeli. → düzgün.
- [x] **[SEN]** Bilgisayarı yeniden başlat; panel hiçbir şeye dokunmadan geliyor mu? Kısayollar (Terminal vb.) servisten de çalışıyor mu?
      → düzgün. Günlük: açılış 16:47:07, servis 16:47:31'de kendiliğinden başladı, karta bağlandı, kapağı gönderdi.

**Bitti ölçütü:** yeniden başlatma sonrası hiçbir şeye dokunmadan panel çalışıyor.

---

## Faz 7 — İsteğe bağlı geliştirmeler
Kullanıcı 2026-11-17'de önce "kolay paket"i seçti (7A); ardından hava durumunu istemedi ve yazılımcı olarak
işine yarayacak özellikleri istedi (7B).

### 7A — Kolay paket (ayar dosyası, kısayollar, bildirim, kilit saati, uyarılar)
- [x] **[CLAUDE]** Ayar dosyası `~/.config/pc-panel/ayarlar.toml` (örnek: `deploy/ayarlar.ornek.toml`); değişince
      servis yeniden başlatılmadan uygulanır.
- [x] **[CLAUDE]** Kısayollar ayar dosyasından: en çok 12 kutu, ikon adları, uygulama / komut / adres / özel / makro.
- [x] **[CLAUDE]** Bildirimleri karta yansıtma (D-Bus izleme), hariç tutulan uygulamalar, kilitliyken gizli.
- [x] **[CLAUDE]** Kilitliyken büyük saat + tarih, süre dolunca karartma.
- [x] ~~Hava durumu (Open-Meteo)~~ → kullanıcı istemedi, 7B'de kaldırıldı.
- [x] **[CLAUDE]** Sıcaklık / RAM uyarısı (üst şeritte kırmızı), disk dolunca tek seferlik bildirim.

### 7B — Geliştirici paketi (kart 0.8.0, protokol v1.5)
- [x] **[CLAUDE]** Olay soketi `$XDG_RUNTIME_DIR/pc-panel.sock` + `pc-panel-olay` aracı (claude / komut / bildir).
- [x] **[CLAUDE]** Claude Code durumu: hook'lar (`deploy/claude_hooks.py kur|kaldir|durum`), oturum listesi,
      izin isteyince ve uzun iş bitince bildirim, üst şeritte "Claude: N bekliyor", kilit ekranında da.
- [x] **[CLAUDE]** İkinci Claude hesabı (`~/.claude-hesap2`, `claude2`): hook'lar iki dizine de kuruldu, kartta "proje · hesap2".
- [x] **[CLAUDE]** fish: 30 sn'den uzun süren komut bitince ✓/✗ bildirim (`deploy/pc-panel.fish`).
- [x] **[CLAUDE]** GitHub: son Actions çalışmaları, CI bitince / başarısız olunca bildirim, PR ve bildirim sayıları.
- [x] **[CLAUDE]** Sunucu/site sağlığı: 7 kayıt (iurl.tr, app.iurl.tr, hamza.tr, api.hamza.tr, tulparlang.dev,
      pkg.tulparlang.dev, myserver SSH); kapanınca uyarı + bildirim, SSL < 7 gün uyarısı.
- [x] **[CLAUDE]** Kart: 4. sayfa "Geliştirici", bildirim türleri (✓ yeşil, ✗ kırmızı, ⚠ sarı), hava durumu kaldırıldı.
      → Claude denedi: kart 0.8.0 yüklendi; hook olayları (13 ms, çıkış 0), izin bildirimi, `pc-panel-olay bildir`,
      fish'te `sleep 31; false` → "çıkış 1" bildirimi, gh verisi servisten geliyor; Claude ve sunucu mantığı birim denemeli.
- [ ] **[SEN]** Kartta gözle kontrol (7A + 7B birlikte):
      1. Kısayollar sayfası: 8 kutu, ikonlar ve Türkçe yazılar düzgün mü?
      2. Geliştirici sayfası (en sağ): Claude oturumları, GitHub satırları (iurl "Deploy API" kırmızı olmalı), 7 sunucu kutusu.
      3. **Yeni bir** Claude Code oturumu aç, bir şey sor → kartta "çalışıyor"; izin isteyince sarı + bildirim; bitince "bitti".
      4. Yeni bir fish terminalinde `sleep 31` → 31 sn sonra kartta ✓ bildirimi.
      5. `notify-send -a Deneme "Merhaba" "Kart bildirimi"` → balon kayarak geliyor mu, dokununca kapanıyor mu?
      6. Kilit saati: Meta+L → büyük saat; dokununca saat kalıyor; kilidi açınca panel geri geliyor.

### 7D — Günlük kullanım ekleri (kart 0.9.0, protokol v1.6)
Kullanıcı "800 özellik değil, her gün kullanacağım şeyler" dedi; yalnızca ikisi seçildi.
- [x] **[CLAUDE]** Claude kullanım göstergesi: iki hesap için 5 saatlik penceredeki token ve sıfırlanmaya kalan süre
      (Geliştirici → Claude kutusunun altı). Yüzde, son 7 günün en yoğun penceresine göre.
- [x] **[CLAUDE]** Push / commit edilmemiş iş satırı (Geliştirici → GitHub kutusunun altı), son 7 günde dokunulan depolar.
- [ ] **[SEN]** Bir hafta kullan; hiç bakmadığın özellik varsa söyle, kaldıralım.

### 7E — Hızlı uygulama başlatma (kart 0.10.0, protokol v1.7)
- [x] **[CLAUDE]** Yeni "Uygulamalar" sayfası (Medya ile Kısayollar arası), 5×3 = en çok 15 uygulama, gerçek ikonlar
      (`.desktop` + ikon teması → 64×64 RGB565+alfa). Liste: Steam, Epic Games, Antigravity, VS Code, Zen, Discord,
      Spotify, RustDesk, AnyDesk, Thunderbird (`[uygulamalar] liste`).
- [ ] **[SEN]** Uygulamalar sayfasında ikonlar düzgün mü, dokununca uygulama açılıyor / öne geliyor mu?
      (İstersen Kısayollar'daki Tarayıcı ve Spotify kutularını ayar dosyasından sil: artık Uygulamalar'da var.)

### 7C — Sonra (karar verilecek)
- [ ] Görev çalıştırıcı kutular (çalışıyor → ✓/✗ ve süre, tehlikeli işlerde onay)
- [ ] Geliştirme ortamı sayfası: dinlenen localhost portları, docker konteynerleri, adb / tailscale cihazları
- [ ] Odak modu: pomodoro + KDE "Rahatsız Etme"
- [ ] Karttan çalar seçimi · ses çıkışı seçimi
- [ ] Kartın kendi USB girişinden HID medya tuşları, mümkünse tek kablo
- [ ] Wi‑Fi + WebSocket ile kablosuz çalışma + OTA güncelleme
- [ ] **[SEN]** Stand / kasa (3D baskı ya da hazır stand)

---

## İlerleme özeti
| Faz | Durum |
|-----|-------|
| 0 Hazırlık | ✅ bitti (2026-11-17) |
| 1 Ekran + dokunmatik | ✅ bitti (2026-11-17) |
| 2 PC servisi | ✅ bitti (2026-11-17) |
| 3 Protokol | ✅ bitti (2026-11-17) |
| 4 Arayüz | ✅ bitti (2026-11-17) |
| 5 Medya | ✅ bitti (2026-11-17); karttan çalar seçimi isteğe bağlı, yapılmadı |
| 6 Kalıcı kurulum | ✅ bitti (2026-11-17) |
| 7 Ekstralar | 7A + 7B + 7D + 7E kodlandı, kart 0.10.0 (2026-11-17) — bir haftalık kullanım; 7C sonra |
