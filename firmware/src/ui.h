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

// main.cpp'de tanımlı: karttan bilgisayara komut gönderir
void link_send_cmd(const char *cmd, int value, bool has_value);
void link_send_shortcut(const char *id);
