#!/usr/bin/env bash
# PC Panel servisini kurar / kaldırır (sudo GEREKMEZ — systemd kullanıcı servisi).
#   deploy/kur.sh          → kur ve başlat
#   deploy/kur.sh kaldir   → durdur ve kaldır
set -euo pipefail
cd "$(dirname "$0")/.."
UNIT_DIR="$HOME/.config/systemd/user"
UNIT=pc-panel.service

if [ "${1:-}" = "kaldir" ]; then
    systemctl --user disable --now "$UNIT" 2>/dev/null || true
    rm -f "$UNIT_DIR/$UNIT"
    systemctl --user daemon-reload
    echo "pc-panel servisi kaldırıldı."
    exit 0
fi

# Python ortamı hazır mı?
if [ ! -x host/.venv/bin/pc-panel ]; then
    echo "host/.venv yok, kuruluyor (uv sync)…"
    (cd host && uv sync)
fi

# Elle çalışan bir kopya varsa portu tutar; uyar
if pgrep -f "host/.venv/bin/pc-panel" >/dev/null || pgrep -f "uv run pc-panel" >/dev/null; then
    echo "UYARI: elle başlatılmış bir pc-panel çalışıyor; servis portu alamaz. Önce onu Ctrl+C ile kapatın." >&2
fi

mkdir -p "$UNIT_DIR"
install -m 644 deploy/$UNIT "$UNIT_DIR/$UNIT"
systemctl --user daemon-reload
systemctl --user enable --now "$UNIT"
sleep 2
systemctl --user --no-pager --lines=5 status "$UNIT" || true
echo
echo "Kuruldu. Günlüğü izlemek için:  journalctl --user -u pc-panel -f"
