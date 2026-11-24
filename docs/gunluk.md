# Geliştirme Günlüğü

En yeni kayıt en üstte.

## 2026-11-24 — Hata: panel "donuyor", Spotify güncellenmiyor, durdur çalışmıyor
- Kullanıcı: bazen ekran donuyor, eski şarkı kalıyor, durdur düğmesi çalışmıyor.
- İnceleme: servis 7 günde hiç "kart sessiz" uyarısı vermemiş → kartın ana döngüsü takılmıyor. 9 "bağlantı koptu"
  kaydı var ama çekirdek log'unda USB kopması yok. Kart günlüğü (20 sn `--debug`) temiz, kart 6 saattir açık.
- **Asıl neden:** etkin çalar, bilgisayardaki Spotify değil KDE Connect üzerinden telefondaki "Spotify - <telefon>"
  idi (Spotify Connect ikisinde de aynı şarkıyı "çalıyor" gösteriyor; telefon yeniden bağlanınca öne geçiyordu).
  Telefonun bilgisi gecikmeli ve uykudayken komut almıyor → eski şarkı + boşa giden düğmeler.
- **Ek neden:** bir günde 271 "KDE Bağlan" bildirimi (telefondaki Spotify'ın şarkı bildirimleri) Medya sayfasının
  üstünü her şarkıda 6 sn kapatıyordu; `haric = ["Spotify"]` uygulama adı farklı olduğu için süzmüyordu.
- **Üçüncü bulgu:** servis yeniden başlayınca 10 ikonun 2–3'ü ilk seferde bozuk geliyordu (CRC); 15:34'teki
  kopmalarda da kapak/ikon hataları vardı. Neden: UART FIFO taşması (bkz. `01-donanim.md`).
- Düzeltmeler (bkz. `kararlar.md`, üç kayıt):
  - `media.py`: bilgisayardaki çalar öncelikli, `[medya] yoksay` ayarı, boştayken gerçek parçası olan çalar.
  - `__main__.py`: KDE Connect bildirimlerinde başlığa da `haric` uygulanıyor; kalp atışındaki taşma sayaçları
    artınca günlüğe yazılıyor. `link.py`: kopma nedeni günlüğe yazılıyor (önceden yazılmıyordu).
  - Kart 0.11.1: UART kesmesi çekirdek 0, `setRxFIFOFull(32)`, taşma sayacı `hb.ovf` / `hb.full`.
  - `deploy/ayarlar.ornek.toml`: `[medya]` bölümü.
- Deneme: etkin çalar artık bilgisayardaki Spotify; `yoksay = ["p20 pro"]` ile telefon listeden çıkıyor; ayar
  hatalı yazılınca uyarı veriyor. 0.11.1 yüklendi: 3 bağlanma denemesinde ikonların 10/10'u ilk seferde ulaştı,
  taşma 0; servis yeniden başlatıldı, kapak + ikonlar birlikte gitti, hata yok.
- Doğrulanmadı: kullanıcının gerçek kullanımında donmanın bir daha olmaması (zamanla görülecek). Kullanıcının kendi
  `~/.config/pc-panel/ayarlar.toml` dosyasına `[medya]` bölümü eklenmedi (varsayılan boş liste yeterli).

## 2026-11-20 — Faz 8: Windows 11 desteği
- Kullanıcı: bilgisayarda CachyOS ve Windows 11 ikisi de var; Windows'ta kartta hiçbir değer gelmiyor. İstek: proje
  iki sistemde de düzgün çalışsın. Bu oturum Windows'ta (depo: `C:\Users\Hamza\Desktop\projeler\pc-panel`).
- Neden gelmiyordu: Windows'ta servis hiç kurulu/çalışır değildi ve çalışsa da başlayamazdı (`dbus_fast` importu,
  `os.getuid()`, Unix soketi, `loop.add_signal_handler`, `psutil.sensors_temperatures`, `wpctl`, `kstart`).
- Ortam: Python 3.12.10 vardı, `uv` yoktu → `pip install uv` (kullanıcı alanı), `uv sync` (winrt 4.2, pycaw, comtypes).
- Yoklama: kart COM4 (`1A86:55D3`, Windows'un kendi sürücüsü), NVML çalışıyor, GSMTC Spotify'ı görüyor, bildirim
  dinleyici izni "Allowed", kabuk ikonları (IShellItemImageFactory) 64 px alfa ile düzgün, WMI var ama CPU sıcaklığı
  kaynağı yok (termal bölge yok, LibreHardwareMonitor kurulu değil).
- Yazıldı: `backend.py`, `win/` (media, audio, notify, apps, session, sensors), `deploy/kur.ps1`,
  `deploy/ayarlar.ornek.windows.toml`, `deploy/pc-panel.ps1`, `.gitattributes`; ortak dosyalarda Windows dalları
  (ayrıntı: `02-mimari.md` tablo, `kararlar.md` 2026-11-20).
- **Sorun:** Windows'ta kapak ve ikonlar sürekli "alınamadı". Tanı betikleri: tek başına kapak geçiyor; kart meşgulken
  akıştan birkaç bayt düşüyor (`115183 / 115200`). Windows sürücüsü baytları boşluksuz basıyor (1,27 sn; Linux 1,5 sn).
  Düzeltme: ikili bloklar sıralı + onay beklemeli, sayfa kurulumundan sonra 0,5 sn, Windows'ta %85 hızla 1 KB parça.
  Sonrasında servis açılışında kapak + 4 ikon ilk denemede alındı. (Kullanıcı kartın zarar görmesinden endişelendi:
  denemeler yalnızca normal hızda seri veri, yükleme / voltaj yok; yük testleri yine de bırakıldı.)
- Bulunan diğer hatalar: `settings.json` Windows'ta cp1254 ile okunup yazılacaktı (Türkçe bozulurdu) → UTF-8;
  PowerShell borusu BOM ekliyor → `pc-panel-olay` BOM'u atıyor; ev klasöründe erişimi kapalı bağlantılar git
  taramasını düşürebilirdi → yakalanıyor; Pillow 14'te kalkacak `getdata()` → `tobytes()`.
- Denendi (Windows, kart takılı): bütün mesaj türleri karta gidiyor; `pc-panel-olay bildir`, Claude hook olayları,
  WM_ENDSESSION ile kapanış (çıkış 0), ses okuma/yazma (aynı düzey), kilit algılama, git taraması.
  Linux yolları `sys.platform="linux"` benzetimiyle denetlendi. Medya komutları (durdur / ileri) ve kısayollar
  kullanıcının müziğini / ekranını etkilememek için denenmedi → kullanıcı testi.
- Yapılamayan: `kur.ps1` Claude tarafından çalıştırılmadı (kalıcı görev + Claude ayarlarını değiştiriyor; izin
  verilmedi) → plan Faz 8 [SEN]. Statik denetim aracı (pyflakes) çalıştırma izni de verilmedi.
- Kullanıcı `deploy\kur.ps1`'i kendisi çalıştırdı: "PC Panel" görevi Running, 6 Claude hook'u kurulu,
  `%APPDATA%\pc-panel\ayarlar.toml` oluştu. Günlükte karttan medya komutları, uygulama açma, 5 kısayol ve Claude
  izin bildirimi "tamam". Kullanıcı: "her şey düzgün çalışıyor".
- **Kullanıcı doğrulaması (2026-11-20):** panel Windows 11'de kararlı çalışıyor. Sistem değerleri, medya ve kapak,
  uygulama ikonları, kısayollar ve Claude oturumları kartta; servis Görev Zamanlayıcı'dan kendiliğinden başlıyor.
  **Faz 8 Windows tarafı tamamlandı.** Commit atıldı ve GitHub'a gönderildi.
- **Sıradaki:** CachyOS'a geçince `cd host && uv sync` (kilit dosyası değişti) ve kısa bir kontrol;
  istenirse LibreHardwareMonitor (Windows'ta CPU °C).

## 2026-11-18 — Kasa tasarımı (kasa/)
- Kullanıcı: 3D baskı kasa; en iyi soğutma ve masada eğik durma. Hazır modeller bulundu (MakerWorld 374370,
  2982581) ama sayfaları otomatik okunamadı; kullanıcı kendimiz tasarlamayı seçti.
- Waveshare 3D modeli (5,4 MB zip → 31 MB STEP, 693 parça) build123d ile okunup ölçüler çıkarıldı: M3 ayaklar,
  USB-C yerleri, düğmeler, en derin parça (`01-donanim.md`).
- `kasa/kasa.py`: gövde (tepsi, 4 × M3×12 ile kartın ayaklarına), stand (20°, pencereli dayanak, arka destek kolu).
  Denetim: gövde ↔ kart 0,00 mm³, stand ↔ gövde 0,00 mm³. Blender ile önizlemeler (`kasa/onizleme/`).
- İlk sürümde ESP32 modülünün arkasına konan dikey yarıklar yataylarla kesişip kırılgan adacıklar oluşturuyordu
  → kaldırıldı (yatay yarıklar modülü zaten kapsıyor).
- Basılmadı; oturma, USB fişleri ve ısınma kullanıcıda.
- Kullanıcı vidasız montaj istedi → üst ve alt duvarda ikişer geçmeli dil (19 mm esneyen boy, kanca cama
  ≈ 0,85–1,0 mm biner, üstü 45° pahlı). Esneme payı ≈ %0,9. Kancalar kartla çakışmıyor (0,00 mm³); alt kancaların
  çıkıntısı standın dudağına giriyordu (72 mm³) → oturak 1,75 mm derinleştirildi, çakışma 0. Deneme çerçevesi artık
  tabansız gövde (kancaları da dener). Vida delikleri isteğe bağlı olarak kaldı.
- Baskıyı kullanıcının arkadaşı yapacak: STL'ler baskı yönünde dışa aktarılıyor (stand yan yatık), gövdenin ön
  halkasından `deneme_cercevesi.stl` eklendi (oturuş / USB / düğme denemesi), `kasa/BASKI_AYARLARI.txt` notu ve
  gönderim paketi `kasa/pc-panel-kasa-baski.zip` (git dışı) hazırlandı.

## 2026-11-17 — Açık kaynak hazırlığı ve GitHub'da yayın (kart 0.11.0)
- Kullanıcı kararı: depo public olacak; commit e-postası kişisel Gmail yerine `info@hamza.tr`.
- Genelleştirme: kartın seri numarası koddan çıktı (port VID:PID ile bulunup by-id yoluna çevriliyor; PlatformIO
  portu `firmware/*.local.ini` ile, bu bilgisayar için `kart.local.ini` git dışı). Servis ve fish dosyalarında
  `@KOK@` şablonu, `kur.sh` doldurur. CPU/GPU adları bilgisayardan `hw` mesajıyla geliyor (karttan sabit adlar
  kalktı). Disk listesi ayarda (`[sistem] diskler`, varsayılan `/`; tek diskte ikinci satır gizli). Git klasörü
  varsayılanı `~`. Örnek ayarlardaki Zen kısayolu yerine GitHub kutusu.
- Eklendi: `LICENSE` (MIT), `THIRD_PARTY.md` (Montserrat OFL, Font Awesome CC BY/OFL, Espressif CC0/Apache-2.0,
  LVGL MIT), `firmware/fonts/kaynak/OFL-Montserrat.txt`, iki dilli `README.md`.
- Deneme: kart 0.11.0 yüklendi, `kur.sh` yeniden çalıştı (servis ve fish dosyasına doğru yol yazıldı), `hw` mesajı
  "Ryzen 7 9800X3D" / "GeForce RTX 5080" gitti, servis çalışıyor.

## 2026-11-17 — Hata: yeniden bağlanınca ikonlar kayboluyordu (kart 0.10.1)
- Kullanıcı: Uygulamalar sayfasında yalnızca Steam ikonu var, diğerlerinde sadece yazı.
- Günlük: 19:21:18'de seri bağlantı iki kez koptu ve yeniden kuruldu (çekirdek günlüğünde USB kopması yok; o anda
  Steam'den Proton ile bir oyun açılıyordu, Wine'ın seri portları yoklaması olası ama kanıtlanmadı). Her
  bağlanışta `apps` + 10 ikon yeniden gönderildi; kart sayfayı yeniden kurarken tampon taştı, "ikon 1 alınamadı",
  sonrakiler zincirleme kayboldu, kapak da bir kez bozuk geldi.
- Düzeltme: bilgisayar ikonları dur-bekle ile gönderiyor (onay + 2 yeniden deneme); kart aynı `apps`/`tiles`
  listesinde sayfayı yeniden kurmuyor; seri tampon 16 → 32 KB.
- Deneme: kart açılışında 2 ikon bir kez bozuldu, yeniden denemeyle geldi (10/10). Ayar değiştirilerek sayfa iki kez
  yeniden kuruldu: 10/10, hatasız. Servis art arda 3 kez yeniden başlatıldı: her seferinde 10/10, sayfa silinmedi.

## 2026-11-17 — Faz 7E: hızlı uygulama başlatma (kart 0.10.0)
- İstek: Steam, Epic Games, Antigravity, VS Code, Zen, Discord, Spotify, RustDesk, AnyDesk, Thunderbird.
- Yoklama: hepsinin `.desktop` dosyası var (Epic: `~/.local/share/applications/epic-games-launcher.desktop`,
  VS Code: `com.microsoft.VSCode`, Zen: `zen`, Thunderbird: `org.mozilla.Thunderbird`). İkonlar hicolor / pixmaps'te,
  AnyDesk SVG (`rsvg-convert` var).
- `apps.py`: `.desktop` → ad + ikon, ikon teması zinciri, 64×64 RGB565+alfa; `--ayar-kontrol` uygulamaları ve ikon
  yollarını listeliyor. 10 ikonun önizlemesi çizilip gözle kontrol edildi (hepsi doğru).
- Kart 0.10.0: 5. sayfa düzeni Sistem · Medya · Uygulamalar · Kısayollar · Geliştirici. İkili alım kapak + ikon için
  ortaklaştırıldı. RAM %9,6, flash %16,6, uyarısız.
- Deneme (`--debug`): `apps` gitti, 10 ikonun hepsi "alındı" (≈1,5 sn). Uygulamaları açma denenmedi (masaüstünde
  pencere açmamak için); başlatma `kstart --application` ile, Kısayollar'daki gibi.
- Kullanıcının ayar dosyasına `[uygulamalar]` listesi kısa adlarla eklendi.

## 2026-11-17 — Sonraki adım: yeni özellik yok, bir hafta kullanım
- Kullanıcıya ölçüsüne göre ("günlük kullanılacak şeyler") tek aday sunuldu: karttan Claude izin onayı.
  Kullanıcı reddetti → `kararlar.md`'ye yazıldı. Yeni özellik eklenmiyor; bir hafta kullanıp bakılmayanlar kaldırılacak.

## 2026-11-17 — Faz 7D: Claude kullanım göstergesi ve push edilmemiş iş (kart 0.9.0)
- Kullanıcı yeni fikir listesini fazla buldu; günlük kullanacağı iki özellik seçildi.
- `usage.py`: iki hesabın kayıtları (8 günde 600 MB + 150 MB) → konum saklayarak artımlı okuma, (mesaj, istek)
  ile tekilleştirme, ccusage benzeri 5 sa pencereleri. İlk tarama 1,0 sn. Anlık: hesap1 83 K token (en yoğun
  pencerenin %5'i), 3 sa 52 dk sonra sıfırlanıyor; hesap2'de etkin pencere yok.
- `gitwatch.py`: /mnt/veri/yazilim altındaki 30 depo, 1,4 sn. İlk denemede 151 gündür dokunulmamış
  personal-budget-tracker silinmiş bir dosya yüzünden görünüyordu → silinen dosyalar yalnızca depo etkinse sayılıyor.
  Sonuç: tulpar-engine'de 4 push bekleyen commit; esp32-lcd, kup-kure-savasi, tulpar-engine'de değişiklik.
- Kart 0.9.0: Claude kutusu 4 oturum satırı + 2 kullanım satırı (ad, çubuk, "83 K · 3 sa 52 dk sonra"); GitHub
  kutusunun altında PR satırı ve sarı git satırı. RAM %9,0, flash %16,6, uyarısız.
- Kullanıcı ayar dosyasına `[claude] kullanim` ve `[git]` eklendi (diğer satırlara dokunulmadı).
- Deneme: `--debug` ile `cu` ve `git` mesajları karta gitti; servis yeniden çalışıyor. Görünüm kullanıcıda.

## 2026-11-17 — Faz 7B ek: ikinci Claude hesabı
- Kullanıcı Claude'u iki hesapla kullanıyor: `~/.claude` ve `~/.claude-hesap2` (fish `claude2` fonksiyonu,
  `CLAUDE_CONFIG_DIR`). Hook'lar yalnızca birincisindeydi.
- `deploy/claude_hooks.py`: dizin verilmezse bütün `~/.claude*` ayar dizinlerini buluyor; varsayılan dışındakilerde
  `pc-panel-olay claude --hesap hesap2`. Servis oturum adını "proje · hesap2" yapıyor. `claude2` uzun komut
  hariç listesine eklendi (yoksa kapatınca "uzun komut bitti" bildirimi gelirdi).
- Kuruldu: iki dizine de 6'şar hook (yedekler: `settings.json.yedek-20261117-185922`). Servis yeniden başlatıldı
  (açık oturumların durumu bir sonraki olaya kadar kartta görünmez). Deneme: "Tulpar · hesap2: izin bekliyor" geldi.

## 2026-11-17 — Faz 7B: geliştirici paketi (Claude Code, uzun komut, GitHub, sunucular), hava durumu kaldırıldı
- Kullanıcı hava durumunu istemedi ve yazılımcı olarak işine yarayacak özellikler istedi. Sunulan 7 fikirden
  1+2+3+4'ü seçti. Plan 7A / 7B / 7C olarak yeniden düzenlendi.
- Yoklama: gh oturumu açık (hamer1818); Actions çalışan depolar TulparLang, tulpar-engine, dpi-dashboard, iurl,
  kup-kure-savasi, hamzaortatepe-v4. Projelerde geçen alan adları denendi: iurl.dev / app|api.iurl.dev,
  api.iurl.tr ve hamzaortatepe.com çözülmüyor. Çalışanlar ayar dosyasına yazıldı: iurl.tr, app.iurl.tr, hamza.tr,
  api.hamza.tr (404 = ayakta), tulparlang.dev, pkg.tulparlang.dev, myserver SSH.
- Bilgisayar: `olay.py` (pc-panel-olay, pyproject'e giriş noktası, `uv sync`), `claude.py`, `github.py`,
  `servers.py`; servis olay soketi açıyor. `weather.py` silindi. Ayar dosyasına [claude] [komut] [github]
  [sunucular] [[sunucu]] eklendi; kullanıcının dosyası örnekle aynı olduğu için (elle değiştirilmemişti) yeni
  örnek + sunucular ile yeniden yazıldı.
- Kurulum: `deploy/claude_hooks.py kur` → 6 hook (yedek: `~/.claude/settings.json.yedek-20261117-175445`),
  `deploy/pc-panel.fish` → `~/.config/fish/conf.d/`. `kur.sh` ikisini de yapıyor.
- Kart 0.8.0: 4. sayfa "Geliştirici" (Claude 5 satır, GitHub 4 satır + PR/bildirim, 8 sunucu kutusu), bildirim
  ikonu ve kenar rengi türe göre, üst şeritte "Claude: N bekliyor", kilit ekranında bekleyen oturum. Hava UI'ı ve
  ikonları çıkarıldı (icon_font_40: 49 glif). `LINE_MAX` sistem tanımıyla çakışıyordu → `LINK_LINE_MAX`.
  RAM %9,0, flash %16,5.
- Denemeler (Claude): elle gönderilen hook olayları → "TulparLang: izin bekliyor" bildirimi; olay başına 13 ms,
  çıkış 0. `pc-panel-olay bildir` çalıştı. fish'te (`script` ile etkileşimli) `sleep 31; false` → "sleep (çıkış 1,
  31 sn)". `GitHubWatcher.poll` gerçek veri döndü (iurl "Deploy API" başarısız, 5 açık PR, 3 bildirim);
  servis içinden de hatasız. Claude durum makinesi ve sunucu kapandı/düzeldi geçişleri saat taklidiyle denendi.
  Deneme oturumları SessionEnd ile silindi.
- Denenmeyenler: gerçek bir Claude Code oturumunun hook'ları (yeni ayarlar yeni oturumlarda geçerli), kartın
  görünümü (kullanıcıda), CI bitince gelen bildirim (bir çalışmanın bitmesini beklemek gerekiyor).
- **Sıradaki:** kullanıcının gözle kontrolü (plandaki 6 madde), sonra commit; 7C'den seçim.

## 2026-11-17 — Faz 7A: ayar dosyası, ayarlanabilir kısayollar, bildirimler, kilit saati, uyarılar
- Kullanıcı Faz 7 için "kolay paket" ile başlamayı seçti. Plan 7A / 7B / 7C olarak bölündü (`00-plan.md`).
- Bilgisayar: `config.py` (TOML, canlı yeniden yükleme, `--ayar-kontrol`), `shortcuts.py` ayardan çalışıyor
  (uygulama / komut / adres / özel / medya / makro + bekle), `notify.py` (D-Bus BecomeMonitor), `weather.py`
  (Open-Meteo), `alerts.py`. Protokol v1.4: `tiles`, `cfg`, `wx`, `notif`, `stat.warn`, `cmd mute`.
- Önce küçük bir denemeyle `BecomeMonitor` + `notify-send` denendi, çalıştı. dbus-fast'ta işleyici `True`
  döndürmezse kütüphane izleyici bağlantıdan hata yanıtı göndermeye çalışıyor; buna dikkat edildi.
- Kart 0.7.0: kutular dinamik (en çok 12, 9+ kutuda 3 satır), bildirim balonu (üstten kayar, dokununca kapanır),
  üst şeritte kırmızı uyarı ve hava durumu, kilit saati ekranı (120 px rakamlar + tarih + hava), ekran durum
  makinesi (panel / kilit saati / karanlık). `LINE_MAX` 2048 → 4096.
- Yazı tipleri yeniden üretildi: icon_font_40'a 42 ikon eklendi (toplam 57), tr_font_*'a hava ikonları, yeni
  clock_font_120. RAM %8,9, flash %16,8. Uyarısız derlendi.
- Denemeler (Claude): servis elle `--debug` ile, karalama klasöründe 10 kutulu ve Ankara'lı bir deneme ayarıyla
  çalıştırıldı. Kutular, ayarlar ve hava durumu karta gitti. Deneme bildirimi karta ulaştı, Spotify bildirimi süzüldü.
  Kartın ekran geçişleri sahte `stat` mesajlarıyla denendi: kilit saati, kilit açılınca panel, ayar kapalıyken
  karanlık, yeni uyarıyla uyanma → hepsi doğru. 10 dakikalık kilit süresinin dolması denenmedi (beklemek gerekiyor).
- `~/.config/pc-panel/ayarlar.toml` örnekten oluşturuldu (şehir boş, hava durumu kapalı). Servis 3 sn içinde
  dosyayı yükledi. `kur.sh` artık dosya yoksa örneği kopyalıyor.
- Ekranın görünümü gözle kontrol edilmedi; bu kullanıcıda (plandaki [SEN] adımı).
- **Sıradaki:** kullanıcı kontrolü; sonra 7B (çalar seçimi, ses çıkışı, sayaç) ya da 7C.

## 2026-11-17 — Faz 6: kalıcı kurulum ve ekran karartma
- Yoklama: systemd kullanıcı ortamında WAYLAND_DISPLAY / DISPLAY / DBUS var; graphical-session.target etkin;
  `org.freedesktop.ScreenSaver.GetActive` yanıt veriyor (/ScreenSaver); `/mnt/veri` fstab'da.
- udev kuralı gereksiz bulundu (by-id yolu kalıcı); plandaki sudo adımı kaldırıldı.
- `deploy/pc-panel.service` + `deploy/kur.sh` yazıldı; `systemd-analyze --user verify` temiz.
- Bilgisayar: `media.screen_locked()`, `stat.locked`; SIGTERM/SIGINT'te `bye` + yazma kuyruğunu boşaltma (`link.flush`).
- Kart 0.6.0: kilit / bye / 60 sn bağlantısızlık → arka ışık kapalı + üst katmanda dokunma yakalayan siyah perde;
  dokununca 20 sn açık. RAM %7,7, flash %15,5.
- Deneme: 8 sn çalıştırıp SIGTERM → "kapanıyor", çıkış kodu 0. Yeniden açınca kart `# ekran acildi` yazdı
  (yani kararmıştı). Her saniye `locked: 0` gönderildi. Kilit testi kullanıcıda: Claude ekranı kilitlemedi.
- Kullanıcı testi: **hepsi düzgün**. Servis kuruldu (enabled/active); kilitlenince kart kararıyor, dokununca
  açılıyor, kilit açılınca geri geliyor. Yeniden başlatma sonrası (açılış 16:47:07) servis 16:47:31'de kendiliğinden
  başladı ve karta bağlandı; kısayollar servis içinden çalışıyor.
- **Faz 6 tamamlandı → Faz 0–6, yani ana plan bitti.** Faz 7 isteğe bağlı; kullanıcı seçecek.
- Kullanıcı Faz 7 için "şimdilik yeter" dedi; proje bu noktada beklemede. Seçenekler `00-plan.md` Faz 7'de.

## 2026-11-17 — Faz 5: kapak resmi
- Protokol v1.2 yazıldı (`02-mimari.md` "Kapak resmi"): başlık satırı + 115.200 bayt RGB565 + CRC-32, kart yanıtı.
- Bilgisayar: `art.py` (https / file:// okuma, ortadan kare kırpma, 240×240, RGB565 LE), Pillow 13.0.0 eklendi.
  `link.py`'ye yazma kuyruğu ve yazıcı iş parçacığı eklendi (write_timeout 0,5 → 5 sn). Servis kapağı
  şarkı değişince bir kez, kart yeniden başlayınca ya da bağlantı yeniden kurulunca tekrar gönderiyor.
  Hatalı alımda en çok 3 deneme yapıyor. Yazarken deneme sayacının her seferinde sıfırlandığı bir hata
  fark edildi ve düzeltildi.
- Kart 0.5.0: `esp_rom_crc32_le` ile CRC, iki PSRAM tamponu (yer değiştirme LVGL kilidi altında),
  `lv_img` + kartta `clip_corner`. RAM %7,7, flash %15,5.
- Deneme: Spotify kapağı 0,26 sn'de indirildi ve çevrildi. Karta 112 KB ≈1,5 sn'de ulaştı, CRC tuttu,
  aktarım sırasında bağlantı kopmadı.
- Kullanıcı testi: **hepsi düzgün**. Şarkı değişince kapak yenileniyor; Spotify, YouTube ve yerel çalarda
  çalışıyor; çalarlar kapanınca yer tutucuya dönüyor.
- **Faz 5 tamamlandı.** Karttan çalar seçimi (isteğe bağlı) yapılmadı. Sıradaki: Faz 6 — kalıcı kurulum.

## 2026-11-17 — Faz 4: Türkçe yazı tipleri ve karta ilk yükleme
- Kullanıcı `npm install --prefix tools/node lv_font_conv@1.5.2` ile dönüştürücüyü kurdu.
- Betik hatası: 1.5.2'de `--lv-font-name` seçeneği yok. Seçenek kaldırıldı; LVGL'deki ad çıktı dosyasının
  adından geliyor. (Seçeneği sed ile silerken satır devam işaretleri de silindi; betik düzeltildi.)
- 7 yazı tipi üretildi (`src/fonts/`, toplam ≈1,8 MB C kaynağı): tr_font_12/14/16/18/22/30 ve icon_font_40.
  15 ikonun hepsi var; Türkçe harfler var.
- `-DPC_PANEL_TR_FONTS=1` ile derlendi: RAM %7,7, flash %15,5 (1,01 MB). Karta yüklendi, 0.4.0 "merhaba" dedi.
  Servisle 12 sn deneme: kart günlüğünde uyarı/hata yok (yalnızca bilinen GT911 adres uyarısı).
- Üretilen `.c` dosyaları git'e ekleniyor: böylece derlemek için lv_font_conv gerekmiyor.
- Kullanıcı testi: **hepsi düzgün**. Türkçe harfler, saat/tarih, sayfa kaydırma, göstergeler/grafikler,
  ilerleme ve ses kaydırıcıları, sessiz düğmesi, 8 kısayolun hepsi çalışıyor.
- **Faz 4 tamamlandı.** Sıradaki: Faz 5 — kapak resmi.

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
