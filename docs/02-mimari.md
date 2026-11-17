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

## Bilgisayar servisi (`host/`)
| Dosya | Görev |
|-------|-------|
| `pc_panel/system.py` | `SystemCollector.sample()` — psutil ile CPU, sıcaklık, RAM, disk, ağ, çalışma süresi |
| `pc_panel/gpu.py` | `GpuCollector.sample()` — NVML; GPU yoksa `None` döner |
| `pc_panel/media.py` | `MediaWatcher.poll()` / `.command()` — MPRIS, etkin çalar seçimi ve kontrol |
| `pc_panel/console.py` | Konsol modu görünümü |
| `pc_panel/protocol.py` | Toplanan verileri protokol v1 mesajlarına (`stat`, `media`) çevirir |
| `pc_panel/link.py` | `SerialLink` — seri port, okuma iş parçacığı, yeniden bağlanma |
| `pc_panel/__main__.py` | Komut satırı (`pc-panel`); varsayılan mod servis: üretici + tüketici + bekçi görevleri |

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
- Bilgisayar portu `/dev/serial/by-id/usb-1a86_USB_Single_Serial_5B90123287-if00` yolundan açar
  (`--port` ile değiştirilebilir; bulunamazsa VID:PID `1a86:55d3` ile aranır).
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

## Kurulum (Faz 6)
- `deploy/pc-panel.service` → `~/.config/systemd/user/`, `deploy/kur.sh` ile kurulur (`kur.sh kaldir` ile kaldırılır).
- Servis `host/.venv/bin/pc-panel`'i doğrudan çalıştırır (uv gerekmez).
- Günlük: `journalctl --user -u pc-panel -f`. Elle çalıştırmak için önce servisi durdurun:
  `systemctl --user stop pc-panel` (port özel modda açılıyor, aynı anda tek program).

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
- Kaynaklar: `https://…` (Spotify vb., 5 sn zaman aşımıyla indirilir) ve `file://…` (yerel çalarlar,
  tarayıcıların geçici kapakları). Resim ortadan kare kırpılıp 240×240'a küçültülür.

### Kısayollar güvenliği
Kart yalnızca bir **kısayol kimliği** (`id`) gönderir. Bilgisayar bu kimliği `pc_panel/shortcuts.py` içindeki sabit
bir listeyle eşleştirir ve oradaki komutu çalıştırır. Karttan komut satırı ya da serbest metin çalıştırılamaz;
listede olmayan bir kimlik yok sayılır.
