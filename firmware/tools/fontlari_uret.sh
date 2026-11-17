#!/usr/bin/env bash
# PC Panel — Türkçe karakterli LVGL yazı tiplerini üretir (src/fonts/*.c).
#
# Gerekli: lv_font_conv 1.5.2. Projeye yerel kurulum (bir kez):
#   npm install --prefix tools/node lv_font_conv@1.5.2
#
# Kaynaklar (fonts/kaynak/, LVGL deposundan kopyalandı):
#   Montserrat-Medium.ttf               — SIL Open Font License 1.1
#   FontAwesome5-Solid+Brands+Regular.woff — Font Awesome Free (ikonlar CC BY 4.0, font SIL OFL 1.1)
#
# Çalıştırma (firmware/ klasöründe):  tools/fontlari_uret.sh
set -euo pipefail
cd "$(dirname "$0")/.."

CONV="tools/node/node_modules/.bin/lv_font_conv"
[ -x "$CONV" ] || CONV="$(command -v lv_font_conv || true)"
if [ -z "$CONV" ]; then
    echo "lv_font_conv bulunamadı. Kurulum: npm install --prefix tools/node lv_font_conv@1.5.2" >&2
    exit 1
fi

SRC=fonts/kaynak
OUT=src/fonts
mkdir -p "$OUT"
TEXT="$SRC/Montserrat-Medium.ttf"
FA="$SRC/FontAwesome5-Solid+Brands+Regular.woff"

# Metin: ASCII + Latin-1 + Latin Genişletilmiş-A (Türkçe ç ğ ı İ ö ş ü dahil, çoğu Avrupa dili de)
# + tire, tırnak, madde imi, üç nokta, eksi işareti, ₺
TEXT_RANGE="0x20-0x7E,0xA0-0x17F,0x2013-0x2014,0x2018-0x201E,0x2022,0x2026,0x2212,0x20BA"

# LVGL'nin LV_SYMBOL_* ikonları (lvgl/scripts/built_in_font/built_in_font_gen.py ile aynı liste)
SYMS="61441,61448,61451,61452,61453,61457,61459,61461,61465,61468,61473,61478,61479,61480,61502,61507,61512,61515,61516,61517,61521,61522,61523,61524,61543,61544,61550,61552,61553,61556,61559,61560,61561,61563,61587,61589,61636,61637,61639,61641,61664,61671,61674,61683,61724,61732,61787,61931,62016,62017,62018,62019,62020,62087,62099,62212,62189,62810,63426,63650"

for size in 12 14 16 18 22 30; do
    echo "tr_font_${size}"
    "$CONV" --bpp 4 --size "$size" --no-compress \
        --font "$TEXT" -r "$TEXT_RANGE" \
        --font "$FA" -r "$SYMS" \
        --format lvgl --force-fast-kern-format \
        --lv-font-name "tr_font_${size}" -o "$OUT/tr_font_${size}.c"
done

# Büyük ikonlar (kısayol kutuları ve medya düğmeleri), 40 px:
# kilit, mikrofon, mikrofon kapalı, kamera, ses açık, ses kapalı, terminal, küre, klasör, Spotify,
# önceki, oynat, duraklat, sonraki, müzik notası
ICONS="0xF023,0xF130,0xF131,0xF030,0xF028,0xF6A9,0xF120,0xF0AC,0xF07B,0xF1BC,0xF048,0xF04B,0xF04C,0xF051,0xF001"
echo "icon_font_40"
"$CONV" --bpp 4 --size 40 --no-compress \
    --font "$FA" -r "$ICONS" \
    --format lvgl --lv-font-name icon_font_40 -o "$OUT/icon_font_40.c"

echo "Tamam: $(ls "$OUT" | wc -l) dosya → $OUT"
