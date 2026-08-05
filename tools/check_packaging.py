#!/usr/bin/env python3
"""
Проверка рецептов сборки: попадает ли в пакет всё, что нужно программе.

Эта мина срабатывала дважды подряд и оба раза молча. Сперва в пакет не
клалась `shared/board` — у поставивших пакетом доска открывалась пустым
окном. Потом ровно то же случилось с `shared/cards`, и каталог формул оказался
бы пуст. Из исходников всё работало, поэтому заметить было нечем.

Здесь сверяется простое: каждая папка `shared/` должна быть перечислена и в
PKGBUILD, и в рецепте Flatpak; версии в них должны совпадать между собой, с
кодом и с `.SRCINFO`; а сторонние библиотеки, без которых программа не
работает, должны быть объявлены зависимостями.

Запуск: python3 tools/check_packaging.py
"""

from __future__ import annotations

import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
PKGBUILD = ROOT / "packaging" / "aur" / "PKGBUILD"
SRCINFO = ROOT / "packaging" / "aur" / ".SRCINFO"
FLATPAK = ROOT / "desktop" / "io.github.volkinstridov.MathMark.yml"
INIT = ROOT / "desktop" / "mathmark" / "__init__.py"
GRADLE = ROOT / "android" / "app" / "build.gradle.kts"

# Что программа берёт снаружи и без чего перестаёт работать. Слева — как
# пишется в исходниках, справа — как называется пакет в Arch.
OUTSIDE = {"sympy": "python-sympy", "gi": "python-gobject"}


def main() -> int:
    problems: list[str] = []
    pkg = PKGBUILD.read_text(encoding="utf-8")
    flat = FLATPAK.read_text(encoding="utf-8")
    srcinfo = SRCINFO.read_text(encoding="utf-8")

    # 1. всё общее — в обоих пакетах
    folders = sorted(p.name for p in (ROOT / "shared").iterdir() if p.is_dir())
    for where, text in (("PKGBUILD", pkg), ("рецепте Flatpak", flat)):
        listed = set(re.findall(r"shared/(\w+)", text))
        for f in folders:
            if f not in listed:
                problems.append(f"shared/{f} не копируется в пакет — нет в {where}")

    # 2. версии сходятся
    def one(pattern: str, text: str, name: str) -> str:
        m = re.search(pattern, text)
        if not m:
            problems.append(f"не нашёл версию в {name}")
            return ""
        return m.group(1)

    code = one(r'__version__ = "([^"]+)"', INIT.read_text(encoding="utf-8"), "коде")
    vers = {
        "PKGBUILD": one(r"(?m)^pkgver=(\S+)", pkg, "PKGBUILD"),
        ".SRCINFO": one(r"pkgver = (\S+)", srcinfo, ".SRCINFO"),
        "android": one(r'versionName = "([^"]+)"', GRADLE.read_text(encoding="utf-8"), "android"),
        "рецепте Flatpak": one(r"tags/v(\S+?)\.tar\.gz", flat, "рецепте Flatpak"),
    }
    for where, v in vers.items():
        if v and code and v != code:
            problems.append(f"версия в {where} — {v}, а в коде {code}")

    # 2б. версия в окне «о программе». Мина того же рода: строка лежит в
    # переводах, её никто не пересобирает при выпуске, и она молча отстаёт —
    # так до 1.4 в настройках обеих версий висело «MathMark 1.0.2».
    for path in sorted((ROOT / "shared" / "i18n").glob("*.json")):
        m = re.search(r'"settings\.version":\s*"MathMark ([^"]+)"',
                      path.read_text(encoding="utf-8"))
        if not m:
            problems.append(f"не нашёл settings.version в {path.name}")
        elif code and m.group(1) != code:
            problems.append(
                f"версия в окне «о программе» ({path.name}) — "
                f"{m.group(1)}, а в коде {code}")

    # 3. отпечаток архива один и тот же в трёх местах
    shas = {
        "PKGBUILD": one(r"sha256sums=\('([0-9a-f]+)'\)", pkg, "PKGBUILD"),
        ".SRCINFO": one(r"sha256sums = ([0-9a-f]+)", srcinfo, ".SRCINFO"),
    }
    m = re.search(r"tags/v[\d.]+\.tar\.gz\s+sha256: ([0-9a-f]+)", flat)
    shas["рецепте Flatpak"] = m.group(1) if m else ""
    uniq = {v for v in shas.values() if v}
    if len(uniq) > 1:
        problems.append("отпечаток архива разный: " +
                        ", ".join(f"{k} {v[:12]}…" for k, v in shas.items()))

    # 4. сторонние библиотеки объявлены
    used = set()
    for py in (ROOT / "desktop" / "mathmark").glob("*.py"):
        text = py.read_text(encoding="utf-8")
        for mod, package in OUTSIDE.items():
            if re.search(rf"^\s*(import|from)\s+{mod}\b", text, re.M):
                used.add(package)
    for package in sorted(used):
        if package not in pkg:
            problems.append(f"{package} используется, но не объявлен в depends PKGBUILD")
        if package not in srcinfo:
            problems.append(f"{package} используется, но не объявлен в .SRCINFO")
    if "sympy" in {p.stem for p in (ROOT / "desktop" / "mathmark").glob("*.py")} or "python-sympy" in used:
        if "sympy" not in flat:
            problems.append("sympy используется, но в рецепте Flatpak его нет — "
                            "в рантайме GNOME он не поставляется")

    print(f"папок в shared: {len(folders)}   версия: {code or '?'}   ошибок: {len(problems)}")
    if problems:
        print()
        for p in problems:
            print("  ✗", p)
        return 1
    print("\nрецепты сходятся: в пакет попадает всё, версии и отпечатки одинаковы")
    return 0


if __name__ == "__main__":
    sys.exit(main())
