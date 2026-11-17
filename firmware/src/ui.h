#pragma once
/*
 * Faz 3 geçici arayüzü: gelen değerleri sade biçimde gösterir, medya düğmeleriyle komut gönderir.
 * Bütün ui_* fonksiyonları LVGL kilidi (lvgl_port_lock) alınmışken çağrılmalı.
 */
#include <ArduinoJson.h>

void ui_create();
void ui_set_link(bool ok, uint32_t rx_count);
void ui_update_stat(JsonObjectConst o);
void ui_update_media(JsonObjectConst o);

// main.cpp'de tanımlı: karttan bilgisayara komut gönderir
void link_send_cmd(const char *cmd, int value, bool has_value);
