/*
 * Проверка каталога записи: каждая запись должна рисоваться.
 *
 * Собирает текст каждой записи двумя способами — с пустыми квадратиками и с
 * заполненными полями — и отдаёт KaTeX. Любая ошибка разбора здесь означает,
 * что человек в программе увидит красную надпись вместо формулы.
 *
 * Запуск: node tools/check_catalog.js
 */
"use strict";
const fs = require("fs"), path = require("path");
const root = path.join(__dirname, "..");
const katex = require(path.join(root, "shared/reader/katex/katex.min.js"));
const cat = JSON.parse(fs.readFileSync(path.join(root, "shared/write/catalog.json"), "utf8"));

/* Тот же сборщик, что в write.js, но без окна. */
const SLOT = "{\\color{#7C3AED}\\square}", HOLE = "\\square";
let vals = {};

function field(it, id) { return it.f.find(f => f.id === id) || null; }
function num(it, id) { const v = vals[id]; const f = field(it, id); return typeof v === "number" ? v : (f ? f.d : 1); }
function cell(v, h) { return (v && String(v).trim()) ? String(v) : h; }
function val(it, id, h) {
  const f = field(it, id), v = vals[id];
  if (!f) return h;
  if (f.t === "choice") return v || f.d;
  if (f.t === "int") return String(typeof v === "number" ? v : f.d);
  if (f.t === "grid" || f.t === "list") return v;
  return (v && String(v).trim()) ? String(v) : h;
}
function listArr(it, id, h) { return (vals[id] || []).map(c => cell(c, h)); }
function gridText(it, id, h) {
  return (vals[id] || []).map(r => r.map(c => cell(c, h)).join(" & ")).join(" \\\\ ");
}
function listText(it, id, h) { return listArr(it, id, h).join(field(it, id).sep); }

const SPECIAL = {
  "#kind:a,b": (it, h) => {
    const L = { "[]": ["[", "]"], "()": ["(", ")"], "[)": ["[", ")"], "(]": ["(", "]"] }[val(it, "kind", h)] || ["(", ")"];
    return "\\left" + L[0] + " " + val(it, "a", h) + ", " + val(it, "b", h) + " \\right" + L[1];
  },
  "#veccoord": (it, h) => {
    const a = val(it, "a", h), c = listArr(it, "cells", h);
    return val(it, "shape", h) === "col"
      ? "\\vec{" + a + "} = \\begin{pmatrix} " + c.join(" \\\\ ") + " \\end{pmatrix}"
      : "\\vec{" + a + "} = \\left( " + c.join(", ") + " \\right)";
  },
  "#dotprod": (it, h) => {
    const m = val(it, "m", h), a = "\\vec{" + val(it, "a", h) + "}", b = "\\vec{" + val(it, "b", h) + "}";
    if (m === "angle") return "\\left\\langle " + a + ", " + b + " \\right\\rangle";
    if (m === "paren") return "\\left( " + a + ", " + b + " \\right)";
    return a + " \\cdot " + b;
  },
  "#conjop": (it, h) => {
    const op = val(it, "op", h), z = val(it, "z", h);
    if (op === "bar") return "\\overline{" + z + "}";
    if (op === "abs") return "\\left| " + z + " \\right|";
    return op + " " + z;
  },
  "#expop": (it, h) => {
    const op = val(it, "op", h), x = val(it, "x", h), y = val(it, "y", h);
    if (op === "E") return "E\\left[ " + x + " \\right]";
    if (op === "D") return "D\\left( " + x + " \\right)";
    if (op === "cov") return "\\operatorname{Cov}\\left( " + x + ", " + y + " \\right)";
    return "\\sigma\\left( " + x + " \\right)";
  },
  "#permop": (it, h) => {
    const op = val(it, "op", h), n = val(it, "n", h), k = val(it, "k", h);
    return op === "P" ? "P_{" + n + "}" : op + "_{" + n + "}^{" + k + "}";
  },
  "#bracetpl": (it, h) => {
    const m = val(it, "m", h);
    return m + "{" + val(it, "a", h) + "}" + (m === "\\underbrace" ? "_" : "^") +
      "{\\text{" + val(it, "t", h) + "}}";
  },
  "#bigparen": (it, h) => {
    const P = { "()": ["(", ")"], "[]": ["[", "]"], "{}": ["\\{", "\\}"], "||": ["|", "|"],
                "<>": ["\\langle", "\\rangle"], "floor": ["\\lfloor", "\\rfloor"] }[val(it, "br", h)] || ["(", ")"];
    return "\\left" + P[0] + " " + val(it, "a", h) + " \\right" + P[1];
  },
  "#piecerows": (it, h) => {
    const v = listArr(it, "vals", h), c = listArr(it, "conds", h), out = [];
    for (let i = 0; i < v.length; i++) out.push(v[i] + ", & \\text{" + (c[i] || h) + "}");
    return out.join(" \\\\ ");
  },
  "#alignrows": (it, h) => {
    const l = listArr(it, "lhs", h), r = listArr(it, "rhs", h), out = [];
    for (let i = 0; i < l.length; i++) out.push(l[i] + " &= " + (r[i] || h));
    return out.join(" \\\\ ");
  },
  "#augrows": (it, h) => {
    const rows = vals.cells || [], rhs = listArr(it, "rhs", h), out = [];
    for (let i = 0; i < rows.length; i++)
      out.push(rows[i].map(c => cell(c, h)).join(" & ") + " & " + (rhs[i] || h));
    return out.join(" \\\\ ");
  },
  "#colspec": (it) => "c".repeat(num(it, "c")),
  "#alspec": (it, h) => val(it, "al", h).repeat(num(it, "c"))
};

function build(it, hole) {
  let s = it.tpl;
  for (const key in SPECIAL) if (s.includes(key)) s = s.split(key).join(SPECIAL[key](it, hole));
  return s.replace(/#([a-z][a-z0-9]*)/g, (whole, id) => {
    const f = field(it, id);
    if (!f) return whole;
    if (f.t === "grid") return gridText(it, id, hole);
    if (f.t === "list") return listText(it, id, hole);
    return val(it, id, hole);
  });
}

function reset(it, filled) {
  vals = {};
  it.f.forEach(f => {
    if (f.t === "int") vals[f.id] = f.d;
    else if (f.t === "choice") vals[f.id] = f.d;
    else if (f.t === "grid" || f.t === "list") vals[f.id] = [];
    else vals[f.id] = filled ? (f.d || "1") : (f.d || "");
  });
  it.f.forEach(f => {
    if (f.t === "grid") {
      const r = num(it, f.rows), c = num(it, f.cols), out = [];
      for (let i = 0; i < r; i++) out.push(new Array(c).fill(filled ? "1" : ""));
      vals[f.id] = out;
    } else if (f.t === "list") {
      vals[f.id] = new Array(num(it, f.n)).fill(filled ? "1" : "");
    }
  });
}

let bad = 0, checked = 0;
const seen = new Set(), sections = new Set(cat.sections.map(s => s.id));

for (const it of cat.items) {
  if (seen.has(it.id)) { console.log("ПОВТОР id:", it.id); bad++; }
  seen.add(it.id);
  if (!sections.has(it.s)) { console.log("НЕТ РАЗДЕЛА:", it.id, "→", it.s); bad++; }
  for (const l of ["en", "ru", "es"]) {
    if (!it.n[l]) { console.log("НЕТ ИМЕНИ", l, ":", it.id); bad++; }
    if (!it.k[l]) { console.log("НЕТ СЛОВ ПОИСКА", l, ":", it.id); bad++; }
  }
  for (const f of it.f)
    if (!cat.labels[f.l]) { console.log("НЕТ ПОДПИСИ:", it.id, "→", f.l); bad++; }

  // все варианты выбора: каждый должен рисоваться, а не только первый
  const choices = it.f.filter(f => f.t === "choice");
  const variants = [];
  reset(it, true); variants.push({ tag: "заполнено", set: {} });
  reset(it, false); variants.push({ tag: "пусто", set: {} });
  for (const f of choices)
    for (const o of f.o) variants.push({ tag: "выбор " + f.id + "=" + o.v, set: { [f.id]: o.v } });

  for (const v of variants) {
    reset(it, true);
    Object.assign(vals, v.set);
    it.f.forEach(f => {
      if (f.t === "grid") { const r = num(it, f.rows), c = num(it, f.cols), o = [];
        for (let i = 0; i < r; i++) o.push(new Array(c).fill("1")); vals[f.id] = o; }
      else if (f.t === "list") vals[f.id] = new Array(num(it, f.n)).fill("1");
    });
    for (const hole of [SLOT, HOLE]) {
      const text = build(it, hole);
      checked++;
      try {
        katex.renderToString(text, { displayMode: !!it.d, throwOnError: true, strict: false });
      } catch (e) {
        bad++;
        console.log("ОШИБКА:", it.id, "|", v.tag, "|", String(e.message).slice(0, 90));
        console.log("        ", text.slice(0, 140));
      }
    }
    if (build(it, HOLE).includes("#")) {
      const leftover = build(it, HOLE).match(/#[a-z]+/g);
      if (leftover && leftover.some(x => x !== "#7C3AED")) {
        console.log("НЕ ПОДСТАВЛЕНО:", it.id, leftover.join(" ")); bad++;
      }
    }
  }
}

console.log("\nзаписей: " + cat.items.length + "  проверок: " + checked +
            "  ошибок: " + bad);
process.exit(bad ? 1 : 0);
