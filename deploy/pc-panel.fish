# PC Panel: uzun süren komut bitince karta bildirim (✓ / ✗, süre).
# Kurulum: deploy/kur.sh bu dosyayı ~/.config/fish/conf.d/pc-panel.fish olarak kopyalar.
# Süre eşiği ve hariç tutulan programlar ~/.config/pc-panel/ayarlar.toml [komut] bölümünde (servis karar verir).
status is-interactive; or exit

function __pc_panel_postexec --on-event fish_postexec
    set -l code $status  # ilk satırda olmalı: komutun çıkış kodu
    test -n "$CMD_DURATION"; and test "$CMD_DURATION" -ge 5000; or return
    set -l olay /mnt/veri/yazilim/esp32-lcd-controller-card/host/.venv/bin/pc-panel-olay
    test -x $olay; or return
    $olay komut --sure $CMD_DURATION --kod $code -- $argv[1] >/dev/null 2>&1 &
    disown 2>/dev/null
end
