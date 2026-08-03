"""
Настройки обычным текстовым файлом — как на телефоне, тем же набором ключей:

    ~/.config/mathmark/mathmark.conf

        folder=/home/имя/Documents/math
        scale=1.0
        theme=auto
        width=1200
        height=800
        sidebar=1

Никакой базы и никакого скрытого состояния: всё, что делает программа,
можно сделать правкой текста — и наоборот.
"""

from __future__ import annotations

import os
from pathlib import Path

DEFAULT_FOLDER = str(Path.home() / "Documents" / "math")


class Settings:
    def __init__(self) -> None:
        base = os.environ.get("XDG_CONFIG_HOME") or str(Path.home() / ".config")
        self.file = Path(base) / "mathmark" / "mathmark.conf"
        self.folder = DEFAULT_FOLDER
        self.scale = 1.0
        self.theme = "auto"          # auto | light | dark
        self.lang = "auto"           # auto | en | ru | es
        # синхронизация: по умолчанию выключена, ничего никуда не уходит
        self.sync_on = False
        self.sync_repo = ""
        self.sync_token = ""
        # какую версию человек уже видел: «что нового» показывается один раз
        self.seen = ""
        self.width = 1180
        self.height = 820
        self.sidebar = True
        # свои цвета доски: список вида «#RRGGBB,#RRGGBB»
        self.colors: list[str] = []
        self.load()

    def load(self) -> None:
        try:
            lines = self.file.read_text(encoding="utf-8").splitlines()
        except OSError:
            return
        for raw in lines:
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = (x.strip() for x in line.split("=", 1))
            try:
                if k == "folder" and v:
                    self.folder = v
                elif k == "scale":
                    self.scale = min(1.6, max(0.8, float(v)))
                elif k == "theme" and v in ("auto", "light", "dark"):
                    self.theme = v
                elif k == "lang" and v in ("auto", "en", "ru", "es"):
                    self.lang = v
                elif k == "colors":
                    self.colors = [c for c in v.split(",") if c.startswith("#")][:8]
                elif k == "sync":
                    self.sync_on = v not in ("0", "false", "нет")
                elif k == "repo":
                    self.sync_repo = v
                elif k == "token":
                    self.sync_token = v
                elif k == "seen":
                    self.seen = v
                elif k == "width":
                    self.width = max(480, int(v))
                elif k == "height":
                    self.height = max(400, int(v))
                elif k == "sidebar":
                    self.sidebar = v not in ("0", "false", "нет")
            except ValueError:
                continue

    @property
    def sync_ready(self) -> bool:
        """Настроено ли всё, что нужно для кнопки."""
        return bool(self.sync_on and self.sync_repo.strip() and self.sync_token.strip())

    def save(self) -> None:
        try:
            self.file.parent.mkdir(parents=True, exist_ok=True)
            self.file.write_text(
                f"folder={self.folder}\n"
                f"scale={self.scale:g}\n"
                f"theme={self.theme}\n"
                f"lang={self.lang}\n"
                f"colors={','.join(self.colors)}\n"
                f"sync={1 if self.sync_on else 0}\n"
                f"repo={self.sync_repo}\n"
                f"token={self.sync_token}\n"
                f"seen={self.seen}\n"
                f"width={self.width}\n"
                f"height={self.height}\n"
                f"sidebar={1 if self.sidebar else 0}\n",
                encoding="utf-8",
            )
        except OSError:
            pass
