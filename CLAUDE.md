# PC Panel — Claude için proje kuralları

## Kayıt tutma (zorunlu)
Bu projede yapılan HER şeyin kaydı Markdown dosyalarında tutulur:

1. **Her çalışma oturumunun sonunda** `docs/gunluk.md` dosyasına tarihli bir kayıt ekle:
   ne yapıldı, ne denendi, ne çalışmadı, sıradaki adım.
2. **Plan adımı bitince** `docs/00-plan.md` içindeki kutucuğu `[x]` yap. Plan değişirse
   planı güncelle ve değişikliği günlüğe yaz.
3. **Bir karar alınınca** (kütüphane, port, protokol, tasarım tercihi) `docs/kararlar.md`
   dosyasına ekle: tarih, karar, seçenekler, neden.
4. Donanımla ilgili yeni öğrenilen bilgi (pin, hata, garip davranış) → `docs/01-donanim.md`.
5. Protokol veya mimari değişikliği → `docs/02-mimari.md`.
6. Kullanıcıdan bir şey istenecekse plandaki **[SEN]** adımı olarak yaz, açık komutlarla.

## Çalışma düzeni
- Adımlar `docs/00-plan.md` sırasıyla yürür; bir fazın "bitti ölçütü" sağlanmadan sonrakine geçilmez.
- `sudo` gerektiren her şeyi (paket kurma, udev, grup ekleme) kullanıcı yapar; Claude komutu hazırlar.
- Git commit'leri kullanıcı onayıyla atılır. Commit mesajları Türkçe.
- Dil: dokümanlar ve yorumlar Türkçe; kod içi isimler İngilizce.

## Ortam
- Bilgisayar: çift açılış — CachyOS (Arch), KDE Plasma, PipeWire **ve** Windows 11; Ryzen 7 9800X3D, RTX 5080.
  Servis iki sistemde de çalışmalı: Windows'a özgü kod `host/pc_panel/win/`, seçim `backend.py`. Linux modüllerini
  değiştirirken Windows karşılığını da düşün (ve tersi). Windows'ta kurulum `deploy/kur.ps1`.
- Kart: Waveshare ESP32-S3-Touch-LCD-4.3 (ESP32-S3N8R8). Ayrıntı: `docs/01-donanim.md`.
