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
import os
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
gi.require_version("WebKit", "6.0")

from gi.repository import Adw, Gio, GLib, Gtk, WebKit  # noqa: E402

from .i18n import current as i18n_current  # noqa: E402
from .i18n import t  # noqa: E402
# Карточкам нужен SymPy. Если его в системе нет, ломаться должна одна кнопка,
# а не вся программа: читалка, доска и вырезание к нему отношения не имеют.
try:
    from .cards import Card, as_markdown, solve  # noqa: E402
    CARDS_OK = True
except ImportError:  # pragma: no cover — зависит от того, что стоит в системе
    Card = as_markdown = solve = None  # type: ignore[assignment]
    CARDS_OK = False
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
        self._broken = False        # открыт испорченный файл — писать нельзя

        self.set_default_size(1180, 800)
        self.set_size_request(560, 420)
        self.connect("close-request", self._on_close)

        self._build()
        self.set_focus(self.web)
        if path is not None:
            self.open(path)

        # Автосохранение: доска живёт одним файлом, и час рисования терять не на что.
        GLib.timeout_add_seconds(60, self._autosave)

    # ——— окно ———

    def _build(self) -> None:
        view = Adw.ToolbarView()
        head = Adw.HeaderBar()

        self.title_widget = Adw.WindowTitle(title=t("board.title"), subtitle="")
        head.set_title_widget(self.title_widget)

        # «Выбрать доску» стоит здесь же, а не отдельной кнопкой слева: искать
        # её ходят именно в это меню, рядом с «Новая» и «Очистить».
        menu = Gio.Menu()
        menu.append(t("board.pick"), "win.board-pick")
        menu.append(t("board.new"), "win.board-new")
        menu.append(t("board.clear"), "win.board-clear")
        menu.append(t("board.png"), "win.board-png")
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

    # ——— поиск и картинка ———

    def find(self) -> None:
        """Через месяц на доске тридцать бумажек, и глазами уже не ищется."""
        dlg = Adw.AlertDialog(heading=t("board.find"))
        entry = Gtk.Entry(placeholder_text=t("board.find"))
        dlg.set_extra_child(entry)
        dlg.add_response("cancel", t("common.cancel"))
        dlg.add_response("ok", t("board.find"))
        dlg.set_default_response("ok")

        def done(_d, answer):
            if answer != "ok":
                return
            needle = entry.get_text().strip()
            if not needle:
                return

            def got(web, res, *_):
                try:
                    n = int(web.evaluate_javascript_finish(res).to_string() or 0)
                except (GLib.Error, ValueError, AttributeError):
                    return
                self.toasts.add_toast(Adw.Toast(
                    title=t("board.found", n) if n else t("board.nothing")))

            self.web.evaluate_javascript(
                f"Board.find({json.dumps(needle)})", -1, None, None, None, got, None)

        dlg.connect("response", done)
        dlg.present(self)

    def save_png(self) -> None:
        """
        Картинка доски.

        Рисовать самим по холсту нельзя: карточки и бумажки живут разметкой
        поверх него, и в картинку попадало бы всё, кроме самого ценного —
        решений. Поэтому снимаем саму страницу целиком, её же движком: он
        рисует и холст, и разметку разом.

        Перед снимком вписываем доску в окно, иначе в кадр попадёт только то,
        что видно сейчас.
        """
        def after_fit(*_):
            def got(view, res, *_):
                try:
                    texture = view.get_snapshot_finish(res)
                except GLib.Error as e:
                    self._js("Board.forShot(false);")
                    self.toasts.add_toast(Adw.Toast(title=t("board.saveFailed", e.message)))
                    return
                self._js("Board.forShot(false);")
                name = (self.path.stem if self.path else t("board.title")) + ".png"
                out = (self.path.parent if self.path else self.folder) / name
                try:
                    texture.save_to_png(str(out))
                    self.toasts.add_toast(Adw.Toast(title=t("board.pngSaved", name), timeout=6))
                except (GLib.Error, OSError) as e:
                    self.toasts.add_toast(Adw.Toast(title=t("board.saveFailed", str(e))))

            self.web.get_snapshot(WebKit.SnapshotRegion.FULL_DOCUMENT,
                                  WebKit.SnapshotOptions.NONE, None, got)
            return False

        self._js("Board.forShot(true); Board.fitAll();")
        GLib.timeout_add(450, after_fit)

    # ——— карточки-скрипты ———

    @property
    def _catalog(self) -> dict:
        if not CARDS_OK:
            return {"version": 1, "sections": [], "items": []}
        if getattr(self, "_cat", None) is None:
            self._cat = cards_catalog()
            self._cards = {c["id"]: Card.of(c) for c in self._cat.get("items", [])}
        return self._cat

    def open_picker(self) -> None:
        """Выбор формулы. Окно одно: второй раз — поднимаем прежнее."""
        from .picker import PickerWindow

        if not CARDS_OK:
            self.toasts.add_toast(Adw.Toast(title=t("card.needs")))
            return

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

    def _write(self, text: str, quiet: bool = False) -> None:
        """
        Запись через временный файл и переименование.

        Прямая запись сначала обрезает файл до нуля и лишь потом наполняет.
        Убили программу или кончилось место в этот миг — на диске остаётся
        обрубок, который в следующий раз не разберётся. Переименование в
        пределах одного диска атомарно: на месте либо старый файл целиком,
        либо новый целиком, третьего не бывает.

        Ошибку записи молчать нельзя: человек нажал «Сохранить», ничего не
        случилось, и он ушёл спокойный, а работа осталась только в окне.
        """
        if self.path is None:
            return
        tmp = self.path.with_name(self.path.name + ".пишется")
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with open(tmp, "w", encoding="utf-8") as f:
                f.write(text)
                f.flush()
                os.fsync(f.fileno())
            self._saving_now = True
            os.replace(tmp, self.path)
            GLib.timeout_add(1200, lambda: (setattr(self, "_saving_now", False), False)[1])
            self._mark_dirty(False)
            if not quiet:
                self.toasts.add_toast(Adw.Toast(title=t("board.saved"), timeout=2))
        except OSError as e:
            tmp.unlink(missing_ok=True)
            self.toasts.add_toast(Adw.Toast(title=t("board.saveFailed", e.strerror or "")))

    def save(self, quiet: bool = False) -> None:
        """Просим страницу отдать содержимое: она хранит всё, окно — ничего."""
        if self.path is None or self._broken:
            return
        self.web.evaluate_javascript(
            "Board.dump()", -1, None, None, None, self._got_dump, quiet)

    def _got_dump(self, web, result, quiet=False):
        try:
            value = web.evaluate_javascript_finish(result)
            self._write(value.to_string(), quiet=bool(quiet))
        except GLib.Error:
            pass

    def _autosave(self) -> bool:
        """Раз в минуту, тихо. Доска — один файл, и терять его не на что."""
        if self.path is not None and self._dirty and not self._broken:
            self.save(quiet=True)
        return True

    def _watch(self) -> None:
        """
        Следим за своим файлом. У читалки слежение есть с самого начала, у
        доски не было: правку `.board` снаружи затирало следующим сохранением.
        """
        old = getattr(self, "_monitor", None)
        if old is not None:
            old.cancel()
        self._monitor = None
        if self.path is None:
            return
        try:
            mon = Gio.File.new_for_path(str(self.path)).monitor_file(
                Gio.FileMonitorFlags.NONE, None)
        except GLib.Error:
            return
        mon.connect("changed", self._file_changed)
        self._monitor = mon

    def _file_changed(self, _m, _f, _o, event) -> None:
        if event != Gio.FileMonitorEvent.CHANGES_DONE_HINT or self.path is None:
            return
        if getattr(self, "_saving_now", False):
            return
        toast = Adw.Toast(title=t("board.outside"), timeout=10)
        toast.set_button_label(t("board.reload"))
        toast.connect("button-clicked", lambda *_: self.open(self.path))
        self.toasts.add_toast(toast)

    def open(self, path: Path) -> None:
        """
        Испорченный файл не открывается молча.

        Раньше неразобранный файл давал пустую доску, человек видел чистый
        лист, закрывал окно — и пустышка ложилась поверх работы. Теперь такой
        файл откладывается в сторону под своим именем, а доска запирается:
        сохранять поверх нечего и незачем.
        """
        path = Path(path)
        text = ""
        self._broken = False
        try:
            text = path.read_text(encoding="utf-8")
            if text.strip():
                json.loads(text)
        except OSError as e:
            self._broken = True
            self.toasts.add_toast(Adw.Toast(title=t("board.readFailed", e.strerror or "")))
        except ValueError:
            self._broken = True
            spare = path.with_name(path.name + ".битый")
            try:
                os.replace(path, spare)
            except OSError:
                spare = path
            self.toasts.add_toast(Adw.Toast(title=t("board.brokenFile", spare.name),
                                            timeout=12))

        self.path = None if self._broken else path
        self.title_widget.set_subtitle(path.stem + ("  —  " + t("board.broken")
                                                    if self._broken else ""))
        self._mark_dirty(False)
        self._js(f"Board.load({json.dumps('' if self._broken else text)});")
        self._watch()

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
        """
        Молча сохранять при закрытии нельзя: это лишает человека права
        передумать. Спрашиваем — и «Отмена» действительно отменяет закрытие.
        """
        if not self._dirty or self.path is None or self._broken:
            return False
        if getattr(self, "_leaving", False):
            return False

        dlg = Adw.AlertDialog(heading=t("board.closeAsk"),
                              body=self.path.stem if self.path else "")
        dlg.add_response("cancel", t("common.cancel"))
        dlg.add_response("no", t("board.dontSave"))
        dlg.add_response("yes", t("edit.save"))
        dlg.set_response_appearance("no", Adw.ResponseAppearance.DESTRUCTIVE)
        dlg.set_response_appearance("yes", Adw.ResponseAppearance.SUGGESTED)
        dlg.set_default_response("yes")
        dlg.set_close_response("cancel")

        def answer(_d, r):
            if r == "cancel":
                return
            self._leaving = True
            if r == "yes":
                # сохраняем и закрываемся уже после записи, а не до неё
                self.save()
                GLib.timeout_add(350, lambda: (self.close(), False)[1])
            else:
                self.close()

        dlg.connect("response", answer)
        dlg.present(self)
        return True                      # закрытие придержано до ответа
