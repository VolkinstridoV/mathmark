"""
Программа целиком: действия, горячие клавиши, окно настроек.
"""

from __future__ import annotations

import sys

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gdk, Gio, Gtk  # noqa: E402

from . import i18n  # noqa: E402
from .i18n import t  # noqa: E402
from .settings import Settings  # noqa: E402
from .window import CSS, MathMarkWindow  # noqa: E402

APP_ID = "dev.yury.mathmark"

SHORTCUTS = [
    ("Ctrl + F", "keys.search"),
    ("Escape", "keys.clearSearch"),
    ("Ctrl + P", "keys.print"),
    ("Ctrl + +/−", "keys.zoom"),
    ("Ctrl + 0", "keys.zoomReset"),
    ("Ctrl + B", "keys.sidebar"),
    ("Ctrl + R", "keys.refresh"),
    ("F11", "keys.fullscreen"),
    ("Ctrl + Q", "keys.quit"),
]


class MathMarkApp(Adw.Application):
    def __init__(self) -> None:
        super().__init__(application_id=APP_ID, flags=Gio.ApplicationFlags.HANDLES_OPEN)
        self.st = Settings()
        # надписи берутся из общей папки переводов — той же, что у телефона
        i18n.use(self.st.lang)
        self.win: MathMarkWindow | None = None

    def do_startup(self) -> None:
        Adw.Application.do_startup(self)
        provider = Gtk.CssProvider()
        provider.load_from_data(CSS)
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(), provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

    def do_activate(self) -> None:
        if self.win is None:
            self.win = MathMarkWindow(self, self.st)
            self._actions(self.win)
        self.win.present()

    def do_open(self, files, n_files, hint) -> None:
        """Открыть переданный файл: `mathmark шпора.md`."""
        self.do_activate()
        if files:
            path = files[0].get_path()
            if path:
                self.win.open_doc(path)

    # ——— действия и клавиши ———

    def _actions(self, win: MathMarkWindow) -> None:
        def add(name: str, fn, *accels: str):
            act = Gio.SimpleAction.new(name, None)
            act.connect("activate", lambda *_: fn())
            win.add_action(act)
            if accels:
                self.set_accels_for_action(f"win.{name}", list(accels))

        add("search", lambda: (win.split.set_show_sidebar(True), win.search.grab_focus()), "<Ctrl>f")
        add("clear-search", lambda: win.search.set_text(""), "Escape")
        add("print", win.do_print, "<Ctrl>p")
        add("zoom-in", lambda: win.set_scale(win.st.scale + 0.05), "<Ctrl>plus", "<Ctrl>equal")
        add("zoom-out", lambda: win.set_scale(win.st.scale - 0.05), "<Ctrl>minus")
        add("zoom-reset", lambda: win.set_scale(1.0), "<Ctrl>0")
        add("sidebar", lambda: win.toggle.set_active(not win.toggle.get_active()), "<Ctrl>b")
        add("refresh", win.refresh, "<Ctrl>r")
        add("fullscreen", lambda: (win.unfullscreen() if win.is_fullscreen() else win.fullscreen()), "F11")
        add("quit", lambda: (win.close(), self.quit()), "<Ctrl>q")
        add("copy-prompt", win.copy_prompt)
        add("new-folder", lambda: win._ask_name(
            t("list.newFolder"), "", lambda n: (win.repo.create_folder(n), win.refresh())))
        add("settings", lambda: self._settings_dialog(win))
        add("shortcuts", lambda: self._shortcuts_dialog(win))

    # ——— окна ———

    def _settings_dialog(self, win: MathMarkWindow) -> None:
        page = Adw.PreferencesPage()

        files = Adw.PreferencesGroup(title=t("settings.files"))
        folder_row = Adw.ActionRow(title=t("desk.folderTitle"), subtitle=win.st.folder)
        pick = Gtk.Button(label=t("desk.pickFolder"), valign=Gtk.Align.CENTER)

        def choose(*_):
            dlg = Gtk.FileDialog(title=t("desk.folderTitle"))
            dlg.select_folder(win, None, done)

        def done(dlg, res):
            try:
                folder = dlg.select_folder_finish(res)
            except Exception:
                return
            path = folder.get_path()
            if path:
                win.set_folder(path)
                folder_row.set_subtitle(path)

        pick.connect("clicked", choose)
        folder_row.add_suffix(pick)
        files.add(folder_row)
        files.add(Adw.ActionRow(
            title=t("settings.shows"),
            subtitle=t("settings.showsHint"),
        ))
        page.add(files)

        look = Adw.PreferencesGroup(title=t("settings.view"))
        scale_row = Adw.ActionRow(title=t("settings.textSize"),
                                  subtitle=t("settings.textSizeHint"))
        adj = Gtk.Adjustment(value=win.st.scale, lower=0.8, upper=1.6, step_increment=0.05)
        slider = Gtk.Scale(adjustment=adj, hexpand=True, draw_value=False,
                           valign=Gtk.Align.CENTER, width_request=200)
        slider.connect("value-changed", lambda s: win.set_scale(s.get_value()))
        scale_row.add_suffix(slider)
        look.add(scale_row)

        theme_row = Adw.ComboRow(
            title=t("settings.theme"),
            model=Gtk.StringList.new([
                t("settings.themeAuto"), t("settings.themeLight"), t("settings.themeDark"),
            ]),
            selected={"auto": 0, "light": 1, "dark": 2}[win.st.theme],
        )

        def theme_changed(row, *_):
            win.st.theme = ["auto", "light", "dark"][row.get_selected()]
            win.st.save()
            win._apply_theme()
            win._render()

        theme_row.connect("notify::selected", theme_changed)
        look.add(theme_row)

        # язык: флажок и родное название, чтобы не гадать по коду страны
        codes = ["auto"] + list(i18n.LANGUAGES)
        lang_row = Adw.ComboRow(
            title=t("settings.language"),
            model=Gtk.StringList.new(
                [t("settings.languageAuto")]
                + [f"{i18n.FLAGS[c]}  {i18n.NATIVE[c]}" for c in i18n.LANGUAGES]
            ),
            selected=codes.index(win.st.lang) if win.st.lang in codes else 0,
        )

        def lang_changed(row, *_):
            win.st.lang = codes[row.get_selected()]
            win.st.save()
            i18n.use(win.st.lang)
            win.relabel()
            dlg.close()
            self._settings_dialog(win)      # окно настроек тоже на новом языке

        lang_row.connect("notify::selected", lang_changed)
        look.add(lang_row)
        page.add(look)

        ai = Adw.PreferencesGroup(
            title=t("settings.ai"),
            description=t("settings.copyPromptHint"),
        )
        prompt_row = Adw.ActionRow(title=t("settings.copyPrompt"))
        btn = Gtk.Button(label=t("settings.copyPrompt"), valign=Gtk.Align.CENTER)
        btn.connect("clicked", lambda *_: win.copy_prompt())
        prompt_row.add_suffix(btn)
        ai.add(prompt_row)
        page.add(ai)

        about = Adw.PreferencesGroup(title=t("settings.about"))
        about.add(Adw.ActionRow(
            title=t("settings.version"),
            subtitle=t("settings.versionHint") + " · ~/.config/mathmark/mathmark.conf",
        ))
        page.add(about)

        dlg = Adw.PreferencesDialog()
        dlg.add(page)
        dlg.present(win)

    def _shortcuts_dialog(self, win: MathMarkWindow) -> None:
        page = Adw.PreferencesPage()
        group = Adw.PreferencesGroup(title=t("desk.shortcuts"))
        for keys, what in SHORTCUTS:
            row = Adw.ActionRow(title=t(what))
            label = Gtk.Label(label=keys, valign=Gtk.Align.CENTER)
            label.add_css_class("dim-label")
            label.add_css_class("monospace")
            row.add_suffix(label)
            group.add(row)
        page.add(group)
        dlg = Adw.PreferencesDialog()
        dlg.add(page)
        dlg.present(win)


def main() -> int:
    return MathMarkApp().run(sys.argv)
