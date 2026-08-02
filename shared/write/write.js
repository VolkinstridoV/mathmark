/*
 * Помогалка по записи математики.
 *
 * Выбираешь, что нужно написать, заполняешь квадратики — получаешь готовый
 * текст. Знать LaTeX не нужно: его пишет эта страница.
 *
 * Каталог лежит рядом в catalog.json и передаётся сюда снаружи: страница
 * открыта из файла, а из файла запросы наружу браузер не пускает.
 *
 * Одна и та же страница работает и на компьютере, и на телефоне.
 */
(function () {
  "use strict";

  var SLOT = "{\\color{#7C3AED}\\square}";   // пустой квадратик в показе
  var HOLE = "\\square";                     // он же в готовом тексте

  var cat = null, lang = "ru", sel = null, vals = {}, open = {}, shownIds = [];
  var UI = {
    "write.search": "Поиск",
    "write.pick": "Выберите, что нужно записать",
    "write.hint": "Слева — разделы и поиск. Заполните поля — текст соберётся сам.",
    "write.copy": "Скопировать",
    "write.copyPlain": "Без долларов",
    "write.copied": "Скопировано",
    "write.none": "Ничего не нашлось"
  };

  function t(k) { return UI[k] || k; }
  function el(id) { return document.getElementById(id); }
  function name(o) { return (o.n && (o.n[lang] || o.n.en)) || o.id; }

  function send(n, payload) {
    if (window.Android && typeof window.Android[n] === "function") window.Android[n](payload);
    else if (window.webkit && webkit.messageHandlers && webkit.messageHandlers.mathmark)
      webkit.messageHandlers.mathmark.postMessage(JSON.stringify({ name: n, payload: payload }));
  }

  // ─────────────────────── сборка текста ───────────────────────

  function item(id) {
    for (var i = 0; i < cat.items.length; i++) if (cat.items[i].id === id) return cat.items[i];
    return null;
  }
  function field(it, id) {
    for (var i = 0; i < it.f.length; i++) if (it.f[i].id === id) return it.f[i];
    return null;
  }
  function num(it, id) { var v = vals[id]; return typeof v === "number" ? v : (field(it, id) || {}).d || 1; }

  /* Значение поля или квадратик, если пусто. */
  function val(it, id, hole) {
    var f = field(it, id), v = vals[id];
    if (!f) return hole;
    if (f.t === "choice") return v || f.d;
    if (f.t === "int") return String(typeof v === "number" ? v : f.d);
    if (f.t === "grid" || f.t === "list") return v;
    return (v && String(v).trim()) ? String(v) : hole;
  }
  function cell(v, hole) { return (v && String(v).trim()) ? String(v) : hole; }

  function gridText(it, id, hole) {
    var rows = vals[id] || [];
    return rows.map(function (r) {
      return r.map(function (c) { return cell(c, hole); }).join(" & ");
    }).join(" \\\\ ");
  }
  function listText(it, id, hole) {
    var f = field(it, id), a = vals[id] || [];
    return a.map(function (c) { return cell(c, hole); }).join(f.sep);
  }
  function listArr(it, id, hole) {
    return (vals[id] || []).map(function (c) { return cell(c, hole); });
  }

  /* Особые случаи: то, что не собирается простой подстановкой. */
  var SPECIAL = {
    "#kind:a,b": function (it, h) {
      var k = val(it, "kind", h), a = val(it, "a", h), b = val(it, "b", h);
      var L = { "[]": ["[", "]"], "()": ["(", ")"], "[)": ["[", ")"], "(]": ["(", "]"] }[k] || ["(", ")"];
      return "\\left" + L[0] + " " + a + ", " + b + " \\right" + L[1];
    },
    "#veccoord": function (it, h) {
      var a = val(it, "a", h), c = listArr(it, "cells", h);
      if (val(it, "shape", h) === "col")
        return "\\vec{" + a + "} = \\begin{pmatrix} " + c.join(" \\\\ ") + " \\end{pmatrix}";
      return "\\vec{" + a + "} = \\left( " + c.join(", ") + " \\right)";
    },
    "#dotprod": function (it, h) {
      var m = val(it, "m", h), a = "\\vec{" + val(it, "a", h) + "}", b = "\\vec{" + val(it, "b", h) + "}";
      if (m === "angle") return "\\left\\langle " + a + ", " + b + " \\right\\rangle";
      if (m === "paren") return "\\left( " + a + ", " + b + " \\right)";
      return a + " \\cdot " + b;
    },
    "#conjop": function (it, h) {
      var op = val(it, "op", h), z = val(it, "z", h);
      if (op === "bar") return "\\overline{" + z + "}";
      if (op === "abs") return "\\left| " + z + " \\right|";
      return op + " " + z;
    },
    "#expop": function (it, h) {
      var op = val(it, "op", h), x = val(it, "x", h), y = val(it, "y", h);
      if (op === "E") return "E\\left[ " + x + " \\right]";
      if (op === "D") return "D\\left( " + x + " \\right)";
      if (op === "cov") return "\\operatorname{Cov}\\left( " + x + ", " + y + " \\right)";
      return "\\sigma\\left( " + x + " \\right)";
    },
    "#permop": function (it, h) {
      var op = val(it, "op", h), n = val(it, "n", h), k = val(it, "k", h);
      if (op === "P") return "P_{" + n + "}";
      return op + "_{" + n + "}^{" + k + "}";
    },
    "#bracetpl": function (it, h) {
      var m = val(it, "m", h), a = val(it, "a", h), x = val(it, "t", h);
      var mark = m === "\\underbrace" ? "_" : "^";
      return m + "{" + a + "}" + mark + "{\\text{" + x + "}}";
    },
    "#bigparen": function (it, h) {
      var b = val(it, "br", h), a = val(it, "a", h);
      var P = { "()": ["(", ")"], "[]": ["[", "]"], "{}": ["\\{", "\\}"],
                "||": ["|", "|"], "<>": ["\\langle", "\\rangle"],
                "floor": ["\\lfloor", "\\rfloor"] }[b] || ["(", ")"];
      return "\\left" + P[0] + " " + a + " \\right" + P[1];
    },
    "#piecerows": function (it, h) {
      var v = listArr(it, "vals", h), c = listArr(it, "conds", h), out = [];
      for (var i = 0; i < v.length; i++)
        out.push(v[i] + ", & \\text{" + (c[i] || h) + "}");
      return out.join(" \\\\ ");
    },
    "#alignrows": function (it, h) {
      var l = listArr(it, "lhs", h), r = listArr(it, "rhs", h), out = [];
      for (var i = 0; i < l.length; i++) out.push(l[i] + " &= " + (r[i] || h));
      return out.join(" \\\\ ");
    },
    "#augrows": function (it, h) {
      var rows = vals.cells || [], rhs = listArr(it, "rhs", h), out = [];
      for (var i = 0; i < rows.length; i++)
        out.push(rows[i].map(function (c) { return cell(c, h); }).join(" & ") + " & " + (rhs[i] || h));
      return out.join(" \\\\ ");
    },
    "#colspec": function (it) { return new Array(num(it, "c") + 1).join("c"); },
    "#alspec": function (it, h) { return new Array(num(it, "c") + 1).join(val(it, "al", h)); }
  };

  function build(preview) {
    var it = item(sel), hole = preview ? SLOT : HOLE, s = it.tpl;
    for (var key in SPECIAL)
      if (s.indexOf(key) >= 0) s = s.split(key).join(SPECIAL[key](it, hole));
    return s.replace(/#([a-z][a-z0-9]*)/g, function (whole, id) {
      var f = field(it, id);
      if (!f) return whole;
      if (f.t === "grid") return gridText(it, id, hole);
      if (f.t === "list") return listText(it, id, hole);
      return val(it, id, hole);
    });
  }

  // ─────────────────────── левая колонка ───────────────────────

  function hay(o) {
    var s = [];
    ["en", "ru", "es"].forEach(function (l) {
      if (o.n && o.n[l]) s.push(o.n[l]);
      if (o.k && o.k[l]) s.push(o.k[l]);
    });
    return s.join(" ").toLowerCase();
  }

  function matches(it, words, secName) {
    var h = hay(it) + " " + secName;
    for (var i = 0; i < words.length; i++) if (h.indexOf(words[i]) < 0) return false;
    return true;
  }

  function drawList() {
    var q = el("search").value.trim().toLowerCase();
    var words = q ? q.split(/\s+/) : [];
    var box = el("list");
    box.textContent = "";
    var shown = 0;
    shownIds = [];

    cat.sections.forEach(function (sec) {
      var secName = (sec.n[lang] || sec.n.en).toLowerCase();
      var rows = cat.items.filter(function (it) {
        return it.s === sec.id && (!words.length || matches(it, words, secName));
      });
      if (!rows.length) return;
      shown += rows.length;
      if (words.length || open[sec.id]) rows.forEach(function (r) { shownIds.push(r.id); });

      var wrap = document.createElement("div");
      wrap.className = "sec" + ((words.length || open[sec.id]) ? "" : " closed");

      var h = document.createElement("h3");
      var ar = document.createElement("span");
      ar.className = "ar"; ar.textContent = "▼";
      h.appendChild(ar);
      h.appendChild(document.createTextNode(sec.n[lang] || sec.n.en));
      var cnt = document.createElement("span");
      cnt.style.cssText = "margin-left:auto;opacity:.6;font-weight:500";
      cnt.textContent = rows.length;
      h.appendChild(cnt);
      h.onclick = function () { open[sec.id] = !open[sec.id]; drawList(); };
      wrap.appendChild(h);

      var body = document.createElement("div");
      body.className = "body";
      rows.forEach(function (it) {
        var r = document.createElement("div");
        r.className = "row" + (it.id === sel ? " on" : "");
        r.textContent = name(it);
        r.onclick = function () { pick(it.id); };
        body.appendChild(r);
      });
      wrap.appendChild(body);
      box.appendChild(wrap);
    });

    if (!shown) {
      var n = document.createElement("div");
      n.id = "none"; n.textContent = t("write.none");
      box.appendChild(n);
    }
  }

  // ─────────────────────── правая колонка ───────────────────────

  function pick(id) {
    sel = id; vals = {};
    var it = item(id);
    it.f.forEach(function (f) {
      if (f.t === "int") vals[f.id] = f.d;
      else if (f.t === "choice") vals[f.id] = f.d;
      else if (f.t === "grid") vals[f.id] = [];
      else if (f.t === "list") vals[f.id] = [];
      else vals[f.id] = f.d || "";
    });
    resize(it);
    el("empty").style.display = "none";
    el("card").style.display = "";
    el("title").textContent = name(it);
    var sec = cat.sections.filter(function (s) { return s.id === it.s; })[0];
    el("sub").textContent = sec ? (sec.n[lang] || sec.n.en) : "";
    drawList(); drawForm(); recompute();
  }

  /* Сетки и списки зависят от чисел: меняется число — меняется размер. */
  function resize(it) {
    it.f.forEach(function (f) {
      if (f.t === "grid") {
        var r = num(it, f.rows), c = num(it, f.cols), old = vals[f.id] || [], out = [];
        for (var i = 0; i < r; i++) {
          var row = [];
          for (var j = 0; j < c; j++) row.push((old[i] && old[i][j]) || "");
          out.push(row);
        }
        vals[f.id] = out;
      } else if (f.t === "list") {
        var n = num(it, f.n), o = vals[f.id] || [], a = [];
        for (var k = 0; k < n; k++) a.push(o[k] || "");
        vals[f.id] = a;
      }
    });
  }

  function label(f) {
    var l = cat.labels[f.l];
    return l ? (l[lang] || l.en) : f.id;
  }

  function drawForm() {
    var it = item(sel), box = el("fields");
    box.textContent = "";

    it.f.forEach(function (f) {
      var row = document.createElement("div");
      row.className = "fld" + (f.t === "grid" || f.t === "list" ? " top" : "");
      var lb = document.createElement("label");
      lb.textContent = label(f);
      row.appendChild(lb);

      if (f.t === "text") {
        var i = document.createElement("input");
        i.type = "text"; i.value = vals[f.id] || "";
        i.oninput = function () { vals[f.id] = i.value; recompute(); };
        row.appendChild(i);

      } else if (f.t === "int") {
        var w = document.createElement("div");
        w.className = "num";
        var minus = document.createElement("button"); minus.textContent = "−";
        var span = document.createElement("span"); span.textContent = vals[f.id];
        var plus = document.createElement("button"); plus.textContent = "+";
        function step(d) {
          var v = Math.min(f.hi, Math.max(f.lo, num(it, f.id) + d));
          vals[f.id] = v; span.textContent = v; resize(it); drawForm(); recompute();
        }
        minus.onclick = function () { step(-1); };
        plus.onclick = function () { step(1); };
        w.appendChild(minus); w.appendChild(span); w.appendChild(plus);
        row.appendChild(w);

      } else if (f.t === "choice") {
        var s = document.createElement("select");
        f.o.forEach(function (o) {
          var op = document.createElement("option");
          op.value = o.v; op.textContent = o.n[lang] || o.n.en;
          if (o.v === vals[f.id]) op.selected = true;
          s.appendChild(op);
        });
        s.onchange = function () { vals[f.id] = s.value; recompute(); };
        row.appendChild(s);

      } else if (f.t === "grid") {
        var g = document.createElement("div");
        g.className = "grid";
        g.style.gridTemplateColumns = "repeat(" + num(it, f.cols) + ", minmax(48px, 1fr))";
        vals[f.id].forEach(function (r, ri) {
          r.forEach(function (c, ci) {
            var i2 = document.createElement("input");
            i2.type = "text"; i2.value = c;
            i2.oninput = function () { vals[f.id][ri][ci] = i2.value; recompute(); };
            g.appendChild(i2);
          });
        });
        row.appendChild(g);

      } else if (f.t === "list") {
        var g2 = document.createElement("div");
        g2.className = "grid";
        g2.style.gridTemplateColumns = "1fr";
        vals[f.id].forEach(function (c, ci) {
          var i3 = document.createElement("input");
          i3.type = "text"; i3.value = c;
          i3.oninput = function () { vals[f.id][ci] = i3.value; recompute(); };
          g2.appendChild(i3);
        });
        row.appendChild(g2);
      }
      box.appendChild(row);
    });
  }

  function recompute() {
    var it = item(sel);
    var shown = build(true), plain = build(false);
    var p = el("preview");
    p.className = "";
    try {
      p.innerHTML = katex.renderToString(shown, {
        displayMode: !!it.d, throwOnError: true, strict: false
      });
    } catch (e) {
      p.className = "bad";
      p.textContent = String(e.message || e).replace(/^KaTeX parse error:\s*/, "");
    }
    el("outtext").value = plain;
  }

  function wrapped() {
    var it = item(sel), s = build(false);
    return it.d ? "$$\n" + s + "\n$$" : "$" + s + "$";
  }

  function said() {
    var s = el("said");
    s.textContent = t("write.copied");
    s.classList.add("on");
    setTimeout(function () { s.classList.remove("on"); }, 1400);
  }

  function copy(text) {
    send("onCopy", text);
    if (navigator.clipboard && navigator.clipboard.writeText)
      navigator.clipboard.writeText(text).catch(function () {});
    said();
  }

  // ─────────────────────── снаружи ───────────────────────

  window.Write = {
    setCatalog: function (data) {
      cat = typeof data === "string" ? JSON.parse(data) : data;
      drawList();
      el("search").focus();   // окно открылось — можно сразу печатать
    },
    setLang: function (l) {
      lang = l || "en";
      if (cat) { drawList(); if (sel) { pick(sel); } }
    },
    setLabels: function (map) {
      var m = typeof map === "string" ? JSON.parse(map) : map;
      for (var k in m) UI[k] = m[k];
      el("search").placeholder = t("write.search");
      el("copy").textContent = t("write.copy");
      el("copyplain").textContent = t("write.copyPlain");
      el("empty").textContent = t("write.hint");
    },
    setTheme: function (dark) {
      document.documentElement.setAttribute("data-theme", dark ? "dark" : "light");
    },
    text: function () { return sel ? wrapped() : ""; }
  };

  el("search").oninput = drawList;
  el("search").placeholder = t("write.search");
  el("empty").textContent = t("write.hint");
  el("copy").textContent = t("write.copy");
  el("copyplain").textContent = t("write.copyPlain");
  el("copy").onclick = function () { if (sel) copy(wrapped()); };
  el("copyplain").onclick = function () { if (sel) copy(build(false)); };
  function step(d) {
    if (!shownIds.length) return;
    var i = shownIds.indexOf(sel);
    i = i < 0 ? (d > 0 ? 0 : shownIds.length - 1) : (i + d + shownIds.length) % shownIds.length;
    pick(shownIds[i]);
    var on = document.querySelector(".row.on");
    if (on && on.scrollIntoView) on.scrollIntoView({ block: "nearest" });
  }

  document.addEventListener("keydown", function (e) {
    if (e.key === "ArrowDown") { e.preventDefault(); step(1); return; }
    if (e.key === "ArrowUp") { e.preventDefault(); step(-1); return; }
    if (e.key === "Enter" && document.activeElement === el("search")) {
      e.preventDefault();
      if (shownIds.length) pick(shownIds[sel && shownIds.indexOf(sel) >= 0 ? shownIds.indexOf(sel) : 0]);
      return;
    }
    if (e.key === "Escape") { el("search").value = ""; drawList(); }
    if ((e.ctrlKey || e.metaKey) && e.key === "f") { e.preventDefault(); el("search").focus(); }
  });
})();
