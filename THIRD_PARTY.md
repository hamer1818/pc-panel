# Third-party components / Üçüncü taraf bileşenler

The project's own code is MIT licensed (see `LICENSE`). The following files come from, or are derived from,
third-party works and keep their original licenses.

Projenin kendi kodu MIT lisanslıdır. Aşağıdaki dosyalar başka projelerden alınmış ya da onlardan üretilmiştir ve
kendi lisanslarını korur.

| Files / Dosyalar | Source / Kaynak | License / Lisans |
|---|---|---|
| `firmware/fonts/kaynak/Montserrat-Medium.ttf`, generated `firmware/src/fonts/tr_font_*.c`, `clock_font_120.c` (text glyphs) | [Montserrat](https://github.com/JulietaUla/Montserrat), copied from the LVGL repository | SIL Open Font License 1.1 — `firmware/fonts/kaynak/OFL-Montserrat.txt` |
| `firmware/fonts/kaynak/FontAwesome5-Solid+Brands+Regular.woff`, icon glyphs in generated `firmware/src/fonts/*.c` | [Font Awesome Free 5](https://fontawesome.com) by Fonticons, Inc., copied from the LVGL repository | Icons: CC BY 4.0 · Fonts: SIL OFL 1.1 — <https://fontawesome.com/license/free>. Brand icons are trademarks of their respective owners. |
| `firmware/src/lvgl_v8_port.cpp`, `firmware/src/lvgl_v8_port.h` | [ESP32_Display_Panel](https://github.com/esp-arduino-libs/ESP32_Display_Panel) v1.0.4 example (Espressif Systems) | CC0-1.0 |
| `firmware/src/esp_panel_board_custom_conf.h`, `firmware/src/esp_panel_drivers_conf.h`, `firmware/src/esp_utils_conf.h` | ESP32_Display_Panel / esp-lib-utils (Espressif Systems) | Apache-2.0 (SPDX headers kept in the files) |
| `firmware/src/lv_conf.h` | [LVGL](https://github.com/lvgl/lvgl) v8.4 configuration template | MIT |

Libraries downloaded at build time (not in this repository) — derleme sırasında indirilen kütüphaneler:
LVGL (MIT), ESP32_Display_Panel / ESP32_IO_Expander / esp-lib-utils (Apache-2.0), ArduinoJson (MIT),
arduino-esp32 (LGPL-2.1); Python: psutil (BSD-3-Clause), nvidia-ml-py (BSD-3-Clause), dbus-fast (MIT),
pyserial (BSD-3-Clause), Pillow (MIT-CMU).

Application icons shown on the Apps page are read at runtime from the user's own system and are not part of this
repository. Uygulamalar sayfasındaki ikonlar çalışırken kullanıcının kendi sisteminden okunur, depoda yoktur.
