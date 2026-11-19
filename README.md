# PC Panel

**Waveshare ESP32-S3-Touch-LCD-4.3** (800×480, kapasitif dokunmatik) kartını bilgisayarın yanında duran bir
durum + kontrol paneline çeviren proje. Bilgisayarda çalışan bir Python servisi (**Linux / KDE Plasma** ya da
**Windows 10/11**) ile karttaki LVGL arayüzü USB üzerinden konuşur. Çift açılışlı (dual boot) bilgisayarda iki
sistemde de aynı kart, aynı kart yazılımıyla çalışır.

*English summary below.*

## Özellikler

| Sayfa | Ne var |
|---|---|
| **Sistem** | CPU / GPU yükü ve sıcaklığı (yay + 60 sn grafik), RAM, VRAM, diskler, ağ, çalışma süresi |
| **Medya** | Çalan şarkı (MPRIS: Spotify, tarayıcı, yerel çalarlar), kapak resmi, ⏮ ⏯ ⏭, ±10 sn, sarma, sistem sesi |
| **Uygulamalar** | 15 uygulamaya kadar hızlı başlatma, gerçek uygulama ikonlarıyla (`.desktop` dosyalarından) |
| **Kısayollar** | 12 kutuya kadar: uygulama, komut, adres, ekran kilidi, mikrofon / ses kapatma, ekran görüntüsü, makrolar |
| **Geliştirici** | Claude Code oturumları (çalışıyor / izin bekliyor / bitti) ve hesap başına 5 saatlik kullanım, GitHub Actions + PR'lar, push edilmemiş işler, sunucu / site sağlığı |

Ayrıca: masaüstü bildirimleri karta yansır; 30 sn'den uzun süren terminal komutu (fish) bitince ✓/✗ bildirimi;
sıcaklık / RAM / disk uyarıları; PC kilitliyken büyük saat, süre dolunca ekran kararır. Bütün ayarlar tek bir
TOML dosyasında ve kaydedince servis yeniden başlatılmadan uygulanır.

## Gerekenler

- Kart: Waveshare ESP32-S3-Touch-LCD-4.3 (ESP32-S3, 16 MB flash, 8 MB PSRAM), **USB-UART** girişinden bağlı
- Bilgisayar: Python ≥ 3.12 ve [uv](https://docs.astral.sh/uv/), ayrıca
  - **Linux:** KDE Plasma (kısayollar `kstart`, `spectacle`, `loginctl` kullanır), PipeWire (`wpctl`)
  - **Windows 10/11:** ek bir şey gerekmez (medya, ses, bildirimler Windows API'lerinden). CPU sıcaklığı için
    isteğe bağlı [LibreHardwareMonitor](https://github.com/LibreHardwareMonitor/LibreHardwareMonitor) açık olmalı.
  - NVIDIA GPU isteğe bağlı (NVML), yoksa GPU kutusu boş kalır.
- Kart yazılımı için [PlatformIO](https://platformio.org/) (`pio`)
- İsteğe bağlı: `gh` (GitHub sayfası), fish (uzun komut bildirimi), Claude Code (Geliştirici sayfası), `rsvg-convert` (SVG ikonlar)

## Kurulum

```bash
git clone https://github.com/hamer1818/pc-panel.git && cd pc-panel

# 1) Kart yazılımı (yazı tipleri depoda hazır; yeniden üretmek için firmware/tools/fontlari_uret.sh)
cd firmware && pio run -t upload && cd ..

# 2) Bilgisayar servisi: önce elle dene, sonra kalıcı kur (sudo gerekmez)
cd host && uv sync && uv run pc-panel --konsol   # karta göndermeden değerleri gösterir; Ctrl+C
cd .. && deploy/kur.sh                            # systemd kullanıcı servisi + ayar dosyası + fish + Claude hook'ları
```

Kartın seri portu USB kimliğiyle (CH343, `1a86:55d3`) kendiliğinden bulunur. Bilgisayarda başka seri cihazlar
varsa yükleme portunu `firmware/kart.local.ini` dosyasına yaz (örnek `firmware/platformio.ini` içinde).

Kaldırmak için: `deploy/kur.sh kaldir` ve `deploy/claude_hooks.py kaldir`.

### Windows

```powershell
git clone https://github.com/hamer1818/pc-panel.git; cd pc-panel
cd host; uv sync; uv run pc-panel --konsol; cd ..           # önce elle dene; Ctrl+C
powershell -ExecutionPolicy Bypass -File deploy\kur.ps1     # Görev Zamanlayıcı (yönetici gerekmez) + ayarlar + Claude hook'ları
```

Windows 11'de denendi ve kararlı çalışıyor (Ryzen 7 9800X3D + RTX 5080, aynı kart CachyOS ile çift açılışta).
Kart Windows'un kendi sürücüsüyle `COMn` olarak görünür ve kendiliğinden bulunur. Servis oturum açılınca penceresiz
başlar; günlük `%LOCALAPPDATA%\pc-panel\pc-panel.log`. `-PowerShell` eklenirse PowerShell'de uzun süren komutlar
bitince bildirim gelir. Kaldırmak için: `deploy\kur.ps1 kaldir`.
Uygulamalar sayfasına yazılabilecek adlar: `uv run pc-panel --uygulamalar`.

## Ayarlar

Linux `~/.config/pc-panel/ayarlar.toml` — açıklamalı örnek: [`deploy/ayarlar.ornek.toml`](deploy/ayarlar.ornek.toml).
Windows `%APPDATA%\pc-panel\ayarlar.toml` — örnek: [`deploy/ayarlar.ornek.windows.toml`](deploy/ayarlar.ornek.windows.toml).
Denetlemek için: `cd host && uv run pc-panel --ayar-kontrol`. Günlük: `journalctl --user -u pc-panel -f` (Linux).

Kendi betiklerinden karta bildirim: `host/.venv/bin/pc-panel-olay bildir "Başlık" "Gövde"`.

## Gizlilik

Her şey yerelde çalışır. Dışarıya giden istekler yalnızca senin açtıkların: kapak resimleri (çaların verdiği
adres), `gh api` (GitHub sayfası) ve ayar dosyasına yazdığın sunuculara sağlık denetimi. Claude Code hook'ları
yalnızca olay adı, oturum kimliği, klasör ve bildirim metnini yerel bir Unix soketinden servise iletir; istemler
ve araç girdileri gönderilmez. Kullanım göstergesi konuşma kayıtlarından yalnızca token sayılarını okur.

## Belgeler

- [docs/02-mimari.md](docs/02-mimari.md) — mimari ve seri protokol (satır başına JSON + ikili bloklar)
- [docs/01-donanim.md](docs/01-donanim.md) — kart notları, pinler, fabrika yazılımını geri yükleme
- [docs/kararlar.md](docs/kararlar.md) — alınan kararlar ve nedenleri
- [docs/00-plan.md](docs/00-plan.md), [docs/gunluk.md](docs/gunluk.md) — geliştirme planı ve günlüğü

```
firmware/   ESP32-S3 yazılımı (PlatformIO, Arduino 3.1, LVGL 8.4, ESP32_Display_Panel)
host/       bilgisayar servisi (Python, uv) — pc_panel/
deploy/     systemd servisi, kurulum betiği, örnek ayarlar, fish eklentisi, Claude Code hook kurulumu
docs/       belgeler (Türkçe)
```

## Lisans

MIT — bkz. [LICENSE](LICENSE). Yazı tipleri ve bazı kart dosyaları kendi lisanslarını korur: [THIRD_PARTY.md](THIRD_PARTY.md).

---

## English

PC Panel turns a **Waveshare ESP32-S3-Touch-LCD-4.3** board into a desk-side status and control panel for a
Linux (KDE Plasma) PC. A Python service on the PC talks to an LVGL UI on the board over USB serial
(newline-delimited JSON plus binary blocks for album art and app icons).

**Pages:** System (CPU/GPU load and temperature with 60 s charts, RAM, VRAM, disks, network) · Media (MPRIS now
playing, album art, transport controls, seek, volume) · Apps (launcher with real app icons from `.desktop` files)
· Shortcuts (commands, URLs, lock screen, mic/mute toggles, macros) · Developer (Claude Code sessions and per-account
5-hour usage, GitHub Actions and PRs, unpushed work, server/site health). Also mirrors desktop notifications,
notifies when long fish commands finish, shows temperature/RAM/disk warnings and a clock while the PC is locked.

**Requirements:** the board above (connected via its USB-UART port), Linux with KDE Plasma and PipeWire **or**
Windows 10/11, Python ≥ 3.12 with `uv`, PlatformIO. Optional: NVIDIA GPU (NVML), `gh`, fish, Claude Code,
`rsvg-convert`; on Windows, LibreHardwareMonitor for CPU temperature.
**Windows:** `uv sync` in `host/`, then `powershell -ExecutionPolicy Bypass -File deploy\kur.ps1` (per-user
Task Scheduler task, no admin). Config: `%APPDATA%\pc-panel\ayarlar.toml`, log: `%LOCALAPPDATA%\pc-panel\pc-panel.log`.

**Install:** see the commands in *Kurulum* above — `pio run -t upload` in `firmware/`, `uv sync` in `host/`, then
`deploy/kur.sh` (user-level systemd service, no sudo). Configuration lives in `~/.config/pc-panel/ayarlar.toml`
(commented example in `deploy/ayarlar.ornek.toml`). Documentation and UI text are in Turkish; code identifiers are
in English.

**License:** MIT, see `LICENSE`; third-party fonts and files: `THIRD_PARTY.md`.
