"""
Окно настольной версии.

Разметку и формулы рисует та же самая страница, что и на телефоне
(`shared/reader/`). Здесь — список файлов, поиск, слежение за папкой,
клавиатура и печать, то есть всё, чего на телефоне быть не может.
"""

from __future__ import annotations

import json
import math
import threading
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
gi.require_version("WebKit", "6.0")

from gi.repository import Adw, Gdk, Gio, GLib, Gtk, WebKit  # noqa: E402

from . import md_items as md  # noqa: E402
from .files import Entry, FilesRepo  # noqa: E402
from .i18n import subtitle, sync_message, t  # noqa: E402
from . import reminders as rem  # noqa: E402
from .stats import record  # noqa: E402
from .sync import FROZEN, GitHub, Sync  # noqa: E402
from .paths import prompt_text, reader_html, stamped  # noqa: E402
from .settings import Settings  # noqa: E402

ACCENT = (0.482, 0.231, 1.000)      # #7B3BFF
ACCENT2 = (0.635, 0.420, 1.000)     # #A26BFF
DEEP = (0.357, 0.094, 0.863)        # #5B18DC

# Оформление «Слои»: у всего, на что нажимают, есть высота. Свет падает
# сверху, поэтому светлая грань — по верхнему краю, тень — под низом.
# Содержимое (текст, формулы) остаётся плоской бумагой: тени под абзацами
# убили бы чтение, ради которого программа и написана.
CSS = """
.mathmark-title { font-weight: 700; }
.mathmark-dim { opacity: 0.62; font-size: 0.86em; }
.mathmark-hit { font-family: monospace; font-size: 0.82em; opacity: 0.7; }

.mathmark-progress trough { min-height: 4px; border-radius: 3px; }
.mathmark-progress progress {
  min-height: 4px; border-radius: 3px;
  background: linear-gradient(90deg, #7B3BFF, #A26BFF);
}

/* строка списка — плитка, которая поднимается под курсором */
row.mathmark-row {
  padding: 8px 6px;
  margin: 3px 6px;
  border-radius: 13px;
  transition: background 140ms ease, box-shadow 140ms ease;
}
row.mathmark-row:hover {
  background: alpha(@window_fg_color, 0.045);
  box-shadow: 0 6px 16px -8px alpha(@window_fg_color, 0.55);
}
row.mathmark-row:selected {
  background: alpha(#7B3BFF, 0.14);
  box-shadow: inset 0 1px 0 alpha(#ffffff, 0.5), 0 8px 18px -10px alpha(#3A0D9E, 0.8);
}

/* кнопка доски — приподнятая, с бликом сверху */
.mathmark-board {
  background: linear-gradient(160deg, #A26BFF, #7B3BFF);
  color: #ffffff;
  font-weight: 600;
  border: none;
  border-radius: 12px;
  padding: 5px 14px;
  box-shadow: inset 0 1px 0 alpha(#ffffff, 0.42),
              0 5px 12px -5px alpha(#4A11C8, 0.85);
}
.mathmark-board:hover { background: linear-gradient(160deg, #B27FFF, #8B4DFF); }
.mathmark-board:active {
  background: linear-gradient(160deg, #7B3BFF, #6A22F0);
  box-shadow: inset 0 2px 5px alpha(#2E0A74, 0.5);
}

/* кружки выбора цвета на доске и в вырезании — те же плитки, только круглые */
button.mm-dot {
  box-shadow: inset 0 1px 0 alpha(#ffffff, 0.5),
              0 2px 6px -2px alpha(#1C1230, 0.6);
}
""".encode()


# ——————————————————————— значки ———————————————————————

def _rounded(cr, x, y, w, h, r):
    cr.new_sub_path()
    cr.arc(x + w - r, y + r, r, -math.pi / 2, 0)
    cr.arc(x + w - r, y + h - r, r, 0, math.pi / 2)
    cr.arc(x + r, y + h - r, r, math.pi / 2, math.pi)
    cr.arc(x + r, y + r, r, math.pi, 3 * math.pi / 2)
    cr.close_path()


def draw_glyph(area, cr, width, height, kind):
    """
    Значок строки: квадрат — задачник, круг — темы, квадрат с кругом —
    смешанный, закладка — справочник, папка — папка. Те же, что на телефоне.
    """
    s = min(width, height)
    deeper = kind in ("plain", "folder")
    grad = __import__("cairo").LinearGradient(0, 0, s, s)
    if deeper:
        grad.add_color_stop_rgb(0, *ACCENT)
        grad.add_color_stop_rgb(1, *DEEP)
    else:
        grad.add_color_stop_rgb(0, *ACCENT2)
        grad.add_color_stop_rgb(1, *ACCENT)
    _rounded(cr, 0, 0, s, s, s * 0.30)
    cr.set_source(grad)
    cr.fill()

    cr.set_source_rgb(1, 1, 1)
    cr.set_line_cap(1)
    cr.set_line_join(1)
    c = s / 2

    def check(cx, cy, w, lw):
        cr.set_line_width(lw)
        cr.move_to(cx - w * 0.5, cy + w * 0.04)
        cr.line_to(cx - w * 0.12, cy + w * 0.42)
        cr.line_to(cx + w * 0.55, cy - w * 0.42)
        cr.stroke()

    if kind == "tasks":
        cr.set_line_width(s * 0.075)
        _rounded(cr, c - s * 0.22, c - s * 0.22, s * 0.44, s * 0.44, s * 0.10)
        cr.stroke()
        check(c, c, s * 0.26, s * 0.085)
    elif kind == "topics":
        cr.set_line_width(s * 0.075)
        cr.arc(c, c, s * 0.23, 0, 2 * math.pi)
        cr.stroke()
        check(c, c, s * 0.24, s * 0.085)
    elif kind == "both":
        cr.set_line_width(s * 0.07)
        _rounded(cr, s * 0.40 - s * 0.19, s * 0.40 - s * 0.19, s * 0.38, s * 0.38, s * 0.09)
        cr.stroke()
        cr.arc(s * 0.62, s * 0.62, s * 0.20, 0, 2 * math.pi)
        cr.stroke()
    elif kind == "folder":
        cr.set_line_width(s * 0.075)
        cr.move_to(s * 0.24, s * 0.68)
        cr.line_to(s * 0.24, s * 0.34)
        cr.line_to(s * 0.44, s * 0.34)
        cr.line_to(s * 0.51, s * 0.42)
        cr.line_to(s * 0.76, s * 0.42)
        cr.line_to(s * 0.76, s * 0.68)
        cr.close_path()
        cr.stroke()
    else:  # plain — закладка
        cr.set_line_width(s * 0.075)
        cr.move_to(s * 0.34, s * 0.26)
        cr.line_to(s * 0.66, s * 0.26)
        cr.line_to(s * 0.66, s * 0.74)
        cr.line_to(s * 0.50, s * 0.60)
        cr.line_to(s * 0.34, s * 0.74)
        cr.close_path()
        cr.stroke()


def glyph_widget(kind: str, size: int = 34) -> Gtk.DrawingArea:
    area = Gtk.DrawingArea()
    area.set_content_width(size)
    area.set_content_height(size)
    area.set_valign(Gtk.Align.CENTER)
    area.set_draw_func(draw_glyph, kind)
    return area


# ——————————————————————— окно ———————————————————————

class MathMarkWindow(Adw.ApplicationWindow):
    def __init__(self, app: Adw.Application, settings: Settings):
        super().__init__(application=app, title=t("app.name"))
        self.st = settings
        self.repo = FilesRepo(self.st.folder)
        self.repo.create_root()

        self.current: Path | None = None
        self.text: str = ""
        self.toc: list[tuple[str, str]] = []
        self._writing: set[str] = set()   # свои записи, чтобы не перечитывать самих себя
        self._syncing = False
        self._editing = False
        self._monitors: list[Gio.FileMonitor] = []

        self.set_default_size(self.st.width, self.st.height)
        self.set_size_request(480, 420)
        self.connect("close-request", self._on_close)

        self._fired: set[str] = set()
        self._build()
        self._apply_theme()
        self.refresh()

        # напоминания проверяются раз в минуту, пока окно открыто.
        # Закрытая программа ничего не покажет — на компьютере это честнее,
        # чем держать службу ради двух строк.
        GLib.timeout_add_seconds(60, self._reminder_tick)

    # ——— сборка окна ———

    def _build(self) -> None:
        self.toasts = Adw.ToastOverlay()
        self.split = Adw.OverlaySplitView(
            sidebar_width_fraction=0.30,
            min_sidebar_width=260,
            max_sidebar_width=380,
            show_sidebar=self.st.sidebar,
        )
        self.toasts.set_child(self.split)
        self.set_content(self.toasts)

        # узкое окно — боковая панель уезжает поверх, а не жмёт текст
        bp = Adw.Breakpoint.new(Adw.BreakpointCondition.parse("max-width: 760sp"))
        bp.add_setter(self.split, "collapsed", True)
        self.add_breakpoint(bp)

        self.split.set_sidebar(self._sidebar())
        self.split.set_content(self._content())

    def _sidebar(self) -> Gtk.Widget:
        view = Adw.ToolbarView()

        head = Adw.HeaderBar(show_end_title_buttons=False)
        self.title_widget = Adw.WindowTitle(title=t("app.name"), subtitle=str(self.repo.root))
        head.set_title_widget(self.title_widget)

        self.up_btn = Gtk.Button(icon_name="go-previous-symbolic", tooltip_text=t("desk.upOneLevel"))
        self.up_btn.connect("clicked", lambda *_: (self.repo.up(), self.refresh()))
        self.up_btn.set_visible(False)
        head.pack_start(self.up_btn)

        menu = Gio.Menu()
        menu.append(t("edit.new"), "win.new-file")
        menu.append(t("list.newFolder"), "win.new-folder")
        menu.append(t("desk.refresh"), "win.refresh")
        menu.append(t("settings.copyPrompt"), "win.copy-prompt")
        menu.append(t("rem.today"), "win.today")
        menu.append(t("stats.title"), "win.stats")
        menu.append(t("settings.title"), "win.settings")
        menu.append(t("desk.shortcuts"), "win.shortcuts")
        btn = Gtk.MenuButton(icon_name="open-menu-symbolic", menu_model=menu)
        head.pack_end(btn)
        view.add_top_bar(head)

        self.search = Gtk.SearchEntry(placeholder_text=t("list.searchHint"))
        self.search.set_margin_start(8)
        self.search.set_margin_end(8)
        self.search.set_margin_bottom(6)
        self.search.connect("search-changed", lambda *_: self.refresh())
        self.search.connect("stop-search", lambda *_: self.search.set_text(""))

        self.listbox = Gtk.ListBox(selection_mode=Gtk.SelectionMode.SINGLE)
        self.listbox.add_css_class("navigation-sidebar")
        self.listbox.connect("row-activated", self._on_row)

        scroll = Gtk.ScrolledWindow(vexpand=True, child=self.listbox)
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        box.append(self.search)
        box.append(scroll)
        view.set_content(box)
        return view

    def _content(self) -> Gtk.Widget:
        view = Adw.ToolbarView()
        head = Adw.HeaderBar()

        self.board_btn = Gtk.Button(valign=Gtk.Align.CENTER)
        self.board_btn.set_child(Gtk.Box(spacing=6))
        self.board_btn.get_child().append(Gtk.Image.new_from_icon_name("view-grid-symbolic"))
        self.board_btn.get_child().append(Gtk.Label(label=t("board.open")))
        self.board_btn.add_css_class("mathmark-board")
        self.board_btn.connect("clicked", lambda *_: self.get_application().open_board(self))
        head.pack_end(self.board_btn)

        self.write_btn = Gtk.Button(icon_name="accessories-dictionary-symbolic",
                                    tooltip_text=t("write.title") + "  (Ctrl+M)",
                                    valign=Gtk.Align.CENTER)
        self.write_btn.connect("clicked", lambda *_: self.get_application().open_writer(self))
        head.pack_end(self.write_btn)

        self.toggle = Gtk.ToggleButton(icon_name="sidebar-show-symbolic", tooltip_text=t("desk.fileList"))
        self.toggle.set_active(self.st.sidebar)
        self.toggle.connect("toggled", lambda b: self.split.set_show_sidebar(b.get_active()))
        head.pack_start(self.toggle)

        self.doc_title = Adw.WindowTitle(title=t("app.name"), subtitle=t("desk.chooseFile"))
        head.set_title_widget(self.doc_title)

        self.edit_btn = Gtk.ToggleButton(icon_name="document-edit-symbolic",
                                         tooltip_text=t("edit.title"))
        self.edit_btn.connect("toggled", self._on_edit_toggled)
        self.edit_btn.set_sensitive(False)
        head.pack_end(self.edit_btn)

        self.toc_btn = Gtk.MenuButton(icon_name="view-list-symbolic", tooltip_text=t("doc.sections"))
        self.toc_pop = Gtk.Popover()
        self.toc_btn.set_popover(self.toc_pop)
        self.toc_btn.set_sensitive(False)
        head.pack_end(self.toc_btn)

        prn = Gtk.Button(icon_name="printer-symbolic", tooltip_text=t("desk.print"))
        prn.connect("clicked", lambda *_: self.do_print())
        head.pack_end(prn)

        self.sync_btn = Gtk.Button(icon_name="view-refresh-symbolic",
                                   tooltip_text=t("sync.frozen") if FROZEN else t("sync.button"))
        self.sync_btn.connect("clicked", lambda *_: self.do_sync())
        # кнопка остаётся видимой и нажимаемой: молча погасшая кнопка
        # выглядит поломкой, а нажатие объясняет, что происходит.
        head.pack_end(self.sync_btn)

        view.add_top_bar(head)

        ucm = WebKit.UserContentManager()
        ucm.register_script_message_handler("mathmark", None)
        ucm.connect("script-message-received::mathmark", self._on_message)

        self.web = WebKit.WebView(user_content_manager=ucm, vexpand=True)
        self.web.connect("load-changed", self._on_load)
        page = reader_html()
        self.web.load_html(stamped(page), page.as_uri())
        view.set_content(self.web)
        return view

    # ——— список ———

    def refresh(self) -> None:
        query = self.search.get_text().strip()
        while (row := self.listbox.get_first_child()) is not None:
            self.listbox.remove(row)

        self.up_btn.set_visible(not self.repo.at_root and not query)
        crumbs = self.repo.crumbs()
        self.title_widget.set_title(t("app.name") if self.repo.at_root else self.repo.cwd.name)
        self.title_widget.set_subtitle(
            str(self.repo.root) if self.repo.at_root
            else " / ".join(c.name for c in crumbs)
        )

        if query:
            for path, hit in self.repo.search(query):
                self.listbox.append(self._search_row(path, hit))
        else:
            for entry in self.repo.list():
                self.listbox.append(self._entry_row(entry))
        self._watch()

    def _row_shell(self, glyph: str, title: str, subtitle: str) -> tuple[Gtk.ListBoxRow, Gtk.Box]:
        row = Gtk.ListBoxRow()
        row.add_css_class("mathmark-row")
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        box.set_margin_top(4)
        box.set_margin_bottom(4)
        box.append(glyph_widget(glyph))
        col = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, hexpand=True)
        lbl = Gtk.Label(label=title, xalign=0, ellipsize=3)
        lbl.add_css_class("mathmark-title")
        sub = Gtk.Label(label=subtitle, xalign=0, ellipsize=3)
        sub.add_css_class("mathmark-dim")
        col.append(lbl)
        col.append(sub)
        box.append(col)
        row.set_child(box)
        return row, col

    def _entry_row(self, entry: Entry) -> Gtk.ListBoxRow:
        if entry.is_folder:
            row, _ = self._row_shell("folder", entry.name, t("list.inside", entry.inside))
        else:
            c = md.counts(self.repo.read(entry.path))
            row, col = self._row_shell(c.kind.value, entry.title, subtitle(c))
            if c.kind is not md.FileKind.PLAIN:
                bar = Gtk.ProgressBar(fraction=c.progress)
                bar.add_css_class("mathmark-progress")
                bar.set_margin_top(5)
                col.append(bar)
        row.entry = entry
        self._attach_menu(row, entry)
        return row

    def _search_row(self, path: Path, hit: str) -> Gtk.ListBoxRow:
        c = md.counts(self.repo.read(path))
        rel = path.relative_to(self.repo.root).parent
        where = f"{rel} · " if str(rel) != "." else ""
        row, col = self._row_shell(c.kind.value, path.stem, where + subtitle(c))
        lbl = Gtk.Label(label=hit, xalign=0, ellipsize=3)
        lbl.add_css_class("mathmark-hit")
        col.append(lbl)
        row.entry = Entry(path, False)
        self._attach_menu(row, row.entry)
        return row

    def _on_row(self, _box, row) -> None:
        entry: Entry = row.entry
        if entry.is_folder:
            self.repo.enter(entry.path)
            self.search.set_text("")
            self.refresh()
        else:
            self.open_doc(entry.path)

    # ——— действия над строкой ———

    def _attach_menu(self, row: Gtk.ListBoxRow, entry: Entry) -> None:
        gesture = Gtk.GestureClick(button=3)
        gesture.connect("pressed", lambda *_: self._row_menu(row, entry))
        row.add_controller(gesture)
        long = Gtk.GestureLongPress()
        long.connect("pressed", lambda *_: self._row_menu(row, entry))
        row.add_controller(long)

    def _row_menu(self, row: Gtk.ListBoxRow, entry: Entry) -> None:
        pop = Gtk.Popover(has_arrow=True)
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        box.set_margin_top(6)
        box.set_margin_bottom(6)

        def item(label: str, fn, danger=False):
            b = Gtk.Button(label=label, has_frame=False)
            b.get_child().set_xalign(0)
            if danger:
                b.add_css_class("error")
            b.connect("clicked", lambda *_: (pop.popdown(), fn()))
            box.append(b)

        item(t("list.open"), lambda: self._on_row(None, row))
        item(t("list.rename"), lambda: self._ask_name(
            t("list.renameTitle"), entry.title,
            lambda n: (self.repo.rename(entry, n), self.refresh())))
        if not entry.is_folder:
            item(t("list.move"), lambda: self._ask_move(entry))
        if not entry.is_folder:
            item(t("rem.add"), lambda: self.get_application().reminder_dialog(
                self, str(entry.path.relative_to(self.repo.root))))
        item(t("desk.showInFiles"), lambda: Gio.AppInfo.launch_default_for_uri(
            entry.path.parent.as_uri(), None))
        item(t("common.delete"), lambda: self._ask_delete(entry), danger=True)

        pop.set_child(box)
        pop.set_parent(row)
        pop.popup()

    def _ask_name(self, title: str, initial: str, done) -> None:
        dlg = Adw.AlertDialog(heading=title)
        entry = Gtk.Entry(text=initial)
        dlg.set_extra_child(entry)
        dlg.add_response("cancel", t("common.cancel"))
        dlg.add_response("ok", t("common.done"))
        dlg.set_default_response("ok")
        dlg.set_response_appearance("ok", Adw.ResponseAppearance.SUGGESTED)
        dlg.connect("response", lambda _d, r: r == "ok" and done(entry.get_text()))
        dlg.present(self)

    def _ask_delete(self, entry: Entry) -> None:
        what = (t("list.deleteFolder", entry.name) if entry.is_folder
                else t("list.deleteFile", entry.name))
        dlg = Adw.AlertDialog(heading=t("list.deleteQ"), body=what)
        dlg.add_response("cancel", t("common.cancel"))
        dlg.add_response("del", t("common.delete"))
        dlg.set_response_appearance("del", Adw.ResponseAppearance.DESTRUCTIVE)

        def resp(_d, r):
            if r == "del":
                self.repo.delete(entry)
                if self.current == entry.path:
                    self.current = None
                    self.text = ""
                    self._render()
                self.refresh()

        dlg.connect("response", resp)
        dlg.present(self)

    def _ask_move(self, entry: Entry) -> None:
        targets = [self.repo.root] + self.repo.all_folders()
        dlg = Adw.AlertDialog(heading=t("list.moveTo", entry.title))
        lst = Gtk.ListBox(selection_mode=Gtk.SelectionMode.SINGLE)
        for target in targets:
            rel = (t("list.moveRoot") if target == self.repo.root
                   else str(target.relative_to(self.repo.root)))
            r = Gtk.ListBoxRow(child=Gtk.Label(label=rel, xalign=0, margin_top=6, margin_bottom=6,
                                               margin_start=8, margin_end=8))
            r.target = target
            lst.append(r)
        scroll = Gtk.ScrolledWindow(child=lst, min_content_height=220, propagate_natural_height=True)
        dlg.set_extra_child(scroll)
        dlg.add_response("cancel", t("common.cancel"))
        dlg.add_response("ok", t("desk.move"))
        dlg.set_default_response("ok")

        def resp(_d, r):
            row = lst.get_selected_row()
            if r == "ok" and row is not None:
                self.repo.move(entry, row.target)
                self.refresh()

        dlg.connect("response", resp)
        dlg.present(self)

    # ——— документ ———

    def open_doc(self, path: Path) -> None:
        self.current = Path(path)
        self.text = self.repo.read(self.current)
        c = md.counts(self.text)
        self.doc_title.set_title(self.current.stem)
        self.doc_title.set_subtitle(subtitle(c))
        self._render()
        self.edit_btn.set_sensitive(True)
        if self.split.get_collapsed():
            self.split.set_show_sidebar(False)

    def _on_load(self, _web, event) -> None:
        if event == WebKit.LoadEvent.FINISHED:
            self._render()

    def _js(self, script: str) -> None:
        self.web.evaluate_javascript(script, -1, None, None, None, None, None)

    def _render(self) -> None:
        dark = Adw.StyleManager.get_default().get_dark()
        self._js(
            f"MathMark.setLabels({json.dumps({'empty': t('doc.empty')})});"
            f"MathMark.setTheme({str(dark).lower()});MathMark.setScale({self.st.scale:g});"
        )
        if self.current is None:
            self._js("MathMark.render('');")
            self.toc_btn.set_sensitive(False)
            return
        self._js(f"MathMark.render({json.dumps(self.text)});")

    def _edit_labels(self) -> str:
        keys = ("edit.save", "edit.cancel", "edit.task", "edit.topic", "edit.hidden",
                "edit.formula", "edit.matrix", "edit.heading", "edit.plot",
                "edit.problems", "edit.clean", "edit.matrixSize")
        return json.dumps({k: t(k) for k in keys})

    def _on_edit_toggled(self, btn) -> None:
        if btn.get_active():
            if self.current is None:
                btn.set_active(False)
                return
            self._editing = True
            self._js(f"MathMarkEdit.setLabels({self._edit_labels()});"
                     f"MathMarkEdit.open({json.dumps(self.text)});")
        else:
            self._editing = False
            self._js("MathMarkEdit.close();")

    def _save_edited(self, fresh: str) -> None:
        """Сохраняем ровно то, что набрано. Чужие правки молча не затираем."""
        on_disk = self.repo.read(self.current)
        if on_disk != self.text:
            dlg = Adw.AlertDialog(heading=t("edit.title"), body=t("edit.changedOutside"))
            dlg.add_response("cancel", t("common.cancel"))
            dlg.add_response("save", t("edit.save"))
            dlg.set_response_appearance("save", Adw.ResponseAppearance.DESTRUCTIVE)
            dlg.connect("response", lambda _d, r: r == "save" and self._write_edited(fresh))
            dlg.present(self)
            return
        self._write_edited(fresh)

    def _write_edited(self, fresh: str) -> None:
        self._writing.add(str(self.current))
        if self.repo.write(self.current, fresh):
            self.text = fresh
            self._editing = False
            self.edit_btn.set_active(False)
            self._js(f"MathMarkEdit.close();MathMark.render({json.dumps(fresh)});")
            self.doc_title.set_subtitle(subtitle(md.counts(fresh)))
            self.toast(t("edit.saved"))
            self.refresh()
        GLib.timeout_add(700, lambda: self._writing.discard(str(self.current)) or False)

    def _on_message(self, _ucm, value) -> None:
        try:
            data = json.loads(value.to_string())
        except (ValueError, AttributeError):
            return
        name, payload = data.get("name"), data.get("payload")

        if name == "onEditSave" and self.current is not None:
            self._save_edited(payload)
            return
        if name == "onEditCancel":
            self._editing = False
            self.edit_btn.set_active(False)
            self._js("MathMarkEdit.close();")
            return

        if name == "onToc":
            self.toc = [(h["id"], h["txt"]) for h in json.loads(payload)]
            self._fill_toc()
        elif name == "onCycle" and self.current is not None:
            self._cycle(int(payload))

    def _cycle(self, offset: int) -> None:
        try:
            updated = md.cycle(self.text, offset)
        except ValueError:
            return
        self._writing.add(str(self.current))
        if self.repo.write(self.current, updated):
            self.text = updated
            new_mark = md.Mark.of(updated[offset])
            self._js(f"MathMark.setMark({offset},'{new_mark.name.lower()}');")
            # журнал помнит, КОГДА отмечено — в самом файле этого нет
            item = next((i for i in md.items(updated) if i.box_offset == offset), None)
            if item is not None:
                record(self.st.file.parent / "journal.log",
                       self.current.name, item.kind, new_mark)
            c = md.counts(self.text)
            self.doc_title.set_subtitle(subtitle(c))
            self.refresh()
        GLib.timeout_add(700, lambda: self._writing.discard(str(self.current)) or False)

    def _fill_toc(self) -> None:
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        box.set_margin_top(6)
        box.set_margin_bottom(6)
        for hid, label in self.toc:
            b = Gtk.Button(label=label, has_frame=False)
            b.get_child().set_xalign(0)
            b.connect("clicked", lambda _b, i=hid: (self.toc_pop.popdown(),
                                                    self._js(f"MathMark.goto('{i}');")))
            box.append(b)
        scroll = Gtk.ScrolledWindow(child=box, max_content_height=420,
                                    propagate_natural_height=True)
        self.toc_pop.set_child(scroll)
        self.toc_btn.set_sensitive(bool(self.toc))

    # ——— слежение за папкой ———

    def _watch(self) -> None:
        for m in self._monitors:
            m.cancel()
        self._monitors.clear()
        try:
            mon = Gio.File.new_for_path(str(self.repo.cwd)).monitor_directory(
                Gio.FileMonitorFlags.WATCH_MOVES, None)
            mon.connect("changed", self._on_folder_change)
            self._monitors.append(mon)
        except GLib.Error:
            pass

    def _on_folder_change(self, _mon, file, _other, _event) -> None:
        path = file.get_path() or ""
        if path in self._writing:
            return                       # это наша собственная запись
        if self.current is not None and path == str(self.current):
            fresh = self.repo.read(self.current)
            if fresh != self.text:
                self.text = fresh
                self._render()           # файл поменяли снаружи — показываем новое
        GLib.timeout_add(120, lambda: (self.refresh(), False)[1])

    # ——— прочее ———

    @property
    def reminders_file(self) -> Path:
        return self.st.file.parent / "reminders.conf"

    def _reminder_tick(self) -> bool:
        from datetime import datetime

        now = datetime.now()
        for r in rem.for_day(rem.load(self.reminders_file), now.date()):
            key = f"{r.path}|{now.date()}|{r.at:%H:%M}"
            if key in self._fired:
                continue
            if (now.hour, now.minute) >= (r.at.hour, r.at.minute):
                self._fired.add(key)
                self._notify(r)
        return True                      # продолжать проверять

    def _notify(self, r) -> None:
        note = Gio.Notification.new(r.text or t("rem.title"))
        note.set_body(r.path.removesuffix(".md"))
        note.set_default_action_and_target_value(
            "app.open-file", GLib.Variant.new_string(str(self.repo.root / r.path))
        )
        app = self.get_application()
        if app is not None:
            app.send_notification(f"rem-{r.path}", note)

    def new_file(self, name: str) -> None:
        """Создать пустой файл и сразу открыть его на правку."""
        clean = name.strip()
        if not clean:
            return
        if not clean.lower().endswith(".md"):
            clean += ".md"
        path = self.repo.cwd / clean
        if path.exists():
            self.toast(clean)
            return
        if self.repo.write(path, "# " + clean[:-3] + "\n\n"):
            self.refresh()
            self.open_doc(path)
            self.edit_btn.set_active(True)

    def do_sync(self) -> None:
        """
        Синхронизация идёт в отдельной нити — иначе окно замирает на время
        обращения к сети. Обратно в окно возвращаемся через GLib.idle_add,
        трогать виджеты из чужой нити нельзя.
        """
        if FROZEN:
            self.toast(t("sync.frozen"))
            return
        if self._syncing:
            return
        if not self.st.sync_ready:
            self.toast(t("sync.notSet"))
            return
        self._syncing = True
        self.sync_btn.set_sensitive(False)
        self.toast(t("sync.running"))

        def work():
            report = Sync(
                folder=Path(self.st.folder),
                state_dir=self.st.file.parent,
                gh=GitHub(self.st.sync_repo, self.st.sync_token),
                device="компьютер",
            ).run()
            GLib.idle_add(done, report)

        def done(report):
            self._syncing = False
            self.sync_btn.set_sensitive(True)
            self.toast(sync_message(report))
            self.refresh()
            if self.current is not None:
                fresh = self.repo.read(self.current)
                if fresh != self.text:
                    self.text = fresh
                    self._render()
            return False

        threading.Thread(target=work, daemon=True).start()

    def do_print(self) -> None:
        op = WebKit.PrintOperation(web_view=self.web)
        op.run_dialog(self)

    def set_scale(self, value: float) -> None:
        self.st.scale = min(1.6, max(0.8, value))
        self.st.save()
        self._js(f"MathMark.setScale({self.st.scale:g});")

    def _apply_theme(self) -> None:
        sm = Adw.StyleManager.get_default()
        sm.set_color_scheme({
            "light": Adw.ColorScheme.FORCE_LIGHT,
            "dark": Adw.ColorScheme.FORCE_DARK,
        }.get(self.st.theme, Adw.ColorScheme.DEFAULT))
        sm.connect("notify::dark", lambda *_: self._render())

    def set_folder(self, path: str) -> None:
        self.st.folder = path
        self.st.save()
        self.repo = FilesRepo(path)
        self.repo.create_root()
        self.current = None
        self.text = ""
        self.doc_title.set_title(t("app.name"))
        self.doc_title.set_subtitle(t("desk.chooseFile"))
        self._render()
        self.refresh()

    def relabel(self) -> None:
        """Переписать надписи после смены языка, не перезапуская программу."""
        self.search.set_placeholder_text(t("list.searchHint"))
        if self.current is None:
            self.doc_title.set_title(t("app.name"))
            self.doc_title.set_subtitle(t("desk.chooseFile"))
        else:
            self.doc_title.set_subtitle(subtitle(md.counts(self.text)))
        self.refresh()

    def toast(self, message: str) -> None:
        self.toasts.add_toast(Adw.Toast(title=message, timeout=2))

    def copy_prompt(self) -> None:
        Gdk.Display.get_default().get_clipboard().set(prompt_text())
        self.toast(t("toast.promptCopied"))

    def _on_close(self, *_):
        w, h = self.get_default_size()
        self.st.width, self.st.height = w, h
        self.st.sidebar = self.split.get_show_sidebar()
        self.st.save()
        return False
