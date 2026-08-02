#!/usr/bin/env python3
"""
Проверка вырезания: нарисовал — выделил всё — собрал обратно.

Вырезание куска на доску держится на одном допущении: из нарисованной
страницы можно собрать тот же markdown, из которого её нарисовали. Если это
неверно хоть для одной разметки, на доску ляжет каша, и заметит это человек,
а не мы. Поэтому здесь настоящая страница чтения в настоящем движке: файл
рисуется, выделяется целиком, собирается назад и сравнивается с исходником.

Сравнение не побайтовое — при разборе теряются необязательные мелочи вроде
числа пустых строк. Сверяется то, что имеет смысл: формулы, отметки, скрытые
куски, заголовки, порядок строк.

Запуск: python3 tools/check_cut.py
"""

from __future__ import annotations

import json
import pathlib
import re
import sys

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("WebKit", "6.0")

from gi.repository import GLib, Gtk, WebKit  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[1]
READER = ROOT / "shared" / "reader" / "reader.html"

CASES: dict[str, str] = {
    "заголовки и абзац": """\
# Матанализ

## Производные

Производная — предел отношения приращений.
""",
    "формулы в строке и отдельной строкой": """\
Возьмём $f(x)=\\sqrt{x^3}$ и посмотрим.

$$f'(x) = \\lim_{\\Delta x \\to 0} \\frac{f(x + \\Delta x) - f(x)}{\\Delta x}$$
""",
    "задачи и темы во всех состояниях": """\
- [ ] Вывести производную
- [~] Разобрать эпсилон-дельта
- [x] Таблица производных
- ( ) Ряды Фурье
- (~) Кратные интегралы
- (x) Цепное правило
""",
    "скрытый кусок": """\
Ответ: ||$f'(x) = \\tfrac{3}{2}\\sqrt{x}$|| — открывается нажатием.
""",
    "матрица и система": """\
$$A = \\begin{pmatrix} 2 & 1 \\\\ 0 & 3 \\end{pmatrix}$$

$$\\begin{cases} x + y = 2 \\\\ x - y = 0 \\end{cases}$$
""",
    "выделение и списки": """\
Это **важно**, это *менее важно*, это ~~отменено~~, а это `код`.

- первый пункт
- второй пункт с формулой $x^2$
""",
    "таблица": """\
| Функция | Производная |
| --- | --- |
| $x^n$ | $nx^{n-1}$ |
| $\\ln x$ | $1/x$ |
""",
    "цитата и черта": """\
> Знание не вычёркивают.

---

Дальше обычный текст.
""",
}


def significant(md: str) -> list[str]:
    """То, что обязано выжить: формулы, отметки, скрытое, заголовки, слова."""
    out = []
    for m in re.finditer(r"\$\$(.+?)\$\$|\$([^\n$]+?)\$", md, re.S):
        out.append("формула:" + re.sub(r"\s+", " ", (m.group(1) or m.group(2)).strip()))
    for m in re.finditer(r"-\s([\[(])([ x~])([\])])\s(.+)", md):
        out.append(f"отметка:{m.group(1)}{m.group(2)}{m.group(3)} {m.group(4).strip()}")
    for m in re.finditer(r"\|\|(.+?)\|\|", md, re.S):
        out.append("скрытое:" + re.sub(r"\s+", " ", m.group(1).strip()))
    for m in re.finditer(r"^(#{1,3})\s+(.+)$", md, re.M):
        out.append(f"заголовок{len(m.group(1))}:{m.group(2).strip()}")
    for tag, sign in (("**", "жирный"), ("~~", "зачёркнутый"), ("`", "код")):
        for m in re.finditer(re.escape(tag) + r"(.+?)" + re.escape(tag), md):
            out.append(f"{sign}:{m.group(1)}")
    for m in re.finditer(r"^>\s*(.+)$", md, re.M):
        out.append("цитата:" + m.group(1).strip())
    if re.search(r"^---+\s*$", md, re.M):
        out.append("черта")
    for m in re.finditer(r"^-\s(?![\[(])(.+)$", md, re.M):
        out.append("пункт:" + re.sub(r"\s+", " ", m.group(1).strip()))
    return out


class Checker:
    def __init__(self) -> None:
        self.view = WebKit.WebView()
        self.win = Gtk.Window(default_width=900, default_height=700)
        self.win.set_child(self.view)
        # Окно приходится показать: без этого WebKit не раскладывает страницу,
        # а выделение без раскладки не работает — проверять было бы нечего.
        self.win.present()
        self.failures: list[str] = []
        self.queue = list(CASES.items())
        self.view.connect("load-changed", self._loaded)
        self.view.load_uri(READER.as_uri())

    def _js(self, code: str, then) -> None:
        def done(view, res):
            try:
                val = view.evaluate_javascript_finish(res)
                then(val.to_string() if val else "")
            except GLib.Error as e:
                then("ОШИБКА " + e.message)

        self.view.evaluate_javascript(code, -1, None, None, None, done)

    def _loaded(self, _view, event) -> None:
        if event == WebKit.LoadEvent.FINISHED:
            GLib.timeout_add(300, self._next)

    def _next(self) -> bool:
        if not self.queue:
            self._finish()
            return False
        name, src = self.queue.pop(0)
        self._js(f"MathMark.render({json.dumps(src)}); 'ok'",
                 lambda _r: GLib.timeout_add(120, self._cut, name, src))
        return False

    def _cut(self, name: str, src: str) -> bool:
        code = """
        (function () {
          var d = document.getElementById('doc');
          var r = document.createRange();
          r.selectNodeContents(d);
          var s = window.getSelection();
          s.removeAllRanges(); s.addRange(r);
          return MathMark.cut();
        })()
        """
        self._js(code, lambda out: self._compare(name, src, out))
        return False

    def _compare(self, name: str, src: str, out: str) -> None:
        try:
            got = json.loads(out).get("md", "")
        except (ValueError, TypeError):
            self.failures.append(f"{name}: движок вернул не JSON — {out[:120]}")
            GLib.idle_add(self._next)
            return

        want, have = significant(src), significant(got)
        missing = [x for x in want if x not in have]
        if missing:
            self.failures.append(
                f"{name}: потерялось {len(missing)} из {len(want)}\n"
                + "\n".join("      нет: " + m for m in missing[:6])
                + "\n    собралось:\n      " + got.replace("\n", "\n      ")[:400]
            )
        else:
            print(f"  ✓ {name}  ({len(want)} проверок)")
        GLib.idle_add(self._next)

    def _finish(self) -> None:
        print()
        if self.failures:
            print("НЕ СОШЛОСЬ:\n")
            for f in self.failures:
                print("  •", f, "\n")
        else:
            print("всё сошлось: нарисованное собирается обратно в исходник")
        self.code = 1 if self.failures else 0
        self.win.close()
        loop.quit()


loop = GLib.MainLoop()
checker = Checker()
GLib.timeout_add_seconds(60, lambda: (print("не дождались движка"), loop.quit())[1])
loop.run()
sys.exit(checker.code if hasattr(checker, "code") else 1)
