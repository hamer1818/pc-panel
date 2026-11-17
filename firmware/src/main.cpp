/*
 * PC Panel — Faz 1 test ekranı
 *
 * Amaç: ekranın (ST7262 RGB), dokunmatiğin (GT911) ve LVGL'nin düzgün çalıştığını görmek.
 *  - Üstte başlık ve sürümler
 *  - Renk çubukları (renk sırası / bit hatası var mı?)
 *  - Dokunulan yerde imleç + koordinat (eksenler doğru mu?)
 *  - Sayaçlı düğme (dokunma olayları çalışıyor mu?)
 *  - Sürekli dönen yay ve çalışma süresi (titreme / kayma var mı?)
 *  - Sağ altta LVGL FPS/CPU göstergesi
 *
 * Not: LVGL'nin hazır Montserrat yazı tiplerinde Türkçe harf yok; ekrandaki metinler bu yüzden
 * şimdilik ASCII. Türkçe yazı tipi Faz 4'te eklenecek.
 *
 * Kart başlatma kodu ESP32_Display_Panel v1.0.4 "lvgl_v8_port" örneğinden alınmıştır (CC0-1.0).
 */

#include <Arduino.h>
#include <esp_display_panel.hpp>
#include <lvgl.h>
#include "lvgl_v8_port.h"

using namespace esp_panel::drivers;
using namespace esp_panel::board;

static lv_obj_t *cursor_dot;
static lv_obj_t *touch_label;
static lv_obj_t *count_label;
static lv_obj_t *uptime_label;
static lv_obj_t *spin_arc;
static uint32_t tap_count = 0;

// Ekrana dokunuldukça imleci taşı ve koordinatı yaz
static void screen_touch_cb(lv_event_t *e)
{
    lv_indev_t *indev = lv_indev_get_act();
    if (indev == nullptr) {
        return;
    }
    lv_point_t p;
    lv_indev_get_point(indev, &p);
    lv_obj_clear_flag(cursor_dot, LV_OBJ_FLAG_HIDDEN);
    lv_obj_set_pos(cursor_dot, p.x - 15, p.y - 15);
    lv_label_set_text_fmt(touch_label, "Touch: x=%d  y=%d", p.x, p.y);

    if (lv_event_get_code(e) == LV_EVENT_PRESSED) {
        Serial.printf("[touch] x=%d y=%d\n", p.x, p.y);
    }
}

static void button_cb(lv_event_t *e)
{
    tap_count++;
    lv_label_set_text_fmt(count_label, "Taps: %lu", (unsigned long)tap_count);
    Serial.printf("[button] taps=%lu\n", (unsigned long)tap_count);
}

// Her 50 ms: yayı döndür; her saniye: çalışma süresini güncelle
static void tick_cb(lv_timer_t *t)
{
    static uint16_t angle = 0;
    static uint32_t last_sec = UINT32_MAX;

    angle = (angle + 6) % 360;
    lv_arc_set_angles(spin_arc, angle, angle + 90);

    uint32_t sec = millis() / 1000;
    if (sec != last_sec) {
        last_sec = sec;
        lv_label_set_text_fmt(uptime_label, "Uptime: %02lu:%02lu:%02lu  |  Free PSRAM: %u KB  |  Free SRAM: %u KB",
                              (unsigned long)(sec / 3600), (unsigned long)(sec / 60 % 60), (unsigned long)(sec % 60),
                              (unsigned)(heap_caps_get_free_size(MALLOC_CAP_SPIRAM) / 1024),
                              (unsigned)(heap_caps_get_free_size(MALLOC_CAP_INTERNAL) / 1024));
    }
}

static lv_obj_t *make_plain_box(lv_obj_t *parent, int x, int y, int w, int h, lv_color_t color)
{
    lv_obj_t *o = lv_obj_create(parent);
    lv_obj_remove_style_all(o);
    lv_obj_set_style_bg_color(o, color, 0);
    lv_obj_set_style_bg_opa(o, LV_OPA_COVER, 0);
    lv_obj_set_pos(o, x, y);
    lv_obj_set_size(o, w, h);
    lv_obj_clear_flag(o, LV_OBJ_FLAG_CLICKABLE);  // dokunma ekrana geçsin
    return o;
}

static void create_test_ui()
{
    lv_obj_t *scr = lv_scr_act();
    lv_obj_set_style_bg_color(scr, lv_color_hex(0x101418), 0);
    lv_obj_clear_flag(scr, LV_OBJ_FLAG_SCROLLABLE);
    lv_obj_add_event_cb(scr, screen_touch_cb, LV_EVENT_PRESSED, nullptr);
    lv_obj_add_event_cb(scr, screen_touch_cb, LV_EVENT_PRESSING, nullptr);

    // Başlık
    lv_obj_t *title = lv_label_create(scr);
    lv_label_set_text(title, "PC Panel - Faz 1 test");
    lv_obj_set_style_text_font(title, &lv_font_montserrat_30, 0);
    lv_obj_set_style_text_color(title, lv_color_white(), 0);
    lv_obj_set_pos(title, 20, 14);

    lv_obj_t *ver = lv_label_create(scr);
    lv_label_set_text_fmt(ver, "ESP32_Display_Panel %d.%d.%d  |  LVGL %d.%d.%d  |  Arduino %d.%d.%d",
                          ESP_PANEL_VERSION_MAJOR, ESP_PANEL_VERSION_MINOR, ESP_PANEL_VERSION_PATCH,
                          LVGL_VERSION_MAJOR, LVGL_VERSION_MINOR, LVGL_VERSION_PATCH,
                          ESP_ARDUINO_VERSION_MAJOR, ESP_ARDUINO_VERSION_MINOR, ESP_ARDUINO_VERSION_PATCH);
    lv_obj_set_style_text_font(ver, &lv_font_montserrat_14, 0);
    lv_obj_set_style_text_color(ver, lv_color_hex(0x9aa4ad), 0);
    lv_obj_set_pos(ver, 22, 54);

    // Renk çubukları: kırmızı, yeşil, mavi, beyaz, sarı, camgöbeği, eflatun, siyah
    const uint32_t colors[] = {0xFF0000, 0x00FF00, 0x0000FF, 0xFFFFFF, 0xFFFF00, 0x00FFFF, 0xFF00FF, 0x000000};
    const char *names[] = {"R", "G", "B", "W", "Y", "C", "M", "K"};
    for (int i = 0; i < 8; i++) {
        lv_obj_t *box = make_plain_box(scr, 20 + i * 95, 84, 90, 60, lv_color_hex(colors[i]));
        lv_obj_t *l = lv_label_create(box);
        lv_label_set_text(l, names[i]);
        lv_obj_set_style_text_color(l, (i == 3 || i == 4 || i == 5) ? lv_color_black() : lv_color_white(), 0);
        lv_obj_center(l);
    }

    // Gri tonlama geçişi (renk derinliği / bant kontrolü)
    for (int i = 0; i < 32; i++) {
        uint8_t v = i * 255 / 31;
        make_plain_box(scr, 20 + i * 23, 152, 23, 24, lv_color_make(v, v, v));
    }

    // Kenar çerçevesi: ekranın 4 kenarının tam görünüp görünmediği
    lv_obj_t *frame = lv_obj_create(scr);
    lv_obj_remove_style_all(frame);
    lv_obj_set_size(frame, 800, 480);
    lv_obj_set_pos(frame, 0, 0);
    lv_obj_set_style_border_color(frame, lv_color_hex(0xFF8800), 0);
    lv_obj_set_style_border_width(frame, 2, 0);
    lv_obj_clear_flag(frame, LV_OBJ_FLAG_CLICKABLE);

    // Sayaçlı düğme
    lv_obj_t *btn = lv_btn_create(scr);
    lv_obj_set_size(btn, 220, 90);
    lv_obj_set_pos(btn, 20, 200);
    lv_obj_add_event_cb(btn, button_cb, LV_EVENT_CLICKED, nullptr);
    lv_obj_t *btn_label = lv_label_create(btn);
    lv_label_set_text(btn_label, LV_SYMBOL_PLAY "  Press me");
    lv_obj_set_style_text_font(btn_label, &lv_font_montserrat_24, 0);
    lv_obj_center(btn_label);

    count_label = lv_label_create(scr);
    lv_label_set_text(count_label, "Taps: 0");
    lv_obj_set_style_text_font(count_label, &lv_font_montserrat_24, 0);
    lv_obj_set_style_text_color(count_label, lv_color_white(), 0);
    lv_obj_set_pos(count_label, 20, 300);

    touch_label = lv_label_create(scr);
    lv_label_set_text(touch_label, "Touch: -");
    lv_obj_set_style_text_font(touch_label, &lv_font_montserrat_24, 0);
    lv_obj_set_style_text_color(touch_label, lv_color_hex(0x7fd1ff), 0);
    lv_obj_set_pos(touch_label, 20, 336);

    lv_obj_t *hint = lv_label_create(scr);
    lv_label_set_text(hint, "Touch anywhere: the white dot should be under your finger.\n"
                            "Try all four corners.");
    lv_obj_set_style_text_color(hint, lv_color_hex(0x9aa4ad), 0);
    lv_obj_set_pos(hint, 20, 376);

    // Dönen yay (akıcılık / titreme testi)
    spin_arc = lv_arc_create(scr);
    lv_obj_set_size(spin_arc, 200, 200);
    lv_obj_set_pos(spin_arc, 560, 200);
    lv_arc_set_bg_angles(spin_arc, 0, 360);
    lv_obj_remove_style(spin_arc, nullptr, LV_PART_KNOB);
    lv_obj_clear_flag(spin_arc, LV_OBJ_FLAG_CLICKABLE);
    lv_obj_set_style_arc_width(spin_arc, 18, LV_PART_MAIN);
    lv_obj_set_style_arc_width(spin_arc, 18, LV_PART_INDICATOR);
    lv_obj_set_style_arc_color(spin_arc, lv_color_hex(0x00c896), LV_PART_INDICATOR);

    uptime_label = lv_label_create(scr);
    lv_label_set_text(uptime_label, "Uptime: -");
    lv_obj_set_style_text_color(uptime_label, lv_color_hex(0x9aa4ad), 0);
    lv_obj_set_pos(uptime_label, 20, 440);

    // İmleç en üstte olsun
    cursor_dot = lv_obj_create(scr);
    lv_obj_remove_style_all(cursor_dot);
    lv_obj_set_size(cursor_dot, 30, 30);
    lv_obj_set_style_radius(cursor_dot, LV_RADIUS_CIRCLE, 0);
    lv_obj_set_style_bg_color(cursor_dot, lv_color_white(), 0);
    lv_obj_set_style_bg_opa(cursor_dot, LV_OPA_80, 0);
    lv_obj_set_style_border_color(cursor_dot, lv_color_hex(0xFF0000), 0);
    lv_obj_set_style_border_width(cursor_dot, 3, 0);
    lv_obj_clear_flag(cursor_dot, LV_OBJ_FLAG_CLICKABLE);
    lv_obj_add_flag(cursor_dot, LV_OBJ_FLAG_HIDDEN);

    lv_timer_create(tick_cb, 50, nullptr);
}

void setup()
{
    Serial.begin(115200);
    Serial.println("\n[pc-panel] Faz 1 test yazilimi basliyor");

    Serial.println("[pc-panel] Kart baslatiliyor");
    Board *board = new Board();
    board->init();
#if LVGL_PORT_AVOID_TEARING_MODE
    auto lcd = board->getLCD();
    // Yırtılma önleme açıkken çerçeve tampon sayısı kart sürücüsünde ayarlanmalı
    lcd->configFrameBufferNumber(LVGL_PORT_DISP_BUFFER_NUM);
#if ESP_PANEL_DRIVERS_BUS_ENABLE_RGB && CONFIG_IDF_TARGET_ESP32S3
    auto lcd_bus = lcd->getBus();
    // PSRAM bant genişliği için "bounce buffer" (SRAM'de bounce_size * 2 bayt * 2 yer kaplar)
    if (lcd_bus->getBasicAttributes().type == ESP_PANEL_BUS_TYPE_RGB) {
        static_cast<BusRGB *>(lcd_bus)->configRGB_BounceBufferSize(lcd->getFrameWidth() * 10);
    }
#endif
#endif
    if (!board->begin()) {
        Serial.println("[pc-panel] HATA: board->begin() basarisiz");
        while (true) {
            delay(1000);
        }
    }

    Serial.println("[pc-panel] LVGL baslatiliyor");
    lvgl_port_init(board->getLCD(), board->getTouch());

    lvgl_port_lock(-1);
    create_test_ui();
    lvgl_port_unlock();

    Serial.printf("[pc-panel] Hazir. PSRAM bos: %u KB, SRAM bos: %u KB\n",
                  (unsigned)(heap_caps_get_free_size(MALLOC_CAP_SPIRAM) / 1024),
                  (unsigned)(heap_caps_get_free_size(MALLOC_CAP_INTERNAL) / 1024));
}

void loop()
{
    delay(1000);
}
