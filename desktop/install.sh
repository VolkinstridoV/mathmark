#!/bin/sh
# Установка себе, в домашнюю папку. Пакеты для этого не нужны.
#
#   ./desktop/install.sh
#
# Кладёт запускалку в ~/.local/bin/mathmark, ярлык и значок — в ~/.local/share.
# Сам код остаётся в репозитории: правишь файл — изменения сразу в деле.

set -e
REPO=$(cd "$(dirname "$0")/.." && pwd)
BIN="$HOME/.local/bin"
SHARE="$HOME/.local/share"

mkdir -p "$BIN" "$SHARE/applications" "$SHARE/icons/hicolor/scalable/apps"

cat > "$BIN/mathmark" <<EOF
#!/bin/sh
exec python3 "$REPO/desktop/run.py" "\$@"
EOF
chmod +x "$BIN/mathmark"

sed "s|^Exec=mathmark|Exec=$BIN/koren|" "$REPO/desktop/dev.yury.mathmark.desktop" \
    > "$SHARE/applications/dev.yury.mathmark.desktop"
cp "$REPO/desktop/data/dev.yury.mathmark.svg" "$SHARE/icons/hicolor/scalable/apps/"

update-desktop-database "$SHARE/applications" 2>/dev/null || true
gtk4-update-icon-cache -q -t "$SHARE/icons/hicolor" 2>/dev/null || true

echo "Готово. Запуск: mathmark"
echo "Если команда не нашлась — добавь $BIN в PATH."
