"""
Где лежат общие файлы: страница чтения, KaTeX и промпт.

Одни и те же файлы использует версия для телефона. Ищем их сначала рядом с
исходниками (когда программа запущена из репозитория), потом в местах, куда
их кладёт установка — обычная или через Flatpak.
"""

from __future__ import annotations

import os
from pathlib import Path

_HERE = Path(__file__).resolve().parent

_CANDIDATES = [
    _HERE.parents[1] / "shared",              # запуск из репозитория
    Path("/app/share/mathmark"),                 # Flatpak
    Path(os.environ.get("MATHMARK_SHARE", "/usr/share/mathmark")),
    Path.home() / ".local/share/mathmark",
]


def share_dir() -> Path:
    for c in _CANDIDATES:
        if (c / "reader" / "reader.html").is_file():
            return c
    raise FileNotFoundError(
        "не нашёл общую папку с reader.html — искал в: "
        + ", ".join(str(c) for c in _CANDIDATES)
    )


def stamped(page: Path) -> str:
    """
    Страница со «штампом» на каждом своём сценарии и стиле.

    WebKit держит `file://`-файлы в кэше и правки до окна не доносит: меняешь
    вид, перезапускаешь — а на экране прежнее. Обход простой: к именам
    подставляемых файлов дописывается время их правки, и для WebKit это уже
    другой адрес. Обход был у доски, из-за чего доска обновлялась, а читалка,
    помогалка и вырезание — нет.
    """
    import re

    html = page.read_text(encoding="utf-8")

    def mark(m: str) -> str:
        target = (page.parent / m).resolve()
        try:
            return f"{m}?v={int(target.stat().st_mtime)}"
        except OSError:
            return m

    def sub(match: "re.Match[str]") -> str:
        src = match.group(2)
        if "://" in src or src.startswith("data:") or "?" in src:
            return match.group(0)
        return match.group(1) + mark(src) + match.group(3)

    html = re.sub(r'(<script[^>]*\ssrc=")([^"]+)(")', sub, html)
    return re.sub(r'(<link[^>]*\shref=")([^"]+)(")', sub, html)


def reader_html() -> Path:
    return share_dir() / "reader" / "reader.html"


def board_html() -> Path:
    return share_dir() / "board" / "board.html"


def write_html() -> Path:
    return share_dir() / "write" / "write.html"


def cards_catalog() -> dict:
    """Каталог карточек-скриптов. Нет файла — пустой каталог, доска не падает."""
    import json
    try:
        return json.loads((share_dir() / "cards" / "catalog.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"version": 1, "sections": [], "items": []}


def write_catalog() -> dict:
    """Каталог записи математики. Нет файла — пустой каталог, окно не падает."""
    import json
    try:
        return json.loads((share_dir() / "write" / "catalog.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"version": 1, "labels": {}, "sections": [], "items": []}


def links() -> dict:
    """Ссылки наружу — общий файл на обе версии."""
    import json
    try:
        return json.loads((share_dir() / "meta" / "links.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def whats_new(version: str, lang: str) -> list:
    """Список новинок этой версии на нужном языке. Нет файла — пусто."""
    import json
    try:
        table = json.loads((share_dir() / "whatsnew" / f"{version}.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    return table.get(lang) or table.get("en") or []


def prompt_text() -> str:
    p = share_dir() / "prompt" / "prompt.md"
    try:
        return p.read_text(encoding="utf-8")
    except OSError:
        return ""
