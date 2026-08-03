"""
Выбор формулы для доски: список каталога с поиском.

Окно нарочно простое и родное, без встроенной страницы: здесь нечего рисовать
формулами — нужен быстрый список, по которому идут стрелками и ищут словами.
Сама формула со всеми полями появляется уже на доске.

Поиск идёт по названию и по словам-подсказкам сразу на трёх языках: человек
ищет тем словом, которое пришло в голову, а не тем, что записано в учебнике.
"""

from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gdk, Gtk  # noqa: E402

from .i18n import current, t  # noqa: E402


class PickerWindow(Adw.ApplicationWindow):
    def __init__(self, app, catalog: dict, on_pick) -> None:
        super().__init__(application=app, title=t("card.title"))
        self.catalog = catalog
        self.on_pick = on_pick
        self.lang = current()

        self.set_default_size(460, 640)
        self.set_size_request(360, 380)
        self._build()
        self.fill("")

        keys = Gtk.EventControllerKey()
        keys.connect("key-pressed", self._on_key)
        self.add_controller(keys)

    def _build(self) -> None:
        view = Adw.ToolbarView()
        head = Adw.HeaderBar()
        head.set_title_widget(Adw.WindowTitle(title=t("card.title"),
                                              subtitle=t("card.pick")))
        view.add_top_bar(head)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.search = Gtk.SearchEntry(placeholder_text=t("card.search"))
        self.search.set_margin_top(8)
        self.search.set_margin_bottom(8)
        self.search.set_margin_start(10)
        self.search.set_margin_end(10)
        self.search.connect("search-changed", lambda e: self.fill(e.get_text()))
        # Enter из строки поиска берёт первое найденное: искать и тут же
        # выбирать — обычный ход, а без этого нажатие просто пропадало.
        self.search.connect("activate", lambda *_: self._take_selected())
        box.append(self.search)

        self.list = Gtk.ListBox(selection_mode=Gtk.SelectionMode.SINGLE)
        self.list.add_css_class("navigation-sidebar")
        self.list.connect("row-activated", self._activated)
        box.append(Gtk.ScrolledWindow(vexpand=True, child=self.list))

        view.set_content(box)
        self.set_content(view)

    # ——— список ———

    def _name(self, d: dict) -> str:
        n = d.get("n", {})
        return n.get(self.lang) or n.get("en") or d.get("id", "")

    def _matches(self, item: dict, needle: str) -> bool:
        if not needle:
            return True
        hay = " ".join(list(item.get("n", {}).values()) + list(item.get("k", {}).values()))
        return all(w in hay.lower() for w in needle.lower().split())

    def fill(self, needle: str) -> None:
        child = self.list.get_first_child()
        while child is not None:
            nxt = child.get_next_sibling()
            self.list.remove(child)
            child = nxt

        shown = 0
        for sec in self.catalog.get("sections", []):
            inside = [i for i in self.catalog.get("items", [])
                      if i.get("s") == sec.get("id") and self._matches(i, needle)]
            if not inside:
                continue
            self.list.append(self._header(self._name(sec)))
            for item in inside:
                self.list.append(self._row(item))
                shown += 1

        if not shown:
            self.list.append(self._header(t("card.none")))
        first = self._first_pickable()
        if first is not None:
            self.list.select_row(first)

    def _header(self, text: str) -> Gtk.ListBoxRow:
        row = Gtk.ListBoxRow(selectable=False, activatable=False)
        lab = Gtk.Label(label=text.upper(), xalign=0)
        lab.add_css_class("dim-label")
        lab.add_css_class("caption-heading")
        lab.set_margin_top(12)
        lab.set_margin_bottom(2)
        lab.set_margin_start(12)
        row.set_child(lab)
        return row

    def _row(self, item: dict) -> Gtk.ListBoxRow:
        row = Gtk.ListBoxRow()
        row._item = item                     # noqa: SLF001
        lab = Gtk.Label(label=self._name(item), xalign=0, ellipsize=3)
        lab.set_margin_top(7)
        lab.set_margin_bottom(7)
        lab.set_margin_start(14)
        lab.set_margin_end(10)
        row.set_child(lab)
        return row

    def _first_pickable(self) -> Gtk.ListBoxRow | None:
        i = 0
        while True:
            row = self.list.get_row_at_index(i)
            if row is None:
                return None
            if getattr(row, "_item", None) is not None:
                return row
            i += 1

    def _activated(self, _lb, row: Gtk.ListBoxRow) -> None:
        item = getattr(row, "_item", None)
        if item is not None:
            self.on_pick(item["id"])
            self.close()

    def _take_selected(self) -> bool:
        row = self.list.get_selected_row() or self._first_pickable()
        if row is not None and getattr(row, "_item", None) is not None:
            self._activated(self.list, row)
            return True
        return False

    def _on_key(self, _c, keyval, _code, _state) -> bool:
        if keyval == Gdk.KEY_Escape:
            self.close()
            return True
        if keyval in (Gdk.KEY_Return, Gdk.KEY_KP_Enter):
            return self._take_selected()
        if keyval in (Gdk.KEY_Down, Gdk.KEY_Up):
            # Стрелки ходят по списку, даже когда курсор в поиске.
            self._step(1 if keyval == Gdk.KEY_Down else -1)
            return True
        return False

    def _step(self, way: int) -> None:
        rows = []
        i = 0
        while True:
            r = self.list.get_row_at_index(i)
            if r is None:
                break
            if getattr(r, "_item", None) is not None:
                rows.append(r)
            i += 1
        if not rows:
            return
        cur = self.list.get_selected_row()
        at = rows.index(cur) if cur in rows else -1
        nxt = rows[(at + way) % len(rows)]
        self.list.select_row(nxt)
        nxt.grab_focus()
        self.search.grab_focus_without_selecting()
