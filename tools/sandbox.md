# Проверять на отдельной папке, не на своей

Приложение при проверке водят подставными нажатиями, и они попадают куда
угодно: буквы переключают инструмент, Backspace удаляет выделенное. Один раз
так уже была потеряна доска в рабочей папке.

Поэтому перед проверкой окна папка подменяется:

```bash
cp ~/.config/mathmark/mathmark.conf ~/.config/mathmark/mathmark.conf.свой
sed -i 's|^folder=.*|folder=/home/volkinstridoff/.cache/mathmark-проверка|' \
    ~/.config/mathmark/mathmark.conf
# …проверка…
mv ~/.config/mathmark/mathmark.conf.свой ~/.config/mathmark/mathmark.conf
```

Проверки, которым окно не нужно, папку не трогают вовсе:
`check_board.py`, `check_cards.py`, `check_cut.py`, `check_catalog.js`,
`check_packaging.py`.
