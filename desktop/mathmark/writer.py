"""
Окно помогалки по записи.

Отдельное окно: слева разделы и поиск, справа выбранная запись с пустыми
квадратиками. Заполнил — нажал «Скопировать» — вставил куда нужно.

Сама страница живёт в `shared/write/` и одинакова для компьютера и телефона.
Каталог отдаём ей отсюда: страница открыта из файла, а из файла браузер
наружу за файлами не ходит.
"""

from __future__ import annotations

import json

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
gi.require_version("WebKit", "6.0")

from gi.repository import Adw, Gdk, Gtk, WebKit  # noqa: E402

from .i18n import current, t  # noqa: E402
from .paths import write_catalog, write_html  # noqa: E402

UI_KEYS = ("write.search", "write.pick", "write.hint", "write.copy",
           "write.copyPlain", "write.copied", "write.none")


class WriterWindow(Adw.ApplicationWindow):
    """Одно окно на всю программу: второй раз — просто поднимаем это же."""

    def __init__(self, app, settings):
        super().__init__(application=app, title=t("write.title"))
        self.st = settings
        self.set_default_size(1080, 760)
        self.set_size_request(720, 480)
        self._build()

    def _build(self) -> None:
        view = Adw.ToolbarView()
        head = Adw.HeaderBar()
        head.set_title_widget(Adw.WindowTitle(title=t("write.title"), subtitle=t("write.pick")))
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
        """Как и у доски: правим ссылку на сценарий, чтобы не подсовывался старый."""
        page = write_html()
        html = page.read_text(encoding="utf-8")
        stamp = int((page.parent / "write.js").stat().st_mtime)
        html = html.replace('src="write.js"', f'src="write.js?v={stamp}"')
        self.web.load_html(html, page.as_uri())

    def _js(self, script: str) -> None:
        self.web.evaluate_javascript(script, -1, None, None, None, None, None)

    def _on_load(self, _web, event) -> None:
        if event != WebKit.LoadEvent.FINISHED:
            return
        dark = Adw.StyleManager.get_default().get_dark()
        labels = json.dumps({k: t(k) for k in UI_KEYS})
        self._js(
            f"Write.setLabels({labels});"
            f"Write.setLang({json.dumps(current())});"
            f"Write.setTheme({str(dark).lower()});"
            f"Write.setCatalog({json.dumps(write_catalog())});"
        )
        self.web.grab_focus()

    def _on_message(self, _ucm, value) -> None:
        try:
            data = json.loads(value.to_string())
        except (ValueError, AttributeError):
            return
        if data.get("name") == "onCopy":
            text = data.get("payload") or ""
            display = Gdk.Display.get_default()
            if display is not None:
                display.get_clipboard().set(text)
            self.toasts.add_toast(Adw.Toast(title=t("write.copied"), timeout=2))

    def refresh_theme(self) -> None:
        dark = Adw.StyleManager.get_default().get_dark()
        self._js(f"Write.setTheme({str(dark).lower()});")
