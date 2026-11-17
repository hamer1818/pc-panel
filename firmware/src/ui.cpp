/*
 * Faz 3 geçici arayüzü (800×480). Son tasarım Faz 4'te yapılacak.
 *
 * Not: LVGL'nin hazır Montserrat yazı tiplerinde Türkçe harf yok. Faz 4'te Türkçe yazı tipi gelene kadar
 * şarkı bilgilerindeki ç, ğ, ı, ö, ş, ü harfleri ASCII karşılıklarına çevriliyor (translit).
 */
#include "ui.h"

#include <Arduino.h>
#include <lvgl.h>

namespace {

struct Row {
    lv_obj_t *bar;
    lv_obj_t *val;
    lv_obj_t *name;
};

Row r_cpu, r_cpu_t, r_gpu, r_gpu_t, r_vram, r_ram, r_disk0, r_disk1;
lv_obj_t *lbl_net, *lbl_dsk, *lbl_up;
lv_obj_t *link_dot, *link_lbl;
lv_obj_t *m_player, *m_status, *m_title, *m_artist, *m_album, *m_bar, *m_time, *pp_lbl;

const lv_color_t C_BG = lv_color_hex(0x101418);
const lv_color_t C_PANEL = lv_color_hex(0x1b2128);
const lv_color_t C_TEXT = lv_color_hex(0xe8edf2);
const lv_color_t C_MUTED = lv_color_hex(0x8a96a3);
const lv_color_t C_OK = lv_color_hex(0x2ecc71);
const lv_color_t C_WARN = lv_color_hex(0xf1c40f);
const lv_color_t C_BAD = lv_color_hex(0xe74c3c);
const lv_color_t C_ACCENT = lv_color_hex(0x3aa0ff);

// UTF-8 Türkçe harfleri ASCII'ye çevirir; bilinmeyen çok baytlı karakterler '?' olur.
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
        if (c == 0xC3 && s[1]) {
            switch (s[1]) {
                case 0xA7: r = 'c'; break; case 0x87: r = 'C'; break;   // ç Ç
                case 0xB6: r = 'o'; break; case 0x96: r = 'O'; break;   // ö Ö
                case 0xBC: r = 'u'; break; case 0x9C: r = 'U'; break;   // ü Ü
                case 0xA2: r = 'a'; break; case 0xAE: r = 'i'; break;   // â î
                case 0xA9: case 0xA8: r = 'e'; break;                   // é è
            }
        } else if (c == 0xC4 && s[1]) {
            switch (s[1]) {
                case 0x9F: r = 'g'; break; case 0x9E: r = 'G'; break;   // ğ Ğ
                case 0xB1: r = 'i'; break; case 0xB0: r = 'I'; break;   // ı İ
            }
        } else if (c == 0xC5 && s[1]) {
            switch (s[1]) {
                case 0x9F: r = 's'; break; case 0x9E: r = 'S'; break;   // ş Ş
            }
        }
        out[o++] = r;
        // Karakterin geri kalan baytlarını atla
        int len = (c >= 0xF0) ? 4 : (c >= 0xE0) ? 3 : (c >= 0xC0) ? 2 : 1;
        for (int i = 0; i < len && *s; i++) {
            s++;
        }
    }
    out[o] = 0;
}

void set_text_tr(lv_obj_t *lbl, const char *utf8)
{
    char buf[256];
    translit(utf8, buf, sizeof(buf));
    lv_label_set_text(lbl, buf);
}

void fmt_rate(float bps, char *out, size_t n)
{
    if (bps < 1024) {
        snprintf(out, n, "%.0f B/s", bps);
    } else if (bps < 1024 * 1024) {
        snprintf(out, n, "%.1f KB/s", bps / 1024);
    } else {
        snprintf(out, n, "%.1f MB/s", bps / (1024 * 1024));
    }
}

void fmt_time(int sec, char *out, size_t n)
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
    return pct < 60 ? C_OK : pct < 85 ? C_WARN : C_BAD;
}

lv_color_t temp_color(float t)
{
    return t < 65 ? C_OK : t < 80 ? C_WARN : C_BAD;
}

lv_obj_t *make_panel(lv_obj_t *parent, int x, int y, int w, int h)
{
    lv_obj_t *p = lv_obj_create(parent);
    lv_obj_set_pos(p, x, y);
    lv_obj_set_size(p, w, h);
    lv_obj_set_style_bg_color(p, C_PANEL, 0);
    lv_obj_set_style_border_width(p, 0, 0);
    lv_obj_set_style_radius(p, 12, 0);
    lv_obj_set_style_pad_all(p, 0, 0);
    lv_obj_clear_flag(p, LV_OBJ_FLAG_SCROLLABLE);
    return p;
}

lv_obj_t *make_label(lv_obj_t *parent, int x, int y, const char *text, const lv_font_t *font, lv_color_t color)
{
    lv_obj_t *l = lv_label_create(parent);
    lv_label_set_text(l, text);
    lv_obj_set_style_text_font(l, font, 0);
    lv_obj_set_style_text_color(l, color, 0);
    lv_obj_set_pos(l, x, y);
    return l;
}

Row make_row(lv_obj_t *parent, int y, const char *name)
{
    Row r;
    r.name = make_label(parent, 14, y, name, &lv_font_montserrat_16, C_MUTED);
    r.bar = lv_bar_create(parent);
    lv_obj_set_pos(r.bar, 108, y + 3);
    lv_obj_set_size(r.bar, 150, 14);
    lv_bar_set_range(r.bar, 0, 100);
    lv_obj_set_style_bg_color(r.bar, lv_color_hex(0x2a323b), LV_PART_MAIN);
    lv_obj_set_style_bg_color(r.bar, C_OK, LV_PART_INDICATOR);
    r.val = make_label(parent, 268, y, "-", &lv_font_montserrat_16, C_TEXT);
    return r;
}

void set_row(Row &r, float pct, lv_color_t color, const char *text)
{
    lv_bar_set_value(r.bar, static_cast<int>(pct + 0.5f), LV_ANIM_OFF);
    lv_obj_set_style_bg_color(r.bar, color, LV_PART_INDICATOR);
    lv_label_set_text(r.val, text);
}

void media_btn_cb(lv_event_t *e)
{
    const char *cmd = static_cast<const char *>(lv_event_get_user_data(e));
    if (strcmp(cmd, "seek_back") == 0) {
        link_send_cmd("seek_rel", -10, true);
    } else if (strcmp(cmd, "seek_fwd") == 0) {
        link_send_cmd("seek_rel", 10, true);
    } else {
        link_send_cmd(cmd, 0, false);
    }
}

lv_obj_t *make_btn(lv_obj_t *parent, int x, int y, int w, int h, const char *text, const char *cmd,
                   lv_obj_t **label_out = nullptr)
{
    lv_obj_t *b = lv_btn_create(parent);
    lv_obj_set_pos(b, x, y);
    lv_obj_set_size(b, w, h);
    lv_obj_set_style_radius(b, 12, 0);
    lv_obj_set_style_bg_color(b, lv_color_hex(0x2a323b), 0);
    lv_obj_set_style_bg_color(b, C_ACCENT, LV_STATE_PRESSED);
    lv_obj_add_event_cb(b, media_btn_cb, LV_EVENT_CLICKED, const_cast<char *>(cmd));
    lv_obj_t *l = lv_label_create(b);
    lv_label_set_text(l, text);
    lv_obj_set_style_text_font(l, &lv_font_montserrat_28, 0);
    lv_obj_center(l);
    if (label_out) {
        *label_out = l;
    }
    return b;
}

}  // namespace

void ui_create()
{
    lv_obj_t *scr = lv_scr_act();
    lv_obj_set_style_bg_color(scr, C_BG, 0);
    lv_obj_clear_flag(scr, LV_OBJ_FLAG_SCROLLABLE);

    // Üst şerit
    make_label(scr, 16, 10, "PC Panel", &lv_font_montserrat_24, C_TEXT);
    make_label(scr, 140, 16, "Faz 3 - baglanti testi", &lv_font_montserrat_14, C_MUTED);
    link_dot = lv_obj_create(scr);
    lv_obj_remove_style_all(link_dot);
    lv_obj_set_size(link_dot, 14, 14);
    lv_obj_set_style_radius(link_dot, LV_RADIUS_CIRCLE, 0);
    lv_obj_set_style_bg_opa(link_dot, LV_OPA_COVER, 0);
    lv_obj_set_style_bg_color(link_dot, C_BAD, 0);
    lv_obj_set_pos(link_dot, 560, 17);
    link_lbl = make_label(scr, 582, 13, "NO LINK", &lv_font_montserrat_16, C_BAD);

    // Sol panel: sistem
    lv_obj_t *sp = make_panel(scr, 10, 48, 380, 422);
    r_cpu = make_row(sp, 12, "CPU");
    r_cpu_t = make_row(sp, 44, "CPU temp");
    r_gpu = make_row(sp, 84, "GPU");
    r_gpu_t = make_row(sp, 116, "GPU temp");
    r_vram = make_row(sp, 148, "VRAM");
    r_ram = make_row(sp, 188, "RAM");
    r_disk0 = make_row(sp, 228, "Disk /");
    r_disk1 = make_row(sp, 260, "Disk 2");
    lbl_net = make_label(sp, 14, 304, "Net: -", &lv_font_montserrat_16, C_TEXT);
    lbl_dsk = make_label(sp, 14, 334, "Disk IO: -", &lv_font_montserrat_16, C_TEXT);
    lbl_up = make_label(sp, 14, 364, "PC uptime: -", &lv_font_montserrat_16, C_MUTED);

    // Sağ panel: medya
    lv_obj_t *mp = make_panel(scr, 400, 48, 390, 422);
    m_player = make_label(mp, 16, 12, "No player", &lv_font_montserrat_14, C_MUTED);
    m_status = make_label(mp, 300, 12, "", &lv_font_montserrat_14, C_MUTED);

    m_title = make_label(mp, 16, 44, "-", &lv_font_montserrat_28, C_TEXT);
    lv_label_set_long_mode(m_title, LV_LABEL_LONG_SCROLL_CIRCULAR);
    lv_obj_set_width(m_title, 358);
    m_artist = make_label(mp, 16, 84, "", &lv_font_montserrat_20, C_TEXT);
    lv_label_set_long_mode(m_artist, LV_LABEL_LONG_DOT);
    lv_obj_set_width(m_artist, 358);
    m_album = make_label(mp, 16, 112, "", &lv_font_montserrat_16, C_MUTED);
    lv_label_set_long_mode(m_album, LV_LABEL_LONG_DOT);
    lv_obj_set_width(m_album, 358);

    m_bar = lv_bar_create(mp);
    lv_obj_set_pos(m_bar, 16, 160);
    lv_obj_set_size(m_bar, 358, 10);
    lv_bar_set_range(m_bar, 0, 1000);
    lv_obj_set_style_bg_color(m_bar, lv_color_hex(0x2a323b), LV_PART_MAIN);
    lv_obj_set_style_bg_color(m_bar, C_ACCENT, LV_PART_INDICATOR);
    m_time = make_label(mp, 16, 178, "0:00 / 0:00", &lv_font_montserrat_16, C_MUTED);

    make_btn(mp, 16, 230, 110, 80, LV_SYMBOL_PREV, "prev");
    make_btn(mp, 140, 230, 110, 80, LV_SYMBOL_PLAY, "play_pause", &pp_lbl);
    make_btn(mp, 264, 230, 110, 80, LV_SYMBOL_NEXT, "next");
    make_btn(mp, 16, 324, 172, 64, "-10 s", "seek_back");
    make_btn(mp, 202, 324, 172, 64, "+10 s", "seek_fwd");
}

void ui_set_link(bool ok, uint32_t rx_count)
{
    lv_obj_set_style_bg_color(link_dot, ok ? C_OK : C_BAD, 0);
    lv_obj_set_style_text_color(link_lbl, ok ? C_OK : C_BAD, 0);
    if (ok) {
        lv_label_set_text_fmt(link_lbl, "LINK OK  (%lu msg)", static_cast<unsigned long>(rx_count));
    } else {
        lv_label_set_text(link_lbl, "NO LINK - waiting for PC");
    }
}

void ui_update_stat(JsonObjectConst o)
{
    char buf[64], a[24], b[24];

    float cpu = o["cpu"] | 0.0f;
    snprintf(buf, sizeof(buf), "%.0f %%  %d MHz", cpu, o["cpu_mhz"] | 0);
    set_row(r_cpu, cpu, level_color(cpu), buf);

    if (!o["cpu_t"].isNull()) {
        float t = o["cpu_t"];
        snprintf(buf, sizeof(buf), "%.0f C", t);
        set_row(r_cpu_t, t, temp_color(t), buf);
    }

    if (!o["gpu"].isNull()) {
        float g = o["gpu"];
        snprintf(buf, sizeof(buf), "%.0f %%  %d W", g, o["gpu_w"] | 0);
        set_row(r_gpu, g, level_color(g), buf);
        float gt = o["gpu_t"] | 0.0f;
        snprintf(buf, sizeof(buf), "%.0f C", gt);
        set_row(r_gpu_t, gt, temp_color(gt), buf);
        float vu = o["vram"] | 0.0f, vt = o["vram_tot"] | 1.0f;
        snprintf(buf, sizeof(buf), "%.1f / %.0f GB", vu / 1024, vt / 1024);
        set_row(r_vram, vu / vt * 100, level_color(vu / vt * 100), buf);
    }

    float ru = o["ram"] | 0.0f, rt = o["ram_tot"] | 1.0f;
    snprintf(buf, sizeof(buf), "%.1f / %.0f GB", ru / 1024, rt / 1024);
    set_row(r_ram, ru / rt * 100, level_color(ru / rt * 100), buf);

    JsonArrayConst disks = o["disks"];
    Row *drows[2] = {&r_disk0, &r_disk1};
    for (int i = 0; i < 2; i++) {
        if (i < static_cast<int>(disks.size())) {
            float p = disks[i]["p"] | 0.0f;
            snprintf(buf, sizeof(buf), "Disk %s", static_cast<const char *>(disks[i]["m"] | "?"));
            lv_label_set_text(drows[i]->name, buf);
            snprintf(buf, sizeof(buf), "%.0f %%", p);
            set_row(*drows[i], p, level_color(p), buf);
        }
    }

    fmt_rate(o["net_dn"] | 0.0f, a, sizeof(a));
    fmt_rate(o["net_up"] | 0.0f, b, sizeof(b));
    lv_label_set_text_fmt(lbl_net, "Net:  " LV_SYMBOL_DOWN " %s   " LV_SYMBOL_UP " %s", a, b);
    fmt_rate(o["dsk_r"] | 0.0f, a, sizeof(a));
    fmt_rate(o["dsk_w"] | 0.0f, b, sizeof(b));
    lv_label_set_text_fmt(lbl_dsk, "Disk IO:  R %s   W %s", a, b);

    long up = o["up"] | 0L;
    lv_label_set_text_fmt(lbl_up, "PC uptime: %ldh %02ldm", up / 3600, up / 60 % 60);
}

void ui_update_media(JsonObjectConst o)
{
    const char *st = o["st"] | "none";
    if (strcmp(st, "none") == 0) {
        lv_label_set_text(m_player, "No player");
        lv_label_set_text(m_status, "");
        lv_label_set_text(m_title, "-");
        lv_label_set_text(m_artist, "");
        lv_label_set_text(m_album, "");
        lv_bar_set_value(m_bar, 0, LV_ANIM_OFF);
        lv_label_set_text(m_time, "0:00 / 0:00");
        lv_label_set_text(pp_lbl, LV_SYMBOL_PLAY);
        return;
    }

    set_text_tr(m_player, o["pl"] | "");
    bool playing = strcmp(st, "play") == 0;
    lv_label_set_text(m_status, playing ? "playing" : strcmp(st, "pause") == 0 ? "paused" : "stopped");
    lv_label_set_text(pp_lbl, playing ? LV_SYMBOL_PAUSE : LV_SYMBOL_PLAY);

    // Başlık değişmediyse yeniden yazma (kayan yazı baştan başlamasın)
    char title[256];
    translit(o["ti"] | "", title, sizeof(title));
    if (strcmp(lv_label_get_text(m_title), title) != 0) {
        lv_label_set_text(m_title, title[0] ? title : "(no title)");
    }
    set_text_tr(m_artist, o["ar"] | "");
    set_text_tr(m_album, o["al"] | "");

    int len = o["len"] | 0, pos = o["pos"] | 0;
    lv_bar_set_value(m_bar, len > 0 ? pos * 1000 / len : 0, LV_ANIM_OFF);
    char a[16], b[16];
    fmt_time(pos, a, sizeof(a));
    fmt_time(len, b, sizeof(b));
    lv_label_set_text_fmt(m_time, "%s / %s", a, b);
}
