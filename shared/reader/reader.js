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

  function math(tex, display) {
    var out;
    try {
      out = katex.renderToString(tex.trim(), {
        displayMode: display,
        throwOnError: false,   // кривая формула краснеет на месте, файл живёт дальше
        strict: false,
        trust: false,
      });
    } catch (e) {
      out = '<span class="bad">' + esc(tex) + '</span>';
    }
    return display ? '<div class="disp">' + out + '</div>' : out;
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
