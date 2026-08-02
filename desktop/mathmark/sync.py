"""
Синхронизация папки с математикой через GitHub.

Работает по обычному сетевому обращению к GitHub, без установки git —
это важно, потому что на телефоне git взять неоткуда, а правила должны
совпадать до мелочей.

Как устроено:

* рядом с настройками лежит **теневая копия** того, что было при прошлой
  синхронизации: `~/.config/mathmark/base/`. Она нужна, чтобы понимать,
  кто что менял, а не просто затирать;
* при нажатии кнопки сравниваются три версии каждого файла — своя, чужая
  и теневая — и сводятся правилом из `merge.py`;
* спорный файл никогда не теряется: своё остаётся, чужое ложится рядом
  отдельным файлом с пометкой.

Токен хранится обычной строкой в настройках. Это не сейф, поэтому выпускать
его надо узким — с правом на один-единственный репозиторий.
"""

from __future__ import annotations

import base64
import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path

from .merge import merge

API = "https://api.github.com"

# Синхронизация написана и покрыта проверками, но по живой сети не гонялась
# ни разу. Пока это так, кнопка и настройки показываются, но не работают:
# ошибка здесь портит чужие файлы, а не рисует кривую кнопку.
#
# Разморозка — одна строка: поставить False. То же самое есть в Kotlin,
# в Sync.kt, и снимать надо обе разом, иначе телефон и компьютер разойдутся.
FROZEN = True


@dataclass
class Report:
    """Что произошло за одну синхронизацию — показывается человеку."""
    uploaded: list[str] = field(default_factory=list)
    downloaded: list[str] = field(default_factory=list)
    merged: list[str] = field(default_factory=list)
    deleted_here: list[str] = field(default_factory=list)
    deleted_there: list[str] = field(default_factory=list)
    conflicts: list[str] = field(default_factory=list)
    error: str | None = None

    @property
    def changed(self) -> int:
        return (len(self.uploaded) + len(self.downloaded) + len(self.merged)
                + len(self.deleted_here) + len(self.deleted_there))


class GitHub:
    """Тонкая обёртка над сетевым обращением. Ничего лишнего."""

    def __init__(self, repo: str, token: str, branch: str = "main"):
        self.repo = repo.strip().strip("/")
        self.token = token.strip()
        self.branch = branch or "main"

    def _call(self, method: str, path: str, body: dict | None = None):
        url = f"{API}{path}"
        data = json.dumps(body).encode("utf-8") if body is not None else None
        req = urllib.request.Request(url, data=data, method=method)
        req.add_header("Authorization", f"Bearer {self.token}")
        req.add_header("Accept", "application/vnd.github+json")
        req.add_header("X-GitHub-Api-Version", "2022-11-28")
        if data is not None:
            req.add_header("Content-Type", "application/json")
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read()
        return json.loads(raw) if raw else {}

    def check(self) -> str | None:
        """Проверка связи. Возвращает описание беды или None, если всё хорошо."""
        try:
            self._call("GET", f"/repos/{self.repo}")
            return None
        except urllib.error.HTTPError as e:
            if e.code == 401:
                return "ключ не подошёл"
            if e.code == 404:
                return "репозиторий не найден или ключ не даёт к нему доступа"
            return f"GitHub ответил {e.code}"
        except OSError as e:
            return f"нет связи: {e}"

    def tree(self) -> dict[str, str]:
        """Все файлы .md в репозитории: путь → отпечаток."""
        try:
            data = self._call("GET", f"/repos/{self.repo}/git/trees/{self.branch}?recursive=1")
        except urllib.error.HTTPError as e:
            if e.code == 409:       # репозиторий пустой, веток ещё нет
                return {}
            raise
        return {
            n["path"]: n["sha"]
            for n in data.get("tree", [])
            if n.get("type") == "blob" and n["path"].lower().endswith(".md")
        }

    def read(self, path: str) -> str:
        data = self._call("GET", f"/repos/{self.repo}/contents/{_q(path)}?ref={self.branch}")
        return base64.b64decode(data["content"]).decode("utf-8", "replace")

    def write(self, path: str, text: str, sha: str | None, message: str) -> str:
        body = {
            "message": message,
            "content": base64.b64encode(text.encode("utf-8")).decode("ascii"),
            "branch": self.branch,
        }
        if sha:
            body["sha"] = sha
        data = self._call("PUT", f"/repos/{self.repo}/contents/{_q(path)}", body)
        return data.get("content", {}).get("sha", "")

    def remove(self, path: str, sha: str, message: str) -> None:
        self._call("DELETE", f"/repos/{self.repo}/contents/{_q(path)}",
                   {"message": message, "sha": sha, "branch": self.branch})


def _q(path: str) -> str:
    return urllib.request.quote(path)


class Sync:
    def __init__(self, folder: Path, state_dir: Path, gh: GitHub, device: str = "компьютер"):
        self.folder = Path(folder)
        self.base_dir = Path(state_dir) / "base"
        self.gh = gh
        self.device = device

    # ——— теневая копия ———

    def _base_path(self, rel: str) -> Path:
        return self.base_dir / rel

    def _base_read(self, rel: str) -> str | None:
        p = self._base_path(rel)
        try:
            return p.read_text(encoding="utf-8")
        except OSError:
            return None

    def _base_write(self, rel: str, text: str) -> None:
        p = self._base_path(rel)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")

    def _base_drop(self, rel: str) -> None:
        try:
            self._base_path(rel).unlink()
        except OSError:
            pass

    # ——— свои файлы ———

    def _local(self) -> dict[str, str]:
        out: dict[str, str] = {}
        for dirpath, dirnames, filenames in os.walk(self.folder):
            dirnames[:] = [d for d in dirnames if not d.startswith(".")]
            for f in filenames:
                if not f.lower().endswith(".md") or f.startswith("."):
                    continue
                p = Path(dirpath) / f
                rel = str(p.relative_to(self.folder))
                try:
                    out[rel] = p.read_text(encoding="utf-8")
                except OSError:
                    pass
        return out

    def _write_local(self, rel: str, text: str) -> None:
        p = self.folder / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")

    # ——— главное ———

    def run(self) -> Report:
        r = Report()
        problem = self.gh.check()
        if problem:
            r.error = problem
            return r

        try:
            remote = self.gh.tree()
            local = self._local()
        except (urllib.error.HTTPError, OSError) as e:
            r.error = f"не получилось прочитать репозиторий: {e}"
            return r

        for rel in sorted(set(local) | set(remote)):
            try:
                self._one(rel, local.get(rel), remote.get(rel), r)
            except (urllib.error.HTTPError, OSError) as e:
                r.error = f"{rel}: {e}"
                return r
        return r

    def _one(self, rel: str, mine: str | None, remote_sha: str | None, r: Report) -> None:
        base = self._base_read(rel)
        theirs = self.gh.read(rel) if remote_sha else None
        msg = f"MathMark: {self.device}"

        # файла нет у меня
        if mine is None:
            if base is not None and theirs is not None and theirs == base:
                self.gh.remove(rel, remote_sha, msg)     # я его удалил — удаляем и там
                self._base_drop(rel)
                r.deleted_there.append(rel)
            elif theirs is not None:
                self._write_local(rel, theirs)           # он появился на той стороне
                self._base_write(rel, theirs)
                r.downloaded.append(rel)
            return

        # файла нет на той стороне
        if theirs is None:
            if base is not None:
                os.remove(self.folder / rel)             # его удалили там
                self._base_drop(rel)
                r.deleted_here.append(rel)
            else:
                sha = self.gh.write(rel, mine, None, msg)
                self._base_write(rel, mine)
                r.uploaded.append(rel)
            return

        # есть с обеих сторон
        text, conflict = merge(base, mine, theirs)
        if conflict:
            spare = rel[:-3] + " (спор).md"
            self._write_local(spare, theirs)
            r.conflicts.append(rel)
            return

        if text != mine:
            self._write_local(rel, text)
        if text != theirs:
            self.gh.write(rel, text, remote_sha, msg)
        self._base_write(rel, text)

        if text != mine and text != theirs:
            r.merged.append(rel)
        elif text != mine:
            r.downloaded.append(rel)
        elif text != theirs:
            r.uploaded.append(rel)
