"""
Проверки синхронизации без единого обращения в сеть: вместо GitHub — заглушка,
которая держит файлы в памяти и ведёт себя так же.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest  # noqa: E402

from mathmark.sync import Sync  # noqa: E402


class FakeGitHub:
    """Тот же набор действий, что у настоящего, только всё в памяти."""

    def __init__(self, files: dict[str, str] | None = None):
        self.files = dict(files or {})
        self.log: list[str] = []

    def check(self):
        return None

    def tree(self):
        return {p: f"sha-{p}-{len(t)}" for p, t in self.files.items()}

    def read(self, path):
        return self.files[path]

    def write(self, path, text, sha, message):
        self.files[path] = text
        self.log.append(f"write {path}")
        return f"sha-{path}-{len(text)}"

    def remove(self, path, sha, message):
        del self.files[path]
        self.log.append(f"remove {path}")


@pytest.fixture()
def setup(tmp_path):
    folder = tmp_path / "math"
    folder.mkdir()
    state = tmp_path / "state"
    return folder, state


def make(folder, state, remote_files=None, device="компьютер"):
    gh = FakeGitHub(remote_files)
    return Sync(folder, state, gh, device), gh


def write(folder, rel, text):
    p = Path(folder) / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")


def test_новый_свой_файл_уезжает(setup):
    folder, state = setup
    write(folder, "шпора.md", "- [ ] раз\n")
    sync, gh = make(folder, state)

    r = sync.run()
    assert r.uploaded == ["шпора.md"]
    assert gh.files["шпора.md"] == "- [ ] раз\n"


def test_новый_чужой_файл_приезжает(setup):
    folder, state = setup
    sync, gh = make(folder, state, {"линал.md": "- ( ) Ряды\n"})

    r = sync.run()
    assert r.downloaded == ["линал.md"]
    assert (folder / "линал.md").read_text(encoding="utf-8") == "- ( ) Ряды\n"


def test_вложенные_папки_переносятся(setup):
    folder, state = setup
    write(folder, "Линал/собственные.md", "- [ ] раз\n")
    sync, gh = make(folder, state)

    sync.run()
    assert "Линал/собственные.md" in gh.files


def test_отметки_с_двух_сторон_сводятся(setup):
    folder, state = setup
    write(folder, "ф.md", "- [ ] раз\n- ( ) два\n")
    sync, gh = make(folder, state)
    sync.run()                                    # теневая копия появилась

    write(folder, "ф.md", "- [x] раз\n- ( ) два\n")      # отметил у себя
    gh.files["ф.md"] = "- [ ] раз\n- (x) два\n"          # и на той стороне

    r = sync.run()
    assert r.merged == ["ф.md"]
    assert (folder / "ф.md").read_text(encoding="utf-8") == "- [x] раз\n- (x) два\n"
    assert gh.files["ф.md"] == "- [x] раз\n- (x) два\n"


def test_спор_об_отметке_решается_в_пользу_продвинутого(setup):
    folder, state = setup
    write(folder, "ф.md", "- [ ] раз\n")
    sync, gh = make(folder, state)
    sync.run()

    write(folder, "ф.md", "- [~] раз\n")
    gh.files["ф.md"] = "- [x] раз\n"

    r = sync.run()
    assert not r.conflicts
    assert (folder / "ф.md").read_text(encoding="utf-8") == "- [x] раз\n"


def test_свой_файл_удалён_значит_удаляется_и_там(setup):
    folder, state = setup
    write(folder, "ф.md", "- [ ] раз\n")
    sync, gh = make(folder, state)
    sync.run()

    (folder / "ф.md").unlink()
    r = sync.run()
    assert r.deleted_there == ["ф.md"]
    assert "ф.md" not in gh.files


def test_чужой_файл_удалён_значит_удаляется_и_здесь(setup):
    folder, state = setup
    write(folder, "ф.md", "- [ ] раз\n")
    sync, gh = make(folder, state)
    sync.run()

    del gh.files["ф.md"]
    r = sync.run()
    assert r.deleted_here == ["ф.md"]
    assert not (folder / "ф.md").exists()


def test_спор_о_тексте_ничего_не_теряет(setup):
    folder, state = setup
    write(folder, "ф.md", "- [ ] раз\n")
    sync, gh = make(folder, state)
    sync.run()

    write(folder, "ф.md", "- [ ] раз по-моему\n")
    gh.files["ф.md"] = "- [ ] раз по-ихнему\n"

    r = sync.run()
    assert r.conflicts == ["ф.md"]
    assert (folder / "ф.md").read_text(encoding="utf-8") == "- [ ] раз по-моему\n"
    assert (folder / "ф (спор).md").read_text(encoding="utf-8") == "- [ ] раз по-ихнему\n"


def test_повторная_синхронизация_ничего_не_делает(setup):
    folder, state = setup
    write(folder, "ф.md", "- [ ] раз\n")
    sync, gh = make(folder, state)
    sync.run()
    gh.log.clear()

    r = sync.run()
    assert r.changed == 0
    assert gh.log == []


def test_беда_со_связью_видна_человеку(setup):
    folder, state = setup
    sync, gh = make(folder, state)
    gh.check = lambda: "ключ не подошёл"

    r = sync.run()
    assert r.error == "ключ не подошёл"
