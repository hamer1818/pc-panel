# Kararlar

Her karar: tarih · karar · düşünülen seçenekler · neden.

## 2026-11-24 · Etkin çalar: bu bilgisayardaki çalar telefona (KDE Connect) göre öncelikli
- Sorun: Spotify Connect aynı şarkıyı hem bilgisayardaki Spotify'da hem KDE Connect üzerinden telefondaki
  "Spotify - <telefon>"da "çalıyor" gösteriyor. "En son çalmaya başlayan" kuralı yüzünden telefon her yeniden
  bağlandığında öne geçiyordu. Bilgisi gecikmeli geldiği, telefon uykudayken komutlara da yanıt vermediği için
  panelde eski şarkı kalıyor, durdur düğmesi boşa gidiyordu.
- Seçenekler: KDE Connect çalarlarını hep yok saymak · bilgisayardakini öncelikli tutmak · yalnızca ayarla seçmek
- Karar: bilgisayardaki çalar öncelikli (telefon yalnızca burada bir şey çalmıyorsa); isteyen `[medya] yoksay` ile
  tamamen gizler. Böylece telefonda tek başına müzik dinlerken panelden kontrol etme özelliği de korunuyor.
- Ek: hiçbir şey çalmıyorken ve geçmiş yokken (servis yeni başladı) gerçek parçası olan çalar seçilir; tarayıcıdaki
  2 sn'lik WhatsApp bildirim sesi Spotify'ın önüne geçmesin.

## 2026-11-24 · KDE Connect bildirimlerinde `haric` telefondaki uygulama adına da uygulanır
- KDE Connect bildirimleri uygulama adı "KDE Bağlan" (KDE Connect) ile, başlığı telefondaki uygulama adı olarak
  gelir. Telefondaki Spotify'ın "şimdi çalıyor" bildirimi her şarkıda Medya sayfasının üstünü 6 sn kapatıyordu
  (bir günde 271 bildirim). `haric = ["Spotify"]` artık bunları da süzüyor.

## 2026-11-24 · Kart: UART kesmesi çekirdek 0'da, FIFO eşiği 32, taşma sayacı (0.11.1)
- Sorun ve ölçüm: `01-donanim.md` "Seri alım ve bayt kaybı".
- Seçenekler: baud'u düşürmek (kapak 2,5 sn'ye çıkar) · donanım akış denetimi (kartta RTS/CTS hattı yok) ·
  kesmeyi ekran kesmesinden ayırıp FIFO'yu erken boşaltmak
- Karar: sonuncusu; hız korunuyor, kanıt için taşma sayacı kalp atışında.
- İlişki: Windows'ta aynı bayt kaybı (2026-11-20) bilgisayar tarafında büyük blokları yavaşlatarak çözülmüştü
  (aşağıda "Windows'ta ikili bloklar yavaşlatılır"). 0.11.1'deki kart tarafı düzeltmesi iki işletim sisteminde de
  geçerli; Windows'taki yavaşlatma ek güvenlik payı olarak kaldı.

## 2026-11-20 · Faz 8: tek kod tabanı, iki işletim sistemi (Linux + Windows 11)
- İstek: bilgisayarda CachyOS ve Windows 11 ikisi de var; Windows açılınca kartta hiçbir değer gelmiyordu
  (servis Windows'ta hiç başlayamıyordu: `dbus_fast`, `os.getuid`, Unix soketi, `add_signal_handler`, `wpctl`…).
- Seçenekler: ayrı bir Windows servisi (C# / ayrı depo) · aynı Python servisi, işletim sistemine özgü modüller ayrı.
- Neden aynı servis: protokol, kart yazılımı, ayar biçimi, Claude/GitHub/sunucu/git mantığı zaten taşınabilir;
  yalnızca 6 dokunma noktası farklı. `backend.py` seçer, Windows karşılıkları `pc_panel/win/` altında, Linux
  modülleri olduğu gibi kaldı. Bağımlılıklar `sys_platform` işaretiyle (Linux'ta winrt/pycaw kurulmaz).
- Kart yazılımı değişmedi (yeniden yükleme gerekmez).

## 2026-11-20 · Windows medya: GSMTC (winrt); ses: pycaw; bildirimler: UserNotificationListener
- Medya: GlobalSystemMediaTransportControlsSessionManager — sistemin ses penceresindeki medya kutusunun kaynağı;
  Spotify, tarayıcılar, Medya Oynatıcı… MPRIS'in Windows karşılığı. Kapak adres değil akış: `art_url` yerine
  parça bilgisinden anahtar ("gsmtc:…"), servis kapağı `media.fetch_art()` ile ister (Linux'ta da aynı ad).
- Ses: Core Audio IAudioEndpointVolume (pycaw); her çağrıda varsayılan aygıt yeniden alınır (kulaklık değişimi).
- Bildirimler: UserNotificationListener paketlenmemiş uygulamada da izin verdi (bu bilgisayarda "Allowed").
  Olay aboneliği paketsiz uygulamalarda güvenilmez → saniyede bir liste okunur, yeni kimlikler gönderilir.
- COM: winrt + comtypes aynı süreçte → ikisi de MTA (`sys.coinit_flags = 0`, `win/__init__.py`).

## 2026-11-20 · Windows'ta CPU sıcaklığı yalnızca LibreHardwareMonitor ile
- Windows, Ryzen / Core sıcaklığını sürücüsüz vermiyor; bu bilgisayarda ACPI termal bölge de yok (WMI boş).
- Seçenekler: servisi yönetici yapıp sürücü yüklemek (LibreHardwareMonitorLib + pythonnet) · LibreHardwareMonitor
  açıksa onun WMI sağlayıcısını okumak · sıcaklığı göstermemek.
- Neden WMI: servis yönetici olmadan çalışmaya devam eder; LHM kurulu değilse kart "-" gösterir, başka bir şey
  bozulmaz. 30 sn'de bir yeniden bağlanmayı dener (LHM sonradan açılırsa kendiliğinden gelir).
- Saat hızı: psutil Windows'ta taban hızı veriyor → Görev Yöneticisi'nin yöntemi (PDH "% Processor Performance"
  × taban MHz), yönetici gerekmez.

## 2026-11-20 · Windows'ta ikili bloklar yavaşlatılır ve sıraya konur
- Sorun: Windows'ta kapak ve ikonlar sürekli "alınamadı" (CRC). Tanı: kartın kendi zaman aşımı satırı
  `115183 / 115200 bayt` → kart meşgulken (sayfa kurma, ikon işleme) akışın ortasından birkaç bayt düşüyor.
  Tek başına gönderilen kapak sorunsuz. Linux'ta aynı kapak ≈1,5 sn, Windows'ta ≈1,27 sn sürüyor: Windows'un
  USB-seri sürücüsü baytları boşluksuz, tam baud hızında basıyor; Linux'ta paketler arasında doğal boşluk var.
- Seçenekler: kart yazılımında UART FIFO eşiğini düşürmek (yeniden yükleme gerekir) · baud düşürmek (her şey
  yavaşlar) · bilgisayar tarafında ikili blokları sıraya koyup yavaşlatmak.
- Karar: bilgisayar tarafı. (1) İkili bloklar üst üste gönderilmez, her biri kartın onayını bekler; (2) `tiles` /
  `apps` sonrası 0,5 sn beklenir; (3) Windows'ta 4 KB üstü yazmalar 1 KB parça, hattın %85'i hızında
  (Linux süresiyle aynı). Deneme: servis açılışında kapak + 4 ikon ilk seferde alındı, yeniden deneme yok.
  (1) ve (2) Linux'ta da geçerli, zararsız. Kart yazılımı değişmedi.

## 2026-11-20 · Windows uygulama kimlikleri: Başlat menüsü adı ya da AppID; Linux kimlikleri de tanınır
- Kaynak: kabuğun `shell:AppsFolder` klasörü (Get-StartApps'ın kaynağı) — ad, AppID ve varsa exe yolu tek sorguda.
- Eşleşme: tam AppID → bilinen Linux kimliği tablosu (`com.microsoft.VSCode` → Visual Studio Code, `org.kde.konsole`
  → Terminal …) → ad. Böylece Linux ayar dosyası kopyalansa da çoğu uygulama bulunur.
- İkon: IShellItemImageFactory (Gezgin'deki ikonun aynısı, alfa önçarpımsız — denendi). Başlatma: exe'nin penceresi
  açıksa öne getirilir (kstart davranışı), değilse `shell:AppsFolder\<AppID>` açılır.
- Windows'ta kimlik kuralı genişletildi (boşluk, `!`, `{}`, `\`): kimlik yalnızca listede aranır, çalıştırılmaz.

## 2026-11-20 · Windows'ta olay kanalı 127.0.0.1:47613 TCP
- Python Windows'ta AF_UNIX açamıyor. Seçenekler: adlandırılmış kanal (pywin32 gerekir) · yerel TCP.
- Neden TCP: standart kütüphane yeter (`pc-panel-olay` hızlı açılmalı), PowerShell'den de doğrudan yazılabiliyor.
  Yalnızca 127.0.0.1'e bağlanır. Olaylar yalnızca karta bildirim / Claude durumu getirir, komut çalıştırmaz;
  bu yüzden ek kimlik doğrulama konmadı.

## 2026-11-20 · Windows'ta kalıcı kurulum: Görev Zamanlayıcı + pythonw
- Seçenekler: Windows hizmeti (oturum 0'da çalışır, medya / bildirim / masaüstüne erişemez; yönetici gerekir) ·
  Başlangıç klasörü kısayolu (çökünce yeniden başlamaz) · Görev Zamanlayıcı'da kullanıcı görevi.
- Neden görev: kullanıcı oturumunda çalışır (GSMTC, bildirimler, ses), yönetici gerekmez, süre sınırı kaldırılabilir,
  çökünce yeniden başlar. Eklenemezse betik Başlangıç klasörüne düşer. Penceresiz çalıştığı için çıktı
  `--gunluk` dosyasına; kapanış Ctrl+C yerine WM_ENDSESSION ile yakalanıp karta "bye" gönderilir.

## 2026-11-17 · Faz 7E: uygulamalar ayrı sayfada, gerçek ikonlarla
- İstek: Steam, Epic Games, Antigravity, VS Code, Zen, Discord, Spotify, RustDesk, AnyDesk, Thunderbird için hızlı başlatma.
- Seçenekler: mevcut Kısayollar sayfasına eklemek (12 kutu sınırı, 8'i dolu; Font Awesome'da Epic, Antigravity,
  RustDesk, AnyDesk, Thunderbird yok) · ayrı sayfa + gerçek ikonlar.
- Neden ayrı sayfa: 10 uygulama + mevcut 8 kısayol tek sayfaya sığmıyor; gerçek ikonlar kutuları bir bakışta
  tanınır yapıyor. İkonlar kartta saklanmıyor, her bağlantıda bilgisayardan gönderiliyor (≈1,5 sn); yazı tipine
  derlenseydi her yeni uygulama için kart yazılımı yeniden yüklenmeliydi.
- Uygulama ayar dosyasında yalnızca `.desktop` kimliğiyle yazılıyor; ad ve ikon oradan geliyor, ad isteğe göre kısaltılabiliyor.

## 2026-11-18 · Kasa: kendi tasarımımız, build123d, ön çerçevesiz tepsi + ayrı stand
- Seçenekler: hazır modeller (MakerWorld 374370 / 2982581; içerikleri ve USB-UART erişimi doğrulanamadı) ·
  OpenSCAD (kurulu değil, sudo ister) · build123d (Python, `uv` ile kullanıcı alanında).
- Neden build123d: Waveshare'in STEP modelini doğrudan okuyup ölçü çıkarmak ve tasarımı modelle çakışma
  denetiminden geçirmek mümkün; parametrik, STL + STEP üretiyor.
- (Güncelleme, aynı gün: kullanıcı vidasız istedi → kart üst/alt duvardaki geçmeli kancalarla tutuluyor, vida
  delikleri isteğe bağlı. Kanca camın siyah kenarına ≈1 mm biner; dil 19 mm, esneme ≈ %0,9.)
- Tasarım: kartın kendi 4 × M3 dişi ayağına arkadan vidalanan tepsi (ön çerçeve yok; cam önden görünür, duvar
  camdan 0,4 mm önde). Ön çerçeve olsaydı ayaklar camın arkasında kaldığı için vidalar önden takılamazdı ve
  çerçeveyi tutacak ayrı bir bağlantı gerekirdi. Stand ayrı parça: tepsi arkası düz basılabilsin, eğim
  değiştirilebilsin. Pasif soğutma: 3 mm arka hava katmanı + alt/üst duvar yarıkları (baca) + arka yarıklar;
  fan yok (1–2 W).

## 2026-11-17 · Açık kaynak (MIT) ve commit e-postası info@hamza.tr
- Kullanıcı kararı: GitHub'da public. Depoda gizli bilgi yok (sunucu IP'si ve kişisel ayarlar yalnızca
  `~/.config/pc-panel/ayarlar.toml`'da). Lisans MIT; üçüncü taraf dosyalar kendi lisanslarıyla (`THIRD_PARTY.md`).
- Commit geçmişindeki kişisel Gmail adresi `info@hamza.tr` ile değiştirildi (depo henüz hiç push edilmemişti, yani
  geçmişi yeniden yazmak kimseyi etkilemedi). Bu depo için `git config user.email info@hamza.tr`.

## 2026-11-17 · İkonlar dur-bekle ile gönderilir; aynı liste gelince kart sayfayı yeniden kurmaz
- Sorun (kullanıcı fark etti): yeniden bağlanınca yalnızca Steam ikonu kaldı. Kart `apps`/`tiles` ile sayfayı
  kurarken (LVGL kilidi) gelen veri 16 KB seri tamponu taştı; bir ikon bozulunca arkasındakiler de zincirleme
  kayboldu ve yeniden denenmedi.
- Seçenekler: yalnızca tamponu büyütmek · ikonları tek tek, onay bekleyerek göndermek · ikonları kartta saklamak.
- Karar: üçünün en ucuz ikisi birlikte + yeniden kurmayı önlemek. Dur-bekle 10 ikonda ≈2 sn sürüyor (öncekinden
  ≈0,5 sn yavaş) ama bozulan ikon kendiliğinden yeniden geliyor. Tampon 32 KB. Aynı liste gelince kart hiçbir şeyi
  silmiyor, yani bağlantı kopmaları ikonları artık hiç etkilemiyor.

## 2026-11-17 · Karttan Claude izin onayı YAPILMAYACAK
- Önerilmişti: Claude izin isteyince kartta komut + Onayla / Reddet (PermissionRequest hook'u ile).
- Kullanıcı kararı: yapılmayacak. Kart yalnızca haber verir; izinler her zaman bilgisayardan verilir.
  Tekrar önerilmesin.

## 2026-11-17 · Faz 7D: yalnızca günlük kullanılacak iki ek; paneli büyütmeme kuralı
- Kullanıcı uzun özellik listesini istemedi: "günlük olarak kullanabileceğim özellikler". Seçilen: Claude kullanım
  göstergesi ve push edilmemiş iş satırı. Diğer fikirler 7C'de bekliyor; önce bir hafta kullanılıp bakılmayan
  özellikler kaldırılacak.
- **Kullanım:** plan sınırı yerelde yok; uydurma yüzde yerine "son 7 günün en yoğun penceresine göre" gösteriliyor.
  Önbellekten okuma token'ları sayılmıyor (çok büyük, sınırı belirleyen değil). Kayıtlar 600+ MB olabildiği için
  dosya başına okunan konum saklanıyor; ilk tarama ≈1 sn, sonra yalnızca yeni satırlar.
- **Git:** yalnızca son 7 günde dokunulan depolar (eski depolardaki yarım işler sürekli uyarı vermesin). Silinen
  dosyaların zamanı bilinmediği için yalnızca depo yakın zamanda etkinse sayılıyor (eski bir depo yanlışlıkla
  görünüyordu). Ayrı sayfa ya da bildirim yok, yalnızca bir satır.

## 2026-11-17 · Faz 7B: geliştirici paketi — Claude Code, uzun komut, GitHub, sunucular
Kullanıcı yazılımcı; seçtiği dört özellik: 1 Claude Code durumu, 2 uzun komut bildirimi, 3 GitHub, 4 sunucu sağlığı.
- **Dış olaylar için yerel Unix soketi** (`$XDG_RUNTIME_DIR/pc-panel.sock`, 0600) + `pc-panel-olay` aracı.
  Seçenekler: soket · D-Bus servisi · dosya bırakma. Neden: soket en basiti, yalnızca bu kullanıcı erişebiliyor,
  servis kapalıyken araç sessizce çıkıyor. Araç yalnızca standart kütüphaneyi kullanıyor, olay başına ≈13 ms.
- **Claude Code: hook'lar** (`~/.claude/settings.json`, `deploy/claude_hooks.py` ile eklenip kaldırılıyor, önce yedek
  alınıyor). Seçenekler: hook'lar · oturum dosyalarını (transcript) izlemek · süreç listesine bakmak. Neden:
  "izin bekliyor" ve "bitti" bilgisi yalnızca hook'larda var. Gönderilen alanlar: olay adı, oturum kimliği, klasör
  ve bildirim metni; istem ve araç girdileri gönderilmiyor. PostToolUse, izin verildikten sonra durumu "çalışıyor"a
  döndürmek için eklendi; her araç çağrısına ≈13 ms ekliyor. "Bitti" bildirimi yalnızca 20 sn'den uzun işlerde geliyor.
- **İki Claude hesabı:** kullanıcı ikinci hesabı `claude2` (`CLAUDE_CONFIG_DIR=~/.claude-hesap2`) ile açıyor.
  `claude_hooks.py` dizin verilmezse `~/.claude` ve `~/.claude-*` dizinlerinin hepsine kuruyor; varsayılan dışındakilerde
  hook `--hesap <ad>` ile çağrılıyor ve kartta oturum "proje · hesap2" diye görünüyor. Oturum kimlikleri hesaplar
  arasında çakışmadığı için tek liste yeterli. `claude2` uzun komut bildiriminin hariç listesine eklendi.
- **Uzun komut: fish `fish_postexec`** (`~/.config/fish/conf.d/pc-panel.fish`). fish ≥ 5 sn süren her komutu
  bildiriyor; eşik (30 sn) ve hariç tutulan etkileşimli programlar (editörler, ssh, claude…) serviste. Böylece
  ayarlar fish dosyasına dokunmadan değişebiliyor.
- **GitHub: `gh api`.** Ayrı bir anahtar saklanmıyor, gh'nin kendi oturumu kullanılıyor. Depolar yazılmadıysa en son
  push yapılan 6 depo (fork ve arşiv hariç). 2 dk'da bir ≈10 istek (saatte ≈300; sınır 5000). İlk yoklamada
  bildirim yok. Başarı bildirimi yalnızca push / PR / elle başlatılan çalışmalarda (zamanlanmış "Generate Snake" gibi
  işler gürültü yapmasın); başarısızlık her zaman bildiriliyor.
- **Sunucular: HTTP'de 500'den küçük her yanıt "ayakta".** API kökleri 404 dönebiliyor (api.hamza.tr); bu da
  sunucunun cevap verdiğini gösteriyor. Art arda 2 başarısız denetimde "kapalı" sayılıyor. SSL kalan gün 6 saatte bir.
- Kartta yeni 4. sayfa "Geliştirici"; Claude'un bekleyen oturumları üst şeritte ve kilit ekranında da gösteriliyor.

## 2026-11-17 · Faz 7: ayarlar tek bir TOML dosyasında, servis yeniden başlatılmadan uygulanır
- Yer: `~/.config/pc-panel/ayarlar.toml` (örnek `deploy/ayarlar.ornek.toml`; `kur.sh` yoksa kopyalar).
- Seçenekler: TOML · JSON · YAML · kartta ayar ekranı
- Neden: TOML Python 3.12'de hazır (`tomllib`, ek paket yok), yorum yazılabiliyor ve elle düzenlemesi kolay.
  Kartta ayar ekranı yapmak çok daha fazla iş, metin girmek de zor. Dosya 3 sn'de bir yoklanıyor; hatalı dosyada
  son geçerli ayarlarla devam ediliyor.
- Kısayollar kartta değil bilgisayarda tanımlı: kart yalnızca kutu bilgisini (ad, ikon adı, açıklama) alıyor.
  Kart yazılımını yeniden yüklemeden kısayol değişiyor. En çok 12 kutu (4×3); ikonlar sabit bir ad listesinden
  seçiliyor, çünkü ikon glifleri yazı tipine derlenmiş durumda.

## 2026-11-17 · Faz 7: bildirimler D-Bus izleyici (BecomeMonitor) ile okunur
- Seçenekler: `BecomeMonitor` izleyici bağlantısı · kendi bildirim sunucumuz (KDE'ninkinin yerine geçerdi) ·
  `dbus-monitor` alt süreci
- Neden: izleyici bağlantı bildirimlere dokunmuyor, KDE bildirimleri her zamanki gibi çalışıyor. Ek program
  gerektirmiyor (dbus-fast zaten var). Dikkat: izleyici bağlantı mesaj gönderemez. Bu yüzden ileti işleyici
  her zaman `True` döndürüyor, yoksa dbus-fast "bilinmeyen yöntem" yanıtı göndermeye kalkıyor.
- Gizlilik: PC kilitliyken bildirim gönderilmiyor (ayarla açılabilir); hariç tutulan uygulamalar var (varsayılan Spotify).

## 2026-11-17 · Faz 7: hava durumu eklendi, sonra kaldırıldı
- 7A'da Open-Meteo ile eklenmişti (şehir ayar dosyasında). Kullanıcı istemedi ("her yerde bakabilirim"); kart 0.8.0'da
  ve serviste kaldırıldı, yazı tiplerinden hava ikonları çıkarıldı.

## 2026-11-17 · Faz 7: kilit saati — kilitliyken önce saat, süre dolunca karanlık
- Arka ışık yalnızca aç/kapa olduğu için "sönük saat" kısarak değil, siyah zemin ve gri rakamlarla yapılıyor.
- Varsayılan süre 10 dk (`sure_dk`, 0 = sürekli). Kilitliyken dokunma artık paneli değil saati açıyor; yani
  kilitliyken karttan kısayol çalıştırılamıyor (önceden 20 sn panel açılıyordu). Kilit saati kapalıysa eski davranış sürüyor.
- Saat rakamları için ayrı bir 120 px yazı tipi üretildi (yalnızca 0–9 ve ":", ≈ 40 KB).

## 2026-11-17 · Faz 4 arayüz tercihleri (kullanıcı seçti)
- **İçerik (Sistem sayfası):** hepsi. CPU ve GPU yükü ile sıcaklığı; RAM ve VRAM; diskler ve ağ hızı;
  son 60 sn grafikleri.
- **Düzen:** kaydırmalı sayfalar. Sistem, Medya ve Kısayollar ayrı tam ekran sayfalar, sola/sağa kaydırılarak geçiliyor.
  - Diğer seçenekler: tek ekran ikiye bölünmüş · özet ekranı ve ayrıntı sayfaları.
- **Tema:** koyu, sade. Siyaha yakın zemin, tek vurgu rengi, süs yok.
  - Diğer seçenekler: koyu "oyuncu" (neon) · aydınlık.
- **Kısayollar sayfası:** olacak (Faz 7'ye bırakılmadı).

## 2026-11-17 · udev kuralı yazılmadı; kalıcı yol olarak /dev/serial/by-id kullanılıyor
- Seçenekler: `99-pc-panel.rules` ile `/dev/pcpanel` · udev'in zaten oluşturduğu by-id yolu
- Neden: by-id yolu kartın seri numarasını içeriyor ve her takışta aynı kalıyor. Ek kural sudo gerektirirdi ve
  yeni bir şey kazandırmıyordu.

## 2026-11-17 · Servis: systemd kullanıcı servisi, graphical-session.target'a bağlı
- Seçenekler: kullanıcı servisi · sistem servisi · KDE otomatik başlatma (.desktop)
- Neden: medya (MPRIS), ses (wpctl), kilit sorgusu ve kısayollar kullanıcının oturumunu (D-Bus, Wayland) istiyor.
  Bu yüzden sistem servisi olamaz. systemd kullanıcı ortamında `WAYLAND_DISPLAY`, `DISPLAY` ve `DBUS_SESSION_BUS_ADDRESS` var
  (Plasma systemd ile başlıyor). Çöküşte 3 sn sonra yeniden başlıyor; günlük `journalctl --user -u pc-panel`.

## 2026-11-17 · Ekran karartma kartta karar verilir
- Kural: `locked` (KDE kilidi) ya da `bye` (servis kapanıyor) ya da 60 sn bağlantı yok → arka ışık kapalı.
  Karanlıkta dokunma, ekranı 20 sn açar ve düğmelere geçmez (üst katmanda siyah perde).
- Neden: bilgisayar uykuya geçince ya da kapanınca servis mesaj gönderemeyebilir. Kartın kendi zaman aşımı her
  durumu kapsıyor; `bye` ise düzgün kapanışta beklemeden karartıyor. Arka ışık bu kartta yalnızca aç/kapa
  (CH422G), kısma yok.

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
- `/dev/serial/by-id/usb-1a86_USB_Single_Serial_<seri>-if00` (platformio.ini'de `upload_port`/`monitor_port`)
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
