# Mimari

```
┌──────────────────────── Bilgisayar ────────────────────────┐        ┌──────── Kart ────────┐
│ host/ (Python, systemd kullanıcı servisi)                   │        │ firmware/ (LVGL)      │
│  ├─ sistem: psutil, k10temp, NVML (RTX 5080)                │  USB   │  ├─ Sistem sayfası    │
│  ├─ medya : MPRIS (D-Bus) — Spotify, tarayıcı, VLC...       │ ─────► │  ├─ Medya sayfası     │
│  ├─ ses   : PipeWire (wpctl)                                │ ◄───── │  └─ Kısayollar        │
│  └─ bağlantı: seri port, yeniden bağlanma                   │ seri   │  dokunma → komut      │
└─────────────────────────────────────────────────────────────┘        └───────────────────────┘
```

**İki işletim sistemi (2026-11-20):** aynı servis Linux (KDE Plasma) ve Windows 10/11'de çalışır; kart yazılımı ve
protokol ortaktır. İşletim sistemine özgü kısımlar `pc_panel/backend.py`'de seçilir:

| İş | Linux | Windows (`pc_panel/win/`) |
|----|-------|---------------------------|
| Medya + kapak | MPRIS (D-Bus), kapak adresi (https / file://) | GSMTC (`win/media.py`), kapak oturumun akışından |
| Ses / mikrofon | `wpctl` | Core Audio, pycaw (`win/audio.py`) |
| Bildirim yansıtma | D-Bus izleyici | UserNotificationListener, saniyede bir okuma (`win/notify.py`) |
| Uygulamalar | `.desktop` + ikon teması, `kstart` | `shell:AppsFolder` listesi, kabuk ikonu, pencereyi öne getir / aç (`win/apps.py`) |
| Kilit durumu, kilitle, ekran görüntüsü | KDE ScreenSaver, `loginctl`, `spectacle` | giriş masaüstü adı, `LockWorkStation`, Win+PrtScn (`win/session.py`) |
| CPU adı / MHz / sıcaklık | `/proc/cpuinfo`, psutil, `k10temp` | kayıt defteri, PDH sayaçları, LibreHardwareMonitor WMI (`win/sensors.py`) |
| Olay kanalı | `$XDG_RUNTIME_DIR/pc-panel.sock` | `127.0.0.1:47613` (TCP) |
| Kapanışta "bye" | SIGTERM / SIGINT | WM_ENDSESSION (görünmez pencere), Ctrl+C / Ctrl+Break |
| Kalıcı kurulum | systemd kullanıcı servisi (`kur.sh`) | Görev Zamanlayıcı, oturum açılınca `pythonw` (`kur.ps1`) |
| Ayar dosyası | `~/.config/pc-panel/ayarlar.toml` | `%APPDATA%\pc-panel\ayarlar.toml` |
| Seri port | `/dev/serial/by-id/…` (VID:PID ile bulunur) | `COMn` (VID:PID ile bulunur) |

## Bilgisayar servisi (`host/`)
| Dosya | Görev |
|-------|-------|
| `pc_panel/system.py` | `SystemCollector.sample()` — psutil ile CPU, sıcaklık, RAM, disk, ağ, çalışma süresi |
| `pc_panel/gpu.py` | `GpuCollector.sample()` — NVML; GPU yoksa `None` döner |
| `pc_panel/media.py` | `MediaWatcher.poll()` / `.command()` — MPRIS, etkin çalar seçimi ve kontrol |
| `pc_panel/console.py` | Konsol modu görünümü |
| `pc_panel/protocol.py` | Toplanan verileri protokol v1 mesajlarına (`stat`, `media`) çevirir |
| `pc_panel/link.py` | `SerialLink` — seri port, okuma iş parçacığı, yeniden bağlanma |
| `pc_panel/__main__.py` | Komut satırı (`pc-panel`); servis görevleri: üretici, tüketici, bekçi, bildirim izleyici, olay soketi, GitHub, sunucular |
| `pc_panel/config.py` | **Faz 7:** `~/.config/pc-panel/ayarlar.toml` okuma, denetleme, değişince yeniden yükleme (`ConfigWatcher`) |
| `pc_panel/shortcuts.py` | Kısayol adımlarını uygular (uygulama / komut / adres / özel / medya / bekle) |
| `pc_panel/notify.py` | **Faz 7:** D-Bus izleyici bağlantısıyla `Notify` çağrılarını yakalar |
| `pc_panel/olay.py` | **Faz 7B:** `pc-panel-olay` aracı (yalnız standart kütüphane) ve soket yolu |
| `pc_panel/apps.py` | **Faz 7E:** uygulama adı/ikonu bulma, ikonu 64×64 RGB565+alfa'ya çevirme, `kstart` ile başlatma |
| `pc_panel/claude.py` | **Faz 7B:** Claude Code oturum durumları (hook olaylarından) |
| `pc_panel/github.py` | **Faz 7B:** `gh api` ile Actions çalışmaları, PR ve bildirim sayıları, CI geçiş bildirimleri |
| `pc_panel/servers.py` | **Faz 7B:** HTTP / TCP denetimi, SSL kalan gün, kapandı / düzeldi geçişleri |
| `pc_panel/alerts.py` | **Faz 7:** sıcaklık / RAM uyarısı (eşik + 5 birim geri dönüş payı), disk doluluk bildirimi |
| `pc_panel/backend.py` | **Faz 8:** işletim sistemine göre `media` / `audio` / `notify` / `apps` modüllerini seçer |
| `pc_panel/win/` | **Faz 8:** Windows karşılıkları: `media.py`, `audio.py`, `notify.py`, `apps.py`, `session.py`, `sensors.py` (COM, MTA ile başlatılır; `win/__init__.py`) |

## Kart yazılımı (`firmware/src/`)
| Dosya | Görev |
|-------|-------|
| `main.cpp` | Kart/LVGL başlatma, seri satır okuma, JSON ayrıştırma, kalp atışı, bağlantı zaman aşımı |
| `ui.cpp` / `ui.h` | Ekran (Faz 3 geçici arayüzü); düğmeler `link_send_cmd()` ile komut yollar |
| `lvgl_v8_port.*`, `lv_conf.h`, `esp_*_conf.h` | ESP32_Display_Panel örneğinden; yırtılma önleme modu 3 |

LVGL kendi görevinde çalışır. `loop()` içinden ekrana dokunmadan önce `lvgl_port_lock(-1)` alınır.

- **Ölçüm aralığı:** varsayılan 1 sn (`--aralik`).
- **Hız hesapları:** ağ ve disk hızı iki ölçüm arasındaki fark / geçen süre ile bulunur. Sanal ağ arayüzleri
  (lo, tailscale, virbr, docker, veth…) ve disk bölümleri sayılmaz.
- **Etkin çalar kuralı:** çalanlar arasında en son çalmaya başlayan → yoksa en son çalan → yoksa ilk bulunan.
- **MPRIS okuma yöntemi:** her ölçümde `Properties.GetAll` ile yoklama (polling). Sinyal dinleme yok; her çağrıda 1 sn zaman aşımı var.

Çalıştırma (`host/` klasöründe):
```bash
uv run pc-panel            # servis (karta gönderir)
uv run pc-panel --debug    # servis + bütün trafik ve kart günlükleri
uv run pc-panel --konsol   # sadece terminalde göster
```

## Protokol (v1 — Faz 3, v1.1 eklemeleri — Faz 4)

### Bağlantı
- Kart üzerindeki **USB-UART** (CH343) girişi, **921600 baud**, 8N1.
- Bilgisayar kartı USB kimliğiyle (VID:PID `1a86:55d3`, WCH CH343) bulur ve varsa kalıcı
  `/dev/serial/by-id/usb-1a86_USB_Single_Serial_<seri>-if00` yolunu kullanır (`--port` ile değiştirilebilir).
  PlatformIO portu kendisi bulur; bilgisayarda başka seri cihazlar varsa `firmware/*.local.ini` ile sabitlenir.
- ⚠️ **Port açılınca kart resetlenmesin diye DTR ve RTS açık bırakılır** (pyserial varsayılanı). Deneyde ikisi
  kapatılınca kart yeniden başladı, varsayılanla başlamadı (2026-11-17).
- Port **özel (exclusive) modda** açılır. Aynı anda yalnızca bir program bağlanabilir: ikinci bir `pc-panel`
  ya da `pio device monitor` açıksa servis "port kullanılıyor" der ve port boşalınca kendiliğinden bağlanır.
- Her mesaj **tek satır JSON**, `\n` ile biter, en fazla 1 KB (kapak resmi hariç).
- `{` ile başlamayan satırlar günlük (log) sayılır; bilgisayar bunları yok sayar ya da `--debug` ile yazdırır.
  Açılıştaki ROM mesajları 115200 baud'da geldiği için bozuk görünür, bu normaldir.

### Bilgisayar → kart
| Tip | Ne zaman | Alanlar |
|-----|----------|---------|
| `stat` | her 1 sn | `cpu` %, `cpu_t` °C, `cpu_mhz`, `gpu` %, `gpu_t` °C, `gpu_w` W, `gpu_wmax` W, `vram` MB, `vram_tot` MB, `ram` MB, `ram_tot` MB, `disks` `[{"m":"/","p":82.7}]`, `net_dn` / `net_up` B/s, `dsk_r` / `dsk_w` B/s, `up` sn, **v1.1:** `cpu_max` en yoğun çekirdek %, `gpu_fan` %, `swap` %, `clock` "16:09", `date` "17 Kasım Pazartesi" |
| `vol` | her 1 sn (**v1.1**) | `v` sistem sesi % (0–150), `mute` 0/1, `mic` mikrofon sesi %, `mic_mute` 0/1 |
| `media` | her 1 sn | `st` (`play`/`pause`/`stop`/`none`), `ti` başlık, `ar` sanatçı, `al` albüm, `pl` çalar adı, `len` sn, `pos` sn, `can` `{"pp":1,"nx":1,"pv":1,"sk":1}` |

Örnek:
```json
{"t":"stat","cpu":4.1,"cpu_t":46,"cpu_mhz":3581,"gpu":7,"gpu_t":45,"gpu_w":39,"gpu_wmax":360,"vram":2225,"vram_tot":16303,"ram":8510,"ram_tot":31687,"disks":[{"m":"/","p":82.7},{"m":"/mnt/veri","p":42.2}],"net_dn":2650,"net_up":8400,"dsk_r":0,"dsk_w":146000,"up":16409}
{"t":"media","st":"play","ti":"Test Et","ar":"SAS","al":"Yola Çıktık Çoktan","pl":"Spotify","len":161,"pos":66,"can":{"pp":1,"nx":1,"pv":1,"sk":1}}
```

### Kart → bilgisayar
| Tip | Ne zaman | Alanlar |
|-----|----------|---------|
| `hello` | açılışta | `fw` yazılım sürümü, `proto` protokol sürümü (1) |
| `hb` | her 1 sn | `up` kartın çalışma süresi (sn) |
| `cmd` | dokununca | `c`: `play_pause` / `next` / `prev` / `seek_rel` (+ `v` sn) / `seek_abs` (+ `v` sn) / **v1.1:** `vol_set` (+ `v` %) / `shortcut` (+ `id`: `lock`, `mic`, `screenshot`, `mute`, `terminal`, `browser`, `files`, `spotify`) |

### Bağlantı durumu
- Kart: 3 sn boyunca geçerli bir mesaj gelmezse ekranda "bağlantı yok" gösterir.
- Bilgisayar: port kaybolursa (kablo çıktı) 2 sn arayla yeniden açmayı dener. 5 sn boyunca karttan `hb` gelmezse
  bunu günlüğe yazar, ama göndermeye devam eder.

### Ekran karartma (v1.3 — Faz 6)
- `stat` mesajına `locked` (0/1) alanı eklendi (KDE `org.freedesktop.ScreenSaver.GetActive`).
- Yeni mesaj `{"t":"bye"}`: servis kapanırken (SIGTERM / Ctrl+C) gönderilir; kart ekranı hemen karartır.
- Kart kuralları için bkz. `kararlar.md` "Ekran karartma kartta karar verilir".

### Ayar dosyasından gelenler (v1.4 — Faz 7)
Ayar dosyası: `~/.config/pc-panel/ayarlar.toml` (örnek ve açıklamalar `deploy/ayarlar.ornek.toml`). Servis dosyayı
3 sn'de bir yoklar; değişince aşağıdaki mesajları yeniden gönderir. Kart yeniden başlayınca (`hello`) ya da bağlantı
yeniden kurulunca da gönderilir. Denetlemek için: `uv run pc-panel --ayar-kontrol`.

| Tip | Ne zaman | Alanlar |
|-----|----------|---------|
| `tiles` | bağlantı / ayar değişince | `items`: `[{"id":"terminal","ic":"terminal","ti":"Terminal","de":"Konsole","tg":"mic"?}]`, en çok 12. `ic` ikon adı (kartta `ICONS` tablosu), `tg` "mic"/"mute" durum gösteren kutu |
| `cfg` | bağlantı / ayar değişince | `lock_clock` 0/1, `lock_min` dk (0: kararmaz), `notif_s` bildirim süresi sn |
| `notif` | bildirim gelince | `app`, `ti` başlık, `bd` gövde (HTML'den arındırılmış), **v1.5:** `lvl` `info`/`ok`/`err`/`wait` |
| `stat` | her 1 sn | yeni alan `warn`: etkin uyarılar ("CPU 92°C · RAM %96") ya da "" |

Kart → bilgisayar: yeni komut `{"t":"cmd","c":"mute"}` (Medya sayfasındaki ses simgesi; kısayol listesinden bağımsız).
Kısayol kutusu yine `{"c":"shortcut","id":…}` gönderir; bilgisayar kimliği **o anki** ayarlardaki listede arar.

Kart ekran durumu (v1.4):
| Durum | Ne zaman |
|-------|----------|
| panel | normal; ya da karanlıkta dokunma / yeni uyarı sonrası 20 sn |
| kilit saati | PC kilitli ve `lock_clock`=1, kilitlendikten sonra `lock_min` dakika boyunca (dokununca 20 sn daha) |
| karanlık | `bye`, 60 sn bağlantı yok, ya da kilitli ve (kilit saati kapalı ya da süresi doldu) |

Bildirimler kilitliyken varsayılan olarak gönderilmez (`[bildirim] kilitliyken = false`). Aynı bildirim 3 sn içinde
tekrar gelirse yok sayılır. Disk doluluk uyarısı bir `notif` mesajı olarak gider.

### Geliştirici sayfası (v1.5 — Faz 7B)
| Tip | Ne zaman | Alanlar |
|-----|----------|---------|
| `cc` | Claude olayı gelince + 10 sn'de bir | `items` `[{"p":"TulparLang","s":"wait","m":"izin bekliyor","age":12}]` (en çok 5; `s`: `work`/`wait`/`done`/`idle`), `wait` ve `work` sayıları |
| `gh` | `[github] sure_sn` (120 sn) | `ok` 1: `runs` `[{"r":"iurl","w":"Deploy API","s":"fail","b":"main","age":429949}]` (en çok 4; `s`: `ok`/`fail`/`run`/`wait`/`cancel`), `rev` inceleme bekleyen PR, `prs` açık PR'larım, `ntf` okunmamış bildirim · `ok` 0: `err` |
| `srv` | `[sunucular] sure_sn` (60 sn) | `items` `[{"n":"iurl.tr","ok":1,"ms":240,"ssl":61}]` (en çok 8; `ok` 1 ayakta, 0 kapalı, -1 tek başarısızlık) |

**v1.6 (Faz 7D):**
| Tip | Ne zaman | Alanlar |
|-----|----------|---------|
| `cu` | 60 sn'de bir | `acc` `[{"n":"hesap1","txt":"83 K","pct":5,"rst":13978}]` — 5 sa penceresindeki token (girdi + çıktı + önbelleğe yazma), `pct` son 7 günün en yoğun penceresine göre, `rst` sıfırlanmaya sn (-1: pencere yok) |
| `git` | 5 dk'da bir | `txt` hazır satır ("Push bekliyor: tulpar-engine (4) · commit edilmemiş: …"), `n` dikkat isteyen depo sayısı |

**v1.7 (Faz 7E) — Uygulamalar sayfası:**
| Tip | Yön | Alanlar |
|-----|-----|---------|
| `apps` | PC → kart, bağlantı / ayar değişince | `items` `[{"id":"steam","ti":"Steam"}]`, en çok 15 |
| `icon` | PC → kart, `apps`'ın hemen ardından | başlık `{"t":"icon","i":0,"w":64,"h":64,"n":12288,"crc":…}` + 12 288 bayt ikili veri: 64×64 `LV_IMG_CF_TRUE_COLOR_ALPHA` (RGB565 küçük uçlu + alfa, 3 bayt/piksel). Kart yanıtı `{"t":"icon","i":0,"ok":1}` |
| `cmd` `app` | kart → PC | `{"t":"cmd","c":"app","id":"steam"}`; PC kimliği listede arar, `kstart --application <id>` |

İkili alım kapak resmiyle ortak (aynı zaman aşımı ve CRC); ikon ortak bir PSRAM tamponuna alınır, CRC tutunca
kutunun kendi tamponuna kopyalanır. **İkonlar dur-bekle ile gider** (0.10.1): bilgisayar bir ikonu gönderir, kartın
`icon` yanıtını bekler (5 sn), ulaşmadıysa 2 kez daha dener; `apps` mesajından sonra 0,3 sn bekler. Kart aynı `apps`
ya da `tiles` listesi gelirse sayfayı yeniden kurmaz (ikonlar yerinde kalır). Kartın seri alım tamponu 32 KB. 10 ikon ≈ 120 KB, ≈ 1,5 sn. Kaynak: `apps.py` (`.desktop` → `Icon=` →
ikon teması + hicolor + pixmaps; SVG için `rsvg-convert`).

Kaynaklar: `usage.py` (`~/.claude*/projects/**/*.jsonl`, yalnızca eklenen satırlar okunur, içerik okunmaz),
`gitwatch.py` (`[git] klasorler` altındaki depolar, `git --no-optional-locks`).

Sunucu "kapalı" ve SSL < 7 gün uyarıları `stat.warn` alanına eklenir (üst şeritte kırmızı).

#### Olay soketi (dışarıdan servise)
`$XDG_RUNTIME_DIR/pc-panel.sock` (Unix akış soketi, 0600). Her bağlantı tek satır JSON gönderir ve kapanır.
Gönderici: `host/.venv/bin/pc-panel-olay`.
Windows'ta Python Unix soketi açamadığı için aynı satırlar `127.0.0.1:47613` TCP portuna gider (yalnızca bu
bilgisayardan erişilebilir; gönderici `host\.venv\Scripts\pc-panel-olay.exe`, PowerShell eklentisi doğrudan porta yazar).
`pc-panel-olay` stdin'i bayt olarak okur ve UTF-8 BOM'u atar (PowerShell borusu BOM ekleyebiliyor).

| `k` | Kaynak | Alanlar |
|-----|--------|---------|
| `claude` | Claude Code hook'ları (`~/.claude/settings.json`: SessionStart, UserPromptSubmit, PostToolUse, Notification, Stop, SessionEnd) | `ev` olay adı, `sid`, `cwd`, `msg`, `ntype`, `acct` hesap etiketi (`~/.claude-<ad>` dizinlerinden gelen hook'larda `--hesap <ad>`; kartta "proje · ad") (istem metni ve araç girdileri gönderilmez) |
| `cmd` | fish `fish_postexec` / Windows'ta PowerShell `prompt` (`deploy/pc-panel.ps1`) (≥ 5 sn süren komutlar; eşik ve hariç liste serviste) | `cmd`, `ms`, `code` |
| `notif` | `pc-panel-olay bildir "Başlık" "Gövde"` | `title`, `body` |

## Kurulum (Faz 6)
- `deploy/pc-panel.service` → `~/.config/systemd/user/`, `deploy/kur.sh` ile kurulur (`kur.sh kaldir` ile kaldırılır).
- Servis `host/.venv/bin/pc-panel`'i doğrudan çalıştırır (uv gerekmez).
- Günlük: `journalctl --user -u pc-panel -f`. Elle çalıştırmak için önce servisi durdurun:
  `systemctl --user stop pc-panel` (port özel modda açılıyor, aynı anda tek program).

### Windows'ta kurulum (Faz 8)
- `deploy\kur.ps1` (yönetici gerekmez): `uv sync`, `%APPDATA%\pc-panel\ayarlar.toml` (yoksa
  `deploy/ayarlar.ornek.windows.toml`'dan), Claude Code hook'ları, Görev Zamanlayıcı'da **"PC Panel"** görevi:
  oturum açılınca `host\.venv\Scripts\pythonw.exe -m pc_panel --gunluk %LOCALAPPDATA%\pc-panel\pc-panel.log`
  (penceresiz, süre sınırı yok, çökerse 1 dk'da bir yeniden başlar). Görev eklenemezse Başlangıç klasörüne kısayol.
  `-PowerShell` ile uzun komut bildirimi profile eklenir. `kur.ps1 kaldir` hepsini geri alır (hook'lar hariç).
- Günlük 2 MB'ı geçince `pc-panel.log.1` olarak saklanır. Elle çalıştırmak için önce görevi durdurun
  (`Stop-ScheduledTask "PC Panel"`): COM portu Windows'ta da tek programa açılır.
- Alt süreçler (`git`, `gh`, `powershell`, kısayol komutları) `CREATE_NO_WINDOW` ile başlar: pythonw altında her
  yoklamada konsol penceresi yanıp sönmesin.

### Kapak resmi (v1.2 — Faz 5)
Kapak, satır tabanlı protokolün içinde **tek ikili (binary) blok** olarak gider:

1. Başlık satırı: `{"t":"art","w":240,"h":240,"n":115200,"crc":3735928559}`
2. Hemen ardından **tam `n` bayt** ham veri: RGB565, küçük uçlu (little-endian), satır satır, 240×240.
   `crc`, bu baytların standart CRC-32 değeri (Python `zlib.crc32` = ESP32 `esp_rom_crc32_le(0, …)`).
3. Kart veriyi ikinci bir PSRAM tamponuna alır. CRC tutarsa gösterilen tamponla yer değiştirir (yırtılma olmaz).
   Sonra `{"t":"art","ok":1}` (ya da hata için `"ok":0`) ile yanıt verir.
4. Kapak yoksa `{"t":"art","n":0}` gelir; kart yer tutucuyu gösterir.

Kurallar:
- Bilgisayar aynı kapağı ikinci kez göndermez. Kart "merhaba" dediğinde (yeniden başladığında) ya da bağlantı
  yeniden kurulduğunda kapak yeniden gönderilir.
- Kart `"ok":0` derse aynı kapak en fazla 3 kez yeniden denenir.
- Kart, ikili veri 2 sn içinde tamamlanmazsa aktarımı bırakır ve satır moduna döner (kaybolan baytlara karşı).
- Bütün giden mesajlar tek bir **yazıcı iş parçacığından** sırayla yazılır. Böylece kapak verisinin ortasına
  başka bir satır karışmaz ve 115 KB'lık yazma (≈1,3 sn) ana döngüyü bekletmez.
- **(Faz 8)** İkili bloklar (kapak, ikonlar) asla üst üste gönderilmez: biri gider, kartın `ok` yanıtı (en çok 5 sn)
  beklenir, sonra diğeri. Sayfa kuran bir mesajdan (`tiles`, `apps`) sonra 0,5 sn beklenir.
- **(Faz 8, yalnızca Windows)** 4 KB'tan büyük yazmalar 1 KB'lık parçalarla, hattın ~%85'i hızında gider
  (921600 baud'da ≈13 ms / KB; kapak ≈1,5 sn — Linux'taki süreyle aynı). Neden: `kararlar.md` 2026-11-20.
- Kaynaklar: `https://…` (Spotify vb., 5 sn zaman aşımıyla indirilir) ve `file://…` (yerel çalarlar,
  tarayıcıların geçici kapakları). Resim ortadan kare kırpılıp 240×240'a küçültülür.

### Kısayollar güvenliği
Kart yalnızca bir **kısayol kimliği** (`id`) gönderir. Bilgisayar bu kimliği ayar dosyasındaki listeyle eşleştirir
ve oradaki adımları uygular; komutlar kabuk olmadan, argüman listesiyle çalıştırılır. Karttan komut satırı ya da serbest metin çalıştırılamaz;
listede olmayan bir kimlik yok sayılır.
