/* Knead — edit one letterform at a time on a phone.
   Mould the vector points directly on the glyph, or select a point and
   nudge it with precision on the trackpad below (your finger never covers
   the node you're shaping). Vanilla JS, no build, no dependencies.

   Letterforms are real cubic outlines baked from several type families
   (serif, sans, mono, display, blackletter, pixel). Working coordinates are
   y-down (SVG); font data is y-up, flipped on load. */

(function () {
  "use strict";

  var DATA = window.GLYPHS;
  if (!DATA) return;

  var FAMS = {};
  DATA.families.forEach(function (f) { FAMS[f.id] = f; });

  var SVGNS = "http://www.w3.org/2000/svg";
  var fam;             // active family object
  var A, EM_H;         // y-flip reference (ascent) + em height, per family

  // ---- DOM ---------------------------------------------------------------
  var stage   = document.getElementById("stage");
  var rail    = document.getElementById("rail");
  var readout = document.getElementById("readout");
  var pad     = document.getElementById("pad");
  var puck    = document.getElementById("pad-puck");
  var sens    = document.getElementById("sens");
  var toastEl = document.getElementById("toast");
  var famSel  = document.getElementById("family");

  // ---- state -------------------------------------------------------------
  var pristine = {};   // "famId/letter" -> original (flipped) contours
  var session  = {};   // "famId/letter" -> current working contours
  var key, work;       // current letter + its working contours
  var sel = { c: 0, n: 0 };
  var target = "anchor";              // anchor | in | out
  var fillOn = false;
  var history = [];                   // snapshots for undo (current letter)
  var scale = 1;                      // user-units -> screen px (for sizing)

  function sk(k) { return fam.id + "/" + k; }   // session/pristine key

  // ---- geometry helpers --------------------------------------------------
  function clone(c) { return JSON.parse(JSON.stringify(c)); }
  function len(dx, dy) { return Math.hypot(dx, dy); }

  function isSmooth(nd) {
    var ix = nd.inX - nd.x, iy = nd.inY - nd.y;
    var ox = nd.outX - nd.x, oy = nd.outY - nd.y;
    var li = len(ix, iy), lo = len(ox, oy);
    if (li < 1 || lo < 1) return false;          // a handle is retracted -> corner
    var cross = ix * oy - iy * ox;               // ~0 when colinear
    var dot = ix * ox + iy * oy;                 // <0 when pointing opposite ways
    return Math.abs(cross) / (li * lo) < 0.08 && dot < 0;
  }

  function buildGlyph(k) {
    var g = fam.glyphs[k];
    var c = g.contours.map(function (ct) {
      return ct.map(function (p) {
        return {
          x: p.x, y: A - p.y,
          inX: p.inX, inY: A - p.inY,
          outX: p.outX, outY: A - p.outY,
          smooth: false
        };
      });
    });
    c.forEach(function (ct) { ct.forEach(function (nd) { nd.smooth = isSmooth(nd); }); });
    return c;
  }

  // ---- load family / glyph / frame --------------------------------------
  function loadFamily(id) {
    fam = FAMS[id] || DATA.families[0];
    A = fam.ascent;
    EM_H = fam.ascent - fam.descent;
    rail.style.fontFamily = '"' + fam.railFont + '", Georgia, serif';
    if (famSel) famSel.value = fam.id;
    if (!key || !fam.glyphs[key]) key = fam.glyphs.a ? "a" : Object.keys(fam.glyphs)[0];
    sel = { c: 0, n: 0 };
    loadGlyph(key);
  }

  function loadGlyph(k) {
    key = k;
    if (!pristine[sk(k)]) pristine[sk(k)] = buildGlyph(k);
    if (!session[sk(k)]) session[sk(k)] = clone(pristine[sk(k)]);
    work = session[sk(k)];
    if (sel.c >= work.length) sel = { c: 0, n: 0 };
    history = [];
    frame();
    syncRail();
    syncSmoothBtn();
    render();
    updateUndo();
  }

  // viewBox sized to the letter (+ metric guides), centred and scaled to fit.
  function frame() {
    var xs = [], ys = [];
    work.forEach(function (ct) {
      ct.forEach(function (p) {
        xs.push(p.x, p.inX, p.outX);
        ys.push(p.y, p.inY, p.outY);
      });
    });
    var minx = Math.min.apply(null, xs), maxx = Math.max.apply(null, xs);
    var miny = Math.min.apply(null, ys), maxy = Math.max.apply(null, ys);
    // keep baseline + x-height in view
    miny = Math.min(miny, A - fam.capHeight);
    maxy = Math.max(maxy, A - fam.descent);
    var w = maxx - minx, h = maxy - miny;
    var padU = Math.max(w, h) * 0.16;
    stage.setAttribute("viewBox",
      (minx - padU) + " " + (miny - padU) + " " + (w + 2 * padU) + " " + (h + 2 * padU));
    stage.setAttribute("preserveAspectRatio", "xMidYMid meet");
  }

  function measureScale() {
    var ctm = stage.getScreenCTM();
    scale = ctm ? Math.abs(ctm.a) || 1 : 1;
  }

  // ---- path data ---------------------------------------------------------
  function contourD(ct) {
    var d = "M" + r(ct[0].x) + " " + r(ct[0].y);
    for (var i = 0; i < ct.length; i++) {
      var cur = ct[i], nx = ct[(i + 1) % ct.length];
      d += "C" + r(cur.outX) + " " + r(cur.outY) + " " +
                 r(nx.inX) + " " + r(nx.inY) + " " +
                 r(nx.x) + " " + r(nx.y);
    }
    return d + "Z";
  }
  function glyphD() { return work.map(contourD).join(" "); }
  function r(n) { return Math.round(n * 100) / 100; }

  // ---- render ------------------------------------------------------------
  function el(name, attrs) {
    var e = document.createElementNS(SVGNS, name);
    for (var k in attrs) e.setAttribute(k, attrs[k]);
    return e;
  }

  function render() {
    measureScale();
    var nodeR = 6.5 / scale, hitR = 21 / scale, handR = 5 / scale;
    while (stage.firstChild) stage.removeChild(stage.firstChild);

    var vb = stage.viewBox.baseVal;

    // guides: baseline + x-height + cap
    [["base", A], ["x", A - fam.xHeight], ["cap", A - fam.capHeight]].forEach(function (gd) {
      stage.appendChild(el("line", {
        class: "guide", x1: vb.x, y1: gd[1], x2: vb.x + vb.width, y2: gd[1]
      }));
    });

    // fill
    if (fillOn) stage.appendChild(el("path", { class: "glyph-fill", d: glyphD() }));
    // outline (always, so the shape reads while editing)
    stage.appendChild(el("path", { class: "glyph-outline", d: glyphD(),
      style: fillOn ? "opacity:.25" : "" }));

    // handles for the selected node
    var node = work[sel.c] && work[sel.c][sel.n];
    if (node) {
      stage.appendChild(el("line", { class: "handle-line", x1: node.x, y1: node.y, x2: node.inX, y2: node.inY }));
      stage.appendChild(el("line", { class: "handle-line", x1: node.x, y1: node.y, x2: node.outX, y2: node.outY }));
      stage.appendChild(el("rect", { class: "handle-dot",
        x: node.inX - handR, y: node.inY - handR, width: handR * 2, height: handR * 2 }));
      stage.appendChild(el("rect", { class: "handle-dot",
        x: node.outX - handR, y: node.outY - handR, width: handR * 2, height: handR * 2 }));
    }

    // anchors
    work.forEach(function (ct, ci) {
      ct.forEach(function (nd, ni) {
        var on = (ci === sel.c && ni === sel.n);
        stage.appendChild(el("circle", {
          class: "node" + (nd.smooth ? " smooth" : "") + (on ? " sel" : ""),
          cx: nd.x, cy: nd.y, r: nodeR
        }));
      });
    });

    updateReadout();
  }

  function updateReadout() {
    var nd = work[sel.c] && work[sel.c][sel.n];
    if (!nd) { readout.hidden = true; return; }
    readout.hidden = false;
    var px = nd.x, py = A - nd.y;            // back to font units (y-up) for the type nerd
    if (target === "in")  { px = nd.inX;  py = A - nd.inY; }
    if (target === "out") { px = nd.outX; py = A - nd.outY; }
    var label = target === "anchor" ? "Point" : (target === "in" ? "In handle" : "Out handle");
    readout.innerHTML = "<b>" + key + "</b> &middot; <span class='tgt'>" + label + "</span><br>" +
      "x " + Math.round(px) + "&nbsp;&nbsp; y " + Math.round(py);
  }

  // ---- mutation ----------------------------------------------------------
  function pushHistory() {
    history.push(clone(work));
    if (history.length > 60) history.shift();
    updateUndo();
  }
  function updateUndo() {
    document.getElementById("undo").disabled = history.length === 0;
  }

  // move a point of the selected node by (dx,dy) in user units
  function nudge(which, dx, dy) {
    var nd = work[sel.c][sel.n];
    if (which === "anchor") {
      nd.x += dx; nd.y += dy;
      nd.inX += dx; nd.inY += dy;
      nd.outX += dx; nd.outY += dy;
    } else if (which === "in") {
      nd.inX += dx; nd.inY += dy;
      if (nd.smooth) mirror(nd, "in");
    } else {
      nd.outX += dx; nd.outY += dy;
      if (nd.smooth) mirror(nd, "out");
    }
  }

  // keep the opposite handle colinear (preserve its own length)
  function mirror(nd, moved) {
    if (moved === "in") {
      var dx = nd.inX - nd.x, dy = nd.inY - nd.y;
      var ol = len(nd.outX - nd.x, nd.outY - nd.y) || len(dx, dy);
      var l = len(dx, dy) || 1;
      nd.outX = nd.x - dx / l * ol;
      nd.outY = nd.y - dy / l * ol;
    } else {
      var ex = nd.outX - nd.x, ey = nd.outY - nd.y;
      var il = len(nd.inX - nd.x, nd.inY - nd.y) || len(ex, ey);
      var l2 = len(ex, ey) || 1;
      nd.inX = nd.x - ex / l2 * il;
      nd.inY = nd.y - ey / l2 * il;
    }
  }

  function setSmooth(on) {
    var nd = work[sel.c][sel.n];
    nd.smooth = on;
    if (on) {
      // align handles along the average of their current directions
      var ox = nd.outX - nd.x, oy = nd.outY - nd.y;
      var ix = nd.x - nd.inX, iy = nd.y - nd.inY;   // line direction (in -> anchor)
      var lo = len(ox, oy), li = len(nd.inX - nd.x, nd.inY - nd.y);
      var dx = (lo ? ox / lo : 0) + (li ? ix / Math.hypot(ix, iy) : 0);
      var dy = (lo ? oy / lo : 0) + (li ? iy / Math.hypot(ix, iy) : 0);
      var dl = len(dx, dy);
      if (dl < 1e-3) { dx = ox || 1; dy = oy; dl = len(dx, dy); }
      dx /= dl; dy /= dl;
      if (!lo && !li) { lo = li = 60; }
      nd.outX = nd.x + dx * (lo || li);
      nd.outY = nd.y + dy * (lo || li);
      nd.inX = nd.x - dx * (li || lo);
      nd.inY = nd.y - dy * (li || lo);
    }
    syncSmoothBtn();
    render();
  }

  // ---- pointer mapping ---------------------------------------------------
  function clientToUser(cx, cy) {
    var ctm = stage.getScreenCTM().inverse();
    var p = stage.createSVGPoint(); p.x = cx; p.y = cy;
    p = p.matrixTransform(ctm);
    return { x: p.x, y: p.y };
  }
  function userToClient(ux, uy) {
    var ctm = stage.getScreenCTM();
    return { x: ctm.a * ux + ctm.c * uy + ctm.e, y: ctm.b * ux + ctm.d * uy + ctm.f };
  }

  // ---- direct moulding on the glyph -------------------------------------
  var drag = null;   // {kind, offx, offy}

  stage.addEventListener("pointerdown", function (ev) {
    ev.preventDefault();
    var node = work[sel.c] && work[sel.c][sel.n];
    var best = null, bestD = 28;   // px

    // selected node's handles take priority
    if (node) {
      [["in", node.inX, node.inY], ["out", node.outX, node.outY]].forEach(function (h) {
        var s = userToClient(h[1], h[2]);
        var d = len(s.x - ev.clientX, s.y - ev.clientY);
        if (d < bestD) { bestD = d; best = { kind: h[0] }; }
      });
    }
    // then any anchor
    work.forEach(function (ct, ci) {
      ct.forEach(function (nd, ni) {
        var s = userToClient(nd.x, nd.y);
        var d = len(s.x - ev.clientX, s.y - ev.clientY);
        if (d < bestD) { bestD = d; best = { kind: "anchor", c: ci, n: ni }; }
      });
    });
    if (!best) return;

    if (best.kind === "anchor") { sel = { c: best.c, n: best.n }; target = "anchor"; syncTargetSeg(); syncSmoothBtn(); }
    pushHistory();
    var nd = work[sel.c][sel.n];
    var ux = best.kind === "in" ? nd.inX : best.kind === "out" ? nd.outX : nd.x;
    var uy = best.kind === "in" ? nd.inY : best.kind === "out" ? nd.outY : nd.y;
    var u = clientToUser(ev.clientX, ev.clientY);
    drag = { kind: best.kind, offx: ux - u.x, offy: uy - u.y };
    stage.setPointerCapture(ev.pointerId);
    render();
  });

  stage.addEventListener("pointermove", function (ev) {
    if (!drag) return;
    var u = clientToUser(ev.clientX, ev.clientY);
    var nd = work[sel.c][sel.n];
    var tx = u.x + drag.offx, ty = u.y + drag.offy;
    if (drag.kind === "anchor") nudge("anchor", tx - nd.x, ty - nd.y);
    else if (drag.kind === "in") { nd.inX = tx; nd.inY = ty; if (nd.smooth) mirror(nd, "in"); }
    else { nd.outX = tx; nd.outY = ty; if (nd.smooth) mirror(nd, "out"); }
    render();
  });

  function endDrag(ev) { if (drag) { drag = null; try { stage.releasePointerCapture(ev.pointerId); } catch (e) {} } }
  stage.addEventListener("pointerup", endDrag);
  stage.addEventListener("pointercancel", endDrag);

  // ---- trackpad (precise, occlusion-free) --------------------------------
  var padState = null;   // {lastx, lasty}

  function unitsPerPx() { return (+sens.value) / 100; }

  pad.addEventListener("pointerdown", function (ev) {
    ev.preventDefault();
    if (!(work[sel.c] && work[sel.c][sel.n])) { flash("Tap a point on the letter first"); return; }
    pushHistory();
    padState = { lastx: ev.clientX, lasty: ev.clientY };
    pad.classList.add("live");
    placePuck(ev);
    pad.setPointerCapture(ev.pointerId);
  });
  pad.addEventListener("pointermove", function (ev) {
    if (!padState) return;
    var k = unitsPerPx();
    var dx = (ev.clientX - padState.lastx) * k;
    var dy = (ev.clientY - padState.lasty) * k;
    padState.lastx = ev.clientX; padState.lasty = ev.clientY;
    nudge(target, dx, dy);
    placePuck(ev);
    render();
  });
  function padEnd(ev) {
    if (!padState) return;
    padState = null;
    pad.classList.remove("live");
    try { pad.releasePointerCapture(ev.pointerId); } catch (e) {}
  }
  pad.addEventListener("pointerup", padEnd);
  pad.addEventListener("pointercancel", padEnd);

  function placePuck(ev) {
    var b = pad.getBoundingClientRect();
    var x = Math.max(10, Math.min(b.width - 10, ev.clientX - b.left));
    var y = Math.max(10, Math.min(b.height - 10, ev.clientY - b.top));
    puck.style.left = x + "px";
    puck.style.top = y + "px";
  }

  // ---- selection stepping ------------------------------------------------
  function flat() {
    var list = [];
    work.forEach(function (ct, ci) { ct.forEach(function (_, ni) { list.push([ci, ni]); }); });
    return list;
  }
  function step(dir) {
    var list = flat();
    var idx = list.findIndex(function (p) { return p[0] === sel.c && p[1] === sel.n; });
    idx = (idx + dir + list.length) % list.length;
    sel = { c: list[idx][0], n: list[idx][1] };
    syncSmoothBtn();
    render();
  }

  // ---- UI wiring ---------------------------------------------------------
  function syncRail() {
    Array.prototype.forEach.call(rail.children, function (b) {
      b.classList.toggle("on", b.dataset.key === key);
    });
  }
  function syncTargetSeg() {
    document.querySelectorAll(".seg [data-target]").forEach(function (b) {
      b.classList.toggle("on", b.dataset.target === target);
    });
  }
  function syncSmoothBtn() {
    var nd = work[sel.c] && work[sel.c][sel.n];
    var btn = document.getElementById("smooth");
    var on = !!(nd && nd.smooth);
    btn.classList.toggle("on", on);
    btn.setAttribute("aria-pressed", on ? "true" : "false");
    btn.textContent = on ? "Smooth" : "Corner";
  }

  // letter rail (letters are shared across families)
  Object.keys(DATA.families[0].glyphs).forEach(function (k) {
    var b = document.createElement("button");
    b.type = "button"; b.dataset.key = k; b.textContent = k;
    b.addEventListener("click", function () { loadGlyph(k); });
    rail.appendChild(b);
  });

  // family dropdown
  DATA.families.forEach(function (f) {
    var o = document.createElement("option");
    o.value = f.id; o.textContent = f.label;
    famSel.appendChild(o);
  });
  famSel.addEventListener("change", function () { loadFamily(famSel.value); });

  // target segmented control
  document.querySelectorAll(".seg [data-target]").forEach(function (b) {
    b.addEventListener("click", function () { target = b.dataset.target; syncTargetSeg(); updateReadout(); });
  });

  document.getElementById("prev").addEventListener("click", function () { step(-1); });
  document.getElementById("next").addEventListener("click", function () { step(1); });
  document.getElementById("smooth").addEventListener("click", function () {
    var nd = work[sel.c] && work[sel.c][sel.n]; if (!nd) return;
    pushHistory(); setSmooth(!nd.smooth);
  });
  document.getElementById("undo").addEventListener("click", function () {
    if (!history.length) return;
    session[sk(key)] = history.pop(); work = session[sk(key)];
    if (sel.c >= work.length) sel = { c: 0, n: 0 };
    updateUndo(); syncSmoothBtn(); render();
  });
  document.getElementById("reset").addEventListener("click", function () {
    pushHistory();
    session[sk(key)] = clone(pristine[sk(key)]); work = session[sk(key)];
    sel = { c: 0, n: 0 }; syncSmoothBtn(); render();
    flash("Letter reset");
  });
  document.getElementById("fill-toggle").addEventListener("click", function () {
    fillOn = !fillOn;
    this.classList.toggle("on", fillOn);
    this.setAttribute("aria-pressed", fillOn ? "true" : "false");
    render();
  });
  document.getElementById("export").addEventListener("click", exportSVG);

  // ---- export ------------------------------------------------------------
  function exportSVG() {
    var adv = fam.glyphs[key].advance;
    var svg =
      '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ' + adv + ' ' + Math.round(EM_H) + '">\n' +
      '  <path fill-rule="evenodd" d="' + glyphD() + '"/>\n' +
      '</svg>\n';
    copy(svg, "SVG copied to clipboard");
  }
  function copy(text, msg) {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text).then(function () { flash(msg); }, function () { fallbackCopy(text, msg); });
    } else fallbackCopy(text, msg);
  }
  function fallbackCopy(text, msg) {
    var ta = document.createElement("textarea");
    ta.value = text; ta.style.position = "fixed"; ta.style.opacity = "0";
    document.body.appendChild(ta); ta.select();
    try { document.execCommand("copy"); flash(msg); } catch (e) { flash("Copy failed"); }
    document.body.removeChild(ta);
  }

  // ---- toast -------------------------------------------------------------
  var toastT;
  function flash(msg) {
    toastEl.textContent = msg;
    toastEl.classList.add("show");
    clearTimeout(toastT);
    toastT = setTimeout(function () { toastEl.classList.remove("show"); }, 1500);
  }

  // ---- resize / boot -----------------------------------------------------
  var rT;
  window.addEventListener("resize", function () { clearTimeout(rT); rT = setTimeout(render, 120); });
  window.addEventListener("orientationchange", function () { setTimeout(render, 250); });

  // start on the default family's lowercase a
  loadFamily(DATA.default || DATA.families[0].id);
  syncTargetSeg();
  syncSmoothBtn();

  // register the service worker for offline use (skipped on file://)
  if ("serviceWorker" in navigator && location.protocol.indexOf("http") === 0) {
    window.addEventListener("load", function () {
      navigator.serviceWorker.register("sw.js").catch(function () {});
    });
  }
})();
