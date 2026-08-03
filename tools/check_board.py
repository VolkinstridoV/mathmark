#!/usr/bin/env python3
"""
Проверка доски: что положили — то и достаётся обратно.

Доска хранит всё в одном файле, и любая потеря там необратима. Причём
потерять легко и незаметно: страница читает файл, что-то роняет по дороге,
показывает остаток — а следующее сохранение кладёт остаток поверх целого.
Поэтому здесь гоняется самое главное: `Board.load` и `Board.dump` в настоящем
движке, на доске со всеми видами предметов сразу.

Проверяется:
* ничего не пропало и не размножилось;
* штрихи, фигуры, надписи, бумажки и карточки вернулись со своими полями;
* границы предметов считаются числами, а не NaN — на этом ломалось
  «вписать всё в окно», едва на доске появлялась карточка;
* пометка «числа изменились» встаёт, когда числа в карточке поменяли, и
  не встаёт, когда не меняли.

Запуск: python3 tools/check_board.py
"""

from __future__ import annotations

import json
import pathlib
import sys

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("WebKit", "6.0")

from gi.repository import GLib, Gtk, WebKit  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[1]
PAGE = ROOT / "shared" / "board" / "board.html"

BOARD = {
    "version": 1,
    "view": {"x": 60, "y": 40, "z": 1},
    "items": [
        {"t": "stroke", "tool": "pen", "color": "#7B3BFF", "w": 3,
         "pts": [[10, 10], [40, 60], [90, 30]]},
        {"t": "shape", "kind": "rect", "tool": "pen", "color": "#C0392B", "w": 2,
         "x": 120, "y": 20, "w2": 80, "h2": 50},
        {"t": "text", "color": "#1B1720", "size": 20, "x": 30, "y": 150,
         "text": "D > 0 ⇒ два корня"},
        {"t": "card", "card": "quadratic", "key": 1, "color": "violet",
         "x": 40, "y": 220, "w": 330,
         "vals": {"a": "1", "b": "-5", "c": "6"}, "ready": True},
        {"t": "note", "md": "## Bessel\n\n$$\\sum |c_i|^2 \\le \\|x\\|^2$$",
         "color": "green", "w": 380, "x": 430, "y": 220,
         "file": "/tmp/нет.md", "heading": "Bessel"},
        {"t": "note", "md": "$$D = 1$$", "color": "violet", "w": 360,
         "x": 430, "y": 460,
         "from": {"card": "quadratic", "key": 1, "vals": {"a": "1", "b": "-5", "c": "6"}}},
    ],
}


class Check:
    def __init__(self) -> None:
        self.view = WebKit.WebView()
        self.win = Gtk.Window(title="ПРОВЕРКА ДОСКИ", default_width=1100, default_height=760)
        self.win.set_child(self.view)
        self.win.present()
        self.problems: list[str] = []
        self.view.connect("load-changed", self._loaded)
        html = PAGE.read_text(encoding="utf-8")
        self.view.load_html(html, PAGE.as_uri())

    def _js(self, code: str, then) -> None:
        def done(view, res):
            try:
                val = view.evaluate_javascript_finish(res)
                then(val.to_string() if val else "")
            except GLib.Error as e:
                then("ОШИБКА " + e.message)

        self.view.evaluate_javascript(code, -1, None, None, None, done)

    def _loaded(self, _v, event) -> None:
        if event == WebKit.LoadEvent.FINISHED:
            GLib.timeout_add(500, self._start)

    def _start(self) -> bool:
        cat = json.loads((ROOT / "shared" / "cards" / "catalog.json").read_text(encoding="utf-8"))
        self._js(f"Board.setLabels({{}}); Board.setCards({json.dumps(json.dumps(cat))}); "
                 f"Board.load({json.dumps(json.dumps(BOARD))}); 'ok'",
                 lambda _r: GLib.timeout_add(700, self._dump))
        return False

    def _dump(self) -> bool:
        self._js("Board.dump()", self._compare)
        return False

    def _compare(self, out: str) -> None:
        try:
            got = json.loads(out)
        except (ValueError, TypeError):
            self.problems.append(f"доска вернула не JSON: {out[:160]}")
            self._finish()
            return

        want, have = BOARD["items"], got.get("items", [])
        if len(have) != len(want):
            self.problems.append(f"предметов было {len(want)}, вернулось {len(have)}")

        by_kind_want = sorted(i["t"] for i in want)
        by_kind_have = sorted(i.get("t", "?") for i in have)
        if by_kind_want != by_kind_have:
            self.problems.append(f"состав изменился: было {by_kind_want}, стало {by_kind_have}")

        for w in want:
            same = [h for h in have
                    if h.get("t") == w["t"] and h.get("x") == w.get("x")
                    and h.get("y") == w.get("y")]
            if not same:
                self.problems.append(f"пропал предмет {w['t']} на x={w.get('x')}")
                continue
            h = same[0]
            for field in ("md", "text", "card", "color", "w", "pts", "vals", "file"):
                if field in w and h.get(field) != w[field]:
                    self.problems.append(f"{w['t']}: поле «{field}» изменилось при чтении")

        self._js("(function(){var r=[];Board.__bounds ? 0 : 0; return 'ok';})()",
                 lambda _r: self._bounds())

    def _bounds(self) -> None:
        """
        Границы обязаны быть числами. На NaN ломалось «вписать всё в окно»,
        едва на доске появлялась карточка, и заметить это было нечем.
        """
        code = """
        (function () {
          Board.find('');            // сбросить подсветку
          Board.fitAll();
          Board.forShot(true); Board.forShot(false);
          return JSON.stringify({
            find_card: Board.find('квадрат'),
            find_none: Board.find('такого_слова_нет_12345'),
            // выделение и находки — разные списки: иначе Delete после поиска
            // стирал бы все находки разом
            after_find: JSON.parse(Board.dump()).items.length
          });
        })()
        """
        def then(out: str) -> None:
            try:
                d = json.loads(out)
            except (ValueError, TypeError):
                self.problems.append(f"страница не ответила про картинку: {out[:120]}")
                self._stale()
                return
            if d.get("find_card") == "0":
                self.problems.append("поиск не нашёл карточку, которая на доске есть")
            if d.get("after_find") != len(BOARD["items"]):
                self.problems.append("после поиска на доске стало другое число предметов")
            if d.get("find_none") != "0":
                self.problems.append("поиск нашёл несуществующее слово")
            self._stale()

        self._js(code, then)

    def _stale(self) -> None:
        """Меняем числа в карточке — решение обязано пометиться устаревшим."""
        code = """
        (function () {
          var d = JSON.parse(Board.dump());
          for (var i = 0; i < d.items.length; i++) {
            if (d.items[i].t === 'card') d.items[i].vals.a = '2';
          }
          Board.load(JSON.stringify(d));
          var out = JSON.parse(Board.dump());
          var note = out.items.filter(function (x) { return x.from; })[0];
          return JSON.stringify({ stale: !!(note && note.stale) });
        })()
        """
        def then(out: str) -> None:
            try:
                if not json.loads(out).get("stale"):
                    self.problems.append("числа в карточке поменяли, а решение не помечено устаревшим")
            except (ValueError, TypeError):
                self.problems.append("не удалось проверить пометку «числа изменились»")
            self._finish()

        self._js(code, then)

    def _finish(self) -> None:
        print(f"предметов на доске: {len(BOARD['items'])}   ошибок: {len(self.problems)}")
        if self.problems:
            print()
            for p in self.problems:
                print("  ✗", p)
        else:
            print("\nдоска ничего не теряет: что положили — то и достали")
        self.code = 1 if self.problems else 0
        self.win.close()
        loop.quit()


loop = GLib.MainLoop()
check = Check()
GLib.timeout_add_seconds(60, lambda: (print("движок не ответил"), loop.quit())[1])
loop.run()
sys.exit(getattr(check, "code", 1))
