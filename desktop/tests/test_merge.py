"""Проверки сведения версий при синхронизации."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from mathmark.merge import merge   # noqa: E402


def test_одинаковые_версии_сводятся_молча():
    text = "- [ ] раз\n- ( ) два\n"
    assert merge(text, text, text) == (text, False)


def test_изменилась_только_одна_сторона():
    base = "- [ ] раз\n"
    assert merge(base, "- [x] раз\n", base) == ("- [x] раз\n", False)
    assert merge(base, base, "- [x] раз\n") == ("- [x] раз\n", False)


def test_спор_об_отметке_выигрывает_продвинутое():
    base = "- [ ] раз\n"
    text, conflict = merge(base, "- [~] раз\n", "- [x] раз\n")
    assert text == "- [x] раз\n"
    assert not conflict

    text, conflict = merge(base, "- [x] раз\n", "- [~] раз\n")
    assert text == "- [x] раз\n"
    assert not conflict


def test_у_тем_то_же_правило():
    base = "- ( ) Ряды Фурье\n"
    text, conflict = merge(base, "- (~) Ряды Фурье\n", "- (x) Ряды Фурье\n")
    assert text == "- (x) Ряды Фурье\n"
    assert not conflict


def test_разные_строки_сводятся_каждая_по_себе():
    base = "- [ ] раз\n- ( ) два\n"
    local = "- [x] раз\n- ( ) два\n"
    remote = "- [ ] раз\n- (x) два\n"
    text, conflict = merge(base, local, remote)
    assert text == "- [x] раз\n- (x) два\n"
    assert not conflict


def test_разошёлся_текст_а_не_отметка_это_спор():
    base = "- [ ] раз\n"
    text, conflict = merge(base, "- [ ] раз другой\n", "- [ ] раз третий\n")
    assert conflict
    assert text == "- [ ] раз другой\n"     # своё не теряем


def test_разное_число_строк_это_спор():
    base = "- [ ] раз\n"
    _, conflict = merge(base, "- [ ] раз\n- [ ] два\n", "- [ ] раз\n- [ ] три\n")
    assert conflict


def test_файл_появился_с_двух_сторон_с_одинаковым_текстом():
    text = "# Шпора\n"
    assert merge(None, text, text) == (text, False)


def test_обычный_текст_не_считается_отметкой():
    base = "просто строка\n"
    _, conflict = merge(base, "строка слева\n", "строка справа\n")
    assert conflict
