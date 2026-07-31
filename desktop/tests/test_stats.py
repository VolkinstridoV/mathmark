"""Проверки журнала и подсчёта движения."""

import sys
from datetime import date, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from mathmark.md_items import Kind, Mark   # noqa: E402
from mathmark.stats import parse, record, summarise   # noqa: E402

TODAY = date(2026, 7, 31)


def at(days_ago: int, hour: int = 12) -> datetime:
    d = TODAY - timedelta(days=days_ago)
    return datetime(d.year, d.month, d.day, hour)


def entry(days_ago: int, kind=Kind.TASK, mark=Mark.DONE):
    from mathmark.stats import Entry
    return Entry(at(days_ago), "ф.md", kind, mark)


def test_запись_и_чтение_журнала(tmp_path):
    j = tmp_path / "journal.log"
    record(j, "Матан.md", Kind.TASK, Mark.DONE, at(0))
    record(j, "Линал.md", Kind.TOPIC, Mark.HALF, at(0))

    got = parse(j.read_text(encoding="utf-8"))
    assert len(got) == 2
    assert got[0].path == "Матан.md"
    assert got[0].kind is Kind.TASK
    assert got[0].mark is Mark.DONE
    assert got[1].mark is Mark.HALF


def test_кривые_строки_пропускаются():
    text = "мусор\n2026-07-31T12:00:00|ф.md|task|x\nещё мусор|две|части\n"
    assert len(parse(text)) == 1


def test_считается_только_закрытие():
    got = summarise([entry(0), entry(0, mark=Mark.HALF), entry(0, mark=Mark.NONE)], TODAY)
    assert got.today_tasks == 1


def test_задачи_и_темы_считаются_отдельно():
    got = summarise([entry(0), entry(0, Kind.TOPIC), entry(0, Kind.TOPIC)], TODAY)
    assert got.today_tasks == 1
    assert got.today_topics == 2


def test_окна_недели_и_месяца():
    got = summarise([entry(0), entry(3), entry(10), entry(40)], TODAY)
    assert got.today_tasks == 1
    assert got.week_tasks == 2       # сегодня и три дня назад
    assert got.month_tasks == 3      # плюс десять дней назад
    

def test_серия_дней_подряд():
    got = summarise([entry(0), entry(1), entry(2), entry(4)], TODAY)
    assert got.streak == 3           # четвёртый день назад в серию не входит


def test_серия_обрывается_если_сегодня_пусто():
    got = summarise([entry(1), entry(2)], TODAY)
    assert got.streak == 0


def test_разбивка_по_дням_ровно_тридцать():
    got = summarise([entry(0), entry(0), entry(5)], TODAY)
    assert len(got.per_day) == 30
    assert got.per_day[-1] == (TODAY, 2)
    assert got.per_day[-6][1] == 1
