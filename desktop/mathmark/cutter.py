"""
Окно вырезания: взять кусок конспекта и повесить его на доску.

Одно окно, два входа — так решено нарочно, чтобы не заводить две почти
одинаковые штуки, которые придётся чинить по отдельности:

* кнопка «Вырезать» на доске открывает его на списке папок и файлов;
* кнопка «Показать источник» на бумажке открывает его сразу на нужном файле
  и списка не показывает вовсе — окно отвечает на вопрос «откуда это
  взялось», а не служит проводником.

Выделять человек будет в нарисованной странице, а на доску ляжет исходный
markdown: разбором занимается `MathMark.cut` в общей странице чтения.
"""

from __future__ import annotations

import json
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
gi.require_version("WebKit", "6.0")

from gi.repository import Adw, GLib, Gtk, WebKit  # noqa: E402

from .files import Entry, FilesRepo  # noqa: E402
from .i18n import t  # noqa: E402
from .paths import reader_html  # noqa: E402

# Те же цвета, что на доске. Бумажка не заливается ими в лоб: насыщенный
# красный лист с текстом читать невозможно, поэтому цвет живёт в подложке
# и в полосе по краю, а текст остаётся тёмным.
COLORS: list[tuple[str, str]] = [
    ("blue", "#2563EB"),
    ("violet", "#7C3AED"),
    ("green", "#0F9D58"),
    ("amber", "#B4690E"),
    ("red", "#DC2626"),
    ("slate", "#334155"),
]


class CutWindow(Adw.ApplicationWindow):
    """Список файлов слева, нарисованный файл справа, «Вытащить» внизу."""

    def __init__(self, app, settings, folder: Path, on_cut,
                 path: Path | None = None, text: str | None = None,
                 heading: str = "") -> None:
        super().__init__(application=app, title=t("cut.title"))
        self.st = settings
        self.repo = FilesRepo(folder)
        self.on_cut = on_cut
        # Третий вход: показать готовый кусок, у которого файла нет вовсе —
        # так открывается формула решённой карточки. Список тоже не нужен.
        self.given = text
        self.source_mode = path is not None or text is not None
        self.current: Path | None = None
        self.color = "blue"
        self._ready = False

        self.set_default_size(1040, 760)
        self.set_size_request(520, 420)

        self._build()

        # Выделил — и сразу Ctrl+Enter, не отрывая рук от текста.
        keys = Gtk.EventControllerKey()
        keys.connect("key-pressed", self._on_key)
        self.add_controller(keys)

        if self.given is not None:
            self.set_title(heading or t("cut.source"))
            self.title_widget.set_title(heading or t("cut.source"))
            self.title_widget.set_subtitle("")
            self._show(self.given)
        elif self.source_mode:
            self.set_title(t("cut.source"))
            self.open(path)
        else:
            self.refresh()
            # Открылось — сразу можно ходить стрелками по списку, без мыши.
            self._focus_list()

    # ——— сборка ———

    def _build(self) -> None:
        self.toasts = Adw.ToastOverlay()
        view = Adw.ToolbarView()

        head = Adw.HeaderBar()
        self.title_widget = Adw.WindowTitle(
            title=t("cut.source") if self.source_mode else t("cut.title"), subtitle="")
        head.set_title_widget(self.title_widget)

        if not self.source_mode:
            self.back_btn = Gtk.Button(icon_name="go-previous-symbolic",
                                       tooltip_text=t("cut.back"))
            self.back_btn.connect("clicked", lambda *_: self._go_up())
            head.pack_start(self.back_btn)

        view.add_top_bar(head)

        ucm = WebKit.UserContentManager()
        ucm.register_script_message_handler("mathmark", None)
        ucm.connect("script-message-received::mathmark", self._from_page)
        self.web = WebKit.WebView(user_content_manager=ucm, vexpand=True, hexpand=True)
        self.web.connect("load-changed", self._on_load)
        self.web.load_uri(reader_html().as_uri())

        if self.source_mode:
            body: Gtk.Widget = self.web
        else:
            self.split = Adw.OverlaySplitView(
                sidebar_width_fraction=0.30, min_sidebar_width=240, max_sidebar_width=360)
            self.split.set_content(self.web)
            self.split.set_sidebar(self._sidebar())
            body = self.split

        view.set_content(body)
        view.add_bottom_bar(self._bottom())
        self.toasts.set_child(view)
        self.set_content(self.toasts)

    def _sidebar(self) -> Gtk.Widget:
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.listbox = Gtk.ListBox(selection_mode=Gtk.SelectionMode.SINGLE)
        self.listbox.add_css_class("navigation-sidebar")
        self.listbox.connect("row-activated", self._row_activated)
        scroll = Gtk.ScrolledWindow(vexpand=True, child=self.listbox)
        box.append(scroll)
        return box

    def _bottom(self) -> Gtk.Widget:
        bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        bar.set_margin_top(8)
        bar.set_margin_bottom(8)
        bar.set_margin_start(12)
        bar.set_margin_end(12)

        hint = Gtk.Label(label=t("cut.hint"), xalign=0, hexpand=True, wrap=True)
        hint.add_css_class("dim-label")
        bar.append(hint)

        self._dots: dict[str, Gtk.Button] = {}
        dots = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        for name, hexv in COLORS:
            btn = Gtk.Button(valign=Gtk.Align.CENTER, tooltip_text=t("cut.color"))
            btn.set_size_request(22, 22)
            btn.add_css_class("mm-dot")
            btn.set_name("mm-dot-" + name)
            btn.connect("clicked", lambda _b, n=name: self._pick(n))
            self._dots[name] = btn
            dots.append(btn)
            self._paint_dot(btn, hexv, name == self.color)
        bar.append(dots)

        self.take_btn = Gtk.Button(label=t("cut.take") + "  (Ctrl+Enter)",
                                   valign=Gtk.Align.CENTER)
        self.take_btn.add_css_class("suggested-action")
        self.take_btn.set_sensitive(False)
        self.take_btn.connect("clicked", lambda *_: self._take())
        bar.append(self.take_btn)
        return bar

    @staticmethod
    def _paint_dot(btn: Gtk.Button, hexv: str, chosen: bool) -> None:
        css = Gtk.CssProvider()
        ring = "box-shadow:0 0 0 2px %s;" % hexv if chosen else ""
        css.load_from_data(
            ("button{min-width:18px;min-height:18px;padding:0;border-radius:999px;"
             "background:%s;border:1px solid rgba(0,0,0,.18);%s}" % (hexv, ring)).encode())
        btn.get_style_context().add_provider(css, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

    def _on_key(self, _c, keyval, _code, state) -> bool:
        from gi.repository import Gdk as _Gdk

        ctrl = state & _Gdk.ModifierType.CONTROL_MASK
        if ctrl and keyval in (_Gdk.KEY_Return, _Gdk.KEY_KP_Enter):
            self._take()
            return True
        if keyval == _Gdk.KEY_Escape:
            self.close()
            return True
        if keyval == _Gdk.KEY_BackSpace and not self.source_mode:
            self._go_up()
            return True
        # Enter на выбранной строке открывает её: сам ListBox этого не делает,
        # пока по строке не щёлкнули мышью.
        if keyval in (_Gdk.KEY_Return, _Gdk.KEY_KP_Enter) and not self.source_mode:
            row = self.listbox.get_selected_row()
            # focus сидит на самой строке, а не на списке, поэтому спрашиваем
            # про предка: has_focus() у списка всегда ложь, и Enter пропадал.
            here = self.get_focus()
            in_list = here is not None and (here is self.listbox or here.is_ancestor(self.listbox))
            if row is not None and in_list:
                self._row_activated(self.listbox, row)
                return True
        return False

    def _pick(self, name: str) -> None:
        self.color = name
        for n, hexv in COLORS:
            self._paint_dot(self._dots[n], hexv, n == name)

    # ——— список файлов ———

    def refresh(self) -> None:
        if self.source_mode:
            return
        child = self.listbox.get_first_child()
        while child is not None:
            nxt = child.get_next_sibling()
            self.listbox.remove(child)
            child = nxt
        for entry in self.repo.list():
            self.listbox.append(self._row(entry))
        self.back_btn.set_sensitive(not self.repo.at_root)
        self.title_widget.set_subtitle(str(self.repo.cwd))

    def _row(self, entry: Entry) -> Gtk.ListBoxRow:
        row = Gtk.ListBoxRow()
        row._entry = entry            # noqa: SLF001 — привязка строки к записи
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        box.set_margin_top(8)
        box.set_margin_bottom(8)
        box.set_margin_start(10)
        box.set_margin_end(10)
        icon = Gtk.Image.new_from_icon_name(
            "folder-symbolic" if entry.is_folder else "text-x-generic-symbolic")
        box.append(icon)
        box.append(Gtk.Label(label=entry.title, xalign=0, hexpand=True, ellipsize=3))
        row.set_child(box)
        return row

    def _row_activated(self, _lb, row: Gtk.ListBoxRow) -> None:
        entry = getattr(row, "_entry", None)
        if entry is None:
            return
        if entry.is_folder:
            self.repo.enter(entry.path)
            self.refresh()
            self._focus_list()
        else:
            self.open(entry.path)

    def _focus_list(self) -> None:
        """После перехода по папкам список снова под стрелками, а не мимо."""
        self.listbox.grab_focus()
        first = self.listbox.get_row_at_index(0)
        if first is not None:
            self.listbox.select_row(first)

    def _go_up(self) -> None:
        if self.repo.up():
            self.refresh()
            self._focus_list()

    # ——— файл ———

    def open(self, path: Path) -> None:
        self.current = Path(path)
        text = FilesRepo.read(self.current)
        self.title_widget.set_subtitle(self.current.name)
        # Открыл файл — можно сразу выделять, курсор уже в тексте.
        self.web.grab_focus()
        if self._ready:
            self._render(text)
        else:
            self._pending = text

    def _show(self, text: str) -> None:
        """Готовый кусок без файла: вырезать из него можно, источника нет."""
        self.current = None
        if self._ready:
            self._render(text)
        else:
            self._pending = text

    def _render(self, text: str) -> None:
        self._js(f"MathMark.render({json.dumps(text)});")

    def _js(self, script: str) -> None:
        self.web.evaluate_javascript(script, -1, None, None, None, None, None)

    def _on_load(self, _web, event) -> None:
        if event != WebKit.LoadEvent.FINISHED:
            return
        self._ready = True
        dark = Adw.StyleManager.get_default().get_dark()
        self._js(f"MathMark.setTheme({str(dark).lower()});"
                 f"MathMark.setScale({self.st.scale:g});"
                 f"MathMark.cutMode(true);")
        pending = getattr(self, "_pending", None)
        if pending is not None:
            self._render(pending)
            self._pending = None

    def _from_page(self, _ucm, value) -> None:
        """Страница сообщает, есть ли что вырезать — по этому живёт кнопка."""
        try:
            data = json.loads(value.to_string())
        except (ValueError, AttributeError):
            return
        if data.get("name") == "onSelection":
            self.take_btn.set_sensitive(data.get("payload") == "1")

    # ——— вытащить ———

    def _take(self) -> None:
        def done(_web, res):
            try:
                val = self.web.evaluate_javascript_finish(res)
                data = json.loads(val.to_string()) if val else {}
            except (GLib.Error, ValueError, TypeError):
                data = {}
            md = (data.get("md") or "").strip()
            if not md:
                self.toasts.add_toast(Adw.Toast(title=t("cut.nothing")))
                return
            self.on_cut({
                "md": md,
                "color": self.color,
                "file": str(self.current) if self.current else "",
                "heading": data.get("heading") or "",
            })
            self.toasts.add_toast(Adw.Toast(title=t("cut.done")))

        self.web.evaluate_javascript("MathMark.cut()", -1, None, None, None, done)
