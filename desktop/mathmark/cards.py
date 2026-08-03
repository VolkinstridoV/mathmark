"""
Карточки-скрипты: формула, поля, кнопка «Решить», пошаговый разбор.

Карточка — описание в `shared/cards/catalog.json`, а не отдельная программа:
какие поля просить, что проверить, что посчитать, какие шаги показать. Считает
всё один движок. Так формула добавляется десятком строк текста, не трогая код,
и пополнять каталог может кто угодно через GitHub.

Про доверие — без прикрас. Выражения карточки **вычисляются**, а значит это
всё-таки код, пусть и на крохотном языке. Поэтому граница проведена не внутри
движка, а снаружи: каталог едет вместе с программой из репозитория и проходит
такую же проверку, как любой другой код. Ничего не подгружается на ходу и не
берётся из чужой папки. А вот то, что человек набирает в поля, — чужое, и
разбирается отдельно и строго, в `parse_value`.

Разбор идёт **одной математикой, без единого слова**: человек, взявший формулу
дисперсии, знает, что это дисперсия, ему лень расписывать её руками. Поэтому
шаги не переводятся ни на один язык — переводится только оболочка.

Язык шагов маленький и весь здесь:

    {"tex": "..."}              строка разбора; @имя подставляет значение
    {"set": "D = b**2-4*a*c"}   посчитать и запомнить
    {"set": "...", "keep": true} посчитать, но не упрощать: разложение на
                                множители иначе схлопнется обратно в число
    {"when": "D > 0", "steps":[…]}   ветка, если условие верно
    {"else": [...]}             иначе

Проверка полей — список `need`: условие и то, что показать человеку, если оно
нарушено. Показывается математикой (`a \\neq 0`), а не словами.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

import sympy
from sympy.parsing.sympy_parser import (  # noqa: E402
    convert_xor,
    implicit_multiplication_application,
    parse_expr,
    standard_transformations,
)

# convert_xor обязателен: без него «x^3» разбирается как исключающее ИЛИ —
# в Python «^» именно это и значит, — и поле молча объявляется негодным.
TRANSFORMS = standard_transformations + (implicit_multiplication_application, convert_xor)

# Что человеку вообще позволено набрать в поле. Пускаем цифры, буквы, точку,
# запятую, скобки, знаки и пробелы — и ничего больше. Точки и подчёркивания
# закрывают доступ к внутренностям Python через разбор выражения.
SAFE = re.compile(r"^[0-9A-Za-zА-Яа-я+\-*/^().,;=<>\s|!√π]*$")
BANNED = ("_", "lambda", "import", "eval", "exec", "open", "os", "sys", "\\")

FUNCS = {
    name: getattr(sympy, name)
    for name in ("sqrt", "sin", "cos", "tan", "cot", "asin", "acos", "atan",
                 "log", "ln", "exp", "Abs", "factorial", "binomial", "pi", "E")
    if hasattr(sympy, name)
}
FUNCS["ln"] = sympy.log
FUNCS["abs"] = sympy.Abs


class BadInput(Exception):
    """Человек набрал то, что разобрать нельзя. Не поломка, а обычное дело."""


def parse_value(raw: str):
    """
    Строка из поля — в математическое выражение.

    Намеренно строго: сначала смотрим на сами символы, только потом отдаём
    разборщику. `sympify` на чужой строке умеет выполнять код, поэтому до него
    доходит лишь то, что прошло проверку.
    """
    s = (raw or "").strip().replace(",", ".").replace("√", "sqrt").replace("π", "pi")
    if not s:
        raise BadInput("пусто")
    if not SAFE.match(s) or any(b in s.lower() for b in BANNED):
        raise BadInput("недопустимые знаки")
    try:
        return parse_expr(s, local_dict=dict(FUNCS), transformations=TRANSFORMS,
                          evaluate=True)
    except Exception as e:  # разборщик бросает что угодно
        raise BadInput(str(e)) from e


def parse_list(raw: str) -> list:
    """Поле-набор: «2, 4, 4, 6» — для дисперсии, среднего и им подобных."""
    parts = [p for p in re.split(r"[;,\s]+", (raw or "").strip()) if p]
    if not parts:
        raise BadInput("пусто")
    return [parse_value(p) for p in parts]


@dataclass
class Field:
    id: str
    label: str = ""
    kind: str = "num"          # num | list | expr
    default: str = ""

    @staticmethod
    def of(d: dict) -> "Field":
        return Field(id=d["id"], label=d.get("l", d["id"]),
                     kind=d.get("t", "num"), default=d.get("d", ""))


@dataclass
class Card:
    id: str
    section: str
    names: dict
    keys: dict
    form: str                       # как формула выглядит на карточке
    fields: list[Field]
    need: list[dict] = field(default_factory=list)
    steps: list[dict] = field(default_factory=list)

    @staticmethod
    def of(d: dict) -> "Card":
        return Card(
            id=d["id"], section=d.get("s", ""), names=d.get("n", {}),
            keys=d.get("k", {}), form=d.get("form", ""),
            fields=[Field.of(f) for f in d.get("f", [])],
            need=d.get("need", []), steps=d.get("steps", []),
        )

    def name(self, lang: str) -> str:
        return self.names.get(lang) or self.names.get("en") or self.id


@dataclass
class Solved:
    ok: bool
    lines: list[str] = field(default_factory=list)   # готовые строки LaTeX
    blocked: list[str] = field(default_factory=list)  # нарушенные условия
    bad: list[str] = field(default_factory=list)      # поля, что не разобрались


def _env(card: Card, raw: dict[str, str]) -> tuple[dict, list[str]]:
    env: dict[str, Any] = {}
    bad: list[str] = []
    for f in card.fields:
        text = raw.get(f.id, "")
        try:
            if f.kind == "list":
                vals = parse_list(text)
                if any(not v.is_number for v in vals):
                    raise BadInput("не число")
                env[f.id] = vals
            else:
                v = parse_value(text)
                # Поле числа обязано быть числом: иначе «хрень» разбиралась бы
                # в произведение букв и карточка честно «решала» бессмыслицу.
                if f.kind == "num" and not v.is_number:
                    raise BadInput("не число")
                env[f.id] = v
        except BadInput:
            bad.append(f.id)
    return env, bad


def _num(env: dict) -> dict:
    """Наборы отдаём разборщику как sympy-списки, остальное как есть."""
    out = {}
    for k, v in env.items():
        out[k] = sympy.Array(v) if isinstance(v, list) else v
    return out


# Что доступно выражениям каталога сверх самой sympy. Наборы значений живут
# обычными списками, поэтому нужны len/sum и перебор — без них дисперсию и
# наименьшие квадраты не посчитать.
HELPERS = {"len": len, "sum": sum, "range": range, "abs": abs,
           "min": min, "max": max, "sorted": sorted, "list": list}


def _eval(expr: str, env: dict):
    """
    Выражение из каталога. Каталог свой и проверенный, но встроенные Python
    отсюда всё равно убраны: лишняя дверь, которая никому не нужна.
    """
    scope = {"__builtins__": {}}
    scope.update(sympy.__dict__)
    scope.update(HELPERS)
    # Ходовые буквы должны быть именно математическими символами: без этого
    # «diff(f, x)» падало на неизвестном имени, и весь разбор выходил пустым.
    scope.update({c: sympy.Symbol(c) for c in ("x", "y", "z", "t", "u", "v", "w")})
    scope.update(env)
    return eval(expr, scope)  # noqa: S307 — выражение из своего же репозитория


EQ = re.compile(r"^(?P<l>[^<>=!]+?)\s*=\s*(?P<r>[^<>=!]+)$")


def _check(cond: str, env: dict) -> bool:
    """
    Условие карточки. Одиночное «=» читается как равенство, а не как
    присваивание: в описании естественно писать «D = 0», и молчаливое
    «ложь» вместо равенства уводило разбор не в ту ветку.
    """
    m = EQ.match(cond.strip())
    if m:
        cond = f"Eq({m.group('l')}, {m.group('r')})"
    try:
        return bool(_eval(cond, env))
    except Exception:
        return False


# Подстановка помечается собачкой, а не фигурными скобками: скобки — рабочий
# знак LaTeX, и «\frac{b}{a}» подставлялось бы как значения, превращая формулу
# в «\frac-93». Собачка в математике не встречается.
TOKEN = re.compile(r"@([A-Za-z][A-Za-z0-9]*)")


def _fill(tex: str, env: dict) -> str:
    """@имя → значение в LaTeX. Незнакомое имя остаётся как было."""
    def sub(m):
        key = m.group(1)
        if key not in env:
            return m.group(0)
        v = env[key]
        if isinstance(v, list):
            return ",\\ ".join(sympy.latex(x) for x in v)
        return sympy.latex(v)
    return TOKEN.sub(sub, tex)


def _walk(steps: list[dict], env: dict, out: list[str]) -> None:
    for st in steps:
        if "set" in st:
            name, _, expr = st["set"].partition("=")
            val = _eval(expr.strip(), env)
            if st.get("keep") or isinstance(val, (list, tuple)):
                env[name.strip()] = val
            else:
                env[name.strip()] = sympy.simplify(val)
        if "when" in st:
            if _check(st["when"], env):
                _walk(st.get("steps", []), env, out)
            elif st.get("else"):
                _walk(st["else"], env, out)
            continue
        if "tex" in st:
            out.append(_fill(st["tex"], env))


def solve(card: Card, raw: dict[str, str]) -> Solved:
    """
    Посчитать карточку. Ничего не бросает: негодный ввод — обычное дело,
    про него надо не падать, а погасить кнопку и показать, что не так.
    """
    env, bad = _env(card, raw)
    if bad:
        return Solved(ok=False, bad=bad)

    blocked = [c.get("show", "") for c in card.need if not _check(c.get("if", "True"), env)]
    if blocked:
        return Solved(ok=False, blocked=blocked)

    out: list[str] = []
    try:
        _walk(card.steps, dict(env), out)
    except Exception:
        return Solved(ok=False, blocked=[])
    return Solved(ok=True, lines=out)


def as_markdown(card: Card, raw: dict[str, str], res: Solved) -> str:
    """
    Решение в том же виде, в каком живут бумажки: обычный markdown.

    Сверху формула, из которой считали, — чтобы было видно, чем решали, не
    открывая ничего. Дальше только математика, ни одного слова.
    """
    parts = []
    if card.form:
        parts.append("$$\n" + _fill(card.form, {}) + "\n$$")
    for line in res.lines:
        parts.append("$$\n" + line + "\n$$")
    return "\n\n".join(parts)
