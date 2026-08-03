"""
Окно доски.

Отдельное окно той же программы: своя папка не нужна, свои настройки не нужны,
но живёт оно само по себе — закрыл доску, читалка осталась.

Сам холст рисует страница в `shared/board/`. Так сделано нарочно: позже на
доску лягут листочки с формулами, а рисует их KaTeX, который живёт в странице.
Здесь — только окно вокруг: список досок, сохранение, тема.

Файлы досок лежат в той же папке с математикой, но с расширением `.board`,
поэтому в списке заметок они не появляются и каши не создают.
"""

from __future__ import annotations

import json
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
gi.require_version("WebKit", "6.0")

from gi.repository import Adw, Gio, GLib, Gtk, WebKit  # noqa: E402

from .i18n import current as i18n_current  # noqa: E402
from .i18n import t  # noqa: E402
from .cards import Card, as_markdown, solve  # noqa: E402
from .paths import board_html, cards_catalog, stamped  # noqa: E402

SUFFIX = ".board"


def boards_in(folder: Path) -> list[Path]:
    """Все доски папки, включая вложенные. Порядок — по имени."""
    try:
        return sorted(
            (p for p in Path(folder).rglob("*" + SUFFIX) if not p.name.startswith(".")),
            key=lambda p: p.name.lower(),
        )
    except OSError:
        return []


class BoardWindow(Adw.ApplicationWindow):
    """Одно окно — одна доска. Список досок открывается кнопкой в шапке."""

    def __init__(self, app, settings, folder: Path, path: Path | None = None):
        super().__init__(application=app, title=t("board.title"))
        self.st = settings
        self.folder = Path(folder)
        self.path: Path | None = None
        self._dirty = False

        self.set_default_size(1180, 800)
        self.set_size_request(560, 420)
        self.connect("close-request", self._on_close)

        self._build()
        self.set_focus(self.web)
        if path is not None:
            self.open(path)

    # ——— окно ———

    def _build(self) -> None:
        view = Adw.ToolbarView()
        head = Adw.HeaderBar()

        self.title_widget = Adw.WindowTitle(title=t("board.title"), subtitle="")
        head.set_title_widget(self.title_widget)

        menu = Gio.Menu()
        menu.append(t("board.new"), "win.board-new")
        menu.append(t("board.clear"), "win.board-clear")
        head.pack_end(Gtk.MenuButton(icon_name="open-menu-symbolic", menu_model=menu))

        write = Gtk.Button(icon_name="accessories-dictionary-symbolic",
                           tooltip_text=t("write.title") + "  (Ctrl+M)")
        write.connect("clicked", lambda *_: self.get_application().open_writer(self))
        head.pack_end(write)

        formula = Gtk.Button(icon_name="list-add-symbolic",
                             tooltip_text=t("card.open") + "  (Ctrl+G)")
        formula.connect("clicked", lambda *_: self.open_picker())
        head.pack_end(formula)

        cut = Gtk.Button(icon_name="edit-cut-symbolic",
                         tooltip_text=t("cut.open") + "  (Ctrl+T)")
        cut.connect("clicked", lambda *_: self.open_cutter())
        head.pack_end(cut)

        save = Gtk.Button(icon_name="document-save-symbolic", tooltip_text=t("edit.save"))
        save.connect("clicked", lambda *_: self.save())
        head.pack_end(save)

        self.list_btn = Gtk.MenuButton(icon_name="view-list-symbolic",
                                       tooltip_text=t("board.title"))
        self.list_pop = Gtk.Popover()
        self.list_btn.set_popover(self.list_pop)
        head.pack_start(self.list_btn)

        view.add_top_bar(head)

        ucm = WebKit.UserContentManager()
        ucm.register_script_message_handler("mathmark", None)
        ucm.connect("script-message-received::mathmark", self._on_message)

        self.web = WebKit.WebView(user_content_manager=ucm, vexpand=True)
        self.web.connect("load-changed", self._on_load)
        self._load_page()
        view.set_content(self.web)

        self.toasts = Adw.ToastOverlay()
        self.toasts.set_child(view)
        self.set_content(self.toasts)

    def _load_page(self) -> None:
        """Страница со штампами на сценариях — обход кэша WebKit, см. paths.stamped."""
        page = board_html()
        self.web.load_html(stamped(page), page.as_uri())

    # ——— связь со страницей ———

    def _js(self, script: str) -> None:
        self.web.evaluate_javascript(script, -1, None, None, None, None, None)

    def _labels(self) -> str:
        keys = ("board.select", "board.hand", "board.text", "board.pen", "board.marker", "board.eraser",
                "board.line", "board.arrow", "board.rect", "board.ellipse", "board.triangle",
                "board.undo", "board.redo", "board.fit", "board.zoomIn", "board.zoomOut")
        out = {"board." + k.split(".", 1)[1]: t(k) for k in keys}
        # бумажки подписаны своими строками, не из набора инструментов
        for k in ("note.source", "note.edited", "card.solve", "card.formula", "card.stale"):
            out[k] = t(k)
        out["__lang"] = i18n_current()
        return json.dumps(out)

    def _on_load(self, _web, event) -> None:
        if event != WebKit.LoadEvent.FINISHED:
            return
        dark = Adw.StyleManager.get_default().get_dark()
        self._js(f"Board.setLabels({self._labels()});Board.setTheme({str(dark).lower()});")
        self._js(f"Board.setCards({json.dumps(json.dumps(self._catalog))});")
        # без этого нажатия клавиш до страницы не доходят и отмена не работает
        self.web.grab_focus()
        if self.path is not None:
            self._js(f"Board.load({json.dumps(self._read())});")

    def _on_message(self, _ucm, value) -> None:
        try:
            data = json.loads(value.to_string())
        except (ValueError, AttributeError):
            return
        name, payload = data.get("name"), data.get("payload")
        if name == "onDirty":
            self._mark_dirty(True)
        elif name == "onSave":
            self._write(payload)
        elif name == "onSource":
            self._show_source(payload)
        elif name == "onCardCheck":
            self._card_check(payload)
        elif name == "onCardSolve":
            self._card_solve(payload)
        elif name == "onCardForm":
            self._card_form(payload)

    # ——— карточки-скрипты ———

    @property
    def _catalog(self) -> dict:
        if getattr(self, "_cat", None) is None:
            self._cat = cards_catalog()
            self._cards = {c["id"]: Card.of(c) for c in self._cat.get("items", [])}
        return self._cat

    def open_picker(self) -> None:
        """Выбор формулы. Окно одно: второй раз — поднимаем прежнее."""
        from .picker import PickerWindow

        old = getattr(self, "_picker", None)
        if old is not None:
            old.present()
            return

        def pick(card_id: str) -> None:
            self._js(f"Board.addCard({json.dumps(card_id)});")

        win = PickerWindow(self.get_application(), self._catalog, pick)

        def gone(*_):
            self._picker = None
            return False

        win.connect("close-request", gone)
        self._picker = win
        win.present()

    def _solve(self, payload: str):
        try:
            d = json.loads(payload)
        except (ValueError, TypeError):
            return None, None
        self._catalog  # noqa: B018 — подтягиваем каталог, если ещё не читали
        card = self._cards.get(d.get("card"))
        if card is None:
            return None, None
        return d, (card, solve(card, d.get("vals") or {}))

    def _card_check(self, payload: str) -> None:
        """Ответ на каждую правку поля: гасить кнопку или нет и почему."""
        d, got = self._solve(payload)
        if not got:
            return
        _card, res = got
        state = {"i": d.get("i"), "ok": res.ok, "bad": res.bad, "blocked": res.blocked}
        self._js(f"Board.cardState({json.dumps(json.dumps(state))});")

    def _card_solve(self, payload: str) -> None:
        d, got = self._solve(payload)
        if not got:
            return
        card, res = got
        if not res.ok:
            return
        md = as_markdown(card, d.get("vals") or {}, res)
        out = {"i": d.get("i"), "md": md, "color": d.get("color"),
               "h": 150 + 26 * len(res.lines)}
        self._js(f"Board.addSolution({json.dumps(json.dumps(out))});")

    def _card_form(self, payload: str) -> None:
        """«Показать формулу» — то же окно, что и «Показать источник»."""
        try:
            d = json.loads(payload)
        except (ValueError, TypeError):
            return
        self._catalog  # noqa: B018
        card = self._cards.get(d.get("card"))
        if card is None:
            return
        text = "$$\n" + card.form + "\n$$\n"
        for f in card.fields:
            val = (d.get("vals") or {}).get(f.id)
            if val:
                text += f"\n$${f.label} = {val}$$\n"
        self._show_text(t("card.formula"), text)

    # ——— вырезание куска конспекта ———

    def open_cutter(self, path: Path | None = None) -> None:
        """
        Окно вырезания одно на доску: второй раз — поднимаем прежнее, чтобы
        не разводить одинаковые окна. Открытое на источнике списка не
        показывает — это разные входы в одно и то же окно.
        """
        from .cutter import CutWindow

        old = getattr(self, "_cutter", None)
        if old is not None and path is None:
            old.present()
            return
        if old is not None:
            old.close()

        win = CutWindow(self.get_application(), self.st, Path(self.folder),
                        on_cut=self._take_note, path=path)

        def gone(*_):
            self._cutter = None
            return False

        win.connect("close-request", gone)
        self._cutter = win
        win.present()

    def _show_text(self, heading: str, text: str) -> None:
        """Показать готовый кусок в том же окне, что и источник вырезанного."""
        from .cutter import CutWindow

        old = getattr(self, "_cutter", None)
        if old is not None:
            old.close()
        win = CutWindow(self.get_application(), self.st, Path(self.folder),
                        on_cut=self._take_note, text=text, heading=heading)

        def gone(*_):
            self._cutter = None
            return False

        win.connect("close-request", gone)
        self._cutter = win
        win.present()

    def _take_note(self, payload: dict) -> None:
        self._js(f"Board.addNote({json.dumps(json.dumps(payload))});")

    def _show_source(self, payload: str) -> None:
        try:
            data = json.loads(payload)
        except (ValueError, TypeError):
            return
        path = Path(data.get("file") or "")
        if not path.is_file():
            self.toasts.add_toast(Adw.Toast(title=t("note.gone")))
            return
        self.open_cutter(path)

    # ——— файлы ———

    def _read(self) -> str:
        try:
            return self.path.read_text(encoding="utf-8")
        except OSError:
            return ""

    def _write(self, text: str) -> None:
        if self.path is None:
            return
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(text, encoding="utf-8")
            self._mark_dirty(False)
            self.toasts.add_toast(Adw.Toast(title=t("board.saved"), timeout=2))
        except OSError:
            pass

    def save(self) -> None:
        """Просим страницу отдать содержимое: она хранит всё, окно — ничего."""
        if self.path is None:
            return
        self.web.evaluate_javascript(
            "Board.dump()", -1, None, None, None, self._got_dump, None)

    def _got_dump(self, web, result, *_):
        try:
            value = web.evaluate_javascript_finish(result)
            self._write(value.to_string())
        except GLib.Error:
            pass

    def open(self, path: Path) -> None:
        self.path = Path(path)
        self.title_widget.set_subtitle(self.path.stem)
        self._mark_dirty(False)
        self._js(f"Board.load({json.dumps(self._read())});")

    def create(self, name: str) -> None:
        clean = name.strip().replace("/", "").replace("\\", "")
        if not clean:
            return
        if not clean.endswith(SUFFIX):
            clean += SUFFIX
        path = self.folder / clean
        if not path.exists():
            path.write_text('{"version":1,"items":[]}', encoding="utf-8")
        self.open(path)

    def fill_list(self) -> None:
        """Список досок — свой, отдельный от списка заметок."""
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        box.set_margin_top(6)
        box.set_margin_bottom(6)
        found = boards_in(self.folder)
        if not found:
            label = Gtk.Label(label=t("board.empty"), margin_start=14, margin_end=14,
                              margin_top=8, margin_bottom=8)
            label.add_css_class("dim-label")
            box.append(label)
        for p in found:
            b = Gtk.Button(label=p.stem, has_frame=False)
            b.get_child().set_xalign(0)
            b.connect("clicked", lambda _b, path=p: (self.list_pop.popdown(), self.open(path)))
            box.append(b)
        self.list_pop.set_child(box)

    # ——— прочее ———

    def _mark_dirty(self, value: bool) -> None:
        self._dirty = value
        self.title_widget.set_title(t("board.title") + (" •" if value else ""))

    def clear(self) -> None:
        dlg = Adw.AlertDialog(heading=t("board.clear"), body=t("board.clearAsk"))
        dlg.add_response("cancel", t("common.cancel"))
        dlg.add_response("ok", t("common.delete"))
        dlg.set_response_appearance("ok", Adw.ResponseAppearance.DESTRUCTIVE)
        dlg.connect("response", lambda _d, r: r == "ok" and self._js("Board.clear();"))
        dlg.present(self)

    def _on_close(self, *_):
        if self._dirty:
            self.save()
        return False
