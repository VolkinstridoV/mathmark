"""
Журнал отметок и подсчёт движения по нему.

Каждое нажатие на кружок дописывает одну строку в обычный текстовый файл
рядом с настройками:

    2026-07-31T18:50:12|Матан.md|task|done

Именно момент отметки, а не момент синхронизации: отметил утром,
синхронизировал через три дня — статистика должна показать утро.

Файл только растёт и никогда не переписывается, поэтому испортить его
нечем. Строку можно удалить руками — ничего не сломается.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path

from .md_items import Kind, Mark


@dataclass
class Entry:
    when: datetime
    path: str
    kind: Kind
    mark: Mark


@dataclass
class Stats:
    """Сводка для экрана «сколько сделано»."""
    today_tasks: int = 0
    today_topics: int = 0
    week_tasks: int = 0
    week_topics: int = 0
    month_tasks: int = 0
    month_topics: int = 0
    streak: int = 0                       # дней подряд, считая назад от сегодня
    per_day: list[tuple[date, int]] = field(default_factory=list)   # последние 30 дней


def record(journal: Path, path: str, kind: Kind, mark: Mark, when: datetime | None = None) -> None:
    """Дописать строку. Ошибка записи не должна мешать работе — молчим."""
    when = when or datetime.now()
    line = f"{when.isoformat(timespec='seconds')}|{path}|{kind.value}|{mark.value}\n"
    try:
        journal.parent.mkdir(parents=True, exist_ok=True)
        with journal.open("a", encoding="utf-8") as fh:
            fh.write(line)
    except OSError:
        pass


def parse(text: str) -> list[Entry]:
    out: list[Entry] = []
    for raw in text.split("\n"):
        parts = raw.strip().split("|")
        if len(parts) != 4:
            continue
        try:
            when = datetime.fromisoformat(parts[0])
        except ValueError:
            continue
        kind = Kind.TASK if parts[2] == "task" else Kind.TOPIC
        out.append(Entry(when, parts[1], kind, Mark.of(parts[3] or " ")))
    return out


def summarise(entries: list[Entry], today: date | None = None) -> Stats:
    """
    Считаем только закрытия — переход в «готово». Снятие отметки не отнимает:
    это не отчётность, а счётчик движения вперёд.
    """
    today = today or date.today()
    done = [e for e in entries if e.mark is Mark.DONE]
    s = Stats()

    by_day: Counter[date] = Counter()
    for e in done:
        d = e.when.date()
        by_day[d] += 1
        days = (today - d).days
        if days == 0:
            if e.kind is Kind.TASK:
                s.today_tasks += 1
            else:
                s.today_topics += 1
        if 0 <= days < 7:
            if e.kind is Kind.TASK:
                s.week_tasks += 1
            else:
                s.week_topics += 1
        if 0 <= days < 30:
            if e.kind is Kind.TASK:
                s.month_tasks += 1
            else:
                s.month_topics += 1

    # серия: сколько дней подряд подряд что-то закрывалось, считая назад
    day = today
    while by_day.get(day, 0) > 0:
        s.streak += 1
        day -= timedelta(days=1)

    s.per_day = [(today - timedelta(days=i), by_day.get(today - timedelta(days=i), 0))
                 for i in range(29, -1, -1)]
    return s
