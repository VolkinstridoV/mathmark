/*
 * Страница чтения. Всё, что видно на экране файла, рисуется здесь.
 *
 * Порядок разбора важен и меняться не должен:
 *   1. вынимаем <svg> и формулы между долларами, кладём заглушки;
 *   2. разбираем markdown построчно;
 *   3. возвращаем формулы на место.
 *
 * Иначе разметка съест подчёркивания и звёздочки внутри формул: x_1 стало бы
 * курсивом, а не индексом.
 */
(function () {
  'use strict';

  var MathMark = {};
  window.MathMark = MathMark;

  /* Надписи страницы приходят снаружи — язык выбирает программа, не страница. */
  var labels = { empty: '' };
  MathMark.setLabels = function (map) {
    for (var k in map) labels[k] = map[k];
  };

  /* Одна и та же страница работает и на телефоне, и на компьютере.
     Отличается только способ докричаться до программы:
       Android — объект, положенный внутрь страницы;
       WebKitGTK — очередь сообщений.
     Всё остальное — разбор, вёрстка, формулы — общее до буквы. */
  function send(name, payload) {
    if (window.Android && typeof window.Android[name] === 'function') {
      window.Android[name](payload);
    } else if (window.webkit && webkit.messageHandlers && webkit.messageHandlers.mathmark) {
      webkit.messageHandlers.mathmark.postMessage(JSON.stringify({ name: name, payload: payload }));
    }
  }

  function esc(s) {
    return s.replace(/[&<>]/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;' }[c];
    });
  }

  function attr(s) {
    return s.replace(/[&<>"]/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c];
    });
  }

  function math(tex, display) {
    var out, src = tex.trim();
    try {
      out = katex.renderToString(src, {
        displayMode: display,
        throwOnError: false,   // кривая формула краснеет на месте, файл живёт дальше
        strict: false,
        trust: false,
      });
    } catch (e) {
      out = '<span class="bad">' + esc(tex) + '</span>';
    }
    /* Нарисованная формула носит при себе свой исходник. Без этого вырезание
       куска на доску собирало бы то, что видно на экране, а видно там сразу
       два представления одной формулы — вышла бы каша вроде «∫01dxx∫_0^1». */
    var d = ' data-tex="' + attr(src) + '"';
    return display
      ? '<div class="disp tex" data-disp="1"' + d + '>' + out + '</div>'
      : '<span class="tex" data-disp="0"' + d + '>' + out + '</span>';
  }

  function inlineFmt(s) {
    return s
      .replace(/`([^`]+)`/g, function (_, c) { return '<code>' + esc(c) + '</code>'; })
      /* ||любой кусок|| — закрашен, открывается нажатием. Внутри может быть
         что угодно, включая формулу: она к этому месту уже заглушка. */
      .replace(/\|\|([^|\n]+)\|\|/g,
               '<span class="hide" tabindex="0" role="button">$1</span>')
      .replace(/\*\*([^*]+)\*\*/g, '<b>$1</b>')
      .replace(/~~([^~]+)~~/g, '<s>$1</s>')
      .replace(/(^|[\s(])\*([^*\n]+)\*/g, '$1<i>$2</i>');
  }

  var MARK = { ' ': 'none', '~': 'half', '/': 'half', 'x': 'done', 'X': 'done' };
  var CHECK = '<svg viewBox="0 0 24 24"><path d="M5 13l4 4L19 7"/></svg>';

  /* Разбор одной отмечаемой строки. Смещение символа между скобками считается
     в кодовых единицах строки — Kotlin считает так же, файл читается как UTF-8
     и правится тем же смещением. */
  var ITEM = /^(\s*)-\s([[(])([ xX~/])([\])])\s(.*)$/;

  function pairs(o, c) { return (o === '[' && c === ']') || (o === '(' && c === ')'); }

  MathMark.render = function (src) {
    var slots = [];
    function hold(html) { return '@@' + (slots.push(html) - 1) + '@@'; }

    /* смещения начала строк — по ним считается адрес символа отметки */
    var starts = [0];
    for (var k = 0; k < src.length; k++) if (src[k] === '\n') starts.push(k + 1);
    var srcLines = src.split('\n');

    var t = src
      .replace(/<svg[\s\S]*?<\/svg>/g, function (m) {
        return hold(m.replace('<svg', '<svg class="plot"'));
      })
      .replace(/\$\$([\s\S]+?)\$\$/g, function (_, f) { return hold(math(f, true)); })
      .replace(/\$([^\n$]+?)\$/g, function (_, f) { return hold(math(f, false)); });

    var lines = t.split('\n');
    var out = [], toc = [], i = 0, hn = 0;

    while (i < lines.length) {
      var L = lines[i];

      if (/^\s*$/.test(L)) { i++; continue; }

      var m = L.match(/^(#{1,3})\s+(.*)$/);
      if (m) {
        var lvl = m[1].length, id = 'h' + (hn++);
        if (lvl <= 2) toc.push({ id: id, txt: m[2].replace(/@@\d+@@/g, '…'), lvl: lvl });
        out.push('<h' + lvl + ' id="' + id + '">' + inlineFmt(m[2]) + '</h' + lvl + '>');
        i++; continue;
      }

      if (/^---+\s*$/.test(L)) { out.push('<hr>'); i++; continue; }

      if (/^```/.test(L)) {
        var buf = []; i++;
        while (i < lines.length && !/^```/.test(lines[i])) buf.push(lines[i++]);
        i++;
        out.push('<pre><code>' + esc(buf.join('\n')) + '</code></pre>');
        continue;
      }

      if (/^>\s?/.test(L)) {
        var q = [];
        while (i < lines.length && /^>\s?/.test(lines[i])) q.push(lines[i++].replace(/^>\s?/, ''));
        out.push('<blockquote><p>' + inlineFmt(q.join(' ')) + '</p></blockquote>');
        continue;
      }

      /* отмечаемые строки — задачи и темы вперемешку идут одним списком */
      if (ITEM.test(srcLines[i]) && pairs(srcLines[i].match(ITEM)[2], srcLines[i].match(ITEM)[4])) {
        var li = [];
        while (i < lines.length) {
          var raw = srcLines[i];
          var g = raw ? raw.match(ITEM) : null;
          if (!g || !pairs(g[2], g[4])) break;
          var kind = g[2] === '[' ? 'task' : 'topic';
          var mark = MARK[g[3]] || 'none';
          var off = starts[i] + raw.indexOf(g[2]) + 1;
          /* текст берём из обработанной строки — там формулы уже заглушками */
          var body = lines[i].match(ITEM);
          var label = body ? body[5] : g[5];
          li.push(
            '<li data-kind="' + kind + '" data-mark="' + mark + '" data-off="' + off + '">' +
            '<span class="box ' + kind + '" data-off="' + off + '" tabindex="0" role="checkbox">' +
            CHECK + '</span>' +
            '<span class="txt">' + inlineFmt(label) + '</span></li>'
          );
          i++;
        }
        out.push('<ul class="marks">' + li.join('') + '</ul>');
        continue;
      }

      if (/^\s*[-*]\s+/.test(L)) {
        var ul = [];
        while (i < lines.length && /^\s*[-*]\s+/.test(lines[i]) && !ITEM.test(srcLines[i])) {
          ul.push('<li>' + inlineFmt(lines[i].replace(/^\s*[-*]\s+/, '')) + '</li>');
          i++;
        }
        out.push('<ul class="plain">' + ul.join('') + '</ul>');
        continue;
      }

      if (/^\s*\|.*\|\s*$/.test(L) && /^\s*\|[\s:|-]+\|\s*$/.test(lines[i + 1] || '')) {
        var cells = function (r) {
          return r.trim().replace(/^\||\|$/g, '').split('|').map(function (c) {
            return inlineFmt(c.trim());
          });
        };
        var head = cells(lines[i]); i += 2;
        var rows = [];
        while (i < lines.length && /^\s*\|.*\|\s*$/.test(lines[i])) rows.push(cells(lines[i++]));
        out.push('<div class="tw"><table><thead><tr>' +
          head.map(function (c) { return '<th>' + c + '</th>'; }).join('') +
          '</tr></thead><tbody>' +
          rows.map(function (r) {
            return '<tr>' + r.map(function (c) { return '<td>' + c + '</td>'; }).join('') + '</tr>';
          }).join('') +
          '</tbody></table></div>');
        continue;
      }

      var par = [];
      while (i < lines.length && !/^\s*$/.test(lines[i]) &&
             !/^(#{1,3}\s|>|```|---+\s*$|\s*[-*]\s|\s*\|)/.test(lines[i])) par.push(lines[i++]);
      var text = par.join(' ').trim();
      out.push(/^@@\d+@@$/.test(text) ? text : '<p>' + inlineFmt(text) + '</p>');
    }

    var html = out.join('\n').replace(/@@(\d+)@@/g, function (_, n) { return slots[+n]; });
    document.getElementById('doc').innerHTML =
      html || '<div class="empty">' + esc(labels.empty) + '</div>';

    send('onToc', JSON.stringify(toc));
  };

  /* Точечное обновление после отметки: перерисовывать весь файл незачем,
     прокрутка осталась бы на месте только случайно. */
  MathMark.setMark = function (off, mark) {
    var li = document.querySelector('li[data-off="' + off + '"]');
    if (li) li.setAttribute('data-mark', mark);
  };

  MathMark.setTheme = function (dark) {
    document.documentElement.setAttribute('data-theme', dark ? 'dark' : 'light');
  };

  MathMark.setScale = function (v) {
    document.documentElement.style.setProperty('--sc', v);
  };

  MathMark.goto = function (id) {
    var el = document.getElementById(id);
    if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' });
  };

  MathMark.top = function () { window.scrollTo(0, 0); };

  /* ——— Вырезание куска на доску ———
     Человек выделяет мышью нарисованную страницу, а на доску должен лечь
     исходный markdown — тот же, что лежит в файле. Поэтому мы не берём
     видимый текст, а разбираем разметку обратно: у каждой формулы при себе
     её LaTeX, остальное собирается по тем же правилам, по которым рисовалось.
     Набор разметки маленький и весь известен — он расписан в MathMark.render. */

  var MARKCH = { none: ' ', half: '~', done: 'x' };

  function isTex(n) {
    return n.nodeType === 1 && n.classList && n.classList.contains('tex');
  }

  /* Половины формулы не бывает: если конец выделения попал внутрь неё,
     раздвигаем выделение до её краёв, иначе в кусок попадут внутренности
     KaTeX вместо самой формулы. */
  function widen(range) {
    var r = range.cloneRange();
    for (var n = r.startContainer; n && n !== document.body; n = n.parentNode) {
      if (isTex(n)) { r.setStartBefore(n); break; }
    }
    for (var m = r.endContainer; m && m !== document.body; m = m.parentNode) {
      if (isTex(m)) { r.setEndAfter(m); break; }
    }
    return r;
  }

  function kids(node) {
    var s = '';
    for (var i = 0; i < node.childNodes.length; i++) s += toMd(node.childNodes[i]);
    return s;
  }

  function toMd(node) {
    if (node.nodeType === 3) return node.nodeValue;
    if (node.nodeType === 11) return kids(node);   // обёртка выделения
    if (node.nodeType !== 1) return '';

    var tag = node.nodeName.toLowerCase();
    var cl = node.classList || { contains: function () { return false; } };

    if (cl.contains('tex')) {
      var tex = node.getAttribute('data-tex') || '';
      return node.getAttribute('data-disp') === '1'
        ? '\n\n$$\n' + tex + '\n$$\n\n'
        : '$' + tex + '$';
    }
    if (tag === 'svg') {
      var c = node.cloneNode(true);
      c.classList.remove('plot');          // класс наш, в файле его не было
      return '\n\n' + c.outerHTML + '\n\n';
    }
    if (cl.contains('hide')) return '||' + kids(node) + '||';
    if (tag === 'b' || tag === 'strong') return '**' + kids(node) + '**';
    if (tag === 'i' || tag === 'em') return '*' + kids(node) + '*';
    if (tag === 's') return '~~' + kids(node) + '~~';
    if (tag === 'code' && node.parentNode && node.parentNode.nodeName.toLowerCase() !== 'pre') {
      return '`' + kids(node) + '`';
    }
    if (tag === 'pre') return '\n\n```\n' + node.textContent + '\n```\n\n';
    if (/^h[1-3]$/.test(tag)) return '\n\n' + Array(+tag[1] + 1).join('#') + ' ' + kids(node) + '\n\n';
    if (tag === 'hr') return '\n\n---\n\n';
    if (tag === 'blockquote') return '\n\n> ' + kids(node).trim() + '\n\n';

    if (tag === 'li') {
      var kind = node.getAttribute('data-kind');
      var txt = node.querySelector ? node.querySelector('.txt') : null;
      if (kind) {
        var ch = MARKCH[node.getAttribute('data-mark')] || ' ';
        var br = kind === 'task' ? ['[', ']'] : ['(', ')'];
        return '\n- ' + br[0] + ch + br[1] + ' ' + (txt ? kids(txt) : kids(node)).trim();
      }
      return '\n- ' + kids(node).trim();
    }
    if (tag === 'ul') return '\n' + kids(node) + '\n\n';

    if (tag === 'table') {
      var rows = [], i, j;
      var trs = node.querySelectorAll('tr');
      for (i = 0; i < trs.length; i++) {
        var cells = trs[i].children, line = [];
        for (j = 0; j < cells.length; j++) line.push(kids(cells[j]).trim());
        rows.push('| ' + line.join(' | ') + ' |');
        if (i === 0) rows.push('|' + line.map(function () { return ' --- '; }).join('|') + '|');
      }
      return '\n\n' + rows.join('\n') + '\n\n';
    }

    if (tag === 'p' || tag === 'div') return '\n\n' + kids(node) + '\n\n';
    return kids(node);
  }

  function tidy(s) {
    return s.replace(/[ \t]+\n/g, '\n')
            .replace(/\n{3,}/g, '\n\n')
            .replace(/^\s+|\s+$/g, '');
  }

  /* Заголовок, под которым лежит выделенное — чтобы бумажка помнила не только
     файл, но и место в нём. */
  function headingAbove(node) {
    var el = node.nodeType === 1 ? node : node.parentNode;
    var all = Array.prototype.slice.call(document.querySelectorAll('#doc h1, #doc h2, #doc h3'));
    var best = '';
    for (var i = 0; i < all.length; i++) {
      var pos = all[i].compareDocumentPosition(el);
      if (pos & Node.DOCUMENT_POSITION_FOLLOWING) best = all[i].textContent.trim();
    }
    return best;
  }

  MathMark.hasSelection = function () {
    var s = window.getSelection();
    return !!(s && !s.isCollapsed && s.toString().trim());
  };

  /** Выделенное в виде исходного markdown. Пусто — значит нечего вырезать. */
  MathMark.cut = function () {
    var s = window.getSelection();
    if (!s || s.isCollapsed) return JSON.stringify({ md: '', heading: '' });
    var r = widen(s.getRangeAt(0));
    var md = tidy(toMd(r.cloneContents()));
    return JSON.stringify({ md: md, heading: headingAbove(r.startContainer) });
  };

  document.addEventListener('selectionchange', function () {
    send('onSelection', MathMark.hasSelection() ? '1' : '0');
  });

  function fire(box) {
    var off = parseInt(box.getAttribute('data-off'), 10);
    if (!isNaN(off)) send('onCycle', off);
  }

  document.addEventListener('click', function (e) {
    if (!e.target.closest) return;
    var hide = e.target.closest('.hide');
    if (hide) {
      hide.classList.toggle('open');
      return;                       // нажатие по закрашенному не отмечает задачу
    }
    var box = e.target.closest('.box');
    if (box) fire(box);
  });

  /* Клавиатура — только для компьютера, на телефоне её нет.
     Пробел или Enter отмечают, стрелки и j/k ходят по строкам. */
  document.addEventListener('keydown', function (e) {
    var boxes = Array.prototype.slice.call(document.querySelectorAll('.box'));
    if (!boxes.length) return;
    var here = boxes.indexOf(document.activeElement);

    var act = document.activeElement;
    if ((e.key === ' ' || e.key === 'Enter') && act && act.classList &&
        act.classList.contains('hide')) {
      e.preventDefault();
      act.classList.toggle('open');
      return;
    }

    if ((e.key === ' ' || e.key === 'Enter') && here >= 0) {
      e.preventDefault();
      fire(boxes[here]);
      return;
    }
    var step = (e.key === 'ArrowDown' || e.key === 'j') ? 1
             : (e.key === 'ArrowUp' || e.key === 'k') ? -1 : 0;
    if (!step) return;
    e.preventDefault();
    var next = here < 0 ? (step > 0 ? 0 : boxes.length - 1)
                        : (here + step + boxes.length) % boxes.length;
    boxes[next].focus();
    boxes[next].scrollIntoView({ block: 'nearest' });
  });
})();
