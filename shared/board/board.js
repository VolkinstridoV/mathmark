/*
 * Холст доски: лист в точку, перо, выделитель, фигуры.
 *
 * Всё, что нарисовано, хранится в мировых координатах — независимо от того,
 * куда сдвинут и насколько приближён вид. Поэтому файл доски не зависит от
 * размера окна, а масштаб можно менять сколько угодно без потери точности.
 *
 * Рисуется в обычном холсте страницы. Так сделано намеренно: позже сюда же
 * лягут листочки с формулами, а их рисует KaTeX — он живёт в этой же странице.
 */
(function () {
  'use strict';

  var B = {};
  window.Board = B;

  var cv = document.getElementById('c');
  var ctx = cv.getContext('2d');
  var toolsBox = document.getElementById('tools');
  var colorsBox = document.getElementById('colors');
  var widthInput = document.getElementById('width');
  var pctLabel = document.getElementById('pct');

  /* вид: сдвиг и масштаб */
  var view = { x: 0, y: 0, z: 1 };
  var items = [];          // всё, что лежит на доске
  var undone = [];         // отменённое, чтобы можно было вернуть
  var labels = {};

  var tool = 'pen';
  var color = '#7C3AED';
  var width = 3;
  var selected = -1;
  var dirty = false;

  var COLORS = ['#1B1720', '#7C3AED', '#C0392B', '#1E7A5A', '#2B6CB0', '#B7791F'];

  var ICONS = {
    select: '<svg viewBox="0 0 24 24"><path d="M5 3l6 17 2.5-6.5L20 11z"/></svg>',
    hand:   '<svg viewBox="0 0 24 24"><path d="M8 12V6a1.5 1.5 0 013 0v5m0-1V5a1.5 1.5 0 013 0v6m0-2a1.5 1.5 0 013 0v6a6 6 0 01-6 6h-1a6 6 0 01-6-6v-3a1.5 1.5 0 013 0"/></svg>',
    pen:    '<svg viewBox="0 0 24 24"><path d="M4 20l4-1 10-10-3-3L5 16z"/><path d="M14 6l3 3"/></svg>',
    marker: '<svg viewBox="0 0 24 24"><path d="M5 19h6l8-8-4-4-8 8z"/><path d="M4 21h16"/></svg>',
    eraser: '<svg viewBox="0 0 24 24"><path d="M6 18l-3-3 9-9 6 6-6 6z"/><path d="M8 20h11"/></svg>',
    line:   '<svg viewBox="0 0 24 24"><path d="M4 20L20 4"/></svg>',
    arrow:  '<svg viewBox="0 0 24 24"><path d="M4 20L19 5"/><path d="M12 5h7v7"/></svg>',
    rect:   '<svg viewBox="0 0 24 24"><rect x="4" y="6" width="16" height="12" rx="1"/></svg>',
    ellipse:'<svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="8"/></svg>',
    triangle:'<svg viewBox="0 0 24 24"><path d="M12 4L20 19H4z"/></svg>',
    undo:   '<svg viewBox="0 0 24 24"><path d="M9 7L4 12l5 5"/><path d="M4 12h11a5 5 0 010 10h-2"/></svg>',
    redo:   '<svg viewBox="0 0 24 24"><path d="M15 7l5 5-5 5"/><path d="M20 12H9a5 5 0 000 10h2"/></svg>',
  };

  var TOOLS = ['select', 'hand', null, 'pen', 'marker', 'eraser', null,
               'line', 'arrow', 'rect', 'ellipse', 'triangle', null, 'undo', 'redo'];

  /* ——————————— перевод мировых и экранных координат ——————————— */

  function toWorld(px, py) {
    return { x: (px - view.x) / view.z, y: (py - view.y) / view.z };
  }

  /* ——————————— фон в точку ——————————— */

  /* Шаг сетки переключается ступенями, чтобы при отдалении точки
     не слипались в кашу, а при приближении не разъезжались. */
  function dotStep() {
    var base = 24;
    var step = base;
    while (step * view.z < 14) step *= 2;
    while (step * view.z > 56) step /= 2;
    return step;
  }

  function drawDots(w, h) {
    var step = dotStep();
    var s = step * view.z;
    var x0 = view.x % s;
    var y0 = view.y % s;
    var r = view.z < 0.6 ? 0.8 : 1.1;
    ctx.fillStyle = css('--dot');
    for (var x = x0; x < w; x += s) {
      for (var y = y0; y < h; y += s) {
        ctx.beginPath();
        ctx.arc(x, y, r, 0, 6.2832);
        ctx.fill();
      }
    }
  }

  function css(name) {
    return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  }

  /* ——————————— отрисовка ——————————— */

  function draw() {
    var w = cv.width / devicePixelRatio;
    var h = cv.height / devicePixelRatio;
    ctx.setTransform(devicePixelRatio, 0, 0, devicePixelRatio, 0, 0);
    ctx.clearRect(0, 0, w, h);
    ctx.fillStyle = css('--paper');
    ctx.fillRect(0, 0, w, h);
    drawDots(w, h);

    ctx.save();
    ctx.translate(view.x, view.y);
    ctx.scale(view.z, view.z);
    for (var i = 0; i < items.length; i++) drawItem(items[i], i === selected);
    if (draft) drawItem(draft, false);
    ctx.restore();

    pctLabel.textContent = Math.round(view.z * 100) + '%';
  }

  function drawItem(it, isSelected) {
    ctx.lineCap = 'round';
    ctx.lineJoin = 'round';
    ctx.strokeStyle = it.color;
    ctx.lineWidth = it.w;
    ctx.globalAlpha = it.tool === 'marker' ? 0.32 : 1;

    if (it.t === 'stroke') {
      var p = it.pts;
      if (p.length < 2) {
        ctx.beginPath();
        ctx.arc(p[0][0], p[0][1], it.w / 2, 0, 6.2832);
        ctx.fillStyle = it.color;
        ctx.fill();
      } else {
        ctx.beginPath();
        ctx.moveTo(p[0][0], p[0][1]);
        for (var i = 1; i < p.length; i++) ctx.lineTo(p[i][0], p[i][1]);
        ctx.stroke();
      }
    } else if (it.t === 'shape') {
      shapePath(it);
      ctx.stroke();
    }
    ctx.globalAlpha = 1;

    if (isSelected) {
      var b = bounds(it);
      ctx.setLineDash([5 / view.z, 4 / view.z]);
      ctx.strokeStyle = css('--accent');
      ctx.lineWidth = 1.5 / view.z;
      ctx.strokeRect(b.x - 6, b.y - 6, b.w + 12, b.h + 12);
      ctx.setLineDash([]);
    }
  }

  function shapePath(it) {
    var x = it.x, y = it.y, w = it.w2, h = it.h2;
    ctx.beginPath();
    if (it.kind === 'line' || it.kind === 'arrow') {
      ctx.moveTo(x, y);
      ctx.lineTo(x + w, y + h);
      if (it.kind === 'arrow') {
        var a = Math.atan2(h, w);
        var len = Math.min(18, Math.hypot(w, h) * 0.3);
        ctx.moveTo(x + w, y + h);
        ctx.lineTo(x + w - len * Math.cos(a - 0.4), y + h - len * Math.sin(a - 0.4));
        ctx.moveTo(x + w, y + h);
        ctx.lineTo(x + w - len * Math.cos(a + 0.4), y + h - len * Math.sin(a + 0.4));
      }
    } else if (it.kind === 'rect') {
      ctx.rect(x, y, w, h);
    } else if (it.kind === 'ellipse') {
      ctx.ellipse(x + w / 2, y + h / 2, Math.abs(w / 2), Math.abs(h / 2), 0, 0, 6.2832);
    } else if (it.kind === 'triangle') {
      ctx.moveTo(x + w / 2, y);
      ctx.lineTo(x + w, y + h);
      ctx.lineTo(x, y + h);
      ctx.closePath();
    }
  }

  function bounds(it) {
    if (it.t === 'stroke') {
      var xs = it.pts.map(function (p) { return p[0]; });
      var ys = it.pts.map(function (p) { return p[1]; });
      var x = Math.min.apply(null, xs), y = Math.min.apply(null, ys);
      return { x: x, y: y, w: Math.max.apply(null, xs) - x, h: Math.max.apply(null, ys) - y };
    }
    return {
      x: Math.min(it.x, it.x + it.w2), y: Math.min(it.y, it.y + it.h2),
      w: Math.abs(it.w2), h: Math.abs(it.h2),
    };
  }

  /* ——————————— ввод ——————————— */

  var draft = null;
  var drag = null;

  function pos(e) {
    var r = cv.getBoundingClientRect();
    return { x: e.clientX - r.left, y: e.clientY - r.top };
  }

  cv.addEventListener('pointerdown', function (e) {
    cv.setPointerCapture(e.pointerId);
    var p = pos(e);
    var wpt = toWorld(p.x, p.y);

    if (tool === 'hand' || e.button === 1 || e.shiftKey) {
      drag = { kind: 'pan', sx: p.x, sy: p.y, ox: view.x, oy: view.y };
      document.body.classList.add('panning');
      return;
    }

    if (tool === 'select') {
      selected = hit(wpt);
      if (selected >= 0) drag = { kind: 'move', sx: wpt.x, sy: wpt.y, item: items[selected], snap: clone(items[selected]) };
      draw();
      return;
    }

    if (tool === 'eraser') {
      var i = hit(wpt);
      if (i >= 0) { push(); items.splice(i, 1); selected = -1; markDirty(); draw(); }
      drag = { kind: 'erase' };
      return;
    }

    if (tool === 'pen' || tool === 'marker') {
      draft = { t: 'stroke', tool: tool, color: color, w: width, pts: [[wpt.x, wpt.y]] };
      drag = { kind: 'draw' };
      return;
    }

    draft = { t: 'shape', kind: tool, tool: 'pen', color: color, w: width,
              x: wpt.x, y: wpt.y, w2: 0, h2: 0 };
    drag = { kind: 'shape' };
  });

  cv.addEventListener('pointermove', function (e) {
    if (!drag) return;
    var p = pos(e);
    var wpt = toWorld(p.x, p.y);

    if (drag.kind === 'pan') {
      view.x = drag.ox + (p.x - drag.sx);
      view.y = drag.oy + (p.y - drag.sy);
      draw();
    } else if (drag.kind === 'draw') {
      var last = draft.pts[draft.pts.length - 1];
      if (Math.hypot(wpt.x - last[0], wpt.y - last[1]) * view.z > 1.4) {
        draft.pts.push([round(wpt.x), round(wpt.y)]);
        draw();
      }
    } else if (drag.kind === 'shape') {
      draft.w2 = wpt.x - draft.x;
      draft.h2 = wpt.y - draft.y;
      draw();
    } else if (drag.kind === 'move') {
      var dx = wpt.x - drag.sx, dy = wpt.y - drag.sy;
      var it = drag.item, s = drag.snap;
      if (it.t === 'stroke') {
        for (var i = 0; i < it.pts.length; i++) {
          it.pts[i][0] = round(s.pts[i][0] + dx);
          it.pts[i][1] = round(s.pts[i][1] + dy);
        }
      } else { it.x = round(s.x + dx); it.y = round(s.y + dy); }
      markDirty();
      draw();
    } else if (drag.kind === 'erase') {
      var j = hit(wpt);
      if (j >= 0) { push(); items.splice(j, 1); markDirty(); draw(); }
    }
  });

  function stop() {
    if (draft) {
      var keep = draft.t === 'stroke'
        ? draft.pts.length > 0
        : Math.abs(draft.w2) > 2 || Math.abs(draft.h2) > 2;
      if (keep) { push(); items.push(draft); markDirty(); }
      draft = null;
    }
    drag = null;
    document.body.classList.remove('panning');
    draw();
  }
  cv.addEventListener('pointerup', stop);
  cv.addEventListener('pointercancel', stop);

  cv.addEventListener('wheel', function (e) {
    e.preventDefault();
    var p = pos(e);
    zoomAt(p.x, p.y, e.deltaY < 0 ? 1.12 : 1 / 1.12);
  }, { passive: false });

  function zoomAt(px, py, k) {
    var before = toWorld(px, py);
    view.z = Math.min(8, Math.max(0.08, view.z * k));
    view.x = px - before.x * view.z;
    view.y = py - before.y * view.z;
    draw();
  }

  function round(v) { return Math.round(v * 10) / 10; }
  function clone(o) { return JSON.parse(JSON.stringify(o)); }

  /* Попадание: сначала по рамке, потом по самой линии — иначе выделять
     тонкие штрихи было бы мучением. */
  function hit(p) {
    for (var i = items.length - 1; i >= 0; i--) {
      var b = bounds(items[i]);
      var pad = Math.max(8, items[i].w);
      if (p.x < b.x - pad || p.y < b.y - pad || p.x > b.x + b.w + pad || p.y > b.y + b.h + pad) continue;
      if (items[i].t === 'stroke') {
        var pts = items[i].pts;
        for (var k = 1; k < pts.length; k++) {
          if (nearSegment(p, pts[k - 1], pts[k], pad)) return i;
        }
        if (pts.length === 1 && Math.hypot(p.x - pts[0][0], p.y - pts[0][1]) < pad) return i;
      } else {
        return i;
      }
    }
    return -1;
  }

  function nearSegment(p, a, b, pad) {
    var vx = b[0] - a[0], vy = b[1] - a[1];
    var len2 = vx * vx + vy * vy;
    var t = len2 ? Math.max(0, Math.min(1, ((p.x - a[0]) * vx + (p.y - a[1]) * vy) / len2)) : 0;
    var dx = p.x - (a[0] + t * vx), dy = p.y - (a[1] + t * vy);
    return dx * dx + dy * dy < pad * pad;
  }

  /* ——————————— отмена ——————————— */

  function push() { undone = []; history.push(clone(items)); if (history.length > 80) history.shift(); }
  var history = [];

  function undo() {
    if (!history.length) return;
    undone.push(clone(items));
    items = history.pop();
    selected = -1;
    markDirty();
    draw();
  }

  function redo() {
    if (!undone.length) return;
    history.push(clone(items));
    items = undone.pop();
    selected = -1;
    markDirty();
    draw();
  }

  /* ——————————— панели ——————————— */

  function buildTools() {
    toolsBox.innerHTML = '';
    TOOLS.forEach(function (name) {
      if (name === null) {
        toolsBox.appendChild(document.createElement('hr'));
        return;
      }
      var b = document.createElement('button');
      b.innerHTML = ICONS[name];
      b.title = labels['board.' + name] || name;
      b.dataset.tool = name;
      b.onclick = function () {
        if (name === 'undo') return undo();
        if (name === 'redo') return redo();
        setTool(name);
      };
      toolsBox.appendChild(b);
    });
    highlight();
  }

  function highlight() {
    toolsBox.querySelectorAll('button').forEach(function (b) {
      b.classList.toggle('on', b.dataset.tool === tool);
    });
  }

  function setTool(name) {
    tool = name;
    if (name !== 'select') selected = -1;
    document.body.dataset.tool = name;
    highlight();
    draw();
  }

  function buildColors() {
    colorsBox.innerHTML = '';
    COLORS.forEach(function (col) {
      var i = document.createElement('i');
      i.style.background = col;
      i.onclick = function () {
        color = col;
        colorsBox.querySelectorAll('i').forEach(function (n) { n.classList.remove('on'); });
        i.classList.add('on');
      };
      if (col === color) i.classList.add('on');
      colorsBox.appendChild(i);
    });
  }

  widthInput.oninput = function () { width = +widthInput.value; };
  document.getElementById('in').onclick = function () { zoomAt(cv.clientWidth / 2, cv.clientHeight / 2, 1.25); };
  document.getElementById('out').onclick = function () { zoomAt(cv.clientWidth / 2, cv.clientHeight / 2, 0.8); };
  document.getElementById('fit').onclick = function () { fit(); };

  function fit() {
    if (!items.length) { view = { x: cv.clientWidth / 2, y: cv.clientHeight / 2, z: 1 }; draw(); return; }
    var b = items.map(bounds);
    var x0 = Math.min.apply(null, b.map(function (r) { return r.x; }));
    var y0 = Math.min.apply(null, b.map(function (r) { return r.y; }));
    var x1 = Math.max.apply(null, b.map(function (r) { return r.x + r.w; }));
    var y1 = Math.max.apply(null, b.map(function (r) { return r.y + r.h; }));
    var pad = 60;
    var z = Math.min((cv.clientWidth - pad * 2) / Math.max(1, x1 - x0),
                     (cv.clientHeight - pad * 2) / Math.max(1, y1 - y0));
    view.z = Math.min(4, Math.max(0.08, z));
    view.x = cv.clientWidth / 2 - (x0 + x1) / 2 * view.z;
    view.y = cv.clientHeight / 2 - (y0 + y1) / 2 * view.z;
    draw();
  }

  document.addEventListener('keydown', function (e) {
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'z') {
      e.preventDefault();
      e.shiftKey ? redo() : undo();
      return;
    }
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 's') { e.preventDefault(); send('onSave', B.dump()); return; }
    if (e.key === 'Delete' || e.key === 'Backspace') {
      if (selected >= 0) { push(); items.splice(selected, 1); selected = -1; markDirty(); draw(); }
    }
    var keys = { v: 'select', h: 'hand', p: 'pen', m: 'marker', e: 'eraser',
                 l: 'line', a: 'arrow', r: 'rect', o: 'ellipse', t: 'triangle' };
    if (!e.ctrlKey && !e.metaKey && keys[e.key.toLowerCase()]) setTool(keys[e.key.toLowerCase()]);
  });

  /* ——————————— наружу ——————————— */

  function markDirty() {
    if (!dirty) { dirty = true; send('onDirty', ''); }
  }

  B.setLabels = function (map) { for (var k in map) labels[k] = map[k]; buildTools(); };
  B.setTheme = function (dark) {
    document.documentElement.setAttribute('data-theme', dark ? 'dark' : 'light');
    draw();
  };

  /** Доска в текст: обычный JSON, который можно прочитать и поправить руками. */
  B.dump = function () {
    dirty = false;
    return JSON.stringify({ version: 1, view: { x: Math.round(view.x), y: Math.round(view.y), z: +view.z.toFixed(3) }, items: items }, null, 1);
  };

  B.load = function (text) {
    var data = null;
    try { data = JSON.parse(text); } catch (e) { data = null; }
    items = (data && data.items) || [];
    if (data && data.view) view = { x: data.view.x, y: data.view.y, z: data.view.z || 1 };
    else view = { x: cv.clientWidth / 2, y: cv.clientHeight / 2, z: 1 };
    history = []; undone = []; selected = -1; dirty = false;
    draw();
  };

  B.clear = function () { push(); items = []; selected = -1; markDirty(); draw(); };

  function send(name, payload) {
    if (window.webkit && webkit.messageHandlers && webkit.messageHandlers.mathmark) {
      webkit.messageHandlers.mathmark.postMessage(JSON.stringify({ name: name, payload: payload }));
    }
  }

  function resize() {
    cv.width = cv.clientWidth * devicePixelRatio;
    cv.height = cv.clientHeight * devicePixelRatio;
    draw();
  }
  window.addEventListener('resize', resize);
  /* Окно может открыться уже нужного размера, и события resize не будет —
     поэтому следим за самим холстом. */
  if (window.ResizeObserver) new ResizeObserver(resize).observe(cv);

  buildColors();
  buildTools();
  view = { x: 0, y: 0, z: 1 };
  resize();
  window.addEventListener('load', resize);
  setTimeout(resize, 60);
  setTimeout(resize, 300);
})();
