"""
Сведение двух версий одного файла при синхронизации.

Правило, о котором договорились: если один и тот же пункт отмечен по-разному
на телефоне и на компьютере, **выигрывает более продвинутое состояние** —
пройдено бьёт «разбираю», «разбираю» бьёт пустое. Вперёд, а не назад.

Всё остальное — разные строки, разные файлы — сходится само, потому что
отметка меняет один символ и никогда не двигает строки.

Если же разошёлся сам текст, а не отметки, программа ничего не выбирает:
говорит о споре и отдаёт обе версии наверх.
"""

from __future__ import annotations

from .md_items import ITEM, Mark, _pairs

RANK = {Mark.NONE: 0, Mark.HALF: 1, Mark.DONE: 2}


def _strip_mark(line: str) -> str | None:
    """Строка без символа отметки — чтобы сравнивать «всё, кроме галочки»."""
    m = ITEM.fullmatch(line)
    if not m or not _pairs(m.group(2), m.group(4)):
        return None
    return m.group(1) + "- " + m.group(2) + m.group(4) + " " + m.group(5)


def merge(base: str | None, local: str, remote: str) -> tuple[str, bool]:
    """
    Свести версии. Возвращает текст и признак спора.

    base — то, что было при прошлой синхронизации; None, если файл появился
    сразу с двух сторон.
    """
    if local == remote:
        return local, False
    if base is not None and local == base:
        return remote, False
    if base is not None and remote == base:
        return local, False

    ll = local.split("\n")
    rl = remote.split("\n")
    if len(ll) != len(rl):
        return local, True

    out: list[str] = []
    for a, b in zip(ll, rl):
        if a == b:
            out.append(a)
            continue
        sa, sb = _strip_mark(a), _strip_mark(b)
        if sa is None or sb is None or sa != sb:
            return local, True          # разошёлся текст, а не отметка
        ma = Mark.of(ITEM.fullmatch(a).group(3))
        mb = Mark.of(ITEM.fullmatch(b).group(3))
        winner = a if RANK[ma] >= RANK[mb] else b
        out.append(winner)
    return "\n".join(out), False
