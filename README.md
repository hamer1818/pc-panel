# PC Panel

Waveshare ESP32-S3-Touch-LCD-4.3 (800×480, kapasitif dokunmatik) kartını bilgisayarın
yanında duran bir **canlı durum + medya kontrol paneli** yapma projesi.

- Bilgisayar (CachyOS/KDE) → karta: CPU, GPU, RAM, sıcaklık, disk, ağ, çalan şarkı, kapak resmi
- Kart → bilgisayara: oynat/durdur, ileri/geri, ses, sarma, kısayollar

## Klasör yapısı (hedef)

```
esp32-lcd-controller-card/
├── README.md            ← bu dosya
├── CLAUDE.md            ← Claude için proje kuralları (kayıt tutma dahil)
├── docs/
│   ├── 00-plan.md       ← adım adım ana plan, kim ne yapacak, ilerleme kutucukları
│   ├── 01-donanim.md    ← kartın özellikleri, pinler, dikkat edilecekler
│   ├── 02-mimari.md     ← sistem tasarımı ve iletişim protokolü
│   ├── kararlar.md      ← alınan kararlar ve nedenleri
│   └── gunluk.md        ← tarihli geliştirme günlüğü
├── firmware/            ← ESP32-S3 kodu (PlatformIO + LVGL)       [Faz 1'de açılır]
├── host/                ← bilgisayardaki Python servisi            [Faz 2'de açılır]
└── deploy/              ← udev kuralı, systemd servisi, kurulum    [Faz 6'da açılır]
```

## Durum

Şu anki faz ve yapılanlar için: [docs/00-plan.md](docs/00-plan.md) ve [docs/gunluk.md](docs/gunluk.md).
