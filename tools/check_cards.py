#!/usr/bin/env python3
"""
Проверка карточек-скриптов: каждая обязана посчитаться и нарисоваться.

Карточек десятки, и растёт их число текстом — значит, сломаться они будут
молча. Одна опечатка в описании, и человек нажмёт «Решить» и получит либо
пустоту, либо красную надпись вместо формулы. Поэтому здесь два прохода
подряд, и оба обязательны:

1. **Считает.** Каждая карточка решается на своём образце (поле `try` в
   каталоге — оно же подставляется в поля при открытии). Пустой разбор,
   негодные поля и сорвавшееся вычисление — ошибка.
2. **Рисуется.** Все строки разбора вместе с формулой карточки прогоняются
   через настоящий KaTeX. Что не отрисуется у нас — не отрисуется и у
   человека.

Проверяются заодно и мелочи, на которых легко проколоться: одинаковые
названия, забытый перевод, поле без подписи, условие без пояснения.

Запуск: python3 tools/check_cards.py
"""

from __future__ import annotations

import json
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "desktop"))

from mathmark.cards import Card, as_markdown, solve  # noqa: E402

CATALOG = ROOT / "shared" / "cards" / "catalog.json"
KATEX = ROOT / "shared" / "reader" / "katex" / "katex.min.js"
LANGS = ("en", "ru", "es")


def render_check(pieces: list[tuple[str, str]]) -> list[tuple[str, str]]:
    """Отдаём все формулы KaTeX разом — запускать node по разу на строку долго."""
    script = f"""
const katex = require({str(KATEX)!r});
const items = JSON.parse(require('fs').readFileSync(0, 'utf8'));
const bad = [];
for (const [who, tex] of items) {{
  try {{ katex.renderToString(tex, {{displayMode: true, throwOnError: true, strict: false}}); }}
  catch (e) {{ bad.push([who, String(e.message).slice(0, 120)]); }}
}}
process.stdout.write(JSON.stringify(bad));
"""
    out = subprocess.run(["node", "-e", script], input=json.dumps(pieces),
                         capture_output=True, text=True)
    if out.returncode != 0:
        print("не удалось запустить KaTeX:", out.stderr[:300])
        return [("движок", "node не отработал")]
    return json.loads(out.stdout or "[]")


def main() -> int:
    cat = json.loads(CATALOG.read_text(encoding="utf-8"))
    items = cat["items"]
    sections = {s["id"] for s in cat["sections"]}
    problems: list[str] = []
    pieces: list[tuple[str, str]] = []
    solved = 0

    seen_names: dict[str, str] = {}
    for raw in items:
        card = Card.of(raw)
        who = card.id

        if card.section not in sections:
            problems.append(f"{who}: раздел «{card.section}» не объявлен")
        for lang in LANGS:
            if not card.names.get(lang):
                problems.append(f"{who}: нет названия на «{lang}»")
            if not card.keys.get(lang):
                problems.append(f"{who}: нет слов для поиска на «{lang}»")
        for f in card.fields:
            if not f.label:
                problems.append(f"{who}: поле «{f.id}» без подписи")
        for need in card.need:
            if not need.get("show"):
                problems.append(f"{who}: условие «{need.get('if')}» без пояснения")

        key = card.names.get("ru", "")
        if key in seen_names:
            problems.append(f"{who}: то же название, что у «{seen_names[key]}»")
        seen_names[key] = who

        sample = raw.get("try")
        if not sample:
            problems.append(f"{who}: нет образца (`try`) — проверять не на чем")
            continue

        res = solve(card, sample)
        if res.bad:
            problems.append(f"{who}: образец не разобрался, поля {res.bad}")
            continue
        if res.blocked:
            problems.append(f"{who}: образец не проходит условия {res.blocked}")
            continue
        if not res.lines:
            problems.append(f"{who}: разбор пуст")
            continue

        solved += 1
        if card.form:
            pieces.append((f"{who} (формула)", card.form))
        for i, line in enumerate(res.lines, 1):
            pieces.append((f"{who} шаг {i}", line))

        md = as_markdown(card, sample, res)
        if "$$" not in md:
            problems.append(f"{who}: решение собралось без формул")

    bad = render_check(pieces)
    for who, err in bad:
        problems.append(f"{who}: не рисуется — {err}")

    print(f"карточек: {len(items)}   посчиталось: {solved}   "
          f"формул проверено: {len(pieces)}   ошибок: {len(problems)}")
    if problems:
        print()
        for p in problems:
            print("  ✗", p)
        return 1
    print("\nвсё сходится: каждая карточка считает и рисуется")
    return 0


if __name__ == "__main__":
    sys.exit(main())
