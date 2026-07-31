"""Проверки напоминаний."""

import sys
from datetime import date, datetime, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from mathmark import reminders as rm   # noqa: E402


def test_ежедневное_записывается_и_читается():
    r = rm.Reminder("Линал.md", rm.DAILY, time(19, 0), "повторить линал")
    assert r.line() == "Линал.md|daily|19:00|повторить линал"
    assert rm.parse(r.line()) == [r]


def test_еженедельное_записывается_и_читается():
    r = rm.Reminder("Матан.md", rm.WEEKLY, time(9, 30), "Тейлор", weekday=1)
    assert r.line() == "Матан.md|weekly|1|09:30|Тейлор"
    assert rm.parse(r.line()) == [r]


def test_однократное_записывается_и_читается():
    r = rm.Reminder("Шпора.md", rm.ONCE, time(19, 0), "перед экзаменом", on=date(2026, 8, 5))
    assert r.line() == "Шпора.md|once|2026-08-05T19:00|перед экзаменом"
    assert rm.parse(r.line()) == [r]


def test_кривые_строки_пропускаются():
    text = "мусор\nЛинал.md|daily|19:00|ок\nМатан.md|weekly|9|10:00|плохой день\n"
    got = rm.parse(text)
    assert len(got) == 1
    assert got[0].text == "ок"


def test_текст_с_пробелами_и_запятыми_переживает_круг():
    r = rm.Reminder("ф.md", rm.DAILY, time(8, 5), "повторить: ряды, пределы")
    assert rm.parse(rm.dump([r])) == [r]


def test_в_какой_день_сработает():
    daily = rm.Reminder("ф.md", rm.DAILY, time(19, 0), "т")
    weekly = rm.Reminder("ф.md", rm.WEEKLY, time(19, 0), "т", weekday=1)   # понедельник
    once = rm.Reminder("ф.md", rm.ONCE, time(19, 0), "т", on=date(2026, 8, 5))

    monday = date(2026, 8, 3)
    tuesday = date(2026, 8, 4)
    assert daily.due_on(monday) and daily.due_on(tuesday)
    assert weekly.due_on(monday) and not weekly.due_on(tuesday)
    assert once.due_on(date(2026, 8, 5)) and not once.due_on(monday)


def test_ближайшее_срабатывание_ежедневного():
    r = rm.Reminder("ф.md", rm.DAILY, time(19, 0), "т")
    assert r.next_after(datetime(2026, 8, 3, 10, 0)) == datetime(2026, 8, 3, 19, 0)
    assert r.next_after(datetime(2026, 8, 3, 20, 0)) == datetime(2026, 8, 4, 19, 0)


def test_ближайшее_срабатывание_еженедельного():
    r = rm.Reminder("ф.md", rm.WEEKLY, time(19, 0), "т", weekday=1)
    assert r.next_after(datetime(2026, 8, 4, 10, 0)) == datetime(2026, 8, 10, 19, 0)


def test_однократное_в_прошлом_больше_не_сработает():
    r = rm.Reminder("ф.md", rm.ONCE, time(19, 0), "т", on=date(2026, 8, 1))
    assert r.next_after(datetime(2026, 8, 2, 0, 0)) is None


def test_список_на_день_по_времени():
    items = [
        rm.Reminder("а.md", rm.DAILY, time(21, 0), "вечер"),
        rm.Reminder("б.md", rm.DAILY, time(8, 0), "утро"),
        rm.Reminder("в.md", rm.WEEKLY, time(12, 0), "среда", weekday=3),
    ]
    day = date(2026, 8, 3)      # понедельник
    got = rm.for_day(items, day)
    assert [r.text for r in got] == ["утро", "вечер"]


def test_запись_в_файл_и_чтение(tmp_path):
    f = tmp_path / "reminders.conf"
    items = [rm.Reminder("ф.md", rm.DAILY, time(7, 45), "зарядка мозгу")]
    rm.save(f, items)
    assert rm.load(f) == items
