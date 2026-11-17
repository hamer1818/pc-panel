#pragma once
/*
 * Yazı tipleri. `tools/fontlari_uret.sh` ile Türkçe karakterli yazı tipleri üretildiyse platformio.ini'de
 * -DPC_PANEL_TR_FONTS=1 tanımlanır; yoksa LVGL'nin hazır (Türkçe harfsiz) Montserrat'ına düşülür.
 */
#include <lvgl.h>

#ifndef PC_PANEL_TR_FONTS
#define PC_PANEL_TR_FONTS 0
#endif

#if PC_PANEL_TR_FONTS
LV_FONT_DECLARE(tr_font_12);
LV_FONT_DECLARE(tr_font_14);
LV_FONT_DECLARE(tr_font_16);
LV_FONT_DECLARE(tr_font_18);
LV_FONT_DECLARE(tr_font_22);
LV_FONT_DECLARE(tr_font_30);
LV_FONT_DECLARE(icon_font_40);
#define F12 (&tr_font_12)
#define F14 (&tr_font_14)
#define F16 (&tr_font_16)
#define F18 (&tr_font_18)
#define F22 (&tr_font_22)
#define F30 (&tr_font_30)
#define FICON (&icon_font_40)
// Font Awesome 5 kod noktaları (UTF-8)
#define ICON_LOCK "\xEF\x80\xA3"        // U+F023
#define ICON_MIC "\xEF\x84\xB0"         // U+F130
#define ICON_MIC_OFF "\xEF\x84\xB1"     // U+F131
#define ICON_CAMERA "\xEF\x80\xB0"      // U+F030
#define ICON_VOLUME "\xEF\x80\xA8"      // U+F028
#define ICON_VOLUME_OFF "\xEF\x9A\xA9"  // U+F6A9
#define ICON_TERMINAL "\xEF\x84\xA0"    // U+F120
#define ICON_GLOBE "\xEF\x82\xAC"       // U+F0AC
#define ICON_FOLDER "\xEF\x81\xBB"      // U+F07B
#define ICON_SPOTIFY "\xEF\x86\xBC"     // U+F1BC
#define ICON_MUSIC "\xEF\x80\x81"       // U+F001
#else
#define F12 (&lv_font_montserrat_12)
#define F14 (&lv_font_montserrat_14)
#define F16 (&lv_font_montserrat_16)
#define F18 (&lv_font_montserrat_18)
#define F22 (&lv_font_montserrat_22)
#define F30 (&lv_font_montserrat_30)
#define FICON (&lv_font_montserrat_40)
// Yedek: hazır yazı tipinde yalnızca LV_SYMBOL_* var
#define ICON_LOCK LV_SYMBOL_EYE_CLOSE
#define ICON_MIC LV_SYMBOL_AUDIO
#define ICON_MIC_OFF LV_SYMBOL_CLOSE
#define ICON_CAMERA LV_SYMBOL_IMAGE
#define ICON_VOLUME LV_SYMBOL_VOLUME_MAX
#define ICON_VOLUME_OFF LV_SYMBOL_MUTE
#define ICON_TERMINAL LV_SYMBOL_KEYBOARD
#define ICON_GLOBE LV_SYMBOL_WIFI
#define ICON_FOLDER LV_SYMBOL_DIRECTORY
#define ICON_SPOTIFY LV_SYMBOL_AUDIO
#define ICON_MUSIC LV_SYMBOL_AUDIO
#endif
