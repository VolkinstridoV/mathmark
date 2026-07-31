#!/bin/sh
# Установка себе, в домашнюю папку. Пакеты для этого не нужны.
#
#   ./desktop/install.sh
#
# Кладёт запускалку в ~/.local/bin/koren, ярлык и значок — в ~/.local/share.
# Сам код остаётся в репозитории: правишь файл — изменения сразу в деле.

set -e
REPO=$(cd "$(dirname "$0")/.." && pwd)
BIN="$HOME/.local/bin"
SHARE="$HOME/.local/share"

mkdir -p "$BIN" "$SHARE/applications" "$SHARE/icons/hicolor/scalable/apps"

cat > "$BIN/koren" <<EOF
#!/bin/sh
exec python3 "$REPO/desktop/run.py" "\$@"
EOF
chmod +x "$BIN/koren"

sed "s|^Exec=koren|Exec=$BIN/koren|" "$REPO/desktop/dev.yury.koren.desktop" \
    > "$SHARE/applications/dev.yury.koren.desktop"
cp "$REPO/desktop/data/dev.yury.koren.svg" "$SHARE/icons/hicolor/scalable/apps/"

update-desktop-database "$SHARE/applications" 2>/dev/null || true
gtk4-update-icon-cache -q -t "$SHARE/icons/hicolor" 2>/dev/null || true

echo "Готово. Запуск: koren"
echo "Если команда не нашлась — добавь $BIN в PATH."
