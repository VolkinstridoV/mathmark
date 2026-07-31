/*
 * Правка файла: голый текст, цвета, проверка на лету и подсказки по слэшу.
 *
 * Живёт в той же странице, что и чтение, — поэтому появляется сразу
 * и на телефоне, и на компьютере.
 *
 * Программа ничего не переформатирует: сохраняется ровно то, что набрано.
 * Отметка галочки идёт мимо редактора и по-прежнему меняет один байт.
 */
(function () {
  'use strict';

  var E = {};
  window.MathMarkEdit = E;

  var box, hl, tools, statusBar, verdict, slash;
  var firstBad = -1;
  var labels = {};
  var slashItems = [], slashPick = 0, slashFrom = -1;

  function $(id) { return document.getElementById(id); }
  function esc(s) {
    return s.replace(/[&<>]/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;' }[c];
    });
  }

  /* ——————————— заготовки ——————————— */

  var SNIPPETS = [
    { key: 'task',    ins: '- [ ] ' },
    { key: 'topic',   ins: '- ( ) ' },
    { key: 'hidden',  ins: '||\u0000||' },
    { key: 'formula', ins: '$\u0000$' },
    { key: 'heading', ins: '## ' },
    { key: 'matrix',  ins: null },              // размер спрашивается отдельно
    { key: 'plot',    ins: '<svg viewBox="0 0 320 180" width="100%">\n' +
        '  <line x1="20" y1="145" x2="305" y2="145" stroke="currentColor"/>\n' +
        '  <line x1="34" y1="14" x2="34" y2="164" stroke="currentColor"/>\n' +
        '  <path d="M34 145 L300 30" fill="none" stroke="#7C3AED" stroke-width="2"/>\n' +
        '</svg>\n' },
  ];

  /* Знаки, которые с клавиатуры не набрать. Слово → что вставить. */
  var SLASH = [
    ['sum',      '\\sum_{i=1}^{n} \u0000'],
    ['prod',     '\\prod_{i=1}^{n} \u0000'],
    ['int',      '\\int_{a}^{b} \u0000\\,dx'],
    ['iint',     '\\iint_{D} \u0000\\,dx\\,dy'],
    ['oint',     '\\oint_{\\gamma} \u0000'],
    ['lim',      '\\lim_{x \\to 0} \u0000'],
    ['frac',     '\\frac{\u0000}{}'],
    ['sqrt',     '\\sqrt{\u0000}'],
    ['root',     '\\sqrt[n]{\u0000}'],
    ['pow',      '^{\u0000}'],
    ['sub',      '_{\u0000}'],
    ['matrix',   null],
    ['cases',    '\\begin{cases}\n  \u0000 \\\\\n  \n\\end{cases}'],
    ['aligned',  '\\begin{aligned}\n  \u0000 &= \\\\\n  &=\n\\end{aligned}'],
    ['partial',  '\\frac{\\partial \u0000}{\\partial x}'],
    ['nabla',    '\\nabla \u0000'],
    ['infty',    '\\infty'],
    ['pm',       '\\pm'],
    ['leq',      '\\leqslant'],
    ['geq',      '\\geqslant'],
    ['neq',      '\\neq'],
    ['approx',   '\\approx'],
    ['to',       '\\to'],
    ['alpha',    '\\alpha'], ['beta', '\\beta'], ['gamma', '\\gamma'],
    ['delta',    '\\delta'], ['Delta', '\\Delta'], ['theta', '\\theta'],
    ['lambda',   '\\lambda'], ['mu', '\\mu'], ['pi', '\\pi'],
    ['sigma',    '\\sigma'], ['Sigma', '\\Sigma'], ['phi', '\\varphi'],
    ['omega',    '\\omega'], ['Omega', '\\Omega'], ['eps', '\\varepsilon'],
    ['inR',      'x \\in \\mathbb{R}'],
    ['forall',   '\\forall \u0000'],
    ['exists',   '\\exists \u0000'],
    ['vec',      '\\vec{\u0000}'],
    ['norm',     '\\lVert \u0000 \\rVert'],
  ];

  function matrixSkeleton(rows, cols) {
    var line = [];
    for (var c = 0; c < cols; c++) line.push('');
    var body = [];
    for (var r = 0; r < rows; r++) body.push('  ' + line.join(' & '));
    return '\\begin{pmatrix}\n' + body.join(' \\\\\n') + '\n\\end{pmatrix}';
  }

  /* ——————————— разбор строки на куски для окраски ——————————— */

  var ITEM = /^(\s*-\s[[(][ xX~\/][\])]\s)/;

  function paintLine(line, broken) {
    if (broken) return '<span class="t-bad">' + esc(line) + '</span>';
    if (/^\s*#{1,3}\s/.test(line)) return '<span class="t-head">' + esc(line) + '</span>';
    if (/^\s*<\/?svg/.test(line) || /^\s*<(path|line|text|circle|rect|g)\b/.test(line)) {
      return '<span class="t-draw">' + esc(line) + '</span>';
    }
    if (/^\s*[>|]/.test(line)) return '<span class="t-soft">' + esc(line) + '</span>';

    var out = '';
    var rest = line;
    var m = line.match(ITEM);
    if (m) {
      out += '<span class="t-mark">' + esc(m[1]) + '</span>';
      rest = line.slice(m[1].length);
    }
    /* формулы и скрытое внутри остатка */
    var re = /(\$\$[^$]*\$\$|\$[^$]*\$|\|\|[^|]*\|\||`[^`]*`)/g;
    var last = 0, mm;
    while ((mm = re.exec(rest)) !== null) {
      out += esc(rest.slice(last, mm.index));
      var t = mm[0];
      var cls = t.charAt(0) === '$' ? 't-math' : (t.charAt(0) === '|' ? 't-hide' : 't-soft');
      out += '<span class="' + cls + '">' + esc(t) + '</span>';
      last = mm.index + t.length;
    }
    out += esc(rest.slice(last));
    return out;
  }

  /* ——————————— проверка: что не отрисуется ——————————— */

  function check(text) {
    var lines = text.split('\n');
    var bad = {};
    var inDisplay = false, displayStart = -1, displayBuf = '';

    for (var i = 0; i < lines.length; i++) {
      var line = lines[i];

      /* блок $$ ... $$ */
      var dd = (line.match(/\$\$/g) || []).length;
      if (inDisplay) {
        displayBuf += '\n' + line;
        if (dd > 0) {
          inDisplay = false;
          if (!formulaOk(displayBuf.replace(/\$\$/g, ''), true)) bad[displayStart] = true;
        }
        continue;
      }
      if (dd === 1) { inDisplay = true; displayStart = i; displayBuf = line; continue; }
      if (dd === 2) {
        var inner = line.split('$$')[1] || '';
        if (!formulaOk(inner, true)) bad[i] = true;
      }

      /* формулы в одну строку */
      var single = line.replace(/\$\$[^$]*\$\$/g, '');
      var dollars = (single.match(/\$/g) || []).length;
      if (dollars % 2 === 1) { bad[i] = true; continue; }
      var re = /\$([^$\n]+)\$/g, mm;
      while ((mm = re.exec(single)) !== null) {
        if (!formulaOk(mm[1], false)) { bad[i] = true; break; }
      }

      /* скрытое */
      if (((line.match(/\|\|/g) || []).length) % 2 === 1) bad[i] = true;

      /* скобки отметки не совпадают */
      if (/^\s*-\s[[(][ xX~\/][\])]/.test(line)) {
        var o = line.match(/^\s*-\s([[(])/)[1];
        var c = line.match(/^\s*-\s[[(][ xX~\/]([\])])/)[1];
        if (!((o === '[' && c === ']') || (o === '(' && c === ')'))) bad[i] = true;
      }
    }
    if (inDisplay) bad[displayStart] = true;      // блок не закрыт
    return bad;
  }

  /* Спрашиваем сам движок: он и рисует, значит его слово окончательное. */
  function formulaOk(tex, display) {
    if (!window.katex) return true;
    try {
      katex.renderToString(tex, { displayMode: !!display, throwOnError: true, strict: false });
      return true;
    } catch (e) {
      return false;
    }
  }

  /* ——————————— отрисовка окна правки ——————————— */

  function repaint() {
    var text = box.value;
    var bad = check(text);
    var lines = text.split('\n');
    var painted = [], count = 0;
    firstBad = -1;

    for (var i = 0; i < lines.length; i++) {
      var isBad = !!bad[i];
      if (isBad) { count++; if (firstBad < 0) firstBad = i; }
      painted.push(paintLine(lines[i], isBad));
    }
    hl.innerHTML = painted.join('\n') + '\n';

    statusBar.classList.toggle('bad', count > 0);
    verdict.textContent = count > 0
      ? fmt(labels['edit.problems'], count)
      : labels['edit.clean'];
    syncScroll();
  }

  function fmt(s, v) { return (s || '').replace('%1$s', v); }

  function syncScroll() {
    hl.scrollTop = box.scrollTop;
    hl.scrollLeft = box.scrollLeft;
  }

  /* Нажал на «не отрисуется строк» — попал курсором на первую такую строку. */
  function jumpToBad() {
    if (firstBad < 0) return;
    var pos = 0, lines = box.value.split('\n');
    for (var i = 0; i < firstBad; i++) pos += lines[i].length + 1;
    box.focus();
    box.selectionStart = box.selectionEnd = pos;
    var ratio = pos / Math.max(1, box.value.length);
    box.scrollTop = Math.max(0, box.scrollHeight * ratio - box.clientHeight / 2);
    syncScroll();
  }

  /* ——————————— вставка ——————————— */

  function insert(snippet) {
    var caret = snippet.indexOf('\u0000');
    var clean = snippet.replace('\u0000', '');
    var a = box.selectionStart, b = box.selectionEnd;
    box.value = box.value.slice(0, a) + clean + box.value.slice(b);
    var pos = a + (caret >= 0 ? caret : clean.length);
    box.selectionStart = box.selectionEnd = pos;
    box.focus();
    repaint();
  }

  function askMatrix() {
    var size = (window.prompt(labels['edit.matrixSize'] || 'n x m', '2x2') || '').trim();
    var m = size.match(/^(\d+)\s*[x\u0445\u0425*]\s*(\d+)$/i);
    var rows = m ? Math.min(9, +m[1]) : 2;
    var cols = m ? Math.min(9, +m[2]) : 2;
    insert(matrixSkeleton(rows, cols));
  }

  /* ——————————— меню по слэшу ——————————— */

  function slashLookup() {
    var upto = box.value.slice(0, box.selectionStart);
    var m = upto.match(/(^|[\s({\[])\/([A-Za-z]*)$/);
    if (!m) { hideSlash(); return; }
    slashFrom = box.selectionStart - m[2].length - 1;
    var q = m[2].toLowerCase();
    slashItems = SLASH.filter(function (it) { return it[0].toLowerCase().indexOf(q) === 0; });
    if (!slashItems.length) { hideSlash(); return; }
    slashPick = 0;
    drawSlash();
  }

  function drawSlash() {
    slash.innerHTML = slashItems.map(function (it, i) {
      return '<div class="' + (i === slashPick ? 'sel' : '') + '" data-i="' + i + '">/' +
        it[0] + '</div>';
    }).join('');
    slash.classList.add('on');
  }

  function hideSlash() { slash.classList.remove('on'); slashItems = []; }

  function takeSlash() {
    var it = slashItems[slashPick];
    if (!it) return;
    box.selectionStart = slashFrom;
    box.selectionEnd = box.selectionStart + (box.value.slice(slashFrom).match(/^\/[A-Za-z]*/) || [''])[0].length;
    hideSlash();
    if (it[1] === null) askMatrix(); else insert(it[1]);
  }

  /* ——————————— наружу ——————————— */

  E.setLabels = function (map) {
    for (var k in map) labels[k] = map[k];
    if (tools) buildTools();
    if (box) repaint();
  };

  E.open = function (text) {
    box.value = text;
    window.scrollTo(0, 0);
    document.documentElement.setAttribute('data-mode', 'edit');
    repaint();
    box.focus();
    box.selectionStart = box.selectionEnd = 0;
  };

  E.close = function () {
    document.documentElement.removeAttribute('data-mode');
    hideSlash();
  };

  E.text = function () { return box.value; };
  E.dirty = function () { return box.dataset.start !== box.value; };

  function buildTools() {
    tools.innerHTML = '';
    SNIPPETS.forEach(function (s) {
      var b = document.createElement('button');
      b.textContent = labels['edit.' + s.key] || s.key;
      b.onclick = function () { s.ins === null ? askMatrix() : insert(s.ins); };
      tools.appendChild(b);
    });
    $('save').textContent = labels['edit.save'] || 'Save';
    $('cancel').textContent = labels['edit.cancel'] || 'Cancel';
  }

  document.addEventListener('DOMContentLoaded', function () {
    box = $('raw'); hl = $('hl'); tools = $('tools');
    statusBar = $('status'); verdict = $('verdict'); slash = $('slash');

    buildTools();

    box.addEventListener('input', function () { repaint(); slashLookup(); });
    box.addEventListener('scroll', syncScroll);
    box.addEventListener('click', hideSlash);

    box.addEventListener('keydown', function (e) {
      if (slash.classList.contains('on')) {
        if (e.key === 'ArrowDown') { e.preventDefault(); slashPick = (slashPick + 1) % slashItems.length; drawSlash(); return; }
        if (e.key === 'ArrowUp') { e.preventDefault(); slashPick = (slashPick - 1 + slashItems.length) % slashItems.length; drawSlash(); return; }
        if (e.key === 'Enter' || e.key === 'Tab') { e.preventDefault(); takeSlash(); return; }
        if (e.key === 'Escape') { e.preventDefault(); hideSlash(); return; }
      }
      if (e.key === 'Tab') { e.preventDefault(); insert('  '); }
      if ((e.ctrlKey || e.metaKey) && e.key === 's') { e.preventDefault(); doSave(); }
    });

    slash.addEventListener('click', function (e) {
      var d = e.target.closest ? e.target.closest('div[data-i]') : null;
      if (!d) return;
      slashPick = +d.dataset.i;
      takeSlash();
    });

    verdict.onclick = jumpToBad;
    $('save').onclick = doSave;
    $('cancel').onclick = function () { send('onEditCancel', ''); };
  });

  function doSave() { send('onEditSave', box.value); }

  function send(name, payload) {
    if (window.Android && typeof window.Android[name] === 'function') {
      window.Android[name](payload);
    } else if (window.webkit && webkit.messageHandlers && webkit.messageHandlers.mathmark) {
      webkit.messageHandlers.mathmark.postMessage(JSON.stringify({ name: name, payload: payload }));
    }
  }
})();
