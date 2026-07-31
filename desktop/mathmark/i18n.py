"""
Надписи программы. Берутся из общей папки `shared/i18n/` — те же самые файлы
читает версия для телефона, поэтому перевод один на обе.
"""

from __future__ import annotations

import json
import locale
from functools import lru_cache

from .md_items import Counts, FileKind, plural_form
from .paths import share_dir

LANGUAGES = ("en", "ru", "es")
FLAGS = {"en": "🇬🇧", "ru": "🇷🇺", "es": "🇪🇸"}
NATIVE = {"en": "English", "ru": "Русский", "es": "Español"}

_current = "en"


@lru_cache(maxsize=8)
def _table(code: str) -> dict:
    try:
        return json.loads((share_dir() / "i18n" / f"{code}.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def resolve(setting: str) -> str:
    if setting in LANGUAGES:
        return setting
    try:
        sys_lang = (locale.getlocale()[0] or "").split("_")[0]
    except ValueError:
        sys_lang = ""
    return sys_lang if sys_lang in LANGUAGES else "en"


def use(setting: str) -> str:
    """Выбрать язык. Возвращает то, что реально выбралось."""
    global _current
    _current = resolve(setting)
    return _current


def current() -> str:
    return _current


def t(key: str, *args) -> str:
    """Надпись по ключу. Если ключа нет — виден он сам, а не пустота."""
    raw = _table(_current).get(key, key)
    if not args:
        return raw
    # тот же вид подстановки, что у Android: %1$s, %2$s …
    out = raw
    for i, a in enumerate(args, start=1):
        out = out.replace(f"%{i}$s", str(a))
    return out


def subtitle(c: Counts) -> str:
    """Подпись под именем файла в списке."""
    if c.kind is FileKind.TASKS:
        return t("counts.tasks", c.tasks_done, c.tasks_total)
    if c.kind is FileKind.TOPICS:
        return t("counts.topics", c.topics_done, c.topics_total)
    if c.kind is FileKind.BOTH:
        return t("counts.both", c.tasks_done, c.tasks_total, c.topics_done, c.topics_total)
    if c.sections:
        return t("sections." + plural_form(c.sections, _current), c.sections)
    return t("counts.reference")


def sync_message(r) -> str:
    """Человеческий итог синхронизации."""
    if r.error:
        return r.error
    parts = []
    if r.changed == 0 and not r.conflicts:
        parts.append(t("sync.nothing"))
    else:
        parts.append(t("sync.done", len(r.uploaded), len(r.downloaded),
                       len(r.merged) + len(r.deleted_here) + len(r.deleted_there)))
    if r.conflicts:
        parts.append(t("sync.conflicts", len(r.conflicts)))
    return ". ".join(parts)
