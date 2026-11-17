/*
 * PC Panel — kart yazılımı
 *
 * Bilgisayardan seri port (CH343, 921600 baud) ile gelen JSON satırlarını okur, ekranda gösterir;
 * dokunmatik arayüzden bilgisayara komut gönderir. Protokol v1.1: ../docs/02-mimari.md
 * Arayüz (Faz 4): ui.cpp — Sistem · Medya · Kısayollar.
 *
 * Kart başlatma kodu ESP32_Display_Panel v1.0.4 "lvgl_v8_port" örneğinden alınmıştır (CC0-1.0).
 */

#include <Arduino.h>
#include <ArduinoJson.h>
#include <esp_display_panel.hpp>
#include <esp_heap_caps.h>
#include <esp_rom_crc.h>
#include <lvgl.h>

#include "lvgl_v8_port.h"
#include "ui.h"

using namespace esp_panel::drivers;
using namespace esp_panel::board;

#define FW_VERSION "0.5.0"
#define PROTO_VERSION 1
#define LINK_BAUD 921600
#define LINK_TIMEOUT_MS 3000
#define HEARTBEAT_MS 1000
#define LINE_MAX 2048
#define ART_W 240
#define ART_H 240
#define ART_BYTES (ART_W * ART_H * 2)
#define ART_TIMEOUT_MS 2000

static char line_buf[LINE_MAX];
static size_t line_len = 0;
static bool line_overflow = false;
static uint32_t last_rx_ms = 0;
static uint32_t rx_count = 0;

// Kapak resmi: biri alınırken öteki gösterilen iki PSRAM tamponu (bkz. docs/02-mimari.md "Kapak resmi")
static uint8_t *art_rx = nullptr;     // alınmakta olan
static uint8_t *art_show = nullptr;   // ekranda gösterilen
static size_t art_need = 0;           // >0 ise ikili alım modundayız
static size_t art_got = 0;
static uint32_t art_crc = 0;
static uint32_t art_deadline = 0;

// UI'dan (LVGL görevi) ve loop()'tan çağrılabilir; tek printf çağrısı = tek yazma, satırlar karışmaz.
void link_send_cmd(const char *cmd, int value, bool has_value)
{
    if (has_value) {
        Serial.printf("{\"t\":\"cmd\",\"c\":\"%s\",\"v\":%d}\n", cmd, value);
    } else {
        Serial.printf("{\"t\":\"cmd\",\"c\":\"%s\"}\n", cmd);
    }
}

// Kısayol kimliği sabit listeden gelir (ui.cpp), serbest metin değildir
void link_send_shortcut(const char *id)
{
    Serial.printf("{\"t\":\"cmd\",\"c\":\"shortcut\",\"id\":\"%s\"}\n", id);
}

static void handle_line(char *line, size_t len)
{
    if (line[0] != '{') {
        return;  // JSON değil (ör. açılıştaki bozuk ROM çıktısı)
    }
    JsonDocument doc;
    if (deserializeJson(doc, line, len) != DeserializationError::Ok) {
        return;
    }
    const char *t = doc["t"] | "";
    JsonObjectConst o = doc.as<JsonObjectConst>();

    lvgl_port_lock(-1);
    if (strcmp(t, "stat") == 0) {
        ui_update_stat(o);
    } else if (strcmp(t, "media") == 0) {
        ui_update_media(o);
    } else if (strcmp(t, "vol") == 0) {
        ui_update_vol(o);
    } else if (strcmp(t, "art") == 0) {
        size_t n = doc["n"] | 0;
        if (n == 0) {
            ui_clear_art();
        } else if (n == ART_BYTES && (doc["w"] | 0) == ART_W && (doc["h"] | 0) == ART_H && art_rx) {
            art_need = n;  // bu satırdan sonraki n bayt ikili veri
            art_got = 0;
            art_crc = doc["crc"] | 0UL;
            art_deadline = millis() + ART_TIMEOUT_MS;
        } else {
            Serial.println("{\"t\":\"art\",\"ok\":0}");  // beklenmeyen boyut
        }
    }
    lvgl_port_unlock();

    last_rx_ms = millis();
    rx_count++;
}

static void finish_art()
{
    uint32_t crc = esp_rom_crc32_le(0, art_rx, art_need);
    bool ok = crc == art_crc;
    if (ok) {
        lvgl_port_lock(-1);
        uint8_t *tmp = art_show;  // tamponları değiştir: LVGL yarım resim çizmez
        art_show = art_rx;
        art_rx = tmp;
        ui_set_art(art_show, ART_W, ART_H);
        lvgl_port_unlock();
    }
    Serial.printf("{\"t\":\"art\",\"ok\":%d}\n", ok ? 1 : 0);
    art_need = 0;
}

static void poll_serial()
{
    while (Serial.available() > 0) {
        if (art_need) {  // ikili alım modu
            size_t avail = Serial.available();
            size_t want = art_need - art_got;
            art_got += Serial.read(art_rx + art_got, avail < want ? avail : want);
            art_deadline = millis() + ART_TIMEOUT_MS;  // veri geldikçe süre uzar (hareketsizlik zaman aşımı)
            if (art_got >= art_need) {
                finish_art();
            }
            continue;
        }
        int c = Serial.read();
        if (c == '\n') {
            if (!line_overflow && line_len > 0) {
                line_buf[line_len] = 0;
                handle_line(line_buf, line_len);
            }
            line_len = 0;
            line_overflow = false;
        } else if (c != '\r') {
            if (line_len < LINE_MAX - 1) {
                line_buf[line_len++] = static_cast<char>(c);
            } else {
                line_overflow = true;  // çok uzun satır: sonuna kadar at
            }
        }
    }
    if (art_need && static_cast<int32_t>(millis() - art_deadline) > 0) {
        Serial.printf("# kapak zaman asimi (%u / %u bayt)\n", static_cast<unsigned>(art_got),
                      static_cast<unsigned>(art_need));
        Serial.println("{\"t\":\"art\",\"ok\":0}");
        art_need = 0;  // satır moduna dön
    }
}

void setup()
{
    Serial.setRxBufferSize(16384);
    Serial.begin(LINK_BAUD);
    Serial.println("# pc-panel basliyor");

    art_rx = static_cast<uint8_t *>(heap_caps_malloc(ART_BYTES, MALLOC_CAP_SPIRAM));
    art_show = static_cast<uint8_t *>(heap_caps_malloc(ART_BYTES, MALLOC_CAP_SPIRAM));
    if (!art_rx || !art_show) {
        Serial.println("# HATA: kapak tamponlari ayrilamadi");
        art_rx = nullptr;  // kapak özelliği kapalı, panel çalışmaya devam eder
    }

    Board *board = new Board();
    board->init();
#if LVGL_PORT_AVOID_TEARING_MODE
    auto lcd = board->getLCD();
    lcd->configFrameBufferNumber(LVGL_PORT_DISP_BUFFER_NUM);
#if ESP_PANEL_DRIVERS_BUS_ENABLE_RGB && CONFIG_IDF_TARGET_ESP32S3
    auto lcd_bus = lcd->getBus();
    if (lcd_bus->getBasicAttributes().type == ESP_PANEL_BUS_TYPE_RGB) {
        static_cast<BusRGB *>(lcd_bus)->configRGB_BounceBufferSize(lcd->getFrameWidth() * 10);
    }
#endif
#endif
    if (!board->begin()) {
        Serial.println("# HATA: board->begin() basarisiz");
        while (true) {
            delay(1000);
        }
    }
    lvgl_port_init(board->getLCD(), board->getTouch());

    lvgl_port_lock(-1);
    ui_create();
    lvgl_port_unlock();

    Serial.printf("{\"t\":\"hello\",\"fw\":\"%s\",\"proto\":%d}\n", FW_VERSION, PROTO_VERSION);
}

void loop()
{
    poll_serial();

    static uint32_t last_hb = 0;
    static uint32_t last_ui = 0;
    static bool shown_ok = false;
    uint32_t now = millis();

    if (now - last_hb >= HEARTBEAT_MS) {
        last_hb = now;
        Serial.printf("{\"t\":\"hb\",\"up\":%lu,\"fw\":\"%s\"}\n", static_cast<unsigned long>(now / 1000), FW_VERSION);
    }

    if (now - last_ui >= 250) {
        last_ui = now;
        bool ok = last_rx_ms != 0 && now - last_rx_ms < LINK_TIMEOUT_MS;
        if (ok != shown_ok) {  // yalnızca durum değişince ekrana dokun
            lvgl_port_lock(-1);
            ui_set_link(ok);
            lvgl_port_unlock();
        }
        shown_ok = ok;
    }

    delay(2);
}
