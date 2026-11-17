/*
 * PC Panel — kart yazılımı
 *
 * Bilgisayardan seri port (CH343, 921600 baud) ile gelen JSON satırlarını okur, ekranda gösterir;
 * dokunmatik arayüzden bilgisayara komut gönderir. Protokol v1.7: ../docs/02-mimari.md
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

#define FW_VERSION "0.10.1"
#define PROTO_VERSION 1
#define LINK_BAUD 921600
#define LINK_TIMEOUT_MS 3000
#define HEARTBEAT_MS 1000
#define LINK_LINE_MAX 4096  // v1.4: 12 kutuluk "tiles" mesajı ≈2 KB
#define ART_W 240
#define ART_H 240
#define ART_BYTES (ART_W * ART_H * 2)
#define ART_TIMEOUT_MS 2000  // ikili blok hareketsizlik zaman aşımı (kapak ve ikonlar)
#define ICON_PX 64
#define ICON_BYTES (ICON_PX * ICON_PX * 3)  // LV_IMG_CF_TRUE_COLOR_ALPHA: RGB565 + alfa
#define MAX_APPS 15
#define IDLE_DARK_MS 60000  // bu kadar süre bağlantı yoksa ekranı karart
#define WAKE_MS 20000       // karanlıkken dokununca ekran bu kadar açık kalır

static char line_buf[LINK_LINE_MAX];
static size_t line_len = 0;
static bool line_overflow = false;
static uint32_t last_rx_ms = 0;
static uint32_t rx_count = 0;

// İkili bloklar (kapak resmi, uygulama ikonları): bkz. docs/02-mimari.md "Kapak resmi"
// Kapak: biri alınırken öteki gösterilen iki PSRAM tamponu. İkon: ortak alım tamponu, CRC tutunca ui kopyalar.
static uint8_t *art_rx = nullptr;     // alınmakta olan kapak
static uint8_t *art_show = nullptr;   // ekranda gösterilen kapak
static uint8_t *icon_rx = nullptr;    // alınmakta olan ikon
enum BinKind { BIN_ART, BIN_ICON };
static BinKind bin_kind = BIN_ART;
static int bin_index = 0;             // ikon sırası
static uint8_t *bin_dst = nullptr;
static size_t art_need = 0;           // >0 ise ikili alım modundayız
static size_t art_got = 0;
static uint32_t art_crc = 0;
static uint32_t art_deadline = 0;

// Ekran karartma (Faz 6): PC kilitli, servis "bye" dedi ya da uzun süre bağlantı yok
static Board *g_board = nullptr;
static bool pc_locked = false;
static bool pc_bye = false;
static uint32_t locked_since = 0;

// Faz 7: ayar dosyasından gelenler (cfg mesajı); bilgisayar söyleyene kadar eski davranış (kilitte karart)
static bool lock_clock_on = false;
static uint32_t lock_clock_ms = 10 * 60000UL;  // 0: kilit saati hiç kararmasın
static uint32_t notif_ms = 6000;
static bool warn_wake = false;  // yeni bir uyarı başladı: ekranı uyandır

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

// Uygulama kimliği bilgisayardan gelen listeden ([\w.+-]); bilgisayar yine listesinde arar
void link_send_app(const char *id)
{
    Serial.printf("{\"t\":\"cmd\",\"c\":\"app\",\"id\":\"%s\"}\n", id);
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
        bool locked = (doc["locked"] | 0) != 0;
        if (locked && !pc_locked) {
            locked_since = millis();
        }
        pc_locked = locked;
        pc_bye = false;
        if (ui_set_warn(doc["warn"] | "")) {
            warn_wake = true;
        }
    } else if (strcmp(t, "bye") == 0) {
        pc_bye = true;  // servis kapanıyor: ekranı hemen karart
    } else if (strcmp(t, "media") == 0) {
        ui_update_media(o);
    } else if (strcmp(t, "vol") == 0) {
        ui_update_vol(o);
    } else if (strcmp(t, "icon") == 0) {
        size_t n = doc["n"] | 0;
        int i = doc["i"] | -1;
        if (n == ICON_BYTES && (doc["w"] | 0) == ICON_PX && i >= 0 && i < MAX_APPS && icon_rx) {
            bin_kind = BIN_ICON;
            bin_index = i;
            bin_dst = icon_rx;
            art_need = n;
            art_got = 0;
            art_crc = doc["crc"] | 0UL;
            art_deadline = millis() + ART_TIMEOUT_MS;
        } else {
            Serial.printf("{\"t\":\"icon\",\"i\":%d,\"ok\":0}\n", i);
            // Beklenmeyen boyut: ardından gelecek n bayt satır gibi okunur, JSON olmadığı için atılır
        }
    } else if (strcmp(t, "apps") == 0) {
        ui_set_apps(doc["items"].as<JsonArrayConst>());
    } else if (strcmp(t, "tiles") == 0) {
        ui_set_tiles(doc["items"].as<JsonArrayConst>());
    } else if (strcmp(t, "cfg") == 0) {
        lock_clock_on = (doc["lock_clock"] | 0) != 0;
        lock_clock_ms = (doc["lock_min"] | 10UL) * 60000UL;
        notif_ms = (doc["notif_s"] | 6UL) * 1000UL;
    } else if (strcmp(t, "notif") == 0) {
        ui_show_notif(doc["app"] | "", doc["ti"] | "", doc["bd"] | "", doc["lvl"] | "info", notif_ms);
    } else if (strcmp(t, "cc") == 0) {
        ui_update_cc(o);
    } else if (strcmp(t, "gh") == 0) {
        ui_update_gh(o);
    } else if (strcmp(t, "srv") == 0) {
        ui_update_srv(o);
    } else if (strcmp(t, "cu") == 0) {
        ui_update_cu(o);
    } else if (strcmp(t, "git") == 0) {
        ui_update_git(o);
    } else if (strcmp(t, "art") == 0) {
        size_t n = doc["n"] | 0;
        if (n == 0) {
            ui_clear_art();
        } else if (n == ART_BYTES && (doc["w"] | 0) == ART_W && (doc["h"] | 0) == ART_H && art_rx) {
            bin_kind = BIN_ART;
            bin_dst = art_rx;
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
    uint32_t crc = esp_rom_crc32_le(0, bin_dst, art_need);
    bool ok = crc == art_crc;
    if (bin_kind == BIN_ICON) {
        if (ok) {
            lvgl_port_lock(-1);
            ui_set_app_icon(bin_index, icon_rx, ICON_PX, ICON_PX);  // ui kendi tamponuna kopyalar
            lvgl_port_unlock();
        }
        Serial.printf("{\"t\":\"icon\",\"i\":%d,\"ok\":%d}\n", bin_index, ok ? 1 : 0);
        art_need = 0;
        return;
    }
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
            art_got += Serial.read(bin_dst + art_got, avail < want ? avail : want);
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
            if (line_len < LINK_LINE_MAX - 1) {
                line_buf[line_len++] = static_cast<char>(c);
            } else {
                line_overflow = true;  // çok uzun satır: sonuna kadar at
            }
        }
    }
    if (art_need && static_cast<int32_t>(millis() - art_deadline) > 0) {
        Serial.printf("# ikili blok zaman asimi (%u / %u bayt)\n", static_cast<unsigned>(art_got),
                      static_cast<unsigned>(art_need));
        if (bin_kind == BIN_ICON) {
            Serial.printf("{\"t\":\"icon\",\"i\":%d,\"ok\":0}\n", bin_index);
        } else {
            Serial.println("{\"t\":\"art\",\"ok\":0}");
        }
        art_need = 0;  // satır moduna dön
    }
}

void setup()
{
    Serial.setRxBufferSize(32768);  // kart sayfa kurarken (LVGL kilidi) gelen veri taşmasın
    Serial.begin(LINK_BAUD);
    Serial.println("# pc-panel basliyor");

    art_rx = static_cast<uint8_t *>(heap_caps_malloc(ART_BYTES, MALLOC_CAP_SPIRAM));
    art_show = static_cast<uint8_t *>(heap_caps_malloc(ART_BYTES, MALLOC_CAP_SPIRAM));
    icon_rx = static_cast<uint8_t *>(heap_caps_malloc(ICON_BYTES, MALLOC_CAP_SPIRAM));
    if (!art_rx || !art_show) {
        Serial.println("# HATA: kapak tamponlari ayrilamadi");
        art_rx = nullptr;  // kapak özelliği kapalı, panel çalışmaya devam eder
    }

    Board *board = new Board();
    g_board = board;
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

    // Ekran durumu (bkz. docs/kararlar.md "Ekran karartma" ve "Kilit saati")
    //   servis kapandı / bağlantı yok → karanlık
    //   PC kilitli → kilit saati (ayarda açıksa, süresi dolana kadar) ya da karanlık
    //   karanlıkta dokunma ya da yeni uyarı → WAKE_MS boyunca açık (kilitliyken saat, değilse panel)
    enum Screen { SCR_PANEL, SCR_CLOCK, SCR_DARK };
    static Screen screen = SCR_PANEL;
    static uint32_t wake_until = 0;
    bool woke = ui_take_wake_request();
    if (woke || warn_wake) {
        wake_until = now + WAKE_MS;
        warn_wake = false;
    }
    bool awake = static_cast<int32_t>(now - wake_until) < 0;
    bool link_idle = last_rx_ms == 0 ? now > IDLE_DARK_MS : now - last_rx_ms > IDLE_DARK_MS;
    Screen want = SCR_PANEL;
    if (pc_bye || link_idle) {
        want = awake ? SCR_PANEL : SCR_DARK;
    } else if (pc_locked && lock_clock_on) {
        bool expired = lock_clock_ms && now - locked_since > lock_clock_ms;
        want = (!expired || awake) ? SCR_CLOCK : SCR_DARK;
    } else if (pc_locked) {
        want = awake ? SCR_PANEL : SCR_DARK;
    }
    if (want != screen) {
        screen = want;
        lvgl_port_lock(-1);
        ui_set_lock_clock(want == SCR_CLOCK);
        ui_set_sleep(want == SCR_DARK);
        lvgl_port_unlock();
        auto bl = g_board ? g_board->getBacklight() : nullptr;
        if (bl) {
            want == SCR_DARK ? bl->off() : bl->on();
        }
        static const char *const NAMES[] = {"panel", "kilit saati", "karartildi"};
        Serial.printf("# ekran: %s\n", NAMES[want]);
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
