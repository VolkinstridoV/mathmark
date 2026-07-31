"""
Напоминания, навешенные на файл.

Хранятся отдельным текстовым файлом рядом с настройками — внутрь `.md`
не пишется ничего:

    Линал/собственные.md|daily|19:00|повторить линал
    Матан.md|weekly|1|09:30|разобрать Тейлора
    Шпора.md|once|2026-08-05T19:00|перед экзаменом

Строку можно поправить руками. Раз файл лежит не в папке с математикой,
синхронизация его не переносит: на каждом устройстве свои напоминания.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from pathlib import Path

DAILY, WEEKLY, ONCE = "daily", "weekly", "once"


@dataclass(frozen=True)
class Reminder:
    path: str          # путь файла относительно папки с математикой
    repeat: str        # daily | weekly | once
    at: time           # время суток
    text: str
    weekday: int = 0   # для weekly: 1 — понедельник … 7 — воскресенье
    on: date | None = None   # для once

    def line(self) -> str:
        if self.repeat == DAILY:
            return f"{self.path}|daily|{self.at:%H:%M}|{self.text}"
        if self.repeat == WEEKLY:
            return f"{self.path}|weekly|{self.weekday}|{self.at:%H:%M}|{self.text}"
        when = datetime.combine(self.on or date.today(), self.at)
        return f"{self.path}|once|{when.isoformat(timespec='minutes')}|{self.text}"

    def due_on(self, day: date) -> bool:
        """Сработает ли в этот день."""
        if self.repeat == DAILY:
            return True
        if self.repeat == WEEKLY:
            return day.isoweekday() == self.weekday
        return self.on == day

    def next_after(self, moment: datetime) -> datetime | None:
        """Ближайшее срабатывание строго после указанного момента."""
        if self.repeat == ONCE:
            when = datetime.combine(self.on, self.at) if self.on else None
            return when if when and when > moment else None
        day = moment.date()
        for step in range(0, 8):
            d = day + timedelta(days=step)
            if not self.due_on(d):
                continue
            when = datetime.combine(d, self.at)
            if when > moment:
                return when
        return None


def parse(text: str) -> list[Reminder]:
    out: list[Reminder] = []
    for raw in text.split("\n"):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split("|")
        try:
            if len(parts) == 4 and parts[1] == DAILY:
                out.append(Reminder(parts[0], DAILY, _time(parts[2]), parts[3]))
            elif len(parts) == 5 and parts[1] == WEEKLY:
                wd = int(parts[2])
                if not 1 <= wd <= 7:
                    continue
                out.append(Reminder(parts[0], WEEKLY, _time(parts[3]), parts[4], weekday=wd))
            elif len(parts) == 4 and parts[1] == ONCE:
                when = datetime.fromisoformat(parts[2])
                out.append(Reminder(parts[0], ONCE, when.time(), parts[3], on=when.date()))
        except (ValueError, IndexError):
            continue
    return out


def _time(s: str) -> time:
    h, m = s.split(":")
    return time(int(h), int(m))


def dump(items: list[Reminder]) -> str:
    return "".join(r.line() + "\n" for r in items)


def load(file: Path) -> list[Reminder]:
    try:
        return parse(file.read_text(encoding="utf-8"))
    except OSError:
        return []


def save(file: Path, items: list[Reminder]) -> None:
    try:
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text(dump(items), encoding="utf-8")
    except OSError:
        pass


def for_day(items: list[Reminder], day: date) -> list[Reminder]:
    """Что сработает в этот день — по возрастанию времени."""
    return sorted((r for r in items if r.due_on(day)), key=lambda r: r.at)
