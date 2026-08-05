#!/usr/bin/env python3
"""
Собирает страницы изменений из общих списков новинок.

Источник один — `shared/whatsnew/<версия>.json`. Те же файлы приложение
показывает в окне «что нового» после обновления, поэтому список изменений
и то, что видит человек, не могут разойтись.

Запуск: python3 tools/changelog.py
"""

import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[1]
NEWS = ROOT / "shared" / "whatsnew"

DATES = {"1.0": "2026-07-31", "1.0.1": "2026-07-31", "1.0.2": "2026-07-31",
         "1.1": "2026-08-02",
         "1.2": "2026-08-02",
         "1.3": "2026-08-03",
         "1.4": "2026-08-03",
         "1.4.1": "2026-08-05"}

HEAD = {
    "en": ("# Changelog\n\n[Русский](CHANGELOG.ru.md) · [Español](CHANGELOG.es.md)\n\n"
           "Every version and what appeared in it. The same lists are shown inside the app\n"
           "after an update.\n"),
    "ru": ("# Что менялось\n\n[English](CHANGELOG.md) · [Español](CHANGELOG.es.md)\n\n"
           "Все версии и что в них появилось. Те же списки приложение показывает\n"
           "после обновления.\n"),
    "es": ("# Cambios\n\n[English](CHANGELOG.md) · [Русский](CHANGELOG.ru.md)\n\n"
           "Todas las versiones y lo que apareció en cada una. Las mismas listas se ven\n"
           "dentro de la aplicación tras actualizar.\n"),
}

FILES = {"en": "CHANGELOG.md", "ru": "CHANGELOG.ru.md", "es": "CHANGELOG.es.md"}


def key(name: str):
    return tuple(int(p) for p in name.split("."))


def main() -> None:
    versions = sorted(
        (p.stem for p in NEWS.glob("*.json") if re.fullmatch(r"[\d.]+", p.stem)),
        key=key, reverse=True,
    )
    for lang, filename in FILES.items():
        out = [HEAD[lang]]
        for v in versions:
            table = json.loads((NEWS / f"{v}.json").read_text(encoding="utf-8"))
            items = table.get(lang) or table.get("en") or []
            date = DATES.get(v, "")
            out.append(f"\n## {v}" + (f" — {date}" if date else "") + "\n")
            out.extend(f"- {line}" for line in items)
            out.append("")
        (ROOT / filename).write_text("\n".join(out) + "\n", encoding="utf-8")
        print("собрал", filename)


if __name__ == "__main__":
    main()
