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

// main.cpp'de tanımlı: karttan bilgisayara komut gönderir
void link_send_cmd(const char *cmd, int value, bool has_value);
void link_send_shortcut(const char *id);
