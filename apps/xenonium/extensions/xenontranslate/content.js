/* XenonTranslate 1.0  -  Xenonium extension
 * - Translates the selected text (small button -> card)
 * - Translates the whole page / restores the original (toolbar button or Alt+T)
 * - Detects the page language automatically; also translates dynamic content
 * Service: translate.googleapis.com (gtx, keyless) - fallback: MyMemory (selected text only)
 */
(function () {
  "use strict";
  if (window.__xenonTranslateLoaded || !window.xenon) return;
  window.__xenonTranslateLoaded = true;
  if (window.top !== window) return;

  var LANGS = [
    ["tr", "Türkçe"], ["en", "English"], ["de", "Deutsch"], ["fr", "Français"], ["es", "Español"],
    ["it", "Italiano"], ["pt", "Português"], ["ru", "Русский"], ["ar", "العربية"], ["zh-CN", "中文 (简体)"],
    ["ja", "日本語"], ["ko", "한국어"], ["nl", "Nederlands"], ["pl", "Polski"], ["uk", "Українська"],
    ["el", "Ελληνικά"], ["he", "עברית"], ["fa", "فارسی"], ["hi", "हिन्दी"], ["id", "Bahasa Indonesia"],
    ["sv", "Svenska"], ["cs", "Čeština"], ["ro", "Română"], ["hu", "Magyar"], ["bg", "Български"],
    ["az", "Azərbaycanca"], ["da", "Dansk"], ["fi", "Suomi"], ["no", "Norsk"], ["vi", "Tiếng Việt"], ["th", "ไทย"]
  ];
  var SEP = "\n⁣\n";           // invisible separator: splits the parts of a batched translation
  var SKIP_TAGS = { SCRIPT: 1, STYLE: 1, NOSCRIPT: 1, CODE: 1, PRE: 1, TEXTAREA: 1, INPUT: 1, SELECT: 1, SVG: 1, MATH: 1, KBD: 1, SAMP: 1 };
  var BATCH_CHARS = 1200, PARALLEL = 3;

  var state = {
    target: "tr", translated: false, running: false, detected: null,
    originals: new Map(), observer: null, pending: new Set(), obsTimer: null
  };

  /* ---------------------------------------------------------------- service */
  function gtx(text, target) {
    var url = "https://translate.googleapis.com/translate_a/single?client=gtx&sl=auto&tl=" + encodeURIComponent(target) +
      "&dt=t&q=" + encodeURIComponent(text);
    return xenon.fetch(url).then(function (r) {
      if (r.status !== 200) throw new Error("Translation service returned an error (" + r.status + ")");
      var d = JSON.parse(r.text);
      var out = "";
      (d[0] || []).forEach(function (s) { out += s[0] || ""; });
      return { text: out, lang: d[2] || null };
    });
  }
  function mymemory(text, target) {
    // fallback service for short text only; chunks of at most ~450 characters
    var chunks = [], cur = "";
    text.split(/(?<=[.!?\n])\s+/).forEach(function (s) {
      if ((cur + " " + s).length > 450 && cur) { chunks.push(cur); cur = s; } else { cur = cur ? cur + " " + s : s; }
    });
    if (cur) chunks.push(cur);
    return Promise.all(chunks.map(function (c) {
      var url = "https://api.mymemory.translated.net/get?q=" + encodeURIComponent(c.slice(0, 480)) +
        "&langpair=" + encodeURIComponent((state.detected || "en") + "|" + target);
      return xenon.fetch(url).then(function (r) { return JSON.parse(r.text).responseData.translatedText; });
    })).then(function (parts) { return { text: parts.join(" "), lang: null }; });
  }
  function translate(text, target) {
    return gtx(text, target).catch(function (e1) {
      return mymemory(text, target).catch(function () { throw e1; });
    });
  }

  /* ---------------------------------------------------------------- UI (shadow DOM) */
  var host = document.createElement("xenon-translate-root");
  host.style.cssText = "all:initial;position:fixed;z-index:2147483647;top:0;left:0;width:0;height:0";
  var root = host.attachShadow({ mode: "closed" });
  var CSS = ":host{all:initial}*{box-sizing:border-box;font-family:'Ubuntu','Noto Sans',system-ui,sans-serif}" +
    ".card{position:fixed;background:#140c36;color:#e6faff;border:1px solid #3a2a78;border-radius:14px;box-shadow:0 10px 40px #0009;" +
    "padding:14px 16px;font-size:14px;line-height:1.45;max-width:380px;min-width:240px}" +
    ".hd{display:flex;align-items:center;gap:8px;font-weight:700;color:#6ee7ff;margin-bottom:10px;letter-spacing:.04em}" +
    ".hd .x{margin-left:auto;cursor:pointer;opacity:.7;font-size:18px;line-height:1}.hd .x:hover{opacity:1}" +
    "select,button{font:inherit;color:#e6faff;background:#241a5c;border:1px solid #3a2a78;border-radius:8px;padding:6px 10px}" +
    "select{-webkit-appearance:none;appearance:none;padding-right:28px;color-scheme:dark;" +
    "background-image:linear-gradient(45deg,transparent 50%,#6ee7ff 50%),linear-gradient(135deg,#6ee7ff 50%,transparent 50%);" +
    "background-position:calc(100% - 16px) 55%,calc(100% - 11px) 55%;background-size:5px 5px;background-repeat:no-repeat}" +
    "option{background:#241a5c;color:#e6faff}" +
    "button{cursor:pointer}button:hover{background:#34297f}button.pri{background:linear-gradient(135deg,#6ee7ff,#9b6bff);border:0;color:#fff;font-weight:600}" +
    ".row{display:flex;gap:8px;margin-top:10px;align-items:center}.row select{flex:1}" +
    ".res{margin-top:10px;max-height:240px;overflow:auto;white-space:pre-wrap;word-break:break-word;background:#0b0720;border-radius:8px;padding:10px}" +
    ".mut{opacity:.65;font-size:12px;margin-top:8px}" +
    ".bar{height:4px;border-radius:2px;background:#241a5c;margin-top:10px;overflow:hidden}.bar i{display:block;height:100%;width:0;background:linear-gradient(90deg,#6ee7ff,#7c4dff);transition:width .2s}" +
    ".fab{position:fixed;width:34px;height:34px;border-radius:50%;background:linear-gradient(135deg,#6ee7ff,#9b6bff);color:#fff;display:flex;" +
    "align-items:center;justify-content:center;cursor:pointer;box-shadow:0 4px 14px #0008;font-size:15px;font-weight:700;user-select:none}" +
    ".fab:hover{transform:scale(1.08)}";
  try {
    var sheet = new CSSStyleSheet(); sheet.replaceSync(CSS); root.adoptedStyleSheets = [sheet];
  } catch (e) { var st = document.createElement("style"); st.textContent = CSS; root.appendChild(st); }
  function mount() { if (!host.isConnected) (document.documentElement || document.body).appendChild(host); }

  function el(tag, cls, text) { var e = document.createElement(tag); if (cls) e.className = cls; if (text != null) e.textContent = text; return e; }
  function langSelect(value, onchange) {
    var s = el("select");
    LANGS.forEach(function (l) { var o = el("option", null, l[1]); o.value = l[0]; if (l[0] === value) o.selected = true; s.appendChild(o); });
    s.addEventListener("change", function () { onchange(s.value); });
    return s;
  }
  function setTarget(code) { state.target = code; xenon.storage.set("target", code); }

  /* ---- selected-text button + card ---- */
  var fab = null, card = null, lastSel = "";
  function removeFab() { if (fab) { fab.remove(); fab = null; } }
  function removeCard() { if (card) { card.remove(); card = null; } }
  function selectionRect() {
    var s = window.getSelection(); if (!s || !s.rangeCount) return null;
    var r = s.getRangeAt(0).getBoundingClientRect();
    return r && (r.width || r.height) ? r : null;
  }
  function onSelect(ev) {
    if (ev && host.contains && ev.target === host) return;
    setTimeout(function () {
      var s = window.getSelection(); var t = s ? String(s).trim() : "";
      if (t.length < 2 || t.length > 5000) { removeFab(); return; }
      var r = selectionRect(); if (!r) return;
      lastSel = t; mount(); removeFab();
      fab = el("div", "fab", "文"); fab.title = "XenonTranslate: translate selected text";
      fab.style.left = Math.min(window.innerWidth - 44, Math.max(6, r.right + 6)) + "px";
      fab.style.top = Math.min(window.innerHeight - 44, Math.max(6, r.bottom + 6)) + "px";
      fab.addEventListener("mousedown", function (e) { e.preventDefault(); e.stopPropagation(); });
      fab.addEventListener("click", function (e) { e.stopPropagation(); showSelectionCard(r, lastSel); });
      root.appendChild(fab);
    }, 10);
  }
  document.addEventListener("mouseup", onSelect, true);
  document.addEventListener("keyup", function (e) { if (e.shiftKey || e.key === "Shift") onSelect(e); }, true);
  document.addEventListener("mousedown", function (e) { if (e.target !== host) { removeFab(); if (card && !card.__pinned) removeCard(); } }, true);
  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape") { removeFab(); removeCard(); closePanel(); }
    if (e.altKey && (e.key === "t" || e.key === "T")) { e.preventDefault(); togglePanel(); }
  }, true);

  function showSelectionCard(rect, text) {
    removeFab(); removeCard(); mount();
    card = el("div", "card"); card.__pinned = true;
    var hd = el("div", "hd"); hd.appendChild(el("span", null, "XenonTranslate"));
    var x = el("span", "x", "×"); x.addEventListener("click", removeCard); hd.appendChild(x);
    var res = el("div", "res", "Translating…");
    var meta = el("div", "mut", "");
    var row = el("div", "row");
    var sel = langSelect(state.target, function (v) { setTarget(v); run(); });
    var copy = el("button", null, "Copy");
    copy.addEventListener("click", function () {
      var t = res.textContent;
      if (navigator.clipboard && navigator.clipboard.writeText) navigator.clipboard.writeText(t).catch(function () {});
      var ta = document.createElement("textarea"); ta.value = t; document.body.appendChild(ta); ta.select();
      try { document.execCommand("copy"); } catch (e) {} ta.remove(); copy.textContent = "Copied";
      setTimeout(function () { copy.textContent = "Copy"; }, 1200);
    });
    row.appendChild(sel); row.appendChild(copy);
    card.appendChild(hd); card.appendChild(res); card.appendChild(row); card.appendChild(meta);
    var left = Math.min(window.innerWidth - 400, Math.max(8, rect.left));
    var top = rect.bottom + 12; if (top + 260 > window.innerHeight) top = Math.max(8, rect.top - 270);
    card.style.left = left + "px"; card.style.top = top + "px";
    root.appendChild(card);
    function run() {
      res.textContent = "Translating…"; meta.textContent = "";
      translate(text, state.target).then(function (r) {
        res.textContent = r.text;
        if (r.lang) { state.detected = r.lang; meta.textContent = "Detected language: " + langName(r.lang); }
      }).catch(function (e) { res.textContent = "Could not translate: " + e.message; });
    }
    run();
  }
  function langName(code) { for (var i = 0; i < LANGS.length; i++) if (LANGS[i][0].toLowerCase() === String(code).toLowerCase() || LANGS[i][0].split("-")[0] === code) return LANGS[i][1]; return code; }

  /* ---- page translation ---- */
  function collectNodes(rootNode) {
    var out = [];
    var w = document.createTreeWalker(rootNode, NodeFilter.SHOW_TEXT, {
      acceptNode: function (n) {
        var v = n.nodeValue; if (!v || !/\p{L}/u.test(v)) return NodeFilter.FILTER_REJECT;
        if (state.originals.has(n)) return NodeFilter.FILTER_REJECT;
        for (var p = n.parentNode; p && p !== document; p = p.parentNode) {
          if (p.nodeType !== 1) continue;
          if (SKIP_TAGS[p.tagName.toUpperCase()] || p === host) return NodeFilter.FILTER_REJECT;
          if (p.isContentEditable || p.getAttribute("translate") === "no" || p.classList.contains("notranslate")) return NodeFilter.FILTER_REJECT;
        }
        return NodeFilter.FILTER_ACCEPT;
      }
    });
    var n; while ((n = w.nextNode())) out.push(n);
    return out;
  }
  function inView(n) {
    var p = n.parentElement; if (!p) return false;
    var r = p.getBoundingClientRect(); return r.bottom > -200 && r.top < window.innerHeight + 600;
  }
  /* --- units: text nodes in the same block (split by bold / links etc.) are translated like a single sentence --- */
  function blockOf(node) {
    for (var p = node.parentElement; p && p !== document.body; p = p.parentElement) {
      var d = getComputedStyle(p).display;
      if (d.indexOf("inline") !== 0) return p;
    }
    return document.body;
  }
  /* sentence containing links: links are marked one by one with <k>..</k>, the plain text in between is translated as a whole */
  function isLink(n) { return !!(n.parentElement && n.parentElement.closest("a,button,input,select,label,summary")); }
  function buildTags(u) {
    var items = [], k = 0, str = "";
    u.nodes.forEach(function (n) {
      if (isLink(n)) { k++; items.push({ link: n, k: k }); str += "<" + k + ">" + n.nodeValue.trim() + "</" + k + ">"; }
      else {
        var last = items[items.length - 1];
        if (last && last.plain) last.plain.push(n); else items.push({ plain: [n] });
        str += n.nodeValue.replace(/\s+/g, " ");
      }
    });
    u.items = items; u.linkCount = k; u.text = str;
  }
  function applyTags(u, translated) {
    var parts = translated.split(/<(\d+)>([\s\S]*?)<\/\1>/);        // [seg0, n1, c1, seg1, n2, c2, seg2 ...]
    var K = u.linkCount;
    if (parts.length !== 3 * K + 1) return false;
    var segs = [], contents = [];
    for (var i = 0; i < K; i++) {
      if (parseInt(parts[1 + 3 * i], 10) !== i + 1 || !parts[2 + 3 * i].trim()) return false;   // order is broken / empty tag
      contents.push(parts[2 + 3 * i]);
    }
    for (var j = 0; j <= K; j++) segs.push(parts[3 * j]);
    var slots = [], cur = 0;
    u.items.forEach(function (it) { if (it.plain) slots[cur] = it; else cur++; });
    for (var s = 0; s <= K; s++) if (!slots[s] && segs[s].replace(/[\s.,;:!?'"()\-–—]+/g, "") !== "") return false; // text landed where there is no plain-text node
    for (var s2 = 0; s2 <= K; s2++) {
      var run = slots[s2]; if (!run) continue;
      var seg = segs[s2].replace(/\s+/g, " ");
      run.plain.forEach(function (n, idx) {
        state.originals.set(n, n.nodeValue);
        n.nodeValue = idx === 0 ? seg : "";
      });
    }
    u.items.forEach(function (it) { if (it.link) setNode(it.link, contents[it.k - 1].replace(/^\s+|\s+$/g, "")); });
    return true;
  }
  function makeUnits(nodes) {
    var map = new Map(), units = [];
    nodes.forEach(function (n) {
      var core = n.nodeValue.trim(); if (!core) return;
      var simple = core.indexOf("<") < 0 && core.indexOf(">") < 0;
      var b = simple ? blockOf(n) : null;
      if (b && map.has(b)) { map.get(b).nodes.push(n); return; }
      var u = { nodes: [n], block: b }; units.push(u);
      if (b) map.set(b, u);
    });
    units.forEach(function (u) {
      u.kind = "single";
      if (u.nodes.length > 1) {
        var b = u.block;
        if (u.nodes.length > 40 || !b || b.querySelector("br,p,div,ul,ol,table,li,h1,h2,h3,h4,h5,h6,pre,blockquote,form")) u.split = true;
        else {
          var inter = u.nodes.some(function (n) { return n.parentElement && n.parentElement.closest("a,button,input,select,label,summary"); });
          u.kind = inter ? "tags" : "sentence";
        }
      }
      u.group = u.kind === "tags";
      if (u.split) { u.text = null; u.len = 0; }
      else if (u.kind === "sentence") { u.text = u.nodes.map(function (n) { return n.nodeValue; }).join("").replace(/\s+/g, " ").trim(); u.len = u.text.length; }
      else if (u.kind === "tags") { buildTags(u); u.len = u.text.length; }
      else { u.text = u.nodes[0].nodeValue.trim(); u.len = u.text.length; }
    });
    var out = [];
    units.forEach(function (u) {
      if (u.split) u.nodes.forEach(function (n) { var t = n.nodeValue.trim(); out.push({ nodes: [n], group: false, text: t, len: t.length }); });
      else out.push(u);
    });
    return out;
  }
  function makeBatches(nodes) {
    var units = makeUnits(nodes);
    // visible ones first
    units.sort(function (a, b) { return (inView(b.nodes[0]) ? 1 : 0) - (inView(a.nodes[0]) ? 1 : 0); });
    var batches = [], cur = [], len = 0;
    units.forEach(function (u) {
      if (len + u.len > BATCH_CHARS && cur.length) { batches.push(cur); cur = []; len = 0; }
      cur.push(u); len += u.len + SEP.length;
    });
    if (cur.length) batches.push(cur);
    return batches;
  }
  function applyUnit(u, translated, target) {
    if (u.kind === "single") { setNode(u.nodes[0], translated.replace(/^\s+|\s+$/g, "") || u.nodes[0].nodeValue.trim()); return Promise.resolve(); }
    if (u.kind === "sentence") {
      // sentence containing standalone formatting (bold/italic...): translated as a whole and placed in the first part
      var full = translated.replace(/^\s+|\s+$/g, "");
      if (!full) return Promise.resolve();
      setNode(u.nodes[0], full);
      for (var k = 1; k < u.nodes.length; k++) { state.originals.set(u.nodes[k], u.nodes[k].nodeValue); u.nodes[k].nodeValue = ""; }
      return Promise.resolve();
    }
    if (applyTags(u, translated)) return Promise.resolve();
    // if the tags were corrupted: translate the parts one by one
    return Promise.all(u.nodes.map(function (n) {
      var c = n.nodeValue.trim();
      return gtx(c, target).then(function (x) { setNode(n, x.text.replace(/^\s+|\s+$/g, "") || c); }).catch(function () {});
    }));
  }
  function totalNodes(units) { return units.reduce(function (s, u) { return s + u.nodes.length; }, 0); }
  function applyBatch(units, target, ui) {
    return gtx(units.map(function (u) { return u.text; }).join(SEP), target).then(function (r) {
      if (r.lang && !state.detected) state.detected = r.lang;
      var parts = r.text.split(SEP);
      if (parts.length !== units.length) {            // if the separator was corrupted, try the units one by one
        return Promise.all(units.map(function (u) {
          return gtx(u.text, target).then(function (x) { return applyUnit(u, x.text, target); }).catch(function () {});
        }));
      }
      return Promise.all(parts.map(function (t, i) { return applyUnit(units[i], t, target); }));
    }).then(function () { ui.done += totalNodes(units); ui.update(); });
  }
  function setNode(n, text) {
    if (!n.isConnected) return;
    var v = n.nodeValue, lead = (v.match(/^\s*/) || [""])[0], trail = (v.match(/\s*$/) || [""])[0];
    state.originals.set(n, v);
    n.nodeValue = lead + text + trail;
  }
  function translatePage(ui) {
    state.running = true;
    var nodes = collectNodes(document.body || document.documentElement);
    var ui2 = ui || { done: 0, update: function () {} };
    ui2.total = nodes.length; ui2.done = 0; ui2.update();
    var batches = makeBatches(nodes), idx = 0, failed = null;
    function worker() {
      if (idx >= batches.length || failed) return Promise.resolve();
      var b = batches[idx++];
      return applyBatch(b, state.target, ui2).catch(function (e) { failed = e; }).then(worker);
    }
    var ws = []; for (var i = 0; i < PARALLEL; i++) ws.push(worker());
    return Promise.all(ws).then(function () {
      state.running = false;
      if (failed) throw failed;
      state.translated = true;
      if (document.title && !state.origTitle) {
        state.origTitle = document.title;
        gtx(document.title, state.target).then(function (r) { document.title = r.text; }).catch(function () {});
      }
      startObserver();
    }).catch(function (e) { state.running = false; throw e; });
  }
  function restorePage() {
    stopObserver();
    state.originals.forEach(function (orig, n) { if (n.isConnected) n.nodeValue = orig; });
    state.originals.clear(); state.translated = false;
    if (state.origTitle) { document.title = state.origTitle; state.origTitle = null; }
  }
  function startObserver() {
    stopObserver();
    state.observer = new MutationObserver(function (muts) {
      muts.forEach(function (m) { m.addedNodes.forEach(function (n) { if (n !== host) state.pending.add(n); }); });
      if (state.obsTimer) return;
      state.obsTimer = setTimeout(function () {
        state.obsTimer = null; var added = Array.from(state.pending); state.pending.clear();
        var nodes = [];
        added.forEach(function (n) {
          if (n.nodeType === 3) { if (!state.originals.has(n) && /\p{L}/u.test(n.nodeValue)) nodes.push(n); }
          else if (n.nodeType === 1 && n.isConnected) nodes = nodes.concat(collectNodes(n));
        });
        if (!nodes.length || !state.translated) return;
        var ui = { done: 0, update: function () {} };
        makeBatches(nodes).reduce(function (p, b) { return p.then(function () { return applyBatch(b, state.target, ui); }); }, Promise.resolve()).catch(function () {});
      }, 600);
    });
    state.observer.observe(document.body || document.documentElement, { childList: true, subtree: true });
  }
  function stopObserver() { if (state.observer) { state.observer.disconnect(); state.observer = null; } state.pending.clear(); }

  /* ---- panel ---- */
  var panel = null;
  function closePanel() { if (panel) { panel.remove(); panel = null; } }
  function togglePanel() { panel ? closePanel() : openPanel(); }
  function openPanel() {
    mount(); closePanel(); removeFab(); removeCard();
    panel = el("div", "card"); panel.style.top = "14px"; panel.style.right = "14px";
    var hd = el("div", "hd"); hd.appendChild(el("span", null, "XenonTranslate"));
    var x = el("span", "x", "×"); x.addEventListener("click", closePanel); hd.appendChild(x);
    var info = el("div", "mut", "Pick a target language, then translate the page.");
    var row = el("div", "row"), sel = langSelect(state.target, function (v) {
      var was = state.translated; setTarget(v);
      if (was) { restorePage(); go(); }
    });
    row.appendChild(el("span", null, "Target:")); row.appendChild(sel);
    var bar = el("div", "bar"), fill = el("i"); bar.appendChild(fill);
    var btns = el("div", "row"), go_ = el("button", "pri", "Translate page"), back = el("button", null, "Show original");
    btns.appendChild(go_); btns.appendChild(back);
    var ui = { total: 0, done: 0, update: function () { fill.style.width = (ui.total ? Math.round(100 * ui.done / ui.total) : 0) + "%"; } };
    function refresh() {
      go_.textContent = state.translated ? "Translate again" : "Translate page";
      back.disabled = !state.translated; back.style.opacity = state.translated ? 1 : .45;
      var d = state.detected ? "Detected page language: " + langName(state.detected) + ". " : "";
      info.textContent = d + (state.translated ? "Page translated." : "Pick a target language, then translate the page.");
    }
    function go() {
      if (state.running) return;
      if (state.translated) restorePage();
      info.textContent = "Translating…"; go_.disabled = true;
      translatePage(ui).then(function () { ui.done = ui.total; ui.update(); }).catch(function (e) {
        info.textContent = "Could not translate: " + e.message;
      }).then(function () { go_.disabled = false; if (!/Could not translate/.test(info.textContent)) refresh(); });
    }
    go_.addEventListener("click", go);
    panel.__go = go;
    back.addEventListener("click", function () { restorePage(); fill.style.width = "0"; refresh(); });
    var note = el("div", "mut", "To translate a selection, select text and click the 文 button. Shortcut: Alt+T");
    panel.appendChild(hd); panel.appendChild(info); panel.appendChild(row); panel.appendChild(btns); panel.appendChild(bar); panel.appendChild(note);
    root.appendChild(panel); refresh();
  }

  /* ---------------------------------------------------------------- start */
  xenon.onCommand(function (name) {
    if (name === "toggle-panel") togglePanel();
    else if (name === "translate-page") { openPanel(); }
    else if (name === "translate-now") { openPanel(); if (panel && panel.__go) panel.__go(); }
    else if (name === "restore-page") restorePage();
  });
  Promise.all([xenon.storage.get("target", null), xenon.info()]).then(function (v) {
    var code = v[0];
    if (!code) {
      var loc = ((v[1] && v[1].locale) || navigator.language || "tr").replace("_", "-");
      var base = loc.split("-")[0];
      code = LANGS.some(function (l) { return l[0] === loc; }) ? loc : (LANGS.some(function (l) { return l[0] === base; }) ? base : "tr");
    }
    state.target = code;
  }).catch(function () {});
})();
