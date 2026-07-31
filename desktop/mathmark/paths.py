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


def reader_html() -> Path:
    return share_dir() / "reader" / "reader.html"


def prompt_text() -> str:
    p = share_dir() / "prompt" / "prompt.md"
    try:
        return p.read_text(encoding="utf-8")
    except OSError:
        return ""
