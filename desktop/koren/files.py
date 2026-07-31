"""
Папка с математикой: чтение содержимого, переходы по вложенным папкам,
действия над файлами и папками, поиск.

Повтор `FilesRepo.kt`, плюс поиск по всем файлам — на компьютере он нужен,
на телефоне его нет.
"""

from __future__ import annotations

import os
import tempfile
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Entry:
    path: Path
    is_folder: bool
    inside: int = 0          # сколько всего внутри, для папок

    @property
    def name(self) -> str:
        return self.path.name

    @property
    def title(self) -> str:
        n = self.path.name
        return n[:-3] if n.lower().endswith(".md") else n


class FilesRepo:
    def __init__(self, root: str | os.PathLike):
        self.root = Path(root).expanduser()
        self.cwd = self.root

    # ——— переходы ———

    @property
    def at_root(self) -> bool:
        return self.cwd.resolve() == self.root.resolve()

    def create_root(self) -> bool:
        try:
            self.root.mkdir(parents=True, exist_ok=True)
            return True
        except OSError:
            return False

    def enter(self, folder: Path) -> None:
        folder = Path(folder)
        if folder.is_dir() and str(folder.resolve()).startswith(str(self.root.resolve())):
            self.cwd = folder

    def up(self) -> bool:
        if self.at_root:
            return False
        self.cwd = self.cwd.parent
        return True

    def reset(self) -> None:
        self.cwd = self.root

    def crumbs(self) -> list[Path]:
        """Дорожка от корня до текущей папки."""
        out: list[Path] = []
        cur = self.cwd.resolve()
        root = self.root.resolve()
        while True:
            out.insert(0, cur)
            if cur == root or cur == cur.parent:
                break
            cur = cur.parent
        return out

    # ——— содержимое ———

    def list(self, folder: Path | None = None) -> list[Entry]:
        """Сначала вложенные папки, потом файлы `.md`. Скрытое не показывается."""
        d = Path(folder) if folder else self.cwd
        try:
            children = list(d.iterdir())
        except OSError:
            return []
        folders = sorted(
            (c for c in children if c.is_dir() and not c.name.startswith(".")),
            key=lambda c: c.name.lower(),
        )
        docs = sorted(
            (c for c in children
             if c.is_file() and not c.name.startswith(".") and c.suffix.lower() == ".md"),
            key=lambda c: c.name.lower(),
        )
        return (
            [Entry(f, True, self._count_inside(f)) for f in folders]
            + [Entry(f, False) for f in docs]
        )

    @staticmethod
    def _count_inside(d: Path) -> int:
        try:
            return sum(
                1 for c in d.iterdir()
                if not c.name.startswith(".") and (c.is_dir() or c.suffix.lower() == ".md")
            )
        except OSError:
            return 0

    def all_docs(self) -> list[Path]:
        """Все файлы `.md` в дереве — для поиска."""
        out: list[Path] = []
        for dirpath, dirnames, filenames in os.walk(self.root):
            dirnames[:] = sorted(d for d in dirnames if not d.startswith("."))
            for f in sorted(filenames):
                if f.lower().endswith(".md") and not f.startswith("."):
                    out.append(Path(dirpath) / f)
        return out

    def all_folders(self) -> list[Path]:
        out: list[Path] = []
        for dirpath, dirnames, _ in os.walk(self.root):
            dirnames[:] = sorted(d for d in dirnames if not d.startswith("."))
            for d in dirnames:
                out.append(Path(dirpath) / d)
        return out

    # ——— чтение и запись ———

    @staticmethod
    def read(file: Path) -> str:
        try:
            return Path(file).read_text(encoding="utf-8")
        except OSError:
            return ""

    @staticmethod
    def write(file: Path, text: str) -> bool:
        """
        Атомарная запись: во временный файл рядом, затем переименование.
        Обрыв посреди записи не оставит покалеченный файл.
        """
        file = Path(file)
        try:
            fd, tmp = tempfile.mkstemp(dir=file.parent, prefix=".", suffix=".tmp")
            with os.fdopen(fd, "w", encoding="utf-8", newline="") as fh:
                fh.write(text)
            os.replace(tmp, file)
            return True
        except OSError:
            try:
                os.unlink(tmp)      # noqa: F821
            except Exception:
                pass
            return False

    # ——— действия ———

    def create_folder(self, name: str) -> bool:
        clean = self._safe(name)
        if not clean:
            return False
        try:
            (self.cwd / clean).mkdir()
            return True
        except OSError:
            return False

    def rename(self, entry: Entry, new_name: str) -> bool:
        clean = self._safe(new_name)
        if not clean:
            return False
        if not entry.is_folder and not clean.lower().endswith(".md"):
            clean += ".md"
        target = entry.path.parent / clean
        if target.exists():
            return False
        try:
            entry.path.rename(target)
            return True
        except OSError:
            return False

    def move(self, entry: Entry, target_dir: Path) -> bool:
        target_dir = Path(target_dir)
        if not target_dir.is_dir():
            return False
        target = target_dir / entry.path.name
        if target.exists():
            return False
        try:
            entry.path.rename(target)
            return True
        except OSError:
            return False

    def delete(self, entry: Entry) -> bool:
        try:
            if entry.is_folder:
                import shutil
                shutil.rmtree(entry.path)
            else:
                entry.path.unlink()
            return True
        except OSError:
            return False

    # ——— поиск ———

    def search(self, query: str, limit: int = 200) -> list[tuple[Path, str]]:
        """
        Поиск по всем файлам: сначала совпадения в имени, потом в тексте.
        Возвращает пары «файл, строка с попаданием».
        """
        q = query.strip().lower()
        if not q:
            return []
        by_name: list[tuple[Path, str]] = []
        by_text: list[tuple[Path, str]] = []
        for f in self.all_docs():
            if q in f.name.lower():
                by_name.append((f, "совпадает имя файла"))
                continue
            for line in self.read(f).split("\n"):
                if q in line.lower():
                    by_text.append((f, line.strip()[:120]))
                    break
            if len(by_name) + len(by_text) >= limit:
                break
        return by_name + by_text

    @staticmethod
    def _safe(raw: str) -> str | None:
        # пробелы в именах разрешены, косые черты — нет: они уводят из папки
        n = raw.strip().replace("/", "").replace("\\", "")
        return None if n in ("", ".", "..") else n
