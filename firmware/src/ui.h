#pragma once
/*
 * PC Panel arayüzü (Faz 4): Sistem · Medya · Kısayollar, kaydırmalı sayfalar.
 * Tasarım: docs/tasarim/taslak-v1.html (onaylandı 2026-11-17).
 * Bütün ui_* fonksiyonları LVGL kilidi (lvgl_port_lock) alınmışken çağrılmalı.
 */
#include <ArduinoJson.h>

void ui_create();
void ui_set_link(bool ok);
void ui_update_stat(JsonObjectConst o);
void ui_update_media(JsonObjectConst o);
void ui_update_vol(JsonObjectConst o);
// Kapak resmi: RGB565 (küçük uçlu) w×h piksel; veri, yeni çağrıya kadar geçerli kalmalı
void ui_set_art(const uint8_t *rgb565, int w, int h);
void ui_clear_art();
// Ekran karartma: true → üst katmana dokunmayı yakalayan siyah perde; dokunulunca uyandırma isteği oluşur
void ui_set_sleep(bool dark);
bool ui_take_wake_request();  // loop() çağırır; istek varsa true döner ve isteği siler

// Faz 7 (protokol v1.4)
void ui_set_tiles(JsonArrayConst items);  // kısayol kutuları (en çok 12); boş liste → yerleşik varsayılanlar
void ui_show_notif(const char *app, const char *title, const char *body, const char *lvl, uint32_t ms);
bool ui_set_warn(const char *text);       // "" → uyarı yok; yeni bir uyarı başladıysa true döner
// Faz 7B (protokol v1.5): Geliştirici sayfası
void ui_update_cc(JsonObjectConst o);   // Claude Code oturumları (+ üst şerit / kilit ekranı göstergesi)
void ui_update_gh(JsonObjectConst o);   // GitHub Actions, PR, bildirim
void ui_update_srv(JsonObjectConst o);  // sunucu sağlığı
void ui_update_cu(JsonObjectConst o);   // Claude kullanımı (hesap başına 5 sa penceresi)
void ui_update_git(JsonObjectConst o);  // push / commit edilmemiş iş
// Faz 7E (protokol v1.7): Uygulamalar sayfası
void ui_set_hw(JsonObjectConst o);       // CPU / GPU adları
void ui_set_apps(JsonArrayConst items);  // [{"id","ti"}], en çok 15; ikonlar sonra gelir
void ui_set_app_icon(int index, const uint8_t *rgb565a8, int w, int h);  // veriyi kopyalar
void ui_set_lock_clock(bool on);          // PC kilitliyken büyük saat ekranı

// main.cpp'de tanımlı: karttan bilgisayara komut gönderir
void link_send_cmd(const char *cmd, int value, bool has_value);
void link_send_shortcut(const char *id);
void link_send_app(const char *id);
