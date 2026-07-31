"""
Те же проверки, что и у телефонной версии, слово в слово по смыслу.
Если правило разъедется между Kotlin и Python, упадёт здесь.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from mathmark import md_items as md   # noqa: E402

SAMPLE = """# Шпора

## Пределы

- [ ] Вывести производную $f(x)=\\sqrt{x^3}$
- [x] Разобрать эпсилон-дельта
- [~] Предел по двум переменным

## Темы

- ( ) Ряды Фурье
- (x) Кратные интегралы

Просто строка, не задача.
- обычный пункт списка"""


def test_находит_задачи_и_темы_различая_скобки():
    found = md.items(SAMPLE)
    assert len(found) == 5
    assert sum(1 for i in found if i.kind is md.Kind.TASK) == 3
    assert sum(1 for i in found if i.kind is md.Kind.TOPIC) == 2


def test_читает_три_состояния():
    found = md.items(SAMPLE)
    assert found[0].mark is md.Mark.NONE
    assert found[1].mark is md.Mark.DONE
    assert found[2].mark is md.Mark.HALF


def test_обычный_список_и_текст_задачами_не_считаются():
    assert not md.is_item("- обычный пункт списка")
    assert not md.is_item("Просто строка, не задача.")
    assert not md.is_item("## Заголовок")


def test_несовпадающие_скобки_не_считаются_отметкой():
    assert not md.is_item("- [ ) кривая строка")
    assert not md.is_item("- ( ] кривая строка")


def test_отметка_меняет_ровно_один_байт_в_utf8():
    before = SAMPLE
    after = md.cycle(before, md.items(before)[0].box_offset)
    a = before.encode("utf-8")
    b = after.encode("utf-8")
    assert len(a) == len(b), "длина файла обязана сохраниться"
    assert sum(1 for x, y in zip(a, b) if x != y) == 1


def test_состояния_идут_по_кругу():
    text = "- [ ] дело"
    off = md.items(text)[0].box_offset
    text = md.cycle(text, off)
    assert text == "- [~] дело"
    text = md.cycle(text, off)
    assert text == "- [x] дело"
    text = md.cycle(text, off)
    assert text == "- [ ] дело"


def test_у_тем_состояния_переключаются_так_же():
    text = "- ( ) Ряды Фурье"
    off = md.items(text)[0].box_offset
    assert md.cycle(text, off) == "- (~) Ряды Фурье"
    assert md.cycle(md.cycle(text, off), off) == "- (x) Ряды Фурье"


def test_порядок_строк_и_отступы_не_меняются():
    before = "  - [ ] с отступом\n\n\n- [x] после пустых строк\n"
    after = md.cycle(before, md.items(before)[1].box_offset)
    assert len(before.split("\n")) == len(after.split("\n"))
    assert after.split("\n")[0] == "  - [ ] с отступом"
    assert after.endswith("\n")


def test_одинаковые_строки_не_путаются_между_собой():
    text = "- [ ] одно и то же\n- [ ] одно и то же\n"
    after = md.cycle(text, md.items(text)[1].box_offset)
    assert after.split("\n")[0] == "- [ ] одно и то же"
    assert after.split("\n")[1] == "- [~] одно и то же"


def test_вид_файла_определяется_содержимым():
    assert md.counts(SAMPLE).kind is md.FileKind.BOTH
    assert md.counts("- [ ] раз\n- [x] два").kind is md.FileKind.TASKS
    assert md.counts("- ( ) раз").kind is md.FileKind.TOPICS
    assert md.counts("# Шпора\n\n## Ряды\n\nтекст").kind is md.FileKind.PLAIN


def test_половинка_считается_за_половину():
    c = md.counts("- [x] раз\n- [~] два\n- [ ] три\n- [ ] четыре")
    assert abs(c.progress - 1.5 / 4) < 1e-6


def test_формы_слова_считаются_по_правилам_языка():
    assert md.plural_form(1, "ru") == "one"
    assert md.plural_form(2, "ru") == "few"
    assert md.plural_form(4, "ru") == "few"
    assert md.plural_form(5, "ru") == "many"
    assert md.plural_form(11, "ru") == "many"
    assert md.plural_form(14, "ru") == "many"
    assert md.plural_form(21, "ru") == "one"

    assert md.plural_form(1, "en") == "one"
    assert md.plural_form(2, "en") == "few"
    assert md.plural_form(21, "es") == "few"


def test_формулы_с_долларами_и_скобками_не_ломают_разбор():
    text = "- [ ] Посчитать $\\int_0^1 (x+1)\\,dx$ и $[a,b]$"
    found = md.items(text)
    assert len(found) == 1
    assert found[0].kind is md.Kind.TASK
    assert "\\int" in found[0].label
