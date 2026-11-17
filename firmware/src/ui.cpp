/*
 * PC Panel arayüzü (Faz 4) — 800×480, koyu sade tema, 3 kaydırmalı sayfa.
 * Tasarım kaynağı: docs/tasarim/taslak-v1.html. Ölçüler ve renkler oradan birebir alındı.
 *
 *   ┌ üst şerit (40 px): saat · tarih · SAYFA ADI · bağlantı ┐
 *   │ tileview (440 px): [Sistem] ↔ [Medya] ↔ [Kısayollar]   │
 *   └ sayfa noktaları                                         ┘
 */
#include "ui.h"

#include <Arduino.h>
#include <esp_heap_caps.h>
#include <lvgl.h>

#include "ui_fonts.h"

namespace {

// ---- Renkler (taslaktaki :root değişkenleri) ----
#define C_BG lv_color_hex(0x0d1014)
#define C_CARD lv_color_hex(0x161b21)
#define C_CARD2 lv_color_hex(0x1e252d)
#define C_LINE lv_color_hex(0x262e37)
#define C_TEXT lv_color_hex(0xe8edf2)
#define C_MUTED lv_color_hex(0x8a96a3)
#define C_FAINT lv_color_hex(0x5b6672)
#define C_ACCENT lv_color_hex(0x3aa0ff)
#define C_OK lv_color_hex(0x2ecc71)
#define C_WARN lv_color_hex(0xf1c40f)
#define C_BAD lv_color_hex(0xe74c3c)

constexpr int TOP_H = 40;
constexpr int PAGE_H = 440;

// ---- Nesneler ----
lv_obj_t *lbl_clock, *lbl_date, *lbl_page, *link_dot, *link_lbl;
constexpr int PAGES = 5;
lv_obj_t *tileview, *page_dots[PAGES];
lv_obj_t *toast;
lv_timer_t *toast_timer;

// Faz 7
lv_obj_t *warn_pill, *dev_top;                                  // üst şerit: uyarı, Claude durumu
lv_obj_t *notif_box, *notif_icon, *notif_app, *notif_title, *notif_body;  // bildirim balonu
lv_timer_t *notif_timer;
lv_obj_t *lock_scr, *lock_clock, *lock_date, *lock_warn, *lock_dev;  // kilit saati ekranı
lv_obj_t *sleep_overlay;
volatile bool wake_requested = false;

struct Big {  // CPU / GPU kartı
    lv_obj_t *arc, *num, *v1, *v2, *v3, *chart;
    lv_chart_series_t *ser;
};
Big cpu, gpu;

struct Small {
    lv_obj_t *main, *sub, *bar, *foot;
};
Small ram, vram;
lv_obj_t *disk_name[2], *disk_pct[2], *disk_bar[2], *disk_io;
lv_obj_t *net_dn, *net_up, *pc_up;

lv_obj_t *m_pill, *m_state, *m_title, *m_artist, *m_album, *m_seek, *m_pos, *m_len, *m_pp, *m_pp_lbl;
lv_obj_t *v_icon, *v_slider, *v_pct;
lv_obj_t *art_img, *art_note;
lv_img_dsc_t art_dsc;
int media_len = 0;

// ---- Kısayol kutuları (Faz 7: bilgisayardaki ayar dosyasından `tiles` mesajıyla gelir) ----
constexpr int MAX_TILES = 12;
enum Toggle : uint8_t { TG_NONE, TG_MIC, TG_MUTE };
struct Tile {
    char id[20], title[64], desc[64];
    const char *icon;
    Toggle tg;
    lv_obj_t *obj, *icon_lbl, *desc_lbl;
};
Tile tiles[MAX_TILES];
int tile_count = 0;
lv_obj_t *shortcut_page;
bool mic_off = false, mute_off = false;

// Bilgisayardan mesaj gelmeden önce gösterilenler (ayar dosyası örneğindeki varsayılanlarla aynı)
struct DefaultTile {
    const char *id, *icon, *title, *desc;
    Toggle tg;
};
const DefaultTile DEFAULT_TILES[] = {
    {"lock", "lock", "Ekranı kilitle", "KDE oturumu", TG_NONE},
    {"mic", "mic", "Mikrofon", "", TG_MIC},
    {"screenshot", "camera", "Ekran görüntüsü", "Spectacle", TG_NONE},
    {"mute", "volume", "Sesi kapat", "", TG_MUTE},
    {"terminal", "terminal", "Terminal", "Konsole", TG_NONE},
    {"tarayici", "globe", "Tarayıcı", "Zen", TG_NONE},
    {"dosyalar", "folder", "Dosyalar", "Dolphin", TG_NONE},
    {"spotify", "spotify", "Spotify", "öne getir", TG_NONE},
};

struct NamedGlyph {
    const char *name, *glyph;
};
#if PC_PANEL_TR_FONTS
// Ad → Font Awesome 5 (UTF-8). Adlar host/pc_panel/config.py ICONS ile aynı; glifler icon_font_40'ta.
const NamedGlyph ICONS[] = {
    {"lock", "\xEF\x80\xA3"},        {"mic", "\xEF\x84\xB0"},        {"camera", "\xEF\x80\xB0"},
    {"volume", "\xEF\x80\xA8"},      {"terminal", "\xEF\x84\xA0"},   {"globe", "\xEF\x82\xAC"},
    {"folder", "\xEF\x81\xBB"},      {"spotify", "\xEF\x86\xBC"},    {"code", "\xEF\x84\xA1"},
    {"gamepad", "\xEF\x84\x9B"},     {"steam", "\xEF\x86\xB6"},      {"discord", "\xEF\x8E\x92"},
    {"firefox", "\xEF\x89\xA9"},     {"chrome", "\xEF\x89\xA8"},     {"youtube", "\xEF\x85\xA7"},
    {"github", "\xEF\x82\x9B"},      {"envelope", "\xEF\x83\xA0"},   {"calendar", "\xEF\x81\xB3"},
    {"calculator", "\xEF\x87\xAC"},  {"cog", "\xEF\x80\x93"},        {"power", "\xEF\x80\x91"},
    {"moon", "\xEF\x86\x86"},        {"sync", "\xEF\x8B\xB1"},       {"desktop", "\xEF\x84\x88"},
    {"download", "\xEF\x80\x99"},    {"home", "\xEF\x80\x95"},       {"bolt", "\xEF\x83\xA7"},
    {"clipboard", "\xEF\x8C\xA8"},   {"image", "\xEF\x80\xBE"},      {"video", "\xEF\x80\xBD"},
    {"headphones", "\xEF\x80\xA5"},  {"star", "\xEF\x80\x85"},       {"bell", "\xEF\x83\xB3"},
    {"search", "\xEF\x80\x82"},      {"keyboard", "\xEF\x84\x9C"},   {"file", "\xEF\x85\x9C"},
    {"rocket", "\xEF\x84\xB5"},      {"tv", "\xEF\x89\xAC"},         {"wifi", "\xEF\x87\xAB"},
    {"telegram", "\xEF\x8B\x86"},    {"whatsapp", "\xEF\x88\xB2"},   {"music", "\xEF\x80\x81"},
    {"play", "\xEF\x81\x8B"},        {"pause", "\xEF\x81\x8C"},      {"next", "\xEF\x81\x91"},
    {"prev", "\xEF\x81\x88"},
};
#else
const NamedGlyph ICONS[] = {
    {"lock", ICON_LOCK},         {"mic", ICON_MIC},        {"camera", ICON_CAMERA}, {"volume", ICON_VOLUME},
    {"terminal", ICON_TERMINAL}, {"globe", ICON_GLOBE},    {"folder", ICON_FOLDER}, {"spotify", ICON_SPOTIFY},
    {"music", ICON_MUSIC},       {"play", LV_SYMBOL_PLAY}, {"pause", LV_SYMBOL_PAUSE},
    {"next", LV_SYMBOL_NEXT},    {"prev", LV_SYMBOL_PREV}, {"cog", LV_SYMBOL_SETTINGS},
    {"home", LV_SYMBOL_HOME},    {"wifi", LV_SYMBOL_WIFI}, {"bell", LV_SYMBOL_BELL},
};
#endif

const char *glyph_by_name(const NamedGlyph *table, size_t n, const char *name, const char *fallback)
{
    for (size_t i = 0; i < n; i++) {
        if (strcmp(table[i].name, name) == 0) {
            return table[i].glyph;
        }
    }
    return fallback;
}
#define ICON(name) glyph_by_name(ICONS, sizeof(ICONS) / sizeof(ICONS[0]), (name), LV_SYMBOL_DUMMY "?")

const char *const PAGE_NAMES[PAGES] = {"SİSTEM", "MEDYA", "UYGULAMALAR", "KISAYOLLAR", "GELİŞTİRİCİ"};

// ---- Yardımcılar ----

#if !PC_PANEL_TR_FONTS
// Türkçe yazı tipi yokken: ç ğ ı İ ö ş ü → ASCII (Faz 3'teki geçici çözüm)
void translit(const char *in, char *out, size_t n)
{
    size_t o = 0;
    const unsigned char *s = reinterpret_cast<const unsigned char *>(in ? in : "");
    while (*s && o + 1 < n) {
        unsigned char c = *s;
        if (c < 0x80) {
            out[o++] = static_cast<char>(c);
            s++;
            continue;
        }
        char r = '?';
        if (c == 0xC3) {
            switch (s[1]) {
                case 0xA7: r = 'c'; break; case 0x87: r = 'C'; break;
                case 0xB6: r = 'o'; break; case 0x96: r = 'O'; break;
                case 0xBC: r = 'u'; break; case 0x9C: r = 'U'; break;
            }
        } else if (c == 0xC4) {
            switch (s[1]) {
                case 0x9F: r = 'g'; break; case 0x9E: r = 'G'; break;
                case 0xB1: r = 'i'; break; case 0xB0: r = 'I'; break;
            }
        } else if (c == 0xC5) {
            switch (s[1]) {
                case 0x9F: r = 's'; break; case 0x9E: r = 'S'; break;
            }
        }
        out[o++] = r;
        int len = (c >= 0xF0) ? 4 : (c >= 0xE0) ? 3 : 2;
        for (int i = 0; i < len && *s; i++) {
            s++;
        }
    }
    out[o] = 0;
}
#endif

void set_text(lv_obj_t *l, const char *utf8)
{
#if PC_PANEL_TR_FONTS
    lv_label_set_text(l, utf8 ? utf8 : "");
#else
    char buf[256];
    translit(utf8, buf, sizeof(buf));
    lv_label_set_text(l, buf);
#endif
}

// Ondalık virgüllü sayı: 8.4 → "8,4"
void fmt_dec(char *out, size_t n, float v, int digits = 1)
{
    snprintf(out, n, "%.*f", digits, v);
    for (char *p = out; *p; p++) {
        if (*p == '.') {
            *p = ',';
        }
    }
}

void fmt_rate(char *out, size_t n, float bps)
{
    char num[16];
    if (bps < 1024) {
        snprintf(out, n, "%.0f B/s", bps);
    } else if (bps < 1024 * 1024) {
        snprintf(out, n, "%.0f KB/s", bps / 1024);
    } else {
        fmt_dec(num, sizeof(num), bps / (1024 * 1024));
        snprintf(out, n, "%s MB/s", num);
    }
}

void fmt_time(char *out, size_t n, int sec)
{
    if (sec < 0) {
        sec = 0;
    }
    if (sec >= 3600) {
        snprintf(out, n, "%d:%02d:%02d", sec / 3600, sec / 60 % 60, sec % 60);
    } else {
        snprintf(out, n, "%d:%02d", sec / 60, sec % 60);
    }
}

lv_color_t level_color(float pct)
{
    return pct < 60 ? C_ACCENT : pct < 85 ? C_WARN : C_BAD;
}

lv_color_t temp_color(float t)
{
    return t < 65 ? C_TEXT : t < 80 ? C_WARN : C_BAD;
}

lv_obj_t *label(lv_obj_t *parent, const lv_font_t *font, lv_color_t color, const char *text = "")
{
    lv_obj_t *l = lv_label_create(parent);
    lv_obj_set_style_text_font(l, font, 0);
    lv_obj_set_style_text_color(l, color, 0);
    lv_label_set_text(l, text);
    return l;
}

// Sağa dayalı etiket: sağ kenarı x_right'ta
lv_obj_t *label_right(lv_obj_t *parent, const lv_font_t *font, lv_color_t color, int x_right, int y, int w)
{
    lv_obj_t *l = label(parent, font, color);
    lv_obj_set_width(l, w);
    lv_obj_set_style_text_align(l, LV_TEXT_ALIGN_RIGHT, 0);
    lv_obj_set_pos(l, x_right - w, y);
    return l;
}

lv_obj_t *card(lv_obj_t *parent, int x, int y, int w, int h)
{
    lv_obj_t *c = lv_obj_create(parent);
    lv_obj_remove_style_all(c);
    lv_obj_set_pos(c, x, y);
    lv_obj_set_size(c, w, h);
    lv_obj_set_style_bg_color(c, C_CARD, 0);
    lv_obj_set_style_bg_opa(c, LV_OPA_COVER, 0);
    lv_obj_set_style_radius(c, 14, 0);
    lv_obj_clear_flag(c, LV_OBJ_FLAG_SCROLLABLE);
    lv_obj_clear_flag(c, LV_OBJ_FLAG_CLICKABLE);  // sayfa kaydırma kartın üstünden de çalışsın
    return c;
}

lv_obj_t *caption(lv_obj_t *parent, int x, int y, const char *text)
{
    lv_obj_t *l = label(parent, F12, C_MUTED, text);
    lv_obj_set_style_text_letter_space(l, 1, 0);
    lv_obj_set_pos(l, x, y);
    return l;
}

lv_obj_t *bar(lv_obj_t *parent, int x, int y, int w, int h)
{
    lv_obj_t *b = lv_bar_create(parent);
    lv_obj_set_pos(b, x, y);
    lv_obj_set_size(b, w, h);
    lv_bar_set_range(b, 0, 100);
    lv_obj_set_style_bg_color(b, C_CARD2, LV_PART_MAIN);
    lv_obj_set_style_bg_color(b, C_ACCENT, LV_PART_INDICATOR);
    lv_obj_set_style_radius(b, h / 2, LV_PART_MAIN);
    lv_obj_set_style_radius(b, h / 2, LV_PART_INDICATOR);
    lv_obj_clear_flag(b, LV_OBJ_FLAG_CLICKABLE);
    return b;
}

void set_bar(lv_obj_t *b, float pct, lv_color_t color)
{
    lv_bar_set_value(b, static_cast<int>(pct + 0.5f), LV_ANIM_OFF);
    lv_obj_set_style_bg_color(b, color, LV_PART_INDICATOR);
}

lv_obj_t *slider(lv_obj_t *parent, int x, int y, int w)
{
    lv_obj_t *s = lv_slider_create(parent);
    lv_obj_set_pos(s, x, y);
    lv_obj_set_size(s, w, 6);
    lv_obj_set_style_bg_color(s, C_CARD2, LV_PART_MAIN);
    lv_obj_set_style_bg_opa(s, LV_OPA_COVER, LV_PART_MAIN);
    lv_obj_set_style_bg_color(s, C_ACCENT, LV_PART_INDICATOR);
    lv_obj_set_style_bg_color(s, C_TEXT, LV_PART_KNOB);
    lv_obj_set_style_pad_all(s, 6, LV_PART_KNOB);  // tutamak 18 px
    lv_obj_set_ext_click_area(s, 18);               // parmakla tutması kolay olsun
    return s;
}

// ---- Toast (kısa bildirim) ----
void toast_hide_cb(lv_timer_t *t)
{
    lv_obj_add_flag(toast, LV_OBJ_FLAG_HIDDEN);
    toast_timer = nullptr;
}

void show_toast(const char *text)
{
    set_text(toast, text);
    lv_obj_clear_flag(toast, LV_OBJ_FLAG_HIDDEN);
    lv_obj_align(toast, LV_ALIGN_BOTTOM_MID, 0, -34);
    if (toast_timer) {
        lv_timer_reset(toast_timer);
    } else {
        toast_timer = lv_timer_create(toast_hide_cb, 1400, nullptr);
        lv_timer_set_repeat_count(toast_timer, 1);
    }
}

// ---- Sayfa değişimi ----
void tile_changed_cb(lv_event_t *e)
{
    lv_obj_t *act = lv_tileview_get_tile_act(tileview);
    int idx = static_cast<int>(lv_obj_get_x(act) / 800);
    lv_label_set_text(lbl_page, PAGE_NAMES[idx]);
    for (int i = 0; i < PAGES; i++) {
        lv_obj_set_width(page_dots[i], i == idx ? 20 : 7);
        lv_obj_set_style_bg_color(page_dots[i], i == idx ? C_ACCENT : C_LINE, 0);
    }
}

// =====================================================================================
// 1) Sistem
// =====================================================================================
Big make_big(lv_obj_t *page, int x, const char *title, const char *name, const char *k1, const char *k2,
             const char *k3)
{
    Big b;
    lv_obj_t *c = card(page, x, 4, 380, 228);
    caption(c, 16, 14, title);
    lv_obj_t *n = label_right(c, F12, C_FAINT, 364, 14, 200);
    lv_label_set_text(n, name);

    b.arc = lv_arc_create(c);
    lv_obj_set_size(b.arc, 118, 118);
    lv_obj_set_pos(b.arc, 16, 38);
    lv_arc_set_bg_angles(b.arc, 135, 45);
    lv_arc_set_range(b.arc, 0, 100);
    lv_arc_set_value(b.arc, 0);
    lv_obj_remove_style(b.arc, nullptr, LV_PART_KNOB);
    lv_obj_clear_flag(b.arc, LV_OBJ_FLAG_CLICKABLE);
    lv_obj_set_style_arc_width(b.arc, 11, LV_PART_MAIN);
    lv_obj_set_style_arc_width(b.arc, 11, LV_PART_INDICATOR);
    lv_obj_set_style_arc_color(b.arc, C_CARD2, LV_PART_MAIN);
    lv_obj_set_style_arc_color(b.arc, C_ACCENT, LV_PART_INDICATOR);
    lv_obj_set_style_arc_rounded(b.arc, true, LV_PART_MAIN);
    lv_obj_set_style_arc_rounded(b.arc, true, LV_PART_INDICATOR);
    lv_obj_set_style_pad_all(b.arc, 0, 0);

    b.num = label(c, F30, C_TEXT, "-");
    lv_obj_align_to(b.num, b.arc, LV_ALIGN_CENTER, 0, -6);
    lv_obj_t *unit = label(c, F12, C_MUTED, "% yük");
    lv_obj_align_to(unit, b.arc, LV_ALIGN_CENTER, 0, 20);

    const char *keys[3] = {k1, k2, k3};
    lv_obj_t **vals[3] = {&b.v1, &b.v2, &b.v3};
    for (int i = 0; i < 3; i++) {
        lv_obj_t *k = label(c, F12, C_MUTED, keys[i]);
        lv_obj_set_pos(k, 152, 58 + i * 28);
        *vals[i] = label_right(c, F18, C_TEXT, 364, 54 + i * 28, 110);
        lv_label_set_text(*vals[i], "-");
    }

    lv_obj_t *cap = label_right(c, F12, C_FAINT, 364, 146, 100);
    lv_label_set_text(cap, "son 60 sn");

    b.chart = lv_chart_create(c);
    lv_obj_set_pos(b.chart, 16, 162);
    lv_obj_set_size(b.chart, 348, 54);
    lv_chart_set_type(b.chart, LV_CHART_TYPE_LINE);
    lv_chart_set_point_count(b.chart, 60);
    lv_chart_set_range(b.chart, LV_CHART_AXIS_PRIMARY_Y, 0, 100);
    lv_chart_set_div_line_count(b.chart, 0, 0);
    lv_chart_set_update_mode(b.chart, LV_CHART_UPDATE_MODE_SHIFT);
    lv_obj_set_style_bg_opa(b.chart, LV_OPA_TRANSP, 0);
    lv_obj_set_style_border_width(b.chart, 0, 0);
    lv_obj_set_style_pad_all(b.chart, 0, 0);
    lv_obj_set_style_line_width(b.chart, 2, LV_PART_ITEMS);
    lv_obj_set_style_size(b.chart, 0, LV_PART_INDICATOR);  // nokta işaretleri yok
    lv_obj_clear_flag(b.chart, LV_OBJ_FLAG_CLICKABLE);
    b.ser = lv_chart_add_series(b.chart, C_ACCENT, LV_CHART_AXIS_PRIMARY_Y);
    return b;
}

Small make_small(lv_obj_t *page, int x, int w, const char *title, const char *foot)
{
    Small s;
    lv_obj_t *c = card(page, x, 244, w, 150);
    caption(c, 14, 12, title);
    s.main = label(c, F22, C_TEXT, "-");
    lv_obj_set_pos(s.main, 14, 36);
    s.sub = label(c, F14, C_MUTED, "");
    s.bar = bar(c, 14, 74, w - 28, 8);
    s.foot = label(c, F12, C_MUTED, foot);
    lv_obj_set_pos(s.foot, 14, 94);
    return s;
}

void build_system(lv_obj_t *page)
{
    cpu = make_big(page, 14, "CPU", "Ryzen 7 9800X3D", "Sıcaklık", "Frekans", "En yoğun çekirdek");
    gpu = make_big(page, 406, "GPU", "GeForce RTX 5080", "Sıcaklık", "Güç", "Fan");

    ram = make_small(page, 14, 185, "RAM", "swap -");
    vram = make_small(page, 211, 185, "VRAM", "GPU belleği");

    lv_obj_t *dc = card(page, 408, 244, 185, 150);
    caption(dc, 14, 12, "DİSKLER");
    for (int i = 0; i < 2; i++) {
        int y = 38 + i * 36;
        disk_name[i] = label(dc, F12, C_MUTED, i == 0 ? "Sistem /" : "Veri");
        lv_obj_set_pos(disk_name[i], 14, y);
        disk_pct[i] = label_right(dc, F12, C_TEXT, 171, y, 50);
        disk_bar[i] = bar(dc, 14, y + 18, 157, 6);
    }
    disk_io = label(dc, F12, C_MUTED, "oku - · yaz -");
    lv_obj_set_pos(disk_io, 14, 120);

    lv_obj_t *nc = card(page, 605, 244, 181, 150);
    caption(nc, 14, 12, "AĞ");
    lv_obj_t *a = label(nc, F14, C_MUTED, LV_SYMBOL_DOWN " indirme");
    lv_obj_set_pos(a, 14, 44);
    net_dn = label_right(nc, F18, C_TEXT, 167, 40, 90);
    lv_obj_t *b = label(nc, F14, C_MUTED, LV_SYMBOL_UP " yükleme");
    lv_obj_set_pos(b, 14, 76);
    net_up = label_right(nc, F18, C_TEXT, 167, 72, 90);
    pc_up = label(nc, F12, C_MUTED, "PC açık: -");
    lv_obj_set_pos(pc_up, 14, 116);
}

// =====================================================================================
// 2) Medya
// =====================================================================================
void media_btn_cb(lv_event_t *e)
{
    const char *cmd = static_cast<const char *>(lv_event_get_user_data(e));
    if (strcmp(cmd, "back10") == 0) {
        link_send_cmd("seek_rel", -10, true);
    } else if (strcmp(cmd, "fwd10") == 0) {
        link_send_cmd("seek_rel", 10, true);
    } else {
        link_send_cmd(cmd, 0, false);
    }
}

void seek_released_cb(lv_event_t *e)
{
    if (media_len > 0) {
        link_send_cmd("seek_abs", lv_slider_get_value(m_seek), true);
    }
}

void seek_changed_cb(lv_event_t *e)
{
    char a[16];
    fmt_time(a, sizeof(a), lv_slider_get_value(m_seek));
    lv_label_set_text(m_pos, a);
}

void vol_released_cb(lv_event_t *e)
{
    link_send_cmd("vol_set", lv_slider_get_value(v_slider), true);
}

void vol_changed_cb(lv_event_t *e)
{
    lv_label_set_text_fmt(v_pct, "%d%%", static_cast<int>(lv_slider_get_value(v_slider)));
}

void mute_click_cb(lv_event_t *e)
{
    link_send_cmd("mute", 0, false);  // kısayol listesinden bağımsız (v1.4)
}

lv_obj_t *button(lv_obj_t *parent, int x, int w, lv_color_t bg, const char *cmd)
{
    lv_obj_t *b = lv_btn_create(parent);
    lv_obj_set_pos(b, x, 262);
    lv_obj_set_size(b, w, 84);
    lv_obj_set_style_radius(b, 14, 0);
    lv_obj_set_style_shadow_width(b, 0, 0);
    lv_obj_set_style_bg_color(b, bg, 0);
    lv_obj_set_style_bg_color(b, C_CARD2, LV_STATE_PRESSED);
    lv_obj_add_event_cb(b, media_btn_cb, LV_EVENT_CLICKED, const_cast<char *>(cmd));
    return b;
}

void icon_in(lv_obj_t *btn, const char *icon)
{
    lv_obj_t *l = label(btn, FICON, C_TEXT, icon);
    lv_obj_center(l);
}

void seek_btn(lv_obj_t *page, int x, const char *text, const char *cmd)
{
    lv_obj_t *b = button(page, x, 84, C_CARD, cmd);
    lv_obj_t *t = label(b, F18, C_TEXT, text);
    lv_obj_align(t, LV_ALIGN_CENTER, 0, -8);
    lv_obj_t *s = label(b, F12, C_MUTED, "sn");
    lv_obj_align(s, LV_ALIGN_CENTER, 0, 14);
}

void build_media(lv_obj_t *page)
{
    // Kapak alanı (gerçek resim Faz 5'te)
    lv_obj_t *art = card(page, 14, 4, 240, 240);
    lv_obj_set_style_bg_color(art, lv_color_hex(0x2b3a4a), 0);
    lv_obj_set_style_bg_grad_color(art, lv_color_hex(0x3a2b35), 0);
    lv_obj_set_style_bg_grad_dir(art, LV_GRAD_DIR_VER, 0);
    lv_obj_set_style_clip_corner(art, true, 0);  // kapak resmi yuvarlak köşelerden taşmasın
    art_note = label(art, FICON, C_TEXT, ICON_MUSIC);
    lv_obj_set_style_text_opa(art_note, LV_OPA_20, 0);
    lv_obj_center(art_note);
    art_img = lv_img_create(art);
    lv_obj_set_pos(art_img, 0, 0);
    lv_obj_add_flag(art_img, LV_OBJ_FLAG_HIDDEN);

    m_pill = label(page, F12, C_TEXT, "-");
    lv_obj_set_pos(m_pill, 274, 10);
    lv_obj_set_style_bg_color(m_pill, C_CARD2, 0);
    lv_obj_set_style_bg_opa(m_pill, LV_OPA_COVER, 0);
    lv_obj_set_style_radius(m_pill, 10, 0);
    lv_obj_set_style_pad_hor(m_pill, 9, 0);
    lv_obj_set_style_pad_ver(m_pill, 3, 0);
    m_state = label(page, F12, C_MUTED, "");
    lv_obj_align_to(m_state, m_pill, LV_ALIGN_OUT_RIGHT_MID, 8, 0);

    m_title = label(page, F30, C_TEXT, "Çalan bir şey yok");
    lv_obj_set_pos(m_title, 274, 40);
    lv_obj_set_width(m_title, 506);
    lv_label_set_long_mode(m_title, LV_LABEL_LONG_SCROLL_CIRCULAR);
    m_artist = label(page, F22, C_TEXT, "");
    lv_obj_set_pos(m_artist, 274, 84);
    lv_obj_set_width(m_artist, 506);
    lv_label_set_long_mode(m_artist, LV_LABEL_LONG_DOT);
    m_album = label(page, F14, C_MUTED, "");
    lv_obj_set_pos(m_album, 274, 116);
    lv_obj_set_width(m_album, 506);
    lv_label_set_long_mode(m_album, LV_LABEL_LONG_DOT);

    m_seek = slider(page, 274, 186, 506);
    lv_slider_set_range(m_seek, 0, 1);
    lv_obj_add_event_cb(m_seek, seek_released_cb, LV_EVENT_RELEASED, nullptr);
    lv_obj_add_event_cb(m_seek, seek_changed_cb, LV_EVENT_VALUE_CHANGED, nullptr);
    m_pos = label(page, F12, C_MUTED, "0:00");
    lv_obj_set_pos(m_pos, 274, 204);
    m_len = label_right(page, F12, C_MUTED, 780, 204, 80);
    lv_label_set_text(m_len, "0:00");

    // Düğmeler: x = 14 / 110 / 218 / 350 / 458, ses kutusu 554..786
    seek_btn(page, 14, "-10", "back10");
    icon_in(button(page, 110, 96, C_CARD, "prev"), LV_SYMBOL_PREV);
    m_pp = button(page, 218, 120, C_ACCENT, "play_pause");
    m_pp_lbl = label(m_pp, FICON, C_TEXT, LV_SYMBOL_PLAY);
    lv_obj_center(m_pp_lbl);
    icon_in(button(page, 350, 96, C_CARD, "next"), LV_SYMBOL_NEXT);
    seek_btn(page, 458, "+10", "fwd10");

    lv_obj_t *vb = card(page, 554, 262, 232, 84);
    v_icon = label(vb, F22, C_MUTED, LV_SYMBOL_VOLUME_MAX);
    lv_obj_set_pos(v_icon, 16, 29);
    lv_obj_add_flag(v_icon, LV_OBJ_FLAG_CLICKABLE);
    lv_obj_set_ext_click_area(v_icon, 16);
    lv_obj_add_event_cb(v_icon, mute_click_cb, LV_EVENT_CLICKED, nullptr);
    v_slider = slider(vb, 56, 39, 98);
    lv_slider_set_range(v_slider, 0, 100);
    lv_obj_add_event_cb(v_slider, vol_released_cb, LV_EVENT_RELEASED, nullptr);
    lv_obj_add_event_cb(v_slider, vol_changed_cb, LV_EVENT_VALUE_CHANGED, nullptr);
    v_pct = label_right(vb, F16, C_TEXT, 222, 32, 58);
    lv_label_set_text(v_pct, "-");
}

// =====================================================================================
// 3) Kısayollar
// =====================================================================================
void tile_click_cb(lv_event_t *e)
{
    Tile *t = static_cast<Tile *>(lv_event_get_user_data(e));
    link_send_shortcut(t->id);
    char msg[80];
    snprintf(msg, sizeof(msg), "%s…", t->title);
    show_toast(msg);
}

// Kutu yerleşimi: 8'e kadar 2 satır (178 px), daha fazlası 3 satır (124 px); her zaman 4 sütun
int tile_icon_dy = -26, tile_title_dy = 22, tile_desc_dy = 44;

void apply_tile_toggle(Tile &t)
{
    if (t.tg == TG_NONE) {
        return;
    }
    bool off = t.tg == TG_MIC ? mic_off : mute_off;
    lv_obj_set_style_text_color(t.icon_lbl, off ? C_ACCENT : C_TEXT, 0);
    lv_obj_set_style_text_color(t.desc_lbl, off ? C_ACCENT : C_MUTED, 0);
    set_text(t.desc_lbl, off ? "kapalı" : "açık");
    if (t.tg == TG_MIC) {
        lv_label_set_text(t.icon_lbl, off ? ICON_MIC_OFF : ICON_MIC);
    } else {
        lv_label_set_text(t.icon_lbl, off ? ICON_VOLUME_OFF : ICON_VOLUME);
    }
    lv_obj_align(t.icon_lbl, LV_ALIGN_CENTER, 0, tile_icon_dy);
    lv_obj_align(t.desc_lbl, LV_ALIGN_CENTER, 0, tile_desc_dy);
}

void build_shortcuts(lv_obj_t *page)
{
    lv_obj_clean(page);
    const bool three_rows = tile_count > 8;
    const int w = 184, gap = three_rows ? 10 : 12, h = three_rows ? 124 : 178;
    tile_icon_dy = three_rows ? -20 : -26;
    tile_title_dy = three_rows ? 22 : 22;
    tile_desc_dy = three_rows ? 42 : 44;
    for (int i = 0; i < tile_count; i++) {
        Tile &t = tiles[i];
        int col = i % 4, row = i / 4;
        t.obj = lv_obj_create(page);
        lv_obj_remove_style_all(t.obj);
        lv_obj_set_pos(t.obj, 14 + col * (w + gap), 4 + row * (h + gap));
        lv_obj_set_size(t.obj, w, h);
        lv_obj_set_style_bg_color(t.obj, C_CARD, 0);
        lv_obj_set_style_bg_color(t.obj, C_CARD2, LV_STATE_PRESSED);
        lv_obj_set_style_bg_opa(t.obj, LV_OPA_COVER, 0);
        lv_obj_set_style_radius(t.obj, 14, 0);
        lv_obj_clear_flag(t.obj, LV_OBJ_FLAG_SCROLLABLE);
        lv_obj_add_event_cb(t.obj, tile_click_cb, LV_EVENT_CLICKED, &t);

        t.icon_lbl = label(t.obj, FICON, C_TEXT, t.icon);
        lv_obj_align(t.icon_lbl, LV_ALIGN_CENTER, 0, tile_icon_dy);
        lv_obj_t *title = label(t.obj, F16, C_TEXT);
        set_text(title, t.title);
        lv_obj_set_width(title, w - 16);
        lv_obj_set_style_text_align(title, LV_TEXT_ALIGN_CENTER, 0);
        lv_label_set_long_mode(title, LV_LABEL_LONG_DOT);
        lv_obj_align(title, LV_ALIGN_CENTER, 0, tile_title_dy);
        t.desc_lbl = label(t.obj, F12, C_MUTED);
        set_text(t.desc_lbl, t.desc);
        lv_obj_align(t.desc_lbl, LV_ALIGN_CENTER, 0, tile_desc_dy);
        apply_tile_toggle(t);
    }
}

void set_tile(Tile &t, const char *id, const char *icon_name, const char *title, const char *desc, Toggle tg)
{
    strlcpy(t.id, id, sizeof(t.id));
    strlcpy(t.title, title, sizeof(t.title));
    strlcpy(t.desc, desc, sizeof(t.desc));
    t.icon = ICON(icon_name);
    t.tg = tg;
}

void load_default_tiles()
{
    tile_count = sizeof(DEFAULT_TILES) / sizeof(DEFAULT_TILES[0]);
    for (int i = 0; i < tile_count; i++) {
        const DefaultTile &d = DEFAULT_TILES[i];
        set_tile(tiles[i], d.id, d.icon, d.title, d.desc, d.tg);
    }
}

void refresh_toggles()
{
    for (int i = 0; i < tile_count; i++) {
        apply_tile_toggle(tiles[i]);
    }
}

// =====================================================================================
// Faz 7: bildirim balonu, kilit saati ekranı
// =====================================================================================
void notif_hide_cb(lv_timer_t *t)
{
    lv_obj_add_flag(notif_box, LV_OBJ_FLAG_HIDDEN);
    notif_timer = nullptr;
}

void notif_click_cb(lv_event_t *e)
{
    lv_obj_add_flag(notif_box, LV_OBJ_FLAG_HIDDEN);  // dokununca kapanır
    if (notif_timer) {
        lv_timer_del(notif_timer);
        notif_timer = nullptr;
    }
}

void anim_y_cb(void *obj, int32_t v)
{
    lv_obj_set_y(static_cast<lv_obj_t *>(obj), static_cast<lv_coord_t>(v));
}

void build_notif()
{
    // Üst katmanda (kilit saati ekranının da üstünde, karartma perdesinin altında)
    notif_box = lv_obj_create(lv_layer_top());
    lv_obj_remove_style_all(notif_box);
    lv_obj_set_size(notif_box, 600, 92);
    lv_obj_set_pos(notif_box, 100, 6);
    lv_obj_set_style_bg_color(notif_box, C_CARD2, 0);
    lv_obj_set_style_bg_opa(notif_box, LV_OPA_COVER, 0);
    lv_obj_set_style_radius(notif_box, 14, 0);
    lv_obj_set_style_border_color(notif_box, C_LINE, 0);
    lv_obj_set_style_border_width(notif_box, 1, 0);
    lv_obj_set_style_shadow_color(notif_box, lv_color_black(), 0);
    lv_obj_set_style_shadow_width(notif_box, 24, 0);
    lv_obj_set_style_shadow_opa(notif_box, LV_OPA_60, 0);
    lv_obj_clear_flag(notif_box, LV_OBJ_FLAG_SCROLLABLE);
    lv_obj_add_flag(notif_box, LV_OBJ_FLAG_CLICKABLE);
    lv_obj_add_event_cb(notif_box, notif_click_cb, LV_EVENT_CLICKED, nullptr);

    notif_icon = label(notif_box, F22, C_ACCENT, LV_SYMBOL_BELL);
    lv_obj_set_width(notif_icon, 30);
    lv_obj_set_style_text_align(notif_icon, LV_TEXT_ALIGN_CENTER, 0);
    lv_obj_set_pos(notif_icon, 14, 32);
    notif_app = label(notif_box, F12, C_MUTED);
    lv_obj_set_pos(notif_app, 58, 10);
    lv_obj_set_width(notif_app, 520);
    lv_label_set_long_mode(notif_app, LV_LABEL_LONG_DOT);
    notif_title = label(notif_box, F16, C_TEXT);
    lv_obj_set_pos(notif_title, 58, 28);
    lv_obj_set_width(notif_title, 520);
    lv_label_set_long_mode(notif_title, LV_LABEL_LONG_DOT);
    notif_body = label(notif_box, F14, C_MUTED);
    lv_obj_set_pos(notif_body, 58, 52);
    lv_obj_set_size(notif_body, 520, 34);  // en çok 2 satır
    lv_label_set_long_mode(notif_body, LV_LABEL_LONG_DOT);
    lv_obj_add_flag(notif_box, LV_OBJ_FLAG_HIDDEN);
}

void build_lock_screen()
{
    lock_scr = lv_obj_create(lv_layer_top());
    lv_obj_remove_style_all(lock_scr);
    lv_obj_set_size(lock_scr, 800, 480);
    lv_obj_set_style_bg_color(lock_scr, lv_color_black(), 0);
    lv_obj_set_style_bg_opa(lock_scr, LV_OPA_COVER, 0);
    lv_obj_clear_flag(lock_scr, LV_OBJ_FLAG_SCROLLABLE);
    lv_obj_add_flag(lock_scr, LV_OBJ_FLAG_CLICKABLE);  // dokunma alttaki düğmelere geçmesin
    lv_obj_add_event_cb(lock_scr, [](lv_event_t *e) { wake_requested = true; }, LV_EVENT_PRESSED, nullptr);

    lv_obj_t *hint = label(lock_scr, F14, C_FAINT);
    set_text(hint, "Bilgisayar kilitli");
    lv_obj_align(hint, LV_ALIGN_TOP_MID, 0, 22);
    lock_warn = label(lock_scr, F18, C_BAD, "");
    lv_obj_align(lock_warn, LV_ALIGN_TOP_MID, 0, 50);

    lock_clock = label(lock_scr, FCLOCK, lv_color_hex(0xc8d0d8), "--:--");
    lv_obj_align(lock_clock, LV_ALIGN_CENTER, 0, -50);
    lock_date = label(lock_scr, F22, C_MUTED, "");
    lv_obj_align(lock_date, LV_ALIGN_CENTER, 0, 34);
    lock_dev = label(lock_scr, F18, C_WARN, "");  // ör. "Claude: 1 oturum bekliyor"
    lv_obj_align(lock_dev, LV_ALIGN_BOTTOM_MID, 0, -50);


    lv_obj_add_flag(lock_scr, LV_OBJ_FLAG_HIDDEN);
}


// =====================================================================================
// Uygulamalar (Faz 7E): 5×3 ızgara, gerçek uygulama ikonları bilgisayardan (64×64 RGB565 + alfa)
// =====================================================================================
constexpr int MAX_APPS = 15, APP_ICON_PX = 64, APP_ICON_BYTES = APP_ICON_PX * APP_ICON_PX * 3;
struct AppTile {
    char id[44], title[64];
    lv_obj_t *obj, *img, *letter;
    uint8_t *px;  // PSRAM, ilk ikonda ayrılır ve saklanır
    lv_img_dsc_t dsc;
};
AppTile apps[MAX_APPS];
int app_count = 0;
lv_obj_t *apps_page, *apps_empty;

void app_click_cb(lv_event_t *e)
{
    AppTile *a = static_cast<AppTile *>(lv_event_get_user_data(e));
    link_send_app(a->id);
    char msg[96];
    snprintf(msg, sizeof(msg), "%s açılıyor…", a->title);
    show_toast(msg);
}

void build_apps()
{
    lv_obj_clean(apps_page);
    const int w = 148, h = 128, gx = 8, gy = 8;
    for (int i = 0; i < app_count; i++) {
        AppTile &a = apps[i];
        a.obj = lv_obj_create(apps_page);
        lv_obj_remove_style_all(a.obj);
        lv_obj_set_pos(a.obj, 14 + (i % 5) * (w + gx), 4 + (i / 5) * (h + gy));
        lv_obj_set_size(a.obj, w, h);
        lv_obj_set_style_bg_color(a.obj, C_CARD, 0);
        lv_obj_set_style_bg_color(a.obj, C_CARD2, LV_STATE_PRESSED);
        lv_obj_set_style_bg_opa(a.obj, LV_OPA_COVER, 0);
        lv_obj_set_style_radius(a.obj, 14, 0);
        lv_obj_clear_flag(a.obj, LV_OBJ_FLAG_SCROLLABLE);
        lv_obj_add_event_cb(a.obj, app_click_cb, LV_EVENT_CLICKED, &a);

        // İkon gelene kadar adın baş harfi
        a.letter = label(a.obj, F30, C_MUTED, "");
        char first[5] = {0};
        const unsigned char c0 = static_cast<unsigned char>(a.title[0]);
        size_t len = c0 < 0x80 ? 1 : c0 < 0xE0 ? 2 : c0 < 0xF0 ? 3 : 4;
        memcpy(first, a.title, len < sizeof(first) ? len : sizeof(first) - 1);
        set_text(a.letter, first);
        lv_obj_align(a.letter, LV_ALIGN_CENTER, 0, -14);
        a.img = lv_img_create(a.obj);
        lv_obj_align(a.img, LV_ALIGN_CENTER, 0, -14);
        lv_obj_add_flag(a.img, LV_OBJ_FLAG_HIDDEN);

        lv_obj_t *t = label(a.obj, F14, C_TEXT);
        set_text(t, a.title);
        lv_obj_set_width(t, w - 12);
        lv_obj_set_style_text_align(t, LV_TEXT_ALIGN_CENTER, 0);
        lv_label_set_long_mode(t, LV_LABEL_LONG_DOT);
        lv_obj_align(t, LV_ALIGN_BOTTOM_MID, 0, -12);
    }
    apps_empty = label(apps_page, F16, C_FAINT);
    set_text(apps_empty, "Ayar dosyasında [uygulamalar] listesi yok");
    lv_obj_align(apps_empty, LV_ALIGN_CENTER, 0, -20);
    if (app_count) {
        lv_obj_add_flag(apps_empty, LV_OBJ_FLAG_HIDDEN);
    }
}

// =====================================================================================
// 4) Geliştirici (Faz 7B): Claude Code oturumları · GitHub Actions · sunucular
// =====================================================================================
constexpr int CC_ROWS = 4, GH_ROWS = 4, SRV_MAX = 8, CU_MAX = 2;
struct Row {
    lv_obj_t *dot, *name, *info;
};
Row cc_rows[CC_ROWS], gh_rows[GH_ROWS];
lv_obj_t *cc_count, *cc_empty, *gh_foot, *gh_empty, *git_line;
struct UsageRow {
    lv_obj_t *name, *bar, *info;
};
UsageRow cu_rows[CU_MAX];
struct Chip {
    lv_obj_t *box, *dot, *name, *info;
};
Chip chips[SRV_MAX];
lv_obj_t *srv_empty;

lv_obj_t *dot(lv_obj_t *parent, int x, int y, int d)
{
    lv_obj_t *o = lv_obj_create(parent);
    lv_obj_remove_style_all(o);
    lv_obj_set_pos(o, x, y);
    lv_obj_set_size(o, d, d);
    lv_obj_set_style_radius(o, LV_RADIUS_CIRCLE, 0);
    lv_obj_set_style_bg_opa(o, LV_OPA_COVER, 0);
    lv_obj_set_style_bg_color(o, C_FAINT, 0);
    lv_obj_clear_flag(o, LV_OBJ_FLAG_CLICKABLE);
    return o;
}

Row make_row(lv_obj_t *c, int y, int name_w)
{
    Row r;
    r.dot = dot(c, 16, y + 6, 10);
    r.name = label(c, F16, C_TEXT);
    lv_obj_set_pos(r.name, 34, y);
    lv_obj_set_width(r.name, name_w);
    lv_label_set_long_mode(r.name, LV_LABEL_LONG_DOT);
    int info_w = 364 - 34 - name_w - 8;
    r.info = label_right(c, F14, C_MUTED, 364, y + 2, info_w);
    lv_label_set_long_mode(r.info, LV_LABEL_LONG_DOT);
    return r;
}

void row_visible(Row &r, bool on)
{
    lv_obj_t *objs[3] = {r.dot, r.name, r.info};
    for (lv_obj_t *o : objs) {
        if (on) {
            lv_obj_clear_flag(o, LV_OBJ_FLAG_HIDDEN);
        } else {
            lv_obj_add_flag(o, LV_OBJ_FLAG_HIDDEN);
        }
    }
}

void show(lv_obj_t *o, bool on)
{
    if (on) {
        lv_obj_clear_flag(o, LV_OBJ_FLAG_HIDDEN);
    } else {
        lv_obj_add_flag(o, LV_OBJ_FLAG_HIDDEN);
    }
}

// Geçen süre: "45 sn", "12 dk", "3 sa", "2 gün"
void fmt_ago(char *out, size_t n, long sec)
{
    if (sec < 60) {
        snprintf(out, n, "%ld sn", sec < 0 ? 0 : sec);
    } else if (sec < 3600) {
        snprintf(out, n, "%ld dk", sec / 60);
    } else if (sec < 86400) {
        snprintf(out, n, "%ld sa", sec / 3600);
    } else {
        snprintf(out, n, "%ld gün", sec / 86400);
    }
}

void build_dev(lv_obj_t *page)
{
    lv_obj_t *cc = card(page, 14, 4, 380, 228);
    caption(cc, 16, 14, "CLAUDE CODE");
    cc_count = label_right(cc, F12, C_FAINT, 364, 14, 200);
    for (int i = 0; i < CC_ROWS; i++) {
        cc_rows[i] = make_row(cc, 42 + i * 36, 170);
        row_visible(cc_rows[i], false);
    }
    cc_empty = label(cc, F14, C_FAINT);
    set_text(cc_empty, "Açık oturum yok");
    lv_obj_set_pos(cc_empty, 16, 90);
    // Kullanım (hesap başına): ad · çubuk (en yoğun 5 sa penceresine göre) · token ve sıfırlanmaya kalan
    for (int i = 0; i < CU_MAX; i++) {
        UsageRow &u = cu_rows[i];
        int y = 182 + i * 22;
        u.name = label(cc, F12, C_MUTED, "");
        lv_obj_set_pos(u.name, 16, y);
        u.bar = bar(cc, 82, y + 5, 110, 6);
        u.info = label_right(cc, F12, C_MUTED, 364, y, 166);
        lv_label_set_long_mode(u.info, LV_LABEL_LONG_DOT);
        lv_obj_add_flag(u.name, LV_OBJ_FLAG_HIDDEN);
        lv_obj_add_flag(u.bar, LV_OBJ_FLAG_HIDDEN);
        lv_obj_add_flag(u.info, LV_OBJ_FLAG_HIDDEN);
    }

    lv_obj_t *gh = card(page, 406, 4, 380, 228);
    caption(gh, 16, 14, "GITHUB ACTIONS");
    for (int i = 0; i < GH_ROWS; i++) {
        gh_rows[i] = make_row(gh, 42 + i * 36, 170);
        row_visible(gh_rows[i], false);
    }
    gh_foot = label(gh, F12, C_MUTED, "");
    lv_obj_set_pos(gh_foot, 16, 182);
    lv_obj_set_width(gh_foot, 348);
    lv_label_set_long_mode(gh_foot, LV_LABEL_LONG_DOT);
    git_line = label(gh, F12, C_FAINT, "");
    lv_obj_set_pos(git_line, 16, 204);
    lv_obj_set_width(git_line, 348);
    lv_label_set_long_mode(git_line, LV_LABEL_LONG_DOT);
    gh_empty = label(gh, F14, C_FAINT);
    set_text(gh_empty, "yükleniyor…");
    lv_obj_set_pos(gh_empty, 16, 100);
    lv_obj_set_width(gh_empty, 348);
    lv_label_set_long_mode(gh_empty, LV_LABEL_LONG_DOT);

    lv_obj_t *sv = card(page, 14, 244, 772, 150);
    caption(sv, 14, 12, "SUNUCULAR");
    for (int i = 0; i < SRV_MAX; i++) {
        Chip &ch = chips[i];
        ch.box = lv_obj_create(sv);
        lv_obj_remove_style_all(ch.box);
        lv_obj_set_pos(ch.box, 14 + (i % 4) * 188, 36 + (i / 4) * 54);
        lv_obj_set_size(ch.box, 178, 46);
        lv_obj_set_style_bg_color(ch.box, C_CARD2, 0);
        lv_obj_set_style_bg_opa(ch.box, LV_OPA_COVER, 0);
        lv_obj_set_style_radius(ch.box, 10, 0);
        lv_obj_clear_flag(ch.box, LV_OBJ_FLAG_CLICKABLE);
        lv_obj_clear_flag(ch.box, LV_OBJ_FLAG_SCROLLABLE);
        ch.dot = dot(ch.box, 10, 18, 10);
        ch.name = label(ch.box, F14, C_TEXT, "");
        lv_obj_set_pos(ch.name, 28, 5);
        lv_obj_set_width(ch.name, 142);
        lv_label_set_long_mode(ch.name, LV_LABEL_LONG_DOT);
        ch.info = label(ch.box, F12, C_MUTED, "");
        lv_obj_set_pos(ch.info, 28, 25);
        lv_obj_set_width(ch.info, 142);
        lv_label_set_long_mode(ch.info, LV_LABEL_LONG_DOT);
        lv_obj_add_flag(ch.box, LV_OBJ_FLAG_HIDDEN);
    }
    srv_empty = label(sv, F14, C_FAINT);
    set_text(srv_empty, "Ayar dosyasında [[sunucu]] yok");
    lv_obj_set_pos(srv_empty, 14, 60);
}

}  // namespace

// =====================================================================================
// Dışa açık fonksiyonlar
// =====================================================================================
void ui_create()
{
    lv_obj_t *scr = lv_scr_act();
    lv_obj_set_style_bg_color(scr, C_BG, 0);
    lv_obj_clear_flag(scr, LV_OBJ_FLAG_SCROLLABLE);

    // Üst şerit
    lbl_clock = label(scr, F22, C_TEXT, "--:--");
    lv_obj_set_pos(lbl_clock, 18, 8);
    lbl_date = label(scr, F14, C_MUTED, "");
    lv_obj_align_to(lbl_date, lbl_clock, LV_ALIGN_OUT_RIGHT_BOTTOM, 14, -2);
    lbl_page = label(scr, F12, C_MUTED, PAGE_NAMES[0]);
    lv_obj_set_style_text_letter_space(lbl_page, 2, 0);
    lv_obj_align(lbl_page, LV_ALIGN_TOP_MID, 0, 14);
    link_lbl = label_right(scr, F12, C_MUTED, 782, 14, 140);
    lv_label_set_text(link_lbl, "Bağlantı yok");
    link_dot = lv_obj_create(scr);
    lv_obj_remove_style_all(link_dot);
    lv_obj_set_size(link_dot, 9, 9);
    lv_obj_set_style_radius(link_dot, LV_RADIUS_CIRCLE, 0);
    lv_obj_set_style_bg_opa(link_dot, LV_OPA_COVER, 0);
    lv_obj_set_style_bg_color(link_dot, C_BAD, 0);

    // Uyarı (sayfa adının yerine çıkar) ve hava durumu (bağlantı durumunun solunda)
    warn_pill = label(scr, F14, C_TEXT, "");
    lv_obj_set_style_bg_color(warn_pill, C_BAD, 0);
    lv_obj_set_style_bg_opa(warn_pill, LV_OPA_COVER, 0);
    lv_obj_set_style_radius(warn_pill, 12, 0);
    lv_obj_set_style_pad_hor(warn_pill, 12, 0);
    lv_obj_set_style_pad_ver(warn_pill, 4, 0);
    lv_obj_add_flag(warn_pill, LV_OBJ_FLAG_HIDDEN);
    dev_top = label_right(scr, F14, C_WARN, 640, 13, 190);
    lv_obj_add_flag(dev_top, LV_OBJ_FLAG_HIDDEN);

    // Sayfalar
    tileview = lv_tileview_create(scr);
    lv_obj_set_pos(tileview, 0, TOP_H);
    lv_obj_set_size(tileview, 800, PAGE_H);
    lv_obj_set_style_bg_opa(tileview, LV_OPA_TRANSP, 0);
    lv_obj_set_scrollbar_mode(tileview, LV_SCROLLBAR_MODE_OFF);
    lv_obj_add_event_cb(tileview, tile_changed_cb, LV_EVENT_VALUE_CHANGED, nullptr);
    lv_obj_t *t0 = lv_tileview_add_tile(tileview, 0, 0, LV_DIR_RIGHT);
    lv_obj_t *t1 = lv_tileview_add_tile(tileview, 1, 0, LV_DIR_LEFT | LV_DIR_RIGHT);
    lv_obj_t *t2 = lv_tileview_add_tile(tileview, 2, 0, LV_DIR_LEFT | LV_DIR_RIGHT);
    lv_obj_t *t3 = lv_tileview_add_tile(tileview, 3, 0, LV_DIR_LEFT | LV_DIR_RIGHT);
    lv_obj_t *t4 = lv_tileview_add_tile(tileview, 4, 0, LV_DIR_LEFT);
    build_system(t0);
    build_media(t1);
    apps_page = t2;
    build_apps();
    shortcut_page = t3;
    load_default_tiles();
    build_shortcuts(t3);
    build_dev(t4);

    // Sayfa noktaları
    for (int i = 0; i < PAGES; i++) {
        page_dots[i] = lv_obj_create(scr);
        lv_obj_remove_style_all(page_dots[i]);
        lv_obj_set_size(page_dots[i], i == 0 ? 20 : 7, 7);
        lv_obj_set_style_radius(page_dots[i], 4, 0);
        lv_obj_set_style_bg_opa(page_dots[i], LV_OPA_COVER, 0);
        lv_obj_set_style_bg_color(page_dots[i], i == 0 ? C_ACCENT : C_LINE, 0);
        lv_obj_clear_flag(page_dots[i], LV_OBJ_FLAG_CLICKABLE);
    }
    // Etkin nokta genişleyince diğerleri kendiliğinden kaysın diye noktalar bir flex satırında
    lv_obj_t *row = lv_obj_create(scr);
    lv_obj_remove_style_all(row);
    lv_obj_set_size(row, 80, 7);
    lv_obj_align(row, LV_ALIGN_BOTTOM_MID, 0, -10);
    lv_obj_set_flex_flow(row, LV_FLEX_FLOW_ROW);
    lv_obj_set_flex_align(row, LV_FLEX_ALIGN_CENTER, LV_FLEX_ALIGN_CENTER, LV_FLEX_ALIGN_CENTER);
    lv_obj_set_style_pad_column(row, 8, 0);
    lv_obj_clear_flag(row, LV_OBJ_FLAG_CLICKABLE);
    for (int i = 0; i < PAGES; i++) {
        lv_obj_set_parent(page_dots[i], row);
    }

    // Toast
    toast = label(scr, F14, C_TEXT, "");
    lv_obj_set_style_bg_color(toast, C_CARD2, 0);
    lv_obj_set_style_bg_opa(toast, LV_OPA_COVER, 0);
    lv_obj_set_style_radius(toast, 10, 0);
    lv_obj_set_style_pad_hor(toast, 16, 0);
    lv_obj_set_style_pad_ver(toast, 9, 0);
    lv_obj_add_flag(toast, LV_OBJ_FLAG_HIDDEN);

    // Üst katman, alttan üste: kilit saati · bildirim balonu · karartma perdesi
    build_lock_screen();
    build_notif();
    sleep_overlay = lv_obj_create(lv_layer_top());
    lv_obj_remove_style_all(sleep_overlay);
    lv_obj_set_size(sleep_overlay, 800, 480);
    lv_obj_set_style_bg_color(sleep_overlay, lv_color_black(), 0);
    lv_obj_set_style_bg_opa(sleep_overlay, LV_OPA_COVER, 0);
    lv_obj_add_flag(sleep_overlay, LV_OBJ_FLAG_CLICKABLE);
    // dokunma burada tükenir, alttaki düğmelere geçmez
    lv_obj_add_event_cb(sleep_overlay, [](lv_event_t *e) { wake_requested = true; }, LV_EVENT_PRESSED, nullptr);
    lv_obj_add_flag(sleep_overlay, LV_OBJ_FLAG_HIDDEN);

    ui_set_link(false);
}

void ui_set_link(bool ok)
{
    set_text(link_lbl, ok ? "Bağlı" : "Bağlantı yok");
    lv_obj_set_style_text_color(link_lbl, ok ? C_MUTED : C_BAD, 0);
    lv_obj_set_style_bg_color(link_dot, ok ? C_OK : C_BAD, 0);
    lv_obj_update_layout(link_lbl);
    // Nokta, sağa dayalı yazının hemen soluna
    lv_point_t sz;
    lv_txt_get_size(&sz, lv_label_get_text(link_lbl), F12, 0, 0, LV_COORD_MAX, LV_TEXT_FLAG_NONE);
    lv_obj_set_pos(link_dot, 782 - sz.x - 17, 18);
}

void ui_update_stat(JsonObjectConst o)
{
    char buf[48], a[24], b[24];

    if (o["clock"].is<const char *>()) {
        lv_label_set_text(lbl_clock, o["clock"].as<const char *>());
        set_text(lbl_date, o["date"] | "");
        lv_obj_align_to(lbl_date, lbl_clock, LV_ALIGN_OUT_RIGHT_BOTTOM, 14, -2);
        if (!lv_obj_has_flag(lock_scr, LV_OBJ_FLAG_HIDDEN)) {  // kilit saati yalnızca görünürken çizilsin
            if (strcmp(lv_label_get_text(lock_clock), o["clock"].as<const char *>()) != 0) {
                lv_label_set_text(lock_clock, o["clock"].as<const char *>());
            }
            set_text(lock_date, o["date"] | "");
        }
    }

    // CPU
    float c = o["cpu"] | 0.0f;
    lv_arc_set_value(cpu.arc, static_cast<int>(c + 0.5f));
    lv_obj_set_style_arc_color(cpu.arc, level_color(c), LV_PART_INDICATOR);
    lv_label_set_text_fmt(cpu.num, "%d", static_cast<int>(c + 0.5f));
    lv_obj_align_to(cpu.num, cpu.arc, LV_ALIGN_CENTER, 0, -6);
    lv_chart_set_next_value(cpu.chart, cpu.ser, static_cast<lv_coord_t>(c));
    if (!o["cpu_t"].isNull()) {
        float t = o["cpu_t"];
        lv_label_set_text_fmt(cpu.v1, "%d°C", static_cast<int>(t + 0.5f));
        lv_obj_set_style_text_color(cpu.v1, temp_color(t), 0);
    }
    fmt_dec(a, sizeof(a), (o["cpu_mhz"] | 0) / 1000.0f, 2);
    snprintf(buf, sizeof(buf), "%s GHz", a);
    lv_label_set_text(cpu.v2, buf);
    lv_label_set_text_fmt(cpu.v3, "%%%d", o["cpu_max"] | 0);

    // GPU
    if (!o["gpu"].isNull()) {
        float g = o["gpu"];
        lv_arc_set_value(gpu.arc, static_cast<int>(g + 0.5f));
        lv_obj_set_style_arc_color(gpu.arc, level_color(g), LV_PART_INDICATOR);
        lv_label_set_text_fmt(gpu.num, "%d", static_cast<int>(g + 0.5f));
        lv_obj_align_to(gpu.num, gpu.arc, LV_ALIGN_CENTER, 0, -6);
        lv_chart_set_next_value(gpu.chart, gpu.ser, static_cast<lv_coord_t>(g));
        float gt = o["gpu_t"] | 0.0f;
        lv_label_set_text_fmt(gpu.v1, "%d°C", static_cast<int>(gt + 0.5f));
        lv_obj_set_style_text_color(gpu.v1, temp_color(gt), 0);
        lv_label_set_text_fmt(gpu.v2, "%d W", o["gpu_w"] | 0);
        lv_label_set_text_fmt(gpu.v3, "%%%d", o["gpu_fan"] | 0);

        float vu = (o["vram"] | 0.0f) / 1024, vt = (o["vram_tot"] | 1.0f) / 1024;
        fmt_dec(a, sizeof(a), vu);
        lv_label_set_text(vram.main, a);
        lv_label_set_text_fmt(vram.sub, "/ %d GB", static_cast<int>(vt + 0.5f));
        lv_obj_align_to(vram.sub, vram.main, LV_ALIGN_OUT_RIGHT_BOTTOM, 6, -3);
        set_bar(vram.bar, vu / vt * 100, level_color(vu / vt * 100));
    }

    // RAM
    float ru = (o["ram"] | 0.0f) / 1024, rt = (o["ram_tot"] | 1.0f) / 1024;
    fmt_dec(a, sizeof(a), ru);
    lv_label_set_text(ram.main, a);
    lv_label_set_text_fmt(ram.sub, "/ %d GB", static_cast<int>(rt + 0.5f));
    lv_obj_align_to(ram.sub, ram.main, LV_ALIGN_OUT_RIGHT_BOTTOM, 6, -3);
    set_bar(ram.bar, ru / rt * 100, level_color(ru / rt * 100));
    lv_label_set_text_fmt(ram.foot, "swap %%%d", o["swap"] | 0);

    // Diskler
    JsonArrayConst disks = o["disks"];
    for (int i = 0; i < 2 && i < static_cast<int>(disks.size()); i++) {
        float p = disks[i]["p"] | 0.0f;
        const char *m = disks[i]["m"] | "?";
        if (i == 0) {
            snprintf(buf, sizeof(buf), "Sistem %s", m);
        } else {
            snprintf(buf, sizeof(buf), "Veri %s", m);
        }
        set_text(disk_name[i], buf);
        lv_label_set_text_fmt(disk_pct[i], "%%%d", static_cast<int>(p + 0.5f));
        set_bar(disk_bar[i], p, level_color(p));
    }
    fmt_rate(a, sizeof(a), o["dsk_r"] | 0.0f);
    fmt_rate(b, sizeof(b), o["dsk_w"] | 0.0f);
    lv_label_set_text_fmt(disk_io, "oku %s · yaz %s", a, b);

    // Ağ
    fmt_rate(a, sizeof(a), o["net_dn"] | 0.0f);
    lv_label_set_text(net_dn, a);
    fmt_rate(a, sizeof(a), o["net_up"] | 0.0f);
    lv_label_set_text(net_up, a);
    long up = o["up"] | 0L;
    if (up >= 86400) {
        snprintf(buf, sizeof(buf), "PC açık: %ld gün %ld sa", up / 86400, up / 3600 % 24);
    } else {
        snprintf(buf, sizeof(buf), "PC açık: %ld sa %ld dk", up / 3600, up / 60 % 60);
    }
    set_text(pc_up, buf);
}

void ui_update_media(JsonObjectConst o)
{
    const char *st = o["st"] | "none";
    bool none = strcmp(st, "none") == 0;
    bool playing = strcmp(st, "play") == 0;

    set_text(m_pill, none ? "Çalar yok" : (o["pl"] | ""));
    set_text(m_state, none ? "" : playing ? "çalıyor" : strcmp(st, "pause") == 0 ? "duraklatıldı" : "durdu");
    lv_obj_align_to(m_state, m_pill, LV_ALIGN_OUT_RIGHT_MID, 8, 0);
    lv_label_set_text(m_pp_lbl, playing ? LV_SYMBOL_PAUSE : LV_SYMBOL_PLAY);
    lv_obj_center(m_pp_lbl);
    lv_obj_set_style_bg_color(m_pp, playing ? C_ACCENT : C_CARD, 0);

    const char *title = none ? "Çalan bir şey yok" : (o["ti"] | "");
#if PC_PANEL_TR_FONTS
    if (strcmp(lv_label_get_text(m_title), title) != 0) {  // aynıysa kayan yazı baştan başlamasın
        lv_label_set_text(m_title, title[0] ? title : "(başlık yok)");
    }
#else
    char tbuf[256];
    translit(title, tbuf, sizeof(tbuf));
    if (strcmp(lv_label_get_text(m_title), tbuf) != 0) {
        lv_label_set_text(m_title, tbuf[0] ? tbuf : "(no title)");
    }
#endif
    set_text(m_artist, none ? "" : (o["ar"] | ""));
    set_text(m_album, none ? "" : (o["al"] | ""));

    int len = none ? 0 : (o["len"] | 0), pos = none ? 0 : (o["pos"] | 0);
    media_len = len;
    char a[16];
    fmt_time(a, sizeof(a), len);
    lv_label_set_text(m_len, a);
    if (!lv_obj_has_state(m_seek, LV_STATE_PRESSED)) {  // kullanıcı sürüklerken üzerine yazma
        lv_slider_set_range(m_seek, 0, len > 0 ? len : 1);
        lv_slider_set_value(m_seek, pos, LV_ANIM_OFF);
        fmt_time(a, sizeof(a), pos);
        lv_label_set_text(m_pos, a);
    }
    bool can_seek = !none && (o["can"]["sk"] | 0) && len > 0;
    if (can_seek) {
        lv_obj_clear_state(m_seek, LV_STATE_DISABLED);
    } else {
        lv_obj_add_state(m_seek, LV_STATE_DISABLED);
    }
}

void ui_update_vol(JsonObjectConst o)
{
    bool mute = (o["mute"] | 0) != 0;
    int v = o["v"] | 0;
    if (!lv_obj_has_state(v_slider, LV_STATE_PRESSED)) {
        lv_slider_set_value(v_slider, v, LV_ANIM_OFF);
        if (mute) {
            set_text(v_pct, "sessiz");
        } else {
            lv_label_set_text_fmt(v_pct, "%d%%", v);
        }
    }
    lv_label_set_text(v_icon, mute ? LV_SYMBOL_MUTE : LV_SYMBOL_VOLUME_MAX);
    lv_obj_set_style_text_color(v_icon, mute ? C_ACCENT : C_MUTED, 0);
    bool mic = (o["mic_mute"] | 0) != 0;
    if (mute != mute_off || mic != mic_off) {
        mute_off = mute;
        mic_off = mic;
        refresh_toggles();
    }
}

void ui_set_art(const uint8_t *rgb565, int w, int h)
{
    art_dsc.header.always_zero = 0;
    art_dsc.header.cf = LV_IMG_CF_TRUE_COLOR;
    art_dsc.header.w = w;
    art_dsc.header.h = h;
    art_dsc.data_size = static_cast<uint32_t>(w) * h * 2;
    art_dsc.data = rgb565;
    lv_img_cache_invalidate_src(&art_dsc);  // aynı tanımlayıcı, yeni veri
    lv_img_set_src(art_img, &art_dsc);
    lv_obj_clear_flag(art_img, LV_OBJ_FLAG_HIDDEN);
    lv_obj_add_flag(art_note, LV_OBJ_FLAG_HIDDEN);
    lv_obj_invalidate(art_img);
}

void ui_clear_art()
{
    lv_obj_add_flag(art_img, LV_OBJ_FLAG_HIDDEN);
    lv_obj_clear_flag(art_note, LV_OBJ_FLAG_HIDDEN);
}

// ---- Faz 7: kısayollar, bildirim, uyarı, hava durumu, kilit saati ----
void ui_set_tiles(JsonArrayConst items)
{
    // Aynı liste tekrar gelirse yeniden kurma (yeniden bağlanmalarda LVGL'yi boşuna meşgul etmesin)
    bool same = static_cast<int>(items.size()) == tile_count;
    int k = 0;
    for (JsonObjectConst it : items) {
        if (!same || k >= MAX_TILES) {
            break;
        }
        const Tile &t = tiles[k++];
        const char *tg = it["tg"] | "";
        Toggle want = strcmp(tg, "mic") == 0 ? TG_MIC : strcmp(tg, "mute") == 0 ? TG_MUTE : TG_NONE;
        same = strcmp(t.id, it["id"] | "") == 0 && strcmp(t.title, it["ti"] | "?") == 0 &&
               strcmp(t.desc, it["de"] | "") == 0 && t.icon == ICON(it["ic"] | "star") && t.tg == want;
    }
    if (same) {
        return;
    }
    int n = 0;
    for (JsonObjectConst it : items) {
        if (n >= MAX_TILES) {
            break;
        }
        const char *id = it["id"] | "";
        if (!id[0]) {
            continue;
        }
        const char *tg = it["tg"] | "";
        Toggle t = strcmp(tg, "mic") == 0 ? TG_MIC : strcmp(tg, "mute") == 0 ? TG_MUTE : TG_NONE;
        set_tile(tiles[n++], id, it["ic"] | "star", it["ti"] | "?", it["de"] | "", t);
    }
    if (n == 0) {
        load_default_tiles();
    } else {
        tile_count = n;
    }
    build_shortcuts(shortcut_page);
}

void ui_show_notif(const char *app, const char *title, const char *body, const char *lvl, uint32_t ms)
{
    const char *icon = LV_SYMBOL_BELL;
    lv_color_t color = C_ACCENT;
    if (strcmp(lvl, "ok") == 0) {
        icon = LV_SYMBOL_OK;
        color = C_OK;
    } else if (strcmp(lvl, "err") == 0) {
        icon = LV_SYMBOL_CLOSE;
        color = C_BAD;
    } else if (strcmp(lvl, "wait") == 0) {
        icon = LV_SYMBOL_WARNING;
        color = C_WARN;
    }
    lv_label_set_text(notif_icon, icon);
    lv_obj_set_style_text_color(notif_icon, color, 0);
    lv_obj_set_style_border_color(notif_box, strcmp(lvl, "info") == 0 ? C_LINE : color, 0);
    set_text(notif_app, app);
    set_text(notif_title, title && title[0] ? title : body);
    set_text(notif_body, title && title[0] ? body : "");
    bool was_hidden = lv_obj_has_flag(notif_box, LV_OBJ_FLAG_HIDDEN);
    lv_obj_clear_flag(notif_box, LV_OBJ_FLAG_HIDDEN);
    if (was_hidden) {  // yukarıdan kayarak gelsin
        lv_anim_t a;
        lv_anim_init(&a);
        lv_anim_set_var(&a, notif_box);
        lv_anim_set_exec_cb(&a, anim_y_cb);
        lv_anim_set_values(&a, -100, 6);
        lv_anim_set_time(&a, 220);
        lv_anim_set_path_cb(&a, lv_anim_path_ease_out);
        lv_anim_start(&a);
    }
    if (notif_timer) {
        lv_timer_set_period(notif_timer, ms);
        lv_timer_reset(notif_timer);
    } else {
        notif_timer = lv_timer_create(notif_hide_cb, ms, nullptr);
        lv_timer_set_repeat_count(notif_timer, 1);
    }
}

bool ui_set_warn(const char *text)
{
    bool was = !lv_obj_has_flag(warn_pill, LV_OBJ_FLAG_HIDDEN);
    bool now = text && text[0];
    if (now) {
        char buf[160];
        snprintf(buf, sizeof(buf), LV_SYMBOL_WARNING " %s", text);
        if (strcmp(lv_label_get_text(warn_pill), buf) != 0) {
            set_text(warn_pill, buf);
            set_text(lock_warn, buf);
            lv_obj_align(warn_pill, LV_ALIGN_TOP_MID, 0, 8);
            lv_obj_align(lock_warn, LV_ALIGN_TOP_MID, 0, 50);
        }
        lv_obj_clear_flag(warn_pill, LV_OBJ_FLAG_HIDDEN);
        lv_obj_clear_flag(lock_warn, LV_OBJ_FLAG_HIDDEN);
        lv_obj_add_flag(lbl_page, LV_OBJ_FLAG_HIDDEN);
    } else if (was) {
        lv_obj_add_flag(warn_pill, LV_OBJ_FLAG_HIDDEN);
        lv_obj_add_flag(lock_warn, LV_OBJ_FLAG_HIDDEN);
        lv_obj_clear_flag(lbl_page, LV_OBJ_FLAG_HIDDEN);
    }
    return now && !was;
}

// ---- Faz 7B: Geliştirici sayfası ----
void ui_update_cc(JsonObjectConst o)
{
    JsonArrayConst items = o["items"];
    int n = 0;
    char buf[96], ago[24];
    for (JsonObjectConst it : items) {
        if (n >= CC_ROWS) {
            break;
        }
        Row &r = cc_rows[n++];
        const char *st = it["s"] | "idle";
        fmt_ago(ago, sizeof(ago), it["age"] | 0L);
        lv_color_t c = C_FAINT;
        if (strcmp(st, "work") == 0) {
            c = C_ACCENT;
            snprintf(buf, sizeof(buf), "çalışıyor · %s", ago);
        } else if (strcmp(st, "wait") == 0) {
            c = C_WARN;
            snprintf(buf, sizeof(buf), "%s · %s", it["m"] | "bekliyor", ago);
        } else if (strcmp(st, "done") == 0) {
            c = C_OK;
            snprintf(buf, sizeof(buf), "bitti · %s", ago);
        } else {
            snprintf(buf, sizeof(buf), "boşta");
        }
        set_text(r.name, it["p"] | "?");
        set_text(r.info, buf);
        lv_obj_set_style_text_color(r.info, strcmp(st, "idle") == 0 ? C_FAINT : c, 0);
        lv_obj_set_style_bg_color(r.dot, c, 0);
        row_visible(r, true);
    }
    for (int i = n; i < CC_ROWS; i++) {
        row_visible(cc_rows[i], false);
    }
    show(cc_empty, n == 0);
    int total = items.size();
    if (total) {
        lv_label_set_text_fmt(cc_count, "%d oturum", total);
    } else {
        lv_label_set_text(cc_count, "");
    }

    // Üst şerit ve kilit ekranı: bekleyen oturum varsa sarı, yalnızca çalışan varsa sönük
    int wait = o["wait"] | 0, work = o["work"] | 0;
    if (wait) {
        snprintf(buf, sizeof(buf), "Claude: %d bekliyor", wait);
        set_text(dev_top, buf);
        lv_obj_set_style_text_color(dev_top, C_WARN, 0);
        snprintf(buf, sizeof(buf), "Claude: %d oturum seni bekliyor", wait);
        set_text(lock_dev, buf);
        lv_obj_align(lock_dev, LV_ALIGN_BOTTOM_MID, 0, -50);
    } else if (work) {
        set_text(dev_top, "Claude çalışıyor");
        lv_obj_set_style_text_color(dev_top, C_MUTED, 0);
    }
    show(dev_top, wait || work);
    show(lock_dev, wait);
}

void ui_update_gh(JsonObjectConst o)
{
    char buf[96], ago[24];
    if (!(o["ok"] | 0)) {
        for (Row &r : gh_rows) {
            row_visible(r, false);
        }
        snprintf(buf, sizeof(buf), "GitHub: %s", o["err"] | "?");
        set_text(gh_empty, buf);
        show(gh_empty, true);
        lv_label_set_text(gh_foot, "");
        return;
    }
    int n = 0;
    for (JsonObjectConst it : o["runs"].as<JsonArrayConst>()) {
        if (n >= GH_ROWS) {
            break;
        }
        Row &r = gh_rows[n++];
        const char *st = it["s"] | "";
        lv_color_t c = strcmp(st, "ok") == 0     ? C_OK
                       : strcmp(st, "fail") == 0 ? C_BAD
                       : strcmp(st, "run") == 0  ? C_ACCENT
                       : strcmp(st, "wait") == 0 ? C_WARN
                                                 : C_FAINT;
        fmt_ago(ago, sizeof(ago), it["age"] | 0L);
        const char *what = strcmp(st, "run") == 0    ? "çalışıyor"
                           : strcmp(st, "wait") == 0 ? "sırada"
                           : strcmp(st, "fail") == 0 ? "başarısız"
                                                     : (it["w"] | "");
        snprintf(buf, sizeof(buf), "%s · %s", what, ago);
        set_text(r.name, it["r"] | "?");
        set_text(r.info, buf);
        lv_obj_set_style_text_color(r.info, strcmp(st, "fail") == 0 ? C_BAD : C_MUTED, 0);
        lv_obj_set_style_bg_color(r.dot, c, 0);
        row_visible(r, true);
    }
    for (int i = n; i < GH_ROWS; i++) {
        row_visible(gh_rows[i], false);
    }
    set_text(gh_empty, "Actions çalışması yok");
    show(gh_empty, n == 0);
    snprintf(buf, sizeof(buf), "İnceleme bekleyen PR: %d · açık PR: %d · bildirim: %d", o["rev"] | 0,
             o["prs"] | 0, o["ntf"] | 0);
    set_text(gh_foot, buf);
}

void ui_update_srv(JsonObjectConst o)
{
    int n = 0;
    char buf[48];
    for (JsonObjectConst it : o["items"].as<JsonArrayConst>()) {
        if (n >= SRV_MAX) {
            break;
        }
        Chip &ch = chips[n++];
        int ok = it["ok"] | -1;
        set_text(ch.name, it["n"] | "?");
        if (ok == 0) {
            set_text(ch.info, "yanıt yok");
        } else if (it["ms"].isNull()) {
            set_text(ch.info, "denetleniyor…");
        } else if (!it["ssl"].isNull()) {
            snprintf(buf, sizeof(buf), "%d ms · SSL %d gün", it["ms"].as<int>(), it["ssl"].as<int>());
            set_text(ch.info, buf);
        } else {
            lv_label_set_text_fmt(ch.info, "%d ms", it["ms"].as<int>());
        }
        lv_obj_set_style_text_color(ch.info, ok == 0 ? C_BAD : C_MUTED, 0);
        lv_obj_set_style_bg_color(ch.dot, ok == 1 ? C_OK : ok == 0 ? C_BAD : C_WARN, 0);
        lv_obj_clear_flag(ch.box, LV_OBJ_FLAG_HIDDEN);
    }
    for (int i = n; i < SRV_MAX; i++) {
        lv_obj_add_flag(chips[i].box, LV_OBJ_FLAG_HIDDEN);
    }
    show(srv_empty, n == 0);
}

void ui_update_cu(JsonObjectConst o)
{
    int n = 0;
    char buf[64];
    for (JsonObjectConst a : o["acc"].as<JsonArrayConst>()) {
        if (n >= CU_MAX) {
            break;
        }
        UsageRow &u = cu_rows[n++];
        int pct = a["pct"] | 0;
        long rst = a["rst"] | -1L;
        set_text(u.name, a["n"] | "?");
        set_bar(u.bar, pct > 100 ? 100 : pct, pct < 60 ? C_ACCENT : pct < 85 ? C_WARN : C_BAD);
        if (rst < 0) {
            set_text(u.info, "pencere yok");
        } else {
            char left[24];
            if (rst >= 3600) {
                snprintf(left, sizeof(left), "%ld sa %ld dk", rst / 3600, rst / 60 % 60);
            } else {
                snprintf(left, sizeof(left), "%ld dk", rst / 60);
            }
            snprintf(buf, sizeof(buf), "%s · %s sonra", a["txt"] | "0", left);
            set_text(u.info, buf);
        }
        lv_obj_clear_flag(u.name, LV_OBJ_FLAG_HIDDEN);
        lv_obj_clear_flag(u.bar, LV_OBJ_FLAG_HIDDEN);
        lv_obj_clear_flag(u.info, LV_OBJ_FLAG_HIDDEN);
    }
    for (int i = n; i < CU_MAX; i++) {
        lv_obj_add_flag(cu_rows[i].name, LV_OBJ_FLAG_HIDDEN);
        lv_obj_add_flag(cu_rows[i].bar, LV_OBJ_FLAG_HIDDEN);
        lv_obj_add_flag(cu_rows[i].info, LV_OBJ_FLAG_HIDDEN);
    }
}

void ui_update_git(JsonObjectConst o)
{
    set_text(git_line, o["txt"] | "");
    lv_obj_set_style_text_color(git_line, (o["n"] | 0) ? C_WARN : C_FAINT, 0);
}

void ui_set_apps(JsonArrayConst items)
{
    // Liste aynıysa sayfayı yeniden kurma: ikonlar yerinde kalsın (yeniden bağlanınca aynı liste tekrar gelir)
    bool same = static_cast<int>(items.size()) == app_count;
    int k = 0;
    for (JsonObjectConst it : items) {
        if (!same || k >= MAX_APPS) {
            break;
        }
        same = strcmp(apps[k].id, it["id"] | "") == 0 && strcmp(apps[k].title, it["ti"] | (it["id"] | "")) == 0;
        k++;
    }
    if (same) {
        return;
    }
    int n = 0;
    for (JsonObjectConst it : items) {
        if (n >= MAX_APPS) {
            break;
        }
        const char *id = it["id"] | "";
        if (!id[0]) {
            continue;
        }
        strlcpy(apps[n].id, id, sizeof(apps[n].id));
        strlcpy(apps[n].title, it["ti"] | id, sizeof(apps[n].title));
        n++;
    }
    app_count = n;
    build_apps();  // ikonlar ardından `icon` bloklarıyla gelir
}

void ui_set_app_icon(int index, const uint8_t *data, int w, int h)
{
    if (index < 0 || index >= app_count || w != APP_ICON_PX || h != APP_ICON_PX) {
        return;
    }
    AppTile &a = apps[index];
    if (!a.px) {
        a.px = static_cast<uint8_t *>(heap_caps_malloc(APP_ICON_BYTES, MALLOC_CAP_SPIRAM));
        if (!a.px) {
            return;
        }
    }
    memcpy(a.px, data, APP_ICON_BYTES);
    a.dsc.header.always_zero = 0;
    a.dsc.header.cf = LV_IMG_CF_TRUE_COLOR_ALPHA;
    a.dsc.header.w = w;
    a.dsc.header.h = h;
    a.dsc.data_size = APP_ICON_BYTES;
    a.dsc.data = a.px;
    lv_img_cache_invalidate_src(&a.dsc);
    lv_img_set_src(a.img, &a.dsc);
    lv_obj_clear_flag(a.img, LV_OBJ_FLAG_HIDDEN);
    lv_obj_add_flag(a.letter, LV_OBJ_FLAG_HIDDEN);
    lv_obj_invalidate(a.img);
}

void ui_set_lock_clock(bool on)
{
    if (on) {
        lv_obj_clear_flag(lock_scr, LV_OBJ_FLAG_HIDDEN);
        lv_label_set_text(lock_clock, lv_label_get_text(lbl_clock));  // görünür olur olmaz güncel saat
        lv_label_set_text(lock_date, lv_label_get_text(lbl_date));
    } else {
        lv_obj_add_flag(lock_scr, LV_OBJ_FLAG_HIDDEN);
    }
}

// ---- Ekran karartma ----
void ui_set_sleep(bool dark)
{
    if (dark) {
        lv_obj_clear_flag(sleep_overlay, LV_OBJ_FLAG_HIDDEN);
    } else {
        lv_obj_add_flag(sleep_overlay, LV_OBJ_FLAG_HIDDEN);
    }
}

bool ui_take_wake_request()
{
    if (!wake_requested) {
        return false;
    }
    wake_requested = false;
    return true;
}
