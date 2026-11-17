/*
 * PC Panel — kart yazılımı
 *
 * Faz 3: bilgisayardan seri port (CH343, 921600 baud) ile gelen JSON satırlarını okur, ekranda gösterir;
 * medya düğmelerine basılınca bilgisayara komut gönderir. Protokol: ../docs/02-mimari.md
 *
 * Kart başlatma kodu ESP32_Display_Panel v1.0.4 "lvgl_v8_port" örneğinden alınmıştır (CC0-1.0).
 */

#include <Arduino.h>
#include <ArduinoJson.h>
#include <esp_display_panel.hpp>
#include <lvgl.h>

#include "lvgl_v8_port.h"
#include "ui.h"

using namespace esp_panel::drivers;
using namespace esp_panel::board;

#define FW_VERSION "0.3.0"
#define PROTO_VERSION 1
#define LINK_BAUD 921600
#define LINK_TIMEOUT_MS 3000
#define HEARTBEAT_MS 1000
#define LINE_MAX 2048

static char line_buf[LINE_MAX];
static size_t line_len = 0;
static bool line_overflow = false;
static uint32_t last_rx_ms = 0;
static uint32_t rx_count = 0;

// UI'dan (LVGL görevi) ve loop()'tan çağrılabilir; tek printf çağrısı = tek yazma, satırlar karışmaz.
void link_send_cmd(const char *cmd, int value, bool has_value)
{
    if (has_value) {
        Serial.printf("{\"t\":\"cmd\",\"c\":\"%s\",\"v\":%d}\n", cmd, value);
    } else {
        Serial.printf("{\"t\":\"cmd\",\"c\":\"%s\"}\n", cmd);
    }
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
    }
    lvgl_port_unlock();

    last_rx_ms = millis();
    rx_count++;
}

static void poll_serial()
{
    while (Serial.available() > 0) {
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
}

void setup()
{
    Serial.setRxBufferSize(16384);
    Serial.begin(LINK_BAUD);
    Serial.println("# pc-panel basliyor");

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
    ui_set_link(false, 0);
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
        if (ok || shown_ok) {  // bağlıyken sayaç güncellensin; kopunca bir kez "bağlantı yok" yazılsın
            lvgl_port_lock(-1);
            ui_set_link(ok, rx_count);
            lvgl_port_unlock();
        }
        shown_ok = ok;
    }

    delay(2);
}
