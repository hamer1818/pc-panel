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

## Protokol (taslak — Faz 3'te kesinleşecek)
- Bağlantı: USB-UART (CH343), 921600 baud (*denenecek*)
- Metin mesajları: her satır bir JSON nesnesi, `\n` ile biter
- Kapak resmi: başlık satırı + ikili RGB565 veri (200×200 = 80.000 bayt)

| Yön | Tip | Sıklık | Örnek |
|-----|-----|--------|-------|
| PC → kart | `stat` | 1–2 Hz | `{"t":"stat","cpu":23,"cput":61,"gpu":8,"gput":44,"ram":41,...}` |
| PC → kart | `media` | değişince | `{"t":"media","st":"play","ti":"...","ar":"...","len":215,"pos":42}` |
| PC → kart | `vol` | değişince | `{"t":"vol","v":55,"mute":false}` |
| PC → kart | `art` | şarkı değişince | `{"t":"art","w":200,"h":200,"n":80000}` + ikili veri |
| kart → PC | `cmd` | dokununca | `{"t":"cmd","c":"play_pause"}` / `next` / `prev` / `seek` / `vol` |
| iki yön | `hb` | 1 Hz | kalp atışı; 3 sn gelmezse "bağlantı yok" |
