"""
Программа целиком: действия, горячие клавиши, окно настроек.
"""

from __future__ import annotations

import sys

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from pathlib import Path  # noqa: E402

from gi.repository import Adw, Gdk, Gio, GLib, Gtk  # noqa: E402

from . import i18n  # noqa: E402
from .i18n import t  # noqa: E402
from .board import BoardWindow, boards_in  # noqa: E402
from .writer import WriterWindow  # noqa: E402
from .settings import Settings  # noqa: E402
from .sync import FROZEN  # noqa: E402
from .window import CSS, MathMarkWindow  # noqa: E402

APP_ID = "io.github.volkinstridov.MathMark"

SHORTCUTS = [
    ("Ctrl + F", "keys.search"),
    ("Escape", "keys.clearSearch"),
    ("Ctrl + P", "keys.print"),
    ("Ctrl + +/−", "keys.zoom"),
    ("Ctrl + 0", "keys.zoomReset"),
    ("Ctrl + B", "keys.sidebar"),
    ("Ctrl + R", "keys.refresh"),
    ("F11", "keys.fullscreen"),
    ("Ctrl + D", "keys.board"),
    ("Ctrl + M", "keys.write"),
    ("Ctrl + T", "keys.cut"),
    ("Ctrl + G", "keys.card"),
    ("Ctrl + E", "keys.edit"),
    ("Ctrl + N", "keys.newFile"),
    ("Ctrl + S", "keys.sync"),
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
        self._whats_new(self.win)

    def _whats_new(self, win) -> None:
        """Один раз после обновления — короткий список, что появилось."""
        from . import __version__
        from .paths import whats_new

        if self.st.seen == __version__:
            return
        items = whats_new(__version__, i18n.current())
        if not items:
            self.st.seen = __version__
            self.st.save()
            return

        dlg = Adw.AlertDialog(heading=t("new.title"))
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        for line in items:
            row = Gtk.Box(spacing=8)
            dot = Gtk.Label(label="•", valign=Gtk.Align.START)
            dot.add_css_class("accent")
            text = Gtk.Label(label=line, wrap=True, xalign=0, max_width_chars=46)
            row.append(dot)
            row.append(text)
            box.append(row)
        dlg.set_extra_child(box)
        dlg.add_response("ok", t("new.ok"))
        dlg.set_default_response("ok")

        def done(_d, _r):
            self.st.seen = __version__
            self.st.save()

        dlg.connect("response", done)
        dlg.present(win)

    def open_board(self, parent) -> None:
        """
        Доска — отдельное окно, читалка при этом остаётся открытой.

        Окно одно: раньше каждое нажатие Ctrl+D открывало новое, два окна
        садились на один файл и по очереди затирали друг друга — чьё
        сохранение последнее, того и доска.
        """
        old = getattr(self, "_board", None)
        if old is not None:
            old.present()
            return

        folder = Path(self.st.folder)
        existing = boards_in(folder)
        win = BoardWindow(self, self.st, folder)
        self._board_actions(win)
        win.fill_list()
        if existing:
            win.open(existing[0])
        else:
            win.create(t("board.title"))

        def gone(*_):
            self._board = None
            return False

        win.connect("close-request", gone)
        self._board = win
        win.present()

    def open_writer(self, parent=None) -> None:
        """Помогалка по записи. Окно одно на всю программу: второй раз — поднимаем."""
        if getattr(self, "_writer", None) is not None:
            self._writer.present()
            return
        win = WriterWindow(self, self.st)
        self._writer = win

        def gone(*_):
            self._writer = None
            return False

        win.connect("close-request", gone)
        win.present()

    def _board_actions(self, win) -> None:
        def add(name, fn, *accels):
            act = Gio.SimpleAction.new(name, None)
            act.connect("activate", lambda *_: fn())
            win.add_action(act)
            if accels:
                self.set_accels_for_action(f"win.{name}", list(accels))

        add("board-write", lambda: self.open_writer(win), "<Ctrl>m")
        add("board-cut", lambda: win.open_cutter(), "<Ctrl>t")
        add("board-card", lambda: win.open_picker(), "<Ctrl>g")
        add("board-save", win.save, "<Ctrl>s")
        add("board-clear", win.clear)
        add("board-new", lambda: self._ask_board_name(win))
        add("board-pick", lambda: win.list_btn.popup())
        add("board-png", win.save_png)
        add("board-rename", win.rename)
        add("board-find", win.find, "<Ctrl>f")

    def _ask_board_name(self, win) -> None:
        dlg = Adw.AlertDialog(heading=t("board.new"))
        entry = Gtk.Entry(placeholder_text=t("board.name"))
        dlg.set_extra_child(entry)
        dlg.add_response("cancel", t("common.cancel"))
        dlg.add_response("ok", t("common.done"))
        dlg.set_default_response("ok")

        def done(_d, answer):
            if answer == "ok" and entry.get_text().strip():
                win.create(entry.get_text())
                win.fill_list()

        dlg.connect("response", done)
        dlg.present(win)

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
        add("sync", win.do_sync, "<Ctrl>s")
        add("edit", lambda: win.edit_btn.set_active(not win.edit_btn.get_active()), "<Ctrl>e")
        add("board", lambda: self.open_board(win), "<Ctrl>d")
        add("write", lambda: self.open_writer(win), "<Ctrl>m")
        add("new-file", lambda: win._ask_name(
            t("edit.new"), "", win.new_file), "<Ctrl>n")
        add("new-folder", lambda: win._ask_name(
            t("list.newFolder"), "", lambda n: (win.repo.create_folder(n), win.refresh())))
        add("settings", lambda: self._settings_dialog(win))
        add("stats", lambda: self._stats_dialog(win))
        add("today", lambda: self._today_dialog(win))

        # переход из уведомления: открыть тот файл, о котором напомнили
        open_file = Gio.SimpleAction.new("open-file", GLib.VariantType.new("s"))
        open_file.connect("activate", lambda _a, v: win.open_doc(Path(v.get_string())))
        self.add_action(open_file)
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

        sync_group = Adw.PreferencesGroup(title=t("sync.title"))
        if FROZEN:
            # Раздел на месте, но не работает: так видно, что возможность есть
            # и она готовится, а не исчезла между версиями.
            sync_group.set_description(t("sync.frozen"))
            sync_group.set_sensitive(False)

        on_row = Adw.SwitchRow(title=t("sync.enabled"), active=win.st.sync_on)

        def sync_toggled(row, *_):
            win.st.sync_on = row.get_active()
            win.st.save()

        on_row.connect("notify::active", sync_toggled)
        sync_group.add(on_row)

        repo_row = Adw.EntryRow(title=t("sync.repo"), text=win.st.sync_repo)

        def repo_changed(row, *_):
            win.st.sync_repo = row.get_text().strip()
            win.st.save()

        repo_row.connect("changed", repo_changed)
        sync_group.add(repo_row)

        token_row = Adw.PasswordEntryRow(title=t("sync.token"), text=win.st.sync_token)

        def token_changed(row, *_):
            win.st.sync_token = row.get_text().strip()
            win.st.save()

        token_row.connect("changed", token_changed)
        sync_group.add(token_row)

        check_row = Adw.ActionRow(title=t("sync.check"), subtitle=t("sync.checkHint"))
        check_btn = Gtk.Button(label=t("sync.check"), valign=Gtk.Align.CENTER)

        def do_check(*_):
            import threading

            from gi.repository import GLib

            from .sync import GitHub

            check_btn.set_sensitive(False)

            def work():
                problem = GitHub(win.st.sync_repo, win.st.sync_token).check()
                GLib.idle_add(show, problem)

            def show(problem):
                check_btn.set_sensitive(True)
                check_row.set_subtitle(problem or t("sync.ok"))
                return False

            threading.Thread(target=work, daemon=True).start()

        check_btn.connect("clicked", do_check)
        check_row.add_suffix(check_btn)
        sync_group.add(check_row)
        page.add(sync_group)

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

        from .paths import links as outside_links
        urls = outside_links()

        talk = Adw.PreferencesGroup(title=t("settings.feedback"))
        for key, title_key, hint_key in (
            ("telegram", "settings.feedback", "settings.feedbackHint"),
            ("issues", "settings.issues", "settings.issuesHint"),
        ):
            if not urls.get(key):
                continue
            row = Adw.ActionRow(title=t(title_key), subtitle=t(hint_key))
            btn = Gtk.LinkButton(uri=urls[key], label="→", valign=Gtk.Align.CENTER)
            row.add_suffix(btn)
            row.set_activatable_widget(btn)
            talk.add(row)
        page.add(talk)

        about = Adw.PreferencesGroup(title=t("settings.about"))
        about.add(Adw.ActionRow(
            title=t("settings.version"),
            subtitle=t("settings.versionHint") + " · ~/.config/mathmark/mathmark.conf",
        ))
        page.add(about)

        dlg = Adw.PreferencesDialog(title=t("settings.title"))
        dlg.add(page)
        dlg.present(win)

    def _today_dialog(self, win: MathMarkWindow) -> None:
        """Что напомнит сегодня. Список, а не всплывающие окна."""
        from datetime import date

        from . import reminders as rem

        items = rem.for_day(rem.load(win.reminders_file), date.today())
        page = Adw.PreferencesPage()
        group = Adw.PreferencesGroup(title=t("rem.today"))
        if not items:
            group.add(Adw.ActionRow(title=t("rem.none")))
        for r in items:
            row = Adw.ActionRow(
                title=r.text or r.path.removesuffix(".md"),
                subtitle=f"{r.at:%H:%M} · {r.path.removesuffix('.md')}",
            )
            drop = Gtk.Button(label=t("rem.remove"), valign=Gtk.Align.CENTER)

            def remove(_b, victim=r):
                rest = [x for x in rem.load(win.reminders_file) if x != victim]
                rem.save(win.reminders_file, rest)
                dlg.close()
                self._today_dialog(win)

            drop.connect("clicked", remove)
            row.add_suffix(drop)
            group.add(row)
        page.add(group)
        dlg = Adw.PreferencesDialog(title=t("rem.today"))
        dlg.add(page)
        dlg.present(win)

    def reminder_dialog(self, win: MathMarkWindow, path: str) -> None:
        """Навесить напоминание на файл. Внутрь .md ничего не пишется."""
        from datetime import date, datetime, time as dtime, timedelta

        from . import reminders as rem

        existing = next((x for x in rem.load(win.reminders_file) if x.path == path), None)
        start = existing.at if existing else dtime(19, 0)

        dlg = Adw.AlertDialog(heading=t("rem.title"), body=path.removesuffix(".md"))
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)

        text = Gtk.Entry(placeholder_text=t("rem.text"),
                         text=existing.text if existing else "")
        box.append(text)

        repeat = Gtk.DropDown.new_from_strings([t("rem.daily"), t("rem.weekly"), t("rem.once")])
        repeat.set_selected({rem.DAILY: 0, rem.WEEKLY: 1, rem.ONCE: 2}[existing.repeat] if existing else 0)
        box.append(repeat)

        days = Gtk.DropDown.new_from_strings([t(f"rem.day{i}") for i in range(1, 8)])
        days.set_selected((existing.weekday - 1) if existing and existing.weekday else 0)
        box.append(days)

        row = Gtk.Box(spacing=6, halign=Gtk.Align.CENTER)
        hh = Gtk.SpinButton.new_with_range(0, 23, 1)
        mm = Gtk.SpinButton.new_with_range(0, 59, 1)
        hh.set_value(start.hour)
        mm.set_value(start.minute)
        for w in (hh, mm):
            w.set_orientation(Gtk.Orientation.VERTICAL)
        row.append(hh)
        row.append(Gtk.Label(label=":"))
        row.append(mm)
        box.append(row)

        dlg.set_extra_child(box)
        dlg.add_response("cancel", t("common.cancel"))
        dlg.add_response("ok", t("common.done"))
        dlg.set_default_response("ok")

        def resp(_d, answer):
            if answer != "ok":
                return
            at = dtime(int(hh.get_value()), int(mm.get_value()))
            kind = [rem.DAILY, rem.WEEKLY, rem.ONCE][repeat.get_selected()]
            on = None
            if kind == rem.ONCE:
                today = date.today()
                on = today if datetime.combine(today, at) > datetime.now() else today + timedelta(days=1)
            item = rem.Reminder(path, kind, at, text.get_text().strip(),
                                weekday=days.get_selected() + 1 if kind == rem.WEEKLY else 0,
                                on=on)
            rest = [x for x in rem.load(win.reminders_file) if x.path != path]
            rem.save(win.reminders_file, rest + [item])
            win.toast(t("rem.saved"))

        dlg.connect("response", resp)
        dlg.present(win)

    def _stats_dialog(self, win: MathMarkWindow) -> None:
        """Сколько сделано. Считается по журналу отметок, не по файлам."""
        from .stats import parse, summarise

        try:
            text = (win.st.file.parent / "journal.log").read_text(encoding="utf-8")
        except OSError:
            text = ""
        st = summarise(parse(text))

        page = Adw.PreferencesPage()
        group = Adw.PreferencesGroup(title=t("stats.title"))

        if st.month_tasks == 0 and st.month_topics == 0 and st.streak == 0:
            group.add(Adw.ActionRow(title=t("stats.empty")))
        else:
            for title, tasks, topics in (
                (t("stats.today"), st.today_tasks, st.today_topics),
                (t("stats.week"), st.week_tasks, st.week_topics),
                (t("stats.month"), st.month_tasks, st.month_topics),
            ):
                row = Adw.ActionRow(
                    title=title,
                    subtitle=f"{t('stats.tasks', tasks)} · {t('stats.topics', topics)}",
                )
                big = Gtk.Label(label=str(tasks + topics), valign=Gtk.Align.CENTER)
                big.add_css_class("title-2")
                row.add_suffix(big)
                group.add(row)

            from .md_items import plural_form
            streak_row = Adw.ActionRow(
                title=t("stats.streak"),
                subtitle=t("days." + plural_form(st.streak, i18n.current()), st.streak),
            )
            big = Gtk.Label(label=str(st.streak), valign=Gtk.Align.CENTER)
            big.add_css_class("title-2")
            streak_row.add_suffix(big)
            group.add(streak_row)
        page.add(group)

        if st.per_day:
            chart = Adw.PreferencesGroup(title=t("stats.last30"))
            area = Gtk.DrawingArea(content_height=90)
            top = max((n for _, n in st.per_day), default=0) or 1

            def draw(_a, cr, w, h, *_):
                gap = 3
                bw = max(2.0, (w - gap * (len(st.per_day) - 1)) / len(st.per_day))
                for i, (_, n) in enumerate(st.per_day):
                    frac = 0.04 if n == 0 else max(0.12, n / top)
                    bh = h * frac
                    x = i * (bw + gap)
                    if n == 0:
                        cr.set_source_rgba(0.6, 0.6, 0.6, 0.25)
                    else:
                        cr.set_source_rgb(0.486, 0.227, 0.929)
                    cr.rectangle(x, h - bh, bw, bh)
                    cr.fill()

            area.set_draw_func(draw)
            box = Gtk.Box()
            box.append(area)
            area.set_hexpand(True)
            chart.add(box)
            page.add(chart)

        dlg = Adw.PreferencesDialog(title=t("stats.title"))
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
        dlg = Adw.PreferencesDialog(title=t("desk.shortcuts"))
        dlg.add(page)
        dlg.present(win)


def main() -> int:
    return MathMarkApp().run(sys.argv)
