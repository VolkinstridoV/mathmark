"""
Разбор отмечаемых строк в тексте markdown и их правка.

Точный повтор `MdItems.kt` из версии для телефона — вплоть до тех же тестов.
Здесь нет ни одной ссылки на окна и графику.

Главное правило приложения: отметка меняет РОВНО ОДИН символ исходного текста.
Текст не разбирается в модель и не собирается обратно, порядок строк не
меняется никогда, длина файла остаётся прежней.

Две разновидности строк, различаются скобками:

    - [ ] Вывести производную     задача — сделанная перечёркивается
    - ( ) Ряды Фурье              тема   — пройденная гаснет, но остаётся целой

Три состояния у обеих: пусто → наполовину → готово → пусто.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum

# `- [ ] текст` или `- ( ) текст`, с любым отступом слева
ITEM = re.compile(r"^(\s*)-\s([\[(])([ xX~/])([\])])\s(.*)$")
HEAD = re.compile(r"^(#{1,3})\s+(.+)$")


class Kind(Enum):
    TASK = "task"
    TOPIC = "topic"


class Mark(Enum):
    NONE = " "
    HALF = "~"
    DONE = "x"

    @staticmethod
    def of(c: str) -> "Mark":
        if c in "~/":
            return Mark.HALF
        if c in "xX":
            return Mark.DONE
        return Mark.NONE


class FileKind(Enum):
    TASKS = "tasks"
    TOPICS = "topics"
    BOTH = "both"
    PLAIN = "plain"


@dataclass(frozen=True)
class MdItem:
    line_index: int
    box_offset: int   # смещение символа между скобками в исходном тексте
    kind: Kind
    mark: Mark
    label: str


@dataclass(frozen=True)
class Counts:
    tasks_total: int = 0
    tasks_done: int = 0
    tasks_half: int = 0
    topics_total: int = 0
    topics_done: int = 0
    topics_half: int = 0
    sections: int = 0

    @property
    def kind(self) -> FileKind:
        if self.tasks_total and self.topics_total:
            return FileKind.BOTH
        if self.tasks_total:
            return FileKind.TASKS
        if self.topics_total:
            return FileKind.TOPICS
        return FileKind.PLAIN

    @property
    def progress(self) -> float:
        """Половинка считается за половину — иначе прогресс стоит на месте."""
        total = self.tasks_total + self.topics_total
        if total == 0:
            return 0.0
        done = self.tasks_done + self.topics_done + (self.tasks_half + self.topics_half) * 0.5
        return done / total


def _pairs(open_br: str, close_br: str) -> bool:
    return (open_br == "[" and close_br == "]") or (open_br == "(" and close_br == ")")


def is_item(line: str) -> bool:
    m = ITEM.fullmatch(line)
    return bool(m) and _pairs(m.group(2), m.group(4))


def _line_starts(text: str) -> list[int]:
    starts = [0]
    for i, ch in enumerate(text):
        if ch == "\n":
            starts.append(i + 1)
    return starts


def items(text: str) -> list[MdItem]:
    """Все отмечаемые строки текста, в порядке появления."""
    starts = _line_starts(text)
    out: list[MdItem] = []
    for i, line in enumerate(text.split("\n")):
        m = ITEM.fullmatch(line)
        if not m or not _pairs(m.group(2), m.group(4)):
            continue
        open_br = m.group(2)
        out.append(
            MdItem(
                line_index=i,
                box_offset=starts[i] + line.index(open_br) + 1,
                kind=Kind.TASK if open_br == "[" else Kind.TOPIC,
                mark=Mark.of(m.group(3)),
                label=m.group(5).rstrip("\r"),
            )
        )
    return out


def cycle(text: str, box_offset: int) -> str:
    """
    Переключить отметку по кругу: пусто → наполовину → готово → пусто.

    Меняется ровно один символ по смещению. Длина текста не меняется,
    все остальные байты остаются прежними.
    """
    if not 0 <= box_offset < len(text):
        raise ValueError(f"смещение {box_offset} вне текста длиной {len(text)}")
    c = text[box_offset]
    mark = Mark.of(c)
    if mark is Mark.NONE:
        if c != " ":
            raise ValueError(f"по смещению {box_offset} ожидался пробел, ~ или x, а там {c!r}")
        nxt = Mark.HALF.value
    elif mark is Mark.HALF:
        nxt = Mark.DONE.value
    else:
        nxt = Mark.NONE.value
    return text[:box_offset] + nxt + text[box_offset + 1:]


def counts(text: str) -> Counts:
    """Сводка по файлу — для подписи и значка в списке."""
    found = items(text)
    tasks = [i for i in found if i.kind is Kind.TASK]
    topics = [i for i in found if i.kind is Kind.TOPIC]
    return Counts(
        tasks_total=len(tasks),
        tasks_done=sum(1 for i in tasks if i.mark is Mark.DONE),
        tasks_half=sum(1 for i in tasks if i.mark is Mark.HALF),
        topics_total=len(topics),
        topics_done=sum(1 for i in topics if i.mark is Mark.DONE),
        topics_half=sum(1 for i in topics if i.mark is Mark.HALF),
        sections=sum(1 for line in text.split("\n") if HEAD.fullmatch(line)),
    )


def _razdelov(n: int) -> str:
    if 11 <= n % 100 <= 14:
        return "разделов"
    last = n % 10
    if last == 1:
        return "раздел"
    if last in (2, 3, 4):
        return "раздела"
    return "разделов"


def subtitle(c: Counts) -> str:
    """Подпись под именем файла в списке."""
    if c.kind is FileKind.TASKS:
        return f"{c.tasks_done} из {c.tasks_total} задач"
    if c.kind is FileKind.TOPICS:
        return f"пройдено {c.topics_done} из {c.topics_total} тем"
    if c.kind is FileKind.BOTH:
        return (f"{c.tasks_done} из {c.tasks_total} задач · "
                f"{c.topics_done} из {c.topics_total} тем")
    return f"{c.sections} {_razdelov(c.sections)}" if c.sections else "справочник"
