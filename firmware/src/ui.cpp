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
lv_obj_t *tileview, *page_dots[3];
lv_obj_t *toast;
lv_timer_t *toast_timer;

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

struct Tile {
    const char *id, *icon, *title, *desc;
    bool toggle;
    lv_obj_t *obj, *icon_lbl, *desc_lbl;
};
Tile tiles[] = {
    {"lock", ICON_LOCK, "Ekranı kilitle", "KDE oturumu", false},
    {"mic", ICON_MIC, "Mikrofon", "açık", true},
    {"screenshot", ICON_CAMERA, "Ekran görüntüsü", "Spectacle", false},
    {"mute", ICON_VOLUME, "Sesi kapat", "açık", true},
    {"terminal", ICON_TERMINAL, "Terminal", "Konsole", false},
    {"browser", ICON_GLOBE, "Tarayıcı", "Zen", false},
    {"files", ICON_FOLDER, "Dosyalar", "Dolphin", false},
    {"spotify", ICON_SPOTIFY, "Spotify", "öne getir", false},
};
constexpr int TILE_COUNT = sizeof(tiles) / sizeof(tiles[0]);
const char *const PAGE_NAMES[3] = {"SİSTEM", "MEDYA", "KISAYOLLAR"};

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
    for (int i = 0; i < 3; i++) {
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
    link_send_shortcut("mute");
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
    char msg[64];
    snprintf(msg, sizeof(msg), "%s…", t->title);
    show_toast(msg);
}

void build_shortcuts(lv_obj_t *page)
{
    const int w = 184, h = 178, gap = 12;
    for (int i = 0; i < TILE_COUNT; i++) {
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
        lv_obj_align(t.icon_lbl, LV_ALIGN_CENTER, 0, -26);
        lv_obj_t *title = label(t.obj, F16, C_TEXT, t.title);
        lv_obj_align(title, LV_ALIGN_CENTER, 0, 22);
        t.desc_lbl = label(t.obj, F12, C_MUTED, t.desc);
        lv_obj_align(t.desc_lbl, LV_ALIGN_CENTER, 0, 44);
    }
}

void set_tile_toggle(const char *id, bool off)
{
    for (int i = 0; i < TILE_COUNT; i++) {
        Tile &t = tiles[i];
        if (strcmp(t.id, id) != 0) {
            continue;
        }
        lv_obj_set_style_text_color(t.icon_lbl, off ? C_ACCENT : C_TEXT, 0);
        lv_obj_set_style_text_color(t.desc_lbl, off ? C_ACCENT : C_MUTED, 0);
        set_text(t.desc_lbl, off ? "kapalı" : "açık");
        if (strcmp(id, "mic") == 0) {
            lv_label_set_text(t.icon_lbl, off ? ICON_MIC_OFF : ICON_MIC);
        } else if (strcmp(id, "mute") == 0) {
            lv_label_set_text(t.icon_lbl, off ? ICON_VOLUME_OFF : ICON_VOLUME);
        }
        lv_obj_align(t.icon_lbl, LV_ALIGN_CENTER, 0, -26);
        lv_obj_align(t.desc_lbl, LV_ALIGN_CENTER, 0, 44);
    }
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

    // Sayfalar
    tileview = lv_tileview_create(scr);
    lv_obj_set_pos(tileview, 0, TOP_H);
    lv_obj_set_size(tileview, 800, PAGE_H);
    lv_obj_set_style_bg_opa(tileview, LV_OPA_TRANSP, 0);
    lv_obj_set_scrollbar_mode(tileview, LV_SCROLLBAR_MODE_OFF);
    lv_obj_add_event_cb(tileview, tile_changed_cb, LV_EVENT_VALUE_CHANGED, nullptr);
    lv_obj_t *t0 = lv_tileview_add_tile(tileview, 0, 0, LV_DIR_RIGHT);
    lv_obj_t *t1 = lv_tileview_add_tile(tileview, 1, 0, LV_DIR_LEFT | LV_DIR_RIGHT);
    lv_obj_t *t2 = lv_tileview_add_tile(tileview, 2, 0, LV_DIR_LEFT);
    build_system(t0);
    build_media(t1);
    build_shortcuts(t2);

    // Sayfa noktaları
    for (int i = 0; i < 3; i++) {
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
    for (int i = 0; i < 3; i++) {
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
    set_tile_toggle("mute", mute);
    set_tile_toggle("mic", (o["mic_mute"] | 0) != 0);
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
